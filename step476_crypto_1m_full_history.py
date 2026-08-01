"""
step476_crypto_1m_full_history.py - ROUND 476

THE CRYPTO 1-MINUTE ARM, RE-RUN ON THE BACKFILLED 2021-2026 HISTORY.

Research only. No orders. No live file touched. Nothing here is deployed by
this script under any outcome.

READ THIS BEFORE THE NUMBERS: THIS ROUND CANNOT QUALIFY ANYTHING
  Both sealed windows this family had are gone. R474 spent SPY/QQQ's; R475
  spent crypto's. The backfilled 2021-2026 crypto window has boundaries that
  R450 and R475 have both already read inside, so there is no clean
  out-of-sample slice left anywhere on the sweep-to-break-of-structure
  family. THEREFORE this round produces a DESCRIPTION, not a qualification.
  It opens no look, it proposes no deployment, and no number in it may be
  treated as out-of-sample evidence. A candidate off this family needs a NEW
  instrument or NEW data. Fixed before the run, and it is why the script has
  no qualification block and no sealed-slice block at all.

QUEUE ITEM 2, VERBATIM
  "R450 ran on 147 days because that was all the 1-minute data there was.
   The parquet files now hold 2021-01-01 -> 2026-07-26 - 2.6M BTC 1-minute
   bars against R450's 208k. R475 replayed the bare parent over that window
   as a side effect and got +0.1769% of price per entry over 42,354 entries,
   t = 15.33, against R450's +0.0551% at t = 2.63. Three times the effect,
   six times the t, fourteen times the sample.
   What is owed: the t clustered BY DAY (R474 showed clustering roughly
   halves a t of this shape), the year-by-year read that R450 could not do,
   and the arm-A/arm-B/random-control comparison redone at this sample size."

  Three deliverables, and this file does exactly those three. No new
  construction, no grid, no tuning. The machinery is round 450's module
  imported unchanged - same swings, same sweep scan, same 1-minute trigger,
  same structural stop, same costs, same 2-hour pending expiry and 24-hour
  hold cap.

WHAT IS FAITHFUL TO HIM, AND WHAT IS OURS
  Everything inherited from round 450, unchanged, because this is the same
  population measured properly rather than a new hypothesis:
    faithful: the two-candle swing; levels marked on the high timeframes
      only; a level traded through is not a sweep until price reacts and the
      reaction IS the break of structure; break of structure is a BODY
      close; the sweep is hunted on the 5-minute and the entry triggers on
      the 1-minute; the stop is chart structure (the extreme traded between
      the sweep and the entry), never a swept percentage, so leverage is an
      OUTPUT.
    ours: the UTC midnight day boundary (the live desk's decision, and on a
      24/7 market nothing decides it for us); the 2-hour pending expiry; the
      24-hour hold cap; sessions read on the New York clock.

  ONE thing is new here and it is a measurement choice, not a strategy
  choice, and it is OURS: the clustering unit. Crypto has no trading day, so
  the cluster is the UTC calendar day - the same boundary the live desk cuts
  on. Every entry on BTC, ETH and SOL inside one UTC day collapses to one
  observation, because three coins on the same day are one draw of the
  market, not three. That is the most conservative reading available and it
  is the one quoted.

COSTS
  Charged so the P&L is honest and used for NOTHING else (owner rule,
  2026-07-25). 0.50% of notional round trip, Alpaca crypto taker a side.
  Gross sits beside every net number so the venue can be separated from the
  method. Costs decline nothing here.

USAGE
  python3 step476_crypto_1m_full_history.py
"""

import io
import contextlib
import sys

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"


# --------------------------------------------------------------- helpers
def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def utc_day(res):
    """OURS: the live desk's UTC midnight boundary. Crypto has no session."""
    return pd.to_datetime(res["sig_t"]).dt.normalize()


def clustered(res, col="gross_pct"):
    """One mean per UTC day pooled across every asset, then t across days.
    Overlapping entries inside a day - and the three coins moving together
    inside that day - are ONE observation, not thirty."""
    d = res.assign(day=utc_day(res)).groupby("day")[col].mean()
    return tstat(d)


def mean_R(res, col="gross_pct"):
    if col == "net_R":
        return res["net_R"].replace([np.inf, -np.inf], np.nan).mean()
    return (res[col] / res["stop_pct"]).replace(
        [np.inf, -np.inf], np.nan).mean()


def dedupe(res):
    """The four target settings score the SAME entries, so a pooled frame
    holds each entry four times. Collapse to one row per distinct entry."""
    return res.drop_duplicates(subset=["sig_i", "sig_t", "stop_pct"])


