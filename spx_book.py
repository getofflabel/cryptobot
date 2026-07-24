"""
spx_book.py — THE S&P BOOK (internal-ledger PAPER book, round-60 sealed
RSI2 dip-buy edge, deployed verbatim).

WHAT THIS IS AND WHY IT IS PAPER-ONLY
Round 60 (see RESEARCH_LOG.md "ROUND 60 — the S&P system" and
MARKET_PLAYBOOKS.md's S&P section) sealed-validated a classic Connors-style
mean-reversion edge on the index, TWO independent instruments, BOTH pass:
    SPY  +$75.36/t x33, +24.9%, DD -8.8% (6.7y)
    ES=F +$124.07/t x29, +36.0%, DD -4.6% (5.2y)
That is a real, validated edge. But there is nowhere on this program's
actual trading venue to put it on: BloFin's demo host lists SPX-USDT, but
that instrument is a memecoin, not an S&P product (confirmed against
BloFin's own instrument metadata — it does not track the index). SPY-USDT
exists on BloFin's PROD host and does track real S&P levels (~0.08% basis,
per the R60 notes) but is PROD-ONLY (this program only ever trades DEMO)
and its book is thin. So there is currently no real order this program can
place that is honestly "the S&P edge."

Rather than let a sealed-passed edge sit on a shelf, THE S&P BOOK runs it
LIVE, for real, on its own terms: every day it reads the actual close price
of SPY off Yahoo Finance (yfinance) — a real, independent, public market
data source, not a synthetic feed — and simulates the fill against that
real price on this book's own internal virtual ledger
(state["spx_book"]["virtual_equity"]). Every trade is logged
(step5_paper_trade.log_event) and pushed to Wallace's phone
(step5_paper_trade.notify) exactly like a real book's trades are — visible,
trackable, held to account — the ONLY difference from a real book is that
no exchange order is ever placed and the money is fictional. See the
NEVER-ORDERS GUARD below for how that boundary is enforced in code, not
just in this paragraph.

THE VALIDATED RULE, DEPLOYED VERBATIM (daily SPY bars):
    ENTER LONG  when RSI(2) < 5  AND  close > SMA(200)
    EXIT        when close > SMA(5)  OR  RSI(2) > 65
    No fixed target (round 60's own dose-response test: capping the winner
    with a TP is what "no target" specifically outperformed).
    One position at a time, long-only.
_rsi()/_sma() below are Wilder's-RSI / plain-rolling-mean, the exact same
formula step70_replay.rsi2_dipbuy_sealed used as R60's own sealed oracle
(ewm(alpha=1/n, adjust=False)) — re-implemented inline here rather than
imported, so this file has zero import-time coupling to the backtest stack.

THE CLOSE-FILL ASSUMPTION, STATED HONESTLY
Every fill in this book — entry AND exit — happens at the SAME daily close
that generated the signal (the close that made RSI2<5 true is also the
fill price for going long that day; the close that made close>SMA5 true is
also the fill price for flattening that day). This is not a simplification
invented for this book: it is EXACTLY how the R60 sealed test itself was
scored (see step70_replay.rsi2_dipbuy_sealed's own entry_price=c[i] /
exit_price=c[exit_i]). A real book would have some slippage getting a fill
right at the printed close; this book does not model that, on purpose,
because doing anything else would silently stop matching the validated
config. Anyone reading this book's numbers should read them as "the sealed
backtest, continued forward in real time" — not as "what a live broker
fill would have looked like."

LEVERAGE & SIZING — the REALISTIC S&P line, not crypto's
Every crypto book in this program runs at 10-20x because BTC's own
geometry (tight stops, hourly bars) supports it. The S&P is a completely
different instrument with a completely different realistic leverage
ceiling — round 70 (see step70_replay.py / the round-70 notes) established
4x as the honest "how a real, non-crypto trader would actually size index
exposure" line, and that is the number used here, not a copy-pasted crypto
dial. Size = ALLOC_FRAC (95%) of THIS BOOK'S OWN virtual_equity, at
LEVERAGE (4x) — i.e. ~3.8x-equity notional, spent entirely on SPY "shares"
(fractional, since this is a pure ledger, never a real brokerage order).

FEES: 1bp (0.0001) per leg, applied to notional at both entry and exit —
matches this program's ETF cost convention (MARKET_PLAYBOOKS.md: "ETF costs
4bps round trip" is the two-leg total; 1bp/leg here is the conservative,
more-favorable-to-the-edge side of that range, stated plainly so nobody
mistakes it for the round-trip number).

PROTECTION: the sealed config has NONE — R60's own robustness grid tested
optional ATR stops on this exact shape and found they only ever hurt it
("give the dip room" — MARKET_PLAYBOOKS.md). Deploying verbatim means no
per-trade stop here either. But an edge with no per-trade stop deployed on
NEW, unproven-live-money (even if that money is fictional) with no human
watching every tick deserves ONE piece of insurance that is NOT part of
the validated config and is documented as exactly that: CRASH_ABORT_DD
(10%) is a ledger-level circuit breaker — if virtual_equity ever falls 10%+
off its own running peak, this book fires ONE loud alert
("🚨 ... crash-abort") so Wallace hears about it immediately. It does NOT
change the strategy, does NOT force an exit ahead of the real signal, and
does NOT stop future trading — it exists purely so a bad stretch is never
silent. This is insurance ON TOP of the sealed config, not a change to it.

CONTAINMENT — this book's money is FICTIONAL and must stay that way
state["spx_book"]["virtual_equity"] is this book's ENTIRE world. It is
never read by, written by, or reconciled against step5_paper_trade's
sync_ledger_to_account, book_ledger.recorded_book_positions,
book_ledger.attributed_position, or any other book's PnL. No BloFin
position exists for this book (SYMBOL is deliberately not a tradeable
instrument reference anywhere in this file — TICKER="SPY" is a yfinance
ticker string, nothing else touches it). See the NEVER-ORDERS GUARD in
run_spx_book for the code-level enforcement of "this book can never place
a real order," and test_spx_book.py's guard test + source-scan for the
proof.

IDEMPOTENCY: state["spx_book"]["last_bar_date"] — same pattern as
gold_book.py. If the newest available SPY daily bar's date matches, the
whole decision step is a clean no-op. Never a re-trade on the same bar.

TIMING: evaluated once per day, gated to weekdays at/after 21:30 UTC (US
cash-market close is 21:00 UTC standard / 20:00 UTC daylight — 21:30 is a
safe margin so the day's real closing print has settled before this book
reads it off Yahoo). Outside that window (and on weekends), a live call is
simply "not due" and returns without touching anything. dry=True bypasses
the due-check entirely (always renders a preview, see below) so smoke
tools can run it any time.

DATA: yfinance imported INSIDE the fetch function (never at module import
time), wrapped in try/except by the caller — a yfinance outage degrades to
"skip this cycle," never a crash, matching morning_read.py's own fetcher
convention.

DRY MODE: run_spx_book(None, state, dry=True) computes and prints the full
decision (latest bar, RSI2/SMA200/SMA5, would-enter/would-hold/would-exit +
sizing) with NO state writes, NO notify, NO log_event. Also bypasses the
due-check so it can be previewed at any time of day.

NOTIFY VOICE: one-trader voice, no internal book-name jargon, "(paper)"
stated every single time so this can never be mistaken for real BloFin
money — see _finish_exit and the entry branch in run_spx_book for the
exact copy.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

TICKER = "SPY"                 # a yfinance ticker string — NOT a BloFin
                                # instrument id; nothing in this file ever
                                # talks to an exchange (see module docstring)
HISTORY_PERIOD = "5y"          # yfinance history pulled fresh every cycle —
                                # ample margin over SMA200's 200-bar warmup

RSI_N = 2                      # R60 sealed shape
RSI_ENTRY_MAX = 5.0
RSI_EXIT_MIN = 65.0
SMA_TREND_N = 200
SMA_EXIT_N = 5

START_EQUITY = 2000.0
ALLOC_FRAC = 0.95               # 95% of THIS BOOK'S OWN virtual ledger
LEVERAGE = 4.0                  # the realistic S&P line (R70) — NOT crypto's
                                 # 20x, see module docstring
FEE_BPS_PER_LEG = 1.0           # 1bp/leg, see module docstring

CRASH_ABORT_DD = 0.10           # emergency 10% ledger-crash insurance,
                                 # BEYOND the sealed config (which has none)
CRASH_REARM_DD = 0.05           # re-arm the alert once equity recovers to
                                 # within 5% of peak — avoids re-alerting
                                 # every single cycle of one bad drawdown

DUE_HOUR_UTC = 21               # first cycle at/after 21:30 UTC, weekdays
DUE_MINUTE_UTC = 30             # (safe margin past the US cash close)


def _now():
    return datetime.now(timezone.utc)


def _now_str() -> str:
    return f"{_now():%Y-%m-%d %H:%M:%S} UTC"


def _fmt(v):
    return f"{v:.2f}" if v is not None else "n/a"


# ---------------------------------------------------------------------------
# book state
# ---------------------------------------------------------------------------


def _fresh_book() -> dict:
    return {
        "virtual_equity": START_EQUITY,
        "peak_equity": START_EQUITY,
        "open_trade": None,
        "last_bar_date": None,
        "trades": [],
        "realized_pnl_total": 0.0,
        "n": 0,
        "wins": 0,
        "crash_alerted": False,
    }


def _book(state: dict) -> dict:
    """Live-path accessor: reads/creates state["spx_book"]."""
    sb = state.get("spx_book")
    if sb is None or "virtual_equity" not in sb:
        sb = _fresh_book()
        state["spx_book"] = sb
    return sb


def _book_snapshot(state: dict) -> dict:
    """Dry-path accessor: same shape as _book(), but NEVER writes state."""
    sb = state.get("spx_book")
    if sb is None or "virtual_equity" not in sb:
        return _fresh_book()
    return sb


# ---------------------------------------------------------------------------
# pure signal math (RSI2 / SMA200 / SMA5) — the R60 sealed shape, verbatim
# ---------------------------------------------------------------------------


def _rsi(close: pd.Series, n: int) -> pd.Series:
    """Wilder's RSI — identical formula to strategy.rsi / step70_replay's
    R60 sealed oracle (ewm(alpha=1/n, adjust=False)). See module docstring
    for why this is re-implemented inline rather than imported."""
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down.replace(0, float("nan"))
    return 100 - 100 / (1 + rs)


def _sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n).mean()


def _decision(d: pd.DataFrame) -> dict:
    """Pure: reads the latest bar's dip-buy state off the FULL daily series
    `d` (must have a "close" column and a "timestamp" column). No state
    mutation — dry mode and the live path call this exact same function, so
    they can never drift apart. Mirrors gold_book._decision's shape."""
    close = d["close"]
    sma200 = _sma(close, SMA_TREND_N)
    sma5 = _sma(close, SMA_EXIT_N)
    r2 = _rsi(close, RSI_N)

    i = len(d) - 1
    px = float(close.iloc[i])
    r2_v = float(r2.iloc[i]) if pd.notna(r2.iloc[i]) else None
    sma200_v = float(sma200.iloc[i]) if pd.notna(sma200.iloc[i]) else None
    sma5_v = float(sma5.iloc[i]) if pd.notna(sma5.iloc[i]) else None

    entry_signal = bool(r2_v is not None and sma200_v is not None
                        and r2_v < RSI_ENTRY_MAX and px > sma200_v)
    exit_signal = bool((r2_v is not None and r2_v > RSI_EXIT_MIN)
                       or (sma5_v is not None and px > sma5_v))

    return {
        "bar_date": str(pd.Timestamp(d["timestamp"].iloc[i]).date()),
        "close": px,
        "rsi2": r2_v,
        "sma200": sma200_v,
        "sma5": sma5_v,
        "entry_signal": entry_signal,
        "exit_signal": exit_signal,
    }


