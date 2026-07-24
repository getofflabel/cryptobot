"""
step59_exit_science.py — Round 59: EXIT SCIENCE.

Wallace's thesis: structure-based exits (previous swing high, liquidity
pools, price-action structure) are MORE ACCURATE than fixed-percentage
targets. This script tests that thesis as a BEFORE/AFTER on the program's
ACTUAL LIVE entry systems — the exact conditions deployed in tactical.py
(STRIKES), newsdesk.py (NEWSDESK), gold_book.py (GOLD) — plus one clean
generic testbed (a raw BTC donchian20 breakout with no prior exit
attached). Every entry rule is held IDENTICAL to what is live; only the
EXIT MODULE is swapped. RESEARCH ONLY: writes exactly step59_exit_science.py
(this file) and step59_results.md. No commits, no live orders. Concurrent
agents own step55-58 — never touched, never imported for anything but
reading in a human's own review (this script imports nothing from them).

RUN: python3 step59_exit_science.py

======================================================================
THE FOUR LIVE ENTRIES (held fixed, exactly as deployed)
======================================================================
E1 STRIKES (tactical.py): 4h champion (strategy.vol_gated_ma, 20/100,
   gate 1.5) long AND last-closed-1h-bar RSI(3) < 15. Enter at that 1h
   bar's own close (tactical.py: "post-only limit at the 1h close" — we
   fill at the close itself, the maker best case, see COSTS below).
   INCUMBENT exit: TP +4.5% / SL -1.5% / 48h hard exit.
E2 NEWSDESK (newsdesk.py): a relevant WatcherGuru headline (classify_
   headline, imported verbatim from step45b_news_events) -> the first
   FULL 1h bar after the event (align_events-style no-lookahead) -> enter
   at THAT bar's own close, direction = that bar's close-vs-open sign.
   INCUMBENT exit: TP +2.4% / SL -1.2% / 24h hard exit.
E3 GOLD (gold_book.py): donchian20 daily breakout (close > prior 20-day
   high), long only. Twin instruments: GLD (ETF, 20y) and GC=F (COMEX
   futures, twin confirmation). INCUMBENT exit: close < EMA20, plus an
   18% crash-insurance stop (gold_book.py's CRASH_SL_PCT).
E4 BTC 1h donchian20 breakout long — a CLEAN GENERIC TESTBED. This entry
   has never been deployed with any exit of its own; there is no
   "incumbent" to quote. X0 for E4 is therefore CONSTRUCTED (not
   live-deployed) as a fair fixed-% baseline: stop = 1.5x the median
   ATR14% measured on that split's TRAIN portion only (round-17's own
   convention, reused verbatim), target = 2R, max hold 240 1h-bars
   (10 days). Stated plainly here and again in the results file so it is
   never mistaken for something already running.

======================================================================
THE SIX EXIT MODULES (long-side described; mirrored for E2's shorts)
======================================================================
X0 INCUMBENT   — each entry's live exit (or E4's constructed baseline).
X1 PREV-SWING  — target = the most recent CONFIRMED swing high above
   entry (swings(k), k=5 — see PARAMETER CHOICES). Accepted only if its
   distance from entry falls inside [1.5x, 3x] the stop distance (too
   close = bad R:R and probably noise; too far = unrealistic) — outside
   that band, fall back to the incumbent's fixed target. Stop unchanged
   from the incumbent.
X2 LIQUIDITY POOL — target = the nearest (by PRICE) cluster of >=2
   confirmed swing highs within 0.1% of each other, above entry — the
   level where stops actually pool. Same acceptance band/fallback as X1.
X3 STRUCTURE-TRAILING — no fixed target. A single ratcheting floor,
   initialized at entry to the most recent confirmed swing low (or the
   incumbent's stop distance if none exists yet), that only ever moves
   UP as new confirmed higher swing lows appear. Exit the instant price
   trades AT OR BELOW the floor intrabar (protective stop, fills at the
   floor or the bar's open if it gapped through) OR closes below it
   (the structural break) — whichever comes first. "Ride until the
   chart says stop."
X4 HYBRID — X1's structure target, but never allowed to sit closer than
   1.5x risk (bumped out to 1.5R if the structure level is nearer than
   that); take 50% off at 1x risk, move the stop on the remainder to
   breakeven, let the other 50% run to the (possibly-bumped) target.
X5 ATR-TRAILING (chandelier) — highest high since entry minus mult x
   ATR(14), ratcheting up only, exit on intrabar touch. mult in
   {2.5, 3.0}, SELECTED ON TRAIN ONLY per entry/dataset (round-17's own
   "tune on train, freeze for val" discipline, reused verbatim) — never
   picked by peeking at val. The non-structure trailing control: if X3
   beats X5, structure specifically matters, not just trailing.

PARAMETER CHOICES, STATED PLAINLY (the mandate offers sets, not a further
grid search — "select nothing... COMPARES fixed pairs"):
  swings(k): k=5 throughout (the more data-rich choice; k=8 was spot-
    checked informally on the two headline survivors as a robustness
    note, reported in prose, not as a further matrix column).
  acceptance band 1.5x-3x stop distance: read as a BAND (reject targets
    both too-close and too-far), not two variants to try — this is a
    single, fully-specified rule, needs no further choice.
  X4's "never worse than 1.5x risk" / "partial 50% at 1x risk": these
    are singular values in the mandate, not sets — used verbatim.
  X5's {2.5, 3.0}: the one true two-way choice in the round. Resolved by
    TRAIN-only selection, exactly like every stop-multiplier choice this
    repo has ever made (step41's "A x median(ATR%), computed on TRAIN
    only, held fixed" convention).

======================================================================
THE SIMULATOR — ONE clean event-driven engine, used for EVERY (E, X) pair
======================================================================
Built from scratch (backtest.py's bar-close-N -> fill-at-open-N+1
continuous-signal engine cannot express a dynamic per-trade target that
moves with confirmed swing structure). Contract:
  - entries: a list of (entry_idx, direction) pairs, computed ONCE per
    entry family per data slice, IDENTICAL across every X tested against
    it. (Their REALIZED firing times can still differ downstream between
    X modules, same as any live single-slot book: only one trade open at
    a time, so an exit module that holds a trade longer necessarily
    blocks whichever next entry-condition bar would have fired during
    that hold. The RULE is identical; which of its firings actually get
    taken is a legitimate, expected consequence of a single-slot system,
    not an entry change.)
  - one trade open at a time, exactly like every live book in this repo.
  - entry fill = the entry bar's own CLOSE (matches STRIKES' "enter at
    the 1h close" and NEWSDESK's "enter at that bar's close" verbatim;
    for E3/E4 the donchian breakout bar's own close is the fill, the
    standard convention this repo already uses for daily trend entries).
  - intrabar mechanics for stops/targets: target touched (high>=target
    for a long) fills at the target (maker fee); stop touched (low<=
    stop) fills at the stop (taker fee), ADJUSTED for a gap: if the
    bar's OPEN already traded through the stop/target level, fill AT
    THE OPEN instead (gap-through honesty, step48's own convention);
    stop and target both touched in the same bar -> STOP WINS (the
    engine-wide conservative convention, backtest.py's own rule).
  - close-triggered structural exits (X3's floor break, E3 X0's EMA20
    cross) fill AT THAT BAR'S CLOSE, taker fee (a market order once the
    close confirms the break — no resting order could have caught it
    earlier).
  - time-cap exits fill at that bar's close, taker fee.
  - costs: crypto entries (E1/E2/E4) use backtest.py's CostModel()
    default (6bp taker/2bp maker/1bp spread/2bp slip) — maker fee on
    every TARGET-side fill (2bp), taker on every STOP/structural/time
    fill (6bp, i.e. the fee side only; the modeled "already at the
    exact level" fills skip the extra spread/slippage adverse_frac,
    matching tactical.py's/newsdesk.py's OWN live _book_exit fee
    convention of {2bp maker on TP, 6bp taker on SL/time} — this
    script's crypto fee treatment is that exact convention, not backtest
    .py's separate spread-adjusted taker fill; the entry fill (identical
    across every X for a given E, so it cannot bias the X-vs-X
    comparison) is charged at the 2bp maker rate, matching "we fill
    exactly at the signal bar's own close" being the best-case maker
    scenario. This is the 4-9bps round-trip convention step41/43/45b
    already established (4bp best-case maker both sides, ~9bp realized
    blended in that prior live-shape work) — reused, not reinvented.
    Real BTC perp funding (data_bybit_BTCUSDT_funding.parquet) accrues
    while held, mean rate over the hold x hold_hours/8, signed exactly
    like backtest.py (longs pay a positive rate, shorts receive it).
    Gold (E3) uses step48_tradfi_trend's own per-instrument CostModel
    (GLD ETF: 1bp fee+1bp slip, 0 spread -> 4bp round trip; GC=F future:
    0.5bp fee+0.5bp slip -> 2bp round trip), execution "taker" only (no
    maker distinction — matches step48/step52/step55's own gold
    convention exactly), funding_bps_8h=0 (no perpetual funding on an
    ETF or a dated future).
  - equity: $10,000 start, ALL of current equity into each trade (no
    leverage, no partial sizing — matches every gauntlet script in this
    repo; live leverage is a deployment-time overlay applied AFTER a
    strategy is chosen, never inside the backtest that chooses it),
    trades compound sequentially (never overlapping, by construction).
    expectancy = mean $ pnl/trade on this compounding walk, exactly
    backtest.py's own definition. max_drawdown% is computed over the
    TRADE-level equity curve (peak-to-trough across trade boundaries,
    not intra-trade bar-by-bar) — a deliberate, stated simplification;
    it is the same resolution the mandate's own headline table asks for
    (per-trade expectancy/return/DD/hold), not a bar-level curve.

======================================================================
SIM-VALIDATION (read before trusting any number below)
======================================================================
Before running the real grid, this script reproduces ONE known number:
E1's entries + X0 (the fixed 4.5%/1.5%/48h bracket, maker execution) are
run TWO ways on the identical BTC 1h train slice — (a) through backtest.
py's own trusted run_backtest() engine (stop_pct/target_pct, execution=
"maker", the exact mechanism step41/43/45b already validated this repo
against), and (b) through this file's brand-new hand-rolled simulator.
X0 is a pure static bracket — backtest.py can express it exactly — so
the two engines SHOULD closely agree; if they don't, the new simulator
has a bug and nothing downstream can be trusted. The reproduction check
is printed first, with a numeric tolerance, and restated in step59_
results.md. (They are not expected to match to the penny: backtest.py's
maker mode fills the signal bar's close only if bar i+1 actually
"touches" that limit price and otherwise chases at a taker price on bar
i's own close, a slightly different mechanic than this file's "always
fill exactly at the signal bar's close" simplification — the two are
close cousins, not identical twins, and the tolerance is set with that
honestly stated.)
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step45b_news_events import classify_headline
from strategy import atr, rsi, vol_gated_ma

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

CRYPTO_COSTS = CostModel()                     # 6bp taker/2bp maker/1bp/2bp
CRYPTO_TARGET_FEE_BPS = CRYPTO_COSTS.maker_fee_bps     # 2.0 — target-side fills
CRYPTO_STOP_FEE_BPS = CRYPTO_COSTS.fee_bps             # 6.0 — stop/structural/time fills

GOLD_COSTS = {
    "GLD": CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                     slippage_bps=1.0, funding_bps_8h=0.0),
    "GC=F": CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                      slippage_bps=0.5, funding_bps_8h=0.0),
}

K_SWING = 5                 # swings(k) — see PARAMETER CHOICES
BAND_LO, BAND_HI = 1.5, 3.0  # acceptance band, x stop distance
CLUSTER_TOL = 0.001          # 0.1% equal-highs tolerance, X2
X4_PARTIAL_FRAC = 0.5
X4_PARTIAL_R = 1.0
X4_MIN_TARGET_R = 1.5

INITIAL_EQUITY = 10_000.0


# ===========================================================================
# generic helpers
# ===========================================================================

def split_points(n: int):
    return n, int(n * 0.6), int(n * 0.8)


def bar_hours_of(d: pd.DataFrame) -> float:
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def find_pivots(h: np.ndarray, l: np.ndarray, k: int):
    """Fractal swing pivots. A bar j is a swing high if its high is the max
    of the [j-k, j+k] window; a swing low symmetrically. CONFIRMED only
    k bars later (confirm_idx = j+k) — no lookahead: at confirm_idx the
    pivot is knowable, not before. Returns two dicts of parallel numpy
    arrays {'confirm_idx':..., 'price':...}, sorted by confirm_idx (which
    is monotonic in j, so already sorted)."""
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
        {"confirm_idx": np.array(hi_confirm, dtype=int),
         "price": np.array(hi_price, dtype=float)},
        {"confirm_idx": np.array(lo_confirm, dtype=int),
         "price": np.array(lo_price, dtype=float)},
    )


def most_recent_favorable_pivot(piv, i0: int, entry_price: float, direction: int):
    """Most RECENT (by time) confirmed-by-i0 pivot price on the favorable
    side (above entry for a long target/short stop-source, below for a
    short target). None if no such pivot exists yet."""
    idx = bisect.bisect_right(piv["confirm_idx"], i0)
    prices = piv["price"][:idx]
    for p in prices[::-1]:
        if direction > 0 and p > entry_price:
            return float(p)
        if direction < 0 and p < entry_price:
            return float(p)
    return None


def nearest_liquidity_cluster(piv, i0: int, entry_price: float, direction: int,
                              tol: float = CLUSTER_TOL):
    """Nearest-by-PRICE cluster of >=2 confirmed-by-i0 pivots within `tol`
    relative tolerance of each other, on the favorable side."""
    idx = bisect.bisect_right(piv["confirm_idx"], i0)
    prices = np.sort(piv["price"][:idx])
    if len(prices) < 2:
        return None
    clusters, cur = [], [prices[0]]
    for p in prices[1:]:
        if abs(p - cur[-1]) / cur[-1] <= tol:
            cur.append(p)
        else:
            clusters.append(cur)
            cur = [p]
    clusters.append(cur)
    levels = [float(np.mean(c)) for c in clusters if len(c) >= 2]
    if direction > 0:
        above = [lv for lv in levels if lv > entry_price]
        return min(above) if above else None
    below = [lv for lv in levels if lv < entry_price]
    return max(below) if below else None


def band_accept(target_price, entry_price, stop_dist, direction):
    if target_price is None or stop_dist <= 0:
        return None
    dist = abs(target_price - entry_price)
    if BAND_LO * stop_dist <= dist <= BAND_HI * stop_dist:
        return target_price
    return None


# ===========================================================================
# THE SIMULATOR
# ===========================================================================

class Trade:
    __slots__ = ("entry_idx", "exit_idx", "entry_time", "exit_time",
                "entry_price", "exit_price", "direction", "pnl",
                "hold_bars", "reason")

    def __init__(self, **kw):
        for k_, v in kw.items():
            setattr(self, k_, v)

    @property
    def is_win(self):
        return self.pnl > 0


def _fee_leg(equity_before, entry_price, direction, legs, entry_fee_bps,
            funding_dollars=0.0):
    """legs: list of (frac_of_position, exit_price, exit_fee_bps)."""
    pnl = -equity_before * entry_fee_bps / 10_000
    for frac, price, fee_bps in legs:
        notional = equity_before * frac
        gross = direction * (price / entry_price - 1) * notional
        fee = notional * price / entry_price * fee_bps / 10_000
        pnl += gross - fee
    pnl -= funding_dollars
    return pnl


def _gap_or_level(open_px, level, direction, side):
    """side='stop': for a long, a stop is BREACHED if low<=level; if the
    bar's OPEN already traded through it (open<=level for a long stop),
    fill at the open instead (gap-through honesty). side='target'
    symmetric on the other side."""
    if side == "stop":
        if direction > 0:
            return open_px if open_px <= level else level
        return open_px if open_px >= level else level
    else:
        if direction > 0:
            return open_px if open_px >= level else level
        return open_px if open_px <= level else level


def simulate(candles: pd.DataFrame, entries: list, exit_kind: str, param_builder,
            funding: pd.Series | None = None) -> list:
    """ONE event-driven per-trade simulator, shared by every (E, X) pair.

    candles : OHLCV frame for THIS slice only (train or val), reset_index'd.
    entries : list of (entry_idx, direction) — entry_idx is the bar whose
              own CLOSE is the fill. Only used while flat (single slot).
    exit_kind : 'static' | 'x3_structure' | 'x4_hybrid' | 'x5_atr' |
                'gold_ema'
    param_builder : callable(entry_idx, entry_price, direction) -> params
              dict for THAT trade. Per-trade, not shared, because every
              challenger exit (X1-X5) computes its levels from swing
              structure / ATR AS OF that specific entry — a fresh lookup
              each time, never a single number reused across trades.
    funding : optional per-bar funding_bps series aligned to candles (None
              for gold — no perpetual funding on an ETF/dated future).
    """
    o = candles["open"].to_numpy()
    h = candles["high"].to_numpy()
    l = candles["low"].to_numpy()
    c = candles["close"].to_numpy()
    t = pd.DatetimeIndex(candles["timestamp"])
    n = len(candles)
    fund = funding.to_numpy() if funding is not None else None
    bh = bar_hours_of(candles) if n > 1 else 1.0

    trades = []
    busy_until = -1     # bar index below which we're still holding a trade

    for entry_idx, direction in entries:
        if entry_idx <= busy_until or entry_idx >= n - 1:
            continue
        entry_price = float(c[entry_idx])
        params = param_builder(entry_idx, entry_price, direction)
        if params is None:
            continue

        result = _manage_trade(entry_idx, entry_price, direction, exit_kind,
                               params, o, h, l, c, n)
        if result is None:
            continue
        exit_idx, legs, reason = result

        hold_bars = exit_idx - entry_idx
        hold_hours = hold_bars * bh if hold_bars > 0 else bh
        mean_funding_rate = 0.0
        if fund is not None and exit_idx > entry_idx:
            mr = float(np.nanmean(fund[entry_idx + 1:exit_idx + 1]))
            if mr == mr:               # not NaN
                mean_funding_rate = mr  # bps per 8h settlement, stashed;
                                        # scaled against equity at settle time

        trades.append({
            "entry_idx": entry_idx, "exit_idx": exit_idx,
            "entry_time": t[entry_idx], "exit_time": t[exit_idx],
            "entry_price": entry_price, "direction": direction,
            "legs": legs, "reason": reason,
            "hold_bars": hold_bars, "hold_hours": hold_hours,
            "funding_rate_mean_bps": mean_funding_rate,
        })
        busy_until = exit_idx

    return trades


def _manage_trade(entry_idx, entry_price, direction, exit_kind, params,
                  o, h, l, c, n):
    """Returns (exit_idx, legs, reason) or None if the trade never resolves
    before the data ends (force-closed at the last bar's close)."""
    if exit_kind == "static":
        stop_px = entry_price * (1 - direction * params["stop_pct"] / 100)
        tgt_px = entry_price * (1 + direction * params["target_pct"] / 100)
        max_hold = params["max_hold_bars"]
        for i in range(entry_idx + 1, min(n, entry_idx + 1 + max_hold)):
            hit_stop = (l[i] <= stop_px) if direction > 0 else (h[i] >= stop_px)
            hit_tgt = (h[i] >= tgt_px) if direction > 0 else (l[i] <= tgt_px)
            if hit_stop:
                px = _gap_or_level(o[i], stop_px, direction, "stop")
                return i, [(1.0, px, CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"])], "stop"
            if hit_tgt:
                px = _gap_or_level(o[i], tgt_px, direction, "target")
                fee = CRYPTO_TARGET_FEE_BPS if params["crypto"] else params["fee_bps"]
                return i, [(1.0, px, fee)], "target"
        last = min(n - 1, entry_idx + max_hold)
        fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
        return last, [(1.0, float(c[last]), fee)], "time"

    if exit_kind == "x3_structure":
        floor_px = params["initial_floor"]
        piv = params["floor_pivots"]           # favorable-for-STOP side pivots
        max_hold = params["max_hold_bars"]
        for i in range(entry_idx + 1, min(n, entry_idx + 1 + max_hold)):
            # ratchet the floor up with any newly-confirmed higher (for a
            # long)/lower (for a short) swing on the stop side
            idx_lo = bisect.bisect_left(piv["confirm_idx"], i)
            idx_hi = bisect.bisect_right(piv["confirm_idx"], i)
            for p in piv["price"][idx_lo:idx_hi]:
                if direction > 0 and p > floor_px:
                    floor_px = float(p)
                elif direction < 0 and p < floor_px:
                    floor_px = float(p)
            hit_floor = (l[i] <= floor_px) if direction > 0 else (h[i] >= floor_px)
            if hit_floor:
                px = _gap_or_level(o[i], floor_px, direction, "stop")
                return i, [(1.0, px, CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"])], "structure stop"
            broke_close = (c[i] < floor_px) if direction > 0 else (c[i] > floor_px)
            if broke_close:
                fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
                return i, [(1.0, float(c[i]), fee)], "structure break"
        last = min(n - 1, entry_idx + max_hold)
        fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
        return last, [(1.0, float(c[last]), fee)], "time cap"

    if exit_kind == "x5_atr":
        mult = params["mult"]
        atr_arr = params["atr"]
        stop_px = params["initial_stop"]
        highest = entry_price if direction > 0 else entry_price
        max_hold = params["max_hold_bars"]
        for i in range(entry_idx + 1, min(n, entry_idx + 1 + max_hold)):
            if direction > 0:
                highest = max(highest, float(h[i]))
                trail = highest - mult * float(atr_arr[i])
                stop_px = max(stop_px, trail)
                hit = l[i] <= stop_px
            else:
                highest = min(highest, float(l[i]))
                trail = highest + mult * float(atr_arr[i])
                stop_px = min(stop_px, trail)
                hit = h[i] >= stop_px
            if hit:
                px = _gap_or_level(o[i], stop_px, direction, "stop")
                fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
                return i, [(1.0, px, fee)], "atr trail"
        last = min(n - 1, entry_idx + max_hold)
        fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
        return last, [(1.0, float(c[last]), fee)], "time cap"

    if exit_kind == "x4_hybrid":
        stop_px = entry_price * (1 - direction * params["stop_pct"] / 100)
        stop_dist = abs(entry_price - stop_px)
        partial_px = entry_price + direction * X4_PARTIAL_R * stop_dist
        final_px = params["final_target_px"]
        max_hold = params["max_hold_bars"]
        target_fee = CRYPTO_TARGET_FEE_BPS if params["crypto"] else params["fee_bps"]
        stop_fee = CRYPTO_STOP_FEE_BPS if params["crypto"] else params["fee_bps"]
        legs = []
        phase = 1
        for i in range(entry_idx + 1, min(n, entry_idx + 1 + max_hold)):
            if phase == 1:
                hit_stop = (l[i] <= stop_px) if direction > 0 else (h[i] >= stop_px)
                if hit_stop:
                    px = _gap_or_level(o[i], stop_px, direction, "stop")
                    return i, [(1.0, px, stop_fee)], "stop"
                hit_partial = (h[i] >= partial_px) if direction > 0 else (l[i] <= partial_px)
                if hit_partial:
                    px = _gap_or_level(o[i], partial_px, direction, "target")
                    legs.append((X4_PARTIAL_FRAC, px, target_fee))
                    stop_px = entry_price          # move to breakeven
                    phase = 2
                    # same-bar check on the remainder, stop (BE) wins ties
                    hit_be = (l[i] <= stop_px) if direction > 0 else (h[i] >= stop_px)
                    hit_final = (h[i] >= final_px) if direction > 0 else (l[i] <= final_px)
                    if hit_be:
                        legs.append((1 - X4_PARTIAL_FRAC, stop_px, stop_fee))
                        return i, legs, "partial + BE stop (same bar)"
                    if hit_final:
                        legs.append((1 - X4_PARTIAL_FRAC, final_px, target_fee))
                        return i, legs, "partial + final target (same bar)"
                continue
            # phase 2: breakeven-protected remainder riding to final_px
            hit_be = (l[i] <= stop_px) if direction > 0 else (h[i] >= stop_px)
            if hit_be:
                px = _gap_or_level(o[i], stop_px, direction, "stop")
                legs.append((1 - X4_PARTIAL_FRAC, px, stop_fee))
                return i, legs, "BE stop (remainder)"
            hit_final = (h[i] >= final_px) if direction > 0 else (l[i] <= final_px)
            if hit_final:
                px = _gap_or_level(o[i], final_px, direction, "target")
                legs.append((1 - X4_PARTIAL_FRAC, px, target_fee))
                return i, legs, "final target (remainder)"
        last = min(n - 1, entry_idx + max_hold)
        remain = 1.0 if phase == 1 else (1 - X4_PARTIAL_FRAC)
        legs.append((remain, float(c[last]), stop_fee))
        return last, legs, "time"

    if exit_kind == "gold_ema":
        ema = params["ema"]
        crash_stop = entry_price * (1 - params["crash_sl_pct"])
        max_hold = params["max_hold_bars"]
        for i in range(entry_idx + 1, min(n, entry_idx + 1 + max_hold)):
            if l[i] <= crash_stop:
                px = _gap_or_level(o[i], crash_stop, direction, "stop")
                return i, [(1.0, px, params["fee_bps"])], "crash SL"
            if c[i] < ema[i]:
                return i, [(1.0, float(c[i]), params["fee_bps"])], "EMA20 cross"
        last = min(n - 1, entry_idx + max_hold)
        return last, [(1.0, float(c[last]), params["fee_bps"])], "time cap"

    raise ValueError(exit_kind)


def trades_to_stats(raw_trades, entry_fee_bps, initial_equity=INITIAL_EQUITY):
    equity = initial_equity
    curve = [equity]
    pnls, holds_h, reasons = [], [], []
    for tr in raw_trades:
        funding_dollars = (equity * tr["direction"] * tr["funding_rate_mean_bps"]
                           / 10_000 * (tr["hold_hours"] / 8.0))
        pnl = _fee_leg(equity, tr["entry_price"], tr["direction"], tr["legs"],
                      entry_fee_bps, funding_dollars)
        equity += pnl
        curve.append(equity)
        pnls.append(pnl)
        holds_h.append(tr["hold_hours"])
        reasons.append(tr["reason"])
    n = len(pnls)
    if n == 0:
        return {"n": 0, "expectancy": 0.0, "win_rate": 0.0, "total_return_pct": 0.0,
               "max_dd_pct": 0.0, "median_hold_h": 0.0, "final_equity": initial_equity,
               "reasons": {}}
    arr = np.array(pnls)
    curve_arr = np.array(curve)
    peaks = np.maximum.accumulate(curve_arr)
    dd = (curve_arr - peaks) / peaks
    reason_counts = pd.Series(reasons).value_counts().to_dict()
    return {
        "n": n, "expectancy": float(arr.mean()), "win_rate": float((arr > 0).mean()),
        "total_return_pct": (equity / initial_equity - 1) * 100,
        "max_dd_pct": float(dd.min() * 100),
        "median_hold_h": float(np.median(holds_h)),
        "final_equity": equity, "reasons": reason_counts,
    }


def verdict_for(tr_stats, va_stats):
    if tr_stats["expectancy"] > 0 and va_stats["expectancy"] > 0:
        if tr_stats["n"] >= MIN_TRAIN_TRADES and va_stats["n"] >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def most_recent_protective_pivot(piv, i0: int, entry_price: float, direction: int):
    """The most recent confirmed-by-i0 pivot on the PROTECTIVE side (below
    entry for a long's stop-source, above for a short's) — X3's 'entry-side
    swing low at entry'. Distinct from most_recent_favorable_pivot (which
    searches the profit side for X1's target)."""
    idx = bisect.bisect_right(piv["confirm_idx"], i0)
    prices = piv["price"][:idx]
    for p in prices[::-1]:
        if direction > 0 and p < entry_price:
            return float(p)
        if direction < 0 and p > entry_price:
            return float(p)
    return None


# ===========================================================================
# per-trade parameter builders — one per exit module
# ===========================================================================

def make_param_builder(exit_kind, crypto, fee_bps, incumbent_stop_pct,
                       incumbent_target_pct, max_hold_bars, piv_high=None,
                       piv_low=None, atr_arr=None, mult=None, ema_arr=None,
                       crash_sl_pct=None):
    """Returns (sim_exit_kind, build(entry_idx, entry_price, direction)).
    Every level (target, initial stop/floor) is computed FRESH per trade
    from data available strictly as-of that entry — nothing here is a
    single number reused blindly across trades except the incumbent's own
    fixed stop_pct (X1/X2/X4 explicitly keep the stop unchanged, per the
    mandate)."""
    common = dict(crypto=crypto, fee_bps=fee_bps, max_hold_bars=max_hold_bars)

    def target_side(direction):
        return piv_high if direction > 0 else piv_low

    def stop_side(direction):
        return piv_low if direction > 0 else piv_high

    if exit_kind == "X0":
        def build(entry_idx, entry_price, direction):
            return dict(common, stop_pct=incumbent_stop_pct,
                        target_pct=incumbent_target_pct)
        return "static", build

    if exit_kind in ("X1", "X2"):
        def build(entry_idx, entry_price, direction):
            stop_dist = entry_price * incumbent_stop_pct / 100
            piv = target_side(direction)
            raw = (most_recent_favorable_pivot(piv, entry_idx, entry_price, direction)
                  if exit_kind == "X1" else
                  nearest_liquidity_cluster(piv, entry_idx, entry_price, direction))
            accepted = band_accept(raw, entry_price, stop_dist, direction)
            target_pct = (abs(accepted - entry_price) / entry_price * 100
                         if accepted is not None else incumbent_target_pct)
            return dict(common, stop_pct=incumbent_stop_pct, target_pct=target_pct)
        return "static", build

    if exit_kind == "X3":
        def build(entry_idx, entry_price, direction):
            piv = stop_side(direction)
            init = most_recent_protective_pivot(piv, entry_idx, entry_price, direction)
            if init is None:
                init = entry_price * (1 - direction * incumbent_stop_pct / 100)
            return dict(common, initial_floor=init, floor_pivots=piv)
        return "x3_structure", build

    if exit_kind == "X4":
        def build(entry_idx, entry_price, direction):
            stop_dist = entry_price * incumbent_stop_pct / 100
            piv = target_side(direction)
            raw = most_recent_favorable_pivot(piv, entry_idx, entry_price, direction)
            accepted = band_accept(raw, entry_price, stop_dist, direction)
            base_target = (accepted if accepted is not None else
                          entry_price * (1 + direction * incumbent_target_pct / 100))
            base_dist = abs(base_target - entry_price)
            final_dist = max(base_dist, X4_MIN_TARGET_R * stop_dist)
            final_px = entry_price + direction * final_dist
            return dict(common, stop_pct=incumbent_stop_pct, final_target_px=final_px)
        return "x4_hybrid", build

    if exit_kind == "X5":
        def build(entry_idx, entry_price, direction):
            a = float(atr_arr[entry_idx]) if entry_idx < len(atr_arr) else float("nan")
            if not (a == a) or a <= 0:
                a = entry_price * incumbent_stop_pct / 100 / mult   # warmup fallback
            init_stop = entry_price - direction * mult * a
            return dict(common, mult=mult, atr=atr_arr, initial_stop=init_stop)
        return "x5_atr", build

    if exit_kind == "GOLD_X0":
        def build(entry_idx, entry_price, direction):
            return dict(common, ema=ema_arr, crash_sl_pct=crash_sl_pct)
        return "gold_ema", build

    raise ValueError(exit_kind)


def x5_pick_mult(train_candles, train_entries, piv_high, piv_low, atr_arr,
                 incumbent_stop_pct, max_hold_bars, crypto, fee_bps):
    """TRAIN-only selection between chandelier mult 2.5 vs 3.0 — round-17's
    'tune on train, freeze for val' convention, reused verbatim. Returns the
    winning mult (ties broken toward the tighter 2.5)."""
    best_mult, best_exp = 2.5, None
    for m in (2.5, 3.0):
        kind, build = make_param_builder("X5", crypto, fee_bps, incumbent_stop_pct,
                                         None, max_hold_bars, piv_high=piv_high,
                                         piv_low=piv_low, atr_arr=atr_arr, mult=m)
        raw = simulate(train_candles, train_entries, kind, build)
        stats = trades_to_stats(raw, CRYPTO_TARGET_FEE_BPS if crypto else fee_bps)
        if best_exp is None or stats["expectancy"] > best_exp:
            best_exp, best_mult = stats["expectancy"], m
    return best_mult


# ===========================================================================
# entry builders — the four LIVE entries, held fixed
# ===========================================================================

def align_funding_to(candles: pd.DataFrame, funding: pd.DataFrame) -> pd.Series:
    """Most recent SETTLED funding rate as of each bar's close (same
    merge_asof-backward convention as step11_round6.align_funding)."""
    bars = candles[["timestamp"]].copy()
    merged = pd.merge_asof(bars, funding, on="timestamp", direction="backward")
    return merged["funding_bps"]


def align_htf(ltf_ts: pd.Series, htf_ts: pd.Series, htf_val: np.ndarray,
              lag_hours: float) -> np.ndarray:
    """Value of the higher-timeframe series most recently CLOSED as of each
    LTF bar — i.e. the htf row whose own open satisfies
    open + htf_bar_hours <= ltf_open + ltf_bar_hours, rearranged to
    open <= ltf_open - lag_hours (lag_hours = htf_bar_hours - ltf_bar_hours).
    Both series are already timestamp-sorted ascending, so a plain
    merge_asof(direction='backward') on that shifted key is correct and
    needs no re-sorting."""
    key = pd.DataFrame({"asof": ltf_ts - pd.Timedelta(hours=lag_hours)})
    htf_df = pd.DataFrame({"asof": htf_ts, "val": htf_val})
    merged = pd.merge_asof(key, htf_df, on="asof", direction="backward")
    return merged["val"].to_numpy()


def build_e1_entries(btc1h: pd.DataFrame, btc4h: pd.DataFrame):
    """STRIKES: 4h champion (vol_gated_ma 20/100, gate 1.5) long AND the
    last-closed 1h bar's RSI(3) < 15. Fill at that 1h bar's own close."""
    champ4h = vol_gated_ma(btc4h, fast=20, slow=100, min_atr_pct=1.5)
    champ_on_1h = align_htf(btc1h["timestamp"], btc4h["timestamp"],
                            champ4h.fillna(0).to_numpy(), lag_hours=3.0)
    r3 = rsi(btc1h["close"], 3).fillna(50.0).to_numpy()
    entries = []
    for i in range(len(btc1h)):
        cv = champ_on_1h[i]
        if cv == cv and cv == 1 and r3[i] < 15:
            entries.append((i, 1))
    return entries


def build_e2_entries(btc1h_slice: pd.DataFrame, news: pd.DataFrame):
    """NEWSDESK: a relevant WatcherGuru headline -> the first FULL 1h bar
    after the event (align_events-style, verbatim from step45b/newsdesk) ->
    enter at THAT bar's own close, direction = its close-vs-open sign.

    `news` = data_watcherguru_history.parquet, harvested DIRECTLY from
    https://t.me/s/WatcherGuru (step45b's own Phase 1) — every row IS
    already a WatcherGuru post, unlike the LIVE Supabase RPC newsdesk.py
    reads (a many-source mixed feed where a literal '[WatcherGuru]' text
    prefix is the only way to isolate their posts). No prefix filter is
    needed or applied here; classify_headline's relevance gate is the only
    filter, applied to every harvested row."""
    relevant_mask = news["text"].apply(lambda t: classify_headline(t).get("relevant", False))
    relevant_ts = pd.DatetimeIndex(sorted(news[relevant_mask]["utc_timestamp"]))
    if len(relevant_ts) == 0:
        return []
    ts_vals = btc1h_slice["timestamp"].to_numpy()
    ev_vals = relevant_ts.to_numpy()
    floor_idx = np.searchsorted(ts_vals, ev_vals, side="right") - 1
    valid = (floor_idx >= 0) & (floor_idx < len(ts_vals) - 1)
    trading_idx = floor_idx[valid] + 1

    o = btc1h_slice["open"].to_numpy()
    c = btc1h_slice["close"].to_numpy()
    entries, seen = [], set()
    for idx in sorted(set(int(x) for x in trading_idx)):
        if idx in seen or idx >= len(o):
            continue
        seen.add(idx)
        if c[idx] > o[idx]:
            entries.append((idx, 1))
        elif c[idx] < o[idx]:
            entries.append((idx, -1))
        # doji (open==close): no direction, matches newsdesk.py's own
        # "discard pending" rule — no entry.
    return entries


def load_data():
    btc1h = pd.read_parquet("data_bybit_BTCUSDT_1h_full.parquet")
    btc4h = pd.read_parquet("data_bybit_BTCUSDT_4h_full.parquet")
    funding = pd.read_parquet("data_bybit_BTCUSDT_funding.parquet")
    gld = pd.read_parquet("data_tradfi_GLD_1d.parquet")
    gcf = pd.read_parquet("data_tradfi_GCF_1d.parquet")
    news = pd.read_parquet("data_watcherguru_history.parquet")
    return dict(btc1h=btc1h, btc4h=btc4h, funding=funding, gld=gld, gcf=gcf, news=news)


def build_donchian_entries(d: pd.DataFrame, n: int = 20):
    """E3/E4's shared entry rule: close breaks above the prior n-bar high
    (shift(1)-disciplined, the breakout bar is never inside its own
    window), long only. Fires on every qualifying bar; simulate()'s
    single-slot rule (only while flat) does the rest."""
    hi = d["high"].rolling(n).max().shift(1).to_numpy()
    close = d["close"].to_numpy()
    entries = []
    for i in range(len(d)):
        if hi[i] == hi[i] and close[i] > hi[i]:
            entries.append((i, 1))
    return entries


# ===========================================================================
# family runners — one crypto template (E1/E2/E4), one gold template (E3)
# ===========================================================================

EXIT_KINDS = ("X0", "X1", "X2", "X3", "X4", "X5")


def run_family_crypto(full_candles: pd.DataFrame, entries_all: list,
                      incumbent_stop_pct: float, incumbent_target_pct: float,
                      incumbent_max_hold_bars: int, funding_full: pd.Series | None,
                      dynamic_cap_mult: int = 4, constructed: bool = False):
    """One BTC-perp entry family (E1, E2, or E4) through all six exit
    modules, train + val. `constructed=True` (E4 only) derives the
    'incumbent' stop/target from 1.5x TRAIN-median-ATR% / 2R — see the
    module docstring's E4 section — instead of using a literal live
    number, because E4 has no live exit to inherit."""
    n, i_tr, i_va = split_points(len(full_candles))
    train_c = full_candles.iloc[0:i_tr].reset_index(drop=True)
    val_c = full_candles.iloc[i_tr:i_va].reset_index(drop=True)
    train_entries = [(i, d) for i, d in entries_all if i < i_tr]
    val_entries = [(i - i_tr, d) for i, d in entries_all if i_tr <= i < i_va]
    fund_train = (funding_full.iloc[0:i_tr].reset_index(drop=True)
                 if funding_full is not None else None)
    fund_val = (funding_full.iloc[i_tr:i_va].reset_index(drop=True)
               if funding_full is not None else None)

    if constructed:
        atr_pct_train = atr(train_c, 14) / train_c["close"] * 100
        incumbent_stop_pct = float(1.5 * atr_pct_train.median())
        incumbent_target_pct = float(2.0 * incumbent_stop_pct)

    meta = {}
    for slice_name, c_slice, ents, fund in (
        ("train", train_c, train_entries, fund_train),
        ("val", val_c, val_entries, fund_val),
    ):
        h, l = c_slice["high"].to_numpy(), c_slice["low"].to_numpy()
        piv_high, piv_low = find_pivots(h, l, K_SWING)
        atr_arr = atr(c_slice, 14).to_numpy()
        meta[slice_name] = dict(piv_high=piv_high, piv_low=piv_low, atr_arr=atr_arr,
                                candles=c_slice, entries=ents, funding=fund)

    mult = x5_pick_mult(meta["train"]["candles"], meta["train"]["entries"],
                        meta["train"]["piv_high"], meta["train"]["piv_low"],
                        meta["train"]["atr_arr"], incumbent_stop_pct,
                        incumbent_max_hold_bars * dynamic_cap_mult, True,
                        CRYPTO_STOP_FEE_BPS)

    out = {}
    for exit_kind in EXIT_KINDS:
        row = {}
        for slice_name in ("train", "val"):
            m = meta[slice_name]
            mh = (incumbent_max_hold_bars * dynamic_cap_mult
                 if exit_kind in ("X3", "X5") else incumbent_max_hold_bars)
            kind, build = make_param_builder(
                exit_kind, True, CRYPTO_STOP_FEE_BPS, incumbent_stop_pct,
                incumbent_target_pct, mh, piv_high=m["piv_high"],
                piv_low=m["piv_low"], atr_arr=m["atr_arr"], mult=mult)
            raw = simulate(m["candles"], m["entries"], kind, build, funding=m["funding"])
            row[slice_name] = trades_to_stats(raw, CRYPTO_TARGET_FEE_BPS)
        row["verdict"] = verdict_for(row["train"], row["val"])
        out[exit_kind] = row
    out["_stop_pct"] = incumbent_stop_pct
    out["_target_pct"] = incumbent_target_pct
    out["_max_hold_bars"] = incumbent_max_hold_bars
    out["_x5_mult"] = mult
    return out


GOLD_MAX_HOLD_DAYS = 500   # generous safety cap for structural/EMA exits —
                          # near-never binding in practice (see docstring)


def run_family_gold(instrument: str, d: pd.DataFrame, crash_sl_pct: float = 0.18,
                    ema_n: int = 20, entry_n: int = 20):
    """E3 GOLD: donchian20 breakout entry, six exits, one instrument (GLD
    or GC=F — call twice, once per twin). X0 is the LITERAL live incumbent
    (close < EMA20, 18% crash SL) — untouched. X1/X2/X3/X4/X5 need a well-
    defined risk (stop) DISTANCE to size their bands/partials/warmup
    fallback against, which the real incumbent doesn't cleanly offer (its
    only 'stop' is the far-away 18% disaster insurance); for THOSE five
    modules only, a stop distance is CONSTRUCTED the same way E4's is
    (1.5x TRAIN-median-ATR%) — stated here loudly, restated in the results
    file, never confused with a live number."""
    costs = GOLD_COSTS[instrument]
    fee_bps = costs.fee_bps
    entries_all = build_donchian_entries(d, entry_n)
    n, i_tr, i_va = split_points(len(d))
    train_c = d.iloc[0:i_tr].reset_index(drop=True)
    val_c = d.iloc[i_tr:i_va].reset_index(drop=True)
    train_entries = [(i, dd) for i, dd in entries_all if i < i_tr]
    val_entries = [(i - i_tr, dd) for i, dd in entries_all if i_tr <= i < i_va]

    meta = {}
    for slice_name, c_slice, ents in (("train", train_c, train_entries),
                                      ("val", val_c, val_entries)):
        h, l = c_slice["high"].to_numpy(), c_slice["low"].to_numpy()
        piv_high, piv_low = find_pivots(h, l, K_SWING)
        atr_arr = atr(c_slice, 14).to_numpy()
        ema_arr = c_slice["close"].ewm(span=ema_n, adjust=False).mean().to_numpy()
        meta[slice_name] = dict(piv_high=piv_high, piv_low=piv_low, atr_arr=atr_arr,
                                ema_arr=ema_arr, candles=c_slice, entries=ents)

    atr_pct_train = atr(train_c, 14) / train_c["close"] * 100
    stop_pct = float(1.5 * atr_pct_train.median())
    target_pct = float(2.0 * stop_pct)

    mult = x5_pick_mult(meta["train"]["candles"], meta["train"]["entries"],
                        meta["train"]["piv_high"], meta["train"]["piv_low"],
                        meta["train"]["atr_arr"], stop_pct, GOLD_MAX_HOLD_DAYS,
                        False, fee_bps)

    out = {}
    for exit_kind in EXIT_KINDS:
        row = {}
        for slice_name in ("train", "val"):
            m = meta[slice_name]
            if exit_kind == "X0":
                kind, build = make_param_builder(
                    "GOLD_X0", False, fee_bps, stop_pct, target_pct,
                    GOLD_MAX_HOLD_DAYS, ema_arr=m["ema_arr"], crash_sl_pct=crash_sl_pct)
            else:
                kind, build = make_param_builder(
                    exit_kind, False, fee_bps, stop_pct, target_pct,
                    GOLD_MAX_HOLD_DAYS, piv_high=m["piv_high"], piv_low=m["piv_low"],
                    atr_arr=m["atr_arr"], mult=mult)
            raw = simulate(m["candles"], m["entries"], kind, build, funding=None)
            row[slice_name] = trades_to_stats(raw, fee_bps)
        row["verdict"] = verdict_for(row["train"], row["val"])
        out[exit_kind] = row
    out["_stop_pct"] = stop_pct
    out["_target_pct"] = target_pct
    out["_x5_mult"] = mult
    out["_crash_sl_pct"] = crash_sl_pct
    return out


# ===========================================================================
# sim-validation — reproduce backtest.py's own numbers before trusting
# this file's brand-new simulator (see module docstring)
# ===========================================================================

def sim_validation_check(btc1h_full: pd.DataFrame, btc4h_full: pd.DataFrame):
    entries_all = build_e1_entries(btc1h_full, btc4h_full)
    n, i_tr, i_va = split_points(len(btc1h_full))
    train_c = btc1h_full.iloc[0:i_tr].reset_index(drop=True)
    train_entries_raw = [(i, d) for i, d in entries_all if i < i_tr]

    # (a) THIS file's new simulator, X0 (the literal incumbent bracket),
    #     funding OMITTED on both sides of this check so it isolates the
    #     EXIT-MECHANICS agreement, not the funding-approximation.
    kind, build = make_param_builder("X0", True, CRYPTO_STOP_FEE_BPS, 1.5, 4.5, 48)
    my_trades = simulate(train_c, train_entries_raw, kind, build, funding=None)
    my_stats = trades_to_stats(my_trades, CRYPTO_TARGET_FEE_BPS)

    # (b) backtest.py's own trusted engine, replaying the SAME realized
    #     entry/exit windows (signal=1 for [entry_idx, entry_idx+48) per
    #     trade THIS simulator actually took — guaranteed non-overlapping,
    #     they came from this same single-slot engine) — backtest.py finds
    #     its own stop/target fills inside each window with ITS mechanics.
    sig = np.zeros(len(train_c))
    for tr in my_trades:
        # window = [entry_idx, exit_idx) — leaves sig[exit_idx]=0, a real
        # flat bar between consecutive trades (backtest.py's stopped_out
        # re-entry guard needs to SEE a 0 to reset), while bar exit_idx
        # itself still runs backtest.py's own intrabar stop/target check
        # (the signal-driven flatten only lands at exit_idx+1's open) —
        # so backtest.py gets a genuine chance to find the SAME exit
        # independently, via its own mechanics, inside this window.
        end = min(len(train_c), tr["exit_idx"])
        sig[tr["entry_idx"]:end] = 1.0
    sig_series = pd.Series(sig, index=train_c.index)
    no_funding_costs = CostModel(fee_bps=CRYPTO_COSTS.fee_bps,
                                 maker_fee_bps=CRYPTO_COSTS.maker_fee_bps,
                                 half_spread_bps=CRYPTO_COSTS.half_spread_bps,
                                 slippage_bps=CRYPTO_COSTS.slippage_bps,
                                 funding_bps_8h=0.0)
    bt_result = run_backtest(train_c, sig_series, costs=no_funding_costs,
                             execution="maker", stop_pct=1.5, target_pct=4.5)
    return my_stats, bt_result


# ===========================================================================
# k=8 robustness spot-check (prose footnote, not a further matrix column —
# see PARAMETER CHOICES in the module docstring)
# ===========================================================================

def k8_check(candles: pd.DataFrame, entries: list, exit_kind: str,
            stop_pct: float, target_pct: float, max_hold: int, crypto: bool,
            fee_bps: float, funding: pd.Series | None = None):
    h, l = candles["high"].to_numpy(), candles["low"].to_numpy()
    piv_high, piv_low = find_pivots(h, l, 8)
    atr_arr = atr(candles, 14).to_numpy()
    kind, build = make_param_builder(exit_kind, crypto, fee_bps, stop_pct,
                                     target_pct, max_hold, piv_high=piv_high,
                                     piv_low=piv_low, atr_arr=atr_arr, mult=3.0)
    raw = simulate(candles, entries, kind, build, funding=funding)
    fee = CRYPTO_TARGET_FEE_BPS if crypto else fee_bps
    return trades_to_stats(raw, fee)


# ===========================================================================
# reporting
# ===========================================================================

def fmt_row(label, tr, va):
    return (f"{label:<10} train n={tr['n']:>4}  exp ${tr['expectancy']:>8,.2f}  "
           f"ret {tr['total_return_pct']:>7.1f}%  dd {tr['max_dd_pct']:>6.1f}%  "
           f"hold {tr['median_hold_h']:>6.1f}h  ||  "
           f"val n={va['n']:>4}  exp ${va['expectancy']:>8,.2f}  "
           f"ret {va['total_return_pct']:>7.1f}%  dd {va['max_dd_pct']:>6.1f}%")


def print_family(name, res, incumbent_label="X0"):
    print(f"\n--- {name} ---")
    for x in EXIT_KINDS:
        tr, va = res[x]["train"], res[x]["val"]
        tag = "  <== incumbent" if x == incumbent_label else ""
        print(fmt_row(x, tr, va) + f"  [{res[x]['verdict']}]{tag}")


def md_matrix_row(x_label, x_desc, tr, va, verdict):
    return (f"| {x_label} | {x_desc} | {tr['n']} | ${tr['expectancy']:+,.2f} "
           f"| {tr['total_return_pct']:+.1f}% | {tr['max_dd_pct']:.1f}% "
           f"| {tr['median_hold_h']:.1f}h | {va['n']} | ${va['expectancy']:+,.2f} "
           f"| {va['total_return_pct']:+.1f}% | {va['max_dd_pct']:.1f}% "
           f"| {verdict} |\n")


X_DESC = {
    "X0": "incumbent (live)",
    "X1": "prev-swing target",
    "X2": "liquidity-pool target",
    "X3": "structure-trailing",
    "X4": "hybrid (partial+BE)",
    "X5": "ATR chandelier trail",
}


def matrix_md(fam_name, res):
    out = [f"### {fam_name}\n\n",
          "| exit | description | tr n | tr exp | tr ret | tr DD | tr hold "
          "| va n | va exp | va ret | va DD | verdict |\n",
          "|---|---|---|---|---|---|---|---|---|---|---|---|\n"]
    for x in EXIT_KINDS:
        out.append(md_matrix_row(x, X_DESC[x], res[x]["train"], res[x]["val"],
                                 res[x]["verdict"]))
    out.append("\n")
    return "".join(out)


def challenger_beats_incumbent(res):
    """Challengers (X1-X5) beating X0 on BOTH train and val expectancy —
    never a look-taking trigger by itself, just the ranked candidate list
    the mandate asks for. Sealed test is never touched by this script."""
    x0 = res["X0"]
    winners = []
    for x in ("X1", "X2", "X3", "X4", "X5"):
        tr, va = res[x]["train"], res[x]["val"]
        if (tr["expectancy"] > x0["train"]["expectancy"]
                and va["expectancy"] > x0["val"]["expectancy"]
                and va["expectancy"] > 0):
            winners.append((x, tr["expectancy"] - x0["train"]["expectancy"],
                            va["expectancy"] - x0["val"]["expectancy"]))
    return winners


def main():
    print("=" * 78)
    print("ROUND 59 — EXIT SCIENCE: structure-based vs fixed-% exits")
    print("=" * 78)

    data = load_data()
    btc1h, btc4h, funding, gld, gcf, news = (data["btc1h"], data["btc4h"],
                                             data["funding"], data["gld"],
                                             data["gcf"], data["news"])

    print("\n" + "=" * 78)
    print("SIM-VALIDATION — reproducing backtest.py's own numbers first")
    print("=" * 78)
    my_stats, bt_result = sim_validation_check(btc1h, btc4h)
    print(f"  this file's new simulator : n={my_stats['n']:>4}  "
         f"exp ${my_stats['expectancy']:+.2f}  win% {my_stats['win_rate']*100:.1f}  "
         f"ret {my_stats['total_return_pct']:+.1f}%")
    print(f"  backtest.py (trusted)     : n={len(bt_result.trades):>4}  "
         f"exp ${bt_result.expectancy:+.2f}  win% {bt_result.win_rate*100:.1f}  "
         f"ret {bt_result.total_return_pct:+.1f}%")
    n_match = my_stats["n"] == len(bt_result.trades)
    win_match = abs(my_stats["win_rate"] - bt_result.win_rate) < 0.005
    exp_ratio = (my_stats["expectancy"] / bt_result.expectancy
                if bt_result.expectancy else float("nan"))
    print(f"  trade count match: {n_match}  |  win-rate match: {win_match}  |  "
         f"expectancy ratio (new/trusted): {exp_ratio:.2f}x")
    sim_validated = n_match and win_match and 0.5 < exp_ratio < 2.0
    print(f"  VERDICT: simulator {'VALIDATED' if sim_validated else 'NOT VALIDATED — STOP'}")
    if not sim_validated:
        raise SystemExit("sim-validation failed — refusing to trust downstream numbers")

    print("\n" + "=" * 78)
    print("E1 STRIKES — 4h champion + 1h RSI3<15, TP4.5/SL1.5/48h incumbent")
    print("=" * 78)
    fund1 = align_funding_to(btc1h, funding)
    entries1 = build_e1_entries(btc1h, btc4h)
    print(f"  {len(entries1)} raw trigger bars over {len(btc1h)} 1h bars "
         f"({btc1h['timestamp'].iloc[0]:%Y-%m-%d} -> {btc1h['timestamp'].iloc[-1]:%Y-%m-%d})")
    res1 = run_family_crypto(btc1h, entries1, 1.5, 4.5, 48, fund1)
    print_family("E1 STRIKES", res1)

    print("\n" + "=" * 78)
    print("E2 NEWSDESK — WatcherGuru event momentum, TP2.4/SL1.2/24h incumbent")
    print("=" * 78)
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h["timestamp"] >= news_min - pd.Timedelta(hours=24))
           & (btc1h["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    btc1h_news = btc1h[mask].reset_index(drop=True)
    print(f"  news span: {news_min:%Y-%m-%d} -> {news_max:%Y-%m-%d} "
         f"({(news_max - news_min).days} days) -> {len(btc1h_news)} 1h bars sliced")
    entries2 = build_e2_entries(btc1h_news, news)
    fund2 = align_funding_to(btc1h_news, funding)
    print(f"  {len(entries2)} directional entries from "
         f"{news['text'].apply(lambda t: classify_headline(t).get('relevant', False)).sum()} "
         f"relevant headlines")
    res2 = run_family_crypto(btc1h_news, entries2, 1.2, 2.4, 24, fund2)
    print_family("E2 NEWSDESK", res2)

    print("\n" + "=" * 78)
    print("E3 GOLD — donchian20 daily breakout, EMA20/18%SL incumbent (2 twins)")
    print("=" * 78)
    res3_gld = run_family_gold("GLD", gld)
    print_family("E3 GOLD (GLD)", res3_gld)
    res3_gcf = run_family_gold("GC=F", gcf)
    print_family("E3 GOLD (GC=F)", res3_gcf)

    print("\n" + "=" * 78)
    print("E4 BTC 1h donchian20 breakout — clean generic testbed, X0 CONSTRUCTED")
    print("=" * 78)
    entries4 = build_donchian_entries(btc1h, 20)
    print(f"  {len(entries4)} raw breakout bars")
    res4 = run_family_crypto(btc1h, entries4, None, None, 240, fund1, constructed=True)
    print(f"  constructed X0: stop {res4['_stop_pct']:.2f}% / "
         f"target {res4['_target_pct']:.2f}% / max_hold 240h (10d)")
    print_family("E4 BTC donchian20", res4)

    print("\n" + "=" * 78)
    print("k=8 ROBUSTNESS SPOT-CHECK (prose footnote, not a further column)")
    print("=" * 78)
    n_g, i_tr_g, i_va_g = split_points(len(gld))
    gld_train, gld_val = gld.iloc[0:i_tr_g].reset_index(drop=True), gld.iloc[i_tr_g:i_va_g].reset_index(drop=True)
    gld_entries_all = build_donchian_entries(gld, 20)
    gld_tr_ent = [(i, d) for i, d in gld_entries_all if i < i_tr_g]
    gld_va_ent = [(i - i_tr_g, d) for i, d in gld_entries_all if i_tr_g <= i < i_va_g]
    k8_tr = k8_check(gld_train, gld_tr_ent, "X1", res3_gld["_stop_pct"],
                     res3_gld["_target_pct"], GOLD_MAX_HOLD_DAYS, False,
                     GOLD_COSTS["GLD"].fee_bps)
    k8_va = k8_check(gld_val, gld_va_ent, "X1", res3_gld["_stop_pct"],
                     res3_gld["_target_pct"], GOLD_MAX_HOLD_DAYS, False,
                     GOLD_COSTS["GLD"].fee_bps)
    print(f"  GLD X1 k=8: train n={k8_tr['n']} exp ${k8_tr['expectancy']:+.2f} | "
         f"val n={k8_va['n']} exp ${k8_va['expectancy']:+.2f}  "
         f"(k=5 was train ${res3_gld['X1']['train']['expectancy']:+.2f} / "
         f"val ${res3_gld['X1']['val']['expectancy']:+.2f})")

    n1, i_tr1, i_va1 = split_points(len(btc1h))
    btc1h_train, btc1h_val = btc1h.iloc[0:i_tr1].reset_index(drop=True), btc1h.iloc[i_tr1:i_va1].reset_index(drop=True)
    e1_tr_ent = [(i, d) for i, d in entries1 if i < i_tr1]
    e1_va_ent = [(i - i_tr1, d) for i, d in entries1 if i_tr1 <= i < i_va1]
    fund1_tr = align_funding_to(btc1h_train, funding)
    fund1_va = align_funding_to(btc1h_val, funding)
    k8_tr_e1 = k8_check(btc1h_train, e1_tr_ent, "X3", res1["_stop_pct"],
                        res1["_target_pct"], res1["_max_hold_bars"] * 4, True,
                        CRYPTO_STOP_FEE_BPS, funding=fund1_tr)
    k8_va_e1 = k8_check(btc1h_val, e1_va_ent, "X3", res1["_stop_pct"],
                        res1["_target_pct"], res1["_max_hold_bars"] * 4, True,
                        CRYPTO_STOP_FEE_BPS, funding=fund1_va)
    print(f"  E1 X3 k=8: train n={k8_tr_e1['n']} exp ${k8_tr_e1['expectancy']:+.2f} | "
         f"val n={k8_va_e1['n']} exp ${k8_va_e1['expectancy']:+.2f}  "
         f"(k=5 was train ${res1['X3']['train']['expectancy']:+.2f} / "
         f"val ${res1['X3']['val']['expectancy']:+.2f})")

    return dict(my_stats=my_stats, bt_result=bt_result, res1=res1, res2=res2,
               res3_gld=res3_gld, res3_gcf=res3_gcf, res4=res4,
               k8=dict(gld_x1_train=k8_tr, gld_x1_val=k8_va,
                      e1_x3_train=k8_tr_e1, e1_x3_val=k8_va_e1),
               entries1=entries1, entries2=entries2, entries4=entries4,
               btc1h=btc1h, btc4h=btc4h, gld=gld, gcf=gcf, news=news)


if __name__ == "__main__":
    main()
