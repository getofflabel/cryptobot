"""
tjr_bot.py — one professional trader's stated method, as a causal decision
function. Nothing in here is our idea.

WHAT THIS IS
    An implementation of the specification in step431 / step432 / step433 /
    step434, with step436 overriding wherever those four disagree. It is a
    transcription job, not a strategy design job. Where he does not state a
    number, the number lives in `Config` with a one-line note saying it is
    ours and it is a guess.

THE SHAPE OF THE DAY (step434 section 7, his assembled procedure)

    news gate
      -> daily direction (the daily and the 4-hour must agree)
      -> mark the levels off the 1-hour, the 4-hour, the sessions, the prior day
      -> load BOTH index charts
      -> 09:30 opens; a marked level gets pushed through
      -> a 5-minute break of structure, or a 5-minute gap inversion
      -> BOTH indexes must agree on the 5-minute or there is no trade
      -> a 5-minute pullback into the midpoint or a fair value gap
      -> a 1-minute break against the trade, then one with it
      -> enter

TIMEFRAMES BY JOB (step436 section 4, not negotiable)
    4-hour and daily  : direction only, never an entry
    1-hour and 4-hour : where the tradeable levels are marked
    5-minute          : the working chart
    1-minute          : the entry trigger only
    Never hunt a sweep on the 1-minute.

NO LOOKAHEAD, THE THING MOST LIKELY TO GO WRONG
    Every higher timeframe is truncated to its last COMPLETED candle as of
    the decision moment: a 4-hour candle starting at 08:00 does not exist to
    this bot until 12:00. Every tracker here is fed bars one at a time,
    forward only. test_tjr_bot.py proves it by re-deciding a bar with the
    future deleted.

SIZING, AND THERE IS EXACTLY ONE OF IT (step452 item 3 and item 8)
    `size_position` below is the only place in this project that turns a
    stop into a number of units. The replay calls it and the live path calls
    it, through `tjr_alerts.position_size`, which is now a translation layer
    with no arithmetic of its own. Until 2026-07-26 there were two rules —
    the replay sized fresh at 1% of equity every trade while the orders that
    actually went out used his set size capped at 3% — so every backtest
    number this project had ever produced described a bot nobody was running.

    THE RULE ITSELF IS HIS: the size is worked out once, off the TIGHTEST
    stop the instrument normally gives, so that stop would cost the trade's
    share of the day's budget. It is then held still, and a wider stop today
    costs proportionally more. That is where his one-to-three-percent band
    comes from — it is an output of holding the size still, never a dial.

THE BUDGET IS THE DAY'S, NOT THE TRADE'S (step452 item 3, Boot Camp 2.0)
    "I only lost 50 percent of what I was willing to risk on the day, that's
    better than a full you know like one percent down on the day two percent
    down or three percent down on the day." Every one of those numbers is
    attached to THE DAY. So `DayBudget` holds 1% of the account (0.5% on a
    news day), trades draw shares of it, and the 3% is the outer limit the
    whole day may reach, not a ceiling one trade may spend on its own.

COSTS ARE CHARGED, NEVER CONSULTED
    The measured 0.0035% round trip is subtracted so the money is honest.
    Nothing anywhere skips or alters a trade because of cost — the typical
    stop is 62 times the round trip, so cost cannot decide anything here.

SAFETY
    This module places no orders and imports nothing that can. It reads price
    frames and returns decisions. `live_step` refuses to return an entry when
    the market is shut or the clock is unreadable.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections import namedtuple
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import news_calendar as _nc

# ----------------------------------------------------------------- clock
# All times US Eastern. He states it and repeats it (step434 section 2).
OPEN_T = dt.time(9, 30)          # market opens
MANIP_END_T = dt.time(9, 50)     # end of the manipulation window; no entries before this
ENTRY_IDEAL_END_T = dt.time(10, 10)
CUTOFF_T = dt.time(10, 30)       # HARD: "if I can't find a trade by 10:30, I'm done"
FLAT_T = dt.time(15, 55)         # he goes home flat; the funds stop trading at 16:00
CLOSE_T = dt.time(16, 0)

Bar = namedtuple("Bar", "t o h l c")     # t is the bar's START, US Eastern, naive


# ------------------------------------------------------------ instruments
@dataclass
class Instrument:
    """Everything that is TRUE OF A MARKET rather than true of the method.

    The decision logic below never branches on which market it is looking at.
    A market with no closing bell, or a different clock, or a different cost,
    drops in here as another Instrument and the method is untouched. That is
    what makes crypto a config change later rather than a second bot.

    THE CLOCK IS OPTIONAL. Every time rule below defaults to None, meaning
    it does not apply. A market with no bell does not get invented session
    hours — it gets no session rules at all, and the ban on 5-minute levels
    does the throttling the clock used to do.

    Wallace, on crypto: "keep his trading methods just throw away the times".
    """
    name: str
    round_trip_cost_pct: float      # measured, charged, never consulted
    day_boundary_hour: int = 0      # where one trading day is cut from the next
    open_t: dt.time | None = None   # when the session's new money arrives
    manip_end_t: dt.time | None = None   # no entries before this
    entry_ideal_end_t: dt.time | None = None
    cutoff_t: dt.time | None = None      # hard: no new trades after this
    flat_t: dt.time | None = None        # go home flat
    close_t: dt.time | None = None
    prior_session_window: tuple | None = None  # ("London") start/end hour, for the profile
    early_session_window: tuple | None = None  # ("Asia") start/end hour
    # ("New York") start/end hour. He names THREE session pairs, not two:
    # "Asia session highs, Asia session lows, London session highs, London
    # session lows, New York highs, New York lows. All of these are
    # significant draws on liquidity." And he gives the window: "1800 to 3 is
    # Asia session. 3 to 8:30 London session. 8:30 back to 1800 is New York
    # session. And that encapsulates a full day of trading."
    own_session_window: tuple | None = None
    has_closing_bell: bool = False  # True only where there is an actual bell
    level_minutes: tuple = (60, 240)      # where tradeable levels are marked
    working_minutes: int = 5              # the working chart
    trigger_minutes: int = 1              # the entry trigger only
    continuation_minutes: int = 15        # the smaller-timeframe pool
    target1_minutes: int = 15             # one timeframe above the execution chart
    # Which hour, US Eastern, the higher-timeframe candle grid hangs from.
    # 17 is the futures session open and is what his 4-hour chart is drawn
    # on; a market with no session open carries 0 and gets a midnight grid.
    candle_anchor_hour: int = 0


# The two US index funds. His clock, his sessions, our measured cost.
US_INDEX_ETF = Instrument(
    name="us_index_etf", round_trip_cost_pct=0.000035,
    open_t=dt.time(9, 30), manip_end_t=dt.time(9, 50),
    entry_ideal_end_t=dt.time(10, 10), cutoff_t=dt.time(10, 30),
    flat_t=dt.time(15, 55), close_t=dt.time(16, 0),
    prior_session_window=(3, 8.5), early_session_window=(18, 3),
    own_session_window=(8.5, 18), day_boundary_hour=18, has_closing_bell=True,
    candle_anchor_hour=17)


# ------------------------------------------------------------------ config
@dataclass
class Config:
    """Anything he never gave a number for is marked OURS and is a guess."""

    # --- which market. Nothing below branches on it. ---------------------
    instrument: Instrument = field(default_factory=lambda: US_INDEX_ETF)

    # --- sizing (step433 section 2, step436 section 7, step452 item 3) ----
    #
    # THE UNIT CHANGED ON 2026-07-26 AND THE NUMBERS DID NOT. These were read
    # as a per-TRADE risk. Boot Camp 2.0 Day 8 attaches every one of them to
    # "on the day": "I only lost 50 percent of what I was willing to risk on
    # the day, that's better than a full you know like one percent down on
    # the day two percent down or three percent down on the day." His own
    # working figure is the bottom of the band — Day 3, "my usual risk
    # tolerance is around like 20 grand", against an account his own
    # arithmetic puts near two million.
    risk_pct_normal: float = 0.01        # HIS: 1% of the account PER DAY
    risk_pct_derisk: float = 0.005       # HIS: half of it on news days and holidays
    # HIS: the top of the band, and it is the ceiling on THE DAY. It used to
    # live in tjr_alerts as MAX_RISK_SHARE_OF_ACCOUNT applied to one trade,
    # which let a single position spend the whole outer limit — the exact
    # mistake Day 8 and Day 9 are warning against.
    max_day_risk_share: float = 0.03
    # HIS, Day 8: "I'm going to go in with like half of what I would want to
    # risk on the day knowing damn well that I'm probably going to take a
    # second trade."
    first_trade_share_when_second_expected: float = 0.50
    # HIS, Day 9: once target one is taken and the stop is at break even the
    # trade stops holding the whole allocation — "we lost 50 of what we were
    # willing to lose once take profit one got hit, okay, now we're down to
    # like 25 of what we were willing to lose for the day". 50 -> 25 is half
    # of what that trade was holding.
    break_even_releases_share: float = 0.50
    # OURS, a guess, and it is the only number in the multi-trade path that
    # is not his. He gives no floor. A quarter of the day's budget is the
    # smallest piece his own Day 9 accounting ever names, so below that there
    # is nothing left worth opening and the day is done. Without a floor the
    # last sliver of budget buys a position too small to matter and the
    # ledger never closes.
    min_budget_share_to_open: float = 0.25
    double_size_enabled: bool = False    # HIS: forbidden without a proven record. STAYS OFF.
    partial_fraction: float = 0.50       # HIS: "I took off 50 of the position"
    # HIS, Day 9, said three times in the same words: "take profit two right
    # here where I managed another fifty percent of the OPEN position". Half
    # of the half is a quarter of the original, and the last quarter is the
    # runner he closes by hand.
    second_partial_fraction: float = 0.50

    # --- the targets (step433 section 3, bootcamp Day 37, step452 item 1) -
    # HIS, and Boot Camp 2.0 raised it: "we have take profit three right here
    # and then take profit four all the way up here" (Day 9) and "I also had
    # several other take profits like four and five all the way up here if it
    # wanted to hit some high time frame highs" (Day 11). Four and sometimes
    # five, so five is the top of the range he names.
    max_targets: int = 5
    # OURS, a guess. He skips a building block that "kind of envelops" one he
    # has already used but never says how close that is. A tenth of what was
    # risked is our reading of "envelops".
    target_envelope_fraction_of_risk: float = 0.10

    # Alpaca paper reports about 4x equity of day-trade buying power. In the
    # replay we model it off equity so it compounds; live, the caller passes
    # the broker's own number instead of trusting this.
    buying_power_multiple: float = 4.0

    # --- the stop (step433 section 1.5) ---------------------------------
    # OURS, a guess: he says clear your broker's spread, and gives 0.5 points
    # on an index quoted near 5,000, which is 0.01% of price.
    stop_buffer_pct_of_price: float = 0.0001

    account_start: float = 100_000.0

    # --- the losing-streak escalation (step436 section 8) ----------------
    losing_weeks_to_escalate: int = 2    # HIS: "two losing weeks or like three"

    # --- lookbacks. OURS, all four, guesses that looked sensible. --------
    level_lookback_days: int = 10        # how far back 1h/4h pivots get marked
    dir_lookback_days: int = 90          # history the daily/4-hour direction is read over
    seed_days: int = 3                   # 5-minute trend/gap warm-up before the open
    gap_max_age_bars: int = 288          # a gap is never dragged forward (1 day of 5m)

    # --- how long a pending sweep stays alive. OURS, a guess. ------------
    # He never says. Round 430 measured the median sweep-to-signal gap at 6
    # five-minute bars, so 12 is a generous ceiling; a same-direction break
    # of structure kills the pending state earlier anyway.
    sweep_max_age_bars: int = 12

    # --- the regime label. OURS, a guess: 50 closed daily bars. ----------
    regime_ma_days: int = 50

    # NOTE on the continuation pool, which lives in Instrument: he says "five
    # minute lows and like 15 minute lows" (step434 1A step 4). Round 430
    # measured that a 5-minute pool sits CLOSER than the stop, so such a
    # setup cannot pay. We keep the 15-minute half of that sentence and drop
    # the 5-minute half. OURS.

    enforce_index_agreement: bool = True
    enforce_daily_4h_agreement: bool = True

    # HIS: the direction read is THREE timeframes, not two, and the 1-hour can
    # stand in for the 4-hour. Bootcamp Day 52 on GBPJPY, the setup he calls
    # the best of that morning: "we're bearish on the daily. Not necessarily
    # bearish on the 4-hour. But the 1-hour is saying bearish off this break of
    # structure... then that looks pretty good." Day 54 on GBPUSD, the other
    # way round: "4 hours bearish, daily's bullish... I wouldn't necessarily
    # want to be looking for a trade on here until we get at least 1 hour
    # bullish confirmation." And Day 49 on gold: "the four hour is like just
    # kind of chop Central, Daily's bullish though, one hour broke structure
    # the upside... this is something that I would likely be willing to take."
    # So: the daily must have a direction, and at least one of the 4-hour and
    # the 1-hour must be with it. The daily standing alone against both is the
    # case he refuses — Day 49 on GBPJPY, "this can go to the bottom of my
    # list today."
    use_1h_in_direction: bool = True

    # HIS: the side is the daily's. "can we go against daily bias no"
    # (Day 49). "we have to stay bullish when the daily is telling us Bulls"
    # (Day 53). "I'm looking for longs because that's what the daily trend is"
    # (Day 52). And on the gold short he talked himself out of: "why was it
    # against our trading plan? Cuz we were bearish on the hourly. Um we were
    # bullish on the daily, bullish on the 4-hour." (Day 54)
    enforce_daily_bias_side: bool = True

    # HIS: step431 section 12.2 step 7, and section 5.8 verbatim — "if I see
    # that liquidity has already been swept during pre-market AND WE'RE
    # ALREADY REACTING OFF OF IT, awesome. Then this was the liquidity sweep
    # for the day and I'm just going to take a trade reactive off of this."
    # The reaction is the discriminator: reacted -> that is the day's sweep;
    # not reacted -> step434's "wait for another form of manipulation".
    premarket_sweep_carries_forward: bool = True


# ------------------------------------------------------- higher timeframes
def to_et_frame(d: pd.DataFrame) -> pd.DataFrame:
    """UTC parquet -> a frame whose `t` is the bar's START in US Eastern."""
    out = d.copy()
    ts = pd.to_datetime(out["timestamp"], utc=True)
    out["t"] = ts.dt.tz_convert("America/New_York").dt.tz_localize(None)
    return (out[["t", "open", "high", "low", "close"]]
            .sort_values("t").reset_index(drop=True))


