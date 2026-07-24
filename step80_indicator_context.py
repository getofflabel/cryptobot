"""
step80_indicator_context.py — round 80: INDICATORS USED THE WAY TRADERS
ACTUALLY USE THEM.

Round 76 swept 53 indicators as STANDALONE TRIGGERS ("buy when RSI crosses
30") and concluded indicators don't work. The owner's correction, verbatim
spirit: "hedge funds use indicators, every profitable trader uses
indicators — you're just using it wrong. You have to understand HOW to use
it and WHEN to use it." R76's own conclusion that indicators-as-lone-
triggers are weak is NOT rejected here — what's rejected is treating that
as the final word on indicators generally. This round tests the three ways
professionals actually deploy them, none of which is a lone trigger. Our
own strongest evidence already points this way: CHoCH + CONFLUENCE>=2
(step56) sealed-passed at +$99.52/trade train / stayed positive val, while
each component (CHoCH alone, any single confluence check alone) was weaker
or lost money alone — confirmations inside a context, not triggers.

RESEARCH ONLY. No commits, no live orders. Writes exactly three files:
step80_indicator_context.py (this script), step80_results.md,
step80_full_table.csv. Does not touch dashboard/index.html or any
step79_* file (owned by a concurrent agent).

REUSE, NOT REINVENTION — every non-trivial building block below is
imported unmodified from a prior round, per the mandate:
  - indicator raw-computation wrappers (rsi_osc, macd_hist, stoch_osc,
    cci_osc, willr_osc, di_pair, aroon_osc, vortex_pair, supertrend_signal,
    obv_ma_pair, cmf_osc, mfi_osc, obv_series, ichimoku_cloud_signal) and
    the archetype signal-builders (cross_signal, zero_cross_signal,
    oscillator_hysteresis) — step76_indicators.py, verbatim.
  - the confluence/structure primitives (bos_chain, bias_series_4h,
    train_median_stop_pct) — step56_smc_toolkit.py, verbatim.
  - the 5-axis scenario classifier's TREND axis (build_trend_axis_1h) and
    VOL axis (build_vol_axis) — step63_rehab.py (imported the same way
    step66_scenario_mind.py imports them), verbatim.
  - engine plumbing (run_backtest, day_trade_signal, split_points,
    champ_aligned, hours_to_bars, days_to_bars, bar_hours) —
    backtest.py / step43_daytrade.py / step41_shorts.py, verbatim.
  - R76's OWN "everywhere" numbers for the volatility-family comparison
    are read directly from step76_full_table.csv rather than recomputed —
    same engine, same signal construction, so re-running them would just
    reproduce the same numbers at the cost of runtime.

THE THREE DESIGNS (see module docstring sections below for exact mechanics)
1. COMMITTEE OF VOTES (build_committee_row) — 7 indicator-STATE votes
   (not crossovers), fired only inside an EXISTING TREND CONTEXT (the same
   4h champ+BOS-chain bias step56/step66 already established as this
   project's context definition), entries require >=K votes agreeing in
   the context's own direction. K swept 1..5 to see the dose-response
   shape.
2. CONFIRMATION ON OWNED SETUPS (build_confirmation_row) — three setups
   this project has already validated (RSI3 dip-buy in a champ uptrend,
   Donchian(20,20) breakout, CHoCH structure flip) are re-run with each of
   4 indicator confirmations (MACD histogram sign, ADX>20, OBV vs its own
   MA, Stochastic %K direction) ANDed onto the SAME entries, SAME exit
   rules — does the confirmation add information over the raw setup?
3. CONTEXT-CONDITIONAL HOME REGIME (build_regime_row) — momentum
   oscillators (RSI/Stoch/CCI/Williams) tested ONLY while build_trend_axis_1h
   reads "ranging" (their textbook home); trend indicators (MACD/ADX/
   SuperTrend/Aroon/Vortex) tested ONLY while it reads trending (either
   direction); volume tools tested ONLY while volume itself is elevated
   (above its own trailing 20-bar median) — all compared against R76's own
   "everywhere" number for the SAME family/config/tf. Volatility (Bollinger
   breakout, context-free, vs BB-inside-KC squeeze release, which IS the
   squeeze-to-expansion transition by construction) is read directly off
   R76's own table — the squeeze-release row already IS this family's
   home-regime test, re-running it would just reproduce R76's own numbers.

ENGINE / GAUNTLET DISCIPLINE (identical to step56/step66/step76):
- run_backtest: costs always on (CostModel defaults), execution="maker",
  real funding via align_funding. No lookahead (signal at bar N close
  fills at bar N+1 open) — see strategy.py's own docstring.
- Chronological 60/20/20 split per timeframe (split_points). Sealed 20%
  test slice NEVER touched — only train (0:i_tr) and val (i_tr:i_va) are
  computed. Selection is by TRAIN expectancy; val is read once.
- MIN_TRAIN_TRADES=30, MIN_VAL_TRADES=8 — same floors as step76.
- TIMEFRAMES: 1h and 15m (the owner's preferred), BTC primary. ETH is the
  MANDATORY transfer check on every row that SURVIVES on BTC (positive
  train AND val expectancy, both floors cleared) — run only on survivors,
  never used for selection, matching R76's own "92 of 94 BTC survivors
  died on ETH" discipline (the reason this check is non-negotiable).
- PARAMETERS reuse R76's own sets (textbook defaults) — no re-fishing.
"""

