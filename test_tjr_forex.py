"""
test_tjr_forex.py — the currency half is alert-only, so the message IS the
product. These tests treat it that way.

WHAT IS PROVED HERE
    1. CAUSALITY. Every real entry, and every quiet day, decides identically
       with every later bar deleted. Higher timeframes stay invisible until
       they close. Same standard as every other market on this desk.
    2. THE DAY ROLLS AT FIVE O'CLOCK NEW YORK, which is where currencies
       actually roll — and the shim that does it must leave the crypto and
       stock paths untouched.
    3. THE CLOCK IS KEPT. Crypto threw the times away; currencies do not.
       The London and New York hours, the twenty-minute wait and the 10:30
       cut-off all have to be there.
    4. THE SIZE IS RIGHT, worked out by hand for both pairs, because the
       whole point is that he never does this arithmetic.
    5. THE MESSAGE CARRIES EVERYTHING and says what every percentage is a
       percentage OF. A message he has to think about costs him the trade.
    6. NO COST FILTERING and NO ORDER PATH anywhere in the file.

Repo style: plain asserts, a TESTS list, a main() runner. No pytest. NO
NETWORK — the one feed test builds a bank-format record in memory and hands
it to the reader through a stand-in for the http library.
"""

from __future__ import annotations

import datetime as dt
import inspect
import lzma
import re
import struct
import sys
import traceback
import types

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_alerts
import tjr_bot
import tjr_forex
from tjr_bot import completed_before, decide_at, resample_tf

REPO = "/Users/wallacechen/cryptobot"
PAIR = "GBP/USD"

_CACHE: dict = {}


def data(pair=PAIR):
    if pair not in _CACHE:
        _CACHE[pair] = tjr_forex.load(pair)
    return _CACHE[pair]


def cfg(pair=PAIR):
    k = "cfg:" + pair
    if k not in _CACHE:
        _CACHE[k] = tjr_forex.forex_config(pair)
    return _CACHE[k]


def replay(pair=PAIR):
    k = "rep:" + pair
    if k not in _CACHE:
        _CACHE[k] = tjr_forex.run_pair(pair, cfg=cfg(pair), data=data(pair))
    return _CACHE[k]


def window(day, pair=PAIR):
    return {pair: tjr_forex.slice_for(data(pair), day, cfg(pair))}


def truncate(win: dict, ts: pd.Timestamp) -> dict:
    """Everything AFTER `ts` deleted. The bar starting at `ts` is the one
    being decided on and stays; every later bar is the future and goes."""
    return {s: {tf: win[s][tf][win[s][tf]["t"] <= ts].reset_index(drop=True)
                for tf in ("5m", "1m")} for s in win}


def mk(rows, base="2026-01-05 09:30"):
    base = pd.Timestamp(base)
    return pd.DataFrame([{"t": base + pd.Timedelta(minutes=m), "open": o,
                          "high": h, "low": l, "close": c}
                         for m, o, h, l, c in rows])


# ============================================================ 1. CAUSALITY
def test_a_higher_timeframe_candle_is_invisible_until_it_closes():
    d5 = data()["5m"]
    end = d5["t"].max().normalize()
    d5 = d5[(d5["t"] >= end - pd.Timedelta(days=4)) & (d5["t"] < end)]
    assert len(d5) > 200, "not enough cached currency bars to test on"
    h4 = resample_tf(d5, 240, cfg().instrument.candle_anchor_hour)
    now = pd.Timestamp(d5["t"].max()).normalize() + pd.Timedelta(hours=10)
    seen = completed_before(h4, now)
    assert len(seen) > 0
    assert (seen["close_t"] <= now).all(), "a 4-hour candle leaked before it closed"
    inside = h4[(h4["t"] <= now) & (h4["close_t"] > now)]
    assert len(inside) == 1, "expected exactly one candle in progress"
    assert inside["t"].iloc[0] not in set(seen["t"]), \
        "the candle we are standing inside was treated as finished"


