"""
step75_video.py — round 75: PB BLAKE's "NEW UPDATED 2026 STRATEGY" (4-step
SMC model: bias -> key level -> IFVG confirmation -> execution), formalized
+ gauntleted.

Run:  python3 step75_video.py

Research only — no commits, no live orders. Writes step75_video.py (this
file), step75_results.md, step75_gauntlet_full.csv. The ruleset distillation
with transcript quotes lives in step75_rules.md — read that FIRST; this
docstring only covers the FORMALIZATION (how the mechanical rules become
code) and the GAUNTLET discipline.

WHY THIS ROUND: standing instruction (established round 72, continued 73/
74) — any strategy video the owner sends gets ingested, distilled, and
gauntleted. This round's video teaches a 4-step SMC (smart-money-concepts)
day-trading funnel: (1) top-down bias from FVG respect/disrespect, (2) a
"key level" test (FVG / CISD / rejection block, optionally confirmed by SMT
cross-instrument divergence), (3) an inversion-FVG (IFVG) confirmation on
"the highest timeframe fair value gap inside the manipulation leg" (his own
precisely-stated rule, spanning 30 SECONDS to 5 minutes), (4) execution with
a 1:1-1:3 R:R target, a swing-based stop, a 1-2-trades/day cap, and a
9:30-11:00am ET session window. See step75_rules.md for full quotes.

REUSE / ATTRIBUTION (do not reimplement — imported UNMODIFIED unless noted)
- CostModel, run_backtest -> backtest.py.
- bar_hours, hours_to_bars, days_to_bars, split_points, confirmed_swings,
  last_n_confirmed -> step41_shorts.py.
- bos_chain (break-of-structure / persistent trend-chain state, used here
  as the round's MECHANICAL PROXY for his qualitative "FVG respect/
  disrespect" bias read — both are just "is the market making HH/HL or
  LH/LL," and this repo already has a clean, tested detector for that)
  -> step56_smc_toolkit.py.
- level_break_events, ifvg_events (his OWN IFVG definition — a 3-candle FVG
  that later gets a close back through its own near edge, opposite its
  formation bias — is EXACTLY round 72's ifvg_events, unmodified), in_window,
  resample_ohlc, day_trade_signal, merge_htf_series, stop_distance_pct,
  train_median_stop_pct, load_index_1h, load_index_15m_smoke, load_btc_eth,
  _fetch_yf -> step72_tjr.py, UNMODIFIED, imported. (day_trade_signal is
  EXTENDED here, not replaced — see day_trade_signal_capped below.)

FORMALIZATION — collapsing his 3-tier timeframe stack (biggest fidelity gap)
His full stack is genuinely THREE tiers: bias on daily/4h/1h (mostly 1h),
key level on 3m-4h, and IFVG confirmation on 30s-5m — even finer than round
72's TJR (5m/1m) or round 73's Gonzalez (15m/30m). No data source available
to this repo reaches 30-second or even reliable 1-minute resolution at
60/20/20 gauntlet depth for ANY instrument (yfinance caps sub-hourly index
history at ~60d; this repo's crypto caches bottom out at 5m). Rather than
force a fragile 3-tier build whose finest stage still couldn't reach his
actual 30s-1m examples, this round uses a **TWO-TIER** collapse: a BIAS
context tf (1h) feeding a single WORKING tf where the key-level test, SMT
divergence, and IFVG confirmation all live together — NQ/ES trade on 1h
directly (ctx==working, a 1-tier collapse, identical fidelity gap to round
72's index leg), BTC/ETH trade on 15m (ctx=1h merged down, working=15m, our
best proxy for his 3m-4h key-level tier; his finest 30s-5m IFVG tier is
NOT separately reachable at any deeper resolution this repo holds, so IFVG
confirmation is tested on the SAME 15m working tf as the key level, not a
separate finer entry tf). This keeps all four required-analysis ablations
(section below) on IDENTICAL bars per instrument, which a fragmented 3-tier
build would not — stated as the deliberate trade-off.

CONCEPT DEFINITIONS
- BIAS (step 1): bos_chain(d_ctx, k)["chain"] on the 1h context frame:
  +1 = persistent HH/HL uptrend, -1 = persistent LH/LL downtrend, 0 = none
  yet. Longs gated to chain==1, shorts to chain==-1. MECHANICAL PROXY for
  his FVG-respect/disrespect read (see REUSE above) — his own method has
  no numeric threshold, so this repo's existing trend-chain state is the
  closest already-mechanized equivalent, not a literal re-derivation.
- KEY LEVEL (step 2, all three sub-types COLLAPSED into one): rather than
  separately build FVG-zone / CISD-run-boundary / rejection-wick-zone
  detectors (each of which he himself describes with no numeric
  threshold — see step75_rules.md sec 1), this round tests a single
  universal "sweep of the nearest confirmed swing extreme" event:
  single_level_sweep() (NEW, this file) — a wick beyond the level by
  <=depth_pct that CLOSES back inside, same TEST SHAPE as step56_smc_
  toolkit.sweep_events (a wick-through-close-back liquidity raid), adapted
  to test a single confirmed-swing level instead of an equal-highs/lows
  POOL average, since none of his three key-level sub-types require two
  equal touches. Stated as this round's single biggest formalization
  simplification, exactly parallel to round 72's step-3+4 index collapse.
- SMT DIVERGENCE (step 2's named confluence factor, not a separate top-
  level step): "ES ended up sweeping it out... whereas the NASDAQ did
  not" — the traded instrument (self) shows relative STRENGTH (does NOT
  sweep its own level) while the PARTNER instrument DOES sweep its
  equivalent level, at the matching bar (merge_asof, direction=backward,
  same idiom as step72's partner_alignment but testing DISAGREEMENT, not
  agreement). smt_divergence() (NEW, this file): sweep_partner &
  ~sweep_self. DISCRETIONARY exact time/price "same test" tolerance in
  his own words — approximated here as same-bar (post merge_asof) on a
  shared UTC clock, since NQ/ES and BTC/ETH both trade continuously on
  the same exchange session.
- IFVG CONFIRMATION (step 3): ifvg_events() (step72, UNMODIFIED) on the
  SAME working tf as the key-level/SMT test (see collapse note above) —
  exactly his own definition (a 3-candle FVG that gets a close back
  through its own near edge, opposite its formation bias). His "highest
  timeframe in the manipulation leg" selection logic (scanning 30s-5m for
  the single highest tf with a gap) is NOT separately implemented — at a
  single working tf there is only one timeframe to check, so the
  selection question doesn't arise; this is the direct consequence of the
  two-tier collapse above, stated plainly, not hidden.
- ARMED WINDOW: bias & smt-divergence-confirmed-sweep, rolled forward over
  W1_STRUCT_BARS bars (causal rolling-max, identical idiom to step72's
  armed_short/armed_long), so the IFVG confirmation has a bounded recency
  window in which to appear, not an unbounded one.
- ENTRY: armed_bull & ifvg_bull -> long; armed_bear & ifvg_bear -> short.
  Entry at the IFVG's own close, exactly his stated default ("typically
  just entering on the body closure of the IFG") — his DISCRETIONARY
  limit-order fallback (used "if my risk reward is trash") is not
  separately modeled; every entry here is his stated default (taker,
  market-style) execution.
- STOP: nearest confirmed swing extreme (same k, working tf) opposite the
  trade direction -> TRAIN-only median % distance, held fixed across
  train/val/test — stop_distance_pct + train_median_stop_pct, imported
  UNMODIFIED from step72_tjr, exactly his own stated majority-case default
  ("usually at the swing low").
- TARGET: R-multiple x stop_pct, swept in {1.0, 1.5, 2.0, 3.0} — his own
  stated "1:1 RR to 1:3 RR" neighborhood, with 3.0 as headroom for his
  noted high-conviction extension case.
- MAX TRADES/DAY: his rule is OUTCOME-CONDITIONAL ("one win, done; one
  loss, probably done; two losses, done") — this requires knowing a
  trade's realized P&L before generating the NEXT bar's signal, which
  would mean running the backtest engine INSIDE signal generation,
  circular with this repo's clean signal-then-score architecture (every
  prior round's same discipline). APPROXIMATED as a flat hard cap of 2
  entries per UTC calendar day (day_trade_signal_capped, NEW this file,
  extends step72's day_trade_signal with a per-day entry counter) — the
  tightest literal reading of his own numbers, swept ON/OFF as the
  round's outcome-conditional-rule sensitivity check.
- SESSION WINDOW: TIGHT = [13:30,15:30) UTC (9:30-11:00am ET, his stated
  "golden hour"), EXTENDED = [13:30,16:30) UTC (9:30-12:00pm ET, covering
  his stated rare extension). Swept, same idiom as round 72's TJR ~10:30
  soft-cutoff sensitivity check.
- MAX HOLD: fixed 4.0h, NOT swept — carried forward from round 72's TJR
  index/day-trade convention (same instrument family, same day-trading
  cadence); he gives no max-hold rule himself, exactly like every prior
  round's identical gap.

ENGINE / GAUNTLET DISCIPLINE (read backtest.py for ground truth)
- run_backtest: one fixed stop_pct/target_pct per run, bar-close-N ->
  fill-at-N+1-open, no lookahead. No cost-free mode.
- Costs: INDEX (NQ=F, ES=F) = step72's FUT_COSTS (0.5bps fee + 0.5bps
  slippage) -> 2bps taker RT. BTC/ETH = step72's BTC_COSTS (6bps fee/2bps
  maker + 1bps/8h funding) -> 12bps taker RT + real funding via
  align_funding (step11_round6, unmodified), fetched per-symbol
  (BTCUSDT and ETHUSDT both have cached funding histories in this repo).
- GAUNTLET: chronological 60/20/20 per dataset (split_points, step41,
  unmodified). Select by TRAIN expectancy>0 (>=30 trades) AND POSITIVE VAL
  (>=8 trades) = SURVIVOR. The sealed 20% test slice is NEVER touched by
  this script — score() only ever computes [0:i_tr] and [i_tr:i_va].
- GRID: STAGE 1 (literal-config sensitivity sweep, his own ambiguous-
  parameter neighborhood only) = depth_pct{0.15,0.35} x session{tight,ext}
  x smt_filter{on,off} x trades_cap{on,off} x R{1.0,1.5,2.0,3.0} = 64
  configs/instrument, at k=3 fixed (not swept — he never discusses swing-
  fractal width at all, unlike round 73's Gonzalez who at least gestured
  at it qualitatively; sweeping k too would push total configs well past
  this repo's established ~100-300/round band without reading on a
  genuinely-stated ambiguity). STAGE 2 (component ablation, required
  analysis) = 4 ablations (no_bias, no_smt, no_sweep/no_key_level,
  no_ifvg) x R{1.0,1.5,2.0,3.0} = 16 configs/instrument, at the STAGE 1
  representative point (depth=0.35, session=tight, smt=on, cap=on).
  80 configs/instrument x 4 instruments (NQ, ES, BTC, ETH) = 320 total,
  plus a 15m/60d index SMOKE check (NOT gauntleted, no train/val claims,
  same idiom as round 72).
"""

