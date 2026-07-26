"""
step450b_significance.py - ROUND 450, PART 2

No new configuration is tested here and no new slice is opened. This file
only asks whether the ONE claim round 450 part 1 makes is bigger than noise:

  "moving the entry trigger from the 5-minute bar to the 1-minute bar - the
   resolution he actually specifies - cuts the structural stop by roughly
   two thirds and flips the sign of the gross edge."

It re-uses the exact trade populations part 1 produced, on the choosing
slice only. It also runs the stop-distance census across the five other
crypto pairs, because a leverage fact that only holds on three coins is not
a leverage fact (standing transfer rule).
"""

import io
import contextlib
import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def main():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        df, t_tr, t_va, store = R.main()

    print("=" * 100)
    print("ROUND 450 PART 2 - IS THE TRIGGER DIFFERENCE BIGGER THAN NOISE?")
    print("=" * 100)
    print("choosing slice only. Gross, because the question is about the")
    print("method's signal, not about what Alpaca charges to collect it.")

    arms = {"A": [], "B": []}
    for (nm, arm), parts in store.items():
        for sym, res in parts:
            tr = res[res.sig_t < t_tr]
            arms[arm].append(tr)

    rows = []
    for arm, lab in (("A", "5-minute trigger (round 370's construction)"),
                     ("B", "1-MINUTE trigger (his construction)")):
        allr = pd.concat(arms[arm])
        # de-duplicate: the four target settings score the SAME entries, so
        # the population for a significance test is one row per entry.
        uniq = allr.drop_duplicates(subset=["sig_t", "stop_pct"])
        t, n = tstat(uniq["gross_pct"])
        rows.append((lab, n, uniq["gross_pct"].mean(), t,
                     uniq["stop_pct"].median()))

    print(f"\n{'construction':<46}{'trades':>8}{'mean gross':>12}"
          f"{'t':>8}{'median stop':>14}{'lev @1% risk':>14}")
    for lab, n, m, t, s in rows:
        print(f"{lab:<46}{n:>8,}{m:>11.4f}%{t:>8.2f}{s:>13.3f}%{1/s:>13.1f}x")

    # the control, same treatment
    d5, d1 = R.prep("BTCUSD")
    idx = np.arange(0, len(d5) - 1, 60)
    ctl = []
    for dirn in (+1, -1):
        stop = (d5["mr_sl"].to_numpy() if dirn > 0 else d5["mr_sh"].to_numpy())[idx]
        res = R.simulate(d5, idx, dirn, stop, None, R.MAX_HOLD_MIN // 5)
        ctl.append(res[res.sig_t < t_tr])
    c = pd.concat(ctl)
    t, n = tstat(c["gross_pct"])
    print(f"{'CONTROL random entry, same stop machinery':<46}{n:>8,}"
          f"{c['gross_pct'].mean():>11.4f}%{t:>8.2f}"
          f"{c['stop_pct'].median():>13.3f}%{1/c['stop_pct'].median():>13.1f}x")

    a = pd.concat(arms["A"]).drop_duplicates(subset=["sig_t", "stop_pct"])
    b = pd.concat(arms["B"]).drop_duplicates(subset=["sig_t", "stop_pct"])
    diff = b["gross_pct"].mean() - a["gross_pct"].mean()
    se = np.sqrt(b["gross_pct"].var(ddof=1) / len(b)
                 + a["gross_pct"].var(ddof=1) / len(a))
    print(f"\ndifference, 1-minute trigger minus 5-minute trigger: "
          f"{diff:+.4f}% of price per trade, t = {diff/se:.2f}")
    dc = b["gross_pct"].mean() - c["gross_pct"].mean()
    sec = np.sqrt(b["gross_pct"].var(ddof=1) / len(b)
                  + c["gross_pct"].var(ddof=1) / len(c))
    print(f"difference, 1-minute trigger minus RANDOM ENTRY:      "
          f"{dc:+.4f}% of price per trade, t = {dc/sec:.2f}")
    print(f"\nwhat one round trip costs at Alpaca crypto taker rates: "
          f"{R.COST_RT:.2f}% of notional.")
    print(f"the 1-minute arm's gross mean is {b['gross_pct'].mean()/R.COST_RT:.2f}x "
          f"that cost. Stated, not used to decide anything.")

    # ------------------------------------------------ leverage census
    print("\n" + "=" * 100)
    print("STOP-DISTANCE CENSUS - the durable half, across all eight pairs")
    print("distance from price to the structure that says the idea was wrong,")
    print("as a PRICE move (not a change in the position's value).")
    print("=" * 100)
    print(f"{'pair':<10}{'5m swing':>11}{'1m swing':>11}{'ratio':>8}"
          f"{'lev@1% 5m':>12}{'lev@1% 1m':>12}")
    cen = []
    for sym in R.PRIMARY + R.TRANSFER:
        try:
            d5s = R.load(sym, "5m"); d1s = R.load(sym, "1m")
        except FileNotFoundError:
            continue
        t0 = max(d5s["t"].iloc[0], d1s["t"].iloc[0])
        d5s = d5s[d5s["t"] >= t0]; d1s = d1s[d1s["t"] >= t0]
        out = []
        for dd in (d5s, d1s):
            sh, sl = R.tjr_swings(dd["open"].to_numpy(), dd["high"].to_numpy(),
                                  dd["low"].to_numpy(), dd["close"].to_numpy())
            c_ = dd["close"].to_numpy()
            lo = R.ffill_shift(sl)
            dist = (c_ - lo) / c_ * 100.0
            dist = dist[np.isfinite(dist) & (dist > 0)]
            out.append(np.median(dist))
        m5, m1 = out
        cen.append(dict(pair=sym, med_5m=m5, med_1m=m1, ratio=m1 / m5,
                        lev_5m=1 / m5, lev_1m=1 / m1))
        print(f"{sym:<10}{m5:>10.3f}%{m1:>10.3f}%{m1/m5:>8.2f}"
              f"{1/m5:>11.1f}x{1/m1:>11.1f}x")
    pd.DataFrame(cen).to_csv("/Users/wallacechen/cryptobot/step450_census.csv",
                             index=False)
    print("\nlev@1% means: risking 1% of the account, size = risk / stop, so a")
    print("position this many times the account. Leverage is the OUTPUT.")
    print("US law caps it at 10x regardless of what the structure permits.")


if __name__ == "__main__":
    main()
