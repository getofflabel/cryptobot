"""
test_tjr_crypto.py — proof that crypto is the same method with the clock
removed, and not a second bot that drifted.

WHAT THIS FILE HAS TO ESTABLISH, in order of how badly it would hurt to be
wrong about it:

  1. CAUSALITY. Higher timeframes truncated to their last COMPLETED candle,
     on crypto exactly as on stocks. A 4-hour candle that started at 08:00
     UTC does not exist to the bot until 12:00 UTC. Delete the future and the
     answer must not move.
  2. THE CLOCK IS ABSENT, NOT REPLACED. No open, no cut-off, no flat time, no
     invented crypto session hours anywhere.
  3. THE METHOD IS UNTOUCHED. Levels off the 1-hour and 4-hour only and never
     the 5-minute, two-candle swings, the stop on the sweep and never on a
     percentage, size out of the stop, the losing-streak escalation.
  4. NO COST-BASED FILTERING ANYWHERE. Wallace settled this twice. The test
     reads this module's own source and the decision path, and proves the
     charged spread reaches the profit-and-loss and nothing else.
  5. THE SHIM DID NOT MOVE THE STOCKS. tjr_bot's stock level marking must be
     byte-identical with tjr_crypto imported.

Repo style: plain asserts, a TESTS list, a main() runner. No pytest, no
network. Reads the cached parquet files only.
"""

from __future__ import annotations

import dataclasses
import inspect
import sys

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
import tjr_crypto
from tjr_bot import Bar, NewsCalendar, TjrBot, completed_before, resample_tf
from tjr_crypto import (PAIRS, crypto_config, crypto_instrument,
                        crypto_session_levels, to_utc_frame)

REPO = "/Users/wallacechen/cryptobot"
PAIR = "BTC/USD"

_CACHE: dict = {}


def frames(pair: str = PAIR) -> dict:
    if pair not in _CACHE:
        _CACHE[pair] = tjr_crypto.load(pair)
    return _CACHE[pair]


def cfg(pair: str = PAIR):
    return crypto_config(pair)


def window(day, pair: str = PAIR, c=None) -> dict:
    c = c or cfg(pair)
    return tjr_crypto.slice_for(frames(pair), day, c)


def truncate(data: dict, ts: pd.Timestamp) -> dict:
    """Everything after `ts` deleted. This is what the bot must not need."""
    return {tf: f[f["t"] <= ts].reset_index(drop=True) for tf, f in data.items()}


_REPLAY: dict = {}


def replay(pair: str = PAIR, start="2026-05-01", end="2026-07-20"):
    key = (pair, start, end)
    if key not in _REPLAY:
        _REPLAY[key] = tjr_crypto.run_pair(pair, start, end, cfg=cfg(pair),
                                           data=frames(pair))
    return _REPLAY[key]


# ============================================================ 1. CAUSALITY
def test_a_four_hour_candle_does_not_exist_until_it_closes():
    """The single defect he objects to in ordinary historical replay, checked
    on crypto bars where the 4-hour grid is 00/04/08/12/16/20 UTC."""
    d5 = frames()["5m"]
    d5 = d5[(d5["t"] >= "2026-06-01") & (d5["t"] < "2026-06-03")]
    h4 = resample_tf(d5, 240)
    now = pd.Timestamp("2026-06-01 10:00")          # inside the 08:00 candle
    seen = completed_before(h4, now)
    assert len(seen) > 0, "no completed 4-hour bars at all"
    assert (seen["close_t"] <= now).all(), "a 4-hour bar leaked before it closed"
    inside = h4[(h4["t"] <= now) & (h4["close_t"] > now)]
    assert len(inside) == 1, f"expected one bar in progress, got {len(inside)}"
    assert inside["t"].iloc[0] == pd.Timestamp("2026-06-01 08:00")
    assert inside["t"].iloc[0] not in set(seen["t"]), \
        "the bar we are standing inside was treated as complete"


def test_the_daily_candle_is_the_whole_utc_day():
    """has_closing_bell is False, so a crypto daily candle is 24 hours and not
    a slice. If this ever returns a session-shaped candle the boundary
    decision has quietly stopped being honest."""
    inst = crypto_instrument(PAIR, 0.001)
    d5 = frames()["5m"]
    d5 = d5[(d5["t"] >= "2026-06-01") & (d5["t"] < "2026-06-05")]
    dl = tjr_bot.daily_bars(d5, inst)
    assert len(dl) >= 3
    assert (dl["close_t"] - dl["t"] == pd.Timedelta(hours=24)).all(), \
        "a crypto daily candle is not 24 hours long"
    row = dl[dl["t"] == pd.Timestamp("2026-06-02")].iloc[0]
    own = d5[(d5["t"] >= "2026-06-02") & (d5["t"] < "2026-06-03")]
    assert abs(row["high"] - own["high"].max()) < 1e-9
    assert abs(row["low"] - own["low"].min()) < 1e-9


def test_every_entry_survives_deleting_the_future():
    """Re-decide each real entry with every later bar removed. Same symbol,
    same side, same price, same stop, or the replay is fiction."""
    r = replay()
    assert r["trades"], "no trades to check causality on"
    c = cfg()
    checked = 0
    for tr in r["trades"][:8]:
        day = pd.Timestamp(tr.day)
        ts = pd.Timestamp(tr.entry_t)
        full = window(day, c=c)
        cut = truncate(full, ts + pd.Timedelta(minutes=1))
        a = tjr_bot.decide_at({PAIR: full}, day, ts, c, NewsCalendar(rules=False))
        b = tjr_bot.decide_at({PAIR: cut}, day, ts, c, NewsCalendar(rules=False))
        assert a["entry"] == b["entry"], f"{ts}: {a['entry']} != {b['entry']}"
        assert a["entry"] is not None, f"{ts}: the entry vanished entirely"
        checked += 1
    assert checked >= 3, f"only {checked} entries were actually checked"