import warnings

import numpy as np
import pandas as pd

import config  # noqa: F401 — imported for parity with every other step*.py
from backtest import CostModel, run_backtest
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import (
    bar_hours,
    confirmed_swings,
    hours_to_bars,
    split_points,
)
from step56_smc_toolkit import bos_chain
from step72_tjr import (
    day_trade_signal,
    ifvg_events,
    in_window,
    load_btc_eth,
    load_index_15m_smoke,
    load_index_1h,
    merge_htf_series,
    stop_distance_pct,
    train_median_stop_pct,
)

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 6.0
STOP_FLOOR_PCT = 0.15

FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                       slippage_bps=0.5, funding_bps_8h=0.0)          # 2bps RT
BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)          # 12bps RT + funding

TICKER = {"NQ": "NQ=F", "ES": "ES=F"}
PARTNER_INDEX = {"NQ": "ES", "ES": "NQ"}
PARTNER_CRYPTO = {"BTC": "ETH", "ETH": "BTC"}
FUNDING_SYMBOL = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}

ENTRY_TIGHT = (13.5, 15.5)     # 9:30-11:00 ET, his "golden hour"
ENTRY_EXT = (13.5, 16.5)       # 9:30-12:00 ET, his stated rare extension

MAX_HOLD_HOURS = 4.0
W1_STRUCT_BARS = 48
K_FIXED = 3
DEPTH_LIST = (0.15, 0.35)
R_LIST = (1.0, 1.5, 2.0, 3.0)
MAX_TRADES_PER_DAY = 2
REP_DEPTH = 0.35   # ablation stage's fixed representative point


