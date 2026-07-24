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

import json
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

# ---------------------------------------------------------------------------
# THE VISIBLE PAPER DESK (2026-07-24) — surfacing tradfi_engine.py's and
# spx_book.py's internal-paper ledgers so Wallace can watch them the way he
# watches BloFin. Every real TradFi demo broker (Alpaca/Capital.com/OANDA)
# demands ID verification he won't do, and BloFin demo has no real S&P/oil
# instruments — so these stay self-contained paper books, but they no
# longer stay INVISIBLE. This file only READS tradfi_engine's and
# spx_book's state dicts (never imports those modules — no coupling, no
# risk of touching their trading logic) and republishes a display-only
# `paper` snapshot, exactly like the rest of this file does for every
# other book.
#
# tradfi_engine.py trades ONE shared paper ledger (state["tradfi_engine"])
# across its 2-symbol universe (CL=F oil, SPY S&P) — MAX_CONCURRENT=2, so
# both can be open at once. spx_book.py is a SEPARATE, dedicated S&P
# dip-buy system with its OWN ledger (state["spx_book"]). That's 3 cards,
# not 2: TradFi-Oil and TradFi-S&P share one equity number (it IS one
# account trading two instruments — shown honestly, not hidden), and
# S&P Dip-Buy has its own.
# v2 (2026-07-24, "I want to SEE the trade happening, like BloFin, just
# automated"): the paper desk grew from a stats table into a real trading
# screen — a candlestick chart per market with the position drawn on it
# (entry/stop/target lines) plus a trade log. The chart data is fetched
# SERVER-SIDE (yfinance, in write_live_read) and published straight into
# the `paper` block specifically to dodge CORS entirely — no client-side
# third-party fetch, no browser blocking a cross-origin request the way
# Yahoo/Stooq both do (see write_live_read's paper-price comment for what
# was actually tested).
PAPER_START_EQUITY_FALLBACK = 2000.0   # display-only fallback if a book's
                                       # own state hasn't initialized yet
                                       # (mirrors both books' own starting
                                       # ledger — NOT imported from them)

PAPER_TRADFI_MARKETS = [
    ("CL=F", "Oil", "TradFi Engine · Oil"),
    ("SPY", "S&P 500", "TradFi Engine · S&P 500"),
]

PAPER_TRADE_LOG_CAP = 20      # "I want it logged" — last 20 closed trades
PAPER_CANDLE_BARS = 120       # 1h bars — the chart's visible window


def _paper_recent(rows, n=PAPER_TRADE_LOG_CAP):
    """Cap any trade/daybook list to the most recent `n` entries. Every
    source list here (daybook, sb['trades']) is already append-order
    (oldest-first), so the tail is the most recent — reversed so index 0
    is the newest, matching how the dashboard shows other trade lists."""
    return list(reversed(rows[-n:])) if rows else []


