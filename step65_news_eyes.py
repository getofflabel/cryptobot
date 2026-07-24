"""
step65_news_eyes.py — round 65: GIVE THE NEWS TRADE EYES.

The owner's critique of the live NEWSDESK book (BTC news-momentum, TP+2.4%/
SL-1.2%/24h, sealed-validated in round 45B): "you already know your take
profit before even looking at the situation — no technical analysis, no
price action. No real trader does this." This script tests whether
CHART-AWARE reaction policies (structure targets, structure trailing, a
"don't enter into a wall" veto, vol-scaled brackets) beat the blind fixed-%
incumbent on the SAME validated trigger. Research only. Touches ONLY:
  - step65_news_eyes.py   (this file)
  - step65_results.md     (written by hand from this script's output)
No live orders, no commits, no other repo file read for logic reuse beyond
step45b_news_events.py (entry construction, mandated) and step43_daytrade.py
(gauntlet constants, mandated). Deliberately does NOT import step59_
exit_science.py or gold_book.py — both are owned by a concurrent agent this
round; the exit-simulator machinery below is independently reimplemented
(same repo-standard conventions: gap-through honesty, stop-wins-ties,
maker fee on resting-limit fills / taker on stop-or-market fills) so this
script has zero coupling to files another agent may be editing right now.

======================================================================
THE FIXED TRIGGER (held identical across every policy below — R45B/step45b)
======================================================================
A relevant WatcherGuru headline (classify_headline, imported verbatim from
step45b_news_events) -> align_events' no-lookahead floor/trading-bar
mapping (also imported verbatim) -> the first FULL 1h bar after the event
-> enter at THAT bar's own close, direction = that bar's own close-vs-open
sign (the "first-bar-move" convention — the ONLY one of step45b's two
direction variants that ever passed a sealed test; round 45B's addendum
found the keyword-direction variant does not survive out-of-sample). This
script never touches entry selection — only what happens AFTER entry.

======================================================================
NEWS-SPAN SPLIT (R45B convention)
======================================================================
BTC 1h candles are sliced to the WatcherGuru harvested span (news_min-24h
-> news_max+24h), then chronological 60/20/20 (step43_daytrade.split_points,
same helper R45B itself used). This script computes and reports TRAIN and
VAL only. The final 20% (TEST) is sliced out of every frame before any
pivot/ATR/entry construction ever sees it — the sealed slice is never
loaded into a variable this script's logic can reach, not merely "not
printed". A challenger only earns a sealed-look recommendation if it beats
the incumbent on BOTH train AND val (mandate's own condition).

======================================================================
THE FIVE POLICIES (identical entries, different REACTION)
======================================================================
N0 INCUMBENT      — TP +2.4% / SL -1.2% / 24h. The live bracket. Known
    before the trade is ever looked at — the thing being put on trial.
N1 STRUCTURE TARGETS — TP = the NEAREST-BY-PRICE {confirmed swing high
    (fractal, k in {5,8}), equal-highs liquidity pool (>=2 confirmed
    swing highs within 0.1% of each other)} above entry (mirrored below
    entry for shorts). SL = beyond the ENTRY BAR's own opposite extreme
    (its low for a long, its high for a short — "where does THIS candle
    say danger is") + a buffer in {0.1%, 0.3%}. Accepted only if the
    target's distance sits inside [1x, 3x] the stop distance; outside
    that band (or no confirmed level exists yet) the WHOLE trade falls
    back to the plain incumbent bracket (2.4%/1.2%) — never a mix of a
    structure target with an unbanded, arbitrary distance. 6 configs
    (3 target sources x 2 SL buffers).
N2 STRUCTURE TRAILING — no fixed TP. Initial floor = same entry-bar-
    extreme + buffer construction as N1's SL. The floor only ever
    ratchets favorably as new CONFIRMED swing lows (longs; highs for
    shorts, k=5) print; exit the instant price trades at/through the
    floor intrabar, or closes beyond it, whichever comes first (same
    "ride until the chart says stop" mechanic this repo has used before,
    reimplemented here, not imported). 2 configs (SL buffer only; k=5
    fixed as primary, k=8 spot-checked as a prose footnote).
N3 CONTEXT VETO   — the "look at the situation first" filter. Skip the
    entry entirely if a confirmed opposing swing high or liquidity pool
    sits within {0.5, 0.8}x the trade's OWN take-profit distance
    overhead (for N0: the fixed 2.4%; for the best of N1/N2: that
    trade's own realized target distance, or for N2 specifically — which
    has no fixed target — a stated 2R synthetic reference, 2x its initial
    stop distance, this repo's own established "constructed target"
    convention from step45b/step59's E4). Run as an overlay on N0 AND on
    whichever of N1/N2 is the stronger single challenger (selected by
    TRAIN expectancy only, this repo's standing selection discipline).
    2 veto thresholds x 2 base policies = 4 runs.
N4 ATR-SCALED     — the SAME fixed-shape bracket as N0, just sized by
    CURRENT volatility instead of a constant: TP/SL = {2.0/1.0x,
    3.0/1.5x} x ATR%(14, 1h, AS OF the entry bar's own close — causal,
    strategy.atr's own ewm construction). 24h cap unchanged. 2 configs.

======================================================================
THE SIMULATOR
======================================================================
One event-driven, single-slot-at-a-time per-trade engine (backtest.py's
continuous-signal engine cannot express a per-trade dynamic target/floor
that moves with confirmed chart structure — this repo's own established
reason for hand-rolling this kind of simulator, see step59's docstring).
Entry fill = the entry bar's own CLOSE (matches step45b/newsdesk.py's own
"enter at that bar's close" exactly). Costs: crypto convention already
established and DOCUMENTED live in this repo (step59's own stated
newsdesk.py fee convention) — maker 2bp on every entry fill and every
resting-limit TARGET-side exit, taker 6bp (fee-only, no extra spread/
slippage — "already at the exact level") on every STOP / structural-break
/ time-cap exit. Real BTC perp funding (data_bybit_BTCUSDT_funding.parquet,
merge_asof-backward) accrues while held, signed exactly like backtest.py
(longs pay a positive rate, shorts collect it). Gap-through honesty: if a
bar's OPEN already traded through a stop/target level, fill AT THE OPEN,
not the theoretical level. Stop and target both touched in the same bar:
STOP WINS (backtest.py's own conservative rule, reused). Equity: $10,000
start, full equity into each trade (no leverage), compounding sequentially
(trades never overlap by construction — one slot). Sim-validated against
the SAME numbers R45B/step45b's own event_study + backtest already printed
for the incumbent shape as a first sanity gate (see main()).

Run:  python3 step65_news_eyes.py
"""

