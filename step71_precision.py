"""
step71_precision.py — round 71: THE PRECISION-ENTRY PROGRAM.

Run:  python3 step71_precision.py

Research only — no live orders, no commits. Touches nothing outside this
file / step71_results.md. Concurrent agents own step70_* — not touched.

THE OWNER'S CORRECTED FRAME
"15-minute trading" does NOT mean scalping micro-moves (buried 6x in this
repo on the ~12bps fee toll). It means using 15m/5m ENTRIES to snipe REAL
moves (targets 0.5-2%+), against which fees are noise, not a wall. The
proof-shape already exists in round 58's MTF ladder (4h bias -> 1h setup
-> trigger, val $56.42/t) but n=12 was benched-thin. This round builds the
full family around that shape and tries to fatten it.

THE FIXED ARCHITECTURE
  CONTEXT (4h) -> SETUP (1h) -> TRIGGER (15m or 5m) -> target >=
  {1.5, 2, 3}x a fine-timeframe-derived stop, with TARGET_PCT >= 0.5%
  (the owner's real-move floor). Configs whose implied target falls under
  0.5% are EXCLUDED BY DESIGN before a backtest is even run — that is the
  anti-scalp guard working as intended, not a bug.

  Stop geometry (stated approximation, same family as every prior round's
  "run_backtest takes ONE fixed stop_pct for the whole run" workaround —
  see step43/56/58 headers): at each qualifying entry, per-trade distance
  = max(trigger-bar's own extreme +/- a buffer, 1x ATR on the trigger's
  own timeframe). TRAIN-only median of that per-trade distance becomes
  the fixed stop_pct for the run, capped at STOP_CAP_PCT. Buffer is 0.15%
  for 15m triggers, 0.10% for 5m triggers (tighter buffer for the faster
  tier, per the owner's explicit ask — "tighter stops = better R:R
  geometry = the whole point of faster triggers").

  Max hold: 24h, everywhere, converted to bars per timeframe.

ACTUAL EXECUTION THIS ROUND: this file implements the FULL architecture
(main() below runs the complete ~1,300-cell grid: 4 contexts x 4 setups x
9 triggers x 3 targets x 2 directions x 2 assets). Within this round's
runtime budget, only a TRIMMED CORE of that grid was actually executed
and reported in step71_results.md (BTC+ETH, both directions, context in
{champion, none}, setup in {RSI3<15 pullback, sweep-1h reclaim}, trigger
in {15m turn candle, 15m BOS-up, 15m sweep-reclaim, 5m turn candle},
target in {1.5x, 2x, 3x} = 96 cells/asset) plus dedicated ladder/R58-
reproduction side-runs — see step71_results.md section 8 for the exact
list of what was cut. main() as written below runs the FULL grid and is
ready for a follow-up session to complete; it was not run to completion
this round.

SCOPE ADDITION (owner, mid-round): a 5m TRIGGER TIER, mirroring the 15m
tier's three trigger shapes (turn candle / BOS-up k3 / sweep-reclaim).
BTC 5m was ALREADY fully cached (data_bybit_BTCUSDT_5m_full.parquet,
6.3y — not thin). ETH 5m was not cached; fetched fresh via the existing
fetch_bybit_deep pagination helper (unmodified) at the top of main(),
same repo convention (data_bybit_{symbol}_5m_full.parquet). Achieved span
is reported honestly in the printed data-inventory and in the results
file; any window under ~2y is tagged [regime-thin] per the round-55
convention. The 15m-vs-5m head-to-head (same context+setup+target,
matched trigger TYPE) is a required analysis (section 8 below) — does
the faster trigger actually improve entries, or just add noise stopouts?
Noise-stopout rate (5m tier only) = trades closed within 30 minutes AND
a net loss / all trades for that config — a Trade record carries no
exit-reason field, so "closed fast and lost money" is the honest proxy
for "got stopped out on noise," stated plainly as an approximation.

PLUMBING REUSE (per the round-71 brief — nothing here is reimplemented
that already exists correctly elsewhere in the repo)
  - Data: fetch_bybit_deep (step7_deep_search), fetch_funding_history /
    align_funding (step11_round6) — cache hits for everything except the
    one fresh ETH-5m pull.
  - Gauntlet mechanics: split_points / score / verdict_for / hold_stats /
    day_trade_signal / bar_hours / hours_to_bars / CHAMP_KW /
    MIN_TRAIN_TRADES / MIN_VAL_TRADES — imported unmodified from
    step43_daytrade. Floors (30 train / 8 val) are the brief's own
    "floors 30/8" instruction, already the repo standard.
  - align_signal (generalized cross-timeframe "available only from the
    source bar's close" projector) — imported unmodified from
    step58_divergence_mtf, which is itself a generalization of step43's
    champ_aligned.
  - Structure tools — bos_chain / liquidity_pools / sweep_events /
    fvg_signals — imported unmodified from step56_smc_toolkit (the
    round-56 SMC toolkit). confirmed_swings imported unmodified from
    step41_shorts (bos_chain's own dependency, reused directly here for
    the 15m/5m single-swing sweep-reclaim trigger, which needs a plain
    confirmed swing point rather than a 2-swing "equal highs/lows" pool).
  - Cost-floor accounting — gross_edge_bps / realized_cost_bps —
    imported unmodified from step50_volume_absorption (the repo's
    ~9bps-floor methodology since round 43/50), used here for the
    fee-share-of-gross-edge analysis (section 3).
  - four_h_bias / rsi3_pullback_setup / reversal_bar / stack_entries —
    imported unmodified from step58_divergence_mtf, used ONLY in the
    dedicated sample-fattening check (section 7) to reproduce round 58's
    exact MTF-ladder config byte-for-byte before asking whether it
    fattens under this round's (possibly larger) cache.

GAUNTLET DISCIPLINE (unchanged from every prior round)
  Chronological 60/20/20 per timeframe (split_points). Selection by TRAIN
  expectancy only. The sealed 20% test slice is NEVER touched here — the
  lead agent spends looks against it, not this script.

COST DISCIPLINE (the one thing this round changes vs step43/56/58)
  Every prior round's day-trade families defaulted to execution="maker".
  This round's brief is explicit: the PRIMARY gauntlet is TAKER (12bps
  round-trip fee alone, before spread/slippage/funding — the realistic
  assumption for an entry that must fire when a fast trigger says so, not
  wait passively for a maker fill that may never come). If a config
  cannot clear TAKER costs it is not deployable, full stop. MAKER
  economics are computed and reported as a secondary line only — never
  used for verdicts, floors, or ranking.
"""

