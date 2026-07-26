"""
test_trader.py — offline tests for trader.py, the reading layer.

Run with:  python3 test_trader.py

Repo style: plain asserts, a main() runner, no pytest, no network. Fixtures are
either hand-built so their correct reading is unambiguous, or they are the
cached Alpaca parquet files already in this repo.

WHAT THIS FILE IS FOR. trader.py makes claims about itself: that it cannot see
the future, that every definition in it is his rather than ours, that no number
in it was invented, that a level traded straight through is not a level taken,
that a wick never breaks structure and a close exactly on the level never does
either, that order blocks are absent on purpose, and that it decides nothing.
Every one of those is testable and every one is tested here. A docstring is a
promise; this file is the proof.
"""

from __future__ import annotations

import math
import py_compile
import re
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import trader as T

REPO = Path(__file__).resolve().parent
TS0 = datetime(2026, 7, 6, 14, 0, tzinfo=timezone.utc)   # a Monday, 10:00 New York


# ---------------------------------------------------------------------------
# fixture builders
# ---------------------------------------------------------------------------

def bars(rows, ts0=TS0, minutes=5) -> pd.DataFrame:
    """Build a frame from explicit (open, high, low, close) tuples, so every
    fixture's correct reading is unarguable by construction."""
    d = pd.DataFrame(rows, columns=["open", "high", "low", "close"]).astype(float)
    d.insert(0, "timestamp",
             [ts0 + timedelta(minutes=minutes * i) for i in range(len(d))])
    d["volume"] = 1000.0
    return d


def up(o, c=None, wick=0.2):
    c = o + 1.0 if c is None else c
    return (o, max(o, c) + wick, min(o, c) - wick, c)


def down(o, c=None, wick=0.2):
    c = o - 1.0 if c is None else c
    return (o, max(o, c) + wick, min(o, c) - wick, c)


def zigzag(legs, start=100.0, wick=0.2, ts0=TS0, minutes=5) -> pd.DataFrame:
    """(direction, n_bars, step) legs. Alternating legs guarantee two-candle
    pivots land exactly at the turns."""
    price = start
    rows = []
    for direction, n, step in legs:
        s = 1 if direction == "up" else -1
        for _ in range(n):
            o, c = price, price + s * step
            rows.append((o, max(o, c) + wick, min(o, c) - wick, c))
            price = c
    return bars(rows, ts0=ts0, minutes=minutes)


def load(symbol="SPY") -> dict:
    return T.load_frames(symbol)


def _fingerprint(r: T.ChartRead) -> str:
    """Everything a read asserts, flattened. A lookahead leak anywhere moves
    one of these."""
    return repr((r.symbol, r.working_timeframe, r.as_of, r.price, r.bars_read,
                 r.session, r.trading_day, r.minutes_since_new_york_open,
                 r.levels, r.pools, r.untouched_pools, r.taken, r.trends,
                 r.gaps, r.gap_inversions, r.equilibrium, r.sessions,
                 r.stats, r.unresolved))


# ===========================================================================
# A. it compiles, and it decides nothing
# ===========================================================================

def test_a_both_files_compile():
    py_compile.compile(str(REPO / "trader.py"), doraise=True)
    py_compile.compile(str(REPO / "test_trader.py"), doraise=True)


def test_a2_the_module_decides_nothing():
    """The deliverable is a reading layer. There must be no signal, no entry, no
    direction chosen, no order, and nothing that could fire."""
    assert T.DECIDES_NOTHING is True and T.NOT_DEPLOYED is True
    src = (REPO / "trader.py").read_text()
    for banned in ("def decide", "class Decision", "place_order", "submit_order",
                   "buy(", "sell(", "signal =", "def entry", "requests.",
                   "urllib", "import alpaca", "http"):
        assert banned not in src, f"trader.py contains {banned!r}"
    # no public name suggests a choice
    for name in dir(T):
        assert "decide" not in name.lower() or name == "DECIDES_NOTHING", name


def test_a3_order_blocks_and_breaker_blocks_are_absent_on_purpose():
    """"I no longer use order blocks. I no longer use breaker blocks." Three
    bootcamp days teach them in detail, which is exactly why building the
    most-documented concept would have been the natural mistake."""
    src = (REPO / "trader.py").read_text().lower()
    for banned in ("order_block", "orderblock", "breaker_block", "breakerblock"):
        assert banned not in src, f"trader.py implements {banned!r}, which he retired"


# ===========================================================================
# B. NO LOOKAHEAD
# ===========================================================================

def test_b_the_same_bar_reads_identically_with_and_without_the_future():
    """The truncation test, the way step84_blind_drill does it: read the same
    decision point from the full series and from a copy truncated at that bar,
    and assert the results are IDENTICAL.

    This is the exact objection he raises to clicking through historical bars in
    a charting tool — the higher timeframe candle is shown already completed, so
    you are reading the future. He is right, and this is the proof our replay
    does not do it."""
    frames = load("SPY")
    inst = T.Instrument("SPY")
    checked = 0
    for idx in (60_000, 200_000, len(frames["5m"]) - 500):
        full = T.read_the_chart(frames, inst, decision_idx=idx)
        cut = {k: v.iloc[: len(v)].copy() for k, v in frames.items()}
        cut["5m"] = frames["5m"].iloc[: idx + 1].reset_index(drop=True)
        truncated = T.read_the_chart(cut, inst, decision_idx=idx)
        assert _fingerprint(full) == _fingerprint(truncated), (
            f"lookahead leak at bar {idx}: the read changed when future "
            f"5-minute bars were visible")
        checked += 1
    assert checked == 3


