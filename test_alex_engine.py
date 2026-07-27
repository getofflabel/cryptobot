#!/usr/bin/env python3
"""test_alex_engine.py — the Alex Gonzalez engine, held to the desk's standard.

SIX THINGS ARE PROVED HERE

  1. CAUSALITY. Every setup the engine stamps on real tape is re-derived with
     every candle after its own confirmation DELETED, on every timeframe at
     once, and must come out identical. Higher timeframes stay invisible until
     they close. This is the truncation pattern ported from the TJR suite and
     it is the only thing standing between a measured edge and a lookahead
     artefact.

  2. HIS RULES ARE THE RULES. Three touches minimum, body close only, the
     confirmation is a rejection / engulfing / star, the stop is at structure,
     the target is 1:2 of the risk actually taken, entries only 01:00-10:30
     New York, no Sunday, nothing after Thursday 09:00.

  3. THERE IS NO BREAK EVEN, NO PARTIAL, NO TRAIL, AND NO CLOCK ON THE EXIT.
     "I am not a break even trader." Proved by reading the management code,
     not by trusting the docstring.

  4. ONE SIZING PATH, and it is the project's single sizing function. Leverage
     is an OUTPUT of the structural stop, never an input.

  5. COSTS ARE CHARGED AND NEVER CONSULTED, proved by reading this file's own
     source the same way the crypto suites do it.

  6. NOTHING IS TOUCHED. No venue, no order, no fetch, no write, no git, and
     no import of TJR's or Craig's judgement.

NO NETWORK. Everything reads the parquet `step470_fetch_oanda.py` already
pulled.
"""

from __future__ import annotations

import inspect
import os
import re

import numpy as np
import pandas as pd
import pytest

import alex_engine as ae

REPO = os.path.dirname(os.path.abspath(__file__))
SRC = inspect.getsource(ae)
BODY = SRC.split('"""', 2)[2]          # the module docstring removed

INST = "GBP_USD"
START = pd.Timestamp("2025-07-27")
END = pd.Timestamp("2026-07-26")

_DATA: dict = {}


def data(inst=INST):
    if inst not in _DATA:
        _DATA[inst] = ae.load(inst)
    return _DATA[inst]


def mk(rows, start="2026-03-02 02:00", minutes=60) -> pd.DataFrame:
    base = pd.Timestamp(start)
    return pd.DataFrame([{"t": base + pd.Timedelta(minutes=minutes * i),
                          "open": o, "high": h, "low": l, "close": c,
                          "volume": 100.0}
                         for i, (o, h, l, c) in enumerate(rows)])


# =========================================================== 1. CAUSALITY
def truncate(frames: dict, when) -> dict:
    """Every frame cut to the bars that had CLOSED by `when`. A higher
    timeframe bar still forming is deleted outright, not merely masked."""
    when = pd.Timestamp(when)
    out = {}
    for tf, d in frames.items():
        closes = d["t"] + pd.Timedelta(minutes=ae._TF_MINUTES[tf])
        out[tf] = d[closes <= when].reset_index(drop=True)
    return out


def test_truncation_every_setup_survives_deleting_the_future():
    """THE test. Re-derive each real setup with every bar after its own
    confirmation candle deleted, on all five timeframes. Same side, same
    entry, same stop, same target, same area, same confirmation."""
    cfg = ae.config_for(INST)
    full = ae.find_setups_topdown(INST, data(), cfg, START, END)
    assert len(full) >= 12, f"only {len(full)} setups to test causality on"
    for s in full:
        cut = truncate(data(), s.decided_t)
        again = ae.find_setups_topdown(INST, cut, cfg,
                               s.decided_t - pd.Timedelta(hours=2),
                               s.decided_t)
        match = [g for g in again if g.decided_t == s.decided_t]
        assert match, f"{s.decided_t}: the setup vanished with the future gone"
        g = match[0]
        assert g.direction == s.direction, f"{s.decided_t}: side moved"
        assert g.entry == pytest.approx(s.entry), f"{s.decided_t}: entry moved"
        assert g.stop == pytest.approx(s.stop), f"{s.decided_t}: stop moved"
        assert g.target == pytest.approx(s.target), f"{s.decided_t}: target moved"
        assert g.confirm == s.confirm, f"{s.decided_t}: confirmation changed"
        assert g.area_lo == pytest.approx(s.area_lo)
        assert g.area_hi == pytest.approx(s.area_hi)
        assert g.touches == s.touches


def test_truncation_a_quiet_hour_stays_quiet():
    """The hours the engine sits out must also be decided without the future.
    Sampled across the year so it is not one lucky stretch."""
    cfg = ae.config_for(INST)
    h1 = data()["1h"]
    fired = {pd.Timestamp(s.decided_t)
             for s in ae.find_setups_topdown(INST, data(), cfg, START, END)}
    win = h1[(h1["t"] >= START) & (h1["t"] <= END)].reset_index(drop=True)
    quiet = 0
    for k in range(0, len(win), 61):
        ts = pd.Timestamp(win["t"].iloc[k]) + pd.Timedelta(hours=1)
        if ts in fired or not ae.in_entry_window(ts, cfg):
            continue
        cut = truncate(data(), ts)
        got = ae.find_setups_topdown(INST, cut, cfg, ts - pd.Timedelta(hours=2), ts)
        assert not [g for g in got if g.decided_t == ts], \
            f"{ts}: traded once the future was removed"
        quiet += 1
    assert quiet >= 20, f"only {quiet} quiet hours checked"


def test_a_setup_reads_no_candle_after_its_own():
    """Stronger than truncation: the bars after the confirmation candle are
    replaced with garbage and the answer may not move."""
    cfg = ae.config_for(INST)
    full = ae.find_setups_topdown(INST, data(), cfg, START, END)[:8]
    assert full
    rng = np.random.default_rng(11)
    for s in full:
        poisoned = {}
        for tf, d in data().items():
            d = d.copy()
            closes = d["t"] + pd.Timedelta(minutes=ae._TF_MINUTES[tf])
            after = closes > s.decided_t
            n = int(after.sum())
            if n:
                for col in ("open", "high", "low", "close"):
                    d.loc[after, col] = rng.uniform(0.5, 3.0, n)
                d.loc[after, "high"] = d.loc[after, ["open", "high", "low",
                                                     "close"]].max(axis=1)
                d.loc[after, "low"] = d.loc[after, ["open", "high", "low",
                                                    "close"]].min(axis=1)
            poisoned[tf] = d
        again = ae.find_setups_topdown(INST, poisoned, cfg,
                               s.decided_t - pd.Timedelta(hours=2),
                               s.decided_t)
        m = [g for g in again if g.decided_t == s.decided_t]
        assert m, f"{s.decided_t}: vanished when the future was poisoned"
        assert m[0].entry == pytest.approx(s.entry)
        assert m[0].stop == pytest.approx(s.stop)