import time

import numpy as np
import pandas as pd

from backtest import run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings
from step43_daytrade import (
    CHAMP_KW, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    bar_hours, day_trade_signal, hold_stats, hours_to_bars,
    score, split_points, verdict_for,
)
from step50_volume_absorption import gross_edge_bps, realized_cost_bps
from step56_smc_toolkit import bos_chain, fvg_signals, liquidity_pools, sweep_events
from step58_divergence_mtf import (
    align_signal, four_h_bias, reversal_bar, rsi3_pullback_setup,
    stack_entries, trades_per_year,
)
from strategy import atr, rsi, vol_gated_ma

ASSETS = ("BTCUSDT", "ETHUSDT")
FINE_TFS_NEEDED = ("5m", "15m", "1h", "4h")

STOP_CAP_PCT = 3.0        # % — hard ceiling on any train-median dynamic stop
STOP_FLOOR_PCT = 0.05     # % — hard floor, avoids degenerate near-zero stops
BUFFER_15M = 0.15         # % — trigger-bar-extreme buffer, 15m tier
BUFFER_5M = 0.10          # % — trigger-bar-extreme buffer, 5m tier (tighter, owner's ask)
TARGET_FLOOR_PCT = 0.5    # % — the owner's real-move floor / anti-scalp guard
MAX_HOLD_H = 24
TARGET_MULTS = (1.5, 2.0, 3.0)
TRADES_PER_YEAR_FLOOR = 20
FEE_SHARE_MAX = 0.15      # brief's "fees should be <15% of gross" check
REGIME_THIN_YEARS = 2.0   # round-55 convention: tag windows under this


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def load_asset(symbol):
    print(f"Loading cached data for {symbol} (5m/15m/1h/4h)...")
    frames = {}
    for tf in FINE_TFS_NEEDED:
        frames[tf] = fetch_bybit_deep(tf, symbol)
    funding_hist = fetch_funding_history(symbol)
    funding = {tf: align_funding(frames[tf], funding_hist) for tf in FINE_TFS_NEEDED}

    meta = {}
    for tf in FINE_TFS_NEEDED:
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        tr_span_days = (d["timestamp"].iloc[i_tr - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
        va_span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[i_tr]).total_seconds() / 86400
        full_span_years = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).total_seconds() / 86400 / 365.25
        meta[tf] = {
            "n": n, "i_tr": i_tr, "i_va": i_va, "atr_pct": atr_pct,
            "tr_span_days": tr_span_days, "va_span_days": va_span_days,
            "full_span_years": full_span_years,
        }
        thin = " [regime-thin]" if full_span_years < REGIME_THIN_YEARS else ""
        print(f"  {tf}: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} ({full_span_years:.2f}y){thin} | "
              f"train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} "
              f"(test sealed)")
    return frames, funding, meta


