"""
step455_report.py — turn what step455_measure.py walked into the tables.

Reads only the trade-level CSVs that step455_measure.py wrote, plus the bar
files (to count how many weeks the bot actually walked, which is the
denominator for "trades a week" and must be the SESSIONS' weeks rather than
the trades' weeks).

WHAT IT PRINTS
    1. the S&P year by year, new numbers beside the pre-step453 ones
    2. crypto year by year, pooled across the eight pairs, and per pair
    3. gold
    4. everything pooled, which is the account Wallace actually has
    5. the day-boundary artefact on crypto, measured, as a sensitivity check

THE POOLED DOLLARS, SAID PLAINLY
    Every market was walked on its own fresh $100,000, and each crypto pair
    got its own book because `tjr_crypto` gives each pair its own day budget.
    So the pooled dollar figure is the sum of parallel independent books, NOT
    one account compounding. The figure that does not depend on that choice is
    the average result as a multiple of what was risked, and it is reported
    beside it every time.

RESEARCH ONLY. Reads CSVs and parquet, prints and writes step455_* files.
"""

from __future__ import annotations

import os
import sys

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import tjr_crypto as tc
from step455_measure import load_pair, weeks_walked

ACCOUNT = 100_000.0


def load_trades() -> pd.DataFrame:
    out = []
    for f in ("step455_sp_trades.csv", "step455_crypto_trades.csv",
              "step455_gold_trades.csv"):
        p = f"{REPO}/{f}"
        if os.path.exists(p):
            d = pd.read_csv(p)
            if len(d):
                out.append(d)
    d = pd.concat(out, ignore_index=True)
    d["entered_utc"] = pd.to_datetime(d["entered_utc"])
    return d.sort_values("entered_utc").reset_index(drop=True)


def figures(d: pd.DataFrame, weeks: int, start: float = ACCOUNT) -> dict:
    n = len(d)
    if not n:
        return {"trades": 0, "per_week": 0.0, "won_pct": 0.0, "mean_x": 0.0,
                "net": 0, "fall": 0, "fall_pct": 0.0, "losing_run": 0}
    pnl = d["pnl_dollars"].to_numpy()
    equity, peak, worst = start, start, 0.0
    run, longest = 0, 0
    for p in pnl:
        equity += p
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
        run = run + 1 if p <= 0 else 0
        longest = max(longest, run)
    return {
        "trades": n,
        "per_week": round(n / max(weeks, 1), 2),
        "won_pct": round(100.0 * (pnl > 0).sum() / n, 1),
        "mean_x": round(float(d["result_x_risked"].mean()), 3),
        "net": int(round(pnl.sum())),
        "fall": int(round(worst)),
        "fall_pct": round(100.0 * worst / start, 2),
        "losing_run": longest,
    }


def books_in(d: pd.DataFrame) -> int:
    """How many separate $100,000 accounts produced these trades.

    ONE for the S&P: tjr_replay runs a single bot over SPY and QQQ, and they
    share the day's budget because they are two charts of one read. ONE for
    gold. But ONE PER CRYPTO PAIR, because tjr_crypto deliberately gives each
    pair its own account clone and its own day budget — handing all eight to
    one run_day would let whichever pair moved first silence the other seven.
    """
    n = 0
    if (d.market == "sp500").any():
        n += 1
    if (d.market == "gold").any():
        n += 1
    n += d.loc[d.market == "crypto", "symbol"].nunique()
    return max(n, 1)


def crypto_weeks() -> dict:
    """(pair, year) -> weeks the pair's own bars covered, and (year) -> the
    weeks any pair covered. Cheap: only the 1-minute timestamps are read."""
    per, per_year = {}, {}
    for pair in tc.PAIRS:
        try:
            t = load_pair(pair)["1m"]["t"]
        except FileNotFoundError:
            continue
        days = pd.Series(t.dt.normalize().unique())
        for y, grp in days.groupby(days.dt.year):
            per[(pair, int(y))] = weeks_walked(grp)
            per_year.setdefault(int(y), set()).update(
                (pd.Timestamp(d) - pd.Timedelta(days=pd.Timestamp(d).weekday())
                 ).normalize() for d in grp)
    return per, {y: max(len(v), 1) for y, v in per_year.items()}


def table(title, rows, cols):
    print(f"\n{title}")
    w = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  " + "  ".join(c.rjust(w[c]) for c in cols))
    print("  " + "  ".join("-" * w[c] for c in cols))
    for r in rows:
        print("  " + "  ".join(str(r[c]).rjust(w[c]) for c in cols))


