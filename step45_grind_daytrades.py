"""
step45_grind_daytrades.py: round 45A, hunting DAY-TRADE strategies for BTC
built for the CURRENT LOW-VOL GRIND, not against it.

Run:  python3 step45_grind_daytrades.py

CONTEXT (see RESEARCH_LOG.md rounds 41 + 43, the graveyard)
Round 41 (shorts) and round 43 (day-trades) both confirmed the 2025-26 grind
kills momentum/breakout/short families built for a livelier market. The ONE
gate that ever improved anything in round 41 was the QUIET gate (current
ATR% BELOW its own trailing-365d median, `adaptive_vol_gate(..., direction=
"below")`), round 41's "3-breakdown N20 gate-below-median 1h" was one of
only two short survivors. This round's whole thesis: "grind" means RANGES:
price oscillates, extremes revert, funding settles rhythmically. So hunt
families that are STRUCTURED to profit from quiet, calm-range conditions
instead of fighting them.

FOUR NATIVE FAMILIES
  1. CALM-GATED RANGE FADE : fade z-score extremes off a rolling mean, but
                                ONLY when the market reads quiet. Distinct
                                from round 43's VWAP fade, which was
                                CHAMP-gated (4h trend regime), not
                                vol-gated: this is the untested variant.
  2. FUNDING-SETTLEMENT SCALP: trade the 8h funding cycle itself: fade the
                                crowded side ahead of settlement (hyp. A) or
                                snap opposite the pre-settlement drift right
                                at settlement (hyp. B).
  3. OI-SHOCK FADE/FOLLOW   : fade or follow price moves accompanied by an
                                extreme change in open interest.
  4. QUIET-RANGE BREAKOUT-FAILURE: the grind's signature move: a breakout
                                that immediately fails and snaps back
                                inside the prior range.

Every family (1/3/4) is tested BOTH calm-gated and ungated on the exact same
entry/exit geometry, so the results table itself answers "does the calm
gate genuinely condition profitability" per family, not just by assertion.

ENGINE NOTES: reused wholesale from step43_daytrade.py / step41_shorts.py,
not reimplemented (see those files' headers for the ground truth this round
inherits unchanged):
- run_backtest takes ONE fixed stop_pct/target_pct for the whole run. Where
  a family calls for a per-trade dynamic distance (distance-to-mean,
  distance-to-wick, distance-to-midpoint), we follow the established
  approximation: TRAIN-only median distance at qualifying entries, held
  fixed across train/val, stated per family below. Every stop is
  hard-capped at 1.7% (HARD_STOP_CAP, imported from step43_daytrade).
- max_hold is enforced by a signal-side state machine, not an engine
  parameter; `day_trade_signal` (family 2/3/4, imported unchanged from
  step43_daytrade) or `range_fade_signal` (family 1, new here: same idea
  plus an explicit "z crosses back through 0" exit, since the range-fade
  spec calls for a mean-touch exit that a plain time-stop can't express).
- No lookahead: rolling extremes/means/stds are used exactly as elsewhere
  in this repo (the engine's own bar-close-N -> fill-at-open-N+1 mechanic
  is what enforces it), PLUS the family-1 z-score gets an explicit extra
  shift(1) per this round's brief ("z ... shift(1)'d"), one bar more
  conservative than strictly required, done because the brief asked for it
  literally. Family 4's rolling high/low channel is shift(1)'d exactly like
  strategy.donchian_breakout. Family 2's funding-based entries use only the
  MOST RECENTLY SETTLED funding rate (`align_funding`'s backward asof, which
  is already-known info as of the entry bar's close), never a future
  settlement's realized rate, which would be lookahead.
- GAUNTLET: chronological 60/20/20 per timeframe (`split_points`, imported).
  This script NEVER slices into the final 20% (test).
- Cost discipline: CostModel defaults, execution="maker", real funding via
  align_funding, identical to step41/step43.

DISCIPLINE: selection is by TRAIN expectancy only; val is checked once and
never tuned against. No 15m configs here: 15m is 4x-confirmed dead
(rounds 4-8 lineage + round 43's cost-floor analysis: ~9.2bps realized cost
vs ~3bps gross edge at that resolution). Research only, no live orders, no
file touched outside step45_grind_daytrades.py / step45_results.md.
"""

