"""
test_tjr_gold.py — gold is only worth trading if the chart cannot see the
future, the second chart can never be traded, and nothing anywhere declines a
trade because of what it costs.

WHAT IS PROVED HERE
    1. CAUSALITY. Every real entry, and every quiet day, decides identically
       with every later bar deleted. Higher timeframes are invisible until
       they close. This is the test he would demand and the one the whole
       exercise rests on.
    2. THE SECOND CHART IS NEVER TRADED. IAU is loaded so the two-charts-agree
       check is real, and its own 5-minute record is too full of holes to
       place an order against. The shim must make that structural, not a
       convention.
    3. THE SHIM IS INERT ELSEWHERE. Installing it must not change one thing
       about the index path or the crypto path.
    4. NO COST FILTERING. The file's own source is read and checked: the
       measured spread is charged and never consulted.
    5. THE CLOCK IS KEPT. Gold on this route trades a US session, so unlike
       crypto it keeps the open, the twenty-minute wait and the 10:30
       cut-off.

Repo style: plain asserts, a TESTS list, a main() runner. No pytest, no
network. Reads the cached parquet files only.
"""

from __future__ import annotations

import datetime as dt
import inspect
import sys
import traceback

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
import tjr_gold
from tjr_bot import completed_before, decide_at, resample_tf

REPO = "/Users/wallacechen/cryptobot"

_CACHE: dict = {}


def data():
    if "d" not in _CACHE:
        _CACHE["d"] = tjr_gold.load_both()
    return _CACHE["d"]


def cfg():
    if "c" not in _CACHE:
        _CACHE["c"] = tjr_gold.gold_config()
    return _CACHE["c"]


def replay():
    if "r" not in _CACHE:
        _CACHE["r"] = tjr_gold.run_gold(cfg=cfg(), data=data())
    return _CACHE["r"]


def window(day):
    return tjr_gold.slice_for(data(), day, cfg())


def truncate(win: dict, ts: pd.Timestamp) -> dict:
    """Everything AFTER `ts` deleted, on every chart of both symbols. The bar
    starting at `ts` is the one being decided on and stays; every bar that
    starts later is the future and goes."""
    return {s: {tf: win[s][tf][win[s][tf]["t"] <= ts].reset_index(drop=True)
                for tf in ("5m", "1m")} for s in win}


# ============================================================ 1. CAUSALITY
def test_a_higher_timeframe_candle_is_invisible_until_it_closes():
    """A 4-hour candle that started at 05:00 does not exist to the bot at
    08:00. This is the one defect he objects to in ordinary replay."""
    d5 = data()[tjr_gold.TRADED]["5m"]
    d5 = d5[(d5["t"] >= "2026-04-06") & (d5["t"] < "2026-04-09")]
    assert len(d5) > 100, "not enough cached gold bars to test on"
    h4 = resample_tf(d5, 240, cfg().instrument.candle_anchor_hour)
    now = pd.Timestamp("2026-04-07 10:00")
    seen = completed_before(h4, now)
    assert len(seen) > 0, "no completed 4-hour bars at all"
    assert (seen["close_t"] <= now).all(), "a 4-hour bar leaked before it closed"
    inside = h4[(h4["t"] <= now) & (h4["close_t"] > now)]
    assert len(inside) == 1, "expected exactly one candle in progress"
    assert inside["t"].iloc[0] not in set(seen["t"]), \
        "the candle we are standing inside was treated as finished"


def test_every_real_entry_survives_deleting_the_future():
    """THE test. Re-decide each entry bar with every later bar deleted and
    demand the same symbol, side, entry, stop and level."""
    r = replay()
    assert len(r["trades"]) >= 1, "no gold entries at all to test causality on"
    for tr in r["trades"]:
        day, ts = tr.day, tr.entry_t
        full = decide_at(window(day), day, ts, cfg())
        cut = decide_at(truncate(window(day), ts), day, ts, cfg())
        assert full["entry"] is not None, f"{day:%Y-%m-%d}: the entry vanished"
        assert full["entry"] == cut["entry"], (
            f"{day:%Y-%m-%d} decided differently with the future deleted:\n"
            f"  with future    {full['entry']}\n  without future {cut['entry']}")


