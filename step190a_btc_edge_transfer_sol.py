"""
step190a_btc_edge_transfer_sol.py — SOL, THIRD-ASSET TRANSFER TEST of BTC's
five validated edges (MARKET_PLAYBOOKS.md BITCOIN section), UNCHANGED
config, per the standing transfer rule (R89: a sealed-passed BTC config
replayed unchanged on nine fresh assets, 6/9 failed — the real transfer
test is the unchanged replay, not a resemblance check).

sol-trader is the desk's third-asset skeptic (R88: the chart-read veto
passed on BTC+XRP but showed NO information content on SOL specifically —
"two assets agreeing is a hypothesis, not evidence"). This script is that
same discipline applied to all five currently-validated BTC edges at once,
run properly as a program rather than a spot-check.

THE FIVE EDGES REPLAYED, EXACT SOURCE CONFIG (no threshold re-tuned):
  1. 1h CHoCH k8 + confluence>=2, tgt2x, train-median structural stop
     (step56_smc_toolkit.py family5_confluence, CHoCH tool, threshold=2,
     target_mult=2.0 — the exact cell that sealed-passed +$99.52/t on BTC).
  2. 4h hidden RSI(14) divergence, k8 swings, buffer 0.35%, tgt3x, hold48h,
     champion-gated (step58_divergence_mtf.py family1_divergences, the
     exact cell that sealed-passed +$52.03/t on BTC).
  3. 4h trend, vol_gated_ma fast20/slow100/min_atr_pct=1.5, allow_short=
     False, live -8% SL (step54_adaptive_ride.py "fixed-1.5" config, R54
     sealed-proof incumbent).
  4. 1h RSI3<10 washout dip-buy, 1d-trend gate, turn-candle guard, ATR-
     scaled stop (1.0xATR capped 1.0%/floored 0.05%), target=1.5x stop,
     max hold 4h (step83_eye_filter.py build_B — daily_pick.py's ACTUAL
     LIVE washout spec, ground truth per that file's own docstring). This
     exact config was ALREADY replayed on SOL in round 88 (maker
     execution): before -$47.13/t x27, after-veto -$35.35/t, both losers,
     control percentile 68th (no information content). Reproduced here
     under this desk's TAKER standard for a fresh, house-standard number.
  5. 1h news momentum, FIRST-BAR-MOVE direction, stop1.2%/target2.4%
     (tmult2.0)/hold24h (step45b_news_events.py A-news-momentum family,
     the exact cell that sealed-passed +$20.81/t on BTC — first strategy
     ever to pass the program's sealed test).

EXECUTION: taker, always, per this desk's standard — NOTE this differs
from the source BTC rounds' maker convention (step43/45b/54/56/58 all use
maker as their repo-wide day-trade default). Taker costs MORE (6bps vs
2bps per side), so this is a STRICTER bar than the original BTC passes
cleared, never a laxer one. Stated once here, applies to every cell below.

DATA: Bybit-cached SOL 1h/4h/1d + funding (data_bybit_SOLUSDT_*), the same
source and convention every other round in this repo uses for backtest
history (BLOFIN_API_REFERENCE.md governs LIVE position/account fields —
read not computed — not backtest OHLCV history, which this repo has always
sourced from Bybit's deeper cache).

CHANCE BASELINE: for each edge, a 100-draw random-entry null (same n_long/
n_short, same stop/target/hold geometry, same taker costs, random bar
picks) — see step190_common.random_entry_baseline. This isolates entry-
timing skill from the geometry/cost structure, which cannot inflate the
result since it's identical in the null.

THICKNESS: edge as % of notional AND as a multiple of SOL's own taker
round-trip cost (12bps: 2 x (6 fee + 1 half-spread + 2 slippage)). Under
5x is a REJECT per house standard.

Research only. Writes step190a_btc_edge_transfer_sol.py (this file),
step190a_results.md, step190a_table.csv, and appends lines to
step190_family_map.md. No git commands, no live orders, no live-file
edits. Sealed test never touched (every gauntlet here is train+val only).
"""

