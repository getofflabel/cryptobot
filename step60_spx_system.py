"""
step60_spx_system.py — Round 60: THE S&P SYSTEM.

MANDATE (Wallace): "look at gold, the S&P, and crypto — they're different
markets, adjust to each." Prior rounds (R47: WatcherGuru news does NOT move
SPY in-session, 1.03x baseline; R48: generic crypto-shape ports were
sample-thin/mostly INSUFFICIENT on daily SPY) proved the index needs its
OWN playbook, not crypto hand-me-downs or a gold-shaped port. This round
builds five INDEX-NATIVE families born from the index's own personality:
famous dip-buy folklore, overnight/gap structure, the slow trend backbone,
the "different weapons for different regimes" architecture, and a
seasonality audit.

RESEARCH ONLY. Writes exactly: step60_spx_system.py (this file),
step60_results.md (composed by hand from this script's stdout, same
discipline as step48/step55), and data_spx_<TAG>_<TF>.parquet data files.
No commits, no live orders.

★★★ NO DEMO VENUE EXISTS for the real S&P 500. BloFin's "SPX-USDT" is the
SPX6900 MEMECOIN — completely unrelated to the S&P 500 index, and is NEVER
touched or referenced by this script. This entire round is KNOWLEDGE-
BANKING for when a real S&P execution venue (Alpaca paper for SPY, a
futures broker for ES=F) exists. See step60_results.md's closing section.

DATA
  SPY (ETF proxy for the index, RTH-only 9:30-16:00 ET) via yfinance:
    - 1d: max history (33 years, since 1993 — the longest, deepest series
      in this program).
    - 1h: ~730d, yfinance's practical ceiling for hourly ETF bars. RTH
      only: yfinance returns no pre/post-market 1h bars for SPY, so the
      first bar of every trading day is exactly the 9:30-10:30 ET bar —
      the literal "first hour" the family-2c spec asks for, with no
      further session-boundary detection needed.
  ES=F (CME E-mini S&P futures, ~23h/day session with a ~1h maintenance
    break ~17:00-18:00 ET, closed weekends) via yfinance, same 1d "max" /
    1h "730d" pulls, as the ROBUSTNESS TWIN: same-shape families re-run on
    a near-continuous-session instrument to see whether an edge survives
    a completely different session structure (SPY's hard 6.5h RTH box vs
    ES's near-24h grind). Used for families 1 (dip-buying) and 3 (trend);
    families 2/4/5 are SPY-only because they are explicitly about SPY's
    session/RTH structure (gap-fill needs a real close-to-open gap,
    first-hour-break needs an RTH open, the regime-split centerpiece and
    seasonality audit are about "the index" in its most literal, most
    heavily-arbitraged form).
  Both instruments' data are cached at data_spx_<TAG>_<TF>.parquet
  (TAG in {SPY, ES}). SPY 1d/1h reuse round-48's data_tradfi_SPY_<TF>.parquet
  cache if this round's own cache is absent (same underlying series,
  fetched <24h before this round; re-fetching would just reproduce it —
  same reuse discipline as step55's GC=F cache chain). ES=F has no prior
  cache in this repo and is fetched fresh.

SESSION HANDLING (documented per the task's explicit ask)
  SPY: RTH-only bars mean there is a REAL overnight gap every single
  trading day (16:00 close -> 9:30 next-day open, ~17.5h dark, more over
  weekends/holidays) — this is where family 2's gap-fill and overnight-
  drift families live. gap_stats_summary() (imported from step48) reports,
  per instrument/TF, what fraction of bars gap past each stop candidate —
  the structural exposure this round's protective stops must respect.
  ES=F: near-continuous session means gaps are structurally much smaller
  (no long dark window except the weekend), reported side-by-side with
  SPY's for direct contrast — the single clearest number-based illustration
  of "session structure changes what a stop even means" this round has.

GAP HONESTY (fill at open when a stop/entry is gapped through, quantified)
  - FAMILY 1 (dip-buying) and FAMILY 4 (regime-split) use an OPTIONAL
    ATR-scaled protective stop on daily bars. Every SURVIVOR/
    INSUFFICIENT-SAMPLE config with a stop is re-checked with
    gap_honesty_correction() (imported from step48): did the exit bar's
    OPEN already gap past the modeled stop-fill price? If so, the trade
    is re-priced at the (worse) open, and the gap-adjusted expectancy is
    reported alongside the engine's raw one. A BUILDER_REGISTRY (same
    idiom as step55) lets every candidate's exact signal be rebuilt for
    this second pass without re-deriving parsing logic from the config
    string.
  - FAMILY 2a (gap-fill) is a CUSTOM same-day simulator (see below) that
    already prices its stop/target fills path-honestly bar-by-bar — no
    separate correction pass is needed there; the entry itself IS the
    gap event, priced at the day's own open.

ENGINE-MISMATCH APPROXIMATIONS (stated plainly, per this codebase's
standing discipline — see step43/step48 headers for the same idiom)
  1. GAP-FILL (family 2a) needs to trade the exact bar whose OPEN defines
     the entry condition (today's gap vs yesterday's close) — impossible
     to express through backtest.run_backtest's bar-close-decide /
     next-bar-open-fill mechanic, which always lags by one full bar. A
     dedicated simulate_gap_trades() reproduces the SAME cost discipline
     (CostModel adverse-fill fractions, taker fees on both legs, stop-
     before-target tie-breaking) as a bar-local, same-day loop instead:
     entry at today's open, target = prior close, stop = k*gap_size away,
     exit at target/stop/day's-own-close, whichever is touched first (and
     stop wins a same-bar tie, matching the engine's own convention).
     This is the honest research-grade proxy for a contingent
     market-on-open order — real fill quality vs the exact print is
     idealized, flagged here rather than hidden.
  2. FAMILY 2c (first-hour range break) wants "exit by close" but the
     engine cannot express an exact same-bar close-out any more than
     family 2a can (same one-bar-lag mechanic). Rather than build new
     day-boundary machinery, this family reuses step43's OWN precedent
     for the identical limitation (its session-breakout family used a
     fixed hours-based max_hold as the approximation): a 6-bar safety
     cap (day_trade_signal, imported) — SPY's RTH is 6.5h ≈ 7 bars, so 6
     bars covers essentially the whole session without carrying
     positions overnight in the vast majority of cases.
  3. FAMILY 2b (overnight drift) is computed as a DIRECT statistical
     audit (paired close[t]->open[t+1] returns, gated by regime, with a
     one-sample t-stat and a round-trip-cost haircut) rather than forced
     through run_backtest, exactly as the task instructs ("report as an
     anomaly audit even if untradeable-thin per event") — this sidesteps
     the same one-bar-lag mismatch entirely by never pretending it is a
     tradeable signal in engine terms.

COSTS (no cost-free mode exists — see backtest.py's CostModel)
  ETF (SPY):   1bp fee + 1bp slippage each side, 0 half-spread, 0 funding
               -> round_trip_bps() = 2*(1+0+1) = 4bps. (Matches step48's
               "1bp+1bp ETF" convention exactly.)
  Futures (ES=F): 0.5bp fee + 0.5bp slippage each side, 0 half-spread,
               0 funding -> round_trip_bps() = 2*(0.5+0+0.5) = 2bps,
               matching the task's "2bps futures round trip" literally.
  execution="taker" throughout (matches step48/step55's TradFi
  convention, not the crypto-BloFin "maker" default used in step41/43).

GAUNTLET
  Chronological 60/20/20 per instrument/TF (split_points, imported from
  step43). >=30 train / >=8 val trades to earn SURVIVOR (MIN_TRAIN_TRADES/
  MIN_VAL_TRADES, imported). Selection is by TRAIN expectancy only; val is
  computed and reported, never tuned against. This script NEVER slices
  into the final 20% (test) of ANY split — not SPY, not ES=F, not the 1h
  frames. Family 2b/5 statistical audits are likewise restricted to
  [:i_va] (train+val only) for the same reason.

PLUMBING REUSE (by import, per the task mandate)
  step43_daytrade: MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours,
    hours_to_bars, split_points, day_trade_signal, hold_stats,
    session_range (imported but unused directly — family 2c needed an
    ET-RTH-specific variant, built locally; session_range's UTC-midnight
    convention doesn't fit an ET trading day).
  step48_tradfi_trend: days_to_bars, event_long, gap_stats_summary,
    gap_honesty_correction.
  step41_shorts: adaptive_vol_gate.
  strategy.py: atr, rsi, vol_gated_ma, buy_and_hold (verbatim, never
    reimplemented).
  backtest.py: CostModel, run_backtest (verbatim, the only engine there is).
  score()/verdict_for()/mk_row() are written LOCALLY (same reasoning
  step48/step55 gave: they need a per-instrument CostModel + "taker"
  execution, which step41/43's imported score() hardcode differently for
  crypto/funding).

FIVE FAMILIES — see each family_*() function's docstring for the exact
spec, traceable line-by-line back to the round-60 brief.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from strategy import atr, buy_and_hold, rsi, vol_gated_ma
from step41_shorts import adaptive_vol_gate
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours, day_trade_signal,
    hold_stats, hours_to_bars, split_points,
)
from step48_tradfi_trend import (
    days_to_bars, event_long, gap_honesty_correction, gap_stats_summary,
)

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

ETF_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                       slippage_bps=1.0, funding_bps_8h=0.0)
FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                       slippage_bps=0.5, funding_bps_8h=0.0)
COSTS = {"SPY": ETF_COSTS, "ES": FUT_COSTS}
TICKER = {"SPY": "SPY", "ES": "ES=F"}

# (family, config, symbol, tf) -> full-length signal Series, for the
# gap-honesty second pass (same idiom as step55's BUILDER_REGISTRY).
BUILDER_REGISTRY: dict[tuple, pd.Series] = {}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def _fetch_yf(symbol: str, interval: str, period: str) -> pd.DataFrame:
    raw = None
    for attempt in range(3):
        try:
            raw = yf.Ticker(symbol).history(period=period, interval=interval,
                                             auto_adjust=False)
            if raw is not None and len(raw) > 0:
                break
        except Exception as e:
            print(f"  retry {symbol} {interval} ({e})")
        time.sleep(2)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"no data returned for {symbol} {interval}")
    df = raw.reset_index()
    tcol = "Date" if "Date" in df.columns else "Datetime"
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df[tcol], utc=True),
        "open": df["Open"].astype(float), "high": df["High"].astype(float),
        "low": df["Low"].astype(float), "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp")
    return out.reset_index(drop=True)


def load_symbol(tag: str, tf: str) -> pd.DataFrame:
    own = f"data_spx_{tag}_{tf}.parquet"
    try:
        d = pd.read_parquet(own)
        print(f"  cached {own}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
        return d
    except FileNotFoundError:
        pass
    legacy = f"data_tradfi_{tag}_{tf}.parquet"
    try:
        d = pd.read_parquet(legacy)
        print(f"  reused {legacy} -> {own}: {len(d)} bars "
              f"{d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
        d.to_parquet(own)
        return d
    except FileNotFoundError:
        pass
    period = "max" if tf == "1d" else "730d"
    interval = "1d" if tf == "1d" else "1h"
    print(f"  fetching fresh {TICKER[tag]} {tf} ({period}) via yfinance...")
    d = _fetch_yf(TICKER[tag], interval, period)
    d.to_parquet(own)
    print(f"  saved {own}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def load_all() -> dict:
    frames = {"SPY": {}, "ES": {}}
    for tag in ("SPY", "ES"):
        frames[tag]["1d"] = load_symbol(tag, "1d")
        frames[tag]["1h"] = load_symbol(tag, "1h")
    return frames


# ---------------------------------------------------------------------------
# local gauntlet plumbing
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution="taker", stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va) -> str:
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(family, config, symbol, tf, tr, va, stop_pct=None, target_pct=None, extra=None):
    med_h, mean_h = hold_stats(tr, va)
    row = {
        "family": family, "config": config, "symbol": symbol, "tf": tf,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def mk_gap_row(family, config, symbol, tf, tr, va):
    """Same schema as mk_row, for the FAMILY-2a custom SimResult objects
    (they have no meaningful hold_stats — trades are same-day by
    construction, so med/mean_hold_h are pinned to 0.0)."""
    return {
        "family": family, "config": config, "symbol": symbol, "tf": tf,
        "stop%": None, "target%": None,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "med_hold_h": 0.0, "mean_hold_h": 0.0,
        "verdict": verdict_for(tr, va),
    }


# ---------------------------------------------------------------------------
# indicators / small helpers
# ---------------------------------------------------------------------------

def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def down_streak(close: pd.Series) -> pd.Series:
    """Length of the CURRENT consecutive down-day run ending at this bar
    (0 on any non-down day). Standard pandas group-cumcount trick."""
    down = close < close.shift(1)
    grp = (~down).cumsum()
    streak = down.groupby(grp).cumcount() + 1
    return streak.where(down, 0).astype(float)


def realized_vol_pct(d: pd.DataFrame, window: int = 756, min_periods: int = 252) -> pd.Series:
    """20d realized-vol percentile: today's 20-trading-day return stdev,
    ranked (0-100) within its own trailing `window` (~3y) distribution —
    INCLUDING today's own reading, the standard "vol percentile" idiom
    (IV-percentile indicators work the same way). This is not lookahead:
    the rank uses only data available by today's close. window=756 (~3y)
    balances "long enough to define a real regime" against "short enough
    to still respond within the sample"; min_periods=252 (~1y) sets the
    earliest day the metric is trusted."""
    ret = d["close"].pct_change()
    vol20 = ret.rolling(20).std()
    return vol20.rolling(window, min_periods=min_periods).rank(pct=True) * 100


def dipbuy_exit(d: pd.DataFrame) -> pd.Series:
    """The shared exit condition for every family-1/4 dip-buy shape:
    close back above SMA5 (short-term normalization) OR RSI2 > 65
    (momentum snap-back) — literally the task's spec, not tuned further."""
    return (d["close"] > sma(d["close"], 5)) | (rsi(d["close"], 2) > 65)


