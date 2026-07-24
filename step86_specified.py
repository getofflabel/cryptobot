"""
step86_specified.py — round 86: RETEST THE FAMILIES WE UNDER-SPECIFIED.

R85 collected 36 documented winning-trade setups and the CONDITIONS each one
required before the setup counts (step85_setups.csv / step85_winning_trades.md).
Comparing that checklist to this project's own prior tests found several of
our "this doesn't work" verdicts measured tests that omitted conditions
practitioners treat as mandatory — most concretely: R58's regular RSI
divergence test (1 survivor in 96 configs) fired on ANY confirmed swing, with
no level gate, no confirmation candle, and no trend-extreme restriction,
while R58's HIDDEN divergence test implemented its one required gate (trend
alignment) and sealed-PASSED. This round codes the eight proposals from
step85 section 5 and runs each ALONGSIDE its under-specified predecessor so
every family shows a real before/after.

RESEARCH ONLY. No commits, no live orders. Writes step86_specified.py (this
file), step86_results.md, step86_table.csv.

EIGHT PROPOSALS -> FIVE FAMILIES (1-4 share one base signal, so they are one
family with four gate variants plus the baseline):

  FAMILY A — regular RSI/MACD-hist divergence (reuses step58's swings() and
    divergence event logic verbatim):
    A0  before   — R58's exact regular divergence, unconditional (baseline)
    A1  proposal-1 level-gated       — divergence extreme within N% of a
        prior confirmed swing (same swings() definition) or a step56
        liquidity pool, at least M bars old
    A2  proposal-2 confirmation-gated — entry delayed to the first
        subsequent close back through the intervening structural point
        (the swing between the two divergence swings), within a wait window
    A3  proposal-3 trend-extreme-restricted — divergence only fires when
        the PRE-existing move is objectively extended: |close - SMA100| in
        ATR units clears a threshold at the divergence bar (this project's
        own objective operationalization of "at a trend's exhaustion",
        chosen over the step85 draft's "champion regime age" phrasing
        because it is unambiguous and directly testable — stated plainly)
    A4  proposal-4 ALL THREE COMBINED — the practitioner's actual stack:
        level gate AND trend-extreme gate pre-filter the raw divergence
        events, THEN the confirmation gate shifts entry to the trigger bar

  FAMILY B — MACD crossover (proposal 5):
    B0  before — bare MACD-histogram 0-line crossover, event-entry
    B1  after  — crossover only counts with a Donchian(20) breakout
        confirming within W bars (0 = same bar, 5 = within 5 bars)

  FAMILY C — breakout (proposal 6):
    C0  before — R76's exact BTC 1h SIGNAL-mode breakout survivors
        (Bollinger breakout 20/2.5; BB-in-KC squeeze release BB20/2 KC20/1.5)
    C1  after  — same two configs, entry additionally gated: the breakout
        (or squeeze-release) bar's volume >= 1.2x / 1.5x its own trailing
        20-bar average volume

  FAMILY D — liquidity sweep (proposal 7, a genuinely new family):
    D0  before — naive fade-the-raid: enter AT the sweep bar itself
        (reuses step56's liquidity_pools/sweep_events verbatim, same grid
        shape as step56's own family1_sweep)
    D1  after  — sweep -> wait for a Market-Structure-Shift (close breaks
        the nearest OPPOSING confirmed swing point) WITH a displacement bar
        (range > disp_mult x ATR14) -> entry there, never at the sweep.
        Stop beyond the sweep wick extreme; target the opposing liquidity
        pool level (falls back to the MSS swing point if no pool is active)

  FAMILY E — opening-range breakout (proposal 8):
    E0  before — step43's exact session-breakout (first-H-hour UTC range,
        bare level-cross entry)
    E1  after  — same range definition, entry additionally requires the
        breakout bar's range > the average of the prior 5 bars' range AND
        the bar's body occupies >= 70% of its own range

DATA + DISCIPLINE (identical to every prior round)
  - Cached BTC 1h/15m/4h + ETH 1h/15m/4h via step7_deep_search.fetch_bybit_deep
    (all cache hits, no network calls) + real funding via step11_round6.
  - Chronological 60/20/20 split per timeframe (split_points, imported).
    Sealed test (final 20%) is NEVER sliced by this script.
  - Selection by TRAIN expectancy only; val is read once, never tuned
    against. MIN_TRAIN_TRADES=30, MIN_VAL_TRADES=8 — same floors as every
    prior round.
  - ETH TRANSFER CHECK IS MANDATORY on anything that clears SURVIVOR on
    BTC (train AND val positive, both floors cleared) — R76's 92-of-94 ETH
    failure is exactly why. Same exact config/params replayed on ETH, stop/
    target distances recalibrated from ETH's OWN train median (the nuisance
    nesting parameter, not a selection choice — same discipline step76 used
    for its own indicator replay).
  - Costs always on: CostModel defaults (6bps taker / 2bps maker, 1bp
    half-spread, 2bp slippage), execution="maker", REAL funding via
    align_funding — the repo standard since step43.
  - Every SURVIVOR row also reports trades/year (train+val trades pooled,
    annualized over the train+val calendar span) — a setup that fires twice
    a year is not deployable regardless of expectancy.

ENGINE NOTE (same approximation every prior round states): run_backtest
takes ONE fixed stop_pct/target_pct per call. Every family here that wants a
per-trade dynamic stop (past a swing, past a sweep wick, an ATR multiple)
follows the repo's established pattern: TRAIN-only median distance, held
fixed across train+val, hard-capped. Stated plainly here and in
step86_results.md.
"""

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    CHAMP_KW, HARD_STOP_CAP, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    bar_hours, day_trade_signal, hold_stats, hours_to_bars,
    score, session_range, split_points, verdict_for,
)
from step56_smc_toolkit import (
    bos_chain, liquidity_pools, sweep_events, train_median_stop_pct,
)
from step58_divergence_mtf import (
    STOP_CAP_SWING, divergence_events, macd_hist, swing_stop_pct, swings,
)
from step76_indicators import bb_bands, kc_bands, squeeze_release_signal
from strategy import atr, donchian_breakout, rsi, vol_gated_ma

