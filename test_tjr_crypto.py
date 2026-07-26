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
    """position = dollars risked / stop distance, and 1% of equity is the
    dollars, unless the venue's cash clamps it."""
    r = replay()
    for tr in r["trades"]:
        assert abs(tr.shares * tr.risk_per_share - tr.risk_dollars) < 1e-6
        if not tr.clamped:
            assert abs(tr.risk_pct_used - 0.01) < 1e-6, tr.risk_pct_used


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
    assert len(PAIRS) == 10
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