# ---------------------------------------------------------------------------
# FAMILY 1 — index dip-buying (the index's most famous personality)
# ---------------------------------------------------------------------------

def family1_dipbuying(frames, meta):
    """(a) RSI(2) < {5,10,15} on daily, price > SMA200 -> long.
       (b) N-day-low pullback: close = lowest close in {3,5} days while
           > SMA200 -> long.
       (c) consecutive down-days {2,3} while > SMA200 -> long.
    All three share the same exit (dipbuy_exit: close>SMA5 or RSI2>65) and
    NO FIXED TARGET, per the task's literal spec — "the classic Connors
    shape, decades of folklore — test it honestly." Robustness grid: an
    OPTIONAL ATR-scaled protective stop (none / 1.0x / 1.5x TRAIN-median
    ATR%) and an OPTIONAL hard time-cap safety net (none / 60 trading
    days) test whether the folklore needs (or is hurt by) either guardrail.
    Both SPY and ES=F (robustness twin)."""
    rows = []
    stop_variants = [("none", None), ("1.0xATR", 1.0), ("1.5xATR", 1.5)]
    hold_variants = [("nocap", 0), ("cap60d", 60)]
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        med_atr = m["med_atr"]
        close = d["close"]
        sma200 = sma(close, 200)
        r2 = rsi(close, 2)
        exit_cond = dipbuy_exit(d).fillna(False)

        shapes = []
        for th in (5, 10, 15):
            enter = ((r2 < th) & (close > sma200)).fillna(False)
            shapes.append((f"1a-rsi2<{th}", enter))
        for N in (3, 5):
            enter = ((close <= close.rolling(N).min() + 1e-9) & (close > sma200)).fillna(False)
            shapes.append((f"1b-{N}daylow", enter))
        ds = down_streak(close)
        for k in (2, 3):
            enter = ((ds >= k) & (close > sma200)).fillna(False)
            shapes.append((f"1c-downstreak{k}", enter))

        for shape_name, enter in shapes:
            for stop_name, stop_mult in stop_variants:
                stop_pct = None if stop_mult is None else stop_mult * med_atr
                for hold_name, hold_days in hold_variants:
                    hold_bars = days_to_bars(d, hold_days) if hold_days else 0
                    sig = event_long(d, enter, exit_cond, hold_bars)
                    tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                    cfg = f"{shape_name} stop={stop_name} hold={hold_name}"
                    BUILDER_REGISTRY[("1-dipbuying", cfg, tag, "1d")] = sig
                    rows.append(mk_row("1-dipbuying", cfg, tag, "1d", tr, va, stop_pct, None))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2a — gap-fill (custom same-day simulator, see module docstring)
