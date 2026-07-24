"""
tradfi_engine.py — THE TRADFI ENGINE: the crypto learning engine's twin for
GOLD, OIL, and the S&P (Wallace, 2026-07-24: "trade S&P and oil like it's
the market, like you're looking at the candle charts; there should be
multiple trades happening right now, not all crypto").

WHAT THIS IS, PLAINLY: there is no venue on BloFin (or anywhere this bot
has real API access) for practice orders on CL=F/SPY, so this book
runs a fully self-contained PAPER ledger. It scores real market data
(yfinance) every 2h slot exactly like daily_pick.py's learning engine
scores BTC/ETH/SOL, but every fill is simulated against the real price and
booked only against its OWN virtual ledger
(state["tradfi_engine"]["ledger_equity"], starts at $2,000). It NEVER
touches BloFin, NEVER calls an order-placement endpoint, and NEVER reads
or writes state["virtual_equity"] or any book_ledger.py-tracked key — this
book's PnL is its own, isolated fiction, real prices in a fake account.

REUSE, NOT REINVENTION: the scorer (score_instrument), its tight-zone stop/
target geometry (_stop_target_pct), the conviction floor (CONVICTION_FLOOR
= 40) and the stop-out cooldown window (STOPOUT_COOLDOWN_H = 6h) are
imported straight from daily_pick.py — read-only, no mutation of that
module's own state or globals. Those functions are venue-agnostic pure
math on (c1h, c1d, funding_bps) / a `cand` dict; nothing about them assumes
BloFin. The 2h-UTC-slot cadence (_slot_ts) is imported the same way.
funding_bps is always None here — futures/ETFs don't carry a funding rate.

UNIVERSE + DATA (yfinance only, imported INSIDE each fetch function — never
at module import time, so this module has zero network/import cost until a
cycle actually runs, and tests can monkeypatch the fetch functions with no
yfinance install required):
  OIL   = "CL=F"   (WTI crude futures — same ticker morning_read.py already
                    uses for oil)
  SPX   = "SPY"    (S&P 500 ETF — the only S&P proxy yfinance serves
                    reliably as a tradeable instrument; SPX itself is an
                    index, not an order-able ticker)
1h candles (60d lookback — plenty for the scorer's MA100/RSI3/volume-shock
warmup, comfortably under yfinance's 730d cap for 1h data) + 1d candles
(400d) for context, normalized to the same open/high/low/close/volume(+
timestamp) shape daily_pick.py's live_feed already returns.

MARKET HOURS — documented approximations, not exact-second precision (a
coarse "is this market roughly open right now" gate, matching what the
brief asked for):
  - assumes US Eastern is at its DST offset, UTC-4 (EDT), YEAR ROUND. Real
    ET shifts to UTC-5 (EST) roughly Nov-Mar, so during that window the
    true boundaries below can be off by up to 1h. Acceptable for a slot
    gate that only needs to be right within an hour, not for building a
    real order router.
  - GOLD/OIL (CME futures): ~23h/day Sunday 22:00 UTC through Friday 21:00
    UTC, closed the weekend, closed daily 21:00-22:00 UTC (CME's own daily
    maintenance break) Mon-Thu.
  - SPX (SPY, cash equity hours): 13:30-20:00 UTC, Monday-Friday only. No
    pre/post-market, no holiday calendar (a holiday reads as "open" here
    and simply scores/fetches into a flat, low-signal tape — harmless,
    just an unnecessary API call).
A symbol whose market reads closed is skipped SILENTLY from that slot's
scoring — no log spam, no notify, exactly per brief. Existing open
positions are still reconciled every call regardless of market-open state
(see run_tradfi_engine): a stop/target/time exit can still fire off the
last available closed 1h bar even while the market that produced it is
currently shut.

MECHANIC (mirrors daily_pick's run_daily_pick shape): every 2h UTC slot,
score every OPEN market, rank by conviction, guard out anything already
held (max MAX_CONCURRENT=2 concurrent positions, always different
symbols), apply the SAME calm-regime A-only rule daily_pick uses (1h ATR%
< 0.8x its own trailing-14d median -> require conviction >= CONVICTION_FLOOR,
mirrored locally in _regime() since daily_pick's own regime calc lives
inline in analyze_universe rather than as an importable function), and the
SAME stop-out cooldown (STOPOUT_COOLDOWN_H, imported). No other
conviction-floor skip — take the best available every slot, exactly like
daily_pick's own owner mandate. Tight-zone geometry is _stop_target_pct's
(imported unchanged): stop = 1.0x ATR(14,1h) capped at 1.0%, target = 1.5x
stop. MAX_HOLD_H = 6h here (vs crypto's 4h) — a deliberately slightly
longer leash for slower TradFi tapes, per the brief.

SIZING: fixed-fractional RISK_PCT (2%) of the engine's OWN ledger_equity
per trade, at leverage min(MAX_LEV, max(MIN_LEV, 85/stop_pct)) — SPY is
additionally capped at SPY_MAX_LEV=4x (realistic; nobody trades an ETF at
20x). Exactly like daily_pick's _build_entry_plan, leverage here is
informational/margin-realism only — it does not change the trade's
notional, which fixed-fractional risk sizing already pins to
RISK_PCT*equity/(stop_pct/100) regardless of leverage.

FEES: 1bp/leg standard (SPY), 2bp/leg for the futures (CL=F) —
booked on both the entry and exit leg, same formula shape as daily_pick's
_book_exit (gross directional PnL minus entry_price*fee_bps +
exit_price*fee_bps, scaled by the paper position's share count).

LEARNING LOOP: same daybook shape as the crypto engine's
(symbol/dir/conviction/components/outcome_pnl/hold_min) in
state["tradfi_engine"]["daybook"]; a stop-out stamps
state["tradfi_engine"]["last_stopouts"][symbol:direction] exactly like
daily_pick's _book_exit does (condition mirrored verbatim: ANY losing
exit stamps, not just a literal stop-hit — that is daily_pick's actual
behavior, not a simplification). Once per UTC day (checked on every call,
independent of slot/capacity — deliberately decoupled from the entry
branch daily_pick nests its own recap inside, so a string of at-capacity
or closed-market slots can never delay the recap) this book sends its own
Telegram recap off yesterday's daybook: "TradFi engine yesterday: N
trades, WW/LL, net $+/-X.XX (paper)".

WHAT THIS MODULE NEVER DOES: place an order, touch a private/exchange
client, read or write state["virtual_equity"] or any book_ledger.py key,
or import anything from daemon.py/hourly.py/spx_book.py/gold_book.py/
newsdesk.py. It has NO private-client dependency at all — run_tradfi_engine
takes only (state, dry). A module-source check in test_tradfi_engine.py
asserts none of that ever creeps in.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from daily_pick import (CONVICTION_FLOOR, STOPOUT_COOLDOWN_H, _explain,
                        _slot_ts, _top_component, score_instrument,
                        _stop_target_pct)
from step5_paper_trade import log_event, notify, now_utc, save_state
from strategy import atr as _atr

# ===========================================================================
# universe
# ===========================================================================

OIL = "CL=F"
SPX = "SPY"
# gold trades REAL demo orders on XAUT-USDT via the crypto engine (owner,
# 2026-07-24) — it left this paper universe the same day it briefly joined.
UNIVERSE = [OIL, SPX]
NICE_NAMES = {OIL: "oil", SPX: "the S&P 500"}
FUTURES = {GOLD, OIL}          # 2bp/leg fee tier; SPX (SPY) is 1bp/leg

# ---------------------------------------------------------------------------
# cadence / concurrency (SLOT_INTERVAL_H comes along for free via the
# imported _slot_ts — daily_pick's own SLOT_INTERVAL_H is 2, matching this
# book's brief exactly, so there is nothing to redeclare)
# ---------------------------------------------------------------------------

MAX_CONCURRENT = 2             # up to 2 concurrent paper positions, always
                               # different symbols (3-symbol universe)
STARTING_EQUITY = 2000.0       # the engine's OWN virtual ledger, isolated
                               # from every other book's money

# ---------------------------------------------------------------------------
# sizing / geometry (tight-zone stop/target math is imported unchanged from
# daily_pick._stop_target_pct — only the things that genuinely differ for
# a slower TradFi tape live here)
# ---------------------------------------------------------------------------

RISK_PCT = 0.02                 # 2% of ledger_equity risked per trade, at stop
MAX_LEV = 20.0
MIN_LEV = 4.0
SPY_MAX_LEV = 4.0               # realistic cap — nobody runs an ETF at 20x
MAX_HOLD_H = 6.0                # slightly longer than crypto's 4h (brief)
FEE_BPS_STANDARD = 1.0          # 1bp/leg — SPX (SPY)
FEE_BPS_FUTURES = 2.0           # 2bp/leg — GOLD / OIL futures
LOT_EPS = 1e-9

# regime detection window — mirrors analyze_universe's own `[-336:]`
# trailing slice (its comment: "14d" against 1h bars; here that slice is
# necessarily biased by each symbol's own session-hours density — futures
# trade ~23h/day so 336 bars is genuinely ~14 calendar days, SPY trades
# ~6.5h/day so 336 bars is closer to ~7-8 WEEKS of trading time. Same
# "own documented approximation" spirit as the market-hours gate above:
# still a meaningful trailing-volatility baseline, just not a literal
# calendar fortnight for every symbol.
REGIME_WINDOW_BARS = 336
REGIME_MIN_BARS = 100
REGIME_CALM_RATIO = 0.8
REGIME_VIOLENT_RATIO = 1.5


# ===========================================================================
# market hours — pure function, no I/O
# ===========================================================================

def is_market_open(symbol: str, now: datetime) -> bool:
    """True if `symbol`'s market is (approximately) open at `now`. See the
    module docstring's MARKET HOURS section for the documented
    approximations this makes (fixed EDT/UTC-4 offset, no holiday
    calendar). `now` may be naive (assumed UTC) or aware (converted)."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    wd = now.weekday()              # Mon=0 ... Sun=6
    minute_of_day = now.hour * 60 + now.minute

    if symbol == SPX:
        if wd >= 5:                 # Sat/Sun
            return False
        return 13 * 60 + 30 <= minute_of_day < 20 * 60

    # GOLD / OIL (CME futures): ~23h Sun-Fri with the daily maintenance
    # break; closed the weekend.
    if wd == 5:                     # Saturday: fully closed
        return False
    if wd == 6:                     # Sunday: opens 22:00 UTC (6pm ET)
        return minute_of_day >= 22 * 60
    if wd == 4:                     # Friday: closes 21:00 UTC (5pm ET)
        return minute_of_day < 21 * 60
    # Monday-Thursday: open all day except the 21:00-22:00 UTC daily break
    return not (21 * 60 <= minute_of_day < 22 * 60)