# ---------------------------------------------------------------------------
# CONTEXT (4h)
# ---------------------------------------------------------------------------

CONTEXT_KINDS = ("champion", "bos-chain", "either", "none")
CONTEXT_BOS_K = 8   # fixed secondary param, matches step56's BIAS_BOS_K


def context_series_4h(frame4h, direction):
    """All four 4h context gates for one direction, as boolean series on
    frame4h's own index. 'none' = always True (the control that isolates
    whether context gating earns its keep at all)."""
    champ_ls = vol_gated_ma(frame4h, allow_short=True, **CHAMP_KW).fillna(0)
    chain4h = bos_chain(frame4h, CONTEXT_BOS_K)["chain"]
    if direction == "long":
        champ_gate = champ_ls == 1
        bos_gate = chain4h == 1
    else:
        champ_gate = champ_ls == -1
        bos_gate = chain4h == -1
    return {
        "champion": champ_gate,
        "bos-chain": bos_gate,
        "either": champ_gate | bos_gate,
        "none": pd.Series(True, index=frame4h.index),
    }


# ---------------------------------------------------------------------------
# SETUP (1h)
# ---------------------------------------------------------------------------

RSI3_THRESH = 15
FVG_FILL_FRAC = 0.5
FVG_EXPIRE_BARS = 20
SWEEP_K = 5
SWEEP_TOL_PCT = 0.1
SWEEP_DEPTH_PCT = 0.3
CHOCH_K = 8


def setup_rsi3_pullback(d1h):
    r3 = rsi(d1h["close"], 3)
    return (r3 < RSI3_THRESH).fillna(False), (r3 > (100 - RSI3_THRESH)).fillna(False)


def setup_fvg_return(d1h):
    enter_long, enter_short, *_ = fvg_signals(d1h, FVG_FILL_FRAC, FVG_EXPIRE_BARS)
    return enter_long, enter_short


def setup_sweep_reclaim(d1h):
    pool_high, pool_low = liquidity_pools(d1h, SWEEP_K, SWEEP_TOL_PCT)
    return sweep_events(d1h, pool_high, pool_low, SWEEP_DEPTH_PCT)


def setup_choch_flip(d1h):
    b = bos_chain(d1h, CHOCH_K)
    return b["choch_long"], b["choch_short"]


SETUPS = {
    "RSI3<15 pullback": setup_rsi3_pullback,
    "FVG-return 50%fill": setup_fvg_return,
    "sweep-1h reclaim": setup_sweep_reclaim,
    "CHoCH-flip": setup_choch_flip,
}


