"""
step67_scalp.py — round 67: SCALPING THE QUIET TAPE (research only).

Run:  python3 step67_scalp.py

OWNER'S SYNTHESIS
"Swing trading needs market action; right now BTC has none; look into
scalping." The thesis under test: RANGE SCALPING is the calm regime's
NATIVE family — the chop that starves trend tools (round after round of
this project) is exactly the texture range scalpers eat. It should fire
ONLY in calm regimes, the mirror image of every trend tool's vol gate,
completing the regime router (trend tools want ATR ABOVE norm, scalpers
should want it BELOW norm).

THIS FAMILY HAS DIED FIVE TIMES ON COSTS (rounds 4-8, 39, 41, 43, 45A):
every fast/candle-derived edge this repo has ever tested loses to the
round-trip cost hurdle once real fees+spread+slippage are charged. This
round treats the cost floor as the headline finding, not a footnote —
every config is scored under THREE cost lenses (see COST FLOOR MATH
below), and a config only earns "deployable" if it clears the harshest
one.

THE CALM GATE (mirrors the LIVE engine exactly — daily_pick.py lines
~505-524): instrument's 1h ATR14% vs its OWN trailing 336-bar (14-day)
median, ratio < 0.8 = calm. Computed on 1h candles, then merged onto the
15m signal frame with a forward-shifted join key so a 15m bar only ever
sees a CLOSED 1h bar's regime (no lookahead — see merge_htf_onto_ltf).
Every family runs BOTH calm-gated and ungated (control) to prove — or
disprove — the owner's regime thesis on its own evidence.

COST FLOOR MATH (config.py / backtest.py CostModel: 6bps taker fee,
2bps maker fee, 1bp half-spread, 2bps slippage — BloFin's real published
rates, unchanged project-wide):
  (a) TAKER-TAKER   (deployable today): fee-only RT = 6+6  = 12bps
                     all-in RT (fee+spread+slippage both legs) = 18bps
                     ENGINE-NATIVE: execution="taker" on both entry and
                     every signal-driven exit; the hard stop is ALWAYS a
                     taker fill in this engine (a stop is a market order
                     by construction) so this model is honest end to end.
  (b) MAKER-ENTRY + TAKER-EXIT (aspirational, "needs execution work"):
                     fee-only RT = 2+6 = 8bps; all-in RT = 2+9 = 11bps.
                     Not directly expressible in run_backtest (execution
                     is one flag for the whole backtest, and the engine's
                     own hard-stop is always taker). Computed ANALYTI-
                     CALLY from the taker-taker trade list: subtract the
                     entry leg's taker cost, add back the maker-fee-only
                     cost, ASSUMING the maker entry always fills at the
                     posted limit (upper bound — see fill-probability
                     proxy below for how often that assumption is shaky).
  (c) MAKER-MAKER   (aspirational ceiling): fee-only RT = 2+2 = 4bps;
                     all-in RT = 4bps (maker legs pay no spread/slippage
                     in this model). TWO versions reported:
                       - ENGINE-SIMULATED (execution="maker" end to end):
                         REALISTIC — posts a limit at the prior bar's
                         close, fills passively only if the next bar
                         actually trades through it, otherwise CHASES
                         with a full taker fill. This bakes in real
                         miss risk, not a fantasy.
                       - THEORETICAL best case (both legs assumed to
                         touch, no chase): computed analytically from
                         the taker-taker trades the same way as (b). The
                         GAP between theoretical and engine-simulated
                         maker-maker is itself the honest cost of "the
                         market didn't wait for you."
A config only counts DEPLOYABLE if it survives (a). Survivors of (b)/(c)
that fail (a) go on the "needs execution work" list, never the deploy
list.

THE ADVERSE-SELECTION CAVEAT (stated loudly, per the owner's brief): a
limit resting at a range edge fills MORE often exactly when the edge is
about to break — that is adverse selection, and it is NOT modeled by
"assume it always fills at the limit." As a crude proxy, for every
WINNING fade we measure how far price ran BEYOND the would-be limit
during the fill bar before bouncing (excess beyond the limit, in bps of
price). A high touch-and-run-through rate on winners is a tell that the
edge was being tested, not cleanly respected — real queue risk, not a
free lunch.

FAMILIES (S1-S4, all built to run BOTH calm-gated and ungated):
  S1 RANGE-EDGE FADE     — fade touches of a REAL 1h-defined range's
                            edges on 15m, stop beyond the edge, target
                            mid-range/opposite edge (structural exit).
  S2 MICRO MEAN-REVERSION — 15m z-score extremes fade to the mean.
  S3 VWAP MAGNET          — session-anchored VWAP band fades; R43 killed
                            this ungated, R63 rehabbed weekend VWAP
                            fades in violent markets — this round adds
                            the calm gate + a weekend-only cell.
  S4 COMPRESSION-EDGE SCALP — inside a compressed 1h range, trade 15m
                            closes back INSIDE after a wick beyond an
                            edge (the R64 sweep-and-reclaim finding: the
                            reclaim is the tradeable side, not the break).

ENGINE / DISCIPLINE NOTES (matches step41/step43 conventions):
- No lookahead: all higher-timeframe (1h) context is merged onto the 15m
  frame via merge_htf_onto_ltf, which shifts the join key to the 1h
  bar's CLOSE time — a 15m bar never sees an unclosed 1h bar. Rolling
  medians used as adaptive baselines are shift(1)'d (self-exclusion),
  matching step41's adaptive_vol_gate convention.
- GAUNTLET: chronological 60/20/20 per asset. This script NEVER slices
  into the final 20% (test) — only train (0:i_tr) and val (i_tr:i_va)
  are ever computed. Selection is by TRAIN expectancy only. Floors:
  >=30 train trades, >=8 val trades (SURVIVOR); below that but still
  train+val positive = INSUFFICIENT-SAMPLE (never a look-spend target).
- Costs always on (CostModel defaults, no cost-free mode exists in this
  engine by construction).
- Assets: BTC + ETH, both on cached Bybit 15m + 1h history (no network
  calls needed — BTC 5m is also cached back to 2020-03-30, ~6.3 years,
  far beyond the 18-24mo ask, but this round's families are built for
  15m per the task; a 5m variant is left for a future round if the 15m
  results earn it, see step67_results.md).
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

COSTS = CostModel()
TAKER_FEE = COSTS.fee_bps                # 6.0
MAKER_FEE = COSTS.maker_fee_bps          # 2.0
HALF_SPREAD = COSTS.half_spread_bps      # 1.0
SLIPPAGE = COSTS.slippage_bps            # 2.0
TAKER_LEG_ALLIN = TAKER_FEE + HALF_SPREAD + SLIPPAGE   # 9.0 bps
MAKER_LEG_ALLIN = MAKER_FEE                             # 2.0 bps (if touched)

ASSETS = ("BTCUSDT", "ETHUSDT")


# ---------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------

def bar_hours(d):
    t = pd.DatetimeIndex(d["timestamp"])
    return float((t[1:] - t[:-1]).total_seconds().min() / 3600)


def hours_to_bars(d, hours):
    return max(1, round(hours / bar_hours(d)))


def split_points(n):
    return int(n * 0.6), int(n * 0.8)


def merge_htf_onto_ltf(d_ltf, d_htf, cols, htf_bar_hours):
    """Attach higher-timeframe context columns onto the LTF frame with NO
    lookahead: an HTF bar's information only becomes real once that bar
    CLOSES (its open-timestamp + htf_bar_hours). We shift the join key
    forward by one HTF bar's duration before merge_asof(direction=
    'backward'), so an LTF bar only ever sees a CLOSED HTF bar's data."""
    right = d_htf[["timestamp"] + cols].copy()
    right["known_at"] = right["timestamp"] + pd.Timedelta(hours=htf_bar_hours)
    right = right.drop(columns=["timestamp"]).rename(columns={"known_at": "timestamp"})
    right = right.sort_values("timestamp")
    left = d_ltf[["timestamp"]].copy()
    merged = pd.merge_asof(left, right, on="timestamp", direction="backward")
    return merged[cols].reset_index(drop=True)


