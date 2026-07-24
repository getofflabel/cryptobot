"""
step78_oil_playbook.py — Round 78: AN OIL PLAYBOOK FROM ZERO.

HONEST STATE GOING IN: we have ZERO strategies validated on oil itself.
What runs on oil in the live paper engine (per step70_replay.py's own
`[transfer-assumption]` tag) is donchian20 + structure-trailing-exit
(gold_book.py's shape, proven on GOLD) and an RSI2 dip-buy (proven on the
S&P, step70's rsi2_dipbuy_sealed). Neither has ever been independently
gauntleted on CL=F/BZ=F/USO's own data. This round closes that gap from
zero: six families built around oil's ACTUAL character (inventory cycle,
spike-and-reversion, the Brent-WTI spread, session structure), gauntleted
honestly, with an explicit verdict on whether the two strategies we are
CURRENTLY running on oil hold up.

RESEARCH ONLY. No commits, no live orders. Writes ONLY:
  step78_oil_playbook.py (this file), step78_results.md (hand-composed
  from this script's stdout, same convention as step48/step74),
  step78_full_table.csv (every config, nothing omitted),
  data_oil_<SYM>_<TF>.parquet (CL/BZ/USO caches).
Does NOT touch step75_*/step76_*/step77_* or the dashboard (concurrent
agents own those).

DATA: yfinance.
  CL=F (WTI)  1d period="max", 1h period="730d" (yfinance's hard cap on
              hourly bars — stated plainly, not worked around).
  BZ=F (Brent) same two pulls — the Brent twin for every WTI family.
  USO (ETF)   1d period="max" only — the instrument a retail account can
              actually hold; no liquid USO options/futures-style 1h edge
              is claimed, so no 1h pull for it.
  Sub-hourly (15m/5m) is NOT fetched: yfinance caps intraday-below-1h
  history at ~60 calendar days, far too shallow to clear this round's
  30-train/8-val floors on anything but the most frequent triggers. State
  spans honestly (printed per-dataset below) rather than faking finer
  resolution we don't have.
  Cached as data_oil_<TAG>_<TF>.parquet, TAG in {CL, BZ, USO}.

COSTS (step48_tradfi_trend.py's TradFi convention, unchanged):
  Futures (CL=F, BZ=F): 0.5bp fee + 0.5bp slippage each side, 0 half
                         spread -> round_trip_bps() = 2bps.
  ETF (USO):             1bp fee + 1bp slippage each side, 0 half spread
                         -> round_trip_bps() = 4bps.
  funding_bps_8h = 0.0 explicitly on every CostModel (no perpetual-funding
  analogue exists on dated futures or ETFs — see step48's docstring for
  why this must be set, not left at the engine's crypto-flavored default).

REUSE / ATTRIBUTION (imported, not reimplemented):
  step41_shorts.py: bar_hours, days_to_bars, hours_to_bars, split_points,
    adaptive_vol_gate, confirmed_swings, last_n_confirmed — unmodified.
  step56_smc_toolkit.py: bos_chain — unmodified.
  step73_video.py: body_frame, engulf2_events, merge_event_recency_with_
    value, retest_confirm_entries, breakout_entries, day_trade_signal,
    resample_ohlc — unmodified. (This is the toolkit round 74 also reused
    to build its structure->retest->engulf pipeline; family 4a here is
    that same pipeline pointed at oil 1h instead of 20yr FX dailies.)
  backtest.py: CostModel, run_backtest — unmodified (rule 1/2/3 engine).
  strategy.py: atr, rsi, event_short — unmodified.

GAUNTLET: chronological 60/20/20 per dataset (split_points). Select by
TRAIN expectancy>0 AND VAL expectancy>0, floors tr_n>=30 / va_n>=8 ->
SURVIVOR. The sealed 20% test window is NEVER sliced or scored anywhere
in this script — score() only ever touches [0:i_tr] and [i_tr:i_va].
Every row also carries tr_per_yr (trades/year across train+val); the
task's own bar is explicit: under 10/yr = too rare to be a playbook
piece, flagged CADENCE=TOO-RARE regardless of expectancy.

SIX FAMILIES (built around oil's own character, not ported blind):
  1. TREND — donchian(20/55) breakout + a REAL structure-trailing exit
     (ratcheting confirmed-swing floor/ceiling, k=5 — the literal shape
     gold_book.py validated on gold and step70 transferred to oil on
     faith), tested BOTH directions (oil has real bear markets, gold
     mostly doesn't) with a vol-regime gate axis (family 6 folded in).
  2. MEAN REVERSION AFTER SPIKES — z-score(20) and RSI2 extremes, both
     directions, gated by trend (none/with-trend/counter-trend) and by
     volatility regime (none/high-vol/low-vol) — family 6 folded in here
     too, since 1&2 are where a vol gate is mechanically meaningful.
  3. INVENTORY-CYCLE / DAY-OF-WEEK — (a) which weekday has a tradeable
     next-session drift on daily bars; (b) the EIA-Wednesday 10:30am ET
     release-hour continuation/reversal on 1h bars, oil's closest
     analogue to the validated crypto news edge; (c) the Tuesday
     4:30pm ET API-report hour, same test.
  4. STRUCTURE, 1h — (a) break-of-structure + retest + engulf (step56/
     step73's toolkit, literally reused, pointed at oil); (b) sweep-and-
     reclaim of the PRIOR CALENDAR DAY's high/low (new: oil's session
     structure is real, unlike a 24/7 crypto tape).
  5. THE BRENT-WTI SPREAD — (a) spread-percentile reversion tested as an
     outright CL directional bet (stated single-leg approximation of a
     true dollar-neutral pairs trade — this engine trades one instrument
     at a time); (b) a regime breakdown tagging family-1/2's flagship
     CL-daily configs by spread-percentile regime at entry (does the
     stress-era spread predict which regime pays).
  6. VOLATILITY REGIME — folded into families 1 & 2 as an explicit gate
     axis (adaptive_vol_gate: current ATR% vs its own trailing 365-day
     median) rather than bolted separately onto every family — it is
     mechanically meaningful for continuous trend/mean-reversion entries
     and redundant on 3/4, which are already vol-spike-shaped events by
     construction (release hours, sweeps).
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from step41_shorts import (
    adaptive_vol_gate,
    bar_hours,
    confirmed_swings,
    days_to_bars,
    hours_to_bars,
    split_points,
)
from step56_smc_toolkit import bos_chain
from step73_video import (
    body_frame,
    breakout_entries,
    day_trade_signal,
    engulf2_events,
    merge_event_recency_with_value,
    retest_confirm_entries,
)
from strategy import atr, event_short, rsi

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
MIN_TRADES_PER_YEAR = 10.0
STOP_CAP_PCT = 10.0
STOP_FLOOR_PCT = 0.25

YF_TICKERS = {"CL": "CL=F", "BZ": "BZ=F", "USO": "USO"}
ASSET_CLASS = {"CL": "future", "BZ": "future", "USO": "etf"}
MARKET_NAME = {"CL": "WTI (CL=F)", "BZ": "Brent (BZ=F)", "USO": "USO (ETF)"}


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_and_save(tag: str, symbol: str, interval: str, period: str,
                    use_cache: bool = True) -> pd.DataFrame:
    tf = "1d" if interval == "1d" else "1h"
    fname = f"data_oil_{tag}_{tf}.parquet"
    if use_cache:
        try:
            cached = pd.read_parquet(fname)
            print(f"  cached {fname}: {len(cached)} bars, "
                  f"{cached['timestamp'].iloc[0]:%Y-%m-%d} -> {cached['timestamp'].iloc[-1]:%Y-%m-%d}")
            return cached
        except FileNotFoundError:
            pass

    raw = None
    for attempt in range(3):
        try:
            raw = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
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
        "open": df["Open"].astype(float),
        "high": df["High"].astype(float),
        "low": df["Low"].astype(float),
        "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    out.to_parquet(fname)
    print(f"  saved {fname}: {len(out)} bars, "
          f"{out['timestamp'].iloc[0]:%Y-%m-%d} -> {out['timestamp'].iloc[-1]:%Y-%m-%d}")
    return out


def load_all_data() -> dict:
    frames = {"CL": {}, "BZ": {}, "USO": {}}
    print("Fetching DAILY (max history)...")
    for tag, sym in YF_TICKERS.items():
        frames[tag]["1d"] = fetch_and_save(tag, sym, "1d", "max")
    print("Fetching HOURLY (~730d, yfinance's hard cap for 1h bars; CL/BZ only) ...")
    for tag in ("CL", "BZ"):
        frames[tag]["1h"] = fetch_and_save(tag, YF_TICKERS[tag], "1h", "730d")
    return frames


# ---------------------------------------------------------------------------
# shared gauntlet plumbing
# ---------------------------------------------------------------------------

def costs_for(tag: str) -> CostModel:
    if ASSET_CLASS[tag] == "etf":
        return CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                          slippage_bps=1.0, funding_bps_8h=0.0)
    return CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                      slippage_bps=0.5, funding_bps_8h=0.0)


def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None):
    def run(lo, hi):
        return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                             sig.iloc[lo:hi].reset_index(drop=True),
                             costs=costs, execution="taker",
                             stop_pct=stop_pct, target_pct=target_pct)
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va) -> str:
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0 and tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
        return "SURVIVOR"
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def trades_per_year(d, tr, va, i_va) -> float:
    n_trades = len(tr.trades) + len(va.trades)
    span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return n_trades / span_days * 365.25 if span_days > 0 else float("nan")


def cadence_flag(tpy: float) -> str:
    if np.isnan(tpy):
        return "N/A"
    return "OK" if tpy >= MIN_TRADES_PER_YEAR else f"TOO-RARE({tpy:.1f}/yr)"


def mk_row(family, config, tag, tf, d, i_va, tr, va, extra=None):
    tpy = trades_per_year(d, tr, va, i_va)
    row = {
        "family": family, "config": config, "symbol": tag,
        "market": MARKET_NAME[tag], "tf": tf,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
        "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
        "va_ret%": va.total_return_pct,
        "tr_per_yr": tpy, "cadence": cadence_flag(tpy),
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def build_meta(frames: dict) -> dict:
    meta = {tag: {} for tag in frames}
    print("\nSpans + split points + median TRAIN ATR% (train window only — "
          "sealed test window's own stats never computed):")
    for tag, tfs in frames.items():
        for tf, d in tfs.items():
            n, i_tr, i_va = split_points(d)
            atr_pct = atr(d, 14) / d["close"] * 100
            med_atr_train = float(atr_pct.iloc[:i_tr].median())
            meta[tag][tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
            print(f"  {tag:4s} {tf}: {n:6d} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
                  f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
                  f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
                  f"med train ATR%={med_atr_train:.2f}%")
    return meta


# ===========================================================================
# FAMILY 1 — TREND: donchian breakout + real structure-trailing exit
# ===========================================================================

def structure_trail_signal(d, entry_n, k_swing, direction, crash_sl_pct=0.18):
    """Donchian(entry_n) breakout entry; exit = close breaks back past a
    RATCHETING floor/ceiling built from confirmed_swings(k_swing) — the
    literal shape gold_book.py / step70_replay's donchian_structure_trail
    validated on gold, reimplemented as a boolean position series so it
    runs through the SAME run_backtest signal engine (real CostModel,
    next-bar-open fill, no lookahead) as every other family this round —
    unlike step70's separate trade-list bookkeeping. direction='long' or
    'short'; each direction is its own standalone config (not combined
    into one bidirectional position), so oil's short side is judged on
    its own merits rather than folded into a mirror-image net signal."""
    close = d["close"].to_numpy()
    high = d["high"].to_numpy()
    low = d["low"].to_numpy()
    n = len(d)
    sh_price, sl_price = confirmed_swings(d, k_swing)
    sh_arr = sh_price.to_numpy()
    sl_arr = sl_price.to_numpy()

    if direction == "long":
        roll = d["high"].rolling(entry_n).max().shift(1).to_numpy()
        breakout = (~np.isnan(roll)) & (close > roll)
    else:
        roll = d["low"].rolling(entry_n).min().shift(1).to_numpy()
        breakout = (~np.isnan(roll)) & (close < roll)

    pos = np.zeros(n)
    in_pos = False
    level = None
    for i in range(n):
        if not in_pos:
            if breakout[i]:
                in_pos = True
                entry_price = close[i]
                if direction == "long":
                    seen = sl_arr[:i + 1]
                    valid = seen[~np.isnan(seen) & (seen < entry_price)]
                    level = float(valid[-1]) if len(valid) else entry_price * (1 - crash_sl_pct)
                else:
                    seen = sh_arr[:i + 1]
                    valid = seen[~np.isnan(seen) & (seen > entry_price)]
                    level = float(valid[-1]) if len(valid) else entry_price * (1 + crash_sl_pct)
                pos[i] = 1.0 if direction == "long" else -1.0
            continue
        if direction == "long":
            cur = sl_arr[i]
            if not np.isnan(cur) and cur > level:
                level = float(cur)
            if low[i] <= level:
                in_pos = False
                pos[i] = 0.0
            else:
                pos[i] = 1.0
        else:
            cur = sh_arr[i]
            if not np.isnan(cur) and cur < level:
                level = float(cur)
            if high[i] >= level:
                in_pos = False
                pos[i] = 0.0
            else:
                pos[i] = -1.0
    return pd.Series(pos, index=d.index)


def apply_gate(sig, gate_bool):
    """Zero the signal out on bars the gate disallows, WITHOUT chopping an
    already-open position mid-trade (the gate only blocks NEW entries —
    matches vol_gated_ma's own entry_filter convention elsewhere in this
    repo, not a mid-trade force-flat)."""
    g = gate_bool.fillna(False).to_numpy()
    s = sig.to_numpy(dtype=float)
    out = np.zeros(len(s))
    in_pos = False
    for i in range(len(s)):
        if not in_pos:
            if s[i] != 0.0 and g[i]:
                in_pos = True
                out[i] = s[i]
            else:
                out[i] = 0.0
        else:
            if s[i] == 0.0:
                in_pos = False
                out[i] = 0.0
            else:
                out[i] = s[i]
    return pd.Series(out, index=sig.index)


FAM1_DATASETS = [("CL", "1d"), ("CL", "1h"), ("BZ", "1d"), ("BZ", "1h"), ("USO", "1d")]


def family1_trend(frames, meta):
    rows = []
    for tag, tf in FAM1_DATASETS:
        d = frames[tag][tf]
        m = meta[tag][tf]
        costs = costs_for(tag)
        gate_hi, _ = adaptive_vol_gate(d, direction="above")
        gate_lo, _ = adaptive_vol_gate(d, direction="below")
        for entry_n in (20, 55):
            base_long = structure_trail_signal(d, entry_n, 5, "long")
            base_short = structure_trail_signal(d, entry_n, 5, "short")
            for direction, base in (("long", base_long), ("short", base_short)):
                for gate_name, gate in (("ungated", None), ("high-vol", gate_hi), ("low-vol", gate_lo)):
                    sig = base if gate is None else apply_gate(base, gate)
                    tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                    cfg = f"donchian{entry_n} k5-structtrail {direction} gate={gate_name}"
                    rows.append(mk_row("1-trend", cfg, tag, tf, d, m["i_va"], tr, va,
                                        extra={"vol_gate": gate_name, "direction": direction}))
    return rows


# ===========================================================================
# FAMILY 2 — MEAN REVERSION AFTER SPIKES
# ===========================================================================

def event_long(d, enter, exit_, max_hold=0):
    e = enter.fillna(False).to_numpy(dtype=bool)
    x = exit_.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if e[i]:
                pos, held = 1.0, 0
        else:
            held += 1
            if x[i] or (max_hold and held >= max_hold):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def zscore(close, window=20):
    m = close.rolling(window).mean()
    s = close.rolling(window).std()
    return (close - m) / s


def trend_filter(d, mode):
    """none: no restriction. with-trend: long only if close>SMA100 (dip
    IN an uptrend), short only if close<SMA100 (pop-fade IN a downtrend).
    counter-trend: the opposite pairing (fading extremes AGAINST the
    prevailing trend — the 'catch the falling knife' variant)."""
    sma = d["close"].rolling(100).mean()
    above = (d["close"] > sma).fillna(False)
    below = (d["close"] < sma).fillna(False)
    if mode == "none":
        return pd.Series(True, index=d.index), pd.Series(True, index=d.index)
    if mode == "with-trend":
        return above, below
    if mode == "counter-trend":
        return below, above
    raise ValueError(mode)


def mr_signal(d, trigger, direction, thresh, trend_mode, vol_gate_name, gate_hi, gate_lo,
              max_hold_bars, exit_sma_n=5):
    close = d["close"]
    exit_sma = close.rolling(exit_sma_n).mean()
    long_trend_ok, short_trend_ok = trend_filter(d, trend_mode)

    if trigger == "zscore":
        z = zscore(close, 20)
        enter_long = (z < -thresh)
        enter_short = (z > thresh)
    else:  # rsi2
        r2 = rsi(close, 2)
        enter_long = (r2 < thresh)
        enter_short = (r2 > (100 - thresh))

    if vol_gate_name == "high-vol":
        enter_long = enter_long & gate_hi.fillna(False)
        enter_short = enter_short & gate_hi.fillna(False)
    elif vol_gate_name == "low-vol":
        enter_long = enter_long & gate_lo.fillna(False)
        enter_short = enter_short & gate_lo.fillna(False)

    if direction == "long":
        enter = (enter_long & long_trend_ok).fillna(False)
        exit_ = (close > exit_sma).fillna(False)
        return event_long(d, enter, exit_, max_hold_bars)
    else:
        enter = (enter_short & short_trend_ok).fillna(False)
        exit_ = (close < exit_sma).fillna(False)
        return event_short(d, enter, exit_, max_hold_bars)


FAM2_DATASETS = [("CL", "1d"), ("CL", "1h"), ("BZ", "1d"), ("BZ", "1h"), ("USO", "1d")]


def family2_meanrev(frames, meta):
    rows = []
    for tag, tf in FAM2_DATASETS:
        d = frames[tag][tf]
        m = meta[tag][tf]
        costs = costs_for(tag)
        gate_hi, _ = adaptive_vol_gate(d, direction="above")
        gate_lo, _ = adaptive_vol_gate(d, direction="below")
        max_hold = days_to_bars(d, 10) if tf == "1d" else hours_to_bars(d, 48)

        for trigger, thresh in (("zscore", 2.0), ("rsi2", 5.0)):
            for direction in ("long", "short"):
                for trend_mode in ("none", "with-trend"):
                    for vol_gate_name in ("none", "high-vol", "low-vol"):
                        sig = mr_signal(d, trigger, direction, thresh, trend_mode,
                                         vol_gate_name, gate_hi, gate_lo, max_hold)
                        tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                        cfg = (f"{trigger}>{thresh:.0f} {direction} trend={trend_mode} "
                               f"vol={vol_gate_name}")
                        rows.append(mk_row("2-meanrev", cfg, tag, tf, d, m["i_va"], tr, va,
                                            extra={"vol_gate": vol_gate_name, "trend_gate": trend_mode,
                                                   "direction": direction}))
        # counter-trend ablation at a fixed representative point (vol gate off)
        for trigger, thresh in (("zscore", 2.0), ("rsi2", 5.0)):
            for direction in ("long", "short"):
                sig = mr_signal(d, trigger, direction, thresh, "counter-trend",
                                 "none", gate_hi, gate_lo, max_hold)
                tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                cfg = f"{trigger}>{thresh:.0f} {direction} trend=counter-trend vol=none"
                rows.append(mk_row("2-meanrev", cfg, tag, tf, d, m["i_va"], tr, va,
                                    extra={"vol_gate": "none", "trend_gate": "counter-trend",
                                           "direction": direction}))
    return rows


# ===========================================================================
# FAMILY 3 — INVENTORY-CYCLE / DAY-OF-WEEK
# ===========================================================================

def weekday_hold_signal(d, weekday_name, direction):
    """signal[i]=+-1 on every bar whose weekday==weekday_name -> the
    engine fills at the NEXT bar's open (the following session, i.e. the
    day right after weekday_name — since oil doesn't trade weekends, the
    'day after Tuesday' bar IS Wednesday) and flips flat on the bar after
    that (weekday_name's own bar carries signal 0), so the position covers
    exactly one full session: [next-session open -> session-after open]."""
    wd = pd.DatetimeIndex(d["timestamp"]).tz_convert("America/New_York").day_name()
    mask = (wd == weekday_name)
    val = 1.0 if direction == "long" else -1.0
    return pd.Series(np.where(mask, val, 0.0), index=d.index)


def release_hour_mask(d, weekday_name, hour_et):
    """Bar covering the given ET hour on the given weekday — the 1h bar
    starting at hour_et:00 ET spans hour_et:00-hour_et+1:00, which
    contains a :30 release. KNOWN SIMPLIFICATION: does not shift EIA's
    Wed->Thu holiday-week move; stated here and in the results writeup,
    not silently absorbed."""
    et = pd.DatetimeIndex(d["timestamp"]).tz_convert("America/New_York")
    return pd.Series((et.day_name() == weekday_name) & (et.hour == hour_et), index=d.index)


def release_continuation_signal(d, mask, hold_bars, mode):
    """On the release-hour bar's own return sign, go WITH it (mode=
    continuation) or AGAINST it (mode=reversal) starting the NEXT bar
    (engine's own next-open fill), held for hold_bars then flat."""
    ret = (d["close"] / d["open"] - 1)
    direction = np.sign(ret).to_numpy()
    if mode == "reversal":
        direction = -direction
    m = mask.to_numpy()
    n = len(d)
    out = np.zeros(n)
    pos, held = 0.0, 0
    for i in range(n):
        if pos == 0.0:
            if m[i] and direction[i] != 0:
                pos, held = direction[i], 0
        else:
            held += 1
            if held >= hold_bars:
                pos = 0.0
        out[i] = pos
    return pd.Series(out, index=d.index)


def family3_inventory(frames, meta):
    rows = []
    # 3a — day-of-week next-session drift, daily
    for tag in ("CL", "BZ"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = costs_for(tag)
        for weekday in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
            for direction in ("long", "short"):
                sig = weekday_hold_signal(d, weekday, direction)
                tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                cfg = f"next-session-after-{weekday} {direction}"
                rows.append(mk_row("3a-dow", cfg, tag, "1d", d, m["i_va"], tr, va))

    # 3b — EIA Wednesday 10:30am ET + API Tuesday 4:30pm ET release-hour reaction, 1h
    reports = [("EIA-Wed10:30ET", "Wednesday", 10), ("API-Tue16:30ET", "Tuesday", 16)]
    for tag in ("CL", "BZ"):
        d = frames[tag]["1h"]
        m = meta[tag]["1h"]
        costs = costs_for(tag)
        for report_name, weekday, hour in reports:
            mask = release_hour_mask(d, weekday, hour)
            n_release_bars = int(mask.sum())
            for mode in ("continuation", "reversal"):
                for hold_bars in (1, 2, 4):
                    sig = release_continuation_signal(d, mask, hold_bars, mode)
                    tr, va = score(d, sig, costs, m["i_tr"], m["i_va"])
                    cfg = f"{report_name} {mode} hold{hold_bars}h (n_release_bars={n_release_bars})"
                    rows.append(mk_row("3b-release-hour", cfg, tag, "1h", d, m["i_va"], tr, va))
    return rows


# ===========================================================================
# FAMILY 4 — STRUCTURE, 1h
# ===========================================================================

def build_ctx(d, k):
    return bos_chain(body_frame(d), k)


def armed_and_touch(d, ctx, mode, window_bars, tol_pct):
    bh = bar_hours(d)
    EVENT_LONG = {"reversal": ctx["choch_long"], "continuation": ctx["cont_long"], "both": ctx["bos_up"]}
    EVENT_SHORT = {"reversal": ctx["choch_short"], "continuation": ctx["cont_short"], "both": ctx["bos_down"]}
    armed_long, level_long = merge_event_recency_with_value(
        d["timestamp"], d["timestamp"], EVENT_LONG[mode], ctx["lsh"], bh, window_bars, bh)
    armed_short, level_short = merge_event_recency_with_value(
        d["timestamp"], d["timestamp"], EVENT_SHORT[mode], ctx["lsl"], bh, window_bars, bh)
    close = d["close"]
    touch_long = (armed_long & ((close - level_long).abs() / level_long * 100 <= tol_pct)).fillna(False)
    touch_short = (armed_short & ((close - level_short).abs() / level_short * 100 <= tol_pct)).fillna(False)
    return armed_long, armed_short, touch_long, touch_short


def retest_touch_entries(armed_long, armed_short, touch_long, touch_short):
    n = len(armed_long)
    al, as_ = armed_long.to_numpy(), armed_short.to_numpy()
    tl, ts = touch_long.to_numpy(), touch_short.to_numpy()
    entry_long = np.zeros(n, dtype=bool)
    entry_short = np.zeros(n, dtype=bool)
    touched_l = touched_s = False
    for i in range(n):
        if al[i]:
            if not touched_l and tl[i]:
                entry_long[i] = True
                touched_l = True
        else:
            touched_l = False
        if as_[i]:
            if not touched_s and ts[i]:
                entry_short[i] = True
                touched_s = True
        else:
            touched_s = False
    idx = armed_long.index
    return pd.Series(entry_long, index=idx), pd.Series(entry_short, index=idx)


def stop_distance_pct_body(d_body, k, entry_long, entry_short):
    sh, sl = confirmed_swings(d_body, k)
    lsh, lsl = sh.ffill(), sl.ffill()
    close = d_body["close"]
    dist_short = ((lsh - close) / close * 100).where(entry_short.to_numpy())
    dist_long = ((close - lsl) / close * 100).where(entry_long.to_numpy())
    return dist_long, dist_short


def train_median_stop(entry_mask, distance_pct, i_tr, cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    mask = entry_mask.iloc[:i_tr].fillna(False)
    vals = distance_pct.iloc[:i_tr][mask.to_numpy()].dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(min(max(vals.median(), floor), cap))


TOL_PCT_STRUCT = 0.35
K_STRUCT = 3
WINDOW_STRUCT = 10


def run_structure_config(d, i_tr, i_va, k, el, es, r_list, costs, tag, cfg_prefix, rows):
    entry_mask = (el | es)
    dist_long, dist_short = stop_distance_pct_body(body_frame(d), k, el, es)
    dist_combined = dist_long.where(el.to_numpy(), dist_short)
    stop_pct = train_median_stop(entry_mask, dist_combined, i_tr)
    if stop_pct is None:
        return
    mh_bars = hours_to_bars(d, 72)  # 72h max hold on 1h structure trades — stated, not swept
    for rmult in r_list:
        target_pct = round(stop_pct * rmult, 4)
        sig = day_trade_signal(d, el, es, mh_bars)
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        cfg = f"{cfg_prefix} stop={stop_pct:.2f}% R={rmult:.1f}"
        rows.append(mk_row("4a-structure-retest", cfg, tag, "1h", d, i_va, tr, va))


def prior_day_extremes(d):
    """Prior CALENDAR day's (ET) high/low, forward-visible only from the
    first bar of the NEXT day — real session structure, not a rolling
    lookback window."""
    et = pd.DatetimeIndex(d["timestamp"]).tz_convert("America/New_York")
    date = pd.Series(et.date, index=d.index)
    daily = pd.DataFrame({"_date": date, "high": d["high"], "low": d["low"]}) \
        .groupby("_date").agg(high=("high", "max"), low=("low", "min")).reset_index()
    daily["prior_high"] = daily["high"].shift(1)
    daily["prior_low"] = daily["low"].shift(1)
    merged = pd.DataFrame({"_date": date}).merge(
        daily[["_date", "prior_high", "prior_low"]], on="_date", how="left")
    return merged["prior_high"].reset_index(drop=True), merged["prior_low"].reset_index(drop=True)


def sweep_reclaim_entries(d, prior_high, prior_low):
    high, low, close = d["high"], d["low"], d["close"]
    sweep_long = (prior_low.notna() & (low < prior_low) & (close > prior_low)).fillna(False)
    sweep_short = (prior_high.notna() & (high > prior_high) & (close < prior_high)).fillna(False)
    return sweep_long, sweep_short


def family4_structure(frames, meta):
    rows = []
    # 4a — break of structure + retest + engulf (step56/step73 toolkit, reused)
    for tag in ("CL", "BZ"):
        d = frames[tag]["1h"]
        m = meta[tag]["1h"]
        costs = costs_for(tag)
        i_tr, i_va = m["i_tr"], m["i_va"]
        ctx = build_ctx(d, K_STRUCT)
        engulf_bull, engulf_bear = engulf2_events(d)
        for mode in ("reversal", "continuation", "both"):
            armed_long, armed_short, touch_long, touch_short = armed_and_touch(
                d, ctx, mode, WINDOW_STRUCT, TOL_PCT_STRUCT)
            el, es = retest_confirm_entries(armed_long, armed_short, touch_long, touch_short,
                                             engulf_bull, engulf_bear)
            run_structure_config(d, i_tr, i_va, K_STRUCT, el, es, (2.0, 3.0, 4.0), costs, tag,
                                  f"BOS+retest+engulf mode={mode} k={K_STRUCT} w={WINDOW_STRUCT}", rows)
        # ablations at mode=both
        armed_long, armed_short, touch_long, touch_short = armed_and_touch(
            d, ctx, "both", WINDOW_STRUCT, TOL_PCT_STRUCT)
        el, es = retest_touch_entries(armed_long, armed_short, touch_long, touch_short)
        run_structure_config(d, i_tr, i_va, K_STRUCT, el, es, (2.0, 3.0, 4.0), costs, tag,
                              "ablation-no_engulf mode=both", rows)
        el, es = breakout_entries(armed_long, armed_short)
        run_structure_config(d, i_tr, i_va, K_STRUCT, el, es, (2.0, 3.0, 4.0), costs, tag,
                              "ablation-breakout(no_retest) mode=both", rows)

    # 4b — sweep-and-reclaim of prior calendar day's high/low
    for tag in ("CL", "BZ"):
        d = frames[tag]["1h"]
        m = meta[tag]["1h"]
        costs = costs_for(tag)
        i_tr, i_va = m["i_tr"], m["i_va"]
        prior_high, prior_low = prior_day_extremes(d)
        el, es = sweep_reclaim_entries(d, prior_high, prior_low)
        dist_long = ((d["close"] - prior_low) / d["close"] * 100).where(el.to_numpy())
        dist_short = ((prior_high - d["close"]) / d["close"] * 100).where(es.to_numpy())
        dist_combined = dist_long.where(el.to_numpy(), dist_short)
        entry_mask = (el | es)
        stop_pct = train_median_stop(entry_mask, dist_combined, i_tr)
        if stop_pct is None:
            continue
        for max_hold_h in (24, 48):
            mh_bars = hours_to_bars(d, max_hold_h)
            sig = day_trade_signal(d, el, es, mh_bars)
            for rmult in (1.5, 2.0, 3.0):
                target_pct = round(stop_pct * rmult, 4)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                cfg = f"sweep-reclaim priorday hold{max_hold_h}h stop={stop_pct:.2f}% R={rmult:.1f}"
                rows.append(mk_row("4b-sweep-reclaim", cfg, tag, "1h", d, i_va, tr, va))
    return rows


# ===========================================================================
# FAMILY 5 — THE BRENT-WTI SPREAD
# ===========================================================================

def build_spread_daily(frames):
    cl = frames["CL"]["1d"][["timestamp", "close"]].rename(columns={"close": "cl_close"})
    bz = frames["BZ"]["1d"][["timestamp", "close"]].rename(columns={"close": "bz_close"})
    cl["_date"] = pd.DatetimeIndex(cl["timestamp"]).date
    bz["_date"] = pd.DatetimeIndex(bz["timestamp"]).date
    merged = pd.merge(cl[["_date", "cl_close"]], bz[["_date", "bz_close"]], on="_date", how="inner")
    merged["spread_pct"] = (merged["cl_close"] - merged["bz_close"]) / merged["bz_close"] * 100
    merged = merged.sort_values("_date").reset_index(drop=True)
    return merged


def rolling_percentile(series, window):
    return series.rolling(window, min_periods=max(30, window // 5)).apply(
        lambda x: (x < x[-1]).mean() * 100, raw=True)


def spread_reversion_signal(cl_daily, spread_pctile, hi_thresh, lo_thresh, max_hold_days):
    """Single-leg approximation of the Brent-WTI pairs trade: when the
    spread is EXTREME WIDE (WTI rich vs Brent, pctile>=hi_thresh) short
    CL outright expecting convergence; when EXTREME NARROW/negative
    (pctile<=lo_thresh) long CL outright. STATED CAVEAT: this is NOT a
    dollar-neutral spread position (the engine trades one instrument at
    a time) — it is a directional bet whose thesis comes from the spread,
    not a real basis trade. Exit: pctile reverts back through the 50th
    percentile midline, or max_hold_days."""
    n = len(cl_daily)
    pct = spread_pctile.to_numpy()
    out = np.zeros(n)
    pos, held = 0.0, 0
    for i in range(n):
        if pos == 0.0:
            if not np.isnan(pct[i]):
                if pct[i] >= hi_thresh:
                    pos, held = -1.0, 0
                elif pct[i] <= lo_thresh:
                    pos, held = 1.0, 0
        else:
            held += 1
            crossed_mid = (pos > 0 and not np.isnan(pct[i]) and pct[i] >= 50) or \
                          (pos < 0 and not np.isnan(pct[i]) and pct[i] <= 50)
            if crossed_mid or held >= max_hold_days:
                pos = 0.0
        out[i] = pos
    return pd.Series(out, index=cl_daily.index)


def family5_spread(frames, meta):
    rows = []
    spread_daily = build_spread_daily(frames)
    print(f"\n  Brent-WTI spread (daily, {len(spread_daily)} overlapping days): "
          f"latest spread={spread_daily['spread_pct'].iloc[-1]:+.2f}%, "
          f"train-median={spread_daily['spread_pct'].iloc[:int(len(spread_daily)*0.6)].median():+.2f}%")

    # align spread onto CL's own daily candles (inner-joined dates) for execution
    cl = frames["CL"]["1d"].copy()
    cl["_date"] = pd.DatetimeIndex(cl["timestamp"]).date
    cl_aligned = cl.merge(spread_daily[["_date", "spread_pct"]], on="_date", how="inner") \
        .sort_values("timestamp").reset_index(drop=True)
    n, i_tr, i_va = split_points(cl_aligned)
    costs = costs_for("CL")
    pctile = rolling_percentile(cl_aligned["spread_pct"], 252)

    for hi_thresh, lo_thresh in ((80, 20), (90, 10)):
        for max_hold_days in (10, 20):
            sig = spread_reversion_signal(cl_aligned, pctile, hi_thresh, lo_thresh, max_hold_days)
            tr, va = score(cl_aligned, sig, costs, i_tr, i_va)
            cfg = f"spread-reversion(outright-CL,single-leg-approx) extreme>={hi_thresh}/<={lo_thresh} hold{max_hold_days}d"
            rows.append(mk_row("5-spread-reversion", cfg, "CL", "1d", cl_aligned, i_va, tr, va))

    # 5b — regime breakdown: tag family-1/2 flagship CL-daily configs by spread regime at entry
    d = frames["CL"]["1d"]
    m = meta["CL"]["1d"]
    trend_sig = structure_trail_signal(d, 20, 5, "long")
    tr_trend, va_trend = score(d, trend_sig, costs_for("CL"), m["i_tr"], m["i_va"])
    mr_sig = mr_signal(d, "rsi2", "long", 5.0, "none", "none", None, None,
                        days_to_bars(d, 10))
    tr_mr, va_mr = score(d, mr_sig, costs_for("CL"), m["i_tr"], m["i_va"])

    pctile_by_date = dict(zip(cl_aligned["timestamp"], pctile))
    for label, tr_res, va_res in (("1-trend donchian20 long", tr_trend, va_trend),
                                   ("2-meanrev rsi2 long", tr_mr, va_mr)):
        all_trades = list(tr_res.trades) + list(va_res.trades)
        buckets = {"extreme(>=80 or <=20)": [], "normal": [], "unknown": []}
        for t in all_trades:
            p = pctile_by_date.get(t.entry_time, np.nan)
            if pd.isna(p):
                buckets["unknown"].append(t.pnl)
            elif p >= 80 or p <= 20:
                buckets["extreme(>=80 or <=20)"].append(t.pnl)
            else:
                buckets["normal"].append(t.pnl)
        print(f"  regime breakdown [{label}]:")
        for bucket, pnls in buckets.items():
            if pnls:
                print(f"    {bucket}: n={len(pnls)} exp=${np.mean(pnls):+.2f}")
            else:
                print(f"    {bucket}: n=0")
    return rows


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 90)
    print("ROUND 78 — AN OIL PLAYBOOK FROM ZERO (research only, no commits/live orders)")
    print("=" * 90)

    frames = load_all_data()
    meta = build_meta(frames)

    print("\n--- FAMILY 1: TREND (donchian breakout + real structure-trailing exit, "
          "both directions, vol-regime gate) ---")
    rows = family1_trend(frames, meta)

    print("--- FAMILY 2: MEAN REVERSION AFTER SPIKES (z-score / RSI2, both directions, "
          "trend + vol gates) ---")
    rows += family2_meanrev(frames, meta)

    print("--- FAMILY 3: INVENTORY-CYCLE / DAY-OF-WEEK (weekday drift + EIA/API "
          "release-hour reaction) ---")
    rows += family3_inventory(frames, meta)

    print("--- FAMILY 4: STRUCTURE, 1h (break+retest+engulf reused from step56/step73; "
          "sweep-and-reclaim of prior-day extremes) ---")
    rows += family4_structure(frames, meta)

    print("--- FAMILY 5: THE BRENT-WTI SPREAD (reversion signal + regime breakdown on "
          "families 1/2) ---")
    rows += family5_spread(frames, meta)

    df = pd.DataFrame(rows)
    df.to_csv("step78_full_table.csv", index=False)
    print(f"\n{len(df)} configs tested. Full table -> step78_full_table.csv")

    print("\nVerdict counts overall:")
    print(df["verdict"].value_counts().to_string())
    print("\nVerdict counts per family:")
    print(df.groupby(["family", "verdict"]).size().to_string())
    print("\nCadence (trades/year) counts:")
    print(df["cadence"].apply(lambda x: "OK" if x == "OK" else "TOO-RARE").value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"].sort_values("va_exp", ascending=False)
    print(f"\n--- SURVIVORS (train+val positive, floors met): {len(survivors)} ---")
    cols = ["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
            "tr_per_yr", "cadence"]
    if len(survivors):
        print(survivors[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    else:
        print("  none")

    playbook = survivors[survivors["cadence"] == "OK"]
    print(f"\n--- PLAYBOOK-VIABLE SURVIVORS (also clear >=10 trades/yr): {len(playbook)} ---")
    if len(playbook):
        print(playbook[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    else:
        print("  none")

    # ---- explicit verdict on the strategies CURRENTLY running on oil ----
    print("\n--- VERDICT: do the CURRENTLY-RUNNING (transfer-assumption) oil strategies "
          "hold up on oil's own data? ---")
    is_gold_donchian_transfer = (df["family"] == "1-trend") & \
        df["config"].str.contains("donchian20 k5-structtrail long gate=ungated", regex=False)
    is_index_rsi2_transfer = (df["family"] == "2-meanrev") & \
        df["config"].str.contains("rsi2>5 long trend=none vol=none", regex=False)
    current = df[is_gold_donchian_transfer | is_index_rsi2_transfer]
    print(current[["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                    "tr_per_yr", "verdict", "cadence"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print("\nDone. No sealed test window was ever sliced or scored above.")
    return df


if __name__ == "__main__":
    main()
