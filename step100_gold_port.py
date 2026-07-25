"""
step100_gold_port.py — Round 100: PORT EVERY CRYPTO STRATEGY FAMILY TO GOLD.

Wallace, 2026-07-25: "Have you even tested using the logic you use for
crypto on gold? Creating logic wise... This isn't gonna work unless you
are able to create multiple [edges]." Honest answer going in: no. Gold has
had 2 research rounds (48, 55) and 5 families tested, producing ONE
survivor (donchian20/55 + EMA20 exit). Crypto has ~30 families tested
across 50+ rounds producing 5 live edges. This round ports every
crypto-validated family's LOGIC (never its constants) to gold and
re-derives every threshold from gold's own distributions, plus tests
gold-native structure (sessions as FILTERS, the overnight gap, DXY regime).

RESEARCH ONLY. Writes exactly: step100_gold_port.py (this file),
step100_results.md, step100_table.csv. No commits, no live orders,
gold_book.py and every other live file untouched.

PLUMBING REUSE (imported verbatim — logic ported, not reinvented)
  backtest.py        CostModel, run_backtest — the only engine there is.
  strategy.py        atr, rsi, vol_gated_ma, ma_crossover, resample_4h,
                      _hysteresis — generic indicators/signals, no BTC
                      constants baked in (vol_gated_ma's own default
                      min_atr_pct=1.5 is BTC-calibrated and is NEVER used
                      here — every call below passes gold's own recomputed
                      threshold explicitly).
  step41_shorts.py    confirmed_swings, last_n_confirmed, adaptive_vol_gate
                      — per the task's explicit instruction, swing
                      detection is NOT reinvented.
  step43_daytrade.py  MIN_TRAIN_TRADES, MIN_VAL_TRADES, bar_hours,
                      hours_to_bars, split_points, day_trade_signal,
                      hold_stats, champ_aligned — generic gauntlet
                      plumbing, no market-specific constants.
  step56_smc_toolkit.py  bos_chain, liquidity_pools, sweep_events,
                      equilibrium, fvg_signals, train_median_stop_pct —
                      the CHoCH/liquidity-sweep/FVG toolkit, sealed
                      +$99.52/trade on BTC (BOS-continuation).
  step58_divergence_mtf.py  swings, macd_hist, divergence_events,
                      swing_stop_pct, STOP_CAP_SWING — the hidden-
                      divergence family, sealed +$52/trade on BTC.
  step86_specified.py  confirm_after_level, carry_extreme,
                      divergence_events_ext, volume_gate_entry,
                      sweep_mss_displacement, bollinger_breakout_signal —
                      R86's confirmation-gate fix (the condition that
                      makes regular divergence work) and the volume-gated
                      breakout shape.

WHAT IS NOT PORTED HERE, AND WHY
  News/event momentum: gold's analogue is scheduled macro (CPI/FOMC/NFP).
  This repo has no verified economic-calendar dataset — data_news_mkts_
  GC=F.parquet is plain OHLCV, not event timestamps. NFP is tested via a
  public, well-known PROXY RULE (first Friday of the month, ~12:30 UTC)
  explicitly caveated as a proxy, not a verified release calendar
  (misses holiday-shifted releases, no revisions data). CPI and FOMC are
  NOT tested — a 26-year hand-recalled meeting calendar would risk being
  exactly the kind of confident-wrong-answer this repo has been burned by
  before (see BLOFIN_API_REFERENCE.md's own lesson). Stated plainly
  rather than faked.

STRUCTURAL STOPS (the task's central new standard)
  Every stop in this script is derived from confirmed_swings() — never a
  swept percentage. run_backtest takes ONE fixed stop_pct per call (see
  every step4x/5x/8x docstring for this same note), so — following this
  repo's own established approximation — the per-trade structural
  distance (entry close to the nearest confirmed opposing swing, plus a
  stated buffer) is measured at every qualifying TRAIN entry, and its
  MEDIAN is held fixed across train+val, hard-capped. The resulting stop
  distance is reported as an OUTPUT for every row (stop_pct column), in
  both units: % of price AND % of margin at a stated reference leverage
  (20x — illustrative only, matching the BLOFIN_API_REFERENCE.md
  convention, NOT a sizing recommendation).

SIZING FROM THE STOP
  size_frac = clip(RISK_FRAC_PCT / stop_pct, floor, cap). This is
  run_backtest's own `size_frac` (fraction of equity deployed as
  notional) — a tighter structural stop buys a bigger position, a wider
  one a smaller one, so every trade risks approximately the same
  RISK_FRAC_PCT of equity at its own stop. Leverage (size_frac itself,
  since size_frac=1.0 means "1x equity as notional, no leverage" in this
  engine) is reported as an OUTPUT, never hand-picked per config.

COSTS — execution="taker" ALWAYS (the round's other new standard: a
  maker-fill validated strategy on BTC flipped from +$5.21 to -$8.15/
  trade at taker hours after going live. Every number in this file is a
  taker number.)
  GC=F (COMEX futures): GOLD_COSTS, 0.5bp fee + 0.5bp slippage, no spread,
    no funding (dated futures) -> round trip 2.0bps.
  GLD (ETF): GLD_COSTS, 1.0bp fee + 1.0bp slippage, no spread, no funding
    -> round trip 4.0bps.
  XAUT-USDT (BloFin venue-transfer check only): BLOFIN_COSTS, the repo
    default (6bp taker/2bp maker/1bp spread/2bp slippage/1bp funding
    conservative-always-pay) — what a real position on that venue costs.

THICKNESS BAR: edge reported as % of notional per trade AND as a multiple
  of round-trip cost. Under 5x is a reject regardless of the dollar
  figure (the task's own bar; the killed crypto breakout was 1.5x, gold's
  donchian is 17x).

GAUNTLET: chronological 60/20/20 per asset/timeframe (split_points).
  SURVIVOR = positive expectancy train AND val, >=30 train / >=8 val
  trades. INSUFFICIENT-SAMPLE = positive both windows, under the floor.
  FAIL = negative either window. The sealed final 20% is NEVER sliced,
  scored, or printed anywhere in this script. Selection is by TRAIN
  expectancy only; val is read once.

CROSS-INSTRUMENT TRANSFER: every family's grid runs identically-shaped on
  BOTH GC=F and GLD (same k / buffer / threshold / gate values — only the
  train-median stop distance, a nuisance nesting parameter not a
  selection choice, differs per asset's own data, same convention R86
  used for its ETH replay). A `transfer` column reports whether a config
  that clears SURVIVOR on one asset also clears it (any verdict >=
  INSUFFICIENT-SAMPLE with positive both windows) on the other. Top
  overall survivors additionally get a whole-history XAUT-USDT
  compatibility read (not a validation split, same convention as R55).

CHANCE BASELINE: for the final survivor set, a random-entry permutation
  test (same trade count, same stop/target/size, 25 shuffles) reports how
  often a SURVIVOR verdict would happen on pure noise — R83/R88's own
  standard for "state cells run vs expected by chance."
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from strategy import atr, rsi, vol_gated_ma, ma_crossover, resample_4h, _hysteresis
from step41_shorts import confirmed_swings, last_n_confirmed, adaptive_vol_gate
from step43_daytrade import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    bar_hours, hours_to_bars, split_points, day_trade_signal, hold_stats,
    champ_aligned,
)
from step56_smc_toolkit import (
    bos_chain, liquidity_pools, sweep_events, equilibrium, fvg_signals,
    train_median_stop_pct,
)
from step58_divergence_mtf import (
    swings, macd_hist, divergence_events, swing_stop_pct, STOP_CAP_SWING,
)
from step86_specified import (
    confirm_after_level, carry_extreme, divergence_events_ext,
    volume_gate_entry, sweep_mss_displacement, bollinger_breakout_signal,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------------------
# Costs — taker, always. Round-trip bps stated beside every number via mk_row.
# ---------------------------------------------------------------------------

GOLD_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                        slippage_bps=0.5, funding_bps_8h=0.0)          # GC=F, RT=2.0bps
GLD_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                       slippage_bps=1.0, funding_bps_8h=0.0)           # GLD ETF, RT=4.0bps
BLOFIN_COSTS = CostModel()                                             # XAUT-USDT transfer check only

COSTS_BY_ASSET = {"GC=F": GOLD_COSTS, "GLD": GLD_COSTS}
EXECUTION = "taker"

RISK_FRAC_PCT = 1.0     # % of equity risked per trade at the structural stop
SIZE_FRAC_CAP, SIZE_FRAC_FLOOR = 5.0, 0.1
REF_LEVERAGE = 20        # illustrative only, for the owner's "% of margin" framing
INITIAL_EQUITY = 10_000.0

RESULTS: list[dict] = []


# ---------------------------------------------------------------------------
# data loading — no new files written (task's file-list is exhaustive)
# ---------------------------------------------------------------------------

def load_gcf(tf: str) -> pd.DataFrame:
    return pd.read_parquet(f"data_gold_{tf}.parquet")


def load_gld(tf: str) -> pd.DataFrame:
    return pd.read_parquet(f"data_tradfi_GLD_{tf}.parquet")


def load_xaut_1h() -> pd.DataFrame:
    return pd.read_parquet("data_gold_xaut_1h.parquet")


def load_dxy_1d() -> pd.DataFrame | None:
    """DX-Y.NYB daily via yfinance, fetched fresh (no cache file — the task's
    file list is exhaustive). Returns None (family skipped honestly) if the
    fetch fails for any reason."""
    try:
        import yfinance as yf
        raw = yf.Ticker("DX-Y.NYB").history(period="max", interval="1d", auto_adjust=False)
        if raw is None or len(raw) == 0:
            return None
        df = raw.reset_index()
        out = pd.DataFrame({
            "timestamp": pd.to_datetime(df["Date"], utc=True),
            "close": df["Close"].astype(float),
        }).dropna().sort_values("timestamp").reset_index(drop=True)
        return out
    except Exception as e:
        print(f"  DXY fetch failed ({e}) — Family DXY-regime will be skipped honestly")
        return None


print("Loading gold data (cached parquet, no network calls for GC=F/GLD/XAUT)...")
FRAMES: dict[str, dict[str, pd.DataFrame]] = {"GC=F": {}, "GLD": {}}
FRAMES["GC=F"]["1d"] = load_gcf("1d")
FRAMES["GC=F"]["1h"] = load_gcf("1h")
FRAMES["GC=F"]["4h"] = load_gcf("4h")
FRAMES["GLD"]["1d"] = load_gld("1d")
FRAMES["GLD"]["1h"] = load_gld("1h")
FRAMES["GLD"]["4h"] = resample_4h(FRAMES["GLD"]["1h"])
XAUT_1H = load_xaut_1h()
DXY_1D = load_dxy_1d()

for asset, tfs in FRAMES.items():
    for tf, d in tfs.items():
        print(f"  {asset} {tf}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
print(f"  XAUT-USDT 1h: {len(XAUT_1H)} bars {XAUT_1H['timestamp'].iloc[0]:%Y-%m-%d} -> "
      f"{XAUT_1H['timestamp'].iloc[-1]:%Y-%m-%d} (transfer check only)")
if DXY_1D is not None:
    print(f"  DXY 1d: {len(DXY_1D)} bars {DXY_1D['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{DXY_1D['timestamp'].iloc[-1]:%Y-%m-%d}")

# meta: per asset/tf -> n, i_tr, i_va, med_atr% (train), p75_atr% (train)
META: dict[str, dict[str, dict]] = {"GC=F": {}, "GLD": {}}
for asset, tfs in FRAMES.items():
    for tf, d in tfs.items():
        n, i_tr, i_va = split_points(d)
        atr_pct = atr(d, 14) / d["close"] * 100
        med = float(atr_pct.iloc[:i_tr].median())
        p75 = float(atr_pct.iloc[:i_tr].quantile(0.75))
        META[asset][tf] = {"n": n, "i_tr": i_tr, "i_va": i_va, "med_atr": med, "p75_atr": p75}
        print(f"  {asset} {tf}: train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | "
              f"median train ATR%={med:.3f}  p75={p75:.3f}")

ASSETS = ("GC=F", "GLD")


# ---------------------------------------------------------------------------
# shared plumbing (gold-specific: taker execution, no funding series, and
# structural-stop-based sizing)
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None, size_frac=1.0):
    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution=EXECUTION, size_frac=size_frac,
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


def both_positive(tr, va):
    return tr.expectancy > 0 and va.expectancy > 0


def size_frac_from_stop(stop_pct):
    if not stop_pct or stop_pct <= 0:
        return 1.0
    return float(np.clip(RISK_FRAC_PCT / stop_pct, SIZE_FRAC_FLOOR, SIZE_FRAC_CAP))


def trades_per_year(d, i_va, tr, va):
    n = len(tr.trades) + len(va.trades)
    ts = pd.DatetimeIndex(d["timestamp"])
    span_days = (ts[i_va - 1] - ts[0]).total_seconds() / 86400
    yrs = span_days / 365.25
    return n / yrs if yrs > 0 else float("nan")


def fresh_entries(sig):
    """0/±1 continuous state signal -> boolean (long_entry, short_entry) at
    every fresh 0->nonzero transition (a re-entry after a flip counts too)."""
    s = sig.fillna(0)
    prev = s.shift(1).fillna(0)
    long_entry = (s > 0) & (prev <= 0)
    short_entry = (s < 0) & (prev >= 0)
    return long_entry, short_entry


def structural_dist(d, k, buffer_pct=0.15):
    """Distance (%) from close to the nearest CONFIRMED opposing swing,
    plus a buffer — the stop-distance candidate for every family. Long
    stops reference the last confirmed swing LOW; short stops the last
    confirmed swing HIGH. confirmed_swings() imported verbatim from
    step41_shorts.py, per the task's explicit instruction."""
    sh_price, sl_price = confirmed_swings(d, k)
    lsh, lsl = sh_price.ffill(), sl_price.ffill()
    dist_long = (d["close"] - lsl) / d["close"] * 100 + buffer_pct
    dist_short = (lsh - d["close"]) / d["close"] * 100 + buffer_pct
    return dist_long, dist_short, lsh, lsl


