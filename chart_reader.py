"""
chart_reader.py — give the machine a trader's PERCEPTION of the chart,
computed from candle data alone, running 24/7 inside the always-on daemon
with no API key and no cost.

THE INSIGHT THIS MODULE IS BUILT ON (Wallace, 2026-07-24): "Could you not
just build something that gives you a visual read instead of having to take
screenshots? Doesn't BloFin give you market data?" Yes. Everything a
trader's eye extracts from a chart — "big green body closing on its high",
"sellers keep rejecting this level", "this is chop, stay out" — is
COMPUTABLE FROM OHLCV. The candlestick image is only a rendering of the same
numbers. The machine's missing capability was never "vision"; it was that
nothing ever translated numbers into the perceptual language a trader
actually thinks in. This module is that translation layer: pure,
deterministic, offline, no model call, no network, no cost.

(A sibling module, chart_eyes.py, takes the OTHER path to the same
question — it renders real PNGs and hands them to an actual vision-capable
reader. That module is expensive/scheduled and needs a real "eye". This one
is the always-on, free, numbers-only path. Same read schema on purpose, so
the two can be compared against each other and against a human eye — that
comparison is exactly what verify_read() below is for.)

THREE PIECES:
  1. read_chart()   — the pure function. candles_df (+ optional prior_day /
                       week context) in, the strict read schema out. No
                       network, no model, fully deterministic.
  2. verify_read()   — renders a clean candlestick PNG (+ a zoomed companion
                       of the newest ~30 bars) from the SAME candles, and
                       returns it next to the computed read, so a
                       vision-capable reviewer can look at the picture and
                       check whether the computed read agrees with real
                       perception. That comparison loop is how this module
                       gets tuned to agree with a human eye.
  3. store_read() / get_read() / get_read_history() — a rolling memory of
                       computed reads in state["chart_reads"][symbol], capped
                       at CHART_READ_HISTORY_CAP entries per symbol.

HARD SAFETY
  ADVISORY_ONLY = True — no book may act on a stored read until a
  validation round proves these reads actually improve outcomes. This
  module only perceives; store_read() exists to build that evidence.

  NO EXCEPTIONS CURRENTLY. One was granted on 2026-07-24 (round 83:
  daily_pick's washout trigger dropped its vote on a "messy" read, having
  beaten a random-skip control at the 98th percentile on BTC and ETH) and
  REVOKED the same night by round 88, which attacked it properly:
    - on 3 assets it had never been selected on, only XRP passed; SOL
      showed no information content and DOGE was worse than useless. SOL
      is a symbol daily_pick actually trades.
    - across 122 cells, 28 cleared the 90th percentile where ~12 are
      expected by chance, but 45 landed at or BELOW the 10th where ~12 are
      expected. The read carries real information and is double-edged; we
      cannot tell in advance which edge a given symbol gets.
  Two winning cells out of 36 was always inside what luck produces. The
  lesson for the next exception: two assets agreeing is not evidence, it
  is a hypothesis. Test a third and a fourth before shipping.

This file is self-contained on purpose (no import from chart_eyes.py, its
sibling) except for ONE deliberate reuse: swing/pivot detection uses the
repo's existing confirmed_swings() helper (step41_shorts.py) rather than
reinventing fractal-swing math a third time in this project.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from step41_shorts import confirmed_swings

# ---------------------------------------------------------------------------
# HARD SAFETY
# ---------------------------------------------------------------------------

ADVISORY_ONLY = True   # no book may act on a chart_reads[] entry until a
                        # validation round proves these reads improve
                        # outcomes; the store exists to build that evidence.

# ---------------------------------------------------------------------------
# vocabulary — the ONLY values a read is allowed to use (see chart_eyes.py's
# identical discipline: a free-text field drifts into synonyms and stops
# being comparable over time).
# ---------------------------------------------------------------------------

VALID_STRUCTURE = {"uptrend", "downtrend", "range", "chop", "transition"}
VALID_LOCATION = {
    "at range low", "mid range", "at range high",
    "breaking out", "breaking down", "pulling back in trend",
}
VALID_QUALITY = {"clean", "messy"}
VALID_MOMENTUM = {"expanding", "contracting", "stalling"}
VALID_BEST_TOOL = {"trend-follow", "range-fade", "breakout", "stand aside"}

VALID_CANDLE_COLOR = {"green", "red"}
VALID_BODY = {"large", "average", "small", "doji"}
VALID_WICKS = {"long upper", "long lower", "both", "none"}
VALID_CLOSE_POSITION = {"near high", "upper half", "middle", "lower half", "near low"}

REQUIRED_COLUMNS = ("open", "high", "low", "close")

# ===========================================================================
# THRESHOLDS — every number below is a deliberate choice, documented, so a
# future reader can argue with it rather than guess where it came from.
# ===========================================================================

# --- candle-character baseline -------------------------------------------
BASELINE_WINDOW = 20
# How many bars (strictly BEFORE the bar being classified) feed the median
# body used to call a body "large"/"small". 20 bars is roughly a trading
# day on the 1h chart this project runs on — long enough to smooth out one
# freak bar, short enough to track a genuine regime shift within a session.

LARGE_BODY_MULT = 1.5
SMALL_BODY_MULT = 0.5
# A body is "large" at 1.5x the local median (a bar that's 50% bigger than
# what's typical is the kind of bar a trader's eye actually snaps to) and
# "small" at half the median or less. Everything in between is "average" —
# deliberately a wide band, because most bars in a real session ARE
# unremarkable and calling them all "large-ish" or "small-ish" would make
# the vocabulary meaningless.

DOJI_BODY_RATIO = 0.10
# Classic charting definition: body under 10% of the bar's own high-low
# range is a doji, full stop. This is range-relative, not baseline-relative
# — a doji is a doji regardless of how volatile the recent session has
# been, because it's a statement about THIS bar's open vs close, not about
# how big bars have been lately.

# --- wicks ------------------------------------------------------------
LONG_WICK_RATIO = 0.40
# A wick covering 40%+ of the bar's total range is unmistakably a rejection
# wick to a trader's eye — the kind of tail you'd point at on a chart and
# say "look, it got rejected there." Below that, wicks read as normal
# noise, not a story.

# --- close position within the bar's own range -------------------------
POS_NEAR_HIGH = 0.80
POS_UPPER_HALF = 0.55
POS_LOWER_HALF = 0.45   # (implicitly: below this and above POS_NEAR_LOW)
POS_NEAR_LOW = 0.20
# Splits the bar's own [low, high] into five bands. The top/bottom 20% are
# "near high"/"near low" (unambiguously at an extreme); the middle 10%
# (0.45-0.55) is genuinely "middle"; the remaining two bands are the
# ordinary upper/lower halves. Symmetric on purpose.

# --- quality (is this chart "clean" or "messy" to a disciplined trader) --
QUALITY_WINDOW = 8
# CALIBRATED AGAINST A REAL FRAME (2026-07-24, BTC-USDT 1h): a 10-bar window
# let a single large capitulation bar sitting 9 bars back drag its
# trend-efficiency into the window and mask the tight, overlapping
# congestion that followed it — a human reviewer looking at the same PNG
# called the tail "textbook congestion, messy" while the 10-bar read said
# "clean." The read must describe WHERE PRICE IS **NOW**, not the shape of
# the move that got it there. At 8 bars the window is short enough that an
# outlier bar from the PRIOR regime ages out within a bar or two of it
# happening, while still spanning close to a third of a trading day on this
# project's 1h chart — enough to tell real chop from 2-3 noisy prints.

DIRECTION_CHANGE_MESSY = 0.5
# If half or more of consecutive bar pairs flip direction (green-then-red-
# then-green...), that IS the textbook definition of chop: no bar's move
# survives the next bar. A disciplined trader skips this.

BODY_RATIO_MESSY = 0.35
# If the MEDIAN bar in the window has a body under 35% of its own range,
# most bars are indecisive (long wicks, small real bodies) rather than
# committed directional pushes — another chop signature.

OVERLAP_MESSY = 0.45
# An "inside bar" (high <= prior high AND low >= prior low) means that bar
# made zero net progress — it traded entirely within the prior bar's
# territory. If 45%+ of bars in the window are inside bars, price is
# stuck, not developing — the visual a trader calls "going nowhere."
# (Quality is "messy" if ANY ONE of these three fires — each is an
# independent, sufficient signature of chop; they don't need to agree.)

# --- structure (via confirmed swing highs/lows) -------------------------
SWING_K = 3
# confirmed_swings() (step41_shorts.py) needs K bars on each side to
# confirm a fractal swing point. K=3 requires a swing to hold for 3 bars
# either side before it counts — enough to filter single-bar noise spikes,
# short enough that on this project's 1h chart a swing is confirmed within
# ~3 hours of forming, which is what keeps "structure" responsive rather
# than stale.

SWING_LOOKBACK = 60
# Max closed bars fed into swing detection — roughly 2.5 days on 1h bars.
# Long enough to find at least 2-3 genuine swing points in a normal
# session, short enough that ancient structure doesn't dictate today's read.

# --- location (position within the active range) ------------------------
RANGE_WINDOW = 20
# Bars (strictly before the bar being located) that define the "active
# range" a trader is implicitly comparing price to — same window length as
# the body baseline, for the same reason (about a trading day of context).

RANGE_EDGE_HIGH = 0.70
RANGE_EDGE_LOW = 0.30
# CALIBRATED AGAINST A REAL FRAME (2026-07-24, BTC-USDT 1h): price sitting
# ~20% off the low of a ~$2,080 range read as "mid range" under the old
# 0.85/0.15 split — a human reviewer looking at the same PNG called that
# "down near the lows," not mid-range. The old split made the outer edges
# too narrow (only the extreme top/bottom 15%); a trader actually talks
# about range location closer to thirds. Bottom 30% = "at range low," top
# 30% = "at range high," the middle 40% = "mid range." Still wider than the
# close-position bands above, deliberately — location is judged against the
# whole recent range, a noisier reference than one bar's own high-low, so
# the edge zone still has to mean something, just not so narrow that a
# trader's own "down near the lows" call falls outside it.

# --- momentum (body/range progression) -----------------------------------
MOMENTUM_LOOKBACK = 4
# Compare the newer half of the last 4 closed bars against the older half.
# 4 is the minimum that lets "recent vs prior" mean anything (2 bars each)
# while staying tight enough that momentum reflects what's happening RIGHT
# NOW, not a multi-day average.

MOMENTUM_EXPAND_MULT = 1.15
MOMENTUM_CONTRACT_MULT = 0.85
# Recent bodies averaging 15%+ bigger than the prior pair = real expansion
# (bodies just don't grow by chance run to run); 15%+ smaller = real
# contraction. Between the two is "stalling" — a deliberately wide neutral
# band so noise doesn't flip the label bar to bar.

_CLOSE_PHRASE = {
    "near high": "closed near its high",
    "upper half": "closed in the upper half",
    "middle": "closed mid-range",
    "lower half": "closed in the lower half",
    "near low": "closed near its low",
}
_BODY_WORD = {"large": "big", "average": "", "small": "small", "doji": "doji"}
_WICK_PHRASE = {
    "long upper": "long upper wick",
    "long lower": "long lower wick",
    "both": "wicks on both sides",
    "none": None,
}


# ---------------------------------------------------------------------------
# small time / io helpers (self-contained on purpose — no cross-module
# import beyond confirmed_swings(), per the "files you own" boundary)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prepare(candles_df: pd.DataFrame) -> pd.DataFrame:
    if candles_df is None or len(candles_df) == 0:
        raise ValueError("chart_reader: candles_df is empty")
    missing = [c for c in REQUIRED_COLUMNS if c not in candles_df.columns]
    if missing:
        raise ValueError(f"chart_reader: candles_df missing columns {missing}")
    return candles_df.reset_index(drop=True)


def _hi_lo(obj):
    """Accept prior_day / week as a candles DataFrame, a {'high':.., 'low':..}
    dict, a (hi, lo) tuple, or None. Returns (hi, lo) as floats or
    (None, None)."""
    if obj is None:
        return None, None
    if isinstance(obj, pd.DataFrame):
        if obj.empty:
            return None, None
        return float(obj["high"].max()), float(obj["low"].min())
    if isinstance(obj, dict) and "high" in obj and "low" in obj:
        return float(obj["high"]), float(obj["low"])
    if isinstance(obj, (tuple, list)) and len(obj) == 2:
        return float(obj[0]), float(obj[1])
    raise ValueError(
        "chart_reader: prior_day/week must be a DataFrame with high/low "
        "columns, a {'high':.., 'low':..} dict, a (hi, lo) tuple, or None"
    )


def _is_forming(df: pd.DataFrame, now=None) -> bool:
    """The newest bar is FORMING (unfinished) if `now` hasn't reached the
    time its interval would close. Interval is inferred from the median gap
    between this frame's own timestamps — no hardcoded timeframe assumption,
    so the same function works on 15m/1h/4h/1d frames alike.

    Deliberately timestamp-driven rather than 'trust an external flag':
    BloFin's own get_candles() only ever returns CONFIRMED (closed) bars,
    so a live pull's newest row is correctly read as NOT forming here — the
    forming path only fires when the caller hands in a bar whose close time
    is still in the future relative to `now` (real-time use, or a test
    fixture built to exercise this)."""
    if "timestamp" not in df.columns or len(df) < 2:
        return False
    ts = pd.to_datetime(df["timestamp"])
    diffs = ts.diff().dropna()
    if diffs.empty:
        return False
    interval = diffs.median()
    if pd.isna(interval) or interval <= pd.Timedelta(0):
        return False

    last_ts = ts.iloc[-1]
    reference_now = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz=timezone.utc)
    if last_ts.tzinfo is None:
        last_ts = last_ts.tz_localize(timezone.utc)
    if reference_now.tzinfo is None:
        reference_now = reference_now.tz_localize(timezone.utc)

    expected_close = last_ts + interval
    return reference_now < expected_close


def _median_body(window_df: pd.DataFrame) -> float:
    if window_df is None or window_df.empty:
        return 0.0
    bodies = (window_df["close"] - window_df["open"]).abs()
    med = bodies.median()
    return float(med) if pd.notna(med) else 0.0


# ===========================================================================
# CANDLE-LEVEL CLASSIFICATION
# ===========================================================================

def _classify_candle(o: float, h: float, l: float, c: float, baseline_body: float) -> dict:
    """Classify ONE bar's body/wicks/close-position. `baseline_body` is the
    median body of the bars BEFORE this one (see BASELINE_WINDOW) — never
    this bar's own body, so classification never grades a bar against
    itself."""
    o, h, l, c = float(o), float(h), float(l), float(c)
    body = abs(c - o)
    rng = max(h - l, 1e-9)
    color = "green" if c >= o else "red"

    if body / rng <= DOJI_BODY_RATIO:
        body_class = "doji"
    elif baseline_body > 0 and body >= LARGE_BODY_MULT * baseline_body:
        body_class = "large"
    elif baseline_body > 0 and body <= SMALL_BODY_MULT * baseline_body:
        body_class = "small"
    else:
        body_class = "average"

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    long_upper = upper_wick >= LONG_WICK_RATIO * rng
    long_lower = lower_wick >= LONG_WICK_RATIO * rng
    if long_upper and long_lower:
        wick_class = "both"
    elif long_upper:
        wick_class = "long upper"
    elif long_lower:
        wick_class = "long lower"
    else:
        wick_class = "none"

    pos = (c - l) / rng
    if pos >= POS_NEAR_HIGH:
        close_position = "near high"
    elif pos >= POS_UPPER_HALF:
        close_position = "upper half"
    elif pos >= POS_LOWER_HALF:
        close_position = "middle"
    elif pos >= POS_NEAR_LOW:
        close_position = "lower half"
    else:
        close_position = "near low"

    return {
        "color": color, "body": body_class, "wicks": wick_class,
        "close_position": close_position, "_pos": pos,
    }


def _short_phrase(cls: dict) -> str:
    """The short, plain-English phrase used in recent_candles[]."""
    color, body, wicks = cls["color"], cls["body"], cls["wicks"]
    if body == "doji":
        base = f"{color} doji"
    else:
        word = _BODY_WORD[body]
        base = " ".join(f"{word} {color} body".split())
    bits = [base, _CLOSE_PHRASE[cls["close_position"]]]
    wp = _WICK_PHRASE[wicks]
    if wp:
        bits.append(wp)
    return ", ".join(bits)


def _tells(cls: dict, forming: bool) -> str:
    """The longer, current_candle.tells sentence — what this specific bar
    is saying, in priority order: doji (pure indecision) first, then
    rejection wicks (the clearest single-bar story a trader reads), then
    strong directional bodies, then the softer fallbacks."""
    color, body, wicks, pos = cls["color"], cls["body"], cls["wicks"], cls["close_position"]

    if body == "doji":
        base = "Open and close are essentially equal, indecision, neither side in control."
    elif wicks == "long lower" and pos in ("near high", "upper half"):
        base = "Sellers pushed it down and buyers stepped in hard, rejecting the low."
    elif wicks == "long upper" and pos in ("near low", "lower half"):
        base = "Buyers tried to push higher and sellers rejected it, sending it back down."
    elif body == "large" and pos == "near high" and color == "green":
        base = "Strong buying pressure, closed at the top of its range."
    elif body == "large" and pos == "near low" and color == "red":
        base = "Strong selling pressure, closed at the bottom of its range."
    elif wicks == "both":
        base = "Pushed both directions and went nowhere, a fight with no winner yet."
    elif body == "small":
        base = "Low conviction, small range, no one pressing hard."
    else:
        base = f"{color.capitalize()} bar, {body} body, {_CLOSE_PHRASE[pos]}."

    if forming:
        base += " Still forming, not closed yet."
    return base


def _dedupe_consecutive(values: list) -> list:
    """confirmed_swings() can confirm the SAME swing extreme at two adjacent
    bars when a turn is flat-topped/bottomed (the rolling-max/min window
    ties across neighboring bars) — that is one swing, not two, and letting
    it stand as two identical consecutive entries would make the most
    recent 'swing' comparison a same-value tie (neither higher nor lower)
    even when the real trend is unambiguous. Collapse consecutive
    duplicates before comparing."""
    out = []
    for v in values:
        if not out or v != out[-1]:
            out.append(v)
    return out


# ===========================================================================
# STRUCTURE, LOCATION, QUALITY, MOMENTUM
# ===========================================================================

def _structure(closed_df: pd.DataFrame, quality: str):
    """Confirmed-swing structure via step41_shorts.confirmed_swings() (see
    SWING_K/SWING_LOOKBACK above): higher-highs + higher-lows = uptrend,
    the mirror = downtrend. If the two legs DISAGREE (a higher high but a
    lower low, or a lower high but a higher low) the prior chain just
    broke — that's "transition", not a coin flip between the two. With
    fewer than 2 confirmed swings on each side there isn't enough structure
    to call a trend at all: "range" if the recent bars are orderly (quality
    clean), "chop" if they aren't — a trader doesn't call an unclear chart
    a trend just because swings haven't confirmed yet."""
    window = closed_df.tail(SWING_LOOKBACK).reset_index(drop=True)
    if len(window) < 2 * SWING_K + 1:
        structure = "chop" if quality == "messy" else "range"
        return structure, [], []

    sh_price, sl_price = confirmed_swings(window, SWING_K)
    swing_highs = _dedupe_consecutive(sh_price.dropna().to_list())
    swing_lows = _dedupe_consecutive(sl_price.dropna().to_list())

    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hd = swing_highs[-1] - swing_highs[-2]
        ld = swing_lows[-1] - swing_lows[-2]
        if hd > 0 and ld > 0:
            structure = "uptrend"
        elif hd < 0 and ld < 0:
            structure = "downtrend"
        elif (hd > 0 and ld < 0) or (hd < 0 and ld > 0):
            structure = "transition"
        else:
            structure = "range"
    else:
        structure = "chop" if quality == "messy" else "range"

    return structure, swing_highs, swing_lows


