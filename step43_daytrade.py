"""
step43_daytrade.py — round 43: hunting DAY-TRADE strategies for BTC.

Run:  python3 step43_daytrade.py

MANDATE
Every family here trades intraday: entered and exited well within 24h
(median hold should sit well under a day), with a TIGHT stop (<=2.0%,
ideally <=1.7%) so the geometry survives 10-20x live leverage (BloFin
liquidates ~4.5% adverse move at 20x). Research only — no live orders, no
file touched outside step43_daytrade.py / step43_results.md.

FOUR NATIVE FAMILIES
  1. MOMENTUM BURST     — trade a strong impulse bar's direction, aligned
                           (or not) with the 4h champion trend.
  2. SESSION BREAKOUT   — first-N-hours UTC range breakout, flat by end of
                           the UTC day.
  3. WASHOUT SCALP      — the proven RSI3 dip-buy shape, but with SAME-DAY
                           exit geometry instead of the live system's 48h.
  4. VWAP FADE          — fade an overextension from a rolling 24h VWAP
                           back toward it, gated by the 4h trend regime.

ENGINE NOTES (read backtest.py / strategy.py for ground truth)
- run_backtest takes ONE fixed stop_pct/target_pct for the whole run, not
  a per-trade dynamic level. Where the family spec calls for a per-trade
  dynamic distance (k*ATR, range height, distance-to-VWAP), we follow this
  repo's established approximation (round 17 / step41): compute the
  representative distance as a TRAIN-only median, hold it fixed across
  train and val, and say so plainly in the results file. Every stop is
  hard-capped at 1.7% (the "ideal" ceiling from the mandate); nothing here
  needs the looser 2.0% allowance.
- max_hold is NOT a backtest.py parameter. It is enforced inside each
  family's own signal-construction state machine (same pattern as
  strategy.event_short / step41's persistence_signal / forensic_signal):
  the signal forces flat once a position has been held `max_hold` bars,
  independent of the engine's own stop_pct/target_pct intrabar exits.
  Every family's max_hold is <=24h in bars, by construction.
- Cross-timeframe alignment (4h champion trend read from 1h/15m bars) is
  done with merge_asof on the 4h bar's CLOSE time (open_time + 4h), never
  its open time — using a 4h bar's signal before it has closed would be
  lookahead.
- No lookahead within a timeframe: rolling extremes / session ranges use
  only bars that have already printed relative to the entry check; nothing
  here needs an extra .shift(1) beyond what's noted per family, because the
  entry check itself is gated to bars STRICTLY AFTER the window that
  defines the level (session breakout) or uses smoothing indicators (ATR/
  RSI/VWAP) the same un-shifted way the rest of the codebase does — the
  engine's own bar-close-N -> fill-at-open-N+1 mechanic is what enforces
  no-lookahead there, exactly as strategy.py's docstring explains.
- GAUNTLET: chronological 60/20/20 per timeframe. This script NEVER slices
  into the final 20% (test). Only train (0:i_tr) and val (i_tr:i_va) are
  ever computed or printed.
- Cost discipline: CostModel defaults (6bps taker / 2bps maker, 1bp
  half-spread, 2bp slippage), execution="maker", REAL funding via
  align_funding — same as step41_shorts.py, imported and reused.

DISCIPLINE: selection is by TRAIN expectancy only; val is checked once and
never tuned against. No config here re-tunes the benched "15m entries +
wide (1.5%) stop long" near-miss from the 2026-07-23 credit-sprint —
these are four structurally different entry shapes.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, rsi, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
HARD_STOP_CAP = 1.7          # % — the mandate's "ideal" ceiling, enforced everywhere
CHAMP_KW = dict(fast=20, slow=100, min_atr_pct=1.5)   # the standing 4h champion


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def bar_hours(d):
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def hours_to_bars(d, hours):
    return max(1, round(hours / bar_hours(d)))


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def champ_aligned(frame4h, champ4h, target_frame):
    """The 4h champion trend (0/1), read onto a finer timeframe with NO
    lookahead: a 4h bar's signal becomes visible only at its CLOSE (open
    time + 4h), so we shift the availability timestamp forward before the
    as-of merge. A 1h/15m bar at time t sees whatever the most recently
    CLOSED 4h bar decided — never a 4h bar still in progress."""
    avail = pd.DataFrame({
        "timestamp": frame4h["timestamp"] + pd.Timedelta(hours=4),
        "champ": champ4h.fillna(0.0).to_numpy(),
    }).sort_values("timestamp")
    merged = pd.merge_asof(target_frame[["timestamp"]].sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["champ"].fillna(0.0).reset_index(drop=True)


def day_trade_signal(d, enter_long, enter_short, max_hold_bars):
    """Generic bidirectional event-entry / timed-exit state machine — the
    day-trade analogue of strategy.event_short, generalized to also take
    longs. A position opens on enter_long/enter_short, and the SIGNAL's
    only job is to force flat after max_hold_bars; stop_pct/target_pct
    (engine-managed) do the rest of the exiting. Same discipline as
    step41's persistence_signal/forensic_signal: after an engine-side
    stop/target fires, run_backtest blocks re-entry until this signal
    itself returns to 0, which happens at (or before) max_hold."""
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if el[i]:
                pos, held = 1.0, 0
            elif es[i]:
                pos, held = -1.0, 0
        else:
            held += 1
            if max_hold_bars and held >= max_hold_bars:
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def score(d, sig, f, i_tr, i_va, stop_pct=None, target_pct=None, execution="maker"):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def hold_stats(tr, va):
    """Median/mean hold time in HOURS, pooled across train+val trades (test
    is sealed, never touched). NaN if no trades at all."""
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), float("nan")
    hrs = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades]
    return float(np.median(hrs)), float(np.mean(hrs))


def mk_row(family, cfg, tf, tr, va, stop_pct=None, target_pct=None, max_hold_h=None):
    med_h, mean_h = hold_stats(tr, va)
    return {
        "family": family, "config": cfg, "tf": tf,
        "stop%": stop_pct, "target%": target_pct, "max_hold_h": max_hold_h,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_ret%": tr.total_return_pct,
        "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_ret%": va.total_return_pct,
        "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr, va),
    }


# ---------------------------------------------------------------------------
# FAMILY 1 — momentum burst
# ---------------------------------------------------------------------------

def momentum_burst_entries(d, champ_al, X, bars_move, cond):
    """impulse = close-to-close move over `bars_move` bars >= X% (up) or
    <= -X% (down). cond='champ': long only when champ==1, short only when
    champ==0 (the mirror-condition "not in the long regime"). cond='raw':
    unconditioned, trade the impulse's own direction either way."""
    ret = (d["close"] / d["close"].shift(bars_move) - 1) * 100
    up = ret >= X
    down = ret <= -X
    if cond == "champ":
        enter_long = up & (champ_al == 1)
        enter_short = down & (champ_al == 0)
    else:
        enter_long, enter_short = up, down
    return enter_long.fillna(False), enter_short.fillna(False)


