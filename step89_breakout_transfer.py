"""
step89_breakout_transfer.py — ROUND 89: DOES THE SEALED-PASSED BREAKOUT WORK
ON ASSETS IT HAS NEVER SEEN?

R87 sealed-tested one frozen config (volume-gated Bollinger breakout, 1h) on
BTC and ETH only. BTC passed cleanly (durable across train/val/sealed-test).
ETH passed but degraded monotonically across all three windows and was
flagged fragile. This round asks whether the edge is a general market-
structure effect or a two-asset coincidence, by replaying the EXACT frozen
config on assets that have never been looked at for this strategy at all —
their entire history is genuinely out-of-sample, with zero selection.

CONFIG UNDER TEST (frozen, unchanged from round 86/87 — nothing here was
re-tuned):

    Signal:      Bollinger Band breakout, period 20, 2.5 std
    Entry gate:  breakout bar's OWN volume >= 1.2x its trailing 20-bar
                 average volume, checked only at the 0->nonzero transition
                 bar (R76/R86/R87 convention — unchanged)
    Exit:        close back through the band's midline (no fixed stop/target)
    Timeframe:   1h
    Costs:       CostModel defaults, execution="maker", real funding via
                 align_funding — identical to R86/R87, always on

CODE PROVENANCE (hard rule): `bollinger_breakout_signal`, `volume_gate_entry`,
`BREAKOUT_CONFIGS`, and `load_frames` are IMPORTED from step86_specified.py,
verbatim, not retyped. `score` and `split_points` are imported from
step43_daytrade.py (step86's own import source), reused to reproduce the
identical chronological 60/20/20 split. `run_backtest` is imported from
backtest.py.

ONE DELIBERATE EFFICIENCY DEVIATION, stated plainly: `load_frames()` (as
written in step86_specified.py) fetches THREE timeframes (15m, 1h, 4h) per
asset, but this round's frozen config only ever touches "1h". Fetching 15m
history for 9 new assets (each requiring 150-250 paginated API calls) would
burn ~15-20 minutes of pure network time for data this round never reads.
So this script calls the SAME underlying primitives `load_frames` itself
calls — `fetch_bybit_deep` (imported from step7_deep_search, load_frames'
own import source) and `fetch_funding_history` / `align_funding` (imported
from step11_round6, load_frames' own import source) — but only for "1h".
This is NOT a change to the signal, gate, exit, timeframe, or cost model;
it is purely which unused timeframes get downloaded. Nothing about the
strategy under test is touched.

Writes ONLY: step89_breakout_transfer.py (this file), step89_results.md,
step89_table.csv. RESEARCH ONLY. No commits, no live orders, no live-file
edits.
"""

import time

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import MIN_TRAIN_TRADES, MIN_VAL_TRADES, score, split_points
from step86_specified import (
    BREAKOUT_CONFIGS,
    bollinger_breakout_signal,
    volume_gate_entry,
)
from strategy import atr

pd.set_option("display.width", 160)

CFG_NAME = "Bollinger breakout 20/2.5"
VMULT = 1.2
TF = "1h"

# Assets this round has NEVER been looked at for this strategy — the brief's
# named three, plus additional Bybit-servable perps chosen for a spread of
# liquidity/age/volatility so the pooled correlation read has something to
# work with. Nothing here was cherry-picked on performance — this is the
# full list decided BEFORE any backtest in this script ran.
NEW_ASSETS = [
    ("SOL", "SOLUSDT"),
    ("XRP", "XRPUSDT"),
    ("DOGE", "DOGEUSDT"),
    ("BNB", "BNBUSDT"),
    ("ADA", "ADAUSDT"),
    ("LINK", "LINKUSDT"),
    ("AVAX", "AVAXUSDT"),
    ("LTC", "LTCUSDT"),
    ("DOT", "DOTUSDT"),
]