# ---------------------------------------------------------------------------

@dataclass
class GapTrade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    pnl: float
    reason: str

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


class SimResult:
    """A minimal BacktestResult-alike for the gap-fill family's bar-local
    simulator — same expectancy/win_rate/total_return_pct/max_drawdown_pct
    surface mk_row() and print_* helpers expect."""

    def __init__(self, trades: list[GapTrade], initial_equity: float = 10_000.0):
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


def simulate_gap_trades(d: pd.DataFrame, lo: int, hi: int, direction: str,
                         gap_thresh_pct: float, stop_mult: float, costs: CostModel,
                         initial_equity: float = 10_000.0) -> SimResult:
    """GAP-FILL: a day whose OPEN gaps >= gap_thresh_pct against the
    prior close is traded intending a return to that prior close (the
    'fill'). direction='long' = gap DOWN, buy the open, target = prior
    close, stop = stop_mult * gap_size below entry, flat by the day's own
    close if neither is touched. direction='short' mirrors: gap UP, sell
    the open, target = prior close, stop = stop_mult * gap_size above.
    Same-bar stop-before-target tie-break as the engine (backtest.py's own
    stated convention). Costs applied exactly like run_backtest: entry
    price/exit price both adverse-adjusted (CostModel._adverse_frac) with
    taker fees on both legs, compounding on the running `equity`."""
    opens = d["open"].to_numpy()
    highs = d["high"].to_numpy()
    lows = d["low"].to_numpy()
    closes = d["close"].to_numpy()
    times = pd.DatetimeIndex(d["timestamp"])
    adv = costs._adverse_frac
    equity = initial_equity
    trades: list[GapTrade] = []
    lo = max(lo, 1)
    for i in range(lo, hi):
        prior_close = closes[i - 1]
        gap_pct = (opens[i] - prior_close) / prior_close * 100
        if direction == "long":
            if gap_pct > -gap_thresh_pct:
                continue
            gap_size = abs(gap_pct)
            entry = opens[i] * (1 + adv)
            target = prior_close
            stop_price = entry * (1 - stop_mult * gap_size / 100)
            hit_stop = lows[i] <= stop_price
            hit_target = highs[i] >= target
            if hit_stop:
                exit_price, reason = stop_price * (1 - adv), "stop"
            elif hit_target:
                exit_price, reason = target * (1 - adv), "target"
            else:
                exit_price, reason = closes[i] * (1 - adv), "close"
            sign = 1
        elif direction == "short":
            if gap_pct < gap_thresh_pct:
                continue
            gap_size = abs(gap_pct)
            entry = opens[i] * (1 - adv)
            target = prior_close
            stop_price = entry * (1 + stop_mult * gap_size / 100)
            hit_stop = highs[i] >= stop_price
            hit_target = lows[i] <= target
            if hit_stop:
                exit_price, reason = stop_price * (1 + adv), "stop"
            elif hit_target:
                exit_price, reason = target * (1 + adv), "target"
            else:
                exit_price, reason = closes[i] * (1 + adv), "close"
            sign = -1
        else:
            raise ValueError(direction)

        notional_in = equity
        entry_fee = costs.fee(notional_in)
        ret_frac = sign * (exit_price - entry) / entry
        gross = notional_in * ret_frac
        exit_fee = costs.fee(abs(notional_in + gross))
        pnl = gross - entry_fee - exit_fee
        equity += pnl
        trades.append(GapTrade(times[i], times[i], pnl, reason))
    return SimResult(trades, initial_equity)


