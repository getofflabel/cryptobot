"""
test_gold_book.py — offline tests for gold_book.py's REAL-ORDER
donchian(ENTRY_N)/STRUCTURE-TRAILING book (round-59 exit swap: EMA20-close
retired, replaced by a ratcheting confirmed-swing-low floor enforced via a
REAL exchange-side stop order — see gold_book.py's module docstring, ROUND
59 EXIT SWAP section). NO NETWORK: a fake private client and a fake
candle/ticker/instrument feed stand in for BloFin; every Telegram/log/state
side effect on step5_paper_trade is monkeypatched to a no-op, exactly like
before.

ORACLE: there is no external strategy function to import as an oracle
anymore (the entry is a plain per-bar donchian check computed inline in
gold_book._decision, and the exit floor is computed by gold_book's own
_compute_trail_floor / _find_swing_lows — those functions ARE the deployed
strategy, ported verbatim from step59_exit_science.py's sealed-validated
X3). So the oracle here is gold_book's own pure functions, called directly
against hand-constructed, hand-verified synthetic data (documented inline,
below) — never a magic hardcoded floor number. Where a value can be
independently hand-computed (the fallback floor, the PnL math), it is.

Nine intents:
  a) breakout entry — market order + leverage + INITIAL structure floor
     (a real confirmed swing low here, not the crash-SL fallback)
  b) holds through noise — no new orders, floor unchanged, before any new
     swing confirms
  c) floor RATCHETS UP the cycle a new confirmed swing low appears above
     it — and the exchange bracket is cancelled + replaced at the new
     level (cancel/replace mechanics)
  d) floor stays put (never ratchets DOWN) on quiet cycles after that
  e) exit fires via reconciliation when the exchange's own floor-stop has
     obviously fired (position gone) — booked with the correct PnL
  f) idempotent — same bar processed twice while holding = no duplicate
     bracket calls
  g) ledger math — sizing formula (25% alloc x 2x lev / contract math) and
     realized_pnl_total bookkeeping match a hand computation
  h) dry mode — zero orders/brackets/leverage calls, zero state writes,
     in BOTH the would-enter and the would-hold cases
  i) crash-SL fallback — when NO confirmed protective swing low exists yet
     as of entry, the floor starts at entry*(1 - CRASH_SL_PCT), hand-
     computed independently of gold_book's own function

Run with:  python3 test_gold_book.py
"""

from __future__ import annotations

import sys
import traceback
from types import SimpleNamespace

import numpy as np
import pandas as pd

import gold_book
import step5_paper_trade as s5


def _noop(*a, **kw):
    pass


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLiveFeed:
    """Stands in for config.make_exchange("live") — public market data
    only. `day_idx` controls how many bars are "available" (simulates the
    bot watching a growing daily series one bar at a time)."""

    CONTRACT_VALUE = 0.001
    MIN_SIZE = 1.0
    LOT_SIZE = 1.0
    TICK_SIZE = 0.1

    def __init__(self, full_df: pd.DataFrame):
        self.full = full_df
        self.day_idx = len(full_df) - 1

    def get_candles(self, symbol, timeframe, limit):
        assert symbol == gold_book.SYMBOL
        return self.full.iloc[:self.day_idx + 1].reset_index(drop=True)

    def get_ticker(self, symbol):
        assert symbol == gold_book.SYMBOL
        px = float(self.full["close"].iloc[self.day_idx])
        return SimpleNamespace(last=px)

    def get_instrument(self, symbol):
        assert symbol == gold_book.SYMBOL
        return {"contractValue": str(self.CONTRACT_VALUE),
                "minSize": str(self.MIN_SIZE), "lotSize": str(self.LOT_SIZE),
                "tickSize": str(self.TICK_SIZE)}


