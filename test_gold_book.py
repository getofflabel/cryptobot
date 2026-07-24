"""
test_gold_book.py — offline tests for gold_book.py's REAL-ORDER
donchian55/EMA20 book (round-51 rewire). NO NETWORK: a fake private client
and a fake candle/ticker/instrument feed stand in for BloFin; every
Telegram/log/state side effect on step5_paper_trade is monkeypatched to a
no-op, exactly like the pre-rewire test did.

Seven intents:
  a) breakout entry — correct market order + leverage + crash-insurance SL
  b) holds through noise (no new orders, position untouched)
  c) EMA20 exit — reduce-only close, tpsl cancelled, correct PnL sign
  d) idempotent — same bar processed twice = one trade, no duplicate orders
  e) ledger math — sizing formula (25% alloc x 2x lev / contract math) and
     realized_pnl_total bookkeeping match a hand computation
  f) dry mode — zero orders, zero state writes
  g) reconcile — exchange shows the position gone (crash SL fired) while
     the book still thinks it's open -> books the exit from the fill,
     notifies, never places a redundant order

Run with:  python3 test_gold_book.py
"""

from __future__ import annotations

import sys
import traceback
from types import SimpleNamespace

import pandas as pd

import gold_book
import step48_tradfi_trend as s48
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
    currently be quoting) — market_order() fills against it."""

    def __init__(self):
        self.mark_price = 0.0
        self.position = 0.0        # signed contracts, long-only in practice
        self.leverage_calls = []
        self.orders = []           # list of dicts
        self.tpsl_calls = []       # list of dicts
        self.cancelled_tpsl = []
        self._next_oid = 1
        self._last_fill_price = None
        self.fail_market_order = False
        self.fail_net_read = False

    def net_position_contracts(self, symbol):
        if self.fail_net_read:
            raise RuntimeError("simulated read failure")
        return self.position

    def ensure_leverage(self, symbol, leverage, margin_mode="cross"):
        self.leverage_calls.append((symbol, leverage, margin_mode))
        return True

    def market_order(self, symbol, side, contracts, reduce_only=False,
                     margin_mode="cross"):
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
                   sl_price, margin_mode="cross"):
        tid = f"tpsl{len(self.tpsl_calls) + 1}"
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
# Synthetic data — same shape as the pre-rewire test: warmup, breakout,
# noise, crash. The imported donchian_ema_exit is the oracle for which bars
# are entry/exit, never hand-guessed.
# ---------------------------------------------------------------------------


def make_synthetic() -> pd.DataFrame:
    import numpy as np
    rng = np.random.default_rng(7)
    closes = list(4000.0 + rng.normal(0, 4.0, 60))    # bars 0..59, warmup
    closes.append(4300.0)                              # bar 60: breakout
    closes += list(np.linspace(4230.0, 4150.0, 10))     # 61..70: ease down
    closes += [3600.0] * 10                             # 71..80: crash

    dates = pd.date_range("2025-01-01", periods=len(closes), freq="D",
                          tz="UTC")
    return pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes,
        "volume": [500.0] * len(closes),
    })


FULL = make_synthetic()

_oracle_sig = s48.donchian_ema_exit(FULL, gold_book.ENTRY_N,
                                    ema_n=gold_book.EMA_N)
ENTRY_DAY = int(_oracle_sig[_oracle_sig > 0].index[0])
EXIT_DAY = int(_oracle_sig.iloc[ENTRY_DAY:][_oracle_sig.iloc[ENTRY_DAY:] == 0]
              .index[0])
# ENTRY_DAY is derived from the ORACLE (the real imported strategy fn with
# the book's live ENTRY_N), never hardcoded — so changing ENTRY_N (55 -> 20
# on 2026-07-24) cannot silently break the suite. We only require that the
# synthetic series produces exactly one well-formed trade to test against.
assert ENTRY_DAY is not None and ENTRY_DAY >= gold_book.ENTRY_N, (
    f"synthetic data must break out after warmup (ENTRY_N={gold_book.ENTRY_N}), got {ENTRY_DAY}")
assert EXIT_DAY > ENTRY_DAY, "exit must come after entry"

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


def new_rig():
    install_offline()
    live = FakeLiveFeed(FULL)
    private = FakePrivate()
    state = make_state()
    return live, private, state


# ---------------------------------------------------------------------------
# a) breakout entry
# ---------------------------------------------------------------------------


def test_a_enters_on_breakout_with_order_and_sl():
    live, private, state = new_rig()
    result = run_day(live, private, state, ENTRY_DAY)
    assert result["action"] == "entered", f"expected entry, got {result['action']}"

    gb = state["gold_book"]
    t = gb["open_trade"]
    assert t is not None, "should have an open trade after the breakout"
    breakout_date = str(FULL["timestamp"].iloc[ENTRY_DAY].date())
    assert t["entry_date"] == breakout_date

    # exactly one market order, a BUY, not reduce-only
    assert len(private.orders) == 1, private.orders
    order = private.orders[0]
    assert order["side"] == "buy" and not order["reduce_only"]
    assert order["symbol"] == gold_book.SYMBOL

    # leverage was set to GOLD_LEV before the order
    assert private.leverage_calls == [(gold_book.SYMBOL, gold_book.GOLD_LEV, "cross")]

    # sizing matches the 25%-alloc / 2x-lev formula, whole-contract lot
    ref_price = float(FULL["close"].iloc[ENTRY_DAY])
    exp_contracts = expected_contracts(ref_price)
    assert order["contracts"] == exp_contracts, (order["contracts"], exp_contracts)
    assert t["contracts"] == exp_contracts
    assert float(t["contracts"]).is_integer(), "lotSize=1 -> whole contracts only"

    # crash-insurance SL placed: no TP, sl = entry * (1 - 18%)
    assert len(private.tpsl_calls) == 1, private.tpsl_calls
    tp = private.tpsl_calls[0]
    assert tp["position_side_close"] == "sell"
    assert tp["tp_price"] is None, "no take-profit — winners must run"
    expected_sl = round(t["entry_price"] * (1 - gold_book.CRASH_SL_PCT), 1)
    assert abs(tp["sl_price"] - expected_sl) < 1e-6, (tp["sl_price"], expected_sl)
    assert t["sl_price"] == expected_sl

    print(f"  [a] OK — entered {breakout_date} @ {t['entry_price']:.2f}, "
          f"{t['contracts']:.0f} ct, lev={gold_book.GOLD_LEV:.0f}x, "
          f"SL {t['sl_price']:.2f} (no TP)")
    return live, private, state


# ---------------------------------------------------------------------------
# b) holds through noise
# ---------------------------------------------------------------------------


def test_b_holds_through_noise():
    live, private, state = test_a_enters_on_breakout_with_order_and_sl()
    open_trade_at_entry = dict(state["gold_book"]["open_trade"])
    orders_at_entry = len(private.orders)

    for day_idx in range(ENTRY_DAY + 1, EXIT_DAY):
        result = run_day(live, private, state, day_idx)
        assert result["action"] == "hold", (
            f"day {day_idx}: expected hold, got {result['action']}")
        assert state["gold_book"]["open_trade"] == open_trade_at_entry, (
            f"day {day_idx}: open trade must be untouched through noise")
        assert len(private.orders) == orders_at_entry, (
            "no new orders should be placed while holding")
        assert state["gold_book"]["trades"] == []

    print(f"  [b] OK — held unchanged through bars "
          f"{ENTRY_DAY + 1}..{EXIT_DAY - 1}, zero new orders")
    return live, private, state


# ---------------------------------------------------------------------------
# c) EMA20 exit
# ---------------------------------------------------------------------------


def test_c_exits_on_ema20_break_reduce_only_correct_pnl():
    live, private, state = test_b_holds_through_noise()
    t_before = dict(state["gold_book"]["open_trade"])
    orders_before = len(private.orders)

    result = run_day(live, private, state, EXIT_DAY)
    assert result["action"] == "exited", f"expected exit, got {result['action']}"

    gb = state["gold_book"]
    assert gb["open_trade"] is None, "should be flat after the exit"
    assert len(gb["trades"]) == 1
    trade = gb["trades"][0]

    # exactly one NEW order: reduce-only sell for the exact recorded size
    assert len(private.orders) == orders_before + 1
    exit_order = private.orders[-1]
    assert exit_order["side"] == "sell" and exit_order["reduce_only"]
    assert exit_order["contracts"] == t_before["contracts"]

    # the crash-insurance bracket was cancelled on the way out
    assert private.cancelled_tpsl == [t_before["tpsl_id"]]

    exit_close = float(FULL["close"].iloc[EXIT_DAY])
    assert exit_close < t_before["entry_price"], (
        "synthetic data should be a clear loser")
    assert trade["pnl"] < 0, f"crash-exit below breakout entry must lose, got {trade['pnl']}"

    # hand-check the PnL math
    size_units = t_before["contracts"] * t_before["contract_value"]
    gross = size_units * (exit_close - t_before["entry_price"])
    fees = (t_before["entry_price"] * gold_book.ENTRY_FEE_BPS
            + exit_close * gold_book.EXIT_FEE_BPS) * size_units / 10_000
    expected_pnl = round(gross - fees, 2)
    assert trade["pnl"] == expected_pnl, (trade["pnl"], expected_pnl)
    assert gb["realized_pnl_total"] == expected_pnl

    print(f"  [c] OK — exited {trade['exit_date']} @ {trade['exit_price']:.2f}, "
          f"pnl ${trade['pnl']:+,.2f} (correctly negative), reduce-only "
          f"order placed, SL bracket cancelled")
    return live, private, state


# ---------------------------------------------------------------------------
# d) idempotency
# ---------------------------------------------------------------------------


def test_d_idempotent_same_bar_twice_is_one_trade():
    live, private, state = test_c_exits_on_ema20_break_reduce_only_correct_pnl()
    trades_before = list(state["gold_book"]["trades"])
    orders_before = len(private.orders)

    result = run_day(live, private, state, EXIT_DAY)
    assert result["action"] == "noop_already_processed", result["action"]
    assert state["gold_book"]["trades"] == trades_before
    assert len(private.orders) == orders_before, "must not place a duplicate order"

    live2, private2, state2 = new_rig()
    run_day(live2, private2, state2, ENTRY_DAY)
    trade_after_first = dict(state2["gold_book"]["open_trade"])
    orders_after_first = len(private2.orders)
    result2 = run_day(live2, private2, state2, ENTRY_DAY)
    assert result2["action"] == "noop_already_processed"
    assert state2["gold_book"]["open_trade"] == trade_after_first
    assert len(private2.orders) == orders_after_first, "must not double-enter"

    print("  [d] OK — same bar processed twice produced exactly one trade "
          "(and one entry), no duplicate orders either time")
    return live, private, state


# ---------------------------------------------------------------------------
# e) ledger math
# ---------------------------------------------------------------------------


def test_e_ledger_math():
    live, private, state = new_rig()
    ref_price = float(FULL["close"].iloc[ENTRY_DAY])
    exp_contracts = expected_contracts(ref_price)
    exp_notional = round(exp_contracts * FakeLiveFeed.CONTRACT_VALUE * ref_price, 2)

    # hand-check the formula itself: 25% alloc x 2x lev == 0.5x equity notional
    raw_notional = STARTING_EQUITY * gold_book.GOLD_ALLOC * gold_book.GOLD_LEV
    assert abs(raw_notional - STARTING_EQUITY * 0.5) < 1e-9, (
        "25% alloc x 2x leverage must equal 0.5x equity notional")

    run_day(live, private, state, ENTRY_DAY)
    t = state["gold_book"]["open_trade"]
    assert t["contracts"] == exp_contracts
    assert abs(t["notional"] - exp_notional) <= exp_contracts * FakeLiveFeed.CONTRACT_VALUE, (
        "notional should reconstruct from contracts*contract_value*entry_price")

    for day_idx in range(ENTRY_DAY + 1, EXIT_DAY):
        run_day(live, private, state, day_idx)
    run_day(live, private, state, EXIT_DAY)

    trade = state["gold_book"]["trades"][0]
    assert state["gold_book"]["realized_pnl_total"] == trade["pnl"], (
        "realized_pnl_total should equal the sum of booked trades "
        "(one trade here)")

    # second round trip accumulates rather than overwrites
    live3, private3, state3 = new_rig()
    state3["gold_book"] = dict(state["gold_book"])
    state3["gold_book"]["trades"] = list(state["gold_book"]["trades"])
    prior_total = state3["gold_book"]["realized_pnl_total"]
    run_day(live3, private3, state3, ENTRY_DAY)
    for day_idx in range(ENTRY_DAY + 1, EXIT_DAY):
        run_day(live3, private3, state3, day_idx)
    run_day(live3, private3, state3, EXIT_DAY)
    assert len(state3["gold_book"]["trades"]) == 2
    second_pnl = state3["gold_book"]["trades"][1]["pnl"]
    assert state3["gold_book"]["realized_pnl_total"] == round(
        prior_total + second_pnl, 2), "realized_pnl_total must ACCUMULATE"

    print(f"  [e] OK — sizing formula (25% x 2x = 0.5x equity notional) "
          f"and realized_pnl_total accumulation both match hand-computed "
          f"values")


# ---------------------------------------------------------------------------
# f) dry mode
# ---------------------------------------------------------------------------


def test_f_dry_mode_zero_side_effects():
    live, private, state = new_rig()
    result = run_day(live, private, state, ENTRY_DAY, dry=True)
    assert "gold_book" not in state, (
        "dry mode must never create/write state")
    assert result["action"] == "would_enter"
    assert private.orders == [], "dry mode must place zero orders"
    assert private.tpsl_calls == [], "dry mode must place zero SL brackets"
    assert private.leverage_calls == [], "dry mode must never touch leverage"
    print("  [f] OK — dry mode computed a full decision "
          f"({result['contracts']:.0f} ct would-enter) with zero orders "
          "and zero state writes")


# ---------------------------------------------------------------------------
# g) reconcile: crash SL fired between cycles
# ---------------------------------------------------------------------------


def test_g_reconcile_books_sl_fired_exit():
    live, private, state = test_a_enters_on_breakout_with_order_and_sl()
    t = dict(state["gold_book"]["open_trade"])
    orders_before = len(private.orders)

    # simulate the crash-insurance SL firing on the exchange: the position
    # is just gone, and the exchange's own fill was at the SL price.
    private.position = 0.0
    private.mark_price = t["sl_price"]
    private._last_fill_price = t["sl_price"]

    result = run_day(live, private, state, ENTRY_DAY + 1)
    assert result["action"] == "reconciled_sl_exit", result["action"]
    assert state["gold_book"]["open_trade"] is None
    assert len(state["gold_book"]["trades"]) == 1
    trade = state["gold_book"]["trades"][0]
    assert trade["reason"] == "sl_fired"
    assert trade["exit_price"] == t["sl_price"]

    # crucially: NO new order was placed to "chase" a position that's
    # already gone — reconcile only ever books the ledger line
    assert len(private.orders) == orders_before, (
        "reconcile must never place an order — the exchange already did "
        "the closing")

    size_units = t["contracts"] * t["contract_value"]
    gross = size_units * (t["sl_price"] - t["entry_price"])
    fees = (t["entry_price"] * gold_book.ENTRY_FEE_BPS
            + t["sl_price"] * gold_book.EXIT_FEE_BPS) * size_units / 10_000
    expected_pnl = round(gross - fees, 2)
    assert trade["pnl"] == expected_pnl
    assert trade["pnl"] < 0, "an 18% crash SL must be a clear loss"

    print(f"  [g] OK — reconcile detected the exchange net gone, booked "
          f"the SL-fired exit @ {trade['exit_price']:.2f} (pnl "
          f"${trade['pnl']:+,.2f}) from the fill, placed ZERO new orders")


TESTS = [
    ("a) breakout entry — order + leverage + crash SL",
     test_a_enters_on_breakout_with_order_and_sl),
    ("b) holds through noise", test_b_holds_through_noise),
    ("c) EMA20 exit — reduce-only + correct PnL",
     test_c_exits_on_ema20_break_reduce_only_correct_pnl),
    ("d) idempotent — same bar twice = one trade, no dup orders",
     test_d_idempotent_same_bar_twice_is_one_trade),
    ("e) ledger math — sizing formula + realized_pnl_total",
     test_e_ledger_math),
    ("f) dry mode — zero orders, zero state writes",
     test_f_dry_mode_zero_side_effects),
    ("g) reconcile — books an SL-fired exit, no chase order",
     test_g_reconcile_books_sl_fired_exit),
]


def main():
    print("=" * 78)
    print(f"test_gold_book.py — synthetic breakout at bar {ENTRY_DAY}, "
          f"EMA20 breakdown at bar {EXIT_DAY} (oracle: the real, imported "
          f"donchian_ema_exit) — REAL-ORDER architecture (round 51)")
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