import warnings

import numpy as np
import pandas as pd
import ta

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import days_to_bars
from step43_daytrade import (
    bar_hours,
    champ_aligned,
    day_trade_signal,
    hold_stats,
    hours_to_bars,
    split_points,
)
from step56_smc_toolkit import bias_series_4h, bos_chain, train_median_stop_pct
from step63_rehab import build_trend_axis_1h, build_vol_axis
from step76_indicators import (
    aroon_osc,
    cci_osc,
    cmf_osc,
    construct,
    cross_signal,
    di_pair,
    ichimoku_cloud_signal,
    macd_hist,
    mfi_osc,
    obv_ma_pair,
    obv_series,
    oscillator_hysteresis,
    rsi_osc,
    stoch_osc,
    supertrend_signal,
    vortex_pair,
    willr_osc,
    zero_cross_signal,
)
from strategy import atr as atr_
from strategy import donchian_breakout, rsi as rsi_, vol_gated_ma

warnings.filterwarnings("ignore")

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
TF_LIST = ["1h", "15m"]

RESULTS = []          # -> step80_full_table.csv
REPLAY = []            # entries needed to rebuild a SURVIVOR config on ETH


# ---------------------------------------------------------------------------
# data loading (mirrors step76's load_data exactly)
# ---------------------------------------------------------------------------

FRAMES, FUND = {}, {}


def load_data():
    for asset, symbol in [("BTC", "BTCUSDT"), ("ETH", "ETHUSDT")]:
        FRAMES[asset] = {}
        FUND[asset] = {}
        fund_hist = fetch_funding_history(symbol)
        for tf in ["15m", "1h", "4h"]:
            d = fetch_bybit_deep(tf, symbol)
            FRAMES[asset][tf] = d
            FUND[asset][tf] = align_funding(d, fund_hist)


# ---------------------------------------------------------------------------
# shared scoring plumbing (same conventions as step76/step43)
# ---------------------------------------------------------------------------

def score(d, sig, f, i_tr, i_va, stop_pct=None, target_pct=None):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution="maker",
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def mk_row(approach, family, indicator, config, tf, asset, tr, va,
           stop_pct=None, target_pct=None, max_hold_h=None, **extra):
    med_h, mean_h = hold_stats(tr, va)
    row = {
        "approach": approach, "family": family, "indicator": indicator,
        "config": config, "tf": tf, "asset": asset,
        "stop%": stop_pct, "target%": target_pct, "max_hold_h": max_hold_h,
        "tr_n": len(tr.trades), "tr_exp": round(tr.expectancy, 4),
        "tr_win%": round(tr.win_rate * 100, 2),
        "tr_ret%": round(tr.total_return_pct, 2),
        "va_n": len(va.trades), "va_exp": round(va.expectancy, 4),
        "va_win%": round(va.win_rate * 100, 2),
        "va_ret%": round(va.total_return_pct, 2),
        "va_dd%": round(va.max_drawdown_pct, 2),
        "med_hold_h": med_h,
        "verdict": verdict_for(tr, va),
    }
    row.update(extra)
    RESULTS.append(row)
    return row


