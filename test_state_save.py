"""
test_state_save.py — the bookkeeping save must never lose the books.

WHY (2026-07-25): Wallace got repeated "book-keeping save FAILED (demo)"
alerts. Two separate faults, both of which let DISPLAY data destroy
POSITION data, because they share one blob:

  1. THE REAL CAUSE — a single NaN anywhere in the state. JSON cannot
     represent NaN, so requests' encoder raises before a byte leaves the
     machine. No timeout, no retry helps; all three attempts fail
     identically. It arrived via live_read's market data (a yfinance gap or
     a rolling stat with an incomplete window) and took the books with it.
  2. SIZE — the blob was 170KB, ~80% panel candles and AI judgment history,
     against ~100 bytes of actual position records.

Fixes under test here: _json_safe() sanitises NaN/Inf at the write
boundary for every writer at once, and save_state falls back to a
books-only write if the full blob still will not go.

This is the same failure that manufactured a phantom BTC short earlier in
the week: a lost save is a books-vs-reality fork, never a shrug.
"""

from __future__ import annotations

import json
import sys
import traceback

import numpy as np

import step5_paper_trade as s5


def test_a_nan_and_inf_are_sanitised():
    """A NaN anywhere must not be able to block the save."""
    bad = {
        "virtual_equity": 1343.67,
        "breakout_book": {"open_trade": {"entry": 64118.4,
                                         "atr": np.float64(np.nan)}},
        "live_read": {"paper": {"candles": [[1, 2.0, float("nan"), 4.0, 5.0]],
                                "stat": float("inf"),
                                "neg": float("-inf")}},
        "nested": [{"a": [float("nan"), 1.5]}],
        "np_good": np.float64(3.25),
    }
    # precondition: this really is unserialisable before sanitising
    try:
        json.dumps(bad, allow_nan=False)
        raise AssertionError("fixture is wrong — it should not serialise")
    except ValueError:
        pass

    clean = s5._json_safe(bad)
    json.dumps(clean, allow_nan=False)          # must not raise

    assert clean["live_read"]["paper"]["candles"][0][2] is None
    assert clean["live_read"]["paper"]["stat"] is None
    assert clean["live_read"]["paper"]["neg"] is None
    assert clean["breakout_book"]["open_trade"]["atr"] is None
    assert clean["nested"][0]["a"] == [None, 1.5]
    # real numbers must survive completely untouched
    assert clean["virtual_equity"] == 1343.67
    assert clean["breakout_book"]["open_trade"]["entry"] == 64118.4
    assert clean["np_good"] == 3.25


def test_b_books_survive_when_the_full_save_fails():
    """If the whole blob will not go, the POSITIONS must still be written."""
    state = {
        "virtual_equity": 1343.67,
        "daily_pick": {"open_trades": [{"symbol": "BTC-USDT", "contracts": 5}]},
        "breakout_book": {"open_trade": {"direction": -1, "entry": 64118.4}},
        "live_read": {"paper": {"candles": "x" * 70000}},
        "situation_room": {"calls": ["y"] * 200},
    }
    seen = {"attempts": 0, "saved": None, "alerted": False, "logged": []}

    def fake_rpc(fn, payload):
        seen["attempts"] += 1
        p = payload["payload"]
        if "live_read" in p or "situation_room" in p:
            raise RuntimeError("simulated failure on the full blob")
        seen["saved"] = p
        return {}

    orig = (s5._sb_rpc, s5.CLOUD_STATE, s5.notify, s5.log_event)
    s5._sb_rpc = fake_rpc
    s5.CLOUD_STATE = True
    s5.notify = lambda *a, **k: seen.__setitem__("alerted", True)
    s5.log_event = lambda e: seen["logged"].append(e.get("action"))
    try:
        s5.save_state(dict(state))
    finally:
        s5._sb_rpc, s5.CLOUD_STATE, s5.notify, s5.log_event = orig

    saved = seen["saved"]
    assert saved is not None, "books were never written at all"
    # the books themselves, intact
    assert saved["virtual_equity"] == 1343.67
    assert saved["breakout_book"]["open_trade"]["direction"] == -1
    assert saved["daily_pick"]["open_trades"][0]["symbol"] == "BTC-USDT"
    # derived display data dropped, by design
    assert "live_read" not in saved and "situation_room" not in saved
    # 3 full attempts + 1 books-only
    assert seen["attempts"] == 4, seen["attempts"]
    # a degraded save is logged, and must NOT fire the scary phone alert
    assert "state_save_degraded" in seen["logged"], seen["logged"]
    assert not seen["alerted"], "books were saved — the alarm must stay quiet"


def test_c_alert_still_fires_when_even_the_books_cannot_save():
    """The fallback must not silence a genuine total failure."""
    state = {"virtual_equity": 1343.67, "live_read": {"x": 1}}
    seen = {"alerted": False}

    def always_fail(fn, payload):
        raise RuntimeError("supabase is down")

    orig = (s5._sb_rpc, s5.CLOUD_STATE, s5.notify, s5.log_event, s5.STATE_FILE)
    s5._sb_rpc = always_fail
    s5.CLOUD_STATE = True
    s5.notify = lambda *a, **k: seen.__setitem__("alerted", True)
    s5.log_event = lambda e: None
    s5.STATE_FILE = "/tmp/_test_state_save_fallback.json"
    try:
        s5.save_state(dict(state))
    finally:
        (s5._sb_rpc, s5.CLOUD_STATE, s5.notify, s5.log_event,
         s5.STATE_FILE) = orig

    assert seen["alerted"], (
        "when the books genuinely cannot be saved, Wallace MUST be told")


def main():
    tests = [test_a_nan_and_inf_are_sanitised,
             test_b_books_survive_when_the_full_save_fails,
             test_c_alert_still_fires_when_even_the_books_cannot_save]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("STATE SAVE TESTS")
    print("=" * 72)
    for name, ok, tb in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if tb:
            print("          " + tb.replace("\n", "\n          "))
    n = sum(1 for _, ok, _ in results if ok)
    print("-" * 72)
    print(f"  {n}/{len(results)} passed")
    print("=" * 72)
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
