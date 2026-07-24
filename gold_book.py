"""
gold_book.py — THE GOLD BOOK: REAL BloFin DEMO orders on gold, running a
donchian(ENTRY_N) breakout entry with a STRUCTURE-TRAILING exit
(round-59 sealed-validated — see ROUND 59 EXIT SWAP below; this replaced
round 48's original donchian/EMA20 trend edge, which is now historical
background only, kept in the sections below for the full history).

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

THE VALIDATED RULE, ENTRY (deployed verbatim in spirit; see ROUND 59 EXIT
SWAP below for why the entry is now computed as a plain per-bar check
instead of importing step48_tradfi_trend.donchian_ema_exit's combined
state machine): daily bars. ENTER LONG when the daily close breaks above
the highest HIGH of the prior ENTRY_N daily bars (Donchian breakout,
shift(1)-disciplined so the breakout bar is never inside the window it's
breaking out of). Long-only, one position at a time.

ROUND 59 EXIT SWAP (this file, 2026-07-24): the EMA20-close exit above is
RETIRED. round-59's exit-science sealed test (step59_exit_science.py,
X3 STRUCTURE-TRAILING, twin-confirmed on GLD +$440.81/t +61.7% and
GC=F +$338.38/t +60.9% vs the EMA20 incumbent's +$56.44/t +14.7% / +$62.04
/t +18.0% — roughly 4x on BOTH sealed twins, identical donchian20 entries)
replaces it with STRUCTURE-TRAILING: a single protective floor, initialized
at entry to the most recently CONFIRMED daily swing low (k=K_SWING=5,
fractal-confirmed — a swing needs 5 closed bars after it before it counts,
no lookahead) below entry, that only ever ratchets UP as new confirmed
swing lows appear above it, never down. The position exits the instant
price trades at or below that floor — enforced by a REAL exchange-side
stop order (place_tpsl), cancelled and replaced at the new level every
time the floor ratchets, so protection lives on the exchange the whole
time, exactly like every other book in this repo (never a book-computed
close-based exit placing a market order after the fact). See
_compute_trail_floor()'s docstring for the exact ratchet/fallback rule,
and run_gold_book()'s "in a position" branch for the cancel/replace
mechanics. R59's own documented caveat applies here too: because a bar's
low is always <= its close, a close-below-floor break can never happen
without the intrabar low having already touched the floor first — so in
practice this exit fires via the exchange's intrabar stop, never via a
close confirmation, exactly as R59 observed in simulation.

ENTRY CONSEQUENCE OF THE SWAP: step48's donchian_ema_exit() bundles ENTRY
and EXIT into one hysteresis state machine ("in" from the breakout bar
until the EMA20 exit condition, remembered as internal state). Since the
real exit is no longer EMA20-based, that state machine's memory of
"still in signal" can desync from the real, exchange-fired exit (the
floor can trigger long before the EMA20 line would have crossed, leaving
the state machine still reporting "in" — which would cause an immediate,
spurious re-entry the next time the book finds itself flat, without a
fresh breakout). So entries are now a plain PER-BAR check — "did TODAY's
close break the prior ENTRY_N-day high" — with no memory at all. This is
not a separate design change; it is a forced, direct consequence of
retiring the EMA20 exit, and it is in fact the MORE faithful match to
step59's own entry definition (build_donchian_entries: "fires on every
qualifying bar; the single-slot book does the rest").

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
-8% hard stop bounds the loss on every trade. Pre-round-59, THIS book's only
downside stop was the crash-insurance SL 18% away, with the real exit a
trend LINE (EMA20), not a fixed distance — a loose geometry that argued for
a low leverage number. ROUND 59 NOTE: the exit is now a much tighter,
ratcheting structure floor (see ROUND 59 EXIT SWAP above), which is a
strictly BETTER-bounded geometry than what set this number originally — but
re-deriving leverage/allocation against the new geometry is a separate
decision this round does not make. GOLD_ALLOC and GOLD_LEV are left
UNCHANGED here (leverage 2x, allocation 25% of the shared ledger, i.e.
~0.5x equity notional) — a deliberate scope boundary, not an oversight.

PROTECTION: no take-profit — round 11 (see step5_paper_trade.py's SL_PCT
comment) measured that a TP amputates exactly the big winners a trend
system lives on, so the winners run, always. Pre-round-59: a WIDE
crash-insurance stop-loss was placed via place_tpsl at entry*(1 - 0.18) —
18% below entry — pure disaster insurance for a flash crash between daily
decisions, and the EMA20 close-below exit was executed by THIS BOOK
ITSELF, on daily closes, via a reduce-only market order. ROUND 59: that
book-driven EMA20 exit is GONE. The ONLY protective mechanism now is the
structure-trailing floor's exchange-side stop order (place_tpsl), which
STARTS at the 18% crash-SL distance whenever no confirmed swing low exists
yet to anchor it (entry day, or very young data) and ratchets tighter from
there as swings confirm — so the crash SL is still exactly what its name
says, the entry-day fallback / outer disaster insurance, just expressed as
the floor's own starting value instead of a second, separate bracket order.
See _compute_trail_floor()'s docstring for the precise rule.

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
gone, the structure-trailing floor's exchange-side stop must have fired
(ROUND 59: this is now the ONLY way a real exit ever happens — see ROUND 59
EXIT SWAP above): book the exit from the most recent fill and notify. If
the exchange shows an unexplained position while the book's own record is
flat, this book does NOT auto-adopt it (unlike shorts_lab) — it logs and
notifies loudly and skips trading that cycle, because nothing else should
ever be touching this symbol and a mismatch here is more likely a bug than
routine drift.

HUD: SKIPPED on purpose (future work). live_read.py's position card prices
everything off the BTC-USDT live feed; showing an XAUT-USDT position there
with BTC prices would just be wrong. Wiring gold into the HUD needs its own
price feed plumbing in live_read.py, not attempted here. ROUND 59: the
decision dict returned by _decision()/run_gold_book() now carries
"trail_floor" (None while flat) precisely so a future HUD hookup can show
"trailing floor $X" without any further plumbing on this file's side.

DRY MODE: run_gold_book(private, live_feed, state, dry=True) computes and
prints the full decision (latest bar, ENTRY_N-day high, the current
trailing floor when holding, breakout/hold/flat, would-enter/hold + sizing)
with NO orders placed and NO state writes, NO notify, NO log_event. It DOES
make read-only calls (candles, instrument spec, current net position) so
the printed decision reflects the real account — reads are never a
live-order risk. Used by step51_gold_smoke.py.
"""

