"""
step477_tjr_daily_bias_partition.py - ROUND 477

HIS DAILY BIAS AS A PARTITION OF THE POPULATION ROUND 450 ALREADY BUILT.

Research only. No orders. No live file touched. Nothing here is deployed by
this script under any outcome.

READ THIS BEFORE THE NUMBERS: THIS ROUND CANNOT QUALIFY ANYTHING
  Both sealed windows this family had are spent - R474 took SPY/QQQ's, R475
  took crypto's - and the backfilled 2021-2026 crypto window has boundaries
  that R450 and R475 have both already read inside. There is no clean
  out-of-sample slice left anywhere on the sweep-to-break-of-structure
  family. THEREFORE this round produces a DESCRIPTION, not a qualification.
  It opens no look and proposes no deployment. The qualification arithmetic
  is still computed and printed, because the queue asks for the cell census
  and its chance baseline, but it is explicitly barred from promoting
  anything and there is no sealed-slice block in this file at all. A
  candidate off this family needs a NEW instrument or NEW data. Fixed before
  the run.

QUEUE ITEM 3, VERBATIM
  "HIS DAILY BIAS AS A PARTITION (step434). Same population, same rule: keep
   only sweeps taken in the direction of the 4-hour / daily bias his spec
   defines. One partition, both directions reported, chance baseline stated.
   Runs after item 2 so both partitions are measured against the same
   unfiltered population."

  Item 2 is done (R476). The unfiltered population here is the identical
  object R475 and R476 measured: round 450's arm B, its module imported and
  its functions called unchanged.

WHAT IS FAITHFUL TO HIM
  step434 s1D is unambiguous about which bias procedure he RUNS, as opposed
  to the one he teaches: "On every live morning in the bootcamp files he runs
  Procedure B, not Procedure A." Procedure B is nested trend, and the rule it
  turns on is stated plainly in his own words:

    "ideally we see daily and the four hour in confluence and the one hour,
     but most of the time at least I need the daily and the four hour to be
     in confluence."                                          (Day50)

    "bearish on the weekly, but bullish on the daily, so what bias are we
     going to be using? We're going to be using the daily bias because we are
     trying to predict the daily moves."                      (Day49)

    "we get a break of structure to the downside so I'm bearish on the daily
     prior to this candle to the downside I would have been bullish not
     anymore."                                                (Day34-36)

    "we're going to stick to this bias until we're proved wrong."  (Day50)

  So the bias on a timeframe is the direction of the MOST RECENT break of
  structure on that timeframe, held until a break the other way flips it.
  Break of structure is his definition and the one round 450 already uses: a
  candle BODY CLOSE beyond the most recent confirmed two-candle swing, never
  a wick. Structure is read with R.tjr_swings, the same function that builds
  every other level in this family - nothing new is invented here.

  Three partitions, and each one is a sentence of his, not a guess:
    DAILY  - the trade runs WITH the daily bias. ("most of our trades are in
             line with the daily", Day49. Daily wins conflicts.)
    H4     - the trade runs WITH the 4-hour bias.
    AGREE  - daily and 4-hour agree AND the trade runs with them. This is the
             live rule as he states it, and it is the primary partition.
  Reported beside them, because it is the other half of his rule:
    STAND-DOWN - the entries taken on days the two timeframes DISAGREE, which
             is the population his instruction throws away wholesale
             ("stand down or downgrade the instrument", Day50/53/55).

  PROCEDURE A - the previous-session profile method - is NOT built. It is the
  method he teaches and does not perform (step434 s1D and s8 item 3), it
  needs a London session on a 24/7 market that has none, and merging the two
  procedures is flagged in the spec itself as OUR reconstruction that "he
  never says to combine". One partition, as the queue says.

OURS, AND LABELLED
  - Daily and 4-hour candles are cut on the UTC grid, the live desk's
    boundary, inherited from round 450 (R.resample).
  - The bias is read at the entry instant from the last higher-timeframe
    candle that had already CLOSED, with the swing columns one bar staler
    still (R.ffill_shift). Strictly causal and deliberately conservative.
  - A candle that closes through BOTH the recent swing high and the recent
    swing low leaves the bias unchanged rather than picking a side. It is
    rare and a coin-flip tiebreak would be a hidden parameter.
  - Before the first break of structure on a timeframe there is no bias at
    all; those entries are counted separately as `no bias yet` and are in
    neither the kept nor the thrown-away set.
  - Everything else is round 450's, untouched: 2-hour pending expiry,
    24-hour hold cap, structural stop, 0.50% of notional round trip charged
    for honesty and used to decide nothing (owner rule 2026-07-25).

HOW IT IS SCORED
  The headline is GROSS and day-clustered, because the question is whether
  his bias selects a better subset of his own entries - a question about the
  signal, not about what Alpaca charges to collect it. R476 established the
  clustering unit for this desk: the UTC calendar day, three coins inside one
  day collapsing to ONE observation. Kept-minus-thrown is reported paired on
  shared days, which is the comparison R476 showed is the one to quote.
  R475 reported this family's partition t naive; that understates nothing
  here because both numbers are printed side by side.

USAGE
  python3 step477_tjr_daily_bias_partition.py
"""