def gate_signal_by_regime(sig, regime_mask):
    """Bidirectional analogue of step76's apply_filter: a new position
    (flat -> nonzero, or a direction FLIP) is only permitted while
    regime_mask is True at that bar; once open, ride to the signal's own
    exit even if the regime later turns false (a regime gate permits/
    blocks entries, it does not intra-trade flatten — identical philosophy
    to step76's apply_filter, generalized from long-only 0/1 to -1/0/1)."""
    s = sig.fillna(0).to_numpy()
    m = regime_mask.fillna(False).to_numpy()
    out = np.zeros(len(s))
    pos = 0.0
    for i in range(len(s)):
        want = s[i]
        if pos == 0.0:
            if want != 0.0 and m[i]:
                pos = want
        else:
            if want == 0.0:
                pos = 0.0
            elif want != pos:
                pos = want if m[i] else 0.0
        out[i] = pos
    return pd.Series(out, index=sig.index)


# ===========================================================================
# APPROACH 1 — COMMITTEE OF VOTES
# ===========================================================================
# 7 indicator-STATE votes (booleans, not crossovers), fired only inside an
# EXISTING TREND CONTEXT (this project's own established context
# definition: step56's bias_series_4h — 4h vol_gated_ma sign AND 4h
# BOS-chain direction must AGREE — read onto the trading tf via
# champ_aligned, exactly as step56/step66's T3 already do). Entries require
# >=K of the 7 votes to agree IN THE CONTEXT'S OWN DIRECTION. K swept
# 1..5 to see whether expectancy rises monotonically with K (the R56
# confluence signature).
#
# THE 7 VOTES (each a boolean per bar, long-vote / short-vote where
# directional, else a shared gate counted toward both):
#   1. RSI(14) in its oversold zone (<30) for long / overbought (>70) short
#   2. MACD(12,26,9) histogram RISING for long / FALLING for short
#      (momentum building, not a crossover)
#   3. Price above the 4h Ichimoku cloud (aligned down) for long / below
#      for short
#   4. ADX(14) > 20 — "a trend exists" — shared gate, counted for both
#      directions (same textbook use as R76's own ADX-filtered DI cross)
#   5. Stochastic(14,3,3) %K turning UP from below 30 for long / turning
#      DOWN from above 70 for short
#   6. Volume above its own trailing 20-bar median — shared gate (real
#      participation behind the move), counted for both directions
#   7. OBV above its own 20-bar MA for long / below for short (volume-flow
#      confirms price)
# ===========================================================================

N_VOTES = 7


def build_committee_votes(d, frame4h):
    rsi14 = rsi_osc(d, 14)
    macdh = macd_hist(d, fast=12, slow=26, sig=9)
    stochk = stoch_osc(d, n=14, smooth_k=3, smooth_d=3)
    adx_val = ta.trend.ADXIndicator(d["high"], d["low"], d["close"], window=14).adx()
    vol_med = d["volume"].rolling(20).median()
    obv = obv_series(d)
    obv_ma = obv.rolling(20).mean()
    ich_sig_4h = ichimoku_cloud_signal(frame4h, tenkan_n=9, kijun_n=26, span_b_n=52)
    ich_aligned = champ_aligned(frame4h, ich_sig_4h, d)

    v_rsi_l, v_rsi_s = (rsi14 < 30).fillna(False), (rsi14 > 70).fillna(False)
    v_macd_l = (macdh > macdh.shift(1)).fillna(False)
    v_macd_s = (macdh < macdh.shift(1)).fillna(False)
    v_ichi_l, v_ichi_s = (ich_aligned == 1), (ich_aligned == -1)
    v_adx = (adx_val > 20).fillna(False)
    v_stoch_l = ((stochk < 30) & (stochk > stochk.shift(1))).fillna(False)
    v_stoch_s = ((stochk > 70) & (stochk < stochk.shift(1))).fillna(False)
    v_vol = (d["volume"] > vol_med).fillna(False)
    v_obv_l, v_obv_s = (obv > obv_ma).fillna(False), (obv < obv_ma).fillna(False)

    count_long = (v_rsi_l.astype(int) + v_macd_l.astype(int) + v_ichi_l.astype(int)
                  + v_adx.astype(int) + v_stoch_l.astype(int) + v_vol.astype(int)
                  + v_obv_l.astype(int))
    count_short = (v_rsi_s.astype(int) + v_macd_s.astype(int) + v_ichi_s.astype(int)
                   + v_adx.astype(int) + v_stoch_s.astype(int) + v_vol.astype(int)
                   + v_obv_s.astype(int))
    return count_long, count_short


