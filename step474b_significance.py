"""
step474b_significance.py - ROUND 474, PART 2

No new configuration is tested here. This file asks whether part 1's claim is
bigger than noise, and whether it survives being translated into the currency
the desk actually sizes in.

THREE THINGS PART 1 DOES NOT SETTLE

1. OVERLAPPING TRADES INFLATE THE t. Every candidate is scored
   independently, so one session can carry dozens of entries off eight
   different levels, all riding the same few hours of tape. A plain t-stat
   over 10,180 such rows treats them as 10,180 independent draws. They are
   not. Here the population is collapsed to ONE mean per trading day and the
   t is taken across DAYS, which is the number that should be quoted.

2. PERCENT OF PRICE IS NOT WHAT THE DESK EARNS. Size = risk / stop distance,
   so the money follows the RISK MULTIPLE, not the price move. A 0.04%
   round trip against a 0.084% stop is half the stop distance - R370's
   arithmetic, reappearing. Gross R and net R are both reported.

3. ONE REGIME OR TEN YEARS. The choosing slice is 2016-2022. The gross mean
   is broken out by year so a single regime cannot hide inside the average.

Then, and only if part 1's protocol was satisfied, ONE test look is taken on
the SINGLE best cell by choosing-slice net - the cell chosen by the rule that
was fixed before the run, not by looking at anything else.
"""

import contextlib
import io

import numpy as np
import pandas as pd

import step474_tjr_index_1m as R

NY = "America/New_York"


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def ny_day(res):
    t = pd.to_datetime(res["sig_t"]).dt.tz_localize("UTC").dt.tz_convert(NY)
    return t.dt.normalize().dt.tz_localize(None)