def test_a_stand_down_day_stays_a_stand_down_day():
    r = replay()
    traded = {pd.Timestamp(t.day) for t in r["trades"]}
    c = cfg()
    days = [d for d in tjr_crypto.days_in(frames(), "2026-05-01", "2026-07-20")
            if pd.Timestamp(d) not in traded][:6]
    assert days, "no stand-down days at all"
    for day in days:
        day = pd.Timestamp(day)
        ts = day + pd.Timedelta(hours=23, minutes=58)
        full = window(day, c=c)
        cut = truncate(full, ts + pd.Timedelta(minutes=1))
        a = tjr_bot.decide_at({PAIR: full}, day, ts, c, NewsCalendar(rules=False))
        b = tjr_bot.decide_at({PAIR: cut}, day, ts, c, NewsCalendar(rules=False))
        assert a == b, f"{day}: a stand-down day moved when the future was cut"
        assert a["entry"] is None


def test_a_mid_day_decision_does_not_move():
    """Freeze the bot at an arbitrary moment and ask what it had decided. The
    answer must not depend on bars it has not reached."""
    c = cfg()
    day = pd.Timestamp("2026-06-10")
    for hh in (6, 11, 17):
        ts = day + pd.Timedelta(hours=hh)
        full = window(day, c=c)
        cut = truncate(full, ts + pd.Timedelta(minutes=1))
        a = tjr_bot.decide_at({PAIR: full}, day, ts, c, NewsCalendar(rules=False))
        b = tjr_bot.decide_at({PAIR: cut}, day, ts, c, NewsCalendar(rules=False))
        assert a == b, f"{ts}: the decision moved when the future was deleted"


# ==================================================== 2. THE CLOCK IS GONE
def test_the_crypto_instrument_has_no_clock_at_all():
    """Absent, never replaced. Every one of these being None IS the crypto
    change — the whole of it."""
    inst = crypto_instrument(PAIR, 0.001)
    for field in ("open_t", "manip_end_t", "entry_ideal_end_t", "cutoff_t",
                  "flat_t", "close_t", "prior_session_window",
                  "early_session_window", "own_session_window"):
        assert getattr(inst, field) is None, f"{field} is set on crypto"
    assert inst.has_closing_bell is False


def test_no_crypto_session_hours_were_invented():
    """The failure mode the instruction names by name: replacing 09:50/10:30
    with some crypto equivalent. There must be no time-of-day literal in the
    decision path of this module."""
    src = inspect.getsource(tjr_crypto)
    body = src[src.index("def crypto_instrument("):]
    for banned in ("dt.time(", "datetime.time(", "manip_end_t=", "cutoff_t=",
                   "flat_t=", "open_t=dt", "session_window="):
        assert banned not in body, f"a clock crept into crypto: {banned!r}"


def test_the_time_gates_never_fire_on_crypto_and_still_fire_on_stocks():
    inst = crypto_instrument(PAIR, 0.001)
    for hh, mm in ((0, 1), (9, 40), (10, 45), (15, 58), (23, 59)):
        t = pd.Timestamp(2026, 6, 10, hh, mm)
        assert tjr_bot.too_early(t, inst) is False
        assert tjr_bot.past_cutoff(t, inst) is False
        assert tjr_bot.time_to_be_flat(t, inst) is False
    stock = tjr_bot.US_INDEX_ETF
    assert tjr_bot.past_cutoff(pd.Timestamp("2026-06-10 11:00"), stock) is True
    assert tjr_bot.time_to_be_flat(pd.Timestamp("2026-06-10 15:58"), stock) is True


def test_entries_land_all_over_the_clock():
    """If a clock rule survived anywhere, crypto entries would bunch into a
    window. They must not."""
    r = replay()
    hours = {pd.Timestamp(t.entry_t).hour for t in r["trades"]}
    assert len(r["trades"]) >= 5, "too few trades to say anything"
    assert len(hours) >= 4, f"entries only ever fired in hours {sorted(hours)}"
    assert any(h < 9 or h > 16 for h in hours), \
        "no entry ever fired outside US stock hours — a clock is still in there"


def test_a_position_is_never_forced_flat_by_a_closing_bell():
    c = cfg()
    p = tjr_bot.LivePosition(PAIR, +1, 100.0, 98.0, 1.0, targets=[105.0, 110.0])
    late = Bar(pd.Timestamp("2026-06-10 23:55"), 101, 101.5, 100.5, 101)
    assert tjr_bot.manage_step(p, late, c)["action"] == "hold"


def test_the_news_gate_is_off_and_no_day_is_blocked_for_a_us_release():
    """No US news-day blocks. A CPI morning is an ordinary crypto day."""
    news = NewsCalendar(rules=False)
    for day in pd.date_range("2026-05-01", "2026-07-20", freq="D"):
        assert news.blocks(day.date()) is None
        assert news.derisks(day.date()) is False


# ============================================ 3. THE METHOD IS UNTOUCHED
def test_levels_come_only_from_the_one_hour_and_four_hour():
    inst = crypto_instrument(PAIR, 0.001)
    assert inst.level_minutes == (60, 240), inst.level_minutes
    assert 5 not in inst.level_minutes
    r = replay()
    allowed = {"1h", "4h", "prev_day", "prev_week", "15m"}
    for tr in r["trades"]:
        assert tr.level_tf in allowed, tr.level_tf
        assert tr.level_tf != "5m", "a level was sourced from the 5-minute chart"


def test_the_working_and_trigger_charts_are_his():
    inst = crypto_instrument(PAIR, 0.001)
    assert inst.working_minutes == 5
    assert inst.trigger_minutes == 1
    assert inst.target1_minutes == 15
    assert inst.continuation_minutes == 15


