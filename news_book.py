"""
news_book.py — THE NEWS-MOMENTUM PAPER BOOK (round 45B, forward test).

WHAT THIS IS
The first strategy in the whole program to pass a sealed out-of-sample test
(round 45B: A-news-momentum, first-bar-move, 1h, stop1.2%/tgt2.4%, hold24h,
TEST +$20.81/t x67, +13.9%, 52.2% win). One sealed pass is ENCOURAGING, NOT
PROVEN. Per the owner's own discipline — "you haven't proven yourself yet,
prove it on paper first" — this book forward-tests that exact setup on LIVE
news with SIMULATED money before a single real (even demo) order is ever
placed.

THE SETUP (identical to the sealed-test config)
  1. A NEW relevant headline appears on the live news wire (same relevance
     keywords as the backtest, step45b_news_events.classify_headline).
  2. Let the 1h bar the news landed in CLOSE. Read the sign of that bar's
     own move (close - open) — the market's first reaction. This is the
     "first_bar_move" direction; it beat reading the headline's wording,
     which FAILED the sealed test (kept here as a lesson, not a signal).
  3. Enter WITH that first-bar direction at the next bar. Stop 1.2%, target
     2.4% (2x), force flat after 24h. One position at a time.

WHY IT IS ISOLATED (and must stay that way)
This book places NO exchange orders. It keeps its own virtual equity and a
single simulated position in state["news_book"], marks it against the live
price every cycle, and books simulated PnL on stop/target/time. It therefore
CANNOT interact with the shared BloFin BTC-USDT net the way the real books
(ride/tact/lab) do — which is the entire point. For that same reason it is
deliberately NOT registered in book_ledger.recorded_book_positions: it owns
zero real contracts, and telling the real books otherwise would corrupt
THEIR attribution (the exact class of bug the 2026-07-23 incident was).
Promotion to a real demo book is a SEPARATE, reviewed step, only after this
paper book shows forward edge.

SIZING (documented so the scoreboard is interpretable)
Owner's 15-20x tier mandate: 20% of the ledger at 20x => 4x-equity notional.
A 1.2% adverse move is thus ~4.8% of equity. Fees modelled at 2bps/side maker
(the config's best-case, matching execution="maker" in the backtest). Equity,
win rate, and return% are all reported so the result reads at any sizing.
"""

from __future__ import annotations

from datetime import datetime, timezone

START_EQUITY = 10_000.0     # paper scoreboard base (matches backtest account)
STOP_PCT = 1.2              # % — the sealed-test config, under the 1.7% cap
TARGET_PCT = 2.4            # % — 2x the stop
MAX_HOLD_H = 24
LEDGER_FRAC = 0.20          # 20% of equity ...
LEVERAGE = 20.0             # ... at 20x  => 4x-equity notional
FEE_BPS_PER_SIDE = 2.0      # maker, both fills passive (best case)
TF = "1h"


def _now():
    return datetime.now(timezone.utc)


def _book(state: dict) -> dict:
    return state.setdefault("news_book", {
        "equity": START_EQUITY,
        "open_trade": None,      # {direction, entry_price, entry_time, stop, target}
        "pending": None,         # {arm_ref_ts, headline} — waiting for the bar to close
        "last_headline": None,   # newest headline string we've already reacted to
        "closed": [],            # recent booked trades (capped)
        "n": 0, "wins": 0,       # lifetime scoreboard
    })


def _classify(headline: str) -> dict:
    """Same relevance/tag logic as the backtest. Imported lazily so a self
    test can monkeypatch or run without the network stack."""
    from step45b_news_events import classify_headline
    return classify_headline(headline or "")


def _fee(notional: float) -> float:
    return notional * FEE_BPS_PER_SIDE / 10_000.0


def _notional(equity: float) -> float:
    return equity * LEDGER_FRAC * LEVERAGE


def _book_exit(nb: dict, exit_price: float, reason: str, log=None, notify=None):
    t = nb["open_trade"]
    notional = _notional_at_entry(t)
    move_frac = (exit_price - t["entry_price"]) / t["entry_price"] * t["direction"]
    gross = move_frac * notional
    fees = _fee(notional) * 2                      # entry + exit, maker both sides
    realized = round(gross - fees, 2)
    nb["equity"] = round(nb["equity"] + realized, 2)
    nb["n"] += 1
    nb["wins"] += 1 if realized > 0 else 0
    rec = {"closed_at": _now().isoformat(), "direction": t["direction"],
           "entry": t["entry_price"], "exit": round(exit_price, 2),
           "reason": reason, "pnl": realized, "equity": nb["equity"]}
    nb["closed"].append(rec)
    del nb["closed"][:-100]
    nb["open_trade"] = None
    acc = (nb["wins"] / nb["n"] * 100) if nb["n"] else 0.0
    line = (f"[NEWSBOOK] EXIT {reason}: {'LONG' if t['direction'] > 0 else 'SHORT'} "
            f"{t['entry_price']:,.1f}->{exit_price:,.1f} | pnl ${realized:+,.2f} | "
            f"equity ${nb['equity']:,.2f} | record {nb['wins']}/{nb['n']} = {acc:.0f}%")
    print("  " + line)
    if log:
        log({"action": "news_book_exit", **rec, "record": f"{nb['wins']}/{nb['n']}"})
    if notify and abs(realized) >= 0:
        pass  # exits are logged, not pushed — entries/milestones push (below)
    return realized


