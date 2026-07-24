"""
live_read.py — the bot's CURRENT STATE, published for the on-screen HUD.

v2 (2026-07-23): rebuilt for a trader's eye. Out went the academic storm
gauge (violence percentiles, size multipliers) that Wallace couldn't read.
In came the three things a trader actually glances for:
  1. is the bot IN a trade, and is it winning or losing RIGHT NOW
  2. if flat, what is it waiting for — and how close is that trigger
  3. a one-line plain-English thought

v3 (2026-07-23): SYMBOL-AWARE. The flaw v2 had: it only ever described
BTC-USDT, even while Wallace was staring at BloFin's XAUT-USDT (gold) page —
he'd see Bitcoin's price and a Bitcoin news trade next to a gold chart.
Fixed by publishing a `symbols` map keyed by instId (BTC-USDT, XAUT-USDT,
ETH-USDT, SOL-USDT, TSLA-USDT, + anything else the Daily Pick happens to
hold) alongside a `global` block for the account-wide stuff (equity, goal,
market weather, thought, the news-armed object). The extension detects what
the viewer is actually looking at and renders THAT symbol's content.

Every OLD top-level key (price, market, trend, position, armed, thesis,
waiting, thought, ...) is KEPT VERBATIM for one deploy cycle — still BTC's
own numbers, exactly as v2 published them — so a stale extension that hasn't
picked up the new content.js yet keeps working unmodified. Delete the old
keys once the new extension is confirmed live everywhere.

The panel ticks the PRICE itself live (fetched by the extension every ~2s,
straight from BloFin) and does the P&L / distance math locally against the
entry, stop, and target this snapshot provides — so the money number moves
with the market, not on our 60s publish clock. This file just hands the
panel the levels and context; the panel makes them live.

DISPLAY ONLY. Nothing here feeds the bot's own sizing or entries.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from strategy import atr as _atr
from strategy import vol_gated_ma, rsi

CONTRACT_SIZE = {"The Ride": 0.001, "The Strikes": 0.001,
                 "ETH Amplifier": 0.01, "Shorts Lab": 0.001,
                 "The Gold Book": 0.001, "Daily Pick": 0.001,
                 "The Diver": 0.001}

# instId -> the plain-English name the HUD shows next to it.
DISPLAY_NAMES = {
    "BTC-USDT": "Bitcoin", "ETH-USDT": "Ethereum", "XAUT-USDT": "Gold",
    "SOL-USDT": "Solana", "TSLA-USDT": "Tesla",
}


def _annualized_vol(daily):
    c = daily["close"]
    logret = (c / c.shift(1)).apply(lambda x: math.log(x) if x and x > 0 else 0.0)
    v = (logret.rolling(20).std() * math.sqrt(365) * 100).dropna()
    if len(v) < 30:
        return "CALM"
    current = float(v.iloc[-1])
    year = v.iloc[-365:] if len(v) > 365 else v
    pct = float((year < current).mean()) * 100
    return "STORM" if pct >= 80 else ("CHOPPY" if pct >= 50 else "CALM")


def _norm_trade(book, t, contract_size, target_label=None):
    """Turn ANY book's open_trade dict into the one panel-ready shape every
    position card renders (side, entry, stop, target, size). Shared by every
    symbol below so a card looks the same whether it's BTC's The Ride or
    Gold's donchian breakout. `contract_size` is the fallback when the trade
    itself didn't record its own contract_value (The Ride/Strikes/Shorts Lab/
    ETH Amplifier never do; Gold and Daily Pick always do, and that's more
    accurate than a hardcoded constant, so it wins when present)."""
    direction = t.get("direction", 1)
    d = {
        "book": book,
        "side": "SHORT" if direction < 0 else "LONG",
        "dir": direction,
        "entry": t.get("entry_price"),
        "stop": t.get("sl_price"),
        "target": t.get("tp_price"),
        "contracts": t.get("contracts", 0),
        "contract_size": t.get("contract_value", contract_size),
        "trigger": t.get("trigger", book),
    }
    if target_label:
        d["target_label"] = target_label
    return d


def _open_position(state):
    """Return BTC-USDT's single open book as a panel-ready dict, or None.
    Checks each BTC book; the exchange nets to one position so at most one
    is open at a time."""
    # BTC-USDT books ONLY. The ETH Amplifier lives under symbols["ETH-USDT"]
    # — including it here is what put an ETH trade on the Bitcoin card with
    # BTC prices (the fake +$10k of 2026-07-24). The Daily Pick counts only
    # when the symbol it holds IS BTC.
    pick_t = state.get("daily_pick", {}).get("open_trade")
    if pick_t and pick_t.get("symbol") not in (None, "BTC-USDT"):
        pick_t = None
    books = [("The Ride", state.get("open_trade"), CONTRACT_SIZE["The Ride"]),
             ("The Strikes", state.get("tactical", {}).get("open_trade"),
              CONTRACT_SIZE["The Strikes"]),
             ("Shorts Lab", state.get("shorts_lab", {}).get("open_trade"),
              CONTRACT_SIZE["Shorts Lab"]),
             ("The Newsdesk", state.get("newsdesk", {}).get("open_trade"),
              0.001),
             ("The Diver", state.get("diver", {}).get("open_trade"),
              CONTRACT_SIZE["The Diver"]),
             ("Daily Pick", pick_t, 0.001)]
    for name, t, csize in books:
        if not t:
            continue
        return _norm_trade(name, t, csize)
    return None


def _gold_status(gold_daily):
    """The Gold Book's flat-state card: the donchian55 breakout level and
    the EMA20 trend line, off XAUT-USDT daily candles. `gold_daily` is
    fetched by write_live_read (one extra candles call per 60s heartbeat);
    if that fetch failed, or there isn't 56 bars of history yet, this
    degrades to {"mode": "unknown"} rather than raising — a gold outage
    must never take the rest of the snapshot down with it."""
    try:
        if gold_daily is None or len(gold_daily) < 56:
            return {"mode": "unknown"}
        hi55 = gold_daily["high"].rolling(55).max().shift(1).iloc[-1]
        if hi55 != hi55:   # NaN guard (matches this file's existing style)
            return {"mode": "unknown"}
        ema20 = gold_daily["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        last_close = float(gold_daily["close"].iloc[-1])
        level_55d = round(float(hi55), 1)
        ema20_v = round(float(ema20), 1)
        return {
            "mode": "waiting_breakout",
            "level_55d": level_55d,
            "ema20": ema20_v,
            "last_close": round(last_close, 1),
            "text": f"Buying a close above ${level_55d:,.0f}. "
                    f"Trend line ${ema20_v:,.0f}.",
        }
    except Exception:
        return {"mode": "unknown"}


def _build_symbols(state, position, thesis, waiting, armed, gold_daily):
    """The v3 payload: every instrument the bot might have on screen,
    keyed by BloFin instId. See the module docstring for why this exists."""
    symbols = {
        "BTC-USDT": {
            "display": DISPLAY_NAMES["BTC-USDT"],
            "thesis": thesis,
            "waiting": waiting,
            "position": position,
            "armed": armed,
        },
    }

    # --- XAUT-USDT — The Gold Book --------------------------------------
    gold_open = state.get("gold_book", {}).get("open_trade")
    if gold_open:
        symbols["XAUT-USDT"] = {
            "display": DISPLAY_NAMES["XAUT-USDT"], "book": "The Gold Book",
            "position": _norm_trade(
                "The Gold Book", gold_open,
                CONTRACT_SIZE["The Gold Book"], target_label="trend exit"),
        }
    else:
        symbols["XAUT-USDT"] = {
            "display": DISPLAY_NAMES["XAUT-USDT"], "book": "The Gold Book",
            "position": None, "status": _gold_status(gold_daily),
        }

    # --- ETH-USDT — ETH Amplifier ---------------------------------------
    eth_open = state.get("tactical_eth", {}).get("open_trade")
    if eth_open:
        symbols["ETH-USDT"] = {
            "display": DISPLAY_NAMES["ETH-USDT"], "book": "ETH Amplifier",
            "position": _norm_trade("ETH Amplifier", eth_open,
                                    CONTRACT_SIZE["ETH Amplifier"]),
        }
    else:
        symbols["ETH-USDT"] = {
            "display": DISPLAY_NAMES["ETH-USDT"], "book": "ETH Amplifier",
            "position": None,
            "status": {"mode": "waiting_dip",
                       "text": "amplifier waits for a BTC panic-dip"},
        }

    # --- Daily Pick rotation (SOL-USDT, TSLA-USDT, + whatever else it's --
    # --- holding) — read defensively, this book may not be deployed yet --
    dp = state.get("daily_pick", {}) or {}
    dp_open = dp.get("open_trade")
    dp_symbol = dp_open.get("symbol") if dp_open else None
    rotation_status = {"mode": "rotation",
                       "text": "in the Daily Pick rotation, scored every "
                               "morning"}

    for sym in ("SOL-USDT", "TSLA-USDT"):
        if dp_open and dp_symbol == sym:
            symbols[sym] = {
                "display": DISPLAY_NAMES[sym], "book": "Daily Pick",
                "position": _norm_trade("Daily Pick", dp_open,
                                        CONTRACT_SIZE["Daily Pick"]),
            }
        else:
            symbols[sym] = {
                "display": DISPLAY_NAMES[sym], "book": "Daily Pick",
                "position": None, "status": rotation_status,
            }

    # any OTHER symbol the daily pick currently holds (not one of the named
    # ones above) still gets exposed, under its own instId
    if dp_open and dp_symbol and dp_symbol not in symbols:
        symbols[dp_symbol] = {
            "display": DISPLAY_NAMES.get(dp_symbol,
                                         dp_symbol.replace("-USDT", "")),
            "book": "Daily Pick",
            "position": _norm_trade("Daily Pick", dp_open,
                                    CONTRACT_SIZE["Daily Pick"]),
        }

    return symbols


def _thesis(champ, price, fb, r3, lo20, pop4h):
    """The bot's CURRENT TRADE THESIS: if it had to pick a trade this second,
    what would it be — side, entry, TP, SL, reward:risk, and a conviction
    score (heuristic v1) reflecting how well conditions favor it. This is the
    'here's how I'd trade it' Wallace asked to see, even on a flat day."""
    if champ == 1:
        side, book = "LONG", "The Strikes"
        sl = round(price * (1 - 0.015), 1)      # tight strike stop
        tp = round(price * (1 + 0.045), 1)      # 3:1
        conv = 35                               # uptrend base
        if r3 < 10:
            conv += 32; dip = f"deep dip (RSI3 {r3:.0f}) — prime add"
        elif r3 < 30:
            conv += 16; dip = f"shallow pullback (RSI3 {r3:.0f})"
        else:
            dip = f"no dip yet (RSI3 {r3:.0f}) — extended"
        why = f"Uptrend intact; {dip}."
    else:
        side, book = "SHORT", "Shorts Lab"
        sl = round(price * (1 + 0.0169), 1)     # forensic geometry
        tp = round(price * (1 - 0.0507), 1)     # 3:1
        conv = 20                               # downtrend base
        parts = ["downtrend"]
        if fb is not None:
            conv += min(30, max(0, fb / 2.0 * 30))
            parts.append(f"funding {fb:+.1f}bp"
                         + (" (hot)" if fb > 1.5 else ""))
        broke = lo20 is not None and price < lo20
        if broke:
            conv += 30; parts.append("broke the 20-bar low")
        elif lo20 is not None:
            prox = max(0.0, 1 - (price / lo20 - 1) / 0.01)   # within 1% above
            conv += round(18 * prox)
            parts.append(f"{(price/lo20-1)*100:.2f}% above breakdown")
        if pop4h < 0:
            conv += min(8, -pop4h * 3)
        why = "; ".join(parts).capitalize() + "."
    conv = int(max(5, min(95, round(conv))))
    risk = abs(price - sl) / price * 100
    reward = abs(tp - price) / price * 100
    return {
        "side": side, "book": book,
        "entry": round(price, 1), "tp": tp, "sl": sl,
        "risk_pct": round(risk, 2), "reward_pct": round(reward, 2),
        "rr": round(reward / risk, 1) if risk else 0,
        "conviction": conv,
        "why": why,
    }


def compute_live_read(candles_1h, candles_4h, candles_1d, funding_bps,
                      state, gold_daily=None) -> dict:
    price = float(candles_1h["close"].iloc[-1])
    cv = vol_gated_ma(candles_4h, fast=20, slow=100, min_atr_pct=1.5).iloc[-1]
    champ = int(cv) if cv == cv else 0
    market = _annualized_vol(candles_1d)

    atr1h = float(_atr(candles_1h, 14).iloc[-1])
    atr1h_pct = round(atr1h / price * 100, 2) if price else 0.0
    r3 = float(rsi(candles_1h["close"], 3).iloc[-1])
    lo20_raw = candles_1h["low"].rolling(20).min().shift(1).iloc[-1]
    lo20 = round(float(lo20_raw), 1) if lo20_raw == lo20_raw else None
    fb = round(funding_bps, 2) if funding_bps is not None else None
    pop4h = round((price / float(candles_1h["close"].iloc[-5]) - 1) * 100, 2) \
        if len(candles_1h) >= 5 else 0.0
    ledger = round(float(state.get("virtual_equity", 0) or 0), 2)
    goal = round(float(state.get("goal", 2000) or 2000), 2)

    position = _open_position(state)
    thesis = _thesis(champ, price, fb, r3, lo20, pop4h)

    # the Newsdesk's armed/pending news trade — the HUD must NEVER say
    # "nothing to do" while a trade is cocked and counting down. Tagged with
    # its symbol so a viewer looking at gold/ETH/etc. can still be told a
    # BTC news trade is armed, without mistaking it for THEIR symbol's news.
    armed = None
    nd_pending = state.get("newsdesk", {}).get("pending")
    if nd_pending:
        try:
            from datetime import datetime as _dt, timedelta as _td
            bar_open = _dt.strptime(nd_pending["direction_bar_open_ts"],
                                    "%Y-%m-%d %H:%M:%S UTC")
            decision_iso = (bar_open + _td(hours=1)).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            decision_iso = None
        armed = {"book": "The Newsdesk", "symbol": "BTC-USDT",
                 "headline": str(nd_pending.get("headline", ""))[:160],
                 "decision_ts": decision_iso}

    # --- what each book is waiting for (only meaningful when flat) ----------
    benched = state.get("benched_triggers", [])
    waiting = []
    # THE RIDE
    waiting.append({
        "name": "The Ride",
        "text": "riding the trend up" if champ == 1 else "trend flat — standing aside",
        "kind": "trend", "ready": champ == 1,
    })
    # THE STRIKES (dip-buy in an uptrend)
    if champ == 1:
        waiting.append({
            "name": "The Strikes",
            "text": "dip-buy: needs RSI3 < 10", "now": round(r3, 0),
            "need": 10, "kind": "rsi_below", "ready": r3 < 10,
        })
    else:
        waiting.append({"name": "The Strikes",
                        "text": "asleep — needs an uptrend", "kind": "none",
                        "ready": False})
    # SHORTS LAB (needs trend down + a funding/breakdown trigger)
    if champ != 0:
        waiting.append({"name": "Shorts Lab",
                        "text": "asleep — trend isn't down", "kind": "none",
                        "ready": False})
    elif fb is None:
        waiting.append({"name": "Shorts Lab", "text": "funding unreadable",
                        "kind": "none", "ready": False})
    else:
        waiting.append({
            "name": "Shorts Lab",
            "text": "short: needs funding > +2.0 + breakdown",
            "now": fb, "need": 2.0, "kind": "funding",
            "level": lo20,   # panel shows live price-vs-breakdown
            "ready": fb > 2.0,
        })

    # --- one-line thought ---------------------------------------------------
    if position:
        thought = f"In a {position['side'].lower()} ({position['book']}) — managing it."
    elif armed:
        thought = "News trade ARMED — direction decides at the bar close."
    elif any(w.get("ready") for w in waiting):
        armed_names = ", ".join(w["name"] for w in waiting if w.get("ready"))
        thought = f"{armed_names} armed — watching for the entry."
    elif champ == 1:
        thought = "Trend's up. Riding, waiting for a dip to add."
    else:
        thought = "Quiet tape. Nothing to do but watch."

    symbols = _build_symbols(state, position, thesis, waiting, armed,
                             gold_daily)

    return {
        # --- OLD v2 keys, kept verbatim for one deploy cycle (backward
        # compat for a stale extension) — always BTC-USDT's own numbers ---
        "ts": datetime.now(timezone.utc).isoformat(),
        "price": round(price, 1),
        "market": market,
        "trend": "UP" if champ == 1 else "FLAT/DOWN",
        "ledger": ledger,
        "funding_bps": fb,
        "atr1h_pct": atr1h_pct,
        "position": position,
        "armed": armed,
        "thesis": thesis,
        "waiting": waiting,
        "benched": benched,
        "thought": thought,
        # --- NEW v3 keys ------------------------------------------------
        "global": {
            "equity": ledger,
            "goal": goal,
            "market": market,
            "thought": thought,
            "armed": armed,
        },
        "symbols": symbols,
    }


def write_live_read(live_feed, state, save=True):
    try:
        from step5_paper_trade import current_funding_bps, save_state
        c1 = live_feed.get_candles("BTC-USDT", "1h", 60)
        c4 = live_feed.get_candles("BTC-USDT", "4h", 300)
        cd = live_feed.get_candles("BTC-USDT", "1d", 400)
        fb = current_funding_bps(live_feed, "BTC-USDT")

        # ONE extra candles call per 60s heartbeat, for the Gold Book's
        # flat-state levels (donchian55 high + EMA20) — see _gold_status.
        # Isolated in its own try/except so a gold-feed hiccup degrades
        # gold's card to {"status": {"mode": "unknown"}} and never takes
        # down the BTC snapshot the rest of this function builds.
        try:
            from gold_book import SYMBOL as GOLD_SYMBOL
            gold_daily = live_feed.get_candles(GOLD_SYMBOL, "1d", 90)
        except Exception as e:
            print(f"  live_read: gold candles unavailable ({str(e)[:60]})")
            gold_daily = None

        snap = compute_live_read(c1, c4, cd, fb, state, gold_daily=gold_daily)
        state["live_read"] = snap
        if save:
            save_state(state)
        return snap
    except Exception as e:
        print(f"  live_read skipped: {str(e)[:80]}")
        return None
