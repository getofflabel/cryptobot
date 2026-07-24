"""
gold_book.py — THE GOLD BOOK: REAL BloFin DEMO orders on gold, running
round 48's sealed-test-validated donchian55/EMA20 trend edge
(step48_tradfi_trend.donchian_ema_exit — imported, never reimplemented).

ROUND 51 REWIRE (this file): before this round, THE GOLD BOOK was an
invisible internal paper sim — a self-contained ledger that simulated fills
against yfinance GLD closes and never touched the exchange. Owner directive:
he wants to SEE gold trades on his BloFin screen. This file now places real
orders on the BloFin DEMO account, the same way THE STRIKES (tactical.py)
and THE SHORTS LAB (shorts_lab.py) do. The strategy logic (donchian55 entry,
EMA20 exit) is UNCHANGED — only the data source and execution layer moved
from (yfinance GLD, an internal ledger) to (BloFin candles, real demo
orders).

THE SYMBOL — an important, plainly-stated substitution:
BloFin's instruments endpoint lists BOTH XAU-USDT and XAUT-USDT. We
confirmed empirically (2026-07 rewire) that XAU-USDT is listed on BloFin's
PROD instruments endpoint but is NOT tradeable, and has NO market data, on
the DEMO trading host (both /api/v1/market/tickers and
/api/v1/market/candles return code 152002 "Parameter instId error" for
XAU-USDT on demo-trading-openapi.blofin.com; the private
/api/v1/account/positions endpoint rejects it too). XAUT-USDT (Tether Gold,
a token pegged to one troy ounce of gold) IS listed and fully tradeable on
BOTH the demo and prod hosts, and its price tracks the same underlying gold
market XAU-USDT would (we compared same-day closes on both venues and they
match). So THIS BOOK TRADES XAUT-USDT ON DEMO — the closest available real,
owner-visible proxy for gold exposure the demo venue actually offers. SYMBOL
below is the single place this lives; if BloFin ever lists XAU-USDT on demo,
flip this one constant.

THE VALIDATED RULE (deployed VERBATIM, imported not reimplemented):
  daily bars. ENTER LONG when the daily close breaks above the highest HIGH
  of the prior 55 daily bars (Donchian-55 breakout, shift(1)-disciplined so
  the breakout bar is never inside the window it's breaking out of). EXIT
  when the daily close falls below EMA20 of close. Long-only, one position
  at a time. This IS step48_tradfi_trend.donchian_ema_exit(d, 55, ema_n=20).

TRANSFER ASSUMPTION, stated plainly: the edge was sealed-test-validated on
TWO different session structures — GLD (NYSE cash-session daily bars, closes
21:00 UTC) and GC=F (COMEX gold futures, nearly-24h trading) — and it
survived both. XAUT-USDT's 24/7 crypto-venue daily bars (UTC-midnight close)
are a THIRD variant of the same underlying gold market. We are transferring
the rule to this third variant on the strength of "same edge, two session
shapes already survived it" — not on a fresh validation of this exact venue.
That is an assumption, not a proof, and it is stated here so nobody mistakes
it for one.

DATA: daily candles come from the repo's own BloFin adapter
(config.make_exchange("live") -> exchange.BlofinExchange, i.e. the PROD
market-data host, which has fuller history for XAUT-USDT than demo: 399
bars vs demo's 217 at rewire time — plenty of margin over the 55+20 bar
warmup this rule needs). BlofinExchange.get_candles() already discards the
still-forming bar using BloFin's own "confirmed" flag (candle row index 8;
verified empirically: the newest row comes back with confirmed="0" and
every prior row "1" — see exchange.py's BlofinExchange.get_candles). So
"only ever act on a CLOSED daily bar" is enforced by the adapter itself,
not by anything in this file; we rely on it and note it here so the
guarantee is documented somewhere a human will actually read it. Bars are
UTC-midnight-close, confirmed against a live pull: the newest CLOSED row's
timestamp was always the calendar day before "now" in UTC, exactly as
expected for a UTC-midnight daily close.

IDEMPOTENCY: state["gold_book"]["last_bar_date"] records the date of the
last daily bar this book actually decided on; if the newest available bar's
date matches, the whole decision step is skipped — a clean no-op, never a
re-trade. Unchanged from the paper-sim version.

LEVERAGE & SIZING — the owner's "max the dial per geometry" principle,
applied honestly to THIS book's geometry: the ride's dial is 10x because an
-8% hard stop bounds the loss on every trade. THIS book's only downside stop
is the crash-insurance SL 18% away (see PROTECTION below) — the real exit is
the EMA20 close, a trend line, not a fixed distance, and the validated
backtest's own max drawdown at 1x was -13.9%. No hard stop close to price +
a trend-following exit means leverage compounds an uncapped-by-design
drawdown, not a bounded one. So the SAME principle that put the ride at 10x
puts THIS book at A LOW NUMBER: leverage 2x, allocation 25% of the shared
ledger (state["virtual_equity"]) — i.e. ~0.5x equity notional. The dial is
set by the stop geometry, and this system's stop geometry is loose.

PROTECTION: no take-profit — round 11 (see step5_paper_trade.py's SL_PCT
comment) measured that a TP amputates exactly the big winners a trend
system lives on, so the winners run, always. A WIDE crash-insurance stop-
loss is placed via place_tpsl at entry*(1 - 0.18) — 18% below entry, far
outside the EMA20 exit's normal reach — pure disaster insurance for a flash
crash between daily decisions, never trade management. The EMA20
close-below exit is executed by THIS BOOK ITSELF, on daily closes, via a
reduce-only market order; the 18% SL should essentially never be the thing
that closes a winning or normally-losing trade.

BOOK ACCOUNTING: state["gold_book"] = {"open_trade": {...}|None,
"last_bar_date", "trades": [...], "realized_pnl_total"}. This trades a
DIFFERENT symbol (XAUT-USDT) than every BTC-USDT book (the ride, the
strikes, the shorts lab, the apprentice, the newsdesk) — book_ledger.py's
attribution layer does not need to know about it, and it is never added to
recorded_book_positions(). But it SHARES the demo account's margin and
overall USDT balance with every other book: a gold win or loss changes the
SAME futures_balance() every BTC book eventually syncs against. See
step5_paper_trade.sync_ledger_to_account's has_trade guard, extended by
this rewire to also check gold_book's open_trade — so the shared ledger
sync never folds an in-flight, unrealized gold position into virtual_equity
mid-trade (it already skipped that for every BTC book; gold now gets the
same protection).

RECONCILIATION: every cycle, before deciding anything, this book reads
private.net_position_contracts(SYMBOL) — the exchange's own truth for this
symbol (no other book ever touches XAUT-USDT, so the whole net belongs to
gold, unlike the BTC books which must share their symbol's net). If the
book's own record says a trade is open but the exchange shows it materially
gone, the crash-insurance SL must have fired: book the exit from the most
recent fill and notify. If the exchange shows an unexplained position while
the book's own record is flat, this book does NOT auto-adopt it (unlike
shorts_lab) — it logs and notifies loudly and skips trading that cycle,
because nothing else should ever be touching this symbol and a mismatch
here is more likely a bug than routine drift.

HUD: SKIPPED on purpose (future work). live_read.py's position card prices
everything off the BTC-USDT live feed; showing an XAUT-USDT position there
with BTC prices would just be wrong. Wiring gold into the HUD needs its own
price feed plumbing in live_read.py, not attempted here.

DRY MODE: run_gold_book(private, live_feed, state, dry=True) computes and
prints the full decision (latest bar, 55-day high, EMA20, in/out,
would-enter/exit + sizing) with NO orders placed and NO state writes, NO
notify, NO log_event. It DOES make read-only calls (candles, instrument
spec, current net position) so the printed decision reflects the real
account — reads are never a live-order risk. Used by step51_gold_smoke.py.
"""

