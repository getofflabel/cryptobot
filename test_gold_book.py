"""
test_gold_book.py — offline tests for gold_book.py's donchian55/EMA20 paper
book: entry on the breakout bar, holding through noise, exit on the first
EMA20 breakdown, idempotency (same bar processed twice = one trade), and
correct cost-adjusted equity math. NO NETWORK — the data loader and every
Telegram/log/state side effect are monkeypatched offline.

Run with:  python3 test_gold_book.py
"""

from __future__ import annotations

import sys
import traceback

import pandas as pd

import gold_book
import step48_tradfi_trend as s48
import step5_paper_trade as s5


def _noop(*a, **kw):
    pass


def make_synthetic() -> pd.DataFrame:
    """A daily OHLC series with a clean, unambiguous donchian55 breakout
    followed by an EMA20 breakdown:
      bars   0..59  : flat noise around $100 (warmup — donchian55 needs 55
                       prior bars, EMA20 needs to settle near $100 too)
      bar    60      : jumps to $130 — breaks the ~$100 55-day high
      bars   61..70  : eases back slightly (125 -> 116) but stays well
                       above a still-catching-up EMA20 — holds the position
                       through ordinary noise
      bars   71..80  : crashes to $70 and stays there — EMA20 is breached
                       hard on bar 71, forcing an exit
    open == high == low == close on every bar: donchian_ema_exit only reads
    'high' and 'close', and this keeps the breakout/exit levels unambiguous
    (no intrabar wicks to reason about).
    """
    import numpy as np
    rng = np.random.default_rng(7)
    closes = list(100.0 + rng.normal(0, 0.4, 60))   # bars 0..59, flat noise
    closes.append(130.0)                             # bar 60: breakout
    # bars 61..70: ease down from 125 to 116, still far above EMA20
    closes += list(np.linspace(125.0, 116.0, 10))
    # bars 71..80: crash and stay down, well below EMA20
    closes += [70.0] * 10

    dates = pd.date_range("2020-01-01", periods=len(closes), freq="B",
                           tz="UTC")
    df = pd.DataFrame({
        "timestamp": dates,
        "open": closes, "high": closes, "low": closes, "close": closes,
        "volume": [5_000_000.0] * len(closes),
    })
    return df


FULL = make_synthetic()

# Let the imported, validated function itself be the oracle for WHICH bars
# are the entry/exit bars — never hand-guessed — so the test can never
# silently drift from the real rule.
_oracle_sig = s48.donchian_ema_exit(FULL, gold_book.ENTRY_N,
                                    ema_n=gold_book.EMA_N)
ENTRY_DAY = int(_oracle_sig[_oracle_sig > 0].index[0])
EXIT_DAY = int(_oracle_sig.iloc[ENTRY_DAY:][_oracle_sig.iloc[ENTRY_DAY:] == 0]
              .index[0])
assert ENTRY_DAY == 60, f"synthetic data should break out on bar 60, got {ENTRY_DAY}"
assert EXIT_DAY > ENTRY_DAY, "exit must come after entry"


def install_offline(state):
    """Neutralize every network/Telegram/state side effect so the test can
    run with zero network and never touch the real bot_state.json."""
    s5.notify = _noop
    s5.log_event = _noop
    s5.save_state = _noop
    s5.CLOUD_STATE = False


def make_state():
    return {}


def run_day(state, day_idx, dry=False):
    """Monkeypatch the loader to return only bars [0..day_idx] — exactly
    what a real daily bot would see on that day — then run one cycle."""
    gold_book._load_gld_daily = lambda: FULL.iloc[:day_idx + 1].reset_index(drop=True)
    return gold_book.run_gold_book(state, dry=dry)


