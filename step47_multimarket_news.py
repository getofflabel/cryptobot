"""
step47_multimarket_news.py — round 47: does the program's ONE proven edge
(news momentum off WatcherGuru headlines — sealed-test PASS on BTC, round
45B: A-news-momentum FIRST-BAR-MOVE 1h stop1.2%/tgt2.4% hold24h, TEST
+$20.81/t x67, +13.9%, 52.2% win) transfer to TRADITIONAL markets? Owner's
thesis: macro news should move GOLD / OIL / NASDAQ / S&P HARDER than
crypto, since crypto trades on its own momentum a lot of the time while
these four are "pure macro receptors."

Run:  python3 step47_multimarket_news.py

Research only. Touches ONLY:
  - step47_multimarket_news.py   (this file)
  - step47_results.md            (written by hand from this script's output)
  - data_news_mkts_<SYM>.parquet (GLD, USO, QQQ, SPY, GC=F, CL=F caches)
No live orders, no commits, no other repo file is written or modified.
Other agents own step48*/step49* — not touched.

READ FIRST (per the mandate): step45b_news_events.py supplies
classify_headline (imported verbatim — the exact live-reusable keyword
classifier) and align_events (imported verbatim — the no-lookahead
event-to-bar alignment) and event_study (imported verbatim — it is already
fully generic over any candle frame, so round 47 reuses the actual
function, not just its "structure"). step43_daytrade.py supplies
split_points / verdict_for / mk_row / MIN_TRAIN_TRADES / MIN_VAL_TRADES —
all generic over any (tr, va) BacktestResult pair.

WHAT'S GENUINELY NEW HERE (the two things a crypto-only script gets wrong
if copy-pasted blind onto TradFi):

  1. THESE MARKETS ARE NOT 24/7. A 3am headline's "first tradable bar" for
     QQQ is hours away at the 9:30am open — a real gap, not a a few-minute
     wait like BTC. align_events is reused unchanged (it already does the
     right thing: floor_idx = last bar with open<=event, trading_idx =
     floor_idx+1 = the next bar that EXISTS in the data — and since ETF/
     futures bars only exist during their sessions, "next bar that exists"
     automatically becomes "first tradable bar of the next open session").
     What's new is honesty ABOUT that gap: every event is tagged SESSION
     (the next tradable bar's open lands within 75 minutes of the event —
     i.e. the market was live and caught it on the very next normal 1h
     print) or OFF-HOURS (the market was closed and the "reaction" is
     really an overnight/weekend gap-open, a different animal). Pooled and
     session-only results are reported SEPARATELY throughout — never
     blended into one number.
  2. GAP-THROUGH-STOP HONESTY. backtest.py's intra-bar hard stop fires
     whenever a bar's LOW/HIGH crosses the stop level and fills AT the
     stop price (a fair assumption when the stop was touched mid-bar).
     But if the bar OPENS beyond the stop (the overnight-gap case that is
     rare in 24/7 crypto and common here), that fill is a fiction — a real
     stop order would have filled at the (worse) open. gap_adjust() below
     detects exactly this case (comparing each stop-exit's known trigger
     level against that exit bar's actual OPEN) and recomputes the honest
     post-adjustment P&L using the exact same cash/fee arithmetic
     backtest.py itself uses (verified byte-for-byte against a direct
     engine run on a synthetic gap in dev — see git history / session log
     if reproduced). Every reported config states its gap-adjusted train+
     val expectancy ALONGSIDE the raw engine number, plus how many trades
     were touched.

COSTS — TradFi assumption, stated explicitly (commission-free ETFs, tight
NYSE-Arca spreads on all four):
  ETF_COSTS   (GLD/USO/QQQ/SPY): fee 1.0bp (maker=taker, no discount
              structure worth modeling) + 0.5bp half-spread + 0.5bp
              slippage => TAKER round trip = 2*(1.0+0.5+0.5) = 4.0 bps.
  FUT_COSTS   (GC=F/CL=F, robustness only): fee 0.5bp + 0.25bp half-spread
              + 0.25bp slippage => TAKER round trip = 2.0 bps (mandate's
              "2bp round trip" for futures, hit exactly).
  No funding series exists for any of these (no perpetual funding market).
  Per the mandate: passing funding_series=None would make backtest.py fall
  back to CostModel's conservative flat "always pay" funding charge, which
  is a REAL crypto-perp mechanic these markets do not have — so we pass an
  explicit all-zero funding_series instead, which correctly zeroes the
  funding leg while leaving every other cost honest.

GAUNTLET — same discipline as step43/45b: chronological 60/20/20 computed
via split_points() over each market's NEWS-SPAN-SLICED 1h frame (news
span +/- 24h buffer, same convention as step45b). Only (0,i_tr) [train]
and (i_tr,i_va) [val] are ever passed to run_backtest. The final 20% slice
is never sliced, run, or looked at — the lead agent spends sealed looks,
not this script.
"""