def resample_tf(d5: pd.DataFrame, minutes: int,
                anchor_hour: int = 0) -> pd.DataFrame:
    """Build a `minutes` chart out of 5-minute bars.

    `anchor_hour` is the hour the grid is hung from, in US Eastern. On a
    market whose day starts at the 17:00 futures open his 4-hour candles sit
    at 17:00 / 21:00 / 01:00 / 05:00 / 09:00 / 13:00, not on a midnight
    grid, and he says the close time out loud at about 09:25 one morning:
    "this four hour candle won't close for another three and a half hours."
    Three and a half hours from 09:25 is 13:00, which fixes the grid.

    A midnight grid made our last completed 4-hour candle at the bell the
    04:00-08:00 one, which on SPY is built out of thin overnight prints —
    the fund has no bars at all between 00:00 and 04:00. His is 05:00-09:00.

    The offset divides out of any timeframe that goes evenly into an hour,
    so the 1-hour, 15-minute and 5-minute grids are untouched by it.

    `close_t` is when the bar FINISHES, which is the only moment the bot is
    allowed to know it exists.
    """
    cols = ["t", "open", "high", "low", "close", "close_t"]
    if len(d5) == 0:
        return pd.DataFrame(columns=cols)
    off = pd.Timedelta(hours=anchor_hour)
    g = d5.groupby((d5["t"] - off).dt.floor(f"{minutes}min") + off)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "t"
    out = out.reset_index()
    out["close_t"] = out["t"] + pd.Timedelta(minutes=minutes)
    return out


def daily_bars(d5: pd.DataFrame, inst: Instrument = US_INDEX_ETF) -> pd.DataFrame:
    """One candle per trading day. On a market with a closing bell that is
    the regular session only, which is what a daily chart of a fund shows;
    on a 24/7 market it is the whole day."""
    cols = ["t", "open", "high", "low", "close", "close_t"]
    if len(d5) == 0:
        return pd.DataFrame(columns=cols)
    reg = d5
    if inst.has_closing_bell:
        tt = d5["t"].dt.time
        reg = d5[(tt >= inst.open_t) & (tt < inst.close_t)]
    if len(reg) == 0:
        return pd.DataFrame(columns=cols)
    g = reg.groupby(reg["t"].dt.normalize())
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "t"
    out = out.reset_index()
    end_h = 24.0
    if inst.has_closing_bell and inst.close_t is not None:
        end_h = inst.close_t.hour + inst.close_t.minute / 60
    out["close_t"] = out["t"] + pd.Timedelta(hours=end_h)
    return out