def test_every_real_entry_survives_deleting_the_future():
    r = replay()
    assert len(r["trades"]) >= 1, "no currency entries at all to test on"
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
    days = [pd.Timestamp(d) for d in tjr_forex.days_in(data())]
    quiet = [d for d in days if d not in traded][-12:]
    assert len(quiet) >= 5
    for day in quiet:
        ts = day + pd.Timedelta(hours=10, minutes=29)
        full = decide_at(window(day), day, ts, cfg())
        cut = decide_at(truncate(window(day), ts), day, ts, cfg())
        assert full["entry"] is None, f"{day:%Y-%m-%d} traded unexpectedly"
        assert cut["entry"] is None, f"{day:%Y-%m-%d} traded once truncated"
        assert full["stand_down"] == cut["stand_down"], \
            f"{day:%Y-%m-%d} gave a different reason without the future"


# =============================================== 2. THE FIVE O'CLOCK ROLL
def test_the_currency_day_is_cut_at_five_oclock_new_york():
    """A currency day runs 17:00 to 17:00. A candle built the other way puts
    the direction read on the wrong day's high and low."""
    inst = cfg().instrument
    assert inst.day_boundary_hour == 17
    d = mk([(i * 60, 1.30, 1.30 + i * 0.001, 1.29, 1.30) for i in range(40)],
           base="2026-01-05 00:00")
    daily = tjr_bot.daily_bars(d, inst)
    for t in daily["t"]:
        assert pd.Timestamp(t).hour == 17, f"a daily candle started at {t}, not 17:00"
    for t, ct in zip(daily["t"], daily["close_t"]):
        assert ct - t == pd.Timedelta(days=1), "a currency day was not 24 hours"


def test_the_roll_shim_leaves_crypto_and_stocks_exactly_as_they_were():
    """Inert elsewhere, which is the whole justification for a shim."""
    d = mk([(i * 60, 10, 11, 9, 10.5) for i in range(60)], base="2026-01-05 00:00")
    # a stock: cut by the bell, as before
    stock = tjr_bot.daily_bars(d, tjr_bot.US_INDEX_ETF)
    direct = tjr_forex._ORIGINAL_DAILY_BARS(d, tjr_bot.US_INDEX_ETF)
    assert stock.equals(direct), "the shim changed the stock daily candle"
    # a market with no bell that really does roll at midnight
    midnight = tjr_bot.Instrument(name="round_the_clock", round_trip_cost_pct=0.0,
                                  day_boundary_hour=0, has_closing_bell=False)
    assert tjr_bot.daily_bars(d, midnight).equals(
        tjr_forex._ORIGINAL_DAILY_BARS(d, midnight)), \
        "the shim changed a midnight-rolling market"


def test_the_previous_day_level_is_the_previous_currency_day():
    inst = cfg().instrument
    d5 = data()["5m"]
    day = pd.Timestamp(tjr_forex.days_in(data())[-2])
    hist = d5[d5["t"] < day]
    lv = tjr_bot.session_levels(hist, day, inst)
    tags = {x.tf for x in lv}
    assert "prev_day" in tags, "no previous-day level was marked at all"
    for x in lv:
        if x.tf == "prev_day":
            assert pd.Timestamp(x.formed).hour == 17, \
                "the previous currency day did not end at five o'clock"


def test_monday_still_gets_a_previous_day_and_a_previous_new_york():
    """THE MONDAY HOLE. Currencies are shut all weekend and open again on
    Sunday evening, so "the day before" a Monday is Friday, not Sunday. A
    version that stepped back exactly one calendar day found Sunday, whose
    own currency day is empty, and marked nothing at all — on one morning in
    five, silently."""
    inst = cfg().instrument
    d5 = data()["5m"]
    mondays = [pd.Timestamp(d) for d in tjr_forex.days_in(data())
               if pd.Timestamp(d).weekday() == 0]
    assert len(mondays) >= 8, "not enough Mondays in the cache to check"
    for day in mondays[-8:]:
        lv = tjr_bot.session_levels(d5[d5["t"] < day], day, inst)
        tags = {x.tf for x in lv}
        assert "prev_day" in tags, \
            f"{day:%Y-%m-%d} is a Monday with no previous-day level"
        assert "new_york" in tags, \
            f"{day:%Y-%m-%d} is a Monday with no previous New York levels"
        for x in lv:
            if x.tf == "prev_day":
                # Friday's currency day ended at five o'clock on Friday
                assert pd.Timestamp(x.formed).weekday() == 4, \
                    f"{day:%Y-%m-%d}: the previous currency day was not Friday's"


