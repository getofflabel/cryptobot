"""
step475_tjr_confluence_partition.py - ROUND 475

HIS CONTINUATION CONFLUENCES, AS PARTITIONS OF THE POPULATION ROUND 450
ALREADY BUILT.

Research only. No orders. No live file touched. Nothing here is deployed by
this script under any outcome.

QUEUE ITEM 2, VERBATIM
  "R450 tested his ENTRY sequence bare. step432/step436 s1 say the
   continuation confluences are equilibrium and fair value gaps, and nothing
   else - order blocks and breaker blocks are retired and a test fails the
   build if they reappear. Question: does requiring price to be at the
   equilibrium of the sweep leg, or to be filling a fair value gap,
   partition the 1-minute-trigger population into a materially better
   subset?
   A partition, never a re-run (the round-400 lesson): every candidate is
   scored independently, the filtered set must be a strict subset of the
   same entries by timestamp, and the script asserts it. FVG definition is
   fixed by step436 s5 - three candles, low of the third above the high of
   the first, dies on a body close through it, never on a wick. No grid."

WHAT IS FAITHFUL TO HIM
  The parent population is round 450's arm B, unchanged and re-run from the
  same module, so the partition is measured against the exact entries it
  came from. On top of it, ONE thing changes: the entry must also be
  standing on a continuation confluence.

  The confluence is read on the FIVE-MINUTE chart, not the one-minute.
  That is his own instruction, step432 s2 line: "The entry trigger on the
  1-minute: a break of structure or a gap inversion in the direction of the
  5-minute trend, taken at a 5-MINUTE ingredient (gap, midpoint...). Once
  that happens he does not wait for a 1-minute gap or a 1-minute midpoint:
  'I'm not looking for order flow to get respected on the 1-minute
  timeframe.'"

  EQUILIBRIUM (step436 s6, the settled spec): the exact halfway point
  between the MOST RECENT confirmed 5-minute swing low and the MOST RECENT
  confirmed 5-minute swing high. Below it is cheap, above it is expensive.
  A long must be triggering at or below the midpoint; a short at or above.
  He spends five unbroken minutes warning against anchoring to an earlier
  swing, so "most recent" is taken literally and mechanically.

  FAIR VALUE GAP (step436 s5, the settled spec): three consecutive
  5-minute candles; bullish when the LOW of the third is above the HIGH of
  the first, and the box runs between those two prices; bearish mirrored.
  Overlapping wicks means no gap. It DIES on a candle body CLOSING through
  it, never on a wick. A long must be triggering with price inside a live
  BULLISH gap, a short inside a live bearish one.

  EITHER is his own escalation rule (step436 s8): after a bad run he
  promotes the entry bar from a bare sweep plus break of structure up to a
  sweep plus break of structure PLUS an equilibrium level or a fair value
  gap. So the third partition is EQ or FVG, and it is his sentence, not a
  third guess.

  ORDER BLOCKS AND BREAKER BLOCKS ARE NOT BUILT. step436 s1: he says
  verbatim that he stopped using them. A test that reintroduces them fails
  the build. There is no order-block code in this file.

OURS, AND LABELLED
  - The confluence is evaluated at the CLOSE of the 1-minute signal bar,
    using the last 5-minute bar that had already CLOSED at that instant,
    and reading the swing columns one bar staler still (round 450's
    ffill_shift). Strictly causal, deliberately conservative.
  - Everything inherited from round 450 stays as it was: UTC day boundary,
    2-hour pending expiry, 24-hour hold cap, costs charged at 0.50% of
    notional round trip and used for nothing else.

PROTOCOL, FIXED BEFORE THE RUN
  - Same 60/20/20 boundaries as round 450, derived the same way from BTC's
    overlap, so the slices mean the same calendar dates.
  - Floors 30 choosing / 8 middle trades. A partition that thins a cell
    below the floor is reported as thin and cannot qualify.
  - QUALIFY, and this bar is HIGHER than round 450's, deliberately:
      (a) positive NET mean on the choosing AND middle slice, pooled;
      (b) positive on at least 2 of the 3 assets individually;
      (c) beats its OWN PARENT cell's net mean on BOTH slices - a partition
          that does not improve on the population it came from is not a
          better subset, whatever its sign; and
      (d) the complement (the entries the filter throws away) is reported
          beside it, because a filter that keeps the good half must leave a
          worse half behind.
  - Expected-by-chance is printed in the same breath as the survivor count.
  - The crypto 1-minute family's sealed final 20% is still untouched
    (round 450 opened nothing). If and only if a cell clears (a)-(c), ONE
    test look is taken, on the single best cell by choosing-slice net.
  - The sweep-leg equilibrium variant (midpoint of sweep extreme to the
    opposite swing) is reported for completeness because the queue names
    that phrasing, and is BARRED FROM QUALIFYING. Only step436 s6's
    definition can spend a look. Stated here before the run so the better
    of two definitions cannot be picked after seeing them.

THE DATA MOVED UNDER THIS ROUND, AND IT IS RECORDED HERE
  Round 450 ran on 147 days: "the 1-minute history starts 2026-03-01",
  42,386 BTC 5-minute bars and 208,210 1-minute bars. The parquet files now
  hold 2021-01-01 -> 2026-07-26: 578,831 BTC 5-minute bars and 2,597,036
  1-minute bars. The 1-minute crypto history was backfilled after round 450
  ran, and the data files are gitignored so nothing recorded it.

  Two consequences, both handled rather than papered over:
  1. Round 450's honest limit number one - "147 days, one regime" - is
     closed by the data itself. Its arm B is replayed here over 5.5 years.
  2. The extended window's slice boundaries are NOT round 450's. Round
     450's whole 147 days now sit inside the extended window's FINAL 20%,
     so its choosing and middle slices are data this round would be sealing.
     Round 450 opened no look, so no look was burned, but a partition that
     qualified on the extended window would be spending a slice that round
     450 had already read. THEREFORE: the extended-window run is allowed to
     qualify a cell but is NOT allowed to spend the sealed look; only the
     round-450-window run, whose slices are the ones round 450 defined, can.
     Fixed before the run.

  So the round runs TWICE, same partition, same code, no tuning between
  them: once on round 450's own 147-day window, which is the queue item as
  literally written, and once on the full 5.5 years, which is the stronger
  test the new data makes possible.
"""