# R87's already-sealed, already-published BTC/ETH numbers, REFERENCED here
# (not recomputed) for the pooled cross-asset view requested by this round.
# Re-running the sealed test slice a second time would not "un-burn" it and
# would not change these numbers (deterministic script, no new tuning) — but
# to avoid any appearance of a second "look", the published figures from
# step87_results.md are quoted directly instead of re-executed.
R87_SEALED = {
    "BTC": {"n": 242, "exp": 6.97, "total_pnl": 1687.38, "win_rate_pct": 36.4,
            "avg_win": 196.81, "avg_loss": -101.51, "trades_yr": 191.2,
            "max_dd_pct": -23.33, "streak": 11,
            "span": "2025-04-18 to 2026-07-24 (~15.3mo)"},
    "ETH": {"n": 226, "exp": 9.68, "total_pnl": 2188.75, "win_rate_pct": 37.6,
            "avg_win": 319.61, "avg_loss": -177.15, "trades_yr": 210.9,
            "max_dd_pct": -35.01, "streak": 6,
            "span": "2025-06-28 to 2026-07-24 (~13.0mo)"},
}

MIN_MEANINGFUL_TRADES = 30  # below this on the pooled full-history run: INSUFFICIENT SAMPLE


# ---------------------------------------------------------------------------
# Lean 1h-only loader (see module docstring for why this isn't load_frames)
# ---------------------------------------------------------------------------

def load_1h(symbol):
    d = fetch_bybit_deep("1h", symbol)
    fund_hist = fetch_funding_history(symbol)
    f = align_funding(d, fund_hist)
    return d, f


# ---------------------------------------------------------------------------
# Signal (imported pieces only — this function just wires them together,
# identical to family_c()'s construction in step86_specified.py)
# ---------------------------------------------------------------------------

def gated_signal(d):
    assert CFG_NAME in BREAKOUT_CONFIGS
    base_sig = bollinger_breakout_signal(d)
    vol_avg20 = d["volume"].rolling(20).mean().shift(1)
    vol_ok = d["volume"] >= VMULT * vol_avg20
    return volume_gate_entry(base_sig, vol_ok)


def run_window(d, sig, f, lo, hi):
    """Identical in shape to step43_daytrade.score()'s inner run() closure /
    step87's run_test_slice — same CostModel defaults, execution='maker',
    real funding, no fixed stop/target (exits purely on the base signal's
    own midline cross)."""
    return run_backtest(
        d.iloc[lo:hi].reset_index(drop=True),
        sig.iloc[lo:hi].reset_index(drop=True),
        execution="maker",
        funding_series=f.iloc[lo:hi].reset_index(drop=True),
        stop_pct=None, target_pct=None,
    )


def longest_losing_streak(trades):
    longest = cur = 0
    for t in trades:
        if not t.is_win:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0
    return longest


def trades_per_year_slice(n_trades, d, lo, hi):
    if n_trades == 0 or hi <= lo:
        return float("nan")
    t0 = d["timestamp"].iloc[lo]
    t1 = d["timestamp"].iloc[hi - 1]
    span_yrs = (t1 - t0).total_seconds() / (365.25 * 86400)
    return round(n_trades / span_yrs, 2) if span_yrs > 0 else float("nan")


def worst_adverse_excursion_pct(d, trades):
    """For every trade, the max % move against the open position, measured
    from the entry fill price using the underlying candle highs/lows from
    the entry bar through the exit bar (inclusive) — the true intrabar
    worst point, not just the eventual exit price. Returns the WORST (max)
    value across the given trade list, plus which trade produced it. This
    metric does NOT exist anywhere in R86 or R87's code (checked directly —
    grep for "adverse"/"MAE" in step86/87 returns nothing); it is computed
    fresh here despite the round-89 brief's claim that R87 already did this."""
    if not trades:
        return None
    ts = d["timestamp"]
    idx_of = pd.Series(np.arange(len(ts)), index=ts)  # timestamp -> position
    worst = None
    for t in trades:
        try:
            i0 = int(idx_of.loc[t.entry_time])
            i1 = int(idx_of.loc[t.exit_time])
        except KeyError:
            continue
        if i1 < i0:
            continue
        window = d.iloc[i0:i1 + 1]
        if t.direction > 0:
            mae = (t.entry_price - window["low"].min()) / t.entry_price * 100
        else:
            mae = (window["high"].max() - t.entry_price) / t.entry_price * 100
        mae = max(0.0, float(mae))
        if worst is None or mae > worst[0]:
            worst = (mae, str(t.entry_time), str(t.exit_time), t.direction)
    return worst