def test_the_level_shim_leaves_the_index_path_byte_identical():
    """The dispatch must be invisible to the market it was not written for."""
    d5 = data()["5m"]
    day = pd.Timestamp(tjr_forex.days_in(data())[-2])
    hist = d5[d5["t"] < day]
    a = tjr_bot.session_levels(hist, day, tjr_bot.US_INDEX_ETF)
    b = tjr_forex._ORIGINAL_SESSION_LEVELS(hist, day, tjr_bot.US_INDEX_ETF)
    assert a == b, "the shim changed what the index path marks"


# ================================================== 3. THE CLOCK IS KEPT
def test_currencies_keep_his_sessions_where_crypto_threw_them_away():
    i = cfg().instrument
    assert i.prior_session_window == (3, 8.5), "London hours were dropped"
    assert i.early_session_window == (18, 3), "Asia hours were dropped"
    assert i.own_session_window == (8.5, 18), "New York hours were dropped"
    assert i.open_t == dt.time(9, 30)
    assert i.manip_end_t == dt.time(9, 50)
    assert i.cutoff_t == dt.time(10, 30)
    assert i.has_closing_bell is False, "currencies do not have a closing bell"


def test_no_entry_before_0950_or_after_1030():
    for pair in tjr_forex.PAIRS:
        for tr in replay(pair)["trades"]:
            t = pd.Timestamp(tr.entry_t).time()
            assert dt.time(9, 50) <= t < dt.time(10, 30), \
                f"{pair}: an entry landed at {t}, outside his window"


def test_the_week_starts_and_ends_where_the_market_says():
    o = tjr_forex.currencies_open
    assert not o(dt.datetime(2026, 7, 25, 12)), "Saturday was treated as open"
    assert not o(dt.datetime(2026, 7, 26, 12)), "Sunday lunchtime was treated as open"
    assert o(dt.datetime(2026, 7, 26, 18)), "Sunday evening should be open"
    assert o(dt.datetime(2026, 7, 24, 12)), "Friday morning should be open"
    assert not o(dt.datetime(2026, 7, 24, 18)), "Friday after the roll should be shut"
    assert o(dt.datetime(2026, 7, 22, 3)), "Wednesday London should be open"


def test_live_step_refuses_outside_his_window_and_when_the_week_is_over():
    d = data()
    day = pd.Timestamp(tjr_forex.days_in(d)[-2])
    early = tjr_forex.live_step(PAIR, d, day + pd.Timedelta(hours=8),
                                100_000.0, cfg=cfg())
    assert early["action"] == "stand_down" and "before the New York open" in early["reason"]
    late = tjr_forex.live_step(PAIR, d, day + pd.Timedelta(hours=11),
                               100_000.0, cfg=cfg())
    assert late["action"] == "stand_down" and "10:30" in late["reason"]
    shut = tjr_forex.live_step(PAIR, d, day + pd.Timedelta(hours=10),
                               100_000.0, cfg=cfg(), clock_open=False)
    assert shut["action"] == "stand_down" and "shut" in shut["reason"]


