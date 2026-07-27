"""
test_bitcoin.py — offline tests for bitcoin.py (THE BITCOIN BOOK: one book,
one market, one thesis, with a memory loop that actually gates).

Run with:  python3 test_bitcoin.py

NO NETWORK. Everything that would normally touch BloFin, Supabase, Telegram
or ntfy is replaced with an in-memory fake, same discipline as
test_diver.py / test_breakout_book.py:
  - FakePrivate (imported from test_book_attribution) stands in for
    BlofinDemoPrivate — never an HTTP call, records every order/cancel/
    bracket call so a test can assert what did, and did NOT, happen.
  - FakeFeed stands in for both live_feed and demo_feed.
  - notify / log_event / save_state are monkeypatched to no-ops on BOTH
    bitcoin and step5_paper_trade, so a run can never ping Wallace's phone,
    write the real state, or reach Supabase.

NOTHING HERE WRITES THE REPO'S REAL data/ FILES. The one test that
exercises export_journal's own writer does it inside a temporary working
directory and changes back, so the live data/learnings.md is never touched.

THE SIGNAL FIXTURES ARE REAL, NOT MONKEYPATCHED. build_trend_turn_series()
is a hand-built 4h OHLC frame — a long, volatile decline followed by a
sharp rally — engineered so the REAL, imported strategy.vol_filtered_ma
(FAST=20, SLOW=100, MIN_ATR_PCT=1.5) turns from flat to long on EXACTLY the
final bar, with ATR ~2.8% of price, comfortably clearing the 1.5%-of-price
gate. build_gate_shut_series() is the identical price path with tiny wicks,
so ATR lands ~0.6% of price and the gate refuses the same trend turn. Any
edit to either fixture must re-verify those two facts before the tests
below mean anything; test (k) exists to catch exactly that drift.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import traceback

import numpy as np
import pandas as pd

import bitcoin as B
import step5_paper_trade as s5
from strategy import atr, vol_filtered_ma, vol_gated_ma
from test_book_attribution import FakePrivate

SYMBOL = B.SYMBOL


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def build_trend_turn_series(n_down: int = 260, n_up: int = 15,
                            wick: float = 0.015) -> pd.DataFrame:
    """A 4h frame whose LAST bar is a fresh flat -> long transition of the
    real vol_filtered_ma champion, with the volatility gate OPEN.

    Shape: 260 bars of noisy decline (drives SMA20 under SMA100 and keeps
    it there), then 15 bars of hard rally that crosses SMA20 back above
    SMA100 on the final bar. `wick` sets high/low as a fraction of close,
    which is what drives ATR: 0.015 gives ~2.8% of price, well over the
    1.5%-of-price gate."""
    closes = [1000.0]
    for i in range(n_down):
        closes.append(closes[-1] - 0.9 + np.sin(i / 2.0) * 3.0)
    for _ in range(n_up):
        closes.append(closes[-1] + 6.0)
    c = np.array(closes, dtype=float)
    n = len(c)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="4h",
                                   tz="UTC"),
        "open": np.r_[c[0], c[:-1]], "high": c * (1 + wick),
        "low": c * (1 - wick), "close": c, "volume": np.ones(n)})


def build_gate_shut_series() -> pd.DataFrame:
    """The identical price path with tiny wicks, so ATR falls to ~0.6% of
    price and the 1.5%-of-price volatility gate keeps the book flat."""
    return build_trend_turn_series(wick=0.001)


def build_rising_series(n: int = 400) -> pd.DataFrame:
    """A rising series WITH pullbacks — used to prove the structural floor
    ratchets UP and never back down as bars are added.

    The pullbacks matter: a strictly monotonic rise has no confirmed swing
    lows at all (a fractal low needs a bar that is the minimum of the k
    bars on BOTH sides), so the floor would sit on the fallback forever and
    the ratchet would never be exercised. The sine wobble puts real swing
    lows on the chart for the floor to climb."""
    rng = np.random.default_rng(11)
    drift = np.cumsum(np.abs(rng.normal(3.0, 1.0, n)))
    wobble = np.sin(np.arange(n) / 4.0) * 25.0
    c = 1000.0 + drift + wobble
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="4h",
                                   tz="UTC"),
        "open": np.r_[c[0], c[:-1]], "high": c * 1.01, "low": c * 0.99,
        "close": c, "volume": np.ones(n)})


class FakeFeed:
    """Stands in for both live_feed and demo_feed. get_candles ignores
    symbol/bar/n and always returns the frame it was built with."""

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.last_close = float(frame["close"].iloc[-1])

    def get_candles(self, symbol, bar, n):
        return self.frame

    def get_ticker(self, symbol):
        px = self.last_close

        class _T:
            last = px
            bid = px
            ask = px
        return _T()

    def get_instrument(self, symbol=SYMBOL):
        # BLOFIN_API_REFERENCE.md's verified BTC-USDT values.
        return {"instId": symbol, "contractValue": "0.001", "minSize": "0.1",
                "lotSize": "0.1", "tickSize": "0.1", "maxLeverage": "150"}


def make_state(open_trade=None, last_bar_ts=None, trades=None,
               rules_stood_down=None, **extra) -> dict:
    """A state shaped like the live one: every legacy book's key present
    (book attribution reads them all) plus this book's own."""
    state = {
        "virtual_equity": 1000.0, "goal": 2000.0, "lessons": [],
        "open_trade": None,                      # the ride
        "tactical": {"open_trade": None},
        "shorts_lab": {"open_trade": None},
        "apprentice": {"open_trade": None},
        "newsdesk": {"open_trade": None},
        "diver": {"open_trade": None},
        "breakout_book": {"open_trade": None},
        B.STATE_KEY: {"open_trade": open_trade, "last_bar_ts": last_bar_ts,
                      "trades": list(trades or []),
                      "realized_pnl_total": 0.0,
                      "rules_stood_down": dict(rules_stood_down or {}),
                      "stand_down_history": []},
    }
    state.update(extra)
    return state