def test_the_trend_state_is_a_forward_only_machine():
    """trend_series must give the same answer for bar i whether or not the
    bars after i exist."""
    d = data()["1d"].iloc[:400].reset_index(drop=True)
    full = ae.trend_series(d)
    for i in (120, 200, 260, 333):
        cut = ae.trend_series(d.iloc[:i + 1].reset_index(drop=True))
        assert cut[i] == full[i], f"day {i}: trend changed with the future gone"
        assert list(cut) == list(full[:i + 1]), "the whole history moved"


# ================================== 1b. THE SPINE — his newest teaching
#
# KPVVOa6c6dY_dumb_clean.txt, 2026-06-14. "one pair, one time frame, one
# session, and one entry signal." This is what SHIPS; the top-down path above
# is the older reading, kept so the conflict is measured rather than asserted.

def test_the_spine_is_the_default_and_it_is_the_four_hour_alone():
    cfg = ae.dumb_config_for("EUR_USD")
    assert cfg.tf == "4h"
    assert cfg.signal == "engulfing"
    assert cfg.instrument == "EUR_USD"          # "it would be EuroUSD"
    # the default run mode is the spine, not the older reading
    import inspect as _i
    assert _i.signature(ae.run_book).parameters["mode"].default == "dumb"
    assert _i.signature(ae.run_instrument).parameters["mode"].default == "dumb"


def test_the_spine_reads_only_the_four_hour_frame():
    """'This video is picking one time frame only.' A daily, weekly or hourly
    bar may not change a spine setup — so delete them all and nothing moves."""
    cfg = ae.dumb_config_for(INST)
    full = ae.find_setups_dumb(INST, data(), cfg, START, END)
    assert len(full) >= 15
    only4h = {"4h": data()["4h"], "15m": data()["15m"]}
    again = ae.find_setups_dumb(INST, only4h, cfg, START, END)
    assert [(s.decided_t, s.entry, s.stop, s.target) for s in again] == \
           [(s.decided_t, s.entry, s.stop, s.target) for s in full], \
        "the spine is reading a timeframe it is not allowed to read"


def test_the_spine_survives_deleting_the_future():
    cfg = ae.dumb_config_for(INST)
    full = ae.find_setups_dumb(INST, data(), cfg, START, END)
    assert len(full) >= 15
    for s in full:
        cut = truncate(data(), s.decided_t)
        again = ae.find_setups_dumb(INST, cut, cfg,
                                    s.decided_t - pd.Timedelta(hours=8),
                                    s.decided_t)
        m = [g for g in again if g.decided_t == s.decided_t]
        assert m, f"{s.decided_t}: the spine setup vanished"
        assert m[0].entry == pytest.approx(s.entry)
        assert m[0].stop == pytest.approx(s.stop)
        assert m[0].target == pytest.approx(s.target)
        assert m[0].direction == s.direction
        assert m[0].touches == s.touches         # how many candles it ate


def test_the_engulf_only_reading_of_the_spine_is_still_available():
    """'that is going to be the bullish and bearish engulfing candlestick
    confirmations.' — KPVVOa6c6dY_dumb_clean.txt, 2026-06-14. Switching to
    his one-signal reading gives back exactly one signal."""
    cfg = ae.dumb_config_for(INST, signal_mode="engulf")
    setups = ae.find_setups_dumb(INST, data(), cfg, START, END)
    assert setups
    for s in setups:
        # every one of them IS an engulfing candle; the label also records
        # when a rejection happened to be present in the same candle
        assert s.confirm in ("engulfing", "engulf+rejection")
        assert s.engulfed >= cfg.min_engulfed >= 1


def test_the_rejection_is_the_other_half_of_his_trigger():
    """'the two types of confirmation we look for is either a REJECTION, a
    DOJI, or a bullish engulfing ... But if you have both of these combined,
    they would be a lot more powerful.' — BcWxqfcjk9A.txt 00:03:18,
    2026-04-16. The default admits both, and never anything else."""
    # the June-2026 spine is NEWER than the April-2026 two-trigger video, so
    # the engulf alone is what ships; the rejection half is built and gated
    cfg = ae.dumb_config_for(INST, signal_mode="either")
    assert ae.DumbConfig().signal_mode == "engulf"
    setups = ae.find_setups_dumb(INST, data(), cfg, START, END)
    kinds = {s.confirm for s in setups}
    assert kinds <= {"engulfing", "rejection", "engulf+rejection"}
    assert "rejection" in kinds, "his other half never fires"
    # and taking both cannot LOSE any setup the engulf-only reading found
    only = ae.find_setups_dumb(INST, data(),
                               ae.dumb_config_for(INST, signal_mode="engulf"),
                               START, END)
    both_t = {s.decided_t for s in setups}
    assert {s.decided_t for s in only} <= both_t
    # D3: a rejection with no level under it is refused, and that is a bar
    # being RAISED, not lowered
    loose = ae.find_setups_dumb(INST, data(), ae.dumb_config_for(
        INST, signal_mode="either", rejection_needs_area=False), START, END)
    assert len(loose) > len(setups)


def test_both_together_is_the_highest_quality_tier_and_size_follows():
    """'if you have both of these combined, they would be a lot more
    powerful. The more dojis that you would have, the more powerful.'
    — BcWxqfcjk9A.txt, 2026-04-16, feeding 'you can risk more on low-risk
    trades' — LwMsai2ppKc.txt 00:22:34, 2026-02-22."""
    # a combined trigger always scores at least as high as the engulf alone
    a, _ = ae.quality_points(1, False, 0, None)
    b, _ = ae.quality_points(1, True, 0, None)
    c, _ = ae.quality_points(1, True, 3, None)
    d, _ = ae.quality_points(4, True, 3, None)
    assert a < b < c < d
    f = ae.DumbConfig.quality_floor_share
    # anchored at the top: full size only at perfect confluence
    assert ae.quality_weight(0, 4, f, "top") == pytest.approx(f)
    assert ae.quality_weight(4, 4, f, "top") == pytest.approx(1.0)
    # anchored at his own sentence: a plain valid setup gets the configured
    # risk and confluence scales it UP from there
    assert ae.quality_weight(0, 4, f, "base", 2.0) == pytest.approx(1.0)
    assert ae.quality_weight(4, 4, f, "base", 2.0) == pytest.approx(2.0)
    assert ae.DumbConfig().quality_anchor == "base"
    # the floor is a SIZE floor, never a validity floor
    assert ae.DumbConfig().min_engulfed == 1


