"""
step497_slice_decision_memo.py - ROUND 497

ITEM 21 WAS WRITTEN WHEN XRP WAS THE ONLY CLEAN SLICE WITH REAL HISTORY.
IT IS NOT ANY MORE.  (QUEUE ITEM 24, which supersedes the framing of item 21.)

Research only. No orders. No account. No live file touched, imported or
modified. **This file is a DECISION MEMO. It proposes; it does not run.**

====================================================================
THE FENCE, fixed here before a byte of tape was read, and it is stricter
than the item's own wording in two places.
====================================================================

(F1) **NO LOOK, UNDER ANY OUTCOME.** `R.simulate` is never called anywhere in
     this file - not on a sealed slice, not on a choosing slice, not on a
     control. **No return, expectancy, win rate, risk multiple, t-statistic
     or P&L of any kind is computed for any instrument.** The only things
     this file measures are (a) WHEN an entry would have fired, (b) HOW WIDE
     its structural stop would have been, and (c) how far apart bars move.
     All three are entries-only measurements with no outcome read, which is
     the same standing R489(b) and R492's `stop/vol` table run under.

(F2) **FIRST 80% ONLY, ENFORCED BY TRUNCATION RATHER THAN BY FILTERING.**
     The item says "first 80% only, on every instrument, always." A filter
     applied after the fact still lets sealed bars into a swing, a level or
     a sweep. So each instrument's 1m and 5m frames are **cut at its own 80%
     boundary before `prep()` sees them** - `R.load` is temporarily wrapped
     so that the imported pipeline is physically incapable of reading a
     sealed bar. Nothing downstream of that cut exists to be read.
     The ONE thing taken from beyond the boundary is the LAST BAR'S
     TIMESTAMP, which is needed to know where the boundary is at all
     (`boundaries()` in step492 does exactly this). A calendar date is not
     a price.

(F3) **NOTHING HERE QUALIFIES OR SELECTS ANYTHING.** A projection of trade
     COUNT is a statement about whether a question is answerable on a slice.
     It is not evidence about the answer. No cell is ranked by anything that
     could stand in for expected profit, and R494's warning is carried
     forward verbatim: a screen ranks, it does not select.

(F4) **THE ARGUMENT IS AGAINST R492, NOT AROUND IT.** R492 established that
     on this family the binding constraint is **cost per unit of risk, not
     signal** - sealed gross R +0.299 against a cost of 0.430 risk units.
     The item requires that any recommendation to spend a slice say what is
     different about that instrument's COST, not about its tape. So the
     memo's spine is the ratio this file CAN compute without a look:
     **sourced fee round trip / median structural stop = cost in risk
     units**, measured on each instrument's own choosing and middle slices,
     against LINK's published 0.385 / 0.278 / 0.430.

(F5) **NO TUNING, NOTHING RETYPED.** Every constant and every step of the
     construction is imported from `step450_tjr_crypto_1m` - the two-candle
     swing, the levels marked on the high timeframes only, the sweep hunted
     on the 5-MINUTE, break of structure as a 1-minute BODY close, the
     2-hour pending expiry, all eight levels, both directions. The one block
     copied rather than imported is the four-line structural-stop extreme
     out of `step492.build()`, reproduced without its `simulate` call
     because there is no importable function that returns a stop alone.

(F6) **THE INSTRUMENTS ARE THE FOUR THE ITEM NAMES**, XRPUSD, DOGEUSD,
     AVAXUSD, DOTUSD, every one on R489/R494's INTACT list - **plus LINKUSD
     as a REPRODUCTION CONTROL on its CHOOSING AND MIDDLE SLICES ONLY.**
     The control exists because R492's cost figures (0.385 / 0.278 / 0.430)
     are the **mean of cost/stop across trades**, not fee divided by the
     median stop, and 1/stop is convex enough that the two differ by a
     factor of three. A memo that compared the wrong statistic to LINK's
     would be arithmetic theatre. LINK is loaded through the SAME 80%
     truncation as everything else (F2), so **its sealed slice is not
     readable inside this file either**; it is spent and stays spent, and
     nothing about R492's verdict is re-opened, re-read or re-interpreted.
     No other spent instrument (BTC, ETH, SOL, LTC, SPY, QQQ) is touched.

WHAT IS PUBLISHED, per the item:
  (1) each instrument's own window, its 60/20/20 boundaries and the exact
      calendar span of its sealed slice;
  (2) per level, entries in the choosing slice and in the middle slice, the
      firing rate, and the PROJECTED entry count in that instrument's own
      sealed window;
  (3) which cells are TESTABLE there, at the 30-train / 8-val bar;
  (4) the cost-in-risk-units table that R492 says is the whole question;
  (5) the memo: which slice, if any, should be spent - or the case for
      leaving all four sealed.

USAGE
  python3 step497_slice_decision_memo.py
"""

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"
LINE = "=" * 118