from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import config
from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings, days_to_bars  # noqa: F401 (available for later families)
from step43_daytrade import (
    CHAMP_KW, HARD_STOP_CAP, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    champ_aligned, day_trade_signal, hold_stats, hours_to_bars, split_points,
    verdict_for,
)
from step45b_news_events import align_events, classify_frame, make_bool_array
from step56_smc_toolkit import (
    CONF_DEPTH, CONF_EXPIRE_DAYS, CONF_FIB_EXPIRE_DAYS, CONF_FILL,
    CONF_HOLD_DAYS, CONF_TOL, STOP_CAP_PCT as CHOCH_STOP_CAP_PCT,
    STOP_FLOOR_PCT as CHOCH_STOP_FLOOR_PCT, bias_series_4h, bos_chain,
    equilibrium, fib_entries, fvg_signals, leg_tracker, liquidity_pools,
    sweep_events, train_median_stop_pct,
)
from step58_divergence_mtf import STOP_CAP_SWING, divergence_events, swing_stop_pct
from step83_eye_filter import daily_trend_on_tf
import strategy as STRAT
from step190_common import (
    ROUND_TRIP_COST_BPS, adverse_excursion_stats, append_family_line,
    avg_notional, chance_percentile, combined_expectancy, random_entry_baseline,
    score_taker,
)

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


RNG_SEED = 190
N_DRAWS = 100
ASSET = "SOL"
SYM = f"{ASSET}USDT"


def load_frames():
    d1h = fetch_bybit_deep("1h", SYM)
    d4h = fetch_bybit_deep("4h", SYM)
    d1d = fetch_bybit_deep("1d", SYM)
    funding_hist = fetch_funding_history(SYM)
    f1h = align_funding(d1h, funding_hist)
    f4h = align_funding(d4h, funding_hist)
    return d1h, d4h, d1d, f1h, f4h, funding_hist


def row(edge, tf, cfg, tr, va, stop_pct, target_pct, max_hold_h,
       chance_pctile=None, notional=None):
    exp, n_t = combined_expectancy(tr, va)
    ae = adverse_excursion_stats(tr, va)
    edge_pct = mult = float("nan")
    if notional and notional > 0 and not np.isnan(exp):
        edge_pct = exp / notional * 100
        mult = (edge_pct * 100) / ROUND_TRIP_COST_BPS
    return dict(
        edge=edge, tf=tf, config=cfg,
        tr_n=len(tr.trades), tr_exp=tr.expectancy, tr_win=tr.win_rate * 100,
        va_n=len(va.trades), va_exp=va.expectancy, va_win=va.win_rate * 100,
        combined_n=n_t, combined_exp=exp,
        stop_pct=stop_pct, target_pct=target_pct, max_hold_h=max_hold_h,
        chance_pctile=chance_pctile, avg_notional=notional,
        edge_pct_notional=edge_pct, thickness_x_cost=mult,
        worst_adverse_pct=ae["worst_pct"], p5_adverse_pct=ae["p5_pct"],
        median_move_pct=ae["median_pct"],
        verdict=verdict_for(tr, va),
    )


# ===========================================================================
# EDGE 1 — 1h CHoCH k8 + confluence>=2, tgt2x
# ===========================================================================