def completed_before(tf: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """The only higher-timeframe bars that exist at `now` are the ones that
    have already CLOSED. This one line is the whole no-lookahead guarantee
    for every timeframe above the one being walked."""
    if len(tf) == 0:
        return tf
    return tf[tf["close_t"] <= now].reset_index(drop=True)


# --------------------------------------------------------- the two-candle
# swing: the anchor under trend state, both midpoint anchors, and every
# break of structure (step436 section 2, step431 section 2).
def two_candle_swings(d: pd.DataFrame):
    """HIGH = an up candle then a down candle, level at the HIGHER of the two
    wicks. LOW = a down candle then an up candle, at the LOWER wick. Stamped
    on the SECOND candle, so it is known the moment that candle closes and
    uses nothing after it."""
    o = d["open"].to_numpy(dtype=float); h = d["high"].to_numpy(dtype=float)
    l = d["low"].to_numpy(dtype=float); c = d["close"].to_numpy(dtype=float)
    n = len(d)
    sh = np.full(n, np.nan); sl = np.full(n, np.nan)
    if n < 2:
        return sh, sl
    up, dn = c > o, c < o
    sh[1:] = np.where(up[:-1] & dn[1:], np.maximum(h[:-1], h[1:]), np.nan)
    sl[1:] = np.where(dn[:-1] & up[1:], np.minimum(l[:-1], l[1:]), np.nan)
    return sh, sl


class TrendTracker:
    """Trend state on one timeframe, fed one closed bar at a time.

    In an uptrend you watch only the lows; in a downtrend only the highs
    (step431 section 7.3). A break needs a BODY CLOSE strictly beyond the
    level — a wick does nothing, and a close exactly on the level is not a
    break. A higher low inside a downtrend changes nothing.
    """

    def __init__(self):
        self.prev: Bar | None = None
        self.mrh: float | None = None      # most recent swing high LEVEL
        self.mrl: float | None = None      # most recent swing low LEVEL
        self.state: int = 0                # +1 up, -1 down, 0 not yet known
        self.last_bos_level: float | None = None
        self.last_bos_t = None

    def update(self, bar: Bar) -> int:
        """Returns +1 / -1 if this bar broke structure, else 0."""
        bos = 0
        if self.state >= 0 and self.mrl is not None and bar.c < self.mrl:
            bos, self.last_bos_level = -1, self.mrl
        elif self.state <= 0 and self.mrh is not None and bar.c > self.mrh:
            bos, self.last_bos_level = +1, self.mrh
        if bos:
            self.state = bos
            self.last_bos_t = bar.t
        # then stamp any pivot this bar completes. It uses this bar's own
        # wick, so it cannot have fed the break test above.
        if self.prev is not None:
            if self.prev.c > self.prev.o and bar.c < bar.o:
                self.mrh = max(self.prev.h, bar.h)
            if self.prev.c < self.prev.o and bar.c > bar.o:
                self.mrl = min(self.prev.l, bar.l)
        self.prev = bar
        return bos

    def equilibrium(self) -> float | None:
        """The exact halfway point between the MOST RECENT swing low and the
        MOST RECENT swing high. It re-anchors itself, because mrh and mrl
        move — anchoring to an earlier swing is the error he spends five
        unbroken minutes on."""
        if self.mrh is None or self.mrl is None:
            return None
        return (self.mrh + self.mrl) / 2.0


# ------------------------------------------------------- fair value gaps
@dataclass
class Gap:
    direction: int          # +1 bullish gap, -1 bearish gap
    top: float
    bottom: float
    born: int
    touched: bool = False


class GapBook:
    """Three consecutive candles; the middle one is the only colour that
    matters (step436 section 5). A bullish gap is the LOW of the third above
    the HIGH of the first. Overlapping wicks means there is no gap. It dies
    on a candle CLOSING through it, never on a wick, and that death IS the
    inversion signal."""

    def __init__(self, minutes: int, max_age_bars: int = 288):
        self.minutes = minutes
        self.max_age_bars = max_age_bars
        self.gaps: list[Gap] = []
        self.buf: list[Bar] = []
        self.n = 0

    def update(self, bar: Bar) -> int:
        """Feed one closed bar. Returns +1 / -1 if a gap inverted, else 0."""
        self.n += 1
        inverted = 0
        bulls = [g for g in self.gaps if g.direction > 0]
        bears = [g for g in self.gaps if g.direction < 0]
        lowest_bull = min(bulls, key=lambda g: g.bottom, default=None)
        highest_bear = max(bears, key=lambda g: g.top, default=None)

        keep = []
        for g in self.gaps:
            dead = False
            if g.direction > 0:
                if bar.l <= g.top:
                    g.touched = True
                if bar.c < g.bottom:            # a CLOSE through it, not a wick
                    dead = True
                    if g is lowest_bull:
                        inverted = -1           # only the bottom gap of a stack counts
            else:
                if bar.h >= g.bottom:
                    g.touched = True
                if bar.c > g.top:
                    dead = True
                    if g is highest_bear:
                        inverted = +1
            if not dead:
                keep.append(g)
        # a gap is never dragged forward in time
        self.gaps = [g for g in keep if self.n - g.born <= self.max_age_bars]

        self.buf.append(bar)
        if len(self.buf) > 3:
            self.buf.pop(0)
        if len(self.buf) == 3:
            c1, c2, c3 = self.buf
            step = pd.Timedelta(minutes=self.minutes)
            if (c2.t - c1.t == step) and (c3.t - c2.t == step):
                if c3.l > c1.h:
                    self.gaps.append(Gap(+1, top=c3.l, bottom=c1.h, born=self.n))
                elif c3.h < c1.l:
                    self.gaps.append(Gap(-1, top=c1.l, bottom=c3.h, born=self.n))
        return inverted

    def on_break_of_structure(self, direction: int, level: float | None) -> None:
        """Kill condition 2: the trend continued without needing the gap."""
        if level is None:
            return
        if direction > 0:
            self.gaps = [g for g in self.gaps
                         if not (g.direction > 0 and g.top < level)]
        elif direction < 0:
            self.gaps = [g for g in self.gaps
                         if not (g.direction < 0 and g.bottom > level)]

    def live_in_direction(self, direction: int) -> list[Gap]:
        return [g for g in self.gaps if g.direction == direction]


# ------------------------------------------------------------ the levels
# Higher time frames hold higher power, so when two levels are taken on the
# same bar the higher-ranked one is the setup.
LEVEL_RANK = {"premarket_ny": 1, "15m": 1, "1h": 2, "asia": 2, "london": 2,
              "new_york": 2, "prev_day": 3, "4h": 3}


@dataclass
class Level:
    price: float
    side: int            # +1 a HIGH (price gets pushed UP through it), -1 a LOW
    tf: str              # "1h", "4h", "asia", "london", "prev_day", "15m"
    formed: object


def _unswept(levels: list[Level], d5: pd.DataFrame, now: pd.Timestamp) -> list[Level]:
    """Drop every level price has already traded through. A level pushed past
    with no reaction is dead (step434 step 1, step431 section 4b)."""
    if not levels or len(d5) == 0:
        return list(levels)
    t = d5["t"].to_numpy()
    hi = d5["high"].to_numpy(dtype=float)
    lo = d5["low"].to_numpy(dtype=float)
    out = []
    for lv in levels:
        i = int(np.searchsorted(t, np.datetime64(lv.formed), side="left"))
        j = int(np.searchsorted(t, np.datetime64(now), side="left"))
        if i >= j:
            out.append(lv)
            continue
        if lv.side > 0 and hi[i:j].max() > lv.price:
            continue
        if lv.side < 0 and lo[i:j].min() < lv.price:
            continue
        out.append(lv)
    return out


def swing_levels(d5: pd.DataFrame, minutes: int, now: pd.Timestamp,
                 tag: str, anchor: int = 0) -> list[Level]:
    """Highs and lows on a higher timeframe, from COMPLETED bars only.

    `anchor` is the hour the candle grid hangs from — see `resample_tf`. It
    only changes anything on a timeframe longer than an hour."""
    tf = completed_before(resample_tf(d5, minutes, anchor), now)
    if len(tf) < 2:
        return []
    sh, sl = two_candle_swings(tf)
    known = tf["close_t"].to_numpy()
    out = []
    for i in range(len(tf)):
        if not np.isnan(sh[i]):
            out.append(Level(float(sh[i]), +1, tag, pd.Timestamp(known[i])))
        if not np.isnan(sl[i]):
            out.append(Level(float(sl[i]), -1, tag, pd.Timestamp(known[i])))
    return out


def _window_extremes(d5: pd.DataFrame, start, end):
    w = d5[(d5["t"] >= start) & (d5["t"] < end)]
    if len(w) == 0:
        return None, None
    return float(w["high"].max()), float(w["low"].min())


def _previous_trading_day(d5: pd.DataFrame, day: pd.Timestamp) -> pd.Timestamp | None:
    """The last day before `day` that actually traded. A fixed one-calendar-day
    step lands on Sunday every Monday and on the holiday after every holiday,
    and silently marks no previous-day levels at all on those mornings."""
    if len(d5) == 0:
        return None
    prior = d5["t"][d5["t"] < day]
    if len(prior) == 0:
        return None
    return prior.dt.normalize().max()


def session_levels(d5: pd.DataFrame, day: pd.Timestamp,
                   inst: Instrument = US_INDEX_ETF) -> list[Level]:
    """Asia high/low, London high/low, New York high/low, previous day high/low.

    He names three session pairs and the previous day, not two and the previous
    day: "Asia session highs, Asia session lows, London session highs, London
    session lows, NEW YORK HIGHS, NEW YORK LOWS. All of these are significant
    draws on liquidity." And he trades off the current morning's pre-market
    portion of that New York window by name — "just taking out the pre-market
    New York highs would be pretty solid as well" (bootcamp Day 53).

    VENUE NOTE, a real difference: SPY and QQQ do not trade 20:00 to 04:00
    Eastern. His Asia window is 18:00 to 03:00 and his London window 03:00
    to 08:30; on a fund we can only measure 18:00-20:00 of Asia and
    04:00-08:30 of London. The windows below are his, and what comes back is
    whatever actually traded inside them.
    """
    b = pd.Timedelta(hours=inst.day_boundary_hour)
    prev = _previous_trading_day(d5, day)
    windows = []
    if prev is not None:
        windows.append(("prev_day", prev - pd.Timedelta(days=1) + b, prev + b))
    if inst.early_session_window:
        e0, e1 = inst.early_session_window
        windows.append(("asia", day - pd.Timedelta(days=1) + pd.Timedelta(hours=e0),
                        day + pd.Timedelta(hours=e1)))
    if inst.prior_session_window:
        p0, p1 = inst.prior_session_window
        windows.append(("london", day + pd.Timedelta(hours=p0),
                        day + pd.Timedelta(hours=p1)))
    if inst.own_session_window:
        n0, n1 = inst.own_session_window
        if prev is not None:
            windows.append(("new_york", prev + pd.Timedelta(hours=n0),
                            prev + pd.Timedelta(hours=n1)))
        # the part of today's New York session that has already happened by the
        # bell: his "pre-market New York highs"
        windows.append(("premarket_ny", day + pd.Timedelta(hours=n0),
                        session_start(day, inst)))
    out = []
    for tag, start, end in windows:
        h, l = _window_extremes(d5, start, end)
        if h is not None:
            out.append(Level(h, +1, tag, end))
            out.append(Level(l, -1, tag, end))
    return out


# --------------------------------------------------------------- the news
class NewsCalendar:
    """CPI, PPI, FOMC and NFP block the whole day (step434 section 3B).

    Dates come from news_calendar.py, which reads them off the BLS, Federal
    Reserve and BEA release schedules. Nothing is generated from a rhythm.
    `extra_block` / `extra_derisk` still take a live feed if we ever add one.
    """

    def __init__(self, extra_block=None, extra_derisk=None, rules: bool = True):
        self.extra_block = set(extra_block or ())
        self.extra_derisk = set(extra_derisk or ())
        self.rules = rules          # False = calendar off, for A/B runs

    def blocks(self, day: dt.date) -> str | None:
        if day in self.extra_block:
            return "high-impact release"
        if not self.rules:
            return None
        if not _nc.covers(day):
            return "no release calendar for this date"   # stand down, do not guess
        return _nc.blocking_release(day)                 # e.g. "Consumer Price Index"

    def derisks(self, day: dt.date) -> bool:
        if day in self.extra_derisk:
            return True
        return self.rules and _nc.covers(day) and _nc.derisks_the_day(day)


def session_start(day: pd.Timestamp, inst: Instrument) -> pd.Timestamp:
    """When the session's new money arrives. A market with no bell starts at
    the day boundary and nothing is barred by the clock."""
    if inst.open_t is None:
        return day + pd.Timedelta(hours=inst.day_boundary_hour)
    return day + pd.Timedelta(hours=inst.open_t.hour, minutes=inst.open_t.minute)


def too_early(t, inst: Instrument) -> bool:
    return inst.manip_end_t is not None and t.time() < inst.manip_end_t


def past_cutoff(t, inst: Instrument) -> bool:
    return inst.cutoff_t is not None and t.time() >= inst.cutoff_t


def time_to_be_flat(t, inst: Instrument) -> bool:
    return inst.flat_t is not None and t.time() >= inst.flat_t


def classify_regime(daily: pd.DataFrame, daily_dir: int, cfg) -> str:
    """Which regime the day opened in, from CLOSED daily bars only.

    Why this is recorded at all: under size = dollars risked / stop distance,
    raw volatility CANCELS — a market that moves three times as much puts its
    structure three times further away, so the same risk buys a third of the
    position and nothing is gained. What does not cancel is how far price
    runs before the next untaken level stops it. In a trending regime that
    level is much further away while the stop is still just beyond the sweep.
    So a trend should show up as BETTER REWARD AGAINST RISK at the same risk
    per trade, not as a bigger position and not as a higher win rate. The
    replay reports reward-to-risk split by this field so that is visible
    rather than averaged away.
    """
    n = cfg.regime_ma_days
    if len(daily) < n + 1:
        return "unknown"
    closes = daily["close"].to_numpy(dtype=float)
    ma = float(closes[-n:].mean())
    last = float(closes[-1])
    if daily_dir > 0 and last > ma:
        return "trending up"
    if daily_dir < 0 and last < ma:
        return "trending down"
    return "no trend"


# ------------------------------------------------------- the day's context
@dataclass
class DayContext:
    symbol: str
    day: pd.Timestamp
    daily_dir: int = 0
    h4_dir: int = 0
    h1_dir: int = 0
    bias_dir: int = 0
    profile: str = ""
    regime: str = "unknown"
    continuation_dir: int = 0
    levels: list = field(default_factory=list)
    cont_levels: list = field(default_factory=list)
    premarket_took_a_level: bool = False
    # levels taken between 08:30 and 09:30, as (level, furthest price reached)
    premarket_swept: list = field(default_factory=list)
    stand_down: str | None = None


def london_profile(d5: pd.DataFrame, day: pd.Timestamp,
                   pre_london_levels: list[Level],
                   inst: Instrument = US_INDEX_ETF):
    """His three daily profiles, and there are only three (step434 1A step 2).

      consolidation           -> New York manipulates and then reverses
      manipulation            -> New York delivers the reversal
      manipulation_reversal   -> New York continues that same direction
    """
    if not inst.prior_session_window:
        return "consolidation", 0     # no prior session to read on a 24/7 market
    p0, p1 = inst.prior_session_window
    w = d5[(d5["t"] >= day + pd.Timedelta(hours=p0)) &
           (d5["t"] < day + pd.Timedelta(hours=p1))]
    if len(w) == 0 or not pre_london_levels:
        return "consolidation", 0
    hi, lo = float(w["high"].max()), float(w["low"].min())
    last = float(w["close"].iloc[-1])
    pushed = []
    for lv in pre_london_levels:
        if lv.side > 0 and hi > lv.price:
            pushed.append((lv, +1, hi - lv.price))
        if lv.side < 0 and lo < lv.price:
            pushed.append((lv, -1, lv.price - lo))
    if not pushed:
        return "consolidation", 0
    lv, direction, _ = max(pushed, key=lambda x: x[2])   # the one pushed furthest
    came_back = (last < lv.price) if direction > 0 else (last > lv.price)
    if came_back:
        return "manipulation_reversal", -direction
    return "manipulation", 0


def build_context(symbol: str, d5_hist: pd.DataFrame, day: pd.Timestamp,
                  cfg: Config, news: NewsCalendar) -> DayContext:
    """Everything decided BEFORE 09:30, using only bars that had closed by
    09:30. No orders are ever placed in here."""
    inst = cfg.instrument
    ctx = DayContext(symbol=symbol, day=day)
    open_t = session_start(day, inst)

    blocked = news.blocks(day.date())
    if blocked:
        ctx.stand_down = f"news gate: {blocked} blocks the whole day"
        return ctx

    hist = d5_hist[d5_hist["t"] < open_t]
    if len(hist) == 0:
        ctx.stand_down = "no price history before the open"
        return ctx
    d_dir = hist[hist["t"] >= day - pd.Timedelta(days=cfg.dir_lookback_days)]
    d_lev = hist[hist["t"] >= day - pd.Timedelta(days=cfg.level_lookback_days)]

    # -- direction: the daily and the 4-hour, and they must agree ---------
    tt = TrendTracker()
    dl = completed_before(daily_bars(d_dir, inst), open_t)
    for r in dl.itertuples():
        tt.update(Bar(r.t, r.open, r.high, r.low, r.close))
    ctx.daily_dir = tt.state
    ctx.regime = classify_regime(dl, ctx.daily_dir, cfg)
    tt4 = TrendTracker()
    for r in completed_before(
            resample_tf(d_dir, 240, inst.candle_anchor_hour), open_t).itertuples():
        tt4.update(Bar(r.t, r.open, r.high, r.low, r.close))
    ctx.h4_dir = tt4.state
    tt1 = TrendTracker()
    for r in completed_before(
            resample_tf(d_dir, 60, inst.candle_anchor_hour), open_t).itertuples():
        tt1.update(Bar(r.t, r.open, r.high, r.low, r.close))
    ctx.h1_dir = tt1.state

    if cfg.enforce_daily_4h_agreement:
        if ctx.daily_dir == 0:
            ctx.stand_down = "the daily direction is not yet established"
            return ctx
        if cfg.use_1h_in_direction:
            # the daily is the boss; the 4-hour ideally agrees, and when it does
            # not the 1-hour has to. Both against the daily is the case he sends
            # to the bottom of the list.
            with_daily = [tf for tf, d in (("4-hour", ctx.h4_dir),
                                           ("1-hour", ctx.h1_dir))
                          if d == ctx.daily_dir]
            if not with_daily:
                ctx.stand_down = ("the daily stands alone — the 4-hour and the "
                                  "1-hour are both against it")
                return ctx
        else:
            if ctx.h4_dir == 0:
                ctx.stand_down = "the 4-hour direction is not yet established"
                return ctx
            if ctx.daily_dir != ctx.h4_dir:
                ctx.stand_down = "the daily and the 4-hour disagree"
                return ctx
    ctx.bias_dir = ctx.daily_dir      # the daily wins when they conflict

    # -- mark the levels --------------------------------------------------
    levels = list(session_levels(d_lev, day, inst))
    for m in inst.level_minutes:
        levels += swing_levels(d_lev, m, open_t,
                               f"{m//60}h" if m >= 60 else f"{m}m",
                               inst.candle_anchor_hour)
    pre_open = open_t - pd.Timedelta(hours=1)
    at_830 = _unswept(levels, d_lev, pre_open)
    ctx.levels = _unswept(at_830, d_lev, open_t)
    # Did pre-market already take one of the marked levels? He splits this into
    # two cases and the discriminator is whether price REACTED (step431 5.8):
    #   reacted     -> "this was the liquidity sweep for the day and I'm just
    #                   going to take a trade reactive off of this"
    #   not reacted -> "we need to be waiting for another form of five-minute
    #                   manipulation" (step434 STEP 1)
    # Which of the two applies needs the 5-minute trend at the bell, so the
    # decision itself lives in SymbolDay. Here we only record what was taken
    # and how far past the level price went, which is where the stop rests.
    ctx.premarket_took_a_level = len(ctx.levels) < len(at_830)
    if ctx.premarket_took_a_level:
        kept = {id(lv) for lv in ctx.levels}
        win = d_lev[(d_lev["t"] >= pre_open) & (d_lev["t"] < open_t)]
        for lv in at_830:
            if id(lv) in kept or len(win) == 0:
                continue
            if lv.side > 0:
                past = win[win["high"] > lv.price]
                if len(past) == 0:
                    continue
                ctx.premarket_swept.append(
                    (lv, float(past["high"].max()), past["t"].iloc[0]))
            else:
                past = win[win["low"] < lv.price]
                if len(past) == 0:
                    continue
                ctx.premarket_swept.append(
                    (lv, float(past["low"].min()), past["t"].iloc[0]))

    # -- what London did, measured against the levels that existed before
    #    London started ---------------------------------------------------
    lon_start = day + pd.Timedelta(
        hours=inst.prior_session_window[0] if inst.prior_session_window else 0)
    pre = [lv for lv in levels if lv.formed <= lon_start]
    pre = _unswept(pre, d_lev[d_lev["t"] < lon_start], lon_start)
    ctx.profile, ctx.continuation_dir = london_profile(d_lev, day, pre, inst)

    # Two cases need the smaller-timeframe pool instead of the marked one:
    # a continuation day (New York carries on the way London turned, and the
    # direction comes from the session profile, not from the daily — step436
    # section 10), and a day where pre-market already took the marked level.
    if ctx.profile == "manipulation_reversal" or ctx.premarket_took_a_level:
        tag = f"{inst.continuation_minutes}m"
        ctx.cont_levels = _unswept(
            swing_levels(d_lev, inst.continuation_minutes, open_t, tag,
                         inst.candle_anchor_hour),
            d_lev, open_t)
        if ctx.profile == "manipulation_reversal" and not ctx.cont_levels:
            ctx.stand_down = ("continuation day with no smaller-timeframe "
                              "level left to push through")
            return ctx
    if not ctx.levels and not ctx.cont_levels:
        ctx.stand_down = "no unswept level left to trade off"
    return ctx


# ---------------------------------------------------------- the sequence
@dataclass
class SeqState:
    """Where this symbol is in his four steps, right now."""
    stage: str = "waiting_for_sweep"
    level: Level | None = None
    trade_dir: int = 0
    sweep_extreme: float | None = None
    # The other end of the same leg: the local high price made just before
    # diving to take a low (or the local low before spiking to take a high).
    # This is the line he draws fresh after a sweep, and breaking it is what
    # counts as the turn — see `on_5m`.
    leg_origin: float | None = None
    swept_at: object = None
    sweep_age: int = 0
    confirm_kind: str | None = None
    confirmed_at: object = None
    index_gate_ok: bool = False
    pullback_kind: str | None = None
    pullback_at: object = None
    counter_bos: bool = False


@dataclass
class Trade:
    symbol: str
    day: object
    direction: int
    level_price: float
    level_tf: str
    swept_at: object
    confirm_kind: str
    confirmed_at: object
    pullback_kind: str
    entry_t: object
    entry: float
    stop: float
    stop_anchor: str
    risk_per_share: float
    shares: float
    notional: float
    risk_dollars: float          # what we ACTUALLY risked after the clamp
    risk_wanted: float           # what 1% of equity asked for
    risk_pct_used: float         # actual risk as a fraction of equity
    clamped: bool                # the venue's buying power bound the size
    targets: list          # three or four chart levels, nearest first
    target_srcs: list      # which building block each one is
    escalated: bool
    regime: str
    # what share of the DAY's budget this trade was allowed to spend, and
    # whether it was halved because a second setup was already forming
    budget_share: float = 1.0
    second_setup_expected: bool = False
    size_basis: str = ""
    # the exact inputs the size was worked out from, kept so the live path
    # can be asked for a size on the same inputs and be held to the same
    # answer. See test_the_replay_and_the_live_path_size_identically.
    sizing_account: float = 0.0
    sizing_buying_power: float = 0.0
    sizing_outer_allowance: float = 0.0
    exit_t: object = None
    exit_price: float = 0.0
    outcome: str = ""
    pnl: float = 0.0
    cost: float = 0.0
    r_multiple: float = 0.0
    account_after: float = 0.0
    pct_of_account: float = 0.0
    targets_filled: int = 0      # how many of them price actually reached

    # The first two by name, for anything that only wants those two. A trade
    # with fewer than two building blocks in front of it genuinely has fewer
    # than two targets, and these say so instead of inventing one.
    @property
    def tp1(self) -> float:
        return self.targets[0] if self.targets else float("nan")

    @property
    def tp1_src(self) -> str:
        return self.target_srcs[0] if self.target_srcs else "no building block ahead"

    @property
    def tp2(self) -> float:
        return self.targets[1] if len(self.targets) > 1 else float("nan")

    @property
    def tp2_src(self) -> str:
        return (self.target_srcs[1] if len(self.target_srcs) > 1
                else "no second building block ahead")


class SymbolDay:
    """One symbol, one day, walked forward. The 5-minute is the working
    chart; the 1-minute is only the trigger."""

    def __init__(self, symbol, d5_hist, d1_hist, day, cfg, news, escalated):
        self.symbol, self.cfg, self.day = symbol, cfg, day
        self.escalated = escalated
        self.ctx = build_context(symbol, d5_hist, day, cfg, news)
        self.seq = SeqState()
        self.notes: list[str] = []
        self.blocked_by_direction = False
        self.d5_hist = d5_hist
        self.last_bos1 = 0          # the 1-minute's most recent break, if any

        open_t = session_start(day, cfg.instrument)
        # warm the 5-minute trend and gap book on bars that had ALL closed
        # before the open. Nothing after 09:30 is touched in here.
        self.t5 = TrendTracker()
        self.g5 = GapBook(cfg.instrument.working_minutes, cfg.gap_max_age_bars)
        warm5 = d5_hist[(d5_hist["t"] >= day - pd.Timedelta(days=cfg.seed_days)) &
                        (d5_hist["t"] < open_t)]
        for r in warm5.itertuples():
            b = Bar(r.t, r.open, r.high, r.low, r.close)
            bos = self.t5.update(b)
            self.g5.update(b)
            if bos:
                self.g5.on_break_of_structure(bos, self.t5.last_bos_level)

        # the 1-minute tracker starts in pre-market: that price action counts
        # even though an order can never be placed in it
        self.t1 = TrendTracker()
        warm1 = d1_hist[(d1_hist["t"] >= open_t - pd.Timedelta(hours=1, minutes=30)) &
                        (d1_hist["t"] < open_t)]
        for r in warm1.itertuples():
            self.t1.update(Bar(r.t, r.open, r.high, r.low, r.close))

        # THE PRE-MARKET CARVE-OUT, his step 7 (step431 12.2), decided here
        # because it needs the 5-minute trend as it stood at the bell and
        # nothing after it. "if I see that liquidity has already been swept
        # during pre-market and we're already reacting off of it, awesome.
        # Then this was the liquidity sweep for the day and I'm just going to
        # take a trade reactive off of this. I'm not looking to be taking a
        # trade off of a liquidity sweep from New York market open because the
        # liquidity sweep already happened." The entry still cannot fire in
        # pre-market, still needs the pullback, the index gate and the
        # 1-minute trigger — this only carries the sweep across the bell.
        self.premarket_setup = False
        if cfg.premarket_sweep_carries_forward and self.ctx.premarket_swept:
            best = None
            for lv, extreme, at in self.ctx.premarket_swept:
                if not self._direction_allowed(-lv.side):
                    continue
                d = abs(extreme - lv.price)
                rank = LEVEL_RANK.get(lv.tf, 0)
                if best is None or (rank, d) > (LEVEL_RANK.get(best[0].tf, 0),
                                                abs(best[1] - best[0].price)):
                    best = (lv, extreme, at)
            reacted = (best is not None and
                       self.t5.state == -best[0].side and
                       self.t5.last_bos_t is not None and
                       self.t5.last_bos_t >= best[2])
            if reacted:
                lv, extreme, at = best
                self.seq = SeqState(
                    stage="confirmed", level=lv, trade_dir=-lv.side,
                    sweep_extreme=extreme, swept_at=at, sweep_age=0,
                    confirm_kind="a 5-minute break of structure that printed "
                                 "before the bell",
                    confirmed_at=self.t5.last_bos_t)
                self.premarket_setup = True
                self.notes.append(
                    f"{at:%H:%M} pre-market took the {lv.tf} level at "
                    f"{lv.price:.2f} and the 5-minute already turned against "
                    f"it — that is the day's sweep")

    def _pool(self):
        """A continuation day still needs a smaller-timeframe push-through,
        and so does a day whose marked level was already taken pre-market."""
        if self.ctx.profile == "manipulation_reversal":
            return self.ctx.cont_levels
        return self.ctx.levels + self.ctx.cont_levels

    def _direction_allowed(self, trade_dir: int) -> bool:
        """Which way this day is allowed to trade.

        On a consolidation day or a manipulation-with-no-turn day, New York
        reverses off whichever level it pushes through, so either direction
        is live and the push-through picks it. On a manipulation-and-reversal
        day New York continues the way London turned, so only that direction
        is live. step436 section 10: the taught method sets the direction and
        the daily/4-hour agreement is a veto on the day, not on the side.
        """
        if self.cfg.enforce_daily_bias_side and self.ctx.bias_dir:
            # "can we go against daily bias no... we're going to stick to this
            # bias until we're proved wrong" (bootcamp Day 49). The trade he
            # talked himself out of on Day 54 was refused on exactly this
            # ground: "why was it against our trading plan? Cuz we were bearish
            # on the hourly. Um we were bullish on the daily, bullish on the
            # 4-hour."
            if trade_dir != self.ctx.bias_dir:
                return False
        if self.ctx.profile == "manipulation_reversal":
            return trade_dir == self.ctx.continuation_dir
        return True

    def on_5m(self, bar: Bar) -> None:
        bos = self.t5.update(bar)
        inv = self.g5.update(bar)
        if bos:
            self.g5.on_break_of_structure(bos, self.t5.last_bos_level)
        s, t = self.seq, bar.t

        if s.stage == "waiting_for_sweep":
            best = None
            for lv in self._pool():
                if lv.side > 0 and bar.h > lv.price:
                    d = bar.h - lv.price
                elif lv.side < 0 and bar.l < lv.price:
                    d = lv.price - bar.l
                else:
                    continue
                if not self._direction_allowed(-lv.side):
                    self.blocked_by_direction = True
                    self.notes.append(
                        f"{t:%H:%M} a {lv.tf} level was pushed through, but a "
                        f"trade off it would run against the day's bias")
                    continue
                # higher time frames hold higher power: when several levels
                # are taken on one bar, the highest-timeframe one is the
                # setup and the 15-minute pool only fills in behind it
                rank = LEVEL_RANK.get(lv.tf, 0)
                if best is None or (rank, d) > (LEVEL_RANK.get(best[0].tf, 0), best[1]):
                    best = (lv, d)
            if best:
                lv = best[0]
                s.stage, s.level, s.trade_dir = "swept", lv, -lv.side
                s.sweep_extreme = bar.h if lv.side > 0 else bar.l
                # and the OTHER end of the same leg — the high price made
                # just before diving to take a low, or the low made just
                # before spiking to take a high. He draws that line fresh
                # after every sweep: "again, we made a new high, so I marked
                # that with another red line there. And then we get a break
                # of structure with a closure above equilibrium." (Day 48)
                if s.trade_dir > 0:
                    s.leg_origin = max(bar.h, self.t5.mrh if self.t5.mrh
                                       is not None else bar.h)
                else:
                    s.leg_origin = min(bar.l, self.t5.mrl if self.t5.mrl
                                       is not None else bar.l)
                s.swept_at, s.sweep_age = t, 0
            return

        if s.stage == "swept":
            s.sweep_age += 1
            if s.level.side > 0:
                s.sweep_extreme = max(s.sweep_extreme, bar.h)
            else:
                s.sweep_extreme = min(s.sweep_extreme, bar.l)
            if bos == -s.trade_dir:
                self.notes.append(
                    f"{t:%H:%M} price kept going through the {s.level.tf} level "
                    f"instead of reacting to it — that was never a sweep")
                self.seq = SeqState()
                return
            if s.sweep_age > self.cfg.sweep_max_age_bars:
                self.notes.append(
                    f"{t:%H:%M} the {s.level.tf} level was taken but nothing "
                    f"reacted within {self.cfg.sweep_max_age_bars} bars")
                self.seq = SeqState()
                return
            if bos == s.trade_dir:
                s.confirm_kind = "5-minute break of structure"
            elif s.leg_origin is not None and (
                    bar.c > s.leg_origin if s.trade_dir > 0
                    else bar.c < s.leg_origin):
                # The line drawn fresh after the sweep. Without this the
                # tracker's structural reference is whatever it was before
                # the sweep, which in an established uptrend sits far below
                # price — so a swept low followed by an immediate rally can
                # never confirm, because the break would have to exceed a
                # level price is already well above. That is the largest
                # single stand-down reason in the record, and it bites
                # hardest on a bullish trending morning, which is his
                # favourite condition.
                s.confirm_kind = ("5-minute close back through the price the "
                                  "sweep leg started from")
            elif inv == s.trade_dir:
                s.confirm_kind = "5-minute gap inversion"
            if s.confirm_kind:
                s.stage, s.confirmed_at = "confirmed", t
            return

        if s.stage in ("confirmed", "pullback") and bos == -s.trade_dir:
            self.notes.append(f"{t:%H:%M} the 5-minute turned back against the trade")
            self.seq = SeqState()
            return

        if s.stage == "confirmed":
            # The index gate is a condition on TAKING the trade, not on
            # watching the retrace: "if the indexes weren't aligned at the
            # start of the session, that's fine. They can still get aligned
            # later in the session. So, let's look for it." Gating the
            # observation here threw away a pullback that happened while the
            # two charts were briefly out of step, and it could never come
            # back. `on_1m` still refuses to enter unless the gate is open.
            eq = self.t5.equilibrium()
            hit_eq = eq is not None and (
                (s.trade_dir < 0 and bar.h >= eq) or (s.trade_dir > 0 and bar.l <= eq))
            hit_gap = any(bar.h >= g.bottom and bar.l <= g.top
                          for g in self.g5.live_in_direction(s.trade_dir))
            ok = (hit_eq and hit_gap) if self.escalated else (hit_eq or hit_gap)
            if ok:
                s.stage, s.pullback_at = "pullback", t
                s.pullback_kind = ("the midpoint and a fair value gap" if self.escalated
                                   else "the midpoint" if hit_eq else "a fair value gap")

    def check_index_gate(self, other_state: int) -> None:
        """Both indexes must agree on the 5-minute or there is no trade. They
        may align later in the session, and that is fine (step436 section 12)."""
        s = self.seq
        if s.stage not in ("confirmed", "pullback"):
            return
        if not self.cfg.enforce_index_agreement:
            s.index_gate_ok = True
            return
        s.index_gate_ok = (other_state == s.trade_dir and self.t5.state == s.trade_dir)

    def on_1m(self, bar: Bar) -> bool:
        """One closed 1-minute bar. True when the entry fires.

        His trigger, verbatim: "a one minute break of structure to the upside
        and then one minute break of structure to the downside" for a short.
        The counter-move is watched from the moment the 5-minute confirmed,
        because that break against the trade IS how he sees the 5-minute
        retrace on the 1-minute chart. The entry itself still waits for the
        5-minute pullback to have reached the midpoint or a gap.
        """
        bos = self.t1.update(bar)
        # kept so an OPEN position can be managed off the same 1-minute
        # structure the entry was triggered on: "I closed the rest of the
        # trade out once we broke structure to the downside on the one
        # minute" (Day 9).
        self.last_bos1 = bos
        s = self.seq
        if s.stage not in ("confirmed", "pullback"):
            return False
        if bos == -s.trade_dir:
            s.counter_bos = True          # the pullback, seen on the 1-minute
            return False
        return (s.stage == "pullback" and s.counter_bos and
                s.index_gate_ok and bos == s.trade_dir)

    # ------------------------------------------------- choosing between two
    def confluence_count(self) -> int:
        """How many separate things are lining up behind this setup.

        HIS TEST, OUR TALLY. Day 8, on picking between setups: "which one has
        more confluences, which one is more in line with your daily bias, and
        which one gives a better risk reward — those are kind of the top
        three ones that I would cycle through in my head." The three tests
        and their ORDER are his. Turning "more confluences" into a number is
        OURS, NOT HIS: he counts what he sees on the chart and never lists
        what is on the list. Everything counted below is something the
        sequence had already established for its own reasons, so nothing new
        is invented — but the tally itself is ours, and it is only ever used
        to break a tie between two setups that both already qualify. It can
        never let a trade in or keep one out.
        """
        s, n = self.seq, 0
        pb = str(s.pullback_kind or "")
        if "midpoint" in pb:
            n += 1
        if "fair value gap" in pb:
            n += 1
        if "break of structure" in str(s.confirm_kind or ""):
            n += 1
        if s.level is not None and LEVEL_RANK.get(s.level.tf, 0) >= 3:
            n += 1
        return n

    def timeframes_with_the_trade(self) -> int:
        """His second test: "which one is more in line with your daily bias".
        How many of the daily, the 4-hour and the 1-hour point the same way
        as this trade. All three of them are already read in build_context."""
        d = self.seq.trade_dir
        return sum(1 for x in (self.ctx.daily_dir, self.ctx.h4_dir,
                               self.ctx.h1_dir) if x == d and d != 0)


# ------------------------------------------------------------ the targets
def gaps_at(d5_hist, now, minutes: int, cfg, anchor: int = 0) -> list[Gap]:
    """The fair value gaps alive on a `minutes` chart at `now`.

    Built from CLOSED bars only, so it can be called at fill time without
    the bot learning anything it has not reached. Day 37, on setting a
    target: "we can scale up 15 minute time frame, what do we have here,
    wow would you look at that, a fair value gap, boom, take profit here."
    """
    d5 = d5_hist[(d5_hist["t"] >= now - pd.Timedelta(days=cfg.level_lookback_days)) &
                 (d5_hist["t"] < now)]
    tf = completed_before(resample_tf(d5, minutes, anchor), now)
    book = GapBook(minutes, cfg.gap_max_age_bars)
    for r in tf.itertuples():
        book.update(Bar(r.t, r.open, r.high, r.low, r.close))
    return list(book.gaps)


def _orders_filled_beyond(d5: pd.DataFrame, lv: Level, now) -> float | None:
    """Where the orders actually sat, when the level being targeted is a high
    that was ITSELF taken out before a leg back down.

    HIS RULE, Day 11 "Where to Take Profit", and it is a placement rule we
    did not have:

        "this was a liquidity sweep then a leg down so technically this high
         is not where orders were filled, orders were filled ABOVE this high,
         so with that in mind it's just an easier way for me to be able to
         set take profits... because sometimes you'll see hey why didn't
         price come up and sweep this high, it's because everything from this
         high and above is where previous downward orders were able to get
         filled."

    So a target on such a high goes ABOVE the high, not at it. Mirrored for a
    low. HOW FAR above is not a number he gives, and rather than invent an
    offset this returns THE FURTHEST PRICE THE SWEEP ITSELF REACHED — the top
    of the ground price actually covered when those orders were filled. That
    choice of price is OURS, NOT HIS; the rule that the target belongs above
    the high rather than at it is his.

    Causal: it reads only bars between the moment the level became knowable
    and `now`, both of which have already closed.
    """
    if len(d5) == 0 or lv.formed is None:
        return None
    w = d5[(d5["t"] >= lv.formed) & (d5["t"] < now)]
    if len(w) == 0:
        return None
    last = float(w["close"].iloc[-1])
    if lv.side > 0:
        hi = float(w["high"].max())
        # taken out, and then a leg back down: price is on the near side again
        return hi if hi > lv.price and last < lv.price else None
    lo = float(w["low"].min())
    return lo if lo < lv.price and last > lv.price else None


def building_blocks(d5_hist, now, direction, entry, marked_levels, cfg):
    """Every place he would consider taking profit, beyond the entry, in the
    trade's direction, nearest first.

    "where are we looking to take profit at? okay, it's at our building
    blocks... it's literally just at our building blocks on whatever time
    frame that you're executing on, or whatever one higher time frame you're
    on." (Day 37)

    The building blocks he names are liquidity (previous highs and lows),
    order blocks, fair value gaps and equilibrium. Three of the four are
    here. ORDER BLOCKS ARE NOT — nothing in this bot finds one, so every
    target he would place at an order block is a target we cannot see. That
    is a known hole, written down rather than papered over.

    The gap edge is the FAR one, which is both of his worked examples: for a
    long, "we can target the TOP of that imbalance"; for a short, "you could
    have a take profit within here and at the BOTTOM of it".
    """
    d5 = d5_hist[(d5_hist["t"] >= now - pd.Timedelta(days=cfg.level_lookback_days)) &
                 (d5_hist["t"] < now)]
    tf1 = cfg.instrument.target1_minutes
    out = []

    # (1) liquidity: unswept previous highs and lows one timeframe above the
    #     execution chart. This is the one he states as a rule.
    anchor = cfg.instrument.candle_anchor_hour
    for lv in _unswept(swing_levels(d5, tf1, now, f"{tf1}m", anchor), d5, now):
        if (direction > 0 and lv.side > 0) or (direction < 0 and lv.side < 0):
            out.append((lv.price, f"a {tf1}-minute draw on liquidity", True))

    # (2) liquidity on the marked higher timeframes, "another draw on
    #     liquidity all the way up here"
    for lv in marked_levels:
        if (direction > 0 and lv.side > 0) or (direction < 0 and lv.side < 0):
            beyond = _orders_filled_beyond(d5, lv, now)
            if beyond is None:
                out.append((lv.price, f"a {lv.tf} draw on liquidity", False))
            else:
                out.append((beyond, f"a {lv.tf} draw on liquidity, placed at "
                                    f"the far edge of where the orders were "
                                    f"actually filled", False))

    # (3) fair value gaps on that same higher timeframe
    for g in gaps_at(d5_hist, now, tf1, cfg, anchor):
        edge = g.top if direction > 0 else g.bottom
        out.append((edge, f"the far side of a {tf1}-minute fair value gap", False))

    beyond = [(p, s, isliq) for (p, s, isliq) in out
              if (p > entry if direction > 0 else p < entry)]
    beyond.sort(key=lambda x: (x[0] if direction > 0 else -x[0]))
    return beyond


def build_targets(d5_hist, now, direction, entry, risk_per_share,
                  marked_levels, cfg):
    """Three or four targets, every one of them a chart level.

    Target 1, stated as a rule: "I set it off of the one higher time frame
    draw on liquidity on whatever execution time frame I'm on... let's say we
    take a short position on the five minute, I would probably scale up to
    the 15 minute and find the first draw in liquidity within the direction
    that we're taking the trade... this would be my first take profit."

    The 1:1 is how he PICKS among those draws, not a price of its own:
    "most of the time my first take profit is going to be minimum one to
    one, okay, that's kind of the goal... so boom, one to one, what kind of
    matches up with that? Cool, this high, draw on liquidity, perfect, first
    take profit." So: the first 15-minute draw at or beyond 1:1 if there is
    one, otherwise the nearest building block of any kind at or beyond 1:1.

    NEVER AN INVENTED PRICE. The old code, when nothing sat at or beyond 1:1,
    put target 1 at the 1:1 distance itself and target 2 at twice what was
    risked. Both are a multiple of the risk, and a multiple of the risk is
    the one thing he never targets: "where are we looking to take profit at?
    okay, it's at our building blocks." When there is no building block at or
    beyond 1:1 this returns NOTHING, and the caller records that the chart
    offered nowhere he would take profit. That is the honest answer and it is
    on the unresolved list.

    Targets 2 onward: "the first take profit is going to be the one higher
    time frame draw on liquidity and then I'm going to use building blocks
    for the rest of it... I usually set like three or four take profits."

    He also skips a block that sits on top of one already used — "there's
    this order block right here, but that kind of envelops this high
    already, so what can we do, boom, another draw on liquidity all the way
    up here." How close counts as enveloping is OURS.
    """
    blocks = building_blocks(d5_hist, now, direction, entry, marked_levels, cfg)
    if not blocks:
        return [], []
    floor = entry + direction * risk_per_share
    at_or_past = [b for b in blocks
                  if (b[0] >= floor if direction > 0 else b[0] <= floor)]
    if not at_or_past:
        return [], []
    liq_past = [b for b in at_or_past if b[2]]
    first = liq_past[0] if liq_past else at_or_past[0]

    targets, srcs = [first[0]], [first[1]]
    envelope = cfg.target_envelope_fraction_of_risk * risk_per_share
    for price, src, _ in blocks:
        if len(targets) >= cfg.max_targets:
            break
        if (price - targets[-1]) * direction <= envelope:
            continue
        targets.append(price)
        srcs.append(src)
    return targets, srcs


def target_fractions(n: int, cfg) -> list[float]:
    """How much of the ORIGINAL position comes off at each target.

    HIS, and he says it three times in the same words. Day 9 "Leveraging
    Risk": "we had take profit one right here where I managed 50 of the
    position, we had take profit two right here where I managed ANOTHER
    FIFTY PERCENT OF THE OPEN POSITION, and then I closed the rest of the
    trade out once we broke structure to the downside on the one minute."
    Day 7: "first take profit was just like a simple one-to-one RR off, I
    closed fifty percent of the open position there and move stop to break
    even." Day 5.5: "I've already taken half of this position off and stops
    at break even."

    So: half at target one, half of what is STILL OPEN at target two — which
    is a quarter of the original — and the last quarter is a RUNNER. The
    runner sits on no target. He closes it by hand when the 1-minute breaks
    structure against him, and `TjrBot._manage` does exactly that.

    This replaces an even spread across the tail (50 / 16.7 / 16.7 / 16.7
    with four targets) whose own docstring said it was ours and a guess.
    Targets three, four and five are still set and still reported — he draws
    them and points at them — they simply take nothing off, because the
    ladder he narrates stops after two.
    """
    if n <= 0:
        return []
    first = cfg.partial_fraction
    if n == 1:
        return [first]
    second = (1.0 - first) * cfg.second_partial_fraction
    return [first, second] + [0.0] * (n - 2)


def runner_fraction(n: int, cfg) -> float:
    """What is left over once his ladder is done — the piece he closes by
    hand. A quarter of the original at his usual two-rung ladder."""
    return max(0.0, 1.0 - sum(target_fractions(n, cfg)))


# ============================================================ THE SIZING
#
# ONE FUNCTION. THE REPLAY AND THE LIVE PATH BOTH CALL THIS ONE, AND NOTHING
# ANYWHERE ELSE WORKS OUT A SIZE.
#
# Until 2026-07-26 there were two of them and they disagreed. `TjrBot._open`
# sized fresh at 1% of equity on every trade, which is what every replay and
# every backtest number came out of; `tjr_alerts.position_size` used his set
# size capped at 3%, which is what the orders that actually went out used. So
# the backtests described a bot we were not running. The fix is deletion, not
# agreement: the arithmetic lives here once and `tjr_alerts.position_size` is
# a translation layer in front of it with no arithmetic of its own.
# `test_tjr_bot.test_the_replay_and_the_live_path_size_identically` fails if
# they can ever drift apart again.

STOP_FLOOR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "step443_stop_floors.json")
_STOP_FLOORS: dict = {}