from __future__ import annotations

import time

import pandas as pd

from step48_tradfi_trend import donchian_ema_exit

SYMBOL = "XAUT-USDT"          # see module docstring: the demo-tradeable
                               # gold proxy — NOT XAU-USDT (unlisted on demo)
# 2026-07-24: 55 -> 20 after Wallace's dormancy audit. donchian55 needed a
# +17.7% rally to fire (median ~113 days away); donchian20 is the SAME shape,
# was a round-48 two-window survivor on BOTH GLD and GC=F, and PASSED ITS OWN
# SEALED TESTS on both (GLD +$156.63/t, +40.7%, DD -13.9%, 4.4y; GC=F
# +$83.72/t, +24.3%, 5.2y). ~5.4 trades/yr vs 3.0, and fires on a +3.3% move
# instead of a +17.7% one. Faster trigger, same discipline, sealed-validated.
ENTRY_N = 20                  # donchian breakout lookback, in daily bars
EMA_N = 20                    # EMA exit span, in daily bars
CANDLE_BARS = 400             # requested history depth (warmup margin)

GOLD_ALLOC = 0.25             # 25% of the SHARED ledger, state["virtual_equity"]
GOLD_LEV = 2.0                # see LEVERAGE & SIZING in the module docstring
CRASH_SL_PCT = 0.18           # 18% crash-insurance SL, see PROTECTION above
ENTRY_FEE_BPS = 6.0           # BloFin taker fee — every order here is a
EXIT_FEE_BPS = 6.0            # plain market order, always taker-side