class FakePrivate:
    """Stands in for blofin_private.BlofinDemoPrivate. `mark_price` is the
    price the harness sets each cycle (mirrors what the real exchange would
    currently be quoting) — market_order() fills against it. `position` /
    `_last_fill_price` can be poked directly by a test to simulate the
    exchange's OWN resting stop order having already fired between
    cycles — exactly how a real floor-touch exit is discovered (see
    gold_book.run_gold_book's reconciliation branch)."""

    def __init__(self):
        self.mark_price = 0.0
        self.position = 0.0        # signed contracts, long-only in practice
        self.leverage_calls = []
        self.orders = []           # list of dicts
        self.tpsl_calls = []       # list of dicts, one per place_tpsl call
        self.cancelled_tpsl = []
        self._next_oid = 1
        self._next_tpsl = 1
        self._last_fill_price = None
        self.fail_market_order = False
        self.fail_net_read = False
        self.fail_place_tpsl = False

    def net_position_contracts(self, symbol):
        if self.fail_net_read:
            raise RuntimeError("simulated read failure")
        return self.position

    def ensure_leverage(self, symbol, leverage, margin_mode="cross"):
        self.leverage_calls.append((symbol, leverage, margin_mode))
        return True

    def market_order(self, symbol, side, contracts, reduce_only=False,
                     margin_mode="cross", client_order_id=None):
        if self.fail_market_order:
            raise RuntimeError("simulated order rejection")
        oid = str(self._next_oid)
        self._next_oid += 1
        self.orders.append({"symbol": symbol, "side": side,
                            "contracts": contracts,
                            "reduce_only": reduce_only, "order_id": oid})
        sign = 1 if side == "buy" else -1
        self.position += sign * contracts
        self._last_fill_price = self.mark_price
        return oid

    def place_tpsl(self, symbol, position_side_close, contracts, tp_price,
                   sl_price, margin_mode="cross", client_order_id=None):
        if self.fail_place_tpsl:
            raise RuntimeError("simulated bracket rejection")
        tid = f"tpsl{self._next_tpsl}"
        self._next_tpsl += 1
        self.tpsl_calls.append({"symbol": symbol,
                                "position_side_close": position_side_close,
                                "contracts": contracts, "tp_price": tp_price,
                                "sl_price": sl_price, "id": tid})
        return tid

    def cancel_tpsl(self, symbol, tpsl_id):
        self.cancelled_tpsl.append(tpsl_id)

    def fills(self, symbol, order_id=None):
        if self._last_fill_price is None:
            return []
        return [{"fillPrice": self._last_fill_price,
                 "orderId": order_id or "x"}]


# ---------------------------------------------------------------------------
# Synthetic data — RATCHET_DATA: a breakout WITH a real confirmed
# protective swing low already in place at entry, then a SECOND, higher
# confirmed swing low forming after entry (to prove the floor ratchets up).
# Hand-verified below (not just "the code says so") against
# gold_book._find_swing_lows's exact rule: bar j is a confirmed swing low
# iff low[j] <= min(low[j-k:j+k+1]), confirmed at j+k, k=gold_book.K_SWING=5.
#
# idx  0- 4: 4010,4008,4006,4004,4002   (descending into a dip)
# idx     5: 4000                        <- swing low #1, confirmed at 5+5=10
# idx  6-10: 4002,4004,4006,4008,4010   (ascending back out, symmetric)
# idx 11-19: 4012,4014,...,4028         (STRICTLY increasing warmup — no
#                                         ties, so no spurious pivots; see
#                                         module docstring below for why a
#                                         flat run would have caused extra
#                                         tied pivots via the "<=" rule)
# idx    20: 4300                        <- BREAKOUT (rolling20 high of
#                                            idx0-19 is 4028; entry fires)
# idx 21-25: 4290,4280,4270,4260,4250   (descending into a second dip)
# idx    26: 4240                        <- swing low #2, confirmed at 31
# idx 27-31: 4250,4260,4270,4280,4290   (ascending back out, symmetric)
# idx 32-36: 4295 (flat) x5              (quiet — no new pivot forms; see
#                                         hand-check below)
#
# At ENTRY_DAY=20 (n=21 bars, j checked over range(5,16)=5..15): only j=5
# registers (window min 4000, unique — segment idx11-19 is strictly
# increasing so no interior bar there is ever <= its own window's min).
# So the ONLY confirmed-by-entry protective pivot is (confirm_idx=10,
# price=4000) -> initial floor = 4000.0 exactly.
#
# The second dip's bottom (j=26) only enters the checkable range
# range(5, n-5) once n>31, i.e. once the daily pull includes bar index 31
# (day_idx=31, n=32 -> range(5,27) includes 26) -> confirm_idx=31. So the
# floor should ratchet from 4000 -> 4240 exactly starting the day-31 cycle,
# not before.
BREAKOUT_DAY = 20
RATCHET_CONFIRM_DAY = 31
INIT_FLOOR = 4000.0
RATCHET_FLOOR = 4240.0