def test_engulfed_count_is_his_grading_and_it_counts_leftward():
    """'The more candlestick it engulfs, the better.' And 'this looks like a
    bullish candle, but it didn't really engulf anything ... this is NOT a
    bullish engulfing candlestick.'"""
    # one big red body swallowing the three small green bodies before it
    d = mk([(1.000, 1.004, 0.999, 1.002), (1.002, 1.005, 1.001, 1.003),
            (1.003, 1.006, 1.002, 1.004), (1.0065, 1.007, 0.9985, 0.999)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.engulfed_count(o, h, l, c, 3, -1) == 3
    assert ae.engulfed_count(o, h, l, c, 3, +1) == 0, "wrong side counted"
    # a candle that engulfs nothing is not one at all
    d = mk([(1.000, 1.010, 0.990, 1.008), (1.0081, 1.0085, 1.0079, 1.0083)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.engulfed_count(o, h, l, c, 1, +1) == 0
    # raising his dial genuinely removes trades
    cfg1 = ae.dumb_config_for(INST, min_engulfed=1)
    cfg3 = ae.dumb_config_for(INST, min_engulfed=3)
    n1 = len(ae.find_setups_dumb(INST, data(), cfg1, START, END))
    n3 = len(ae.find_setups_dumb(INST, data(), cfg3, START, END))
    assert 0 < n3 < n1, f"the dial is not wired: {n1} -> {n3}"


def test_the_spine_session_is_pre_london_and_london_only():
    """'one or two hours before London session ... like 1 2 in the morning my
    time zone EST'. On the 17:00-anchored 4-hour grid that is the 01:00 and
    05:00 New York closes and nothing else."""
    cfg = ae.dumb_config_for(INST)
    assert cfg.entry_hours == (1.0, 5.0)
    assert ae.dumb_in_window(pd.Timestamp("2026-07-06 01:00"), cfg)
    assert ae.dumb_in_window(pd.Timestamp("2026-07-06 05:00"), cfg)
    for out in ("2026-07-06 09:00", "2026-07-06 13:00", "2026-07-06 17:00",
                "2026-07-06 21:00", "2026-07-06 00:30"):
        assert not ae.dumb_in_window(pd.Timestamp(out), cfg), out
    for day in ("2026-07-10", "2026-07-11", "2026-07-12"):   # Fri, Sat, Sun
        assert not ae.dumb_in_window(pd.Timestamp(day + " 01:00"), cfg)
    # and no real entry escapes it
    f = ae.frame(ae.run_book([INST], START, END, cache=_DATA, verbose=False))
    assert len(f) >= 10
    for ts in f["entry_t"]:
        t = pd.Timestamp(ts)
        assert (t.hour + t.minute / 60.0) in (1.0, 5.0), f"{t}: out of session"
        assert t.weekday() <= 3, f"{t}: entered on a {t.day_name()}"


def test_his_friday_rule_exists_fires_and_is_not_a_break_even():
    """'if you're in a losing position and the weekend is coming up and you're
    halfway through your stop loss, I would probably close before the market
    closes' — the spine, 2026-06-14. NEW; no older video has it."""
    assert ae.dumb_config_for(INST).friday_exit_at_half_stop is True
    book = ae.run_book(None, pd.Timestamp("2021-07-05"), END, cache=_DATA,
                       verbose=False)
    f = ae.frame(book)
    fri = f[f["outcome"] == "friday"]
    assert len(fri) >= 3, "his Friday rule never fired in five years"
    for _, r in fri.iterrows():
        t = pd.Timestamp(r["exit_t"])
        assert t.weekday() == 4, f"{t}: a 'friday' exit that is not a Friday"
        # it is a LOSS, never a break even and never a win
        assert r["pnl"] < 0, "the Friday exit came out at or above break even"
        moved = (r["exit"] - r["entry"]) * (1 if r["side"] == "long" else -1)
        assert moved <= -0.5 * abs(r["entry"] - r["stop"]) + 1e-9, \
            "closed before it was halfway to the stop"


def test_turning_his_friday_rule_off_changes_the_answer():
    a = ae.frame(ae.run_book([INST], pd.Timestamp("2021-07-05"), END,
                             cache=_DATA, verbose=False))
    b = ae.frame(ae.run_book([INST], pd.Timestamp("2021-07-05"), END,
                             cfg_over={"friday_exit_at_half_stop": False},
                             cache=_DATA, verbose=False))
    assert (a["outcome"] == "friday").sum() > 0
    assert (b["outcome"] == "friday").sum() == 0
    assert a["pnl"].sum() != b["pnl"].sum()


def test_the_spine_takes_few_trades_on_his_one_pair():
    """His spine is ONE pair. On EUR/USD alone it must stay inside his stated
    one-to-two a week."""
    r = ae.run_book(["EUR_USD"], pd.Timestamp("2021-07-05"), END,
                    cache=_DATA, verbose=False)["EUR_USD"]
    per_week = len(r["trades"]) / r["weeks"]
    assert 0.05 <= per_week <= 2.0, f"EUR/USD fires {per_week:.2f} a week"


# ======================================================== 2. HIS RULES
def test_an_area_needs_three_touches():
    """'We need to have a minimum of three touches for it to be considered an
    area of interest.' — MhWSZp4yS2c.txt 00:24:10, 2026-06-28"""
    cfg = ae.config_for(INST)
    assert cfg.min_touches == 3
    d = data()["1d"]
    a = ae.atr(d, cfg.atr_len)
    seen = 0
    for i in range(300, 900, 17):
        for ar in ae.areas_at(d, i, cfg, "1d", a):
            assert ar.touches >= 3, f"an area with {ar.touches} touches"
            assert ar.lo <= ar.hi
            seen += 1
    assert seen >= 20
    # and two touches is genuinely refused
    tight = ae.config_for(INST, min_touches=2)
    more = sum(len(ae.areas_at(d, i, tight, "1d", a))
               for i in range(300, 900, 17))
    assert more > seen, "lowering the touch count changed nothing — not wired"


def test_an_area_uses_no_bar_after_the_one_it_is_stamped_on():
    cfg = ae.config_for(INST)
    d = data()["1d"]
    a = ae.atr(d, cfg.atr_len)
    for i in (350, 500, 777):
        full = ae.areas_at(d, i, cfg, "1d", a)
        cut = ae.areas_at(d.iloc[:i + 1].reset_index(drop=True), i, cfg, "1d",
                          ae.atr(d.iloc[:i + 1].reset_index(drop=True),
                                 cfg.atr_len))
        assert [(x.lo, x.hi, x.touches) for x in full] == \
               [(x.lo, x.hi, x.touches) for x in cut]


def test_the_confirmations_are_his_three_and_they_are_shape_tests():
    """rejection, engulfing, and the star that 'engulfs the last two'."""
    # a clean bearish engulfing after a small up candle
    d = mk([(1.0, 1.02, 0.99, 1.01), (1.01, 1.03, 1.005, 1.02),
            (1.03, 1.035, 1.00, 1.005)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, -1) == "bearish_engulfing"
    assert ae.confirmation(o, h, l, c, 2, +1) == ""

    # the mirror
    d = mk([(1.03, 1.04, 1.02, 1.025), (1.025, 1.03, 1.015, 1.02),
            (1.015, 1.045, 1.012, 1.04)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, +1) == "bullish_engulfing"

    # an evening star: big up, tiny middle, big down that eats both
    d = mk([(1.00, 1.031, 1.00, 1.030), (1.0305, 1.034, 1.0300, 1.0310),
            (1.0345, 1.035, 0.995, 0.998)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, -1) == "evening_star"

    # a rejection: long upper wick, small body
    d = mk([(1.00, 1.01, 0.99, 1.005), (1.005, 1.01, 1.00, 1.008),
            (1.010, 1.060, 1.008, 1.012)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, -1) == "rejection"

    # a nothing candle is nothing: mostly body, no wick worth the name,
    # engulfing neither the candle before it nor the two before it
    d = mk([(1.00, 1.01, 0.99, 1.005), (1.005, 1.01, 1.00, 1.008),
            (1.0080, 1.0095, 1.0078, 1.0093)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, -1) == ""
    assert ae.confirmation(o, h, l, c, 2, +1) == ""

    # and a candle with a long wick the WRONG way is not a confirmation
    d = mk([(1.00, 1.01, 0.99, 1.005), (1.005, 1.01, 1.00, 1.008),
            (1.010, 1.060, 1.008, 1.012)])
    o, h, l, c = (d[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    assert ae.confirmation(o, h, l, c, 2, +1) == "", \
        "a long UPPER wick was read as a confirmation to buy"


def test_the_entry_window_is_his_and_it_gates_entries_only():
    """01:00-10:30 New York, no Sunday, nothing past Thursday 09:00."""
    cfg = ae.config_for(INST)
    # Monday 2026-07-06
    assert ae.in_entry_window(pd.Timestamp("2026-07-06 01:00"), cfg)
    assert ae.in_entry_window(pd.Timestamp("2026-07-06 10:30"), cfg)
    assert not ae.in_entry_window(pd.Timestamp("2026-07-06 00:59"), cfg)
    assert not ae.in_entry_window(pd.Timestamp("2026-07-06 10:31"), cfg)
    assert not ae.in_entry_window(pd.Timestamp("2026-07-06 14:00"), cfg)
    # Thursday 2026-07-09: 09:00 in, 09:01 out
    assert ae.in_entry_window(pd.Timestamp("2026-07-09 09:00"), cfg)
    assert not ae.in_entry_window(pd.Timestamp("2026-07-09 09:01"), cfg)
    # Friday, Saturday, Sunday: never
    for day in ("2026-07-10", "2026-07-11", "2026-07-12"):
        assert not ae.in_entry_window(pd.Timestamp(day + " 04:00"), cfg)


def test_no_real_entry_lands_outside_his_hours():
    book = ae.run_book([INST, "XAU_USD"], START, END, cache=_DATA,
                       verbose=False, mode="topdown")
    f = ae.frame(book)
    assert len(f) >= 10
    for ts in f["entry_t"]:
        t = pd.Timestamp(ts)
        hh = t.hour + t.minute / 60.0
        assert 1.0 <= hh <= 10.5, f"{t}: entered outside 01:00-10:30 New York"
        assert t.weekday() <= 3, f"{t}: entered on a {t.day_name()}"
        if t.weekday() == 3:
            assert hh <= 9.0, f"{t}: entered past the Thursday cut-off"
    assert set(f["session"]) <= {"london", "new_york"}


def test_exits_are_not_gated_by_the_clock_and_trades_live_for_days():
    """His 10:30 is an ENTRY cut-off, not a flatten. TJR's is a flatten.
    Getting this backwards would turn his method into someone else's."""
    book = ae.run_book([INST, "XAU_USD"], START, END, cache=_DATA,
                       verbose=False, mode="topdown")
    f = ae.frame(book)
    done = f[f["outcome"].isin(["stop", "target"])]
    assert len(done) >= 10
    outside = [pd.Timestamp(t) for t in done["exit_t"]
               if not (1.0 <= pd.Timestamp(t).hour
                       + pd.Timestamp(t).minute / 60.0 <= 10.5)]
    assert outside, "every exit landed inside the entry window — clock-gated"
    assert done["hours_held"].max() > 24.0, \
        "nothing was held overnight; this is not his method"


def test_the_target_is_the_risk_actually_taken_times_two():
    """'always be a minimum of a one to two risk-to-reward'"""
    cfg = ae.config_for(INST)
    for s in ae.find_setups_topdown(INST, data(), cfg, START, END):
        risk = abs(s.entry - s.stop)
        reward = abs(s.target - s.entry)
        assert reward == pytest.approx(cfg.target_r * risk), \
            f"{s.decided_t}: {reward / risk:.2f}R target"
        if s.direction < 0:
            assert s.stop > s.entry > s.target
        else:
            assert s.stop < s.entry < s.target


def test_the_stop_sits_beyond_the_area_it_is_defending():
    cfg = ae.config_for(INST)
    for s in ae.find_setups_topdown(INST, data(), cfg, START, END):
        if s.direction < 0:
            assert s.stop > s.area_hi, f"{s.decided_t}: stop inside the area"
        else:
            assert s.stop < s.area_lo, f"{s.decided_t}: stop inside the area"


def test_the_daily_calls_the_direction_and_the_four_hour_agrees():
    cfg = ae.config_for(INST)
    for s in ae.find_setups_topdown(INST, data(), cfg, START, END):
        assert s.trend_d == s.direction, f"{s.decided_t}: against the daily"
        assert s.trend_4h == s.direction, f"{s.decided_t}: 4h disagreed"


def test_he_takes_few_trades():
    """'the max amount of trades that you want to take in a week is anywhere
    from one to two trades.' If the engine fires daily it has misread him."""
    book = ae.run_book(None, START, END, cache=_DATA, verbose=False)
    book.update(ae.run_book(None, START, END, cache=_DATA, verbose=False,
                            mode="topdown"))
    for inst, r in book.items():
        per_week = len(r["trades"]) / r["weeks"]
        assert per_week <= 2.0, f"{inst}: {per_week:.2f} trades a week"
    total = sum(len(r["trades"]) for r in book.values())
    weeks = list(book.values())[0]["weeks"]
    assert 0.3 <= total / weeks <= 4.0, \
        f"the whole book fires {total / weeks:.2f} a week"


# ========================= 3. NO BREAK EVEN, NO PARTIAL, NO TRAIL, NO CLOCK
def test_the_management_code_contains_no_break_even_mechanic():
    """'I am not a break even trader.' — ig6Z2Gbk_LE.txt 00:18:54, 2025-11-09
    Read out of the code, not out of the docstring."""
    body = inspect.getsource(ae.manage)
    code = body.split('"""', 2)[2]
    for banned in ("break_even", "breakeven", "partial", "trail", "scale_out",
                   "move_stop"):
        assert banned not in code.lower(), \
            f"manage() contains a {banned} mechanic — that is not his method"
    # the stop is only ever the one it entered with
    assert code.count("s.stop") >= 2
    assert "tr.stop =" not in code, "the stop is being reassigned"


def test_the_only_exits_are_the_stop_the_target_and_our_own_declared_cap():
    book = ae.run_book(None, START, END, cache=_DATA, verbose=False)
    seen = set(ae.frame(book)["outcome"])
    assert seen <= {"stop", "target", "open", "held_out", "friday"}, seen
    assert {"stop", "target"} <= seen


def test_the_exit_path_never_reads_a_wall_clock():
    """His 10:30 gates ENTRIES. No exit in this engine may look at a clock —
    the only time `manage` touches is elapsed duration, never wall time."""
    code = inspect.getsource(ae.manage).split('"""', 2)[2]
    for banned in (".hour ", ".hour)", ".minute", "in_entry_window",
                   "session_of", "entry_to_hour", "entry_from_hour",
                   "10.5", "day_name"):
        assert banned not in code, f"manage() consults {banned}"
    # THE ONE EXCEPTION, and it is HIS: the Friday rule from the spine.
    assert "_is_last_bar_of_the_week" in code
    assert code.count("_is_last_bar_of_the_week") == 1, \
        "more than one clock read in the exit path"


# ============================================================ 4. SIZING
def test_there_is_exactly_one_sizing_path():
    assert BODY.count("size_position(") == 1
    assert "risk_pct" in inspect.getsource(ae.manage)
    for banned in ("units =", "lots ="):
        assert BODY.count(banned) <= 2


def test_leverage_is_an_output_of_the_structural_stop():
    """A tighter stop must produce more leverage for the same share of the
    account risked. That is the direction of causation his rule requires."""
    book = ae.run_book(None, START, END, cache=_DATA, verbose=False)
    f = ae.frame(book)
    f = f[f["outcome"].isin(["stop", "target"])]
    assert (f["leverage"] > 0).all()
    for inst, g in f.groupby("instrument"):
        if len(g) < 8:
            continue
        r = np.corrcoef(g["stop_move_in_price_pct"], g["leverage"])[0, 1]
        assert r < -0.5, f"{inst}: leverage does not fall as the stop widens"


def test_the_dollars_at_risk_are_the_configured_share_of_the_account():
    cfg = ae.config_for(INST)
    book = ae.run_book([INST], START, END, cache=_DATA, verbose=False)
    top = ae.DumbConfig().quality_max_mult
    for t in book[INST]["trades"]:
        assert t.risk_dollars > 0
        # the configured share of the account, times this setup's own
        # confluence multiplier ("you can risk more on low-risk trades"),
        # times headroom for the account having grown
        assert t.risk_dollars <= cfg.risk_pct_per_trade * \
            cfg.account_start * top * 1.6
        assert t.quality <= top + 1e-9


def test_the_yen_pair_converts_its_profit_into_dollars():
    """Off by a factor of about 150 if this is wrong."""
    frames = ae.load("GBP_JPY")
    s = ae.usd_per_quote_series("GBP_JPY", frames, {})
    assert s is not None and len(s) > 500
    assert 0.005 < s["upq"].median() < 0.012, s["upq"].median()
    assert ae.usd_per_quote_series("EUR_USD", frames, {}) is None
    assert ae._upq_at(None, pd.Timestamp("2026-01-01")) == 1.0


def test_no_percentage_is_reported_without_saying_which_one_it_is():
    f = ae.frame(ae.run_book([INST], START, END, cache=_DATA, verbose=False))
    assert "stop_move_in_price_pct" in f.columns
    assert not any(c == "pct" or c.endswith("_pct") and "move_in_price" not in c
                   for c in f.columns), list(f.columns)


# ============================================================== 5. COSTS
def test_the_cost_is_charged_and_never_consulted():
    """Wallace's standing rule: fees are charged for an honest P&L and never
    allowed to decline a trade, gate a strategy, or rank an instrument.

    The two lines that merely FILL IN the cost number when a config is built
    are exempt by name — they choose a venue's price list, not a trade.
    """
    exempt = ("round_trip_cost_share", "self.round_trip_cost_pct",
              'over.get("round_trip_cost_pct")')
    for i, line in enumerate(BODY.splitlines(), 1):
        code = line.split("#")[0]
        if "cost" not in code.lower():
            continue
        if code.strip().startswith(("def ", "class ", '"', "'")):
            continue
        if any(x in code for x in exempt):
            continue
        for bad in (" if ", " > ", " < ", ">=", "<=", " and ", " or "):
            assert bad not in code, \
                f"line {i}: the cost reached a decision:\n  {line}"
    # and the one place it is applied is a multiplication and nothing else
    assert "tr.cost = notional * cfg.round_trip_cost_pct" in BODY


def test_gold_is_charged_blofin_and_the_pairs_are_charged_oanda():
    g = ae.round_trip_cost_share("XAU_USD")
    assert g == pytest.approx(2 * ae.BLOFIN_FEE_PER_SIDE + ae.XAUT_SPREAD_SHARE)
    assert ae.BLOFIN_FEE_PER_SIDE == 0.0006
    for p in ae.PAIRS:
        c = ae.round_trip_cost_share(p)
        assert 0 < c < 0.001, f"{p}: {c}"
        assert c != g


def test_every_closed_trade_actually_paid_its_cost():
    book = ae.run_book(None, START, END, cache=_DATA, verbose=False)
    f = ae.frame(book)
    done = f[f["outcome"].isin(["stop", "target"])]
    assert (done["cost"] > 0).all()
    assert done["cost"].sum() > 0


# ==================================================== 6. NOTHING IS TOUCHED
def test_nothing_is_fetched_written_or_ordered():
    for bad in ("to_parquet", "requests", "urllib", "httpx", "subprocess",
                "os.system", "place_order", "market_order", "limit_order",
                "submit_order", "create_order", ".post(", ".put("):
        assert bad not in SRC, f"the engine reaches for {bad}"


def test_no_venue_is_imported():
    imports = [l for l in SRC.splitlines() if l.startswith(("import ", "from "))]
    for bad in ("oanda_api", "blofin", "venue", "alpaca", "daemon",
                "tjr_desk", "tjr_forex", "craig_crypto", "tjr_crypto"):
        assert not any(bad in l for l in imports), f"imports {bad}"


def test_only_two_pure_helpers_come_from_another_method():
    """Methods never mix. A swing definition and the project's one sizing
    function are the whole of what crosses the line, and neither carries an
    opinion about when to trade."""
    imports = [l for l in SRC.splitlines() if l.startswith(("import ", "from "))]
    tjr = [l for l in imports if "tjr" in l]
    assert tjr == ["from tjr_bot import size_position, two_candle_swings"], tjr
    assert set(re.findall(r"tjr_bot\.(\w+)", BODY)) <= {
        "two_candle_swings", "size_position"}
    for name in ("craig", "Craig", "TJR", "tjr_alerts"):
        assert name not in BODY, f"{name} leaked into the engine body"


def test_the_instruments_are_his_pairs_plus_gold():
    assert ae.PAIRS == ["GBP_JPY", "GBP_USD", "EUR_USD"]
    assert ae.GOLD == "XAU_USD"
    assert ae.INSTRUMENTS == ae.PAIRS + [ae.GOLD]


def test_no_news_gate_exists_because_he_does_not_use_one():
    """'There's no way that I am going to modify my trading approach simply
    because of a news event' — grw58BIzotU.txt 03:01:55, 2025-09-28"""
    for bad in ("news", "calendar", "cpi", "nfp", "fomc"):
        assert bad not in BODY.lower(), f"a {bad} gate exists"


def test_every_invention_is_declared():
    words = ae.in_his_words()
    for must in ("swing", "touch", "engulf", "1:2", "one position at a time",
                 "30-day cap", "3% of the account", "gold replays",
                 "buying-power"):
        assert must.lower() in words.lower(), f"{must} is not declared"
    assert "SILENT" in words


def test_the_engine_runs_end_to_end_and_books_money():
    book = ae.run_book(None, START, END, cache=_DATA, verbose=False)
    f = ae.frame(book)
    assert len(f) >= 40
    assert {"instrument", "session", "leverage", "stop_move_in_price_pct",
            "pnl", "cost", "r", "outcome"}.issubset(f.columns)
    for inst, r in book.items():
        assert r["account"] == pytest.approx(
            r["config"].account_start + sum(t.pnl for t in r["trades"]))


# ============================================ 12. step472 — THE HEAD AND
#                                              SHOULDERS, TARGETS, EXITS, SIZE
def test_the_head_and_shoulders_exists_and_it_fires():
    """'my favorites and the ONLY reversal pattern that you're going to need
    is going to be this head and shoulders pattern ... This is my go-to
    pattern.' — grw58BIzotU.txt 06:49:00, 2025-09-28. It was missing from the
    engine until step472, which is why his prop plan was graded on a pattern
    he was not recommending."""
    cfg = ae.dumb_config_for(INST, pattern="hs")
    setups = ae.find_setups_hs(INST, data(), cfg, START, END)
    assert len(setups) >= 5, f"only {len(setups)} head-and-shoulders in a year"
    for s in setups:
        assert s.pattern == "hs"
        assert not np.isnan(s.neckline) and not np.isnan(s.head)
        # the head is beyond the neckline, on the side the pattern reverses
        if s.direction < 0:
            assert s.head > s.neckline
        else:
            assert s.head < s.neckline


def test_the_neckline_is_built_only_from_closed_candles():
    """THE mandatory test for this pattern. Re-derive every head-and-shoulders
    with every bar after its own entry candle deleted on all five timeframes.
    A neckline is a level that already existed and was already broken; if any
    part of it were read from the future this test would fail."""
    cfg = ae.dumb_config_for(INST, pattern="hs")
    full = ae.find_setups_hs(INST, data(), cfg, START, END)
    assert len(full) >= 5
    for s in full:
        cut = truncate(data(), s.decided_t)
        again = ae.find_setups_hs(INST, cut, cfg,
                                  s.decided_t - pd.Timedelta(hours=8),
                                  s.decided_t)
        match = [g for g in again if g.decided_t == s.decided_t]
        assert match, f"{s.decided_t}: the pattern vanished with the future gone"
        g = match[0]
        assert g.direction == s.direction
        assert g.entry == pytest.approx(s.entry)
        assert g.stop == pytest.approx(s.stop)
        assert g.target == pytest.approx(s.target)
        assert g.neckline == pytest.approx(s.neckline)
        assert g.head == pytest.approx(s.head)


def test_the_head_and_shoulders_reads_no_candle_after_its_own():
    """Garbage in place of the future, and the answer may not move."""
    cfg = ae.dumb_config_for(INST, pattern="hs")
    full = ae.find_setups_hs(INST, data(), cfg, START, END)[:8]
    assert full
    for s in full:
        junk = {}
        for tf, d in data().items():
            e = d.copy()
            after = (e["t"] + pd.Timedelta(minutes=ae._TF_MINUTES[tf])) > s.decided_t
            for col in ("open", "high", "low", "close"):
                e.loc[after, col] = e.loc[after, col] * 7.3 + 11.0
            junk[tf] = e
        again = ae.find_setups_hs(INST, junk, cfg,
                                  s.decided_t - pd.Timedelta(hours=8),
                                  s.decided_t)
        m = [g for g in again if g.decided_t == s.decided_t]
        assert m, f"{s.decided_t}: vanished when the future was corrupted"
        assert m[0].entry == pytest.approx(s.entry)
        assert m[0].stop == pytest.approx(s.stop)
        assert m[0].neckline == pytest.approx(s.neckline)


def test_the_pattern_is_drawn_on_bodies_and_the_stop_on_the_wick():
    """'that is done to the BODIES of the candlestick. We are not including
    the wicks at no point when identifying a head and shoulders.'
    — grw58BIzotU.txt 06:51:10. And, in the same method, 'entered this
    position with my STOP LOSS ABOVE THE WICK' — hb7ot1_szWI.txt 00:28:46,
    2026-07-26. Two different reads, both his, kept apart."""
    d = mk([(1.0, 1.9, 0.9, 1.1), (1.1, 1.2, 0.5, 1.0)], minutes=240)
    b = ae.body_frame(d)
    assert list(b["high"]) == [1.1, 1.1]
    assert list(b["low"]) == [1.0, 1.0]
    assert list(b["close"]) == list(d["close"])
    # and the stop on a real pattern sits beyond the real wick, not the body
    cfg = ae.dumb_config_for(INST, pattern="hs")
    d4 = data()["4h"]
    for s in ae.find_setups_hs(INST, data(), cfg, START, END)[:10]:
        w = d4[(d4["t"] <= s.signal_t)].tail(20)
        if s.direction < 0:
            assert s.stop > max(s.entry, float(w["close"].iloc[-1]))
        else:
            assert s.stop < min(s.entry, float(w["close"].iloc[-1]))


def test_no_head_and_shoulders_without_the_neckline_break():
    """'The head and shoulders will only be valid ONCE WE BREAK THE NECKLINE.
    If we have not broken the neckline, we cannot count it as a head and
    shoulders.' — grw58BIzotU.txt 06:56:50, 2025-09-28. Every entry sits on
    the far side of its own neckline, in the trade's direction."""
    cfg = ae.dumb_config_for(INST, pattern="hs")
    for s in ae.find_setups_hs(INST, data(), cfg, START, END):
        tol = s.area_hi - s.neckline
        if s.direction < 0:
            assert s.entry <= s.neckline + tol + 1e-9
        else:
            assert s.entry >= s.neckline - tol - 1e-9


def test_the_right_shoulder_entry_is_off_because_he_says_not_to_take_it():
    """'SELLING AT THE RIGHT SHOULDER IS EXTREMELY HIGH RISK. I DON'T
    RECOMMEND IT unless you are an experienced trader.' — grw58BIzotU.txt
    06:54:46, 2025-09-28. Built, defaulted off, and it changes the answer."""
    assert ae.DumbConfig().hs_allow_right_shoulder is False
    off = ae.find_setups_hs(INST, data(), ae.dumb_config_for(INST, pattern="hs"),
                            START, END)
    on = ae.find_setups_hs(
        INST, data(),
        ae.dumb_config_for(INST, pattern="hs", hs_allow_right_shoulder=True),
        START, END)
    assert len(on) > len(off), "his high-risk entry adds nothing"


# --------------------------------------------------------- structure targets
def test_the_target_is_a_structure_point_not_a_multiple_of_the_risk():
    """'my take profit to the NEXT STRUCTURE POINT. That is it.'
    — hb7ot1_szWI.txt 00:28:46, 2026-07-26. The flat 1:2 was OURS; this is
    his. The two disagree on nearly every trade, which is the point."""
    assert ae.DumbConfig().target_mode == "structure"
    fx = ae.find_setups_dumb(INST, data(),
                             ae.dumb_config_for(INST, target_mode="fixed_r"),
                             START, END)
    st = ae.find_setups_dumb(INST, data(), ae.dumb_config_for(INST),
                             START, END)
    by_t = {s.decided_t: s for s in fx}
    moved = [s for s in st if s.decided_t in by_t
             and abs(s.target - by_t[s.decided_t].target) > 1e-9]
    assert moved, "the structure target never differs from a flat 1:2"
    # and the OTHER reading of the same sentence — "take profit to the next
    # structure point ... but I decided to close at my 1 to 2" — keeps the
    # flat exit while REFUSING every setup with no structure point paying it
    dflt = ae.find_setups_dumb(INST, data(),
                               ae.dumb_config_for(INST,
                                                  target_mode="filtered_2r"),
                               START, END)
    assert len(dflt) < len(fx), "the structure filter refuses nothing"
    by_d = {s.decided_t: s for s in dflt}
    assert set(by_d) <= set(by_t)
    for k, v in by_d.items():
        assert v.target == pytest.approx(by_t[k].target)


def test_no_setup_survives_that_cannot_pay_his_minimum():
    """'always at a minimum of a 1:2' — DsPLtzjTONI.txt 00:10:50, 2026-06-22,
    and 'Do not take a trade that is not worth the risk' — hb7ot1_szWI.txt
    00:33:38, 2026-07-26. His 1:2 is a filter on which setups are worth
    taking, so a setup whose nearest structure cannot pay it is DROPPED, not
    stretched to fit."""
    for pat in ("engulf", "hs"):
        cfg = ae.dumb_config_for(INST, pattern=pat)
        finder = ae.find_setups_dumb if pat == "engulf" else ae.find_setups_hs
        for s in finder(INST, data(), cfg, START, END):
            rr = abs(s.target - s.entry) / abs(s.entry - s.stop)
            assert rr >= cfg.min_rr - 1e-9, f"{s.decided_t}: {rr:.2f} paid"


def test_the_structure_target_is_the_nearest_one_that_pays():
    """'THE CLOSER THE BETTER and always at a minimum of a 1:2.'
    — DsPLtzjTONI.txt 00:10:50, 2026-06-22."""
    sl = np.array([np.nan, 90.0, np.nan, 80.0, np.nan, 60.0, np.nan])
    sh = np.full(7, np.nan)
    cfg = ae.dumb_config_for(INST)
    # entry 100, stop 110 -> risk 10, so 1:2 needs 80 or lower. 90 fails,
    # 80 is the nearest that pays, 60 is further and must not be chosen.
    t = ae.next_structure_target(sh, sl, 6, 100.0, 110.0, -1, 0.0, cfg)
    assert t == pytest.approx(80.0)


def test_a_setup_with_no_structure_within_reach_is_not_taken():
    sl = np.array([np.nan, 99.0, np.nan, 98.0])
    sh = np.full(4, np.nan)
    cfg = ae.dumb_config_for(INST)
    assert ae.next_structure_target(sh, sl, 3, 100.0, 110.0, -1, 0.0, cfg) is None


# ------------------------------------------------------- structure-shift exit
def test_the_structure_shift_exit_is_built_off_by_default_and_it_bites():
    """'Change of character is when the market shifts ... Break of structure
    is when this was the previous structure and we break it.'
    — grw58BIzotU.txt 06:09:21, 2025-09-28. Applying it to an OPEN trade is
    OURS — his own management is 'set and forget' — so it ships off and is
    measured on."""
    assert ae.DumbConfig().exit_on_structure_flip is False
    base = ae.run_instrument(INST, START, END)
    flip = ae.run_instrument(INST, START, END, cfg=ae.dumb_config_for(
        INST, exit_on_structure_flip=True))
    outs = {t.outcome for t in flip["trades"]}
    assert "flip" in outs, "the structure-shift exit never fired"
    assert not any(t.outcome == "flip" for t in base["trades"])


def test_the_runner_is_built_off_by_default_and_holds_past_the_target():
    """'Once your trade gets to your original take profit, close this trade
    fully and then LEAVE THIS ONE RUN' — o1T6dLoywTw.en.vtt 00:06:25,
    2023-03-26, and 'I would always aim for the trade to have a potential of
    a one to 4' — grw58BIzotU.txt 08:38:10, 2025-09-28."""
    assert ae.DumbConfig().runner is False
    r = ae.run_instrument(INST, START, END,
                          cfg=ae.dumb_config_for(INST, runner=True))
    kept = [t for t in r["trades"] if t.outcome.startswith("runner")]
    assert kept, "nothing ever ran past his target"
    for t in kept:
        assert t.target_t is not None and t.exit_t >= t.target_t
        assert t.runner_share == pytest.approx(0.5)


def test_no_stop_is_ever_moved_anywhere_in_the_exit_path():
    """'I am not a break even trader' — ig6Z2Gbk_LE_gold_clean.txt,
    2025-11-09. The runner keeps the ORIGINAL stop; nothing trails."""
    src = inspect.getsource(ae.manage)
    code = re.sub(r'"""(?:.|\n)*?"""', "", src)      # prose out, code only
    for bad in ("tr.stop =", "s.stop =", "trail", "break_even", "breakeven"):
        assert bad not in code, f"{bad} appears in the exit path"


# ------------------------------------------------------------- his cadence
def test_his_two_a_week_cap_is_built_and_defaults_off():
    """'Do not overtrade ... LIMIT YOURSELF TO TWO POSITIONS A WEEK.'
    — hb7ot1_szWI.txt 00:04:16, 2026-07-26. Its stated purpose is not to
    over-trade and not to let emotion in, which is a human problem, so it
    ships OFF and is measured both ways. Wallace's ruling, 2026-07-27."""
    assert ae.DumbConfig().human_cadence_cap is False
    assert ae.DumbConfig().max_positions_per_week == 2
    capped = ae.run_instrument(INST, START, END, cfg=ae.dumb_config_for(
        INST, pattern="both", human_cadence_cap=True))
    free = ae.run_instrument(INST, START, END,
                             cfg=ae.dumb_config_for(INST, pattern="both"))
    assert len(capped["trades"]) <= len(free["trades"])
    weeks = {}
    for t in capped["trades"]:
        k = pd.Timestamp(t.entry_t).to_period("W")
        weeks[k] = weeks.get(k, 0) + 1
    assert weeks and max(weeks.values()) <= 2


def test_the_cap_never_loosens_what_counts_as_a_valid_setup():
    """Wallace's ruling was 'take every VALID setup', not 'lower the bar'.
    Turning the cap off may only ADD trades the engine already validated."""
    free = ae.run_instrument(INST, START, END,
                             cfg=ae.dumb_config_for(INST, pattern="both"))
    capped = ae.run_instrument(INST, START, END, cfg=ae.dumb_config_for(
        INST, pattern="both", human_cadence_cap=True))
    assert {s.decided_t for s in capped["setups"]} == \
        {s.decided_t for s in free["setups"]}


# --------------------------------------------------------------- the control
def test_the_control_holds_everything_but_the_side():
    """step471's standard: same entries, same days, same stop distances,
    DIRECTION REVERSED. A pattern whose fade beats it is noise."""
    cfg = ae.dumb_config_for(INST, pattern="both")
    real = ae.find_setups_dumb(INST, data(), cfg, START, END)
    faded = ae.apply_control(list(real), ae.dumb_config_for(
        INST, pattern="both", control="reversed"))
    assert len(faded) == len(real)
    for a, b in zip(real, faded):
        assert b.direction == -a.direction
        assert b.entry == pytest.approx(a.entry)
        assert b.decided_t == a.decided_t
        assert abs(b.entry - b.stop) == pytest.approx(abs(a.entry - a.stop))
        assert (abs(b.target - b.entry) / abs(b.entry - b.stop)) == \
            pytest.approx(abs(a.target - a.entry) / abs(a.entry - a.stop))


# ------------------------------------------------------------ the layers
def test_the_weekly_close_gate_is_his_and_it_only_reads_closed_weeks():
    """'those candlesticks OPENING AND CLOSING dictate the direction of the
    following week.' — 1dL3xmxA2e0.txt 00:06:12, 2026-05-25."""
    w = ae.weekly_bias_table(data())
    wk = data()["1w"]
    assert (w["known_at"] > pd.to_datetime(wk["t"])).all()
    cfg = ae.dumb_config_for(INST, weekly_bias=True)
    kept = ae.find_setups_dumb(INST, data(), cfg, START, END)
    allk = ae.find_setups_dumb(INST, data(), ae.dumb_config_for(INST),
                               START, END)
    assert 0 < len(kept) < len(allk), "the weekly gate does nothing"
    for s in kept:
        j = int(np.searchsorted(w["known_at"].to_numpy(),
                                np.datetime64(s.decided_t), "right")) - 1
        assert int(w["dir"].iloc[j]) == s.direction


def test_the_top_down_layers_never_read_an_unfinished_higher_bar():
    cfg = ae.dumb_config_for(INST, context_tfs=("1w", "1d"))
    setups = ae.find_setups_dumb(INST, data(), cfg, START, END)
    assert setups
    for s in setups[:20]:
        cut = truncate(data(), s.decided_t)
        again = ae.find_setups_dumb(INST, cut, cfg,
                                    s.decided_t - pd.Timedelta(hours=8),
                                    s.decided_t)
        assert [g for g in again if g.decided_t == s.decided_t]


# ------------------------------------------------------------- his doctrine
def test_no_liquidity_sweep_machinery_exists_because_he_calls_it_a_hoax():
    """'this right here is what many would call a LIQUIDITY SWEEP, a fake
    out, an institutional grab ... IT REALLY IS ALMOST A BIG HOAX.'
    — Rua24ytuHuY.txt 00:06:29, 2026-06-04. The TJR book in this repo is
    built on sweeps and none of it may ever be imported here. This is
    doctrine, not an omission."""
    low = BODY.lower()
    for bad in ("sweep", "liquidity", "stop_hunt", "stophunt", "judas",
                "inducement"):
        assert bad not in low, f"{bad} machinery leaked into Alex's engine"


def test_fibonacci_never_appears_because_he_barely_mentions_it():
    """Four mentions in a ten-hour course against 272 for area of interest.
    Nothing in this engine may rest on it."""
    assert "fib" not in BODY.lower()


def test_the_candle_must_be_closed_and_he_says_why():
    """'as soon as that candlestick closes, it is a confirmation. 1 SECOND
    BEFORE IT CLOSES, IT IS AN ENTIRE ANTICIPATION.' — BcWxqfcjk9A.txt
    00:02:53, 2026-04-16. Every decision moment in this file is a bar close
    plus that bar's length."""
    cfg = ae.dumb_config_for(INST, pattern="both")
    step = pd.Timedelta(minutes=ae._TF_MINUTES[cfg.tf])
    for finder in (ae.find_setups_dumb, ae.find_setups_hs):
        for s in finder(INST, data(), cfg, START, END):
            assert s.decided_t == pd.Timestamp(s.signal_t) + step


# ------------------------------------------------------------ size follows
def test_size_still_flows_through_the_one_sizing_function():
    """Quality changes the dollars at risk, never the path they take."""
    src = inspect.getsource(ae.manage)
    assert src.count("size_position(") == 1
    assert "risk_allowance=allow" in src


def test_a_weaker_setup_takes_a_smaller_position():
    """'you can risk more on low-risk trades' — LwMsai2ppKc.txt 00:22:34,
    2026-02-22. And the weakest VALID setup still trades."""
    r = ae.run_instrument(INST, START, END,
                          cfg=ae.dumb_config_for(INST, pattern="both"))
    f = ae.frame({INST: r})
    assert f["quality"].min() < f["quality"].max(), "the dial never moves"
    assert f["quality"].min() > 0.0, "a valid setup was sized to nothing"
    strong = f[f["quality_pts"] >= 2]["risk_dollars"]
    weak = f[f["quality_pts"] == 0]["risk_dollars"]
    if len(strong) and len(weak):
        assert strong.mean() > weak.mean()


def test_turning_quality_sizing_off_puts_every_trade_on_full_size():
    r = ae.run_instrument(INST, START, END, cfg=ae.dumb_config_for(
        INST, pattern="both", size_by_quality=False))
    assert all(t.quality == 1.0 for t in r["trades"])