def _quality(closed_df: pd.DataFrame) -> str:
    """See QUALITY_WINDOW / DIRECTION_CHANGE_MESSY / BODY_RATIO_MESSY /
    OVERLAP_MESSY above. Any ONE of the three chop signatures firing is
    enough to call the chart messy — they are independent, sufficient
    tells, not a vote."""
    window = closed_df.tail(QUALITY_WINDOW)
    if len(window) < 3:
        return "messy"   # not enough bars to call anything "clean"

    o = window["open"].to_numpy(dtype=float)
    h = window["high"].to_numpy(dtype=float)
    l = window["low"].to_numpy(dtype=float)
    c = window["close"].to_numpy(dtype=float)
    rng = np.maximum(h - l, 1e-9)

    median_body_ratio = float(np.median(np.abs(c - o) / rng))

    directions = np.sign(c - o)
    nonzero_pairs = 0
    changes = 0
    for i in range(1, len(directions)):
        a, b = directions[i - 1], directions[i]
        if a != 0 and b != 0:
            nonzero_pairs += 1
            if a != b:
                changes += 1
    direction_change_rate = (changes / nonzero_pairs) if nonzero_pairs else 0.0

    inside = sum(1 for i in range(1, len(window)) if h[i] <= h[i - 1] and l[i] >= l[i - 1])
    overlap_rate = (inside / (len(window) - 1)) if len(window) > 1 else 0.0

    if (direction_change_rate >= DIRECTION_CHANGE_MESSY
            or median_body_ratio < BODY_RATIO_MESSY
            or overlap_rate >= OVERLAP_MESSY):
        return "messy"
    return "clean"


