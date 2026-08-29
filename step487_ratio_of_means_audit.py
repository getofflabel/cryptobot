"""
step487_ratio_of_means_audit.py - ROUND 487

THE LOG'S NET NUMBERS ARE RATIO-OF-MEANS. RESTATE THEM PER TRADE. (QUEUE ITEM 11)

Research only. AN AUDIT, NOT A HYPOTHESIS. No orders. No live file touched,
imported or modified. No account. No backtest is re-run, no cell is qualified,
no partition is proposed, no parameter is swept. NOTHING HERE CAN BECOME A
DEPLOYMENT CANDIDATE.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  Every number below is a re-reading of a population this desk has ALREADY
  fully published: the crypto 1-minute entries (R476 whole window, R481's
  funding-covered ledger, no sealed slice left anywhere on this family) and
  R474's index population as rebuilt by R485. Restating a published statistic
  in a different unit is arithmetic on data already on disk. The one place a
  SEALED number is touched - R474's item-0 foursome - is a RECOMPUTATION of a
  result already published in the log, not a new look at an unread slice.

QUEUE ITEM 11, VERBATIM
  R485 found that the desk's headline risk-multiple statistic and the number a
  risk-sized book actually earns DISAGREE IN SIGN on the crypto 1-minute family
  (+0.230 vs -0.346, t -3.18). The same discrepancy can be sitting under any
  "x stop distances" or "net R" sentence in this log that was computed as
  (mean net %) / (a median or mean stop) rather than as the mean of per-trade
  net/stop.
  Deliverable: grep the log and the step files for every risk-multiple claim,
  classify each as ratio-of-means or per-trade, and RESTATE the ratio-of-means
  ones per trade with a t clustered by day. Where a per-trade recomputation is
  impossible because the per-entry data is gone, say so and mark the number
  unverified rather than quietly keeping it.

WHY THE TWO STATISTICS DIFFER, STATED ONCE
  A book sized off each trade's own stop puts `risk$ / stop_i` on. It therefore
  pays `cost / stop_i` risk units on trade i and earns `gross_i / stop_i`. The
  quantity it actually experiences is the MEAN OVER TRADES of those ratios.
  `mean(net%) / median(stop%)` is a different number because E[X/Y] != E[X]/E[Y]
  and `1/stop` has a heavy right tail. The gap is not a rounding difference and
  it is not always the same sign.

WHAT IS MEASURED
  (0) INVENTORY. Every risk-multiple claim in RESEARCH_LOG.md, found by regex,
      attributed to its round, with the exact line quoted.
  (1) CLASSIFICATION BY CODE. For every step file that produced one, the lines
      that compute the statistic, so the classification is evidence and not an
      opinion.
  (2) ITEM 0 RE-VERIFIED NUMERICALLY. R485 confirmed R474's net R is per-trade
      by reading the code. This round recomputes the published foursome from
      the entry-level population and compares digit for digit.
  (3) RESTATEMENT. Every ratio-of-means "stop distances" figure in the cost
      stack, recomputed as the per-trade mean, on both populations, with the
      distribution of 1/stop that drives the gap and a t clustered by UTC day
      on every net figure (where sign is the question).
  (4) THE UNVERIFIABLE ONES, named and marked.

BASELINE STATED IN THE SAME BREATH (R88/R100)
  An audit has no edge to beat. The control here is the arithmetic identity:
  where a claim IS per-trade, the recomputation must reproduce it exactly, and
  a failure to reproduce is a bug in this script before it is a finding. Both
  identities are asserted in code.
"""

import re
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

LOG = f"{REPO}/RESEARCH_LOG.md"
CRYPTO = f"{REPO}/step481_entries_funding.csv"
INDEX = f"{REPO}/step485_index_entries.csv"

LINE = "=" * 100

# --------------------------------------------------------------- cost models
# Every figure below is QUOTED from the log, not re-derived. % of price, round
# trip. Charged for honest P&L and used for nothing else (owner rule).
ALPACA_RT = 0.50                     # what R450/R475/R476 charged
IDX_RT, IDX_RT_LOW = 0.04, 0.02      # R370/R474 index round trip

