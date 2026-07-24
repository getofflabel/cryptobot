"""
tactical.py — the TACTICAL SLEEVE executor: MTF Dip at 10x, live.

The round-15 gauntlet survivor, mirrored exactly:
  FILTER : the 4h champion state (trend + vol gate) must be LONG
  TRIGGER: last closed 1h bar's RSI(3) < 15 — a sharp washout
  ENTRY  : post-only limit at the 1h close (chase if it runs)
  BRACKET: reduce-only LIMIT at +4.5% (true maker take-profit, as
           backtested) + stop-loss trigger at -1.5%
  TIME   : hard exit after 48 hours, whatever else happens
  SIZE   : 20% of the ledger x 10 leverage; with the 1.5% stop that is
           ~3% of total equity risked per shot — high-leverage discipline,
           not high-leverage bravado.

BOOKKEEPING RULES (two books, one exchange position, net mode):
  The exchange nets core + tactical into one position. Attribution lives
  in the ledger state: state["open_trade"] is the core's, and
  state["tactical"]["open_trade"] is ours. Every cycle starts by
  RECONCILING: if the exchange holds less than the two books say, a
  bracket fired between cycles — find the fill, book it, clean up the
  leftover orders. Only then decide anything new.

Known live-vs-backtest approximation, on the record: the backtest's
champion filter used historical funding; live we apply the CURRENT
funding veto at entry instead (the cap rarely binds in this regime).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import config
from blofin_private import BlofinDemoPrivate
from book_ledger import attributed_position
from step5_paper_trade import (CONTRACT_BTC, LOT, MAX_ENTRY_FUNDING_BPS,
                               current_funding_bps, execute_maker_or_chase, execute_market_clips,
                               log_event, notify, now_utc,
                               record_trade_outcome, save_state)
from strategy import rsi, vol_gated_ma

# THE STRIKE FORCE — multi-asset (round 21). Tradeable universe per
# Wallace: BTC, ETH, SOL. Same machine, different volatility levels, so
# each slot carries its own contract math, geometry, and leverage.
#   BTC slot: three validated triggers (panic-dip 10x, flag 6x, flag-2h 3x)
#   ETH slot: THE AMPLIFIER (gauntlet survivor #5) — fires on BTC's
#             panic-dip signal, trades ETH at ETH's vol-scaled geometry.
#             Lev 8x = risk parity with the BTC dip (8 x 1.81% ~ 10 x 1.5%).
#   SOL slot: BUILT BUT DORMANT — missed qualification by $0.55/trade;
#             activates only if a quarterly re-audit passes it.
# Allocation split so a simultaneous BTC+ETH fire (same signal by design)
# stays inside the agreed total aggression:
SLOTS = {
    "BTC-USDT": {"state_key": "tactical", "alloc": 0.25,
                 "contract": 0.001, "lot": 0.1},
    "ETH-USDT": {"state_key": "tactical_eth", "alloc": 0.15,
                 "contract": 0.01, "lot": 0.1,
                 "stop": 1.81, "target": 5.43, "lev": 20.0,
                 "trigger": "amplifier"},
}
TACT_ALLOC = 0.25          # BTC slot share (ETH slot carries its own)
STOP_PCT = 1.5
TARGET_PCT = 4.5
MAX_HOLD_H = 48


def _champion_state(live_feed, symbol) -> int:
    candles = live_feed.get_candles(symbol, "4h", 300)
    sig = vol_gated_ma(candles, fast=20, slow=100, min_atr_pct=1.5)
    v = sig.iloc[-1]
    return int(v) if v == v else 0


def _signals_1h(live_feed, symbol):
    """The tactical book's two validated triggers, from the last closed 1h bar:
    PANIC DIP  — RSI(3) < 15 (round 15 survivor)
    FLAG TOUCH — bar dips to the 80h trend line and closes back above it
                 (round 18 survivor: train +$14, val +$64, test +$52/trade)"""
    candles = live_feed.get_candles(symbol, "1h", 120)
    r = rsi(candles["close"], 3).iloc[-1]
    r = float(r) if r == r else 50.0
    sma80 = candles["close"].rolling(80).mean().iloc[-1]
    last = candles.iloc[-1]
    flag = bool(sma80 == sma80 and last["low"] <= sma80
                and last["close"] > sma80)
    # third validated trigger (nightly researcher, step22): flag-touch on
    # 2h bars — checked only when a 2h bar just closed (even UTC hours)
    flag2h = False
    from datetime import datetime, timezone
    if datetime.now(timezone.utc).hour % 2 == 0:
        c2 = live_feed.get_candles(symbol, "2h", 120)
        s40 = c2["close"].rolling(40).mean().iloc[-1]   # ~ the 80h line
        l2 = c2.iloc[-1]
        flag2h = bool(s40 == s40 and l2["low"] <= s40 and l2["close"] > s40)
    return r, flag, flag2h


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["tactical"]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    print(f"  [TACT] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "tact_exit", "reason": reason,
               "trigger": t.get("trigger", "?"), "exit_price": exit_price,
               "realized_pnl": realized, "virtual_equity": eq})
    record_trade_outcome(state, t.get("trigger", "tactical"), realized)
    from step5_paper_trade import write_lesson
    write_lesson(state, t.get("trigger", "tactical"), realized,
                 t["entry_price"], exit_price, reason, t.get("ctx"))
    notify(f"⚡ tactical {reason}: ${realized:+,.2f}",
           f"ledger ${eq:,.2f} / ${state.get('goal', 2000):,.0f} (demo)")
    return realized


def _bracket_present(private, symbol, t) -> bool:
    """True if a live TP/SL bracket exists for this position. When we have
    OUR OWN tpsl_id on record, require THAT specific bracket to be present
    — not just any bracket resting on the symbol — so we never mistake
    another book's bracket for ours (or ours for gone because a *different*
    book's bracket happens to still be there)."""
    brackets = private.pending_tpsl(symbol)
    if not brackets:
        return False
    our_id = t.get("tpsl_id")
    if our_id:
        return any(str(b.get("tpslId")) == str(our_id) for b in brackets)
    return True   # no id on record (legacy state) — any bracket is enough


