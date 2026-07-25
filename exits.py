"""
exits.py — ROUND 99, PART 1: THE EXIT LIBRARY.

Wallace, 2026-07-25: "Do research on how to take a stop loss and how to
take a take profit, and then start backtesting them until you find every
single way that for every single different scenario that it works in...
there's no point of coming back to me with some fast result, not having
done your thorough work."

And the central correction that governs every function in this file:

    "The stop loss is not supposed to be placed depending on thirty percent
     or fifty percent. It's supposed to be stopped based on the CHART.
     There's targets on the chart such as a higher high or higher low,
     where you're like, okay, if it crosses this line it's probably gonna
     continue going down. That's where you cut the trade."

A stop is a LEVEL where the idea is proven wrong. A target is a LEVEL
where the idea's objective is reached. Neither is a tuned percentage.
The one percentage-based stop in this file (stop_percentage) exists
ONLY as the naive control everything else has to beat — see its
docstring, which says so loudly a second time.

THIS ROUND BUILDS THE LIBRARY, NOT THE VERDICT. No backtest engine lives
here, no costs, no verdicts on which exit wins. That is round 99 part 2.
This file's only job: every stop and target method, implemented ONCE,
correctly, with no lookahead, unit-tested, and freely COMPOSABLE — any
stop pairs with any target, because nothing here hardcodes a pairing
table the way step59_exit_science.py's X0-X5 did.

======================================================================
ARCHITECTURE
======================================================================
1. SeriesCtx — precomputed, once per candle dataset: pivots (wick AND
   close variants), ATR, Bollinger bands, liquidity pools. Building this
   is the only "expensive" step; every stop/target lookup after that is
   cheap.
2. TradeCtx — a SeriesCtx plus one trade's (entry_idx, entry_price,
   direction). Cheap to build, one per trade.
3. ExitMethod — the atomic unit. Wraps a `level_fn(trade_ctx, i) ->
   price|None`, a trigger `style` ("intrabar" / "close" /
   "intrabar_or_close"), and OPTIONALLY an `event_fn(trade_ctx, i) ->
   bool` for methods that are not a price level at all (time stop,
   opposite-signal exit). `level_fn` is a PURE function of
   (trade_ctx, i): it may read trade_ctx's arrays only up to index i.
   That purity is what makes every method's no-lookahead property
   mechanically provable (see self_test_causality() and
   test_exits.py's truncation test) — proof by construction, not by
   promise.
4. run_trade(trade_ctx, stop, target, max_hold_bars) — the ONE generic
   engine that walks a trade forward and asks each method "did you fire
   at bar i, and at what price" using the SAME hit-detection/gap-through/
   stop-wins-ties rules for every combination. ANY ExitMethod built for
   the stop role can sit in the stop slot of ANY OTHER pair; same for
   targets. This is what "methods must compose" means in code, not just
   in prose.
5. simulate_partial_scale(...) — the one exit that is inherently
   two-legged (take half at 1R, move stop to breakeven, trail/target the
   rest) and so cannot be expressed as a single ExitMethod; it composes
   an ExitMethod for its stop and an ExitMethod for its final target
   exactly like run_trade does, it just has two phases.
6. classify_regime(...) — the causal regime/volatility label for an
   entry bar, reusing chart_reader.py's structure/quality/momentum reads
   rather than inventing a second vocabulary.
7. describe_distance(...) — every distance reported as BOTH price% and
   margin% at a given leverage, per BLOFIN_API_REFERENCE.md's
   convention ("5% of margin = 0.25% price move at 20x").

======================================================================
WHAT WAS REUSED VS WRITTEN NEW (also restated in step99_exit_library.md)
======================================================================
- find_pivots() / _nth_pivot() / _gap_or_level() / _nearest_liquidity_
  cluster(): ADAPTED (not imported) from step59_exit_science.py's
  find_pivots / most_recent_favorable_pivot / most_recent_protective_
  pivot / nearest_liquidity_cluster / _gap_or_level (round 59, "EXIT
  SCIENCE"). Copied rather than imported so this file stays a light,
  dependency-minimal shared library — step59_exit_science.py pulls in
  backtest.py, step45b_news_events.py and a news classifier at import
  time, appropriate for a one-off research script, wrong for a toolbox
  every future round imports. The math is IDENTICAL; only packaging
  differs, and this docstring says so instead of hiding it.
- stop_structure_trailing(): the SAME ratcheting-floor design step59's
  X3 validated (train ${...}, GOLD sealed-validated 4x its EMA20
  incumbent) AND that gold_book.py now runs LIVE via
  _compute_trail_floor()/_find_swing_lows() (K_SWING=5, "mirrors
  step59_exit_science's X3 exit EXACTLY" per that file's own docstring).
  Generalized here to both directions (gold_book's live version is
  long-only; step59's X3 already handled both — this is that same
  bidirectional design, not a rewrite).
- liquidity_pools(): IMPORTED, UNMODIFIED, from step56_smc_toolkit.py —
  used verbatim for stop_liquidity_pool()'s "beyond the swept pool"
  level (the pool made from the two most recent confirmed swings, which
  IS the pool a sweep-and-reverse entry just traded against).
- ATR: imported unmodified from strategy.py (the repo's one true ATR).
- Regime read (structure/quality/momentum): reuses chart_reader.py's
  read_chart() wholesale rather than a parallel vocabulary — see
  classify_regime().
- Causality-truncation self-test pattern: adapted from
  step84_blind_drill.py's self_test_causality() (render the same
  decision point from the full series and from a series truncated one
  bar past the decision, assert IDENTICAL output).
- New in this round: the whole ExitMethod/SeriesCtx/TradeCtx/run_trade
  composition engine, stop_atr, stop_chandelier, stop_bollinger,
  stop_moving_average, stop_breakeven_after_r, stop_time/target_time,
  target_fixed_r, target_measured_move, target_opposite_signal,
  target_trail_only, simulate_partial_scale, classify_regime,
  describe_distance.

======================================================================
CONVENTIONS CARRIED FORWARD FROM THE REST OF THIS REPO
======================================================================
- direction: +1 long, -1 short (LONG/SHORT constants below).
- Intrabar fills use the gap-through-honesty rule: if the bar's OPEN
  already traded past the level, fill at the open, not the level itself
  (step48's convention, reused verbatim in step59). A same-bar stop AND
  target both touching resolves to the STOP (the engine-wide
  conservative convention — backtest.py's own rule, restated in
  run_trade()).
- No costs, no fees, no slippage model live in this file. That is the
  backtest ENGINE's job (round 99 part 2) — this file returns bar+price,
  clean, so the engine can price it with real costs (CostModel in
  backtest.py) however it likes.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

import chart_reader as _chart_reader
from step56_smc_toolkit import liquidity_pools as _smc_liquidity_pools
from strategy import atr as _atr_series

LONG = 1
SHORT = -1

# far-future "now" so chart_reader.read_chart() never treats a historical
# window's last bar as "still forming" — ported verbatim from
# step84_blind_drill.py's eye_read_at()/_FAR_FUTURE convention.
_FAR_FUTURE = pd.Timestamp("2099-01-01", tz="UTC")

BASELINE_METHODS = frozenset({"stop_percentage"})
# Every method whose .name starts with something in this set is a NAIVE
# CONTROL, not a candidate. See stop_percentage()'s docstring.


# ===========================================================================
# 0. PIVOT / STRUCTURE PRIMITIVES
#    Adapted from step59_exit_science.py (round 59) — see module docstring
#    "WHAT WAS REUSED" section.
# ===========================================================================

def find_pivots(extreme_hi: np.ndarray, extreme_lo: np.ndarray, k: int) -> tuple[dict, dict]:
    """Fractal swing pivots. A bar j is a swing high if extreme_hi[j] is the
    max of the [j-k, j+k] window; a swing low symmetrically on extreme_lo.
    CONFIRMED only k bars later (confirm_idx = j+k) — no lookahead: at
    confirm_idx the pivot is knowable, not before.

    Pass (high, low) for the classic wick-based pivot, or (close, close)
    for a close-based pivot (the "wick-vs-close" parameter the mandate
    asks for on stop_structure() — see build_series_ctx(), which computes
    both variants once per dataset).

    Returns two dicts of parallel numpy arrays {'confirm_idx':...,
    'price':...}, sorted by confirm_idx (monotonic in j, so already
    sorted). ADAPTED VERBATIM from step59_exit_science.find_pivots()."""
    n = len(extreme_hi)
    hi_confirm, hi_price, lo_confirm, lo_price = [], [], [], []
    for j in range(k, n - k):
        wh = extreme_hi[j - k:j + k + 1]
        if extreme_hi[j] >= wh.max():
            hi_confirm.append(j + k)
            hi_price.append(extreme_hi[j])
        wl = extreme_lo[j - k:j + k + 1]
        if extreme_lo[j] <= wl.min():
            lo_confirm.append(j + k)
            lo_price.append(extreme_lo[j])
    return (
        {"confirm_idx": np.array(hi_confirm, dtype=int), "price": np.array(hi_price, dtype=float)},
        {"confirm_idx": np.array(lo_confirm, dtype=int), "price": np.array(lo_price, dtype=float)},
    )


def _nth_pivot(piv: dict, i0: int, entry_price: float, direction: int,
               side: str, n_back: int = 1) -> Optional[float]:
    """The n_back'th most RECENT (by time) confirmed-by-i0 pivot on the
    requested side. side='favorable': above entry for a long (target
    source), below for a short. side='protective': the mirror (stop
    source). n_back=1 is step59's most_recent_favorable_pivot /
    most_recent_protective_pivot; n_back=2+ generalizes to 'the Nth swing
    back', which the mandate asks stop_structure() to parameterise.
    Returns None if fewer than n_back qualifying pivots exist yet."""
    idx = bisect.bisect_right(piv["confirm_idx"], i0)
    prices = piv["price"][:idx]
    count = 0
    want_above = (direction > 0) == (side == "favorable")
    for p in prices[::-1]:
        if (want_above and p > entry_price) or ((not want_above) and p < entry_price):
            count += 1
            if count == n_back:
                return float(p)
    return None


def _nearest_liquidity_cluster(piv: dict, i0: int, entry_price: float,
                               direction: int, side: str, tol: float) -> Optional[float]:
    """Nearest-by-PRICE cluster of >=2 confirmed-by-i0 pivots within `tol`
    relative tolerance of each other, on the requested side ('favorable'
    or 'protective', see _nth_pivot). This is the "next equal-highs/
    equal-lows pool" a target or a stop should look for — the level where
    stops actually pool up in the real market. ADAPTED from
    step59_exit_science.nearest_liquidity_cluster(), generalized with a
    `side` parameter so the SAME scan serves both target_liquidity_pool()
    (favorable side) and would serve a protective-side liquidity stop if
    a future round wants one (stop_liquidity_pool() below instead reuses
    step56_smc_toolkit.liquidity_pools() directly per the mandate — see
    that function's docstring for why the two liquidity methods use two
    different underlying implementations on purpose)."""
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
    want_above = (direction > 0) == (side == "favorable")
    if want_above:
        above = [lv for lv in levels if lv > entry_price]
        return min(above) if above else None
    below = [lv for lv in levels if lv < entry_price]
    return max(below) if below else None


def _gap_or_level(open_px: float, level: float, direction: int, side: str) -> float:
    """side='stop': for a long, a stop is BREACHED if low<=level; if the
    bar's OPEN already traded through it (open<=level for a long stop),
    fill at the open instead (gap-through honesty). side='target'
    symmetric on the other side. ADAPTED VERBATIM from
    step59_exit_science._gap_or_level() (itself step48's convention)."""
    if side == "stop":
        if direction > 0:
            return open_px if open_px <= level else level
        return open_px if open_px >= level else level
    if direction > 0:
        return open_px if open_px >= level else level
    return open_px if open_px <= level else level


def _bollinger(close: pd.Series, n: int, k: float):
    """Standard Bollinger bands. Rolling stats only — causal by
    construction, each row uses only rows up to and including itself."""
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    return mid, mid + k * std, mid - k * std


# ===========================================================================
# 1. SeriesCtx / TradeCtx — precomputed context
# ===========================================================================

@dataclass
class SeriesCtx:
    """Everything every stop/target method for ONE candle dataset needs,
    computed ONCE. Building this is O(n); every ExitMethod lookup after
    that is cheap. k/atr_n/boll_n/boll_k/pool_tol_pct are fixed per
    SeriesCtx — a different k (fractal lookback) or ATR period means
    building a second SeriesCtx (cheap: build_series_ctx() again), the
    same secondary-parameter-fixing convention step41/43/45b/56/59 all
    use ("select a value, hold it fixed, state it plainly") rather than
    threading k through every single per-bar call."""
    candles: pd.DataFrame
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray
    n: int
    k: int
    atr_n: int
    atr_arr: np.ndarray
    ma_cache: dict = field(default_factory=dict)   # {n: ema array}, lazy
    piv_high: dict = None       # wick-based, confirmed at k
    piv_low: dict = None
    piv_high_close: dict = None  # close-based (the "use='close'" pivot variant)
    piv_low_close: dict = None
    boll_n: int = 20
    boll_k: float = 2.0
    boll_mid: np.ndarray = None
    boll_upper: np.ndarray = None
    boll_lower: np.ndarray = None
    pool_tol_pct: float = 0.1
    pool_high: np.ndarray = None   # step56_smc_toolkit.liquidity_pools(), verbatim
    pool_low: np.ndarray = None

    def ema(self, n: int) -> np.ndarray:
        """Lazily-cached EMA(n) of close — used by stop_moving_average().
        Causal: pandas .ewm() at row i depends only on rows <= i."""
        if n not in self.ma_cache:
            self.ma_cache[n] = self.candles["close"].ewm(span=n, adjust=False).mean().to_numpy()
        return self.ma_cache[n]


@dataclass
class TradeCtx:
    """A SeriesCtx plus one trade's identity. Every ExitMethod.level_fn
    takes (TradeCtx, i) and must only read s.{o,h,l,c,...}[<=i] (or
    pivot/pool arrays gated by confirm_idx<=i, which encodes the same
    causal guarantee — see find_pivots()'s docstring)."""
    s: SeriesCtx
    entry_idx: int
    entry_price: float
    direction: int


def build_series_ctx(candles: pd.DataFrame, k: int = 5, atr_n: int = 14,
                     boll_n: int = 20, boll_k: float = 2.0,
                     pool_tol_pct: float = 0.1) -> SeriesCtx:
    """Build a SeriesCtx from a candles DataFrame (oldest-first, open/high/
    low/close required). Pure function of `candles` — nothing here reads
    anything not inside the passed frame, which is exactly what makes the
    causality-truncation test meaningful: build_series_ctx(df.iloc[:i+1])
    must reproduce build_series_ctx(df).<field>[<=i] exactly."""
    candles = candles.reset_index(drop=True)
    o = candles["open"].to_numpy(dtype=float)
    h = candles["high"].to_numpy(dtype=float)
    l = candles["low"].to_numpy(dtype=float)
    c = candles["close"].to_numpy(dtype=float)
    n = len(candles)
    atr_arr = _atr_series(candles, atr_n).to_numpy()
    piv_high, piv_low = find_pivots(h, l, k)
    piv_high_close, piv_low_close = find_pivots(c, c, k)
    boll_mid, boll_upper, boll_lower = _bollinger(candles["close"], boll_n, boll_k)
    pool_high, pool_low = _smc_liquidity_pools(candles, k, pool_tol_pct)
    return SeriesCtx(
        candles=candles, o=o, h=h, l=l, c=c, n=n, k=k, atr_n=atr_n, atr_arr=atr_arr,
        piv_high=piv_high, piv_low=piv_low,
        piv_high_close=piv_high_close, piv_low_close=piv_low_close,
        boll_n=boll_n, boll_k=boll_k,
        boll_mid=boll_mid.to_numpy(), boll_upper=boll_upper.to_numpy(), boll_lower=boll_lower.to_numpy(),
        pool_tol_pct=pool_tol_pct, pool_high=pool_high.to_numpy(), pool_low=pool_low.to_numpy(),
    )


def build_trade_ctx(s: SeriesCtx, entry_idx: int, entry_price: float, direction: int) -> TradeCtx:
    return TradeCtx(s=s, entry_idx=entry_idx, entry_price=entry_price, direction=direction)


# ===========================================================================
# 2. ExitMethod — the atomic, composable unit
# ===========================================================================

@dataclass
class ExitMethod:
    name: str
    level_fn: Callable[[TradeCtx, int], Optional[float]]
    style: str = "intrabar"   # "intrabar" | "close" | "intrabar_or_close"
    event_fn: Optional[Callable[[TradeCtx, int], bool]] = None
    # event_fn methods (time stop, opposite-signal) ignore level_fn/style
    # entirely — see _resolve(). Fill price for an event exit is always
    # that bar's own close (a market order fired once the condition is
    # true; no resting order could have caught it earlier).

    def is_baseline(self) -> bool:
        return any(self.name.startswith(b) for b in BASELINE_METHODS)


def _resolve(method: ExitMethod, tc: TradeCtx, i: int, role: str) -> Optional[float]:
    """The ONE hit-detection routine every method goes through, regardless
    of whether it's sitting in the stop slot or the target slot. role
    only changes WHICH side of the level counts as a breach — role='stop'
    breaches on the adverse side, role='target' on the favorable side.
    This is what makes composition real: nothing here is specialized to
    a particular (stop, target) pair."""
    if method.event_fn is not None:
        return float(tc.s.c[i]) if method.event_fn(tc, i) else None

    level = method.level_fn(tc, i)
    if level is None:
        return None
    o, h, l, c = tc.s.o[i], tc.s.h[i], tc.s.l[i], tc.s.c[i]
    direction = tc.direction

    def intrabar_hit():
        if role == "stop":
            hit = (l <= level) if direction > 0 else (h >= level)
            return _gap_or_level(o, level, direction, "stop") if hit else None
        hit = (h >= level) if direction > 0 else (l <= level)
        return _gap_or_level(o, level, direction, "target") if hit else None

    def close_hit():
        if role == "stop":
            hit = (c < level) if direction > 0 else (c > level)
        else:
            hit = (c > level) if direction > 0 else (c < level)
        return float(c) if hit else None

    if method.style == "intrabar":
        return intrabar_hit()
    if method.style == "close":
        return close_hit()
    if method.style == "intrabar_or_close":
        px = intrabar_hit()
        return px if px is not None else close_hit()
    raise ValueError(f"unknown ExitMethod.style {method.style!r}")


# ===========================================================================
# 3. STOPS
# ===========================================================================

def stop_percentage(pct: float) -> ExitMethod:
    """BASELINE CONTROL, NOT A CANDIDATE. entry -/+ pct% of price, fixed at
    entry. This is exactly the "thirty percent or fifty percent" Wallace
    said IS NOT how a stop should be chosen. It exists in this file for
    exactly one reason: every other method below has to beat it, or it
    isn't earning its keep. Never present this as a recommended exit —
    label it "baseline" everywhere it appears in a results table (see
    ExitMethod.is_baseline() / BASELINE_METHODS)."""
    def level_fn(tc: TradeCtx, i: int) -> float:
        return tc.entry_price * (1 - tc.direction * pct / 100)
    return ExitMethod(f"stop_percentage(pct={pct})", level_fn, style="intrabar")


def stop_structure(k: int = 5, n_back: int = 1, buffer_pct: float = 0.0,
                   use: str = "wick") -> ExitMethod:
    """Beyond the confirmed swing low/high the entry rests on — Wallace's
    literal definition of a real stop. n_back=1: the most recent confirmed
    swing on the protective side as of entry. n_back=2+: the Nth swing
    back (a trader who wants more room than the very last pivot).
    buffer_pct: extra distance past the level (a real trader never rests
    a stop exactly ON the level everyone else's stop sits at either —
    this parameterises that choice instead of hardcoding it).
    use='wick': the classic high/low fractal pivot. use='close': a pivot
    defined on closing prices only (ignores wicks) — some traders trust
    the close, not the tail, as "where structure actually broke".
    FIXED at entry — recomputed at every i for causality-testability, but
    since it only depends on pivots confirmed by entry_idx, the returned
    level never changes across a trade's life (that's what makes it a
    STRUCTURE stop, not a STRUCTURE-TRAILING one — see the next
    function)."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        piv = ((tc.s.piv_low if tc.direction > 0 else tc.s.piv_high) if use == "wick"
              else (tc.s.piv_low_close if tc.direction > 0 else tc.s.piv_high_close))
        level = _nth_pivot(piv, tc.entry_idx, tc.entry_price, tc.direction, "protective", n_back)
        if level is None:
            return None
        return level * (1 - tc.direction * buffer_pct / 100)
    return ExitMethod(f"stop_structure(k={k},n_back={n_back},buffer_pct={buffer_pct},use={use})",
                      level_fn, style="intrabar")


def stop_structure_trailing(buffer_pct: float = 0.0, fallback_pct: float = 5.0) -> ExitMethod:
    """STRUCTURE-TRAILING: a single ratcheting floor, initialized at entry
    to the most recent confirmed swing on the protective side (or
    entry*(1-direction*fallback_pct/100) if none exists yet — the SAME
    "young data, nothing to anchor to" case gold_book.py's live floor
    handles with its CRASH_SL_PCT fallback), that only ever moves in the
    trade's favor as new confirmed swings appear beyond it — never back.
    "Ride until the chart says stop" — this IS gold_book.py's live,
    K_SWING=5 floor (_compute_trail_floor/_find_swing_lows), generalized
    here to short trades too (that book is long-only; this function's
    long branch matches it exactly, pivot-for-pivot).

    Exit fires the instant price trades AT OR BELOW the floor intrabar
    (protective stop) OR closes beyond it (the structural break itself)
    — whichever comes first (style="intrabar_or_close", step59's X3
    mechanic, restated in that file's own module docstring).

    Uses the WICK pivot variant only (SeriesCtx.piv_low/piv_high) — a
    trailing floor that could be knocked out by a single wick and then
    un-knocked-out by a close-based recompute would be incoherent; the
    close-confirmed break is a SEPARATE, second trigger on the same
    floor, not a second floor."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        piv = tc.s.piv_low if tc.direction > 0 else tc.s.piv_high
        floor = _nth_pivot(piv, tc.entry_idx, tc.entry_price, tc.direction, "protective", 1)
        if floor is None:
            floor = tc.entry_price * (1 - tc.direction * fallback_pct / 100)
        idx_hi = bisect.bisect_right(piv["confirm_idx"], i)
        for cidx, price in zip(piv["confirm_idx"][:idx_hi], piv["price"][:idx_hi]):
            if cidx <= tc.entry_idx:
                continue
            if tc.direction > 0 and price > floor:
                floor = float(price)
            elif tc.direction < 0 and price < floor:
                floor = float(price)
        return floor * (1 - tc.direction * buffer_pct / 100)
    return ExitMethod(f"stop_structure_trailing(buffer_pct={buffer_pct},fallback_pct={fallback_pct})",
                      level_fn, style="intrabar_or_close")


def stop_atr(mult: float = 1.5) -> ExitMethod:
    """entry -/+ mult x ATR(n) — n fixed by the SeriesCtx (build_series_ctx
    (..., atr_n=...)), only the multiplier varies per-call, matching this
    repo's own secondary-parameter-fixing convention. FIXED at entry
    (ATR measured at the entry bar itself, not re-measured as the trade
    ages) — the "how much room did this instrument need at the moment I
    got in" reading. For a version that keeps re-measuring room as the
    trade ages, see stop_chandelier() below, which ALSO ratchets."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        a = tc.s.atr_arr[tc.entry_idx]
        if not (a == a) or a <= 0:
            return None
        return tc.entry_price - tc.direction * mult * a
    return ExitMethod(f"stop_atr(mult={mult})", level_fn, style="intrabar")


def stop_chandelier(mult: float = 3.0) -> ExitMethod:
    """Chandelier exit: highest high since entry (lowest low for a short)
    minus (plus) mult x ATR(n), ratcheting — never gives back room once
    earned. Computed as the RUNNING MAX (long) / MIN (short) of the raw
    per-bar trail across [entry_idx, i], not just the raw trail AT bar i
    — a raw ATR expansion on a single bar must never pull the stop back
    toward price; only a genuine new high (or a genuine ATR contraction
    happening WHILE at a standing high) can tighten it, and the running-
    max formulation enforces that automatically, matching step59's own
    per-bar `stop_px = max(stop_px, trail)` ratchet exactly (a running
    max IS that same ratchet, just computed in one vectorized pass
    instead of a bar-by-bar loop — provably identical output)."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        a_slice = tc.s.atr_arr[tc.entry_idx:i + 1]
        if len(a_slice) == 0 or not np.isfinite(a_slice[-1]):
            return None
        if tc.direction > 0:
            running_high = np.maximum.accumulate(tc.s.h[tc.entry_idx:i + 1])
            trail = running_high - mult * a_slice
            return float(np.nanmax(trail))
        running_low = np.minimum.accumulate(tc.s.l[tc.entry_idx:i + 1])
        trail = running_low + mult * a_slice
        return float(np.nanmin(trail))
    return ExitMethod(f"stop_chandelier(mult={mult})", level_fn, style="intrabar")


def stop_bollinger(use: str = "opposite_band") -> ExitMethod:
    """Volatility/Bollinger stop. use='opposite_band': the band on the far
    side of price (a long's protective stop sits at the LOWER band — if
    price falls all the way back to the lower band, the volatility
    expansion that justified the entry has round-tripped). use='midline':
    the band's own moving average — a tighter, more conservative version.
    n/k fixed by the SeriesCtx (build_series_ctx(..., boll_n=, boll_k=))."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        if use == "midline":
            lvl = tc.s.boll_mid[i]
        else:
            lvl = tc.s.boll_lower[i] if tc.direction > 0 else tc.s.boll_upper[i]
        return float(lvl) if lvl == lvl else None
    return ExitMethod(f"stop_bollinger(use={use})", level_fn, style="intrabar")


def stop_moving_average(n: int = 20) -> ExitMethod:
    """close through an MA — the shape of gold_book.py's ORIGINAL (pre-
    round-59) EMA20 exit, kept here as a named, general method (any n) now
    that gold_book itself has moved to stop_structure_trailing(). style=
    "close": a moving-average cross is a CLOSE-confirmed event in every
    trend-following tradition this repo follows (a wick poking through
    the average and closing back on the right side is noise, not a
    signal)."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        v = tc.s.ema(n)[i]
        return float(v) if v == v else None
    return ExitMethod(f"stop_moving_average(n={n})", level_fn, style="close")


def stop_breakeven_after_r(base: ExitMethod, r_multiple: float = 1.0) -> ExitMethod:
    """Composer, not a standalone stop: wraps ANY other stop method and
    shifts it to breakeven (entry price) the moment the trade's maximum
    favorable excursion (MFE), measured in units of the BASE stop's own
    initial distance, reaches r_multiple — then holds breakeven forever
    after (never re-widens even if the base stop would have trailed
    further out, and never re-tightens past breakeven either — breakeven
    is a floor/ceiling on the base stop, one-directional exactly like
    every other trailing mechanism in this file). MFE is measured
    causally from tc.s.h/l[entry_idx:i+1] — a pure function of (tc, i),
    same purity guarantee as everything else here.

    This is exactly "move to breakeven after +1R, then hold" from the
    mandate, expressed as composition rather than a bespoke stop — it
    works with stop_atr, stop_structure, stop_chandelier, anything."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        base_at_entry = base.level_fn(tc, tc.entry_idx)
        if base_at_entry is None:
            return base.level_fn(tc, i)
        stop_dist = abs(tc.entry_price - base_at_entry)
        if stop_dist <= 0:
            return base.level_fn(tc, i)
        if tc.direction > 0:
            mfe = float(tc.s.h[tc.entry_idx:i + 1].max()) - tc.entry_price
        else:
            mfe = tc.entry_price - float(tc.s.l[tc.entry_idx:i + 1].min())
        if mfe >= r_multiple * stop_dist:
            base_now = base.level_fn(tc, i)
            if base_now is None:
                return tc.entry_price
            if tc.direction > 0:
                return max(tc.entry_price, base_now)
            return min(tc.entry_price, base_now)
        return base.level_fn(tc, i)
    return ExitMethod(f"stop_breakeven_after_r(base={base.name},r={r_multiple})",
                      level_fn, style=base.style)


def _event_time(n_bars: int) -> Callable[[TradeCtx, int], bool]:
    def event_fn(tc: TradeCtx, i: int) -> bool:
        return (i - tc.entry_idx) >= n_bars
    return event_fn


def stop_time(n_bars: int) -> ExitMethod:
    """Flatten after N bars regardless of price. An event method (no price
    level at all) — fires at that bar's own close, taker-side (a market
    order once the clock runs out; no resting order could have caught it
    earlier). Usable in either the stop slot OR the target slot (see
    target_time(), a documented alias) — the mandate lists "time stop"
    under STOPS and "time exit" under TARGETS; mechanically they are the
    exact same clock, so one function serves both, honestly labeled as
    such rather than duplicated."""
    return ExitMethod(f"stop_time(n_bars={n_bars})", level_fn=lambda tc, i: None,
                      event_fn=_event_time(n_bars))


def stop_liquidity_pool(buffer_pct: float = 0.0) -> ExitMethod:
    """Beyond the swept pool. Uses step56_smc_toolkit.liquidity_pools()
    DIRECTLY, unmodified — reused rather than reimplemented per the
    mandate ("step56_smc_toolkit has pool detection — reuse it"). That
    function's pool_low/pool_high (>=2 confirmed swings within
    SeriesCtx.pool_tol_pct of each other, causal/forward-filled) IS "the
    pool a sweep-and-reverse entry just traded against" — the level a
    trader who faded a stop-hunt would rest their protective stop beyond.
    FIXED at entry (read once, at entry_idx — a swept pool is a specific
    historical level, not something that should silently drift as later,
    unrelated pools form)."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        raw = tc.s.pool_low[tc.entry_idx] if tc.direction > 0 else tc.s.pool_high[tc.entry_idx]
        if raw != raw:
            return None
        return float(raw) * (1 - tc.direction * buffer_pct / 100)
    return ExitMethod(f"stop_liquidity_pool(buffer_pct={buffer_pct})", level_fn, style="intrabar")