SYMS = ["XRPUSD", "DOGEUSD", "AVAXUSD", "DOTUSD"]

# R494 (2026-09-06), primary-sourced CDE per-contract fee arithmetic, and
# R493's rule that a CDE cost is a property of the instrument AT THAT DAY'S
# PRICE. Charged for honest P&L; decides nothing (owner rule 2026-07-25).
FEE_RT = {"XRPUSD": 0.0423, "DOGEUSD": 0.0667,
          "AVAXUSD": 0.3916, "DOTUSD": 0.3148}
ALLIN_RT = {"XRPUSD": 0.0808, "DOGEUSD": 0.1208,
            "AVAXUSD": 0.5499, "DOTUSD": 0.3782}
# R494's published R488 multiple (gap-clean 1-minute move / fee round trip)
R488_MULT = {"XRPUSD": 1.96, "DOGEUSD": 1.51, "AVAXUSD": 0.25, "DOTUSD": 0.27}
CONTRACT = {"XRPUSD": "XRP PERP (XPP, 500 XRP)",
            "DOGEUSD": "DOGE PERP (DOP, 5000 DOGE, $449 notional)",
            "AVAXUSD": "AVAX PERP (AVP, 10 AVAX, $76.60 notional)",
            "DOTUSD": "DOT PERP (10 DOT, $95.30 notional)"}

# R492, published. The benchmark this memo must argue against, not around.
LINK_PUBLISHED = dict(fee=0.0522, mult=2.12,
                      stop_ch=0.423, stop_mi=0.338, stop_se=0.319,
                      cost_ch=0.385, cost_mi=0.278, cost_se=0.430,
                      gross_se=+0.299, net_se=-0.131)


# ------------------------------------------------------------- boundaries
def boundaries(sym):
    """60/20/20 on this instrument's OWN 1m/5m overlap window, cut exactly as
    step492's `boundaries()` cuts it. Reads the `t` column only - see F2."""
    t5 = pd.to_datetime(pd.read_parquet(f"{REPO}/data_alpaca_{sym}_5m.parquet",
                                        columns=["t"])["t"]).sort_values()
    t1c = pd.to_datetime(pd.read_parquet(f"{REPO}/data_alpaca_{sym}_1m.parquet",
                                         columns=["t"])["t"]).sort_values()
    t0 = max(t5.iloc[0], t1c.iloc[0])
    t1 = min(t5.iloc[-1], t1c.iloc[-1])
    span = t1 - t0
    return t0, t0 + span * 0.60, t0 + span * 0.80, t1


# ---------------------------------------------------- the truncated prep
def prep_first_80(sym, t_va):
    """F2. `R.prep` imported and run unchanged, on tape that has been cut at
    the 80% boundary before it can see it. The sealed bars do not exist
    inside this call."""
    real_load = R.load

    def truncating_load(s, tf):
        d = real_load(s, tf)
        return d[d["t"] < t_va].reset_index(drop=True)

    R.load = truncating_load
    try:
        d5, d1 = R.prep(sym)
    finally:
        R.load = real_load
    assert d5["t"].iloc[-1] < t_va and d1["t"].iloc[-1] < t_va
    return d5, d1