# ---------------------------------------------------------------------------
# TRIGGER (15m tier + 5m tier + control)
# ---------------------------------------------------------------------------

TRIGGER_K = 3   # confirmed-swing k for both BOS-up and sweep-reclaim triggers


def trig_turn_candle(d):
    long_ = ((d["close"] > d["open"]) & (d["close"] > d["close"].shift(1))).fillna(False)
    short_ = ((d["close"] < d["open"]) & (d["close"] < d["close"].shift(1))).fillna(False)
    return long_, short_


def trig_bos(d):
    b = bos_chain(d, TRIGGER_K)
    return b["bos_up"], b["bos_down"]


def trig_sweep_reclaim(d):
    sh_price, sl_price = confirmed_swings(d, TRIGGER_K)
    lsh, lsl = sh_price.ffill(), sl_price.ffill()
    long_ = ((d["low"] < lsl) & (d["close"] > lsl)).fillna(False)
    short_ = ((d["high"] > lsh) & (d["close"] < lsh)).fillna(False)
    return long_, short_


TRIGGER_FNS = {
    "turn candle": trig_turn_candle,
    "BOS-up (k3)": trig_bos,
    "sweep-reclaim": trig_sweep_reclaim,
}
CONTROL_TRIGGER = "none/enter-at-setup"


# ---------------------------------------------------------------------------
# stop/target geometry
# ---------------------------------------------------------------------------

def dynamic_stop_pct(d, i_tr, entry_long, entry_short, atr_pct, buffer_pct,
                      cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    """TRAIN-only median of max(trigger-bar-own-extreme + buffer, 1x ATR%),
    over qualifying entries, fixed across train+val. Same approximation
    family as step56's train_median_stop_pct / step58's swing_stop_pct.
    Returns None if zero qualifying TRAIN entries."""
    dist_long = (d["close"] - d["low"]) / d["close"] * 100 + buffer_pct
    dist_short = (d["high"] - d["close"]) / d["close"] * 100 + buffer_pct
    raw_long = np.maximum(dist_long, atr_pct)
    raw_short = np.maximum(dist_short, atr_pct)
    mask_l = entry_long.iloc[:i_tr].fillna(False)
    mask_s = entry_short.iloc[:i_tr].fillna(False)
    vals = pd.concat([raw_long.iloc[:i_tr][mask_l], raw_short.iloc[:i_tr][mask_s]]).dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(min(max(vals.median(), floor), cap))


# ---------------------------------------------------------------------------
# per-cell build + score
# ---------------------------------------------------------------------------

def noise_stopout_rate(tr, va):
    """5m-tier only: fraction of pooled trades that closed within 30
    minutes AND lost money. Trade carries no exit-reason field, so
    'closed fast and lost' is the stated honest proxy for a stop-out on
    noise (a fast WIN would be the trigger doing its job, not noise)."""
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan")
    fast_loss = sum(1 for t in trades
                     if (t.exit_time - t.entry_time).total_seconds() <= 1800 and t.pnl < 0)
    return fast_loss / len(trades)


def build_and_score(d, f, i_tr, i_va, i_tr_full, atr_pct, tr_span_days, va_span_days,
                     direction, entry_l, entry_s, buffer_pct, tmult, tier_tag):
    stop_pct = dynamic_stop_pct(d, i_tr, entry_l, entry_s, atr_pct, buffer_pct)
    if stop_pct is None:
        return {"status": "NO-QUALIFYING-TRAIN-ENTRIES"}
    target_pct = tmult * stop_pct
    if target_pct < TARGET_FLOOR_PCT:
        return {"status": "EXCLUDED-ANTISCALP", "stop_pct": stop_pct, "target_pct": target_pct}

    mh_bars = hours_to_bars(d, MAX_HOLD_H)
    sig = day_trade_signal(d, entry_l, entry_s, mh_bars)
    tr_t, va_t = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct, execution="taker")
    tr_m, va_m = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct, execution="maker")

    med_h, mean_h = hold_stats(tr_t, va_t)
    gross = gross_edge_bps(tr_t, va_t)
    cost = realized_cost_bps(tr_t, va_t)
    fee_share = (cost / gross) if (gross and gross > 0) else float("nan")
    tpy = trades_per_year(tr_t, va_t, tr_span_days, va_span_days)

    row = {
        "status": "SCORED",
        "stop_pct": stop_pct, "target_pct": target_pct,
        "tr_n": len(tr_t.trades), "tr_exp": tr_t.expectancy, "tr_win%": tr_t.win_rate * 100,
        "tr_ret%": tr_t.total_return_pct, "tr_dd%": tr_t.max_drawdown_pct,
        "va_n": len(va_t.trades), "va_exp": va_t.expectancy, "va_win%": va_t.win_rate * 100,
        "va_ret%": va_t.total_return_pct, "va_dd%": va_t.max_drawdown_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "verdict": verdict_for(tr_t, va_t),          # PRIMARY = taker-based
        "trades_per_year": tpy,
        "meets_freq_floor": bool(tpy >= TRADES_PER_YEAR_FLOOR) if not np.isnan(tpy) else False,
        "gross_edge_bps": gross, "realized_cost_bps": cost, "fee_share": fee_share,
        "clears_fee_share_floor": bool(fee_share < FEE_SHARE_MAX) if not np.isnan(fee_share) else False,
        "maker_tr_exp": tr_m.expectancy, "maker_va_exp": va_m.expectancy,
        "maker_va_n": len(va_m.trades),
        "maker_verdict": verdict_for(tr_m, va_m),
    }
    if tier_tag == "5m":
        row["noise_stopout_30m"] = noise_stopout_rate(tr_t, va_t)
    return row