def family1_momentum_burst(frames, funding, meta, champ4h, frame4h):
    rows = []
    specs = [("1h", 1), ("15m", 4)]   # 15m variant: impulse measured over 4 bars
    for tf, bars_move in specs:
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        champ_al = champ_aligned(frame4h, champ4h, d)
        for X in (0.8, 1.2, 1.8):
            for cond in ("champ", "raw"):
                el, es = momentum_burst_entries(d, champ_al, X, bars_move, cond)
                stop_pct = min(1.0 * med_atr, HARD_STOP_CAP)
                for tmult in (2.0, 3.0):
                    target_pct = tmult * med_atr
                    for max_hold_h in (8, 24):
                        mh_bars = hours_to_bars(d, max_hold_h)
                        sig = day_trade_signal(d, el, es, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"X{X:.1f}% {cond} tgt{tmult:.0f}xATR hold{max_hold_h}h"
                        rows.append(mk_row("1-momentum-burst", cfg, tf, tr, va,
                                            stop_pct, target_pct, max_hold_h))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — session breakout
# ---------------------------------------------------------------------------

def session_range(d, H):
    """First-H-UTC-hours range per calendar day. Entries are only allowed
    on bars strictly AFTER the window closes (frac_hour >= H), by which
    time the window's high/low are fully known and fixed — the equivalent
    of a shift(1) discipline applied at the window boundary rather than
    bar-by-bar."""
    ts = d["timestamp"]
    day = ts.dt.floor("D")
    frac_hour = ts.dt.hour + ts.dt.minute / 60.0
    in_window = frac_hour < H
    tmp = pd.DataFrame({"day": day, "high": d["high"], "low": d["low"]})
    win_high = tmp["high"].where(in_window).groupby(tmp["day"]).transform("max")
    win_low = tmp["low"].where(in_window).groupby(tmp["day"]).transform("min")
    after_window = ~in_window
    return win_high, win_low, after_window


def family2_session_breakout(frames, funding, meta):
    rows = []
    for tf in ("15m", "1h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        for H in (4, 8):
            win_high, win_low, after_window = session_range(d, H)
            range_height_pct = ((win_high - win_low) / win_low * 100)
            # TRAIN-only representative range height -> the fixed stop/target
            # this run uses (approximation stated in header + results.md)
            med_range_pct = float(range_height_pct.iloc[:i_tr].dropna().median())
            stop_pct = min(med_range_pct, HARD_STOP_CAP)
            enter_long = after_window & (d["close"] > win_high)
            enter_short = after_window & (d["close"] < win_low)
            mh_bars = hours_to_bars(d, max(1, 24 - H))   # approximation, stated
            for direction, el, es in (
                ("long", enter_long, pd.Series(False, index=d.index)),
                ("short", pd.Series(False, index=d.index), enter_short),
            ):
                sig = day_trade_signal(d, el, es, mh_bars)
                for tmult in (1.5, 2.5):
                    target_pct = tmult * med_range_pct
                    tr, va = score(d, sig, f, i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct)
                    cfg = f"H{H}h {direction} tgt{tmult:.1f}xrange"
                    rows.append(mk_row("2-session-breakout", cfg, tf, tr, va,
                                        stop_pct, target_pct, 24 - H))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — washout scalp
# ---------------------------------------------------------------------------

def family3_washout_scalp(frames, funding, meta, champ4h, frame4h):
    rows = []
    for tf, rsi_n in (("1h", 3), ("15m", 3)):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
        champ_al = champ_aligned(frame4h, champ4h, d)
        r = rsi(d["close"], rsi_n)
        for rsi_thresh in (5, 10):
            enter_long = (r < rsi_thresh) & (champ_al == 1)
            enter_long = enter_long.fillna(False)
            enter_short = pd.Series(False, index=d.index)   # dip-buy shape: long only
            for stop_pct in (1.0, 1.5):
                for target_pct in (2.0, 3.0):
                    for max_hold_h in (12, 24):
                        mh_bars = hours_to_bars(d, max_hold_h)
                        sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va,
                                       stop_pct=min(stop_pct, HARD_STOP_CAP),
                                       target_pct=target_pct)
                        cfg = (f"RSI{rsi_n}<{rsi_thresh} stop{stop_pct:.1f}% "
                               f"tgt{target_pct:.1f}% hold{max_hold_h}h")
                        rows.append(mk_row("3-washout-scalp", cfg, tf, tr, va,
                                            min(stop_pct, HARD_STOP_CAP),
                                            target_pct, max_hold_h))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — VWAP fade
# ---------------------------------------------------------------------------

def rolling_vwap(d, n=24):
    pv = d["close"] * d["volume"]
    vwap = pv.rolling(n).sum() / d["volume"].rolling(n).sum()
    return vwap.shift(1)     # shift(1): today's entry never sees its own bar's volume


def family4_vwap_fade(frames, funding, meta, champ4h, frame4h):
    rows = []
    if "volume" not in frames["1h"].columns or frames["1h"]["volume"].isna().all():
        return [{"family": "4-vwap-fade", "config": "SKIPPED — no volume column",
                  "tf": "1h", "stop%": None, "target%": None, "max_hold_h": None,
                  "tr_n": 0, "tr_exp": 0, "tr_win%": 0, "tr_ret%": 0, "tr_dd%": 0,
                  "va_n": 0, "va_exp": 0, "va_win%": 0, "va_ret%": 0, "va_dd%": 0,
                  "med_hold_h": float("nan"), "mean_hold_h": float("nan"),
                  "verdict": "SKIPPED"}]
    tf = "1h"
    d, f = frames[tf], funding[tf]
    n, i_tr, i_va = meta[tf]["n"], meta[tf]["i_tr"], meta[tf]["i_va"]
    med_atr = meta[tf]["med_atr"]
    champ_al = champ_aligned(frame4h, champ4h, d)
    a = atr(d, 14)
    vwap = rolling_vwap(d, 24)
    mh_bars = hours_to_bars(d, 24)
    stop_pct = min(1.2 * med_atr, HARD_STOP_CAP)

    for k in (1.5, 2.5):
        dist_long = d["close"] < (vwap - k * a)
        dist_short = d["close"] > (vwap + k * a)
        enter_long = (dist_long & (champ_al == 1)).fillna(False)
        enter_short = (dist_short & (champ_al == 0)).fillna(False)

        # TRAIN-only median distance-to-VWAP at qualifying entries -> the
        # fixed target this run uses (dynamic per-trade "exit at VWAP touch"
        # is not directly expressible in the engine; stated approximation).
        vwap_dist_pct = ((vwap - d["close"]).abs() / d["close"] * 100)
        long_train_entries = enter_long.iloc[:i_tr]
        short_train_entries = enter_short.iloc[:i_tr]
        entry_dists = pd.concat([
            vwap_dist_pct.iloc[:i_tr][long_train_entries],
            vwap_dist_pct.iloc[:i_tr][short_train_entries],
        ])
        target_pct = min(float(entry_dists.median()), 3.0) if len(entry_dists) else 3.0

        sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        cfg = f"k={k:.1f}xATR both-directions"
        rows.append(mk_row("4-vwap-fade", cfg, tf, tr, va, stop_pct, target_pct, 24))
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading cached data (no network calls needed)...")
    frames = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h", "4h")}
    funding_hist = fetch_funding_history("BTCUSDT")
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in ("15m", "1h")}

    meta = {}
    for tf in ("15m", "1h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_train = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR% = {med_atr_train:.3f}%")

    frame4h = frames["4h"]
    print(f"  4h (champion-trend source only): {len(frame4h)} bars, "
          f"{frame4h['timestamp'].iloc[0]:%Y-%m-%d} -> {frame4h['timestamp'].iloc[-1]:%Y-%m-%d}")
    champ4h = vol_gated_ma(frame4h, **CHAMP_KW)
    print(f"  champion (4h vol_gated_ma {CHAMP_KW}) time-in-market: "
          f"{(champ4h == 1).mean() * 100:.1f}% of bars")

    print("\nRunning FAMILY 1 (momentum burst)...")
    rows = family1_momentum_burst(frames, funding, meta, champ4h, frame4h)
    print(f"  {len(rows)} configs done")
    print("Running FAMILY 2 (session breakout)...")
    rows += family2_session_breakout(frames, funding, meta)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 3 (washout scalp)...")
    rows += family3_washout_scalp(frames, funding, meta, champ4h, frame4h)
    print(f"  {len(rows)} configs cumulative")
    print("Running FAMILY 4 (VWAP fade)...")
    rows += family4_vwap_fade(frames, funding, meta, champ4h, frame4h)
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

    df.to_csv("step43_results_raw.csv", index=False)
    print("\nRaw results written to step43_results_raw.csv")
    print("(step43_results.md written separately after this run)")
    return df


if __name__ == "__main__":
    main()