def _size_shares(virtual_equity: float, price: float) -> float:
    if not price:
        return 0.0
    notional = virtual_equity * ALLOC_FRAC * LEVERAGE
    return notional / price


# ---------------------------------------------------------------------------
# data fetch — yfinance, imported lazily, degrades on failure (never raises
# out of run_spx_book's caller)
# ---------------------------------------------------------------------------


def _default_fetch():
    import yfinance as yf
    df = yf.Ticker(TICKER).history(period=HISTORY_PERIOD, interval="1d")
    if df is None or df.empty:
        return None
    df = df.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    if "date" in df.columns:
        df = df.rename(columns={"date": "timestamp"})
    elif "datetime" in df.columns:
        df = df.rename(columns={"datetime": "timestamp"})
    keep = ["timestamp", "open", "high", "low", "close"]
    df = df[[c for c in keep if c in df.columns]].dropna()
    return df


def latest_signal(fetch=None) -> dict | None:
    """Read-only convenience: today's live decision dict, or None if the
    fetch fails / there isn't enough history yet. Never touches state,
    never trades — safe to call any time (used by smoke checks)."""
    fetch_fn = fetch or _default_fetch
    try:
        raw = fetch_fn()
    except Exception as e:
        print(f"  [SPX] yfinance fetch failed: {str(e)[:100]}")
        return None
    if raw is None or len(raw) < SMA_TREND_N + 5:
        return None
    d = raw.sort_values("timestamp").reset_index(drop=True)
    return _decision(d)