import io
import contextlib
import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"
FILTERS = ["EQ", "FVG", "EITHER"]


# ------------------------------------------------------- fair value gaps
def five_min_gaps(d5):
    """His three-candle gap on the 5-minute chart (step436 s5).

    Returns arrays over gaps: direction (+1 bullish / -1 bearish), box low,
    box high, the 5-minute index at which the gap is KNOWN (the close of the
    third candle), and the index at which it DIES - the first later bar
    whose BODY CLOSES through it. A wick never kills it.
    """
    h = d5["high"].to_numpy()
    l = d5["low"].to_numpy()
    c = d5["close"].to_numpy()
    n = len(d5)
    g_dir, g_lo, g_hi, g_born = [], [], [], []
    for i in range(2, n):
        if l[i] > h[i - 2]:                 # bullish: no overlap of wicks
            g_dir.append(+1); g_lo.append(h[i - 2]); g_hi.append(l[i])
            g_born.append(i)
        elif h[i] < l[i - 2]:               # bearish
            g_dir.append(-1); g_lo.append(h[i]); g_hi.append(l[i - 2])
            g_born.append(i)
    g_dir = np.array(g_dir, int)
    g_lo = np.array(g_lo, float)
    g_hi = np.array(g_hi, float)
    g_born = np.array(g_born, int)
    g_die = np.full(len(g_born), n, int)
    for k in range(len(g_born)):
        b = g_born[k]
        if g_dir[k] > 0:
            hit = np.flatnonzero(c[b + 1:] < g_lo[k])   # body close BELOW it
        else:
            hit = np.flatnonzero(c[b + 1:] > g_hi[k])   # body close ABOVE it
        if len(hit):
            g_die[k] = b + 1 + hit[0]
    return g_dir, g_lo, g_hi, g_born, g_die


def last_closed_5m(d5, d1, ent1):
    """For each 1-minute signal bar, the index of the last 5-minute bar that
    had already CLOSED at that bar's close. Strictly causal."""
    close5 = (d5["t"] + pd.Timedelta(minutes=5)).to_numpy()
    close1 = (d1["t"].to_numpy()[ent1] + np.timedelta64(1, "m"))
    return np.searchsorted(close5, close1, side="right") - 1


