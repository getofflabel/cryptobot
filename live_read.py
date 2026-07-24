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
import pandas as pd
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

# ---------------------------------------------------------------------------
# BLOFIN-CLONE PAPER DESK v4 (2026-07-24) — "if you're gonna do a paper
# desk, build the entire thing... you will literally have to copy BloFin
# 1:1." Two upgrades over v3 (the single-1h-chart version above):
#   1. MULTI-TIMEFRAME candles (5m/15m/1h/4h/1d), published as COMPACT
#      [t,o,h,l,c] arrays (t = unix epoch seconds, not an ISO string) —
#      publishing 5 timeframes x 2 markets x up to 150 bars each in
#      object-per-candle form would roughly triple the payload for no
#      reason; a bare array is all the dashboard's chart code needs.
#   2. Honest BloFin-style position math (margin, est. liq price, break
#      even price, margin ratio, fees) computed from the SAME numbers the
#      paper engines already store — never a fabricated exchange feed.
# ---------------------------------------------------------------------------

PAPER_TIMEFRAMES = [
    # (label, yfinance interval, yfinance period). 4h has interval=None —
    # yfinance has no native 4h bar, so it's resampled from the SAME 1h
    # fetch in the loop below (_resample_4h) rather than costing a second
    # network call. Periods are yfinance's actual real limits for each
    # interval ("pull what each allows"); the OUTPUT is separately capped
    # to PAPER_CANDLE_CAP bars per timeframe — see _fmt_candles_compact.
    ("5m", "5m", "60d"),
    ("15m", "15m", "60d"),
    ("1h", "60m", "730d"),
    ("4h", None, None),
    ("1d", "1d", "2y"),
]
PAPER_CANDLE_CAP = 150   # per timeframe, per market

MAINT_MARGIN_RATE_ASSUMED = 0.005   # 0.5% — OUR assumption, used for the
                                     # est. liq price / margin ratio math
                                     # below. BloFin does not publish a
                                     # maintenance margin rate for CL=F or
                                     # SPY because no such BloFin
                                     # instrument exists — this is labelled
                                     # (mmr_assumed) on every payload that
                                     # carries a liq/margin-ratio number
                                     # built from it, never presented as
                                     # exchange truth.

# Fee constants MIRRORED (read only, never imported — see this file's
# module-isolation contract below) from the two engines that actually run
# these two paper ledgers:
#   tradfi_engine.py: FEE_BPS_FUTURES=2.0 (CL=F), FEE_BPS_STANDARD=1.0 (SPY)
#   spx_book.py:      FEE_BPS_PER_LEG=1.0, LEVERAGE=4.0 fixed (not stored
#                      per-trade — see _spx_open_dict)
# These are OUR modeled paper-ledger fees, NOT BloFin's real futures
# schedule. Verified against exchange.py's BlofinExchange (the venue
# step5_paper_trade.py/blofin_private.py actually trade BTC-USDT on):
# TAKER_FEE_BPS=6.0 / MAKER_FEE_BPS=2.0 — i.e. BloFin's real VIP0 futures
# rate (0.02% maker / 0.06% taker) IS exactly what this repo already
# models for BTC, no discrepancy there. But CL=F/SPY aren't BloFin
# instruments at all — no exchange charges these paper trades anything —
# so their fee is shown as OUR flat modeled rate (maker==taker, no tier),
# never dressed up as BloFin's own schedule. See _fee_block.
TRADFI_FEE_BPS = {"CL=F": 2.0, "SPY": 1.0}
SPX_DIPBUY_FEE_BPS = 1.0
SPX_DIPBUY_LEVERAGE = 4.0


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
                        # log_event() stamps EVERY event with this at write
                        # time (step5_paper_trade.py's log_event) — the one
                        # real close TIMESTAMP available for a paper trade
                        # (closed_date on the daybook row is date-only).
                        # v5 (2026-07-24, "treat paper trades like LIVE"):
                        # threaded into the published trade so the
                        # dashboard can place a paper trade correctly in
                        # its 1D/7D/30D/etc window, same as a BloFin trade.
                        "closed_at": ev.get("logged_at"),
                    })
        return exits[-limit:]
    except Exception:
        return []