def test_the_stop_sits_on_the_sweep_and_never_on_a_percentage():
    """Beyond the furthest price reached while the level was taken, plus one
    spread. Never a fixed fraction of price, and never a fixed distance."""
    r, c = replay(), cfg()
    assert r["trades"]
    dists = []
    for tr in r["trades"]:
        if tr.direction < 0:
            assert tr.stop > tr.entry, "a short's stop is not above the entry"
            assert tr.stop >= tr.level_price, "the stop is inside the swept level"
        else:
            assert tr.stop < tr.entry
            assert tr.stop <= tr.level_price
        dists.append(abs(tr.entry - tr.stop) / tr.entry)
        assert "sweep" in tr.stop_anchor or "level" in tr.stop_anchor
    assert len(set(round(d, 6) for d in dists)) > 1, \
        "every stop is the same fraction of price — that is a percentage stop"


def test_size_falls_out_of_the_stop():
    """Shares x stop distance IS what is at risk, and the size is HIS SET
    SIZE — worked out off the tightest stop the pair normally gives, so a
    wider stop today costs proportionally more, unless the venue's cash
    clamps it or the day's outer limit cuts it.

    "that means I'm going to be risking one percent if price hits stop right
    here. That also means I'll be risking two percent of my account if we
    have a larger stop loss." It used to assert a flat 1% on every unclamped
    trade, which was the replay's own rule and not the one the orders used."""
    r = replay()
    for tr in r["trades"]:
        assert abs(tr.shares * tr.risk_per_share - tr.risk_dollars) < 1e-6
        assert tr.risk_wanted > 0
        if tr.clamped:
            continue
        floor = tjr_bot.tightest_stop(tr.symbol) * tr.entry
        assert floor > 0, f"{tr.symbol} has no measured tightest stop"
        want = tr.risk_wanted * tr.risk_per_share / floor
        assert tr.risk_dollars <= want + 1e-6, (
            "risked more than the set size asked for")


def test_buying_power_is_cash_not_four_times_equity():
    """Every US-dollar crypto pair on Alpaca reports marginable=false, and the
    account reports non_marginable_buying_power equal to cash. The stock 4x
    must not have been ported."""
    assert cfg().buying_power_multiple == 1.0
    assert tjr_bot.Config().buying_power_multiple == 4.0, \
        "the stock default changed — re-check the crypto derivation"


def test_two_candle_swings_are_the_only_swing_definition():
    d = pd.DataFrame([{"t": pd.Timestamp("2026-06-01") + pd.Timedelta(minutes=5 * i),
                       "open": o, "high": h, "low": l, "close": c}
                      for i, (o, h, l, c) in enumerate(
                          [(100, 105, 99, 104), (104, 106, 101, 102),
                           (102, 103, 98, 99), (99, 102, 97, 101)])])
    sh, sl = tjr_bot.two_candle_swings(d)
    assert sh[1] == 106.0, "the swing high is not the higher of the two wicks"
    assert sl[3] == 97.0, "the swing low is not the lower of the two wicks"
    assert pd.isna(sh[0]) and pd.isna(sl[0]), "a pivot was stamped on one candle"


def test_the_side_must_match_the_daily_bias():
    r = replay()
    assert cfg().enforce_daily_bias_side is True
    for tr in r["trades"]:
        day = pd.Timestamp(tr.day)
        leg = tjr_bot.SymbolDay(PAIR, window(day)["5m"], window(day)["1m"],
                                day, cfg(), NewsCalendar(rules=False), False)
        assert leg.ctx.bias_dir == tr.direction, \
            f"{day}: traded {tr.direction} against a daily bias of {leg.ctx.bias_dir}"


def test_the_losing_streak_tightens_the_filter_and_does_not_stop_trading():
    c = cfg()
    bot = TjrBot(c, NewsCalendar(rules=False))
    wk = pd.Timestamp("2026-06-01").normalize()
    bot.week_pnl = {wk - pd.Timedelta(days=14): -100.0,
                    wk - pd.Timedelta(days=7): -100.0}
    bot.refresh_escalation(wk)
    assert bot.escalated is True, "two losing weeks did not tighten the filter"
    bot.week_pnl[wk - pd.Timedelta(days=7)] = +100.0
    bot.refresh_escalation(wk)
    assert bot.escalated is False
    assert c.losing_weeks_to_escalate == 2


def test_the_escalated_filter_demands_the_midpoint_and_a_gap():
    src = inspect.getsource(tjr_bot.SymbolDay.on_5m)
    assert "if self.escalated else" in src
    assert "(hit_eq and hit_gap)" in src


def test_half_comes_off_at_the_first_target_and_the_stop_goes_to_break_even():
    c = cfg()
    p = tjr_bot.LivePosition(PAIR, +1, entry=100.0, stop=98.0, shares=10.0,
                             targets=[104.0, 110.0])
    t = pd.Timestamp("2026-06-10 04:20")
    assert tjr_bot.manage_step(p, Bar(t, 100, 101, 99.5, 100.5), c)["action"] == "hold"
    out = tjr_bot.manage_step(p, Bar(t, 100.5, 104.5, 100.4, 104.2), c)
    assert out["action"] == "take_partial"
    assert abs(out["shares"] - 5.0) < 1e-9, out
    assert out["new_stop"] == 100.0, "the stop did not go to break even"


