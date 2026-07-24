"""
test_newsdesk_timing.py — offline tests for newsdesk.py's no-lookahead
timing (matched to step45b_news_events.align_events), the direction gate,
reconcile/exit math, and the doji discard. NO NETWORK.

Run with:  python3 test_newsdesk_timing.py

Reuses test_book_attribution.py's FakePrivate (a fake BlofinDemoPrivate
that records every order/cancel/bracket call so a test can assert exactly
what did — or, more often here, did NOT — happen) and its no-op
notify/log_event/save_state neutralization pattern, applied to newsdesk
itself.
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

import newsdesk
import step5_paper_trade as s5
from test_book_attribution import FakePrivate, make_state

SYMBOL = "BTC-USDT"


class FakeCandleFeed:
    """A controllable 1h-candle source. `set_candles` installs the CLOSED
    bars the test wants visible right now (mirrors the real
    BlofinExchange.get_candles contract: only confirmed/closed bars are
    ever returned — see exchange.py)."""

    def __init__(self):
        self._candles = pd.DataFrame(
            columns=["timestamp", "open", "high", "low", "close"])

    def set_candles(self, rows):
        self._candles = pd.DataFrame(rows)

    def get_candles(self, symbol, bar, n):
        return self._candles.tail(n).reset_index(drop=True)

    def get_ticker(self, symbol):
        last = float(self._candles["close"].iloc[-1]) if len(self._candles) else 65000.0
        class _T:
            pass
        t = _T()
        t.last, t.bid, t.ask = last, last, last
        return t


def ts(s: str) -> pd.Timestamp:
    return pd.Timestamp(s, tz="UTC")


def _noop(*a, **kw):
    pass


def _no_news(n=None):
    return []      # the offline default: no test may ever hit the real RPC


def _reset_newsdesk_side_effects():
    newsdesk.notify = _noop
    newsdesk.log_event = _noop
    newsdesk.save_state = _noop
    newsdesk.time.sleep = _noop
    newsdesk._fetch_recent_news = _no_news   # NEVER the real (networked) one
    # execute_maker_or_chase (called from newsdesk via step5_paper_trade)
    # polls with s5's OWN time.sleep — neutralize that too, or the fake
    # maker loop really sleeps 20s per clip.
    s5.time.sleep = _noop


_reset_newsdesk_side_effects()


def approx(a, b, tol=0.02):
    return abs(a - b) < tol


# ---------------------------------------------------------------------------
# (i) event at 14:07 -> pending direction bar opens 15:00 -> no entry
#     before 16:00 close -> entry after, correct direction from the bar's
#     own sign, correct TP/SL prices, BOTH directions.
# ---------------------------------------------------------------------------

def test_i_bar_close_timing_and_direction():
    # -- arm on a relevant WatcherGuru headline observed at 14:07 ---------
    state = make_state()
    private = FakePrivate(net=0.0)
    feed = FakeCandleFeed()

    real_now_utc = newsdesk.now_utc
    newsdesk._fetch_recent_news = \
        lambda n=newsdesk.SCAN_N: ["[WatcherGuru] JUST IN: Bitcoin ETF sees record net inflows"]
    newsdesk.now_utc = lambda: "2026-07-23 14:07:00 UTC"
    try:
        result = newsdesk.run_newsdesk(private, feed, feed, state)
    finally:
        newsdesk.now_utc = real_now_utc
        newsdesk._fetch_recent_news = _no_news   # back to the offline default
    assert result["action"] == "armed", result
    pending = state["newsdesk"]["pending"]
    assert pending is not None
    assert pending["event_ts"] == "2026-07-23 14:07:00 UTC"
    assert pending["direction_bar_open_ts"] == "2026-07-23 15:00:00 UTC", \
        f"14:07 event must arm the 15:00 direction bar, got {pending}"

    # -- before the direction bar (15:00-16:00) has closed: only bars up to
    #    14:00 exist yet -> must NOT enter, pending stays armed
    feed.set_candles([
        {"timestamp": ts("2026-07-23 13:00:00"), "open": 100000.0,
         "high": 100200.0, "low": 99900.0, "close": 100100.0},
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "pending", result
    assert state["newsdesk"]["open_trade"] is None
    assert private.orders == [], "must not enter before the direction bar closes"

    # -- the 15:00 bar has now closed, UP (close > open) -> LONG entry -----
    # round 65 N2: initial stop = THIS bar's own LOW - 0.3% buffer, no TP.
    feed.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100600.0, "low": 100000.0, "close": 100550.0},
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "entered", result
    assert result["direction"] == 1, "up bar must produce a LONG"
    assert state["newsdesk"]["pending"] is None
    t = state["newsdesk"]["open_trade"]
    assert t is not None and t["direction"] == 1
    entry = t["entry_price"]
    assert approx(entry, 100550.0), "entry fills at the direction bar's OWN close"
    assert t["tp_price"] is None, "N2 has no take-profit, ever"
    exp_sl = round(100000.0 * (1 - newsdesk.TRAIL_BUFFER_PCT / 100), 1)
    assert t["sl_price"] == exp_sl, (t["sl_price"], exp_sl)
    assert t["entry_bar_high"] == 100600.0
    assert t["entry_bar_low"] == 100000.0
    assert t["entry_bar_open_ts"] == "2026-07-23 15:00:00 UTC"
    assert t["trail_floor"] == exp_sl
    assert t["trail_k"] == newsdesk.TRAIL_K
    assert t["headline"].startswith("[WatcherGuru]")

    # -- SHORT direction, fresh state: 15:00 bar closes DOWN ---------------
    state2 = make_state()
    private2 = FakePrivate(net=0.0)
    feed2 = FakeCandleFeed()
    state2["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: SEC sues major exchange",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed2.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 103000.0,
         "high": 103100.0, "low": 102000.0, "close": 102500.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 102500.0,
         "high": 102600.0, "low": 101800.0, "close": 102000.0},
    ])
    result2 = newsdesk.run_newsdesk(private2, feed2, feed2, state2)
    assert result2["action"] == "entered", result2
    assert result2["direction"] == -1, "down bar must produce a SHORT"
    t2 = state2["newsdesk"]["open_trade"]
    entry2 = t2["entry_price"]
    assert approx(entry2, 102000.0), entry2
    assert t2["tp_price"] is None, "N2 has no take-profit, ever"
    exp_sl2 = round(102600.0 * (1 + newsdesk.TRAIL_BUFFER_PCT / 100), 1)
    assert t2["sl_price"] == exp_sl2, (t2["sl_price"], exp_sl2)
    assert t2["entry_bar_high"] == 102600.0
    assert t2["entry_bar_low"] == 101800.0


# ---------------------------------------------------------------------------
# (ii) direction-gate skip when the desired direction opposes the exchange
#      net (must never physically fight another book on the shared symbol).
# ---------------------------------------------------------------------------

def test_ii_direction_gate_skip_when_opposed():
    # desired SHORT (down bar) while the exchange net is LONG -> skip
    state = make_state()
    private = FakePrivate(net=45.0)     # e.g. the ride holding 45 ct long
    feed = FakeCandleFeed()
    state["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: something bearish",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100060.0, "low": 99400.0, "close": 99500.0},   # DOWN
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "skipped_opposed", result
    assert state["newsdesk"]["pending"] is None
    assert state["newsdesk"]["open_trade"] is None
    assert private.orders == []
    assert private.tpsl_placed == []

    # desired LONG (up bar) while the exchange net is SHORT -> skip
    state2 = make_state()
    private2 = FakePrivate(net=-30.0)   # e.g. the lab holding 30 ct short
    feed2 = FakeCandleFeed()
    state2["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: something bullish",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed2.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100050.0,
         "high": 100600.0, "low": 100000.0, "close": 100550.0},   # UP
    ])
    result2 = newsdesk.run_newsdesk(private2, feed2, feed2, state2)
    assert result2["action"] == "skipped_opposed", result2
    assert state2["newsdesk"]["pending"] is None
    assert state2["newsdesk"]["open_trade"] is None
    assert private2.orders == []
    assert private2.tpsl_placed == []


# ---------------------------------------------------------------------------
# (iii) reconcile books a favorable ("TP hit" — see note below) exit with
#       correct signed PnL for a SHORT news trade (profit when price
#       FALLS). N2 never places a real TP order any more (see round 65's
#       EXIT SWAP) — this exercises the reconcile branch's price-direction
#       reason/fee heuristic, which the task's brief says stays UNCHANGED,
#       so it is tested exactly as it already behaves, unmodified.
# ---------------------------------------------------------------------------

def test_iii_reconcile_books_short_tp_exit():
    entry = 65000.0
    contracts = 10.0
    t = {
        "trigger": "news_momentum", "direction": -1, "contracts": contracts,
        "entry_price": entry, "entry_fee_bps": 6.0,
        "entry_time": s5.now_utc(),
        "tp_price": None,
        "sl_price": round(entry * (1 + newsdesk.TRAIL_BUFFER_PCT / 100), 1),
        "tpsl_id": "tpsl-x", "max_hold_h": 24,
        "headline": "[WatcherGuru] JUST IN: test headline",
        "event_ts": s5.now_utc(),
        "entry_bar_open_ts": "2026-07-23 15:00:00 UTC",
        "entry_bar_high": entry, "entry_bar_low": entry,
        "trail_floor": round(entry * (1 + newsdesk.TRAIL_BUFFER_PCT / 100), 1),
        "trail_k": newsdesk.TRAIL_K, "ctx": {"news": "[WatcherGuru] test"},
    }
    state = make_state()
    state["newsdesk"]["open_trade"] = t
    exit_price = 63440.0        # below entry -> "TP hit" label (favorable
                                 # for a short) under the reconcile branch's
                                 # own price-direction heuristic — in N2 this
                                 # exit was actually the trailed SL firing
                                 # in-the-money, not a resting TP order
    private = FakePrivate(net=0.0, fills=[{"fillPrice": str(exit_price)}])
    feed = FakeCandleFeed()

    result = newsdesk.run_newsdesk(private, feed, feed, state)

    assert state["newsdesk"]["open_trade"] is None, "the exit must be booked"
    size_btc = contracts * newsdesk.CONTRACT_BTC
    gross = -1 * (exit_price - entry) * size_btc
    fees = (entry * 6.0 + exit_price * 2.0) * size_btc / 10_000   # TP -> maker
    expected_pnl = round(gross - fees, 2)
    assert expected_pnl > 0, "sanity: a short profiting on a fall must be positive"
    assert state["virtual_equity"] == round(1000.0 + expected_pnl, 2), \
        (state["virtual_equity"], round(1000.0 + expected_pnl, 2))
    assert state["trigger_stats"]["news_momentum"]["n"] == 1
    assert abs(state["trigger_stats"]["news_momentum"]["pnl"] - expected_pnl) < 1e-6


# ---------------------------------------------------------------------------
# (iv) a doji direction bar (open == close) discards the pending event —
#      no entry, no direction.
# ---------------------------------------------------------------------------

def test_iv_doji_discards_pending():
    state = make_state()
    private = FakePrivate(net=0.0)
    feed = FakeCandleFeed()
    state["newsdesk"]["pending"] = {
        "event_ts": "2026-07-23 14:07:00 UTC",
        "headline": "[WatcherGuru] JUST IN: doji test",
        "direction_bar_open_ts": "2026-07-23 15:00:00 UTC",
    }
    feed.set_candles([
        {"timestamp": ts("2026-07-23 14:00:00"), "open": 100100.0,
         "high": 100150.0, "low": 100000.0, "close": 100050.0},
        {"timestamp": ts("2026-07-23 15:00:00"), "open": 100200.0,
         "high": 100300.0, "low": 100100.0, "close": 100200.0},   # FLAT
    ])
    result = newsdesk.run_newsdesk(private, feed, feed, state)
    assert result["action"] == "no_direction", result
    assert state["newsdesk"]["pending"] is None
    assert state["newsdesk"]["open_trade"] is None
    assert private.orders == []
    assert private.tpsl_placed == []


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_i_bar_close_timing_and_direction,
        test_ii_direction_gate_skip_when_opposed,
        test_iii_reconcile_books_short_tp_exit,
        test_iv_doji_discards_pending,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("NEWSDESK TIMING TEST SUMMARY")
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