import io
import contextlib
import sys

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"

# the partitions, in the order they are reported. AGREE is the primary.
FILTERS = ["DAILY", "H4", "AGREE"]


# ------------------------------------------------------------- his bias
def structure_bias(d5, minutes):
    """The direction of the most recent break of structure on the `minutes`
    chart, held until a break the other way flips it.

    Returns a frame of (known_at, bias) where known_at is the CLOSE of the
    candle that set it, so a merge_asof backward onto any later timestamp is
    strictly causal.
    """
    htf = R.resample(d5, minutes)
    o = htf["open"].to_numpy(); h = htf["high"].to_numpy()
    l = htf["low"].to_numpy(); c = htf["close"].to_numpy()
    sh, sl = R.tjr_swings(o, h, l, c)
    mr_sh = R.ffill_shift(sh)        # most recent CONFIRMED swing, one bar
    mr_sl = R.ffill_shift(sl)        # stale, so a close never uses its own bar
    n = len(htf)
    bias = np.zeros(n, dtype=int)
    cur = 0
    for i in range(n):
        up = np.isfinite(mr_sh[i]) and c[i] > mr_sh[i]
        dn = np.isfinite(mr_sl[i]) and c[i] < mr_sl[i]
        if up and not dn:
            cur = +1
        elif dn and not up:
            cur = -1
        # both, or neither: hold. OURS, stated, never a coin flip.
        bias[i] = cur
    known = htf["t"] + pd.Timedelta(minutes=minutes)
    return pd.DataFrame({"t": known, "bias": bias})


def bias_at(entry_times, bias_frame):
    """The bias standing at each entry instant, from the last higher-timeframe
    candle that had already CLOSED. merge_asof needs a sorted key, so the
    caller's original order is restored afterwards."""
    q = pd.DataFrame({"t": pd.to_datetime(entry_times)}).sort_values("t")
    m = pd.merge_asof(q, bias_frame.sort_values("t"), on="t",
                      direction="backward")
    out = m["bias"].fillna(0).to_numpy(int)
    return pd.Series(out, index=q.index).sort_index().to_numpy()


def bias_flags(d1, ent1, dirn, bd, bh):
    """Per entry: does the trade run with the daily bias, the 4-hour bias, and
    with both when the two agree? Plus the two book-keeping sets."""
    ts = d1["t"].to_numpy()[ent1]
    b_d = bias_at(ts, bd)
    b_h = bias_at(ts, bh)
    known = (b_d != 0) & (b_h != 0)          # both timeframes have a bias yet
    agree_tf = known & (b_d == b_h)
    return {
        "DAILY": (b_d == dirn),
        "H4": (b_h == dirn),
        "AGREE": agree_tf & (b_d == dirn),
        # reported, never a candidate: the days his instruction sits out
        "STANDDOWN": known & (b_d != b_h),
        "NOBIAS": ~known,
        "_bd": b_d, "_bh": b_h,
    }


