"""
step73_video.py — round 73: ALEX GONZALEZ / fxalexg "10+ HOUR COURSE"
market-structure / break-and-retest strategy, formalized + gauntleted.

Run:  python3 step73_video.py

Research only — no commits, no live orders. Writes step73_video.py (this
file), step73_results.md, step73_gauntlet_full.csv. The ruleset
distillation with transcript quotes lives in step73_rules.md — read that
FIRST; this docstring only covers the FORMALIZATION (how the mechanical
rules become code) and the GAUNTLET discipline.

WHY THIS ROUND: the owner's standing instruction is that any strategy
video gets ingested, distilled, and gauntleted (established in round 72
with TJR's 2026 ES/NQ playbook). Round 73's video is a full 10.6-hour
"zero to 100%" course by Alex Gonzalez ("fxalexg," Swing Trading Lab
LLC), NOT a single-strategy reveal — but underneath the platform
tutorials and backstory, it teaches one consistent mechanical core: a
market-structure break-and-retest system, applied to BOTH "reversal" and
"trend continuation" setups with the same trigger. His stated markets
are "Forex, indices, commodities, and cryptocurrencies," but every real
trade shown on screen is a FOREX pair — this round tests his stated
system on his ACTUAL traded instrument family (USDJPY, GBPCHF) plus
transfer tests on EURUSD (forex proxy), gold (commodity), an index
future, and BTC (crypto) — his three claimed-but-never-demonstrated
market families.

FORMALIZATION — the two-tier collapse (the single biggest fidelity gap)
His full stack is 4-6 timeframes: weekly/daily/4H for trend + area-of-
interest (AOI), then 1H/30min/15min for the actual entry-confirmation
candle (his own words: "weekly, the daily and the 4 hour... used to
identify trend and area of interest," then "lower time frames as entry
signal confirmations" — worked live examples cite 30m/15m confirmation
candles specifically). This script tests a TWO-TIER approximation:
DAILY context (trend + the broken structure level, standing in for his
weekly+daily AOI stage — deep daily history exists for every dataset
here) -> 4H entry (retest + candlestick confirmation, standing in for
his 4H/1H/30m/15m confirmation stack). This is a coarser proxy than his
full cascade in the same spirit as round 72's index collapse — stated
loudly, not hidden. yfinance's ~60d cap on sub-hourly bars (identical
constraint to round 72) makes an honest 60/20/20 gauntlet at 30m/15m
resolution impossible for the forex/gold/index legs; only BTC has a deep
sub-hourly cache, and even there his own real trades never touched BTC.

CONCEPT DEFINITIONS
- BODY-ONLY STRUCTURE: he repeats, explicitly and often, "do not take the
  wicks into account" — market structure (HH/HL/LH/LL) and its breaks
  are built from candle BODIES only, not high/low wicks. Formalized by
  feeding confirmed_swings()/bos_chain() (step41/step56, UNMODIFIED) a
  body-substituted frame: high -> max(open,close), low -> min(open,close).
  The break condition itself (a body CLOSE beyond the prior confirmed
  swing) is already exactly his rule in bos_chain()'s unmodified form
  (it compares raw `close`, which is a true body edge) — only the SWING-
  POINT locator needed the body substitution.
- SWING/STRUCTURE POINTS ("snake trick"): confirmed_swings(d_body, k), a
  k-bar fractal on body extremes — a STATED APPROXIMATION of his
  admittedly non-numeric "sharp, clean turn" identification (his own
  words: "there's never going to be like a proper black or white
  textbook"). k=3 throughout, not swept (kept fixed like round 72/56).
- BOS-CONTINUATION vs CHoCH (his "trend continuation" vs "reversal"
  chapters): imported unmodified from step56_smc_toolkit.bos_chain — a
  body-close break of structure IN the prevailing chain direction
  (cont_long/cont_short) vs. the FIRST break AGAINST it (choch_long/
  choch_short). His own two chapters describe the SAME break-retest-
  confirm mechanism for both cases, differing only in which side of this
  split the break lands on — confirmed directly by his own worked live
  example, which waits for the identical sequence whether fading a top
  or riding a pullback ("I want the market to show me its hand first").
  Swept as MODE in {reversal-only (choch), continuation-only (cont),
  both (any bos_up/bos_down)} — the round's test of whether his two
  named setups behave differently in practice.
- AREA OF INTEREST (AOI): his stated construction (>=3 body-touches,
  5-60 pip zone, weekly/daily only) is NOT separately built here. His
  own touch-counting is already admittedly discretionary in practice
  ("I would not count that one because the candlestick isn't that
  clean") — this script instead anchors the "retest" directly to the
  broken structure level itself (bos_chain's own lsh/lsl at the moment
  of the break), which is where his break-and-retest sequence always
  ends up operating anyway. Stated simplification: skips the separate
  multi-touch zone-building stage, keeps the mechanical part he actually
  trades off (the level, and the retest of it).
- RETEST: after a daily break event becomes available on the 4H entry
  frame (merge_event_recency_with_value, this file — round 72's
  merge_event_recency idiom, extended to also carry the frozen broken-
  level VALUE forward through the armed window, not just an availability
  flag), price must close within TOL_PCT=0.35% of that frozen level
  (a stated, cross-instrument-portable approximation of his pip-based
  "20-35 pip sweet spot" AOI width — pips don't translate across
  BTC/gold/index/forex, so this is expressed as a %). W1_ARMED_BARS=36
  (4H bars, ~6 trading days) bounds how long a break stays "live"
  waiting for its retest.
- CANDLESTICK CONFIRMATION: engulf2_events() (this file, NEW) — his own,
  stricter-than-textbook engulfing rule: "needs to engulf the last
  candlestick and then the previous one minimum." A confirmation candle
  is bullish/bearish if its body range (open/close extremes) fully
  contains BOTH of the prior two candles' body ranges, direction set by
  its own close-vs-open. His separately named "morning star"/"evening
  star" pattern (a small indecision candle immediately followed by an
  engulfing candle that eats the prior two bodies) REDUCES numerically
  to this identical test — the small candle is simply one of the two
  bodies being engulfed. Formalizing both his named patterns as ONE
  function avoids inventing an arbitrary doji/small-body size ratio he
  never gives a number for (an UNSPECIFIED parameter, not guessed).
- ENTRY STYLE (the discretionary-gap sensitivity check, this round's
  analogue of round 72's alignment on/off test): "breakout" = enter on
  the first 4H bar the daily break becomes available, no retest wait
  (his own stated ~30%-of-the-time behavior). "retest" = his STATED
  preference — wait for the retest touch, then an engulf2 confirmation
  candle, before entering (retest_confirm_entries(), this file).
- STOP: nearest confirmed body-swing extreme (4H, k=3) opposite the
  trade direction at entry -> TRAIN-only median % distance, held fixed
  across train/val/test (this repo's established per-trade-dynamic-
  distance approximation since round 17/41/43/56/72). Capped
  [0.15%, 6.0%]. His only numeric worked example ("10 to 15 pips above
  this wick... 20 23 pips") supports a tight-stop system; no general
  formula is ever given, so the repo's standard approximation is used
  as-is, not force-fit to his one example.
- TARGET: R-multiple x stop_pct, swept over {1.0, 2.0, 4.0} — bracketing
  his own two explicitly stated anchors, "a minimum of a one to two
  risk-to-reward" (R=2.0) and "always aim for the trade to have a
  potential of a one to 4" (R=4.0), plus R=1.0 as a conservative floor.
  His realized live examples range far wider (1:2.7, 1:3.4, 1:5, one
  outlier at 1:11) but holding past his own stated floor/potential pair
  is explicitly framed as a live, subjective, unruled decision — not
  mechanized here as a trailing/scaling exit, exactly like his own
  description of it.
- MAX HOLD: fixed 240h (10 trading days), not swept. His own real
  trades (a swing/day-trade hybrid, weekly/daily-anchored) run for many
  days to weeks in the worked live examples (the 1:5 and 1:11 R:R closes
  both took multi-day moves) — a tight day-trade-shaped cap like round
  72's 4h would systematically truncate exactly the trades his own
  numbers lean on, so a longer, explicitly-stated cap is used instead.
- RISK PER TRADE / POSITION SIZING: never stated as a formula anywhere
  in the teaching chapters (21/22) — confirmed by exhaustive transcript
  search. His live-challenge risk narration (100% of account on trade 1,
  stepping down over weeks to "never went below 35%... maybe 30%, 27%")
  is gut-feel, non-formulaic, and explicitly tied to a marketing-stunt
  account-flip narrative he himself walks back on camera ("I did not...
  I technically took $300,000 into a million"). UNSPECIFIED / not
  mechanizable from this source — flagged, not guessed, exactly like
  round 72's identical gap for TJR. The engine's standard full-equity
  size_frac=1.0 convention is used, as in every prior round.

ENGINE / GAUNTLET DISCIPLINE (read backtest.py for ground truth)
- run_backtest: one fixed stop_pct/target_pct per run, bar-close-N ->
  fill-at-N+1-open, no lookahead. No cost-free mode.
- Costs: FOREX (EURUSD, USDJPY, GBPCHF) = FOREX_COSTS, a stated retail-
  forex approximation (~1.8bps RT, roughly 2 pips round-trip on a major
  pair — real spreads vary by broker/session/pair, tighter on ECN,
  wider on exotics or off-hours; no commission data exists in this repo
  for any forex venue, so this is a reasoned approximation, not a
  measured one, exactly flagged as such). GOLD (XAU, via cached
  data_gold_1h/1d) = GOLD_COSTS, identical 2bps RT convention to round
  55's GC=F futures cost model. INDEX (ES=F) = FUT_COSTS, identical
  2bps RT convention to round 72. BTC = BTC_COSTS, identical 12bps RT +
  real funding convention to round 72 (align_funding, step11_round6,
  unmodified).
- GAUNTLET: chronological 60/20/20 per dataset (split_points, step41,
  unmodified). Select by TRAIN expectancy > 0 AND VAL expectancy > 0,
  tr_n>=30 and va_n>=8 = SURVIVOR. The sealed 20% test window is NEVER
  computed by this script for any config — score() only ever touches
  [0:i_tr] and [i_tr:i_va]. Ranked survivor candidates are left for the
  lead agent to spend sealed looks against, exactly like every prior
  round's discipline.
- GRID: MODE in {reversal, continuation, both} x ENTRY_STYLE in
  {breakout, retest} x R-multiple in {1.0, 2.0, 4.0} = 18 configs per
  dataset x 5 datasets (USDJPY, GBPCHF, EURUSD, GOLD, ES) + BTC = 108
  configs total, in the repo's established 60-120-configs-per-round
  band. k (swing fractal bars), the retest tolerance, the armed window,
  and max hold are all FIXED per the module docstring above, not swept,
  to keep the grid within that band.
"""