# ===========================================================================
# data (yfinance — imported inside functions only, try/except degrade)
# ===========================================================================

def _normalize_candles(df) -> pd.DataFrame | None:
    """yfinance's Ticker().history() frame -> this codebase's own OHLCV(+
    timestamp) shape, UTC-aware. Returns None on anything unusable — never
    raises into the caller."""
    if df is None or df.empty:
        return None
    df = df.rename(columns=str.lower)
    if not {"open", "high", "low", "close"}.issubset(df.columns):
        return None
    if "volume" not in df.columns:
        df["volume"] = 0.0
    idx = df.index
    ts = idx.tz_localize("UTC") if getattr(idx, "tz", None) is None else idx.tz_convert("UTC")
    out = df[["open", "high", "low", "close", "volume"]].copy()
    out.insert(0, "timestamp", ts)
    return out.reset_index(drop=True)


def _fetch_1h(symbol: str) -> pd.DataFrame | None:
    """Recent 1h candles for `symbol`. 60d lookback — well under
    yfinance's 730d cap for 1h resolution, plenty for the scorer's own
    warmup needs (MA100 / RSI3 / 48-bar volume-shock window)."""
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="60d", interval="1h")
    except Exception as e:
        print(f"  [TRADFI] {symbol}: 1h fetch failed — {str(e)[:100]}")
        return None
    return _normalize_candles(df)


