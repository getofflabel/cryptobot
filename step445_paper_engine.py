"""
step445_paper_engine.py — the engine driven the way a live runner drives it.

WHAT THIS PROVES, using REAL prices and placing NOTHING anywhere:

  1. The venue is resolved from config and it is PAPER, loudly.
  2. Real bid and ask come off Alpaca's free data API — read, never traded
     through. The Alpaca account still has zero orders ever placed.
  3. A SHORT opens. That is the whole reason this file exists: 190 of the 324
     crypto setups the bot found were shorts and the old venue refused every
     one of them.
  4. A stop is placed and then triggered by a REAL bar out of the cached
     history, and it fills WORSE than its level.
  5. Half comes off at a target and the stop moves to break even, with the
     runner still protected.
  6. The whole account is rebuilt from the fill log alone and matches.

SAFETY. Every write goes to a scratch state file in /tmp, not to the real
paper_state.json, so running this cannot disturb a paper week in progress.
No order is sent to any venue. `--offline` skips the network entirely.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import paper
import venue
from paper import PaperBroker, Quote

UTC = dt.timezone.utc
SCRATCH = os.path.join(tempfile.gettempdir(), "step445_paper")
PAIR = "BTC/USD"


def line(title=""):
    print("\n" + "=" * 74)
    if title:
        print(title)
        print("=" * 74)


def real_quotes(pairs):
    """Read the live bid and ask. READ ONLY. Nothing here can place an order:
    it touches the data host and no order path at all."""
    import alpaca
    cli = alpaca.from_env()
    if cli is None:
        return {}, "ALPACA keys are not in .env, so no live quotes"
    return paper.live_quotes(pairs, client=cli), ""


def real_bars(pair, n=400):
    """A real slice of 5-minute history out of the cache this repo already
    keeps, so the stop is triggered by a bar the market actually printed."""
    try:
        import pandas as pd
        import tjr_crypto
        d = pd.read_parquet(tjr_crypto.cache_name(pair, "5m"))
        return d.tail(n).to_dict("records")
    except Exception as e:                            # noqa: BLE001
        print(f"  no cached bars ({str(e)[:80]}) — using the live quote only")
        return []


def main(argv):
    offline = "--offline" in argv
    os.makedirs(SCRATCH, exist_ok=True)
    state = os.path.join(SCRATCH, "state.json")
    log = os.path.join(SCRATCH, "fills.jsonl")
    for p in (state, log):
        if os.path.exists(p):
            os.remove(p)

    # ---------------------------------------------------------- 1. the venue
    line("1. WHICH VENUE, AND IS IT REAL MONEY")
    v, decision = venue.resolve(state_path=state, log_path=log)
    venue.announce(decision, to_phone=False)
    assert decision["chosen"] == "paper" and not decision["real_money"]

    # ------------------------------------------------------- 2. real prices
    line("2. REAL PRICES, READ AND NEVER TRADED THROUGH")
    quotes, why = ({}, "offline") if offline else real_quotes([PAIR, "ETH/USD"])
    if quotes:
        for sym, q in quotes.items():
            print(f"  {sym:10s} bid {q.bid:>12,.2f}   ask {q.ask:>12,.2f}   "
                  f"the gap is {q.spread_pct_of_price:.4f}% of the price   "
                  f"({q.source})")
    else:
        print(f"  no live quotes ({why}). Falling back to a written-down "
              f"quote so the rest still runs.")
        quotes = {PAIR: Quote(PAIR, 100_000.0, 100_113.6, dt.datetime.now(UTC),
                              "stand-in at the measured spread")}

    q = quotes[PAIR]
    board = dict(quotes)
    feed = lambda syms: {s: board[s] for s in syms if s in board}   # noqa: E731

    b = PaperBroker(state_path=state, log_path=log, quotes=feed)
    print(f"\n  opening equity ${b.account(refresh=False)['equity']:,.2f}")

    # ------------------------------------------------------------ 3. a SHORT
    line("3. A SHORT. THE THING THE OLD VENUE REFUSED 190 TIMES")
    size = round(20_000.0 / q.bid, 6)
    got = b.market_order(PAIR, "sell", size, reason="a short setup fired")
    print(f"  sold {size} {PAIR} at {got['price']:,.2f}")
    print(f"  filled at {got['price_basis']}")
    print(f"  the gap cost us ${got['spread_cost']:,.2f}, recorded and "
          f"nothing else")
    pos = b.position(PAIR)
    print(f"  position: {pos['qty']} ({pos['side']}), cash now "
          f"${b.cash:,.2f} — shorting credits the proceeds")

    stop_level = round(q.ask * 1.006, 2)
    st = b.place_stop(PAIR, stop_level, reason="above the high that was swept")
    print(f"  stop at {stop_level:,.2f} — {st['fill_note']}")
    print(f"  open risk if it fills AT the level: "
          f"${b.open_risk()['dollars_if_stops_fill_at_their_level']:,.2f}")

    # ------------------------------------------- 4. a real bar takes it out
    line("4. A REAL BAR TRIGGERS THE STOP, AND IT FILLS WORSE THAN THE LEVEL")
    bars = [] if offline else real_bars(PAIR)
    trigger = None
    for row in bars:                       # find a real bar with a big range
        b_ = paper._bar_fields(row)        # the cache says open/high/low/close
        if not {"h", "l", "o", "c"} <= set(b_):
            continue
        if float(b_["h"]) / float(b_["l"]) - 1.0 > 0.004:
            trigger = b_
            break
    if trigger is None:
        base = q.ask
        trigger = {"t": dt.datetime.now(UTC), "o": base,
                   "h": base * 1.009, "l": base * 0.998, "c": base * 1.007}
        print("  (no wide real bar to hand — using a written-down one)")
    else:
        print(f"  using a real 5-minute bar from {trigger['t']}")
    # rescale the real bar's SHAPE onto today's price, so the stop sits inside
    # it. The shape is real; only the level is moved.
    lo, hi = float(trigger["l"]), float(trigger["h"])
    scale = stop_level / lo * 0.999
    shaped = {"t": trigger["t"], "o": float(trigger["o"]) * scale,
              "h": hi * scale, "l": lo * scale, "c": float(trigger["c"]) * scale}
    print(f"  bar high {shaped['h']:,.2f}   low {shaped['l']:,.2f}   "
          f"stop {stop_level:,.2f}")
    res = b.on_bar(PAIR, shaped, target=q.bid * 0.99)
    print(f"  -> {res['action']}: {res['reason']}")
    print(f"  filled at {res['price']:,.2f}, which is "
          f"{res['fill']['slippage_versus_the_stop_level']:,.2f} WORSE than "
          f"the stop level")
    if res.get("target_also_in_this_bar"):
        print("  the target was inside this bar too and the stop still won")
    print(f"  equity now ${b.account(refresh=False)['equity']:,.2f}")

    # ------------------------------------------ 5. half off, stop to break even
    line("5. HALF OFF AT THE FIRST TARGET, STOP TO BREAK EVEN")
    b.market_order(PAIR, "buy", size, reason="a long setup fired")
    entry = b.position(PAIR)["avg_entry"]
    b.place_stop(PAIR, round(entry * 0.994, 2), reason="below the swing low")
    board[PAIR] = Quote(PAIR, entry * 1.008, entry * 1.0082,
                        dt.datetime.now(UTC), "the market moved our way")
    half = b.close_position(PAIR, size / 2, reason="target 1: half off")
    print(f"  took {half['qty']} off at {half['price']:,.2f}, banking "
          f"${half['realised_on_this_fill']:,.2f}")
    b.place_stop(PAIR, round(entry, 2), reason="break even, and never moved again")
    pos = b.position(PAIR)
    print(f"  runner: {pos['qty']} left, stop at {pos['stop']:,.2f}, entry "
          f"still {pos['avg_entry']:,.2f}")

    # ------------------------------------------------- 6. restart and rebuild
    line("6. IT SURVIVES A RESTART, AND REBUILDS FROM THE FILL LOG ALONE")
    live_cash, live_pos = b.cash, {k: dict(v) for k, v in b._pos.items()}
    del b
    again = PaperBroker(state_path=state, log_path=log, quotes=feed)
    print(f"  reloaded from disk: cash ${again.cash:,.2f}, "
          f"{len(again._pos)} open position(s), stop "
          f"{again.position(PAIR)['stop']:,.2f}")
    assert abs(again.cash - live_cash) < 1e-9
    assert again._pos.keys() == live_pos.keys()

    rebuilt = PaperBroker.rebuild_from_log(log)
    ok = (abs(rebuilt.cash - live_cash) < 1e-9
          and rebuilt._pos.keys() == live_pos.keys()
          and all(abs(rebuilt._pos[k]["qty"] - v["qty"]) < 1e-12
                  for k, v in live_pos.items())
          and all(rebuilt._pos[k]["stop"] == v["stop"]
                  for k, v in live_pos.items()))
    print(f"  rebuilt from {len(rebuilt.fills())} fills in the log alone: "
          f"{'MATCHES' if ok else 'DOES NOT MATCH'}")
    assert ok, "the log is not a complete record"

    # ------------------------------------------------------ 7. the misses
    line("7. WHAT HAPPENS WHEN THERE IS NO PRICE")
    miss = again.market_order("XAU/USD", "buy", 1.0, reason="gold setup")
    print(f"  {miss['status']}: {miss['reason']}")
    print("  a missed trade is honest. An invented fill is not.")

    line("THE AUDIT TRAIL")
    for rec in again.orders():
        if rec.get("event") == "fill":
            print(f"  {rec['ts']}  {rec['kind']:<7} {rec['side']:<4} "
                  f"{rec['qty']:<12} @ {rec['price']:>12,.2f}   {rec['reason']}")
        elif rec.get("event") == "stop_placed":
            print(f"  {rec['ts']}  stop    at {rec['level']:>17,.2f}   "
                  f"{rec['reason']}")
        else:
            print(f"  {rec['ts']}  {rec.get('event'):<7} {rec.get('reason', '')[:60]}")

    line("ACCOUNT")
    print(json.dumps(again.account(refresh=False), indent=2))
    print(f"\nscratch files: {state}\n               {log}")
    print("no order was sent to any venue.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
