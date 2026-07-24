"""
step51_gold_smoke.py — REAL BloFin smoke test for gold_book.py (round-51
rewire: real demo orders, replacing the old yfinance/paper-sim smoke).

READ-ONLY + DRY: pulls the REAL BloFin instrument spec, REAL candles (via
config.make_exchange("live"), the prod market-data host), and the REAL
current net position on the demo account (config.make_exchange("demo") +
BlofinDemoPrivate — a read, never a write), then runs
gold_book.run_gold_book(private, live_feed, state, dry=True) ONCE. Dry mode
places NO order, sets NO leverage, and makes NO state/log/notify side
effect — enforced inside run_gold_book itself.

Prints, in order:
  1. the XAU-USDT/XAUT-USDT instrument spec found on BloFin (both hosts)
  2. the real candle history pulled and its span
  3. current price, ENTRY_N-day high, EMA20 (informational only — round 59
     retired it as the exit; see gold_book's ROUND 59 EXIT SWAP), breakout
     signal
  4. the CURRENT STRUCTURE-TRAILING FLOOR if a trade is open (round 59:
     gold_book._compute_trail_floor — the sealed-validated exit; there is
     no more book-computed "would-exit", the exchange's own bracket owns
     that), what the book WOULD do right now (would-enter sizing / would-
     hold + floor preview / stay flat), and the current live account
     position
  5. proof the dry run made zero state writes (reload from source of truth)

Run:  python3 step51_gold_smoke.py
"""

from __future__ import annotations

import config
from blofin_private import BlofinDemoPrivate, load_env