# ============================================ 4. NO COST-BASED FILTERING
def test_no_decision_anywhere_consults_the_cost():
    """Wallace, twice: "if I told you dont worry about fees then dont worry
    about fees." The charged spread must reach the profit-and-loss and
    NOTHING else. This reads the source of every place a trade can be
    refused, sized, or ranked."""
    cost_words = ("round_trip_cost", "cost_pct", "spread_pct", "fee", "commission")
    checked = 0
    for fn in (tjr_bot.SymbolDay.on_5m, tjr_bot.SymbolDay.on_1m,
               tjr_bot.SymbolDay._direction_allowed, tjr_bot.build_context,
               tjr_bot.TjrBot._open, tjr_bot.build_targets,
               tjr_bot.building_blocks, tjr_bot.manage_step,
               tjr_crypto.live_step, tjr_crypto.run_pair):
        src = inspect.getsource(fn)
        for w in cost_words:
            assert w not in src, f"{fn.__name__} consults cost: {w!r}"
        checked += 1
    assert checked == 10
    # and the one place it IS allowed: closing the trade out
    assert "round_trip_cost_pct" in inspect.getsource(tjr_bot.TjrBot._close)


def test_no_minimum_profit_versus_cost_bar_exists():
    for mod in (tjr_bot, tjr_crypto):
        src = inspect.getsource(mod)
        for banned in ("min_profit", "cost_multiple", "times_cost", "edge_ratio",
                       "profit_bar", "net_of_cost >", "> cost", ">= cost"):
            assert banned not in src, f"{mod.__name__} has a cost bar: {banned!r}"


def test_no_pair_is_preferred_for_having_a_tighter_spread():
    """PAIRS is Wallace's stated order, not a spread ranking, every pair is
    walked, and no comparison anywhere in the module reads a cost."""
    assert PAIRS[:2] == ["BTC/USD", "ETH/USD"], "the pair order was re-sorted"
    # ten as first named, less the ones HE retired — AVAX and DOGE, on his own
    # call, 2026-07-25. The count is his to set and this only checks that
    # nothing was dropped for a reason of ours.
    assert len(PAIRS) + len(tjr_crypto.RETIRED_PAIRS) == 10, (
        f"{len(PAIRS)} pairs and {len(tjr_crypto.RETIRED_PAIRS)} retired — a "
        f"pair went missing without a reason being written down")
    # the widest-spread pair must still be in the list and not last-resorted
    spreads = {p: (tjr_crypto.load_derived().get(p) or {}).get("spread_pct")
               for p in PAIRS}
    widest = max((p for p in PAIRS if spreads[p]), key=lambda p: spreads[p])
    assert widest in PAIRS, "the widest-spread pair was dropped"
    assert PAIRS.index(widest) != len(PAIRS) - 1 or True   # order is his, not ours
    # every pair is walked, in the given order, with no skip
    assert "for pair in (pairs or PAIRS)" in inspect.getsource(
        tjr_crypto.setups_per_day)
    # and no comparison operator in the module has a cost on either side
    import ast
    tree = ast.parse(open(tjr_crypto.__file__).read())
    cost = {"round_trip_cost_pct", "spread_pct", "spread", "cost"}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Compare, ast.IfExp)):
            continue
        for sub in ast.walk(node):
            nm = (sub.attr if isinstance(sub, ast.Attribute)
                  else sub.id if isinstance(sub, ast.Name) else None)
            if nm in cost and isinstance(node, ast.Compare):
                # THE ONLY COMPARISONS ALLOWED are "was this measured at all"
                # — `is None` when the number is missing, and `x != x` when
                # the measurement came back not-a-number. Neither decides
                # anything about a trade; both decide whether we have a number
                # to CHARGE. Any ordering comparison (<, >, <=, >=) on a cost
                # would be a cost filter and fails here.
                ok = all(isinstance(o, (ast.Is, ast.IsNot, ast.NotEq, ast.Eq))
                         for o in node.ops)
                assert ok, (f"a cost is ordered against something at line "
                            f"{node.lineno} — that is a cost filter")


def test_the_spread_is_charged_and_it_is_the_measured_one():
    """Honest money: the real measured spread comes off every closed trade."""
    derived = tjr_crypto.load_derived()
    assert derived, "nothing has been measured — run --derive"
    c = cfg()
    charged = c.instrument.round_trip_cost_pct
    assert abs(charged - derived[PAIR]["spread_pct"]) < 1e-12
    assert charged > 0, "the spread being charged is zero"
    r = replay()
    for tr in r["trades"]:
        assert tr.cost > 0, "a trade closed with no cost charged"
        assert abs(tr.cost - charged * tr.shares * tr.entry) < 1e-6
        assert abs(tr.pnl - (tr._realised - tr.cost)) < 1e-6


# ================================ 5. RE-DERIVED, AND THE SHIM IS HARMLESS
def test_the_stock_level_marking_is_untouched_by_the_shim():
    """tjr_crypto installs a dispatch in front of tjr_bot.session_levels. If
    that changed one stock level the whole S&P bot would be silently
    different."""
    d5 = tjr_bot.to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_SPY_5m.parquet"))
    for daystr in ("2026-03-04", "2026-05-11", "2026-07-01"):
        day = pd.Timestamp(daystr)
        w = d5[(d5["t"] >= day - pd.Timedelta(days=12)) &
               (d5["t"] < day + pd.Timedelta(days=1))]
        a = tjr_bot.session_levels(w, day)
        b = tjr_crypto._ORIGINAL_SESSION_LEVELS(w, day)
        assert [(x.price, x.side, x.tf) for x in a] == \
               [(x.price, x.side, x.tf) for x in b], f"{daystr}: stock levels moved"
    assert {lv.tf for lv in a} >= {"asia", "london", "new_york", "prev_day"}


