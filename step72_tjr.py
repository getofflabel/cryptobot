"""
step72_tjr.py — round 72: THE TJR 2026 STRATEGY, formalized + gauntleted.

Run:  python3 step72_tjr.py

Research only — no commits, no live orders. Writes step72_tjr.py (this
file), step72_results.md. The ruleset distillation with transcript quotes
lives in step72_tjr_rules.md — read that FIRST; this docstring only
covers the FORMALIZATION (how the mechanical rules become code) and the
GAUNTLET discipline.

WHY THIS ROUND: the owner's model trader (TJR) published an updated 2026
playbook claiming $700k this year off one strategy. Mandate: distill his
exact rules from the transcript, formalize the mechanical core as
shift-disciplined signals, and gauntlet it honestly on (a) his actual
instruments (NQ=F/ES=F/SPY, index futures/ETF, 1h resolution — 730d is
the yfinance ceiling, REGIME-THIN per the standing R55 convention) and
(b) BTC as a transfer test (our deep 6y 15m/5m/1h cache).

THREE-TIER vs COLLAPSED FORMALIZATION (the single biggest fidelity gap)
His stack is genuinely three timeframes: HTF levels (session/1h/4h) ->
5-minute reversal confirmation -> 1-minute retrace-then-continuation
entry. yfinance only gives 730d of history at 1h resolution for index
futures (5m/1m are capped at ~60d, unusable for an honest 60/20/20
gauntlet) — so the INDEX leg necessarily COLLAPSES steps 2+3+4 into a
single 1h-resolution reversal-confirmation bar: level break (step 1) +
1h BOS/IFVG confirmation (step 2) IS the entry. Steps 3 (continuation
confluence) and 4 (1m retrace-then-continue) cannot be expressed at 1h
and are NOT separately modeled for index — stated as the loudest,
largest approximation in this file. A 15m SMOKE check (60d, NOT
gauntleted, no train/val claims) partially restores step 2 at finer
resolution to sanity-check the collapse isn't hiding something crazy.

BTC gets the fuller 3-tier build the transcript actually describes,
because our own cache goes deep at 15m/5m/1h: HTF context = 1h (session/
1h/4h levels), STRUCTURE tf = 15m (his "5-minute": BOS/IFVG reversal
confirmation), ENTRY tf = 5m (his "1-minute": retrace-then-continuation
BOS state machine). This is a ONE-TIER-UP transfer (his 5m->our 15m, his
1m->our 5m) because we have no 1-minute BTC cache — stated plainly.

CONCEPT DEFINITIONS
- SESSION LEVELS: Asia [00:00,07:00) UTC, London [07:00,13:00) UTC, NY
  [13:30,20:00) UTC (fixed UTC, NOT DST-adjusted — a stated
  approximation of 9:30am-4pm ET that drifts up to 1h against real ET
  across the year). named_session_extremes() reveals a session's own
  high/low to bars ONLY after that session's window has closed for the
  day (step43's session_range() idiom, generalized to 3 named windows),
  then forward-fills — "the most recently completed session's H/L" at
  every later bar, causal by construction.
- 1h / 4h SWING LEVELS: confirmed_swings() (step41, unmodified) on the
  context timeframe itself (1h) and on a same-instrument 4h resample,
  merged back with a "+4h availability" offset identical to step43's
  champ_aligned() idiom — a 4h bar's swing is visible only once that 4h
  bar has actually closed.
- BREAK EVENT (step 1): edge-triggered crossing of the working
  timeframe's close through a level series (session H/L, 1h H/L, or 4h
  H/L, unioned via OR) — "push above a high."
- BOS (step 2/4 continuation and retrace): imported unmodified from
  step56_smc_toolkit.bos_chain — candle-close-through-the-last-confirmed-
  swing, exactly TJR's own verbal definition of BOS.
- IFVG (step 2, "inverse fair value gap"): NEW function ifvg_events()
  here — a 3-candle FVG (same bull/bear gap test as step56's
  fvg_signals) that later gets a CLOSE back through its own near edge,
  opposite its formation bias ("we close underneath it... disrespecting
  bullish market structure"). Bullish-gap disrespect -> bearish signal;
  bearish-gap disrespect -> bullish signal. Fixed 200-bar expiry
  (unswept constant, stated).
- REVERSAL-CONFIRM (step 2 fires): break_event ARMED for W1 structure-
  bars (rolling-max of the break boolean, causal), AND a BOS or IFVG in
  the direction OPPOSITE the break, on the structure timeframe. W1=48
  structure-bars, fixed (not swept, to keep the grid within the "his own
  parameter neighborhood" budget).
- ENTRY (BTC 3-tier only): the structure-tf reversal-confirm event is
  merged onto the entry tf with a "+structure-bar-hours availability"
  offset and a W2=24 entry-bar recency window (armed flag). Within that
  window a small state machine (retrace_continuation_entries()) requires
  a retrace BOS (opposite direction) THEN a continuation BOS (trade
  direction) on the entry tf, exactly steps 3+4 folded together per
  TJR's own simplification ("we can just say we want a one minute break
  of structure... then... the same exact thing in the direction that
  we're looking to push").
- INDEX (collapsed): entry_short/entry_long = the reversal-confirm event
  itself, directly on the 1h working timeframe. No separate retrace
  stage — the stated fidelity gap above.
- STOP: nearest confirmed swing extreme (entry tf, same k as structure)
  opposite the trade direction at entry time -> TRAIN-only median %
  distance, held fixed across train/val/test (this repo's established
  per-trade-dynamic-distance approximation since round 17/41/43/56).
  Capped [0.15%, 6.0%].
- TARGET: R-multiple x stop_pct — the swept parameter that lets us read
  off the realized win-rate/R:R profile against his claimed 64.29% /
  1.33R directly (required analysis).
- CROSS-INSTRUMENT ALIGNMENT FILTER: bos_chain's persistent trend state
  on the structure tf of BOTH pair instruments (ES<->NQ, SPY<->NQ,
  BTC<->ETH) must agree and be non-zero. Swept ON/OFF — this IS the
  discretionary-gap sensitivity check for the ~10:30 cutoff's sibling
  rule (the one filter he states as an absolute hard rule).
- SESSION WINDOW (entry gate): TIGHT = [13:30,14:30) UTC (9:30-10:30
  ET), EXTENDED = [13:30,15:30) UTC (9:30-11:30 ET, covering his own
  11:05 entry example). Swept — the mechanization of his soft "~10:30"
  cutoff.
- MAX HOLD: fixed 4h (not swept), forced flat — every worked example in
  the transcript resolves same-session; no overnight hold is ever shown.

ENGINE / GAUNTLET DISCIPLINE (read backtest.py for ground truth)
- run_backtest: one fixed stop_pct/target_pct per run, bar-close-N ->
  fill-at-N+1-open, no lookahead. No cost-free mode.
- Costs: INDEX (ES=F, NQ=F) = step60's FUT_COSTS (0.5bps fee + 0.5bps
  slippage, 0 half-spread/funding) -> exactly 2bps taker RT, per the
  lead's mandate. SPY = step60's ETF_COSTS (1+1bps) -> 4bps RT, noted as
  the sibling's own honest ETF cost, not force-fit to 2bps. BTC =
  fee_bps=6.0 (BloFin/Bybit taker), half_spread=0, slippage=0 -> exactly
  12bps taker RT per the mandate, PLUS real funding via align_funding
  (step11_round6, unmodified). ETH (partner-only, not itself gauntleted)
  uses the same BTC cost model where its own trades are ever scored.
- GAUNTLET: chronological 60/20/20 per dataset (split_points idiom).
  Select by TRAIN expectancy only (>=30 trades) + POSITIVE VAL (>=8
  trades) = SURVIVOR. The sealed 20% test slice is NEVER touched by this
  script — score() only ever computes [0:i_tr] and [i_tr:i_va]. Ranked
  survivor candidates are left for the lead agent to spend sealed looks
  against, exactly like every prior round's discipline.
- GRID: his own parameter neighborhood only — R-multiple in
  {1.0, 1.33, 2.0, 3.0} (centered on his stated 1.33R), session window
  in {tight, extended}, alignment filter in {on, off}. k (swing fractal
  bars) fixed per dataset resolution, not swept, to keep total configs
  in the 60-120 band across 5 gauntleted datasets (NQ 1h, ES 1h, SPY 1h,
  BTC 3-tier, plus the 15m/60d smoke which is NOT part of the grid
  count).
"""

