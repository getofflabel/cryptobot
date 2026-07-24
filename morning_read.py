"""
morning_read.py — THE MACHINE'S MARKET MEMORY, with a Telegram note as the
byproduct.

PRIMARY PURPOSE (owner, 2026-07-24): "the morning read doesn't do anything
for me — it's supposed to help YOU build a better machine. Everything we
trade should be treated as if it has a HISTORY — what last week did can
affect this week." So the thing this module actually builds, once per UTC
day, is a small structured CONTEXT STORE in state:

    state["market_context"][symbol]          -> today's read (latest)
    state["market_context_history"][symbol]  -> rolling list of past reads
                                                 (capped at HISTORY_CAP)

symbol is one of "BTC-USDT", "ETH-USDT", "XAUT-USDT", or the pseudo-symbol
"macro" (cross-asset: SPY/oil). Read access is via get_context() /
get_context_history() below — never reach into state["market_context"]
directly from another module, so the schema can evolve in one place.

PER-SYMBOL SCHEMA (BTC-USDT / ETH-USDT / XAUT-USDT):
    date, weekly_hi, weekly_lo, weekly_mid, width_pct, pos_pct, zone
    ("lower_edge" / "midrange" / "upper_edge"), prior_day_high,
    prior_day_low, ret_5d, rel_strength_vs_btc (None for BTC itself),
    regime ("calm" / "normal" / "violent"), plus two rendering-only extras
    (last_price, tape) kept so the note below can be built FROM this dict
    alone, with no second source of truth.

MACRO SCHEMA ("macro" pseudo-symbol):
    date, spy_close, spy_zone, brent_wti_spread, spread_pctile,
    stress_flag, plus rendering-only extras (brent_close, wti_close,
    spy_weekly_hi, spy_weekly_lo, spy_prior_low_broken).

AUTHORITY (loud on purpose): books MAY READ this context (get_context /
get_context_history) for situational awareness. NO BOOK CHANGES TRADING
BEHAVIOR FROM IT YET — this is observation only until a validation round
(tracked as R67+) says which context rules actually earn a place in a
book's entry/exit logic. Wiring a book to react to this without that
validation would be exactly the kind of unearned rule the project's whole
sealed-testing discipline exists to prevent.

THE TELEGRAM NOTE: rendered FROM the stored context (render_note()), in
one trader's plain voice — no internal book names, no jargon. It fires
once per UTC day, at the first cycle at/after DUE_HOUR_UTC (12:00, i.e.
pre-NY / after the London morning). state["morning_read_date"] guards the
once-daily send. Entrypoint: run_morning_read(live_feed, state, dry=False)
— a no-op unless due; dry=True renders and returns the text WITHOUT
sending or persisting anything (pure preview).

NO TRADING: this module only reads candles/tickers and sends one notify().
It never places an order.
"""

from __future__ import annotations

from datetime import datetime, timezone

from strategy import atr

BTC_SYMBOL = "BTC-USDT"
ETH_SYMBOL = "ETH-USDT"
GOLD_SYMBOL = "XAUT-USDT"

DUE_HOUR_UTC = 12          # first cycle at/after this UTC hour fires the note
HISTORY_CAP = 30           # rolling days kept per symbol in market_context_history

ZONE_LOWER = "lower_edge"
ZONE_MID = "midrange"
ZONE_UPPER = "upper_edge"


# ---------------------------------------------------------------------------
# pure math — every one of these is unit-testable with synthetic data, no
# network, no state
# ---------------------------------------------------------------------------


def fmt_px(x) -> str:
    """Trader-style rounding: $63.9k / $65k above 10k, $1,856 below."""
    x = float(x)
    if abs(x) >= 10000:
        val = x / 1000
        s = f"{val:.1f}"
        if s.endswith(".0"):
            s = s[:-2]
        return f"${s}k"
    return f"${x:,.0f}"


