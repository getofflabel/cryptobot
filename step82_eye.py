"""
step82_eye.py — ROUND 82: THE EYE, VECTORIZED.

chart_reader.read_chart() (built in the round just before this one) computes
a trader's PERCEPTION of a chart — structure / location / quality / momentum
— from a trailing window of OHLCV, one call per snapshot. It is deterministic
and cheap, but it is written to be called ONCE, live, on the newest bar. To
grade the eye across an entire history (this project's cached BTC 1h history
alone is ~55k bars, 15m is ~222k bars, and this round needs BTC 1h + BTC 15m
+ ETH 1h + ETH 15m all labeled bar-by-bar) we cannot call read_chart() once
per bar — the per-bar reference implementation was measured (see the
_spotcheck-style validation this module runs at the bottom) at roughly 1-2ms
a call including its own internal windowing and confirmed-swing recompute,
which extrapolates to minutes, not seconds, across four full histories, and
would need to be paid AGAIN for every state-census / matrix rerun.

This module reimplements the SAME four thresholds (structure via confirmed
swings, quality via the three chop signatures, location via range position,
momentum via body expansion/contraction) as whole-series vectorized numpy/
pandas operations, run once per (asset, timeframe). Every threshold constant
is imported directly from chart_reader.py — not retyped — so the two can
never silently drift apart.

ONE DELIBERATE APPROXIMATION, documented honestly (see validate_against_
chart_reader() below, which measures exactly how often it matters):
chart_reader's _structure() recomputes confirmed_swings() on a FRESH
SWING_LOOKBACK(=60)-bar slice at every call, so a swing sitting in the first
few bars of that slice can occasionally fail to confirm (it's missing left-
context that a full-series computation would have). This module computes
confirmed_swings() ONCE across the whole series (still fully causal — no
lookahead is introduced) and then windows the RESULT to the same trailing
60 bars via a single O(n) forward pass. The two disagree only when a swing
sits in the first ~3 bars of a 60-bar window AND that swing is one of the
two most recent confirmed points structure depends on — a narrow, bounded
edge case. validate_against_chart_reader() draws a random sample of real
bars, calls the actual read_chart() on each, and reports the measured
agreement rate per axis, so this approximation is trusted on EVIDENCE, not
assumption.

State label = "structure|location|quality|momentum", the exact 4-axis
combination round 82's brief asks the census to be built on.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

import chart_reader as CR

# ---------------------------------------------------------------------------
# thresholds — imported, not retyped, from chart_reader.py (see module
# docstring: this is what keeps the vectorized path honest against the
# reference implementation as chart_reader.py evolves).
# ---------------------------------------------------------------------------
SWING_K = CR.SWING_K
SWING_LOOKBACK = CR.SWING_LOOKBACK
QUALITY_WINDOW = CR.QUALITY_WINDOW
DIRECTION_CHANGE_MESSY = CR.DIRECTION_CHANGE_MESSY
BODY_RATIO_MESSY = CR.BODY_RATIO_MESSY
OVERLAP_MESSY = CR.OVERLAP_MESSY
RANGE_WINDOW = CR.RANGE_WINDOW
RANGE_EDGE_HIGH = CR.RANGE_EDGE_HIGH
RANGE_EDGE_LOW = CR.RANGE_EDGE_LOW
MOMENTUM_LOOKBACK = CR.MOMENTUM_LOOKBACK
MOMENTUM_EXPAND_MULT = CR.MOMENTUM_EXPAND_MULT
MOMENTUM_CONTRACT_MULT = CR.MOMENTUM_CONTRACT_MULT


def _confirmed_swings_global(h: np.ndarray, l: np.ndarray, k: int):
    """Whole-series version of step41_shorts.confirmed_swings() — identical
    math (centered 2k+1 rolling max/min, shift(k) for no-lookahead
    confirmation), just called once instead of once per bar."""
    hs, ls = pd.Series(h), pd.Series(l)
    is_sh = (hs == hs.rolling(2 * k + 1, center=True).max())
    is_sl = (ls == ls.rolling(2 * k + 1, center=True).min())
    sh_conf = is_sh.shift(k).astype("boolean").fillna(False).to_numpy(dtype=bool)
    sl_conf = is_sl.shift(k).astype("boolean").fillna(False).to_numpy(dtype=bool)
    sh_price = np.where(sh_conf, hs.shift(k).to_numpy(), np.nan)
    sl_price = np.where(sl_conf, ls.shift(k).to_numpy(), np.nan)
    return sh_price, sl_price


def _quality_array(o, h, l, c) -> np.ndarray:
    n = len(c)
    rng = np.maximum(h - l, 1e-9)
    body_ratio = np.abs(c - o) / rng
    median_body_ratio = pd.Series(body_ratio).rolling(
        QUALITY_WINDOW, min_periods=3).median().to_numpy()

    direction = np.sign(c - o)
    nz_pair = np.concatenate([[False], (direction[1:] != 0) & (direction[:-1] != 0)])
    chg_pair = np.concatenate([[False],
                               (direction[1:] != direction[:-1]) & (direction[1:] != 0)
                               & (direction[:-1] != 0)])
    inside = np.concatenate([[False], (h[1:] <= h[:-1]) & (l[1:] >= l[:-1])])

    win_pairs = QUALITY_WINDOW - 1
    nz_sum = pd.Series(nz_pair.astype(float)).rolling(win_pairs, min_periods=1).sum().to_numpy()
    chg_sum = pd.Series(chg_pair.astype(float)).rolling(win_pairs, min_periods=1).sum().to_numpy()
    inside_sum = pd.Series(inside.astype(float)).rolling(win_pairs, min_periods=1).sum().to_numpy()
    pair_count = pd.Series(np.ones(n)).rolling(win_pairs, min_periods=1).sum().to_numpy()
    # bar 0 has zero pairs available (no prior bar) — pair_count already 0 there
    pair_count[0] = 0

    direction_change_rate = np.divide(chg_sum, nz_sum, out=np.zeros(n), where=nz_sum > 0)
    overlap_rate = np.divide(inside_sum, pair_count, out=np.zeros(n), where=pair_count > 0)

    messy = ((direction_change_rate >= DIRECTION_CHANGE_MESSY)
             | (np.nan_to_num(median_body_ratio, nan=1.0) < BODY_RATIO_MESSY)
             | (overlap_rate >= OVERLAP_MESSY))
    quality = np.where(messy, "messy", "clean").astype(object)
    quality[:2] = "messy"   # window has <3 bars for idx 0,1 -> code forces "messy"
    return quality


def _structure_array(sh_price, sl_price, quality) -> np.ndarray:
    n = len(sh_price)
    structure = np.empty(n, dtype=object)
    hist_h: deque = deque()   # deduped (pos, value) confirmed swing highs in window
    hist_l: deque = deque()

    for t in range(n):
        lo_bound = t - SWING_LOOKBACK + 1
        while hist_h and hist_h[0][0] < lo_bound:
            hist_h.popleft()
        while hist_l and hist_l[0][0] < lo_bound:
            hist_l.popleft()

        v = sh_price[t]
        if v == v:  # not NaN
            if not hist_h or hist_h[-1][1] != v:
                hist_h.append((t, v))
        v = sl_price[t]
        if v == v:
            if not hist_l or hist_l[-1][1] != v:
                hist_l.append((t, v))

        if t < 2 * SWING_K + 1:
            structure[t] = "chop" if quality[t] == "messy" else "range"
            continue

        if len(hist_h) >= 2 and len(hist_l) >= 2:
            hd = hist_h[-1][1] - hist_h[-2][1]
            ld = hist_l[-1][1] - hist_l[-2][1]
            if hd > 0 and ld > 0:
                structure[t] = "uptrend"
            elif hd < 0 and ld < 0:
                structure[t] = "downtrend"
            elif (hd > 0 and ld < 0) or (hd < 0 and ld > 0):
                structure[t] = "transition"
            else:
                structure[t] = "range"
        else:
            structure[t] = "chop" if quality[t] == "messy" else "range"
    return structure


def _location_array(h, l, c, structure) -> np.ndarray:
    n = len(c)
    range_hi = pd.Series(h).rolling(RANGE_WINDOW).max().shift(1).to_numpy()
    range_lo = pd.Series(l).rolling(RANGE_WINDOW).min().shift(1).to_numpy()
    has_range = ~np.isnan(range_hi) & ~np.isnan(range_lo)
    span = range_hi - range_lo
    pos = np.divide(c - range_lo, span, out=np.full(n, 0.5), where=span > 0)

    breaking_out = has_range & (c > range_hi)
    breaking_down = has_range & ~breaking_out & (c < range_lo)
    at_high = has_range & ~breaking_out & ~breaking_down & (pos >= RANGE_EDGE_HIGH)
    at_low = has_range & ~breaking_out & ~breaking_down & ~at_high & (pos <= RANGE_EDGE_LOW)
    trending = np.isin(structure, ["uptrend", "downtrend"])
    pullback = has_range & ~breaking_out & ~breaking_down & ~at_high & ~at_low & trending

    location = np.full(n, "mid range", dtype=object)
    location[breaking_out] = "breaking out"
    location[breaking_down] = "breaking down"
    location[at_high] = "at range high"
    location[at_low] = "at range low"
    location[pullback] = "pulling back in trend"
    return location


def _momentum_array(o, c) -> np.ndarray:
    n = len(c)
    bodies = pd.Series(np.abs(c - o))
    recent_mean = (bodies + bodies.shift(1)) / 2.0          # positions t, t-1
    prior_mean = (bodies.shift(2) + bodies.shift(3)) / 2.0  # positions t-2, t-3
    recent_mean = recent_mean.to_numpy()
    prior_mean = prior_mean.to_numpy()

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(
            prior_mean > 0, recent_mean / prior_mean,
            np.where(recent_mean > 0, np.inf, np.nan))

    momentum = np.full(n, "stalling", dtype=object)
    momentum[ratio >= MOMENTUM_EXPAND_MULT] = "expanding"
    momentum[(ratio <= MOMENTUM_CONTRACT_MULT) & (ratio == ratio)] = "contracting"
    momentum[:4] = "stalling"   # <4 bars of history: not enough for a read
    return momentum


def label_eye_states(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized bar-by-bar eye state for the FULL series. Row t's state
    describes the chart AS OF bar t's close (bar t treated as the newest
    CLOSED bar — matches chart_reader's non-forming path). Returns a
    DataFrame aligned to df's index with columns structure/location/
    quality/momentum/state. First ~65 bars (max warmup across all four
    axes) are real output, just noisier — callers should start any
    aggregate stats from index >= WARMUP_BARS."""
    o = df["open"].to_numpy(dtype=float)
    h = df["high"].to_numpy(dtype=float)
    l = df["low"].to_numpy(dtype=float)
    c = df["close"].to_numpy(dtype=float)

    quality = _quality_array(o, h, l, c)
    sh_price, sl_price = _confirmed_swings_global(h, l, SWING_K)
    structure = _structure_array(sh_price, sl_price, quality)
    location = _location_array(h, l, c, structure)
    momentum = _momentum_array(o, c)

    state = np.array([f"{s}|{loc}|{q}|{m}"
                      for s, loc, q, m in zip(structure, location, quality, momentum)],
                     dtype=object)

    out = pd.DataFrame({
        "structure": structure, "location": location,
        "quality": quality, "momentum": momentum, "state": state,
    }, index=df.index)
    return out