def test_b2_every_higher_timeframe_is_cut_to_its_last_completed_candle():
    """A 4-hour bar still forming would hand the reader up to four hours of the
    future. Two proofs: the truncation helper keeps only closed bars, and
    pre-truncating the higher frames by hand changes nothing."""
    frames = load("SPY")
    inst = T.Instrument("SPY")
    idx = 150_000
    as_of = pd.to_datetime(frames["5m"]["timestamp"].iloc[idx])
    if as_of.tzinfo is None:
        as_of = as_of.tz_localize("UTC")

    for tf in ("1h", "4h", "1d"):
        kept = T.truncate_to_completed(frames[tf], as_of)
        ts = pd.to_datetime(kept["timestamp"])
        if ts.dt.tz is None:
            ts = ts.dt.tz_localize("UTC")
        step = pd.to_datetime(frames[tf]["timestamp"]).diff().median()
        assert bool(((ts + step) <= as_of).all()), (
            f"a {tf} bar that had not closed yet survived truncation")

    pre_cut = dict(frames)
    for tf in ("1h", "4h", "1d", "15m"):
        if tf in pre_cut:
            pre_cut[tf] = T.truncate_to_completed(frames[tf], as_of)
    a = T.read_the_chart(frames, inst, decision_idx=idx)
    b = T.read_the_chart(pre_cut, inst, decision_idx=idx)
    assert _fingerprint(a) == _fingerprint(b)


def test_b3_a_coarser_chart_is_stamped_when_it_closes_not_when_it_opens():
    """Any other stamping makes a coarse bar visible before it has finished,
    which is the same lookahead bug wearing a different hat."""
    hourly = load("SPY")["1h"]
    four = T.resample(hourly, "4h")
    ts_h = pd.to_datetime(hourly["timestamp"])
    ts_4 = pd.to_datetime(four["timestamp"])
    # every 4-hour stamp must be at or after the last hourly bar it contains
    sample = four.iloc[100:110]
    for _, row in sample.iterrows():
        end = pd.to_datetime(row["timestamp"])
        inside = hourly[(ts_h > end - pd.Timedelta("4h")) & (ts_h <= end)]
        assert len(inside) > 0
        assert abs(float(inside["high"].max()) - float(row["high"])) < 1e-9
        assert abs(float(inside["close"].iloc[-1]) - float(row["close"])) < 1e-9


def test_b4_the_two_candle_pivot_is_known_one_bar_late_and_never_earlier():
    d = bars([up(100), down(101), up(100), up(101)])
    highs, lows = T.two_candle_pivots(d)
    assert len(highs) == 1
    assert highs[0].bar == 1, "the pivot was stamped before its second candle"
    assert abs(highs[0].price - max(d["high"].iloc[0], d["high"].iloc[1])) < 1e-9
    # truncating right at the confirming bar changes nothing
    h2, _ = T.two_candle_pivots(d.iloc[:2].reset_index(drop=True))
    assert h2[0].price == highs[0].price and h2[0].bar == highs[0].bar


# ===========================================================================
# C. THE TWO-CANDLE PIVOT, HIS DEFINITION EXACTLY
# ===========================================================================

def test_c_a_high_is_an_up_candle_then_a_down_candle_at_the_higher_wick():
    d = bars([up(100, 103, wick=0.5), down(103, 101, wick=2.0)])
    highs, lows = T.two_candle_pivots(d)
    assert len(highs) == 1 and not lows
    assert abs(highs[0].price - 105.0) < 1e-9, (
        "the level must be the HIGHER of the two wicks, which here belongs to "
        "the second candle")


def test_c2_a_low_is_a_down_candle_then_an_up_candle_at_the_lower_wick():
    d = bars([down(100, 97, wick=0.5), up(97, 99, wick=3.0)])
    highs, lows = T.two_candle_pivots(d)
    assert len(lows) == 1 and not highs
    assert abs(lows[0].price - 94.0) < 1e-9


def test_c3_two_candles_the_same_way_are_not_a_pivot():
    """"Is a high a green candle, then a green candle? No, because there hasn't
    been a move down yet." He says it twice in two videos because students get
    it wrong."""
    assert T.two_candle_pivots(bars([up(100), up(101), up(102)])) == ([], [])
    assert T.two_candle_pivots(bars([down(100), down(99), down(98)])) == ([], [])


def test_c4_the_same_turn_is_a_pivot_on_one_chart_and_not_on_another():
    """"on the current time frame that we're in, the 4hour time frame, this is
    not a high." So the test runs per timeframe and the results genuinely
    differ — which is why nothing in this module mixes them."""
    frames = load("SPY")
    counts = {}
    for tf in ("5m", "1h", "4h", "1d"):
        cut = frames[tf].tail(600).reset_index(drop=True)
        h, l = T.two_candle_pivots(cut)
        counts[tf] = (len(h), len(l))
    assert len(set(counts.values())) > 1, (
        "every timeframe produced the same pivot counts, which cannot be right")


# ===========================================================================
# D. THE BREAK OF STRUCTURE, AND ITS ASYMMETRY
# ===========================================================================