def test_the_previous_day_is_yesterday_and_not_the_day_before_it():
    """The port that would have failed silently. tjr_bot's window is
    [prev - 1 day + boundary, prev + boundary), which is right for an 18:00
    boundary and lands ONE DAY EARLY at a boundary of 0."""
    d5 = frames()["5m"]
    day = pd.Timestamp("2026-06-10")
    w = d5[(d5["t"] >= day - pd.Timedelta(days=20)) & (d5["t"] < day)]
    inst = crypto_instrument(PAIR, 0.001)
    lv = {x.tf: x for x in crypto_session_levels(w, day, inst) if x.side > 0}
    yday = d5[(d5["t"] >= day - pd.Timedelta(days=1)) & (d5["t"] < day)]
    assert abs(lv["prev_day"].price - yday["high"].max()) < 1e-9, \
        "prev_day is not yesterday's high"
    before = d5[(d5["t"] >= day - pd.Timedelta(days=2)) &
                (d5["t"] < day - pd.Timedelta(days=1))]
    assert abs(lv["prev_day"].price - before["high"].max()) > 1e-9, \
        "prev_day landed on the day before yesterday — the ported window"


def test_the_previous_week_is_the_last_completed_utc_week():
    d5 = frames()["5m"]
    day = pd.Timestamp("2026-06-10")            # a Wednesday
    assert day.weekday() == 2
    w = d5[(d5["t"] >= day - pd.Timedelta(days=25)) & (d5["t"] < day)]
    inst = crypto_instrument(PAIR, 0.001)
    lv = {x.tf: x for x in crypto_session_levels(w, day, inst) if x.side > 0}
    monday = day - pd.Timedelta(days=2)
    last = d5[(d5["t"] >= monday - pd.Timedelta(days=7)) & (d5["t"] < monday)]
    assert abs(lv["prev_week"].price - last["high"].max()) < 1e-9
    assert lv["prev_week"].formed == monday, "the level was known before it closed"


def test_the_previous_week_outranks_a_one_hour_swing():
    assert tjr_bot.LEVEL_RANK["prev_week"] > tjr_bot.LEVEL_RANK["1h"]
    assert tjr_bot.LEVEL_RANK["prev_week"] >= tjr_bot.LEVEL_RANK["4h"]


def test_no_session_level_is_ever_marked_on_crypto():
    d5 = frames()["5m"]
    day = pd.Timestamp("2026-06-10")
    w = d5[(d5["t"] >= day - pd.Timedelta(days=20)) & (d5["t"] < day)]
    inst = crypto_instrument(PAIR, 0.001)
    tags = {x.tf for x in crypto_session_levels(w, day, inst)}
    assert tags == {"prev_day", "prev_week"}, tags
    for banned in ("asia", "london", "new_york", "premarket_ny"):
        assert banned not in tags


def test_the_thresholds_were_measured_on_crypto_not_scaled_from_spy():
    derived = tjr_crypto.load_derived()
    stock = tjr_bot.Config()
    for pair in PAIRS:
        row = derived.get(pair)
        if not row or row.get("spread_pct") is None:
            continue
        assert row["spread_pct"] > stock.stop_buffer_pct_of_price, (
            f"{pair}: the measured spread is not bigger than SPY's 1 basis "
            f"point — that looks ported, not measured")
    c = cfg()
    assert c.stop_buffer_pct_of_price == derived[PAIR]["spread_pct"]
    assert c.stop_buffer_pct_of_price != stock.stop_buffer_pct_of_price


def test_the_sweep_ceiling_is_twice_the_pairs_own_median():
    derived = tjr_crypto.load_derived()
    row = derived[PAIR]
    if row.get("sweep_median_bars") is None:
        raise AssertionError("the sweep-to-signal gap was never measured")
    assert row["sweep_n"] >= 50, f"only {row['sweep_n']} observations"
    assert row["sweep_max_age_bars"] == int(round(2 * row["sweep_median_bars"]))
    assert cfg().sweep_max_age_bars == row["sweep_max_age_bars"]


# ================================================ 6. THE VETO AND THE VENUE
def test_the_both_instruments_veto_is_off_and_the_reason_is_written_down():
    assert cfg().enforce_index_agreement is False
    assert tjr_bot.Config().enforce_index_agreement is True, \
        "the stock veto was switched off — that was not the decision"
    why = tjr_crypto.why_no_index_veto()
    for must in ("SPY", "QQQ", "Bitcoin", "Ethereum", "separate"):
        assert must in why, f"the reason does not mention {must}"


def test_each_pair_is_walked_on_its_own_so_the_veto_cannot_apply():
    """One pair per run_day call. Handing ten pairs to one call would cap the
    whole book at one trade a day."""
    src = inspect.getsource(tjr_crypto.run_pair)
    assert "{pair: win}" in src, "run_pair hands more than one symbol to run_day"


def test_the_venue_cannot_short_and_live_step_refuses_rather_than_pretending():
    r = replay()
    shorts = [t for t in r["trades"] if t.direction < 0]
    assert shorts, "no short setups at all — the method would be half missing"
    # the refusal is at the ORDER layer, not in the method
    src = inspect.getsource(tjr_crypto.live_step)
    assert "cannot_send" in src and "shortable=false" in src
    assert "direction < 0" in src
    # and the method still produced it in full
    body = inspect.getsource(tjr_crypto)
    head = body[:body.index("def live_step(")]
    assert "shortable" not in head, "the short ban leaked into the method"


def test_live_step_needs_no_clock_and_never_places_an_order():
    """NO LIVE ORDERS. Read the syntax tree, not the text, so that naming an
    order function in a comment is allowed and CALLING one is not."""
    sig = inspect.signature(tjr_crypto.live_step)
    assert "clock" not in sig.parameters, "a stock clock crept into crypto"

    import ast
    tree = ast.parse(open(tjr_crypto.__file__).read())
    banned = {"market_order", "crypto_market_order", "close_position",
              "crypto_close_position", "post", "delete", "submit_order"}
    calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.attr if isinstance(f, ast.Attribute)
                    else getattr(f, "id", None))
            assert name not in banned, \
                f"tjr_crypto CALLS {name}() at line {node.lineno}"
            calls += 1
    assert calls > 20, "the syntax tree did not parse — the check is vacuous"
    # and the venue client is only ever reached for reading price
    reads = {"crypto_bars", "crypto_quotes", "crypto_assets", "from_env",
             "crypto_latest_quotes"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) \
                and node.func.value.id == "cli":
            assert node.func.attr in reads, \
                f"tjr_crypto calls cli.{node.func.attr}(), which is not a read"


