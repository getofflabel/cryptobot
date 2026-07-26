"""
trader.py — THE READING LAYER. What is on the chart, and nothing else.

WHOSE CHART READING THIS IS (Wallace, 2026-07-25):

    "lets give up trying to find our own strategy, its a waste of time. use
     these guy's ideology, thats it, and just trade as is"

    "you and i are not professionals. tjr is. if you were a professional you
     would be profitable already. there is no disagreeing with him, only
     testing it when you find the opputunity"

So every definition below is his, transcribed into step431_tjr_spec_entries.md,
step432_tjr_spec_confluences.md, step433_tjr_spec_management.md,
step434_tjr_spec_bias_and_strategy.md, with his own contradictions resolved in
step436_spec_conflicts_resolved.md. Our own research rounds govern the
ENGINEERING only — no lookahead, thresholds recomputed per instrument, numbers
never invented — because those are lessons about how to build and measure.

===========================================================================
THIS FILE DECIDES NOTHING
===========================================================================
There is no signal, no entry, no direction, no order, no scoring, no
weighting and no threshold that anybody here made up. It reads a chart and
hands back what is on it. The decision layer is being built separately from
the finished specs and consumes `ChartRead`.

===========================================================================
WHAT IT COMPUTES
===========================================================================
  the two-candle pivot   an up candle then a down candle makes a HIGH at the
                         HIGHER of the two wicks; a down candle then an up
                         candle makes a LOW at the LOWER of the two. Run
                         separately on each timeframe's own candles and never
                         mixed, because the same visual turn is a pivot on one
                         chart and not on another. This one definition is the
                         anchor under trend state, both equilibrium anchors and
                         the break of structure.
  trend state            higher highs with higher lows, or the mirror.
  break of structure     THE ASYMMETRY: the level is set by a WICK, the break
                         is judged by a candle BODY closing STRICTLY beyond it.
                         A close sitting exactly on the level is not a break. A
                         wick past it does nothing at all. In an uptrend only
                         the most recent LOW is watched; in a downtrend only
                         the most recent HIGH. A higher low inside a downtrend
                         changes nothing.
  levels, tagged by      4-hour and 1-hour pivots are levels worth trading off.
  where they came from   5-minute pivots are NOT, and carrying the timeframe on
                         the level is what stops one being treated as one.
  session extremes       New York time always. Asia 18:00-03:00, London
                         03:00-08:30, pre-market 08:30-09:30, New York
                         09:30-17:00. Previous day and previous week high and
                         low.
  stacked and            several unswept levels sitting at about the same
  roughly-equal levels   price. The tolerance is a NAMED PARAMETER he never
                         states, so nothing is marked until it is filled in.
  taking a level, in     PENDING the moment price trades through it. CONFIRMED
  TWO STATES             only once a break of structure follows in the opposite
                         direction. A level traded straight through with no
                         reaction was never taken and never becomes taken.
  fair value gaps        three candles: bullish when the LOW of the third is
                         above the HIGH of the first, bearish mirrored, box
                         between those two prices. Killed by a candle CLOSING
                         through it, never by a wick. Also killed once the trend
                         continued without needing it. Never dragged forward.
                         Stacks tracked, and the gap whose death inverts the
                         trend identified.
  gap inversion          that same close-through, which he uses INSTEAD of
                         waiting for a break of structure because it fires
                         earlier.
  equilibrium            the exact halfway point between the MOST RECENT swing
                         low and the MOST RECENT swing high. Re-anchored the
                         moment a new extreme forms. Below it is cheap, above it
                         is expensive.
  the overnight gap      a level the market jumped over without ever trading to
                         it was not taken. SPY stops at 16:00 and reopens at
                         09:30, so this is real here in a way it never was on a
                         market that does not close.
  instrument agreement   whether SPY and QQQ are telling the same story on the
                         5-minute, which is a reading, not a rule.

NOT BUILT ON PURPOSE: order blocks and breaker blocks. He retired both, in one
sentence: "I no longer use order blocks. I no longer use breaker blocks. The
only continuation confluences that I need are equilibrium and fair value gaps."
Three bootcamp days teach them in detail, which is exactly why building them
would have been the natural mistake.

===========================================================================
THE PARAMETERS HE NEVER STATES
===========================================================================
Named in NEEDS_VIDEO, defaulting to None in `Unresolved`, and anything that
depends on one is simply NOT COMPUTED and reported as unresolved. A number
guessed here becomes a fitted setting later and nobody remembers it was
invented. TODO(video) on every one.

===========================================================================
THE VENUE (step435_venue_decision.md)
===========================================================================
Alpaca paper, SPY and QQQ — the funds tracking the two indexes he trades. A
round trip costs 0.0035% of the position, measured over about 700,000 real
quotes, no commission. Fractional shares, so a position can be sized to the
cent against wherever the stop sits.

===========================================================================
LANGUAGE
===========================================================================
Name the ACTION, never the category. "Price traded through the prior low and
closed back above it", not "a liquidity sweep". "The level that proves the idea
wrong", not "the invalidation". "0.0035%", not "0.35 basis points". Every
percentage says which kind it is: a PRICE MOVE (how far price has to travel) or
a CHANGE IN THE POSITION'S VALUE.

SAFETY: no orders, no network, no live imports, imported by nothing live.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional

import numpy as np
import pandas as pd

NOT_DEPLOYED = True     # nothing live imports this
DECIDES_NOTHING = True  # this module reads; it does not choose

NEW_YORK = "America/New_York"


# ===========================================================================
# 1. THE PARAMETERS HE NEVER STATES
# ===========================================================================

NEEDS_VIDEO = {
    "A1_trading_window_end": (
        "He says he is 'never going to be trading an hour after New York market "
        "opens'. That reads two ways: he stops at 10:30, or he avoids the first "
        "hour. Separately, step436 section 4 records him starting around 09:50. "
        "The window's END is what is unresolved."),
    "A2_new_york_session_window": (
        "One video gives the New York session as 09:30-17:00 with a dead hour "
        "after, another as 08:30-18:00 covering the day with no gap. Asia and "
        "London agree in both, so the levels traded at the open are unaffected. "
        "09:30-17:00 is used here and the conflict is recorded."),
    "A3_roughly_equal_tolerance_pct": (
        "How close two highs must sit to count as roughly equal. His only number "
        "is one observation, 'literally 50 cents apart' on a 15-minute S&P chart, "
        "which is an instance and not a threshold."),
    "A3_minimum_stack_count": (
        "How many levels sitting together make a stack. He shows four and five "
        "and never states a floor."),
    "A4_news_candle_timeframe": (
        "He says to mark the high and low of the candle that prints on a "
        "high-impact release and never names which chart's candle."),
    "A5_consolidation_breakout_rule": (
        "He promises a rule for breaking out of sideways price and never gives "
        "it. Trend state sits at unknown through sideways price with no rule for "
        "leaving it other than a normal break."),
    "A7_which_entry_timeframe": (
        "One worked entry confirms on the 1-minute, another on the 5-minute. "
        "Whether both must agree, or one takes precedence, is never said."),
    "A8_protective_exit_buffer_pct": (
        "'We can put our stop loss above these highs.' Above by how much is "
        "never stated."),
    "A9_pending_lifetime_bars": (
        "A level taken with no reaction was never taken. How many bars before "
        "that is declared, he never says."),
    "A10_order_type_at_entry": (
        "'We can take a short position there' on the close of the trigger "
        "candle. Market on the close or a resting limit is not stated."),
    "A11_which_levels_are_tradeable": (
        "Session, previous-day and stacked levels work as both entries and "
        "objectives. News levels he calls 'advanced advanced' and says to stay "
        "off. Whether the bot may enter off one at all is unresolved."),
    "A12_equilibrium_reached_by_wick_or_body": (
        "Whether a wick past the halfway point counts as reaching it, or a body "
        "must close past. His language ('poke our head under') and his chart "
        "examples suggest the wick suffices; he never states it. Both readings "
        "are computed here and neither is chosen."),
    "A13_stack_grouping_test": (
        "Fair value gaps join one stack when there is 'no retracement between "
        "them', which he phrases as 'no black candle in between'. Implemented as "
        "no opposite-direction candle between the two gaps, which is his words "
        "taken literally, but he never says whether a doji or a tiny opposite "
        "candle breaks the stack."),
}


@dataclass(frozen=True)
class Unresolved:
    """Everything he never states. Every field defaults to None and stays None
    until somebody re-watches the video and fills it in DELIBERATELY.

    TODO(video): fill these one at a time, each with the video id and timestamp
    written next to it. Do not fit them to data. A number chosen because it
    backtested well is not his method, it is ours wearing his name."""
    A1_trading_window_end: Optional[str] = None
    A3_roughly_equal_tolerance_pct: Optional[float] = None   # a PRICE MOVE
    A3_minimum_stack_count: Optional[int] = None
    A4_news_candle_timeframe: Optional[str] = None
    A5_consolidation_breakout_rule: Optional[str] = None
    A7_which_entry_timeframe: Optional[str] = None
    A8_protective_exit_buffer_pct: Optional[float] = None    # a PRICE MOVE
    A9_pending_lifetime_bars: Optional[int] = None
    A10_order_type_at_entry: Optional[str] = None
    A11_which_levels_are_tradeable: Optional[tuple] = None
    A12_equilibrium_reached_by_wick_or_body: Optional[str] = None
    A13_stack_grouping_test: Optional[str] = None

    def missing(self) -> tuple[str, ...]:
        return tuple(k for k in vars(self) if getattr(self, k) is None)


UNRESOLVED = Unresolved()


# ===========================================================================
# 2. INSTRUMENT CONFIG — the only place per-instrument knowledge lives
# ===========================================================================

@dataclass(frozen=True)
class Instrument:
    """He trades US index futures. We read the funds tracking the same two
    indexes, on Alpaca. The timeframe split is part of the method rather than a
    preference, so it lives here as separate tuples:

      4-hour and daily   direction only, never entries
      1-hour and 4-hour  where the levels worth trading are marked
      5-minute           the working chart, "dictates like everything"
      1-minute           the entry only, explicitly NOT where levels are hunted
    """
    symbol: str
    direction_timeframes: tuple[str, ...] = ("1d", "4h")
    level_timeframes: tuple[str, ...] = ("4h", "1h")
    working_timeframe: str = "5m"
    entry_timeframe: Optional[str] = None      # "1m" when we hold it; we do not
    round_trip_cost_pct: float = 0.0035        # a PRICE MOVE, ~700k real quotes
    fractional_shares: bool = True


SPY = Instrument("SPY")
QQQ = Instrument("QQQ")

# The desk's own bar: a trade has to be worth at least five times what getting
# in and out costs. Reported, never enforced here.
COST_MULTIPLE_BAR = 5.0


# ===========================================================================
# 3. THE SESSION CLOCK — New York time, always
#
#   "we need to make sure that we are on Eastern time."
#
#   Asia and London are identical across every video. The New York window
#   conflicts between two of them (A2); 09:30-17:00 is used and the conflict is
#   carried rather than hidden.
# ===========================================================================

SESSIONS = {
    "Asia":        ((18, 0), (3, 0)),     # crosses midnight
    "London":      ((3, 0), (8, 30)),
    "pre-market":  ((8, 30), (9, 30)),
    "New York":    ((9, 30), (17, 0)),
}
NEW_YORK_OPEN = (9, 30)
BLACKOUT = ((17, 0), (18, 0))   # "you can't trade... it's called spread hour"


def _mins(t) -> int:
    return t[0] * 60 + t[1]


def new_york_index(d: pd.DataFrame) -> Optional[pd.DatetimeIndex]:
    if "timestamp" not in d.columns or len(d) == 0:
        return None
    ts = pd.to_datetime(d["timestamp"])
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    return pd.DatetimeIndex(ts).tz_convert(NEW_YORK)


def trading_day_of(ny: pd.DatetimeIndex) -> np.ndarray:
    """Which 18:00-to-18:00 trading day each bar belongs to, as a date string.
    A bar at or after 18:00 belongs to the NEXT calendar day, because that is
    the day whose London and New York sessions follow it — and it is how he
    defines the previous day, "all of those sessions encapsulated into one"."""
    day = pd.Series(ny.normalize())
    rolled = pd.Series((ny.hour * 60 + ny.minute) >= _mins(SESSIONS["Asia"][0]))
    return (day + pd.to_timedelta(rolled.astype(int), unit="D")
            ).dt.strftime("%Y-%m-%d").to_numpy()


def in_window(ny: pd.DatetimeIndex, window) -> np.ndarray:
    m = ny.hour * 60 + ny.minute
    s, e = _mins(window[0]), _mins(window[1])
    return (m >= s) & (m < e) if s < e else ((m >= s) | (m < e))


def session_of(stamp) -> str:
    m = stamp.hour * 60 + stamp.minute
    if _mins(BLACKOUT[0]) <= m < _mins(BLACKOUT[1]):
        return "blackout, no trading"
    for name, w in SESSIONS.items():
        s, e = _mins(w[0]), _mins(w[1])
        if (s <= m < e) if s < e else (m >= s or m < e):
            return name
    return "between sessions"


# ===========================================================================
# 4. THE OBJECTS
# ===========================================================================

@dataclass(frozen=True)
class Pivot:
    bar: int          # the bar it could FIRST have been known on
    price: float
    side: str         # "high" or "low"


@dataclass(frozen=True)
class Level:
    """One price the market might be pulled toward, and where it came from.
    `timeframe` is part of the level: a 5-minute high is not a level worth
    trading off, and this field is what stops one being treated as one."""
    price: float
    side: str             # "high" or "low"
    kind: str             # "4h pivot high", "London session low", ...
    timeframe: str        # "" for session and calendar levels
    origin_bar: int       # -1 when it is not a single bar
    tradeable_pool: bool  # is this one of the levels he actually watches
    traded_through: bool = False
    jumped_over: bool = False   # the market gapped past it without trading to it
    note: str = ""


@dataclass(frozen=True)
class BreakOfStructure:
    """A candle BODY closing STRICTLY past the most recent watched pivot.

        "We need a full candlestick body close above a high or underneath a low."
        "we don't actually close underneath the low right here because the
         candle body is equal with this low."   (ruled NOT a break)
    """
    direction: str        # "up" or "down"
    level: float
    bar: int
    timeframe: str
    source: str = "break of structure"   # or "gap inversion"


@dataclass(frozen=True)
class TrendRead:
    timeframe: str
    state: str            # "uptrend" / "downtrend" / "unknown"
    watched_low: Optional[float]     # in an uptrend, the only level that matters
    watched_high: Optional[float]    # in a downtrend, the only one
    last_swing_low: Optional[Pivot]
    last_swing_high: Optional[Pivot]
    breaks: tuple[BreakOfStructure, ...]
    detail: str


@dataclass(frozen=True)
class TakenLevel:
    """A level price traded past. TWO STATES, never one boolean.

      pending    price traded through it, and that is all that has happened.
                 "If price comes down and takes out a low and keeps going down,
                  is it a liquidity sweep? No. Because it's not reacting to it."
      confirmed  a break of structure (or a gap inversion, which he uses for the
                 same job because it fires earlier) printed AFTER that bar, in
                 the OPPOSITE direction. Nothing else converts it.
      no reaction  a break printed in the SAME direction instead: the trend
                 continuing, not turning.
    """
    level: Level
    state: str            # "pending" / "confirmed" / "no reaction" / "stale"
    turn_direction: str   # the way a turn out of it would go: "up" or "down"
    bar: int
    bars_ago: int
    extreme: float        # furthest price got past the level, which is the
                          # structure a protective exit would sit beyond
    confirmed_by: Optional[BreakOfStructure]
    detail: str


@dataclass(frozen=True)
class FairValueGap:
    """Three candles with a hole in the middle of them.

    Bullish: the LOW of the third is above the HIGH of the first. The box runs
    between those two prices. Bearish is the mirror. The colours of the first
    and third candles are irrelevant.

    It dies when a candle CLOSES through it, never on a wick. It also dies once
    the trend continued past the prior swing without ever needing it. It is
    never dragged forward in time."""
    side: str             # "bullish" or "bearish"
    top: float
    bottom: float
    created_bar: int
    timeframe: str
    state: str            # "live" / "touched" / "dead"
    touched_bar: Optional[int]
    died_bar: Optional[int]
    death_reason: str
    stack_id: int
    holds_the_trend: bool   # the BOTTOM gap of a bullish stack / TOP of a
                            # bearish one: the one whose death inverts the trend


@dataclass(frozen=True)
class Equilibrium:
    """The exact halfway point between the MOST RECENT swing low and the MOST
    RECENT swing high. He is angrier about this than anything else in the
    method, because students anchor it to an earlier swing.

    Below the halfway point is the cheap half, above it is the expensive half.
    Re-anchored the moment a new most-recent extreme forms."""
    timeframe: str
    trend: str
    anchor_low: float
    anchor_high: float
    price: float          # the halfway point
    where_price_sits: str  # "below the halfway point" / "above" / "at"
    reached_by_wick: bool
    reached_by_body: bool
    detail: str


@dataclass(frozen=True)
class SessionExtremes:
    name: str
    trading_day: str
    high: Optional[float]
    low: Optional[float]
    complete: bool
    bars: int


@dataclass(frozen=True)
class ChartRead:
    """Everything on the chart. The decision layer consumes this and nothing
    else — if a rule needs something that is not here, THIS layer gets extended
    rather than the decision layer reaching back into raw candles."""
    symbol: str
    working_timeframe: str
    as_of: Optional[str]
    price: float
    bars_read: int

    session: str
    trading_day: str
    minutes_since_new_york_open: Optional[int]

    levels: tuple[Level, ...]
    pools: tuple[Level, ...]              # only the ones he watches
    untouched_pools: tuple[Level, ...]
    taken: tuple[TakenLevel, ...]         # newest first

    trends: dict                          # {timeframe: TrendRead}
    gaps: dict                            # {timeframe: tuple[FairValueGap]}
    gap_inversions: tuple[BreakOfStructure, ...]
    equilibrium: dict                     # {timeframe: Equilibrium}
    sessions: tuple[SessionExtremes, ...]

    stats: dict
    unresolved: tuple[str, ...]

    def confirmed_takes(self):
        return tuple(t for t in self.taken if t.state == "confirmed")

    def pending_takes(self):
        return tuple(t for t in self.taken if t.state == "pending")

    def live_gaps(self, timeframe: str, side: Optional[str] = None):
        out = tuple(g for g in self.gaps.get(timeframe, ())
                    if g.state in ("live", "touched"))
        return out if side is None else tuple(g for g in out if g.side == side)

    def pools_above(self):
        return tuple(sorted((lv for lv in self.untouched_pools
                             if lv.price > self.price), key=lambda lv: lv.price))

    def pools_below(self):
        return tuple(sorted((lv for lv in self.untouched_pools
                             if lv.price < self.price), key=lambda lv: -lv.price))


# ===========================================================================
# 5. THE TWO-CANDLE PIVOT — the anchor under everything else
# ===========================================================================

def two_candle_pivots(d: pd.DataFrame) -> tuple[list[Pivot], list[Pivot]]:
    """HIS definition, and the only one this file uses.

        "a high consists of an up candle, then a down candle... we're looking
         for the highest wick of those two candlesticks"
        "a low consists of a down candle followed by an up candle... the lowest
         point of those two candlesticks"

    What does NOT count, said twice in two videos because students get it wrong:
    an up candle then another up candle is not a high; a down candle then
    another down candle is not a low.

    RUN PER TIMEFRAME, NEVER MIXED. "on the current time frame that we're in,
    the 4hour time frame, this is not a high."

    Measured against the centred fractal this project used to use, this level
    sits 35-44% closer to price on every one of 12 instruments tested, which
    for the same dollars risked is roughly double the position.

    No lookahead by construction: the pair (i, i+1) is fully known at bar i+1
    and the pivot is stamped at i+1, the bar you could first have known it."""
    o = d["open"].to_numpy(dtype=float)
    c = d["close"].to_numpy(dtype=float)
    h = d["high"].to_numpy(dtype=float)
    lo = d["low"].to_numpy(dtype=float)
    highs: list[Pivot] = []
    lows: list[Pivot] = []
    for i in range(len(d) - 1):
        if c[i] > o[i] and c[i + 1] < o[i + 1]:
            highs.append(Pivot(i + 1, float(max(h[i], h[i + 1])), "high"))
        elif c[i] < o[i] and c[i + 1] > o[i + 1]:
            lows.append(Pivot(i + 1, float(min(lo[i], lo[i + 1])), "low"))
    return highs, lows


# ===========================================================================
# 6. TREND STATE AND THE BREAK OF STRUCTURE
# ===========================================================================

def read_trend(d: pd.DataFrame, timeframe: str,
               extra_breaks: Optional[list[BreakOfStructure]] = None) -> TrendRead:
    """Walk the bars forward, maintaining trend state exactly as specified.

    IN AN UPTREND ONLY THE LOWS ARE WATCHED. IN A DOWNTREND ONLY THE HIGHS.

        "within an uptrend, how can we identify when the uptrend is broken?
         when a low gets closed underneath... within a downtrend... when we
         close above the most recent high within the trend."
        "we are looking at the MOST RECENT high that has been created."

    THE ASYMMETRY THAT IS EASY TO GET WRONG: the level is the full WICK of the
    two-candle pivot; the break is the candle's CLOSE, and it must be STRICTLY
    beyond. A close sitting exactly on the level is not a break — he hits that
    exact bar on tape and rules it out. A wick past the level does nothing at
    all: no state change, no event.

    A higher low inside a downtrend changes nothing. A lower high inside an
    uptrend changes nothing. "this is where a lot of people can get confused is
    they keep flipping their bias."

    From cold, his own procedure: look left, find the most recent high and the
    most recent low, and see which has been closed past most recently.

    Sideways price has no rule — he promises one and never gives it (A5), so the
    state stays unknown until a normal break fires.

    `extra_breaks` lets a gap inversion be fed in, because he uses one for
    exactly the same job and says it fires earlier."""
    highs, lows = two_candle_pivots(d)
    close = d["close"].to_numpy(dtype=float)
    n = len(d)
    injected = sorted(extra_breaks or [], key=lambda b: b.bar)
    inj = iter(injected)
    next_inj = next(inj, None)

    hi_iter, lo_iter = iter(highs), iter(lows)
    next_hi, next_lo = next(hi_iter, None), next(lo_iter, None)
    watched_hi = watched_lo = None
    last_hi = last_lo = None
    state = "unknown"
    breaks: list[BreakOfStructure] = []

    for i in range(n):
        while next_hi is not None and next_hi.bar <= i:
            watched_hi, last_hi = next_hi.price, next_hi
            next_hi = next(hi_iter, None)
        while next_lo is not None and next_lo.bar <= i:
            watched_lo, last_lo = next_lo.price, next_lo
            next_lo = next(lo_iter, None)

        while next_inj is not None and next_inj.bar == i:
            breaks.append(next_inj)
            state = "uptrend" if next_inj.direction == "up" else "downtrend"
            next_inj = next(inj, None)

        c = close[i]
        if state == "uptrend":
            if watched_lo is not None and c < watched_lo:       # strictly below
                breaks.append(BreakOfStructure("down", watched_lo, i, timeframe))
                state = "downtrend"
        elif state == "downtrend":
            if watched_hi is not None and c > watched_hi:       # strictly above
                breaks.append(BreakOfStructure("up", watched_hi, i, timeframe))
                state = "uptrend"
        else:
            if watched_hi is not None and c > watched_hi:
                breaks.append(BreakOfStructure("up", watched_hi, i, timeframe))
                state = "uptrend"
            elif watched_lo is not None and c < watched_lo:
                breaks.append(BreakOfStructure("down", watched_lo, i, timeframe))
                state = "downtrend"

    if state == "uptrend":
        detail = (f"an uptrend, so the only level being watched is the most "
                  f"recent low at {watched_lo:,.6g}; a body closing strictly "
                  f"below it flips the trend, a wick does not")
    elif state == "downtrend":
        detail = (f"a downtrend, so the only level being watched is the most "
                  f"recent high at {watched_hi:,.6g}; a body closing strictly "
                  f"above it flips the trend, a wick does not")
    else:
        detail = ("no trend established on this chart yet, and he never gives a "
                  "rule for breaking out of sideways price (A5), so this stays "
                  "unknown until a normal break fires")

    return TrendRead(timeframe, state, watched_lo, watched_hi, last_lo, last_hi,
                     tuple(sorted(breaks, key=lambda b: b.bar)), detail)


# ===========================================================================
# 7. FAIR VALUE GAPS, THEIR STACKS, AND THE INVERSION
# ===========================================================================

def find_fair_value_gaps(d: pd.DataFrame, timeframe: str,
                         trend_breaks: tuple[BreakOfStructure, ...] = ()
                         ) -> tuple[list[FairValueGap], list[BreakOfStructure]]:
    """Detect, maintain and retire every gap on this chart, and emit the
    inversions.

    DETECT, on the close of each candle, from the last three closed candles:
        bullish  low[i] > high[i-2]     box = [high[i-2], low[i]]
        bearish  high[i] < low[i-2]     box = [high[i], low[i-2]]
    The colours of the outer two candles are irrelevant: "we do not see colour,
    we are not racist". Overlapping wicks means there is no gap.

    KILL 1, a candle CLOSING through it, never a wick:
        "it's just like break of structure where we need to see a candlestick
         closure underneath this line in order for the gap to be invalidated."
    When the gap that dies is the one holding the trend up — the BOTTOM gap of a
    bullish stack, the TOP gap of a bearish one — that death IS the inversion,
    and he uses it in place of waiting for a break of structure precisely
    because it fires earlier.

    KILL 2, the trend continued without needing it: price closed past the prior
    swing extreme, so every gap behind it is deleted. He treats "used" and
    "never needed" identically.

    Gaps are NEVER dragged forward in time. "You're not going to drag it all the
    way over and say, yeah, this is going to be valid somewhere over here in
    like 3 years."

    STACKS: a new gap joins the previous one's stack when there was no
    opposite-direction candle between them — his "no black candle in between",
    taken literally. Whether a doji breaks a stack he never says (A13)."""
    o = d["open"].to_numpy(dtype=float)
    c = d["close"].to_numpy(dtype=float)
    h = d["high"].to_numpy(dtype=float)
    lo = d["low"].to_numpy(dtype=float)
    n = len(d)

    breaks_by_bar: dict[int, BreakOfStructure] = {b.bar: b for b in trend_breaks}

    # An inversion only fires INSIDE the matching trend: a bullish gap closing
    # through only inverts an UPTREND, a bearish one only a DOWNTREND. Without
    # that gate every stack-leading gap on a 5-minute chart would emit one and
    # the signal would mean nothing. The state per bar is rebuilt from the
    # break list rather than cached, so it stays causal.
    state_at = np.array(["unknown"] * n, dtype=object)
    cur = "unknown"
    for i in range(n):
        b = breaks_by_bar.get(i)
        if b is not None:
            cur = "uptrend" if b.direction == "up" else "downtrend"
        state_at[i] = cur

    gaps: list[dict] = []
    inversions: list[BreakOfStructure] = []
    stack_counter = 0
    last_gap_index: dict[str, int] = {}

    for i in range(n):
        # ---- maintain everything already alive -------------------------
        for g in gaps:
            if g["state"] == "dead" or i <= g["created_bar"]:
                continue
            if g["side"] == "bullish":
                if lo[i] <= g["top"] and g["state"] == "live":
                    g["state"], g["touched_bar"] = "touched", i
                if c[i] < g["bottom"]:                     # a CLOSE through it
                    g["state"], g["died_bar"] = "dead", i
                    g["death_reason"] = ("a candle closed below the bottom of "
                                         "the gap")
                    if g["holds_the_trend"] and state_at[i] == "uptrend":
                        inversions.append(BreakOfStructure(
                            "down", g["bottom"], i, timeframe, "gap inversion"))
            else:
                if h[i] >= g["bottom"] and g["state"] == "live":
                    g["state"], g["touched_bar"] = "touched", i
                if c[i] > g["top"]:
                    g["state"], g["died_bar"] = "dead", i
                    g["death_reason"] = ("a candle closed above the top of the "
                                         "gap")
                    if g["holds_the_trend"] and state_at[i] == "downtrend":
                        inversions.append(BreakOfStructure(
                            "up", g["top"], i, timeframe, "gap inversion"))

        # ---- kill 2: the trend continued past the prior swing ----------
        b = breaks_by_bar.get(i)
        if b is not None:
            doomed = "bullish" if b.direction == "up" else "bearish"
            for g in gaps:
                if g["state"] != "dead" and g["side"] == doomed \
                        and g["created_bar"] < i:
                    g["state"], g["died_bar"] = "dead", i
                    g["death_reason"] = ("the trend carried on past the prior "
                                         "swing without needing this gap")

        # ---- detect a new one on this close ----------------------------
        if i >= 2:
            side = top = bottom = None
            if lo[i] > h[i - 2]:
                side, bottom, top = "bullish", float(h[i - 2]), float(lo[i])
            elif h[i] < lo[i - 2]:
                side, bottom, top = "bearish", float(h[i]), float(lo[i - 2])
            if side is not None:
                prev = last_gap_index.get(side)
                joined = False
                if prev is not None:
                    between = range(gaps[prev]["created_bar"] + 1, i)
                    opposite = any(
                        (c[k] < o[k]) if side == "bullish" else (c[k] > o[k])
                        for k in between)
                    if not opposite and gaps[prev]["state"] != "dead":
                        joined = True
                if joined:
                    stack_id = gaps[prev]["stack_id"]
                    # the one that HOLDS the trend is the bottom of a bullish
                    # stack and the top of a bearish one, so a later gap in the
                    # same stack never takes that role
                    holds = False
                else:
                    stack_counter += 1
                    stack_id = stack_counter
                    holds = True
                gaps.append({"side": side, "top": top, "bottom": bottom,
                             "created_bar": i, "state": "live",
                             "touched_bar": None, "died_bar": None,
                             "death_reason": "", "stack_id": stack_id,
                             "holds_the_trend": holds})
                last_gap_index[side] = len(gaps) - 1

    out = [FairValueGap(g["side"], g["top"], g["bottom"], g["created_bar"],
                        timeframe, g["state"], g["touched_bar"], g["died_bar"],
                        g["death_reason"], g["stack_id"], g["holds_the_trend"])
           for g in gaps]
    return out, inversions


# ===========================================================================
# 8. EQUILIBRIUM
# ===========================================================================

def read_equilibrium(d: pd.DataFrame, timeframe: str, trend: TrendRead
                     ) -> Optional[Equilibrium]:
    """The exact halfway point between the MOST RECENT swing low and the MOST
    RECENT swing high.

        "If there's a low right here that's connected to this high, do we draw
         equilibrium from this low up to this high? No. We draw it from the most
         recent low up to the most recent high."

    Re-anchored the instant a new most-recent extreme forms — which is automatic
    here, because the anchors ARE the last two-candle pivots and nothing is
    cached.

    In an uptrend the high must be the later of the two; in a downtrend the low
    must be. Below the halfway point is the cheap half, above it the expensive
    half.

    Whether a wick past the halfway point counts as reaching it, or a body must
    close past, he never says (A12). BOTH are computed and neither is chosen."""
    lo_p, hi_p = trend.last_swing_low, trend.last_swing_high
    if lo_p is None or hi_p is None or trend.state == "unknown":
        return None
    if trend.state == "uptrend" and hi_p.bar <= lo_p.bar:
        return None
    if trend.state == "downtrend" and lo_p.bar <= hi_p.bar:
        return None

    eq = (lo_p.price + hi_p.price) / 2
    last = d.iloc[-1]
    close, low, high = float(last["close"]), float(last["low"]), float(last["high"])
    where = ("below the halfway point, the cheap half" if close < eq else
             "above the halfway point, the expensive half" if close > eq else
             "exactly on the halfway point")
    if trend.state == "uptrend":
        wick, body = low <= eq, close <= eq
    else:
        wick, body = high >= eq, close >= eq

    return Equilibrium(
        timeframe, trend.state, lo_p.price, hi_p.price, eq, where, wick, body,
        (f"halfway between the most recent swing low {lo_p.price:,.6g} and the "
         f"most recent swing high {hi_p.price:,.6g} is {eq:,.6g}; price at "
         f"{close:,.6g} sits {where}"))


# ===========================================================================
# 9. SESSIONS, CALENDAR LEVELS, STACKS, AND THE GAP RULE
# ===========================================================================

def session_extremes(d: pd.DataFrame, days_back: int = 3) -> list[SessionExtremes]:
    """The highest and lowest price TRADED inside each session window. This is
    the running extreme of the window, not a two-candle pivot — he uses both
    definitions and they are different objects.

        "Where is London session high? Well, from 3 to 8:30, where's the highest
         point that we got to?" """
    ny = new_york_index(d)
    if ny is None:
        return []
    days = trading_day_of(ny)
    high = d["high"].to_numpy(dtype=float)
    low = d["low"].to_numpy(dtype=float)
    now_min = int(ny[-1].hour) * 60 + int(ny[-1].minute)
    today = days[-1]

    out: list[SessionExtremes] = []
    for day in sorted(set(days))[-days_back:]:
        for name, window in SESSIONS.items():
            mask = (days == day) & in_window(ny, window)
            if not mask.any():
                out.append(SessionExtremes(name, day, None, None, False, 0))
                continue
            s, e = _mins(window[0]), _mins(window[1])
            complete = True
            if day == today:
                complete = (now_min >= e) if s < e else (e <= now_min < s)
            out.append(SessionExtremes(name, day, float(high[mask].max()),
                                       float(low[mask].min()), complete,
                                       int(mask.sum())))
    return out


