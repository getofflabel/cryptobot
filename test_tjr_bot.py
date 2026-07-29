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
        # EVERY trade, not res["trade"]. More than one a day is the method
        # now (step452 item 4) and collecting only the first would hide the
        # second from every test in this file.
        trades += res["trades"]
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
        full = decide_at(window(day), day, ts, CFG, escalated=tr.escalated)
        cut = decide_at(truncate(window(day), ts), day, ts, CFG,
                        escalated=tr.escalated)
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
    """STEP465, WHAT SHIPS. Shares x stop distance IS what is at risk, and
    what is at risk is the trade's own share of the account — never more.

    "Me personally I'm risking anywhere from 1 to 3% of my account per trade."
    So the size is worked out off TODAY's stop and the allowance is spent
    exactly. A trade may come in UNDER it, because the venue's own buying
    power can refuse to carry the position; it may never come in over.
    """
    bot, trades, _, _, _ = replay()
    for tr in trades:
        assert abs(tr.shares * tr.risk_per_share - tr.risk_dollars) < 1e-6
        assert abs(tr.shares * tr.entry - tr.notional) < 1e-6
        assert tr.risk_wanted > 0
        assert tr.risk_dollars <= tr.risk_wanted + 1e-6, (
            f"{tr.day:%Y-%m-%d} {tr.symbol} put ${tr.risk_dollars:,.0f} behind "
            f"its stop against an allowance of ${tr.risk_wanted:,.0f} — the "
            f"size is being held still again")
        if not tr.clamped:
            assert abs(tr.risk_dollars - tr.risk_wanted) < 1e-6, (
                "unclamped, the allowance has to be spent exactly")
    assert any(t.clamped for t in trades), (
        "no trade was ever clamped by buying power — the clamp is untested")


def test_the_old_set_size_is_still_reachable_and_still_overspends():
    """The rule step465 replaced, kept whole behind `size_per_trade=False`.

    Held still off the tightest stop, a wider stop today costs proportionally
    more, so the unclamped risk is the trade's share of the day's budget
    multiplied by how much wider today's stop is — never equal to the budget
    except by coincidence. This is what the recorded baseline was taken on and
    it has to keep working, or "off reproduces the old binary" means nothing.
    """
    _, trades, _, _, _ = replay(cfg=OLD_SIZING)
    for tr in trades:
        if tr.clamped:
            continue
        floor = tjr_bot.tightest_stop(tr.symbol) * tr.entry
        assert floor > 0, f"{tr.symbol} has no measured tightest stop"
        want = tr.risk_wanted * tr.risk_per_share / floor
        assert tr.risk_dollars <= want + 1e-6, (
            "risked more than the set size asked for")
    assert any(t.risk_dollars > t.risk_wanted * 1.05 for t in trades), (
        "no trade ever cost more than its share of the day's budget — the set "
        "size is not being held still, it is shrinking to hold the risk flat")


def test_one_trades_size_does_not_depend_on_any_other_trade_that_day():
    """THE POINT OF STEP465, stated as an invariant.

    Every trade puts the same share of the session's opening equity behind its
    stop — the day's first and the day's fourth alike. Nothing it may spend is
    drawn from a pot that earlier trades have run down.
    """
    _, _, _, _, results = replay()
    seen = 0
    for res in results:
        trades = res["trades"]
        if len(trades) < 2:
            continue
        seen += 1
        want = {round(t.risk_wanted, 6) for t in trades}
        assert len(want) == 1, (
            f"{res['day']:%Y-%m-%d} allowed {sorted(want)} on the same day — "
            f"one trade's size still depends on the others")
        for t in trades:
            assert abs(t.budget_share - 1.0) < 1e-9, (
                f"{res['day']:%Y-%m-%d} a trade took a SHARE of a day budget")
    assert seen > 20, "not enough multi-trade days to test this on"


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
def test_no_entry_before_0950_and_none_past_the_go_flat_time():
    """09:30 to 09:50 is the manipulation window and he does not enter in it.
    That end of the window is untouched by step461.

    The OTHER end moved on Wallace's instruction: entries now run through the
    session and stop at `flat_t`, the same instant an open position is closed
    out. No hour was invented in between — an entry past the go-flat time
    would be a position with nowhere to go, and the assertion below is what
    holds the removal to that."""
    _, trades, _, _, _ = replay()
    for tr in trades:
        assert tr.entry_t.time() >= CFG.instrument.manip_end_t, (
            f"{tr.day:%Y-%m-%d} entered at {tr.entry_t:%H:%M}, inside the "
            f"manipulation window")
        assert tr.entry_t.time() < CFG.instrument.flat_t, (
            f"{tr.day:%Y-%m-%d} entered at {tr.entry_t:%H:%M}, past the "
            f"go-flat time")


OLD_CLOCK = Config(entries_run_to_the_close=False)
# step465. The day-budget machinery ships OFF and the whole of it is still
# reachable behind one flag, which is what the tests below hold it to.
OLD_SIZING = Config(size_per_trade=False)
OLD_BOOK = Config(entries_run_to_the_close=False, size_per_trade=False)


def test_the_1030_cutoff_still_binds_when_it_is_switched_back_on():
    """The cut-off ships OFF now, but the machinery that reads it has to
    survive so the before/after is real rather than notional. With the switch
    off, no entry may land past 10:30 — the rule this bot ran until step461."""
    _, trades, _, _, _ = replay(cfg=OLD_CLOCK)
    assert trades, "the old-clock build took no trades to test with"
    for tr in trades:
        assert tr.entry_t.time() < CFG.instrument.cutoff_t, (
            f"{tr.day:%Y-%m-%d} entered at {tr.entry_t:%H:%M} with the cut-off "
            f"switched back on")


def test_removing_the_cutoff_actually_adds_trades_after_1030():
    """Wallace: "man [expletive] the 10:30 cut off then, if you clearly see
    him trade after then the 10:30". If the shipped default does not produce
    entries past 10:30 then the removal is cosmetic."""
    _, trades, _, _, _ = replay()
    _, old, _, _, _ = replay(cfg=OLD_CLOCK)
    late = [t for t in trades if t.entry_t.time() >= dt.time(10, 30)]
    assert late, "the cut-off was removed and nothing entered after 10:30"
    assert len(trades) > len(old), (
        f"removing the cut-off changed nothing: {len(trades)} vs {len(old)}")


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


def test_a_cutoff_that_is_switched_on_is_actually_read():
    """Move the cut-off back to 10:00, with the switch on, and trades must
    disappear. If nothing changes, the clock is not being read at all."""
    _, trades, _, _, _ = replay(cfg=OLD_CLOCK)
    late = [t for t in trades if t.entry_t.time() >= dt.time(10, 0)]
    assert late, "no trade after 10:00 to test the cut-off with"
    tr = late[0]
    import dataclasses
    early_inst = dataclasses.replace(CFG.instrument, cutoff_t=dt.time(10, 0))
    cfg = dataclasses.replace(OLD_CLOCK, instrument=early_inst)
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
    # step461: this counted DAYS on one side and TRADES on the other, which
    # were near enough the same number while the entry window was 40 minutes
    # long and are not once entries run to the close. Both sides count trades.
    n = sum(len(bot.run_day(window(d, cfg), d)["trades"]) for d in days)
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
        "never turned before",
        "the 1-minute never broke back",
    ]
    for w in wanted:
        assert w in joined, f"this stand-down never fired: {w}\nsaw: {joined}"
    # "the two indexes never agreed" is no longer a way a SESSION ends with
    # entries running to the close: given the whole day the two charts always
    # line up eventually. The gate is not gone — it still has to be satisfied
    # before any entry, and `test_the_index_veto_removes_real_trades` shows it
    # still removes trades — it is simply no longer the last word on a day.
    # With the cut-off switched back on it is, and that is checked here so the
    # sentence cannot rot.
    _, _, old_reasons, _, _ = replay(cfg=OLD_CLOCK)
    assert any("the two indexes never agreed" in r for r in old_reasons), (
        f"the index gate never ended a day even with the cut-off on: {old_reasons}")