def _spx_log_exits(limit=PAPER_TRADE_LOG_CAP):
    """Same best-effort LOCAL-log lookup as _tradfi_log_exits, for
    spx_book.py's 'spx_book_exit' events — which carry no 'symbol' key of
    their own (spx_book only ever trades SPY), so this doesn't filter by
    symbol. Returns just the close timestamp (spx_book's own state
    already carries entry/exit price/reason — see _spx_book_entry — this
    only fills the ONE thing state doesn't: a real close timestamp,
    exit_date being date-only). Same ephemeral-file caveat, same
    never-authoritative contract, wrapped in try/except."""
    try:
        from step5_paper_trade import LOG_FILE
        import os
        if not os.path.exists(LOG_FILE):
            return []
        out = []
        with open(LOG_FILE) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("action") != "spx_book_exit":
                    continue
                out.append(ev.get("logged_at"))
        return out[-limit:]
    except Exception:
        return []


def _fmt_candles_compact(hist_df, cap=PAPER_CANDLE_CAP):
    """A yfinance/resampled OHLC DataFrame (DatetimeIndex, Open/High/Low/
    Close columns) -> [[t, o, h, l, c], ...], oldest-first, capped to the
    last `cap` rows. `t` is UNIX epoch SECONDS (UTC, int) rather than an
    ISO8601 string — with 5 timeframes x 2 markets x up to 150 bars each
    now published every cycle, an epoch int is roughly a third of the
    bytes an ISO string costs once JSON-encoded, and every array element
    stays a bare number — no {t,o,h,l,c} key names repeated 1,500 times.
    Any row that fails to convert is skipped rather than aborting the
    whole array."""
    if hist_df is None or not len(hist_df):
        return []
    out = []
    for ts, row in hist_df.tail(cap).iterrows():
        try:
            ts_utc = ts.tz_convert("UTC") if ts.tzinfo is not None \
                else ts.tz_localize("UTC")
            out.append([
                int(ts_utc.timestamp()),
                round(float(row["Open"]), 4),
                round(float(row["High"]), 4),
                round(float(row["Low"]), 4),
                round(float(row["Close"]), 4),
            ])
        except Exception:
            continue
    return out


def _resample_4h(hist_1h):
    """1h OHLC -> 4h OHLC by resampling — yfinance has no native 4h
    interval, so this reuses the SAME 1h fetch rather than costing a
    second network call. Bucket = [t, t+4h); label='left', closed='left'
    means the bucket is NAMED by its start time and a bar landing exactly
    on a boundary belongs to the bucket that OPENS there, not the one that
    just closed — the standard OHLC resample convention, and the one a 4H
    candle's own timestamp means (its open time), same as every other
    timeframe published here."""
    if hist_1h is None or not len(hist_1h):
        return None
    try:
        agg = hist_1h.resample("4h", label="left", closed="left").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last",
        })
        return agg.dropna(subset=["Open", "High", "Low", "Close"])
    except Exception:
        return None


def _24h_window_stats(hist_1h):
    """Rolling 24-CALENDAR-HOUR high/low/change off the 1h series — a real
    elapsed-time window, not a fixed bar count. That matters because CL=F
    trades near-continuously and SPY doesn't: a gappy market (SPY over a
    weekend) correctly shows fewer bars in the trailing 24h, never a
    fabricated one. Returns None (never a guess) if under 2 bars fall in
    the window — not enough to compute a change."""
    if hist_1h is None or not len(hist_1h):
        return None
    try:
        last_ts = hist_1h.index[-1]
        last_close = float(hist_1h["Close"].iloc[-1])
        cutoff = last_ts - pd.Timedelta(hours=24)
        window = hist_1h[hist_1h.index >= cutoff]
        if len(window) < 2:
            return None
        ref_close = float(window["Close"].iloc[0])
        high = float(window["High"].max())
        low = float(window["Low"].min())
        change_pct = round((last_close / ref_close - 1) * 100, 2) \
            if ref_close else None
        return {"change_24h_pct": change_pct, "high_24h": round(high, 4),
                "low_24h": round(low, 4)}
    except Exception:
        return None