def build_committee_signal(d, frame4h, K):
    count_long, count_short = build_committee_votes(d, frame4h)
    bias4h = bias_series_4h(frame4h)
    bias_on_tf = champ_aligned(frame4h, bias4h, d)
    enter_long = ((bias_on_tf == 1) & (count_long >= K)).fillna(False)
    enter_short = ((bias_on_tf == -1) & (count_short >= K)).fillna(False)
    return enter_long, enter_short


def run_committee(asset, tf, K):
    d, f = FRAMES[asset][tf], FUND[asset][tf]
    frame4h = FRAMES[asset]["4h"]
    n, i_tr, i_va = split_points(d)
    enter_long, enter_short = build_committee_signal(d, frame4h, K)

    atr_pct = atr_(d, 14) / d["close"] * 100
    stop_pct = min(max(1.5 * float(atr_pct.iloc[:i_tr].median()), 0.25), 8.0)
    target_pct = 2.0 * stop_pct
    max_hold_bars = hours_to_bars(d, 48)

    sig = day_trade_signal(d, enter_long, enter_short, max_hold_bars)
    tr, va = score(d, sig, f, i_tr, i_va, stop_pct, target_pct)
    indicator_label = f"{N_VOTES}-vote committee (context-gated)"
    row = mk_row("1-committee", "committee", indicator_label,
                 f"K>={K}", tf, asset, tr, va, stop_pct, target_pct, 48, K=K)
    REPLAY.append({"key": ("1-committee", "committee", f"K>={K}", tf, indicator_label),
                  "kind": "committee", "K": K})
    return row


def run_approach1():
    for tf in TF_LIST:
        for K in (1, 2, 3, 4, 5):
            run_committee("BTC", tf, K)


# ===========================================================================
# APPROACH 2 — CONFIRMATION ON SETUPS WE ALREADY OWN
# ===========================================================================
# Three setups this project has already validated in prior rounds, each
# re-run RAW (no confirmation) and then with each of 4 indicator
# confirmations ANDed onto the SAME entry bar, SAME exit rule (does the
# indicator add information over what we already trust?):
#   SETUP A — RSI3 dip-buy in a champ uptrend (step59's "STRIKES" / T5 in
#     step66): 4h champ (vol_gated_ma 20/100, gate1.5) aligned down AND
#     RSI(3) < 15. Bracket TP+4.5%/SL-1.5%/48h (the incumbent's own, T5).
#   SETUP B — Donchian(20,20) breakout (the fixed base every R76 filter
#     row was gated against): close > prior 20-bar high. stop = 1.5x
#     train-median ATR%, target = 2x stop, max_hold 240 bars (~10 trading
#     days at 1h, same absolute horizon at 15m via hours_to_bars).
#   SETUP C — CHoCH structure flip, k=8 (step56 family2): the first BOS
#     event against the prevailing 1h/15m structure. stop = train-median
#     distance to the opposite structure point, target = 2x stop (step56's
#     own construction).
# CONFIRMATIONS (indicator STATE at the entry bar, matching direction):
#   MACD histogram sign, ADX(14)>20 (shared gate), OBV vs its own 20-MA,
#   Stochastic %K direction — plus ALL-4-COMBINED.
# ===========================================================================