import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

import config
from backtest import CostModel, run_backtest
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import bar_hours, confirmed_swings, hours_to_bars, split_points
from step56_smc_toolkit import bos_chain

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 6.0
STOP_FLOOR_PCT = 0.15

FOREX_COSTS = CostModel(fee_bps=0.1, maker_fee_bps=0.1, half_spread_bps=0.5,
                         slippage_bps=0.3, funding_bps_8h=0.0)   # ~1.8bps RT
GOLD_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                        slippage_bps=0.5, funding_bps_8h=0.0)    # 2bps RT
FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                       slippage_bps=0.5, funding_bps_8h=0.0)     # 2bps RT
BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)     # 12bps RT + funding

FX_PAIRS = {"USDJPY": "USDJPY=X", "GBPCHF": "GBPCHF=X", "EURUSD": "EURUSD=X"}
FX_COSTS = {p: FOREX_COSTS for p in FX_PAIRS}

K_CTX = 3          # daily body-swing fractal bars
K_ENTRY = 3         # 4h body-swing fractal bars (also used for stop distance)
W1_ARMED_BARS = 36  # 4h bars a daily break event stays "live" waiting for its retest (~6 trading days)
TOL_PCT = 0.35      # retest tolerance, % of price (stated AOI-width approximation)
MAX_HOLD_HOURS = 240.0   # 10 trading days
R_MULTIPLES = (1.0, 2.0, 4.0)


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def split_pts(d):
    return split_points(d)