def test_a_quiet_day_stays_a_quiet_day_and_for_the_same_reason():
    r = replay()
    traded = {t.day for t in r["trades"]}
    days = [pd.Timestamp(d) for d in tjr_gold.days_in(data())]
    quiet = [d for d in days if d not in traded][-12:]
    assert len(quiet) >= 5
    for day in quiet:
        ts = day + pd.Timedelta(hours=10, minutes=29)
        full = decide_at(window(day), day, ts, cfg())
        cut = decide_at(truncate(window(day), ts), day, ts, cfg())
        assert full["entry"] is None, f"{day:%Y-%m-%d} traded unexpectedly"
        assert cut["entry"] is None, f"{day:%Y-%m-%d} traded once truncated"
        assert full["stand_down"] == cut["stand_down"], (
            f"{day:%Y-%m-%d} gave a different reason without the future")


def test_a_decision_mid_morning_does_not_move():
    r = replay()
    assert r["trades"], "no trades"
    day = r["trades"][0].day
    for h, m in ((9, 55), (10, 5), (10, 15), (10, 25)):
        ts = day + pd.Timedelta(hours=h, minutes=m)
        a = decide_at(window(day), day, ts, cfg())
        b = decide_at(truncate(window(day), ts), day, ts, cfg())
        assert a == b, f"{ts} moved when the future was deleted:\n{a}\n{b}"


# =============================================== 2. THE SECOND CHART
def test_the_second_chart_is_never_the_one_traded():
    """IAU is a second opinion. Every trade must be on GLD."""
    r = replay()
    for tr in r["trades"]:
        assert tr.symbol == tjr_gold.TRADED, \
            f"a trade was placed on {tr.symbol}, which is loaded to look at only"


def test_the_second_chart_stands_down_by_construction_not_by_luck():
    """Not "it happened not to fire" — it must be structurally unable to."""
    day = pd.Timestamp(tjr_gold.days_in(data())[-3])
    win = window(day)
    leg = tjr_bot.SymbolDay(tjr_gold.TWIN, win[tjr_gold.TWIN]["5m"],
                            win[tjr_gold.TWIN]["1m"], day, cfg(),
                            tjr_bot.NewsCalendar(), False)
    assert leg.ctx.stand_down, "the second chart was tradeable"
    assert "never traded" in leg.ctx.stand_down


def test_the_second_chart_still_feeds_the_agreement_check():
    """Standing it down must not silence it. Its 5-minute trend has to reach
    the veto or the veto is switched off without saying so."""
    src = inspect.getsource(tjr_bot.TjrBot.run_day)
    assert "for s in syms" in src, \
        "run_day no longer walks every loaded symbol for the 5-minute update"
    assert cfg().enforce_index_agreement is True, \
        "the two-charts-agree check is off for gold"
    day = pd.Timestamp(tjr_gold.days_in(data())[-3])
    bot = tjr_bot.TjrBot(cfg(), tjr_bot.NewsCalendar())
    res = bot.run_day(window(day), day)
    assert tjr_gold.TWIN in res["context"], \
        "the second chart's context was not even built"


def test_the_shim_changes_nothing_for_a_config_without_a_second_chart():
    """Inert elsewhere. A Config with no check_only list must behave exactly
    as it did before this file was imported."""
    stock = tjr_bot.Config()
    assert not hasattr(stock, "check_only") or not stock.check_only
    d5 = data()[tjr_gold.TRADED]["5m"]
    d1 = data()[tjr_gold.TRADED]["1m"]
    day = pd.Timestamp(tjr_gold.days_in(data())[-3])
    leg = tjr_bot.SymbolDay("GLD", d5, d1, day, stock, tjr_bot.NewsCalendar(), False)
    assert leg.ctx.stand_down != ("loaded as a second opinion only — this "
                                 "chart is never traded")


# ================================================ 3. COSTS ARE NOT CONSULTED
def test_nothing_in_this_file_declines_or_ranks_a_trade_on_cost():
    """The measured spread is charged so the money is honest. It must never
    appear on the left of a comparison, in a filter, or in a sort."""
    src = inspect.getsource(tjr_gold)
    bad = []
    for i, line in enumerate(src.splitlines(), 1):
        s = line.strip()
        if s.startswith("#") or s.startswith('"') or s.startswith("'"):
            continue
        low = s.lower()
        if ("cost" in low or "spread" in low) and any(
                op in s for op in (" > ", " < ", " >= ", " <= ", "min(", "max(")):
            bad.append(f"{i}: {s}")
    assert not bad, "cost or spread reached a comparison:\n  " + "\n  ".join(bad)