def tightest_stop(symbol: str) -> float:
    """The tightest stop this instrument NORMALLY gives, as a share of the
    price, measured from its own past setups.

    Measured by tjr_desk.derive_stop_floors at the tenth percentile of that
    instrument's own stop distances — "what's USUALLY the lowest your stop
    loss will be during a trade" — and stored in step443_stop_floors.json.
    Read here rather than imported, so this module still imports nothing that
    can reach a broker.

    ZERO when it has never been measured for this symbol. Borrowing another
    market's number is the one thing his rule forbids: "Bitcoin's tightest
    stop and SPY's are permanently different numbers."
    """
    global _STOP_FLOORS
    if not _STOP_FLOORS:
        try:
            with open(STOP_FLOOR_PATH) as fh:
                _STOP_FLOORS = json.load(fh)
        except (FileNotFoundError, ValueError):
            _STOP_FLOORS = {"__missing__": True}
    row = _STOP_FLOORS.get(symbol) or {}
    return float(row.get("tightest_stop_pct") or 0.0)


def size_position(account: float, entry: float, stop_distance: float,
                  risk_allowance: float, tightest_stop_pct: float = 0.0,
                  usd_per_quote: float = 1.0,
                  buying_power: float | None = None,
                  outer_allowance: float | None = None) -> dict:
    """HIS ARITHMETIC, ONCE. Every path that needs a size calls this.

    THE RULE, from the bootcamp day he gives entirely to position size:

        "you're going to set your stop loss in points — what's usually the
         LOWEST your stop loss will be during a trade. For me it's usually
         400. We calculate that, boom, 25 lots. That is going to be our SET
         lot size. And you're probably saying, well that doesn't make any
         sense — well it does, because that means I'm going to be risking one
         percent if price hits stop right here. That also means I'll be
         risking two percent of my account if we have a larger stop loss."

    So the size is worked out ONCE, off the TIGHTEST stop the instrument
    normally gives, such that THAT stop would cost `risk_allowance`. Then it
    is held still. A wider stop today therefore costs proportionally more,
    and that is the rule rather than a leak in it — his one-to-three-percent
    band is the OUTPUT of holding the size still, never a dial.

    account         the equity the day's budget was worked out on
    entry           the reference price
    stop_distance   today's stop, in the price
    risk_allowance  DOLLARS this trade may spend if the tightest stop is hit
                    — its share of the DAY's budget, not a per-trade ceiling
    tightest_stop_pct  that instrument's own tightest stop, as a share of the
                    price. ZERO means it has never been measured, and the
                    size then falls out of today's stop instead; the answer
                    says which of the two it was.
    usd_per_quote   1 everywhere except a yen pair, where profit arrives in
                    yen and has to become dollars before the size means
                    anything — off by a factor of about 145 if it is wrong
    buying_power    the broker's own figure. None means do not clamp.
    outer_allowance DOLLARS still free under the DAY's outer limit. When the
                    set size would spend more than the day has left, the size
                    is cut and `capped` says so.
    """
    out = {"units": 0.0, "lots": 0.0, "per_step": 0.0, "ok": False,
           "risk_dollars": 0.0, "risk_share_pct": 0.0, "wider": 1.0,
           "risk_wanted": float(risk_allowance or 0.0), "measured": False,
           "capped": False, "clamped": False, "basis": "not worked out"}
    if (account <= 0 or entry <= 0 or stop_distance <= 0 or usd_per_quote <= 0
            or not risk_allowance or risk_allowance <= 0):
        return out

    baseline = float(tightest_stop_pct or 0.0) * float(entry)
    measured = baseline > 0
    if measured:
        basis = ("his set size, worked out off the tightest stop this market "
                 "normally gives and then held still")
    else:
        # Never measured. Sizing off another market's number is what his rule
        # forbids, so the size falls out of TODAY's stop instead, which makes
        # the allowance exact rather than a floor. Said out loud in `basis`.
        baseline = float(stop_distance)
        basis = ("today's own stop — this market's tightest stop has never "
                 "been measured, and borrowing another market's is what his "
                 "rule forbids")
    units = float(risk_allowance) / (baseline * usd_per_quote)
    risk_dollars = units * stop_distance * usd_per_quote
    uncapped_units, uncapped_risk = units, risk_dollars

    # THE OUTER LIMIT, AND IT IS NOW ON THE DAY. His band tops out at three
    # percent OF THE ACCOUNT ON THE DAY, so what is passed in here is what
    # the day has left, not a fresh ceiling for every trade.
    capped = False
    if outer_allowance is not None and float(outer_allowance) > 0 and \
            risk_dollars > float(outer_allowance):
        units *= float(outer_allowance) / risk_dollars
        risk_dollars = units * stop_distance * usd_per_quote
        capped = True

    # THE VENUE'S OWN CEILING, which is not a choice of ours either.
    clamped = False
    if buying_power is not None and entry > 0:
        max_units = float(buying_power) / entry
        if units > max_units:
            units = max_units
            risk_dollars = units * stop_distance * usd_per_quote
            clamped = True

    out.update({
        "units": units, "lots": units / 100_000, "ok": True,
        "basis": basis, "measured": measured, "baseline_stop": baseline,
        "risk_dollars": risk_dollars,
        "risk_share_pct": 100.0 * risk_dollars / account,
        # how much wider today's stop is than the one the size was set on
        "wider": stop_distance / baseline if baseline else 1.0,
        "capped": capped, "clamped": clamped,
        "uncapped_units": uncapped_units,
        "uncapped_risk_dollars": uncapped_risk,
        "uncapped_risk_share_pct": 100.0 * uncapped_risk / account,
        "per_step": units * usd_per_quote})
    return out