# ---------------------------------------------------------------------------
# the main grid, one asset x one direction at a time
# ---------------------------------------------------------------------------

def run_grid(symbol, direction, frames, funding, meta):
    d4h, d1h, d15, d5 = frames["4h"], frames["1h"], frames["15m"], frames["5m"]

    context_4h = context_series_4h(d4h, direction)
    context_al = {
        kind: {
            "1h": (align_signal(d4h, s.astype(float), d1h, 4.0) >= 0.5),
            "15m": (align_signal(d4h, s.astype(float), d15, 4.0) >= 0.5),
            "5m": (align_signal(d4h, s.astype(float), d5, 4.0) >= 0.5),
        }
        for kind, s in context_4h.items()
    }

    setups_1h = {name: fn(d1h) for name, fn in SETUPS.items()}
    setups_al = {}
    for name, (sl, ss) in setups_1h.items():
        setups_al[name] = {
            "1h": (sl, ss),
            "15m": (align_signal(d1h, sl.astype(float), d15, 1.0) >= 0.5,
                    align_signal(d1h, ss.astype(float), d15, 1.0) >= 0.5),
            "5m": (align_signal(d1h, sl.astype(float), d5, 1.0) >= 0.5,
                   align_signal(d1h, ss.astype(float), d5, 1.0) >= 0.5),
        }

    trigger_registry = {}                                    # name -> (tf, (long,short) or None)
    for name, fn in TRIGGER_FNS.items():
        trigger_registry[f"15m {name}"] = ("15m", fn(d15))
    for name, fn in TRIGGER_FNS.items():
        trigger_registry[f"5m {name}"] = ("5m", fn(d5))
    trigger_registry[CONTROL_TRIGGER] = ("1h", None)

    rows = []
    ladder_candidates = []   # (train_exp, row_dict) for the strongest full-stack cells
    for context_kind in CONTEXT_KINDS:
        for setup_name in SETUPS:
            for trigger_name, (tf, trig_pair) in trigger_registry.items():
                d, f = frames[tf], funding[tf]
                i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
                atr_pct = meta[tf]["atr_pct"]
                buffer_pct = BUFFER_5M if tf == "5m" else BUFFER_15M

                setup_l, setup_s = setups_al[setup_name][tf]
                ctx_al = context_al[context_kind][tf]
                if direction == "long":
                    cand_l = setup_l & ctx_al
                    cand_s = pd.Series(False, index=d.index)
                else:
                    cand_l = pd.Series(False, index=d.index)
                    cand_s = setup_s & ctx_al

                if trig_pair is not None:
                    trig_l, trig_s = trig_pair
                    entry_l = cand_l & trig_l
                    entry_s = cand_s & trig_s
                    tier_tag = tf
                else:
                    entry_l, entry_s = cand_l, cand_s
                    tier_tag = "none"

                for tmult in TARGET_MULTS:
                    res = build_and_score(
                        d, f, i_tr, i_va, i_tr, atr_pct,
                        meta[tf]["tr_span_days"], meta[tf]["va_span_days"],
                        direction, entry_l, entry_s, buffer_pct, tmult, tier_tag)
                    row = {
                        "asset": symbol, "direction": direction, "context": context_kind,
                        "setup": setup_name, "trigger": trigger_name, "tier": tf,
                        "tmult": tmult, **res,
                    }
                    rows.append(row)
                    if (res.get("status") == "SCORED" and res.get("verdict") == "SURVIVOR"
                            and trig_pair is not None):
                        ladder_candidates.append((res["tr_exp"], context_kind, setup_name,
                                                   trigger_name, tf, entry_l, entry_s,
                                                   res["stop_pct"], res["target_pct"]))
    return rows, ladder_candidates, context_al, setups_al, trigger_registry