# ===========================================================================
# 4. TARGETS
# ===========================================================================

def target_fixed_r(stop: ExitMethod, r_multiple: float) -> ExitMethod:
    """R multiple of R (R = the paired STOP's own initial distance —
    "the stop distance", exactly the mandate's definition, computed by
    calling stop.level_fn AT THE ENTRY BAR, before any trailing has had a
    chance to move it). This is the literal mechanism of composition:
    pass it whatever stop you are testing, and the target is correctly
    sized against THAT stop's risk, not a hardcoded number."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        stop_at_entry = stop.level_fn(tc, tc.entry_idx)
        if stop_at_entry is None:
            return None
        stop_dist = abs(tc.entry_price - stop_at_entry)
        if stop_dist <= 0:
            return None
        return tc.entry_price + tc.direction * r_multiple * stop_dist
    return ExitMethod(f"target_fixed_r(stop={stop.name},r={r_multiple})", level_fn, style="intrabar")


def target_structure(n_ahead: int = 1, buffer_pct: float = 0.0, use: str = "wick") -> ExitMethod:
    """The next opposing swing high/low ahead of entry — n_ahead=1: the
    nearest confirmed favorable-side swing as of entry. n_ahead=2+: skip
    past the nearest and target a further one (a trader who thinks the
    nearest level won't hold as resistance/support). FIXED at entry, same
    reasoning as stop_structure()."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        piv = ((tc.s.piv_high if tc.direction > 0 else tc.s.piv_low) if use == "wick"
              else (tc.s.piv_high_close if tc.direction > 0 else tc.s.piv_low_close))
        level = _nth_pivot(piv, tc.entry_idx, tc.entry_price, tc.direction, "favorable", n_ahead)
        if level is None:
            return None
        return level * (1 + tc.direction * buffer_pct / 100)
    return ExitMethod(f"target_structure(n_ahead={n_ahead},buffer_pct={buffer_pct},use={use})",
                      level_fn, style="intrabar")


