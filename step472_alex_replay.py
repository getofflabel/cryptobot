#!/usr/bin/env python3
"""step472_alex_replay.py — the four gaps closed, and what closing them did.

WHAT THIS MEASURES AND WHY IT IS SHAPED THIS WAY

    step470 built the June-2026 "spine" — one pair, one timeframe, one
    session, one engulfing candle — and reported a pace forty times under what
    he says he does. Four pieces of him were missing from that build:

        1. THE HEAD AND SHOULDERS, his own go-to pattern and the one he names
           for growing a small account.
        2. STRUCTURE TARGETS. The flat 1:2 was OUR simplification of a floor
           he states for ACCEPTING a trade.
        3. STRUCTURE-SHIFT EXITS, cutting and holding on his change of
           character rather than on nothing at all.
        4. QUALITY-WEIGHTED SIZING off his own confluence count.

    Each is reported ON ITS OWN and in combination, each against the same
    control step471 made the standard: SAME ENTRIES, SAME STOP DISTANCES,
    DIRECTION REVERSED. A pattern whose fade beats it is noise no matter what
    its dollars say.

LANGUAGE

    LEVERAGE, never "risk %". Every percentage says which one it is: a move in
    the PRICE, or a change in the ACCOUNT. Costs are charged and never shown
    as a line item — they are already inside every net dollar here.

    Each instrument runs on its OWN $100,000, exactly as step470 did, so the
    numbers on this page and that one are directly comparable.

NO VENUE. NO ORDER. NO FETCH. NO WRITE outside this file's own CSV.

Run:  python3 step472_alex_replay.py            (12 months + 5 years)
      python3 step472_alex_replay.py --quick    (12 months only)
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alex_engine as ae

REPO = os.path.dirname(os.path.abspath(__file__))

# A CLOSED TRADE IS A CLOSED TRADE. His Friday exit closes at a real loss and
# is counted; so is every exit the runner and the structure-shift rule produce.
CLOSED = ["stop", "target", "friday", "flip",
          "runner_stop", "runner_flip", "runner_friday", "runner_cap"]

WINDOWS = [("12 months", "2025-07-27", "2026-07-26"),
           ("5 years", "2021-07-05", "2026-07-26")]

# HIS OWN CLAIM, which is the bar every pace number below is measured against.
#   "one to three percent a week" — his stated growth on a funded account.
HIS_PACE_LO, HIS_PACE_HI = 0.01, 0.03


# =============================================================== THE ARMS
def arm(**over) -> dict:
    return dict(over)


ARMS = {
    # step470 exactly: engulf only, flat 1:2, one size for everything
    "step470 spine (engulf, flat 1:2)": arm(
        pattern="engulf", signal_mode="engulf", target_mode="fixed_r",
        size_by_quality=False, use_ema50=False),

    # the four gaps, each alone, on top of that baseline
    "+ head and shoulders only": arm(
        pattern="hs", signal_mode="engulf", target_mode="fixed_r",
        size_by_quality=False, use_ema50=False),
    "+ structure FILTER only (his newest)": arm(
        pattern="engulf", signal_mode="engulf", target_mode="filtered_2r",
        size_by_quality=False, use_ema50=False),
    "+ structure RIDE only (hold to the level)": arm(
        pattern="engulf", signal_mode="engulf", target_mode="structure",
        size_by_quality=False, use_ema50=False),
    "+ quality-weighted size only": arm(
        pattern="engulf", signal_mode="engulf", target_mode="fixed_r",
        size_by_quality=True, use_ema50=True),
    "+ his rejection candle only": arm(
        pattern="engulf", signal_mode="either", target_mode="fixed_r",
        size_by_quality=False, use_ema50=False),
    "+ rejection with no level under it": arm(
        pattern="engulf", signal_mode="either", target_mode="fixed_r",
        size_by_quality=False, use_ema50=False, rejection_needs_area=False),

    # and the whole thing
    "step472 engulf spine": arm(pattern="engulf"),
    "step472 head and shoulders": arm(pattern="hs"),
    "step472 BOTH PATTERNS": arm(pattern="both"),
    "step472 BOTH, engulf trigger only": arm(pattern="both",
                                             signal_mode="engulf"),
    "step472 BOTH, engulf trigger, flat size": arm(pattern="both",
                                                   signal_mode="engulf",
                                                   size_by_quality=False),
}

# switches measured on top of the full build, one at a time
SENSITIVITIES = {
    "his two-a-week cap ON": arm(pattern="both", human_cadence_cap=True),
    "structure-shift exit ON": arm(pattern="both", exit_on_structure_flip=True),
    "runner ON (half past target, 1:4 ceiling)": arm(pattern="both", runner=True),
    "weekly-close direction ON": arm(pattern="both", weekly_bias=True),
    "top-down layers ON (weekly+daily)": arm(pattern="both",
                                             context_tfs=("1w", "1d")),
    "his engulf-quality floor at 3": arm(pattern="both", min_engulfed=3),
    "size anchored at the top instead": arm(pattern="both",
                                            quality_anchor="top"),
    "flat size, no quality dial": arm(pattern="both", size_by_quality=False),
    "his high-risk right-shoulder entry ON": arm(pattern="both",
                                                 hs_allow_right_shoulder=True),
    "neckline need not be an area": arm(pattern="both",
                                        hs_require_area_neckline=False),
    "his rejection half ON (level-gated)": arm(pattern="both",
                                               signal_mode="either"),
}

# THE LAYERED READINGS. His June-2026 spine is one timeframe and it is the
# newest, so the shipping default is the spine alone. But the weekly-close
# rule (2026-05-25) and the top-down order (2026-02-02) are also his, one
# month and five months older, and what they do to the deep window is the
# single largest number this file produces. Measured, never assumed.
LAYERED = {
    "spine alone (ships)": arm(pattern="both"),
    "+ his weekly-close direction": arm(pattern="both", weekly_bias=True),
    "+ weekly close, engulf pattern only": arm(pattern="engulf",
                                               weekly_bias=True),
    "+ weekly close + top-down layers": arm(pattern="both", weekly_bias=True,
                                            context_tfs=("1w", "1d")),
    "+ weekly close, his engulf floor at 3": arm(pattern="both",
                                                 weekly_bias=True,
                                                 min_engulfed=3),
    "+ weekly close, head and shoulders only": arm(pattern="hs",
                                                   weekly_bias=True),
}


# ============================================================ MEASUREMENT
def stats(f: pd.DataFrame, weeks: float, start_equity: float) -> dict:
    done = f[f["outcome"].isin(CLOSED)]
    n = len(done)
    wins = done[done["pnl"] > 0]
    net = done["pnl"].sum()
    return {
        "trades": n,
        "per_week": n / weeks if weeks else 0.0,
        "win_rate": 100.0 * len(wins) / n if n else 0.0,
        "mean_r": done["r"].mean() if n else 0.0,
        "net": net,
        # THE PACE. Share of the ACCOUNT added per week — not a price move.
        "acct_per_week": (net / start_equity / weeks) if weeks else 0.0,
        "lev_med": done["leverage"].median() if n else 0.0,
        "lev_hi": done["leverage"].max() if n else 0.0,
        "size_med": done["quality"].median() if n else 1.0,
        "open": int((f["outcome"] == "open").sum()),
        "held_out": int((f["outcome"] == "held_out").sum()),
    }


def run(over: dict, start, end, cache: dict, control: str = "none") -> tuple:
    o = dict(over)
    o["control"] = control
    book = ae.run_book(start=start, end=end, cfg_over=o, cache=cache,
                       verbose=False, mode="dumb")
    return ae.frame(book), book


def line(name: str, s: dict, extra: str = "") -> str:
    return (f"  {name:<42s} {s['trades']:>4d} {s['per_week']:>6.2f} "
            f"{s['win_rate']:>6.1f}% {s['mean_r']:>6.2f} "
            f"${s['net']:>+11,.0f} {s['acct_per_week']*100:>+7.2f}% "
            f"{s['lev_med']:>5.1f}x{extra}")


HEAD = ("  {:<42s} {:>4s} {:>6s} {:>7s} {:>6s} {:>12s} {:>8s} {:>6s}".format(
    "", "n", "/week", "won", "mean R", "net $", "acct/wk", "lev"))


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    quick = "--quick" in argv
    windows = WINDOWS[:1] if quick else WINDOWS
    cache: dict = {}
    rows = []

    print("=" * 118)
    print("step472 — THE ALEX GONZALEZ ENGINE WITH THE FOUR MISSING PIECES "
          "BUILT. Replay only; no order on any venue.")
    print("Each instrument on its OWN $100,000. 'acct/wk' is the share of "
          "THAT ACCOUNT added per week — not a price move.")
    print("His own stated pace is +1% to +3% of the account per week.")
    print("=" * 118)

    for wname, wstart, wend in windows:
        weeks = (pd.Timestamp(wend) - pd.Timestamp(wstart)).days / 7.0
        print(f"\n\n{'#' * 118}\n#  {wname.upper()}   {wstart} -> {wend}   "
              f"({weeks:.0f} weeks)\n{'#' * 118}")

        # ---------------------------------------------------- 1. THE BOOK
        print(f"\n1. THE BOOK — four instruments, four accounts, $400,000 "
              f"in total. Costs are already inside every net figure.")
        print(HEAD)
        books = {}
        for name, over in ARMS.items():
            f, book = run(over, wstart, wend, cache)
            books[name] = (f, book)
            s = stats(f, weeks, 400_000.0)
            print(line(name, s))
            rows.append({"window": wname, "arm": name, "instrument": "BOOK",
                         "control": "none", **s})

        # ------------------------------------------------- 2. THE CONTROL
        print(f"\n2. THE CONTROL — same entries, same days, same stop "
              f"distances, DIRECTION REVERSED.")
        print("   If fading a pattern beats taking it, that pattern's "
              "direction call is noise whatever its dollars say.")
        print("  {:<42s} {:>9s} {:>9s} {:>9s} {:>9s}   {}".format(
            "", "won", "FADED", "mean R", "FADED R", "verdict"))
        for name in ("step472 engulf spine", "step472 head and shoulders",
                     "step472 BOTH PATTERNS", "step472 BOTH, engulf trigger only",
                     "step472 BOTH, engulf trigger, flat size",
                     "+ head and shoulders only",
                     "+ structure FILTER only (his newest)",
                     "step470 spine (engulf, flat 1:2)"):
            f, _ = books[name]
            g, _ = run(ARMS[name], wstart, wend, cache, control="reversed")
            a = stats(f, weeks, 400_000.0)
            b = stats(g, weeks, 400_000.0)
            v = ("real — beats its own fade" if a["mean_r"] > b["mean_r"] + 0.05
                 else "NOISE — the fade wins" if b["mean_r"] > a["mean_r"] + 0.05
                 else "indistinguishable from its fade")
            print("  {:<42s} {:>8.1f}% {:>8.1f}% {:>9.2f} {:>9.2f}   {}".format(
                name, a["win_rate"], b["win_rate"], a["mean_r"], b["mean_r"], v))
            rows.append({"window": wname, "arm": name, "instrument": "BOOK",
                         "control": "reversed", **b})

        # --------------------------------------------- 3. PER INSTRUMENT
        print(f"\n3. PER INSTRUMENT — the full build, both patterns. His own "
              f"configuration is ONE PAIR, EUR/USD;")
        print("   the other three are OUR extension of him and are read "
              "separately for that reason.")
        f, book = books["step472 BOTH PATTERNS"]
        print(HEAD)
        for inst in ae.INSTRUMENTS:
            fi = f[f["instrument"] == inst]
            s = stats(fi, weeks, 100_000.0)
            print(line(inst, s))
            rows.append({"window": wname, "arm": "step472 BOTH PATTERNS",
                         "instrument": inst, "control": "none", **s})
        # and the same four, faded
        g, _ = run(ARMS["step472 BOTH PATTERNS"], wstart, wend, cache,
                   control="reversed")
        for inst in ae.INSTRUMENTS:
            rows.append({"window": wname, "arm": "step472 BOTH PATTERNS",
                         "instrument": inst, "control": "reversed",
                         **stats(g[g["instrument"] == inst], weeks, 100_000.0)})

        # ------------------------------------------------ 4. BY PATTERN
        print(f"\n4. WHERE THE MONEY CAME FROM — the full build split by "
              f"which of his two setups fired,")
        print("   and by which of his triggers pulled it.")
        print("  {:<42s} {:>4s} {:>7s} {:>6s} {:>12s}".format(
            "", "n", "won", "mean R", "net $"))
        done = f[f["outcome"].isin(CLOSED)]
        for key in ("pattern", "signal_kind"):
            for v in sorted(done[key].dropna().unique()):
                sub = done[done[key] == v]
                print("  {:<42s} {:>4d} {:>6.1f}% {:>6.2f} ${:>+11,.0f}".format(
                    f"{key} = {v}", len(sub), 100.0 * (sub["pnl"] > 0).mean(),
                    sub["r"].mean(), sub["pnl"].sum()))
        print("\n   and by how much confluence he had, which is what sets the "
              "size:")
        for q in sorted(done["quality_pts"].unique()):
            sub = done[done["quality_pts"] == q]
            print("  {:<42s} {:>4d} {:>6.1f}% {:>6.2f} ${:>+11,.0f}".format(
                f"{int(q)} confluences  (size {sub['quality'].iloc[0]:.0%} "
                f"of full)", len(sub), 100.0 * (sub["pnl"] > 0).mean(),
                sub["r"].mean(), sub["pnl"].sum()))

        # -------------------------------------------- 5. SENSITIVITIES
        print(f"\n5. EVERY SWITCH, ONE AT A TIME, ON TOP OF THE FULL BUILD.")
        print("   The first is his cadence cap, which ships OFF on Wallace's "
              "ruling: its purpose in his own")
        print("   material is not over-trading and not letting emotion in, "
              "and a bot on a demo venue has neither.")
        print(HEAD)
        base = stats(f, weeks, 400_000.0)
        print(line("(the full build, for reference)", base))
        for name, over in SENSITIVITIES.items():
            g2, bk = run(over, wstart, wend, cache)
            s = stats(g2, weeks, 400_000.0)
            skipped = sum(b.get("cap_skipped", 0) for b in bk.values())
            extra = f"   ({skipped} setups refused by the cap)" if skipped else ""
            print(line(name, s, extra))
            rows.append({"window": wname, "arm": name, "instrument": "BOOK",
                         "control": "none", **s})

        # ------------------------------------------ 5b. THE LAYERED READING
        print(f"\n5b. HIS OWN HIGHER-TIMEFRAME RULES, WHICH THE JUNE SPINE "
              f"TELLS A BEGINNER TO IGNORE.")
        print("    'those candlesticks opening and closing dictate the "
              "direction of the following week' (2026-05-25)")
        print("    and 'we go weekly, daily and then we stop at the 4 hour' "
              "(2026-02-02). The June spine is NEWER and")
        print("    says one timeframe only, so the spine alone is what ships. "
              "This is what the layers do to it.")
        print(HEAD + "   fade R")
        for name, over in LAYERED.items():
            g3, _ = run(over, wstart, wend, cache)
            h3, _ = run(over, wstart, wend, cache, control="reversed")
            s3 = stats(g3, weeks, 400_000.0)
            s4 = stats(h3, weeks, 400_000.0)
            print(line(name, s3, f"   {s4['mean_r']:>+6.2f}"))
            rows.append({"window": wname, "arm": "LAYERED: " + name,
                         "instrument": "BOOK", "control": "none", **s3})
            rows.append({"window": wname, "arm": "LAYERED: " + name,
                         "instrument": "BOOK", "control": "reversed", **s4})

        # ------------------------------------------------ 6. THE PACE
        print(f"\n6. THE PACE, AGAINST HIS OWN CLAIM. He says +1% to +3% of "
              f"the ACCOUNT per week.")
        wkly, _ = run(LAYERED["+ his weekly-close direction"], wstart, wend,
                      cache)
        eur = f[f["instrument"] == "EUR_USD"]
        for label, fr, eq in (("his own configuration, EUR/USD alone", eur,
                               100_000.0),
                              ("our four-instrument book", f, 400_000.0),
                              ("EUR/USD with his weekly-close rule on",
                               wkly[wkly["instrument"] == "EUR_USD"],
                               100_000.0),
                              ("the book with his weekly-close rule on",
                               wkly, 400_000.0)):
            s = stats(fr, weeks, eq)
            pace = s["acct_per_week"]
            gap = (HIS_PACE_LO / pace) if pace > 0 else float("inf")
            verdict = (f"{gap:,.0f}x under his floor" if pace > 0
                       else "loses money")
            if pace >= HIS_PACE_LO:
                verdict = "inside his own band"
            print(f"  {label:<42s} {pace*100:>+7.2f}% of the account per week"
                  f"   ->  {verdict}")

    out = pd.DataFrame(rows)
    p = os.path.join(REPO, "step472_alex_results.csv")
    out.to_csv(p, index=False)
    print(f"\n\nEvery row above: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
