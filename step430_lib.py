"""
step430_lib.py - ROUND 430 shared machinery (liquidity-sweep framework).

RESEARCH ONLY. Nothing in here places an order or touches a live file.

UNITS
  Every "%" in this file is a PRICE move - how far the price travelled -
  unless the name says otherwise. It is never a change in the value of a
  position. Position value moves by the price move times the leverage,
  and leverage is an OUTPUT of (dollars risked / stop distance).

COSTS
  Round-trip cost, no commission, measured from real quoted spreads in
  round 410 (step410_table_costs.csv). We charge the p75 (worse than
  typical) number, half on the way in and half on the way out.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")

REPO = "/Users/wallacechen/cryptobot"
NY = "America/New_York"

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8


# ----------------------------------------------------------------- loading
def load_5m(symbol: str, source: str = "alpaca") -> pd.DataFrame:
    if source == "alpaca":
        path = f"{REPO}/data_alpaca_{symbol}_5m.parquet"
    else:
        path = f"{REPO}/data_bybit_{symbol}_5m_full.parquet"
    d = pd.read_parquet(path)
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = (d.sort_values("timestamp").drop_duplicates("timestamp")
           .reset_index(drop=True))
    et = d["timestamp"].dt.tz_convert(NY)
    d["et"] = et
    d["date"] = et.dt.date
    d["mins"] = et.dt.hour * 60 + et.dt.minute
    return d


def split_60_20_20(n: int) -> tuple[int, int]:
    """First validation bar index, first final-untouched-slice bar index."""
    return int(n * 0.60), int(n * 0.80)


def costs_table() -> dict:
    t = pd.read_csv(f"{REPO}/step410_table_costs.csv")
    return {r.symbol: dict(med=r.med_quoted_spread_pct,
                           p75=r.p75_quoted_spread_pct)
            for r in t.itertuples()}


# ------------------------------------------------------------ swing points
def tjr_swings(d: pd.DataFrame):
    """TJR's two-candle swing.

    HIGH = an up candle then a down candle; the level is the HIGHER of the
    two highs.  LOW = a down candle then an up candle; the level is the
    LOWER of the two lows.  Stamped at the SECOND candle, so it is known
    at the close of that bar and uses nothing after it.
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
    return sh, sl


def fractal_swings(d: pd.DataFrame, k: int = 3):
    """Our own k-bar fractal, aligned so the value stamped at bar t refers
    to a pivot at t-k confirmed with data through t only."""
    h, l = d["high"], d["low"]
    is_sh = (h == h.rolling(2 * k + 1, center=True).max())
    is_sl = (l == l.rolling(2 * k + 1, center=True).min())
    sh_conf = is_sh.shift(k).astype("boolean").fillna(False).astype(bool)
    sl_conf = is_sl.shift(k).astype("boolean").fillna(False).astype(bool)
    return (h.shift(k).where(sh_conf).to_numpy(),
            l.shift(k).where(sl_conf).to_numpy())


# ------------------------------------------------- higher-timeframe levels
def htf_swing_levels(d5: pd.DataFrame, minutes: int):
    """TJR two-candle swing levels built on a `minutes`-bar chart, then
    mapped back onto the 5-minute index.

    Returns two float arrays the length of d5.  Position t holds the level
    stamped by the HTF bar that had ALREADY CLOSED at or before the close
    of 5m bar t, with the extra one-bar delay the two-candle rule needs.
    No value at t uses information from after the close of bar t.
    """
    g = d5.set_index("timestamp")
    agg = g.resample(f"{minutes}min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"), close=("close", "last"))
    agg = agg.dropna()
    sh, sl = tjr_swings(agg.reset_index())
    # The HTF bar starting at T closes at T+minutes; a swing stamped on it
    # is knowable only from T+minutes onward.
    close_ts = agg.index + pd.Timedelta(minutes=minutes)
    lev = pd.DataFrame({"sh": sh, "sl": sl}, index=close_ts)
    # forward-fill onto the 5m grid, strictly at-or-before the 5m bar close
    b5_close = d5["timestamp"] + pd.Timedelta(minutes=5)
    idx = np.searchsorted(close_ts.values, b5_close.values, side="right") - 1
    out_h = np.full(len(d5), np.nan)
    out_l = np.full(len(d5), np.nan)
    shv, slv = lev["sh"].to_numpy(), lev["sl"].to_numpy()
    return shv, slv, idx, close_ts