_spec_cache: dict = {}


def _instrument_spec(live_feed) -> dict:
    """Contract math for SYMBOL, parsed from BloFin's own instruments
    endpoint — never assumed. Confirmed at rewire time (GET
    /api/v1/market/instruments on BOTH demo and prod hosts, identical):
      contractValue = "0.001"  -> 1 contract = 0.001 XAUT (~0.001 troy oz)
      minSize       = "1"      -> smallest order is 1 contract
      lotSize       = "1"      -> order size must be a WHOLE number of
                                   contracts (unlike BTC-USDT's 0.1 lot) —
                                   this is why gold sizing below rounds to
                                   whole contracts, not tenths
      tickSize      = "0.1"    -> prices quoted/placed to 1 decimal
    Cached in-process (the spec does not change between cycles); one real
    GET per process lifetime, not one per decision."""
    if SYMBOL not in _spec_cache:
        spec = live_feed.get_instrument(SYMBOL)
        _spec_cache[SYMBOL] = {
            "contract_value": float(spec["contractValue"]),
            "min_size": float(spec["minSize"]),
            "lot_size": float(spec["lotSize"]),
            "tick_size": float(spec.get("tickSize", 0.1)),
        }
    return _spec_cache[SYMBOL]


def _fresh_book() -> dict:
    return {"open_trade": None, "last_bar_date": None, "trades": [],
            "realized_pnl_total": 0.0}


def _book(state: dict) -> dict:
    """Live-path accessor: reads state["gold_book"], migrating in place if
    it's still the OLD paper-sim schema (has "equity", no
    "realized_pnl_total" — the pre-rewire shape). The pre-rewire book was
    never a real position (it never placed an order), so migrating it is
    safe: there is nothing on the exchange to reconcile against from the
    old schema."""
    gb = state.get("gold_book")
    if gb is None or "realized_pnl_total" not in gb:
        gb = _fresh_book()
        state["gold_book"] = gb
    return gb


def _book_snapshot(state: dict) -> dict:
    """Dry-path accessor: same shape as _book(), but NEVER writes state."""
    gb = state.get("gold_book")
    if gb is None or "realized_pnl_total" not in gb:
        return _fresh_book()
    return gb


def _load_daily(live_feed) -> pd.DataFrame:
    """CANDLE_BARS daily bars from the repo's own BloFin adapter — see the
    DATA section of the module docstring for the closed-bar guarantee."""
    d = live_feed.get_candles(SYMBOL, "1d", CANDLE_BARS)
    return d.sort_values("timestamp").reset_index(drop=True)


def _decision(d: pd.DataFrame) -> dict:
    """Pure: computes the donchian55/EMA20 signal on the FULL series `d`
    (step48's own donchian_ema_exit — imported, not reimplemented) and
    reads the latest bar's desired in/out state. No state mutation, so dry
    mode and the live path can never drift apart — they call this exact
    same function."""
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


def _round_lot(raw: float, lot: float, minimum: float) -> float:
    n = round(raw / lot) * lot if lot else raw
    return max(minimum, n)


