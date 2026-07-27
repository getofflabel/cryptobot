"""
step456_before_after.py — the same year, his old teaching and his newest.

WHY THIS FILE EXISTS
    Wallace asked for "a before and after of that playlist ran on the past
    year". step456 put three rules from his newest videos into `tjr_bot.py`
    behind switches that all ship OFF, so ONE binary produces both halves.
    This runs it both ways over the same sessions and, one switch at a time,
    shows what each rule on its own is worth.

WHAT IT DOES NOT DO
    It does not tune anything and it is not evidence. He does not count
    replay as evidence and neither do we — step454 section 4a is blunt about
    it: his own year is roughly a 60-65% win rate at a reward-to-risk a
    little above 1:1, and "beating any of them in a replay is a bug report,
    not a success". The number this run is actually FOR is the trade count.
    step436 item 11 has him trading 7-15 days a month; a build that trades
    most days has dropped a stand-down condition.

USAGE
    python3 step456_before_after.py                # the full year
    python3 step456_before_after.py 2026-01-05 2026-07-24

RESEARCH ONLY. No orders, no network beyond the cached parquet, no git.
"""

from __future__ import annotations

import collections
import sys

import step456_baseline as B
from tjr_bot import Config

# Each switch on its own, so a rule that costs money is visible rather than
# averaged into the pile. The order is the order step454 puts them in.
ONE_AT_A_TIME = [
    ("SMT: bias only (120)", dict(smt_enabled=True)),
    ("SMT: + it picks the chart (100, 112, 120)",
     dict(smt_enabled=True, smt_picks_the_instrument=True)),
    ("SMT: + it joins the menu (112, 103)",
     dict(smt_enabled=True, smt_in_confirmation_menu=True)),
    ("the 79% extension (066, 099, 112)", dict(extension_79_enabled=True)),
    ("the 1-minute inverse fair value gap (112)",
     dict(trigger_menu_1m_gap_inversion=True)),
    ("step 2B: a fresh 5-minute sweep after the open (112)",
     dict(require_fresh_5m_sweep_after_open=True)),
    ("the continuation confluence has to hold on a close (112)",
     dict(invalidate_on_close_beyond_continuation=True)),
]


def summarise(out: dict) -> dict:
    tr = out["trades"]
    wins = [t for t in tr if t["pnl"] > 0]
    days = len({t["day"] for t in tr})
    return {
        "trades": len(tr),
        "days_traded": days,
        "sessions": out["sessions"],
        "share_of_sessions": (100.0 * days / out["sessions"]
                              if out["sessions"] else 0.0),
        "days_per_month": days / (out["sessions"] / 21.0) if out["sessions"] else 0.0,
        "win_rate": 100.0 * len(wins) / len(tr) if tr else 0.0,
        "net": out["account_end"] - 100_000.0,
        "account_end": out["account_end"],
    }


def line(tag: str, s: dict) -> str:
    return (f"  {tag:<52} {s['trades']:>4} trades  "
            f"{s['days_traded']:>4} days ({s['share_of_sessions']:.0f}% of "
            f"sessions, {s['days_per_month']:.1f}/month)  "
            f"win {s['win_rate']:.1f}%  net {s['net']:>+11,.0f}")


def main(argv):
    start = argv[1] if len(argv) > 1 else B.START
    end = argv[2] if len(argv) > 2 else B.END

    print("=" * 100)
    print(f"step456 — the same {start} to {end} sessions, twice")
    print("=" * 100)
    print()

    before = B.run(Config(), start, end)
    after = B.run(Config.newest_teaching(), start, end)
    sb, sa = summarise(before), summarise(after)

    print("THE TWO HALVES")
    print(line("BEFORE — every step456 switch off", sb))
    print(line("AFTER  — every step456 switch on", sa))
    print()

    print("EACH RULE ON ITS OWN, against BEFORE")
    for tag, kw in ONE_AT_A_TIME:
        s = summarise(B.run(Config(**kw), start, end))
        d = s["trades"] - sb["trades"]
        print(line(tag, s) + f"   [{d:+d} trades]")
    print()

    print("WHAT FIRED, in the AFTER run")
    for field, title in (("confirm_kind", "5-minute confirmation"),
                         ("trigger_kind", "1-minute trigger"),
                         ("pullback_kind", "continuation confluence")):
        print(f"  {title}:")
        for k, n in collections.Counter(
                t.get(field, "") for t in after["trades"]).most_common():
            print(f"      {n:>3}  {k or '(not recorded)'}")
    smt = [t for t in after["trades"] if t.get("smt")]
    print(f"  a divergence was live on {len(smt)} of {len(after['trades'])} "
          f"trades; roles: "
          f"{dict(collections.Counter(t.get('smt_role') for t in smt))}")
    print()

    print("HIS OWN NUMBERS, which are the bar rather than the target")
    print("  UPDATED-2026 Jan-June : 64.29% win, 1:1.233, 7-15 trading days a month")
    print("  099  April-October    : average win $22,000, average loss ~$11,000")
    print("  120  365 days to April: ~60% win, ~1:1.5, overall green")
    print("  A replay that beats these is a bug report, not a success (step454 4a).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
