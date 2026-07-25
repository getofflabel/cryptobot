"""
test_phantom_fill.py — an order that did not fill must never be booked.

WHY (2026-07-25): `_execute_single`'s wait loop decided an order had filled
by checking whether it had left `pending_orders()`. But BloFin CANCELS
post-only orders that would cross the book (cancel_by_post_only_depth) —
the order leaves pending having filled NOTHING. The old code then returned
`(limit_price, True)`: a trade booked at a price that never happened, for a
position that does not exist.

Reproduced live 8 times out of 8 on the demo account, and 84% of that
account's visible post-only orders ended in exactly that cancel.

This is the same class of fault as the 2026-07-24 ghost: a books-vs-reality
fork, which is how a phantom BTC short reached Wallace's screen.
"""

from __future__ import annotations

import sys
import traceback

import step5_paper_trade as s5


class _FakePrivate:
    """Reproduces BloFin's actual post-only-cancel behaviour."""

    def __init__(self, mode, contracts=10.0):
        self.mode = mode          # "cancelled" | "filled" | "partial"
        self.contracts = contracts
        self.market_orders = []

    def post_only_order(self, *a, **k):
        return "OID1"

    def pending_orders(self, symbol):
        return []                 # gone from pending in every scenario

    def fills(self, symbol, oid=None):
        if oid in self.market_orders:
            return [{"fillPrice": "101.0", "fillSize": str(self._rest)}]
        if self.mode == "cancelled":
            return []             # left pending having filled NOTHING
        if self.mode == "partial":
            return [{"fillPrice": "100.0", "fillSize": str(self.contracts / 2)}]
        return [{"fillPrice": "100.0", "fillSize": str(self.contracts)}]

    def market_order(self, symbol, side, contracts, **k):
        self._rest = contracts
        self.market_orders.append("OID2")
        return "OID2"

    def cancel_order(self, *a, **k):
        pass


def _run(mode, contracts=10.0):
    p = _FakePrivate(mode, contracts)
    orig_sleep = s5.time.sleep
    s5.time.sleep = lambda *_: None
    try:
        return p, s5._execute_single(p, None, "BTC-USDT", "buy", contracts,
                                     100.0)
    finally:
        s5.time.sleep = orig_sleep


def test_a_cancelled_order_is_not_a_fill():
    p, (price, was_maker) = _run("cancelled")
    assert p.market_orders, (
        "an exchange-cancelled post-only was treated as filled — this is the "
        "phantom-fill bug: no market order was ever sent, so no position "
        "exists, but the caller was told it filled")
    assert was_maker is False, "a chased fill must not be reported as maker"
    assert price == 101.0, f"must report the REAL chase fill, got {price}"


def test_b_a_real_fill_is_still_reported_as_maker():
    p, (price, was_maker) = _run("filled")
    assert not p.market_orders, "should not chase when the order really filled"
    assert was_maker is True and price == 100.0, (price, was_maker)


def test_c_partial_fill_chases_the_remainder():
    p, (price, was_maker) = _run("partial", contracts=10.0)
    assert p.market_orders, "a partial fill must chase the rest, not pretend"
    assert was_maker is False
    # 5 ct at 100 + 5 ct at 101 = 100.5 blended
    assert abs(price - 100.5) < 1e-6, price


def test_d_the_ride_uses_the_atomic_path():
    """THE RIDE was the last caller on the pre-OWNER'S-LAW path, which also
    still clip-splits — the shape that caused the XAUT orphan."""
    import ast
    import inspect
    import textwrap
    # Parse the AST rather than grepping the text — the source carries a
    # comment explaining the migration AWAY from execute_maker_or_chase, and
    # a naive string search matches that comment.
    tree = ast.parse(textwrap.dedent(inspect.getsource(s5.decide_and_trade)))
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "execute_maker_or_chase" not in called, (
        "the ride is back on the maker-or-chase path; it must use "
        "execute_market_clips (one atomic order, real fills)")
    assert "execute_market_clips" in called, (
        f"the ride does not call execute_market_clips: {sorted(called)}")


def main():
    tests = [test_a_cancelled_order_is_not_a_fill,
             test_b_a_real_fill_is_still_reported_as_maker,
             test_c_partial_fill_chases_the_remainder,
             test_d_the_ride_uses_the_atomic_path]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("PHANTOM FILL TESTS")
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
