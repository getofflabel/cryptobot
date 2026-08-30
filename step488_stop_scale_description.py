"""
step488_stop_scale_description.py - ROUND 488

IF THE GROSS IS A LINEAR FUNCTION OF VOLATILITY, WHAT IS THE STOP?
(QUEUE ITEM 12)

Research only. No orders. No live file touched, imported or modified. No
account. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 12, VERBATIM
  R485 established that this method's gross tracks realized 1-minute
  volatility at r = +0.92 on the index over 11 years and r = +0.93 on
  crypto over 6, and that the binding problem is the SHAPE of the stop
  distribution: 12% of crypto entries and 14.5% of index entries carry a
  stop tighter than the round trip they must pay, which is what drives
  per-trade net R negative while the ratio-of-means looks positive.
  Deliverable, purely descriptive:
  (a) The joint distribution of stop size and outcome. Do the tightest-stop
      entries differ in gross R from the widest, or are they the same trade
      at a different scale? If they are the same trade, the cost problem is
      a pure SIZING fact and can be stated as one.
  (b) Is the tight-stop share itself a function of volatility? If low
      volatility manufactures unaffordable stops, then "the method degrades
      in quiet markets" and "cost eats it" are one sentence, not two.
  (c) The same two readings on the index, where volatility did not compress.
  THE FENCE, non-negotiable: this item may NOT propose, test or imply a
  minimum-stop filter, a volatility gate, or any threshold. Both families'
  sealed slices are spent; nothing here can become a candidate and no
  parameter may be swept. If the round finds itself wanting to cut the
  population, it has failed and must report the description only.

THE FENCE, RESTATED AS CODE DISCIPLINE
  Deciles below are a DESCRIPTION of a distribution, not a selection rule.
  No cell is qualified, no subset is proposed, nothing is carried forward,
  and no number produced here may be used to cut a population in any future
  round. The only threshold that appears anywhere in this file is the
  MEASURED COST (R482/R486 all-in per coin, R370/R474 on the index), which
  is a fact about the venue and not a parameter of the method. Everything
  else is reported as a continuous relationship precisely so that no cut
  point is manufactured.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  Both populations are ALREADY FULLY PUBLISHED and have no sealed slice
  left anywhere: crypto is step481's 68,992 chargeable entries (R476/R481/
  R485), index is R485's rebuild of R474's population, read off
  step485_index_entries.csv without re-running R474's code. This round
  re-reads them and decomposes published means by a covariate that was
  always in the file. No cell is qualified, no partition is proposed, no
  slice is opened, nothing is tuned.

BASELINE STATED IN THE SAME BREATH (R88/R100)
  The whole question in (a) is whether a difference EXISTS across the stop
  distribution, so the null - "the same trade at a different scale" - is
  the interesting outcome and gets the strong test, not the weak one. Two
  are run: a Spearman across the ten decile means, and a paired-by-day
  difference between the tightest and widest decile, which controls for
  the fact that a quiet day supplies mostly tight stops and a wild day
  mostly wide ones. An unpaired reading is printed beside it.

COSTS
  Charged for honest P&L and used for nothing else (owner rule 2026-07-25).
  Nothing here gates, declines or ranks anything.

HONEST LIMITS, FIXED BEFORE RUNNING
  - Deciles are cut WITHIN COIN (and within index symbol), because the three
    coins have different structural stop scales and a pooled decile would
    otherwise be sorting coins rather than stops. The pooled version is
    printed beside it so the choice is visible.
  - Realized volatility is the mean absolute 1-minute return, in % of price,
    the same scale R485 used. For the index it is computed on regular-hours
    bars (13:30-20:00 UTC) for the daily series, and on the whole tape for
    the year table so R485's published figures reproduce. Both are printed.
  - A per-day tight share is a ratio of small counts on thin days; the daily
    correlations are therefore reported alongside monthly ones, which are
    the reading to trust.
  - "Tight" means "stop smaller than the measured all-in round trip on the
    venue" and nothing else. It is not a proposed cut.
  - Index entries carry `reason`; a non-stopped index entry exits at the
    close and CAN exit negative, unlike a crypto cap-runner. Tables label
    this as surv% rather than win%.

USAGE
  python3 step488_stop_scale_description.py
"""

import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats as sps

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

CRYPTO_ENTRIES = f"{REPO}/step481_entries_funding.csv"
INDEX_ENTRIES = f"{REPO}/step485_index_entries.csv"