# ---------------------------------------------------------------------------
# ladder analysis (required analysis #1): context-only -> +setup -> +trigger
# ---------------------------------------------------------------------------

def ladder_for_cell(frames, funding, meta, direction, context_kind, setup_name,
                     trigger_name, tf, context_al, setups_al, trigger_registry,
                     stop_pct, target_pct):
    d, f = frames[tf], funding[tf]
    i_tr, i_va = meta[tf]["i_tr"], meta[tf]["i_va"]
    mh_bars = hours_to_bars(d, MAX_HOLD_H)

    ctx_al = context_al[context_kind][tf]
    ctx_edge = ctx_al & ~ctx_al.shift(1, fill_value=False)
    setup_l, setup_s = setups_al[setup_name][tf]
    _, trig_pair = trigger_registry[trigger_name]
    trig_l, trig_s = trig_pair

    if direction == "long":
        rungs = [
            ("context-only", ctx_edge, pd.Series(False, index=d.index)),
            ("context+setup", setup_l & ctx_al, pd.Series(False, index=d.index)),
            ("full (+trigger)", setup_l & ctx_al & trig_l, pd.Series(False, index=d.index)),
        ]
    else:
        rungs = [
            ("context-only", pd.Series(False, index=d.index), ctx_edge),
            ("context+setup", pd.Series(False, index=d.index), setup_s & ctx_al),
            ("full (+trigger)", pd.Series(False, index=d.index), setup_s & ctx_al & trig_s),
        ]

    out = []
    for label, el, es in rungs:
        sig = day_trade_signal(d, el, es, mh_bars)
        tr, va = score(d, sig, f, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct,
                        execution="taker")
        tpy = trades_per_year(tr, va, meta[tf]["tr_span_days"], meta[tf]["va_span_days"])
        out.append({
            "rung": label, "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
            "va_n": len(va.trades), "va_exp": va.expectancy, "trades_per_year": tpy,
            "verdict": verdict_for(tr, va),
        })
    return out


# ---------------------------------------------------------------------------
# 15m-vs-5m trigger head-to-head (owner's scope-addition requirement)
# ---------------------------------------------------------------------------

