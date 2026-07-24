"""
newsdesk.py — THE NEWSDESK: the live demo-trading book for round 45B, the
FIRST strategy in this whole program to pass a sealed out-of-sample test
(step45b_news_events.py: A-news-momentum, first-bar-move, 1h,
stop1.2%/tgt2.4%, hold24h — train +$23.74/t, val +$7.11/t, SEALED TEST
+$20.81/t x67, +13.9%). news_book.py forward-tested this exact setup with
SIMULATED money, isolated from the shared BloFin net. This file is the
promotion: real demo orders, on the shared BTC-USDT position, joined to
book_ledger.py's attribution system. Structural template: shorts_lab.py
(one slot, dry mode, reconcile, hardened double-read _ensure_bracket,
_book_exit math, entry via ensure_leverage + a single place_tpsl bracket).

THE VALIDATED ENTRY RULE (deployed VERBATIM — no improvements; UNCHANGED by
the round-65 exit swap below):
  When a RELEVANT WatcherGuru headline lands, take the FIRST FULL 1h bar
  after the event (the bar whose entire life is post-event: event at
  14:07 -> the 15:00-16:00 bar), read its close-vs-open sign, and enter AT
  THAT BAR'S CLOSE in that direction. Relevance = the EXACT classify_
  headline() imported from step45b_news_events.py, unmodified. Direction
  comes from the BAR, never the keyword tag — keyword tags are irrelevant
  to this variant; they are imported only as a side effect of importing
  classify_headline itself. (Historical note: this entry was originally
  validated round 45B alongside a fixed stop1.2%/target2.4%/hold24h exit —
  see the ROUND 65 EXIT SWAP section just below for what replaced that
  exit and why; the entry itself was never touched.)

NO-LOOKAHEAD ALIGNMENT, matched to step45b_news_events.align_events exactly:
  floor bar  = the bar whose open <= event_ts (== event_ts floored to the
               hour) — the bar that was already live when the headline hit.
  trading bar (direction_bar_open_ts) = floor bar's open + 1h — the first
               bar whose ENTIRE life happens strictly after the event was
               public. Event 14:07 -> floor 14:00 -> direction bar 15:00,
               exactly the mandate's own worked example. We enter at THAT
               bar's own close once it has closed (16:00), i.e. one full
               bar later than align_events' `trading_idx` flag position —
               align_events sets the signal flag on trading_idx and lets
               the backtest engine fill at trading_idx's OPEN; the live
               rule instead reads trading_idx's own CLOSE for direction
               and fills there. Same bar, same no-lookahead boundary,
               different (mandate-specified) fill point within it.

ROUND 65 EXIT SWAP (this file, 2026-07-24): the ENTRY above is UNCHANGED —
still the exact validated trigger, verbatim. The EXIT is not: the fixed
TP+2.4%/SL-1.2%/24h bracket (N0, the "incumbent") is RETIRED. It was the
owner's own critique (step65_news_eyes.py's docstring, verbatim): "you
already know your take profit before even looking at the situation — no
technical analysis, no price action. No real trader does this." Round 65's
sealed test (step65_news_eyes.py, N2 STRUCTURE TRAILING, k=5, buffer 0.3%)
found the incumbent STALE and bleeding in the current regime (-$14.93/t,
-15.7% on the sealed 2026-05->07 slice, 104-105 trades) while N2 PASSED on
all three windows (train +$9.57/t x315, val +$4.34/t x112, sealed test
+$10.35/t x104-105, +10.8%) — beating the incumbent everywhere, not just
in-sample. This file now deploys N2 EXACTLY as step65_news_eyes.py defines
it (mirrored/ported below, NOT imported — same convention gold_book.py
already established for its own round-59 structure-trailing exit, so a
research file can keep iterating without ever being a live import
dependency):
  INITIAL STOP = entry_bar_extreme_stop: the ENTRY BAR's own opposite
    extreme (its low for a long, its high for a short — "read the reaction
    candle") +/- a TRAIL_BUFFER_PCT=0.3% buffer. Stored at entry from the
    same 1h candle already read for direction (see _resolve_direction).
  NO TAKE-PROFIT. tp_price is always None now — the winners run until the
    chart itself says stop, never amputated at a fixed distance.
  FLOOR TRAILING = the initial stop only ever ratchets FAVORABLY, as new
    CONFIRMED 1h swing lows (longs; highs for shorts, k=TRAIL_K=5 — a swing
    counts only once 5 further bars have CLOSED after it, no lookahead)
    print above it (below it, for shorts) — never backward. Recomputed
    FRESH every cycle from the live 1h series (_compute_trail_floor), the
    same "no incremental ratchet state to drift" pattern gold_book.py's own
    _compute_trail_floor uses.
  24h max hold is UNCHANGED.
PROTECTION LIVES EXCHANGE-SIDE, exactly like every other book in this repo:
  place_tpsl at entry with an SL-only bracket (tp_price=None) at the
  initial stop; every hourly cycle while holding, if the recomputed floor
  ratcheted, a NEW bracket is placed BEFORE the old one is cancelled (see
  the "in a position" branch below — mirrors gold_book.py's own R59
  cancel/replace mechanics verbatim: place-then-cancel, never the reverse,
  so a failed new placement never leaves the position naked even for one
  cycle). _ensure_bracket's double-read self-heal (below) needed NO change
  for this: it only ever asserted a non-empty sl_price, never a tp — a
  missing TP was already a no-op there, now it is simply always the case.
DEVIATION CHECK: none. Every number and mechanic above (buffer 0.3%, k=5,
entry-bar-extreme anchor, favorable-only ratchet, exchange-side SL-only
bracket, 24h cap) matches step65_news_eyes.py's N2 definition exactly —
this file only had to translate "recompute a floor over a fixed backtest
array" into "recompute a floor over the live 1h feed every hourly cycle."

NEWS SOURCE — REALITY CHECK (read before touching anything above)
The Supabase RPC `cryptobot_recent_news` was inspected live (read-only,
n=200) before writing this file. It returns a PLAIN LIST OF STRINGS —
no id, no timestamp, no source column, nothing but headline text, ordered
newest-first. The `cryptobot_news` table it reads from mixes MANY sources
into one feed: Donald Trump's own Truth Social reposts, WHITEHOUSE press
releases, COINTELEGRAPH, CoinDesk, DECRYPT, THE BLOCK, FORBES, BLOOMBERG
LAW, EU COUNCIL, dozens of individual crypto-project Twitter accounts,
SEC filings, and — the ones we want — WatcherGuru. WatcherGuru's own posts
are recognizable ONLY by a literal "[WatcherGuru]" text prefix baked into
the string itself (confirmed empirically: 25 of a 200-row sample carried
it, all in the form "[WatcherGuru] JUST IN: ..."). `_is_watcherguru()`
below is that filter — a text-prefix check, because that is the only
signal the feed actually carries.

DEVIATION FROM THE BRIEF, FORCED BY THAT REALITY (flagged loudly, also in
the final report): the brief says to track `last_event_ts` and process
"news rows newer than" it. With no per-row timestamp or id in what the RPC
actually returns, a literal `row.timestamp > last_event_ts` comparison is
impossible — there is no row.timestamp. This module instead:
  - dedupes by keeping a rolling set of already-seen headline TEXT
    (state["newsdesk"]["seen_headlines"], capped) — text is the only
    stable identity the feed offers;
  - treats the WALL-CLOCK moment we first observe a new relevant
    WatcherGuru headline as that headline's event_ts. Defensible: the
    news-watch -> workflow_dispatch wake fires promptly on new rows (see
    the WIRE-IN note below), so observation time closely tracks post
    time, and this bot can only ever act on news once its own pipeline
    has seen it — the same causal boundary the backtest itself enforced
    (it could only trade on the bar after a post became public);
  - still keeps `state["newsdesk"]["last_event_ts"]` exactly as specified
    in the schema, populated with the wall-clock time of the last scan
    that found anything — an informational/audit field, not the dedup
    mechanism (that's `seen_headlines`).
No other deviation from the validated rule was necessary or made.

WIRE-IN / TIMING (daemon.py + hourly.py): newsdesk timing depends on 1h
bar closes. The daemon's hourly bar-close full_cycle (and hourly.py's own
top-of-hour cron) satisfy the entry timing on their own. A headline that
lands MID-HOUR is picked up sooner than that: the news-watch edge function
fires a `workflow_dispatch` wake, hourly.py runs immediately, scans the
wire, and (if daemon isn't already alive and owning trading) sets
`pending` right then — well before the direction bar even opens, let alone
closes. Either path — the daemon's own next hourly cycle, or the
workflow_dispatch wake — arms `pending` comfortably before
`direction_bar_open_ts + 1h`; actual ENTRY only ever happens on a
bar-close decision cycle, matching the backtest's own fill timing exactly.

DRY MODE: run_newsdesk(..., dry=True) computes and prints the full
decision every cycle would make — reconcile, gate, sizing, stop/target —
but places NO orders and makes NO state/log/notify side effects. Used by
step46_newsdesk_smoke.py against the REAL news RPC and REAL candles.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from blofin_private import BlofinDemoPrivate
from book_ledger import attributed_position, unexplained_position
from step45b_news_events import classify_headline
from step5_paper_trade import (CLOUD_STATE, CONTRACT_BTC, LOT, _SB_SECRET,
                               _sb_rpc, execute_maker_or_chase, execute_market_clips, log_event,
                               notify, now_utc, record_trade_outcome,
                               save_state, write_lesson)

SYMBOL = "BTC-USDT"

# -- sizing: one slot, 15% of ledger equity, 20x leverage (owner's 15-20x
# tier mandate — see shorts_lab.py's identical LAB_ALLOC/LAB_LEV choice) --
NEWS_ALLOC = 0.15
NEWS_LEV = 20.0

# -- N0 INCUMBENT geometry — RETIRED round 65 (see the module docstring's
# ROUND 65 EXIT SWAP). No longer read anywhere to place an order; kept
# defined, unused, purely as historical reference — same precedent as
# gold_book.py keeping its own retired EMA_N constant around after its
# round-59 exit swap.
STOP_PCT = 1.2
TARGET_PCT = 2.4          # 2x the stop

MAX_HOLD_H = 24            # UNCHANGED by the round-65 exit swap

# -- N2 STRUCTURE TRAILING geometry (round 65, sealed-validated — see the
# module docstring's ROUND 65 EXIT SWAP) — the live exit, deployed verbatim
# from step65_news_eyes.py's N2 (mirrored/ported, not imported, below) ---
TRAIL_BUFFER_PCT = 0.3      # % beyond the entry bar's opposite extreme
TRAIL_K = 5                 # confirmed-swing pivot lag (a swing counts only
                            # once k further 1h bars have CLOSED after it —
                            # no lookahead, mirrors step65's K_SWING_PRIMARY)
TRAIL_CANDLE_BARS = 60      # 1h bars pulled each cycle to recompute the
                            # floor — comfortably covers the 24h max hold
                            # plus TRAIL_K confirmation lag plus margin for
                            # locating the entry bar itself in the window

SCAN_N = 40                # recent news rows pulled from the RPC each cycle
SEEN_CAP = 400              # rolling dedup window (headline TEXT, see above)


# ===========================================================================
# news source
# ===========================================================================

def _fetch_recent_news(n: int = SCAN_N) -> list[str]:
    """The RPC returns a plain newest-first list of headline strings — see
    the module docstring's REALITY CHECK. Monkeypatched wholesale by
    test_newsdesk_timing.py to inject fake headlines offline."""
    if not CLOUD_STATE:
        return []
    try:
        rows = _sb_rpc("cryptobot_recent_news", {"secret": _SB_SECRET, "n": n})
        return [r for r in (rows or []) if isinstance(r, str)]
    except Exception as e:
        print(f"  [NEWS] news RPC unreachable: {str(e)[:80]}")
        return []


def _is_watcherguru(headline: str) -> bool:
    """The ONLY source signal the feed actually carries: a literal
    '[WatcherGuru]' text prefix (see the module docstring)."""
    return (headline or "").strip().lower().startswith("[watcherguru]")


def _find_new_relevant(seen_headlines: list[str], headlines: list[str]):
    """Pure. `headlines` is the RPC's newest-first snapshot; `seen_headlines`
    is what we've already judged (any cycle, any verdict). Returns
    (chosen_or_None, updated_seen) — `chosen` is the chronologically FIRST
    (i.e. oldest-of-the-new-batch) new RELEVANT WatcherGuru headline;
    `updated_seen` marks EVERYTHING just scanned as seen either way (each
    headline is judged exactly once, matching the mandate). The caller
    decides whether to persist `updated_seen` — skipped entirely in dry
    mode so a preview run never marks anything as processed."""
    seen_set = set(seen_headlines)
    new_rows = [h for h in headlines if h not in seen_set]
    chosen = None
    for h in reversed(new_rows):          # oldest of the new batch first
        if _is_watcherguru(h) and classify_headline(h).get("relevant"):
            chosen = h
            break
    updated = list(seen_headlines)
    for h in headlines:
        if h not in seen_set:
            updated.append(h)
            seen_set.add(h)
    return chosen, updated[-SEEN_CAP:]


# ===========================================================================
# no-lookahead alignment (mirrors step45b_news_events.align_events)
# ===========================================================================

def _direction_bar_open_ts(event_ts: pd.Timestamp) -> pd.Timestamp:
    """event_ts floored to the hour == the FLOOR bar's open (the bar that
    was already live when the headline hit); +1h == the TRADING bar's own
    open — the first bar whose entire life is strictly after the event.
    Event 14:07 -> 15:00, the mandate's own worked example."""
    return pd.Timestamp(event_ts).floor("1h") + pd.Timedelta(hours=1)


