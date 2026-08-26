"""
step485_decay_anatomy.py - ROUND 485

THE DECAY IS NOW THE WHOLE ARGUMENT. NOBODY HAS MEASURED IT.  (QUEUE ITEM 9)

Research only. No orders. No live file touched, imported or modified. No
account. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 9, VERBATIM
  Three rounds have been spent driving the cost side of this family to a
  finish (R478 fee, R479/R480 spread, R481 funding), and the answer is that
  cost is no longer what kills it. On the full 5.5 years the method clears
  the whole Coinbase stack with +0.196 stop distances left over. On the 2026
  stub it does not, because the GROSS fell from +0.2908% (2021) to +0.0387%
  (R476's year table) - a 7.5x decay in the signal itself. Every "not
  deployable" verdict since R478 rests on that one number and no round has
  ever interrogated it.
  Deliverable, and it is a DESCRIPTION not a candidate:
    (a) Is the decay in the ENTRY COUNT, the WIN RATE, or the SIZE of the
        winners? R481's split is the handle - 90.3% stopped / 9.7% run the
        cap, and the whole +0.1309% comes from that 9.7% at +4.13% each. If
        the decay is the tail thinning, that is a different fact about the
        market than if the stops got worse.
    (b) Is it monotone or is 2026 a stub? 2026 is a partial year ending
        2026-07-26 and is being quoted as if it were a regime.
    (c) Does the same decay show on the INDEX over the same calendar years?
        R474's SPY/QQQ population is already built. If the decay is
        crypto-only it is a crowding story; if it is both, it is a
        volatility story.
  R482 ADDITION: (a) is the most decisive leg. The CDE overnight leverage
  ceiling is 4.07x BTC / 4.08x ETH / 2.73x SOL against a method that needs
  5.4x / 4.2x / 2.9x - the 9.7% tail that produces the whole gross is
  exactly the part the venue is least willing to finance. If (a) shows the
  decay IS that tail thinning, the venue constraint and the decay are
  pointed at the same 9.7% of trades and this family is finished on two
  independent grounds.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  Part (a) and (b) re-read an entry population the desk has ALREADY fully
  published (R476, whole window, no sealed slice left anywhere on this
  family) and decompose its published mean into arithmetic parts. No cell is
  qualified, no partition is proposed, no slice is opened, nothing is tuned.
  Part (c) rebuilds R474's index population with R474's own code, unchanged,
  and reads the whole 2016-2026 window as ONE series by calendar year. It
  qualifies nothing and proposes nothing; the SPY/QQQ sealed window was
  spent in R474 and this round does not re-open it as a test - it describes
  the time profile of a population whose aggregate is already in the log.
  NOTHING HERE IS A DEPLOYMENT CANDIDATE AND NOTHING COULD BE.

THE ARITHMETIC HANDLE, AND IT IS EXACT
  In this construction a stopped entry loses EXACTLY its stop (the stop is
  the fill, intra-bar). So with p = share running the 24h cap, W = mean
  gross of the cap-runners, L = mean stop of the stopped:
        mean gross%  =  p*W  -  (1-p)*L
        mean R       =  p*W_R -  (1-p)          [because a stop is -1.000R]
  The identity is VERIFIED in code before it is used. It turns "why did the
  gross fall" into a three-number question with no residual, and it splits
  the answer cleanly into the queue's own three candidates: how many trades
  (n), how often they win (p), how big the winners are (W).

WHAT IS MEASURED
  (a) The five quantities above per year, per coin, in % of price AND in
      risk multiples, with the median stop (the price scale) beside them and
      a shift-share decomposition that attributes the 2021->2026 fall to
      Dp, DW and DL with no residual.
  (b) Half-years and quarters; the SAME CALENDAR WINDOW (Jan 1 -> Jul 26)
      read in every year so 2026's stub is compared to stubs; an OLS trend
      on the daily series with a t clustered by UTC day; a Spearman rank
      test on the year series.
  (c) R474's index population rebuilt with R474's own functions, pooled over
      the same eight levels, 1-minute trigger, hold to close, SPY and QQQ,
      read by calendar year - and realized 1-minute volatility by year for
      all five instruments, because if the % decay tracks volatility it is
      not a decay in the edge.

BASELINE STATED IN THE SAME BREATH (R88/R100)
  A fall in "% of price" is only news if the price scale did NOT fall with
  it. Realized volatility per year is printed beside every gross, and the
  same anatomy is read in risk multiples where the scale divides out.
  R476's random-entry control by year is quoted (not recomputed) for the
  same reason.

COSTS
  Charged for honest P&L and used for nothing else (owner rule, 2026-07-25).
  Nothing here gates, declines or ranks anything. Crypto cost is R482's
  measured all-in on Coinbase Derivatives (fee + spread, per coin); index
  cost is R370/R474's 0.04% round trip.

HONEST LIMITS, FIXED BEFORE RUNNING
  - The crypto population is step481's 68,992 chargeable entries, which is
    the funding-covered subset of R476's 71,073. Year means will differ from
    R476's table in the third decimal for that reason; the difference is
    stated, not hidden.
  - 2026 ends 2026-07-26 in this data. Every 2026 number is 207 days.
  - The index population is on Alpaca's regular-hours tape with R474's rules
    (09:50 fill floor, flat by the close). It is pooled over eight levels
    un-deduped, exactly as the crypto population is; the dedupe sensitivity
    is printed.
  - Realized volatility is the mean absolute 1-minute return per year, in %
    of price. It is a scale, not a model.

USAGE
  python3 step485_decay_anatomy.py
"""

