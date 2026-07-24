"""
step61_diver_smoke.py — REAL BloFin smoke test for diver.py (round 58, THE
DIVER: 4h hidden RSI divergence continuation on BTC-USDT).

READ-ONLY + DRY: pulls REAL 4h BTC-USDT candles (config.make_exchange("live"))
and the REAL current net position on the demo account (config.make_exchange
("demo") + BlofinDemoPrivate — a read, never a write), then runs
diver.run_diver(private, live_feed, demo_feed, state, dry=True) ONCE. Dry
mode places NO order, sets NO leverage, and makes NO state/log/notify side
effect — enforced inside run_diver itself.

Prints, in order:
  1. the real 4h candle history pulled and its span
  2. the most recently CONFIRMED swing high/low (diver.swing_debug(), which
     calls the imported step58_divergence_mtf.swings() directly)
  3. the latest closed bar's RSI14, 4h champion state, and whether a hidden
     divergence event is firing right now (long/short/none)
  4. the frozen STOP_PCT/TARGET_PCT/LEVERAGE this book trades with
  5. what the book WOULD do right now (would-enter sizing incl. the
     direction-gate check, or would-exit, or holding, or stay flat), and
     the current live account position
  6. proof the dry run made zero state writes (reload from source of truth)

Run:  python3 step61_diver_smoke.py
"""

from __future__ import annotations

import config
from blofin_private import BlofinDemoPrivate, load_env


def main():
    print("=" * 78)
    print("THE DIVER SMOKE TEST (round 58) — REAL BloFin data, dry run, "
          "zero orders")
    print("=" * 78)

    env = load_env()
    live_feed, symbol = config.make_exchange("live")
    demo_feed, _ = config.make_exchange("demo")

    import diver

    print(f"\nsymbol={diver.SYMBOL}  timeframe={diver.TIMEFRAME}  "
          f"swing k={diver.SWING_K}  rsi n={diver.RSI_N}")
    print(f"FROZEN geometry: STOP_PCT={diver.STOP_PCT:.6f}%  "
          f"TARGET_PCT={diver.TARGET_PCT:.6f}% (3x)  "
          f"LEVERAGE={diver.LEVERAGE:.0f}x  ALLOC={diver.DIVER_ALLOC*100:.0f}%  "
          f"MAX_HOLD={diver.MAX_HOLD_H}h")

    # -- 1. real candle history ----------------------------------------------
    d = diver._load_4h(live_feed)
    print(f"\n{diver.SYMBOL} {diver.TIMEFRAME} bars: {len(d)}, "
          f"{d['timestamp'].iloc[0]:%Y-%m-%d %H:%M} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d %H:%M} UTC")

    # -- 2. current swing state (imported swings(), never reimplemented) ----
    swings_now = diver.swing_debug(d)
    print("\n-- most recently CONFIRMED swings (step58_divergence_mtf.swings) --")
    sh = swings_now["last_confirmed_swing_high"]
    sl = swings_now["last_confirmed_swing_low"]
    if sh:
        print(f"  swing HIGH: ${sh['price']:,.1f} at {sh['origin_bar_ts']} "
              f"(confirmed {sh['confirmed_at']})")
    else:
        print("  swing HIGH: none found in this window")
    if sl:
        print(f"  swing LOW : ${sl['price']:,.1f} at {sl['origin_bar_ts']} "
              f"(confirmed {sl['confirmed_at']})")
    else:
        print("  swing LOW : none found in this window")

    # -- 3. the latest closed bar's full decision (imported divergence_events) -
    dec = diver._decision(d)
    print(f"\n-- latest CLOSED bar: {dec['bar_ts']} --")
    print(f"  close  : ${dec['close']:,.1f}")
    print(f"  RSI14  : {dec['rsi14']:.1f}" if dec['rsi14'] is not None
          else "  RSI14  : n/a (warmup)")
    print(f"  champ4h: {dec['champ']} "
          f"({'uptrend' if dec['champ'] == 1 else 'not-uptrend' if dec['champ'] == 0 else 'n/a'})")
    print(f"  hidden LONG  event firing right now : "
          f"{'YES' if dec['long_hidden'] else 'no'}"
          + (f" (swing low ${dec['low_extreme']:,.1f})" if dec['long_hidden'] else ""))
    print(f"  hidden SHORT event firing right now : "
          f"{'YES' if dec['short_hidden'] else 'no'}"
          + (f" (swing high ${dec['high_extreme']:,.1f})" if dec['short_hidden'] else ""))

    # -- 4. current state + real account position ----------------------------
    from step5_paper_trade import load_state
    state = load_state()
    dv_raw_before = state.get("diver")     # RAW, for the no-write proof below
    dv_before = dv_raw_before or {"open_trade": None, "last_bar_ts": None}
    print(f"\ndiver open_trade   : {dv_before.get('open_trade')}")
    print(f"diver last_bar_ts  : {dv_before.get('last_bar_ts')}")
    print(f"shared ledger virtual_equity: ${state.get('virtual_equity', 0):,.2f}")

    private = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                env["BLOFIN_DEMO_API_SECRET"],
                                env["BLOFIN_DEMO_PASSPHRASE"])
    try:
        net = private.net_position_contracts(diver.SYMBOL)
        print(f"REAL demo account net position on {diver.SYMBOL}: "
              f"{net:+.2f} ct")
    except Exception as e:
        print(f"  live position read failed: {str(e)[:150]}")

    # -- 5. what the book would do now ---------------------------------------
    print("\n--- run_diver(private, live_feed, demo_feed, state, dry=True) ---")
    result = diver.run_diver(private, live_feed, demo_feed, state, dry=True)
    print("--- end run_diver ---\n")
    print(f"DECISION SUMMARY: {result}")

    have_position = dv_before.get("open_trade") is not None
    if have_position:
        print("\n>>> RIGHT NOW: The Diver is holding an open position — see "
              "the holding summary above. <<<")
    elif dec["long_hidden"]:
        print("\n>>> RIGHT NOW: a HIDDEN BULLISH divergence just confirmed "
              "on the latest closed 4h bar. If the direction gate is clear, "
              "the real book would go LONG on the next live cycle. <<<")
    elif dec["short_hidden"]:
        print("\n>>> RIGHT NOW: a HIDDEN BEARISH divergence just confirmed "
              "on the latest closed 4h bar. If the direction gate is clear, "
              "the real book would go SHORT on the next live cycle. <<<")
    else:
        print("\n>>> RIGHT NOW: no divergence event on the latest closed "
              "bar — flat, waiting for the next confirmed swing. <<<")

    # -- 6. prove dry mode made no state changes -----------------------------
    state_after = load_state()
    dv_raw_after = state_after.get("diver")
    unchanged = dv_raw_before == dv_raw_after
    print(f"\nstate unchanged by dry run: {'YES' if unchanged else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
