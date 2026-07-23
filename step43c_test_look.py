"""
step43c_test_look.py — round 43's authorized sealed-test looks (2 spent).

Survivors under examination, reconstructed byte-for-byte from
step43_daytrade.py (same entries, same train-derived stop, same costs +
real funding; the ONLY new thing is the slice iloc[i_va:n]):

  1. momentum burst 1h, X>=1.8% impulse, CHAMP-gated, tgt 3xATR, hold 24h
     (train +$7.20/t x257, val +$8.74/t x61, median hold 1h)
  2. same but RAW (uncondition/no trend gate)
     (train +$7.13/t x389, val +$37.90/t x100 — the 5x val jump is the
      suspected luck we're testing)

Session-breakout survivor: NO look spent — thin edge (+$1.08/t val) with a
-77% train drawdown disqualifies it from ever taking real size; not worth
eroding the test set for.
"""

from step43_daytrade import (fetch_bybit_deep, fetch_funding_history,
                             align_funding, atr, split_points, champ_aligned,
                             momentum_burst_entries, day_trade_signal,
                             hours_to_bars, HARD_STOP_CAP)
from backtest import run_backtest
from strategy import vol_gated_ma


def report(name, r):
    holds = []
    for t in r.trades:
        try:
            holds.append((t.exit_time - t.entry_time).total_seconds() / 3600)
        except Exception:
            pass
    med_hold = sorted(holds)[len(holds)//2] if holds else 0
    print(f"\n=== SEALED TEST — {name} ===")
    print(f"  trades {len(r.trades)} | expectancy ${r.expectancy:+,.2f}/t | "
          f"win {r.win_rate*100:.1f}% | return {r.total_return_pct:+.1f}% | "
          f"maxDD {r.max_drawdown_pct:.1f}% | median hold {med_hold:.0f}h")
    verdict = "PASS" if (r.expectancy > 0 and len(r.trades) >= 15) else \
              ("THIN" if r.expectancy > 0 else "FAIL")
    print(f"  verdict: {verdict}")
    return verdict


def main():
    d = fetch_bybit_deep("1h", "BTCUSDT")
    d4 = fetch_bybit_deep("4h", "BTCUSDT")
    f = align_funding(d, fetch_funding_history("BTCUSDT"))
    n, i_tr, i_va = split_points(d)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(1.0 * med_atr, HARD_STOP_CAP)
    target_pct = 3.0 * med_atr
    champ4h = vol_gated_ma(d4, fast=20, slow=100, min_atr_pct=1.5)
    champ_al = champ_aligned(d4, champ4h, d)
    mh = hours_to_bars(d, 24)
    print(f"test window {d['timestamp'].iloc[i_va]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | stop {stop_pct:.2f}% "
          f"target {target_pct:.2f}%")

    results = {}
    for cond in ("champ", "raw"):
        el, es = momentum_burst_entries(d, champ_al, 1.8, 1, cond)
        sig = day_trade_signal(d, el, es, mh)
        r = run_backtest(d.iloc[i_va:n].reset_index(drop=True),
                         sig.iloc[i_va:n].reset_index(drop=True),
                         execution="maker",
                         funding_series=f.iloc[i_va:n].reset_index(drop=True),
                         stop_pct=stop_pct, target_pct=target_pct)
        results[cond] = report(f"momentum burst 1h X1.8 {cond} 3xATR 24h", r)

    print(f"\nSUMMARY: champ={results['champ']} | raw={results['raw']}")


if __name__ == "__main__":
    main()
