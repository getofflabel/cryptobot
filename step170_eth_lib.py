"""
step170_eth_lib.py — shared plumbing for ETH's transfer-test + native
research program (Morgan's expanded mandate, 2026-07-25: build ETH a
family map comparable to BTC's ~30-family program).

Nothing here is BTC-specific plumbing copied blind — it is the SAME
generic helpers step43/step45b/step58 already built (day_trade_signal,
score, split_points, champ_aligned, mk_row, verdict_for, hold_stats),
imported where possible, re-declared only where the BTC module hardcodes
"maker" execution or a BTC-only constant that this desk's standards for
tonight override (execution MUST be "taker" here per the eth-trader
mandate, not step43's "maker" default).

DATA: ETH has its own bybit history (data_bybit_ETHUSDT_1h/4h/15m_full +
funding), same vintage/depth as BTC's (2021-03 -> 2026-07, ~5.4y), loaded
via the same fetch_bybit_deep() cache-or-fetch helper used everywhere else
in this repo. No network calls needed — every file is already cached.

COSTS: BloFin's fee schedule (config.fee_bps) is EXCHANGE-WIDE, not
per-symbol — 6bps taker / 2bps maker, same figure this repo has used for
BTC/gold/SPX throughout. Per BLOFIN_API_REFERENCE.md, contract VALUE
differs wildly per symbol (never assumed elsewhere in this file), but fee
bps do not. Taker round trip = 2*(6+1+2) = 18bps worst-case; this repo's
realized blended cost on day-trade-shaped signals has run closer to ~9bps
(step43/step45b) — both figures are the hurdle stated per family below.

STRUCTURE STOPS: confirmed_swings() (step41_shorts.py) gives lookahead-
safe k-bar fractal swing prices. Two usages appear in this program and
both are used here:
  (a) the step58 pattern — TRAIN-only median distance from entry to the
      qualifying swing extreme, held fixed across train+val (because
      backtest.run_backtest takes one stop_pct for the whole run) — used
      for the vectorized family sweeps (this file's swing_stop_pct).
  (b) exits.py's per-trade stop_structure()/target_structure() — the
      TRUE per-trade dynamic level, used for the exit-variation rounds
      that specifically test whether a smarter dynamic stop (vs the
      approximation in (a)) changes the verdict.
Neither is ever a swept percentage; a fixed % stop appears in this file
ONLY as the naive control, exactly as exits.py's own docstring insists.
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings
from strategy import atr, donchian_breakout, rsi, vol_gated_ma

SYMBOL = "ETHUSDT"
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
HARD_STOP_CAP_DAYTRADE = 1.7     # % — BTC's day-trade ceiling, stated when reused unchanged
STOP_CAP_SWING = 4.0             # % — BTC's swing-stop ceiling (step58), stated when reused
EXECUTION = "taker"              # desk standard tonight: ALWAYS taker, never maker

cm = CostModel()
TAKER_RT_BPS = cm.round_trip_bps()                 # worst-case taker round trip
MAKER_RT_BPS = 2 * cm.maker_fee_bps                # best-case maker round trip (for reference only)
REALIZED_DAYTRADE_RT_BPS = 9.0                      # this program's realized blended cost, day-trade shapes


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def load_frames(timeframes=("15m", "1h", "4h")):
    frames = {tf: fetch_bybit_deep(tf, SYMBOL) for tf in timeframes}
    funding_hist = fetch_funding_history(SYMBOL)
    funding = {tf: align_funding(frames[tf], funding_hist)
               for tf in timeframes if tf != "4h" or "4h" in timeframes}
    return frames, funding, funding_hist


# ---------------------------------------------------------------------------
# generic helpers (same contracts as step43/step58, taker by default)
# ---------------------------------------------------------------------------

def bar_hours(d):
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def hours_to_bars(d, hours):
    return max(1, round(hours / bar_hours(d)))


def days_to_bars(d, days):
    return hours_to_bars(d, days * 24)


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def champ_aligned(frame4h, champ4h, target_frame):
    avail = pd.DataFrame({
        "timestamp": frame4h["timestamp"] + pd.Timedelta(hours=4),
        "champ": champ4h.fillna(0.0).to_numpy(),
    }).sort_values("timestamp")
    merged = pd.merge_asof(target_frame[["timestamp"]].sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["champ"].fillna(0.0).reset_index(drop=True)


def day_trade_signal(d, enter_long, enter_short, max_hold_bars):
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


def score(d, sig, f, i_tr, i_va, stop_pct=None, target_pct=None, execution=EXECUTION):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True) if f is not None else None,
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def score_sealed(d, sig, f, i_va, n, stop_pct=None, target_pct=None, execution=EXECUTION):
    """Test-only run — ONLY call this after a config has already been
    selected on train and read once on val. i_va:n is the sealed 20%."""
    return run_backtest(
        d.iloc[i_va:n].reset_index(drop=True),
        sig.iloc[i_va:n].reset_index(drop=True),
        execution=execution,
        funding_series=f.iloc[i_va:n].reset_index(drop=True) if f is not None else None,
        stop_pct=stop_pct, target_pct=target_pct,
    )


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def hold_stats(tr, va):
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), float("nan")
    hrs = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in trades]
    return float(np.median(hrs)), float(np.mean(hrs))


def thickness(tr, va):
    """Edge as a multiple of round-trip cost, taker. backtest.py's Trade
    has no return_pct field, so it is derived here the same way the
    engine derives PnL%: net pnl / notional at entry (entry_price *
    units), pooled across train+val trades (test stays sealed)."""
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), float("nan")
    rets = []
    for t in trades:
        notional = abs(t.entry_price * t.units)
        if notional > 0:
            rets.append(t.pnl / notional * 100)
    if not rets:
        return float("nan"), float("nan")
    mean_ret_pct = float(np.mean(rets))
    mult_taker = (mean_ret_pct * 100) / TAKER_RT_BPS if TAKER_RT_BPS else float("nan")
    return mean_ret_pct, mult_taker


def mk_row(family, cfg, tf, tr, va, stop_pct=None, target_pct=None, max_hold_h=None,
           extra=None):
    med_h, mean_h = hold_stats(tr, va)
    mean_ret_pct, mult_taker = thickness(tr, va)
    row = {
        "family": family, "config": cfg, "tf": tf,
        "stop%": stop_pct, "target%": target_pct, "max_hold_h": max_hold_h,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_ret%": tr.total_return_pct,
        "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_ret%": va.total_return_pct,
        "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "mean_ret_pct_of_notional": mean_ret_pct,
        "thickness_x_taker_cost": mult_taker,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


# ---------------------------------------------------------------------------
# structure-stop helpers (chart structure, not a swept percentage)
# ---------------------------------------------------------------------------

def swing_stop_pct(entry_close, extreme, entries_mask, i_tr, buffer_pct, cap):
    """TRAIN-only median distance from entry close to the qualifying swing
    extreme, plus a stated buffer, hard-capped. Identical method to
    step58's swing_stop_pct on BTC — the RECIPE (k, buffer_pct, cap) is
    unchanged; the resulting number is naturally ETH's own, because it is
    computed from ETH's own train-window swings, not ported from BTC."""
    dist = ((entry_close - extreme).abs() / entry_close * 100)
    train_dist = dist.iloc[:i_tr][entries_mask.iloc[:i_tr]]
    if len(train_dist) == 0 or train_dist.isna().all():
        return cap
    return min(float(train_dist.median()) + buffer_pct, cap)