import time
import warnings

import numpy as np
import pandas as pd
import yfinance as yf

import config
from backtest import CostModel, run_backtest
from step11_round6 import align_funding, fetch_funding_history
from step41_shorts import confirmed_swings, last_n_confirmed
from step43_daytrade import bar_hours as _bar_hours_generic
from step56_smc_toolkit import bos_chain

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
STOP_CAP_PCT = 6.0
STOP_FLOOR_PCT = 0.15

FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                       slippage_bps=0.5, funding_bps_8h=0.0)          # 2bps RT
ETF_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                       slippage_bps=1.0, funding_bps_8h=0.0)          # 4bps RT
BTC_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.0,
                       slippage_bps=0.0, funding_bps_8h=1.0)          # 12bps RT + funding

TICKER = {"NQ": "NQ=F", "ES": "ES=F", "SPY": "SPY"}
COSTS = {"NQ": FUT_COSTS, "ES": FUT_COSTS, "SPY": ETF_COSTS}
PARTNER = {"NQ": "ES", "ES": "NQ", "SPY": "NQ"}   # cross-instrument alignment partner

# session windows, fixed UTC (not DST-adjusted, stated approximation)
ASIA = (0.0, 7.0)
LONDON = (7.0, 13.0)
NY_REF = (13.5, 20.0)
ENTRY_TIGHT = (13.5, 14.5)     # 9:30-10:30 ET
ENTRY_EXT = (13.5, 15.5)       # 9:30-11:30 ET