from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

from backtest import CostModel
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import MIN_TRAIN_TRADES, MIN_VAL_TRADES, split_points
from step45b_news_events import align_events, classify_headline
from strategy import atr

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

INITIAL_EQUITY = 10_000.0
CRYPTO_COSTS = CostModel()                          # 6bp taker / 2bp maker / 1bp spread / 2bp slip
TARGET_FEE_BPS = CRYPTO_COSTS.maker_fee_bps          # 2.0 — entry fills + resting-limit target fills
STOP_FEE_BPS = CRYPTO_COSTS.fee_bps                  # 6.0 — stop / structural-break / time-cap fills

K_SWING_PRIMARY = 5
K_SWING_SPOTCHECK = 8
CLUSTER_TOL = 0.001            # 0.1% equal-highs liquidity-pool tolerance
SL_BUFFERS = (0.1, 0.3)        # % beyond the entry bar's opposite extreme
N1_BAND = (1.0, 3.0)           # accept a structure target inside [1x,3x] stop distance
VETO_MULTS = (0.5, 0.8)        # x TP-distance overhead
ATR_PAIRS = ((2.0, 1.0), (3.0, 1.5))   # (target_mult, stop_mult) x ATR%

INCUMBENT_TP_PCT = 2.4
INCUMBENT_SL_PCT = 1.2
MAX_HOLD_H = 24


# ===========================================================================
# generic helpers
# ===========================================================================

def bar_hours_of(d: pd.DataFrame) -> float:
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600) if len(d) > 1 else 1.0


def hours_to_bars_of(d: pd.DataFrame, hours: float) -> int:
    return max(1, round(hours / bar_hours_of(d)))


def find_pivots(h: np.ndarray, l: np.ndarray, k: int):
    """Fractal swing pivots, CONFIRMED only k bars later (no lookahead:
    at confirm_idx=j+k the pivot is knowable, not before). Standard
    technique, reimplemented locally (see module docstring — deliberately
    not imported from step59)."""
    n = len(h)
    hi_confirm, hi_price, lo_confirm, lo_price = [], [], [], []
    for j in range(k, n - k):
        wh = h[j - k:j + k + 1]
        if h[j] >= wh.max():
            hi_confirm.append(j + k)
            hi_price.append(h[j])
        wl = l[j - k:j + k + 1]
        if l[j] <= wl.min():
            lo_confirm.append(j + k)
            lo_price.append(l[j])
    return (
        {"confirm_idx": np.array(hi_confirm, dtype=int), "price": np.array(hi_price, dtype=float)},
        {"confirm_idx": np.array(lo_confirm, dtype=int), "price": np.array(lo_price, dtype=float)},
    )


def confirmed_prices(piv, i0: int) -> np.ndarray:
    idx = bisect.bisect_right(piv["confirm_idx"], i0)
    return piv["price"][:idx]


def nearest_favorable_swing(piv, i0: int, entry_price: float, direction: int):
    """NEAREST-BY-PRICE confirmed swing on the favorable (target) side —
    the immediately-overhead level, not the most-recently-printed one."""
    prices = confirmed_prices(piv, i0)
    if direction > 0:
        above = prices[prices > entry_price]
        return float(above.min()) if len(above) else None
    below = prices[prices < entry_price]
    return float(below.max()) if len(below) else None


def liquidity_pools(piv, i0: int, tol: float = CLUSTER_TOL):
    """All confirmed-by-i0 clusters of >=2 pivots within `tol` relative
    tolerance of each other -> one level (mean) per cluster."""
    prices = np.sort(confirmed_prices(piv, i0))
    if len(prices) < 2:
        return np.array([])
    clusters, cur = [], [prices[0]]
    for p in prices[1:]:
        if abs(p - cur[-1]) / cur[-1] <= tol:
            cur.append(p)
        else:
            clusters.append(cur)
            cur = [p]
    clusters.append(cur)
    return np.array([float(np.mean(c)) for c in clusters if len(c) >= 2])