def _fetch_1d(symbol: str) -> pd.DataFrame | None:
    """Daily candles for `symbol` — context for the scorer's trend_1d /
    breakout-channel components (55-bar high/low, SMA50)."""
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(period="400d", interval="1d")
    except Exception as e:
        print(f"  [TRADFI] {symbol}: 1d fetch failed — {str(e)[:100]}")
        return None
    return _normalize_candles(df)


# ===========================================================================
# scoring — mirrors daily_pick.analyze_universe's per-symbol shape, but
# reuses score_instrument (imported) for the actual math
# ===========================================================================

def _regime(c1h: pd.DataFrame) -> tuple[str, float]:
    """(regime, atr_pct_1h) — same calm/normal/violent classification as
    daily_pick.analyze_universe: current ATR% vs this symbol's OWN
    trailing REGIME_WINDOW_BARS-bar median ATR%. Not importable as a
    function from daily_pick (it lives inline in analyze_universe), so
    mirrored here with the exact same thresholds (0.8x / 1.5x)."""
    atr_series = _atr(c1h, 14)
    last_close = float(c1h["close"].iloc[-1])
    atr_pct = (float(atr_series.iloc[-1]) / last_close * 100) if last_close else 0.0
    if len(c1h) >= REGIME_MIN_BARS:
        atr_pct_series = atr_series / c1h["close"] * 100
        med = float(atr_pct_series.iloc[-REGIME_WINDOW_BARS:].median())
    else:
        med = None
    if med and med > 0:
        ratio = atr_pct / med
        if ratio < REGIME_CALM_RATIO:
            regime = "calm"
        elif ratio > REGIME_VIOLENT_RATIO:
            regime = "violent"
        else:
            regime = "normal"
    else:
        regime = "normal"
    return regime, atr_pct