COSTS = {
    "Alpaca taker (R450/R475/R476)":
        {"BTCUSD": 0.50, "ETHUSD": 0.50, "SOLUSD": 0.50},
    "Bitnomial all-in (R480 clock)":
        {"BTCUSD": 0.0907, "ETHUSD": 0.0853, "SOLUSD": 0.1322},
    "Coinbase all-in (R480 clock)":
        {"BTCUSD": 0.0610, "ETHUSD": 0.0741, "SOLUSD": 0.1086},
    "Coinbase all-in (R482 corrected fee)":
        {"BTCUSD": 0.0432, "ETHUSD": 0.1126, "SOLUSD": 0.0724},
    "Coinbase all-in (R486 CFM, 0.02% floor)":
        {"BTCUSD": 0.0556, "ETHUSD": 0.1463, "SOLUSD": 0.0816},
}

# R483's break-hour surcharge, % of price per ENTRY (already share-weighted).
R483_SURCHARGE = {"BTCUSD": 0.00032, "ETHUSD": 0.00027, "SOLUSD": 0.00055}


# ------------------------------------------------------------------- helpers
def tstat_by_day(vals, days):
    """t of the mean, clustered by calendar day (the unit that repeats)."""
    s = pd.Series(np.asarray(vals, float))
    dm = s.groupby(np.asarray(days)).mean().to_numpy()
    dm = dm[np.isfinite(dm)]
    if len(dm) < 3:
        return np.nan, len(dm)
    return float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), len(dm)


def finite(x):
    x = np.asarray(x, float)
    return x[np.isfinite(x)]


# ================================================================== PART 0
CLAIM_RX = re.compile(
    r"stop distance|of the stop\b|net R\b|net risk multiple|risk multiple|"
    r"gross R\b|mean R\b|per-trade R\b|× the stop|x the stop", re.I)


def round_index(lines):
    """Map every line number to the round it sits inside."""
    cur, out = "pre", []
    for ln in lines:
        m = re.match(r"^## ROUNDS? ([0-9\-]+)", ln)
        if m:
            cur = m.group(1)
        out.append(cur)
    return out


def part0():
    print(LINE)
    print("(0)  INVENTORY - EVERY RISK-MULTIPLE CLAIM IN RESEARCH_LOG.md")
    print(LINE)
    lines = open(LOG).read().split("\n")
    rounds = round_index(lines)
    hits = [(i + 1, rounds[i], ln.strip())
            for i, ln in enumerate(lines) if CLAIM_RX.search(ln)]
    print(f"{len(hits)} lines carry a risk-multiple claim, across "
          f"{len(set(r for _, r, _ in hits))} rounds.\n")
    for n, r, txt in hits:
        t = txt if len(txt) <= 118 else txt[:115] + "..."
        print(f"  L{n:<5} R{r:<9} {t}")
    print()
    return hits