def test_a_enters_on_breakout_bar_at_its_close():
    state = make_state()
    install_offline(state)

    result = run_day(state, ENTRY_DAY)
    assert result["action"] == "entered", f"expected entry, got {result['action']}"

    gb = state["gold_book"]
    t = gb["open_trade"]
    assert t is not None, "should have an open trade after the breakout"
    breakout_close = float(FULL["close"].iloc[ENTRY_DAY])
    breakout_date = str(FULL["timestamp"].iloc[ENTRY_DAY].date())
    assert t["entry_date"] == breakout_date, (
        f"entry should be dated the breakout bar {breakout_date}, "
        f"got {t['entry_date']}")

    costs = s48.costs_for("GLD")
    expected_entry_price = costs.fill_price(breakout_close, +1)
    assert abs(t["entry_price"] - expected_entry_price) < 1e-6, (
        f"entry fill should be the breakout bar's close, cost-adjusted: "
        f"expected {expected_entry_price}, got {t['entry_price']}")
    print(f"  [a] OK — entered {breakout_date} @ {t['entry_price']:.4f} "
          f"(breakout close {breakout_close:.2f})")
    return state


def test_b_holds_through_noise():
    state = test_a_enters_on_breakout_bar_at_its_close()
    open_trade_at_entry = dict(state["gold_book"]["open_trade"])

    # step through several noisy bars between entry and the eventual exit —
    # the position must NOT be touched (no re-entry, no premature exit).
    for day_idx in range(ENTRY_DAY + 1, EXIT_DAY):
        result = run_day(state, day_idx)
        assert result["action"] == "hold", (
            f"day {day_idx}: expected hold (still in, signal still in), "
            f"got {result['action']}")
        assert state["gold_book"]["open_trade"] == open_trade_at_entry, (
            f"day {day_idx}: open trade must be untouched through noise")
        assert state["gold_book"]["trades"] == [], (
            "no trade should be booked while still holding")
    print(f"  [b] OK — held unchanged through bars "
          f"{ENTRY_DAY + 1}..{EXIT_DAY - 1} ({EXIT_DAY - ENTRY_DAY - 1} bars "
          f"of noise)")
    return state


def test_c_exits_on_first_close_below_ema20_with_correct_pnl_sign():
    state = test_b_holds_through_noise()
    t_before = dict(state["gold_book"]["open_trade"])

    result = run_day(state, EXIT_DAY)
    assert result["action"] == "exited", f"expected exit, got {result['action']}"

    gb = state["gold_book"]
    assert gb["open_trade"] is None, "position should be flat after the exit"
    assert len(gb["trades"]) == 1, "exactly one trade should be booked"
    trade = gb["trades"][0]

    exit_close = float(FULL["close"].iloc[EXIT_DAY])
    assert exit_close < t_before["entry_price"], (
        "synthetic data should be a clear loser — exit close crashed well "
        "below the entry price")
    assert trade["pnl"] < 0, (
        f"a crash-exit below a breakout entry must be a LOSS, got "
        f"pnl={trade['pnl']}")
    print(f"  [c] OK — exited {trade['exit_date']} @ {trade['exit_price']:.4f}, "
          f"pnl ${trade['pnl']:+,.2f} (correctly negative)")
    return state


def test_d_idempotent_same_bar_twice_is_one_trade():
    state = test_c_exits_on_first_close_below_ema20_with_correct_pnl_sign()
    trades_before = list(state["gold_book"]["trades"])
    equity_before = state["gold_book"]["equity"]

    # re-run the SAME day (EXIT_DAY) again — must be a pure no-op
    result = run_day(state, EXIT_DAY)
    assert result["action"] == "noop_already_processed", (
        f"reprocessing the same bar must no-op, got {result['action']}")
    assert state["gold_book"]["trades"] == trades_before, (
        "reprocessing the same bar must NOT add a second trade")
    assert state["gold_book"]["equity"] == equity_before, (
        "reprocessing the same bar must NOT move equity again")

    # also re-run the ENTRY day again from a fresh state — must not double-enter
    state2 = make_state()
    install_offline(state2)
    run_day(state2, ENTRY_DAY)
    trade_after_first = dict(state2["gold_book"]["open_trade"])
    result2 = run_day(state2, ENTRY_DAY)
    assert result2["action"] == "noop_already_processed"
    assert state2["gold_book"]["open_trade"] == trade_after_first, (
        "reprocessing the entry bar must not re-enter or resize")
    print("  [d] OK — same bar processed twice produced exactly one trade "
          "(and one entry), both times")
    return state


