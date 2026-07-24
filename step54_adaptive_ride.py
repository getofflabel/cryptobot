"""
step54_adaptive_ride.py — round 54: UNTHROTTLE THE BTC RIDE.

Run:  python3 step54_adaptive_ride.py

CONTEXT (read RESEARCH_LOG.md rounds 3-8 / 30 / 31 for the full history;
this docstring only restates what's load-bearing for this round):

The live 4h trend champion (strategy.vol_gated_ma / vol_filtered_ma,
fast=20/slow=100, FIXED min_atr_pct=1.5, live -8% SL) is a FIXED ATR% gate:
enter longs only when 14-period ATR is >= 1.5% of price. As of 2026-07-22
the live 4h ATR% is 0.95% — BELOW the gate — and the gate has been open
only 18.7% of bars in the trailing 3 months (53.5% across the full ~6.3y
cached history). Round 30 (the 15-year Bitstamp daily backtest) proved the
structural cause: BTC's volatility has DECAYED era over era, and found that
an ADAPTIVE gate (current ATR% vs its own trailing-365d median, not a fixed
number) survives every era on daily data ($1k->$187k vs fixed's $11k) where
the fixed gate goes completely dead by 2023. Round 30 also transferred a
SINGLE adaptive variant (mult=1.3x trailing median) to the live 4h
train/val gauntlet and it did NOT beat the champion on val (+26.4% vs
+63.9%) — belt retained, ZERO test looks spent, and the finding was logged
as a standing risk to monitor, not a closed case. Round 31 separately
gauntleted a GARCH-percentile REPLACEMENT of the gate (different
mechanism, thresholds 50/60/70th percentile) on a shorter common window
(2022-02 on) — also FAILED train, zero test looks spent, family CLOSED.

WHAT THIS ROUND ADDS THAT ROUND 30/31 DID NOT COVER:
  - fresh data through 2026-07 (round 30's 4h transfer used older data;
    this is the regime that actually strangled the live book)
  - the exact 1.0x and 0.8x trailing-median multipliers (round 30 only
    ever tried 1.3x on 4h — a stricter gate than the plain "above median"
    prescription; never tried mild-tolerance 0.8x either)
  - a robustness sibling MA pair (50,200), not just the champion's own
    (20,100)
  - the live book's actual -8% crash stop_pct as a first-class grid axis
    (round 30's 4h transfer did not model a stop)
  - the frequency/gate-open-share diagnostics the owner explicitly wants
    (this is a NEW angle, not previously reported anywhere in the log)

This is therefore a legitimate re-look, not a repeat of a spent look:
different thresholds, fresher data, an added MA pair, an added stop axis,
and entirely new diagnostics. Per round 30's own precedent (train/val
screen, no test look unless something clears the bar), THIS SCRIPT NEVER
TOUCHES THE SEALED FINAL 20% (test). Only train (0:i_tr) and val
(i_tr:i_va) are ever computed, scored, or printed as PERFORMANCE numbers.
The gate-open-share diagnostic (a property of price/ATR data, not of any
strategy's PnL) is reported over the FULL cached window including the
calendar dates that fall inside the test slice — this reveals nothing
about test-period returns, only how often an indicator would have fired,
and the owner's own brief already discloses the current live ATR% and a
trailing-3-month gate-open figure computed exactly this way.

GRID (kept modest — a surgical revalidation, not a fishing trip):
  MA pairs   : (20,100) champion, (50,200) robustness sibling
  gates      : adaptive-1.0x (== "above trailing median", round 30's own
               prescription), adaptive-0.8x (mild tolerance band),
               fixed-1.5 (live incumbent baseline), ungated (baseline)
  stops      : none, -8% crash SL (the live book's actual stop)
  timeframe  : 4h only (the champion's home)
  -> 2 x 4 x 2 = 16 configs, long-only, maker execution, real funding,
     costs always on, chronological 60/20/20, select by TRAIN only.

Verdict floor: >=30 train trades, >=8 val trades, positive expectancy both
windows to earn SURVIVOR. Below the trade floor but positive both windows
= INSUFFICIENT-SAMPLE (still reported, never promoted to candidate).
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import bar_hours, split_points   # reuse the gauntlet plumbing
from strategy import atr, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
LIVE_SL_PCT = 8.0

pd.set_option("display.width", 220)


# ---------------------------------------------------------------------------
# adaptive gate, WITH a multiplier (step41's adaptive_vol_gate is mult=1.0
# only; this generalizes it for the 0.8x/1.0x grid). Same no-lookahead
# convention: trailing median is an expanding-then-rolling median computed
# strictly on PAST bars, shift(1)'d so the current bar's own ATR is never
# part of the median it's compared against.
# ---------------------------------------------------------------------------

def adaptive_gate(d, mult=1.0, window_days=365, atr_n=14):
    a_pct = atr(d, atr_n) / d["close"] * 100
    window = max(30, round(24 / bar_hours(d) * window_days))
    min_periods = max(30, window // 10)
    trailing_med = a_pct.rolling(window, min_periods=min_periods).median().shift(1)
    gate = a_pct >= mult * trailing_med
    return gate.fillna(False), a_pct, trailing_med


def gate_open_share(mask, bool_series):
    sub = bool_series[mask]
    return float(sub.mean() * 100) if len(sub) else float("nan")


# ---------------------------------------------------------------------------
# signal builder for the grid
# ---------------------------------------------------------------------------

def build_signal(d, fast, slow, gate_mode):
    if gate_mode == "ungated":
        return vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False)
    if gate_mode == "fixed-1.5":
        return vol_gated_ma(d, fast, slow, min_atr_pct=1.5, allow_short=False)
    if gate_mode == "adaptive-1.0x":
        gate, _, _ = adaptive_gate(d, mult=1.0)
        return vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False,
                             entry_filter=gate)
    if gate_mode == "adaptive-0.8x":
        gate, _, _ = adaptive_gate(d, mult=0.8)
        return vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False,
                             entry_filter=gate)
    raise ValueError(gate_mode)


def score(d, sig, f, i_tr, i_va, stop_pct=None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution="maker",
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def recent_entries(trades, boundary_time, months=18):
    """Count trade ENTRIES whose entry_time falls in the last `months` months
    of the train+val period (i.e. right up against the sealed test boundary,
    never past it — `boundary_time` is the val end / test start)."""
    cutoff = boundary_time - pd.DateOffset(months=months)
    return sum(1 for t in trades if cutoff <= t.entry_time < boundary_time)


def mk_row(fast, slow, gate_mode, stop_label, tr, va, tr_va_years,
           boundary_time):
    all_trades = list(tr.trades) + list(va.trades)
    entries_total = len(all_trades)
    entries_per_year = entries_total / tr_va_years if tr_va_years else float("nan")
    recent = recent_entries(all_trades, boundary_time, months=18)
    return {
        "ma": f"{fast}/{slow}", "gate": gate_mode, "stop": stop_label,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
        "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
        "va_ret%": va.total_return_pct,
        "entries/yr": entries_per_year,
        "recent_entries_18mo": recent,
        "verdict": verdict_for(tr, va),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached 4h BTC data + real funding (no network calls needed)...")
    d = fetch_bybit_deep("4h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    f = align_funding(d, funding_hist)

    n, i_tr, i_va = split_points(d)
    t0, t_tr, t_va, t_end = (d["timestamp"].iloc[0], d["timestamp"].iloc[i_tr],
                              d["timestamp"].iloc[i_va], d["timestamp"].iloc[-1])
    tr_va_years = (t_va - t0).days / 365.25
    print(f"  4h: {n} bars, {t0:%Y-%m-%d} -> {t_end:%Y-%m-%d} | "
          f"train->{t_tr:%Y-%m-%d} val->{t_va:%Y-%m-%d} (test sealed, "
          f"NEVER computed below) | train+val span = {tr_va_years:.2f}y")

    # -----------------------------------------------------------------
    # ANALYSIS 1: GATE-OPEN SHARE (indicator-level diagnostic, no PnL,
    # computed over the FULL cached window including recent calendar
    # dates — reveals gate on/off frequency only, not test performance).
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("GATE-OPEN SHARE — fixed 1.5% vs adaptive (1.0x / 0.8x trailing median)")
    print("=" * 78)
    fixed_gate = (atr(d, 14) / d["close"] * 100) >= 1.5
    adapt10, atr_pct, trail_med = adaptive_gate(d, mult=1.0)
    adapt08, _, _ = adaptive_gate(d, mult=0.8)
    defined = trail_med.notna()

    mask_6y = defined
    mask_12mo = defined & (d["timestamp"] >= t_end - pd.Timedelta(days=365))
    mask_3mo = defined & (d["timestamp"] >= t_end - pd.Timedelta(days=90))

    gate_rows = []
    for label, mask in (("full ~6.3y history", mask_6y),
                         ("trailing 12mo", mask_12mo),
                         ("trailing 3mo", mask_3mo)):
        gate_rows.append({
            "window": label,
            "fixed-1.5 open%": gate_open_share(mask, fixed_gate),
            "adaptive-1.0x open%": gate_open_share(mask, adapt10),
            "adaptive-0.8x open%": gate_open_share(mask, adapt08),
        })
    gate_df = pd.DataFrame(gate_rows)
    print(gate_df.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    print(f"\n  live ATR% right now (last bar, {t_end:%Y-%m-%d}): "
          f"{atr_pct.iloc[-1]:.2f}%  |  trailing-365d median right now: "
          f"{trail_med.iloc[-1]:.2f}%")

    # -----------------------------------------------------------------
    # ANALYSIS 2: full grid, train/val only, test NEVER computed.
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("FULL GRID — train / val, maker execution, real funding, costs on")
    print("=" * 78)
    rows = []
    for fast, slow in ((20, 100), (50, 200)):
        for gate_mode in ("adaptive-1.0x", "adaptive-0.8x", "fixed-1.5", "ungated"):
            sig = build_signal(d, fast, slow, gate_mode)
            for stop_pct, stop_label in ((None, "none"), (LIVE_SL_PCT, "SL-8%")):
                tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct)
                rows.append(mk_row(fast, slow, gate_mode, stop_label, tr, va,
                                    tr_va_years, t_va))

    df = pd.DataFrame(rows)
    with pd.option_context("display.max_rows", None):
        print(df.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    # Deliverables for this round are step54_adaptive_ride.py + step54_results.md
    # ONLY — no side files. Everything above is printed for the results.md
    # write-up to be drawn from; nothing is written to disk here.

    # -----------------------------------------------------------------
    # ANALYSIS 3: head-to-head, champion MA pair (20,100), no-stop AND
    # SL-8%: adaptive-1.0x vs fixed-1.5 (incumbent) vs ungated.
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("HEAD-TO-HEAD — (20,100), adaptive-1.0x vs fixed-1.5 (incumbent) vs ungated")
    print("=" * 78)
    h2h = df[(df["ma"] == "20/100") &
             (df["gate"].isin(["adaptive-1.0x", "fixed-1.5", "ungated"]))]
    print(h2h.sort_values(["stop", "gate"])
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # -----------------------------------------------------------------
    # ANALYSIS 4: candidate selection — best adaptive config, selected
    # by TRAIN expectancy, must also beat fixed-1.5 on TRAIN and VAL,
    # clear the trade floor, and show healthy recent entries.
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("CANDIDATE SCREEN")
    print("=" * 78)
    adaptive_rows = df[df["gate"].isin(["adaptive-1.0x", "adaptive-0.8x"])].copy()
    adaptive_rows = adaptive_rows.sort_values("tr_exp", ascending=False)
    print("Adaptive configs ranked by TRAIN expectancy:")
    print(adaptive_rows.to_string(index=False,
                                   float_format=lambda x: f"{x:,.2f}"))

    candidate = None
    for _, r in adaptive_rows.iterrows():
        fixed_match = df[(df["ma"] == r["ma"]) & (df["gate"] == "fixed-1.5") &
                          (df["stop"] == r["stop"])].iloc[0]
        beats_fixed_train = r["tr_exp"] > fixed_match["tr_exp"]
        beats_fixed_val = r["va_exp"] > fixed_match["va_exp"]
        healthy_sample = r["tr_n"] >= MIN_TRAIN_TRADES and r["va_n"] >= MIN_VAL_TRADES
        healthy_recent = r["recent_entries_18mo"] >= 3     # still trading recently
        positive_both = r["tr_exp"] > 0 and r["va_exp"] > 0
        if (beats_fixed_train and beats_fixed_val and healthy_sample
                and healthy_recent and positive_both):
            candidate = r
            break

    if candidate is not None:
        print(f"\nCANDIDATE FOUND: ma={candidate['ma']} gate={candidate['gate']} "
              f"stop={candidate['stop']}")
        print(candidate.to_string())
    else:
        print("\nNO CANDIDATE: no adaptive config beat the fixed-1.5 incumbent on "
              "BOTH train and val with adequate samples and healthy recent-entry "
              "counts. 'Keep the throttle' stands unless overridden by the "
              "head-to-head / frequency evidence above.")

    return df, gate_df


if __name__ == "__main__":
    main()