def position_pct(price: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 50.0
    pct = (price - lo) / (hi - lo) * 100
    return max(0.0, min(100.0, pct))


def zone_label(pos_pct: float) -> str:
    if pos_pct < 25:
        return ZONE_LOWER
    if pos_pct > 75:
        return ZONE_UPPER
    return ZONE_MID


def zone_phrase(zone: str) -> str:
    return {ZONE_LOWER: "the lower edge", ZONE_MID: "midrange",
            ZONE_UPPER: "the upper edge"}.get(zone, "midrange")


def compute_weekly_stats(bars_1d, current_price: float) -> dict:
    """From the prior daily bars (>=6 ideally, degrades gracefully with
    fewer) plus a live price, return the full weekly-range read."""
    week = bars_1d.iloc[-6:] if len(bars_1d) >= 6 else bars_1d
    hi = float(week["high"].max())
    lo = float(week["low"].min())
    mid = (hi + lo) / 2
    width_pct = (hi - lo) / mid * 100 if mid else 0.0
    pos = position_pct(current_price, lo, hi)
    zone = zone_label(pos)
    prior_high = float(bars_1d["high"].iloc[-1])
    prior_low = float(bars_1d["low"].iloc[-1])
    open0 = float(week["close"].iloc[0])
    ret_5d = ((float(week["close"].iloc[-1]) / open0 - 1) * 100) if open0 else 0.0
    return {
        "weekly_hi": round(hi, 2), "weekly_lo": round(lo, 2),
        "weekly_mid": round(mid, 2), "width_pct": round(width_pct, 2),
        "pos_pct": round(pos, 1), "zone": zone,
        "prior_day_high": round(prior_high, 2),
        "prior_day_low": round(prior_low, 2),
        "ret_5d": round(ret_5d, 2),
        "last_price": round(float(current_price), 2),
    }


def classify_tape(bars_4h, atr_1d: float | None) -> str:
    """3-4 honest classifications off the last 6 4h bars (~24h)."""
    if bars_4h is None or len(bars_4h) < 6:
        return "not enough data"
    last6 = bars_4h.iloc[-6:]
    red = int((last6["close"] < last6["open"]).sum())
    green = 6 - red
    range24h = float(last6["high"].max() - last6["low"].min())
    if red >= 5:
        return "bled steadily"
    if green >= 5:
        return "pushed higher"
    if atr_1d and range24h < atr_1d:
        return "chopped sideways"
    return "chopped, no clear direction"


def compute_regime(atr_pct_now: float, atr_pct_median: float | None) -> str:
    """Same calm/normal/violent convention as daily_pick.py: current 1h
    ATR% vs its own trailing-14d median."""
    if not atr_pct_median or atr_pct_median <= 0:
        return "normal"
    ratio = atr_pct_now / atr_pct_median
    if ratio < 0.8:
        return "calm"
    if ratio > 1.5:
        return "violent"
    return "normal"


def consequence_line(regime: str, zone: str, lo: float, hi: float) -> str:
    if zone in (ZONE_LOWER, ZONE_UPPER):
        return "at the edge of the week's range — decision zone"
    if regime == "calm":
        return f"let it chop — better trades closer to {fmt_px(lo)} or {fmt_px(hi)}"
    if regime == "violent":
        return "moving tape — trend tools have fuel"
    return "midrange chop, nothing decisive yet"


def rel_strength_phrase(diff, tol: float = 0.15):
    if diff is None:
        return None
    if abs(diff) < tol:
        return "ETH and BTC tracking each other closely this week"
    if diff > 0:
        return "ETH holding better than BTC this week"
    return "BTC holding better than ETH this week"


def compute_macro_context(today: str, spy_bars, oil_data) -> dict | None:
    """spy_bars: daily OHLC DataFrame (>=2 rows) or None.
    oil_data: (brent_last, wti_last, spread_hist) or None."""
    macro: dict = {"date": today}
    got_any = False

    if spy_bars is not None and len(spy_bars) >= 2:
        got_any = True
        week = spy_bars.iloc[-6:] if len(spy_bars) >= 6 else spy_bars
        last_close = float(spy_bars["close"].iloc[-1])
        hi = float(week["high"].max())
        lo = float(week["low"].min())
        zone = zone_label(position_pct(last_close, lo, hi))
        prior_low = float(spy_bars["low"].iloc[-2])
        macro.update(
            spy_close=round(last_close, 2), spy_zone=zone,
            spy_weekly_hi=round(hi, 2), spy_weekly_lo=round(lo, 2),
            spy_prior_low_broken=bool(last_close < prior_low),
        )

    if oil_data is not None:
        brent, wti, spread_hist = oil_data
        if brent is not None and wti is not None:
            got_any = True
            brent, wti = float(brent), float(wti)
            spread = brent - wti
            pctile = None
            if spread_hist:
                n = len(spread_hist)
                if n:
                    below = sum(1 for s in spread_hist if s <= spread)
                    pctile = round(below / n * 100, 1)
            macro.update(
                brent_close=round(brent, 2), wti_close=round(wti, 2),
                brent_wti_spread=round(spread, 2), spread_pctile=pctile,
                stress_flag=bool(pctile is not None and pctile >= 80),
            )

    return macro if got_any else None


# ---------------------------------------------------------------------------
# context store — the actual deliverable
# ---------------------------------------------------------------------------


def store_market_context(state: dict, contexts: dict) -> dict:
    """Write today's contexts as the latest read AND append them to each
    symbol's rolling history (capped at HISTORY_CAP). Pure state mutation,
    no I/O — callers own load_state()/save_state()."""
    mc = state.setdefault("market_context", {})
    hist = state.setdefault("market_context_history", {})
    for sym, ctx in contexts.items():
        mc[sym] = ctx
        h = hist.setdefault(sym, [])
        h.append(ctx)
        del h[:-HISTORY_CAP]
    return state


def get_context(state: dict, sym: str) -> dict | None:
    """Latest stored read for `sym` ("BTC-USDT" / "ETH-USDT" / "XAUT-USDT"
    / "macro"), or None if never written. Read-only — the sanctioned way
    for any book to look at this data (see module docstring on authority)."""
    return (state or {}).get("market_context", {}).get(sym)


def get_context_history(state: dict, sym: str, n: int = HISTORY_CAP) -> list:
    """Up to the last `n` stored reads for `sym`, oldest-first, newest
    last. Empty list if nothing stored yet."""
    hist = (state or {}).get("market_context_history", {}).get(sym, [])
    return hist[-n:] if n else list(hist)


# ---------------------------------------------------------------------------
# fetchers (network / yfinance) — kept thin and swappable so tests can
# inject fakes; run_morning_read wraps every call in try/except so an
# outage degrades to "skip that section", never a broken note
# ---------------------------------------------------------------------------


def _default_equities_fetch():
    import yfinance as yf
    df = yf.Ticker("SPY").history(period="2mo", interval="1d")
    if df is None or df.empty:
        return None
    df = df.rename(columns=str.lower)
    return df[["open", "high", "low", "close"]]


def _default_oil_fetch():
    import yfinance as yf
    brent = yf.Ticker("BZ=F").history(period="3mo", interval="1d")
    wti = yf.Ticker("CL=F").history(period="3mo", interval="1d")
    if brent is None or wti is None or brent.empty or wti.empty:
        return None
    brent = brent.rename(columns=str.lower)
    wti = wti.rename(columns=str.lower)
    merged = brent[["close"]].join(wti[["close"]], lsuffix="_b", rsuffix="_w",
                                   how="inner")
    if merged.empty:
        return None
    merged["spread"] = merged["close_b"] - merged["close_w"]
    brent_last = float(merged["close_b"].iloc[-1])
    wti_last = float(merged["close_w"].iloc[-1])
    spread_hist = merged["spread"].iloc[-61:-1].tolist()   # trailing 60d
    return (brent_last, wti_last, spread_hist)


def _default_news_fetch():
    try:
        from step5_paper_trade import recent_news_headline
        return recent_news_headline()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# posture (read-only look at live book state — never mutated here)
# ---------------------------------------------------------------------------


def _open_trade_line(trade: dict, label: str) -> str:
    direction = trade.get("direction", 1)
    side = "long" if direction > 0 else "short"
    line = f"We're {side} {label} from {fmt_px(trade.get('entry_price', 0))}"
    sl = trade.get("sl_price")
    if sl:
        line += f", stop at {fmt_px(sl)}"
    return line + "."


def _find_btc_open_trade(state: dict):
    """Same set of BTC-USDT books step5_paper_trade's own has_trade check
    reads — see its docstring. Returns the first open one, if any."""
    paths = [
        ("open_trade",),
        ("tactical", "open_trade"),
        ("shorts_lab", "open_trade"),
        ("newsdesk", "open_trade"),
        ("diver", "open_trade"),
    ]
    for path in paths:
        node = state
        for k in path:
            node = (node or {}).get(k)
        if node:
            return node
    return None


# ---------------------------------------------------------------------------
# note rendering — built ENTIRELY from the stored context dict (single
# source of truth) plus a couple of live, non-historical reads (open
# positions, gold's live trigger distance, a fresh headline)
# ---------------------------------------------------------------------------


def render_note(contexts: dict, state: dict, live_feed, now, news_fetch=None) -> str:
    lines: list[str] = []
    btc = contexts.get(BTC_SYMBOL)
    eth = contexts.get(ETH_SYMBOL)
    macro = contexts.get("macro")

    if btc:
        lines.append(
            f"BTC {btc['tape']}, {btc['ret_5d']:+.1f}% over 5 days — now "
            f"{fmt_px(btc['last_price'])}, {zone_phrase(btc['zone'])} of the "
            f"week's {fmt_px(btc['weekly_lo'])}-{fmt_px(btc['weekly_hi'])} range."
        )
    if eth:
        lines.append(
            f"ETH {eth['tape']}, {eth['ret_5d']:+.1f}% over 5 days — now "
            f"{fmt_px(eth['last_price'])}, {zone_phrase(eth['zone'])} of its "
            f"own range."
        )
        rel = rel_strength_phrase(eth.get("rel_strength_vs_btc"))
        if rel:
            lines.append(rel + ".")
    if btc:
        cons = consequence_line(btc["regime"], btc["zone"], btc["weekly_lo"],
                                btc["weekly_hi"])
        lines.append(f"Volatility is {btc['regime']} — {cons}.")

    # gold: an open position speaks for itself; otherwise the trigger
    # distance (read straight off the real book's own entry rule)
    gold_trade = (state or {}).get("gold_book", {}).get("open_trade")
    if gold_trade:
        lines.append(_open_trade_line(gold_trade, "gold"))
    else:
        trigger = None
        try:
            from gold_book import compute_trigger_level
            trigger = compute_trigger_level(live_feed)
        except Exception:
            trigger = None
        if trigger:
            lines.append(f"Gold wakes up above {fmt_px(trigger)}.")

    btc_trade = _find_btc_open_trade(state or {})
    if btc_trade:
        lines.append(_open_trade_line(btc_trade, "BTC"))
    eth_trade = (state or {}).get("tactical_eth", {}).get("open_trade")
    if eth_trade:
        lines.append(_open_trade_line(eth_trade, "ether"))

    if macro and "spy_close" in macro:
        if macro.get("spy_prior_low_broken"):
            lines.append(
                f"SPY {fmt_px(macro['spy_close'])}, lost the prior session's "
                f"low — {zone_phrase(macro['spy_zone'])} of the week's range."
            )
        else:
            lines.append(
                f"SPY {fmt_px(macro['spy_close'])}, holding "
                f"{zone_phrase(macro['spy_zone'])} of the week's "
                f"{fmt_px(macro['spy_weekly_lo'])}-{fmt_px(macro['spy_weekly_hi'])} range."
            )

    if macro and "brent_wti_spread" in macro:
        suffix = ""
        if macro.get("stress_flag"):
            suffix = (" — Brent trading at a premium to WTI, the "
                      "March-style dislocation")
        lines.append(
            f"Brent {fmt_px(macro['brent_close'])}, WTI "
            f"{fmt_px(macro['wti_close'])}, spread "
            f"${macro['brent_wti_spread']:+.2f}{suffix}."
        )

    if now.weekday() == 4:      # Friday, UTC
        lines.append("Weekend headline risk — the news watch stays on "
                      "through Saturday and Sunday.")
    fetch = news_fetch or _default_news_fetch
    try:
        headline = fetch()
    except Exception:
        headline = None
    if headline:
        lines.append(f"On the radar: {str(headline)[:140]}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def _compute_symbol_context(live_feed, sym: str, today: str) -> dict:
    bars_1d = live_feed.get_candles(sym, "1d", 40)
    bars_4h = live_feed.get_candles(sym, "4h", 20)
    c1h = live_feed.get_candles(sym, "1h", 400)
    price = float(live_feed.get_ticker(sym).last)

    stats = compute_weekly_stats(bars_1d, price)
    atr_1d_now = float(atr(bars_1d, 14).iloc[-1]) if len(bars_1d) >= 15 else None
    tape = classify_tape(bars_4h, atr_1d_now)

    atr_pct_series = (atr(c1h, 14) / c1h["close"] * 100)
    atr_pct_now = float(atr_pct_series.iloc[-1])
    atr_pct_med = (float(atr_pct_series.iloc[-336:].median())
                  if len(c1h) >= 100 else None)
    regime = compute_regime(atr_pct_now, atr_pct_med)

    return {"date": today, "symbol": sym, "tape": tape, "regime": regime,
            **stats}


def run_morning_read(live_feed, state: dict, dry: bool = False, now=None,
                     equities_fetch=None, oil_fetch=None, news_fetch=None):
    """No-op unless due (see module docstring), except when dry=True, which
    always renders and returns the note WITHOUT sending or persisting
    anything — a pure preview for tests/manual checks.

    On a due call: builds the per-symbol + macro context, WRITES it to
    state (market_context / market_context_history — the primary
    deliverable), renders the Telegram note from that same stored context
    (the byproduct), sends it, and marks the day done."""
    now = now or datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    if not dry:
        if state.get("morning_read_date") == today:
            return None
        if now.hour < DUE_HOUR_UTC:
            return None

    contexts: dict = {}
    ret5d_by_sym: dict = {}
    for sym in (BTC_SYMBOL, ETH_SYMBOL, GOLD_SYMBOL):
        try:
            ctx = _compute_symbol_context(live_feed, sym, today)
        except Exception as e:
            print(f"  [MORNING READ] {sym} context failed: {str(e)[:100]}")
            continue
        contexts[sym] = ctx
        ret5d_by_sym[sym] = ctx["ret_5d"]

    if BTC_SYMBOL in ret5d_by_sym:
        btc_ret = ret5d_by_sym[BTC_SYMBOL]
        for sym, ctx in contexts.items():
            ctx["rel_strength_vs_btc"] = (
                None if sym == BTC_SYMBOL else round(ret5d_by_sym[sym] - btc_ret, 2))
    else:
        for ctx in contexts.values():
            ctx["rel_strength_vs_btc"] = None

    fetch_equities = equities_fetch or _default_equities_fetch
    fetch_oil = oil_fetch or _default_oil_fetch
    try:
        spy_bars = fetch_equities()
    except Exception as e:
        print(f"  [MORNING READ] equities fetch failed: {str(e)[:100]}")
        spy_bars = None
    try:
        oil_data = fetch_oil()
    except Exception as e:
        print(f"  [MORNING READ] oil fetch failed: {str(e)[:100]}")
        oil_data = None

    macro_ctx = compute_macro_context(today, spy_bars, oil_data)
    if macro_ctx is not None:
        contexts["macro"] = macro_ctx

    if dry:
        return render_note(contexts, state, live_feed, now, news_fetch)

    store_market_context(state, contexts)
    text = render_note(contexts, state, live_feed, now, news_fetch)

    from step5_paper_trade import notify, save_state
    title = f"\U0001f305 Morning read — {now.strftime('%A')}"
    notify(title, text)
    state["morning_read_date"] = today
    save_state(state)
    return text