WARMUP_BARS = max(SWING_LOOKBACK, RANGE_WINDOW, QUALITY_WINDOW, MOMENTUM_LOOKBACK) + 5


# ===========================================================================
# validation against the real reference implementation
# ===========================================================================

def validate_against_chart_reader(df: pd.DataFrame, n_samples: int = 300, seed: int = 82):
    """Draws n_samples random bar indices (>= WARMUP_BARS), calls the REAL
    chart_reader.read_chart() on df.iloc[:t+1] for each, and compares against
    this module's vectorized label at index t. Returns per-axis agreement
    rates plus overall (all-4-axes-agree) rate — the honest evidence for how
    much the single documented approximation (structure's window-edge
    truncation) actually costs."""
    import datetime as _dt
    rng = np.random.default_rng(seed)
    n = len(df)
    lo = WARMUP_BARS
    if n <= lo + 1:
        raise ValueError("series too short to validate")
    idxs = rng.choice(np.arange(lo, n), size=min(n_samples, n - lo), replace=False)

    vec = label_eye_states(df)
    far_future = pd.Timestamp("2099-01-01", tz="UTC")

    agree = {"structure": 0, "location": 0, "quality": 0, "momentum": 0, "all4": 0}
    checked = 0
    disagreements = []
    for t in idxs:
        window = df.iloc[: int(t) + 1]
        try:
            real = CR.read_chart(window, prior_day=None, week=None, now=far_future)
        except Exception:
            continue
        checked += 1
        row = vec.iloc[int(t)]
        ok_all = True
        for axis in ("structure", "location", "quality", "momentum"):
            if real[axis] == row[axis]:
                agree[axis] += 1
            else:
                ok_all = False
                disagreements.append((int(t), axis, real[axis], row[axis]))
        if ok_all:
            agree["all4"] += 1

    rates = {k: (v / checked if checked else float("nan")) for k, v in agree.items()}
    return {"checked": checked, "rates": rates, "sample_disagreements": disagreements[:25]}


if __name__ == "__main__":
    import time
    import step7_deep_search as S7

    d = S7.fetch_bybit_deep("1h", "BTCUSDT")
    t0 = time.time()
    labeled = label_eye_states(d)
    t1 = time.time()
    print(f"labeled {len(d)} BTC 1h bars in {t1 - t0:.2f}s")
    vr = validate_against_chart_reader(d, n_samples=200)
    print("validation:", vr["checked"], "checked, rates:", vr["rates"])
    if vr["sample_disagreements"]:
        print("sample disagreements:", vr["sample_disagreements"][:10])
