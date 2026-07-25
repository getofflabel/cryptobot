"""
test_breakout_book.py — offline tests for breakout_book.py (round 87: THE
BREAKOUT BOOK, volume-gated Bollinger breakout on BTC-USDT).

Run with:  python3 test_breakout_book.py

NO NETWORK. Same discipline as test_gold_book.py / test_diver.py:
  - FakePrivate (imported from test_book_attribution) stands in for
    BlofinDemoPrivate — never an HTTP call, records every order/cancel/
    bracket call.
  - FakeFeed stands in for both live_feed and demo_feed. get_candles
    ignores its arguments and always returns the fixed frame it was built
    with; get_ticker returns that frame's last close.
  - notify / log_event / save_state are monkeypatched to no-ops on the
    breakout_book module so a test run never pings Wallace's phone or
    touches real state. time.sleep is also patched out (the bracket
    self-heal path sleeps 4s between reads).

THE SYNTHETIC FIXTURES (build_series): a low-volatility ~40-bar baseline
(small rolling std, so the Bollinger bands sit close to price) followed by
ONE breakout bar whose close jumps far enough to clear the band regardless
of volume, with its OWN volume set independently of the baseline so the
1.2x-of-trailing-20-bar-average gate can be pinned exactly on either side.
Every fixture below is verified against the REAL, imported
bollinger_breakout_signal() / volume_gate_entry() functions (never
monkeypatched, never reimplemented) via the module's own _decision() —
that IS the test, not an assumption about what those functions do.
"""

from __future__ import annotations

import copy
import sys
import traceback

import numpy as np
import pandas as pd

import breakout_book
from test_book_attribution import FakePrivate

SYMBOL = breakout_book.SYMBOL


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def build_series(direction: int = 1, vol_breakout: float = 1300.0,
                 n_base: int = 40, jump: float = 40.0, base_price: float = 100.0,
                 base_vol: float = 1000.0, hold: int = 0,
                 drop_to: float | None = None, seed: int = 1) -> pd.DataFrame:
    """See module docstring. `direction` > 0 jumps price UP through the
    upper band (long setup), < 0 jumps it DOWN through the lower band
    (short setup). `vol_breakout` is the breakout bar's own volume against
    a constant `base_vol` baseline elsewhere, so the trailing 20-bar
    average at the breakout bar sits very close to `base_vol` and the
    1.2x gate can be pinned precisely (1300 clears it, 1000 does not).
    `hold` appends bars that stay elevated/depressed (still gated in,
    verified at authoring time — see test_d). `drop_to`, if given, appends
    one final bar priced to force a clean midline cross."""
    np.random.seed(seed)
    closes = [base_price]
    for i in range(n_base):
        closes.append(closes[-1] + np.sin(i / 4.0) * 0.3)
    vols = [base_vol] * len(closes)
    if jump:
        closes.append(closes[-1] + direction * jump)
        vols.append(vol_breakout)
        for i in range(hold):
            closes.append(closes[-1] + direction * np.sin(i / 3.0) * 0.5)
            vols.append(base_vol)
        if drop_to is not None:
            closes.append(drop_to)
            vols.append(base_vol)
    n = len(closes)
    ts = pd.date_range("2020-01-01", periods=n, freq="1h", tz="UTC")
    highs = [c + 0.5 for c in closes]
    lows = [c - 0.5 for c in closes]
    opens = [closes[i - 1] if i > 0 else closes[0] for i in range(n)]
    return pd.DataFrame({"timestamp": ts, "open": opens, "high": highs,
                         "low": lows, "close": closes, "volume": vols})


class FakeFeed:
    """Stands in for both live_feed and demo_feed. get_candles ignores
    symbol/bar/n and always returns the fixed frame it was built with —
    fine here since every test only ever asks for (SYMBOL, "1h", N)."""

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
             "diver": {"open_trade": None, "last_bar_ts": None},
             "breakout_book": {"open_trade": open_trade,
                               "last_bar_ts": last_bar_ts, "trades": [],
                               "realized_pnl_total": 0.0}}
    state.update(extra_books)
    return state


# ---------------------------------------------------------------------------
# neutralize side effects, same discipline as test_diver.py
# ---------------------------------------------------------------------------

def _noop_notify(title, message):
    pass


def _noop_log_event(event):
    pass


def _noop_save_state(state):
    pass


breakout_book.notify = _noop_notify
breakout_book.log_event = _noop_log_event
breakout_book.save_state = _noop_save_state
breakout_book.time.sleep = lambda *_a, **_kw: None


