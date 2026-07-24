"""
gold_book.py — THE GOLD BOOK: a broker-free, self-contained paper-trading
book for round 48's sealed-test-validated gold breakout edge (GLD
donchian55 + EMA20 exit; step48_tradfi_trend.py family3_breakout,
"donchian55 EMA20exit" GLD 1d row — sealed test +$199/trade / +31.9% /
4.4y). No Alpaca, no broker, no tax ID: fills are SIMULATED against real
daily GLD closes pulled from yfinance, using the repo's own cost engine
(backtest.CostModel, via step48's own costs_for("GLD") so the round-trip
cost is byte-identical to the sealed test: 1.0bp fee + 1.0bp slippage each
side, 0 half-spread, 0 funding — 4bps round trip. See step48's costs_for()
and its module docstring's COSTS section).

THE VALIDATED RULE (deployed VERBATIM, imported not reimplemented):
  daily GLD bars. ENTER LONG when the daily close breaks above the highest
  HIGH of the prior 55 daily bars (Donchian-55 breakout, shift(1)-
  disciplined so the breakout bar is never inside the window it's breaking
  out of). EXIT when the daily close falls below EMA20 of close. Long-
  only, one position at a time. This IS
  step48_tradfi_trend.donchian_ema_exit(d, 55, ema_n=20) — imported and
  called directly, never copied or reimplemented.

OWN LEDGER, NEVER MIXED: state["gold_book"] is a completely separate
scoreboard from the BloFin crypto ledger (state["virtual_equity"] and
friends). Gold is a different market and a different account; the two
numbers must never be added, subtracted, or displayed as one figure.
Starts at $10,000 paper, matching the backtest's own account size.

STRUCTURAL TEMPLATE: news_book.py — an isolated paper book with its own
state dict, own equity, own simulated PnL, ZERO exchange orders, safe to
run on every daemon/hourly cycle because it can never collide with the
shared BloFin net. Gold follows the same shape.

FILL CONVENTION — a deliberate, explicit choice, DIFFERENT from the
backtest's own next-bar-open fill, and worth reading closely: this is a
DAILY bot that only ever wakes up AFTER a daily bar has already closed
(yfinance daily bars finalize once the US market closes, ~21:00 UTC). By
the time this code can act at all, the signal bar's close is already
fixed, known history — waiting for "next bar's open" would mean giving up
a full extra day of exposure for no reason a real trader managing this by
hand would accept. So the live paper book fills AT the signal bar's own
close (adjusted for CostModel's spread+slippage, exactly like the
backtest adjusts every one of its fills), not next-bar-open. This is NOT
a lookahead relaxation: nothing about a future, not-yet-closed bar is
ever read — only the already-closed bar's own already-public close.

SIZING: full-notional, one slot, size_frac=1.0 — the same all-in sizing
run_backtest used for family 3 (score() never passes a smaller
size_frac). Simplified relative to the backtest's internal cash/units
bookkeeping (which sizes off the bar's raw open but fills at the
adverse-adjusted price, a quirk documented in backtest.py's execute()):
here shares = equity / entry_fill_price, i.e. the fill price ITSELF sets
the share count, so the position is exactly fully invested with no
open/fill mismatch. The dollar difference against the backtest's own
convention is at most one adverse_frac (~1bp) of one trade's sizing —
immaterial next to the validated edge's expectancy.

IDEMPOTENCY: yfinance daily bars finalize once, but this function may be
called many times before the NEXT bar closes (every daemon cycle, every
hourly.py backstop run). state["gold_book"]["last_bar_date"] records the
date of the last daily bar this book actually decided on; if the newest
available bar's date matches, the whole decision step is skipped — a
clean no-op, never a re-trade.

DRY MODE: run_gold_book(state, dry=True) computes and prints the full
decision (latest bar, 55-day high, EMA20, in/out, would-enter/exit +
sizing) with NO state writes, NO notify, NO log_event. Used by
step51_gold_smoke.py against the real cached/fresh GLD data.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from step48_tradfi_trend import costs_for, donchian_ema_exit, fetch_and_save

SYMBOL = "GLD"
ENTRY_N = 55                 # donchian breakout lookback, in daily bars
EMA_N = 20                   # EMA exit span, in daily bars
START_EQUITY = 10_000.0      # paper scoreboard base — its OWN ledger

FETCH_THROTTLE_S = 30 * 60   # never hit yfinance more than once per 30 min,
                              # no matter how often the daemon/hourly cycle
                              # calls this function
_last_fetch_ts = 0.0


def _now():
    return datetime.now(timezone.utc)


def _book(state: dict) -> dict:
    return state.setdefault("gold_book", {
        "equity": START_EQUITY,
        "open_trade": None,      # {entry_date, entry_price, shares,
                                  #  notional, stop, reason, hi55_at_entry,
                                  #  entry_fee}
        "last_bar_date": None,   # date string of the last daily bar this
                                  # book actually decided on (idempotency)
        "trades": [],            # closed round trips, most-recent last
    })


def _load_gld_daily() -> pd.DataFrame:
    """Cached GLD daily bars via step48's OWN fetch_and_save (imported, not
    reimplemented) — same file (data_tradfi_GLD_1d.parquet), same schema.
    Throttled to at most one live yfinance pull per FETCH_THROTTLE_S; in
    between, this just rereads the parquet cache (no network at all).
    Monkeypatched wholesale by tests / the smoke script's own callers to
    inject synthetic or point-in-time data offline."""
    global _last_fetch_ts
    now = time.time()
    if (now - _last_fetch_ts) >= FETCH_THROTTLE_S:
        d = fetch_and_save(SYMBOL, "1d", "max", use_cache=False)
        _last_fetch_ts = now
    else:
        d = fetch_and_save(SYMBOL, "1d", "max", use_cache=True)
    return d.sort_values("timestamp").reset_index(drop=True)


def _decision(d: pd.DataFrame) -> dict:
    """Pure: computes the donchian55/EMA20 signal on the FULL series `d`
    (step48's own donchian_ema_exit — imported, not reimplemented) and
    reads the latest bar's desired in/out state. No state mutation, so
    dry mode and the live path can never drift apart — they call this
    exact same function."""
    sig = donchian_ema_exit(d, ENTRY_N, ema_n=EMA_N)
    i = len(d) - 1
    hi55 = d["high"].rolling(ENTRY_N).max().shift(1)
    ema20 = d["close"].ewm(span=EMA_N, adjust=False).mean()
    hi55_v = hi55.iloc[i]
    return {
        "bar_date": str(pd.Timestamp(d["timestamp"].iloc[i]).date()),
        "close": float(d["close"].iloc[i]),
        "hi55": float(hi55_v) if pd.notna(hi55_v) else None,
        "ema20": float(ema20.iloc[i]),
        "desired_in": bool(sig.iloc[i] > 0),
    }


def _fmt(v):
    return f"{v:.2f}" if v is not None else "n/a"


def run_gold_book(state: dict, dry: bool = False) -> dict:
    """One decision cycle. Idempotent per daily bar — safe to call every
    daemon cycle / every hourly.py backstop run. Returns a small summary
    dict, mainly for tests/smoke. Places zero broker orders; this is a
    pure paper simulation against real GLD prices."""
    gb = state.get("gold_book") if dry else _book(state)
    if gb is None:
        gb = {"equity": START_EQUITY, "open_trade": None,
              "last_bar_date": None, "trades": []}
    tag = " DRY" if dry else ""

    d = _load_gld_daily()
    dec = _decision(d)
    have_position = gb["open_trade"] is not None

    print(f"  [GOLD{tag}] {dec['bar_date']} close ${dec['close']:.2f} | "
          f"55d-high {_fmt(dec['hi55'])} | EMA20 {dec['ema20']:.2f} | "
          f"signal={'IN' if dec['desired_in'] else 'OUT'} | "
          f"position={'OPEN' if have_position else 'FLAT'}")

    if dry:
        equity = gb["equity"]
        if not have_position and dec["desired_in"]:
            action = "would_enter"
        elif have_position and not dec["desired_in"]:
            action = "would_exit"
        elif have_position:
            action = "would_hold"
        else:
            action = "would_stay_flat"
        shares = equity / dec["close"] if dec["close"] else 0.0
        print(f"  [GOLD DRY] equity ${equity:,.2f} -> {action} | "
              f"full-notional would be {shares:.2f} sh (~${equity:,.0f}) — "
              f"NO STATE WRITES, NO NOTIFY")
        return {"action": action, **dec, "equity": equity,
                "open_trade": gb.get("open_trade")}

    if gb.get("last_bar_date") == dec["bar_date"]:
        print(f"  [GOLD] {dec['bar_date']} already processed — no-op "
              f"(idempotent)")
        return {"action": "noop_already_processed", **dec,
                "equity": gb["equity"]}

    from step5_paper_trade import log_event, notify, save_state

    costs = costs_for(SYMBOL)

    # -- flat, signal says enter -------------------------------------------
    if not have_position and dec["desired_in"]:
        entry_price = costs.fill_price(dec["close"], +1)
        notional = gb["equity"]
        shares = notional / entry_price
        entry_fee = costs.fee(shares * entry_price)
        gb["equity"] = round(gb["equity"] - entry_fee, 2)
        gb["open_trade"] = {
            "entry_date": dec["bar_date"],
            "entry_price": round(entry_price, 4),
            "shares": shares,
            "notional": round(notional, 2),
            "stop": None,           # no hard stop — EMA20 close is the exit
            "reason": "donchian55_breakout",
            "hi55_at_entry": dec["hi55"],
            "entry_fee": round(entry_fee, 2),
        }
        gb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print(f"  [GOLD] LONG @ ${entry_price:.2f} | {shares:.2f} sh "
              f"(~${notional:,.0f}) | broke above 55d high "
              f"${_fmt(dec['hi55'])} | equity ${gb['equity']:,.2f}")
        log_event({"action": "gold_enter", "bar_date": dec["bar_date"],
                   "entry_price": round(entry_price, 4),
                   "shares": round(shares, 4), "hi55": dec["hi55"],
                   "equity": gb["equity"]})
        notify("🥇 GOLD BOOK LONG (paper)",
               f"GLD ${dec['close']:.2f} broke above the 55-day high "
               f"${_fmt(dec['hi55'])} — entered ${entry_price:.2f}, "
               f"equity ${gb['equity']:,.2f}")
        return {"action": "entered", **dec, "equity": gb["equity"]}

    # -- in a position, signal says exit ------------------------------------
    if have_position and not dec["desired_in"]:
        t = gb["open_trade"]
        exit_price = costs.fill_price(dec["close"], -1)
        gross = t["shares"] * (exit_price - t["entry_price"])
        exit_fee = costs.fee(t["shares"] * exit_price)
        realized = round(gross - exit_fee, 2)
        gb["equity"] = round(gb["equity"] + realized, 2)
        rec = {"entry_date": t["entry_date"], "entry_price": t["entry_price"],
               "exit_date": dec["bar_date"], "exit_price": round(exit_price, 4),
               "shares": t["shares"], "pnl": realized,
               "reason": "close_below_ema20", "equity_after": gb["equity"]}
        gb["trades"].append(rec)
        del gb["trades"][:-200]
        gb["open_trade"] = None
        gb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print(f"  [GOLD] EXIT @ ${exit_price:.2f} | close ${dec['close']:.2f} "
              f"< EMA20 ${dec['ema20']:.2f} | pnl ${realized:+,.2f} | "
              f"equity ${gb['equity']:,.2f}")
        log_event({"action": "gold_exit", **rec})
        notify(f"🥇 GOLD exit ${realized:+,.2f} (paper)",
               f"GLD closed ${dec['close']:.2f}, below EMA20 "
               f"${dec['ema20']:.2f} — equity ${gb['equity']:,.2f}")
        return {"action": "exited", **dec, "pnl": realized,
                "equity": gb["equity"]}

    # -- nothing changes (still in, or still flat) — mark the bar done ------
    gb["last_bar_date"] = dec["bar_date"]
    save_state(state)
    status = "holding" if have_position else "flat, no signal"
    print(f"  [GOLD] {status} — nothing to do")
    return {"action": "hold", **dec, "equity": gb["equity"]}