import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

ENTRIES = f"{REPO}/step481_entries_funding.csv"

# R482's measured all-in round trip on Coinbase Derivatives (exchange fee +
# median spread), % of price. Charged for honest P&L, used for nothing else.
COST_CRYPTO = {"BTCUSD": 0.0432, "ETHUSD": 0.1126, "SOLUSD": 0.0724}
COST_INDEX = 0.04            # R370/R474 headline round trip, % of notional

# R476's random-entry control, per year, quoted not recomputed.
R476_CONTROL = {2021: 0.0604, 2022: 0.0418, 2023: -0.0535,
                2024: 0.0046, 2025: -0.0290, 2026: -0.0350}
R476_N = {2021: 13890, 2022: 13956, 2023: 11314, 2024: 10863,
          2025: 13609, 2026: 7441}
R476_GROSS = {2021: 0.2908, 2022: 0.1800, 2023: 0.0371,
              2024: 0.1320, 2025: 0.1106, 2026: 0.0387}

LINE = "=" * 100


def tstat_by_day(vals, days):
    """t of the mean, clustered by calendar day (the unit that repeats)."""
    s = pd.Series(np.asarray(vals, float))
    dm = s.groupby(np.asarray(days)).mean().to_numpy()
    dm = dm[np.isfinite(dm)]
    if len(dm) < 3:
        return np.nan, len(dm)
    return float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), len(dm)


def anatomy(g, win_mask):
    """The exact three-number decomposition of a mean gross."""
    w = g[win_mask]
    l = g[~win_mask]
    p = len(w) / len(g)
    W = w["gross_pct"].mean() if len(w) else np.nan
    L = l["stop_pct"].mean() if len(l) else np.nan
    Lg = -l["gross_pct"].mean() if len(l) else np.nan
    return dict(n=len(g), p=p, W=W, L=L, Lg=Lg,
                W_R=(w["R"].mean() if len(w) else np.nan),
                mean=g["gross_pct"].mean(), meanR=g["R"].mean(),
                stop_med=g["stop_pct"].median())


# ===================================================================== load
def load_crypto():
    d = pd.read_csv(ENTRIES, usecols=[
        "sig_t", "stop_pct", "gross_pct", "reason", "sym", "level", "dirn",
        "bars_held", "entry_t", "exit_t"])
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["y"] = d["sig_t"].dt.year
    d["day"] = d["sig_t"].dt.floor("D")
    d["R"] = d["gross_pct"] / d["stop_pct"]
    d["win"] = d["reason"] == "time"          # ran the 24h cap
    d["cost"] = d["sym"].map(COST_CRYPTO)
    d["netR"] = (d["gross_pct"] - d["cost"]) / d["stop_pct"]
    return d


def realized_vol(sym, path):
    """Mean |1-minute return| per calendar year, % of price. The crypto
    parquets carry `t`, the index parquets carry tz-aware `timestamp`."""
    b = pd.read_parquet(path)
    tcol = "t" if "t" in b.columns else "timestamp"
    t = pd.to_datetime(b[tcol])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    r = (b["close"].pct_change().abs() * 100.0)
    return r.groupby(t.dt.year).mean()