# ======================================================== THE DAY'S BUDGET
@dataclass
class DayBudget:
    """What the day may lose, and the ledger the trades draw from.

    HIS, Day 8 "How to split positions" and Day 9 "Leveraging Risk", which
    together are the biggest fill in Boot Camp 2.0:

        "if you do have two trades that you are able to take during the day
         make sure your risk plan is like set up and ready for that... I'm
         going to go in with like half of what I would want to risk on the
         day knowing damn well that I'm probably going to take a second trade"
        "I only risked 50 of what I was willing to risk for the day"
        "we lost 50 of what we were willing to lose once take profit one got
         hit okay now we're down to like 25 of what we were willing to lose
         for the day"
        "that gives me the ability to now know that hey the most I'm going to
         lose on the day is going to be 25, I can now risk an extra 75 of
         whatever I'm willing to risk on the day"
        "if I risk 75 of what I'm willing to risk on the day and I'm only
         down 25... then if this one hits stop loss then I'll lose 100 of
         what I'm willing to risk on the day"

    So the accounting is in SHARES OF ONE DAY'S BUDGET: what the open trades
    are holding plus what has already been lost may never exceed 100%, and a
    trade that has taken target one and moved its stop to break even stops
    holding half of what it was holding.

    A SECOND, SEPARATE LEDGER runs alongside it in dollars, against the top
    of his band — three percent of the account, on the day. It exists because
    the set size does not shrink for a wider stop, so a day can hold 100% of
    its budget in his accounting and still be carrying two or three times the
    budget in real dollars. That is exactly the one-to-three-percent band he
    describes, and the outer ledger is where it stops.

    NOTHING HERE HALTS TRADING AFTER A LOSS. Day 12 "Red Day": he took three
    losses, took a fourth trade at the same size, and says "if this was a
    fourth loss I would have been completely okay with it". What ends his day
    is this budget running out, never the count of losses.
    """
    account: float
    share_of_account: float          # 1% normally, half that on a news day
    outer_share: float               # 3% — the top of his band, on the day
    held: float = 0.0                # shares of the budget the OPEN trades hold
    lost: float = 0.0                # shares of the budget already lost
    dollars_at_risk: float = 0.0     # what the open trades can still lose
    dollars_lost: float = 0.0        # what the day has already lost

    @property
    def budget_dollars(self) -> float:
        return self.account * self.share_of_account

    @property
    def outer_dollars(self) -> float:
        return self.account * self.outer_share

    def free(self) -> float:
        """Shares of the day's budget still available. His 75%."""
        return max(0.0, 1.0 - self.held - self.lost)

    def outer_free(self) -> float:
        """Dollars still available under the top of his band."""
        return max(0.0, self.outer_dollars - self.dollars_at_risk
                   - self.dollars_lost)

    def take(self, share: float, risk_dollars: float) -> None:
        self.held += share
        self.dollars_at_risk += risk_dollars

    def to_break_even(self, share: float, risk_dollars: float) -> None:
        """Target one filled and the stop moved to the entry: the trade can
        no longer cost what it was holding, so the budget comes back."""
        self.held = max(0.0, self.held - share)
        self.dollars_at_risk = max(0.0, self.dollars_at_risk - risk_dollars)

    def release(self, share: float, risk_dollars: float, pnl: float) -> None:
        """The trade is closed. It stops holding anything, and whatever it
        actually lost is spent. A winner spends nothing and frees the lot."""
        self.held = max(0.0, self.held - share)
        self.dollars_at_risk = max(0.0, self.dollars_at_risk - risk_dollars)
        if pnl < 0:
            self.dollars_lost += -pnl
            if self.budget_dollars > 0:
                self.lost += -pnl / self.budget_dollars