# ---------------------------------------------------------------------------
# (a) entry fires on a band break WITH volume >= 1.2x, both directions,
#     AND the 6% disaster stop is sent to the exchange with the order
# ---------------------------------------------------------------------------

def test_a_entry_fires_both_directions_with_disaster_stop():
    # -- LONG ----------------------------------------------------------------
    d_long = build_series(direction=1, vol_breakout=1300.0)
    dec = breakout_book._decision(d_long)
    assert dec["entry_direction"] == 1, \
        f"fixture must show a fresh LONG transition, got {dec}"
    assert dec["prev_gated"] == 0.0 and dec["gated"] == 1.0
    assert dec["vol_ok"] is True

    feed = FakeFeed(d_long)
    private = FakePrivate(net=0.0)
    state = make_state()

    result = breakout_book.run_breakout_book(private, feed, feed, state)
    assert result["action"] == "entered", result
    assert result["direction"] == 1

    t = state["breakout_book"]["open_trade"]
    assert t is not None
    assert t["direction"] == 1
    assert t["trigger"] == "bollinger_breakout"
    assert t["tp_price"] is None, "no fixed take-profit — the midline is the exit"

    entry = t["entry_price"]
    expected_sl = round(entry * (1 - breakout_book.DISASTER_STOP_PCT / 100), 1)
    assert t["sl_price"] == expected_sl, (t["sl_price"], expected_sl)

    # sizing: 2x LEVERAGE of the full $1,000 book equity, no ALLOC fraction
    notional = 1000.0 * breakout_book.LEVERAGE
    assert notional == 1000.0 * 2.0
    assert t["contracts"] >= breakout_book.LOT

    # market order only (never resting)
    assert private.orders, "expected at least one order"
    assert all(o["kind"] == "market" for o in private.orders)
    assert all(o["side"] == "buy" for o in private.orders)

    # the 6% disaster stop was placed AS PART OF THE ORDER, tp=None, on the
    # exchange (place_tpsl) — never a book-computed close-based exit
    assert private.tpsl_placed, "expected the disaster stop to be placed"
    br = private.tpsl_placed[-1]
    assert br["tp"] is None, "no take-profit bracket"
    assert br["sl"] == expected_sl, (br["sl"], expected_sl)
    assert br["side"] == "sell", "closing a long uses a sell-side bracket"

    assert state["breakout_book"]["last_bar_ts"] == dec["bar_ts"]

    # -- SHORT -----------------------------------------------------------
    d_short = build_series(direction=-1, vol_breakout=1300.0, seed=2)
    dec_s = breakout_book._decision(d_short)
    assert dec_s["entry_direction"] == -1, \
        f"fixture must show a fresh SHORT transition, got {dec_s}"
    assert dec_s["vol_ok"] is True

    feed_s = FakeFeed(d_short)
    private_s = FakePrivate(net=0.0)
    state_s = make_state()

    result_s = breakout_book.run_breakout_book(private_s, feed_s, feed_s, state_s)
    assert result_s["action"] == "entered", result_s
    assert result_s["direction"] == -1

    t_s = state_s["breakout_book"]["open_trade"]
    assert t_s["direction"] == -1
    assert t_s["tp_price"] is None

    entry_s = t_s["entry_price"]
    expected_sl_s = round(entry_s * (1 + breakout_book.DISASTER_STOP_PCT / 100), 1)
    assert t_s["sl_price"] == expected_sl_s, (t_s["sl_price"], expected_sl_s)

    assert all(o["side"] == "sell" for o in private_s.orders)
    br_s = private_s.tpsl_placed[-1]
    assert br_s["tp"] is None
    assert br_s["sl"] == expected_sl_s
    assert br_s["side"] == "buy", "closing a short uses a buy-side bracket"


# ---------------------------------------------------------------------------
# (b) THE MOST IMPORTANT TEST: entry does NOT fire when the breakout bar's
#     volume is below 1.2x its trailing 20-bar average, either direction —
#     the volume gate IS the whole edge (round 86/87)
# ---------------------------------------------------------------------------