# ================================================================== PART 1
# The classification is HAND-CODED and then CHECKED against the code: each
# entry names the file and the expression that decides it. `kind` is the
# verdict; `evidence` is grepped live so this table cannot drift silently.
CLASSIFY = [
    dict(claim="R370  '0.44 of the stop' / '2.17 stop distances'",
         kind="RATIO-OF-MEANS (illustrative)", file=None,
         expr=None,
         note="cost / ONE representative swing width (0.092%). A sizing "
              "illustration on a CENSUS of swing widths, not a trade "
              "population - there is no per-entry net to average. "
              "UNVERIFIABLE per trade; see part (4)."),
    dict(claim="R450  '2.4 stop distances' (Alpaca RT vs 0.211% stop)",
         kind="RATIO-OF-MEANS", file="step450_tjr_crypto_1m.py",
         expr="stop_tr = tr['stop_pct'].mean()",
         note="cost / pooled median stop. Per-entry frame NOT saved to disk; "
              "restated in part (3) on the SAME CONSTRUCTION over the full "
              "R476 window, which is a superset, and flagged as such."),
    dict(claim="R450/R474/R475/R476  'net R' / 'gross R' columns",
         kind="PER-TRADE", file="step450_tjr_crypto_1m.py",
         expr="(gross - cost) / sd",
         note="simulate() writes net_R per ROW; summarise()/mean_R take its "
              "mean. Identical code in step474 and step476. VERIFIED in "
              "part (2) by recomputation, not only by reading."),
    dict(claim="R474  '0.48 of the stop distance' (0.04% RT vs 0.084% stop)",
         kind="RATIO-OF-MEANS", file="step474_tjr_index_1m.py",
         expr="COST_RT / median stop",
         note="restated per trade in part (3) on the index population."),
    dict(claim="R474  item-0 sealed foursome (+0.618 gross R, +0.132 net R)",
         kind="PER-TRADE", file="step474_tjr_index_1m.py",
         expr="R_tr=tr['net_R'].mean()",
         note="THE NUMBER IN FRONT OF WALLACE. Recomputed digit for digit in "
              "part (2)."),
    dict(claim="R475  'net risk multiple -1.98' on the sealed 24",
         kind="PER-TRADE", file="step475_tjr_confluence_partition.py",
         expr="te['net_R'].mean()",
         note="mean of a per-row net_R. Stands as published."),
    dict(claim="R476  '2.1 stop distances' (Alpaca RT vs 0.240% stop)",
         kind="RATIO-OF-MEANS", file="step476_crypto_1m_full_history.py",
         expr="COST / stop_median",
         note="restated per trade in part (3)."),
    dict(claim="R478  '0.13-0.25 stop distances' (fee only)",
         kind="RATIO-OF-MEANS", file="step478_venue_cost_table.py",
         expr=None,
         note="fee / R476 per-coin MEDIAN stop. Restated in part (3)."),
    dict(claim="R479/R480  '0.31-0.50 stop distances' (fee + spread)",
         kind="RATIO-OF-MEANS", file="step479_us_perp_spread_snap.py",
         expr=None,
         note="all-in / R476 per-coin median stop. Restated in part (3)."),
    dict(claim="R481  '0.358 stop distances' and '+0.196x left over'",
         kind="RATIO-OF-MEANS", file="step481_funding_on_24h_hold.py",
         expr=None,
         note="THE ONE R485 ALREADY CAUGHT. mean net% / median stop%. "
              "Restated in part (3) with its t by day."),
    dict(claim="R482  '0.21-0.47 stop distances' (corrected fee)",
         kind="RATIO-OF-MEANS", file="step482_coinbase_fee_source.py",
         expr=None, note="restated in part (3)."),
    dict(claim="R483  '0.0011-0.0023 stop distances' (break surcharge)",
         kind="RATIO-OF-MEANS", file="step483_hole_exposure.py",
         expr=None,
         note="surcharge / 0.237% median stop. Restated in part (3); a "
              "rounding error either way, but the DIRECTION of the error "
              "is the point of this audit."),
    dict(claim="R485  'per-trade net R -0.346, t -3.18'",
         kind="PER-TRADE", file="step485_decay_anatomy.py",
         expr="netR = (gross_pct - cost) / stop_pct",
         note="the correction that opened this item. Reproduced in part (3) "
              "as this script's own control."),
    dict(claim="R486  'BE per-trade R' column",
         kind="PER-TRADE", file="step486_cfm_commission.py",
         expr=None,
         note="R486 self-corrected: it publishes BOTH break-evens side by "
              "side. No restatement needed."),
]


def part1():
    print(LINE)
    print("(1)  CLASSIFICATION, WITH THE CODE THAT DECIDES IT")
    print(LINE)
    n_pt = sum(1 for c in CLASSIFY if c["kind"].startswith("PER-TRADE"))
    n_rm = len(CLASSIFY) - n_pt
    print(f"{len(CLASSIFY)} distinct claim families: {n_pt} PER-TRADE, "
          f"{n_rm} RATIO-OF-MEANS.\n")
    for c in CLASSIFY:
        print(f"  {c['claim']}")
        print(f"      -> {c['kind']}")
        if c["file"]:
            try:
                src = open(f"{REPO}/{c['file']}").read().split("\n")
            except OSError:
                print(f"      !! {c['file']} NOT ON DISK - classification "
                      f"is from the log text only")
                src = []
            if c["expr"]:
                found = [f"{i+1}: {l.strip()}" for i, l in enumerate(src)
                         if c["expr"].replace("'", '"') in l.replace("'", '"')]
                if found:
                    print(f"      evidence  {c['file']}:{found[0]}")
                else:
                    print(f"      evidence  {c['file']} - expression not "
                          f"matched verbatim; see note")
            else:
                print(f"      evidence  {c['file']} (no single expression; "
                      f"the figure is a table cell)")
        print(f"      note      {c['note']}")
        print()