def _seg_dip(base_lo=4000, base_hi=4010, step=2):
    lo = list(range(base_hi, base_lo - step, -step))     # 4010..4000 desc
    hi = list(range(base_lo + step, base_hi + step, step))  # 4002..4010 asc
    return lo + hi   # 4010,4008,4006,4004,4002,4000,4002,4004,4006,4008,4010


def make_ratchet_data() -> pd.DataFrame:
    seg_a = _seg_dip(4000, 4010, 2)                        # idx0-10, 11 bars
    seg_b = [4012, 4014, 4016, 4018, 4020, 4022, 4024, 4026, 4028]  # idx11-19
    breakout = [4300]                                       # idx20
    seg_c = [4290, 4280, 4270, 4260, 4250, 4240,             # idx21-26
            4250, 4260, 4270, 4280, 4290]                   # idx27-31
    seg_d = [4295] * 5                                       # idx32-36
    closes = [float(x) for x in seg_a + seg_b + breakout + seg_c + seg_d]

    dates = pd.date_range("2025-01-01", periods=len(closes), freq="D",
                          tz="UTC")
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes,
        "volume": [500.0] * len(closes),
    })


RATCHET = make_ratchet_data()

# hand-verify the dataset does what the comment above claims, using
# gold_book's OWN pivot function directly (not a re-derivation) — this is
# a sanity check on the SYNTHETIC DATA's construction, run once at import
# time, independent of any test below.
_low_full = RATCHET["low"].to_numpy()
_ci_at_entry, _pr_at_entry = gold_book._find_swing_lows(
    _low_full[:BREAKOUT_DAY + 1], gold_book.K_SWING)
assert list(_ci_at_entry) == [10], (
    f"dataset construction assumption broken: expected exactly one "
    f"confirmed pivot (idx10) as of entry, got confirm_idx={list(_ci_at_entry)}")
assert list(_pr_at_entry) == [4000.0]

_ci_at_ratchet, _pr_at_ratchet = gold_book._find_swing_lows(
    _low_full[:RATCHET_CONFIRM_DAY + 1], gold_book.K_SWING)
assert 31 in list(_ci_at_ratchet) and 4240.0 in list(_pr_at_ratchet), (
    f"dataset construction assumption broken: expected confirm_idx=31 "
    f"price=4240 by day {RATCHET_CONFIRM_DAY}, got "
    f"{list(zip(_ci_at_ratchet, _pr_at_ratchet))}")


# ---------------------------------------------------------------------------
# Synthetic data — FALLBACK_DATA: a breakout with NO prior confirmed
# protective swing low at all (strictly increasing warmup — see the
# Dataset-2 reasoning in the module docstring: a strictly increasing
# sequence's window-minimum is always its LEFT edge, so no interior bar j
# ever satisfies low[j] <= window.min()). Tests the CRASH_SL_PCT fallback.
#
# idx 0-19: 4000, 4005, 4010, ..., 4095 (step 5, strictly increasing)
# idx   20: 4300  <- BREAKOUT (rolling20 high of idx0-19 is 4095)
def make_fallback_data() -> pd.DataFrame:
    closes = [4000.0 + 5.0 * i for i in range(20)] + [4300.0]
    dates = pd.date_range("2025-03-01", periods=len(closes), freq="D",
                          tz="UTC")
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes,
        "volume": [500.0] * len(closes),
    })


FALLBACK = make_fallback_data()
FALLBACK_ENTRY_DAY = 20

