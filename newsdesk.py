"""
newsdesk.py — THE NEWSDESK: the live demo-trading book for round 45B, the
FIRST strategy in this whole program to pass a sealed out-of-sample test
(step45b_news_events.py: A-news-momentum, first-bar-move, 1h,
stop1.2%/tgt2.4%, hold24h — train +$23.74/t, val +$7.11/t, SEALED TEST
+$20.81/t x67, +13.9%). news_book.py forward-tested this exact setup with
SIMULATED money, isolated from the shared BloFin net. This file is the
promotion: real demo orders, on the shared BTC-USDT position, joined to
book_ledger.py's attribution system. Structural template: shorts_lab.py
(one slot, dry mode, reconcile, hardened double-read _ensure_bracket,
_book_exit math, entry via ensure_leverage + a single place_tpsl bracket).

THE VALIDATED RULE (deployed VERBATIM — no improvements):
  When a RELEVANT WatcherGuru headline lands, take the FIRST FULL 1h bar
  after the event (the bar whose entire life is post-event: event at
  14:07 -> the 15:00-16:00 bar), read its close-vs-open sign, and enter AT
  THAT BAR'S CLOSE in that direction. Stop 1.2% / target 2.4% (2x) / max
  hold 24h. Relevance = the EXACT classify_headline() imported from
  step45b_news_events.py, unmodified. Direction comes from the BAR, never
  the keyword tag — keyword tags are irrelevant to this variant; they are
  imported only as a side effect of importing classify_headline itself.

NO-LOOKAHEAD ALIGNMENT, matched to step45b_news_events.align_events exactly:
  floor bar  = the bar whose open <= event_ts (== event_ts floored to the
               hour) — the bar that was already live when the headline hit.
  trading bar (direction_bar_open_ts) = floor bar's open + 1h — the first
               bar whose ENTIRE life happens strictly after the event was
               public. Event 14:07 -> floor 14:00 -> direction bar 15:00,
               exactly the mandate's own worked example. We enter at THAT
               bar's own close once it has closed (16:00), i.e. one full
               bar later than align_events' `trading_idx` flag position —
               align_events sets the signal flag on trading_idx and lets
               the backtest engine fill at trading_idx's OPEN; the live
               rule instead reads trading_idx's own CLOSE for direction
               and fills there. Same bar, same no-lookahead boundary,
               different (mandate-specified) fill point within it.

NEWS SOURCE — REALITY CHECK (read before touching anything above)
The Supabase RPC `cryptobot_recent_news` was inspected live (read-only,
n=200) before writing this file. It returns a PLAIN LIST OF STRINGS —
no id, no timestamp, no source column, nothing but headline text, ordered
newest-first. The `cryptobot_news` table it reads from mixes MANY sources
into one feed: Donald Trump's own Truth Social reposts, WHITEHOUSE press
releases, COINTELEGRAPH, CoinDesk, DECRYPT, THE BLOCK, FORBES, BLOOMBERG
LAW, EU COUNCIL, dozens of individual crypto-project Twitter accounts,
SEC filings, and — the ones we want — WatcherGuru. WatcherGuru's own posts
are recognizable ONLY by a literal "[WatcherGuru]" text prefix baked into
the string itself (confirmed empirically: 25 of a 200-row sample carried
it, all in the form "[WatcherGuru] JUST IN: ..."). `_is_watcherguru()`
below is that filter — a text-prefix check, because that is the only
signal the feed actually carries.

DEVIATION FROM THE BRIEF, FORCED BY THAT REALITY (flagged loudly, also in
the final report): the brief says to track `last_event_ts` and process
"news rows newer than" it. With no per-row timestamp or id in what the RPC
actually returns, a literal `row.timestamp > last_event_ts` comparison is
impossible — there is no row.timestamp. This module instead:
  - dedupes by keeping a rolling set of already-seen headline TEXT
    (state["newsdesk"]["seen_headlines"], capped) — text is the only
    stable identity the feed offers;
  - treats the WALL-CLOCK moment we first observe a new relevant
    WatcherGuru headline as that headline's event_ts. Defensible: the
    news-watch -> workflow_dispatch wake fires promptly on new rows (see
    the WIRE-IN note below), so observation time closely tracks post
    time, and this bot can only ever act on news once its own pipeline
    has seen it — the same causal boundary the backtest itself enforced
    (it could only trade on the bar after a post became public);
  - still keeps `state["newsdesk"]["last_event_ts"]` exactly as specified
    in the schema, populated with the wall-clock time of the last scan
    that found anything — an informational/audit field, not the dedup
    mechanism (that's `seen_headlines`).
No other deviation from the validated rule was necessary or made.

WIRE-IN / TIMING (daemon.py + hourly.py): newsdesk timing depends on 1h
bar closes. The daemon's hourly bar-close full_cycle (and hourly.py's own
top-of-hour cron) satisfy the entry timing on their own. A headline that
lands MID-HOUR is picked up sooner than that: the news-watch edge function
fires a `workflow_dispatch` wake, hourly.py runs immediately, scans the
wire, and (if daemon isn't already alive and owning trading) sets
`pending` right then — well before the direction bar even opens, let alone
closes. Either path — the daemon's own next hourly cycle, or the
workflow_dispatch wake — arms `pending` comfortably before
`direction_bar_open_ts + 1h`; actual ENTRY only ever happens on a
bar-close decision cycle, matching the backtest's own fill timing exactly.

DRY MODE: run_newsdesk(..., dry=True) computes and prints the full
decision every cycle would make — reconcile, gate, sizing, stop/target —
but places NO orders and makes NO state/log/notify side effects. Used by
step46_newsdesk_smoke.py against the REAL news RPC and REAL candles.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import pandas as pd

from blofin_private import BlofinDemoPrivate
from book_ledger import attributed_position, unexplained_position
from step45b_news_events import classify_headline
from step5_paper_trade import (CLOUD_STATE, CONTRACT_BTC, LOT, _SB_SECRET,
                               _sb_rpc, execute_maker_or_chase, log_event,
                               notify, now_utc, record_trade_outcome,
                               save_state, write_lesson)

SYMBOL = "BTC-USDT"

# -- sizing: one slot, 15% of ledger equity, 20x leverage (owner's 15-20x
# tier mandate — see shorts_lab.py's identical LAB_ALLOC/LAB_LEV choice) --
NEWS_ALLOC = 0.15
NEWS_LEV = 20.0

# -- the validated rule's geometry, deployed verbatim ------------------
STOP_PCT = 1.2
TARGET_PCT = 2.4          # 2x the stop
MAX_HOLD_H = 24

SCAN_N = 40                # recent news rows pulled from the RPC each cycle
SEEN_CAP = 400              # rolling dedup window (headline TEXT, see above)


# ===========================================================================
# news source
# ===========================================================================

def _fetch_recent_news(n: int = SCAN_N) -> list[str]:
    """The RPC returns a plain newest-first list of headline strings — see
    the module docstring's REALITY CHECK. Monkeypatched wholesale by
    test_newsdesk_timing.py to inject fake headlines offline."""
    if not CLOUD_STATE:
        return []
    try:
        rows = _sb_rpc("cryptobot_recent_news", {"secret": _SB_SECRET, "n": n})
        return [r for r in (rows or []) if isinstance(r, str)]
    except Exception as e:
        print(f"  [NEWS] news RPC unreachable: {str(e)[:80]}")
        return []


def _is_watcherguru(headline: str) -> bool:
    """The ONLY source signal the feed actually carries: a literal
    '[WatcherGuru]' text prefix (see the module docstring)."""
    return (headline or "").strip().lower().startswith("[watcherguru]")


def _find_new_relevant(seen_headlines: list[str], headlines: list[str]):
    """Pure. `headlines` is the RPC's newest-first snapshot; `seen_headlines`
    is what we've already judged (any cycle, any verdict). Returns
    (chosen_or_None, updated_seen) — `chosen` is the chronologically FIRST
    (i.e. oldest-of-the-new-batch) new RELEVANT WatcherGuru headline;
    `updated_seen` marks EVERYTHING just scanned as seen either way (each
    headline is judged exactly once, matching the mandate). The caller
    decides whether to persist `updated_seen` — skipped entirely in dry
    mode so a preview run never marks anything as processed."""
    seen_set = set(seen_headlines)
    new_rows = [h for h in headlines if h not in seen_set]
    chosen = None
    for h in reversed(new_rows):          # oldest of the new batch first
        if _is_watcherguru(h) and classify_headline(h).get("relevant"):
            chosen = h
            break
    updated = list(seen_headlines)
    for h in headlines:
        if h not in seen_set:
            updated.append(h)
            seen_set.add(h)
    return chosen, updated[-SEEN_CAP:]


# ===========================================================================
# no-lookahead alignment (mirrors step45b_news_events.align_events)
# ===========================================================================

def _direction_bar_open_ts(event_ts: pd.Timestamp) -> pd.Timestamp:
    """event_ts floored to the hour == the FLOOR bar's open (the bar that
    was already live when the headline hit); +1h == the TRADING bar's own
    open — the first bar whose entire life is strictly after the event.
    Event 14:07 -> 15:00, the mandate's own worked example."""
    return pd.Timestamp(event_ts).floor("1h") + pd.Timedelta(hours=1)