def test_the_bot_stands_aside_on_most_sessions():
    """He trades 7 to 15 DAYS a month out of about 21, which is 33% to 71% of
    sessions.

    step461 corrected what this counts. It used to divide the TRADE count by
    the session count, which only tracked his number while a 40-minute entry
    window made a second trade almost impossible. More than one trade a day is
    the method — three on Boot Camp 2.0 Day 9, four on Day 12 — so trades over
    sessions has never been the same quantity as his 7 to 15, and with entries
    running to the close the two come apart badly. This counts days, which is
    what he counts."""
    _, trades, _, days, _ = replay()
    traded = len({t.day for t in trades})
    per_month = 21.0 * traded / len(days)
    assert 7.0 <= per_month <= 15.0, (
        f"took a trade on {traded} of {len(days)} sessions = {per_month:.1f} "
        f"days a month, and he says 7 to 15")


def test_more_than_one_trade_a_day_is_the_method():
    """This file used to assert the opposite — one trade a day at most, which
    was a structural consequence of a single `trade` variable rather than a
    rule of his. Boot Camp 2.0 Day 8 and Day 9 make it the method:

        "how to leverage your risk management so you're able to take two
         positions a day like I did today and still be risking the same amount
         as if it were one trade"

    and the counts are on the record — two on Day 8, "we took three trades
    today, absurd for me" on Day 9, four on Day 12. What ends the day is the
    budget, never a count."""
    _, trades, _, days, _ = replay()
    by_day = {}
    for t in trades:
        by_day.setdefault(t.day, []).append(t)
    multi = {d: ts for d, ts in by_day.items() if len(ts) > 1}
    assert multi, ("no session ever took a second trade — the one-a-day stop "
                   "is still in there somewhere")
    src = open(f"{REPO}/tjr_bot.py").read()
    body = src[src.index("def run_day("):src.index("def _second_setup_forming")]
    assert "trade = self._open" not in body, (
        "run_day still holds a single trade")
    # step461: per DAY AND SYMBOL. Two charts firing on the same minute is
    # two setups, not one counted twice, and it only started happening once
    # entries ran past 10:30.
    per_leg = {}
    for t in trades:
        per_leg.setdefault((t.day, t.symbol), []).append(t)
    for (d, sym), ts in per_leg.items():
        assert len({t.entry_t for t in ts}) == len(ts), (
            f"{d:%Y-%m-%d} {sym}: two trades claim the same entry minute")


def test_the_days_budget_is_never_overspent():
    """"if I risk 75 of what I'm willing to risk on the day and I'm only down
    25 of what I'm willing to risk on the day with stop loss at break even on
    this s p trade, cool, then if this one hits stop loss then I'll lose 100
    of what I'm willing to risk on the day." A hundred percent is the
    ceiling, and the outer limit in dollars is the top of his band."""
    _, trades, _, _, results = replay()
    # step461 corrected what this reads, and found a hole while doing it.
    #
    # It used to add up `budget_share` across a day and demand the total stay
    # under 100%. `budget_share` is what a trade was ALLOWED TO TAKE, and that
    # is bounded by `share = min(share, budget.free())` — so the assertion was
    # true by construction and could never have failed. It only looked like a
    # statement about the day because a 40-minute entry window meant trades
    # overlapped and nothing was ever handed back and re-drawn. Once entries
    # run to the close, a winner closes, hands its share back, and a later
    # setup draws on it again: the sum passes 100% while nothing has gone
    # wrong. So allocation is asserted where allocation actually lives.
    # step465 moved this test onto the OLD path, because the day's budget is
    # no longer what ships. It is not deleted: the whole ledger is still
    # reachable behind `size_per_trade=False`, the recorded baseline was taken
    # on it, and a rule nothing tests is a rule that has quietly rotted.
    _, trades, _, _, results = replay(cfg=OLD_SIZING)
    for res in results:
        assert res["budget"].free() >= 0.0, (
            f"{res['day']:%Y-%m-%d} allocated past its budget")
    src = open(f"{REPO}/tjr_bot.py").read()
    assert "share = min(share, budget.free())" in src, (
        "the day's budget no longer bounds what a trade may take")
    assert any(t.budget_share < 0.999 for t in trades), (
        "no trade ever took less than the whole day's budget")


def test_a_day_can_still_lose_more_than_its_budget_and_this_is_why():
    """WHAT THE OLD ASSERTION WAS HIDING, recorded rather than fixed.

    The 100% ceiling binds what a trade may be ALLOCATED. It does not bind
    what the day actually LOSES, and on real sessions the day loses up to
    three times its share budget. That is not a step461 regression — it is the
    same 3.01x with the cut-off switched back on, and it was invisible only
    because the old test summed allocations.

    The cause is HIS rule, not a defect of ours: the size is set off the
    tightest stop the instrument gives and is deliberately NOT resized down
    when today's stop is wider (step436 section 7 step 3), so a wide-stop
    morning risks two or three times the share the ledger recorded. He has
    since added the missing half of that rule — Risk Management & Psychology,
    2026-01-16: "if the stop-loss is like very drastically larger than usual,
    then I'm going to just cut the contract size in half" — and "drastically"
    is a number he never gives. step460 section 6 files it as NEEDS VIDEO and
    section 5 item 4 as a profitability-affecting change that is Wallace's to
    authorise, so step461 measures it and changes nothing.

    STEP465 CLOSED IT, and the test is kept pointed at the OLD path so the
    thing that was wrong stays visible and cannot come back unnoticed. What
    ships now sizes every trade off its own stop, so a trade cannot cost more
    than the share of the account it was allowed — asserted separately in
    `test_size_falls_out_of_the_stop`.

    OURS, NOT HIS — the tolerance below. He gives no ceiling on a day's
    realised loss at all. 3.5x is set just above what the record actually
    does, purely so the number cannot drift further without this failing. It
    is a tripwire, not a rule of his.
    """
    _, _, _, _, results = replay(cfg=OLD_SIZING)
    _, _, _, _, old = replay(cfg=OLD_BOOK)
    def worst(rs):
        return max((r["budget"].held + r["budget"].lost) for r in rs)
    w_new, w_old = worst(results), worst(old)
    assert w_old > 1.0, (
        "the overshoot is being blamed on the clock; with the cut-off back on "
        f"the worst day is {w_old:.2f}, so it is not new")
    assert w_new <= 3.5, (
        f"a day lost {w_new:.2f} times its share budget, which is worse than "
        f"the {w_old:.2f} on the record when this was measured")


def test_the_first_trade_halves_when_a_second_setup_is_forming():
    """"I'm going to go in with like half of what I would want to risk on the
    day knowing damn well that I'm probably going to take a second trade."

    step465: this halving is part of the DAY-BUDGET path and does not ship any
    more — sizing per trade there is no day to split. Pointed at the old path
    so the machinery stays exercised.
    """
    _, trades, _, _, _ = replay(cfg=OLD_SIZING)
    halved = [t for t in trades if t.second_setup_expected]
    assert halved, "the second-setup halving never fired on a real session"
    # step461: the share is `min(half, what the day has left)`, so a trade
    # opened later in a session that has already spent some budget takes LESS
    # than half. Half is the ceiling, and at least one trade has to sit
    # exactly on it or the rule is not being applied at all.
    for t in halved:
        assert t.budget_share <= CFG.first_trade_share_when_second_expected + 1e-9, (
            f"{t.day:%Y-%m-%d} took {t.budget_share:.2f} with a second setup "
            f"forming, which is more than half the day")
    assert any(abs(t.budget_share
                   - CFG.first_trade_share_when_second_expected) < 1e-9
               for t in halved), "no trade ever took exactly half the day"


