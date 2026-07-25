"""
step94_quiet_day.py -- ROUND 94: THE QUIET-DAY PLAYBOOK.

Run:  python3 step94_quiet_day.py

Research only -- no commits, no live orders, no live-file edits. Writes
step94_quiet_day.py (this file), step94_results.md, step94_table.csv.

WHY THIS ROUND EXISTS
Every strategy this project has sealed-passed so far either needs the
market to be LOUD (the volume-gated Bollinger breakout requires the
breakout bar's own volume to clear 1.2x its trailing 20-bar average -- by
construction it cannot fire on a quiet day) or needs a large move to fully
develop (the divergence-confirm family). The owner's point (2026-07-24):
some days have little news, and those are often the EASIEST days to trade
-- range-bound, mean-reverting, low-drama -- even though the total dollars
on offer are smaller. We own a loud-day playbook and nothing for the
quiet two-thirds of the calendar. This round builds and tests one.

The opportunity was pre-measured on BTC daily bars (2020-04 to 2026-07,
n=2,294) by trailing-20-day volume tercile: QUIET days (bottom third,
n=757) have median high-low range 2.25% (25th pct 1.61%, 75th pct 3.16%),
94% of quiet days range >1%. Measured round-trip cost on this project's
468 sealed trades is 0.044% of position. A typical quiet day's range is
therefore >50x the cost floor -- there is unambiguously room here; this
round asks whether any MECHANICAL rule can actually harvest a slice of it
after real costs, train/val discipline, and ETH transfer.

THREE CANDIDATE SETUPS, ALL MEAN-REVERSION (the mirror-image of the loud-
day breakout family, deliberately):
  S1 fade-prior-range   -- price touches/exceeds YESTERDAY's high or low on
                            a quiet day; fade back toward the developing
                            range, no volume condition.
  S2 bb-midline-reversion -- SAME Bollinger(20, 2.5std) extreme family C's
                            breakout uses, opposite trade: fade back to the
                            midline instead of riding the break. This is
                            literally the mirror of our one sealed-passed
                            breakout strategy, which is the whole point --
                            same geometry, opposite bet, opposite regime.
  S3 failed-breakout-fade -- price WICKS through a Bollinger edge but
                            CLOSES back inside, AND that bar's own volume is
                            BELOW its trailing 20-bar average (LOW volume is
                            the tell the poke wasn't real) -- the mirror
                            image of family C's gate, which requires HIGH
                            volume to let a breakout THROUGH; here LOW
                            volume is required to let a FADE through.

TWO INDEPENDENT "QUIET" DEFINITIONS, both bottom-tercile, both strictly
CAUSAL (decided before day t's first bar prints, using only fully-closed
PRIOR days -- see build_quiet_flags() docstring for the exact shift/lag
discipline):
  quiet_A -- trailing 20-day VOLUME, ranked against its own trailing
             180-day distribution.
  quiet_B -- trailing 20-day REALIZED VOLATILITY (stdev of daily log
             returns), ranked the same way.
Both flags are computed once per calendar day and broadcast unchanged to
every intraday (1h) bar of that day -- the flag never looks at today's own
price action, only at days that have already fully closed.

SIZING: no fixed stop/target constants anywhere. Every cell's stop_pct and
target_pct are STOP_FRAC / TARGET_FRAC of a single TRAIN-only number:
train_quiet_range_pct = the median day-range% (high-low as % of close)
across TRAIN-split days flagged quiet under that cell's own quiet
definition. This is the repo's standard "TRAIN-only median distance, held
fixed across train+val, hard-capped" approximation (step43/step86 ENGINE
NOTE), applied here to the regime's own measured range instead of ATR or a
session-window height. TARGET_FRAC in {0.3, 0.5, 0.8} directly answers the
brief's own framing ("capturing even a third of a quiet day's range is
~17x costs"); STOP_FRAC in {0.4, 0.6} is swept alongside it. Both are
capped to [0.05%, 3.0%] against degenerate configs.

GRID: 3 setups x 2 quiet-defs x 2 stop_frac x 3 target_frac = 36 BTC
cells, every one scored on TRAIN and VAL only (chronological 60/20/20,
split_points, imported -- the sealed final 20% is never touched by this
script), at REAL costs (maker_fee_bps=2.0, half_spread=slippage=0,
funding_bps_8h=1.0 -- matches the 0.044% round-trip figure cited above:
2 x 2bps maker fee + a sliver of funding) AND at near-zero GROSS costs
(fee_bps=maker_fee_bps=0.01, funding=0), run on the IDENTICAL signal/stop/
target so fills are bit-for-bit identical between the two runs and the
dollar difference cleanly isolates what costs took out (same technique as
step93's gross_net_fields). Selection is by TRAIN expectancy only; val is
read once. MIN_TRAIN_TRADES=30 / MIN_VAL_TRADES=8, else INSUFFICIENT-
SAMPLE (verdict_for, same floors as every prior round).

COMPLEMENTARITY: for every cell, the fraction of its train+val trades whose
entry falls on a calendar day where R87's exact sealed config (Bollinger
breakout 20/2.5 + volume>=1.2x, 1h) did NOT also fire an entry. Computed by
literally re-deriving that config's own entry days on the same frame (via
imported bollinger_breakout_signal / volume_gate_entry / BREAKOUT_CONFIGS
from step86_specified -- not re-running its PnL, just its entry calendar).

EMPIRICAL CHANCE BASELINE: one representative cell per setup (quiet_A,
stop_frac=0.4, target_frac=0.5) has its exact train+val trade count,
stop_pct, and target_pct replayed on RANDOMLY chosen quiet-day bars (same
quiet mask, same cost model, same max-hold, same engine), 30 draws, to
measure the empirical SURVIVOR rate under pure-luck timing -- then scaled
by the number of cells sharing that setup (12) to get an expected-by-
chance count, same method step93 used for its own per-timeframe control.

ETH TRANSFER: mandatory on every BTC SURVIVOR. Same setup, same quiet
definition, same STOP_FRAC/TARGET_FRAC -- only the underlying
train_quiet_range_pct is recalibrated from ETH's OWN train-quiet days (the
nuisance sizing parameter, not a selection choice, per this project's
standing ETH-transfer discipline).

DATA: BTC & ETH 1h bybit USDT-perp caches (fetch_bybit_deep, cache hits,
no network calls) with real funding (align_funding/fetch_funding_history).
Daily bars used only for the quiet-flag classification and the
train_quiet_range_pct sizing input are built by resampling this SAME
cached 1h data (open=first, high=max, low=min, close=last, volume=sum) --
no separate daily dataset is loaded, so the "2.25% median quiet-day range"
figure cited above (measured on a different Bitstamp daily source) is
independently reproduced here as a sanity check, not assumed.
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, day_trade_signal, hours_to_bars,
    split_points,
)
from step76_indicators import bb_bands
from step86_specified import BREAKOUT_CONFIGS, volume_gate_entry

pd.set_option("display.width", 160)
pd.set_option("display.max_columns", None)

RANDOM_TRIALS = 30
RANDOM_SEED = 94

# REAL costs: maker fee round trip (2 x 2bps = 4bps) + real funding -- this
# matches the 0.044% (4.4bps) round-trip figure measured on the 468 sealed
# trades cited in the brief. GROSS: near-zero, isolates the pre-cost edge
# on the IDENTICAL signal/stop/target (half_spread=slippage=0 in BOTH
# models so fills never differ between the two runs -- step93's technique).
REAL_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                        slippage_bps=0.0, funding_bps_8h=1.0)
GROSS_COSTS = CostModel(fee_bps=0.01, maker_fee_bps=0.01, half_spread_bps=0.0,
                         slippage_bps=0.0, funding_bps_8h=0.0)

VOL_WINDOW = 20        # trailing days for volume / realized-vol averaging
PCT_WINDOW = 180       # trailing days for the percentile-rank calc
QUIET_PCTILE = 1 / 3   # bottom third = "quiet", matching the brief's tercile
LOW_VOL_MULT = 0.8     # S3's failed-breakout tell: bar volume < 0.8x its 20-bar avg
STOP_FRACS = (0.4, 0.6)
TARGET_FRACS = (0.3, 0.5, 0.8)
MAX_HOLD_H = 48
RANGE_CAP, RANGE_FLOOR = 3.0, 0.05     # % -- hard caps on stop_pct/target_pct
QUIET_DEFS = ("quiet_A", "quiet_B")

RESULTS = []


# ---------------------------------------------------------------------------
# data + regime classification
# ---------------------------------------------------------------------------

def load_asset(symbol):
    d = fetch_bybit_deep("1h", symbol)
    fh = fetch_funding_history(symbol)
    f = align_funding(d, fh)
    return d.reset_index(drop=True), f.reset_index(drop=True)


def daily_ohlcv(d):
    date = d["timestamp"].dt.floor("D")
    g = d.groupby(date)
    daily = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last(),
        "volume": g["volume"].sum(),
    })
    daily["range_pct"] = (daily["high"] - daily["low"]) / daily["close"] * 100
    return daily


def rolling_percentile_rank(s, window):
    """Percentile rank (0-1) of each value within its OWN trailing `window`
    (inclusive of itself). Every input value in that window is already
    knowable at the decision point by construction (see build_quiet_flags),
    so this adds no additional lookahead of its own."""
    vals = s.to_numpy(dtype=float)
    n = len(vals)
    out = np.full(n, np.nan)
    for i in range(window - 1, n):
        w = vals[i - window + 1:i + 1]
        if np.isnan(w).any():
            continue
        out[i] = float((w <= w[-1]).mean())
    return pd.Series(out, index=s.index)


def build_quiet_flags(daily):
    """Two independent, causal 'quiet' definitions, both bottom-tercile.
    Day t's flags use ONLY data through day t-1's close:
      quiet_A: causal_vol20 = 20-day avg volume ending YESTERDAY
               (.shift(1) drops today's still-forming volume), percentile-
               ranked against its own trailing 180-day distribution.
      quiet_B: causal_relvol = 20-day stdev of daily log returns, itself
               only using returns through yesterday's close (shift(1)
               again), ranked the same way.
    Nothing here ever reads day t's own high/low/close/volume to decide
    day t's flag."""
    causal_vol20 = daily["volume"].rolling(VOL_WINDOW).mean().shift(1)
    pct_vol = rolling_percentile_rank(causal_vol20, PCT_WINDOW)
    quiet_a = (pct_vol <= QUIET_PCTILE).fillna(False)

    log_ret = np.log(daily["close"] / daily["close"].shift(1))
    vol20ret = log_ret.rolling(VOL_WINDOW).std()
    causal_relvol = vol20ret.shift(1)
    pct_relvol = rolling_percentile_rank(causal_relvol, PCT_WINDOW)
    quiet_b = (pct_relvol <= QUIET_PCTILE).fillna(False)

    out = daily.copy()
    out["quiet_A"] = quiet_a
    out["quiet_B"] = quiet_b
    out["prior_high"] = daily["high"].shift(1)
    out["prior_low"] = daily["low"].shift(1)
    return out


