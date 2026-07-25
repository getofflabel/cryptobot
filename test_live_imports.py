"""
test_live_imports.py — THE DEPLOY GUARD. Would this crash on Render?

WHY THIS FILE EXISTS (2026-07-25, written in blood):

Twice in one night a module that only exists on the developer's laptop got
onto the LIVE import path, and both times every local test passed:

  1. chart_reader.py imported matplotlib at module scope. daily_pick began
     importing chart_reader for the round-83 eye veto. matplotlib is not in
     requirements.txt. Caught before deploy, but only by luck.
  2. step76_indicators.py imported `ta` at module scope. breakout_book
     imports step86_specified, which imports step76_indicators. `ta` is not
     in requirements.txt. NOT caught — the Breakout Book shipped and then
     crashed EVERY CYCLE on its first night with "No module named 'ta'".

Worse, the ad-hoc check written to catch (1) was itself broken: it used a
`find_module`-based meta_path finder, and Python 3.12 removed that hook, so
the blocker silently did nothing and reported a clean pass. A test that
cannot fail is more dangerous than no test.

A book that crashes every cycle is this project's worst failure mode: it
silently MISSES trades, which quietly biases the live track record (it can
still take losers while crashing through winners) — exactly what daemon.py's
book-health watchdog was built to shout about.

WHAT THIS TEST DOES: blocks every third-party module that is NOT in
requirements.txt, then imports every module the live worker actually loads.
If any of them needs a laptop-only library, this fails HERE instead of at
02:28 on the Render worker.
"""

from __future__ import annotations

import sys
import traceback
from importlib.abc import MetaPathFinder

# RESEARCH-ONLY packages: installed on the laptop, deliberately NOT in
# requirements.txt, and therefore absent from the live Render worker.
#
# A denylist, not an allowlist, and that choice is deliberate: an allowlist
# has to enumerate every transitive dependency of pandas/yfinance and it
# breaks the moment it misses one (the first attempt blocked pandas' own C
# extensions and reported every live module as broken, which is a false
# alarm that would train us to ignore this test). This list targets the
# actual failure mode instead — heavyweight analysis libraries drifting from
# a research file into a live import chain.
#
# ADD TO THIS LIST whenever a research-only package enters the repo.
RESEARCH_ONLY = {
    "ta", "matplotlib", "sklearn", "scikit_learn", "scipy", "statsmodels",
    "seaborn", "plotly", "imageio_ffmpeg", "imageio", "PIL", "Pillow",
    "torch", "tensorflow", "arch", "numba", "cvxpy", "pmdarima",
}

# Every module the live worker imports, directly or through a book.
LIVE_MODULES = [
    "daemon", "hourly", "config", "exchange", "blofin_private",
    "step5_paper_trade", "book_ledger", "strategy", "backtest",
    "daily_pick", "gold_book", "diver", "newsdesk", "shorts_lab",
    "tactical", "spx_book", "tradfi_engine", "breakout_book",
    "live_read", "export_journal", "morning_read",
]


# The check runs in a FRESH subprocess. Trying to do it in-process meant
# purging sys.modules, which rips out already-initialised C extensions and
# produces nonsense errors ('abi_thread'). A clean interpreter is also the
# honest simulation: it is exactly what the Render worker does on boot.

_CHILD = r"""
import sys, os, json
from importlib.abc import MetaPathFinder

BLOCKED = set(json.loads(sys.argv[1]))
MODULES = json.loads(sys.argv[2])
HERE = sys.argv[3]
sys.path.insert(0, HERE)

class Blocker(MetaPathFinder):
    # find_spec, NOT find_module — Python 3.12 removed find_module, which
    # silently turned the first version of this guard into a no-op.
    def find_spec(self, name, path=None, target=None):
        top = name.split(".")[0]
        if top in BLOCKED:
            raise ImportError(top + " is not in requirements.txt and would "
                              "NOT exist on the live Render worker")
        return None

sys.meta_path.insert(0, Blocker())

# prove the blocker bites before trusting anything it passes
sentinel_ok = False
try:
    __import__(sorted(BLOCKED)[0])
except ImportError as e:
    sentinel_ok = "not in requirements.txt" in str(e)

failures = []
for m in MODULES:
    try:
        __import__(m)
    except Exception as e:
        failures.append([m, type(e).__name__ + ": " + str(e)[:160]])

print(json.dumps({"sentinel_ok": sentinel_ok, "failures": failures}))
"""


def _run_guard():
    import json
    import os
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.run(
        [sys.executable, "-c", _CHILD, json.dumps(sorted(RESEARCH_ONLY)),
         json.dumps(LIVE_MODULES), here],
        capture_output=True, text=True, timeout=300, cwd=here)
    out = (p.stdout or "").strip().splitlines()
    if not out:
        raise AssertionError(f"guard subprocess produced no output.\n"
                             f"stderr: {(p.stderr or '')[-800:]}")
    return json.loads(out[-1])


def test_the_blocker_itself_actually_blocks():
    """A guard that cannot fail is worse than no guard: the first version of
    this check used the removed find_module hook and silently passed
    everything. Prove the blocker really raises before trusting it."""
    res = _run_guard()
    assert res["sentinel_ok"], (
        "the import blocker did NOT stop a non-requirements package — this "
        "guard is not actually testing anything")


def test_live_modules_import_without_laptop_only_packages():
    res = _run_guard()
    failures = res["failures"]
    assert not failures, (
        "these live modules need packages the Render worker does not have "
        "(add to requirements.txt, or make the import lazy/optional):\n"
        + "\n".join(f"   {m}: {err}" for m, err in failures))


def main():
    tests = [test_the_blocker_itself_actually_blocks,
             test_live_modules_import_without_laptop_only_packages]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("LIVE IMPORT GUARD")
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