def edge1_choch_confluence(d1h, d4h, f1h):
    n, i_tr, i_va = split_points(d1h)
    bias4h = bias_series_4h(d4h)
    bias_1h = champ_aligned(d4h, bias4h, d1h)

    k = 8
    d = d1h
    bos = bos_chain(d, k)
    discount, premium, eq, lsh, lsl = equilibrium(d, k)
    pool_high, pool_low = liquidity_pools(d, k, CONF_TOL)
    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, CONF_DEPTH)
    window = hours_to_bars(d, 24)
    swept_recent_long = (sweep_long.astype(int).rolling(window, min_periods=1)
                          .max().fillna(0).astype(bool))
    swept_recent_short = (sweep_short.astype(int).rolling(window, min_periods=1)
                           .max().fillna(0).astype(bool))
    el_fvg, es_fvg, dl_fvg, ds_fvg, ab, ar = fvg_signals(
        d, CONF_FILL, days_to_bars(d, CONF_EXPIRE_DAYS))
    bull_low, bull_high, bear_low, bear_high = leg_tracker(
        d, k, days_to_bars(d, CONF_FIB_EXPIRE_DAYS))
    el_fib, es_fib, dl_fib, ds_fib, extl, exts, lz, sz = fib_entries(
        d, bull_low, bull_high, bear_low, bear_high, 0.618, 0.79)

    dist_bos_long = (d["close"] - bos["lsl"]) / d["close"] * 100
    dist_bos_short = (bos["lsh"] - d["close"]) / d["close"] * 100

    bias_long = (bias_1h == 1)
    bias_short = (bias_1h == -1)
    count_long = (bias_long.astype(int) + discount.astype(int) + lz.astype(int)
                  + swept_recent_long.astype(int) + ab.astype(int))
    count_short = (bias_short.astype(int) + premium.astype(int) + sz.astype(int)
                   + swept_recent_short.astype(int) + ar.astype(int))

    choch_long, choch_short = bos["choch_long"], bos["choch_short"]
    threshold = 2
    el = choch_long & (count_long >= threshold)
    es = choch_short & (count_short >= threshold)
    mask = el | es
    n_events = int(mask.iloc[:i_va].sum())
    if n_events == 0:
        log("  EDGE1 CHoCH+confluence: ZERO qualifying events on SOL train+val")
        return None

    dist = pd.Series(np.nan, index=d.index)
    dist = dist.mask(el, dist_bos_long)
    dist = dist.mask(es, dist_bos_short)
    stop_pct = train_median_stop_pct(d, i_tr, mask, dist,
                                     cap=CHOCH_STOP_CAP_PCT, floor=CHOCH_STOP_FLOOR_PCT)
    if stop_pct is None:
        log("  EDGE1 CHoCH+confluence: no TRAIN qualifying entries -> can't size a stop")
        return None
    target_pct = stop_pct * 2.0
    mh_bars = days_to_bars(d, CONF_HOLD_DAYS)
    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = score_taker(d, sig, f1h, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)

    n_long, n_short = int(el.sum()), int(es.sum())
    rng = np.random.default_rng(RNG_SEED + 1)
    draws = random_entry_baseline(d, f1h, i_tr, i_va, n_long, n_short, mh_bars,
                                  stop_pct, target_pct, rng, n_draws=N_DRAWS)
    exp, _ = combined_expectancy(tr, va)
    pctile = chance_percentile(exp, draws)
    notional = avg_notional(tr, va)

    log(f"  EDGE1 CHoCH k8 thresh>=2 tgt2x: stop={stop_pct:.2f}% tgt={target_pct:.2f}% "
       f"| train n={len(tr.trades)} exp=${tr.expectancy:.2f} | val n={len(va.trades)} "
       f"exp=${va.expectancy:.2f} | combined ${exp:.2f}/t | chance pctile {pctile:.1f} "
       f"| notional ${notional:.0f} | verdict {verdict_for(tr, va)}")
    return row("1_CHoCH_confluence>=2", "1h", "k8 thresh>=2 tgt2x", tr, va,
              stop_pct, target_pct, CONF_HOLD_DAYS * 24, pctile, notional)


# ===========================================================================
# EDGE 2 — 4h hidden RSI(14) divergence, k8, buf0.35%, tgt3x, hold48h
# ===========================================================================