def attach_daily(d, daily):
    """Broadcasts each day's (already-causal) flags/levels to every 1h bar
    of that day -- safe because every value being broadcast was decided
    BEFORE the day started."""
    out = d.copy()
    out["date"] = out["timestamp"].dt.floor("D")
    for col in ("quiet_A", "quiet_B", "prior_high", "prior_low", "range_pct"):
        out[col] = out["date"].map(daily[col])
    return out


def prepare_frame(symbol):
    d, funding = load_asset(symbol)
    daily = daily_ohlcv(d)
    daily = build_quiet_flags(daily)
    d = attach_daily(d, daily)
    n, i_tr, i_va = split_points(d)
    return d, funding, daily, n, i_tr, i_va


def train_quiet_range_pct(d, i_tr, quiet_col):
    """TRAIN-only median day-range% across TRAIN-split calendar days
    flagged quiet under `quiet_col` -- the one sizing input every cell's
    stop_pct/target_pct is a fraction of. This project's standard
    'compute once from TRAIN, hold fixed across val' approximation
    (step43/step86 ENGINE NOTE), applied to the regime's own range."""
    train_dates = set(d["date"].iloc[:i_tr])
    sub = d.drop_duplicates("date")
    sub = sub[sub["date"].isin(train_dates) & sub[quiet_col].astype(bool)]
    vals = sub["range_pct"].dropna()
    return float(vals.median()) if len(vals) else float("nan")


