"""
step22_round17.py — research round: 2h-resolution tactical entries.

Run:  python3 step22_round17.py

QUEUED HYPOTHESIS (RESEARCH_QUEUE.md item #1):
The live tactical book fires two triggers on 1h bars — panic-dip (RSI(3)
< 15) and flag-touch (bar dips to its 80-hour trend line and closes back
above it) — both gated by the 4h champion's bull state. This round asks a
single clean question: does the SAME tactical logic carry an edge at 2h
resolution instead of 1h? Slower bars = fewer, cleaner signals and a
wider natural stop; the question is whether the after-cost expectancy
survives the full gauntlet on a resolution we have never spent a tactical
test look on.

CONFIG (frozen from the queue, no tuning, no grids):
  FILTER : 4h champion state == long (vol-gated MA 20/100, funding<=1bp),
           mapped onto 2h bars with NO lookahead (a 4h bar's state applies
           only to 2h bars after that 4h bar has fully closed).
  TRIGGERS (tested separately AND as the live OR-of-both):
    panic-dip  — RSI(3) on the 2h close < 15
    flag-touch — 2h bar low <= the 80-hour trend line (40-bar SMA at 2h)
                 AND the 2h close back above it
  STOP   : 1.85 x median(2h ATR%), median computed on the TRAIN window
           ONLY (no lookahead into val/test). Queue estimate ~2.2%.
  TARGET : 3:1 (3 x stop).
  HOLD   : 24 bars (= 48 hours, matching the live tactical time exit).
  EXEC   : maker (dip/flag entries are limit-natural, as the live book and
           round 15 model them). Real funding cashflows.

DISCIPLINE: 60/20/20. Qualify = positive expectancy on train AND val with
>=30 train / >=8 val trades -> exactly ONE sealed-test look. This is the
FIRST tactical test look ever taken at 2h resolution (all prior tactical
work — rounds 12-17 — was on 1h), so the 2h test window is pristine for
this family. Every look taken is logged to RESEARCH_LOG.md.

(On the record: the 2h window was looked at ONCE before, in round 5, but
for a completely different family — the CORE MA-crossover champion 30/50,
which topped val then died on test. Different strategy, different signal;
the tactical dip/flag family has never touched 2h.)
"""

import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import machine
from step20_round15 import champion_state_on_1h
from strategy import atr, rsi

RSI_TH = 15
FLAG_TREND_BARS = 40      # 80-hour trend line at 2h resolution
ATR_MULT = 1.85           # stop = 1.85 x median 2h ATR% (train only)
R_MULT = 3.0              # 3:1 target
MAX_HOLD = 24             # 24 x 2h = 48h, matches live tactical


def score(df, sig, f_bps, stop, target):
    n = len(df)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)

    def run(lo, hi):
        return run_backtest(df.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            execution="maker", stop_pct=stop,
                            target_pct=target,
                            funding_series=f_bps.iloc[lo:hi].reset_index(drop=True))
    return run(0, i_tr), run(i_tr, i_va), run(i_va, n)


def main():
    print("ROUND 17 RESEARCH — 2h-resolution tactical entries "
          "(panic-dip + flag-touch)\n")

    d2 = fetch_bybit_deep("2h", "BTCUSDT")
    d4 = fetch_bybit_deep("4h", "BTCUSDT")
    funding = fetch_funding_history("BTCUSDT")
    f2 = align_funding(d2, funding)
    f4 = align_funding(d4, funding)

    n = len(d2)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)
    yrs = (d2["timestamp"].iloc[-1] - d2["timestamp"].iloc[0]).days / 365

    # --- stop from TRAIN-ONLY 2h ATR (no lookahead into val/test) ---------
    atr_pct = (atr(d2, 14) / d2["close"] * 100)
    med_train = float(atr_pct.iloc[:i_tr].median())
    STOP = round(ATR_MULT * med_train, 2)
    TARGET = round(R_MULT * STOP, 2)
    print(f"  {n} 2h bars, {yrs:.1f} years. median 2h ATR% (train only) = "
          f"{med_train:.2f}%")
    print(f"  -> STOP = {ATR_MULT} x {med_train:.2f}% = {STOP}%  |  "
          f"TARGET (3:1) = {TARGET}%  |  hold {MAX_HOLD} bars (48h)\n")

    # --- signals ----------------------------------------------------------
    champ = champion_state_on_1h(d2, d4, f4)         # generic: maps 4h onto d2
    bull = (champ == 1)
    r3 = rsi(d2["close"], 3)
    sma = d2["close"].rolling(FLAG_TREND_BARS).mean()
    no_exit = pd.Series(False, index=d2.index)

    panic = bull & (r3 < RSI_TH)
    flag = bull & (d2["low"] <= sma) & (d2["close"] > sma)

    variants = [
        ("panic-dip 2h", machine(d2, panic, no_exit, +1, MAX_HOLD)),
        ("flag-touch 2h", machine(d2, flag, no_exit, +1, MAX_HOLD)),
        ("panic OR flag (live)", machine(d2, panic | flag, no_exit, +1, MAX_HOLD)),
    ]

    rows, keep = [], {}
    for tag, sig in variants:
        runs = score(d2, sig, f2, STOP, TARGET)
        keep[tag] = (sig, runs)
        r_tr, r_va, _ = runs
        rows.append({
            "config": tag,
            "tr_n": len(r_tr.trades), "tr_win%": r_tr.win_rate * 100,
            "tr_exp": r_tr.expectancy, "tr_ret%": r_tr.total_return_pct,
            "va_n": len(r_va.trades), "va_win%": r_va.win_rate * 100,
            "va_exp": r_va.expectancy, "va_ret%": r_va.total_return_pct,
        })
    print("TRAIN + VALIDATION (2h, maker, real funding, full costs):")
    print(pd.DataFrame(rows).to_string(index=False,
                                       float_format=lambda x: f"{x:,.2f}"))

    qual = [t for t, (s, r) in keep.items()
            if r[0].expectancy > 0 and r[1].expectancy > 0
            and len(r[0].trades) >= 30 and len(r[1].trades) >= 8]
    print(f"\nqualified (positive BOTH windows, >=30 train/>=8 val): "
          f"{qual or 'NONE'}")

    if not qual:
        print("\nVERDICT: no 2h tactical variant clears train+val. Test")
        print("windows stay SEALED (zero looks burned). The 1h tactical")
        print("book keeps the monopoly; 2h resolution adds no edge here.")
        return

    print("\nSEALED TEST (ONE look per qualifier — logged as looks consumed):")
    for t in qual:
        sig, runs = keep[t]
        r_te = runs[2]
        print(f"\n  {t}: TEST exp ${r_te.expectancy:+,.2f}, "
              f"{r_te.total_return_pct:+.1f}%, win {r_te.win_rate * 100:.0f}%, "
              f"{len(r_te.trades)} trades, DD {r_te.max_drawdown_pct:.1f}%")
        if r_te.expectancy > 0:
            print(f"  ==> SURVIVES THE FULL GAUNTLET — AWAITING DEPLOYMENT "
                  f"REVIEW (do NOT auto-deploy)")
        else:
            print("  ==> died on test — the gauntlet holds, no sleeve.")


if __name__ == "__main__":
    main()