_ci_fb, _pr_fb = gold_book._find_swing_lows(
    FALLBACK["low"].to_numpy()[:FALLBACK_ENTRY_DAY + 1], gold_book.K_SWING)
assert len(_ci_fb) == 0, (
    f"dataset construction assumption broken: FALLBACK_DATA must have ZERO "
    f"confirmed pivots as of entry, got {list(_ci_fb)}")


STARTING_EQUITY = 2000.0


def install_offline():
    s5.notify = _noop
    s5.log_event = _noop
    s5.save_state = _noop
    s5.CLOUD_STATE = False


def make_state():
    return {"virtual_equity": STARTING_EQUITY}


def expected_contracts(ref_price: float) -> float:
    notional = STARTING_EQUITY * gold_book.GOLD_ALLOC * gold_book.GOLD_LEV
    raw = notional / (FakeLiveFeed.CONTRACT_VALUE * ref_price)
    return gold_book._round_lot(raw, FakeLiveFeed.LOT_SIZE,
                                FakeLiveFeed.MIN_SIZE)


def run_day(live, private, state, day_idx, dry=False):
    live.day_idx = day_idx
    private.mark_price = float(live.full["close"].iloc[day_idx])
    return gold_book.run_gold_book(private, live, state, dry=dry)


def new_rig(full=RATCHET):
    install_offline()
    live = FakeLiveFeed(full)
    private = FakePrivate()
    state = make_state()
    return live, private, state


# ---------------------------------------------------------------------------
# a) breakout entry — order + leverage + INITIAL structure floor
# ---------------------------------------------------------------------------


def test_a_enters_with_order_leverage_and_initial_floor():
    live, private, state = new_rig()
    result = run_day(live, private, state, BREAKOUT_DAY)
    assert result["action"] == "entered", f"expected entry, got {result['action']}"

    gb = state["gold_book"]
    t = gb["open_trade"]
    assert t is not None, "should have an open trade after the breakout"
    breakout_date = str(RATCHET["timestamp"].iloc[BREAKOUT_DAY].date())
    assert t["entry_date"] == breakout_date
    assert t["entry_price"] == 4300.0

    # exactly one market order, a BUY, not reduce-only
    assert len(private.orders) == 1, private.orders
    order = private.orders[0]
    assert order["side"] == "buy" and not order["reduce_only"]
    assert order["symbol"] == gold_book.SYMBOL

    # leverage was set to GOLD_LEV before the order
    assert private.leverage_calls == [(gold_book.SYMBOL, gold_book.GOLD_LEV, "cross")]

    # sizing matches the 25%-alloc / 2x-lev formula, whole-contract lot
    ref_price = 4300.0
    exp_contracts = expected_contracts(ref_price)
    assert order["contracts"] == exp_contracts, (order["contracts"], exp_contracts)
    assert t["contracts"] == exp_contracts
    assert float(t["contracts"]).is_integer(), "lotSize=1 -> whole contracts only"

    # INITIAL structure floor placed: no TP, floor == the real confirmed
    # protective swing low (4000), NOT the crash-SL fallback (this dataset
    # has a real pivot — see the module-level hand-check above)
    assert t["trail_floor"] == INIT_FLOOR, (t["trail_floor"], INIT_FLOOR)
    assert t["sl_price"] == INIT_FLOOR
    assert len(private.tpsl_calls) == 1, private.tpsl_calls
    tp = private.tpsl_calls[0]
    assert tp["position_side_close"] == "sell"
    assert tp["tp_price"] is None, "no take-profit — winners must run"
    assert tp["sl_price"] == INIT_FLOOR

    print(f"  [a] OK — entered {breakout_date} @ {t['entry_price']:.2f}, "
          f"{t['contracts']:.0f} ct, lev={gold_book.GOLD_LEV:.0f}x, "
          f"initial structure floor ${t['trail_floor']:.2f} (a real "
          f"confirmed swing low, not the crash-SL fallback)")
    return live, private, state


# ---------------------------------------------------------------------------
# b) holds through noise — floor unchanged BEFORE the second swing confirms
# ---------------------------------------------------------------------------