STOP_CAP_MACD = 3.0
STOP_CAP_SWEEP = 4.0

RESULTS = []          # every row, both before/after, both assets
BTC_AFTER_SURVIVORS = []   # (family, variant_tag, params-dict) queued for ETH replay


# ---------------------------------------------------------------------------
# shared plumbing
# ---------------------------------------------------------------------------

def mk_row(family, variant, cfg, tf, asset, tr, va, **extra):
    med_h, mean_h = hold_stats(tr, va)
    row = {
        "family": family, "variant": variant, "config": cfg, "tf": tf, "asset": asset,
        "tr_n": len(tr.trades), "tr_exp": round(tr.expectancy, 4),
        "tr_win%": round(tr.win_rate * 100, 2), "tr_ret%": round(tr.total_return_pct, 2),
        "tr_dd%": round(tr.max_drawdown_pct, 2),
        "va_n": len(va.trades), "va_exp": round(va.expectancy, 4),
        "va_win%": round(va.win_rate * 100, 2), "va_ret%": round(va.total_return_pct, 2),
        "va_dd%": round(va.max_drawdown_pct, 2),
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr, va),
    }
    row.update(extra)
    RESULTS.append(row)
    return row


def trades_per_year(tr, va, d, i_tr, i_va):
    n = len(tr.trades) + len(va.trades)
    t0 = d["timestamp"].iloc[0]
    t1 = d["timestamp"].iloc[i_va - 1]
    span_yrs = (t1 - t0).total_seconds() / (365.25 * 86400)
    return round(n / span_yrs, 1) if span_yrs > 0 else float("nan")


def queue_for_eth(family, variant, tf, params):
    if variant != "before":   # only "after" (properly-specified) configs are the round's
        BTC_AFTER_SURVIVORS.append((family, variant, tf, params))  # headline transfer check,
        # but see run_eth_transfer(): BEFORE-variant BTC survivors are ALSO transfer-checked
        # (queued separately below) since the round wants an honest before/after on ETH too.


# ===========================================================================
# FAMILY A — regular divergence: level / confirmation / trend-extreme gates
# ===========================================================================

DIV_OSC = {"RSI14": lambda d: rsi(d["close"], 14), "MACDhist": lambda d: macd_hist(d["close"])}


def swing_level_pool(d, k):
    """All confirmed swing high/low PRICES (same swings() definition R58's
    divergence family already uses), each tagged with the bar index at
    which it first becomes knowable (per swings()' own shift(k) discipline)
    — i.e. proposal 1's 'prior confirmed swing high/low' candidate pool."""
    conf_high, conf_low = swings(d["high"], d["low"], k)
    hi_np, lo_np = d["high"].to_numpy(), d["low"].to_numpy()
    hi_idx = np.where(conf_high.to_numpy())[0]
    lo_idx = np.where(conf_low.to_numpy())[0]
    levels = [(int(i), float(hi_np[i - k])) for i in hi_idx] + \
             [(int(i), float(lo_np[i - k])) for i in lo_idx]
    levels.sort()
    return levels


def level_gate(event_mask, extreme, levels, pool_series, M, N_pct):
    """Proposal 1: True only where the divergence extreme sits within N_pct
    of (a) a same/opposite-side confirmed swing level at least M bars OLDER
    than the event, OR (b) the currently-active step56 liquidity pool value
    at that bar (already causal/historical by construction of pool k)."""
    idxs = np.where(event_mask.fillna(False).to_numpy())[0]
    ext = extreme.to_numpy()
    pool = pool_series.to_numpy()
    lv_idx = np.array([c for c, _ in levels]) if levels else np.array([])
    lv_price = np.array([p for _, p in levels]) if levels else np.array([])
    out = np.zeros(len(event_mask), dtype=bool)
    for j in idxs:
        e = ext[j]
        if np.isnan(e):
            continue
        cands = []
        if lv_idx.size:
            valid = lv_idx <= (j - M)
            if valid.any():
                cands.append(np.min(np.abs(lv_price[valid] - e) / e * 100))
        if not np.isnan(pool[j]):
            cands.append(abs(pool[j] - e) / e * 100)
        if cands and min(cands) <= N_pct:
            out[j] = True
    return pd.Series(out, index=event_mask.index)


def extension_gate(d, event_mask, sma_n, atr_n, thresh):
    """Proposal 3, objective form (per the round-86 brief's own stated
    alternative): distance of close from its own SMA(sma_n), in ATR(atr_n)
    units, must clear `thresh` at the event bar — i.e. the pre-existing move
    is objectively extended/exhausted, not mid-trend."""
    sma = d["close"].rolling(sma_n).mean()
    a = atr(d, atr_n)
    ext_units = ((d["close"] - sma).abs() / a).fillna(0)
    return event_mask.fillna(False) & (ext_units >= thresh)


def confirm_after_level(event_mask, level_arr, close_arr, direction, max_wait):
    """Proposal 2: shift entry from the divergence bar to the first bar
    (strictly after) that closes back through the intervening structural
    level, within max_wait bars. Returns (trigger_mask, {trigger_idx:
    origin_event_idx}) so the caller can carry the ORIGINAL divergence's
    stop-relevant extreme forward to the later trigger bar."""
    n = len(close_arr)
    idxs = np.where(event_mask.fillna(False).to_numpy())[0]
    lv = level_arr.to_numpy()
    out = np.zeros(n, dtype=bool)
    origin_of = {}
    for j in idxs:
        level = lv[j]
        if np.isnan(level):
            continue
        end = min(n, j + 1 + max_wait)
        for t in range(j + 1, end):
            c = close_arr[t]
            ok = (c > level) if direction == "long" else (c < level)
            if ok:
                out[t] = True
                origin_of[t] = j
                break
    return pd.Series(out, index=range(n)), origin_of


def carry_extreme(n, index, origin_of, extreme_arr):
    out = np.full(n, np.nan)
    for t, j in origin_of.items():
        out[t] = extreme_arr[j]
    return pd.Series(out, index=index)