# ---------------------------------------------------------------------------
# NEW for round 75 — key level (sweep), SMT divergence, day-cap signal
# ---------------------------------------------------------------------------

def single_level_sweep(d, level_high, level_low, depth_pct):
    """Sweep = wick beyond `level` by <= depth_pct but CLOSE BACK inside —
    same wick-through-close-back TEST as step56_smc_toolkit.sweep_events,
    adapted here to a single confirmed-swing level (not an equal-highs/
    lows POOL average) since none of PB Blake's three key-level sub-types
    (FVG / CISD / rejection block, step75_rules.md sec 1) require two
    equal touches. See module docstring's KEY LEVEL note."""
    high, low, close = d["high"], d["low"], d["close"]
    sweep_short = (level_high.notna() & (high > level_high) &
                   (high <= level_high * (1 + depth_pct / 100)) &
                   (close < level_high))
    sweep_long = (level_low.notna() & (low < level_low) &
                  (low >= level_low * (1 - depth_pct / 100)) &
                  (close > level_low))
    return sweep_long.fillna(False), sweep_short.fillna(False)


def align_partner_series(ts_self, ts_partner, series_partner):
    """Merge a partner instrument's boolean series onto self's timestamps,
    same merge_asof idiom as step72_tjr.partner_alignment."""
    merged = pd.merge_asof(
        pd.DataFrame({"timestamp": ts_self}).sort_values("timestamp"),
        pd.DataFrame({"timestamp": ts_partner, "v": series_partner.to_numpy()}).sort_values("timestamp"),
        on="timestamp", direction="backward")
    return merged["v"].reset_index(drop=True)