# ================================================================== PART A
def part_a(d):
    print(LINE)
    print("(a)  WHERE IS THE DECAY?  THE EXACT THREE-NUMBER ANATOMY")
    print(LINE)

    st = d[~d["win"]]
    exact = np.allclose(st["gross_pct"], -st["stop_pct"])
    print(f"identity check - a stopped entry loses exactly its stop: {exact}")
    print(f"                 stopped {len(st):,} of {len(d):,} "
          f"({len(st)/len(d)*100:.1f}%), cap-runners {d['win'].sum():,} "
          f"({d['win'].mean()*100:.1f}%)")
    if not exact:
        print("  !! identity FAILS - the decomposition below is not exact")

    print("\n  mean gross% = p*W - (1-p)*L      mean R = p*W_R - (1-p)")
    print("  p = share running the 24h cap, W = mean gross of those,")
    print("  L = mean stop of the stopped (= their loss, exactly)\n")

    hdr = (f"{'year':<6}{'n':>7}{'days':>6}{'n/day':>7}{'p_win%':>8}"
           f"{'W%':>8}{'L%':>7}{'gross%':>9}{'check':>9}{'stopmed%':>10}"
           f"{'W_R':>8}{'meanR':>8}{'t_day':>8}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for y, g in d.groupby("y"):
        a = anatomy(g, g["win"].to_numpy().astype(bool))
        days = g["day"].nunique()
        chk = a["p"] * a["W"] - (1 - a["p"]) * a["L"]
        t, _ = tstat_by_day(g["gross_pct"], g["day"])
        a.update(y=y, days=days, t=t, chk=chk)
        rows.append(a)
        print(f"{y:<6}{a['n']:>7,}{days:>6}{a['n']/days:>7.1f}"
              f"{a['p']*100:>8.2f}{a['W']:>8.3f}{a['L']:>7.3f}"
              f"{a['mean']:>9.4f}{chk:>9.4f}{a['stop_med']:>10.3f}"
              f"{a['W_R']:>8.2f}{a['meanR']:>8.3f}{t:>8.2f}")
    A = pd.DataFrame(rows).set_index("y")

    print("\n  R476 published on 71,073 entries; this is the 68,992 "
          "funding-covered subset.")
    print(f"{'year':<6}{'R476 n':>9}{'here n':>9}{'covered':>9}"
          f"{'R476 gross%':>13}{'here gross%':>13}{'diff':>9}"
          f"{'R476 control%':>15}")
    for y in A.index:
        if y in R476_GROSS:
            n0 = R476_N[y]
            print(f"{y:<6}{n0:>9,}{A.loc[y,'n']:>9,.0f}"
                  f"{A.loc[y,'n']/n0*100:>8.1f}%"
                  f"{R476_GROSS[y]:>13.4f}{A.loc[y,'mean']:>13.4f}"
                  f"{A.loc[y,'mean']-R476_GROSS[y]:>9.4f}"
                  f"{R476_CONTROL[y]:>15.4f}")
    print("  Only 2021 loses a real share of its entries to funding coverage,")
    print("  and it is the ONE year where this table and R476 disagree.")

    # ------------------------------------------------ shift-share, no residual
    print("\n" + "-" * 100)
    print("SHIFT-SHARE: what produced the 2021 -> 2026 fall in gross%?")
    print("-" * 100)
    a0, a1 = A.loc[2021], A.loc[2026]
    pm, Wm, Lm = (a0.p + a1.p) / 2, (a0.W + a1.W) / 2, (a0.L + a1.L) / 2
    c_p = (a1.p - a0.p) * Wm + (a1.p - a0.p) * Lm       # p moves both terms
    c_W = pm * (a1.W - a0.W)
    c_L = -(1 - pm) * (a1.L - a0.L)
    tot = a1["mean"] - a0["mean"]
    resid = tot - (c_p + c_W + c_L)
    print(f"  total fall                          {tot:>+9.4f}% of price")
    print(f"  from the WIN RATE   p  {a0.p*100:>5.2f}% -> {a1.p*100:5.2f}%"
          f"   {c_p:>+9.4f}   ({c_p/tot*100:>5.1f}% of the fall)")
    print(f"  from the WINNERS    W  {a0.W:>5.3f}% -> {a1.W:5.3f}%"
          f"   {c_W:>+9.4f}   ({c_W/tot*100:>5.1f}% of the fall)")
    print(f"  from the LOSERS     L  {a0.L:>5.3f}% -> {a1.L:5.3f}%"
          f"   {c_L:>+9.4f}   ({c_L/tot*100:>5.1f}% of the fall)")
    print(f"  residual                            {resid:>+9.4f}"
          f"   (exact decomposition -> ~0)")
    print(f"\n  ENTRY COUNT is not in this identity - it is a mean per entry."
          f"  Entries/day went {a0.n/a0.days:.1f} -> {a1.n/a1.days:.1f} "
          f"({(a1.n/a1.days)/(a0.n/a0.days)-1:+.1%}).")

    # ------------------------------------------------ the risk-multiple view
    print("\n" + "-" * 100)
    print("THE SAME YEARS IN RISK MULTIPLES - where the price scale divides out")
    print("-" * 100)
    print(f"{'year':<6}{'gross%':>9}{'x2021':>8}{'meanR':>9}{'x2021':>8}"
          f"{'stopmed%':>10}{'x2021':>8}{'p_win%':>9}{'W_R':>8}")
    for y in A.index:
        r = A.loc[y]
        print(f"{y:<6}{r['mean']:>9.4f}{r['mean']/A.loc[2021,'mean']:>8.2f}"
              f"{r['meanR']:>9.3f}{r['meanR']/A.loc[2021,'meanR']:>8.2f}"
              f"{r['stop_med']:>10.3f}"
              f"{r['stop_med']/A.loc[2021,'stop_med']:>8.2f}"
              f"{r['p']*100:>9.2f}{r['W_R']:>8.2f}")

    # ------------------------------------------------ per coin
    print("\n" + "-" * 100)
    print("BY COIN - is the decay one asset or all three?")
    print("-" * 100)
    print(f"{'coin':<9}{'year':<6}{'n':>7}{'p_win%':>8}{'W%':>8}{'L%':>7}"
          f"{'gross%':>9}{'meanR':>8}{'stopmed%':>10}")
    for sym, gs in d.groupby("sym"):
        for y, g in gs.groupby("y"):
            a = anatomy(g, g["win"].to_numpy().astype(bool))
            print(f"{sym:<9}{y:<6}{a['n']:>7,}{a['p']*100:>8.2f}"
                  f"{a['W']:>8.3f}{a['L']:>7.3f}{a['mean']:>9.4f}"
                  f"{a['meanR']:>8.3f}{a['stop_med']:>10.3f}")
        print()

    # ------------------------------------------------ cost in stop distances
    print("-" * 100)
    print("COST IN STOP DISTANCES, YEAR BY YEAR (R482 all-in on Coinbase)")
    print("charged for honest P&L, used for nothing else")
    print("-" * 100)
    print(f"{'year':<6}{'gross%':>9}{'cost%':>8}{'net%':>9}"
          f"{'cost/stop':>11}{'grossR':>9}{'t_day R':>9}{'netR':>9}"
          f"{'t_day netR':>12}{'net%/stopmed':>14}")
    for y, g in d.groupby("y"):
        cs = (g["cost"] / g["stop_pct"]).mean()
        t, _ = tstat_by_day(g["netR"], g["day"])
        tr, _ = tstat_by_day(g["R"], g["day"])
        rom = (g["gross_pct"] - g["cost"]).mean() / g["stop_pct"].median()
        print(f"{y:<6}{g['gross_pct'].mean():>9.4f}{g['cost'].mean():>8.4f}"
              f"{(g['gross_pct']-g['cost']).mean():>9.4f}{cs:>11.3f}"
              f"{g['R'].mean():>9.3f}{tr:>9.2f}{g['netR'].mean():>9.3f}"
              f"{t:>12.2f}{rom:>14.3f}")

    print("\n" + "-" * 100)
    print("TWO STATISTICS OF THE SAME POPULATION THAT DISAGREE IN SIGN")
    print("-" * 100)
    net = d["gross_pct"] - d["cost"]
    rom = net.mean() / d["stop_pct"].median()
    pertrade = d["netR"].mean()
    t_pt, nd = tstat_by_day(d["netR"], d["day"])
    print(f"  ratio of means  (mean net%) / (median stop%)      "
          f"{net.mean():.4f} / {d['stop_pct'].median():.4f} = {rom:>+7.3f}")
    print(f"  mean per trade  mean( net% / that trade's stop% ) "
          f"{'':>17}{pertrade:>+7.3f}   t by day {t_pt:+.2f} ({nd:,} days)")
    print("  R481 quoted the FIRST as '+0.196 stop distances left over'. A")
    print("  book sized off each trade's OWN stop earns the SECOND. They")
    print("  disagree because 1/stop has a heavy right tail: the tightest")
    print("  stops pay the same % cost against a far smaller distance.")
    q = d["stop_pct"].quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    print(f"  stop% deciles: p10 {q[0.1]:.3f}  p25 {q[0.25]:.3f}  "
          f"p50 {q[0.5]:.3f}  p75 {q[0.75]:.3f}  p90 {q[0.9]:.3f}")
    print(f"  share of entries whose stop is under the round-trip cost: "
          f"{(d['stop_pct'] < d['cost']).mean()*100:.2f}%")
    print("  Stated, not acted on: no filter is proposed here and none may be")
    print("  (a stop threshold would be a swept parameter).")
    return A


# ================================================================== PART B
def part_b(d):
    print("\n" + LINE)
    print("(b)  IS IT MONOTONE, OR IS 2026 A STUB?")
    print(LINE)

    d = d.copy()
    d["half"] = d["sig_t"].dt.year.astype(str) + "H" + \
        ((d["sig_t"].dt.month > 6).astype(int) + 1).astype(str)
    d["q"] = d["sig_t"].dt.to_period("Q").astype(str)

    print("\nHALF-YEARS")
    print(f"{'half':<9}{'n':>7}{'p_win%':>8}{'W%':>8}{'L%':>7}{'gross%':>9}"
          f"{'meanR':>8}{'stopmed%':>10}{'t_day':>8}")
    for h, g in d.groupby("half"):
        a = anatomy(g, g["win"].to_numpy().astype(bool))
        t, _ = tstat_by_day(g["gross_pct"], g["day"])
        print(f"{h:<9}{a['n']:>7,}{a['p']*100:>8.2f}{a['W']:>8.3f}"
              f"{a['L']:>7.3f}{a['mean']:>9.4f}{a['meanR']:>8.3f}"
              f"{a['stop_med']:>10.3f}{t:>8.2f}")

    print("\nQUARTERS (gross% / meanR / stop median%)")
    qs = []
    for q, g in d.groupby("q"):
        qs.append((q, len(g), g["gross_pct"].mean(), g["R"].mean(),
                   g["stop_pct"].median()))
    for i in range(0, len(qs), 4):
        print("   " + "   ".join(
            f"{q:<8}{m:>+7.3f}%{r:>+7.2f}R{s:>7.3f}"
            for q, n, m, r, s in qs[i:i + 4]))

    # ------------------------------------------------ calendar-matched
    print("\n" + "-" * 100)
    print("THE STUB, FIXED: every year cut to 2026's own window "
          "(Jan 1 -> Jul 26)")
    print("-" * 100)
    doy = d["sig_t"].dt.dayofyear
    cut = d[doy <= 207]
    print(f"{'year':<6}{'n':>7}{'days':>6}{'p_win%':>8}{'W%':>8}{'L%':>7}"
          f"{'gross%':>9}{'meanR':>8}{'stopmed%':>10}{'t_day':>8}")
    for y, g in cut.groupby("y"):
        a = anatomy(g, g["win"].to_numpy().astype(bool))
        t, _ = tstat_by_day(g["gross_pct"], g["day"])
        print(f"{y:<6}{a['n']:>7,}{g['day'].nunique():>6}{a['p']*100:>8.2f}"
              f"{a['W']:>8.3f}{a['L']:>7.3f}{a['mean']:>9.4f}"
              f"{a['meanR']:>8.3f}{a['stop_med']:>10.3f}{t:>8.2f}")
    print("\n  2026 is now compared to stubs, not to full years.")

    # ------------------------------------------------ trend tests
    print("\n" + "-" * 100)
    print("TREND TESTS on the daily series (the unit that repeats)")
    print("-" * 100)
    for lab, col in (("gross% of price", "gross_pct"), ("risk multiple R", "R"),
                     ("stop median%", "stop_pct")):
        day = d.groupby("day")[col].mean()
        x = (day.index - day.index[0]).days.to_numpy(float)
        y = day.to_numpy(float)
        ok = np.isfinite(y)
        x, y = x[ok], y[ok]
        n = len(x)
        b, a0 = np.polyfit(x, y, 1)
        yhat = a0 + b * x
        se = np.sqrt(((y - yhat) ** 2).sum() / (n - 2) /
                     ((x - x.mean()) ** 2).sum())
        tb = b / se
        print(f"  {lab:<18} slope {b*365:>+9.5f} per YEAR   t = {tb:>6.2f}"
              f"   ({n:,} days)   {'DECAYING' if tb < -2 else ''}"
              f"{'RISING' if tb > 2 else ''}"
              f"{'flat (|t| < 2)' if abs(tb) <= 2 else ''}")

    # Spearman on the six year means, gross and R
    from scipy import stats as sps
    yr = d.groupby("y").agg(g=("gross_pct", "mean"), r=("R", "mean"),
                            s=("stop_pct", "median"))
    for lab, col in (("gross%", "g"), ("meanR", "r"), ("stop median%", "s")):
        rho, p = sps.spearmanr(yr.index.to_numpy(float), yr[col].to_numpy())
        print(f"  Spearman year vs {lab:<14} rho {rho:>+6.3f}  p {p:>6.3f}"
              f"   (n = 6 years, so this is weak by construction)")


# ================================================================== PART C
def part_c():
    print("\n" + LINE)
    print("(c)  DOES THE INDEX DECAY OVER THE SAME CALENDAR YEARS?")
    print(LINE)
    import step474_tjr_index_1m as S

    frames = []
    for sym in ("SPY", "QQQ"):
        d5, d1 = S.prep(sym)
        lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
        i1n = d5["i1_next"].to_numpy()
        for col, dirn, lab in S.LEVELS:
            sw, sig5 = S.scan_sweeps(d5, col, dirn)
            if len(sig5) == 0:
                continue
            ent1, swB = S.trigger_1m(d5, d1, sw, dirn)
            if not len(ent1):
                continue
            a1 = i1n[swB]
            stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                              else hi1[max(0, a):b + 1].max()
                              for a, b in zip(a1, ent1)])
            r = S.simulate(d1, ent1, dirn, stopB, None)   # hold to close
            if not len(r):
                continue
            r = r.copy()
            r["sym"], r["level"], r["dirn"] = sym, lab, dirn
            frames.append(r)
        print(f"  {sym}: built")
    ix = pd.concat(frames, ignore_index=True)
    ix["sig_t"] = pd.to_datetime(ix["sig_t"])
    ix["y"] = ix["sig_t"].dt.year
    ix["day"] = ix["sig_t"].dt.floor("D")
    ix["R"] = ix["gross_pct"] / ix["stop_pct"]
    ix["netR_pt"] = (ix["gross_pct"] - COST_INDEX) / ix["stop_pct"]
    ix["win"] = ix["reason"] != "stop"      # survived to the close
    ix.to_csv(f"{REPO}/step485_index_entries.csv", index=False)

    print(f"\n  {len(ix):,} index entries, 1-minute trigger, hold to close, "
          f"eight levels pooled, SPY + QQQ")
    ded = ix.drop_duplicates(["sym", "sig_i"])
    print(f"  dedupe sensitivity: {len(ded):,} unique (sym, signal bar) - "
          f"pooled gross {ix['gross_pct'].mean():+.4f}% vs deduped "
          f"{ded['gross_pct'].mean():+.4f}%")

    print("\nBY CALENDAR YEAR (whole population, no slice, no qualification)")
    hdr = (f"{'year':<6}{'n':>7}{'days':>6}{'surv%':>8}{'W%':>8}{'L%':>7}"
           f"{'gross%':>9}{'net%':>9}{'meanR':>8}{'netR_pt':>9}"
           f"{'net%/stop':>11}{'stopmed%':>10}{'t_day':>8}")
    print(hdr)
    print("-" * len(hdr))
    for y, g in ix.groupby("y"):
        a = anatomy(g, g["win"].to_numpy().astype(bool))
        t, _ = tstat_by_day(g["gross_pct"], g["day"])
        print(f"{y:<6}{a['n']:>7,}{g['day'].nunique():>6}{a['p']*100:>8.2f}"
              f"{a['W']:>8.3f}{a['Lg']:>7.3f}{a['mean']:>9.4f}"
              f"{a['mean']-COST_INDEX:>9.4f}{a['meanR']:>8.3f}"
              f"{g['netR_pt'].mean():>9.3f}"
              f"{(a['mean']-COST_INDEX)/a['stop_med']:>11.3f}"
              f"{a['stop_med']:>10.3f}{t:>8.2f}")
    print(f"\n  INDEX, whole 2016-2026 population, the same two statistics:")
    print(f"    ratio of means  {(ix['gross_pct'].mean()-COST_INDEX):.4f} / "
          f"{ix['stop_pct'].median():.4f} = "
          f"{(ix['gross_pct'].mean()-COST_INDEX)/ix['stop_pct'].median():+.3f}")
    tix, ndix = tstat_by_day(ix["netR_pt"], ix["day"])
    print(f"    mean per trade  {ix['netR_pt'].mean():+.3f}   "
          f"t by day {tix:+.2f} ({ndix:,} days)")
    print(f"    share of index entries whose stop is under the 0.04% round "
          f"trip: {(ix['stop_pct'] < COST_INDEX).mean()*100:.2f}%")
    print("\n  surv% = share NOT stopped (they exit at the close, and unlike")
    print("  crypto's cap-runners they can exit negative). W = their mean")
    print("  gross; L = the mean LOSS of the stopped.")

    # per asset, overlapping years only
    print("\nPER ASSET, 2021-2026 (the crypto window)")
    print(f"{'sym':<5}{'year':<6}{'n':>7}{'gross%':>9}{'meanR':>8}"
          f"{'stopmed%':>10}")
    for sym, gs in ix[ix["y"] >= 2021].groupby("sym"):
        for y, g in gs.groupby("y"):
            print(f"{sym:<5}{y:<6}{len(g):>7,}{g['gross_pct'].mean():>9.4f}"
                  f"{g['R'].mean():>8.3f}{g['stop_pct'].median():>10.3f}")
        print()
    return ix