def _score_symbol(symbol: str) -> dict | None:
    """Fetch + score ONE symbol. Returns None on any fetch/data failure —
    the caller simply excludes it from that slot's ranking (per-symbol
    degrade, never a crashed cycle)."""
    try:
        c1h = _fetch_1h(symbol)
        c1d = _fetch_1d(symbol)
        if c1h is None or c1h.empty or c1d is None or c1d.empty:
            return None
        sc = score_instrument(c1h, c1d, None)   # funding_bps=None — no
                                                # funding rate on futures/ETFs
        regime, atr_pct = _regime(c1h)
        return {"symbol": symbol, "conviction": sc["conviction"],
                "direction": sc["direction"], "long_score": sc["long_score"],
                "short_score": sc["short_score"], "components": sc["components"],
                "last_close": float(c1h["close"].iloc[-1]),
                "atr_pct_1h": atr_pct, "regime": regime}
    except Exception as e:
        print(f"  [TRADFI] {symbol}: scoring failed — {str(e)[:100]} (skipped)")
        return None


# ===========================================================================
# state shape
# ===========================================================================

def _fresh_engine() -> dict:
    return {"ledger_equity": STARTING_EQUITY, "last_slot_ts": None,
            "open_trades": [], "daybook": [], "last_recap_date": None,
            "last_stopouts": {}, "picks": []}


def _migrate_engine(eng: dict) -> None:
    eng.setdefault("ledger_equity", STARTING_EQUITY)
    eng.setdefault("last_slot_ts", None)
    eng.setdefault("open_trades", [])
    eng.setdefault("daybook", [])
    eng.setdefault("last_recap_date", None)
    eng.setdefault("last_stopouts", {})
    eng.setdefault("picks", [])


# ===========================================================================
# exit check — stop/target vs the latest closed 1h bar's high/low,
# STOP-FIRST on a same-bar tie; else the wall-clock time exit
# ===========================================================================