def _location(closed_df: pd.DataFrame, current_row, forming: bool, structure: str,
               prior_day, week):
    """Position within the active range (RANGE_WINDOW bars BEFORE the bar
    being located, so a genuine breakout can be told apart from 'still
    inside the range that produced it'), cross-checked against the prior
    day's and week's range when given. A 'breaking out'/'breaking down'
    call requires clearing BOTH the local active range AND the prior day's
    range (when known) — a new local high that's still inside yesterday's
    range is not a real breakout to a trader's eye, it's noise."""
    prior_window = closed_df if forming else closed_df.iloc[:-1]
    prior_window = prior_window.tail(RANGE_WINDOW)

    if prior_window.empty:
        range_hi = range_lo = None
    else:
        range_hi = float(prior_window["high"].max())
        range_lo = float(prior_window["low"].min())

    last_price = float(current_row["close"])
    day_hi, day_lo = _hi_lo(prior_day)
    week_hi, week_lo = _hi_lo(week)

    if range_hi is None:
        location = "mid range"
    elif last_price > range_hi and (day_hi is None or last_price > day_hi):
        location = "breaking out"
    elif last_price < range_lo and (day_lo is None or last_price < day_lo):
        location = "breaking down"
    else:
        pos = (last_price - range_lo) / (range_hi - range_lo) if range_hi > range_lo else 0.5
        if pos >= RANGE_EDGE_HIGH:
            location = "at range high"
        elif pos <= RANGE_EDGE_LOW:
            location = "at range low"
        elif structure in ("uptrend", "downtrend"):
            location = "pulling back in trend"
        else:
            location = "mid range"

    levels = {"range_hi": range_hi, "range_lo": range_lo, "day_hi": day_hi,
              "day_lo": day_lo, "week_hi": week_hi, "week_lo": week_lo}
    return location, levels


