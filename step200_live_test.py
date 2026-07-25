"""
step200_live_test.py — live-fire safety drill for a MAKER (post-only limit)
entry, run on the BloFin DEMO account (demo-trading-openapi.blofin.com —
paper money, not a funded account), per Wallace's step200 request.

Does NOT touch execution code and does NOT change the OWNER'S LAW. This is
a standalone, one-off diagnostic script (like exec_test.py, which already
exists for this purpose) — it imports blofin_private/exchange/book_ledger
read-only and places its own minimum-size orders, all tagged and all
cleaned up.

Symbol: XRP-USDT — verified via grep that no live book (daily_pick,
gold_book, diver, newsdesk, shorts_lab, tactical, breakout_book, core_ride)
has this symbol in its UNIVERSE, so nothing here can collide with a real
book's position or be misread by book_ledger's per-book accounting.

DRILLS (matches step200 task spec exactly):
  1. post-only limit AWAY from market (won't fill) -> confirm it appears in
     orders-pending with our clientOrderId
  2. confirm book_ledger.unexplained_position() does NOT count a resting
     order as a position (net position must still be 0 while it rests)
  3. cancel it -> confirm gone from orders-pending
  4. post-only limit AT the touch (join best bid) -> wait for a real maker
     fill -> read the ACTUAL fee from fills-history via order_fee()
  5. close the resulting position (reduce-only) -> confirm flat
  6. print a fee-bps summary (2bps maker vs 6bps taker expected)

Run: python3 step200_live_test.py
"""

import time

from blofin_private import BlofinDemoPrivate, load_env, make_client_order_id
from book_ledger import unexplained_position
from exchange import BlofinExchange

SYMBOL = "XRP-USDT"
TAG = "step200"          # not in BOOK_TAGS on purpose — this is not a book