# ----------------------------------------------------------------- the bot
class TjrBot:
    """The method, run day by day. `run_day` walks one session forward, bar
    by bar, and never reads a bar it has not reached."""

    def __init__(self, cfg: Config | None = None, news: NewsCalendar | None = None):
        self.cfg = cfg or Config()
        self.news = news or NewsCalendar()
        self.account = self.cfg.account_start
        self.buying_power: float | None = None   # live: the broker's own number
        self.week_pnl: dict = {}
        self.escalated = False

    def _buying_power(self) -> float:
        if self.buying_power is not None:
            return float(self.buying_power)
        return self.account * self.cfg.buying_power_multiple

    def refresh_escalation(self, day: pd.Timestamp) -> None:
        """A bad run tightens the filter, it does not stop trading. Two losing
        WEEKS promote the entry bar, so the pullback must show the midpoint
        AND a fair value gap rather than either one (step436 section 8)."""
        wk = (day - pd.Timedelta(days=day.weekday())).normalize()
        past = sorted(k for k in self.week_pnl if k < wk)
        need = self.cfg.losing_weeks_to_escalate
        self.escalated = (len(past) >= need and
                          all(self.week_pnl[k] < 0 for k in past[-need:]))

    def run_day(self, data: dict, day: pd.Timestamp, stop_at=None) -> dict:
        """One session, both index charts, strictly forward.

        MORE THAN ONE TRADE A DAY IS THE METHOD, NOT AN EDGE CASE (step452
        item 4). This used to hold a single `trade` and break out of the walk
        the moment it resolved. He runs two, three ("we took three trades
        today, absurd for me", Day 9) and four (Day 12), and what governs is
        the day's budget rather than a count. So the walk now keeps going,
        several positions can be open at once, and `DayBudget` is the thing
        that stops the day.

        data:    {symbol: {"5m": frame, "1m": frame}}, `t` in US Eastern
        stop_at: walk no further than this timestamp — the truncation test
                 uses it to ask "what had you decided by then".
        """
        cfg = self.cfg
        self.refresh_escalation(day)
        derisk = self.news.derisks(day.date())
        risk_pct = cfg.risk_pct_derisk if derisk else cfg.risk_pct_normal

        syms = list(data.keys())
        legs = {s: SymbolDay(s, data[s]["5m"], data[s]["1m"], day, cfg,
                             self.news, self.escalated) for s in syms}
        budget = DayBudget(account=self.account, share_of_account=risk_pct,
                           outer_share=cfg.max_day_risk_share)
        self.budget = budget
        result = {"day": day, "escalated": self.escalated, "derisk": derisk,
                  "trade": None, "trades": [], "budget": budget,
                  "stand_down": {}, "notes": {},
                  "context": {s: legs[s].ctx for s in syms}}
        for s in syms:
            if legs[s].ctx.stand_down:
                result["stand_down"][s] = legs[s].ctx.stand_down
        live = [s for s in syms if legs[s].ctx.stand_down is None]
        if not live:
            return result

        inst = cfg.instrument
        open_t = session_start(day, inst)
        end_t = day + pd.Timedelta(hours=24 if inst.close_t is None
                                   else inst.close_t.hour)
        d1 = {s: data[s]["1m"][(data[s]["1m"]["t"] >= open_t) &
                               (data[s]["1m"]["t"] < end_t)] for s in syms}
        d5 = {s: data[s]["5m"][(data[s]["5m"]["t"] >= open_t) &
                               (data[s]["5m"]["t"] < end_t)] for s in syms}
        if any(len(d1[s]) == 0 for s in live):
            for s in live:
                result["stand_down"].setdefault(s, "no session bars — market shut")
            return result

        idx = {s: {r.t: Bar(r.t, r.open, r.high, r.low, r.close)
                   for r in d1[s].itertuples()} for s in syms}
        rows5 = {s: {r.t + pd.Timedelta(minutes=5):
                     Bar(r.t, r.open, r.high, r.low, r.close)
                     for r in d5[s].itertuples()} for s in syms}
        stamps = sorted({t for s in live for t in idx[s]})

        open_trades: list[Trade] = []
        taken: list[Trade] = []
        for t in stamps:
            close_t = t + pd.Timedelta(minutes=1)
            if stop_at is not None and close_t > stop_at:
                break

            # 1) any 5-minute bar closing right now, on EVERY symbol first,
            #    so the index gate reads both charts at the same instant
            #    EVERY symbol, not just the tradeable ones: the veto is "if
            #    the S&P 500 and the NASDAQ on the five minute are not aligned,
            #    I do not want to be taking a trade", and that reads the other
            #    chart's 5-minute trend whether or not he would trade that
            #    chart today. Reading only the tradeable ones switched the veto
            #    off on every day the other index had stood down.
            fired5 = False
            for s in syms:
                b5 = rows5[s].get(close_t)
                if b5 is not None:
                    legs[s].on_5m(b5)
                    fired5 = True
            if fired5:
                for s in live:
                    others = [legs[o].t5.state for o in syms if o != s]
                    legs[s].check_index_gate(others[0] if others else legs[s].t5.state)

            # 2) the 1-minute bar, fed to every live symbol whether or not it
            #    is holding a position, because the runner is closed off this
            #    same 1-minute structure
            fires = []
            for s in live:
                b1 = idx[s].get(t)
                if b1 is None:
                    continue
                if legs[s].on_1m(b1):
                    fires.append((s, b1))

            # 3) manage what is already open, on the bar that just closed
            for tr in list(open_trades):
                self._manage(tr, idx[tr.symbol].get(t), budget,
                             legs[tr.symbol].last_bos1)
                if tr.outcome:
                    open_trades.remove(tr)

            # 4) 10:30: he stops LOOKING, he does not stop managing. "if I
            #    can't find a trade by 10:30, I'm done." With nothing open
            #    and nothing left to find, the day is over.
            if past_cutoff(t, inst):
                if not open_trades:
                    break
                continue

            # 5) new entries. Never before 09:50, never after 10:30.
            if not fires:
                continue
            if too_early(t, inst):
                for s, _ in fires:
                    legs[s].notes.append(
                        f"{t:%H:%M} the trigger landed inside the manipulation "
                        f"window — no entry")
                continue
            for s, b1 in self._choose(legs, fires, day):
                if budget.free() < cfg.min_budget_share_to_open:
                    legs[s].notes.append(
                        f"{t:%H:%M} a setup completed but the day's risk "
                        f"budget is spent — {100*budget.free():.0f}% of it is "
                        f"left and he does not open on less than "
                        f"{100*cfg.min_budget_share_to_open:.0f}%")
                    continue
                second = self._second_setup_forming(legs, live, s)
                tr = self._open(legs[s], b1, day, budget, second,
                                legs[s].d5_hist)
                if tr is None:
                    continue
                open_trades.append(tr)
                taken.append(tr)
                # a fresh setup is needed before this symbol may fire again:
                # the sweep that produced this trade has been used
                legs[s].seq = SeqState()

        for s in syms:
            result["notes"][s] = legs[s].notes
            if legs[s].ctx.stand_down is None and not any(
                    tr.symbol == s for tr in taken):
                result["stand_down"].setdefault(s, self._why_no_trade(legs[s]))

        for tr in open_trades:
            if not tr.outcome:
                self._force_flat(tr, idx[tr.symbol], budget)
        for tr in taken:
            self.account += tr.pnl
            tr.account_after = self.account
        wk = (day - pd.Timedelta(days=day.weekday())).normalize()
        self.week_pnl[wk] = (self.week_pnl.get(wk, 0.0)
                             + sum(tr.pnl for tr in taken))
        result["trades"] = taken
        # kept for every caller that predates the day budget. It is the FIRST
        # trade of the day, which is the one that used to be the only one.
        result["trade"] = taken[0] if taken else None
        return result

    @staticmethod
    def _second_setup_forming(legs: dict, live: list, this: str) -> bool:
        """Is a second setup already visibly forming somewhere else?

        HIS RULE, Day 8: "when I see like two or three trade setups for the
        day like today right... I pretty much was like okay cool like I'm
        going to go in with like half of what I would want to risk on the day
        knowing damn well that I'm probably going to take a second trade."

        HOW WE SEE IT IS OURS, NOT HIS. He is looking at several charts and
        judging it. Our stand-in is the only observable equivalent: another
        symbol whose sequence has already CONFIRMED — the level was taken
        there and the 5-minute has turned on it, so what is left is a
        pullback and a trigger. A level merely pushed through is not yet a
        setup and does not count. It reads nothing from the future and it can
        only ever HALVE a size, never enlarge one.
        """
        for o in live:
            if o == this:
                continue
            if legs[o].seq.stage in ("confirmed", "pullback"):
                return True
        return False

    def _choose(self, legs: dict, fires: list, day) -> list:
        """Several setups completed on the same minute — his order of tests.

        HIS, Day 8, and the ORDER is his: "which one has more confluences,
        which one is more in line with your daily bias, and which one gives a
        better risk reward — those are kind of the top three ones that I would
        cycle through in my head." The worked example is arithmetic on the
        reward, not on feel: he dropped a setup because "the best it was going
        to give me was a one to one, or actually when I mapped it out it was
        like a one to like 0.7... that's not worth it to me when gu is giving
        me like a one two 1.5 on my first take profit."

        This RANKS, it does not refuse. Every setup here has already passed
        the entry sequence. When the day's budget can fund them all, they are
        all taken and the ranking only decides who draws first — "let's say
        you got like three and two of them are higher probability than the
        other, there's no reason to take all three, just split those positions
        up amongst those two trades."
        """
        if len(fires) < 2:
            return fires

        def rank(item):
            s, b1 = item
            leg = legs[s]
            reward = 0.0
            seq = leg.seq
            entry = b1.c
            buf = self.cfg.stop_buffer_pct_of_price * entry
            stop = (seq.sweep_extreme + buf if seq.trade_dir < 0
                    else seq.sweep_extreme - buf)
            rps = abs(entry - stop)
            if rps > 0:
                tg, _ = build_targets(leg.d5_hist,
                                      b1.t + pd.Timedelta(minutes=1),
                                      seq.trade_dir, entry, rps,
                                      leg.ctx.levels, self.cfg)
                if tg:
                    reward = abs(tg[0] - entry) / rps
            return (leg.confluence_count(), leg.timeframes_with_the_trade(),
                    reward)

        return sorted(fires, key=rank, reverse=True)

    @staticmethod
    def _why_no_trade(leg: SymbolDay) -> str:
        s = leg.seq
        if s.stage == "waiting_for_sweep":
            if leg.blocked_by_direction:
                return ("a level was pushed through, but only on the side the "
                        "day's bias forbids")
            return "no marked level was pushed through before 10:30"
        if s.stage == "swept":
            return (f"a {s.level.tf} level was swept but the 5-minute never "
                    f"turned before 10:30")
        if s.stage == "confirmed" and not s.index_gate_ok:
            return "the two indexes never agreed on the 5-minute before 10:30"
        if s.stage == "confirmed":
            return "no 5-minute pullback into the midpoint or a gap before 10:30"
        if s.stage == "pullback":
            return "the 1-minute never broke back with the trade before 10:30"
        return "the sequence did not complete before 10:30"

    def _open(self, leg: SymbolDay, b1: Bar, day, budget: DayBudget,
              second_setup: bool, d5_hist) -> Trade | None:
        """Open one trade against the DAY's budget.

        The share it may spend is his: half the day's budget when a second
        setup is already forming (Day 8), otherwise whatever the day has
        left. The size then falls out of `size_position`, which is the same
        function the live path calls.
        """
        cfg, s = self.cfg, leg.seq
        entry = b1.c
        buf = cfg.stop_buffer_pct_of_price * entry
        stop = s.sweep_extreme + buf if s.trade_dir < 0 else s.sweep_extreme - buf
        rps = abs(entry - stop)
        if rps <= 0:
            return None
        # THE STOP HAS TO BE ON THE PROTECTIVE SIDE OF THE ENTRY, and once in
        # a while it is not: `sweep_extreme` freezes when the 5-minute
        # confirms, so a pullback that runs back past it and then triggers
        # would put a short's stop BELOW its entry. That is not a trade, it is
        # a position with nothing under it. The live order path already
        # refuses the same thing at the venue — on 26 July it opened a DOT
        # short, could not place the stop because price had already run past
        # where the stop belonged, and closed the position one second later.
        # Refusing here is that same refusal, one step earlier.
        if (stop <= entry) if s.trade_dir < 0 else (stop >= entry):
            leg.notes.append(
                f"{b1.t:%H:%M} price had already run back past where the stop "
                f"belonged, so there was nothing to put under the trade — no "
                f"entry")
            return None

        share = (cfg.first_trade_share_when_second_expected if second_setup
                 else 1.0)
        share = min(share, budget.free())
        if share < cfg.min_budget_share_to_open:
            return None
        risk_wanted = share * budget.budget_dollars
        bp, outer = self._buying_power(), budget.outer_free()

        size = size_position(
            account=budget.account, entry=entry, stop_distance=rps,
            risk_allowance=risk_wanted,
            tightest_stop_pct=tightest_stop(leg.symbol),
            buying_power=bp, outer_allowance=outer)
        if not size["ok"]:
            leg.notes.append(f"{b1.t:%H:%M} the size could not be worked out")
            return None
        shares = size["units"]
        clamped = size["clamped"]
        if second_setup:
            leg.notes.append(
                f"{b1.t:%H:%M} a second setup was already forming elsewhere, "
                f"so this one took {100*share:.0f}% of the day's risk budget "
                f"instead of all of it")
        if size["capped"]:
            leg.notes.append(
                f"{b1.t:%H:%M} size cut to hold the DAY inside "
                f"{100*cfg.max_day_risk_share:.0f}% of the account: the set "
                f"size would have put ${size['uncapped_risk_dollars']:,.0f} "
                f"at risk and the day had ${budget.outer_free():,.0f} left")
        if clamped:
            leg.notes.append(
                f"{b1.t:%H:%M} size clamped by buying power: wanted "
                f"${size['uncapped_risk_dollars']:,.0f} at risk, took "
                f"${size['risk_dollars']:,.0f} "
                f"({100*size['risk_dollars']/budget.account:.2f}% of the "
                f"account)")
        risk_dollars = size["risk_dollars"]
        notional = shares * entry

        targets, target_srcs = build_targets(
            d5_hist, b1.t + pd.Timedelta(minutes=1), s.trade_dir, entry, rps,
            leg.ctx.levels, cfg)
        if not targets:
            # He never says what to do here and this is not an entry rule, so
            # nothing is refused: the position simply has no place to take
            # profit and runs to its stop or to the close. Recorded so it is
            # visible if it ever actually happens.
            leg.notes.append(f"{b1.t:%H:%M} no building block anywhere ahead of "
                             f"the entry — this trade has no take profit")
        tr = Trade(
            symbol=leg.symbol, day=day, direction=s.trade_dir,
            level_price=s.level.price, level_tf=s.level.tf, swept_at=s.swept_at,
            confirm_kind=s.confirm_kind, confirmed_at=s.confirmed_at,
            pullback_kind=s.pullback_kind, entry_t=b1.t, entry=entry, stop=stop,
            stop_anchor=(f"beyond the furthest price reached while the "
                         f"{s.level.tf} level was being taken, plus a spread buffer"),
            risk_per_share=rps, shares=shares, notional=notional,
            risk_dollars=risk_dollars, risk_wanted=risk_wanted,
            risk_pct_used=(risk_dollars / budget.account if budget.account
                           else 0.0),
            clamped=clamped, targets=targets, target_srcs=target_srcs,
            escalated=self.escalated, regime=leg.ctx.regime,
            budget_share=share, second_setup_expected=second_setup,
            size_basis=size["basis"], sizing_account=budget.account,
            sizing_buying_power=bp, sizing_outer_allowance=outer)
        tr._share_held = share
        tr._risk_held = risk_dollars
        budget.take(share, risk_dollars)
        return tr

    def _manage(self, tr: Trade, b1: Bar | None, budget: DayBudget | None = None,
                bos1: int = 0) -> None:
        """His ladder, and then the runner he closes by hand.

        HIS, Day 9: "we had take profit one right here where I managed 50 of
        the position, we had take profit two right here where I managed
        another fifty percent of the OPEN position, and then I closed the rest
        of the trade out once we broke structure to the downside on the one
        minute." So half at target one, a quarter at target two, and the last
        quarter is a runner with no resting target on it — it comes off when
        the 1-minute breaks structure against the trade, and otherwise it
        stops at break even, which is a NORMAL outcome he describes and there
        is no logic here that tries to avoid it.

        The stop moves once, to the entry, when the first target fills, and
        never again — he describes no trail and none is added. That move is
        also what releases budget back to the day: "we lost 50 of what we were
        willing to lose, once take profit one got hit, okay, now we're down to
        like 25 of what we were willing to lose for the day."
        """
        if b1 is None or tr.outcome:
            return
        d = tr.direction
        if not hasattr(tr, "_open_shares"):
            tr._open_shares, tr._realised = tr.shares, 0.0
            tr._filled, tr._stop_now = 0, tr.stop
            tr._fracs = target_fractions(len(tr.targets), self.cfg)
            tr._rungs = sum(1 for f in tr._fracs if f > 0)
        # the stop is checked first inside a bar: we never take the good side
        # of an ambiguous bar
        if (b1.l <= tr._stop_now) if d > 0 else (b1.h >= tr._stop_now):
            self._close(tr, tr._stop_now, b1.t,
                        "stopped at break even" if tr._filled else "stopped out",
                        budget)
            return
        while tr._filled < len(tr.targets):
            tp = tr.targets[tr._filled]
            if not ((b1.h >= tp) if d > 0 else (b1.l <= tp)):
                break
            part = min(tr.shares * tr._fracs[tr._filled], tr._open_shares)
            tr._realised += part * (tp - tr.entry) * d
            tr._open_shares -= part
            tr._filled += 1
            tr.targets_filled = tr._filled
            if tr._filled == 1:
                tr._stop_now = tr.entry      # break even, once, after target 1
                if budget is not None:
                    # HIS 50 -> 25: the trade stops holding half of what it
                    # was holding, and the rest goes back to the day.
                    back = tr._share_held * self.cfg.break_even_releases_share
                    back_d = tr._risk_held * self.cfg.break_even_releases_share
                    budget.to_break_even(back, back_d)
                    tr._share_held -= back
                    tr._risk_held -= back_d
        if tr._open_shares <= 1e-9:
            self._close(tr, tr.targets[-1], b1.t,
                        f"all {tr._filled} targets reached", budget)
            return
        # THE RUNNER. His ladder is done and the last piece has no resting
        # target — he closes it on the opposite break of structure on the
        # 1-minute. OURS, and marked: he also has targets three, four and
        # five drawn, and if price reaches the last of them the runner comes
        # off there rather than being carried past every level he named.
        if tr._rungs and tr._filled >= tr._rungs and bos1 == -d:
            self._close(tr, b1.c, b1.t,
                        "the 1-minute broke structure against the trade — the "
                        "rest closed by hand", budget)
            return
        if time_to_be_flat(b1.t, self.cfg.instrument):
            self._close(tr, b1.c, b1.t, "flat by the close", budget)

    def _force_flat(self, tr: Trade, index: dict,
                    budget: DayBudget | None = None) -> None:
        if tr.outcome:
            return
        if not index:
            self._close(tr, tr.entry, tr.entry_t, "no bars left, flat at entry",
                        budget)
            return
        last = max(index)
        self._close(tr, index[last].c, last, "flat by the close", budget)

    def _close(self, tr: Trade, price: float, t, outcome: str,
               budget: DayBudget | None = None) -> None:
        if not hasattr(tr, "_open_shares"):
            tr._open_shares, tr._realised, tr._filled = tr.shares, 0.0, 0
        tr._realised += tr._open_shares * (price - tr.entry) * tr.direction
        tr._open_shares = 0.0
        tr.cost = self.cfg.instrument.round_trip_cost_pct * tr.shares * tr.entry
        tr.pnl = tr._realised - tr.cost
        tr.exit_t, tr.exit_price, tr.outcome = t, price, outcome
        tr.r_multiple = tr.pnl / tr.risk_dollars if tr.risk_dollars else 0.0
        tr.account_after = self.account + tr.pnl
        tr.pct_of_account = 100.0 * tr.pnl / self.account if self.account else 0.0
        if budget is not None:
            budget.release(getattr(tr, "_share_held", 0.0),
                           getattr(tr, "_risk_held", 0.0), tr.pnl)
            tr._share_held, tr._risk_held = 0.0, 0.0