def main() -> int:
    d = load_trades()
    sp_year = pd.read_csv(f"{REPO}/step455_sp_by_year.csv").set_index("year")
    gold_year = pd.read_csv(f"{REPO}/step455_gold_by_year.csv").set_index("year")
    cw, cw_year = crypto_weeks()

    COLS = ["year", "trades", "per_week", "won_pct", "mean_x", "net",
            "fall", "fall_pct", "losing_run"]

    # ---------------------------------------------------------------- S&P
    old = pd.read_csv(f"{REPO}/step450_trade_rate_by_year.csv").set_index("year")
    sp = d[d.market == "sp500"]
    rows = []
    for y, wk in sp_year["weeks"].items():
        r = figures(sp[sp.year == y], int(wk))
        r["year"] = y
        rows.append(r)
    table("1. THE S&P — SPY and QQQ, one fresh $100,000 a year", rows, COLS)

    print("\n   the same years against the numbers taken before the sizing was "
          "made to match")
    print("   (old = step450_trade_rate_by_year.csv, the bot we were not "
          "running)")
    hdr = (f"   {'year':<6}{'trades':>16}{'a week':>14}{'won':>16}"
           f"{'x risked':>18}{'net $':>22}")
    print(hdr)
    print("   " + "-" * (len(hdr) - 3))
    for r in rows:
        y = r["year"]
        if y not in old.index:
            continue
        o = old.loc[y]
        print(f"   {y:<6}"
              f"{int(o.trades):>7} ->{r['trades']:>6}"
              f"{o.trades_per_week:>7.2f} ->{r['per_week']:>5.2f}"
              f"{o.win_rate_pct:>8.1f}% ->{r['won_pct']:>5.1f}%"
              f"{o.mean_result_x_risked:>+9.3f} ->{r['mean_x']:>+8.3f}"
              f"{int(o.net_dollars):>+11,} ->{r['net']:>+10,}")
    o_net, n_net = int(old.net_dollars.sum()), int(sp.pnl_dollars.sum())
    print(f"   {'all':<6}{int(old.trades.sum()):>7} ->{len(sp):>6}"
          f"{'':>14}{'':>16}{'':>18}{o_net:>+11,} ->{n_net:>+10,}")

    # ------------------------------------------------------------- crypto
    cr = d[d.market == "crypto"]
    rows = []
    for y in sorted(cr.year.unique()):
        r = figures(cr[cr.year == y], cw_year.get(int(y), 52))
        r["year"] = int(y)
        rows.append(r)
    table("2. CRYPTO — the eight live pairs pooled, each pair on its own "
          "fresh $100,000 a year", rows, COLS)

    prows = []
    for pair in tc.PAIRS:
        p = cr[cr.symbol == pair]
        if not len(p):
            continue
        wk = sum(cw.get((pair, int(y)), 0) for y in sorted(p.year.unique()))
        r = figures(p, wk)
        r["pair"] = pair
        r["from"] = f"{p.entered_utc.min():%Y-%m}"
        r["to"] = f"{p.entered_utc.max():%Y-%m}"
        prows.append(r)
    table("   per pair, over whatever span its own bars cover", prows,
          ["pair", "from", "to", "trades", "per_week", "won_pct", "mean_x",
           "net", "fall", "fall_pct", "losing_run"])

    # --------------------------------------------------------------- gold
    rows = []
    for y, wk in gold_year["weeks"].items():
        g = d[(d.market == "gold") & (d.year == y)]
        r = figures(g, int(wk))
        r["year"] = y
        rows.append(r)
    table("3. GOLD — GLD, the whole span its 1-minute record covers "
          f"({d[d.market=='gold'].entered_utc.min():%Y-%m-%d} on)", rows, COLS)

    # -------------------------------------------------------------- pooled
    rows = []
    for y in sorted(d.year.unique()):
        yy = d[d.year == y]
        books = books_in(yy)
        wk = max(cw_year.get(int(y), 0),
                 int(sp_year["weeks"].get(y, 0)) or 0, 1)
        r = figures(yy, wk, start=ACCOUNT * max(books, 1))
        r["year"] = int(y)
        r["books"] = books
        rows.append(r)
    table("4. EVERYTHING POOLED, in the order the trades actually closed",
          rows, ["year", "books"] + COLS[1:])

    allbooks = books_in(d)
    total_weeks = sum(r["trades"] / r["per_week"] for r in rows if r["per_week"])
    tot = figures(d, int(round(total_weeks)), start=ACCOUNT * allbooks)
    print(f"\n   every market, every year, one line")
    print(f"     trades                    {tot['trades']:,}")
    print(f"     trades a week             {tot['per_week']}")
    print(f"     won                       {tot['won_pct']}%")
    print(f"     average result            {tot['mean_x']:+.3f} times what was "
          f"risked")
    print(f"     net                       ${tot['net']:+,}")
    print(f"     deepest fall from a high  ${tot['fall']:,}  "
          f"({tot['fall_pct']}% of the ${ACCOUNT*allbooks:,.0f} the "
          f"{allbooks} separate books started with)")
    print(f"     longest run of losers     {tot['losing_run']}")
    print(f"\n     THE DOLLARS ARE {allbooks} PARALLEL BOOKS, NOT ONE ACCOUNT: "
          f"every market, and\n     every crypto pair inside it, was walked on "
          f"its own fresh $100,000\n     because tjr_crypto gives each pair its "
          f"own day budget. The figure that\n     does not depend on that "
          f"choice is the {tot['mean_x']:+.3f} times what was risked.")

    # ------------------------------------------- the day-boundary artefact
    cut = cr[cr.day_boundary_cut]
    kept = cr[~cr.day_boundary_cut]
    print(f"\n5. THE DAY-BOUNDARY ARTEFACT ON CRYPTO, measured")
    print(f"   tjr_bot.run_day closes anything still open when a UTC day's "
          f"bars run out.\n   The live path does not: manage_step holds "
          f"through the boundary. So these\n   exits are truncations, and they "
          f"truncate winners while losers still reach\n   their stops.")
    print(f"   trades that ended that way   {len(cut):,} of {len(cr):,}  "
          f"({100*len(cut)/max(len(cr),1):.1f}%)")
    print(f"   what they made               ${cut.pnl_dollars.sum():+,.0f}   "
          f"({100*(cut.pnl_dollars>0).sum()/max(len(cut),1):.1f}% of them won, "
          f"average {cut.result_x_risked.mean():+.3f} times what was risked)")
    a = figures(cr, 1)
    b = figures(kept, 1)
    print(f"   crypto as measured           {a['trades']:>6,} trades  "
          f"{a['won_pct']:>5.1f}% won  {a['mean_x']:>+7.3f}x risked  "
          f"${a['net']:>+12,}")
    print(f"   crypto with them removed     {b['trades']:>6,} trades  "
          f"{b['won_pct']:>5.1f}% won  {b['mean_x']:>+7.3f}x risked  "
          f"${b['net']:>+12,}")
    print(f"   This is a SENSITIVITY CHECK, not the headline. Removing them "
          f"drops real\n   trades the bot really took.")
    print(f"   AND IT DOES NOT POINT THE WAY THE ARTEFACT WAS ASSUMED TO. "
          f"Those trades were\n   AHEAD at the boundary — {100*(cut.pnl_dollars>0).sum()/max(len(cut),1):.1f}% "
          f"of them were in profit when the day's bars ran\n   out — so deleting "
          f"them deletes a winning subset and the result gets WORSE,\n   not "
          f"better. What the artefact actually does is CAP those winners at "
          f"whatever\n   they had at 00:00 UTC when the live path would have "
          f"run them on to a target\n   or a stop. The true cost therefore "
          f"sits between the two lines above and\n   cannot be settled by "
          f"deleting anything. Settling it needs a replay that\n   walks "
          f"through the boundary, which this round was not allowed to build.")

    # -------------------------------------------- 6. is the mean trustworthy
    print(f"\n6. THE AVERAGE RESULT, CHECKED FOR OUTLIERS")
    print(f"   A few crypto trades sit on a stop a fraction of a cent wide. "
          f"The set size\n   then buys an enormous position against a few "
          f"dollars of intended loss, and\n   the result as a MULTIPLE of that "
          f"few dollars goes to -225. The dollars are\n   unaffected — it is "
          f"the ratio that blows up — but the mean multiple is not\n   safe on "
          f"its own, so here it is beside its median and its 1%-trimmed mean.")
    rows = []
    for m in ("sp500", "crypto", "gold"):
        x = d.loc[d.market == m, "result_x_risked"]
        if not len(x):
            continue
        lo, hi = x.quantile(.01), x.quantile(.99)
        rows.append({"market": m, "trades": len(x),
                     "mean_x": round(x.mean(), 3),
                     "median_x": round(x.median(), 3),
                     "trimmed_mean_x": round(x[(x >= lo) & (x <= hi)].mean(), 3),
                     "net": int(round(d.loc[d.market == m,
                                            "pnl_dollars"].sum()))})
    table("   ", rows, ["market", "trades", "mean_x", "median_x",
                        "trimmed_mean_x", "net"])
    sp = d[d.market == "sp500"]
    best = sp[sp.year.isin([2023, 2024])].pnl_dollars.sum()
    print(f"   And the one that matters most on the S&P: of its "
          f"${sp.pnl_dollars.sum():+,.0f} over eleven\n   years, "
          f"${best:+,.0f} — {100*best/sp.pnl_dollars.sum():.0f}% of it — is "
          f"2023 and 2024. Its 1%-trimmed\n   average trade across all eleven "
          f"years is "
          f"{sp.result_x_risked[(sp.result_x_risked>=sp.result_x_risked.quantile(.01))&(sp.result_x_risked<=sp.result_x_risked.quantile(.99))].mean():+.3f} "
          f"times what was risked.")

    # ------------------------------------------------------------- written
    pd.DataFrame(rows).to_csv(f"{REPO}/step455_pooled_by_year.csv", index=False)
    d.to_csv(f"{REPO}/step455_all_trades.csv", index=False)
    print(f"\nwritten: step455_pooled_by_year.csv, step455_all_trades.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