def main():
    env = load_env()
    p = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                          env["BLOFIN_DEMO_API_SECRET"],
                          env["BLOFIN_DEMO_PASSPHRASE"])
    ex = BlofinExchange(demo=True)

    spec = ex.get_instrument(SYMBOL)
    print(f"instrument spec: {spec}\n")
    min_size = float(spec.get("minSize", spec.get("lotSize", 1)))
    lot = float(spec.get("lotSize", min_size))
    size = max(min_size, lot)
    print(f"using size {size} contracts (min_size={min_size}, lot={lot})\n")

    start_net = p.net_position_contracts(SYMBOL)
    print(f"[0] starting net position on {SYMBOL}: {start_net:+.4f}\n")
    if abs(start_net) > 1e-9:
        print("!!! non-zero starting position on a symbol no book trades — "
              "stopping, not touching this (investigate by hand).")
        return

    fake_state = {}   # no book anywhere records anything for XRP-USDT

    # -- 1. post-only AWAY from market (must rest, not fill) ----------------
    q = ex.get_ticker(SYMBOL)
    print(f"[1] ticker: bid {q.bid} ask {q.ask}")
    away_price = round(q.bid * 0.85, 4)   # 15% below bid -> cannot fill
    coid1 = make_client_order_id(TAG)
    oid1 = p.post_only_order(SYMBOL, "buy", size, away_price,
                             client_order_id=coid1)
    print(f"    placed post-only BUY {size} @ {away_price} "
          f"(15% below bid) oid={oid1} clientOrderId={coid1}")
    time.sleep(3)
    pending = p.pending_orders(SYMBOL)
    match = [o for o in pending if str(o.get("orderId")) == oid1]
    print(f"    orders-pending for {SYMBOL}: {len(pending)} order(s)")
    print(f"    ours present: {bool(match)}  "
          f"clientOrderId on exchange: "
          f"{match[0].get('clientOrderId') if match else 'N/A'}")
    assert match, "FAIL: resting order not found in orders-pending"
    assert match[0].get("clientOrderId") == coid1, \
        "FAIL: clientOrderId mismatch"

    # -- 2. confirm the resting order is NOT counted as a position ----------
    net_while_resting = p.net_position_contracts(SYMBOL)
    unexplained = unexplained_position(net_while_resting, fake_state)
    print(f"\n[2] net position while order rests: {net_while_resting:+.4f}")
    print(f"    unexplained_position(): {unexplained:+.4f}")
    assert abs(net_while_resting) < 1e-9, \
        "FAIL: a merely-resting order moved net_position_contracts"
    assert abs(unexplained) < 1e-9, \
        "FAIL: book_ledger sees a resting order as an unexplained position"
    print("    CONFIRMED: a resting post-only order is invisible to "
          "net_position_contracts() and unexplained_position() until it "
          "actually fills — book_ledger cannot mistake it for a position.")

    # -- 3. cancel -> confirm gone -------------------------------------------
    p.cancel_order(SYMBOL, oid1)
    time.sleep(2)
    pending2 = p.pending_orders(SYMBOL)
    still_there = any(str(o.get("orderId")) == oid1 for o in pending2)
    print(f"\n[3] cancelled. still present after cancel: {still_there}")
    assert not still_there, "FAIL: order still resting after cancel"

    # -- 4. post-only AT the touch -> real maker fill ------------------------
    # NOTE (learned live, first run of this script): a post-only order
    # placed exactly at a fast-moving best bid frequently gets CANCELLED by
    # the exchange itself with cancelSource "cancel_by_post_only_depth" (the
    # book moved between our quote read and order placement such that
    # resting there would have crossed / taken liquidity — BloFin protects
    # the post-only guarantee by cancelling rather than converting to
    # taker). That is NOT a fill and must not be mistaken for one — checking
    # only "no longer in orders-pending" is a false positive. This version
    # checks the order's real terminal state via orders_history and RETRIES
    # at a fresh touch price on a post-only-depth cancel, up to RETRY_MAX
    # times, before concluding it genuinely won't fill.
    print("\n[4] joining the best bid with a post-only BUY — waiting for a "
          "genuine maker fill (retrying on post-only-depth cancels, up to "
          "6 attempts / ~3 min)...")
    RETRY_MAX = 6
    real_fill = None
    oid2 = None
    for attempt in range(1, RETRY_MAX + 1):
        q2 = ex.get_ticker(SYMBOL)
        touch_price = q2.bid
        coid2 = make_client_order_id(TAG)
        oid2 = p.post_only_order(SYMBOL, "buy", size, touch_price,
                                 client_order_id=coid2)
        print(f"    attempt {attempt}/{RETRY_MAX}: post-only BUY {size} @ "
              f"{touch_price} (best bid) oid={oid2}")
        waited = 0
        outcome = None
        while waited < 30:
            time.sleep(5)
            waited += 5
            pend = p.pending_orders(SYMBOL)
            if not any(str(o.get("orderId")) == oid2 for o in pend):
                # left the book — find out WHY via orders_history
                hist = p.orders_history(SYMBOL, limit=10)
                row = next((h for h in hist
                           if str(h.get("orderId")) == oid2), None)
                if row and row.get("state") == "filled":
                    outcome = "filled"
                elif row and row.get("state") == "canceled":
                    outcome = row.get("cancelSource", "canceled")
                else:
                    outcome = f"unknown ({row})"
                break
        if outcome == "filled":
            real_fill = oid2
            print(f"    -> FILLED after {waited}s (confirmed via "
                  f"orders_history, not just absence from pending)")
            break
        elif outcome == "cancel_by_post_only_depth":
            print(f"    -> cancelled by exchange (post-only-depth, book "
                  f"moved through our price) — not a fill, retrying")
            continue
        elif outcome is None:
            print(f"    -> still resting after {waited}s, cancelling this "
                  f"attempt and retrying at a fresh touch")
            try:
                p.cancel_order(SYMBOL, oid2)
            except Exception:
                pass
            continue
        else:
            print(f"    -> left the book for reason: {outcome} — retrying")
            continue

    if not real_fill:
        print(f"\nRESULT: no genuine maker fill achieved in {RETRY_MAX} "
              f"attempts — either the book kept moving through our price "
              f"(post-only-depth cancels) or it never touched. No fee data "
              f"to report from drill 4. Drills 1-3 (resting-order safety) "
              f"still stand as PASSED above. See step200_fill_rate.py for "
              f"the historical-data fill-rate estimate.")
        return

    time.sleep(2)
    fills = p.fills(SYMBOL, real_fill)
    fill_price = float(fills[0]["fillPrice"]) if fills else None
    fee = p.order_fee(SYMBOL, real_fill)
    notional = (fill_price * size * 100) if fill_price else None   # x100 =
                                                                     # XRP-USDT
                                                                     # contractValue
    bps = (abs(fee) / notional * 10_000) if (fee and notional) else None
    if bps is not None:
        print(f"\n    fill_price={fill_price} fee={fee} notional={notional} "
              f"-> {bps:.2f} bps  (BloFin standard: maker 2bps / taker 6bps)")
    else:
        print(f"\n    filled but fee/notional unavailable yet (fills-history "
              f"lag) — re-check manually with order_fee('{SYMBOL}', "
              f"'{real_fill}').")

    # -- 5. close the position, confirm flat ---------------------------------
    print("\n[5] closing the resulting position (reduce-only market order)")
    pos = p.net_position_contracts(SYMBOL)
    print(f"    position before close: {pos:+.4f}")
    if abs(pos) > 1e-9:
        side = "sell" if pos > 0 else "buy"
        coid3 = make_client_order_id(TAG)
        oid3 = p.market_order(SYMBOL, side, abs(pos), reduce_only=True,
                              client_order_id=coid3)
        time.sleep(2)
        final = p.net_position_contracts(SYMBOL)
        print(f"    closed with {side} {abs(pos)} ct (oid={oid3}). "
              f"final position: {final:+.4f}")
        assert abs(final) < 1e-9, "FAIL: account not flat after close"
    else:
        print("    already flat, nothing to close")

    print("\nRESULT: all drills passed. Account confirmed flat.")


if __name__ == "__main__":
    main()