def test_e_equity_updates_correctly_with_costs():
    state = make_state()
    install_offline(state)
    costs = s48.costs_for("GLD")

    run_day(state, ENTRY_DAY)
    t = state["gold_book"]["open_trade"]
    entry_price = t["entry_price"]
    shares = t["shares"]
    notional = t["notional"]
    expected_entry_fee = costs.fee(shares * entry_price)
    expected_equity_after_entry = round(
        gold_book.START_EQUITY - expected_entry_fee, 2)
    assert notional == gold_book.START_EQUITY, (
        "full-notional sizing should deploy the ENTIRE paper equity")
    assert abs(shares * entry_price - notional) < 1e-6, (
        "shares * entry_price must reconstruct the notional exactly "
        "(full-notional sizing)")
    assert state["gold_book"]["equity"] == expected_equity_after_entry, (
        f"equity after entry should be START_EQUITY minus the entry fee: "
        f"expected {expected_equity_after_entry}, "
        f"got {state['gold_book']['equity']}")

    for day_idx in range(ENTRY_DAY + 1, EXIT_DAY):
        run_day(state, day_idx)
    run_day(state, EXIT_DAY)

    exit_close = float(FULL["close"].iloc[EXIT_DAY])
    expected_exit_price = costs.fill_price(exit_close, -1)
    expected_gross = shares * (expected_exit_price - entry_price)
    expected_exit_fee = costs.fee(shares * expected_exit_price)
    expected_realized = round(expected_gross - expected_exit_fee, 2)
    expected_final_equity = round(
        expected_equity_after_entry + expected_realized, 2)

    trade = state["gold_book"]["trades"][0]
    assert trade["pnl"] == expected_realized, (
        f"realized pnl should match manual cost-adjusted calc: expected "
        f"{expected_realized}, got {trade['pnl']}")
    assert state["gold_book"]["equity"] == expected_final_equity, (
        f"final equity should be entry-fee-adjusted equity plus realized "
        f"pnl: expected {expected_final_equity}, got "
        f"{state['gold_book']['equity']}")
    print(f"  [e] OK — equity ${gold_book.START_EQUITY:,.2f} -> "
          f"${expected_equity_after_entry:,.2f} (entry fee "
          f"${expected_entry_fee:.2f}) -> ${state['gold_book']['equity']:,.2f} "
          f"(realized ${expected_realized:+,.2f}), all cost-adjusted math "
          f"matches exactly")


def test_f_dry_mode_makes_no_side_effects():
    state = make_state()
    install_offline(state)
    # dry mode against a state with NO gold_book key yet
    result = run_day(state, ENTRY_DAY, dry=True)
    assert "gold_book" not in state, (
        "dry mode must never create/write state — even the setdefault "
        "book key must stay absent")
    assert result["action"] == "would_enter"
    print("  [f] OK — dry mode computed a full decision with zero state "
          "writes")


TESTS = [
    ("a) enters on breakout bar at its close",
     test_a_enters_on_breakout_bar_at_its_close),
    ("b) holds through noise", test_b_holds_through_noise),
    ("c) exits on first close<EMA20, correct PnL sign",
     test_c_exits_on_first_close_below_ema20_with_correct_pnl_sign),
    ("d) idempotent — same bar twice = one trade",
     test_d_idempotent_same_bar_twice_is_one_trade),
    ("e) equity updates correctly with costs",
     test_e_equity_updates_correctly_with_costs),
    ("f) dry mode has zero side effects",
     test_f_dry_mode_makes_no_side_effects),
]


def main():
    print("=" * 78)
    print(f"test_gold_book.py — synthetic breakout at bar {ENTRY_DAY}, "
          f"EMA20 breakdown at bar {EXIT_DAY} (oracle: the real, imported "
          f"donchian_ema_exit)")
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