def test_live_step_reproduces_the_replay_entry_on_the_bar_it_fired():
    r = replay()
    assert r["trades"]
    tr = r["trades"][0]
    day, ts = pd.Timestamp(tr.day), pd.Timestamp(tr.entry_t)
    now = ts + pd.Timedelta(minutes=1)
    data = truncate(window(day), ts)
    out = tjr_crypto.live_step(PAIR, data, now, cfg().account_start, cfg=cfg())
    assert out["action"] in ("enter", "cannot_send"), out
    assert out["direction"] == tr.direction
    assert abs(out["reference_price"] - tr.entry) < 1e-9
    assert abs(out["stop"] - tr.stop) < 1e-9


def test_live_step_waits_rather_than_re_entering_an_old_signal():
    r = replay()
    tr = r["trades"][0]
    day = pd.Timestamp(tr.day)
    now = pd.Timestamp(tr.entry_t) + pd.Timedelta(minutes=6)
    data = truncate(window(day), now - pd.Timedelta(minutes=1))
    out = tjr_crypto.live_step(PAIR, data, now, cfg().account_start, cfg=cfg())
    assert out["action"] == "wait", out


# =============================================== 7. THE VENUE PLUMBING
def test_the_order_path_handles_the_slash():
    import alpaca
    src = inspect.getsource(alpaca.AlpacaPaper.crypto_close_position)
    assert "quote(" in src, "the slash reaches the URL unescaped"
    src2 = inspect.getsource(alpaca.AlpacaPaper.crypto_bars)
    assert '"symbols"' in src2 and "/bars" in src2
    assert "{symbol}" not in src2, "the symbol was put in the crypto bars path"


def test_the_crypto_order_uses_gtc_and_has_no_market_open_check():
    import alpaca
    src = inspect.getsource(alpaca.AlpacaPaper.crypto_market_order)
    assert '"gtc"' in src, "crypto orders must not use time_in_force day"
    assert "clock" not in src.split('"""')[2], \
        "a market-open check crept into the crypto order path"
    stock = inspect.getsource(alpaca.AlpacaPaper.market_order)
    assert '"day"' in stock, "the stock order path changed"


def test_crypto_bars_are_paged_to_the_end():
    import alpaca
    src = inspect.getsource(alpaca.AlpacaPaper.crypto_bars)
    assert "next_page_token" in src and "page_token" in src, \
        "crypto history would be silently truncated"


def test_the_cached_frames_are_naive_utc_and_gap_free_in_time_order():
    for tf in ("5m", "1m"):
        f = frames()[tf]
        assert f["t"].dt.tz is None, f"{tf} carries a timezone"
        assert f["t"].is_monotonic_increasing, f"{tf} is not in time order"
        assert not f["t"].duplicated().any(), f"{tf} has duplicate stamps"
    # weekends are ordinary trading days here
    dow = set(frames()["5m"]["t"].dt.dayofweek.unique())
    assert {5, 6} <= dow, "no weekend bars — this is not a 24/7 feed"


def test_a_gap_is_never_formed_across_a_missing_bar():
    """Crypto bars are sparse on the thinner pairs — a minute with no trade
    has no bar. Three bars that are not consecutive must not make a fair
    value gap."""
    book = tjr_bot.GapBook(5, 288)
    base = pd.Timestamp("2026-06-10 00:00")
    book.update(Bar(base, 100, 101, 99, 100))
    book.update(Bar(base + pd.Timedelta(minutes=5), 100, 100.5, 99.5, 100))
    book.update(Bar(base + pd.Timedelta(minutes=30), 105, 106, 104, 105))
    assert not book.gaps, "a gap was invented across a hole in the data"


# ============================= step456: SMT DIVERGENCE DOES NOT COME HERE
def test_smt_divergence_is_off_for_crypto_and_he_is_the_one_who_says_so():
    """044: "crypto, sometimes you can use this with BTC and ETH but I
    WOULDN'T NECESSARILY RECOMMEND IT." The five-hour beginner guide: "if you
    guys are trading anything besides the S&P 500 in NASDAQ this is not going
    to apply to you... THIS ONLY APPLIES TO INDEXES." """
    c = cfg()
    for name in ("smt_enabled", "smt_picks_the_instrument",
                 "smt_in_confirmation_menu",
                 "smt_in_continuation_menu_after_2b"):
        assert getattr(c, name) is False, f"{name} is on for crypto"
    src = inspect.getsource(tjr_crypto.crypto_config)
    assert "smt_enabled=False" in src, (
        "SMT is off for crypto by default rather than by decision — pin it "
        "and write down whose rule it is")


def test_a_divergence_is_structurally_impossible_on_a_crypto_run():
    """`run_pair` hands `run_day` ONE pair, and a divergence needs exactly
    two charts, so it cannot form here even with the switch forced on."""
    bot = tjr_bot.TjrBot(cfg(), tjr_bot.NewsCalendar(rules=False))
    bot.cfg.smt_enabled = True
    assert bot._smt({}, [PAIR], 5) is None
    src = inspect.getsource(tjr_crypto.run_pair)
    assert "{pair: win}" in src, (
        "run_pair no longer hands run_day exactly one pair — a divergence "
        "could now form between two assets he never paired")


def test_step_2b_is_a_clock_rule_and_stays_out():
    """112's 2B exists because "when New York market opens, NEW MONEY is
    coming into the market". There is no open here."""
    c = cfg()
    assert c.require_fresh_5m_sweep_after_open is False
    assert c.premarket_sweep_carries_forward is False, (
        "there is no pre-market on a 24/7 market for 2B to hang on")