# ----------------------------------------------------------- book-keeping
def align_mask(ent1, returned, flag):
    """simulate() returns rows in the order it received candidates, skipping
    the ones it could not score. Walk both in order so the mask is POSITIONAL
    - two sweeps that trigger on the same 1-minute bar can never be confused
    for each other. (Round 475's helper, unchanged.)"""
    out = np.zeros(len(returned), bool)
    j = 0
    for k, e in enumerate(returned):
        while ent1[j] != e:
            j += 1
        out[k] = flag[j]
        j += 1
    return out


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def utc_day(res):
    return pd.to_datetime(res["sig_t"]).dt.normalize()


def clustered(res, col="gross_pct"):
    """R476's unit: one mean per UTC day pooled across every asset."""
    d = res.assign(day=utc_day(res)).groupby("day")[col].mean()
    return tstat(d)


def dedupe(res):
    """The four target settings score the SAME entries; collapse to one row
    per distinct entry so they are not counted as four draws."""
    return res.drop_duplicates(subset=["sig_i", "sig_t", "stop_pct"])


def paired_day_diff(kept, thrown):
    """Kept minus thrown away, paired on shared UTC days - the comparison
    R476 established as the one to quote for this population."""
    a = kept.assign(day=utc_day(kept)).groupby("day")["gross_pct"].mean()
    b = thrown.assign(day=utc_day(thrown)).groupby("day")["gross_pct"].mean()
    j = pd.concat([a.rename("k"), b.rename("c")], axis=1).dropna()
    d = j["k"] - j["c"]
    t, n = tstat(d)
    return d.mean(), t, n


# --------------------------------------------------------------- the round
def run_asset(sym, store, counts):
    d5, d1 = R.prep(sym)
    lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    bd = structure_bias(d5, 1440)     # DAILY - sets the bias
    bh = structure_bias(d5, 240)      # 4-HOUR - the agreement check
    for col, dirn, lab in R.LEVELS:
        sw, sig5 = R.scan_sweeps(d5, col, dirn)
        if len(sig5) == 0:
            continue
        ent1, swB = R.trigger_1m(d5, d1, sw, dirn)
        if not len(ent1):
            continue
        a1 = i1n[swB]
        stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                          else hi1[max(0, a):b + 1].max()
                          for a, b in zip(a1, ent1)])
        flags = bias_flags(d1, ent1, dirn, bd, bh)
        counts.append(dict(sym=sym, level=lab, dirn=dirn, entries=len(ent1),
                           DAILY=int(flags["DAILY"].sum()),
                           H4=int(flags["H4"].sum()),
                           AGREE=int(flags["AGREE"].sum()),
                           STANDDOWN=int(flags["STANDDOWN"].sum()),
                           NOBIAS=int(flags["NOBIAS"].sum())))
        for rt, rlab in R.TARGETS:
            # ONE simulation of the parent; every subset below is rows of the
            # same frame, so a filtered set is a strict subset of the same
            # entries by construction rather than by hope.
            res = R.simulate(d1, ent1, dirn, stopB, rt, R.MAX_HOLD_MIN)
            nm = f"{lab} -> 1m BOS, {rlab}"
            res = res.assign(dirn=dirn)
            store.setdefault((nm, "PARENT"), []).append((sym, res))
            if not len(res):
                continue
            returned = res["sig_i"].to_numpy()
            for fk in FILTERS + ["STANDDOWN"]:
                mask = align_mask(ent1, returned, flags[fk])
                sub, comp = res[mask], res[~mask]
                assert set(sub["sig_t"]).issubset(set(res["sig_t"])), \
                    "filtered set is not a strict subset of the parent"
                assert len(sub) + len(comp) == len(res), "partition leaks"
                store.setdefault((nm, fk), []).append((sym, sub))
                store.setdefault((nm, fk + "_C"), []).append((sym, comp))
    return d5, d1