def divergence_events_ext(d, osc, k):
    """R58's regular-flavor divergence loop, reimplemented locally to ALSO
    emit the intervening structural level (proposal 2's confirmation-candle
    reference) — the highest high between the two swing-low origins for a
    bullish setup, the lowest low between the two swing-high origins for a
    bearish setup. long_reg/short_reg/low_extreme/high_extreme are bit-for-
    bit identical to step58.divergence_events' regular-flavor output."""
    conf_high, conf_low = swings(d["high"], d["low"], k)
    conf_high, conf_low = conf_high.to_numpy(), conf_low.to_numpy()
    price_h, price_l = d["high"].to_numpy(), d["low"].to_numpy()
    osc_v = osc.to_numpy()
    n = len(d)
    long_reg = np.zeros(n, dtype=bool)
    short_reg = np.zeros(n, dtype=bool)
    low_extreme = np.full(n, np.nan)
    high_extreme = np.full(n, np.nan)
    confirm_long = np.full(n, np.nan)
    confirm_short = np.full(n, np.nan)
    prev_low = prev_high = None
    for j in range(n):
        if conf_low[j]:
            origin = j - k
            p, o = price_l[origin], osc_v[origin]
            if prev_low is not None and not (np.isnan(o) or np.isnan(prev_low[1])):
                p0, o0, orig0 = prev_low
                if p < p0 and o > o0:
                    long_reg[j] = True
                    low_extreme[j] = p
                    confirm_long[j] = price_h[orig0:origin + 1].max()
            prev_low = (p, o, origin)
        if conf_high[j]:
            origin = j - k
            p, o = price_h[origin], osc_v[origin]
            if prev_high is not None and not (np.isnan(o) or np.isnan(prev_high[1])):
                p0, o0, orig0 = prev_high
                if p > p0 and o < o0:
                    short_reg[j] = True
                    high_extreme[j] = p
                    confirm_short[j] = price_l[orig0:origin + 1].min()
            prev_high = (p, o, origin)
    idx = d.index
    return (pd.Series(long_reg, idx), pd.Series(short_reg, idx),
            pd.Series(low_extreme, idx), pd.Series(high_extreme, idx),
            pd.Series(confirm_long, idx), pd.Series(confirm_short, idx))


def _run_div_config(d, f, i_tr, i_va, el, es, ext_l, ext_h, buffer_pct, tmult, max_hold_h):
    stop_l = swing_stop_pct(d["close"], ext_l, el, i_tr, buffer_pct, STOP_CAP_SWING)
    stop_s = swing_stop_pct(d["close"], ext_h, es, i_tr, buffer_pct, STOP_CAP_SWING)
    n_l, n_s = int(el.sum()), int(es.sum())
    stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else STOP_CAP_SWING
    target_pct = min(tmult * stop_pct, 3 * STOP_CAP_SWING)
    mh_bars = hours_to_bars(d, max_hold_h)
    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return tr, va, stop_pct, target_pct


BUFFER_PCT = 0.15     # fixed secondary param (R58's own tighter buffer)
HOLD_H = 96            # fixed secondary param (R58's longer hold, gives divergence room)


def family_a(frames, funding, meta, asset):
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        for osc_name, osc_fn in DIV_OSC.items():
            osc = osc_fn(d)
            for k in (5, 8):
                (long_reg, short_reg, low_ext, high_ext,
                 confirm_l, confirm_s) = divergence_events_ext(d, osc, k)
                levels = swing_level_pool(d, k)
                pool_high, pool_low = liquidity_pools(d, k, 0.1)
                # candidate "levels" for a bullish (long) setup = swing lows
                # AND highs (resistance-turned-support etc, per step85 §2's
                # "structural level confluence" — symmetric); mirror for short.
                pool_for_long = pool_low.combine_first(pool_high)
                pool_for_short = pool_high.combine_first(pool_low)

                for tmult in (2.0, 3.0):
                    # ---- A0: BEFORE (R58's exact unconditional regular divergence) ----
                    tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, long_reg, short_reg,
                                                      low_ext, high_ext, BUFFER_PCT, tmult, HOLD_H)
                    cfg = f"{osc_name} k{k} regular UNCONDITIONAL tgt{tmult:.0f}x"
                    params = dict(osc=osc_name, k=k, tmult=tmult)
                    row = mk_row("A-divergence", "before", cfg, tf, asset, tr, va,
                                  stop_pct=sp, target_pct=tp,
                                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)
                    if row["verdict"] == "SURVIVOR" and asset == "BTC":
                        BTC_AFTER_SURVIVORS.append(("A-divergence", "before", tf, dict(params, gate="none")))

                    # ---- A1: proposal 1, level-gated ----
                    for M in (50, 100, 200):
                        for N_pct in (0.5, 1.0, 2.0):
                            gl = level_gate(long_reg, low_ext, levels, pool_for_long, M, N_pct)
                            gs = level_gate(short_reg, high_ext, levels, pool_for_short, M, N_pct)
                            tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, gl, gs,
                                                              low_ext, high_ext, BUFFER_PCT, tmult, HOLD_H)
                            cfg = f"{osc_name} k{k} regular LEVEL-GATE M{M} N{N_pct}% tgt{tmult:.0f}x"
                            p = dict(osc=osc_name, k=k, tmult=tmult, M=M, N_pct=N_pct, gate="level")
                            row = mk_row("A-divergence", "after-level", cfg, tf, asset, tr, va,
                                         stop_pct=sp, target_pct=tp,
                                         trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                            if row["verdict"] == "SURVIVOR" and asset == "BTC":
                                BTC_AFTER_SURVIVORS.append(("A-divergence", "after-level", tf, p))

                    # ---- A2: proposal 2, confirmation-gated ----
                    for max_wait in (10, 30):
                        trig_l, orig_l = confirm_after_level(long_reg, confirm_l,
                                                              d["close"].to_numpy(), "long", max_wait)
                        trig_s, orig_s = confirm_after_level(short_reg, confirm_s,
                                                              d["close"].to_numpy(), "short", max_wait)
                        n = len(d)
                        ext_l_trig = carry_extreme(n, d.index, orig_l, low_ext.to_numpy())
                        ext_h_trig = carry_extreme(n, d.index, orig_s, high_ext.to_numpy())
                        tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, trig_l, trig_s,
                                                          ext_l_trig, ext_h_trig, BUFFER_PCT, tmult, HOLD_H)
                        cfg = f"{osc_name} k{k} regular CONFIRM-GATE wait{max_wait} tgt{tmult:.0f}x"
                        p = dict(osc=osc_name, k=k, tmult=tmult, max_wait=max_wait, gate="confirm")
                        row = mk_row("A-divergence", "after-confirm", cfg, tf, asset, tr, va,
                                     stop_pct=sp, target_pct=tp,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("A-divergence", "after-confirm", tf, p))

                    # ---- A3: proposal 3, trend-extreme-restricted ----
                    for thresh in (2.0, 3.0):
                        gl = extension_gate(d, long_reg, 100, 14, thresh)
                        gs = extension_gate(d, short_reg, 100, 14, thresh)
                        tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, gl, gs,
                                                          low_ext, high_ext, BUFFER_PCT, tmult, HOLD_H)
                        cfg = f"{osc_name} k{k} regular TREND-EXTREME>={thresh}ATR tgt{tmult:.0f}x"
                        p = dict(osc=osc_name, k=k, tmult=tmult, ext_thresh=thresh, gate="extreme")
                        row = mk_row("A-divergence", "after-extreme", cfg, tf, asset, tr, va,
                                     stop_pct=sp, target_pct=tp,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("A-divergence", "after-extreme", tf, p))

                    # ---- A4: proposal 4, ALL THREE COMBINED (headline) ----
                    M, N_pct, max_wait = 100, 1.0, 30   # fixed middle-of-grid secondary params
                    for thresh in (2.0, 3.0):
                        gl = level_gate(long_reg, low_ext, levels, pool_for_long, M, N_pct)
                        gs = level_gate(short_reg, high_ext, levels, pool_for_short, M, N_pct)
                        gl = extension_gate(d, gl, 100, 14, thresh)
                        gs = extension_gate(d, gs, 100, 14, thresh)
                        trig_l, orig_l = confirm_after_level(gl, confirm_l, d["close"].to_numpy(),
                                                              "long", max_wait)
                        trig_s, orig_s = confirm_after_level(gs, confirm_s, d["close"].to_numpy(),
                                                              "short", max_wait)
                        n = len(d)
                        ext_l_trig = carry_extreme(n, d.index, orig_l, low_ext.to_numpy())
                        ext_h_trig = carry_extreme(n, d.index, orig_s, high_ext.to_numpy())
                        tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, trig_l, trig_s,
                                                          ext_l_trig, ext_h_trig, BUFFER_PCT, tmult, HOLD_H)
                        cfg = (f"{osc_name} k{k} regular ALL3-COMBINED M{M} N{N_pct}% "
                               f"wait{max_wait} ext>={thresh}ATR tgt{tmult:.0f}x")
                        p = dict(osc=osc_name, k=k, tmult=tmult, M=M, N_pct=N_pct,
                                 max_wait=max_wait, ext_thresh=thresh, gate="all3")
                        row = mk_row("A-divergence", "after-all3", cfg, tf, asset, tr, va,
                                     stop_pct=sp, target_pct=tp,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("A-divergence", "after-all3", tf, p))