def test_b_holds_through_noise_floor_unchanged():
    live, private, state = test_a_enters_with_order_leverage_and_initial_floor()
    orders_at_entry = len(private.orders)
    tpsl_at_entry = len(private.tpsl_calls)

    for day_idx in range(BREAKOUT_DAY + 1, RATCHET_CONFIRM_DAY):
        result = run_day(live, private, state, day_idx)
        assert result["action"] == "hold", (
            f"day {day_idx}: expected hold, got {result['action']}")
        assert result["trail_floor"] == INIT_FLOOR, (
            f"day {day_idx}: floor must stay at {INIT_FLOOR} before the "
            f"second swing confirms, got {result['trail_floor']}")
        assert state["gold_book"]["open_trade"]["trail_floor"] == INIT_FLOOR
        assert len(private.orders) == orders_at_entry, (
            "no new market orders should be placed while holding")
        assert len(private.tpsl_calls) == tpsl_at_entry, (
            f"day {day_idx}: no new bracket should be placed — the floor "
            f"hasn't moved yet")
        assert state["gold_book"]["trades"] == []

    print(f"  [b] OK — held unchanged through bars "
          f"{BREAKOUT_DAY + 1}..{RATCHET_CONFIRM_DAY - 1}, floor stayed "
          f"${INIT_FLOOR:.2f}, zero new orders or brackets")
    return live, private, state


# ---------------------------------------------------------------------------
# c) floor RATCHETS UP when the second swing confirms — bracket cancelled
#    and replaced on the exchange (cancel/replace mechanics)
# ---------------------------------------------------------------------------


def test_c_floor_ratchets_up_and_bracket_replaced():
    live, private, state = test_b_holds_through_noise_floor_unchanged()
    old_tpsl_id = state["gold_book"]["open_trade"]["tpsl_id"]
    tpsl_before = list(private.tpsl_calls)
    cancelled_before = list(private.cancelled_tpsl)

    result = run_day(live, private, state, RATCHET_CONFIRM_DAY)
    assert result["action"] == "hold"
    assert result["trail_floor"] == RATCHET_FLOOR, (
        result["trail_floor"], RATCHET_FLOOR)

    t = state["gold_book"]["open_trade"]
    assert t["trail_floor"] == RATCHET_FLOOR
    assert t["sl_price"] == RATCHET_FLOOR
    assert t["trail_floor"] > INIT_FLOOR, "the floor must have moved UP"

    # exactly ONE new bracket placed, at the new floor
    assert len(private.tpsl_calls) == len(tpsl_before) + 1, private.tpsl_calls
    new_call = private.tpsl_calls[-1]
    assert new_call["sl_price"] == RATCHET_FLOOR
    assert new_call["position_side_close"] == "sell"
    assert new_call["contracts"] == t["contracts"]

    # the OLD bracket was cancelled (cancel/replace, not a naked second
    # order left resting)
    assert private.cancelled_tpsl == cancelled_before + [old_tpsl_id], (
        private.cancelled_tpsl)
    assert t["tpsl_id"] == new_call["id"]
    assert t["tpsl_id"] != old_tpsl_id

    # no new MARKET order — this is a bracket update, never a re-entry
    assert not any(o["symbol"] == gold_book.SYMBOL for o in private.orders[1:]), (
        "ratcheting the floor must never place a market order")

    print(f"  [c] OK — floor ratcheted ${INIT_FLOOR:.2f} -> "
          f"${RATCHET_FLOOR:.2f} on the day the second swing low confirmed "
          f"(day {RATCHET_CONFIRM_DAY}); old bracket {old_tpsl_id} "
          f"cancelled, new bracket {t['tpsl_id']} placed at the new floor")
    return live, private, state


# ---------------------------------------------------------------------------
# d) floor stays put after the ratchet — never moves down
# ---------------------------------------------------------------------------