def structural_stop_for_signal(d, i_tr, long_entry, short_entry, k, buffer_pct=0.15,
                                cap=8.0, floor=0.3):
    dist_long, dist_short, _, _ = structural_dist(d, k, buffer_pct)
    dist = pd.Series(np.nan, index=d.index)
    dist = dist.mask(long_entry, dist_long)
    dist = dist.mask(short_entry, dist_short)
    mask = long_entry | short_entry
    return train_median_stop_pct(d, i_tr, mask, dist, cap=cap, floor=floor)


def edge_stats(tr, va, size_frac, rt_bps):
    """Edge as % of notional per trade (pooled train+val expectancy over
    notional deployed) and as a multiple of round-trip cost — the task's
    THICKNESS BAR, computed for every row."""
    n = len(tr.trades) + len(va.trades)
    if n == 0 or size_frac is None:
        return None, None
    combined_exp = (tr.expectancy * len(tr.trades) + va.expectancy * len(va.trades)) / n
    notional = size_frac * INITIAL_EQUITY
    edge_pct_notional = combined_exp / notional * 100
    edge_bps = edge_pct_notional * 100
    edge_cost_mult = edge_bps / rt_bps if rt_bps else None
    return edge_pct_notional, edge_cost_mult


def mk_row(family, config, tf, asset, tr, va, stop_pct=None, target_pct=None,
           size_frac=None, k=None, extra=None):
    med_h, mean_h = hold_stats(tr, va)
    costs = COSTS_BY_ASSET.get(asset, BLOFIN_COSTS)
    rt_bps = costs.round_trip_bps()
    edge_pct, edge_mult = edge_stats(tr, va, size_frac if size_frac else 1.0, rt_bps)
    row = {
        "family": family, "config": config, "tf": tf, "asset": asset,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_dd%": tr.max_drawdown_pct, "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_dd%": va.max_drawdown_pct, "va_ret%": va.total_return_pct,
        "med_hold_h": med_h, "mean_hold_h": mean_h,
        "stop_%price": stop_pct, "target_%price": target_pct,
        "stop_%margin_at_20x": (round(stop_pct * REF_LEVERAGE, 2) if stop_pct else None),
        "size_frac_leverage": size_frac,
        "round_trip_cost_bps": rt_bps,
        "edge_%notional_per_trade": edge_pct,
        "edge_x_cost": edge_mult,
        "k": k,
        "verdict": verdict_for(tr, va),
    }
    if extra:
        row.update(extra)
    return row