def calm_gate_1h(d1h):
    """Mirrors daily_pick.py's live calm-regime gate exactly: current 1h
    ATR14% vs its OWN trailing 336-bar (14-day) median, ratio < 0.8."""
    atr_pct = atr(d1h, 14) / d1h["close"] * 100
    med14 = atr_pct.rolling(336, min_periods=100).median()
    ratio = atr_pct / med14
    calm = (ratio < 0.8).fillna(False)
    return calm


def event_two_sided(d, enter_long, enter_short, exit_long, exit_short, max_hold=0):
    """Two-directional state machine (long OR short, never both at once),
    same discipline as strategy.event_short but bidirectional: whichever
    entry condition fires first while flat opens that side; exits on its
    own exit condition or the shared hard time stop."""
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    xl = exit_long.fillna(False).to_numpy(dtype=bool)
    xs = exit_short.fillna(False).to_numpy(dtype=bool)
    out = np.zeros(len(d))
    pos, held = 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if el[i]:
                pos, held = 1.0, 0
            elif es[i]:
                pos, held = -1.0, 0
        else:
            held += 1
            if pos > 0 and (xl[i] or (max_hold and held >= max_hold)):
                pos = 0.0
            elif pos < 0 and (xs[i] or (max_hold and held >= max_hold)):
                pos = 0.0
        out[i] = pos
    return pd.Series(out, index=d.index)


