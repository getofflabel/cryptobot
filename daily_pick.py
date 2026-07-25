"""
daily_pick.py — THE LEARNING ENGINE: owner mandate, verbatim spirit
(Wallace, 2026-07-24 ~01:45am): "I'd rather you take 10-20 trades tomorrow
and have most of them lose than take one trade or none. You can't learn
from one trade a day. Take 10-20 small trades; 4/10 becomes 5/10 becomes
6/10 because you learn from previous mistakes." Demo account = sanctioned
tuition. This upgrades the old once-a-day/one-position design into a
high-cadence, multi-slot learning loop over the same BloFin universe —
crypto majors + a synthetic TradFi perp — WITHOUT changing the scorer,
the guards, or the universe-probe machinery that already earned its keep.

Structural template: shorts_lab.py / newsdesk.py (state dict, reconcile
against the exchange every cycle, hardened double-read _ensure_bracket,
_book_exit PnL math, entry via ensure_leverage + execute_market_clips +
ONE place_tpsl bracket, record_trade_outcome for auto-bench, dry mode).

DOES NOT TOUCH daemon.py / hourly.py / gold_book.py — another agent owns
those; this file is wired into the cycle separately. daemon.py already
calls run_daily_pick(...) on EVERY full_cycle (see `_run_book("Daily
Pick", _pick)`); ALL of the new cadence/concurrency logic below lives
inside this book, gated by its own idempotency key, exactly like
gold_book.py's last_bar_date and diver.py's last_bar_ts already do for
their own bar cadences. Calling this every cycle was always safe and stays
safe — it is a no-op except at an actual due slot.

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
memecoin, not an index tracker — excluded from this book's universe for
that reason, not availability. TSLA-USDT is a genuine platform quirk: its
DEMO candles endpoint returns rows, but its DEMO instrument-spec endpoint
404s (code 122003) and its DEMO ticker returns an empty array — i.e. it
LOOKS tradeable on one endpoint and isn't on the two that matter for
actually sizing and placing an order. Rather than hand-pick around quirks
like that forever, UNIVERSE below is deliberately just the plain list, and
_probe_universe() below is a STARTUP GUARD that empirically drops anything
that fails a real DEMO candle fetch — so a future UNIVERSE edit can never
crash this book; the symbol just gets logged and skipped, same failure
class as the instId errors above.

SCORING (per instrument, on its own 1h + 1d candles, both fetched from
live_feed — PROD, which has full history for everything in the named
universe even where demo does not): a LONG score and a SHORT score built
from named ± components (trend_1d, trend_1h, breakout, washout,
volume_shock, funding, momentum_4h — see score_instrument()), summed,
conviction = max(long, short) clipped to [5, 95], direction = argmax. ALL
components are recorded on every scored instrument for the log/notify —
the pick must always be explainable. Auto-bench (see THE LEARNING LOOP
below) can silence a component TYPE entirely: score_instrument() takes the
live `benched_triggers` list and a component whose "pick_<tag>" trigger is
benched simply stops contributing points or appearing in `components` —
the engine keeps scoring on whatever components are still healthy.

CADENCE (the core upgrade): a fresh pick decision is evaluated every
SLOT_INTERVAL_H (2) UTC hours, on even-hour boundaries (00:00, 02:00, ...,
22:00) — state["daily_pick"]["last_slot_ts"] is the idempotency key,
replacing the old last_pick_date. The daemon/hourly loop calls this book
roughly once an hour; `_slot_ts(now)` collapses "now" to its containing
even-hour window, and a slot is "due" exactly once, the first cycle that
runs at or after crossing into a new window — the direct 2h-cadence
generalization of the old once-daily PICK_HOUR_UTC gate.

CONCURRENCY: up to MAX_CONCURRENT (3) open picks at once, each on a
DIFFERENT symbol — state["daily_pick"]["open_trades"] is now a LIST
(replacing the single open_trade). Per due slot: reconcile/exit runs on
EVERY currently-open trade first (so a trade that times out this exact
cycle frees its slot before the entry decision below even looks at
capacity — "so slots recycle", per the owner's tight-zone direction); THEN,
if capacity remains, score the universe, rank by conviction, and take the
best symbol that clears every guard: (a) not stale/fetch-failed (never
ranked at all), (b) BTC-USDT only: never picked while any BTC book holds a
position or newsdesk has an armed pending, never opposing the exchange's
existing BTC net (book_ledger.py's shared accounting, unchanged), (c) any
symbol: skip if the exchange already shows a position on it, OR if this
book's own open_trades list already holds it (the different-symbols rule,
checked before the guard even touches the network), (d) instrument spec
must fetch OK from the DEMO host. There is NO conviction-floor skip — the
owner's explicit order is "take the best available every slot" — but a
pick scoring under CONVICTION_FLOOR (40) fires at HALF risk, tagged
"low_conviction": true (the old "boredom_pick" renamed to match the new
per-slot semantics — there is no such thing as "boredom" when a slot
elapses every two hours). If every ranked candidate fails a guard, the
slot is logged as "slot passed — all guarded" and last_slot_ts is stamped
anyway — the only acceptable no-trade outcome; with a fresh slot arriving
every two hours there is no value in re-polling the SAME slot repeatedly.

TIGHT-ZONE GEOMETRY (owner's "in and out within the hour" direction): stop
= 1.0x ATR(14, 1h), capped at 1.0% (STOP_ATR_MULT / STOP_CAP_PCT); target
= 1.5x stop (TARGET_STOP_MULT); MAX HOLD 4 HOURS (MAX_HOLD_H), a reduce-
only time exit — short holds mean slots recycle fast, which is exactly
what "10-20 trades a day" needs mechanically. Expected realized cadence,
per the owner's own math, is roughly 8-14 trades/day (12 slots/day x up to
3 concurrent, gated by how many symbols/guards actually clear each slot).

SIZING (owner's call 2026-07-24: "bigger — these trades should matter"):
fixed-fractional RISK sizing, not allocation sizing — risk RISK_PCT (2.0%)
of virtual_equity at the stop, regardless of stop width:
    position_notional = RISK_PCT * equity / (stop_pct / 100)
    leverage           = min(MAX_LEV(20), spec_max_leverage, 85 / stop_pct)
A low_conviction pick risks HALF (LOW_CONV_RISK_MULT): 1.0% of equity.
WORST CASE, STATED PLAINLY: at up to 3 concurrent full-risk trades and the
owner's own cited cadence of ~14 trades in a day, the ledger's worst-case
one-day drawdown if EVERY single trade were a full loss is
    14 * 2.0% = 28% of virtual_equity in one day (bounded in practice by
    MAX_CONCURRENT=3 open at once + 4h recycling; realistic bad day ~12-20%).
    The owner accepted a bigger swing in exchange for trades that matter.
That is a real, accepted number, not a hidden one — the owner named this
exact scenario ("4/10 becomes 5/10 becomes 6/10") as the price of the
learning loop and OK'd it explicitly for the demo book. It is a ceiling,
not an expectation: real trades stop out at 1.0x ATR (a real, current
volatility read, not a fixed guess), the auto-bench below prunes bad setup
types out of the rotation as it goes, and every slot's guard walk still
refuses to double up on a symbol or fight another book's BTC position.

THE LEARNING LOOP (the point of it all): every exit fires
record_trade_outcome TWICE, exactly as before — once under "daily_pick"
(the book-wide auto-bench line) and once under "pick_<top_component>"
(e.g. "pick_breakout") — so the memory system learns per SETUP TYPE, not
just per book; a subtag with >=8 live trades and negative expectancy is
auto-benched (step5_paper_trade.record_trade_outcome, unchanged) and
score_instrument() then makes that component stop contributing points at
all — the engine keeps trading on whatever components are still healthy.
NEW: every exit also appends a state["daily_pick"]["daybook"] entry —
{date, symbol, dir, conviction, components, outcome_pnl, hold_min,
setup, low_conviction} — the plain trade-level ledger the daily recap
below reads. NEW: on the first due slot of each new UTC day (the date
rolling over relative to state["daily_pick"]["last_recap_date"]), this
book sends ONE plain-English Telegram recap of the PRIOR day's daybook
entries — trade count, win/loss, net PnL, best- and worst-performing setup
group — no book-name jargon, matching the owner's one-voice mandate.

RECONCILE/EXIT run every cycle on every open trade, not just at a due
slot: bracket-fired exits booked from the fill, the 4h hard time-exit, and
a hardened self-heal on the TP/SL bracket (shorts_lab.py's own double-read
pattern, copied verbatim) so an open pick is never left naked.

DRY MODE: run_daily_pick(..., dry=True) computes and prints the full
decision every cycle would make (reconcile every open trade, the guard
walk, sizing, the whole ranked scoreboard) but places NO orders and makes
NO state/log/notify side effects — including NOT stamping last_slot_ts or
last_recap_date, so a dry preview never consumes the real idempotency
keys. Used by step53_pick_smoke.py.
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from book_ledger import recorded_book_positions
from step5_paper_trade import (current_funding_bps, execute_market_clips,
                               log_event, notify, now_utc,
                               record_trade_outcome, save_state,
                               write_lesson)
from strategy import atr as _atr
from strategy import rsi as _rsi

# ---------------------------------------------------------------------------
# universe (see module docstring: small on purpose — a DEMO-host limitation)
# ---------------------------------------------------------------------------

# 2026-07-24: XAUT-USDT and TSLA-USDT REMOVED. XAUT is the Gold Book's
# exclusive turf — letting the Learning Engine also short it caused two live
# failures at once: (1) XAUT's demo book is THIN, so market clips got
# rejected mid-fill, leaving a naked unbracketed -30ct short that no book
# owned; (2) two books trading one symbol is exactly the tangle we banned for
# BTC. TSLA-USDT 404s on the demo /instruments probe (never tradeable here).
# 2026-07-24 (owner: "the gold vehicle should literally be XAUT-USDT — you
# can use BloFin demo"): XAUT RESTORED. The jam that benched it was the
# rate-limiter bug (73 rapid clips), root-caused and fixed with atomic
# one-shot orders, then proven with a clean 361ct fill. The gold-book
# collision is handled by mutual guards: this engine skips XAUT whenever
# ANY position exists on it (existing exchange-position guard), and
# gold_book stands down from entering when an unowned XAUT position exists
# (see its entry paths). TSLA stays out (demo spec-dead).
UNIVERSE = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XAUT-USDT"]

NICE_NAMES = {
    "BTC-USDT": "bitcoin", "ETH-USDT": "ether", "SOL-USDT": "solana",
    "XAUT-USDT": "gold", "TSLA-USDT": "Tesla",
}

# ---------------------------------------------------------------------------
# cadence / concurrency
# ---------------------------------------------------------------------------

SLOT_INTERVAL_H = 2        # a fresh pick decision every 2 UTC hours
MAX_CONCURRENT = 3         # up to 3 concurrent open picks, each a different symbol

# ---------------------------------------------------------------------------
# sizing / geometry (fixed-fractional RISK sizing — see module docstring's
# "SIZING FOR SURVIVABLE TUITION" for the worst-case math)
# ---------------------------------------------------------------------------

RISK_PCT = 0.02            # 2% of virtual_equity risked per trade, at the stop
                           # (owner's call 2026-07-24: ~4x the old tuition
                           # size so trades are meaningful, not $6 dust)
LOW_CONV_RISK_MULT = 0.5   # half risk on a low_conviction (sub-floor) pick
MAX_LEV = 20.0
STOP_ATR_MULT = 1.0        # stop = 1.0x ATR(14, 1h)
STOP_CAP_PCT = 1.0         # ... capped at 1.0%
STOP_FLOOR_PCT = 0.05      # numerical safety only (never a strategy choice) —
                           # keeps risk-sizing's division well-defined even on
                           # degenerate near-zero-ATR data
TARGET_STOP_MULT = 1.5     # target = 1.5x stop (tight-zone geometry)
MAX_HOLD_H = 4.0           # reduce-only time exit — short holds so slots recycle
CONVICTION_FLOOR = 40.0
STOPOUT_COOLDOWN_H = 6.0   # after a losing stop, don't re-take the same
                           # (symbol, direction) for this many hours unless
                           # conviction is genuinely higher (+5 or more) —
                           # the first rule the daybook EARNED (2026-07-24)
LOT_EPS = 1e-6             # "is there a position at all" threshold

# ---------------------------------------------------------------------------
# THE MISSED-TRADE LEDGER (owner, 2026-07-24: "I've seen a lot of trades
# that could've gone well, but you just were not in them") — every gate
# that skips a candidate logs a receipt with the SAME tight-zone geometry a
# real entry would have used, so the daily recap can replay what actually
# happened and settle "does this gate earn its keep" with a real number
# instead of a feeling. See select_pick(), score_passed_trades().
# ---------------------------------------------------------------------------
PASSED_LOG_CAP = 400        # rolling cap on state["daily_pick"]["passed_log"]
CF_TAKER_FEE_BPS = 6.0      # counterfactual fee assumption — taker BOTH legs
                           # (see score_passed_trades docstring: flattering,
                           # the conservative direction for judging a gate)
REASON_LABEL = {            # short tag -> plain-English phrase for the recap
    "guard": "position guard", "correlation": "correlation guard",
    "one_thesis": "one-thesis guard", "cooldown": "cooldown",
    "calm_gate": "calm gate",
}

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
    "trend_1d": "trend", "trend_1d_align": "trend", "trend_1h": "trend", "breakout": "breakout",
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
                     funding_bps: float | None,
                     benched: list[str] | None = None) -> dict:
    """Score ONE instrument on its own closed 1h + 1d candles. Returns
    {long_score, short_score, conviction, direction, components}.
    `components` records EVERY check that actually fired (either side),
    as {"name", "long", "short"} — the pick must always be explainable.

    `benched` is the live state["benched_triggers"] list (see THE LEARNING
    LOOP in the module docstring): if a component's own "pick_<tag>"
    trigger is in it, that component contributes NOTHING this call — no
    points, no components entry — exactly as if it never fired. Auto-bench
    silences one component TYPE; every other component keeps scoring."""
    benched_set = set(benched or [])
    long_pts, short_pts = 0.0, 0.0
    comps: list[dict] = []

    def add(name: str, long_add: float = 0.0, short_add: float = 0.0):
        nonlocal long_pts, short_pts
        tag = COMPONENT_TAG.get(name, name)
        if f"pick_{tag}" in benched_set:
            return          # this setup-type is auto-benched — stops firing
        long_pts += long_add
        short_pts += short_add
        comps.append({"name": name, "long": long_add, "short": short_add})

    # -- HORIZON COHERENCE (owner, 2026-07-24: "you justified a 4h scalp
    #    with the daily chart — your stop and target are scalp-sized, so the
    #    intraday tape should cast the deciding votes"): the DAILY trend no
    #    longer votes direction for this tight-zone book. It is computed
    #    (washout still uses it as context) and applied AFTER the intraday
    #    components pick a direction, as a small ALIGNMENT BONUS (+5) —
    #    never the reason for a trade, only a tailwind acknowledgment.
    trend_1d, _, _ = _trend_1d_state(c1d)

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
    # KNIFE-CATCH GUARD (owner, 2026-07-24: "the downtrend hasn't even
    # stopped and you went long" + R58's monotonic ladder finding that
    # dip-buys improve ~12x when they wait for a reversal bar): oversold
    # alone is NOT a buy — the last closed 1h bar must be a TURN CANDLE
    # (closed green above the prior close for longs; mirror for shorts)
    # before washout may vote. Oversold + the turn, never oversold raw.
    turn_up = turn_down = False
    if len(c1h) >= 3:
        last_o, last_c = float(c1h["open"].iloc[-1]), float(c1h["close"].iloc[-1])
        prev_c = float(c1h["close"].iloc[-2])
        turn_up = last_c > last_o and last_c > prev_c
        turn_down = last_c < last_o and last_c < prev_c
    if pd.notna(r3):
        if r3 < 10 and trend_1d == "up" and turn_up:
            w_long = 20.0
        if r3 > 90 and trend_1d == "down" and turn_down:
            w_short = 20.0
    # NO EYE GATE HERE — deliberately, and this comment exists so nobody
    # re-adds one without redoing the work. Round 83 found that skipping
    # washouts on a "messy" chart read beat a random-skip control at the
    # 98th percentile on BTC and ETH, and it was shipped live on 2026-07-24.
    # Round 88 attacked that result and it did not hold:
    #   - of 3 NEW assets, only XRP passed (92nd); SOL showed no information
    #     content (68th) and DOGE was worse than useless (36th). SOL is a
    #     symbol this very book trades, and XAUT was never testable at all.
    #   - across 122 cells, 28 cleared the 90th percentile (12 expected by
    #     chance) but 45 landed at or below the 10th (12 expected) — the eye
    #     is informative but DOUBLE-EDGED, and we cannot predict in advance
    #     which side of it a given symbol lands on.
    # Two cells out of 36 was always inside what luck produces. Washout
    # trades its own rule: oversold + daily trend + the turn candle.
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

    # daily-trend ALIGNMENT BONUS (see HORIZON COHERENCE above): +5 to the
    # side the intraday components already chose, only when the daily
    # agrees — a tailwind note, never a deciding vote.
    if long_pts > short_pts and trend_1d == "up":
        add("trend_1d_align", long_add=5.0)
    elif short_pts > long_pts and trend_1d == "down":
        add("trend_1d_align", short_add=5.0)
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
    return ", ".join(parts) if parts else "no components fired (low-conviction pick)"


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


def analyze_universe(live_feed, universe: list[str] = UNIVERSE,
                     benched: list[str] | None = None) -> list[dict]:
    """Score EVERY instrument in `universe` (candles from live_feed — PROD,
    full history regardless of demo availability). Returns one record per
    symbol, always — even a fetch failure or staleness produces a record
    (marked ok=False / stale=True) so the full scoreboard is always
    printable, per step53_pick_smoke.py's brief. `benched` is forwarded to
    score_instrument() unchanged — see its docstring."""
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
        sc = score_instrument(c1h, c1d, fb, benched)
        last_close = float(c1h["close"].iloc[-1])
        atr_series = _atr(c1h, 14)
        atr14 = float(atr_series.iloc[-1])
        atr_pct = (atr14 / last_close * 100) if last_close else 0.0
        # VOLATILITY REGIME (owner, 2026-07-24: "for a day like today to be
        # trading a 4h window, you're basically gambling — the tape isn't
        # moving"): current ATR% vs this instrument's OWN trailing-14d
        # median. calm = the expected move is too small for the tight-zone
        # geometry to beat noise+costs; select_pick refuses C-grade picks
        # in calm tape (A-setups only), keeps take-best in normal/violent.
        atr_pct_series = (atr_series / c1h["close"] * 100)
        med14 = float(atr_pct_series.iloc[-336:].median()) if len(c1h) >= 100 else None
        if med14 and med14 > 0:
            ratio = atr_pct / med14
            regime = "calm" if ratio < 0.8 else ("violent" if ratio > 1.5 else "normal")
        else:
            regime = "normal"
        rec["regime"] = regime
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
    """True if ANY BTC-USDT book (ride/tact/lab/apprentice/newsdesk/diver,
    via book_ledger.py's own shared accounting) currently holds a
    position, or newsdesk has an armed-but-not-yet-filled pending news
    trade. Guard (b): the daily pick never even considers BTC while the
    snipers own it."""
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
    # different-symbols rule: never stack a second slot on a symbol this
    # book already holds itself — checked before any network call.
    own_open_syms = {t["symbol"] for t
                     in state.get("daily_pick", {}).get("open_trades", [])}
    if sym in own_open_syms:
        return False, f"already held by this book's own open slots ({sym})"
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


# The crypto majors move together — betting LONG one while SHORT another is
# a near-self-cancelling position (Wallace, 2026-07-24: "you have Bitcoin
# long and Solana short, which is crazy — they're correlated"). The engine
# treats them as ONE correlated cluster: it will not open a position that
# opposes net exposure already on the book (from ANY book) in this cluster.
CORRELATED_CLUSTER = {"BTC-USDT", "ETH-USDT", "SOL-USDT"}


def _cluster_direction(private) -> int:
    """Net directional lean of the correlated crypto cluster across the whole
    account: +1 if net long, -1 if net short, 0 if flat/mixed-to-zero. Uses
    the exchange's own positions so it sees every book, not just our own."""
    lean = 0
    for s in CORRELATED_CLUSTER:
        try:
            net = private.net_position_contracts(s)
        except Exception:
            continue
        if net > 0:
            lean += 1
        elif net < 0:
            lean -= 1
    return (lean > 0) - (lean < 0)


def _log_passed_trade(state: dict, cand: dict, reason: str, slot_ts: str) -> None:
    """THE MISSED-TRADE LEDGER: record ONE skipped candidate with the exact
    stop/target geometry a real entry would have used (_stop_target_pct —
    same function _build_entry_plan calls), so score_passed_trades() can
    later replay this candidate against real candles and find out whether
    the gate that skipped it actually earned its keep. `reason` is one of
    the short tags in REASON_LABEL. Rolling cap PASSED_LOG_CAP, oldest
    dropped first — this is a receipt trail, not a full audit log."""
    dp = state.setdefault("daily_pick", _fresh_dp())
    stop_pct, target_pct = _stop_target_pct(cand.get("atr_pct_1h"))
    log = dp.setdefault("passed_log", [])
    log.append({
        "ts": slot_ts, "symbol": cand["symbol"], "direction": cand["direction"],
        "conviction": cand["conviction"], "reason": reason,
        "ref_price": cand["last_close"], "stop_pct": stop_pct,
        "target_pct": target_pct, "scored": False,
    })
    del log[:-PASSED_LOG_CAP]


def select_pick(analysis: list[dict], private, demo_feed, state: dict):
    """Rank by conviction, walk down applying every guard, return the
    BEST guard-clearing candidate — no conviction-floor skip (owner's
    order: take the best available every slot). Returns
    ((cand, spec) | None, is_low_conviction, skip_log).

    Every candidate a guard/gate skips is ALSO logged to the missed-trade
    ledger (_log_passed_trade) with the same geometry a real entry would
    have used — including the slot's best (highest-conviction) candidate
    when the whole slot ends up passing (every ranked candidate fails some
    guard): it is simply the first one this loop evaluates and logs, since
    `ranked` is sorted by descending conviction. Not-due/no-capacity cycles
    never reach select_pick at all, so those never get logged — correctly,
    since nothing was actually decided against."""
    ranked = sorted([a for a in analysis if a["ok"] and not a["stale"]],
                    key=lambda a: a["conviction"], reverse=True)
    from book_ledger import cluster_state
    cluster_dir, cluster_mixed = cluster_state(private)   # read once per slot
    slot_ts = _slot_ts(datetime.now(timezone.utc))
    guarded = []
    skips = []
    for cand in ranked:
        ok, info = _guard_check(cand, private, demo_feed, state)
        if not ok:
            skips.append((cand["symbol"], info))
            _log_passed_trade(state, cand, "guard", slot_ts)
            print(f"  [PICK] {cand['symbol']} (conv {cand['conviction']:.0f}) "
                  f"GUARD FAIL: {info}")
            continue
        # NO GAMBLING IN QUIET TAPE (owner, 2026-07-24): in a calm regime
        # the tight-zone geometry is a coin flip — only genuine A-setups
        # (conviction >= CONVICTION_FLOOR) may fire; C-grade reps wait for
        # a tape that actually moves.
        if cand.get("regime") == "calm" and cand["conviction"] < CONVICTION_FLOOR:
            msg = (f"calm tape (ATR below its own norm) — conviction "
                   f"{cand['conviction']:.0f} < {CONVICTION_FLOOR:.0f} floor, "
                   f"not gambling in a quiet market")
            skips.append((cand["symbol"], msg))
            _log_passed_trade(state, cand, "calm_gate", slot_ts)
            print(f"  [PICK] {cand['symbol']} CALM-REGIME SKIP: {msg}")
            continue
        # stop-out cooldown: don't re-take a setup that just stopped us out
        # unless the signal has ACTUALLY gotten stronger (see the daybook
        # stamp above for the lesson this rule was earned from)
        key = f"{cand['symbol']}:{cand['direction']}"
        stamp = state.get("daily_pick", {}).get("last_stopouts", {}).get(key)
        if stamp:
            try:
                age_h = (datetime.now(timezone.utc)
                         - datetime.fromisoformat(stamp["ts"])
                         ).total_seconds() / 3600
            except Exception:
                age_h = 999
            if (age_h < STOPOUT_COOLDOWN_H
                    and cand["conviction"] <= stamp["conviction"] + 5):
                msg = (f"stopped out of this exact setup {age_h:.1f}h ago at "
                       f"conv {stamp['conviction']:.0f} — signal no stronger, "
                       f"cooling down")
                skips.append((cand["symbol"], msg))
                _log_passed_trade(state, cand, "cooldown", slot_ts)
                print(f"  [PICK] {cand['symbol']} COOLDOWN SKIP: {msg}")
                continue
        # ONE-THESIS GUARD (2026-07-24 upgrade: a MIXED book — both
        # directions open across the majors — now blocks ALL new cluster
        # entries until coherence returns; the old rule treated "mixed" as
        # "no lean" and let a third contradictory position walk in)
        if cand["symbol"] in CORRELATED_CLUSTER and cluster_mixed:
            msg = "crypto book is MIXED (both directions open) — no new cluster risk until coherent"
            skips.append((cand["symbol"], msg))
            _log_passed_trade(state, cand, "one_thesis", slot_ts)
            print(f"  [PICK] {cand['symbol']} ONE-THESIS SKIP: {msg}")
            continue
        # clean lean: reject a cluster pick that fights it
        cand_dir = 1 if cand["direction"] == "long" else -1
        if (cand["symbol"] in CORRELATED_CLUSTER and cluster_dir != 0
                and cand_dir != cluster_dir):
            msg = (f"opposes correlated crypto exposure "
                   f"(cluster is {'long' if cluster_dir>0 else 'short'})")
            skips.append((cand["symbol"], msg))
            _log_passed_trade(state, cand, "correlation", slot_ts)
            print(f"  [PICK] {cand['symbol']} (conv {cand['conviction']:.0f}) "
                  f"CORRELATION SKIP: {msg}")
            continue
        guarded.append((cand, info))
    if not guarded:
        return None, False, skips
    best_cand, best_spec = guarded[0]     # guarded preserves the descending
                                          # conviction order of `ranked`
    low_conviction = best_cand["conviction"] < CONVICTION_FLOOR
    return (best_cand, best_spec), low_conviction, skips


# ===========================================================================
# sizing
# ===========================================================================

def _round_lot(raw: float, lot: float, minimum: float) -> float:
    n = round(raw / lot) * lot if lot else raw
    return max(minimum, n)


def _stop_target_pct(atr_pct_1h: float | None) -> tuple[float, float]:
    """TIGHT-ZONE GEOMETRY: stop = 1.0x ATR(14,1h), capped at 1.0%; target
    = 1.5x stop. STOP_FLOOR_PCT is a numerical safety net only (keeps the
    risk-sizing division below well-defined even on degenerate near-zero
    ATR data), not a strategy choice."""
    stop_pct = min(STOP_ATR_MULT * (atr_pct_1h or 0.0), STOP_CAP_PCT)
    stop_pct = max(stop_pct, STOP_FLOOR_PCT)
    target_pct = TARGET_STOP_MULT * stop_pct
    return stop_pct, target_pct


def _build_entry_plan(cand: dict, spec: dict, equity: float,
                      low_conviction: bool) -> dict:
    """Fixed-fractional RISK sizing (see module docstring's "SIZING FOR
    SURVIVABLE TUITION" for the worst-case math): notional is sized so
    that a full stop-out loses exactly RISK_PCT of equity (half that on a
    low_conviction pick), regardless of how tight or wide the stop is."""
    stop_pct, target_pct = _stop_target_pct(cand["atr_pct_1h"])
    lev = min(MAX_LEV, spec["max_leverage"], math.floor(85 / stop_pct))
    lev = max(1.0, lev)
    risk_pct = RISK_PCT * (LOW_CONV_RISK_MULT if low_conviction else 1.0)
    notional = risk_pct * equity / (stop_pct / 100)
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
            "risk_pct": risk_pct, "notional": notional, "contracts": contracts,
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
    return {"last_slot_ts": None, "open_trades": [],
            "conviction_ledger": _fresh_ledger(), "picks": [],
            "daybook": [], "last_recap_date": None,
            "passed_log": [], "gate_scoreboard": {}}


def _migrate_dp(dp: dict) -> None:
    """In-place migration from the old once-a-day/single-trade state shape
    to the new 2h-slot/concurrent shape, so a state file saved before this
    upgrade loads cleanly instead of crashing. Idempotent — a no-op once
    migrated. The old open_trade (if any) becomes the sole entry in the
    new open_trades list; the old last_pick_date has no clean mapping onto
    the new 2h slot grid, so it is simply dropped (worst case: one extra
    slot's evaluation runs sooner than the old daily cadence would have —
    harmless, and exactly what the upgrade wants anyway)."""
    if "open_trades" not in dp:
        legacy = dp.pop("open_trade", None)
        dp["open_trades"] = [legacy] if legacy else []
    dp.setdefault("open_trades", [])
    if "last_slot_ts" not in dp:
        dp.pop("last_pick_date", None)
        dp["last_slot_ts"] = None
    dp.setdefault("conviction_ledger", _fresh_ledger())
    dp.setdefault("picks", [])
    dp.setdefault("daybook", [])
    dp.setdefault("last_recap_date", None)
    dp.setdefault("passed_log", [])
    dp.setdefault("gate_scoreboard", {})


def _slot_ts(now: datetime) -> str:
    """The even-UTC-hour slot `now` falls in, as a stable idempotency-key
    string — e.g. 14:37 UTC -> '2026-07-24T14:00 UTC'. Slot boundaries are
    every SLOT_INTERVAL_H hours starting at UTC midnight (00, 02, 04, ...,
    22) — the direct 2h-cadence generalization of the old once-daily
    PICK_HOUR_UTC gate: a slot is "due" the first cycle that runs at or
    after crossing into a new window."""
    slot_hour = (now.hour // SLOT_INTERVAL_H) * SLOT_INTERVAL_H
    return f"{now:%Y-%m-%d}T{slot_hour:02d}:00 UTC"


# ===========================================================================
# THE MISSED-TRADE LEDGER — counterfactual scoring
# ===========================================================================

def _simulate_bracket(live_feed, entry: dict, entry_dt: datetime):
    """Replays the EXACT tight-zone bracket a real entry would have used
    (same sl_ref/tp_ref formulas as _build_entry_plan) against REAL 1h
    candles from `live_feed`, starting just after entry_dt and covering up
    to MAX_HOLD_H. Returns (outcome_pct, exit_kind):
      outcome_pct — the trade's % move in the risk-scaled sense (+stop_pct
                    on a stop, +target_pct on a target, or the actual %
                    move at the 4h close on a time exit) so the caller can
                    scale it by risk_pct/stop_pct exactly like a real
                    fixed-fractional fill.
      exit_kind   — "stop" | "target" | "time", for debugging/audit.
    Returns (None, None) if the candles needed to judge the window aren't
    available — the caller leaves the entry unscored and retries on a
    later day rather than guessing.

    STOP-FIRST-ON-TIE: if a single 1h bar's range would trip BOTH the stop
    and the target, this books the STOP — conservative, matching how a
    real bracket order behaves when both levels sit inside one bar's
    range (the stop is the safety net; it must win any ambiguity)."""
    symbol = entry["symbol"]
    direction = entry["direction"]
    ref_price = entry["ref_price"]
    stop_pct = entry["stop_pct"]
    target_pct = entry["target_pct"]
    if direction == "long":
        sl_ref = ref_price * (1 - stop_pct / 100)
        tp_ref = ref_price * (1 + target_pct / 100)
    else:
        sl_ref = ref_price * (1 + stop_pct / 100)
        tp_ref = ref_price * (1 - target_pct / 100)

    window_end = entry_dt + timedelta(hours=MAX_HOLD_H)
    try:
        end_ms = int((window_end + timedelta(hours=1)).timestamp() * 1000)
        candles = live_feed.get_candles(symbol, "1h", limit=12, end_ms=end_ms)
    except Exception:
        return None, None
    if candles is None or candles.empty:
        return None, None
    bars = candles[(candles["timestamp"] > entry_dt)
                   & (candles["timestamp"] <= window_end)]
    if bars.empty:
        return None, None

    last_close = ref_price
    for _, bar in bars.iterrows():
        last_close = float(bar["close"])
        hi, lo = float(bar["high"]), float(bar["low"])
        if direction == "long":
            stop_hit, target_hit = lo <= sl_ref, hi >= tp_ref
        else:
            stop_hit, target_hit = hi >= sl_ref, lo <= tp_ref
        if stop_hit:
            return -stop_pct, "stop"
        if target_hit:
            return target_pct, "target"

    # no bar in the window hit either level -> the same 4h reduce-only time
    # exit run_daily_pick's own reconcile loop would have applied to a real
    # trade, booked at the last closed bar's close inside the window.
    if direction == "long":
        time_pct = (last_close / ref_price - 1) * 100
    else:
        time_pct = (ref_price / last_close - 1) * 100
    return time_pct, "time"


def score_passed_trades(live_feed, state: dict) -> int:
    """Counterfactually scores every unscored state["daily_pick"]["passed_log"]
    entry older than MAX_HOLD_H: replays the tight-zone bracket against real
    candles (_simulate_bracket) and records `counterfactual_pnl` on the same
    risk basis a real trade would use. Marks each entry `scored` so it is
    NEVER re-fetched/re-simulated. Returns the count of entries scored this
    call. Run once per UTC day, inside the daily-recap path, before the
    recap message is composed (run_daily_pick), so the aggregates it
    updates — state["daily_pick"]["gate_scoreboard"][reason] = {passed_n,
    cf_pnl}, accumulating across days — are current when the recap reads
    them.

    HONESTY NOTES (read before trusting a number out of this):
    - Fees use CF_TAKER_FEE_BPS on BOTH legs (no maker/taker nuance — a real
      TP exit often fills maker at a lower fee than modeled here).
    - No slippage is modeled at all.
    - The trade is assumed to fill exactly at the logged ref_price (a real
      order can slip on entry too).
    All three assumptions flatter the missed trade relative to what a real
    fill would have looked like — that is the CONSERVATIVE direction for
    judging a gate: a gate has to beat even a flattered counterfactual to
    prove it's earning its keep, not just an average one.
    - EQUITY: risk_pct is computed the same way _build_entry_plan would
      (RISK_PCT, halved via LOW_CONV_RISK_MULT for a sub-CONVICTION_FLOOR
      pick), but scaled against state["virtual_equity"] AT SCORING TIME —
      not the equity that actually existed when the slot was passed, since
      a historical equity snapshot isn't logged per passed candidate. Fine
      for a "would this gate have helped or hurt" read; not a cent-accurate
      ledger entry."""
    dp = state.setdefault("daily_pick", _fresh_dp())
    passed_log = dp.get("passed_log", [])
    scoreboard = dp.setdefault("gate_scoreboard", {})
    equity = state.get("virtual_equity", 0.0)
    now = datetime.now(timezone.utc)
    fee_pct = CF_TAKER_FEE_BPS * 2 / 100     # both legs, in percent terms
    scored_n = 0
    for entry in passed_log:
        if entry.get("scored"):
            continue
        try:
            entry_dt = datetime.strptime(
                entry["ts"], "%Y-%m-%dT%H:%M UTC").replace(tzinfo=timezone.utc)
        except Exception:
            entry["scored"] = True   # unparsable timestamp -> never retry
            continue
        age_h = (now - entry_dt).total_seconds() / 3600
        if age_h < MAX_HOLD_H:
            continue                 # too soon to know the 4h outcome yet
        outcome_pct, exit_kind = _simulate_bracket(live_feed, entry, entry_dt)
        if outcome_pct is None:
            continue                 # candle data unavailable — retry later
        low_conv = entry["conviction"] < CONVICTION_FLOOR
        risk_pct = RISK_PCT * (LOW_CONV_RISK_MULT if low_conv else 1.0)
        net_pct = outcome_pct - fee_pct
        cf_pnl = round(risk_pct * equity * (net_pct / entry["stop_pct"]), 2)
        entry["scored"] = True
        entry["counterfactual_pnl"] = cf_pnl
        entry["exit_kind"] = exit_kind
        reason = entry.get("reason", "other")
        board = scoreboard.setdefault(reason, {"passed_n": 0, "cf_pnl": 0.0})
        board["passed_n"] += 1
        board["cf_pnl"] = round(board["cf_pnl"] + cf_pnl, 2)
        scored_n += 1
    return scored_n


# ===========================================================================
# daily recap (the learning loop's plain-English summary)
# ===========================================================================

def _yesterday_str(today_str: str) -> str:
    d = datetime.strptime(today_str, "%Y-%m-%d") - timedelta(days=1)
    return f"{d:%Y-%m-%d}"


def _missed_trade_lines(dp: dict, today_str: str) -> list[str]:
    """1-2 plain-English lines off YESTERDAY's SCORED passed_log entries —
    the missed-trade ledger's receipts. Only entries score_passed_trades()
    has already marked `scored` are counted (an entry logged late yesterday
    may still be < MAX_HOLD_H old and simply isn't judgeable yet; it picks
    up on a later day's recap once it is — this line can under-count on the
    very next day, which is the honest state of knowledge at that point,
    not a bug). Returns [] when there's nothing scored to report."""
    y = _yesterday_str(today_str)
    rows = [r for r in dp.get("passed_log", [])
           if r.get("scored") and r.get("ts", "")[:10] == y]
    if not rows:
        return []
    n = len(rows)
    saved = sum(-r["counterfactual_pnl"] for r in rows if r["counterfactual_pnl"] < 0)
    cost = sum(r["counterfactual_pnl"] for r in rows if r["counterfactual_pnl"] > 0)
    net = sum(r["counterfactual_pnl"] for r in rows)
    lines = [f"Passed {n} trade{'s' if n != 1 else ''} yesterday: gates saved "
            f"${saved:,.2f} / cost ${cost:,.2f} (net ${net:+,.2f})."]
    winners = [r for r in rows if r["counterfactual_pnl"] > 0]
    if winners:
        biggest = max(winners, key=lambda r: r["counterfactual_pnl"])
        label = REASON_LABEL.get(biggest["reason"], biggest["reason"])
        lines.append(f"Biggest miss: {biggest['symbol']} {biggest['direction']} "
                     f"({label}) would've made ${biggest['counterfactual_pnl']:,.2f}.")
    return lines


def _build_recap_message(dp: dict, state: dict, today_str: str) -> str:
    """Plain-English, ONE message, no book-name jargon (owner's one-voice
    mandate) — a trade count, win/loss, net PnL, and (when more than one
    setup group traded) the best- and worst-performing group from
    YESTERDAY's daybook entries, so Wallace sees the learning happening
    without reading a single log line. ALSO appends the missed-trade
    ledger's 1-2 lines (_missed_trade_lines) — what the gates that skipped
    trades yesterday actually cost or saved, the receipts behind every
    protective rule in select_pick()."""
    y = _yesterday_str(today_str)
    rows = [r for r in dp.get("daybook", []) if r.get("date") == y]
    missed = _missed_trade_lines(dp, today_str)

    if not rows:
        base = "Learning engine yesterday: no trades logged (quiet 24h)."
        return " ".join([base] + missed) if missed else base

    n = len(rows)
    wins = sum(1 for r in rows if r.get("outcome_pnl", 0.0) > 0)
    losses = n - wins
    net = sum(r.get("outcome_pnl", 0.0) for r in rows)
    headline = (f"Learning engine yesterday: {n} trade{'s' if n != 1 else ''}, "
               f"{wins}W/{losses}L, net ${net:+,.2f}.")

    groups: dict[str, dict] = {}
    for r in rows:
        key = "low-conviction" if r.get("low_conviction") else (r.get("setup") or "other")
        g = groups.setdefault(key, {"n": 0, "wins": 0})
        g["n"] += 1
        g["wins"] += 1 if r.get("outcome_pnl", 0.0) > 0 else 0
    if len(groups) <= 1:
        base = headline
    else:
        ranked_groups = sorted(groups.items(),
                               key=lambda kv: kv[1]["wins"] / kv[1]["n"], reverse=True)
        best_key, best = ranked_groups[0]
        worst_key, worst = ranked_groups[-1]
        benched = state.get("benched_triggers", [])
        worst_tag = f"pick_{worst_key}" if worst_key != "low-conviction" else None
        worst_note = " (benched)" if worst_tag and worst_tag in benched else ""
        base = (f"{headline} Best: {best_key} picks {best['wins']}/{best['n']}. "
               f"Worst: {worst_key} picks {worst['wins']}/{worst['n']}{worst_note}.")
    return " ".join([base] + missed) if missed else base


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
    """Close ONE of this book's open trades (removed from dp["open_trades"]
    by identity), updates the conviction ledger bucket, fires BOTH
    auto-bench subtags (the book-wide "daily_pick" line and the per-setup-
    type "pick_<top_component>" line), and appends a daybook entry — the
    trade-level record the daily recap reads."""
    sym = t["symbol"]
    contract_value = t.get("contract_value", 0.001)
    size = t["contracts"] * contract_value
    gross = t["direction"] * (exit_price - t["entry_price"]) * size
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)

    dp["open_trades"] = [x for x in dp.get("open_trades", []) if x is not t]

    bucket = _bucket(t.get("conviction", 5.0))
    ledger = dp.setdefault("conviction_ledger", _fresh_ledger())
    b = ledger.setdefault(bucket, {"n": 0, "wins": 0, "pnl": 0.0})
    b["n"] += 1
    b["wins"] += 1 if realized > 0 else 0
    b["pnl"] = round(b["pnl"] + realized, 2)

    entry_dt = datetime.strptime(
        t["entry_time"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    exit_dt = datetime.now(timezone.utc)
    hold_min = round((exit_dt - entry_dt).total_seconds() / 60, 1)
    daybook = dp.setdefault("daybook", [])
    daybook.append({
        "date": f"{exit_dt:%Y-%m-%d}", "symbol": sym,
        "dir": "long" if t["direction"] > 0 else "short",
        "conviction": t.get("conviction"),
        "components": t.get("ctx", {}).get("components", []),
        "outcome_pnl": realized, "hold_min": hold_min,
        "setup": t.get("top_component"),
        "low_conviction": t.get("low_conviction", False),
    })
    del daybook[:-500]

    # STOP-OUT COOLDOWN STAMP (the learning loop's first EARNED rule,
    # 2026-07-24: the engine stopped out of an ETH long at conv 15, then
    # re-entered the IDENTICAL setup 2h later at conv 15 and lost the same
    # money again — emotionless revenge-trading. A losing stop now stamps
    # (symbol, direction) with its conviction; select_pick refuses the same
    # trade for STOPOUT_COOLDOWN_H hours UNLESS conviction has genuinely
    # improved — the 14:00 re-entry at conv 35 vs 15 would rightly pass.)
    if realized < 0:
        dp.setdefault("last_stopouts", {})[
            f"{sym}:{'long' if t['direction'] > 0 else 'short'}"] = {
            "ts": exit_dt.isoformat(),
            "conviction": t.get("conviction") or 0.0}

    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [PICK] {sym} {reason}: PnL ${realized:+,.2f} -> "
          f"ledger ${eq:,.2f} (held {hold_min:.0f}m)")
    log_event({"action": "pick_exit", "symbol": sym, "reason": reason,
              "direction": t["direction"], "exit_price": exit_price,
              "realized_pnl": realized, "virtual_equity": eq,
              "conviction": t.get("conviction"), "bucket": bucket,
              "top_component": t.get("top_component"),
              "low_conviction": t.get("low_conviction", False),
              "hold_min": hold_min})
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

def _preview_entry(cand: dict, spec: dict, equity: float,
                   low_conviction: bool) -> dict:
    plan = _build_entry_plan(cand, spec, equity, low_conviction)
    sym = cand["symbol"]
    explain = _explain(cand)
    print(f"  [PICK DRY] {cand['direction'].upper()} {sym} WOULD FIRE — "
          f"conviction {cand['conviction']:.0f}%"
          f"{' LOW-CONV' if low_conviction else ''} — {explain} — "
          f"{plan['contracts']:.4g} ct (~${plan['notional']:,.0f} notional "
          f"at {plan['leverage']:.0f}x, risking {plan['risk_pct']*100:.2f}% "
          f"of equity) @ ~{plan['ref_price']:,.4f} | est TP "
          f"{plan['tp_ref']:,.4f} est SL {plan['sl_ref']:,.4f} | max hold "
          f"{MAX_HOLD_H:.0f}h — NO ORDER PLACED")
    return {"action": "would_enter", "symbol": sym,
            "direction": cand["direction"], "conviction": cand["conviction"],
            "low_conviction": low_conviction, "contracts": plan["contracts"],
            "leverage": plan["leverage"], "entry_ref": plan["ref_price"],
            "est_tp": plan["tp_ref"], "est_sl": plan["sl_ref"],
            "components": cand["components"]}


def _do_entry(private, demo_feed, state, dp, cand, spec, low_conviction,
             slot_ts) -> dict:
    plan = _build_entry_plan(cand, spec, state.get("virtual_equity", 0.0),
                             low_conviction)
    sym = cand["symbol"]
    direction = cand["direction"]
    explain = _explain(cand)
    print(f"  [PICK] {direction.upper()} SIGNAL {sym} conv="
          f"{cand['conviction']:.0f}%{' LOW-CONV' if low_conviction else ''} "
          f"— {plan['contracts']:.4g} ct (~${plan['notional']:,.0f} notional "
          f"at {plan['leverage']:.0f}x, risking {plan['risk_pct']*100:.2f}% "
          f"of equity)")

    if not private.ensure_leverage(sym, plan["leverage"]):
        notify("⚠️ daily pick entry ABORTED (demo)",
              f"couldn't set leverage on {sym} — no order placed")
        return {"action": "entry_aborted_leverage", "symbol": sym}

    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, sym, plan["open_side"], plan["contracts"],
            plan["ref_price"])
    except Exception as e:
        print(f"  [PICK] ENTRY FAILED: {str(e)[:100]}")
        # PARTIAL-FILL ROLLBACK (2026-07-24): a rejected clip can still leave
        # a partial position on the book (this is exactly how the naked -30ct
        # XAUT orphan happened). Before bailing, read the exchange's own net
        # and flatten anything that filled, so a failed entry NEVER leaves an
        # unbracketed, unattributed position behind.
        stray = 0.0
        try:
            stray = private.net_position_contracts(sym)
            if abs(stray) >= spec["min_size"]:
                for br in private.pending_tpsl(sym):
                    try: private.cancel_tpsl(sym, br.get("tpslId"))
                    except Exception: pass
                flat_side = "sell" if stray > 0 else "buy"
                private.market_order(sym, flat_side, abs(stray), reduce_only=True)
                print(f"  [PICK] rolled back partial fill: flattened "
                      f"{stray:+.4g}ct on {sym}")
        except Exception as e2:
            print(f"  [PICK] ROLLBACK FAILED: {str(e2)[:80]}")
        notify("⚠️ daily pick entry rejected (demo)",
              f"{sym} {direction} entry hit a book error and was rolled back "
              f"(no position left open). Skipping {sym} this slot.")
        return {"action": "entry_failed", "symbol": sym,
                "error": str(e)[:120], "rolled_back": round(stray, 4)}

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

    trade = {
        "symbol": sym, "direction": 1 if direction == "long" else -1,
        "contracts": plan["contracts"], "entry_price": entry,
        "entry_fee_bps": 2.0 if was_maker else 6.0, "entry_time": now_utc(),
        "tp_price": tp, "sl_price": sl, "tpsl_id": tpsl_id,
        "max_hold_h": MAX_HOLD_H, "conviction": cand["conviction"],
        "low_conviction": low_conviction, "top_component": top_tag,
        "leverage": plan["leverage"], "contract_value": spec["contract_value"],
        "ctx": {"atr_pct": round(cand["atr_pct_1h"] or 0.0, 2),
                "funding_bps": cand["funding_bps"],
                "components": cand["components"], "explain": explain},
    }
    dp.setdefault("open_trades", []).append(trade)
    dp["last_slot_ts"] = slot_ts
    picks = dp.setdefault("picks", [])
    picks.append({"date": slot_ts, "symbol": sym, "direction": direction,
                  "conviction": round(cand["conviction"], 1),
                  "low_conviction": low_conviction, "entry": entry, "tp": tp,
                  "sl": sl, "leverage": plan["leverage"],
                  "components": cand["components"]})
    del picks[:-200]
    save_state(state)

    log_event({"action": "pick_enter", "symbol": sym, "direction": direction,
              "conviction": cand["conviction"], "low_conviction": low_conviction,
              "components": cand["components"], "entry": entry, "tp": tp,
              "sl": sl, "leverage": plan["leverage"],
              "contracts": plan["contracts"], "top_component": top_tag})
    nice = NICE_NAMES.get(sym, sym.replace("-USDT", ""))
    notify(f"\U0001f4cc DAILY PICK: {direction.upper()} {sym} ({nice})",
          f"conviction {cand['conviction']:.0f}% — {explain} — entry "
          f"${entry:,.4f} TP ${tp:,.4f} SL ${sl:,.4f}"
          f"{' [LOW CONVICTION, half risk]' if low_conviction else ''} "
          f"(demo) — {len(dp['open_trades'])}/{MAX_CONCURRENT} slots open")
    return {"action": "entered", "symbol": sym, "direction": direction,
            "entry": entry, "tp": tp, "sl": sl, "contracts": plan["contracts"],
            "conviction": cand["conviction"], "low_conviction": low_conviction}


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_daily_pick(private, live_feed, demo_feed, state: dict, dry: bool = False):
    """One cycle. Reconcile/exit runs on EVERY currently open trade every
    call; a new pick is only attempted on a due slot (see _slot_ts) AND
    only if capacity remains under MAX_CONCURRENT. Returns a structured
    summary dict — {"action": "cycle", "due", "slot_ts", "exits",
    "holding", "entry", "open_count"} — mainly for tests/smoke."""
    dp = state.setdefault("daily_pick", _fresh_dp())
    _migrate_dp(dp)
    tag = " DRY" if dry else ""
    now = datetime.now(timezone.utc)
    today_str = f"{now:%Y-%m-%d}"
    slot_ts = _slot_ts(now)
    due = dp.get("last_slot_ts") != slot_ts

    open_trades = dp.get("open_trades", [])
    print(f"  [PICK{tag}] cycle @ {now:%H:%M} UTC | open={len(open_trades)}/"
          f"{MAX_CONCURRENT} {[t['symbol'] for t in open_trades]} | "
          f"last_slot_ts={dp.get('last_slot_ts')} | slot={slot_ts} | "
          f"due={due}")

    # -- reconcile every open trade: bracket-fired exits, 4h time exits,
    #    self-heal the bracket on anything still open. This ALWAYS runs,
    #    due slot or not — "so slots recycle" means a trade that times out
    #    THIS cycle must free its slot before the entry decision below
    #    even looks at capacity. --------------------------------------------
    exits: list[dict] = []
    holdings: list[dict] = []
    for t in list(open_trades):
        gone, exit_price, reason, fee_bps = _check_gone(private, t)
        if gone:
            print(f"  [PICK{tag}] {t['symbol']} position gone -> {reason} "
                  f"@ {exit_price:,.4f}")
            if dry:
                exits.append({"action": "would_exit", "symbol": t["symbol"],
                             "reason": reason, "exit_price": exit_price})
                continue
            _cleanup_orders(private, t["symbol"], t)
            realized = _book_exit(state, dp, t, exit_price, fee_bps, reason)
            exits.append({"action": "exit", "symbol": t["symbol"],
                         "reason": reason, "pnl": realized})
            continue

        entry_dt = datetime.strptime(
            t["entry_time"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
        held_h = (now - entry_dt).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", MAX_HOLD_H)
        if held_h >= max_hold_h:
            print(f"  [PICK{tag}] closing {t['symbol']} ({max_hold_h:.0f}h "
                  f"time exit, held {held_h:.1f}h)")
            if dry:
                exits.append({"action": "would_time_exit", "symbol": t["symbol"],
                             "contracts": t["contracts"]})
                continue
            _cleanup_orders(private, t["symbol"], t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(t["symbol"])
            ref_price = quote.bid if side == "sell" else quote.ask
            fill, was_maker = execute_market_clips(
                private, demo_feed, t["symbol"], side, t["contracts"],
                ref_price, reduce_only=True)
            realized = _book_exit(state, dp, t, fill, 2.0 if was_maker else 6.0,
                                  f"{max_hold_h:.0f}h time")
            exits.append({"action": "time_exit", "symbol": t["symbol"],
                         "pnl": realized})
            continue

        if not dry:
            _ensure_bracket(private, t["symbol"], state, t)
        print(f"  [PICK{tag}] holding {t['contracts']:.4g} ct "
              f"{'long' if t['direction'] > 0 else 'short'} {t['symbol']} "
              f"from {t['entry_price']:,.4f} ({held_h:.1f}h/{max_hold_h:.0f}h), "
              f"bracket verified")
        holdings.append({"symbol": t["symbol"], "direction": t["direction"],
                         "held_h": round(held_h, 1)})

    # -- entry: only on a due slot, and only if a slot is actually free
    #    (capacity = MAX_CONCURRENT - trades still holding after the
    #    reconcile pass above, which is correct in BOTH dry and real mode:
    #    real mode already removed exited trades from open_trades, and in
    #    dry mode `holdings` already excludes anything that would've
    #    exited this cycle). --------------------------------------------------
    entry_action = None
    if due:
        capacity_open = MAX_CONCURRENT - len(holdings)
        if capacity_open <= 0:
            print(f"  [PICK{tag}] slot due but at capacity "
                  f"({len(holdings)}/{MAX_CONCURRENT} open) — no new pick "
                  f"this slot")
            entry_action = {"action": "at_capacity", "open_count": len(holdings)}
            if not dry:
                dp["last_slot_ts"] = slot_ts
                save_state(state)
        else:
            if dp.get("last_recap_date") != today_str:
                # THE MISSED-TRADE LEDGER settles yesterday's passed
                # candidates BEFORE the recap is composed, once per UTC day
                # (this whole block is gated on last_recap_date), so
                # _build_recap_message sees fresh counterfactuals. Skipped
                # in dry mode — scoring mutates state (marks entries
                # scored, updates gate_scoreboard) and dry mode makes no
                # state side effects, same as last_slot_ts/last_recap_date.
                if not dry:
                    n_scored = score_passed_trades(live_feed, state)
                    if n_scored:
                        print(f"  [PICK{tag}] missed-trade ledger: scored "
                              f"{n_scored} passed candidate(s)")
                recap_msg = _build_recap_message(dp, state, today_str)
                print(f"  [PICK{tag}] daily recap: {recap_msg}")
                if not dry:
                    notify("\U0001f4d3 Learning engine — daily recap", recap_msg)
                    dp["last_recap_date"] = today_str
                    log_event({"action": "daily_recap", "message": recap_msg})

            print(f"  [PICK{tag}] === SLOT DUE ({slot_ts}) — scoring the "
                  f"universe ({len(holdings)}/{MAX_CONCURRENT} slots open, "
                  f"{capacity_open} free) ===")
            active_universe = _probe_universe(demo_feed)
            benched = state.get("benched_triggers", [])
            analysis = analyze_universe(live_feed, active_universe, benched)
            for a in sorted(analysis, key=lambda r: (r["conviction"] is None,
                                                      -(r["conviction"] or 0))):
                if a["ok"] and not a["stale"]:
                    print(f"    {a['symbol']:10s} conv={a['conviction']:5.1f} "
                          f"dir={a['direction']:5s} long={a['long_score']:5.1f} "
                          f"short={a['short_score']:5.1f} fund="
                          f"{a['funding_bps'] if a['funding_bps'] is not None else 'n/a'}")
                else:
                    print(f"    {a['symbol']:10s} SKIPPED "
                          f"({'stale' if a['stale'] else a['error']})")

            chosen, low_conv, skips = select_pick(analysis, private, demo_feed, state)
            if chosen is None:
                print("  [PICK] slot passed — all guarded")
                entry_action = {"action": "slot_passed_all_guarded", "skips": skips}
                if not dry:
                    dp["last_slot_ts"] = slot_ts
                    log_event({"action": "pick_slot_passed", "skips": skips})
                    save_state(state)
            else:
                cand, spec = chosen
                if dry:
                    entry_action = _preview_entry(
                        cand, spec, state.get("virtual_equity", 0.0), low_conv)
                else:
                    entry_action = _do_entry(private, demo_feed, state, dp,
                                             cand, spec, low_conv, slot_ts)
    else:
        print(f"  [PICK{tag}] not due yet (next slot at the next even-UTC "
              f"{SLOT_INTERVAL_H}h boundary) — reconcile only")

    return {"action": "cycle", "due": due, "slot_ts": slot_ts,
            "exits": exits, "holding": holdings, "entry": entry_action,
            "open_count": len(holdings)}