def test_break_even_hands_the_budget_back():
    """"we lost 50 of what we were willing to lose once take profit one got
    hit, okay, now we're down to like 25 of what we were willing to lose for
    the day... I can now risk an extra 75 of whatever I'm willing to risk on
    the day." His arithmetic, run through DayBudget."""
    b = tjr_bot.DayBudget(account=100_000.0, share_of_account=0.01,
                          outer_share=0.03)
    b.take(0.50, 500.0)
    assert abs(b.free() - 0.50) < 1e-12
    b.to_break_even(0.25, 250.0)
    assert abs(b.free() - 0.75) < 1e-12, "target one did not free his 75%"
    b.take(0.75, 750.0)
    assert abs(b.free()) < 1e-12
    b.release(0.75, 750.0, -1000.0)
    assert abs(b.free()) < 1e-12, "a full loss left budget on the table"


def test_a_red_day_never_halts_trading():
    """Day 12 "Red Day": three losses, then a fourth trade at the same size.
    "if this was a fourth loss I would have been completely okay with it on
    my side." There must be no per-day loss limit anywhere in the bot."""
    src = open(f"{REPO}/tjr_bot.py").read()
    for banned in ("daily_loss_limit", "max_losses_per_day", "stop_for_the_day",
                   "halt_after_loss", "losses_today >"):
        assert banned not in src, f"a red-day halt appeared: {banned!r}"
    # and the losing-WEEKS escalation is untouched: it tightens, never stops
    assert Config().losing_weeks_to_escalate == 2


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
    # step461: 11:00 is inside the window now, so the boundary the live path
    # refuses at is the go-flat time. With the cut-off switched back on it is
    # 10:30 again, and both are checked so neither can rot.
    late = live_step(window(day), day + pd.Timedelta(hours=16),
                     100_000.0, clock=clock)
    assert late["action"] == "stand_down" and "15:55" in late["reason"], late
    old = live_step(window(day, OLD_CLOCK), day + pd.Timedelta(hours=11),
                    100_000.0, clock=clock, cfg=OLD_CLOCK)
    assert old["action"] == "stand_down" and "10:30" in old["reason"], old


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
    """2026-07-28: the boundary MOVED. A poll landing a few minutes after
    the trigger now still gets the entry (`live_entry_grace_minutes`),
    because the live loop takes several minutes to walk four markets and
    the old exact-minute rule silently ate both of the first live session's
    entries. Beyond the grace window the old law still holds: too stale is
    too stale."""
    _, trades, _, _, _ = replay()
    tr = trades[0]
    past_grace = CFG.live_entry_grace_minutes + 1
    now = tr.entry_t + pd.Timedelta(minutes=past_grace)
    out = live_step(truncate(window(tr.day), now - pd.Timedelta(minutes=1)),
                    now, CFG.account_start, clock={"is_open": True})
    assert out["action"] != "enter", out
    # and the grace window itself never spans the truncation guard: a grace
    # entry needs the sim's own trade record, never a bar that has not closed
    assert CFG.live_entry_grace_minutes >= 0


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


def test_manage_step_takes_half_then_half_of_what_is_open_then_runs_the_rest():
    """HIS LADDER, Day 9, said three times in the same words: "take profit one
    right here where I managed 50 of the position, we had take profit two
    right here where I managed ANOTHER FIFTY PERCENT OF THE OPEN POSITION, and
    then I closed the rest of the trade out once we broke structure to the
    downside on the one minute."

    So 50 of the original, then 25 of the original, then a 25 runner that
    sits on no target at all."""
    p = tjr_bot.LivePosition(symbol="SPY", direction=-1, entry=100.0,
                             stop=102.0, shares=600.0,
                             targets=[98.0, 95.0, 92.0, 90.0])
    t = pd.Timestamp("2026-03-02 10:40")
    assert tjr_bot.manage_step(p, Bar(t, 100, 100.5, 99.0, 99.5))["action"] == "hold"
    out = tjr_bot.manage_step(p, Bar(t, 99.5, 99.6, 97.9, 98.1))
    assert out["action"] == "take_partial"
    assert out["shares"] == 300.0 and out["new_stop"] == 100.0
    # the loop applies it, then the rest is live with the stop at entry
    p.targets_filled, p.stop, p.shares = 1, 100.0, 300.0
    out = tjr_bot.manage_step(p, Bar(t, 98.1, 100.2, 98.0, 100.1))
    assert out["action"] == "close" and out["price"] == 100.0
    assert "break even" in out["reason"], out
    # target 2 takes HALF OF WHAT IS OPEN — a quarter of the original — and
    # does not close the position
    p.stop = 100.0
    out = tjr_bot.manage_step(p, Bar(t, 96.0, 96.1, 94.5, 94.8))
    assert out["action"] == "take_partial", out
    assert out["shares"] == 150.0 and out["price"] == 95.0, out
    # the runner. Target 3 takes NOTHING off — it rides through it.
    p.targets_filled, p.shares = 2, 150.0
    out = tjr_bot.manage_step(p, Bar(t, 94.8, 94.9, 91.5, 91.8))
    assert out["action"] == "hold", out
    # it comes off on the opposite break of structure on the 1-minute, which
    # is the thing he does by hand
    out = tjr_bot.manage_step(p, Bar(t, 94.8, 94.9, 93.5, 94.4), bos1=+1)
    assert out["action"] == "close" and out["shares"] == 150.0, out
    assert "1-minute broke structure" in out["reason"], out
    # and the final target still closes whatever is left
    out = tjr_bot.manage_step(p, Bar(t, 91.0, 91.1, 89.5, 89.8))
    assert out["action"] == "close" and out["price"] == 90.0, out


def test_the_target_split_is_fifty_then_half_of_what_is_open():
    """The tail used to be spread evenly and the docstring said so — with four
    targets that was 50 / 16.7 / 16.7 / 16.7. Day 9 answers it."""
    cfg = Config()
    assert tjr_bot.target_fractions(1, cfg) == [0.5]
    assert tjr_bot.target_fractions(2, cfg) == [0.5, 0.25]
    assert tjr_bot.target_fractions(4, cfg) == [0.5, 0.25, 0.0, 0.0]
    assert tjr_bot.target_fractions(5, cfg) == [0.5, 0.25, 0.0, 0.0, 0.0]
    for n in (1, 2, 3, 4, 5):
        assert abs(sum(tjr_bot.target_fractions(n, cfg))
                   + tjr_bot.runner_fraction(n, cfg) - 1.0) < 1e-12
    assert abs(tjr_bot.runner_fraction(4, cfg) - 0.25) < 1e-12
    # four and sometimes five, not three: "we have take profit three right
    # here and then take profit four all the way up here" (Day 9), "I also
    # had several other take profits like four and five" (Day 11)
    assert cfg.max_targets == 5


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