# ---------------------------------------------------------------------------
# the three candidate setups -- all mean-reversion, mirror of family C
# ---------------------------------------------------------------------------

def setup1_fade_prior_range(d):
    """Price touches/exceeds YESTERDAY's high or low; fade back toward the
    developing range. No volume condition -- the quiet-day gate alone is
    this setup's filter."""
    long_mask = (d["low"] <= d["prior_low"]).fillna(False)
    short_mask = (d["high"] >= d["prior_high"]).fillna(False)
    return long_mask, short_mask


def setup2_bb_midline_reversion(d):
    """SAME Bollinger(20, 2.5std) extreme family C's breakout enters on,
    opposite trade: fade back toward the midline instead of riding the
    break. The literal mirror of this project's one sealed-passed
    strategy -- same geometry, opposite bet, opposite (quiet) regime."""
    _, lo, mid, up = bb_bands(d, 20, 2.5)
    long_mask = (d["close"] < lo).fillna(False)
    short_mask = (d["close"] > up).fillna(False)
    return long_mask, short_mask


def setup3_failed_breakout_fade(d):
    """Price WICKS through a Bollinger edge but CLOSES back inside on the
    SAME bar, AND that bar's own volume is BELOW its trailing 20-bar
    average -- the mirror image of family C's gate: there, high volume
    lets a breakout THROUGH; here, low volume is required to let a FADE
    through (the tell that the poke wasn't real)."""
    _, lo, mid, up = bb_bands(d, 20, 2.5)
    vol_avg20 = d["volume"].rolling(20).mean().shift(1)
    low_vol = (d["volume"] < LOW_VOL_MULT * vol_avg20).fillna(False)
    poke_up_fail = (d["high"] > up) & (d["close"] <= up)
    poke_down_fail = (d["low"] < lo) & (d["close"] >= lo)
    short_mask = (poke_up_fail & low_vol).fillna(False)
    long_mask = (poke_down_fail & low_vol).fillna(False)
    return long_mask, short_mask


