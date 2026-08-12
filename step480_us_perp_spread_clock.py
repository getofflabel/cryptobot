"""
step480_us_perp_spread_clock.py - ROUND 480

DOES THE US PERPETUAL BOOK GET WIDER AT SOME HOURS THAN OTHERS?
The 24-hour close of queue item 5.

Research only. READ-ONLY, and it does not even touch the network: it reads the
file the launch agent already recorded. No account, no key, no order, no money.
Nothing in the live bot is touched.

THIS ROUND CONSUMES NO LOOK
  Same standing as R479. It is a measurement of a recorded order book, not a
  backtest. It fits nothing, sweeps nothing, and reads no out-of-sample slice.
  No test window is touched, so no look is spent.

WHAT THE QUEUE ASKED FOR, AND WHAT WAS ACTUALLY LEFT
  Queue item 5 asked for the book "sampled across the 24h clock". R479 answered
  it on 3 of 24 UTC hours (06, 07, 08) and left this note:

    "WHAT IS LEFT: coverage was 3 of 24 UTC hours (06-08). A launch agent
     com.wallace.usperp-book-snap now records 6 min at :30 every hour into
     data_usperp_book.jsonl, so the next session runs
     step479_us_perp_spread_snap.py --report on full-clock data and closes
     this. Do not re-record; just read it."

  That report has been run and is quoted in RESEARCH_LOG.md R480. This file is
  the part the pooled report cannot do, and the part the item was actually
  about:

  1. R479's own recording is STILL IN THE FILE, and it is all in hours 06-08.
     Those three hours hold 39% of the 5,064 samples against the 12.5% the
     clock would give them. The pooled median is therefore weighted toward
     exactly the slice whose representativeness was the open question. Every
     number here is reported hour-equal-weighted as well as pooled.
  2. Was the 06-08 window representative? Answered by comparison, not assumed.
  3. Does the spread vary by hour at all, beyond what shuffling the clock
     labels would produce by luck? (R100's rule: beat a control, not zero.)
  4. Is R479's headline - Coinbase is the better venue - true hour by hour, or
     only on average?
  5. The account-size ceiling R479 found is a MEDIAN-hour number. The binding
     number for a real account is the WORST hour. That is computed here.

WHAT THIS ROUND CANNOT DO
  It cannot weight the cost by WHEN THE METHOD ACTUALLY ENTERS. R476 did not
  persist its entry timestamps, only its aggregates, so the hour distribution
  of the 71,073 entries is not on disk. Everything here is clock-weighted, i.e.
  it assumes entries are spread evenly over the 24 hours. If the hourly
  variation turns out to matter, that weighting becomes a queue item rather
  than something improvised here.

  One day of recording. Hour effects on a book are the kind of thing that is
  stable day to day (they track when humans and market makers are awake), but
  ONE DAY IS ONE DAY, and a single wide print in a thin hour moves that hour's
  numbers. Sample counts are printed beside every hour for that reason.
"""

import json
import os
import statistics
from collections import defaultdict

import numpy as np

REPO = os.path.dirname(os.path.abspath(__file__))
DATA = f"{REPO}/data_usperp_book.jsonl"

# Quoted from R478/R479, never re-derived here.
R478_FEE_RT = {"BTC": 0.0463, "ETH": 0.0314, "SOL": 0.0811}
R476_STOP = {"BTC": 0.185, "ETH": 0.239, "SOL": 0.341}
R476_SIGNAL_FULL = 0.1435
R476_SIGNAL_2026 = 0.0387
R479_HOURS = {"06", "07", "08"}      # the slice R479 actually read
POS_MULT = 4.13                      # R478: position notional at 1% risked

RNG = np.random.default_rng(4801)
N_SHUFFLE = 500


def load():
    rows = []
    with open(DATA) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return float("nan")
    i = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return vals[i]


def hourly_medians(rs, key="spread_pct"):
    """-> {hour: median}, {hour: n}"""
    by_h = defaultdict(list)
    for r in rs:
        by_h[r["ts"][11:13]].append(r[key])
    return {h: med(v) for h, v in by_h.items()}, {h: len(v) for h, v in by_h.items()}


def shuffle_control(rs, observed_sd):
    """Shuffle the hour labels. How often does luck alone produce this much
    hour-to-hour variation in the median spread? Sample sizes are preserved
    exactly, so an hour with 6 samples stays an hour with 6 samples."""
    vals = np.array([r["spread_pct"] for r in rs])
    hours = [r["ts"][11:13] for r in rs]
    sizes = defaultdict(int)
    for h in hours:
        sizes[h] += 1
    sizes = list(sizes.values())
    hits = 0
    for _ in range(N_SHUFFLE):
        perm = RNG.permutation(vals)
        i, meds = 0, []
        for n in sizes:
            meds.append(float(np.median(perm[i:i + n])))
            i += n
        if statistics.pstdev(meds) >= observed_sd:
            hits += 1
    return (hits + 1) / (N_SHUFFLE + 1)