# ------------------------------------------------------- the causal probe
def decide_at(data: dict, day: pd.Timestamp, ts: pd.Timestamp,
              cfg: Config | None = None, news: NewsCalendar | None = None,
              escalated: bool = False) -> dict:
    """What had the bot decided by the close of the 1-minute bar starting at
    `ts`? Calling this on the whole history and calling it with every bar
    after `ts` DELETED must give the same answer. That is the test."""
    bot = TjrBot(cfg, news)
    bot.escalated = escalated
    res = bot.run_day(data, day, stop_at=ts + pd.Timedelta(minutes=1))
    tr = res["trade"]
    return {
        "stand_down": dict(res["stand_down"]),
        "entry": None if tr is None else (
            tr.symbol, tr.direction, round(tr.entry, 6), round(tr.stop, 6),
            tr.level_tf, round(tr.level_price, 6), str(tr.entry_t)),
    }


# ------------------------------------------------------------------- live
@dataclass
class LivePosition:
    """What the live loop has to remember between minutes. Everything here
    is decided at fill time and never widened afterwards."""
    symbol: str
    direction: int          # +1 long, -1 short
    entry: float
    stop: float             # moves to entry ONCE, after target 1, and never again
    shares: float           # what is STILL OPEN right now, not the original size
    original_shares: float = 0.0     # what was filled, so the slices stay fixed
    targets: list = field(default_factory=list)
    targets_filled: int = 0

    def __post_init__(self):
        if not self.original_shares:
            self.original_shares = self.shares