def _ensure_bracket(private, symbol, state, t):
    """Self-healing protection for the LONG books (close side = sell). Every
    cycle, verify the TP/SL bracket is live on the exchange; re-place it if
    missing so a leveraged position never sits naked (the 2026-07-23 bug).

    HARDENED (2026-07-23, later that day): the sandbox's BloFin reads are
    flaky — an empty/HTML response briefly made this function re-arm a stop
    that actually existed. Now: read pending_tpsl TWICE, 4 seconds apart,
    and only re-arm if BOTH reads come back empty AND a fresh net-position
    read confirms the position we'd be protecting still exists. Any
    exception during the READS means "don't know" — do nothing, never act
    on bad data. A failure during the actual re-arm PLACEMENT is still
    reported loudly (that one is a real, actionable failure)."""
    if not t or not t.get("sl_price"):
        return
    try:
        if _bracket_present(private, symbol, t):
            return                                   # a bracket exists — good
        time.sleep(4)
        if _bracket_present(private, symbol, t):
            return                     # 1st read was a flaky empty response
        net = private.net_position_contracts(symbol)
        if abs(net) < LOT / 2:
            return           # position itself is gone — nothing to protect;
                              # reconcile handles the exit next cycle
    except Exception as e:
        # a read failed or returned garbage (HTML edge-throttle, etc.) —
        # NEVER act on bad data. Skip this cycle, try again next time.
        print(f"  [TACT] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    # Both reads independently confirmed no bracket, AND the position is
    # still genuinely open. Re-arm once.
    try:
        tpsl_id = private.place_tpsl(symbol, "sell", t["contracts"],
                                     t.get("tp_price"), t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [TACT] ⚠️ bracket was MISSING — re-armed SL {t['sl_price']:,.1f}")
        notify("🛡️ Stop re-armed (demo)",
               f"A long's TP/SL had vanished — re-placed. SL ${t['sl_price']:,.0f}.")
    except Exception as e:
        print(f"  [TACT] bracket re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ tactical UNPROTECTED (demo)",
               "bracket missing and re-arm failed — check BloFin now")


def _cleanup_orders(private, symbol, t):
    """Cancel whichever of our bracket orders is still resting."""
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


def run_strikes(private: BlofinDemoPrivate, live_feed, demo_feed, state: dict):
    """Round 21 entrypoint: evaluate every strike slot, BTC first.
    The BTC panic-dip condition is computed ONCE and shared with the
    amplifier slot so both books read the same signal."""
    champ = _champion_state(live_feed, "BTC-USDT")
    r3, flag, flag2h = _signals_1h(live_feed, "BTC-USDT")
    btc_dip = champ == 1 and r3 < 15
    tactical_cycle(private, live_feed, demo_feed, "BTC-USDT", state,
                   precomputed=(champ, r3, flag, flag2h))
    amplifier_cycle(private, live_feed, demo_feed, state, btc_dip)


def tactical_cycle(private: BlofinDemoPrivate, live_feed, demo_feed,
                   symbol: str, state: dict, precomputed=None):
    """One hourly decision for the tactical book."""
    tact = state.setdefault("tactical", {"open_trade": None})
    t = tact.get("open_trade")

    # Book-aware attribution (2026-07-23 fix, see book_ledger.py): net minus
    # every OTHER book's own recorded position (ride, shorts lab,
    # apprentice) leaves ONLY the tactical slot's actual slice of the
    # exchange net. Comparing hand-summed core+tact contracts against raw
    # net (the old way) silently broke the instant the shorts lab held a
    # position too — its short would shrink "net" and could look like this
    # book's own bracket had fired when nothing had.
    net = private.net_position_contracts(symbol)
    attributed_tact = attributed_position(net, state, "tact")

    # -- reconcile: did a bracket fire between cycles? --------------------
    if t and attributed_tact < t["contracts"] - LOT / 2:
        # our position is gone (or partially) — find what filled
        exit_price, fee_bps = t["entry_price"], 6.0
        try:
            fills = private.fills(symbol)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        # infer which side of the bracket by where price landed
        reason = ("TP hit" if exit_price >= t["entry_price"] else "SL hit")
        fee_bps = 2.0 if reason == "TP hit" else 6.0
        _cleanup_orders(private, symbol, t)
        _book_exit(state, t, exit_price, fee_bps, reason)
        t = None

    # -- time exit ---------------------------------------------------------
    if t:
        entry_dt = datetime.strptime(t["entry_time"],
                                     "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if held_h >= MAX_HOLD_H:
            _cleanup_orders(private, symbol, t)
            quote = demo_feed.get_ticker(symbol)
            fill, was_maker = execute_market_clips(
                private, demo_feed, symbol, "sell", t["contracts"],
                quote.bid, reduce_only=True)
            _book_exit(state, t, fill, 2.0 if was_maker else 6.0, "48h time")
            t = None
        else:
            _ensure_bracket(private, symbol, state, t)   # self-heal the stop
            print(f"  [TACT] holding {t['contracts']:.1f} ct from "
                  f"{t['entry_price']:,.1f} ({held_h:.0f}h), bracket verified")
            return

    # -- entry -------------------------------------------------------------
    if precomputed is not None:
        champ, r3, flag, flag2h = precomputed
    else:
        champ = _champion_state(live_feed, symbol)
        r3, flag, flag2h = _signals_1h(live_feed, symbol)
    trigger = ("panic-dip" if r3 < 15 else
               "flag-touch" if flag else
               "flag-2h" if flag2h else None)
    print(f"  [TACT] champ4h={champ:+d} rsi3(1h)={r3:.1f} "
          f"flag={'Y' if flag else 'n'} flag2h={'Y' if flag2h else 'n'} "
          f"-> {trigger or 'no trigger'}")
    if champ != 1 or trigger is None:
        return
    if trigger in state.get("benched_triggers", []):
        print(f"  [TACT] {trigger} is BENCHED by live memory — skipping")
        log_event({"action": "memory_skip", "trigger": trigger})
        return
    fb = current_funding_bps(live_feed, symbol)
    if fb is not None and fb > MAX_ENTRY_FUNDING_BPS:
        print(f"  [TACT] funding veto ({fb:+.2f} bps)")
        log_event({"action": "tact_veto", "funding_bps": fb})
        return

    candles = live_feed.get_candles(symbol, "1h", 3)
    last_close = float(candles["close"].iloc[-1])
    # situational leverage (Kelly study 2026-07-23): each trigger sized to
    # its own measured optimum ratio — more size where the math earns it,
    # less where it doesn't. Flat 10x was over-levering the flag triggers.
    # OWNER DIRECTIVE (2026-07-23): minimum 10x, target 20x. Every trigger
    # runs at the max its stop geometry allows under BloFin's ~4.5%
    # liquidation distance at 20x — all three stops (1.5/1.5/2.2%) fit.
    trig_lev = {"panic-dip": 20.0, "flag-touch": 20.0, "flag-2h": 20.0}[trigger]
    notional = state["virtual_equity"] * TACT_ALLOC * trig_lev
    contracts = max(LOT, round(notional / last_close / CONTRACT_BTC / LOT) * LOT)

    print(f"  [TACT] {trigger} SIGNAL — entering {contracts:.1f} ct "
          f"(~${notional:,.0f} notional at {trig_lev:.0f}x sleeve leverage)")
    private.ensure_leverage(symbol, trig_lev, "cross")   # per-trade leverage
    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, symbol, "buy", contracts, last_close)
    except Exception as e:
        print(f"  [TACT] ENTRY FAILED: {str(e)[:100]}")
        notify("⚠️ tactical ENTRY FAILED (demo)",
               f"{trigger} order rejected: {str(e)[:80]}. No position — check BloFin.")
        return {"action": "entry_failed", "trigger": trigger}

    stop_pct = 2.2 if trigger == "flag-2h" else STOP_PCT
    tgt_pct = 6.6 if trigger == "flag-2h" else TARGET_PCT
    tp = round(entry * (1 + tgt_pct / 100), 1)
    sl = round(entry * (1 - stop_pct / 100), 1)
    tp_oid = None
    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(symbol, "sell", contracts, tp, sl)
    except Exception as e:
        print(f"  [TACT] TP/SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ tactical bracket failed (demo)",
               "position opened but TP/SL not set — check BloFin now")

    from strategy import atr as _atr
    _c = live_feed.get_candles(symbol, "4h", 20)
    _atrnow = float((_atr(_c, 14) / _c["close"] * 100).iloc[-1])
    from step5_paper_trade import recent_news_headline
    tact["open_trade"] = {
        "trigger": trigger, "ctx": {"atr_pct": round(_atrnow, 2),
                                    "funding_bps": fb,
                                    "news": recent_news_headline()},
        "direction": 1, "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0,
        "entry_time": now_utc(), "tp_price": tp, "sl_price": sl,
        "tp_order_id": tp_oid, "tpsl_id": tpsl_id,
    }
    save_state(state)
    log_event({"action": "tact_enter", "trigger": trigger,
               "fill_price": entry, "contracts": contracts, "tp": tp,
               "sl": sl, "maker": was_maker})
    notify("⚡ TACTICAL entry (10x sleeve)",
           f"buy {contracts:.1f} ct @{entry:,.0f} | TP {tp:,.0f} "
           f"SL {sl:,.0f} (demo)")


def amplifier_cycle(private: BlofinDemoPrivate, live_feed, demo_feed,
                    state: dict, btc_dip: bool):
    """THE AMPLIFIER slot: BTC's panic-dip signal, traded on ETH.

    Gauntlet survivor #5 (test +$50.43/trade, 43% win). ETH's own
    reconciliation, brackets, and 48h clock — independent of the BTC slot
    except for sharing the trigger.
    """
    cfg = SLOTS["ETH-USDT"]
    sym, key = "ETH-USDT", cfg["state_key"]
    book = state.setdefault(key, {"open_trade": None})
    t = book.get("open_trade")
    net = private.net_position_contracts(sym)

    # reconcile: our ETH position is the only one on this symbol
    if t and net < t["contracts"] - cfg["lot"] / 2:
        exit_price, fee_bps = t["entry_price"], 6.0
        try:
            fills = private.fills(sym)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        reason = "TP hit" if exit_price >= t["entry_price"] else "SL hit"
        _cleanup_orders(private, sym, t)
        _book_slot_exit(state, key, cfg, t, exit_price,
                        2.0 if reason == "TP hit" else 6.0, reason)
        t = None

    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        if held_h >= MAX_HOLD_H:
            _cleanup_orders(private, sym, t)
            quote = demo_feed.get_ticker(sym)
            fill, was_maker = execute_market_clips(
                private, demo_feed, sym, "sell", t["contracts"],
                quote.bid, reduce_only=True)
            _book_slot_exit(state, key, cfg, t, fill,
                            2.0 if was_maker else 6.0, "48h time")
        else:
            print(f"  [AMP ] holding {t['contracts']:.1f} ct ETH from "
                  f"{t['entry_price']:,.2f} ({held_h:.0f}h)")
        return

    print(f"  [AMP ] BTC-dip signal: {'FIRING' if btc_dip else 'no'}")
    if not btc_dip:
        return
    if "amplifier" in state.get("benched_triggers", []):
        print("  [AMP ] BENCHED by live memory — skipping")
        return
    fb = current_funding_bps(live_feed, "BTC-USDT")
    if fb is not None and fb > MAX_ENTRY_FUNDING_BPS:
        print(f"  [AMP ] funding veto ({fb:+.2f} bps)")
        return

    c = live_feed.get_candles(sym, "1h", 3)
    last_close = float(c["close"].iloc[-1])
    notional = state["virtual_equity"] * cfg["alloc"] * cfg["lev"]
    contracts = max(cfg["lot"],
                    round(notional / last_close / cfg["contract"] / cfg["lot"])
                    * cfg["lot"])
    print(f"  [AMP ] entering {contracts:.1f} ct ETH "
          f"(~${notional:,.0f} notional at {cfg['lev']:.0f}x slot leverage)")
    private.ensure_leverage(sym, cfg["lev"], "cross")    # per-trade leverage
    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, sym, "buy", contracts, last_close)
    except Exception as e:
        print(f"  [AMP ] ENTRY FAILED: {str(e)[:100]}")
        notify("⚠️ amplifier ENTRY FAILED (demo)",
               f"ETH order rejected: {str(e)[:80]}. No position — check BloFin.")
        return {"action": "entry_failed"}
    tp = round(entry * (1 + cfg["target"] / 100), 2)
    sl = round(entry * (1 - cfg["stop"] / 100), 2)
    tp_oid = None
    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(sym, "sell", contracts, tp, sl)
    except Exception as e:
        print(f"  [AMP ] TP/SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ amplifier bracket failed (demo)",
               "ETH position opened but TP/SL not set — check BloFin")
    book["open_trade"] = {
        "direction": 1, "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0,
        "entry_time": now_utc(), "tp_price": tp, "sl_price": sl,
        "tp_order_id": tp_oid, "tpsl_id": tpsl_id,
    }
    save_state(state)
    log_event({"action": "amp_enter", "symbol": sym, "fill_price": entry,
               "contracts": contracts, "tp": tp, "sl": sl, "maker": was_maker})
    notify("🔗 AMPLIFIER entry (ETH, 8x slot)",
           f"buy {contracts:.1f} ct ETH @{entry:,.2f} | TP {tp:,.0f} "
           f"SL {sl:,.0f} (demo)")


def _book_slot_exit(state, key, cfg, t, exit_price, exit_fee_bps, reason):
    size_base = t["contracts"] * cfg["contract"]
    gross = (exit_price - t["entry_price"]) * size_base
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_base / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state[key]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    print(f"  [AMP ] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "amp_exit", "reason": reason,
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq})
    record_trade_outcome(state, "amplifier", realized)
    from step5_paper_trade import write_lesson
    write_lesson(state, "amplifier", realized, t["entry_price"],
                 exit_price, reason, t.get("ctx"))
    notify(f"🔗 amplifier {reason}: ${realized:+,.2f}",
           f"ledger ${eq:,.2f} / ${state.get('goal', 2000):,.0f} (demo)")