def _resolve_direction(live_feed, direction_bar_open_ts: pd.Timestamp):
    """Look for the CLOSED 1h bar that opened at direction_bar_open_ts.
    live_feed.get_candles only ever returns confirmed/closed bars (see
    exchange.py), so if that timestamp appears at all, the bar is closed.
    Returns (direction, bar_open, bar_high, bar_low, bar_close); direction
    is None if the bar hasn't closed yet, 0 for a doji (no direction). The
    high/low are read here (not just open/close) because round 65's N2
    exit needs THIS SAME bar's own opposite extreme for the initial
    structure stop — see _entry_bar_extreme_stop below — and this is the
    one place that bar is already being fetched, so no second read."""
    candles = live_feed.get_candles(SYMBOL, "1h", 12)
    if candles is None or len(candles) == 0:
        return None, None, None, None, None
    match = candles[candles["timestamp"] == direction_bar_open_ts]
    if match.empty:
        return None, None, None, None, None
    row = match.iloc[-1]
    o, h, l, c = (float(row["open"]), float(row["high"]),
                 float(row["low"]), float(row["close"]))
    if c > o:
        return 1, o, h, l, c
    if c < o:
        return -1, o, h, l, c
    return 0, o, h, l, c


# ===========================================================================
# N2 STRUCTURE TRAILING (round 65, sealed-validated — see the module
# docstring's ROUND 65 EXIT SWAP). Mirrored/ported verbatim from
# step65_news_eyes.py's entry_bar_extreme_stop / find_pivots, NOT imported —
# the same "production books re-implement a sealed pure function locally"
# convention gold_book.py already established for its own round-59
# structure-trailing exit (_find_swing_lows / _compute_trail_floor), so a
# research file (step65_news_eyes.py) stays free to keep iterating without
# ever becoming a live import dependency.
# ===========================================================================