def losing_trade(exit_time: str, reason: str = "structural_stop",
                 rule: str = "vol_gated_trend", pnl: float = -40.0) -> dict:
    return {"rule": rule, "entry_time": exit_time, "entry_price": 100.0,
            "direction": 1, "contracts": 1.0, "exit_price": 96.0,
            "pnl": pnl, "reason": reason, "exit_time": exit_time}


# ---------------------------------------------------------------------------
# neutralize every side effect, on BOTH modules
# ---------------------------------------------------------------------------

def _noop(*_a, **_kw):
    pass


B.notify = _noop
B.log_event = _noop
B.save_state = _noop
B.time.sleep = _noop
s5.notify = _noop
s5.log_event = _noop
s5.save_state = _noop

# HERMETIC MEMORY. run_bitcoin loads its journal from these module paths at
# CALL time, so pointing them at nothing makes every test below depend only
# on the state it built itself — never on whatever the repo's real
# data/ledger.csv happens to contain today. Test (l) passes real paths
# explicitly, which is where the file reading is actually exercised.
B.LEDGER_CSV = "no/such/ledger.csv"
B.LEARNINGS_MD = "no/such/learnings.md"


# ---------------------------------------------------------------------------
# (a) entry fires on the validated signal
# ---------------------------------------------------------------------------

def test_a_entry_fires_on_the_validated_signal():
    B.NEW_ENTRIES_ENABLED = True
    d = build_trend_turn_series()

    # the REAL imported champion really does turn on at the last bar, and
    # the volatility gate really is open — never monkeypatched, this is the
    # whole point of the fixture
    sig = vol_filtered_ma(d, B.FAST, B.SLOW, min_atr_pct=B.MIN_ATR_PCT).fillna(0)
    assert sig.iloc[-1] == 1.0 and sig.iloc[-2] != 1.0, \
        "fixture must be a FRESH flat->long transition on the final bar"
    atr_pct = float((atr(d, 14) / d["close"] * 100).iloc[-1])
    assert atr_pct >= B.MIN_ATR_PCT, atr_pct

    feed = FakeFeed(d)
    private = FakePrivate(net=0.0)
    state = make_state()

    r = B.run_bitcoin(private, feed, feed, state)
    assert r["action"] == "entered", r
    assert r["rule"] == "vol_gated_trend" and r["direction"] == 1

    t = state[B.STATE_KEY]["open_trade"]
    assert t is not None and t["direction"] == 1
    assert t["rule"] == "vol_gated_trend"

    # ONE atomic market order, buy side — never a resting/maker order
    assert private.orders, "expected an order"
    assert all(o["kind"] == "market" for o in private.orders), private.orders
    assert all(o["side"] == "buy" for o in private.orders)
    assert len(private.orders) == 1, "entry must be ONE atomic order"

    # the stop is real chart structure, not a swept percentage: it sits the
    # 1.5%-of-price buffer under the confirmed swing low the entry rests on
    swing = B.anchor_swing(d, len(d) - 1, float(d["close"].iloc[-1]), 1)
    assert swing is not None, "fixture should have a confirmed swing low"
    expected = round(swing * (1 - B.TRAIL_BUFFER_PCT / 100), 1)
    assert abs(t["sl_price"] - expected) < 0.15, (t["sl_price"], expected)
    assert t["sl_price"] < t["entry_price"], "a long's stop must sit below entry"

    # leverage is an OUTPUT of risk/stop-distance, inside both caps
    assert 0 < t["leverage_at_entry"] <= B.MAX_LEVERAGE, t["leverage_at_entry"]
    assert abs(t["risk_usd"] - 1000.0 * B.RISK_PCT / 100) < 1e-6

    # what the book KNEW when it fired is on the trade itself
    assert "memory_at_entry" in t and "lessons_known" in t
    assert t["n_closed_trades_known"] == 0 and t["n_lessons_known"] == 0
    assert t["entry_reason"] and "structure" in t["entry_reason"]
    assert state[B.STATE_KEY]["last_bar_ts"] == r["bar_ts"]


# ---------------------------------------------------------------------------
# (b) entry does NOT fire when the vol gate is shut
# ---------------------------------------------------------------------------

def test_b_the_volatility_gate_is_NOT_applied():
    """Round 400 removed the 'only trade when it is moving enough'
    condition. It does not skip a trade, it DELAYS one, and in a
    one-position engine a delayed entry lets a different later trade
    happen — 30% of the gated run's first-window trades and 57% of its
    middle-window trades entered on bars the ungated run could never take.
    Tested like-for-like on the same 59 trend legs, entering at the
    crossover earns +$181.61 per leg against +$45.27 for waiting, and the
    condition cost 71% of the system's money.

    This test exists so the gate cannot quietly come back."""
    B.NEW_ENTRIES_ENABLED = True
    d = build_gate_shut_series()

    # the fixture IS quiet — that is the point. The old gate would have
    # stood the bot down here; the ungated rule must not.
    atr_pct = float((atr(d, 14) / d["close"] * 100).iloc[-1])
    assert atr_pct < B.MIN_ATR_PCT, \
        f"fixture must be quiet, ATR was {atr_pct:.2f}% of price"

    gated = vol_filtered_ma(d, B.FAST, B.SLOW,
                            min_atr_pct=B.MIN_ATR_PCT).fillna(0)
    ungated = vol_filtered_ma(d, B.FAST, B.SLOW, min_atr_pct=0.0).fillna(0)
    assert gated.iloc[-1] != 1.0, "fixture precondition: old gate shuts here"
    assert ungated.iloc[-1] == 1.0, \
        "fixture precondition: the trend itself is up here"

    # the rule must follow the UNGATED signal
    sig = B.rule_vol_gated_trend(d, {})
    assert sig is not None, (
        "the volatility gate is back — the bot stood down on a quiet bar "
        "where the trend was up. See step400_gate_artifact_audit.md")
    assert sig.direction == 1

    import inspect
    src = inspect.getsource(B.rule_vol_gated_trend)
    assert "min_atr_pct=0.0" in src, (
        "the rule must call the champion signal ungated")
    assert "min_atr_pct=MIN_ATR_PCT" not in src, (
        "the gate was reintroduced")