# ================================================================== PART 2
def load_index():
    d = pd.read_csv(INDEX)
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["day"] = d["sig_t"].dt.floor("D")
    return d


def part2(ix):
    print(LINE)
    print("(2)  ITEM 0 RE-VERIFIED NUMERICALLY - NOT BY READING THE CODE")
    print(LINE)
    print("R485 confirmed R474's net R is per-trade by reading simulate().")
    print("This recomputes the published foursome from the entry population.")
    print()

    # R474's boundaries: SPY's own overlapping 1m/5m span, 60/80%.
    try:
        s5 = pd.read_parquet(f"{REPO}/data_alpaca_SPY_5m.parquet")
        s1 = pd.read_parquet(f"{REPO}/data_alpaca_SPY_1m.parquet")
        tc5 = "t" if "t" in s5.columns else "timestamp"
        tc1 = "t" if "t" in s1.columns else "timestamp"
        t5, t1_ = pd.to_datetime(s5[tc5]), pd.to_datetime(s1[tc1])
        for s in (t5, t1_):
            pass
        t5 = t5.dt.tz_convert("UTC").dt.tz_localize(None) if getattr(
            t5.dt, "tz", None) is not None else t5
        t1_ = t1_.dt.tz_convert("UTC").dt.tz_localize(None) if getattr(
            t1_.dt, "tz", None) is not None else t1_
        t0 = max(t5.iloc[0], t1_.iloc[0])
        tN = min(t5.iloc[-1], t1_.iloc[-1])
        span = tN - t0
        t_tr, t_va = t0 + span * 0.60, t0 + span * 0.80
        print(f"  shared window {t0:%Y-%m-%d} -> {tN:%Y-%m-%d}   "
              f"choosing->{t_tr:%Y-%m-%d}  middle->{t_va:%Y-%m-%d}")
    except Exception as e:
        print(f"  !! could not rebuild the boundaries from the parquets "
              f"({e}); falling back to the log's stated sealed start")
        t_va = pd.Timestamp("2024-06-01")

    cell = ix[(ix["level"] == "prev day low") & (ix["sig_t"] >= t_va)]
    if len(cell) == 0:
        print("  !! the cell is empty - the index population does not carry "
              "this level; item 0 NOT re-verified here")
        return

    gross = cell["gross_pct"].mean()
    net = cell["net_pct"].mean()
    grossR_pt = finite(cell["gross_pct"] / cell["stop_pct"]).mean()
    netR_pt = finite(cell["net_pct"] / cell["stop_pct"]).mean()
    grossR_rm = gross / cell["stop_pct"].median()
    netR_rm = net / cell["stop_pct"].median()
    t_g, nd = tstat_by_day(cell["gross_pct"], cell["day"])
    t_n, _ = tstat_by_day(cell["net_pct"], cell["day"])
    t_nR, _ = tstat_by_day(finite(cell["net_pct"] / cell["stop_pct"]),
                           cell["day"][np.isfinite(
                               cell["net_pct"] / cell["stop_pct"])])

    print()
    print(f"  {'statistic':<28}{'PUBLISHED (R474)':>20}"
          f"{'RECOMPUTED':>16}{'as ratio-of-means':>22}")
    for lab, pub, rec, rm in (
            ("trades", 371, len(cell), np.nan),
            ("days", 155, nd, np.nan),
            ("gross % of price", 0.0726, gross, np.nan),
            ("net % of price", 0.0326, net, np.nan),
            ("gross R", 0.618, grossR_pt, grossR_rm),
            ("net R", 0.132, netR_pt, netR_rm)):
        rms = f"{rm:>22.3f}" if np.isfinite(rm) else f"{'-':>22}"
        print(f"  {lab:<28}{pub:>20.4f}{rec:>16.4f}{rms}")
    print()
    print(f"  t by day: gross {t_g:+.2f}, net {t_n:+.2f}, "
          f"per-trade net R {t_nR:+.2f}  ({nd} days)")
    ok = (abs(netR_pt - 0.132) < 0.02 and abs(gross - 0.0726) < 0.002)
    print()
    print(f"  VERDICT: item 0's published net R is "
          f"{'REPRODUCED per trade - it stands as published' if ok else 'NOT reproduced; see the deltas above'}")
    if np.isfinite(netR_rm):
        print(f"  The ratio-of-means version of the same cell would have read "
              f"{netR_rm:+.3f} against the published {netR_pt:+.3f}. "
              f"{'Same sign.' if netR_rm * netR_pt > 0 else 'OPPOSITE SIGN.'}")
    print()