# =============================================== 4. THE SIZE, BY HAND
def test_size_on_a_dollar_pair_is_set_off_the_tightest_stop():
    """GBP/USD at 1.2500 whose tightest stop is 0.20% of price: that stop is
    25 pips, so one percent of a $100,000 account buys 400,000 pounds — four
    standard lots, each pip worth $40. That is the SET size. A 50-pip stop
    that day does not halve it; it doubles what the trade costs."""
    s = tjr_alerts.position_size("currencies", "GBP/USD", 100_000.0, 1.25,
                                 0.0025, 0.002, 1.0)
    assert abs(s["units"] - 400_000) < 1, s
    assert abs(s["lots"] - 4.0) < 1e-6
    assert abs(s["per_step"] - 40.0) < 1e-6
    assert abs(s["risk_dollars"] - 1000.0) < 0.01
    wide = tjr_alerts.position_size("currencies", "GBP/USD", 100_000.0, 1.25,
                                    0.0050, 0.002, 1.0)
    assert abs(wide["units"] - s["units"]) < 1e-6, "the set size moved"
    assert abs(wide["risk_share_pct"] - 2.0) < 1e-9


def test_size_on_a_yen_pair_converts_the_profit_into_dollars():
    """GBP/JPY at 200 with a tightest stop of 0.06% of price — 12 pips. The
    profit arrives in yen, so a dollar per yen is 1.34/200 = 0.0067, and one
    percent of $100,000 buys 1,000 / (0.12 x 0.0067) = 1,243,781 pounds."""
    upq = tjr_forex.usd_per_quote("GBP/JPY", 1.34, 200.0)
    assert abs(upq - 0.0067) < 1e-9
    s = tjr_alerts.position_size("currencies", "GBP/JPY", 100_000.0, 200.0,
                                 0.12, 0.0006, upq)
    assert abs(s["units"] - 1_243_781.09) < 1.0, s
    assert abs(s["risk_dollars"] - 1000.0) < 0.01
    assert abs(12 * s["per_step"] - 1000.0) < 0.01


def test_a_dollar_pair_needs_no_conversion_at_all():
    assert tjr_forex.usd_per_quote("GBP/USD", 1.34, 200.0) == 1.0


def test_the_two_pairs_do_not_share_a_pip():
    assert tjr_alerts.pip_size("GBP/USD") == 0.0001
    assert tjr_alerts.pip_size("GBP/JPY") == 0.01
    assert tjr_alerts.to_pips("GBP/USD", 0.0025) == 25.0
    assert tjr_alerts.to_pips("GBP/JPY", 0.30) == 30.0


def test_the_alert_never_gets_a_share_count_from_the_bot():
    """tjr_bot sizes as money risked over the distance to the stop, which is
    right where the price is in dollars and WRONG on a yen pair by roughly
    the yen rate. The size has to come from position_size, where the
    conversion happens on purpose, so the raw count must not even be offered.
    """
    d = data()
    day = pd.Timestamp(tjr_forex.days_in(d)[-2])
    out = tjr_forex.live_step(PAIR, d, day + pd.Timedelta(hours=10),
                              100_000.0, cfg=cfg())
    assert "shares" not in out, "a raw share count reached the alert layer"
    src = inspect.getsource(tjr_forex.live_step)
    assert "tr.shares" not in src, "live_step still hands out tr.shares"
    src2 = inspect.getsource(tjr_alerts.trade_block)
    assert "sig[\"shares\"]" not in src2, \
        "the alert reads a share count instead of working the size out"


def test_size_falls_out_of_the_stop_on_every_real_setup():
    for pair in tjr_forex.PAIRS:
        for tr in replay(pair)["trades"]:
            dist = abs(tr.entry - tr.stop)
            assert dist > 0
            assert tr.stop_anchor, "the stop has no chart feature under it"
            assert abs(dist / tr.entry) < 0.5


# ================================================= 5. THE MESSAGE ITSELF
def sample_sig(pair="GBP/JPY"):
    return {"market": "currencies", "symbol": pair, "direction": -1,
            "reference_price": 218.470, "stop": 218.760,
            "targets": [217.900, 217.320],
            "target_sources": ["a 15-minute draw on liquidity",
                               "a prev_day draw on liquidity"],
            "level_tf": "prev_day", "level_price": 218.760,
            "confirmed_by": "5-minute break of structure",
            "pullback_into": "the midpoint",
            "risk_dollars": 1000.0, "risk_wanted": 1000.0,
            "tightest_stop_pct": 0.0006}