def test_b_volume_gate_blocks_entry_both_directions():
    # -- LONG side, price clears the band but volume does not (1.0x) -------
    d = build_series(direction=1, vol_breakout=1000.0)
    dec = breakout_book._decision(d)
    assert dec["base_sig"] == 1.0, \
        "the RAW (ungated) signal must still show a breakout — proves the " \
        "block is coming from the volume gate, not a bad fixture"
    assert dec["vol_ok"] is False, "breakout bar volume must be BELOW 1.2x"
    assert dec["gated"] == 0.0, "the gate must suppress the signal entirely"
    assert dec["entry_direction"] == 0, \
        "no fresh transition -> no entry, despite a real band break"

    feed = FakeFeed(d)
    private = FakePrivate(net=0.0)
    state = make_state()
    result = breakout_book.run_breakout_book(private, feed, feed, state)

    assert result["action"] == "no_signal", result
    assert private.orders == [], \
        "a volume-blocked breakout must place ZERO orders"
    assert private.tpsl_placed == []
    assert state["breakout_book"]["open_trade"] is None

    # -- SHORT side, same story, mirrored -----------------------------------
    d2 = build_series(direction=-1, vol_breakout=1000.0, seed=2)
    dec2 = breakout_book._decision(d2)
    assert dec2["base_sig"] == -1.0
    assert dec2["vol_ok"] is False
    assert dec2["gated"] == 0.0
    assert dec2["entry_direction"] == 0

    feed2 = FakeFeed(d2)
    private2 = FakePrivate(net=0.0)
    state2 = make_state()
    result2 = breakout_book.run_breakout_book(private2, feed2, feed2, state2)

    assert result2["action"] == "no_signal", result2
    assert private2.orders == []
    assert state2["breakout_book"]["open_trade"] is None

    # -- sanity: the EXACT same price move with volume >= 1.2x DOES enter,
    #    proving 1000 vs 1300 volume is the only thing that changed ---------
    d_pass = build_series(direction=1, vol_breakout=1300.0)
    feed_pass = FakeFeed(d_pass)
    private_pass = FakePrivate(net=0.0)
    state_pass = make_state()
    result_pass = breakout_book.run_breakout_book(private_pass, feed_pass,
                                                   feed_pass, state_pass)
    assert result_pass["action"] == "entered", result_pass


# ---------------------------------------------------------------------------
# (c) no entry on an unclosed/forming bar — a bar the exchange adapter
#     hasn't returned yet (BloFin's own "confirmed" flag) can never trigger
#     an entry, because the decision only ever reads bars actually present
#     in the closed series it was handed
# ---------------------------------------------------------------------------

def test_c_no_entry_on_unclosed_forming_bar():
    # the full series WITH the breakout bar closed and appended
    d_closed = build_series(direction=1, vol_breakout=1300.0)
    # the same series with that bar NOT YET returned by the exchange (i.e.
    # still forming, exactly what BlofinExchange.get_candles guarantees
    # never happens — see gold_book.py's DATA section) — simulated by
    # simply not including it
    d_forming = d_closed.iloc[:-1].reset_index(drop=True)

    dec_forming = breakout_book._decision(d_forming)
    assert dec_forming["entry_direction"] == 0, \
        "a bar not yet present in the closed series must never look like a breakout"
    assert dec_forming["gated"] == 0.0

    feed_forming = FakeFeed(d_forming)
    private_forming = FakePrivate(net=0.0)
    state_forming = make_state()
    result_forming = breakout_book.run_breakout_book(
        private_forming, feed_forming, feed_forming, state_forming)
    assert result_forming["action"] == "no_signal", result_forming
    assert private_forming.orders == [], \
        "the still-forming bar must never place an order"

    # the moment that exact bar actually CLOSES (appears in the series),
    # the same decision logic correctly fires — proves the prior no-op was
    # about the bar being absent, not a broken fixture
    dec_closed = breakout_book._decision(d_closed)
    assert dec_closed["entry_direction"] == 1
    feed_closed = FakeFeed(d_closed)
    private_closed = FakePrivate(net=0.0)
    state_closed = make_state()
    result_closed = breakout_book.run_breakout_book(
        private_closed, feed_closed, feed_closed, state_closed)
    assert result_closed["action"] == "entered", result_closed


# ---------------------------------------------------------------------------
# (d) exit triggers on a midline cross back, and ONLY then — holding while
#     price stays on our side of the midline must never exit early
# ---------------------------------------------------------------------------

