"""
test_tjr_bot.py — the bot is only worth running if it cannot see the future.

WHY THIS FILE EXISTS
    Every number tjr_bot produces is fiction unless a bar decides identically
    with and without the bars that came after it. He rejects the ordinary way
    people replay history for exactly this reason, and he is right about it:
    a charting tool shows you a COMPLETED higher-timeframe candle while you
    are standing in the middle of it. `test_truncation_*` below deletes the
    future and demands the same answer.

    Everything else here is the method's own guard rails: the stop landing on
    a chart level and never on a percentage, size falling out of that stop,
    the timing windows, the news gate, the both-indexes-agree veto, and every
    stand-down condition actually firing on real sessions.

Repo style: plain asserts, a TESTS list, a main() runner. No pytest, no
network. Reads the cached parquet files only.
"""

from __future__ import annotations

import datetime as dt
import sys
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
from tjr_bot import (Bar, Config, GapBook, Level, NewsCalendar, SeqState,
                     SymbolDay, TjrBot, TrendTracker, completed_before,
                     daily_bars, decide_at, live_step, resample_tf,
                     two_candle_swings)

REPO = "/Users/wallacechen/cryptobot"
CFG = Config()

# --------------------------------------------------------------- fixtures
_CACHE: dict = {}


def frames(symbol: str) -> dict:
    if symbol not in _CACHE:
        _CACHE[symbol] = {
            "5m": tjr_bot.to_et_frame(
                pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_5m.parquet")),
            "1m": tjr_bot.to_et_frame(
                pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_1m.parquet")),
        }
    return _CACHE[symbol]


def window(day, cfg=CFG, symbols=("SPY", "QQQ")) -> dict:
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    out = {}
    for s in symbols:
        f = frames(s)
        out[s] = {tf: f[tf][(f[tf]["t"] >= lo) & (f[tf]["t"] < hi)]
                  .reset_index(drop=True) for tf in ("5m", "1m")}
    return out


def truncate(data: dict, ts: pd.Timestamp) -> dict:
    """Everything after `ts` deleted. This is what the bot must not need."""
    return {s: {tf: f[f["t"] <= ts].reset_index(drop=True)
                for tf, f in d.items()} for s, d in data.items()}


_REPLAY: dict = {}


def replay(start="2026-01-05", end="2026-07-24", cfg=None):
    """One shared pass over the real sessions, so the integration tests are
    not each paying for their own."""
    cfg = cfg or CFG
    key = (start, end, id(cfg))
    if key in _REPLAY:
        return _REPLAY[key]
    import tjr_replay as R
    data = {s: frames(s) for s in ("SPY", "QQQ")}
    days = R.trading_days(data, pd.Timestamp(start), pd.Timestamp(end))
    bot = TjrBot(cfg, NewsCalendar())
    trades, reasons, results = [], set(), []
    for day in days:
        res = bot.run_day(window(day, cfg), day)
        results.append(res)
        if res["trade"] is not None:
            trades.append(res["trade"])
        reasons |= set(res["stand_down"].values())
    _REPLAY[key] = (bot, trades, reasons, days, results)
    return _REPLAY[key]


def mk(rows) -> pd.DataFrame:
    """rows: (minute_offset, o, h, l, c) on a 5-minute grid from 09:30."""
    base = pd.Timestamp("2026-03-02 09:30")
    return pd.DataFrame([{"t": base + pd.Timedelta(minutes=m), "open": o,
                          "high": h, "low": l, "close": c}
                         for m, o, h, l, c in rows])


# ============================================================ 1. CAUSALITY
def test_truncation_higher_timeframe_bar_is_invisible_until_it_closes():
    """A 4-hour candle starting at 08:00 does not exist at 10:00. This is the
    single defect he objects to in ordinary historical replay."""
    d5 = frames("SPY")["5m"]
    d5 = d5[(d5["t"] >= "2026-03-02") & (d5["t"] < "2026-03-04")]
    h4 = resample_tf(d5, 240)
    now = pd.Timestamp("2026-03-02 10:00")
    seen = completed_before(h4, now)
    assert len(seen) > 0, "no completed 4-hour bars at all"
    assert (seen["close_t"] <= now).all(), "a 4-hour bar leaked before it closed"
    unfinished = h4[(h4["t"] <= now) & (h4["close_t"] > now)]
    assert len(unfinished) == 1, "expected exactly one bar in progress"
    assert unfinished["t"].iloc[0] not in set(seen["t"]), \
        "the bar we are standing inside was treated as complete"

    dl = daily_bars(d5)
    seen_d = completed_before(dl, now)
    assert pd.Timestamp("2026-03-02") not in set(seen_d["t"]), \
        "today's daily candle was visible at 10:00"


def test_truncation_a_pivot_is_stamped_on_the_second_candle():
    """The two-candle swing is knowable the moment the second candle closes,
    and not one bar earlier."""
    d = mk([(0, 10, 12, 9, 11),      # up
            (5, 11, 13, 10, 10.5),   # down  -> HIGH at max(12, 13) = 13
            (10, 10.5, 11, 8, 9),    # down
            (15, 9, 10, 8.5, 9.8)])  # up    -> LOW at min(8, 8.5) = 8
    sh, sl = two_candle_swings(d)
    assert np.isnan(sh[0]) and np.isnan(sl[0])
    assert sh[1] == 13.0, sh
    assert np.isnan(sh[2])
    assert sl[3] == 8.0, sl
    # deleting everything after bar 1 must not change bar 1's answer
    sh2, _ = two_candle_swings(d.iloc[:2].reset_index(drop=True))
    assert sh2[1] == sh[1], "the pivot moved when the future was removed"


def test_truncation_every_real_entry_survives_deleting_the_future():
    """THE test. Re-decide each real entry bar with every later bar deleted.
    Same symbol, same side, same entry, same stop, same swept level."""
    _, trades, _, _, _ = replay()
    assert len(trades) >= 5, f"only {len(trades)} trades to test causality on"
    checked = 0
    for tr in trades:
        day, ts = tr.day, tr.entry_t
        full = decide_at(window(day), day, ts, CFG)
        cut = decide_at(truncate(window(day), ts), day, ts, CFG)
        assert full["entry"] is not None, f"{day:%Y-%m-%d}: entry vanished"
        assert full["entry"] == cut["entry"], (
            f"{day:%Y-%m-%d} decided differently with the future deleted:\n"
            f"  with future    {full['entry']}\n  without future {cut['entry']}")
        checked += 1
    assert checked == len(trades)


def test_truncation_a_stand_down_day_stays_a_stand_down_day():
    """The days he sits out must also be decided without the future."""
    _, trades, _, days, results = replay()
    traded = {t.day for t in trades}
    quiet = [d for d in days if d not in traded][:12]
    assert len(quiet) >= 5
    for day in quiet:
        ts = day + pd.Timedelta(hours=10, minutes=29)
        full = decide_at(window(day), day, ts, CFG)
        cut = decide_at(truncate(window(day), ts), day, ts, CFG)
        assert full["entry"] is None, f"{day:%Y-%m-%d} traded unexpectedly"
        assert cut["entry"] is None, f"{day:%Y-%m-%d} traded once truncated"
        assert full["stand_down"] == cut["stand_down"], (
            f"{day:%Y-%m-%d} gave a different reason without the future:\n"
            f"  {full['stand_down']}\n  {cut['stand_down']}")


def test_truncation_a_decision_mid_morning_does_not_move():
    """Sample decision moments through the entry window, not just the moment
    a trade fired."""
    _, trades, _, _, _ = replay()
    tr = trades[0]
    day = tr.day
    for m in (55, 5, 15, 25):
        ts = day + pd.Timedelta(hours=9 if m == 55 else 10, minutes=m)
        a = decide_at(window(day), day, ts, CFG)
        b = decide_at(truncate(window(day), ts), day, ts, CFG)
        assert a == b, f"{ts} moved when the future was deleted:\n{a}\n{b}"


# ====================================================== 2. THE BUILDING BLOCKS
def test_break_of_structure_needs_a_body_close_strictly_beyond():
    """A wick past the level does nothing. A body closing exactly ON the
    level is not a break either — he rules that one out on tape."""
    tt = TrendTracker()
    tt.update(Bar(pd.Timestamp("2026-01-01 09:30"), 10, 11, 9.5, 10.5))   # up
    tt.update(Bar(pd.Timestamp("2026-01-01 09:35"), 10.5, 10.8, 9, 9.2))  # down
    assert tt.mrh == 11.0
    # a wick above 11, closing below -> nothing
    assert tt.update(Bar(pd.Timestamp("2026-01-01 09:40"), 9.2, 11.5, 9.1, 10.9)) == 0
    assert tt.state == 0
    # closing exactly on 11 -> still nothing
    assert tt.update(Bar(pd.Timestamp("2026-01-01 09:45"), 10.9, 11.2, 10.8, 11.0)) == 0
    # closing strictly above -> a break
    assert tt.update(Bar(pd.Timestamp("2026-01-01 09:50"), 11.0, 11.4, 10.9, 11.1)) == +1
    assert tt.state == +1


def test_a_higher_low_inside_a_downtrend_changes_nothing():
    """Only the monitored extreme matters. He spends a full minute on this
    because his students keep flipping their bias on it."""
    tt = TrendTracker()
    tt.state = -1
    tt.mrh, tt.mrl = 20.0, 10.0
    b = Bar(pd.Timestamp("2026-01-01 09:30"), 12, 13, 11, 12.5)   # a higher low
    assert tt.update(b) == 0
    assert tt.state == -1


def test_equilibrium_anchors_to_the_most_recent_swings_only():
    tt = TrendTracker()
    tt.mrh, tt.mrl = 100.0, 90.0
    assert tt.equilibrium() == 95.0
    tt.mrh = 110.0                       # a newer high must re-anchor it
    assert tt.equilibrium() == 100.0


def test_a_fair_value_gap_dies_on_a_close_through_it_never_on_a_wick():
    g = GapBook(5)
    t = pd.Timestamp("2026-01-01 09:30")
    g.update(Bar(t, 10, 10.5, 9.9, 10.4))
    g.update(Bar(t + pd.Timedelta(minutes=5), 10.4, 12.0, 10.4, 11.9))
    g.update(Bar(t + pd.Timedelta(minutes=10), 11.9, 12.5, 11.0, 12.2))
    assert len(g.gaps) == 1 and g.gaps[0].direction == +1
    assert (g.gaps[0].bottom, g.gaps[0].top) == (10.5, 11.0)
    # a wick through the bottom, closing above it -> still alive, no signal
    assert g.update(Bar(t + pd.Timedelta(minutes=15), 12.2, 12.3, 10.2, 10.7)) == 0
    assert len(g.gaps) == 1
    # a close below the bottom -> dead, and that death IS the inversion
    assert g.update(Bar(t + pd.Timedelta(minutes=20), 10.7, 10.8, 10.0, 10.1)) == -1
    assert not [x for x in g.gaps if x.direction > 0], \
        "the bullish gap survived a close through its bottom"


def test_overlapping_wicks_are_not_a_gap():
    g = GapBook(5)
    t = pd.Timestamp("2026-01-01 09:30")
    g.update(Bar(t, 10, 11.0, 9.9, 10.9))
    g.update(Bar(t + pd.Timedelta(minutes=5), 10.9, 12.0, 10.8, 11.9))
    g.update(Bar(t + pd.Timedelta(minutes=10), 11.9, 12.5, 10.5, 12.2))
    assert g.gaps == [], "the third candle's wick reached back into the first"


def test_a_gap_is_never_formed_across_a_time_hole():
    """SPY stops trading at 20:00 and reopens at 04:00. The overnight jump is
    not a three-candle fair value gap."""
    g = GapBook(5)
    t = pd.Timestamp("2026-01-01 19:50")
    g.update(Bar(t, 10, 10.5, 9.9, 10.4))
    g.update(Bar(t + pd.Timedelta(minutes=5), 10.4, 10.6, 10.3, 10.5))
    g.update(Bar(pd.Timestamp("2026-01-02 04:00"), 12, 12.5, 11.8, 12.2))
    assert g.gaps == [], "an overnight hole was read as a fair value gap"


# ============================================== 3. THE STOP, AND THE SIZE
def test_the_stop_sits_on_the_sweep_and_never_on_a_percentage():
    """The stop is the price that proves the idea wrong: beyond the furthest
    price reached while the level was being taken, plus a spread buffer.
    Never a distance, never a percentage."""
    _, trades, _, _, _ = replay()
    ratios = []
    for tr in trades:
        buf = CFG.stop_buffer_pct_of_price * tr.entry
        if tr.direction < 0:
            assert tr.stop > tr.entry, "a short's stop must sit above the entry"
            anchor = tr.stop - buf
            assert anchor >= tr.level_price - 1e-6, (
                "a short's stop is not beyond the swept high")
        else:
            assert tr.stop < tr.entry
            anchor = tr.stop + buf
            assert anchor <= tr.level_price + 1e-6, (
                "a long's stop is not beyond the swept low")
        assert tr.stop != tr.entry, "the stop was placed at the entry"
        ratios.append(tr.risk_per_share / tr.entry)
    assert len(set(round(r, 6) for r in ratios)) > 1, (
        "every stop was the same fraction of price — that is a percentage "
        "stop wearing a chart's clothes")
    assert max(ratios) / min(ratios) > 2, (
        f"stop distances barely varied ({min(ratios):.5f}..{max(ratios):.5f})")


def test_size_falls_out_of_the_stop():
    """Shares = dollars risked / stop distance, then clamped to the buying
    power the broker reports. A clamped trade must say so."""
    bot, trades, _, _, _ = replay()
    for tr in trades:
        assert abs(tr.shares * tr.risk_per_share - tr.risk_dollars) < 1e-6
        assert abs(tr.shares * tr.entry - tr.notional) < 1e-6
        if tr.clamped:
            assert tr.risk_dollars < tr.risk_wanted - 1e-9, (
                "flagged as clamped but nothing was clamped")
            assert tr.notional <= CFG.buying_power_multiple * 1e9
        else:
            assert abs(tr.risk_dollars - tr.risk_wanted) < 1e-6, (
                "unclamped size did not equal the 1% target")
    assert any(t.clamped for t in trades), (
        "no trade was ever clamped by buying power — the clamp is untested")


def test_the_double_size_tier_ships_disabled():
    assert Config().double_size_enabled is False
    src = open(f"{REPO}/tjr_bot.py").read()
    assert "double_size_enabled" in src
    assert "if cfg.double_size_enabled" not in src and \
           "if self.cfg.double_size_enabled" not in src, (
        "something reads the double-size tier — it must stay dead")


def test_half_size_on_a_news_day():
    """Half size on news days and holidays, applied before the clamp."""
    _, trades, _, _, _ = replay()
    tr = trades[0]
    news = NewsCalendar(extra_derisk={tr.day.date()})
    bot = TjrBot(CFG, news)
    res = bot.run_day(window(tr.day), tr.day)
    assert res["derisk"] is True
    t2 = res["trade"]
    assert t2 is not None, "the de-risk day stopped trading instead of halving"
    assert abs(t2.risk_wanted - tr.risk_wanted / 2) < 1e-6, (
        f"de-risk did not halve the intended risk: "
        f"{t2.risk_wanted} vs {tr.risk_wanted}")


# =================================================== 4. THE TIMING WINDOWS
def test_no_entry_before_0950_or_after_1030():
    """09:30 to 09:50 is the manipulation window and he does not enter in it.
    10:30 is the hard cut-off."""
    _, trades, _, _, _ = replay()
    for tr in trades:
        assert tr.entry_t.time() >= CFG.instrument.manip_end_t, (
            f"{tr.day:%Y-%m-%d} entered at {tr.entry_t:%H:%M}, inside the "
            f"manipulation window")
        assert tr.entry_t.time() < CFG.instrument.cutoff_t, (
            f"{tr.day:%Y-%m-%d} entered at {tr.entry_t:%H:%M}, past 10:30")


def test_nothing_is_ever_entered_in_pre_market():
    """"Do we want to be entering during pre-market? The answer is always
    going to be no." The SWEEP may sit in pre-market — step431 12.2 step 7,
    "if I see that liquidity has already been swept during pre-market and
    we're already reacting off of it... that was the liquidity sweep for the
    day". The ENTRY never may."""
    _, trades, _, _, _ = replay()
    for tr in trades:
        assert tr.entry_t.time() >= CFG.instrument.open_t
        assert tr.entry_t.time() >= CFG.instrument.manip_end_t, (
            "an entry landed inside the manipulation window")


def test_a_pre_market_sweep_only_carries_forward_if_price_already_reacted():
    """His discriminator, verbatim: "already swept during pre-market AND WE'RE
    ALREADY REACTING OFF OF IT". With the reaction requirement removed the
    carve-out must produce MORE setups — if it does not, the reaction test is
    not being applied."""
    import dataclasses
    _, trades, _, _, _ = replay()
    carried = [t for t in trades if t.swept_at.time() < CFG.instrument.open_t]
    off = dataclasses.replace(CFG, premarket_sweep_carries_forward=False)
    _, without, _, _, _ = replay(cfg=off)
    assert carried, "the pre-market carve-out never fired"
    assert len(without) < len(trades), (
        "switching the pre-market carve-out off changed nothing")


def test_the_1030_cutoff_actually_removes_trades():
    """Move the cut-off back to 10:00 and trades must disappear. If nothing
    changes, the clock is not being read."""
    _, trades, _, _, _ = replay()
    late = [t for t in trades if t.entry_t.time() >= dt.time(10, 0)]
    assert late, "no trade after 10:00 to test the cut-off with"
    tr = late[0]
    import dataclasses
    early_inst = dataclasses.replace(CFG.instrument, cutoff_t=dt.time(10, 0))
    cfg = dataclasses.replace(CFG, instrument=early_inst)
    res = TjrBot(cfg, NewsCalendar()).run_day(window(tr.day, cfg), tr.day)
    assert res["trade"] is None, "an entry after 10:00 survived a 10:00 cut-off"


def test_a_position_is_flat_by_the_close():
    _, trades, _, _, _ = replay()
    for tr in trades:
        assert tr.outcome, f"{tr.day:%Y-%m-%d} was never closed"
        assert tr.exit_t.time() <= dt.time(16, 0), "held past the close"


# ======================================================= 5. THE NEWS GATE
def test_cpi_ppi_fomc_and_nfp_block_the_whole_day():
    n = NewsCalendar()
    found = set()
    for d in pd.date_range("2026-01-01", "2026-12-31"):
        tag = n.blocks(d.date())
        if tag:
            found.add(tag)
    # the real calendar returns the publishing agency's own release name
    for want in ("Consumer Price Index", "Producer Price Index",
                 "FOMC Statement", "Employment Situation"):
        assert want in found, f"{want} never blocks a day"
    # BLS's own 2026 schedule, not a rhythm: the March jobs report lands on
    # Friday the 6th and the March consumer price report on WEDNESDAY the 11th
    assert n.blocks(dt.date(2026, 3, 6)) == "Employment Situation"
    assert n.blocks(dt.date(2026, 3, 11)) == "Consumer Price Index"
    # and an ordinary Tuesday is not blocked
    assert n.blocks(dt.date(2026, 3, 24)) is None
    # the gate can still be switched off for an A/B run
    assert NewsCalendar(rules=False).blocks(dt.date(2026, 3, 11)) is None


def test_a_blocked_day_produces_no_trade_and_says_why():
    _, trades, _, _, _ = replay()
    tr = trades[0]
    news = NewsCalendar(extra_block={tr.day.date()})
    res = TjrBot(CFG, news).run_day(window(tr.day), tr.day)
    assert res["trade"] is None, "traded on a blocked news day"
    assert all("news gate" in v for v in res["stand_down"].values()), \
        res["stand_down"]


# ============================================ 6. BOTH INDEXES MUST AGREE
def test_the_two_indexes_must_agree_on_the_five_minute():
    """If the two indexes are telling different stories the market is
    indecisive and there is no trade. This gate has no counterpart in the
    older material and is a real reason his trade count is low."""
    day = pd.Timestamp("2026-03-02")
    leg = SymbolDay("SPY", frames("SPY")["5m"], frames("SPY")["1m"], day,
                    CFG, NewsCalendar(rules=False), False)
    leg.seq = SeqState(stage="confirmed", trade_dir=-1)
    leg.t5.state = -1
    leg.check_index_gate(+1)             # the other index is bullish
    assert leg.seq.index_gate_ok is False, "a disagreeing pair was let through"
    leg.check_index_gate(-1)             # now they agree
    assert leg.seq.index_gate_ok is True, "an agreeing pair was blocked"
    # they may align later in the session, and that is fine
    leg.check_index_gate(+1)
    assert leg.seq.index_gate_ok is False


def test_the_index_veto_removes_real_trades():
    """Switching the veto off must let more trades through. If the count does
    not move, the veto is not wired to anything."""
    with_veto = len(replay()[1])
    cfg = Config(enforce_index_agreement=False)
    import tjr_replay as R
    data = {s: frames(s) for s in ("SPY", "QQQ")}
    days = R.trading_days(data, pd.Timestamp("2026-01-05"),
                          pd.Timestamp("2026-07-24"))
    bot = TjrBot(cfg, NewsCalendar())
    n = sum(1 for d in days
            if bot.run_day(window(d, cfg), d)["trade"] is not None)
    assert n > with_veto, (
        f"turning the veto off changed nothing ({n} vs {with_veto})")


# ================================================ 7. THE STAND-DOWNS FIRE
def test_every_stand_down_condition_fires_on_real_sessions():
    """These days ARE the method. Each of these reasons must appear at least
    once across the replay, or a filter is present in name only."""
    _, _, reasons, days, _ = replay()
    joined = " || ".join(sorted(reasons))
    wanted = [
        "news gate",
        "the daily stands alone",
        "no marked level was pushed through",
        "never turned before 10:30",
        "the two indexes never agreed",
        "the 1-minute never broke back",
    ]
    for w in wanted:
        assert w in joined, f"this stand-down never fired: {w}\nsaw: {joined}"


def test_the_bot_stands_aside_on_most_sessions():
    """He trades 7 to 15 days a month out of about 21. A build that trades
    most days has dropped a stand-down."""
    _, trades, _, days, _ = replay()
    share = len(trades) / len(days)
    assert share < 0.5, (
        f"traded {100*share:.0f}% of sessions — that is more than he does, "
        f"which means a filter is missing")


def test_one_trade_per_day_at_most():
    _, trades, _, days, _ = replay()
    by_day = {}
    for t in trades:
        by_day[t.day] = by_day.get(t.day, 0) + 1
    assert all(v == 1 for v in by_day.values()), by_day


def test_a_level_is_never_sourced_from_the_five_minute_chart():
    """Round 430 measured that on a 5-minute pool the nearest target sits
    CLOSER than the stop, so such a setup is structurally unable to pay.
    Treat one appearing as an error, not a low-quality option."""
    _, trades, _, _, _ = replay()
    allowed = {"1h", "4h", "asia", "london", "new_york", "premarket_ny",
               "prev_day", "15m"}
    for tr in trades:
        assert tr.level_tf in allowed, f"a {tr.level_tf} level was traded"
        assert tr.level_tf != "5m"


# ===================================== 8. THE LOSING-STREAK ESCALATION
def test_two_losing_weeks_tighten_the_filter_and_do_not_stop_trading():
    bot = TjrBot(CFG, NewsCalendar())
    day = pd.Timestamp("2026-03-16")           # a Monday
    w1 = pd.Timestamp("2026-03-02")
    w2 = pd.Timestamp("2026-03-09")
    bot.week_pnl = {w1: -500.0, w2: -300.0}
    bot.refresh_escalation(day)
    assert bot.escalated is True, "two losing weeks did not tighten the filter"
    bot.week_pnl = {w1: -500.0, w2: +300.0}
    bot.refresh_escalation(day)
    assert bot.escalated is False, "one losing week tightened the filter"
    # and it is a FILTER, not a stand-down: nothing switches trading off
    src = open(f"{REPO}/tjr_bot.py").read()
    assert "three-strike" not in src and "consecutive_losses" not in src


def test_the_escalated_filter_demands_both_the_midpoint_and_a_gap():
    day = pd.Timestamp("2026-03-02")
    leg = SymbolDay("SPY", frames("SPY")["5m"], frames("SPY")["1m"], day,
                    CFG, NewsCalendar(rules=False), True)
    assert leg.escalated is True
    lv = Level(100.0, +1, "1h", day)
    leg.ctx.levels = [lv]
    leg.seq = SeqState(stage="confirmed", trade_dir=-1, level=lv,
                       index_gate_ok=True)
    leg.t5.mrh, leg.t5.mrl = 100.0, 90.0        # midpoint 95
    leg.g5.gaps = []                             # no gap live
    leg.on_5m(Bar(day + pd.Timedelta(hours=10), 94, 96, 93, 94))
    assert leg.seq.stage == "confirmed", (
        "the escalated filter accepted the midpoint with no fair value gap")


# ================================================= 9. THE LIVE ENTRY POINT
def test_live_step_refuses_when_the_market_is_shut():
    day = pd.Timestamp("2026-03-02")
    now = day + pd.Timedelta(hours=10)
    for clock in (None, {}, {"is_open": False}):
        out = live_step(window(day), now, 100_000.0, clock=clock)
        assert out["action"] == "stand_down", out
        assert "shut" in out["reason"] or "unreadable" in out["reason"], out


def test_live_step_refuses_before_the_open_and_after_the_cutoff():
    day = pd.Timestamp("2026-03-02")
    clock = {"is_open": True}
    early = live_step(window(day), day + pd.Timedelta(hours=9, minutes=15),
                      100_000.0, clock=clock)
    assert early["action"] == "stand_down" and "pre-market" in early["reason"]
    late = live_step(window(day), day + pd.Timedelta(hours=11),
                     100_000.0, clock=clock)
    assert late["action"] == "stand_down" and "10:30" in late["reason"]


def test_live_step_reproduces_the_replay_entry_on_the_bar_it_fired():
    """The live path and the replay path must be the same decision."""
    _, trades, _, _, _ = replay()
    tr = trades[0]
    now = tr.entry_t + pd.Timedelta(minutes=1)
    out = live_step(truncate(window(tr.day), tr.entry_t), now,
                    CFG.account_start, clock={"is_open": True})
    assert out["action"] == "enter", out
    assert out["symbol"] == tr.symbol
    assert out["direction"] == tr.direction
    assert abs(out["reference_price"] - tr.entry) < 1e-9
    assert abs(out["stop"] - tr.stop) < 1e-9
    assert out["shares"] > 0


def test_live_step_waits_rather_than_re_entering_an_old_signal():
    _, trades, _, _, _ = replay()
    tr = trades[0]
    now = tr.entry_t + pd.Timedelta(minutes=6)
    out = live_step(truncate(window(tr.day), now - pd.Timedelta(minutes=1)),
                    now, CFG.account_start, clock={"is_open": True})
    assert out["action"] != "enter", out


def test_a_market_with_no_bell_has_no_clock_rules_at_all():
    """Crypto later: keep the method, throw away the times. The time rules
    must be ABSENT, never replaced with invented session hours."""
    import dataclasses
    crypto = tjr_bot.Instrument(name="crypto", round_trip_cost_pct=0.001)
    assert crypto.open_t is None and crypto.cutoff_t is None
    assert crypto.manip_end_t is None and crypto.flat_t is None
    assert crypto.prior_session_window is None
    assert crypto.has_closing_bell is False
    t = pd.Timestamp("2026-03-02 03:17")
    assert tjr_bot.too_early(t, crypto) is False
    assert tjr_bot.past_cutoff(t, crypto) is False
    assert tjr_bot.time_to_be_flat(t, crypto) is False
    # and the index's clock still binds, so the check is real
    assert tjr_bot.past_cutoff(pd.Timestamp("2026-03-02 11:00"),
                               CFG.instrument) is True
    # the day boundary is a choice on a 24/7 market: UTC midnight
    assert crypto.day_boundary_hour == 0
    # levels still come off the 1-hour and 4-hour, never the 5-minute
    assert crypto.level_minutes == (60, 240)


def test_every_trade_carries_a_regime_computed_only_from_closed_bars():
    _, trades, _, _, _ = replay()
    allowed = {"trending up", "trending down", "no trend", "unknown"}
    for tr in trades:
        assert tr.regime in allowed, tr.regime
    assert any(t.regime != "unknown" for t in trades), \
        "no trade was ever classified — the regime label is not wired up"


def test_manage_step_takes_half_moves_to_break_even_and_lets_the_rest_run():
    """Half at the first target, the other half spread over the ones after
    it, and something still open after target 2 — "take profit one gets hit,
    take profit two gets hit, take profit three gets hit, we miss out on take
    profit four, and then the rest of our position gets stopped out at break
    even"."""
    p = tjr_bot.LivePosition(symbol="SPY", direction=-1, entry=100.0,
                             stop=102.0, shares=600.0,
                             targets=[98.0, 95.0, 92.0, 90.0])
    t = pd.Timestamp("2026-03-02 10:40")
    assert tjr_bot.manage_step(p, Bar(t, 100, 100.5, 99.0, 99.5))["action"] == "hold"
    out = tjr_bot.manage_step(p, Bar(t, 99.5, 99.6, 97.9, 98.1))
    assert out["action"] == "take_partial"
    assert out["shares"] == 300.0 and out["new_stop"] == 100.0
    # the loop applies it, then the runner is live with the stop at entry
    p.targets_filled, p.stop, p.shares = 1, 100.0, 300.0
    out = tjr_bot.manage_step(p, Bar(t, 98.1, 100.2, 98.0, 100.1))
    assert out["action"] == "close" and out["price"] == 100.0
    assert "break even" in out["reason"], out
    # target 2 takes ANOTHER SLICE, it does not close the position
    p.stop = 100.0
    out = tjr_bot.manage_step(p, Bar(t, 96.0, 96.1, 94.5, 94.8))
    assert out["action"] == "take_partial", out
    assert out["shares"] == 100.0 and out["price"] == 95.0
    # only the last target closes what is left
    p.targets_filled, p.shares = 3, 100.0
    out = tjr_bot.manage_step(p, Bar(t, 91.0, 91.1, 89.5, 89.8))
    assert out["action"] == "close" and out["price"] == 90.0


def test_manage_step_never_widens_the_stop_and_never_adds_size():
    src = open(f"{REPO}/tjr_bot.py").read()
    body = src[src.index("def manage_step("):src.index("def live_step(")]
    for banned in ("+= ", "pos.stop =", "pos.shares ="):
        assert banned not in body, f"manage_step mutates state: {banned!r}"
    assert "new_stop" in body and "pos.entry" in body


def test_the_flat_by_the_close_rule_only_exists_where_there_is_a_bell():
    import dataclasses
    crypto = tjr_bot.Instrument(name="crypto", round_trip_cost_pct=0.001)
    cfg = dataclasses.replace(CFG, instrument=crypto)
    p = tjr_bot.LivePosition("BTC", +1, 100.0, 98.0, 1.0, targets=[105.0, 110.0])
    late = Bar(pd.Timestamp("2026-03-02 23:50"), 101, 101.5, 100.5, 101)
    assert tjr_bot.manage_step(p, late, cfg)["action"] == "hold"
    assert tjr_bot.manage_step(p, late, CFG)["action"] == "close"


def test_nothing_in_the_bot_can_place_an_order():
    src = open(f"{REPO}/tjr_bot.py").read()
    for banned in ("import alpaca", "import blofin", "requests", "_post(",
                   "submit_order", "/v2/orders"):
        assert banned not in src, f"tjr_bot.py references {banned!r}"


# --------------------------------------------------------------- runner
def test_the_new_york_session_levels_are_actually_marked():
    """He names three session pairs, not two: "Asia session highs, Asia session
    lows, London session highs, London session lows, New York highs, New York
    lows. All of these are significant draws on liquidity." Marking only Asia
    and London left the pool with nothing near the open on most mornings."""
    day = pd.Timestamp("2026-03-04")
    d5 = frames("SPY")["5m"]
    d5 = d5[(d5["t"] >= day - pd.Timedelta(days=12)) & (d5["t"] < day + pd.Timedelta(days=1))]
    tags = {lv.tf for lv in tjr_bot.session_levels(d5, day)}
    for want in ("asia", "london", "new_york", "premarket_ny", "prev_day"):
        assert want in tags, f"{want} levels were never marked: {sorted(tags)}"


def test_previous_day_levels_exist_on_a_monday():
    """A fixed one-calendar-day step lands on Sunday every Monday, and the
    previous day's high and low silently vanish on the morning they matter
    most. The lookup must walk back to the last day that actually traded."""
    d5 = frames("SPY")["5m"]
    mondays = 0
    for day in pd.date_range("2026-02-02", "2026-06-29", freq="W-MON"):
        w = d5[(d5["t"] >= day - pd.Timedelta(days=12)) &
               (d5["t"] < day + pd.Timedelta(days=1))]
        if len(w) == 0:
            continue
        tags = {lv.tf for lv in tjr_bot.session_levels(w, day)}
        if "prev_day" not in tags:
            continue
        mondays += 1
    assert mondays >= 15, f"previous-day levels present on only {mondays} Mondays"


def test_the_one_hour_can_stand_in_for_the_four_hour():
    """His three worked mornings: daily+4h+1h all agree -> trade; daily+1h
    agree with the 4-hour chopping -> "something that I would likely be willing
    to take"; the daily alone against both -> "this can go to the bottom of my
    list today"."""
    import dataclasses
    _, with_1h, _, _, _ = replay()
    off = dataclasses.replace(CFG, use_1h_in_direction=False)
    _, without, _, _, _ = replay(cfg=off)
    assert len(with_1h) > len(without), (
        "letting the 1-hour stand in for the 4-hour changed nothing")



# --------------------------------------------------- targets are chart levels
def test_no_target_is_ever_a_multiple_of_what_was_risked():
    """"where are we looking to take profit at? okay, it's at our building
    blocks." (Day 37) The old code, when it found no liquidity pool beyond
    1:1, put target 1 at the 1:1 distance and target 2 at twice what was
    risked. Both are a multiple of the risk, which is the one thing he never
    targets. This asserts no target ever lands on one again."""
    _, trades, _, _, _ = replay()
    assert trades, "no trades to check"
    for tr in trades:
        for p in tr.targets:
            for mult in (1.0, 1.5, 2.0, 2.5, 3.0):
                fake = tr.entry + tr.direction * mult * tr.risk_per_share
                assert abs(p - fake) > 1e-6, (
                    f"{tr.day:%Y-%m-%d} {tr.symbol}: target {p} is exactly "
                    f"{mult}x what was risked, not a chart level")
        assert len(tr.targets) <= CFG.max_targets
        assert len(tr.targets) == len(tr.target_srcs)


def test_every_target_sits_beyond_the_one_before_it():
    _, trades, _, _, _ = replay()
    for tr in trades:
        for a, b in zip(tr.targets, tr.targets[1:]):
            assert (b - a) * tr.direction > 0, (
                f"{tr.day:%Y-%m-%d} targets are not in order: {tr.targets}")


def test_the_four_hour_candle_hangs_from_the_session_open_not_midnight():
    """"this four hour candle won't close for another three and a half hours"
    said at about 09:25 puts his close at 13:00, so the grid is 17:00 / 21:00
    / 01:00 / 05:00 / 09:00 / 13:00 Eastern. On a midnight grid our last
    completed candle at the bell was 04:00-08:00, which on SPY is built out
    of thin overnight prints — the fund has no bars at all before 04:00."""
    assert tjr_bot.US_INDEX_ETF.candle_anchor_hour == 17
    d5 = frames("SPY")["5m"]
    day = pd.Timestamp("2026-07-16")
    d = d5[(d5["t"] >= day - pd.Timedelta(days=4)) &
           (d5["t"] < day + pd.Timedelta(days=1))]
    bell = day + pd.Timedelta(hours=9, minutes=30)
    h4 = tjr_bot.completed_before(
        tjr_bot.resample_tf(d, 240, tjr_bot.US_INDEX_ETF.candle_anchor_hour), bell)
    assert h4["t"].iloc[-1].time() == dt.time(5, 0), h4["t"].iloc[-1]
    assert h4["close_t"].iloc[-1].time() == dt.time(9, 0)
    # and the 1-hour grid is untouched by the offset
    a = tjr_bot.resample_tf(d, 60, 0)["t"].tolist()
    b = tjr_bot.resample_tf(d, 60, 17)["t"].tolist()
    assert a == b, "the offset moved the 1-hour grid, it must not"

TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]


def main():
    print("=" * 78)
    print("test_tjr_bot.py — the method, and proof it cannot see the future")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
            print("  PASS")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
    print("\n" + "=" * 78)
    if failed:
        print(f"{failed}/{len(TESTS)} TEST(S) FAILED")
        sys.exit(1)
    print(f"ALL {len(TESTS)} TESTS PASSED")


if __name__ == "__main__":
    main()