def test_d_floor_never_moves_down_after_ratchet():
    live, private, state = test_c_floor_ratchets_up_and_bracket_replaced()
    tpsl_after_ratchet = len(private.tpsl_calls)

    for day_idx in range(RATCHET_CONFIRM_DAY + 1, len(RATCHET) - 1):
        result = run_day(live, private, state, day_idx)
        assert result["action"] == "hold"
        assert result["trail_floor"] == RATCHET_FLOOR, (
            f"day {day_idx}: floor must stay at {RATCHET_FLOOR}, got "
            f"{result['trail_floor']}")
        assert result["trail_floor"] >= RATCHET_FLOOR, "floor must never regress"
        assert len(private.tpsl_calls) == tpsl_after_ratchet, (
            f"day {day_idx}: no bracket update should fire on a quiet day")

    print(f"  [d] OK — floor held at ${RATCHET_FLOOR:.2f} through bars "
          f"{RATCHET_CONFIRM_DAY + 1}..{len(RATCHET) - 2}, never moved down, "
          f"zero spurious bracket updates")
    return live, private, state


# ---------------------------------------------------------------------------
# e) exit fires via reconciliation when the exchange's floor-stop fires —
#    booked through _finish_exit with the correct PnL
# ---------------------------------------------------------------------------


def test_e_exit_fires_via_reconcile_with_correct_pnl():
    live, private, state = test_d_floor_never_moves_down_after_ratchet()
    t_before = dict(state["gold_book"]["open_trade"])
    orders_before = len(private.orders)

    # simulate the REAL exchange-side floor stop having already fired
    # between cycles — exactly like a crash-SL firing pre-round-59, this
    # book only ever finds out via reconciliation (net_position_contracts
    # shows the position materially gone).
    exit_day = len(RATCHET) - 1
    private.position = 0.0
    private._last_fill_price = RATCHET_FLOOR

    result = run_day(live, private, state, exit_day)
    assert result["action"] == "reconciled_floor_exit", result["action"]

    gb = state["gold_book"]
    assert gb["open_trade"] is None, "should be flat after the exit"
    assert len(gb["trades"]) == 1
    trade = gb["trades"][0]
    assert trade["reason"] == "floor_fired"
    assert trade["exit_price"] == RATCHET_FLOOR

    # reconcile must NEVER place a new order — the exchange already closed
    # the position; this book only books the ledger line
    assert len(private.orders) == orders_before, (
        "reconcile must never place an order — the exchange already did "
        "the closing")

    # hand-check the PnL math independently of gold_book's own arithmetic
    size_units = t_before["contracts"] * t_before["contract_value"]
    gross = size_units * (RATCHET_FLOOR - t_before["entry_price"])
    fees = (t_before["entry_price"] * gold_book.ENTRY_FEE_BPS
            + RATCHET_FLOOR * gold_book.EXIT_FEE_BPS) * size_units / 10_000
    expected_pnl = round(gross - fees, 2)
    assert trade["pnl"] == expected_pnl, (trade["pnl"], expected_pnl)
    assert trade["pnl"] < 0, (
        f"exit below entry (floor {RATCHET_FLOOR} < entry "
        f"{t_before['entry_price']}) must be a loss, got {trade['pnl']}")
    assert gb["realized_pnl_total"] == expected_pnl

    print(f"  [e] OK — exit reconciled from the exchange's floor stop @ "
          f"${trade['exit_price']:.2f}, pnl ${trade['pnl']:+,.2f} "
          f"(hand-checked, correctly negative), zero new orders placed")
    return live, private, state


# ---------------------------------------------------------------------------
# f) idempotent — same bar (a ratchet day) processed twice = no duplicate
#    bracket calls
# ---------------------------------------------------------------------------


def test_f_idempotent_same_bar_twice_no_duplicate_brackets():
    live, private, state = test_b_holds_through_noise_floor_unchanged()
    tpsl_before = len(private.tpsl_calls)

    result1 = run_day(live, private, state, RATCHET_CONFIRM_DAY)
    assert result1["action"] == "hold"
    assert len(private.tpsl_calls) == tpsl_before + 1, "the ratchet itself"

    tpsl_after_ratchet = len(private.tpsl_calls)
    open_trade_snapshot = dict(state["gold_book"]["open_trade"])

    result2 = run_day(live, private, state, RATCHET_CONFIRM_DAY)
    assert result2["action"] == "noop_already_processed", result2["action"]
    assert len(private.tpsl_calls) == tpsl_after_ratchet, (
        "must not place a duplicate bracket on a re-run of the same bar")
    assert state["gold_book"]["open_trade"] == open_trade_snapshot

    print("  [f] OK — the same bar processed twice produced exactly one "
          "bracket update (and one ratchet), no duplicates")