def test_the_message_carries_everything_he_needs_to_place_it():
    title, msg = tjr_alerts.entry_message(
        sample_sig(), 100_000.0, 1.34 / 218.47,
        fired_at=dt.datetime(2026, 7, 24, 9, 58))
    # THE MESSAGE IS THE COMPACT TABLE HE ASKED FOR, 2026-07-26: "instead of
    # all these words, just do tp($,%) if theres only 1, if theres more than
    # one just do tp1, tp2. and same for sl($,%)." The long-form labels this
    # used to look for ("Enter around", "First target") were rewritten then
    # and this list had not caught up.
    for must in ("SELL", "GBP/JPY", "Entry", "SL", "TP1", "TP2",
                 "standard lots", "Margin", "Leverage",
                 "Why:", "New York time"):
        assert must in msg, f"the alert is missing: {must}"
    assert "218.470" in msg and "218.760" in msg
    assert "217.900" in msg and "217.320" in msg
    assert "09:58" in msg
    assert "CURRENCIES" in title


def test_the_message_says_what_to_do_when_the_first_target_is_reached():
    _, msg = tjr_alerts.entry_message(sample_sig(), 100_000.0, 1.0)
    assert "take half off" in msg.lower()
    assert "move the stop" in msg.lower() or "move your stop" in msg.lower()
    _, m2 = tjr_alerts.first_target_message("currencies", "GBP/JPY",
                                            218.470, 217.900)
    assert "HALF" in m2 and "218.470" in m2
    _, m3 = tjr_alerts.close_message("currencies", "GBP/JPY", 218.10,
                                     "The reason is gone.")
    assert "close it now" in m3.lower()
    _, m4 = tjr_alerts.stopped_message("currencies", "GBP/JPY", 218.760)
    assert "218.760" in m4


