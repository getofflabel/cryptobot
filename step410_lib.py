"""
step410_lib.py - ROUND 410 shared machinery.

Research only. Nothing in here places an order or touches a live file.

WHAT IS IN HERE
  - loading Alpaca daily and 5-minute bars, regular hours only
  - the 60 / 20 / 40 ... no: 60 / 20 / 20 split, in time, on bars
  - two swing-point definitions (our fractal, and the two-candle one)
  - a single-position long-only engine that enters on the next open with a
    market order, exits on the next open when the exit rule fires, and
    exits at a stop placed at chart structure
  - the coin-flip control: the SAME engine, the SAME exit rule, the SAME
    stop rule, the SAME number of trades, but entry moments drawn at
    random. If a strategy cannot beat that, the entry rule is not picking
    anything and the money was coming from the exit riding a rising
    market.

UNITS, ALWAYS STATED
  Everything called a "%" in here is a PRICE move - how far the price
  travelled - not a change in the value of a position. Position value
  moves by the price move times the leverage. Leverage is an OUTPUT of
  the sizing rule (dollars risked divided by the stop distance), never an
  input.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step41_shorts import confirmed_swings

REPO = "/Users/wallacechen/cryptobot"
NY = "America/New_York"

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8


# ------------------------------------------------------------------ data
def load_daily(symbol: str) -> pd.DataFrame:
    d = pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_1d.parquet")
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    d["et"] = d["timestamp"].dt.tz_convert(NY)
    d["date"] = d["et"].dt.date
    return d


def load_5m_rth(symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (all bars incl. extended hours, regular-hours-only bars)."""
    d = pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_5m.parquet")
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    et = d["timestamp"].dt.tz_convert(NY)
    d["et"] = et
    d["date"] = et.dt.date
    d["mins"] = et.dt.hour * 60 + et.dt.minute
    # a bar stamped 09:30 covers 09:30-09:35; 15:55 is the last one that
    # closes at 16:00. Alpaca rejects market orders outside these hours.
    rth = d[(d["mins"] >= 570) & (d["mins"] <= 955)].reset_index(drop=True)
    return d, rth


def split_60_20_20(n: int) -> tuple[int, int]:
    """Index of the first validation bar and the first sealed-test bar."""
    return int(n * 0.60), int(n * 0.80)


def costs_table() -> dict:
    t = pd.read_csv(f"{REPO}/step410_table_costs.csv")
    return {r.symbol: dict(med=r.med_quoted_spread_pct, p75=r.p75_quoted_spread_pct)
            for r in t.itertuples()}


# ------------------------------------------------- swing point definitions
def tjr_swings(d: pd.DataFrame):
    """The two-candle swing from step301_tjr_rules.md 2.1.

    Swing HIGH = an up candle then a down candle; the level is the higher
    of the two highs. Swing LOW = a down candle then an up candle; the
    level is the lower of the two lows. Known one bar after the pivot, so
    it is stamped at bar t and uses nothing after bar t.
    """
    o = d["open"].to_numpy(); h = d["high"].to_numpy()
    l = d["low"].to_numpy();  c = d["close"].to_numpy()
    up, dn = c > o, c < o
    n = len(d)
    sh = np.full(n, np.nan); sl = np.full(n, np.nan)
    is_h = up[:-1] & dn[1:]
    is_l = dn[:-1] & up[1:]
    sh[1:] = np.where(is_h, np.maximum(h[:-1], h[1:]), np.nan)
    sl[1:] = np.where(is_l, np.minimum(l[:-1], l[1:]), np.nan)
    return pd.Series(sh, index=d.index), pd.Series(sl, index=d.index)


def last_below(level_series, ref_price, session=None):
    """At each bar t, the most recent CONFIRMED level strictly below the
    reference price. Walks backwards, so a swing low that now sits ABOVE
    price is skipped and an older, lower one is used - which is what a
    real stop has to do. If `session` is given, only levels stamped in the
    same session count."""
    lv = np.asarray(level_series, dtype=float)
    ref = np.asarray(ref_price, dtype=float)
    sess = None if session is None else np.asarray(session)
    n = len(lv)
    out = np.full(n, np.nan); ago = np.full(n, np.nan)
    hist_p, hist_i = [], []
    for t in range(n):
        p = ref[t]
        for j in range(len(hist_p) - 1, -1, -1):
            if sess is not None and sess[hist_i[j]] != sess[t]:
                break
            if hist_p[j] < p:
                out[t] = hist_p[j]; ago[t] = t - hist_i[j]
                break
        if not np.isnan(lv[t]):
            hist_p.append(lv[t]); hist_i.append(t)
            if len(hist_p) > 400:
                hist_p = hist_p[-400:]; hist_i = hist_i[-400:]
    return out, ago