def smt_divergence(sweep_self, sweep_partner_aligned):
    """SELF shows relative strength (does NOT sweep its own level) while
    PARTNER sweeps its equivalent level -> divergence confirms self's
    reversal. See module docstring's SMT DIVERGENCE note."""
    return sweep_partner_aligned.fillna(False) & ~sweep_self.fillna(False)


def day_trade_signal_capped(d, enter_long, enter_short, max_hold_bars, max_trades_per_day=None):
    """EXTENDS step72_tjr.day_trade_signal's state machine (imported
    unmodified elsewhere in this file for the smoke check) with an
    optional per-UTC-calendar-day entry-count cap — the flat-cap
    APPROXIMATION of his outcome-conditional 'one win done, two losses
    done' rule, see module docstring's MAX TRADES/DAY note. Every entry
    (long or short) counts toward the same day's cap, per his own words
    ('done for the day' regardless of direction)."""
    day_key = d["timestamp"].dt.floor("D").to_numpy()
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    cur_day, day_count = None, 0
    for i in range(len(d)):
        if day_key[i] != cur_day:
            cur_day, day_count = day_key[i], 0
        if pos == 0.0:
            capped = (max_trades_per_day is not None) and (day_count >= max_trades_per_day)
            if not capped:
                if el[i]:
                    pos, held = 1.0, 0
                    day_count += 1
                elif es[i]:
                    pos, held = -1.0, 0
                    day_count += 1
        else:
            held += 1
            if max_hold_bars and held >= max_hold_bars:
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ---------------------------------------------------------------------------
# core signal construction — bias -> key level/SMT -> IFVG confirm
# ---------------------------------------------------------------------------