def _finish_exit(state, gb, t, exit_price, reason, bar_date) -> float:
    """Shared by BOTH exit paths (planned EMA20 exit and reconciled
    SL-fired exit): books the round trip on the book's own ledger line.
    Long-only PnL: profit when price RISES (exit - entry)."""
    from step5_paper_trade import log_event, notify, save_state

    contract_value = t.get("contract_value", 0.001)
    size_units = t["contracts"] * contract_value
    gross = size_units * (exit_price - t["entry_price"])
    fees = (t["entry_price"] * t.get("entry_fee_bps", ENTRY_FEE_BPS)
            + exit_price * EXIT_FEE_BPS) * size_units / 10_000
    realized = round(gross - fees, 2)

    rec = {"entry_date": t["entry_date"], "entry_price": t["entry_price"],
           "exit_date": bar_date, "exit_price": round(exit_price, 4),
           "contracts": t["contracts"], "pnl": realized, "reason": reason}
    gb["trades"].append(rec)
    del gb["trades"][:-200]
    gb["realized_pnl_total"] = round(
        gb.get("realized_pnl_total", 0.0) + realized, 2)
    gb["open_trade"] = None
    gb["last_bar_date"] = bar_date
    save_state(state)

    print(f"  [GOLD] EXIT ({reason}) @ ${exit_price:.2f} | pnl "
          f"${realized:+,.2f} | book total ${gb['realized_pnl_total']:+,.2f}")
    log_event({"action": "gold_exit", **rec})
    notify(f"🥇 GOLD exit ${realized:+,.2f} (demo)",
           f"{SYMBOL} closed ${exit_price:.2f} — {reason.replace('_', ' ')} "
           f"— book total ${gb['realized_pnl_total']:+,.2f} (demo)")
    return realized


