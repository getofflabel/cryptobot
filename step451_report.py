"""
step451_report.py — run the crypto trigger-timeframe comparison and print it.

One job per (pair, trigger). Each job walks that pair's WHOLE cached span, so
every setting sees exactly the same days for that pair and no result is ever
computed over a different window from the one it is compared against. The span
differs BETWEEN pairs (Alpaca's history starts where each pair was listed) and
is printed per pair.

Nothing here decides anything. It runs step451_trigger_tf and prints.
Reads parquet, places no orders, runs no git.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys

import pandas as pd

import step451_trigger_tf as S
import tjr_crypto

REPO = os.path.dirname(os.path.abspath(__file__))
OUT = f"{REPO}/step451_results.json"


def job(args):
    pair, m, start, end = args
    try:
        r = S.run_pair(pair, m, start, end)
    except FileNotFoundError:
        return {"pair": pair, "trigger": m, "missing": True}
    return {
        "pair": pair, "trigger": m, "days": r["days"],
        "first_day": r["first_day"], "last_day": r["last_day"],
        "rows": [S.trade_row(t, pair) for t in r["trades"]],
        "reasons": sorted(r["reasons"].items(), key=lambda kv: -kv[1])[:4],
    }


def run(pairs=None, triggers=S.TRIGGERS, start=None, end=None, workers=6):
    pairs = list(pairs or tjr_crypto.PAIRS)
    jobs = [(p, m, start, end) for p in pairs for m in triggers]
    with mp.Pool(workers) as pool:
        res = []
        for i, r in enumerate(pool.imap_unordered(job, jobs), 1):
            res.append(r)
            print(f"  [{i}/{len(jobs)}] {r['pair']:9s} trigger {r['trigger']:>2}m  "
                  f"{len(r.get('rows', [])):>4} trades  "
                  f"{r.get('first_day')} .. {r.get('last_day')}", flush=True)
    return res


def collate(res, triggers=S.TRIGGERS) -> dict:
    by = {m: [] for m in triggers}
    days = {m: 0 for m in triggers}
    spans = {}
    for r in res:
        if r.get("missing"):
            continue
        by[r["trigger"]] += r["rows"]
        days[r["trigger"]] += r["days"]
        spans.setdefault(r["pair"], (r["first_day"], r["last_day"], r["days"]))
    n_pairs = len(spans)
    out = {"spans": spans, "settings": {}}
    for m in triggers:
        rows = by[m]
        s = S.summarise(rows, days[m], 100_000.0, max(n_pairs, 1))
        s["pair_days_total"] = days[m]
        if rows:
            s["trades_per_pair_day"] = round(len(rows) / max(days[m], 1), 4)
        out["settings"][m] = s
    # ------------------------------------------------------- populations
    #
    # THE UNIT IS THE PAIR-DAY, NOT THE TIMESTAMP. The bot takes at most one
    # trade per pair per day, and a 3-minute grid and a 1-minute grid almost
    # never stamp the same trade at the same minute — diffing raw timestamps
    # would report ~100% different for two runs taking the same setups, which
    # is a measurement artefact, not a finding. So: same pair-day means the
    # same opportunity was taken; same pair-day AND same direction AND the
    # same marked level means it is literally the same setup, entered at a
    # different moment.
    base = triggers[0]

    def key(r):
        return (r["pair"], str(r["day"])[:10])

    def ident(r):
        return (r["pair"], str(r["day"])[:10], r["direction"],
                round(float(r["level_price"]), 6))

    bmap = {key(r): r for r in by[base]}
    bident = {ident(r) for r in by[base]}
    pops, paired = {}, {}
    for m in triggers:
        rows = by[m]
        k = {key(r) for r in rows}
        i = {ident(r) for r in rows}
        same = [r for r in rows if ident(r) in bident]
        pops[m] = {
            "trades": len(rows),
            "pair_days_not_traded_by_the_1m_run": len(k - set(bmap)),
            "pct_of_this_run_not_in_the_1m_run": round(
                100.0 * len(k - set(bmap)) / max(len(k), 1), 1),
            "1m_pair_days_absent_here": len(set(bmap) - k),
            "same_pair_day_as_a_1m_trade": len(k & set(bmap)),
            "literally_the_same_setup_as_a_1m_trade": len(i & bident),
            "pct_of_this_run_that_is_the_same_setup": round(
                100.0 * len(i & bident) / max(len(i), 1), 1),
            "raw_entry_timestamp_matches_1m": len(
                {(r["pair"], str(r["entry_t"])) for r in rows} &
                {(r["pair"], str(r["entry_t"])) for r in by[base]}),
        }
        # the paired comparison: only the trades BOTH runs took, so the stop
        # distance is not being compared across two different populations
        if same:
            b_by_ident = {ident(r): r for r in by[base]}
            ds, dt, dr = [], [], []
            for r in same:
                b = b_by_ident[ident(r)]
                ds.append((r["stop_move_pct_of_price"],
                           b["stop_move_pct_of_price"]))
                if r["confirm_to_entry_min"] is not None and \
                        b["confirm_to_entry_min"] is not None:
                    dt.append((r["confirm_to_entry_min"],
                               b["confirm_to_entry_min"]))
                dr.append((r["r_multiple"], b["r_multiple"]))
            paired[m] = {
                "n_same_setup": len(same),
                "median_stop_move_pct_of_price_this": round(
                    float(pd.Series([a for a, _ in ds]).median()), 4),
                "median_stop_move_pct_of_price_1m": round(
                    float(pd.Series([b for _, b in ds]).median()), 4),
                "median_stop_gap_this_minus_1m_pct_of_price": round(
                    float(pd.Series([a - b for a, b in ds]).median()), 4),
                "median_confirm_to_entry_min_this": (
                    round(float(pd.Series([a for a, _ in dt]).median()), 1)
                    if dt else None),
                "median_confirm_to_entry_min_1m": (
                    round(float(pd.Series([b for _, b in dt]).median()), 1)
                    if dt else None),
                "avg_r_this": round(float(pd.Series([a for a, _ in dr]).mean()), 3),
                "avg_r_1m": round(float(pd.Series([b for _, b in dr]).mean()), 3),
            }
    out["populations"] = pops
    out["paired_on_the_same_setup"] = paired
    out["_rows"] = {m: by[m] for m in triggers}
    return out


def table(out, triggers=S.TRIGGERS) -> str:
    hd = ("setting", "trades", "per pair-day", "win %", "avg R", "net $",
          "worst drop $", "conf->entry", "stop % of price")
    lines = [f"{hd[0]:<9}{hd[1]:>8}{hd[2]:>14}{hd[3]:>8}{hd[4]:>8}"
             f"{hd[5]:>13}{hd[6]:>14}{hd[7]:>13}{hd[8]:>17}"]
    for m in triggers:
        s = out["settings"][m]
        if not s.get("trades"):
            lines.append(f"{str(m)+'m':<9}{0:>8}{'-':>14}{'-':>8}{'-':>8}"
                         f"{'-':>13}{'-':>14}{'-':>13}{'-':>17}")
            continue
        lines.append(
            f"{str(m)+'m':<9}{s['trades']:>8}{s['trades_per_pair_day']:>14.4f}"
            f"{s['win_rate_pct_of_trades']:>8.1f}{s['avg_r_multiple']:>8.3f}"
            f"{s['net_dollars']:>13,.0f}{s['max_drawdown_dollars']:>14,.0f}"
            f"{str(s['median_confirm_to_entry_min'])+' min':>13}"
            f"{s['median_stop_move_pct_of_price']:>17.4f}")
    return "\n".join(lines)


def main(argv):
    pairs = None
    workers = 6
    for a in argv[1:]:
        if a.startswith("--pairs="):
            pairs = a.split("=", 1)[1].split(",")
        elif a.startswith("--workers="):
            workers = int(a.split("=", 1)[1])
    res = run(pairs, workers=workers)
    out = collate(res)
    print()
    print("PER-PAIR SPAN (identical across every setting for that pair)")
    for p, (a, b, d) in sorted(out["spans"].items()):
        print(f"  {p:9s} {a} .. {b}   {d} days")
    print()
    print(table(out))
    print()
    print("POPULATIONS, against the 1-minute run (unit = the pair-day)")
    print(json.dumps(out["populations"], indent=2))
    print()
    print("THE SAME SETUPS ONLY — both runs took this trade, so nothing here")
    print("is comparing one population against another")
    print(json.dumps(out["paired_on_the_same_setup"], indent=2))
    rows = out.pop("_rows")
    with open(OUT, "w") as f:
        json.dump({"settings": out["settings"], "spans": out["spans"],
                   "populations": out["populations"],
                   "paired_on_the_same_setup": out["paired_on_the_same_setup"],
                   "rows": {m: [{k: str(v) for k, v in r.items()} for r in v]
                            for m, v in rows.items()}}, f, indent=2, default=str)
    print(f"\nwritten: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