def htf_new_levels(d5: pd.DataFrame, minutes: int):
    """Per 5-minute bar, the higher-timeframe swing level that BECAME
    KNOWN at the close of that bar (NaN when none did).

    A `minutes`-bar starting at T closes at T+minutes.  The two-candle
    rule stamps the swing on the SECOND bar, so the level is knowable only
    once that second bar has closed.  Nothing here uses a price printed
    after the 5-minute bar it is stamped on.
    """
    g = d5.set_index("timestamp")
    agg = (g.resample(f"{minutes}min", label="left", closed="left")
             .agg(open=("open", "first"), high=("high", "max"),
                  low=("low", "min"), close=("close", "last"))
             .dropna())
    sh, sl = tjr_swings(agg.reset_index())
    known_at = agg.index + pd.Timedelta(minutes=minutes)   # HTF bar close
    b5_close = d5["timestamp"] + pd.Timedelta(minutes=5)   # 5m bar close
    pos = np.searchsorted(b5_close.values, known_at.values, side="left")
    out_h = np.full(len(d5), np.nan)
    out_l = np.full(len(d5), np.nan)
    ok = (pos < len(d5))
    ph, pl = pos[ok], pos[ok]
    vh, vl = sh[ok], sl[ok]
    mh = ~np.isnan(vh); ml = ~np.isnan(vl)
    out_h[ph[mh]] = vh[mh]
    out_l[pl[ml]] = vl[ml]
    return out_h, out_l


# ------------------------------------------------------- sweeps + confirm
def scan_sweeps(d: pd.DataFrame, new_high, new_low,
                sweep_window: int = 12, max_active: int = 40):
    """Find completed SWEEPS of higher-timeframe levels.

    A sweep of a LOW: price trades through a prior unswept swing low
    (some bar's low < L) and then CLOSES back above it within
    sweep_window bars.  The sweep extreme is the lowest low reached while
    it was through.  A level that is pierced and does NOT close back above
    inside the window is simply broken - trend continuation, no setup -
    and is retired.

    Mirror for a HIGH.

    Returns a DataFrame: s (bar the sweep COMPLETED on, i.e. the close
    that came back), side (+1 long setup after a low sweep, -1 short
    setup after a high sweep), level, extreme, pierce_bar.
    """
    hi = d["high"].to_numpy(); lo = d["low"].to_numpy()
    cl = d["close"].to_numpy()
    n = len(d)
    live_lo, live_hi = [], []       # unswept levels: [price]
    pierce_lo, pierce_hi = {}, {}   # level -> [pierce_bar, running extreme]
    out = []
    for t in range(n):
        # ---- levels already through get resolved first
        for L in list(pierce_lo):
            st = pierce_lo[L]
            st[1] = min(st[1], lo[t])
            if cl[t] > L:
                out.append(dict(s=t, side=1, level=L, extreme=st[1],
                                pierce_bar=st[0]))
                del pierce_lo[L]
            elif t - st[0] >= sweep_window:
                del pierce_lo[L]                    # broken, not swept
        for L in list(pierce_hi):
            st = pierce_hi[L]
            st[1] = max(st[1], hi[t])
            if cl[t] < L:
                out.append(dict(s=t, side=-1, level=L, extreme=st[1],
                                pierce_bar=st[0]))
                del pierce_hi[L]
            elif t - st[0] >= sweep_window:
                del pierce_hi[L]
        # ---- new pierces on this bar (nearest level only, to avoid
        #      counting one flush as five separate setups)
        pierced = [L for L in live_lo if lo[t] < L]
        if pierced:
            for L in pierced:
                live_lo.remove(L)
            L = max(pierced)                        # the nearest one below
            if cl[t] > L:
                out.append(dict(s=t, side=1, level=L, extreme=lo[t],
                                pierce_bar=t))
            else:
                pierce_lo[L] = [t, lo[t]]
        pierced = [L for L in live_hi if hi[t] > L]
        if pierced:
            for L in pierced:
                live_hi.remove(L)
            L = min(pierced)
            if cl[t] < L:
                out.append(dict(s=t, side=-1, level=L, extreme=hi[t],
                                pierce_bar=t))
            else:
                pierce_hi[L] = [t, hi[t]]
        # ---- levels that became known at THIS bar's close join the pool
        v = new_low[t]
        if not np.isnan(v) and v < cl[t]:
            live_lo.append(v)
            if len(live_lo) > max_active:
                live_lo = sorted(live_lo)[-max_active:]
        v = new_high[t]
        if not np.isnan(v) and v > cl[t]:
            live_hi.append(v)
            if len(live_hi) > max_active:
                live_hi = sorted(live_hi)[:max_active]
    return pd.DataFrame(out)