def last_above(level_series, ref_price, session=None):
    lv = np.asarray(level_series, dtype=float)
    ref = np.asarray(ref_price, dtype=float)
    sess = None if session is None else np.asarray(session)
    n = len(lv)
    out = np.full(n, np.nan); ago = np.full(n, np.nan)
    hist_p, hist_i = [], []
    for t in range(n):
        p = ref[t]
        for j in range(len(hist_p) - 1, -1, -1):
            if sess is not None and sess[hist_i[j]] != sess[t]:
                break
            if hist_p[j] > p:
                out[t] = hist_p[j]; ago[t] = t - hist_i[j]
                break
        if not np.isnan(lv[t]):
            hist_p.append(lv[t]); hist_i.append(t)
            if len(hist_p) > 400:
                hist_p = hist_p[-400:]; hist_i = hist_i[-400:]
    return out, ago


# ------------------------------------------------------------- the engine
def run_long_engine(d: pd.DataFrame,
                    enter: np.ndarray,
                    exit_sig: np.ndarray,
                    stop_level: np.ndarray | None,
                    cost_pct: float,
                    lo: int, hi: int,
                    max_hold: int | None = None) -> pd.DataFrame:
    """One position at a time, long only.

    enter[t]     - the entry rule fired on the CLOSE of bar t.
                   The market order goes in at the OPEN of bar t+1.
    exit_sig[t]  - the exit rule fired on the CLOSE of bar t.
                   The market order goes out at the OPEN of bar t+1.
    stop_level[t]- where the stop sits for a trade signalled at bar t.
                   NaN means no valid structure was available, and the
                   trade is SKIPPED rather than given an invented stop.
                   Pass None for a no-stop run.
    cost_pct     - the whole round trip, as a percentage of price. Half is
                   charged on the way in and half on the way out.

    Gap honesty: if a bar OPENS at or below the stop, the fill is the
    open, not the stop price. A real stop order cannot do better than the
    price the market reopens at.

    Only bars in [lo, hi) can start a trade; a trade that starts inside
    the window is allowed to finish outside it (that is what a real
    position does) but never past the end of the data.
    """
    o = d["open"].to_numpy(); h = d["high"].to_numpy()
    l = d["low"].to_numpy();  c = d["close"].to_numpy()
    n = len(d)
    half = cost_pct / 2.0 / 100.0
    trades = []
    t = lo
    while t < hi:
        if not enter[t]:
            t += 1
            continue
        i_in = t + 1                       # the bar the market order fills on
        if i_in >= n:
            break
        stop = np.nan if stop_level is None else stop_level[t]
        if stop_level is not None and (np.isnan(stop) or stop >= o[i_in]):
            t += 1                         # no usable structure below entry
            continue
        entry_px = o[i_in] * (1 + half)    # a buy market order lifts the ask
        # walk forward
        j = i_in
        exit_px = None; reason = None; i_out = None
        while j < n:
            if stop_level is not None:
                if o[j] <= stop:                        # gapped through it
                    exit_px = o[j] * (1 - half); reason = "stop-gap"; i_out = j
                    break
                if l[j] <= stop:
                    exit_px = stop * (1 - half); reason = "stop"; i_out = j
                    break
            if max_hold is not None and (j - i_in) >= max_hold:
                k = min(j + 1, n - 1)
                exit_px = o[k] * (1 - half); reason = "time"; i_out = k
                break
            if exit_sig[j] and j > i_in - 1:
                k = j + 1
                if k >= n:
                    exit_px = c[n - 1] * (1 - half); reason = "eod-data"; i_out = n - 1
                    break
                exit_px = o[k] * (1 - half); reason = "signal"; i_out = k
                break
            j += 1
        if exit_px is None:
            exit_px = c[n - 1] * (1 - half); reason = "eod-data"; i_out = n - 1

        ret_pct = (exit_px / entry_px - 1.0) * 100.0
        stop_dist = np.nan if stop_level is None else (o[i_in] - stop) / o[i_in] * 100.0
        r_mult = np.nan
        if stop_level is not None and stop_dist and stop_dist > 0:
            r_mult = ret_pct / stop_dist
        trades.append(dict(sig_idx=t, in_idx=i_in, out_idx=i_out,
                           entry=entry_px, exit=exit_px, ret_pct=ret_pct,
                           bars_held=i_out - i_in, reason=reason,
                           stop=stop, stop_dist_pct=stop_dist, r=r_mult,
                           in_ts=d["timestamp"].iloc[i_in]))
        t = i_out + 1                       # single position: no overlap
    return pd.DataFrame(trades)