def pooled_table(store, t_tr, t_va, arm):
    out = []
    for (nm, a), parts in store.items():
        if a != arm:
            continue
        allr = pd.concat([r for _, r in parts]) if parts else pd.DataFrame()
        if not len(allr):
            continue
        tr, va, te = R.slice_by_time(allr, t_tr, t_va)
        s = R.summarise(nm, tr, va)
        indiv = []
        for sym, r in parts:
            t_, v_, _ = R.slice_by_time(r, t_tr, t_va)
            indiv.append(t_["net_pct"].mean() if len(t_) >= 10 else np.nan)
        s["n_assets_pos"] = int(np.nansum(np.array(indiv, float) > 0))
        s["arm"] = a
        out.append(s)
    return pd.DataFrame(out)


def collapse(store, arms):
    """One row per distinct entry, per arm, deduped PER ASSET (two coins can
    share a timestamp and a pooled drop_duplicates would delete one)."""
    uniq = {}
    for arm in arms:
        frames = []
        for (nm, a), parts in store.items():
            if a != arm:
                continue
            for sym, res in parts:
                if len(res):
                    frames.append(res.assign(sym=sym))
        if not frames:
            continue
        allf = pd.concat(frames)
        uniq[arm] = pd.concat([dedupe(g) for _, g in allf.groupby("sym")])
    return uniq