def replay_family_a(frames, funding, meta, variant, tf, params):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    osc = DIV_OSC[params["osc"]](d)
    k, tmult = params["k"], params["tmult"]
    long_reg, short_reg, low_ext, high_ext, confirm_l, confirm_s = divergence_events_ext(d, osc, k)

    if variant == "before":
        el, es, ext_l, ext_h = long_reg, short_reg, low_ext, high_ext
    elif variant == "after-level":
        levels = swing_level_pool(d, k)
        pool_high, pool_low = liquidity_pools(d, k, 0.1)
        pool_for_long = pool_low.combine_first(pool_high)
        pool_for_short = pool_high.combine_first(pool_low)
        el = level_gate(long_reg, low_ext, levels, pool_for_long, params["M"], params["N_pct"])
        es = level_gate(short_reg, high_ext, levels, pool_for_short, params["M"], params["N_pct"])
        ext_l, ext_h = low_ext, high_ext
    elif variant == "after-confirm":
        trig_l, orig_l = confirm_after_level(long_reg, confirm_l, d["close"].to_numpy(),
                                              "long", params["max_wait"])
        trig_s, orig_s = confirm_after_level(short_reg, confirm_s, d["close"].to_numpy(),
                                              "short", params["max_wait"])
        n = len(d)
        el, es = trig_l, trig_s
        ext_l = carry_extreme(n, d.index, orig_l, low_ext.to_numpy())
        ext_h = carry_extreme(n, d.index, orig_s, high_ext.to_numpy())
    elif variant == "after-extreme":
        el = extension_gate(d, long_reg, 100, 14, params["ext_thresh"])
        es = extension_gate(d, short_reg, 100, 14, params["ext_thresh"])
        ext_l, ext_h = low_ext, high_ext
    else:  # after-all3
        levels = swing_level_pool(d, k)
        pool_high, pool_low = liquidity_pools(d, k, 0.1)
        pool_for_long = pool_low.combine_first(pool_high)
        pool_for_short = pool_high.combine_first(pool_low)
        gl = level_gate(long_reg, low_ext, levels, pool_for_long, params["M"], params["N_pct"])
        gs = level_gate(short_reg, high_ext, levels, pool_for_short, params["M"], params["N_pct"])
        gl = extension_gate(d, gl, 100, 14, params["ext_thresh"])
        gs = extension_gate(d, gs, 100, 14, params["ext_thresh"])
        trig_l, orig_l = confirm_after_level(gl, confirm_l, d["close"].to_numpy(), "long", params["max_wait"])
        trig_s, orig_s = confirm_after_level(gs, confirm_s, d["close"].to_numpy(), "short", params["max_wait"])
        n = len(d)
        el, es = trig_l, trig_s
        ext_l = carry_extreme(n, d.index, orig_l, low_ext.to_numpy())
        ext_h = carry_extreme(n, d.index, orig_s, high_ext.to_numpy())

    tr, va, sp, tp = _run_div_config(d, f, i_tr, i_va, el, es, ext_l, ext_h, BUFFER_PCT, tmult, HOLD_H)
    cfg = f"[ETH replay] {params['osc']} k{k} regular {variant} tgt{tmult:.0f}x"
    return mk_row("A-divergence", variant, cfg, tf, "ETH", tr, va, stop_pct=sp, target_pct=tp,
                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)