def summarize(result, label, d=None, lo=None, hi=None):
    n = len(result.trades)
    wins = [t.pnl for t in result.trades if t.is_win]
    losses = [t.pnl for t in result.trades if not t.is_win]
    row = {
        "label": label,
        "n_trades": n,
        "expectancy": result.expectancy,
        "total_pnl": float(sum(t.pnl for t in result.trades)) if n else 0.0,
        "win_rate_pct": result.win_rate * 100,
        "avg_win": float(np.mean(wins)) if wins else 0.0,
        "avg_loss": float(np.mean(losses)) if losses else 0.0,
        "max_dd_pct": result.max_drawdown_pct,
        "longest_losing_streak": longest_losing_streak(result.trades),
    }
    if d is not None and lo is not None and hi is not None:
        row["trades_yr"] = trades_per_year_slice(n, d, lo, hi)
    return row


def asset_meta(d, i_tr):
    """Liquidity / volatility / age proxies, computed on the TRAIN window
    only (no lookahead into val/test), for the pooled correlation read."""
    med_dollar_vol = float((d["close"] * d["volume"]).iloc[:i_tr].median())
    atr_pct = (atr(d, 14) / d["close"] * 100).iloc[:i_tr]
    med_atr_pct = float(atr_pct.median())
    years_history = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).total_seconds() / (365.25 * 86400)
    return {
        "med_dollar_vol_per_bar": med_dollar_vol,
        "med_atr_pct": med_atr_pct,
        "years_cached_history": round(years_history, 2),
    }