def test_d_exit_only_on_midline_cross():
    d_full = build_series(direction=1, vol_breakout=1300.0, hold=6, drop_to=95.0)
    dec_full = breakout_book._decision(d_full)
    assert dec_full["gated"] == 0.0, \
        "fixture's final bar must show the midline cross (gated back to 0)"

    # entry price = the breakout bar's close (bar index 41 in this fixture)
    entry_price = float(d_full["close"].iloc[41])
    t = {"trigger": "bollinger_breakout", "direction": 1, "contracts": 10.0,
        "entry_price": entry_price, "entry_fee_bps": 6.0,
        "entry_time": breakout_book.now_utc(),
        "tp_price": None,
        "sl_price": round(entry_price * (1 - breakout_book.DISASTER_STOP_PCT / 100), 1),
        "tpsl_id": "tpsl-hold", "bar_ts": "x"}

    # -- (d1) still HOLDING: truncate the series to the last bar BEFORE the
    #    drop (still gated in) — must NOT exit, disaster stop stays as-is --
    d_holding = d_full.iloc[:-1].reset_index(drop=True)   # through the last hold bar
    dec_holding = breakout_book._decision(d_holding)
    assert dec_holding["gated"] == 1.0, \
        "must still be gated in one bar before the drop"

    feed_holding = FakeFeed(d_holding)
    private_holding = FakePrivate(
        net=10.0, pending_tpsl_default=[{"tpslId": "tpsl-hold"}])
    state_holding = make_state(open_trade=dict(t))

    result_holding = breakout_book.run_breakout_book(
        private_holding, feed_holding, feed_holding, state_holding)
    assert result_holding["action"] == "hold", result_holding
    assert private_holding.orders == [], "must place zero orders while still holding"
    assert state_holding["breakout_book"]["open_trade"] is not None, \
        "must NOT exit before the midline cross"

    # -- (d2) the drop bar: midline cross -> must exit now, exactly once ---
    feed_exit = FakeFeed(d_full)
    private_exit = FakePrivate(
        net=10.0, pending_tpsl_default=[{"tpslId": "tpsl-hold"}])
    state_exit = make_state(open_trade=dict(t))

    result_exit = breakout_book.run_breakout_book(
        private_exit, feed_exit, feed_exit, state_exit)
    assert result_exit["action"] == "exited", result_exit
    assert result_exit["reason"] == "midline_exit"
    assert state_exit["breakout_book"]["open_trade"] is None, \
        "the position must be closed on the book"

    # closing a long uses a reduce-only sell market order
    assert private_exit.orders, "expected a market close order"
    close_order = private_exit.orders[-1]
    assert close_order["kind"] == "market"
    assert close_order["side"] == "sell"
    assert close_order["reduce_only"] is True

    # the resting disaster-stop bracket was cancelled on exit
    assert any(c["kind"] == "tpsl" for c in private_exit.cancels), \
        "the disaster-stop bracket must be cancelled on a signal exit"


# ---------------------------------------------------------------------------
# (e) OWNERSHIP HANDSHAKE: a net position explained by ANOTHER book's own
#     recorded claim is left completely alone — never flattened, never
#     adjusted, no alert
# ---------------------------------------------------------------------------

def test_e_handshake_other_book_position_left_alone():
    # a flat, no-signal price series so nothing about OUR own signal
    # muddies this test
    d = build_series(direction=1, vol_breakout=1300.0, n_base=60, jump=0.0)
    dec = breakout_book._decision(d)
    assert dec["entry_direction"] == 0, "fixture must be signal-flat"

    feed = FakeFeed(d)
    # the diver holds 50ct long BTC-USDT — the exchange net matches that
    # claim EXACTLY, so book_ledger's unexplained_position(...) must read 0
    state = make_state()
    state["diver"]["open_trade"] = {"direction": 1, "contracts": 50.0,
                                    "entry_price": 65000.0}
    private = FakePrivate(net=50.0)
    diver_before = copy.deepcopy(state["diver"])

    notified = []
    breakout_book.notify = lambda title, msg: notified.append((title, msg))
    try:
        result = breakout_book.run_breakout_book(private, feed, feed, state)
    finally:
        breakout_book.notify = _noop_notify

    assert result["action"] == "no_signal", result
    assert private.orders == [], \
        "must never touch a position explained by another book's own claim"
    assert private.cancels == []
    assert state["diver"] == diver_before, \
        "must never adjust another book's own recorded trade"
    assert state["breakout_book"]["open_trade"] is None
    assert not notified, \
        "a fully-explained net position must not trigger the unexplained alert"

    # -- contrast: a slice of net NO book claims DOES alert, exactly once --
    private_orphan = FakePrivate(net=65.0)   # 50ct explained by diver, 15ct not
    state_orphan = make_state()
    state_orphan["diver"]["open_trade"] = {"direction": 1, "contracts": 50.0,
                                           "entry_price": 65000.0}
    notified2 = []
    breakout_book.notify = lambda title, msg: notified2.append((title, msg))
    try:
        r1 = breakout_book.run_breakout_book(private_orphan, feed, feed, state_orphan)
        # simulate a SEPARATE later cycle (a new bar, or just another daemon
        # trigger) rather than the same-bar idempotency guard — that guard
        # is a different mechanism (see test elsewhere) and would mask what
        # this assertion is actually checking: that the ALERT ITSELF, not
        # bar idempotency, is what keeps a persistent unclaimed slice from
        # spamming Wallace's phone every cycle.
        state_orphan["breakout_book"]["last_bar_ts"] = "2000-01-01 00:00 UTC"
        r2 = breakout_book.run_breakout_book(private_orphan, feed, feed, state_orphan)
    finally:
        breakout_book.notify = _noop_notify

    assert r1["action"] == "no_signal" and r2["action"] == "no_signal", (r1, r2)
    assert private_orphan.orders == [], \
        "an unclaimed slice is never adopted, only alerted on"
    assert len(notified2) == 1, \
        f"the unclaimed-position alert must fire exactly ONCE per episode, got {notified2}"


