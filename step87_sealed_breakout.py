"""
step87_sealed_breakout.py — ROUND 87: THE SEALED EXAM for the volume-gated
Bollinger breakout selected in round 86.

CONFIG (frozen, pre-specified in round 86 on TRAIN expectancy only, on BTC —
NOT re-tuned here, per the exam's hard rules):

    Signal:      Bollinger Band breakout, period 20, 2.5 std
    Entry gate:  breakout bar's OWN volume >= 1.2x its trailing 20-bar
                 average volume, checked only at the 0->nonzero transition
                 bar (R76/R86 convention — unchanged)
    Exit:        close back through the band's midline (no fixed stop/target)
    Timeframe:   1h
    Assets:      BTC and ETH (one candidate, two assets)

IMPORTED, not reimplemented: bollinger_breakout_signal, volume_gate_entry,
BREAKOUT_CONFIGS, and the data/meta loaders load_frames / build_meta, all
from step86_specified.py — the exact functions step86 itself called. score()
and split_points() are imported from step43_daytrade (step86's own import
source) to reproduce the identical chronological 60/20/20 split and the
identical train/val scoring call. run_backtest is imported from backtest.py
to evaluate the previously-untouched final 20% (test) slice with the exact
same call shape score() uses internally (same CostModel defaults,
execution="maker", real funding via align_funding — nothing new is coded).

Only new code in this file: (1) a reproduction check that re-runs step86's
train/val numbers for this exact config and asserts they match, and (2) a
`run_test_slice()` function that is a direct copy of score()'s inner `run()`
closure, just pointed at [i_va:n] instead of [0:i_tr] / [i_tr:i_va] — no
signal, gate, cost, or split logic is altered.

ZERO parameter selection performed here. One config, one look, both assets.
RESEARCH ONLY. No commits, no live orders, no live-file edits.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step43_daytrade import score, split_points
from step86_specified import (
    BREAKOUT_CONFIGS,
    bollinger_breakout_signal,
    build_meta,
    load_frames,
    volume_gate_entry,
)

pd.set_option("display.width", 140)

CFG_NAME = "Bollinger breakout 20/2.5"
VMULT = 1.2
TF = "1h"

# round 86's reported numbers for this exact config, for the reproduction check
R86_EXPECTED = {
    "BTC": {"train": 14.87, "val": 5.21, "trades_yr": 203},
    "ETH": {"train": 39.59, "val": 26.01, "trades_yr": 196},
}
REPRO_TOL = 0.05   # relative tolerance (5%) — floating point / lib version drift only


def gated_signal(d):
    """Exactly family_c's construction in step86_specified.py: base Bollinger
    breakout signal, then volume_gate_entry at vmult=1.2, tf=1h."""
    assert CFG_NAME in BREAKOUT_CONFIGS
    base_sig = bollinger_breakout_signal(d)
    vol_avg20 = d["volume"].rolling(20).mean().shift(1)
    vol_ok = d["volume"] >= VMULT * vol_avg20
    return volume_gate_entry(base_sig, vol_ok)


def run_test_slice(d, sig, f, i_va, n):
    """Identical in shape to step43_daytrade.score()'s inner run() closure,
    pointed at the sealed final-20% slice [i_va:n] instead of train/val. Same
    CostModel defaults (via run_backtest's own default construction), same
    execution='maker', same real funding_series alignment. No stop_pct /
    target_pct — this config exits purely on the base signal's own midline
    cross, exactly as family_c calls score() with stop_pct=target_pct=None."""
    return run_backtest(
        d.iloc[i_va:n].reset_index(drop=True),
        sig.iloc[i_va:n].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[i_va:n].reset_index(drop=True),
        stop_pct=None, target_pct=None,
    )


def trades_per_year_slice(result, d, lo, hi):
    n = len(result.trades)
    if n == 0 or hi <= lo:
        return float("nan")
    t0 = d["timestamp"].iloc[lo]
    t1 = d["timestamp"].iloc[hi - 1]
    span_yrs = (t1 - t0).total_seconds() / (365.25 * 86400)
    return round(n / span_yrs, 2) if span_yrs > 0 else float("nan")


def longest_losing_streak(trades):
    longest = cur = 0
    for t in trades:
        if not t.is_win:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return longest


def summarize(result, label):
    n = len(result.trades)
    wins = [t.pnl for t in result.trades if t.is_win]
    losses = [t.pnl for t in result.trades if not t.is_win]
    return {
        "label": label,
        "n_trades": n,
        "expectancy": result.expectancy,
        "total_pnl": float(sum(t.pnl for t in result.trades)) if n else 0.0,
        "win_rate_pct": result.win_rate * 100,
        "avg_win": float(np.mean(wins)) if wins else 0.0,
        "avg_loss": float(np.mean(losses)) if losses else 0.0,   # negative
        "max_dd_pct": result.max_drawdown_pct,
        "longest_losing_streak": longest_losing_streak(result.trades),
    }


def main():
    print("=" * 78)
    print("ROUND 87 — SEALED EXAM: volume-gated Bollinger breakout (BTC + ETH, 1h)")
    print("=" * 78)

    print("\nLoading cached data (no network calls expected)...")
    frames_btc, funding_btc = load_frames("BTCUSDT")
    frames_eth, funding_eth = load_frames("ETHUSDT")
    meta_btc = build_meta(frames_btc)
    meta_eth = build_meta(frames_eth)

    all_rows = []
    repro_ok = True
    per_asset = {}

    for asset, frames, funding, meta in (
        ("BTC", frames_btc, funding_btc, meta_btc),
        ("ETH", frames_eth, funding_eth, meta_eth),
    ):
        d, f = frames[TF], funding[TF]
        n, i_tr, i_va = split_points(d)
        assert (n, i_tr, i_va) == (meta[TF]["n"], meta[TF]["i_tr"], meta[TF]["i_va"])

        sig = gated_signal(d)

        # ---- Reproduction check: re-run train + val exactly as step86 did ----
        tr, va = score(d, sig, f, i_tr, i_va, execution="maker")
        exp_tr, exp_va = R86_EXPECTED[asset]["train"], R86_EXPECTED[asset]["val"]
        ok_tr = abs(tr.expectancy - exp_tr) <= REPRO_TOL * abs(exp_tr)
        ok_va = abs(va.expectancy - exp_va) <= REPRO_TOL * abs(exp_va)
        trades_yr_trval = round((len(tr.trades) + len(va.trades)) /
                                 ((d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0])
                                  .total_seconds() / (365.25 * 86400)), 1)

        print(f"\n[{asset}] REPRODUCTION CHECK (train/val, config frozen from R86)")
        print(f"  train: n={len(tr.trades)}  exp=${tr.expectancy:+.2f}/trade  "
              f"(R86 reported ${exp_tr:+.2f})  {'MATCH' if ok_tr else 'MISMATCH'}")
        print(f"  val:   n={len(va.trades)}  exp=${va.expectancy:+.2f}/trade  "
              f"(R86 reported ${exp_va:+.2f})  {'MATCH' if ok_va else 'MISMATCH'}")
        print(f"  trades/yr (train+val pooled): {trades_yr_trval} "
              f"(R86 reported ~{R86_EXPECTED[asset]['trades_yr']})")

        repro_ok = repro_ok and ok_tr and ok_va

        # ---- Sealed test slice: [i_va:n], never touched before this run ----
        test_result = run_test_slice(d, sig, f, i_va, n)
        test_stats = summarize(test_result, f"{asset} SEALED TEST")
        test_stats["trades_yr"] = trades_per_year_slice(test_result, d, i_va, n)
        test_stats["span_start"] = str(d["timestamp"].iloc[i_va])
        test_stats["span_end"] = str(d["timestamp"].iloc[n - 1])
        test_stats["verdict"] = "PASS" if test_result.expectancy > 0 else "FAIL"

        per_asset[asset] = {
            "train": summarize(tr, f"{asset} train"),
            "val": summarize(va, f"{asset} val"),
            "test": test_stats,
        }

        print(f"\n[{asset}] SEALED TEST SLICE ({test_stats['span_start']} -> "
              f"{test_stats['span_end']})")
        print(f"  trades: {test_stats['n_trades']}   trades/yr: {test_stats['trades_yr']}")
        print(f"  expectancy/trade: ${test_stats['expectancy']:+.2f}   "
              f"total PnL: ${test_stats['total_pnl']:+.2f}")
        print(f"  win rate: {test_stats['win_rate_pct']:.1f}%   "
              f"avg win: ${test_stats['avg_win']:+.2f}   avg loss: ${test_stats['avg_loss']:+.2f}")
        print(f"  max drawdown: {test_stats['max_dd_pct']:.2f}%   "
              f"longest losing streak: {test_stats['longest_losing_streak']}")
        print(f"  VERDICT: {test_stats['verdict']}")

        for split_name, res in (("train", tr), ("val", va), ("test", test_result)):
            for t in res.trades:
                all_rows.append({
                    "asset": asset, "split": split_name,
                    "entry_time": t.entry_time, "exit_time": t.exit_time,
                    "direction": t.direction, "entry_price": t.entry_price,
                    "exit_price": t.exit_price, "units": t.units,
                    "fees": t.fees, "funding": t.funding, "pnl": t.pnl,
                    "is_win": t.is_win,
                })

    # ---- Pooled (BTC + ETH) sealed-test view ----
    btc_test = per_asset["BTC"]["test"]
    eth_test = per_asset["ETH"]["test"]
    pooled_n = btc_test["n_trades"] + eth_test["n_trades"]
    pooled_pnl = btc_test["total_pnl"] + eth_test["total_pnl"]
    pooled_exp = pooled_pnl / pooled_n if pooled_n else float("nan")
    pooled_wins = (btc_test["win_rate_pct"] / 100 * btc_test["n_trades"] +
                   eth_test["win_rate_pct"] / 100 * eth_test["n_trades"])
    pooled_winrate = pooled_wins / pooled_n * 100 if pooled_n else float("nan")

    print("\n" + "=" * 78)
    print("POOLED (BTC + ETH) SEALED TEST")
    print("=" * 78)
    print(f"  trades: {pooled_n}   total PnL: ${pooled_pnl:+.2f}   "
          f"expectancy/trade: ${pooled_exp:+.2f}   win rate: {pooled_winrate:.1f}%")
    pooled_verdict = "PASS" if pooled_exp > 0 else "FAIL"
    print(f"  VERDICT (pooled): {pooled_verdict}")

    print("\n" + "=" * 78)
    print(f"REPRODUCTION CHECK OVERALL: {'PASSED' if repro_ok else 'FAILED'}")
    print("=" * 78)
    if not repro_ok:
        print("STOP: train/val did not reproduce R86's figures within tolerance. "
              "Per the exam's hard rules, do NOT trust the sealed-test numbers above "
              "as a clean read — the split or signal likely drifted. Report this "
              "mismatch instead of the sealed result as a pass/fail verdict.")

    trades_df = pd.DataFrame(all_rows)
    trades_df.to_csv("step87_table.csv", index=False)
    print(f"\nwrote step87_table.csv: {len(trades_df)} per-trade rows "
          f"(train+val+test, both assets)")

    return per_asset, repro_ok, {
        "pooled_n": pooled_n, "pooled_pnl": pooled_pnl,
        "pooled_exp": pooled_exp, "pooled_winrate": pooled_winrate,
        "pooled_verdict": pooled_verdict,
    }


if __name__ == "__main__":
    main()