import numpy as np
import pandas as pd

from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import adaptive_vol_gate
from step43_daytrade import (
    HARD_STOP_CAP,
    MIN_TRAIN_TRADES,
    MIN_VAL_TRADES,
    bar_hours,
    day_trade_signal,
    hold_stats,
    hours_to_bars,
    mk_row,
    score,
    split_points,
    verdict_for,
)
from strategy import atr

RANGE_TARGET_CAP = 2.5   # family 1's own target cap (mean-touch distance)
BREAKOUT_TARGET_CAP = 3.0   # family 4's own target cap (midpoint distance)
BREAKOUT_STOP_CAP = 1.5     # family 4's own stop cap (above the wick)


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def no_gate(d):
    return pd.Series(True, index=d.index)


def load_oi_history(symbol="BTCUSDT"):
    """Bybit hourly open-interest, cached by collector.py. Not fetched here
    (research only, no network calls); if the cache is missing this raises,
    which is the correct behavior (fail loud, don't silently skip)."""
    path = f"data_bybit_{symbol}_oi_1h.parquet"
    df = pd.read_parquet(path)
    return df.sort_values("timestamp").reset_index(drop=True)


def align_oi(candles, oi_df):
    """Most recent OI reading as of each bar's close (merge_asof, same
    pattern as align_funding). A 2h tolerance handles the rare gap without
    silently carrying a stale reading forward indefinitely."""
    bars = candles[["timestamp"]].copy()
    merged = pd.merge_asof(bars, oi_df, on="timestamp", direction="backward",
                            tolerance=pd.Timedelta(hours=2))
    return merged["oi"]


def range_fade_signal(d, enter_long, enter_short, z, max_hold_bars):
    """Bidirectional range-fade state machine: opens on enter_long/
    enter_short, forces flat the moment the (already-lagged) z-score
    crosses back through 0 (the "mean touch" exit the spec calls for),
    or after max_hold_bars, whichever comes first. Engine-managed
    stop_pct/target_pct may still exit a trade before either of those
    fires; this machine only owns the "force flat" side, exactly like
    day_trade_signal, with one extra exit condition."""
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    zz = z.fillna(0.0).to_numpy(dtype=float)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if el[i]:
                pos, held = 1.0, 0
            elif es[i]:
                pos, held = -1.0, 0
        else:
            held += 1
            crossed = (pos > 0 and zz[i] >= 0) or (pos < 0 and zz[i] <= 0)
            if crossed or (max_hold_bars and held >= max_hold_bars):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def tag_gate(row, gate_tag):
    row["gate"] = gate_tag
    return row


# ---------------------------------------------------------------------------
# FAMILY 1: calm-gated range fade (1h, 2h)
# ---------------------------------------------------------------------------
# z = (close - rolling_mean(N)) / rolling_std(N), N in {24, 48}, the whole
# z series shift(1)'d per the brief. calm-gate = adaptive_vol_gate(...,
# direction="below"), quiet regime only. long when z < -{1.5,2.0} & calm;
# short mirror. Exit at mean-touch (train-only median distance-to-mean at
# qualifying entries, capped 2.5%) OR z crossing 0, whichever first; stop
# {1.0, 1.5}% (capped at HARD_STOP_CAP); max hold 24h.
#
# Tested BOTH calm-gated and ungated on identical geometry so the results
# table itself carries the "does the gate matter" comparison this family
# is explicitly about. UNLIKE round 43's VWAP fade (champ-gated on the 4h
# trend regime), this gate is purely volatility-based.