# ============================== THE REPLAY AND THE LIVE PATH SIZE THE SAME
def test_the_replay_and_the_live_path_size_identically():
    """THE MOST IMPORTANT TEST IN THIS FILE, AND IT IS HERE BECAUSE THEY DID
    NOT.

    Until 2026-07-26 there were two sizing rules. `TjrBot._open` sized fresh
    at 1% of equity on every trade, which is what every replay and every
    backtest number this project had ever produced came out of.
    `tjr_alerts.position_size` used his set size, worked out off the tightest
    stop the instrument normally gives and then held still, which is what the
    orders that actually went out used. The two differ by the ratio of
    today's stop to that tightest stop — up to 36 times on DOT — so every
    backtest described a bot nobody was running.

    This takes the trades the REPLAY actually produced and asks the LIVE
    sizing function for a size on exactly the same inputs. Every one must
    come back to the share.

    STEP465 SHARPENED IT, because it was blunter than it looked. Sizing per
    trade at the top of his band asks for more leverage than Alpaca's
    day-trade buying power will carry on nine trades in ten, and BOTH paths
    then land on the venue's ceiling — so the two could have been running
    different rules and this test would still have passed on almost every
    trade. The second pass below takes the ceiling away, which is the only
    way the rules themselves are compared rather than the clamp.
    """
    import tjr_alerts
    _, trades, _, _, _ = replay()
    assert trades, "no trades to compare"
    bp = None
    for tr in trades:
        # exactly the inputs the replay sized from, and nothing else
        acct = tr.sizing_account
        live = tjr_alerts.position_size(
            "sp500", tr.symbol, acct, tr.entry, tr.risk_per_share,
            tjr_bot.tightest_stop(tr.symbol), 1.0,
            risk_pct=tr.risk_wanted / acct,
            buying_power=tr.sizing_buying_power,
            outer_allowance=tr.sizing_outer_allowance)
        assert live["ok"], f"{tr.symbol}: the live path refused to size"
        assert abs(live["units"] - tr.shares) < 1e-6, (
            f"{tr.day:%Y-%m-%d} {tr.symbol}: the replay took "
            f"{tr.shares:,.4f} units and the live path would have sent "
            f"{live['units']:,.4f} — THE TWO PATHS HAVE DRIFTED APART AGAIN")
        assert abs(live["risk_dollars"] - tr.risk_dollars) < 1e-6
        bp = live
    assert bp is not None

    # WITH THE VENUE'S CEILING REMOVED, so the two RULES are what is compared.
    was_clamped = 0
    for tr in trades:
        acct = tr.sizing_account
        mine = tjr_bot.size_position(
            account=acct, entry=tr.entry, stop_distance=tr.risk_per_share,
            risk_allowance=tr.risk_wanted,
            tightest_stop_pct=tjr_bot.tightest_stop(tr.symbol),
            outer_allowance=tr.sizing_outer_allowance,
            hold_size_still=not CFG.size_per_trade)
        live = tjr_alerts.position_size(
            "sp500", tr.symbol, acct, tr.entry, tr.risk_per_share,
            tjr_bot.tightest_stop(tr.symbol), 1.0,
            risk_pct=tr.risk_wanted / acct,
            outer_allowance=tr.sizing_outer_allowance,
            hold_size_still=not CFG.size_per_trade)
        assert abs(live["units"] - mine["units"]) < 1e-6, (
            f"{tr.day:%Y-%m-%d} {tr.symbol}: with no buying-power ceiling the "
            f"replay's rule gives {mine['units']:,.4f} units and the live "
            f"path gives {live['units']:,.4f} — THE TWO RULES HAVE DRIFTED, "
            f"and the clamp was hiding it")
        if tr.clamped:
            was_clamped += 1
    assert was_clamped, (
        "no trade in the sample was clamped, so the second pass proved "
        "nothing that the first did not")


def test_the_desk_can_only_ever_under_size():
    """THE ONE SEAM STEP465 COULD NOT CLOSE, BOUNDED AND WRITTEN DOWN.

    `tjr_desk._size_for` calls `tjr_alerts.position_size` without saying which
    of the two sizing rules it wants, so it gets the default — the old
    held-still rule — while the index book now sizes per trade. tjr_desk.py
    was out of bounds for this round, so instead of leaving that unstated this
    proves the direction of the disagreement: the desk can come in at the
    replay's size or under it, and never over it.

    It holds because the desk DOES forward `outer_allowance`, and sizing per
    trade sets that equal to the allowance itself. Held still, the size is
    `allowance x wider`, then cut back to the allowance whenever `wider` > 1.
    Where `wider` < 1 — today's stop tighter than the tightest this market
    normally gives — the desk would send less. Less is safe. More would not be.

    MEASURED, AND IT IS BETTER THAN THE BOUND: on every trade in the record
    the desk lands on exactly the replay's size, because between the outer
    allowance and Alpaca's 4x day-trade buying power the two rules have
    nowhere left to disagree. Both are asserted — the equality because it is
    what is true today, and the bound because it is what must stay true if a
    stop floor is ever re-measured and the equality stops holding.
    """
    import tjr_alerts
    _, trades, _, _, _ = replay()
    assert trades
    under = 0
    for tr in trades:
        acct = tr.sizing_account
        desk = tjr_alerts.position_size(
            "sp500", tr.symbol, acct, tr.entry, tr.risk_per_share,
            tjr_bot.tightest_stop(tr.symbol), 1.0,
            risk_pct=tr.risk_wanted / acct,
            buying_power=tr.sizing_buying_power,
            outer_allowance=tr.sizing_outer_allowance)
        assert desk["risk_dollars"] <= tr.risk_dollars + 1e-6, (
            f"{tr.day:%Y-%m-%d} {tr.symbol}: the desk would have put "
            f"${desk['risk_dollars']:,.0f} behind the stop where the replay "
            f"put ${tr.risk_dollars:,.0f} — it is now sizing OVER, which is "
            f"the direction that is not safe")
        if desk["risk_dollars"] < tr.risk_dollars - 1e-6:
            under += 1
    assert under == 0, (
        f"the desk came in under the replay on {under} trades. Safe, but it "
        f"used to match exactly on all of them — something moved and the "
        f"orders no longer describe the backtest")


def test_only_one_function_in_the_project_turns_a_stop_into_a_size():
    """The arithmetic lives in tjr_bot.size_position and nowhere else. This
    is the guard that stops a second one growing back: if a sizing formula
    reappears in tjr_alerts, the two paths can silently disagree again and
    nothing else in this file would notice."""
    src = open(f"{REPO}/tjr_alerts.py").read()
    body = src[src.index("def position_size("):src.index("def size_lines(")]
    assert "tjr_bot.size_position(" in body, (
        "tjr_alerts.position_size no longer delegates — it is sizing again")
    for banned in ("risk_pct * account", "(risk_pct * account)",
                   "/ (baseline", "units = ", "units *"):
        assert banned not in body, (
            f"tjr_alerts.position_size does its own arithmetic again: "
            f"{banned!r}")
    bot = open(f"{REPO}/tjr_bot.py").read()
    assert bot.count("def size_position(") == 1
    open_body = bot[bot.index("def _open("):bot.index("def _manage(")]
    assert "size_position(" in open_body, "_open sizes by hand again"
    for banned in ("shares = risk_wanted / rps", "risk_wanted / rps"):
        assert banned not in open_body, f"_open sizes by hand again: {banned!r}"


def test_the_outer_limit_is_the_days_and_not_one_trades():
    """"I only lost 50 percent of what I was willing to risk ON THE DAY,
    that's better than a full you know like one percent down ON THE DAY, two
    percent down or three percent down ON THE DAY." (Day 8) The 3% moved off
    the trade and onto the day."""
    import tjr_alerts
    assert Config().max_day_risk_share == 0.03
    assert tjr_alerts.MAX_DAY_RISK_SHARE_OF_ACCOUNT == 0.03
    src = open(f"{REPO}/tjr_bot.py").read()
    assert "max_day_risk_share" in src
    # the ledger, not the trade, is what the outer limit is checked against
    assert "budget.outer_free()" in src and "outer_allowance=outer" in src, (
        "the outer limit is not being read off the day's ledger")
    b = tjr_bot.DayBudget(account=100_000.0, share_of_account=0.01,
                          outer_share=0.03)
    assert b.outer_free() == 3_000.0
    b.take(0.5, 2_500.0)
    assert b.outer_free() == 500.0, (
        "a second trade could still spend the whole outer limit on its own")


