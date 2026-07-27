"""
step410_overnight.py - ROUND 410, JOB 2 PART 4
THE WINDOW THAT ACTUALLY PAYS, AND THE COST NUMBER THAT WAS WRONG.

Research only. No orders of any kind. Nothing live is touched. There is no
paper position behind any number in this file.

WHY THIS FILE EXISTS
  Job 2 asked whether a high-volatility single name has a lit session worth
  trading, since the index does not. Part 3 answered that: no. Not one name
  in the AI basket has a regular-session drift with a t-statistic even
  above 1.1. Several are negative.

  But the same measurement turned up something the desk had written off.
  The playbook says overnight drift on the index is "real, t=4.4, but
  ~0.033%/night gross does not clear one ETF round trip", where the round
  trip was taken to be 4 basis points. That 4 bps came from a crypto-shaped
  cost model, 1 bp of fee plus 1 bp of slippage on each side. On US
  equities at Alpaca there is NO commission. The only cost is the spread
  you cross. Measured from real national best bid and offer, sampled at
  fourteen regular-hours moments spread across 2016 to 2026, SPY's round
  trip is 0.0035% of price at the 75th percentile, not 0.04%. That is an
  order of magnitude apart, and it flips the verdict.

  So this file tests the overnight hold properly, on the AI names where the
  drift is several times larger than the index's.

WHAT THE TRADE IS
  Buy with a market order in the last minutes of the regular session. Sell
  with a market order at the next regular open. Both inside the hours
  Alpaca accepts market orders. One round trip per night held.

WHAT CANNOT BE DONE, SAID PLAINLY
  This position has NO STOP. The market is shut for the entire holding
  period, so there is nothing for a stop order to do. A stop cannot survive
  the gap here because the gap IS the trade. That means the sizing rule
  used everywhere else on this desk - size = dollars risked divided by the
  stop distance - has no stop to divide by. Instead the size has to come
  from the distribution of overnight losses themselves, which this file
  measures, and the leverage that results is far lower than an intraday
  setup would allow. That is a real limitation, not a footnote.

PROTOCOL
  First 60% of sessions to choose on. Middle 20% read once. Final 20%
  never opened.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step410_lib import (REPO, load_daily, load_5m_rth, split_60_20_20,
                         costs_table, tstat)

NAMES = ["NVDA", "AMD", "AVGO", "MU", "MSFT", "GOOGL", "META", "AMZN",
         "TSLA", "SMH", "SPY", "QQQ"]
COST_STRESS = [1, 2, 3, 5]     # multiples of the measured quoted spread


def section(t):
    print("\n" + "=" * 84)
    print(t)
    print("=" * 84)


def overnight_returns(d):
    """Gross price move from one session's close to the next session's open,
    as a percentage of price. Index i is the night AFTER session i."""
    o, c = d["open"].to_numpy(), d["close"].to_numpy()
    r = np.full(len(d), np.nan)
    r[:-1] = (o[1:] - c[:-1]) / c[:-1] * 100.0
    return r


def main():
    costs = costs_table()

    # ================================================================== 1
    section("1. THE OVERNIGHT HOLD, AFTER REAL MEASURED COSTS")
    print("Every night, buy at the close and sell at the next open, both market")
    print("orders. Choosing slice only. All figures are PRICE moves, % of price.")
    print("The cost column is one full round trip, measured from real quotes.")
    print(f"\n  {'name':>6}{'nights':>8}{'gross%':>9}{'cost%':>8}{'net%':>9}"
          f"{'t':>7}{'win%':>7}{'x cost':>8}{'ann.net':>10}  verdict")
    rows = []
    for sym in NAMES:
        try:
            d = load_daily(sym)
        except FileNotFoundError:
            continue
        i_tr, i_va = split_60_20_20(len(d))
        r = overnight_returns(d)[:i_tr]
        r = r[~np.isnan(r)]
        cost = costs[sym]["p75"]
        net = r - cost
        # compounded, per year: about 252 nights
        ann = (np.exp(np.log1p(net / 100.0).mean() * 252) - 1) * 100.0
        ratio = r.mean() / cost
        t = tstat(net)
        ok = (t >= 2.0) and (ratio >= 5.0)
        print(f"  {sym:>6}{len(r):>8,}{r.mean():>9.4f}{cost:>8.4f}"
              f"{net.mean():>9.4f}{t:>7.2f}{100*(net>0).mean():>7.1f}"
              f"{ratio:>8.1f}{ann:>9.1f}%  "
              f"{'clears both bars' if ok else 'fails'}")
        rows.append(dict(symbol=sym, n_nights=len(r), gross_pct=r.mean(),
                         cost_pct=cost, net_pct=net.mean(), t=t,
                         win_pct=100 * (net > 0).mean(),
                         gross_over_cost=ratio, ann_net_pct=ann,
                         sd_pct=r.std(ddof=1),
                         p01=np.percentile(r, 1), p05=np.percentile(r, 5),
                         worst=r.min(), verdict="clears" if ok else "fails"))
    tab = pd.DataFrame(rows)
    tab.to_csv(f"{REPO}/step410_table_overnight.csv", index=False)
    print("\n  'ann.net' compounds the net nightly move over 252 nights. It is a")
    print("  price-move figure at 1x size, not a change in the value of a levered")
    print("  position, and it ignores that the money is idle all day.")

    # ================================================================== 2
    section("2. HOW WRONG DOES THE COST HAVE TO BE BEFORE THIS DIES?")
    print("The measured cost is the quoted spread. A market order in real size")
    print("can pay more than the quoted spread when it eats past the top of the")
    print("book. So: multiply the measured cost and see what survives.")
    print("The last column is the useful one: how many times worse than the")
    print("measured spread the true cost could be before the trade stops")
    print("clearing the five-times-cost bar.")
    print(f"\n  {'name':>6}" + "".join(f"{'net at x'+str(m):>13}" for m in COST_STRESS)
          + f"{'breaks at':>12}")
    for r in tab.itertuples():
        line = f"  {r.symbol:>6}"
        for m in COST_STRESS:
            line += f"{r.gross_pct - r.cost_pct * m:>12.3f}%"
        line += f"{r.gross_over_cost / 5.0:>11.1f}x"
        print(line)
    print("\n  So NVDA tolerates roughly twice the measured spread and no more.")
    print("  That is a thin margin for an assumption, and it is the single")
    print("  number most worth checking against real fills if this ever runs.")

    # ================================================================== 3
    section("3. THERE IS NO STOP. WHAT DOES THAT COST IN SIZE?")
    print("The market is shut for the whole hold, so no stop order can act. The")
    print("sizing rule has to use the distribution of overnight losses instead.")
    print("Below: the 1-in-100 bad night and the worst night in the choosing")
    print("slice, and the size a 1% and 2% risk budget buys against each.")
    print("Compare these with an intraday 5-minute stop, which on these names")
    print("sits a small fraction of a percent away and buys many times the size.")
    print(f"\n  {'name':>6}{'1-in-100 night':>16}{'1% risk':>10}{'2% risk':>10}"
          f"{'worst night':>14}{'1% risk':>10}{'2% risk':>10}")
    for r in tab.itertuples():
        d1, d2 = abs(r.p01), abs(r.worst)
        print(f"  {r.symbol:>6}{d1:>15.2f}%{1.0/d1:>9.1f}x{2.0/d1:>9.1f}x"
              f"{d2:>13.2f}%{1.0/d2:>9.1f}x{2.0/d2:>9.1f}x")
    print("\n  Leverage is the OUTPUT of the risk budget divided by the distance")
    print("  price can travel against the position. Against a real overnight tail")
    print("  these numbers are around 1x, i.e. the position is about the size of")
    print("  the account. This is NOT a high-leverage setup and cannot be made")
    print("  into one, because there is no stop to tighten.")

    # ================================================================== 4
    section("4. DOES THE DRIFT SURVIVE BEING SPLIT IN HALF? (like-for-like)")
    print("Round 400's rule: comparing a filtered run to an unfiltered run does")
    print("NOT test a filter, because removing a trade frees the slot for a")
    print("different one. So here the SAME population of nights is partitioned,")
    print("never filtered - every night lands in exactly one half, and the two")
    print("halves add back up to the whole. Trade counts are reported so the")
    print("partition can be checked to be exhaustive.")
    parts = []
    for sym in NAMES:
        try:
            d = load_daily(sym)
        except FileNotFoundError:
            continue
        i_tr, _ = split_60_20_20(len(d))
        t = d.iloc[:i_tr].reset_index(drop=True)
        r = overnight_returns(t)
        cost = costs[sym]["p75"]
        ok = ~np.isnan(r)
        # partition A: was the session that just ended an up day or a down day?
        sess_up = (t["close"].to_numpy() > t["open"].to_numpy())
        # partition B: first half of the sample against the second half
        half = np.arange(len(t)) < (len(t) // 2)
        for pname, mask, la, lb in (
                ("day just ended UP / DOWN", sess_up, "after an up day", "after a down day"),
                ("first half / second half", half, "first half", "second half")):
            a = r[ok & mask] - cost
            b = r[ok & ~mask] - cost
            if len(a) < 30 or len(b) < 30:
                continue
            parts.append(dict(symbol=sym, partition=pname,
                              a_label=la, a_n=len(a), a_mean=a.mean(), a_t=tstat(a),
                              b_label=lb, b_n=len(b), b_mean=b.mean(), b_t=tstat(b),
                              total_n=len(a) + len(b),
                              whole_n=int(ok.sum())))
    pdf = pd.DataFrame(parts)
    pdf.to_csv(f"{REPO}/step410_table_overnight_partitions.csv", index=False)
    for pname in pdf["partition"].unique():
        s = pdf[pdf.partition == pname]
        print(f"\n  partition: {pname}")
        print(f"    {'name':>6}{'half A n':>10}{'A net%':>9}{'A t':>7}"
              f"{'half B n':>10}{'B net%':>9}{'B t':>7}{'A+B = all':>12}")
        for r in s.itertuples():
            match = "yes" if r.total_n == r.whole_n else f"NO {r.total_n}/{r.whole_n}"
            print(f"    {r.symbol:>6}{r.a_n:>10,}{r.a_mean:>9.4f}{r.a_t:>7.2f}"
                  f"{r.b_n:>10,}{r.b_mean:>9.4f}{r.b_t:>7.2f}{match:>12}")
        print(f"    A = {s.iloc[0].a_label}, B = {s.iloc[0].b_label}")

    # ================================================================== 5
    section("5. READ THE MIDDLE SLICE ONCE")
    print("No setting was chosen here - the trade is 'hold every night', which")
    print("has nothing to tune. So this is a straight out-of-sample read of the")
    print("same rule on bars the choosing slice never saw. The final 20% of the")
    print("bars is NOT opened.")
    print(f"\n  {'name':>6}{'nights':>8}{'net%':>9}{'t':>7}{'x cost':>8}"
          f"{'ann.net':>10}   choosing-slice net% for comparison")
    vrows = []
    for sym in NAMES:
        try:
            d = load_daily(sym)
        except FileNotFoundError:
            continue
        i_tr, i_va = split_60_20_20(len(d))
        r = overnight_returns(d)[i_tr:i_va]
        r = r[~np.isnan(r)]
        cost = costs[sym]["p75"]
        net = r - cost
        ann = (np.exp(np.log1p(net / 100.0).mean() * 252) - 1) * 100.0
        tr_net = float(tab[tab.symbol == sym].net_pct.iloc[0])
        print(f"  {sym:>6}{len(r):>8,}{net.mean():>9.4f}{tstat(net):>7.2f}"
              f"{r.mean()/cost:>8.1f}{ann:>9.1f}%   {tr_net:+.4f}")
        vrows.append(dict(symbol=sym, n_nights=len(r), net_pct=net.mean(),
                          t=tstat(net), over_cost=r.mean() / cost,
                          ann_net_pct=ann, train_net_pct=tr_net))
    pd.DataFrame(vrows).to_csv(f"{REPO}/step410_table_overnight_val.csv", index=False)

    # ================================================================== 6
    section("6. THE ONE SUB-RULE THE PARTITION SUGGESTED, READ ONCE")
    print("Section 4 showed that on the choosing slice the overnight move on")
    print("NVDA, AMD, MU and TSLA is concentrated after a session that closed")
    print("UP, and largely absent after a down day. On MSFT, SMH and SPY it")
    print("leans the other way, so this is not a mechanism the whole basket")
    print("shares - but it is the strongest thing the partition turned up and")
    print("leaving it untested would be leaving the thread open.")
    print("")
    print("So: hold overnight ONLY after an up session. Chosen from the choosing")
    print("slice, read once on the middle slice, applied to all 12 names rather")
    print("than to the four that looked best - cherry-picking the four would be")
    print("the whole error. With 12 names, luck alone produces about 0.6 that")
    print("clear a 95% bar, so one or two passes here would mean nothing.")
    print(f"\n  {'name':>6}{'nights':>8}{'net%':>9}{'t':>7}{'x cost':>8}"
          f"{'   |':>4}{'choosing-slice net%':>21}{'t':>7}")
    srows = []
    for sym in NAMES:
        try:
            d = load_daily(sym)
        except FileNotFoundError:
            continue
        i_tr, i_va = split_60_20_20(len(d))
        cost = costs[sym]["p75"]
        r_all = overnight_returns(d)
        up = (d["close"].to_numpy() > d["open"].to_numpy())
        m_tr = np.zeros(len(d), dtype=bool); m_tr[:i_tr] = True
        m_va = np.zeros(len(d), dtype=bool); m_va[i_tr:i_va] = True
        ok = ~np.isnan(r_all)
        a = r_all[ok & up & m_tr] - cost
        b = r_all[ok & up & m_va] - cost
        if len(b) < 30:
            continue
        print(f"  {sym:>6}{len(b):>8,}{b.mean():>9.4f}{tstat(b):>7.2f}"
              f"{(b.mean()+cost)/cost:>8.1f}{'   |':>4}{a.mean():>20.4f}"
              f"{tstat(a):>7.2f}")
        srows.append(dict(symbol=sym, val_n=len(b), val_net_pct=b.mean(),
                          val_t=tstat(b), val_over_cost=(b.mean() + cost) / cost,
                          train_net_pct=a.mean(), train_t=tstat(a)))
    sd = pd.DataFrame(srows)
    sd.to_csv(f"{REPO}/step410_table_overnight_upday.csv", index=False)
    n_pass = int(((sd.val_t >= 2.0) & (sd.val_over_cost >= 5.0)).sum())
    print(f"\n  names clearing both bars out of sample: {n_pass} of {len(sd)}")
    print(f"  expected from luck alone at a 95% bar: {0.05*len(sd):.1f}")

    print("\nwrote step410_table_overnight.csv, step410_table_overnight_partitions.csv,")
    print("      step410_table_overnight_val.csv, step410_table_overnight_upday.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