def build_working_signals(d_work, d_partner_work, k, depth_pct, bias_bull_work, bias_bear_work,
                           mode="full"):
    """mode in {full, no_bias, no_smt, no_sweep, no_ifvg} — the STAGE-1
    literal build (mode='full') and STAGE-2 component ablations (all
    others), computed on the SAME working tf so every ablation is exactly
    comparable bar-for-bar. Returns (entry_long, entry_short)."""
    sh, sl = confirmed_swings(d_work, k)
    lsh, lsl = sh.ffill(), sl.ffill()
    sweep_long_self, sweep_short_self = single_level_sweep(d_work, lsh, lsl, depth_pct)

    sh_p, sl_p = confirmed_swings(d_partner_work, k)
    lsh_p, lsl_p = sh_p.ffill(), sl_p.ffill()
    sweep_long_p, sweep_short_p = single_level_sweep(d_partner_work, lsh_p, lsl_p, depth_pct)
    sweep_long_p_aligned = align_partner_series(d_work["timestamp"], d_partner_work["timestamp"], sweep_long_p)
    sweep_short_p_aligned = align_partner_series(d_work["timestamp"], d_partner_work["timestamp"], sweep_short_p)

    smt_bull = smt_divergence(sweep_long_self, sweep_long_p_aligned)
    smt_bear = smt_divergence(sweep_short_self, sweep_short_p_aligned)

    ifvg_bull, ifvg_bear = ifvg_events(d_work)

    if mode == "no_bias":
        bias_bull_g = pd.Series(True, index=d_work.index)
        bias_bear_g = pd.Series(True, index=d_work.index)
    else:
        bias_bull_g, bias_bear_g = bias_bull_work, bias_bear_work

    if mode == "no_smt":
        key_bull, key_bear = (sweep_long_self | sweep_long_p_aligned.fillna(False)), \
                              (sweep_short_self | sweep_short_p_aligned.fillna(False))
    elif mode == "no_sweep":
        key_bull = pd.Series(True, index=d_work.index)
        key_bear = pd.Series(True, index=d_work.index)
    else:
        key_bull, key_bear = smt_bull, smt_bear

    armed_bull = (bias_bull_g.astype(bool) & key_bull.astype(bool)).rolling(
        W1_STRUCT_BARS, min_periods=1).max().astype(bool)
    armed_bear = (bias_bear_g.astype(bool) & key_bear.astype(bool)).rolling(
        W1_STRUCT_BARS, min_periods=1).max().astype(bool)

    if mode == "no_ifvg":
        raw_bull = (bias_bull_g.astype(bool) & key_bull.astype(bool))
        raw_bear = (bias_bear_g.astype(bool) & key_bear.astype(bool))
        entry_long = raw_bull & ~raw_bull.shift(1, fill_value=False)
        entry_short = raw_bear & ~raw_bear.shift(1, fill_value=False)
    else:
        entry_long = armed_bull & ifvg_bull
        entry_short = armed_bear & ifvg_bear

    return entry_long.fillna(False), entry_short.fillna(False)


def apply_filters(d, entry_long, entry_short, window):
    win_mask = in_window(d, *window)
    return (entry_long & win_mask).fillna(False), (entry_short & win_mask).fillna(False)


# ---------------------------------------------------------------------------
# gauntlet plumbing (adapted from step72_tjr's score/verdict/mk_row)
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None, funding=None):
    def run(lo, hi):
        kw = dict(costs=costs, execution="taker", stop_pct=stop_pct, target_pct=target_pct)
        if funding is not None:
            kw["funding_series"] = funding.iloc[lo:hi].reset_index(drop=True)
        return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                             sig.iloc[lo:hi].reset_index(drop=True), **kw)
    return run(0, i_tr), run(i_tr, i_va)


