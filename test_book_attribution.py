"""
test_book_attribution.py — offline tests for book_ledger.py and the
2026-07-23 incident fix (the ride treating another book's position as its
own, then stripping that book's protective bracket on the way out).

Run with:  python3 test_book_attribution.py

NO NETWORK. Everything that would normally touch BloFin, Supabase, Telegram
or ntfy is replaced with an in-memory fake:
  - FakePrivate stands in for BlofinDemoPrivate. It never makes an HTTP
    call; it just returns whatever the test programmed and records every
    order/cancel/bracket call so a test can assert "zero orders placed".
  - FakeLiveFeed stands in for the live market-data feed.
  - notify / log_event / save_state are monkeypatched to no-ops in every
    module that imported them (step5_paper_trade, tactical, shorts_lab) so
    a test run never pings Wallace's phone, appends to the real
    trades_log.jsonl, or writes to Supabase/bot_state.json.
  - time.sleep is monkeypatched to a no-op in tactical.py and shorts_lab.py
    so the hardened _ensure_bracket's real 4-second flaky-read wait doesn't
    make the test suite slow.

THE TEST THAT MATTERS MOST: test_a_incident_replay(). It reproduces the
exact 2026-07-23 state (a shorts-lab short recorded, the ride flat, the
champion signal flat) and asserts decide_and_trade places ZERO orders and
cancels NOTHING. On the pre-fix code path — current = raw
net_position_contracts() treated as the ride's own position — this exact
scenario made the ride buy the lab's short back in clips and strip its
bracket. It cannot happen anymore because decide_and_trade now only ever
acts on book_ledger.attributed_position(net, state, "ride").
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

import shorts_lab
import step5_paper_trade as s5
import tactical
from book_ledger import (attributed_position, recorded_book_positions,
                         unexplained_position)

SYMBOL = "BTC-USDT"


# ---------------------------------------------------------------------------
# Fakes — no network, ever.
# ---------------------------------------------------------------------------

class FakePrivate:
    """Stands in for BlofinDemoPrivate. Records every order/cancel/bracket
    call so tests can assert exactly what did (or, more importantly for the
    incident test, did NOT) happen. `net` is a fixed net position unless a
    test wants it to change mid-call (none of ours need that)."""

    def __init__(self, net: float = 0.0, tpsl_reads: list | None = None,
                pending_tpsl_default: list | None = None,
                fills: list | None = None):
        self.net = net
        self.orders: list[dict] = []          # every market/post-only order
        self.cancels: list[dict] = []          # every cancel_order/cancel_tpsl
        self.tpsl_placed: list[dict] = []      # every place_tpsl call
        self.pending_tpsl_calls = 0
        # a queue of canned responses consumed one-per-call by pending_tpsl;
        # once exhausted, falls back to pending_tpsl_default (or [])
        self._tpsl_queue = list(tpsl_reads) if tpsl_reads else []
        self._tpsl_default = pending_tpsl_default if pending_tpsl_default is not None else []
        self._fills = fills if fills is not None else []
        self._tpsl_counter = 0

    # -- account/position ---------------------------------------------------
    def net_position_contracts(self, symbol):
        return self.net

    def positions(self, symbol=None):
        return []

    def futures_balance(self):
        return {"balance": 1000.0, "available": 1000.0}

    def set_leverage(self, symbol, leverage=3, margin_mode="cross"):
        pass

    def ensure_leverage(self, symbol, leverage, margin_mode="cross"):
        return True

    # -- orders ---------------------------------------------------------
    def post_only_order(self, symbol, side, contracts, price, reduce_only=False):
        oid = f"post{len(self.orders) + 1}"
        self.orders.append({"kind": "post_only", "symbol": symbol,
                            "side": side, "contracts": contracts,
                            "price": price, "reduce_only": reduce_only,
                            "id": oid})
        return oid

    def market_order(self, symbol, side, contracts, reduce_only=False,
                     margin_mode="cross"):
        oid = f"mkt{len(self.orders) + 1}"
        self.orders.append({"kind": "market", "symbol": symbol, "side": side,
                            "contracts": contracts, "reduce_only": reduce_only,
                            "id": oid})
        return oid

    def pending_orders(self, symbol):
        return []          # nothing resting — maker fills "instantly" in tests

    def cancel_order(self, symbol, order_id):
        self.cancels.append({"kind": "order", "symbol": symbol, "id": order_id})

    # -- brackets -------------------------------------------------------
    def place_tpsl(self, symbol, position_side_close, contracts, tp_price,
                   sl_price, margin_mode="cross"):
        self._tpsl_counter += 1
        tid = f"tpsl{self._tpsl_counter}"
        self.tpsl_placed.append({"symbol": symbol, "side": position_side_close,
                                 "contracts": contracts, "tp": tp_price,
                                 "sl": sl_price, "id": tid})
        return tid

    def pending_tpsl(self, symbol):
        self.pending_tpsl_calls += 1
        if self._tpsl_queue:
            return self._tpsl_queue.pop(0)
        return self._tpsl_default

    def cancel_tpsl(self, symbol, tpsl_id):
        self.cancels.append({"kind": "tpsl", "symbol": symbol, "id": tpsl_id})

    def fills(self, symbol, order_id=None):
        return self._fills


class FakeLiveFeed:
    """A minimal candle/ticker source. Signal functions are monkeypatched
    directly in the tests that need a specific desired direction, so the
    actual candle values here are just placeholders — they only need to be
    shaped correctly (a 'close' column, a 'timestamp' column)."""

    def __init__(self, last_close: float = 65000.0):
        self.last_close = last_close

    def get_candles(self, symbol, bar, n):
        return pd.DataFrame({
            "timestamp": [pd.Timestamp("2026-07-23 12:00:00", tz="UTC")],
            "open": [self.last_close], "high": [self.last_close],
            "low": [self.last_close], "close": [self.last_close],
        })

    def get_ticker(self, symbol):
        class _T:
            last = self.last_close
            bid = self.last_close
            ask = self.last_close
        return _T()

    def _get(self, path, params=None):
        return [{"fundingRate": "0.0"}]


def make_state(**books) -> dict:
    """A bare bot state dict. Pass open_trade dicts by book keyword, e.g.
    make_state(ride={...}, lab={...})."""
    state = {"virtual_equity": 1000.0, "goal": 2000.0, "open_trade": None,
             "tactical": {"open_trade": None},
             "shorts_lab": {"open_trade": None}}
    if "ride" in books:
        state["open_trade"] = books["ride"]
    if "tact" in books:
        state["tactical"]["open_trade"] = books["tact"]
    if "lab" in books:
        state["shorts_lab"]["open_trade"] = books["lab"]
    return state


def ride_trade(contracts, entry=65000.0, tpsl_id=None):
    return {"direction": 1, "contracts": contracts, "entry_price": entry,
            "entry_fee_bps": 6.0, "entry_time": s5.now_utc(),
            "tp_price": None, "sl_price": entry * 0.92,
            "tp_order_id": None, "tpsl_id": tpsl_id}


def lab_trade(contracts, entry=65000.0, trigger="forensic_short",
             tpsl_id=None, entry_time=None):
    return {"trigger": trigger, "ctx": {}, "direction": -1,
            "contracts": contracts, "entry_price": entry,
            "entry_fee_bps": 6.0, "entry_time": entry_time or s5.now_utc(),
            "tp_price": entry * 0.95, "sl_price": entry * 1.017,
            "tp_order_id": None, "tpsl_id": tpsl_id, "max_hold_h": 48}


# ---------------------------------------------------------------------------
# Neutralize every side effect that would otherwise touch the network or
# real local files. Do this once, at import time, for every module that
# bound its own reference to these names.
# ---------------------------------------------------------------------------

def _noop_notify(title, message):
    pass


def _noop_log_event(event):
    pass


def _noop_save_state(state):
    pass


for _mod in (s5, tactical, shorts_lab):
    _mod.notify = _noop_notify
    _mod.log_event = _noop_log_event
    _mod.save_state = _noop_save_state

s5.CLOUD_STATE = False        # belt-and-suspenders: never let a stray path
                              # through load_state()/save_state() reach
                              # Supabase even if a future edit re-imports.

tactical.time.sleep = lambda *_a, **_kw: None
shorts_lab.time.sleep = lambda *_a, **_kw: None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_a_incident_replay():
    """THE INCIDENT, replayed exactly: shorts lab holds -69.6 ct (recorded),
    the ride has no position, the champion signal is flat (desired 0).
    decide_and_trade must place ZERO orders and cancel NOTHING — the net
    -69.6 ct on the exchange belongs entirely to the lab, and the ride's
    attributed slice is 0, which already matches what it wants."""
    state = make_state(lab=lab_trade(69.6))
    private = FakePrivate(net=-69.6)
    live_feed = FakeLiveFeed()

    s5.load_state = lambda: state              # inject our crafted state
    s5.vol_filtered_ma = lambda *a, **kw: pd.Series([0])   # champion: flat

    s5.decide_and_trade(private, live_feed, SYMBOL)

    assert private.orders == [], f"expected zero orders, got {private.orders}"
    assert private.cancels == [], f"expected zero cancels, got {private.cancels}"
    assert state["shorts_lab"]["open_trade"] is not None, \
        "the lab's own record must be untouched"
    assert state["shorts_lab"]["open_trade"]["contracts"] == 69.6


def test_b_attribution_math():
    """Ride long 45 ct + lab short -69.6 ct recorded, net -24.6 ->
    attributed ride = +45, attributed lab = -69.6, unexplained = 0. Also
    sanity-checks recorded_book_positions() and the tact book directly."""
    state = make_state(ride=ride_trade(45.0), lab=lab_trade(69.6))
    net = -24.6

    recorded = recorded_book_positions(state)
    assert recorded["ride"] == 45.0
    assert recorded["lab"] == -69.6
    assert recorded["tact"] == 0.0
    assert recorded["apprentice"] == 0.0

    assert abs(attributed_position(net, state, "ride") - 45.0) < 1e-9
    assert abs(attributed_position(net, state, "lab") - (-69.6)) < 1e-9
    assert abs(unexplained_position(net, state) - 0.0) < 1e-9

    # a tact position layered on top shouldn't confuse the ride's slice
    state2 = make_state(ride=ride_trade(45.0), tact=ride_trade(10.0),
                        lab=lab_trade(69.6))
    net2 = -14.6   # 45 + 10 - 69.6
    assert abs(attributed_position(net2, state2, "ride") - 45.0) < 1e-9
    assert abs(attributed_position(net2, state2, "tact") - 10.0) < 1e-9
    assert abs(attributed_position(net2, state2, "lab") - (-69.6)) < 1e-9
    assert abs(unexplained_position(net2, state2) - 0.0) < 1e-9


def test_c_lab_bracket_fires_ride_untouched():
    """Lab's bracket fires while the ride holds 45 long: net goes from
    -24.6 (45 ride - 69.6 lab) to +45 (the lab's whole short bought back).
    The lab's reconcile must book its own exit; the ride's record must be
    completely untouched."""
    ride = ride_trade(45.0)
    lab = lab_trade(69.6, entry=65000.0)
    state = make_state(ride=ride, lab=lab)
    # bracket bought back at 63000 (below entry -> TP hit for a short)
    private = FakePrivate(net=45.0, fills=[{"fillPrice": "63000"}])
    live_feed = FakeLiveFeed()

    # force the champion gate to read LONG so run_lab stands down cleanly
    # right after reconciling, without needing breakdown/funding data.
    shorts_lab.vol_gated_ma = lambda *a, **kw: pd.Series([1])

    result = shorts_lab.run_lab(private, live_feed, live_feed, state)

    assert state["shorts_lab"]["open_trade"] is None, \
        "the lab's exit must be booked"
    assert state["open_trade"] is ride, "the ride's record must be untouched"
    assert state["open_trade"]["contracts"] == 45.0
    assert result["action"] == "stand_down"


def test_d_unexplained_vs_recorded_short():
    """An unclaimed short (net -10, no book records it anywhere) makes the
    lab adopt it. The SAME net, but fully explained by the lab's own
    recorded short, must NOT re-trigger adoption."""
    # -- case 1: nobody claims it -> adopt --------------------------------
    state1 = make_state()
    private1 = FakePrivate(net=-10.0)
    live_feed = FakeLiveFeed()
    shorts_lab.vol_gated_ma = lambda *a, **kw: pd.Series([1])  # stand down
                                                               # right after
    shorts_lab.run_lab(private1, live_feed, live_feed, state1)
    assert state1["shorts_lab"]["open_trade"] is not None, \
        "an unclaimed short must be adopted"
    assert abs(state1["shorts_lab"]["open_trade"]["contracts"] - 10.0) < 1e-9
    assert state1["shorts_lab"]["open_trade"]["trigger"] == "adopted"

    # -- case 2: the lab's own record already explains all of net --------
    recorded_lab = lab_trade(10.0, trigger="forensic_short")
    state2 = make_state(lab=recorded_lab)
    private2 = FakePrivate(net=-10.0)
    shorts_lab.run_lab(private2, live_feed, live_feed, state2)
    assert state2["shorts_lab"]["open_trade"] is recorded_lab, \
        "adoption must NOT fire when the net is already fully explained"
    assert state2["shorts_lab"]["open_trade"]["trigger"] == "forensic_short", \
        "the trigger must not have been overwritten to 'adopted'"


def test_e_ensure_bracket_flaky_reads():
    """The sandbox's BloFin reads are flaky. First read empty, second read
    returns a bracket -> the first read was noise, do NOT re-arm. Both
    reads empty AND the position genuinely exists -> re-arm exactly once."""
    t1 = lab_trade(10.0)
    # first call: [], second call: a real bracket present
    private1 = FakePrivate(net=-10.0,
                           tpsl_reads=[[], [{"tpslId": "existing-1"}]])
    shorts_lab._ensure_bracket(private1, SYMBOL, {}, t1)
    assert private1.tpsl_placed == [], \
        "a flaky first empty read must not cause a re-arm"
    assert private1.pending_tpsl_calls == 2

    t2 = lab_trade(10.0)
    # both reads empty, position still open -> genuine re-arm
    private2 = FakePrivate(net=-10.0, tpsl_reads=[[], []])
    shorts_lab._ensure_bracket(private2, SYMBOL, {}, t2)
    assert len(private2.tpsl_placed) == 1, \
        "two independently-empty reads with the position still open must re-arm once"
    assert t2["tpsl_id"] == private2.tpsl_placed[0]["id"]

    # same two cases for tactical.py's copy (long-side variant)
    t3 = ride_trade(10.0)
    t3["sl_price"] = 60000.0
    private3 = FakePrivate(net=10.0, tpsl_reads=[[], [{"tpslId": "existing-2"}]])
    tactical._ensure_bracket(private3, SYMBOL, {}, t3)
    assert private3.tpsl_placed == []

    t4 = ride_trade(10.0)
    t4["sl_price"] = 60000.0
    private4 = FakePrivate(net=10.0, tpsl_reads=[[], []])
    tactical._ensure_bracket(private4, SYMBOL, {}, t4)
    assert len(private4.tpsl_placed) == 1

    # position is ALSO gone (net ~0) on both empty reads -> must NOT re-arm
    # (nothing to protect; reconcile handles the exit, never act on a
    # position that no longer exists)
    t5 = lab_trade(10.0)
    private5 = FakePrivate(net=0.0, tpsl_reads=[[], []])
    shorts_lab._ensure_bracket(private5, SYMBOL, {}, t5)
    assert private5.tpsl_placed == [], \
        "must not re-arm a bracket for a position that no longer exists"


def test_f_flaky_read_exception_never_acts():
    """If the read itself raises (an HTML edge-throttle response, etc.),
    _ensure_bracket must do nothing — never treat a failed read as 'missing
    bracket, re-arm'."""
    class ExplodingPrivate(FakePrivate):
        def pending_tpsl(self, symbol):
            raise RuntimeError("Got an HTML page (edge throttle). Try again.")

    t = lab_trade(10.0)
    private = ExplodingPrivate(net=-10.0)
    shorts_lab._ensure_bracket(private, SYMBOL, {}, t)
    assert private.tpsl_placed == [], \
        "a read exception must never lead to a re-arm"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_a_incident_replay,
        test_b_attribution_math,
        test_c_lab_bracket_fires_ride_untouched,
        test_d_unexplained_vs_recorded_short,
        test_e_ensure_bracket_flaky_reads,
        test_f_flaky_read_exception_never_acts,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("BOOK ATTRIBUTION TEST SUMMARY")
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