# ---------------------------------------------------------------------------
# crash-abort insurance (beyond the sealed config — see module docstring)
# ---------------------------------------------------------------------------


def _check_crash_abort(sb: dict) -> bool:
    """Returns True the cycle a NEW >=10%-off-peak breach is detected (i.e.
    fires once per drawdown episode, not every cycle the ledger stays
    down). Re-arms once equity recovers to within CRASH_REARM_DD of peak.
    Peak-tracking happens here so this is the single source of truth for
    both the trigger and the ratchet."""
    sb["peak_equity"] = max(sb.get("peak_equity", sb["virtual_equity"]),
                            sb["virtual_equity"])
    peak = sb["peak_equity"]
    dd = (1 - sb["virtual_equity"] / peak) if peak else 0.0
    fired = False
    if dd >= CRASH_ABORT_DD and not sb.get("crash_alerted"):
        sb["crash_alerted"] = True
        fired = True
    elif dd < CRASH_REARM_DD:
        sb["crash_alerted"] = False
    return fired


# ---------------------------------------------------------------------------
# exit bookkeeping
# ---------------------------------------------------------------------------


def _finish_exit(state, sb, t, exit_price, exit_date, reason) -> float:
    from step5_paper_trade import log_event, notify, save_state

    shares = t["shares"]
    gross = shares * (exit_price - t["entry_price"])
    fees = ((t["entry_price"] * FEE_BPS_PER_LEG
            + exit_price * FEE_BPS_PER_LEG) * shares / 10_000)
    realized = round(gross - fees, 2)

    sb["virtual_equity"] = round(sb["virtual_equity"] + realized, 2)
    sb["n"] = sb.get("n", 0) + 1
    sb["wins"] = sb.get("wins", 0) + (1 if realized > 0 else 0)
    rec = {"entry_date": t["entry_date"], "entry_price": t["entry_price"],
           "exit_date": exit_date, "exit_price": round(exit_price, 4),
           "shares": round(shares, 4), "pnl": realized, "reason": reason}
    sb["trades"].append(rec)
    del sb["trades"][:-200]
    sb["realized_pnl_total"] = round(
        sb.get("realized_pnl_total", 0.0) + realized, 2)
    sb["open_trade"] = None
    sb["last_bar_date"] = exit_date

    acc = (sb["wins"] / sb["n"] * 100) if sb["n"] else 0.0
    crashed = _check_crash_abort(sb)
    save_state(state)

    print(f"  [SPX PAPER] EXIT ({reason}) @ ${exit_price:.2f} | pnl "
          f"${realized:+,.2f} | ledger ${sb['virtual_equity']:,.2f} | "
          f"record {sb['wins']}/{sb['n']} = {acc:.0f}%")
    log_event({"action": "spx_book_exit", **rec,
               "ledger": sb["virtual_equity"]})
    notify("📈 S&P dip-buy closed (paper)",
           f"Sold SPY ${exit_price:,.2f} — {reason.replace('_', ' ')} — "
           f"${realized:+,.2f} on this trade (paper). Running record "
           f"{sb['wins']}/{sb['n']} ({acc:.0f}%), ledger "
           f"${sb['virtual_equity']:,.2f} (paper).")

    if crashed:
        notify("🚨 S&P paper ledger down 10%+ (paper)",
               f"The simulated S&P ledger has fallen "
               f"{CRASH_ABORT_DD * 100:.0f}%+ off its peak "
               f"(${sb['peak_equity']:,.2f} -> "
               f"${sb['virtual_equity']:,.2f}). Nothing real is at risk — "
               f"this is paper money — but flagging loudly since the "
               f"sealed rule itself carries no per-trade stop.")
        log_event({"action": "spx_book_crash_abort",
                   "peak_equity": sb["peak_equity"],
                   "virtual_equity": sb["virtual_equity"]})

    return realized


