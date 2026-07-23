"""
step45b_news_events.py — round 45b: the FIRST NEWS-EVENT dataset and the
first news-driven day-trade backtest. A family no candle backtest can see:
the owner's trusted feed is the WatcherGuru Telegram channel
(https://t.me/s/WatcherGuru), and this script asks whether that feed
carries tradeable energy at all before ever proposing a strategy.

Run:  python3 step45b_news_events.py

Research only. Touches ONLY:
  - step45b_news_events.py   (this file)
  - data_watcherguru_history.parquet   (harvested headline cache)
  - step45b_results.md       (written by hand from this script's output)
No live orders, no commits, no other repo file is written or modified.

THREE PHASES
  1. HARVEST  — scrape https://t.me/s/WatcherGuru's public preview,
     walking backward with the `before=<message_id>` param, caching
     incrementally so a crash never loses progress. Polite: 2-3s sleep
     between requests, a standard browser User-Agent, real retry/backoff.
  2. CLASSIFY — a pure, deterministic (NO LLM) keyword function tagging
     each headline (a) relevant to BTC/macro or not, and (b) crude
     direction BULLISH / BEARISH / MIXED / NEUTRAL. Kept as a standalone
     pure function (`classify_headline`) so the live bot can import and
     reuse it verbatim later.
  3. BACKTEST — align every relevant headline to the NEXT tradeable bar
     (fanatically no-lookahead — see `align_events`), run an EVENT STUDY
     (the scientific core: does |move| after news exceed the unconditional
     baseline?) and then two strategy families (NEWS MOMENTUM, NEWS FADE)
     through the same GAUNTLET discipline as step43_daytrade.py: chrono
     60/20/20 of the NEWS SAMPLE's span, full costs via backtest.py's
     CostModel, survivor bar reused verbatim from step43_daytrade.score() /
     verdict_for() (>=30 train / >=8 val trades, positive both). If the
     harvested span can't clear the floor, configs are marked
     INSUFFICIENT-SAMPLE rather than the bar being lowered.

COST FLOOR (stated explicitly per the mandate, esp. for 15m configs):
  CostModel taker round trip = 2 * (6 + 1 + 2) = 18 bps  (fee+spread+slip,
    both fills at worst case)
  CostModel best-case maker round trip = 2 * 2 = 4 bps (both fills rest
    passively and get touched)
  Prior rounds' (step41/step43) REALIZED blended maker/chase cost on real
  day-trade signal shapes: ~9 bps round trip. That 9bps figure — not the
  4bps best case — is the number every config below must clear before it
  earns a cent, and it is why 15m (smaller average moves per bar) has
  historically been the hardest resolution to clear (step43's 4th
  confirmation of the "15m below cost floor" finding).
"""

import os
import random
import time

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from backtest import CostModel
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (HARD_STOP_CAP, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
                             day_trade_signal, hours_to_bars, mk_row, score,
                             split_points, verdict_for)

CACHE_PATH = "data_watcherguru_history.parquet"
BASE_URL = "https://t.me/s/WatcherGuru"
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

TARGET_SPAN_DAYS = 400        # "12+ months" with a little headroom
MAX_PAGES = 650                # safety cap; ~16-17 posts/page observed
CHECKPOINT_EVERY = 15          # pages between incremental parquet saves
SLEEP_RANGE = (2.0, 3.0)       # polite delay between requests, seconds


# ===========================================================================
# PHASE 1 — HARVEST
# ===========================================================================

def fetch_page(session, before_id=None, retries=4):
    """One GET against the public preview, with backoff retries. Returns
    the HTML text, or None if every retry failed (network/blocking)."""
    url = BASE_URL if before_id is None else f"{BASE_URL}?before={before_id}"
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                return r.text
            print(f"    HTTP {r.status_code} on attempt {attempt + 1}/{retries}, "
                  f"retrying...")
        except requests.RequestException as e:
            print(f"    request error on attempt {attempt + 1}/{retries}: {e}")
        time.sleep(5 * (attempt + 1))
    return None