def body_frame(d):
    """Copy of d with high/low replaced by candle-body extremes — his
    repeated, explicit rule: 'do not take the wicks into account.'"""
    out = d.copy()
    out["high"] = np.maximum(d["open"].to_numpy(), d["close"].to_numpy())
    out["low"] = np.minimum(d["open"].to_numpy(), d["close"].to_numpy())
    return out


def resample_ohlc(d, rule):
    df = d.set_index("timestamp")
    o = df["open"].resample(rule).first()
    h = df["high"].resample(rule).max()
    l = df["low"].resample(rule).min()
    c = df["close"].resample(rule).last()
    out = pd.DataFrame({"timestamp": o.index, "open": o.values, "high": h.values,
                         "low": l.values, "close": c.values}).dropna()
    return out.reset_index(drop=True)


def merge_htf_series(working_ts, htf_ts, htf_series, htf_bar_hours):
    """A HTF series value becomes visible on working_ts only once that HTF
    bar has CLOSED (open + htf_bar_hours) — round 72/step43's
    champ_aligned idiom."""
    avail = pd.DataFrame({"timestamp": htf_ts + pd.Timedelta(hours=htf_bar_hours),
                           "v": htf_series.to_numpy()}).sort_values("timestamp")
    merged = pd.merge_asof(pd.DataFrame({"timestamp": working_ts}).sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["v"].reset_index(drop=True)


def merge_event_recency_with_value(entry_ts, struct_ts, struct_event_bool, struct_level,
                                    struct_bar_hours, window_entry_bars, entry_bar_hours):
    """Round 72's merge_event_recency, extended to also carry the FROZEN
    level value of the most recent qualifying event forward through the
    armed window (not just a boolean flag). Returns (armed: bool Series,
    level: float Series) on entry_ts. level is NaN wherever armed=False."""
    avail_time = struct_ts + pd.Timedelta(hours=struct_bar_hours)
    avail = pd.DataFrame({"timestamp": avail_time, "flag": struct_event_bool.to_numpy(),
                           "level": struct_level.to_numpy()})
    avail = avail[avail["flag"]].drop(columns="flag")
    avail["event_time"] = avail["timestamp"]
    if len(avail) == 0:
        n = len(entry_ts)
        return (pd.Series(np.zeros(n, dtype=bool)), pd.Series(np.full(n, np.nan)))
    idx = pd.DataFrame({"timestamp": entry_ts}).sort_values("timestamp")
    merged = pd.merge_asof(idx, avail.sort_values("timestamp"), on="timestamp",
                            direction="backward")
    bars_since = (merged["timestamp"] - merged["event_time"]).dt.total_seconds() / 3600.0 / entry_bar_hours
    armed = bars_since.notna() & (bars_since <= window_entry_bars) & (bars_since >= 0)
    level = merged["level"].where(armed.to_numpy())
    return armed.reset_index(drop=True), level.reset_index(drop=True)


# ---------------------------------------------------------------------------
# concept functions — engulf-prior-2-candles confirmation (NEW)
# ---------------------------------------------------------------------------

def engulf2_events(d):
    """His own, stricter-than-textbook engulfing rule: 'needs to engulf
    the last candlestick and then the previous one minimum.' Also stands
    in for his separately named morning-star/evening-star pattern, which
    numerically reduces to this same test (the small indecision candle
    is simply one of the two bodies being engulfed) — see module
    docstring. Returns (engulf_bull, engulf_bear) boolean Series."""
    o = d["open"].to_numpy()
    c = d["close"].to_numpy()
    bh = np.maximum(o, c)
    bl = np.minimum(o, c)
    n = len(d)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    for i in range(2, n):
        contains = (bh[i] >= max(bh[i - 1], bh[i - 2])) and (bl[i] <= min(bl[i - 1], bl[i - 2]))
        if not contains:
            continue
        if c[i] > o[i]:
            bull[i] = True
        elif c[i] < o[i]:
            bear[i] = True
    idx = d.index
    return pd.Series(bull, index=idx), pd.Series(bear, index=idx)


def retest_confirm_entries(armed_long, armed_short, touch_long, touch_short,
                            engulf_bull, engulf_bear):
    """State machine: within an armed window, once a retest touch fires,
    require an engulf2 confirmation candle (same direction) before the
    entry itself fires. Mirrors round 72's retrace_continuation_entries
    idiom (armed window -> stage 1 -> stage 2 = entry)."""
    n = len(armed_long)
    al, as_ = armed_long.to_numpy(), armed_short.to_numpy()
    tl, ts = touch_long.to_numpy(), touch_short.to_numpy()
    eb, es_ = engulf_bull.to_numpy(), engulf_bear.to_numpy()
    entry_long = np.zeros(n, dtype=bool)
    entry_short = np.zeros(n, dtype=bool)
    touched_l = False
    touched_s = False
    for i in range(n):
        if al[i]:
            if tl[i]:
                touched_l = True
            if touched_l and eb[i]:
                entry_long[i] = True
                touched_l = False
        else:
            touched_l = False
        if as_[i]:
            if ts[i]:
                touched_s = True
            if touched_s and es_[i]:
                entry_short[i] = True
                touched_s = False
        else:
            touched_s = False
    idx = armed_long.index
    return pd.Series(entry_long, index=idx), pd.Series(entry_short, index=idx)


def breakout_entries(armed_long, armed_short):
    """'breakout' entry style: fire on the first bar an event becomes
    armed, no retest wait — his own stated ~30%-of-the-time behavior."""
    el = armed_long & ~armed_long.shift(1, fill_value=False)
    es = armed_short & ~armed_short.shift(1, fill_value=False)
    return el.fillna(False), es.fillna(False)


# ---------------------------------------------------------------------------
# day-trade-shaped signal (max-hold state machine, round 72/43 idiom)
# ---------------------------------------------------------------------------

def day_trade_signal(d, enter_long, enter_short, max_hold_bars):
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    out, pos, held = [], 0.0, 0
    for i in range(len(d)):
        if pos == 0.0:
            if el[i]:
                pos, held = 1.0, 0
            elif es[i]:
                pos, held = -1.0, 0
        else:
            held += 1
            if max_hold_bars and held >= max_hold_bars:
                pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ---------------------------------------------------------------------------
# stop sizing (train-median convention, reused pattern from step56/step72)
# ---------------------------------------------------------------------------

def train_median_stop_pct(entry_mask, distance_pct, i_tr, cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    mask = entry_mask.iloc[:i_tr].fillna(False)
    vals = distance_pct.iloc[:i_tr][mask.to_numpy()].dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(min(max(vals.median(), floor), cap))


def stop_distance_pct(d_body, k, entry_long, entry_short):
    """Distance from entry close to the nearest confirmed body-swing
    extreme opposite the trade direction, in % — his stop 'beyond the
    invalidating wick,' approximated on body extremes per the module
    docstring's body-only rule."""
    sh, sl = confirmed_swings(d_body, k)
    lsh, lsl = sh.ffill(), sl.ffill()
    close = d_body["close"]
    dist_short = ((lsh - close) / close * 100).where(entry_short.to_numpy())
    dist_long = ((close - lsl) / close * 100).where(entry_long.to_numpy())
    return dist_long, dist_short


# ---------------------------------------------------------------------------
# gauntlet plumbing
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


# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def _fetch_yf(symbol, interval, period):
    raw = None
    for attempt in range(3):
        try:
            raw = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=False)
            if raw is not None and len(raw) > 0:
                break
        except Exception as e:
            print(f"  retry {symbol} {interval} ({e})")
        time.sleep(2)
    if raw is None or len(raw) == 0:
        raise RuntimeError(f"no data for {symbol} {interval}")
    df = raw.reset_index()
    tcol = "Date" if "Date" in df.columns else "Datetime"
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df[tcol], utc=True),
        "open": df["Open"].astype(float), "high": df["High"].astype(float),
        "low": df["Low"].astype(float), "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float) if "Volume" in df.columns else 0.0,
    }).dropna(subset=["open", "high", "low", "close"]).drop_duplicates(subset="timestamp").sort_values("timestamp")
    return out.reset_index(drop=True)