# ---------------------------------------------------------------------------
# g) ledger math — sizing formula + realized_pnl_total accumulation
# ---------------------------------------------------------------------------


def test_g_ledger_math():
    live, private, state = new_rig()
    ref_price = 4300.0
    exp_contracts = expected_contracts(ref_price)
    exp_notional = round(exp_contracts * FakeLiveFeed.CONTRACT_VALUE * ref_price, 2)

    raw_notional = STARTING_EQUITY * gold_book.GOLD_ALLOC * gold_book.GOLD_LEV
    assert abs(raw_notional - STARTING_EQUITY * 0.5) < 1e-9, (
        "25% alloc x 2x leverage must equal 0.5x equity notional")

    run_day(live, private, state, BREAKOUT_DAY)
    t = state["gold_book"]["open_trade"]
    assert t["contracts"] == exp_contracts
    assert abs(t["notional"] - exp_notional) <= exp_contracts * FakeLiveFeed.CONTRACT_VALUE

    for day_idx in range(BREAKOUT_DAY + 1, len(RATCHET) - 1):
        run_day(live, private, state, day_idx)

    private.position = 0.0
    private._last_fill_price = state["gold_book"]["open_trade"]["trail_floor"]
    run_day(live, private, state, len(RATCHET) - 1)

    trade = state["gold_book"]["trades"][0]
    assert state["gold_book"]["realized_pnl_total"] == trade["pnl"]

    # a second round trip accumulates rather than overwrites
    live3, private3, state3 = new_rig()
    state3["gold_book"] = dict(state["gold_book"])
    state3["gold_book"]["trades"] = list(state["gold_book"]["trades"])
    prior_total = state3["gold_book"]["realized_pnl_total"]
    run_day(live3, private3, state3, BREAKOUT_DAY)
    for day_idx in range(BREAKOUT_DAY + 1, len(RATCHET) - 1):
        run_day(live3, private3, state3, day_idx)
    private3.position = 0.0
    private3._last_fill_price = state3["gold_book"]["open_trade"]["trail_floor"]
    run_day(live3, private3, state3, len(RATCHET) - 1)
    assert len(state3["gold_book"]["trades"]) == 2
    second_pnl = state3["gold_book"]["trades"][1]["pnl"]
    assert state3["gold_book"]["realized_pnl_total"] == round(
        prior_total + second_pnl, 2), "realized_pnl_total must ACCUMULATE"

    print(f"  [g] OK — sizing formula (25% x 2x = 0.5x equity notional) "
          f"and realized_pnl_total accumulation both match hand-computed "
          f"values")


# ---------------------------------------------------------------------------
# h) dry mode — zero orders/brackets/leverage, zero state writes, in BOTH
#    the would-enter and the would-hold cases
# ---------------------------------------------------------------------------