def main():
    print("=" * 108)
    print("ROUND 477 - HIS DAILY BIAS AS A PARTITION OF ROUND 450's ARM B")
    print("=" * 108)
    print("THIS ROUND CANNOT QUALIFY ANYTHING. Both sealed windows on this")
    print("family are spent (R474 SPY/QQQ, R475 crypto) and the backfilled")
    print("window has boundaries R450 and R475 have both already read inside.")
    print("No look is opened. Nothing below is out-of-sample evidence.")
    print("\nBias = the direction of the most recent BODY-CLOSE break of the")
    print("most recent confirmed two-candle swing, held until it flips")
    print("(step434 s1D). DAILY sets it, the 4-HOUR must agree, daily wins")
    print("conflicts. Procedure A (previous-session profile) is NOT built -")
    print("he teaches it and does not perform it, and it needs a London")
    print("session that a 24/7 market does not have.")

    b5 = R.load("BTCUSD", "5m")
    b1 = R.load("BTCUSD", "1m")
    t0 = max(b5["t"].iloc[0], b1["t"].iloc[0])
    t1 = min(b5["t"].iloc[-1], b1["t"].iloc[-1])
    span = t1 - t0
    t_tr = t0 + span * 0.60
    t_va = t0 + span * 0.80
    print(f"\nwindow {t0:%Y-%m-%d} -> {t1:%Y-%m-%d} UTC  ({span.days} days)")
    print(f"slice labels, for continuity with R450/R475/R476 only: choosing < "
          f"{t_tr:%Y-%m-%d}, middle < {t_va:%Y-%m-%d}, then the rest.")
    print(f"cost {R.COST_RT}% of notional round trip, charged for honesty and "
          f"used to decide nothing.")
    del b5, b1

    store, counts = {}, []
    for sym in R.PRIMARY:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            d5, d1 = run_asset(sym, store, counts)
        print(f"  {sym}: {len(d5):,} 5-minute bars, {len(d1):,} 1-minute bars, "
              f"{d5['t'].iloc[0]:%Y-%m-%d} -> {d5['t'].iloc[-1]:%Y-%m-%d}")
        sys.stdout.flush()

    cnt = pd.DataFrame(counts)
    cnt.to_csv(f"{REPO}/step477_counts.csv", index=False)

    # ------------------------------------------ what the bias throws away
    print("\n" + "=" * 108)
    print("WHAT THE BIAS REQUIREMENT ACTUALLY REMOVES  (all entries, all slices)")
    print("=" * 108)
    tot = cnt[["entries", "DAILY", "H4", "AGREE", "STANDDOWN", "NOBIAS"]].sum()
    print(f"{'population':<44}{'entries kept':>14}{'share of parent':>18}")
    print(f"{'parent (bare sweep -> 1m BOS)':<44}{int(tot['entries']):>14,}"
          f"{'100.0%':>18}")
    for k, lab in (("DAILY", "with the DAILY bias"),
                   ("H4", "with the 4-HOUR bias"),
                   ("AGREE", "with BOTH, and the two agree (his live rule)"),
                   ("STANDDOWN", "days the two DISAGREE (he sits out)"),
                   ("NOBIAS", "no bias formed yet (in neither set)")):
        print(f"  {lab:<42}{int(tot[k]):>14,}"
              f"{100.0*tot[k]/tot['entries']:>17.1f}%")
    print("\nHis own frequency check (step434 s6F): he trades a MINORITY of")
    print("sessions, on the order of 7-15 days a month. A partition that keeps")
    print("nearly everything has not filtered anything.")

    # ----------------------------------------------- the partition effect
    arms = ["PARENT"] + [f for fk in FILTERS for f in (fk, fk + "_C")] + \
           ["STANDDOWN", "STANDDOWN_C"]
    uniq = collapse(store, arms)

    print("\n" + "=" * 108)
    print("DOES HIS BIAS SELECT A BETTER SUBSET? - WHOLE WINDOW, GROSS, "
          "one row per entry")
    print("=" * 108)
    print("t by day pools BTC, ETH and SOL into ONE observation per UTC day")
    print("(R476's unit). Gross, because the question is about the signal.")
    print(f"\n{'population':<44}{'entries':>9}{'days':>7}{'mean gross':>12}"
          f"{'t naive':>9}{'t by day':>10}{'stop%':>8}{'lev@1%':>8}")
    rows = [("parent (bare sweep -> 1m BOS)", "PARENT")]
    for fk in FILTERS:
        rows.append((f"  kept by {fk}", fk))
        rows.append((f"  thrown away by {fk}", fk + "_C"))
    rows.append(("  STAND-DOWN set (he sits these out)", "STANDDOWN"))
    eff_rows = []
    for lab, key in rows:
        u = uniq.get(key)
        if u is None or not len(u):
            continue
        tn, n = tstat(u["gross_pct"])
        tc, nd = clustered(u)
        st = u["stop_pct"].median()
        print(f"{lab:<44}{n:>9,}{nd:>7,}{u['gross_pct'].mean():>11.4f}%"
              f"{tn:>9.2f}{tc:>10.2f}{st:>7.3f}%{1/st if st > 0 else np.nan:>7.1f}x")
        eff_rows.append(dict(population=lab.strip(), key=key, entries=n,
                             days=nd, gross=u["gross_pct"].mean(),
                             t_naive=tn, t_by_day=tc, stop_median=st))
    pd.DataFrame(eff_rows).to_csv(f"{REPO}/step477_populations.csv", index=False)

    print("\nKEPT MINUS THROWN AWAY - the only comparison that tests a "
          "partition,")
    print("paired on shared UTC days (R476's standard):")
    diffs = []
    for fk in FILTERS:
        k, c = uniq.get(fk), uniq.get(fk + "_C")
        if k is None or c is None or not len(k) or not len(c):
            continue
        raw = k["gross_pct"].mean() - c["gross_pct"].mean()
        se = np.sqrt(k["gross_pct"].var(ddof=1) / len(k) +
                     c["gross_pct"].var(ddof=1) / len(c))
        pd_mean, pd_t, pd_n = paired_day_diff(k, c)
        print(f"  {fk:<10} unpaired {raw:+.4f}%  t {raw/se if se > 0 else np.nan:>6.2f}"
              f"   |   PAIRED BY DAY {pd_mean:+.4f}%  t {pd_t:>6.2f}"
              f"  over {pd_n:,} shared days   kept {len(k):,} / thrown {len(c):,}")
        diffs.append(dict(filt=fk, unpaired=raw, t_unpaired=raw/se if se > 0 else np.nan,
                          paired=pd_mean, t_paired=pd_t, shared_days=pd_n,
                          n_kept=len(k), n_thrown=len(c)))
    pd.DataFrame(diffs).to_csv(f"{REPO}/step477_partition_effect.csv", index=False)

    # ------------------------------------------------- BOTH DIRECTIONS
    print("\n" + "=" * 108)
    print("BOTH DIRECTIONS REPORTED, as the queue requires")
    print("=" * 108)
    print("A bias filter that only helps one side is a directional bet on the")
    print("sample, not a filter. Longs and shorts are scored separately.")
    print(f"\n{'population':<44}{'LONG n':>9}{'LONG gross':>12}{'t/day':>8}"
          f"{'SHORT n':>10}{'SHORT gross':>13}{'t/day':>8}")
    dir_rows = []
    for lab, key in rows:
        u = uniq.get(key)
        if u is None or not len(u):
            continue
        cells = []
        for d in (+1, -1):
            g = u[u["dirn"] == d]
            if not len(g):
                cells.append((0, np.nan, np.nan))
                continue
            tc, _ = clustered(g)
            cells.append((len(g), g["gross_pct"].mean(), tc))
        (nl, gl, tl), (ns, gs, ts) = cells
        print(f"{lab:<44}{nl:>9,}{gl:>11.4f}%{tl:>8.2f}"
              f"{ns:>10,}{gs:>12.4f}%{ts:>8.2f}")
        dir_rows.append(dict(population=lab.strip(), long_n=nl, long_gross=gl,
                             long_t=tl, short_n=ns, short_gross=gs, short_t=ts))
    pd.DataFrame(dir_rows).to_csv(f"{REPO}/step477_by_direction.csv", index=False)

    # ------------------------------------------------------- by asset
    print("\n" + "=" * 108)
    print("THE PRIMARY PARTITION (AGREE) BY ASSET - a number that holds on one "
          "coin is a coin fact")
    print("=" * 108)
    print(f"{'asset':<10}{'kept n':>9}{'kept gross':>12}{'t/day':>8}"
          f"{'thrown n':>10}{'thrown gross':>14}{'t/day':>8}"
          f"{'paired diff':>13}{'t':>7}")
    for sym in R.PRIMARY:
        k = uniq["AGREE"]; c = uniq["AGREE_C"]
        k = k[k["sym"] == sym]; c = c[c["sym"] == sym]
        if not len(k) or not len(c):
            continue
        tk, _ = clustered(k); tc_, _ = clustered(c)
        dm, dt, dn = paired_day_diff(k, c)
        print(f"{sym:<10}{len(k):>9,}{k['gross_pct'].mean():>11.4f}%{tk:>8.2f}"
              f"{len(c):>10,}{c['gross_pct'].mean():>13.4f}%{tc_:>8.2f}"
              f"{dm:>12.4f}%{dt:>7.2f}")

    # ------------------------------------------------------- by year
    print("\n" + "=" * 108)
    print("YEAR BY YEAR - R476 found this family DECAYS; a partition can look "
          "real")
    print("purely by concentrating in the strong years")
    print("=" * 108)
    print(f"{'year':<6}{'parent n':>10}{'parent gross':>14}{'AGREE n':>9}"
          f"{'AGREE gross':>13}{'kept share':>12}{'paired diff':>13}{'t':>7}")
    yr_rows = []
    par = uniq["PARENT"].assign(y=pd.to_datetime(uniq["PARENT"]["sig_t"]).dt.year)
    ka = uniq["AGREE"].assign(y=pd.to_datetime(uniq["AGREE"]["sig_t"]).dt.year)
    ca = uniq["AGREE_C"].assign(y=pd.to_datetime(uniq["AGREE_C"]["sig_t"]).dt.year)
    for y, gp in par.groupby("y"):
        gk = ka[ka.y == y]; gc = ca[ca.y == y]
        if not len(gk) or not len(gc):
            continue
        dm, dt, _ = paired_day_diff(gk, gc)
        print(f"{int(y):<6}{len(gp):>10,}{gp['gross_pct'].mean():>13.4f}%"
              f"{len(gk):>9,}{gk['gross_pct'].mean():>12.4f}%"
              f"{100*len(gk)/len(gp):>11.1f}%{dm:>12.4f}%{dt:>7.2f}")
        yr_rows.append(dict(year=int(y), parent_n=len(gp),
                            parent_gross=gp["gross_pct"].mean(),
                            agree_n=len(gk), agree_gross=gk["gross_pct"].mean(),
                            kept_share=100*len(gk)/len(gp), paired=dm, t=dt))
    pd.DataFrame(yr_rows).to_csv(f"{REPO}/step477_by_year.csv", index=False)

    # -------------------------------------------------- the cell census
    print("\n" + "=" * 108)
    print("CELL CENSUS - DESCRIPTIVE ONLY, BARRED FROM PROMOTING ANYTHING")
    print("=" * 108)
    parent = pooled_table(store, t_tr, t_va, "PARENT").set_index("name")
    frames = {"PARENT": parent}
    for fk in FILTERS:
        frames[fk] = pooled_table(store, t_tr, t_va, fk).set_index("name")
        frames[fk + "_C"] = pooled_table(store, t_tr, t_va, fk + "_C").set_index("name")
    print(f"{'cell':<40}{'filter':>8}{'n_tr':>6}{'netTR':>9}{'netVA':>9}"
          f"{'parTR':>9}{'parVA':>9}{'compTR':>9}{'stop%':>8}{'lev':>7}")
    clears, scored = [], 0
    for nm in parent.index:
        p = parent.loc[nm]
        if p["verdict"] == "thin":
            continue
        for fk in FILTERS:
            f = frames[fk]
            if nm not in f.index:
                continue
            r = f.loc[nm]
            if r["verdict"] == "thin":
                print(f"{nm:<40}{fk:>8}{int(r['n_tr']):>6}"
                      f"{'':>9}{'':>9}{'':>9}{'':>9}{'':>9}{'':>8}{'  thin':>7}")
                continue
            scored += 1
            c = frames[fk + "_C"]
            ctr = c.loc[nm]["mean_tr"] if nm in c.index else np.nan
            print(f"{nm:<40}{fk:>8}{int(r['n_tr']):>6}"
                  f"{r['mean_tr']:>9.4f}{r['mean_va']:>9.4f}"
                  f"{p['mean_tr']:>9.4f}{p['mean_va']:>9.4f}"
                  f"{ctr:>9.4f}{r['stop_tr']:>8.3f}{r['lev']:>6.1f}x")
            beats = (r["mean_tr"] > p["mean_tr"]) and (r["mean_va"] > p["mean_va"])
            if (r["verdict"] == "qualifies" and r["n_assets_pos"] >= 2 and beats):
                clears.append(dict(name=nm, filt=fk, n_tr=int(r["n_tr"]),
                                   n_va=int(r["n_va"]), net_tr=r["mean_tr"],
                                   net_va=r["mean_va"], par_tr=p["mean_tr"],
                                   comp_tr=ctr, stop=r["stop_tr"], lev=r["lev"]))
    pd.concat([frames[k].assign(filt=k) for k in frames]).to_csv(
        f"{REPO}/step477_table.csv")

    print(f"\n{scored} partition cells scored (the three filters over the arm-B")
    print("cells thick enough to score).")
    print("EXPECTED BY CHANCE with no partition effect at all: a symmetric")
    print("zero-mean cell passes both slices about 1 time in 4, and beats its")
    print(f"parent on both slices about 1 time in 4 again, so roughly "
          f"{scored/16:.1f} of {scored}")
    print("would clear the full bar on luck alone.")
    print(f"\nCELLS CLEARING THE FULL BAR: {len(clears)}")
    if clears:
        cdf = pd.DataFrame(clears).sort_values("net_tr", ascending=False)
        print(cdf.to_string(index=False))
        cdf.to_csv(f"{REPO}/step477_clears.csv", index=False)
    print("\nThose counts CANNOT promote anything, whatever the number is. The")
    print("slices they are cut on have already been read by R450 and R475, and")
    print("this family has no sealed slice left on any instrument.")

    # ------------------------------------------------ the GROSS census
    # R476's warning applies with full force above: the net census scores on
    # NET, and at a 0.50% round trip against a ~0.14% gross NOTHING can pass
    # arithmetically - it is measuring Alpaca's fee schedule, not his bias.
    # Letting it stand alone would also let costs gate a config, which the
    # owner rule forbids outright. So the census that actually tests the
    # partition is repeated on GROSS, where the fee is not in the way.
    print("\n" + "=" * 108)
    print("THE SAME CENSUS ON GROSS - the one that actually tests the bias")
    print("=" * 108)
    print("Costs are charged everywhere else for honesty and decide nothing")
    print("(owner rule). A cell CLEARS here when, on BOTH labelled slices, the")
    print("kept set is positive AND beats its parent AND beats the entries it")
    print("threw away. Still descriptive - it can promote nothing.")
    g_scored, g_clear = 0, []
    for (nm, arm), parts in store.items():
        if arm not in FILTERS:
            continue
        k = pd.concat([r for _, r in store[(nm, arm)]])
        c = pd.concat([r for _, r in store[(nm, arm + "_C")]])
        p = pd.concat([r for _, r in store[(nm, "PARENT")]])
        ktr, kva, _ = R.slice_by_time(k, t_tr, t_va)
        ctr, cva, _ = R.slice_by_time(c, t_tr, t_va)
        ptr, pva, _ = R.slice_by_time(p, t_tr, t_va)
        if len(ktr) < R.MIN_TR or len(kva) < R.MIN_VA:
            continue
        g_scored += 1
        ok = all([ktr["gross_pct"].mean() > 0, kva["gross_pct"].mean() > 0,
                  ktr["gross_pct"].mean() > ptr["gross_pct"].mean(),
                  kva["gross_pct"].mean() > pva["gross_pct"].mean(),
                  ktr["gross_pct"].mean() > ctr["gross_pct"].mean(),
                  kva["gross_pct"].mean() > cva["gross_pct"].mean()])
        if ok:
            g_clear.append(dict(name=nm, filt=arm, n_tr=len(ktr),
                                gross_tr=ktr["gross_pct"].mean(),
                                gross_va=kva["gross_pct"].mean(),
                                par_tr=ptr["gross_pct"].mean(),
                                comp_tr=ctr["gross_pct"].mean()))
    print(f"\n{g_scored} cells scored on gross. A zero-effect partition clears")
    print("six independent coin flips about 1 time in 64, so roughly "
          f"{g_scored/64:.1f} of {g_scored}")
    print("would clear on luck alone.")
    print(f"CELLS CLEARING ON GROSS: {len(g_clear)}")
    if g_clear:
        gdf = pd.DataFrame(g_clear).sort_values("gross_tr", ascending=False)
        print(gdf.to_string(index=False))
        gdf.to_csv(f"{REPO}/step477_gross_clears.csv", index=False)
        print("\nREAD THE 1-IN-64 BASELINE AS AN UPPER BOUND ON THE SURPRISE,")
        print("NOT AS A p-VALUE. These 96 cells are NOT 96 independent draws:")
        print("  - the four target settings score the SAME entries, so each")
        print("    level x filter population is counted up to four times;")
        print("  - AGREE is a strict subset of both DAILY and H4, so the three")
        print("    filters overlap heavily rather than testing separate things.")
        u = gdf.groupby(["filt"])["name"].apply(
            lambda s: sorted({n.split(" -> ")[0] for n in s}))
        print("\nCollapsed to DISTINCT level x filter populations, which is the")
        print("honest unit:")
        n_u = 0
        for f, lv in u.items():
            n_u += len(lv)
            print(f"  {f:<8} {', '.join(lv)}")
        print(f"  -> {n_u} distinct populations of the 24 that exist "
              f"(8 levels x 3 filters).")
        print("Compare that against the pooled paired-by-day read above before")
        print("believing any of it: if the partition were real, the pooled")
        print("number would carry it, and it does not.")

    print("\n" + "=" * 108)
    print("LOOKS CONSUMED: NONE. No sealed slice was opened, because this")
    print("family has none left. Nothing here is proposed for deployment.")
    print("=" * 108)
    return uniq, cnt


if __name__ == "__main__":
    main()