def family2a_gapfill(frames, meta):
    """Gap-down longs + mirrored gap-up shorts, both SPY and ES=F, gap
    thresholds {0.3, 0.5}% and stop multiples {0.5, 1.0}x the gap's own
    size — exactly the task's grid."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        for gap_th in (0.3, 0.5):
            for stop_mult in (0.5, 1.0):
                for direction in ("long", "short"):
                    tr = simulate_gap_trades(d, 0, i_tr, direction, gap_th, stop_mult, costs)
                    va = simulate_gap_trades(d, i_tr, i_va, direction, gap_th, stop_mult, costs)
                    cfg = f"gapfill {direction} thresh{gap_th}% stop{stop_mult}xgap"
                    rows.append(mk_gap_row("2a-gapfill", cfg, tag, "1d", tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2b — overnight drift (statistical audit, report-only)
# ---------------------------------------------------------------------------

def overnight_drift_stats(d: pd.DataFrame, i_va: int, costs: CostModel,
                           gate_mask: pd.Series | None, label: str) -> dict:
    """Buy at close[t], sell at open[t+1] — the famous overnight-drift
    anomaly. Computed for t in [0, i_va-2] (train+val only, test sealed).
    Reports gross mean %, a cost-haircut net mean (one round_trip_bps()
    charge per event — an honest, if optimistic, single-lot approximation),
    a one-sample t-stat, and the win rate. `gate_mask` (aligned to day t,
    i.e. the day whose CLOSE starts the overnight leg) restricts to a
    regime subset when given."""
    closes = d["close"].to_numpy()
    opens = d["open"].to_numpy()
    on_ret = (opens[1:i_va] / closes[0:i_va - 1] - 1) * 100
    if gate_mask is not None:
        g = gate_mask.to_numpy()[0:i_va - 1]
        on_ret = on_ret[g]
    n = len(on_ret)
    if n < 2:
        return {"label": label, "n": n, "mean_gross_pct": np.nan,
                "mean_net_pct": np.nan, "tstat": np.nan, "win_pct": np.nan}
    mean = float(np.mean(on_ret))
    std = float(np.std(on_ret, ddof=1))
    tstat = mean / (std / np.sqrt(n)) if std > 0 else np.nan
    cost_pct = costs.round_trip_bps() / 100
    return {"label": label, "n": n, "mean_gross_pct": mean,
            "mean_net_pct": mean - cost_pct, "tstat": tstat,
            "win_pct": float((on_ret > 0).mean() * 100)}


def family2b_overnight_drift(frames, meta):
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_va = m["i_va"]
        close = d["close"]
        sma200 = sma(close, 200)
        vol_pct = realized_vol_pct(d)
        gates = [
            ("unconditioned", None),
            ("trend-above-sma200", (close > sma200)),
            ("trend-below-sma200", ~(close > sma200)),
            ("vol-calm(<50pct)", (vol_pct < 50)),
            ("vol-crash(>80pct)", (vol_pct > 80)),
        ]
        for gname, gmask in gates:
            rows.append(overnight_drift_stats(d, i_va, costs, gmask, f"{tag} {gname}"))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2c — first-hour range break (1h SPY only)
# ---------------------------------------------------------------------------

def family2c_firsthour_breakout(frames, meta):
    """Break of the 9:30-10:30 ET opening range (the RTH-only 1h frame's
    FIRST bar of each trading day IS that window — see module docstring),
    exit by session-safety cap (6 bars, ~the rest of RTH), both
    unconditioned (trade every breakout) and with-trend (daily SMA200
    side, known as of the PRIOR day's close only — no lookahead into a
    still-forming day). SPY 1h only, per the task's literal spec."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1h"].reset_index(drop=True)
    d1d = frames[tag]["1d"]
    m = meta[tag]["1h"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]

    ts_et = d["timestamp"].dt.tz_convert("America/New_York")
    day = ts_et.dt.date
    tmp = pd.DataFrame({"day": day, "time": ts_et, "high": d["high"], "low": d["low"]})
    first_idx = tmp.groupby("day")["time"].idxmin()
    is_first = pd.Series(tmp.index.isin(first_idx.values), index=tmp.index)
    range_high_map = tmp.loc[is_first].set_index("day")["high"]
    range_low_map = tmp.loc[is_first].set_index("day")["low"]
    win_high = tmp["day"].map(range_high_map)
    win_low = tmp["day"].map(range_low_map)
    after_window = ~is_first

    enter_long_raw = (after_window & (d["close"] > win_high)).fillna(False)
    enter_short_raw = (after_window & (d["close"] < win_low)).fillna(False)

    daily_trend = (d1d["close"] > sma(d1d["close"], 200)).shift(1).fillna(False)
    d1d_date = d1d["timestamp"].dt.tz_convert("America/New_York").dt.date
    trend_map = pd.Series(daily_trend.to_numpy(), index=d1d_date.to_numpy())
    trend_map = trend_map[~trend_map.index.duplicated(keep="last")]
    trend_up = tmp["day"].map(trend_map).fillna(False)

    range_height_pct = (win_high - win_low) / win_low * 100
    med_range_train = float(range_height_pct.iloc[:i_tr].dropna().median())
    mh_bars = hours_to_bars(d, 6)

    for mode in ("unconditioned", "with-trend"):
        if mode == "unconditioned":
            el, es = enter_long_raw, enter_short_raw
        else:
            el, es = enter_long_raw & trend_up, enter_short_raw & (~trend_up)
        flat = pd.Series(False, index=d.index)
        for direction, elx, esx in (("long", el, flat), ("short", flat, es), ("both", el, es)):
            sig = day_trade_signal(d, elx, esx, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_range_train
                stop_pct = min(med_range_train, 3.0)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                cfg = f"{mode} {direction} tgt{tmult}xrange stop=rangeheight"
                rows.append(mk_row("2c-firsthour-break", cfg, tag, "1h", tr, va, stop_pct, target_pct))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — trend/regime backbone (daily, both instruments)
# ---------------------------------------------------------------------------

def family3_trend_regime(frames, meta):
    """SMA{100,200} regime membership (implemented as vol_gated_ma with
    fast=1 — a 1-bar SMA is just close itself — vs the slow SMA, i.e.
    'long while close > SMA(slow)', reusing the proven building block
    verbatim rather than writing a new regime primitive) and the classic
    50/200 golden cross. Each tested ungated and with the adaptive vol
    gate (imported). Both SPY and ES=F."""
    rows = []
    shapes = [(1, 100, "sma100-regime"), (1, 200, "sma200-regime"), (50, 200, "goldencross")]
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        for fast, slow, name in shapes:
            for gate_mode in ("none", "adaptive"):
                if gate_mode == "none":
                    sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False)
                else:
                    gate, _ = adaptive_vol_gate(d, direction="above")
                    sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0, allow_short=False,
                                        entry_filter=gate)
                tr, va = score(d, sig, costs, i_tr, i_va)
                rows.append(mk_row("3-trend-regime", f"{name} gate={gate_mode}", tag, "1d", tr, va))
    return rows