def _momentum(closed_df: pd.DataFrame) -> str:
    """See MOMENTUM_LOOKBACK/MULT above: newer-half vs older-half average
    body over the last few closed bars."""
    tail = closed_df.tail(MOMENTUM_LOOKBACK)
    bodies = (tail["close"] - tail["open"]).abs().to_numpy(dtype=float)
    n = len(bodies)
    if n < 2:
        return "stalling"

    half = n // 2
    prior = bodies[:n - half]
    recent = bodies[n - half:]
    prior_mean = float(prior.mean())
    recent_mean = float(recent.mean())

    if prior_mean <= 0:
        return "expanding" if recent_mean > 0 else "stalling"
    ratio = recent_mean / prior_mean
    if ratio >= MOMENTUM_EXPAND_MULT:
        return "expanding"
    if ratio <= MOMENTUM_CONTRACT_MULT:
        return "contracting"
    return "stalling"


def _best_tool(structure: str, location: str, quality: str, momentum: str):
    """Derives (tradeable, best_tool). Order matters:
      1. A genuine break (location says so) is checked FIRST — a breakout
         can fire out of a messy/chop chart by definition (compression
         resolving), so it isn't gated behind the quality check the way
         everything else is. It's only marked untradeable if the chart was
         messy AND momentum isn't confirming the break (classic fakeout
         setup).
      2. Otherwise, a messy chart is stand-aside, full stop — a disciplined
         trader doesn't trend-follow or range-fade chop.
      3. A clean trending chart is trend-follow.
      4. A clean range with price AT an edge is range-fade.
      5. Everything else (clean but no trend and not at an edge, e.g. mid
         range or a structure "transition") is stand-aside — there's no
         edge to trade yet."""
    if location in ("breaking out", "breaking down"):
        best_tool = "breakout"
        tradeable = not (quality == "messy" and momentum != "expanding")
    elif quality == "messy":
        best_tool = "stand aside"
        tradeable = False
    elif structure in ("uptrend", "downtrend"):
        best_tool = "trend-follow"
        tradeable = True
    elif structure == "range" and location in ("at range low", "at range high"):
        best_tool = "range-fade"
        tradeable = True
    else:
        best_tool = "stand aside"
        tradeable = False
    return tradeable, best_tool


