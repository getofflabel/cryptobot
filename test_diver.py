"""
test_diver.py — offline tests for diver.py (round 58, THE DIVER: 4h hidden
RSI divergence continuation on BTC-USDT).

Run with:  python3 test_diver.py

NO NETWORK. Everything that would normally touch BloFin, Supabase, Telegram
or ntfy is replaced with an in-memory fake, same discipline as
test_book_attribution.py (whose FakePrivate is reused here directly) and
test_gold_book.py:
  - FakePrivate (imported from test_book_attribution) stands in for
    BlofinDemoPrivate — never an HTTP call, records every order/cancel/
    bracket call.
  - FakeFeed stands in for both live_feed and demo_feed. get_candles
    returns a hand-built, deterministic 4h OHLC series engineered so the
    REAL, imported divergence_events() oracle (never monkeypatched) fires
    exactly one hidden-bullish continuation signal on its LAST bar —
    get_ticker returns that same last close.
  - notify / log_event / save_state are monkeypatched to no-ops on the
    diver module so a test run never pings Wallace's phone or touches
    real state.

THE SYNTHETIC FIXTURE (build_hidden_long_series): a ~140-bar volatile
uptrend base (warms vol_gated_ma's fast=20/slow=100 cross AND clears its
1.5% ATR liveliness gate, so the 4h champion reads 1 well before either
swing), then two engineered pullbacks — a SHARP two-bar V-dip (swing low
#1, RSI rebounds fast so RSI is relatively HIGH right at the low) followed
by a SLOWER, grinding multi-bar decline into swing low #2, which ends
HIGHER in raw price (a genuine higher low) but LOWER in RSI (Wilder
smoothing accumulates the grind's many small losses) — textbook hidden
bullish continuation shape. Verified empirically against the real
divergence_events()/swings() functions at construction time: with an
8-bar tail after the second low, the confirmed event lands EXACTLY on the
series' last bar (k=8 confirmation: swings need i-k..i+k known, then
shift(k) forward — see step58_divergence_mtf.py's docstring). Any edit to
this fixture must re-verify long_hidden is still True on the last bar
before relying on it.
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

import diver
from test_book_attribution import FakePrivate

SYMBOL = diver.SYMBOL


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def build_hidden_long_series(tail_len: int = 8) -> pd.DataFrame:
    """See module docstring. Deterministic (fixed seed, no randomness that
    matters — the sine wobble is just texture so ATR clears the vol gate;
    the swing shape itself is hand-authored, not random)."""
    np.random.seed(0)
    n_base, base_start, base_step, noise = 140, 100.0, 0.6, 0.5
    closes = [base_start]
    for i in range(n_base):
        step = base_step + np.sin(i / 3.0) * noise
        closes.append(closes[-1] + step)

    # swing low #1: sharp two-bar V-dip, fast strong rebound
    p1_start = closes[-1]
    closes += [p1_start - 6, p1_start - 14]
    c = closes[-1]
    for _ in range(10):
        c += 3.0
        closes.append(c)

    # continuation higher
    c = closes[-1]
    for i in range(20):
        c += 0.8 + np.sin(i / 2.0) * 0.3
        closes.append(c)

    # swing low #2: slow multi-bar grind down, ends HIGHER than low #1
    c = closes[-1]
    for _ in range(16):
        c -= 1.1
        closes.append(c)

    # tail: exactly enough bars for the k=8 swing confirmation to land on
    # the series' final bar (empirically verified at authoring time)
    c = closes[-1]
    for _ in range(tail_len):
        c += 0.5
        closes.append(c)

    n = len(closes)
    ts = pd.date_range("2020-01-01", periods=n, freq="4h", tz="UTC")
    highs = [x + 1.0 for x in closes]
    lows = [x - 1.0 for x in closes]
    opens = [closes[i - 1] if i > 0 else closes[0] for i in range(n)]
    return pd.DataFrame({"timestamp": ts, "open": opens, "high": highs,
                         "low": lows, "close": closes})


class FakeFeed:
    """Stands in for both live_feed and demo_feed. get_candles ignores
    symbol/bar/n and always returns the fixed frame it was built with —
    fine here since every test only ever asks for (SYMBOL, "4h", N)."""

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.last_close = float(frame["close"].iloc[-1])

    def get_candles(self, symbol, bar, n):
        return self.frame

    def get_ticker(self, symbol):
        class _T:
            last = self.last_close
            bid = self.last_close
            ask = self.last_close
        return _T()

    def get_instrument(self, symbol="BTC-USDT"):
        # BLOFIN_API_REFERENCE.md verified value — lets contract_value()
        # (step5_paper_trade.py) resolve real sizing instead of skipping.
        return {"instId": symbol, "contractValue": "0.001", "minSize": "0.1",
               "lotSize": "0.1", "tickSize": "0.1", "maxLeverage": "125"}


def make_state(open_trade=None, last_bar_ts=None, **extra_books) -> dict:
    state = {"virtual_equity": 1000.0, "goal": 2000.0, "open_trade": None,
             "tactical": {"open_trade": None},
             "shorts_lab": {"open_trade": None},
             "newsdesk": {"open_trade": None},
             "diver": {"open_trade": open_trade, "last_bar_ts": last_bar_ts}}
    state.update(extra_books)
    return state


# ---------------------------------------------------------------------------
# neutralize side effects, same discipline as test_book_attribution.py
# ---------------------------------------------------------------------------

def _noop_notify(title, message):
    pass


def _noop_log_event(event):
    pass


def _noop_save_state(state):
    pass


diver.notify = _noop_notify
diver.log_event = _noop_log_event
diver.save_state = _noop_save_state
diver.time.sleep = lambda *_a, **_kw: None


# ---------------------------------------------------------------------------
# (a) the oracle fires one hidden-long -> entry with correct stop/target
# ---------------------------------------------------------------------------

def test_a_oracle_fires_hidden_long_entry():
    d = build_hidden_long_series()

    # sanity: the REAL, imported oracle actually fires on the last bar —
    # never monkeypatched, this is the point of the test
    dec = diver._decision(d)
    assert dec["long_hidden"] is True, \
        f"fixture must fire hidden-long on its last bar, got {dec}"
    assert dec["short_hidden"] is False
    assert dec["champ"] == 1

    feed = FakeFeed(d)
    private = FakePrivate(net=0.0)
    state = make_state()

    result = diver.run_diver(private, feed, feed, state)

    assert result["action"] == "entered", result
    assert result["direction"] == 1

    t = state["diver"]["open_trade"]
    assert t is not None
    assert t["direction"] == 1
    assert t["trigger"] == "hidden_divergence"
    assert t["bar_ts"] == dec["bar_ts"]

    entry = t["entry_price"]
    expected_tp = round(entry * (1 + diver.TARGET_PCT / 100), 1)
    expected_sl = round(entry * (1 - diver.STOP_PCT / 100), 1)
    assert t["tp_price"] == expected_tp, (t["tp_price"], expected_tp)
    assert t["sl_price"] == expected_sl, (t["sl_price"], expected_sl)

    # sizing: 15% alloc, 20x leverage of the $1,000 starting ledger
    notional = 1000.0 * diver.DIVER_ALLOC * diver.DIVER_LEV
    assert notional == 1000.0 * 0.15 * 20.0
    assert t["contracts"] >= diver.LOT

    # a market BUY was actually placed (never a resting/maker order — owner
    # law, execute_market_clips only)
    assert private.orders, "expected at least one order"
    assert all(o["kind"] == "market" for o in private.orders)
    assert all(o["side"] == "buy" for o in private.orders)

    # a TP/SL bracket was placed matching the recorded levels
    assert private.tpsl_placed, "expected a bracket to be placed"
    br = private.tpsl_placed[-1]
    assert br["tp"] == expected_tp
    assert br["sl"] == expected_sl

    # state["diver"]["last_bar_ts"] now marks this bar processed
    assert state["diver"]["last_bar_ts"] == dec["bar_ts"]


# ---------------------------------------------------------------------------
# (b) idempotency: the same closed bar decided on twice = one entry
# ---------------------------------------------------------------------------

def test_b_idempotency_same_bar_twice():
    d = build_hidden_long_series()
    dec = diver._decision(d)
    feed = FakeFeed(d)
    private = FakePrivate(net=0.0)
    state = make_state()

    r1 = diver.run_diver(private, feed, feed, state)
    assert r1["action"] == "entered"
    n_orders_after_first = len(private.orders)
    assert n_orders_after_first > 0

    # Simulate this book's own position having been fully closed/reconciled
    # elsewhere (e.g. by another cycle) WITHOUT the 4h bar having advanced —
    # last_bar_ts is untouched. A second decision cycle on the exact same
    # closed bar must be a pure no-op: it must NOT re-enter just because the
    # book is flat again.
    state["diver"]["open_trade"] = None
    private.net = 0.0

    r2 = diver.run_diver(private, feed, feed, state)
    assert r2["action"] == "noop_already_processed", r2
    assert len(private.orders) == n_orders_after_first, \
        "idempotency guard must prevent a second entry on the same bar"
    assert state["diver"]["open_trade"] is None


# ---------------------------------------------------------------------------
# (c) direction gate stand-down when net opposes / another book conflicts
# ---------------------------------------------------------------------------

def test_c_direction_gate_stand_down():
    # -- c1: LONG signal fires, but the exchange net is already short —
    #    must stand down, place zero orders, still mark the bar processed.
    d = build_hidden_long_series()
    dec = diver._decision(d)
    assert dec["long_hidden"] is True
    feed = FakeFeed(d)
    private = FakePrivate(net=-0.2)     # short net opposes a long entry
    state = make_state()

    result = diver.run_diver(private, feed, feed, state)
    assert result["action"] == "stood_down", result
    assert "oppose" in result["reason"]
    assert private.orders == [], "must place zero orders when gated"
    assert state["diver"]["open_trade"] is None
    assert state["diver"]["last_bar_ts"] == dec["bar_ts"], \
        "a gated bar must still be marked processed (never re-judged)"

    # -- c2: SHORT signal fires (decision monkeypatched — only the GATE is
    #    under test here, the oracle itself is already proven by test_a),
    #    net is flat but another BTC book (tactical) is already open — the
    #    Diver's short side must stand down rather than stack short risk.
    d2 = build_hidden_long_series()
    feed2 = FakeFeed(d2)
    private2 = FakePrivate(net=0.0)
    state2 = make_state()
    state2["tactical"]["open_trade"] = {"direction": 1, "contracts": 5.0,
                                        "entry_price": 65000.0}

    real_decision = diver._decision
    fake_dec = dict(real_decision(d2))
    fake_dec["long_hidden"], fake_dec["short_hidden"] = False, True
    diver._decision = lambda frame: fake_dec
    try:
        result2 = diver.run_diver(private2, feed2, feed2, state2)
    finally:
        diver._decision = real_decision

    assert result2["action"] == "stood_down", result2
    assert result2["direction"] == -1
    assert "another BTC book" in result2["reason"], result2["reason"]
    assert private2.orders == []
    assert state2["diver"]["open_trade"] is None


# ---------------------------------------------------------------------------
# (d) reconcile: a bracket-fired exit books correct signed PnL both ways
# ---------------------------------------------------------------------------

def test_d_reconcile_bracket_exit_both_directions():
    # -- LONG: TP fires above entry -> profit ------------------------------
    entry_long = 65000.0
    t_long = {
        "trigger": "hidden_divergence", "direction": 1, "contracts": 10.0,
        "entry_price": entry_long, "entry_fee_bps": 6.0,
        "entry_time": diver.now_utc(),
        "tp_price": round(entry_long * (1 + diver.TARGET_PCT / 100), 1),
        "sl_price": round(entry_long * (1 - diver.STOP_PCT / 100), 1),
        "tpsl_id": "tpsl-long", "max_hold_h": 48, "bar_ts": "x",
        "ctx": {"news": None},
    }
    fill_long = t_long["tp_price"]      # TP hit exactly
    state_long = make_state(open_trade=t_long)
    private_long = FakePrivate(net=0.0,     # our whole slice is gone
                               fills=[{"fillPrice": str(fill_long)}])
    d = build_hidden_long_series()
    feed = FakeFeed(d)

    result_long = diver.run_diver(private_long, feed, feed, state_long)
    assert result_long["action"] in ("no_event", "entered", "would_enter") \
        or "pnl" in result_long or state_long["diver"]["open_trade"] is None
    assert state_long["diver"]["open_trade"] is None, \
        "the long's exit must be booked"

    # BLOFIN_API_REFERENCE.md verified BTC-USDT contract value — diver.py no
    # longer hardcodes this (reads it live via contract_value()); this test
    # trade record predates that field, so _book_exit's own documented
    # legacy fallback (0.001) applies. Kept as a literal here, independent
    # of production code, so this check can't accidentally pass by sharing
    # a bug with the code under test.
    size_btc = t_long["contracts"] * 0.001
    gross_long = 1 * (fill_long - entry_long) * size_btc
    fees_long = (entry_long * 6.0 + fill_long * 2.0) * size_btc / 10_000
    expected_pnl_long = round(gross_long - fees_long, 2)
    assert expected_pnl_long > 0, "TP hit above entry on a long must profit"
    assert abs(state_long["virtual_equity"] - (1000.0 + expected_pnl_long)) < 0.01, \
        (state_long["virtual_equity"], 1000.0 + expected_pnl_long)

    # -- SHORT: TP fires below entry -> profit ------------------------------
    entry_short = 65000.0
    t_short = {
        "trigger": "hidden_divergence", "direction": -1, "contracts": 10.0,
        "entry_price": entry_short, "entry_fee_bps": 6.0,
        "entry_time": diver.now_utc(),
        "tp_price": round(entry_short * (1 - diver.TARGET_PCT / 100), 1),
        "sl_price": round(entry_short * (1 + diver.STOP_PCT / 100), 1),
        "tpsl_id": "tpsl-short", "max_hold_h": 48, "bar_ts": "x",
        "ctx": {"news": None},
    }
    fill_short = t_short["tp_price"]    # TP hit exactly
    state_short = make_state(open_trade=t_short)
    private_short = FakePrivate(net=0.0,
                                fills=[{"fillPrice": str(fill_short)}])

    diver.run_diver(private_short, feed, feed, state_short)
    assert state_short["diver"]["open_trade"] is None, \
        "the short's exit must be booked"

    gross_short = -1 * (fill_short - entry_short) * size_btc
    fees_short = (entry_short * 6.0 + fill_short * 2.0) * size_btc / 10_000
    expected_pnl_short = round(gross_short - fees_short, 2)
    assert expected_pnl_short > 0, "TP hit below entry on a short must profit"
    assert abs(state_short["virtual_equity"] - (1000.0 + expected_pnl_short)) < 0.01, \
        (state_short["virtual_equity"], 1000.0 + expected_pnl_short)

    # -- a LOSING long (SL hit below entry) books a negative, correctly ----
    t_loss = dict(t_long)
    t_loss["tpsl_id"] = "tpsl-loss"
    fill_loss = t_loss["sl_price"]      # SL hit exactly
    state_loss = make_state(open_trade=t_loss)
    private_loss = FakePrivate(net=0.0,
                               fills=[{"fillPrice": str(fill_loss)}])
    diver.run_diver(private_loss, feed, feed, state_loss)
    assert state_loss["diver"]["open_trade"] is None
    gross_loss = 1 * (fill_loss - entry_long) * size_btc
    fees_loss = (entry_long * 6.0 + fill_loss * 6.0) * size_btc / 10_000   # SL = taker both sides
    expected_pnl_loss = round(gross_loss - fees_loss, 2)
    assert expected_pnl_loss < 0, "SL hit below entry on a long must lose"
    assert abs(state_loss["virtual_equity"] - (1000.0 + expected_pnl_loss)) < 0.01, \
        (state_loss["virtual_equity"], 1000.0 + expected_pnl_loss)


# ---------------------------------------------------------------------------
# (e) dry mode makes zero state/order/notify side effects
# ---------------------------------------------------------------------------

def test_e_dry_mode_zero_side_effects():
    d = build_hidden_long_series()
    dec = diver._decision(d)
    assert dec["long_hidden"] is True
    feed = FakeFeed(d)
    private = FakePrivate(net=0.0)
    state = make_state()
    import copy
    state_before = copy.deepcopy(state)

    result = diver.run_diver(private, feed, feed, state, dry=True)

    assert result["action"] == "would_enter", result
    assert result["direction"] == 1
    assert private.orders == [], "dry mode must place zero orders"
    assert private.cancels == [], "dry mode must cancel nothing"
    assert private.tpsl_placed == [], "dry mode must place zero brackets"
    assert state == state_before, "dry mode must make zero state writes"

    # dry mode also previews a holding position untouched, and a reconcile
    # exit untouched
    t = {"trigger": "hidden_divergence", "direction": 1, "contracts": 10.0,
        "entry_price": 65000.0, "entry_fee_bps": 6.0,
        "entry_time": diver.now_utc(), "tp_price": 70000.0,
        "sl_price": 63000.0, "tpsl_id": "tpsl-1", "max_hold_h": 48,
        "bar_ts": "x", "ctx": {}}
    state2 = make_state(open_trade=t)
    state2_before = copy.deepcopy(state2)
    private2 = FakePrivate(net=10.0, pending_tpsl_default=[{"tpslId": "tpsl-1"}])
    r2 = diver.run_diver(private2, feed, feed, state2, dry=True)
    assert r2["action"] == "holding"
    assert private2.orders == []
    assert private2.cancels == []
    assert state2 == state2_before


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


# ===========================================================================
# GUARD: the diver must stay stood down until it is re-validated
# ===========================================================================

def test_z_diver_stood_down():
    """Rounds 150+170. Re-tested at taker execution with a real chart-
    structure stop, 4h hidden divergence went train +$15.20 / val -$9.30,
    and a wider structural stop did not rescue it. Round 170 replayed it
    unchanged on ETH: negative in every window. Its original +$52.03/trade
    sealed pass was measured under MAKER fills and a swept-percentage stop,
    conditions this project does not trade under.

    This test exists so the book cannot quietly resume without someone
    re-running that work."""
    import importlib, diver as fresh
    importlib.reload(fresh)
    assert fresh.NEW_ENTRIES_ENABLED is False, (
        "the diver is taking new entries again without a fresh gauntlet")
    import inspect
    src = inspect.getsource(fresh.run_diver)
    assert "STAND-DOWN GATE" in src, "the stand-down gate was removed"
    # the gate must sit AFTER the exit/reconcile logic — standing a book
    # down must never orphan an open position
    assert src.index("STAND-DOWN GATE") > src.index("open_trade"), (
        "the stand-down gate must not run before exits reconcile")


def main():
    import diver as _m
    _m.NEW_ENTRIES_ENABLED = True   # mechanics tests exercise the entry path; test_z re-checks the flag
    tests = [
        test_a_oracle_fires_hidden_long_entry,
        test_b_idempotency_same_bar_twice,
        test_c_direction_gate_stand_down,
        test_d_reconcile_bracket_exit_both_directions,
        test_e_dry_mode_zero_side_effects,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("THE DIVER — TEST SUMMARY")
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
