"""
step51_gold_smoke.py — local smoke test for gold_book.py.

Pulls the REAL cached/fresh GLD daily bars (via gold_book's own loader —
same yfinance-backed cache step48_tradfi_trend.py uses,
data_tradfi_GLD_1d.parquet), then runs gold_book.run_gold_book ONCE with
dry=True: it computes and prints the full donchian55/EMA20 decision (the
55-day high, EMA20, in/out, would-enter/exit + sizing) but makes NO state
writes, NO log_event, NO Telegram notify (enforced inside run_gold_book
itself — the dry branch returns before any of those calls happen).

Prints, in order:
  1. the real GLD data span now cached / just pulled
  2. current gold_book state (before the dry run) — equity, open trade
  3. what the book WOULD do right now: latest bar, 55-day high, EMA20,
     in/out signal, and (if flat+signal-in or in+signal-out) the exact
     entry/exit it would take
  4. proof the dry run made zero state writes (reload from source of truth)

Run:  python3 step51_gold_smoke.py
"""

from __future__ import annotations

from gold_book import _decision, _load_gld_daily
from step5_paper_trade import load_state


def main():
    print("=" * 78)
    print("GOLD BOOK SMOKE TEST — real cached/fresh GLD daily data, dry run")
    print("=" * 78)

    # -- 1. the real data -------------------------------------------------
    d = _load_gld_daily()
    print(f"\nGLD daily bars: {len(d)}, "
          f"{d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")

    dec = _decision(d)
    hi55_str = f"${dec['hi55']:.2f}" if dec["hi55"] is not None else "n/a"
    print(f"\nlatest CLOSED bar   : {dec['bar_date']}")
    print(f"latest close        : ${dec['close']:.2f}")
    print(f"55-day high (shift1): {hi55_str}")
    print(f"EMA20 of close      : ${dec['ema20']:.2f}")
    print(f"donchian55/EMA20 signal right now: "
          f"{'IN A BREAKOUT (long)' if dec['desired_in'] else 'FLAT (waiting for a breakout)'}")

    # -- 2. current state, before the dry run ------------------------------
    from gold_book import START_EQUITY
    state = load_state()
    gb_before = state.get("gold_book", {})
    equity = gb_before.get("equity", START_EQUITY)
    open_trade_before = gb_before.get("open_trade")
    print(f"\ngold_book equity (pre-run) : ${equity:,.2f}")
    print(f"gold_book open_trade       : {open_trade_before}")
    print(f"gold_book last_bar_date    : {gb_before.get('last_bar_date')}")
    print(f"gold_book trades booked    : {len(gb_before.get('trades', []))}")

    # -- 3. what the book would do now -------------------------------------
    from gold_book import run_gold_book
    print("\n--- run_gold_book(state, dry=True) ---")
    result = run_gold_book(state, dry=True)
    print("--- end run_gold_book ---\n")
    print(f"DECISION SUMMARY: {result}")

    have_position = open_trade_before is not None
    if not have_position and dec["desired_in"]:
        print("\n>>> RIGHT NOW: GLD is IN A DONCHIAN-55 BREAKOUT. The real "
              "book would go LONG on the next live cycle. <<<")
    elif have_position and not dec["desired_in"]:
        print("\n>>> RIGHT NOW: the open trade's close is BELOW EMA20. The "
              "real book would EXIT on the next live cycle. <<<")
    elif have_position:
        print("\n>>> RIGHT NOW: holding an open long, still above EMA20 — "
              "no action. <<<")
    else:
        print("\n>>> RIGHT NOW: flat, no breakout — waiting. <<<")

    # -- 4. prove dry mode made no state changes -----------------------------
    state_after = load_state()
    gb_after = state_after.get("gold_book", {})
    unchanged = (gb_before.get("open_trade") == gb_after.get("open_trade")
                and gb_before.get("last_bar_date") == gb_after.get("last_bar_date")
                and gb_before.get("equity", START_EQUITY)
                    == gb_after.get("equity", START_EQUITY)
                and gb_before.get("trades", []) == gb_after.get("trades", []))
    print(f"\nstate unchanged by dry run: {'YES' if unchanged else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