MAX_HOLD_HOURS = 4.0
W1_STRUCT_BARS = 48
W2_ENTRY_BARS = 24
IFVG_EXPIRE = 200


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def bar_hours(d):
    return _bar_hours_generic(d)


def hours_to_bars(d, hours):
    return max(1, round(hours / bar_hours(d)))


def split_points(d):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


def in_window(d, start_h, end_h):
    hour = d["timestamp"].dt.hour + d["timestamp"].dt.minute / 60.0
    return (hour >= start_h) & (hour < end_h)


def named_session_extremes(d, start_h, end_h):
    """Most-recently-COMPLETED session's high/low, causal (step43's
    session_range idiom generalized to an arbitrary UTC window)."""
    ts = d["timestamp"]
    day = ts.dt.floor("D")
    win = in_window(d, start_h, end_h)
    tmp = pd.DataFrame({"day": day, "high": d["high"], "low": d["low"]})
    win_high = tmp["high"].where(win).groupby(tmp["day"]).transform("max")
    win_low = tmp["low"].where(win).groupby(tmp["day"]).transform("min")
    after = ~win & (ts.dt.hour + ts.dt.minute / 60.0 >= end_h)
    level_high = win_high.where(after).ffill()
    level_low = win_low.where(after).ffill()
    return level_high, level_low


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
    bar has CLOSED (open + htf_bar_hours) — champ_aligned's idiom."""
    avail = pd.DataFrame({"timestamp": htf_ts + pd.Timedelta(hours=htf_bar_hours),
                           "v": htf_series.to_numpy()}).sort_values("timestamp")
    merged = pd.merge_asof(pd.DataFrame({"timestamp": working_ts}).sort_values("timestamp"),
                            avail, on="timestamp", direction="backward")
    return merged["v"].reset_index(drop=True)


def merge_event_recency(entry_ts, struct_ts, struct_event_bool, struct_bar_hours,
                         window_entry_bars, entry_bar_hours):
    """How many ENTRY-tf bars ago did the most recent struct_event become
    available (at its bar's close)? Returns a boolean 'armed' series on
    entry_ts, True for window_entry_bars bars after availability."""
    avail_time = struct_ts + pd.Timedelta(hours=struct_bar_hours)
    avail = pd.DataFrame({"timestamp": avail_time, "flag": struct_event_bool.to_numpy()})
    avail = avail[avail["flag"]].drop(columns="flag")
    avail["event_time"] = avail["timestamp"]
    if len(avail) == 0:
        return pd.Series(np.zeros(len(entry_ts), dtype=bool))
    idx = pd.DataFrame({"timestamp": entry_ts}).sort_values("timestamp")
    merged = pd.merge_asof(idx, avail.sort_values("timestamp"), on="timestamp",
                            direction="backward")
    bars_since = (merged["timestamp"] - merged["event_time"]).dt.total_seconds() / 3600.0 / entry_bar_hours
    armed = bars_since.notna() & (bars_since <= window_entry_bars) & (bars_since >= 0)
    return armed.reset_index(drop=True)


# ---------------------------------------------------------------------------
# concept functions — level break, IFVG (BOS reused unmodified from step56)
# ---------------------------------------------------------------------------

def level_break_events(close, level):
    """Edge-triggered: close crosses above/below `level` for the first
    time since the level last changed value (no re-fire while it stays
    broken and the level hasn't updated)."""
    above = (close > level).fillna(False)
    below = (close < level).fillna(False)
    break_up = above & ~above.shift(1, fill_value=False)
    break_down = below & ~below.shift(1, fill_value=False)
    return break_up, break_down