def scan_confirm(d: pd.DataFrame, sweeps: pd.DataFrame,
                 sh5, sl5, conf_window: int = 24):
    """TJR's load-bearing rule: the sweep is only the OPPORTUNITY.  The
    trade needs proof the opposite trend actually formed.

    After a LOW is swept at bar s with extreme m:
      1. wait for a two-candle swing LOW stamped after s whose level is
         ABOVE m           -> "a higher low"
      2. then wait for a CLOSE above the highest swing high stamped
         between the sweep and that higher low   -> "a higher high"
      Signal on that close; the order fills at the next open.
    If price prints a new low under m at any point first, the reversal did
    not form and the setup is abandoned.  Mirror for a swept high.

    Everything read at bar j comes from bars <= j.
    """
    hi = d["high"].to_numpy(); lo = d["low"].to_numpy()
    cl = d["close"].to_numpy()
    n = len(d)
    rows = []
    for r in sweeps.itertuples():
        s, side, m = int(r.s), int(r.side), float(r.extreme)
        found_hl = False
        ref = np.nan
        best_pivot = -np.inf if side > 0 else np.inf
        run_ext = -np.inf if side > 0 else np.inf
        j = s + 1
        while j < n and (j - s) <= conf_window:
            if side > 0:
                if lo[j] < m:
                    break                       # made a lower low, dead
                run_ext = max(run_ext, hi[j])
                if not np.isnan(sh5[j]):
                    best_pivot = max(best_pivot, sh5[j])
                if not found_hl:
                    if not np.isnan(sl5[j]) and sl5[j] > m:
                        found_hl = True
                        ref = (best_pivot if np.isfinite(best_pivot)
                               else run_ext)
                elif cl[j] > ref:
                    rows.append(dict(sig_idx=j, side=1, stop=m,
                                     sweep_bar=s, level=r.level,
                                     extreme=m, wait=j - s))
                    break
            else:
                if hi[j] > m:
                    break
                run_ext = min(run_ext, lo[j])
                if not np.isnan(sl5[j]):
                    best_pivot = min(best_pivot, sl5[j])
                if not found_hl:
                    if not np.isnan(sh5[j]) and sh5[j] < m:
                        found_hl = True
                        ref = (best_pivot if np.isfinite(best_pivot)
                               else run_ext)
                elif cl[j] < ref:
                    rows.append(dict(sig_idx=j, side=-1, stop=m,
                                     sweep_bar=s, level=r.level,
                                     extreme=m, wait=j - s))
                    break
            j += 1
    return pd.DataFrame(rows)


def add_target(ev: pd.DataFrame, d: pd.DataFrame, r_mult: float):
    """Target price at r_mult times the distance from the NEXT OPEN (the
    real fill) to the stop.  The stop is chart structure; the target is
    the thing test 4 tries to replace with a level from the chart."""
    o = d["open"].to_numpy()
    ev = ev.copy()
    i_in = np.minimum(ev["sig_idx"].to_numpy() + 1, len(o) - 1)
    fill = o[i_in]
    dist = np.abs(fill - ev["stop"].to_numpy())
    ev["target"] = fill + ev["side"].to_numpy() * r_mult * dist
    ev["fill_ref"] = fill
    ev["risk_pct"] = dist / fill * 100.0
    return ev


def random_control(d: pd.DataFrame, real: pd.DataFrame, cost_pct: float,
                   r_mult: float, max_hold: int, lo: int, hi: int,
                   n_runs: int = 400, seed: int = 430,
                   single_position: bool = True, eligible=None):
    """The same engine, the same exit, the same stop DISTANCES, the same
    number of trades and the same mix of long and short - entry moments
    drawn at random.  If the sweep-and-confirm rule cannot beat this, the
    entry rule is not picking anything.

    Stop distances are RESAMPLED from the real trades, so the two
    populations risk the same amount per trade and the only difference
    left is WHEN they entered.
    """
    rng = np.random.default_rng(seed)
    o = d["open"].to_numpy()
    n_t = len(real)
    if n_t < 5:
        return dict(mean=np.array([]), win=np.array([]), total=np.array([]))
    dists = real["stop_dist_pct"].to_numpy()
    sides = real["side"].to_numpy()
    means, wins, totals = [], [], []
    for _ in range(n_runs):
        picks = rng.integers(lo, hi, size=n_t * 4)
        picks = np.unique(picks)
        rng.shuffle(picks)
        k = len(picks)
        dd = rng.choice(dists, size=k, replace=True)
        ss = rng.choice(sides, size=k, replace=True)
        fill = o[np.minimum(picks + 1, len(o) - 1)]
        stop = fill * (1 - ss * dd / 100.0)
        tgt = fill * (1 + ss * r_mult * dd / 100.0)
        ev = pd.DataFrame(dict(sig_idx=picks, side=ss, stop=stop,
                               target=tgt))
        tr = run_engine(d, ev, cost_pct, max_hold,
                        single_position=single_position)
        if len(tr) == 0:
            continue
        tr = tr.iloc[:n_t]
        means.append(tr["ret_pct"].mean())
        wins.append((tr["ret_pct"] > 0).mean() * 100.0)
        totals.append(tr["ret_pct"].sum())
    return dict(mean=np.array(means), win=np.array(wins),
                total=np.array(totals))