def _liq_price(entry, leverage, direction, mmr=MAINT_MARGIN_RATE_ASSUMED):
    """ISOLATED-margin estimated liquidation price:
      long:  entry * (1 - 1/leverage + mmr)
      short: entry * (1 + 1/leverage - mmr)
    See MAINT_MARGIN_RATE_ASSUMED's comment — mmr is OUR assumption, not a
    published BloFin figure (no such BloFin instrument exists for CL=F/
    SPY to publish one for)."""
    if not entry or not leverage:
        return None
    try:
        if direction >= 0:
            return round(entry * (1 - 1 / leverage + mmr), 4)
        return round(entry * (1 + 1 / leverage - mmr), 4)
    except Exception:
        return None


def _break_even_price(entry, direction, fee_rate):
    """Exit price at which BOTH legs' round-trip fees exactly offset the
    directional move — the exact solve (not the entry*(1 +/- 2*fee)
    approximation): for a long, entry*(1+fee) [cost incl. entry fee] must
    equal X*(1-fee) [proceeds net of exit fee] -> X = entry*(1+fee)/(1-fee).
    Mirrored for a short."""
    if not entry:
        return None
    try:
        if direction >= 0:
            return round(entry * (1 + fee_rate) / (1 - fee_rate), 4)
        return round(entry * (1 - fee_rate) / (1 + fee_rate), 4)
    except Exception:
        return None


def _fee_block(fee_bps):
    """The per-book 'fees' line: maker%/taker% (deliberately EQUAL — these
    paper books charge one flat rate, no maker/taker tier, so showing them
    as equal is the honest representation, not a fabricated split) + the
    raw bps + a one-line note. See TRADFI_FEE_BPS's comment for sourcing
    and why this is NOT BloFin's real schedule."""
    pct = round(fee_bps / 100.0, 4)
    return {
        "maker_pct": pct, "taker_pct": pct, "fee_bps": fee_bps,
        "note": "modeled paper-ledger fee, not BloFin's — no real "
                "exchange charges CL=F/SPY perpetual fees",
    }


def _tradfi_open_dict(t, symbol=None):
    """state['tradfi_engine']['open_trades'][i] -> the paper block's open
    position shape. tradfi_engine's trade dict uses stop_price/
    target_price/shares (NOT sl_price/tp_price/contracts like the crypto
    books' _norm_trade expects) — normalized separately here rather than
    overloading _norm_trade with a third key-naming convention.

    v4 (2026-07-24): adds the BloFin-column math (margin, fee, est. liq
    price, break-even price) so the positions table never has to fabricate
    a number the dashboard doesn't have — every field here is computed
    from the SAME trade dict tradfi_engine.py itself stores."""
    if not t:
        return None
    direction = t.get("direction", 1)
    entry = t.get("entry_price")
    leverage = t.get("leverage")
    notional = t.get("notional")
    qty = t.get("shares")
    fee_bps = t.get("fee_bps")
    if fee_bps is None:
        fee_bps = TRADFI_FEE_BPS.get(symbol, TRADFI_FEE_BPS["SPY"])
    fee_rate = fee_bps / 10000.0
    margin = round(notional / leverage, 2) if (notional and leverage) else None
    entry_fee = round(entry * fee_rate * qty, 4) \
        if (entry is not None and qty is not None) else None
    return {
        "side": "SHORT" if direction < 0 else "LONG",
        "entry": entry,
        "stop": t.get("stop_price"),
        "target": t.get("target_price"),
        "contracts_or_notional": qty,
        "notional": notional,
        "leverage": leverage,
        "opened_at": t.get("entry_time"),
        "margin": margin,
        "margin_mode": "isolated",
        "fee_bps": fee_bps,
        "entry_fee": entry_fee,
        "liq_price": _liq_price(entry, leverage, direction),
        "break_even": _break_even_price(entry, direction, fee_rate),
        "mmr_assumed": MAINT_MARGIN_RATE_ASSUMED,
    }