def nearest_pool(piv, i0: int, entry_price: float, direction: int, tol: float = CLUSTER_TOL):
    levels = liquidity_pools(piv, i0, tol)
    if direction > 0:
        above = levels[levels > entry_price]
        return float(above.min()) if len(above) else None
    below = levels[levels < entry_price]
    return float(below.max()) if len(below) else None


def entry_bar_extreme_stop(o, h, l, c, entry_idx, direction, buffer_pct):
    """SL = beyond the ENTRY BAR's own opposite extreme + buffer%. Longs:
    below that bar's low. Shorts: above that bar's high. This is the
    'read the reaction candle' stop the owner's critique is about."""
    if direction > 0:
        return float(l[entry_idx]) * (1 - buffer_pct / 100)
    return float(h[entry_idx]) * (1 + buffer_pct / 100)


def band_accept(target_price, entry_price, stop_dist_pct, direction, band=N1_BAND):
    if target_price is None or stop_dist_pct <= 0:
        return None
    dist_pct = abs(target_price - entry_price) / entry_price * 100
    lo, hi = band[0] * stop_dist_pct, band[1] * stop_dist_pct
    return target_price if lo <= dist_pct <= hi else None


def overhead_obstructed(piv_target_side, i0, entry_price, direction, tp_dist_pct, mult,
                        pool_tol=CLUSTER_TOL):
    """N3's veto test: does a confirmed swing high (or a >=2-pivot
    liquidity pool) sit anywhere between entry and entry + mult*tp_dist
    (mirrored for shorts)? tp_dist_pct is THIS trade's own TP distance
    (fixed 2.4% for N0; the realized structure/synthetic distance for
    N1/N2)."""
    zone = entry_price * (mult * tp_dist_pct / 100)
    prices = confirmed_prices(piv_target_side, i0)
    pools = liquidity_pools(piv_target_side, i0, pool_tol)
    candidates = np.concatenate([prices, pools]) if len(pools) else prices
    if direction > 0:
        hits = candidates[(candidates > entry_price) & (candidates <= entry_price + zone)]
    else:
        hits = candidates[(candidates < entry_price) & (candidates >= entry_price - zone)]
    return len(hits) > 0, (candidates if direction > 0 else candidates)


# ===========================================================================
# THE SIMULATOR
# ===========================================================================

def _gap_or_level(open_px, level, direction, side):
    """Gap-through honesty (backtest.py's own convention, reused): if the
    bar's OPEN already traded through the level, fill at the open."""
    if side == "stop":
        return open_px if ((direction > 0 and open_px <= level) or
                           (direction < 0 and open_px >= level)) else level
    return open_px if ((direction > 0 and open_px >= level) or
                       (direction < 0 and open_px <= level)) else level


def simulate(candles: pd.DataFrame, entries: list, kind: str, param_builder,
            funding: pd.Series | None = None) -> list:
    """Single-slot event-driven simulator shared by every policy. Returns a
    list of trade dicts: entry_time, exit_time, direction, pnl, reason,
    hold_hours."""
    o = candles["open"].to_numpy()
    h = candles["high"].to_numpy()
    l = candles["low"].to_numpy()
    c = candles["close"].to_numpy()
    t = pd.DatetimeIndex(candles["timestamp"])
    n = len(candles)
    fund = funding.to_numpy() if funding is not None else None
    bh = bar_hours_of(candles)

    equity = INITIAL_EQUITY
    trades, busy_until = [], -1

    for entry_idx, direction in entries:
        if entry_idx <= busy_until or entry_idx >= n - 1:
            continue
        entry_price = float(c[entry_idx])
        params = param_builder(entry_idx, entry_price, direction)
        if params is None:
            continue     # N3 veto: this entry is simply refused

        exit_idx, exit_price, reason, fee_bps = _manage(
            entry_idx, entry_price, direction, kind, params, o, h, l, c, n)

        hold_bars = exit_idx - entry_idx
        hold_hours = hold_bars * bh if hold_bars > 0 else bh
        funding_dollars = 0.0
        if fund is not None and exit_idx > entry_idx:
            mr = float(np.nanmean(fund[entry_idx + 1:exit_idx + 1]))
            if mr == mr:
                funding_dollars = equity * direction * mr / 10_000 * (hold_hours / 8.0)

        entry_fee = equity * TARGET_FEE_BPS / 10_000
        notional = equity
        gross = direction * (exit_price / entry_price - 1) * notional
        exit_fee = notional * exit_price / entry_price * fee_bps / 10_000
        pnl = -entry_fee + gross - exit_fee - funding_dollars
        equity += pnl

        trades.append({
            "entry_idx": entry_idx, "exit_idx": exit_idx,
            "entry_time": t[entry_idx], "exit_time": t[exit_idx],
            "entry_price": entry_price, "exit_price": exit_price,
            "direction": direction, "pnl": pnl, "reason": reason,
            "hold_hours": hold_hours,
        })
        busy_until = exit_idx

    return trades