def edge2_hidden_divergence(d4h, f4h):
    n, i_tr, i_va = split_points(d4h)
    champ4h = STRAT.vol_gated_ma(d4h, **CHAMP_KW)
    osc = STRAT.rsi(d4h["close"], 14)
    k = 8
    (long_reg, short_reg, long_hid, short_hid, low_ext, high_ext) = \
        divergence_events(d4h, osc, k, champ4h)
    el, es = long_hid, short_hid
    if el.sum() == 0 and es.sum() == 0:
        log("  EDGE2 hidden divergence: ZERO qualifying swings on SOL")
        return None

    buffer_pct = 0.35
    stop_l = swing_stop_pct(d4h["close"], low_ext, el, i_tr, buffer_pct, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d4h["close"], high_ext, es, i_tr, buffer_pct, STOP_CAP_SWING)
    n_l, n_s = int(el.sum()), int(es.sum())
    stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else STOP_CAP_SWING
    target_pct = min(3.0 * stop_pct, 3 * STOP_CAP_SWING)
    max_hold_h = 48
    mh_bars = hours_to_bars(d4h, max_hold_h)
    sig = day_trade_signal(d4h, el, es, mh_bars)
    tr, va = score_taker(d4h, sig, f4h, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)

    rng = np.random.default_rng(RNG_SEED + 2)
    draws = random_entry_baseline(d4h, f4h, i_tr, i_va, n_l, n_s, mh_bars,
                                  stop_pct, target_pct, rng, n_draws=N_DRAWS)
    exp, _ = combined_expectancy(tr, va)
    pctile = chance_percentile(exp, draws)
    notional = avg_notional(tr, va)

    log(f"  EDGE2 4h hidden RSI14 div k8 buf0.35 tgt3x hold48h: stop={stop_pct:.2f}% "
       f"tgt={target_pct:.2f}% | train n={len(tr.trades)} exp=${tr.expectancy:.2f} "
       f"| val n={len(va.trades)} exp=${va.expectancy:.2f} | combined ${exp:.2f}/t "
       f"| chance pctile {pctile:.1f} | notional ${notional:.0f} | verdict {verdict_for(tr, va)}")
    return row("2_4h_hidden_RSI_divergence", "4h", "RSI14 k8 buf0.35% tgt3x hold48h",
              tr, va, stop_pct, target_pct, max_hold_h, pctile, notional)


# ===========================================================================
# EDGE 3 — 4h trend, vol_gated_ma 20/100, min_atr_pct=1.5, -8% SL
# ===========================================================================