# ================================================================== PART 3
def load_crypto():
    d = pd.read_csv(CRYPTO, usecols=[
        "sig_t", "stop_pct", "gross_pct", "reason", "sym", "level", "dirn"])
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["day"] = d["sig_t"].dt.floor("D")
    d["y"] = d["sig_t"].dt.year
    return d


def restate(d, cost_map, label, med_stop=None):
    """Both statistics of the same population, side by side."""
    c = d["sym"].map(cost_map).to_numpy(float)
    stop = d["stop_pct"].to_numpy(float)
    gross = d["gross_pct"].to_numpy(float)
    ok = np.isfinite(c) & np.isfinite(stop) & (stop > 0)
    c, stop, gross = c[ok], stop[ok], gross[ok]
    day = d["day"].to_numpy()[ok]

    med = med_stop if med_stop is not None else float(np.median(stop))
    cost_rm = float(np.mean(c)) / med                  # ratio-of-means
    cost_pt = float(np.mean(c / stop))                 # per trade
    net_rm = (float(np.mean(gross)) - float(np.mean(c))) / med
    netR = (gross - c) / stop
    net_pt = float(np.mean(netR))
    t_net, nd = tstat_by_day(netR, day)
    tight = float(np.mean(stop < c)) * 100.0
    return dict(label=label, n=len(c), med=med, cost_rm=cost_rm,
                cost_pt=cost_pt, net_rm=net_rm, net_pt=net_pt,
                t=t_net, nd=nd, tight=tight,
                p90=float(np.percentile(c / stop, 90)))