def percentile_of(value, dist):
    if len(dist) == 0:
        return np.nan
    return 100.0 * (np.asarray(dist) < value).mean()


# ------------------------------------------------------------ the sessions
def tag_sessions(d: pd.DataFrame) -> pd.DataFrame:
    """New-York-clock sessions, exactly as the framework states them:
       Asia   18:00-03:00, London 03:00-08:30, New York 09:30-17:00.
    A session label plus a 'session day' so the Asia session that starts
    at 18:00 belongs to the NEXT calendar day's trading day.
    """
    m = d["mins"].to_numpy()
    sess = np.full(len(d), "none", dtype=object)
    sess[(m >= 1080) | (m < 180)] = "asia"        # 18:00-03:00
    sess[(m >= 180) & (m < 510)] = "london"       # 03:00-08:30
    sess[(m >= 570) & (m < 1020)] = "ny"          # 09:30-17:00
    d = d.copy()
    d["sess"] = sess
    # session-day: everything from 18:00 belongs to the next day
    sd = pd.Series(d["date"].values, index=d.index)
    roll = d["mins"].to_numpy() >= 1080
    sd = pd.to_datetime(pd.Series(d["date"].astype(str).values))
    sd = sd + pd.to_timedelta(np.where(roll, 1, 0), unit="D")
    d["sday"] = sd.dt.date.values
    return d