def main():
    print("=" * 78)
    print("ROUND 89 — TRANSFER TEST: volume-gated Bollinger breakout on unseen assets")
    print("=" * 78)
    print(f"\nImported (not retyped): bollinger_breakout_signal, volume_gate_entry, "
          f"BREAKOUT_CONFIGS from step86_specified.py; score, split_points, "
          f"MIN_TRAIN_TRADES, MIN_VAL_TRADES from step43_daytrade.py; run_backtest "
          f"from backtest.py. NOT using step86's load_frames() as-is (see module "
          f"docstring) — instead calling its own underlying primitives "
          f"(fetch_bybit_deep, fetch_funding_history, align_funding) for '1h' only, "
          f"since this config never touches 15m/4h.")

    per_asset = {}
    all_trade_rows = []

    for label, symbol in NEW_ASSETS:
        print(f"\n--- {label} ({symbol}) ---")
        t0 = time.time()
        d, f = load_1h(symbol)
        print(f"  loaded {len(d)} 1h bars ({d['timestamp'].iloc[0]} to "
              f"{d['timestamp'].iloc[-1]}) in {time.time() - t0:.1f}s")

        n, i_tr, i_va = split_points(d)
        sig = gated_signal(d)

        tr = run_window(d, sig, f, 0, i_tr)
        va = run_window(d, sig, f, i_tr, i_va)
        te = run_window(d, sig, f, i_va, n)
        full = run_window(d, sig, f, 0, n)

        tr_s = summarize(tr, f"{label} train", d, 0, i_tr)
        va_s = summarize(va, f"{label} val", d, i_tr, i_va)
        te_s = summarize(te, f"{label} test", d, i_va, n)
        full_s = summarize(full, f"{label} full-history (pooled)", d, 0, n)

        mae = worst_adverse_excursion_pct(d, full.trades)
        meta = asset_meta(d, i_tr)

        insufficient = full_s["n_trades"] < MIN_MEANINGFUL_TRADES
        verdict = ("INSUFFICIENT SAMPLE" if insufficient
                    else ("PASS" if full_s["expectancy"] > 0 else "FAIL"))

        per_asset[label] = {
            "symbol": symbol, "train": tr_s, "val": va_s, "test": te_s,
            "full": full_s, "mae": mae, "meta": meta, "verdict": verdict,
            "n_bars": len(d),
        }

        print(f"  train n={tr_s['n_trades']:4d} exp=${tr_s['expectancy']:+8.2f}   "
              f"val n={va_s['n_trades']:4d} exp=${va_s['expectancy']:+8.2f}   "
              f"test n={te_s['n_trades']:4d} exp=${te_s['expectancy']:+8.2f}")
        print(f"  FULL-HISTORY: n={full_s['n_trades']} exp=${full_s['expectancy']:+.2f} "
              f"total_pnl=${full_s['total_pnl']:+.2f} win%={full_s['win_rate_pct']:.1f} "
              f"trades/yr={full_s['trades_yr']} max_dd={full_s['max_dd_pct']:.2f}% "
              f"streak={full_s['longest_losing_streak']}  VERDICT={verdict}")
        if mae:
            print(f"  worst adverse excursion (any trade, full history): {mae[0]:.2f}%  "
                  f"(entry {mae[1]}, dir {mae[3]:+d})")

        for split_name, res in (("train", tr), ("val", va), ("test", te)):
            for t in res.trades:
                all_trade_rows.append({
                    "asset": label, "symbol": symbol, "split": split_name,
                    "entry_time": t.entry_time, "exit_time": t.exit_time,
                    "direction": t.direction, "entry_price": t.entry_price,
                    "exit_price": t.exit_price, "units": t.units,
                    "fees": t.fees, "funding": t.funding, "pnl": t.pnl,
                    "is_win": t.is_win,
                })

    # ---- Pooled view across ALL assets (new + R87's already-sealed BTC/ETH) ----
    print("\n" + "=" * 78)
    print("POOLED SUMMARY — every asset, new + R87's sealed BTC/ETH")
    print("=" * 78)

    pooled_rows = []
    for asset, r87 in R87_SEALED.items():
        pooled_rows.append({
            "asset": asset, "source": "R87 sealed test", "n_trades": r87["n"],
            "expectancy": r87["exp"], "trades_yr": r87["trades_yr"],
            "verdict": "PASS",
        })
    for label, r in per_asset.items():
        pooled_rows.append({
            "asset": label, "source": "R89 full-history (new)",
            "n_trades": r["full"]["n_trades"], "expectancy": r["full"]["expectancy"],
            "trades_yr": r["full"]["trades_yr"], "verdict": r["verdict"],
        })
    pooled_df = pd.DataFrame(pooled_rows)
    print(pooled_df.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    n_pass = int((pooled_df["verdict"] == "PASS").sum())
    n_total = len(pooled_df)
    trades_yr_if_all_pass_run = float(
        pooled_df.loc[pooled_df["verdict"] == "PASS", "trades_yr"].sum())
    print(f"\n{n_pass} / {n_total} assets PASS.")
    print(f"Total trades/year if every PASSing asset were run: {trades_yr_if_all_pass_run:.1f}")

    trades_df = pd.DataFrame(all_trade_rows)
    trades_df.to_csv("step89_table.csv", index=False)
    print(f"\nwrote step89_table.csv: {len(trades_df)} per-trade rows "
          f"(train+val+test, {len(NEW_ASSETS)} new assets)")
    # Per the round-89 file allowlist (step89_breakout_transfer.py,
    # step89_results.md, step89_table.csv only), the pooled cross-asset
    # summary is NOT written to its own CSV — it is folded into
    # step89_results.md instead.

    return per_asset, pooled_df


if __name__ == "__main__":
    main()