def score(d, sig, f, i_tr, i_va, stop_pct, execution):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def analytical_recost(taker_result, entry_maker=True, exit_maker=True):
    """Re-price every trade in a TAKER-TAKER result under an alternate
    execution assumption, WITHOUT re-running the engine. Only the legs
    flagged maker=True get re-priced (fee drops to MAKER_FEE, friction
    drops to 0); this is a best-case (assumes the maker order always
    touches/fills) — the honest gap vs the engine-simulated maker-maker
    run (which models the chase-on-miss penalty) is reported separately.
    Returns (trade_count, expectancy) — enough for the summary tables."""
    pnls = []
    for t in taker_result.trades:
        notional_entry = abs(t.units) * t.entry_price
        notional_exit = abs(t.units) * t.exit_price
        adj = 0.0
        if entry_maker:
            adj += notional_entry * (TAKER_LEG_ALLIN - MAKER_LEG_ALLIN) / 10_000
        if exit_maker:
            adj += notional_exit * (TAKER_LEG_ALLIN - MAKER_LEG_ALLIN) / 10_000
        pnls.append(t.pnl + adj)
    n = len(pnls)
    exp = float(np.mean(pnls)) if n else 0.0
    return n, exp


def touch_stats(d, idx_of, trades, direction, threshold_bps=2.0):
    """Crude fill-probability / adverse-selection proxy for WINNING trades
    of the given direction: at the entry fill bar, how far beyond the
    would-be maker limit (prior bar's close, exactly what execution=
    "maker" would have posted) did price run before the trade's outcome
    was decided? threshold_bps approximates "1-2 ticks" as a small bps
    buffer (true exchange tick size is far below 1bp on BTC/ETH; this is
    a cross-asset proxy, stated as an approximation, not exchange truth).
    Returns (n_winners_checked, frac_touched, frac_touched_beyond_thresh).
    """
    lows = d["low"].to_numpy()
    highs = d["high"].to_numpy()
    closes = d["close"].to_numpy()
    excess = []
    touched_flags = []
    for t in trades:
        if int(np.sign(t.direction)) != direction or not t.is_win:
            continue
        i = idx_of.get(t.entry_time)
        if i is None or i == 0:
            continue
        limit = closes[i - 1]
        if direction > 0:
            touched = lows[i] <= limit
            ex = (limit - lows[i]) / limit * 10_000
        else:
            touched = highs[i] >= limit
            ex = (highs[i] - limit) / limit * 10_000
        touched_flags.append(touched)
        excess.append(max(ex, 0.0))
    n = len(excess)
    if n == 0:
        return 0, None, None
    frac_touched = float(np.mean(touched_flags))
    frac_beyond = float(np.mean([e > threshold_bps for e in excess]))
    return n, frac_touched, frac_beyond