# ------------------------------------------------------------- the engine
def run_engine(d: pd.DataFrame,
               events: pd.DataFrame,
               cost_pct: float,
               max_hold: int,
               single_position: bool = True) -> pd.DataFrame:
    """One trade list in, one result list out.

    `events` must carry, per row:
        sig_idx  - bar whose CLOSE produced the signal
        side     - +1 long, -1 short
        stop     - the stop PRICE (chart structure; never a fixed %)
        target   - the target PRICE, or NaN for no target
    Entry fills at the OPEN of sig_idx+1.  Half the round-trip cost is
    charged on the way in and half on the way out, in the direction that
    hurts.

    Gap honesty: if a bar opens beyond the stop, the fill is the open.
    If a bar's range contains both the stop and the target we assume the
    STOP filled first (the pessimistic reading).

    single_position=True walks the list in time order and skips any signal
    that fires while a trade is open.  False measures every event on its
    own, which is what a like-for-like partition needs.
    """
    o = d["open"].to_numpy(); h = d["high"].to_numpy()
    l = d["low"].to_numpy();  c = d["close"].to_numpy()
    ts = d["timestamp"].to_numpy()
    n = len(d)
    if len(events) == 0:
        return pd.DataFrame()
    half = cost_pct / 2.0 / 100.0
    ev = events.sort_values("sig_idx").reset_index(drop=True)
    sig = ev["sig_idx"].to_numpy().astype(np.int64)
    side = ev["side"].to_numpy().astype(np.int64)
    stop = ev["stop"].to_numpy().astype(float)
    tgt = (ev["target"].to_numpy().astype(float) if "target" in ev
           else np.full(len(ev), np.nan))
    i_in = sig + 1
    keep = (i_in < n) & ~np.isnan(stop)
    px_open = np.where(keep, o[np.minimum(i_in, n - 1)], np.nan)
    keep &= np.where(side > 0, stop < px_open, stop > px_open)
    if not keep.any():
        return pd.DataFrame()
    sig, side, stop, tgt, i_in = (sig[keep], side[keep], stop[keep],
                                  tgt[keep], i_in[keep])
    px_open = px_open[keep]

    # ---- resolve every trade's exit independently, in one shot.
    # The exit of a trade depends only on its own entry, so this is exactly
    # what the bar-by-bar walk produced, just without the Python loop.
    W = i_in[:, None] + np.arange(max_hold + 1)[None, :]
    valid = W < n
    Wc = np.minimum(W, n - 1)
    o_w, h_w, l_w = o[Wc], h[Wc], l[Wc]
    sd = side[:, None]
    st = stop[:, None]
    tg = tgt[:, None]
    BIG = max_hold + 10
    long_ = sd > 0
    stop_gap = np.where(long_, o_w <= st, o_w >= st) & valid
    stop_touch = np.where(long_, l_w <= st, h_w >= st) & valid
    has_t = ~np.isnan(tgt)[:, None]
    tgt_gap = has_t & np.where(long_, o_w >= tg, o_w <= tg) & valid
    tgt_touch = has_t & np.where(long_, h_w >= tg, l_w <= tg) & valid
    any_stop = stop_gap | stop_touch
    any_tgt = tgt_gap | tgt_touch
    f_stop = np.where(any_stop.any(1), any_stop.argmax(1), BIG)
    f_tgt = np.where(any_tgt.any(1), any_tgt.argmax(1), BIG)
    # a bar holding both is read pessimistically: the stop filled first
    k = np.minimum(f_stop, f_tgt)
    last_valid = valid.sum(1) - 1
    timed = k >= BIG
    k_eff = np.where(timed, last_valid, k)
    rows_i = np.arange(len(k_eff))
    # a trade that never hits either level is closed with a market order at
    # the NEXT open after the holding limit - the same next-open convention
    # every other fill in here uses.
    i_out = np.where(timed,
                     np.minimum(i_in + last_valid + 1, n - 1),
                     np.minimum(i_in + k_eff, n - 1))
    is_stop = (~timed) & (f_stop <= f_tgt)
    gap_s = stop_gap[rows_i, k_eff]
    gap_t = tgt_gap[rows_i, k_eff]
    exit_px = np.where(
        timed, o[i_out],
        np.where(is_stop,
                 np.where(gap_s, o[i_out], stop),
                 np.where(gap_t, o[i_out], tgt)))
    reason = np.where(timed, "time",
                      np.where(is_stop,
                               np.where(gap_s, "stop-gap", "stop"),
                               np.where(gap_t, "target-gap", "target")))
    entry = px_open * (1 + half * side)
    exit_fill = exit_px * (1 - half * side)
    ret = (exit_fill / entry - 1.0) * 100.0 * side
    stop_dist = np.abs(px_open - stop) / px_open * 100.0

    if single_position:
        # one position at a time: walk the list once and drop any signal
        # that fires while a trade is still open.
        take = np.zeros(len(sig), dtype=bool)
        busy = -1
        for i in range(len(sig)):
            if sig[i] <= busy:
                continue
            take[i] = True
            busy = i_out[i]
    else:
        take = np.ones(len(sig), dtype=bool)

    return pd.DataFrame(dict(
        sig_idx=sig[take], in_idx=i_in[take], out_idx=i_out[take],
        side=side[take], entry=entry[take], exit=exit_fill[take],
        ret_pct=ret[take], bars_held=(i_out - i_in)[take],
        reason=reason[take], stop_dist_pct=stop_dist[take],
        r=np.where(stop_dist[take] > 0, ret[take] / stop_dist[take], np.nan),
        in_ts=ts[i_in[take]]))


# ------------------------------------------------------------- statistics
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
    return dict(n=len(tr), mean_pct=r.mean(), med_pct=float(np.median(r)),
                perbar_pct=r.sum() / held.sum(), t=tstat(r),
                win_pct=(r > 0).mean() * 100.0, total_pct=r.sum(),
                mean_hold=float(tr["bars_held"].mean()),
                thickness=r.mean() / cost_pct if cost_pct else np.nan,
                mean_stop_pct=float(np.nanmean(tr["stop_dist_pct"])),
                mean_r=float(np.nanmean(tr["r"])))


def fmt(s: dict) -> str:
    if s.get("n", 0) == 0:
        return "no trades"
    return (f"n={s['n']:>5}  mean {s['mean_pct']:+.4f}% of price/trade  "
            f"t={s['t']:>5.2f}  win {s['win_pct']:4.1f}%  "
            f"hold {s['mean_hold']:5.1f} bars  "
            f"{s['thickness']:6.1f}x the round trip")


def wilson(k, n, z=1.96):
    """Confidence interval for a proportion, so a frequency claim comes
    with the range luck alone allows."""
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    ctr = (p + z * z / (2 * n)) / den
    rad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (ctr - rad, ctr + rad)