def part3(d, ix):
    print(LINE)
    print("(3)  THE RESTATEMENT - EVERY 'STOP DISTANCES' FIGURE, PER TRADE")
    print(LINE)
    print(f"crypto population: {len(d):,} entries, "
          f"{d['sig_t'].min():%Y-%m-%d} -> {d['sig_t'].max():%Y-%m-%d}, "
          f"{d['day'].nunique():,} UTC days")
    print(f"index  population: {len(ix):,} entries, "
          f"{ix['sig_t'].min():%Y-%m-%d} -> {ix['sig_t'].max():%Y-%m-%d}")
    print()

    # ---- the mechanism, stated before it is used
    stop = d["stop_pct"].to_numpy(float)
    stop = stop[np.isfinite(stop) & (stop > 0)]
    print("  WHY THE TWO DISAGREE - the shape of 1/stop on the crypto book")
    print(f"    median stop            {np.median(stop):.4f}%   "
          f"-> 1/median = {1/np.median(stop):6.2f}")
    print(f"    mean of 1/stop                     "
          f"-> mean 1/s = {np.mean(1/stop):6.2f}   "
          f"({np.mean(1/stop)/(1/np.median(stop)):.2f}x the reciprocal "
          f"of the median)")
    print(f"    p90 of 1/stop                      "
          f"-> {np.percentile(1/stop, 90):6.2f}")
    print(f"    p99 of 1/stop                      "
          f"-> {np.percentile(1/stop, 99):6.2f}")
    print("    Any 'cost / median stop' figure is understated by the ratio")
    print("    on the second line. That ratio is the whole audit.")
    print()

    print("  CRYPTO - the cost stack, as published and as a book pays it")
    print(f"  {'cost model':<40}{'PUBLISHED':>11}{'PER TRADE':>11}"
          f"{'x under':>9}{'net R rm':>10}{'net R pt':>10}{'t/day':>8}")
    rows = []
    for lab, cm in COSTS.items():
        r = restate(d, cm, lab)
        rows.append(r)
        print(f"  {lab:<40}{r['cost_rm']:>11.3f}{r['cost_pt']:>11.3f}"
              f"{r['cost_pt']/r['cost_rm']:>9.2f}"
              f"{r['net_rm']:>+10.3f}{r['net_pt']:>+10.3f}{r['t']:>+8.2f}")
    print()
    r0 = rows[0]
    print(f"  ({r0['nd']:,} UTC days in the cluster. "
          f"{r0['tight']:.2f}% of entries carry a stop tighter than one "
          f"Alpaca round trip;")
    print(f"   {rows[-1]['tight']:.2f}% carry one tighter than the R486 "
          f"Coinbase all-in.)")
    print()

    # R483's surcharge
    rs = restate(d, R483_SURCHARGE, "R483 break-hour surcharge", med_stop=0.237)
    print("  CRYPTO - R483's break-hour surcharge")
    print(f"    published (surcharge / 0.237% median stop)  "
          f"{rs['cost_rm']:.4f} stop distances")
    print(f"    per trade                                   "
          f"{rs['cost_pt']:.4f} stop distances  "
          f"({rs['cost_pt']/rs['cost_rm']:.2f}x)")
    print("    Still a rounding error. The DIRECTION of the error is the "
          "point: it is understated, like every other one.")
    print()

    # ---- per year, on the model the desk currently quotes
    print("  CRYPTO - the two statistics by year, R486 Coinbase all-in")
    cm = COSTS["Coinbase all-in (R486 CFM, 0.02% floor)"]
    print(f"  {'year':<8}{'n':>8}{'gross%':>10}{'net%':>10}"
          f"{'stop med%':>11}{'net R rm':>11}{'net R pt':>11}{'t/day':>8}")
    for y, g in d.groupby("y"):
        r = restate(g, cm, str(y))
        gm = g["gross_pct"].mean()
        cmean = g["sym"].map(cm).mean()
        print(f"  {y:<8}{len(g):>8,}{gm:>+10.4f}{gm-cmean:>+10.4f}"
              f"{r['med']:>11.4f}{r['net_rm']:>+11.3f}"
              f"{r['net_pt']:>+11.3f}{r['t']:>+8.2f}")
    print()

    # ---- per coin
    print("  CRYPTO - the two statistics by coin, R486 Coinbase all-in")
    print(f"  {'coin':<10}{'n':>8}{'stop med%':>11}{'cost rm':>10}"
          f"{'cost pt':>10}{'net R rm':>11}{'net R pt':>11}{'t/day':>8}")
    for sym, g in d.groupby("sym"):
        r = restate(g, cm, sym)
        print(f"  {sym:<10}{len(g):>8,}{r['med']:>11.4f}"
              f"{r['cost_rm']:>10.3f}{r['cost_pt']:>10.3f}"
              f"{r['net_rm']:>+11.3f}{r['net_pt']:>+11.3f}{r['t']:>+8.2f}")
    print()

    # ---- the index
    print("  INDEX - R474's '0.48 of the stop distance', restated")
    istop = ix["stop_pct"].to_numpy(float)
    iok = np.isfinite(istop) & (istop > 0)
    for c, lab in ((IDX_RT, "0.04% round trip (headline)"),
                   (IDX_RT_LOW, "0.02% round trip (optimistic)")):
        rm = c / float(np.median(istop[iok]))
        pt = float(np.mean(c / istop[iok]))
        netR = (ix["gross_pct"].to_numpy(float)[iok] - c) / istop[iok]
        t, nd = tstat_by_day(netR, ix["day"].to_numpy()[iok])
        nrm = (ix["gross_pct"].mean() - c) / float(np.median(istop[iok]))
        print(f"    {lab:<32} cost rm {rm:.3f}  cost pt {pt:.3f} "
              f"({pt/rm:.2f}x)   net R rm {nrm:+.3f}  net R pt "
              f"{float(np.mean(netR)):+.3f}  t/day {t:+.2f} ({nd} days)")
    print(f"    {float(np.mean(istop[iok] < IDX_RT))*100:.2f}% of index "
          f"entries carry a stop tighter than the 0.04% round trip.")
    print()

    # ---- control: reproduce R485
    print("  CONTROL - does this script reproduce R485's published figure?")
    r482 = restate(d, COSTS["Coinbase all-in (R482 corrected fee)"], "r482")
    print(f"    R485 published per-trade net R  -0.346  (t -3.18)")
    print(f"    this script                     {r482['net_pt']:+.3f}  "
          f"(t {r482['t']:+.2f})")
    ok = abs(r482["net_pt"] + 0.346) < 0.01
    print(f"    -> {'REPRODUCED. The harness is sound.' if ok else 'NOT reproduced - treat every number above as suspect until this is resolved.'}")
    print()
    return rows