# ==================================================== step456: THE NEWEST HIM
#
# Three rules out of his newest videos, every one of them switchable, every
# one of them OFF by default. The first test below is the load-bearing one:
# with the switches off this file has to decide exactly what it decided on
# 2026-07-26, trade for trade, or the before/after Wallace asked for is
# comparing two different bots rather than two teachings.


def test_everything_off_reproduces_the_recorded_baseline_trade_for_trade():
    """`step456_baseline.json` was written by the binary BEFORE step456 was
    added — a photograph of the old bot over 251 real sessions, not a
    re-description of the new one. Every trade, every field, both accounts.

    step461 note: this is now run with `entries_run_to_the_close=False`,
    because that switch ships True on Wallace's instruction and so `Config()`
    no longer describes the photographed binary. 2026-07-27: bias parts 2+3
    also ship True now, so they too must be said out loud here to describe
    the photographed binary."""
    import step456_baseline as SB
    want = SB.as_recorded(SB.load())
    got = SB.as_recorded(SB.run(Config(bias_yields_to_a_divergence=False,
                                       bias_flips_on_a_gap_invalidation=False,
                                       **SB.OLD_CLOCK)))
    assert len(want["trades"]) == len(got["trades"]), (
        f"the baseline took {len(want['trades'])} trades, this build takes "
        f"{len(got['trades'])} with every step456 switch off")
    for i, (a, b) in enumerate(zip(want["trades"], got["trades"])):
        assert a == b, f"trade {i} moved:\n  was {a}\n  now {b}"
    assert want["account_end"] == got["account_end"]
    assert want["stand_down"] == got["stand_down"], (
        "the same sessions stood down for different reasons")


def test_every_step456_switch_ships_off():
    c = Config()
    off = ["smt_enabled", "smt_picks_the_instrument", "smt_in_confirmation_menu",
           "smt_in_continuation_menu_after_2b", "extension_79_enabled",
           "trigger_menu_1m_gap_inversion", "require_fresh_5m_sweep_after_open",
           "invalidate_on_close_beyond_continuation"]
    for name in off:
        assert getattr(c, name) is False, f"{name} does not ship off"
    on = Config.newest_teaching()
    for name in off:
        assert getattr(on, name) is True, f"newest_teaching() left {name} off"
    # and nothing else moved between the two halves
    for f in ("risk_pct_normal", "max_day_risk_share", "partial_fraction",
              "second_partial_fraction", "max_targets", "losing_weeks_to_escalate",
              "stop_buffer_pct_of_price", "enforce_index_agreement",
              "enforce_daily_bias_side", "double_size_enabled"):
        assert getattr(c, f) == getattr(on, f), (
            f"newest_teaching() changed {f}, which is not one of the three "
            f"things step456 was allowed to touch")


def test_the_index_agreement_veto_survives_smt():
    """step454 checked this specifically and it survives: the veto is about
    the two charts' 5-minute TREND STATE, a divergence is about a single
    swing point taken on one chart and not the other. 120, in the same
    coaching session that explains SMT: "we want both to be confirmed." """
    import inspect
    assert Config().enforce_index_agreement is True
    assert Config.newest_teaching().enforce_index_agreement is True
    assert "check_index_gate" in inspect.getsource(tjr_bot.TjrBot.run_day), (
        "the veto was removed from run_day")
    assert "enforce_index_agreement" in inspect.getsource(
        SymbolDay.check_index_gate)


# --------------------------------------------------------- 1. SMT divergence
def test_a_divergence_is_a_lower_high_against_a_higher_high():
    """115: "a bearish SMT divergence is formed when we are in an uptrend and
    one index forms a high then a LOWER high. Okay, and the other index forms
    a high then a HIGHER high." And bullish: "one index makes a low, then a
    lower low, and the other index makes a low, then a higher low." """
    t0 = pd.Timestamp("2026-06-10 09:35")
    t1 = pd.Timestamp("2026-06-10 09:55")

    def log_with(highs=(), lows=()):
        lg = tjr_bot.SwingLog(5)
        for p, t in highs:
            lg.highs.append(tjr_bot.Swing(p, t, +1, p))
        for p, t in lows:
            lg.lows.append(tjr_bot.Swing(p, t, -1, p))
        return lg

    # bearish: A makes the lower high, so A is LEADING
    a = log_with(highs=[(100.0, t0), (99.0, t1)])
    b = log_with(highs=[(200.0, t0), (201.0, t1)])
    s = tjr_bot.smt_between("A", a, "B", b, 2, 5)
    assert s is not None and s.direction == -1
    assert s.leading == "A" and s.lagging == "B", (
        "leading must be the chart that BROKE the trend — 115: "
        '"why is this index the leading index? because this index is telling '
        'us the future"')

    # bullish: B makes the higher low, so B is LEADING
    a = log_with(lows=[(100.0, t0), (99.0, t1)])
    b = log_with(lows=[(200.0, t0), (201.0, t1)])
    s = tjr_bot.smt_between("A", a, "B", b, 2, 5)
    assert s is not None and s.direction == +1
    assert s.leading == "B" and s.lagging == "A"

    # both did the same thing: no divergence, the two charts agree
    a = log_with(highs=[(100.0, t0), (99.0, t1)])
    b = log_with(highs=[(200.0, t0), (199.0, t1)])
    assert tjr_bot.smt_between("A", a, "B", b, 2, 5) is None


def test_the_two_swings_have_to_line_up_in_time():
    """"this high was formed at the same time that this one was, but then this
    one forms a higher high at the same time that this lower high was getting
    formed." With the clock on screen: "it's literally happening at the exact
    same time 935 935." """
    t0 = pd.Timestamp("2026-06-10 09:35")
    t1 = pd.Timestamp("2026-06-10 09:55")

    def log_with(highs):
        lg = tjr_bot.SwingLog(5)
        for p, t in highs:
            lg.highs.append(tjr_bot.Swing(p, t, +1, p))
        return lg

    a = log_with([(100.0, t0), (99.0, t1)])
    far = log_with([(200.0, t0), (201.0, t1 + pd.Timedelta(minutes=60))])
    assert tjr_bot.smt_between("A", a, "B", far, 2, 5) is None, (
        "two swings an hour apart were treated as simultaneous")
    near = log_with([(200.0, t0), (201.0, t1 + pd.Timedelta(minutes=10))])
    assert tjr_bot.smt_between("A", a, "B", near, 2, 5) is not None


def test_a_divergence_needs_a_sweep_and_the_days_bias():
    """Two gates, both his. SMT_Divergence_Explained: "OUTSIDE of sweeping out
    draws and liquidity, these things will show up all the time and will be
    pretty much like USELESS to us." 044: "let's say our daily bias is bullish
    but we see a bearish smt Divergence are we going to want to take that? NO."
    """
    day = pd.Timestamp("2026-06-10")
    cfg = Config(smt_enabled=True)
    data = window(day, cfg)
    leg = SymbolDay("SPY", data["SPY"]["5m"], data["SPY"]["1m"], day, cfg,
                    NewsCalendar(), False)
    smt = tjr_bot.Smt(direction=-1, leading="QQQ", lagging="SPY",
                      formed_at=day + pd.Timedelta(hours=10), minutes=5,
                      leading_prev=1.0, leading_now=0.0,
                      lagging_prev=1.0, lagging_now=2.0)
    leg.seq = SeqState()                     # waiting_for_sweep
    assert leg.smt_live(smt) is False, "a divergence counted with no sweep behind it"
    leg.ctx.bias_dir = +1
    leg.seq = SeqState(stage="swept", trade_dir=-1,
                       swept_at=day + pd.Timedelta(hours=9, minutes=45))
    assert leg.smt_live(smt) is False, "a bearish divergence counted on a bullish day"
    leg.ctx.bias_dir = -1
    assert leg.smt_live(smt) is True
    # and one that formed long before the sweep is not this sweep's divergence
    stale = dataclasses_replace(smt, formed_at=day + pd.Timedelta(hours=4))
    assert leg.smt_live(stale) is False