SETUPS = {
    "S1-fade-prior-range": setup1_fade_prior_range,
    "S2-bb-midline-reversion": setup2_bb_midline_reversion,
    "S3-failed-breakout-fade": setup3_failed_breakout_fade,
}


# ---------------------------------------------------------------------------
# scoring / verdict / complementarity / random control
# ---------------------------------------------------------------------------

def score_costed(d, sig, funding, i_tr, i_va, stop_pct, target_pct, costs):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True), sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution="maker",
            funding_series=funding.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    if tr.expectancy > 0 and va.expectancy > 0:
        if len(tr.trades) >= MIN_TRAIN_TRADES and len(va.trades) >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def trades_per_year(tr, va, d, i_tr, i_va):
    n = len(tr.trades) + len(va.trades)
    t0, t1 = d["timestamp"].iloc[0], d["timestamp"].iloc[i_va - 1]
    span_yrs = (t1 - t0).total_seconds() / (365.25 * 86400)
    return round(n / span_yrs, 2) if span_yrs > 0 else float("nan")


def breakout_entry_days(d):
    """R87's exact sealed config (Bollinger breakout 20/2.5 + volume>=
    1.2x, 1h) replayed on this SAME frame -- used only to ask 'did the
    existing sealed breakout strategy also fire an entry today', not to
    re-score its own PnL."""
    base_sig = BREAKOUT_CONFIGS["Bollinger breakout 20/2.5"](d)
    vol_avg20 = d["volume"].rolling(20).mean().shift(1)
    vol_ok = d["volume"] >= 1.2 * vol_avg20
    gated = volume_gate_entry(base_sig, vol_ok)
    entries = (gated != 0) & (gated.shift(1).fillna(0) == 0)
    return set(d.loc[entries, "date"])


def complementarity_fraction(trades, breakout_days):
    if not trades:
        return float("nan")
    n_other = sum(1 for t in trades if t.entry_time.floor("D") not in breakout_days)
    return n_other / len(trades)