def edge3_vol_gated_trend(d4h, f4h):
    n, i_tr, i_va = split_points(d4h)
    sig = STRAT.vol_gated_ma(d4h, fast=20, slow=100, min_atr_pct=1.5, allow_short=False)
    tr, va = score_taker(d4h, sig, f4h, i_tr, i_va, stop_pct=8.0, target_pct=None)

    atr_pct = STRAT.atr(d4h, 14) / d4h["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    live_atr_now = float(atr_pct.iloc[-1])
    gate_open_share = float((atr_pct >= 1.5).mean() * 100)

    exp, n_t = combined_expectancy(tr, va)
    notional = avg_notional(tr, va)
    log(f"  EDGE3 4h vol-gated trend 20/100 gate1.5% -8%SL: train n={len(tr.trades)} "
       f"exp=${tr.expectancy:.2f} | val n={len(va.trades)} exp=${va.expectancy:.2f} "
       f"| combined ${exp:.2f}/t | SOL median train ATR%={med_atr_train:.3f}% "
       f"(BTC's own train-window ATR runs ~0.4-0.9%, see MARKET_PLAYBOOKS) "
       f"| gate open {gate_open_share:.1f}% of all 4h bars | live ATR%={live_atr_now:.3f}% "
       f"| notional ${notional:.0f} | verdict {verdict_for(tr, va)}")

    # chance baseline: this is a trend-following state-machine (position
    # persists on trend, not a fixed-hold entry), so the random-entry-count
    # null doesn't directly apply the same way as the day-trade families.
    # Instead: how many of the trend's OWN entries are needed vs a random
    # walk-forward long-flat coin flip of the same duty-cycle (time-in-
    # market share)? Report the duty cycle explicitly instead of forcing
    # an ill-fitting draw-based baseline.
    time_in_market_pct = float((sig.fillna(0) != 0).mean() * 100)
    return dict(
        edge="3_4h_vol_gated_trend", tf="4h", config="fast20/slow100 gate1.5% -8%SL",
        tr_n=len(tr.trades), tr_exp=tr.expectancy, tr_win=tr.win_rate * 100,
        va_n=len(va.trades), va_exp=va.expectancy, va_win=va.win_rate * 100,
        combined_n=n_t, combined_exp=exp,
        stop_pct=8.0, target_pct=None, max_hold_h=None,
        chance_pctile=None, avg_notional=notional,
        edge_pct_notional=(exp / notional * 100 if notional else float("nan")),
        thickness_x_cost=((exp / notional * 100 * 100 / ROUND_TRIP_COST_BPS)
                          if notional else float("nan")),
        worst_adverse_pct=adverse_excursion_stats(tr, va)["worst_pct"],
        p5_adverse_pct=adverse_excursion_stats(tr, va)["p5_pct"],
        median_move_pct=adverse_excursion_stats(tr, va)["median_pct"],
        verdict=verdict_for(tr, va),
        note=(f"chance baseline N/A (state-machine trend, not fixed-hold entries) — "
             f"time-in-market {time_in_market_pct:.1f}%, gate open {gate_open_share:.1f}%, "
             f"SOL median train ATR% {med_atr_train:.3f}%"),
    )


# ===========================================================================
# EDGE 4 — 1h RSI3<10 washout dip-buy, live daily_pick.py spec (build_B)
# ===========================================================================

WASHOUT_RSI_N = 3
WASHOUT_RSI_TH = 10
STOP_ATR_MULT = 1.0
WASHOUT_STOP_CAP_PCT = 1.0
WASHOUT_STOP_FLOOR_PCT = 0.05
TARGET_STOP_MULT = 1.5
WASHOUT_MAX_HOLD_H = 4.0


def edge4_washout_dipbuy(d1h, d1d, f1h):
    n, i_tr, i_va = split_points(d1h)
    r3 = STRAT.rsi(d1h["close"], WASHOUT_RSI_N)
    trend1d = daily_trend_on_tf(d1d, d1h)
    turn_up = (d1h["close"] > d1h["open"]) & (d1h["close"] > d1h["close"].shift(1))
    turn_down = (d1h["close"] < d1h["open"]) & (d1h["close"] < d1h["close"].shift(1))
    el = (r3 < WASHOUT_RSI_TH) & (trend1d == "up") & turn_up
    es = (r3 > (100 - WASHOUT_RSI_TH)) & (trend1d == "down") & turn_down
    el, es = el.fillna(False), es.fillna(False)

    atr_pct = STRAT.atr(d1h, 14) / d1h["close"] * 100
    med_atr_train = float(atr_pct.iloc[:i_tr].median())
    stop_pct = min(STOP_ATR_MULT * med_atr_train, WASHOUT_STOP_CAP_PCT)
    stop_pct = max(stop_pct, WASHOUT_STOP_FLOOR_PCT)
    target_pct = TARGET_STOP_MULT * stop_pct
    mh_bars = hours_to_bars(d1h, WASHOUT_MAX_HOLD_H)
    sig = day_trade_signal(d1h, el, es, mh_bars)
    tr, va = score_taker(d1h, sig, f1h, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)

    n_long, n_short = int(el.sum()), int(es.sum())
    rng = np.random.default_rng(RNG_SEED + 4)
    draws = random_entry_baseline(d1h, f1h, i_tr, i_va, n_long, n_short, mh_bars,
                                  stop_pct, target_pct, rng, n_draws=N_DRAWS)
    exp, _ = combined_expectancy(tr, va)
    pctile = chance_percentile(exp, draws)
    notional = avg_notional(tr, va)

    log(f"  EDGE4 1h RSI3<10 washout (live daily_pick.py spec, TAKER): stop={stop_pct:.2f}% "
       f"tgt={target_pct:.2f}% | train n={len(tr.trades)} exp=${tr.expectancy:.2f} "
       f"| val n={len(va.trades)} exp=${va.expectancy:.2f} | combined ${exp:.2f}/t "
       f"| chance pctile {pctile:.1f} | notional ${notional:.0f} | verdict {verdict_for(tr, va)} "
       f"| cf. round-88 MAKER replay already on record: -$47.13/t x27, veto -$35.35/t, "
       f"control pctile 68th (established, not re-derived here)")
    return row("4_1h_RSI3_washout_dipbuy", "1h", "RSI3<10 1d-trend-gate turn-guard hold4h",
              tr, va, stop_pct, target_pct, WASHOUT_MAX_HOLD_H, pctile, notional)


# ===========================================================================
# EDGE 5 — 1h news momentum, FIRST-BAR-MOVE, stop1.2%/tgt2.4%/hold24h
# ===========================================================================

def edge5_news_momentum(d1h_full, funding_hist):
    news_raw = pd.read_parquet("data_watcherguru_history.parquet")
    news = classify_frame(news_raw)
    relevant = news[news["relevant"]]
    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()

    mask = ((d1h_full["timestamp"] >= news_min - pd.Timedelta(hours=24)) &
            (d1h_full["timestamp"] <= news_max + pd.Timedelta(hours=24)))
    d = d1h_full[mask].reset_index(drop=True)
    f = align_funding(d, funding_hist)
    n, i_tr, i_va = split_points(d)
    log(f"  EDGE5 news window sliced to SOL 1h: {n} bars "
       f"{d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")

    floor_rel, trad_rel, valid_rel = align_events(d, relevant["utc_timestamp"])
    trad_rel = trad_rel[valid_rel]
    trad_rel = trad_rel[trad_rel < len(d)]
    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    move_sign = np.sign(closes[trad_rel] - opens[trad_rel])
    up_idx = trad_rel[move_sign > 0]
    down_idx = trad_rel[move_sign < 0]

    el = make_bool_array(len(d), up_idx)
    es = make_bool_array(len(d), down_idx)
    if el.sum() == 0 and es.sum() == 0:
        log("  EDGE5 news momentum: no qualifying events")
        return None

    stop_pct = min(1.2, HARD_STOP_CAP)  # HARD_STOP_CAP=1.7 (imported); 1.2 is already under it
    target_pct = stop_pct * 2.0   # 2.4%
    max_hold_h = 24
    mh_bars = hours_to_bars(d, max_hold_h)
    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = score_taker(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)

    n_long, n_short = int(el.sum()), int(es.sum())
    rng = np.random.default_rng(RNG_SEED + 5)
    draws = random_entry_baseline(d, f, i_tr, i_va, n_long, n_short, mh_bars,
                                  stop_pct, target_pct, rng, n_draws=N_DRAWS)
    exp, _ = combined_expectancy(tr, va)
    pctile = chance_percentile(exp, draws)
    notional = avg_notional(tr, va)

    log(f"  EDGE5 1h news momentum FIRST-BAR-MOVE stop1.2/tgt2.4/hold24h: "
       f"train n={len(tr.trades)} exp=${tr.expectancy:.2f} | val n={len(va.trades)} "
       f"exp=${va.expectancy:.2f} | combined ${exp:.2f}/t | chance pctile {pctile:.1f} "
       f"| notional ${notional:.0f} | verdict {verdict_for(tr, va)} "
       f"| n_up={len(up_idx)} n_down={len(down_idx)} events (same event set as BTC — "
       f"WatcherGuru is asset-agnostic macro/crypto news, only SOL's own price reaction differs)")
    return row("5_1h_news_momentum_firstbar", "1h", "stop1.2% tgt2.4% hold24h",
              tr, va, stop_pct, target_pct, max_hold_h, pctile, notional)


# ===========================================================================
# main
# ===========================================================================

def main():
    log("STEP 190a — SOL third-asset transfer test of BTC's five validated edges")
    log(f"execution=taker always; SOL taker round-trip cost = {ROUND_TRIP_COST_BPS:.1f}bps "
       f"(config.fee_bps() -> BlofinExchange.TAKER_FEE_BPS, published rate, same across BloFin "
       f"perpetuals incl. SOL — not computed)")
    d1h, d4h, d1d, f1h, f4h, funding_hist = load_frames()
    n1, i_tr1, i_va1 = split_points(d1h)
    n4, i_tr4, i_va4 = split_points(d4h)
    log(f"SOL 1h: {n1} bars {d1h['timestamp'].iloc[0]:%Y-%m-%d}->{d1h['timestamp'].iloc[-1]:%Y-%m-%d} "
       f"| train->{d1h['timestamp'].iloc[i_tr1]:%Y-%m-%d} val->{d1h['timestamp'].iloc[i_va1]:%Y-%m-%d} (test sealed)")
    log(f"SOL 4h: {n4} bars {d4h['timestamp'].iloc[0]:%Y-%m-%d}->{d4h['timestamp'].iloc[-1]:%Y-%m-%d} "
       f"| train->{d4h['timestamp'].iloc[i_tr4]:%Y-%m-%d} val->{d4h['timestamp'].iloc[i_va4]:%Y-%m-%d} (test sealed)")

    rows = []
    log("\nEDGE 1/5 -- CHoCH+confluence...")
    r1 = edge1_choch_confluence(d1h, d4h, f1h)
    if r1: rows.append(r1)

    log("\nEDGE 2/5 -- 4h hidden RSI divergence...")
    r2 = edge2_hidden_divergence(d4h, f4h)
    if r2: rows.append(r2)

    log("\nEDGE 3/5 -- 4h vol-gated trend...")
    r3 = edge3_vol_gated_trend(d4h, f4h)
    if r3: rows.append(r3)

    log("\nEDGE 4/5 -- 1h RSI3 washout dip-buy...")
    r4 = edge4_washout_dipbuy(d1h, d1d, f1h)
    if r4: rows.append(r4)

    log("\nEDGE 5/5 -- 1h news momentum...")
    r5 = edge5_news_momentum(d1h, funding_hist)
    if r5: rows.append(r5)

    table = pd.DataFrame(rows)
    table.to_csv("step190a_table.csv", index=False)
    log(f"\nwrote step190a_table.csv ({len(table)} rows)")

    for r in rows:
        thick = r.get("thickness_x_cost", float("nan"))
        thick_str = f"{thick:.1f}x" if thick == thick else "n/a"
        pct = r.get("chance_pctile")
        pct_str = f"{pct:.0f}th pctile" if pct is not None and pct == pct else "N/A (see note)"
        append_family_line(
            f"- **{r['edge']}** [{r['tf']}, unchanged-config replay] `{r['config']}` — "
            f"{r['verdict']} | combined {r['combined_n']}t ${r['combined_exp']:.2f}/t "
            f"(train {r['tr_n']}t ${r['tr_exp']:.2f}, val {r['va_n']}t ${r['va_exp']:.2f}) "
            f"| chance baseline: {pct_str} | thickness {thick_str} of {ROUND_TRIP_COST_BPS:.0f}bps "
            f"taker cost | worst realized move {r['worst_adverse_pct']:.2f}% "
            f"| source: BTC's own sealed/validated number in MARKET_PLAYBOOKS.md, config unchanged"
        )
    log(f"appended {len(rows)} lines to step190_family_map.md")
    log(f"total runtime: {round(time.time() - T0, 1)}s")


if __name__ == "__main__":
    main()