def _notional_at_entry(t: dict) -> float:
    # notional is frozen at entry so a mid-trade equity change can't rescale it
    return t.get("notional") or 0.0


def _enter(nb: dict, direction: int, price: float, headline: str,
           log=None, notify=None):
    notional = _notional(nb["equity"])
    stop = price * (1 - direction * STOP_PCT / 100.0)
    target = price * (1 + direction * TARGET_PCT / 100.0)
    nb["open_trade"] = {
        "direction": direction, "entry_price": round(price, 2),
        "entry_time": _now().isoformat(), "stop": round(stop, 2),
        "target": round(target, 2), "notional": round(notional, 2),
        "headline": headline[:180],
    }
    side = "LONG" if direction > 0 else "SHORT"
    line = (f"[NEWSBOOK] ENTER {side} @ {price:,.1f} (stop {stop:,.1f} / "
            f"tgt {target:,.1f}) on news: {headline[:80]!r}")
    print("  " + line)
    if log:
        log({"action": "news_book_entry", "direction": direction,
             "entry": round(price, 2), "stop": round(stop, 2),
             "target": round(target, 2), "headline": headline[:180]})
    if notify:
        notify("📰 news-book paper ENTER",
               f"{side} BTC @ ${price:,.0f} — {headline[:90]}")


def _manage_open(nb: dict, price: float, log=None, notify=None) -> bool:
    """Returns True if a trade was closed this call. Checks target, stop,
    then 24h max-hold, against the live price."""
    t = nb["open_trade"]
    d = t["direction"]
    # target / stop (intrabar order can't be known live — check both; target
    # first is the optimistic tie-break, matching a limit-tp resting order)
    if (d > 0 and price >= t["target"]) or (d < 0 and price <= t["target"]):
        _book_exit(nb, t["target"], "target", log, notify)
        return True
    if (d > 0 and price <= t["stop"]) or (d < 0 and price >= t["stop"]):
        _book_exit(nb, t["stop"], "stop", log, notify)
        return True
    entry_dt = datetime.fromisoformat(t["entry_time"])
    held_h = (_now() - entry_dt).total_seconds() / 3600.0
    if held_h >= MAX_HOLD_H:
        _book_exit(nb, price, "24h time", log, notify)
        return True
    return False


def news_book_cycle(live_feed, symbol, state, headlines=None,
                    log=None, notify=None):
    """One tick. Safe to call every hourly cycle (and on news wake-ups).

    live_feed : provides get_ticker(symbol).last and get_candles(symbol, tf, n).
    headlines : optional pre-fetched list (newest first); if None, pulled from
                the live wire. Passing it in is what makes this unit-testable.
    Returns the news_book dict (for inspection/tests).
    """
    nb = _book(state)

    # 1. mark any open position against the live price first.
    price = None
    if nb["open_trade"] is not None:
        price = live_feed.get_ticker(symbol).last
        _manage_open(nb, price, log, notify)

    # 2. detect a fresh relevant headline and ARM (only if flat & not armed).
    if headlines is None:
        headlines = _fetch_headlines()
    newest = headlines[0] if headlines else None
    if (newest and newest != nb["last_headline"]
            and nb["open_trade"] is None and nb["pending"] is None):
        nb["last_headline"] = newest
        if _classify(newest).get("relevant"):
            candles = live_feed.get_candles(symbol, TF, 3)
            arm_ref_ts = str(candles["timestamp"].iloc[-1])
            nb["pending"] = {"arm_ref_ts": arm_ref_ts, "headline": newest}
            print(f"  [NEWSBOOK] ARMED on relevant news, waiting for the "
                  f"{TF} bar to close: {newest[:80]!r}")
        else:
            print(f"  [NEWSBOOK] news not BTC-relevant, ignored: {newest[:60]!r}")
    elif newest and newest != nb["last_headline"]:
        # still record we've seen it so we don't re-evaluate it forever
        nb["last_headline"] = newest

    # 3. if armed and the news bar has now CLOSED, read its move and enter.
    if nb["pending"] is not None and nb["open_trade"] is None:
        candles = live_feed.get_candles(symbol, TF, 3)
        last_ts = str(candles["timestamp"].iloc[-1])
        if last_ts != nb["pending"]["arm_ref_ts"]:
            o = float(candles["open"].iloc[-1])
            c = float(candles["close"].iloc[-1])
            direction = 1 if c > o else (-1 if c < o else 0)
            headline = nb["pending"]["headline"]
            nb["pending"] = None
            if direction == 0:
                print("  [NEWSBOOK] first post-news bar was flat — no entry.")
            else:
                if price is None:
                    price = live_feed.get_ticker(symbol).last
                _enter(nb, direction, price, headline, log, notify)

    return nb


