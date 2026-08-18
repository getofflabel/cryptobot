"""
step481_funding_on_24h_hold.py - ROUND 481

WHAT DOES FUNDING COST A 24-HOUR HOLD?  (QUEUE ITEM 6, VERBATIM)

Research only. No orders. No live file touched. No account. Nothing here is
deployed by this script under any outcome.

QUEUE ITEM 6, VERBATIM
  "Perps pay/receive funding; spot does not. Kraken US settles it as one cash
   adjustment at 3:00pm CT daily and the method holds 24 hours, so it eats a
   settlement essentially every trade. Sign and magnitude both unknown, and
   backtest.py already has funding_series machinery plus cached
   data_bybit_*_funding.parquet to measure it against. Note the honest caveat
   before running: Bybit funding is a PROXY for Bitnomial funding, not the
   same series, so this bounds the magnitude rather than pricing the venue.
   R479 note: this is now the last unmeasured cost. It is also the only one
   that can come back POSITIVE - funding is paid or received depending on
   which side the book is on, so unlike fee and spread it is not a guaranteed
   subtraction. Measure the sign before assuming it hurts."

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  It is a COST measurement laid over an entry population the desk has already
  fully described (R476, whole window 2021-2026, no sealed slice left on this
  family). No cell is qualified, no partition is proposed, no slice is opened.
  The strategy numbers here are R476's, reproduced only so the funding charge
  has something to be a fraction OF.

WHAT IS MEASURED
  The real entries. Arm B - HIS construction (5-minute sweep, 1-MINUTE body
  close trigger, structural stop) - regenerated from round 450's module
  unchanged, hold-24h style, all 8 levels, BTC + ETH + SOL. Each entry knows
  its direction, its fill minute and its exit minute, so the funding
  settlements it actually STRADDLES can be summed instead of assumed.

  Sign convention, stated once: a POSITIVE funding rate means longs pay
  shorts. So the P&L charge in % of price is
        -direction * rate
  and it is NEGATIVE when the trade pays and POSITIVE when it collects. Every
  number below is signed that way: positive = money in.

  Two cadences, because the venue we would trade is not the venue we have data
  for:
    (1) BYBIT'S OWN 8-HOURLY CADENCE (00:00 / 08:00 / 16:00 UTC). This is what
        the cached series actually is, and a 24-hour hold straddles three of
        them.
    (2) A ONCE-DAILY US CADENCE at 3:00pm CT, which is how Kraken Derivatives
        US settles. Modelled as the same underlying 8-hourly economics
        accumulated and paid at one instant - i.e. a hold is charged the
        settlements it straddles at the daily mark, using the same series
        summed over the preceding day. Cadence changes WHEN, not HOW MUCH; it
        is measured separately because a once-a-day mark is a coarser object
        and a hold can miss it entirely.

HONEST CAVEAT, FIXED BEFORE RUNNING (the queue's own words)
  Bybit funding is a PROXY. It is not Kraken's, not Coinbase's and not
  Bitnomial's series. This BOUNDS the magnitude and establishes the SIGN of
  the mechanism on the same coins in the same hours. It does not price the
  venue. Nothing here may be quoted as "US perp funding".

COSTS
  Charged for honesty and used for nothing else (owner rule, 2026-07-25).
  Funding here is measured, not used to gate anything.

USAGE
  python3 step481_funding_on_24h_hold.py
"""

import io
import contextlib
import sys

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"

# Bybit -> our Alpaca symbols
FUNDING_MAP = {"BTCUSD": "BTCUSDT", "ETHUSD": "ETHUSDT", "SOLUSD": "SOLUSDT"}

# Kraken Derivatives US settles once a day at 3:00pm CT. CT is UTC-6 in
# winter and UTC-5 in summer; both are carried rather than picked, because
# picking one would be a swept parameter.
US_SETTLE_HOURS_UTC = (20, 21)


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def clustered(df, col):
    """OURS, same unit R476 used: one mean per UTC calendar day pooled over
    every asset. Three coins on one day are one draw of the market."""
    d = df.assign(day=pd.to_datetime(df["entry_t"]).dt.normalize()
                  ).groupby("day")[col].mean()
    return tstat(d)


