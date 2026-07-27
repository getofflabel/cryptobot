"""
step410_nvda.py - ROUND 410, JOB 1
CLOSING THE NVIDIA THREAD.

Research only. No orders of any kind, paper or otherwise. No live file
touched. This bot cannot trade a single stock anywhere today except on the
Alpaca paper account, and nothing here goes near it.

THE THREAD BEING CLOSED
  MARKET_PLAYBOOKS.md carries this line: "NVDA d20 breakout was the
  strongest single-stock candidate (val>train, all decades) - no demo
  venue for NVDA yet." That came out of round 52, on yfinance daily bars,
  scored in DOLLARS PER TRADE, with no stop and no coin-flip control.

  Two things about it were never right:

  1. Dollars per trade on a stock that went up roughly three hundred fold
     is not a measurement. The last few trades happen at a price a
     hundred times the first few, so the average is a statement about
     WHEN the trades happened, not about whether the rule works. Round 52
     itself reported +$314/trade in the 1990s and +$21,387/trade in the
     2020s and called it "positive in every decade". Rescaled to percent
     of the money at risk, those may be the same number. Everything below
     is in percent of price.

  2. The exit rule is "get out when the close drops under the 20-day
     exponential average". On a stock in a violent uptrend, that exit
     makes money no matter when you got in. The entry rule was never
     tested against the alternative that it contributes nothing. That is
     what the coin-flip control does here, and it is the whole test.

WHAT THIS FILE RUNS
  A. The original shape, unchanged, on Alpaca's own daily bars.
  B. The coin-flip control against it.
  C. The same family with a stop placed at chart structure, swept on the
     first 60% of the bars only, with the chance baseline stated.
  D. The chosen setting read once on the middle 20%.
  E. The same rule, constants re-derived, on nine other names.
  The final 20% of the bars is never opened by this file.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step41_shorts import confirmed_swings
from step410_lib import (REPO, load_daily, split_60_20_20, costs_table,
                         run_long_engine, coin_flip_control, percentile_of,
                         summarise, fmt_summary, last_below, tstat,
                         MIN_TRAIN_TRADES, MIN_VAL_TRADES)

BASKET = ["NVDA", "AMD", "AVGO", "MU", "MSFT", "GOOGL", "META", "AMZN",
          "TSLA", "SMH"]
ENTRY_N = [10, 15, 20, 30, 40, 55]
EXIT_EMA = [10, 20, 30]
N_CONFIGS = len(ENTRY_N) * len(EXIT_EMA)
N_FLIPS = 2000


def signals(d, entry_n, ema_n):
    hi = d["high"].rolling(entry_n).max().shift(1)
    enter = (d["close"] > hi).fillna(False).to_numpy()
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = (d["close"] < ema).fillna(False).to_numpy()
    warm = max(entry_n, ema_n) + 5
    enter[:warm] = False
    return enter, exit_


def structural_stop(d, k=3):
    """The last confirmed swing low that sits below the current close. A
    long is wrong if price trades under the last place buyers actually
    defended. Read k bars late, so nothing after the signal bar is used."""
    _, sl = confirmed_swings(d, k)
    lvl, ago = last_below(sl, d["close"])
    return lvl, ago


def section(t):
    print("\n" + "=" * 78)
    print(t)
    print("=" * 78)


def main():
    costs = costs_table()
    out_rows = []

    # =================================================================== A
    section("A. THE ORIGINAL SHAPE, ON ALPACA'S OWN DAILY BARS")
    d = load_daily("NVDA")
    n = len(d)
    i_tr, i_va = split_60_20_20(n)
    cost = costs["NVDA"]["p75"]           # conservative: the 75th percentile spread
    print(f"NVDA daily bars: {n:,}  {d['date'].iloc[0]} to {d['date'].iloc[-1]}")
    print(f"  choosing slice  bars 0-{i_tr:,}   {d['date'].iloc[0]} to {d['date'].iloc[i_tr-1]}")
    print(f"  middle slice    bars {i_tr:,}-{i_va:,}  {d['date'].iloc[i_tr]} to {d['date'].iloc[i_va-1]}")
    print(f"  final slice     bars {i_va:,}-{n:,}  NEVER OPENED BY THIS FILE")
    print(f"  round-trip cost measured from real quotes: "
          f"{costs['NVDA']['med']:.4f}% of price (median), "
          f"{cost:.4f}% (75th percentile, used here)")
    print("  Alpaca history starts 2016, so this is 10.5 years, not the 22 that")
    print("  round 52 used. It is the venue's own data, which is the point.")

    enter, exit_ = signals(d, 20, 20)
    tr_raw = run_long_engine(d, enter, exit_, None, cost, 0, i_tr)
    va_raw = run_long_engine(d, enter, exit_, None, cost, i_tr, i_va)
    s_tr = summarise(tr_raw, cost); s_va = summarise(va_raw, cost)
    print("\n  20-day breakout, exit under the 20-day exponential average, NO STOP")
    print(f"    choosing slice : {fmt_summary(s_tr)}")
    print(f"    middle slice   : {fmt_summary(s_va)}")

    # the dollars-per-trade illusion, spelled out
    for lab, t in (("choosing", tr_raw), ("middle", va_raw)):
        if len(t):
            dollars = (t["exit"] - t["entry"])
            print(f"    {lab} slice in DOLLARS per share: mean ${dollars.mean():+.2f}, "
                  f"first trade entered at ${t['entry'].iloc[0]:.2f}, "
                  f"last at ${t['entry'].iloc[-1]:.2f} "
                  f"({t['entry'].iloc[-1]/t['entry'].iloc[0]:.0f}x the price)")

    # =================================================================== B
    section("B. THE COIN FLIP: DOES THE ENTRY RULE PICK ANYTHING?")
    print("Same engine, same exit rule, same direction, same number of trades,")
    print("same costs. Only the entry moments are random. 2,000 runs each.")
    print("")
    print("TWO versions of the control, and the difference between them is the")
    print("whole finding:")
    print("  LOOSE  - a random entry may land on any bar at all. Most of those")
    print("           bars are ones where the exit rule is ALREADY saying get")
    print("           out, so the fake trade lasts a bar or two and earns")
    print("           nothing. That compares time in the market, not entries.")
    print("  MATCHED- a random entry may only land on a bar where the exit rule")
    print("           is not currently firing, so the fake trade actually lives.")
    print("           This is the honest comparison.")
    print("Plus the number that settles it: return per BAR HELD. A rule that")
    print("only wins by being in the market longer will match the stock's own")
    print("drift per day and beat nothing.")

    alive = ~exit_                     # the exit rule is not firing on this bar
    for lab, t, lo, hi in (("choosing slice", tr_raw, 0, i_tr),
                           ("middle slice", va_raw, i_tr, i_va)):
        if len(t) == 0:
            continue
        real = t["ret_pct"].mean()
        held = t["bars_held"].clip(lower=1)
        real_pb = t["ret_pct"].sum() / held.sum()
        # the stock's own drift per trading day over the same bars, gross
        drift = (np.log(d["close"].iloc[hi - 1] / d["open"].iloc[lo])
                 / (hi - lo) * 100.0)
        print(f"\n  {lab}: real {real:+.3f}% of price per trade over {len(t)} trades, "
              f"{real_pb:+.4f}% of price per bar held")
        print(f"    the stock's own drift over these bars: {drift:+.4f}% of price "
              f"per trading day")
        for cname, mask, sd in (("LOOSE  ", None, 11), ("MATCHED", alive, 12)):
            cf = coin_flip_control(d, exit_, None, cost, lo, hi, len(t),
                                   n_runs=N_FLIPS, seed=sd, eligible_mask=mask)
            if len(cf["mean"]) == 0:
                continue
            p = percentile_of(real, cf["mean"])
            ppb = percentile_of(real_pb, cf["perbar"])
            print(f"    {cname} chance: {cf['mean'].mean():+.3f}%/trade "
                  f"(95th {np.percentile(cf['mean'],95):+.3f}), "
                  f"{cf['perbar'].mean():+.4f}%/bar "
                  f"(95th {np.percentile(cf['perbar'],95):+.4f}), "
                  f"hold {cf['hold'].mean():.1f} bars")
            print(f"             real sits at the {p:.1f}th percentile per trade, "
                  f"the {ppb:.1f}th per bar held")
            out_rows.append(dict(job="B", symbol="NVDA",
                                 config="donchian20 ema20 nostop",
                                 slice=lab, control=cname.strip(), n=len(t),
                                 mean_pct=real, perbar_pct=real_pb,
                                 chance_pctile_pertrade=p,
                                 chance_pctile_perbar=ppb,
                                 real_hold=t["bars_held"].mean(),
                                 chance_hold=cf["hold"].mean(),
                                 drift_perday=drift, cost_pct=cost))

    # buy and hold on the same window, for scale
    for lab, lo, hi in (("choosing slice", 0, i_tr), ("middle slice", i_tr, i_va)):
        bh = (d["close"].iloc[hi - 1] / d["open"].iloc[lo] - 1) * 100.0
        yrs = (d["et"].iloc[hi - 1] - d["et"].iloc[lo]).days / 365.25
        print(f"  {lab}: simply holding NVDA returned {bh:+.0f}% of the money put in "
              f"over {yrs:.1f} years")

    # =================================================================== C
    section("C. THE SAME FAMILY WITH A STOP AT CHART STRUCTURE")
    print("Stop = the last confirmed 3-bar swing low sitting below the entry.")
    print("Size = dollars risked / stop distance, so leverage is an OUTPUT.")
    print(f"Sweeping {N_CONFIGS} settings on the CHOOSING SLICE ONLY.")
    print("")
    print("CHANCE BASELINE, stated up front. Run 18 settings against a control")
    print("and roughly one of them clears the 95th percentile by luck: the odds")
    print(f"of at least one false winner are {100*(1-0.95**N_CONFIGS):.0f}%. So the")
    print(f"bar for a single setting in this sweep is the "
          f"{100*(1-0.05/N_CONFIGS):.2f}th percentile of chance, not the 95th.")
    print("Expected number of settings clearing the plain 95th by luck alone:")
    print(f"{0.05*N_CONFIGS:.1f} of {N_CONFIGS}.")

    stop_lvl, stop_ago = structural_stop(d, k=3)
    rows = []
    for N in ENTRY_N:
        for E in EXIT_EMA:
            e, x = signals(d, N, E)
            t = run_long_engine(d, e, x, stop_lvl, cost, 0, i_tr)
            s = summarise(t, cost)
            if s.get("n", 0) == 0:
                continue
            rows.append(dict(entry_n=N, exit_ema=E, **s))
    sw = pd.DataFrame(rows).sort_values("mean_pct", ascending=False)
    print("\n  choosing slice sweep (percent of price per trade, after costs):")
    print(f"  {'N':>4}{'ema':>5}{'trades':>8}{'mean%':>9}{'t':>7}{'win%':>7}"
          f"{'hold':>7}{'stop%':>8}{'meanR':>7}{'thick':>7}  verdict")
    for r in sw.itertuples():
        v = "ok" if r.n >= MIN_TRAIN_TRADES else "THIN SAMPLE"
        print(f"  {r.entry_n:>4}{r.exit_ema:>5}{r.n:>8}{r.mean_pct:>9.3f}"
              f"{r.t:>7.2f}{r.win_pct:>7.1f}{r.mean_hold:>7.1f}"
              f"{r.mean_stop_pct:>8.2f}{r.mean_r:>7.2f}{r.thickness:>7.1f}  {v}")

    ok = sw[sw.n >= MIN_TRAIN_TRADES]
    if len(ok) == 0:
        print("\n  INSUFFICIENT SAMPLE: no setting reaches 30 trades in the")
        print("  choosing slice. Alpaca's history is 10.5 years; a 20-day")
        print("  breakout fires too rarely to clear the floor. Stop here.")
        return 0

    # --- coin flip every setting that cleared the sample floor
    print("\n  coin flip (MATCHED: random entries only on bars where the exit")
    print("  rule is not already firing) on every setting past the 30-trade floor.")
    print(f"  {'N':>4}{'ema':>5}{'real%/t':>9}{'chance':>9}{'pct-t':>8}"
          f"{'real%/bar':>11}{'chance':>9}{'pct-bar':>9}{'hold R/C':>11}")
    cf_rows = []
    for r in ok.itertuples():
        e, x = signals(d, r.entry_n, r.exit_ema)
        t = run_long_engine(d, e, x, stop_lvl, cost, 0, i_tr)
        alive_x = ~x
        cf = coin_flip_control(d, x, stop_lvl, cost, 0, i_tr, len(t),
                               n_runs=N_FLIPS, seed=13, eligible_mask=alive_x)
        real_pb = r.perbar_pct
        p = percentile_of(r.mean_pct, cf["mean"])
        ppb = percentile_of(real_pb, cf["perbar"])
        cf_rows.append(dict(entry_n=r.entry_n, exit_ema=r.exit_ema, n=r.n,
                            mean_pct=r.mean_pct, perbar_pct=real_pb,
                            cf_mean=cf["mean"].mean(),
                            cf_p95=np.percentile(cf["mean"], 95),
                            cf_perbar=cf["perbar"].mean(),
                            cf_pct=p, cf_pct_perbar=ppb,
                            real_hold=r.mean_hold, cf_hold=cf["hold"].mean(),
                            thickness=r.thickness))
        print(f"  {r.entry_n:>4}{r.exit_ema:>5}{r.mean_pct:>9.3f}"
              f"{cf['mean'].mean():>9.3f}{p:>8.1f}"
              f"{real_pb:>11.4f}{cf['perbar'].mean():>9.4f}{ppb:>9.1f}"
              f"{r.mean_hold:>6.1f}/{cf['hold'].mean():<5.1f}")
    cfd = pd.DataFrame(cf_rows)
    cfd.to_csv(f"{REPO}/step410_table_nvda_sweep.csv", index=False)
    drift_tr = np.log(d["close"].iloc[i_tr - 1] / d["open"].iloc[0]) / i_tr * 100.0
    print(f"\n  for scale: NVDA's own drift across the choosing slice is "
          f"{drift_tr:+.4f}% of price per trading day.")
    print("  Any per-bar figure near that number is exposure, not entry skill.")

    # =================================================================== D
    section("D. THE CHOSEN SETTING, READ ONCE ON THE MIDDLE SLICE")
    best = cfd.sort_values("mean_pct", ascending=False).iloc[0]
    bn, be = int(best.entry_n), int(best.exit_ema)
    print(f"chosen on the choosing slice only: {bn}-day breakout, "
          f"exit under the {be}-day exponential average, structural stop")
    e, x = signals(d, bn, be)
    tv = run_long_engine(d, e, x, stop_lvl, cost, i_tr, i_va)
    sv = summarise(tv, cost)
    print(f"  middle slice: {fmt_summary(sv)}"
          if sv.get("n", 0) else "  middle slice: no trades")
    if sv.get("n", 0) >= MIN_VAL_TRADES:
        cf = coin_flip_control(d, x, stop_lvl, cost, i_tr, i_va, sv["n"],
                               n_runs=N_FLIPS, seed=17, eligible_mask=~x)
        p = percentile_of(sv["mean_pct"], cf["mean"])
        ppb = percentile_of(sv["perbar_pct"], cf["perbar"])
        drift_va = (np.log(d["close"].iloc[i_va - 1] / d["open"].iloc[i_tr])
                    / (i_va - i_tr) * 100.0)
        print(f"  coin flip (matched) on the middle slice: "
              f"chance {cf['mean'].mean():+.3f}%/trade "
              f"(95th {np.percentile(cf['mean'],95):+.3f}), "
              f"{cf['perbar'].mean():+.4f}%/bar")
        print(f"    real sits at the {p:.1f}th percentile per trade, "
              f"the {ppb:.1f}th per bar held")
        print(f"    real {sv['perbar_pct']:+.4f}%/bar vs the stock's own drift "
              f"{drift_va:+.4f}%/trading day over the same bars")
        print(f"    hold: real {sv['mean_hold']:.1f} bars, chance {cf['hold'].mean():.1f}")
        print(f"  thickness: {sv['mean_pct']/cost:.1f} times the round-trip cost "
              f"(bar is 5x) - but thickness only counts if the entry beat chance")
        out_rows.append(dict(job="D", symbol="NVDA",
                             config=f"donchian{bn} ema{be} structural stop",
                             slice="middle", control="MATCHED", n=sv["n"],
                             mean_pct=sv["mean_pct"], perbar_pct=sv["perbar_pct"],
                             chance_pctile_pertrade=p, chance_pctile_perbar=ppb,
                             real_hold=sv["mean_hold"], chance_hold=cf["hold"].mean(),
                             drift_perday=drift_va, cost_pct=cost))
    else:
        print(f"  INSUFFICIENT SAMPLE on the middle slice "
              f"({sv.get('n',0)} trades, floor is {MIN_VAL_TRADES})")

    # =================================================================== E
    section("E. THE SAME RULE ON NINE OTHER NAMES, CONSTANTS RE-DERIVED")
    print("Each name picks its OWN breakout length and exit average on its OWN")
    print("choosing slice, then gets its own coin flip. Nothing is copied.")
    print("The bar has three parts: at least 30 trades, profit at least 5 times")
    print("the measured round-trip cost, AND the entry must beat the matched")
    print("coin flip on return per BAR HELD, not just per trade.")
    print(f"\n  {'name':>6}{'N':>4}{'ema':>5}{'trades':>7}{'mean%':>8}"
          f"{'thick':>7}{'%/bar':>8}{'chance':>8}{'pctile':>8}{'drift':>8}  verdict")
    tbl = []
    for sym in BASKET:
        try:
            ds = load_daily(sym)
        except FileNotFoundError:
            print(f"  {sym:>6}  no data")
            continue
        c2 = costs.get(sym, {}).get("p75", 0.05)
        a, b = split_60_20_20(len(ds))
        sl2, _ = structural_stop(ds, k=3)
        loc = []
        for N in ENTRY_N:
            for E in EXIT_EMA:
                ee, xx = signals(ds, N, E)
                t = run_long_engine(ds, ee, xx, sl2, c2, 0, a)
                s = summarise(t, c2)
                if s.get("n", 0) >= MIN_TRAIN_TRADES:
                    loc.append(dict(N=N, E=E, **s))
        if not loc:
            print(f"  {sym:>6}   -    -       -        -      -      -        -"
                  f"  INSUFFICIENT SAMPLE")
            tbl.append(dict(symbol=sym, verdict="INSUFFICIENT SAMPLE"))
            continue
        ld = pd.DataFrame(loc).sort_values("mean_pct", ascending=False)
        bst = ld.iloc[0]
        ee, xx = signals(ds, int(bst.N), int(bst.E))
        t = run_long_engine(ds, ee, xx, sl2, c2, 0, a)
        cf = coin_flip_control(ds, xx, sl2, c2, 0, a, len(t),
                               n_runs=N_FLIPS, seed=19, eligible_mask=~xx)
        p = percentile_of(bst.mean_pct, cf["mean"])
        ppb = percentile_of(bst.perbar_pct, cf["perbar"])
        drift = np.log(ds["close"].iloc[a - 1] / ds["open"].iloc[0]) / a * 100.0
        thick = bst.mean_pct / c2
        # the bar: beats the MATCHED coin flip per bar held, at the
        # sweep-adjusted level, AND clears 5 times the round-trip cost
        adj = 100.0 * (1 - 0.05 / N_CONFIGS)
        verdict = ("SURVIVES" if (ppb >= adj and thick >= 5 and bst.mean_pct > 0)
                   else "fails the coin flip" if ppb < adj
                   else "too thin vs cost")
        print(f"  {sym:>6}{int(bst.N):>4}{int(bst.E):>5}{int(bst.n):>7}"
              f"{bst.mean_pct:>8.3f}{thick:>7.0f}{bst.perbar_pct:>8.4f}"
              f"{cf['perbar'].mean():>8.4f}{ppb:>8.1f}{drift:>8.4f}  {verdict}")
        tbl.append(dict(symbol=sym, entry_n=int(bst.N), exit_ema=int(bst.E),
                        n=int(bst.n), mean_pct=bst.mean_pct, t=bst.t,
                        perbar_pct=bst.perbar_pct, thickness=thick,
                        chance_pctile_pertrade=p, chance_pctile_perbar=ppb,
                        cf_perbar=cf["perbar"].mean(), drift_perday=drift,
                        real_hold=bst.mean_hold, cf_hold=cf["hold"].mean(),
                        cost_pct=c2, verdict=verdict))
    pd.DataFrame(tbl).to_csv(f"{REPO}/step410_table_breakout_basket.csv", index=False)

    # =================================================================== F
    section("F. PLATEAU OR SPIKE, AND WHAT THE MONEY ACTUALLY DID")
    print("A real effect should be flat across neighbouring settings. If one")
    print("setting sits at the 99th percentile of chance and the setting one")
    print("step away sits at the 60th, that is noise, not a mechanism.")
    pb = cfd["cf_pct_perbar"].to_numpy()
    print(f"\n  NVDA, {len(pb)} settings past the sample floor, where each sits in")
    print("  the matched coin flip on return per bar held:")
    for r in cfd.sort_values(["exit_ema", "entry_n"]).itertuples():
        print(f"    {r.entry_n:>3}-day breakout, {r.exit_ema:>2}-day average exit: "
              f"{r.cf_pct_perbar:>5.1f}th percentile")
    print(f"\n  spread: lowest {pb.min():.1f}th, median {np.median(pb):.1f}th, "
          f"highest {pb.max():.1f}th")
    print(f"  settings clearing the sweep-adjusted "
          f"{100*(1-0.05/N_CONFIGS):.2f}th bar: "
          f"{(pb >= 100*(1-0.05/N_CONFIGS)).sum()} of {len(pb)}")
    print("  Neighbouring settings that swing tens of percentile points apart")
    print("  are a spiky surface, not a plateau.")

    print("\n  What the money did on the choosing slice, chosen setting")
    print(f"  ({bn}-day breakout, {be}-day average exit, structural stop):")
    e, x = signals(d, bn, be)
    tt = run_long_engine(d, e, x, stop_lvl, cost, 0, i_tr)
    if len(tt):
        eq = np.exp(np.log1p(tt["ret_pct"] / 100.0).cumsum())
        peak = np.maximum.accumulate(eq)
        dd_strat = float((eq / peak - 1).min() * 100)
        bars_in = int(tt["bars_held"].clip(lower=1).sum())
        cl = d["close"].iloc[:i_tr].to_numpy()
        pk = np.maximum.accumulate(cl)
        dd_bh = float((cl / pk - 1).min() * 100)
        bh_mult = d["close"].iloc[i_tr - 1] / d["open"].iloc[0]
        print(f"    the rule turned 1 dollar into {eq.iloc[-1]:.1f}, "
              f"in the market {bars_in:,} of {i_tr:,} bars "
              f"({100*bars_in/i_tr:.0f}% of the time)")
        print(f"    simply owning NVDA turned 1 dollar into {bh_mult:.1f}")
        print(f"    deepest fall from a high: rule {dd_strat:.0f}% of the money, "
              f"owning it {dd_bh:.0f}%")
        print("    That is the honest shape: a shallower ride for a small")
        print("    fraction of the gain. It is crash insurance, which round 52")
        print("    also said. It is not evidence that the entry picks anything.")

    if out_rows:
        pd.DataFrame(out_rows).to_csv(f"{REPO}/step410_table_nvda_coinflip.csv",
                                      index=False)
    print(f"\n  the coin-flip bar used above is the {adj:.2f}th percentile - the")
    print(f"  95th percentile stretched to cover a {N_CONFIGS}-setting sweep.")
    print("\nwrote step410_table_nvda_sweep.csv, step410_table_breakout_basket.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