def target_liquidity_pool(tol_pct: float = 0.1) -> ExitMethod:
    """The next equal-highs/equal-lows pool AHEAD of entry — where
    opposing stops/take-profits actually cluster, the level price tends
    to react to. Unlike stop_liquidity_pool() (which reuses step56's
    "most recent 2-swing pool" directly, exactly right for "the pool
    just swept"), a TARGET needs to search the full pivot history for
    the nearest qualifying cluster in front of price — step56's own
    liquidity_pools() only ever reports the single most-recent pair, so
    it cannot answer "what's the next one ahead". _nearest_liquidity_
    cluster() (adapted from step59_exit_science's nearest_liquidity_
    cluster, itself built for exactly this "equal highs/lows" concept)
    does that full scan. Same underlying pool-clustering IDEA as
    step56's, different-scoped implementation for a different question —
    documented here rather than silently switched."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        piv = tc.s.piv_high if tc.direction > 0 else tc.s.piv_low
        return _nearest_liquidity_cluster(piv, tc.entry_idx, tc.entry_price, tc.direction,
                                          "favorable", tol_pct / 100)
    return ExitMethod(f"target_liquidity_pool(tol_pct={tol_pct})", level_fn, style="intrabar")


def target_measured_move(extension: float = 1.0) -> ExitMethod:
    """The height of the preceding leg (last confirmed favorable-side
    swing minus last confirmed protective-side swing, both as of entry —
    "the range that got price here") projected forward from entry in the
    trade's direction, scaled by `extension` (1.0 = a 1:1 projection,
    1.618 = a fib-extension-flavored projection, etc.). A stated
    simplification of "measured move" (a real trader might measure a
    specific labeled leg, not just the two nearest confirmed pivots) —
    documented plainly rather than pretending to more precision than the
    data supports."""
    def level_fn(tc: TradeCtx, i: int) -> Optional[float]:
        fav_piv = tc.s.piv_high if tc.direction > 0 else tc.s.piv_low
        prot_piv = tc.s.piv_low if tc.direction > 0 else tc.s.piv_high
        fav = _nth_pivot(fav_piv, tc.entry_idx, tc.entry_price, tc.direction, "favorable", 1)
        prot = _nth_pivot(prot_piv, tc.entry_idx, tc.entry_price, tc.direction, "protective", 1)
        if fav is None or prot is None:
            return None
        leg_height = abs(fav - prot)
        if leg_height <= 0:
            return None
        return tc.entry_price + tc.direction * extension * leg_height
    return ExitMethod(f"target_measured_move(extension={extension})", level_fn, style="intrabar")


def target_trail_only() -> ExitMethod:
    """No target at all — "ride until the trailing stop takes you out".
    Documented no-op: level_fn always returns None, so run_trade()'s
    target slot never fires and only the paired stop (or max_hold_bars)
    can end the trade. Passing target=None to run_trade() directly does
    the same thing; this exists so "trail-only" appears as a named,
    discoverable method in the library rather than an implicit absence."""
    return ExitMethod("target_trail_only()", level_fn=lambda tc, i: None, style="intrabar")


def target_time(n_bars: int) -> ExitMethod:
    """Flatten after N bars — see stop_time()'s docstring; the identical
    clock mechanic, offered under both names because the mandate lists
    both a STOPS "time stop" and a TARGETS "time exit"."""
    return ExitMethod(f"target_time(n_bars={n_bars})", level_fn=lambda tc, i: None,
                      event_fn=_event_time(n_bars))


def target_opposite_signal(signal_arr: np.ndarray, treat_zero_as_exit: bool = False) -> ExitMethod:
    """Out when the entry rule flips. `signal_arr` is the CALLER's own
    causal per-bar desired-direction series (+1/-1/0), computed however
    that entry rule is defined elsewhere (this file has no opinion on
    entries) — it is the caller's responsibility that signal_arr[i] only
    ever reflects data knowable as of bar i; this method just reads it.
    Fires the instant signal_arr[i] shows the OPPOSITE direction to the
    open trade. treat_zero_as_exit=False (default): a signal that goes
    flat/neutral does NOT by itself flatten the trade (many trend rules
    mean "no NEW entry", not "exit the current one") — set True for
    entry rules where neutral genuinely means "get out"."""
    def event_fn(tc: TradeCtx, i: int) -> bool:
        if i >= len(signal_arr):
            return False
        sig = signal_arr[i]
        if sig != sig:
            return False
        if sig == -tc.direction:
            return True
        if treat_zero_as_exit and sig == 0:
            return True
        return False
    return ExitMethod("target_opposite_signal(...)", level_fn=lambda tc, i: None, event_fn=event_fn)


# ===========================================================================
# 5. THE GENERIC ENGINE
# ===========================================================================

@dataclass
class Leg:
    frac: float
    price: float
    bar: int
    reason: str


@dataclass
class ExitOutcome:
    legs: list   # list[Leg]; fracs sum to 1.0

    @property
    def exit_bar(self) -> int:
        return self.legs[-1].bar

    @property
    def exit_price(self) -> float:
        """The single fill price for a one-leg trade. For a multi-leg
        (partial-scale) trade this is the FINAL leg's price only — use
        .blended_price() for the size-weighted average."""
        return self.legs[-1].price

    @property
    def reason(self) -> str:
        return self.legs[-1].reason

    def blended_price(self) -> float:
        return sum(leg.frac * leg.price for leg in self.legs)


def run_trade(tc: TradeCtx, stop: Optional[ExitMethod], target: Optional[ExitMethod],
             max_hold_bars: int) -> ExitOutcome:
    """THE generic composition engine. Walks forward from entry_idx+1,
    asking `stop` and `target` (any ExitMethod built anywhere above, in
    any combination — nothing here is specialized to a particular pair)
    whether they fired at each bar, via the shared _resolve() routine.
    Stop is checked FIRST every bar and wins any same-bar tie (the
    engine-wide conservative convention this repo has used since
    backtest.py). target=None means "trail-only" (equivalent to pairing
    with target_trail_only()). If neither fires within max_hold_bars, the
    trade force-closes at that bar's own close (time cap, taker-side)."""
    s = tc.s
    last = min(s.n - 1, tc.entry_idx + max_hold_bars)
    for i in range(tc.entry_idx + 1, last + 1):
        if stop is not None:
            px = _resolve(stop, tc, i, "stop")
            if px is not None:
                return ExitOutcome([Leg(1.0, px, i, f"stop:{stop.name}")])
        if target is not None:
            px = _resolve(target, tc, i, "target")
            if px is not None:
                return ExitOutcome([Leg(1.0, px, i, f"target:{target.name}")])
    fill = float(s.c[last])
    return ExitOutcome([Leg(1.0, fill, last, "time_cap")])