def _key_levels(levels: dict, swing_highs: list, swing_lows: list) -> list:
    candidates = [levels.get("range_hi"), levels.get("range_lo"),
                  levels.get("day_hi"), levels.get("day_lo"),
                  levels.get("week_hi"), levels.get("week_lo")]
    if swing_highs:
        candidates.append(swing_highs[-1])
    if swing_lows:
        candidates.append(swing_lows[-1])

    out = []
    for v in candidates:
        if v is None:
            continue
        v = float(v)
        if not any(abs(v - seen) < 1e-9 for seen in out):
            out.append(v)
    return sorted(out)


_TOOL_PHRASE = {
    "trend-follow": "ride the trend",
    "range-fade": "fade the edge",
    "breakout": "watch for the break to run",
    "stand aside": "stand aside, nothing to do here",
}


def _one_line(structure: str, location: str, quality: str, best_tool: str) -> str:
    return (f"{quality.capitalize()} {structure}, {location}. "
            f"{_TOOL_PHRASE[best_tool].capitalize()}.")


# ===========================================================================
# 1. read_chart() — THE PURE FUNCTION
# ===========================================================================

def read_chart(candles_df: pd.DataFrame, prior_day=None, week=None, now=None) -> dict:
    """Compute a trader's PERCEPTION of `candles_df` — pure, deterministic,
    no network, no model. See the module docstring / VALID_* constants for
    the schema and its exact vocabulary, and the THRESHOLDS block above for
    every numeric cutoff and why it was chosen.

    candles_df: DataFrame with (at least) open/high/low/close columns,
        oldest-first, one row per bar. A 'timestamp' column (if present) is
        used to detect whether the newest bar is still forming.
    prior_day / week: optional context for the LOCATION read — each may be
        a candles DataFrame (high/low columns used), a {'high':, 'low':}
        dict, a (hi, lo) tuple, or None.
    now: optional reference timestamp for forming-bar detection (defaults
        to real UTC now); pass explicitly for deterministic tests.
    """
    df = _prepare(candles_df)
    n = len(df)
    last_idx = n - 1

    forming = _is_forming(df, now)
    closed_df = df.iloc[:-1] if forming else df

    # bars strictly BEFORE the newest one — the baseline for classifying
    # both the newest bar and every bar in recent_candles, so nothing is
    # ever graded against itself.
    baseline_src = df.iloc[:last_idx]
    baseline_body = _median_body(baseline_src.tail(BASELINE_WINDOW))

    current_row = df.iloc[last_idx]
    current_cls = _classify_candle(current_row["open"], current_row["high"],
                                    current_row["low"], current_row["close"],
                                    baseline_body)
    current_candle = {
        "color": current_cls["color"], "body": current_cls["body"],
        "wicks": current_cls["wicks"], "close_position": current_cls["close_position"],
        "forming": forming, "tells": _tells(current_cls, forming),
    }

    recent_src = baseline_src.tail(5)
    recent_candles = [
        _short_phrase(_classify_candle(r.open, r.high, r.low, r.close, baseline_body))
        for r in recent_src.itertuples()
    ]

    quality = _quality(closed_df)
    structure, swing_highs, swing_lows = _structure(closed_df, quality)
    location, level_ctx = _location(closed_df, current_row, forming, structure, prior_day, week)
    momentum = _momentum(closed_df)
    tradeable, best_tool = _best_tool(structure, location, quality, momentum)
    key_levels = _key_levels(level_ctx, swing_highs, swing_lows)
    one_line = _one_line(structure, location, quality, best_tool)

    return {
        "structure": structure,
        "location": location,
        "quality": quality,
        "momentum": momentum,
        "key_levels": key_levels,
        "tradeable": tradeable,
        "best_tool": best_tool,
        "recent_candles": recent_candles,
        "current_candle": current_candle,
        "one_line": one_line,
    }