def random_control_rate(d, funding, i_tr, i_va, quiet_mask, n_events, stop_pct,
                         target_pct, trials=RANDOM_TRIALS, seed=RANDOM_SEED):
    """Same n_events, same stop_pct/target_pct/max-hold/cost engine, but
    fired at RANDOMLY chosen bars restricted to quiet-flagged bars within
    [0, i_va) with a random long/short coinflip per draw -- an EMPIRICAL
    calibration of 'expected by chance' for this exact engine/floor
    combination (step93's technique), not an assumed coin-flip."""
    if n_events < 5:
        return float("nan")
    eligible = np.where(quiet_mask.iloc[:i_va].to_numpy())[0]
    if len(eligible) < n_events:
        return float("nan")
    rng = np.random.default_rng(seed)
    mh_bars = hours_to_bars(d, MAX_HOLD_H)
    hits = 0
    for _ in range(trials):
        idx = rng.choice(eligible, size=n_events, replace=False)
        direction = rng.integers(0, 2, size=n_events)
        long_mask = pd.Series(False, index=d.index)
        short_mask = pd.Series(False, index=d.index)
        long_mask.iloc[idx[direction == 0]] = True
        short_mask.iloc[idx[direction == 1]] = True
        sig = day_trade_signal(d, long_mask, short_mask, mh_bars)
        tr, va = score_costed(d, sig, funding, i_tr, i_va, stop_pct, target_pct, REAL_COSTS)
        if verdict_for(tr, va) == "SURVIVOR":
            hits += 1
    return hits / trials


# ---------------------------------------------------------------------------
# main grid
# ---------------------------------------------------------------------------

def run_grid(asset, d, funding, i_tr, i_va):
    rows, survivors = [], []
    breakout_days = breakout_entry_days(d)
    for setup_name, setup_fn in SETUPS.items():
        raw_long, raw_short = setup_fn(d)
        for qdef in QUIET_DEFS:
            quiet_mask = d[qdef].astype(bool)
            long_mask = raw_long & quiet_mask
            short_mask = raw_short & quiet_mask
            range_pct = train_quiet_range_pct(d, i_tr, qdef)
            if not np.isfinite(range_pct) or range_pct <= 0:
                continue
            for stop_frac in STOP_FRACS:
                stop_pct = min(max(stop_frac * range_pct, RANGE_FLOOR), RANGE_CAP)
                for target_frac in TARGET_FRACS:
                    target_pct = min(max(target_frac * range_pct, RANGE_FLOOR), RANGE_CAP)
                    mh_bars = hours_to_bars(d, MAX_HOLD_H)
                    sig = day_trade_signal(d, long_mask, short_mask, mh_bars)

                    tr_n, va_n = score_costed(d, sig, funding, i_tr, i_va,
                                               stop_pct, target_pct, REAL_COSTS)
                    tr_g, va_g = score_costed(d, sig, funding, i_tr, i_va,
                                               stop_pct, target_pct, GROSS_COSTS)
                    net_verdict = verdict_for(tr_n, va_n)
                    gross_verdict = verdict_for(tr_g, va_g)

                    net_trades = list(tr_n.trades) + list(va_n.trades)
                    gross_trades = list(tr_g.trades) + list(va_g.trades)
                    comp_frac = complementarity_fraction(net_trades, breakout_days)

                    if net_trades:
                        net_exp = float(np.mean([t.pnl for t in net_trades]))
                        gross_exp = float(np.mean([t.pnl for t in gross_trades]))
                        avg_notional = float(np.mean([abs(t.units) * t.entry_price
                                                       for t in net_trades]))
                        cost_drag_bps = ((gross_exp - net_exp) / avg_notional * 1e4
                                         if avg_notional else float("nan"))
                    else:
                        net_exp = gross_exp = cost_drag_bps = float("nan")

                    row = dict(
                        asset=asset, setup=setup_name, quiet_def=qdef,
                        stop_frac=stop_frac, target_frac=target_frac,
                        range_pct_train=round(range_pct, 3),
                        stop_pct=round(stop_pct, 3), target_pct=round(target_pct, 3),
                        tr_n=len(tr_n.trades), tr_exp_net=round(tr_n.expectancy, 3),
                        tr_exp_gross=round(tr_g.expectancy, 3),
                        va_n=len(va_n.trades), va_exp_net=round(va_n.expectancy, 3),
                        va_exp_gross=round(va_g.expectancy, 3),
                        pooled_net_exp=round(net_exp, 3) if net_trades else float("nan"),
                        pooled_gross_exp=round(gross_exp, 3) if net_trades else float("nan"),
                        cost_drag_bps=round(cost_drag_bps, 2) if net_trades else float("nan"),
                        net_verdict=net_verdict, gross_verdict=gross_verdict,
                        complementarity=(round(comp_frac, 3)
                                          if not (isinstance(comp_frac, float) and np.isnan(comp_frac))
                                          else float("nan")),
                        trades_yr=trades_per_year(tr_n, va_n, d, i_tr, i_va),
                    )
                    rows.append(row)
                    if net_verdict == "SURVIVOR":
                        survivors.append(dict(row, stop_pct=stop_pct, target_pct=target_pct))
    return rows, survivors, breakout_days