def load_forex(tag):
    """Daily (max history) + 4H (resampled from 730d/1h, yfinance's
    practical intraday ceiling — identical constraint to round 72)."""
    d1_fname = f"data_fx73_{tag}_1d.parquet"
    h1_fname = f"data_fx73_{tag}_1h.parquet"
    try:
        d1 = pd.read_parquet(d1_fname)
        print(f"  cached {d1_fname}: {len(d1)} bars {d1['timestamp'].iloc[0]:%Y-%m-%d} -> {d1['timestamp'].iloc[-1]:%Y-%m-%d}")
    except FileNotFoundError:
        print(f"  fetching {FX_PAIRS[tag]} 1d (max) via yfinance...")
        d1 = _fetch_yf(FX_PAIRS[tag], "1d", "max")
        d1.to_parquet(d1_fname)
        print(f"  saved: {len(d1)} bars")
    try:
        h1 = pd.read_parquet(h1_fname)
        print(f"  cached {h1_fname}: {len(h1)} bars {h1['timestamp'].iloc[0]:%Y-%m-%d} -> {h1['timestamp'].iloc[-1]:%Y-%m-%d}")
    except FileNotFoundError:
        print(f"  fetching {FX_PAIRS[tag]} 1h (730d) via yfinance...")
        h1 = _fetch_yf(FX_PAIRS[tag], "1h", "730d")
        h1.to_parquet(h1_fname)
        print(f"  saved: {len(h1)} bars")
    d4h = resample_ohlc(h1, "4h")
    return d1, d4h