def _entry_bar_extreme_stop(direction: int, bar_high: float, bar_low: float,
                            buffer_pct: float = TRAIL_BUFFER_PCT) -> float:
    """Initial protective stop = the ENTRY BAR's own opposite extreme, plus
    a buffer — "read the reaction candle," the owner's own critique of the
    old fixed bracket. Longs: below that bar's low. Shorts: above that
    bar's high. Ported verbatim from step65_news_eyes.entry_bar_extreme_
    stop (same formula, this file's own o/h/l/c array indexing collapsed
    to the single bar newsdesk already has in hand at entry)."""
    if direction > 0:
        return bar_low * (1 - buffer_pct / 100)
    return bar_high * (1 + buffer_pct / 100)


def _find_pivots(h: np.ndarray, l: np.ndarray, k: int = TRAIL_K):
    """Fractal swing pivots, CONFIRMED only k bars later (no lookahead: at
    confirm_idx=j+k the pivot is knowable, not before). Ported verbatim
    from step65_news_eyes.find_pivots. Returns (hi_pivots, lo_pivots),
    each {"confirm_idx": np.array[int], "price": np.array[float]}."""
    n = len(h)
    hi_confirm, hi_price, lo_confirm, lo_price = [], [], [], []
    for j in range(k, n - k):
        wh = h[j - k:j + k + 1]
        if h[j] >= wh.max():
            hi_confirm.append(j + k)
            hi_price.append(h[j])
        wl = l[j - k:j + k + 1]
        if l[j] <= wl.min():
            lo_confirm.append(j + k)
            lo_price.append(l[j])
    return (
        {"confirm_idx": np.array(hi_confirm, dtype=int), "price": np.array(hi_price, dtype=float)},
        {"confirm_idx": np.array(lo_confirm, dtype=int), "price": np.array(lo_price, dtype=float)},
    )