def test_the_divergence_picks_the_leading_chart_and_only_ever_refuses():
    """120: "me personally I use it to determine WHAT INDEX I should take the
    trade off of." 100: "That's why we always take the LEADING index. Before I
    used to take the lagging index, but I changed that around." """
    day = pd.Timestamp("2026-06-10")
    cfg = Config(smt_enabled=True, smt_picks_the_instrument=True)
    data = window(day, cfg)
    leg = SymbolDay("SPY", data["SPY"]["5m"], data["SPY"]["1m"], day, cfg,
                    NewsCalendar(), False)
    leg.ctx.bias_dir = -1
    leg.seq = SeqState(stage="pullback", trade_dir=-1,
                       swept_at=day + pd.Timedelta(hours=9, minutes=45))
    leg.smt5 = tjr_bot.Smt(direction=-1, leading="QQQ", lagging="SPY",
                           formed_at=day + pd.Timedelta(hours=10), minutes=5,
                           leading_prev=1.0, leading_now=0.0,
                           lagging_prev=1.0, lagging_now=2.0)
    assert leg.smt_forbids_this_chart(), "SPY is the lagging chart and was allowed"
    leg.smt5 = tjr_bot.Smt(direction=-1, leading="SPY", lagging="QQQ",
                           formed_at=day + pd.Timedelta(hours=10), minutes=5,
                           leading_prev=1.0, leading_now=0.0,
                           lagging_prev=1.0, lagging_now=2.0)
    assert leg.smt_forbids_this_chart() is None, "SPY is the leading chart"
    # with the switch off it never refuses anything
    leg.cfg = Config(smt_enabled=True)
    leg.smt5 = tjr_bot.Smt(direction=-1, leading="QQQ", lagging="SPY",
                           formed_at=day + pd.Timedelta(hours=10), minutes=5,
                           leading_prev=1.0, leading_now=0.0,
                           lagging_prev=1.0, lagging_now=2.0)
    assert leg.smt_forbids_this_chart() is None


def test_a_divergence_needs_exactly_two_charts():
    """"if you guys are trading anything besides the S&P 500 in NASDAQ this is
    not going to apply to you... this only applies to indexes." A run handed
    one symbol — which is every crypto run — cannot produce one at all, and
    that is structural rather than a switch."""
    bot = TjrBot(Config(smt_enabled=True), NewsCalendar())
    assert bot._smt({}, ["ONLY"], 5) is None
    assert bot._smt({}, ["A", "B", "C"], 5) is None


def test_a_divergence_never_reaches_a_size_a_stop_or_a_target():
    """120: "It doesn't tell me to take a trade. It doesn't tell me to
    execute." The completion draw from 115 is recorded and deliberately not
    fed to build_targets — step453 rebuilt the ladder and this round does not
    touch it."""
    import inspect
    for fn in (tjr_bot.size_position, tjr_bot.build_targets,
               tjr_bot.building_blocks, tjr_bot.target_fractions,
               tjr_bot.manage_step, tjr_bot.TjrBot._manage):
        src = inspect.getsource(fn)
        for banned in ("smt", "Smt", "extension_79", "79"):
            assert banned not in src, (
                f"{fn.__name__} reads {banned!r} — a bias input reached the "
                f"money")
    open_src = inspect.getsource(tjr_bot.TjrBot._open)
    assert "smt_completion" in open_src and "completion" in open_src
    assert "targets=targets" in open_src, "targets stopped coming from build_targets"


# ------------------------------------------------------ 2. the 79% extension
def test_the_79_percent_sits_inside_the_leg_and_needs_a_body_close():
    """099, bearish: "we take it from the LOW UP TO THE HIGH and we just wait
    for a candlestick closure UNDERNEATH the 79% extension." Bullish: "Take it
    from this HIGH DOWN TO THIS LOW. Did we close ABOVE the 79% extension?"
    And 082 fixes the arithmetic: "you take it from the high down to the low
    AS IF YOU GUYS ARE DRAWING A EQUILIBRIUM" — so it is 79% of the same leg
    equilibrium halves, a deep retracement inside it, never a projection."""
    # a short: the leg ran 100 -> 200, so the level sits at 200 - 0.79*100
    lvl = tjr_bot.extension_79_level(origin=100.0, extreme=200.0, trade_dir=-1)
    assert abs(lvl - 121.0) < 1e-9, lvl
    assert 100.0 < lvl < 200.0, "the level fell outside the leg"
    # exactly 21% of the leg up from where the leg started
    assert abs((lvl - 100.0) / 100.0 - 0.21) < 1e-9
    # a long: the leg ran 200 -> 100
    lvl = tjr_bot.extension_79_level(origin=200.0, extreme=100.0, trade_dir=+1)
    assert abs(lvl - 179.0) < 1e-9, lvl
    # a wick through it is not enough — 080: "we POKED underneath the 79%
    # extension. I would love to see NASDAQ CLOSE underneath that."
    t = pd.Timestamp("2026-06-10 09:55")
    poke = Bar(t, 130, 131, 118, 125)          # low went through, close did not
    assert tjr_bot.closed_past_79(poke, 121.0, -1) is False
    shut = Bar(t, 130, 131, 118, 120)
    assert tjr_bot.closed_past_79(shut, 121.0, -1) is True


def test_the_79_percent_is_never_a_target_and_never_a_stop():
    """086: "we're not just taking profits off of random draws, okay? We're
    NOT just taking profits off of Fibonacci extensions." It is a confirmation
    and nothing else."""
    import inspect
    for fn in (tjr_bot.build_targets, tjr_bot.building_blocks):
        assert "79" not in inspect.getsource(fn)
    src = inspect.getsource(tjr_bot.TjrBot._open)
    assert "stop = s.sweep_extreme + buf" in src, "the stop anchor moved"


def test_the_79_percent_only_ever_adds_trades():
    """He ranks it last himself, 066: "I rarely use this one, you guys can
    very well do without this." So it widens a menu; it can never be the
    reason a trade is refused."""
    a = len(replay_trades(Config()))
    b = len(replay_trades(Config(extension_79_enabled=True)))
    assert b >= a, f"the 79% extension REMOVED trades: {a} -> {b}"
    assert b > a, "the 79% extension changed nothing over a whole year"


# --------------------------------------------------- 3. his six-step entry
def test_the_one_minute_menu_has_all_four_of_his_options():
    """112: "we're looking for a one minute confirmation confluence... VIA THE
    SAME EXACT CONFIRMATION CONFLUENCE that we had had before. So break of
    structure inverse for value gap 79% extension on the Fibonacci or an SMT
    divergence and then boom from there plain as simple we can enter." """
    import inspect
    src = inspect.getsource(SymbolDay.on_1m)
    for want in ('"1-minute break of structure"', '"1-minute gap inversion"',
                 '"1-minute close beyond the 79% extension"', "self.smt1"):
        assert want in src, f"{want} is not on the 1-minute menu"
    # and it is an OR — "we don't need every single one of these to happen. We
    # just need one" — so each route returns on its own
    assert src.count("return True") == 4


