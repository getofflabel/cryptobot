"""
step4_out_of_sample.py — does the strategy survive data it has never seen?

Run:  python3 step4_out_of_sample.py

THE PROBLEM THIS SOLVES

In Step 3 we looked at a table and were drawn to the best row. But we chose
it AFTER seeing its results on that data. Given enough parameter combos,
one of them will always look great on any dataset by pure luck — the same
way that in a room of 1,000 coin-flippers, someone flips ten heads straight.
Picking that person and calling them a coin-flipping talent is overfitting.

THE FIX: SPLIT TIME IN TWO

  TRAIN (older ~70%)  : try every parameter combo here, pick the best.
  TEST  (newest ~30%) : run ONLY the chosen combo here, ONCE.

The test window acts like the future: it played no part in choosing the
parameters, so performance there is an honest preview of live trading.
Two rules keep it honest:
  - the test data is touched ONCE, by ONE pre-committed combo. If you rerun
    this with tweaks until the test looks good, the test has silently become
    training data and proves nothing.
  - indicator WARMUP on the test slice may use earlier history (an SMA only
    looks backward — live trading would have history too). What must never
    cross the split line is a PARAMETER CHOICE.
"""

import pandas as pd

import config
from backtest import run_backtest
from step3_run_strategy import fetch_history
from strategy import buy_and_hold, ma_crossover

TRAIN_FRAC = 0.7
MIN_TRADES_TRAIN = 10   # fewer trades than this = expectancy is just noise
MIN_TRADES_TEST = 5


def run_slice(df, signal, lo, hi):
    """Backtest rows [lo:hi) using signals computed on the FULL history.

    Signals may warm up on pre-slice bars (backward-looking only, legal).
    Parameters were chosen elsewhere — that is the only thing that matters.
    """
    c = df.iloc[lo:hi].reset_index(drop=True)
    s = signal.iloc[lo:hi].reset_index(drop=True)
    return run_backtest(c, s)


