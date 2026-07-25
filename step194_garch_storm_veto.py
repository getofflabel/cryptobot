"""
step194_garch_storm_veto.py — ROUND 194. THE GARCH STORM-VETO ON THE STRIKES.

Run:  python3 step194_garch_storm_veto.py

QUEUED HYPOTHESIS (RESEARCH_QUEUE.md, "GARCH era" docket, item #2 — the
item Round 31's log entry named as "next in queue" and which has never
been run):

    "GARCH storm-veto for strikes: skip entries when forecast > trailing p90"

The strikes book (tactical.py, BTC slot) fires on the 1h panic-dip: the 4h
champion must be in its bull state AND the last closed 1h bar's RSI(3) must
be under 15. Round 29 built walk-forward GARCH(1,1) daily-vol FORECASTS
(zero lookahead, refit every 21 days, cached in data_garch_btc_1d.parquet).
Round 31 asked whether that forecast could REPLACE the ride's ATR gate and
the answer was a clean no. This round asks the opposite-shaped question, on
a different book: not "does high forecast vol give the trend fuel" but
"does high forecast vol mean a dip-buy is standing in front of a truck."

WHY IT IS WORTH A ROUND EVEN THOUGH THE BOOK IS STOOD DOWN. Round 150
stood the strikes down for new entries: retested at taker execution with
real chart-structure stops the panic-dip ran -$70.09/trade on train and
-$69.54 on val, worse than chance twice. A pre-specified veto is exactly
the instrument that could either rescue a stood-down book or bury it for
good, and this one was specified back in Round 29 — before any of the bad
news — so it cannot be an after-the-fact rescue attempt fitted to the
failure. That is the only kind of rescue attempt this program allows.

CONFIG (frozen here, no tuning, no grids beyond the pre-specified one):
  SYMBOL : BTCUSDT (the live strikes symbol), Bybit 1h, full history.
  FILTER : 4h champion state == long (vol_gated_ma 20/100, min_atr_pct 1.5,
           funding <= 1bp), mapped onto 1h bars with no lookahead.
  TRIGGER: RSI(3) on the 1h close < 15.
  VETO   : SKIP the entry when the walk-forward GARCH daily-vol forecast
           for that day is >= its TRAILING EXPANDING p90 (min 180 days of
           baseline). Trailing = the quantile at day D uses only forecasts
           up to and including D, so no lookahead. Daily gate mapped onto
           1h bars backward, same as Round 31 did onto 4h.
  BRACKET: stop 1.5%, target 4.5%, hard exit after 48 bars (48h).
           These flat percentages are FAITHFUL here, not lazy: the live
           executor literally places a fixed +4.5% / -1.5% TP/SL bracket
           (tactical.py STOP_PCT / TARGET_PCT). Round 150's structure-stop
           retest asked a different and harder question and is not the
           model being reproduced in this round.
  EXEC   : TAKER — primary and decisive. The live book enters with
           execute_market_clips (market orders), so taker is what it
           actually pays. Round 15 validated this family at maker; that
           frame is reported below as a clearly-labelled REFERENCE ONLY and
           takes no part in qualification (Round 150's standing correction).
  FUNDING: real per-bar funding cashflows.
  WINDOW : the COMMON window on which the trailing p90 threshold exists, so
           the veto arm and its baseline are scored on identical bars.

DISCIPLINE:
- 60/20/20 train/val/test on the common window.
- Qualify = positive expectancy on train AND val, >= 30 train / >= 8 val
  trades, AND beating the un-vetoed baseline on both -> exactly ONE sealed
  test look. A veto that is merely positive while being WORSE than not
  vetoing is a failure, not a survivor.
- MULTIPLE-COMPARISONS DECLARATION (the standing rule earned in Round 88):
  exactly ONE cell decides this round — p90, taker. Expected to clear a
  90th-percentile chance bar by luck: 0.1 cells. Everything else printed
  (the maker reference frame, the p80/p95 neighbourhood) is ROBUSTNESS
  REPORTING and is explicitly barred from qualifying anything.
- CHANCE CONTROL (the standing rule earned in Round 100): the veto removes
  a specific set of trades. The honest control is not "is the kept set
  positive" but "is the kept set better than dropping the SAME NUMBER of
  trades at random from the same baseline." 400 random draws, percentile
  reported. A veto that cannot beat a coin flip is decoration.
- PLATEAU CHECK (the standing rule earned in Round 88): p80 and p95 are
  reported so the result can be read as a plateau or as a lone spike. They
  do not qualify anything; they only get to DISQUALIFY a lone spike.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step17_round12 import machine
from step20_round15 import champion_state_on_1h
from strategy import rsi

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

RSI_TH = 15
STOP_PCT = 1.5
TARGET_PCT = 4.5
MAX_HOLD = 48          # bars = hours, matches tactical.MAX_HOLD_H
MIN_BASELINE_DAYS = 180
N_DRAWS = 400
SEED = 194             # fixed so the control is reproducible

ROUND_TRIP_USD = 10_000.0 * CostModel().round_trip_bps() / 10_000.0   # $18/trade


def garch_gate_on_1h(d1: pd.DataFrame, thresh_q: float,
                     min_periods: int = MIN_BASELINE_DAYS):
    """(storm, thr_ok) per 1h bar. storm = the walk-forward GARCH daily-vol
    forecast for that day is at or above its TRAILING EXPANDING `thresh_q`
    quantile. Identical construction to step23_round31.garch_gate_on_4h,
    mapped onto 1h bars instead of 4h."""
    g = (pd.read_parquet("data_garch_btc_1d.parquet")
         .dropna(subset=["garch_daily_vol"]).reset_index(drop=True))
    v = g["garch_daily_vol"]
    thr = v.expanding(min_periods=min_periods).quantile(thresh_q)
    daily = pd.DataFrame({
        "effective": g["timestamp"],       # forecast known at the start of day D
        "storm": (v >= thr),
        "thr_ok": thr.notna(),
    })
    merged = pd.merge_asof(d1[["timestamp"]], daily,
                           left_on="timestamp", right_on="effective",
                           direction="backward")
    return (pd.Series(merged["storm"].fillna(False).to_numpy(), index=d1.index),
            pd.Series(merged["thr_ok"].fillna(False).to_numpy(), index=d1.index))


def score(d, sig, f, lo, hi, execution):
    return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True),
                        execution=execution,
                        stop_pct=STOP_PCT, target_pct=TARGET_PCT,
                        funding_series=f.iloc[lo:hi].reset_index(drop=True))


def row(tag, r_tr, r_va):
    return {
        "config": tag,
        "tr_n": len(r_tr.trades), "tr_exp": r_tr.expectancy,
        "tr_thick": r_tr.expectancy / ROUND_TRIP_USD,
        "tr_win%": r_tr.win_rate * 100,
        "va_n": len(r_va.trades), "va_exp": r_va.expectancy,
        "va_thick": r_va.expectancy / ROUND_TRIP_USD,
        "va_win%": r_va.win_rate * 100,
    }


def main():
    print("=" * 78)
    print("ROUND 194 — GARCH STORM-VETO ON THE STRIKES (1h panic-dip, BTC)")
    print("=" * 78)

    d1 = fetch_bybit_deep("1h", "BTCUSDT")
    d4 = fetch_bybit_deep("4h", "BTCUSDT")
    funding = fetch_funding_history("BTCUSDT")
    f1 = align_funding(d1, funding)
    f4 = align_funding(d4, funding)

    champ1h = champion_state_on_1h(d1, d4, f4)
    r3 = rsi(d1["close"], 3)
    raw_entry = (champ1h == 1) & (r3 < RSI_TH)

    # common window = where the trailing threshold exists at all
    _, thr_ok = garch_gate_on_1h(d1, 0.90)
    mask = thr_ok.to_numpy()
    first = int(np.argmax(mask)) if mask.any() else len(d1)

    dc = d1.iloc[first:].reset_index(drop=True)
    fc = f1.iloc[first:].reset_index(drop=True)
    entry_c = raw_entry.iloc[first:].reset_index(drop=True)
    n = len(dc)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)
    no_exit = pd.Series(False, index=dc.index)

    print(f"\nCommon window: {dc['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{dc['timestamp'].iloc[-1]:%Y-%m-%d}  ({n:,} 1h bars, "
          f"{(dc['timestamp'].iloc[-1] - dc['timestamp'].iloc[0]).days / 365:.1f} yrs)")
    print(f"  train ..{dc['timestamp'].iloc[i_tr-1]:%Y-%m-%d} | "
          f"val ..{dc['timestamp'].iloc[i_va-1]:%Y-%m-%d} | "
          f"test ..{dc['timestamp'].iloc[-1]:%Y-%m-%d} (SEALED)")
    print(f"  bracket: stop {STOP_PCT}% / target {TARGET_PCT}% / hold "
          f"{MAX_HOLD}h   |   round-trip cost ${ROUND_TRIP_USD:.2f}/trade")
    print(f"  raw panic-dip signal bars in window: {int(entry_c.sum()):,}")

    storm, _ = garch_gate_on_1h(d1, 0.90)
    storm_c = storm.iloc[first:].reset_index(drop=True)
    vetoed_c = entry_c & ~storm_c
    killed = int((entry_c & storm_c).sum())
    print(f"  signal bars the p90 storm-veto KILLS: {killed:,} "
          f"({killed / max(int(entry_c.sum()), 1) * 100:.1f}%)")

    sig_base = machine(dc, entry_c, no_exit, +1, MAX_HOLD)
    sig_veto = machine(dc, vetoed_c, no_exit, +1, MAX_HOLD)

    # ---------------- PRIMARY FRAME: taker (what the live book pays) -----
    print("\n" + "-" * 78)
    print("PRIMARY (taker execution, real funding, full costs) — THE DECIDING CELL")
    print("-" * 78)
    b_tr = score(dc, sig_base, fc, 0, i_tr, "taker")
    b_va = score(dc, sig_base, fc, i_tr, i_va, "taker")
    v_tr = score(dc, sig_veto, fc, 0, i_tr, "taker")
    v_va = score(dc, sig_veto, fc, i_tr, i_va, "taker")
    tbl = pd.DataFrame([row("baseline: no veto", b_tr, b_va),
                        row("STORM-VETO p90", v_tr, v_va)])
    print(tbl.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # ---------------- chance control: is the veto better than random? ----
    print("\n" + "-" * 78)
    print(f"CHANCE CONTROL — drop the same number of trades AT RANDOM, "
          f"{N_DRAWS} draws")
    print("-" * 78)
    rng = np.random.default_rng(SEED)
    idx_all = np.flatnonzero(entry_c.to_numpy())
    idx_keep = np.flatnonzero(vetoed_c.to_numpy())
    n_keep = len(idx_keep)
    ctrl_tr, ctrl_va = [], []
    for _ in range(N_DRAWS):
        pick = rng.choice(idx_all, size=n_keep, replace=False)
        e = pd.Series(False, index=dc.index)
        e.iloc[pick] = True
        s = machine(dc, e, no_exit, +1, MAX_HOLD)
        ctrl_tr.append(score(dc, s, fc, 0, i_tr, "taker").expectancy)
        ctrl_va.append(score(dc, s, fc, i_tr, i_va, "taker").expectancy)
    ctrl_tr = np.array(ctrl_tr)
    ctrl_va = np.array(ctrl_va)
    p_tr = float((ctrl_tr < v_tr.expectancy).mean() * 100)
    p_va = float((ctrl_va < v_va.expectancy).mean() * 100)
    print(f"  random-drop TRAIN expectancy: mean ${ctrl_tr.mean():+,.2f}  "
          f"p10 ${np.percentile(ctrl_tr, 10):+,.2f}  "
          f"p90 ${np.percentile(ctrl_tr, 90):+,.2f}")
    print(f"  -> the storm-veto's train ${v_tr.expectancy:+,.2f} sits at the "
          f"{p_tr:.1f}th percentile of chance")
    print(f"  random-drop VAL   expectancy: mean ${ctrl_va.mean():+,.2f}  "
          f"p10 ${np.percentile(ctrl_va, 10):+,.2f}  "
          f"p90 ${np.percentile(ctrl_va, 90):+,.2f}")
    print(f"  -> the storm-veto's val   ${v_va.expectancy:+,.2f} sits at the "
          f"{p_va:.1f}th percentile of chance")

    # ---------------- robustness ONLY (cannot qualify anything) ----------
    print("\n" + "-" * 78)
    print("ROBUSTNESS REPORTING ONLY — barred from qualifying anything")
    print("-" * 78)
    print("\n[a] neighbourhood: is p90 a plateau or a lone spike?")
    nb = []
    for q in (0.80, 0.90, 0.95):
        st, _ = garch_gate_on_1h(d1, q)
        st_c = st.iloc[first:].reset_index(drop=True)
        s = machine(dc, entry_c & ~st_c, no_exit, +1, MAX_HOLD)
        nb.append(row(f"storm-veto p{int(q*100)}",
                      score(dc, s, fc, 0, i_tr, "taker"),
                      score(dc, s, fc, i_tr, i_va, "taker")))
    print(pd.DataFrame(nb).to_string(index=False,
                                     float_format=lambda x: f"{x:,.2f}"))

    print("\n[b] the ORIGINAL round-15 frame (maker) — reference only, the "
          "live book does not trade this way:")
    mk = [row("baseline: no veto (maker)",
              score(dc, sig_base, fc, 0, i_tr, "maker"),
              score(dc, sig_base, fc, i_tr, i_va, "maker")),
          row("STORM-VETO p90 (maker)",
              score(dc, sig_veto, fc, 0, i_tr, "maker"),
              score(dc, sig_veto, fc, i_tr, i_va, "maker"))]
    print(pd.DataFrame(mk).to_string(index=False,
                                     float_format=lambda x: f"{x:,.2f}"))

    # ---------------- verdict --------------------------------------------
    print("\n" + "=" * 78)
    positive = v_tr.expectancy > 0 and v_va.expectancy > 0
    sample = len(v_tr.trades) >= 30 and len(v_va.trades) >= 8
    beats = (v_tr.expectancy > b_tr.expectancy
             and v_va.expectancy > b_va.expectancy)
    beats_chance = p_tr >= 90.0 and p_va >= 90.0
    print(f"QUALIFICATION (all four required, primary taker cell only):")
    print(f"  positive train AND val ............ {'PASS' if positive else 'FAIL'}"
          f"  (${v_tr.expectancy:+,.2f} / ${v_va.expectancy:+,.2f})")
    print(f"  sample >=30 train / >=8 val ....... {'PASS' if sample else 'FAIL'}"
          f"  ({len(v_tr.trades)} / {len(v_va.trades)})")
    print(f"  beats the un-vetoed baseline ...... {'PASS' if beats else 'FAIL'}"
          f"  (baseline ${b_tr.expectancy:+,.2f} / ${b_va.expectancy:+,.2f})")
    print(f"  beats chance (>=90th both windows)  {'PASS' if beats_chance else 'FAIL'}"
          f"  ({p_tr:.1f}th / {p_va:.1f}th)")

    if positive and sample and beats and beats_chance:
        print("\nQUALIFIED -> spending ONE sealed-test look.")
        v_te = score(dc, sig_veto, fc, i_va, n, "taker")
        b_te = score(dc, sig_base, fc, i_va, n, "taker")
        print(f"  STORM-VETO p90 TEST: exp ${v_te.expectancy:+,.2f}/t over "
              f"{len(v_te.trades)} trades, {v_te.total_return_pct:+.1f}%, "
              f"win {v_te.win_rate*100:.0f}%, DD {v_te.max_drawdown_pct:.1f}%, "
              f"thickness {v_te.expectancy / ROUND_TRIP_USD:.2f}x")
        print(f"  baseline  TEST: exp ${b_te.expectancy:+,.2f}/t over "
              f"{len(b_te.trades)} trades")
        print("\n  LOOKS CONSUMED THIS ROUND: 1 (sealed test, storm-veto family)")
    else:
        print("\nNOT QUALIFIED — the sealed test window is NOT opened.")
        print("LOOKS CONSUMED THIS ROUND: 0 sealed-test looks.")
    print("=" * 78)


if __name__ == "__main__":
    main()