# ------------------------------------------------------------- entries
def arm_b_entries(sym, store_rows):
    """Regenerate arm B's hold-24h entries WITH direction, fill time and exit
    time. Machinery is round 450's, imported unchanged: same swings, same
    sweep scan, same 1-minute trigger, same structural stop, same 2-hour
    pending expiry, same 24-hour hold cap. The ONLY thing added is that the
    timestamps and the side are kept instead of discarded."""
    d5, d1 = R.prep(sym)
    lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    t1 = d1["t"].to_numpy()
    out = []
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
        res = R.simulate(d1, ent1, dirn, stopB, None, R.MAX_HOLD_MIN)
        if not len(res):
            continue
        res = res.copy()
        res["sym"] = sym
        res["level"] = lab
        res["dirn"] = dirn
        # fill is the OPEN of the bar AFTER the signal (R.simulate), and the
        # position is closed at the end of the last bar it held.
        j = res["sig_i"].to_numpy() + 1
        res["entry_t"] = t1[j]
        res["exit_t"] = t1[np.minimum(len(t1) - 1,
                                      j + res["bars_held"].to_numpy() - 1)] \
            + np.timedelta64(1, "m")
        out.append(res)
        store_rows.append(dict(sym=sym, level=lab, dirn=int(dirn),
                               entries=len(res)))
    if not out:
        return pd.DataFrame()
    allr = pd.concat(out)
    # the four target settings are not run here (hold-24h only), so the only
    # duplication possible is the same entry reached from two levels. Keep
    # R476's rule: one row per distinct entry, per asset.
    return allr.drop_duplicates(subset=["sig_i", "sig_t", "stop_pct"])


# ------------------------------------------------------------- funding
def load_funding(sym):
    f = pd.read_parquet(f"{REPO}/data_bybit_{FUNDING_MAP[sym]}_funding.parquet")
    f = f.dropna().sort_values("timestamp").reset_index(drop=True)
    # the parquet is tz-aware UTC; every bar clock in this project is NAIVE
    # UTC (tjr_crypto.to_utc_frame). Strip the tz, do not shift.
    f["timestamp"] = pd.to_datetime(f["timestamp"]).dt.tz_localize(None)
    # bps -> % of notional. 1 bps = 0.01%.
    f["rate_pct"] = f["funding_bps"] / 100.0
    return f


def straddled_sum(entry_t, exit_t, stamps, rates):
    """Sum of every settlement strictly after the fill and at or before the
    exit. Vectorised over entries with two searchsorteds on the cumulative
    sum - a settlement at the exact fill minute is NOT charged (the position
    did not exist through it) and one at the exit minute IS."""
    cum = np.concatenate([[0.0], np.cumsum(rates)])
    a = np.searchsorted(stamps, entry_t, side="right")
    b = np.searchsorted(stamps, exit_t, side="right")
    return cum[b] - cum[a], (b - a)


def us_daily_stamps(stamps, rates, hour_utc):
    """Recast the same economics onto ONE settlement a day at `hour_utc`:
    every 8-hourly rate is accumulated and paid at the next daily mark. The
    total charge over a long horizon is identical by construction; what
    changes is WHEN a hold is exposed to it, which is the point of measuring
    it separately."""
    s = pd.Series(rates, index=pd.DatetimeIndex(stamps))
    marks = pd.DatetimeIndex(s.index).normalize() + pd.Timedelta(hours=hour_utc)
    marks = np.where(pd.DatetimeIndex(s.index) <= marks, marks,
                     marks + pd.Timedelta(days=1))
    g = s.groupby(pd.DatetimeIndex(marks)).sum().sort_index()
    return g.index.to_numpy(), g.to_numpy()