def main():
    # ---- data -----------------------------------------------------------
    print("Fetching ~11 months of hourly history from BloFin...")
    df = fetch_history(8000)
    split = int(len(df) * TRAIN_FRAC)
    t0, t1, t2 = (df["timestamp"].iloc[0], df["timestamp"].iloc[split],
                  df["timestamp"].iloc[-1])
    print(f"  {len(df)} bars total")
    print(f"  TRAIN: {t0:%Y-%m-%d} to {t1:%Y-%m-%d}  ({split} bars)")
    print(f"  TEST : {t1:%Y-%m-%d} to {t2:%Y-%m-%d}  ({len(df) - split} bars)"
          f"  <- untouched until the end\n")

    # ---- 1. tune on TRAIN only ------------------------------------------
    grid = [(f, s) for f in (10, 20, 30, 50) for s in (50, 100, 150, 200, 300)
            if f < s]
    print(f"[1] TUNING on train data only — {len(grid)} parameter combos")

    rows = []
    signals = {}
    for fast, slow in grid:
        sig = ma_crossover(df, fast, slow)      # backward-looking only
        signals[(fast, slow)] = sig
        r = run_slice(df, sig, 0, split)
        rows.append({"fast": fast, "slow": slow, "trades": len(r.trades),
                     "expectancy": r.expectancy, "return %": r.total_return_pct,
                     "max DD %": r.max_drawdown_pct})

    train = pd.DataFrame(rows)
    eligible = train[train["trades"] >= MIN_TRADES_TRAIN]
    ranked = eligible.sort_values("expectancy", ascending=False)

    print("\n  top 5 on TRAIN (by expectancy, after costs):")
    print(ranked.head(5).to_string(index=False,
                                   float_format=lambda x: f"{x:,.2f}"))
    ineligible = len(train) - len(eligible)
    if ineligible:
        print(f"  ({ineligible} combos excluded: fewer than "
              f"{MIN_TRADES_TRAIN} trades — too few to judge)")

    best = ranked.iloc[0]
    fast, slow = int(best["fast"]), int(best["slow"])
    print(f"\n  COMMITTED before touching test data: MA {fast}/{slow}")

    # ---- 2. the one honest look at TEST ---------------------------------
    print(f"\n[2] VALIDATING MA {fast}/{slow} on the untouched test window")
    r_train = run_slice(df, signals[(fast, slow)], 0, split)
    r_test = run_slice(df, signals[(fast, slow)], split, len(df))
    r_hold = run_slice(df, buy_and_hold(df), split, len(df))

    comp = pd.DataFrame([
        {"window": "train (tuned here)", "trades": len(r_train.trades),
         "expectancy": r_train.expectancy, "return %": r_train.total_return_pct,
         "max DD %": r_train.max_drawdown_pct},
        {"window": "TEST (never seen)", "trades": len(r_test.trades),
         "expectancy": r_test.expectancy, "return %": r_test.total_return_pct,
         "max DD %": r_test.max_drawdown_pct},
        {"window": "buy & hold on test", "trades": len(r_hold.trades),
         "expectancy": r_hold.expectancy, "return %": r_hold.total_return_pct,
         "max DD %": r_hold.max_drawdown_pct},
    ])
    print(comp.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---- 3. how did the OTHER train picks fare out of sample? -----------
    # Educational: the in-sample ranking rarely survives. Seeing the top-5
    # reshuffle out-of-sample is the fastest cure for trusting leaderboards.
    print("\n[3] the train top-5, re-scored on the test window:")
    for _, row in ranked.head(5).iterrows():
        f_, s_ = int(row["fast"]), int(row["slow"])
        rt = run_slice(df, signals[(f_, s_)], split, len(df))
        print(f"  MA {f_:>3}/{s_:<3}  train exp ${row['expectancy']:>8,.2f}"
              f"   ->   test exp ${rt.expectancy:>8,.2f}"
              f"   ({len(rt.trades)} trades)")

    # ---- 4. verdict ------------------------------------------------------
    print("\n" + "=" * 64)
    print("VERDICT")
    print("=" * 64)
    te, ve = r_train.expectancy, r_test.expectancy

    if te <= 0:
        print("NOTHING TO VALIDATE — the strategy has no edge to test.")
        print(f"  The BEST tuning on the training data still loses "
              f"${-te:,.2f}/trade")
        print("  after costs. Out-of-sample validation exists to check whether")
        print("  an apparent edge is real; here there was no apparent edge in")
        print("  the first place. That is not a failure of the process — the")
        print("  harness just saved you from months of paying to find out.")
        print(f"  (For context, the test window run came out "
              f"${ve:+,.2f}/trade.)")
    elif len(r_test.trades) < MIN_TRADES_TEST:
        print(f"INCONCLUSIVE: only {len(r_test.trades)} test trades. Neither")
        print("belief nor rejection is justified on this few. Get more data")
        print("or a faster-trading configuration before concluding anything.")
    elif te > 0 and ve <= 0:
        print("OVERFIT — the classic signature.")
        print(f"  Positive on the data it was tuned on  (${te:+,.2f}/trade)")
        print(f"  but loses on data it had never seen   (${ve:+,.2f}/trade).")
        print("  The tuning fitted THIS PAST's noise, not a repeatable edge.")
        print("  Do NOT trade this. Do not re-tune until the test looks good")
        print("  either — that just launders the overfit through more tries.")
    elif ve > 0 and ve < 0.3 * te:
        print("DEGRADED — survived, barely.")
        print(f"  ${te:+,.2f}/trade in training collapsed to ${ve:+,.2f} on")
        print("  unseen data. Some edge may exist, but plan around the test")
        print("  number, never the training number.")
    else:
        print("SURVIVED out-of-sample — necessary, but not sufficient.")
        print(f"  train ${te:+,.2f}/trade   test ${ve:+,.2f}/trade")
        print("  One honest pass earns the next test (paper trading),")
        print("  not real money.")

    print()
    print("Reminder: this script's test window is now SPENT. Rerunning with")
    print("tweaked grids until the verdict improves would quietly turn the")
    print("test into training data. The next honest checkpoint is Step 5:")
    print("live paper trading on data that does not exist yet.")


if __name__ == "__main__":
    main()