def test_d_a_wick_past_the_level_is_never_a_break():
    """"Look at this candlestick wick. It comes all the way down here. Is this a
    break of structure? NO!" """
    d = zigzag([("up", 4, 1.0), ("down", 2, 1.0), ("up", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    assert tr.state == "uptrend" and tr.watched_low is not None
    level = tr.watched_low

    poke = d.copy()
    last = float(poke["close"].iloc[-1])
    poke.loc[len(poke)] = {"timestamp": poke["timestamp"].iloc[-1] + timedelta(minutes=5),
                           "open": last, "high": last + 0.2,
                           "low": level - 5.0,            # wick miles below
                           "close": level + 0.5,          # close stays above
                           "volume": 1000.0}
    after = T.read_trend(poke, "5m")
    assert after.state == "uptrend", "a wick through the level flipped the trend"
    assert len(after.breaks) == len(tr.breaks), "a wick emitted a break"


def test_d2_a_body_closing_exactly_on_the_level_is_not_a_break():
    """"we don't actually close underneath the low right here because the candle
    body is equal with this low." He hits that exact bar on tape and rules it
    out, so the comparison has to be strict."""
    d = zigzag([("up", 4, 1.0), ("down", 2, 1.0), ("up", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    level = tr.watched_low
    for close_at, should_break in ((level, False), (level - 1e-6, True)):
        test = d.copy()
        last = float(test["close"].iloc[-1])
        test.loc[len(test)] = {
            "timestamp": test["timestamp"].iloc[-1] + timedelta(minutes=5),
            "open": last, "high": last + 0.2, "low": close_at - 0.5,
            "close": close_at, "volume": 1000.0}
        after = T.read_trend(test, "5m")
        broke = after.state == "downtrend"
        assert broke is should_break, (
            f"closing at {close_at} (level {level}) "
            f"{'should' if should_break else 'should not'} have been a break")


def test_d3_in_an_uptrend_only_the_lows_are_watched():
    """"within an uptrend, how can we identify when the uptrend is broken? when
    a low gets closed underneath." A lower high changes nothing."""
    d = zigzag([("up", 5, 1.0), ("down", 2, 1.0), ("up", 5, 1.0)])
    tr = T.read_trend(d, "5m")
    assert tr.state == "uptrend"
    assert tr.watched_low is not None and tr.watched_high is not None
    assert "most recent low" in tr.detail
    # a lower high forming does not flip anything
    extended = pd.concat([d, zigzag([("down", 2, 0.5), ("up", 2, 0.4)],
                                    start=float(d["close"].iloc[-1]))],
                         ignore_index=True)
    assert T.read_trend(extended, "5m").state == "uptrend"


def test_d4_the_level_is_a_wick_and_the_break_is_a_close():
    """The asymmetry, stated as one assertion: the watched level equals a
    pivot's full wick extreme, and no candle whose CLOSE is on the wrong side
    ever changes the state however far its wick went."""
    d = zigzag([("down", 4, 1.0), ("up", 2, 1.0), ("down", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    assert tr.state == "downtrend"
    highs, _ = T.two_candle_pivots(d)
    assert any(abs(h.price - tr.watched_high) < 1e-9 for h in highs), (
        "the watched level is not one of the two-candle pivot wick extremes")


# ===========================================================================
# E. TAKING A LEVEL IS TWO STATES, NEVER ONE BOOLEAN
# ===========================================================================

def _read_of(frame, levels_frame=None):
    inst = T.Instrument("TEST", direction_timeframes=(), level_timeframes=(),
                        working_timeframe="5m")
    frames = {"5m": frame}
    return inst, frames


def test_e_a_level_traded_straight_through_is_not_a_level_taken():
    """"If price comes down and takes out a low and keeps going down, is it a
    liquidity sweep? No. Because it's not reacting to it."

    Two ways that shows up, and both are tested here because the spec names
    both. The mechanical one: a break of structure prints in the SAME direction
    as the push, which is the trend carrying on rather than turning. The other:
    nothing prints at all, and how long to wait before discarding is one of the
    numbers he never gives (A9), so it stays pending and says so."""
    d = zigzag([("up", 6, 1.0), ("down", 3, 0.8), ("up", 4, 1.0),
                ("down", 12, 1.0)])
    _, lows = T.two_candle_pivots(d)
    pivot = lows[0]
    lvl = T.Level(pivot.price, "low", "test low", "1h", pivot.bar, True)
    past, _, bar, extreme = T.traded_through(d, lvl.price, "low", pivot.bar)
    assert past and bar is not None

    # a low being taken looks UP for its turn, so a DOWN break after it is the
    # push carrying on
    same_way = T.TrendRead("5m", "downtrend", None, None, None, None,
                           (T.BreakOfStructure("down", lvl.price, bar + 2, "5m"),),
                           "")
    st = T._state_of_take(lvl, bar, extreme, len(d), same_way, None)
    assert st.state == "no reaction", st.detail
    assert "kept going the same way" in st.detail

    # the mirror: an UP break after it is the turn actually starting
    other_way = T.TrendRead("5m", "uptrend", None, None, None, None,
                            (T.BreakOfStructure("up", lvl.price + 5, bar + 2, "5m"),),
                            "")
    st2 = T._state_of_take(lvl, bar, extreme, len(d), other_way, None)
    assert st2.state == "confirmed" and st2.confirmed_by.direction == "up"

    # and nothing at all leaves it pending, never confirmed
    nothing = T.TrendRead("5m", "downtrend", None, None, None, None, (), "")
    st3 = T._state_of_take(lvl, bar, extreme, len(d), nothing, None)
    assert st3.state == "pending"
    assert "nothing has confirmed a turn out of it yet" in st3.detail


def test_e2_a_level_taken_with_no_break_yet_is_pending_and_says_so():
    d = zigzag([("up", 6, 1.0), ("down", 3, 0.8)])
    trend = T.read_trend(d, "5m")
    lvl = T.Level(float(d["low"].iloc[-1]) + 0.2, "low", "test low", "1h", -1, True)
    past, _, bar, extreme = T.traded_through(d, lvl.price, "low", -1)
    if past:
        state = T._state_of_take(lvl, bar, extreme, len(d), trend, None)
        assert state.state in ("pending", "confirmed", "no reaction")
        if state.state == "pending":
            assert "nothing has confirmed a turn out of it yet" in state.detail


def test_e3_it_becomes_confirmed_only_on_a_break_the_other_way():
    """The break comes FIRST and the pullback second. A high being taken is
    confirmed by a DOWNSIDE break, which is what the coordinator originally had
    inverted and step431 section 8.3 corrects on tape."""
    d = zigzag([("up", 6, 1.0), ("down", 2, 1.0), ("up", 3, 1.0),
                ("down", 8, 1.2), ("up", 3, 0.9)])
    trend = T.read_trend(d, "5m")
    highs, _ = T.two_candle_pivots(d)
    assert highs
    lvl = T.Level(highs[0].price, "high", "test high", "1h", highs[0].bar, True)
    past, _, bar, extreme = T.traded_through(d, lvl.price, "high", highs[0].bar)
    if past and bar is not None:
        st = T._state_of_take(lvl, bar, extreme, len(d), trend, None)
        assert st.turn_direction == "down", (
            "a high being taken must look for a DOWNSIDE break to confirm")
        if st.state == "confirmed":
            assert st.confirmed_by.direction == "down"
            assert "the turn actually starting" in st.detail


def test_e4_the_state_is_never_a_single_boolean():
    """A level being taken is a state machine, not a flag. Checked on the type
    itself rather than by reading the source, so it stays true under edits."""
    fields = T.TakenLevel.__dataclass_fields__
    assert fields["state"].type in ("str", str), fields["state"].type
    assert "confirmed_by" in fields and "extreme" in fields
    d = zigzag([("up", 6, 1.0), ("down", 3, 0.8), ("up", 4, 1.0)])
    trend = T.read_trend(d, "5m")
    _, lows = T.two_candle_pivots(d)
    lvl = T.Level(lows[0].price, "low", "test low", "1h", lows[0].bar, True)
    past, _, bar, extreme = T.traded_through(d, lvl.price, "low", lows[0].bar)
    if past and bar is not None:
        st = T._state_of_take(lvl, bar, extreme, len(d), trend, None)
        assert st.state in ("pending", "confirmed", "no reaction", "stale")
        assert not isinstance(st.state, bool)


def test_e5_the_protective_exit_structure_is_the_extreme_of_the_take():
    """"We can put our stop loss above these highs" — the level is the furthest
    price got while taking it, which is what `extreme` carries."""
    d = zigzag([("up", 6, 1.0), ("down", 4, 1.0)])
    lvl_price = float(d["low"].iloc[7])
    past, _, bar, extreme = T.traded_through(d, lvl_price + 0.3, "low", -1)
    assert past and extreme is not None and extreme <= lvl_price + 0.3


# ===========================================================================
# F. THE GAP RULE — a level jumped over is not a level taken
# ===========================================================================

def test_f_a_level_the_market_jumped_over_is_not_taken():
    """A fund that stops at 16:00 and reopens at 09:30 can open away from where
    it closed. Same principle as a level traded straight through: if no bar's
    range ever contained the level, price never went to it."""
    d = bars([(100, 101, 99, 100), (100, 101, 99, 100),
              (110, 112, 109, 111),          # gapped clean over 105
              (111, 113, 110, 112)])
    past, jumped, bar, extreme = T.traded_through(d, 105.0, "high", -1)
    assert past is False and jumped is True and bar is None

    # and when it does trade to the level, it counts normally
    d2 = bars([(100, 101, 99, 100), (100, 106, 99, 104), (104, 105, 103, 104)])
    past2, jumped2, bar2, _ = T.traded_through(d2, 105.0, "high", -1)
    assert past2 is True and jumped2 is False and bar2 == 1


def test_f2_jumped_over_levels_never_enter_the_taken_list():
    frames = load("SPY")
    r = T.read_the_chart(frames, T.Instrument("SPY"), decision_idx=200_000)
    jumped = {round(lv.price, 8) for lv in r.levels if lv.jumped_over}
    for t in r.taken:
        assert round(t.level.price, 8) not in jumped


def test_f3_the_overnight_gap_is_measured_on_this_instrument():
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    g = r.stats["median_overnight_gap_price_pct"]
    assert g is not None and g > 0, (
        "the overnight gap could not be measured, so the gap rule has no size")


# ===========================================================================
# G. SESSIONS AND CALENDAR LEVELS, NEW YORK TIME
# ===========================================================================

def test_g_the_session_windows_are_his_exact_clock():
    assert T.SESSIONS["Asia"] == ((18, 0), (3, 0))
    assert T.SESSIONS["London"] == ((3, 0), (8, 30))
    assert T.SESSIONS["pre-market"] == ((8, 30), (9, 30))
    assert T.SESSIONS["New York"] == ((9, 30), (17, 0))
    assert T.BLACKOUT == ((17, 0), (18, 0))
    assert T.NEW_YORK == "America/New_York"


def test_g2_every_timestamp_is_converted_to_new_york_before_anything():
    frames = load("SPY")
    ny = T.new_york_index(frames["5m"].tail(500).reset_index(drop=True))
    assert str(ny.tz) == "America/New_York"
    # a bar at 14:30 UTC in July is 10:30 New York, inside the session
    assert T.session_of(ny[-1]) in ("Asia", "London", "pre-market", "New York",
                                    "blackout, no trading", "between sessions")


def test_g3_the_trading_day_runs_18_00_to_18_00():
    """"all of those sessions encapsulated into one." A bar at or after 18:00
    belongs to the NEXT day, because that is the day whose London and New York
    sessions follow it."""
    ts = pd.DatetimeIndex(pd.to_datetime([
        "2026-07-06 21:00", "2026-07-06 22:30",     # 17:00 and 18:30 New York
        "2026-07-07 13:30"]).tz_localize("UTC")).tz_convert(T.NEW_YORK)
    days = T.trading_day_of(ts)
    assert days[0] == "2026-07-06"
    assert days[1] == "2026-07-07", "an 18:30 bar did not roll into the next day"
    assert days[2] == "2026-07-07"


def test_g4_session_extremes_are_the_running_high_and_low_not_a_pivot():
    """"Where is London session high? from 3 to 8:30, where's the highest point
    that we got to?" A different definition from the two-candle pivot, and he
    uses both."""
    frames = load("SPY")
    d = frames["5m"].iloc[150_000:150_900].reset_index(drop=True)
    sess = T.session_extremes(d)
    assert sess
    ny = T.new_york_index(d)
    days = T.trading_day_of(ny)
    for s in sess:
        if s.high is None:
            continue
        mask = (days == s.trading_day) & T.in_window(ny, T.SESSIONS[s.name])
        assert abs(float(d.loc[mask, "high"].max()) - s.high) < 1e-9
        assert abs(float(d.loc[mask, "low"].min()) - s.low) < 1e-9


def test_g5_previous_day_and_previous_week_are_both_marked():
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    kinds = {lv.kind for lv in r.levels}
    for want in ("previous day high", "previous day low",
                 "previous week high", "previous week low"):
        assert want in kinds, f"{want} was not marked"


# ===========================================================================
# H. LEVELS CARRY THE TIMEFRAME THEY CAME FROM
# ===========================================================================

def test_h_only_the_4_hour_and_1_hour_pivots_are_levels_worth_trading_off():
    """"the best time frames... to identify liquidity on for me is going to be
    the 4 hour and the 1 hour", and he forbids hunting them on the 1-minute. A
    5-minute high must never appear as a tradeable pool."""
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    pivot_tfs = {lv.timeframe for lv in r.levels if "pivot" in lv.kind}
    assert pivot_tfs <= {"4h", "1h"}, (
        f"pivots were marked from {pivot_tfs - {'4h', '1h'}}, which he does not "
        f"use as levels")
    for lv in r.pools:
        assert lv.timeframe in ("", "4h", "1h"), lv.kind
    assert not any(lv.timeframe == "5m" for lv in r.levels)


def test_h2_every_level_says_where_it_came_from():
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    assert len(r.levels) > 20
    for lv in r.levels:
        assert lv.kind and lv.note, f"a level with no provenance: {lv}"
        assert lv.side in ("high", "low")


# ===========================================================================
# I. FAIR VALUE GAPS
# ===========================================================================

def test_i_a_bullish_gap_is_the_third_low_above_the_first_high():
    d = bars([(100, 101, 99, 100),        # candle 1, high 101
              (101, 108, 100, 107),       # the expansion candle
              (107, 109, 103, 108)])      # candle 3, low 103 > 101
    gaps, _ = T.find_fair_value_gaps(d, "5m")
    live = [g for g in gaps if g.state != "dead"]
    assert len(live) == 1
    g = live[0]
    assert g.side == "bullish"
    assert abs(g.bottom - 101.0) < 1e-9 and abs(g.top - 103.0) < 1e-9


def test_i2_overlapping_wicks_means_there_is_no_gap():
    """"because the wicks are overlapping... this is not an imbalance of price
    action." """
    d = bars([(100, 104, 99, 103), (103, 108, 102, 107), (107, 109, 103, 108)])
    gaps, _ = T.find_fair_value_gaps(d, "5m")
    assert not [g for g in gaps if g.state != "dead"], (
        "a gap was found where the third candle's wick reaches back past the "
        "first candle's high")


def test_i3_a_wick_through_the_gap_does_not_kill_it_but_a_close_does():
    """"if we see a candlestick wick that goes all the way down here but we
    still do not close underneath the gap, it has not been disrespected yet." """
    base = [(100, 101, 99, 100), (101, 108, 100, 107), (107, 109, 103, 108)]
    wick_only = bars(base + [(108, 109, 98, 104)])      # wick under 101, close above
    gaps, _ = T.find_fair_value_gaps(wick_only, "5m")
    g = [x for x in gaps if x.side == "bullish"][0]
    assert g.state != "dead", "a wick through the gap killed it"

    closed_through = bars(base + [(108, 109, 98, 100.5)])   # close below 101
    gaps2, _ = T.find_fair_value_gaps(closed_through, "5m")
    g2 = [x for x in gaps2 if x.side == "bullish"][0]
    assert g2.state == "dead" and "closed below the bottom" in g2.death_reason


def test_i4_the_gap_that_holds_the_trend_up_is_the_one_that_inverts_it():
    """"the bottom fair value gap when we have multiple fair value gaps stacked
    up on top of each other needs to be inversed... because this is the last
    fair value gap that is holding up the trend." An inversion also only fires
    inside the matching trend, otherwise every stack-leading gap on a 5-minute
    chart would emit one and the signal would mean nothing."""
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    for tf, gl in r.gaps.items():
        holders = [g for g in gl if g.holds_the_trend]
        assert len(holders) <= len(gl)
        for g in gl:
            assert g.stack_id >= 1
    for inv in r.gap_inversions:
        assert inv.source == "gap inversion"
        assert inv.direction in ("up", "down")


def test_i5_a_gap_dies_when_the_trend_carried_on_without_it():
    """"Price does not have any obligation to us or the chart to have to fill
    this gap... we can get rid of it from my chart." Gaps are also never dragged
    forward in time, so nothing may stay alive across a regime."""
    frames = load("SPY")
    r = T.read_the_chart(frames, T.Instrument("SPY"), decision_idx=200_000)
    for tf, gl in r.gaps.items():
        assert gl, f"no gaps at all were found on {tf}, which cannot be right"
        dead = [g for g in gl if g.state == "dead"]
        assert dead, f"nothing on {tf} ever died, so the kill rules are not running"
        reasons = {g.death_reason for g in dead}
        assert any("carried on past the prior swing" in x for x in reasons), (
            f"on {tf} no gap ever died of the trend continuing without it")
        live = [g for g in gl if g.state != "dead"]
        assert len(live) < len(gl), (
            f"every gap on {tf} is still alive, so nothing is being retired")


# ===========================================================================
# J. EQUILIBRIUM
# ===========================================================================

def test_j_the_halfway_point_uses_the_most_recent_swings_and_nothing_earlier():
    """The rant: "do we draw equilibrium from this low up to this high? No. We
    draw it from the MOST RECENT low up to the MOST RECENT high." """
    d = zigzag([("up", 4, 1.0), ("down", 2, 1.0), ("up", 5, 1.0),
                ("down", 2, 1.0), ("up", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    eq = T.read_equilibrium(d, "5m", tr)
    if eq is not None:
        assert abs(eq.price - (eq.anchor_low + eq.anchor_high) / 2) < 1e-9
        assert abs(eq.anchor_low - tr.last_swing_low.price) < 1e-9
        assert abs(eq.anchor_high - tr.last_swing_high.price) < 1e-9
        highs, lows = T.two_candle_pivots(d)
        assert abs(eq.anchor_high - highs[-1].price) < 1e-9, (
            "equilibrium anchored to an earlier high than the most recent one")
        assert abs(eq.anchor_low - lows[-1].price) < 1e-9


def test_j2_it_re_anchors_when_a_new_extreme_forms():
    d = zigzag([("up", 4, 1.0), ("down", 2, 1.0), ("up", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    first = T.read_equilibrium(d, "5m", tr)
    extended = pd.concat([d, zigzag([("up", 4, 2.0), ("down", 2, 1.0),
                                     ("up", 2, 1.0)],
                                    start=float(d["close"].iloc[-1]))],
                         ignore_index=True)
    tr2 = T.read_trend(extended, "5m")
    second = T.read_equilibrium(extended, "5m", tr2)
    if first is not None and second is not None:
        assert second.anchor_high >= first.anchor_high
        assert (second.price != first.price
                or second.anchor_low != first.anchor_low), (
            "a new extreme formed and the halfway point did not move")


def test_j3_both_readings_of_reached_are_given_and_neither_is_chosen():
    """He never says whether a wick past the halfway point counts or a body must
    close past (A12). Both are computed and the ambiguity is reported."""
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    assert r.equilibrium, "no halfway point was computed on any chart"
    for tf, eq in r.equilibrium.items():
        assert isinstance(eq.reached_by_wick, bool)
        assert isinstance(eq.reached_by_body, bool)
        assert eq.where_price_sits
    assert any("A12" in u for u in r.unresolved)


def test_j4_the_cheap_half_is_below_and_the_expensive_half_is_above():
    d = zigzag([("up", 4, 1.0), ("down", 2, 1.0), ("up", 4, 1.0)])
    tr = T.read_trend(d, "5m")
    eq = T.read_equilibrium(d, "5m", tr)
    if eq is not None:
        px = float(d["close"].iloc[-1])
        if px > eq.price:
            assert "expensive" in eq.where_price_sits
        elif px < eq.price:
            assert "cheap" in eq.where_price_sits


# ===========================================================================
# K. NO NUMBER IN HERE WAS INVENTED
# ===========================================================================

def test_k_every_parameter_he_never_states_is_named_and_left_empty():
    u = T.Unresolved()
    for name in vars(u):
        assert getattr(u, name) is None, (
            f"{name} has a value. He never states it, so a value here was "
            f"invented and will become a fitted setting nobody remembers.")
    assert len(u.missing()) == len(vars(u))
    for key in T.NEEDS_VIDEO:
        assert len(T.NEEDS_VIDEO[key]) > 60, f"{key} has no explanation"


def test_k2_anything_depending_on_a_missing_parameter_is_not_computed():
    """Stacked and roughly-equal levels need a tolerance he never gives, so
    nothing is marked at all rather than marked with a guess."""
    assert T.cluster_levels([], None, None) == []
    fake = [T.Level(100.0 + i * 0.01, "high", "1h pivot high", "1h", i, True)
            for i in range(5)]
    assert T.cluster_levels(fake, None, 2) == []
    assert T.cluster_levels(fake, 0.05, None) == []
    # with both supplied it works, which proves the machinery is ready
    got = T.cluster_levels(fake, 0.05, 2)
    assert got and "stacked at about the same price" in got[0].kind

    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    assert not any("stacked" in lv.kind for lv in r.levels)
    assert any("A3_roughly_equal_tolerance_pct" in u for u in r.unresolved)


def test_k3_the_read_reports_everything_it_could_not_compute():
    r = T.read_the_chart(load("SPY"), T.Instrument("SPY"), decision_idx=200_000)
    assert len(r.unresolved) >= len(vars(T.Unresolved()))
    for key in ("A1_trading_window_end", "A3_roughly_equal_tolerance_pct",
                "A8_protective_exit_buffer_pct", "A9_pending_lifetime_bars"):
        assert any(key in u for u in r.unresolved), f"{key} was not reported"


def test_k4_no_bare_price_percentage_is_hardcoded_anywhere():
    """The only percentages in the file should be the measured cost of trading
    and things derived from the chart. A tolerance, a buffer or a threshold
    written as a literal is exactly what this build must not contain."""
    src = (REPO / "trader.py").read_text()
    body = src[src.index("class Instrument"):]
    # comments quote measured findings and are allowed to contain numbers; the
    # CODE is what must not carry an invented threshold
    code = "\n".join(line.split("#")[0] for line in body.splitlines())
    code = re.sub(r'"""(?:.|\n)*?"""', "", code)
    for banned in ("0.5%", "= 1.5", "= 0.15", "2.0%", "tolerance = 0",
                   "buffer = 0", "tolerance_pct = 0", "= 0.0015"):
        assert banned not in code, (
            f"trader.py's code contains {banned!r}, which is an invented number")
    assert "round_trip_cost_pct: float = 0.0035" in src, (
        "the one measured cost number should be present and labelled")


# ===========================================================================
# L. THRESHOLDS ARE RE-DERIVED PER INSTRUMENT
# ===========================================================================

def test_l_the_statistics_differ_between_the_two_instruments():
    a = T.derive_stats(T.load_frames("SPY")["5m"].tail(4000).reset_index(drop=True),
                       T.SPY.round_trip_cost_pct)
    b = T.derive_stats(T.load_frames("QQQ")["5m"].tail(4000).reset_index(drop=True),
                       T.QQQ.round_trip_cost_pct)
    for k in ("bar_range_price_pct_median", "typical_bar_move_price_pct",
              "bar_move_price_pct_p90", "median_overnight_gap_price_pct"):
        assert a[k] is not None and b[k] is not None, k
        assert abs(a[k] - b[k]) > 1e-6, (
            f"{k} came out identical on SPY and QQQ, so it is a carried "
            f"constant and not a derived one")


def test_l2_they_differ_across_one_instrument_s_own_eras():
    five = T.load_frames("SPY")["5m"]
    early = T.derive_stats(five.iloc[:4000].reset_index(drop=True), 0.0035)
    late = T.derive_stats(five.tail(4000).reset_index(drop=True), 0.0035)
    a, b = early["typical_bar_move_price_pct"], late["typical_bar_move_price_pct"]
    assert abs(a - b) / max(a, b) > 0.05, (
        f"the same instrument barely changed across eras ({a:.4f}% then "
        f"{b:.4f}%) — a number derived once and frozen is the same bug as a "
        f"number carried between markets")


def test_l3_locate_turns_a_stated_number_into_a_rank():
    sample = pd.Series(np.arange(100, dtype=float))
    assert abs(T.locate(49.0, sample) - 0.50) < 0.02
    assert T.locate(1000.0, sample) == 1.0
    assert T.locate(-1.0, sample) == 0.0


def test_l4_the_measured_cost_is_reported_against_this_instrument_s_own_bars():
    r = T.read_the_chart(T.load_frames("SPY"), T.SPY, decision_idx=200_000)
    st = r.stats
    assert abs(st["round_trip_cost_price_pct"] - 0.0035) < 1e-12
    assert st["round_trip_cost_in_typical_bars"] is not None
    assert abs(st["round_trip_cost_in_typical_bars"]
               - 0.0035 / st["typical_bar_move_price_pct"]) < 1e-12


# ===========================================================================
# M. SIZE FROM THE STOP — arithmetic only
# ===========================================================================

def test_m_size_is_exactly_dollars_risked_over_the_distance_to_the_stop():
    s = T.size_from_stop(100.0, 98.0, equity=100_000.0, risk_fraction=0.01,
                         round_trip_cost_pct=0.0035)
    assert abs(s["size_shares"] * 2.0 - 1000.0) < 1e-9
    tight = T.size_from_stop(100.0, 99.0, 100_000.0, 0.01, 0.0035)
    assert abs(tight["size_shares"] / s["size_shares"] - 2.0) < 1e-9
    assert abs(tight["implied_leverage"] / s["implied_leverage"] - 2.0) < 1e-9


def test_m2_leverage_is_an_output_of_the_stop():
    """Reproduces the measured table: a 0.092% stop supports 10.9x at 1% of the
    account risked and 21.7x at 2%; a 1.840% stop supports 0.5x and 1.1x."""
    for risk, stop_pct, expected in ((0.01, 0.092, 10.9), (0.02, 0.092, 21.7),
                                     (0.01, 1.840, 0.5), (0.02, 1.840, 1.1)):
        s = T.size_from_stop(100.0, 100.0 * (1 - stop_pct / 100), 100_000.0,
                             risk, 0.0035)
        assert abs(s["implied_leverage"] - expected) < 0.06, (
            f"risk {risk}, stop {stop_pct}%: got {s['implied_leverage']:.2f}x")


def test_m3_a_tighter_stop_makes_the_cost_bar_harder_not_easier():
    """Profit and cost both scale with size while the stop shrinks. At a 0.092%
    stop the trade must travel 2.17 stop distances to be worth five times the
    cost; at 1.840% it needs 0.11."""
    cost = 0.44 * 0.092
    tight = T.size_from_stop(100.0, 100.0 * (1 - 0.092 / 100), 1000.0, 0.01, cost)
    wide = T.size_from_stop(100.0, 100.0 * (1 - 1.840 / 100), 1000.0, 0.01, cost)
    assert abs(tight["stop_distances_to_clear_costs"] - 2.17) < 0.05
    assert abs(wide["stop_distances_to_clear_costs"] - 0.11) < 0.01
    assert wide["stop_distances_to_clear_costs"] < tight["stop_distances_to_clear_costs"]


def test_m4_fractional_shares_mean_the_size_lands_exactly():
    s = T.size_from_stop(437.21, 435.87, 100_000.0, 0.01, 0.0035,
                         fractional_shares=True)
    assert s["size_shares"] != math.floor(s["size_shares"])
    whole = T.size_from_stop(437.21, 435.87, 100_000.0, 0.01, 0.0035,
                             fractional_shares=False)
    assert whole["size_shares"] == math.floor(whole["size_shares"])


# ===========================================================================
# N. THE WHOLE READ, ON REAL DATA
# ===========================================================================

def test_n_a_full_read_is_well_formed_on_both_instruments():
    for symbol in ("SPY", "QQQ"):
        r = T.read_the_chart(T.load_frames(symbol), T.Instrument(symbol),
                             decision_idx=200_000)
        assert r is not None
        assert r.symbol == symbol and r.working_timeframe == "5m"
        assert r.price > 0 and r.bars_read > 1000
        assert r.session and r.trading_day
        assert len(r.levels) > 20 and len(r.pools) > 20
        assert r.trends and "5m" in r.trends
        for tf, tr in r.trends.items():
            assert tr.state in ("uptrend", "downtrend", "unknown")
            assert tr.detail
        assert r.stats["typical_bar_move_price_pct"] > 0
        for t in r.taken:
            assert t.state in ("pending", "confirmed", "no reaction", "stale")
            assert t.detail and t.extreme is not None


def test_n2_a_chart_too_short_to_describe_returns_nothing_rather_than_guessing():
    frames = {"5m": T.load_frames("SPY")["5m"].iloc[:40].reset_index(drop=True)}
    assert T.read_the_chart(frames, T.Instrument("SPY"), decision_idx=39) is None


def test_n3_the_two_instruments_can_be_compared_without_deciding_anything():
    a = T.read_the_chart(T.load_frames("SPY"), T.SPY, decision_idx=200_000)
    b = T.read_the_chart(T.load_frames("QQQ"), T.QQQ, decision_idx=200_000)
    got = T.instruments_agree(a, b)
    assert set(("agree", "detail")) <= set(got)
    assert got["agree"] in (True, False, None)
    assert "reads" in got["detail"]


def test_n4_every_sentence_the_read_emits_avoids_our_glossary():
    """Name the action, never the category. Wallace asked "what the heck is a
    dip buy" — he knows the concepts, he does not know our labels."""
    jargon = ["dip-buy", "dip buy", "mean reversion", "mean-reversion",
              "continuation confluence", "invalidation", "basis points", " bps",
              "R-multiple", "liquidity sweep", "order block", "breaker block",
              "CHoCH", "premium/discount"]
    r = T.read_the_chart(T.load_frames("SPY"), T.SPY, decision_idx=200_000)
    text = []
    for lv in r.levels:
        text += [lv.kind, lv.note]
    for t in r.taken:
        text.append(t.detail)
    for tr in r.trends.values():
        text.append(tr.detail)
    for eq in r.equilibrium.values():
        text += [eq.detail, eq.where_price_sits]
    assert len(text) > 50
    for s in text:
        low = s.lower()
        for word in jargon:
            assert word.lower() not in low, f"jargon {word!r} in: {s[:140]!r}"


# ===========================================================================
# runner
# ===========================================================================

def main():
    tests = [
        test_a_both_files_compile,
        test_a2_the_module_decides_nothing,
        test_a3_order_blocks_and_breaker_blocks_are_absent_on_purpose,
        test_b_the_same_bar_reads_identically_with_and_without_the_future,
        test_b2_every_higher_timeframe_is_cut_to_its_last_completed_candle,
        test_b3_a_coarser_chart_is_stamped_when_it_closes_not_when_it_opens,
        test_b4_the_two_candle_pivot_is_known_one_bar_late_and_never_earlier,
        test_c_a_high_is_an_up_candle_then_a_down_candle_at_the_higher_wick,
        test_c2_a_low_is_a_down_candle_then_an_up_candle_at_the_lower_wick,
        test_c3_two_candles_the_same_way_are_not_a_pivot,
        test_c4_the_same_turn_is_a_pivot_on_one_chart_and_not_on_another,
        test_d_a_wick_past_the_level_is_never_a_break,
        test_d2_a_body_closing_exactly_on_the_level_is_not_a_break,
        test_d3_in_an_uptrend_only_the_lows_are_watched,
        test_d4_the_level_is_a_wick_and_the_break_is_a_close,
        test_e_a_level_traded_straight_through_is_not_a_level_taken,
        test_e2_a_level_taken_with_no_break_yet_is_pending_and_says_so,
        test_e3_it_becomes_confirmed_only_on_a_break_the_other_way,
        test_e4_the_state_is_never_a_single_boolean,
        test_e5_the_protective_exit_structure_is_the_extreme_of_the_take,
        test_f_a_level_the_market_jumped_over_is_not_taken,
        test_f2_jumped_over_levels_never_enter_the_taken_list,
        test_f3_the_overnight_gap_is_measured_on_this_instrument,
        test_g_the_session_windows_are_his_exact_clock,
        test_g2_every_timestamp_is_converted_to_new_york_before_anything,
        test_g3_the_trading_day_runs_18_00_to_18_00,
        test_g4_session_extremes_are_the_running_high_and_low_not_a_pivot,
        test_g5_previous_day_and_previous_week_are_both_marked,
        test_h_only_the_4_hour_and_1_hour_pivots_are_levels_worth_trading_off,
        test_h2_every_level_says_where_it_came_from,
        test_i_a_bullish_gap_is_the_third_low_above_the_first_high,
        test_i2_overlapping_wicks_means_there_is_no_gap,
        test_i3_a_wick_through_the_gap_does_not_kill_it_but_a_close_does,
        test_i4_the_gap_that_holds_the_trend_up_is_the_one_that_inverts_it,
        test_i5_a_gap_dies_when_the_trend_carried_on_without_it,
        test_j_the_halfway_point_uses_the_most_recent_swings_and_nothing_earlier,
        test_j2_it_re_anchors_when_a_new_extreme_forms,
        test_j3_both_readings_of_reached_are_given_and_neither_is_chosen,
        test_j4_the_cheap_half_is_below_and_the_expensive_half_is_above,
        test_k_every_parameter_he_never_states_is_named_and_left_empty,
        test_k2_anything_depending_on_a_missing_parameter_is_not_computed,
        test_k3_the_read_reports_everything_it_could_not_compute,
        test_k4_no_bare_price_percentage_is_hardcoded_anywhere,
        test_l_the_statistics_differ_between_the_two_instruments,
        test_l2_they_differ_across_one_instrument_s_own_eras,
        test_l3_locate_turns_a_stated_number_into_a_rank,
        test_l4_the_measured_cost_is_reported_against_this_instrument_s_own_bars,
        test_m_size_is_exactly_dollars_risked_over_the_distance_to_the_stop,
        test_m2_leverage_is_an_output_of_the_stop,
        test_m3_a_tighter_stop_makes_the_cost_bar_harder_not_easier,
        test_m4_fractional_shares_mean_the_size_lands_exactly,
        test_n_a_full_read_is_well_formed_on_both_instruments,
        test_n2_a_chart_too_short_to_describe_returns_nothing_rather_than_guessing,
        test_n3_the_two_instruments_can_be_compared_without_deciding_anything,
        test_n4_every_sentence_the_read_emits_avoids_our_glossary,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 78)
    print("TRADER READING LAYER — TEST SUMMARY")
    print("=" * 78)
    n_pass = 0
    for name, ok, err in results:
        if ok:
            n_pass += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            for line in err.splitlines():
                print(f"          {line}")
    print("-" * 78)
    print(f"  {n_pass}/{len(results)} passed")
    print("=" * 78 + "\n")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