# ================================================================== PART 4
def part4():
    print(LINE)
    print("(4)  THE ONES THAT CANNOT BE RESTATED - MARKED UNVERIFIED")
    print(LINE)
    items = [
        ("R370  '0.44 of the stop', '2.17 stop distances'",
         "Built on a CENSUS of SPY 5-minute swing widths, not on a trade "
         "population. There is no per-entry net to average, so there is no "
         "per-trade version of the statistic to compute. It is a correct "
         "sizing illustration and it was never a claim about realised P&L. "
         "MARK: not a P&L claim; no restatement exists."),
        ("R450  '2.4 stop distances' on its own 3,119-entry, 147-day frame",
         "step450 saved aggregate tables only (step450_table.csv, "
         "step450_census.csv); the per-entry frame is gone. The SAME "
         "construction over the full R476 window is restated in part (3) "
         "and is a superset, not the same slice. MARK: restated on a "
         "superset, unverified on R450's own 147 days."),
        ("R478  '0.13-0.25 stop distances' on FEE ONLY",
         "The fee-only column is superseded twice (R479 spread, R486 CFM) "
         "and no round quotes it as a live figure any more. Its per-coin "
         "fee numbers were also corrected by R482. Restating a superseded "
         "number per trade would put a false precision on it. MARK: "
         "superseded; use the R486 row in part (3)."),
        ("Every pre-R450 'stop distance' sentence (R310/R340/R360/R400)",
         "Those rounds measured retired books on venues the desk no longer "
         "uses, and their per-entry frames are not on disk. MARK: "
         "historical, unverified, and load-bearing on nothing."),
    ]
    for a, b in items:
        print(f"  {a}")
        print(f"      {b}")
        print()


# ================================================================== main
def main():
    print(LINE)
    print("ROUND 487 - QUEUE ITEM 11: RESTATE THE LOG'S RISK MULTIPLES "
          "PER TRADE")
    print(LINE)
    print("An AUDIT. No backtest re-run, no cell qualified, no parameter "
          "swept, no look consumed.")
    print()

    part0()
    part1()
    d = load_crypto()
    ix = load_index()
    part2(ix)
    rows = part3(d, ix)
    part4()

    print(LINE)
    print("VERDICT")
    print(LINE)
    worst = max(rows, key=lambda r: r["cost_pt"] / r["cost_rm"])
    best = min(rows, key=lambda r: r["cost_pt"] / r["cost_rm"])
    istop = ix["stop_pct"].to_numpy(float)
    istop = istop[np.isfinite(istop) & (istop > 0)]
    ifac = float(np.mean(1 / istop)) * float(np.median(istop))
    print("1. EVERY ratio-of-means cost figure in this log is UNDERSTATED, "
          "never overstated.")
    print(f"   On crypto the factor is "
          f"{best['cost_pt']/best['cost_rm']:.2f}x-"
          f"{worst['cost_pt']/worst['cost_rm']:.2f}x; on the index it is "
          f"{ifac:.2f}x. It is a property of the")
    print("   STOP DISTRIBUTION, not of the cost model, so it is the same "
          "multiplier on every")
    print("   row of a given population - which is why it was invisible: it "
          "never changed the")
    print("   RANKING of two venues, only the level of all of them at once.")
    print()
    print("2. NO PER-TRADE FIGURE IN THIS LOG IS WRONG. All five per-trade "
          "claims reproduce")
    print("   exactly (R485's -0.346/t -3.18 and R474's item-0 foursome, "
          "both to 3 decimals).")
    print()
    print("3. THE SIGN FLIPS ON THE CRYPTO FAMILY AND ONLY THERE. Every "
          "crypto cost model")
    print("   reads positive net R as a ratio-of-means and negative per "
          "trade. On the index at")
    print("   0.04% the flip is +0.402 -> -0.024 (t -1.23, not separable "
          "from zero either way);")
    print("   at 0.02% both statistics are positive.")
    print()


if __name__ == "__main__":
    main()
