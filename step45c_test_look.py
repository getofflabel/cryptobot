"""
step45c_test_look.py — round 45A's sealed-test look at the OI-shock survivor.

Config, reconstructed byte-for-byte from step45_grind_daytrades.py family 3:
  dOI 1h-window, q90 threshold, FOLLOW mode, CALM-gated, stop 1.0% / tgt 2.0%
  (train +$7.56/t x358, val +$12.28/t x20, median hold 6h)

Same train-derived threshold, same calm gate, same costs + real funding. The
only new thing is the slice iloc[i_va:n]. If it fails, it is BURIED, never
re-tuned.
"""

from step45_grind_daytrades import (
    fetch_bybit_deep, fetch_funding_history, align_funding, atr,
    split_points, adaptive_vol_gate, load_oi_history, align_oi,
    day_trade_signal, hours_to_bars, HARD_STOP_CAP,
)
from backtest import run_backtest


def main():
    d = fetch_bybit_deep("1h", "BTCUSDT")
    f = align_funding(d, fetch_funding_history("BTCUSDT"))
    oi_1h = align_oi(d, load_oi_history("BTCUSDT"))
    n, i_tr, i_va = split_points(d)
    calm, _ = adaptive_vol_gate(d, direction="below")

    w_bars = hours_to_bars(d, 1)                       # 1h window
    ret_w = (d["close"] / d["close"].shift(w_bars) - 1) * 100
    doi_w = (oi_1h / oi_1h.shift(w_bars) - 1) * 100
    thresh = float(doi_w.iloc[:i_tr].abs().dropna().quantile(0.90))   # TRAIN only
    extreme = (doi_w.abs() >= thresh).fillna(False)

    # FOLLOW: long with an up-shock, short with a down-shock, calm only
    enter_long = (extreme & (ret_w > 0) & calm).fillna(False)
    enter_short = (extreme & (ret_w < 0) & calm).fillna(False)
    sig = day_trade_signal(d, enter_long, enter_short, hours_to_bars(d, 24))

    r = run_backtest(
        d.iloc[i_va:n].reset_index(drop=True),
        sig.iloc[i_va:n].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[i_va:n].reset_index(drop=True),
        stop_pct=min(1.0, HARD_STOP_CAP), target_pct=2.0)

    holds = []
    for t in r.trades:
        try:
            holds.append((t.exit_time - t.entry_time).total_seconds() / 3600)
        except Exception:
            pass
    med = sorted(holds)[len(holds)//2] if holds else 0
    print(f"\n=== SEALED TEST — OI-shock 1h q90 follow calm stop1.0/tgt2.0 ===")
    print(f"  test window {d['timestamp'].iloc[i_va]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | dOI thresh {thresh:.2f}%")
    print(f"  trades {len(r.trades)} | expectancy ${r.expectancy:+,.2f}/t | "
          f"win {r.win_rate*100:.1f}% | return {r.total_return_pct:+.1f}% | "
          f"maxDD {r.max_drawdown_pct:.1f}% | median hold {med:.0f}h")
    verdict = "PASS" if (r.expectancy > 0 and len(r.trades) >= 8) else \
              ("THIN" if r.expectancy > 0 else "FAIL")
    print(f"  VERDICT: {verdict}")


if __name__ == "__main__":
    main()