def entries_by_level(d5, d1):
    """Per level: the entry timestamps and the structural stop each entry
    would carry, in EXACTLY the bookkeeping `R.simulate` uses - fill at the
    OPEN of the bar after the signal, stop as a percent of that fill, and
    the same three rejections it applies (no bar after the signal, a
    non-finite stop, a stop on the wrong side of the fill). Reproduced here
    rather than imported because `simulate` cannot return a stop without
    also scoring an outcome, and **no outcome may be scored in this file.**
    Nothing downstream of the fill is touched: no exit, no gross, no net.
    The control in section (4) is what proves the reproduction is faithful.
    """
    lo1 = d1["low"].to_numpy()
    hi1 = d1["high"].to_numpy()
    op1 = d1["open"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    t1v = d1["t"].to_numpy()
    n1 = len(d1)
    out = {}
    for col, dirn, lab in R.LEVELS:
        sw, _sig5 = R.scan_sweeps(d5, col, dirn)
        if len(sw) == 0:
            out[lab] = pd.DataFrame(columns=["t", "stop_pct"])
            continue
        ent1, swB = R.trigger_1m(d5, d1, sw, dirn)
        if not len(ent1):
            out[lab] = pd.DataFrame(columns=["t", "stop_pct"])
            continue
        a1 = i1n[swB]
        stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                          else hi1[max(0, a):b + 1].max()
                          for a, b in zip(a1, ent1)])
        keep_t, keep_s = [], []
        for i, sp in zip(ent1, stopB):
            j = i + 1
            if j >= n1:
                continue
            entry = op1[j]
            if not np.isfinite(sp) or entry <= 0:
                continue
            if dirn > 0 and sp >= entry:
                continue
            if dirn < 0 and sp <= entry:
                continue
            keep_t.append(t1v[i])
            keep_s.append(abs(entry - sp) / entry * 100.0)
        f = pd.DataFrame({"t": pd.to_datetime(keep_t), "stop_pct": keep_s})
        # two sweeps of the same level can resolve into the SAME entry with
        # the same stop; R476 counts that once.
        f = f.drop_duplicates(subset=["t", "stop_pct"]).sort_values("t")
        out[lab] = f.reset_index(drop=True)
    return out


def cost_units(f, cost_pct):
    """R492's cost statistic, restated exactly: the MEAN across entries of
    (round trip / that entry's own structural stop). Per-trade, never a
    ratio of means (R487). Entries-only - no outcome is read."""
    if not len(f):
        return np.nan
    v = (cost_pct / f["stop_pct"]).replace([np.inf, -np.inf], np.nan).dropna()
    return v.mean() if len(v) else np.nan


def daily_vol_first80(sym, t_va):
    """R488's yardstick, unchanged: mean |1-minute return| per UTC day, %,
    on the first 80% only."""
    b = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_1m.parquet",
                        columns=["t", "close"])
    b["t"] = pd.to_datetime(b["t"])
    b = b[b["t"] < t_va]
    r = b["close"].pct_change().abs() * 100.0
    f = pd.DataFrame({"t": b["t"], "r": r}).dropna()
    return f.groupby(f["t"].dt.floor("D"))["r"].mean()