# ---------------------------------------------------------------------------
# (c) the structural stop is placed on the exchange, and only ratchets in
#     the trade's favour
# ---------------------------------------------------------------------------

def test_c_structural_stop_is_exchange_side_and_ratchets_one_way():
    B.NEW_ENTRIES_ENABLED = True

    # -- c1: entry places a REAL exchange-side stop at the structural level
    d = build_trend_turn_series()
    feed, private, state = FakeFeed(d), FakePrivate(net=0.0), make_state()
    r = B.run_bitcoin(private, feed, feed, state)
    assert private.tpsl_placed, "protection must live on the exchange"
    br = private.tpsl_placed[-1]
    assert br["tp"] is None, "this is a ride — no take-profit, ever"
    assert br["sl"] == state[B.STATE_KEY]["open_trade"]["sl_price"]
    assert br["side"] == "sell" and br["symbol"] == SYMBOL
    assert br["client_order_id"] and B.BOOK_TAG in br["client_order_id"], \
        f"every order must carry this book's tag: {br['client_order_id']}"

    # -- c2: the floor itself never moves against the trade as bars are added
    rising = build_rising_series()
    entry_idx = 150
    entry_price = float(rising["close"].iloc[entry_idx])
    floors = [B._structural_stop(rising, entry_idx, entry_price, 1, at_idx=i)
              for i in range(entry_idx, len(rising))]
    assert all(b >= a - 1e-9 for a, b in zip(floors, floors[1:])), \
        "a long's structural floor moved DOWN — a floor that can loosen is " \
        "not a floor"
    assert floors[-1] > floors[0], "the floor should have ratcheted up here"

    # -- c3: ensure_protection re-places the bracket when the floor improved
    t = {"direction": 1, "contracts": 5.0, "sl_price": 100.0,
         "tpsl_id": "tpsl1"}
    p = FakePrivate(net=5.0,
                    pending_tpsl_default=[{"tpslId": "tpsl1"}])
    st = make_state(open_trade=t)
    B.ensure_protection(p, st, t, new_stop=110.0)
    assert p.tpsl_placed and p.tpsl_placed[-1]["sl"] == 110.0, p.tpsl_placed
    assert any(c["kind"] == "tpsl" for c in p.cancels), \
        "the old bracket must be cancelled before the new one is placed"
    assert t["sl_price"] == 110.0

    # -- c4: a WORSE stop is refused outright, bracket untouched
    t2 = {"direction": 1, "contracts": 5.0, "sl_price": 110.0,
          "tpsl_id": "tpsl1"}
    p2 = FakePrivate(net=5.0, pending_tpsl_default=[{"tpslId": "tpsl1"}])
    B.ensure_protection(p2, make_state(open_trade=t2), t2, new_stop=90.0)
    assert not p2.tpsl_placed, "the stop must never move against the trade"
    assert not p2.cancels
    assert t2["sl_price"] == 110.0

    # -- c5: a vanished bracket is re-armed at the recorded level
    t3 = {"direction": 1, "contracts": 5.0, "sl_price": 105.0,
          "tpsl_id": "tpsl1"}
    p3 = FakePrivate(net=5.0, pending_tpsl_default=[])     # gone from both reads
    B.ensure_protection(p3, make_state(open_trade=t3), t3, new_stop=105.0)
    assert p3.tpsl_placed and p3.tpsl_placed[-1]["sl"] == 105.0
    assert r["action"] == "entered"


# ---------------------------------------------------------------------------
# (d) exits reconcile when the exchange shows the position gone
# ---------------------------------------------------------------------------

def test_d_exit_reconciles_when_the_exchange_shows_it_gone():
    B.NEW_ENTRIES_ENABLED = True
    d = build_trend_turn_series()
    t = {"rule": "vol_gated_trend", "trigger": "vol_gated_trend",
         "direction": 1, "contracts": 10.0, "entry_price": 1000.0,
         "contract_value": 0.001, "entry_fee_bps": 6.0,
         "entry_time": "2024-01-01 00:00:00 UTC", "bar_ts": "x",
         "sl_price": 950.0, "tpsl_id": "tpsl1", "anchor_swing": 960.0,
         "atr_gate_pct_of_price": 1.5, "leverage_at_entry": 3.0,
         "memory_at_entry": {}}
    state = make_state(open_trade=t)
    feed = FakeFeed(d)
    # exchange says flat, and reports the fill the stop got
    private = FakePrivate(net=0.0, fills=[{"fillPrice": "950.0"}])

    r = B.run_bitcoin(private, feed, feed, state)
    assert r["action"] == "reconciled_exit", r
    assert r["reason"] == "structural_stop"
    assert r["exit_price"] == 950.0
    assert state[B.STATE_KEY]["open_trade"] is None
    assert len(state[B.STATE_KEY]["trades"]) == 1
    rec = state[B.STATE_KEY]["trades"][0]
    assert rec["rule"] == "vol_gated_trend" and rec["reason"] == "structural_stop"
    # -10 USD of price move on 0.01 BTC = -$0.50 gross, minus taker both legs
    assert rec["pnl"] < 0, rec
    assert state["virtual_equity"] == round(1000.0 + rec["pnl"], 2)
    # no NEW position was opened while reconciling an exit
    assert not private.orders, private.orders

    # our own bracket was cancelled, and ONLY ours (never a blanket sweep)
    assert [c["id"] for c in private.cancels] == ["tpsl1"], private.cancels