def previous_period_extremes(d: pd.DataFrame):
    """Previous whole trading DAY (18:00 to 18:00, "all of those sessions
    encapsulated into one") and previous whole WEEK."""
    ny = new_york_index(d)
    if ny is None:
        return {}
    days = trading_day_of(ny)
    high = d["high"].to_numpy(dtype=float)
    low = d["low"].to_numpy(dtype=float)
    out = {}

    today = days[-1]
    earlier = sorted(set(days[days < today]))
    if earlier:
        m = days == earlier[-1]
        out["day"] = (float(high[m].max()), float(low[m].min()), earlier[-1])

    naive = pd.DatetimeIndex(ny).tz_localize(None)
    weeks = naive.to_period("W").start_time.astype("datetime64[ns]")
    this_week = weeks[-1]
    prior = weeks[weeks < this_week]
    if len(prior):
        prev = prior.max()
        m = weeks == prev
        out["week"] = (float(high[m].max()), float(low[m].min()),
                       str(pd.Timestamp(prev).date()))
    return out


def traded_through(d: pd.DataFrame, price: float, side: str, from_bar: int):
    """Has price traded PAST this level since it formed, and did it actually
    trade TO it or jump over it?

    THE GAP RULE. A fund that stops at 16:00 and reopens at 09:30 can open away
    from where it closed, so a level can be left behind without price ever
    visiting it. A level the market jumped straight over was not taken — the
    same principle as a level traded straight through not being taken.

    Returns (traded_past, jumped_over, bar, extreme)."""
    after = d.iloc[from_bar + 1:] if from_bar >= 0 else d
    if len(after) == 0:
        return False, False, None, None
    high = after["high"].to_numpy(dtype=float)
    low = after["low"].to_numpy(dtype=float)
    base = (from_bar + 1) if from_bar >= 0 else 0

    if side == "high":
        past = high > price
        touched = past & (low <= price)
    else:
        past = low < price
        touched = past & (high >= price)

    if not past.any():
        return False, False, None, None
    if not touched.any():
        return False, True, None, None       # gapped clean over it
    idx = int(np.argmax(touched))
    return (True, False, base + idx,
            float(high[idx] if side == "high" else low[idx]))