# ---------------------------------------------------------------------------
# main entrypoint
# ---------------------------------------------------------------------------


def run_spx_book(live_feed_unused, state: dict, dry: bool = False,
                  now=None, fetch=None) -> dict:
    """One decision cycle. Idempotent per daily bar, gated to weekdays
    at/after DUE_HOUR_UTC:DUE_MINUTE_UTC — safe to call every daemon cycle
    / every hourly.py backstop run.

    NEVER-ORDERS GUARD: `live_feed_unused` is accepted only for call-site
    symmetry with the other books in this program (daemon.py/hourly.py all
    thread a `private`-style client through their book functions) — it is
    NEVER read from, NEVER called, and this book takes no `private` client
    at all. If something upstream ever threads an order-capable object in
    here anyway, refuse immediately, before touching state — see
    test_spx_book.py's guard test for the proof this actually fires, and
    its source-scan test for proof no order call exists anywhere below.
    """
    if live_feed_unused is not None and (
            hasattr(live_feed_unused, "market_order")
            or hasattr(live_feed_unused, "place_tpsl")
            or hasattr(live_feed_unused, "cancel_tpsl")
            or hasattr(live_feed_unused, "ensure_leverage")):
        raise AssertionError(
            "spx_book must NEVER receive an order-capable client — this "
            "book is simulation-only by design (see spx_book.py's module "
            "docstring)")

    now = now or _now()
    tag = " DRY" if dry else ""

    # -- due-check: weekdays only, at/after DUE_HOUR:DUE_MINUTE UTC. dry
    #    mode always evaluates (a pure preview) so smoke tools can run any
    #    time of day. ---------------------------------------------------
    if not dry:
        is_weekday = now.weekday() < 5
        due = is_weekday and (now.hour, now.minute) >= (DUE_HOUR_UTC,
                                                         DUE_MINUTE_UTC)
        if not due:
            return {"action": "not_due", "now": now.isoformat()}

    sb = _book_snapshot(state) if dry else _book(state)
    have_position = sb["open_trade"] is not None

    fetch_fn = fetch or _default_fetch
    try:
        raw = fetch_fn()
    except Exception as e:
        print(f"  [SPX{tag}] yfinance fetch failed ({str(e)[:80]}) — "
              f"skipping this cycle")
        return {"action": "fetch_failed", "error": str(e)[:120]}
    if raw is None or len(raw) < SMA_TREND_N + 5:
        print(f"  [SPX{tag}] insufficient SPY history — skipping this cycle")
        return {"action": "insufficient_data"}

    d = raw.sort_values("timestamp").reset_index(drop=True)
    dec = _decision(d)

    print(f"  [SPX{tag}] {dec['bar_date']} SPY close ${dec['close']:.2f} | "
          f"RSI2 {_fmt(dec['rsi2'])} | SMA200 {_fmt(dec['sma200'])} | "
          f"SMA5 {_fmt(dec['sma5'])} | "
          f"book={'OPEN' if have_position else 'FLAT'}")

    # -- dry mode: compute and print every possible action, write nothing --
    if dry:
        if have_position:
            t = sb["open_trade"]
            if dec["exit_signal"]:
                print(f"  [SPX DRY] WOULD EXIT {t['shares']:.2f} sh @ "
                      f"${dec['close']:.2f} — NO WRITES")
                return {"action": "would_exit", **dec,
                        "shares": t["shares"]}
            print(f"  [SPX DRY] HOLDING {t['shares']:.2f} sh — no exit "
                  f"signal yet — NO WRITES")
            return {"action": "would_hold", **dec, "shares": t["shares"]}
        if dec["entry_signal"]:
            shares = _size_shares(sb["virtual_equity"], dec["close"])
            notional = shares * dec["close"]
            print(f"  [SPX DRY] WOULD ENTER LONG {shares:.2f} sh "
                  f"(~${notional:,.0f} notional, {LEVERAGE:.0f}x, "
                  f"{ALLOC_FRAC * 100:.0f}% of ${sb['virtual_equity']:,.2f} "
                  f"paper ledger) @ ${dec['close']:.2f} — NO WRITES")
            return {"action": "would_enter", **dec, "shares": shares,
                    "notional_est": round(notional, 2)}
        print("  [SPX DRY] would_stay_flat — NO WRITES")
        return {"action": "would_stay_flat", **dec}

    # -- idempotency: this exact bar was already decided on ----------------
    if sb.get("last_bar_date") == dec["bar_date"]:
        print(f"  [SPX] {dec['bar_date']} already processed — no-op "
              f"(idempotent)")
        return {"action": "noop_already_processed", **dec}

    from step5_paper_trade import log_event, notify, save_state

    # -- holding: check the exit signal -------------------------------------
    if have_position:
        t = sb["open_trade"]
        if dec["exit_signal"]:
            reason = ("sma5_reclaim"
                      if (dec["sma5"] is not None
                          and dec["close"] > dec["sma5"])
                      else "rsi2_snapback")
            realized = _finish_exit(state, sb, t, dec["close"],
                                    dec["bar_date"], reason)
            return {"action": "exited", **dec, "pnl": realized}
        sb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print("  [SPX] holding — no exit signal yet")
        return {"action": "hold", **dec}

    # -- flat: check the entry signal ---------------------------------------
    if dec["entry_signal"]:
        shares = _size_shares(sb["virtual_equity"], dec["close"])
        notional = round(shares * dec["close"], 2)
        sb["open_trade"] = {
            "entry_date": dec["bar_date"],
            "entry_price": round(dec["close"], 4),
            "shares": round(shares, 4),
            "notional": notional,
            "entry_time": _now_str(),
            "rsi2_at_entry": dec["rsi2"],
        }
        sb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print(f"  [SPX] ENTER LONG {shares:.2f} sh SPY (~${notional:,.0f} "
              f"notional, {LEVERAGE:.0f}x, {ALLOC_FRAC * 100:.0f}% of "
              f"${sb['virtual_equity']:,.2f} paper ledger) @ "
              f"${dec['close']:.2f} | RSI2 {_fmt(dec['rsi2'])}")
        log_event({"action": "spx_book_enter", "bar_date": dec["bar_date"],
                   "entry_price": dec["close"], "shares": shares,
                   "rsi2": dec["rsi2"]})
        notify("📈 S&P dip-buy (paper)",
               f"the index panicked below its short-term range while the "
               f"long uptrend holds — bought SPY ${dec['close']:,.2f} on "
               f"the close. This one's simulated (no S&P venue yet) but "
               f"tracked for real.")
        return {"action": "entered", **dec, "shares": shares,
                "notional": notional}

    # -- flat, no signal — mark the bar done --------------------------------
    sb["last_bar_date"] = dec["bar_date"]
    save_state(state)
    print("  [SPX] flat, no signal — nothing to do")
    return {"action": "hold_flat", **dec}