# ---------------------------------------------------------------------------
# asset context builder
# ---------------------------------------------------------------------------

def build_asset(symbol):
    print(f"Loading cached data for {symbol}...")
    d15 = fetch_bybit_deep("15m", symbol)
    d1h = fetch_bybit_deep("1h", symbol)
    funding_hist = fetch_funding_history(symbol)

    n = len(d15)
    i_tr, i_va = split_points(n)
    f15 = align_funding(d15, funding_hist)

    # --- 1h derived context, all shift(1)'d where they're adaptive baselines ---
    calm_1h = calm_gate_1h(d1h)
    atr1h_dollar = atr(d1h, 14)

    ctx_1h = pd.DataFrame({"timestamp": d1h["timestamp"], "calm": calm_1h,
                            "atr1h": atr1h_dollar})

    # S1 range bounds, two window widths
    for W in (24, 48):
        rh = d1h["high"].rolling(W).max()
        rl = d1h["low"].rolling(W).min()
        ctx_1h[f"rh{W}"] = rh
        ctx_1h[f"rl{W}"] = rl
        ctx_1h[f"rwidth{W}"] = rh - rl

    # S4 compression: 12x1h range + its own trailing (90d) median, shift(1)'d
    ch12 = d1h["high"].rolling(12).max()
    cl12 = d1h["low"].rolling(12).min()
    cwidth12 = ch12 - cl12
    window_bars = max(60, round(24 * 90))  # 90 trailing days of 1h bars
    med_cwidth12 = cwidth12.rolling(window_bars, min_periods=200).median().shift(1)
    ctx_1h["ch12"] = ch12
    ctx_1h["cl12"] = cl12
    ctx_1h["cwidth12"] = cwidth12
    ctx_1h["compressed12"] = (cwidth12 < 0.6 * med_cwidth12).fillna(False)

    merge_cols = [c for c in ctx_1h.columns if c != "timestamp"]
    merged = merge_htf_onto_ltf(d15, ctx_1h, merge_cols, htf_bar_hours=1.0)
    d = pd.concat([d15.reset_index(drop=True), merged], axis=1)
    d["calm"] = d["calm"].fillna(False)
    d["compressed12"] = d["compressed12"].fillna(False)

    # --- 15m native indicators ---
    atr15_pct = atr(d, 14) / d["close"] * 100
    d["atr15_pct"] = atr15_pct

    # session-anchored VWAP (00:00 UTC anchor) + expanding-within-session std
    ts = pd.DatetimeIndex(d["timestamp"])
    day = ts.floor("D")
    tp = (d["high"] + d["low"] + d["close"]) / 3
    pv = tp * d["volume"]
    grp_pv = pd.Series(pv.to_numpy(), index=day).groupby(level=0).cumsum()
    grp_vol = pd.Series(d["volume"].to_numpy(), index=day).groupby(level=0).cumsum()
    vwap = (grp_pv / grp_vol.replace(0, np.nan)).to_numpy()
    d["vwap"] = vwap
    dev = d["close"] - d["vwap"]
    dev_by_day = pd.Series(dev.to_numpy(), index=day)
    band_std = dev_by_day.groupby(level=0).transform(
        lambda s: s.expanding(min_periods=5).std())
    d["vwap_std"] = band_std.to_numpy()
    d["is_weekend"] = ts.weekday >= 5   # UTC Sat/Sun

    idx_of = {t: i for i, t in enumerate(pd.DatetimeIndex(d["timestamp"]))}

    train_med = {
        "atr15_pct": float(atr15_pct.iloc[:i_tr].median()),
    }
    for W in (24, 48):
        train_med[f"rwidthpct{W}"] = float(
            (d[f"rwidth{W}"].iloc[:i_tr] / d["close"].iloc[:i_tr] * 100).median())
    train_med["cwidth12pct"] = float(
        (d["cwidth12"].iloc[:i_tr] / d["close"].iloc[:i_tr] * 100).median())

    calm_bars = int(d["calm"].iloc[:i_va].sum())
    calm_days = calm_bars * (bar_hours(d) / 24.0)

    print(f"  {symbol} 15m: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
          f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
          f"calm bars in train+val: {calm_bars} ({calm_days:.0f} days, "
          f"{100*calm_bars/i_va:.1f}% of train+val)")

    return {
        "symbol": symbol, "d": d, "f": f15, "n": n, "i_tr": i_tr, "i_va": i_va,
        "train_med": train_med, "idx_of": idx_of, "calm_days": calm_days,
    }