def family1_calm_range_fade(frames, funding, meta):
    rows = []
    for tf in ("1h", "2h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        calm = meta[tf]["calm"]
        mh_bars = hours_to_bars(d, 24)
        for N in (24, 48):
            m = d["close"].rolling(N).mean()
            s = d["close"].rolling(N).std()
            z = ((d["close"] - m) / s).shift(1)
            dist_to_mean_pct = ((m.shift(1) - d["close"]).abs() / d["close"] * 100)
            for z_thresh in (1.5, 2.0):
                long_cond = z < -z_thresh
                short_cond = z > z_thresh
                for gated in (True, False):
                    gate = calm if gated else no_gate(d)
                    enter_long = (long_cond & gate).fillna(False)
                    enter_short = (short_cond & gate).fillna(False)

                    train_dists = pd.concat([
                        dist_to_mean_pct.iloc[:i_tr][enter_long.iloc[:i_tr]],
                        dist_to_mean_pct.iloc[:i_tr][enter_short.iloc[:i_tr]],
                    ])
                    target_pct = (min(float(train_dists.median()), RANGE_TARGET_CAP)
                                  if len(train_dists) else RANGE_TARGET_CAP)

                    for stop_pct in (1.0, 1.5):
                        stop_capped = min(stop_pct, HARD_STOP_CAP)
                        sig = range_fade_signal(d, enter_long, enter_short, z, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=stop_capped, target_pct=target_pct)
                        gate_tag = "calm-gated" if gated else "ungated"
                        cfg = f"N{N} z{z_thresh:.1f} {gate_tag} stop{stop_pct:.1f}%"
                        rows.append(tag_gate(
                            mk_row("1-calm-range-fade", cfg, tf, tr, va,
                                   stop_capped, target_pct, 24), gate_tag))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2: funding-settlement scalp (1h)
# ---------------------------------------------------------------------------
# Settlements at 00/08/16 UTC. Hypothesis A (pre-settlement drift): funding
# extreme -> enter AGAINST the crowded side {2,4} bars before settlement,
# exit 1-2 bars after (max hold capped at bars_before+exit_after <= 6h),
# stop 1.0%. Hypothesis B (post-settlement snap): enter AT the settlement
# bar, opposite the prior 8h drift, when funding extreme, same 6h cap.
# Both use the REAL, already-settled funding series (align_funding), never
# an unknowable future settlement's rate. Tested calm-gated + ungated.

def family2_funding_scalp(frames, funding, meta):
    rows = []
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    calm = meta[tf]["calm"]
    is_settle = d["timestamp"].dt.hour.isin([0, 8, 16])

    # Hypothesis A: pre-settlement drift
    for fund_thresh in (1.5, 2.5):
        for bars_before in (2, 4):
            pre_signal = is_settle.shift(-bars_before).fillna(False).astype(bool)
            for exit_after in (1, 2):
                mh_bars = bars_before + exit_after
                enter_long_raw = (pre_signal & (f < -fund_thresh)).fillna(False)
                enter_short_raw = (pre_signal & (f > fund_thresh)).fillna(False)
                for gated in (True, False):
                    gate = calm if gated else no_gate(d)
                    enter_long = (enter_long_raw & gate).fillna(False)
                    enter_short = (enter_short_raw & gate).fillna(False)
                    for target_pct in (None, 1.0, 2.0):
                        sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=1.0, target_pct=target_pct)
                        gate_tag = "calm-gated" if gated else "ungated"
                        tgt_tag = f"{target_pct:.1f}%" if target_pct is not None else "none"
                        cfg = (f"A f>{fund_thresh:.1f}bp before{bars_before} "
                               f"exit+{exit_after} {gate_tag} tgt{tgt_tag}")
                        rows.append(tag_gate(
                            mk_row("2-funding-pre", cfg, tf, tr, va,
                                   1.0, target_pct, mh_bars), gate_tag))

    # Hypothesis B: post-settlement snap
    drift_bars = hours_to_bars(d, 8)
    prior_drift = (d["close"] / d["close"].shift(drift_bars) - 1) * 100
    mh_bars_b = hours_to_bars(d, 6)
    for fund_thresh in (1.5, 2.5):
        enter_long_raw = (is_settle & (f.abs() >= fund_thresh) & (prior_drift < 0)).fillna(False)
        enter_short_raw = (is_settle & (f.abs() >= fund_thresh) & (prior_drift > 0)).fillna(False)
        for gated in (True, False):
            gate = calm if gated else no_gate(d)
            enter_long = (enter_long_raw & gate).fillna(False)
            enter_short = (enter_short_raw & gate).fillna(False)
            for target_pct in (None, 1.0, 2.0):
                sig = day_trade_signal(d, enter_long, enter_short, mh_bars_b)
                tr, va = score(d, sig, f, i_tr, i_va,
                               stop_pct=1.0, target_pct=target_pct)
                gate_tag = "calm-gated" if gated else "ungated"
                tgt_tag = f"{target_pct:.1f}%" if target_pct is not None else "none"
                cfg = f"B f>{fund_thresh:.1f}bp {gate_tag} tgt{tgt_tag}"
                rows.append(tag_gate(
                    mk_row("2-funding-post", cfg, tf, tr, va,
                           1.0, target_pct, mh_bars_b), gate_tag))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3: OI-shock fade/follow (1h)