def eth_transfer(survivor, d_eth, funding_eth, i_tr_eth, i_va_eth, breakout_days_eth):
    setup_fn = SETUPS[survivor["setup"]]
    raw_long, raw_short = setup_fn(d_eth)
    quiet_mask = d_eth[survivor["quiet_def"]].astype(bool)
    long_mask = raw_long & quiet_mask
    short_mask = raw_short & quiet_mask
    range_pct = train_quiet_range_pct(d_eth, i_tr_eth, survivor["quiet_def"])
    if not np.isfinite(range_pct) or range_pct <= 0:
        return dict(survivor, eth_verdict="NO-QUIET-TRAIN-SAMPLE", eth_tr_n=0, eth_va_n=0,
                     eth_tr_exp=float("nan"), eth_va_exp=float("nan"),
                     eth_trades_yr=float("nan"), eth_complementarity=float("nan"),
                     eth_range_pct_train=float("nan"))
    stop_pct = min(max(survivor["stop_frac"] * range_pct, RANGE_FLOOR), RANGE_CAP)
    target_pct = min(max(survivor["target_frac"] * range_pct, RANGE_FLOOR), RANGE_CAP)
    mh_bars = hours_to_bars(d_eth, MAX_HOLD_H)
    sig = day_trade_signal(d_eth, long_mask, short_mask, mh_bars)
    tr_n, va_n = score_costed(d_eth, sig, funding_eth, i_tr_eth, i_va_eth,
                               stop_pct, target_pct, REAL_COSTS)
    verdict = verdict_for(tr_n, va_n)
    trades = list(tr_n.trades) + list(va_n.trades)
    comp = complementarity_fraction(trades, breakout_days_eth)
    return dict(survivor, eth_verdict=verdict, eth_tr_n=len(tr_n.trades),
                eth_va_n=len(va_n.trades), eth_tr_exp=round(tr_n.expectancy, 3),
                eth_va_exp=round(va_n.expectancy, 3),
                eth_trades_yr=trades_per_year(tr_n, va_n, d_eth, i_tr_eth, i_va_eth),
                eth_complementarity=(round(comp, 3) if not (isinstance(comp, float) and np.isnan(comp))
                                      else float("nan")),
                eth_range_pct_train=round(range_pct, 3),
                eth_stop_pct=round(stop_pct, 3), eth_target_pct=round(target_pct, 3))


