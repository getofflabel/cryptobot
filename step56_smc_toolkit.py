"""
step56_smc_toolkit.py — round 56: THE TRADER'S TOOLKIT.

Run:  python3 step56_smc_toolkit.py

MANDATE (owner, verbatim spirit): "you have to know liquidity
identification, break of structure, fair value gaps, equilibrium levels,
fib retracement, context, bias, and confluence — in different situations
you use different weapons." This round FORMALIZES the owner's named
Smart-Money/ICT concept family on BTC as pure, shift-disciplined functions,
then gauntlets every concept both as its own single-tool baseline AND as
an input to a CONFLUENCE SCORER — the owner's central claim under test:
does requiring multiple tools to agree beat any single tool alone, or does
it just cut the sample without adding real edge? Research only — no
commits, no live orders, no file touched outside step56_smc_toolkit.py /
step56_results.md.

CONCEPT DEFINITIONS USED (read this before reading any function below)
------------------------------------------------------------------------
SWINGS — confirmed_swings(d, k) [imported from step41_shorts, unmodified]:
    a k-bar fractal high/low, confirmed k bars AFTER its own extreme (a
    swing only "exists" once we can see k bars on both sides of it — no
    lookahead: the value at bar t reflects an extreme at bar t-k).

LIQUIDITY POOLS — liquidity_pools(): >=2 confirmed swing highs (or lows)
    within tol% of each other = an "equal highs/lows" resting-liquidity
    pool. APPROXIMATION: the pool level is recomputed fresh each bar from
    the two MOST RECENT confirmed swing points (causal, forward-filled).
    There is no separate "consumed" bookkeeping — once price cleanly
    breaks a pool, later swing points naturally replace it as the newer
    pair becomes "most recent". Stated plainly as a simplification.

SWEEP — sweep_events(): a bar's wick pierces the pool by <= depth% but
    CLOSES back inside it -> fade the raid. Sweeping equal LOWS (wick
    below, close back above) = LONG (stop-hunt reclaimed). Sweeping equal
    HIGHS (wick above, close back below) = SHORT. Classic SMC stop-hunt
    reversal logic.

BREAK OF STRUCTURE (BOS) / CHANGE OF CHARACTER (CHoCH) — bos_chain():
    LSH/LSL = last confirmed swing high/low (causal, ffilled). Chain state
    (1 = uptrend structure, -1 = down, 0 = undetermined) updates on HH+HL
    (higher high AND higher low vs the prior confirmed pair) -> 1, or
    LH+LL -> -1, and PERSISTS (ffill) otherwise. BOS-UP = close
    edge-crosses above LSH; BOS-DOWN = close edge-crosses below LSL
    (fires once per breach, not every bar it stays broken).
    BOS-CONTINUATION = a BOS event in the SAME direction as the already-
    prevailing chain (trade with the trend, on confirmation).
    CHoCH = the first BOS event AGAINST the prevailing chain (or with no
    chain yet established) — the structural shift itself (reversal
    trade).

FAIR VALUE GAP (FVG) — fvg_signals(): a 3-candle imbalance: bar1.high <
    bar3.low = bullish gap (impulse up); bar1.low > bar3.high = bearish
    gap (impulse down). ENTRY = price's first RETURN into the gap to at
    least `fill_frac` depth (0.5 = midpoint, 1.0 = full fill), traded WITH
    the gap's own impulse direction (a continuation entry on the pullback,
    not a fade). Only the nearest unfilled gap per direction is tracked;
    a gap not touched within `expire_bars` stops being tracked. No
    lookahead: a gap is only knowable once its 3rd candle has closed, and
    entries only fire on bars strictly after formation.

EQUILIBRIUM / PREMIUM-DISCOUNT — equilibrium(): active range = the last
    confirmed swing high <-> swing low (the same LSH/LSL as BOS). eq =
    the 50% midpoint. discount = close below eq (cheap, buy zone),
    premium = close above eq (expensive, sell zone). Per the mandate this
    is a FILTER, not a standalone family — used to gate other tools'
    longs to discount / shorts to premium, both as an ablation on other
    families and as one of the five confluence checks.

FIB RETRACEMENT — leg_tracker() + fib_entries(): the LAST BOS-CONFIRMED
    impulse leg (locked in at the moment its own BOS fires — a stated
    simplification vs. a leg whose extremity keeps extending) defines a
    swing-low<->swing-high (bullish leg) or swing-high<->swing-low
    (bearish leg) range. Entry zone = {0.618-0.705, 0.705-0.79} pullback
    WITH the leg's own trend; stop past the 0.9 retracement (structure
    failed); target = {2x, 3x} the stop distance, or the leg's own 1.272
    extension beyond its origin (whichever the config specifies). The leg
    is invalidated (stops being tracked) once close crosses the 0.9 level
    or `expire_bars` elapse untouched.

CONTEXT / BIAS — bias_series_4h(): the 4h trend state, defined exactly as
    the mandate specifies: vol_gated_ma's sign (the standing champion
    trend filter, allow_short=True so it reads -1/0/1) AND the 4h BOS
    chain direction must AGREE for a bias to register; otherwise neutral
    (0, no bias). Read onto 1h via the repo's existing "a coarser
    timeframe's read becomes visible only at its own close" convention
    (champ_aligned, reused unmodified from step43_daytrade).

CONFLUENCE SCORER — family5_confluence(): for each candidate entry from a
    base tool (BOS-continuation, CHoCH, FIB, FVG, or their pooled union
    "ANY"), count how many of five conditions agree AT THAT BAR:
    bias-aligned + discount/premium-correct + inside a broad 0.618-0.79
    fib zone + a same-direction pool sweep fired in the last 24h + a
    same-direction FVG is currently active/unfilled. Test entry
    thresholds >=2 / >=3 against the threshold-0 (ungated) baseline for
    the SAME tool, SAME geometry — the owner's central claim: does
    requiring agreement beat the single tool, or just cut the sample?

ENGINE NOTES (read backtest.py / strategy.py for ground truth)
- run_backtest takes ONE fixed stop_pct/target_pct for the whole run, not
  a per-trade dynamic level. Every concept above that wants a per-trade
  dynamic distance (behind a swing, past a gap edge, past a fib
  invalidation level) follows this repo's established approximation
  (round 17 / step41 / step43 / step50): compute the representative
  distance as a TRAIN-only median over that config's actual qualifying
  entries, cap it at STOP_CAP_PCT, hold it fixed across train and val.
  Stated plainly here and in step56_results.md — this is a known
  simplification, not a claim that the engine expresses true trailing/
  structural stops.
- max_hold is enforced inside each family's own signal state machine
  (day_trade_signal, imported unmodified from step43_daytrade), exactly
  like every other day-trade-shaped family in this repo.
- No lookahead: every concept function above is documented with its own
  no-lookahead argument. Smoothing indicators (ATR, the champion MA) are
  NOT shifted, matching the rest of the codebase — the engine's own
  bar-close-N -> fill-at-open-N+1 mechanic is what enforces no-lookahead
  there, same as strategy.py's own docstring states.
- GAUNTLET: chronological 60/20/20 per timeframe (split_points, imported
  from step43_daytrade, unmodified: i_tr = 60%, i_va = 80%). This script
  NEVER slices into the final 20% (test) — score() only ever touches
  [0:i_tr] and [i_tr:i_va]. Selection is by TRAIN expectancy only; val is
  looked at once and never tuned against. The sealed test window is left
  entirely for the lead agent to spend looks against.
- 15m cost floor: sweep and FVG (the only families run on 15m, per the
  owner's mandate — dense families die there) get an HONEST realized-cost
  check via realized_cost_bps / gross_edge_bps, imported unmodified from
  step50_volume_absorption (the repo's established ~9bps-floor
  methodology since round 43/50).
- Costs always on: CostModel defaults (6bps taker / 2bps maker, 1bp
  half-spread, 2bp slippage), execution="maker" (the repo standard for
  every day-trade-shaped family since step43), REAL funding via
  align_funding.
- GRID DISCIPLINE: ~300 configs total. Secondary parameters (expiry
  windows, hold caps, the 4h bias's own BOS k) are FIXED at a stated
  default rather than swept; only the load-bearing dimensions the owner
  named — tolerances, fill depths, confluence thresholds, k in {5,8},
  fib zones, target multiples — are actually swept.
"""

