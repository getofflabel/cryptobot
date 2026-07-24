"""
daily_pick.py — THE DAILY PICK: owner mandate "at least one trade every
single day, no excuses" (Wallace, 2026-07-23), scanning the full BloFin
universe — crypto majors + synthetic TradFi perps — and taking exactly ONE
fresh position a day, sized and stopped off its own conviction score.
Structural template: shorts_lab.py / newsdesk.py (state dict, reconcile
against the exchange every cycle, hardened double-read _ensure_bracket,
_book_exit PnL math, entry via ensure_leverage + execute_maker_or_chase +
ONE place_tpsl bracket, record_trade_outcome for auto-bench, dry mode).

DOES NOT TOUCH daemon.py / hourly.py / gold_book.py — another agent owns
those; this file is wired into the cycle separately.

THE UNIVERSE IS SMALL ON PURPOSE — A DEMO-HOST LIMITATION, NOT A DESIGN
CHOICE. The task brief's full universe (BTC/ETH/SOL + XAU/XAG/WTIOIL/SPX +
ten stock perps) was censused live against BloFin's DEMO trading host
(demo-trading-openapi.blofin.com) before writing a line of scoring code —
round 52's own finding (step52_blofin_tradfi.py) confirmed live here again
the same day: PROD (openapi.blofin.com) lists and histories every one of
those symbols, but DEMO only lists 88 instruments total, and of the task's
named universe only BTC-USDT, ETH-USDT, SOL-USDT and XAUT-USDT (Tether
Gold — NOT XAU-USDT, which 404s on demo; see gold_book.py's own identical
substitution) are actually queryable there. XAU-USDT, XAG-USDT, WTIOIL-USDT
and every one of the ten single-stock perps (NVDA/TSLA/AAPL/MSFT/AMZN/
META/GOOGL/COIN/MSTR/HOOD-USDT) return code 152002 "Parameter instId
error" on demo's own /api/v1/market/instruments AND /api/v1/market/candles.
SPX-USDT queries fine on demo but is NOT the S&P 500: its instrument spec
marks assetClass="Crypto", it trades at ~$0.33, and it is the SPX6900
memecoin, not an index tracker (confirmed both in round 52's yfinance
cross-check and independently here) — excluded from this book's universe
for that reason, not availability. TSLA-USDT is a genuine platform quirk:
its DEMO candles endpoint returns rows, but its DEMO instrument-spec
endpoint 404s (code 122003) and its DEMO ticker returns an empty array —
i.e. it LOOKS tradeable on one endpoint and isn't on the two that matter
for actually sizing and placing an order. Rather than hand-pick around
quirks like that forever, UNIVERSE below is deliberately just the plain
list, and _probe_universe() below is a STARTUP GUARD that empirically
drops anything that fails a real DEMO candle fetch — so a future UNIVERSE
edit (BloFin adding more instruments to demo, or removing one) can never
crash this book; the symbol just gets logged and skipped, same failure
class as the instId errors above. TSLA-USDT is deliberately LEFT IN the
UNIVERSE constant despite the instrument-spec quirk: the candle probe lets
it through (its candles endpoint works), and guard (d) below (instrument
spec fetched ok) then correctly excludes it from ever actually being
PICKED until BloFin fixes that endpoint — nothing to maintain by hand.

WHY XAUT-USDT NEEDS NO SPECIAL CASE: gold_book.py already trades
XAUT-USDT live on this exact demo account. This book's generic guard (c)
("skip if the exchange already shows a position on this symbol" — a plain
private.net_position_contracts(sym) read, not book-specific) means the
daily pick automatically steps aside any day the gold book is holding —
no code here needs to know gold_book exists.

SCORING (per instrument, on its own 1h + 1d candles, both fetched from
live_feed — PROD, which has full history for everything in the named
universe even where demo does not): a LONG score and a SHORT score built
from named ± components (trend_1d, trend_1h, breakout, washout,
volume_shock, funding, momentum_4h — see score_instrument()), summed,
conviction = max(long, short) clipped to [5, 95], direction = argmax. ALL
components are recorded on every scored instrument for the log/notify —
the pick must always be explainable.

SELECTION: rank the (non-stale, successfully-fetched) instruments by
conviction; walk down, taking the first that clears every guard —
(a) not stale/fetch-failed, (b) BTC-USDT only: never picked at all while
any BTC book (ride/tact/lab/apprentice/newsdesk — via book_ledger.py's
recorded_book_positions, this book's own respect for that shared ledger)
holds a position or newsdesk has an armed pending, and never opposing the
exchange's existing BTC net; (c) any symbol: skip if the exchange already
shows ANY position on it; (d) instrument spec must fetch OK from the DEMO
host (this is what actually gates whether an order can be placed there,
so it's checked against demo_feed, not live_feed). If the best
guard-clearing candidate's conviction is still under CONVICTION_FLOOR (40),
take it ANYWAY at HALF allocation, tagged "boredom_pick": true — the
owner's no-excuses clause. If literally nothing clears every guard (every
instrument stale, held, or spec-dead), this cycle books nothing and does
NOT stamp last_pick_date, so the very next cycle tries again — the mandate
is "a trade every day", not "a trade every cycle no matter what is
actually available".

CADENCE: fires once per UTC day, on the first cycle at/after 13:00 UTC (9am
ET, US premarket — the stock/TradFi oracles are awake) where
last_pick_date != today. If yesterday's pick is still open at that moment
it is force-closed (reduce-only market) BEFORE the fresh pick, in the same
cycle — one daily-pick position at a time, by construction never older
than ~24h anyway.

RECONCILE/EXIT run EVERY cycle, not just at pick time: bracket-fired exits
booked from the fill, a 24h hard time-exit, and a hardened self-heal on
the TP/SL bracket (shorts_lab.py's own double-read pattern, copied
verbatim) so an open pick is never left naked. record_trade_outcome fires
twice per exit — once under "daily_pick" (the book-wide auto-bench line)
and once under "pick_<top_component>" (e.g. "pick_breakout") so the memory
system can learn per SETUP TYPE, not just per book.

DRY MODE: run_daily_pick(..., dry=True) computes and prints the full
decision every cycle would make (reconcile, guard walk, sizing, the whole
ranked scoreboard) but places NO orders and makes NO state/log/notify
side effects. Used by step53_pick_smoke.py.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone

import pandas as pd

from book_ledger import recorded_book_positions
from step5_paper_trade import (current_funding_bps, execute_maker_or_chase, execute_market_clips,
                               log_event, notify, now_utc,
                               record_trade_outcome, save_state,
                               write_lesson)
from strategy import atr as _atr
from strategy import rsi as _rsi

# ---------------------------------------------------------------------------
# universe (see module docstring: small on purpose — a DEMO-host limitation)
# ---------------------------------------------------------------------------

UNIVERSE = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XAUT-USDT", "TSLA-USDT"]

NICE_NAMES = {
    "BTC-USDT": "bitcoin", "ETH-USDT": "ether", "SOL-USDT": "solana",
    "XAUT-USDT": "gold", "TSLA-USDT": "Tesla",
}

# ---------------------------------------------------------------------------
# sizing / geometry
# ---------------------------------------------------------------------------

PICK_ALLOC = 0.10          # 10% of virtual_equity (5% on a boredom pick)
BOREDOM_ALLOC_MULT = 0.5
MAX_LEV = 20.0
MAX_HOLD_H = 24.0
PICK_HOUR_UTC = 13         # 9am ET US premarket — stock/TradFi oracles awake
CONVICTION_FLOOR = 40.0
LOT_EPS = 1e-6             # "is there a position at all" threshold

CANDLE_1H_BARS = 150       # >=100 for MA100, >=49 for the vol-shock median
CANDLE_1D_BARS = 120       # >=55+1 for the breakout channel, >=50 for SMA50

# ---------------------------------------------------------------------------
# scoring component vocabulary — names used both in `components` records and
# (via COMPONENT_TAG) in the per-setup-type auto-bench subtag
# ---------------------------------------------------------------------------

COMPONENT_LABEL = {
    "trend_1d": "trend", "trend_1h": "trend(1h)", "breakout": "breakout",
    "washout": "washout", "volume_shock": "volume shock",
    "funding": "funding", "momentum_4h": "momentum",
}
COMPONENT_TAG = {
    "trend_1d": "trend", "trend_1h": "trend", "breakout": "breakout",
    "washout": "washout", "volume_shock": "volume", "funding": "funding",
    "momentum_4h": "momentum",
}


# ===========================================================================
# scoring — pure functions, no I/O, fully unit-testable
# ===========================================================================

def _trend_1d_state(c1d: pd.DataFrame):
    """('up'|'down'|None, sma20, sma50) from 1d close vs SMA20/SMA50
    alignment. None on warmup or a non-aligned (choppy) market."""
    close = c1d["close"]
    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    c, s20, s50 = close.iloc[-1], sma20.iloc[-1], sma50.iloc[-1]
    if pd.isna(s20) or pd.isna(s50):
        return None, s20, s50
    if c > s20 > s50:
        return "up", s20, s50
    if c < s20 < s50:
        return "down", s20, s50
    return None, s20, s50


def score_instrument(c1h: pd.DataFrame, c1d: pd.DataFrame,
                     funding_bps: float | None) -> dict:
    """Score ONE instrument on its own closed 1h + 1d candles. Returns
    {long_score, short_score, conviction, direction, components}.
    `components` records EVERY check that actually fired (either side),
    as {"name", "long", "short"} — the pick must always be explainable."""
    long_pts, short_pts = 0.0, 0.0
    comps: list[dict] = []

    def add(name: str, long_add: float = 0.0, short_add: float = 0.0):
        nonlocal long_pts, short_pts
        long_pts += long_add
        short_pts += short_add
        comps.append({"name": name, "long": long_add, "short": short_add})

    # -- trend: 1d SMA20/SMA50 alignment (+15), 1h MA20>MA100 state (+10) --
    trend_1d, _, _ = _trend_1d_state(c1d)
    if trend_1d == "up":
        add("trend_1d", long_add=15.0)
    elif trend_1d == "down":
        add("trend_1d", short_add=15.0)

    ma20_1h = c1h["close"].rolling(20).mean().iloc[-1]
    ma100_1h = c1h["close"].rolling(100).mean().iloc[-1]
    if pd.notna(ma20_1h) and pd.notna(ma100_1h):
        if ma20_1h > ma100_1h:
            add("trend_1h", long_add=10.0)
        elif ma20_1h < ma100_1h:
            add("trend_1h", short_add=10.0)

    # -- breakout proximity: within 0.5% of the 55-bar 1d high/low, or
    #    already through it (+20 through, +10 near) ------------------------
    hi55 = c1d["high"].rolling(55).max().shift(1).iloc[-1]
    lo55 = c1d["low"].rolling(55).min().shift(1).iloc[-1]
    close_1d = c1d["close"].iloc[-1]
    b_long = b_short = 0.0
    if pd.notna(hi55):
        if close_1d > hi55:
            b_long = 20.0
        elif close_1d >= hi55 * (1 - 0.005):
            b_long = 10.0
    if pd.notna(lo55):
        if close_1d < lo55:
            b_short = 20.0
        elif close_1d <= lo55 * (1 + 0.005):
            b_short = 10.0
    if b_long or b_short:
        add("breakout", long_add=b_long, short_add=b_short)

    # -- washout: RSI3(1h) < 10 with a 1d uptrend (+20 long); RSI3 > 90 with
    #    a 1d downtrend (+20 short) ------------------------------------------
    r3 = _rsi(c1h["close"], 3).iloc[-1] if len(c1h) >= 2 else float("nan")
    w_long = w_short = 0.0
    if pd.notna(r3):
        if r3 < 10 and trend_1d == "up":
            w_long = 20.0
        if r3 > 90 and trend_1d == "down":
            w_short = 20.0
    if w_long or w_short:
        add("washout", long_add=w_long, short_add=w_short)

    # -- volume shock continuation: last closed 1h bar volume >= 6x
    #    trailing-48 median AND |ret| >= 2x median |ret| -> +15 in the
    #    bar's own direction ------------------------------------------------
    v_long = v_short = 0.0
    if len(c1h) >= 49 and "volume" in c1h.columns:
        vols = c1h["volume"]
        last_vol = vols.iloc[-1]
        med_vol = vols.iloc[-49:-1].median()
        rets = c1h["close"].pct_change()
        last_ret = rets.iloc[-1]
        med_abs_ret = rets.iloc[-49:-1].abs().median()
        if (pd.notna(med_vol) and med_vol > 0 and last_vol >= 6 * med_vol
                and pd.notna(med_abs_ret) and med_abs_ret > 0
                and pd.notna(last_ret) and abs(last_ret) >= 2 * med_abs_ret):
            if last_ret > 0:
                v_long = 15.0
            elif last_ret < 0:
                v_short = 15.0
    if v_long or v_short:
        add("volume_shock", long_add=v_long, short_add=v_short)

    # -- funding extreme: >= +2bp adds +8 SHORT; <= -2bp adds +8 LONG -------
    if funding_bps is not None:
        if funding_bps >= 2.0:
            add("funding", short_add=8.0)
        elif funding_bps <= -2.0:
            add("funding", long_add=8.0)

    # -- 4h momentum: |close vs close 4 bars (hours) ago| > 1% adds +8 -------
    m_long = m_short = 0.0
    if len(c1h) >= 5:
        mom_pct = (c1h["close"].iloc[-1] / c1h["close"].iloc[-5] - 1) * 100
        if pd.notna(mom_pct):
            if mom_pct > 1.0:
                m_long = 8.0
            elif mom_pct < -1.0:
                m_short = 8.0
    if m_long or m_short:
        add("momentum_4h", long_add=m_long, short_add=m_short)

    raw = max(long_pts, short_pts)
    conviction = min(max(raw, 5.0), 95.0)
    direction = "long" if long_pts >= short_pts else "short"
    return {"long_score": long_pts, "short_score": short_pts,
            "conviction": conviction, "direction": direction,
            "components": comps}


def _is_stale(c1h: pd.DataFrame) -> bool:
    """Frozen oracle / weekend-dead stock perp: the last 3 closed 1h bars
    all share the exact same close. Also stale if there simply isn't
    enough data to check."""
    if c1h is None or len(c1h) < 3:
        return True
    return bool(c1h["close"].iloc[-3:].nunique() == 1)


def _top_component(cand: dict) -> str | None:
    """The single highest-scoring component IN THE WINNING DIRECTION —
    used for the per-setup-type auto-bench subtag."""
    key = "long" if cand["direction"] == "long" else "short"
    best_name, best_val = None, 0.0
    for c in cand["components"]:
        v = c.get(key, 0.0)
        if v > best_val:
            best_val, best_name = v, c["name"]
    return best_name


def _explain(cand: dict) -> str:
    key = "long" if cand["direction"] == "long" else "short"
    parts = [f"{COMPONENT_LABEL.get(c['name'], c['name'])} +{c[key]:.0f}"
             for c in cand["components"] if c.get(key, 0.0)]
    return ", ".join(parts) if parts else "no components fired (boredom pick)"


# ===========================================================================
# universe probing + per-instrument analysis (I/O, not pure)
# ===========================================================================

_active_universe_cache: list[str] | None = None


def _probe_universe(demo_feed, universe: list[str] = UNIVERSE) -> list[str]:
    """STARTUP GUARD (see module docstring): probe each symbol's DEMO
    candles ONCE per process, drop any that error or return nothing. This
    is what lets UNIVERSE stay a plain list — a future edit that adds a
    symbol BloFin hasn't actually listed on demo yet just gets logged and
    skipped here, never a crash. Cached for the process lifetime (demo
    listings don't change cycle to cycle)."""
    global _active_universe_cache
    if _active_universe_cache is not None:
        return _active_universe_cache
    active = []
    for sym in universe:
        try:
            c = demo_feed.get_candles(sym, "1h", 3)
            if c is not None and len(c) > 0:
                active.append(sym)
            else:
                print(f"  [PICK] universe probe: {sym} — no candles on "
                      f"DEMO, dropping from today's universe")
        except Exception as e:
            print(f"  [PICK] universe probe: {sym} FAILED on DEMO "
                  f"({str(e)[:80]}) — dropping from today's universe")
    _active_universe_cache = active
    print(f"  [PICK] active demo-tradeable universe: {active}")
    return active


def _fetch(live_feed, symbol: str):
    c1h = live_feed.get_candles(symbol, "1h", CANDLE_1H_BARS)
    c1d = live_feed.get_candles(symbol, "1d", CANDLE_1D_BARS)
    return c1h, c1d


def analyze_universe(live_feed, universe: list[str] = UNIVERSE) -> list[dict]:
    """Score EVERY instrument in `universe` (candles from live_feed — PROD,
    full history regardless of demo availability). Returns one record per
    symbol, always — even a fetch failure or staleness produces a record
    (marked ok=False / stale=True) so the full scoreboard is always
    printable, per step53_pick_smoke.py's brief."""
    out = []
    for sym in universe:
        rec = {"symbol": sym, "ok": False, "stale": False, "conviction": None,
               "long_score": 0.0, "short_score": 0.0, "direction": None,
               "components": [], "funding_bps": None, "atr_pct_1h": None,
               "last_close": None, "error": None}
        try:
            c1h, c1d = _fetch(live_feed, sym)
        except Exception as e:
            rec["error"] = str(e)[:120]
            out.append(rec)
            print(f"  [PICK] {sym}: candle fetch FAILED — {rec['error']} "
                  f"(skipped)")
            continue
        if c1h is None or c1h.empty or c1d is None or c1d.empty:
            rec["error"] = "empty candles"
            out.append(rec)
            print(f"  [PICK] {sym}: empty candles (skipped)")
            continue
        if _is_stale(c1h):
            rec["ok"], rec["stale"] = True, True
            out.append(rec)
            print(f"  [PICK] {sym}: STALE (frozen last-3 1h closes) — "
                  f"skipped")
            continue
        fb = current_funding_bps(live_feed, sym)
        sc = score_instrument(c1h, c1d, fb)
        last_close = float(c1h["close"].iloc[-1])
        atr14 = float(_atr(c1h, 14).iloc[-1])
        atr_pct = (atr14 / last_close * 100) if last_close else 0.0
        rec.update(ok=True, conviction=sc["conviction"],
                   long_score=sc["long_score"], short_score=sc["short_score"],
                   direction=sc["direction"], components=sc["components"],
                   funding_bps=fb, atr_pct_1h=atr_pct, last_close=last_close)
        out.append(rec)
    return out


# ===========================================================================
# guards + selection
# ===========================================================================

def _btc_books_active(state: dict) -> bool:
    """True if ANY BTC-USDT book (ride/tact/lab/apprentice/newsdesk, via
    book_ledger.py's own shared accounting) currently holds a position, or
    newsdesk has an armed-but-not-yet-filled pending news trade. Guard (b):
    the daily pick never even considers BTC while the snipers own it."""
    recorded = recorded_book_positions(state)
    if any(abs(v) > LOT_EPS for v in recorded.values()):
        return True
    if state.get("newsdesk", {}).get("pending"):
        return True
    return False


_spec_cache: dict = {}


def _demo_spec(demo_feed, symbol: str) -> dict | None:
    """Contract math for `symbol`, read from BloFin's own DEMO instruments
    endpoint (never assumed) — this is guard (d): it is what actually
    determines whether an order can be placed on this host, so it is
    checked against demo_feed, never live_feed. NOT cached on failure (a
    symbol that 404s today for a transient reason should be re-tried
    tomorrow, not locked out for the rest of the process's life) — only
    successes are cached, mirroring gold_book.py's _instrument_spec."""
    if symbol in _spec_cache:
        return _spec_cache[symbol]
    try:
        spec = demo_feed.get_instrument(symbol)
        parsed = {
            "contract_value": float(spec["contractValue"]),
            "min_size": float(spec["minSize"]),
            "lot_size": float(spec["lotSize"]),
            "tick_size": float(spec.get("tickSize", 0.1)),
            "max_leverage": float(spec.get("maxLeverage", MAX_LEV)),
        }
    except Exception:
        return None
    _spec_cache[symbol] = parsed
    return parsed


def _guard_check(cand: dict, private, demo_feed, state: dict):
    """Guards (b)-(d) for one ranked candidate (guard (a), staleness, is
    already enforced by analyze_universe/select_pick never ranking a stale
    or fetch-failed instrument in the first place). Returns (True, spec)
    or (False, reason)."""
    sym = cand["symbol"]
    if sym == "BTC-USDT" and _btc_books_active(state):
        return False, ("a BTC book has an open trade or an armed pending "
                       "(the snipers own BTC first)")
    try:
        net = private.net_position_contracts(sym)
    except Exception as e:
        return False, f"position read failed: {str(e)[:80]}"
    if sym == "BTC-USDT":
        if net > LOT_EPS and cand["direction"] == "short":
            return False, f"would oppose existing net long BTC ({net:+.2f} ct)"
        if net < -LOT_EPS and cand["direction"] == "long":
            return False, f"would oppose existing net short BTC ({net:+.2f} ct)"
    if abs(net) > LOT_EPS:
        return False, f"exchange already shows a position on {sym} ({net:+.2f} ct)"
    spec = _demo_spec(demo_feed, sym)
    if spec is None:
        return False, "instrument spec unavailable on demo (not listed / fetch failed)"
    return True, spec


def select_pick(analysis: list[dict], private, demo_feed, state: dict):
    """Rank by conviction, walk down applying every guard. Returns
    ((cand, spec) | None, is_boredom, skip_log)."""
    ranked = sorted([a for a in analysis if a["ok"] and not a["stale"]],
                    key=lambda a: a["conviction"], reverse=True)
    guarded = []
    skips = []
    for cand in ranked:
        ok, info = _guard_check(cand, private, demo_feed, state)
        if ok:
            guarded.append((cand, info))
        else:
            skips.append((cand["symbol"], info))
            print(f"  [PICK] {cand['symbol']} (conv {cand['conviction']:.0f}) "
                  f"GUARD FAIL: {info}")
    if not guarded:
        return None, False, skips
    for cand, spec in guarded:
        if cand["conviction"] >= CONVICTION_FLOOR:
            return (cand, spec), False, skips
    # nobody cleared the floor -> boredom pick: the best-guarded candidate
    # anyway, at half allocation (owner's no-excuses clause)
    return guarded[0], True, skips


# ===========================================================================
# sizing
# ===========================================================================

def _round_lot(raw: float, lot: float, minimum: float) -> float:
    n = round(raw / lot) * lot if lot else raw
    return max(minimum, n)


def _build_entry_plan(cand: dict, spec: dict, equity: float, boredom: bool) -> dict:
    stop_pct = min(max(1.5 * (cand["atr_pct_1h"] or 0.0), 0.1), 1.7)
    target_pct = 3 * stop_pct
    lev = min(MAX_LEV, spec["max_leverage"], math.floor(85 / stop_pct))
    lev = max(1.0, lev)
    alloc = PICK_ALLOC * (BOREDOM_ALLOC_MULT if boredom else 1.0)
    notional = equity * alloc * lev
    price = cand["last_close"]
    raw = notional / (spec["contract_value"] * price) if price else 0.0
    contracts = _round_lot(raw, spec["lot_size"], spec["min_size"])
    direction = cand["direction"]
    if direction == "long":
        sl_ref = price * (1 - stop_pct / 100)
        tp_ref = price * (1 + target_pct / 100)
        open_side, close_side = "buy", "sell"
    else:
        sl_ref = price * (1 + stop_pct / 100)
        tp_ref = price * (1 - target_pct / 100)
        open_side, close_side = "sell", "buy"
    return {"stop_pct": stop_pct, "target_pct": target_pct, "leverage": lev,
            "alloc": alloc, "notional": notional, "contracts": contracts,
            "ref_price": price, "sl_ref": sl_ref, "tp_ref": tp_ref,
            "open_side": open_side, "close_side": close_side}


# ===========================================================================
# conviction ledger
# ===========================================================================

def _fresh_ledger() -> dict:
    return {b: {"n": 0, "wins": 0, "pnl": 0.0}
            for b in ("30-44", "45-59", "60-74", "75+")}


def _bucket(conviction: float) -> str:
    if conviction < 45:
        return "30-44"
    if conviction < 60:
        return "45-59"
    if conviction < 75:
        return "60-74"
    return "75+"


def _fresh_dp() -> dict:
    return {"last_pick_date": None, "open_trade": None,
            "conviction_ledger": _fresh_ledger(), "picks": []}


# ===========================================================================
# bracket protection — hardened double-read, copied verbatim from
# shorts_lab.py, generalized to arbitrary symbol/direction
# ===========================================================================

def _cleanup_orders(private, symbol, t):
    try:
        if t.get("tp_order_id"):
            private.cancel_order(symbol, t["tp_order_id"])
    except Exception:
        pass
    try:
        if t.get("tpsl_id"):
            private.cancel_tpsl(symbol, t["tpsl_id"])
    except Exception:
        pass


def _bracket_present(private, symbol, t) -> bool:
    brackets = private.pending_tpsl(symbol)
    if not brackets:
        return False
    our_id = t.get("tpsl_id")
    if our_id:
        return any(str(b.get("tpslId")) == str(our_id) for b in brackets)
    return True


def _ensure_bracket(private, symbol, state, t):
    """SELF-HEALING PROTECTION: read pending_tpsl TWICE, 4s apart, only
    re-arm if BOTH reads come back empty AND a fresh net-position read
    confirms the position still exists. A read exception means 'don't
    know' — do nothing, never act on bad data (shorts_lab.py's own
    hardening, verbatim)."""
    if not t or not t.get("sl_price"):
        return
    try:
        if _bracket_present(private, symbol, t):
            return
        time.sleep(4)
        if _bracket_present(private, symbol, t):
            return
        net = private.net_position_contracts(symbol)
        if abs(net) < t["contracts"] / 2:
            return
    except Exception as e:
        print(f"  [PICK] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return
    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(symbol, close_side, t["contracts"],
                                     t.get("tp_price"), t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [PICK] ⚠️ bracket was MISSING for {symbol} — "
              f"re-armed SL {t['sl_price']:,.4f}")
        notify("\U0001f6e1️ Stop re-armed (demo)",
              f"The daily pick's TP/SL had vanished on {symbol} — "
              f"re-placed. SL now back at {t['sl_price']:,.4f}.")
    except Exception as e:
        print(f"  [PICK] bracket re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ daily pick UNPROTECTED (demo)",
              f"{symbol} bracket missing and re-arm failed — check BloFin "
              f"now")


# ===========================================================================
# exit / reconcile
# ===========================================================================

def _check_gone(private, t):
    """Returns (gone, exit_price, reason, fee_bps). On an unreliable
    position read, returns gone=False — never book an exit from bad data."""
    try:
        net = private.net_position_contracts(t["symbol"])
    except Exception as e:
        print(f"  [PICK] position read failed for {t['symbol']} "
              f"({str(e)[:80]}) — skipping reconcile this cycle")
        return False, None, None, None
    if abs(net) >= t["contracts"] / 2:
        return False, None, None, None
    exit_price = t["entry_price"]
    try:
        fills = private.fills(t["symbol"])
        if fills:
            exit_price = float(fills[0]["fillPrice"])
    except Exception:
        pass
    direction = t["direction"]
    if direction > 0:
        reason = "TP hit" if exit_price >= t["entry_price"] else "SL hit"
    else:
        reason = "TP hit" if exit_price <= t["entry_price"] else "SL hit"
    fee_bps = 2.0 if reason == "TP hit" else 6.0
    return True, exit_price, reason, fee_bps


def _book_exit(state, dp, t, exit_price, exit_fee_bps, reason):
    """Close the daily pick's trade on its own ledger line, updates the
    conviction ledger bucket, fires BOTH auto-bench subtags (the book-wide
    "daily_pick" line and the per-setup-type "pick_<top_component>" line
    so the memory system learns per setup, not just per book)."""
    sym = t["symbol"]
    contract_value = t.get("contract_value", 0.001)
    size = t["contracts"] * contract_value
    gross = t["direction"] * (exit_price - t["entry_price"]) * size
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    dp["open_trade"] = None

    bucket = _bucket(t.get("conviction", 5.0))
    ledger = dp.setdefault("conviction_ledger", _fresh_ledger())
    b = ledger.setdefault(bucket, {"n": 0, "wins": 0, "pnl": 0.0})
    b["n"] += 1
    b["wins"] += 1 if realized > 0 else 0
    b["pnl"] = round(b["pnl"] + realized, 2)

    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [PICK] {sym} {reason}: PnL ${realized:+,.2f} -> "
          f"ledger ${eq:,.2f}")
    log_event({"action": "pick_exit", "symbol": sym, "reason": reason,
              "direction": t["direction"], "exit_price": exit_price,
              "realized_pnl": realized, "virtual_equity": eq,
              "conviction": t.get("conviction"), "bucket": bucket,
              "top_component": t.get("top_component"),
              "boredom_pick": t.get("boredom_pick", False)})
    record_trade_outcome(state, "daily_pick", realized)
    top_tag = t.get("top_component")
    if top_tag:
        record_trade_outcome(state, f"pick_{top_tag}", realized)
    write_lesson(state, "daily_pick", realized, t["entry_price"], exit_price,
                reason, t.get("ctx"))
    notify(f"\U0001f4cc daily pick {reason}: ${realized:+,.2f}",
          f"{side} {sym} — ledger ${eq:,.2f} (demo)")
    return realized


# ===========================================================================
# entry
# ===========================================================================

def _preview_entry(cand: dict, spec: dict, equity: float, boredom: bool) -> dict:
    plan = _build_entry_plan(cand, spec, equity, boredom)
    sym = cand["symbol"]
    explain = _explain(cand)
    print(f"  [PICK DRY] {cand['direction'].upper()} {sym} WOULD FIRE — "
          f"conviction {cand['conviction']:.0f}%"
          f"{' BOREDOM' if boredom else ''} — {explain} — "
          f"{plan['contracts']:.4g} ct (~${plan['notional']:,.0f} notional "
          f"at {plan['leverage']:.0f}x, {plan['alloc']*100:.1f}% alloc) @ "
          f"~{plan['ref_price']:,.4f} | est TP {plan['tp_ref']:,.4f} est SL "
          f"{plan['sl_ref']:,.4f} | max hold {MAX_HOLD_H:.0f}h — NO ORDER "
          f"PLACED")
    return {"action": "would_enter", "symbol": sym,
            "direction": cand["direction"], "conviction": cand["conviction"],
            "boredom_pick": boredom, "contracts": plan["contracts"],
            "leverage": plan["leverage"], "entry_ref": plan["ref_price"],
            "est_tp": plan["tp_ref"], "est_sl": plan["sl_ref"],
            "components": cand["components"]}


def _do_entry(private, demo_feed, state, dp, cand, spec, boredom, today_str) -> dict:
    plan = _build_entry_plan(cand, spec, state.get("virtual_equity", 0.0), boredom)
    sym = cand["symbol"]
    direction = cand["direction"]
    explain = _explain(cand)
    print(f"  [PICK] {direction.upper()} SIGNAL {sym} conv="
          f"{cand['conviction']:.0f}%{' BOREDOM' if boredom else ''} — "
          f"{plan['contracts']:.4g} ct (~${plan['notional']:,.0f} notional "
          f"at {plan['leverage']:.0f}x)")

    if not private.ensure_leverage(sym, plan["leverage"], "cross"):
        notify("⚠️ daily pick entry ABORTED (demo)",
              f"couldn't set leverage on {sym} — no order placed")
        return {"action": "entry_aborted_leverage", "symbol": sym}

    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, sym, plan["open_side"], plan["contracts"],
            plan["ref_price"])
    except Exception as e:
        print(f"  [PICK] ENTRY FAILED: {str(e)[:100]}")
        notify("⚠️ daily pick ENTRY FAILED (demo)",
              f"{sym} {direction} entry rejected: {str(e)[:80]}. No "
              f"position opened — check BloFin.")
        return {"action": "entry_failed", "symbol": sym,
                "error": str(e)[:120]}

    if direction == "long":
        sl = entry * (1 - plan["stop_pct"] / 100)
        tp = entry * (1 + plan["target_pct"] / 100)
    else:
        sl = entry * (1 + plan["stop_pct"] / 100)
        tp = entry * (1 - plan["target_pct"] / 100)

    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(sym, plan["close_side"],
                                     plan["contracts"], tp, sl)
    except Exception as e:
        print(f"  [PICK] TP/SL bracket FAILED: {str(e)[:80]}")
        notify("⚠️ daily pick bracket failed (demo)",
              f"{sym} position opened but TP/SL not set — check BloFin now")

    top_comp = _top_component(cand)
    top_tag = COMPONENT_TAG.get(top_comp, top_comp)

    dp["open_trade"] = {
        "symbol": sym, "direction": 1 if direction == "long" else -1,
        "contracts": plan["contracts"], "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0, "entry_time": now_utc(),
        "tp_price": tp, "sl_price": sl, "tpsl_id": tpsl_id,
        "max_hold_h": MAX_HOLD_H, "conviction": cand["conviction"],
        "boredom_pick": boredom, "top_component": top_tag,
        "leverage": plan["leverage"], "contract_value": spec["contract_value"],
        "ctx": {"atr_pct": round(cand["atr_pct_1h"] or 0.0, 2),
                "funding_bps": cand["funding_bps"],
                "components": cand["components"], "explain": explain},
    }
    dp["last_pick_date"] = today_str
    picks = dp.setdefault("picks", [])
    picks.append({"date": today_str, "symbol": sym, "direction": direction,
                  "conviction": round(cand["conviction"], 1),
                  "boredom_pick": boredom, "entry": entry, "tp": tp,
                  "sl": sl, "leverage": plan["leverage"],
                  "components": cand["components"]})
    del picks[:-100]
    save_state(state)

    log_event({"action": "pick_enter", "symbol": sym, "direction": direction,
              "conviction": cand["conviction"], "boredom_pick": boredom,
              "components": cand["components"], "entry": entry, "tp": tp,
              "sl": sl, "leverage": plan["leverage"],
              "contracts": plan["contracts"], "top_component": top_tag})
    nice = NICE_NAMES.get(sym, sym.replace("-USDT", ""))
    notify(f"\U0001f4cc DAILY PICK: {direction.upper()} {sym} ({nice})",
          f"conviction {cand['conviction']:.0f}% — {explain} — entry "
          f"${entry:,.4f} TP ${tp:,.4f} SL ${sl:,.4f}"
          f"{' [BOREDOM PICK]' if boredom else ''} (demo)")
    return {"action": "entered", "symbol": sym, "direction": direction,
            "entry": entry, "tp": tp, "sl": sl, "contracts": plan["contracts"],
            "conviction": cand["conviction"], "boredom_pick": boredom}


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_daily_pick(private, live_feed, demo_feed, state: dict, dry: bool = False):
    """One cycle. Reconcile/exit logic runs every call; the actual pick
    only happens on the first cycle at/after PICK_HOUR_UTC each day.
    Returns a small summary dict, mainly for tests/smoke."""
    dp = state.setdefault("daily_pick", _fresh_dp())
    t = dp.get("open_trade")
    tag = " DRY" if dry else ""
    now = datetime.now(timezone.utc)
    today_str = f"{now:%Y-%m-%d}"
    due = now.hour >= PICK_HOUR_UTC and dp.get("last_pick_date") != today_str

    print(f"  [PICK{tag}] cycle @ {now:%H:%M} UTC | open="
          f"{'YES ' + t['symbol'] if t else 'no'} | last_pick_date="
          f"{dp.get('last_pick_date')} | due_today={due}")

    # -- reconcile: our position is gone -> a bracket fired -----------------
    if t:
        gone, exit_price, reason, fee_bps = _check_gone(private, t)
        if gone:
            print(f"  [PICK{tag}] {t['symbol']} position gone -> {reason} "
                  f"@ {exit_price:,.4f}")
            if dry:
                print("  [PICK DRY] would cancel remaining bracket orders "
                      "and book this exit — no changes made")
                return {"action": "would_exit", "symbol": t["symbol"],
                        "reason": reason, "exit_price": exit_price}
            _cleanup_orders(private, t["symbol"], t)
            _book_exit(state, dp, t, exit_price, fee_bps, reason)
            t = None

    # -- time exit (24h) OR forced close because a new pick day arrived -----
    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (now - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", MAX_HOLD_H)
        time_up = held_h >= max_hold_h
        if time_up or due:
            close_reason = f"{max_hold_h:.0f}h time" if time_up else "new-day pick close"
            print(f"  [PICK{tag}] closing {t['symbol']} ({close_reason}, "
                  f"held {held_h:.1f}h)")
            if dry:
                print(f"  [PICK DRY] would market-close {t['contracts']:.4g} "
                      f"ct {t['symbol']} now — no orders placed")
                return {"action": "would_time_exit", "symbol": t["symbol"],
                        "contracts": t["contracts"]}
            _cleanup_orders(private, t["symbol"], t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(t["symbol"])
            ref_price = quote.bid if side == "sell" else quote.ask
            fill, was_maker = execute_market_clips(
                private, demo_feed, t["symbol"], side, t["contracts"],
                ref_price, reduce_only=True)
            _book_exit(state, dp, t, fill, 2.0 if was_maker else 6.0,
                      close_reason)
            t = None

    # -- still holding: self-heal the bracket, report ------------------------
    if t:
        if not dry:
            _ensure_bracket(private, t["symbol"], state, t)
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (now - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        print(f"  [PICK{tag}] holding {t['contracts']:.4g} ct "
              f"{'long' if t['direction'] > 0 else 'short'} {t['symbol']} "
              f"from {t['entry_price']:,.4f} ({held_h:.1f}h/"
              f"{t.get('max_hold_h', MAX_HOLD_H):.0f}h), bracket verified")
        return {"action": "holding", "symbol": t["symbol"],
                "direction": t["direction"], "held_h": round(held_h, 1)}

    # -- not holding: only act if it's pick time and today isn't done -------
    if not due:
        print(f"  [PICK{tag}] not due yet (needs UTC hour >= "
              f"{PICK_HOUR_UTC} and a fresh day) — waiting")
        return {"action": "waiting", "last_pick_date": dp.get("last_pick_date")}

    print(f"  [PICK{tag}] === PICK TIME — scoring the universe ===")
    active_universe = _probe_universe(demo_feed)
    analysis = analyze_universe(live_feed, active_universe)
    for a in sorted(analysis, key=lambda r: (r["conviction"] is None, -(r["conviction"] or 0))):
        if a["ok"] and not a["stale"]:
            print(f"    {a['symbol']:10s} conv={a['conviction']:5.1f} "
                  f"dir={a['direction']:5s} long={a['long_score']:5.1f} "
                  f"short={a['short_score']:5.1f} fund="
                  f"{a['funding_bps'] if a['funding_bps'] is not None else 'n/a'}")
        else:
            print(f"    {a['symbol']:10s} SKIPPED "
                  f"({'stale' if a['stale'] else a['error']})")

    chosen, boredom, skips = select_pick(analysis, private, demo_feed, state)
    if chosen is None:
        print("  [PICK] NOTHING passed guards today — no instrument is "
              "currently tradeable/available. Retrying next cycle "
              "(last_pick_date NOT stamped).")
        if not dry:
            log_event({"action": "pick_none_available", "skips": skips})
            notify("⚠️ Daily pick: nothing tradeable today (demo)",
                  "every instrument in the universe failed a guard "
                  "(staleness / BTC-owned / already-held / no demo spec) — "
                  "will keep retrying today.")
        return {"action": "no_candidate", "skips": skips}

    cand, spec = chosen
    if dry:
        return _preview_entry(cand, spec, state.get("virtual_equity", 0.0),
                              boredom)
    return _do_entry(private, demo_feed, state, dp, cand, spec, boredom,
                     today_str)