def family3_buyhold_baseline(frames, meta):
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        sig = buy_and_hold(d)
        tr, va = score(d, sig, costs, i_tr, i_va)
        rows.append(mk_row("3-buyhold-baseline", "buy&hold", tag, "1d", tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — mean reversion vs momentum split by regime (the centerpiece)
# ---------------------------------------------------------------------------

def family4_regime_split(frames, meta):
    """The index's signature "different situations, different weapons"
    test: does RSI2 dip-buying (mean reversion) actually work best in
    calm uptrends and die in vol-spike/crash regimes, while a plain
    momentum-continuation shape does the opposite? Four regime cells
    (vol-percentile {<50 calm, >80 crash} x SMA200 side {above, below}),
    each tested with BOTH weapons and an optional ATR-scaled protective
    stop. SPY only (daily) — this is deliberately the most literal read
    of "the index," and running it on the younger ES=F series would bias
    the vol-percentile ranking's baseline."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1d"]
    m = meta[tag]["1d"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    med_atr = m["med_atr"]
    close = d["close"]
    sma200 = sma(close, 200)
    r2 = rsi(close, 2)
    exit_cond = dipbuy_exit(d).fillna(False)
    vol_pct = realized_vol_pct(d)
    above = close > sma200
    cells = {
        "calm+above": ((vol_pct < 50) & above).fillna(False),
        "calm+below": ((vol_pct < 50) & ~above).fillna(False),
        "crash+above": ((vol_pct > 80) & above).fillna(False),
        "crash+below": ((vol_pct > 80) & ~above).fillna(False),
    }
    stop_variants = [("none", None), ("1.0xATR", 1.0), ("1.5xATR", 1.5)]

    for cell_name, cm in cells.items():
        for th in (5, 10, 15):
            enter = ((r2 < th) & cm).fillna(False)
            for stop_name, stop_mult in stop_variants:
                stop_pct = None if stop_mult is None else stop_mult * med_atr
                sig = event_long(d, enter, exit_cond, 0)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                cfg = f"MR rsi2<{th} cell={cell_name} stop={stop_name}"
                BUILDER_REGISTRY[("4-regime-split", cfg, tag, "1d")] = sig
                rows.append(mk_row("4-regime-split", cfg, tag, "1d", tr, va, stop_pct, None,
                                    {"weapon": "mean-reversion", "cell": cell_name}))

    for cell_name, cm in cells.items():
        for lookback in (5, 10):
            mom_up = close > close.shift(lookback)
            enter = (mom_up & cm).fillna(False)
            exit_ = (~mom_up).fillna(False)
            for stop_name, stop_mult in stop_variants:
                stop_pct = None if stop_mult is None else stop_mult * med_atr
                sig = event_long(d, enter, exit_, 0)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
                cfg = f"MOM {lookback}d-continuation cell={cell_name} stop={stop_name}"
                BUILDER_REGISTRY[("4-regime-split", cfg, tag, "1d")] = sig
                rows.append(mk_row("4-regime-split", cfg, tag, "1d", tr, va, stop_pct, None,
                                    {"weapon": "momentum", "cell": cell_name}))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 5 — seasonality audit (report-only, SPY, 30y+, no strategy claims)
# ---------------------------------------------------------------------------

def _tstat(sub: pd.Series):
    n = len(sub)
    if n < 2:
        return np.nan
    std = float(sub.std(ddof=1))
    if std <= 0:
        return np.nan
    return float(sub.mean()) / (std / np.sqrt(n))


def family5_seasonality(frames, meta):
    tag = "SPY"
    d = frames[tag]["1d"]
    m = meta[tag]["1d"]
    i_va = m["i_va"]
    d_use = d.iloc[:i_va].reset_index(drop=True)
    ts_et = d_use["timestamp"].dt.tz_convert("America/New_York")
    ret = d_use["close"].pct_change() * 100

    dow_rows = []
    dow_names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}
    for wd, name in dow_names.items():
        sub = ret[ts_et.dt.dayofweek == wd].dropna()
        dow_rows.append({"bucket": name, "n": len(sub), "mean_ret_pct": float(sub.mean()),
                          "tstat": _tstat(sub)})

    month = ts_et.dt.to_period("M")
    is_month_end = (month != month.shift(-1)).fillna(False)
    day_rank = d_use.groupby(month.to_numpy()).cumcount()
    tom_flag = is_month_end | (day_rank < 3)
    tom_ret = ret[tom_flag].dropna()
    rest_ret = ret[~tom_flag].dropna()
    tom_rows = []
    for name, sub in (("turn-of-month", tom_ret), ("rest-of-month", rest_ret)):
        tom_rows.append({"bucket": name, "n": len(sub), "mean_ret_pct": float(sub.mean()),
                          "tstat": _tstat(sub)})
    return dow_rows, tom_rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 78)
    print("ROUND 60 — THE S&P SYSTEM: index-native families for SPY / ES=F")
    print("=" * 78)
    print("NOTE: no demo venue exists for the real S&P 500. BloFin's 'SPX-USDT' is")
    print("the SPX6900 MEMECOIN, never touched here. Pure knowledge-banking research.")

    frames = load_all()

    meta = {tag: {} for tag in ("SPY", "ES")}
    print("\nSpans + split points + median TRAIN ATR% + gap structure "
          "(SPY RTH-only vs ES=F near-24h, side by side):")
    for tag in ("SPY", "ES"):
        for tf in ("1d", "1h"):
            d = frames[tag][tf]
            n, i_tr, i_va = split_points(d)
            atr_pct = atr(d, 14) / d["close"] * 100
            med_atr_train = float(atr_pct.iloc[:i_tr].median())
            meta[tag][tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
            gaps = gap_stats_summary(d, [0.3, 0.5, 0.8, 1.0, med_atr_train])
            print(f"  {tag:4s} {tf}: {n:6d} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
                  f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
                  f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
                  f"med train ATR%={med_atr_train:.3f}% | gap>thresh: {gaps}")

    print("\nRunning FAMILY 1 (index dip-buying)...")
    rows = family1_dipbuying(frames, meta)
    print(f"  {len(rows)} configs")
    print("Running FAMILY 2a (gap-fill)...")
    rows += family2a_gapfill(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 2c (first-hour range break, SPY 1h)...")
    rows += family2c_firsthour_breakout(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 3 (trend/regime backbone)...")
    rows += family3_trend_regime(frames, meta)
    rows += family3_buyhold_baseline(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 4 (regime split: mean reversion vs momentum)...")
    rows += family4_regime_split(frames, meta)
    print(f"  {len(rows)} cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} strategy configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nFull results table (train+val, full costs, test sealed):")
    cols = ["family", "config", "symbol", "tf", "stop%", "target%", "tr_n", "tr_exp",
            "tr_win%", "tr_dd%", "va_n", "va_exp", "va_win%", "va_dd%", "verdict"]
    with pd.option_context("display.max_rows", None):
        print(df.sort_values(["family", "symbol", "tr_exp"], ascending=[True, True, False])[cols]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("FAMILY 2b — OVERNIGHT DRIFT AUDIT (report-only, buy close / sell next open)")
    print("=" * 78)
    audit_rows = family2b_overnight_drift(frames, meta)
    audit_df = pd.DataFrame(audit_rows)
    print(audit_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\n" + "=" * 78)
    print("FAMILY 5 — SEASONALITY AUDIT (report-only, SPY daily, 30y+, test sealed)")
    print("=" * 78)
    dow_rows, tom_rows = family5_seasonality(frames, meta)
    dow_df, tom_df = pd.DataFrame(dow_rows), pd.DataFrame(tom_rows)
    print("Day-of-week:")
    print(dow_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))
    print("Turn-of-month:")
    print(tom_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\n" + "=" * 78)
    print("GAP-HONESTY CORRECTION — FAMILY 1 / FAMILY 4 SURVIVOR + INSUFFICIENT-SAMPLE")
    print("configs that carry a protective stop (daily bars can gap through them)")
    print("=" * 78)
    stop_candidates = pd.concat([survivors, near])
    stop_candidates = stop_candidates[
        stop_candidates["family"].isin(["1-dipbuying", "4-regime-split"])
        & stop_candidates["stop%"].notna()
    ]
    if len(stop_candidates) == 0:
        print("  (no stop-bearing survivor/near-miss configs to check)")
    for _, row in stop_candidates.iterrows():
        family, cfg, tag, tf = row["family"], row["config"], row["symbol"], row["tf"]
        key = (family, cfg, tag, tf)
        sig = BUILDER_REGISTRY.get(key)
        if sig is None:
            continue
        d = frames[tag][tf]
        m = meta[tag][tf]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        stop_pct = row["stop%"]
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct)
        d_tr = d.iloc[:i_tr].reset_index(drop=True)
        d_va = d.iloc[i_tr:i_va].reset_index(drop=True)
        gap_tr, n_tr = gap_honesty_correction(d_tr, tr.trades, stop_pct, costs)
        gap_va, n_va = gap_honesty_correction(d_va, va.trades, stop_pct, costs)
        tr_adj = tr.expectancy + (gap_tr / len(tr.trades) if tr.trades else 0.0)
        va_adj = va.expectancy + (gap_va / len(va.trades) if va.trades else 0.0)
        print(f"  [{family}] {cfg} ({tag}) stop={stop_pct:.3f}% | "
              f"TRAIN raw={tr.expectancy:+.3f} gapadj={tr_adj:+.3f} gapped={n_tr}/{len(tr.trades)} | "
              f"VAL raw={va.expectancy:+.3f} gapadj={va_adj:+.3f} gapped={n_va}/{len(va.trades)}")

    print("\nDone. No sealed-test window was ever sliced or scored above.")
    return df, audit_df, dow_df, tom_df


if __name__ == "__main__":
    main()