def run_gold_book(private, live_feed, state: dict, dry: bool = False) -> dict:
    """One decision cycle. Idempotent per daily bar — safe to call every
    daemon cycle / every hourly.py backstop run. Places REAL market orders
    on the BloFin DEMO account (SYMBOL, see module docstring) unless
    dry=True. Returns a small summary dict, mainly for tests/smoke."""
    gb = _book_snapshot(state) if dry else _book(state)
    tag = " DRY" if dry else ""

    d = _load_daily(live_feed)
    dec = _decision(d)
    have_position = gb["open_trade"] is not None

    try:
        net = private.net_position_contracts(SYMBOL)
    except Exception as e:
        print(f"  [GOLD{tag}] position read failed ({str(e)[:80]}) — "
              f"skipping this cycle (never trade on an unreadable position)")
        return {"action": "skip_unreadable", **dec}

    print(f"  [GOLD{tag}] {dec['bar_date']} close ${dec['close']:.2f} | "
          f"55d-high {_fmt(dec['hi55'])} | EMA20 {dec['ema20']:.2f} | "
          f"signal={'IN' if dec['desired_in'] else 'OUT'} | "
          f"book={'OPEN' if have_position else 'FLAT'} | "
          f"exchange net {net:+.1f} ct")

    # -- reconcile: book says open, exchange shows it materially gone ------
    if have_position and abs(net) < gb["open_trade"]["contracts"] / 2:
        t = gb["open_trade"]
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        print(f"  [GOLD{tag}] our long is GONE on the exchange (net "
              f"{net:+.1f} vs recorded {t['contracts']:.0f} ct) -> "
              f"crash-insurance SL fired")
        if dry:
            print("  [GOLD DRY] would book this SL-fired exit — no state "
                  "changes made")
            return {"action": "would_reconcile_sl_exit",
                    "exit_price": exit_price, **dec}
        realized = _finish_exit(state, gb, t, exit_price, "sl_fired",
                                dec["bar_date"])
        return {"action": "reconciled_sl_exit", **dec, "pnl": realized}

    # -- reconcile: exchange shows a position the book has no record of ----
    if not have_position and abs(net) > 0.5:
        print(f"  [GOLD{tag}] ⚠️ unexplained {SYMBOL} position on "
              f"the exchange (net {net:+.1f} ct) — no other book trades "
              f"this symbol and the gold book has no record of it. NOT "
              f"trading this cycle — check BloFin by hand.")
        if not dry:
            from step5_paper_trade import log_event, notify
            log_event({"action": "gold_unexplained_position", "net": net})
            notify("⚠️ Unexplained gold position (demo)",
                   f"BloFin shows {net:+.1f} ct net on {SYMBOL} that the "
                   f"gold book never opened — check the app.")
        return {"action": "unexplained_position", "net": net, **dec}

    # -- dry mode: compute and print every possible action, write nothing --
    if dry:
        spec = _instrument_spec(live_feed)
        if not have_position and dec["desired_in"]:
            try:
                ref_price = live_feed.get_ticker(SYMBOL).last
            except Exception:
                ref_price = dec["close"]
            notional = float(state.get("virtual_equity", 0.0)) * GOLD_ALLOC * GOLD_LEV
            raw = notional / (spec["contract_value"] * ref_price) if ref_price else 0.0
            contracts = _round_lot(raw, spec["lot_size"], spec["min_size"])
            sl_est = round(ref_price * (1 - CRASH_SL_PCT), 1)
            est_notional = contracts * spec["contract_value"] * ref_price
            print(f"  [GOLD DRY] WOULD ENTER LONG {contracts:.0f} ct "
                  f"(~${est_notional:,.0f} notional, {GOLD_LEV:.0f}x, "
                  f"{GOLD_ALLOC*100:.0f}% of "
                  f"${state.get('virtual_equity', 0):,.2f} ledger) @ "
                  f"~${ref_price:,.2f} | broke 55d-high ${_fmt(dec['hi55'])} "
                  f"| crash-insurance SL ~${sl_est:,.2f} (no TP) — NO ORDER "
                  f"PLACED")
            return {"action": "would_enter", **dec, "contracts": contracts,
                    "ref_price": ref_price, "sl_est": sl_est,
                    "notional_est": round(est_notional, 2)}
        if have_position and not dec["desired_in"]:
            t = gb["open_trade"]
            print(f"  [GOLD DRY] WOULD EXIT LONG {t['contracts']:.0f} ct — "
                  f"close ${dec['close']:.2f} < EMA20 ${dec['ema20']:.2f} "
                  f"— NO ORDER PLACED")
            return {"action": "would_exit", **dec, "contracts": t["contracts"]}
        action = "would_hold" if have_position else "would_stay_flat"
        print(f"  [GOLD DRY] {action} — NO ORDER PLACED")
        return {"action": action, **dec}

    # -- idempotency: this exact bar was already decided on ----------------
    if gb.get("last_bar_date") == dec["bar_date"]:
        print(f"  [GOLD] {dec['bar_date']} already processed — no-op "
              f"(idempotent)")
        return {"action": "noop_already_processed", **dec}

    from step5_paper_trade import log_event, notify, now_utc, save_state

    # -- flat, signal says enter --------------------------------------------
    if not have_position and dec["desired_in"]:
        spec = _instrument_spec(live_feed)
        try:
            ref_price = live_feed.get_ticker(SYMBOL).last
        except Exception:
            ref_price = dec["close"]
        notional = float(state.get("virtual_equity", 0.0)) * GOLD_ALLOC * GOLD_LEV
        raw = notional / (spec["contract_value"] * ref_price) if ref_price else 0.0
        contracts = _round_lot(raw, spec["lot_size"], spec["min_size"])

        print(f"  [GOLD] BREAKOUT — entering LONG {contracts:.0f} ct "
              f"{SYMBOL} (~${contracts * spec['contract_value'] * ref_price:,.0f} "
              f"notional) @ ~${ref_price:,.2f}")
        if not private.ensure_leverage(SYMBOL, GOLD_LEV, "cross"):
            notify("⚠️ gold entry ABORTED (demo)",
                   "couldn't set leverage — no order placed, check BloFin")
            return {"action": "entry_aborted_leverage", **dec}
        try:
            order_id = private.market_order(SYMBOL, "buy", contracts)
        except Exception as e:
            print(f"  [GOLD] ENTRY FAILED: {str(e)[:100]}")
            log_event({"action": "gold_entry_failed", "error": str(e)[:200]})
            notify("⚠️ gold entry FAILED (demo)",
                   f"tried to go long {SYMBOL} but the order was rejected: "
                   f"{str(e)[:80]}. No position opened — check BloFin.")
            return {"action": "entry_failed", "error": str(e)[:120], **dec}

        time.sleep(1.5)
        entry_price = ref_price
        try:
            fills = private.fills(SYMBOL, order_id)
            if fills:
                entry_price = float(fills[0]["fillPrice"])
        except Exception:
            pass

        sl_price = round(entry_price * (1 - CRASH_SL_PCT), 1)
        tpsl_id = None
        try:
            tpsl_id = private.place_tpsl(SYMBOL, "sell", contracts, None,
                                         sl_price)
        except Exception as e:
            print(f"  [GOLD] crash-insurance SL FAILED to place: "
                  f"{str(e)[:80]}")
            notify("⚠️ gold position UNPROTECTED (demo)",
                   f"{SYMBOL} long opened but the {CRASH_SL_PCT*100:.0f}% "
                   f"crash SL failed to place — check BloFin now")

        gb["open_trade"] = {
            "entry_date": dec["bar_date"],
            "entry_price": round(entry_price, 4),
            "contracts": contracts,
            "contract_value": spec["contract_value"],
            "notional": round(contracts * spec["contract_value"] * entry_price, 2),
            "sl_price": sl_price,
            "tpsl_id": tpsl_id,
            "order_id": order_id,
            "reason": "donchian55_breakout",
            "hi55_at_entry": dec["hi55"],
            "entry_fee_bps": ENTRY_FEE_BPS,
            "entry_time": now_utc(),
        }
        gb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print(f"  [GOLD] LONG @ ${entry_price:.2f} | {contracts:.0f} ct "
              f"(~${gb['open_trade']['notional']:,.0f}) | broke above 55d "
              f"high ${_fmt(dec['hi55'])} | crash SL ${sl_price:,.2f}")
        log_event({"action": "gold_enter", "bar_date": dec["bar_date"],
                   "entry_price": round(entry_price, 4),
                   "contracts": contracts, "hi55": dec["hi55"],
                   "sl_price": sl_price, "order_id": order_id})
        notify("🥇 GOLD LONG on your BloFin (demo)",
               f"{SYMBOL} @ ${entry_price:,.2f} — broke the 55-day high "
               f"${_fmt(dec['hi55'])}. {contracts:.0f} ct, {GOLD_LEV:.0f}x, "
               f"crash SL ${sl_price:,.2f} (no TP — riding the trend).")
        return {"action": "entered", **dec, "entry_price": entry_price,
                "contracts": contracts, "sl_price": sl_price}

    # -- in a position, signal says exit ------------------------------------
    if have_position and not dec["desired_in"]:
        t = gb["open_trade"]
        try:
            if t.get("tpsl_id"):
                private.cancel_tpsl(SYMBOL, t["tpsl_id"])
        except Exception:
            pass
        try:
            order_id = private.market_order(SYMBOL, "sell", t["contracts"],
                                            reduce_only=True)
        except Exception as e:
            print(f"  [GOLD] EXIT FAILED: {str(e)[:100]}")
            log_event({"action": "gold_exit_failed", "error": str(e)[:200]})
            notify("⚠️ gold exit FAILED (demo)",
                   f"EMA20 says exit {SYMBOL} but the order was rejected: "
                   f"{str(e)[:80]} — the crash SL is still protecting it, "
                   f"check BloFin.")
            return {"action": "exit_failed", "error": str(e)[:120], **dec}

        time.sleep(1.5)
        exit_price = dec["close"]
        try:
            fills = private.fills(SYMBOL, order_id)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass

        realized = _finish_exit(state, gb, t, exit_price,
                                "close_below_ema20", dec["bar_date"])
        return {"action": "exited", **dec, "pnl": realized}

    # -- nothing changes (still in, or still flat) — mark the bar done ------
    gb["last_bar_date"] = dec["bar_date"]
    save_state(state)
    status = "holding" if have_position else "flat, no signal"
    print(f"  [GOLD] {status} — nothing to do")
    return {"action": "hold", **dec}