# ---------------------------------------------------------------------------
# FAMILY builders — each returns a list of dicts:
#   {family, param_tag, enter_long, enter_short, exit_long, exit_short,
#    max_hold, stop_pct}
# gate (calm) is applied LATER by the caller, ANDed into entries.
# ---------------------------------------------------------------------------

def family_s1_range_edge_fade(ctx):
    d = ctx["d"]
    configs = []
    for W in (24, 48):
        rh, rl = d[f"rh{W}"], d[f"rl{W}"]
        width = d[f"rwidth{W}"]
        mid = (rh + rl) / 2
        for K in (1.5, 2.5):
            real_range = (width < K * d["atr1h"]).fillna(False)
            for S in (0.3, 0.5):
                stop_pct = S * ctx["train_med"][f"rwidthpct{W}"]
                for hold_h in (2, 4):
                    max_hold = hours_to_bars(d, hold_h)
                    touch_low = (d["low"] <= rl) & real_range
                    touch_high = (d["high"] >= rh) & real_range
                    enter_long = touch_low.fillna(False)
                    enter_short = touch_high.fillna(False)
                    exit_long = (d["close"] >= mid).fillna(False)
                    exit_short = (d["close"] <= mid).fillna(False)
                    tag = f"W{W} K{K:.1f} S{S:.1f} hold{hold_h}h"
                    configs.append({
                        "family": "S1-range-edge-fade", "param_tag": tag,
                        "enter_long": enter_long, "enter_short": enter_short,
                        "exit_long": exit_long, "exit_short": exit_short,
                        "max_hold": max_hold, "stop_pct": stop_pct,
                    })
    return configs


def family_s2_micro_meanrev(ctx):
    d = ctx["d"]
    configs = []
    stop_pct = 1.0 * ctx["train_med"]["atr15_pct"]
    max_hold = hours_to_bars(d, 2)
    for window in (48, 96):
        mean = d["close"].rolling(window).mean()
        std = d["close"].rolling(window).std()
        z = (d["close"] - mean) / std
        for Z in (2.0, 2.5):
            enter_long = (z <= -Z).fillna(False)
            enter_short = (z >= Z).fillna(False)
            exit_long = (z >= 0).fillna(False)
            exit_short = (z <= 0).fillna(False)
            tag = f"win{window} Z{Z:.1f}"
            configs.append({
                "family": "S2-micro-meanrev", "param_tag": tag,
                "enter_long": enter_long, "enter_short": enter_short,
                "exit_long": exit_long, "exit_short": exit_short,
                "max_hold": max_hold, "stop_pct": stop_pct,
            })
    return configs