def test_the_menu_is_an_or_and_every_route_fires_over_a_year():
    """Each of the four has to actually be reachable on real sessions, or the
    menu is wider on paper than in the market."""
    trades = replay_trades(Config.newest_teaching())
    kinds = {t.trigger_kind for t in trades}
    for want in ("1-minute break of structure", "1-minute gap inversion",
                 "1-minute close beyond the 79% extension"):
        assert want in kinds, f"{want} never fired in a year: {sorted(kinds)}"
    assert any("SMT divergence" in k for k in kinds), (
        f"a 1-minute SMT divergence never fired in a year: {sorted(kinds)}")
    confirms = {t.confirm_kind for t in trades}
    assert any("79% extension" in c for c in confirms)
    assert any("SMT divergence" in c for c in confirms)


def test_step_2b_only_ever_removes_trades_and_only_after_a_premarket_sweep():
    """112: "the ONLY time that we use 2B is if the high time frame form of
    manipulation happens BEFORE market opens." """
    a = replay_trades(Config())
    b = replay_trades(Config(require_fresh_5m_sweep_after_open=True))
    assert len(b) <= len(a), f"step 2B ADDED trades: {len(a)} -> {len(b)}"
    day = pd.Timestamp("2026-06-10")
    cfg = Config(require_fresh_5m_sweep_after_open=True)
    data = window(day, cfg)
    leg = SymbolDay("SPY", data["SPY"]["5m"], data["SPY"]["1m"], day, cfg,
                    NewsCalendar(), False)
    assert leg.needs_2b == leg.premarket_setup, (
        "2B was owed on a day whose sweep did not happen pre-market")


def test_the_continuation_smt_is_locked_behind_2b():
    """112: "equilibrium fair value gaps OR IF 2B HAPPENS THEN AN SMT
    divergence. And that's only if 2B happens." He enforces it himself on the
    next example: "2B didn't happen... So, we're NOT ABLE TO USE an SMT
    divergence." """
    import inspect
    src = inspect.getsource(SymbolDay.on_5m)
    assert "smt_in_continuation_menu_after_2b" in src and "self.saw_2b" in src
    i = src.index("smt_in_continuation_menu_after_2b")
    assert "self.saw_2b" in src[i:i + 200], (
        "the continuation divergence is not gated on 2B having fired")


def test_the_escalated_filter_is_not_softened_by_a_divergence():
    """Two losing weeks still demand the midpoint AND a fair value gap."""
    import inspect
    src = inspect.getsource(SymbolDay.on_5m)
    assert "(hit_eq and hit_gap) if self.escalated" in src, (
        "the two-losing-weeks filter no longer demands both")


def test_truncation_the_new_rules_cannot_see_the_future_either():
    """The existing truncation tests all run with the switches OFF, so none of
    them touches a divergence, a 79% level or a 1-minute gap. This re-runs THE
    test with every switch ON: re-decide each entry bar with every later bar
    deleted and demand the same answer.

    The two things that could have gone wrong are a divergence read off a
    swing that had not been stamped yet, and a 79% level anchored on a sweep
    extreme that had not happened yet. Both are fed one closed bar at a time,
    forward only, and this is what says so."""
    on = Config.newest_teaching()
    trades = replay_trades(on)
    assert len(trades) >= 5, f"only {len(trades)} trades to test causality on"
    for tr in trades:
        day, ts = tr.day, tr.entry_t
        # step461: the replay carries an escalation state across days and a
        # fresh bot does not. With entries running to the close there are
        # enough trades for two losing weeks to accumulate, so the state the
        # trade was actually decided under has to be handed back in or this
        # compares two different filters rather than two different histories.
        full = decide_at(window(day, on), day, ts, on, escalated=tr.escalated)
        cut = decide_at(truncate(window(day, on), ts), day, ts, on,
                        escalated=tr.escalated)
        assert full["entry"] is not None, f"{day:%Y-%m-%d}: entry vanished"
        assert full["entry"] == cut["entry"], (
            f"{day:%Y-%m-%d} decided differently with the future deleted:\n"
            f"  with future    {full['entry']}\n  without future {cut['entry']}")


def test_truncation_a_divergence_is_never_read_before_its_swing_is_stamped():
    """A SwingLog fed the whole day and one stopped short at bar N must hold
    the identical swings up to N — no swing may appear early and none may be
    revised once stamped."""
    day = pd.Timestamp("2026-06-10")
    d5 = window(day, Config(smt_enabled=True))["SPY"]["5m"]
    bars = [Bar(r.t, r.open, r.high, r.low, r.close)
            for r in d5[(d5["t"] >= day) &
                        (d5["t"] < day + pd.Timedelta(days=1))].itertuples()]
    assert len(bars) > 40
    # `keep` is raised so nothing is evicted — this is testing WHEN a swing is
    # known, not how many the log holds
    whole = tjr_bot.SwingLog(5, keep=10_000)
    for b in bars:
        whole.update(b)
    cut = tjr_bot.SwingLog(5, keep=10_000)
    for b in bars[:40]:
        cut.update(b)
    stamped_by_40 = [(s.price, s.t) for s in whole.highs if s.t <= bars[39].t]
    assert [(s.price, s.t) for s in cut.highs] == stamped_by_40, (
        "the swing log knew something at bar 40 that it only learns later")
    # and feeding the same bar twice changes nothing
    before = [(s.price, s.t) for s in cut.highs]
    cut.update(bars[39])
    assert [(s.price, s.t) for s in cut.highs] == before


# ------------------------------------------------------------- shared helpers
_R456: dict = {}


def replay_trades(cfg):
    """One walk of the year per config, cached — these tests are integration
    tests and they should not each pay for their own."""
    key = tuple(sorted((k, v) for k, v in vars(cfg).items()
                       if isinstance(v, (bool, int, float, str))))
    if key not in _R456:
        import step456_baseline as SB
        bot = TjrBot(cfg, NewsCalendar())
        out = []
        for day in SB.trading_days(SB.START, SB.END):
            out += bot.run_day(SB.window(day, cfg), day)["trades"]
        _R456[key] = out
    return _R456[key]


def dataclasses_replace(obj, **kw):
    import dataclasses
    return dataclasses.replace(obj, **kw)


# ================= step461: THE BIAS IS A LEAN, NOT A VETO
#
# step459 graded this bot against 73 dated recaps. He traded and we stood down
# on 51 days; we traded and he stood down on none. The daily bias gate is the
# largest single cause, 22 of the 51. step461 turns it from a veto into a lean
# that can be overruled and that can flip, out of the January 2026 course.
#
# The load-bearing test is `test_everything_off_reproduces_the_recorded_
# baseline_trade_for_trade` above: it already covers step461, because with
# every step461 switch off this file has to decide exactly what it decided
# before step461 existed, over 251 real sessions, trade for trade.

LEAN = Config(bias_revisable_intraday=True)


def test_every_step461_switch_ships_off():
    """2026-07-27: the shipping policy CHANGED. Parts 2 and 3 are his own
    mechanism (the divergence and the gap invalidation), step461 measured
    them as the parts that pay, and Wallace's standing instruction is 'just
    do whatever the pros say' — so they ship ON. Part 1 cost $8.3k for 1.4
    points and stays off, as does the master switch."""
    c = Config()
    assert c.bias_revisable_intraday is False, "the master switch must ship off"
    assert c.bias_holds_on_a_split_read is False, "part 1 must ship off"
    assert c.bias_yields_to_a_divergence is True, "part 2 ships ON (2026-07-27)"
    assert c.bias_flips_on_a_gap_invalidation is True, "part 3 ships ON (2026-07-27)"
    assert (c.lean_part1, c.lean_part2, c.lean_part3) == (False, True, True)
    # the master switch turns on all three parts and nothing else
    on = Config(bias_revisable_intraday=True)
    assert (on.lean_part1, on.lean_part2, on.lean_part3) == (True, True, True)
    for f in ("risk_pct_normal", "max_day_risk_share", "enforce_index_agreement",
              "enforce_daily_bias_side", "enforce_daily_4h_agreement",
              "use_1h_in_direction", "smt_enabled", "extension_79_enabled"):
        assert getattr(c, f) == getattr(on, f), (
            f"the lean switch changed {f}, which is not its to touch")


