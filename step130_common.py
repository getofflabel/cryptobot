"""
step130_common.py — shared infra for the round 130+ SPX family-map night.

Context: R60 (step60_spx_system.py) validated exactly TWO real edges (RSI2<5
dip-buy, SMA regime membership) across ~6 families in one round. Wallace's
verdict: "your entire thing is that you're only doing panic buys... that's
barely different from a buy limit at a low price" — and morgan's follow-up
mandate is a real family map, comparable in breadth to BTC's ~30-family/50+
round programme (survivors AND confirmed-dead both matter). This file is the
one shared toolkit every step13X_*.py script in that push imports from,
instead of re-deriving data loading, cost models, or gauntlet scoring N
times — same anti-duplication discipline step60 itself used relative to
step41/43/48.

REUSED VERBATIM OR NEAR-VERBATIM (not reinvented):
- CostModel construction (ETF_COSTS/FUT_COSTS): identical bps to step60's
  ETF_COSTS/FUT_COSTS (SPY 1bp+1bp=4bps RT, ES=F 0.5bp+0.5bp=2bps RT,
  funding zeroed — matches MARKET_PLAYBOOKS.md exactly).
- score()/verdict_for()/mk_row(): copied from step60_spx_system.py, same
  MIN_TRAIN_TRADES=30/MIN_VAL_TRADES=8 bar (step43_daytrade), same
  SURVIVOR/INSUFFICIENT-SAMPLE/FAIL taxonomy.
- split_points, bar_hours, hours_to_bars, day_trade_signal: imported
  unmodified from step43_daytrade.py.
- gap_stats_summary, gap_honesty_correction, days_to_bars: imported
  unmodified from step48_tradfi_trend.py.
- confirmed_swings, adaptive_vol_gate: imported unmodified from
  step41_shorts.py (per the task's explicit "use confirmed_swings()" ask).
- exits.py imported wholesale as X — every stop/target below composes its
  ExitMethod library rather than hand-rolling new exit logic.

DATA: same data_spx_<TAG>_<TF>.parquet cache step60 built (SPY/ES x 1d/1h),
plus data_spx_QQQ_1d/1h (already cached, third instrument for extra
confirmation where useful) and the 15m smoke files
(data_spx72_ES_15m_smoke.parquet / data_spx72_NQ_15m_smoke.parquet — ~72
days, ES/NQ only, no SPY). NOTHING is re-fetched here; if a file is
missing, load_symbol() raises loudly rather than silently pulling fresh
data with a different span (a silent re-fetch would quietly break the
frozen 60/20/20 split point every downstream script assumes).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from strategy import atr, rsi, buy_and_hold, vol_gated_ma, ma_crossover
from step41_shorts import adaptive_vol_gate, confirmed_swings
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours, day_trade_signal,
    hours_to_bars, split_points,
)
from step48_tradfi_trend import (
    days_to_bars, event_long, gap_honesty_correction, gap_stats_summary,
)
import exits as X

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

INITIAL_EQUITY = 10_000.0

ETF_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                       slippage_bps=1.0, funding_bps_8h=0.0)
FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                       slippage_bps=0.5, funding_bps_8h=0.0)
COSTS = {"SPY": ETF_COSTS, "ES": FUT_COSTS, "QQQ": ETF_COSTS, "NQ": FUT_COSTS}
ROUND_TRIP_BPS = {"SPY": ETF_COSTS.round_trip_bps(), "ES": FUT_COSTS.round_trip_bps(),
                   "QQQ": ETF_COSTS.round_trip_bps(), "NQ": FUT_COSTS.round_trip_bps()}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load_symbol(tag: str, tf: str) -> pd.DataFrame:
    """Loads the FROZEN cache only — never re-fetches. tf='15m' routes to
    the smoke files (ES/NQ only, ~72 days)."""
    fname = f"data_spx72_{tag}_15m_smoke.parquet" if tf == "15m" else f"data_spx_{tag}_{tf}.parquet"
    d = pd.read_parquet(fname)
    return d.reset_index(drop=True)


def span_meta(d: pd.DataFrame) -> dict:
    n, i_tr, i_va = split_points(d)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    return {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def realized_vol_pct(d: pd.DataFrame, window: int = 756, min_periods: int = 252) -> pd.Series:
    """Same definition as step60's realized_vol_pct(): 20d realized-vol
    ranked (0-100) within its own trailing ~3y distribution, causal."""
    ret = d["close"].pct_change()
    vol20 = ret.rolling(20).std()
    return vol20.rolling(window, min_periods=min_periods).rank(pct=True) * 100


def down_streak(close: pd.Series) -> pd.Series:
    down = close < close.shift(1)
    grp = (~down).cumsum()
    streak = down.groupby(grp).cumcount() + 1
    return streak.where(down, 0).astype(float)


def dipbuy_exit_mask(d: pd.DataFrame) -> pd.Series:
    """The shared R60 dip-buy exit condition: close > SMA5 OR RSI2 > 65."""
    sma5 = sma(d["close"], 5)
    r2 = rsi(d["close"], 2)
    return (d["close"] > sma5) | (r2 > 65)


def tom_flag(d: pd.DataFrame) -> pd.Series:
    """R60 family 5's EXACT turn-of-month definition, reused verbatim so
    this round's TOM work is the same window that produced t=2.43: last
    trading day of the month (is_month_end) OR one of the first 3 trading
    days of the new month (day_rank<3, 0-indexed -> days 1,2,3)."""
    ts_et = d["timestamp"].dt.tz_convert("America/New_York")
    month = ts_et.dt.to_period("M")
    is_month_end = (month != month.shift(-1)).fillna(False)
    day_rank = d.groupby(month.to_numpy()).cumcount()
    return (is_month_end | (day_rank < 3)).astype(bool)


# ---------------------------------------------------------------------------
# gauntlet plumbing (copied from step60_spx_system.py)
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None, execution="taker"):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution=execution, stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va) -> str:
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def hold_stats(tr, va):
    def med_mean(res):
        if not res.trades:
            return 0.0, 0.0
        hrs = [(t.exit_time - t.entry_time).total_seconds() / 3600 for t in res.trades]
        return float(np.median(hrs)), float(np.mean(hrs))
    m1 = med_mean(tr)
    m2 = med_mean(va)
    return m1, m2


def mk_row(family, config, symbol, tf, tr, va, stop_pct=None, target_pct=None, extra=None):
    (med_h_tr, mean_h_tr), (med_h_va, mean_h_va) = hold_stats(tr, va)
    row = {
        "family": family, "config": config, "symbol": symbol, "tf": tf,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def thickness_multiple(exp_dollar: float, symbol: str) -> tuple[float, float]:
    """Edge as % of notional (expectancy / INITIAL_EQUITY, the same
    approximation basis the engine's own total_return_pct uses) AND as a
    multiple of that instrument's OWN round-trip cost (never a shared
    constant across SPY/ES=F, which have different bps). Returns
    (edge_pct_of_notional, multiple_of_round_trip_cost)."""
    edge_pct = exp_dollar / INITIAL_EQUITY * 100
    cost_pct = ROUND_TRIP_BPS[symbol] / 100
    mult = edge_pct / cost_pct if cost_pct else float("nan")
    return edge_pct, mult


def tstat_1samp(x: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 2:
        return float("nan")
    std = float(np.std(x, ddof=1))
    if std <= 0:
        return float("nan")
    return float(np.mean(x)) / (std / np.sqrt(n))


# ---------------------------------------------------------------------------
# family map logging
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# generic same-bar simulator result (for custom loops that can't go through
# run_backtest's next-bar-open-fill mechanic — same engine-mismatch reason
# step60's family 2a needed its own simulate_gap_trades(); this is that
# same SimTrade/SimResult pair, generalized and promoted to shared infra
# since round 130+ needs it in more than one script).
# ---------------------------------------------------------------------------

class SimTrade:
    __slots__ = ("entry_time", "exit_time", "pnl", "reason")

    def __init__(self, entry_time, exit_time, pnl, reason):
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.pnl = pnl
        self.reason = reason

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


class SimResult:
    """Same expectancy/win_rate/total_return_pct/max_drawdown_pct surface
    as BacktestResult, for bar-local custom simulators."""

    def __init__(self, trades: list, initial_equity: float = INITIAL_EQUITY):
        self.trades = trades
        self.initial_equity = initial_equity

    @property
    def expectancy(self) -> float:
        return float(np.mean([t.pnl for t in self.trades])) if self.trades else 0.0

    @property
    def win_rate(self) -> float:
        return (sum(t.is_win for t in self.trades) / len(self.trades)) if self.trades else 0.0

    @property
    def total_return_pct(self) -> float:
        return float(sum(t.pnl for t in self.trades) / self.initial_equity * 100)

    @property
    def max_drawdown_pct(self) -> float:
        if not self.trades:
            return 0.0
        curve = [self.initial_equity]
        eq = self.initial_equity
        for t in self.trades:
            eq += t.pnl
            curve.append(eq)
        curve = np.array(curve)
        peak = np.maximum.accumulate(curve)
        dd = (curve - peak) / peak
        return float(dd.min() * 100)


def mk_sim_row(family, config, symbol, tf, tr, va, extra=None):
    row = {
        "family": family, "config": config, "symbol": symbol, "tf": tf,
        "stop%": None, "target%": None,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


FAMILY_MAP_PATH = "step130_family_map.md"


def append_family_map(lines: list[str]) -> None:
    """Append-only log, one line per family, per morgan's ask: family name,
    status, key number, chance baseline, thickness multiple. Appends (never
    overwrites) so re-running an earlier step13X script during the same
    night doesn't erase prior entries — dedup is visual/manual, matching
    this repo's plain-append convention elsewhere (RESEARCH_LOG.md)."""
    with open(FAMILY_MAP_PATH, "a") as f:
        for line in lines:
            f.write(line + "\n")