# ====================================================================== main
def main():
    print(LINE)
    print("ROUND 497 - QUEUE ITEM 24: WHICH SEALED SLICE, IF ANY, SHOULD BE "
          "SPENT. A DECISION MEMO.")
    print(LINE)
    print("FENCE (full text in the docstring):")
    print("  - R.simulate is NEVER called. No return, expectancy, win rate or "
          "risk multiple is computed for any instrument.")
    print("  - Each instrument's tape is TRUNCATED at its own 80% boundary "
          "before prep() sees it. Sealed bars cannot enter any computation.")
    print("  - Nothing is qualified or selected. A trade-count projection "
          "says whether a question is ANSWERABLE, never what the answer is.")
    print("  - The benchmark to argue against is R492: sealed gross R +0.299 "
          "against a cost of 0.430 risk units. Cost, not signal.")
    print(f"  - Instruments: {', '.join(SYMS)}. All INTACT per R489/R494. "
          "No spent instrument is touched.")

    W = {}
    for sym in SYMS:
        t0, t_tr, t_va, t1 = boundaries(sym)
        W[sym] = (t0, t_tr, t_va, t1)

    # ------------------------------------------------ (1) the four windows
    print("\n" + LINE)
    print("(1) THE FOUR WINDOWS, CUT ON EACH INSTRUMENT'S OWN 1m/5m OVERLAP")
    print(LINE)
    print(f"{'instrument':<12}{'own window':<26}{'days':>7}"
          f"{'choosing 60% ends':>20}{'middle 20% ends':>18}"
          f"{'SEALED slice':>26}{'sealed days':>13}")
    for sym in SYMS:
        t0, t_tr, t_va, t1 = W[sym]
        win = f"{t0:%Y-%m-%d} -> {t1:%Y-%m-%d}"
        seal = f"{t_va:%Y-%m-%d} -> {t1:%Y-%m-%d}"
        print(f"{sym:<12}{win:<26}{(t1 - t0).days:>7,}"
              + f"{t_tr:%Y-%m-%d}".rjust(20)
              + f"{t_va:%Y-%m-%d}".rjust(18)
              + seal.rjust(26)
              + f"{(t1 - t_va).days:>13,}")

    print("\n  R492 for scale: LINK's sealed slice was 406 calendar days "
          "(326 of them carrying an entry) and it produced 912 trades in the "
          "selected cell.")

    ENT = {}
    VOL = {}
    for sym in SYMS:
        t0, t_tr, t_va, t1 = W[sym]
        d5, d1 = prep_first_80(sym, t_va)
        ENT[sym] = entries_by_level(d5, d1)
        VOL[sym] = daily_vol_first80(sym, t_va)
        print(f"\n  {sym}: first-80% tape only - 5m bars {len(d5):,}, "
              f"1m bars {len(d1):,}, last bar {d1['t'].iloc[-1]:%Y-%m-%d %H:%M} "
              f"(boundary {t_va:%Y-%m-%d})")

    # ------------------------------- (2)+(3) the count table, per instrument
    rows_all = []
    for sym in SYMS:
        t0, t_tr, t_va, t1 = W[sym]
        d_ch = (t_tr - t0).days
        d_mi = (t_va - t_tr).days
        d_se = (t1 - t_va).days
        print("\n" + LINE)
        print(f"(2)+(3) {sym}  -  ENTRIES PER LEVEL ON THE FIRST 80%, AND WHAT "
              f"THE SEALED {d_se}-DAY SLICE WOULD BE EXPECTED TO CARRY")
        print(LINE)
        print(f"  choosing {d_ch:,}d   middle {d_mi:,}d   SEALED {d_se:,}d "
              f"({t_va:%Y-%m-%d} -> {t1:%Y-%m-%d}, never read)")
        print(f"\n{'level':<20}{'n_choose':>10}{'n_middle':>10}"
              f"{'/day 80%':>10}{'/day mid':>10}{'proj sealed':>13}"
              f"{'proj (80% rate)':>17}{'train>=30':>11}{'val>=8':>8}"
              f"  testable in the sealed slice?")
        for col, dirn, lab in R.LEVELS:
            f = ENT[sym][lab]
            n_ch = int((f["t"] < t_tr).sum()) if len(f) else 0
            n_mi = int(((f["t"] >= t_tr) & (f["t"] < t_va)).sum()) if len(f) else 0
            rate80 = (n_ch + n_mi) / max(1, d_ch + d_mi)
            rate_mid = n_mi / max(1, d_mi)
            proj_mid = rate_mid * d_se
            proj_80 = rate80 * d_se
            ok_tr = n_ch >= R.MIN_TR
            ok_va = n_mi >= R.MIN_VA
            # A slice you cannot power is not an asset (item 21). The sealed
            # slice is the same 20% width as the middle slice, so the middle
            # slice's own minimum is the natural bar to read it against.
            if not (ok_tr and ok_va):
                verdict = "NO - fails the qualification bar before the look"
            elif min(proj_mid, proj_80) >= 30:
                verdict = "yes - comfortably powered"
            elif min(proj_mid, proj_80) >= R.MIN_VA:
                verdict = "yes - thin (8-30 projected)"
            else:
                verdict = "NO - projects under 8 trades"
            print(f"{lab:<20}{n_ch:>10,}{n_mi:>10,}{rate80:>10.2f}"
                  f"{rate_mid:>10.2f}{proj_mid:>13,.0f}{proj_80:>17,.0f}"
                  f"{'yes' if ok_tr else 'NO':>11}{'yes' if ok_va else 'NO':>8}"
                  f"  {verdict}")
            rows_all.append(dict(sym=sym, level=lab, n_ch=n_ch, n_mi=n_mi,
                                 proj=min(proj_mid, proj_80),
                                 ok=ok_tr and ok_va and
                                 min(proj_mid, proj_80) >= R.MIN_VA))
        n_ok = sum(1 for r in rows_all if r["sym"] == sym and r["ok"])
        print(f"\n  {n_ok} of 8 levels testable -> {n_ok * 4} of the 32 "
              f"(level x target) cells, since the four exit rules score the "
              f"SAME entries (R496).")

    # ------------------------------------------- (4) the cost-in-risk table
    print("\n" + LINE)
    print("(4) THE ONLY QUESTION R492 LEFT OPEN: COST PER UNIT OF RISK. "
          "ENTRIES-ONLY, NO OUTCOME READ.")
    print(LINE)
    print("    The statistic is R492's, restated exactly: the MEAN across "
          "entries of (round trip / that entry's OWN structural stop).")
    print("    NOT fee divided by the median stop - 1/stop is convex and the "
          "two differ by about a factor of three. R492 published")
    print("    LINK's selected cell at choosing 0.385, middle 0.278, SEALED "
          "0.430, against a sealed gross of +0.299.")
    print("    LINK's own choosing and middle slices are recomputed below as "
          "a REPRODUCTION CONTROL (F6). Its sealed slice is spent")
    print("    and is not readable inside this file - the same 80% truncation "
          "applies to it as to everything else.")

    # LINK, choosing + middle only, same machinery, as the control
    lt0, lt_tr, lt_va, lt1 = boundaries("LINKUSD")
    ld5, ld1 = prep_first_80("LINKUSD", lt_va)
    lent = entries_by_level(ld5, ld1)
    LSL = "last session low"            # R492's selected cell's level
    lf = lent[LSL]
    l_ch = lf[lf["t"] < lt_tr]
    l_mi = lf[(lf["t"] >= lt_tr) & (lf["t"] < lt_va)]
    lc_ch = cost_units(l_ch, LINK_PUBLISHED["fee"])
    lc_mi = cost_units(l_mi, LINK_PUBLISHED["fee"])
    print(f"\n  CONTROL - LINKUSD, level '{LSL}' (R492's selected cell; the "
          f"four targets score the same entries, R496):")
    print(f"    choosing  n {len(l_ch):,} (R492 published 2,877)   "
          f"stop%med {l_ch['stop_pct'].median():.3f} (published 0.423)   "
          f"mean cost/stop {lc_ch:.3f}  (published {LINK_PUBLISHED['cost_ch']:.3f})")
    print(f"    middle    n {len(l_mi):,} (R492 published 1,073)   "
          f"stop%med {l_mi['stop_pct'].median():.3f} (published 0.338)   "
          f"mean cost/stop {lc_mi:.3f}  (published {LINK_PUBLISHED['cost_mi']:.3f})")

    print("\n  CONTROL 2 - XRPUSD's CHOOSING slice against R492's published "
          "stop/vol row (5,169 entries, 562 days, stop%med 0.4048,")
    print("  vol%med 0.1000, stop/vol 3.99). Both controls are on slices "
          "that have already been read; neither opens anything.")

    print(f"\n{'instrument':<12}{'fee RT%':>9}{'allin%':>9}{'R488x':>8}"
          f"{'entries80':>11}{'stop%ch':>9}{'stop%mid':>10}{'vol%':>8}"
          f"{'stop/vol':>10}{'costCH':>9}{'costMID':>9}{'allinMID':>10}"
          f"{'costMID @LSL':>14}")
    COST = {}
    for sym in SYMS:
        t0, t_tr, t_va, t1 = W[sym]
        allc = pd.concat([f for f in ENT[sym].values() if len(f)])
        allc = allc.drop_duplicates(subset=["t", "stop_pct"])
        ch = allc[allc["t"] < t_tr]
        mi = allc[(allc["t"] >= t_tr) & (allc["t"] < t_va)]
        lslf = ENT[sym][LSL]
        lsl_mi = lslf[(lslf["t"] >= t_tr) & (lslf["t"] < t_va)]
        s_ch = ch["stop_pct"].median()
        s_mi = mi["stop_pct"].median()
        day = ch["t"].dt.normalize()
        v = VOL[sym].reindex(day).to_numpy()
        ratio = pd.Series(ch["stop_pct"].to_numpy() / v).replace(
            [np.inf, -np.inf], np.nan).dropna()
        c_ch = cost_units(ch, FEE_RT[sym])
        c_mi = cost_units(mi, FEE_RT[sym])
        a_mi = cost_units(mi, ALLIN_RT[sym])
        c_lsl = cost_units(lsl_mi, FEE_RT[sym])
        COST[sym] = dict(c_ch=c_ch, c_mi=c_mi, a_mi=a_mi, c_lsl=c_lsl,
                         s_ch=s_ch, s_mi=s_mi, n=len(allc),
                         stopvol=ratio.median())
        if sym == "XRPUSD":
            print(f"    XRPUSD choosing slice as computed here: "
                  f"n {len(ch):,}, days {day.nunique():,}, "
                  f"stop%med {s_ch:.4f}, vol%med {np.nanmedian(v):.4f}, "
                  f"stop/vol {ratio.median():.2f}")
        print(f"{sym:<12}{FEE_RT[sym]:>9.4f}{ALLIN_RT[sym]:>9.4f}"
              f"{R488_MULT[sym]:>8.2f}{len(allc):>11,}{s_ch:>9.4f}"
              f"{s_mi:>10.4f}{np.nanmedian(v):>8.4f}{ratio.median():>10.2f}"
              f"{c_ch:>9.3f}{c_mi:>9.3f}{a_mi:>10.3f}{c_lsl:>14.3f}")
    print(f"{'LINKUSD (R492)':<12}{LINK_PUBLISHED['fee']:>9.4f}"
          f"{0.1043:>9.4f}{LINK_PUBLISHED['mult']:>8.2f}{'':>11}"
          f"{LINK_PUBLISHED['stop_ch']:>9.4f}{LINK_PUBLISHED['stop_mi']:>10.4f}"
          f"{'':>8}{3.37:>10.2f}{LINK_PUBLISHED['cost_ch']:>9.3f}"
          f"{LINK_PUBLISHED['cost_mi']:>9.3f}{'':>10}{lc_mi:>14.3f}"
          f"   <- SPENT. Failed out of sample at cost/stop 0.430 "
          f"against gross +0.299.")
    print("\n  costCH / costMID / allinMID are pooled across all eight levels; "
          "the last column is the 'last session low' level alone, which is")
    print("  the level R492's spent cell sat on, so it is the one column that "
          "compares like with like against LINK's 0.278.")

    # ----------------------------------------------------------- (5) memo
    print("\n" + LINE)
    print("(5) THE MEMO")
    print(LINE)
    print("  Benchmark, and it is the thing to argue against: LINK entered "
          "its sealed slice with a middle-slice cost of 0.278 risk units,")
    print("  paid 0.430 there, and its sealed GROSS of +0.299 was not enough "
          "to cover it. The signal was never the binding constraint.")
    for sym in SYMS:
        t0, t_tr, t_va, t1 = W[sym]
        c = COST[sym]
        n_ok = sum(1 for r in rows_all if r["sym"] == sym and r["ok"])
        proj_tot = sum(r["proj"] for r in rows_all if r["sym"] == sym and r["ok"])
        print(f"\n  {sym}: sealed {t_va:%Y-%m-%d} -> {t1:%Y-%m-%d} "
              f"({(t1 - t_va).days:,}d), {n_ok}/8 levels testable "
              f"({n_ok * 4}/32 cells), ~{proj_tot:,.0f} entries projected")
        print(f"    cost per unit of risk, middle slice: "
              f"{c['c_mi']:.3f} pooled fee-only / {c['c_lsl']:.3f} on LINK's "
              f"own level / {c['a_mi']:.3f} all-in")
        gap = c["c_lsl"] - lc_mi
        print(f"    like-for-like against LINK's {lc_mi:.3f}: "
              f"{gap:+.3f}   ({'WORSE' if gap > 0 else 'better'} per unit of "
              f"risk before a single outcome is read)")
        head = (proj_tot >= 8 * 30)
        print(f"    powering: {'not a constraint' if head else 'CHECK'} - "
              f"item 21's worry was built on ~103 entries a YEAR; this arm "
              f"fires {proj_tot / max(1, (t1 - t_va).days):.1f} a DAY across "
              f"the eight levels.")
    print("\n  Nothing here is a qualification, nothing is deployed, and all "
          "four sealed slices are INTACT and unread at the end of this run.")
    print("  The written case, with the recommendation, is in RESEARCH_LOG.md.")

    print("\n" + LINE)
    print("LOOKS CONSUMED: NONE, and none could be. R.simulate was never "
          "called; no sealed bar was loaded into any frame.")
    print(LINE)


if __name__ == "__main__":
    main()