def ifvg_events(d, expire_bars=IFVG_EXPIRE):
    """Inverse fair value gap — see module docstring. Returns
    (ifvg_bull, ifvg_bear) boolean Series."""
    h, l, c = d["high"].to_numpy(), d["low"].to_numpy(), d["close"].to_numpy()
    n = len(d)
    bull_bot = np.full(n, np.nan)   # bottom edge of a bullish gap = bar1.high
    bear_top = np.full(n, np.nan)   # top edge of a bearish gap = bar1.low
    if n > 2:
        bg = h[:-2] < l[2:]
        beg = l[:-2] > h[2:]
        bull_bot[2:] = np.where(bg, h[:-2], np.nan)
        bear_top[2:] = np.where(beg, l[:-2], np.nan)

    ifvg_bear = np.zeros(n, dtype=bool)
    ifvg_bull = np.zeros(n, dtype=bool)
    ab = None   # (bull_bot, formed_i)
    ar = None   # (bear_top, formed_i)
    for i in range(n):
        if not np.isnan(bull_bot[i]):
            ab = (bull_bot[i], i)
        if not np.isnan(bear_top[i]):
            ar = (bear_top[i], i)
        if ab is not None:
            bot, formed = ab
            if i - formed > expire_bars:
                ab = None
            elif i > formed and c[i] < bot:
                ifvg_bear[i] = True
                ab = None
        if ar is not None:
            top, formed = ar
            if i - formed > expire_bars:
                ar = None
            elif i > formed and c[i] > top:
                ifvg_bull[i] = True
                ar = None
    idx = d.index
    return pd.Series(ifvg_bull, index=idx), pd.Series(ifvg_bear, index=idx)


def retrace_continuation_entries(armed_short, armed_long, bos_up, bos_down):
    """The step-3/4 fold: within an armed window, require a retrace BOS
    (opposite direction) THEN a continuation BOS (trade direction).
    armed_short: looking for a short (retrace=bos_up, continuation=bos_down).
    armed_long:  looking for a long  (retrace=bos_down, continuation=bos_up)."""
    n = len(armed_short)
    a_s = armed_short.to_numpy(); a_l = armed_long.to_numpy()
    up = bos_up.to_numpy(); dn = bos_down.to_numpy()
    entry_short = np.zeros(n, dtype=bool)
    entry_long = np.zeros(n, dtype=bool)
    seen_retrace_s = False
    seen_retrace_l = False
    for i in range(n):
        if a_s[i]:
            if up[i]:
                seen_retrace_s = True
            elif dn[i] and seen_retrace_s:
                entry_short[i] = True
                seen_retrace_s = False
        else:
            seen_retrace_s = False
        if a_l[i]:
            if dn[i]:
                seen_retrace_l = True
            elif up[i] and seen_retrace_l:
                entry_long[i] = True
                seen_retrace_l = False
        else:
            seen_retrace_l = False
    idx = armed_short.index
    return pd.Series(entry_short, index=idx), pd.Series(entry_long, index=idx)


# ---------------------------------------------------------------------------
# context levels (session + 1h swing + 4h swing), built on a 1h "context" frame
# ---------------------------------------------------------------------------

def build_context_levels(d_ctx, k1h=3, k4h=2):
    """d_ctx MUST be 1h bars. Returns dict of level_high/level_low Series
    (unioned session/1h/4h -> break events), all living on d_ctx's own
    timestamps."""
    asia_h, asia_l = named_session_extremes(d_ctx, *ASIA)
    lon_h, lon_l = named_session_extremes(d_ctx, *LONDON)
    ny_h, ny_l = named_session_extremes(d_ctx, *NY_REF)

    sh1h, sl1h = confirmed_swings(d_ctx, k1h)
    lsh1h, lsl1h = sh1h.ffill(), sl1h.ffill()

    d4h = resample_ohlc(d_ctx, "4h")
    sh4h, sl4h = confirmed_swings(d4h, k4h)
    lsh4h_raw, lsl4h_raw = sh4h.ffill(), sl4h.ffill()
    lsh4h = merge_htf_series(d_ctx["timestamp"], d4h["timestamp"], lsh4h_raw, 4.0)
    lsl4h = merge_htf_series(d_ctx["timestamp"], d4h["timestamp"], lsl4h_raw, 4.0)

    level_high = {"asia": asia_h, "london": lon_h, "ny": ny_h,
                   "sw1h": lsh1h.reset_index(drop=True), "sw4h": lsh4h}
    level_low = {"asia": asia_l, "london": lon_l, "ny": ny_l,
                  "sw1h": lsl1h.reset_index(drop=True), "sw4h": lsl4h}
    # any-level break: OR across the 5 level sources, edge-triggered per source then unioned
    close = d_ctx["close"].reset_index(drop=True)
    break_up = pd.Series(False, index=d_ctx.index)
    break_down = pd.Series(False, index=d_ctx.index)
    for name, series in level_high.items():
        bu, _ = level_break_events(close, series.reset_index(drop=True))
        break_up = break_up | bu.to_numpy()
    for name, series in level_low.items():
        _, bd = level_break_events(close, series.reset_index(drop=True))
        break_down = break_down | bd.to_numpy()
    # target distance: nearest OPPOSING level beyond current close (for R analysis only, not used by engine directly)
    return dict(break_up=break_up.fillna(False), break_down=break_down.fillna(False))


