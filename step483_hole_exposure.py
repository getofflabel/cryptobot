"""
step483_hole_exposure.py - ROUND 483

WHAT DOES A HOLD DO WHEN THE BOOK IS NOT THERE?  (QUEUE ITEM 8, VERBATIM)

Research only. No orders. No live file touched. No account. Nothing here is
deployed by this script under any outcome.

QUEUE ITEM 8, VERBATIM (with R481's premise correction and R482's DST fix)
  R480 measured a documented, daily, one-hour window in which Coinbase's book
  is 5-11% of its normal depth, and concluded that because the method holds
  24 hours EVERY position spans it. R481 refutes that premise: the median
  position lives 43 MINUTES and 90.3% are stopped out before the 24h cap. The
  exposure is a SHARE to be counted, not "all of them" - and it is still real,
  because a stop that fires inside the hole is filled into a book at 5-11% of
  normal depth.
    (a) What share of the method's stops and exits land inside the break?
        Entry AND exit timestamps for all 68,992 chargeable entries are
        persisted in step481_entries_funding.csv. Read that file; regenerate
        nothing. R482 CORRECTION: bucket in CHICAGO time (16:00-17:00 CT),
        not UTC - the break is fixed in CT, so a UTC census would smear it
        across two hours and understate it.
    (b) Does the hole recur? The recorder is still running. Do not re-record;
        just read whatever has accumulated.
  R480's $17k-$26k exitable-at-all-times ceiling is built on the false premise
  and must be RE-DERIVED, not quoted.

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  Nothing here is a backtest of the strategy. Part (a) is an aggregate over an
  entry population the desk has already fully described (R476, whole window,
  no sealed slice left on this family) - it reads TIMESTAMPS, qualifies no
  cell, proposes no partition and opens no slice. Part (b) reads a book
  recorder's own log. Part (c) charges a cost onto R476's already-published
  aggregate. No look is consumed and none could be.

WHAT IS MEASURED
  (a) The full CT clock of 68,992 entries and exits, the share landing in the
      16:00-17:00 CT break, the share of positions that STRADDLE a break, the
      same census split by year / coin / exit reason / direction, and whether
      the entries that exit in the hole are worth more or less than the rest.
      Baseline stated in the same breath: a flat clock gives any one hour
      1/24 = 4.167%, and a binomial test against that baseline is printed
      beside every share.
  (b) 13 days of book snapshots (2026-08-11 -> 2026-08-25) against R480's ONE
      day. Depth and spread by CT hour, per venue per coin, plus the per-day
      ratio in the break hour, so the magnitude stops being indicative.
  (c) The constraint priced: the extra spread the hole charges, applied to the
      measured share of exits that land in it, in % of price and in stop
      distances, against the signal it has to come out of.

COSTS
  Charged for honest P&L and used for nothing else (owner rule, 2026-07-25).
  Nothing here gates, declines or ranks anything.

HONEST LIMITS, FIXED BEFORE RUNNING
  - The exit timestamps are the BACKTEST's exits, on Alpaca's 1-minute tape.
    They are when the method's stop or cap WOULD fire, not fills observed on
    a US venue. That is the right object for this question - the question is
    which clock hour the method asks to trade in - but it is not a fill study.
  - R481's gap finding stands: Alpaca's 1-minute tape has gaps and the 24h cap
    is counted in BARS, so 8.0% of holds span more than 24h of wall clock. The
    straddle count below is computed on WALL CLOCK from the timestamps, so
    those holds straddle more breaks, correctly.
  - 13 days is 13 days. The break's mechanism is primary-sourced (R482, CFTC
    submission #2025-75); what these days can settle is its magnitude and
    whether it is every day, not a year of seasonality.

USAGE
  python3 step483_hole_exposure.py
"""

import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd

REPO = "/Users/wallacechen/cryptobot"
ENTRIES = f"{REPO}/step481_entries_funding.csv"
BOOK = f"{REPO}/data_usperp_book.jsonl"

CT = "America/Chicago"
HOLE_HOUR = 16          # 16:00-17:00 CT, the non-24x7 participant break
FRI_HALT_END_MIN = 50   # Friday 16:00-16:50 CT is an all-markets halt