def family_s3_vwap_magnet(ctx):
    d = ctx["d"]
    configs = []
    stop_pct = 1.0 * ctx["train_med"]["atr15_pct"]
    max_hold = hours_to_bars(d, 4)
    for band in (1.5, 2.0):
        upper = d["vwap"] + band * d["vwap_std"]
        lower = d["vwap"] - band * d["vwap_std"]
        for variant in ("allweek", "weekend"):
            mask = d["is_weekend"] if variant == "weekend" else pd.Series(True, index=d.index)
            enter_long = ((d["close"] <= lower) & mask).fillna(False)
            enter_short = ((d["close"] >= upper) & mask).fillna(False)
            exit_long = (d["close"] >= d["vwap"]).fillna(False)
            exit_short = (d["close"] <= d["vwap"]).fillna(False)
            tag = f"band{band:.1f} {variant}"
            configs.append({
                "family": "S3-vwap-magnet", "param_tag": tag,
                "enter_long": enter_long, "enter_short": enter_short,
                "exit_long": exit_long, "exit_short": exit_short,
                "max_hold": max_hold, "stop_pct": stop_pct,
            })
    return configs


def family_s4_compression_edge(ctx):
    d = ctx["d"]
    configs = []
    ch12, cl12 = d["ch12"], d["cl12"]
    compressed = d["compressed12"]
    for S in (0.3, 0.5):
        stop_pct = S * ctx["train_med"]["cwidth12pct"]
        for hold_h in (2, 4):
            max_hold = hours_to_bars(d, hold_h)
            swept_low_reclaimed = (d["low"] < cl12) & (d["close"] > cl12) & compressed
            swept_high_reclaimed = (d["high"] > ch12) & (d["close"] < ch12) & compressed
            enter_long = swept_low_reclaimed.fillna(False)
            enter_short = swept_high_reclaimed.fillna(False)
            exit_long = (d["close"] >= ch12).fillna(False)
            exit_short = (d["close"] <= cl12).fillna(False)
            tag = f"S{S:.1f} hold{hold_h}h"
            configs.append({
                "family": "S4-compression-edge", "param_tag": tag,
                "enter_long": enter_long, "enter_short": enter_short,
                "exit_long": exit_long, "exit_short": exit_short,
                "max_hold": max_hold, "stop_pct": stop_pct,
            })
    return configs