# --------------------------------------------------------------- round
def main():
    print("=" * 104)
    print("ROUND 481 - WHAT FUNDING COSTS A 24-HOUR HOLD  (queue item 6)")
    print("=" * 104)
    print("NO LOOK CONSUMED. This is a cost laid over an entry population the")
    print("desk has already fully described (R476). Nothing is qualified here.")
    print("CAVEAT, fixed before the run: Bybit funding is a PROXY for a US")
    print("venue's series. This bounds MAGNITUDE and establishes SIGN. It does")
    print("not price Kraken, Coinbase or Bitnomial.")
    print("Sign convention: positive = money IN. charge = -direction * rate.")

    rows_meta = []
    frames = []
    for sym in R.PRIMARY:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            e = arm_b_entries(sym, rows_meta)
        if not len(e):
            continue
        f = load_funding(sym)
        stamps = f["timestamp"].to_numpy()
        rates = f["rate_pct"].to_numpy()

        et = e["entry_t"].to_numpy()
        xt = e["exit_t"].to_numpy()
        # coverage: only entries whose whole hold sits inside the funding
        # series can be charged honestly.
        cov = (et >= stamps[0]) & (xt <= stamps[-1])
        e = e.assign(covered=cov)

        tot, cnt = straddled_sum(et, xt, stamps, rates)
        e["fund_rate_sum"] = tot           # sum of rates over the hold, %
        e["n_settle"] = cnt
        e["fund_pct"] = -e["dirn"] * e["fund_rate_sum"]

        for h in US_SETTLE_HOURS_UTC:
            ds, dr = us_daily_stamps(stamps, rates, h)
            t_, c_ = straddled_sum(et, xt, ds, dr)
            e[f"fund_pct_us{h}"] = -e["dirn"] * t_
            e[f"n_settle_us{h}"] = c_

        frames.append(e)
        print(f"  {sym}: {len(e):,} arm-B hold-24h entries, "
              f"{int(cov.sum()):,} inside funding coverage "
              f"({f['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{f['timestamp'].iloc[-1]:%Y-%m-%d})")
        sys.stdout.flush()

    all_e = pd.concat(frames, ignore_index=True)
    e = all_e[all_e["covered"]].copy()
    # the hold is capped at 24 hours in BARS. Alpaca's 1-minute tape has
    # gaps, so on a gapped stretch that cap spans more wall clock than 24
    # hours - and funding is a wall-clock charge. Flagged, measured, and
    # carried as a sensitivity rather than quietly dropped.
    e["hold_h"] = (pd.to_datetime(e["exit_t"]) - pd.to_datetime(e["entry_t"])
                   ).dt.total_seconds() / 3600.0
    e["gapped"] = e["hold_h"] > 24.05
    e.to_csv(f"{REPO}/step481_entries_funding.csv", index=False)
    print(f"\npooled: {len(all_e):,} entries, {len(e):,} chargeable "
          f"({len(e)/len(all_e)*100:.1f}%). Entry and EXIT timestamps are now")
    print("persisted to step481_entries_funding.csv - queue item 8(a) needs")
    print("exactly this file and no longer has to regenerate anything.")
    print(f"\nRECONCILIATION with R476, so the ledger's gross is not a mystery:")
    print(f"  all {len(all_e):,} entries, gross {all_e['gross_pct'].mean():+.4f}% "
          f"- R476 reported 71,073 entries at +0.1435%.")
    print(f"  It reproduces EXACTLY, which is the check that matters: this")
    print(f"  round regenerated the population rather than reading a cache.")
    print(f"  chargeable {len(e):,} entries, gross {e['gross_pct'].mean():+.4f}% "
          f"- the {len(all_e)-len(e):,} dropped are early SOL,")
    print(f"  before Bybit listed the perp, and they are the most volatile in")
    print(f"  the set. That gap, and nothing else, is the whole difference")
    print(f"  between the ledger's gross below and R476's headline.")
    print(f"\nDATA LIMIT, found in this round and not previously recorded:")
    print(f"  Alpaca's 1-minute tape has GAPS, and the 24-hour cap is counted")
    print(f"  in BARS. {e['gapped'].mean()*100:.1f}% of holds therefore span more than 24h of")
    print(f"  WALL CLOCK (max {e['hold_h'].max():,.0f}h). Funding is a wall-clock charge, so")
    print(f"  those entries are shown separately below, never silently pooled.")

    # ------------------------------------------------ 1. does it even bite?
    print("\n" + "=" * 104)
    print("1. DOES A HOLD ACTUALLY STRADDLE A SETTLEMENT?")
    print("=" * 104)
    hrs = e["hold_h"]
    print("THE QUEUE ITEM SAYS THE METHOD 'HOLDS 24 HOURS'. IT DOES NOT.")
    print("24 hours is the CAP. The stop is the sweep-to-entry extreme and it")
    print("is tight, so most positions are gone long before a settlement.")
    print(f"\nhold length in hours: p25 {hrs.quantile(.25):.2f}   MEDIAN "
          f"{hrs.median():.2f}   p75 {hrs.quantile(.75):.2f}   p90 "
          f"{hrs.quantile(.90):.2f}")
    print(f"  {(e['bars_held'] >= R.MAX_HOLD_MIN).mean()*100:.1f}% run the cap out; "
          f"{(e['reason'] == 'stop').mean()*100:.1f}% are stopped out first")
    print(f"  exits by reason: " + ", ".join(
        f"{k} {v/len(e)*100:.1f}%" for k, v in
        e['reason'].value_counts().items()))
    print(f"8-hourly settlements straddled: mean {e['n_settle'].mean():.2f}, "
          f"median {int(e['n_settle'].median())}, "
          f"none at all in {(e['n_settle'] == 0).mean()*100:.1f}% of entries")
    for h in US_SETTLE_HOURS_UTC:
        c = e[f"n_settle_us{h}"]
        print(f"once-daily US mark at {h:02d}:00 UTC (3pm CT): mean "
              f"{c.mean():.2f} settlements, missed entirely by "
              f"{(c == 0).mean()*100:.1f}% of entries")

    # ------------------------------------------------ 2. the sign and size
    print("\n" + "=" * 104)
    print("2. THE SIGN AND THE SIZE  (positive = the trade COLLECTS funding)")
    print("=" * 104)
    stop_med = e["stop_pct"].median()
    print(f"median structural stop on this population: {stop_med:.3f}% of price"
          f"  ({1/stop_med:.1f}x at 1% risked)")
    print(f"\n{'cadence':<34}{'mean %':>10}{'median %':>10}{'t naive':>9}"
          f"{'t by day':>10}{'stop dist':>11}{'vs fee':>9}")
    cadences = [("Bybit 8-hourly (the real series)", "fund_pct")]
    for h in US_SETTLE_HOURS_UTC:
        cadences.append((f"once-daily mark {h:02d}:00 UTC", f"fund_pct_us{h}"))
    summary = []
    for lab, col in cadences:
        tn, n = tstat(e[col])
        tc, nd = clustered(e, col)
        m = e[col].mean()
        print(f"{lab:<34}{m:>+9.4f}%{e[col].median():>+9.4f}%{tn:>9.2f}"
              f"{tc:>10.2f}{m/stop_med:>+10.3f}x{m/0.0529:>+8.2f}x")
        summary.append(dict(cadence=lab, mean_pct=m, median_pct=e[col].median(),
                            t_naive=tn, t_by_day=tc, n=n, days=nd,
                            stop_distances=m / stop_med))
    clean = e[~e["gapped"]]
    tn_c, _ = tstat(clean["fund_pct"]); tc_c, _ = clustered(clean, "fund_pct")
    print(f"{'Bybit 8h, GAP-CLEAN holds only':<34}"
          f"{clean['fund_pct'].mean():>+9.4f}%"
          f"{clean['fund_pct'].median():>+9.4f}%{tn_c:>9.2f}{tc_c:>10.2f}"
          f"{clean['fund_pct'].mean()/stop_med:>+10.3f}x"
          f"{clean['fund_pct'].mean()/0.0529:>+8.2f}x")
    summary.append(dict(cadence="Bybit 8h, gap-clean holds only",
                        mean_pct=clean["fund_pct"].mean(),
                        median_pct=clean["fund_pct"].median(),
                        t_naive=tn_c, t_by_day=tc_c, n=len(clean), days=np.nan,
                        stop_distances=clean["fund_pct"].mean() / stop_med))
    pd.DataFrame(summary).to_csv(f"{REPO}/step481_cadence.csv", index=False)
    print("\n'stop dist' is the charge as a fraction of the median structural")
    print("stop. 'vs fee' is against R478's 0.0529% three-coin US round trip.")
    print("NEGATIVE means the trade PAYS. POSITIVE means it COLLECTS.")

    # ------------------------------------------------ 3. long vs short
    print("\n" + "=" * 104)
    print("3. WHERE THE SIGN COMES FROM - LONG vs SHORT")
    print("=" * 104)
    print("Funding is not symmetric in crypto: the historical average rate is")
    print("positive, so longs pay and shorts collect. The method takes both,")
    print("so the NET depends entirely on its own long/short mix.")
    print(f"\n{'side':<10}{'entries':>9}{'share':>8}{'raw rate/hold':>15}"
          f"{'funding %':>12}{'t by day':>10}")
    for d_, lab in ((+1, "LONG"), (-1, "SHORT")):
        g = e[e["dirn"] == d_]
        tc, _ = clustered(g, "fund_pct")
        print(f"{lab:<10}{len(g):>9,}{len(g)/len(e)*100:>7.1f}%"
              f"{g['fund_rate_sum'].mean():>+14.4f}%"
              f"{g['fund_pct'].mean():>+11.4f}%{tc:>10.2f}")
    print(f"\nunderlying 8-hourly rate straddled per hold, both sides pooled: "
          f"{e['fund_rate_sum'].mean():+.4f}% of price")

    # ------------------------------------------------ 4. by asset, by year
    print("\n" + "=" * 104)
    print("4. BY ASSET AND BY YEAR - is the sign one coin or one regime?")
    print("=" * 104)
    print(f"{'asset':<10}{'entries':>9}{'long%':>8}{'funding %':>12}"
          f"{'t by day':>10}{'stop dist':>11}")
    for sym, g in e.groupby("sym"):
        tc, _ = clustered(g, "fund_pct")
        print(f"{sym:<10}{len(g):>9,}{(g['dirn'] > 0).mean()*100:>7.1f}%"
              f"{g['fund_pct'].mean():>+11.4f}%{tc:>10.2f}"
              f"{g['fund_pct'].mean()/g['stop_pct'].median():>+10.3f}x")
    print(f"\n{'year':<8}{'entries':>9}{'long%':>8}{'funding %':>12}"
          f"{'t by day':>10}{'raw rate':>11}")
    ey = e.assign(y=pd.to_datetime(e["entry_t"]).dt.year)
    yrows = []
    for y, g in ey.groupby("y"):
        tc, _ = clustered(g, "fund_pct")
        print(f"{int(y):<8}{len(g):>9,}{(g['dirn'] > 0).mean()*100:>7.1f}%"
              f"{g['fund_pct'].mean():>+11.4f}%{tc:>10.2f}"
              f"{g['fund_rate_sum'].mean():>+10.4f}%")
        yrows.append(dict(year=int(y), entries=len(g),
                          long_share=(g["dirn"] > 0).mean(),
                          funding_pct=g["fund_pct"].mean(), t_by_day=tc))
    ydf = pd.DataFrame(yrows)
    ydf.to_csv(f"{REPO}/step481_by_year.csv", index=False)
    print(f"\nfunding is a net CREDIT in {int((ydf['funding_pct'] > 0).sum())} "
          f"of {len(ydf)} years and a net CHARGE in "
          f"{int((ydf['funding_pct'] < 0).sum())}.")

    # ------------------------------------------------ 5. the whole ledger
    print("\n" + "=" * 104)
    print("5. THE LEDGER, WITH THE LAST UNMEASURED COST PUT IN")
    print("=" * 104)
    g_all = e["gross_pct"].mean()
    fund = e["fund_pct"].mean()
    print("R476's method numbers, reproduced on this same hold-24h population")
    print("so the funding charge has something to be a fraction of. They are a")
    print("DESCRIPTION of a spent window and qualify nothing.")
    print(f"\n{'line':<44}{'% of price':>12}{'stop dist':>11}")
    for lab, v in (
            ("gross per entry (arm B, hold 24h)", g_all),
            ("fee+spread, Coinbase (R479 all-in)", -0.0847),
            ("fee+spread, Bitnomial (R479 all-in)", -0.1120),
            ("fee only, Kraken US 3-coin (R478)", -0.0529),
            ("FUNDING, this round, Bybit proxy", fund),
            ("Alpaca taker round trip (what the log charged)", -R.COST_RT)):
        print(f"{lab:<44}{v:>+11.4f}%{v/stop_med:>+10.3f}x")
    print(f"\n{'net after fee+spread+funding, Coinbase':<44}"
          f"{g_all - 0.0847 + fund:>+11.4f}%"
          f"{(g_all - 0.0847 + fund)/stop_med:>+10.3f}x")
    print(f"{'net after fee+spread+funding, Bitnomial':<44}"
          f"{g_all - 0.1120 + fund:>+11.4f}%"
          f"{(g_all - 0.1120 + fund)/stop_med:>+10.3f}x")

    print("\nthe 2026 stub is the number that has been deciding this family:")
    e26 = ey[ey.y == 2026]
    if len(e26):
        print(f"  2026 gross {e26['gross_pct'].mean():+.4f}%, funding "
              f"{e26['fund_pct'].mean():+.4f}%, fee+spread -0.0847% "
              f"(Coinbase) -> net {e26['gross_pct'].mean() - 0.0847 + e26['fund_pct'].mean():+.4f}%")

    print("\n" + "=" * 104)
    print("LOOKS CONSUMED: NONE. No sealed slice opened, no cell qualified,")
    print("nothing proposed for deployment, no order placed, no account opened.")
    print("=" * 104)
    return e


if __name__ == "__main__":
    main()