def _manage(entry_idx, entry_price, direction, kind, params, o, h, l, c, n):
    max_hold = params["max_hold_bars"]
    last_i = min(n - 1, entry_idx + max_hold)

    if kind == "static":
        stop_px = entry_price * (1 - direction * params["stop_pct"] / 100) \
            if params.get("stop_from_pct", True) else params["stop_px"]
        tgt_px = entry_price * (1 + direction * params["target_pct"] / 100) \
            if params.get("target_from_pct", True) else params["target_px"]
        for i in range(entry_idx + 1, last_i + 1):
            hit_stop = (l[i] <= stop_px) if direction > 0 else (h[i] >= stop_px)
            hit_tgt = (h[i] >= tgt_px) if direction > 0 else (l[i] <= tgt_px)
            if hit_stop:      # stop wins ties (both hit same bar)
                return i, _gap_or_level(o[i], stop_px, direction, "stop"), "stop", STOP_FEE_BPS
            if hit_tgt:
                return i, _gap_or_level(o[i], tgt_px, direction, "target"), "target", TARGET_FEE_BPS
        return last_i, float(c[last_i]), "time", STOP_FEE_BPS

    if kind == "trailing":
        floor_px = params["initial_floor"]
        piv = params["floor_pivots"]
        for i in range(entry_idx + 1, last_i + 1):
            lo_ = bisect.bisect_left(piv["confirm_idx"], i)
            hi_ = bisect.bisect_right(piv["confirm_idx"], i)
            for p in piv["price"][lo_:hi_]:
                if direction > 0 and p > floor_px:
                    floor_px = float(p)
                elif direction < 0 and p < floor_px:
                    floor_px = float(p)
            hit_floor = (l[i] <= floor_px) if direction > 0 else (h[i] >= floor_px)
            if hit_floor:
                return i, _gap_or_level(o[i], floor_px, direction, "stop"), "structure stop", STOP_FEE_BPS
            broke_close = (c[i] < floor_px) if direction > 0 else (c[i] > floor_px)
            if broke_close:
                return i, float(c[i]), "structure break", STOP_FEE_BPS
        return last_i, float(c[last_i]), "time", STOP_FEE_BPS

    raise ValueError(kind)


def trades_to_stats(trades: list) -> dict:
    if not trades:
        return {"n": 0, "expectancy": 0.0, "win_rate": 0.0, "total_return_pct": 0.0,
               "max_dd_pct": 0.0, "median_hold_h": 0.0, "reasons": {}}
    equity = INITIAL_EQUITY
    curve = [equity]
    for tr in trades:
        equity += tr["pnl"]
        curve.append(equity)
    arr = np.array([tr["pnl"] for tr in trades])
    curve_arr = np.array(curve)
    peaks = np.maximum.accumulate(curve_arr)
    dd = (curve_arr - peaks) / peaks
    reasons = pd.Series([tr["reason"] for tr in trades]).value_counts().to_dict()
    return {
        "n": len(trades), "expectancy": float(arr.mean()), "win_rate": float((arr > 0).mean()),
        "total_return_pct": (equity / INITIAL_EQUITY - 1) * 100, "max_dd_pct": float(dd.min() * 100),
        "median_hold_h": float(np.median([tr["hold_hours"] for tr in trades])),
        "final_equity": equity, "reasons": reasons,
    }


def verdict_for(tr_stats, va_stats):
    if tr_stats["expectancy"] > 0 and va_stats["expectancy"] > 0:
        if tr_stats["n"] >= MIN_TRAIN_TRADES and va_stats["n"] >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


# ===========================================================================
# entries — the ONE fixed trigger (R45B / step45b, first-bar-move)
# ===========================================================================

def build_news_entries(d: pd.DataFrame, news: pd.DataFrame) -> list:
    relevant_mask = news["text"].apply(lambda t: classify_headline(t).get("relevant", False))
    relevant_ts = pd.DatetimeIndex(sorted(news[relevant_mask]["utc_timestamp"]))
    if len(relevant_ts) == 0:
        return []
    _, trading_idx, valid = align_events(d, relevant_ts)
    trading_idx = trading_idx[valid]
    trading_idx = trading_idx[trading_idx < len(d)]
    o, c = d["open"].to_numpy(), d["close"].to_numpy()
    entries, seen = [], set()
    for idx in sorted(set(int(x) for x in trading_idx)):
        if idx in seen:
            continue
        seen.add(idx)
        if c[idx] > o[idx]:
            entries.append((idx, 1))
        elif c[idx] < o[idx]:
            entries.append((idx, -1))
    return entries


# ===========================================================================
# per-slice precompute (pivots/ATR computed PER SLICE — never across a
# train/val boundary, so no boundary bar's confirmed pivot ever depends on
# data from the other slice, let alone the sealed test)
# ===========================================================================

def slice_meta(c_slice: pd.DataFrame):
    h, l = c_slice["high"].to_numpy(), c_slice["low"].to_numpy()
    piv_high5, piv_low5 = find_pivots(h, l, K_SWING_PRIMARY)
    piv_high8, piv_low8 = find_pivots(h, l, K_SWING_SPOTCHECK)
    atr_arr = atr(c_slice, 14).to_numpy()
    return dict(o=c_slice["open"].to_numpy(), h=h, l=l, c=c_slice["close"].to_numpy(),
               piv_high5=piv_high5, piv_low5=piv_low5, piv_high8=piv_high8, piv_low8=piv_low8,
               atr_arr=atr_arr, max_hold_bars=hours_to_bars_of(c_slice, MAX_HOLD_H))


# ===========================================================================
# N0 — incumbent
# ===========================================================================