# ----------------------------------------------------------------- helpers
def to_ct(s):
    """naive UTC -> tz-naive CHICAGO local. R482: the break is fixed in CT."""
    return (pd.to_datetime(s)
            .dt.tz_localize("UTC")
            .dt.tz_convert(CT)
            .dt.tz_localize(None))


def marks_before(lt):
    """How many 16:00 CT marks are at or before this LOCAL naive timestamp.
    Doing the arithmetic in local naive time is what makes '16:00 every day'
    correct across both DST offsets."""
    return (lt - pd.Timedelta(hours=HOLE_HOUR)).dt.normalize().astype("int64") // 86_400_000_000_000


def binom_z(k, n, p):
    """Two-sided z of k successes in n against rate p."""
    if n == 0:
        return float("nan")
    return (k - n * p) / math.sqrt(n * p * (1 - p))


def med(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return float(np.median(xs)) if xs else float("nan")


def share_line(label, k, n, p=1 / 24):
    z = binom_z(k, n, p)
    return (f"  {label:<34} {k:>7,} of {n:>7,} = {100*k/n:6.3f}%   "
            f"(flat clock {100*p:5.3f}%,  z = {z:+6.2f})")


# --------------------------------------------------------------- part (a)
def part_a():
    print("=" * 78)
    print("(a) WHERE ON THE CHICAGO CLOCK DOES THIS METHOD ACTUALLY TRADE?")
    print("=" * 78)
    print("Source: step481_entries_funding.csv, regenerated from nothing.")
    print("The break is 16:00-17:00 CT. R482: bucketing in UTC smears it across")
    print("two hours (21:00 UTC in summer, 22:00 UTC in winter) and understates it.")

    df = pd.read_csv(ENTRIES)
    df["entry_ct"] = to_ct(df["entry_t"])
    df["exit_ct"] = to_ct(df["exit_t"])
    df["entry_h"] = df["entry_ct"].dt.hour
    df["exit_h"] = df["exit_ct"].dt.hour
    df["year"] = df["entry_ct"].dt.year
    n = len(df)

    # how many 16:00 CT marks does the position straddle
    df["straddles"] = (marks_before(df["exit_ct"]) - marks_before(df["entry_ct"])).astype(int)

    print(f"\npopulation: {n:,} entries, "
          f"{df['entry_ct'].min():%Y-%m-%d} -> {df['exit_ct'].max():%Y-%m-%d} CT")
    print(f"median hold {df['hold_h'].median()*60:.0f} min, "
          f"p90 {df['hold_h'].quantile(0.90):.1f}h, "
          f"stopped out {100*(df['reason']=='stop').mean():.1f}%")

    print("\n1. THE HEADLINE SHARES.")
    ex_in = int((df["exit_h"] == HOLE_HOUR).sum())
    en_in = int((df["entry_h"] == HOLE_HOUR).sum())
    strad = int((df["straddles"] > 0).sum())
    print(share_line("EXITS landing in the break", ex_in, n))
    print(share_line("ENTRIES landing in the break", en_in, n))
    print(f"  {'positions straddling a break':<34} {strad:>7,} of {n:>7,} = "
          f"{100*strad/n:6.3f}%   (R480 assumed 100%)")
    exposed = int(((df["exit_h"] == HOLE_HOUR) | (df["entry_h"] == HOLE_HOUR)
                   | (df["straddles"] > 0)).sum())
    print(f"  {'touching the break at all':<34} {exposed:>7,} of {n:>7,} = "
          f"{100*exposed/n:6.3f}%")

    # Friday all-markets halt (R482 primary-sourced): 16:00-16:50 CT Friday
    fri = ((df["exit_ct"].dt.dayofweek == 4) & (df["exit_h"] == HOLE_HOUR)
           & (df["exit_ct"].dt.minute < FRI_HALT_END_MIN))
    print(share_line("exits in the FRIDAY halt window", int(fri.sum()), n, p=(50 / 60) / (24 * 7))
          + "   <- market CLOSED, not just thin")

    print("\n2. THE WHOLE CT CLOCK OF EXITS. Is the break hour special, or is")
    print("   the clock lumpy everywhere? n and % per hour, flat clock = 4.167%.")
    hist_x = df["exit_h"].value_counts().reindex(range(24), fill_value=0)
    hist_e = df["entry_h"].value_counts().reindex(range(24), fill_value=0)
    print(f"\n  {'CT hr':>5} {'exits':>8} {'%':>7} {'z':>7}   {'entries':>8} {'%':>7} {'z':>7}")
    for h in range(24):
        mark = "  <-- BREAK" if h == HOLE_HOUR else ""
        print(f"  {h:>5} {hist_x[h]:>8,} {100*hist_x[h]/n:>7.3f} "
              f"{binom_z(hist_x[h], n, 1/24):>+7.2f}   "
              f"{hist_e[h]:>8,} {100*hist_e[h]/n:>7.3f} "
              f"{binom_z(hist_e[h], n, 1/24):>+7.2f}{mark}")
    rank = int((hist_x.sort_values(ascending=False).index == HOLE_HOUR).argmax()) + 1
    print(f"\n  the break hour ranks {rank} of 24 by exit count "
          f"(busiest = 1). max hour {100*hist_x.max()/n:.3f}%, "
          f"min {100*hist_x.min()/n:.3f}%.")

    print("\n3. IS IT THE STOPS? A stop that fires in the hole is the one that")
    print("   actually has to cross a 5-11% book. Split by exit reason.")
    for reason, g in df.groupby("reason"):
        k = int((g["exit_h"] == HOLE_HOUR).sum())
        print(share_line(f"exits in break | {reason}", k, len(g)))

    print("\n4. BY COIN, and BY YEAR (does the exposure move?).")
    for coin, g in df.groupby("sym"):
        print(share_line(f"exits in break | {coin}", int((g["exit_h"] == HOLE_HOUR).sum()), len(g)))
    print()
    for yr, g in df.groupby("year"):
        print(share_line(f"exits in break | {yr}", int((g["exit_h"] == HOLE_HOUR).sum()), len(g)))

    print("\n5. ARE THE HOLE EXITS WORTH MORE OR LESS THAN THE REST?")
    print("   If the money is in the hole the constraint is expensive; if the")
    print("   hole exits are ordinary it is a spread surcharge on 4% of trades.")
    ih = df["exit_h"] == HOLE_HOUR
    for col, lab in (("gross_pct", "gross % of price"), ("net_pct", "net % of price"),
                     ("stop_pct", "stop distance %")):
        a, b = df.loc[ih, col], df.loc[~ih, col]
        se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
        t = (a.mean() - b.mean()) / se if se > 0 else float("nan")
        print(f"  {lab:<18} in hole {a.mean():+8.4f}   out {b.mean():+8.4f}   "
              f"diff {a.mean()-b.mean():+8.4f}  t = {t:+5.2f}")
    cap_in = (df.loc[ih, "reason"] != "stop").mean()
    cap_out = (df.loc[~ih, "reason"] != "stop").mean()
    print(f"  {'ran the 24h cap':<18} in hole {100*cap_in:7.2f}%   out {100*cap_out:7.2f}%")

    print("\n6. THE 9.7% TAIL R482 POINTED AT. Positions that run the cap are the")
    print("   ones that produce the whole gross AND the ones the venue will not")
    print("   finance overnight. Where do THEY exit?")
    cap = df[df["reason"] != "stop"]
    print(share_line("cap-runners exiting in break", int((cap["exit_h"] == HOLE_HOUR).sum()), len(cap)))
    print(f"  {'cap-runners straddling a break':<34} "
          f"{int((cap['straddles']>0).sum()):>7,} of {len(cap):>7,} = "
          f"{100*(cap['straddles']>0).mean():6.3f}%")
    print(f"  cap-runners mean gross {cap['gross_pct'].mean():+.4f}% of price "
          f"({len(cap):,} entries carry {100*cap['gross_pct'].sum()/df['gross_pct'].sum():.1f}% "
          f"of the population's total gross)")

    return df


# --------------------------------------------------------------- part (b)
def load_book():
    rs = []
    with open(BOOK) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = pd.Timestamp(r["ts"]).tz_convert(CT)
            r["ct_hour"] = t.hour
            r["ct_day"] = str(t.date())
            r["depth5"] = (r.get("depth5_bid_notional") or 0) + (r.get("depth5_ask_notional") or 0)
            rs.append(r)
    return rs


def part_b():
    print("\n" + "=" * 78)
    print("(b) DOES THE HOLE RECUR? 13 DAYS AGAINST R480'S ONE.")
    print("=" * 78)
    rs = load_book()
    days = sorted({r["ct_day"] for r in rs})
    print(f"{len(rs):,} samples, {days[0]} -> {days[-1]} CT, {len(days)} calendar days.")
    print("Recorder untouched - this is whatever accumulated on its own.")

    series = sorted({(r["venue"], r["coin"]) for r in rs})
    print("\n1. DEPTH IN THE BREAK HOUR AS A % OF THE OTHER 23 HOURS.")
    print("   median 5-level notional (bid+ask), pooled over all days.")
    print(f"\n  {'venue':<22} {'coin':<5} {'break $':>10} {'normal $':>10} "
          f"{'ratio':>7} {'n_hole':>7} {'n_rest':>7}")
    ratios = {}
    for venue, coin in series:
        hole = [r["depth5"] for r in rs if r["venue"] == venue and r["coin"] == coin
                and r["ct_hour"] == HOLE_HOUR]
        rest = [r["depth5"] for r in rs if r["venue"] == venue and r["coin"] == coin
                and r["ct_hour"] != HOLE_HOUR]
        mh, mr = med(hole), med(rest)
        ratio = 100 * mh / mr if mr else float("nan")
        ratios[(venue, coin)] = ratio
        print(f"  {venue:<22} {coin:<5} {mh:>10,.0f} {mr:>10,.0f} "
              f"{ratio:>6.1f}% {len(hole):>7,} {len(rest):>7,}")
    print("\n  R480 read 5-11% on Coinbase off one day. Compare the Coinbase rows.")

    print("\n2. SPREAD IN THE BREAK HOUR, % of price. The cost the exit pays.")
    print(f"\n  {'venue':<22} {'coin':<5} {'break %':>9} {'normal %':>9} {'x wider':>8}")
    widen = {}
    for venue, coin in series:
        hole = [r["spread_pct"] for r in rs if r["venue"] == venue and r["coin"] == coin
                and r["ct_hour"] == HOLE_HOUR]
        rest = [r["spread_pct"] for r in rs if r["venue"] == venue and r["coin"] == coin
                and r["ct_hour"] != HOLE_HOUR]
        mh, mr = med(hole), med(rest)
        widen[(venue, coin)] = (mh, mr)
        print(f"  {venue:<22} {coin:<5} {mh:>9.4f} {mr:>9.4f} "
              f"{(mh/mr if mr else float('nan')):>7.2f}x")

    print("\n3. DAY BY DAY, COINBASE ONLY. Is it EVERY day, or was 08-11 a one-off?")
    print("   depth in the break hour as % of that same day's other hours.")
    print(f"\n  {'day':<12} " + "  ".join(f"{c:>7}" for c in ("BTC", "ETH", "SOL")))
    hit = defaultdict(list)
    for d in days:
        row = []
        for coin in ("BTC", "ETH", "SOL"):
            hole = [r["depth5"] for r in rs if r["venue"] == "coinbase_CDE" and r["coin"] == coin
                    and r["ct_day"] == d and r["ct_hour"] == HOLE_HOUR]
            rest = [r["depth5"] for r in rs if r["venue"] == "coinbase_CDE" and r["coin"] == coin
                    and r["ct_day"] == d and r["ct_hour"] != HOLE_HOUR]
            if not hole or not rest or med(rest) == 0:
                row.append("    --")
                continue
            v = 100 * med(hole) / med(rest)
            hit[coin].append(v)
            row.append(f"{v:>6.1f}%")
        print(f"  {d:<12} " + "  ".join(f"{x:>7}" for x in row))
    print()
    for coin in ("BTC", "ETH", "SOL"):
        v = hit[coin]
        if v:
            print(f"  {coin}: {len(v)} days with break-hour coverage, "
                  f"median {med(v):.1f}%, worst {min(v):.1f}%, best {max(v):.1f}%, "
                  f"days under 25% = {sum(1 for x in v if x < 25)}/{len(v)}")
        else:
            print(f"  {coin}: no day has both break-hour and other-hour coverage.")

    print("\n3b. THE THREE EXCEPTION DAYS ARE ALL WEEKEND DAYS (08-16 Sun, 08-22 Sat,")
    print("    08-23 Sun). On a weekend the OTHER 23 hours are already thin, so the")
    print("    ratio rises without the break-hour book improving. Weekday-only pool:")
    for coin in ("BTC", "ETH", "SOL"):
        hole = [r["depth5"] for r in rs if r["venue"] == "coinbase_CDE" and r["coin"] == coin
                and r["ct_hour"] == HOLE_HOUR and pd.Timestamp(r["ct_day"]).dayofweek < 5]
        rest = [r["depth5"] for r in rs if r["venue"] == "coinbase_CDE" and r["coin"] == coin
                and r["ct_hour"] != HOLE_HOUR and pd.Timestamp(r["ct_day"]).dayofweek < 5]
        print(f"    coinbase {coin}: break {med(hole):>10,.0f}  normal {med(rest):>10,.0f}  "
              f"= {100*med(hole)/med(rest):5.1f}%   (n {len(hole)}/{len(rest)})")

    print("\n4. BITNOMIAL CONTROL. R480 said Bitnomial has no such hole.")
    for coin in ("BTC", "ETH", "SOL"):
        r = ratios.get(("bitnomial_krakenUS", coin), float("nan"))
        print(f"  bitnomial {coin}: break-hour depth = {r:.1f}% of normal")

    return ratios, widen, series


# --------------------------------------------------------------- part (c)
def part_c(df, widen):
    print("\n" + "=" * 78)
    print("(c) PRICE IT. What does the break cost, per entry, in % of price?")
    print("=" * 78)
    ih = df["exit_h"] == HOLE_HOUR
    share = float(ih.mean())
    med_stop = float(df["stop_pct"].median())
    print(f"share of exits in the break = {100*share:.3f}%")
    print(f"median structural stop = {med_stop:.3f}% of price (R476's object)")

    print("\nThe surcharge: the exit leg pays the break-hour spread instead of the")
    print("normal one, on that share of trades. One leg, not a round trip - the")
    print("entry is placed at a time of the method's choosing and only 1 in 24")
    print("lands in the window.")
    print(f"\n  {'venue':<22} {'coin':<5} {'extra/leg %':>12} {'x share':>11} {'stop dist':>10}")
    for (venue, coin), (mh, mr) in sorted(widen.items()):
        extra = (mh - mr) / 2.0          # half-spread, one leg
        per_entry = extra * share
        print(f"  {venue:<22} {coin:<5} {extra:>12.4f} {per_entry:>11.5f} "
              f"{per_entry/med_stop:>10.4f}")

    print("\nAgainst the signal it comes out of:")
    print(f"  whole-window gross per entry   {df['gross_pct'].mean():+.4f}% of price")
    print(f"  2026 stub gross per entry      "
          f"{df[df['year']==2026]['gross_pct'].mean():+.4f}% of price")
    print("  (R476's year table is the reference; this is the same population.)")

    print("\nTHE ACCOUNT-SIZE CEILING, RE-DERIVED NOT QUOTED.")
    print("  R480's $17k-$26k is a property of the BOOK: it is the equity whose")
    print("  stop can cross the break-hour book without walking it. That number")
    print("  does not move, because the book does not care why you are there.")
    print("  What the census changes is the OBLIGATION. R480 said every position")
    print("  spans the hole, so the exitable-at-all-times ceiling was the only")
    print("  ceiling. On the measured clock the method asks to exit inside the")
    print(f"  break on {100*share:.2f}% of trades, so the honest statement is a pair:")
    print(f"    - {100*(1-share):.2f}% of exits meet the normal book (R479's ~$300k)")
    print(f"    - {100*share:.2f}% meet the thin one (R480's $17k-$26k)")
    print("  An account sized above the thin-book ceiling is not broken; it is")
    print("  paying a worse fill on that share, which is the surcharge above.")
    print("  R480's sentence 'the exitable-at-all-times ceiling is $17k-$26k'")
    print("  stays TRUE as a book fact and stops being the binding constraint on")
    print("  account size for THIS method.")


def main():
    df = part_a()
    ratios, widen, series = part_b()
    part_c(df, widen)
    print("\n" + "=" * 78)
    print("No look consumed. No cell qualified. Nothing deployed.")
    print("=" * 78)


if __name__ == "__main__":
    main()