def _check_exit(trade: dict, bar_high: float, bar_low: float,
                bar_close: float, now: datetime):
    """Returns (exit_price, reason) | None. `reason` is 'stop' | 'target' |
    'time'. Checks the stop BEFORE the target so a single bar whose range
    spans both books the stop — the conservative, real-bracket-order
    behavior daily_pick's own _simulate_bracket documents."""
    direction = trade["direction"]
    stop, target = trade["stop_price"], trade["target_price"]
    hit_stop = (bar_low <= stop) if direction == 1 else (bar_high >= stop)
    if hit_stop:
        return stop, "stop"
    hit_target = (bar_high >= target) if direction == 1 else (bar_low <= target)
    if hit_target:
        return target, "target"
    entry_dt = datetime.strptime(
        trade["entry_time"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    held_h = (now - entry_dt).total_seconds() / 3600
    if held_h >= trade.get("max_hold_h", MAX_HOLD_H):
        return bar_close, "time"
    return None


_REASON_LABEL = {"stop": "SL hit", "target": "TP hit", "time": "time exit"}


def _book_exit(state: dict, eng: dict, t: dict, exit_price: float,
              reason: str, now: datetime) -> float:
    """Close ONE paper trade against the engine's OWN ledger_equity —
    NEVER state['virtual_equity'], never a book_ledger.py key. Fee/PnL
    shape mirrors daily_pick._book_exit: gross directional move on the
    paper share count, minus both legs' fees."""
    direction = t["direction"]
    shares = t["shares"]
    fee_bps = t.get("fee_bps", FEE_BPS_STANDARD)
    gross = direction * (exit_price - t["entry_price"]) * shares
    fees = (t["entry_price"] * fee_bps + exit_price * fee_bps) * shares / 10_000
    realized = round(gross - fees, 2)
    eng["ledger_equity"] = round(eng.get("ledger_equity", STARTING_EQUITY) + realized, 2)
    eng["open_trades"] = [x for x in eng.get("open_trades", []) if x is not t]

    entry_dt = datetime.strptime(
        t["entry_time"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    hold_min = round((now - entry_dt).total_seconds() / 60, 1)
    daybook = eng.setdefault("daybook", [])
    daybook.append({
        "date": f"{now:%Y-%m-%d}", "symbol": t["symbol"],
        "dir": "long" if direction == 1 else "short",
        "conviction": t.get("conviction"), "components": t.get("components", []),
        "outcome_pnl": realized, "hold_min": hold_min,
        "setup": t.get("top_component"),
    })
    del daybook[:-500]

    # STOP-OUT COOLDOWN STAMP — mirrors daily_pick._book_exit's actual
    # condition verbatim: ANY losing exit stamps (symbol, direction), not
    # only a literal stop-hit reason.
    if realized < 0:
        eng.setdefault("last_stopouts", {})[
            f"{t['symbol']}:{'long' if direction == 1 else 'short'}"] = {
            "ts": now.isoformat(), "conviction": t.get("conviction") or 0.0}

    save_state(state)
    eq = eng["ledger_equity"]
    side = "LONG" if direction == 1 else "SHORT"
    label = _REASON_LABEL[reason]
    print(f"  [TRADFI] {t['symbol']} {label}: PnL ${realized:+,.2f} (paper) -> "
          f"ledger ${eq:,.2f} (held {hold_min:.0f}m)")
    log_event({"action": "tradfi_exit", "symbol": t["symbol"], "reason": label,
              "direction": direction, "exit_price": exit_price,
              "realized_pnl": realized, "ledger_equity": eq,
              "conviction": t.get("conviction"), "hold_min": hold_min})
    nice = NICE_NAMES.get(t["symbol"], t["symbol"])
    notify(f"{'✅' if realized >= 0 else '\U0001f6d1'} TRADFI {label} (paper): "
          f"{side} {t['symbol']} ({nice})",
          f"PnL ${realized:+,.2f} (paper) -> ledger ${eq:,.2f}")
    return realized


# ===========================================================================
# entry
# ===========================================================================

def _leverage_for(symbol: str, stop_pct: float) -> float:
    lev = min(MAX_LEV, max(MIN_LEV, 85.0 / stop_pct)) if stop_pct else MAX_LEV
    if symbol == SPX:
        lev = min(lev, SPY_MAX_LEV)
    return lev


def _do_entry(state: dict, eng: dict, cand: dict, now: datetime) -> dict:
    symbol = cand["symbol"]
    direction = 1 if cand["direction"] == "long" else -1
    stop_pct, target_pct = _stop_target_pct(cand["atr_pct_1h"])
    lev = _leverage_for(symbol, stop_pct)
    equity = eng.get("ledger_equity", STARTING_EQUITY)
    notional = RISK_PCT * equity / (stop_pct / 100)
    price = cand["last_close"]
    shares = notional / price if price else 0.0
    if direction == 1:
        stop_price = price * (1 - stop_pct / 100)
        target_price = price * (1 + target_pct / 100)
    else:
        stop_price = price * (1 + stop_pct / 100)
        target_price = price * (1 - target_pct / 100)
    fee_bps = FEE_BPS_FUTURES if symbol in FUTURES else FEE_BPS_STANDARD
    top = _top_component(cand)
    explain = _explain(cand)

    trade = {"symbol": symbol, "direction": direction, "entry_price": price,
             "shares": shares, "notional": round(notional, 2),
             "leverage": round(lev, 2), "stop_pct": stop_pct,
             "target_pct": target_pct, "stop_price": stop_price,
             "target_price": target_price, "fee_bps": fee_bps,
             "entry_time": now_utc(), "conviction": cand["conviction"],
             "components": cand["components"], "top_component": top,
             "max_hold_h": MAX_HOLD_H}
    eng.setdefault("open_trades", []).append(trade)
    picks = eng.setdefault("picks", [])
    picks.append({"date": _slot_ts(now), "symbol": symbol,
                  "direction": cand["direction"],
                  "conviction": round(cand["conviction"], 1),
                  "entry": price, "tp": target_price, "sl": stop_price,
                  "leverage": trade["leverage"], "components": cand["components"]})
    del picks[:-200]

    nice = NICE_NAMES.get(symbol, symbol)
    log_event({"action": "tradfi_enter", "symbol": symbol,
              "direction": cand["direction"], "conviction": cand["conviction"],
              "components": cand["components"], "entry": price,
              "tp": target_price, "sl": stop_price, "leverage": trade["leverage"],
              "top_component": top})
    notify(f"\U0001f4c8 TRADFI PICK (paper): {cand['direction'].upper()} {symbol} ({nice})",
          f"conviction {cand['conviction']:.0f}% — {explain} — entry "
          f"${price:,.2f} TP ${target_price:,.2f} SL ${stop_price:,.2f} — "
          f"{len(eng['open_trades'])}/{MAX_CONCURRENT} slots open (paper)")
    return {"action": "entered", "symbol": symbol, "direction": cand["direction"],
            "entry": price, "tp": target_price, "sl": stop_price,
            "conviction": cand["conviction"]}


# ===========================================================================
# daily recap
# ===========================================================================

def _yesterday_str(today_str: str) -> str:
    d = datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)
    return f"{d:%Y-%m-%d}"


def _build_recap_line(eng: dict, today_str: str) -> str:
    y = _yesterday_str(today_str)
    rows = [r for r in eng.get("daybook", []) if r.get("date") == y]
    if not rows:
        return "TradFi engine yesterday: no trades (paper)."
    n = len(rows)
    wins = sum(1 for r in rows if r["outcome_pnl"] > 0)
    losses = n - wins
    net = sum(r["outcome_pnl"] for r in rows)
    sign = "-" if net < 0 else "+"
    return (f"TradFi engine yesterday: {n} trade{'s' if n != 1 else ''}, "
            f"{wins}W/{losses}L, net {sign}${abs(net):,.2f} (paper)")


def _send_daily_recap(eng: dict, today_str: str) -> None:
    notify("\U0001f4ca TradFi engine daily recap (paper)",
          _build_recap_line(eng, today_str))


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_tradfi_engine(state: dict, dry: bool = False) -> dict:
    """One cycle. Reconciles every open paper trade (stop/target/time exit
    off the latest closed 1h bar) EVERY call, regardless of market-open
    state or slot cadence. A new pick is only attempted on a due 2h-UTC
    slot AND only if capacity remains under MAX_CONCURRENT. `dry=True`
    makes NO state/log/notify side effects whatsoever (including not
    stamping last_slot_ts/last_recap_date) — a pure preview of what this
    cycle WOULD do, same contract as daily_pick.run_daily_pick's dry mode.
    Returns {"action": "cycle", "due", "slot_ts", "exits", "holding",
    "entry", "open_count"}."""
    eng = state.setdefault("tradfi_engine", _fresh_engine())
    _migrate_engine(eng)

    tag = " DRY" if dry else ""
    now = datetime.now(timezone.utc)
    today_str = f"{now:%Y-%m-%d}"
    slot_ts = _slot_ts(now)
    due = eng.get("last_slot_ts") != slot_ts

    open_trades = eng.get("open_trades", [])
    print(f"  [TRADFI{tag}] cycle @ {now:%H:%M} UTC | open={len(open_trades)}/"
          f"{MAX_CONCURRENT} {[t['symbol'] for t in open_trades]} | "
          f"last_slot_ts={eng.get('last_slot_ts')} | slot={slot_ts} | due={due}")

    # -- daily recap: checked every call, independent of slot/capacity, so
    #    a run of closed-market or at-capacity slots can never delay it.
    if not dry and eng.get("last_recap_date") != today_str:
        _send_daily_recap(eng, today_str)
        eng["last_recap_date"] = today_str
        save_state(state)

    # -- reconcile every open trade, every call. `holdings` (not raw
    #    eng["open_trades"]) is what capacity math below reads — in dry
    #    mode a would-exit position must NOT still occupy a slot, exactly
    #    like daily_pick.run_daily_pick's own dry-mode contract (its
    #    comment: "dry mode already excludes anything that would've
    #    exited this cycle"). In real mode this ends up identical to
    #    eng["open_trades"], since _book_exit has already removed it.
    # ----------------------------------------------------------------------
    exits: list[dict] = []
    holdings: list[str] = []
    for t in list(open_trades):
        c1h = _fetch_1h(t["symbol"])
        if c1h is None or c1h.empty:
            print(f"  [TRADFI{tag}] {t['symbol']}: 1h fetch failed this "
                  f"cycle — holding, no exit check")
            holdings.append(t["symbol"])
            continue
        last = c1h.iloc[-1]
        result = _check_exit(t, float(last["high"]), float(last["low"]),
                             float(last["close"]), now)
        if result is None:
            holdings.append(t["symbol"])
            continue
        exit_price, reason = result
        if dry:
            exits.append({"action": f"would_exit_{reason}", "symbol": t["symbol"],
                         "exit_price": exit_price})
            continue                # NOT held — frees the slot in preview
        realized = _book_exit(state, eng, t, exit_price, reason, now)
        exits.append({"action": "exit", "symbol": t["symbol"], "reason": reason,
                     "pnl": realized})

    held_symbols = set(holdings)

    # -- entry: only on a due slot, only if capacity remains -------------
    entry_action = None
    if due:
        capacity = MAX_CONCURRENT - len(holdings)
        if capacity <= 0:
            print(f"  [TRADFI{tag}] slot due but at capacity "
                  f"({len(holdings)}/{MAX_CONCURRENT} open) — no new "
                  f"pick this slot")
            entry_action = {"action": "at_capacity", "open_count": len(holdings)}
            if not dry:
                eng["last_slot_ts"] = slot_ts
                save_state(state)
        else:
            scored = []
            for sym in UNIVERSE:
                if not is_market_open(sym, now):
                    continue                    # closed market — skipped silently
                rec = _score_symbol(sym)
                if rec is not None:
                    scored.append(rec)
            ranked = sorted(scored, key=lambda r: r["conviction"], reverse=True)

            picked = None
            for cand in ranked:
                if cand["symbol"] in held_symbols:
                    continue
                # NO GAMBLING IN QUIET TAPE — mirrors daily_pick's
                # select_pick calm-regime A-only rule exactly.
                if cand["regime"] == "calm" and cand["conviction"] < CONVICTION_FLOOR:
                    print(f"  [TRADFI{tag}] {cand['symbol']} CALM-REGIME SKIP: "
                          f"conviction {cand['conviction']:.0f} < "
                          f"{CONVICTION_FLOOR:.0f} floor")
                    continue
                key = f"{cand['symbol']}:{cand['direction']}"
                stamp = eng.get("last_stopouts", {}).get(key)
                if stamp:
                    try:
                        age_h = (now - datetime.fromisoformat(stamp["ts"])
                                ).total_seconds() / 3600
                    except Exception:
                        age_h = 999
                    if (age_h < STOPOUT_COOLDOWN_H
                            and cand["conviction"] <= stamp["conviction"] + 5):
                        print(f"  [TRADFI{tag}] {cand['symbol']} COOLDOWN SKIP: "
                              f"stopped out {age_h:.1f}h ago at conv "
                              f"{stamp['conviction']:.0f}, signal no stronger")
                        continue
                picked = cand
                break

            if picked is None:
                entry_action = {"action": "no_pick", "scored": len(scored)}
                if not dry:
                    eng["last_slot_ts"] = slot_ts
                    save_state(state)
            elif dry:
                entry_action = {"action": "would_enter", "symbol": picked["symbol"],
                               "direction": picked["direction"],
                               "conviction": picked["conviction"]}
            else:
                entry_action = _do_entry(state, eng, picked, now)
                eng["last_slot_ts"] = slot_ts
                save_state(state)
    else:
        print(f"  [TRADFI{tag}] not due yet — reconcile only")

    return {"action": "cycle", "due": due, "slot_ts": slot_ts, "exits": exits,
            "holding": [t["symbol"] for t in eng.get("open_trades", [])],
            "entry": entry_action, "open_count": len(eng.get("open_trades", []))}