# ===========================================================================
# 2. verify_read() — RENDER + COMPUTE, SIDE BY SIDE
# ===========================================================================

BG_COLOR = "#0b0f14"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#e5e7eb"
UP_COLOR = "#26d07c"
DOWN_COLOR = "#ef4444"
FORMING_EDGE = "#facc15"
LAST_PRICE_COLOR = "#facc15"

FIGSIZE = (14.0, 8.0)   # x DPI=100 -> 1400x800px
DPI = 100
ZOOM_BARS = 30


def _pick_x_ticks(n: int, want: int = 6) -> list:
    if n <= want:
        return list(range(n))
    step = max(1, n // want)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


def _render_png(df: pd.DataFrame, out_path, *, n_closed: int, title: str) -> Path:
    """Pure, network-free candlestick renderer. Draws every row of `df` as
    a dark-theme candle; rows at index >= n_closed are drawn dashed/yellow
    ('forming') so an unfinished bar is never mistaken for a closed one on
    the picture either."""
    if df is None or len(df) == 0:
        raise ValueError("chart_reader: cannot render an empty candle frame")

    # matplotlib is imported HERE, not at module scope, and deliberately:
    # since round 83 daily_pick imports this module on the live path, and
    # matplotlib is a local-only dev dependency (not in requirements.txt).
    # A module-scope import would take the whole live worker down on
    # deploy. read_chart() is pure pandas/numpy and needs no plotting.
    import matplotlib
    matplotlib.use("Agg")      # headless — never try to open a display
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    df = df.reset_index(drop=True)
    n = len(df)

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    body_w = 0.62
    for i in range(n):
        o = float(df.at[i, "open"]); h = float(df.at[i, "high"])
        l = float(df.at[i, "low"]);  c = float(df.at[i, "close"])
        up = c >= o
        color = UP_COLOR if up else DOWN_COLOR
        forming = i >= n_closed

        ax.add_line(Line2D([i, i], [l, h], color=color, linewidth=1.1,
                            solid_capstyle="round", zorder=2))

        y0, height = (o, c - o) if up else (c, o - c)
        if height <= 0:
            span = h - l
            height = max(span * 0.015, abs(c) * 0.0006, 1e-9)
            y0 = (o + c) / 2 - height / 2

        edge = FORMING_EDGE if forming else color
        lw = 1.6 if forming else 0.0
        ls = (0, (3, 2)) if forming else "-"
        rect = Rectangle((i - body_w / 2, y0), body_w, height,
                          facecolor=color, edgecolor=edge, linewidth=lw,
                          linestyle=ls, zorder=3)
        ax.add_patch(rect)
        if forming:
            ax.text(i, h + (h - l) * 0.10 + 1e-9, "forming", ha="center",
                    va="bottom", fontsize=7, color=FORMING_EDGE, zorder=5)

    last_price = float(df["close"].iloc[-1])
    ax.axhline(last_price, color=LAST_PRICE_COLOR, linewidth=0.7,
               linestyle=":", zorder=1)
    ax.text(n - 1 + 0.6, last_price, f" {last_price:,.4g}",
            color=LAST_PRICE_COLOR, fontsize=9, va="center",
            fontweight="bold", zorder=6)

    tick_idx = _pick_x_ticks(n)
    ax.set_xticks(tick_idx)
    labels = []
    for i in tick_idx:
        ts = df["timestamp"].iloc[i] if "timestamp" in df.columns else i
        labels.append(ts.strftime("%m-%d %H:%M") if hasattr(ts, "strftime") else str(ts))
    ax.set_xticklabels(labels, rotation=25, ha="right", color=TEXT_COLOR, fontsize=8)
    ax.set_xlim(-1, n - 1 + 3.2)

    ax.tick_params(axis="y", colors=TEXT_COLOR, labelsize=9)
    ax.set_ylabel("price", color=TEXT_COLOR, fontsize=10)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    ax.set_title(title, color=TEXT_COLOR, fontsize=12, loc="left", pad=10)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def verify_read(candles_df: pd.DataFrame, out_png, *, prior_day=None, week=None,
                 now=None, symbol: str = "", timeframe: str = "",
                 zoom_bars: int = ZOOM_BARS):
    """Compute the read AND render it, so a vision-capable reviewing agent
    can look at the picture and check whether the computed read matches
    real perception — the tuning loop this module is built around.

    Returns (read, image_paths) where image_paths = {"full": <path to the
    whole `candles_df` window>, "zoom": <path to the newest ~zoom_bars
    bars>}. Both PNGs mark the forming bar (if any) the same way
    current_candle.forming does, so the two never disagree."""
    df = _prepare(candles_df)
    read = read_chart(df, prior_day=prior_day, week=week, now=now)

    n = len(df)
    forming = read["current_candle"]["forming"]
    n_closed = n - 1 if forming else n

    label = " ".join(p for p in (symbol, timeframe) if p)
    out_png = Path(out_png)

    full_title = f"{label}  ·  full ({n} bars)".strip("  ·  ").strip()
    full_path = _render_png(df, out_png, n_closed=n_closed, title=full_title or f"full ({n} bars)")

    zoom_n = min(zoom_bars, n)
    zoom_df = df.tail(zoom_n).reset_index(drop=True)
    zoom_n_closed = max(0, n_closed - (n - zoom_n))
    zoom_path_out = out_png.with_name(out_png.stem + "_zoom" + out_png.suffix)
    zoom_title = f"{label}  ·  zoom (last {zoom_n})".strip("  ·  ").strip()
    zoom_path = _render_png(zoom_df, zoom_path_out, n_closed=zoom_n_closed,
                            title=zoom_title or f"zoom (last {zoom_n})")

    return read, {"full": str(full_path), "zoom": str(zoom_path)}


# ===========================================================================
# 3. store_read() / get_read() / get_read_history() — a rolling memory
# ===========================================================================

CHART_READ_HISTORY_CAP = 20   # rolling cap per symbol — a memory, not an archive


def store_read(state: dict, symbol: str, read: dict) -> dict:
    """Persist one computed read into state["chart_reads"][symbol], a
    rolling list capped at CHART_READ_HISTORY_CAP entries (oldest dropped
    first). Returns the stored entry (== read, with 'as_of' filled in only
    if the caller omitted it). ADVISORY_ONLY: nothing downstream may act on
    this yet — see module docstring."""
    entry = dict(read)
    entry.setdefault("as_of", _now_iso())

    bucket = state.setdefault("chart_reads", {})
    history = bucket.setdefault(symbol, [])
    history.append(entry)
    del history[:-CHART_READ_HISTORY_CAP]
    return entry


def get_read(state: dict, symbol: str):
    """The most recent stored read for `symbol`, or None."""
    history = (state or {}).get("chart_reads", {}).get(symbol)
    return history[-1] if history else None


def get_read_history(state: dict, symbol: str, n: int = CHART_READ_HISTORY_CAP) -> list:
    """Up to the last `n` stored reads for `symbol`, oldest-first. Empty
    list if nothing stored yet."""
    hist = (state or {}).get("chart_reads", {}).get(symbol, [])
    return hist[-n:] if n else list(hist)


# ===========================================================================
# DEMONSTRATION — pull BTC-USDT 1h live, print the read, render the image
# ===========================================================================

def _demo():
    from config import make_exchange

    ex, symbol = make_exchange("live")
    df = ex.get_candles(symbol, timeframe="1h", limit=150)

    read = read_chart(df)

    print("=" * 72)
    print(f"CHART READER — live demo — {symbol} 1h — {len(df)} bars")
    print("=" * 72)
    import json
    print(json.dumps(read, indent=2))

    out_dir = Path("chart_reads_demo")
    out_dir.mkdir(exist_ok=True)
    out_png = out_dir / f"{symbol.replace('/', '-')}_1h.png"
    read2, images = verify_read(df, out_png, symbol=symbol, timeframe="1h")

    print("\nRendered verification images:")
    print(f"  full: {images['full']}")
    print(f"  zoom: {images['zoom']}")
    print("\nread_chart() == verify_read()'s computed read:", read == read2)


if __name__ == "__main__":
    _demo()