def main():
    rows = load()
    rows = [r for r in rows if not r["venue"].startswith("kraken_INTL")]
    by_key = defaultdict(list)
    for r in rows:
        by_key[(r["venue"], r["coin"])].append(r)

    print(f"{len(rows)} US-venue samples in {os.path.basename(DATA)}")
    print(f"window: {min(r['ts'] for r in rows)}  ->  {max(r['ts'] for r in rows)}")

    # ---------------------------------------------------------------- 1
    print("\n" + "=" * 102)
    print("1. THE SAMPLE IS NOT FLAT ACROSS THE CLOCK, AND THAT MATTERS")
    print("R479's own recording is still in the file and all of it is in hours 06-08.")
    print("=" * 102)
    allh = defaultdict(int)
    for r in rows:
        allh[r["ts"][11:13]] += 1
    tot = sum(allh.values())
    r479n = sum(n for h, n in allh.items() if h in R479_HOURS)
    print(f"  hours 06-08 hold {r479n:,} of {tot:,} samples = {100*r479n/tot:.1f}%")
    print(f"  a flat clock would give those three hours {3/24*100:.1f}%")
    thin = sorted((n, h) for h, n in allh.items())[:4]
    print(f"  thinnest hours (all 6 US series pooled): " +
          ", ".join(f"{h}={n}" for n, h in thin))
    print("  -> every table below reports POOLED (as-recorded) and HOUR-EQUAL-WEIGHTED")
    print("     (mean of the 24 hourly medians). The second is the honest clock estimate.")

    # ---------------------------------------------------------------- 2
    print("\n" + "=" * 102)
    print("2. SPREAD BY UTC HOUR, IN % OF PRICE. median per hour.")
    print("=" * 102)
    hgrid = [f"{h:02d}" for h in range(24)]
    hm = {}
    for (venue, coin), rs in sorted(by_key.items()):
        m, n = hourly_medians(rs)
        hm[(venue, coin)] = (m, n)
        print(f"\n  {venue} {coin}   (n per hour in brackets)")
        for chunk in (hgrid[:12], hgrid[12:]):
            print("    " + "  ".join(f"{h}" for h in chunk))
            print("    " + "  ".join(f"{m.get(h, float('nan')):.4f}" for h in chunk))
            print("    " + "  ".join(f"[{n.get(h,0):2d}]  " for h in chunk))

    # ---------------------------------------------------------------- 3
    print("\n" + "=" * 102)
    print("3. IS THE HOUR-TO-HOUR VARIATION REAL, OR IS IT LUCK?")
    print("Control: shuffle the hour labels 500 times, preserving each hour's sample count.")
    print("p = share of shuffles whose spread-of-hourly-medians is at least as big as observed.")
    print("=" * 102)
    print(f"{'venue':22s} {'coin':4s} {'pooled':>8s} {'clock-wt':>9s} {'best hr':>9s} "
          f"{'worst hr':>9s} {'worst/best':>11s} {'sd':>7s} {'p':>7s}")
    clockwt = {}
    for (venue, coin), rs in sorted(by_key.items()):
        m, n = hm[(venue, coin)]
        meds = [m[h] for h in hgrid if h in m]
        pooled = med([r["spread_pct"] for r in rs])
        cw = statistics.fmean(meds)
        clockwt[(venue, coin)] = cw
        best_h = min(m, key=m.get)
        worst_h = max(m, key=m.get)
        sd = statistics.pstdev(meds)
        p = shuffle_control(rs, sd)
        print(f"{venue:22s} {coin:4s} {pooled:8.4f} {cw:9.4f} "
              f"{m[best_h]:6.4f}@{best_h} {m[worst_h]:6.4f}@{worst_h} "
              f"{m[worst_h]/max(m[best_h],1e-9):10.2f}x {sd:7.4f} {p:7.3f}")
    print("  'clock-wt' = mean of the 24 hourly medians: each hour counts once, as the clock has it.")
    print("  p < 0.05 means the book really is wider at some hours than others.")

    # ---------------------------------------------------------------- 4
    print("\n" + "=" * 102)
    print("4. WAS R479'S 06-08 WINDOW REPRESENTATIVE? (the actual open question)")
    print("=" * 102)
    print(f"{'venue':22s} {'coin':4s} {'06-08':>8s} {'other 21 hrs':>13s} {'ratio':>7s} "
          f"{'clock-wt':>9s} {'R479 err':>10s}")
    for (venue, coin), rs in sorted(by_key.items()):
        a = [r["spread_pct"] for r in rs if r["ts"][11:13] in R479_HOURS]
        b = [r["spread_pct"] for r in rs if r["ts"][11:13] not in R479_HOURS]
        ma, mb, cw = med(a), med(b), clockwt[(venue, coin)]
        print(f"{venue:22s} {coin:4s} {ma:8.4f} {mb:13.4f} {mb/max(ma,1e-9):6.2f}x "
              f"{cw:9.4f} {100*(ma-cw)/max(cw,1e-9):+9.1f}%")
    print("  'R479 err' = how far R479's published median sat from the full-clock truth,")
    print("  as a percentage of it. Negative = R479 was OPTIMISTIC (quoted a tighter book).")

    # ---------------------------------------------------------------- 5
    print("\n" + "=" * 102)
    print("5. THE TAIL BY HOUR. A wide print costs the same whenever it lands, but if the")
    print("tail concentrates in known hours it is avoidable rather than a cost of doing business.")
    print("=" * 102)
    print(f"{'venue':22s} {'coin':4s} {'p90 pooled':>11s} {'p99 pooled':>11s} "
          f"{'worst hr by p90':>16s} {'share of p90+ prints in 3 worst hrs':>36s}")
    for (venue, coin), rs in sorted(by_key.items()):
        sp = [r["spread_pct"] for r in rs]
        p90, p99 = pct(sp, 0.90), pct(sp, 0.99)
        by_h = defaultdict(list)
        for r in rs:
            by_h[r["ts"][11:13]].append(r["spread_pct"])
        h90 = {h: pct(v, 0.90) for h, v in by_h.items()}
        worst3 = sorted(h90, key=h90.get, reverse=True)[:3]
        wide = [r for r in rs if r["spread_pct"] >= p90]
        share = 100.0 * sum(1 for r in wide if r["ts"][11:13] in worst3) / max(len(wide), 1)
        print(f"{venue:22s} {coin:4s} {p90:11.4f} {p99:11.4f} "
              f"{max(h90.values()):8.4f}@{worst3[0]:2s}  {share:33.0f}%")
    print("  3 of 24 hours is 12.5% by luck. Well above that = the wide prints have a home.")

    # ---------------------------------------------------------------- 6
    print("\n" + "=" * 102)
    print("6. IS COINBASE THE BETTER VENUE EVERY HOUR, OR ONLY ON AVERAGE?")
    print("R479 concluded Coinbase wins on spread and depth. This checks it hour by hour.")
    print("=" * 102)
    print(f"{'coin':4s} {'hours coinbase tighter':>23s} {'median gap (bitnomial-coinbase)':>33s} "
          f"{'worst hour for coinbase':>25s}")
    for coin in ("BTC", "ETH", "SOL"):
        b = hm.get(("bitnomial_krakenUS", coin), ({}, {}))[0]
        c = hm.get(("coinbase_CDE", coin), ({}, {}))[0]
        both = [h for h in hgrid if h in b and h in c]
        wins = sum(1 for h in both if c[h] < b[h])
        gaps = [b[h] - c[h] for h in both]
        worst = min(both, key=lambda h: b[h] - c[h])
        print(f"{coin:4s} {wins:12d} / {len(both):<8d} {med(gaps):33.4f} "
              f"{'gap ' + format(b[worst]-c[worst], '+.4f') + ' @' + worst:>25s}")

    # ---------------------------------------------------------------- 7
    print("\n" + "=" * 102)
    print("7. THE ACCOUNT CEILING IN THE WORST HOUR, NOT THE MEDIAN ONE.")
    print("R479 quoted depth at the median. An account has to survive its thinnest hour.")
    print(f"equity = min(5-level bid, ask) notional / {POS_MULT} (R478: 1% risked = {POS_MULT}x equity)")
    print("=" * 102)
    print(f"{'venue':22s} {'coin':4s} {'median-hr equity $':>19s} {'worst-hr equity $':>18s} "
          f"{'worst hr':>9s} {'ratio':>7s}")
    for (venue, coin), rs in sorted(by_key.items()):
        by_h = defaultdict(list)
        for r in rs:
            by_h[r["ts"][11:13]].append(min(r["depth5_bid_notional"], r["depth5_ask_notional"]))
        hmed = {h: med(v) for h, v in by_h.items()}
        overall = med([min(r["depth5_bid_notional"], r["depth5_ask_notional"]) for r in rs])
        wh = min(hmed, key=hmed.get)
        print(f"{venue:22s} {coin:4s} {overall/POS_MULT:19,.0f} {hmed[wh]/POS_MULT:18,.0f} "
              f"{wh:>9s} {hmed[wh]/max(overall,1e-9):6.2f}x")

    # ---------------------------------------------------------------- 8
    print("\n" + "=" * 102)
    print("8. THE ALL-IN TABLE, CORRECTED TO THE FULL CLOCK.")
    print("Same construction as R479: all-in = R478 fee + one median spread. Only the")
    print("spread changes, from the 06-08 median to the hour-equal-weighted median.")
    print("=" * 102)
    print(f"{'venue':22s} {'coin':4s} {'fee':>7s} {'spread':>8s} {'ALL-IN':>8s} "
          f"{'in stops':>9s} {'vs full sig':>12s} {'vs 2026 sig':>12s}")
    for (venue, coin) in sorted(by_key):
        fee = R478_FEE_RT[coin]
        sp = clockwt[(venue, coin)]
        allin = fee + sp
        print(f"{venue:22s} {coin:4s} {fee:7.4f} {sp:8.4f} {allin:8.4f} "
              f"{allin/R476_STOP[coin]:8.2f}x {R476_SIGNAL_FULL-allin:+12.4f} "
              f"{R476_SIGNAL_2026-allin:+12.4f}")
    print("\n  'vs sig' = R476's gross signal minus all-in cost, in % of price per entry.")
    print("  Coinbase's fee is still carried at the Kraken US rate (queue item 7, unsourced).")
    print("  The spread column is measured on the venue named.")

    # ---------------------------------------------------------------- 9
    print("\n" + "=" * 102)
    print("9. THE HOLE AT 21:00 UTC. Not an outlier - a scheduled, DAILY, documented one.")
    print("=" * 102)
    print("  MEASURED: at 21:30-21:36 UTC the Coinbase book is a fraction of its own depth on")
    print("  all three coins at once, sustained across every sample in the window, and it is")
    print("  the widest hour of the clock for BTC and SOL. Bitnomial shows nothing at that hour.")
    print()
    print(f"  {'venue':22s} {'coin':4s} {'depth @21 $':>13s} {'depth other 23h $':>19s} {'@21 as share':>13s}")
    for (venue, coin), rs in sorted(by_key.items()):
        a = [min(r["depth5_bid_notional"], r["depth5_ask_notional"])
             for r in rs if r["ts"][11:13] == "21"]
        b = [min(r["depth5_bid_notional"], r["depth5_ask_notional"])
             for r in rs if r["ts"][11:13] != "21"]
        print(f"  {venue:22s} {coin:4s} {med(a):13,.0f} {med(b):19,.0f} "
              f"{100*med(a)/max(med(b),1e-9):12.0f}%")
    print()
    print("  MECHANISM, PRIMARY-SOURCED (docs.cdp.coinbase.com/derivatives/introduction/")
    print("  market-hours, read 2026-08-12): Coinbase Derivatives runs 24x7 for 24x7-enabled")
    print("  products, halting only Fridays 16:00-16:50 CT. But NON-24x7 PARTICIPANTS take")
    print("  'a one-hour break each day from 4:00 PM - 5:00 PM CT'. That is 21:00-22:00 UTC,")
    print("  exactly the hour measured. The market stays OPEN; a large share of who quotes it")
    print("  goes home. 2026-08-11 was a TUESDAY, so the weekly Friday halt cannot explain it.")
    print()
    print("  WHY IT MATTERS MORE THAN A COST LINE: the method holds 24 hours, so EVERY")
    print("  position spans this hour. If a stop triggers inside it, the book that has to")
    print("  absorb the exit is the thin one. R479's headline - Coinbase supports ~$300k of")
    print("  equity - is a 23-hour number. The exitable-at-all-times ceiling is the 21:00 one.")
    print()
    print(f"  {'venue':22s} {'coin':4s} {'R479 ceiling $':>15s} {'21:00 ceiling $':>16s} {'cut':>7s}")
    for (venue, coin), rs in sorted(by_key.items()):
        a = med([min(r["depth5_bid_notional"], r["depth5_ask_notional"])
                 for r in rs if r["ts"][11:13] == "21"]) / POS_MULT
        b = med([min(r["depth5_bid_notional"], r["depth5_ask_notional"])
                 for r in rs if r["ts"][11:13] != "21"]) / POS_MULT
        print(f"  {venue:22s} {coin:4s} {b:15,.0f} {a:16,.0f} {a/max(b,1e-9):6.2f}x")
    print()
    print("  HONEST LIMIT: the MECHANISM is documented and recurs daily, so it will be there")
    print("  tomorrow. The MAGNITUDE is one day's observation of that hour. Treat the size of")
    print("  the hole as indicative and the existence of it as established.")


if __name__ == "__main__":
    main()