def cluster_levels(levels: list[Level], tolerance_pct: Optional[float],
                   minimum_count: Optional[int]) -> list[Level]:
    """Stacked and roughly-equal levels: several untouched highs, or several
    untouched lows, sitting at about the same price.

        "Low resistance liquidity is when we have a bunch of stacked up highs or
         a bunch of stacked up lows that have not been swept out yet."

    HE NEVER GIVES THE NUMBERS — no maximum spacing for "roughly equal", no
    minimum count for a stack. His only figure is one observation, "literally 50
    cents apart" on a 15-minute chart, and his examples show four and five. So
    this REFUSES TO RUN without both parameters rather than picking them (A3). A
    number invented here becomes a fitted setting that nobody remembers
    inventing."""
    if tolerance_pct is None or minimum_count is None:
        return []
    out: list[Level] = []
    for side in ("high", "low"):
        group = sorted((lv for lv in levels
                        if lv.side == side and not lv.traded_through
                        and lv.tradeable_pool),
                       key=lambda lv: lv.price)
        i = 0
        while i < len(group):
            cluster = [group[i]]
            j = i + 1
            while (j < len(group) and group[i].price
                   and abs(group[j].price - group[i].price)
                   / abs(group[i].price) * 100 <= tolerance_pct):
                cluster.append(group[j])
                j += 1
            if len(cluster) >= minimum_count:
                out.append(Level(
                    float(np.mean([lv.price for lv in cluster])), side,
                    f"{len(cluster)} {side}s stacked at about the same price",
                    "", -1, tradeable_pool=True,
                    note=(f"{len(cluster)} levels inside {tolerance_pct}% of "
                          f"each other, none of them taken out")))
            i = j if j > i + 1 else i + 1
    return out


