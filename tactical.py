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
from step5_paper_trade import (CONTRACT_BTC, LOT, MAX_ENTRY_FUNDING_BPS,
                               current_funding_bps, execute_maker_or_chase,
                               log_event, notify, now_utc, save_state)
from strategy import rsi, vol_gated_ma

TACT_ALLOC = 0.2
TACT_LEV = 10.0
STOP_PCT = 1.5
TARGET_PCT = 4.5
MAX_HOLD_H = 48


def _champion_state(live_feed, symbol) -> int:
    candles = live_feed.get_candles(symbol, "4h", 300)
    sig = vol_gated_ma(candles, fast=20, slow=100, min_atr_pct=1.5)
    v = sig.iloc[-1]
    return int(v) if v == v else 0


def _rsi3_1h(live_feed, symbol) -> float:
    candles = live_feed.get_candles(symbol, "1h", 50)
    r = rsi(candles["close"], 3).iloc[-1]
    return float(r) if r == r else 50.0


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
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq})
    notify(f"⚡ tactical {reason}: ${realized:+,.2f}",
           f"ledger ${eq:,.2f} / ${state.get('goal', 2000):,.0f} (demo)")
    return realized


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


def tactical_cycle(private: BlofinDemoPrivate, live_feed, demo_feed,
                   symbol: str, state: dict):
    """One hourly decision for the tactical book."""
    tact = state.setdefault("tactical", {"open_trade": None})
    t = tact.get("open_trade")

    core = state.get("open_trade")
    core_ct = core["contracts"] if core else 0.0
    tact_ct = t["contracts"] if t else 0.0
    net = private.net_position_contracts(symbol)

    # -- reconcile: did a bracket fire between cycles? --------------------
    if t and net < core_ct + tact_ct - LOT / 2:
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
            fill, was_maker = execute_maker_or_chase(
                private, demo_feed, symbol, "sell", t["contracts"],
                quote.bid, reduce_only=True)
            _book_exit(state, t, fill, 2.0 if was_maker else 6.0, "48h time")
            t = None
        else:
            print(f"  [TACT] holding {t['contracts']:.1f} ct from "
                  f"{t['entry_price']:,.1f} ({held_h:.0f}h), bracket working")
            return

    # -- entry -------------------------------------------------------------
    champ = _champion_state(live_feed, symbol)
    r3 = _rsi3_1h(live_feed, symbol)
    print(f"  [TACT] champ4h={champ:+d} rsi3(1h)={r3:.1f}")
    if champ != 1 or r3 >= 15:
        return
    fb = current_funding_bps(live_feed, symbol)
    if fb is not None and fb > MAX_ENTRY_FUNDING_BPS:
        print(f"  [TACT] funding veto ({fb:+.2f} bps)")
        log_event({"action": "tact_veto", "funding_bps": fb})
        return

    candles = live_feed.get_candles(symbol, "1h", 3)
    last_close = float(candles["close"].iloc[-1])
    notional = state["virtual_equity"] * TACT_ALLOC * TACT_LEV
    contracts = max(LOT, round(notional / last_close / CONTRACT_BTC / LOT) * LOT)

    print(f"  [TACT] DIP SIGNAL — entering {contracts:.1f} ct "
          f"(~${notional:,.0f} notional at {TACT_LEV:.0f}x sleeve leverage)")
    entry, was_maker = execute_maker_or_chase(
        private, demo_feed, symbol, "buy", contracts, last_close)

    tp = round(entry * (1 + TARGET_PCT / 100), 1)
    sl = round(entry * (1 - STOP_PCT / 100), 1)
    tp_oid = tpsl_id = None
    try:
        tp_oid = private.post_only_order(symbol, "sell", contracts, tp,
                                         reduce_only=True)
    except Exception as e:
        print(f"  [TACT] TP limit failed: {str(e)[:80]}")
    try:
        tpsl_id = private.place_tpsl(symbol, "sell", contracts, None, sl)
    except Exception as e:
        print(f"  [TACT] SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ tactical SL failed", "position unprotected — check BloFin")

    tact["open_trade"] = {
        "direction": 1, "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0,
        "entry_time": now_utc(), "tp_price": tp, "sl_price": sl,
        "tp_order_id": tp_oid, "tpsl_id": tpsl_id,
    }
    save_state(state)
    log_event({"action": "tact_enter", "fill_price": entry,
               "contracts": contracts, "tp": tp, "sl": sl,
               "maker": was_maker})
    notify("⚡ TACTICAL entry (10x sleeve)",
           f"buy {contracts:.1f} ct @{entry:,.0f} | TP {tp:,.0f} "
           f"SL {sl:,.0f} (demo)")