def manage_step(pos: LivePosition, last: Bar, cfg: Config | None = None,
                bos1: int = 0) -> dict:
    """What to do with an open position on this closed bar.

    HIS LADDER, Day 9: half the position at target one, "another fifty
    percent of the OPEN position" at target two — a quarter of the original —
    and "then I closed the rest of the trade out once we broke structure to
    the downside on the one minute". From the first fill onward the stop sits
    at break even. A runner stopped at break even is a NORMAL outcome and
    there is nothing here that tries to avoid it. The stop is never widened,
    never removed, never moved before target 1, and never trailed. Size is
    never added.

    `bos1` is the 1-minute chart's most recent break of structure on this bar
    (+1 up, -1 down, 0 none). It is the only thing that closes the runner
    before its stop or the final target, and it is what he does by hand.

    Returns one of:
      {"action": "hold"}
      {"action": "take_partial", "shares": .., "price": .., "new_stop": ..}
      {"action": "close", "shares": .., "price": .., "reason": ..}
    """
    cfg = cfg or Config()
    inst = cfg.instrument
    d = pos.direction
    hit_stop = (last.l <= pos.stop) if d > 0 else (last.h >= pos.stop)
    if hit_stop:
        return {"action": "close", "shares": pos.shares, "price": pos.stop,
                "reason": ("stopped at break even" if pos.targets_filled
                           else "stopped out")}
    n = pos.targets_filled
    fracs = target_fractions(len(pos.targets), cfg)
    rungs = sum(1 for f in fracs if f > 0)
    if n < rungs:
        # still on his ladder: half, then half of what is open
        tp = pos.targets[n]
        if (last.h >= tp) if d > 0 else (last.l <= tp):
            want = min(pos.original_shares * fracs[n], pos.shares)
            if n == len(pos.targets) - 1 or want >= pos.shares:
                return {"action": "close", "shares": pos.shares, "price": tp,
                        "reason": f"all {n + 1} targets reached"}
            return {"action": "take_partial", "shares": want, "price": tp,
                    "new_stop": pos.entry,
                    "reason": (f"target {n + 1} reached: "
                               f"{100 * fracs[n]:.0f}% off, stop at break even")}
    elif rungs:
        # THE RUNNER. Targets three, four and five are drawn and pointed at
        # and take nothing off; the runner rides through them and comes off
        # on the opposite break of structure on the 1-minute. A position with
        # no target at all never becomes a runner — his ladder never ran, so
        # it goes to its stop or to the close.
        if len(pos.targets) > rungs:
            fin = pos.targets[-1]
            if (last.h >= fin) if d > 0 else (last.l <= fin):
                return {"action": "close", "shares": pos.shares, "price": fin,
                        "reason": f"all {len(pos.targets)} targets reached"}
        if bos1 == -d:
            return {"action": "close", "shares": pos.shares, "price": last.c,
                    "reason": ("the 1-minute broke structure against the "
                               "trade — the rest closed by hand")}
    if time_to_be_flat(last.t, inst):
        return {"action": "close", "shares": pos.shares, "price": last.c,
                "reason": "flat by the close"}
    return {"action": "hold"}


def live_step(data: dict, now: pd.Timestamp, account: float,
              buying_power: float | None = None, clock: dict | None = None,
              cfg: Config | None = None, news: NewsCalendar | None = None,
              week_pnl: dict | None = None) -> dict:
    """The one call a live loop makes. Returns an intention, never an order.

    data         : {symbol: {"5m": frame, "1m": frame}} in US Eastern, ending
                   at the last CLOSED 1-minute bar
    now          : the CLOSE time of that last 1-minute bar, US Eastern
    account      : the broker's own equity figure. Read it, do not compute it.
    buying_power : the broker's own figure too. Omitted -> 4x equity.
    clock        : Alpaca's /v2/clock. Missing, or shut, and this refuses.
                   That refusal is deliberate: a bot that cannot read the
                   clock must not send.

    Returns:
      {"action": "stand_down" | "wait" | "enter", "reason": str, ...}
      On "enter": symbol, direction (+1 long, -1 short), reference price,
      stop, shares, both targets, and the chart feature the stop rests on.
    """
    cfg = cfg or Config()
    if not clock or not clock.get("is_open"):
        return {"action": "stand_down",
                "reason": "the market is shut or the clock is unreadable"}
    if not isinstance(now, pd.Timestamp):
        return {"action": "stand_down", "reason": "the clock is unreadable"}
    inst = cfg.instrument
    if inst.open_t is not None and now.time() < inst.open_t:
        return {"action": "stand_down",
                "reason": "pre-market: he never enters here"}
    if past_cutoff(now, inst):
        return {"action": "stand_down",
                "reason": f"past the {inst.cutoff_t:%H:%M} cut-off — done for the day"}

    day = now.normalize()
    bot = TjrBot(cfg, news)
    bot.account = float(account)
    bot.buying_power = None if buying_power is None else float(buying_power)
    bot.week_pnl = dict(week_pnl or {})
    res = bot.run_day(data, day, stop_at=now)
    # MORE THAN ONE TRADE A DAY IS THE METHOD, so the one that matters on
    # this minute is the one that fired on this minute, not the first of the
    # day. Reading res["trade"] here silently ignored every trade after the
    # first the moment the day budget went in.
    fired = [t for t in res["trades"]
             if t.entry_t == now - pd.Timedelta(minutes=1)]
    if not fired:
        if not res["trades"]:
            why = "; ".join(f"{k}: {v}" for k, v in res["stand_down"].items())
            return {"action": "wait", "escalated": res["escalated"],
                    "reason": why or "the sequence has not completed yet"}
        last = res["trades"][-1]
        return {"action": "wait",
                "reason": f"the entry fired at {last.entry_t}, already handled"}
    tr = fired[0]
    if too_early(now, inst):
        return {"action": "wait", "reason": "inside the manipulation window"}
    return {"action": "enter", "symbol": tr.symbol, "direction": tr.direction,
            "reference_price": tr.entry, "stop": tr.stop, "shares": tr.shares,
            "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
            "target_fractions": target_fractions(len(tr.targets), cfg),
            "runner_fraction": runner_fraction(len(tr.targets), cfg),
            "target1": tr.tp1, "target2": tr.tp2,
            "partial_fraction": cfg.partial_fraction,
            "budget_share": tr.budget_share,
            "second_setup_expected": tr.second_setup_expected,
            "size_basis": tr.size_basis,
            # the exact three inputs the size was worked out from. A caller
            # that re-sizes rather than sending tr.shares must pass these
            # three into tjr_alerts.position_size or it will get a different
            # number the moment a second position is open.
            "sizing_account": tr.sizing_account,
            "buying_power_used": tr.sizing_buying_power,
            "outer_allowance": tr.sizing_outer_allowance,
            "stop_anchor": tr.stop_anchor, "level_tf": tr.level_tf,
            "level_price": tr.level_price, "confirmed_by": tr.confirm_kind,
            "pullback_into": tr.pullback_kind, "notional": tr.notional,
            "risk_dollars": tr.risk_dollars, "risk_wanted": tr.risk_wanted,
            "risk_pct_used": tr.risk_pct_used, "clamped": tr.clamped,
            "reason": (f"a {tr.level_tf} level at {tr.level_price:.2f} was swept, "
                       f"{tr.confirm_kind}, both indexes agreed, pullback into "
                       f"{tr.pullback_kind}, the 1-minute broke back with the trade")}