def simulate_partial_scale(tc: TradeCtx, stop: ExitMethod, final_target: Optional[ExitMethod],
                          max_hold_bars: int, r_multiple: float = 1.0, frac: float = 0.5,
                          move_to_breakeven: bool = True) -> Optional[ExitOutcome]:
    """Take `frac` off at r_multiple x R (R = stop's own initial distance,
    exactly like target_fixed_r), move the stop to breakeven on the
    remainder (or leave it trailing per `stop` if move_to_breakeven=
    False), then let the remainder run to `final_target` (any ExitMethod,
    or None for trail-only-after-partial) or the ORIGINAL `stop` still
    trailing underneath it. This is what most real traders actually do
    and the mandate explicitly says the repo has never tested it — it is
    inherently two-legged (the stop distance itself changes mid-trade),
    so it cannot be expressed as a single ExitMethod the way run_trade's
    other pairings can; it composes a stop ExitMethod and a target
    ExitMethod exactly like run_trade does, just across two phases.
    Design adapted from step59_exit_science's X4 hybrid exit, generalized
    to accept ANY stop and ANY final target instead of X4's one hardcoded
    pairing. Returns None if the paired stop has no defined level at
    entry (nothing to size R against)."""
    s = tc.s
    entry_price, direction = tc.entry_price, tc.direction
    stop_at_entry = stop.level_fn(tc, tc.entry_idx)
    if stop_at_entry is None:
        return None
    stop_dist = abs(entry_price - stop_at_entry)
    if stop_dist <= 0:
        return None
    partial_level = entry_price + direction * r_multiple * stop_dist

    last = min(s.n - 1, tc.entry_idx + max_hold_bars)
    legs: list[Leg] = []
    phase = 1
    be_level = entry_price

    for i in range(tc.entry_idx + 1, last + 1):
        o, h, l = s.o[i], s.h[i], s.l[i]
        if phase == 1:
            lvl = stop.level_fn(tc, i)
            if lvl is not None:
                hit_stop = (l <= lvl) if direction > 0 else (h >= lvl)
                if hit_stop:
                    px = _gap_or_level(o, lvl, direction, "stop")
                    legs.append(Leg(1.0, px, i, f"stop:{stop.name}"))
                    return ExitOutcome(legs)
            hit_partial = (h >= partial_level) if direction > 0 else (l <= partial_level)
            if not hit_partial:
                continue
            px = _gap_or_level(o, partial_level, direction, "target")
            legs.append(Leg(frac, px, i, f"partial_{r_multiple}R"))
            phase = 2
            be_level = entry_price if move_to_breakeven else (lvl if lvl is not None else entry_price)
            hit_be = (l <= be_level) if direction > 0 else (h >= be_level)
            final_lvl = final_target.level_fn(tc, i) if final_target is not None else None
            hit_final = final_lvl is not None and ((h >= final_lvl) if direction > 0 else (l <= final_lvl))
            if hit_be:
                px2 = _gap_or_level(o, be_level, direction, "stop:breakeven")
                legs.append(Leg(1 - frac, px2, i, "breakeven_stop"))
                return ExitOutcome(legs)
            if hit_final:
                px2 = _gap_or_level(o, final_lvl, direction, "target")
                legs.append(Leg(1 - frac, px2, i, f"final_target:{final_target.name}"))
                return ExitOutcome(legs)
            continue

        # phase 2: partial already taken, remainder is breakeven-protected
        hit_be = (l <= be_level) if direction > 0 else (h >= be_level)
        if hit_be:
            px = _gap_or_level(o, be_level, direction, "stop:breakeven")
            legs.append(Leg(1 - frac, px, i, "breakeven_stop"))
            return ExitOutcome(legs)
        final_lvl = final_target.level_fn(tc, i) if final_target is not None else None
        if final_lvl is not None:
            hit_final = (h >= final_lvl) if direction > 0 else (l <= final_lvl)
            if hit_final:
                px = _gap_or_level(o, final_lvl, direction, "target")
                legs.append(Leg(1 - frac, px, i, f"final_target:{final_target.name}"))
                return ExitOutcome(legs)

    remain = 1.0 if phase == 1 else (1 - frac)
    legs.append(Leg(remain, float(s.c[last]), last, "time_cap"))
    return ExitOutcome(legs)