def main():
    print("=" * 78)
    print("GOLD BOOK SMOKE TEST (round 51) — REAL BloFin data, dry run, "
          "zero orders")
    print("=" * 78)

    env = load_env()
    live_feed, _ = config.make_exchange("live")
    demo_feed, _ = config.make_exchange("demo")

    import gold_book

    # -- 0. instrument spec, straight from BloFin ---------------------------
    print(f"\n-- instrument spec for {gold_book.SYMBOL} --")
    try:
        raw_spec = live_feed.get_instrument(gold_book.SYMBOL)
        print(f"  found on PROD instruments endpoint: {raw_spec}")
    except Exception as e:
        print(f"  prod instrument lookup failed: {str(e)[:150]}")
        raw_spec = None
    try:
        demo_spec = demo_feed.get_instrument(gold_book.SYMBOL)
        print(f"  found on DEMO instruments endpoint: {demo_spec}")
    except Exception as e:
        print(f"  demo instrument lookup failed: {str(e)[:150]}")

    try:
        xau_spec = live_feed.get_instrument("XAU-USDT")
        print(f"  (for context) XAU-USDT on PROD instruments: {xau_spec}")
    except Exception as e:
        print(f"  (for context) XAU-USDT lookup on prod failed: {str(e)[:120]}")
    try:
        demo_feed.get_instrument("XAU-USDT")
        print("  (for context) XAU-USDT IS listed on DEMO too")
    except Exception as e:
        print(f"  (for context) XAU-USDT on DEMO: {str(e)[:150]}")

    spec = gold_book._instrument_spec(live_feed)
    print(f"  parsed for order math: contract_value={spec['contract_value']} "
          f"min_size={spec['min_size']} lot_size={spec['lot_size']} "
          f"tick_size={spec['tick_size']}")

    # -- 1. real candle history ----------------------------------------------
    d = gold_book._load_daily(live_feed)
    print(f"\n{gold_book.SYMBOL} daily bars: {len(d)}, "
          f"{d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")

    dec = gold_book._decision(d)
    hi_str = f"${dec['hi55']:.2f}" if dec["hi55"] is not None else "n/a"
    print(f"\nlatest CLOSED bar        : {dec['bar_date']}")
    print(f"latest close             : ${dec['close']:.2f}")
    print(f"{gold_book.ENTRY_N}-day high (shift1)     : {hi_str}")
    print(f"EMA20 of close (info only, no longer drives any exit — see "
          f"gold_book's ROUND 59 EXIT SWAP): ${dec['ema20']:.2f}")
    print(f"donchian{gold_book.ENTRY_N} breakout right now: "
          f"{'YES — fresh breakout today' if dec['desired_in'] else 'no'}")

    # -- 2. current state + real account position ----------------------------
    from gold_book import _fresh_book
    from step5_paper_trade import load_state
    state = load_state()
    gb_raw_before = state.get("gold_book")     # RAW, for the no-write proof below
    gb_before = gb_raw_before
    if gb_before is None or "realized_pnl_total" not in gb_before:
        gb_before = _fresh_book()
    open_trade = gb_before.get("open_trade")
    print(f"\ngold_book open_trade       : {open_trade}")
    print(f"gold_book last_bar_date    : {gb_before.get('last_bar_date')}")
    print(f"gold_book trades booked    : {len(gb_before.get('trades', []))}")
    print(f"gold_book realized_pnl_total: ${gb_before.get('realized_pnl_total', 0.0):+,.2f}")
    print(f"shared ledger virtual_equity: ${state.get('virtual_equity', 0):,.2f}")

    # STRUCTURE-TRAILING floor (round 59): recomputed fresh, exactly like
    # gold_book.run_gold_book does every cycle while holding — see
    # gold_book._compute_trail_floor's docstring for the ratchet/fallback
    # rule this mirrors from step59_exit_science's sealed-validated X3.
    current_floor = None
    if open_trade is not None:
        current_floor = gold_book._compute_trail_floor(
            d, gold_book._entry_date_of(open_trade), open_trade["entry_price"])
        moved = (open_trade.get("trail_floor") is None
                or current_floor > open_trade.get("trail_floor", 0) + 1e-9)
        print(f"CURRENT TRAILING FLOOR      : ${current_floor:,.2f}")
        if moved and open_trade.get("trail_floor") is not None:
            print(f"  (this is HIGHER than the last recorded floor "
                  f"${open_trade['trail_floor']:,.2f} — the next live/dry "
                  f"cycle would ratchet the exchange bracket up to this)")
    else:
        print("CURRENT TRAILING FLOOR      : n/a (flat, no open trade)")

    private = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                env["BLOFIN_DEMO_API_SECRET"],
                                env["BLOFIN_DEMO_PASSPHRASE"])
    try:
        net = private.net_position_contracts(gold_book.SYMBOL)
        print(f"REAL demo account net position on {gold_book.SYMBOL}: "
              f"{net:+.1f} ct")
    except Exception as e:
        print(f"  live position read failed: {str(e)[:150]}")

    # -- 3. what the book would do now ---------------------------------------
    print("\n--- run_gold_book(private, live_feed, state, dry=True) ---")
    result = gold_book.run_gold_book(private, live_feed, state, dry=True)
    print("--- end run_gold_book ---\n")
    print(f"DECISION SUMMARY: {result}")
    print(f"  -> trail_floor from the decision dict: "
          f"{result.get('trail_floor')}")

    have_position = gb_before.get("open_trade") is not None
    if not have_position and dec["desired_in"]:
        print(f"\n>>> RIGHT NOW: gold just broke its {gold_book.ENTRY_N}-day "
              f"high. The real book would go LONG on the next live cycle, "
              f"protected by a structure-trailing floor (not a fixed TP/EMA "
              f"exit). <<<")
    elif have_position:
        print(f"\n>>> RIGHT NOW: holding an open long. The ONLY real exit is "
              f"the structure-trailing floor's exchange-side stop — "
              f"currently {'$' + f'{current_floor:,.2f}' if current_floor is not None else 'n/a'} "
              f"— firing there, never a book-computed close check. <<<")
    else:
        print("\n>>> RIGHT NOW: flat, no breakout — waiting. <<<")

    # -- 4. prove dry mode made no state changes -----------------------------
    # compare the RAW gold_book value captured BEFORE the dry run against a
    # fresh reload AFTER it (not the migrated _fresh_book() view used for
    # display above, which would falsely read as "changed" against an old,
    # pre-rewire-schema gold_book key even though nothing was written).
    state_after = load_state()
    gb_raw_after = state_after.get("gold_book")
    unchanged = gb_raw_before == gb_raw_after
    print(f"\nstate unchanged by dry run: {'YES' if unchanged else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