def load_gold():
    d1 = pd.read_parquet("data_gold_1d.parquet")
    h1 = pd.read_parquet("data_gold_1h.parquet")
    d4h = resample_ohlc(h1, "4h")
    print(f"  GOLD 1d: {len(d1)} bars, 4h (resampled from cached 1h): {len(d4h)} bars")
    return d1, d4h


def load_index():
    d1 = pd.read_parquet("data_spx_ES_1d.parquet")
    h1 = pd.read_parquet("data_spx_ES_1h.parquet")
    d4h = resample_ohlc(h1, "4h")
    print(f"  ES 1d: {len(d1)} bars, 4h (resampled from cached 1h): {len(d4h)} bars")
    return d1, d4h


def load_btc():
    d1 = pd.read_parquet("data_bybit_BTCUSDT_1d_full.parquet")
    d4h = pd.read_parquet("data_bybit_BTCUSDT_4h_full.parquet")
    print(f"  BTC 1d: {len(d1)} bars, 4h (cached): {len(d4h)} bars")
    return d1, d4h


# ---------------------------------------------------------------------------
# core construction — daily context -> 4h entry
# ---------------------------------------------------------------------------

def build_daily_context(d1, k=K_CTX):
    """Body-based bos_chain on the daily frame — HH/HL/LH/LL trend state
    + bos_up/down + cont_*/choch_* + lsh/lsl (the broken level itself),
    all body-substituted per the module docstring's wick-exclusion rule."""
    d1b = body_frame(d1)
    return bos_chain(d1b, k)