def _compute_trail_floor(candles: pd.DataFrame, direction: int,
                         entry_bar_open_ts, initial_floor: float,
                         k: int = TRAIL_K):
    """The live floor for one hourly cycle — mirrors step65_news_eyes.py's
    N2 "trailing" _manage loop EXACTLY (that loop is itself just a running
    max over confirmed post-entry pivots, so recomputing fresh every cycle
    from scratch gives the identical final floor an incremental per-bar
    loop would — same reasoning gold_book.py's own _compute_trail_floor
    docstring gives for its round-59 exit). Starts at `initial_floor` (the
    entry bar's own extreme +/- buffer, see _entry_bar_extreme_stop) and
    only ever ratchets FAVORABLY as new swing lows (longs; highs, shorts)
    CONFIRM strictly after the entry bar — never backward, and pre-entry
    pivots never move it (matches step65's own bisect-from-entry_idx+1
    window exactly).

    Returns (new_floor, entry_idx). entry_idx is None if `candles` doesn't
    contain the entry bar's own timestamp (too little history pulled this
    cycle, or a clock/feed hiccup) — the caller must treat that as "skip
    this cycle's ratchet, try again next cycle," never as a reset."""
    ts = pd.DatetimeIndex(candles["timestamp"])
    matches = np.where(ts == pd.Timestamp(entry_bar_open_ts))[0]
    if len(matches) == 0:
        return initial_floor, None
    entry_idx = int(matches[0])
    h = candles["high"].to_numpy()
    l = candles["low"].to_numpy()
    hi_piv, lo_piv = _find_pivots(h, l, k)
    piv = lo_piv if direction > 0 else hi_piv
    floor_px = initial_floor
    for confirm_i, price in zip(piv["confirm_idx"], piv["price"]):
        if confirm_i > entry_idx:
            if direction > 0 and price > floor_px:
                floor_px = float(price)
            elif direction < 0 and price < floor_px:
                floor_px = float(price)
    return floor_px, entry_idx