def confluence_flags(d5, d1, ent1, stop_px, dirn, gaps):
    """Per entry: is it standing at his equilibrium, and/or inside a live
    5-minute fair value gap, at the close of the 1-minute trigger bar?"""
    g_dir, g_lo, g_hi, g_born, g_die = gaps
    k5 = last_closed_5m(d5, d1, ent1)
    price = d1["close"].to_numpy()[ent1]
    sh = d5["mr_sh"].to_numpy()
    sl = d5["mr_sl"].to_numpy()

    eq = np.full(len(ent1), False)
    eq_leg = np.full(len(ent1), False)
    fvg = np.full(len(ent1), False)
    for j in range(len(ent1)):
        k = k5[j]
        if k < 0:
            continue
        hi_s, lo_s, p = sh[k], sl[k], price[j]
        # step436 s6 - midpoint of the most recent confirmed swing low and
        # the most recent confirmed swing high. Buy the cheap half.
        if np.isfinite(hi_s) and np.isfinite(lo_s):
            mid = 0.5 * (hi_s + lo_s)
            eq[j] = (p <= mid) if dirn > 0 else (p >= mid)
        # secondary, reported only, BARRED from qualifying: the midpoint of
        # the sweep leg itself - sweep extreme to the opposite swing.
        opp = hi_s if dirn > 0 else lo_s
        if np.isfinite(opp) and np.isfinite(stop_px[j]):
            mid_leg = 0.5 * (opp + stop_px[j])
            eq_leg[j] = (p <= mid_leg) if dirn > 0 else (p >= mid_leg)
        # live gap in the trade's direction, containing price
        if len(g_born):
            live = (g_dir == dirn) & (g_born <= k) & (g_die > k) & \
                   (g_lo <= p) & (p <= g_hi)
            fvg[j] = bool(live.any())
    return {"EQ": eq, "FVG": fvg, "EITHER": eq | fvg, "EQ_LEG": eq_leg}


# ------------------------------------------------------------- the round
def align_mask(ent1, returned, flag):
    """simulate() returns rows in the order it received candidates, skipping
    the ones it could not score. Walk both in order so the mask is POSITIONAL
    - two sweeps that happen to trigger on the same 1-minute bar can never be
    confused for each other."""
    out = np.zeros(len(returned), bool)
    j = 0
    for k, e in enumerate(returned):
        while ent1[j] != e:
            j += 1
        out[k] = flag[j]
        j += 1
    return out


def run_asset(sym, store):
    d5, d1 = R.prep(sym)
    lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    gaps = five_min_gaps(d5)
    counts = []
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
        flags = confluence_flags(d5, d1, ent1, stopB, dirn, gaps)
        counts.append((sym, lab, len(ent1),
                       int(flags["EQ"].sum()), int(flags["FVG"].sum()),
                       int(flags["EITHER"].sum()), int(flags["EQ_LEG"].sum())))
        for rt, rlab in R.TARGETS:
            # ONE simulation of the parent. Every subset below is rows of
            # this same frame, so a filtered set is a strict subset of the
            # same entries by construction, not by hope.
            res = R.simulate(d1, ent1, dirn, stopB, rt, R.MAX_HOLD_MIN)
            nm = f"{lab} -> 1m BOS, {rlab}"
            store.setdefault((nm, "PARENT"), []).append((sym, res))
            if not len(res):
                continue
            returned = res["sig_i"].to_numpy()
            for fk in FILTERS + ["EQ_LEG"]:
                mask = align_mask(ent1, returned, flags[fk])
                sub = res[mask]
                comp = res[~mask]
                assert set(sub["sig_t"]).issubset(set(res["sig_t"])), \
                    "filtered set is not a strict subset of the parent"
                assert len(sub) + len(comp) == len(res), "partition leaks"
                store.setdefault((nm, fk), []).append((sym, sub))
                store.setdefault((nm, fk + "_C"), []).append((sym, comp))
    return d5, d1, counts, len(gaps[0])


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


_ORIG_LOAD = R.load