# R482's measured all-in round trip on Coinbase Derivatives (exchange fee +
# median spread), % of price. R485 used exactly these. Charged for honest
# P&L, used for nothing else.
COST_CRYPTO = {"BTCUSD": 0.0432, "ETHUSD": 0.1126, "SOLUSD": 0.0724}
COST_INDEX = 0.04            # R370/R474 headline round trip, % of notional

CRYPTO_PARQUET = {"BTCUSD": "data_alpaca_BTCUSD_1m.parquet",
                  "ETHUSD": "data_alpaca_ETHUSD_1m.parquet",
                  "SOLUSD": "data_alpaca_SOLUSD_1m.parquet"}
INDEX_PARQUET = {"SPY": "data_alpaca_SPY_1m.parquet",
                 "QQQ": "data_alpaca_QQQ_1m.parquet"}

LINE = "=" * 100


# ==================================================================== stats
def tstat_by_day(vals, days):
    """t of the mean, clustered by calendar day (the unit that repeats)."""
    s = pd.Series(np.asarray(vals, float))
    dm = s.groupby(np.asarray(days)).mean().to_numpy()
    dm = dm[np.isfinite(dm)]
    if len(dm) < 3:
        return np.nan, len(dm)
    return float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), len(dm)


def paired_day_diff(d, col, mask_a, mask_b):
    """Mean of (daily mean under A) - (daily mean under B) over days that
    supply both, with a t on the paired daily differences."""
    a = d.loc[mask_a].groupby("day")[col].mean()
    b = d.loc[mask_b].groupby("day")[col].mean()
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(j) < 3:
        return np.nan, np.nan, len(j)
    dif = (j["a"] - j["b"]).to_numpy()
    t = dif.mean() / (dif.std(ddof=1) / np.sqrt(len(dif)))
    return float(dif.mean()), float(t), len(j)


def unpaired_day_diff(d, col, mask_a, mask_b):
    """Welch t on the two sets of daily means (no pairing)."""
    a = d.loc[mask_a].groupby("day")[col].mean().to_numpy()
    b = d.loc[mask_b].groupby("day")[col].mean().to_numpy()
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    if len(a) < 3 or len(b) < 3:
        return np.nan, np.nan
    t, _ = sps.ttest_ind(a, b, equal_var=False)
    return float(a.mean() - b.mean()), float(t)


# ===================================================================== load
def load_crypto():
    d = pd.read_csv(CRYPTO_ENTRIES, usecols=[
        "sig_t", "stop_pct", "gross_pct", "reason", "sym", "level", "dirn",
        "bars_held"])
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["y"] = d["sig_t"].dt.year
    d["day"] = d["sig_t"].dt.floor("D")
    d["R"] = d["gross_pct"] / d["stop_pct"]
    d["win"] = d["reason"] == "time"          # ran the 24h cap
    d["cost"] = d["sym"].map(COST_CRYPTO)
    d["netR"] = (d["gross_pct"] - d["cost"]) / d["stop_pct"]
    d["tight"] = d["stop_pct"] < d["cost"]
    return d


def load_index():
    d = pd.read_csv(INDEX_ENTRIES, usecols=[
        "sig_t", "stop_pct", "gross_pct", "reason", "sym", "level", "dirn",
        "bars_held"])
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["y"] = d["sig_t"].dt.year
    d["day"] = d["sig_t"].dt.floor("D")
    d["R"] = d["gross_pct"] / d["stop_pct"]
    d["win"] = d["reason"] != "stop"          # survived to the close
    d["cost"] = COST_INDEX
    d["netR"] = (d["gross_pct"] - COST_INDEX) / d["stop_pct"]
    d["tight"] = d["stop_pct"] < COST_INDEX
    return d


def daily_vol(path, rth=False):
    """Mean |1-minute return| per calendar day, % of price."""
    b = pd.read_parquet(path)
    tcol = "t" if "t" in b.columns else "timestamp"
    t = pd.to_datetime(b[tcol])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    r = (b["close"].pct_change().abs() * 100.0)
    f = pd.DataFrame({"t": t, "r": r}).dropna()
    if rth:                                    # 13:30-20:00 UTC, US session
        h = f["t"].dt.hour + f["t"].dt.minute / 60.0
        f = f[(h >= 13.5) & (h < 20.0)]
    return f.groupby(f["t"].dt.floor("D"))["r"].mean()