# ------------------------------------------------------- random control
def control_trades(d5, every=60):
    """Round 450's chance control, unchanged in construction, returned as
    RAW TRADES instead of a summary so it can be clustered and paired like
    the two arms. Same machinery entered at an arbitrary eligible moment:
    every 60th 5-minute bar, stop at the most recent confirmed swing, both
    directions. Hold-24h only, which is the style the arms are compared on.
    """
    out = []
    for dirn in (+1, -1):
        idx = np.arange(0, len(d5) - 1, every)
        stop = (d5["mr_sl"].to_numpy() if dirn > 0
                else d5["mr_sh"].to_numpy())[idx]
        out.append(R.simulate(d5, idx, dirn, stop, None, R.MAX_HOLD_MIN // 5))
    return pd.concat(out)


# ------------------------------------------------------------- the round
def main():
    print("=" * 104)
    print("ROUND 476 - THE CRYPTO 1-MINUTE ARM ON THE FULL 2021-2026 HISTORY")
    print("=" * 104)
    print("THIS ROUND CANNOT QUALIFY ANYTHING. Both sealed windows on this")
    print("family are spent (R474 SPY/QQQ, R475 crypto) and the backfilled")
    print("window has boundaries R450 and R475 have both already read inside.")
    print("No look is opened here. Nothing below is out-of-sample evidence.")
    print("It is a DESCRIPTION of a population the desk has already seen.")

    # the shared clock, derived exactly as round 450 derived it, so the
    # slice labels on the year table mean what they meant there.
    b5 = R.load("BTCUSD", "5m")
    b1 = R.load("BTCUSD", "1m")
    t0 = max(b5["t"].iloc[0], b1["t"].iloc[0])
    t1 = min(b5["t"].iloc[-1], b1["t"].iloc[-1])
    span = t1 - t0
    t_tr = t0 + span * 0.60
    t_va = t0 + span * 0.80
    print(f"\nwindow {t0:%Y-%m-%d} -> {t1:%Y-%m-%d} UTC  ({span.days} days)")
    print(f"  R450 ran on 147 days of this same tape, at the very end of it.")
    print(f"  slice labels below, for continuity only: choosing < {t_tr:%Y-%m-%d}"
          f", middle < {t_va:%Y-%m-%d}, then the rest.")
    print(f"cost charged {R.COST_RT}% of notional round trip, for honesty only.")
    del b5, b1

    store = {}
    per_asset_rows = {}
    controls = {}
    for sym in R.PRIMARY:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            d5, d1, rows = R.run_asset(sym, t_tr, t_va, store)
            controls[sym] = control_trades(d5)
        per_asset_rows[sym] = rows
        print(f"  {sym}: {len(d5):,} 5-minute bars, {len(d1):,} 1-minute bars, "
              f"{d5['t'].iloc[0]:%Y-%m-%d} -> {d5['t'].iloc[-1]:%Y-%m-%d}")
        sys.stdout.flush()

    # ---------------------------------------------- collapse to entries
    # dedupe PER ASSET first: two coins can share a timestamp, and a pooled
    # drop_duplicates would silently delete one of them.
    arms = {"A": [], "B": []}
    for (nm, arm), parts in store.items():
        for sym, res in parts:
            if not len(res):
                continue
            arms[arm].append(res.assign(sym=sym))
    uniq = {}
    for arm, frames in arms.items():
        allf = pd.concat(frames)
        uniq[arm] = pd.concat([dedupe(g) for _, g in allf.groupby("sym")])
    ctl = pd.concat([c.assign(sym=s) for s, c in controls.items()])

    # ------------------------------- deliverable 3: A vs B vs the control
    print("\n" + "=" * 104)
    print("DELIVERABLE 3 - ARM A vs ARM B vs RANDOM CONTROL, AT THE NEW SAMPLE")
    print("=" * 104)
    print("Whole window. One row per distinct entry (the four target settings")
    print("score the same entries and are collapsed). t by day pools BTC, ETH")
    print("and SOL into ONE observation per UTC day - the conservative read.")
    print(f"\n{'construction':<42}{'entries':>9}{'days':>7}{'gross%':>9}"
          f"{'t naive':>9}{'t by day':>10}{'grossR':>9}{'netR':>8}"
          f"{'stop%':>8}{'lev@1%':>8}")
    table = []
    for key, lab, frame in (
            ("A", "5-minute trigger (R370's construction)", uniq["A"]),
            ("B", "1-MINUTE trigger (HIS construction)", uniq["B"]),
            ("CTL", "RANDOM entry, same stop machinery", ctl)):
        tn, n = tstat(frame["gross_pct"])
        tc, nd = clustered(frame)
        st = frame["stop_pct"].median()
        print(f"{lab:<42}{n:>9,}{nd:>7,}{frame['gross_pct'].mean():>8.4f}%"
              f"{tn:>9.2f}{tc:>10.2f}{mean_R(frame):>9.3f}"
              f"{mean_R(frame, 'net_R'):>8.3f}{st:>7.3f}%{1/st:>7.1f}x")
        table.append(dict(construction=lab, key=key, entries=n, days=nd,
                          gross=frame["gross_pct"].mean(), t_naive=tn,
                          t_by_day=tc, grossR=mean_R(frame),
                          netR=mean_R(frame, "net_R"), stop_median=st))
    pd.DataFrame(table).to_csv(f"{REPO}/step476_arms.csv", index=False)

    print("\nR475 quoted +0.1769% at t = 15.33 on 42,354 entries for arm B.")
    print("The t by day above is the number that should replace it: R474")
    print("found day-clustering roughly halves a t of this shape on the index.")

    # ------------------------------- deliverable 1: the paired differences
    print("\nTHE DIFFERENCES, PAIRED ON SHARED UTC DAYS (the numbers to quote):")
    db = uniq["B"].assign(day=utc_day(uniq["B"])).groupby("day")["gross_pct"].mean()
    for lab, other in (("1-minute trigger minus 5-minute trigger", uniq["A"]),
                       ("1-minute trigger minus RANDOM entry    ", ctl),
                       ("5-minute trigger minus RANDOM entry    ", None)):
        base = db
        if other is None:
            base = uniq["A"].assign(day=utc_day(uniq["A"])).groupby(
                "day")["gross_pct"].mean()
            other = ctl
        do = other.assign(day=utc_day(other)).groupby("day")["gross_pct"].mean()
        j = pd.concat([base.rename("b"), do.rename("o")], axis=1).dropna()
        d_ = j["b"] - j["o"]
        t_, nd_ = tstat(d_)
        print(f"  {lab}: {d_.mean():+.4f}% of price per day, "
              f"t = {t_:.2f} over {nd_:,} shared days")

    # -------------------------------------- deliverable 2: year by year
    print("\n" + "=" * 104)
    print("DELIVERABLE 2 - ONE REGIME OR SIX YEARS? THE YEAR-BY-YEAR READ")
    print("=" * 104)
    print("R450 could not ask this: it held 147 days. Slice labels are")
    print("round 450's boundaries, carried for continuity only - no slice")
    print("here is sealed and none is being spent.")
    print(f"\n{'year':<6}{'slice':<10}{'1m entries':>11}{'days':>6}"
          f"{'1m gross':>10}{'t by day':>10}{'1m grossR':>10}{'1m netR':>9}"
          f"{'5m gross':>10}{'ctl gross':>10}")
    yb = uniq["B"].assign(y=pd.to_datetime(uniq["B"]["sig_t"]).dt.year)
    ya = uniq["A"].assign(y=pd.to_datetime(uniq["A"]["sig_t"]).dt.year)
    yc = ctl.assign(y=pd.to_datetime(ctl["sig_t"]).dt.year)
    year_rows = []
    for y, g in yb.groupby("y"):
        which = ("choosing" if g["sig_t"].max() < t_tr
                 else "middle" if g["sig_t"].max() < t_va else "late")
        ga = ya[ya.y == y]
        gc = yc[yc.y == y]
        tc, nd = clustered(g)
        row = dict(year=int(y), slice=which, entries=len(g), days=nd,
                   gross_1m=g["gross_pct"].mean(), t_by_day=tc,
                   grossR_1m=mean_R(g), netR_1m=mean_R(g, "net_R"),
                   gross_5m=ga["gross_pct"].mean() if len(ga) else np.nan,
                   gross_ctl=gc["gross_pct"].mean() if len(gc) else np.nan)
        year_rows.append(row)
        print(f"{row['year']:<6}{which:<10}{row['entries']:>11,}{nd:>6,}"
              f"{row['gross_1m']:>9.4f}%{tc:>10.2f}{row['grossR_1m']:>10.3f}"
              f"{row['netR_1m']:>9.3f}{row['gross_5m']:>9.4f}%"
              f"{row['gross_ctl']:>9.4f}%")
    ydf = pd.DataFrame(year_rows)
    ydf.to_csv(f"{REPO}/step476_by_year.csv", index=False)
    pos = int((ydf["gross_1m"] > 0).sum())
    print(f"\narm B gross is positive in {pos} of {len(ydf)} years; its risk "
          f"multiple after costs is positive in "
          f"{int((ydf['netR_1m'] > 0).sum())} of {len(ydf)}.")

    # ----------------------------------------------- per asset, whole window
    print("\n" + "=" * 104)
    print("ARM B BY ASSET (a number that only holds on one coin is a coin fact)")
    print("=" * 104)
    print(f"{'asset':<10}{'entries':>9}{'days':>7}{'gross%':>9}{'t naive':>9}"
          f"{'t by day':>10}{'net%':>9}{'grossR':>9}{'netR':>8}{'stop%':>8}")
    for sym, g in uniq["B"].groupby("sym"):
        tn, n = tstat(g["gross_pct"])
        tc, nd = clustered(g)
        print(f"{sym:<10}{n:>9,}{nd:>7,}{g['gross_pct'].mean():>8.4f}%"
              f"{tn:>9.2f}{tc:>10.2f}{g['net_pct'].mean():>8.4f}%"
              f"{mean_R(g):>9.3f}{mean_R(g, 'net_R'):>8.3f}"
              f"{g['stop_pct'].median():>7.3f}%")

    # ------------------------------------------------ the cell census
    print("\n" + "=" * 104)
    print("CELL CENSUS - DESCRIPTIVE ONLY, NOT A QUALIFICATION")
    print("=" * 104)
    pooled = []
    for (nm, arm), parts in store.items():
        allr = pd.concat([r for _, r in parts])
        tr, va, te = R.slice_by_time(allr, t_tr, t_va)
        s = R.summarise(nm, tr, va)
        if s["verdict"] == "thin":
            continue
        indiv = []
        for sym, r in parts:
            t_, v_, _ = R.slice_by_time(r, t_tr, t_va)
            indiv.append(t_["net_pct"].mean() if len(t_) >= 10 else np.nan)
        s["n_assets_pos"] = int(np.nansum(np.array(indiv, float) > 0))
        s["arm"] = arm
        pooled.append(s)
    pdf = pd.DataFrame(pooled)
    pdf.to_csv(f"{REPO}/step476_cells.csv", index=False)
    for arm, lab in (("A", "5-minute trigger"), ("B", "1-MINUTE trigger")):
        sub = pdf[pdf.arm == arm]
        if not len(sub):
            continue
        ok = sub[(sub.verdict == "qualifies") & (sub.n_assets_pos >= 2)]
        print(f"{lab:<20} cells {len(sub):>3}   positive on both labelled "
              f"slices and 2+ assets: {len(ok):>3}   expected by luck alone "
              f"~{len(sub)/8:.0f}")
        print(f"{'':<20} median gross choosing {sub.gross_tr.median():>8.4f}%"
              f"   median net {sub.mean_tr.median():>8.4f}%"
              f"   median stop {sub.stop_tr.median():.3f}%"
              f" -> {1/sub.stop_tr.median():.1f}x at 1% risked")
    print("\nThose counts CANNOT promote anything. The slices they are cut on")
    print("have already been read by R450 and R475. They are printed so the")
    print("shape of the population is on the record, and for no other use.")

    # --------------------------------------------------- venue arithmetic
    print("\n" + "=" * 104)
    print("THE VENUE ARITHMETIC, CHARGED FOR HONESTY AND DECIDING NOTHING")
    print("=" * 104)
    st = uniq["B"]["stop_pct"].median()
    print(f"median structural stop, arm B: {st:.3f}% of price "
          f"-> {1/st:.1f}x at 1% of the account risked")
    print(f"one Alpaca crypto round trip: {R.COST_RT}% of notional = "
          f"{R.COST_RT/st:.2f} stop distances, charged before the trade moves")
    print(f"arm B gross per entry: {uniq['B']['gross_pct'].mean():.4f}% of "
          f"price = {uniq['B']['gross_pct'].mean()/R.COST_RT:.2f} round trips")
    print("Queue item 4 - the venue table - is the number that moves this.")

    print("\n" + "=" * 104)
    print("LOOKS CONSUMED: NONE. No sealed slice was opened, because this")
    print("family has none left. Nothing here is proposed for deployment.")
    print("=" * 104)
    return uniq, ctl, ydf, pdf


if __name__ == "__main__":
    main()