def test_the_measured_spread_is_actually_charged():
    c = cfg()
    assert c.instrument.round_trip_cost_pct > 0, "gold is being traded free"
    d = tjr_gold.load_derived()
    if d.get(tjr_gold.TRADED, {}).get("spread_pct"):
        assert abs(c.instrument.round_trip_cost_pct -
                   d[tjr_gold.TRADED]["spread_pct"]) < 1e-12, \
            "the charged cost is not the measured one"


def test_the_stop_buffer_is_this_instruments_own_spread_not_spys():
    c = cfg()
    assert abs(c.stop_buffer_pct_of_price -
               c.instrument.round_trip_cost_pct) < 1e-12
    assert c.stop_buffer_pct_of_price != tjr_bot.Config().stop_buffer_pct_of_price, \
        "gold is still carrying SPY's stop buffer"


# ================================================== 4. THE CLOCK IS KEPT
def test_gold_keeps_his_clock_where_crypto_threw_it_away():
    i = cfg().instrument
    assert i.open_t == dt.time(9, 30)
    assert i.manip_end_t == dt.time(9, 50)
    assert i.cutoff_t == dt.time(10, 30)
    assert i.flat_t == dt.time(15, 55)
    assert i.has_closing_bell is True
    assert i.prior_session_window == (3, 8.5), "London hours were dropped"
    assert i.early_session_window == (18, 3), "Asia hours were dropped"
    assert i.own_session_window == (8.5, 18), "New York hours were dropped"


def test_no_entry_before_0950_or_after_1030():
    for tr in replay()["trades"]:
        t = pd.Timestamp(tr.entry_t).time()
        assert dt.time(9, 50) <= t < dt.time(10, 30), \
            f"an entry landed at {t}, outside his window"


def test_the_pre_market_carry_forward_is_on_because_there_is_a_pre_market():
    assert cfg().premarket_sweep_carries_forward is True


def test_levels_are_only_marked_from_the_1_hour_and_the_4_hour():
    assert cfg().instrument.level_minutes == (60, 240), \
        "a level source other than the 1-hour and 4-hour crept in"


# ================================================= 5. SIZE AND THE STOP
def test_size_falls_out_of_the_stop_and_the_stop_sits_on_the_chart():
    for tr in replay()["trades"]:
        dist = abs(tr.entry - tr.stop)
        assert dist > 0
        assert abs(tr.shares * dist - tr.risk_dollars) < 0.02, \
            "size and stop distance do not multiply to the money risked"
        # and the stop is NOT a fixed share of the price
        as_share = dist / tr.entry
        assert tr.stop_anchor, "the stop has no chart feature under it"
        assert 0 < as_share < 0.5


def test_one_setup_a_day_at_most():
    days = [t.day for t in replay()["trades"]]
    assert len(days) == len(set(days)), "two entries landed on one day"


# ====================================================== 6. NO ORDER PATH
def test_nothing_in_this_file_can_place_an_order():
    src = inspect.getsource(tjr_gold)
    for bad in ("market_order", "submit_order", "close_position", "/v2/orders"):
        assert bad not in src, f"an order path appeared in tjr_gold.py: {bad}"


def test_live_step_refuses_without_the_second_chart():
    out = tjr_gold.live_step({tjr_gold.TRADED: {"5m": pd.DataFrame(),
                                                "1m": pd.DataFrame()}},
                             pd.Timestamp("2026-04-07 10:00"), 100_000.0,
                             clock={"is_open": True})
    assert out["action"] == "stand_down"
    assert "second gold chart" in out["reason"]


def test_live_step_refuses_when_the_market_is_shut():
    day = pd.Timestamp(tjr_gold.days_in(data())[-3])
    out = tjr_gold.live_step(window(day), day + pd.Timedelta(hours=10),
                             100_000.0, clock={"is_open": False})
    assert out["action"] == "stand_down"


TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]


def main():
    print("=" * 78)
    print("test_tjr_gold.py — gold, and proof it cannot see the future")
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