# ---------------------------------------------------------------------------
# (e) THE MEMORY LOOP ACTUALLY GATES
# ---------------------------------------------------------------------------

def test_e_memory_gates_a_rule_with_consecutive_losses():
    B.NEW_ENTRIES_ENABLED = True          # the BOOK is on; the MEMORY blocks
    d = build_trend_turn_series()

    # -- e1: below the threshold, the rule is only FLAGGED and still trades,
    #        but the arbiter must carry an explicit note about it
    flagged = [losing_trade(f"2026-07-2{i} 00:00:00 UTC")
               for i in range(1, 1 + B.FLAG_AFTER_LOSSES)]
    state = make_state(trades=flagged)
    mem = B.load_memory(state, ledger_path="does/not/exist.csv",
                        learnings_path="does/not/exist.md")
    assert mem["rules"]["vol_gated_trend"]["status"] == "flagged", mem["rules"]
    r = B.run_bitcoin(FakePrivate(net=0.0), FakeFeed(d), FakeFeed(d), state)
    assert r["action"] == "entered", r
    assert r["memory_note"], "a flagged rule must never be taken silently"
    assert "lost" in r["memory_note"]
    assert state[B.STATE_KEY]["open_trade"]["memory_note"] == r["memory_note"]

    # -- e2: at the threshold, with the SAME reason every time, the rule is
    #        STOOD DOWN and no order is placed at all
    dead = [losing_trade(f"2026-07-2{i} 00:00:00 UTC")
            for i in range(1, 1 + B.STAND_DOWN_AFTER_LOSSES)]
    state = make_state(trades=dead)
    mem = B.load_memory(state, ledger_path="does/not/exist.csv",
                        learnings_path="does/not/exist.md")
    m = mem["rules"]["vol_gated_trend"]
    assert m["status"] == "stood_down", m
    assert m["identical_failures"] >= B.STAND_DOWN_AFTER_LOSSES

    private = FakePrivate(net=0.0)
    r = B.run_bitcoin(private, FakeFeed(d), FakeFeed(d), state)
    assert r["action"] == "stand_down", r
    assert "stood down" in r["reason"]
    assert not private.orders, "a stood-down rule must place NO order"
    assert state[B.STATE_KEY]["open_trade"] is None

    # -- e3: the stand-down LATCHES in state and survives a clean record
    latched = state[B.STATE_KEY]["rules_stood_down"]
    assert "vol_gated_trend" in latched, latched
    state["virtual_equity"] = 1000.0
    state[B.STATE_KEY]["trades"] = []          # counters now read clean...
    mem2 = B.load_memory(state, ledger_path="does/not/exist.csv",
                         learnings_path="does/not/exist.md")
    assert mem2["rules"]["vol_gated_trend"]["status"] == "stood_down", \
        "a latched stand-down must not un-latch itself when the counters " \
        "go quiet — only a human clears it"

    # -- e4: and a human, and only a human, clears it
    assert B.clear_rule_stand_down(state, "vol_gated_trend", who="wallace")
    assert not B.clear_rule_stand_down(state, "vol_gated_trend")
    mem3 = B.load_memory(state, ledger_path="does/not/exist.csv",
                         learnings_path="does/not/exist.md")
    assert mem3["rules"]["vol_gated_trend"]["status"] == "clear"
    assert state[B.STATE_KEY]["stand_down_history"][-1]["cleared_by"] == "wallace"

    # -- e5: mixed exit reasons never escalate past a flag (the escalation
    #        rule is REPEATED IDENTICAL failures, not just losses)
    mixed = [losing_trade("2026-07-21 00:00:00 UTC", reason="structural_stop"),
             losing_trade("2026-07-22 00:00:00 UTC", reason="trend_flip"),
             losing_trade("2026-07-23 00:00:00 UTC", reason="structural_stop")]
    mem4 = B.load_memory(make_state(trades=mixed),
                         ledger_path="does/not/exist.csv",
                         learnings_path="does/not/exist.md")
    assert mem4["rules"]["vol_gated_trend"]["status"] == "flagged", mem4["rules"]
    assert mem4["rules"]["vol_gated_trend"]["consecutive_losses"] == 3


# ---------------------------------------------------------------------------
# (f) a lesson is written on EVERY close
# ---------------------------------------------------------------------------