def confirmation_masks(d):
    macdh = macd_hist(d, fast=12, slow=26, sig=9)
    adx_val = ta.trend.ADXIndicator(d["high"], d["low"], d["close"], window=14).adx()
    obv = obv_series(d)
    obv_ma = obv.rolling(20).mean()
    stochk = stoch_osc(d, n=14, smooth_k=3, smooth_d=3)
    return {
        "MACD-hist>0": ((macdh > 0).fillna(False), (macdh < 0).fillna(False)),
        "ADX>20": ((adx_val > 20).fillna(False), (adx_val > 20).fillna(False)),
        "OBV-vs-MA20": ((obv > obv_ma).fillna(False), (obv < obv_ma).fillna(False)),
        "Stoch-%K-direction": ((stochk > stochk.shift(1)).fillna(False),
                                (stochk < stochk.shift(1)).fillna(False)),
    }


def setup_rsi3_dip(asset, tf):
    d, f = FRAMES[asset][tf], FUND[asset][tf]
    frame4h = FRAMES[asset]["4h"]
    champ4h = vol_gated_ma(frame4h, fast=20, slow=100, min_atr_pct=1.5)
    champ_on = champ_aligned(frame4h, champ4h, d)
    r3 = rsi_(d["close"], 3)
    el = ((champ_on == 1) & (r3 < 15)).fillna(False)
    es = pd.Series(False, index=d.index)
    return dict(name="A-RSI3-dip-in-uptrend", d=d, f=f, el=el, es=es,
               stop_pct=1.5, target_pct=4.5, mh_bars=hours_to_bars(d, 48))


def setup_donchian(asset, tf):
    d, f = FRAMES[asset][tf], FUND[asset][tf]
    n, i_tr, i_va = split_points(d)
    hi = d["high"].rolling(20).max().shift(1)
    el = (d["close"] > hi).fillna(False)
    es = pd.Series(False, index=d.index)
    atr_pct_train = atr_(d, 14).iloc[:i_tr] / d["close"].iloc[:i_tr] * 100
    stop_pct = float(1.5 * atr_pct_train.median())
    target_pct = 2.0 * stop_pct
    return dict(name="B-donchian20-breakout", d=d, f=f, el=el, es=es,
               stop_pct=stop_pct, target_pct=target_pct, mh_bars=hours_to_bars(d, 240))


def setup_choch(asset, tf, k=8):
    d, f = FRAMES[asset][tf], FUND[asset][tf]
    n, i_tr, i_va = split_points(d)
    bos = bos_chain(d, k)
    el, es = bos["choch_long"], bos["choch_short"]
    dist_long = (d["close"] - bos["lsl"]) / d["close"] * 100
    dist_short = (bos["lsh"] - d["close"]) / d["close"] * 100
    mask = el | es
    dist = pd.Series(np.nan, index=d.index)
    dist = dist.mask(el, dist_long)
    dist = dist.mask(es, dist_short)
    stop_pct = train_median_stop_pct(d, i_tr, mask, dist)
    if stop_pct is None:
        stop_pct = 1.0
    target_pct = stop_pct * 2.0
    return dict(name="C-CHoCH-k8", d=d, f=f, el=el, es=es,
               stop_pct=stop_pct, target_pct=target_pct, mh_bars=days_to_bars(d, 10))


SETUP_BUILDERS = {"A-RSI3-dip-in-uptrend": setup_rsi3_dip,
                  "B-donchian20-breakout": setup_donchian,
                  "C-CHoCH-k8": setup_choch}


def run_confirmation(asset, tf, setup_name, confirm_name=None):
    spec = SETUP_BUILDERS[setup_name](asset, tf)
    d, f = spec["d"], spec["f"]
    n, i_tr, i_va = split_points(d)
    el0, es0 = spec["el"], spec["es"]

    if confirm_name is None:
        el, es, tag = el0, es0, "RAW (no confirmation)"
    elif confirm_name == "ALL-4-combined":
        masks = confirmation_masks(d)
        el = el0.copy(); es = es0.copy()
        for cl, cs in masks.values():
            el = el & cl
            es = es & cs
        tag = "ALL-4-combined"
    else:
        cl, cs = confirmation_masks(d)[confirm_name]
        el, es = el0 & cl, es0 & cs
        tag = confirm_name

    sig = day_trade_signal(d, el, es, spec["mh_bars"])
    tr, va = score(d, sig, f, i_tr, i_va, spec["stop_pct"], spec["target_pct"])
    max_hold_h = spec["mh_bars"] * bar_hours(d)
    row = mk_row("2-confirmation", "confirmation", spec["name"], tag, tf, asset, tr, va,
                 spec["stop_pct"], spec["target_pct"], max_hold_h, confirm=tag)
    REPLAY.append({"key": ("2-confirmation", "confirmation", tag, tf, spec["name"]),
                  "kind": "confirmation", "setup_name": setup_name, "confirm_name": confirm_name})
    return row


