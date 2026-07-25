"""
step130_intraday_structure.py — ROUND 130. DELIVERABLE 1: intraday
structure — opening range, first-hour behavior, gap direction predicting
the REST OF THE DAY.

Explicitly distinct from R60's already-dead family 2a (gap-fill: chasing a
return to the prior close, 0/16 FAIL, confirmed dead both directions both
instruments). This script tests a DIFFERENT question: does the gap's
DIRECTION predict how the rest of the session behaves (continuation vs
reversal), never targeting "the fill" at all.

THREE PARTS
  A. Gap-direction audit (statistical, daily bars, full history, SPY+ES) —
     report-only, mirrors R60 family 2b's audit discipline (gross AND net
     of one round-trip cost, t-stat, chance baseline = the unconditioned
     mean).
  B. Gap-day tradeable strategies built from part A's train-window read:
     CONTINUATION (trade the gap's own direction) and REVERSAL (fade it)
     for the REST OF THE DAY (enter at today's open, flatten at today's
     own close — a same-day trade, not a fill target). Custom same-day
     simulator (SimTrade/SimResult from step130_common), engine-mismatch
     documented below, same discipline as R60 family 2a's
     simulate_gap_trades(). Stops: 'priorclose' (continuation's natural
     invalidation level — full gap reversion) or exits.py's
     stop_structure(k=5) (nearest confirmed swing, the literal chart-
     structure ask) or an ATR multiple (secondary comparison only).
  C. First-hour opening-range breakout, GAP-CONDITIONED (new axis vs R60
     family 2c's trend-conditioning) — SPY 1h + ES 1h, and a 15m ES smoke
     attempt explicitly labeled INSUFFICIENT-SAMPLE given ~72 days of
     history (well under the min-trade bar once split 60/20/20).

ENGINE-MISMATCH NOTE (part B): identical limitation to R60 family 2a —
backtest.py's run_backtest always lags fill by one full bar
(signal-at-close -> fill-at-next-open), so it cannot express "trade the
bar whose own OPEN defines today's gap." The same-day simulator here
prices entry at today's open (after the gap is already fully known — a
real trader watching the pre-market print can act on it before the bell)
and resolves the stop/close exit using that SAME bar's own H/L/close,
gap-through-honesty applied via exits.py's own _gap_or_level() (imported,
not reimplemented).

execution="taker" throughout. Costs: SPY 4bps RT, ES=F 2bps RT
(step130_common.COSTS). No sealed-test look spent below — every score is
train (0:i_tr) and val (i_tr:i_va) only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import step130_common as C
import exits as X

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)


# ===========================================================================
# PART A — gap-direction audit (report-only, daily, full history)
# ===========================================================================

def gap_audit(d: pd.DataFrame, i_va: int, costs, thresh_pct: float) -> list[dict]:
    """For each day t: gap = (open_t - close_{t-1})/close_{t-1}. Bucket
    gap_up / gap_down / flat by `thresh_pct`. Report the REST-OF-DAY
    (open_t -> close_t) return per bucket, train+val only (test sealed),
    gross AND net of ONE round-trip cost. Chance baseline = the
    unconditioned all-days mean (last row)."""
    opens = d["open"].to_numpy()[1:i_va]
    closes_prior = d["close"].to_numpy()[0:i_va - 1]
    closes = d["close"].to_numpy()[1:i_va]
    gap_pct = (opens - closes_prior) / closes_prior * 100
    intraday_pct = (closes - opens) / opens * 100
    cost_pct = costs.round_trip_bps() / 100

    rows = []
    for name, mask in (
        ("gap_up", gap_pct >= thresh_pct),
        ("gap_down", gap_pct <= -thresh_pct),
        ("flat", np.abs(gap_pct) < thresh_pct),
        ("unconditioned (baseline)", np.ones_like(gap_pct, dtype=bool)),
    ):
        sub = intraday_pct[mask]
        n = len(sub)
        mean_gross = float(np.mean(sub)) if n else np.nan
        rows.append({
            "thresh%": thresh_pct, "bucket": name, "n": n,
            "mean_gross_pct": mean_gross,
            "mean_net_pct": mean_gross - cost_pct if n else np.nan,
            "tstat": C.tstat_1samp(sub), "win_pct": float((sub > 0).mean() * 100) if n else np.nan,
        })
    return rows


# ===========================================================================
# PART B — gap-day tradeable strategies (custom same-day simulator)
# ===========================================================================

def simulate_gap_dayclose(d: pd.DataFrame, s_ctx, lo: int, hi: int, shape: str, side: str,
                          gap_thresh_pct: float, stop_style: str, costs) -> C.SimResult:
    """shape='continuation': side='long' fires on gap_up, side='short' on
    gap_down (trade the gap's own direction). shape='reversal': side='long'
    fires on gap_down (buy the panic), side='short' on gap_up (fade the
    euphoria) — NOT the dead gap-fill target; this rides to the day's own
    close or gets stopped, no target at all, matching R60 family 1's own
    'no fixed target' philosophy. stop_style: 'priorclose' (continuation
    only), 'structure_k5' (exits.py stop_structure(k=5,n_back=1), the
    nearest confirmed swing as of entry), 'atr1.0x'/'atr1.5x' (secondary
    comparison, SPX's OWN daily ATR, never a ported constant)."""
    opens, highs, lows, closes = (d["open"].to_numpy(), d["high"].to_numpy(),
                                   d["low"].to_numpy(), d["close"].to_numpy())
    times = pd.DatetimeIndex(d["timestamp"])
    adv = costs._adverse_frac
    direction = X.LONG if side == "long" else X.SHORT
    trades = []
    lo = max(lo, 1)
    for i in range(lo, hi):
        prior_close = closes[i - 1]
        gap_pct = (opens[i] - prior_close) / prior_close * 100
        if shape == "continuation":
            fires = (side == "long" and gap_pct >= gap_thresh_pct) or \
                    (side == "short" and gap_pct <= -gap_thresh_pct)
        else:
            fires = (side == "long" and gap_pct <= -gap_thresh_pct) or \
                    (side == "short" and gap_pct >= gap_thresh_pct)
        if not fires:
            continue

        entry_raw = opens[i]
        if stop_style == "priorclose":
            stop_level = prior_close
        elif stop_style == "structure_k5":
            tc = X.build_trade_ctx(s_ctx, i, entry_raw, direction)
            stop_level = X.stop_structure(k=5, n_back=1).level_fn(tc, i)
            if stop_level is None:
                continue
        elif stop_style.startswith("atr"):
            mult = float(stop_style[3:].rstrip("x"))
            a = s_ctx.atr_arr[i]
            if not np.isfinite(a) or a <= 0:
                continue
            stop_level = entry_raw - direction * mult * a
        else:
            raise ValueError(stop_style)

        entry = entry_raw * (1 + direction * adv)
        breached = (lows[i] <= stop_level) if direction > 0 else (highs[i] >= stop_level)
        if breached:
            fill = X._gap_or_level(opens[i], stop_level, direction, "stop")
            exit_price = fill * (1 - direction * adv)
            reason = "stop"
        else:
            exit_price = closes[i] * (1 - direction * adv)
            reason = "close"

        notional_in = C.INITIAL_EQUITY
        entry_fee = costs.fee(notional_in)
        ret_frac = direction * (exit_price - entry) / entry
        gross = notional_in * ret_frac
        exit_fee = costs.fee(abs(notional_in + gross))
        pnl = gross - entry_fee - exit_fee
        trades.append(C.SimTrade(times[i], times[i], pnl, reason))
    return C.SimResult(trades)


def run_gap_strategies(frames, meta) -> list[dict]:
    rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        costs = C.COSTS[tag]
        i_tr, i_va = m["i_tr"], m["i_va"]
        s_ctx = X.build_series_ctx(d, k=5, atr_n=14)
        for shape in ("continuation", "reversal"):
            stop_styles = ("priorclose", "structure_k5", "atr1.0x") if shape == "continuation" \
                else ("structure_k5", "atr1.0x", "atr1.5x")
            for side in ("long", "short"):
                for gap_th in (0.3, 0.5, 0.8):
                    for stop_style in stop_styles:
                        tr = simulate_gap_dayclose(d, s_ctx, 0, i_tr, shape, side, gap_th, stop_style, costs)
                        va = simulate_gap_dayclose(d, s_ctx, i_tr, i_va, shape, side, gap_th, stop_style, costs)
                        cfg = f"{shape} {side} thresh{gap_th}% stop={stop_style}"
                        rows.append(C.mk_sim_row("B-gapday", cfg, tag, "1d", tr, va,
                                                  extra={"shape": shape, "side": side,
                                                         "thresh": gap_th, "stop_style": stop_style}))
    return rows


# ===========================================================================
# PART C — first-hour opening-range breakout, gap-conditioned
# ===========================================================================

def firsthour_range(d1h: pd.DataFrame):
    """Same construction as R60 family 2c: SPY/ES 1h bars are RTH-only for
    SPY (first bar of the day = 9:30-10:30 ET exactly); for ES the 1h
    frame is near-continuous but the FIRST bar after the prior day's close
    still marks the session's opening print, used the same way. Returns
    per-bar day-mapped range high/low and a boolean 'after_window' mask."""
    ts_et = d1h["timestamp"].dt.tz_convert("America/New_York")
    day = ts_et.dt.date
    tmp = pd.DataFrame({"day": day, "time": ts_et, "high": d1h["high"], "low": d1h["low"],
                        "open": d1h["open"]})
    first_idx = tmp.groupby("day")["time"].idxmin()
    is_first = pd.Series(tmp.index.isin(first_idx.values), index=tmp.index)
    range_high_map = tmp.loc[is_first].set_index("day")["high"]
    range_low_map = tmp.loc[is_first].set_index("day")["low"]
    range_open_map = tmp.loc[is_first].set_index("day")["open"]
    win_high = tmp["day"].map(range_high_map)
    win_low = tmp["day"].map(range_low_map)
    win_open = tmp["day"].map(range_open_map)
    return tmp, win_high, win_low, win_open, ~is_first


def daily_gap_map(d1d: pd.DataFrame, tz_dates) -> pd.Series:
    """Prior-close gap %, keyed by ET calendar date, for mapping onto the
    1h frame's day column (known as of that day's own open — no lookahead,
    same causal status as R60 family 2c's daily-trend map)."""
    d1d_date = d1d["timestamp"].dt.tz_convert("America/New_York").dt.date
    gap_pct = (d1d["open"] - d1d["close"].shift(1)) / d1d["close"].shift(1) * 100
    gmap = pd.Series(gap_pct.to_numpy(), index=d1d_date.to_numpy())
    gmap = gmap[~gmap.index.duplicated(keep="last")]
    return tz_dates.map(gmap)


def run_firsthour_gapcond(frames, meta) -> list[dict]:
    rows = []
    tag = "SPY"
    d = frames[tag]["1h"].reset_index(drop=True)
    d1d = frames[tag]["1d"]
    m = meta[tag]["1h"]
    costs = C.COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]

    tmp, win_high, win_low, win_open, after_window = firsthour_range(d)
    gap_on_day = daily_gap_map(d1d, tmp["day"])
    range_height_pct = (win_high - win_low) / win_low * 100
    med_range_train = float(range_height_pct.iloc[:i_tr].dropna().median())
    mh_bars = C.hours_to_bars(d, 6)

    enter_long_raw = (after_window & (d["close"] > win_high)).fillna(False)
    enter_short_raw = (after_window & (d["close"] < win_low)).fillna(False)

    for gap_bucket, gap_mask in (
        ("gap_up(>=0.3%)", gap_on_day >= 0.3),
        ("gap_down(<=-0.3%)", gap_on_day <= -0.3),
        ("flat(<0.3%)", gap_on_day.abs() < 0.3),
    ):
        gap_mask = gap_mask.fillna(False)
        el = enter_long_raw & gap_mask
        es = enter_short_raw & gap_mask
        flat = pd.Series(False, index=d.index)
        for direction, elx, esx in (("long", el, flat), ("short", flat, es)):
            sig = C.day_trade_signal(d, elx, esx, mh_bars)
            for tmult in (1.5, 2.5):
                target_pct = tmult * med_range_train
                stop_pct = min(med_range_train, 3.0)
                tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                cfg = f"gapcond={gap_bucket} {direction} tgt{tmult}xrange stop=rangeheight"
                rows.append(C.mk_row("C-firsthour-gapcond", cfg, tag, "1h", tr, va, stop_pct, target_pct))
    return rows


def run_firsthour_fade(frames, meta) -> list[dict]:
    """FADE the opening range instead of breaking it (short back toward
    the range midpoint on a break above, long on a break below) — the
    house doctrine (step99b_exit_research.md: "fading a range that's
    secretly a higher-timeframe trend gets steamrolled") and R60's own
    "shorts lose to their long mirrors everywhere tested" both predict
    this dies. Tested honestly rather than skipped."""
    rows = []
    tag = "SPY"
    d = frames[tag]["1h"].reset_index(drop=True)
    m = meta[tag]["1h"]
    costs = C.COSTS[tag]
    i_tr, i_va = m["i_tr"], m["i_va"]

    tmp, win_high, win_low, win_open, after_window = firsthour_range(d)
    range_mid = (win_high + win_low) / 2
    range_height_pct = (win_high - win_low) / win_low * 100
    med_range_train = float(range_height_pct.iloc[:i_tr].dropna().median())
    mh_bars = C.hours_to_bars(d, 6)

    # fade-short: price breaks ABOVE the range -> short back to the midpoint
    fade_short_entry = (after_window & (d["close"] > win_high)).fillna(False)
    # fade-long: price breaks BELOW the range -> long back to the midpoint
    fade_long_entry = (after_window & (d["close"] < win_low)).fillna(False)
    flat = pd.Series(False, index=d.index)

    for direction, elx, esx in (("fade-long", fade_long_entry, flat), ("fade-short", flat, fade_short_entry)):
        sig = C.day_trade_signal(d, elx, esx, mh_bars)
        stop_pct = min(med_range_train, 3.0)
        # target = the range midpoint itself, expressed as a target_pct
        # against the SAME median-range yardstick 2c/C use (no fixed-target
        # equivalent exists in run_backtest's stop_pct/target_pct signature
        # for "target = a specific price level", so this uses 0.5x range
        # height as the stated approximation of "back to the midpoint").
        target_pct = 0.5 * med_range_train
        tr, va = C.score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
        cfg = f"{direction} tgt=0.5xrange(mid) stop=rangeheight"
        rows.append(C.mk_row("D-firsthour-fade", cfg, tag, "1h", tr, va, stop_pct, target_pct))
    return rows


# ===========================================================================
# PART E — 15m opening range, ES smoke (honesty check on sample depth)
# ===========================================================================

def run_15m_smoke(meta_note: list[str]) -> tuple[list[dict], str]:
    try:
        d = C.load_symbol("ES", "15m")
    except FileNotFoundError:
        return [], "data_spx72_ES_15m_smoke.parquet not found — skipped."
    span_days = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    n_tr = int(len(d) * 0.6)
    n_va = int(len(d) * 0.8)
    note = (f"ES 15m smoke: {len(d)} bars over {span_days:.0f} days "
            f"({d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}). "
            f"An opening-range/breakout signal fires AT MOST once per session; {span_days:.0f} "
            f"days of ES near-continuous trading is nowhere near enough sessions to clear "
            f"{C.MIN_TRAIN_TRADES} train / {C.MIN_VAL_TRADES} val trades once split 60/20/20 "
            f"(60% of {span_days:.0f} days ~ {span_days*0.6:.0f} candidate entries at best, before "
            f"any signal even fires on a subset of those days). Verdict: INSUFFICIENT SAMPLE, "
            f"stated honestly rather than forced. Revisit once more 15m history accumulates.")
    return [], note


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 130 — DELIVERABLE 1: INTRADAY STRUCTURE (opening range, gap, first hour)")
    print("=" * 78)

    frames = {tag: {} for tag in ("SPY", "ES")}
    meta = {tag: {} for tag in ("SPY", "ES")}
    for tag in ("SPY", "ES"):
        for tf in ("1d", "1h"):
            frames[tag][tf] = C.load_symbol(tag, tf)
            meta[tag][tf] = C.span_meta(frames[tag][tf])
            m = meta[tag][tf]
            print(f"  {tag} {tf}: {m['n']} bars, i_tr={m['i_tr']} i_va={m['i_va']} med_atr={m['med_atr']:.3f}%")

    print("\n" + "=" * 78)
    print("PART A — GAP-DIRECTION AUDIT (report-only, train+val, test sealed)")
    print("=" * 78)
    audit_rows = []
    for tag in ("SPY", "ES"):
        d = frames[tag]["1d"]
        m = meta[tag]["1d"]
        for th in (0.3, 0.5, 0.8):
            for r in gap_audit(d, m["i_va"], C.COSTS[tag], th):
                r["symbol"] = tag
                audit_rows.append(r)
    audit_df = pd.DataFrame(audit_rows)
    print(audit_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\n" + "=" * 78)
    print("PART B — GAP-DAY TRADEABLE STRATEGIES (continuation vs reversal, custom same-day sim)")
    print("=" * 78)
    b_rows = run_gap_strategies(frames, meta)
    b_df = pd.DataFrame(b_rows)
    print(f"{len(b_df)} configs. Verdicts:\n{b_df['verdict'].value_counts().to_string()}")
    cols = ["family", "config", "symbol", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]
    print(b_df.sort_values(["shape", "side", "symbol", "tr_exp"], ascending=[True, True, True, False])[cols]
          .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("PART C — FIRST-HOUR OPENING-RANGE BREAKOUT, GAP-CONDITIONED (SPY 1h)")
    print("=" * 78)
    c_rows = run_firsthour_gapcond(frames, meta)
    c_df = pd.DataFrame(c_rows)
    print(c_df[["config", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("PART D — FIRST-HOUR FADE (expect dead per house doctrine)")
    print("=" * 78)
    d_rows = run_firsthour_fade(frames, meta)
    d_df = pd.DataFrame(d_rows)
    print(d_df[["config", "tr_n", "tr_exp", "tr_win%", "va_n", "va_exp", "va_win%", "verdict"]]
          .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("PART E — 15m OPENING RANGE, ES SMOKE (sample-depth honesty check)")
    print("=" * 78)
    _, e_note = run_15m_smoke([])
    print(e_note)

    b_df.to_csv("step130_table_partB_gapday.csv", index=False)
    c_df.to_csv("step130_table_partC_firsthour_gapcond.csv", index=False)
    d_df.to_csv("step130_table_partD_firsthour_fade.csv", index=False)
    audit_df.to_csv("step130_table_partA_gap_audit.csv", index=False)

    print("\nDone. No sealed-test window touched.")
    return audit_df, b_df, c_df, d_df, e_note


if __name__ == "__main__":
    main()