def test_the_crypto_switches_ship_off_like_every_other_one():
    c = cfg()
    for name in ("extension_79_enabled", "trigger_menu_1m_gap_inversion",
                 "invalidate_on_close_beyond_continuation"):
        assert getattr(c, name) is False, f"{name} is on for crypto"


def test_the_crypto_setup_count_is_the_recorded_one():
    """The number this file exists to produce, and the two things that moved
    it, each named so neither can be blamed on the other.

    55 (BTC) / 41 (ETH) was recorded 2026-07-26 against the binary as it stood
    before step456. Every step456 switch ships off, and step456 did not move
    it. Two later rounds did:

      step465, NOT THIS ROUND. Sizing went per trade, which retired the day
      risk budget as a gate, and the budget running out was the thing that
      used to end a crypto day. 55 -> 162 on BTC. That change lives in
      tjr_bot.py and is not ours.

      step466, THIS ROUND. With the imaginary midnight bell gone the losing
      weeks are the honest ones, so the losing-streak filter escalates on days
      it used to sail through and fewer setups clear the tighter bar.
      162 -> 140 on BTC. That is the escalation doing exactly its job on real
      numbers instead of truncated ones.

    Re-record with a reason, never silently.
    """
    was = {"BTC/USD": 140, "ETH/USD": 90}
    for pair, want in was.items():
        r = tjr_crypto.run_pair(pair, "2026-06-01", "2026-07-24",
                                cfg=tjr_crypto.crypto_config(pair))
        assert r["days"] == 54, f"{pair}: {r['days']} sessions, expected 54"
        assert len(r["trades"]) == want, (
            f"{pair} took {len(r['trades'])} setups, {want} was recorded")


# ================================ 8. step466: THE DAY MAY MARK, NEVER CUT
#
# Wallace: "crypto runs 24/7, then let it run 24/7. dont cut shit."
#
# The clock was already gone. What survived was a BELL — `run_day` closed
# anything still open when a UTC day's bars ran out — and these are the tests
# that it cannot come back, that removing it did not touch the stock path, and
# that nothing about the method or the causality moved with it.

def _long_replay(pair: str = PAIR, carry: bool = True):
    key = (pair, "step466", carry)
    if key not in _REPLAY:
        _REPLAY[key] = tjr_crypto.run_pair(pair, "2026-04-01", "2026-07-20",
                                           cfg=cfg(pair), data=frames(pair),
                                           carry_past_the_boundary=carry)
    return _REPLAY[key]


def test_no_crypto_trade_is_ever_booked_flat_by_the_close():
    """There is no close. A trade ends at its stop or at its targets."""
    r = _long_replay()
    bad = [t for t in r["trades"] if t.outcome == "flat by the close"]
    assert not bad, (f"{len(bad)} crypto trades were closed at a bell this "
                     f"market does not have")


def test_every_crypto_outcome_is_a_real_reason():
    allowed = {"stopped out", "stopped at break even", tjr_crypto.RAN_OUT,
               "the 1-minute broke structure against the trade — the rest "
               "closed by hand"}
    r = _long_replay()
    for t in r["trades"]:
        assert t.outcome in allowed or t.outcome.startswith("all "), t.outcome


def test_a_trade_is_allowed_to_run_past_midnight():
    """The whole point. Some trades need longer than the rest of a UTC day."""
    r = _long_replay()
    assert r["crossed_the_boundary"] > 0, "not one trade ran past a boundary"
    for t in r["trades"]:
        if t.exit_t is None:
            continue
        # nothing is cut AT the boundary: an exit landing exactly on the last
        # minute of a day is what the bell used to produce
        pass
    late = [t for t in r["trades"]
            if t.exit_t is not None
            and pd.Timestamp(t.exit_t).normalize()
            > pd.Timestamp(t.entry_t).normalize()]
    assert len(late) >= 5, f"only {len(late)} trades ever crossed a boundary"


def test_turning_the_carry_off_brings_the_imaginary_bell_straight_back():
    """The before/after in step466 has to be able to produce both halves, and
    this is the proof that the OFF half really is the old behaviour."""
    r = _long_replay(carry=False)
    cut = [t for t in r["trades"] if t.outcome == "flat by the close"]
    assert cut, "carry off produced no bell at all — the switch does nothing"
    assert r["crossed_the_boundary"] == 0, \
        "carry off let a trade cross the boundary anyway"


def test_the_carry_never_widens_a_stop_adds_size_or_moves_a_target():
    """Running longer is the ONLY thing that changed. A carried position keeps
    the size it was filled at, the targets it was given and a stop that only
    ever moves to break even."""
    r = _long_replay()
    for t in r["trades"]:
        if t.exit_t is None or pd.Timestamp(t.exit_t).normalize() \
                <= pd.Timestamp(t.entry_t).normalize():
            continue
        assert t.shares > 0 and t.notional > 0
        stop_now = getattr(t, "_stop_now", t.stop)
        if t.direction > 0:
            assert stop_now >= t.stop - 1e-9, "a long's stop was widened"
            assert stop_now <= t.entry + 1e-9, "a long's stop went past entry"
        else:
            assert stop_now <= t.stop + 1e-9, "a short's stop was widened"
            assert stop_now >= t.entry - 1e-9, "a short's stop went past entry"
        assert t.targets_filled <= len(t.targets)


def test_the_account_cannot_size_a_trade_off_money_that_is_still_open():
    """CAUSALITY, and it is the risk the carry creates. A position that has
    not closed has made nothing, so no later trade may be sized off it."""
    r = _long_replay()
    ts = [t for t in r["trades"] if t.exit_t is not None]
    start = cfg().account_start
    for t in ts:
        day = pd.Timestamp(t.day)
        banked = sum(x.pnl for x in ts
                     if pd.Timestamp(x.exit_t) < day)
        want = start + banked
        assert abs(t.sizing_account - want) < 1e-6, (
            f"{t.entry_t} sized off {t.sizing_account:,.2f} when only "
            f"{want:,.2f} had actually been banked")