def run_approach2():
    confirm_names = [None, "MACD-hist>0", "ADX>20", "OBV-vs-MA20",
                     "Stoch-%K-direction", "ALL-4-combined"]
    for tf in TF_LIST:
        for setup_name in SETUP_BUILDERS:
            for confirm_name in confirm_names:
                run_confirmation("BTC", tf, setup_name, confirm_name)


# ===========================================================================
# APPROACH 3 — CONTEXT-CONDITIONAL "HOME REGIME" USE
# ===========================================================================
# Every indicator family has a textbook home regime. Momentum oscillators
# (RSI/Stoch/CCI/Williams %R) are RANGE tools — R76 tested them everywhere,
# including in trends, where they are not supposed to work. Trend
# indicators (MACD/ADX-DMI/SuperTrend/Aroon/Vortex) are supposed to work
# ONLY when a trend actually exists. Volume tools are supposed to matter
# ONLY when volume itself is elevated. Each family's R76 SIGNAL-mode config
# (same param set, same tf, same signal construction — imported verbatim)
# is regime-gated via gate_signal_by_regime and compared against R76's own
# "everywhere" row for the identical family/config/tf, read straight out of
# step76_full_table.csv (re-running it would only reproduce the same
# number).
# ===========================================================================

MOMENTUM_HOME = [
    # (indicator label, R76 config label, archetype, compute_fn, params, extra)
    ("RSI OB/OS", "14/30-70", "oscillator", rsi_osc, {"n": 14},
     {"lower": 30, "upper": 70, "exit_mid": 50}),
    ("Stochastic extremes", "14/3/3", "oscillator", stoch_osc,
     {"n": 14, "smooth_k": 3, "smooth_d": 3}, {"lower": 20, "upper": 80, "exit_mid": 50}),
    ("CCI extremes", "20", "oscillator", cci_osc, {"n": 20},
     {"lower": -100, "upper": 100, "exit_mid": 0}),
    ("Williams %R extremes", "14", "oscillator", willr_osc, {"n": 14},
     {"lower": -80, "upper": -20, "exit_mid": -50}),
]

TREND_HOME = [
    ("MACD histogram 0-cross", "12/26/9", "zero_cross", macd_hist,
     {"fast": 12, "slow": 26, "sig": 9}, {"mid": 0.0}),
    ("ADX/DMI DI cross", "14", "two_line", di_pair, {"n": 14}, {}),
    ("SuperTrend", "ATR14xMult3", "direct", supertrend_signal, {"atr_n": 14, "mult": 3}, {}),
    ("Aroon oscillator 0-cross", "14", "zero_cross", aroon_osc, {"n": 14}, {"mid": 0.0}),
    ("Vortex VI+/VI- cross", "14", "two_line", vortex_pair, {"n": 14}, {}),
]

VOLUME_HOME = [
    ("OBV trend (vs own MA)", "20", "two_line", obv_ma_pair, {"ma_n": 20}, {}),
    ("CMF 0-cross", "20", "zero_cross", cmf_osc, {"n": 20}, {"mid": 0.0}),
    ("MFI extremes", "14/20-80", "oscillator", mfi_osc, {"n": 14},
     {"lower": 20, "upper": 80, "exit_mid": 50}),
]


def build_family_signal(archetype, compute_fn, params, extra, d):
    sig, gate = construct(archetype, compute_fn, params, extra, d)
    return sig


