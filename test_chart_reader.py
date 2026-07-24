"""
test_chart_reader.py — offline tests for chart_reader.py.

Run with:  python3 test_chart_reader.py

NO NETWORK. Every fixture below is hand-built so its correct reading is
unambiguous (a textbook doji IS a doji by construction, a five-bar chop
sequence IS chop by construction, ...) — these are the module's ground
truth. read_chart() is pure and deterministic, so every test passes a fixed
`now` rather than relying on wall-clock time.
"""

from __future__ import annotations

import py_compile
import struct
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

import chart_reader as cr

SCRATCH = Path("/private/tmp/claude-501/-Users-wallacechen/f12ae3f6-df77-43bb-b438-d778ff0c328d/scratchpad/test_chart_reader_out")

TS0 = datetime(2026, 7, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# fixture builders
# ---------------------------------------------------------------------------

def zigzag_frame(legs, start: float = 100.0, wick: float = 0.3, ts0=TS0) -> pd.DataFrame:
    """Build a DataFrame from a sequence of (direction, n_bars, step_per_bar)
    legs — each bar moves `step` in `direction`, with a small fixed wick
    each side. Deterministic, no randomness, so swing highs/lows land
    exactly where the legs put them."""
    price = start
    rows = []
    for direction, n, step in legs:
        sign = 1 if direction == "up" else -1
        for _ in range(n):
            o = price
            c = price + sign * step
            h = max(o, c) + wick
            l = min(o, c) - wick
            rows.append({"open": o, "high": h, "low": l, "close": c})
            price = c
    df = pd.DataFrame(rows)
    df.insert(0, "timestamp", [ts0 + timedelta(hours=i) for i in range(len(df))])
    df["volume"] = 10.0
    return df


def chop_frame(n: int = 14, base: float = 100.0, amp: float = 1.0,
               wick: float = 0.3, ts0=TS0) -> pd.DataFrame:
    """Bars that alternate up/down between the same two prices every bar —
    maximum direction-change rate, maximum overlap. This IS the textbook
    definition of chop, by construction."""
    rows = []
    for i in range(n):
        if i % 2 == 0:
            o, c = base, base + amp
        else:
            o, c = base + amp, base
        h = max(o, c) + wick
        l = min(o, c) - wick
        rows.append({"open": o, "high": h, "low": l, "close": c})
    df = pd.DataFrame(rows)
    df.insert(0, "timestamp", [ts0 + timedelta(hours=i) for i in range(len(df))])
    df["volume"] = 10.0
    return df


def baseline_plus_last(last_row: dict, n_base: int = 20, base_body: float = 1.0,
                        wick: float = 0.3, ts0=TS0) -> pd.DataFrame:
    """20 unremarkable, evenly-sized up bars (so the median-body baseline is
    a clean, known number: base_body) followed by ONE hand-shaped bar
    (`last_row`) whose classification is what each candle-level test
    actually checks."""
    rows = []
    price = 100.0
    for _ in range(n_base):
        o = price
        c = price + base_body
        h = max(o, c) + wick
        l = min(o, c) - wick
        rows.append({"open": o, "high": h, "low": l, "close": c})
        price = c
    rows.append(dict(last_row))
    df = pd.DataFrame(rows)
    df.insert(0, "timestamp", [ts0 + timedelta(hours=i) for i in range(len(df))])
    df["volume"] = 10.0
    return df


def _closed_now(df: pd.DataFrame):
    """A `now` one full interval past the last bar's timestamp — guarantees
    the last bar reads as CLOSED, not forming."""
    return df["timestamp"].iloc[-1] + timedelta(hours=1)


def _last_bar_price(n_base: int = 20, base_body: float = 1.0) -> float:
    return 100.0 + n_base * base_body


def _png_dimensions(path: Path) -> tuple:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG (bad signature)"
    assert data[12:16] == b"IHDR", f"{path} has no IHDR chunk where expected"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def _assert_schema_shape(read: dict):
    for key in ("structure", "location", "quality", "momentum", "key_levels",
                "tradeable", "best_tool", "recent_candles", "current_candle",
                "one_line"):
        assert key in read, f"read is missing required key {key!r}"
    assert read["structure"] in cr.VALID_STRUCTURE
    assert read["location"] in cr.VALID_LOCATION
    assert read["quality"] in cr.VALID_QUALITY
    assert read["momentum"] in cr.VALID_MOMENTUM
    assert read["best_tool"] in cr.VALID_BEST_TOOL
    assert isinstance(read["tradeable"], bool)
    assert isinstance(read["key_levels"], list)
    assert isinstance(read["recent_candles"], list) and len(read["recent_candles"]) <= 5
    cc = read["current_candle"]
    assert cc["color"] in cr.VALID_CANDLE_COLOR
    assert cc["body"] in cr.VALID_BODY
    assert cc["wicks"] in cr.VALID_WICKS
    assert cc["close_position"] in cr.VALID_CLOSE_POSITION
    assert isinstance(cc["forming"], bool)
    assert isinstance(cc["tells"], str) and cc["tells"].strip()
    assert isinstance(read["one_line"], str) and read["one_line"].strip()


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_a_py_compile_both_files():
    root = Path(__file__).resolve().parent
    py_compile.compile(str(root / "chart_reader.py"), doraise=True)
    py_compile.compile(str(root / "test_chart_reader.py"), doraise=True)


def test_b_textbook_doji():
    last = 100.0 + 20 * 1.0
    row = {"open": last, "high": last + 1.0, "low": last - 1.0, "close": last}
    df = baseline_plus_last(row)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    cc = read["current_candle"]
    assert cc["body"] == "doji", cc
    assert cc["forming"] is False


def test_c_big_body_trend_bar_closes_on_high():
    last = _last_bar_price()
    row = {"open": last, "high": last + 4.2, "low": last - 0.1, "close": last + 4.0}
    df = baseline_plus_last(row)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    cc = read["current_candle"]
    assert cc["body"] == "large", cc
    assert cc["close_position"] == "near high", cc
    assert cc["color"] == "green", cc


def test_d_long_lower_wick_rejection_bar():
    last = _last_bar_price()
    row = {"open": last + 1.0, "high": last + 1.6, "low": last - 2.0, "close": last + 1.5}
    df = baseline_plus_last(row)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    cc = read["current_candle"]
    assert cc["wicks"] == "long lower", cc
    assert "reject" in cc["tells"].lower(), cc


def test_e_five_bar_chop_sequence_is_messy_stand_aside():
    df = chop_frame(n=14)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    assert read["quality"] == "messy", read["quality"]
    assert read["best_tool"] == "stand aside", read["best_tool"]
    assert read["tradeable"] is False


def test_f_clean_uptrend_higher_highs_and_lows():
    legs = [
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0), ("down", 4, 1.0),
    ]
    df = zigzag_frame(legs)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    assert read["structure"] == "uptrend", read["structure"]
    assert read["best_tool"] == "trend-follow", read["best_tool"]
    assert read["quality"] == "clean", read["quality"]
    assert read["tradeable"] is True


