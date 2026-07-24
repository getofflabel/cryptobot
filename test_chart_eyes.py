"""
test_chart_eyes.py — offline tests for chart_eyes.py.

Run with:  python3 test_chart_eyes.py

NO NETWORK. render_candles_png() (the piece that actually draws pixels) is
pure and network-free by construction, so rendering tests build a synthetic
OHLCV DataFrame by hand and call it directly — never render_market(), which
is the only network-touching entry point in the module (and is exercised
separately, live, in the demo at the bottom of chart_eyes.py itself).

run_visual_cycle() is tested with a fake `renderer` and a fake `reader`
injected — same discipline as test_diver.py's FakePrivate/FakeFeed: nothing
here calls BloFin, yfinance, or actually draws a chart.
"""

from __future__ import annotations

import struct
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import chart_eyes as ce

SCRATCH = Path("/private/tmp/claude-501/-Users-wallacechen/f12ae3f6-df77-43bb-b438-d778ff0c328d/scratchpad/test_chart_eyes_out")


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------

def build_candle_frame(n: int = 130, seed: int = 0, start_price: float = 100.0) -> pd.DataFrame:
    """Deterministic synthetic OHLCV, oldest first, same shape get_candles()
    returns: timestamp (UTC tz-aware), open, high, low, close, volume."""
    rng = np.random.default_rng(seed)
    ts0 = datetime(2026, 7, 1, tzinfo=timezone.utc)
    price = start_price
    rows = []
    for i in range(n):
        o = price
        c = o + rng.normal(0, 1.0)
        h = max(o, c) + abs(rng.normal(0, 0.3))
        l = min(o, c) - abs(rng.normal(0, 0.3))
        v = abs(rng.normal(10, 2))
        rows.append({"timestamp": ts0 + timedelta(hours=i), "open": o, "high": h,
                     "low": l, "close": c, "volume": v})
        price = c
    return pd.DataFrame(rows)