def _tradfi_log_exits(symbol, limit=PAPER_TRADE_LOG_CAP):
    """BEST-EFFORT enrichment only: entry/exit price + the exit reason
    (SL hit/TP hit/time exit) for tradfi_engine's most recent closed
    trades. state['tradfi_engine']['daybook'] (the authoritative source
    for PnL/W-L, read directly in _tradfi_book_entry) does NOT carry
    entry/exit prices or a reason label — only tradfi_engine.py's
    log_event() calls do (action 'tradfi_enter'/'tradfi_exit'), mirrored
    to this process's LOCAL event log (step5_paper_trade.LOG_FILE).

    This file is ephemeral on a cloud redeploy and this pairing is index
    a heuristic (FIFO-matched by symbol, newest-first, aligned against
    the daybook by position) — never authoritative. A miss just means
    the trade log's entry/exit/reason columns show blank for that row;
    the PnL and date (from the daybook) are never affected. Wrapped
    entirely in try/except — this must never be the reason a paper card
    fails to publish."""
    try:
        from step5_paper_trade import LOG_FILE
        import os
        if not os.path.exists(LOG_FILE):
            return []
        pending_entries = []
        exits = []
        with open(LOG_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("symbol") != symbol:
                    continue
                action = ev.get("action")
                if action == "tradfi_enter":
                    pending_entries.append(ev)
                elif action == "tradfi_exit":
                    entry_ev = pending_entries.pop(0) if pending_entries \
                        else None
                    exits.append({
                        "entry": entry_ev.get("entry") if entry_ev else None,
                        "exit": ev.get("exit_price"),
                        "reason": ev.get("reason"),
                    })
        return exits[-limit:]
    except Exception:
        return []


def _fmt_candles(hist_df, bars=PAPER_CANDLE_BARS):
    """A yfinance OHLC DataFrame (Datetime index, Open/High/Low/Close
    columns) -> [{t, o, h, l, c}, ...], oldest-first, capped to the last
    `bars` rows, timestamps normalized to UTC ISO8601. Any row that fails
    to convert is skipped rather than aborting the whole chart."""
    if hist_df is None or not len(hist_df):
        return []
    out = []
    for ts, row in hist_df.tail(bars).iterrows():
        try:
            t_iso = ts.tz_convert("UTC").isoformat() if ts.tzinfo is not None \
                else ts.tz_localize("UTC").isoformat()
            out.append({
                "t": t_iso,
                "o": round(float(row["Open"]), 4),
                "h": round(float(row["High"]), 4),
                "l": round(float(row["Low"]), 4),
                "c": round(float(row["Close"]), 4),
            })
        except Exception:
            continue
    return out


def _tradfi_open_dict(t):
    """state['tradfi_engine']['open_trades'][i] -> the paper block's
    {side, entry, stop, target, contracts_or_notional, opened_at} shape.
    tradfi_engine's trade dict uses stop_price/target_price/shares (NOT
    sl_price/tp_price/contracts like the crypto books' _norm_trade
    expects) — normalized separately here rather than overloading
    _norm_trade with a third key-naming convention."""
    if not t:
        return None
    direction = t.get("direction", 1)
    return {
        "side": "SHORT" if direction < 0 else "LONG",
        "entry": t.get("entry_price"),
        "stop": t.get("stop_price"),
        "target": t.get("target_price"),
        "contracts_or_notional": t.get("shares"),
        "notional": t.get("notional"),
        "leverage": t.get("leverage"),
        "opened_at": t.get("entry_time"),
    }


def _spx_open_dict(t):
    """spx_book's open_trade -> the same {side, entry, stop, target,
    contracts_or_notional, opened_at} shape. This book is a pure dip-buy
    (always LONG) that exits on an RSI/SMA SIGNAL, not a price level — it
    carries no stop/target at all (see spx_book.py's module docstring: "no
    per-trade stop"), so those two fields degrade to None rather than a
    fabricated number."""
    if not t:
        return None
    return {
        "side": "LONG",
        "entry": t.get("entry_price"),
        "stop": None,
        "target": None,
        "contracts_or_notional": t.get("shares"),
        "notional": t.get("notional"),
        "leverage": None,   # spx_book doesn't store per-trade leverage
        "opened_at": t.get("entry_time") or t.get("entry_date"),
    }


def _tradfi_book_entry(eng, symbol, market, name, market_data=None):
    """One TradFi-engine card (Oil or S&P) for the paper block. `eng` is
    state.get('tradfi_engine', {}) — every read below is defensive
    (.get with defaults) so a partially-initialized or pre-migration
    engine dict degrades to a flat/empty card instead of raising.
    `market_data` is write_live_read's {symbol: {price, as_of, candles,
    stale}} — this function never fetches network data itself."""
    ledger_equity = round(float(eng.get("ledger_equity",
                                        PAPER_START_EQUITY_FALLBACK) or 0), 2)
    open_trades = eng.get("open_trades", []) or []
    t = next((x for x in open_trades if x.get("symbol") == symbol), None)
    daybook = [r for r in (eng.get("daybook", []) or [])
              if r.get("symbol") == symbol]
    wins = sum(1 for r in daybook if (r.get("outcome_pnl") or 0) > 0)
    losses = len(daybook) - wins
    today_str = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    today_pnl = round(sum(r.get("outcome_pnl") or 0 for r in daybook
                          if r.get("date") == today_str), 2)
    all_time_pnl = round(sum(r.get("outcome_pnl") or 0 for r in daybook), 2)

    recent_daybook = _paper_recent(daybook)              # newest-first
    log_exits_desc = list(reversed(_tradfi_log_exits(symbol)))  # newest-first
    trades = []
    for i, r in enumerate(recent_daybook):
        log_row = log_exits_desc[i] if i < len(log_exits_desc) else {}
        trades.append({
            "side": (r.get("dir") or "").upper() or None,
            "entry": log_row.get("entry"), "exit": log_row.get("exit"),
            "pnl": r.get("outcome_pnl"), "reason": log_row.get("reason"),
            "closed_date": r.get("date"), "hold_min": r.get("hold_min"),
            "setup": r.get("setup"),
        })

    book = {
        "name": name, "market": market, "symbol": symbol,
        "ledger_equity": ledger_equity,
        "open": _tradfi_open_dict(t),
        "record": {"w": wins, "l": losses},
        "today_pnl": today_pnl, "all_time_pnl": all_time_pnl,
        "trades": trades,
        "candles": [],
    }
    md = (market_data or {}).get(symbol)
    if md:
        if md.get("price") is not None:
            book["last_price"] = {"price": md["price"], "as_of": md.get("as_of"),
                                  "stale": bool(md.get("stale"))}
        book["candles"] = md.get("candles") or []
    return book


def _spx_book_entry(sb, market_data=None):
    """The spx_book.py card for the paper block. `sb` is
    state.get('spx_book', {}) — same defensive-read contract as
    _tradfi_book_entry. Shares its chart/price feed with TradFi's S&P
    slot (both trade SPY) — keyed the same way in `market_data`."""
    ledger_equity = round(float(sb.get("virtual_equity",
                                       PAPER_START_EQUITY_FALLBACK) or 0), 2)
    wins = int(sb.get("wins", 0) or 0)
    n = int(sb.get("n", 0) or 0)
    losses = max(0, n - wins)
    trades_log = sb.get("trades", []) or []
    today_str = f"{datetime.now(timezone.utc):%Y-%m-%d}"
    today_pnl = round(sum(t.get("pnl") or 0 for t in trades_log
                          if t.get("exit_date") == today_str), 2)
    all_time_pnl = round(float(sb.get("realized_pnl_total", 0.0) or 0), 2)
    trades = [{"side": "LONG", "entry": t.get("entry_price"),
              "exit": t.get("exit_price"), "pnl": t.get("pnl"),
              "closed_date": t.get("exit_date"), "reason": t.get("reason")}
             for t in _paper_recent(trades_log)]
    book = {
        "name": "S&P Dip-Buy", "market": "S&P 500", "symbol": "SPY",
        "ledger_equity": ledger_equity,
        "open": _spx_open_dict(sb.get("open_trade")),
        "record": {"w": wins, "l": losses},
        "today_pnl": today_pnl, "all_time_pnl": all_time_pnl,
        "trades": trades,
        "candles": [],
    }
    md = (market_data or {}).get("SPY")
    if md:
        if md.get("price") is not None:
            book["last_price"] = {"price": md["price"], "as_of": md.get("as_of"),
                                  "stale": bool(md.get("stale"))}
        book["candles"] = md.get("candles") or []
    return book


def _build_paper(state, market_data=None):
    """The paper block: {books: [...], updated}. Reads ONLY
    state['tradfi_engine'] and state['spx_book'] — never imports either
    module. Missing state keys (this engine hasn't run its first cycle
    yet) degrade to an empty books list rather than fabricating cards for
    a book that has never actually initialized; a present-but-fresh dict
    (the book HAS run, just flat) still builds full flat/empty-looking
    cards. Every book is built in its own try/except so one book's bad
    data can never blank out the others or the rest of the snapshot.
    `market_data` is write_live_read's {symbol: {price, as_of, candles,
    stale}} — see that function for how it's sourced and why."""
    books = []
    if "tradfi_engine" in state:
        eng = state.get("tradfi_engine") or {}
        for symbol, market, name in PAPER_TRADFI_MARKETS:
            try:
                books.append(_tradfi_book_entry(eng, symbol, market, name,
                                                market_data))
            except Exception as e:
                print(f"  live_read: paper book {name} skipped "
                     f"({str(e)[:60]})")
    if "spx_book" in state:
        try:
            books.append(_spx_book_entry(state.get("spx_book") or {},
                                         market_data))
        except Exception as e:
            print(f"  live_read: paper book S&P Dip-Buy skipped "
                 f"({str(e)[:60]})")
    return {"books": books,
            "updated": datetime.now(timezone.utc).isoformat()}


def _paper_hud_position(book, t, side="from_trade"):
    """Same normalized position shape every OTHER symbols[...] card uses
    (see _norm_trade) — book/side/dir/entry/stop/target/contracts/
    contract_size/trigger — built from a TradFi-engine trade dict
    (stop_price/target_price/shares naming, not _norm_trade's sl_price/
    tp_price/contracts) or an spx_book open_trade (no stop/target at
    all, always long)."""
    if not t:
        return None
    if side == "long_only":          # spx_book: always long, signal exit
        direction = 1
        stop = target = None
    else:
        direction = t.get("direction", 1)
        stop, target = t.get("stop_price"), t.get("target_price")
    return {
        "book": book,
        "side": "SHORT" if direction < 0 else "LONG",
        "dir": direction,
        "entry": t.get("entry_price"),
        "stop": stop,
        "target": target,
        "contracts": t.get("shares", 0),
        "contract_size": 1,
        "trigger": book,
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
    # daily_pick moved from a single open_trade to a concurrent open_trades
    # list (2026-07-24 learning-engine upgrade) — read defensively so an
    # un-migrated state file (pre-upgrade shape) doesn't crash this card.
    pick_open_trades = state.get("daily_pick", {}).get("open_trades")
    if pick_open_trades is None:
        legacy = state.get("daily_pick", {}).get("open_trade")
        pick_open_trades = [legacy] if legacy else []
    pick_t = next((t for t in pick_open_trades if t.get("symbol") == "BTC-USDT"),
                  None)
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
    # --- holding) — read defensively, this book may not be deployed yet.
    # 2026-07-24 learning-engine upgrade: daily_pick can now hold UP TO 3
    # CONCURRENT positions (state["daily_pick"]["open_trades"] is a list,
    # replacing the old single open_trade) — index by symbol so every
    # concurrently-held symbol gets its own card, not just the first. ------
    dp = state.get("daily_pick", {}) or {}
    dp_open_trades = dp.get("open_trades")
    if dp_open_trades is None:
        legacy = dp.get("open_trade")
        dp_open_trades = [legacy] if legacy else []
    dp_by_symbol = {t["symbol"]: t for t in dp_open_trades if t}
    rotation_status = {"mode": "rotation",
                       "text": "in the Daily Pick rotation, scored every "
                               "2 hours"}

    for sym in ("SOL-USDT", "TSLA-USDT"):
        t = dp_by_symbol.get(sym)
        if t:
            symbols[sym] = {
                "display": DISPLAY_NAMES[sym], "book": "Daily Pick",
                "position": _norm_trade("Daily Pick", t,
                                        CONTRACT_SIZE["Daily Pick"]),
            }
        else:
            symbols[sym] = {
                "display": DISPLAY_NAMES[sym], "book": "Daily Pick",
                "position": None, "status": rotation_status,
            }

    # any OTHER symbol the daily pick currently holds (not one of the named
    # ones above, and there may be several now that up to 3 can be open at
    # once) still gets exposed, under its own instId
    for sym, t in dp_by_symbol.items():
        if sym not in symbols:
            symbols[sym] = {
                "display": DISPLAY_NAMES.get(sym, sym.replace("-USDT", "")),
                "book": "Daily Pick",
                "position": _norm_trade("Daily Pick", t,
                                        CONTRACT_SIZE["Daily Pick"]),
            }

    # --- OIL-PAPER / SPX-PAPER — the paper desk, pseudo-instIds so a HUD
    # viewer on a relevant page can render them like any other symbol.
    # Never BloFin instIds (no such venue exists for these) — "-PAPER"
    # marks them unmistakably as the internal paper books, never mistaken
    # for a real tradeable instrument. ------------------------------------
    eng = state.get("tradfi_engine", {}) or {}
    eng_open = eng.get("open_trades", []) or []
    oil_t = next((x for x in eng_open if x.get("symbol") == "CL=F"), None)
    spx_tradfi_t = next((x for x in eng_open if x.get("symbol") == "SPY"),
                        None)
    symbols["OIL-PAPER"] = {
        "display": "Oil (paper)", "book": "TradFi Engine · Oil",
        "position": _paper_hud_position("TradFi Engine · Oil", oil_t),
    }
    if not oil_t:
        symbols["OIL-PAPER"]["status"] = {
            "mode": "rotation",
            "text": "paper book — scored every 2h, no real venue exists yet",
        }

    # S&P has TWO paper systems (tradfi_engine's SPY slot + spx_book's
    # dedicated dip-buy) — spx_book's own dedicated position wins when
    # both happen to be flat/open at once, since it's literally "the S&P
    # book"; falls back to the TradFi engine's SPY slot when spx_book is
    # flat, so a live TradFi S&P trade is never hidden either.
    sb = state.get("spx_book", {}) or {}
    spx_dipbuy_t = sb.get("open_trade")
    if spx_dipbuy_t:
        symbols["SPX-PAPER"] = {
            "display": "S&P 500 (paper)", "book": "S&P Dip-Buy",
            "position": _paper_hud_position("S&P Dip-Buy", spx_dipbuy_t,
                                            side="long_only"),
        }
    elif spx_tradfi_t:
        symbols["SPX-PAPER"] = {
            "display": "S&P 500 (paper)", "book": "TradFi Engine · S&P 500",
            "position": _paper_hud_position("TradFi Engine · S&P 500",
                                            spx_tradfi_t),
        }
    else:
        symbols["SPX-PAPER"] = {
            "display": "S&P 500 (paper)", "book": "S&P Dip-Buy",
            "position": None,
            "status": {"mode": "rotation",
                      "text": "paper book — dip-buy waits for RSI2 < 5 "
                              "above the 200-day"},
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
                      state, gold_daily=None, tradfi_market=None) -> dict:
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
    paper = _build_paper(state, tradfi_market)

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
        "paper": paper,
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

        # PAPER DESK live prices + chart — tested (2026-07-24) from a REAL
        # browser fetch() (not just curl): Yahoo's query endpoints send no
        # Access-Control-Allow-Origin header (blocked by CORS before the
        # 429 rate-limit even matters) and Stooq's CSV endpoint now sits
        # behind a JS proof-of-work challenge a plain cross-origin fetch
        # can never pass — both came back "TypeError: Failed to fetch" in
        # an actual page context. So both the price AND the chart's
        # candles are sourced HERE, server-side, straight off yfinance —
        # deliberately NOT via tradfi_engine (never import that module) —
        # and published into the snapshot so the dashboard never makes its
        # own network call for them at all. One call per symbol, each
        # isolated so a Yahoo hiccup degrades that ONE book, never the
        # rest of the snapshot. On a hiccup, this reuses the PREVIOUS
        # snapshot's candles (read off state — the one from before this
        # function overwrites it below) so the chart never goes blank,
        # just stale — marked "stale": true so the dashboard can say so.
        prev_paper_books = {
            b.get("symbol"): b
            for b in (state.get("live_read", {}) or {}).get("paper", {})
                          .get("books", []) or []
            if b.get("symbol")
        }
        # `_yf` is resolved ONCE, outside the per-symbol loop, but a failure
        # here (yfinance not installed / import error) must NOT skip the
        # per-symbol previous-candles fallback below — a total import
        # failure degrades exactly like a single symbol's fetch failing,
        # never worse. That's why the fallback loop is unconditional and
        # `_yf` is simply None (never fetched) on an import failure.
        try:
            import yfinance as _yf
        except Exception as e:
            print(f"  live_read: yfinance unavailable for paper prices/"
                 f"charts ({str(e)[:60]})")
            _yf = None

        tradfi_market = {}
        for _sym in ("CL=F", "SPY"):
            entry = {}
            if _yf is not None:
                try:
                    hist = _yf.Ticker(_sym).history(period="10d", interval="1h")
                    if hist is not None and len(hist):
                        entry["price"] = round(float(hist["Close"].iloc[-1]), 2)
                        entry["as_of"] = f"{datetime.now(timezone.utc):%H:%M UTC}"
                        entry["candles"] = _fmt_candles(hist)
                except Exception as e:
                    print(f"  live_read: {_sym} paper price/chart "
                         f"unavailable ({str(e)[:60]})")
            if not entry.get("candles"):
                prev = prev_paper_books.get(_sym) or {}
                prev_candles = prev.get("candles")
                if prev_candles:
                    entry.setdefault("candles", prev_candles)
                    prev_price = prev.get("last_price", {}) or {}
                    entry.setdefault("price", prev_price.get("price"))
                    entry.setdefault("as_of", prev_price.get("as_of"))
                    entry["stale"] = True
            if entry:
                tradfi_market[_sym] = entry

        snap = compute_live_read(c1, c4, cd, fb, state, gold_daily=gold_daily,
                                 tradfi_market=tradfi_market)
        state["live_read"] = snap
        if save:
            save_state(state)
        return snap
    except Exception as e:
        print(f"  live_read skipped: {str(e)[:80]}")
        return None