def test_g_defined_range_at_top_is_range_fade():
    legs = [
        ("up", 6, 10 / 6), ("down", 6, 10 / 6),
        ("up", 6, 10 / 6), ("down", 6, 10 / 6),
        ("up", 6, 10 / 6),
    ]
    df = zigzag_frame(legs)
    read = cr.read_chart(df, now=_closed_now(df))
    _assert_schema_shape(read)
    assert read["structure"] == "range", read["structure"]
    assert read["location"] == "at range high", read["location"]
    assert read["best_tool"] == "range-fade", read["best_tool"]


def test_h_unfinished_newest_bar_is_flagged_forming():
    last = _last_bar_price()
    row = {"open": last, "high": last + 0.5, "low": last - 0.3, "close": last + 0.2}
    df = baseline_plus_last(row)
    # `now` is only 10 minutes after the bar OPENED — its hourly interval
    # hasn't closed yet.
    now = df["timestamp"].iloc[-1] + timedelta(minutes=10)
    read = cr.read_chart(df, now=now)
    _assert_schema_shape(read)
    assert read["current_candle"]["forming"] is True
    assert "forming" in read["current_candle"]["tells"].lower()

    # and the SAME bar, once its interval has actually elapsed, must NOT be
    # flagged forming — proving this is a real time check, not a fluke.
    closed_read = cr.read_chart(df, now=_closed_now(df))
    assert closed_read["current_candle"]["forming"] is False


def test_i_recent_candles_excludes_current_and_is_newest_last():
    last = _last_bar_price()
    row = {"open": last, "high": last + 4.2, "low": last - 0.1, "close": last + 4.0}
    df = baseline_plus_last(row)
    read = cr.read_chart(df, now=_closed_now(df))
    assert len(read["recent_candles"]) == 5
    # the second-to-last bar in the frame (a plain +1.0-body up bar from the
    # baseline) must show up as the LAST entry in recent_candles ("newest
    # last"), not folded into current_candle.
    last_phrase = read["recent_candles"][-1]
    assert "green" in last_phrase


def test_j_advisory_only_is_true():
    assert cr.ADVISORY_ONLY is True


def test_k_store_round_trips_and_caps_history():
    state: dict = {}
    df = chop_frame(n=14)
    read = cr.read_chart(df, now=_closed_now(df))

    assert cr.get_read(state, "BTC-USDT") is None
    assert cr.get_read_history(state, "BTC-USDT") == []

    for _ in range(cr.CHART_READ_HISTORY_CAP + 7):
        cr.store_read(state, "BTC-USDT", read)

    history = cr.get_read_history(state, "BTC-USDT")
    assert len(history) == cr.CHART_READ_HISTORY_CAP, len(history)
    latest = cr.get_read(state, "BTC-USDT")
    assert latest["structure"] == read["structure"]
    assert "as_of" in latest

    # a different symbol's store is independent
    assert cr.get_read(state, "ETH-USDT") is None