def test_f_a_lesson_is_written_on_every_close():
    def _close(reason, exit_price, prior_lessons=0):
        t = {"rule": "vol_gated_trend", "direction": 1, "contracts": 10.0,
             "entry_price": 1000.0, "contract_value": 0.001,
             "entry_fee_bps": 6.0, "entry_time": "2024-01-01 00:00:00 UTC",
             "anchor_swing": 960.0, "atr_gate_pct_of_price": 1.5,
             "leverage_at_entry": 3.0, "memory_at_entry": {}}
        state = make_state(open_trade=t)
        state["lessons"] = [{"date": "old", "trigger": "x", "trade": "y",
                             "conditions": "z", "why": "w"}] * prior_lessons
        pnl = B.book_exit(state, t, exit_price, reason)
        return state, pnl

    for reason, px in [("structural_stop", 950.0), ("trend_flip", 1010.0),
                       ("structure_broken", 990.0)]:
        state, pnl = _close(reason, px)
        assert len(state["lessons"]) == 1, \
            f"{reason} produced {len(state['lessons'])} lessons, expected 1"
        L = state["lessons"][-1]
        # export_journal.write_learnings() renders EXACTLY these five keys
        assert set(L) == {"date", "trigger", "trade", "conditions", "why"}, L
        assert L["trigger"] == "vol_gated_trend"
        assert L["why"] and len(L["why"]) > 20, L["why"]
        assert "of price" in L["trade"], \
            "the trade line quotes a price move and must say so"
        assert ("made" in L["trade"]) == (pnl > 0)

    # a WIN also gets a lesson — the diary is not a loss log
    state, pnl = _close("trend_flip", 1200.0)
    assert pnl > 0 and len(state["lessons"]) == 1
    assert "made" in state["lessons"][-1]["trade"]

    # lessons are capped, exactly like step5_paper_trade.write_lesson
    state, _ = _close("trend_flip", 1010.0, prior_lessons=60)
    assert len(state["lessons"]) == 50, len(state["lessons"])


# ---------------------------------------------------------------------------
# (g) the book never writes another book's state keys
# ---------------------------------------------------------------------------

def test_g_never_writes_another_books_state():
    B.NEW_ENTRIES_ENABLED = True
    import copy

    OTHER_BOOKS = ["open_trade", "tactical", "shorts_lab", "apprentice",
                   "newsdesk", "diver", "breakout_book"]
    # book-agnostic ledger fields every book already shares
    SHARED = {B.STATE_KEY, "virtual_equity", "lessons", "trigger_stats",
              "benched_triggers"}

    # full entry cycle
    d = build_trend_turn_series()
    state = make_state()
    before = copy.deepcopy(state)
    B.run_bitcoin(FakePrivate(net=0.0), FakeFeed(d), FakeFeed(d), state)
    for key in OTHER_BOOKS:
        assert state[key] == before[key], f"the book mutated {key!r}"
    for key in set(state) - SHARED:
        assert state[key] == before.get(key), f"the book mutated {key!r}"

    # full exit cycle
    t = state[B.STATE_KEY]["open_trade"]
    before = copy.deepcopy(state)
    B.run_bitcoin(FakePrivate(net=0.0, fills=[{"fillPrice": "900.0"}]),
                  FakeFeed(d), FakeFeed(d), state)
    assert state[B.STATE_KEY]["open_trade"] is None and t is not None
    for key in OTHER_BOOKS:
        assert state[key] == before[key], f"the exit path mutated {key!r}"
    for key in set(state) - SHARED:
        assert state[key] == before.get(key), f"the exit path mutated {key!r}"

    # and the source never names another book's key on the left of an
    # assignment or inside a setdefault
    import ast
    import inspect
    src = inspect.getsource(B)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store):
            key = getattr(node.slice, "value", None)
            assert key not in OTHER_BOOKS or key == "open_trade", (
                f"bitcoin.py assigns into another book's state key {key!r}")


# ---------------------------------------------------------------------------
# (h) it runs correctly with its own enable flag OFF
# ---------------------------------------------------------------------------

def test_h_runs_correctly_with_the_enable_flag_off():
    B.NEW_ENTRIES_ENABLED = False
    try:
        # -- h1: a firing signal is logged and refused, with no order and no
        #        unbound-name crash (the exact bug that took the Diver down)
        d = build_trend_turn_series()
        private, state = FakePrivate(net=0.0), make_state()
        r = B.run_bitcoin(private, FakeFeed(d), FakeFeed(d), state)
        assert r["action"] == "stood_down", r
        assert r["reason"] == "book_stood_down"
        assert r["rule"] == "vol_gated_trend" and r["contracts"] > 0, r
        assert not private.orders and not private.tpsl_placed
        assert state[B.STATE_KEY]["open_trade"] is None
        assert state[B.STATE_KEY]["last_bar_ts"] == r["bar_ts"]

        # -- h2: A HELD POSITION STILL CLOSES with the flag off. Standing a
        #        book down must never orphan a live position.
        t = {"rule": "vol_gated_trend", "direction": 1, "contracts": 10.0,
             "entry_price": 1000.0, "contract_value": 0.001,
             "entry_fee_bps": 6.0, "entry_time": "2024-01-01 00:00:00 UTC",
             "bar_ts": "x", "sl_price": 950.0, "tpsl_id": "tpsl1",
             "anchor_swing": 960.0, "memory_at_entry": {}}
        state = make_state(open_trade=t)
        r = B.run_bitcoin(FakePrivate(net=0.0, fills=[{"fillPrice": "950.0"}]),
                          FakeFeed(d), FakeFeed(d), state)
        assert r["action"] == "reconciled_exit", r
        assert state[B.STATE_KEY]["open_trade"] is None
        assert state["lessons"], "a close with the flag off still learns"

        # -- h3: the gate sits AFTER reconcile in the source, so it can
        #        never run before the exit logic (test_stand_down_gates.py's
        #        own invariant, checked here too since this book will join
        #        its GATED_BOOKS list at cutover)
        import inspect
        src = inspect.getsource(B.run_bitcoin)
        assert "STAND-DOWN GATE" in src
        assert src.index("STAND-DOWN GATE") > src.index("reconcile"), \
            "the gate runs BEFORE reconcile — an open position could be " \
            "orphaned"
    finally:
        B.NEW_ENTRIES_ENABLED = True

    # This asserted the file shipped switched OFF, which was right while it
    # was unwired. It is deliberately ON as of 2026-07-25. What matters now
    # is that the switch is a real boolean the cycle actually reads.
    import importlib
    fresh = importlib.reload(B)
    assert isinstance(fresh.NEW_ENTRIES_ENABLED, bool), \
        "the enable switch must exist and be a plain on/off"
    _reattach(fresh)