# ---------------------------------------------------------------------------
# stop sizing (train-median convention, reused pattern from step56)
# ---------------------------------------------------------------------------

def train_median_stop_pct(entry_mask, distance_pct, i_tr,
                           cap=STOP_CAP_PCT, floor=STOP_FLOOR_PCT):
    mask = entry_mask.iloc[:i_tr].fillna(False)
    vals = distance_pct.iloc[:i_tr][mask.to_numpy()].dropna()
    vals = vals[vals > 0]
    if len(vals) == 0:
        return None
    return float(min(max(vals.median(), floor), cap))


def stop_distance_pct(d, k, entry_long, entry_short):
    """Distance from entry close to the nearest confirmed swing extreme
    opposite the trade direction, in % — the 'second high/low' TJR
    places his stop beyond."""
    sh, sl = confirmed_swings(d, k)
    lsh, lsl = sh.ffill(), sl.ffill()
    close = d["close"]
    dist_short = ((lsh - close) / close * 100).where(entry_short.to_numpy())
    dist_long = ((close - lsl) / close * 100).where(entry_long.to_numpy())
    return dist_long, dist_short


# ---------------------------------------------------------------------------
# gauntlet plumbing
# ---------------------------------------------------------------------------

def score(d, sig, costs, i_tr, i_va, stop_pct=None, target_pct=None,
          funding=None):
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