# ===========================================================================
# FAMILY B — MACD crossover with structural confirmation
# ===========================================================================

def macd_cross_events(d):
    h = macd_hist(d["close"])
    cross_up = ((h > 0) & (h.shift(1) <= 0)).fillna(False)
    cross_down = ((h < 0) & (h.shift(1) >= 0)).fillna(False)
    return cross_up, cross_down


def donchian_break_events(d, n=20):
    brk_long = (d["close"] > d["high"].rolling(n).max().shift(1)).fillna(False)
    brk_short = (d["close"] < d["low"].rolling(n).min().shift(1)).fillna(False)
    return brk_long, brk_short


def confirm_within(event_mask, confirm_mask, max_wait):
    """True at the first bar (>= the event bar itself) where confirm_mask
    is True, within max_wait bars after the event. max_wait=0 means the
    SAME bar only."""
    n = len(event_mask)
    ev = event_mask.to_numpy()
    cf = confirm_mask.to_numpy()
    out = np.zeros(n, dtype=bool)
    for j in np.where(ev)[0]:
        end = min(n, j + 1 + max_wait)
        for t in range(j, end):
            if cf[t]:
                out[t] = True
                break
    return pd.Series(out, index=event_mask.index)


def _run_macd_config(d, f, i_tr, i_va, el, es, med_atr, tmult, max_hold_h):
    stop_pct = min(1.2 * med_atr, STOP_CAP_MACD)
    target_pct = tmult * stop_pct
    mh_bars = hours_to_bars(d, max_hold_h)
    sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    return tr, va, stop_pct, target_pct