def _reattach(mod):
    """reload() rebinds the module's globals — put the no-ops AND the
    hermetic journal paths back, so the rest of the run stays offline and
    keeps depending only on state each test builds itself."""
    mod.notify = _noop
    mod.log_event = _noop
    mod.save_state = _noop
    mod.time.sleep = _noop
    mod.LEDGER_CSV = "no/such/ledger.csv"
    mod.LEARNINGS_MD = "no/such/learnings.md"
    mod.NEW_ENTRIES_ENABLED = True


# ---------------------------------------------------------------------------
# (i) taker only — the maker/chase path is never reachable from this book
# ---------------------------------------------------------------------------

def test_i_taker_only_execution():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(B))
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    attrs = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}

    assert "execute_market_clips" in called, \
        "the Bitcoin book must place orders through execute_market_clips"
    assert "execute_maker_or_chase" not in called, (
        "the Bitcoin book is on the pre-OWNER'S-LAW maker path — that path "
        "books phantom fills (test_phantom_fill.py)")
    assert "post_only_order" not in attrs, \
        "a resting post-only order must never exist in this book"
    assert "execute_maker_or_chase" not in dir(B), \
        "the maker path must not even be imported here"

    # both fee constants are the taker fee, on both legs
    assert B.ENTRY_FEE_BPS == 6.0 and B.EXIT_FEE_BPS == 6.0


# ---------------------------------------------------------------------------
# (j) never a bare percentage
# ---------------------------------------------------------------------------

def test_j_no_bare_percentages_in_output():
    """Wallace's rule: "Bitcoin down 5%" (price) and "margin down 30%"
    (unrealizedPnlRatio) are different numbers by a factor of the leverage,
    and this repo has already told him a screen meant something it did not.
    Every interpolated percentage in this file must name its base."""
    import re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "bitcoin.py")).read()
    allowed = ("of price", "of margin", "of notional", "of equity",
               "of the ledger")
    offenders = []
    for m in re.finditer(r"\}%", src):
        tail = src[m.start():m.start() + 30]
        if not any(a in tail for a in allowed):
            offenders.append(tail.splitlines()[0])
    assert not offenders, (
        "these percentages do not say what they are a percentage OF:\n  "
        + "\n  ".join(offenders))

    # the two helpers label themselves
    assert B.price_move_pct(100.0, 105.0) == "+5.00% of price"
    assert B.margin_pct(-0.0533) == "-5.33% of margin"
    assert B.margin_pct(None) == "n/a"


# ---------------------------------------------------------------------------
# (k) the live signal is the validated signal
# ---------------------------------------------------------------------------

def test_k_live_signal_matches_the_validated_one():
    """step150c ran the retest through vol_gated_ma(20, 100, 1.5); the live
    ride and this book run vol_filtered_ma with the same three numbers. On
    the long-only side they must be the same state machine — if an edit to
    either function ever makes them differ, this book has silently become a
    strategy nobody validated."""
    for frame in (build_trend_turn_series(), build_rising_series(),
                  build_gate_shut_series()):
        a = vol_filtered_ma(frame, B.FAST, B.SLOW,
                            min_atr_pct=B.MIN_ATR_PCT).fillna(0)
        b = vol_gated_ma(frame, B.FAST, B.SLOW,
                         min_atr_pct=B.MIN_ATR_PCT).fillna(0)
        assert (a == b).all(), (
            "vol_filtered_ma and vol_gated_ma disagree — the live signal is "
            "no longer the one round 150 validated")

    # and the config is the one step150_edges_retest.md recovered
    assert (B.FAST, B.SLOW, B.MIN_ATR_PCT) == (20, 100, 1.5)
    assert B.TRAIL_BUFFER_PCT == 1.5, \
        "1.5% of price of buffer IS the recovery — at 0 the same edge fails " \
        "train (-$12.18/trade)"
    assert B.FALLBACK_STOP_PCT == 8.0 and B.K_SWING == 5


# ---------------------------------------------------------------------------
# (l) the loop is closed: ledger.csv and learnings.md are read BACK
# ---------------------------------------------------------------------------