import os

import numpy as np
import pandas as pd
import yfinance as yf

from backtest import CostModel, run_backtest
from step7_deep_search import fetch_bybit_deep
from step43_daytrade import (MIN_TRAIN_TRADES, MIN_VAL_TRADES, mk_row,
                             split_points, verdict_for)
from step45b_news_events import align_events, classify_frame, event_study
from strategy import atr

pd.set_option("display.width", 160)

CACHE_TMPL = "data_news_mkts_{sym}.parquet"
NEWS_PATH = "data_watcherguru_history.parquet"

ETF_SYMBOLS = ["GLD", "USO", "QQQ", "SPY"]        # gold, oil, nasdaq, s&p
FUT_SYMBOLS = ["GC=F", "CL=F"]                     # futures robustness checks
ALL_SYMBOLS = ETF_SYMBOLS + FUT_SYMBOLS

SESSION_GAP_THRESHOLD_MIN = 75   # see session_offhours_mask() docstring

ETF_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.5,
                       slippage_bps=0.5, funding_bps_8h=0.0)
FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.25, half_spread_bps=0.25,
                       slippage_bps=0.25, funding_bps_8h=0.0)

FIXED_STOPS = [0.5, 0.8, 1.2]           # owner-given candidates
TARGET_MULT = (2.0, 3.0)                # owner-given, x stop
WALLCLOCK_HOLD_H = 24                   # owner-given ceiling


# ===========================================================================
# PHASE 1 — DATA: fetch + normalize + cache
# ===========================================================================

def fetch_market(sym, cache_path, period="730d", interval="1h"):
    """One symbol's 1h bars, normalized to timestamp(UTC tz-aware)/OHLCV.
    Cached to `cache_path`; a second run makes zero network calls."""
    if os.path.exists(cache_path):
        df = pd.read_parquet(cache_path)
        print(f"  {sym}: {len(df)} bars from cache ({cache_path})")
        return df

    raw = yf.Ticker(sym).history(period=period, interval=interval,
                                 auto_adjust=False)
    if raw.empty:
        raise RuntimeError(f"yfinance returned no data for {sym!r}")

    # yfinance quirk #1: some code paths return MultiIndex columns
    # (ticker, field) even for a single symbol. Flatten defensively.
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(-1)

    raw = raw.reset_index()
    ts_col = "Datetime" if "Datetime" in raw.columns else "Date"
    ts = pd.DatetimeIndex(raw[ts_col])
    # yfinance quirk #2: intraday index comes back tz-aware in the
    # EXCHANGE's local tz (America/New_York), not UTC. Convert explicitly;
    # every other file in this repo assumes UTC tz-aware timestamps.
    ts = ts.tz_localize("UTC") if ts.tz is None else ts.tz_convert("UTC")

    df = (pd.DataFrame({
            "timestamp": ts,
            "open": raw["Open"].astype(float),
            "high": raw["High"].astype(float),
            "low": raw["Low"].astype(float),
            "close": raw["Close"].astype(float),
            "volume": raw["Volume"].astype(float),
          })
          .dropna(subset=["open", "high", "low", "close"])
          .drop_duplicates(subset="timestamp")
          .sort_values("timestamp")
          .reset_index(drop=True))
    df.to_parquet(cache_path)
    print(f"  {sym}: fetched {len(df)} bars fresh, cached -> {cache_path}")
    return df