def run_regime(asset, tf, regime_name, indicator, config, archetype, compute_fn, params, extra):
    d, f = FRAMES[asset][tf], FUND[asset][tf]
    frame4h = FRAMES[asset]["4h"]
    n, i_tr, i_va = split_points(d)
    sig = build_family_signal(archetype, compute_fn, params, extra, d)

    if regime_name == "ranging":
        trend_axis = build_trend_axis_1h(frame4h, d)
        regime_mask = pd.Series((trend_axis == "ranging").to_numpy(), index=d.index)
    elif regime_name == "trending":
        trend_axis = build_trend_axis_1h(frame4h, d)
        regime_mask = pd.Series((trend_axis != "ranging").to_numpy(), index=d.index)
    elif regime_name == "volume-elevated":
        vol_med = d["volume"].rolling(20).median()
        regime_mask = (d["volume"] > vol_med).fillna(False)
    else:
        raise ValueError(regime_name)

    gated_sig = gate_signal_by_regime(sig, regime_mask)
    tr, va = score(d, gated_sig, f, i_tr, i_va)
    family_tag = {"ranging": "momentum(home=ranging)", "trending": "trend(home=trending)",
                 "volume-elevated": "volume(home=elevated-volume)"}[regime_name]
    row = mk_row("3-regime", family_tag, indicator, config, tf, asset, tr, va,
                 regime=regime_name, pct_bars_in_regime=round(float(regime_mask.mean() * 100), 1))
    REPLAY.append({"key": ("3-regime", family_tag, config, tf, indicator),
                  "kind": "regime", "regime_name": regime_name, "indicator": indicator,
                  "config": config, "archetype": archetype, "compute_fn": compute_fn,
                  "params": params, "extra": extra})
    return row


def run_approach3():
    for tf in TF_LIST:
        for indicator, config, arche, fn, params, extra in MOMENTUM_HOME:
            run_regime("BTC", tf, "ranging", indicator, config, arche, fn, params, extra)
        for indicator, config, arche, fn, params, extra in TREND_HOME:
            run_regime("BTC", tf, "trending", indicator, config, arche, fn, params, extra)
        for indicator, config, arche, fn, params, extra in VOLUME_HOME:
            run_regime("BTC", tf, "volume-elevated", indicator, config, arche, fn, params, extra)


def load_r76_everywhere_comparators():
    """Pull R76's OWN 'everywhere' (unfiltered signal-mode, BTC) numbers
    for the exact family/config/tf rows this round regime-gates, plus the
    volatility family's squeeze-release-vs-plain-breakout comparison,
    directly from step76_full_table.csv — same engine, same construction,
    re-running would only reproduce the same numbers."""
    df76 = pd.read_csv("step76_full_table.csv")
    sig_btc = df76[(df76["mode"] == "signal") & (df76["asset"] == "BTC")]

    everywhere_rows = []
    all_home = [("RSI OB/OS", "14/30-70"), ("Stochastic extremes", "14/3/3"),
               ("CCI extremes", "20"), ("Williams %R extremes", "14"),
               ("MACD histogram 0-cross", "12/26/9"), ("ADX/DMI DI cross", "14"),
               ("SuperTrend", "ATR14xMult3"), ("Aroon oscillator 0-cross", "14"),
               ("Vortex VI+/VI- cross", "14"), ("OBV trend (vs own MA)", "20"),
               ("CMF 0-cross", "20"), ("MFI extremes", "14/20-80")]
    for indicator, config in all_home:
        for tf in TF_LIST:
            m = sig_btc[(sig_btc["indicator"] == indicator) & (sig_btc["config"] == config)
                       & (sig_btc["tf"] == tf)]
            if len(m):
                r = m.iloc[0]
                everywhere_rows.append({
                    "indicator": indicator, "config": config, "tf": tf,
                    "tr_n": r["tr_n"], "tr_exp": r["tr_exp"], "va_n": r["va_n"], "va_exp": r["va_exp"],
                })

    volatility_rows = []
    for tf in TF_LIST:
        bo = sig_btc[(sig_btc["indicator"] == "Bollinger breakout") & (sig_btc["config"] == "20/2")
                    & (sig_btc["tf"] == tf)]
        sq = sig_btc[(sig_btc["indicator"] == "BB-inside-KC squeeze release")
                    & (sig_btc["config"] == "BB20/2 KC20/1.5") & (sig_btc["tf"] == tf)]
        if len(bo) and len(sq):
            volatility_rows.append({
                "tf": tf,
                "everywhere_indicator": "Bollinger breakout (context-free)",
                "everywhere_tr_exp": float(bo.iloc[0]["tr_exp"]), "everywhere_tr_n": int(bo.iloc[0]["tr_n"]),
                "everywhere_va_exp": float(bo.iloc[0]["va_exp"]), "everywhere_va_n": int(bo.iloc[0]["va_n"]),
                "home_indicator": "BB-inside-KC squeeze release (squeeze->expansion, home regime by construction)",
                "home_tr_exp": float(sq.iloc[0]["tr_exp"]), "home_tr_n": int(sq.iloc[0]["tr_n"]),
                "home_va_exp": float(sq.iloc[0]["va_exp"]), "home_va_n": int(sq.iloc[0]["va_n"]),
            })
    return pd.DataFrame(everywhere_rows), pd.DataFrame(volatility_rows)