from __future__ import annotations

import time

import numpy as np
import pandas as pd

SYMBOL = "XAUT-USDT"          # see module docstring: the demo-tradeable
                               # gold proxy — NOT XAU-USDT (unlisted on demo)
# 2026-07-24: 55 -> 20 after Wallace's dormancy audit. donchian55 needed a
# +17.7% rally to fire (median ~113 days away); donchian20 is the SAME shape,
# was a round-48 two-window survivor on BOTH GLD and GC=F, and PASSED ITS OWN
# SEALED TESTS on both (GLD +$156.63/t, +40.7%, DD -13.9%, 4.4y; GC=F
# +$83.72/t, +24.3%, 5.2y). ~5.4 trades/yr vs 3.0, and fires on a +3.3% move
# instead of a +17.7% one. Faster trigger, same discipline, sealed-validated.
ENTRY_N = 20                  # donchian breakout lookback, in daily bars

# INTRADAY TOUCH ENTRY (2026-07-24): validated Turtle-style — enter the
# MOMENT price touches the prior 20-day high instead of waiting for the
# daily close. Sealed-PASSED on both instruments (GLD +$127.65/t +38.3%
# DD-15.9% 4.4y; GC=F +$68.99/t +23.9% 5.2y). The daemon's fast loop calls
# intraday_check() every ~15s; the daily cycle still owns exits and level
# refresh. No resting orders ever — the trigger lives in code, the entry
# is an instant market order.
EMA_N = 20                    # legacy: the retired EMA20 exit's span. Kept
                               # only for historical reference — no exit
                               # logic reads this anymore (ROUND 59 EXIT
                               # SWAP, see module docstring).
