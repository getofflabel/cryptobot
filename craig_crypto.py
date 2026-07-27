"""
craig_crypto.py — Craig Percoco's method, pointed at crypto. A SECOND engine.

WHY THIS FILE EXISTS AT ALL
    `tjr_bot.py` / `tjr_crypto.py` encode a man who trades two stock index
    futures. Pointed at crypto that method has never had a profitable year:
    2021-2026 on the five surviving pairs it lost every year except a 2021
    reading that is entirely SOL in the year SOL itself did a hundred times,
    and one 2024 on Bitcoin. Thousands of trades, a majority stopped out, and
    a median stop of 0.70% AS A MOVE IN THE PRICE on coins whose typical hour
    overnight moves 0.27%. The stop was smaller than the noise.

    Craig Percoco actually trades crypto, and his stop is not a number at all
    — it is a CANDLE. "Set up my stop loss outside of the fair value gap
    producing candle." That means the stop is as wide as the market's own
    candles were at the moment of the setup, so it grows at the New York open
    and shrinks overnight without a single constant anywhere. That one
    property is the whole reason this engine was built.

    NOTHING HERE TOUCHES THE TJR FILES. This module imports exactly two pure
    helpers from `tjr_bot` (a swing stamp and a size calculation) and the
    parquet path helper from `tjr_crypto`. It writes nothing, fetches nothing,
    and places no orders. Replay only.

HIS METHOD, IN HIS ORDER, FROM `cp_transcripts/clean.txt`
    1. "We're going to be waiting for our session open, whether it's Asia
       session, London session, New York session. I'm trading New York
       session that opens at 9:30 a.m."
    2. "A change of character is effectively where I have say a downtrend
       where I have the highs getting continually lower and the lows getting
       continually lower and then after a lower low we get a candle that
       pushes up and produces a new high." — IN PLAIN WORDS: a candle closing
       beyond the most recent swing point against the trend.
       "Looking to identify the FIRST change of character that happens in
       this session."
    3. "A fair value gap is ... a series of three candles where the first
       candle's high wick ... does not overlap with the low of the third
       candle's wick and it leaves a space here with no wick."
    4. "Waiting for a pullback into what's called my golden 61.8 ratio and
       the middle point of that fair value gap ... have a fair value gap
       align between this 50 level and this 61.8 level."
    5. "Wait for price to trade into the 50% midpoint of this fair value gap.
       And that's going to be where I'm looking for my entries."
    6. "Set up my stop loss outside of the fair value gap producing candle.
       So underneath this low would be my stop loss. So this is my negative
       1R."
    7. "I basically want to target 3 to 4R in the opposite direction." Every
       worked example on the chart is drawn at 1:4. One late example is drawn
       at 1:1. Both are here; 1:4 ships.
    8. "Waiting for a candle to close over this most recent swing up before
       our entry ... that's going to allow me to then reduce this risk all
       the way to break even."
    9. "I trade for about 2 hours a day." "Modeled around trading for 1 to
       two hours per day."

WHAT HE NEVER SAYS, AND WHAT WE CHOSE — every one of these is a config field
and every one is marked OURS, NOT HIS at its definition below:
    - the chart timeframe the change of character is read on
    - how a swing point is identified
    - how long after the open he keeps looking
    - how long a resting entry stays live before it is abandoned
    - what invalidates a setup before it fills
    - how long a position may be held
    - which sessions apply on a 24/7 market

COSTS
    The measured round trip for each pair is subtracted from every closed
    trade so the dollars are honest. Nothing in this file declines a trade,
    prefers a pair, or moves a threshold because of what trading costs.
    Owner rule, 2026-07-25.

SAFETY
    No orders, no network, no git, no writes to any existing file. This module
    reads cached parquet and returns decisions.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# The two pure helpers we borrow, and nothing else.
#   two_candle_swings — a swing stamp that is knowable the moment its second
#                       candle closes and uses nothing after it. Craig requires
#                       swing points and never says how to find them; this is
#                       the project's existing, tested primitive and reusing it
#                       keeps one definition of "swing" in the repo.
#   size_position     — the ONE place in this project that turns a stop into a
#                       number of units. See SIZING below.
from tjr_bot import size_position, two_candle_swings
import tjr_crypto

REPO = os.path.dirname(os.path.abspath(__file__))

# His list, unchanged. LINK / ADA / LTC are retired by Wallace and do not
# come back on the strength of a backtest.
PAIRS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOT/USD"]


# ============================================================ THE SESSIONS
#
# OURS, NOT HIS — the wall-clock times are his, the decision to keep all three
# on a 24/7 market is ours.
#
# He names Asia, London and New York and says he personally trades New York at
# 09:30. Wallace's position is that "sessions have nothing to do with btc",
# and tonight's measurement half agrees with him: Bitcoin's trendiness is flat
# across all 24 hours (0.283 to 0.334, no hour stands out), so session opens do
# not buy a CLEANER trend. What they do buy is SIZE — the typical hour at 10:00
# New York time moves 0.51% of the price against 0.27% at 01:00 New York time,
# a factor of two.
#
# So all three ship on, and every result in this file is also broken out per
# session, so the data settles it rather than either of us.
#
# Each entry is (IANA zone, hour, minute) in that city's own local time, so
# daylight saving is handled by the zone rather than by a fixed UTC offset —
# New York's open is 13:30 UTC in summer and 14:30 UTC in winter, and getting
# that wrong would put the whole book an hour off for five months a year.
SESSIONS = {
    "asia":     ("Asia/Tokyo",       9, 0),    # Tokyo cash open
    "london":   ("Europe/London",    8, 0),    # London cash open
    "new_york": ("America/New_York", 9, 30),   # HIS session, his words
}


@dataclass
class CraigConfig:
    """Every number Craig states, and every number he does not.

    Fields marked HIS are quoted from the transcript. Fields marked OURS are
    ours, with the reason, and are the only ones that may be argued about.
    """

    # ---------------------------------------------------------------- HIS
    fib_deep: float = 0.618      # "my golden 61.8 ratio"
    fib_shallow: float = 0.50    # "align between this 50 level and this 61.8"
    entry_at_gap_midpoint: bool = True   # "the 50% midpoint of this fair value gap"
    target_r: float = 4.0        # "target 3 to 4R"; every chart drawn at 1:4
    breakeven_on_swing_close: bool = True   # "reduce this risk all the way to break even"
    first_choch_only: bool = False
    max_setups_per_session: int = 2

    # WHICH BREAKS HE TAKES — OURS, NOT HIS, and it is the difference between
    # catching a trend day and sitting through one.
    #
    # His step 1 says "looking to identify the FIRST change of character that
    # happens in this session", which is one trade per session and a reversal
    # every time. But he also says "sometimes I'll be able to find THREE TO
    # FIVE of these per session", and the only way both are true is that after
    # the change of character has set the new trend, each further break of
    # structure THE SAME WAY is another leg, another fib, another gap in the
    # 50-61.8 zone and another entry. That is exactly the picture he draws
    # after the entry: "a low, a high, a low here, and then a new high".
    #
    # It also decides the acceptance case. On 26 July 2026 ETH was already
    # trending up when New York opened and ran 2.17% as a move in the price
    # from there. There is no change of character in that session — the flip
    # happened before the bell — so `choch_only` stands down on the best day
    # of the month. `choch_and_continuation` takes the pullback.
    #
    #   "choch_only"              his step 1, literally
    #   "choch_and_continuation"  ships, and both are measured
    entries: str = "choch_and_continuation"

    # --------------------------------------------------------------- OURS
    # THE CHART. He never names a timeframe. His worked examples show a 09:30
    # session marker and a change of character forming within a handful of
    # candles of the open, then a fib, then a three-candle gap inside that same
    # move — a 1-to-5-minute chart, not an hourly one. 5-minute ships because
    # it is the only resolution we hold for all five pairs back to 2021 (DOT's
    # 1-minute history starts 2026-03-01), so the 12-month table is measured on
    # one chart rather than two. The 1-minute arm is measured separately.
    entry_tf: str = "5m"

    # THE SWING. He shows swing points on a chart and never defines one. This
    # is `tjr_bot.two_candle_swings`: an up candle then a down candle stamps a
    # high at the higher of the two wicks. It is stamped on the second candle,
    # so it is knowable the moment that candle closes.
    swing_rule: str = "two_candle"

    # HOW LONG HE KEEPS LOOKING. "I trade for about 2 hours a day", "modeled
    # around trading for 1 to two hours per day". 120 minutes from the open.
    hunt_minutes: int = 120

    # HOW MANY BARS OF CONTEXT BEFORE THE OPEN. A trend has to already exist
    # for a change of character to be a change OF anything, and he reads it off
    # the chart he is already looking at. 60 bars = 5 hours on the 5-minute.
    context_bars: int = 60

    # HOW LONG THE RESTING ENTRY STAYS LIVE. He places a limit at the gap
    # midpoint and does not say when he gives up on it. 24 bars = 2 hours on
    # the 5-minute, which is the length of his own trading day.
    entry_valid_bars: int = 24

    # WHAT KILLS A SETUP BEFORE IT FILLS. If price closes beyond where the
    # stop would be, the structure that produced the setup is gone and there is
    # nothing left to trade. He does not say this; it follows from his stop.
    cancel_on_close_beyond_stop: bool = True

    # HOW LONG A POSITION MAY BE HELD. He says nothing. Crypto has no bell and
    # Wallace's rule is "crypto runs 24/7, then let it run 24/7 — dont cut
    # shit", so this is a backstop against a position living forever in the
    # replay, not a rule. Reported: how many trades ever reach it.
    max_hold_hours: float = 48.0

    # WHICH SESSIONS. See SESSIONS above.
    sessions: tuple = ("asia", "london", "new_york")

    # WHERE THE STOP IS ANCHORED. His words are "outside of the fair value gap
    # producing candle", and the candle that produces a three-candle gap is the
    # middle one — the momentum candle that jumped the distance. When that
    # candle's own extreme does not sit beyond the entry (it can happen when
    # the gap is wide and the middle candle is small) the setup falls back to
    # the extreme of all three candles, and the trade records which was used.
    stop_anchor: str = "middle_candle"

    # HOW THE POSITION IS ACTUALLY ENTERED. "fvg_midpoint" is HIS, and it is a
    # RESTING LIMIT: he waits for price to come back to the middle of the gap.
    #
    # "market_on_signal" IS NOT HIS AND IS NOT THE DEFAULT. It exists because
    # of one measured failure. On 26 July 2026 ETH ran 2.17% as a move in the
    # price; the engine called the reversal correctly at the New York open and
    # then never filled, because price retraced 24% of the leg and his zone
    # starts at 50%. A limit that waits for a pullback cannot board a move that
    # does not pull back. This switch buys at the open of the candle after the
    # signal instead, keeps his stop and keeps his 1:4, and exists so the cost
    # of his patience can be put in dollars rather than argued about.
    entry_style: str = "fvg_midpoint"

    # WHICH GAP WHEN SEVERAL SIT IN THE ZONE. "largest" (the biggest pocket of
    # momentum) or "nearest_618" (the one closest to his golden ratio). See
    # the note at the selection itself.
    gap_choice: str = "largest"

    # HOW SMALL A GAP IS STILL A GAP — OURS, NOT HIS, and it ships OFF (0.0)
    # so every headline number is his rule unfiltered.
    #
    # WHY IT EXISTS. On 3 August 2025 a DOT setup had a gap 0.006% of the
    # price wide. His stop is outside the candle that made the gap, so the
    # stop was 0.00023 of a $3.57 coin; sizing 3% of equity against that
    # distance asks for 465x leverage, and the round trip on that notional
    # took $107,476 off a $93,000 account IN ONE TRADE and killed the pair for
    # the rest of the year. A gap that small is not "a pocket of momentum", it
    # is the tick.
    #
    # The dial is the gap's width as a share of the 50-to-61.8 band it has to
    # sit in. He says the gap should "align between this 50 level and this
    # 61.8 level"; a gap thousands of times narrower than that band is a point,
    # not something that aligns with it. Reported as a sensitivity, never swept
    # to rescue a result.
    min_gap_share_of_zone: float = 0.0

    # ------------------------------------------------------------- SIZING
    # Matched to the TJR book's shipping default so the two engines' dollars
    # are comparable: 3% of CURRENT equity per trade, size falling out of
    # today's own stop. That is also Craig's own arithmetic, word for word:
    # "500 divided by $18 in this case ... that's going to give us the amount
    # of units that we need to enter at this price in order to risk exactly
    # $500".
    risk_pct_per_trade: float = 0.03
    account_start: float = 100_000.0

    # NO BUYING-POWER CLAMP. Alpaca's crypto cash rule (multiple 1.0) and the
    # index book's 4x are both venue facts about venues this engine is not
    # aimed at, and BloFin's ceiling is neither. Leverage here is an OUTPUT of
    # the stop, reported, never an input.
    buying_power_multiple: float | None = None

    # -------------------------------------------------------------- COSTS
    # The pair's own measured round trip, as a share of notional. Charged on
    # every closed trade, consulted by nothing.
    round_trip_cost_pct: float = 0.0

    pair: str = ""


def config_for(pair: str, **over) -> CraigConfig:
    """The config for one pair, with its own measured trading cost."""
    derived = tjr_crypto.load_derived().get(pair) or {}
    cost = derived.get("spread_pct")
    if cost is None:
        raise RuntimeError(f"no measured round trip for {pair}")
    return dataclasses.replace(CraigConfig(pair=pair,
                                           round_trip_cost_pct=float(cost)),
                               **over)


# ================================================================ THE DATA
def load(pair: str) -> dict:
    """The cached bars. REUSES `tjr_crypto.cache_name`; fetches nothing and
    writes nothing. A previous agent truncated nine months of history with a
    careless refetch, so this path is read-only on purpose."""
    return {tf: pd.read_parquet(tjr_crypto.cache_name(pair, tf))
            for tf in ("5m", "1m")}


_TF_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}


def bars(data: dict, tf: str) -> pd.DataFrame:
    """The chart at `tf`. The cached 1-minute and 5-minute frames are returned
    as they are; anything larger is built from the 5-minute by resampling and
    is never fetched. Nothing is written back to disk.

    HE NEVER NAMES A TIMEFRAME, so this is the dial the transcript leaves open
    and `step467_craig_replay.py --timeframes` turns it. His one arithmetically
    usable worked example — "500 divided by $18" against a price he quotes at
    3137 — puts his own stop at about 0.57% AS A MOVE IN THE PRICE, and no
    5-minute crypto candle is that big. That is a measurement, not a rule, and
    the sweep is what settles it.
    """
    if tf in data:
        return data[tf]
    m = _TF_MINUTES.get(tf)
    if m is None or m % 5:
        raise ValueError(f"cannot build {tf} from the cached 5-minute bars")
    d = data["5m"]
    out = (d.set_index("t")
           .resample(f"{m}min", label="left", closed="left")
           .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
           .dropna().reset_index())
    data[tf] = out
    return out


def session_opens(start, end, name: str) -> list:
    """Every session open between `start` and `end`, as naive UTC timestamps.

    The conversion runs through the city's own zone so the open moves with
    daylight saving instead of drifting an hour against it for five months.
    """
    zone, hh, mm = SESSIONS[name]
    out = []
    day = pd.Timestamp(start).normalize()
    last = pd.Timestamp(end).normalize()
    while day <= last:
        local = pd.Timestamp(year=day.year, month=day.month, day=day.day,
                             hour=hh, minute=mm, tz=zone)
        out.append(local.tz_convert("UTC").tz_localize(None))
        day += pd.Timedelta(days=1)
    return sorted(t for t in out
                  if pd.Timestamp(start) <= t <= pd.Timestamp(end)
                  + pd.Timedelta(days=1))


# ============================================================== THE SETUP
@dataclass
class Setup:
    """One change of character with a gap in its 50-61.8 zone, stamped at the
    close of the candle that produced the change of character and using NO bar
    after it."""
    pair: str
    session: str
    direction: int              # +1 long, -1 short
    kind: str                   # "choch" (his step 1) or "continuation"
    choch_t: pd.Timestamp       # the candle whose body closed beyond the swing
    choch_i: int
    broken_level: float         # the swing point his candle closed beyond
    leg_low: float
    leg_high: float
    zone_deep: float            # the 61.8 retracement
    zone_shallow: float         # the 50 retracement
    gap_lo: float
    gap_hi: float
    gap_mid_t: pd.Timestamp     # the gap-producing (middle) candle
    entry: float
    stop: float
    target: float
    stop_from: str              # "middle_candle" or "three_candles"
    be_level: float             # the swing his candle must close beyond for break-even

    @property
    def stop_pct(self) -> float:
        """The stop as A MOVE IN THE PRICE, not a share of anything else."""
        return abs(self.entry - self.stop) / self.entry


def find_setups(d: pd.DataFrame, open_i: int, end_i: int,
                cfg: CraigConfig, pair: str = "", session: str = "") -> list:
    """His steps 2, 3, 4 and 6 on one window of closed candles.

    CAUSALITY IS THE CONTRACT. A setup stamped at bar `i` is computed from
    bars 0..i only. Deleting every bar after `i` must return the identical
    setup, and `test_craig_crypto.py` deletes them and checks.

    `open_i` and `end_i` bound where a setup may be STAMPED — inside his 1-to-2
    hours from the open. The bars before `open_i` are the context the trend is
    read from, exactly as they are on his screen at the open.

    THE TREND IS A STATE THAT PERSISTS, NOT A SNAPSHOT — and this is the single
    most important construction decision in the file, so here is the working.

    Read "the highs getting continually lower and the lows getting continually
    lower" as a test applied to the last two swings at each instant and the
    engine sees a trend on about a third of bars, because on a 5-minute crypto
    chart the swings alternate too fast for two of each to line up. Built that
    way it produced NO SETUP AT ALL on 26 July 2026 ETH, the day the coin ran
    2.17% as a move in the price and Wallace made over $170 catching it by
    hand. That is a disqualifying failure and it is a construction bug, not a
    finding about his method.

    What he actually draws is a state machine, and he says so: "price was
    trending up and then finally produced a new low OUT OF THAT UPTREND which
    is NOW STARTING a potential downtrend". The market is in a downtrend from
    the moment it closes below a swing low until it closes above a swing high.
    The flip IS the change of character. That is what is built here.
    """
    n = len(d)
    if n < 4 or open_i >= n:
        return []
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    t = d["t"].to_numpy()
    sh, sl = two_candle_swings(d)

    mrh = mrl = None       # most recent stamped swing high / low LEVEL
    state = 0              # +1 up, -1 down, 0 not yet known
    last_break_i = 0       # the bar of the last body close beyond a swing
    setups: list = []
    end_i = min(end_i, n - 1)
    want_continuations = cfg.entries == "choch_and_continuation"

    for i in range(n):
        # ---- 1. does THIS candle's body close beyond the standing swing? ----
        event, broke = None, 0
        if mrh is not None and c[i] > mrh:
            broke = +1
            event = "choch" if state < 0 else ("continuation" if state > 0 else None)
        elif mrl is not None and c[i] < mrl:
            broke = -1
            event = "choch" if state > 0 else ("continuation" if state < 0 else None)

        # ---- 2. is it a setup he would take? --------------------------------
        take = event == "choch" or (want_continuations and event == "continuation")
        if take and open_i <= i <= end_i and \
                len(setups) < max(1, cfg.max_setups_per_session):
            # WHERE THE FIB STARTS. One rule covers both cases: the move that
            # just broke began at its own extreme SINCE THE LAST BREAK. After a
            # change of character that is the bottom of the trend that ended;
            # after a continuation it is the pullback low, which is the "low, a
            # high, a LOW HERE, and then a new high" he draws. Anchoring a
            # continuation on the original bottom instead puts the 50-61.8 zone
            # a whole trend away from price and the entry never fills — which
            # is precisely how 26 July's ETH run was missed.
            seg = slice(last_break_i, i + 1)
            anchor = last_break_i + (int(np.argmin(lo[seg])) if broke > 0
                                     else int(np.argmax(h[seg])))
            s = _build(d, o, h, lo, c, t, i, broke, anchor,
                       (mrh if broke > 0 else mrl), cfg, pair, session,
                       kind=event)
            if s is not None:
                setups.append(s)
                if cfg.first_choch_only and event == "choch":
                    return setups
                if len(setups) >= max(1, cfg.max_setups_per_session):
                    return setups

        if broke != 0:
            state = broke
            last_break_i = i
            # a broken swing is spent; the next one is stamped by the tape
            if broke > 0:
                mrh = None
            else:
                mrl = None

        # ---- 3. stamp this bar's own swing, AFTER it has been read against --
        if not np.isnan(sh[i]):
            mrh = float(sh[i])
        if not np.isnan(sl[i]):
            mrl = float(sl[i])

    return setups


def _bar_step(t):
    """The chart's own candle width, read off the tape rather than assumed, so
    the same code works on the 5-minute and the 1-minute. `None` when the
    window is too short or too broken to tell."""
    if len(t) < 4:
        return None
    diffs = np.diff(t)
    vals, counts = np.unique(diffs, return_counts=True)
    return vals[int(np.argmax(counts))]


def _build(d, o, h, lo, c, t, i, direction, start_i, broken, cfg, pair,
           session, kind="choch"):
    """Steps 3 to 6: the fib over the move that broke, the gap sitting in its
    50-61.8 zone, the entry at that gap's midpoint, the stop outside the
    candle that produced it.

    `start_i` is where the move began — the extreme the trend ran from, which
    the state machine has been carrying. HIS WORDS are precise about this:
    "click at the BEGINNING OF THIS MOVE down to THE BOTTOM once we start to
    get a push up." The fib is drawn over the whole leg that just reversed,
    not over the last two candles of it. Anchoring it on the last stamped
    swing instead gave 3-candle legs, 0.004%-of-price stops and a book of
    coin-flips.
    """
    if i - start_i < 2:
        return None
    if direction > 0:
        leg_low = float(np.min(lo[start_i:i + 1]))
        leg_high = float(np.max(h[start_i:i + 1]))
    else:
        leg_high = float(np.max(h[start_i:i + 1]))
        leg_low = float(np.min(lo[start_i:i + 1]))

    rng = leg_high - leg_low
    if rng <= 0:
        return None

    # ---- the fib. "premium and discount zones on a move" -----------------
    if direction > 0:
        z_deep = leg_high - cfg.fib_deep * rng        # the 61.8, further away
        z_shallow = leg_high - cfg.fib_shallow * rng  # the 50, nearer
        zone_lo, zone_hi = z_deep, z_shallow
    else:
        z_deep = leg_low + cfg.fib_deep * rng
        z_shallow = leg_low + cfg.fib_shallow * rng
        zone_lo, zone_hi = z_shallow, z_deep

    # ---- the fair value gap, inside the move, sitting in that zone -------
    #
    # "A SERIES OF THREE CANDLES" — his words, and they mean three CONSECUTIVE
    # candles. The Alpaca crypto tape has minutes with no trade in them, so a
    # window of three ROWS is not always three candles: 03:25, 03:30, 03:45 is
    # three rows with a 10-minute hole in the middle, and the "gap" it shows is
    # the hole, not a pocket of momentum. Rows that are not consecutive on the
    # chart's own grid are skipped.
    step = _bar_step(t[:i + 1])     # read off the past only, never the window
    best = None
    for k in range(start_i, i - 1):
        if step is not None and (t[k + 2] - t[k]) != 2 * step:
            continue                                        # a hole, not a gap
        if direction > 0:
            g_lo, g_hi = float(h[k]), float(lo[k + 2])      # bullish gap
        else:
            g_lo, g_hi = float(h[k + 2]), float(lo[k])      # bearish gap
        if g_hi <= g_lo:
            continue                                        # no gap: they overlap
        if g_hi < zone_lo or g_lo > zone_hi:
            continue                                        # not in his zone
        if cfg.min_gap_share_of_zone > 0 and \
                (g_hi - g_lo) < cfg.min_gap_share_of_zone * (zone_hi - zone_lo):
            continue                                        # the tick, not a gap
        mid = 0.5 * (g_lo + g_hi)
        # WHICH GAP, WHEN SEVERAL QUALIFY — OURS, NOT HIS, and it matters more
        # than it looks. He says the 50-to-61.8 filter is what "allows me to
        # filter through fair value gaps and find the MOST IMPORTANT ONES",
        # and on his chart one obvious gap is left. On a 5-minute crypto tape
        # several survive, most of them a few cents wide. A gap is "a pocket
        # of MOMENTUM" in his own definition, so the biggest pocket in the
        # zone is the one he is pointing at. `gap_choice="nearest_618"` takes
        # the other reading — the one sitting closest to his golden ratio.
        if cfg.gap_choice == "nearest_618":
            score = -abs(mid - z_deep)
        else:
            score = g_hi - g_lo
        if best is None or score > best[0]:
            best = (score, k, g_lo, g_hi, mid)
    if best is None:
        return None
    _, k, g_lo, g_hi, mid = best

    entry = mid if cfg.entry_at_gap_midpoint else (g_lo if direction > 0 else g_hi)

    # ---- the stop, outside the candle that produced the gap --------------
    stop_from = cfg.stop_anchor
    if direction > 0:
        stop = float(lo[k + 1])
        if stop >= entry:
            stop = float(min(lo[k], lo[k + 1], lo[k + 2]))
            stop_from = "three_candles"
        if stop >= entry:
            return None
    else:
        stop = float(h[k + 1])
        if stop <= entry:
            stop = float(max(h[k], h[k + 1], h[k + 2]))
            stop_from = "three_candles"
        if stop <= entry:
            return None

    dist = abs(entry - stop)
    target = entry + direction * cfg.target_r * dist

    return Setup(
        pair=pair, session=session, direction=direction, kind=kind,
        choch_t=pd.Timestamp(t[i]), choch_i=i,
        broken_level=float(broken if broken is not None else np.nan),
        leg_low=leg_low, leg_high=leg_high,
        zone_deep=float(z_deep), zone_shallow=float(z_shallow),
        gap_lo=g_lo, gap_hi=g_hi, gap_mid_t=pd.Timestamp(t[k + 1]),
        entry=float(entry), stop=float(stop), target=float(target),
        stop_from=stop_from,
        # "waiting for a candle to close over this most recent swing up before
        # our entry" — the high the breaking move made, for a long.
        be_level=leg_high if direction > 0 else leg_low)


# =============================================================== THE TRADE
@dataclass
class Trade:
    pair: str
    session: str
    direction: int
    choch_t: pd.Timestamp
    entry_t: pd.Timestamp
    entry: float
    stop: float
    target: float
    stop_at_risk: float          # the ORIGINAL stop, kept when it moves to break even
    units: float
    notional: float
    risk_dollars: float
    equity_at_entry: float
    exit_t: pd.Timestamp | None = None
    exit: float | None = None
    outcome: str = ""
    pnl: float = 0.0             # net, after the round trip
    cost: float = 0.0
    r_multiple: float = 0.0
    mfe_r: float = 0.0           # furthest it ever went in our favour, in R
    moved_to_breakeven: bool = False
    stop_from: str = ""

    @property
    def stop_pct(self) -> float:
        return abs(self.entry - self.stop_at_risk) / self.entry

    @property
    def leverage(self) -> float:
        return self.notional / self.equity_at_entry if self.equity_at_entry else 0.0


def _size(cfg: CraigConfig, equity: float, entry: float, dist: float) -> dict:
    """THE ONE SIZING PATH. `tjr_bot.size_position` is, by its own docstring,
    "the one place in this project that turns a stop into a number of units",
    and every other book in the repo reaches it. This engine calls it directly
    rather than through `tjr_alerts.position_size`, for one reason stated
    plainly: that wrapper REFUSES to state a size for an instrument whose
    tightest stop has never been measured, and no such measurement exists for
    Craig's candle-anchored stop. Going through it would mean inventing the
    number it is refusing to invent. With `hold_size_still=False` — which is
    what the TJR book's shipping default (`size_per_trade=True`) produces —
    the wrapper adds nothing to the arithmetic anyway: units are
    risk_allowance / today's stop, and that is the line below.

    There is exactly one sizing path for a Craig trade and this is it.
    """
    allowance = cfg.risk_pct_per_trade * equity
    return size_position(
        account=equity, entry=entry, stop_distance=dist,
        risk_allowance=allowance,
        tightest_stop_pct=0.0,          # never measured, and never borrowed
        usd_per_quote=1.0,
        buying_power=(None if cfg.buying_power_multiple is None
                      else cfg.buying_power_multiple * equity),
        outer_allowance=allowance,      # per-trade sizing: its own share
        hold_size_still=False)


def manage(d: pd.DataFrame, s: Setup, cfg: CraigConfig,
           equity: float) -> Trade | None:
    """From the bar AFTER the change of character to the exit.

    Every decision is taken on a CLOSED candle. The resting entry is a limit at
    the gap midpoint: a candle whose range contains it fills it at it, a candle
    that opens beyond it fills at the open. When a single candle contains both
    the fill and the stop, the stop wins — the pessimistic reading, because the
    tape inside a 5-minute candle is not in the data and assuming the good
    ordering would be inventing a fill.
    """
    n = len(d)
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    t = d["t"].to_numpy()
    sh, sl = two_candle_swings(d)      # causal: stamped on the second candle
    dirn = s.direction
    dist = abs(s.entry - s.stop)
    if dist <= 0:
        return None

    # ---------------------------------------------------- the resting entry
    fill_i, fill_px = None, None
    last_look = min(n - 1, s.choch_i + cfg.entry_valid_bars)

    if cfg.entry_style == "market_on_signal":
        # NOT HIS. The candle after the signal, at its open — the first price a
        # live desk could actually have paid once the signal candle closed.
        j = s.choch_i + 1
        if j >= n:
            return None
        if (o[j] <= s.stop) if dirn > 0 else (o[j] >= s.stop):
            return None
        fill_i, fill_px = j, float(o[j])
    else:
        for i in range(s.choch_i + 1, last_look + 1):
            # THE SETUP CAN DIE BEFORE IT FILLS, and it dies at the stop. If
            # price trades beyond where the stop would sit while the entry is
            # still resting, the structure that produced the setup is already
            # broken and there is nothing left to buy. Checked BEFORE the fill
            # on every bar, which is also what stops a candle that opened
            # straight through the stop being recorded as a fill on the wrong
            # side of it.
            if (lo[i] <= s.stop) if dirn > 0 else (h[i] >= s.stop):
                return None
            if cfg.cancel_on_close_beyond_stop:
                if (c[i] < s.stop) if dirn > 0 else (c[i] > s.stop):
                    return None                # the structure is gone
            if dirn > 0:
                if o[i] <= s.entry:
                    fill_i, fill_px = i, float(o[i])
                elif lo[i] <= s.entry <= h[i]:
                    fill_i, fill_px = i, float(s.entry)
            else:
                if o[i] >= s.entry:
                    fill_i, fill_px = i, float(o[i])
                elif lo[i] <= s.entry <= h[i]:
                    fill_i, fill_px = i, float(s.entry)
            if fill_i is not None:
                break
        if fill_i is None:
            return None

    # THE PLAN IS RE-DRAWN OFF THE PRICE ACTUALLY PAID. A limit that fills at
    # the open because the candle opened past it is filled BETTER than planned,
    # which makes the real distance to the stop smaller than the planned one.
    # Sizing, the 1R and the target all come off what was paid, so "risk
    # exactly this much" stays true and the reward stays exactly 1:4 of the
    # risk actually taken.
    dist = abs(fill_px - s.stop)
    if dist <= 0:
        return None
    target = fill_px + dirn * cfg.target_r * dist

    size = _size(cfg, equity, fill_px, dist)
    if not size["ok"] or size["units"] <= 0:
        return None
    units = float(size["units"])

    tr = Trade(pair=s.pair, session=s.session, direction=dirn,
               choch_t=s.choch_t, entry_t=pd.Timestamp(t[fill_i]),
               entry=fill_px, stop=s.stop, target=target,
               stop_at_risk=s.stop, units=units, notional=units * fill_px,
               risk_dollars=float(size["risk_dollars"]),
               equity_at_entry=equity, stop_from=s.stop_from)

    # ------------------------------------------------------- the management
    deadline = tr.entry_t + pd.Timedelta(hours=cfg.max_hold_hours)
    stop = s.stop
    best = 0.0
    # the swing the break-even trigger watches, only if price is not already
    # past it at the fill
    be_ref = s.be_level if (
        (fill_px < s.be_level) if dirn > 0 else (fill_px > s.be_level)) else None
    for i in range(fill_i, n):
        ts = pd.Timestamp(t[i])
        fav = (h[i] - fill_px) if dirn > 0 else (fill_px - lo[i])
        best = max(best, fav / dist)

        hit_stop = (lo[i] <= stop) if dirn > 0 else (h[i] >= stop)
        # THE FILL BAR IS SCORED ONE-SIDED, ON PURPOSE. The candle we entered
        # inside also contains the price action BEFORE the entry, and its high
        # is very often made before the pullback that filled us. Reading a
        # target off that high would book wins the trade never had — it inflated
        # the share reaching 1:4 from 39% to 44% when it was left in. The stop
        # is still read on the fill bar, because assuming the good ordering
        # inside a candle is what invents money and assuming the bad one only
        # ever costs it.
        hit_tgt = (i > fill_i) and (
            (h[i] >= target) if dirn > 0 else (lo[i] <= target))

        if hit_stop:
            # pessimistic when a candle contains both
            px = stop
            why = "break even" if tr.moved_to_breakeven and \
                abs(stop - fill_px) < 1e-12 else "stopped out"
            return _close(tr, px, ts, why, dist, best, cfg)
        if hit_tgt:
            return _close(tr, target, ts, "target", dist, best, cfg)

        # HIS BREAK-EVEN. "waiting for a candle to close over this most recent
        # swing up before our entry ... reduce this risk all the way to break
        # even." Applied on the CLOSE, never a wick.
        #
        # THE SWING HAS TO BE ONE PRICE HAS NOT ALREADY PASSED. His own entry
        # is a pullback, so the high the move made sits above it and a close
        # over that high is a real advance. Entered at the signal instead, that
        # high is already underneath the fill, and reading the trigger off it
        # moved the stop to break even on the NEXT CANDLE — 59% of the year's
        # trades exited flat with a median hold of 18 minutes, which is not his
        # rule, it is a bug wearing his rule's name. When the level is already
        # behind us the trigger waits for the FIRST swing stamped after entry
        # that is genuinely in front of the fill.
        if cfg.breakeven_on_swing_close and not tr.moved_to_breakeven:
            if be_ref is not None and (
                    (c[i] > be_ref) if dirn > 0 else (c[i] < be_ref)):
                stop = fill_px
                tr.stop = fill_px
                tr.moved_to_breakeven = True
            elif be_ref is None:
                cand = sh[i] if dirn > 0 else sl[i]
                if not np.isnan(cand) and (
                        (cand > fill_px) if dirn > 0 else (cand < fill_px)):
                    be_ref = float(cand)

        if ts >= deadline:
            return _close(tr, float(c[i]), ts, "held to the cap", dist, best, cfg)

    return _close(tr, float(c[n - 1]), pd.Timestamp(t[n - 1]),
                  "still open when the record ran out", dist, best, cfg)


def _close(tr: Trade, px: float, ts, why: str, dist: float,
           best_r: float, cfg: CraigConfig) -> Trade:
    tr.exit, tr.exit_t, tr.outcome = float(px), pd.Timestamp(ts), why
    gross = tr.direction * (px - tr.entry) * tr.units
    tr.cost = cfg.round_trip_cost_pct * tr.units * tr.entry
    tr.pnl = gross - tr.cost
    tr.r_multiple = (tr.direction * (px - tr.entry)) / dist
    tr.mfe_r = best_r
    return tr


# ============================================================== THE REPLAY
def run_pair(pair: str, start, end, cfg: CraigConfig | None = None,
             data: dict | None = None, verbose: bool = False) -> dict:
    """Every session open in the window, in time order, one account.

    Sizing uses the equity as of the moment of entry, counting only trades that
    had already CLOSED by then. That is what a live account would have shown.
    """
    cfg = cfg or config_for(pair)
    data = data or load(pair)
    d = bars(data, cfg.entry_tf)
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    # one working frame, padded for context before and management after
    pad_before = pd.Timedelta(
        minutes=_TF_MINUTES[cfg.entry_tf] * cfg.context_bars * 3)
    pad_after = pd.Timedelta(hours=cfg.max_hold_hours + 6)
    w = d[(d["t"] >= start - pad_before) & (d["t"] <= end + pad_after)] \
        .reset_index(drop=True)
    if len(w) < 100:
        return {"pair": pair, "trades": [], "sessions": 0, "days": 0}
    tarr = w["t"].to_numpy()

    jobs = []
    for name in cfg.sessions:
        for ts in session_opens(start, end, name):
            if ts < start or ts > end + pd.Timedelta(days=1):
                continue
            jobs.append((ts, name))
    jobs.sort()

    setups = []
    for ts, name in jobs:
        i_open = int(np.searchsorted(tarr, np.datetime64(ts), "left"))
        i_end = int(np.searchsorted(
            tarr, np.datetime64(ts + pd.Timedelta(minutes=cfg.hunt_minutes)),
            "left")) - 1
        if i_open >= len(w) or i_end < i_open:
            continue
        i_ctx = max(0, i_open - cfg.context_bars)
        sub = w.iloc[i_ctx:i_end + 1].reset_index(drop=True)
        for s in find_setups(sub, i_open - i_ctx, i_end - i_ctx, cfg,
                             pair=pair, session=name):
            s.choch_i += i_ctx                     # back onto the working frame
            setups.append(s)

    setups.sort(key=lambda s: s.choch_t)
    trades, closed = [], []
    for s in setups:
        eq = cfg.account_start + sum(
            x.pnl for x in closed if x.exit_t is not None and x.exit_t <= s.choch_t)
        tr = manage(w, s, cfg, eq)
        if tr is None:
            continue
        trades.append(tr)
        closed.append(tr)
        closed.sort(key=lambda x: (x.exit_t or pd.Timestamp.max))

    account = cfg.account_start + sum(t.pnl for t in trades)
    days = len(pd.Series([pd.Timestamp(x).normalize()
                          for x in w["t"]]).unique())
    return {"pair": pair, "trades": trades, "setups": len(setups),
            "sessions": len(jobs), "account": account,
            "days": (pd.Timestamp(end) - pd.Timestamp(start)).days + 1,
            "config": cfg}


def run_book(pairs=None, start=None, end=None, cfg_over: dict | None = None,
             data_cache: dict | None = None, verbose: bool = True) -> dict:
    """Every pair on its OWN $100,000, which is the basis every crypto number
    in this project is quoted on. Five pairs is five accounts, not one."""
    out, cache = {}, (data_cache if data_cache is not None else {})
    for pair in (pairs or PAIRS):
        if pair not in cache:
            cache[pair] = load(pair)
        cfg = config_for(pair, **(cfg_over or {}))
        r = run_pair(pair, start, end, cfg=cfg, data=cache[pair])
        out[pair] = r
        if verbose:
            ts = r["trades"]
            net = sum(t.pnl for t in ts)
            wins = sum(1 for t in ts if t.pnl > 0)
            print(f"  {pair:9s} {len(ts):>4} trades  "
                  f"{(wins / len(ts) * 100 if ts else 0):>5.1f}% won  "
                  f"net ${net:>+11,.0f}")
    return out


# ======================================================== READING IT BACK
def frame(book: dict) -> pd.DataFrame:
    """One row per trade, in the words the report uses."""
    rows = []
    for pair, r in book.items():
        for t in r["trades"]:
            rows.append({
                "pair": pair, "session": t.session,
                "choch_t": t.choch_t, "entry_t": t.entry_t,
                "exit_t": t.exit_t,
                "side": "long" if t.direction > 0 else "short",
                "entry": t.entry, "stop": t.stop_at_risk, "target": t.target,
                "exit": t.exit, "outcome": t.outcome,
                "stop_move_in_price_pct": 100.0 * t.stop_pct,
                "leverage": t.leverage,
                "units": t.units, "notional": t.notional,
                "risk_dollars": t.risk_dollars,
                "pnl": t.pnl, "cost": t.cost, "r": t.r_multiple,
                "mfe_r": t.mfe_r, "moved_to_breakeven": t.moved_to_breakeven,
                "stop_from": t.stop_from,
                "hours_held": ((pd.Timestamp(t.exit_t) - pd.Timestamp(t.entry_t))
                               .total_seconds() / 3600.0
                               if t.exit_t is not None else np.nan),
            })
    return pd.DataFrame(rows)


def in_his_words() -> str:
    """Every choice this file made that he did not make, in one place, so the
    list is a decision and not an oversight."""
    return "\n".join([
        "OURS, NOT HIS — every decision the transcript does not contain:",
        "  1. THE CHART is the 5-minute. He never names one; his worked",
        "     examples are minutes-scale around the 09:30 open, and the",
        "     5-minute is the only chart we hold for all five coins to 2021.",
        "     Measured at 15m, 30m and 1h as well, and the answer matters.",
        "  2. A SWING POINT is an up candle then a down candle, level at the",
        "     higher wick (and the mirror for a low). He shows swings and",
        "     never defines them.",
        "  3. THE TREND IS A STATE THAT PERSISTS — down from the close below",
        "     a swing low until the close above a swing high. Read instead as",
        "     'two lower highs and two lower lows right now', the engine saw",
        "     no setup at all on 26 July's ETH run.",
        "  4. HE KEEPS LOOKING for 120 minutes from the open. He says he",
        "     trades 'about 2 hours a day'.",
        "  5. 60 CANDLES OF CONTEXT before the open, so a trend exists for the",
        "     change of character to be a change of.",
        "  6. CONTINUATION ENTRIES, not only the first change of character.",
        "     His step 1 says the first; he also says 'three to five per",
        "     session', and only continuations make both true.",
        "  7. WHICH GAP when several sit in the 50-61.8 zone: the largest, on",
        "     his own words that a gap is a pocket of momentum. The switch",
        "     'nearest_618' takes the other reading.",
        "  8. THE RESTING ENTRY lives 24 candles (2 hours) and is then",
        "     abandoned. He never says when he gives up on a limit.",
        "  9. A SETUP DIES if price reaches where its stop would be before it",
        "     fills. He never says this; it follows from where he puts the",
        "     stop.",
        " 10. BREAK EVEN watches a swing price has not already passed. His own",
        "     entry is a pullback so the swing is always in front of it; that",
        "     is not true of a market entry, and reading it off a level",
        "     already behind the fill flattened trades on the next candle.",
        " 11. A POSITION may be held 48 hours. He says nothing; crypto has no",
        "     bell and Wallace's rule is not to cut one.",
        " 12. ALL THREE SESSIONS run, not only New York. He trades New York;",
        "     on a 24/7 market the other two are his own list, they are",
        "     configurable, and every table here splits by session so the data",
        "     decides.",
        " 13. WHEN ONE CANDLE HOLDS BOTH the fill and the stop, the stop wins,",
        "     and the candle we entered inside may never book a target.",
        " 14. HOW SMALL A GAP IS STILL A GAP is a dial that ships at zero, so",
        "     the headline numbers are his rule unfiltered. Turning it up to a",
        "     full zone width moves the mean result per trade by 0.02R and the",
        "     dollars by nothing, so the tiny-gap tail is not what is wrong.",
        "",
        "NOT HIS AT ALL, and off by default:",
        "  * 'market on the signal' entry. His entry is a resting limit at the",
        "    fair value gap midpoint. The switch buys at the open of the next",
        "    candle instead, and exists only to put the cost of his patience",
        "    in dollars — on 26 July 2026 ETH his limit never filled on a",
        "    2.17% run and the market entry took two 1:4 winners.",
    ])


if __name__ == "__main__":
    print(__doc__)
    print(in_his_words())
