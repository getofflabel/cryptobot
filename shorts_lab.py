"""
shorts_lab.py — THE SHORTS LAB: experimental shorts, trading LIVE on demo.

Owner directive (Wallace, 2026-07-23): the demo account is a sandbox, not a
scoreboard to protect — so instead of paper-testing short ideas on a shadow
ledger for months, this lab fires REAL demo orders on BTC-USDT and lets the
auto-bench system (record_trade_outcome, BENCH_MIN_TRADES=8) judge them on
forward evidence: 8+ live trades and negative expectancy benches a trigger
automatically. This mirrors tactical.py's own "one strategy, one slot,
reconcile-from-exchange" pattern — read that file first if this one is
confusing.

TWO TRIGGERS, ONE SLOT (first-come; only one lab short open at a time):

  forensic_short — the ROUND-41 SURVIVOR, deployed verbatim (step41_shorts.py
    family 4, f>1.5bp/1h — train +$24.57/t x55, val +$193.25/t x8; sealed
    test 0 trades across the whole 2025-26 grind, i.e. a dormant
    crash-catcher that hibernates through quiet regimes and cannot bleed
    while asleep). POP-based: it shorts the EUPHORIA, not the breakdown:
      funding >= +1.5bp (crowded longs paying up)
      AND 1h close is up > +1.5% vs 4 hours ago (the euphoric pop)
      AND ATR(14,1h) > 1.2% of price (the market is actually alive)
    stop   = entry + 1.69%    (measured geometry from six years of data)
    target = entry - 5.07%
    max hold 48h

  cascade_short — the crowded-longs cascade: funding_bps > +2.0 AND the same
    20-bar-low breakdown. Asymmetric, crash-catching geometry:
    stop   = entry + 1.5 x ATR(14, 1h)
    target = entry - 4.5 x ATR(14, 1h)
    max hold 24h

HARD GATE (checked every cycle, before either trigger is evaluated):
  the 4h champion long signal (strategy.vol_gated_ma, fast=20/slow=100,
  min_atr_pct=1.5 — the exact call tactical.py's _champion_state makes) must
  read 0, AND the exchange's net BTC-USDT position must not be long. BloFin
  nets everything on one symbol into one position — if the ride (or tactical)
  is long, a lab short would partially or fully net against it, corrupting
  both books' attribution. Either condition failing = STAND DOWN, no entry.

BOOKKEEPING: mirrors tactical.py exactly. state["shorts_lab"]["open_trade"]
is this book's own record; the exchange holds one NET position combining
core + tactical (both long) + this lab (short). Every cycle starts by
RECONCILING against the exchange: if our short is gone (bracket fired), book
the exit from the fill; if the exchange shows a short we have no record of,
adopt it rather than fight it.

DRY MODE: run_lab(..., dry=True) computes and prints the full decision —
gate status, both trigger conditions, sizing, stop/target — but places NO
orders and makes NO state/log/notify side effects. Used by
step41b_lab_smoke.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

from blofin_private import BlofinDemoPrivate
from step5_paper_trade import (CONTRACT_BTC, LOT, current_funding_bps,
                               execute_maker_or_chase, log_event, notify,
                               now_utc, record_trade_outcome,
                               recent_news_headline, save_state, write_lesson)
from strategy import atr as _atr
from strategy import vol_gated_ma

SYMBOL = "BTC-USDT"

# -- sizing: one slot, 15% of ledger equity, 5x leverage --------------------
LAB_ALLOC = 0.15
LAB_LEV = 20.0   # owner directive: 10x floor / 20x target; both triggers'
                 # stops (1.69% fixed, 1.5x ATR) sit inside 20x liq distance

# -- trigger thresholds (see module docstring for the exact geometry) ------
# forensic_short = the ROUND-41 SURVIVOR definition exactly (step41_shorts.py
# family 4, f>1.5bp/1h: train +$24.57/t x55, val +$193.25/t x8; sealed test
# 0 trades in the 2025-26 grind = dormant crash-catcher, cannot bleed while
# asleep). POP-based: short euphoric funding + a 4h upward pop + live ATR.
FORENSIC_FUND_MIN_BPS = 1.5
FORENSIC_POP_PCT = 1.5         # close vs close 4h ago, an upward pop
FORENSIC_ATR_MIN_PCT = 1.2     # ATR(14,1h) as % of price — market must be live
FORENSIC_STOP_PCT = 1.69       # measured geometry, % above entry
FORENSIC_TARGET_PCT = 5.07     # measured geometry, % below entry
CASCADE_FUND_MIN_BPS = 2.0
CASCADE_STOP_ATR_MULT = 1.5
CASCADE_TARGET_ATR_MULT = 4.5
FORENSIC_MAX_HOLD_H = 48
CASCADE_MAX_HOLD_H = 24

BREAKDOWN_N = 20                # bars for the prior-low channel


def _champion_state(live_feed, symbol=SYMBOL) -> int:
    """Identical call to tactical.py's _champion_state: the 4h vol-gated MA,
    long/flat only (allow_short=False), so this only ever reads 0 or 1."""
    candles = live_feed.get_candles(symbol, "4h", 300)
    sig = vol_gated_ma(candles, fast=20, slow=100, min_atr_pct=1.5)
    v = sig.iloc[-1]
    return int(v) if v == v else 0


def _breakdown_signals(live_feed, symbol=SYMBOL):
    """From the last CLOSED 1h bar: close, the prior N-bar low (shift(1) so
    the bar that breaks the level is never inside the window defining it),
    ATR(14,1h) in price units, and whether a breakdown just happened."""
    candles = live_feed.get_candles(symbol, "1h", BREAKDOWN_N + 20)
    prior_low = candles["low"].rolling(BREAKDOWN_N).min().shift(1)
    last_close = float(candles["close"].iloc[-1])
    lvl_raw = prior_low.iloc[-1]
    lvl = float(lvl_raw) if lvl_raw == lvl_raw else None
    atr14 = float(_atr(candles, 14).iloc[-1])
    breakdown = bool(lvl is not None and last_close < lvl)
    # forensic's pop condition: close vs close 4 bars (hours) ago, in %
    pop_pct = (last_close / float(candles["close"].iloc[-5]) - 1) * 100 \
        if len(candles) >= 5 else 0.0
    return last_close, lvl, atr14, breakdown, pop_pct


def _cleanup_orders(private, symbol, t):
    """Cancel whichever of our bracket orders is still resting (mirrors
    tactical.py's helper of the same name, symbol-parameterized here since
    tactical.py hardcodes BTC-USDT in its own copy)."""
    try:
        if t.get("tp_order_id"):
            private.cancel_order(symbol, t["tp_order_id"])
    except Exception:
        pass
    try:
        if t.get("tpsl_id"):
            private.cancel_tpsl(symbol, t["tpsl_id"])
    except Exception:
        pass


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    """Close the lab's short on its own ledger line. Short PnL: profit when
    price FALLS (entry - exit), the mirror image of tactical.py's long math."""
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = (t["entry_price"] - exit_price) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["shorts_lab"]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    trigger = t.get("trigger", "shorts_lab")
    print(f"  [LAB ] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "lab_exit", "reason": reason, "trigger": trigger,
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq})
    record_trade_outcome(state, trigger, realized)
    write_lesson(state, trigger, realized, t["entry_price"], exit_price,
                 reason, t.get("ctx"))
    notify(f"🩳 shorts lab {reason}: ${realized:+,.2f}",
           f"{trigger} short — ledger ${eq:,.2f} (demo)")
    return realized