def _spx_open_dict(t):
    """spx_book's open_trade -> the same open-position shape. This book is
    a pure dip-buy (always LONG) that exits on an RSI/SMA SIGNAL, not a
    price level — it carries no stop/target at all (see spx_book.py's
    module docstring: "no per-trade stop"), so those two fields degrade to
    None rather than a fabricated number. leverage/fee_bps aren't stored
    per-trade (spx_book always uses its own fixed module constants) — see
    SPX_DIPBUY_LEVERAGE/SPX_DIPBUY_FEE_BPS's sourcing comment above."""
    if not t:
        return None
    entry = t.get("entry_price")
    leverage = SPX_DIPBUY_LEVERAGE
    notional = t.get("notional")
    qty = t.get("shares")
    fee_bps = SPX_DIPBUY_FEE_BPS
    fee_rate = fee_bps / 10000.0
    margin = round(notional / leverage, 2) if notional else None
    entry_fee = round(entry * fee_rate * qty, 4) \
        if (entry is not None and qty is not None) else None
    return {
        "side": "LONG",
        "entry": entry,
        "stop": None,
        "target": None,
        "contracts_or_notional": qty,
        "notional": notional,
        "leverage": leverage,
        "opened_at": t.get("entry_time") or t.get("entry_date"),
        "margin": margin,
        "margin_mode": "isolated",
        "fee_bps": fee_bps,
        "entry_fee": entry_fee,
        "liq_price": _liq_price(entry, leverage, 1),
        "break_even": _break_even_price(entry, 1, fee_rate),
        "mmr_assumed": MAINT_MARGIN_RATE_ASSUMED,
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
            # real close timestamp when the local log still has it (see
            # _tradfi_log_exits) — None degrades gracefully; the dashboard
            # falls back to closed_date + a fixed time-of-day for window
            # placement. Lets a paper trade be merged into the SAME
            # combined trade record/stats as a real BloFin trade.
            "closed_at": log_row.get("closed_at"),
        })

    fee_bps = (t.get("fee_bps") if t else None) or \
        TRADFI_FEE_BPS.get(symbol, TRADFI_FEE_BPS["SPY"])
    book = {
        "name": name, "market": market, "symbol": symbol,
        "ledger_equity": ledger_equity,
        # TradFi-Oil and TradFi-S&P trade OUT OF THE SAME shared ledger
        # (eng['ledger_equity']) — tagged so a client summing "every
        # paper ledger" for a combined equity headline can dedupe by this
        # key instead of double-counting one account as two.
        "ledger_group": "tradfi_engine",
        "open": _tradfi_open_dict(t, symbol),
        "record": {"w": wins, "l": losses},
        "today_pnl": today_pnl, "all_time_pnl": all_time_pnl,
        "trades": trades,
        "fees": _fee_block(fee_bps),
    }
    md = (market_data or {}).get(symbol)
    if md:
        if md.get("price") is not None:
            book["last_price"] = {"price": md["price"], "as_of": md.get("as_of"),
                                  "stale": bool(md.get("stale"))}
        for k in ("change_24h_pct", "high_24h", "low_24h"):
            if md.get(k) is not None:
                book[k] = md[k]
    # NOTE: candles are NOT embedded per-book — see _build_paper's
    # top-level `candles` dict (keyed by symbol). TradFi-S&P and S&P
    # Dip-Buy both trade SPY; embedding the same ~150-bar x 5-timeframe
    # array in both book dicts would silently double the SPY payload for
    # zero benefit — the dashboard looks candles up by book["symbol"].
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
    recent_trades = _paper_recent(trades_log)             # newest-first
    exit_ts_desc = list(reversed(_spx_log_exits()))        # newest-first
    trades = []
    for i, t in enumerate(recent_trades):
        closed_at = exit_ts_desc[i] if i < len(exit_ts_desc) else None
        trades.append({"side": "LONG", "entry": t.get("entry_price"),
                       "exit": t.get("exit_price"), "pnl": t.get("pnl"),
                       "closed_date": t.get("exit_date"),
                       "reason": t.get("reason"), "closed_at": closed_at})
    book = {
        "name": "S&P Dip-Buy", "market": "S&P 500", "symbol": "SPY",
        "ledger_equity": ledger_equity,
        # spx_book's own dedicated ledger — never shared with tradfi_engine
        # (see _tradfi_book_entry's ledger_group comment).
        "ledger_group": "spx_book",
        "open": _spx_open_dict(sb.get("open_trade")),
        "record": {"w": wins, "l": losses},
        "today_pnl": today_pnl, "all_time_pnl": all_time_pnl,
        "trades": trades,
        "fees": _fee_block(SPX_DIPBUY_FEE_BPS),
    }
    md = (market_data or {}).get("SPY")
    if md:
        if md.get("price") is not None:
            book["last_price"] = {"price": md["price"], "as_of": md.get("as_of"),
                                  "stale": bool(md.get("stale"))}
        for k in ("change_24h_pct", "high_24h", "low_24h"):
            if md.get(k) is not None:
                book[k] = md[k]
    # candles NOT embedded here either — see _build_paper's top-level
    # `candles` dict, shared with TradFi's SPY slot (same symbol).
    return book