def gate_entry(sig, cond_ok):
    """Alias of step86.volume_gate_entry — generalized name, identical
    mechanics: at each fresh 0->nonzero transition of `sig`, the WHOLE
    excursion is suppressed unless cond_ok is True at that transition bar.
    Used here for the session and DXY-regime FILTER families."""
    return volume_gate_entry(sig, cond_ok)


def chance_baseline(d, costs, i_tr, i_va, n_long, n_short, stop_pct, target_pct,
                     size_frac, hold_h=96, trials=25, seed=0):
    """Random-entry permutation test: same trade counts, same stop/target/
    size, shuffled timing. Returns the fraction of `trials` that would
    still clear SURVIVOR by pure noise — R83/R88's own chance-baseline
    standard, applied here to the final gold survivor set."""
    rng = np.random.default_rng(seed)
    n = int(i_va)
    lo = 20
    hi = max(lo + 1, n - 5)
    survivors = 0
    for _ in range(trials):
        pool = np.arange(lo, hi)
        if len(pool) < (n_long + n_short):
            break
        chosen = rng.choice(pool, size=min(len(pool), n_long + n_short), replace=False)
        rng.shuffle(chosen)
        long_idx = chosen[:n_long]
        short_idx = chosen[n_long:n_long + n_short]
        el = pd.Series(False, index=d.index)
        es = pd.Series(False, index=d.index)
        if len(long_idx):
            el.iloc[long_idx] = True
        if len(short_idx):
            es.iloc[short_idx] = True
        mh_bars = hours_to_bars(d, hold_h)
        sig = day_trade_signal(d, el, es, mh_bars)
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct,
                        target_pct=target_pct, size_frac=size_frac)
        if verdict_for(tr, va) == "SURVIVOR":
            survivors += 1
    return survivors / trials if trials else float("nan")


BUFFER_OPTIONS = (0.15, 0.35)   # % — swept per the task's "sweep the buffer" ask
K_OPTIONS = (5, 8)              # fractal swing radius — swept per the task


# ===========================================================================
# FAMILY 1 — hidden RSI/MACD divergence, 4h continuation (BTC: sealed +$52/t)
# ===========================================================================
# Ported unchanged in SHAPE: divergence_events() imported verbatim from
# step58_divergence_mtf.py. The one constant that must be recomputed is the
# 4h "champion trend" gate the hidden flavor requires (continuation only
# fires WITH the prevailing trend) — on BTC this was vol_gated_ma's 1.5%
# ATR gate; on gold it is vol_gated_ma's OWN gate recomputed from gold's own
# 4h train-median ATR% (~0.55%, vs BTC's 1.5% — never ported unscaled).

OSCILLATORS = {"RSI14": lambda d: rsi(d["close"], 14), "MACDhist": lambda d: macd_hist(d["close"])}