def _clipped_load(t_start):
    def f(sym, tf):
        d = _ORIG_LOAD(sym, tf)
        if t_start is not None:
            d = d[d["t"] >= t_start].reset_index(drop=True)
        return d
    return f


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def partition_effect(store, t_tr):
    """The finding, stated on GROSS, because the question is whether his
    confluence selects a better subset of his own entries - a question about
    the signal, not about what Alpaca charges to collect it (owner rule).

    Choosing slice only. One row per distinct ENTRY: the four target settings
    score the same entries, so they are not four independent draws.
    """
    print("\n" + "=" * 110)
    print("DOES THE CONFLUENCE SELECT A BETTER SUBSET? - choosing slice, GROSS, "
          "one row per entry")
    print("=" * 110)
    pools = {}
    for (nm, arm), parts in store.items():
        for sym, res in parts:
            if not len(res):
                continue
            tr = res[res.sig_t < t_tr]
            if len(tr):
                pools.setdefault(arm, []).append(tr.assign(sym=sym))
    uniq = {}
    for arm, frames in pools.items():
        allr = pd.concat(frames)
        uniq[arm] = allr.drop_duplicates(subset=["sym", "sig_t", "stop_pct"])
    par = uniq.get("PARENT")
    print(f"{'population':<34}{'entries':>9}{'mean gross':>12}{'t':>8}"
          f"{'median stop':>13}{'lev @1%':>9}")
    rows = [("parent (bare sweep -> 1m BOS)", par)]
    for fk in FILTERS + ["EQ_LEG"]:
        rows.append((f"  kept by {fk}", uniq.get(fk)))
        rows.append((f"  thrown away by {fk}", uniq.get(fk + "_C")))
    for lab, u in rows:
        if u is None or not len(u):
            continue
        t, n = tstat(u["gross_pct"])
        st = u["stop_pct"].median()
        print(f"{lab:<34}{n:>9,}{u['gross_pct'].mean():>11.4f}%{t:>8.2f}"
              f"{st:>12.3f}%{1.0/st if st > 0 else np.nan:>8.1f}x")
    if par is not None and len(par):
        print("\nkept minus thrown away, the only comparison that tests the "
              "partition:")
        for fk in FILTERS + ["EQ_LEG"]:
            k, c = uniq.get(fk), uniq.get(fk + "_C")
            if k is None or c is None or not len(k) or not len(c):
                continue
            diff = k["gross_pct"].mean() - c["gross_pct"].mean()
            se = np.sqrt(k["gross_pct"].var(ddof=1) / len(k) +
                         c["gross_pct"].var(ddof=1) / len(c))
            note = "  (barred from qualifying)" if fk == "EQ_LEG" else ""
            print(f"  {fk:<8} {diff:+.4f}% of price per entry   "
                  f"t = {diff/se if se > 0 else np.nan:>6.2f}   "
                  f"kept {len(k):,} / thrown {len(c):,}{note}")