def eth_atr_pct_medians(frames):
    """ETH's OWN hourly/4h ATR% medians — recomputed here, never inherited
    from BTC (BTC hourly ATR median ~0.45-0.9% per MARKET_PLAYBOOKS.md;
    ETH's own number is computed fresh below and stated in every report
    that uses it)."""
    out = {}
    for tf, d in frames.items():
        a = atr(d, 14) / d["close"] * 100
        out[tf] = {"median": float(a.median()), "p25": float(a.quantile(.25)),
                   "p75": float(a.quantile(.75))}
    return out


def chance_baseline(d, f, i_tr, i_va, n_long, n_short, max_hold_bars,
                     stop_pct, target_pct, n_draws=30, seed=170):
    """Empirical chance baseline (R83/R90/step93 convention): n_draws
    random-timing entry sets of the SAME cardinality (n_long longs, n_short
    shorts) run through the identical engine/costs/stop/target. Reports the
    fraction of draws that would have cleared the SURVIVOR bar (train AND
    val both positive, both floors met) by pure luck alone."""
    rng = np.random.default_rng(seed)
    n = len(d)
    survivor_hits = 0
    tr_exps, va_exps = [], []
    for draw in range(n_draws):
        idx = rng.choice(n, size=min(n_long + n_short, n), replace=False)
        long_idx = idx[:n_long]
        short_idx = idx[n_long:n_long + n_short]
        el = pd.Series(False, index=d.index)
        es = pd.Series(False, index=d.index)
        el.iloc[long_idx] = True
        es.iloc[short_idx] = True
        sig = day_trade_signal(d, el, es, max_hold_bars)
        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        tr_exps.append(tr.expectancy)
        va_exps.append(va.expectancy)
        if verdict_for(tr, va) == "SURVIVOR":
            survivor_hits += 1
    return {
        "n_draws": n_draws,
        "survivor_rate": survivor_hits / n_draws,
        "mean_tr_exp": float(np.mean(tr_exps)),
        "mean_va_exp": float(np.mean(va_exps)),
    }