def _resolve_direction(live_feed, direction_bar_open_ts: pd.Timestamp):
    """Look for the CLOSED 1h bar that opened at direction_bar_open_ts.
    live_feed.get_candles only ever returns confirmed/closed bars (see
    exchange.py), so if that timestamp appears at all, the bar is closed.
    Returns (direction, bar_open, bar_close); direction is None if the bar
    hasn't closed yet, 0 for a doji (no direction)."""
    candles = live_feed.get_candles(SYMBOL, "1h", 12)
    if candles is None or len(candles) == 0:
        return None, None, None
    match = candles[candles["timestamp"] == direction_bar_open_ts]
    if match.empty:
        return None, None, None
    row = match.iloc[-1]
    o, c = float(row["open"]), float(row["close"])
    if c > o:
        return 1, o, c
    if c < o:
        return -1, o, c
    return 0, o, c


def _parse_utc(s: str) -> pd.Timestamp:
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    return pd.Timestamp(dt)


def _fmt_utc(ts: pd.Timestamp) -> str:
    return f"{pd.Timestamp(ts):%Y-%m-%d %H:%M:%S} UTC"


# ===========================================================================
# bracket protection (hardened double-read, mirrors shorts_lab.py exactly,
# generalized to either direction since newsdesk trades both ways)
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
    """SELF-HEALING PROTECTION, identical hardening to shorts_lab.py's copy:
    read pending_tpsl TWICE 4s apart, only re-arm if BOTH reads come back
    empty AND a fresh net-position read confirms the position still
    exists. A read exception means 'don't know' — do nothing."""
    if not t or not t.get("sl_price"):
        return
    try:
        if _bracket_present(private, symbol, t):
            return
        time.sleep(4)
        if _bracket_present(private, symbol, t):
            return
        net = private.net_position_contracts(symbol)
        if abs(net) < LOT / 2:
            return
    except Exception as e:
        print(f"  [NEWS] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(symbol, close_side, t["contracts"],
                                     t.get("tp_price"), t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [NEWS] ⚠️ bracket was MISSING — re-armed SL "
              f"{t['sl_price']:,.1f}")
        notify("🛡️ Stop re-armed (demo)",
              f"The news trade's TP/SL had vanished — re-placed. "
              f"SL now back at ${t['sl_price']:,.0f}.")
    except Exception as e:
        print(f"  [NEWS] bracket re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ newsdesk UNPROTECTED (demo)",
              "bracket missing and re-arm failed — check BloFin now")


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    """Close the newsdesk's trade on its own ledger line. Direction-aware:
    profit on a rise when long, on a fall when short (mirrors
    shorts_lab.py's short-only math, generalized by t['direction'])."""
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", 6.0)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    state["newsdesk"]["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [NEWS] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "news_exit", "reason": reason,
               "trigger": "news_momentum", "direction": t["direction"],
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq, "headline": t.get("headline")})
    record_trade_outcome(state, "news_momentum", realized)
    write_lesson(state, "news_momentum", realized, t["entry_price"],
                exit_price, reason, t.get("ctx"))
    notify(f"📰 newsdesk {reason}: ${realized:+,.2f}",
          f"{side} news trade — ledger ${eq:,.2f} (demo)")
    return realized