def build_vol(mapping, rth=False):
    out = {}
    for sym, p in mapping.items():
        try:
            out[sym] = daily_vol(f"{REPO}/{p}", rth=rth)
        except Exception as e:                  # pragma: no cover
            print(f"  !! vol unavailable for {sym}: {e}")
    return out


def attach_vol(d, vols):
    """Each entry gets its own coin's realized vol for its own day."""
    idx = pd.MultiIndex.from_arrays([d["sym"], d["day"]])
    ser = pd.concat({s: v for s, v in vols.items()}, names=["sym", "day"])
    d["vol"] = ser.reindex(idx).to_numpy()
    return d


# =============================================================== decile view
def decile_table(d, label, within):
    """(a) The joint distribution of stop size and outcome."""
    d = d.copy()
    if within:
        d["q"] = d.groupby("sym")["stop_pct"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 10, labels=False) + 1)
    else:
        d["q"] = pd.qcut(d["stop_pct"].rank(method="first"), 10,
                         labels=False) + 1

    print(f"\n{label}  (deciles cut {'WITHIN COIN/SYMBOL' if within else 'POOLED'})")
    hdr = (f"{'dec':<5}{'n':>7}{'stop lo%':>10}{'stop med%':>11}"
           f"{'stop hi%':>10}{'p_win%':>9}{'W_R':>8}{'gross%':>9}"
           f"{'grossR':>9}{'t_day':>8}{'cost/stop':>11}{'netR':>9}"
           f"{'t_day':>8}{'bars':>8}{'vol%':>8}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for q, g in d.groupby("q"):
        w = g[g["win"]]
        t, _ = tstat_by_day(g["R"], g["day"])
        tn, _ = tstat_by_day(g["netR"], g["day"])
        r = dict(q=int(q), n=len(g),
                 lo=g["stop_pct"].min(), med=g["stop_pct"].median(),
                 hi=g["stop_pct"].max(), p=g["win"].mean(),
                 W_R=(w["R"].mean() if len(w) else np.nan),
                 gross=g["gross_pct"].mean(), R=g["R"].mean(), t=t,
                 cs=(g["cost"] / g["stop_pct"]).mean(),
                 netR=g["netR"].mean(), tn=tn,
                 bars=g["bars_held"].median(),
                 vol=g["vol"].mean() if "vol" in g else np.nan)
        rows.append(r)
        print(f"{r['q']:<5}{r['n']:>7,}{r['lo']:>10.3f}{r['med']:>11.3f}"
              f"{r['hi']:>10.3f}{r['p']*100:>9.2f}{r['W_R']:>8.2f}"
              f"{r['gross']:>9.4f}{r['R']:>9.3f}{r['t']:>8.2f}"
              f"{r['cs']:>11.3f}{r['netR']:>9.3f}{r['tn']:>8.2f}"
              f"{r['bars']:>8.0f}{r['vol']:>8.4f}")
    T = pd.DataFrame(rows).set_index("q")

    # ---- is gross R flat across the stop distribution?
    rho, p = sps.spearmanr(T.index.to_numpy(float), T["R"].to_numpy())
    rho_p, p_p = sps.spearmanr(T.index.to_numpy(float), T["p"].to_numpy())
    rho_w, p_w = sps.spearmanr(T.index.to_numpy(float), T["W_R"].to_numpy())
    rho_g, p_g = sps.spearmanr(T.index.to_numpy(float), T["gross"].to_numpy())
    print(f"\n  Spearman decile vs mean gross R   rho {rho:>+6.3f}  p {p:>6.3f}"
          f"   (10 points, weak by construction)")
    print(f"  Spearman decile vs win rate p     rho {rho_p:>+6.3f}  p {p_p:>6.3f}")
    print(f"  Spearman decile vs winner size W_R rho {rho_w:>+6.3f}  p {p_w:>6.3f}")
    print(f"  Spearman decile vs gross% of price rho {rho_g:>+6.3f}  p {p_g:>6.3f}"
          f"   (this one MUST rise if R is flat - gross% = R x stop)")

    lo = d["q"] == 1
    hi = d["q"] == 10
    for col, lab in (("R", "gross R"), ("gross_pct", "gross% of price"),
                     ("netR", "net R")):
        pm, pt, nd = paired_day_diff(d, col, hi, lo)
        um, ut = unpaired_day_diff(d, col, hi, lo)
        print(f"  D10 - D1 on {lab:<16} paired by day {pm:>+8.3f} "
              f"t {pt:>+6.2f} ({nd:,} days)   unpaired {um:>+8.3f} t {ut:>+6.2f}")

    # ---- the same trade at a different scale? gross% / stop is R by
    #      construction, so the honest check is whether R's DISPERSION is
    #      flat too, not just its mean.
    print(f"\n  dispersion of gross R by decile (if it is the same trade at a"
          f" different scale, this is flat too)")
    print(f"{'dec':<5}{'meanR':>9}{'sdR':>9}{'p10':>9}{'p50':>9}{'p90':>9}"
          f"{'skew':>9}")
    for q, g in d.groupby("q"):
        r = g["R"]
        print(f"{int(q):<5}{r.mean():>9.3f}{r.std():>9.3f}"
              f"{r.quantile(.1):>9.3f}{r.quantile(.5):>9.3f}"
              f"{r.quantile(.9):>9.3f}{r.skew():>9.2f}")
    return T


def per_coin_deciles(d, label):
    print(f"\n{label} - PER SYMBOL, decile 1 vs decile 10 on gross R")
    print(f"{'sym':<9}{'n':>8}{'D1 stopmed%':>13}{'D1 grossR':>11}"
          f"{'D10 stopmed%':>14}{'D10 grossR':>12}{'D10-D1':>9}"
          f"{'t paired':>10}{'days':>7}")
    for sym, g in d.groupby("sym"):
        g = g.copy()
        g["q"] = pd.qcut(g["stop_pct"].rank(method="first"), 10,
                         labels=False) + 1
        lo, hi = g["q"] == 1, g["q"] == 10
        pm, pt, nd = paired_day_diff(g, "R", hi, lo)
        print(f"{sym:<9}{len(g):>8,}{g.loc[lo,'stop_pct'].median():>13.3f}"
              f"{g.loc[lo,'R'].mean():>11.3f}"
              f"{g.loc[hi,'stop_pct'].median():>14.3f}"
              f"{g.loc[hi,'R'].mean():>12.3f}{pm:>9.3f}{pt:>10.2f}{nd:>7,}")


# ============================================================ vol vs tight
def vol_view(d, label, cost_note):
    """(b) Is the tight-stop share itself a function of volatility?"""
    print("\n" + LINE)
    print(f"(b)  IS THE TIGHT-STOP SHARE A FUNCTION OF VOLATILITY?  [{label}]")
    print(LINE)
    print(f"  'tight' = stop smaller than the measured all-in round trip "
          f"({cost_note}).")
    print("  It is the VENUE's number, not a proposed cut. Continuous "
          "relationships are")
    print("  printed beside it so that no cut point is manufactured.\n")

    ok = d["vol"].notna()
    print(f"  volatility attached to {ok.mean()*100:.1f}% of entries "
          f"({ok.sum():,} of {len(d):,})")
    d = d[ok].copy()

    # ------------------------------------------------------------- by year
    print(f"\n{'year':<6}{'n':>7}{'vol%':>9}{'stopmed%':>10}{'stop/vol':>10}"
          f"{'tight%':>9}{'grossR':>9}{'netR':>9}{'cost/stop':>11}")
    for y, g in d.groupby("y"):
        v = g["vol"].mean()
        print(f"{y:<6}{len(g):>7,}{v:>9.4f}{g['stop_pct'].median():>10.3f}"
              f"{g['stop_pct'].median()/v:>10.2f}{g['tight'].mean()*100:>9.2f}"
              f"{g['R'].mean():>9.3f}{g['netR'].mean():>9.3f}"
              f"{(g['cost']/g['stop_pct']).mean():>11.3f}")
    print("  stop/vol is the structural stop expressed in units of that "
          "year's 1-minute move.")
    print("  If it is FLAT, the stop is a fixed multiple of volatility and "
          "the tight share")
    print("  is mechanical: the market shrank past a fee that did not.")

    # ---------------------------------------------------- daily & monthly
    day = d.groupby("day").agg(vol=("vol", "mean"),
                               stop=("stop_pct", "median"),
                               tight=("tight", "mean"),
                               R=("R", "mean"), netR=("netR", "mean"),
                               n=("R", "size"))
    day = day[day["n"] >= 3]
    mon = d.copy()
    mon["m"] = mon["sig_t"].dt.to_period("M")
    mon = mon.groupby("m").agg(vol=("vol", "mean"),
                               stop=("stop_pct", "median"),
                               tight=("tight", "mean"),
                               R=("R", "mean"), netR=("netR", "mean"),
                               n=("R", "size"))

    print(f"\n  CORRELATIONS  (daily: {len(day):,} days with >=3 entries; "
          f"monthly: {len(mon):,} months)")
    print(f"{'pair':<38}{'daily r':>10}{'p':>9}{'daily rho':>12}"
          f"{'monthly r':>12}{'p':>9}{'monthly rho':>13}")
    pairs = (("realized vol  vs  median stop", "vol", "stop"),
             ("realized vol  vs  tight share", "vol", "tight"),
             ("median stop   vs  tight share", "stop", "tight"),
             ("realized vol  vs  mean gross R", "vol", "R"),
             ("realized vol  vs  mean net R", "vol", "netR"))
    for lab, a, b in pairs:
        r1, p1 = sps.pearsonr(day[a], day[b])
        s1, _ = sps.spearmanr(day[a], day[b])
        r2, p2 = sps.pearsonr(mon[a], mon[b])
        s2, _ = sps.spearmanr(mon[a], mon[b])
        print(f"{lab:<38}{r1:>+10.3f}{p1:>9.3f}{s1:>+12.3f}"
              f"{r2:>+12.3f}{p2:>9.3f}{s2:>+13.3f}")

    # ----------------------------------------- vol deciles (description)
    print(f"\n  THE SAME THING AS A PICTURE: months ranked by realized "
          f"volatility, in fifths")
    mon = mon.copy()
    mon["v5"] = pd.qcut(mon["vol"].rank(method="first"), 5, labels=False) + 1
    print(f"{'vol 5th':<9}{'months':>8}{'vol%':>9}{'stopmed%':>10}"
          f"{'stop/vol':>10}{'tight%':>9}{'grossR':>9}{'netR':>9}")
    for v, g in mon.groupby("v5"):
        print(f"{int(v):<9}{len(g):>8}{g['vol'].mean():>9.4f}"
              f"{g['stop'].mean():>10.3f}"
              f"{g['stop'].mean()/g['vol'].mean():>10.2f}"
              f"{g['tight'].mean()*100:>9.2f}{g['R'].mean():>9.3f}"
              f"{g['netR'].mean():>9.3f}")
    print("  Months are the unit here because a per-day tight share is a "
          "ratio of small counts.")
    print("  Nothing is selected by this table and nothing may be.")



# ================================================================ addendum
def addendum(c, ix):
    """Two checks (a) needs before it can be stated honestly, plus the one
    unifying coordinate the round produced. Descriptions only."""
    print("\n" + LINE)
    print("ADDENDUM - IS THE TIGHT DECILE'S GROSS R REAL, AND HOW HARD IS")
    print("THE STOP TIED TO VOLATILITY?")
    print(LINE)
    print("(a)'s raw means are exposed to the SAME 1/stop tail R487 found on")
    print("the net side. Both checks below exist so the round does not repeat")
    print("that error on the gross side. Nothing here is a cut or a candidate.")

    for nm, d in (("CRYPTO", c), ("INDEX", ix)):
        d = d.copy()
        d["q"] = d.groupby("sym")["stop_pct"].transform(
            lambda s: pd.qcut(s.rank(method="first"), 10, labels=False) + 1)
        T = d.groupby("q").agg(R=("R", "mean"), med=("R", "median"))
        print(f"\n{nm}")
        print("  (1) IS THE TIGHT DECILE'S HIGH GROSS R REAL, OR THE 1/stop TAIL?")
        rho, p = sps.spearmanr(T.index[1:].to_numpy(float),
                               T["R"].to_numpy()[1:])
        print(f"      Spearman decile vs mean gross R, deciles 2-10 only: "
              f"rho {rho:+.3f}  p {p:.3f}   "
              f"(band {T['R'][2:].min():.3f} to {T['R'][2:].max():.3f})")
        print(f"      D1 mean gross R {T['R'][1]:+.3f} vs its MEDIAN "
              f"{T['med'][1]:+.3f}; D10 mean {T['R'][10]:+.3f} median "
              f"{T['med'][10]:+.3f}")
        d1 = d[d["q"] == 1]
        for k in (0.001, 0.01, 0.05):
            cut = d1["R"].quantile(1 - k)
            trimmed = d1.loc[d1["R"] <= cut, "R"].mean()
            carried = d1.loc[d1["R"] > cut, "R"].sum() / d1["R"].sum() * 100
            print(f"      D1 mean gross R with the top {k*100:>5.1f}% of R "
                  f"removed: {trimmed:+.3f}   (share of D1's total R carried "
                  f"by them: {carried:5.1f}%)")
        print("      the same table with each decile's R winsorised at its "
              "own p99:")
        row = []
        for q, g in d.groupby("q"):
            r = g["R"].clip(upper=g["R"].quantile(0.99))
            row.append(f"D{int(q)} {r.mean():+.3f}")
        print("      " + "  ".join(row))

        print("  (2) HOW HARD IS THE STOP TIED TO VOLATILITY?  "
              "(log-log elasticity)")
        day = d.groupby("day").agg(vol=("vol", "mean"),
                                   stop=("stop_pct", "median"),
                                   n=("R", "size"))
        day = day[(day["n"] >= 3) & (day["vol"] > 0) & (day["stop"] > 0)]
        x = np.log(day["vol"].to_numpy())
        y = np.log(day["stop"].to_numpy())
        b, a0 = np.polyfit(x, y, 1)
        yh = a0 + b * x
        se = np.sqrt(((y - yh) ** 2).sum() / (len(x) - 2) /
                     ((x - x.mean()) ** 2).sum())
        r2 = 1 - ((y - yh) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        print(f"      log(median stop) = {a0:+.3f} + {b:.3f} * log(vol)   "
              f"elasticity {b:.3f} (se {se:.3f}, t vs 1.0 = {(b-1)/se:+.2f}), "
              f"R2 {r2:.3f}, {len(x):,} days")
        pt = d["stop_pct"] / d["vol"]
        print(f"      per-entry stop/vol: p10 {pt.quantile(.1):.2f}  p25 "
              f"{pt.quantile(.25):.2f}  p50 {pt.quantile(.5):.2f}  p75 "
              f"{pt.quantile(.75):.2f}  p90 {pt.quantile(.9):.2f}")

        print("  (3) THE PRICE OF THE CONSTRAINT (a description, not a gate):")
        for sym, g in d.groupby("sym"):
            cost = g["cost"].iloc[0]
            gd = g.groupby("day").agg(vol=("vol", "mean"),
                                      stop=("stop_pct", "median"),
                                      n=("R", "size"))
            gd = gd[(gd["n"] >= 3) & (gd["vol"] > 0) & (gd["stop"] > 0)]
            xx = np.log(gd["vol"].to_numpy())
            yy = np.log(gd["stop"].to_numpy())
            bb, aa = np.polyfit(xx, yy, 1)
            volstar = np.exp((np.log(cost) - aa) / bb)
            act = g["vol"].median()
            print(f"      {sym:<8} round trip {cost:.4f}% -> the median stop "
                  f"equals it at a 1-minute move of {volstar:.4f}%; the "
                  f"median day sits at {act:.4f}% ({act/volstar:.2f}x it)")
    print("\n  Descriptions only. No cut, no gate, no candidate. The fence "
          "holds.")


# ===================================================================== main
def main():
    print(LINE)
    print("ROUND 488 - STOP SIZE, OUTCOME AND VOLATILITY  (queue item 12)")
    print("RESEARCH ONLY. NO ORDERS. NO LOOK CONSUMED. NOTHING DEPLOYED.")
    print("DESCRIPTION ONLY - no filter, no gate, no threshold is proposed,")
    print("implied, or permitted to leave this file.")
    print(LINE)

    c = load_crypto()
    ix = load_index()
    print(f"crypto population: {len(c):,} entries, "
          f"{c['sig_t'].min():%Y-%m-%d} -> {c['sig_t'].max():%Y-%m-%d}, "
          f"{c['day'].nunique():,} days, coins {sorted(c['sym'].unique())}")
    print(f"index  population: {len(ix):,} entries, "
          f"{ix['sig_t'].min():%Y-%m-%d} -> {ix['sig_t'].max():%Y-%m-%d}, "
          f"{ix['day'].nunique():,} days, {sorted(ix['sym'].unique())}")
    print(f"published anchors reproduced: crypto per-trade net R "
          f"{c['netR'].mean():+.3f} (R485 -0.346), index per-trade net R "
          f"{ix['netR'].mean():+.3f} (R485 -0.024)")
    print(f"                              crypto tight share "
          f"{c['tight'].mean()*100:.2f}% (R485 12.14), index "
          f"{ix['tight'].mean()*100:.2f}% (R485 14.53)")

    print("\nattaching realized 1-minute volatility, per symbol per day ...")
    cv = build_vol(CRYPTO_PARQUET)
    iv = build_vol(INDEX_PARQUET, rth=True)
    iv_all = build_vol(INDEX_PARQUET, rth=False)
    c = attach_vol(c, cv)
    ix = attach_vol(ix, iv)
    print("  R485 year-scale check (mean |1m return|, % of price):")
    for s, v in list(cv.items()) + list(iv_all.items()):
        yv = v.groupby(v.index.year).mean()
        print(f"    {s:<8}" + "  ".join(
            f"{y}:{yv.loc[y]:.4f}" for y in yv.index if y >= 2016))
    print("  index daily series uses REGULAR HOURS only (13:30-20:00 UTC); "
          "the line above is the whole tape, matching R485.")

    # =================================================== (a) crypto + index
    print("\n" + LINE)
    print("(a)  THE JOINT DISTRIBUTION OF STOP SIZE AND OUTCOME")
    print(LINE)
    print("A decile here is a DESCRIPTION of the stop distribution. If mean")
    print("gross R is flat across the ten and gross% of price rises with them,")
    print("then the tight entries are the SAME TRADE AT A SMALLER SCALE and")
    print("the cost problem is a pure sizing fact. If gross R falls with the")
    print("stop, they are a different, worse trade. Nothing is cut either way.")

    Tc = decile_table(c, "CRYPTO  (68,992 entries, 3 coins, 2021-2026)", True)
    decile_table(c, "CRYPTO  same table, pooled deciles (sanity)", False)
    per_coin_deciles(c, "CRYPTO")

    Ti = decile_table(ix, "INDEX  (SPY + QQQ, 2016-2026)", True)
    per_coin_deciles(ix, "INDEX")

    print("\n" + "-" * 100)
    print("WHERE THE COST LANDS ON THAT DISTRIBUTION")
    print("-" * 100)
    for nm, d, T in (("crypto", c, Tc), ("index", ix, Ti)):
        share = d["tight"].mean() * 100
        tg = d.loc[d["tight"], "R"].mean()
        wg = d.loc[~d["tight"], "R"].mean()
        pm, pt, nd = paired_day_diff(d, "R", ~d["tight"], d["tight"])
        print(f"  {nm:<7} stop under the round trip: {share:>5.2f}% of "
              f"entries.  gross R tight {tg:>+6.3f} vs rest {wg:>+6.3f}, "
              f"paired by day {pm:>+6.3f} (t {pt:>+5.2f}, {nd:,} days)")
        print(f"  {'':<7} their cost/stop mean "
              f"{(d.loc[d['tight'],'cost']/d.loc[d['tight'],'stop_pct']).mean():>6.2f}"
              f" against {(d.loc[~d['tight'],'cost']/d.loc[~d['tight'],'stop_pct']).mean():>5.2f}"
              f" for the rest; they are "
              f"{d.loc[d['tight'],'netR'].mean():+.3f} net R against "
              f"{d.loc[~d['tight'],'netR'].mean():+.3f}")
    print("  Reported, not acted on. No minimum-stop rule follows from this")
    print("  and none is permitted (queue item 12's fence, R485's bar).")

    # ======================================================= (b) and (c)
    vol_view(c, "CRYPTO", "R482 all-in, per coin: BTC 0.0432% / ETH 0.1126% "
             "/ SOL 0.0724%")
    vol_view(ix, "INDEX", "R370/R474 headline 0.04%")

    addendum(c, ix)

    print("\n" + LINE)
    print("END OF ROUND 488. NO CELL QUALIFIED, NONE COULD - THIS ROUND")
    print("DESCRIBES TWO PUBLISHED POPULATIONS. NO LOOK CONSUMED. NO ORDER.")
    print("NO FILTER, GATE OR THRESHOLD IS PROPOSED OR CARRIED FORWARD.")
    print(LINE)


if __name__ == "__main__":
    main()
