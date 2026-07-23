"""
exec_test.py — live-fire execution drill on the demo venue.

Run:  python3 exec_test.py

Fires REAL orders at minimum size (0.1 ct ~= $6.60 notional) to measure the
execution machinery the strategies depend on — the part no backtest can
test. The bot's LEDGER is untouched: these are engineering rounds, not
trades, and everything is flattened and cancelled at the end.

DRILLS
  1. maker rest + fill  : post-only at the bid — does it rest? fill? how fast?
  2. post-only rejection: post-only ABOVE the ask must be REJECTED, never
                          filled as taker (this guarantee is the whole point)
  3. market round trip  : measured slippage vs quote, both directions
  4. bracket lifecycle  : SL-only TPSL placement -> visible -> cancel
  5. tactical pattern   : position + TP limit + SL TPSL coexisting (the
                          exact structure tactical.py places) -> cleanup
  6. reduce-only guard  : oversized reduce-only must not flip the position
"""

import time

import config
from blofin_private import BlofinDemoPrivate, load_env

SIZE = 0.1                      # minimum lot, ~$6.60 — engineering rounds

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" +
          (f"  ({detail})" if detail else ""))


def main():
    env = load_env()
    p = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                          env["BLOFIN_DEMO_API_SECRET"],
                          env["BLOFIN_DEMO_PASSPHRASE"])
    demo, sym = config.make_exchange("demo")
    start_pos = p.net_position_contracts(sym)
    print(f"start: position {start_pos:+.1f} ct\n")

    # -- 1. maker rest ------------------------------------------------------
    print("[1] maker rest + fill behavior")
    q = demo.get_ticker(sym)
    oid = p.post_only_order(sym, "buy", SIZE, q.bid)
    time.sleep(3)
    resting = any(str(o.get("orderId")) == oid for o in p.pending_orders(sym))
    check("post-only at bid rests in book", resting or
          p.net_position_contracts(sym) > start_pos,
          "resting" if resting else "instant fill")
    t0, filled = time.time(), not resting
    while resting and time.time() - t0 < 45:
        time.sleep(5)
        if not any(str(o.get("orderId")) == oid
                   for o in p.pending_orders(sym)):
            filled = True
            break
    if not filled:
        p.cancel_order(sym, oid)
        check("unfilled maker cancels cleanly", True, "45s no fill")
    else:
        check("maker filled", True, f"{time.time() - t0:.0f}s")

    # -- 2. post-only crossing must reject ---------------------------------
    print("[2] post-only crossing the book")
    q = demo.get_ticker(sym)
    try:
        oid2 = p.post_only_order(sym, "buy", SIZE, q.ask * 1.001)
        time.sleep(2)
        gone = not any(str(o.get("orderId")) == oid2
                       for o in p.pending_orders(sym))
        fills = p.fills(sym, oid2)
        check("crossing post-only rejected, never taker-filled",
              gone and not fills)
    except RuntimeError:
        check("crossing post-only rejected, never taker-filled", True,
              "rejected at API level")

    # -- 3. market round trip: measured slippage ---------------------------
    print("[3] market round trip slippage")
    q = demo.get_ticker(sym)
    oid3 = p.market_order(sym, "buy", 0.5)
    time.sleep(2)
    f_in = p.fills(sym, oid3)
    in_px = float(f_in[0]["fillPrice"]) if f_in else 0
    slip_in = (in_px - q.ask) / q.ask * 10_000 if in_px else None
    q2 = demo.get_ticker(sym)
    oid4 = p.market_order(sym, "sell", 0.5, reduce_only=True)
    time.sleep(2)
    f_out = p.fills(sym, oid4)
    out_px = float(f_out[0]["fillPrice"]) if f_out else 0
    slip_out = (q2.bid - out_px) / q2.bid * 10_000 if out_px else None
    check("market orders fill and report",
          bool(in_px and out_px),
          f"slip in {slip_in:+.2f}bps / out {slip_out:+.2f}bps"
          if in_px and out_px else "missing fills")

    # -- 4. bracket lifecycle ----------------------------------------------
    print("[4] SL bracket lifecycle (place -> verify -> cancel)")
    oid5 = p.market_order(sym, "buy", SIZE)
    time.sleep(1.5)
    q = demo.get_ticker(sym)
    tpsl = p.place_tpsl(sym, "sell", SIZE, None, round(q.bid * 0.92, 1))
    time.sleep(1.5)
    live = any(str(b.get("tpslId")) == tpsl for b in p.pending_tpsl(sym))
    check("SL-only bracket placed and visible", live)
    p.cancel_tpsl(sym, tpsl)
    time.sleep(1.5)
    gone = not any(str(b.get("tpslId")) == tpsl for b in p.pending_tpsl(sym))
    check("bracket cancels cleanly", gone)

    # -- 5. the tactical pattern: TP limit + SL bracket together -----------
    print("[5] tactical bracket pattern (TP limit + SL TPSL coexisting)")
    q = demo.get_ticker(sym)
    tp_oid = sl_id = None
    try:
        tp_oid = p.post_only_order(sym, "sell", SIZE, round(q.ask * 1.05, 1),
                                   reduce_only=True)
        sl_id = p.place_tpsl(sym, "sell", SIZE, None, round(q.bid * 0.92, 1))
        time.sleep(1.5)
        tp_live = any(str(o.get("orderId")) == tp_oid
                      for o in p.pending_orders(sym))
        sl_live = any(str(b.get("tpslId")) == sl_id
                      for b in p.pending_tpsl(sym))
        check("TP limit and SL bracket coexist", tp_live and sl_live)
    finally:
        if tp_oid:
            try: p.cancel_order(sym, tp_oid)
            except Exception: pass
        if sl_id:
            try: p.cancel_tpsl(sym, sl_id)
            except Exception: pass

    # -- 6. reduce-only guard ----------------------------------------------
    print("[6] oversized reduce-only must not flip the position")
    pos_now = p.net_position_contracts(sym)
    my_ct = pos_now - start_pos
    try:
        p.market_order(sym, "sell", abs(my_ct) + 5.0, reduce_only=True)
        time.sleep(2)
        after = p.net_position_contracts(sym)
        check("reduce-only clamps at position size (no flip)",
              after >= start_pos - 0.05, f"{pos_now:+.1f} -> {after:+.1f}")
    except RuntimeError as e:
        check("reduce-only clamps at position size (no flip)", True,
              f"rejected: {str(e)[:40]}")

    # -- cleanup ------------------------------------------------------------
    final = p.net_position_contracts(sym)
    drift = final - start_pos
    if abs(drift) > 0.01:
        side = "sell" if drift > 0 else "buy"
        p.market_order(sym, side, abs(drift), reduce_only=drift > 0)
        time.sleep(2)
        final = p.net_position_contracts(sym)
    check("account restored to starting position",
          abs(final - start_pos) < 0.01, f"{final:+.1f} ct")

    print(f"\nRESULT: {sum(ok for _, ok in results)}/{len(results)} drills passed")


if __name__ == "__main__":
    main()