# ---------------------------------------------------------------------------
# (f) this book NEVER writes another book's state keys
# ---------------------------------------------------------------------------

def test_f_never_writes_other_books_state_keys():
    d = build_series(direction=1, vol_breakout=1300.0)
    feed = FakeFeed(d)
    state = make_state()
    # populate a realistic multi-book state so there is plenty to accidentally
    # clobber if the book were careless. net is kept CONSISTENT with the sum
    # of every book's own recorded claim (3 + 2 - 4 = 1.0) so the reconcile
    # step reads a clean, fully-explained net (unexplained ~= 0) and this
    # test stays focused purely on "did it touch keys it shouldn't".
    state["open_trade"] = {"contracts": 3.0, "entry_price": 60000.0}
    state["tactical"]["open_trade"] = {"contracts": 2.0, "entry_price": 61000.0}
    state["shorts_lab"]["open_trade"] = {"direction": -1, "contracts": 4.0}
    state["newsdesk"]["open_trade"] = None
    state["newsdesk"]["pending"] = None
    state["diver"]["open_trade"] = None
    state["some_other_future_book"] = {"nested": {"data": [1, 2, 3]}, "n": 7}
    private = FakePrivate(net=1.0)

    before = copy.deepcopy(state)
    result = breakout_book.run_breakout_book(private, feed, feed, state)
    assert result["action"] == "entered", result

    for key in before:
        if key in ("breakout_book",):
            continue
        assert state[key] == before[key], \
            f"breakout_book must never modify state[{key!r}], but it changed"
    assert state["breakout_book"] != before["breakout_book"], \
        "sanity: the book DID write its own key"


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def test_g_stood_down_book_does_nothing():
    """The kill switch must actually stop the book. Round 87 validated this
    strategy on MAKER fills; the OWNER'S LAW requires MARKET (taker) orders,
    and re-priced at taker the BTC edge is -$8.15/trade. It stays off until
    a taker-viable variant exists."""
    import breakout_book as _bb
    prev = _bb.ENABLED
    _bb.ENABLED = False
    try:
        out = _bb.run_breakout_book(None, None, None, {})
    finally:
        _bb.ENABLED = prev
    assert out["action"] == "stood_down", out
    # and it must not have created or touched any book state
    st = {}
    _bb.ENABLED = False
    try:
        _bb.run_breakout_book(None, None, None, st)
    finally:
        _bb.ENABLED = prev
    assert st == {}, f"a stood-down book must not write state: {st}"


def main():
    import breakout_book as _bb
    _bb.ENABLED = True   # logic tests exercise the strategy; test_g flips it back
    tests = [
        test_a_entry_fires_both_directions_with_disaster_stop,
        test_b_volume_gate_blocks_entry_both_directions,
        test_c_no_entry_on_unclosed_forming_bar,
        test_d_exit_only_on_midline_cross,
        test_e_handshake_other_book_position_left_alone,
        test_f_never_writes_other_books_state_keys,
        test_g_stood_down_book_does_nothing,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("THE BREAKOUT BOOK — TEST SUMMARY")
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