import numpy as np
import pandas as pd

import config
from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import adaptive_vol_gate, confirmed_swings, days_to_bars, last_n_confirmed
from step43_daytrade import (
    HARD_STOP_CAP,
    bar_hours,
    champ_aligned,
    day_trade_signal,
    hold_stats,
    hours_to_bars,
    mk_row,
    score,
    split_points,
    verdict_for,
)
from step50_volume_absorption import gross_edge_bps, realized_cost_bps
from strategy import atr, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 6.0        # hard ceiling on any train-median structural stop
STOP_FLOOR_PCT = 0.25     # hard floor — never a stop tighter than this


# ---------------------------------------------------------------------------
# shared helper: the repo's train-median dynamic-distance approximation
# ---------------------------------------------------------------------------

def train_median_stop_pct(d, i_tr, entry_mask, distance_pct,
                           cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    """TRAIN-only median of a per-trade dynamic stop distance (% of
    price), held fixed across train/val — see module docstring's ENGINE
    NOTES. Returns None if the config has zero qualifying train entries
    (nothing to size a stop from)."""
    mask = entry_mask.iloc[:i_tr].fillna(False)
    vals = distance_pct.iloc[:i_tr][mask].dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(min(max(vals.median(), floor), cap))


# ---------------------------------------------------------------------------
# CONCEPT 1 — liquidity pools & sweeps
# ---------------------------------------------------------------------------

def liquidity_pools(d, k, tol_pct):
    """Equal-highs / equal-lows liquidity pools — see module docstring."""
    sh_price, sl_price = confirmed_swings(d, k)
    sh1, sh2 = last_n_confirmed(sh_price, 2)
    sl1, sl2 = last_n_confirmed(sl_price, 2)
    pool_high = pd.Series(np.where(
        sh1.notna() & sh2.notna() & ((sh1 - sh2).abs() / sh2 * 100 <= tol_pct),
        (sh1 + sh2) / 2, np.nan), index=d.index)
    pool_low = pd.Series(np.where(
        sl1.notna() & sl2.notna() & ((sl1 - sl2).abs() / sl2 * 100 <= tol_pct),
        (sl1 + sl2) / 2, np.nan), index=d.index)
    return pool_high, pool_low


def sweep_events(d, pool_high, pool_low, depth_pct):
    """Wick through a pool by <= depth_pct but close back inside ->
    fade-the-raid entries. See module docstring for direction mapping."""
    high, low, close = d["high"], d["low"], d["close"]
    sweep_short = (pool_high.notna() & (high > pool_high) &
                   (high <= pool_high * (1 + depth_pct / 100)) &
                   (close < pool_high))
    sweep_long = (pool_low.notna() & (low < pool_low) &
                  (low >= pool_low * (1 - depth_pct / 100)) &
                  (close > pool_low))
    return sweep_long.fillna(False), sweep_short.fillna(False)


# ---------------------------------------------------------------------------
# CONCEPT 2 — break of structure / CHoCH
# ---------------------------------------------------------------------------

def bos_chain(d, k):
    """Break-of-structure chain state + event detection. See module
    docstring's BREAK OF STRUCTURE section for the exact rules."""
    sh_price, sl_price = confirmed_swings(d, k)
    lsh = sh_price.ffill()
    lsl = sl_price.ffill()
    sh1, sh2 = last_n_confirmed(sh_price, 2)
    sl1, sl2 = last_n_confirmed(sl_price, 2)
    hh, hl = sh1 > sh2, sl1 > sl2
    lh, ll = sh1 < sh2, sl1 < sl2
    up_struct = hh & hl
    down_struct = lh & ll
    raw_state = pd.Series(np.select([up_struct, down_struct], [1, -1],
                                     default=np.nan), index=d.index)
    chain = raw_state.ffill().fillna(0)

    close = d["close"]
    above = (close > lsh).fillna(False)
    below = (close < lsl).fillna(False)
    bos_up = above & ~above.shift(1, fill_value=False)
    bos_down = below & ~below.shift(1, fill_value=False)

    prior_chain = chain.shift(1).fillna(0)
    cont_long = bos_up & (prior_chain == 1)
    choch_long = bos_up & (prior_chain != 1)
    cont_short = bos_down & (prior_chain == -1)
    choch_short = bos_down & (prior_chain != -1)

    return dict(lsh=lsh, lsl=lsl, chain=chain, bos_up=bos_up, bos_down=bos_down,
                cont_long=cont_long, cont_short=cont_short,
                choch_long=choch_long, choch_short=choch_short)


# ---------------------------------------------------------------------------
# CONCEPT 3 — equilibrium / premium-discount (filter, not standalone)
# ---------------------------------------------------------------------------

def equilibrium(d, k):
    sh_price, sl_price = confirmed_swings(d, k)
    lsh = sh_price.ffill()
    lsl = sl_price.ffill()
    eq = (lsh + lsl) / 2
    discount = (d["close"] < eq).fillna(False)
    premium = (d["close"] > eq).fillna(False)
    return discount, premium, eq, lsh, lsl


# ---------------------------------------------------------------------------
# CONCEPT 4 — fair value gap
# ---------------------------------------------------------------------------

def fvg_signals(d, fill_frac, expire_bars):
    """3-candle imbalance, entry on return-into-gap. See module docstring.
    Returns (enter_long, enter_short, dist_long, dist_short, active_bull,
    active_bear) — the last two are persistent "an unfilled same-
    direction gap exists right now" flags, used later as one of the five
    confluence checks."""
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    n = len(d)
    bull_top = np.full(n, np.nan); bull_bot = np.full(n, np.nan)
    bear_top = np.full(n, np.nan); bear_bot = np.full(n, np.nan)
    if n > 2:
        bg = h[:-2] < l[2:]
        beg = l[:-2] > h[2:]
        bull_top[2:] = np.where(bg, l[2:], np.nan)
        bull_bot[2:] = np.where(bg, h[:-2], np.nan)
        bear_top[2:] = np.where(beg, l[:-2], np.nan)
        bear_bot[2:] = np.where(beg, h[2:], np.nan)

    enter_long = np.zeros(n, dtype=bool); enter_short = np.zeros(n, dtype=bool)
    dist_long = np.full(n, np.nan); dist_short = np.full(n, np.nan)
    active_bull = np.zeros(n, dtype=bool); active_bear = np.zeros(n, dtype=bool)

    ab = None    # active bullish gap: (top, bot, formed_i)
    ar = None    # active bearish gap
    for i in range(n):
        if not np.isnan(bull_top[i]):
            ab = (bull_top[i], bull_bot[i], i)
        if not np.isnan(bear_top[i]):
            ar = (bear_top[i], bear_bot[i], i)

        if ab is not None:
            top, bot, formed = ab
            if i - formed > expire_bars:
                ab = None
            else:
                active_bull[i] = True
                if i > formed:
                    fill_level = top - fill_frac * (top - bot)
                    if l[i] <= fill_level:
                        enter_long[i] = True
                        dist_long[i] = abs(c[i] - bot) / c[i] * 100
                        ab = None

        if ar is not None:
            top, bot, formed = ar
            if i - formed > expire_bars:
                ar = None
            else:
                active_bear[i] = True
                if i > formed:
                    fill_level = bot + fill_frac * (top - bot)
                    if h[i] >= fill_level:
                        enter_short[i] = True
                        dist_short[i] = abs(top - c[i]) / c[i] * 100
                        ar = None

    idx = d.index
    return (pd.Series(enter_long, index=idx), pd.Series(enter_short, index=idx),
            pd.Series(dist_long, index=idx), pd.Series(dist_short, index=idx),
            pd.Series(active_bull, index=idx), pd.Series(active_bear, index=idx))


# ---------------------------------------------------------------------------
# CONCEPT 5 — fib retracement (of the last BOS-confirmed impulse leg)
# ---------------------------------------------------------------------------

def leg_tracker(d, k, expire_bars):
    """Track the single active impulse leg per direction, locked in at
    BOS confirmation. See module docstring's FIB RETRACEMENT section.
    Returns bull_low/bull_high/bear_low/bear_high (Series, NaN when no
    active leg of that direction)."""
    bos = bos_chain(d, k)
    bos_up = bos["bos_up"].to_numpy()
    bos_down = bos["bos_down"].to_numpy()
    lsh = bos["lsh"].to_numpy()
    lsl = bos["lsl"].to_numpy()
    close = d["close"].to_numpy()
    n = len(d)
    bull_low = np.full(n, np.nan); bull_high = np.full(n, np.nan)
    bear_low = np.full(n, np.nan); bear_high = np.full(n, np.nan)
    ab = None
    ar = None
    for i in range(n):
        if bos_up[i] and not np.isnan(lsl[i]) and not np.isnan(lsh[i]) and lsh[i] > lsl[i]:
            ab = (lsl[i], lsh[i], i)
        if bos_down[i] and not np.isnan(lsl[i]) and not np.isnan(lsh[i]) and lsh[i] > lsl[i]:
            ar = (lsl[i], lsh[i], i)
        if ab is not None:
            lo, hi, formed = ab
            invalid = hi - 0.9 * (hi - lo)
            if i - formed > expire_bars or close[i] < invalid:
                ab = None
            else:
                bull_low[i], bull_high[i] = lo, hi
        if ar is not None:
            lo, hi, formed = ar
            invalid = lo + 0.9 * (hi - lo)
            if i - formed > expire_bars or close[i] > invalid:
                ar = None
            else:
                bear_low[i], bear_high[i] = lo, hi
    idx = d.index
    return (pd.Series(bull_low, index=idx), pd.Series(bull_high, index=idx),
            pd.Series(bear_low, index=idx), pd.Series(bear_high, index=idx))


def fib_entries(d, bull_low, bull_high, bear_low, bear_high, zone_lo, zone_hi):
    """Vectorized from leg_tracker's per-bar active-leg bounds: entries
    (edge-triggered — a fresh pullback into the zone during the SAME
    leg's lifetime is its own valid setup, so re-entry is allowed, stated
    plainly) plus persistent zone-membership (long_zone/short_zone) used
    later as one of the five confluence checks."""
    close = d["close"]
    bh = bull_high - bull_low
    zone_top_l = bull_high - zone_lo * bh
    zone_bot_l = bull_high - zone_hi * bh
    long_zone = bull_low.notna() & (close >= zone_bot_l) & (close <= zone_top_l)
    enter_long = (long_zone & ~long_zone.shift(1, fill_value=False)).fillna(False)
    invalid_l = bull_high - 0.9 * bh
    dist_long = ((close - invalid_l) / close * 100).where(enter_long)
    ext_level_l = bull_high + 0.272 * bh
    ext_dist_long = ((ext_level_l - close) / close * 100).where(enter_long)

    bhh = bear_high - bear_low
    zone_bot_s = bear_low + zone_lo * bhh
    zone_top_s = bear_low + zone_hi * bhh
    short_zone = bear_low.notna() & (close >= zone_bot_s) & (close <= zone_top_s)
    enter_short = (short_zone & ~short_zone.shift(1, fill_value=False)).fillna(False)
    invalid_s = bear_low + 0.9 * bhh
    dist_short = ((invalid_s - close) / close * 100).where(enter_short)
    ext_level_s = bear_low - 0.272 * bhh
    ext_dist_short = ((close - ext_level_s) / close * 100).where(enter_short)

    return (enter_long, enter_short, dist_long, dist_short,
            ext_dist_long, ext_dist_short,
            long_zone.fillna(False), short_zone.fillna(False))


# ---------------------------------------------------------------------------
# CONCEPT 6 — context / bias (4h)
# ---------------------------------------------------------------------------

BIAS_BOS_K = 8          # fixed secondary param: k used for the 4h BOS chain read

def bias_series_4h(frame4h):
    """4h bias = vol_gated_ma's sign AND the 4h BOS chain direction must
    AGREE, else neutral (0). See module docstring's CONTEXT/BIAS
    section."""
    champ = vol_gated_ma(frame4h, fast=20, slow=100, min_atr_pct=1.5,
                          allow_short=True).fillna(0)
    chain4h = bos_chain(frame4h, BIAS_BOS_K)["chain"]
    bias = pd.Series(np.select(
        [(champ == 1) & (chain4h == 1), (champ == -1) & (chain4h == -1)],
        [1, -1], default=0.0), index=frame4h.index)
    return bias


# ---------------------------------------------------------------------------
# FAMILY 1 — liquidity sweep (fade the raid)
# ---------------------------------------------------------------------------

def family1_sweep(frames, funding, meta):
    rows = []
    for tf in ("1h", "4h", "15m"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        for k in (5, 8):
            for tol in (0.05, 0.1):
                pool_high, pool_low = liquidity_pools(d, k, tol)
                for depth in (0.3, 0.6):
                    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, depth)
                    mask = sweep_long | sweep_short
                    n_events = int(mask.iloc[:i_va].sum())
                    dist_long = (d["close"] - d["low"]) / d["close"] * 100
                    dist_short = (d["high"] - d["close"]) / d["close"] * 100
                    dist = pd.Series(np.nan, index=d.index)
                    dist = dist.mask(sweep_long, dist_long)
                    dist = dist.mask(sweep_short, dist_short)
                    stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
                    if stop_pct is None:
                        continue
                    for target_mult in (2.0, 3.0):
                        target_pct = stop_pct * target_mult
                        for hold_days in (3, 7):
                            mh_bars = days_to_bars(d, hold_days)
                            sig = day_trade_signal(d, sweep_long, sweep_short, mh_bars)
                            tr, va = score(d, sig, f, i_tr, i_va,
                                           stop_pct=stop_pct, target_pct=target_pct)
                            cfg = (f"k{k} tol{tol:.2f}% depth{depth:.1f}% "
                                   f"tgt{target_mult:.0f}x hold{hold_days}d")
                            row = mk_row("1-sweep", cfg, tf, tr, va,
                                         stop_pct, target_pct, hold_days * 24)
                            row["n_events_tr_va"] = n_events
                            if tf == "15m":
                                row["realized_cost_bps"] = realized_cost_bps(tr, va)
                                row["gross_edge_bps"] = gross_edge_bps(tr, va)
                            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — break of structure (continuation + CHoCH)
# ---------------------------------------------------------------------------

def family2_bos(frames, funding, meta):
    rows = []
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        for k in (5, 8):
            bos = bos_chain(d, k)
            discount, premium, eq, lsh, lsl = equilibrium(d, k)
            dist_long = (d["close"] - bos["lsl"]) / d["close"] * 100
            dist_short = (bos["lsh"] - d["close"]) / d["close"] * 100
            for variant, el_raw, es_raw in (
                ("cont", bos["cont_long"], bos["cont_short"]),
                ("choch", bos["choch_long"], bos["choch_short"]),
            ):
                for eq_filter in (False, True):
                    if eq_filter:
                        el = el_raw & discount
                        es = es_raw & premium
                    else:
                        el, es = el_raw, es_raw
                    mask = el | es
                    n_events = int(mask.iloc[:i_va].sum())
                    dist = pd.Series(np.nan, index=d.index)
                    dist = dist.mask(el, dist_long)
                    dist = dist.mask(es, dist_short)
                    stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
                    if stop_pct is None:
                        continue
                    for target_mult in (2.0, 3.0):
                        target_pct = stop_pct * target_mult
                        for hold_days in (5, 15):
                            mh_bars = days_to_bars(d, hold_days)
                            sig = day_trade_signal(d, el, es, mh_bars)
                            tr, va = score(d, sig, f, i_tr, i_va,
                                           stop_pct=stop_pct, target_pct=target_pct)
                            cfg = (f"k{k} {variant} eqfilt={eq_filter} "
                                   f"tgt{target_mult:.0f}x hold{hold_days}d")
                            row = mk_row("2-bos", cfg, tf, tr, va,
                                         stop_pct, target_pct, hold_days * 24)
                            row["n_events_tr_va"] = n_events
                            rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — fair value gap fill
# ---------------------------------------------------------------------------

def family3_fvg(frames, funding, meta):
    rows = []
    for tf in ("1h", "4h", "15m"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        for expire_days in (7, 14):
            expire_bars = days_to_bars(d, expire_days)
            for fill_frac in (0.5, 1.0):
                el, es, dl, ds, ab, ar = fvg_signals(d, fill_frac, expire_bars)
                mask = el | es
                n_events = int(mask.iloc[:i_va].sum())
                dist = pd.Series(np.nan, index=d.index)
                dist = dist.mask(el, dl)
                dist = dist.mask(es, ds)
                stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
                if stop_pct is None:
                    continue
                for target_mult in (2.0, 3.0):
                    target_pct = stop_pct * target_mult
                    mh_bars = expire_bars
                    sig = day_trade_signal(d, el, es, mh_bars)
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"fill{fill_frac:.1f} expire{expire_days}d tgt{target_mult:.0f}x"
                    row = mk_row("3-fvg", cfg, tf, tr, va, stop_pct, target_pct,
                                 expire_days * 24)
                    row["n_events_tr_va"] = n_events
                    if tf == "15m":
                        row["realized_cost_bps"] = realized_cost_bps(tr, va)
                        row["gross_edge_bps"] = gross_edge_bps(tr, va)
                    rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — fib retracement
# ---------------------------------------------------------------------------

FIB_LEG_EXPIRE_DAYS = 20   # fixed secondary param

def family4_fib(frames, funding, meta):
    rows = []
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        expire_bars = days_to_bars(d, FIB_LEG_EXPIRE_DAYS)
        for k in (5, 8):
            bull_low, bull_high, bear_low, bear_high = leg_tracker(d, k, expire_bars)
            discount, premium, eq, _, _ = equilibrium(d, k)
            for zone_lo, zone_hi, zone_tag in ((0.618, 0.705, "0.618-0.705"),
                                                (0.705, 0.79, "0.705-0.79")):
                el, es, dl, ds, extl, exts, lz, sz = fib_entries(
                    d, bull_low, bull_high, bear_low, bear_high, zone_lo, zone_hi)
                for eq_filter in (False, True):
                    if eq_filter:
                        elf = el & discount
                        esf = es & premium
                    else:
                        elf, esf = el, es
                    mask = elf | esf
                    n_events = int(mask.iloc[:i_va].sum())
                    dist = pd.Series(np.nan, index=d.index)
                    dist = dist.mask(elf, dl)
                    dist = dist.mask(esf, ds)
                    stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
                    if stop_pct is None:
                        continue
                    ext_dist = pd.Series(np.nan, index=d.index)
                    ext_dist = ext_dist.mask(elf, extl)
                    ext_dist = ext_dist.mask(esf, exts)
                    ext_target_pct = train_median_stop_pct(
                        d, i_tr, mask, ext_dist, cap=STOP_CAP_PCT * 2, floor=0.5)
                    target_options = [("2xstop", stop_pct * 2), ("3xstop", stop_pct * 3)]
                    if ext_target_pct:
                        target_options.append(("ext1.272", ext_target_pct))
                    for tgt_tag, target_pct in target_options:
                        mh_bars = expire_bars
                        sig = day_trade_signal(d, elf, esf, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"k{k} zone{zone_tag} eqfilt={eq_filter} tgt={tgt_tag}"
                        row = mk_row("4-fib", cfg, tf, tr, va, stop_pct, target_pct,
                                     FIB_LEG_EXPIRE_DAYS * 24)
                        row["n_events_tr_va"] = n_events
                        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# FAMILY 5 — confluence scorer head-to-head
# ---------------------------------------------------------------------------

CONF_TOL, CONF_DEPTH = 0.1, 0.3          # fixed secondary params (sweep leg)
CONF_FILL, CONF_EXPIRE_DAYS = 0.5, 10    # fixed secondary params (FVG leg)
CONF_FIB_EXPIRE_DAYS = 20
CONF_HOLD_DAYS = 10

def family5_confluence(frames, funding, meta, bias_1h):
    rows = []
    tf = "1h"
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]

    for k in (5, 8):
        bos = bos_chain(d, k)
        discount, premium, eq, lsh, lsl = equilibrium(d, k)
        pool_high, pool_low = liquidity_pools(d, k, CONF_TOL)
        sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, CONF_DEPTH)
        window = hours_to_bars(d, 24)
        swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                              .max().fillna(0).astype(bool))
        swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                               .max().fillna(0).astype(bool))
        el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(
            d, CONF_FILL, days_to_bars(d, CONF_EXPIRE_DAYS))
        bull_low, bull_high, bear_low, bear_high = leg_tracker(
            d, k, days_to_bars(d, CONF_FIB_EXPIRE_DAYS))
        el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
            d, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

        dist_bos_long = (d["close"] - bos["lsl"]) / d["close"] * 100
        dist_bos_short = (bos["lsh"] - d["close"]) / d["close"] * 100

        bias_long = (bias_1h == 1)
        bias_short = (bias_1h == -1)

        count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                      + swept_recent_long.astype(int) + ab.astype(int))
        count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                       + swept_recent_short.astype(int) + ar.astype(int))

        bos_cont_long, bos_cont_short = bos["cont_long"], bos["cont_short"]
        choch_long, choch_short = bos["choch_long"], bos["choch_short"]

        any_long = bos_cont_long | choch_long | el_fib | el_fvg
        any_short = bos_cont_short | choch_short | es_fib | es_fvg
        any_dist_long = (dist_bos_long.where(bos_cont_long | choch_long)
                          .fillna(dl_fib).fillna(dl_fvg))
        any_dist_short = (dist_bos_short.where(bos_cont_short | choch_short)
                           .fillna(ds_fib).fillna(ds_fvg))

        tools = {
            "BOS-cont": (bos_cont_long, bos_cont_short, dist_bos_long, dist_bos_short),
            "CHoCH":    (choch_long, choch_short, dist_bos_long, dist_bos_short),
            "FIB":      (el_fib, es_fib, dl_fib, ds_fib),
            "FVG":      (el_fvg, es_fvg, dl_fvg, ds_fvg),
            "ANY":      (any_long, any_short, any_dist_long, any_dist_short),
        }

        for tool_name, (el0, es0, dl0, ds0) in tools.items():
            for threshold in (0, 1, 2, 3):
                if threshold == 0:
                    el, es = el0, es0
                else:
                    el = el0 & (count_long >= threshold)
                    es = es0 & (count_short >= threshold)
                mask = el | es
                n_events = int(mask.iloc[:i_va].sum())
                if n_events == 0:
                    continue
                dist = pd.Series(np.nan, index=d.index)
                dist = dist.mask(el, dl0)
                dist = dist.mask(es, ds0)
                stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
                if stop_pct is None:
                    continue
                for target_mult in (2.0, 3.0):
                    target_pct = stop_pct * target_mult
                    mh_bars = days_to_bars(d, CONF_HOLD_DAYS)
                    sig = day_trade_signal(d, el, es, mh_bars)
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"k{k} {tool_name} thresh>={threshold} tgt{target_mult:.0f}x"
                    row = mk_row("5-confluence", cfg, tf, tr, va,
                                 stop_pct, target_pct, CONF_HOLD_DAYS * 24)
                    row["n_events_tr_va"] = n_events
                    row["base_tool"] = tool_name
                    row["threshold"] = threshold
                    row["k"] = k
                    rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h", "4h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("15m", "1h", "4h")}

    meta = {}
    for tf, d in frames.items():
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.3f}%")

    frame4h = frames["4h"]
    bias4h = bias_series_4h(frame4h)
    bias_1h = champ_aligned(frame4h, bias4h, frames["1h"])
    bull_pct = float((bias_1h == 1).mean() * 100)
    bear_pct = float((bias_1h == -1).mean() * 100)
    print(f"  4h bias (vol_gated_ma AND BOS chain agree) on 1h: "
          f"bullish {bull_pct:.1f}% / bearish {bear_pct:.1f}% / "
          f"neutral {100 - bull_pct - bear_pct:.1f}% of bars")

    print("\nRunning FAMILY 1 (liquidity sweep)...")
    rows = family1_sweep(frames, funding, meta)
    print(f"  {len(rows)} configs done")
    print("Running FAMILY 2 (break of structure: continuation + CHoCH)...")
    rows += family2_bos(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 3 (fair value gap fill)...")
    rows += family3_fvg(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 4 (fib retracement)...")
    rows += family4_fib(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 5 (confluence scorer head-to-head)...")
    rows += family5_confluence(frames, funding, meta, bias_1h)
    print(f"  {len(rows)} configs cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >=30 train / >=8 val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                     "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    df.to_csv("step56_results_raw.csv", index=False)
    print("\nRaw results written to step56_results_raw.csv")

    conf = df[df["family"] == "5-confluence"].copy()
    if len(conf):
        print("\nCONFLUENCE HEAD-TO-HEAD (mean TRAIN expectancy, base_tool x threshold):")
        piv = conf.groupby(["base_tool", "threshold"])["tr_exp"].mean().unstack()
        print(piv.to_string(float_format=lambda x: f"{x:,.2f}"))
        print("\nCONFLUENCE HEAD-TO-HEAD (mean VAL expectancy, base_tool x threshold):")
        piv_va = conf.groupby(["base_tool", "threshold"])["va_exp"].mean().unstack()
        print(piv_va.to_string(float_format=lambda x: f"{x:,.2f}"))
        print("\nCONFLUENCE event counts (train+val), base_tool x threshold:")
        piv_n = conf.groupby(["base_tool", "threshold"])["n_events_tr_va"].mean().unstack()
        print(piv_n.to_string(float_format=lambda x: f"{x:,.0f}"))

    cost15 = df[(df["tf"] == "15m") & df["realized_cost_bps"].notna()].copy() \
        if "realized_cost_bps" in df.columns else pd.DataFrame()
    if len(cost15):
        print("\n15m COST-FLOOR CHECK (family/config with realized vs gross edge, bps):")
        print(cost15[["family", "config", "realized_cost_bps", "gross_edge_bps", "tr_exp"]]
              .sort_values("gross_edge_bps", ascending=False)
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    return df


if __name__ == "__main__":
    main()
