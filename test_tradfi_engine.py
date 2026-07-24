"""
test_tradfi_engine.py — offline tests for tradfi_engine.py. NO NETWORK.

Follows this codebase's own established convention (see test_daily_pick.py):
module-level functions are monkeypatched directly (te.notify = ..., etc.)
rather than using a mocking library; datetime.now() is frozen with a
_FrozenDatetime subclass so idempotency/hold-time math is deterministic.

yfinance itself is never imported by these tests — tradfi_engine._fetch_1h
and ._fetch_1d (the only two functions that ever call `import yfinance`,
and only inside their own bodies) are monkeypatched wholesale, so no real
network call or yfinance install is exercised at all.

Seven intents (per the build brief):
  a) market-hours gate per symbol (GOLD/OIL futures vs SPX/SPY equity
     hours, weekends, the daily CME maintenance break)
  b) slot idempotency — no re-pick within a slot, fresh pick on the next
     even-UTC-2h slot
  c) scoring reuse (score_instrument, imported from daily_pick) produces a
     ranked pick — verified against score_instrument's OWN output on the
     identical candles, not just a hand-picked expectation
  d) paper fill/exit math incl. stop-first ties + fees, hand-verified
  e) ledger isolation — every OTHER book's shared state key is byte-for-
     byte untouched by a full entry+exit cycle
  f) calm-gate A-only mirror — CONVICTION_FLOOR (imported from daily_pick,
     = 40) only gates a calm-regime candidate; a normal-regime candidate
     under the floor still gets taken (owner's "no gambling in quiet
     tape, take-best everywhere else" rule)
  g) dry mode makes zero writes — no state mutation, no notify/log_event/
     save_state call, across both an entry and an exit scenario

Run with:  python3 test_tradfi_engine.py
"""

from __future__ import annotations

import copy
import sys
import traceback
from datetime import datetime, timedelta, timezone

import pandas as pd

import tradfi_engine as te
from daily_pick import CONVICTION_FLOOR, score_instrument

# ---------------------------------------------------------------------------
# freeze / neutralize — same technique as test_daily_pick.py's _FrozenDatetime
# ---------------------------------------------------------------------------

class _FrozenDatetime(datetime):
    _frozen: datetime | None = None

    @classmethod
    def now(cls, tz=None):
        return cls._frozen


_now_box = {"t": None}


def _fake_now_utc() -> str:
    return f"{_now_box['t']:%Y-%m-%d %H:%M:%S} UTC"


def _freeze(iso_dt: str):
    te.datetime = _FrozenDatetime
    frozen = datetime.strptime(iso_dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    _FrozenDatetime._frozen = frozen
    _now_box["t"] = frozen


def _unfreeze():
    te.datetime = datetime
    _now_box["t"] = None


notify_calls: list[tuple] = []
log_event_calls: list[dict] = []
save_state_calls: list[dict] = []


def _fake_notify(title, message):
    notify_calls.append((title, message))


def _fake_log_event(event):
    log_event_calls.append(event)


def _fake_save_state(state):
    save_state_calls.append(state)


def _reset_call_logs():
    notify_calls.clear()
    log_event_calls.clear()
    save_state_calls.clear()


te.notify = _fake_notify
te.log_event = _fake_log_event
te.save_state = _fake_save_state
te.now_utc = _fake_now_utc


# ---------------------------------------------------------------------------
# candle builders (same shape as test_daily_pick.py's _mk convention)
# ---------------------------------------------------------------------------

def _mk(closes, opens=None, highs=None, lows=None, volumes=None,
       start="2026-01-01", freq="1h"):
    n = len(closes)
    opens = opens if opens is not None else closes
    highs = highs if highs is not None else [max(o, c) for o, c in zip(opens, closes)]
    lows = lows if lows is not None else [min(o, c) for o, c in zip(opens, closes)]
    volumes = volumes if volumes is not None else [1.0] * n
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"timestamp": ts, "open": opens, "high": highs,
                         "low": lows, "close": closes, "volume": volumes})


def _flat_1d(n=55, price=100.0):
    return _mk([price] * n, freq="1d")


def _flat_1h(n=3, price=50.0):
    return _mk([price] * n, freq="1h")


