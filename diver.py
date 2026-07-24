"""
diver.py — THE DIVER: the live demo-trading book for round 58's THIRD
validated edge in this program — 4h HIDDEN RSI DIVERGENCE continuation on
BTC-USDT. Structural template: newsdesk.py (bidirectional, book_ledger
attribution, hardened double-read _ensure_bracket, direction-aware
_book_exit, dry mode with zero side effects) crossed with gold_book.py's
per-bar idempotency guard (state["diver"]["last_bar_ts"], the 4h analogue
of gold_book's last_bar_date).

THE VALIDATED RULE (deployed VERBATIM — no improvements, no reimplementation)
  step58_divergence_mtf.py, FAMILY 1, config "RSI14 k8 hidden buf0.35%
  tgt3x hold48h, 4h": train $74.22/t x66, val $31.99/t x24, 7/16 neighbor
  cluster -> ONE sealed look, PASS: 24t, +$52.03/t, +12.5%, DD -15.5%
  ACROSS THE 2025-26 DROUGHT WINDOW (see RESEARCH_LOG.md ROUND 58).

  On CLOSED 4h bars: RSI(14). A bar is a confirmed swing extreme once a
  centered k=8-bar window around it is fully known (swings(), imported —
  see its docstring for the no-lookahead shift(k) trick). At each
  confirmed swing:
    LONG  (hidden bullish continuation): price prints a HIGHER swing-low
          while RSI prints a LOWER low, AND the 4h champion
          (strategy.vol_gated_ma, fast=20/slow=100, min_atr_pct=1.5 — the
          exact CHAMP_KW step43_daytrade.py already defines and every
          other book already calls) reads 1 (uptrend).
    SHORT (hidden bearish continuation, the mirror): price prints a LOWER
          swing-high while RSI prints a HIGHER high, AND the champion
          reads 0 (not-uptrend).
  This entire definition — swings, the regular/hidden classification, and
  the champion gate on the hidden flavor — lives in
  step58_divergence_mtf.divergence_events(), imported and called AS-IS
  below. Nothing about the signal logic is reimplemented in this file.

FROZEN STOP — the one number this file is not allowed to compute live
  step58's own family1 pipeline never fits one stop_pct per trade; it
  takes ONE fixed stop for the whole run: the TRAIN-only median distance
  from entry close to the qualifying swing extreme (buffer 0.35%, capped
  at STOP_CAP_SWING=4.0%), computed separately for longs and shorts via
  swing_stop_pct() (imported, not reimplemented) and combined into a
  single entry-weighted average. That is a TRAIN-SLICE constant, not a
  live indicator — so it is computed ONCE, offline, from the full cached
  train slice, and hard-coded here. Reproduction (run verbatim, 2026-07-24,
  same cache step58 itself reads — "no network calls needed"):

    from step7_deep_search import fetch_bybit_deep
    from step43_daytrade import CHAMP_KW, split_points
    from step58_divergence_mtf import divergence_events, swing_stop_pct, STOP_CAP_SWING
    from strategy import rsi, vol_gated_ma

    d = fetch_bybit_deep("4h", "BTCUSDT")                    # 13,863 bars
    n, i_tr, i_va = split_points(d)                           # i_tr=8317
                                                                # (train ends
                                                                # 2024-01-10)
    champ4h = vol_gated_ma(d, **CHAMP_KW)
    osc = rsi(d["close"], 14)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = \
        divergence_events(d, osc, 8, champ4h)

    stop_l = swing_stop_pct(d["close"], low_ext,  long_hid,  i_tr, 0.35, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], high_ext, short_hid, i_tr, 0.35, STOP_CAP_SWING)
    n_l, n_s = int(long_hid.sum()), int(short_hid.sum())       # 59, 57
                                                                # (full-series
                                                                # event counts
                                                                # — this is
                                                                # exactly how
                                                                # family1_
                                                                # divergences
                                                                # weights the
                                                                # average; the
                                                                # TRAIN-only
                                                                # discipline
                                                                # lives inside
                                                                # swing_stop_
                                                                # pct itself)
    stop_pct = (stop_l * n_l + stop_s * n_s) / (n_l + n_s)

  Result:  stop_l = 3.803802%   stop_s = 3.267654%
           entry-weighted stop_pct = 3.540350%   (repr: 3.540349843476645)
           STOP_CAP_SWING = 4.0% (not hit)
  -> STOP_PCT = 3.540350 (hard-coded below, exact derivation above).
  -> TARGET_PCT = min(3.0 * STOP_PCT, 3 * STOP_CAP_SWING) = 10.621050
     (family1's own target formula, imported STOP_CAP_SWING and all —
     the 3x cap of 12.0% is never hit either).
  -> LEVERAGE = min(20, floor(85 / STOP_PCT)) = min(20, floor(24.0075))
              = min(20, 24) = 20.
  recompute_frozen_stop_pct() below reproduces this exact computation for
  future audits — NOT called by the live path (needs the offline research
  cache, not BloFin), imported lazily so importing this module never
  requires network access.

SIZING: one slot, 15% of the shared ledger (state["virtual_equity"]),
  20x leverage (derived above from the frozen stop, not chosen by hand).

DIRECTION GATES (checked every time a signal fires, before sizing):
  LONG  requires net > -LOT/2 — never physically oppose an existing short
        net position on the shared, netted BTC-USDT exchange symbol
        (same rule newsdesk.py enforces for its own entries).
  SHORT requires net < +LOT/2 for the same reason, AND that no other
        BTC-USDT book is currently open or armed (via
        book_ledger.recorded_book_positions — the exact accounting
        daily_pick._btc_books_active already uses to keep the daily pick
        off BTC while a sniper book owns it — plus newsdesk's own
        "pending"/armed state). Longs don't get this second check because
        every long-side sniper on this account is itself long-biased;
        shorts are where multiple aggressive books stacking margin on one
        demo account gets genuinely risky (the same shape as the
        2026-07-23 incident book_ledger.py was built to prevent), so the
        Diver's short side simply stands down rather than piling onto
        whatever else already owns BTC's short side.

MAX HOLD 48h, target 3x stop, one position at a time — exactly the
validated rule's own geometry, nothing added.

IDEMPOTENCY: state["diver"]["last_bar_ts"] records the 4h bar timestamp
this book last decided on (entered, stood down, or saw no signal) — the
4h analogue of gold_book.py's last_bar_date. The daemon's full_cycle runs
HOURLY, i.e. up to 4x between two 4h bar closes; without this guard the
same confirmed-swing bar could be re-evaluated (and, if the direction gate
had since opened up, mistakenly entered) on a later hourly cycle. Marked
processed on every terminal branch (entered, stood down, no signal, entry
failed) — matching newsdesk's "judge every headline exactly once" and
gold_book's "every bar exactly once" discipline.

DRY MODE: run_diver(..., dry=True) computes and prints the full decision
every cycle would make — reconcile, signal, gate, sizing, stop/target —
but places NO orders and makes NO state/log/notify side effects. Used by
step61_diver_smoke.py against REAL BloFin candles.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone

import pandas as pd

from blofin_private import BlofinDemoPrivate
from book_ledger import attributed_position, recorded_book_positions, unexplained_position
from step43_daytrade import CHAMP_KW
from step58_divergence_mtf import STOP_CAP_SWING, divergence_events, swings
from step5_paper_trade import (CONTRACT_BTC, LOT, execute_market_clips,
                               log_event, notify, now_utc,
                               record_trade_outcome, recent_news_headline,
                               save_state, write_lesson)
from strategy import rsi, vol_gated_ma

SYMBOL = "BTC-USDT"
TIMEFRAME = "4h"

# -- the validated rule's exact config (step58 family1, "RSI14 k8 hidden
#    buf0.35% tgt3x hold48h, 4h" — see module docstring for the sealed
#    numbers) --------------------------------------------------------------
SWING_K = 8
RSI_N = 14
BUFFER_PCT = 0.35        # documentary only below build time (see the frozen
                         # STOP_PCT derivation); the live path never
                         # recomputes a stop from a buffer at runtime
TARGET_MULT = 3.0
MAX_HOLD_H = 48
CANDLE_BARS = 1000       # ~166 days of 4h bars — ample margin to find each
                         # signal's PREVIOUS same-type confirmed swing;
                         # BloFin's 4h cap is 1440 bars/request (see
                         # exchange.py BlofinExchange.MAX_CANDLES_PER_REQUEST)

# -- FROZEN, train-derived (see module docstring for the exact repro) -----
STOP_PCT = 3.540350       # entry-weighted long/short average, buffer 0.35%,
                          # cap STOP_CAP_SWING, TRAIN slice only — frozen at
                          # build time 2026-07-24, never recomputed live
TARGET_PCT = min(TARGET_MULT * STOP_PCT, 3 * STOP_CAP_SWING)   # = 10.621050
LEVERAGE = min(20, math.floor(85 / STOP_PCT))                  # = 20

DIVER_ALLOC = 0.15        # 15% of the shared ledger, state["virtual_equity"]
DIVER_LEV = float(LEVERAGE)


def recompute_frozen_stop_pct():
    """OFFLINE / AUDIT ONLY — reproduces the STOP_PCT derivation in the
    module docstring exactly. NEVER called by the live path (needs
    step7_deep_search's cached research data, not a BloFin connection); all
    its imports are local so importing diver.py never touches the network.
    Run by hand (`python3 -c "import diver; print(diver.recompute_frozen_stop_pct())"`)
    to re-verify STOP_PCT/TARGET_PCT/LEVERAGE above still match."""
    from step7_deep_search import fetch_bybit_deep
    from step43_daytrade import split_points
    from step58_divergence_mtf import swing_stop_pct

    d = fetch_bybit_deep(TIMEFRAME, "BTCUSDT")
    n, i_tr, i_va = split_points(d)
    champ4h = vol_gated_ma(d, **CHAMP_KW)
    osc = rsi(d["close"], RSI_N)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = \
        divergence_events(d, osc, SWING_K, champ4h)

    stop_l = swing_stop_pct(d["close"], low_ext, long_hid, i_tr,
                            BUFFER_PCT, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], high_ext, short_hid, i_tr,
                            BUFFER_PCT, STOP_CAP_SWING)
    n_l, n_s = int(long_hid.sum()), int(short_hid.sum())
    stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)
               if (n_l + n_s) else STOP_CAP_SWING)
    return {"stop_l": stop_l, "stop_s": stop_s, "n_l": n_l, "n_s": n_s,
           "stop_pct": stop_pct, "matches_frozen": abs(stop_pct - STOP_PCT) < 1e-4}


def _fmt_utc(ts) -> str:
    return f"{pd.Timestamp(ts):%Y-%m-%d %H:%M} UTC"


# ===========================================================================
# signal
# ===========================================================================

def _load_4h(live_feed) -> pd.DataFrame:
    """CANDLE_BARS 4h bars from the repo's own BloFin adapter. get_candles
    already discards the still-forming bar via BloFin's own confirmed flag
    (see exchange.py) — "only ever act on a CLOSED bar" is enforced by the
    adapter, not by anything here, same guarantee gold_book.py relies on."""
    d = live_feed.get_candles(SYMBOL, TIMEFRAME, CANDLE_BARS)
    return d.sort_values("timestamp").reset_index(drop=True)


def _decision(d: pd.DataFrame) -> dict:
    """Pure: runs the exact imported divergence_events() on the FULL series
    `d` and reads the latest CLOSED bar's event flags. No state mutation —
    dry mode and the live path call this exact same function, so they can
    never drift apart."""
    osc = rsi(d["close"], RSI_N)
    champ4h = vol_gated_ma(d, **CHAMP_KW)
    long_reg, short_reg, long_hid, short_hid, low_ext, high_ext = \
        divergence_events(d, osc, SWING_K, champ4h)
    i = len(d) - 1
    champ_v = champ4h.iloc[i]
    low_v, high_v = low_ext.iloc[i], high_ext.iloc[i]
    return {
        "bar_ts": _fmt_utc(d["timestamp"].iloc[i]),
        "close": float(d["close"].iloc[i]),
        "rsi14": float(osc.iloc[i]) if osc.iloc[i] == osc.iloc[i] else None,
        "champ": int(champ_v) if champ_v == champ_v else None,
        "long_hidden": bool(long_hid.iloc[i]),
        "short_hidden": bool(short_hid.iloc[i]),
        "low_extreme": float(low_v) if pd.notna(low_v) else None,
        "high_extreme": float(high_v) if pd.notna(high_v) else None,
    }


def swing_debug(d: pd.DataFrame, k: int = SWING_K) -> dict:
    """Display-only helper for step61_diver_smoke.py: the most recently
    CONFIRMED swing high/low (imported swings(), never reimplemented) —
    what the book is watching right now, independent of whether either one
    just triggered a divergence event."""
    conf_high, conf_low = swings(d["high"], d["low"], k)
    high_idx = [i for i in range(len(d)) if bool(conf_high.iloc[i])]
    low_idx = [i for i in range(len(d)) if bool(conf_low.iloc[i])]

    def _one(idx_list, price_col):
        if not idx_list:
            return None
        j = idx_list[-1]
        origin = j - k
        return {"confirmed_at": _fmt_utc(d["timestamp"].iloc[j]),
               "origin_bar_ts": _fmt_utc(d["timestamp"].iloc[origin]),
               "price": float(d[price_col].iloc[origin])}

    return {"last_confirmed_swing_high": _one(high_idx, "high"),
           "last_confirmed_swing_low": _one(low_idx, "low")}


# ===========================================================================
# direction gate
# ===========================================================================

def _other_btc_book_active(state: dict) -> bool:
    """Mirrors daily_pick._btc_books_active exactly: true if ANY other
    BTC-USDT book (via book_ledger's shared accounting, "diver" itself
    excluded — this book is flat whenever it's asking) holds a position, or
    newsdesk has an armed-but-not-yet-filled pending trade."""
    recorded = recorded_book_positions(state)
    if any(abs(v) > LOT / 2 for k, v in recorded.items() if k != "diver"):
        return True
    if state.get("newsdesk", {}).get("pending"):
        return True
    return False


def _direction_gate(direction: int, net: float, state: dict) -> str | None:
    """Returns a stand-down reason string, or None if the entry is clear.
    See the module docstring's DIRECTION GATES section for why shorts carry
    the extra other-book check and longs don't."""
    if direction > 0:
        if net <= -LOT / 2:
            return f"long would oppose existing net {net:+.2f} ct"
        return None
    if net >= LOT / 2:
        return f"short would oppose existing net {net:+.2f} ct"
    if _other_btc_book_active(state):
        return "short stand-down — another BTC book is already open/armed"
    return None


# ===========================================================================
# bracket protection (hardened double-read, mirrors newsdesk.py/shorts_lab.py
# exactly, generalized to either direction)
# ===========================================================================

def _cleanup_orders(private, symbol, t):
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


def _bracket_present(private, symbol, t) -> bool:
    brackets = private.pending_tpsl(symbol)
    if not brackets:
        return False
    our_id = t.get("tpsl_id")
    if our_id:
        return any(str(b.get("tpslId")) == str(our_id) for b in brackets)
    return True


def _ensure_bracket(private, symbol, state, t):
    """SELF-HEALING PROTECTION, identical hardening to newsdesk.py's copy:
    read pending_tpsl TWICE 4s apart, only re-arm if BOTH reads come back
    empty AND a fresh net-position read confirms the position still
    exists. A read exception means 'don't know' — do nothing."""
    if not t or not t.get("sl_price"):
        return
    try:
        if _bracket_present(private, symbol, t):
            return
        time.sleep(4)
        if _bracket_present(private, symbol, t):
            return
        net = private.net_position_contracts(symbol)
        if abs(net) < LOT / 2:
            return
    except Exception as e:
        print(f"  [DIVER] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(symbol, close_side, t["contracts"],
                                     t.get("tp_price"), t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [DIVER] ⚠️ bracket was MISSING — re-armed SL "
              f"{t['sl_price']:,.1f}")
        notify("\U0001f6e1️ Stop re-armed (demo)",
              f"The Diver's TP/SL had vanished — re-placed. SL now back at "
              f"${t['sl_price']:,.0f}.")
    except Exception as e:
        print(f"  [DIVER] bracket re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ The Diver UNPROTECTED (demo)",
              "bracket missing and re-arm failed — check BloFin now")


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    """Close the Diver's trade on its own ledger line. Direction-aware:
    profit on a rise when long, on a fall when short (mirrors
    newsdesk._book_exit exactly)."""
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["diver"]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [DIVER] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "diver_exit", "reason": reason,
               "trigger": "hidden_divergence", "direction": t["direction"],
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq})
    record_trade_outcome(state, "hidden_divergence", realized)
    write_lesson(state, "hidden_divergence", realized, t["entry_price"],
                exit_price, reason, t.get("ctx"))
    notify(f"\U0001f93f The Diver {reason}: ${realized:+,.2f}",
          f"{side} hidden-divergence trade — ledger ${eq:,.2f} (demo)")
    return realized


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_diver(private: BlofinDemoPrivate, live_feed, demo_feed,
             state: dict, dry: bool = False):
    """One cycle. Returns a small summary dict, mainly for tests/smoke."""
    dv = state.setdefault("diver", {"open_trade": None, "last_bar_ts": None})
    t = dv.get("open_trade")
    tag = " DRY" if dry else ""

    # -- reconcile (book-aware attribution, see book_ledger.py) -----------
    net = private.net_position_contracts(SYMBOL)
    attributed = attributed_position(net, state, "diver")
    unexplained = unexplained_position(net, state)
    recorded_signed = (t["direction"] * t["contracts"]) if t else 0.0
    print(f"  [DIVER{tag}] reconcile: net={net:+.2f} attributed_diver="
          f"{attributed:+.2f} (recorded {recorded_signed:+.1f}) "
          f"unexplained={unexplained:+.2f}")

    if t and abs(attributed) < LOT / 2:
        # our position is gone — a bracket fired (or someone closed it)
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        direction = t["direction"]
        if direction > 0:
            reason = "TP hit" if exit_price >= t["entry_price"] else "SL hit"
        else:
            reason = "TP hit" if exit_price <= t["entry_price"] else "SL hit"
        fee_bps = 2.0 if reason == "TP hit" else 6.0
        print(f"  [DIVER{tag}] our {'long' if direction > 0 else 'short'} "
              f"is gone -> {reason} @ {exit_price:,.1f}")
        if dry:
            print("  [DIVER DRY] would cancel remaining bracket orders and "
                  "book this exit — no state/order changes made")
            return {"action": "would_exit", "reason": reason,
                    "exit_price": exit_price}
        _cleanup_orders(private, SYMBOL, t)
        realized = _book_exit(state, t, exit_price, fee_bps, reason)
        # RETURN HERE (matches gold_book.py, not newsdesk's fallthrough):
        # newsdesk can safely fall through after booking an exit because
        # its own entry path is gated behind a SEPARATE "pending" state
        # that only a fresh headline scan can arm. The Diver's entry check
        # reads the SAME `dec` a reconcile could act on in the same
        # breath, so without an explicit stop here a reconciled exit could
        # immediately re-enter on the very next line, in the very same
        # cycle — two exchange actions where the house pattern (and the
        # "one position at a time" mandate's spirit) expects one. Any
        # fresh signal on a later bar is caught next cycle instead, at
        # most an hour later.
        return {"action": "reconciled_exit", "reason": reason,
                "exit_price": exit_price, "pnl": realized}
    elif not t and abs(unexplained) > LOT / 2:
        # NOT ours to adopt — the shorts lab owns adoption of unexplained
        # positions (see shorts_lab.py); we only ever warn.
        print(f"  [DIVER{tag}] unexplained net {unexplained:+.2f} ct on the "
              f"exchange — NOT adopting (that's the shorts lab's job)")

    # -- open position: 48h time exit, else self-heal the bracket ---------
    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", MAX_HOLD_H)
        if held_h >= max_hold_h:
            print(f"  [DIVER{tag}] {held_h:.0f}h >= {max_hold_h:.0f}h max "
                  f"hold -> closing")
            if dry:
                print(f"  [DIVER DRY] would market-cover {t['contracts']:.1f} "
                      f"ct now — no orders placed")
                return {"action": "would_time_exit", "contracts": t["contracts"]}
            _cleanup_orders(private, SYMBOL, t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(SYMBOL)
            ref_price = quote.bid if side == "sell" else quote.ask
            fill, was_maker = execute_market_clips(
                private, demo_feed, SYMBOL, side, t["contracts"],
                ref_price, reduce_only=True)
            _book_exit(state, t, fill, 2.0 if was_maker else 6.0,
                      f"{max_hold_h:.0f}h time")
            return {"action": "time_exit", "fill": fill}
        if not dry:
            _ensure_bracket(private, SYMBOL, state, t)
        print(f"  [DIVER{tag}] holding {t['contracts']:.1f} ct "
              f"{'long' if t['direction'] > 0 else 'short'} from "
              f"{t['entry_price']:,.1f} ({held_h:.0f}h/{max_hold_h:.0f}h), "
              f"bracket verified")
        return {"action": "holding", "direction": t["direction"],
                "held_h": round(held_h, 1)}

    # -- flat: read the latest closed 4h bar and check for a fresh signal -
    d = _load_4h(live_feed)
    dec = _decision(d)
    signal_str = ("LONG" if dec["long_hidden"] else
                 "SHORT" if dec["short_hidden"] else "none")
    print(f"  [DIVER{tag}] {dec['bar_ts']} close {dec['close']:,.1f} | "
          f"RSI14 {dec['rsi14']:.1f} | champ4h={dec['champ']} | "
          f"signal={signal_str}")

    if dry:
        if not (dec["long_hidden"] or dec["short_hidden"]):
            print("  [DIVER DRY] no signal on the latest closed bar — "
                  "NO ORDER PLACED")
            return {"action": "would_stay_flat", **dec}
        direction = 1 if dec["long_hidden"] else -1
        gate_reason = _direction_gate(direction, net, state)
        if gate_reason:
            print(f"  [DIVER DRY] WOULD STAND DOWN — {gate_reason} — NO "
                  f"ORDER PLACED")
            return {"action": "would_stand_down", "reason": gate_reason,
                    "direction": direction, **dec}
        ref_price = dec["close"]
        try:
            ref_price = live_feed.get_ticker(SYMBOL).last
        except Exception:
            pass
        notional = float(state.get("virtual_equity", 0.0)) * DIVER_ALLOC * DIVER_LEV
        contracts = max(LOT, round(notional / ref_price / CONTRACT_BTC / LOT) * LOT)
        if direction > 0:
            tp_est = round(ref_price * (1 + TARGET_PCT / 100), 1)
            sl_est = round(ref_price * (1 - STOP_PCT / 100), 1)
        else:
            tp_est = round(ref_price * (1 - TARGET_PCT / 100), 1)
            sl_est = round(ref_price * (1 + STOP_PCT / 100), 1)
        print(f"  [DIVER DRY] {'LONG' if direction > 0 else 'SHORT'} WOULD "
              f"FIRE — {contracts:.1f} ct (~${notional:,.0f} notional at "
              f"{DIVER_LEV:.0f}x, {DIVER_ALLOC*100:.0f}% alloc) @ "
              f"~{ref_price:,.1f} | est TP {tp_est:,.1f} est SL {sl_est:,.1f} "
              f"| max hold {MAX_HOLD_H}h — NO ORDER PLACED")
        return {"action": "would_enter", "direction": direction,
                "contracts": contracts, "entry_ref": ref_price,
                "est_tp": tp_est, "est_sl": sl_est, **dec}

    # -- idempotency: this exact 4h bar was already decided on ------------
    if dv.get("last_bar_ts") == dec["bar_ts"]:
        print(f"  [DIVER] {dec['bar_ts']} already processed — no-op "
              f"(idempotent)")
        return {"action": "noop_already_processed", **dec}

    if not (dec["long_hidden"] or dec["short_hidden"]):
        dv["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        return {"action": "no_event", **dec}

    direction = 1 if dec["long_hidden"] else -1
    gate_reason = _direction_gate(direction, net, state)
    if gate_reason:
        dv["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        print(f"  [DIVER] STAND DOWN — {gate_reason}")
        log_event({"action": "diver_stand_down", "reason": gate_reason,
                   "direction": direction, "net": net,
                   "bar_ts": dec["bar_ts"]})
        notify("\U0001f93f The Diver skipped (demo)",
              f"hidden divergence {'long' if direction > 0 else 'short'} "
              f"signal fired but stood down — {gate_reason}")
        return {"action": "stood_down", "reason": gate_reason,
                "direction": direction, **dec}

    # -- entry --------------------------------------------------------------
    ref_price = dec["close"]
    try:
        ref_price = live_feed.get_ticker(SYMBOL).last
    except Exception:
        pass
    notional = float(state.get("virtual_equity", 0.0)) * DIVER_ALLOC * DIVER_LEV
    contracts = max(LOT, round(notional / ref_price / CONTRACT_BTC / LOT) * LOT)
    side = "buy" if direction > 0 else "sell"

    print(f"  [DIVER] {'LONG' if direction > 0 else 'SHORT'} SIGNAL "
          f"(hidden_divergence) — {side} {contracts:.1f} ct "
          f"(~${notional:,.0f} notional at {DIVER_LEV:.0f}x sleeve leverage)")
    private.ensure_leverage(SYMBOL, DIVER_LEV)
    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, SYMBOL, side, contracts, ref_price)
    except Exception as e:
        print(f"  [DIVER] ENTRY FAILED: {str(e)[:100]}")
        log_event({"action": "diver_entry_failed", "error": str(e)[:200]})
        notify("⚠️ The Diver ENTRY FAILED (demo)",
              f"hidden_divergence tried to {side} but the order was "
              f"rejected: {str(e)[:80]}. No position opened — check "
              f"BloFin.")
        dv["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        return {"action": "entry_failed", "error": str(e)[:120], **dec}

    if direction > 0:
        tp = round(entry * (1 + TARGET_PCT / 100), 1)
        sl = round(entry * (1 - STOP_PCT / 100), 1)
        close_side = "sell"
    else:
        tp = round(entry * (1 - TARGET_PCT / 100), 1)
        sl = round(entry * (1 + STOP_PCT / 100), 1)
        close_side = "buy"

    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(SYMBOL, close_side, contracts, tp, sl)
    except Exception as e:
        print(f"  [DIVER] TP/SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ The Diver bracket failed (demo)",
              "position opened but TP/SL not set — check BloFin now")

    dv["open_trade"] = {
        "trigger": "hidden_divergence", "direction": direction,
        "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": 6.0, "entry_time": now_utc(),
        "tp_price": tp, "sl_price": sl, "tpsl_id": tpsl_id,
        "max_hold_h": MAX_HOLD_H, "bar_ts": dec["bar_ts"],
        "rsi_at_entry": dec["rsi14"], "champ_at_entry": dec["champ"],
        "swing_extreme": dec["low_extreme"] if direction > 0 else dec["high_extreme"],
        "ctx": {"news": recent_news_headline()},
    }
    dv["last_bar_ts"] = dec["bar_ts"]
    save_state(state)
    log_event({"action": "diver_enter", "direction": direction,
               "fill_price": entry, "contracts": contracts, "tp": tp,
               "sl": sl, "maker": was_maker, "bar_ts": dec["bar_ts"],
               "rsi14": dec["rsi14"], "champ": dec["champ"]})
    notify(f"\U0001f93f THE DIVER {'LONG' if direction > 0 else 'SHORT'} (demo)",
          f"{side} {contracts:.1f} ct @{entry:,.0f} | TP {tp:,.0f} "
          f"SL {sl:,.0f} | 48h max hold | hidden RSI divergence continuation")
    return {"action": "entered", "direction": direction, "entry": entry,
           "contracts": contracts, "tp": tp, "sl": sl, **dec}