def family1_hidden_divergence():
    rows = []
    for asset in ASSETS:
        d4h = FRAMES[asset]["4h"]
        m4h = META[asset]["4h"]
        champ4h = vol_gated_ma(d4h, fast=20, slow=100, min_atr_pct=m4h["med_atr"],
                                allow_short=False).fillna(0)
        for tf in ("1h", "4h"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            champ_al = champ4h if tf == "4h" else champ_aligned(d4h, champ4h, d)
            for osc_name, osc_fn in OSCILLATORS.items():
                osc = osc_fn(d)
                for k in K_OPTIONS:
                    _, _, long_hid, short_hid, low_ext, high_ext = divergence_events(d, osc, k, champ_al)
                    el, es = long_hid, short_hid
                    n_events = int(el.sum() + es.sum())
                    if n_events == 0:
                        continue
                    for buffer_pct in BUFFER_OPTIONS:
                        stop_l = swing_stop_pct(d["close"], low_ext, el, i_tr, buffer_pct, STOP_CAP_SWING)
                        stop_s = swing_stop_pct(d["close"], high_ext, es, i_tr, buffer_pct, STOP_CAP_SWING)
                        n_l, n_s = int(el.sum()), int(es.sum())
                        stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else STOP_CAP_SWING
                        target_pct = min(2.5 * stop_pct, 3 * STOP_CAP_SWING)
                        mh_bars = hours_to_bars(d, 96)
                        sig = day_trade_signal(d, el, es, mh_bars)
                        size_frac = size_frac_from_stop(stop_pct)
                        tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
                        cfg = f"{osc_name} k{k} hidden buf{buffer_pct:.2f}% (gold champ gate {m4h['med_atr']:.2f}%ATR)"
                        row = mk_row("1-hidden-divergence", cfg, tf, asset, tr, va,
                                      stop_pct, target_pct, size_frac, k=k,
                                      extra={"n_events": n_events, "buffer_pct": buffer_pct,
                                             "trades_yr": trades_per_year(d, i_va, tr, va)})
                        rows.append(row)
    return rows


# ===========================================================================
# FAMILY 2 — regular divergence WITH R86's confirmation gate
# ===========================================================================
# R86 found the confirmation candle (wait for a close back through the
# intervening structural swing between the two divergent points, don't
# enter on the divergence bar itself) is the condition that makes regular
# divergence work. divergence_events_ext / confirm_after_level / carry_
# extreme imported verbatim from step86_specified.py.

def family2_regular_divergence_confirmed():
    rows = []
    for asset in ASSETS:
        for tf in ("1h", "4h"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            for osc_name, osc_fn in OSCILLATORS.items():
                osc = osc_fn(d)
                for k in K_OPTIONS:
                    (long_reg, short_reg, low_ext, high_ext,
                     confirm_long, confirm_short) = divergence_events_ext(d, osc, k)
                    if int(long_reg.sum() + short_reg.sum()) == 0:
                        continue
                    close_arr = d["close"].to_numpy()
                    for max_wait in (10, 20):
                        trig_long, origin_long = confirm_after_level(long_reg, confirm_long, close_arr, "long", max_wait)
                        trig_short, origin_short = confirm_after_level(short_reg, confirm_short, close_arr, "short", max_wait)
                        trig_long.index = d.index
                        trig_short.index = d.index
                        el, es = trig_long.astype(bool), trig_short.astype(bool)
                        n_events = int(el.sum() + es.sum())
                        if n_events == 0:
                            continue
                        ext_l_carried = carry_extreme(len(d), d.index, origin_long, low_ext.to_numpy())
                        ext_h_carried = carry_extreme(len(d), d.index, origin_short, high_ext.to_numpy())
                        for buffer_pct in BUFFER_OPTIONS:
                            stop_l = swing_stop_pct(d["close"], ext_l_carried, el, i_tr, buffer_pct, STOP_CAP_SWING)
                            stop_s = swing_stop_pct(d["close"], ext_h_carried, es, i_tr, buffer_pct, STOP_CAP_SWING)
                            n_l, n_s = int(el.sum()), int(es.sum())
                            stop_pct = ((stop_l * n_l + stop_s * n_s) / (n_l + n_s)) if (n_l + n_s) else STOP_CAP_SWING
                            target_pct = min(2.5 * stop_pct, 3 * STOP_CAP_SWING)
                            mh_bars = hours_to_bars(d, 96)
                            sig = day_trade_signal(d, el, es, mh_bars)
                            size_frac = size_frac_from_stop(stop_pct)
                            tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                                           stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
                            cfg = (f"{osc_name} k{k} regular+CONFIRM wait{max_wait} buf{buffer_pct:.2f}%")
                            row = mk_row("2-regular-div-confirmed", cfg, tf, asset, tr, va,
                                          stop_pct, target_pct, size_frac, k=k,
                                          extra={"n_events": n_events, "buffer_pct": buffer_pct,
                                                 "max_wait": max_wait,
                                                 "trades_yr": trades_per_year(d, i_va, tr, va)})
                            rows.append(row)
    return rows


# ===========================================================================
# FAMILY 3 — CHoCH + confluence >= 2 (BTC: sealed +$99.52/t)
# ===========================================================================
# bos_chain / equilibrium / liquidity_pools / sweep_events / fvg_signals
# imported verbatim from step56_smc_toolkit.py. Confluence votes (4, a
# faithful subset of BTC's 5 — FIB dropped for scope, everything else
# kept): bias (gold's own 20/100 MA-cross direction, NOT BTC's vol-gated
# champion — gold's ATR gate constant would otherwise leak in unstated),
# discount/premium (price vs the 50% LSH/LSL equilibrium), a same-
# direction liquidity sweep in the last 24h, and an active unfilled FVG.

def family3_choch_confluence():
    rows = []
    for asset in ASSETS:
        for tf in ("1h", "4h"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            trend = ma_crossover(d, 20, 100, allow_short=True).fillna(0)
            for k in K_OPTIONS:
                bos = bos_chain(d, k)
                discount, premium, eq, lsh, lsl = equilibrium(d, k)
                pool_high, pool_low = liquidity_pools(d, k, 0.1)
                sweep_long, sweep_short = sweep_events(d, pool_high, pool_low, 0.3)
                window = hours_to_bars(d, 24)
                swept_recent_long = sweep_long.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool)
                swept_recent_short = sweep_short.astype(int).rolling(window, min_periods=1).max().fillna(0).astype(bool)
                _, _, _, _, ab, ar = fvg_signals(d, 0.5, hours_to_bars(d, 240))
                bias_long, bias_short = (trend == 1), (trend == -1)
                count_long = bias_long.astype(int) + discount.astype(int) + swept_recent_long.astype(int) + ab.astype(int)
                count_short = bias_short.astype(int) + premium.astype(int) + swept_recent_short.astype(int) + ar.astype(int)
                choch_long, choch_short = bos["choch_long"], bos["choch_short"]
                dist_long = (d["close"] - bos["lsl"]) / d["close"] * 100
                dist_short = (bos["lsh"] - d["close"]) / d["close"] * 100
                for threshold in (0, 2):
                    if threshold == 0:
                        el, es = choch_long, choch_short
                    else:
                        el = choch_long & (count_long >= threshold)
                        es = choch_short & (count_short >= threshold)
                    mask = el | es
                    n_events = int(mask.sum())
                    if n_events == 0:
                        continue
                    dist = pd.Series(np.nan, index=d.index)
                    dist = dist.mask(el, dist_long)
                    dist = dist.mask(es, dist_short)
                    stop_pct = train_median_stop_pct(d, i_tr, mask, dist, cap=6.0, floor=0.25)
                    if stop_pct is None:
                        continue
                    target_pct = stop_pct * 2.5
                    mh_bars = hours_to_bars(d, 240)
                    sig = day_trade_signal(d, el, es, mh_bars)
                    size_frac = size_frac_from_stop(stop_pct)
                    tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
                    cfg = f"k{k} CHoCH thresh>={threshold}"
                    row = mk_row("3-choch-confluence", cfg, tf, asset, tr, va,
                                  stop_pct, target_pct, size_frac, k=k,
                                  extra={"n_events": n_events, "threshold": threshold,
                                         "trades_yr": trades_per_year(d, i_va, tr, va)})
                    rows.append(row)
    return rows


# ===========================================================================
# FAMILY 4 — vol-gated trend, STRICT gate (BTC: sealed +$401/t, the
# thickest crypto edge owned)
# ===========================================================================
# vol_gated_ma imported verbatim; every min_atr_pct threshold below is
# recomputed from gold's OWN train-median/p75 ATR%, never BTC's 1.5%.
# Also tests an ADAPTIVE-STRICT gate (own trailing 75th percentile, not
# just the median R48/R55 already tried) — the task's explicit "strict"
# ask, genuinely new vs the prior two gold rounds. Entries additionally
# carry a structural safety stop (past the nearest confirmed swing) since
# the original crypto/step48 versions used NO stop at all — signal exit
# (the MA cross itself) remains primary; the structural stop is a floor.

def adaptive_vol_gate_pct(d, pct=75, window_days=365, atr_n=14):
    a_pct = atr(d, atr_n) / d["close"] * 100
    window = max(30, round(24 / bar_hours(d) * window_days))
    min_periods = max(30, window // 10)
    trailing = a_pct.rolling(window, min_periods=min_periods).quantile(pct / 100).shift(1)
    return (a_pct > trailing).fillna(False)


def family4_vol_gated_trend_strict():
    rows = []
    for asset in ASSETS:
        for tf in ("1h", "4h", "1d"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            adapt_med, _ = adaptive_vol_gate(d, direction="above")
            adapt_p75 = adaptive_vol_gate_pct(d, pct=75)
            gates = {
                "ungated": dict(min_atr_pct=0.0, entry_filter=None),
                f"fixed-median({m['med_atr']:.2f}%)": dict(min_atr_pct=m["med_atr"], entry_filter=None),
                f"fixed-p75-STRICT({m['p75_atr']:.2f}%)": dict(min_atr_pct=m["p75_atr"], entry_filter=None),
                "adaptive-median": dict(min_atr_pct=0.0, entry_filter=adapt_med),
                "adaptive-p75-STRICT": dict(min_atr_pct=0.0, entry_filter=adapt_p75),
            }
            for name, kw in gates.items():
                sig = vol_gated_ma(d, fast=20, slow=100, allow_short=False, **kw)
                long_entry, short_entry = fresh_entries(sig)
                n_events = int(long_entry.sum() + short_entry.sum())
                if n_events == 0:
                    continue
                stop_pct = structural_stop_for_signal(d, i_tr, long_entry, short_entry, k=8,
                                                       buffer_pct=0.15, cap=8.0, floor=0.3)
                if stop_pct is None:
                    continue
                size_frac = size_frac_from_stop(stop_pct)
                tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                               stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
                cfg = f"20/100 {name}"
                row = mk_row("4-vol-gated-trend-strict", cfg, tf, asset, tr, va,
                              stop_pct, None, size_frac, k=8,
                              extra={"n_events": n_events, "gate_name": name,
                                     "trades_yr": trades_per_year(d, i_va, tr, va)})
                rows.append(row)
    return rows


# ===========================================================================
# FAMILY 5 — volume-gated breakout (BTC: R86/R87, killed at taker on crypto
# — the task flags this as gold's PRIORITY test since the edge here may be
# an order of magnitude thicker)
# ===========================================================================
# bollinger_breakout_signal / volume_gate_entry imported verbatim from
# step86_specified.py (which itself reuses step76's bb_bands 20/2.5 — the
# shape the task literally names). Structural safety stop added (the R86/
# R87 crypto version ran bare/percent-stop; here it's confirmed-swing-
# based, per this round's mandate).

def family5_volume_gated_breakout():
    rows = []
    for asset in ASSETS:
        for tf in ("1h", "4h"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            base_sig = bollinger_breakout_signal(d)
            vol_avg20 = d["volume"].rolling(20).mean().shift(1)
            variants = {"bare (no volume gate)": base_sig}
            for vmult in (1.2, 1.5):
                vol_ok = d["volume"] >= vmult * vol_avg20
                variants[f"volume>={vmult}x20avg"] = gate_entry(base_sig, vol_ok)
            for name, sig in variants.items():
                long_entry, short_entry = fresh_entries(sig)
                n_events = int(long_entry.sum() + short_entry.sum())
                if n_events == 0:
                    continue
                stop_pct = structural_stop_for_signal(d, i_tr, long_entry, short_entry, k=5,
                                                       buffer_pct=0.15, cap=6.0, floor=0.25)
                if stop_pct is None:
                    continue
                size_frac = size_frac_from_stop(stop_pct)
                tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                               stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
                cfg = f"Bollinger20/2.5 {name} [execution=TAKER, priority test]"
                vmult_val = None if name.startswith("bare") else float(name.split(">=")[1].split("x")[0])
                row = mk_row("5-volume-gated-breakout", cfg, tf, asset, tr, va,
                              stop_pct, None, size_frac, k=5,
                              extra={"n_events": n_events, "vmult": vmult_val,
                                     "trades_yr": trades_per_year(d, i_va, tr, va)})
                rows.append(row)
    return rows


# ===========================================================================
# FAMILY 6 — news/event momentum. Gold's analogue is scheduled macro
# (CPI/FOMC/NFP). Only NFP is tested, via a stated PUBLIC PROXY RULE (first
# Friday of the month, ~12:30 UTC) — CPI and FOMC are explicitly NOT
# tested (no verified economic-calendar dataset in this repo; a hand-
# recalled 26-year meeting calendar risks being confidently wrong, exactly
# what BLOFIN_API_REFERENCE.md's own lesson warns against). GC=F only —
# GLD's US-market-hours-only bars can't see a 12:30 UTC release directly.
# ===========================================================================

def family6_news_event_momentum():
    rows = []
    asset = "GC=F"
    tf = "1h"
    d = FRAMES[asset][tf]
    m = META[asset][tf]
    i_tr, i_va = m["i_tr"], m["i_va"]
    ts = pd.DatetimeIndex(d["timestamp"])
    is_release_bar = (ts.weekday == 4) & (ts.day <= 7) & (ts.hour == 12)   # first Friday, 12:00-13:00 UTC bar
    long_entry = pd.Series(is_release_bar & (d["close"] > d["open"]).to_numpy(), index=d.index)
    short_entry = pd.Series(is_release_bar & (d["close"] < d["open"]).to_numpy(), index=d.index)
    n_events = int(long_entry.sum() + short_entry.sum())
    if n_events == 0:
        return rows
    stop_pct = structural_stop_for_signal(d, i_tr, long_entry, short_entry, k=5,
                                           buffer_pct=0.15, cap=4.0, floor=0.2)
    if stop_pct is None:
        return rows
    for hold_h in (4, 8):
        mh_bars = hours_to_bars(d, hold_h)
        sig = day_trade_signal(d, long_entry, short_entry, mh_bars)
        target_pct = stop_pct * 2.5
        size_frac = size_frac_from_stop(stop_pct)
        tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                       stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
        cfg = f"NFP-proxy(1st-Fri~12:30UTC, UNVERIFIED CALENDAR) hold{hold_h}h"
        row = mk_row("6-news-event-momentum", cfg, tf, asset, tr, va,
                      stop_pct, target_pct, size_frac, k=5,
                      extra={"n_events": n_events, "hold_h": hold_h,
                             "trades_yr": trades_per_year(d, i_va, tr, va),
                             "caveat": "NFP proxy rule only; CPI/FOMC not tested (no verified calendar)"})
        rows.append(row)
    return rows


# ===========================================================================
# FAMILY 7 — liquidity sweep -> structure shift -> displacement (BTC: R86
# found this sample-starved, not disproven — gold's cleaner session
# structure may give it more sample)
# ===========================================================================
# sweep_mss_displacement imported verbatim from step86_specified.py (which
# itself composes step56's liquidity_pools/sweep_events/bos_chain, also
# imported verbatim here).

def family7_sweep_mss_displacement():
    rows = []
    for asset in ASSETS:
        for tf in ("1h", "4h"):
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            i_tr, i_va = m["i_tr"], m["i_va"]
            for k in K_OPTIONS:
                for disp_mult in (1.5, 2.0):
                    for max_wait in (10, 20):
                        (el, es, sref_l, sref_s,
                         tref_l, tref_s) = sweep_mss_displacement(d, k, 0.1, 0.3, disp_mult, max_wait)
                        mask = el | es
                        n_events = int(mask.sum())
                        if n_events == 0:
                            continue
                        stop_dist = pd.Series(np.nan, index=d.index)
                        stop_dist = stop_dist.mask(el, (d["close"] - sref_l).abs() / d["close"] * 100)
                        stop_dist = stop_dist.mask(es, (sref_s - d["close"]).abs() / d["close"] * 100)
                        stop_pct = train_median_stop_pct(d, i_tr, mask, stop_dist, cap=6.0, floor=0.25)
                        if stop_pct is None:
                            continue
                        target_pct = stop_pct * 2.5
                        mh_bars = hours_to_bars(d, max_wait + 120)
                        sig = day_trade_signal(d, el, es, mh_bars)
                        size_frac = size_frac_from_stop(stop_pct)
                        tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                                       stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
                        cfg = f"k{k} SWEEP-MSS-DISPLACEMENT disp{disp_mult}x wait{max_wait}"
                        row = mk_row("7-sweep-mss-displacement", cfg, tf, asset, tr, va,
                                      stop_pct, target_pct, size_frac, k=k,
                                      extra={"n_events": n_events, "disp_mult": disp_mult,
                                             "max_wait": max_wait,
                                             "trades_yr": trades_per_year(d, i_va, tr, va)})
                        rows.append(row)
    return rows


# ===========================================================================
# GOLD-NATIVE #8 — London/NY session as a FILTER on ported strategies
# (R55 found sessions are NOT a trigger, 0/6 — test as a filter instead,
# per the task)
# ===========================================================================

def donchian_ema_exit(d, entry_n, ema_n=20):
    hi = d["high"].rolling(entry_n).max().shift(1)
    enter = d["close"] > hi
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] < ema
    return _hysteresis(enter.fillna(False), exit_.fillna(False))


def hours_since_session_open(d, session_hour_utc):
    ts = pd.DatetimeIndex(d["timestamp"])
    hour = ts.hour + ts.minute / 60.0
    return pd.Series((hour - session_hour_utc) % 24, index=d.index)


def family8_session_filters():
    rows = []
    sessions = {"London(08:00 UTC)": 8.0, "NY(13:30 UTC)": 13.5}
    for asset in ASSETS:
        tf = "1h"
        d = FRAMES[asset][tf]
        m = META[asset][tf]
        i_tr, i_va = m["i_tr"], m["i_va"]
        adapt_med, _ = adaptive_vol_gate(d, direction="above")
        bases = {
            "donchian20+EMA20exit": donchian_ema_exit(d, 20),
            "volgated20/100-adaptive": vol_gated_ma(d, 20, 100, allow_short=False,
                                                      min_atr_pct=0.0, entry_filter=adapt_med),
        }
        for base_name, base_sig in bases.items():
            long_e, short_e = fresh_entries(base_sig)
            stop_pct = structural_stop_for_signal(d, i_tr, long_e, short_e, k=8, buffer_pct=0.15,
                                                   cap=8.0, floor=0.3)
            if stop_pct is None:
                continue
            size_frac = size_frac_from_stop(stop_pct)
            tr, va = score(d, base_sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                           stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
            rows.append(mk_row("8-session-filter", f"{base_name} UNFILTERED (baseline)", tf, asset,
                                tr, va, stop_pct, None, size_frac, k=8,
                                extra={"n_events": int(long_e.sum() + short_e.sum()),
                                       "trades_yr": trades_per_year(d, i_va, tr, va)}))
            for sess_name, sess_hour in sessions.items():
                for window_h in (2, 4):
                    cond = hours_since_session_open(d, sess_hour) < window_h
                    gated = gate_entry(base_sig, cond)
                    long_g, short_g = fresh_entries(gated)
                    n_events = int(long_g.sum() + short_g.sum())
                    if n_events == 0:
                        continue
                    tr, va = score(d, gated, COSTS_BY_ASSET[asset], i_tr, i_va,
                                   stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
                    cfg = f"{base_name} FILTERED to {sess_name} +{window_h}h"
                    rows.append(mk_row("8-session-filter", cfg, tf, asset, tr, va,
                                        stop_pct, None, size_frac, k=8,
                                        extra={"n_events": n_events,
                                               "trades_yr": trades_per_year(d, i_va, tr, va)}))
    return rows


# ===========================================================================
# GOLD-NATIVE #9 — the overnight gap itself as a tradeable event
# ===========================================================================

def family9_overnight_gap():
    rows = []
    for asset in ASSETS:
        tf = "1d"
        d = FRAMES[asset][tf]
        m = META[asset][tf]
        i_tr, i_va = m["i_tr"], m["i_va"]
        prev_close = d["close"].shift(1)
        gap_pct = (d["open"] - prev_close) / prev_close * 100
        for thresh in (0.3, 0.5):
            gap_up = (gap_pct > thresh).fillna(False)
            gap_down = (gap_pct < -thresh).fillna(False)
            for mode, el, es in (("FOLLOW", gap_up, gap_down), ("FADE", gap_down, gap_up)):
                n_events = int(el.sum() + es.sum())
                if n_events == 0:
                    continue
                stop_pct = structural_stop_for_signal(d, i_tr, el, es, k=5, buffer_pct=0.2,
                                                        cap=6.0, floor=0.3)
                if stop_pct is None:
                    continue
                target_pct = stop_pct * 2.5
                mh_bars = hours_to_bars(d, 24 * 5)
                sig = day_trade_signal(d, el, es, mh_bars)
                size_frac = size_frac_from_stop(stop_pct)
                tr, va = score(d, sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                               stop_pct=stop_pct, target_pct=target_pct, size_frac=size_frac)
                cfg = f"gap>{thresh}% {mode} hold5d"
                rows.append(mk_row("9-overnight-gap", cfg, tf, asset, tr, va,
                                    stop_pct, target_pct, size_frac, k=5,
                                    extra={"n_events": n_events, "thresh": thresh, "mode": mode,
                                           "trades_yr": trades_per_year(d, i_va, tr, va)}))
    return rows


# ===========================================================================
# GOLD-NATIVE #10 — DXY (dollar index) direction as a regime filter on the
# already-validated donchian20+EMA20exit breakout
# ===========================================================================

def family10_dxy_regime_filter():
    rows = []
    if DXY_1D is None:
        print("  DXY unavailable — Family 10 skipped honestly (no fake data substituted)")
        return rows
    dxy_trend = DXY_1D["close"] < DXY_1D["close"].rolling(100).mean()
    dxy_avail = pd.DataFrame({
        "timestamp": DXY_1D["timestamp"] + pd.Timedelta(days=1),   # no-lookahead: yesterday's DXY close only
        "weak": dxy_trend.fillna(False).to_numpy(),
    }).sort_values("timestamp")
    for asset in ASSETS:
        tf = "1d"
        d = FRAMES[asset][tf]
        m = META[asset][tf]
        i_tr, i_va = m["i_tr"], m["i_va"]
        merged = pd.merge_asof(d[["timestamp"]].sort_values("timestamp"), dxy_avail,
                                on="timestamp", direction="backward")
        dxy_weak_al = pd.Series(merged["weak"].fillna(False).to_numpy(), index=d.index)
        base_sig = donchian_ema_exit(d, 20)
        long_e, short_e = fresh_entries(base_sig)
        stop_pct = structural_stop_for_signal(d, i_tr, long_e, short_e, k=8, buffer_pct=0.15,
                                               cap=8.0, floor=0.3)
        if stop_pct is None:
            continue
        size_frac = size_frac_from_stop(stop_pct)
        tr, va = score(d, base_sig, COSTS_BY_ASSET[asset], i_tr, i_va,
                       stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
        rows.append(mk_row("10-dxy-regime-filter", "donchian20+EMA20exit UNFILTERED (baseline)", tf, asset,
                            tr, va, stop_pct, None, size_frac, k=8,
                            extra={"n_events": int(long_e.sum() + short_e.sum()),
                                   "trades_yr": trades_per_year(d, i_va, tr, va)}))
        gated = gate_entry(base_sig, dxy_weak_al)
        long_g, short_g = fresh_entries(gated)
        n_events = int(long_g.sum() + short_g.sum())
        if n_events > 0:
            tr, va = score(d, gated, COSTS_BY_ASSET[asset], i_tr, i_va,
                           stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
            rows.append(mk_row("10-dxy-regime-filter", "donchian20+EMA20exit FILTERED to DXY<100dSMA (dollar weak)",
                                tf, asset, tr, va, stop_pct, None, size_frac, k=8,
                                extra={"n_events": n_events,
                                       "trades_yr": trades_per_year(d, i_va, tr, va)}))
    return rows


# ===========================================================================
# XAUT-USDT compatibility check (bonus, not a validation — same convention
# as R55). Mechanically simple families only (4/5/8/10 baselines) where the
# exact signal is cheap to rebuild on the XAUT frame.
# ===========================================================================

def xaut_check_family4(gate_name, tf, stop_pct, size_frac):
    if tf != "1h":
        return None
    d = XAUT_1H
    adapt_med, _ = adaptive_vol_gate(d, direction="above")
    adapt_p75 = adaptive_vol_gate_pct(d, pct=75)
    gates = {
        "ungated": dict(min_atr_pct=0.0, entry_filter=None),
        "adaptive-median": dict(min_atr_pct=0.0, entry_filter=adapt_med),
        "adaptive-p75-STRICT": dict(min_atr_pct=0.0, entry_filter=adapt_p75),
    }
    matched = None
    for label, kw in gates.items():
        if label in gate_name:
            matched = kw
            break
    if matched is None and "fixed-median" in gate_name:
        matched = dict(min_atr_pct=float(META["GC=F"]["1h"]["med_atr"]), entry_filter=None)
    elif matched is None and "fixed-p75" in gate_name:
        matched = dict(min_atr_pct=float(META["GC=F"]["1h"]["p75_atr"]), entry_filter=None)
    if matched is None:
        return None
    sig = vol_gated_ma(d, fast=20, slow=100, allow_short=False, **matched)
    n = len(d)
    n_tr, n_va = int(n * 0.6), int(n * 0.8)
    tr, va = score(d, sig, BLOFIN_COSTS, n_tr, n_va, stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
    n_all = len(tr.trades) + len(va.trades)
    exp_all = ((tr.expectancy * len(tr.trades) + va.expectancy * len(va.trades)) / n_all) if n_all else float("nan")
    return n_all, exp_all


def xaut_check_family5(vmult, tf, stop_pct, size_frac):
    if tf != "1h":
        return None
    d = XAUT_1H
    base_sig = bollinger_breakout_signal(d)
    if vmult is not None:
        vol_avg20 = d["volume"].rolling(20).mean().shift(1)
        vol_ok = d["volume"] >= vmult * vol_avg20
        sig = gate_entry(base_sig, vol_ok)
    else:
        sig = base_sig
    n = len(d)
    n_tr, n_va = int(n * 0.6), int(n * 0.8)
    tr, va = score(d, sig, BLOFIN_COSTS, n_tr, n_va, stop_pct=stop_pct, target_pct=None, size_frac=size_frac)
    n_all = len(tr.trades) + len(va.trades)
    exp_all = ((tr.expectancy * len(tr.trades) + va.expectancy * len(va.trades)) / n_all) if n_all else float("nan")
    return n_all, exp_all


# ===========================================================================
# transfer matching (GC=F <-> GLD, same shape, different asset)
# ===========================================================================

import re


def shape_key(family, tf, config):
    cfg = re.sub(r"\([^)]*\)", "", str(config))
    cfg = re.sub(r"gold champ gate[^)]*", "", cfg)
    cfg = re.sub(r"\s+", " ", cfg).strip()
    return (family, tf, cfg)


def main():
    builders = [
        ("Family 1 — hidden RSI/MACD divergence, 4h continuation", family1_hidden_divergence),
        ("Family 2 — regular divergence + confirmation gate", family2_regular_divergence_confirmed),
        ("Family 3 — CHoCH + confluence>=2", family3_choch_confluence),
        ("Family 4 — vol-gated trend, strict gate", family4_vol_gated_trend_strict),
        ("Family 5 — volume-gated breakout (taker priority test)", family5_volume_gated_breakout),
        ("Family 6 — news/event momentum (NFP proxy only)", family6_news_event_momentum),
        ("Family 7 — liquidity sweep -> MSS -> displacement", family7_sweep_mss_displacement),
        ("Family 8 (gold-native) — session as FILTER", family8_session_filters),
        ("Family 9 (gold-native) — overnight gap event", family9_overnight_gap),
        ("Family 10 (gold-native) — DXY regime filter", family10_dxy_regime_filter),
    ]

    for label, fn in builders:
        print(f"\nRunning {label}...")
        rows = fn()
        print(f"  {len(rows)} configs")
        RESULTS.extend(rows)

    df = pd.DataFrame(RESULTS)
    df["positive_both"] = (df["tr_exp"] > 0) & (df["va_exp"] > 0)
    df["shape_key"] = df.apply(lambda r: shape_key(r["family"], r["tf"], r["config"]), axis=1)

    # cross-instrument transfer: does the SAME shape (family/tf/config, minus
    # asset-specific numbers) also show positive-both-windows on the OTHER asset?
    transfer_col = []
    for _, row in df.iterrows():
        other = "GLD" if row["asset"] == "GC=F" else "GC=F"
        match = df[(df["shape_key"] == row["shape_key"]) & (df["asset"] == other)]
        if len(match) == 0:
            transfer_col.append("no GLD/GC=F counterpart run")
        elif match["positive_both"].any():
            transfer_col.append("HOLDS")
        else:
            transfer_col.append("FAILS")
    df["gld_gcf_transfer"] = transfer_col

    print(f"\n{len(df)} total configs tested across 10 families.")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"].copy()
    insuff = df[df["verdict"] == "INSUFFICIENT-SAMPLE"].copy()
    print(f"\nSURVIVORS: {len(survivors)}")
    print(f"INSUFFICIENT-SAMPLE: {len(insuff)}")

    # thickness bar: reject edge_x_cost < 5
    if len(survivors):
        survivors["thickness_pass"] = survivors["edge_x_cost"] >= 5.0
        print("\n--- SURVIVOR table (thickness bar: edge_x_cost >= 5.0 to pass) ---")
        cols = ["family", "config", "tf", "asset", "tr_n", "tr_exp", "va_n", "va_exp",
                "stop_%price", "stop_%margin_at_20x", "size_frac_leverage",
                "edge_%notional_per_trade", "edge_x_cost", "thickness_pass",
                "trades_yr" if "trades_yr" in survivors.columns else "tr_n",
                "gld_gcf_transfer"]
        cols = [c for c in cols if c in survivors.columns]
        with pd.option_context("display.max_rows", None):
            print(survivors[cols].sort_values("edge_x_cost", ascending=False)
                  .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    # ---- leverage distribution (an OUTPUT, never hand-picked) ----
    lev = df["size_frac_leverage"].dropna()
    if len(lev):
        print(f"\nLeverage (size_frac) distribution across all {len(lev)} configs with a stop: "
              f"mean={lev.mean():.2f}x median={lev.median():.2f}x "
              f"p10={lev.quantile(0.1):.2f}x p90={lev.quantile(0.9):.2f}x "
              f"min={lev.min():.2f}x max={lev.max():.2f}x")

    # ---- XAUT-USDT compatibility check, thickness-passing SURVIVORs only,
    #      families 4/5/8/10 (mechanically simple to rebuild), 1h only ----
    print("\n--- XAUT-USDT compatibility check (whole-history read, NOT a validation) ---")
    xaut_rows = []
    if len(survivors):
        thick = survivors[survivors["thickness_pass"]]
        for _, row in thick.iterrows():
            if row["tf"] != "1h":
                continue
            res = None
            if row["family"] == "4-vol-gated-trend-strict":
                res = xaut_check_family4(row.get("gate_name", row["config"]), row["tf"],
                                          row["stop_%price"], row["size_frac_leverage"])
            elif row["family"] == "5-volume-gated-breakout":
                res = xaut_check_family5(row.get("vmult"), row["tf"],
                                          row["stop_%price"], row["size_frac_leverage"])
            if res is not None:
                n_all, exp_all = res
                xaut_rows.append({"family": row["family"], "config": row["config"],
                                   "asset": row["asset"], "xaut_n": n_all, "xaut_exp": exp_all,
                                   "xaut_holds": exp_all > 0})
                print(f"  [{row['asset']}] {row['config'][:70]:70s} -> XAUT n={n_all} "
                      f"exp=${exp_all:+.2f}/t {'HOLDS' if exp_all > 0 else 'fails'}")
    if not xaut_rows:
        print("  (no thickness-passing 1h survivor in families 4/5/8/10 to replay)")

    # ---- chance baseline: random-entry permutation on final survivors ----
    print("\n--- Chance baseline (25 random-entry shuffles per survivor, same n/stop/target/size) ---")
    chance_rows = []
    if len(survivors):
        top = survivors[survivors["thickness_pass"]].sort_values("edge_x_cost", ascending=False).head(15)
        for _, row in top.iterrows():
            asset, tf = row["asset"], row["tf"]
            d = FRAMES[asset][tf]
            m = META[asset][tf]
            n_events = row.get("n_events", row["tr_n"] + row["va_n"])
            n_long = int(round(n_events * 0.5))
            n_short = int(n_events) - n_long
            rate = chance_baseline(d, COSTS_BY_ASSET[asset], m["i_tr"], m["i_va"], n_long, n_short,
                                    row["stop_%price"], row["target_%price"], row["size_frac_leverage"],
                                    hold_h=96, trials=25)
            chance_rows.append({"family": row["family"], "config": row["config"], "asset": asset,
                                 "tf": tf, "chance_survivor_rate": rate})
            print(f"  [{asset} {tf}] {row['config'][:60]:60s} -> chance SURVIVOR rate "
                  f"{rate * 100:.0f}% ({int(rate * 25)}/25 random shuffles)")

    df.to_csv("step100_table.csv", index=False)
    print("\nWritten: step100_table.csv (chance-baseline numbers are in this stdout capture only, "
          "per the file-list restriction — folded into step100_results.md by hand)")

    return df, survivors, xaut_rows, chance_rows


if __name__ == "__main__":
    main()
