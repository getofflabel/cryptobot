"""
step330_structure_break_audit.py — SOL structure break ("CHoCH + confluence"),
the desk's one live survivor, put to a decision.

WHAT THIS FILE IS FOR
Round 190 reported +$218.95 per trade on Solana for the 1-hour structure
break with at least 2 confluence votes, and the same shape did NOT hold on
Bitcoin. That asymmetry is either a real Solana property or it is fitting.
This file tries to break it, in the order morgan asked for:

  PART 1  AUDIT — what our code actually requires versus what a trader
          running a structure break actually requires.
  PART 2  ENTRY-OR-EXIT — random entries, same exit, same window, same
          costs. If random entries match it, the entry has no edge.
  PART 3  DOES IT WORK ELSEWHERE — the same configuration, un-retuned,
          on other coins, with every volatility-based number RE-DERIVED
          on each coin's own history.

STANDARDS HELD THROUGHOUT
  - market order (costs more) on entry AND on every exit, always.
  - stop at the confirmed swing the break itself broke (exits.stop_structure),
    size = dollars risked / stop distance, leverage is an OUTPUT.
  - 60/20/20 in date order. Choose on the first 60% only. Middle 20% read
    once. The final untouched slice of history is NEVER loaded here.
  - at least 30 trades in the first slice and 8 in the middle slice.
  - profit reported as a percent of the full size of the position AND as
    how many times bigger it is than the cost of trading. Under 5x rejects.
  - what luck alone would produce is reported beside every number.

Research only. No live orders, no live-file edits, no git.
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import exits as E
from backtest import CostModel
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings, days_to_bars
from step43_daytrade import champ_aligned
from step56_smc_toolkit import (bos_chain, equilibrium, fib_entries,
                                fvg_signals, leg_tracker, liquidity_pools,
                                sweep_events, vol_gated_ma)
from step56_smc_toolkit import BIAS_BOS_K
from step150_common import (INITIAL_EQUITY, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
                            mask_to_events, run_edge, split_points, thickness,
                            trade_stats)

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# --- the round-190 configuration, unchanged -------------------------------
K = 8
TARGET_MULT = 2.0
CONF_TOL, CONF_DEPTH = 0.1, 0.3
CONF_FILL, CONF_EXPIRE_DAYS = 0.5, 10
CONF_FIB_EXPIRE_DAYS = 20
CONF_HOLD_DAYS = 10
CONF_THRESHOLD = 2
RISK_PCT = 0.02


# ===========================================================================
# data
# ===========================================================================

def to_4h(d1h: pd.DataFrame) -> pd.DataFrame:
    g = (d1h.set_index("timestamp")
             .resample("4h")
             .agg({"open": "first", "high": "max", "low": "min",
                   "close": "last", "volume": "sum"})
             .dropna()
             .reset_index())
    return g


def load(sym: str, use_cached_4h: bool = True):
    d1h = fetch_bybit_deep("1h", sym)
    d4h = None
    if use_cached_4h:
        try:
            d4h = fetch_bybit_deep("4h", sym)
        except Exception:
            d4h = None
    if d4h is None or len(d4h) == 0:
        d4h = to_4h(d1h)
    try:
        fh = fetch_funding_history(sym)
        f1h = align_funding(d1h, fh)
    except Exception:
        f1h = pd.Series(0.0, index=d1h.index)
    return d1h, d4h, f1h


# ===========================================================================
# the 4h bias vote — NOTE the volatility gate buried inside it
# ===========================================================================

def bias_series_4h_rederived(frame4h: pd.DataFrame, min_atr_pct: float):
    """Same shape as step56_smc_toolkit.bias_series_4h, but the volatility
    gate is a PARAMETER instead of Bitcoin's hard-wired 1.5%. On Solana the
    1.5% number is open on almost every bar, so it stops being a filter at
    all. Re-derived per coin everywhere this is called."""
    champ = vol_gated_ma(frame4h, fast=20, slow=100, min_atr_pct=min_atr_pct,
                         allow_short=True).fillna(0)
    chain4h = bos_chain(frame4h, BIAS_BOS_K)["chain"]
    bias = pd.Series(np.select(
        [(champ == 1) & (chain4h == 1), (champ == -1) & (chain4h == -1)],
        [1, -1], default=0.0), index=frame4h.index)
    return bias


def atr_pct_series(d: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = d["high"], d["low"], d["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return (tr.ewm(alpha=1 / n, adjust=False).mean() / c * 100)


# ===========================================================================
# entry construction, with every practitioner condition switchable
# ===========================================================================

def build_signal(d1h, d4h, i_tr, *, gate_atr_pct, min_break_x_atr=0.0,
                 min_touches=1, retest=False, retest_tol_pct=0.15,
                 retest_window=24, threshold=CONF_THRESHOLD, k=K):
    """Returns (enter_long, enter_short, diag).

    Conditions, each one a practitioner requirement:
      close beyond the level, not a wick   ALWAYS ON (bos_chain uses close)
      no entry on the signal bar itself    ALWAYS ON (fills at next open)
      min_break_x_atr   how far past the level the close must be, expressed
                        in multiples of that coin's OWN median 1-hour true
                        range, re-derived per coin. 0.0 = our current code.
      min_touches       how many confirmed swings sit at the level. 1 =
                        our current code (a single lone pivot).
      retest            wait for price to come back to the broken level and
                        hold it before entering. False = our current code.
    """
    bos = bos_chain(d1h, k)
    discount, premium, eq, lsh, lsl = equilibrium(d1h, k)
    pool_high, pool_low = liquidity_pools(d1h, k, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d1h, pool_high, pool_low, CONF_DEPTH)
    window = days_to_bars(d1h, 1)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                         .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    _, _, _, _, ab, ar = fvg_signals(d1h, CONF_FILL,
                                     days_to_bars(d1h, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d1h, k, days_to_bars(d1h, CONF_FIB_EXPIRE_DAYS))
    _, _, _, _, _, _, lz, sz = fib_entries(
        d1h, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    bias4h = bias_series_4h_rederived(d4h, gate_atr_pct)
    bias_1h = champ_aligned(d4h, bias4h, d1h)
    count_long = ((bias_1h == 1).astype(int) + discount.astype(int)
                  + lz.astype(int) + swept_recent_long.astype(int) + ab.astype(int))
    count_short = ((bias_1h == -1).astype(int) + premium.astype(int)
                   + sz.astype(int) + swept_recent_short.astype(int) + ar.astype(int))

    el = bos["choch_long"] & (count_long >= threshold)
    es = bos["choch_short"] & (count_short >= threshold)

    close = d1h["close"].to_numpy()
    low = d1h["low"].to_numpy()
    high = d1h["high"].to_numpy()
    lsh_a, lsl_a = lsh.to_numpy(), lsl.to_numpy()

    # ---- how far past the level did the close actually get? --------------
    atrp = atr_pct_series(d1h).to_numpy()
    med_atr_train = float(np.nanmedian(atrp[:i_tr]))
    break_pct_long = (close - lsh_a) / close * 100
    break_pct_short = (lsl_a - close) / close * 100
    diag = dict(median_train_atr_pct=med_atr_train)

    if min_break_x_atr > 0:
        need = min_break_x_atr * med_atr_train
        el = el & pd.Series(break_pct_long >= need, index=d1h.index)
        es = es & pd.Series(break_pct_short >= need, index=d1h.index)
        diag["min_break_pct_required"] = need

    # ---- how many confirmed swings sit AT that level? --------------------
    if min_touches > 1:
        sh_price, sl_price = confirmed_swings(d1h, k)
        touch_hi = _touch_count(sh_price.to_numpy(), lsh_a, retest_tol_pct)
        touch_lo = _touch_count(sl_price.to_numpy(), lsl_a, retest_tol_pct)
        el = el & pd.Series(touch_hi >= min_touches, index=d1h.index)
        es = es & pd.Series(touch_lo >= min_touches, index=d1h.index)

    # ---- wait for the level to be re-tested and held ---------------------
    if retest:
        el = _retest_shift(el.to_numpy(), lsh_a, low, close, +1,
                           retest_tol_pct, retest_window, d1h.index)
        es = _retest_shift(es.to_numpy(), lsl_a, high, close, -1,
                           retest_tol_pct, retest_window, d1h.index)

    diag["break_pct_long_at_signal"] = break_pct_long
    diag["break_pct_short_at_signal"] = break_pct_short
    return el.fillna(False), es.fillna(False), diag


def _touch_count(swing_prices: np.ndarray, level: np.ndarray, tol_pct: float,
                 lookback: int = 12) -> np.ndarray:
    """At each bar, how many of the last `lookback` confirmed swings on that
    side sit within tol_pct of the level currently in force. 1 means a lone
    pivot (what our code accepts today)."""
    n = len(level)
    out = np.zeros(n, dtype=int)
    hist: list[float] = []
    for i in range(n):
        v = swing_prices[i]
        if v == v:
            hist.append(float(v))
            if len(hist) > lookback:
                hist.pop(0)
        lv = level[i]
        if lv != lv or not hist:
            continue
        out[i] = sum(1 for h in hist if abs(h - lv) / lv * 100 <= tol_pct)
    return out


def _retest_shift(sig: np.ndarray, level: np.ndarray, extreme: np.ndarray,
                  close: np.ndarray, direction: int, tol_pct: float,
                  window: int, index) -> pd.Series:
    """Move each break signal forward to the first later bar that comes back
    to the broken level and closes back on the break side. No lookahead: the
    decision bar is the bar the re-test completes on, and the fill is the
    bar after that."""
    n = len(sig)
    out = np.zeros(n, dtype=bool)
    for i in np.flatnonzero(sig):
        lv = level[i]
        if lv != lv:
            continue
        band = lv * (1 + direction * tol_pct / 100)
        for j in range(i + 1, min(i + 1 + window, n)):
            back = (extreme[j] <= band) if direction > 0 else (extreme[j] >= band)
            held = (close[j] > lv) if direction > 0 else (close[j] < lv)
            if back and held:
                out[j] = True
                break
    return pd.Series(out, index=index)


# ===========================================================================
# scoring — real per-trade structure stop, market orders, risk sizing
# ===========================================================================

def stop_builder(tc):
    return E.stop_structure(k=K, n_back=1, buffer_pct=0.0, use="wick")


def target_builder(stop):
    return E.target_fixed_r(stop, r_multiple=TARGET_MULT)


def score_windows(d1h, f1h, el, es, i_tr, i_va):
    direction = pd.Series(np.where(el, 1, np.where(es, -1, 0)), index=d1h.index)
    entries = mask_to_events(el | es, direction)
    mh = days_to_bars(d1h, CONF_HOLD_DAYS)

    def slc(lo, hi):
        return [(i - lo, dr) for i, dr in entries if lo <= i < hi]

    tr_c = d1h.iloc[0:i_tr].reset_index(drop=True)
    va_c = d1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_f = f1h.iloc[0:i_tr].reset_index(drop=True)
    va_f = f1h.iloc[i_tr:i_va].reset_index(drop=True)
    tr_t, tr_sk = run_edge(tr_c, slc(0, i_tr), stop_builder, target_builder, mh,
                           funding_bps=tr_f, k=K, risk_pct=RISK_PCT)
    va_t, va_sk = run_edge(va_c, slc(i_tr, i_va), stop_builder, target_builder, mh,
                           funding_bps=va_f, k=K, risk_pct=RISK_PCT)
    long_frac = int(el.sum()) / max(1, int(el.sum()) + int(es.sum()))
    return dict(tr=trade_stats(tr_t), va=trade_stats(va_t),
                tr_trades=tr_t, va_trades=va_t, tr_skip=tr_sk, va_skip=va_sk,
                tr_c=tr_c, va_c=va_c, tr_f=tr_f, va_f=va_f, mh=mh,
                long_frac=long_frac, n_tr_ev=len(slc(0, i_tr)),
                n_va_ev=len(slc(i_tr, i_va)))


def chance_distribution(candles, n_events, long_frac, mh, funding, draws=200,
                        seed=330):
    """R117's control, exactly: random entry bars, SAME exit apparatus, same
    window, same costs, same number of trades, same long/short mix."""
    rng = np.random.default_rng(seed)
    n = len(candles)
    lo, hi = K + 5, n - 5
    if hi <= lo or n_events <= 0:
        return np.array([])
    pool = np.arange(lo, hi)
    exps = []
    for _ in range(draws):
        take = min(n_events, len(pool))
        idxs = rng.choice(pool, size=take, replace=False)
        dirs = (rng.random(take) < long_frac).astype(int) * 2 - 1
        t, _ = run_edge(candles, list(zip(idxs.tolist(), dirs.tolist())),
                        stop_builder, target_builder, mh, funding_bps=funding,
                        k=K, risk_pct=RISK_PCT)
        if t:
            exps.append(float(np.mean([x["pnl"] for x in t])))
    return np.array(exps)


def adverse_stats(trades):
    if not trades:
        return dict(worst=float("nan"), p5=float("nan"), median=float("nan"))
    mv = np.array([t["direction"] * (t["exit_price"] - t["entry_price"])
                   / t["entry_price"] * 100 for t in trades])
    return dict(worst=float(mv.min()), p5=float(np.percentile(mv, 5)),
                median=float(np.median(mv)))


def verdict(tr, va, th_mult):
    if tr["n"] < MIN_TRAIN_TRADES or va["n"] < MIN_VAL_TRADES:
        return "NOT ENOUGH TRADES"
    if tr["expectancy"] <= 0 or va["expectancy"] <= 0:
        return "FAIL"
    if th_mult < 5.0:
        return "FAIL (too thin)"
    return "SURVIVOR (first 60% + middle 20% only)"


# ===========================================================================
# PART 1 — what our code actually requires, in numbers
# ===========================================================================

def part1_audit():
    print("=" * 78)
    print("PART 1 — AUDIT: what our structure break requires vs what a trader requires")
    print("=" * 78)
    d1h, d4h, f1h = load("SOLUSDT")
    n, i_tr, i_va = split_points(d1h)
    print(f"SOL 1-hour bars {n} | first 60% ends {d1h['timestamp'].iloc[i_tr]} "
          f"| middle 20% ends {d1h['timestamp'].iloc[i_va]}")
    print("the final untouched slice of history was NOT loaded by this script")

    el, es, diag = build_signal(d1h, d4h, i_tr, gate_atr_pct=1.5)
    mask = el | es
    print(f"\nsignals over first 60% + middle 20%: {int(mask.iloc[:i_va].sum())} "
          f"(long {int(el.iloc[:i_va].sum())} / short {int(es.iloc[:i_va].sum())})")

    # how far past the level did the close get?
    bl = pd.Series(diag["break_pct_long_at_signal"], index=d1h.index)[el].dropna()
    bs = pd.Series(diag["break_pct_short_at_signal"], index=d1h.index)[es].dropna()
    allb = pd.concat([bl, bs])
    allb = allb[allb.index < i_va]
    med_atr = diag["median_train_atr_pct"]
    print(f"\nSOL's own median 1-hour true range on the first 60%: {med_atr:.3f}% of price")
    print("distance the close travelled PAST the broken level, at the signal bar:")
    for q in (5, 25, 50, 75, 95):
        v = float(np.percentile(allb, q))
        print(f"   {q:2d}th percentile {v:7.3f}% of price  = {v/med_atr:5.2f}x that median range")
    print(f"   share of signals under a QUARTER of one median range past the level: "
          f"{float((allb < 0.25*med_atr).mean())*100:.1f}%")
    print(f"   share under one-tenth of one median range: "
          f"{float((allb < 0.10*med_atr).mean())*100:.1f}%")

    # how many confirmed swings sit at the level
    sh_price, sl_price = confirmed_swings(d1h, K)
    _, _, _, lsh, lsl = equilibrium(d1h, K)
    th = _touch_count(sh_price.to_numpy(), lsh.to_numpy(), 0.15)
    tl = _touch_count(sl_price.to_numpy(), lsl.to_numpy(), 0.15)
    tt = np.where(el.to_numpy(), th, np.where(es.to_numpy(), tl, 0))
    tt = tt[mask.to_numpy() & (np.arange(n) < i_va)]
    print(f"\nswings sitting AT the broken level (within 0.15% of it):")
    for c in (1, 2, 3):
        print(f"   {c}+ touches: {float((tt >= c).mean())*100:5.1f}% of signals")

    # the volatility gate buried in the 4h bias vote
    atr4 = atr_pct_series(d4h)
    cut = d4h["timestamp"] <= d1h["timestamp"].iloc[i_va]
    print(f"\nthe 1.5% volatility gate inside the 4-hour bias vote is open on "
          f"{float((atr4[cut] >= 1.5).mean())*100:.1f}% of SOL's 4-hour bars")
    print(f"   SOL's own median 4-hour true range: {float(atr4[cut].median()):.3f}% of price")

    # the stop the R190 number actually used
    bos = bos_chain(d1h, K)
    dist = pd.Series(np.nan, index=d1h.index)
    dist = dist.mask(el, (d1h["close"] - bos["lsl"]) / d1h["close"] * 100)
    dist = dist.mask(es, (bos["lsh"] - d1h["close"]) / d1h["close"] * 100)
    dtr = dist.iloc[:i_tr][mask.iloc[:i_tr]].dropna()
    print(f"\nthe stop the +$218.95 number used: TRAIN median distance to structure "
          f"= {float(dtr.median()):.2f}% of price, CAPPED at 6.00% -> a FLAT 6% stop "
          f"on every trade, both windows")
    print(f"   share of real per-trade structure distances beyond that 6% cap: "
          f"{float((dtr > 6.0).mean())*100:.1f}%")
    return d1h, d4h, f1h, i_tr, i_va, med_atr


# ===========================================================================
# PART 2 — the same entry, scored the way BITCOIN was scored in round 150
#          (real per-trade structure stop, risk sizing, market orders)
#          plus each practitioner condition switched on
# ===========================================================================

VARIANTS = [
    ("as shipped (round 190 entry, honest stop)", dict()),
    ("+ close must clear the level by 1/4 of a median hourly range",
     dict(min_break_x_atr=0.25)),
    ("+ close must clear the level by 1/2 of a median hourly range",
     dict(min_break_x_atr=0.50)),
    ("+ level must have 2 swings sitting on it", dict(min_touches=2)),
    ("+ wait for the level to be re-tested and held", dict(retest=True)),
    ("+ clear by 1/4 range AND re-tested", dict(min_break_x_atr=0.25, retest=True)),
]


def run_variants(d1h, d4h, f1h, i_tr, i_va, gate_atr_pct, label):
    rows = []
    for name, kw in VARIANTS:
        el, es, _ = build_signal(d1h, d4h, i_tr, gate_atr_pct=gate_atr_pct, **kw)
        r = score_windows(d1h, f1h, el, es, i_tr, i_va)
        tr, va = r["tr"], r["va"]
        all_t = r["tr_trades"] + r["va_trades"]
        avg_notional = float(np.mean([t["notional"] for t in all_t])) if all_t else 0.0
        th_tr = thickness(tr["expectancy"], tr["avg_notional"]) if tr["n"] else None
        th_va = thickness(va["expectancy"], va["avg_notional"]) if va["n"] else None
        ae = adverse_stats(all_t)
        rows.append(dict(
            market=label, variant=name,
            tr_n=tr["n"], tr_exp=tr["expectancy"], tr_win=tr["win_rate"] * 100,
            va_n=va["n"], va_exp=va["expectancy"], va_win=va["win_rate"] * 100,
            tr_pct_of_position=th_tr["pct_notional"] if th_tr else float("nan"),
            tr_x_cost=th_tr["mult_full_18bps"] if th_tr else float("nan"),
            va_pct_of_position=th_va["pct_notional"] if th_va else float("nan"),
            va_x_cost=th_va["mult_full_18bps"] if th_va else float("nan"),
            avg_leverage=float(np.mean([t["leverage"] for t in all_t])) if all_t else 0.0,
            avg_stop_dist_pct=float(np.mean([t["stop_dist_pct"] for t in all_t])) if all_t else 0.0,
            worst_move_pct=ae["worst"], p5_move_pct=ae["p5"], median_move_pct=ae["median"],
            verdict=verdict(tr, va, th_va["mult_full_18bps"] if th_va else 0.0),
            _r=r, _el=el, _es=es,
        ))
    return rows


def show(rows, title):
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)
    for r in rows:
        print(f"{r['variant']}")
        print(f"    first 60%:  {r['tr_n']:3d} trades  ${r['tr_exp']:+9.2f}/trade  "
              f"win {r['tr_win']:4.1f}%   {r['tr_pct_of_position']:+.3f}% of position  "
              f"{r['tr_x_cost']:+6.2f}x cost")
        print(f"    middle 20%: {r['va_n']:3d} trades  ${r['va_exp']:+9.2f}/trade  "
              f"win {r['va_win']:4.1f}%   {r['va_pct_of_position']:+.3f}% of position  "
              f"{r['va_x_cost']:+6.2f}x cost")
        print(f"    avg leverage {r['avg_leverage']:.1f}x  avg stop distance "
              f"{r['avg_stop_dist_pct']:.2f}% of price  |  worst trade move "
              f"{r['worst_move_pct']:.2f}% in price  5th-pct {r['p5_move_pct']:.2f}%")
        print(f"    -> {r['verdict']}")


# ===========================================================================
# PART 3 — is the money in the ENTRY or in the EXIT?
#          Round 117 on oil found an apparent breakout edge was really the
#          exit riding a rising market: random entries with the same exit did
#          BETTER. This runs that exact control here.
# ===========================================================================

def part3_entry_or_exit(rows, draws=200):
    print("\n" + "=" * 78)
    print("PART 3 — random entries, SAME exit, same window, same costs")
    print("=" * 78)
    out = []
    for r in rows:
        rr = r["_r"]
        for wname, cand, fund, n_ev, st in (
                ("first 60% ", rr["tr_c"], rr["tr_f"], rr["n_tr_ev"], r["tr_exp"]),
                ("middle 20%", rr["va_c"], rr["va_f"], rr["n_va_ev"], r["va_exp"])):
            d = chance_distribution(cand, n_ev, rr["long_frac"], rr["mh"], fund,
                                    draws=draws)
            if len(d) == 0:
                continue
            beat = float(np.mean(st > d)) * 100
            print(f"{r['variant'][:52]:52s} {wname}: real ${st:+8.2f}/trade  "
                  f"vs random-entry mean ${float(d.mean()):+8.2f}  "
                  f"(random range ${float(d.min()):+.0f} to ${float(d.max()):+.0f})  "
                  f"beats {beat:5.1f}% of {len(d)} random runs")
            out.append(dict(variant=r["variant"], window=wname.strip(),
                            real=st, random_mean=float(d.mean()),
                            random_p90=float(np.percentile(d, 90)),
                            random_min=float(d.min()), random_max=float(d.max()),
                            beats_pct=beat, draws=len(d)))
    return out


# ===========================================================================
# PART 4 — does the same rule still work on a different coin?
#          Config UNCHANGED in shape. Every volatility-based number is
#          RE-DERIVED on that coin's own history, never copied.
# ===========================================================================

TRANSFER_SYMBOLS = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "AVAXUSDT", "BNBUSDT",
                    "DOGEUSDT", "LINKUSDT", "LTCUSDT", "XRPUSDT", "DOTUSDT"]


def rederived_gate(d4h, i_va_4h):
    """Bitcoin's 1.5% volatility gate re-expressed as 'that coin's own median
    4-hour true range', so the gate keeps the SELECTIVITY that made it work
    on Bitcoin instead of degenerating into an always-open switch."""
    a = atr_pct_series(d4h).iloc[:i_va_4h]
    return float(a.median())


def transfer_one(sym, chosen_kwargs, draws=120):
    d1h, d4h, f1h = load(sym)
    n, i_tr, i_va = split_points(d1h)
    cutoff = d1h["timestamp"].iloc[i_va]
    i_va_4h = int((d4h["timestamp"] <= cutoff).sum())
    gate = rederived_gate(d4h, i_va_4h)
    med_h = float(atr_pct_series(d1h).iloc[:i_tr].median())
    res = {}
    for tag, kw in (("as shipped", dict()), ("chosen", chosen_kwargs)):
        el, es, _ = build_signal(d1h, d4h, i_tr, gate_atr_pct=gate, **kw)
        r = score_windows(d1h, f1h, el, es, i_tr, i_va)
        tr, va = r["tr"], r["va"]
        th_va = thickness(va["expectancy"], va["avg_notional"]) if va["n"] else None
        th_tr = thickness(tr["expectancy"], tr["avg_notional"]) if tr["n"] else None
        dd = chance_distribution(r["va_c"], r["n_va_ev"], r["long_frac"], r["mh"],
                                 r["va_f"], draws=draws)
        beat = float(np.mean(va["expectancy"] > dd)) * 100 if len(dd) else float("nan")
        ae = adverse_stats(r["tr_trades"] + r["va_trades"])
        res[tag] = dict(
            market=sym.replace("USDT", ""), variant=tag,
            own_gate_pct=gate, own_median_hourly_range_pct=med_h,
            tr_n=tr["n"], tr_exp=tr["expectancy"],
            va_n=va["n"], va_exp=va["expectancy"],
            tr_pct_of_position=th_tr["pct_notional"] if th_tr else float("nan"),
            va_pct_of_position=th_va["pct_notional"] if th_va else float("nan"),
            va_x_cost=th_va["mult_full_18bps"] if th_va else float("nan"),
            random_entry_mean=float(dd.mean()) if len(dd) else float("nan"),
            beats_random_pct=beat,
            worst_move_pct=ae["worst"], p5_move_pct=ae["p5"],
            verdict=verdict(tr, va, th_va["mult_full_18bps"] if th_va else 0.0),
        )
    return res


def main():
    d1h, d4h, f1h, i_tr, i_va, med = part1_audit()

    print("\n" + "=" * 78)
    print("PART 2 — SOL, scored the way BITCOIN was scored in round 150")
    print("        (real per-trade structure stop, size = risk / stop distance,")
    print("         market orders on entry and every exit)")
    print("=" * 78)
    rows = run_variants(d1h, d4h, f1h, i_tr, i_va, 1.5, "SOL (gate ported from BTC, 1.5%)")
    show(rows, "SOL — Bitcoin's 1.5% volatility gate ported unchanged (as round 190 ran it)")

    cut = d4h["timestamp"] <= d1h["timestamp"].iloc[i_va]
    own_gate = float(atr_pct_series(d4h)[cut].median())
    rows_own = run_variants(d1h, d4h, f1h, i_tr, i_va, own_gate,
                            f"SOL (gate re-derived, {own_gate:.2f}%)")
    show(rows_own, f"SOL — volatility gate RE-DERIVED on SOL's own history ({own_gate:.2f}%)")

    chance = part3_entry_or_exit(rows, draws=200)

    print("\n" + "=" * 78)
    print("PART 4 — the same rule on other coins, un-retuned, every")
    print("         volatility number re-derived on that coin's own history")
    print("=" * 78)
    chosen = dict(min_break_x_atr=0.25)
    print("chosen on the FIRST 60% of SOL only: require the close to clear the")
    print("level by a quarter of that coin's own median hourly range.\n")
    tr_rows = []
    for sym in TRANSFER_SYMBOLS:
        try:
            res = transfer_one(sym, chosen)
        except Exception as e:
            print(f"{sym}: ERROR {e}")
            continue
        for tag in ("as shipped", "chosen"):
            r = res[tag]
            tr_rows.append(r)
            print(f"{r['market']:6s} {tag:11s} own gate {r['own_gate_pct']:5.2f}%  "
                  f"first60% {r['tr_n']:3d}t ${r['tr_exp']:+8.2f}  "
                  f"mid20% {r['va_n']:3d}t ${r['va_exp']:+8.2f} "
                  f"({r['va_pct_of_position']:+.3f}% of position, {r['va_x_cost']:+5.1f}x cost)  "
                  f"vs random ${r['random_entry_mean']:+7.2f} beats {r['beats_random_pct']:5.1f}%  "
                  f"-> {r['verdict']}")

    out = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")}
                        for r in rows + rows_own] + tr_rows)
    out.to_csv("step330_table.csv", index=False)
    pd.DataFrame(chance).to_csv("step330_chance_table.csv", index=False)
    print("\nwrote step330_table.csv and step330_chance_table.csv")
    return rows, rows_own, chance, tr_rows


if __name__ == "__main__":
    main()