CANDLE_BARS = 400             # requested history depth (warmup margin).
                               # ROUND 59 NOTE: this window must also reach
                               # back far enough to still contain a trade's
                               # own entry bar (plus K_SWING more, for the
                               # entry-anchor pivot search) for as long as
                               # that trade stays open — ~400 daily bars is
                               # well over a year of margin, comfortably
                               # more than this edge's realistic hold
                               # lengths, but it is a real bound, stated
                               # here rather than silently assumed.

GOLD_ALLOC = 0.25             # 25% of the SHARED ledger, state["virtual_equity"]
GOLD_LEV = 2.0                # see LEVERAGE & SIZING in the module docstring
CRASH_SL_PCT = 0.18           # 18% crash-insurance SL — ROUND 59: now also
                               # the structure-trailing floor's entry-day
                               # fallback distance, see PROTECTION above
ENTRY_FEE_BPS = 6.0           # BloFin taker fee — every order here is a
EXIT_FEE_BPS = 6.0            # plain market order, always taker-side

K_SWING = 5                   # confirmed-swing-low pivot lag — mirrors
                               # step59_exit_science.K_SWING EXACTLY (R59
                               # sealed-validated STRUCTURE-TRAILING exit,
                               # X3). A bar j is a CONFIRMED swing low once
                               # k=5 further bars have closed after it AND
                               # its low was the minimum of the closed
                               # [j-5, j+5] window — no lookahead, only the
                               # LOW side (this book is long-only).

_spec_cache: dict = {}


def _find_swing_lows(low: np.ndarray, k: int = K_SWING):
    """Fractal swing-low pivots — ported verbatim (low side only; GOLD is
    long-only, so only the protective/floor side of step59_exit_science's
    find_pivots() applies) from that function's exact rule: bar j is a
    CONFIRMED swing low iff low[j] is the min of the closed window
    [j-k, j+k]; confirmed only k bars later (confirm_idx = j+k), so nothing
    here is knowable before its own confirm bar has actually closed — no
    lookahead, identical to the sealed-validated sim. Returns two parallel
    numpy arrays (confirm_idx, price), already sorted by confirm_idx (which
    is monotonic in j)."""
    n = len(low)
    confirm_idx, price = [], []
    for j in range(k, n - k):
        window = low[j - k:j + k + 1]
        if low[j] <= window.min():
            confirm_idx.append(j + k)
            price.append(low[j])
    return np.array(confirm_idx, dtype=int), np.array(price, dtype=float)


def _entry_date_of(t: dict) -> str:
    """The trade record's entry day, as a 'YYYY-MM-DD' string. Daily-
    breakout entries always set "entry_date" directly (see run_gold_book's
    entry branch). intraday_check()'s touch-entry does NOT — its record is
    intentionally minimal (see that function's docstring) — so this falls
    back to the date component of "entry_time" (now_utc()'s own
    'YYYY-MM-DD HH:MM:SS UTC' format, sliceable at [:10]). Needed anywhere
    a trade's entry day matters (the floor's initial-anchor date, and the
    booked ledger line's own entry_date field) so BOTH entry paths' trades
    can be floor-managed and closed out identically from the very next
    daily cycle onward — this is the "intraday_check's bracket now uses the
    same floor logic after the first daily cycle" plumbing the round-59
    deployment needs."""
    ed = t.get("entry_date")
    if ed:
        return ed
    et = t.get("entry_time", "") or ""
    return et[:10] if len(et) >= 10 else str(pd.Timestamp.utcnow().date())