def trades_per_day(d, tr, va, i_tr, i_va):
    n_trades = len(tr.trades) + len(va.trades)
    span_days = (d["timestamp"].iloc[i_va - 1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return n_trades / span_days if span_days > 0 else float("nan")


def mk_row(dataset, cfg, tr, va, stop_pct, target_pct, d, i_tr, i_va):
    win_rate, avg_win, avg_loss, rr = rr_stats(tr, va)
    return {
        "dataset": dataset, "config": cfg,
        "stop%": stop_pct, "target%": target_pct,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy, "tr_win%": tr.win_rate * 100,
        "tr_ret%": tr.total_return_pct, "tr_dd%": tr.max_drawdown_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy, "va_win%": va.win_rate * 100,
        "va_ret%": va.total_return_pct, "va_dd%": va.max_drawdown_pct,
        "pooled_win%": win_rate, "pooled_RR": rr,
        "tr/day": trades_per_day(d, tr, va, i_tr, i_va),
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
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp")
    return out.reset_index(drop=True)


def load_index_1h(tag):
    for fname in (f"data_spx_{tag}_1h.parquet",):
        try:
            d = pd.read_parquet(fname)
            print(f"  cached {fname}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
            return d
        except FileNotFoundError:
            pass
    print(f"  fetching {TICKER[tag]} 1h (730d) via yfinance...")
    d = _fetch_yf(TICKER[tag], "1h", "730d")
    d.to_parquet(f"data_spx_{tag}_1h.parquet")
    print(f"  saved: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d


def load_index_15m_smoke(tag):
    fname = f"data_spx72_{tag}_15m_smoke.parquet"
    try:
        d = pd.read_parquet(fname)
        print(f"  cached {fname}: {len(d)} bars")
        return d
    except FileNotFoundError:
        pass
    print(f"  fetching {TICKER[tag]} 15m (60d, SMOKE ONLY) via yfinance...")
    d = _fetch_yf(TICKER[tag], "15m", "60d")
    d.to_parquet(fname)
    print(f"  saved: {len(d)} bars")
    return d


def load_btc_eth():
    frames = {}
    for sym, tag in (("BTCUSDT", "BTC"), ("ETHUSDT", "ETH")):
        frames[tag] = {}
        for tf in ("1h", "15m", "5m"):
            fname = f"data_bybit_{sym}_{tf}_full.parquet"
            d = pd.read_parquet(fname)
            frames[tag][tf] = d
            print(f"  {tag} {tf}: {len(d)} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return frames


# ---------------------------------------------------------------------------
# INDEX (collapsed 2-step) construction + gauntlet
# ---------------------------------------------------------------------------

def build_index_signals(d, k=3):
    ctx = build_context_levels(d, k1h=k, k4h=max(2, k - 1))
    bos = bos_chain(d, k)
    ifvg_bull, ifvg_bear = ifvg_events(d)

    armed_short = ctx["break_up"].rolling(W1_STRUCT_BARS, min_periods=1).max().astype(bool)
    armed_long = ctx["break_down"].rolling(W1_STRUCT_BARS, min_periods=1).max().astype(bool)

    entry_short_raw = armed_short & (bos["bos_down"] | ifvg_bear)
    entry_long_raw = armed_long & (bos["bos_up"] | ifvg_bull)
    return entry_long_raw.fillna(False), entry_short_raw.fillna(False), k


def apply_filters(d, entry_long, entry_short, window, align_gate):
    win_mask = in_window(d, *window)
    el = entry_long & win_mask
    es = entry_short & win_mask
    if align_gate is not None:
        el = el & align_gate
        es = es & align_gate
    return el.fillna(False), es.fillna(False)


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


def partner_alignment(d_self, k_self, d_partner, k_partner):
    """Both instruments' bos_chain 'chain' state must agree and be
    non-zero, merged onto d_self's timestamps."""
    chain_self = bos_chain(d_self, k_self)["chain"]
    chain_partner = bos_chain(d_partner, k_partner)["chain"]
    merged = pd.merge_asof(
        pd.DataFrame({"timestamp": d_self["timestamp"], "self": chain_self.to_numpy()}).sort_values("timestamp"),
        pd.DataFrame({"timestamp": d_partner["timestamp"], "partner": chain_partner.to_numpy()}).sort_values("timestamp"),
        on="timestamp", direction="backward")
    aligned_up = (merged["self"] == 1) & (merged["partner"] == 1)
    aligned_down = (merged["self"] == -1) & (merged["partner"] == -1)
    return (aligned_up | aligned_down).reset_index(drop=True)


def gauntlet_index(tag, d, partner_frames, k=3):
    rows = []
    n, i_tr, i_va = split_points(d)
    entry_long_raw, entry_short_raw, _ = build_index_signals(d, k=k)
    d_partner = partner_frames[PARTNER[tag]]
    align_gate_series = partner_alignment(d, k, d_partner, k)
    mh_bars = hours_to_bars(d, MAX_HOLD_HOURS)

    for window_name, window in (("tight9:30-10:30ET", ENTRY_TIGHT), ("ext9:30-11:30ET", ENTRY_EXT)):
        for align_name, align_gate in (("align=ON", align_gate_series), ("align=OFF", None)):
            el, es = apply_filters(d, entry_long_raw, entry_short_raw, window, align_gate)
            dist_long, dist_short = stop_distance_pct(d, k, el, es)
            entry_mask = (el | es)
            dist_combined = dist_long.where(el.to_numpy(), dist_short)
            stop_pct = train_median_stop_pct(entry_mask, dist_combined, i_tr)
            if stop_pct is None:
                rows.append({"dataset": tag, "config": f"{window_name} {align_name}",
                             "stop%": None, "target%": None, "tr_n": 0, "tr_exp": np.nan,
                             "tr_win%": np.nan, "tr_ret%": np.nan, "tr_dd%": np.nan,
                             "va_n": 0, "va_exp": np.nan, "va_win%": np.nan, "va_ret%": np.nan,
                             "va_dd%": np.nan, "pooled_win%": np.nan, "pooled_RR": np.nan,
                             "tr/day": np.nan, "verdict": "NO-ENTRIES"})
                continue
            for rmult in (1.0, 1.33, 2.0, 3.0):
                target_pct = round(stop_pct * rmult, 4)
                sig = day_trade_signal(d, el, es, mh_bars)
                tr, va = score(d, sig, COSTS[tag], i_tr, i_va, stop_pct=stop_pct, target_pct=target_pct)
                cfg = f"{window_name} {align_name} R{rmult:.2f}"
                rows.append(mk_row(tag, cfg, tr, va, stop_pct, target_pct, d, i_tr, i_va))
    return rows


# ---------------------------------------------------------------------------
# BTC 3-tier construction + gauntlet
# ---------------------------------------------------------------------------

def gauntlet_btc(frames_btc, frames_eth, k_ctx=3, k_struct=3, k_entry=3):
    d_ctx = frames_btc["1h"]
    d_struct = frames_btc["15m"]
    d_entry = frames_btc["5m"]
    n, i_tr, i_va = split_points(d_entry)

    ctx = build_context_levels(d_ctx, k1h=k_ctx, k4h=max(2, k_ctx - 1))
    break_up_ctx = merge_htf_series(d_struct["timestamp"], d_ctx["timestamp"], ctx["break_up"].astype(float), 1.0) > 0
    break_down_ctx = merge_htf_series(d_struct["timestamp"], d_ctx["timestamp"], ctx["break_down"].astype(float), 1.0) > 0

    bos_struct = bos_chain(d_struct, k_struct)
    ifvg_bull_struct, ifvg_bear_struct = ifvg_events(d_struct)

    armed_short_struct = break_up_ctx.rolling(W1_STRUCT_BARS, min_periods=1).max().astype(bool)
    armed_long_struct = break_down_ctx.rolling(W1_STRUCT_BARS, min_periods=1).max().astype(bool)
    reversal_confirm_short = (armed_short_struct & (bos_struct["bos_down"] | ifvg_bear_struct)).fillna(False)
    reversal_confirm_long = (armed_long_struct & (bos_struct["bos_up"] | ifvg_bull_struct)).fillna(False)

    struct_bh = bar_hours(d_struct)
    entry_bh = bar_hours(d_entry)
    armed_short_entry = merge_event_recency(d_entry["timestamp"], d_struct["timestamp"],
                                             reversal_confirm_short, struct_bh, W2_ENTRY_BARS, entry_bh)
    armed_long_entry = merge_event_recency(d_entry["timestamp"], d_struct["timestamp"],
                                            reversal_confirm_long, struct_bh, W2_ENTRY_BARS, entry_bh)

    bos_entry = bos_chain(d_entry, k_entry)
    entry_short_raw, entry_long_raw = retrace_continuation_entries(
        armed_short_entry, armed_long_entry, bos_entry["bos_up"], bos_entry["bos_down"])

    d_eth_struct = frames_eth["15m"]
    align_gate_series = partner_alignment(d_struct, k_struct, d_eth_struct, k_struct)
    align_gate_entry = merge_htf_series(d_entry["timestamp"], d_struct["timestamp"],
                                         align_gate_series.astype(float), struct_bh) > 0

    funding = align_funding(d_entry, fetch_funding_history("BTCUSDT"))
    mh_bars = hours_to_bars(d_entry, MAX_HOLD_HOURS)

    rows = []
    for window_name, window in (("tight9:30-10:30ET", ENTRY_TIGHT), ("ext9:30-11:30ET", ENTRY_EXT)):
        for align_name, gate in (("align=ON", align_gate_entry), ("align=OFF", None)):
            el, es = apply_filters(d_entry, entry_long_raw, entry_short_raw, window, gate)
            dist_long, dist_short = stop_distance_pct(d_entry, k_entry, el, es)
            entry_mask = (el | es)
            dist_combined = dist_long.where(el.to_numpy(), dist_short)
            stop_pct = train_median_stop_pct(entry_mask, dist_combined, i_tr)
            if stop_pct is None:
                rows.append({"dataset": "BTC", "config": f"{window_name} {align_name}",
                             "stop%": None, "target%": None, "tr_n": 0, "tr_exp": np.nan,
                             "tr_win%": np.nan, "tr_ret%": np.nan, "tr_dd%": np.nan,
                             "va_n": 0, "va_exp": np.nan, "va_win%": np.nan, "va_ret%": np.nan,
                             "va_dd%": np.nan, "pooled_win%": np.nan, "pooled_RR": np.nan,
                             "tr/day": np.nan, "verdict": "NO-ENTRIES"})
                continue
            for rmult in (1.0, 1.33, 2.0, 3.0):
                target_pct = round(stop_pct * rmult, 4)
                sig = day_trade_signal(d_entry, el, es, mh_bars)
                tr, va = score(d_entry, sig, BTC_COSTS, i_tr, i_va, stop_pct=stop_pct,
                               target_pct=target_pct, funding=funding)
                cfg = f"{window_name} {align_name} R{rmult:.2f}"
                rows.append(mk_row("BTC", cfg, tr, va, stop_pct, target_pct, d_entry, i_tr, i_va))
    return rows


# ---------------------------------------------------------------------------
# smoke check (index, 15m, 60d — NOT gauntleted, no train/val claims)
# ---------------------------------------------------------------------------

def smoke_index_15m(tag, k=3):
    d = load_index_15m_smoke(tag)
    if len(d) < 300:
        return {"dataset": tag, "note": "too few 15m/60d bars for even a smoke read", "n": len(d)}
    el_raw, es_raw, _ = build_index_signals(d, k=k)
    win_mask = in_window(d, *ENTRY_EXT)
    el = (el_raw & win_mask).fillna(False)
    es = (es_raw & win_mask).fillna(False)
    n_days = (d["timestamp"].iloc[-1] - d["timestamp"].iloc[0]).total_seconds() / 86400
    return {"dataset": tag, "bars": len(d), "days": round(n_days, 1),
            "raw_long_events": int(el_raw.sum()), "raw_short_events": int(es_raw.sum()),
            "windowed_long": int(el.sum()), "windowed_short": int(es.sum()),
            "note": "SMOKE ONLY: 60d 15m sample, sanity check for the collapsed-1h approximation, "
                    "NOT gauntleted, no train/val split, no expectancy claim"}


# ---------------------------------------------------------------------------
# session-window performance breakdown (required analysis)
# ---------------------------------------------------------------------------

def session_breakdown(dataset, d, sig, costs, i_tr, i_va, funding=None):
    """Split pooled train+val trades by the UTC hour bucket their ENTRY
    fell into, report count + mean pnl per bucket — 'his edge should live
    in HIS hours if real'."""
    tr, va = score(d, sig, costs, i_tr, i_va, funding=funding)
    trades = list(tr.trades) + list(va.trades)
    buckets = {}
    for t in trades:
        h = t.entry_time.hour
        buckets.setdefault(h, []).append(t.pnl)
    rows = []
    for h in sorted(buckets):
        pnls = buckets[h]
        rows.append({"dataset": dataset, "utc_hour": h, "n": len(pnls),
                     "mean_pnl": float(np.mean(pnls)), "win%": float(np.mean([p > 0 for p in pnls]) * 100)})
    return rows


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 90)
    print("ROUND 72 — THE TJR 2026 STRATEGY: distill, formalize, gauntlet")
    print("=" * 90)

    print("\n--- loading index data (NQ=F, ES=F, SPY) ---")
    index_frames = {tag: load_index_1h(tag) for tag in ("NQ", "ES", "SPY")}

    print("\n--- loading BTC/ETH deep cache (1h/15m/5m) ---")
    crypto_frames = load_btc_eth()

    all_rows = []
    smoke_rows = []
    session_rows = []

    print("\n--- INDEX gauntlet (1h, collapsed 2-step, 730d — REGIME-THIN, R55 convention) ---")
    for tag in ("NQ", "ES", "SPY"):
        print(f"  {tag} ...")
        rows = gauntlet_index(tag, index_frames[tag], index_frames, k=3)
        all_rows.extend(rows)

    print("\n--- INDEX 15m/60d SMOKE (NOT gauntleted) ---")
    for tag in ("NQ", "ES"):
        smoke_rows.append(smoke_index_15m(tag, k=3))

    print("\n--- BTC 3-tier gauntlet (1h context / 15m structure / 5m entry, 6y deep cache) ---")
    btc_rows = gauntlet_btc(crypto_frames["BTC"], crypto_frames["ETH"])
    all_rows.extend(btc_rows)

    df = pd.DataFrame(all_rows)
    df.to_csv("step72_gauntlet_full.csv", index=False)
    print(f"\nTotal configs run: {len(df)}")
    print(df.to_string(index=False))

    survivors = df[df["verdict"] == "SURVIVOR"].sort_values("va_exp", ascending=False)
    print("\n--- SURVIVORS (train+val positive, floors met — sealed test NOT touched) ---")
    print(survivors.to_string(index=False) if len(survivors) else "  none")

    print("\n--- SMOKE (index 15m/60d) ---")
    for r in smoke_rows:
        print(" ", r)

    # session-window breakdown for the best config per dataset (whatever it scored)
    print("\n--- session-window (UTC hour) breakdown, best config per dataset ---")
    for tag in ("NQ", "ES", "SPY"):
        sub = df[df["dataset"] == tag].sort_values("tr_exp", ascending=False)
        if len(sub) == 0 or pd.isna(sub.iloc[0]["stop%"]):
            continue
        best = sub.iloc[0]
        el_raw, es_raw, _ = build_index_signals(index_frames[tag], k=3)
        window = ENTRY_TIGHT if "tight" in best["config"] else ENTRY_EXT
        gate = partner_alignment(index_frames[tag], 3, index_frames[PARTNER[tag]], 3) if "align=ON" in best["config"] else None
        el, es = apply_filters(index_frames[tag], el_raw, es_raw, window, gate)
        n, i_tr, i_va = split_points(index_frames[tag])
        mh_bars = hours_to_bars(index_frames[tag], MAX_HOLD_HOURS)
        sig = day_trade_signal(index_frames[tag], el, es, mh_bars)
        rows = session_breakdown(tag, index_frames[tag], sig, COSTS[tag], i_tr, i_va)
        session_rows.extend(rows)
    sess_df = pd.DataFrame(session_rows)
    if len(sess_df):
        print(sess_df.to_string(index=False))
        sess_df.to_csv("step72_session_breakdown.csv", index=False)

    print("\nDone. See step72_results.md for the full writeup.")
    return df, survivors, smoke_rows, sess_df if len(session_rows) else None


if __name__ == "__main__":
    main()