def main(t_start=None, label="", allow_look=True):
    R.load = _clipped_load(t_start)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        b5 = R.load("BTCUSD", "5m"); b1 = R.load("BTCUSD", "1m")
    t0 = max(b5["t"].iloc[0], b1["t"].iloc[0])
    t1 = min(b5["t"].iloc[-1], b1["t"].iloc[-1])
    span = t1 - t0
    t_tr = t0 + span * 0.60
    t_va = t0 + span * 0.80

    print("\n\n" + "=" * 110)
    print(f"ROUND 475 - HIS CONTINUATION CONFLUENCES AS PARTITIONS OF ROUND 450's"
          f"   [{label}]")
    print("=" * 110)
    print(f"window {t0:%Y-%m-%d} -> {t1:%Y-%m-%d} UTC ({span.days} days)")
    print(f"choosing -> {t_tr:%Y-%m-%d %H:%M},  middle -> {t_va:%Y-%m-%d %H:%M},"
          f"  sealed {t_va:%Y-%m-%d} -> {t1:%Y-%m-%d}")
    print(f"sealed look permitted from this window: {'YES' if allow_look else 'NO'}")
    print("parent population = round 450 arm B (1-minute trigger), unchanged.")
    print("confluences read on the FIVE-minute chart (step432 s2), evaluated at")
    print("the close of the 1-minute trigger bar. Order blocks and breaker")
    print("blocks are NOT built (step436 s1 - he retired them).")
    print(f"cost {R.COST_RT}% of notional round trip, charged for honesty and")
    print("used to decide nothing (owner rule 2026-07-25).")

    store = {}
    all_counts = []
    for sym in R.PRIMARY:
        d5, d1, counts, n_gaps = run_asset(sym, store)
        all_counts += counts
        print(f"  {sym}: 5m {len(d5):,} bars, 1m {len(d1):,} bars, "
              f"{n_gaps:,} five-minute gaps found")

    # ------------------------------------------------ how much it removes
    cnt = pd.DataFrame(all_counts, columns=["sym", "level", "entries",
                                            "EQ", "FVG", "EITHER", "EQ_LEG"])
    tot = cnt[["entries", "EQ", "FVG", "EITHER", "EQ_LEG"]].sum()
    print("\n" + "-" * 110)
    print("WHAT THE CONFLUENCE REQUIREMENT ACTUALLY REMOVES (all entries, all slices)")
    print("-" * 110)
    print(f"{'partition':<36}{'entries kept':>14}{'share of parent':>18}")
    print(f"{'parent (bare sweep -> 1m BOS)':<36}{int(tot['entries']):>14,}"
          f"{'100.0%':>18}")
    for k in ["EQ", "FVG", "EITHER", "EQ_LEG"]:
        lab = k if k != "EQ_LEG" else "EQ_LEG (reported only, barred)"
        print(f"{lab:<36}{int(tot[k]):>14,}"
              f"{100.0*tot[k]/tot['entries']:>17.1f}%")
    print("\nHis own check (step436 s11): he trades a third to two thirds of days.")
    print("A partition that keeps nearly everything has not filtered anything.")

    # ------------------------------------------------------- pooled reads
    parent = pooled_table(store, t_tr, t_va, "PARENT").set_index("name")
    frames = {"PARENT": parent}
    for fk in FILTERS + ["EQ_LEG"]:
        frames[fk] = pooled_table(store, t_tr, t_va, fk).set_index("name")
        frames[fk + "_C"] = pooled_table(store, t_tr, t_va, fk + "_C").set_index("name")

    print("\n" + "=" * 110)
    print("EACH CELL, PARENT vs PARTITION vs COMPLEMENT  (net %, pooled BTC+ETH+SOL)")
    print("=" * 110)
    print(f"{'cell':<40}{'filter':>8}{'n_tr':>6}{'netTR':>9}{'netVA':>9}"
          f"{'parTR':>9}{'parVA':>9}{'compTR':>9}{'stop%':>8}{'lev':>7}")
    survivors = []
    for nm in parent.index:
        p = parent.loc[nm]
        if p["verdict"] == "thin":
            continue
        for fk in FILTERS + ["EQ_LEG"]:
            f = frames[fk]
            c = frames[fk + "_C"]
            if nm not in f.index:
                continue
            r = f.loc[nm]
            if r["verdict"] == "thin":
                print(f"{nm:<40}{fk:>8}{int(r['n_tr']):>6}"
                      f"{'':>9}{'':>9}{'':>9}{'':>9}{'':>9}"
                      f"{'':>8}{'  thin':>7}")
                continue
            ctr = c.loc[nm]["mean_tr"] if nm in c.index else np.nan
            print(f"{nm:<40}{fk:>8}{int(r['n_tr']):>6}"
                  f"{r['mean_tr']:>9.4f}{r['mean_va']:>9.4f}"
                  f"{p['mean_tr']:>9.4f}{p['mean_va']:>9.4f}"
                  f"{ctr:>9.4f}{r['stop_tr']:>8.3f}{r['lev']:>6.1f}x")
            beats = (r["mean_tr"] > p["mean_tr"]) and (r["mean_va"] > p["mean_va"])
            if (r["verdict"] == "qualifies" and r["n_assets_pos"] >= 2
                    and beats and fk != "EQ_LEG"):
                survivors.append(dict(name=nm, filt=fk, n_tr=int(r["n_tr"]),
                                      n_va=int(r["n_va"]),
                                      net_tr=r["mean_tr"], net_va=r["mean_va"],
                                      gross_tr=r["gross_tr"],
                                      par_tr=p["mean_tr"], par_va=p["mean_va"],
                                      comp_tr=ctr, stop=r["stop_tr"],
                                      lev=r["lev"], assets=r["n_assets_pos"]))

    # ------------------------------------------------------------ verdict
    scored = sum(1 for nm in parent.index if parent.loc[nm]["verdict"] != "thin"
                 for fk in FILTERS if nm in frames[fk].index
                 and frames[fk].loc[nm]["verdict"] != "thin")
    print("\n" + "=" * 110)
    print("VERDICT")
    print("=" * 110)
    print(f"{scored} partition cells scored (the three qualifying filters over the")
    print("round-450 arm-B cells thick enough to score).")
    print(f"EXPECTED BY CHANCE with no partition effect at all: a symmetric")
    print(f"zero-mean cell passes both slices about 1 time in 4, and beats its")
    print(f"parent on both slices about 1 time in 4 again, so roughly")
    print(f"{scored/16:.1f} of {scored} would clear the full bar on luck alone.")
    print(f"\nCELLS CLEARING THE FULL BAR: {len(survivors)}")
    if survivors:
        s = pd.DataFrame(survivors).sort_values("net_tr", ascending=False)
        print(s.to_string(index=False))
        s.to_csv(f"{REPO}/step475_survivors_{label}.csv", index=False)
    else:
        print("None. The final 20% of this window stays SEALED.")

    partition_effect(store, t_tr)

    pd.concat([frames[k].assign(filt=k) for k in frames]).to_csv(
        f"{REPO}/step475_table_{label}.csv")
    R.load = _ORIG_LOAD
    return survivors, frames, store, t_tr, t_va, t1