def test_l_memory_reads_the_journal_files_back():
    import export_journal

    tmp = tempfile.mkdtemp(prefix="bitcoin_memory_")
    cwd = os.getcwd()
    try:
        # -- l1: a REAL round trip through export_journal's own writer,
        #        inside a temp CWD so the repo's data/ is never touched
        os.chdir(tmp)
        state = make_state()
        state["lessons"] = [
            {"date": "2026-07-24 22:00:08 UTC", "trigger": "vol_gated_trend",
             "trade": "long $1,000 -> structural_stop $950 (-5.00% of price), "
                      "lost $40.00",
             "conditions": "entered on the 1.5% of price volatility gate",
             "why": "stopped out at real structure — nothing to fix"},
        ]
        export_journal.write_learnings(state)
        parsed = B._parse_learnings_md(os.path.join("data", "learnings.md"))
        assert len(parsed) == 1, parsed
        assert parsed[0]["trigger"] == "vol_gated_trend"
        assert parsed[0]["why"].startswith("stopped out at real structure")
        assert parsed[0]["conditions"].startswith("entered on the 1.5%")

        # -- l2: ledger.csv, in export_journal's own header, read back
        os.makedirs("data", exist_ok=True)
        with open(os.path.join("data", "ledger.csv"), "w") as f:
            f.write("timestamp,symbol,action,price,quantity,reason,mode,"
                    "outcome,pnl\n")
            f.write("2026-07-24T03:01:37.304359+00:00,BTC-USDT,BUY,1868.24,"
                    "10,vol_gated_trend,demo,open,\n")
            for i, pnl in enumerate((-11.0, -12.0, -13.0), start=1):
                f.write(f"2026-07-2{i}T05:00:00+00:00,BTC-USDT,SELL,1800.0,,"
                        f"vol_gated_trend:structural_stop,demo,loss,{pnl}\n")
        rows = B.read_ledger_trades(os.path.join("data", "ledger.csv"))
        assert len(rows) == 3, rows                    # BUY rows are not closes
        assert all(r["rule"] == "vol_gated_trend" for r in rows), rows
        assert all(r["reason"] == "structural_stop" for r in rows)

        # -- l3: and those file-only losses GATE the next decision, with no
        #        book-state trades at all. This is the whole point: the
        #        diary on disk changes what the bot does next.
        st = make_state()
        mem = B.load_memory(st, ledger_path=os.path.join("data", "ledger.csv"),
                            learnings_path=os.path.join("data",
                                                        "learnings.md"))
        assert mem["n_ledger_rows"] == 3 and mem["n_lessons"] == 1
        assert mem["rules"]["vol_gated_trend"]["status"] == "stood_down", \
            mem["rules"]
    finally:
        os.chdir(cwd)
        shutil.rmtree(tmp, ignore_errors=True)

    # -- l4: a missing diary is an empty memory, never an exception
    assert B.read_ledger_trades("no/such/file.csv") == []
    assert B._parse_learnings_md("no/such/file.md") == []
    empty = B.load_memory(make_state(), ledger_path="no/such/file.csv",
                          learnings_path="no/such/file.md")
    assert empty["rules"]["vol_gated_trend"]["status"] == "clear"

    # -- l5: the repo's REAL journal files parse without blowing up
    here = os.path.dirname(os.path.abspath(__file__))
    for L in B._parse_learnings_md(os.path.join(here, "data",
                                                "learnings.md")):
        assert L["why"], f"a real lesson parsed with no lesson text: {L}"


# ---------------------------------------------------------------------------
# (m) the arbiter
# ---------------------------------------------------------------------------

def test_m_arbiter_decides_and_never_hides_a_flag():
    clear = {"rules": {"a": {"status": "clear", "note": ""},
                       "b": {"status": "clear", "note": ""}}}

    def sig(rule, direction):
        return B.RuleSignal(rule=rule, direction=direction, stop_level=90.0,
                            reason=f"{rule} fired")

    # nothing fired
    assert B.arbitrate([], clear).action == "no_signal"

    # two rules, opposite directions -> NOBODY trades
    v = B.arbitrate([sig("a", 1), sig("b", -1)], clear)
    assert v.action == "stand_down" and "ONE thesis" in v.reason, v

    # agreeing rules -> priority order wins (registered rules only)
    prio = {"rules": {"vol_gated_trend": {"status": "clear", "note": ""},
                      "zzz": {"status": "clear", "note": ""}}}
    v = B.arbitrate([sig("zzz", 1), sig("vol_gated_trend", 1)], prio)
    assert v.action == "enter" and v.signal.rule == "vol_gated_trend", v

    # a stood-down rule never reaches the decision
    down = {"rules": {"a": {"status": "stood_down", "note": "3 in a row"}}}
    v = B.arbitrate([sig("a", 1)], down)
    assert v.action == "stand_down" and "stood down" in v.reason, v
    assert "3 in a row" in v.memory_note

    # a flagged rule trades, but never silently
    flagged = {"rules": {"a": {"status": "flagged", "note": "last 2 lost",
                               "consecutive_losses": 2}}}
    v = B.arbitrate([sig("a", 1)], flagged)
    assert v.action == "enter" and v.memory_note == "last 2 lost", v

    # a flagged rule with an EMPTY note still gets one — the arbiter is not
    # allowed to take a flagged setup with nothing on the record
    v = B.arbitrate([sig("a", 1)],
                    {"rules": {"a": {"status": "flagged", "note": "",
                                     "consecutive_losses": 4}}})
    assert v.action == "enter" and v.memory_note, v


# ---------------------------------------------------------------------------
# (n) sizing: leverage is an output, capped by the instrument's own ceiling
# ---------------------------------------------------------------------------

def test_n_sizing_is_risk_first_and_leverage_is_an_output():
    # a wide stop -> small size, low leverage, no cap involved
    r = B.size_from_risk(1000.0, 100.0, 90.0, 0.001, 150.0)
    assert r["capped_by"] is None
    assert abs(r["risk_usd"] - 20.0) < 1e-9
    # risk / stop distance = 20/10 = 2 BTC = 2000 contracts
    assert abs(r["contracts"] - 2000.0) < B.LOT
    assert r["leverage"] == round(r["notional"] / 1000.0, 2)

    # a very tight stop would imply absurd leverage -> the desk ceiling binds
    tight = B.size_from_risk(1000.0, 100.0, 99.9, 0.001, 150.0)
    assert tight["leverage"] <= B.MAX_LEVERAGE + 1e-9
    assert tight["capped_by"] == "desk_ceiling"

    # ...and the INSTRUMENT'S OWN maxLeverage wins when it is lower — this
    # number is read from BloFin, never assumed
    inst = B.size_from_risk(1000.0, 100.0, 99.9, 0.001, 5.0)
    assert inst["leverage"] <= 5.0 + 1e-9 and inst["capped_by"] == "instrument_max"

    # rounding is DOWN to the lot step: a risk-sized position must never be
    # rounded UP past the budget it was authorised
    down = B.size_from_risk(1000.0, 100.0, 90.0, 0.001, 150.0)
    steps = down["contracts"] / B.LOT
    assert abs(steps - round(steps)) < 1e-6, down["contracts"]
    assert down["contracts"] <= 20.0 / 10.0 / 0.001 + 1e-9, \
        "the size must never round UP past the authorised risk budget"

    # the exchange minimum is honoured and REPORTED when it forces us over
    tiny = B.size_from_risk(0.1, 100.0, 1.0, 0.001, 150.0)
    assert tiny["contracts"] == B.LOT and tiny["forced_minimum"] is True
    assert tiny["capped_by"] == "exchange_minimum_size"

    # a nonsense stop never produces a position
    assert B.size_from_risk(1000.0, 100.0, 100.0, 0.001, 150.0)["contracts"] == 0.0

    # and the live path reads maxLeverage off the instrument endpoint
    spec = B.instrument_spec(FakeFeed(build_rising_series()))
    assert spec["contractValue"] == 0.001 and spec["maxLeverage"] == 150.0