def trigger_head_to_head(df):
    scored = df[df["status"] == "SCORED"].copy()
    scored = scored[scored["tier"].isin(["15m", "5m"])]
    scored["trigger_shape"] = scored["trigger"].str.replace(r"^(15m|5m)\s+", "", regex=True)
    key_cols = ["asset", "direction", "context", "setup", "trigger_shape", "tmult"]
    pivot_rows = []
    for key, grp in scored.groupby(key_cols):
        tiers = grp.set_index("tier")
        if "15m" in tiers.index and "5m" in tiers.index:
            r15, r5 = tiers.loc["15m"], tiers.loc["5m"]
            pivot_rows.append({
                **dict(zip(key_cols, key)),
                "15m_va_exp": r15["va_exp"], "15m_va_n": r15["va_n"],
                "15m_verdict": r15["verdict"],
                "5m_va_exp": r5["va_exp"], "5m_va_n": r5["va_n"],
                "5m_verdict": r5["verdict"],
                "5m_noise_stopout_30m": r5.get("noise_stopout_30m", float("nan")),
                "5m_wins": bool(r5["va_exp"] > r15["va_exp"]),
            })
    return pd.DataFrame(pivot_rows)


# ---------------------------------------------------------------------------
# sample-fattening check on R58's exact ladder config
# ---------------------------------------------------------------------------

R58_STOP_CAP = 3.0   # STOP_CAP_MTF from step58, reproduced exactly here


