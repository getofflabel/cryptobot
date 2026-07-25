"""
test_stand_down_gates.py — a stood-down book must STAND DOWN, not CRASH.

WHY THIS EXISTS (2026-07-25, written the same hour it was needed):

Three books were stood down after round 150 showed their edges die at taker
execution with real chart-structure stops. The gates went in, the full test
suite passed, it deployed — and the Diver then crashed EVERY CYCLE live
with "cannot access local variable 'direction'".

The cause: the gate was placed just below the `if dry:` block, but
`direction`, `contracts` and `ref_price` are bound INSIDE that branch. On
the live path they do not exist yet, so the gate itself raised.

The suite missed it because every test sets NEW_ENTRIES_ENABLED = True to
exercise the entry mechanics — so the gate path, the one that actually runs
in production, was never executed by any test.

A book that crashes every cycle is this project's worst failure mode: it
silently MISSES trades, biasing the live record because it can still take
losers while crashing through winners.

THIS FILE RUNS EVERY BOOK'S OWN TESTS WITH THE GATE IN ITS PRODUCTION
STATE (flag OFF) and fails on any unbound-variable crash.
"""

from __future__ import annotations

import importlib
import io
import sys
import traceback
from contextlib import redirect_stdout

# (module, its test module) — books currently stood down for new entries
GATED_BOOKS = [("diver", "test_diver"), ("newsdesk", "test_newsdesk_exit")]


def _run_with_gate_off(mod_name: str, test_mod_name: str):
    """Run every test in `test_mod_name` with the book's gate ACTIVE.

    Assertion failures are IGNORED on purpose — a test that asserts an
    entry happened will legitimately fail when entries are switched off.
    We are hunting exactly one thing: the gate raising because it touches
    a name that is not bound on the live path.
    """
    m = importlib.import_module(mod_name)
    importlib.reload(m)
    m.NEW_ENTRIES_ENABLED = False          # the production configuration
    t = importlib.import_module(test_mod_name)
    importlib.reload(t)
    # the test module's own main() flips the flag on; call the tests direct
    crashes, ran = [], 0
    for name in sorted(dir(t)):
        if not name.startswith("test_"):
            continue
        fn = getattr(t, name)
        if not callable(fn):
            continue
        ran += 1
        try:
            with redirect_stdout(io.StringIO()):
                fn()
        except (NameError, UnboundLocalError) as e:
            crashes.append((name, f"{type(e).__name__}: {e}"))
        except Exception:
            pass                            # any other failure is not our hunt
    return ran, crashes


def test_gated_books_stand_down_without_crashing():
    all_crashes = []
    for mod_name, test_mod_name in GATED_BOOKS:
        ran, crashes = _run_with_gate_off(mod_name, test_mod_name)
        assert ran > 0, f"{test_mod_name} exposed no tests to run"
        all_crashes += [(mod_name, n, e) for n, e in crashes]
    assert not all_crashes, (
        "a stood-down book CRASHED instead of standing down — this is the "
        "exact bug that took the Diver down live on 2026-07-25:\n"
        + "\n".join(f"   {m}.{n}: {e}" for m, n, e in all_crashes))


def test_every_gate_sits_after_the_exit_logic():
    """Standing a book down must never orphan an open position. The gate has
    to run AFTER reconcile/exit, so a held trade still closes normally."""
    import inspect
    # (module, function) for EVERY function that can open a position.
    # tactical has TWO: the BTC slot and the ETH amplifier. The first
    # stand-down gated only one of them and the amplifier kept trading the
    # same dead panic-dip trigger — hence this list is explicit.
    entry_points = {"diver": "run_diver", "newsdesk": "run_newsdesk",
                    "tactical": "tactical_cycle",
                    "tactical:amp": "amplifier_cycle",
                    "shorts_lab": "run_lab",
                    "breakout_book": "run_breakout_book"}
    for key, fn_name in entry_points.items():
        mod_name = key.split(":")[0]
        m = importlib.import_module(mod_name)
        importlib.reload(m)
        src = inspect.getsource(getattr(m, fn_name))
        assert "STAND-DOWN GATE" in src, f"{key}: gate missing"
        assert src.index("STAND-DOWN GATE") > src.index("reconcile"), (
            f"{key}: the gate runs BEFORE reconcile — an open position "
            f"could be orphaned")


def main():
    tests = [test_gated_books_stand_down_without_crashing,
             test_every_gate_sits_after_the_exit_logic]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("STAND-DOWN GATE TESTS")
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