# ===========================================================================
# 6. REGIME CLASSIFIER
#    Reuses chart_reader.py's structure/quality/momentum reads rather than
#    inventing a second vocabulary — see module docstring.
# ===========================================================================

VALID_REGIME = {"uptrend", "downtrend", "range-consolidation", "transition"}
VALID_VOLATILITY = {"expanding", "contracting", "flat"}

_STRUCTURE_TO_REGIME = {
    "uptrend": "uptrend",
    "downtrend": "downtrend",
    "transition": "transition",
    "range": "range-consolidation",
    "chop": "range-consolidation",
}


def classify_regime(candles: pd.DataFrame, i: int, atr_n: int = 14, vol_lookback: int = 14,
                    expand_ratio: float = 1.2, contract_ratio: float = 0.8) -> dict:
    """Causal (no-lookahead) regime label for bar i: candles.iloc[:i+1] is
    all this function ever sees (chart_reader.read_chart() gets exactly
    that slice, nothing more). Returns:
      structure: one of VALID_REGIME (uptrend/downtrend/range-
        consolidation/transition) — chart_reader's own {uptrend,
        downtrend,transition,range,chop} vocabulary collapsed to the
        mandate's 4 states (range and chop, its two "not trending" reads,
        both mean range-consolidation for this purpose).
      volatility: one of VALID_VOLATILITY (expanding/contracting/flat) —
        current ATR(atr_n) vs its own value vol_lookback bars earlier;
        NOT chart_reader's "momentum" field (candle-body momentum is a
        different, correlated-but-distinct concept from ATR volatility
        state; conflating them would hide real information, so this is
        computed fresh here instead of reused).
      raw_structure / quality / momentum: chart_reader's own fields,
        passed through unmodified for anyone who wants the finer-grained
        read underneath the collapsed label.
    Uses the step84_blind_drill.py `_FAR_FUTURE` "now" convention so
    chart_reader never treats candles.iloc[i] as a still-forming bar."""
    window = candles.iloc[: i + 1].reset_index(drop=True)
    read = _chart_reader.read_chart(window, now=_FAR_FUTURE)
    structure = _STRUCTURE_TO_REGIME[read["structure"]]

    a = _atr_series(window, atr_n)
    a_np = a.to_numpy()
    if len(a_np) <= vol_lookback or not np.isfinite(a_np[-1]):
        volatility = "flat"
    else:
        cur, base = a_np[-1], a_np[-1 - vol_lookback]
        if base == base and base > 0:
            ratio = cur / base
            if ratio >= expand_ratio:
                volatility = "expanding"
            elif ratio <= contract_ratio:
                volatility = "contracting"
            else:
                volatility = "flat"
        else:
            volatility = "flat"

    return {
        "structure": structure,
        "volatility": volatility,
        "raw_structure": read["structure"],
        "quality": read["quality"],
        "momentum": read["momentum"],
    }