# ---------------------------------------------------------------------------
# dOI over {1h, 4h} windows (matched to a same-length price return window).
# "Extreme" = |dOI%| >= its TRAIN-only quantile ({90th, 95th}), a fixed
# threshold held constant across train/val (same convention as every other
# train-derived threshold in this repo). fade = counter to the price move
# that accompanied the OI shock; follow = with it. Day-trade geometry:
# stop {1.0,1.5}%, target {2.0,3.0}%, max hold 24h. Tested calm-gated +
# ungated.

def family3_oi_shock(frames, funding, meta, oi_1h):
    rows = []
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    calm = meta[tf]["calm"]
    mh_bars = hours_to_bars(d, 24)

    for w_h, w_label in ((1, "1h"), (4, "4h")):
        w_bars = hours_to_bars(d, w_h)
        ret_w = (d["close"] / d["close"].shift(w_bars) - 1) * 100
        doi_w = (oi_1h / oi_1h.shift(w_bars) - 1) * 100
        for q in (90, 95):
            train_abs = doi_w.iloc[:i_tr].abs().dropna()
            if len(train_abs) < 30:
                continue
            thresh = float(train_abs.quantile(q / 100))
            extreme = (doi_w.abs() >= thresh).fillna(False)
            up_move = ret_w > 0
            down_move = ret_w < 0
            for mode in ("fade", "follow"):
                if mode == "fade":
                    enter_short_raw = (extreme & up_move).fillna(False)
                    enter_long_raw = (extreme & down_move).fillna(False)
                else:
                    enter_long_raw = (extreme & up_move).fillna(False)
                    enter_short_raw = (extreme & down_move).fillna(False)
                for gated in (True, False):
                    gate = calm if gated else no_gate(d)
                    enter_long = (enter_long_raw & gate).fillna(False)
                    enter_short = (enter_short_raw & gate).fillna(False)
                    for stop_pct in (1.0, 1.5):
                        for target_pct in (2.0, 3.0):
                            sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                            tr, va = score(d, sig, f, i_tr, i_va,
                                           stop_pct=min(stop_pct, HARD_STOP_CAP),
                                           target_pct=target_pct)
                            gate_tag = "calm-gated" if gated else "ungated"
                            cfg = (f"dOI{w_label} q{q} {mode} {gate_tag} "
                                   f"stop{stop_pct:.1f}% tgt{target_pct:.1f}%")
                            rows.append(tag_gate(
                                mk_row("3-oi-shock", cfg, tf, tr, va,
                                       min(stop_pct, HARD_STOP_CAP), target_pct, 24),
                                gate_tag))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4: quiet-range breakout-failure (1h)
# ---------------------------------------------------------------------------
# Prior N-bar high/low channel (shift(1)'d, exactly like donchian_breakout).
# A bar closes beyond the channel by >X% (the "breakout"); if the VERY NEXT
# bar closes back inside the channel, that's the failure -> trade the
# reversion. Short on a failed up-break, long on a failed down-break.
# Stop = train-only median distance from entry to the breakout bar's wick,
# capped 1.5%. Target = train-only median distance to the range midpoint,
# capped 3%. Max hold 24h. Calm-gated per the spec; ungated run alongside
# for the required comparison.

