"""
step92_fade_breakdown.py — round 92: fade the aged breakdown? And the drift
trap that decides it.

Round 90 found that shorting the break of an aged, well-tested support
level gets monotonically WORSE the older/more-tested the level is (BTC 1h
shorts: age>=20 -$9.23/t -> age>=500 -$89.12/t, monotonic; BTC 4h same
shape). The obvious next hypothesis: an aged, repeatedly-defended level
that finally gives way is capitulation, not confirmation, so the FADE
(buying the breakdown) is the trade. This round tests that.

THE TRAP THIS ROUND EXISTS TO CATCH: BTC rose over most of this sample. In
an uptrend every short loses and every long wins, and aged setups may
simply carry longer exposure to that drift. A raw "buying the breakdown
makes money" result is worthless on its own. Three controls are run and
the verdict is REAL only if all three, plus the ETH transfer, survive:

  Control 1 — random-entry drift baseline. For every structural fade cell,
    draw >=200 random entries at other timestamps with the SAME slice, the
    SAME holding period (max_hold_bars), and the SAME exit geometry (pure
    time exit, stop_pct=target_pct=None — this round's one fixed rule,
    identical to round 90's). Report the fade's expectancy as a percentile
    against that random distribution.
  Control 2 — the mirror. If aged levels genuinely mean-revert, fading an
    aged RESISTANCE break to the upside (short) must show the same shape
    as fading an aged SUPPORT break to the downside (long). Both are run
    from the exact same break-event machinery, direction flipped. A
    one-sided result (only the breakdown-fade works) is drift wearing a
    costume, not structure.
  Control 3 — bull/bear sub-periods. Regime = close vs a 50-CALENDAR-DAY
    SMA on that timeframe's own bars (via step43_daytrade.hours_to_bars,
    so "50 days" means the same wall-clock window on 1h and 4h). Trades
    tagged by the regime active at their entry bar; expectancy reported
    separately per regime, no re-selection.

REUSED FROM ROUND 90, NOT RETYPED (imported directly from
step90_level_significance.py): load_frames, build_meta, scan_structure
(swing/level/break-event/touch tracking), build_level_masks (STRUCTURAL vs
LOCAL classification), signal_from_mask, run_train, trades_per_year,
AGE_CUTOFFS, TOUCH_CUTOFFS, MAX_HOLD_BARS, TFS, ASSET_LABEL. Reused from
step43_daytrade: score, split_points, day_trade_signal, hours_to_bars,
MIN_TRAIN_TRADES, MIN_VAL_TRADES. Reused from backtest: run_backtest
directly (for the random-baseline draws, which need a plain call rather
than step90's train-only wrapper).

FADE CONSTRUCTION: a "fade" trades the OPPOSITE direction of the original
break-event direction, using the identical break-event machinery.
  fade_breakdown       : break_direction="short" (support broken down),
                          trade_direction="long"  (buy the breakdown)
  fade_breakout_mirror : break_direction="long"  (resistance broken up),
                          trade_direction="short" (sell the breakout)
Both use the SAME STRUCTURAL/LOCAL classification (age_bars>=age_cutoff
AND touches>=touch_cutoff) and the same age/touch sweep grid as round 90,
for direct comparability to round 90's own (losing) short-the-breakdown /
long-the-breakout numbers.

DISCIPLINE: chronological 60/20/20 (split_points), age/touch cutoff
selection on BTC TRAIN ONLY (maximize STRUCTURAL-minus-LOCAL train
expectancy, both buckets clearing MIN_TRAIN_TRADES), val read exactly once
via score(), test ([i_va:n]) never sliced/scored/referenced anywhere in
this file (grep-verified: the only i_va occurrences are the split-point
unpack). MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8. Any BTC survivor is
mandatorily replayed UNCHANGED (no re-tuning) on ETH.

Writes ONLY: step92_fade_breakdown.py (this file), step92_results.md,
step92_table.csv. No other file read for writing, none modified. No
commits, no live orders, no network calls (cached parquet only, same as
round 90).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import run_backtest
from step43_daytrade import (
    MIN_TRAIN_TRADES,
    MIN_VAL_TRADES,
    day_trade_signal,
    hours_to_bars,
    score,
    split_points,
)
from step90_level_significance import (
    AGE_CUTOFFS,
    ASSET_LABEL,
    MAX_HOLD_BARS,
    TFS,
    TOUCH_CUTOFFS,
    build_level_masks,
    build_meta,
    load_frames,
    run_train,
    scan_structure,
    signal_from_mask,
    trades_per_year,
)

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

# (fade_name, break_direction, trade_direction) — see module docstring.
FADE_TYPES = [
    ("fade_breakdown", "short", "long"),          # the round's headline hypothesis
    ("fade_breakout_mirror", "long", "short"),    # Control 2, the strongest test
]

RANDOM_DRAWS = 200          # brief's floor, exactly met (not padded to look extra rigorous)
RANDOM_SEED = 92
RANDOM_PCTL_THRESHOLD = 95.0   # "beats random" bar used for the by-chance accounting

SMA_DAYS = 50                # Control 3 regime definition: close vs 50-calendar-day SMA
MIN_REGIME_TRADES = 15       # floor for a regime sub-bucket to be trusted (looser than
                              # MIN_VAL_TRADES=8 x ~2, since this splits an already-selected n)


def cell_row(**kw):
    return kw


# ---------------------------------------------------------------------------
# fade signal construction (reuses round 90's break-event masks, direction flipped)
# ---------------------------------------------------------------------------

def fade_masks(events_df: pd.DataFrame, break_direction: str, age_cut: int, touch_cut: int, n: int):
    """STRUCTURAL/LOCAL masks over the ORIGINAL break event (support-down or
    resistance-up), unchanged from round 90's build_level_masks. The trade
    direction is applied separately in fade_signal()."""
    return build_level_masks(events_df, break_direction, age_cut, touch_cut, n)


def fade_signal(d: pd.DataFrame, mask: np.ndarray, trade_direction: str, max_hold_bars: int) -> pd.Series:
    return signal_from_mask(d, mask, trade_direction, max_hold_bars)


# ---------------------------------------------------------------------------
# Control 1: random-entry drift baseline
# ---------------------------------------------------------------------------

def random_baseline(d: pd.DataFrame, f: pd.Series, lo: int, hi: int, n_trades: int,
                     trade_direction: str, max_hold_bars: int,
                     n_draws: int = RANDOM_DRAWS, seed: int = RANDOM_SEED) -> np.ndarray:
    """Draw n_draws random entry sets of size n_trades within [lo:hi), each
    run through the IDENTICAL engine (day_trade_signal state machine ->
    run_backtest, maker execution, real funding, stop_pct=target_pct=None,
    same max_hold_bars) as the actual fade. Returns the array of resulting
    per-trade expectancies (one per draw; draws producing zero realized
    trades, essentially never at these bar counts, are skipped)."""
    span = hi - lo
    if n_trades <= 0 or span <= max_hold_bars + 5:
        return np.array([])
    rng = np.random.default_rng(seed)
    d_slice = d.iloc[lo:hi].reset_index(drop=True)
    f_slice = f.iloc[lo:hi].reset_index(drop=True)
    candidates = np.arange(0, span - max_hold_bars)
    k = min(n_trades, len(candidates))
    draws = []
    for _ in range(n_draws):
        idxs = rng.choice(candidates, size=k, replace=False)
        mask = np.zeros(span, dtype=bool)
        mask[idxs] = True
        sig = fade_signal(d_slice, mask, trade_direction, max_hold_bars)
        res = run_backtest(d_slice, sig, execution="maker", funding_series=f_slice,
                            stop_pct=None, target_pct=None)
        if res.trades:
            draws.append(res.expectancy)
    return np.array(draws)


def percentile_of(actual: float, draws: np.ndarray) -> float:
    """% of the random distribution the actual expectancy BEATS. NaN if no
    draws produced trades."""
    if draws.size == 0:
        return float("nan")
    return float((draws < actual).mean() * 100)


# ---------------------------------------------------------------------------
# Control 3: bull/bear regime split (close vs 50-calendar-day SMA, no re-selection)
# ---------------------------------------------------------------------------

def split_trades_by_regime(d: pd.DataFrame, trades, bull_by_ts: dict):
    """Tag each Trade by the regime active at its entry_time; returns
    (bull_pnls, bear_pnls, unknown_count)."""
    bull_pnls, bear_pnls, unknown = [], [], 0
    for t in trades:
        label = bull_by_ts.get(t.entry_time)
        if label is None:
            unknown += 1
        elif label:
            bull_pnls.append(t.pnl)
        else:
            bear_pnls.append(t.pnl)
    return bull_pnls, bear_pnls, unknown


# ---------------------------------------------------------------------------
# main sweep: BTC train, select, confirm on val, ETH transfer, controls
# ---------------------------------------------------------------------------

def sweep_btc_train(d, f, i_tr, events_df, break_direction, trade_direction, mh, table_rows,
                     fade_name, tf):
    n = len(d)
    best = None  # (gap, age_cut, touch_cut, tr_s, tr_l)
    for age_cut in AGE_CUTOFFS:
        for touch_cut in TOUCH_CUTOFFS:
            structural, local = fade_masks(events_df, break_direction, age_cut, touch_cut, n)
            sig_s = fade_signal(d, structural, trade_direction, mh)
            sig_l = fade_signal(d, local, trade_direction, mh)
            tr_s = run_train(d, f, i_tr, sig_s)
            tr_l = run_train(d, f, i_tr, sig_l)
            table_rows.append(cell_row(
                section="fade_sweep", asset="BTC", tf=tf, fade_type=fade_name,
                break_direction=break_direction, trade_direction=trade_direction,
                age_cutoff=age_cut, touch_cutoff=touch_cut, bucket="STRUCTURAL", split="train",
                n_trades=len(tr_s.trades), expectancy=tr_s.expectancy,
                trades_per_year=trades_per_year(len(tr_s.trades), d, 0, i_tr),
                win_rate_pct=tr_s.win_rate * 100,
                random_pctl=np.nan,
            ))
            table_rows.append(cell_row(
                section="fade_sweep", asset="BTC", tf=tf, fade_type=fade_name,
                break_direction=break_direction, trade_direction=trade_direction,
                age_cutoff=age_cut, touch_cutoff=touch_cut, bucket="LOCAL", split="train",
                n_trades=len(tr_l.trades), expectancy=tr_l.expectancy,
                trades_per_year=trades_per_year(len(tr_l.trades), d, 0, i_tr),
                win_rate_pct=tr_l.win_rate * 100,
                random_pctl=np.nan,
            ))
            if len(tr_s.trades) >= MIN_TRAIN_TRADES and len(tr_l.trades) >= MIN_TRAIN_TRADES:
                gap = tr_s.expectancy - tr_l.expectancy
                if best is None or gap > best[0]:
                    best = (gap, age_cut, touch_cut, tr_s, tr_l)
    return best


def control1_full_grid(btc_frames, btc_funding, btc_meta, btc_events, table_rows):
    """Control 1 applied to EVERY STRUCTURAL cell of the full sweep grid
    (60 cells: 2 tf x 2 fade_types x 5 age x 3 touch), on BTC train. This is
    the number used for the cells-run-vs-expected-by-chance accounting."""
    rows = []
    for tf in TFS:
        d, f = btc_frames[tf], btc_funding[tf]
        i_tr = btc_meta[tf]["i_tr"]
        events_df = btc_events[tf]
        mh = MAX_HOLD_BARS[tf]
        n = len(d)
        for fade_name, break_dir, trade_dir in FADE_TYPES:
            for age_cut in AGE_CUTOFFS:
                for touch_cut in TOUCH_CUTOFFS:
                    structural, _ = fade_masks(events_df, break_dir, age_cut, touch_cut, n)
                    sig_s = fade_signal(d, structural, trade_dir, mh)
                    tr_s = run_train(d, f, i_tr, sig_s)
                    n_tr = len(tr_s.trades)
                    if n_tr < MIN_TRAIN_TRADES:
                        pctl = float("nan")
                    else:
                        draws = random_baseline(d, f, 0, i_tr, n_tr, trade_dir, mh)
                        pctl = percentile_of(tr_s.expectancy, draws)
                    rows.append(cell_row(
                        section="fade_sweep_random_baseline", asset="BTC", tf=tf, fade_type=fade_name,
                        break_direction=break_dir, trade_direction=trade_dir,
                        age_cutoff=age_cut, touch_cutoff=touch_cut, bucket="STRUCTURAL", split="train",
                        n_trades=n_tr, expectancy=tr_s.expectancy,
                        trades_per_year=trades_per_year(n_tr, d, 0, i_tr),
                        win_rate_pct=tr_s.win_rate * 100,
                        random_pctl=pctl,
                    ))
                    print(f"  [control1 grid] {ASSET_LABEL['BTCUSDT']} {tf} {fade_name} "
                          f"age>={age_cut} touch>={touch_cut}: n={n_tr} exp=${tr_s.expectancy:+.2f} "
                          f"random_pctl={pctl:.1f}" if not np.isnan(pctl) else
                          f"  [control1 grid] {tf} {fade_name} age>={age_cut} touch>={touch_cut}: INSUFFICIENT")
    table_rows.extend(rows)
    return rows


def fade_section(btc_frames, btc_funding, btc_meta, btc_events,
                  eth_frames, eth_funding, eth_meta, eth_events, table_rows):
    selected = {}  # (tf, fade_name) -> dict
    for tf in TFS:
        d, f = btc_frames[tf], btc_funding[tf]
        i_tr, i_va = btc_meta[tf]["i_tr"], btc_meta[tf]["i_va"]
        events_df = btc_events[tf]
        mh = MAX_HOLD_BARS[tf]
        for fade_name, break_dir, trade_dir in FADE_TYPES:
            best = sweep_btc_train(d, f, i_tr, events_df, break_dir, trade_dir, mh, table_rows,
                                    fade_name, tf)
            if best is None:
                selected[(tf, fade_name)] = {"status": "INSUFFICIENT_SAMPLE_TRAIN"}
                continue
            gap, age_cut, touch_cut, _, _ = best
            n = len(d)
            structural, local = fade_masks(events_df, break_dir, age_cut, touch_cut, n)
            sig_s = fade_signal(d, structural, trade_dir, mh)
            sig_l = fade_signal(d, local, trade_dir, mh)
            s_tr, s_va = score(d, sig_s, f, i_tr, i_va, execution="maker")
            l_tr, l_va = score(d, sig_l, f, i_tr, i_va, execution="maker")

            for bucket, tr, va in (("STRUCTURAL", s_tr, s_va), ("LOCAL", l_tr, l_va)):
                for split_name, res, lo, hi in (("train", tr, 0, i_tr), ("val", va, i_tr, i_va)):
                    pctl = float("nan")
                    if bucket == "STRUCTURAL" and len(res.trades) >= (MIN_TRAIN_TRADES if split_name == "train" else MIN_VAL_TRADES):
                        draws = random_baseline(d, f, lo, hi, len(res.trades), trade_dir, mh)
                        pctl = percentile_of(res.expectancy, draws)
                    table_rows.append(cell_row(
                        section="fade_selected", asset="BTC", tf=tf, fade_type=fade_name,
                        break_direction=break_dir, trade_direction=trade_dir,
                        age_cutoff=age_cut, touch_cutoff=touch_cut, bucket=bucket, split=split_name,
                        n_trades=len(res.trades), expectancy=res.expectancy,
                        trades_per_year=trades_per_year(len(res.trades), d, lo, hi),
                        win_rate_pct=res.win_rate * 100,
                        random_pctl=pctl,
                    ))

            survives = (s_tr.expectancy > 0 and s_va.expectancy > 0
                        and len(s_tr.trades) >= MIN_TRAIN_TRADES
                        and len(s_va.trades) >= MIN_VAL_TRADES)

            # Control 3: bull/bear regime split, on train+val POOLED (no
            # re-selection — the age/touch cutoff was already fixed above).
            pooled_sig = fade_signal(d, structural, trade_dir, mh)
            pooled_res = run_backtest(d.iloc[:i_va].reset_index(drop=True),
                                       pooled_sig.iloc[:i_va].reset_index(drop=True),
                                       execution="maker",
                                       funding_series=f.iloc[:i_va].reset_index(drop=True),
                                       stop_pct=None, target_pct=None)
            # NaN-safe boolean regime label per timestamp (close vs 50-calendar-day SMA)
            sma_bars = hours_to_bars(d, SMA_DAYS * 24)
            sma_series = d["close"].rolling(sma_bars).mean()
            regime_valid = sma_series.notna()
            bull_by_ts = {}
            for ts, c, s, valid in zip(d["timestamp"], d["close"], sma_series, regime_valid):
                bull_by_ts[ts] = (c > s) if valid else None
            bull_pnls, bear_pnls, unknown = split_trades_by_regime(d, pooled_res.trades, bull_by_ts)

            def regime_row(label, pnls):
                n_r = len(pnls)
                exp_r = float(np.mean(pnls)) if pnls else float("nan")
                status = "ok" if n_r >= MIN_REGIME_TRADES else "INSUFFICIENT_SAMPLE"
                table_rows.append(cell_row(
                    section="fade_regime_split", asset="BTC", tf=tf, fade_type=fade_name,
                    break_direction=break_dir, trade_direction=trade_dir,
                    age_cutoff=age_cut, touch_cutoff=touch_cut, bucket=f"STRUCTURAL/{label}",
                    split="train+val", n_trades=n_r, expectancy=exp_r,
                    trades_per_year=trades_per_year(n_r, d, 0, i_va) if n_r else float("nan"),
                    win_rate_pct=(float(np.mean([p > 0 for p in pnls]) * 100) if pnls else float("nan")),
                    random_pctl=np.nan,
                ))
                return n_r, exp_r, status

            bull_stats = regime_row("BULL(close>50d-SMA)", bull_pnls)
            bear_stats = regime_row("BEAR(close<=50d-SMA)", bear_pnls)

            selected[(tf, fade_name)] = {
                "status": "SURVIVOR" if survives else "FAIL_OR_INSUFFICIENT",
                "age_cutoff": age_cut, "touch_cutoff": touch_cut,
                "s_tr": s_tr, "s_va": s_va, "l_tr": l_tr, "l_va": l_va,
                "bull_stats": bull_stats, "bear_stats": bear_stats, "regime_unknown": unknown,
                "break_dir": break_dir, "trade_dir": trade_dir,
            }

            if survives:
                ed, ef = eth_frames[tf], eth_funding[tf]
                ei_tr, ei_va = eth_meta[tf]["i_tr"], eth_meta[tf]["i_va"]
                eevents = eth_events[tf]
                en = len(ed)
                e_structural, e_local = fade_masks(eevents, break_dir, age_cut, touch_cut, en)
                e_sig_s = fade_signal(ed, e_structural, trade_dir, mh)
                e_sig_l = fade_signal(ed, e_local, trade_dir, mh)
                es_tr, es_va = score(ed, e_sig_s, ef, ei_tr, ei_va, execution="maker")
                el_tr, el_va = score(ed, e_sig_l, ef, ei_tr, ei_va, execution="maker")
                for bucket, tr, va in (("STRUCTURAL", es_tr, es_va), ("LOCAL", el_tr, el_va)):
                    for split_name, res, lo, hi in (("train", tr, 0, ei_tr), ("val", va, ei_tr, ei_va)):
                        pctl = float("nan")
                        if bucket == "STRUCTURAL" and len(res.trades) >= (MIN_TRAIN_TRADES if split_name == "train" else MIN_VAL_TRADES):
                            draws = random_baseline(ed, ef, lo, hi, len(res.trades), trade_dir, mh)
                            pctl = percentile_of(res.expectancy, draws)
                        table_rows.append(cell_row(
                            section="fade_eth_transfer", asset="ETH", tf=tf, fade_type=fade_name,
                            break_direction=break_dir, trade_direction=trade_dir,
                            age_cutoff=age_cut, touch_cutoff=touch_cut, bucket=bucket, split=split_name,
                            n_trades=len(res.trades), expectancy=res.expectancy,
                            trades_per_year=trades_per_year(len(res.trades), ed, lo, hi),
                            win_rate_pct=res.win_rate * 100,
                            random_pctl=pctl,
                        ))
                eth_survives = (es_tr.expectancy > 0 and es_va.expectancy > 0
                                and len(es_tr.trades) >= MIN_TRAIN_TRADES
                                and len(es_va.trades) >= MIN_VAL_TRADES)
                selected[(tf, fade_name)]["eth_es_tr"] = es_tr
                selected[(tf, fade_name)]["eth_es_va"] = es_va
                selected[(tf, fade_name)]["eth_survives"] = eth_survives

    return selected


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached BTC + ETH data (no network calls expected)...")
    btc_frames, btc_funding = load_frames("BTCUSDT")
    eth_frames, eth_funding = load_frames("ETHUSDT")
    btc_meta = build_meta(btc_frames)
    eth_meta = build_meta(eth_frames)
    for tf in TFS:
        print(f"  BTC {tf}: {btc_meta[tf]['n']} bars, train->{btc_frames[tf]['timestamp'].iloc[btc_meta[tf]['i_tr']]:%Y-%m-%d} "
              f"val->{btc_frames[tf]['timestamp'].iloc[btc_meta[tf]['i_va']]:%Y-%m-%d} (test sealed)")
        print(f"  ETH {tf}: {eth_meta[tf]['n']} bars, train->{eth_frames[tf]['timestamp'].iloc[eth_meta[tf]['i_tr']]:%Y-%m-%d} "
              f"val->{eth_frames[tf]['timestamp'].iloc[eth_meta[tf]['i_va']]:%Y-%m-%d} (test sealed)")

    print("\nScanning swing structure / break events (reused verbatim from step90)...")
    btc_events, eth_events = {}, {}
    for tf in TFS:
        btc_events[tf] = scan_structure(btc_frames[tf])[0]
        eth_events[tf] = scan_structure(eth_frames[tf])[0]
        print(f"  BTC {tf}: {len(btc_events[tf])} break events")
        print(f"  ETH {tf}: {len(eth_events[tf])} break events")

    table_rows: list[dict] = []

    print("\n" + "=" * 78)
    print("FADE SWEEP — BTC train (both fade types incl. mirror), select, confirm val...")
    print("=" * 78)
    selected = fade_section(
        btc_frames, btc_funding, btc_meta, btc_events,
        eth_frames, eth_funding, eth_meta, eth_events,
        table_rows,
    )
    for (tf, fade_name), info in selected.items():
        print(f"\n[BTC {tf} {fade_name}] status={info['status']}")
        if "age_cutoff" in info:
            print(f"  selected: age>={info['age_cutoff']} touches>={info['touch_cutoff']} "
                  f"(break_dir={info['break_dir']} trade_dir={info['trade_dir']})")
            print(f"  STRUCTURAL train n={len(info['s_tr'].trades)} exp=${info['s_tr'].expectancy:+.2f}  "
                  f"val n={len(info['s_va'].trades)} exp=${info['s_va'].expectancy:+.2f}")
            print(f"  LOCAL      train n={len(info['l_tr'].trades)} exp=${info['l_tr'].expectancy:+.2f}  "
                  f"val n={len(info['l_va'].trades)} exp=${info['l_va'].expectancy:+.2f}")
            bn, bexp, bstat = info["bull_stats"]
            rn, rexp, rstat = info["bear_stats"]
            print(f"  regime split (train+val pooled): BULL n={bn} exp=${bexp:+.2f} ({bstat})  "
                  f"BEAR n={rn} exp=${rexp:+.2f} ({rstat})  unknown={info['regime_unknown']}")
            if "eth_survives" in info:
                print(f"  ETH transfer: STRUCTURAL train n={len(info['eth_es_tr'].trades)} "
                      f"exp=${info['eth_es_tr'].expectancy:+.2f}  val n={len(info['eth_es_va'].trades)} "
                      f"exp=${info['eth_es_va'].expectancy:+.2f}  eth_survives={info['eth_survives']}")

    print("\n" + "=" * 78)
    print("CONTROL 1 — random-entry drift baseline over the FULL sweep grid (BTC train)...")
    print("=" * 78)
    control1_full_grid(btc_frames, btc_funding, btc_meta, btc_events, table_rows)

    df = pd.DataFrame(table_rows)
    df.to_csv("step92_table.csv", index=False)
    print(f"\nwrote step92_table.csv: {len(df)} rows")

    # by-chance accounting
    grid = df[df["section"] == "fade_sweep_random_baseline"]
    n_cells = len(grid)
    n_beat = int((grid["random_pctl"] >= RANDOM_PCTL_THRESHOLD).sum())
    expected_by_chance = n_cells * (1 - RANDOM_PCTL_THRESHOLD / 100)
    print(f"\nCells run (structural, full grid): {n_cells}")
    print(f"Cells beating random p95: {n_beat}  (expected by chance at p<0.05: ~{expected_by_chance:.1f})")

    return selected, df


if __name__ == "__main__":
    main()