# ===========================================================================
# 10. INSTRUMENT STATISTICS — recomputed from the chart in front of us
#
#     The one engineering rule from our own rounds that governs this file
#     absolutely: never carry a number between instruments. A fixed 1.5%
#     condition is open on 96.7% of one market's bars and 18-53% of another's,
#     and on the SAME market it drifted from 63.2% open to 24.3% across three
#     windows with nobody touching it (R190, R320). When the spec eventually
#     gives a number it arrives as a rank or a ratio, and `locate()` puts it
#     where it belongs on THIS instrument.
# ===========================================================================

DERIVE_WINDOW = 2000   # recent closed bars. A bar count, not a price threshold.


def derive_stats(d: pd.DataFrame, round_trip_cost_pct: float,
                 window: int = DERIVE_WINDOW) -> dict:
    w = d.tail(window)
    close = w["close"]
    bar_range = ((w["high"] - w["low"]) / close * 100).dropna()

    prev = close.shift(1)
    tr = pd.concat([w["high"] - w["low"], (w["high"] - prev).abs(),
                    (w["low"] - prev).abs()], axis=1).max(axis=1)
    move = (tr.ewm(alpha=1 / 14, adjust=False).mean() / close * 100).dropna()

    overnight = None
    ny = new_york_index(w)
    if ny is not None:
        days = trading_day_of(ny)
        firsts = np.flatnonzero(np.r_[True, days[1:] != days[:-1]])
        if len(firsts) > 2:
            opens = w["open"].to_numpy(dtype=float)[firsts[1:]]
            closes = w["close"].to_numpy(dtype=float)[firsts[1:] - 1]
            overnight = float(np.median(np.abs(opens - closes) / closes * 100))

    typical = float(move.median()) if len(move) else None
    return {
        "window_bars": int(len(w)),
        "price": float(close.iloc[-1]),
        "bar_range_price_pct_median": float(bar_range.median()) if len(bar_range) else None,
        "bar_range_price_pct_p90": float(bar_range.quantile(0.90)) if len(bar_range) else None,
        "typical_bar_move_price_pct": typical,
        "bar_move_price_pct_p90": float(move.quantile(0.90)) if len(move) else None,
        "median_overnight_gap_price_pct": overnight,
        "round_trip_cost_price_pct": round_trip_cost_pct,
        "round_trip_cost_in_typical_bars": (
            None if not typical else round_trip_cost_pct / typical),
    }