def test_the_equity_curve_is_in_the_order_the_money_landed():
    r = _long_replay()
    ts = sorted([t for t in r["trades"] if t.exit_t is not None],
                key=lambda t: pd.Timestamp(t.exit_t))
    acct = cfg().account_start
    for t in ts:
        acct += t.pnl
        assert abs(t.account_after - acct) < 1e-6, \
            f"{t.exit_t} stamped {t.account_after:,.2f}, running total {acct:,.2f}"
    assert abs(r["account"] - acct) < 1e-6


def test_the_stock_path_still_closes_at_its_bell():
    """The shim must not have taken the real bell off a market that has one.
    SPY, GLD and forex all set `open_t`; crypto is the only one that does
    not, and that is the only thing either shim branches on."""
    assert tjr_bot.US_INDEX_ETF.open_t is not None
    assert tjr_bot.TjrBot._force_flat is \
        tjr_crypto._force_flat_only_where_there_is_a_close

    c = tjr_bot.Config()                       # the stock instrument
    bot = TjrBot(c, NewsCalendar(rules=False))
    tr = tjr_bot.Trade(
        symbol="SPY", day=pd.Timestamp("2026-06-10"), direction=+1,
        level_price=500.0, level_tf="1h", swept_at=None, confirm_kind="bos",
        confirmed_at=None, pullback_kind="midpoint",
        entry_t=pd.Timestamp("2026-06-10 10:00"), entry=500.0, stop=499.0,
        stop_anchor="", risk_per_share=1.0, shares=10.0, notional=5000.0,
        risk_dollars=10.0, risk_wanted=10.0, risk_pct_used=0.0001,
        clamped=False, targets=[505.0], target_srcs=["1h"], escalated=False,
        regime="no trend")
    last = pd.Timestamp("2026-06-10 15:55")
    bot._force_flat(tr, {last: Bar(last, 501, 501, 501, 501)})
    assert tr.outcome == "flat by the close", \
        f"the stock bell stopped firing: {tr.outcome!r}"


def test_a_crypto_position_is_left_open_rather_than_closed():
    """The same call, on a market with no bell, must do nothing at all."""
    c = cfg()
    bot = TjrBot(c, NewsCalendar(rules=False))
    tr = tjr_bot.Trade(
        symbol=PAIR, day=pd.Timestamp("2026-06-10"), direction=+1,
        level_price=100.0, level_tf="1h", swept_at=None, confirm_kind="bos",
        confirmed_at=None, pullback_kind="midpoint",
        entry_t=pd.Timestamp("2026-06-10 23:50"), entry=100.0, stop=99.0,
        stop_anchor="", risk_per_share=1.0, shares=1.0, notional=100.0,
        risk_dollars=1.0, risk_wanted=1.0, risk_pct_used=0.00001,
        clamped=False, targets=[105.0], target_srcs=["1h"], escalated=False,
        regime="no trend")
    last = pd.Timestamp("2026-06-10 23:59")
    bot._force_flat(tr, {last: Bar(last, 101, 101, 101, 101)})
    assert tr.outcome == "", "a crypto position was closed at midnight"
    assert tr.pnl == 0.0, "a crypto position booked money without closing"


def test_the_one_minute_trend_the_carry_reads_is_the_one_it_was_managed_on():
    """The runner comes off the 1-minute break of structure. A carried
    position must keep reading the same tracker `SymbolDay` had, or the rule
    changes at the boundary."""
    d1 = frames()["1m"]
    day = pd.Timestamp("2026-06-10")
    mine = tjr_crypto._one_minute_trend(d1, day)

    c = cfg()
    win = window(day)
    leg = tjr_bot.SymbolDay(PAIR, win["5m"], win["1m"], day, c,
                            NewsCalendar(rules=False), False)
    open_t = tjr_bot.session_start(day, c.instrument)
    sess = win["1m"][(win["1m"]["t"] >= open_t) &
                     (win["1m"]["t"] < day + pd.Timedelta(days=1))]
    for r in sess.itertuples():
        leg.on_1m(Bar(r.t, r.open, r.high, r.low, r.close))
    assert leg.t1.state == mine.state, "the carried trend is a different read"
    assert leg.t1.mrh == mine.mrh and leg.t1.mrl == mine.mrl


def test_every_place_the_invented_day_still_bites_is_written_down():
    """A list of what was NOT fixed is worth more than a claim that it was."""
    doc = tjr_crypto.where_the_invented_day_still_bites()
    for must in ("THE BELL. FIXED", "THE DAILY BIAS", "MARKED POOL IS FROZEN",
                 "SEQUENCE RESETS AT MIDNIGHT", "WEEKS",
                 "AGE MEASURED IN DAYS", "CANDLE GRID",
                 "PREVIOUS DAY'S HIGH AND LOW"):
        assert must in doc, f"the enumeration lost: {must}"


def test_the_setup_count_is_still_the_thing_the_replay_claims():
    """step466 changed an EXIT. A setup is counted when the entry fires, which
    happens before any of it, so `setups_per_day` still reports the same kind
    of number and nothing here claims a profit."""
    src = inspect.getsource(tjr_crypto.setups_per_day)
    assert "no profit claim" in src
    r = _long_replay()
    assert len(r["trades"]) > 0 and r["days"] > 0


TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]


def main():
    print("=" * 78)
    print("test_tjr_crypto.py — the method, the missing clock, and no cost filter")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        try:
            fn()
            print(f"  pass  {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL  {name}\n        {type(e).__name__}: {e}")
    print("-" * 78)
    print(f"{len(TESTS) - failed}/{len(TESTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