def _fetch_headlines(n=6):
    from step5_paper_trade import CLOUD_STATE, _SB_SECRET, _sb_rpc
    if not CLOUD_STATE:
        return []
    try:
        return _sb_rpc("cryptobot_recent_news", {"secret": _SB_SECRET, "n": n}) or []
    except Exception:
        return []


# ---------------------------------------------------------------------------
# self-test — proves the state machine with a fake feed, NO network, NO orders
# ---------------------------------------------------------------------------

def _selftest():
    import pandas as pd

    class FakeFeed:
        def __init__(self):
            self.price = 100_000.0
            self._bar_ts = "2026-07-23T18:00:00+00:00"
            self._o, self._c = 100_000.0, 100_000.0

        class _Tick:
            def __init__(self, last): self.last = last

        def get_ticker(self, symbol):
            return self._Tick(self.price)

        def get_candles(self, symbol, tf, n):
            return pd.DataFrame({"timestamp": [self._bar_ts],
                                 "open": [self._o], "close": [self._c]})

        def close_bar(self, ts, o, c):
            self._bar_ts, self._o, self._c = ts, o, c

    state = {}
    feed = FakeFeed()
    events = []
    log = events.append

    # tick 1: a relevant bullish headline arrives -> should ARM, not enter
    news_book_cycle(feed, "BTC-USDT", state,
                    headlines=["Bitcoin ETF sees record net inflows"], log=log)
    nb = state["news_book"]
    assert nb["pending"] is not None, "should be armed"
    assert nb["open_trade"] is None, "must NOT enter before the bar closes"

    # tick 2: the news bar closes UP (100000 -> 100800). same headline.
    feed.close_bar("2026-07-23T19:00:00+00:00", 100_000.0, 100_800.0)
    feed.price = 100_800.0
    news_book_cycle(feed, "BTC-USDT", state,
                    headlines=["Bitcoin ETF sees record net inflows"], log=log)
    nb = state["news_book"]
    assert nb["pending"] is None, "pending should clear after entry"
    assert nb["open_trade"] is not None, "should have entered"
    assert nb["open_trade"]["direction"] == 1, "up bar -> LONG"
    exp_stop = round(100_800.0 * (1 - 1.2 / 100), 2)
    assert nb["open_trade"]["stop"] == exp_stop, "stop 1.2% below entry"

    # tick 3: price rips to target (2.4% up) -> should BOOK a win
    feed.price = 100_800.0 * (1 + 2.4 / 100)
    news_book_cycle(feed, "BTC-USDT", state, headlines=[], log=log)
    nb = state["news_book"]
    assert nb["open_trade"] is None, "target should have closed it"
    assert nb["n"] == 1 and nb["wins"] == 1, "one win booked"
    assert nb["equity"] > START_EQUITY, "equity should rise on a win"

    # tick 4: an IRRELEVANT headline -> ignored, no arm
    news_book_cycle(feed, "BTC-USDT", state,
                    headlines=["Local bakery wins pie contest"], log=log)
    assert state["news_book"]["pending"] is None, "irrelevant news must not arm"

    # tick 5: relevant bearish-context headline, bar closes DOWN -> SHORT,
    #         then price hits the stop -> booked loss
    news_book_cycle(feed, "BTC-USDT", state,
                    headlines=["SEC lawsuit against major exchange"], log=log)
    feed.close_bar("2026-07-23T20:00:00+00:00", 103_000.0, 102_000.0)
    feed.price = 102_000.0
    news_book_cycle(feed, "BTC-USDT", state,
                    headlines=["SEC lawsuit against major exchange"], log=log)
    nb = state["news_book"]
    assert nb["open_trade"]["direction"] == -1, "down bar -> SHORT"
    feed.price = nb["open_trade"]["stop"] + 1  # short stop is ABOVE entry
    feed.price = nb["open_trade"]["stop"]
    news_book_cycle(feed, "BTC-USDT", state, headlines=[], log=log)
    nb = state["news_book"]
    assert nb["open_trade"] is None and nb["n"] == 2, "loss booked"

    print(f"SELFTEST OK — {nb['n']} paper trades, {nb['wins']} wins, "
          f"equity ${nb['equity']:,.2f}, {len(events)} events logged")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print("news_book.py — import news_book_cycle(live_feed, symbol, state). "
              "Run with --selftest to exercise the state machine offline.")