# ===========================================================================
# ETH TRANSFER CHECK — mandatory on every row that SURVIVES on BTC
# ===========================================================================

def run_eth_transfer():
    survivor_keys = {
        (r["approach"], r["family"], r["config"], r["tf"], r["indicator"])
        for r in RESULTS if r["verdict"] == "SURVIVOR" and r["asset"] == "BTC"
    }
    survivor_entries = [e for e in REPLAY if e["key"] in survivor_keys]
    n_done = 0
    for e in survivor_entries:
        tf = e["key"][3]
        if e["kind"] == "committee":
            run_committee("ETH", tf, e["K"])
            n_done += 1
        elif e["kind"] == "confirmation":
            run_confirmation("ETH", tf, e["setup_name"], e["confirm_name"])
            n_done += 1
        elif e["kind"] == "regime":
            run_regime("ETH", tf, e["regime_name"], e["indicator"], e["config"],
                      e["archetype"], e["compute_fn"], e["params"], e["extra"])
            n_done += 1
    print(f"\nETH transfer check: {len(survivor_entries)} BTC survivor configs, "
         f"{n_done} replayed on ETH.")
    return n_done


# ===========================================================================
# output
# ===========================================================================

def write_outputs():
    df = pd.DataFrame(RESULTS)
    df.to_csv("step80_full_table.csv", index=False)
    print(f"\nwrote step80_full_table.csv: {len(df)} rows")
    return df


def main():
    print("Loading data (cached parquet, no network expected)...")
    load_data()
    for asset in ("BTC", "ETH"):
        for tf in ("15m", "1h", "4h"):
            print(f"  {asset} {tf}: {len(FRAMES[asset][tf])} bars")

    print("\nAPPROACH 1 — committee of votes (K=1..5, context-gated)...")
    run_approach1()
    print(f"  {len(RESULTS)} rows cumulative")

    print("APPROACH 2 — confirmation on owned setups...")
    run_approach2()
    print(f"  {len(RESULTS)} rows cumulative")

    print("APPROACH 3 — context-conditional home-regime use...")
    run_approach3()
    print(f"  {len(RESULTS)} rows cumulative")

    print("\nETH transfer check on BTC survivors...")
    run_eth_transfer()

    df = write_outputs()
    everywhere_df, volatility_df = load_r76_everywhere_comparators()
    everywhere_df.to_csv("step80_everywhere_comparators.csv", index=False)
    volatility_df.to_csv("step80_volatility_comparison.csv", index=False)

    n_survivors_btc = sum(1 for r in RESULTS if r["verdict"] == "SURVIVOR" and r["asset"] == "BTC")
    print(f"\nTOTAL: {len(df)} rows. BTC SURVIVORS: {n_survivors_btc}. "
         f"ETH transfer rows: {sum(1 for r in RESULTS if r['asset']=='ETH')}")
    return df, everywhere_df, volatility_df


if __name__ == "__main__":
    print("=" * 70)
    print("STEP 80 — indicators used the way traders actually use them")
    print("=" * 70)
    main()