def verdict_for(tr, va):
    tr_n, va_n = len(tr.trades), len(va.trades)
    if tr.expectancy > 0 and va.expectancy > 0 and tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
        return "SURVIVOR"
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        return "INSUFFICIENT-SAMPLE"
    return "FAIL"


def rr_stats(tr, va):
    trades = list(tr.trades) + list(va.trades)
    if not trades:
        return float("nan"), float("nan"), float("nan"), float("nan")
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl <= 0]
    win_rate = len(wins) / len(trades) * 100
    avg_win = float(np.mean(wins)) if wins else float("nan")
    avg_loss = float(np.mean(losses)) if losses else float("nan")
    rr = abs(avg_win / avg_loss) if losses and avg_loss != 0 else float("nan")
    return win_rate, avg_win, avg_loss, rr


def trades_per_day(d, tr, va, i_va):
    n_trades = len(tr.trades) + len(va.trades)
    span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return n_trades / span_days if span_days > 0 else float("nan")


def mk_row(dataset, cfg, tr, va, stop_pct, target_pct, d, i_va):
    win_rate, avg_win, avg_loss, rr = rr_stats(tr, va)
    return {
        "dataset": dataset, "config": cfg,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "pooled_win%": win_rate, "pooled_RR": rr,
        "tr/day": trades_per_day(d, tr, va, i_va),
        "verdict": verdict_for(tr, va),
    }


def no_entries_row(dataset, cfg):
    return {"dataset": dataset, "config": cfg, "stop%": None, "target%": None,
            "tr_n": 0, "tr_exp": np.nan, "tr_win%": np.nan, "tr_ret%": np.nan, "tr_dd%": np.nan,
            "va_n": 0, "va_exp": np.nan, "va_win%": np.nan, "va_ret%": np.nan, "va_dd%": np.nan,
            "pooled_win%": np.nan, "pooled_RR": np.nan, "tr/day": np.nan, "verdict": "NO-ENTRIES"}


def run_one_config(d, i_tr, i_va, k, el, es, costs, dataset, cfg_prefix, r_list, funding=None,
                    max_trades_cap=True):
    rows = []
    entry_mask = (el | es)
    dist_long, dist_short = stop_distance_pct(d, k, el, es)
    dist_combined = dist_long.where(el.to_numpy(), dist_short)
    stop_pct = train_median_stop_pct(entry_mask, dist_combined, i_tr)
    if stop_pct is None:
        rows.append(no_entries_row(dataset, f"{cfg_prefix} R=*"))
        return rows
    mh_bars = hours_to_bars(d, MAX_HOLD_HOURS)
    cap = MAX_TRADES_PER_DAY if max_trades_cap else None
    for rmult in r_list:
        target_pct = round(stop_pct * rmult, 4)
        sig = day_trade_signal_capped(d, el, es, mh_bars, max_trades_per_day=cap)
        tr, va = score(d, sig, costs, i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct, funding=funding)
        cfg = f"{cfg_prefix} R={rmult:.1f}"
        rows.append(mk_row(dataset, cfg, tr, va, stop_pct, target_pct, d, i_va))
    return rows


# ---------------------------------------------------------------------------
# per-instrument gauntlet
# ---------------------------------------------------------------------------

