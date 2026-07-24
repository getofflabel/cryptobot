"""
test_morning_read.py — offline tests for morning_read.py (the once-daily
market-context store + its Telegram-note byproduct). NO NETWORK: a fake
live_feed stands in for BloFin, and equities_fetch/oil_fetch/news_fetch are
always injected as plain functions returning synthetic data — yfinance and
Supabase/Telegram are never touched. step5_paper_trade.notify/save_state
are monkeypatched to no-ops (recording calls) exactly like test_gold_book.py
does for gold_book.

Seven intents:
  a) weekly-range math (position_pct/zone_label/compute_weekly_stats) —
     hand-verified against a fixed synthetic 6-bar series
  b) tape-character classifier — all 4 branches on hand-built 4h bars
  c) once-per-day idempotency — due call sends once, a second call the
     same day no-ops, a call before the due hour no-ops
  d) dry mode — always renders (even before the due hour), never notifies,
     never mutates state
  e) context store API — store_market_context / get_context /
     get_context_history, including the 30-entry history cap
  f) macro context math (SPY zone/prior-low-break, Brent-WTI spread
     percentile/stress flag) — hand-verified
  g) full sample render against synthetic data resembling the owner's
     model text — printed verbatim so it can be read in the test output

Run with:  python3 test_morning_read.py
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd

import morning_read as mr
import step5_paper_trade as s5


def _noop(*a, **kw):
    pass


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def _daily_bars(ohlc_rows, start=None):
    """ohlc_rows: list of (open, high, low, close) tuples, oldest first."""
    start = start or datetime(2026, 7, 1, tzinfo=timezone.utc)
    rows = []
    for i, (o, h, l, c) in enumerate(ohlc_rows):
        rows.append({"timestamp": start + timedelta(days=i), "open": o,
                     "high": h, "low": l, "close": c, "volume": 1000.0})
    return pd.DataFrame(rows)


def _4h_bars(ohlc_rows, start=None):
    start = start or datetime(2026, 7, 20, tzinfo=timezone.utc)
    rows = []
    for i, (o, h, l, c) in enumerate(ohlc_rows):
        rows.append({"timestamp": start + timedelta(hours=4 * i), "open": o,
                     "high": h, "low": l, "close": c, "volume": 100.0})
    return pd.DataFrame(rows)


def _flat_1h_bars(n, base=100.0, noisy_last=False):
    """n hourly bars, tight range throughout (a 'calm' regime): current
    ATR% sits below its own trailing median. If noisy_last, the most
    recent ~24 bars widen out (a 'violent' regime instead)."""
    start = datetime(2026, 6, 1, tzinfo=timezone.utc)
    rows = []
    px = base
    for i in range(n):
        wide = noisy_last and i >= n - 24
        step = 0.006 * base if wide else 0.0006 * base
        o = px
        c = px + (step if i % 2 == 0 else -step)
        h = max(o, c) + step * 0.5
        l = min(o, c) - step * 0.5
        rows.append({"timestamp": start + timedelta(hours=i), "open": o,
                     "high": h, "low": l, "close": c, "volume": 10.0})
        px = c
    return pd.DataFrame(rows)


class FakeLiveFeed:
    """Per-symbol {timeframe: DataFrame} + {symbol: last price}."""

    def __init__(self, candles: dict, last_price: dict):
        self.candles = candles
        self.last_price = last_price

    def get_candles(self, symbol, timeframe, limit):
        df = self.candles[symbol][timeframe]
        return df.iloc[-limit:].reset_index(drop=True)

    def get_ticker(self, symbol):
        return SimpleNamespace(last=self.last_price[symbol])


def _rig(btc_close=65000.0, eth_close=1900.0, gold_close=4150.0,
        btc_regime_noisy=False):
    """A complete 3-symbol fake feed with plenty of history for both the
    daily-ATR and the 1h-ATR/median regime math, plus mild, deterministic
    5-day drift so ret_5d/tape are non-trivial."""
    def _sym(base, drift_per_day, noisy):
        daily = _daily_bars([
            (base * (1 + drift_per_day * k), base * (1 + drift_per_day * k) * 1.01,
             base * (1 + drift_per_day * k) * 0.99, base * (1 + drift_per_day * (k + 1)))
            for k in range(30)
        ])
        h4 = _4h_bars([
            (base, base * 1.002, base * 0.998, base * (1 - 0.001 * (i % 6)))
            for i in range(20)
        ])
        h1 = _flat_1h_bars(400, base=base, noisy_last=noisy)
        # the live tick sits AT the last daily close (mirrors reality: the
        # book's own drift is what the "current price" reflects) — using a
        # stale, undriften base here previously put the fake price outside
        # its own weekly range
        last_close = base * (1 + drift_per_day * 30)
        return {"1d": daily, "4h": h4, "1h": h1}, last_close

    btc_data, btc_last = _sym(btc_close, -0.0015, btc_regime_noisy)
    eth_data, eth_last = _sym(eth_close, -0.0025, False)
    gold_data, gold_last = _sym(gold_close, 0.0005, False)
    candles = {mr.BTC_SYMBOL: btc_data, mr.ETH_SYMBOL: eth_data,
              mr.GOLD_SYMBOL: gold_data}
    last_price = {mr.BTC_SYMBOL: btc_last, mr.ETH_SYMBOL: eth_last,
                 mr.GOLD_SYMBOL: gold_last}
    return FakeLiveFeed(candles, last_price)


def _install_noops():
    s5.notify = _noop
    s5.save_state = _noop
    s5.CLOUD_STATE = False


# ---------------------------------------------------------------------------
# a) weekly-range math
# ---------------------------------------------------------------------------


def test_a_weekly_range_math():
    bars = _daily_bars([
        (95, 100, 90, 95),
        (95, 102, 94, 100),
        (100, 105, 98, 103),
        (103, 104, 99, 101),
        (101, 108, 100, 106),
        (106, 110, 104, 109),
    ])

    # upper edge (85% into the range)
    stats = mr.compute_weekly_stats(bars, current_price=107.0)
    assert stats["weekly_hi"] == 110.0, stats
    assert stats["weekly_lo"] == 90.0, stats
    assert stats["weekly_mid"] == 100.0, stats
    assert abs(stats["width_pct"] - 20.0) < 1e-9, stats
    expected_pos = (107.0 - 90.0) / (110.0 - 90.0) * 100
    assert abs(stats["pos_pct"] - round(expected_pos, 1)) < 1e-6, stats
    assert stats["zone"] == mr.ZONE_UPPER, stats
    assert stats["prior_day_high"] == 110.0, stats
    assert stats["prior_day_low"] == 104.0, stats
    expected_ret5d = (109.0 / 95.0 - 1) * 100
    assert abs(stats["ret_5d"] - round(expected_ret5d, 2)) < 1e-6, stats
    assert stats["last_price"] == 107.0, stats

    # midrange (50%)
    mid = mr.compute_weekly_stats(bars, current_price=100.0)
    assert mid["zone"] == mr.ZONE_MID, mid

    # lower edge (20%)
    lower = mr.compute_weekly_stats(bars, current_price=94.0)
    assert lower["zone"] == mr.ZONE_LOWER, lower

    # position_pct clamps outside [0,100]
    assert mr.position_pct(200, 90, 110) == 100.0
    assert mr.position_pct(-50, 90, 110) == 0.0

    print(f"  [i] OK — hi=110 lo=90 mid=100 width=20% pos={stats['pos_pct']}%"
          f" (upper_edge), ret_5d={stats['ret_5d']:+.2f}%")


# ---------------------------------------------------------------------------
# b) tape classifier
# ---------------------------------------------------------------------------


def test_b_tape_classifier():
    # 5 of 6 red -> bled steadily
    bled = _4h_bars([
        (100, 101, 96, 97), (97, 98, 93, 94), (94, 95, 90, 91),
        (91, 92, 87, 88), (88, 89, 84, 85), (85, 90, 84, 89),  # 1 green
    ])
    assert mr.classify_tape(bled, atr_1d=5.0) == "bled steadily"

    # 5 of 6 green -> pushed higher
    pushed = _4h_bars([
        (100, 105, 99, 104), (104, 109, 103, 108), (108, 113, 107, 112),
        (112, 117, 111, 116), (116, 121, 115, 120), (120, 119, 114, 115),  # 1 red
    ])
    assert mr.classify_tape(pushed, atr_1d=5.0) == "pushed higher"

    # 3/3 split, tight 24h range < atr -> chopped sideways
    tight = _4h_bars([
        (100, 100.5, 99.7, 100.2), (100.2, 100.6, 99.9, 100.0),
        (100.0, 100.4, 99.8, 100.3), (100.3, 100.5, 99.9, 100.1),
        (100.1, 100.4, 99.8, 100.0), (100.0, 100.3, 99.7, 100.2),
    ])
    range24 = float(tight["high"].max() - tight["low"].min())
    assert range24 < 5.0
    assert mr.classify_tape(tight, atr_1d=5.0) == "chopped sideways"

    # 3/3 split, wide 24h range >= atr -> chopped, no clear direction
    wide = _4h_bars([
        (100, 108, 99, 103), (103, 104, 95, 100), (100, 106, 98, 104),
        (104, 105, 97, 101), (101, 109, 99, 106), (106, 107, 96, 102),
    ])
    range24w = float(wide["high"].max() - wide["low"].min())
    assert range24w >= 5.0
    assert mr.classify_tape(wide, atr_1d=5.0) == "chopped, no clear direction"

    # not enough data
    assert mr.classify_tape(bled.iloc[:3], atr_1d=5.0) == "not enough data"
    assert mr.classify_tape(None, atr_1d=5.0) == "not enough data"

    print("  [i] OK — bled steadily / pushed higher / chopped sideways / "
          "chopped-no-direction all fire on the intended data")


# ---------------------------------------------------------------------------
# c) once-per-day idempotency (+ before-due-hour no-op)
# ---------------------------------------------------------------------------


def test_c_once_per_day_idempotency():
    _install_noops()
    calls = []
    s5.notify = lambda title, msg: calls.append((title, msg))

    live = _rig()
    state = {}

    before_due = datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc)
    r0 = mr.run_morning_read(live, state, dry=False, now=before_due,
                             equities_fetch=lambda: None,
                             oil_fetch=lambda: None,
                             news_fetch=lambda: None)
    assert r0 is None, "must no-op before DUE_HOUR_UTC"
    assert not calls, "must not notify before the due hour"
    assert "morning_read_date" not in state

    due = datetime(2026, 7, 24, 13, 0, tzinfo=timezone.utc)
    r1 = mr.run_morning_read(live, state, dry=False, now=due,
                             equities_fetch=lambda: None,
                             oil_fetch=lambda: None,
                             news_fetch=lambda: None)
    assert isinstance(r1, str) and r1, "first due call must return the note text"
    assert len(calls) == 1, calls
    assert state.get("morning_read_date") == "2026-07-24"
    assert mr.get_context(state, mr.BTC_SYMBOL) is not None

    later_same_day = datetime(2026, 7, 24, 20, 0, tzinfo=timezone.utc)
    r2 = mr.run_morning_read(live, state, dry=False, now=later_same_day,
                             equities_fetch=lambda: None,
                             oil_fetch=lambda: None,
                             news_fetch=lambda: None)
    assert r2 is None, "second call the same UTC day must no-op"
    assert len(calls) == 1, "must not notify a second time the same day"

    next_day = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
    r3 = mr.run_morning_read(live, state, dry=False, now=next_day,
                             equities_fetch=lambda: None,
                             oil_fetch=lambda: None,
                             news_fetch=lambda: None)
    assert isinstance(r3, str) and r3
    assert len(calls) == 2
    assert state["morning_read_date"] == "2026-07-25"

    print(f"  [i] OK — 1 notify at 13:00, 0 more at 20:00 same day, 1 more "
          f"the next day at 12:00 (3 calls, 2 sends)")


# ---------------------------------------------------------------------------
# d) dry mode
# ---------------------------------------------------------------------------


def test_d_dry_mode_no_side_effects():
    _install_noops()
    calls = []
    s5.notify = lambda title, msg: calls.append((title, msg))

    live = _rig()
    state = {}
    # deliberately BEFORE the due hour and with a date guard already set —
    # dry mode must ignore both
    state["morning_read_date"] = "2026-07-24"
    early = datetime(2026, 7, 24, 3, 0, tzinfo=timezone.utc)

    text = mr.run_morning_read(live, state, dry=True, now=early,
                               equities_fetch=lambda: None,
                               oil_fetch=lambda: None,
                               news_fetch=lambda: None)
    assert isinstance(text, str) and text, "dry mode must still render"
    assert not calls, "dry mode must never notify"
    assert "market_context" not in state, "dry mode must never persist context"
    assert state["morning_read_date"] == "2026-07-24", "dry mode must not touch state"

    print("  [i] OK — dry mode rendered text with zero notify calls and "
          "zero state mutation, even before the due hour")


# ---------------------------------------------------------------------------
# e) context store API
# ---------------------------------------------------------------------------


def test_e_context_store_api():
    state = {}
    assert mr.get_context(state, mr.BTC_SYMBOL) is None
    assert mr.get_context_history(state, mr.BTC_SYMBOL) == []

    for day in range(35):
        ctx = {"date": f"2026-06-{day + 1:02d}", "ret_5d": float(day)}
        mr.store_market_context(state, {mr.BTC_SYMBOL: ctx})

    latest = mr.get_context(state, mr.BTC_SYMBOL)
    assert latest["ret_5d"] == 34.0, latest

    hist = mr.get_context_history(state, mr.BTC_SYMBOL)
    assert len(hist) == mr.HISTORY_CAP == 30, len(hist)
    assert hist[-1]["ret_5d"] == 34.0
    assert hist[0]["ret_5d"] == 5.0, hist[0]        # oldest 5 entries dropped

    small = mr.get_context_history(state, mr.BTC_SYMBOL, n=3)
    assert [h["ret_5d"] for h in small] == [32.0, 33.0, 34.0]

    assert mr.get_context(state, "no-such-symbol") is None

    print(f"  [i] OK — 35 daily writes capped history at {mr.HISTORY_CAP}, "
          f"oldest 5 dropped, latest == history[-1]")


# ---------------------------------------------------------------------------
# f) macro context math
# ---------------------------------------------------------------------------


def test_f_macro_context_math():
    spy = pd.DataFrame([
        {"open": 550, "high": 552, "low": 548, "close": 551},
        {"open": 551, "high": 553, "low": 549, "close": 550},
        {"open": 550, "high": 554, "low": 547, "close": 553},
        {"open": 553, "high": 556, "low": 551, "close": 555},
        {"open": 555, "high": 558, "low": 552, "close": 556},
        {"open": 556, "high": 557, "low": 545, "close": 546},  # broke below
    ])
    macro = mr.compute_macro_context("2026-07-24", spy, None)
    hi, lo = 558.0, 545.0
    assert macro["spy_weekly_hi"] == hi
    assert macro["spy_weekly_lo"] == lo
    assert macro["spy_close"] == 546.0
    # prior session's low (2nd-to-last row) is 552 -> 546 < 552 -> broken
    assert macro["spy_prior_low_broken"] is True
    expected_zone = mr.zone_label(mr.position_pct(546.0, lo, hi))
    assert macro["spy_zone"] == expected_zone

    # oil: spread history with a known percentile
    spread_hist = [float(x) for x in range(1, 60)]     # 1..59, 59 points
    brent, wti = 90.0, 85.0                              # spread = 5.0
    macro2 = mr.compute_macro_context("2026-07-24", None, (brent, wti, spread_hist))
    assert macro2["brent_wti_spread"] == 5.0
    # 5 of the 59 trailing values (1..5) are <= 5.0 -> percentile ~8.5%
    expected_pctile = round(5 / 59 * 100, 1)
    assert macro2["spread_pctile"] == expected_pctile, macro2
    assert macro2["stress_flag"] is False

    high_spread_hist = [1.0] * 90                        # current spread beats ~all of history
    macro3 = mr.compute_macro_context("2026-07-24", None, (95.0, 85.0, high_spread_hist))
    assert macro3["brent_wti_spread"] == 10.0
    assert macro3["spread_pctile"] == 100.0
    assert macro3["stress_flag"] is True

    assert mr.compute_macro_context("2026-07-24", None, None) is None
    assert mr.compute_macro_context("2026-07-24", spy.iloc[:1], None) is None  # <2 rows

    print(f"  [i] OK — SPY zone={macro['spy_zone']!r} prior_low_broken=True; "
          f"spread percentile {expected_pctile}% (not stressed) vs 100% "
          f"(stress_flag True)")


# ---------------------------------------------------------------------------
# g) full sample render (printed verbatim)
# ---------------------------------------------------------------------------


def test_g_full_sample_render():
    _install_noops()
    calls = []
    s5.notify = lambda title, msg: calls.append((title, msg))

    # BTC bleeding (mostly red 4h bars, small negative drift), ETH
    # retracing further (bigger negative drift) — mirrors the owner's
    # model text register: "BTC not convincingly holding... bleeding
    # since Tuesday, while ETH... retraced further than BTC."
    live = _rig(btc_close=65200.0, eth_close=1898.0, gold_close=4150.0)

    # a Friday, so the catalyst line's weekend-risk note fires too
    friday = datetime(2026, 7, 24, 13, 0, tzinfo=timezone.utc)
    assert friday.weekday() == 4

    spy_bars = pd.DataFrame([
        {"open": 550, "high": 552, "low": 548, "close": 551},
        {"open": 551, "high": 553, "low": 549, "close": 550},
        {"open": 550, "high": 554, "low": 547, "close": 553},
        {"open": 553, "high": 556, "low": 551, "close": 555},
        {"open": 555, "high": 558, "low": 552, "close": 556},
        {"open": 556, "high": 557, "low": 549, "close": 553},
    ])
    oil_data = (82.10, 77.80, [4.3] * 40 + [4.1] * 20)

    state = {
        "tactical_eth": {"open_trade": {"direction": 1, "entry_price": 1856.0,
                                        "sl_price": 1843.0}},
    }

    text = mr.run_morning_read(
        live, state, dry=False, now=friday,
        equities_fetch=lambda: spy_bars,
        oil_fetch=lambda: oil_data,
        news_fetch=lambda: "[WatcherGuru] JUST IN: Fed holds rates steady",
    )
    assert isinstance(text, str) and text
    assert len(calls) == 1
    title, sent_body = calls[0]
    assert sent_body == text
    assert title.startswith("\U0001f305 Morning read — ")

    n_lines = len(text.splitlines())
    assert n_lines <= 14, f"note is {n_lines} lines, want <=14"
    assert "We're long ether from $1,856, stop at $1,843." in text

    btc_ctx = mr.get_context(state, mr.BTC_SYMBOL)
    macro_ctx = mr.get_context(state, "macro")
    assert btc_ctx is not None and macro_ctx is not None

    print(f"\n{'=' * 78}\nSAMPLE MORNING READ ({n_lines} lines)\n{'=' * 78}")
    print(f"{title}\n{sent_body}")
    print("=" * 78)
    print(f"\nSAMPLE market_context[{mr.BTC_SYMBOL!r}]:\n{btc_ctx}")
    print(f"\nSAMPLE market_context['macro']:\n{macro_ctx}")


TESTS = [
    ("a) weekly-range math (position/zone/width/ret_5d)",
     test_a_weekly_range_math),
    ("b) tape-character classifier — all 4 branches",
     test_b_tape_classifier),
    ("c) once-per-day idempotency + before-due-hour no-op",
     test_c_once_per_day_idempotency),
    ("d) dry mode — renders, never notifies, never persists",
     test_d_dry_mode_no_side_effects),
    ("e) context store API — get/set + 30-entry history cap",
     test_e_context_store_api),
    ("f) macro context math — SPY zone + Brent-WTI spread percentile",
     test_f_macro_context_math),
    ("g) full sample render against synthetic data (printed verbatim)",
     test_g_full_sample_render),
]


def main():
    print("=" * 78)
    print("test_morning_read.py — the daily market-context store + its "
          "Telegram-note byproduct")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {e}")
            traceback.print_exc()
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
    print("\n" + "=" * 78)
    if failed:
        print(f"{failed}/{len(TESTS)} TEST(S) FAILED")
        sys.exit(1)
    else:
        print(f"ALL {len(TESTS)} TESTS PASSED")


if __name__ == "__main__":
    main()
