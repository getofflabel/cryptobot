"""
step41c_test_look.py — round 41's ONE authorized sealed-test look.

The gauntlet's final step: configs that made money on train AND validation
(with the sample floors met) earn exactly one evaluation on the untouched
final 20% of history. This script spends that look for round 41's top 3:

  1. forensic widened  f>1.5bp, 1h   (train +$24.57/t x55, val +$193.25/t x8)
  2. breakdown N20 gate-below-median, 1h  (train +$9.84/t x278, val +$22.79/t x78)
  3. bleed-rider structural k=5, 1h  (train +$11.38/t x147, val +$26.40/t x40)

Every parameter below is reconstructed byte-for-byte from step41_shorts.py —
same signals, same train-derived stops, same costs, same funding. The ONLY
new thing is the slice: iloc[i_va:n]. Results are logged to RESEARCH_LOG.md
by the operator; failed configs are buried, never re-tuned (that would turn
the sealed test into a second validation set and make its verdicts lies).
"""

from step41_shorts import (
    fetch_bybit_deep, fetch_funding_history, align_funding, atr,
    split_points, adaptive_vol_gate, forensic_signal, breakdown_signal,
    bleed_rider_structural,
)
from backtest import run_backtest


def test_run(d, sig, f, i_va, n, stop_pct=None, target_pct=None):
    return run_backtest(
        d.iloc[i_va:n].reset_index(drop=True),
        sig.iloc[i_va:n].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[i_va:n].reset_index(drop=True),
        stop_pct=stop_pct, target_pct=target_pct,
    )


def report(name, r):
    print(f"\n=== SEALED TEST — {name} ===")
    print(f"  trades {len(r.trades)} | expectancy ${r.expectancy:+,.2f}/trade | "
          f"win rate {r.win_rate*100:.1f}% | return {r.total_return_pct:+.1f}% | "
          f"max DD {r.max_drawdown_pct:.1f}%")
    verdict = "PASS" if (r.expectancy > 0 and len(r.trades) >= 3) else \
              ("THIN" if r.expectancy > 0 else "FAIL")
    print(f"  verdict: {verdict}")
    return verdict


def main():
    d = fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f = align_funding(d, funding_hist)
    n, i_tr, i_va = split_points(d)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    print(f"1h: {n} bars | test window {d['timestamp'].iloc[i_va]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} ({n - i_va} bars)")

    # 1. forensic widened f>1.5bp (family-4 geometry: stop 1.69 / target 5.07)
    sig = forensic_signal(d, f, fund_thresh=1.5, atr_thresh=1.2,
                          pop_thresh=1.5, pop_hours=4,
                          max_hold_hours=48, retest=False)
    r1 = test_run(d, sig, f, i_va, n, stop_pct=1.69, target_pct=5.07)
    v1 = report("forensic widened f>1.5bp 1h", r1)

    # 2. breakdown N20, gate BELOW trailing-365d median ATR%
    gate_below, _ = adaptive_vol_gate(d, direction="below")
    B = round(24 / 1 * 10)                      # days_to_bars(1h, 10 days)
    sig = breakdown_signal(d, 20, gate_below, B)
    r2 = test_run(d, sig, f, i_va, n, stop_pct=2.0 * med_atr_train)
    v2 = report("breakdown N20 gate-below-median 1h", r2)

    # 3. bleed rider structural k=5 (family-1 stop: 2x train median ATR%)
    sig = bleed_rider_structural(d, 5)
    r3 = test_run(d, sig, f, i_va, n, stop_pct=2.0 * med_atr_train)
    v3 = report("bleed rider structural k=5 1h", r3)

    print(f"\nSUMMARY: forensic={v1} | breakdown={v2} | bleed={v3}")


if __name__ == "__main__":
    main()