# ===========================================================================
# main entrypoint
# ===========================================================================

def run_newsdesk(private: BlofinDemoPrivate, live_feed, demo_feed,
                 state: dict, dry: bool = False):
    """One cycle. Returns a small summary dict, mainly for tests/smoke."""
    nd = state.setdefault("newsdesk", {"open_trade": None, "pending": None,
                                       "last_event_ts": None,
                                       "seen_headlines": []})
    t = nd.get("open_trade")
    tag = " DRY" if dry else ""

    # -- reconcile (book-aware attribution, see book_ledger.py) -----------
    net = private.net_position_contracts(SYMBOL)
    attributed = attributed_position(net, state, "newsdesk")
    unexplained = unexplained_position(net, state)
    recorded_signed = (t["direction"] * t["contracts"]) if t else 0.0
    print(f"  [NEWS{tag}] reconcile: net={net:+.2f} attributed_news="
          f"{attributed:+.2f} (recorded {recorded_signed:+.1f}) "
          f"unexplained={unexplained:+.2f}")

    if t and abs(attributed) < LOT / 2:
        # our position is gone — a bracket fired (or someone closed it)
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
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
        print(f"  [NEWS{tag}] our {'long' if direction > 0 else 'short'} "
              f"is gone -> {reason} @ {exit_price:,.1f}")
        if dry:
            print("  [NEWS DRY] would cancel remaining bracket orders and "
                  "book this exit — no state/order changes made")
            return {"action": "would_exit", "reason": reason,
                    "exit_price": exit_price}
        _cleanup_orders(private, SYMBOL, t)
        _book_exit(state, t, exit_price, fee_bps, reason)
        t = None
    elif not t and abs(unexplained) > LOT / 2:
        # NOT ours to adopt — the shorts lab owns adoption of unexplained
        # positions (see shorts_lab.py); we only ever warn.
        print(f"  [NEWS{tag}] unexplained net {unexplained:+.2f} ct on the "
              f"exchange — NOT adopting (that's the shorts lab's job)")

    # -- open position: 24h time exit, else self-heal the bracket ---------
    if t:
        entry_dt = datetime.strptime(t["entry_time"], "%Y-%m-%d %H:%M:%S UTC")
        held_h = (datetime.now(timezone.utc)
                  - entry_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
        max_hold_h = t.get("max_hold_h", MAX_HOLD_H)
        if held_h >= max_hold_h:
            print(f"  [NEWS{tag}] {held_h:.0f}h >= {max_hold_h:.0f}h max "
                  f"hold -> closing")
            if dry:
                print(f"  [NEWS DRY] would market-cover {t['contracts']:.1f} "
                      f"ct now — no orders placed")
                return {"action": "would_time_exit", "contracts": t["contracts"]}
            _cleanup_orders(private, SYMBOL, t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(SYMBOL)
            ref_price = quote.bid if side == "sell" else quote.ask
            fill, was_maker = execute_maker_or_chase(
                private, demo_feed, SYMBOL, side, t["contracts"],
                ref_price, reduce_only=True)
            _book_exit(state, t, fill, 2.0 if was_maker else 6.0,
                      f"{max_hold_h:.0f}h time")
            return {"action": "time_exit", "fill": fill}
        if not dry:
            _ensure_bracket(private, SYMBOL, state, t)
        print(f"  [NEWS{tag}] holding {t['contracts']:.1f} ct "
              f"{'long' if t['direction'] > 0 else 'short'} from "
              f"{t['entry_price']:,.1f} ({held_h:.0f}h/{max_hold_h:.0f}h), "
              f"bracket verified")
        return {"action": "holding", "direction": t["direction"],
                "held_h": round(held_h, 1)}

    # -- pending: waiting for the direction bar to close -------------------
    pending = nd.get("pending")
    if pending:
        direction_bar_open_ts = _parse_utc(pending["direction_bar_open_ts"])
        direction, bar_open, bar_close = _resolve_direction(
            live_feed, direction_bar_open_ts)

        if direction is None:
            print(f"  [NEWS{tag}] pending on {pending['headline'][:60]!r} — "
                  f"waiting for the {direction_bar_open_ts:%m-%d %H:00} bar "
                  f"to close")
            return {"action": "pending", "headline": pending["headline"],
                    "direction_bar_open_ts": pending["direction_bar_open_ts"]}

        if direction == 0:
            print(f"  [NEWS{tag}] direction bar was a doji (open==close) — "
                  f"no direction, discarding pending")
            log_event({"action": "news_no_direction",
                       "headline": pending["headline"]})
            if not dry:
                nd["pending"] = None
                save_state(state)
            return {"action": "no_direction", "headline": pending["headline"]}

        # direction gate — news trades need NO champ gate (the backtest had
        # none); they must simply never physically oppose an existing net
        # position on the shared, netted exchange symbol.
        net = private.net_position_contracts(SYMBOL)   # re-read post-reconcile
        opposes = (direction > 0 and net <= -LOT / 2) or \
                  (direction < 0 and net >= LOT / 2)
        if opposes:
            msg = "news trade skipped — would oppose the ride"
            print(f"  [NEWS{tag}] {msg} (net {net:+.2f} ct, desired "
                  f"{'LONG' if direction > 0 else 'SHORT'})")
            log_event({"action": "news_skip_opposed", "net": net,
                       "direction": direction, "headline": pending["headline"]})
            if not dry:
                notify("📰 NEWSDESK skipped (demo)",
                      f"{msg} — exchange net {net:+.2f} ct. "
                      f"{pending['headline'][:100]}")
                nd["pending"] = None
                save_state(state)
            return {"action": "skipped_opposed", "net": net,
                    "direction": direction}

        notional = state["virtual_equity"] * NEWS_ALLOC * NEWS_LEV
        contracts = max(LOT, round(notional / bar_close / CONTRACT_BTC / LOT)
                        * LOT)
        side = "buy" if direction > 0 else "sell"

        if dry:
            if direction > 0:
                tp_est = round(bar_close * (1 + TARGET_PCT / 100), 1)
                sl_est = round(bar_close * (1 - STOP_PCT / 100), 1)
            else:
                tp_est = round(bar_close * (1 - TARGET_PCT / 100), 1)
                sl_est = round(bar_close * (1 + STOP_PCT / 100), 1)
            print(f"  [NEWS DRY] {'LONG' if direction > 0 else 'SHORT'} "
                  f"WOULD FIRE — {side} {contracts:.1f} ct (~${notional:,.0f} "
                  f"notional at {NEWS_LEV:.0f}x, {NEWS_ALLOC*100:.0f}% alloc) "
                  f"@ ~{bar_close:,.1f} | est TP {tp_est:,.1f} est SL "
                  f"{sl_est:,.1f} | max hold {MAX_HOLD_H}h — NO ORDER PLACED")
            return {"action": "would_enter", "direction": direction,
                    "contracts": contracts, "entry_ref": bar_close,
                    "est_tp": tp_est, "est_sl": sl_est,
                    "headline": pending["headline"]}

        print(f"  [NEWS ] {'LONG' if direction > 0 else 'SHORT'} SIGNAL "
              f"(news_momentum) — {side} {contracts:.1f} ct (~${notional:,.0f} "
              f"notional at {NEWS_LEV:.0f}x sleeve leverage)")
        private.ensure_leverage(SYMBOL, NEWS_LEV, "cross")
        try:
            entry, was_maker = execute_maker_or_chase(
                private, demo_feed, SYMBOL, side, contracts, bar_close)
        except Exception as e:
            print(f"  [NEWS ] ENTRY FAILED: {str(e)[:100]}")
            notify("⚠️ newsdesk ENTRY FAILED (demo)",
                  f"news_momentum tried to {side} but the order was "
                  f"rejected: {str(e)[:80]}. No position opened — check "
                  f"BloFin.")
            nd["pending"] = None
            save_state(state)
            return {"action": "entry_failed", "error": str(e)[:120]}

        if direction > 0:
            tp = round(entry * (1 + TARGET_PCT / 100), 1)
            sl = round(entry * (1 - STOP_PCT / 100), 1)
            close_side = "sell"
        else:
            tp = round(entry * (1 - TARGET_PCT / 100), 1)
            sl = round(entry * (1 + STOP_PCT / 100), 1)
            close_side = "buy"

        tpsl_id = None
        try:
            tpsl_id = private.place_tpsl(SYMBOL, close_side, contracts, tp, sl)
        except Exception as e:
            print(f"  [NEWS ] TP/SL bracket FAILED: {str(e)[:80]}")
            notify("⚠️ newsdesk bracket failed (demo)",
                  "position opened but TP/SL not set — check BloFin now")

        headline = pending["headline"]
        nd["open_trade"] = {
            "trigger": "news_momentum", "direction": direction,
            "contracts": contracts, "entry_price": entry,
            "entry_fee_bps": 2.0 if was_maker else 6.0,
            "entry_time": now_utc(), "tp_price": tp, "sl_price": sl,
            "tpsl_id": tpsl_id, "max_hold_h": MAX_HOLD_H,
            "headline": headline, "event_ts": pending["event_ts"],
            "ctx": {"news": headline},
        }
        nd["pending"] = None
        save_state(state)
        log_event({"action": "news_enter", "direction": direction,
                   "fill_price": entry, "contracts": contracts, "tp": tp,
                   "sl": sl, "maker": was_maker, "headline": headline})
        notify(f"📰 NEWSDESK {'LONG' if direction > 0 else 'SHORT'} (demo)",
              f"{side} {contracts:.1f} ct @{entry:,.0f} | TP {tp:,.0f} "
              f"SL {sl:,.0f} | 24h max hold | {headline[:100]}")
        return {"action": "entered", "direction": direction, "entry": entry,
               "contracts": contracts, "tp": tp, "sl": sl,
               "headline": headline}

    # -- no trade, no pending: scan the wire for a new event ---------------
    headlines = _fetch_recent_news()
    chosen, updated_seen = _find_new_relevant(nd.get("seen_headlines", []),
                                              headlines)

    if chosen:
        event_ts = now_utc()          # see the REALITY CHECK docstring note
        direction_bar_open_ts = _direction_bar_open_ts(_parse_utc(event_ts))
        print(f"  [NEWS{tag}] relevant WatcherGuru headline -> arming, "
              f"direction bar opens {direction_bar_open_ts:%m-%d %H:00}: "
              f"{chosen[:80]!r}")
        if dry:
            print("  [NEWS DRY] would set pending — no state changes made")
            return {"action": "would_arm", "headline": chosen}
        # persist BOTH the arm and the fact that everything scanned this
        # cycle (chosen or not) has now been judged once — one save covers
        # both, so a crash between them can never split them apart.
        nd["seen_headlines"] = updated_seen
        nd["last_event_ts"] = now_utc()
        nd["pending"] = {"event_ts": event_ts, "headline": chosen,
                         "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)}
        save_state(state)
        log_event({"action": "news_armed", "headline": chosen,
                   "event_ts": event_ts,
                   "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)})
        return {"action": "armed", "headline": chosen,
                "direction_bar_open_ts": _fmt_utc(direction_bar_open_ts)}

    print(f"  [NEWS{tag}] scanned {len(headlines)} recent rows — no new "
          f"relevant WatcherGuru headline")
    if not dry:
        # nothing armed, but everything scanned still gets marked seen so
        # it is never re-judged next cycle (must be persisted here — this
        # is the ONLY place that would otherwise happen for a no-event scan).
        nd["seen_headlines"] = updated_seen
        nd["last_event_ts"] = now_utc()
        save_state(state)
    return {"action": "no_event", "scanned": len(headlines)}