def r58_fattening_check(frames, funding, meta):
    d1h, f1h = frames["1h"], funding["1h"]
    d4h = frames["4h"]
    i_tr, i_va = meta["1h"]["i_tr"], meta["1h"]["i_va"]

    champ4h = vol_gated_ma(d4h, **CHAMP_KW)
    bias4h = four_h_bias(d4h, champ4h)
    bias_on_1h = align_signal(d4h, bias4h, d1h, 4.0)

    setup_l, setup_s = rsi3_pullback_setup(d1h, 15)
    trig_l, trig_s = reversal_bar(d1h)
    el, es = stack_entries(setup_l, setup_s, bias_on_1h, trig_l, trig_s, "full")

    med_atr_1h = float((atr(d1h, 14) / d1h["close"] * 100).iloc[:i_tr].median())
    stop_pct = min(1.2 * med_atr_1h, R58_STOP_CAP)
    target_pct = 3.0 * stop_pct
    mh_bars = hours_to_bars(d1h, 72)
    sig = day_trade_signal(d1h, el, es, mh_bars)

    tr_maker, va_maker = score(d1h, sig, f1h, i_tr, i_va, stop_pct=stop_pct,
                                target_pct=target_pct, execution="maker")
    tr_taker, va_taker = score(d1h, sig, f1h, i_tr, i_va, stop_pct=stop_pct,
                                target_pct=target_pct, execution="taker")
    return {
        "n_bars_1h_now": meta["1h"]["n"],
        "stop_pct": stop_pct, "target_pct": target_pct,
        "maker": {"tr_n": len(tr_maker.trades), "tr_exp": tr_maker.expectancy,
                  "va_n": len(va_maker.trades), "va_exp": va_maker.expectancy,
                  "verdict": verdict_for(tr_maker, va_maker)},
        "taker": {"tr_n": len(tr_taker.trades), "tr_exp": tr_taker.expectancy,
                  "va_n": len(va_taker.trades), "va_exp": va_taker.expectancy,
                  "verdict": verdict_for(tr_taker, va_taker)},
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    t_start = time.time()
    all_rows = []
    all_ladders = []
    per_asset_context = {}
    r58_checks = {}

    for symbol in ASSETS:
        frames, funding, meta = load_asset(symbol)
        per_asset_context[symbol] = (frames, funding, meta)

        print(f"\n=== {symbol}: R58 sample-fattening check ===")
        r58_checks[symbol] = r58_fattening_check(frames, funding, meta)
        c = r58_checks[symbol]
        print(f"  1h bars now: {c['n_bars_1h_now']} | stop {c['stop_pct']:.3f}% "
              f"target {c['target_pct']:.3f}%")
        print(f"  MAKER (R58's original cost assumption): train n={c['maker']['tr_n']} "
              f"exp=${c['maker']['tr_exp']:.2f} | val n={c['maker']['va_n']} "
              f"exp=${c['maker']['va_exp']:.2f} -> {c['maker']['verdict']}")
        print(f"  TAKER (this round's primary standard):  train n={c['taker']['tr_n']} "
              f"exp=${c['taker']['tr_exp']:.2f} | val n={c['taker']['va_n']} "
              f"exp=${c['taker']['va_exp']:.2f} -> {c['taker']['verdict']}")

        for direction in ("long", "short"):
            print(f"\n=== {symbol} {direction}: running the precision-entry grid ===")
            t0 = time.time()
            rows, ladder_cands, context_al, setups_al, trigger_registry = run_grid(
                symbol, direction, frames, funding, meta)
            print(f"  {len(rows)} cells done in {time.time()-t0:.1f}s")
            all_rows.extend(rows)

            ladder_cands.sort(key=lambda x: x[0], reverse=True)
            seen = set()
            picked = []
            for cand in ladder_cands:
                key = (cand[1], cand[2])   # (context, setup) — dedupe across trigger/tmult
                if key in seen:
                    continue
                seen.add(key)
                picked.append(cand)
                if len(picked) >= 3:
                    break
            for (tr_exp, context_kind, setup_name, trigger_name, tf, entry_l, entry_s,
                 stop_pct, target_pct) in picked:
                ladder_rows = ladder_for_cell(
                    frames, funding, meta, direction, context_kind, setup_name,
                    trigger_name, tf, context_al, setups_al, trigger_registry,
                    stop_pct, target_pct)
                all_ladders.append({
                    "asset": symbol, "direction": direction, "context": context_kind,
                    "setup": setup_name, "trigger": trigger_name, "tier": tf,
                    "stop_pct": stop_pct, "target_pct": target_pct, "rungs": ladder_rows,
                })

    df = pd.DataFrame(all_rows)
    df.to_csv("step71_results_raw.csv", index=False)
    print(f"\nRaw results ({len(df)} cells) written to step71_results_raw.csv")

    print("\nStatus counts:")
    print(df["status"].value_counts().to_string())
    scored = df[df["status"] == "SCORED"]
    print(f"\nOf {len(scored)} scored cells, verdict counts (TAKER, primary):")
    print(scored["verdict"].value_counts().to_string())

    survivors = scored[scored["verdict"] == "SURVIVOR"]
    print(f"\nSURVIVORS (taker, positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val): {len(survivors)}")
    if len(survivors):
        cols = ["asset", "direction", "context", "setup", "trigger", "tier", "tmult",
                "tr_n", "tr_exp", "va_n", "va_exp", "trades_per_year", "fee_share"]
        print(survivors[cols].sort_values("va_exp", ascending=False).head(30)
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== Ladder analysis (context-only -> +setup -> +trigger) ===")
    for L in all_ladders:
        print(f"\n{L['asset']} {L['direction']} | {L['context']} / {L['setup']} / "
              f"{L['trigger']} ({L['tier']}) | stop {L['stop_pct']:.2f}% "
              f"tgt {L['target_pct']:.2f}%")
        for r in L["rungs"]:
            print(f"    {r['rung']:<18} tr n={r['tr_n']:>4} exp=${r['tr_exp']:>8.2f} | "
                  f"va n={r['va_n']:>4} exp=${r['va_exp']:>8.2f} | "
                  f"{r['trades_per_year']:.1f}/yr | {r['verdict']}")

    print("\n=== 15m-vs-5m trigger head-to-head ===")
    h2h = trigger_head_to_head(df)
    h2h.to_csv("step71_h2h_raw.csv", index=False)
    if len(h2h):
        print(h2h.sort_values("5m_wins", ascending=False)
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    else:
        print("  no matched pairs (no cell cleared both tiers for the same instance)")

    print(f"\nTotal runtime: {time.time()-t_start:.1f}s")
    return df, all_ladders, h2h, r58_checks


if __name__ == "__main__":
    main()