def _breakout_long_candles():
    """The exact recipe test_daily_pick.py's test_a uses for a clean,
    hand-computable LONG pick: 55 flat 1d bars then a spike day (breakout
    THROUGH the 55-bar high, +20) with a matching lagging-trend alignment
    bonus (+5) — long_score=25.0, short_score=0.0, conviction=25.0,
    direction='long'. 1h candles too short (3 bars) for any 1h component
    to fire, isolating the fixture to exactly those two components."""
    c1d = _flat_1d(55, 100.0)
    spike = _mk([130.0], freq="1d", start=c1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d = pd.concat([c1d, spike], ignore_index=True)
    c1h = _flat_1h(3, 50.0)
    return c1h, c1d


def make_state(**overrides) -> dict:
    """A state dict carrying every OTHER book's shared keys, so isolation
    tests have real neighbors to check untouched."""
    state = {
        "virtual_equity": 12345.67,
        "open_trade": {"symbol": "BTC-USDT", "direction": 1, "contracts": 5.0},
        "tactical": {"open_trade": None},
        "shorts_lab": {"open_trade": None},
        "apprentice": {"open_trade": None},
        "newsdesk": {"open_trade": None, "pending": False},
        "diver": {"open_trade": None},
        "daily_pick": {"open_trades": [], "last_slot_ts": None},
    }
    state.update(overrides)
    return state


_SHARED_KEYS = ["virtual_equity", "open_trade", "tactical", "shorts_lab",
               "apprentice", "newsdesk", "diver", "daily_pick"]


def _fetch_stub(map_1h, map_1d):
    def fake_1h(symbol):
        return map_1h.get(symbol)

    def fake_1d(symbol):
        return map_1d.get(symbol)
    return fake_1h, fake_1d


# ===========================================================================
# (a) market-hours gate per symbol
# ===========================================================================

def test_a_market_hours_gate():
    UTC = timezone.utc
    # -- SPX (SPY): weekday 13:30-20:00 UTC only ---------------------------
    mon_open = datetime(2026, 7, 27, 15, 0, tzinfo=UTC)          # Monday, RTH
    mon_before = datetime(2026, 7, 27, 13, 0, tzinfo=UTC)        # before open
    mon_after = datetime(2026, 7, 27, 20, 30, tzinfo=UTC)        # after close
    sat = datetime(2026, 8, 1, 15, 0, tzinfo=UTC)                # Saturday
    sun = datetime(2026, 8, 2, 15, 0, tzinfo=UTC)                # Sunday
    assert te.is_market_open(te.SPX, mon_open) is True
    assert te.is_market_open(te.SPX, mon_before) is False
    assert te.is_market_open(te.SPX, mon_after) is False
    assert te.is_market_open(te.SPX, sat) is False
    assert te.is_market_open(te.SPX, sun) is False

    # -- GOLD / OIL (futures): ~23h Sun 22:00 UTC -> Fri 21:00 UTC, daily
    #    21:00-22:00 UTC maintenance break Mon-Thu, closed Saturday --------
    for sym in (te.GOLD, te.OIL):
        assert te.is_market_open(sym, sat) is False, sym
        sun_before_open = datetime(2026, 8, 2, 21, 0, tzinfo=UTC)
        sun_after_open = datetime(2026, 8, 2, 22, 30, tzinfo=UTC)
        assert te.is_market_open(sym, sun_before_open) is False, sym
        assert te.is_market_open(sym, sun_after_open) is True, sym
        thu_break = datetime(2026, 7, 30, 21, 30, tzinfo=UTC)     # Thursday
        thu_normal = datetime(2026, 7, 30, 15, 0, tzinfo=UTC)
        assert te.is_market_open(sym, thu_break) is False, sym
        assert te.is_market_open(sym, thu_normal) is True, sym
        fri_before_close = datetime(2026, 7, 31, 20, 0, tzinfo=UTC)
        fri_after_close = datetime(2026, 7, 31, 21, 30, tzinfo=UTC)
        assert te.is_market_open(sym, fri_before_close) is True, sym
        assert te.is_market_open(sym, fri_after_close) is False, sym

    print("[PASS] test_a_market_hours_gate")


# ===========================================================================
# (b) slot idempotency
# ===========================================================================

def test_b_slot_idempotency():
    te._fetch_1h = lambda symbol: None       # every symbol fetch-fails ->
    te._fetch_1d = lambda symbol: None       # nothing ever scores -> no_pick
    te.is_market_open = lambda symbol, now: True
    _reset_call_logs()
    state = make_state()

    try:
        _freeze("2026-07-27 10:15:00")
        r1 = te.run_tradfi_engine(state, dry=False)
        assert r1["due"] is True, r1
        assert r1["slot_ts"] == "2026-07-27T10:00 UTC", r1
        assert state["tradfi_engine"]["last_slot_ts"] == "2026-07-27T10:00 UTC"
        assert r1["entry"] == {"action": "no_pick", "scored": 0}, r1

        # same slot, later in the hour -> due False, no re-pick
        _freeze("2026-07-27 11:45:00")
        r2 = te.run_tradfi_engine(state, dry=False)
        assert r2["due"] is False, r2
        assert r2["entry"] is None, r2
        assert state["tradfi_engine"]["last_slot_ts"] == "2026-07-27T10:00 UTC"

        # next even-UTC-2h slot -> due True again
        _freeze("2026-07-27 12:05:00")
        r3 = te.run_tradfi_engine(state, dry=False)
        assert r3["due"] is True, r3
        assert r3["slot_ts"] == "2026-07-27T12:00 UTC", r3
        assert state["tradfi_engine"]["last_slot_ts"] == "2026-07-27T12:00 UTC"
    finally:
        _unfreeze()

    print("[PASS] test_b_slot_idempotency")


# ===========================================================================
# (c) scoring reuse produces a ranked pick
# ===========================================================================

def test_c_scoring_reuse_ranked_pick():
    c1h, c1d = _breakout_long_candles()
    expected = score_instrument(c1h, c1d, funding_bps=None)
    assert expected["conviction"] == 25.0 and expected["direction"] == "long", expected

    fake_1h, fake_1d = _fetch_stub(
        {te.GOLD: c1h}, {te.GOLD: c1d})
    te._fetch_1h = fake_1h
    te._fetch_1d = fake_1d
    te.is_market_open = lambda symbol, now: symbol == te.GOLD   # only GOLD "open"

    rec = te._score_symbol(te.GOLD)
    assert rec is not None
    assert rec["conviction"] == expected["conviction"], rec
    assert rec["direction"] == expected["direction"], rec
    assert rec["components"] == expected["components"], rec

    # OIL/SPX have no fixture installed -> _fetch_1h/_1d return None for
    # them -> _score_symbol degrades to None -> excluded from ranking.
    assert te._score_symbol(te.OIL) is None
    assert te._score_symbol(te.SPX) is None

    # full cycle, dry preview: the only scored/open symbol should be picked
    te.notify = _fake_notify
    te.log_event = _fake_log_event
    te.save_state = _fake_save_state
    _reset_call_logs()
    state = make_state()
    try:
        _freeze("2026-07-27 10:15:00")
        r = te.run_tradfi_engine(state, dry=True)
    finally:
        _unfreeze()
    assert r["entry"] == {"action": "would_enter", "symbol": te.GOLD,
                          "direction": "long", "conviction": 25.0}, r["entry"]
    # dry mode may lazily materialize the engine's OWN fresh/empty state
    # shell (state.setdefault(...) — same contract as
    # daily_pick.run_daily_pick's own dry mode, which does the identical
    # setdefault unconditionally), but must make NO further mutation: no
    # slot stamped, no trade opened, ledger untouched.
    eng = state["tradfi_engine"]
    assert eng["last_slot_ts"] is None, eng
    assert eng["open_trades"] == [], eng
    assert eng["ledger_equity"] == te.STARTING_EQUITY, eng

    print("[PASS] test_c_scoring_reuse_ranked_pick")


# ===========================================================================
# (d) paper fill/exit math incl. stop-first ties + fees, hand-verified
# ===========================================================================

def test_d_paper_fill_exit_math():
    te.is_market_open = lambda symbol, now: True
    _reset_call_logs()
    eng = te._fresh_engine()
    eng["ledger_equity"] = 2000.0
    cand = {"symbol": te.GOLD, "direction": "long", "conviction": 60.0,
           "components": [{"name": "breakout", "long": 20.0, "short": 0.0}],
           "atr_pct_1h": 1.0, "last_close": 2000.0}

    entry_now = datetime(2026, 7, 27, 10, 0, tzinfo=timezone.utc)
    _now_box["t"] = entry_now
    state = make_state()
    result = te._do_entry(state, eng, cand, entry_now)

    # hand math: stop_pct = min(1.0*1.0, 1.0) = 1.0%; target_pct = 1.5%
    # lev = min(20, max(4, 85/1.0)) = 20 (GOLD, no SPY cap)
    # notional = 0.02*2000 / (1.0/100) = 40 / 0.01 = 4000.0
    # shares = 4000.0 / 2000.0 = 2.0
    # stop_price = 2000*(1-0.01) = 1980.0 ; target_price = 2000*1.015 = 2030.0
    trade = eng["open_trades"][0]
    assert trade["stop_pct"] == 1.0 and trade["target_pct"] == 1.5, trade
    assert trade["leverage"] == 20.0, trade
    assert abs(trade["notional"] - 4000.0) < 1e-9, trade
    assert abs(trade["shares"] - 2.0) < 1e-9, trade
    assert abs(trade["stop_price"] - 1980.0) < 1e-6, trade
    assert abs(trade["target_price"] - 2030.0) < 1e-6, trade
    assert trade["fee_bps"] == te.FEE_BPS_FUTURES == 2.0, trade
    assert result["action"] == "entered" and result["symbol"] == te.GOLD

    # -- stop-first-on-tie: one bar's range spans BOTH stop and target ----
    tie_bar = (2050.0, 1970.0, 2010.0)   # high, low, close
    hit = te._check_exit(trade, *tie_bar, entry_now + timedelta(hours=1))
    assert hit == (1980.0, "stop"), hit

    # mirror for a SHORT: stop above entry, target below; a bar spanning
    # both must still book the stop.
    short_trade = dict(trade)
    short_trade["direction"] = -1
    short_trade["stop_price"] = 2020.0
    short_trade["target_price"] = 1970.0
    hit_short = te._check_exit(short_trade, 2050.0, 1960.0, 2000.0,
                               entry_now + timedelta(hours=1))
    assert hit_short == (2020.0, "stop"), hit_short

    # -- exit at target, hand-verified PnL ---------------------------------
    exit_now = entry_now + timedelta(hours=2)
    realized = te._book_exit(state, eng, trade, 2030.0, "target", exit_now)
    # gross = 1*(2030-2000)*2.0 = 60.0
    # fees = (2000*2.0 + 2030*2.0) * 2.0 / 10000 = 8060*2/10000 = 1.612
    # realized = 60.0 - 1.612 = 58.388 -> round 58.39
    assert realized == 58.39, realized
    assert eng["ledger_equity"] == round(2000.0 + 58.39, 2), eng["ledger_equity"]
    assert eng["open_trades"] == [], eng["open_trades"]
    assert len(eng["daybook"]) == 1, eng["daybook"]
    rec = eng["daybook"][0]
    assert rec["symbol"] == te.GOLD and rec["dir"] == "long"
    assert rec["outcome_pnl"] == 58.39, rec
    assert rec["hold_min"] == 120.0, rec

    # -- a losing exit stamps the stop-out cooldown -------------------------
    eng2 = te._fresh_engine()
    eng2["ledger_equity"] = 2000.0
    _now_box["t"] = entry_now
    t2 = te._do_entry(state, eng2, cand, entry_now)
    trade2 = eng2["open_trades"][0]
    loss_realized = te._book_exit(state, eng2, trade2, trade2["stop_price"],
                                  "stop", entry_now + timedelta(hours=1))
    assert loss_realized < 0, loss_realized
    key = f"{te.GOLD}:long"
    assert key in eng2["last_stopouts"], eng2["last_stopouts"]
    assert eng2["last_stopouts"][key]["conviction"] == 60.0

    print("[PASS] test_d_paper_fill_exit_math")


# ===========================================================================
# (e) ledger isolation — shared state keys untouched
# ===========================================================================

def test_e_ledger_isolation():
    before_state = make_state()
    before_snapshot = {k: copy.deepcopy(before_state[k]) for k in _SHARED_KEYS}
    state = make_state()

    # force GOLD to be picked every due slot; nothing else ever scores
    strong_cand = {"symbol": te.GOLD, "conviction": 70.0, "direction": "long",
                  "long_score": 70.0, "short_score": 0.0,
                  "components": [{"name": "breakout", "long": 20.0, "short": 0.0}],
                  "last_close": 2000.0, "atr_pct_1h": 1.0, "regime": "normal"}

    def fake_score(symbol):
        return strong_cand if symbol == te.GOLD else None

    te._score_symbol = fake_score
    te.is_market_open = lambda symbol, now: True
    te.notify = _fake_notify
    te.log_event = _fake_log_event
    te.save_state = _fake_save_state
    _reset_call_logs()

    try:
        _freeze("2026-07-27 10:15:00")
        r1 = te.run_tradfi_engine(state, dry=False)
        assert r1["entry"]["action"] == "entered", r1
        assert r1["entry"]["symbol"] == te.GOLD, r1

        # force a time exit: jump the frozen clock 7h ahead (past
        # MAX_HOLD_H=6) and hand it a flat bar that never touches
        # stop/target, so the ONLY exit trigger available is the clock.
        trade = state["tradfi_engine"]["open_trades"][0]
        flat_bar = _mk([trade["entry_price"]], freq="1h")
        te._fetch_1h = lambda symbol: flat_bar if symbol == te.GOLD else None
        te._score_symbol = lambda symbol: None   # nothing re-enters after the exit
        _freeze("2026-07-27 17:20:00")
        r2 = te.run_tradfi_engine(state, dry=False)
        assert any(e["action"] == "exit" and e["reason"] == "time"
                  for e in r2["exits"]), r2["exits"]
        assert state["tradfi_engine"]["open_trades"] == []
    finally:
        _unfreeze()

    after_snapshot = {k: copy.deepcopy(state[k]) for k in _SHARED_KEYS}
    assert after_snapshot == before_snapshot, \
        "a shared book's state key was mutated by the tradfi engine"
    assert "tradfi_engine" in state
    assert state["tradfi_engine"]["ledger_equity"] != te.STARTING_EQUITY, \
        "the engine's own ledger should have moved from its starting value"

    print("[PASS] test_e_ledger_isolation")


# ===========================================================================
# (f) calm-gate A-only mirror
# ===========================================================================

def test_f_calm_gate_a_only():
    te.is_market_open = lambda symbol, now: True
    te.notify = _fake_notify
    te.log_event = _fake_log_event
    te.save_state = _fake_save_state

    calm_low = {"symbol": te.GOLD, "conviction": 30.0, "direction": "long",
               "components": [], "last_close": 2000.0, "atr_pct_1h": 0.3,
               "regime": "calm"}
    assert 30.0 < CONVICTION_FLOOR

    # -- calm regime, below floor: must be SKIPPED (no_pick) ---------------
    te._score_symbol = lambda symbol: calm_low if symbol == te.GOLD else None
    _reset_call_logs()
    state = make_state()
    try:
        _freeze("2026-07-27 10:15:00")
        r = te.run_tradfi_engine(state, dry=False)
    finally:
        _unfreeze()
    assert r["entry"] == {"action": "no_pick", "scored": 1}, r["entry"]

    # -- calm regime, AT the floor: must be TAKEN ----------------------------
    calm_at_floor = dict(calm_low, conviction=CONVICTION_FLOOR)
    te._score_symbol = lambda symbol: calm_at_floor if symbol == te.GOLD else None
    state2 = make_state()
    try:
        _freeze("2026-07-27 10:15:00")
        r2 = te.run_tradfi_engine(state2, dry=False)
    finally:
        _unfreeze()
    assert r2["entry"]["action"] == "entered", r2["entry"]

    # -- NORMAL regime, well below the floor: must STILL be TAKEN — the
    #    floor is a calm-only gate, "no other conviction-floor skip" -------
    normal_low = {"symbol": te.OIL, "conviction": 10.0, "direction": "short",
                 "components": [], "last_close": 70.0, "atr_pct_1h": 1.2,
                 "regime": "normal"}
    te._score_symbol = lambda symbol: normal_low if symbol == te.OIL else None
    state3 = make_state()
    try:
        _freeze("2026-07-27 10:15:00")
        r3 = te.run_tradfi_engine(state3, dry=False)
    finally:
        _unfreeze()
    assert r3["entry"]["action"] == "entered", r3["entry"]
    assert r3["entry"]["symbol"] == te.OIL, r3["entry"]

    print("[PASS] test_f_calm_gate_a_only")


# ===========================================================================
# (g) dry mode makes zero writes
# ===========================================================================

def test_g_dry_mode_zero_writes():
    te.is_market_open = lambda symbol, now: True
    te.notify = _fake_notify
    te.log_event = _fake_log_event
    te.save_state = _fake_save_state

    strong_cand = {"symbol": te.OIL, "conviction": 80.0, "direction": "short",
                  "components": [{"name": "breakout", "long": 0.0, "short": 20.0}],
                  "last_close": 70.0, "atr_pct_1h": 1.0, "regime": "normal"}
    te._score_symbol = lambda symbol: strong_cand if symbol == te.OIL else None

    # an existing open GOLD trade that WOULD stop out this cycle
    entry_time_str = "2026-07-27 08:00:00 UTC"
    existing = {"symbol": te.GOLD, "direction": 1, "entry_price": 2000.0,
               "shares": 2.0, "notional": 4000.0, "leverage": 20.0,
               "stop_pct": 1.0, "target_pct": 1.5, "stop_price": 1980.0,
               "target_price": 2030.0, "fee_bps": 2.0,
               "entry_time": entry_time_str, "conviction": 55.0,
               "components": [], "top_component": "breakout",
               "max_hold_h": te.MAX_HOLD_H}
    state = make_state()
    state["tradfi_engine"] = te._fresh_engine()
    state["tradfi_engine"]["open_trades"] = [existing]
    before = copy.deepcopy(state)

    stop_bar = _mk([1980.0], highs=[1985.0], lows=[1975.0], freq="1h")

    def fake_1h(symbol):
        return stop_bar if symbol == te.GOLD else None
    te._fetch_1h = fake_1h
    te._fetch_1d = lambda symbol: None

    _reset_call_logs()
    try:
        _freeze("2026-07-27 10:15:00")
        r = te.run_tradfi_engine(state, dry=True)
    finally:
        _unfreeze()

    assert any(e["action"] == "would_exit_stop" for e in r["exits"]), r["exits"]
    assert r["entry"] == {"action": "would_enter", "symbol": te.OIL,
                          "direction": "short", "conviction": 80.0}, r["entry"]
    assert state == before, "dry mode mutated state"
    assert notify_calls == [] and log_event_calls == [] and save_state_calls == [], \
        (notify_calls, log_event_calls, save_state_calls)

    print("[PASS] test_g_dry_mode_zero_writes")


# ===========================================================================
# module hygiene — no order-placement capability exists anywhere in here
# ===========================================================================

def test_h_no_order_capability_in_module():
    import inspect
    src = inspect.getsource(te)
    # substrings that would indicate a real order-placement/exchange-client
    # capability leaked in (as opposed to plain-English docstring mentions
    # of daily_pick's own parameter names, which this deliberately allows)
    forbidden = ["execute_market_clips", "post_only_order", "market_order(",
                "place_tpsl", "ensure_leverage", "blofin_private",
                "BlofinPrivate", "import blofin", "private.net_position",
                "demo_feed.", "cancel_order", "cancel_tpsl"]
    hits = [f for f in forbidden if f in src]
    assert hits == [], f"order-placement-shaped code leaked into tradfi_engine.py: {hits}"
    # and no function anywhere in the module whose own name suggests it
    # can place/cancel/modify a real order
    order_like = [n for n in dir(te)
                 if any(w in n.lower() for w in ("place_order", "cancel_order",
                                                 "submit_order", "send_order"))]
    assert order_like == [], order_like
    print("[PASS] test_h_no_order_capability_in_module")


# ===========================================================================
# harness
# ===========================================================================

if __name__ == "__main__":
    tests = [test_a_market_hours_gate, test_b_slot_idempotency,
            test_c_scoring_reuse_ranked_pick, test_d_paper_fill_exit_math,
            test_e_ledger_isolation, test_f_calm_gate_a_only,
            test_g_dry_mode_zero_writes, test_h_no_order_capability_in_module]
    results = []
    for t in tests:
        try:
            t()
            results.append((t.__name__, True, None))
        except Exception:
            results.append((t.__name__, False, traceback.format_exc()))

    print("\n" + "=" * 72)
    print("TRADFI ENGINE TEST SUMMARY")
    print("=" * 72)
    n_pass = 0
    for name, ok, tb in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            print(tb)
        n_pass += ok
    print("-" * 72)
    print(f"  {n_pass}/{len(results)} passed")
    print("=" * 72)
    sys.exit(0 if n_pass == len(results) else 1)
