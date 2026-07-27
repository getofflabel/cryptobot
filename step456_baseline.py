"""
step456_baseline.py — freeze what the bot does TODAY, trade for trade.

WHY THIS FILE EXISTS
    step456 adds three switchable rules from his newest videos. Every one of
    them ships OFF. "Off" is only a claim until something checks it, so this
    writes down every trade the bot takes with the switches absent, and
    `test_tjr_bot.test_everything_off_reproduces_the_recorded_baseline`
    re-runs the same sessions afterwards and demands the same list, field by
    field.

    The file was produced BEFORE tjr_bot.py was edited. That is the whole
    point: it is a photograph of the old binary, not a re-description of the
    new one.

USAGE
    python3 step456_baseline.py            # write step456_baseline.json
    python3 step456_baseline.py --check    # re-run and compare, exit 1 on drift

RESEARCH ONLY. No orders, no network, no git.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tjr_bot
from tjr_bot import Config, NewsCalendar, TjrBot

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = f"{REPO}/step456_baseline.json"

# A full year of real sessions, which is the span Wallace asked the
# before/after to cover.
START, END = "2025-07-25", "2026-07-24"
SYMBOLS = ("SPY", "QQQ")

# Every field of a Trade that a change in the entry logic could move, AS THEY
# STOOD BEFORE step456. This list is frozen: it is what the recorded baseline
# holds, and widening it would quietly retire the comparison. The floats are
# rounded so a re-run on the same machine matches without the tolerance being
# loose enough to hide a real difference.
FIELDS = ["symbol", "direction", "level_price", "level_tf", "confirm_kind",
          "pullback_kind", "entry_t", "entry", "stop", "risk_per_share",
          "shares", "notional", "risk_dollars", "risk_wanted", "budget_share",
          "second_setup_expected", "size_basis", "targets", "target_srcs",
          "escalated", "regime", "exit_t", "exit_price", "outcome", "pnl",
          "cost", "r_multiple", "account_after", "targets_filled"]

# Fields step456 ADDED. They are carried on every row so the before/after run
# can report them, and stripped before the baseline comparison — a field that
# did not exist in the old binary cannot be evidence that the old binary
# behaved differently. With every switch off `trigger_kind` reads "1-minute
# break of structure" on every trade, because that was the only trigger there
# was; the other three stay empty.
EXTRA = ["trigger_kind", "smt", "smt_role", "smt_completion"]

_CACHE: dict = {}


def frames(symbol: str) -> dict:
    if symbol not in _CACHE:
        _CACHE[symbol] = {
            tf: tjr_bot.to_et_frame(
                pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_{tf}.parquet"))
            for tf in ("5m", "1m")}
    return _CACHE[symbol]


def window(day, cfg) -> dict:
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    out = {}
    for s in SYMBOLS:
        f = frames(s)
        out[s] = {tf: f[tf][(f[tf]["t"] >= lo) & (f[tf]["t"] < hi)]
                  .reset_index(drop=True) for tf in ("5m", "1m")}
    return out


def trading_days(start, end) -> list:
    days = set()
    for s in SYMBOLS:
        t = frames(s)["1m"]["t"]
        d = t[(t >= pd.Timestamp(start)) &
              (t < pd.Timestamp(end) + pd.Timedelta(days=1))]
        tt = d[(d.dt.time >= tjr_bot.OPEN_T) & (d.dt.time < tjr_bot.CLOSE_T)]
        days |= set(tt.dt.normalize().unique())
    return sorted(days)


def _clean(v):
    if isinstance(v, float):
        return round(v, 8)
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, (pd.Timestamp,)):
        return str(v)
    if v is None or isinstance(v, (str, int, bool)):
        return v
    return str(v)


# step461 moved a DEFAULT, not just added a switch: `entries_run_to_the_close`
# ships True on Wallace's instruction, so `Config()` no longer describes the
# binary this file photographed. Reproducing that binary now takes one
# explicit flag, and this is where it is named so the photograph keeps meaning
# what it meant. Everything else about the comparison is unchanged.
#
# step465 moved a second one the same way: `size_per_trade` ships True, so the
# day-budget machinery the photograph was taken on now takes its own flag too.
# The name is kept because every caller and every test says OLD_CLOCK; what it
# means is "the flags that reproduce the photographed binary", and there are
# two of them now.
OLD_CLOCK = dict(entries_run_to_the_close=False, size_per_trade=False)


def run(cfg: Config | None = None, start=START, end=END) -> dict:
    """Walk the sessions and return everything a change could move: the
    trades, and every stand-down reason with its count."""
    cfg = cfg or Config(**OLD_CLOCK)
    bot = TjrBot(cfg, NewsCalendar())
    rows, reasons = [], {}
    for day in trading_days(start, end):
        res = bot.run_day(window(day, cfg), day)
        for tr in res["trades"]:
            row = {"day": str(pd.Timestamp(day).date())}
            row.update({f: _clean(getattr(tr, f)) for f in FIELDS})
            row.update({f: _clean(getattr(tr, f, "")) for f in EXTRA})
            rows.append(row)
        for sym, why in res["stand_down"].items():
            reasons[why] = reasons.get(why, 0) + 1
    return {"start": start, "end": end, "symbols": list(SYMBOLS),
            "sessions": len(trading_days(start, end)),
            "account_end": round(bot.account, 6),
            "trades": rows, "stand_down": dict(sorted(reasons.items()))}


def load() -> dict:
    with open(OUT) as fh:
        return json.load(fh)


def as_recorded(out: dict) -> dict:
    """The run, reduced to what the old binary could have written down —
    every step456-only field dropped. This is what the baseline is compared
    against, so the comparison stays a statement about BEHAVIOUR."""
    return {**out, "trades": [{k: v for k, v in r.items() if k not in EXTRA}
                              for r in out["trades"]]}


def main(argv):
    if "--check" in argv:
        want, got = load(), as_recorded(run())
        want = as_recorded(want)
        ok = json.dumps(want, sort_keys=True) == json.dumps(got, sort_keys=True)
        print("identical" if ok else "DRIFTED")
        if not ok:
            a, b = want["trades"], got["trades"]
            print(f"  baseline {len(a)} trades, now {len(b)}")
            for i in range(max(len(a), len(b))):
                x = a[i] if i < len(a) else None
                y = b[i] if i < len(b) else None
                if x != y:
                    print(f"  first difference at trade {i}:")
                    print(f"    was {x}")
                    print(f"    now {y}")
                    break
        return 0 if ok else 1
    out = run()
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"{out['sessions']} sessions, {len(out['trades'])} trades, "
          f"account -> {out['account_end']:,.2f}")
    print(f"written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