def n0_builder(mh_bars):
    def build(entry_idx, entry_price, direction):
        return dict(stop_pct=INCUMBENT_SL_PCT, target_pct=INCUMBENT_TP_PCT, max_hold_bars=mh_bars)
    return "static", build


# ===========================================================================
# N1 — structure targets (6 configs: 3 TP sources x 2 SL buffers)
# ===========================================================================

N1_TP_SOURCES = ("swing_k5", "swing_k8", "pool")


def n1_builder(meta, tp_source: str, sl_buffer: float):
    def target_side(direction):
        if tp_source == "swing_k5":
            return meta["piv_high5"] if direction > 0 else meta["piv_low5"]
        if tp_source == "swing_k8":
            return meta["piv_high8"] if direction > 0 else meta["piv_low8"]
        return meta["piv_high5"] if direction > 0 else meta["piv_low5"]   # pool uses k5 pivots

    def build(entry_idx, entry_price, direction):
        stop_px = entry_bar_extreme_stop(meta["o"], meta["h"], meta["l"], meta["c"],
                                         entry_idx, direction, sl_buffer)
        stop_dist_pct = abs(entry_price - stop_px) / entry_price * 100
        piv = target_side(direction)
        raw = (nearest_pool(piv, entry_idx, entry_price, direction) if tp_source == "pool"
              else nearest_favorable_swing(piv, entry_idx, entry_price, direction))
        accepted = band_accept(raw, entry_price, stop_dist_pct, direction)
        if accepted is None:
            # fallback: the WHOLE trade reverts to the plain incumbent bracket
            return dict(stop_pct=INCUMBENT_SL_PCT, target_pct=INCUMBENT_TP_PCT,
                       max_hold_bars=meta["max_hold_bars"], fell_back=True)
        target_pct = abs(accepted - entry_price) / entry_price * 100
        return dict(stop_from_pct=False, stop_px=stop_px, target_pct=target_pct,
                   max_hold_bars=meta["max_hold_bars"], fell_back=False)
    return "static", build


# ===========================================================================
# N2 — structure trailing (2 configs: SL buffer only, k=5 primary)
# ===========================================================================

def n2_builder(meta, sl_buffer: float, k: int = K_SWING_PRIMARY):
    piv_high = meta["piv_high5"] if k == K_SWING_PRIMARY else meta["piv_high8"]
    piv_low = meta["piv_low5"] if k == K_SWING_PRIMARY else meta["piv_low8"]

    def build(entry_idx, entry_price, direction):
        stop_px = entry_bar_extreme_stop(meta["o"], meta["h"], meta["l"], meta["c"],
                                         entry_idx, direction, sl_buffer)
        floor_pivots = piv_low if direction > 0 else piv_high
        return dict(initial_floor=stop_px, floor_pivots=floor_pivots,
                   max_hold_bars=meta["max_hold_bars"])
    return "trailing", build


def n2_stop_dist_pct(meta, sl_buffer, entry_idx, entry_price, direction):
    stop_px = entry_bar_extreme_stop(meta["o"], meta["h"], meta["l"], meta["c"],
                                     entry_idx, direction, sl_buffer)
    return abs(entry_price - stop_px) / entry_price * 100


# ===========================================================================
# N3 — context veto (overlay on N0 or on a chosen challenger)
# ===========================================================================

def n3_veto_wrap(meta, base_kind, base_build, tp_dist_fn, mult):
    """tp_dist_fn(entry_idx, entry_price, direction) -> this trade's OWN
    TP-distance-% reference for the obstruction zone. Wraps base_build so a
    vetoed entry returns None (simulate() then simply skips it)."""
    def build(entry_idx, entry_price, direction):
        piv = meta["piv_high5"] if direction > 0 else meta["piv_low5"]
        tp_dist_pct = tp_dist_fn(entry_idx, entry_price, direction)
        obstructed, _ = overhead_obstructed(piv, entry_idx, entry_price, direction,
                                            tp_dist_pct, mult)
        if obstructed:
            return None
        return base_build(entry_idx, entry_price, direction)
    return base_kind, build


# ===========================================================================
# N4 — ATR-scaled
# ===========================================================================

def n4_builder(meta, target_mult, stop_mult):
    def build(entry_idx, entry_price, direction):
        a = float(meta["atr_arr"][entry_idx]) if entry_idx < len(meta["atr_arr"]) else float("nan")
        atr_pct = (a / entry_price * 100) if (a == a and entry_price > 0) else float("nan")
        if not (atr_pct == atr_pct) or atr_pct <= 0:
            return None
        return dict(stop_pct=stop_mult * atr_pct, target_pct=target_mult * atr_pct,
                   max_hold_bars=meta["max_hold_bars"])
    return "static", build


# ===========================================================================
# main driver
# ===========================================================================

def run_policy(candles, entries, kind, build, funding):
    raw = simulate(candles, entries, kind, build, funding=funding)
    return trades_to_stats(raw), raw