def locate(value: float, sample) -> Optional[float]:
    """Where a number sits in this instrument's own distribution, 0 to 1. This
    is what lets a number the spec states travel between instruments: the spec
    supplies the rank, the market supplies the distance."""
    s = pd.Series(sample).dropna()
    return float((s <= value).mean()) if len(s) else None


def resample(d: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Build a coarser chart from a finer one — the 4-hour from the 1-hour.
    Right-closed and right-labelled, so a bar is stamped at the time it CLOSES.
    Any other stamping makes a coarse bar visible before it has finished, which
    is the exact lookahead he objects to in bar-replay tools, and he is right
    about it."""
    g = (d.set_index(pd.to_datetime(d["timestamp"]))
          .resample(rule, label="right", closed="right"))
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    if "volume" in d.columns:
        out["volume"] = g["volume"].sum()
    return out.dropna().reset_index().rename(columns={"index": "timestamp"})


# ===========================================================================
# 11. SIZE FROM THE STOP — arithmetic, not a decision
# ===========================================================================

def size_from_stop(entry: float, stop: float, equity: float,
                   risk_fraction: float, round_trip_cost_pct: float,
                   fractional_shares: bool = True) -> dict:
    """size = dollars risked / distance to the level that proves the idea wrong.
    Leverage is what comes OUT of that, never what goes in. Alpaca does
    fractional shares, so this lands exactly, with no lot size fighting the stop.

    This decides nothing. It is here because the decision layer will need it and
    the arithmetic is proven.

    Every percentage is a PRICE MOVE: how far price has to travel. The change in
    the position's value is that number multiplied by the leverage."""
    distance = abs(entry - stop)
    if distance <= 0 or entry <= 0:
        return {"size_shares": None, "size_dollars": None,
                "implied_leverage": None, "stop_distance_price_pct": None,
                "stop_distances_to_clear_costs": None}
    shares = equity * risk_fraction / distance
    if not fractional_shares:
        shares = float(np.floor(shares))
    stop_pct = distance / entry * 100
    return {
        "size_shares": float(shares),
        "size_dollars": float(shares * entry),
        "implied_leverage": float(risk_fraction / (distance / entry)),
        "stop_distance_price_pct": float(stop_pct),
        # How far the trade must travel, in stop distances, to be worth five
        # times what getting in and out costs. A tighter stop makes this HARDER,
        # not easier: profit and cost both scale with size while the stop shrinks.
        "stop_distances_to_clear_costs": float(
            COST_MULTIPLE_BAR * round_trip_cost_pct / stop_pct),
    }


# ===========================================================================
# 12. THE READ
# ===========================================================================

MIN_BARS = 60
RECENT_BARS = 400     # how much of the working chart the state machines walk


def truncate_to_completed(frame: pd.DataFrame, as_of) -> pd.DataFrame:
    """Keep only bars that had CLOSED by `as_of`.

    This is the whole no-lookahead argument. He rejects clicking through
    historical bars in a charting tool, for a real reason: the higher timeframe
    candle is displayed already completed, so you are reading the future. A
    4-hour bar still forming would hand this reader up to four hours of it."""
    if frame is None or len(frame) == 0 or "timestamp" not in frame.columns:
        return frame
    ts = pd.to_datetime(frame["timestamp"])
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    step = ts.diff().median()
    if pd.isna(step) or step <= pd.Timedelta(0):
        return frame
    return frame.loc[((ts + step) <= as_of).to_numpy()].reset_index(drop=True)


def read_the_chart(frames: dict, instrument: Instrument,
                   decision_idx: Optional[int] = None,
                   unresolved: Unresolved = UNRESOLVED) -> Optional[ChartRead]:
    """Compute everything on the chart, causally.

    frames : {timeframe: DataFrame} with timestamp/open/high/low/close. Levels
        come from instrument.level_timeframes, direction from
        direction_timeframes, and the read lands on working_timeframe.
    decision_idx : which bar of the working chart to read at, defaulting to the
        newest. Passing it explicitly is what makes a historical replay possible
        AND what makes the no-lookahead test mechanical: reading bar i on a
        frame that also holds 400,000 future bars must produce the identical
        read to reading bar i on a frame truncated there.

    Returns None when there is not enough history to describe anything."""
    tf = instrument.working_timeframe
    if tf not in frames:
        raise ValueError(f"trader: {instrument.symbol} reads the {tf} chart and "
                         f"no {tf} frame was given (got {sorted(frames)})")

    full = frames[tf].reset_index(drop=True)
    idx = len(full) - 1 if decision_idx is None else int(decision_idx)
    if idx < 0 or idx >= len(full):
        raise ValueError(f"trader: decision_idx {idx} is outside the frame")
    d = full.iloc[: idx + 1].reset_index(drop=True)
    if len(d) < MIN_BARS:
        return None

    price = float(d["close"].iloc[-1])
    ny = new_york_index(d)
    as_of = None
    if "timestamp" in d.columns:
        t = pd.to_datetime(d["timestamp"].iloc[-1])
        as_of = t if t.tzinfo else t.tz_localize("UTC")

    missing = list(unresolved.missing())
    levels: list[Level] = []

    # -- levels from the 4-hour and the 1-hour ONLY ----------------------
    #    "the best time frames... to identify liquidity on for me is going to be
    #     the 4 hour and the 1 hour", and he forbids hunting them on the
    #     1-minute. A 5-minute pivot is never marked as a tradeable pool.
    for level_tf in instrument.level_timeframes:
        frame = frames.get(level_tf)
        if frame is None:
            continue
        cut = truncate_to_completed(frame.reset_index(drop=True), as_of)
        if cut is None or len(cut) < 3:
            continue
        hi_p, lo_p = two_candle_pivots(cut)
        for group, side in ((hi_p, "high"), (lo_p, "low")):
            for p in group[-10:]:
                past, jumped, _, _ = traded_through(cut, p.price, side, p.bar)
                levels.append(Level(
                    p.price, side, f"{level_tf} pivot {side}", level_tf, p.bar,
                    tradeable_pool=True, traded_through=past, jumped_over=jumped,
                    note=("an up candle then a down candle, marked at the higher "
                          "of the two wicks" if side == "high" else
                          "a down candle then an up candle, marked at the lower "
                          "of the two wicks")))

    # -- session extremes -------------------------------------------------
    sessions = session_extremes(d)
    for s in sessions:
        for side, val in (("high", s.high), ("low", s.low)):
            if val is None:
                continue
            past, jumped, _, _ = traded_through(d, val, side, -1)
            levels.append(Level(
                val, side, f"{s.name} session {side}", "", -1,
                tradeable_pool=True, traded_through=past, jumped_over=jumped,
                note=(("the highest" if side == "high" else "the lowest")
                      + f" price traded in {s.name} hours on {s.trading_day}, "
                        f"New York time"
                      + ("" if s.complete else ", still forming"))))

    # -- previous whole day and previous whole week ------------------------
    for period, got in previous_period_extremes(d).items():
        hi, lo, label = got
        for side, val in (("high", hi), ("low", lo)):
            past, jumped, _, _ = traded_through(d, val, side, -1)
            levels.append(Level(
                val, side, f"previous {period} {side}", "", -1,
                tradeable_pool=True, traded_through=past, jumped_over=jumped,
                note=(f"across the whole {period} of {label}"
                      + (", all three sessions combined" if period == "day" else ""))))

    # -- stacked and roughly-equal levels ---------------------------------
    stacks = cluster_levels(levels, unresolved.A3_roughly_equal_tolerance_pct,
                            unresolved.A3_minimum_stack_count)
    levels.extend(stacks)
    if not stacks and unresolved.A3_roughly_equal_tolerance_pct is None:
        missing.append("A3_roughly_equal_tolerance_pct — no stacked or "
                       "roughly-equal levels were marked at all")
    if unresolved.A4_news_candle_timeframe is None:
        missing.append("A4_news_candle_timeframe — no release-candle levels "
                       "were marked")

    # -- trend, gaps and equilibrium, per timeframe ------------------------
    trends: dict = {}
    gaps: dict = {}
    equilibrium: dict = {}
    all_inversions: list[BreakOfStructure] = []

    read_on = list(dict.fromkeys(
        instrument.direction_timeframes + instrument.level_timeframes
        + (tf,) + ((instrument.entry_timeframe,) if instrument.entry_timeframe else ())))

    for t in read_on:
        frame = frames.get(t)
        if frame is None:
            continue
        cut = d if t == tf else truncate_to_completed(frame.reset_index(drop=True), as_of)
        if cut is None or len(cut) < 3:
            continue
        window = cut.tail(RECENT_BARS).reset_index(drop=True)

        first = read_trend(window, t)
        gap_list, inversions = find_fair_value_gaps(window, t, first.breaks)
        # he uses a gap inversion in place of waiting for a break of structure,
        # so it is fed back in and the trend re-read with both kinds of event
        tr = read_trend(window, t, extra_breaks=inversions) if inversions else first
        trends[t] = tr
        gaps[t] = tuple(gap_list)
        all_inversions.extend(inversions)
        eq = read_equilibrium(window, t, tr)
        if eq is not None:
            equilibrium[t] = eq

    if unresolved.A12_equilibrium_reached_by_wick_or_body is None:
        missing.append("A12_equilibrium_reached_by_wick_or_body — both readings "
                       "are reported and neither is chosen")
    if unresolved.A7_which_entry_timeframe is None and instrument.entry_timeframe:
        missing.append("A7_which_entry_timeframe — which chart governs is "
                       "unresolved")

    # -- which levels price traded past, and what state that leaves --------
    working = trends.get(tf)
    taken: list[TakenLevel] = []
    if working is not None:
        recent = d.tail(RECENT_BARS).reset_index(drop=True)
        for lv in levels:
            if not lv.tradeable_pool or lv.jumped_over:
                continue
            past, jumped, bar, extreme = traded_through(recent, lv.price, lv.side, -1)
            if not past or bar is None:
                continue
            taken.append(_state_of_take(lv, bar, extreme, len(recent), working,
                                        unresolved.A9_pending_lifetime_bars))
        taken.sort(key=lambda t: t.bars_ago)
    if unresolved.A9_pending_lifetime_bars is None:
        missing.append("A9_pending_lifetime_bars — a level taken with no "
                       "reaction stays pending indefinitely")
    if unresolved.A1_trading_window_end is None:
        missing.append("A1_trading_window_end — there is no defined window")

    pools = tuple(lv for lv in levels if lv.tradeable_pool)
    session = day = ""
    minutes_since_open = None
    if ny is not None:
        session = session_of(ny[-1])
        day = trading_day_of(ny)[-1]
        minutes_since_open = (int(ny[-1].hour) * 60 + int(ny[-1].minute)
                              - _mins(NEW_YORK_OPEN))

    return ChartRead(
        symbol=instrument.symbol, working_timeframe=tf,
        as_of=None if as_of is None else str(as_of),
        price=price, bars_read=len(d),
        session=session, trading_day=day,
        minutes_since_new_york_open=minutes_since_open,
        levels=tuple(levels), pools=pools,
        untouched_pools=tuple(lv for lv in pools
                              if not lv.traded_through and not lv.jumped_over),
        taken=tuple(taken), trends=trends, gaps=gaps,
        gap_inversions=tuple(all_inversions), equilibrium=equilibrium,
        sessions=tuple(sessions),
        stats=derive_stats(d, instrument.round_trip_cost_pct),
        unresolved=tuple(dict.fromkeys(missing)))


def _state_of_take(level: Level, bar: int, extreme: float, n: int,
                   trend: TrendRead, lifetime: Optional[int]) -> TakenLevel:
    """Turn a level price traded past into its true state. TWO STATES, and the
    conversion has exactly one cause.

        confirmed    a break of structure, or a gap inversion which he uses for
                     the same job, printed AFTER that bar in the OPPOSITE
                     direction: "How do we know that it's a proper liquidity
                     sweep? Because we literally see the reversal on the low
                     time frames."
        no reaction  a break printed in the SAME direction: the trend carrying
                     on. "If price comes down and takes out a low and keeps
                     going down, is it a liquidity sweep? No."

    BREAK FIRST, PULLBACK SECOND. A high being taken is confirmed by a downside
    break, which by definition makes the lower LOW; the lower high that follows
    is the pullback. Not the other way round.

    How long a pending state stays alive he never says (A9), so with no
    parameter it simply stays pending and reports how long it has."""
    bars_ago = n - 1 - bar
    want = "down" if level.side == "high" else "up"
    for b in trend.breaks:
        if b.bar <= bar:
            continue
        if b.direction == want:
            return TakenLevel(
                level, "confirmed", want, bar, bars_ago, extreme, b,
                (f"price traded past the {level.kind} at {level.price:,.6g} "
                 f"{bars_ago} bars ago, reaching {extreme:,.6g}, and then a "
                 f"candle body closed "
                 f"{'below' if want == 'down' else 'above'} {b.level:,.6g} "
                 f"({b.source} on the {b.timeframe} chart), which is the turn "
                 f"actually starting"))
        return TakenLevel(
            level, "no reaction", want, bar, bars_ago, extreme, None,
            (f"price traded past the {level.kind} at {level.price:,.6g} and then "
             f"kept going the same way, so it was never a level taken and "
             f"reacted to"))
    stale = lifetime is not None and bars_ago > lifetime
    return TakenLevel(
        level, "stale" if stale else "pending", want, bar, bars_ago, extreme, None,
        (f"price traded past the {level.kind} at {level.price:,.6g} {bars_ago} "
         f"bars ago, reaching {extreme:,.6g}, and nothing has confirmed a turn "
         f"out of it yet" + (", and it has gone stale" if stale else "")))


def instruments_agree(a: ChartRead, b: ChartRead) -> dict:
    """Do the two indexes tell the same story on the working chart? New in the
    2026 version and with no older equivalent: if they are not saying the same
    thing there is no trade. This reports; it does not decide."""
    ta = a.trends.get(a.working_timeframe)
    tb = b.trends.get(b.working_timeframe)
    if ta is None or tb is None:
        return {"agree": None, "detail": "one of the charts has no trend read"}
    return {"agree": ta.state == tb.state and ta.state != "unknown",
            a.symbol: ta.state, b.symbol: tb.state,
            "detail": (f"{a.symbol} reads {ta.state} and {b.symbol} reads "
                       f"{tb.state} on the {a.working_timeframe} chart")}


# ===========================================================================
# 13. A LOCAL LOOK — cached Alpaca files only. No network, no orders.
# ===========================================================================

def load_frames(symbol: str = "SPY") -> dict:
    """The charts this method needs, from the cached Alpaca files. The 4-hour is
    built from the 1-hour because Alpaca does not serve it. The 1-minute is not
    held, so the 5-minute is the finest chart available today."""
    frames = {}
    for tf in ("5m", "15m", "1h", "1d"):
        try:
            frames[tf] = pd.read_parquet(
                f"data_alpaca_{symbol}_{tf}.parquet").reset_index(drop=True)
        except Exception:
            pass
    if "1h" in frames:
        frames["4h"] = resample(frames["1h"], "4h")
    return frames


def _demo():
    print("=" * 78)
    print("trader.py — the reading layer. It computes; it decides nothing.")
    print("=" * 78)
    reads = {}
    for symbol in ("SPY", "QQQ"):
        frames = load_frames(symbol)
        if "5m" not in frames:
            print(f"\n  (skipped {symbol}: no cached 5-minute file)")
            continue
        inst = Instrument(symbol)
        five = frames["5m"]
        ny = new_york_index(five)
        in_session = np.flatnonzero(
            (ny.hour * 60 + ny.minute >= _mins(NEW_YORK_OPEN))
            & (ny.hour * 60 + ny.minute < _mins(BLACKOUT[0])))
        idx = int(in_session[-120]) if len(in_session) > 200 else len(five) - 1

        r = read_the_chart(frames, inst, decision_idx=idx)
        reads[symbol] = r
        print(f"\n{'-' * 78}\n{r.symbol}  working chart {r.working_timeframe}  "
              f"{r.bars_read} bars  as of {r.as_of}\n{'-' * 78}")
        print(f"  price            : {r.price:,.6g}")
        print(f"  session          : {r.session}  (trading day {r.trading_day}, "
              f"{r.minutes_since_new_york_open} minutes past the open)")
        for t, tr in r.trends.items():
            print(f"  {t:>3s} trend        : {tr.state:9s} — {tr.detail[:96]}")
        print(f"  levels marked    : {len(r.levels)} "
              f"({len(r.pools)} are levels he watches, "
              f"{len(r.untouched_pools)} not taken yet, "
              f"{sum(1 for lv in r.levels if lv.jumped_over)} jumped over "
              f"without being traded to)")
        kinds: dict = {}
        for lv in r.pools:
            kinds[lv.kind] = kinds.get(lv.kind, 0) + 1
        for k, n in sorted(kinds.items()):
            print(f"      {n:3d}  {k}")
        above, below = r.pools_above(), r.pools_below()
        if above:
            print(f"  nearest untouched above: {above[0].price:,.6g}  {above[0].kind}")
        if below:
            print(f"  nearest untouched below: {below[0].price:,.6g}  {below[0].kind}")
        print(f"  levels traded past: {len(r.taken)} "
              f"(confirmed {len(r.confirmed_takes())}, "
              f"pending {len(r.pending_takes())}, "
              f"no reaction {sum(1 for t in r.taken if t.state == 'no reaction')})")
        for t in r.taken[:3]:
            print(f"      [{t.state:11s}] {t.detail[:110]}")
        for t, gl in r.gaps.items():
            live = [g for g in gl if g.state in ("live", "touched")]
            if live:
                print(f"  {t:>3s} fair value gaps: {len(live)} live of {len(gl)} "
                      f"seen; nearest "
                      f"{min(live, key=lambda g: abs((g.top + g.bottom) / 2 - r.price)).side}"
                      f" box "
                      f"{min(live, key=lambda g: abs((g.top + g.bottom) / 2 - r.price)).bottom:,.6g}"
                      f" to "
                      f"{min(live, key=lambda g: abs((g.top + g.bottom) / 2 - r.price)).top:,.6g}")
        if r.gap_inversions:
            print(f"  gap inversions   : {len(r.gap_inversions)} "
                  f"(a gap that held the trend up got closed through, which he "
                  f"uses in place of waiting for a break of structure)")
        for t, eq in r.equilibrium.items():
            print(f"  {t:>3s} halfway point : {eq.price:,.6g} — {eq.where_price_sits}"
                  f"  (reached by wick {eq.reached_by_wick}, by body "
                  f"{eq.reached_by_body})")
        st = r.stats
        print(f"  how it moves     : a typical {r.working_timeframe} bar covers "
              f"{st['bar_range_price_pct_median']:.3f}% of price, typical move "
              f"{st['typical_bar_move_price_pct']:.3f}%, and one round trip costs "
              f"{st['round_trip_cost_in_typical_bars']:.2f} of that")
        if st["median_overnight_gap_price_pct"] is not None:
            print(f"  overnight gap    : the median open sits "
                  f"{st['median_overnight_gap_price_pct']:.3f}% of price from the "
                  f"prior close, which is why a level jumped over is not a level "
                  f"taken")
        print(f"  could not compute: {len(r.unresolved)}")
        for u in r.unresolved:
            print(f"      {u}")

    if len(reads) == 2:
        a = instruments_agree(reads["SPY"], reads["QQQ"])
        print(f"\n{'-' * 78}\ndo the two indexes agree: {a['agree']} — {a['detail']}")

    print("\n" + "=" * 78)
    print("the numbers he never says — named, never guessed")
    print("=" * 78)
    for k, why in NEEDS_VIDEO.items():
        print(f"  {k}\n      {why[:140]}...")
    print()


if __name__ == "__main__":
    _demo()