def gauntlet_instrument(tag, d_work, d_ctx, d_partner_work, costs, funding=None, k=K_FIXED,
                         same_frame_ctx=False):
    """d_ctx MUST be 1h bars (bias source). If same_frame_ctx, d_work IS
    d_ctx (index legs, 1-tier collapse); otherwise d_ctx is merged down
    onto d_work's timestamps (crypto legs, 1h ctx -> 15m working)."""
    rows = []
    n, i_tr, i_va = split_points(d_work)
    print(f"  {tag}: n={n} bars, train=[0:{i_tr}], val=[{i_tr}:{i_va}], "
          f"test sealed=[{i_va}:{n}] (never touched)")

    chain_ctx = bos_chain(d_ctx, k)["chain"]
    bias_bull_ctx = (chain_ctx == 1)
    bias_bear_ctx = (chain_ctx == -1)
    if same_frame_ctx:
        bias_bull_work = bias_bull_ctx.reset_index(drop=True)
        bias_bear_work = bias_bear_ctx.reset_index(drop=True)
    else:
        bias_bull_work = merge_htf_series(d_work["timestamp"], d_ctx["timestamp"],
                                           bias_bull_ctx.astype(float), 1.0) > 0
        bias_bear_work = merge_htf_series(d_work["timestamp"], d_ctx["timestamp"],
                                           bias_bear_ctx.astype(float), 1.0) > 0

    # ---------------- STAGE 1: literal config, sensitivity sweep ----------------
    for depth_pct in DEPTH_LIST:
        el_full, es_full = build_working_signals(d_work, d_partner_work, k, depth_pct,
                                                   bias_bull_work, bias_bear_work, mode="full")
        el_no_smt, es_no_smt = build_working_signals(d_work, d_partner_work, k, depth_pct,
                                                       bias_bull_work, bias_bear_work, mode="no_smt")
        for window_name, window in (("tight9:30-11:00ET", ENTRY_TIGHT), ("ext9:30-12:00ET", ENTRY_EXT)):
            for smt_name, (el_raw, es_raw) in (("smt=ON", (el_full, es_full)), ("smt=OFF", (el_no_smt, es_no_smt))):
                el, es = apply_filters(d_work, el_raw, es_raw, window)
                for cap_name, cap_on in (("cap=ON", True), ("cap=OFF", False)):
                    cfg_prefix = f"main depth={depth_pct} {window_name} {smt_name} {cap_name}"
                    rows.extend(run_one_config(d_work, i_tr, i_va, k, el, es, costs, tag, cfg_prefix,
                                                R_LIST, funding=funding, max_trades_cap=cap_on))

    # ---------------- STAGE 2: component ablations (fixed rep point) ----------------
    for ablation, mode in (("ablation(a)-no_bias", "no_bias"),
                            ("ablation(b)-no_smt", "no_smt"),
                            ("ablation(c)-no_sweep(no_key_level)", "no_sweep"),
                            ("ablation(d)-no_ifvg", "no_ifvg")):
        el_raw, es_raw = build_working_signals(d_work, d_partner_work, k, REP_DEPTH,
                                                bias_bull_work, bias_bear_work, mode=mode)
        el, es = apply_filters(d_work, el_raw, es_raw, ENTRY_TIGHT)
        cfg_prefix = f"{ablation} depth={REP_DEPTH} tight smt=ON cap=ON"
        rows.extend(run_one_config(d_work, i_tr, i_va, k, el, es, costs, tag, cfg_prefix,
                                    R_LIST, funding=funding, max_trades_cap=True))

    # baseline row for ablation comparison (full stack, same rep point) is
    # already present in stage 1's "depth=0.35 tight smt=ON cap=ON" rows —
    # not duplicated here, cross-referenced in step75_results.md instead.
    return rows


# ---------------------------------------------------------------------------
# smoke check (index, 15m, 60d — NOT gauntleted, no train/val claims)
# ---------------------------------------------------------------------------