def _png_dimensions(path: Path) -> tuple[int, int]:
    """Parse width/height straight out of the PNG IHDR chunk — no Pillow
    dependency needed just to check 'is this a real, plausibly-sized PNG'."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", f"{path} is not a PNG (bad signature)"
    assert data[12:16] == b"IHDR", f"{path} has no IHDR chunk where expected"
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def valid_tf_read(overrides: dict | None = None) -> dict:
    """A minimal, schema-valid single-timeframe read."""
    read = {
        "structure": "uptrend",
        "location": "pulling back in trend",
        "quality": "clean",
        "momentum": "expanding",
        "key_levels": [64000.0, 65500.0],
        "tradeable": True,
        "best_tool": "trend-follow",
        "one_line": "Clean uptrend, pulling back into the 20MA, buyers still in control.",
        "recent_candles": [
            "small red doji, long lower wick",
            "big green body, closed near its high",
            "small green body, upper wick",
            "red inside bar, closed mid-range",
            "green body, closed near its high",
        ],
        "current_candle": {
            "color": "green",
            "body": "average",
            "wicks": "long lower",
            "close_position": "upper half",
            "tells": "Buyers defended the dip and pushed it back toward the high.",
        },
    }
    if overrides:
        read.update(overrides)
    return read


def valid_full_read(symbol: str = "BTC-USDT", timeframes=("15m", "1h")) -> dict:
    return {
        "as_of": "2026-07-24T22:00:00Z",
        "per_timeframe": {tf: valid_tf_read() for tf in timeframes},
        "summary": f"{symbol} is in a clean uptrend across timeframes, pulling back but "
                   f"not breaking structure.",
    }


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_a_render_produces_valid_sized_png():
    """render_candles_png on synthetic data -> a real, non-empty, plausibly
    sized PNG (full ~1400x800, per the brief)."""
    SCRATCH.mkdir(parents=True, exist_ok=True)
    df = build_candle_frame(n=130)
    df = ce._attach_smas(df)
    display = df.tail(ce.DEFAULT_BARS).reset_index(drop=True)

    out = SCRATCH / "full.png"
    result_path = ce.render_candles_png(display, "TEST-USDT", "1h", out, n_closed=len(display))

    assert result_path == out
    assert out.exists() and out.stat().st_size > 1000, "PNG should be a real, non-trivial file"
    w, h = _png_dimensions(out)
    assert 1300 <= w <= 1500, f"width {w} not close to the ~1400 target"
    assert 700 <= h <= 900, f"height {h} not close to the ~800 target"


def test_b_zoom_render_and_forming_candle_marking():
    """The zoom companion image renders at the same target resolution from
    fewer bars, and a synthesized forming bar does not crash the renderer
    (it is the thing the dashed-outline/'forming' label logic runs on)."""
    df = build_candle_frame(n=40)
    df, n_closed = ce._append_forming_candle(df, "1h", last_price=float(df["close"].iloc[-1]) + 5)
    assert n_closed == 40 and len(df) == 41, "forming candle should append exactly one row"

    df = ce._attach_smas(df)
    zoom = df.tail(ce.ZOOM_BARS).reset_index(drop=True)
    zoom_n_closed = max(0, n_closed - (len(df) - len(zoom)))

    out = SCRATCH / "zoom.png"
    ce.render_candles_png(zoom, "TEST-USDT", "1h", out, n_closed=zoom_n_closed, zoom=True)

    assert out.exists() and out.stat().st_size > 1000
    w, h = _png_dimensions(out)
    assert 1300 <= w <= 1500 and 700 <= h <= 900
    # the forming row really is the last row and really is marked as unclosed
    assert zoom_n_closed == len(zoom) - 1


def test_c_render_rejects_empty_frame():
    empty = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    try:
        ce.render_candles_png(empty, "TEST-USDT", "1h", SCRATCH / "should_not_exist.png")
        raise AssertionError("expected ValueError on an empty candle frame")
    except ValueError:
        pass


def test_d_store_round_trips_and_caps_history():
    state: dict = {}
    read1 = valid_full_read()
    stored1 = ce.store_visual_read(state, "BTC-USDT", read1)
    assert stored1["summary"] == read1["summary"]
    assert ce.get_visual_read(state, "BTC-USDT") == stored1
    assert ce.get_visual_read_history(state, "BTC-USDT") == [stored1]

    # unknown symbol -> None, not a crash
    assert ce.get_visual_read(state, "NOPE-USDT") is None
    assert ce.get_visual_read_history(state, "NOPE-USDT") == []

    # push past the cap and confirm oldest is dropped, newest kept, length capped
    for i in range(ce.VISUAL_READ_HISTORY_CAP + 10):
        read = valid_full_read()
        read["as_of"] = f"2026-07-{(i % 27) + 1:02d}T00:00:00Z"
        read["summary"] = f"entry #{i}"
        ce.store_visual_read(state, "BTC-USDT", read)

    history = ce.get_visual_read_history(state, "BTC-USDT")
    assert len(history) == ce.VISUAL_READ_HISTORY_CAP, "history must be capped"
    assert history[-1]["summary"] == f"entry #{ce.VISUAL_READ_HISTORY_CAP + 9}"
    assert ce.get_visual_read(state, "BTC-USDT") == history[-1]


def test_e_run_visual_cycle_calls_reader_once_per_symbol_and_persists_exactly():
    state: dict = {}
    render_calls = []
    reader_calls = []

    def fake_renderer(symbol, timeframes, bars, out_dir):
        render_calls.append(symbol)
        return {tf: {"full": f"/fake/{symbol}_{tf}.png", "zoom": f"/fake/{symbol}_{tf}_zoom.png"}
                for tf in timeframes}

    def fake_reader(symbol, tf_files):
        reader_calls.append((symbol, tuple(sorted(tf_files))))
        return valid_full_read(symbol=symbol, timeframes=tuple(tf_files))

    symbols = ["BTC-USDT", "XAUT-USDT"]
    results = ce.run_visual_cycle(symbols, state, reader=fake_reader, renderer=fake_renderer,
                                   timeframes=("15m", "1h"))

    assert render_calls == symbols, "renderer must be called once per symbol"
    assert [s for s, _ in reader_calls] == symbols, "reader must be called exactly once per symbol"

    for symbol in symbols:
        stored = ce.get_visual_read(state, symbol)
        assert stored is not None
        # what got persisted must equal exactly what the reader returned
        # (store_visual_read only ever fills in 'as_of' if the caller omitted it,
        # and our fake reader always supplies one, so this must be an exact match)
        again = valid_full_read(symbol=symbol, timeframes=("15m", "1h"))
        assert stored == again
        assert results[symbol]["read"] == stored
        assert results[symbol]["tf_files"] == {
            tf: {"full": f"/fake/{symbol}_{tf}.png", "zoom": f"/fake/{symbol}_{tf}_zoom.png"}
            for tf in ("15m", "1h")
        }


def test_f_run_visual_cycle_requires_a_reader():
    try:
        ce.run_visual_cycle(["BTC-USDT"], {}, reader=None, renderer=lambda **kw: {})
        raise AssertionError("expected ValueError when reader is missing")
    except ValueError:
        pass


def test_g_schema_rejects_out_of_vocabulary_values():
    bad = valid_tf_read({"structure": "sideways-ish"})   # not in VALID_STRUCTURE
    try:
        ce.validate_timeframe_read(bad, tf="1h")
        raise AssertionError("expected ValueError for out-of-vocabulary 'structure'")
    except ValueError as e:
        assert "structure" in str(e)

    bad2 = valid_tf_read()
    bad2["current_candle"] = dict(bad2["current_candle"])
    bad2["current_candle"]["wicks"] = "spiky"   # not in VALID_WICKS
    try:
        ce.validate_timeframe_read(bad2, tf="1h")
        raise AssertionError("expected ValueError for out-of-vocabulary 'current_candle.wicks'")
    except ValueError as e:
        assert "wicks" in str(e)

    # a fully valid read must NOT raise
    ce.validate_timeframe_read(valid_tf_read(), tf="1h")

    # missing required field
    missing = valid_tf_read()
    del missing["recent_candles"]
    try:
        ce.validate_timeframe_read(missing, tf="1h")
        raise AssertionError("expected ValueError for missing 'recent_candles'")
    except ValueError as e:
        assert "recent_candles" in str(e)


def test_h_store_rejects_invalid_read():
    state: dict = {}
    bad_full = valid_full_read()
    bad_full["per_timeframe"]["1h"]["momentum"] = "vibing"   # not in VALID_MOMENTUM
    try:
        ce.store_visual_read(state, "BTC-USDT", bad_full)
        raise AssertionError("expected ValueError, and nothing should have been stored")
    except ValueError:
        pass
    assert ce.get_visual_read(state, "BTC-USDT") is None, "a rejected read must not be persisted"


def test_i_advisory_only_is_true():
    assert ce.ADVISORY_ONLY is True


def test_j_prompt_contains_schema_and_files():
    tf_files = {"1h": {"full": "/x/BTC-USDT_1h.png", "zoom": "/x/BTC-USDT_1h_zoom.png"}}
    prompt = ce.visual_read_prompt("BTC-USDT", tf_files)
    assert "BTC-USDT" in prompt
    assert "/x/BTC-USDT_1h.png" in prompt
    assert "/x/BTC-USDT_1h_zoom.png" in prompt
    assert "recent_candles" in prompt and "current_candle" in prompt
    assert "forming" in prompt.lower()
    assert "ADVISORY ONLY" in prompt
    for word in sorted(ce.VALID_STRUCTURE):
        assert word in prompt


def main():
    tests = [
        test_a_render_produces_valid_sized_png,
        test_b_zoom_render_and_forming_candle_marking,
        test_c_render_rejects_empty_frame,
        test_d_store_round_trips_and_caps_history,
        test_e_run_visual_cycle_calls_reader_once_per_symbol_and_persists_exactly,
        test_f_run_visual_cycle_requires_a_reader,
        test_g_schema_rejects_out_of_vocabulary_values,
        test_h_store_rejects_invalid_read,
        test_i_advisory_only_is_true,
        test_j_prompt_contains_schema_and_files,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("CHART EYES — TEST SUMMARY")
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
