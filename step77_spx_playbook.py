"""
step77_spx_playbook.py — Round 77: A REAL S&P PLAYBOOK.

MANDATE (owner, verbatim spirit): "the sole reason you haven't placed a
single S&P trade is you don't even have a real playbook for it. Your
entire thing is 'we only do panic buys'? That's not trading, that's one
little element." Round 60 built five index-native families but only ONE
of them (RSI2<5 dip-buy, family 1a) fires more than a handful of times a
year — crypto got 50+ rounds and 5 validated plays, the index got one
round. This round is BREADTH: six new families, most of them intraday
(SPY 1h has ~730 days of real bars and round 60 barely touched it — first-
hour-breakout was the only 1h family it ran). Research only. Writes
exactly: step77_spx_playbook.py (this file), step77_results.md (composed
by hand from this script's stdout), step77_full_table.csv (every config,
nothing omitted), and data_spx_<TAG>_<TF>.parquet caches (SPY/ES already
exist from round 60; QQQ is new). No commits, no live orders. Concurrent
agents own step75_*/step76_*/dashboard files this round — untouched here.

READ FIRST (do not re-litigate, build on it): step60_spx_system.py /
step60_results.md. What round 60 already found and is NOT re-tested
identically here: gap-fill chasing the same-day fill (0/16, dead — this
round's family 1e is a DIFFERENT shape, trading the first HOUR's reaction
to the gap, not the daily fill); naive N-day momentum continuation (0/24
dead); golden cross (too slow); overnight drift close->next-open (real but
sub-cost-floor on SPY, this round's family 1d looks at the LAST hour of
the SAME day instead); turn-of-month was flagged (t=2.43) but never built
into a strategy — round 77 family 6a finally builds it. Round 60's
surviving RSI2<5 dip-buy is REUSED (imported: sma/realized_vol_pct/
dipbuy_exit/ETF_COSTS/FUT_COSTS from step60_spx_system) as the base shape
for two new vol-regime cuts (families 4b/5b), not re-derived from scratch.

DATA
  SPY 1h (~730d, yfinance's practical intraday ceiling for equities — the
    "two years of real bars round 60 never used properly" this round's
    brief calls out), SPY 1d (30y+). ES=F 1h + 1d (futures twin, near-24h
    session). QQQ 1d + 1h (NEW this round — the correlated cross-check for
    family 5a's relative-strength divergence and family 3a's structure
    toolkit). SPY/ES caches already exist on disk from round 60
    (data_spx_SPY/ES_1d/1h.parquet); this script loads them as-is, no
    re-fetch. QQQ is fetched fresh and cached the same way
    (data_spx_QQQ_1d/1h.parquet). Every span is printed and stated exactly
    as returned — the SPY/ES 1h ~730d cap is a hard yfinance ceiling for
    intraday equity/futures history, NOT faked finer or longer.

COSTS (no cost-free mode exists — see backtest.py's CostModel)
  ETF (SPY, QQQ): 1bp fee + 1bp slippage each side -> 4bps round trip
    (ETF_COSTS, imported unmodified from step60_spx_system).
  Futures (ES=F): 0.5bp fee + 0.5bp slippage each side -> 2bps round trip
    (FUT_COSTS, imported unmodified from step60_spx_system).
  execution="taker" throughout, matching step48/step55/step60's TradFi
  convention.

GAUNTLET
  Chronological 60/20/20 per dataset/timeframe (n, i_tr, i_va — same
  split_points idiom imported from step43_daytrade). >=30 train / >=8 val
  trades to earn SURVIVOR (MIN_TRAIN_TRADES/MIN_VAL_TRADES, imported).
  Selection is by TRAIN expectancy only; val is reported, never tuned
  against. This script NEVER slices into the final 20% (test) of ANY
  split — the sealed window is left for the lead agent to spend looks
  against. TRADES/YEAR is computed and reported for every survivor/near-
  miss (train+val span in years, from the frame's own timestamps) —
  anything under 10/yr is flagged explicitly as "rare, not a playbook
  piece," per the task's own framing.

ENGINE-MISMATCH APPROXIMATIONS (stated plainly, per this codebase's
standing discipline — see step43/step48/step60 headers for the same idiom)
  1. FAMILY 1d (last-hour drift/close-hour momentum) is measured as a
     DIRECT STATISTICAL AUDIT (paired: day's momentum through the second-
     to-last bar vs the final bar's own return, t-stat + mean + win%),
     exactly like step60's family 2b overnight-drift audit, rather than
     forced through run_backtest — the engine's bar-close-decide/next-
     bar-open-fill mechanic cannot express "exit at THIS bar's own close,"
     only "exit at the NEXT bar's open," which would silently turn a
     same-day close-hour trade into an overnight hold. Sidestepped
     entirely by treating it as an anomaly audit, same as step60's
     precedent.
  2. FAMILY 1e (gap reaction) sizes its entry off information (today's
     open vs yesterday's close) that is technically knowable at today's
     first bar's OWN open — but the engine can only act on a signal
     decided at a bar's CLOSE, filled at the NEXT bar's open. So this
     family's "first hour" entries actually execute at the START of the
     SECOND hour (trading the gap's continuation/fade from hour 2
     onward, not hour 1's own print) — stated plainly, the same one-bar-
     lag discipline every family in this codebase respects (see
     strategy.py's own docstring).
  3. Every "exit by end of day" family (1a/1b/1c/1e/3a/3b/3c/4a) uses a
     FIXED HOURS-BASED max_hold safety cap (day_trade_signal, imported
     from step43) rather than exact day-boundary machinery, exactly
     step60's own stated precedent for family 2c (itself inherited from
     step43's original session-breakout family).
  4. Every family that wants a per-trade DYNAMIC stop/target distance
     (range height, ATR, distance-to-broken-structure-level) uses this
     repo's established TRAIN-median-distance approximation, held fixed
     across train/val (round 17 / step41 / step43 / step48 / step56 /
     step60 precedent) — train_median_stop_pct is imported UNMODIFIED
     from step56_smc_toolkit for family 3's structure shapes.

PLUMBING REUSE (by import, per the task mandate — "reuse step56/step73
functions by import")
  step43_daytrade: MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours,
    day_trade_signal, hold_stats, hours_to_bars, split_points.
  step48_tradfi_trend: days_to_bars, event_long.
  step56_smc_toolkit: bos_chain (BOS/CHoCH — the toolkit's core structure
    primitive), train_median_stop_pct, STOP_CAP_PCT, STOP_FLOOR_PCT.
  step73_video: body_frame ("do not take the wicks into account" —
    his own stated structure rule, offered as a grid dimension alongside
    the wick-based reading).
  step60_spx_system: ETF_COSTS, FUT_COSTS, sma, realized_vol_pct,
    dipbuy_exit — the exact surviving RSI2<5 dip-buy shape, reused as the
    base for families 4b/5b's vol-regime cuts rather than re-derived.
  strategy.py: atr, rsi (verbatim, never reimplemented).
  backtest.py: CostModel, run_backtest (verbatim, the only engine there is).

NOTE ON step73's PRIOR "index" TEST: step73_video.py's own docstring
lists ES=F as one of five datasets in its daily-context -> 4h-entry
break-and-retest system (see its load_index()). That IS a prior index
test — but it is NOT what this round's family 3 does. step73 collapses a
DAILY structure read into a 4H entry with a retest+engulf confirmation
gate (mostly NO-ENTRIES on ES per step73_results.md — too few daily break
events even over the ES=F span). Family 3 here runs bos_chain NATIVELY on
the 1H frame itself (SPY/ES/QQQ), no daily->4h collapse, no retest/engulf
gate, and adds the sweep-and-reclaim-of-prior-day's-high/low shape (which
step56/step73 never define) plus a fresh CHoCH+confluence head-to-head —
extending into what step73 did NOT cover, not repeating it.

SIX FAMILIES — see each family_*() function's docstring for the exact
shape, traceable back to the round-77 brief's six-item list.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from strategy import atr, rsi
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours, day_trade_signal,
    hold_stats, hours_to_bars, split_points,
)
from step48_tradfi_trend import days_to_bars, event_long
from step56_smc_toolkit import (
    STOP_CAP_PCT, STOP_FLOOR_PCT, bos_chain, train_median_stop_pct,
)
from step73_video import body_frame
from step60_spx_system import ETF_COSTS, FUT_COSTS, dipbuy_exit, realized_vol_pct, sma

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

TICKER = {"SPY": "SPY", "ES": "ES=F", "QQQ": "QQQ"}
COSTS = {"SPY": ETF_COSTS, "QQQ": ETF_COSTS, "ES": FUT_COSTS}


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
    """data_spx_<tag>_<tf>.parquet — SPY/ES reuse round-60's caches
    verbatim (same filename convention); QQQ fetches fresh."""
    fname = f"data_spx_{tag}_{tf}.parquet"
    try:
        d = pd.read_parquet(fname)
        print(f"  cached {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
        return d
    except FileNotFoundError:
        pass
    period = "max" if tf == "1d" else "730d"
    interval = "1d" if tf == "1d" else "1h"
    print(f"  fetching fresh {TICKER[tag]} {tf} ({period}) via yfinance...")
    d = _fetch_yf(TICKER[tag], interval, period)
    d.to_parquet(fname)
    print(f"  saved {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def load_all() -> dict:
    frames = {}
    for tag in ("SPY", "ES", "QQQ"):
        frames[tag] = {"1d": load_symbol(tag, "1d"), "1h": load_symbol(tag, "1h")}
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


def train_val_years(d, i_va) -> float:
    span = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds()
    return max(span / (3600 * 24 * 365.25), 0.01)


def mk_row(family, config, symbol, tf, d, i_va, tr, va, stop_pct=None, target_pct=None,
           extra=None):
    med_h, mean_h = hold_stats(tr, va)
    n_total = len(tr.trades) + len(va.trades)
    years = train_val_years(d, i_va)
    row = {
        "family": family, "config": config, "symbol": symbol, "tf": tf,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "trades_yr": n_total / years,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def event_signal(d, enter, exit_, direction, max_hold=0):
    """Generic single-direction event-entry / condition-or-timed-exit state
    machine (direction=+1 long, -1 short) — the family-5a divergence
    trades need a SHORT leg that step48's event_long doesn't offer."""
    e = enter.fillna(False).to_numpy(dtype=bool)
    x = exit_.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if e[i]:
                pos, held = float(direction), 0
        else:
            held += 1
            if x[i] or (max_hold and held >= max_hold):
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ---------------------------------------------------------------------------
# session / structure helpers
# ---------------------------------------------------------------------------

def et_ctx(d):
    """ET calendar day, fractional hour-of-day, position-within-day, and
    first/last-bar-of-day flags — the shared building block for every
    intraday family below."""
    ts_et = d["timestamp"].dt.tz_convert("America/New_York")
    day = ts_et.dt.date
    frac_hour = ts_et.dt.hour + ts_et.dt.minute / 60.0
    tmp = pd.DataFrame({"day": day}, index=d.index)
    bar_in_day = tmp.groupby("day")["day"].cumcount()
    day_count = tmp.groupby("day")["day"].transform("count")
    is_first = bar_in_day == 0
    is_last = bar_in_day == (day_count - 1)
    return day, frac_hour, bar_in_day, is_first, is_last


def clock_window(d, day, frac_hour, start_hour, H):
    """High/low of the [start_hour, start_hour+H) ET clock window, per
    calendar day — SPY's literal RTH open (9:30 ET) for the ETF, and the
    SAME clock reference on ES=F's near-continuous session (the window a
    futures trader actually watches even though the contract never
    closes). Returns (win_high, win_low, after_window)."""
    in_window = (frac_hour >= start_hour) & (frac_hour < start_hour + H)
    tmp = pd.DataFrame({"day": day, "high": d["high"], "low": d["low"]})
    win_high = tmp["high"].where(in_window).groupby(tmp["day"]).transform("max")
    win_low = tmp["low"].where(in_window).groupby(tmp["day"]).transform("min")
    after = frac_hour >= start_hour + H
    return win_high, win_low, after


def prior_day_series(d1d, colname):
    """Daily column value SHIFTED BY ONE DAY (yesterday's value), keyed by
    an ET-date index — maps onto any finer frame via `.map(day)` with no
    lookahead (today's bars only ever see YESTERDAY's fixed level)."""
    d1d_date = d1d["timestamp"].dt.tz_convert("America/New_York").dt.date
    s = pd.Series(d1d[colname].shift(1).to_numpy(), index=d1d_date.to_numpy())
    return s[~s.index.duplicated(keep="last")]


def session_vwap(d, day):
    pv = d["close"] * d["volume"]
    cum_pv = pv.groupby(day).cumsum()
    cum_v = d["volume"].groupby(day).cumsum()
    return cum_pv / cum_v.replace(0, np.nan)


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def bollinger_bands(close, n=20, k=2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    return mid - k * std, mid, mid + k * std


def keltner_channel(d, n=20, mult=1.5):
    mid = d["close"].ewm(span=n, adjust=False).mean()
    a = atr(d, n)
    return mid - mult * a, mid, mid + mult * a


# ---------------------------------------------------------------------------
# FAMILY 1 — intraday session structure (SPY/ES 1h)
# ---------------------------------------------------------------------------

def family1a_orb_breakout(frames, meta):
    """Opening-range breakout: first {1,2}h RTH-clock range, trade the
    break, 6-bar safety cap (~a trading day). SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        for H in (1, 2):
            win_high, win_low, after = clock_window(d, day, frac_hour, 9.5, H)
            range_h_pct = (win_high - win_low) / win_low * 100
            med_range_tr = float(range_h_pct.iloc[:i_tr].dropna().median())
            enter_long = (after & (d["close"] > win_high)).fillna(False)
            enter_short = (after & (d["close"] < win_low)).fillna(False)
            mh_bars = hours_to_bars(d, 6)
            for direction, el, es in (
                ("long", enter_long, pd.Series(False, index=d.index)),
                ("short", pd.Series(False, index=d.index), enter_short),
            ):
                sig = day_trade_signal(d, el, es, mh_bars)
                for tmult in (1.5, 2.5):
                    target_pct = tmult * med_range_tr
                    stop_pct = min(med_range_tr, 3.0)
                    tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                    cfg = f"H{H}h {direction} tgt{tmult}xrange"
                    rows.append(mk_row("1a-orb-breakout", cfg, tag, "1h", d, i_va,
                                        tr, va, stop_pct, target_pct))
    return rows


def family1b_orb_fade(frames, meta):
    """Opening-range FADE (the mirror of 1a): price pokes outside the
    opening range then closes back inside it (failed breakout) -> trade
    back the other way. SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        for H in (1, 2):
            win_high, win_low, after = clock_window(d, day, frac_hour, 9.5, H)
            range_h_pct = (win_high - win_low) / win_low * 100
            med_range_tr = float(range_h_pct.iloc[:i_tr].dropna().median())
            broke_up_recent = (d["high"] > win_high).rolling(2, min_periods=1).max().astype(bool)
            broke_down_recent = (d["low"] < win_low).rolling(2, min_periods=1).max().astype(bool)
            fail_up = (after & broke_up_recent & (d["close"] < win_high)).fillna(False)
            fail_down = (after & broke_down_recent & (d["close"] > win_low)).fillna(False)
            mh_bars = hours_to_bars(d, 6)
            for direction, el, es in (
                ("long(fade-low-fail)", fail_down, pd.Series(False, index=d.index)),
                ("short(fade-high-fail)", pd.Series(False, index=d.index), fail_up),
            ):
                sig = day_trade_signal(d, el, es, mh_bars)
                for tmult in (1.0, 1.5):
                    target_pct = tmult * med_range_tr
                    stop_pct = min(med_range_tr, 3.0)
                    tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                    cfg = f"H{H}h {direction} tgt{tmult}xrange"
                    rows.append(mk_row("1b-orb-fade", cfg, tag, "1h", d, i_va,
                                        tr, va, stop_pct, target_pct))
    return rows


def family1c_midsession_reversal(frames, meta):
    """Mid-session (11:00-14:00 ET) failed-new-extreme reversal: price
    makes a fresh session high/low then closes back inside the prior
    extreme -> fade it. SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        cummax_prior = d.groupby(day)["high"].cummax().groupby(day).shift(1)
        cummin_prior = d.groupby(day)["low"].cummin().groupby(day).shift(1)
        mid_window = (frac_hour >= 11) & (frac_hour < 14)
        fail_high = (mid_window & (d["high"] > cummax_prior) & (d["close"] < cummax_prior)).fillna(False)
        fail_low = (mid_window & (d["low"] < cummin_prior) & (d["close"] > cummin_prior)).fillna(False)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_tr = float(atr_pct.iloc[:i_tr].median())
        mh_bars = hours_to_bars(d, 3)
        for direction, el, es in (
            ("long(fail-low)", fail_low, pd.Series(False, index=d.index)),
            ("short(fail-high)", pd.Series(False, index=d.index), fail_high),
            ("both", fail_low, fail_high),
        ):
            sig = day_trade_signal(d, el, es, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_atr_tr
                stop_pct = min(1.0 * med_atr_tr, 2.5)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                cfg = f"{direction} tgt{tmult}xATR"
                rows.append(mk_row("1c-midsession-reversal", cfg, tag, "1h", d, i_va,
                                    tr, va, stop_pct, target_pct))
    return rows


def family1d_lasthour_drift(frames, meta):
    """REPORT-ONLY statistical audit (same discipline as step60's family
    2b): does the day's momentum through the SECOND-TO-LAST bar predict
    the sign/size of the LAST bar's own return (the 'run into the
    close')? Engine-mismatch reasoning in the module docstring. SPY + ES."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        i_va = m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        day_open_map = d.groupby(day)["open"].transform("first")
        day_ret_so_far = (d["close"] - day_open_map) / day_open_map * 100
        is_2nd_last = is_last.shift(-1, fill_value=False)
        last_bar_ret = (d["close"] - d["open"]) / d["open"] * 100
        use = is_2nd_last.iloc[:i_va].to_numpy()
        mom = day_ret_so_far.iloc[:i_va][use]
        nxt = last_bar_ret.shift(-1).iloc[:i_va][use]
        valid = mom.notna() & nxt.notna()
        mom, nxt = mom[valid], nxt[valid]
        buckets = [("all", pd.Series(True, index=mom.index)),
                   ("momentum-up(day-so-far>0)", mom > 0),
                   ("momentum-down(day-so-far<0)", mom < 0)]
        for label, bmask in buckets:
            sub = nxt[bmask.to_numpy()]
            n = len(sub)
            if n < 2:
                rows.append({"symbol": tag, "config": label, "n": n,
                             "mean_ret_pct": np.nan, "tstat": np.nan, "win_pct": np.nan})
                continue
            mean = float(sub.mean())
            std = float(sub.std(ddof=1))
            tstat = mean / (std / np.sqrt(n)) if std > 0 else np.nan
            rows.append({"symbol": tag, "config": label, "n": n, "mean_ret_pct": mean,
                         "tstat": tstat, "win_pct": float((sub > 0).mean() * 100)})
    return rows


def family1e_gap_reaction(frames, meta):
    """Overnight-gap continuation vs fade, measured/TRADED at 1h (not
    step60's daily close->open fill-chase, which is dead): does the
    OPENING gap's own direction continue or reverse over the first
    couple hours? SPY only — ES's structural gap is ~7x smaller
    (step60 finding), not a productive test of this shape."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1h"].reset_index(drop=True)
    d1d = frames[tag]["1d"]
    m = meta[tag]["1h"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
    prior_close_today = day.map(prior_day_series(d1d, "close"))
    day_open_map = d.groupby(day)["open"].transform("first")
    gap_pct = pd.Series((day_open_map.to_numpy() - prior_close_today.to_numpy())
                         / prior_close_today.to_numpy() * 100, index=d.index)
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_tr = float(atr_pct.iloc[:i_tr].median())
    mh_bars = hours_to_bars(d, 3)
    for gap_th in (0.2, 0.4):
        gap_up = gap_pct > gap_th
        gap_down = gap_pct < -gap_th
        modes = [("continuation", (is_first & gap_up).fillna(False),
                  (is_first & gap_down).fillna(False)),
                 ("fade", (is_first & gap_down).fillna(False),
                  (is_first & gap_up).fillna(False))]
        for mode, el, es in modes:
            sig = day_trade_signal(d, el, es, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_atr_tr
                stop_pct = min(1.0 * med_atr_tr, 2.0)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                cfg = f"gap{gap_th}% {mode} tgt{tmult}xATR"
                rows.append(mk_row("1e-gap-reaction", cfg, tag, "1h", d, i_va,
                                    tr, va, stop_pct, target_pct))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 2 — pullback-in-trend (SPY/ES 1h)
# ---------------------------------------------------------------------------

def family2_pullback_trend(frames, meta):
    """Above daily SMA50/SMA200 (yesterday's read, no lookahead) -> buy 1h
    pullbacks to EMA20/EMA50 (intraday) or today's running session VWAP
    (the standard institutional pullback level — used here instead of a
    literal frozen 'prior day's VWAP', stated plainly as the more
    standard tool) on a reclaim (close crosses back above the level after
    dipping below it). Long-only, per the index's own long bias (step60
    finding: shorts lose everywhere). SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        d1d = frames[tag]["1d"]
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_tr = float(atr_pct.iloc[:i_tr].median())

        d1d_sma50 = d1d.assign(_s=sma(d1d["close"], 50))
        d1d_sma200 = d1d.assign(_s=sma(d1d["close"], 200))
        close_prior = day.map(prior_day_series(d1d, "close"))
        above50 = (close_prior > day.map(prior_day_series(d1d_sma50, "_s"))).fillna(False)
        above200 = (close_prior > day.map(prior_day_series(d1d_sma200, "_s"))).fillna(False)

        targets = {"EMA20": ema(d["close"], 20), "EMA50": ema(d["close"], 50),
                   "sessionVWAP": session_vwap(d, day)}
        gates = {"SMA50": above50, "SMA200": above200}
        mh_bars = hours_to_bars(d, 6)

        for tname, tgt in targets.items():
            below = d["close"] < tgt
            reclaim = (below.shift(1, fill_value=False) & (d["close"] > tgt)).fillna(False)
            for gname, gate in gates.items():
                enter_long = (reclaim & gate).fillna(False)
                enter_short = pd.Series(False, index=d.index)
                sig = day_trade_signal(d, enter_long, enter_short, mh_bars)
                for tmult in (1.5, 2.5):
                    target_pct = tmult * med_atr_tr
                    stop_pct = min(1.0 * med_atr_tr, 2.0)
                    tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                    cfg = f"pullback->{tname} trend={gname} tgt{tmult}xATR"
                    rows.append(mk_row("2-pullback-trend", cfg, tag, "1h", d, i_va,
                                        tr, va, stop_pct, target_pct))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 3 — structure (step56 bos_chain / step73 body_frame, NATIVE 1h)
# ---------------------------------------------------------------------------

def family3a_bos_choch(frames, meta):
    """BOS-continuation vs CHoCH vs "both", wick-based vs body-based
    (step73's 'do not take the wicks into account' rule), k in {5,8},
    run NATIVELY on the 1h frame (never done in this repo before — step73
    only ever collapsed daily structure into a 4h entry). SPY + ES=F +
    QQQ (the correlated cross-check)."""
    rows = []
    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        mh_bars = hours_to_bars(d, 12)
        for k in (5, 8):
            for struct_name, dsrc in (("wick", d), ("body", body_frame(d))):
                bos = bos_chain(dsrc, k)
                dist_long = (d["close"] - bos["lsl"]) / d["close"] * 100
                dist_short = (bos["lsh"] - d["close"]) / d["close"] * 100
                modes = [("cont", bos["cont_long"], bos["cont_short"]),
                         ("choch", bos["choch_long"], bos["choch_short"]),
                         ("both", bos["bos_up"], bos["bos_down"])]
                for mode_name, el_raw, es_raw in modes:
                    el, es = el_raw.fillna(False), es_raw.fillna(False)
                    dist = pd.Series(np.nan, index=d.index)
                    dist = dist.mask(el, dist_long)
                    dist = dist.mask(es, dist_short)
                    stop_pct = train_median_stop_pct(d, i_tr, el | es, dist)
                    if stop_pct is None:
                        continue
                    sig = day_trade_signal(d, el, es, mh_bars)
                    for rmult in (1.5, 2.5):
                        target_pct = rmult * stop_pct
                        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                        cfg = f"k={k} struct={struct_name} mode={mode_name} R{rmult}"
                        rows.append(mk_row("3a-bos-choch", cfg, tag, "1h", d, i_va,
                                            tr, va, stop_pct, target_pct))
    return rows


def family3b_sweep_reclaim(frames, meta):
    """Sweep-and-reclaim of the PRIOR DAY's high/low (a level bos_chain's
    own k-bar-swing pools never define): wick pierces yesterday's
    high/low but closes back inside -> fade the raid. SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        d1d = frames[tag]["1d"]
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        prior_high_map = day.map(prior_day_series(d1d, "high"))
        prior_low_map = day.map(prior_day_series(d1d, "low"))
        long_reclaim = ((d["low"] < prior_low_map) & (d["close"] > prior_low_map)).fillna(False)
        short_reclaim = ((d["high"] > prior_high_map) & (d["close"] < prior_high_map)).fillna(False)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_tr = float(atr_pct.iloc[:i_tr].median())
        mh_bars = hours_to_bars(d, 6)
        for direction, el, es in (
            ("long-only", long_reclaim, pd.Series(False, index=d.index)),
            ("short-only", pd.Series(False, index=d.index), short_reclaim),
            ("both", long_reclaim, short_reclaim),
        ):
            sig = day_trade_signal(d, el, es, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_atr_tr
                stop_pct = min(1.0 * med_atr_tr, 2.0)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                cfg = f"{direction} tgt{tmult}xATR"
                rows.append(mk_row("3b-sweep-reclaim-priorday", cfg, tag, "1h", d, i_va,
                                    tr, va, stop_pct, target_pct))
    return rows


def family3c_choch_confluence(frames, meta):
    """The round's central structure question, transferred: does
    requiring CHoCH to AGREE with a recent prior-day sweep-and-reclaim
    (family 3b) beat CHoCH alone — step56's confluence claim, on the
    index. SPY + ES=F, k=8 fixed (the family-3a middling choice)."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        d1d = frames[tag]["1d"]
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
        k = 8
        bos = bos_chain(d, k)
        choch_long, choch_short = bos["choch_long"].fillna(False), bos["choch_short"].fillna(False)
        prior_high_map = day.map(prior_day_series(d1d, "high"))
        prior_low_map = day.map(prior_day_series(d1d, "low"))
        long_reclaim = ((d["low"] < prior_low_map) & (d["close"] > prior_low_map)).fillna(False)
        short_reclaim = ((d["high"] > prior_high_map) & (d["close"] < prior_high_map)).fillna(False)
        window = hours_to_bars(d, 6)
        sweep_recent_long = long_reclaim.astype(int).rolling(window, min_periods=1).max().astype(bool)
        sweep_recent_short = short_reclaim.astype(int).rolling(window, min_periods=1).max().astype(bool)
        dist_long = (d["close"] - bos["lsl"]) / d["close"] * 100
        dist_short = (bos["lsh"] - d["close"]) / d["close"] * 100
        mh_bars = hours_to_bars(d, 12)
        for thresh_name, el, es in (
            ("CHoCH-alone(ungated)", choch_long, choch_short),
            ("CHoCH+sweep-agree(confluence)", choch_long & sweep_recent_long,
             choch_short & sweep_recent_short),
        ):
            dist = pd.Series(np.nan, index=d.index)
            dist = dist.mask(el, dist_long)
            dist = dist.mask(es, dist_short)
            stop_pct = train_median_stop_pct(d, i_tr, el | es, dist)
            if stop_pct is None:
                continue
            sig = day_trade_signal(d, el.fillna(False), es.fillna(False), mh_bars)
            for rmult in (1.5, 2.5):
                target_pct = rmult * stop_pct
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                cfg = f"{thresh_name} R{rmult}"
                rows.append(mk_row("3c-choch-confluence", cfg, tag, "1h", d, i_va,
                                    tr, va, stop_pct, target_pct))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 4 — volatility regime (SPY/ES 1h, SPY 1d)
# ---------------------------------------------------------------------------

def family4a_squeeze_expansion(frames, meta):
    """TTM-style squeeze (BB(20,2) fully inside KC(20,1.5xATR)) -> trade
    the direction of the release. SPY + ES=F, 1h."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1h"].reset_index(drop=True)
        m = meta[tag]["1h"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        bb_lo, bb_mid, bb_hi = bollinger_bands(d["close"], 20, 2.0)
        kc_lo, kc_mid, kc_hi = keltner_channel(d, 20, 1.5)
        squeeze = ((bb_lo > kc_lo) & (bb_hi < kc_hi)).fillna(False)
        release = squeeze.shift(1, fill_value=False) & ~squeeze
        up = d["close"] > kc_mid
        enter_long = (release & up).fillna(False)
        enter_short = (release & ~up).fillna(False)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr_tr = float(atr_pct.iloc[:i_tr].median())
        mh_bars = hours_to_bars(d, 8)
        for direction, el, es in (
            ("long-only", enter_long, pd.Series(False, index=d.index)),
            ("short-only", pd.Series(False, index=d.index), enter_short),
            ("both", enter_long, enter_short),
        ):
            sig = day_trade_signal(d, el, es, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_atr_tr
                stop_pct = min(1.0 * med_atr_tr, 2.5)
                tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
                cfg = f"{direction} tgt{tmult}xATR"
                rows.append(mk_row("4a-squeeze-expansion", cfg, tag, "1h", d, i_va,
                                    tr, va, stop_pct, target_pct))
    return rows


def family4b_volgate_dipbuy(frames, meta):
    """Does round 60's surviving RSI2<5 dip-buy (SPY daily) need an ATR%-
    percentile floor — is there a 'too quiet to trade' state? unfiltered
    vs vol-percentile > {30,50,70}."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1d"]
    m = meta[tag]["1d"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    close = d["close"]
    sma200 = sma(close, 200)
    r2 = rsi(close, 2)
    exit_cond = dipbuy_exit(d).fillna(False)
    vol_pct = realized_vol_pct(d)
    enter_base = ((r2 < 5) & (close > sma200)).fillna(False)
    for gname, gate in (("unfiltered", pd.Series(True, index=d.index)),
                         ("vol>30pct", vol_pct > 30), ("vol>50pct", vol_pct > 50),
                         ("vol>70pct", vol_pct > 70)):
        enter = (enter_base & gate.fillna(False))
        sig = event_long(d, enter, exit_cond, 0)
        tr, va = score(d, sig, costs, i_tr, i_va)
        cfg = f"rsi2<5 gate={gname}"
        rows.append(mk_row("4b-volgate-dipbuy", cfg, tag, "1d", d, i_va, tr, va))
    return rows


def family4c_volgate_orb(frames, meta):
    """Same 'too quiet to trade' question applied to family 1a's H1-long
    opening-range breakout (SPY): unfiltered vs 1h-ATR%-percentile
    (trailing 1y) > {30,50}."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1h"].reset_index(drop=True)
    m = meta[tag]["1h"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    day, frac_hour, bar_in_day, is_first, is_last = et_ctx(d)
    win_high, win_low, after = clock_window(d, day, frac_hour, 9.5, 1)
    range_h_pct = (win_high - win_low) / win_low * 100
    med_range_tr = float(range_h_pct.iloc[:i_tr].dropna().median())
    atr_pct_1h = atr(d, 14) / d["close"] * 100
    window = max(60, hours_to_bars(d, 24 * 365))
    vol_pct_1h = atr_pct_1h.rolling(window, min_periods=60).rank(pct=True) * 100
    enter_long_base = (after & (d["close"] > win_high)).fillna(False)
    mh_bars = hours_to_bars(d, 6)
    for gname, gate in (("unfiltered", pd.Series(True, index=d.index)),
                         ("vol>30pct", vol_pct_1h > 30), ("vol>50pct", vol_pct_1h > 50)):
        el = enter_long_base & gate.fillna(False)
        sig = day_trade_signal(d, el, pd.Series(False, index=d.index), mh_bars)
        target_pct = 2.5 * med_range_tr
        stop_pct = min(med_range_tr, 3.0)
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, target_pct)
        cfg = f"H1h long tgt2.5xrange gate={gname}"
        rows.append(mk_row("4c-volgate-orb", cfg, tag, "1h", d, i_va, tr, va, stop_pct, target_pct))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 5 — relative strength / intermarket (SPY vs QQQ)
# ---------------------------------------------------------------------------

def family5a_relative_strength(frames, meta):
    """SPY vs QQQ divergence: one breaks an N-day return, the other
    doesn't. Four directional hypotheses tested head-to-head: trade the
    LAGGARD for catch-up, or fade the LEADER for mean reversion. Own
    chronological 60/20/20 split on the SPY/QQQ common-date frame."""
    rows = []
    dspy_full, dqqq_full = frames["SPY"]["1d"], frames["QQQ"]["1d"]
    spy_idx = dspy_full.set_index(dspy_full["timestamp"].dt.date)
    qqq_idx = dqqq_full.set_index(dqqq_full["timestamp"].dt.date)
    common = spy_idx.index.intersection(qqq_idx.index)
    spy_c = spy_idx.loc[common].sort_index().reset_index(drop=True)
    qqq_c = qqq_idx.loc[common].sort_index().reset_index(drop=True)
    n = len(spy_c)
    i_tr, i_va = int(n * 0.6), int(n * 0.8)
    med_atr_spy = float((atr(spy_c, 14) / spy_c["close"] * 100).iloc[:i_tr].median())
    med_atr_qqq = float((atr(qqq_c, 14) / qqq_c["close"] * 100).iloc[:i_tr].median())
    for N in (5, 10):
        spy_ret = spy_c["close"].pct_change(N) * 100
        qqq_ret = qqq_c["close"].pct_change(N) * 100
        spy_strong = ((spy_ret > 0) & (qqq_ret < 0)).fillna(False)
        qqq_strong = ((qqq_ret > 0) & (spy_ret < 0)).fillna(False)
        exit_n = min(N, 5)
        specs = [
            ("long-QQQ-catchup", "QQQ", qqq_c, spy_strong, 1, med_atr_qqq),
            ("short-SPY-meanrev", "SPY", spy_c, spy_strong, -1, med_atr_spy),
            ("long-SPY-catchup", "SPY", spy_c, qqq_strong, 1, med_atr_spy),
            ("short-QQQ-meanrev", "QQQ", qqq_c, qqq_strong, -1, med_atr_qqq),
        ]
        for label, sym, dframe, trigger, direction, med_atr in specs:
            costs = COSTS[sym]
            sig = event_signal(dframe, trigger, pd.Series(False, index=dframe.index),
                                direction, max_hold=exit_n)
            stop_pct = min(1.5 * med_atr, 4.0)
            tr, va = score(dframe, sig, costs, i_tr, i_va, stop_pct, None)
            cfg = f"N{N}d {label} hold{exit_n}d"
            rows.append(mk_row("5a-relative-strength", cfg, sym, "1d", dframe, i_va,
                                tr, va, stop_pct, None))
    return rows


def family5b_volpct_terciles_dipbuy(frames, meta):
    """Direct comparison: does the RSI2<5 panic-buy improve when
    volatility is extreme vs moderate vs calm? Low/mid/high realized-vol
    terciles, same shape, side by side. SPY + ES=F."""
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        close = d["close"]
        sma200 = sma(close, 200)
        r2 = rsi(close, 2)
        exit_cond = dipbuy_exit(d).fillna(False)
        vol_pct = realized_vol_pct(d)
        enter_base = ((r2 < 5) & (close > sma200)).fillna(False)
        for tname, lo, hi in (("low-vol(<33pct)", -1, 33), ("mid-vol(33-67pct)", 33, 67),
                               ("high-vol(>67pct)", 67, 101)):
            gate = ((vol_pct >= lo) & (vol_pct < hi)).fillna(False)
            enter = enter_base & gate
            sig = event_long(d, enter, exit_cond, 0)
            tr, va = score(d, sig, costs, i_tr, i_va)
            cfg = f"rsi2<5 volterc={tname}"
            rows.append(mk_row("5b-volpct-tercile-dipbuy", cfg, tag, "1d", d, i_va, tr, va))
    return rows


# ---------------------------------------------------------------------------
# FAMILY 6 — seasonality follow-up (SPY daily, tradeable)
# ---------------------------------------------------------------------------

def tom_signal(d, N):
    """Turn-of-month, built as an actual trade (step60 flagged t=2.43 and
    never built it): enter exactly N trading days before month-end, exit
    exactly N trading days into the new month."""
    month = d["timestamp"].dt.tz_convert("America/New_York").dt.to_period("M")
    rev_rank = d.groupby(month).cumcount(ascending=False)
    fwd_rank = d.groupby(month).cumcount()
    enter_long = (rev_rank == (N - 1))
    exit_ = (fwd_rank == N)
    return enter_long.fillna(False), exit_.fillna(False)


def family6a_turn_of_month(frames, meta):
    rows = []
    tag = "SPY"
    d = frames[tag]["1d"]
    m = meta[tag]["1d"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr_tr = float(atr_pct.iloc[:i_tr].median())
    for N in (1, 2, 3):
        enter_long, exit_ = tom_signal(d, N)
        for stop_name, stop_pct in (("none", None), ("2xATR", min(2.0 * med_atr_tr, 5.0))):
            sig = event_long(d, enter_long, exit_, days_to_bars(d, 40))
            tr, va = score(d, sig, costs, i_tr, i_va, stop_pct, None)
            cfg = f"TOM N={N}d stop={stop_name}"
            rows.append(mk_row("6a-turn-of-month", cfg, tag, "1d", d, i_va, tr, va, stop_pct, None))
    return rows


def family6b_day_of_week(frames, meta):
    rows = []
    tag = "SPY"
    d = frames[tag]["1d"]
    m = meta[tag]["1d"]
    costs = COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]
    dow = d["timestamp"].dt.tz_convert("America/New_York").dt.dayofweek
    enter_mon, exit_fri = (dow == 0), (dow == 4)
    sig = event_long(d, enter_mon, exit_fri, days_to_bars(d, 10))
    tr, va = score(d, sig, costs, i_tr, i_va)
    rows.append(mk_row("6b-day-of-week", "long Mon->Fri", tag, "1d", d, i_va, tr, va))

    enter_tue = (dow == 1)
    sig2 = event_long(d, enter_tue, pd.Series(False, index=d.index), 1)
    tr2, va2 = score(d, sig2, costs, i_tr, i_va)
    rows.append(mk_row("6b-day-of-week", "long Tue-only 1d hold", tag, "1d", d, i_va, tr2, va2))
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 78)
    print("ROUND 77 — A REAL S&P PLAYBOOK: breadth of setups, SPY/ES/QQQ")
    print("=" * 78)

    frames = load_all()

    meta = {tag: {} for tag in ("SPY", "ES", "QQQ")}
    print("\nSpans + split points + median TRAIN ATR% (stated exactly, no faked resolution):")
    for tag in ("SPY", "ES", "QQQ"):
        for tf in ("1d", "1h"):
            d = frames[tag][tf]
            n, i_tr, i_va = split_points(d)
            atr_pct = atr(d, 14) / d["close"] * 100
            med_atr_train = float(atr_pct.iloc[:i_tr].median())
            meta[tag][tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr_train}
            print(f"  {tag:4s} {tf}: {n:6d} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
                  f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
                  f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
                  f"med train ATR%={med_atr_train:.3f}%")

    rows = []
    print("\nRunning FAMILY 1a (opening-range breakout)...")
    rows += family1a_orb_breakout(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 1b (opening-range fade)...")
    rows += family1b_orb_fade(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 1c (mid-session reversal)...")
    rows += family1c_midsession_reversal(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 1e (gap reaction, SPY 1h)...")
    rows += family1e_gap_reaction(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 2 (pullback-in-trend)...")
    rows += family2_pullback_trend(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 3a (BOS/CHoCH, native 1h)...")
    rows += family3a_bos_choch(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 3b (sweep-and-reclaim of prior day's high/low)...")
    rows += family3b_sweep_reclaim(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 3c (CHoCH+confluence head-to-head)...")
    rows += family3c_choch_confluence(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 4a (squeeze -> expansion)...")
    rows += family4a_squeeze_expansion(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 4b (vol-gated dip-buy, daily)...")
    rows += family4b_volgate_dipbuy(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 4c (vol-gated opening-range breakout)...")
    rows += family4c_volgate_orb(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 5a (SPY vs QQQ relative strength)...")
    rows += family5a_relative_strength(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 5b (vol-percentile terciles on dip-buy)...")
    rows += family5b_volpct_terciles_dipbuy(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 6a (turn-of-month, tradeable)...")
    rows += family6a_turn_of_month(frames, meta)
    print(f"  {len(rows)} cumulative")
    print("Running FAMILY 6b (day-of-week, tradeable)...")
    rows += family6b_day_of_week(frames, meta)
    print(f"  {len(rows)} cumulative")

    df = pd.DataFrame(rows)
    print(f"\n{len(df)} strategy configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"].copy()
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"].copy()
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        survivors["rare(<10/yr)"] = survivors["trades_yr"] < 10
        print(survivors[["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "trades_yr", "rare(<10/yr)"]]
              .sort_values("va_exp", ascending=False)
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "symbol", "tf", "tr_n", "tr_exp", "va_n", "va_exp", "trades_yr"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nFull results table (train+val, full costs, test sealed):")
    cols = ["family", "config", "symbol", "tf", "stop%", "target%", "tr_n", "tr_exp",
            "tr_win%", "tr_dd%", "va_n", "va_exp", "va_win%", "va_dd%", "trades_yr", "verdict"]
    with pd.option_context("display.max_rows", None):
        print(df.sort_values(["family", "symbol", "tr_exp"], ascending=[True, True, False])[cols]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("FAMILY 1d — LAST-HOUR DRIFT AUDIT (report-only, SPY+ES 1h, test sealed)")
    print("=" * 78)
    audit_rows = family1d_lasthour_drift(frames, meta)
    audit_df = pd.DataFrame(audit_rows)
    print(audit_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    # full table CSV: main gauntlet rows + the audit rows appended (columns
    # unioned, NaN where a schema doesn't apply) — nothing omitted.
    audit_csv = audit_df.rename(columns={"n": "tr_n"}).copy()
    audit_csv["family"] = "1d-lasthour-drift-AUDIT"
    audit_csv["tf"] = "1h"
    audit_csv["verdict"] = "AUDIT-ONLY"
    full_csv = pd.concat([df, audit_csv], ignore_index=True, sort=False)
    full_csv.to_csv("step77_full_table.csv", index=False)
    print(f"\nFull table ({len(full_csv)} rows incl. audit) written to step77_full_table.csv")

    print("\nDone. No sealed-test window was ever sliced or scored above.")
    return df, audit_df


if __name__ == "__main__":
    main()