def chance_baseline(d, funding, i_tr, i_va, rows_df):
    """One representative cell per setup (quiet_A, stop_frac=0.4,
    target_frac=0.5) -- its real train+val trade count/stop_pct/target_pct
    replayed on random quiet-day timing, 30 draws, scaled by the 12 cells
    (2 quiet-defs x 2 stop_frac x 3 target_frac) sharing that setup."""
    out = []
    cells_per_setup = len(QUIET_DEFS) * len(STOP_FRACS) * len(TARGET_FRACS)
    for setup_name in SETUPS:
        rep = rows_df[(rows_df["setup"] == setup_name) & (rows_df["quiet_def"] == "quiet_A")
                       & (rows_df["stop_frac"] == 0.4) & (rows_df["target_frac"] == 0.5)]
        if rep.empty:
            continue
        rep = rep.iloc[0]
        n_events = int(rep["tr_n"] + rep["va_n"])
        rate = random_control_rate(d, funding, i_tr, i_va, d["quiet_A"].astype(bool),
                                    n_events, rep["stop_pct"], rep["target_pct"])
        out.append(dict(setup=setup_name, rep_n_events=n_events,
                         rep_stop_pct=rep["stop_pct"], rep_target_pct=rep["target_pct"],
                         empirical_survivor_rate=rate, cells_this_setup=cells_per_setup,
                         expected_by_chance=(rate * cells_per_setup
                                              if not (isinstance(rate, float) and np.isnan(rate))
                                              else float("nan"))))
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 78)
    print("ROUND 94 -- THE QUIET-DAY PLAYBOOK")
    print("=" * 78)

    print("\nLoading cached BTC + ETH 1h data (no network calls expected)...")
    d_btc, f_btc, daily_btc, n_btc, i_tr_btc, i_va_btc = prepare_frame("BTCUSDT")
    d_eth, f_eth, daily_eth, n_eth, i_tr_eth, i_va_eth = prepare_frame("ETHUSDT")
    print(f"  BTC 1h: {n_btc} bars, {d_btc['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d_btc['timestamp'].iloc[-1]:%Y-%m-%d} | train ends "
          f"{d_btc['timestamp'].iloc[i_tr_btc]:%Y-%m-%d}, val ends "
          f"{d_btc['timestamp'].iloc[i_va_btc]:%Y-%m-%d} (test sealed)")
    print(f"  ETH 1h: {n_eth} bars, {d_eth['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d_eth['timestamp'].iloc[-1]:%Y-%m-%d}")

    # sanity check: reproduce the pre-measured quiet-day range figure on
    # THIS project's own cached data (independent of the Bitstamp source
    # cited in the brief)
    btc_train_days = daily_btc.iloc[:int(len(daily_btc) * 0.8)]
    q_a = btc_train_days[btc_train_days["quiet_A"]]["range_pct"].dropna()
    print(f"\n  Sanity check (BTC, bybit 1h resampled to daily, quiet_A, "
          f"train+val calendar): n={len(q_a)} quiet days, "
          f"median range%={q_a.median():.2f}, "
          f"25th={q_a.quantile(.25):.2f}, 75th={q_a.quantile(.75):.2f}, "
          f"pct>1%={100 * (q_a > 1.0).mean():.1f}%")

    print(f"\nRunning BTC grid: {len(SETUPS)} setups x {len(QUIET_DEFS)} quiet-defs x "
          f"{len(STOP_FRACS)} stop_fracs x {len(TARGET_FRACS)} target_fracs = "
          f"{len(SETUPS) * len(QUIET_DEFS) * len(STOP_FRACS) * len(TARGET_FRACS)} cells...")
    rows, survivors, breakout_days_btc = run_grid("BTC", d_btc, f_btc, i_tr_btc, i_va_btc)
    df = pd.DataFrame(rows)
    print(f"  {len(df)} cells run. Net verdict counts:\n{df['net_verdict'].value_counts().to_string()}")
    print(f"  BTC net SURVIVORS: {len(survivors)}")

    print("\nComputing empirical chance baseline (30 random-timing draws per representative cell)...")
    chance_df = chance_baseline(d_btc, f_btc, i_tr_btc, i_va_btc, df)
    print(chance_df.to_string(index=False))
    total_expected = chance_df["expected_by_chance"].sum()
    print(f"  Total cells run: {len(df)}  |  total expected SURVIVORs by chance: "
          f"{total_expected:.2f}  |  actual net SURVIVORs: {len(survivors)}")

    print(f"\nRunning ETH transfer on {len(survivors)} BTC survivor(s)...")
    breakout_days_eth = breakout_entry_days(d_eth)
    eth_rows = []
    for surv in survivors:
        eth_rows.append(eth_transfer(surv, d_eth, f_eth, i_tr_eth, i_va_eth, breakout_days_eth))
    eth_df = pd.DataFrame(eth_rows)
    if len(eth_df):
        print(eth_df[["setup", "quiet_def", "stop_frac", "target_frac", "eth_tr_n", "eth_tr_exp",
                       "eth_va_n", "eth_va_exp", "eth_verdict", "eth_trades_yr",
                       "eth_complementarity"]].to_string(index=False))
    else:
        print("  (no BTC survivors to transfer)")

    df.to_csv("step94_table.csv", index=False)
    print(f"\nwrote step94_table.csv: {len(df)} rows")

    return df, survivors, eth_df, chance_df, breakout_days_btc, daily_btc


if __name__ == "__main__":
    main()