def family_b(frames, funding, meta, asset):
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        med_atr = meta[tf]["med_atr"]
        cross_up, cross_down = macd_cross_events(d)
        brk_long, brk_short = donchian_break_events(d, 20)

        for tmult in (2.0, 3.0):
            tr, va, sp, tp = _run_macd_config(d, f, i_tr, i_va, cross_up, cross_down,
                                               med_atr, tmult, 72)
            cfg = f"MACD 12/26/9 0-cross BARE tgt{tmult:.0f}x"
            p = dict(tmult=tmult)
            row = mk_row("B-macd", "before", cfg, tf, asset, tr, va, stop_pct=sp, target_pct=tp,
                         trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
            if row["verdict"] == "SURVIVOR" and asset == "BTC":
                BTC_AFTER_SURVIVORS.append(("B-macd", "before", tf, dict(p, W="none")))

            for W in (0, 5):
                el = confirm_within(cross_up, brk_long, W)
                es = confirm_within(cross_down, brk_short, W)
                tr, va, sp, tp = _run_macd_config(d, f, i_tr, i_va, el, es, med_atr, tmult, 72)
                cfg = f"MACD 12/26/9 0-cross + donchian20-break W{W} tgt{tmult:.0f}x"
                p = dict(tmult=tmult, W=W)
                row = mk_row("B-macd", "after", cfg, tf, asset, tr, va, stop_pct=sp, target_pct=tp,
                             trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                if row["verdict"] == "SURVIVOR" and asset == "BTC":
                    BTC_AFTER_SURVIVORS.append(("B-macd", "after", tf, p))


def replay_family_b(frames, funding, meta, variant, tf, params):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    med_atr = meta[tf]["med_atr"]
    cross_up, cross_down = macd_cross_events(d)
    tmult = params["tmult"]
    if variant == "before":
        el, es = cross_up, cross_down
    else:
        brk_long, brk_short = donchian_break_events(d, 20)
        el = confirm_within(cross_up, brk_long, params["W"])
        es = confirm_within(cross_down, brk_short, params["W"])
    tr, va, sp, tp = _run_macd_config(d, f, i_tr, i_va, el, es, med_atr, tmult, 72)
    cfg = f"[ETH replay] MACD {variant} tgt{tmult:.0f}x"
    return mk_row("B-macd", variant, cfg, tf, "ETH", tr, va, stop_pct=sp, target_pct=tp,
                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)


# ===========================================================================
# FAMILY C — volume-gated breakout (R76's two exact BTC 1h survivors)
# ===========================================================================

def bollinger_breakout_signal(d):
    price, lo, mid, up = bb_bands(d, 20, 2.5)
    sig = pd.Series(np.nan, index=d.index)
    sig[price > up] = 1.0
    sig[price < lo] = -1.0
    long_exit, short_exit = price < mid, price > mid
    sig[long_exit & (sig.ffill() == 1)] = 0.0
    sig[short_exit & (sig.ffill() == -1)] = 0.0
    return sig.ffill().fillna(0)


def squeeze_release_wrapped(d):
    return squeeze_release_signal(d, 20, 2, 20, 1.5)


BREAKOUT_CONFIGS = {
    "Bollinger breakout 20/2.5": bollinger_breakout_signal,
    "BB-in-KC squeeze release BB20/2 KC20/1.5": squeeze_release_wrapped,
}


def volume_gate_entry(sig, vol_ok):
    """Gate a persistent -1/0/1 state signal: at each fresh 0->nonzero
    transition, the entry is allowed only if vol_ok is True at that exact
    transition bar (the literal 'breakout bar's volume', not any bar during
    the ensuing excursion). If blocked, the WHOLE excursion is suppressed —
    stays flat until the base signal returns to 0 and re-attempts."""
    s = sig.fillna(0).to_numpy()
    v = vol_ok.fillna(False).to_numpy()
    n = len(s)
    out = np.zeros(n)
    blocked = False
    prev = 0.0
    for i in range(n):
        if s[i] != 0.0 and prev == 0.0:
            blocked = not v[i]
        if s[i] == 0.0:
            blocked = False
        out[i] = 0.0 if (s[i] != 0.0 and blocked) else s[i]
        prev = s[i]
    return pd.Series(out, index=sig.index)


def family_c(frames, funding, meta, asset):
    tf = "1h"
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    vol_avg20 = d["volume"].rolling(20).mean().shift(1)

    for cfg_name, sig_fn in BREAKOUT_CONFIGS.items():
        base_sig = sig_fn(d)
        tr, va = score(d, base_sig, f, i_tr, i_va, execution="maker")
        row = mk_row("C-breakout", "before", f"{cfg_name} BARE (R76 exact)", tf, asset, tr, va,
                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), config_name=cfg_name, vmult=None)
        if row["verdict"] == "SURVIVOR" and asset == "BTC":
            BTC_AFTER_SURVIVORS.append(("C-breakout", "before", tf, dict(config_name=cfg_name, vmult=None)))

        for vmult in (1.2, 1.5):
            vol_ok = d["volume"] >= vmult * vol_avg20
            gated_sig = volume_gate_entry(base_sig, vol_ok)
            tr, va = score(d, gated_sig, f, i_tr, i_va, execution="maker")
            cfg = f"{cfg_name} + volume>={vmult}x20avg"
            p = dict(config_name=cfg_name, vmult=vmult)
            row = mk_row("C-breakout", "after", cfg, tf, asset, tr, va,
                         trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
            if row["verdict"] == "SURVIVOR" and asset == "BTC":
                BTC_AFTER_SURVIVORS.append(("C-breakout", "after", tf, p))


def replay_family_c(frames, funding, meta, variant, tf, params):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    sig_fn = BREAKOUT_CONFIGS[params["config_name"]]
    base_sig = sig_fn(d)
    if variant == "before" or params["vmult"] is None:
        sig = base_sig
    else:
        vol_avg20 = d["volume"].rolling(20).mean().shift(1)
        vol_ok = d["volume"] >= params["vmult"] * vol_avg20
        sig = volume_gate_entry(base_sig, vol_ok)
    tr, va = score(d, sig, f, i_tr, i_va, execution="maker")
    cfg = f"[ETH replay] {params['config_name']} {variant} vmult={params['vmult']}"
    return mk_row("C-breakout", variant, cfg, tf, "ETH", tr, va,
                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)


# ===========================================================================
# FAMILY D — liquidity sweep -> MSS -> displacement
# ===========================================================================

def sweep_mss_displacement(d, k, tol, depth, disp_mult, max_wait_bars):
    pool_high, pool_low = liquidity_pools(d, k, tol)
    sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, depth)
    bos = bos_chain(d, k)
    lsh_np, lsl_np = bos["lsh"].to_numpy(), bos["lsl"].to_numpy()
    a = atr(d, 14)
    bar_range = d["high"] - d["low"]
    disp = (bar_range > disp_mult * a).fillna(False).to_numpy()
    close = d["close"].to_numpy()
    low_np, high_np = d["low"].to_numpy(), d["high"].to_numpy()
    pool_high_np, pool_low_np = pool_high.to_numpy(), pool_low.to_numpy()
    n = len(d)

    entry_long = np.zeros(n, dtype=bool)
    entry_short = np.zeros(n, dtype=bool)
    stop_ref_long = np.full(n, np.nan)
    stop_ref_short = np.full(n, np.nan)
    target_ref_long = np.full(n, np.nan)
    target_ref_short = np.full(n, np.nan)

    for j in np.where(sweep_long.to_numpy())[0]:
        opp = lsh_np[j]
        if np.isnan(opp):
            continue
        wick = low_np[j]
        end = min(n, j + 1 + max_wait_bars)
        for t in range(j + 1, end):
            if close[t] > opp and disp[t]:
                entry_long[t] = True
                stop_ref_long[t] = wick
                target_ref_long[t] = pool_high_np[t] if not np.isnan(pool_high_np[t]) else opp
                break

    for j in np.where(sweep_short.to_numpy())[0]:
        opp = lsl_np[j]
        if np.isnan(opp):
            continue
        wick = high_np[j]
        end = min(n, j + 1 + max_wait_bars)
        for t in range(j + 1, end):
            if close[t] < opp and disp[t]:
                entry_short[t] = True
                stop_ref_short[t] = wick
                target_ref_short[t] = pool_low_np[t] if not np.isnan(pool_low_np[t]) else opp
                break

    idx = d.index
    return (pd.Series(entry_long, idx), pd.Series(entry_short, idx),
            pd.Series(stop_ref_long, idx), pd.Series(stop_ref_short, idx),
            pd.Series(target_ref_long, idx), pd.Series(target_ref_short, idx))


def family_d(frames, funding, meta, asset):
    for tf in ("1h", "4h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]

        for k in (5, 8):
            # ---- D0: BEFORE — naive fade-the-raid, entry AT the sweep bar ----
            pool_high, pool_low = liquidity_pools(d, k, 0.1)
            sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, 0.3)
            mask = sweep_long | sweep_short
            dist_l = (d["close"] - d["low"]) / d["close"] * 100
            dist_s = (d["high"] - d["close"]) / d["close"] * 100
            dist = pd.Series(np.nan, index=d.index)
            dist = dist.mask(sweep_long, dist_l).mask(sweep_short, dist_s)
            stop_pct = train_median_stop_pct(d, i_tr, mask, dist, cap=STOP_CAP_SWEEP)
            if stop_pct is not None:
                for tmult in (2.0, 3.0):
                    target_pct = stop_pct * tmult
                    for hold_days in (3, 7):
                        mh_bars = hours_to_bars(d, hold_days * 24)
                        sig = day_trade_signal(d, sweep_long, sweep_short, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"k{k} SWEEP-ENTRY(naive) tgt{tmult:.0f}x hold{hold_days}d"
                        p = dict(k=k, tmult=tmult, hold_days=hold_days)
                        row = mk_row("D-sweep", "before", cfg, tf, asset, tr, va,
                                     stop_pct=stop_pct, target_pct=target_pct,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("D-sweep", "before", tf, p))

            # ---- D1: AFTER — sweep -> MSS -> displacement entry ----
            for disp_mult in (1.5, 2.0):
                for max_wait in (10, 20):
                    (el, es, sref_l, sref_s,
                     tref_l, tref_s) = sweep_mss_displacement(d, k, 0.1, 0.3, disp_mult, max_wait)
                    mask = el | es
                    stop_dist = pd.Series(np.nan, index=d.index)
                    stop_dist = stop_dist.mask(el, (d["close"] - sref_l).abs() / d["close"] * 100)
                    stop_dist = stop_dist.mask(es, (sref_s - d["close"]).abs() / d["close"] * 100)
                    stop_pct = train_median_stop_pct(d, i_tr, mask, stop_dist, cap=STOP_CAP_SWEEP)
                    if stop_pct is None:
                        continue
                    tgt_dist = pd.Series(np.nan, index=d.index)
                    tgt_dist = tgt_dist.mask(el, (tref_l - d["close"]).abs() / d["close"] * 100)
                    tgt_dist = tgt_dist.mask(es, (d["close"] - tref_s).abs() / d["close"] * 100)
                    pool_target_pct = train_median_stop_pct(d, i_tr, mask, tgt_dist,
                                                              cap=3 * STOP_CAP_SWEEP, floor=0.5)
                    tgt_options = [("2xstop", stop_pct * 2), ("3xstop", stop_pct * 3)]
                    if pool_target_pct:
                        tgt_options.append(("pool", pool_target_pct))
                    for tgt_tag, target_pct in tgt_options:
                        mh_bars = hours_to_bars(d, max_wait + hours_to_bars(d, 24 * 5))
                        sig = day_trade_signal(d, el, es, mh_bars)
                        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                        cfg = (f"k{k} SWEEP-MSS-DISPLACEMENT disp{disp_mult}x wait{max_wait} "
                               f"tgt={tgt_tag}")
                        p = dict(k=k, disp_mult=disp_mult, max_wait=max_wait, tgt_tag=tgt_tag)
                        row = mk_row("D-sweep", "after", cfg, tf, asset, tr, va,
                                     stop_pct=stop_pct, target_pct=target_pct,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("D-sweep", "after", tf, p))


def replay_family_d(frames, funding, meta, variant, tf, params):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    k = params["k"]
    if variant == "before":
        pool_high, pool_low = liquidity_pools(d, k, 0.1)
        sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, 0.3)
        mask = sweep_long | sweep_short
        dist_l = (d["close"] - d["low"]) / d["close"] * 100
        dist_s = (d["high"] - d["close"]) / d["close"] * 100
        dist = pd.Series(np.nan, index=d.index).mask(sweep_long, dist_l).mask(sweep_short, dist_s)
        stop_pct = train_median_stop_pct(d, i_tr, mask, dist, cap=STOP_CAP_SWEEP) or STOP_CAP_SWEEP
        target_pct = stop_pct * params["tmult"]
        mh_bars = hours_to_bars(d, params["hold_days"] * 24)
        sig = day_trade_signal(d, sweep_long, sweep_short, mh_bars)
    else:
        el, es, sref_l, sref_s, tref_l, tref_s = sweep_mss_displacement(
            d, k, 0.1, 0.3, params["disp_mult"], params["max_wait"])
        mask = el | es
        stop_dist = pd.Series(np.nan, index=d.index)
        stop_dist = stop_dist.mask(el, (d["close"] - sref_l).abs() / d["close"] * 100)
        stop_dist = stop_dist.mask(es, (sref_s - d["close"]).abs() / d["close"] * 100)
        stop_pct = train_median_stop_pct(d, i_tr, mask, stop_dist, cap=STOP_CAP_SWEEP) or STOP_CAP_SWEEP
        if params["tgt_tag"] == "pool":
            tgt_dist = pd.Series(np.nan, index=d.index)
            tgt_dist = tgt_dist.mask(el, (tref_l - d["close"]).abs() / d["close"] * 100)
            tgt_dist = tgt_dist.mask(es, (d["close"] - tref_s).abs() / d["close"] * 100)
            target_pct = train_median_stop_pct(d, i_tr, mask, tgt_dist, cap=3 * STOP_CAP_SWEEP,
                                                floor=0.5) or (stop_pct * 2)
        else:
            target_pct = stop_pct * (2.0 if params["tgt_tag"] == "2xstop" else 3.0)
        mh_bars = hours_to_bars(d, params["max_wait"] + hours_to_bars(d, 24 * 5))
        sig = day_trade_signal(d, el, es, mh_bars)
    tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    cfg = f"[ETH replay] sweep {variant}"
    return mk_row("D-sweep", variant, cfg, tf, "ETH", tr, va, stop_pct=stop_pct, target_pct=target_pct,
                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)


# ===========================================================================
# FAMILY E — opening-range breakout, stricter confirmation bar
# ===========================================================================

def strict_orb_gate(d):
    bar_range = d["high"] - d["low"]
    avg_prior5 = bar_range.rolling(5).mean().shift(1)
    body = (d["close"] - d["open"]).abs()
    body_frac = (body / bar_range.replace(0, np.nan)).fillna(0)
    return ((bar_range > avg_prior5) & (body_frac >= 0.70)).fillna(False)


def family_e(frames, funding, meta, asset):
    for tf in ("15m", "1h"):
        d, f = frames[tf], funding[tf]
        i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
        strict_gate = strict_orb_gate(d)
        for H in (4, 8):
            win_high, win_low, after_window = session_range(d, H)
            range_pct = (win_high - win_low) / win_low * 100
            med_range_pct = float(range_pct.iloc[:i_tr].dropna().median())
            stop_pct = min(med_range_pct, HARD_STOP_CAP)
            enter_long = after_window & (d["close"] > win_high)
            enter_short = after_window & (d["close"] < win_low)
            mh_bars = hours_to_bars(d, max(1, 24 - H))

            for variant, gate in (("before", None), ("after", strict_gate)):
                el = enter_long & gate if gate is not None else enter_long
                es = enter_short & gate if gate is not None else enter_short
                for direction, dl, ds in (("long", el, pd.Series(False, index=d.index)),
                                            ("short", pd.Series(False, index=d.index), es)):
                    sig = day_trade_signal(d, dl, ds, mh_bars)
                    for tmult in (1.5, 2.5):
                        target_pct = tmult * med_range_pct
                        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                        cfg = f"H{H}h {direction} {variant} tgt{tmult:.1f}xrange"
                        p = dict(H=H, direction=direction, tmult=tmult)
                        row = mk_row("E-orb", variant, cfg, tf, asset, tr, va,
                                     stop_pct=stop_pct, target_pct=target_pct,
                                     trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **p)
                        if row["verdict"] == "SURVIVOR" and asset == "BTC":
                            BTC_AFTER_SURVIVORS.append(("E-orb", variant, tf, p))


def replay_family_e(frames, funding, meta, variant, tf, params):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    H = params["H"]
    strict_gate = strict_orb_gate(d)
    win_high, win_low, after_window = session_range(d, H)
    range_pct = (win_high - win_low) / win_low * 100
    med_range_pct = float(range_pct.iloc[:i_tr].dropna().median())
    stop_pct = min(med_range_pct, HARD_STOP_CAP)
    enter_long = after_window & (d["close"] > win_high)
    enter_short = after_window & (d["close"] < win_low)
    gate = strict_gate if variant == "after" else None
    el = enter_long & gate if gate is not None else enter_long
    es = enter_short & gate if gate is not None else enter_short
    mh_bars = hours_to_bars(d, max(1, 24 - H))
    direction = params["direction"]
    dl = el if direction == "long" else pd.Series(False, index=d.index)
    ds = es if direction == "short" else pd.Series(False, index=d.index)
    sig = day_trade_signal(d, dl, ds, mh_bars)
    target_pct = params["tmult"] * med_range_pct
    tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
    cfg = f"[ETH replay] ORB H{H}h {direction} {variant}"
    return mk_row("E-orb", variant, cfg, tf, "ETH", tr, va, stop_pct=stop_pct, target_pct=target_pct,
                  trades_yr=trades_per_year(tr, va, d, i_tr, i_va), **params)


# ===========================================================================
# main
# ===========================================================================

REPLAY_FN = {
    "A-divergence": replay_family_a,
    "B-macd": replay_family_b,
    "C-breakout": replay_family_c,
    "D-sweep": replay_family_d,
    "E-orb": replay_family_e,
}


def load_frames(symbol):
    frames, funding = {}, {}
    fund_hist = fetch_funding_history(symbol)
    for tf in ("15m", "1h", "4h"):
        d = fetch_bybit_deep(tf, symbol)
        frames[tf] = d
        funding[tf] = align_funding(d, fund_hist)
    return frames, funding


def build_meta(frames):
    meta = {}
    for tf, d in frames.items():
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med_atr = float(atr_pct.iloc[:i_tr].median())
        meta[tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr}
    return meta


def main():
    print("Loading cached BTC + ETH data (no network calls expected)...")
    frames_btc, funding_btc = load_frames("BTCUSDT")
    frames_eth, funding_eth = load_frames("ETHUSDT")
    meta_btc = build_meta(frames_btc)
    meta_eth = build_meta(frames_eth)
    for tf in ("15m", "1h", "4h"):
        print(f"  BTC {tf}: {meta_btc[tf]['n']} bars | ETH {tf}: {meta_eth[tf]['n']} bars")

    print("\nRunning FAMILY A (regular divergence: before + 4 gated variants)...")
    family_a(frames_btc, funding_btc, meta_btc, "BTC")
    print(f"  {len(RESULTS)} rows cumulative, {len(BTC_AFTER_SURVIVORS)} BTC survivors queued")

    print("Running FAMILY B (MACD crossover: bare vs structurally confirmed)...")
    family_b(frames_btc, funding_btc, meta_btc, "BTC")
    print(f"  {len(RESULTS)} rows cumulative, {len(BTC_AFTER_SURVIVORS)} BTC survivors queued")

    print("Running FAMILY C (breakout: bare vs volume-gated)...")
    family_c(frames_btc, funding_btc, meta_btc, "BTC")
    print(f"  {len(RESULTS)} rows cumulative, {len(BTC_AFTER_SURVIVORS)} BTC survivors queued")

    print("Running FAMILY D (liquidity sweep: naive vs MSS+displacement)...")
    family_d(frames_btc, funding_btc, meta_btc, "BTC")
    print(f"  {len(RESULTS)} rows cumulative, {len(BTC_AFTER_SURVIVORS)} BTC survivors queued")

    print("Running FAMILY E (ORB: bare vs strict confirmation bar)...")
    family_e(frames_btc, funding_btc, meta_btc, "BTC")
    print(f"  {len(RESULTS)} rows cumulative, {len(BTC_AFTER_SURVIVORS)} BTC survivors queued")

    print(f"\nBTC sweep done: {len(RESULTS)} rows, {len(BTC_AFTER_SURVIVORS)} SURVIVOR configs "
          f"queued for the ETH transfer check (mandatory on anything that survives).")

    print("\nRunning ETH transfer check on every BTC SURVIVOR config...")
    n_replayed = 0
    for family, variant, tf, params in BTC_AFTER_SURVIVORS:
        REPLAY_FN[family](frames_eth, funding_eth, meta_eth, variant, tf, params)
        n_replayed += 1
    print(f"  {n_replayed} configs replayed on ETH.")

    df = pd.DataFrame(RESULTS)
    df.to_csv("step86_table.csv", index=False)
    print(f"\nwrote step86_table.csv: {len(df)} rows")

    btc = df[df["asset"] == "BTC"]
    print(f"\nBTC verdict counts:\n{btc['verdict'].value_counts().to_string()}")
    survivors = btc[btc["verdict"] == "SURVIVOR"]
    print(f"\nBTC SURVIVORS: {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "variant", "config", "tf", "tr_n", "tr_exp", "va_n", "va_exp",
                          "trades_yr"]].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    eth = df[df["asset"] == "ETH"]
    if len(eth):
        print(f"\nETH transfer check results (n={len(eth)}):")
        print(eth[["family", "variant", "config", "tf", "tr_exp", "va_exp", "verdict"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
        eth_survivors = eth[eth["verdict"] == "SURVIVOR"]
        print(f"\nETH TRANSFER SURVIVORS: {len(eth_survivors)} / {len(eth)}")

    return df


if __name__ == "__main__":
    main()