def test_step461_builds_no_machinery_while_it_is_off():
    """Off does not mean the new code runs and is ignored. It means the new
    code is never built at all — same standard step456 set for itself.
    Since 2026-07-27 parts 2+3 ship ON, so 'off' must now be said out loud."""
    all_off = Config(bias_yields_to_a_divergence=False,
                     bias_flips_on_a_gap_invalidation=False)
    _, trades, _, _, _ = replay(cfg=all_off)
    day = trades[0].day
    d = window(day)
    leg = SymbolDay("SPY", d["SPY"]["5m"], d["SPY"]["1m"], day, all_off,
                    NewsCalendar(), False)
    assert leg.ctx.flip_gaps is None, "the flip gap book was built with the switch off"
    assert leg.ctx.flip_trend is None
    assert leg.sw5 is None, "the divergence log was built with the switch off"
    assert leg.ctx.bias_notes == []
    assert leg._lean_may_yield(-1) is False and leg._lean_may_yield(+1) is False


def test_the_lean_refuses_far_more_counter_lean_setups_than_it_allows():
    """The whole point of the change is that the lean SURVIVES as a lean. On
    his own evidence it is picking his better days — 26 wins to 12 losses when
    it agreed with him, 15 to 12 when it blocked him — so a version that let
    every counter-lean sweep through would be throwing away a real edge.

    His test is the divergence between the two indexes: "we had a bearish SMT
    divergence, so that strengthens my bearish bias." A counter-lean sweep on
    which the two charts AGREE is refused here exactly as it is refused with
    the switch off."""
    _, _, _, _, results = replay(cfg=LEAN)
    allowed = refused = 0
    for res in results:
        for notes in res["notes"].values():
            for ln in notes:
                if "the market proved it wrong" in ln:
                    allowed += 1
                elif "did not diverge on the sweep" in ln:
                    refused += 1
    assert refused > 0 and allowed > 0, (
        f"the overrule never came up at all: {allowed} allowed, {refused} refused")
    assert refused > 3 * allowed, (
        f"the lean allowed {allowed} counter-lean setups and refused only "
        f"{refused} — that is a deleted gate, not a lean")


def test_a_trade_against_the_lean_always_names_what_overruled_it():
    """Nothing gets through this path silently, and only his two changes in
    order flow can carry it — capstone 2026-01-17: "the change in order flow
    ... could have been seen in two ways, either via break of structure or an
    inverse fair value gap." """
    _, trades, _, _, _ = replay(cfg=LEAN)
    against = [t for t in trades if t.against_bias]
    assert against, "no trade in the window ran against the lean"
    for t in against:
        assert t.overrule_kind, (
            f"{t.day:%Y-%m-%d} {t.symbol} ran against the lean with nothing named")
        assert "SMT divergence" in t.overrule_kind
        assert t.confirm_kind in SymbolDay._OVERRULE_CONFIRMATIONS, (
            f"{t.day:%Y-%m-%d} overruled the lean off {t.confirm_kind!r}, which "
            f"is not one of the two he names")
        assert t.direction != t.bias_at_open or t.bias_now != t.bias_at_open
    for t in trades:
        if not t.against_bias:
            assert t.overrule_kind == ""


def test_part_one_alone_only_touches_the_split_read_stand_down():
    """Part 1 retires exactly one stand-down reason and invents none."""
    _, _, off_reasons, _, _ = replay()
    _, _, on_reasons, _, _ = replay(cfg=Config(bias_holds_on_a_split_read=True))
    split = "the daily stands alone — the 4-hour and the 1-hour are both against it"
    assert split in off_reasons, "the split-read stand-down never fired at all"
    assert split not in on_reasons, "part 1 did not retire the split-read stand-down"
    # and it invents nothing. The level timeframe is baked into some of these
    # sentences, so they are compared with it stripped — a 1-hour level
    # reaching the same dead end as a 15-minute one is the same stand-down.
    def kinds(rs):
        return {r.split(" level was swept", 1)[-1] if " level was swept" in r
                else r for r in rs}
    assert not (kinds(on_reasons) - kinds(off_reasons) - {split}), (
        f"part 1 invented a stand-down: {kinds(on_reasons) - kinds(off_reasons)}")


def test_the_flip_reads_the_bottom_gap_of_a_stack_and_needs_a_body_close():
    """Which gap of a stack invalidates the trend is HIS, said twice.
    2026-01-14: "just because we close underneath this gap doesn't mean that
    this entire uptrend is invalidated because we have another gap right here
    ... for this entire trend to get invalidated, we would have to invalidate
    this gap down here." Capstone 2026-01-17: "we actually disrespect this gap.
    However, there's one gap underneath it, so it's not a full-fledged
    disrespect of the bullish order flow that we're in." """
    g = GapBook(60, 288)
    base = pd.Timestamp("2026-03-02 04:00")
    rows = [(100, 101, 99, 100), (101, 110, 101, 109), (109, 112, 105, 111),
            (111, 113, 110, 112), (112, 125, 112, 124), (124, 127, 120, 126)]
    for i, (o, h, l, c) in enumerate(rows):
        assert g.update(Bar(base + pd.Timedelta(hours=i), o, h, l, c)) == 0
    lows = sorted(x.bottom for x in g.live_in_direction(+1))
    assert lows == [101.0, 113.0], f"expected a stack of two, got {lows}"
    # a body close through the UPPER gap of the stack, and a wick clean
    # through the lower one: the trend is not invalidated
    inv = g.update(Bar(base + pd.Timedelta(hours=6), 126, 127, 100, 106))
    assert inv == 0, "the upper gap of the stack flipped the trend on its own"
    assert sorted(x.bottom for x in g.live_in_direction(+1)) == [101.0]
    # now a body close through the last gap holding it up
    inv = g.update(Bar(base + pd.Timedelta(hours=7), 106, 107, 95, 98))
    assert inv == -1, "closing through the bottom gap of the stack did nothing"


def test_truncation_the_lean_build_survives_deleting_the_future():
    """Causality is absolute and the new machinery is not exempt. Every entry
    the lean build takes is re-decided with every later bar deleted."""
    _, trades, _, _, _ = replay(cfg=LEAN)
    assert len(trades) >= 5, f"only {len(trades)} trades to test causality on"
    for tr in trades:
        day, ts = tr.day, tr.entry_t
        full = decide_at(window(day, LEAN), day, ts, LEAN,
                         escalated=tr.escalated)
        cut = decide_at(truncate(window(day, LEAN), ts), day, ts, LEAN,
                        escalated=tr.escalated)
        assert full["entry"] is not None, f"{day:%Y-%m-%d}: entry vanished"
        assert full["entry"] == cut["entry"], (
            f"{day:%Y-%m-%d} decided differently with the future deleted:\n"
            f"  with future    {full['entry']}\n  without future {cut['entry']}")


def test_truncation_a_lean_flip_cannot_be_read_before_its_candle_closes():
    """Part 3's whole risk is reading a higher-timeframe candle early. The
    same guarantee `test_truncation_higher_timeframe_bar_is_invisible_until_
    it_closes` gives the 4-hour has to hold for the gap that flips the lean."""
    _, trades, _, days, _ = replay(cfg=LEAN)
    day = trades[0].day
    for m in (55, 5, 15, 25):
        ts = day + pd.Timedelta(hours=9 if m == 55 else 10, minutes=m)
        a = decide_at(window(day, LEAN), day, ts, LEAN)
        b = decide_at(truncate(window(day, LEAN), ts), day, ts, LEAN)
        assert a == b, f"{ts} moved when the future was deleted:\n{a}\n{b}"


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