def family4_breakout_failure(frames, funding, meta):
    rows = []
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    calm = meta[tf]["calm"]
    mh_bars = hours_to_bars(d, 24)

    for N in (24, 48):
        roll_high = d["high"].rolling(N).max().shift(1)
        roll_low = d["low"].rolling(N).min().shift(1)
        range_mid = (roll_high + roll_low) / 2
        wick_hi_at_entry = d["high"].shift(1)   # the breakout bar's own high
        wick_lo_at_entry = d["low"].shift(1)
        for X in (0.10, 0.15, 0.20):
            break_up_bar = d["close"] > roll_high * (1 + X / 100)
            break_down_bar = d["close"] < roll_low * (1 - X / 100)
            fail_up = (break_up_bar.shift(1).fillna(False).astype(bool) & (d["close"] < roll_high))
            fail_down = (break_down_bar.shift(1).fillna(False).astype(bool) & (d["close"] > roll_low))

            dist_stop_short = ((wick_hi_at_entry - d["close"]) / d["close"] * 100)
            dist_stop_long = ((d["close"] - wick_lo_at_entry) / d["close"] * 100)
            dist_tgt = ((range_mid - d["close"]).abs() / d["close"] * 100)

            for gated in (True, False):
                gate = calm if gated else no_gate(d)
                enter_short = (fail_up & gate).fillna(False)
                enter_long = (fail_down & gate).fillna(False)

                train_stop = pd.concat([
                    dist_stop_short.iloc[:i_tr][enter_short.iloc[:i_tr]],
                    dist_stop_long.iloc[:i_tr][enter_long.iloc[:i_tr]],
                ])
                train_tgt = pd.concat([
                    dist_tgt.iloc[:i_tr][enter_short.iloc[:i_tr]],
                    dist_tgt.iloc[:i_tr][enter_long.iloc[:i_tr]],
                ])
                stop_pct = (min(float(train_stop.median()), BREAKOUT_STOP_CAP)
                            if len(train_stop) else BREAKOUT_STOP_CAP)
                stop_pct = min(stop_pct, HARD_STOP_CAP)
                target_pct = (min(float(train_tgt.median()), BREAKOUT_TARGET_CAP)
                              if len(train_tgt) else BREAKOUT_TARGET_CAP)

                sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                tr, va = score(d, sig, f, i_tr, i_va,
                               stop_pct=stop_pct, target_pct=target_pct)
                gate_tag = "calm-gated" if gated else "ungated"
                cfg = f"N{N} X{X:.2f}% {gate_tag}"
                rows.append(tag_gate(
                    mk_row("4-breakout-failure", cfg, tf, tr, va,
                           stop_pct, target_pct, 24), gate_tag))
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("1h", "2h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("1h", "2h")}

    oi_hist = load_oi_history("BTCUSDT")
    print(f"  OI history: {len(oi_hist)} bars, "
          f"{oi_hist['timestamp'].iloc[0]:%Y-%m-%d} -> {oi_hist['timestamp'].iloc[-1]:%Y-%m-%d}")

    meta = {}
    for tf in ("1h", "2h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        calm_gate, _ = adaptive_vol_gate(d, direction="below")
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va,
                    "med_atr": med_atr_train, "calm": calm_gate}
        calm_share = float(calm_gate.iloc[:i_va].mean() * 100)
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.3f}% | calm-gate active "
              f"{calm_share:.1f}% of train+val bars")

    oi_1h = align_oi(frames["1h"], oi_hist)
    print(f"  OI aligned onto 1h frame: {int(oi_1h.notna().sum())}/{len(oi_1h)} bars have OI "
          f"({int(oi_1h.isna().sum())} NaN, mostly pre-2020-07-20 warmup)")

    print("\nRunning FAMILY 1 (calm-gated range fade, 1h+2h)...")
    rows = family1_calm_range_fade(frames, funding, meta)
    print(f"  {len(rows)} configs done")
    print("Running FAMILY 2 (funding-settlement scalp, 1h)...")
    rows += family2_funding_scalp(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 3 (OI-shock fade/follow, 1h)...")
    rows += family3_oi_shock(frames, funding, meta, oi_1h)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 4 (quiet-range breakout-failure, 1h)...")
    rows += family4_breakout_failure(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >=30 train / >=8 val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "med_hold_h", "mean_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                     "med_hold_h", "mean_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # NOTE: per this round's mandate ("touch NOTHING else"), no CSV or other
    # file is written here; step45_results.md is authored separately from
    # this function's returned DataFrame.
    return df


if __name__ == "__main__":
    main()