# ---------------------------------------------------------------------------
# (o) attribution: this book reasons about its OWN slice, never the raw net
# ---------------------------------------------------------------------------

def test_o_attribution_uses_its_own_slice():
    t = {"direction": 1, "contracts": 10.0}
    state = make_state(open_trade=t)
    state["shorts_lab"]["open_trade"] = {"direction": -1, "contracts": 30.0}

    # exchange net = our +10 and the lab's -30
    assert B.attributed(-20.0, state) == 10.0
    assert B.unexplained(-20.0, state) == 0.0

    # a slice nobody claims shows up as unexplained, and is NOT ours
    assert B.attributed(-15.0, state) == 15.0
    assert B.unexplained(-15.0, state) == 5.0

    # with a flat book, our slice is zero even though the net is not
    flat = make_state()
    flat["tactical"]["open_trade"] = {"contracts": 7.0}
    assert B.attributed(7.0, flat) == 0.0
    assert B.unexplained(7.0, flat) == 0.0

    # Daily Pick's BTC slot is folded in too — book_ledger has never known
    # about it, so without this shim its position would land inside THIS
    # book's slice (step300_consolidation_plan.md's hole #1)
    dp = make_state()
    dp["daily_pick"] = {"open_trades": [
        {"symbol": "BTC-USDT", "direction": -1, "contracts": 12.0},
        {"symbol": "SOL-USDT", "direction": 1, "contracts": 99.0}]}
    assert B._daily_pick_btc(dp) == -12.0, "only the BTC slot may count"
    assert B.attributed(-12.0, dp) == 0.0, \
        "a Daily Pick BTC position must never be mistaken for ours"
    assert B.unexplained(-12.0, dp) == 0.0

    # another book's position must never be adopted or flattened
    B.NEW_ENTRIES_ENABLED = True
    d = build_gate_shut_series()
    private = FakePrivate(net=25.0)
    st = make_state()
    r = B.run_bitcoin(private, FakeFeed(d), FakeFeed(d), st)
    # The bot may open ITS OWN position (the gate is gone, so a quiet bar in
    # an uptrend is now tradeable). What it must never do is act on the 25
    # contracts it does not own: no reduce-only order, and its own recorded
    # size must be its own sizing rather than the stranger's.
    assert not any(o.get("reduce_only") for o in private.orders), \
        "an unclaimed net must never be flattened or traded against"
    own = (st[B.STATE_KEY].get("open_trade") or {}).get("contracts")
    assert own != 25.0, "the bot adopted a position it does not own"
    # It may legitimately ENTER here now that the volatility gate is gone —
    # the old assertion of "no_signal" was really testing the gate, not
    # attribution. What matters is the two checks above.
    assert r["action"] in ("entered", "no_signal", "stood_down"), r


# ---------------------------------------------------------------------------
# (p) idempotency: the same closed bar decided on twice is one trade
# ---------------------------------------------------------------------------

def test_p_idempotent_per_bar():
    B.NEW_ENTRIES_ENABLED = True
    d = build_trend_turn_series()
    private, state = FakePrivate(net=0.0), make_state()

    r1 = B.run_bitcoin(private, FakeFeed(d), FakeFeed(d), state)
    assert r1["action"] == "entered"
    n_orders = len(private.orders)

    # the book's own position is closed elsewhere WITHOUT the 4h bar moving
    state[B.STATE_KEY]["open_trade"] = None
    r2 = B.run_bitcoin(private, FakeFeed(d), FakeFeed(d), state)
    assert r2["action"] == "noop_already_processed", r2
    assert len(private.orders) == n_orders, \
        "the idempotency guard must prevent a second entry on the same bar"


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main():
    tests = [test_a_entry_fires_on_the_validated_signal,
             test_b_the_volatility_gate_is_NOT_applied,
             test_c_structural_stop_is_exchange_side_and_ratchets_one_way,
             test_d_exit_reconciles_when_the_exchange_shows_it_gone,
             test_e_memory_gates_a_rule_with_consecutive_losses,
             test_f_a_lesson_is_written_on_every_close,
             test_g_never_writes_another_books_state,
             test_h_runs_correctly_with_the_enable_flag_off,
             test_i_taker_only_execution,
             test_j_no_bare_percentages_in_output,
             test_k_live_signal_matches_the_validated_one,
             test_l_memory_reads_the_journal_files_back,
             test_m_arbiter_decides_and_never_hides_a_flag,
             test_n_sizing_is_risk_first_and_leverage_is_an_output,
             test_o_attribution_uses_its_own_slice,
             test_p_idempotent_per_bar]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("THE BITCOIN BOOK TESTS")
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