def test_look(survivors, store, t_tr, t_va):
    """ONE look, on the single best qualifying cell, and only if one exists."""
    if not survivors:
        return
    best = sorted(survivors, key=lambda r: -r["net_tr"])[0]
    nm, fk = best["name"], best["filt"]
    parts = store[(nm, fk)]
    allr = pd.concat([r for _, r in parts])
    tr, va, te = R.slice_by_time(allr, t_tr, t_va)
    print("\n" + "=" * 110)
    print(f"SEALED SLICE - ONE LOOK, TAKEN ON: {nm}   filter {fk}")
    print("=" * 110)
    if len(te) < R.MIN_VA:
        print(f"only {len(te)} trades in the sealed slice - too thin to read. "
              f"The look is recorded as CONSUMED regardless.")
        return
    print(f"trades {len(te)}   gross {te['gross_pct'].mean():+.4f}%   "
          f"net {te['net_pct'].mean():+.4f}%   net R {te['net_R'].mean():+.3f}   "
          f"win {100*(te['net_pct']>0).mean():.1f}%")
    for sym, r in parts:
        _, _, t_ = R.slice_by_time(r, t_tr, t_va)
        if len(t_):
            print(f"   {sym:<8} n {len(t_):>4}   gross {t_['gross_pct'].mean():+.4f}%"
                  f"   net {t_['net_pct'].mean():+.4f}%")
    print("\nONE LOOK CONSUMED. The crypto 1-minute sweep-to-BOS family's final")
    print("20% is now spent and must never be re-opened for this family.")


if __name__ == "__main__":
    # RUN 1 - the queue item as literally written: round 450's own window,
    # round 450's own slices. This is the only run permitted to spend the
    # sealed look, because these are the boundaries round 450 defined.
    s1, _, st1, tr1, va1, _ = main(t_start=pd.Timestamp("2026-03-01"),
                                   label="r450window", allow_look=True)
    # RUN 2 - the same partition on everything the backfill now gives us.
    # Barred from spending a look: round 450 has already read inside this
    # window's sealed 20%.
    s2, _, st2, tr2, va2, _ = main(t_start=None, label="full",
                                   allow_look=False)

    print("\n\n" + "=" * 110)
    print("SEALED SLICE")
    print("=" * 110)
    if s1:
        test_look(s1, st1, tr1, va1)
    else:
        print("Nothing qualified on round 450's window, which is the only")
        print("window allowed to spend a look. NO LOOK CONSUMED - the crypto")
        print("1-minute sweep-to-BOS family's final 20% is still sealed.")
    if s2:
        print(f"\n{len(s2)} cell(s) cleared the bar on the FULL 5.5-year window.")
        print("No look is taken on them: round 450 already read data inside")
        print("that window's sealed 20%, so it is not a clean out-of-sample")
        print("slice. Recorded, not spent.")