def _compute_trail_floor(d: pd.DataFrame, entry_date: str,
                         entry_price: float) -> float:
    """STRUCTURE-TRAILING floor — mirrors step59_exit_science's X3 exit
    EXACTLY (R59, twin-sealed-validated on identical donchian20 entries:
    GLD +$440.81/t +61.7% and GC=F +$338.38/t +60.9%, ~4x the EMA20
    incumbent's +$56.44/t +14.7% / +$62.04/t +18.0% on BOTH sealed twins):
    a single ratcheting protective floor, initialized at entry to the most
    recently CONFIRMED daily swing low (k=K_SWING=5, fractal-confirmed, no
    lookahead) BELOW entry, that only ever moves UP as new confirmed swing
    lows appear above it — never down. Long-only (this book never shorts),
    so only low-side pivots matter; find_pivots' high-side logic is not
    ported at all.

    Recomputed FRESH from the daily series every cycle — no incremental
    ratchet state to drift — a pure function of (entry_date, entry_price,
    today's closed daily bars), exactly like this module's own
    _decision(). This is order-independent: ratcheting is a monotonic max,
    so scanning every post-entry confirmed low in one pass gives the exact
    same final floor step59_exit_science's own per-bar ratchet loop would
    (that loop is itself just a running max).

    CRASH-SL FALLBACK (entry-day semantics, restated in the module
    docstring too): if no confirmed protective swing low exists yet as of
    entry (young data, or entry itself sits at a fresh low with nothing
    below it), the floor starts CRASH_SL_PCT (18%) below entry — this
    book's own disaster-insurance distance standing in for step59's
    generic ATR-based fallback (which has no analogue here; GOLD's real
    protective concept IS the crash SL). Because the floor only ever
    ratchets UP from there, the 18% distance is never exceeded once a
    confirmed swing takes over — a floor under the floor, exactly the
    "outer disaster insurance" role.

    `d` is the FULL daily series pulled this cycle (see _load_daily); dates
    (not raw array positions) anchor the entry/ratchet comparison so this
    is correct regardless of where the entry bar currently sits inside a
    rolling CANDLE_BARS window."""
    low = d["low"].to_numpy()
    confirm_idx, price = _find_swing_lows(low, K_SWING)
    all_dates = pd.DatetimeIndex(d["timestamp"]).date
    piv_dates = all_dates[confirm_idx]

    entry_date_obj = pd.Timestamp(entry_date).date()

    # initial anchor: most recent confirmed-by-entry swing low BELOW entry
    # (step59's most_recent_protective_pivot, ported verbatim: search
    # backward in time, return the FIRST — i.e. most recent — match)
    init = None
    for pdate, pr in zip(piv_dates[::-1], price[::-1]):
        if pdate <= entry_date_obj and pr < entry_price:
            init = float(pr)
            break
    floor_px = init if init is not None else entry_price * (1 - CRASH_SL_PCT)

    # ratchet: every confirmed swing low AFTER entry that beats the
    # current floor moves it up — never down. No price-vs-floor acceptance
    # filter here either, matching step59's own unconditional ratchet.
    for pdate, pr in zip(piv_dates, price):
        if pdate > entry_date_obj and pr > floor_px:
            floor_px = float(pr)

    return floor_px


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
    """Pure: reads the latest bar's breakout state off the FULL series `d`.
    ROUND 59: this is now a plain PER-BAR donchian breakout check — "did
    TODAY's close break the prior ENTRY_N-day high" — NOT step48's
    donchian_ema_exit() hysteresis state machine (which bundled its own
    EMA20-based exit memory into the same signal). See the module
    docstring's ROUND 59 EXIT SWAP / ENTRY CONSEQUENCE sections for why
    that memory had to go: this book's real exit is no longer EMA20, so a
    signal that "remembers" being in from an old breakout until an EMA20
    cross would desync from the real, exchange-fired floor exit. "ema20"
    is still computed and returned purely for informational trend context
    in logs/smoke — nothing here reads it to make a decision.
    No state mutation, so dry mode and the live path can never drift
    apart — they call this exact same function."""
    i = len(d) - 1
    hi = d["high"].rolling(ENTRY_N).max().shift(1)
    ema20 = d["close"].ewm(span=EMA_N, adjust=False).mean()
    hi_v = hi.iloc[i]
    close = float(d["close"].iloc[i])
    breakout_today = bool(hi_v == hi_v and close > hi_v)   # NaN-safe (hi_v==hi_v is False for NaN)
    return {
        "bar_date": str(pd.Timestamp(d["timestamp"].iloc[i]).date()),
        "close": close,
        "hi55": float(hi_v) if pd.notna(hi_v) else None,   # key name kept
                               # for backward compat (pre-existing naming
                               # debt: it has meant the ENTRY_N=20 high
                               # since the 55->20 dormancy-audit rewire,
                               # not touched here)
        "ema20": float(ema20.iloc[i]),   # informational only, see docstring
        "desired_in": breakout_today,
    }