# ===========================================================================
# 7. DISTANCE REPORTING — BLOFIN_API_REFERENCE.md's dual-unit convention
# ===========================================================================

def describe_distance(entry_price: float, level_price: float, leverage: float = 20.0) -> dict:
    """Every distance in BOTH units, per BLOFIN_API_REFERENCE.md: the
    owner only ever sees PnL as a percentage of margin (BloFin's
    unrealizedPnlRatio), so a stop/target distance stated only as a
    price% is not what he sees on his screen. price_pct x leverage =
    margin_pct EXACTLY (unrealizedPnlRatio's own definition — no
    liquidation-distance or contract-value math needed here, this is
    plain linear leverage scaling of a price move into a margin move,
    the same relationship BLOFIN_API_REFERENCE.md verified against the
    live position: -10.87/204.52 = -5.31% margin from a 20x-scaled price
    move)."""
    price_pct = abs(level_price - entry_price) / entry_price * 100
    margin_pct = price_pct * leverage
    return {
        "price_pct": price_pct,
        "margin_pct": margin_pct,
        "leverage": leverage,
        "text": f"{price_pct:.2f}% price = {margin_pct:.1f}% of margin at {leverage:.0f}x",
    }


# ===========================================================================
# 8. CAUSALITY SELF-TEST
#    Adapted from step84_blind_drill.py's self_test_causality() pattern:
#    render the same decision point from the full series and from a
#    series truncated one bar past the decision, assert IDENTICAL output.
#    The real, exhaustive version of this (every method, many entries) is
#    test_exits.py's test_causality_truncation() — this module-level
#    function is a lightweight `python3 exits.py` smoke check.
# ===========================================================================