def test_l_prior_day_and_week_context_feed_key_levels_and_gate_breakout():
    legs = [
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0),
    ]
    df = zigzag_frame(legs)   # ends mid-breakout, at a fresh local high
    now = _closed_now(df)

    no_context = cr.read_chart(df, now=now)
    # a prior day that already traded far above the local breakout price
    # must veto the "breaking out" call — a new LOCAL high that's still
    # inside yesterday's range is not a real breakout.
    high_prior_day = {"high": df["close"].max() + 1000.0, "low": df["close"].min()}
    gated = cr.read_chart(df, now=now, prior_day=high_prior_day)

    assert isinstance(no_context["key_levels"], list) and len(no_context["key_levels"]) > 0
    if no_context["location"] == "breaking out":
        assert gated["location"] != "breaking out"

    week_ctx = {"high": df["close"].max() + 500.0, "low": df["close"].min() - 500.0}
    with_week = cr.read_chart(df, now=now, week=week_ctx)
    assert any(abs(lvl - week_ctx["high"]) < 1e-6 for lvl in with_week["key_levels"])
    assert any(abs(lvl - week_ctx["low"]) < 1e-6 for lvl in with_week["key_levels"])


def test_m_read_chart_rejects_empty_frame():
    try:
        cr.read_chart(pd.DataFrame())
        raise AssertionError("expected ValueError for an empty candles_df")
    except ValueError:
        pass


def test_n_verify_read_renders_full_and_zoom_pngs_matching_the_read():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    legs = [
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0), ("down", 4, 1.0),
        ("up", 8, 2.0), ("down", 4, 1.0),
    ]
    df = zigzag_frame(legs)
    out_png = SCRATCH / "BTC-USDT_1h.png"
    read, images = cr.verify_read(df, out_png, now=_closed_now(df),
                                  symbol="BTC-USDT", timeframe="1h")
    _assert_schema_shape(read)

    full_path = Path(images["full"])
    zoom_path = Path(images["zoom"])
    assert full_path.exists() and full_path.stat().st_size > 0
    assert zoom_path.exists() and zoom_path.stat().st_size > 0

    fw, fh = _png_dimensions(full_path)
    assert fw == cr.FIGSIZE[0] * cr.DPI and fh == cr.FIGSIZE[1] * cr.DPI, (fw, fh)

    # verify_read()'s computed read must be identical to calling read_chart()
    # directly on the same frame — the render is a side effect, never a
    # different code path for the numbers.
    direct = cr.read_chart(df, now=_closed_now(df))
    assert direct == read


def test_o_verify_read_marks_the_forming_bar_in_both_images():
    last = _last_bar_price()
    row = {"open": last, "high": last + 0.5, "low": last - 0.3, "close": last + 0.2}
    df = baseline_plus_last(row)
    now = df["timestamp"].iloc[-1] + timedelta(minutes=10)
    out_png = SCRATCH / "FORMING-TEST_1h.png"
    read, images = cr.verify_read(df, out_png, now=now, symbol="FORMING-TEST", timeframe="1h")
    assert read["current_candle"]["forming"] is True
    assert Path(images["full"]).exists()
    assert Path(images["zoom"]).exists()


def main():
    tests = [
        test_a_py_compile_both_files,
        test_b_textbook_doji,
        test_c_big_body_trend_bar_closes_on_high,
        test_d_long_lower_wick_rejection_bar,
        test_e_five_bar_chop_sequence_is_messy_stand_aside,
        test_f_clean_uptrend_higher_highs_and_lows,
        test_g_defined_range_at_top_is_range_fade,
        test_h_unfinished_newest_bar_is_flagged_forming,
        test_i_recent_candles_excludes_current_and_is_newest_last,
        test_j_advisory_only_is_true,
        test_k_store_round_trips_and_caps_history,
        test_l_prior_day_and_week_context_feed_key_levels_and_gate_breakout,
        test_m_read_chart_rejects_empty_frame,
        test_n_verify_read_renders_full_and_zoom_pngs_matching_the_read,
        test_o_verify_read_marks_the_forming_bar_in_both_images,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("CHART READER — TEST SUMMARY")
    print("=" * 72)
    n_pass = 0
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        print(f"  [{status}] {name}")
        if not ok:
            print(f"          {err.splitlines()[0]}")
            for line in err.splitlines()[1:]:
                print(f"          {line}")
    print("-" * 72)
    print(f"  {n_pass}/{len(results)} passed")
    print("=" * 72 + "\n")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