def _build_paper(state, market_data=None):
    """The paper block: {books: [...], candles: {symbol: {...}}, updated}.
    Reads ONLY state['tradfi_engine'] and state['spx_book'] — never
    imports either module. Missing state keys (this engine hasn't run its
    first cycle yet) degrade to an empty books list rather than
    fabricating cards for a book that has never actually initialized; a
    present-but-fresh dict (the book HAS run, just flat) still builds full
    flat/empty-looking cards. Every book is built in its own try/except so
    one book's bad data can never blank out the others or the rest of the
    snapshot. `market_data` is write_live_read's {symbol: {price, as_of,
    change_24h_pct, high_24h, low_24h, candles_by_tf, stale_by_tf, stale}}
    — see that function for how it's sourced and why.

    v4 (2026-07-24): candles live ONCE per symbol in the top-level
    `candles` dict, NOT embedded inside every book that trades that
    symbol — TradFi-S&P and S&P Dip-Buy both trade SPY, and duplicating a
    150-bar x 5-timeframe candle set in both book dicts would silently
    double the SPY payload for zero benefit. The dashboard looks candles
    up by a book's `symbol` key."""
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

    candles = {}
    for symbol, md in (market_data or {}).items():
        cbt = (md or {}).get("candles_by_tf")
        if cbt:
            candles[symbol] = {"candles_by_tf": cbt,
                               "stale_by_tf": (md or {}).get("stale_by_tf") or {}}

    return {"books": books, "candles": candles,
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

        # PAPER DESK live prices + MULTI-TIMEFRAME chart — tested
        # (2026-07-24) from a REAL browser fetch() (not just curl): Yahoo's
        # query endpoints send no Access-Control-Allow-Origin header
        # (blocked by CORS before the 429 rate-limit even matters) and
        # Stooq's CSV endpoint now sits behind a JS proof-of-work challenge
        # a plain cross-origin fetch can never pass — both came back
        # "TypeError: Failed to fetch" in an actual page context. So both
        # the price AND every timeframe's candles are sourced HERE,
        # server-side, straight off yfinance — deliberately NOT via
        # tradfi_engine (never import that module) — and published into
        # the snapshot so the dashboard never makes its own network call
        # for them at all.
        #
        # v4 (2026-07-24): PER-TIMEFRAME fetch+fallback, not per-symbol.
        # Each of the 5 timeframes (see PAPER_TIMEFRAMES) is fetched (or,
        # for 4h, resampled off the SAME 1h fetch) independently, each
        # isolated in its own try/except so ONE timeframe's Yahoo hiccup
        # degrades only that timeframe — never the other four, and never
        # the rest of the snapshot. On a per-timeframe miss, this reuses
        # THAT timeframe's PREVIOUSLY published bars (read off state — the
        # snapshot from before this function overwrites it below) so the
        # chart never goes blank on that timeframe, just stale — marked in
        # stale_by_tf so the dashboard can say so per-timeframe, not just
        # per-symbol.
        prev_paper_books = {
            b.get("symbol"): b
            for b in (state.get("live_read", {}) or {}).get("paper", {})
                          .get("books", []) or []
            if b.get("symbol")
        }
        # `_yf` is resolved ONCE, outside the per-symbol loop, but a failure
        # here (yfinance not installed / import error) must NOT skip the
        # per-timeframe previous-candles fallback below — a total import
        # failure degrades exactly like every timeframe's fetch failing,
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
            candles_by_tf = {}
            stale_by_tf = {}
            hist_1h_raw = None
            if _yf is not None:
                try:
                    ticker = _yf.Ticker(_sym)
                except Exception as e:
                    ticker = None
                    print(f"  live_read: {_sym} Ticker() failed "
                         f"({str(e)[:60]})")
                if ticker is not None:
                    for tf_label, interval, period in PAPER_TIMEFRAMES:
                        try:
                            if interval is None:      # 4h: resample only
                                hist = _resample_4h(hist_1h_raw)
                            else:
                                hist = ticker.history(period=period,
                                                      interval=interval)
                                if hist is not None and len(hist) \
                                        and tf_label == "1h":
                                    hist_1h_raw = hist
                            if hist is not None and len(hist):
                                candles_by_tf[tf_label] = \
                                    _fmt_candles_compact(hist)
                        except Exception as e:
                            print(f"  live_read: {_sym} {tf_label} candles "
                                 f"unavailable ({str(e)[:60]})")
                    if hist_1h_raw is not None and len(hist_1h_raw):
                        entry["price"] = round(
                            float(hist_1h_raw["Close"].iloc[-1]), 2)
                        entry["as_of"] = \
                            f"{datetime.now(timezone.utc):%H:%M UTC}"
                        stats24 = _24h_window_stats(hist_1h_raw)
                        if stats24:
                            entry.update(stats24)

            prev = prev_paper_books.get(_sym) or {}
            prev_by_tf = prev.get("candles_by_tf") or {}
            for tf_label, _interval, _period in PAPER_TIMEFRAMES:
                if candles_by_tf.get(tf_label):
                    stale_by_tf[tf_label] = False
                else:
                    prev_c = prev_by_tf.get(tf_label)
                    if prev_c:
                        candles_by_tf[tf_label] = prev_c
                        stale_by_tf[tf_label] = True

            if entry.get("price") is None:
                prev_price = prev.get("last_price", {}) or {}
                entry["price"] = prev_price.get("price")
                entry["as_of"] = prev_price.get("as_of")
                if entry["price"] is not None:
                    entry["stale"] = True
                for k in ("change_24h_pct", "high_24h", "low_24h"):
                    if prev.get(k) is not None:
                        entry[k] = prev[k]

            entry["candles_by_tf"] = candles_by_tf
            entry["stale_by_tf"] = stale_by_tf
            if entry.get("price") is not None or candles_by_tf:
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