def run_lab(private: BlofinDemoPrivate, live_feed, demo_feed, state: dict,
           dry: bool = False):
    """One hourly (or shock-cycle) decision for the shorts lab. Returns a
    small summary dict describing what happened, mainly for the smoke test."""
    lab = state.setdefault("shorts_lab", {"open_trade": None})
    t = lab.get("open_trade")

    core = state.get("open_trade")
    tact = state.get("tactical", {}).get("open_trade")
    core_ct = core["contracts"] if core else 0.0
    tact_ct = tact["contracts"] if tact else 0.0
    lab_ct = t["contracts"] if t else 0.0
    net = private.net_position_contracts(SYMBOL)
    expected = core_ct + tact_ct - lab_ct   # lab's short subtracts from net
    tag = " DRY" if dry else ""
    print(f"  [LAB{tag}] reconcile: net={net:+.2f} expected={expected:+.2f} "
          f"(core {core_ct:.1f} + tact {tact_ct:.1f} - lab {lab_ct:.1f})")

    # -- reconcile: our short is gone (or shrank) — a bracket fired --------
    if t and net > expected + LOT / 2:
        exit_price, fee_bps = t["entry_price"], 6.0
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        reason = "TP hit" if exit_price <= t["entry_price"] else "SL hit"
        fee_bps = 2.0 if reason == "TP hit" else 6.0
        print(f"  [LAB{tag}] our short is gone/reduced -> {reason} "
              f"@ {exit_price:,.1f}")
        if dry:
            print("  [LAB DRY] would cancel remaining bracket orders and "
                  "book this exit — no state/order changes made")
            return {"action": "would_exit", "reason": reason,
                    "exit_price": exit_price}
        _cleanup_orders(private, SYMBOL, t)
        _book_exit(state, t, exit_price, fee_bps, reason)
        t = None

    # -- reconcile: exchange shows a short we have no record of — adopt it -
    elif not t and net < core_ct + tact_ct - LOT / 2:
        adopted_ct = round(core_ct + tact_ct - net, 1)
        print(f"  [LAB{tag}] UNEXPECTED net short {adopted_ct:.1f} ct on "
              f"the exchange — adopting")
        if dry:
            print("  [LAB DRY] would adopt this position into state — no "
                  "state changes made")
            return {"action": "would_adopt", "contracts": adopted_ct}
        px = float(live_feed.get_candles(SYMBOL, "1h", 2)["close"].iloc[-1])
        lab["open_trade"] = t = {
            "trigger": "adopted", "ctx": {},
            "direction": -1, "contracts": adopted_ct, "entry_price": px,
            "entry_fee_bps": 6.0, "entry_time": now_utc(),
            "tp_price": None, "sl_price": None,
            "tp_order_id": None, "tpsl_id": None,
            "max_hold_h": FORENSIC_MAX_HOLD_H,
        }
        save_state(state)
        log_event({"action": "lab_adopt", "contracts": adopted_ct,
                   "price": px})
        notify("⚠️ shorts lab adopted unexpected short",
              f"{adopted_ct:.1f} ct @ {px:,.0f} — no record of how it got "
              f"there, now tracked (demo)")

    # -- time exit -----------------------------------------------------------
    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", FORENSIC_MAX_HOLD_H)
        if held_h >= max_hold_h:
            print(f"  [LAB{tag}] {held_h:.0f}h >= {max_hold_h:.0f}h max "
                  f"hold -> closing")
            if dry:
                print(f"  [LAB DRY] would market-cover {t['contracts']:.1f} "
                      f"ct now — no orders placed")
                return {"action": "would_time_exit", "contracts": t["contracts"]}
            _cleanup_orders(private, SYMBOL, t)
            quote = demo_feed.get_ticker(SYMBOL)
            fill, was_maker = execute_maker_or_chase(
                private, demo_feed, SYMBOL, "buy", t["contracts"],
                quote.ask, reduce_only=True)
            _book_exit(state, t, fill, 2.0 if was_maker else 6.0,
                      f"{max_hold_h:.0f}h time")
            return {"action": "time_exit", "fill": fill}
        print(f"  [LAB{tag}] holding {t['contracts']:.1f} ct short from "
              f"{t['entry_price']:,.1f} trig={t.get('trigger')} "
              f"({held_h:.0f}h/{max_hold_h:.0f}h), bracket working")
        return {"action": "holding", "trigger": t.get("trigger"),
                "held_h": round(held_h, 1)}

    # -- entry -----------------------------------------------------------------
    champ = _champion_state(live_feed, SYMBOL)
    net = private.net_position_contracts(SYMBOL)   # re-read post-reconcile
    last_close, lvl, atr14, breakdown, pop_pct = _breakdown_signals(
        live_feed, SYMBOL)
    fb = current_funding_bps(live_feed, SYMBOL)
    atr_pct = (atr14 / last_close * 100) if last_close else 0.0
    lvl_str = f"{lvl:,.1f}" if lvl is not None else "n/a"
    fb_str = f"{fb:+.2f}" if fb is not None else "n/a"
    print(f"  [LAB{tag}] champ4h={champ:+d} net={net:+.2f} close={last_close:,.1f} "
          f"20lo={lvl_str} breakdown={'Y' if breakdown else 'n'} "
          f"pop4h={pop_pct:+.2f}% funding={fb_str}bp atr14(1h)={atr_pct:.2f}%")

    if champ != 0:
        print("  [LAB ] STAND DOWN — 4h champion is LONG, the lab never "
              "fights the ride on the same netted account")
        return {"action": "stand_down", "reason": "champ_long", "champ": champ}
    if net > LOT / 2:
        print(f"  [LAB ] STAND DOWN — exchange shows net long {net:+.2f} ct")
        return {"action": "stand_down", "reason": "net_long", "net": net}
    if lvl is None or fb is None:
        print("  [LAB ] no trigger (warmup or funding unreadable)")
        return {"action": "no_trigger", "reason": "insufficient_data"}

    benched = state.get("benched_triggers", [])
    # forensic: the round-41 survivor exactly — euphoric funding + 4h pop up
    # + live volatility. It shorts the euphoria, not the breakdown.
    forensic_ready = (fb >= FORENSIC_FUND_MIN_BPS
                      and pop_pct > FORENSIC_POP_PCT
                      and atr_pct > FORENSIC_ATR_MIN_PCT)
    cascade_ready = breakdown and fb > CASCADE_FUND_MIN_BPS

    trigger = None
    if forensic_ready and "forensic_short" not in benched:
        trigger = "forensic_short"
    elif cascade_ready and "cascade_short" not in benched:
        trigger = "cascade_short"
    elif forensic_ready or cascade_ready:
        which = [n for n, r in (("forensic_short", forensic_ready),
                                ("cascade_short", cascade_ready)) if r]
        print(f"  [LAB ] {'/'.join(which)} fired but BENCHED by live "
              f"memory — skipping")
        log_event({"action": "memory_skip", "trigger": "/".join(which)})
        return {"action": "benched", "triggers": which}

    if trigger is None:
        print("  [LAB ] no trigger")
        return {"action": "no_trigger"}

    notional = state["virtual_equity"] * LAB_ALLOC * LAB_LEV
    contracts = max(LOT, round(notional / last_close / CONTRACT_BTC / LOT) * LOT)

    if trigger == "forensic_short":
        max_hold_h = FORENSIC_MAX_HOLD_H
    else:
        max_hold_h = CASCADE_MAX_HOLD_H

    if dry:
        # stop/target off last_close as an entry-price stand-in — the real
        # entry may differ slightly once execute_maker_or_chase fills.
        if trigger == "forensic_short":
            stop_est = round(last_close * (1 + FORENSIC_STOP_PCT / 100), 1)
            target_est = round(last_close * (1 - FORENSIC_TARGET_PCT / 100), 1)
        else:
            stop_est = round(last_close + CASCADE_STOP_ATR_MULT * atr14, 1)
            target_est = round(last_close - CASCADE_TARGET_ATR_MULT * atr14, 1)
        print(f"  [LAB DRY] {trigger} WOULD FIRE — sell {contracts:.1f} ct "
              f"(~${notional:,.0f} notional at {LAB_LEV:.0f}x, {LAB_ALLOC*100:.0f}% "
              f"alloc) @ ~{last_close:,.1f} | est TP {target_est:,.1f} "
              f"est SL {stop_est:,.1f} | max hold {max_hold_h}h — NO ORDER PLACED")
        return {"action": "would_enter", "trigger": trigger,
                "contracts": contracts, "entry_ref": last_close,
                "est_tp": target_est, "est_sl": stop_est,
                "max_hold_h": max_hold_h, "funding_bps": fb,
                "atr_pct": round(atr_pct, 2)}

    print(f"  [LAB ] {trigger} SIGNAL — selling {contracts:.1f} ct "
          f"(~${notional:,.0f} notional at {LAB_LEV:.0f}x sleeve leverage)")
    entry, was_maker = execute_maker_or_chase(
        private, demo_feed, SYMBOL, "sell", contracts, last_close)

    if trigger == "forensic_short":
        stop = round(entry * (1 + FORENSIC_STOP_PCT / 100), 1)
        target = round(entry * (1 - FORENSIC_TARGET_PCT / 100), 1)
    else:
        stop = round(entry + CASCADE_STOP_ATR_MULT * atr14, 1)
        target = round(entry - CASCADE_TARGET_ATR_MULT * atr14, 1)

    tp_oid = tpsl_id = None
    try:
        tp_oid = private.post_only_order(SYMBOL, "buy", contracts, target,
                                         reduce_only=True)
    except Exception as e:
        print(f"  [LAB ] TP limit failed: {str(e)[:80]}")
    try:
        tpsl_id = private.place_tpsl(SYMBOL, "buy", contracts, None, stop)
    except Exception as e:
        print(f"  [LAB ] SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ shorts lab SL failed",
              "position unprotected — check BloFin (demo)")

    lab["open_trade"] = {
        "trigger": trigger,
        "ctx": {"atr_pct": round(atr_pct, 2), "funding_bps": fb,
                "price": entry, "broken_level": lvl,
                "reason": f"{trigger} breakdown below {BREAKDOWN_N}-bar low "
                          f"{lvl:,.1f} at funding {fb:+.2f}bp",
                "news": recent_news_headline()},
        "direction": -1, "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0,
        "entry_time": now_utc(), "tp_price": target, "sl_price": stop,
        "tp_order_id": tp_oid, "tpsl_id": tpsl_id,
        "max_hold_h": max_hold_h,
    }
    save_state(state)
    log_event({"action": "lab_enter", "trigger": trigger,
               "fill_price": entry, "contracts": contracts, "tp": target,
               "sl": stop, "maker": was_maker, "funding_bps": fb,
               "atr_pct": round(atr_pct, 2)})
    notify(f"🩳 SHORTS LAB entry ({trigger}, demo)",
          f"sell {contracts:.1f} ct @{entry:,.0f} | TP {target:,.0f} "
          f"SL {stop:,.0f} | {max_hold_h}h max hold (demo)")
    return {"action": "entered", "trigger": trigger, "entry": entry,
           "contracts": contracts, "tp": target, "sl": stop}
