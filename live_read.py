"""
live_read.py — the bot's CURRENT THOUGHT, published for the on-screen HUD.

Wallace wants to glance at his chart and see what the bot is thinking at that
moment. So every cycle the bot computes a compact snapshot — the STORM GAUGE
(how violent is the market, and therefore how big a slice is sane) plus each
book's live read — and writes it to cloud state under state["live_read"]. A
tiny anon-readable RPC exposes just that snapshot; the browser overlay polls
it. What you see on screen is the SAME code the bot trades on, never a
reimplementation that could drift.

PHILOSOPHY (printed on the gauge): "Says how much — never when." The gauge is
a SIZING advisor keyed to market violence; it never tells you to enter. Entry
is the strategy's job. This snapshot is DISPLAY ONLY — the size multiplier is
advice for the human eye and is NOT wired into the bot's live position sizing
(that would be a strategy change, gated on its own).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from strategy import atr as _atr
from strategy import vol_gated_ma, rsi


def _annualized_vol_series(daily):
    """Realized annualized volatility, %, as a rolling daily series: the std
    of the last 20 daily log returns, scaled to a year. The honest, standard
    measure of 'how violent has this market been'."""
    c = daily["close"]
    logret = (c / c.shift(1)).apply(lambda x: math.log(x) if x and x > 0 else 0.0)
    return logret.rolling(20).std() * math.sqrt(365) * 100


def _weather(percentile):
    if percentile >= 80:
        return "STORM"
    if percentile >= 50:
        return "CHOPPY"
    return "CALM"


def _action(size_mult, weather):
    if weather == "STORM":
        return "HALF SIZE"
    if weather == "CHOPPY":
        return "TRIM SIZE"
    return "FULL SIZE OK"


def compute_live_read(candles_1h, candles_4h, candles_1d, funding_bps,
                      state) -> dict:
    """Pure function (takes fetched candles, returns the snapshot dict) so it
    is testable offline. All the market reads the bot acts on, in one place."""
    price = float(candles_1h["close"].iloc[-1])

    # --- champion trend (the ride's compass) ---
    cv = vol_gated_ma(candles_4h, fast=20, slow=100, min_atr_pct=1.5).iloc[-1]
    champ = int(cv) if cv == cv else 0

    # --- STORM GAUGE: violence, its place in the past year, and the size it
    #     implies (volatility targeting — size DOWN when the market is wild) ---
    vol = _annualized_vol_series(candles_1d).dropna()
    if len(vol) >= 30:
        current = float(vol.iloc[-1])
        year = vol.iloc[-365:] if len(vol) > 365 else vol
        percentile = round(float((year < current).mean()) * 100)
        limit = round(float(year.quantile(0.80)), 1)          # the storm line
        median_vol = float(year.median())
        size_mult = median_vol / current if current > 0 else 1.0
        size_mult = round(max(0.40, min(1.30, size_mult)), 2)
    else:
        current, percentile, limit, size_mult = 0.0, 0, 0.0, 1.0

    weather = _weather(percentile)
    ledger = float(state.get("virtual_equity", 0) or 0)
    entry_dollars = round(size_mult * ledger)

    # --- 1h texture the fast books watch ---
    atr1h = float(_atr(candles_1h, 14).iloc[-1])
    atr1h_pct = round(atr1h / price * 100, 2) if price else 0.0
    r3 = float(rsi(candles_1h["close"], 3).iloc[-1])
    lo20 = candles_1h["low"].rolling(20).min().shift(1).iloc[-1]
    breakdown = bool(lo20 == lo20 and price < lo20)
    pop4h = round((price / float(candles_1h["close"].iloc[-5]) - 1) * 100, 2) \
        if len(candles_1h) >= 5 else 0.0
    fb = round(funding_bps, 2) if funding_bps is not None else None

    # --- what each book sees RIGHT NOW, in plain words ---
    pos = "flat"
    if state.get("open_trade"):
        pos = "LONG (ride)"
    elif state.get("tactical", {}).get("open_trade"):
        pos = "LONG (strike)"
    elif state.get("shorts_lab", {}).get("open_trade"):
        pos = "SHORT (lab)"

    benched = state.get("benched_triggers", [])
    books = []
    # THE RIDE
    books.append({
        "name": "The Ride",
        "read": "trend UP — riding" if champ == 1 else "trend flat — standing aside",
        "armed": champ == 1,
    })
    # THE STRIKES (panic-dip: champ up + RSI3 washout)
    if champ == 1:
        strikes_read = (f"dip-buy armed · RSI3 {r3:.0f}" if r3 < 10
                        else f"waiting RSI3<10 · now {r3:.0f}")
        strikes_armed = r3 < 10
    else:
        strikes_read = "asleep · needs uptrend"
        strikes_armed = False
    books.append({"name": "The Strikes", "read": strikes_read,
                  "armed": strikes_armed})
    # THE SHORTS LAB (forensic: funding + pop + live ATR; cascade: funding + breakdown)
    if champ != 0:
        lab_read = "asleep (trend not down)"
        lab_armed = False
    elif fb is None:
        lab_read = "funding unreadable"
        lab_armed = False
    else:
        cascade_close = fb > 2.0 and breakdown
        forensic_close = fb >= 1.5 and pop4h > 1.5 and atr1h_pct > 1.2
        if cascade_close or forensic_close:
            lab_read = "SHORT armed"
            lab_armed = True
        elif fb > 1.5:
            lab_read = f"funding hot {fb:+.1f}bp · watching"
            lab_armed = False
        else:
            lab_read = f"quiet · funding {fb:+.1f}bp"
            lab_armed = False
    books.append({"name": "Shorts Lab", "read": lab_read, "armed": lab_armed})

    # one-line headline thought
    if pos != "flat":
        thought = f"In a {pos} position — managing it."
    elif any(b["armed"] for b in books):
        armed_names = ", ".join(b["name"] for b in books if b["armed"])
        thought = f"{armed_names} armed — watching for the entry."
    elif weather == "STORM":
        thought = "Market's violent. If anything fires, half size."
    else:
        thought = "Quiet tape. Nothing to do but watch."

    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "price": round(price, 1),
        "storm": {
            "violence": round(current, 1),
            "limit": limit,
            "percentile": percentile,
            "weather": weather,
            "size_mult": size_mult,
            "entry_dollars": entry_dollars,
            "ledger": round(ledger, 2),
            "action": _action(size_mult, weather),
        },
        "trend": "UP" if champ == 1 else "FLAT/DOWN",
        "position": pos,
        "funding_bps": fb,
        "atr1h_pct": atr1h_pct,
        "books": books,
        "benched": benched,
        "thought": thought,
    }


def write_live_read(live_feed, state, save=True):
    """Fetch what compute needs, build the snapshot, stash it in state. Called
    from the daemon heartbeat and the hourly cycle. Never raises — a HUD glitch
    must never disturb trading."""
    try:
        from step5_paper_trade import current_funding_bps, save_state
        c1 = live_feed.get_candles("BTC-USDT", "1h", 60)
        c4 = live_feed.get_candles("BTC-USDT", "4h", 300)
        cd = live_feed.get_candles("BTC-USDT", "1d", 400)
        fb = current_funding_bps(live_feed, "BTC-USDT")
        snap = compute_live_read(c1, c4, cd, fb, state)
        state["live_read"] = snap
        if save:
            save_state(state)
        return snap
    except Exception as e:
        print(f"  live_read skipped: {str(e)[:80]}")
        return None