def clustered(res, col="gross_pct"):
    """One mean per trading day, then t across days. Overlapping intraday
    entries inside a session are one observation, not thirty."""
    d = res.assign(day=ny_day(res)).groupby("day")[col].mean()
    return tstat(d)


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        df, t_tr, t_va, store = R.main()

    print("=" * 104)
    print("ROUND 474 PART 2 - IS THE INDEX TRIGGER DIFFERENCE BIGGER THAN NOISE?")
    print("=" * 104)

    # ------------------------------------------------ the two arms, honest
    arms = {"A": [], "B": []}
    per_asset = {"A": {}, "B": {}}
    for (nm, arm), parts in store.items():
        for sym, res in parts:
            tr = res[res.sig_t < t_tr]
            arms[arm].append(tr)
            per_asset[arm].setdefault(sym, []).append(tr)

    uniq = {a: pd.concat(v).drop_duplicates(subset=["sig_t", "stop_pct"])
            for a, v in arms.items()}

    print("\nchoosing slice only. One row per distinct entry (the four target")
    print("settings score the SAME entries, so they are collapsed).")
    print(f"\n{'construction':<44}{'trades':>8}{'days':>7}{'gross%':>9}"
          f"{'t naive':>9}{'t by day':>10}{'grossR':>9}{'netR':>8}{'stop%':>8}")
    for arm, lab in (("A", "5-minute trigger (round 370's)"),
                     ("B", "1-MINUTE trigger (his)")):
        u = uniq[arm]
        tn, n = tstat(u["gross_pct"])
        tc, nd = clustered(u)
        gR = (u["gross_pct"] / u["stop_pct"]).replace([np.inf, -np.inf], np.nan).mean()
        nR = u["net_R"].replace([np.inf, -np.inf], np.nan).mean()
        print(f"{lab:<44}{n:>8,}{nd:>7,}{u['gross_pct'].mean():>8.4f}%"
              f"{tn:>9.2f}{tc:>10.2f}{gR:>9.3f}{nR:>8.3f}"
              f"{u['stop_pct'].median():>7.3f}%")

    ctl = []
    for sym in R.ASSETS:
        d5, _ = R.prep(sym)
        for dirn, rt, res in R.control_trades(d5):
            if rt is None:
                ctl.append(res[res.sig_t < t_tr])
    c = pd.concat(ctl)
    tn, n = tstat(c["gross_pct"]); tc, nd = clustered(c)
    gRc = (c["gross_pct"] / c["stop_pct"]).replace([np.inf, -np.inf], np.nan).mean()
    print(f"{'CONTROL random entry, same machinery':<44}{n:>8,}{nd:>7,}"
          f"{c['gross_pct'].mean():>8.4f}%{tn:>9.2f}{tc:>10.2f}{gRc:>9.3f}"
          f"{c['net_R'].replace([np.inf,-np.inf],np.nan).mean():>8.3f}"
          f"{c['stop_pct'].median():>7.3f}%")

    a, b = uniq["A"], uniq["B"]
    print("\nTHE DIFFERENCE, clustered by trading day (the number to quote):")
    for lab, other in (("1-minute trigger minus 5-minute trigger", a),
                       ("1-minute trigger minus RANDOM ENTRY     ", c)):
        db = b.assign(day=ny_day(b)).groupby("day")["gross_pct"].mean()
        do = other.assign(day=ny_day(other)).groupby("day")["gross_pct"].mean()
        j = pd.concat([db.rename("b"), do.rename("o")], axis=1).dropna()
        d_ = j["b"] - j["o"]          # PAIRED on the same trading days
        t_, nd_ = tstat(d_)
        print(f"  {lab}: {d_.mean():+.4f}% of price per day, "
              f"t = {t_:.2f} over {nd_:,} shared days")

    # ------------------------------------------------------- by the year
    print("\n" + "=" * 104)
    print("ONE REGIME OR TEN YEARS? gross mean of the 1-minute arm, by year")
    print("(choosing slice ends {:%Y-%m-%d}; middle slice ends {:%Y-%m-%d})".format(
        t_tr, t_va))
    print("=" * 104)
    allb = pd.concat([res for (nm, arm), parts in store.items() if arm == "B"
                      for _, res in parts]).drop_duplicates(
        subset=["sig_t", "stop_pct"])
    alla = pd.concat([res for (nm, arm), parts in store.items() if arm == "A"
                      for _, res in parts]).drop_duplicates(
        subset=["sig_t", "stop_pct"])
    yb = allb.assign(y=pd.to_datetime(allb["sig_t"]).dt.year)
    ya = alla.assign(y=pd.to_datetime(alla["sig_t"]).dt.year)
    print(f"{'year':<7}{'slice':<10}{'1m trades':>11}{'1m gross':>11}"
          f"{'1m grossR':>11}{'1m netR':>10}{'5m gross':>11}")
    for y, g in yb.groupby("y"):
        which = ("choosing" if g["sig_t"].max() < t_tr
                 else "middle" if g["sig_t"].max() < t_va else "SEALED")
        ga = ya[ya.y == y]
        gR = (g["gross_pct"] / g["stop_pct"]).replace([np.inf, -np.inf], np.nan).mean()
        nR = g["net_R"].replace([np.inf, -np.inf], np.nan).mean()
        if which == "SEALED":
            print(f"{y:<7}{which:<10}{'':>11}{'(not opened)':>11}")
            continue
        print(f"{y:<7}{which:<10}{len(g):>11,}{g['gross_pct'].mean():>10.4f}%"
              f"{gR:>11.3f}{nR:>10.3f}{ga['gross_pct'].mean():>10.4f}%")

    # ------------------------------------------------------- the test look
    print("\n" + "=" * 104)
    print("THE SEALED SLICE")
    print("=" * 104)
    q = df[(df.verdict == "qualifies") & (df.n_assets_pos >= 2)]
    print(f"{len(q)} of {len(df)} pooled cells qualified on the choosing AND "
          f"middle slice and on BOTH assets.")
    print(f"Expected by chance with no edge: about {len(df)/8:.0f}.")
    if not len(q):
        print("Nothing qualified. The sealed slice stays sealed. Looks consumed: NONE.")
        return
    top = q.sort_values("mean_tr", ascending=False).iloc[0]
    print(f"\nThe rule fixed before the run: ONE test look, on the single best "
          f"cell by choosing-slice NET.")
    print(f"That cell is: {top['name']}")
    print(f"  choosing net {top['mean_tr']:+.4f}%   middle net {top['mean_va']:+.4f}%"
          f"   stop {top['stop_tr']:.3f}%   {top['lev']:.1f}x at 1% risked")

    parts = store[(top["name"], "B")]
    allr = pd.concat([r for _, r in parts])
    _, _, te = R.slice_by_time(allr, t_tr, t_va)
    if len(te) < R.MIN_VA:
        print("  the sealed slice holds too few trades to read. Look NOT consumed.")
        return
    tn, n = tstat(te["gross_pct"]); tc, nd = clustered(te)
    gR = (te["gross_pct"] / te["stop_pct"]).replace([np.inf, -np.inf], np.nan).mean()
    print(f"\n  SEALED SLICE, opened once, never again for this family:")
    print(f"    trades {len(te):,} over {nd:,} trading days")
    print(f"    gross {te['gross_pct'].mean():+.4f}% of price per trade  "
          f"(t naive {tn:.2f}, t by day {tc:.2f})")
    print(f"    net   {te['net_pct'].mean():+.4f}% of price per trade  "
          f"after {R.COST_RT}% round trip")
    print(f"    gross R {gR:+.3f}   net R "
          f"{te['net_R'].replace([np.inf,-np.inf],np.nan).mean():+.3f}")
    per = []
    for sym, r in parts:
        _, _, t3 = R.slice_by_time(r, t_tr, t_va)
        per.append((sym, len(t3), t3["gross_pct"].mean(), t3["net_pct"].mean()))
    for sym, k, g_, n_ in per:
        print(f"    {sym}: {k:,} trades, gross {g_:+.4f}%, net {n_:+.4f}%")
    survived = (te["net_pct"].mean() > 0 and all(x[3] > 0 for x in per))
    print(f"\n  VERDICT ON THE SEALED SLICE: "
          f"{'SURVIVES - positive net on the sealed slice and on both assets' if survived else 'FAILS - net is not positive on the sealed slice and both assets'}")
    print("  LOOKS CONSUMED: ONE. The final 20% of the SPY/QQQ 1-minute "
          "sweep-to-BOS family is now spent.")


if __name__ == "__main__":
    main()