def _fmt(v):
    return f"{v:.2f}" if v is not None else "n/a"


def _round_lot(raw: float, lot: float, minimum: float) -> float:
    n = round(raw / lot) * lot if lot else raw
    return max(minimum, n)


def _finish_exit(state, gb, t, exit_price, reason, bar_date) -> float:
    """ROUND 59: the ONLY exit path now (every real exit is the structure-
    trailing floor's exchange-side stop firing, detected via reconciliation
    — see run_gold_book's "book says open, exchange shows it gone" branch).
    Books the round trip on the book's own ledger line. Long-only PnL:
    profit when price RISES (exit - entry). Uses _entry_date_of(t) rather
    than t["entry_date"] directly so intraday_check()'s minimal trade
    record (no "entry_date" key — see that function's docstring) can be
    closed out exactly like a daily-breakout entry's."""
    from step5_paper_trade import log_event, notify, save_state

    contract_value = t.get("contract_value", 0.001)
    size_units = t["contracts"] * contract_value
    gross = size_units * (exit_price - t["entry_price"])
    fees = (t["entry_price"] * t.get("entry_fee_bps", ENTRY_FEE_BPS)
            + exit_price * EXIT_FEE_BPS) * size_units / 10_000
    realized = round(gross - fees, 2)

    rec = {"entry_date": _entry_date_of(t), "entry_price": t["entry_price"],
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
    dry=True. Returns a small summary dict, mainly for tests/smoke.

    ROUND 59: the exit is STRUCTURE-TRAILING, not EMA20 (see module
    docstring's ROUND 59 EXIT SWAP section). There is no more "signal says
    exit" branch — while holding, every cycle (a) recomputes the current
    trailing floor fresh off the daily series (_compute_trail_floor), and
    (b) if it ratcheted up since the last time this book set it, cancels
    the old exchange-side stop and places a new one at the new floor. The
    ACTUAL exit always happens on the exchange (a real stop order firing
    intrabar); this book only ever finds out about it afterward, via the
    "book says open, exchange shows it gone" reconciliation branch below —
    exactly the same branch that already handled a crash-SL firing
    pre-round-59, now generalized to the one and only exit mechanism."""
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
        return {"action": "skip_unreadable", **dec, "trail_floor": None}

    # -- current structure-trailing floor, if we're holding -----------------
    trail_floor = None
    if have_position:
        t0 = gb["open_trade"]
        trail_floor = _compute_trail_floor(d, _entry_date_of(t0),
                                           t0["entry_price"])
    dec["trail_floor"] = trail_floor

    floor_str = f"${trail_floor:,.2f}" if trail_floor is not None else "n/a"
    mid_field = (f"trailing floor {floor_str}" if have_position
                else f"breakout={'YES' if dec['desired_in'] else 'no'}")
    print(f"  [GOLD{tag}] {dec['bar_date']} close ${dec['close']:.2f} | "
          f"{ENTRY_N}d-high {_fmt(dec['hi55'])} | {mid_field} | "
          f"book={'OPEN' if have_position else 'FLAT'} | "
          f"exchange net {net:+.1f} ct")

    # -- reconcile: book says open, exchange shows it materially gone ------
    # ROUND 59: this is the ONLY way a real exit is ever discovered — the
    # structure-trailing floor's exchange-side stop fired (whether that
    # floor was still at its entry-day crash-SL fallback or had already
    # ratcheted up on confirmed swings — same mechanism, same branch).
    if have_position and abs(net) < gb["open_trade"]["contracts"] / 2:
        t = gb["open_trade"]
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        last_set_sl = _fmt(t.get("sl_price"))
        print(f"  [GOLD{tag}] our long is GONE on the exchange (net "
              f"{net:+.1f} vs recorded {t['contracts']:.0f} ct) -> "
              f"protective trailing floor fired (last set at ${last_set_sl})")
        if dry:
            print("  [GOLD DRY] would book this floor-fired exit — no "
                  "state changes made")
            return {"action": "would_reconcile_floor_exit",
                    "exit_price": exit_price, **dec}
        realized = _finish_exit(state, gb, t, exit_price, "floor_fired",
                                dec["bar_date"])
        return {"action": "reconciled_floor_exit", **dec, "pnl": realized}

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
            floor_est = _compute_trail_floor(d, dec["bar_date"], ref_price)
            est_notional = contracts * spec["contract_value"] * ref_price
            print(f"  [GOLD DRY] WOULD ENTER LONG {contracts:.0f} ct "
                  f"(~${est_notional:,.0f} notional, {GOLD_LEV:.0f}x, "
                  f"{GOLD_ALLOC*100:.0f}% of "
                  f"${state.get('virtual_equity', 0):,.2f} ledger) @ "
                  f"~${ref_price:,.2f} | broke {ENTRY_N}d-high "
                  f"${_fmt(dec['hi55'])} | initial trailing floor "
                  f"~${floor_est:,.2f} (no TP) — NO ORDER PLACED")
            return {"action": "would_enter", **dec, "contracts": contracts,
                    "ref_price": ref_price, "trail_floor": floor_est,
                    "notional_est": round(est_notional, 2)}
        if have_position:
            t = gb["open_trade"]
            old_floor = t.get("trail_floor")
            moved = old_floor is None or (trail_floor is not None
                                          and trail_floor > old_floor + 1e-9)
            verb = "WOULD RATCHET to" if moved else "stays at"
            print(f"  [GOLD DRY] HOLDING {t['contracts']:.0f} ct — "
                  f"trailing floor {verb} {floor_str} — NO ORDER PLACED")
            return {"action": "would_hold", **dec,
                    "contracts": t["contracts"]}
        print("  [GOLD DRY] would_stay_flat — NO ORDER PLACED")
        return {"action": "would_stay_flat", **dec}

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

        # STRUCTURE-TRAILING floor, anchored at the ACTUAL fill price (see
        # _compute_trail_floor's docstring) — this IS the crash-SL fallback
        # distance whenever no confirmed protective swing low exists yet.
        init_floor = _compute_trail_floor(d, dec["bar_date"], entry_price)
        sl_price = round(init_floor, 1)
        tpsl_id = None
        try:
            tpsl_id = private.place_tpsl(SYMBOL, "sell", contracts, None,
                                         sl_price)
        except Exception as e:
            print(f"  [GOLD] protective floor FAILED to place: "
                  f"{str(e)[:80]}")
            notify("⚠️ gold position UNPROTECTED (demo)",
                   f"{SYMBOL} long opened but the protective floor stop "
                   f"failed to place — check BloFin now")

        gb["open_trade"] = {
            "entry_date": dec["bar_date"],
            "entry_price": round(entry_price, 4),
            "contracts": contracts,
            "contract_value": spec["contract_value"],
            "notional": round(contracts * spec["contract_value"] * entry_price, 2),
            "sl_price": sl_price,
            "trail_floor": init_floor,
            "tpsl_id": tpsl_id,
            "order_id": order_id,
            "reason": f"donchian{ENTRY_N}_breakout",
            "hi55_at_entry": dec["hi55"],
            "entry_fee_bps": ENTRY_FEE_BPS,
            "entry_time": now_utc(),
        }
        gb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        print(f"  [GOLD] LONG @ ${entry_price:.2f} | {contracts:.0f} ct "
              f"(~${gb['open_trade']['notional']:,.0f}) | broke above "
              f"{ENTRY_N}d high ${_fmt(dec['hi55'])} | trailing floor "
              f"${sl_price:,.2f}")
        log_event({"action": "gold_enter", "bar_date": dec["bar_date"],
                   "entry_price": round(entry_price, 4),
                   "contracts": contracts, "hi55": dec["hi55"],
                   "sl_price": sl_price, "trail_floor": init_floor,
                   "order_id": order_id})
        notify("🥇 GOLD LONG on your BloFin (demo)",
               f"{SYMBOL} @ ${entry_price:,.2f} — broke the {ENTRY_N}-day "
               f"high ${_fmt(dec['hi55'])}. {contracts:.0f} ct, "
               f"{GOLD_LEV:.0f}x, trailing floor ${sl_price:,.2f} "
               f"(structure-trailing exit — rides until the chart says "
               f"stop).")
        return {"action": "entered", **dec, "entry_price": entry_price,
                "contracts": contracts, "sl_price": sl_price,
                "trail_floor": init_floor}

    # -- in a position: ratchet the structure-trailing floor's bracket -----
    if have_position:
        t = gb["open_trade"]
        old_floor = t.get("trail_floor")
        new_floor = trail_floor
        if old_floor is None or new_floor > old_floor + 1e-9:
            new_sl = round(new_floor, 1)
            # place the NEW bracket BEFORE cancelling the old one: if the
            # new placement fails, the OLD (looser but still valid) stop
            # keeps resting and the position is never left unprotected.
            # The reverse order (cancel-then-place) has a real window with
            # no bracket at all if the place call fails partway through.
            try:
                new_tpsl_id = private.place_tpsl(SYMBOL, "sell",
                                                 t["contracts"], None, new_sl)
            except Exception as e:
                print(f"  [GOLD] trailing floor ratchet FAILED to place "
                      f"the new bracket ({str(e)[:80]}) — the prior stop "
                      f"(${_fmt(t.get('sl_price'))}) is still resting, "
                      f"will retry next cycle")
                notify("⚠️ gold trailing-stop update FAILED (demo)",
                       f"floor moved to ${new_sl:,.2f} but the new bracket "
                       f"failed to place: {str(e)[:80]} — the old stop is "
                       f"still protecting the position, check BloFin")
            else:
                try:
                    if t.get("tpsl_id"):
                        private.cancel_tpsl(SYMBOL, t["tpsl_id"])
                except Exception as e:
                    print(f"  [GOLD] old bracket cancel failed after the "
                          f"new one was placed ({str(e)[:80]}) — two "
                          f"resting stops for now, the tighter one wins, "
                          f"harmless")
                print(f"  [GOLD] trailing floor ratcheted "
                      f"{_fmt(old_floor)} -> ${new_sl:,.2f} — exchange "
                      f"bracket replaced")
                log_event({"action": "gold_floor_ratchet",
                           "old_floor": old_floor, "new_floor": new_sl})
                t["tpsl_id"] = new_tpsl_id
                t["sl_price"] = new_sl
            t["trail_floor"] = new_floor
        else:
            print(f"  [GOLD] holding — trailing floor unchanged at "
                  f"${_fmt(old_floor)}")
        gb["last_bar_date"] = dec["bar_date"]
        save_state(state)
        return {"action": "hold", **dec, "trail_floor": t.get("trail_floor")}

    # -- flat, no signal — mark the bar done --------------------------------
    gb["last_bar_date"] = dec["bar_date"]
    save_state(state)
    print("  [GOLD] flat, no signal — nothing to do")
    return {"action": "hold", **dec}


def compute_trigger_level(live_feed):
    """Today's intraday entry level = prior ENTRY_N-day high (shift 1 — the
    current, unfinished day never defines its own level)."""
    d = _load_daily(live_feed)
    if d is None or len(d) < ENTRY_N + 2:
        return None
    return float(d["high"].rolling(ENTRY_N).max().shift(1).iloc[-1])


def intraday_check(private, live_feed, state, price: float):
    """Sealed-validated Turtle-style entry (2026-07-24): fire the MOMENT a
    fresh XAUT tick touches the prior 20-day high (GLD +$127.65/t +38.3%,
    GC=F +$68.99/t +23.9% on their sealed windows). Called from the daemon
    fast loop; the daily cycle keeps owning exits and level refresh. No
    resting orders — the trigger lives in code, the entry is market.
    Returns True on entry so the caller can stop hot-polling.

    ROUND 59, UNCHANGED HERE ON PURPOSE: this function still opens with the
    CRASH_SL_PCT bracket below, exactly as before — daily swing pivots
    (K_SWING) are only defined on CLOSED DAILY bars, so there is no
    structure floor to compute mid-day. The open_trade record below stays
    intentionally minimal too (no "entry_date", no "trail_floor"). The very
    next daily cycle (run_gold_book's "in a position" branch) picks this
    trade up like any other: it derives the entry day via _entry_date_of()
    (falling back to entry_time's date, since entry_date is absent here),
    computes the real structure floor, and cancels/replaces this starter
    bracket with it. So the structure-trailing floor logic reaches every
    open trade within one daily cycle regardless of which path opened it —
    without this function needing to know anything about swings itself."""
    gb = _book(state)
    if gb.get("open_trade"):
        return False
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lvl = gb.get("intraday_level")
    if gb.get("intraday_level_date") != today or lvl is None:
        lvl = compute_trigger_level(live_feed)
        if lvl is None:
            return False
        gb["intraday_level"] = lvl
        gb["intraday_level_date"] = today
        from step5_paper_trade import save_state
        save_state(state)
        print(f"  [GOLD] intraday trigger armed at ${lvl:,.1f}")
    if price < lvl:
        return False
    # OWNERSHIP HANDSHAKE (2026-07-24): the learning engine may hold XAUT
    # reps (atomic orders fixed the old jam). If an unowned position exists,
    # stand down this cycle — the breakout persists; we enter when clear.
    try:
        _net_now = private.net_position_contracts(SYMBOL)
        if abs(_net_now) >= 1:
            print(f"  [GOLD] breakout touched but another book holds "
                  f"{_net_now:+.0f}ct XAUT — standing down this cycle")
            return False
    except Exception:
        pass
    # TOUCHED — enter now, matching the validated sim (fill ~= the level)
    from step5_paper_trade import notify, log_event, now_utc, save_state
    spec = _instrument_spec(live_feed)
    equity = float(state.get("virtual_equity", 0) or 0)
    notional = equity * GOLD_ALLOC * GOLD_LEV
    contracts = _round_lot(notional / price / spec["contract_value"],
                           spec["lot_size"], spec["min_size"])
    private.ensure_leverage(SYMBOL, int(GOLD_LEV), "cross")
    remaining = contracts
    while remaining > spec["lot_size"] / 2:
        step = min(50.0, remaining)
        # THIN-BOOK PROTECTION (2026-07-24): XAUT's demo book is thin — the
        # Learning Engine's first live day proved a market clip can be
        # REJECTED MID-SEQUENCE (30ct filled, rest refused, exception thrown).
        # If a clip fails here, we must NOT let the exception escape: that
        # would leave the partial fill unbooked AND unbracketed, and the next
        # 15s fast-watch call (open_trade still None, price still >= level)
        # would enter AGAIN on top of it. Instead: stop clipping, fall
        # through, and BOOK + BRACKET whatever actually filled — a smaller
        # position with a stop beats a bigger one that's naked.
        try:
            private.market_order(SYMBOL, "buy", step)
        except Exception as e:
            print(f"  [GOLD] clip rejected mid-entry ({str(e)[:60]}) — "
                  f"booking what filled")
            break
        remaining = round(remaining - step, 2)
    import time as _t; _t.sleep(1.5)
    net = private.net_position_contracts(SYMBOL)
    if abs(net) < spec["min_size"]:
        print("  [GOLD] touch entry produced no position — aborting book")
        return False
    sl = round(price * (1 - CRASH_SL_PCT), 1)
    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(SYMBOL, "sell", abs(net), None, sl)
    except Exception as e:
        print(f"  [GOLD] SL FAILED: {str(e)[:80]}")
        notify("⚠️ gold SL failed (demo)", "position unprotected — check BloFin")
    gb["open_trade"] = {
        "direction": 1, "contracts": abs(net), "entry_price": price,
        "entry_fee_bps": 6.0, "entry_time": now_utc(), "tp_price": None,
        "sl_price": sl, "tpsl_id": tpsl_id, "trigger": "gold_breakout_touch",
    }
    save_state(state)
    log_event({"action": "gold_enter", "fill_price": price,
               "contracts": abs(net), "sl": sl, "note": "intraday touch"})
    notify("🥇 GOLD LONG on your BloFin (demo)",
           f"Gold touched its 20-day breakout ${lvl:,.0f} — LONG "
           f"{abs(net):.0f} ct XAUT @ ${price:,.1f}. Crash stop ${sl:,.0f}. "
           f"Rides until the trend breaks.")
    return True