def report_span(sym, df):
    span_days = (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days
    # missing-bar honesty: median cadence vs the biggest gaps observed
    dt_min = df["timestamp"].diff().dt.total_seconds().dropna() / 60
    print(f"  {sym}: {len(df)} bars | {df['timestamp'].iloc[0]:%Y-%m-%d %H:%M} "
          f"-> {df['timestamp'].iloc[-1]:%Y-%m-%d %H:%M} UTC ({span_days}d) | "
          f"median gap {dt_min.median():.0f}min, max gap "
          f"{dt_min.max() / 60:.1f}h, {len(dt_min[dt_min > 180])} gaps >3h")


# ===========================================================================
# PHASE 2 — SESSION vs OFF-HOURS classification (the honest split)
# ===========================================================================

def session_offhours_mask(d, event_ts, trading_idx, valid,
                           threshold_min=SESSION_GAP_THRESHOLD_MIN):
    """An event is SESSION if the first tradable bar's OPEN arrives within
    `threshold_min` minutes of the event (the market was live, caught it on
    the very next normal ~60min print). It is OFF-HOURS if the wait is
    longer (overnight close, weekend, or a futures maintenance break) — the
    "reaction" measured there is really an overnight/weekend gap-open, a
    different animal from a live in-session move, and the mandate demands
    they never be blurred together. threshold_min=75 sits comfortably above
    the ~60min normal bar cadence (both ETFs and the two futures print
    hourly) while safely catching the >=2h maintenance/close gaps as
    off-hours. This is an EMPIRICAL split (no holiday calendar hardcoded);
    the one known blind spot is stated in results.md."""
    n = len(d)
    idx_safe = np.clip(trading_idx, 0, n - 1)
    bar_open = d["timestamp"].to_numpy()[idx_safe]
    ev = pd.DatetimeIndex(event_ts).to_numpy()
    gap_min = (pd.DatetimeIndex(bar_open) - pd.DatetimeIndex(ev)).total_seconds() / 60
    session = valid & (gap_min >= 0) & (gap_min <= threshold_min)
    offhours = valid & ~session
    return session, offhours, gap_min


# ===========================================================================
# PHASE 3 — signal construction (WALL-CLOCK holds, not bar-count holds —
# the crypto day_trade_signal's max_hold_bars is the wrong tool here: a
# QQQ "24h" of bar-count would actually span ~3.4 TRADING DAYS since only
# 7 bars print per session day. These two variants are honest wall-clock.)
# ===========================================================================

def make_bool_array(n, idxs):
    arr = np.zeros(n, dtype=bool)
    idxs = np.asarray(idxs)
    idxs = idxs[(idxs >= 0) & (idxs < n)]
    arr[idxs] = True
    return pd.Series(arr)


def day_trade_signal_wallclock(d, enter_long, enter_short, max_hold_hours):
    """Same event-entry / timed-exit shape as step43's day_trade_signal,
    but the exit clock is REAL ELAPSED TIME since entry, not a bar count —
    the correct tool for a market with session gaps."""
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    times = pd.DatetimeIndex(d["timestamp"])
    limit = pd.Timedelta(hours=max_hold_hours)
    out, pos, entry_t = [], 0.0, None
    for i in range(len(d)):
        if pos == 0.0:
            if el[i]:
                pos, entry_t = 1.0, times[i]
            elif es[i]:
                pos, entry_t = -1.0, times[i]
        elif (times[i] - entry_t) >= limit:
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


def day_trade_signal_session_close(d, enter_long, enter_short):
    """Never carry a position overnight: force flat by the LAST bar of the
    session day a position was already held into (checked against the
    calendar date of the NEXT bar — legitimate boundary information, known
    from the public trading calendar, not a price lookahead). A position
    opened ON a day's own final bar is, by construction, allowed to run
    through that next session before its first force-flat check fires
    (force-closing the very bar it opened on would erase the entry) —
    stated plainly as this variant's one approximation."""
    el = enter_long.fillna(False).to_numpy(dtype=bool)
    es = enter_short.fillna(False).to_numpy(dtype=bool)
    days = pd.DatetimeIndex(d["timestamp"]).normalize().to_numpy()
    n = len(d)
    is_last_of_day = np.zeros(n, dtype=bool)
    for i in range(n):
        if i == n - 1 or days[i + 1] != days[i]:
            is_last_of_day[i] = True
    out, pos = [], 0.0
    for i in range(n):
        if pos == 0.0:
            if el[i]:
                pos = 1.0
            elif es[i]:
                pos = -1.0
        elif is_last_of_day[i]:
            pos = 0.0
        out.append(pos)
    return pd.Series(out, index=d.index)


# ===========================================================================
# PHASE 4 — scoring (costs-parameterized; zero funding_series) + GAP HONESTY
# ===========================================================================

def score(d, sig, i_tr, i_va, costs, stop_pct=None, target_pct=None,
         execution="maker"):
    zero_fund = pd.Series(0.0, index=d.index)

    def run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            costs=costs, execution=execution,
            funding_series=zero_fund.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return run(0, i_tr), run(i_tr, i_va)


def gap_adjust(d, trades, stop_pct, costs):
    """For every trade that exited via the engine's intra-bar hard stop
    (identified by matching its exit_price to the EXACT theoretical
    stop-fill price computed from that trade's own known entry_price/
    stop_pct — target-hits and forced-flat exits use a different formula
    and are never misclassified), check whether the exit bar's OPEN had
    already gapped through the stop level. If so, the engine's stop-price
    fill is fiction; recompute the honest fill AT that bar's open (worse),
    using the exact same cash/fee arithmetic backtest.py's execute() uses
    for a real taker exit — verified byte-for-byte against a direct engine
    run on a synthetic gap during development.
    Returns (adjusted_pnls: list[float] same order as `trades`,
    gap_count: int, total_dollar_delta: float)."""
    if not trades or stop_pct is None:
        return [t.pnl for t in trades], 0, 0.0
    idx_map = {t: i for i, t in enumerate(pd.DatetimeIndex(d["timestamp"]))}
    opens = d["open"].to_numpy()
    adjusted, gap_count, total_delta = [], 0, 0.0
    for tr in trades:
        if tr.direction == 1:
            stop_price = tr.entry_price * (1 - stop_pct / 100)
            stop_fill = stop_price * (1 - costs._adverse_frac)
        else:
            stop_price = tr.entry_price * (1 + stop_pct / 100)
            stop_fill = stop_price * (1 + costs._adverse_frac)
        is_stop_exit = abs(tr.exit_price - stop_fill) <= 1e-6 * max(1.0, abs(stop_fill))
        i = idx_map.get(tr.exit_time)
        if not is_stop_exit or i is None:
            adjusted.append(tr.pnl)
            continue
        bar_open = opens[i]
        gapped = (bar_open < stop_price) if tr.direction == 1 else (bar_open > stop_price)
        if not gapped:
            adjusted.append(tr.pnl)
            continue
        side = -1 if tr.direction == 1 else 1
        fill_new = costs.fill_price(bar_open, side)
        signed_units = tr.direction * tr.units
        fee_old = costs.fee(tr.units * stop_fill)
        fee_new = costs.fee(tr.units * fill_new)
        delta = signed_units * (fill_new - stop_fill) - (fee_new - fee_old)
        adjusted.append(tr.pnl + delta)
        gap_count += 1
        total_delta += delta
    return adjusted, gap_count, total_delta


# ===========================================================================
# PHASE 5 — stop candidates (owner-fixed + ATR-scaled per market)
# ===========================================================================

def stop_candidates_for(d, i_tr):
    """Owner-given fixed stops {0.5, 0.8, 1.2}% UNION two ATR-scaled
    candidates (0.75x / 1.25x each market's TRAIN-only median 1h ATR%) —
    TradFi vol is lower than crypto, so the fixed BTC-tuned stops may all
    sit too wide; the ATR-scaled pair lets each market propose its own
    natural stop distance. Deduped (candidates within 0.05% of each other
    collapse to one), clipped to a sane [0.15%, 2.0%] band."""
    atr_pct = atr(d, 14) / d["close"] * 100
    med_atr = float(atr_pct.iloc[:i_tr].dropna().median())
    raw = FIXED_STOPS + [round(0.75 * med_atr, 2), round(1.25 * med_atr, 2)]
    cands = []
    for c in raw:
        c = max(0.15, min(2.0, c))
        if not any(abs(c - x) < 0.05 for x in cands):
            cands.append(round(c, 2))
    return sorted(cands), med_atr


# ===========================================================================
# PHASE 6 — per-market pipeline
# ===========================================================================

TAG_NAMES = ("ALL_RELEVANT", "BULLISH", "BEARISH", "NEUTRAL", "MIXED")


def tag_masks_for(relevant):
    return {
        "ALL_RELEVANT": (relevant["tag"] == relevant["tag"]),
        "BULLISH": relevant["tag"] == "BULLISH",
        "BEARISH": relevant["tag"] == "BEARISH",
        "NEUTRAL": relevant["tag"] == "NEUTRAL",
        "MIXED": relevant["tag"] == "MIXED",
    }


def run_market(sym, d_full, news, costs, session_close_variant, label):
    """Full per-market pipeline: slice to news span, event study
    (pooled + session-only), strategy grid (pooled + session-only),
    gap-adjustment on every stop-exit. Returns a dict of DataFrames/values
    for the results writer."""
    print(f"\n{'=' * 78}\n{label} ({sym})\n{'=' * 78}")

    relevant_all = news[news["relevant"]]
    news_min = relevant_all["utc_timestamp"].min() - pd.Timedelta(hours=24)
    news_max = relevant_all["utc_timestamp"].max() + pd.Timedelta(hours=24)
    mask = (d_full["timestamp"] >= news_min) & (d_full["timestamp"] <= news_max)
    d = d_full[mask].reset_index(drop=True)
    if len(d) < 50:
        print(f"  INSUFFICIENT MARKET DATA in news span ({len(d)} bars) — skipping.")
        return None

    n, i_tr, i_va = split_points(d)
    print(f"  news-span-sliced frame: {n} bars, {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
          f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed, {n - i_va} bars untouched)")

    stop_list, med_atr = stop_candidates_for(d, i_tr)
    print(f"  TRAIN median 1h ATR% = {med_atr:.3f}%  ->  stop candidates used: {stop_list}%")

    floor_idx, trading_idx, valid = align_events(d, relevant_all["utc_timestamp"])
    session_mask, offhours_mask, gap_min = session_offhours_mask(
        d, relevant_all["utc_timestamp"], trading_idx, valid)
    n_valid = int(valid.sum())
    n_session = int(session_mask.sum())
    n_offhours = int(offhours_mask.sum())
    print(f"  relevant events aligned into this span: {n_valid} "
          f"(SESSION: {n_session} [{n_session / max(n_valid,1) * 100:.1f}%], "
          f"OFF-HOURS: {n_offhours} [{n_offhours / max(n_valid,1) * 100:.1f}%])")

    horizons_bars = {"1h": 1, "4h": 4}
    tag_masks = tag_masks_for(relevant_all)

    study_pooled = event_study(d, trading_idx, valid, tag_masks, horizons_bars)
    study_pooled.insert(0, "split", "pooled")
    study_session = event_study(d, trading_idx, session_mask, tag_masks, horizons_bars)
    study_session.insert(0, "split", "session-only")
    study_off = event_study(d, trading_idx, offhours_mask, tag_masks, horizons_bars)
    study_off.insert(0, "split", "off-hours-only")
    study = pd.concat([study_pooled, study_session, study_off], ignore_index=True)
    study.insert(0, "market", sym)
    print("\n  --- EVENT STUDY ---")
    print(study.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    # --- strategy grid: A-news-momentum / B-news-fade, FIRST-BAR-MOVE
    # direction (the ONLY direction convention that survived BTC's own
    # sealed test in round 45B/45B-addendum — keyword direction failed
    # there, so this grid does not re-spend budget re-testing it here) ---
    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    trad_rel_all = trading_idx[valid]
    trad_rel_all = trad_rel_all[trad_rel_all < len(d)]
    move_sign_all = np.sign(closes[trad_rel_all] - opens[trad_rel_all])
    trad_rel_sess = trading_idx[session_mask]
    trad_rel_sess = trad_rel_sess[trad_rel_sess < len(d)]
    move_sign_sess = np.sign(closes[trad_rel_sess] - opens[trad_rel_sess])

    variants = {
        "pooled": (trad_rel_all[move_sign_all > 0], trad_rel_all[move_sign_all < 0]),
        "session-only": (trad_rel_sess[move_sign_sess > 0], trad_rel_sess[move_sign_sess < 0]),
    }

    hold_variants = [("wallclock24h", WALLCLOCK_HOLD_H)]
    if session_close_variant:
        hold_variants.append(("session_close", None))

    rows = []
    for split_label, (up_idx, down_idx) in variants.items():
        el_mom = make_bool_array(n, up_idx)
        es_mom = make_bool_array(n, down_idx)
        el_fade = make_bool_array(n, down_idx)
        es_fade = make_bool_array(n, up_idx)
        n_note = f"n_up={len(up_idx)} n_down={len(down_idx)}"
        if len(up_idx) == 0 and len(down_idx) == 0:
            rows.append({"market": sym, "split": split_label, "family": "A/B",
                         "config": f"NO EVENTS ({n_note})", "tf": "1h",
                         "stop%": None, "target%": None, "max_hold_h": None,
                         "tr_n": 0, "tr_exp": 0, "va_n": 0, "va_exp": 0,
                         "gap_adj_n": 0, "tr_exp_gapadj": 0, "va_exp_gapadj": 0,
                         "verdict": "NO-EVENTS", "verdict_gapadj": "NO-EVENTS"})
            continue
        for family, el, es in (("A-news-momentum", el_mom, es_mom),
                               ("B-news-fade", el_fade, es_fade)):
            for stop_pct in stop_list:
                for tmult in TARGET_MULT:
                    target_pct = stop_pct * tmult
                    for hold_label, hold_h in hold_variants:
                        if hold_label == "session_close":
                            sig = day_trade_signal_session_close(d, el, es)
                        else:
                            sig = day_trade_signal_wallclock(d, el, es, hold_h)
                        tr, va = score(d, sig, i_tr, i_va, costs,
                                      stop_pct=stop_pct, target_pct=target_pct)
                        row = mk_row(family,
                                     f"stop{stop_pct:.2f}% tgt{tmult:.0f}x "
                                     f"hold={hold_label} ({n_note})",
                                     "1h", tr, va, stop_pct, target_pct, hold_label)
                        adj_tr, gap_tr, delta_tr = gap_adjust(d, tr.trades, stop_pct, costs)
                        adj_va, gap_va, delta_va = gap_adjust(d, va.trades, stop_pct, costs)
                        row["gap_adj_n"] = gap_tr + gap_va
                        row["gap_adj_delta_$"] = delta_tr + delta_va
                        row["tr_exp_gapadj"] = float(np.mean(adj_tr)) if adj_tr else 0.0
                        row["va_exp_gapadj"] = float(np.mean(adj_va)) if adj_va else 0.0
                        row["verdict_gapadj"] = (
                            "SURVIVOR" if (row["tr_exp_gapadj"] > 0 and row["va_exp_gapadj"] > 0
                                          and row["tr_n"] >= MIN_TRAIN_TRADES
                                          and row["va_n"] >= MIN_VAL_TRADES)
                            else ("INSUFFICIENT-SAMPLE" if (row["tr_exp_gapadj"] > 0 and row["va_exp_gapadj"] > 0)
                                  else "FAIL"))
                        row["market"] = sym
                        row["split"] = split_label
                        rows.append(row)

    grid = pd.DataFrame(rows)
    print(f"\n  --- STRATEGY GRID: {len(grid)} configs ---")
    print(grid["verdict"].value_counts().to_string())
    survivors = grid[grid["verdict"] == "SURVIVOR"]
    print(f"  SURVIVORS (raw engine numbers): {len(survivors)}")
    if len(survivors):
        cols = ["split", "family", "config", "tr_n", "tr_exp", "va_n", "va_exp",
               "gap_adj_n", "tr_exp_gapadj", "va_exp_gapadj", "verdict_gapadj"]
        print(survivors[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    return {"symbol": sym, "d": d, "i_tr": i_tr, "i_va": i_va, "med_atr": med_atr,
            "stop_list": stop_list, "n_valid": n_valid, "n_session": n_session,
            "n_offhours": n_offhours, "study": study, "grid": grid,
            "span": (d["timestamp"].iloc[0], d["timestamp"].iloc[-1], n)}


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("PHASE 1 — DATA: fetch + normalize 1h bars for all 6 symbols")
    print("=" * 78)
    market_data = {}
    for sym in ALL_SYMBOLS:
        cache_path = CACHE_TMPL.format(sym=sym)
        df = fetch_market(sym, cache_path)
        market_data[sym] = df
        report_span(sym, df)

    print("\nLoading WatcherGuru news cache + classifying (deterministic keywords)...")
    news_raw = pd.read_parquet(NEWS_PATH)
    news = classify_frame(news_raw)
    relevant = news[news["relevant"]]
    print(f"  {len(news)} total posts | relevant: {len(relevant)} "
          f"({len(relevant) / len(news) * 100:.1f}%) | "
          f"span {news['utc_timestamp'].min():%Y-%m-%d} -> "
          f"{news['utc_timestamp'].max():%Y-%m-%d}")
    print("  tag distribution (relevant only):")
    print(relevant["tag"].value_counts().to_string())

    print("\n" + "=" * 78)
    print("COST FLOOR")
    print("=" * 78)
    print(f"  ETF_COSTS  taker round trip: {ETF_COSTS.round_trip_bps():.1f} bps "
          f"(fee 1.0bp x2 + spread/slip 1.0bp x2)")
    print(f"  FUT_COSTS  taker round trip: {FUT_COSTS.round_trip_bps():.1f} bps "
          f"(fee 0.5bp x2 + spread/slip 0.5bp x2)")

    print("\n" + "=" * 78)
    print("BTC REFERENCE — recomputed fresh on the CURRENT (larger) news cache,")
    print("for an exact apples-to-apples comparison. Round 45B logged 1.33x on")
    print("an earlier, smaller cache (674 posts) — a slightly different number")
    print("here is expected and does not contradict that finding.")
    print("=" * 78)
    btc = fetch_bybit_deep("1h", "BTCUSDT")
    news_min = relevant["utc_timestamp"].min() - pd.Timedelta(hours=24)
    news_max = relevant["utc_timestamp"].max() + pd.Timedelta(hours=24)
    btc_d = btc[(btc["timestamp"] >= news_min) & (btc["timestamp"] <= news_max)].reset_index(drop=True)
    floor_b, trad_b, valid_b = align_events(btc_d, relevant["utc_timestamp"])
    btc_study = event_study(btc_d, trad_b, valid_b, tag_masks_for(relevant), {"1h": 1, "4h": 4})
    btc_study.insert(0, "market", "BTC (reference)")
    print(btc_study.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\n" + "=" * 78)
    print("PHASE 2-6 — PER-MARKET EVENT STUDY + STRATEGY GRID")
    print("=" * 78)
    results = {}
    for sym in ETF_SYMBOLS:
        results[sym] = run_market(sym, market_data[sym], news, ETF_COSTS,
                                  session_close_variant=True, label="ETF")
    for sym in FUT_SYMBOLS:
        results[sym] = run_market(sym, market_data[sym], news, FUT_COSTS,
                                  session_close_variant=False, label="FUTURES (robustness)")

    print("\n" + "=" * 78)
    print("THE MONEY TABLE — ALL_RELEVANT, 1h horizon, ratio_vs_baseline")
    print("=" * 78)
    money_rows = []
    btc_1h_all = btc_study[(btc_study["horizon"] == "1h") & (btc_study["tag"] == "ALL_RELEVANT")]
    money_rows.append({"market": "BTC (reference)", "split": "pooled",
                       "n_events": int(btc_1h_all["n_events"].iloc[0]),
                       "ratio_vs_baseline": float(btc_1h_all["ratio_vs_baseline"].iloc[0])})
    for sym, res in results.items():
        if res is None:
            continue
        st = res["study"]
        for split in ("pooled", "session-only", "off-hours-only"):
            row = st[(st["horizon"] == "1h") & (st["tag"] == "ALL_RELEVANT") & (st["split"] == split)]
            if len(row):
                money_rows.append({"market": sym, "split": split,
                                   "n_events": int(row["n_events"].iloc[0]),
                                   "ratio_vs_baseline": float(row["ratio_vs_baseline"].iloc[0])})
    money = pd.DataFrame(money_rows)
    print(money.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\n" + "=" * 78)
    print("ALL SURVIVORS ACROSS ALL MARKETS (raw engine numbers; gap-adjusted")
    print("expectancy shown alongside — NONE of these are sealed-test results,")
    print("only train+val gauntlet survivors awaiting a lead-agent sealed look)")
    print("=" * 78)
    all_survivors = []
    for sym, res in results.items():
        if res is None:
            continue
        surv = res["grid"][res["grid"]["verdict"] == "SURVIVOR"].copy()
        if len(surv):
            all_survivors.append(surv)
    if all_survivors:
        all_surv_df = pd.concat(all_survivors, ignore_index=True)
        cols = ["market", "split", "family", "config", "tr_n", "tr_exp", "va_n",
               "va_exp", "gap_adj_n", "tr_exp_gapadj", "va_exp_gapadj", "verdict_gapadj"]
        print(all_surv_df[cols].to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    else:
        all_surv_df = pd.DataFrame()
        print("  NONE.")

    return {"market_data": market_data, "news": news, "btc_study": btc_study,
            "results": results, "money": money, "all_survivors": all_surv_df}


if __name__ == "__main__":
    main()