def main():
    print("=" * 78)
    print("ROUND 65 — GIVE THE NEWS TRADE EYES")
    print("=" * 78)

    print("\nLoading cached data (no network calls)...")
    btc1h_full = fetch_bybit_deep("1h", "BTCUSDT")
    funding_hist = fetch_funding_history("BTCUSDT")
    news = pd.read_parquet("data_watcherguru_history.parquet")
    print(f"  BTC 1h: {len(btc1h_full)} bars, {btc1h_full['timestamp'].iloc[0]:%Y-%m-%d} -> "
         f"{btc1h_full['timestamp'].iloc[-1]:%Y-%m-%d}")
    print(f"  WatcherGuru: {len(news)} posts, "
         f"{news['utc_timestamp'].min():%Y-%m-%d} -> {news['utc_timestamp'].max():%Y-%m-%d}")

    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    mask = ((btc1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
           (btc1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d_span = btc1h_full[mask].reset_index(drop=True)
    n, i_tr, i_va = split_points(d_span)
    print(f"  news-span slice: {len(d_span)} bars "
         f"({d_span['timestamp'].iloc[0]:%Y-%m-%d} -> {d_span['timestamp'].iloc[-1]:%Y-%m-%d}) "
         f"| train->{d_span['timestamp'].iloc[i_tr]:%Y-%m-%d} "
         f"val->{d_span['timestamp'].iloc[i_va]:%Y-%m-%d} (TEST SEALED, never sliced beyond i_va)")

    # ---- everything below only ever touches [0:i_va] ----
    d = d_span.iloc[:i_va].reset_index(drop=True)          # test rows dropped from memory entirely
    entries_all = build_news_entries(d, news)
    print(f"  {len(entries_all)} directional entries over [0:i_va] "
         f"({sum(1 for _, dd in entries_all if dd > 0)} long / "
         f"{sum(1 for _, dd in entries_all if dd < 0)} short)")

    funding_full = align_funding(d, funding_hist)
    train_c = d.iloc[0:i_tr].reset_index(drop=True)
    val_c = d.iloc[i_tr:i_va].reset_index(drop=True)
    train_entries = [(i, dd) for i, dd in entries_all if i < i_tr]
    val_entries = [(i - i_tr, dd) for i, dd in entries_all if i_tr <= i < i_va]
    fund_train = funding_full.iloc[0:i_tr].reset_index(drop=True)
    fund_val = funding_full.iloc[i_tr:i_va].reset_index(drop=True)

    meta_train = slice_meta(train_c)
    meta_val = slice_meta(val_c)
    print(f"  train: {len(train_entries)} entries, {i_tr} bars | "
         f"val: {len(val_entries)} entries, {i_va - i_tr} bars")
    print(f"  R45B/step43 floors: >= {MIN_TRAIN_TRADES} train / >= {MIN_VAL_TRADES} val trades")

    results = {}   # label -> dict(train=stats, val=stats, verdict=..., raw_train=..., raw_val=...)

    def register(label, kind, build_train, build_val):
        tr_stats, tr_raw = run_policy(train_c, train_entries, kind, build_train, fund_train)
        va_stats, va_raw = run_policy(val_c, val_entries, kind, build_val, fund_val)
        results[label] = dict(train=tr_stats, val=va_stats,
                              verdict=verdict_for(tr_stats, va_stats),
                              raw_train=tr_raw, raw_val=va_raw)
        print(f"  {label:<28} train n={tr_stats['n']:>4} exp ${tr_stats['expectancy']:>8,.2f} "
             f"ret {tr_stats['total_return_pct']:>7.1f}%  ||  "
             f"val n={va_stats['n']:>4} exp ${va_stats['expectancy']:>8,.2f} "
             f"ret {va_stats['total_return_pct']:>7.1f}%   [{results[label]['verdict']}]")

    print("\n" + "=" * 78)
    print("N0 — INCUMBENT (TP+2.4%/SL-1.2%/24h)")
    print("=" * 78)
    kind0, b0_tr = n0_builder(meta_train["max_hold_bars"])
    _, b0_va = n0_builder(meta_val["max_hold_bars"])
    register("N0 incumbent", kind0, b0_tr, b0_va)

    print("\n" + "=" * 78)
    print("N1 — STRUCTURE TARGETS (6 configs)")
    print("=" * 78)
    for tp_source in N1_TP_SOURCES:
        for sl_buffer in SL_BUFFERS:
            label = f"N1 {tp_source} buf{sl_buffer}%"
            kind1, b1_tr = n1_builder(meta_train, tp_source, sl_buffer)
            _, b1_va = n1_builder(meta_val, tp_source, sl_buffer)
            register(label, kind1, b1_tr, b1_va)

    print("\n" + "=" * 78)
    print("N2 — STRUCTURE TRAILING (2 configs, k=5 primary)")
    print("=" * 78)
    for sl_buffer in SL_BUFFERS:
        label = f"N2 trail buf{sl_buffer}%"
        kind2, b2_tr = n2_builder(meta_train, sl_buffer)
        _, b2_va = n2_builder(meta_val, sl_buffer)
        register(label, kind2, b2_tr, b2_va)
    # k=8 spot-check footnote (best buffer only, decided after seeing k=5 above)
    best_n2_buf = min(SL_BUFFERS, key=lambda b: -results[f"N2 trail buf{b}%"]["train"]["expectancy"])
    kind2k8, b2k8_tr = n2_builder(meta_train, best_n2_buf, k=K_SWING_SPOTCHECK)
    _, b2k8_va = n2_builder(meta_val, best_n2_buf, k=K_SWING_SPOTCHECK)
    register(f"N2 trail buf{best_n2_buf}% k=8 (spot-check)", kind2k8, b2k8_tr, b2k8_va)

    print("\n" + "=" * 78)
    print("N4 — ATR-SCALED (2 configs)")
    print("=" * 78)
    for tmult, smult in ATR_PAIRS:
        label = f"N4 {tmult:.1f}x/{smult:.1f}xATR"
        kind4, b4_tr = n4_builder(meta_train, tmult, smult)
        _, b4_va = n4_builder(meta_val, tmult, smult)
        register(label, kind4, b4_tr, b4_va)

    # ---- select the single strongest N1/N2 challenger, by TRAIN expectancy ----
    n1n2_labels = [lbl for lbl in results if lbl.startswith("N1 ") or lbl.startswith("N2 ")]
    best_label = max(n1n2_labels, key=lambda lbl: results[lbl]["train"]["expectancy"])
    print(f"\nStrongest single N1/N2 challenger by TRAIN expectancy: {best_label} "
         f"(train ${results[best_label]['train']['expectancy']:+,.2f}, "
         f"val ${results[best_label]['val']['expectancy']:+,.2f})")

    print("\n" + "=" * 78)
    print("N3 — CONTEXT VETO (overlay on N0 and on the strongest N1/N2 challenger)")
    print("=" * 78)

    def n0_tp_dist_fn(entry_idx, entry_price, direction):
        return INCUMBENT_TP_PCT

    veto_autopsy = {}
    for mult in VETO_MULTS:
        label = f"N3 veto{mult}x on N0"
        kind_v, bv_tr = n3_veto_wrap(meta_train, kind0, b0_tr, n0_tp_dist_fn, mult)
        _, bv_va = n3_veto_wrap(meta_val, kind0, b0_va, n0_tp_dist_fn, mult)
        register(label, kind_v, bv_tr, bv_va)
        vetoed_tr = len(train_entries) - results[label]["train"]["n"]
        vetoed_va = len(val_entries) - results[label]["val"]["n"]
        veto_autopsy[label] = dict(vetoed_train=vetoed_tr, vetoed_val=vetoed_va)

    is_n1 = best_label.startswith("N1 ")
    if is_n1:
        parts = best_label.split()
        tp_source, sl_buffer = parts[1], float(parts[2].replace("buf", "").replace("%", ""))
        base_kind_tr, base_build_tr = n1_builder(meta_train, tp_source, sl_buffer)
        base_kind_va, base_build_va = n1_builder(meta_val, tp_source, sl_buffer)

        def best_tp_dist_fn_factory(meta, tp_source, sl_buffer):
            def fn(entry_idx, entry_price, direction):
                stop_px = entry_bar_extreme_stop(meta["o"], meta["h"], meta["l"], meta["c"],
                                                 entry_idx, direction, sl_buffer)
                stop_dist_pct = abs(entry_price - stop_px) / entry_price * 100
                piv = (meta["piv_high5"] if direction > 0 else meta["piv_low5"])
                raw = (nearest_pool(piv, entry_idx, entry_price, direction) if tp_source == "pool"
                      else nearest_favorable_swing(piv, entry_idx, entry_price, direction))
                accepted = band_accept(raw, entry_price, stop_dist_pct, direction)
                return (abs(accepted - entry_price) / entry_price * 100
                       if accepted is not None else INCUMBENT_TP_PCT)
            return fn
        tp_dist_tr = best_tp_dist_fn_factory(meta_train, tp_source, sl_buffer)
        tp_dist_va = best_tp_dist_fn_factory(meta_val, tp_source, sl_buffer)
    else:
        sl_buffer = float(best_label.split("buf")[1].replace("%", "").split()[0])
        base_kind_tr, base_build_tr = n2_builder(meta_train, sl_buffer)
        base_kind_va, base_build_va = n2_builder(meta_val, sl_buffer)

        def tp_dist_tr(entry_idx, entry_price, direction):
            # N2 has no fixed target: 2R synthetic reference (2x initial
            # stop distance) — this repo's own established "constructed
            # target" convention (step45b/step59's E4), stated explicitly.
            d_pct = n2_stop_dist_pct(meta_train, sl_buffer, entry_idx, entry_price, direction)
            return 2.0 * d_pct

        def tp_dist_va(entry_idx, entry_price, direction):
            d_pct = n2_stop_dist_pct(meta_val, sl_buffer, entry_idx, entry_price, direction)
            return 2.0 * d_pct

    for mult in VETO_MULTS:
        label = f"N3 veto{mult}x on {best_label}"
        kind_v, bv_tr = n3_veto_wrap(meta_train, base_kind_tr, base_build_tr, tp_dist_tr, mult)
        _, bv_va = n3_veto_wrap(meta_val, base_kind_va, base_build_va, tp_dist_va, mult)
        register(label, kind_v, bv_tr, bv_va)
        vetoed_tr = len(train_entries) - results[label]["train"]["n"]
        vetoed_va = len(val_entries) - results[label]["val"]["n"]
        veto_autopsy[label] = dict(vetoed_train=vetoed_tr, vetoed_val=vetoed_va)

    # ---- veto autopsy: what would the BASE policy have done with the
    # vetoed trades? (were they actually losers?) ----
    print("\n--- VETO AUTOPSY: what got skipped, and would it have lost? ---")
    veto_detail = {}
    for base_display, base_results_key in (
        ("N0", "N0 incumbent"),
        (best_label, best_label),
    ):
        base_tr_raw = results[base_results_key]["raw_train"]
        base_va_raw = results[base_results_key]["raw_val"]
        base_by_time = {(tr["entry_time"], tr["direction"]): tr for tr in base_tr_raw + base_va_raw}
        tp_fn_tr = n0_tp_dist_fn if base_display == "N0" else tp_dist_tr
        tp_fn_va = n0_tp_dist_fn if base_display == "N0" else tp_dist_va
        for mult in VETO_MULTS:
            label = f"N3 veto{mult}x on {base_display}"
            vetoed_pnls = []
            for meta_s, ents, c_slice, tp_fn in (
                (meta_train, train_entries, train_c, tp_fn_tr),
                (meta_val, val_entries, val_c, tp_fn_va),
            ):
                t_arr = pd.DatetimeIndex(c_slice["timestamp"])
                for entry_idx, direction in ents:
                    if entry_idx >= len(c_slice) - 1:
                        continue
                    entry_price = float(c_slice["close"].to_numpy()[entry_idx])
                    piv = meta_s["piv_high5"] if direction > 0 else meta_s["piv_low5"]
                    tp_dist_pct = tp_fn(entry_idx, entry_price, direction)
                    obstructed, _ = overhead_obstructed(piv, entry_idx, entry_price, direction,
                                                        tp_dist_pct, mult)
                    if obstructed:
                        key = (t_arr[entry_idx], direction)
                        if key in base_by_time:
                            vetoed_pnls.append(base_by_time[key]["pnl"])
            n_vet = len(vetoed_pnls)
            mean_pnl = float(np.mean(vetoed_pnls)) if n_vet else 0.0
            win_rate = float(np.mean([p > 0 for p in vetoed_pnls])) if n_vet else float("nan")
            veto_detail[label] = dict(n=n_vet, mean_pnl=mean_pnl, win_rate=win_rate)
            print(f"  {label:<30} vetoed {n_vet} entries that WOULD have traded under {base_display}: "
                 f"mean pnl ${mean_pnl:+,.2f}, win rate {win_rate*100:.1f}%")

    # ---- big-winner / big-loser autopsy ----
    print("\n" + "=" * 78)
    print("BIG-TRADE AUTOPSY — the 3 biggest winners and 3 biggest losers under N0")
    print("=" * 78)
    n0_all = results["N0 incumbent"]["raw_train"] + results["N0 incumbent"]["raw_val"]
    n0_sorted = sorted(n0_all, key=lambda tr: tr["pnl"])
    big_losers = n0_sorted[:3]
    big_winners = n0_sorted[-3:][::-1]

    autopsy_labels = ["N0 incumbent", best_label] + [l for l in n1n2_labels if l != best_label][:0]
    # also show the OTHER family's best-in-class alongside, for a fuller picture
    other_family_prefix = "N2 " if best_label.startswith("N1 ") else "N1 "
    other_labels = [l for l in n1n2_labels if l.startswith(other_family_prefix)]
    other_best = max(other_labels, key=lambda lbl: results[lbl]["train"]["expectancy"]) if other_labels else None
    n4_best = max((l for l in results if l.startswith("N4 ")),
                 key=lambda lbl: results[lbl]["train"]["expectancy"])
    autopsy_policies = ["N0 incumbent", best_label] + ([other_best] if other_best else []) + [n4_best]

    def find_match(label, entry_time, direction):
        pool = results[label]["raw_train"] + results[label]["raw_val"]
        for tr in pool:
            if tr["entry_time"] == entry_time and tr["direction"] == direction:
                return tr
        return None

    for tag, group in (("BIGGEST LOSERS", big_losers), ("BIGGEST WINNERS", big_winners)):
        print(f"\n  --- {tag} (ranked by N0 pnl) ---")
        for tr in group:
            print(f"  entry {tr['entry_time']} dir={tr['direction']:+d}  N0: "
                 f"${tr['pnl']:+,.2f} ({tr['reason']}, {tr['hold_hours']:.1f}h)")
            for label in autopsy_policies[1:]:
                m = find_match(label, tr["entry_time"], tr["direction"])
                if m is None:
                    print(f"      {label:<28} -> not taken (single-slot busy or vetoed)")
                else:
                    print(f"      {label:<28} -> ${m['pnl']:+,.2f} ({m['reason']}, {m['hold_hours']:.1f}h)")

    print("\n" + "=" * 78)
    print("VERDICT SUMMARY")
    print("=" * 78)
    for label, res in results.items():
        beats_both = (res["train"]["expectancy"] > results["N0 incumbent"]["train"]["expectancy"] and
                     res["val"]["expectancy"] > results["N0 incumbent"]["val"]["expectancy"])
        print(f"  {label:<32} verdict={res['verdict']:<20} beats N0 both windows: {beats_both}")

    return dict(results=results, veto_autopsy=veto_autopsy, veto_detail=veto_detail,
               best_label=best_label, big_losers=big_losers, big_winners=big_winners,
               autopsy_policies=autopsy_policies, n_train=len(train_entries),
               n_val=len(val_entries), d_span=d_span, i_tr=i_tr, i_va=i_va, n=n)


if __name__ == "__main__":
    main()