def self_test_causality(candles: pd.DataFrame, decision_idx: int, k: int = 5) -> bool:
    """Builds a SeriesCtx from the FULL frame and one from candles
    truncated to [:decision_idx+1], then compares stop_structure_trailing
    ()'s level at decision_idx between the two — a trailing/ratcheting
    method is the hardest case (it scans pivot history up to i), so it is
    the sharpest test that nothing here can see past its own decision
    bar. Returns True iff the two levels are identical (or both None)."""
    full_ctx = build_series_ctx(candles, k=k)
    truncated = candles.iloc[: decision_idx + 1].reset_index(drop=True)
    trunc_ctx = build_series_ctx(truncated, k=k)

    entry_idx = max(0, decision_idx - 20)
    entry_price = float(full_ctx.c[entry_idx])
    tc_full = build_trade_ctx(full_ctx, entry_idx, entry_price, LONG)
    tc_trunc = build_trade_ctx(trunc_ctx, entry_idx, entry_price, LONG)

    method = stop_structure_trailing()
    a = method.level_fn(tc_full, decision_idx)
    b = method.level_fn(tc_trunc, decision_idx)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) < 1e-9


if __name__ == "__main__":
    import sys

    np.random.seed(7)
    n = 400
    close = 100 + np.cumsum(np.random.normal(0, 1, n))
    high = close + np.random.uniform(0.1, 1.0, n)
    low = close - np.random.uniform(0.1, 1.0, n)
    open_ = close + np.random.normal(0, 0.3, n)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"),
        "open": open_, "high": high, "low": low, "close": close,
    })
    ok = self_test_causality(df, decision_idx=300)
    print("exits.py causality self-test PASSED (identical stop_structure_trailing level "
         "with/without future data)" if ok else "exits.py causality self-test FAILED")
    sys.exit(0 if ok else 1)
