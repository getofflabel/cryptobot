"""
test_newsdesk_exit.py — offline tests for newsdesk.py's ROUND 65 EXIT SWAP:
N2 STRUCTURE TRAILING (sealed-validated in step65_news_eyes.py) replacing
the old fixed TP+2.4%/SL-1.2%/24h bracket. NO NETWORK.

Covers, per the round-65 build brief:
  (a) initial stop = entry-bar extreme +/- buffer, both directions
  (b) floor ratchets up on a new confirmed swing low, cancel/replace
      called on the exchange, and NEVER moves backward even when a later,
      less-favorable swing confirms
  (c) no TP is EVER placed, at entry, on ratchet, or on self-heal
  (d) the 24h time exit is intact, unchanged by the exit swap
  (e) a bracket-fired exit books the correct signed PnL using the
      TRAILED sl_price (a profitable trailing-stop exit, not just a loss)
  (f) dry mode makes zero order/state side effects, holding or entering

Reuses test_book_attribution.py's FakePrivate (records every order/cancel/
bracket call) and test_newsdesk_timing.py's FakeCandleFeed (a controllable
1h-candle source), plus this file's own no-op notify/log_event/save_state
neutralization — self-contained, runnable standalone.
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

import newsdesk
import step5_paper_trade as s5
from test_book_attribution import FakePrivate, make_state
from test_newsdesk_timing import FakeCandleFeed, ts

SYMBOL = "BTC-USDT"


def _noop(*a, **kw):
    pass


def _no_news(n=None):
    return []


def _reset_side_effects():
    newsdesk.notify = _noop
    newsdesk.log_event = _noop
    newsdesk.save_state = _noop
    newsdesk.time.sleep = _noop
    newsdesk._fetch_recent_news = _no_news
    s5.time.sleep = _noop


_reset_side_effects()


def approx(a, b, tol=0.02):
    return abs(a - b) < tol


def hour_ts(base: pd.Timestamp, i: int) -> pd.Timestamp:
    """base + i hours — timestamp arithmetic instead of string formatting,
    so a run of bars can cross a day boundary without a hand-rolled
    hour:02d format string overflowing past 23."""
    return base + pd.Timedelta(hours=i)


def _open_long(entry=100000.0, contracts=10.0, entry_bar_high=100600.0,
               entry_bar_low=100000.0, sl_price=None, trail_floor=None,
               tpsl_id="tpsl-1", entry_time=None,
               entry_bar_open_ts="2026-07-23 15:00:00 UTC"):
    """A round-65-shaped newsdesk open_trade record, long side."""
    sl = sl_price if sl_price is not None else round(
        newsdesk._entry_bar_extreme_stop(1, entry_bar_high, entry_bar_low), 1)
    floor_ = trail_floor if trail_floor is not None else sl
    return {
        "trigger": "news_momentum", "direction": 1, "contracts": contracts,
        "entry_price": entry, "entry_fee_bps": 6.0,
        "entry_time": entry_time or s5.now_utc(),
        "tp_price": None, "sl_price": sl, "tpsl_id": tpsl_id,
        "max_hold_h": 24, "headline": "[WatcherGuru] JUST IN: test",
        "event_ts": s5.now_utc(),
        "entry_bar_open_ts": entry_bar_open_ts,
        "entry_bar_high": entry_bar_high, "entry_bar_low": entry_bar_low,
        "trail_floor": floor_, "trail_k": newsdesk.TRAIL_K,
        "ctx": {"news": "[WatcherGuru] test"},
    }


# ---------------------------------------------------------------------------
# (a) initial stop = entry-bar extreme +/- buffer, both directions
# ---------------------------------------------------------------------------

def test_a_initial_stop_entry_bar_extreme():
    buf = newsdesk.TRAIL_BUFFER_PCT

    # -- pure function, both directions -------------------------------------
    sl_long = newsdesk._entry_bar_extreme_stop(1, bar_high=101000.0, bar_low=100000.0)
    assert approx(sl_long, 100000.0 * (1 - buf / 100)), sl_long
    sl_short = newsdesk._entry_bar_extreme_stop(-1, bar_high=101000.0, bar_low=100000.0)
    assert approx(sl_short, 101000.0 * (1 + buf / 100)), sl_short

    # -- integration: a real entry through run_newsdesk uses THIS bar's own
    #    extreme, not a fixed distance off the fill price ------------------
    state = make_state()
    private = FakePrivate(net=0.0)
    feed = FakeCandleFeed()
    state["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: test long entry",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100600.0, "low": 99800.0, "close": 100550.0},   # UP -> LONG
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "entered", result
    t = state["newsdesk"]["open_trade"]
    assert t["tp_price"] is None
    exp_sl = round(99800.0 * (1 - buf / 100), 1)   # the bar's OWN low, +buf
    assert t["sl_price"] == exp_sl, (t["sl_price"], exp_sl)
    assert private.tpsl_placed[-1]["sl"] == exp_sl
    assert private.tpsl_placed[-1]["tp"] is None

    # -- SHORT side -----------------------------------------------------
    state2 = make_state()
    private2 = FakePrivate(net=0.0)
    feed2 = FakeCandleFeed()
    state2["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: test short entry",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed2.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 103000.0,
         "high": 103100.0, "low": 102000.0, "close": 102500.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 102500.0,
         "high": 102900.0, "low": 101800.0, "close": 102000.0},  # DOWN -> SHORT
    ])
    result2 = newsdesk.run_newsdesk(private2, feed2, feed2, state2)
    assert result2["action"] == "entered", result2
    t2 = state2["newsdesk"]["open_trade"]
    assert t2["tp_price"] is None
    exp_sl2 = round(102900.0 * (1 + buf / 100), 1)   # the bar's OWN high, +buf
    assert t2["sl_price"] == exp_sl2, (t2["sl_price"], exp_sl2)
    assert private2.tpsl_placed[-1]["tp"] is None


# ---------------------------------------------------------------------------
# (b) floor ratchets up on a new confirmed swing low, cancel/replace
#     called, and NEVER moves backward even when a later, less-favorable
#     swing confirms.
# ---------------------------------------------------------------------------

def test_b_floor_ratchets_up_never_back():
    entry_bar_open_ts = "2026-07-23 15:00:00 UTC"
    t = _open_long(entry=100300.0, contracts=10.0, entry_bar_high=100600.0,
                   entry_bar_low=100000.0, entry_bar_open_ts=entry_bar_open_ts)
    initial_floor = t["sl_price"]
    assert approx(initial_floor, 100000.0 * (1 - newsdesk.TRAIL_BUFFER_PCT / 100))

    state = make_state()
    state["newsdesk"]["open_trade"] = t
    private = FakePrivate(net=10.0)   # matches recorded -> stays "holding"
    feed = FakeCandleFeed()
    # newsdesk._ensure_bracket's self-heal is orthogonal to the ratchet
    # under test (it's covered on its own in test_book_attribution.py) —
    # neutralize it here so its double-read/self-heal noise can't be
    # mistaken for ratchet activity.
    real_ensure_bracket = newsdesk._ensure_bracket
    newsdesk._ensure_bracket = _noop
    try:
        # -- one clean confirmed swing low at idx6 (price 100500, ABOVE the
        # initial floor 99700) among 12 bars (idx0=entry..idx11) ------------
        entry_ts = ts("2026-07-23 15:00:00")
        rows = [{"timestamp": entry_ts, "open": 100000.0,
                 "high": 100600.0, "low": 100000.0, "close": 100300.0}]
        for i in range(1, 12):
            low = 100500.0 if i == 6 else 101000.0
            rows.append({"timestamp": hour_ts(entry_ts, i),
                        "open": 101000.0, "high": 102000.0, "low": low,
                        "close": 101000.0})
        feed.set_candles(rows)

        result = newsdesk.run_newsdesk(private, feed, feed, state)
        assert result["action"] == "holding", result
        assert t["sl_price"] == 100500.0, t["sl_price"]
        assert t["trail_floor"] == 100500.0, t["trail_floor"]
        assert len(private.tpsl_placed) == 1, private.tpsl_placed
        assert private.tpsl_placed[0]["sl"] == 100500.0
        assert private.tpsl_placed[0]["tp"] is None
        assert len(private.cancels) == 1, private.cancels
        assert private.cancels[0] == {"kind": "tpsl", "symbol": SYMBOL,
                                      "id": "tpsl-1"}
        new_id = t["tpsl_id"]
        assert new_id != "tpsl-1", "tpsl_id must be replaced on ratchet"

        # -- SAME candles again: no new pivot confirmed -> no-op, no new
        # exchange calls, floor unchanged (idempotent) -----------------------
        result2 = newsdesk.run_newsdesk(private, feed, feed, state)
        assert result2["action"] == "holding", result2
        assert t["sl_price"] == 100500.0
        assert len(private.tpsl_placed) == 1, "must not re-place when nothing ratcheted"
        assert len(private.cancels) == 1

        # -- extend the series with a NEW confirmed swing low at a LOWER
        # price (100100 < current floor 100500) -> floor must NOT move
        # backward, and no new cancel/replace should fire -------------------
        for i in range(12, 23):
            low = 100100.0 if i == 17 else 101000.0
            rows.append({"timestamp": hour_ts(entry_ts, i),
                        "open": 101000.0, "high": 102000.0, "low": low,
                        "close": 101000.0})
        feed.set_candles(rows)

        result3 = newsdesk.run_newsdesk(private, feed, feed, state)
        assert result3["action"] == "holding", result3
        assert t["sl_price"] == 100500.0, \
            f"floor must NEVER move backward, got {t['sl_price']}"
        assert len(private.tpsl_placed) == 1, \
            "a less-favorable new pivot must never trigger cancel/replace"
        assert len(private.cancels) == 1
    finally:
        newsdesk._ensure_bracket = real_ensure_bracket


# ---------------------------------------------------------------------------
# (c) no TP is EVER placed — at entry, on ratchet, or on self-heal.
# ---------------------------------------------------------------------------

def test_c_no_tp_ever_placed():
    # entry (reuses (a)'s entered trade's own private.tpsl_placed check
    # already asserts tp is None at the call site above); here we exercise
    # entry + ratchet + self-heal together and scan EVERY place_tpsl call.
    state = make_state()
    private = FakePrivate(net=0.0)
    feed = FakeCandleFeed()
    state["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: no tp ever",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100600.0, "low": 100000.0, "close": 100550.0},
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "entered", result

    # -- now hold + ratchet (a clean favorable pivot) ------------------------
    t = state["newsdesk"]["open_trade"]
    private2 = FakePrivate(net=t["contracts"])
    feed2 = FakeCandleFeed()
    entry_ts_c = ts("2026-07-23 15:00:00")
    rows = [{"timestamp": entry_ts_c, "open": 100050.0,
             "high": 100600.0, "low": 100000.0, "close": 100550.0}]
    for i in range(1, 12):
        low = 100700.0 if i == 6 else 101200.0
        rows.append({"timestamp": hour_ts(entry_ts_c, i),
                    "open": 101200.0, "high": 102200.0, "low": low,
                    "close": 101200.0})
    feed2.set_candles(rows)
    real_ensure_bracket = newsdesk._ensure_bracket
    newsdesk._ensure_bracket = _noop
    try:
        result2 = newsdesk.run_newsdesk(private2, feed2, feed2, state)
        assert result2["action"] == "holding", result2
    finally:
        newsdesk._ensure_bracket = real_ensure_bracket

    all_calls = private.tpsl_placed + private2.tpsl_placed
    assert len(all_calls) >= 2, "expected at least entry + one ratchet call"
    for call in all_calls:
        assert call["tp"] is None, f"a TP was placed: {call}"


# ---------------------------------------------------------------------------
# (d) the 24h time exit is intact, unchanged by the exit swap.
# ---------------------------------------------------------------------------

def test_d_24h_time_exit_intact():
    entry = 100000.0
    contracts = 10.0
    old_entry_time = "2026-07-20 10:00:00 UTC"   # well over 24h ago
    t = _open_long(entry=entry, contracts=contracts, entry_time=old_entry_time)
    state = make_state()
    state["newsdesk"]["open_trade"] = t
    private = FakePrivate(net=contracts)
    feed = FakeCandleFeed()
    feed.set_candles([{"timestamp": ts("2026-07-23 15:00:00"), "open": entry,
                       "high": entry, "low": entry, "close": entry}])

    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "time_exit", result
    assert state["newsdesk"]["open_trade"] is None, "the time exit must be booked"
    assert any(c["kind"] == "tpsl" for c in private.cancels), \
        "the resting bracket must be cancelled before the time-exit market order"
    assert any(o["kind"] == "market" for o in private.orders), \
        "the time exit must be a market order"


# ---------------------------------------------------------------------------
# (e) a bracket-fired exit books the correct signed PnL using the TRAILED
#     sl_price — a profitable trailing-stop exit (floor ratcheted ABOVE
#     entry for a long), not just a loss.
# ---------------------------------------------------------------------------

def test_e_bracket_fired_exit_uses_trailed_sl():
    entry = 100000.0
    contracts = 10.0
    trailed_sl = 100500.0   # ABOVE entry — the floor already ratcheted up
    t = _open_long(entry=entry, contracts=contracts, entry_bar_high=100200.0,
                   entry_bar_low=99700.0, sl_price=trailed_sl,
                   trail_floor=trailed_sl, tpsl_id="tpsl-trailed")
    state = make_state()
    state["newsdesk"]["open_trade"] = t
    exit_price = trailed_sl   # the exchange-side SL fired exactly at the floor
    private = FakePrivate(net=0.0, fills=[{"fillPrice": str(exit_price)}])
    feed = FakeCandleFeed()

    result = newsdesk.run_newsdesk(private, feed, feed, state)

    assert state["newsdesk"]["open_trade"] is None, "the exit must be booked"
    # BLOFIN_API_REFERENCE.md verified BTC-USDT contract value, independent
    # of production code (see test_diver.py's identical note) — this trade
    # record predates contract_value(), so _book_exit's documented legacy
    # fallback (0.001) applies.
    size_btc = contracts * 0.001
    gross = 1 * (exit_price - entry) * size_btc
    # long, exit_price >= entry_price -> the reconcile branch's own
    # (unchanged) price-direction heuristic labels this "TP hit" -> 2bp
    fees = (entry * 6.0 + exit_price * 2.0) * size_btc / 10_000
    expected_pnl = round(gross - fees, 2)
    assert expected_pnl > 0, "a trailing stop that ratcheted above entry " \
                             "must book a PROFIT, not a loss"
    assert state["virtual_equity"] == round(1000.0 + expected_pnl, 2), \
        (state["virtual_equity"], round(1000.0 + expected_pnl, 2))


# ---------------------------------------------------------------------------
# (f) dry mode makes zero order/state side effects — holding+ratchet, and
#     entering.
# ---------------------------------------------------------------------------

def test_f_dry_mode_zero_side_effects():
    # -- holding, with a candle series that WOULD ratchet in live mode ------
    t = _open_long(entry=100300.0, contracts=10.0, entry_bar_high=100600.0,
                   entry_bar_low=100000.0)
    before = dict(t)   # shallow snapshot for comparison
    state = make_state()
    state["newsdesk"]["open_trade"] = t
    private = FakePrivate(net=10.0)
    feed = FakeCandleFeed()
    entry_ts_f = ts("2026-07-23 15:00:00")
    rows = [{"timestamp": entry_ts_f, "open": 100000.0,
             "high": 100600.0, "low": 100000.0, "close": 100300.0}]
    for i in range(1, 12):
        low = 100500.0 if i == 6 else 101000.0
        rows.append({"timestamp": hour_ts(entry_ts_f, i),
                    "open": 101000.0, "high": 102000.0, "low": low,
                    "close": 101000.0})
    feed.set_candles(rows)

    result = newsdesk.run_newsdesk(private, feed, feed, state, dry=True)
    assert result["action"] == "holding", result
    assert private.orders == [] and private.tpsl_placed == [] \
        and private.cancels == [], "dry mode must place/cancel NOTHING"
    assert t == before, "dry mode must not mutate the trade record, even " \
                        "though a live cycle would have ratcheted it"

    # -- entering, dry ---------------------------------------------------
    state2 = make_state()
    private2 = FakePrivate(net=0.0)
    feed2 = FakeCandleFeed()
    state2["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: dry entry",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed2.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100600.0, "low": 100000.0, "close": 100550.0},
    ])
    result2 = newsdesk.run_newsdesk(private2, feed2, feed2, state2, dry=True)
    assert result2["action"] == "would_enter", result2
    assert "est_sl" in result2 and "est_tp" not in result2
    assert private2.orders == [] and private2.tpsl_placed == []
    assert state2["newsdesk"]["open_trade"] is None
    assert state2["newsdesk"]["pending"] is not None, \
        "dry mode must not clear pending either"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


# ===========================================================================
# GUARD: the newsdesk must stay stood down until it is re-validated
# ===========================================================================

def test_z_newsdesk_stood_down():
    """Rounds 150+170. News momentum was BTC's ONLY sealed-pass edge across
    45 rounds (+$10.35/trade). Re-tested at taker execution with a real
    chart-structure stop: train -$8.88 / val -$15.25. A wider stop turns it
    technically positive (+$5.82/+$0.32) at 0.03x round-trip cost — an edge
    three percent the size of the cost of trading it. Round 170: fails at
    val on ETH too. This book also holds the two largest losers on the live
    record.

    This test exists so it cannot quietly resume."""
    import importlib, newsdesk as fresh
    importlib.reload(fresh)
    assert fresh.NEW_ENTRIES_ENABLED is False, (
        "the newsdesk is taking new entries again without a fresh gauntlet")
    import inspect
    src = inspect.getsource(fresh.run_newsdesk)
    assert "STAND-DOWN GATE" in src, "the stand-down gate was removed"
    assert src.index("STAND-DOWN GATE") > src.index("open_trade"), (
        "the stand-down gate must not run before exits reconcile")


def main():
    import newsdesk as _m
    _m.NEW_ENTRIES_ENABLED = True   # mechanics tests exercise the entry path; test_z re-checks the flag
    tests = [
        test_a_initial_stop_entry_bar_extreme,
        test_b_floor_ratchets_up_never_back,
        test_c_no_tp_ever_placed,
        test_d_24h_time_exit_intact,
        test_e_bracket_fired_exit_uses_trailed_sl,
        test_f_dry_mode_zero_side_effects,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("NEWSDESK EXIT (ROUND 65 N2) TEST SUMMARY")
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
