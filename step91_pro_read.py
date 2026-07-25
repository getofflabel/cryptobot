"""
step91_pro_read.py -- round 91: BACKTEST A WORKING PRO'S ACTUAL READ.

Run:  python3 step91_pro_read.py

Research only -- no commits, no live orders, no live-file edits. Writes
step91_pro_read.py (this file), step91_results.md, step91_table.csv.

THE SOURCE
The owner follows a market analyst ("Prof Michael" on The Real World). His
Friday end-of-day review was fact-checked claim-by-claim against real
market data -- every checkable descriptive claim was accurate (the SPY
squeeze-to-744-then-reversal, QQQ new lows into the close, BTC's 3 red
closes / close below 65K / retrace to Monday's low, oil and dollar reads).
Being right about what already happened is a DIFFERENT skill from having a
profitable forward rule. This round formalizes his stated reasoning
pattern into a mechanical, no-lookahead rule and tests whether it is
profitable after costs. If it is not, that is reported plainly -- this is
descriptive-accuracy-INSPIRED, not authority-based.

HIS STATED PATTERN, FORMALIZED
  1. Price moves INTO a prior resistance level (a confirmed swing high)
     and the tape gets bullish there -- treated as a WARNING, not
     confirmation.
  2. N consecutive red daily closes follow (he cited 3; we sweep 2/3/4).
  3. An "interim structure" level -- the most recent minor swing low made
     DURING the rally leg that reached resistance -- breaks. He stressed
     CLOSED BASIS, not a wick. We test both, isolated, to price the
     discipline in dollars.
  4. Forecast: a LOWER HIGH forms before the prior high (resistance) is
     exceeded again, rather than continuation through it.
  5. Explicit invalidation: a decisive CLOSE back above resistance kills
     the bearish read (the mirror of his own "unless BTC starts closing
     below 63.5" framing, stated on closed basis like he stated his own).

MECHANICAL DEFINITIONS (stated so every number is reproducible)
  - "Significant" resistance/support = swings(k_major=10): a bar is a
     confirmed swing high/low once the 21-bar centered window around it is
     fully known -- this repo's standard no-lookahead swing definition
     (step58_divergence_mtf.swings, imported unmodified).
  - "Interim / minor structure" = swings(k_minor=3): a confirmed swing low
     with a 7-bar centered window, formed strictly AFTER the current
     rally's origin (the most recent major swing low). This is the "minor
     swing low formed during the advance."
  - "Into resistance" = the rally's daily HIGH reaches within TOL_PCT=1.5%
     of a previously confirmed major swing high (below it or up to 1.5%
     through it -- a tag or a small poke, matching the SPY squeeze-to-744-
     then-reversal shape) for the FIRST time since the current rally's
     origin. Requires an interim (minor) swing low to already exist on
     this leg, or there is nothing to break -- no setup forms.
  - "N consecutive red closes" counted from the bar AFTER the resistance
     tag; once N is reached the setup stays ARMED (a later green day does
     not un-arm it -- the pattern already printed) until it either
     triggers, times out (SEARCH_WINDOW_BARS=25 trading days with no
     trigger), or invalidates.
  - "Interim structure breaks on a closed basis": CLOSE < interim low.
     WICK variant (isolated comparison): intrabar LOW < interim low,
     closed-basis not required. Everything else about the two variants is
     identical -- same resistance tag, same red-close gate, same stop/
     target -- so the dollar difference between them isolates exactly the
     discipline he emphasized.
  - Invalidation (both variants, closed basis, matching his own stated
     preference for closed-basis triggers): daily CLOSE above resistance x
     (1 + INVALID_PCT=3%) at any point before the setup triggers kills it
     and re-arms the search (band_reached resets, a fresh tag can restart
     the sequence within the same leg).
  - Forecast label ("lower high before new high"), measured independently
     of the traded stop/target: forward from the trigger, MISS the first
     time close > resistance; HIT the first time a confirmed k_minor swing
     high forms below resistance; INCONCLUSIVE if neither resolves within
     a 90-bar horizon.
  - Trade: SHORT, entered at the bar AFTER the trigger's open (engine's
     standard no-lookahead fill). Stop above resistance, target at the
     rally's origin swing low (the "next major level"). run_backtest takes
     ONE fixed stop_pct/target_pct per run (documented engine limitation,
     same approximation every prior round uses for per-trade dynamic
     stops): TRAIN-only median % distance from entry close to each level,
     plus a small buffer, capped -- swing_stop_pct, imported unmodified
     from step58_divergence_mtf. Held fixed across train+val.
  - MAX_HOLD_DAYS=45, a reasoned (not swept) choice: this is a daily-
     structure swing read, not an intraday scalp, and the "next major
     level" target needs room a 45-day cap should rarely bind while still
     forcing flat if the thesis stalls out.

DATA
  BTC: this repo's deep bitstamp daily spot cache (2011-present, 5,439
  bars / 14.9y) -- the same cache step74_structure.py used for daily-chart
  work, chosen over the ~6.3y bybit perp cache specifically because this
  is a RARE daily-chart pattern and the task calls for full cached
  history to have any chance of clearing the 30-train/8-val trade floors.
  Per step74's stated simplification (unchanged here): bitstamp is SPOT,
  no real funding history exists to align against it, so the engine's own
  conservative flat-funding default is used (BTC_COSTS below, identical
  to step72/73/74's convention) instead of inventing one.
  ETH (mandatory transfer on any BTC survivor): bybit ETHUSDT daily perp
  cache (2021-03-15 to present, 1,957 bars), WITH real funding via
  align_funding/fetch_funding_history (step11_round6, cache hit, no
  network call) -- ETH does have real funding history covering its whole
  cached range, so we use it, per this repo's real-funding-when-available
  standard.

DISCIPLINE
  Chronological 60/20/20 (split_points). Selection by TRAIN expectancy
  only; val read once. MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8, else
  INSUFFICIENT-SAMPLE. The sealed 20% test window is NEVER sliced by this
  script for ANY config. ETH transfer mandatory on any BTC SURVIVOR, stop/
  target recalibrated from ETH's own train median (nuisance nesting
  parameter, not a selection choice -- same convention step76/86 use).
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, day_trade_signal, hold_stats,
    split_points,
)
from step58_divergence_mtf import swing_stop_pct, swings

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

K_MAJOR = 10          # significant swing (resistance / rally-origin support)
K_MINOR = 3           # interim / minor structure swing
TOL_PCT = 1.5         # "tags or approaches" resistance, within this %
INVALID_PCT = 3.0     # decisive CLOSE this far above resistance invalidates
SEARCH_WINDOW = 25    # trading days to find N reds + trigger before giving up
FORECAST_HORIZON = 90 # bars to resolve the lower-high-before-new-high label
MAX_HOLD_DAYS = 45
STOP_BUFFER_PCT = 0.5
TARGET_BUFFER_PCT = 0.0
STOP_CAP_PCT = 8.0
TARGET_CAP_PCT = 30.0

BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)   # 12bps RT + funding
ETH_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)   # real funding overrides


# ---------------------------------------------------------------------------
# data loading -- cache hits only, no network calls
# ---------------------------------------------------------------------------

def load_btc_daily():
    d = pd.read_parquet("data_bitstamp_BTCUSD_1d_2011.parquet").reset_index(drop=True)
    return d, None   # no real funding for spot bitstamp -- engine conservative default


def load_eth_daily():
    d = pd.read_parquet("data_bybit_ETHUSDT_1d_full.parquet").reset_index(drop=True)
    funding = fetch_funding_history("ETHUSDT")
    f_bps = align_funding(d, funding)
    return d, f_bps


# ---------------------------------------------------------------------------
# the pattern -- one forward pass, no lookahead
# ---------------------------------------------------------------------------

def detect_pro_read_events(d, k_major=K_MAJOR, k_minor=K_MINOR, n_red=3,
                            tol_pct=TOL_PCT, invalid_pct=INVALID_PCT,
                            search_window=SEARCH_WINDOW, trigger_mode="close"):
    """One O(n) state-machine pass. trigger_mode: 'close' (closed-basis,
    his stated discipline) or 'wick' (intrabar low crosses the interim
    structure -- everything else identical, isolating the comparison).

    Returns a dict of length-n arrays:
      trigger    bool   -- True at the bar the short signal fires
      resist_R   float  -- resistance level (stop reference) at that trigger
      target_L0  float  -- rally-origin swing low (target reference)
      interim_S  float  -- the interim structure level that broke
      outcome    object -- 'HIT'/'MISS'/'INCONCLUSIVE' at trigger bars only,
                 the post-hoc "lower high before new high" forecast label
    """
    n = len(d)
    high = d["high"].to_numpy()
    low = d["low"].to_numpy()
    close = d["close"].to_numpy()

    conf_major_high, conf_major_low = swings(d["high"], d["low"], k_major)
    conf_minor_high, conf_minor_low = swings(d["high"], d["low"], k_minor)
    cMH, cML = conf_major_high.to_numpy(), conf_major_low.to_numpy()
    cmH, cmL = conf_minor_high.to_numpy(), conf_minor_low.to_numpy()

    trigger = np.zeros(n, dtype=bool)
    resist_out = np.full(n, np.nan)
    target_out = np.full(n, np.nan)
    interim_out = np.full(n, np.nan)
    outcome = np.full(n, None, dtype=object)

    majH_price = majH_idx = None
    majL_price = majL_idx = None
    minL_price = minL_idx = None

    state = "SEARCHING"
    band_reached = False
    resist_R = target_L0 = interim_S = tag_idx = None
    red_streak = 0
    armed = False

    for i in range(n):
        if cML[i]:
            majL_price, majL_idx = low[i - k_major], i - k_major
            minL_price, minL_idx = None, None
            band_reached = False
            if state == "AT_RESISTANCE":
                state = "SEARCHING"
        if cMH[i]:
            majH_price, majH_idx = high[i - k_major], i - k_major
        if cmL[i] and majL_idx is not None and (i - k_minor) > majL_idx:
            minL_price, minL_idx = low[i - k_minor], i - k_minor

        if state == "SEARCHING":
            if majH_price is not None and majL_price is not None and not band_reached:
                lo_band = majH_price * (1 - tol_pct / 100)
                hi_band = majH_price * (1 + tol_pct / 100)
                if high[i] > hi_band:
                    # decisive overshoot past tolerance with no valid tag having
                    # fired on this level yet -- lock this level out for this
                    # leg (majH will itself move on once a new swing high past
                    # here confirms, which naturally re-opens the search).
                    band_reached = True
                elif high[i] >= lo_band and minL_price is not None:
                    state = "AT_RESISTANCE"
                    resist_R, target_L0, interim_S = majH_price, majL_price, minL_price
                    tag_idx = i
                    red_streak = 0
                    armed = False
                # else: in-band but no interim structure yet -- keep watching,
                # do not lock (a pullback low may still confirm on a later bar
                # while price is still hovering near resistance)
        elif state == "AT_RESISTANCE":
            if close[i] > resist_R * (1 + invalid_pct / 100):
                state = "SEARCHING"
                band_reached = False
                continue
            if i - tag_idx > search_window:
                state = "SEARCHING"
                band_reached = False
                continue
            if i > tag_idx:
                if close[i] < close[i - 1]:
                    red_streak += 1
                else:
                    red_streak = 0
                if red_streak >= n_red:
                    armed = True
            if armed:
                broke = (close[i] < interim_S) if trigger_mode == "close" else (low[i] < interim_S)
                if broke:
                    trigger[i] = True
                    resist_out[i] = resist_R
                    target_out[i] = target_L0
                    interim_out[i] = interim_S
                    state = "SEARCHING"
                    band_reached = False

    # post-hoc forecast label: lower high before new high, forward scan
    trig_idx = np.where(trigger)[0]
    for i0 in trig_idx:
        R = resist_out[i0]
        label = "INCONCLUSIVE"
        for j in range(i0 + 1, min(n, i0 + 1 + FORECAST_HORIZON)):
            if close[j] > R:
                label = "MISS"
                break
            if cmH[j]:
                peak_idx = j - k_minor
                if peak_idx > i0 and high[peak_idx] < R:
                    label = "HIT"
                    break
        outcome[i0] = label

    return {
        "trigger": pd.Series(trigger, index=d.index),
        "resist_R": pd.Series(resist_out, index=d.index),
        "target_L0": pd.Series(target_out, index=d.index),
        "interim_S": pd.Series(interim_out, index=d.index),
        "outcome": outcome,
    }


# ---------------------------------------------------------------------------
# scoring plumbing
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, funding=None, stop_pct=None, target_pct=None):
    def run(lo, hi):
        f = funding.iloc[lo:hi].reset_index(drop=True) if funding is not None else None
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution="taker", funding_series=f,
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    """This round's task spec states the floor check explicitly: 'Minimum 30
    train / 8 val trades per cell, else INSUFFICIENT SAMPLE' -- sample size
    gates BEFORE sign. That is a deliberate deviation from step43's imported
    verdict_for (which returns FAIL on any non-positive expectancy even at
    n=1, conflating 'not enough data' with 'rejected'). At the trade counts
    this rare a pattern actually produces (single digits per cell), a
    negative-expectancy label on n=1-2 trades is not a defensible FAIL --
    it is INSUFFICIENT SAMPLE, and is reported as such here."""
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        return "INSUFFICIENT-SAMPLE"
    if tr.expectancy > 0 and va.expectancy > 0:
        return "SURVIVOR"
    return "FAIL"


def trades_per_year(d, tr, va, i_va):
    n_trades = len(tr.trades) + len(va.trades)
    span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return n_trades / span_days * 365.25 if span_days > 0 else float("nan")


def mk_row(asset, n_red, mode, tr, va, stop_pct, target_pct, d, i_va,
           n_events, forecast):
    med_h, mean_h = hold_stats(tr, va)
    return {
        "asset": asset, "N_red": n_red, "basis": mode,
        "n_events": n_events, "hit_rate%": forecast["hit_rate"],
        "resolved_n": forecast["resolved_n"], "inconclusive_n": forecast["inconclusive_n"],
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "med_hold_h": med_h, "trades/yr": trades_per_year(d, tr, va, i_va),
        "verdict": verdict_for(tr, va),
    }


def forecast_stats(events, i_va):
    """Hit rate over TRAIN+VAL trigger bars only (test sealed)."""
    outcomes = [o for o in events["outcome"][:i_va] if o is not None]
    hits = sum(o == "HIT" for o in outcomes)
    misses = sum(o == "MISS" for o in outcomes)
    inconclusive = sum(o == "INCONCLUSIVE" for o in outcomes)
    resolved = hits + misses
    hit_rate = 100.0 * hits / resolved if resolved else float("nan")
    return {"hit_rate": hit_rate, "resolved_n": resolved, "inconclusive_n": inconclusive,
            "n": len(outcomes), "hits": hits, "misses": misses}


def run_cell(d, funding, costs, asset, n_red, mode):
    n, i_tr, i_va = split_points(d)
    events = detect_pro_read_events(d, n_red=n_red, trigger_mode=mode)
    trig = events["trigger"]
    n_events = int(trig[:i_va].sum())
    forecast = forecast_stats(events, i_va)

    no_long = pd.Series(False, index=d.index)
    entries_mask = trig
    dist_stop = ((d["close"] - events["resist_R"]).abs() / d["close"] * 100)
    dist_tgt = ((d["close"] - events["target_L0"]).abs() / d["close"] * 100)
    stop_pct = swing_stop_pct(d["close"], events["resist_R"], entries_mask, i_tr,
                               STOP_BUFFER_PCT, STOP_CAP_PCT)
    target_pct = swing_stop_pct(d["close"], events["target_L0"], entries_mask, i_tr,
                                 TARGET_BUFFER_PCT, TARGET_CAP_PCT)

    mh_bars = MAX_HOLD_DAYS  # daily bars: 1 bar = 1 day
    sig = day_trade_signal(d, no_long, trig, mh_bars)
    tr, va = score(d, sig, costs, i_tr, i_va, funding=funding,
                   stop_pct=stop_pct, target_pct=target_pct)
    row = mk_row(asset, n_red, mode, tr, va, stop_pct, target_pct, d, i_va,
                 n_events, forecast)
    return row, tr, va


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("Loading data (cache only, no network calls)...")
    btc, btc_funding = load_btc_daily()
    eth, eth_funding = load_eth_daily()
    n, i_tr, i_va = split_points(btc)
    print(f"  BTC (bitstamp daily): {len(btc)} bars {btc['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{btc['timestamp'].iloc[-1]:%Y-%m-%d} | train ends {btc['timestamp'].iloc[i_tr]:%Y-%m-%d}, "
          f"val ends {btc['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed, never touched)")
    ne, ie_tr, ie_va = split_points(eth)
    print(f"  ETH (bybit daily, real funding): {len(eth)} bars "
          f"{eth['timestamp'].iloc[0]:%Y-%m-%d} -> {eth['timestamp'].iloc[-1]:%Y-%m-%d}")

    rows = []
    btc_runs = {}
    print("\n--- BTC: sweeping N red closes x {closed, wick} basis ---")
    for n_red in (2, 3, 4):
        for mode in ("close", "wick"):
            row, tr, va = run_cell(btc, btc_funding, BTC_COSTS, "BTC", n_red, mode)
            rows.append(row)
            btc_runs[(n_red, mode)] = (tr, va)
            print(f"  N={n_red} {mode:5s}: events={row['n_events']:3d} "
                  f"hit_rate={row['hit_rate%']:.1f}% (resolved {row['resolved_n']}) "
                  f"tr_n={row['tr_n']:3d} tr_exp=${row['tr_exp']:+.2f} "
                  f"va_n={row['va_n']:3d} va_exp=${row['va_exp']:+.2f} "
                  f"tr/yr={row['trades/yr']:.1f} -> {row['verdict']}")

    # closed-basis vs wick-basis $ comparison, same N, BTC pooled train+val
    print("\n--- closed-basis vs wick-basis, same N (BTC, pooled train+val $) ---")
    basis_compare = []
    for n_red in (2, 3, 4):
        tr_c, va_c = btc_runs[(n_red, "close")]
        tr_w, va_w = btc_runs[(n_red, "wick")]
        pnl_c = sum(t.pnl for t in tr_c.trades) + sum(t.pnl for t in va_c.trades)
        pnl_w = sum(t.pnl for t in tr_w.trades) + sum(t.pnl for t in va_w.trades)
        n_c = len(tr_c.trades) + len(va_c.trades)
        n_w = len(tr_w.trades) + len(va_w.trades)
        exp_c = pnl_c / n_c if n_c else float("nan")
        exp_w = pnl_w / n_w if n_w else float("nan")
        basis_compare.append({
            "N_red": n_red, "closed_total_$": pnl_c, "closed_n": n_c, "closed_exp": exp_c,
            "wick_total_$": pnl_w, "wick_n": n_w, "wick_exp": exp_w,
            "closed_minus_wick_$": pnl_c - pnl_w,
        })
        print(f"  N={n_red}: closed ${pnl_c:+,.2f} ({n_c}t, exp ${exp_c:+.2f})  vs  "
              f"wick ${pnl_w:+,.2f} ({n_w}t, exp ${exp_w:+.2f})  "
              f"diff (closed-wick) ${pnl_c - pnl_w:+,.2f}")

    df = pd.DataFrame(rows)
    survivors = df[df["verdict"] == "SURVIVOR"]
    print(f"\nBTC SURVIVORS (train+val positive, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors.to_string(index=False))

    # ---- ETH transfer, mandatory on every BTC survivor ----
    eth_rows = []
    for _, r in survivors.iterrows():
        n_red, mode = int(r["N_red"]), r["basis"]
        eth_row, _, _ = run_cell(eth, eth_funding, ETH_COSTS, "ETH", n_red, mode)
        eth_rows.append(eth_row)
        print(f"\n  ETH transfer N={n_red} {mode}: events={eth_row['n_events']} "
              f"tr_n={eth_row['tr_n']} tr_exp=${eth_row['tr_exp']:+.2f} "
              f"va_n={eth_row['va_n']} va_exp=${eth_row['va_exp']:+.2f} "
              f"-> {eth_row['verdict']}")

    eth_df = pd.DataFrame(eth_rows) if eth_rows else pd.DataFrame()
    full = pd.concat([df, eth_df], ignore_index=True) if len(eth_df) else df
    full.to_csv("step91_table.csv", index=False)
    print("\nFull table written to step91_table.csv")

    write_results_md(df, eth_df, basis_compare, btc, eth)
    return full


def write_results_md(df, eth_df, basis_compare, btc, eth):
    n, i_tr, i_va = split_points(btc)
    survivors = df[df["verdict"] == "SURVIVOR"]
    insufficient = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    fails = df[df["verdict"] == "FAIL"]

    lines = []
    lines.append("# ROUND 91 -- backtesting a working pro's actual read\n")
    lines.append(
        "Source: the owner's followed analyst (\"Prof Michael\", The Real World), "
        "Friday end-of-day review. Every checkable descriptive claim in that "
        "review verified against real market data (SPY squeeze-to-744-then-"
        "reversal, QQQ new lows into the close, BTC's 3 red closes / close "
        "below 65K / retrace to Monday's low, oil and dollar reads). This "
        "round formalizes his STATED reasoning pattern into a mechanical, "
        "no-lookahead rule and tests whether it is profitable after costs -- "
        "descriptive accuracy and predictive edge are different skills, and "
        "this tests the second one.\n"
    )
    lines.append("## Mechanical rule tested\n")
    lines.append(
        "1. Rally's daily high tags a confirmed prior swing high "
        f"(k={K_MAJOR}, ~21-day window) within {TOL_PCT}% -- \"into resistance.\"\n"
        "2. N consecutive red daily closes follow (swept N in [2,3,4]), counted "
        "from the day after the tag; once reached, the setup stays armed.\n"
        "3. The most recent MINOR swing low formed during that rally leg "
        f"(k={K_MINOR}, ~7-day window -- the \"interim structure\") breaks: "
        "CLOSED-basis (his stated discipline) tested head-to-head against a "
        "WICK-basis variant that is otherwise identical.\n"
        "4. Forecast: does a confirmed lower minor swing high form below "
        "resistance before price closes back above it (\"lower high before "
        "new high\")?\n"
        f"5. Invalidation: a daily CLOSE above resistance x (1+{INVALID_PCT}%) "
        "kills the setup -- the mechanical mirror of his own closed-basis "
        "invalidation framing (\"unless BTC starts closing below 63.5\").\n"
        "\nTrade: SHORT at the bar after the trigger's open. Stop above "
        "resistance, target at the rally's origin swing low (\"next major "
        "level\"). Both distances are the TRAIN-only median % from entry "
        f"close to that level (+{STOP_BUFFER_PCT}% stop buffer), fixed across "
        f"train+val, capped at {STOP_CAP_PCT}%/{TARGET_CAP_PCT}% -- the "
        "engine's documented one-stop-per-run limitation, same approximation "
        f"every prior round uses. MAX_HOLD={MAX_HOLD_DAYS} days.\n"
    )

    lines.append("## Data & split\n")
    lines.append(
        f"BTC: bitstamp daily spot, {len(btc)} bars, "
        f"{btc['timestamp'].iloc[0]:%Y-%m-%d} to {btc['timestamp'].iloc[-1]:%Y-%m-%d} "
        f"(14.9y -- chosen over the shorter bybit perp cache because this is a "
        f"rare daily pattern and it needs history to clear the trade floors). "
        f"Train ends {btc['timestamp'].iloc[i_tr]:%Y-%m-%d}, val ends "
        f"{btc['timestamp'].iloc[i_va]:%Y-%m-%d}. Test (final 20%) is SEALED, "
        "never sliced by this script. Spot has no real funding history; the "
        "engine's conservative flat-funding default is used (same simplification "
        "step74 stated for this same cache).\n\n"
        f"ETH (mandatory transfer): bybit ETHUSDT daily perp, {len(eth)} bars, "
        f"{eth['timestamp'].iloc[0]:%Y-%m-%d} to {eth['timestamp'].iloc[-1]:%Y-%m-%d}, "
        "with REAL funding via align_funding (cache hit).\n"
    )

    lines.append("## BTC results, all cells\n")
    lines.append(df.to_markdown(index=False, floatfmt="+.2f"))
    lines.append("")

    lines.append("\n## Closed-basis vs wick-basis -- the discipline priced in dollars\n")
    lines.append(
        "Same N, same resistance/interim/target levels, same costs -- the ONLY "
        "difference is whether the interim structure must break on a CLOSE "
        "(his stated rule) or merely get wicked through intrabar. Pooled "
        "train+val, BTC:\n"
    )
    bc_df = pd.DataFrame(basis_compare)
    lines.append(bc_df.to_markdown(index=False, floatfmt="+.2f"))
    lines.append("")

    lines.append("\n## Forecast: \"lower high before new high\" hit rate (train+val, BTC)\n")
    fc_lines = ["| N_red | basis | events | resolved | hit rate | inconclusive |",
                "|---|---|---|---|---|---|"]
    for _, r in df.iterrows():
        fc_lines.append(
            f"| {r['N_red']} | {r['basis']} | {r['n_events']} | {r['resolved_n']} | "
            f"{r['hit_rate%']:.1f}% | {r['inconclusive_n']} |"
        )
    lines.append("\n".join(fc_lines))
    lines.append("")

    lines.append(f"\n## Verdict counts\n")
    lines.append(f"SURVIVOR: {len(survivors)} | INSUFFICIENT-SAMPLE: {len(insufficient)} | "
                  f"FAIL: {len(fails)}\n")

    if len(survivors):
        lines.append("### BTC survivors\n")
        lines.append(survivors.to_markdown(index=False, floatfmt="+.2f"))
        lines.append("")
        if len(eth_df):
            lines.append("### ETH transfer (mandatory replay of every BTC survivor)\n")
            lines.append(eth_df.to_markdown(index=False, floatfmt="+.2f"))
            eth_pass = eth_df[eth_df["verdict"] == "SURVIVOR"]
            lines.append("")
            if len(eth_pass):
                lines.append(f"**{len(eth_pass)} of {len(eth_df)} BTC survivor(s) transferred to ETH.**\n")
            else:
                lines.append("**0 of the BTC survivor(s) transferred to ETH -- BTC-only edge, if any.**\n")
    else:
        lines.append(
            "No cell cleared both TRAIN-positive AND VAL-positive expectancy "
            "with the minimum trade floors. No ETH transfer to run -- there is "
            "nothing to transfer.\n"
        )

    lines.append("\n## Plain verdict\n")
    if len(survivors) == 0:
        lines.append(
            "**The mechanical version of this method does NOT show a profitable "
            "edge after costs on either asset, in the cells tested.** His "
            "descriptive read of Friday's tape was accurate; that is a different "
            "skill from this specific mechanical translation of his method "
            "having positive expectancy. See per-cell numbers above for exactly "
            "where it failed (train sign, val sign, or sample size) before "
            "concluding the method itself is broken versus this particular "
            "operationalization of it.\n"
        )
    else:
        best = survivors.sort_values("va_exp", ascending=False).iloc[0]
        lines.append(
            f"**Best BTC survivor: N={best['N_red']} red closes, {best['basis']}-basis "
            f"break -- train ${best['tr_exp']:+.2f}/trade ({best['tr_n']}t), "
            f"val ${best['va_exp']:+.2f}/trade ({best['va_n']}t), "
            f"{best['trades/yr']:.1f} trades/yr.** See the ETH transfer table for "
            "whether this generalizes beyond BTC before treating it as durable.\n"
        )

    with open("step91_results.md", "w") as f:
        f.write("\n".join(lines))
    print("\nResults written to step91_results.md")


if __name__ == "__main__":
    main()