def gauntlet_dataset(tag, d1, d4h, costs, funding=None, k_ctx=K_CTX, k_entry=K_ENTRY):
    rows = []
    n, i_tr, i_va = split_pts(d4h)
    ctx = build_daily_context(d1, k=k_ctx)
    ctx_bh = bar_hours(d1)
    entry_bh = bar_hours(d4h)
    mh_bars = hours_to_bars(d4h, MAX_HOLD_HOURS)

    d4h_body = body_frame(d4h)
    engulf_bull, engulf_bear = engulf2_events(d4h)  # uses raw OHLC internally (own body calc)

    EVENT_LONG = {"reversal": ctx["choch_long"], "continuation": ctx["cont_long"], "both": ctx["bos_up"]}
    EVENT_SHORT = {"reversal": ctx["choch_short"], "continuation": ctx["cont_short"], "both": ctx["bos_down"]}

    for mode in ("reversal", "continuation", "both"):
        armed_long, level_long = merge_event_recency_with_value(
            d4h["timestamp"], d1["timestamp"], EVENT_LONG[mode], ctx["lsh"],
            ctx_bh, W1_ARMED_BARS, entry_bh)
        armed_short, level_short = merge_event_recency_with_value(
            d4h["timestamp"], d1["timestamp"], EVENT_SHORT[mode], ctx["lsl"],
            ctx_bh, W1_ARMED_BARS, entry_bh)

        close4h = d4h["close"]
        touch_long = (armed_long & ((close4h - level_long).abs() / level_long * 100 <= TOL_PCT)).fillna(False)
        touch_short = (armed_short & ((close4h - level_short).abs() / level_short * 100 <= TOL_PCT)).fillna(False)

        for entry_style in ("breakout", "retest"):
            if entry_style == "breakout":
                el, es = breakout_entries(armed_long, armed_short)
            else:
                el, es = retest_confirm_entries(armed_long, armed_short, touch_long, touch_short,
                                                  engulf_bull, engulf_bear)

            dist_long, dist_short = stop_distance_pct(d4h_body, k_entry, el, es)
            entry_mask = (el | es)
            dist_combined = dist_long.where(el.to_numpy(), dist_short)
            stop_pct = train_median_stop_pct(entry_mask, dist_combined, i_tr)
            if stop_pct is None:
                rows.append({"dataset": tag, "config": f"{mode} {entry_style}",
                             "stop%": None, "target%": None, "tr_n": 0, "tr_exp": np.nan,
                             "tr_win%": np.nan, "tr_ret%": np.nan, "tr_dd%": np.nan,
                             "va_n": 0, "va_exp": np.nan, "va_win%": np.nan, "va_ret%": np.nan,
                             "va_dd%": np.nan, "pooled_win%": np.nan, "pooled_RR": np.nan,
                             "tr/day": np.nan, "verdict": "NO-ENTRIES"})
                continue
            for rmult in R_MULTIPLES:
                target_pct = round(stop_pct * rmult, 4)
                sig = day_trade_signal(d4h, el, es, mh_bars)
                tr, va = score(d4h, sig, costs, i_tr, i_va, stop_pct=stop_pct,
                                target_pct=target_pct, funding=funding)
                cfg = f"{mode} {entry_style} R{rmult:.2f}"
                rows.append(mk_row(tag, cfg, tr, va, stop_pct, target_pct, d4h, i_va))
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("ROUND 73 — ALEX GONZALEZ / fxalexg MARKET-STRUCTURE SYSTEM: distill, formalize, gauntlet")
    print("=" * 90)

    all_rows = []

    print("\n--- loading FOREX (his actual traded pairs + EURUSD proxy) ---")
    fx_frames = {}
    for tag in ("USDJPY", "GBPCHF", "EURUSD"):
        print(f"  {tag} ...")
        fx_frames[tag] = load_forex(tag)

    print("\n--- loading GOLD (claimed market, never demonstrated live) ---")
    gold_d1, gold_d4h = load_gold()

    print("\n--- loading ES=F index (claimed market, never demonstrated live) ---")
    es_d1, es_d4h = load_index()

    print("\n--- loading BTC (claimed market, never demonstrated live) ---")
    btc_d1, btc_d4h = load_btc()

    print("\n--- FOREX gauntlet (daily context -> 4h entry, two-tier collapse) ---")
    for tag in ("USDJPY", "GBPCHF", "EURUSD"):
        print(f"  {tag} ...")
        d1, d4h = fx_frames[tag]
        rows = gauntlet_dataset(tag, d1, d4h, FX_COSTS[tag])
        all_rows.extend(rows)

    print("\n--- GOLD gauntlet ---")
    all_rows.extend(gauntlet_dataset("GOLD", gold_d1, gold_d4h, GOLD_COSTS))

    print("\n--- ES=F gauntlet ---")
    all_rows.extend(gauntlet_dataset("ES", es_d1, es_d4h, FUT_COSTS))

    print("\n--- BTC gauntlet (real funding) ---")
    funding = align_funding(btc_d4h, fetch_funding_history("BTCUSDT"))
    all_rows.extend(gauntlet_dataset("BTC", btc_d1, btc_d4h, BTC_COSTS, funding=funding))

    df = pd.DataFrame(all_rows)
    df.to_csv("step73_gauntlet_full.csv", index=False)
    print(f"\nTotal configs run: {len(df)}")
    print(df.to_string(index=False))

    survivors = df[df["verdict"] == "SURVIVOR"].sort_values("va_exp", ascending=False)
    print("\n--- SURVIVORS (train+val positive, floors met — sealed test NOT touched) ---")
    print(survivors.to_string(index=False) if len(survivors) else "  none")

    print("\n--- mode breakdown (mean va_exp, reversal vs continuation vs both) ---")
    df["mode"] = df["config"].str.split().str[0]
    print(df.groupby(["dataset", "mode"])["va_exp"].mean().to_string())

    print("\n--- entry-style breakdown (mean va_exp, breakout vs retest — the discretionary-gap check) ---")
    df["entry_style"] = df["config"].str.split().str[1]
    print(df.groupby(["dataset", "entry_style"])["va_exp"].mean().to_string())

    print("\nDone. See step73_results.md for the full writeup.")
    return df, survivors


if __name__ == "__main__":
    main()