def _parse_utc(s: str) -> pd.Timestamp:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    return pd.Timestamp(dt)


def _fmt_utc(ts: pd.Timestamp) -> str:
    return f"{pd.Timestamp(ts):%Y-%m-%d %H:%M:%S} UTC"


# ===========================================================================
# bracket protection (hardened double-read, mirrors shorts_lab.py exactly,
# generalized to either direction since newsdesk trades both ways)
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
    """SELF-HEALING PROTECTION, identical hardening to shorts_lab.py's copy:
    read pending_tpsl TWICE 4s apart, only re-arm if BOTH reads come back
    empty AND a fresh net-position read confirms the position still
    exists. A read exception means 'don't know' — do nothing.

    ROUND 65 CHECK (verified while wiring N2, no change needed): this
    function has NEVER asserted anything about tp_price — only sl_price is
    required, and t.get("tp_price") is passed straight through to
    place_tpsl either way (which already treats None as "omit the TP leg,
    place SL-only" — see blofin_private.place_tpsl). A missing TP was
    always a correct, healthy state here, never a healing trigger; N2 just
    makes that the permanent case instead of the fallback one."""
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
        print(f"  [NEWS] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(symbol, close_side, t["contracts"],
                                     t.get("tp_price"), t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [NEWS] ⚠️ bracket was MISSING — re-armed SL "
              f"{t['sl_price']:,.1f}")
        notify("🛡️ Stop re-armed (demo)",
              f"The news trade's TP/SL had vanished — re-placed. "
              f"SL now back at ${t['sl_price']:,.0f}.")
    except Exception as e:
        print(f"  [NEWS] bracket re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ newsdesk UNPROTECTED (demo)",
              "bracket missing and re-arm failed — check BloFin now")