def parse_page(html):
    """Extract (message_id, utc_timestamp, text) for every post block on
    one preview page. Robust to media-only posts (empty text kept, not
    dropped — classification will simply find no keywords in them)."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for msg in soup.select("div.tgme_widget_message[data-post]"):
        post = msg.get("data-post", "")
        try:
            msg_id = int(post.split("/")[-1])
        except ValueError:
            continue
        time_tag = msg.select_one("time[datetime]")
        if time_tag is None or not time_tag.get("datetime"):
            continue
        ts = pd.Timestamp(time_tag["datetime"])
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        text_div = msg.select_one("div.tgme_widget_message_text")
        text = text_div.get_text(" ", strip=True) if text_div else ""
        out.append({"message_id": msg_id, "utc_timestamp": ts, "text": text})
    return out


def _save(rows_dict, path):
    df = (pd.DataFrame(list(rows_dict.values()))
          .sort_values("utc_timestamp").reset_index(drop=True))
    df.to_parquet(path)
    return df


def harvest_history(cache_path=CACHE_PATH, target_days=TARGET_SPAN_DAYS,
                     max_pages=MAX_PAGES, sleep_range=SLEEP_RANGE,
                     checkpoint_every=CHECKPOINT_EVERY):
    """Walk https://t.me/s/WatcherGuru backward via `before=<msg_id>`,
    caching incrementally. Resumable: if `cache_path` already exists and
    already spans >= target_days, no network calls are made at all."""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT,
                             "Accept-Language": "en-US,en;q=0.9"})

    all_rows = {}
    if os.path.exists(cache_path):
        existing = pd.read_parquet(cache_path)
        for r in existing.itertuples(index=False):
            all_rows[int(r.message_id)] = {
                "message_id": int(r.message_id),
                "utc_timestamp": r.utc_timestamp, "text": r.text,
            }
        print(f"Resuming from cache: {len(all_rows)} posts already harvested.")

    if all_rows:
        oldest_ts = min(r["utc_timestamp"] for r in all_rows.values())
        newest_ts = max(r["utc_timestamp"] for r in all_rows.values())
        span_days = (newest_ts - oldest_ts).total_seconds() / 86400
        print(f"  cached span: {span_days:.1f} days "
              f"({oldest_ts:%Y-%m-%d} -> {newest_ts:%Y-%m-%d})")
        if span_days >= target_days:
            print("  cache already meets target span — skipping network harvest.")
            return (pd.DataFrame(list(all_rows.values()))
                    .sort_values("utc_timestamp").reset_index(drop=True), None)
        before_id = min(all_rows)
    else:
        before_id = None

    page_count, stall_count, limitation = 0, 0, None
    while page_count < max_pages:
        html = fetch_page(session, before_id)
        if html is None:
            limitation = (f"network/blocking failure after retries at page "
                          f"{page_count + 1} (before={before_id})")
            print(f"  STOPPING: {limitation}")
            break

        rows = parse_page(html)
        page_count += 1
        if not rows:
            limitation = (f"empty page at page {page_count} "
                          f"(before={before_id}) — likely reached channel start")
            print(f"  {limitation}")
            break

        new_ids = sum(1 for row in rows if row["message_id"] not in all_rows)
        for row in rows:
            all_rows[row["message_id"]] = row

        page_min_id = min(r["message_id"] for r in rows)
        if before_id is not None and page_min_id >= before_id:
            stall_count += 1
            if stall_count >= 2:
                limitation = "pagination stalled (before= stopped advancing)"
                print(f"  STOPPING: {limitation}")
                break
        else:
            stall_count = 0
        before_id = page_min_id

        cur_oldest = min(r["utc_timestamp"] for r in all_rows.values())
        cur_newest = max(r["utc_timestamp"] for r in all_rows.values())
        span_days = (cur_newest - cur_oldest).total_seconds() / 86400
        if page_count % 10 == 0 or new_ids == 0:
            print(f"  page {page_count}: before={before_id}, +{new_ids} new, "
                  f"total={len(all_rows)}, span={span_days:.1f}d, "
                  f"back to {cur_oldest:%Y-%m-%d}")

        if page_count % checkpoint_every == 0:
            _save(all_rows, cache_path)
            print(f"    [checkpoint saved: {len(all_rows)} posts]")

        if span_days >= target_days:
            print(f"  Reached target span ({span_days:.1f} >= {target_days}d). "
                  f"Stopping harvest.")
            break

        time.sleep(random.uniform(*sleep_range))

    if page_count >= max_pages and limitation is None:
        limitation = f"hit max_pages safety cap ({max_pages}) before target span"
        print(f"  STOPPING: {limitation}")

    df = _save(all_rows, cache_path)
    span = (df["utc_timestamp"].max() - df["utc_timestamp"].min())
    print(f"\nHarvest complete: {len(df)} posts, "
          f"{df['utc_timestamp'].min():%Y-%m-%d} -> "
          f"{df['utc_timestamp'].max():%Y-%m-%d} ({span.days} days)")
    if limitation:
        print(f"LIMITATION: {limitation}")
    return df, limitation


# ===========================================================================
# PHASE 2 — CLASSIFY (deterministic keywords, no LLM — a live-reusable
# pure function)
# ===========================================================================

RELEVANCE_KEYWORDS = [
    # crypto-native
    "bitcoin", "btc", "crypto", "ethereum", "eth", "altcoin", "stablecoin",
    "defi", "nft", "binance", "coinbase", "microstrategy", "ripple", "xrp",
    "solana", "dogecoin", "satoshi", "blockchain", "mining", "halving",
    "wallet", "exchange hack", "el salvador",
    # macro / policy that historically moves BTC
    "sec", "etf", "fed", "federal reserve", "powell", "rate cut", "rate hike",
    "interest rate", "inflation", "cpi", "jobs report", "unemployment", "gdp",
    "recession", "tariff", "treasury", "yields", "yellen", "imf",
    # politics / geopolitics that historically moves risk assets
    "trump", "biden", "election", "congress", "senate", "sanctions", "war",
    "china", "russia", "ukraine", "israel",
    # market-structure events
    "liquidat", "hack", "hacked", "bankrupt", "lawsuit", "fraud", "ban",
    "seize", "seized", "subpoena", "indict", "default", "blackrock",
    # broad markets (WatcherGuru covers these alongside crypto)
    "gold", "oil price", "stock market", "wall street", "nasdaq", "s&p",
    "dow jones", "dollar",
]

BULLISH_KEYWORDS = [
    "etf approved", "approves etf", "approves spot", "spot etf approval",
    "buys bitcoin", "adopts bitcoin", "accumulates bitcoin", "adds bitcoin",
    "legal tender", "all-time high", "all time high", "record high",
    "rate cut", "cuts rates", "pardon", "pardons", "stimulus",
    "strategic reserve", "unveils bitcoin", "launches bitcoin etf",
    "net inflows", "inflow", "surges", "soars", "rally", "rallies",
    "adoption", "integrates bitcoin", "accepts bitcoin", "bull market",
    "upgrade", "raises price target", "approves bitcoin",
]

BEARISH_KEYWORDS = [
    "sec sues", "sec charges", "files lawsuit", "hacked", "hack", "exploit",
    "exploited", "bankrupt", "bankruptcy", "chapter 11",
    "files for bankruptcy", "ban on", "bans crypto", "banned", "rate hike",
    "hikes rates", "liquidated", "liquidation", "liquidations", "crash",
    "crashes", "plunge", "plunges", "tumbles", "sinks", "tariff", "tariffs",
    "sanctions", "war", "fraud", "ponzi", "collapse", "collapses", "outage",
    "halts trading", "delist", "delists", "seized", "seizes", "arrested",
    "indicted", "subpoena", "freezes", "frozen", "default", "selloff",
    "sell-off", "dump", "dumps", "warns", "recession", "downgrade",
    "lowers price target",
]


def classify_headline(text: str) -> dict:
    """Pure, deterministic classifier — no LLM, no network, no state.
    Returns relevance (bool) and a crude direction tag. Kept standalone so
    the live Situation Room can `from step45b_news_events import
    classify_headline` and reuse this exact logic on live headlines.

    Tie-break: a headline matching BOTH bullish and bearish keyword lists
    is tagged MIXED (e.g. "SEC sues over ETF approval") rather than forced
    either way — an honest admission the keyword approach can't resolve it.
    """
    t = (text or "").lower()
    bull_hits = [kw for kw in BULLISH_KEYWORDS if kw in t]
    bear_hits = [kw for kw in BEARISH_KEYWORDS if kw in t]
    relevant = any(kw in t for kw in RELEVANCE_KEYWORDS)
    if bull_hits and bear_hits:
        tag = "MIXED"
    elif bear_hits:
        tag = "BEARISH"
    elif bull_hits:
        tag = "BULLISH"
    else:
        tag = "NEUTRAL"
    return {"relevant": relevant, "tag": tag,
            "bull_hits": bull_hits, "bear_hits": bear_hits}


def classify_frame(news):
    tags = news["text"].apply(classify_headline)
    out = news.copy()
    out["relevant"] = tags.apply(lambda x: x["relevant"])
    out["tag"] = tags.apply(lambda x: x["tag"])
    return out


# ===========================================================================
# PHASE 3 — ALIGNMENT + EVENT STUDY + BACKTEST
# ===========================================================================

def align_events(candles, event_ts):
    """No-lookahead alignment, fanatically.

    floor_idx = index of the LAST candle bar whose open <= event time. This
    is the bar that was live (or had already closed) when the headline hit
    — by the time THIS bar closes, the news is already public knowledge.
    trading_idx = floor_idx + 1 = the first bar whose entire life happens
    strictly after the event became known — the earliest bar a trader
    could actually be filled on. A 14:07 event on 15m bars: floor_idx is
    the 14:00 bar, trading_idx is the 14:15 bar — matching the mandate's
    own example exactly. Setting an entry-signal flag on floor_idx lets
    step43_daytrade's day_trade_signal + backtest.py's engine (which fills
    bar N's decision at bar N+1's open) land the fill precisely at
    trading_idx's open — one mechanism, reused verbatim, gives the correct
    no-lookahead alignment for free.
    """
    ts_vals = candles["timestamp"].to_numpy()
    ev_vals = pd.DatetimeIndex(event_ts).to_numpy()
    floor_idx = np.searchsorted(ts_vals, ev_vals, side="right") - 1
    valid = (floor_idx >= 0) & (floor_idx < len(ts_vals) - 1)
    trading_idx = floor_idx + 1
    return floor_idx, trading_idx, valid


def event_study(d, trading_idx, valid, tag_masks, horizons_bars):
    """THE scientific core: does |move| after a relevant WatcherGuru post
    exceed the UNCONDITIONAL baseline for the same window? Computed BEFORE
    any strategy verdict, exactly as the mandate demands. Baseline is
    computed over the same sliced (news-span) candle window so it is an
    apples-to-apples comparison, not a different-regime one."""
    opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
    n = len(d)
    rows = []
    for h_label, nb in horizons_bars.items():
        end = n - nb
        baseline = np.full(0, np.nan)
        if end > 0:
            baseline = (closes[nb - 1:nb - 1 + end] / opens[:end] - 1) * 100
        base_abs = np.abs(baseline)
        base_abs = base_abs[~np.isnan(base_abs)]
        base_mean = float(np.mean(base_abs)) if len(base_abs) else float("nan")
        for tag_name, mask in tag_masks.items():
            idxs = trading_idx[valid & mask]
            idxs = idxs[idxs < n - nb] if nb > 0 else idxs
            if len(idxs):
                moves = (closes[idxs + nb - 1] / opens[idxs] - 1) * 100
                mean_abs = float(np.mean(np.abs(moves)))
                med_abs = float(np.median(np.abs(moves)))
            else:
                mean_abs = med_abs = float("nan")
            rows.append({
                "horizon": h_label, "tag": tag_name, "n_events": int(len(idxs)),
                "mean_abs_move_%": mean_abs, "median_abs_move_%": med_abs,
                "baseline_mean_abs_%": base_mean,
                "ratio_vs_baseline": (mean_abs / base_mean
                                      if base_mean and not np.isnan(mean_abs)
                                      else float("nan")),
            })
    return pd.DataFrame(rows)


def make_bool_array(n, idxs):
    arr = np.zeros(n, dtype=bool)
    idxs = np.asarray(idxs)
    idxs = idxs[(idxs >= 0) & (idxs < n)]
    arr[idxs] = True
    return pd.Series(arr)


STOP_OPTS = (0.8, 1.2)
TARGET_MULT = (2.0, 3.0)
MAX_HOLD_H = (4, 24)


def run_family(rows, family_label, tf, d, f, i_tr, i_va, long_idx, short_idx,
               n_events_note):
    n = len(d)
    el = make_bool_array(n, long_idx)
    es = make_bool_array(n, short_idx)
    if el.sum() == 0 and es.sum() == 0:
        rows.append({
            "family": family_label, "config": f"NO EVENTS ({n_events_note})",
            "tf": tf, "stop%": None, "target%": None, "max_hold_h": None,
            "tr_n": 0, "tr_exp": 0, "tr_win%": 0, "tr_ret%": 0, "tr_dd%": 0,
            "va_n": 0, "va_exp": 0, "va_win%": 0, "va_ret%": 0, "va_dd%": 0,
            "med_hold_h": float("nan"), "mean_hold_h": float("nan"),
            "verdict": "NO-EVENTS",
        })
        return
    for stop_pct in STOP_OPTS:
        stop_use = min(stop_pct, HARD_STOP_CAP)
        for tmult in TARGET_MULT:
            target_pct = stop_pct * tmult
            for max_hold_h in MAX_HOLD_H:
                mh_bars = hours_to_bars(d, max_hold_h)
                sig = day_trade_signal(d, el, es, mh_bars)
                tr, va = score(d, sig, f, i_tr, i_va,
                              stop_pct=stop_use, target_pct=target_pct)
                cfg = (f"stop{stop_pct:.1f}% tgt{tmult:.0f}x hold{max_hold_h}h "
                      f"({n_events_note}, {int(el.sum())}L/{int(es.sum())}S bars)")
                rows.append(mk_row(family_label, cfg, tf, tr, va,
                                   stop_use, target_pct, max_hold_h))


def build_family_configs(frames, funding, news_tagged):
    """FAMILY A (news momentum) and FAMILY B (news fade), each with two
    direction variants:
      - 'keyword'        direction = the headline's own BULLISH/BEARISH tag
                          (only tagged headlines qualify; entry flag on
                          floor_idx -> fills AT the earliest tradeable bar).
      - 'first_bar_move'  direction = the sign of the first post-news bar's
                          own realized move (works on ANY relevant
                          headline, tagged or not; entry flag on
                          trading_idx itself -> fills one bar later, since
                          we must let that first bar actually close to know
                          its sign — still fully causal).
    """
    rows = []
    relevant = news_tagged[news_tagged["relevant"]]
    bullish = relevant[relevant["tag"] == "BULLISH"]
    bearish = relevant[relevant["tag"] == "BEARISH"]

    for tf in ("15m", "1h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = split_points(d)
        d, f = d.iloc[:n].reset_index(drop=True), f.iloc[:n].reset_index(drop=True)

        # --- keyword-direction variant ---
        floor_bull, _, valid_bull = align_events(d, bullish["utc_timestamp"])
        floor_bear, _, valid_bear = align_events(d, bearish["utc_timestamp"])
        floor_bull, floor_bear = floor_bull[valid_bull], floor_bear[valid_bear]

        run_family(rows, "A-news-momentum", tf, d, f, i_tr, i_va,
                  long_idx=floor_bull, short_idx=floor_bear,
                  n_events_note=f"keyword n_bull={len(floor_bull)} n_bear={len(floor_bear)}")
        run_family(rows, "B-news-fade", tf, d, f, i_tr, i_va,
                  long_idx=floor_bear, short_idx=floor_bull,
                  n_events_note=f"keyword n_bull={len(floor_bull)} n_bear={len(floor_bear)}")

        # --- first-post-news-bar-move-direction variant ---
        floor_rel, trad_rel, valid_rel = align_events(d, relevant["utc_timestamp"])
        trad_rel = trad_rel[valid_rel]
        trad_rel = trad_rel[trad_rel < len(d)]
        opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
        move_sign = np.sign(closes[trad_rel] - opens[trad_rel])
        up_idx = trad_rel[move_sign > 0]
        down_idx = trad_rel[move_sign < 0]

        run_family(rows, "A-news-momentum", tf, d, f, i_tr, i_va,
                  long_idx=up_idx, short_idx=down_idx,
                  n_events_note=f"first_bar_move n_up={len(up_idx)} n_down={len(down_idx)}")
        run_family(rows, "B-news-fade", tf, d, f, i_tr, i_va,
                  long_idx=down_idx, short_idx=up_idx,
                  n_events_note=f"first_bar_move n_up={len(up_idx)} n_down={len(down_idx)}")

    return pd.DataFrame(rows)


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("PHASE 1 — HARVEST WatcherGuru Telegram history")
    print("=" * 78)
    news_raw, limitation = harvest_history()

    print("\n" + "=" * 78)
    print("PHASE 2 — CLASSIFY (deterministic keywords, no LLM)")
    print("=" * 78)
    print(f"RELEVANCE_KEYWORDS ({len(RELEVANCE_KEYWORDS)}): {RELEVANCE_KEYWORDS}")
    print(f"BULLISH_KEYWORDS ({len(BULLISH_KEYWORDS)}): {BULLISH_KEYWORDS}")
    print(f"BEARISH_KEYWORDS ({len(BEARISH_KEYWORDS)}): {BEARISH_KEYWORDS}")
    news = classify_frame(news_raw)
    print(f"\n{len(news)} total posts harvested.")
    print(f"relevant: {news['relevant'].sum()} "
          f"({news['relevant'].mean() * 100:.1f}%)")
    print("tag distribution (relevant posts only):")
    print(news[news["relevant"]]["tag"].value_counts().to_string())
    print("tag distribution (ALL posts, for context):")
    print(news["tag"].value_counts().to_string())

    print("\n" + "=" * 78)
    print("COST FLOOR")
    print("=" * 78)
    cm = CostModel()
    print(f"  taker round trip (worst case)      : {cm.round_trip_bps():.1f} bps")
    print(f"  maker round trip (best case, both fills passive): "
          f"{2 * cm.maker_fee_bps:.1f} bps")
    print("  prior-round REALIZED blended maker/chase cost (step41/step43): "
          "~9 bps round trip — the real hurdle every config below must clear.")

    print("\n" + "=" * 78)
    print("PHASE 3 — ALIGN + EVENT STUDY + BACKTEST")
    print("=" * 78)
    print("Loading cached BTC candles (no network calls needed)...")
    frames_full = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h")}
    funding_hist = fetch_funding_history("BTCUSDT")

    news_min, news_max = news["utc_timestamp"].min(), news["utc_timestamp"].max()
    print(f"News sample span: {news_min:%Y-%m-%d} -> {news_max:%Y-%m-%d} "
          f"({(news_max - news_min).days} days)")

    frames, funding = {}, {}
    for tf in ("15m", "1h"):
        dfull = frames_full[tf]
        mask = (dfull["timestamp"] >= news_min - pd.Timedelta(hours=24)) & \
               (dfull["timestamp"] <= news_max + pd.Timedelta(hours=24))
        d = dfull[mask].reset_index(drop=True)
        fu = align_funding(d, funding_hist)
        frames[tf], funding[tf] = d, fu
        n, i_tr, i_va = split_points(d)
        print(f"  {tf}: {n} bars sliced to news span "
              f"({d['timestamp'].iloc[0]:%Y-%m-%d} -> {d['timestamp'].iloc[-1]:%Y-%m-%d}) "
              f"| train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")

    horizons_bars = {"15m": {"1h": 4, "4h": 16}, "1h": {"1h": 1, "4h": 4}}
    relevant = news[news["relevant"]]
    tag_masks_template = {
        "ALL_RELEVANT": (relevant["tag"] == relevant["tag"]),  # all True
        "BULLISH": relevant["tag"] == "BULLISH",
        "BEARISH": relevant["tag"] == "BEARISH",
        "NEUTRAL": relevant["tag"] == "NEUTRAL",
        "MIXED": relevant["tag"] == "MIXED",
    }

    print("\n--- EVENT STUDY (the scientific core) ---")
    all_studies = []
    for tf in ("15m", "1h"):
        d = frames[tf]
        floor_idx, trading_idx, valid = align_events(d, relevant["utc_timestamp"])
        study = event_study(d, trading_idx, valid, tag_masks_template,
                            horizons_bars[tf])
        study.insert(0, "tf", tf)
        all_studies.append(study)
    event_study_df = pd.concat(all_studies, ignore_index=True)
    print(event_study_df.to_string(index=False, float_format=lambda x: f"{x:,.4f}"))

    print("\n--- STRATEGY BACKTEST GRID (families A/B, gauntlet) ---")
    df = build_family_configs(frames, funding, news)
    print(f"\n{len(df)} configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS (positive train+val, >={MIN_TRAIN_TRADES} train / "
          f">={MIN_VAL_TRADES} val trades): {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "tf", "tr_n", "tr_exp", "va_n",
                          "va_exp", "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "tf", "tr_n", "tr_exp", "va_n",
                     "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    fail = df[df["verdict"] == "FAIL"]
    print(f"\nFAIL: {len(fail)}  |  NO-EVENTS: "
          f"{len(df[df['verdict'] == 'NO-EVENTS'])}")

    return news, event_study_df, df, limitation


if __name__ == "__main__":
    main()