def part_c_vol(ix, d):
    print("-" * 100)
    print("THE PRICE SCALE ITSELF - realized 1-minute volatility by year")
    print("mean |1-minute return|, % of price. If gross% tracks THIS, the")
    print("edge did not decay; the market got smaller.")
    print("-" * 100)
    vols = {}
    for sym, path in (("BTC", "data_alpaca_BTCUSD_1m.parquet"),
                      ("ETH", "data_alpaca_ETHUSD_1m.parquet"),
                      ("SOL", "data_alpaca_SOLUSD_1m.parquet"),
                      ("SPY", "data_alpaca_SPY_1m.parquet"),
                      ("QQQ", "data_alpaca_QQQ_1m.parquet")):
        try:
            vols[sym] = realized_vol(sym, f"{REPO}/{path}")
        except Exception as e:                       # pragma: no cover
            print(f"  {sym}: unavailable ({e})")
    V = pd.DataFrame(vols)
    years = [y for y in range(2016, 2027) if y in V.index]
    print(f"{'year':<6}" + "".join(f"{s:>9}" for s in V.columns) +
          f"{'crypto gross%':>15}{'index gross%':>14}")
    cg = d.groupby("y")["gross_pct"].mean()
    ig = ix.groupby("y")["gross_pct"].mean()
    for y in years:
        row = f"{y:<6}"
        for s in V.columns:
            v = V[s].get(y, np.nan)
            row += f"{v:>9.4f}" if np.isfinite(v) else f"{'-':>9}"
        row += f"{cg.get(y, np.nan):>15.4f}" if y in cg.index else f"{'-':>15}"
        row += f"{ig.get(y, np.nan):>14.4f}" if y in ig.index else f"{'-':>14}"
        print(row)

    # ---- the signal per unit of market movement
    if {"BTC", "ETH", "SOL"} <= set(V.columns):
        cvol = V[["BTC", "ETH", "SOL"]].mean(axis=1)
        print("\nSIGNAL PER UNIT OF MARKET MOVEMENT")
        print("gross% divided by that year's mean |1-minute return|. If the")
        print("edge is intact and only the market shrank, THIS is flat.")
        print(f"{'year':<6}{'crypto gross%':>14}{'crypto vol':>12}"
              f"{'gross/vol':>11}{'index gross%':>14}{'SPY vol':>9}"
              f"{'gross/vol':>11}")
        for y in range(2021, 2027):
            cv = cvol.get(y, np.nan)
            sv = V["SPY"].get(y, np.nan) if "SPY" in V.columns else np.nan
            g1 = cg.get(y, np.nan)
            g2 = ig.get(y, np.nan)
            print(f"{y:<6}{g1:>14.4f}{cv:>12.4f}{g1/cv:>11.2f}"
                  f"{g2:>14.4f}{sv:>9.4f}{g2/sv:>11.2f}")

    # ---- does the gross track the scale, year by year?
    from scipy import stats as sps
    print("\nDOES THE GROSS TRACK THE PRICE SCALE? (correlation across years)")
    if "SPY" in V.columns:
        yrs = [y for y in ig.index if y in V.index]
        a = np.array([ig.loc[y] for y in yrs])
        b = np.array([V["SPY"].loc[y] for y in yrs])
        r, p = sps.pearsonr(a, b)
        rs, ps = sps.spearmanr(a, b)
        print(f"  INDEX  gross% vs SPY 1-minute vol, {len(yrs)} years "
              f"({min(yrs)}-{max(yrs)}):  r {r:+.3f} (p {p:.3f}), "
              f"rho {rs:+.3f} (p {ps:.3f})")
    if {"BTC", "ETH", "SOL"} <= set(V.columns):
        cvol2 = V[["BTC", "ETH", "SOL"]].mean(axis=1)
        yrs = [y for y in cg.index if y in cvol2.index]
        a = np.array([cg.loc[y] for y in yrs])
        b = np.array([cvol2.loc[y] for y in yrs])
        r, p = sps.pearsonr(a, b)
        rs, ps = sps.spearmanr(a, b)
        print(f"  CRYPTO gross% vs 3-coin 1-minute vol, {len(yrs)} years "
              f"({min(yrs)}-{max(yrs)}):  r {r:+.3f} (p {p:.3f}), "
              f"rho {rs:+.3f} (p {ps:.3f})")
        print("  Six points is six points - this is a description, not a test.")

    print("\nRATIOS TO 2021 (crypto window), so the two are on one scale")
    print(f"{'year':<6}{'BTC vol':>9}{'crypto stop':>13}{'crypto gross':>14}"
          f"{'crypto R':>10}{'SPY vol':>9}{'index stop':>12}"
          f"{'index gross':>13}{'index R':>9}")
    cs = d.groupby("y")["stop_pct"].median()
    cr = d.groupby("y")["R"].mean()
    isx = ix.groupby("y")["stop_pct"].median()
    ir = ix.groupby("y")["R"].mean()
    for y in range(2021, 2027):
        def rat(s, base=2021):
            try:
                return float(s.loc[y]) / float(s.loc[base])
            except Exception:
                return np.nan
        bv = V["BTC"] if "BTC" in V.columns else pd.Series(dtype=float)
        sv = V["SPY"] if "SPY" in V.columns else pd.Series(dtype=float)
        print(f"{y:<6}{rat(bv):>9.2f}{rat(cs):>13.2f}{rat(cg):>14.2f}"
              f"{rat(cr):>10.2f}{rat(sv):>9.2f}{rat(isx):>12.2f}"
              f"{rat(ig):>13.2f}{rat(ir):>9.2f}")


def main():
    print(LINE)
    print("ROUND 485 - THE DECAY, MEASURED  (queue item 9)")
    print("RESEARCH ONLY. NO ORDERS. NO LOOK CONSUMED. NOTHING DEPLOYED.")
    print(LINE)
    d = load_crypto()
    print(f"crypto population: {len(d):,} entries, "
          f"{d['sig_t'].min():%Y-%m-%d} -> {d['sig_t'].max():%Y-%m-%d}, "
          f"{d['day'].nunique():,} days, coins {sorted(d['sym'].unique())}")
    part_a(d)
    part_b(d)
    ix = part_c()
    part_c_vol(ix, d)
    print("\n" + LINE)
    print("END OF ROUND 485. NO CELL QUALIFIED, NONE COULD - THIS ROUND")
    print("DESCRIBES A PUBLISHED POPULATION. NO LOOK CONSUMED. NO ORDER.")
    print(LINE)


if __name__ == "__main__":
    main()