FAMILY_BUILDERS = [family_s1_range_edge_fade, family_s2_micro_meanrev,
                   family_s3_vwap_magnet, family_s4_compression_edge]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    rows = []
    touch_rows = []

    for symbol in ASSETS:
        ctx = build_asset(symbol)
        d, f, i_tr, i_va = ctx["d"], ctx["f"], ctx["i_tr"], ctx["i_va"]
        calm = d["calm"]

        base_configs = []
        for builder in FAMILY_BUILDERS:
            base_configs += builder(ctx)

        print(f"  {symbol}: {len(base_configs)} base configs x 2 gates x 2 "
              f"execution models = {len(base_configs) * 4} scored rows")

        for cfg in base_configs:
            for gate_label in ("calm-gated", "ungated"):
                if gate_label == "calm-gated":
                    el = cfg["enter_long"] & calm
                    es = cfg["enter_short"] & calm
                else:
                    el, es = cfg["enter_long"], cfg["enter_short"]
                sig = event_two_sided(d, el, es, cfg["exit_long"], cfg["exit_short"],
                                       cfg["max_hold"])

                for execution in ("taker", "maker"):
                    tr, va = score(d, sig, f, i_tr, i_va, cfg["stop_pct"], execution)
                    v = verdict_for(tr, va)

                    def avg_cost(res):
                        n = len(res.trades)
                        return ((res.total_fees + res.total_friction + res.total_funding) / n
                                if n else float("nan"))

                    tr_avgcost, va_avgcost = avg_cost(tr), avg_cost(va)
                    row = {
                        "asset": symbol, "family": cfg["family"],
                        "config": cfg["param_tag"], "gate": gate_label,
                        "execution": execution,
                        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
                        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
                        "tr_avgcost": tr_avgcost,
                        "tr_grossedge": tr.expectancy + tr_avgcost if len(tr.trades) else float("nan"),
                        "va_n": len(va.trades), "va_exp": va.expectancy,
                        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
                        "va_avgcost": va_avgcost,
                        "va_grossedge": va.expectancy + va_avgcost if len(va.trades) else float("nan"),
                        "verdict": v,
                        # analytical alternate-cost columns: only meaningful when
                        # this row IS the taker-taker run (see below); NaN on the
                        # engine-maker row to keep every row's schema identical
                        # (avoids the KeyError-on-missing-column crash from R1).
                        "tr_exp_makerENTRY_takerEXIT": float("nan"),
                        "va_exp_makerENTRY_takerEXIT": float("nan"),
                        "tr_exp_makerMAKER_theoretical": float("nan"),
                        "va_exp_makerMAKER_theoretical": float("nan"),
                        "trades_per_calm_day": float("nan"),
                    }
                    if execution == "taker":
                        _, exp_be = analytical_recost(tr, entry_maker=True, exit_maker=False)
                        _, exp_va_be = analytical_recost(va, entry_maker=True, exit_maker=False)
                        _, exp_bm = analytical_recost(tr, entry_maker=True, exit_maker=True)
                        _, exp_va_bm = analytical_recost(va, entry_maker=True, exit_maker=True)
                        row["tr_exp_makerENTRY_takerEXIT"] = exp_be
                        row["va_exp_makerENTRY_takerEXIT"] = exp_va_be
                        row["tr_exp_makerMAKER_theoretical"] = exp_bm
                        row["va_exp_makerMAKER_theoretical"] = exp_va_bm
                        if gate_label == "calm-gated":
                            calm_bars_va = int(calm.iloc[:i_va].sum())
                            calm_days = calm_bars_va * (bar_hours(d) / 24.0)
                            trades_per_day = ((len(tr.trades) + len(va.trades))
                                               / calm_days if calm_days > 0 else float("nan"))
                            row["trades_per_calm_day"] = trades_per_day
                        # fill-probability / adverse-selection proxy on winners,
                        # only for meaningfully-sampled configs (keeps output sane)
                        if len(tr.trades) + len(va.trades) >= 10:
                            all_trades = list(tr.trades) + list(va.trades)
                            for direction, dname in ((1, "long"), (-1, "short")):
                                n_w, frac_touch, frac_beyond = touch_stats(
                                    d, ctx["idx_of"], all_trades, direction)
                                if n_w:
                                    touch_rows.append({
                                        "asset": symbol, "family": cfg["family"],
                                        "config": cfg["param_tag"], "gate": gate_label,
                                        "direction": dname, "n_winners": n_w,
                                        "frac_touched": frac_touch,
                                        "frac_touched_beyond_2bps": frac_beyond,
                                    })
                    rows.append(row)

        # engine-simulated (chase-aware) maker-maker is already the
        # execution="maker" rows above; nothing further needed here.

    df = pd.DataFrame(rows)
    touch_df = pd.DataFrame(touch_rows)

    # write raw CSVs FIRST, before any print/formatting step that could crash
    # on an edge case (lesson from this round's first run) — the computed
    # data must survive even if a display step below has a bug.
    df.to_csv("step67_results_raw.csv", index=False)
    touch_df.to_csv("step67_touch_proxy_raw.csv", index=False)
    print("Raw results written to step67_results_raw.csv / step67_touch_proxy_raw.csv")

    print(f"\n{len(df)} scored rows across {df[['asset','family','config','gate']].drop_duplicates().shape[0]} "
          f"unique (asset,family,config,gate) combos x 2 execution models.")

    print("\n=== COST FLOOR: gross edge vs cost hurdle, by family (mean across all "
          "configs/assets/gates, TRAIN window) ===")
    cost_floor = (df.groupby(["family", "execution"])
                  .agg(mean_tr_grossedge=("tr_grossedge", "mean"),
                       mean_tr_avgcost=("tr_avgcost", "mean"),
                       mean_tr_exp=("tr_exp", "mean"),
                       n=("tr_exp", "size"))
                  .reset_index())
    with pd.option_context("display.width", 200):
        print(cost_floor.sort_values(["family", "execution"]).to_string(
            index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== TOP 10 CONFIGS BY TRAIN EXPECTANCY, TAKER-TAKER (regardless of "
          "verdict — shows how close the best got) ===")
    top_taker = df[df["execution"] == "taker"].sort_values("tr_exp", ascending=False).head(10)
    with pd.option_context("display.max_rows", None, "display.width", 220):
        print(top_taker[["asset", "family", "config", "gate", "tr_n", "tr_exp", "tr_grossedge",
                          "tr_avgcost", "va_n", "va_exp", "verdict"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== TOP 10 CONFIGS BY TRAIN EXPECTANCY, ENGINE MAKER-MAKER (regardless "
          "of verdict) ===")
    top_maker = df[df["execution"] == "maker"].sort_values("tr_exp", ascending=False).head(10)
    with pd.option_context("display.max_rows", None, "display.width", 220):
        print(top_maker[["asset", "family", "config", "gate", "tr_n", "tr_exp", "tr_grossedge",
                          "tr_avgcost", "va_n", "va_exp", "verdict"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== VERDICT COUNTS BY EXECUTION MODEL (TAKER-TAKER, deployable-today) ===")
    print(df[df["execution"] == "taker"]["verdict"].value_counts().to_string())
    print("\n=== VERDICT COUNTS BY EXECUTION MODEL (ENGINE MAKER-MAKER, chase-aware) ===")
    print(df[df["execution"] == "maker"]["verdict"].value_counts().to_string())

    print("\n=== TAKER-TAKER survivors + insufficient-sample (deployable tier) ===")
    taker_interesting = df[(df["execution"] == "taker") &
                            (df["verdict"].isin(["SURVIVOR", "INSUFFICIENT-SAMPLE"]))]
    with pd.option_context("display.max_rows", None, "display.width", 220):
        print(taker_interesting[["asset", "family", "config", "gate", "tr_n", "tr_exp",
                                  "va_n", "va_exp", "verdict",
                                  "tr_exp_makerENTRY_takerEXIT", "tr_exp_makerMAKER_theoretical",
                                  "trades_per_calm_day"]]
              .sort_values(["family", "asset", "tr_exp"], ascending=[True, True, False])
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== MAKER-MAKER (engine, chase-aware) survivors + insufficient-sample ===")
    maker_interesting = df[(df["execution"] == "maker") &
                            (df["verdict"].isin(["SURVIVOR", "INSUFFICIENT-SAMPLE"]))]
    with pd.option_context("display.max_rows", None, "display.width", 220):
        print(maker_interesting[["asset", "family", "config", "gate", "tr_n", "tr_exp",
                                  "va_n", "va_exp", "verdict"]]
              .sort_values(["family", "asset", "tr_exp"], ascending=[True, True, False])
              .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n=== GATE HEAD-TO-HEAD (mean train expectancy, taker-taker model) ===")
    h2h = (df[df["execution"] == "taker"]
           .groupby(["family", "gate"])
           .agg(mean_tr_exp=("tr_exp", "mean"), mean_va_exp=("va_exp", "mean"),
                pass_rate=("verdict", lambda s: (s == "SURVIVOR").mean()),
                n_configs=("verdict", "size"))
           .reset_index())
    with pd.option_context("display.width", 200):
        print(h2h.sort_values(["family", "gate"]).to_string(index=False,
              float_format=lambda x: f"{x:,.3f}"))

    print("\n=== FILL-PROBABILITY / ADVERSE-SELECTION PROXY (winners only, "
          "config-level, n_winners>=10 combined) ===")
    if len(touch_df):
        agg = (touch_df.groupby(["family", "config", "gate", "direction"])
               .agg(n_winners=("n_winners", "sum"),
                    frac_touched=("frac_touched", "mean"),
                    frac_touched_beyond_2bps=("frac_touched_beyond_2bps", "mean"))
               .reset_index())
        with pd.option_context("display.max_rows", None, "display.width", 200):
            print(agg.sort_values(["family", "config"]).to_string(index=False,
                  float_format=lambda x: f"{x:,.3f}"))
    else:
        print("(no configs met the n_winners>=10 threshold)")

    print("\n(step67_results.md written separately after this run)")

    return df, touch_df


if __name__ == "__main__":
    main()