def test_h_dry_mode_zero_side_effects():
    # would-enter
    live, private, state = new_rig()
    result = run_day(live, private, state, BREAKOUT_DAY, dry=True)
    assert "gold_book" not in state, "dry mode must never create/write state"
    assert result["action"] == "would_enter"
    assert result["trail_floor"] == INIT_FLOOR, (
        "dry mode's would-enter preview should compute the SAME initial "
        "floor a real entry would")
    assert private.orders == [], "dry mode must place zero orders"
    assert private.tpsl_calls == [], "dry mode must place zero brackets"
    assert private.leverage_calls == [], "dry mode must never touch leverage"

    # would-hold: enter for REAL first, then dry-run subsequent days
    live2, private2, state2 = test_b_holds_through_noise_floor_unchanged()
    tpsl_before = len(private2.tpsl_calls)
    orders_before = len(private2.orders)
    gb_before = dict(state2["gold_book"])

    result2 = run_day(live2, private2, state2, RATCHET_CONFIRM_DAY, dry=True)
    assert result2["action"] == "would_hold"
    assert result2["trail_floor"] == RATCHET_FLOOR, (
        "dry mode must still compute the REAL ratcheted floor for preview")
    assert len(private2.tpsl_calls) == tpsl_before, (
        "dry mode must never actually replace the bracket, even though "
        "the floor moved")
    assert len(private2.orders) == orders_before
    assert state2["gold_book"] == gb_before, "dry mode must never write state"

    print(f"  [h] OK — dry mode computed a full would-enter preview "
          f"({result['contracts']:.0f} ct, floor ${result['trail_floor']:.2f}) "
          f"AND a full would-hold/ratchet preview (floor "
          f"${result2['trail_floor']:.2f}) with zero orders, zero brackets, "
          f"zero leverage calls, and zero state writes in either case")


# ---------------------------------------------------------------------------
# i) crash-SL fallback — no confirmed protective swing low exists yet
# ---------------------------------------------------------------------------


def test_i_crash_sl_fallback_before_first_confirmed_swing():
    live, private, state = new_rig(full=FALLBACK)
    result = run_day(live, private, state, FALLBACK_ENTRY_DAY)
    assert result["action"] == "entered", result["action"]

    t = state["gold_book"]["open_trade"]
    entry_price = t["entry_price"]
    assert entry_price == 4300.0

    # hand-computed, independent of gold_book._compute_trail_floor
    expected_floor = entry_price * (1 - gold_book.CRASH_SL_PCT)
    assert abs(t["trail_floor"] - expected_floor) < 1e-9, (
        t["trail_floor"], expected_floor)
    assert t["sl_price"] == round(expected_floor, 1)

    tp = private.tpsl_calls[0]
    assert tp["sl_price"] == round(expected_floor, 1)

    print(f"  [i] OK — with zero confirmed protective swing lows as of "
          f"entry, the floor fell back to entry*(1-{gold_book.CRASH_SL_PCT}) "
          f"= ${expected_floor:.2f} (hand-computed independently, matches "
          f"gold_book's own placed bracket exactly)")


TESTS = [
    ("a) breakout entry — order + leverage + initial structure floor",
     test_a_enters_with_order_leverage_and_initial_floor),
    ("b) holds through noise — floor unchanged before the swing confirms",
     test_b_holds_through_noise_floor_unchanged),
    ("c) floor RATCHETS UP — bracket cancelled + replaced on the exchange",
     test_c_floor_ratchets_up_and_bracket_replaced),
    ("d) floor never moves down after the ratchet",
     test_d_floor_never_moves_down_after_ratchet),
    ("e) exit fires via reconcile — correct PnL, zero new orders",
     test_e_exit_fires_via_reconcile_with_correct_pnl),
    ("f) idempotent — same bar twice = no duplicate brackets",
     test_f_idempotent_same_bar_twice_no_duplicate_brackets),
    ("g) ledger math — sizing formula + realized_pnl_total",
     test_g_ledger_math),
    ("h) dry mode — zero side effects, would-enter AND would-hold",
     test_h_dry_mode_zero_side_effects),
    ("i) crash-SL fallback before the first confirmed swing",
     test_i_crash_sl_fallback_before_first_confirmed_swing),
]


def main():
    print("=" * 78)
    print(f"test_gold_book.py — synthetic breakout at bar {BREAKOUT_DAY}, "
          f"second swing confirms at bar {RATCHET_CONFIRM_DAY} — "
          f"STRUCTURE-TRAILING exit architecture (round 59)")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {e}")
            traceback.print_exc()
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
    print("\n" + "=" * 78)
    if failed:
        print(f"{failed}/{len(TESTS)} TEST(S) FAILED")
        sys.exit(1)
    else:
        print(f"ALL {len(TESTS)} TESTS PASSED")


if __name__ == "__main__":
    main()