# ------------------------------------------------------- the coin flip
def coin_flip_control(d, exit_sig, stop_level, cost_pct, lo, hi,
                      n_trades_target, n_runs=2000, seed=7,
                      max_hold=None, rng=None, eligible_mask=None):
    """Same engine, same exit, same stop, same direction, same number of
    trades - entry moments chosen at random.

    Entry bars are drawn without replacement from the eligible window.
    The engine still enforces one position at a time, so a draw that lands
    inside an open trade is simply skipped; we over-draw and then take the
    first n_trades_target trades so the trade COUNT matches the real run.

    eligible_mask - restricts which bars a random entry may land on. This
    matters enormously. A random entry dropped anywhere at all often lands
    on a bar where the exit rule ALREADY says get out, so the fake trade
    lasts one bar and earns nothing. That makes the comparison a
    time-in-market comparison rather than an entry-timing comparison. Pass
    the mask "the exit rule is not currently firing" to make the two
    populations comparable, and read the per-bar numbers, not just the
    per-trade ones.

    Returns arrays of mean per-trade returns and mean per-BAR-HELD
    returns, one per run, in percent of price after costs.
    """
    rng = rng or np.random.default_rng(seed)
    eligible = np.arange(lo, hi)
    if stop_level is not None:
        eligible = eligible[~np.isnan(stop_level[lo:hi])]
    if eligible_mask is not None:
        eligible = eligible[eligible_mask[eligible]]
    means, perbar, wins, holds, counts = [], [], [], [], []
    empty = dict(mean=np.array([]), perbar=np.array([]), win=np.array([]),
                 hold=np.array([]), count=np.array([]))
    if len(eligible) < 10 or n_trades_target < 1:
        return empty
    draw = min(len(eligible), max(n_trades_target * 6, n_trades_target + 20))
    for _ in range(n_runs):
        picks = rng.choice(eligible, size=draw, replace=False)
        ent = np.zeros(len(d), dtype=bool)
        ent[picks] = True
        tr = run_long_engine(d, ent, exit_sig, stop_level, cost_pct, lo, hi,
                             max_hold=max_hold)
        if len(tr) == 0:
            continue
        tr = tr.iloc[:n_trades_target]
        held = tr["bars_held"].clip(lower=1)
        means.append(tr["ret_pct"].mean())
        perbar.append(tr["ret_pct"].sum() / held.sum())
        wins.append((tr["ret_pct"] > 0).mean() * 100.0)
        holds.append(tr["bars_held"].mean())
        counts.append(len(tr))
    return dict(mean=np.array(means), perbar=np.array(perbar),
                win=np.array(wins), hold=np.array(holds),
                count=np.array(counts))


def percentile_of(value, dist):
    if len(dist) == 0:
        return np.nan
    return 100.0 * (dist < value).mean()


def tstat(x):
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 3 or x.std(ddof=1) == 0:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def summarise(tr: pd.DataFrame, cost_pct: float) -> dict:
    if len(tr) == 0:
        return dict(n=0)
    r = tr["ret_pct"].to_numpy()
    held = tr["bars_held"].clip(lower=1).to_numpy()
    return dict(
        n=len(tr),
        mean_pct=r.mean(),
        perbar_pct=r.sum() / held.sum(),
        bars_in=int(held.sum()),
        med_pct=np.median(r),
        t=tstat(r),
        win_pct=(r > 0).mean() * 100.0,
        total_pct=r.sum(),
        mean_hold=tr["bars_held"].mean(),
        thickness=r.mean() / cost_pct if cost_pct else np.nan,
        mean_stop_pct=np.nanmean(tr["stop_dist_pct"]),
        mean_r=np.nanmean(tr["r"]),
        stopped_pct=100.0 * tr["reason"].str.startswith("stop").mean(),
    )


def fmt_summary(s: dict) -> str:
    if s.get("n", 0) == 0:
        return "no trades"
    return (f"n={s['n']:>4}  mean {s['mean_pct']:+.3f}% of price/trade  "
            f"t={s['t']:>5.2f}  win {s['win_pct']:.1f}%  "
            f"hold {s['mean_hold']:.1f} bars  "
            f"thickness {s['thickness']:.1f}x cost")
