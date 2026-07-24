"""
step5_paper_trade.py — the live loop: real bars, real demo orders, real fills.

USAGE
    python3 step5_paper_trade.py --check   # verify credentials, read balance
    python3 step5_paper_trade.py --once    # one decision cycle, then exit
    python3 step5_paper_trade.py           # run forever, one cycle per hour

WHAT ONE CYCLE DOES (the same loop a professional system runs, in miniature)

  1. wait for the top of the hour, when the 1h bar has just CLOSED
  2. pull fresh closed candles from the LIVE feed (real prices)
  3. compute the strategy signal on them — the exact same strategy.py
     function the backtester scored; not a copy, the same code
  4. read our current position FROM THE EXCHANGE (it is the source of
     truth, not our memory — a restart must never confuse the bot)
  5. if desired != current: place a market order on the DEMO account
  6. fetch the actual fill price and log expected vs actual — this is
     where you finally SEE real spread and slippage, the numbers we have
     been simulating since Step 2
  7. append everything to trades_log.jsonl for later comparison against
     the backtest's assumptions

WHY MA 30/50, DELIBERATELY, DESPITE STEP 4

Step 4's verdict was that this strategy has NO EDGE — the honest expectation
is that it will slowly lose (about -$3/trade out-of-sample). We run it
anyway because Step 5's goal is to learn the LIVE MACHINERY and measure real
fills, not to make fake money. Watching a known-edgeless strategy behave
live exactly as the harness predicted is the final proof the whole pipeline
tells the truth. Finding an actual edge is the game that starts after.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone

import config
from blofin_private import BlofinDemoPrivate, load_env
from book_ledger import attributed_position, unexplained_position
from strategy import vol_filtered_ma

# ---- run parameters -------------------------------------------------------

# Strategy under live validation: the ROUND-3 CHAMPION.
# MA 20/100 long-only on 4h bars, PLUS the volatility gate: entries are
# only allowed when ATR(14) >= 1.5% of price — i.e. when the market is
# actually moving. Round-3 test window vs the round-2 champion:
#   expectancy  $+41.65 -> $+339.18 per trade
#   return      +7.1%   -> +27.1%
#   max DD      -28.5%  -> -13.5%     (8 test trades — small sample)
# The edge is skipping dead markets: fewer, better entries.
FAST, SLOW = 20, 100
MIN_ATR_PCT = 1.5
BAR = "4h"                     # decisions at UTC 00/04/08/12/16/20
BAR_SECONDS = 4 * 3600
WARMUP_BARS = 300              # hysteresis needs deep history to know state
# THE BARBELL (round 15): one ledger, two books.
#   CORE     80% of equity at 2.0x  — the champion, compounding
#   TACTICAL 20% of equity at 10x   — MTF Dip (tactical.py), tight stops
# Core position sizing below = equity x 0.8 x 2.0 = 1.6x total equity.
# Reweighted 2026-07-23 (Wallace: grow as fast as the math allows):
# THE RIDE gets 60%, THE STRIKES get 40% — the strikes' Kelly analysis
# supports the extra weight (panic-dip standalone: $1k->$28.5k/6yr without
# ever dipping under $1k). Combined bull-dip exposure can reach ~5x equity;
# that is the chosen aggression, inside each strategy's measured optimum.
# 2026-07-23, OWNER DIRECTIVE: the ride's dial is 10x. Wallace set the bar
# ("minimum 10x", "2x is investor behavior") and the demo account is the
# sandbox that proves or breaks it with live trades — the backtest's 3x
# growth-peak estimate is recorded in RESEARCH_LOG.md but does NOT override
# his call. The -8% price stop at 10x means a stop-out costs ~80% of this
# slice; sized off the ledger, that is the chosen, understood risk.
CORE_ALLOC = 0.6
CORE_LEV = 10.0
NOTIONAL_FRACTION = CORE_ALLOC * CORE_LEV
CONTRACT_BTC = 0.001           # BloFin BTC-USDT: 1 contract = 0.001 BTC
LOT = 0.1                      # order size must be a multiple of this
LOG_FILE = "trades_log.jsonl"

# Protective bracket, round-11 revision: STOP-LOSS ONLY, and WIDE.
# We measured our original TP+5%/SL-2.5% bracket against six years of
# data: it cut the strategy's test return from +32.1% to +10.3%, because
# the TP amputated exactly the big winners that pay for everything, and
# the tight SL shook trades out on ordinary 4h noise. An -8% SL leaves
# the backtest IDENTICAL (+32.1%) while still insuring the true disaster:
# a flash crash between 4h decisions. The bracket is crash insurance,
# never trade management — that lesson now has a number on it.
SL_PCT = 8.0
TP_PCT = None

# The bot's own ledger. The demo ACCOUNT holds leftover balance from before
# the reset; the bot's score is kept separately in this file, starting at
# $1,000 — the same stake Wallace will fund a real account with. Positions
# are sized off THIS number, so every trade is exactly the size a real $1k
# account would take. Goal: $2,000.
STATE_FILE = "bot_state.json"

# Cloud state: when these env vars exist (on Render), the ledger lives in
# Supabase behind secret-checked RPC functions, so a stateless cloud
# container can restart, redeploy, or move machines without ever losing
# the $1,000 -> $2,000 scoreboard. Locally (no env vars) it stays a file.
from blofin_private import load_env as _load_env
_cloud = _load_env()
_SB_URL = _cloud.get("CRYPTOBOT_SUPABASE_URL", "")
_SB_KEY = _cloud.get("CRYPTOBOT_SUPABASE_ANON", "")
_SB_SECRET = _cloud.get("CRYPTOBOT_STATE_SECRET", "")
CLOUD_STATE = bool(_SB_URL and _SB_KEY and _SB_SECRET)


def _sb_rpc(fn: str, payload: dict):
    import requests as _rq
    r = _rq.post(f"{_SB_URL}/rest/v1/rpc/{fn}",
                 headers={"apikey": _SB_KEY,
                          "Authorization": f"Bearer {_SB_KEY}",
                          "Content-Type": "application/json"},
                 json=payload, timeout=20)
    r.raise_for_status()
    return r.json() if r.text else None


def sync_ledger_to_account(private, symbol, state) -> None:
    """Wallace's model: the virtual ledger and the BloFin balance are ONE
    number. When the bot is FLAT, set the ledger to the live account
    balance — so a manual balance change (like resetting to $1,500) or any
    realized PnL flows straight into the scoreboard automatically. Skipped
    mid-trade so an open position's math is never disturbed.

    ROUND-51 EXTENSION: the gold book (gold_book.py) now places REAL demo
    orders on XAUT-USDT — a different symbol, but the SAME shared demo
    account balance. Before this line existed, this guard only checked
    BTC-USDT books; a live gold position's unrealized PnL would have been
    silently folded into virtual_equity mid-trade the moment every BTC book
    happened to be flat. gold_book.open_trade is now checked exactly like
    every other book's — this is the one line this rewire is allowed to
    touch here.

    ROUND-58 EXTENSION: the Diver (diver.py) now places REAL demo orders on
    BTC-USDT too — same guard, same reasoning, checked exactly like every
    other BTC book above it."""
    has_trade = (state.get("open_trade")
                 or state.get("tactical", {}).get("open_trade")
                 or state.get("tactical_eth", {}).get("open_trade")
                 or state.get("shorts_lab", {}).get("open_trade")
                 or state.get("newsdesk", {}).get("open_trade")
                 or state.get("gold_book", {}).get("open_trade")
                 or state.get("diver", {}).get("open_trade"))
    if has_trade:
        return
    try:
        if abs(private.net_position_contracts(symbol)) > 0.001:
            return
        bal = round(float(private.futures_balance().get("balance", 0)), 2)
        cur = round(float(state.get("virtual_equity", 0)), 2)
        if bal > 0 and abs(bal - cur) > 0.01:
            state["virtual_equity"] = bal
            save_state(state)
            log_event({"action": "ledger_sync", "from": cur, "to": bal})
            print(f"  LEDGER SYNCED to live BloFin balance: ${bal:,.2f} "
                  f"(was ${cur:,.2f})")
    except Exception as e:
        print(f"  ledger sync skipped: {str(e)[:60]}")


def load_state() -> dict:
    if CLOUD_STATE:
        data = _sb_rpc("cryptobot_get_state", {"secret": _SB_SECRET})
        if data:
            return data
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"virtual_equity": 1000.0, "goal": 2000.0, "open_trade": None}


def save_state(state: dict):
    if CLOUD_STATE:
        try:
            _sb_rpc("cryptobot_set_state",
                    {"secret": _SB_SECRET, "payload": state})
            return
        except Exception as e:
            print(f"  (cloud state save failed, falling back to file: "
                  f"{str(e)[:60]})")
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=1)


def log_event(event: dict):
    """Append one JSON line locally AND mirror to the cloud log when
    configured, so trade history survives wherever the bot runs."""
    event["logged_at"] = datetime.now(timezone.utc).isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(event) + "\n")
    if CLOUD_STATE:
        try:
            _sb_rpc("cryptobot_log_event", {"secret": _SB_SECRET, "e": event})
        except Exception:
            pass                      # cloud mirror is best-effort


NTFY_TOPIC = "cryptobot-d60e8e02cb101257"   # private random topic; the
                                            # phone app subscribes to this


def notify(title: str, message: str):
    """Alerts to Wallace's phone. PRIMARY channel: a Telegram bot DM (set up
    2026-07-23, @wallace_cryptobot_alerts_bot) — reliable, and he confirmed it
    lands. ntfy.sh kept as a silent secondary. Reads creds from the process
    env (Render) first, then .env (local). A failed push must never stop
    trading, but failures now PRINT (no more silent notification black holes)."""
    import os as _os
    _e = _load_env()
    tok = _os.environ.get("TELEGRAM_BOT_TOKEN") or _e.get("TELEGRAM_BOT_TOKEN", "")
    chat = _os.environ.get("TELEGRAM_CHAT_ID") or _e.get("TELEGRAM_CHAT_ID", "")
    if tok and chat:
        try:
            import requests as _rq
            r = _rq.post(f"https://api.telegram.org/bot{tok}/sendMessage",
                         data={"chat_id": chat, "text": f"{title}\n{message}"},
                         timeout=6)
            if r.status_code != 200:
                print(f"  telegram push non-200: {r.status_code} {r.text[:80]}")
        except Exception as e:
            print(f"  telegram push failed: {str(e)[:80]}")
    try:
        import requests as _rq
        _rq.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=message.encode(),
                 headers={"Title": title.encode("ascii", "ignore").decode(),
                          "Priority": "high"}, timeout=6)
    except Exception:
        pass                        # a failed push must never stop trading


def now_utc() -> str:
    return f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S} UTC"


def sleep_until_next_bar():
    """Sleep to shortly after the next 4h boundary (UTC 00/04/08/...), when
    a fresh bar has closed. The +20s margin lets the exchange finalize it."""
    now = time.time()
    next_bar = (int(now // BAR_SECONDS) + 1) * BAR_SECONDS + 20
    wait = next_bar - now
    print(f"  sleeping {wait / 60:.1f} min until the next {BAR} bar closes...")
    time.sleep(wait)


BENCH_MIN_TRADES = 8      # a trigger with this many LIVE trades and negative
                          # expectancy gets auto-benched (the memory system:
                          # learn from real outcomes, never from fewer)


def recent_news_headline() -> str | None:
    """Most recent captured headline (for trade-review context)."""
    if not CLOUD_STATE:
        return None
    try:
        rows = _sb_rpc("cryptobot_recent_news",
                       {"secret": _SB_SECRET, "n": 1})
        return rows[0] if rows else None
    except Exception:
        return None


def write_lesson(state: dict, trigger: str, pnl: float, entry_price: float,
                 exit_price: float, reason: str, ctx: dict | None):
    """Wallace's rule, both directions: EVERY trade gets a plain-English
    review — what it was, the conditions and news around it, why it worked
    or didn't, and what to carry forward. The honest part: wins in thin
    conditions get flagged as luck (don't learn the wrong lesson), and
    losses in solid conditions get labeled as normal strategy cost (don't
    "fix" what isn't broken)."""
    ctx = ctx or {}
    atr_v, fb_v = ctx.get("atr_pct"), ctx.get("funding_bps")
    news = ctx.get("news")
    won = pnl > 0
    obs = []
    if atr_v is not None:
        obs.append(f"market heat {atr_v:.1f}% ({'healthy' if atr_v >= 1.65 else 'barely above the gate'})")
    if fb_v is not None:
        obs.append(f"crowd lean {fb_v:+.1f}bp ({'calm' if fb_v <= 0.8 else 'near euphoria'})")
    if news:
        obs.append(f"backdrop: {str(news)[:90]}")
    thin = (atr_v is not None and atr_v < 1.65) or (fb_v is not None and fb_v > 0.8)
    if won and not thin:
        verdict = ("worked as designed — trend confirmed, market moving, "
                   "crowd calm; keep taking this setup every time")
    elif won and thin:
        verdict = ("WON DESPITE thin conditions — this was closer to luck "
                   "than skill; do not size up on setups like this")
    elif not won and thin:
        verdict = ("lost in thin conditions — the fixable kind; these "
                   "cluster, and the memory is counting them")
    else:
        verdict = ("lost in solid conditions — the normal cost of the "
                   "strategy (it wins by losing small and often); nothing "
                   "to fix")
    lesson = {
        "date": now_utc(), "trigger": trigger,
        "trade": f"long ${entry_price:,.0f} -> {reason} ${exit_price:,.0f}, "
                 f"{'made' if won else 'lost'} ${abs(pnl):,.2f}",
        "conditions": "; ".join(obs) if obs else "context not captured",
        "why": verdict,
    }
    lessons = state.setdefault("lessons", [])
    lessons.append(lesson)
    del lessons[:-50]
    log_event({"action": "lesson", **lesson})


def record_trade_outcome(state: dict, trigger: str, pnl: float):
    """The memory layer (adopted from TradingBotV2's ledger/learnings idea,
    adapted to our evidence standards): every live outcome updates per-
    trigger stats stored durably in cloud state. A trigger that proves
    itself bad LIVE (>=8 trades, negative expectancy) is BENCHED
    automatically — no new entries — and Wallace gets notified. Stats
    with fewer trades never veto anything: small samples are noise."""
    stats = state.setdefault("trigger_stats", {})
    t = stats.setdefault(trigger, {"n": 0, "pnl": 0.0, "wins": 0})
    t["n"] += 1
    t["pnl"] = round(t["pnl"] + pnl, 2)
    t["wins"] += pnl > 0
    exp = t["pnl"] / t["n"]
    if (t["n"] >= BENCH_MIN_TRADES and exp < 0
            and trigger not in state.setdefault("benched_triggers", [])):
        state["benched_triggers"].append(trigger)
        log_event({"action": "auto_bench", "trigger": trigger,
                   "n": t["n"], "expectancy": round(exp, 2)})
        notify(f"🪑 BENCHED: {trigger}",
               f"{t['n']} live trades, ${exp:+.2f}/trade — no new entries "
               f"until review (demo)")


def book_exit(state: dict, exit_price: float, reason: str,
              exit_fee_bps: float | None = None) -> float:
    """Close the open trade on the bot's own ledger and return realized PnL.

    PnL = direction x (exit - entry) x size, minus each side's ACTUAL fee
    (2 bps when we filled as maker, 6 when we had to take).
    This is the number that moves the $1,000 -> $2,000 scoreboard.
    """
    t = state["open_trade"]
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    entry_bps = t.get("entry_fee_bps", config.fee_bps())
    exit_bps = exit_fee_bps if exit_fee_bps is not None else config.fee_bps()
    fees = (t["entry_price"] * entry_bps
            + exit_price * exit_bps) * size_btc / 10_000

    # funding on the time held: events = hours/8, signed like a real perp
    # (long pays positive rates). Estimated at the current rate — rates
    # drift over a hold, but booking an estimate beats booking zero.
    funding_cost = 0.0
    try:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = max(0.0, (datetime.now(timezone.utc)
                           - entry_dt.replace(tzinfo=timezone.utc))
                     .total_seconds() / 3600)
        rate = t.get("funding_bps_est", 1.0)
        funding_cost = (t["direction"] * rate * (held_h / 8)
                        * t["entry_price"] * size_btc / 10_000)
    except Exception:
        pass
    realized = gross - fees - funding_cost
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["open_trade"] = None
    save_state(state)

    eq, goal = state["virtual_equity"], state.get("goal", 2000.0)
    print(f"  LEDGER: {reason} PnL ${realized:+,.2f} -> "
          f"equity ${eq:,.2f} / goal ${goal:,.0f}")
    log_event({"action": "ledger", "reason": reason,
               "realized_pnl": round(realized, 2), "virtual_equity": eq})
    record_trade_outcome(state, "ride", realized)
    write_lesson(state, "ride", realized, t["entry_price"], exit_price,
                 reason, t.get("ctx"))
    notify(f"💰 trade closed: ${realized:+,.2f}",
           f"ledger ${eq:,.2f} / goal ${goal:,.0f} (demo)")
    if eq >= goal:
        notify("🏆 GOAL HIT", f"${eq:,.2f} — the $1k doubled. (demo)")
    return realized


MAKER_PATIENCE_S = 600         # rest the limit up to 10 min, then chase
MAKER_POLL_S = 20

# Round-6 sentiment gate: refuse NEW entries while funding is above this
# (crowd already paying a premium to be long = euphoria). On six years of
# data this filter only ever removed losing entries (train +226%->+269%,
# validation +57.7%->+67.8%, test literally unchanged because the 2025-26
# window contained no euphoric entries). Insurance for the next mania,
# free everywhere else. An OPEN position is never touched by sentiment.
MAX_ENTRY_FUNDING_BPS = 1.0


def current_funding_bps(live_feed, symbol: str) -> float | None:
    """Current funding rate from BloFin's public endpoint, in bps/8h."""
    try:
        data = live_feed._get("/api/v1/market/funding-rate",
                              {"instId": symbol})
        return float(data[0]["fundingRate"]) * 10_000
    except Exception:
        return None                # unreadable -> don't block on missing data


MAX_CLIP = 5.0        # live-fire finding 2026-07-23: the demo book absorbs
                      # ~5 ct passively but chokes on 10+. Bigger orders get
                      # sliced into clips so each rests where depth exists.


def execute_market_clips(private, demo_feed, symbol: str, side: str,
                         contracts: float, ref_price: float,
                         reduce_only: bool = False):
    """OWNER'S LAW (2026-07-24, after three stray-buy-order sightings):
    a buy order only exists when we truly want to BUY NOW, and TP/SL are
    ONLY ever the native bracket. So live entries fill via instant MARKET
    clips — on the screen for seconds, never resting. Costs taker fees
    (6bps vs 2) — the price of clean, atomic, interruption-proof entries;
    the old maker-and-wait loop left orphaned resting orders and partial
    naked positions whenever a deploy or crash hit mid-loop.
    Returns (approx_fill_price, was_maker=False)."""
    import math as _m
    remaining = round(contracts, 1)
    clip = 5.0
    while remaining > 0.05:
        step = min(clip, remaining)
        private.market_order(symbol, side, round(step, 1),
                             reduce_only=reduce_only)
        remaining = round(remaining - step, 1)
    # approximate fill from the live quote (fills endpoint lags); books
    # reconcile against the exchange anyway.
    try:
        q = demo_feed.get_ticker(symbol)
        px = q.ask if side == "buy" else q.bid
    except Exception:
        px = ref_price
    return float(px), False


def execute_maker_or_chase(private: BlofinDemoPrivate, demo_feed, symbol: str,
                           side: str, contracts: float, limit_price: float,
                           reduce_only: bool = False) -> tuple[float, bool]:
    """Fills `contracts` as maker-with-chase. Orders larger than MAX_CLIP
    are executed as a sequence of clips; returns the size-weighted average
    fill and whether the majority filled as maker."""
    if contracts > MAX_CLIP + LOT / 2:
        fills, makers = [], 0.0
        left = contracts
        while left > LOT / 2:
            clip = min(MAX_CLIP, left)
            px, mk = _execute_single(private, demo_feed, symbol, side,
                                     round(clip, 1), limit_price, reduce_only)
            fills.append((px, clip))
            makers += clip if mk else 0.0
            left -= clip
        avg = sum(p * c for p, c in fills) / sum(c for _, c in fills)
        return avg, makers >= contracts / 2
    return _execute_single(private, demo_feed, symbol, side, contracts,
                           limit_price, reduce_only)


def _execute_single(private: BlofinDemoPrivate, demo_feed, symbol: str,
                    side: str, contracts: float, limit_price: float,
                    reduce_only: bool = False) -> tuple[float, bool]:
    """The round-5 execution upgrade, live.

    Try to be the PASSIVE side: post-only limit at the signal price. If it
    fills we pay 2 bps instead of 6 and cross no spread. If price runs away
    for MAKER_PATIENCE_S, cancel and chase with a market order — modeled in
    the backtest, mirrored here.

    Returns (fill_price, was_maker).
    """
    try:
        oid = private.post_only_order(symbol, side, contracts, limit_price,
                                      reduce_only=reduce_only)
    except Exception as e:
        # post-only got rejected (our price would have crossed the book);
        # market is already through our level, so just take it
        print(f"    post-only rejected ({str(e)[:60]}) — taking market")
        oid = private.market_order(symbol, side, contracts,
                                   reduce_only=reduce_only)
        time.sleep(1.5)
        f = private.fills(symbol, oid)
        return (float(f[0]["fillPrice"]) if f else limit_price, False)

    waited = 0
    while waited < MAKER_PATIENCE_S:
        time.sleep(MAKER_POLL_S)
        waited += MAKER_POLL_S
        still_pending = any(str(o.get("orderId")) == oid
                            for o in private.pending_orders(symbol))
        if not still_pending:
            f = private.fills(symbol, oid)
            price = float(f[0]["fillPrice"]) if f else limit_price
            print(f"    MAKER filled at {price:,.1f} after {waited}s "
                  f"(fee 2 bps, no spread crossed)")
            return price, True

    # patience exhausted — cancel the resting order and chase
    try:
        private.cancel_order(symbol, oid)
    except Exception:
        pass                                  # may have just filled; fine
    time.sleep(1)
    f = private.fills(symbol, oid)
    if f:                                     # filled at the last moment
        return float(f[0]["fillPrice"]), True
    print(f"    limit unfilled after {MAKER_PATIENCE_S}s — chasing at market")
    oid2 = private.market_order(symbol, side, contracts,
                                reduce_only=reduce_only)
    time.sleep(1.5)
    f2 = private.fills(symbol, oid2)
    return (float(f2[0]["fillPrice"]) if f2 else limit_price, False)


def decide_and_trade(private: BlofinDemoPrivate, live_feed, symbol: str):
    """One full decision cycle. Returns a summary dict.

    BOOK ATTRIBUTION (fixed 2026-07-23, see book_ledger.py for the full
    incident writeup). BloFin nets every book's BTC-USDT activity — THE
    RIDE (this function), THE STRIKES (tactical.py), THE SHORTS LAB
    (shorts_lab.py) — into ONE exchange position. This function used to
    read that raw net with private.net_position_contracts() and treat the
    WHOLE thing as its own position. On 2026-07-23 the shorts lab opened a
    -69.6 ct short; this function's champion signal was 0 (wants flat), it
    read the net as "I am short 69.6 ct I don't want," and spent cycles
    BUYING it back in 5-ct post-only clips (execute_maker_or_chase's clip
    loop) — fighting a position that belonged entirely to another book. Its
    exit path then did a blanket cancel of every pending TP/SL bracket on
    the symbol, stripping the lab's protective stop out from under a live
    position on its way out.

    THE RULE, now enforced everywhere below: this function only ever acts
    on book_ledger.attributed_position(net, state, "ride") — the exchange
    net minus every OTHER book's own recorded position, i.e. the slice
    that is actually the ride's. It never reads or reacts to the raw net,
    and its bracket cleanup only ever touches an order id it recorded
    itself (never a blanket sweep while another book is holding).
    """
    state = load_state()
    net = private.net_position_contracts(symbol)
    current_ride = attributed_position(net, state, "ride")

    # 0. if we thought we had a trade on but OUR ATTRIBUTED SLICE is flat,
    #    the TP/SL bracket fired between cycles — book it before deciding.
    #    Comparing against our own slice (not raw net) so another book's
    #    still-open position can never mask, or fake, the ride's own exit.
    if state.get("open_trade") and abs(current_ride) < LOT / 2:
        try:
            fills = private.fills(symbol)
            exit_price = float(fills[0]["fillPrice"]) if fills else \
                state["open_trade"]["entry_price"]
        except Exception:
            exit_price = state["open_trade"]["entry_price"]
        print("  bracket fired since last cycle — booking the exit.")
        book_exit(state, exit_price, "TP/SL")
        current_ride = attributed_position(net, state, "ride")   # re-derive
                                                                  # (state changed)

    # 1. fresh CLOSED bars from the live feed (real market prices)
    candles = live_feed.get_candles(symbol, BAR, WARMUP_BARS)
    last_close = float(candles["close"].iloc[-1])
    last_bar = candles["timestamp"].iloc[-1]

    # 2. the same signal function the backtester scored
    sig = vol_filtered_ma(candles, FAST, SLOW, min_atr_pct=MIN_ATR_PCT)
    desired_dir = int(sig.iloc[-1]) if sig.iloc[-1] == sig.iloc[-1] else 0

    # 3. current truth from the exchange — OUR ATTRIBUTED SLICE, never the
    #    raw net (see the module note above; this is the exact 2026-07-23 bug).
    current_dir = 0 if abs(current_ride) < LOT / 2 else (
        1 if current_ride > 0 else -1)
    unexplained = unexplained_position(net, state)

    print(f"\n[{now_utc()}] bar {last_bar:%m-%d %H:%M} close {last_close:,.1f}"
          f" | signal {desired_dir:+d} | ride slice {current_ride:+.1f} ct"
          f" (exchange net {net:+.1f}, unexplained {unexplained:+.1f})")

    # equity snapshot every cycle — this is the "PnL throughout time" series.
    # The scoreboard is the bot's OWN ledger (started at $1,000), never the
    # demo account's balance, which still carries pre-reset money.
    t = state.get("open_trade")
    unreal = 0.0
    if t:
        unreal = (t["direction"] * (last_close - t["entry_price"])
                  * t["contracts"] * CONTRACT_BTC)
    log_event({"action": "snapshot", "bar": str(last_bar),
               "close": last_close, "signal": desired_dir,
               "position_contracts": net, "ride_contracts": current_ride,
               "unexplained_contracts": unexplained,
               "virtual_equity": state["virtual_equity"],
               "unrealized_pnl": round(unreal, 2),
               "equity": round(state["virtual_equity"] + unreal, 2)})

    # Trader-tempo note (Wallace, clarified): prefer strategies that resolve
    # FAST BY NATURE (tight stops/targets — the tactical book) over slow
    # ones; but never amputate a validated trade mid-flight with an
    # arbitrary clock. A hard 14-day cap was tested, shipped for an hour,
    # and removed on his clarification — the uncapped core also tests
    # better (+32.1% vs +27.3%).

    if desired_dir == current_dir:
        if desired_dir == 0 and abs(unexplained) > LOT / 2:
            # THE INCIDENT, structurally impossible now: our own slice is
            # already flat (or already matches what we want), but the raw
            # exchange net is not — some OTHER book owns that contracts.
            # Not ours to touch. Do nothing.
            print(f"  desired flat, our slice is flat — exchange net "
                  f"{net:+.1f} ct belongs to other books "
                  f"(unexplained {unexplained:+.1f}). Doing nothing.")
        else:
            print("  no change needed — holding course.")
        return

    # 4. we need to trade. Snapshot the demo book's quote first so we can
    #    measure what the fill cost us relative to what we saw.
    demo_feed, _ = config.make_exchange("demo")
    quote = demo_feed.get_ticker(symbol)

    # -- exit any existing position first (OUR SLICE ONLY)
    if current_dir != 0:
        # Cancel ONLY our own bracket order — never a blanket sweep of every
        # pending TP/SL on the symbol. That blanket cancel is the exact
        # 2026-07-23 bug: it stripped the shorts lab's protective stop out
        # from under a live position that had nothing to do with the ride.
        t_own = state.get("open_trade")
        own_tpsl_id = t_own.get("tpsl_id") if t_own else None
        other_books_open = bool(
            state.get("tactical", {}).get("open_trade")
            or state.get("shorts_lab", {}).get("open_trade")
            or state.get("apprentice", {}).get("open_trade")
            or state.get("newsdesk", {}).get("open_trade")
            or state.get("diver", {}).get("open_trade"))
        if own_tpsl_id:
            try:
                private.cancel_tpsl(symbol, str(own_tpsl_id))
                print(f"  cancelled our own TP/SL bracket {own_tpsl_id}")
            except Exception as e:
                print(f"  (bracket cleanup: {str(e)[:80]})")
        elif not other_books_open:
            # No id on record (older state, or the bracket placement never
            # got a chance to save one) — but nothing else is holding a
            # position on this symbol either, so a full sweep is safe:
            # there is nothing else on the exchange to protect.
            try:
                for br in private.pending_tpsl(symbol):
                    private.cancel_tpsl(symbol, str(br.get("tpslId")))
                    print(f"  cancelled old TP/SL bracket {br.get('tpslId')}")
            except Exception as e:
                print(f"  (bracket cleanup: {str(e)[:80]})")
        else:
            print("  no recorded bracket id for our own position, and "
                  "another book is open — skipping a blanket cancel so we "
                  "never touch their protection.")

        side = "sell" if current_dir > 0 else "buy"
        print(f"  EXIT  {side} {abs(current_ride):.1f} ct — trying "
              f"maker at {last_close:,.1f}")
        exit_fill, was_maker = execute_maker_or_chase(
            private, demo_feed, symbol, side, abs(current_ride),
            last_close, reduce_only=True)
        log_event({"action": "exit", "side": side, "fill_price": exit_fill,
                   "maker": was_maker})
        if state.get("open_trade"):
            book_exit(state, exit_fill, "signal exit",
                      exit_fee_bps=(2.0 if was_maker else config.fee_bps()))
        notify("🤖 CLOSED position",
               f"{side} {abs(current_ride):.1f} ct {symbol} "
               f"@{exit_fill:,.0f} {'maker' if was_maker else 'taker'} (demo)")

    # 5. enter the new position — sized off the BOT'S LEDGER, not the
    #    account, so every trade is exactly what a real $1k account would do
    if desired_dir != 0:
        # round-6 sentiment gate: no fresh longs into a euphoric crowd
        fb = current_funding_bps(live_feed, symbol)
        if fb is not None and desired_dir > 0 and fb > MAX_ENTRY_FUNDING_BPS:
            print(f"  SENTIMENT VETO: funding {fb:+.2f} bps/8h > "
                  f"+{MAX_ENTRY_FUNDING_BPS} — crowd too long, not entering.")
            log_event({"action": "sentiment_veto", "funding_bps": fb})
            return
        notional = state["virtual_equity"] * NOTIONAL_FRACTION
        contracts = max(LOT, round(notional / last_close / CONTRACT_BTC / LOT)
                        * LOT)
        side = "buy" if desired_dir > 0 else "sell"
        print(f"  ENTER {side} {contracts:.1f} ct ≈ "
              f"${contracts * CONTRACT_BTC * last_close:,.0f} notional — "
              f"trying maker at {last_close:,.1f}")
        entry_fill, was_maker = execute_maker_or_chase(
            private, demo_feed, symbol, side, contracts, last_close)
        log_event({"action": "enter", "side": side, "fill_price": entry_fill,
                   "maker": was_maker})
        state["open_trade"] = {"direction": desired_dir,
                               "contracts": contracts,
                               "entry_price": entry_fill,
                               "entry_fee_bps": 2.0 if was_maker
                               else config.fee_bps(),
                               "funding_bps_est": fb if fb is not None else 1.0,
                               "entry_time": now_utc(),
                               "tp_price": None, "sl_price": None,
                               "tp_order_id": None, "tpsl_id": None}
        save_state(state)

        # protective bracket, visible in the BloFin app on the position
        ref = entry_fill
        if desired_dir > 0:
            sl = ref * (1 - SL_PCT / 100)
            close_side = "sell"
        else:
            sl = ref * (1 + SL_PCT / 100)
            close_side = "buy"
        try:
            bid = private.place_tpsl(symbol, close_side, contracts, None, sl)
            print(f"  BRACKET set: SL {sl:,.1f} (-{SL_PCT}%), no TP — "
                  f"winners run to the signal exit  [{bid}]")
            log_event({"action": "bracket", "tp": None,
                       "sl": round(sl, 1), "tpsl_id": bid})
            # RECORD our own bracket id — this is what lets the exit path
            # cancel ONLY our own bracket later instead of sweeping every
            # pending TP/SL on the symbol (the 2026-07-23 bug).
            state["open_trade"]["sl_price"] = sl
            state["open_trade"]["tpsl_id"] = bid
            save_state(state)
            notify("🤖 OPENED position",
                   f"{side} {contracts:.1f} ct {symbol} ~{entry_fill:,.0f} | "
                   f"SL {sl:,.0f}, no cap on the win (demo)")
        except Exception as e:
            print(f"  BRACKET FAILED (position is unprotected!): "
                  f"{str(e)[:120]}")
            log_event({"action": "bracket_failed", "error": str(e)[:200]})
            notify("⚠️ bot: bracket FAILED",
                   f"position open without TP/SL — check BloFin (demo)")


def report_fill(private: BlofinDemoPrivate, symbol: str, order_id: str,
                expected: float, action: str, side: str):
    """Fetch the actual fill and log expected-vs-actual. THE Step 5 number:
    realized slippage, measured, not assumed."""
    time.sleep(1.5)                       # give the match engine a beat
    fill_price = None
    try:
        fills = private.fills(symbol, order_id)
        if fills:
            prices = [float(f["fillPrice"]) for f in fills if f.get("fillPrice")]
            sizes = [float(f.get("fillSize", 1) or 1) for f in fills]
            fill_price = sum(p * s for p, s in zip(prices, sizes)) / sum(sizes)
    except Exception as e:
        print(f"    (could not fetch fill yet: {str(e)[:80]})")

    if fill_price:
        # slippage: how much worse than the quote we actually did
        sign = 1 if side == "buy" else -1
        slip_bps = sign * (fill_price - expected) / expected * 10_000
        print(f"    FILLED at {fill_price:,.1f} | slippage vs quote: "
              f"{slip_bps:+.2f} bps "
              f"(backtest assumed +{config.DEFAULT_SLIPPAGE_BPS:.0f})")
    log_event({"action": action, "side": side, "order_id": order_id,
               "expected_price": expected, "fill_price": fill_price})
    return fill_price or expected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify credentials and read balance, then exit")
    ap.add_argument("--once", action="store_true",
                    help="run one decision cycle immediately, then exit")
    args = ap.parse_args()

    env = load_env()
    try:
        private = BlofinDemoPrivate(
            env.get("BLOFIN_DEMO_API_KEY", ""),
            env.get("BLOFIN_DEMO_API_SECRET", ""),
            env.get("BLOFIN_DEMO_PASSPHRASE", ""),
        )
    except ValueError as e:
        print(f"NOT READY: {e}")
        return
    live_feed, symbol = config.make_exchange("live")

    # -- credential check ---------------------------------------------------
    bal = private.futures_balance()
    print(f"connected to BloFin DEMO. futures USDT balance: "
          f"{float(bal.get('balance', 0)):,.2f} "
          f"(available {float(bal.get('available', 0)):,.2f})")
    pos = private.net_position_contracts(symbol)
    print(f"current {symbol} position: {pos:+.1f} contracts")
    if args.check:
        return

    try:
        private.set_leverage(symbol, 3)
        print("leverage set to 3x cross (margin headroom; exposure stays <1x)")
    except Exception as e:
        print(f"set-leverage skipped: {str(e)[:100]}")

    state = load_state()
    print(f"\nstrategy: MA {FAST}/{SLOW} + ATR>={MIN_ATR_PCT}% gate, long-only on "
          f"{BAR} {symbol} — the round-3 champion.")
    print(f"LEDGER: ${state['virtual_equity']:,.2f} / goal "
          f"${state.get('goal', 2000):,.0f}. Selective by design: it trades "
          f"when the trend signal turns, not on a schedule.")

    if args.once:
        decide_and_trade(private, live_feed, symbol)
        return

    print("running until interrupted (Ctrl-C). one decision per closed bar.")
    while True:
        try:
            decide_and_trade(private, live_feed, symbol)
        except Exception as e:
            # A failed cycle must never kill the loop. Log it, wait, retry
            # next bar. The exchange still holds the position safely.
            print(f"  CYCLE ERROR (will retry next bar): {str(e)[:150]}")
            log_event({"action": "error", "error": str(e)[:300]})
        sleep_until_next_bar()


if __name__ == "__main__":
    main()