# ============================================ 6. COSTS AND ORDER PATHS
def test_nothing_in_this_file_declines_or_ranks_a_trade_on_cost():
    for mod in (tjr_forex, tjr_alerts):
        src = inspect.getsource(mod)
        bad = []
        for i, line in enumerate(src.splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or s.startswith('"') or s.startswith("'"):
                continue
            low = s.lower()
            if ("cost" in low or "spread" in low) and any(
                    op in s for op in (" > ", " < ", " >= ", " <= ",
                                       "min(", "max(")):
                bad.append(f"{mod.__name__} {i}: {s}")
        assert not bad, "cost or spread reached a comparison:\n  " + "\n  ".join(bad)


def test_the_measured_spread_is_charged_and_is_this_pairs_own():
    base = tjr_bot.Config().stop_buffer_pct_of_price
    for pair in tjr_forex.PAIRS:
        c = cfg(pair)
        assert c.instrument.round_trip_cost_pct > 0, f"{pair} is traded free"
        assert abs(c.stop_buffer_pct_of_price -
                   c.instrument.round_trip_cost_pct) < 1e-12
        assert c.stop_buffer_pct_of_price != base, \
            f"{pair} is still carrying SPY's stop buffer"


def test_nothing_in_these_files_can_place_an_order():
    for mod in (tjr_forex, tjr_alerts):
        src = inspect.getsource(mod)
        for bad in ("market_order", "submit_order", "close_position",
                    "/v2/orders", "crypto_market_order"):
            assert bad not in src, f"an order path appeared in {mod.__name__}: {bad}"


# ==================================================== 7. THE FEED LAYER
def test_the_archive_reader_decodes_a_bank_record_correctly():
    """No network. A record is built in the bank's own format and handed to
    the reader through a stand-in for the http library, so the arithmetic
    that turns integers into prices is checked rather than assumed."""
    recs = [(0,      133960, 133957, 133950, 133965, 132.79),
            (60,     133958, 133970, 133955, 133975, 140.0),
            (120,    133970, 133970, 133970, 133970, 0.0)]   # nothing traded
    raw = b"".join(struct.pack(">5if", *r) for r in recs)
    # the archive ships one plain lzma stream, which is what the reader opens
    c = lzma.LZMACompressor(format=lzma.FORMAT_ALONE)
    blob = c.compress(raw) + c.flush()

    class _Resp:
        status_code = 200
        content = blob

    fake = types.ModuleType("requests")
    fake.get = lambda *a, **k: _Resp()
    real = sys.modules.get("requests")
    sys.modules["requests"] = fake
    try:
        d = tjr_forex.DukascopyArchive().day("GBP/USD", dt.date(2026, 5, 15))
    finally:
        if real is not None:
            sys.modules["requests"] = real
        else:
            del sys.modules["requests"]

    assert d is not None and len(d) == 2, \
        "the minute in which nothing traded was kept, or a real one was dropped"
    assert abs(float(d["open"].iloc[0]) - 1.33960) < 1e-9
    assert abs(float(d["high"].iloc[0]) - 1.33965) < 1e-9
    assert abs(float(d["low"].iloc[0]) - 1.33950) < 1e-9
    assert abs(float(d["close"].iloc[0]) - 1.33957) < 1e-9
    assert (d["high"] >= d["low"]).all(), "a high came out below its own low"


def test_the_month_in_the_archive_path_is_zero_based():
    """The single easiest thing to get wrong in that URL. May is 04."""
    u = tjr_forex.DukascopyArchive().url("GBP/USD", dt.date(2026, 5, 15))
    assert "/2026/04/15/" in u, u
    assert u.endswith("BID_candles_min_1.bi5")


def test_the_archive_is_never_offered_as_the_live_feed():
    """It publishes the day after the day. A feed that cannot see today can
    never raise an alert, and the code has to know that."""
    f = tjr_forex.live_feed()
    assert not isinstance(f, tjr_forex.DukascopyArchive)
    assert f.name in ("yahoo", "twelvedata")
    rep = tjr_forex.feed_report()
    assert rep["dukascopy"]["enough_to_run_continuously"] is False
    assert rep["yahoo"]["enough_to_run_continuously"] is True


def test_the_paid_upgrade_is_a_key_in_env_and_nothing_else():
    """Twelve Data has to be one line of setup Wallace does himself, and the
    bot must never pretend it is switched on when it is not."""
    td = tjr_forex.TwelveDataLive()
    assert td.needs_key is True
    if not td.key():
        assert td.available() is False
        assert tjr_forex.live_feed().name == "yahoo"


def test_this_file_decides_and_does_not_send():
    """One watcher, in tjr_desk.py, with one message format for every market.
    A second currency-only watcher used to live here; two of them means two
    places for the message to drift, and the message is the product."""
    assert not hasattr(tjr_forex, "ForexWatcher")
    assert not hasattr(tjr_forex, "watch_all")
    src = inspect.getsource(tjr_forex)
    assert "tjr_alerts.send" not in src, "this file sends behind the desk's back"
    import tjr_desk
    assert "tjr_alerts.send" in inspect.getsource(tjr_desk), \
        "the desk cannot reach his phone"


# ==================================================== 8. HOUSEKEEPING
def test_one_setup_a_day_at_most_per_pair():
    for pair in tjr_forex.PAIRS:
        days = [t.day for t in replay(pair)["trades"]]
        assert len(days) == len(set(days)), f"{pair}: two entries on one day"


def test_levels_are_only_marked_from_the_1_hour_and_the_4_hour():
    assert cfg().instrument.level_minutes == (60, 240)


def test_the_two_pairs_are_judged_separately():
    """GBP/USD and GBP/JPY share the pound and nothing else, so neither vetoes
    the other and neither can silence the other's day."""
    assert cfg("GBP/USD").enforce_index_agreement is False
    assert cfg("GBP/JPY").enforce_index_agreement is False
    src = inspect.getsource(tjr_forex.run_pair)
    assert "{pair: win}" in src, "both pairs were handed to one run_day call"


TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]


def main():
    print("=" * 78)
    print("test_tjr_forex.py — the alert is the product, so the alert is tested")
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