def _ratchet_trail_floor(private, live_feed, state, t, dry: bool):
    """Round 65's N2 exit, live: recompute the structure-trailing floor
    fresh every hourly cycle and, if it ratcheted favorably, cancel/replace
    the exchange-side SL-only bracket at the new level. Mirrors gold_book.
    py's own R59 "in a position" branch mechanics EXACTLY: place the NEW
    bracket BEFORE cancelling the OLD one, so a failed new placement never
    leaves the position naked even for one cycle (the reverse order has a
    real window with no bracket at all). dry=True computes and PRINTS what
    would happen with zero order/state/log/notify side effects, same
    contract as every other dry branch in this file."""
    entry_bar_open_ts = t.get("entry_bar_open_ts")
    if not entry_bar_open_ts:
        return   # pre-round-65 trade record (shouldn't happen live, but
                 # never crash on an old shape) — nothing to ratchet against
    try:
        candles = live_feed.get_candles(SYMBOL, "1h", TRAIL_CANDLE_BARS)
    except Exception as e:
        print(f"  [NEWS] trail floor recompute skipped (feed read failed): "
              f"{str(e)[:80]}")
        return
    if candles is None or len(candles) == 0:
        return

    old_floor = t.get("trail_floor", t["sl_price"])
    initial_floor = _entry_bar_extreme_stop(
        t["direction"], t["entry_bar_high"], t["entry_bar_low"])
    raw_floor, entry_idx = _compute_trail_floor(
        candles, t["direction"], entry_bar_open_ts, initial_floor,
        t.get("trail_k", TRAIL_K))
    if entry_idx is None:
        print(f"  [NEWS] trail floor recompute skipped — entry bar "
              f"{entry_bar_open_ts} not in the {TRAIL_CANDLE_BARS}-bar "
              f"window pulled this cycle, will retry next cycle")
        return

    # defensive clamp: the floor must NEVER move backward, even if some
    # feed hiccup (a shorter window pulled this cycle, say) would otherwise
    # make a from-scratch recompute look like it retreated.
    new_floor = max(raw_floor, old_floor)
    moved = new_floor > old_floor + 1e-9

    if dry:
        verb = "WOULD RATCHET to" if moved else "stays at"
        print(f"  [NEWS DRY] trailing floor {verb} ${new_floor:,.1f} — "
              f"NO ORDER PLACED")
        return

    if not moved:
        return

    new_sl = round(new_floor, 1)
    close_side = "sell" if t["direction"] > 0 else "buy"
    try:
        new_tpsl_id = private.place_tpsl(SYMBOL, close_side, t["contracts"],
                                         None, new_sl)
    except Exception as e:
        print(f"  [NEWS] trailing floor ratchet FAILED to place the new "
              f"bracket ({str(e)[:80]}) — the prior stop "
              f"(${t['sl_price']:,.1f}) is still resting, will retry next "
              f"cycle")
        notify("⚠️ newsdesk trailing-stop update FAILED (demo)",
              f"floor moved to ${new_sl:,.0f} but the new bracket failed "
              f"to place: {str(e)[:80]} — the old stop is still "
              f"protecting the position, check BloFin")
        return

    try:
        if t.get("tpsl_id"):
            private.cancel_tpsl(SYMBOL, t["tpsl_id"])
    except Exception as e:
        print(f"  [NEWS] old bracket cancel failed after the new one was "
              f"placed ({str(e)[:80]}) — two resting stops for now, the "
              f"tighter one wins, harmless")

    print(f"  [NEWS] trailing floor ratcheted ${old_floor:,.1f} -> "
          f"${new_sl:,.1f} — exchange bracket replaced")
    log_event({"action": "news_floor_ratchet", "old_floor": old_floor,
               "new_floor": new_sl})
    t["tpsl_id"] = new_tpsl_id
    t["sl_price"] = new_sl
    t["trail_floor"] = new_floor
    save_state(state)


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    """Close the newsdesk's trade on its own ledger line. Direction-aware:
    profit on a rise when long, on a fall when short (mirrors
    shorts_lab.py's short-only math, generalized by t['direction'])."""
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["newsdesk"]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [NEWS] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "news_exit", "reason": reason,
               "trigger": "news_momentum", "direction": t["direction"],
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq, "headline": t.get("headline")})
    record_trade_outcome(state, "news_momentum", realized)
    write_lesson(state, "news_momentum", realized, t["entry_price"],
                exit_price, reason, t.get("ctx"))
    notify(f"📰 newsdesk {reason}: ${realized:+,.2f}",
          f"{side} news trade — ledger ${eq:,.2f} (demo)")
    return realized


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_newsdesk(private: BlofinDemoPrivate, live_feed, demo_feed,
                 state: dict, dry: bool = False):
    """One cycle. Returns a small summary dict, mainly for tests/smoke."""
    nd = state.setdefault("newsdesk", {"open_trade": None, "pending": None,
                                       "last_event_ts": None,
                                       "seen_headlines": []})
    t = nd.get("open_trade")
    tag = " DRY" if dry else ""

    # -- reconcile (book-aware attribution, see book_ledger.py) -----------
    net = private.net_position_contracts(SYMBOL)
    attributed = attributed_position(net, state, "newsdesk")
    unexplained = unexplained_position(net, state)
    recorded_signed = (t["direction"] * t["contracts"]) if t else 0.0
    print(f"  [NEWS{tag}] reconcile: net={net:+.2f} attributed_news="
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
        print(f"  [NEWS{tag}] our {'long' if direction > 0 else 'short'} "
              f"is gone -> {reason} @ {exit_price:,.1f}")
        if dry:
            print("  [NEWS DRY] would cancel remaining bracket orders and "
                  "book this exit — no state/order changes made")
            return {"action": "would_exit", "reason": reason,
                    "exit_price": exit_price}
        _cleanup_orders(private, SYMBOL, t)
        _book_exit(state, t, exit_price, fee_bps, reason)
        t = None
    elif not t and abs(unexplained) > LOT / 2:
        # NOT ours to adopt — the shorts lab owns adoption of unexplained
        # positions (see shorts_lab.py); we only ever warn.
        print(f"  [NEWS{tag}] unexplained net {unexplained:+.2f} ct on the "
              f"exchange — NOT adopting (that's the shorts lab's job)")

    # -- open position: 24h time exit, else self-heal the bracket ---------
    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", MAX_HOLD_H)
        if held_h >= max_hold_h:
            print(f"  [NEWS{tag}] {held_h:.0f}h >= {max_hold_h:.0f}h max "
                  f"hold -> closing")
            if dry:
                print(f"  [NEWS DRY] would market-cover {t['contracts']:.1f} "
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
        # -- round 65 N2: recompute + cancel/replace the structure-trailing
        # floor BEFORE the self-heal check, so self-heal's double-read
        # verifies the freshest bracket, not a stale one about to be
        # replaced anyway --------------------------------------------------
        _ratchet_trail_floor(private, live_feed, state, t, dry)
        if not dry:
            _ensure_bracket(private, SYMBOL, state, t)
        print(f"  [NEWS{tag}] holding {t['contracts']:.1f} ct "
              f"{'long' if t['direction'] > 0 else 'short'} from "
              f"{t['entry_price']:,.1f} ({held_h:.0f}h/{max_hold_h:.0f}h), "
              f"trailing floor ${t.get('trail_floor', t['sl_price']):,.1f}, "
              f"bracket verified")
        return {"action": "holding", "direction": t["direction"],
                "held_h": round(held_h, 1),
                "trail_floor": t.get("trail_floor", t["sl_price"])}

    # -- pending: waiting for the direction bar to close -------------------
    pending = nd.get("pending")
    if pending:
        direction_bar_open_ts = _parse_utc(pending["direction_bar_open_ts"])
        direction, bar_open, bar_high, bar_low, bar_close = _resolve_direction(
            live_feed, direction_bar_open_ts)

        if direction is None:
            print(f"  [NEWS{tag}] pending on {pending['headline'][:60]!r} — "
                  f"waiting for the {direction_bar_open_ts:%m-%d %H:00} bar "
                  f"to close")
            return {"action": "pending", "headline": pending["headline"],
                    "direction_bar_open_ts": pending["direction_bar_open_ts"]}

        if direction == 0:
            print(f"  [NEWS{tag}] direction bar was a doji (open==close) — "
                  f"no direction, discarding pending")
            log_event({"action": "news_no_direction",
                       "headline": pending["headline"]})
            if not dry:
                nd["pending"] = None
                save_state(state)
            return {"action": "no_direction", "headline": pending["headline"]}

        # direction gate — news trades need NO champ gate (the backtest had
        # none); they must simply never physically oppose an existing net
        # position on the shared, netted exchange symbol.
        net = private.net_position_contracts(SYMBOL)   # re-read post-reconcile
        opposes = (direction > 0 and net <= -LOT / 2) or \
                  (direction < 0 and net >= LOT / 2)
        if opposes:
            msg = "news trade skipped — would oppose the ride"
            print(f"  [NEWS{tag}] {msg} (net {net:+.2f} ct, desired "
                  f"{'LONG' if direction > 0 else 'SHORT'})")
            log_event({"action": "news_skip_opposed", "net": net,
                       "direction": direction, "headline": pending["headline"]})
            if not dry:
                notify("📰 NEWSDESK skipped (demo)",
                      f"{msg} — exchange net {net:+.2f} ct. "
                      f"{pending['headline'][:100]}")
                nd["pending"] = None
                save_state(state)
            return {"action": "skipped_opposed", "net": net,
                    "direction": direction}

        notional = state["virtual_equity"] * NEWS_ALLOC * NEWS_LEV
        contracts = max(LOT, round(notional / bar_close / CONTRACT_BTC / LOT)
                        * LOT)
        side = "buy" if direction > 0 else "sell"

        if dry:
            sl_est = round(_entry_bar_extreme_stop(direction, bar_high, bar_low), 1)
            print(f"  [NEWS DRY] {'LONG' if direction > 0 else 'SHORT'} "
                  f"WOULD FIRE — {side} {contracts:.1f} ct (~${notional:,.0f} "
                  f"notional at {NEWS_LEV:.0f}x, {NEWS_ALLOC*100:.0f}% alloc) "
                  f"@ ~{bar_close:,.1f} | initial stop (structure, entry-bar "
                  f"extreme +/-{TRAIL_BUFFER_PCT}%) {sl_est:,.1f} | no "
                  f"take-profit — rides until the chart says stop | max "
                  f"hold {MAX_HOLD_H}h — NO ORDER PLACED")
            return {"action": "would_enter", "direction": direction,
                    "contracts": contracts, "entry_ref": bar_close,
                    "est_sl": sl_est, "headline": pending["headline"]}

        print(f"  [NEWS ] {'LONG' if direction > 0 else 'SHORT'} SIGNAL "
              f"(news_momentum) — {side} {contracts:.1f} ct (~${notional:,.0f} "
              f"notional at {NEWS_LEV:.0f}x sleeve leverage)")
        private.ensure_leverage(SYMBOL, NEWS_LEV, "cross")
        try:
            entry, was_maker = execute_market_clips(
                private, demo_feed, SYMBOL, side, contracts, bar_close)
        except Exception as e:
            print(f"  [NEWS ] ENTRY FAILED: {str(e)[:100]}")
            notify("⚠️ newsdesk ENTRY FAILED (demo)",
                  f"news_momentum tried to {side} but the order was "
                  f"rejected: {str(e)[:80]}. No position opened — check "
                  f"BloFin.")
            nd["pending"] = None
            save_state(state)
            return {"action": "entry_failed", "error": str(e)[:120]}

        # round 65 N2: initial stop = THIS bar's own opposite extreme, +/-
        # buffer — no take-profit, ever (see the module docstring's ROUND
        # 65 EXIT SWAP). close_side unchanged: still "sell" to protect a
        # long, "buy" to protect a short.
        sl = round(_entry_bar_extreme_stop(direction, bar_high, bar_low), 1)
        close_side = "sell" if direction > 0 else "buy"

        tpsl_id = None
        try:
            tpsl_id = private.place_tpsl(SYMBOL, close_side, contracts,
                                         None, sl)
        except Exception as e:
            print(f"  [NEWS ] SL bracket FAILED: {str(e)[:80]}")
            notify("⚠️ newsdesk bracket failed (demo)",
                  "position opened but the structure stop was not set — "
                  "check BloFin now")

        headline = pending["headline"]
        nd["open_trade"] = {
            "trigger": "news_momentum", "direction": direction,
            "contracts": contracts, "entry_price": entry,
            "entry_fee_bps": 2.0 if was_maker else 6.0,
            "entry_time": now_utc(), "tp_price": None, "sl_price": sl,
            "tpsl_id": tpsl_id, "max_hold_h": MAX_HOLD_H,
            "headline": headline, "event_ts": pending["event_ts"],
            # round 65 N2 — the entry bar's own OHLC extremes (anchors the
            # initial stop, re-derived identically every ratchet cycle) and
            # the bar's own open timestamp (locates it in the live 1h feed
            # pulled each cycle — see _compute_trail_floor).
            "entry_bar_open_ts": pending["direction_bar_open_ts"],
            "entry_bar_high": bar_high, "entry_bar_low": bar_low,
            "trail_floor": sl, "trail_k": TRAIL_K,
            "ctx": {"news": headline},
        }
        nd["pending"] = None
        save_state(state)
        log_event({"action": "news_enter", "direction": direction,
                   "fill_price": entry, "contracts": contracts,
                   "sl": sl, "maker": was_maker, "headline": headline})
        notify(f"📰 NEWSDESK {'LONG' if direction > 0 else 'SHORT'} (demo)",
              f"{side} {contracts:.1f} ct @{entry:,.0f} | stop {sl:,.0f} "
              f"(structure, entry-bar) | no take-profit — rides until the "
              f"chart says stop | 24h max hold | {headline[:100]}")
        return {"action": "entered", "direction": direction, "entry": entry,
               "contracts": contracts, "sl": sl, "headline": headline}

    # -- no trade, no pending: scan the wire for a new event ---------------
    headlines = _fetch_recent_news()
    chosen, updated_seen = _find_new_relevant(nd.get("seen_headlines", []),
                                              headlines)

    if chosen:
        event_ts = now_utc()          # see the REALITY CHECK docstring note
        direction_bar_open_ts = _direction_bar_open_ts(_parse_utc(event_ts))
        print(f"  [NEWS{tag}] relevant WatcherGuru headline -> arming, "
              f"direction bar opens {direction_bar_open_ts:%m-%d %H:00}: "
              f"{chosen[:80]!r}")
        if dry:
            print("  [NEWS DRY] would set pending — no state changes made")
            return {"action": "would_arm", "headline": chosen}
        # persist BOTH the arm and the fact that everything scanned this
        # cycle (chosen or not) has now been judged once — one save covers
        # both, so a crash between them can never split them apart.
        nd["seen_headlines"] = updated_seen
        nd["last_event_ts"] = now_utc()
        nd["pending"] = {"event_ts": event_ts, "headline": chosen,
                         "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)}
        save_state(state)
        log_event({"action": "news_armed", "headline": chosen,
                   "event_ts": event_ts,
                   "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)})
        return {"action": "armed", "headline": chosen,
                "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)}

    print(f"  [NEWS{tag}] scanned {len(headlines)} recent rows — no new "
          f"relevant WatcherGuru headline")
    if not dry:
        # nothing armed, but everything scanned still gets marked seen so
        # it is never re-judged next cycle (must be persisted here — this
        # is the ONLY place that would otherwise happen for a no-event scan).
        nd["seen_headlines"] = updated_seen
        nd["last_event_ts"] = now_utc()
        save_state(state)
    return {"action": "no_event", "scanned": len(headlines)}