def smoke_index_15m(tag, d15, d_partner15, k=K_FIXED, depth_pct=REP_DEPTH):
    if len(d15) < 300 or len(d_partner15) < 300:
        return {"dataset": tag, "note": "too few 15m/60d bars for even a smoke read", "n": len(d15)}
    chain15 = bos_chain(d15, k)["chain"]
    bias_bull = (chain15 == 1).reset_index(drop=True)
    bias_bear = (chain15 == -1).reset_index(drop=True)
    el_raw, es_raw = build_working_signals(d15, d_partner15, k, depth_pct, bias_bull, bias_bear, mode="full")
    win_mask = in_window(d15, *ENTRY_EXT)
    el = (el_raw & win_mask).fillna(False)
    es = (es_raw & win_mask).fillna(False)
    n_days = (d15["timestamp"].iloc[-1] - d15["timestamp"].iloc[0]).total_seconds() / 86400
    return {"dataset": tag, "bars": len(d15), "days": round(n_days, 1),
            "raw_long_events": int(el_raw.sum()), "raw_short_events": int(es_raw.sum()),
            "windowed_long": int(el.sum()), "windowed_short": int(es.sum()),
            "note": "SMOKE ONLY: 60d 15m sample (his real IFVG tf, one tier finer than the "
                    "gauntleted 1h index leg), sanity check for the 1h collapse, NOT gauntleted, "
                    "no train/val split, no expectancy claim"}


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("ROUND 75 — PB BLAKE's 4-STEP SMC MODEL: distill, formalize, gauntlet")
    print("=" * 90)

    print("\n--- loading index data (NQ=F, ES=F, 1h, 730d, cached from round 72) ---")
    index_frames = {tag: load_index_1h(tag) for tag in ("NQ", "ES")}

    print("\n--- loading index 15m/60d smoke data (cached from round 72) ---")
    index_smoke = {tag: load_index_15m_smoke(tag) for tag in ("NQ", "ES")}

    print("\n--- loading BTC/ETH deep cache (1h/15m/5m, cached from round 72) ---")
    crypto_frames = load_btc_eth()

    all_rows = []

    print("\n--- INDEX gauntlet (1h, 1-tier collapse — bias==working frame, 730d) ---")
    for tag in ("NQ", "ES"):
        d = index_frames[tag]
        d_partner = index_frames[PARTNER_INDEX[tag]]
        rows = gauntlet_instrument(tag, d, d, d_partner, FUT_COSTS, funding=None, same_frame_ctx=True)
        all_rows.extend(rows)

    print("\n--- BTC/ETH gauntlet (15m working tf, 1h bias merged down, deep cache) ---")
    for tag in ("BTC", "ETH"):
        d_work = crypto_frames[tag]["15m"]
        d_ctx = crypto_frames[tag]["1h"]
        d_partner_work = crypto_frames[PARTNER_CRYPTO[tag]]["15m"]
        funding = align_funding(d_work, fetch_funding_history(FUNDING_SYMBOL[tag]))
        rows = gauntlet_instrument(tag, d_work, d_ctx, d_partner_work, BTC_COSTS,
                                    funding=funding, same_frame_ctx=False)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df.to_csv("step75_gauntlet_full.csv", index=False)
    print(f"\nTotal configs run: {len(df)}")

    survivors = df[df["verdict"] == "SURVIVOR"].sort_values("va_exp", ascending=False)
    print("\n--- SURVIVORS (train+val positive, floors met — sealed test NOT touched) ---")
    print(survivors.to_string(index=False) if len(survivors) else "  none")

    print("\n--- verdict counts overall ---")
    print(df["verdict"].value_counts().to_string())

    print("\n--- verdict counts per instrument ---")
    print(df.groupby(["dataset", "verdict"]).size().to_string())

    print("\n--- INDEX 15m/60d SMOKE (NOT gauntleted) ---")
    smoke_rows = []
    smoke_rows.append(smoke_index_15m("NQ", index_smoke["NQ"], index_smoke["ES"]))
    smoke_rows.append(smoke_index_15m("ES", index_smoke["ES"], index_smoke["NQ"]))
    for r in smoke_rows:
        print(" ", r)

    print("\n--- component ablation table (fixed rep point: depth=0.35, tight window, cap=ON, per instrument) ---")
    abl = df[df["config"].str.startswith("ablation") | (
        (df["config"].str.startswith("main depth=0.35 tight9:30-11:00ET smt=ON cap=ON")))]
    print(abl[["dataset", "config", "tr_n", "tr_exp", "va_n", "va_exp", "pooled_win%", "pooled_RR", "verdict"]]
          .to_string(index=False) if len(abl) else "  none")

    print("\nDone. See step75_results.md for the full writeup.")
    return df, survivors, smoke_rows


if __name__ == "__main__":
    main()
