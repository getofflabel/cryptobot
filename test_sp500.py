"""
test_sp500.py — offline tests for sp500.py (THE S&P BOT).

Run with:  python3 test_sp500.py

NO NETWORK, NO ORDERS. Everything that would normally touch Alpaca,
Supabase, Telegram or ntfy is replaced with an in-memory fake, the same
discipline test_bitcoin.py / test_diver.py use:
  - FakeVenue stands in for alpaca.AlpacaPaper. It never makes an HTTP
    call and it records every order it is asked to place, so a test can
    assert what did — and much more importantly what did NOT — happen.
  - notify / log_event / save_state are neutralised on BOTH sp500 and
    step5_paper_trade, so a run can never ping a phone, write the real
    state or reach the cloud.
  - The memory loop is pointed at paths that do not exist, so no test
    depends on whatever the repo's real data/ledger.csv holds today. The
    one test that exercises the file reading passes real paths itself,
    inside a temporary directory.

THE PRICE FIXTURES ARE REAL FRAMES ON REAL SESSION DATES. build_frame()
lays prices on actual New York Stock Exchange sessions (weekends and
holidays removed), because the turn-of-month rule counts SESSIONS, not
calendar days, and a fixture on calendar days would silently test a
different rule from the one that was validated.
"""

from __future__ import annotations

import inspect
import os
import re
import sys
import tempfile
import traceback
from datetime import date, timedelta

import numpy as np
import pandas as pd

import sp500 as S
import step5_paper_trade as s5
from strategy import rsi

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# neutralise every side effect, on BOTH modules
# ---------------------------------------------------------------------------

def _noop(*_a, **_kw):
    pass


S.notify = _noop
S.log_event = _noop
S.save_state = _noop
s5.notify = _noop
s5.log_event = _noop
s5.save_state = _noop

# HERMETIC MEMORY: run_sp500 resolves these at CALL time, so pointing them
# at nothing makes every test depend only on the state it built itself.
S.LEDGER_CSV = "no/such/ledger.csv"
S.LEARNINGS_MD = "no/such/learnings.md"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def sessions_ending(end_day: date, n: int) -> list:
    """The last `n` real trading sessions up to and including end_day."""
    all_days = S._computed_sessions(end_day - timedelta(days=int(n * 1.6)),
                                    end_day)
    return all_days[-n:]


def build_frame(end_day: date, n: int = 420, seed: int = 7,
                drop: tuple | None = None, mu: float = 0.30) -> pd.DataFrame:
    """A daily frame ending at `end_day`, laid on REAL trading sessions.

    A rising drift keeps the close above its 200-day average (both rules
    sit inside that filter), and two sine wobbles put real swing lows on
    the chart so the structure stop has something to rest on. `drop`
    multiplies the last few closes down off the bar before them, which is
    how the deep-dip fixture is made."""
    days = sessions_ending(end_day, n)
    m = len(days)
    rng = np.random.default_rng(seed)
    drift = np.cumsum(np.abs(rng.normal(mu, 0.10, m)))
    wobble = np.sin(np.arange(m) / 5.0) * 4.0 + np.sin(np.arange(m) / 17.0) * 7.0
    c = 300.0 + drift + wobble
    if drop:
        base = c[-len(drop) - 1]
        for j, f in enumerate(drop):
            c[-len(drop) + j] = base * f
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({
        "timestamp": pd.to_datetime([str(d) for d in days]).tz_localize(
            "America/New_York"),
        "day": days,
        "open": o, "high": np.maximum(o, c) * 1.004,
        "low": np.minimum(o, c) * 0.996, "close": c,
        "volume": np.ones(m)})


# The deep-dip fixture's drop: three hard down closes off a rising market,
# which puts the 2-day strength gauge at about 2.4 — under the rule's
# threshold of 5 — while the close is still above its 200-day average.
DIP_DROP = (0.985, 0.970, 0.958)

# The turn-of-month signal day. On the real 2026 calendar Monday
# 2026-07-27 is the session with exactly FOUR trading sessions still to
# come in July (28, 29, 30, 31), which is round 362's own definition
# (step362_spx_round2.month_position: days_left == E). The buy therefore
# fills at the open of Tuesday 2026-07-28.
TOM_SIGNAL_DAY = date(2026, 7, 27)
TOM_ENTRY_SESSION = date(2026, 7, 28)
QUIET_DAY = date(2026, 7, 15)         # mid-month: turn-of-month cannot fire


class FakeVenue:
    """Stands in for alpaca.AlpacaPaper. Records orders, never sends one.

    Deliberately has NO `calendar` method and no `_get`, which is exactly
    the shape alpaca.py has today — so these tests exercise the computed
    New York Stock Exchange fallback, the code path that runs in
    production right now. FakeVenueWithCalendar covers the other branch."""

    def __init__(self, frame: pd.DataFrame, session_date: date,
                 is_open: bool = True, equity: float = 100_000.0,
                 buying_power: float = 200_000.0, position: dict | None = None,
                 clock_raises: bool = False, live_price: float | None = None,
                 serve_partial_bar: bool = True):
        self.frame = frame
        self.session_date = session_date
        self.is_open = is_open
        self.equity = equity
        self.buying_power = buying_power
        self._position = position
        self.clock_raises = clock_raises
        self.serve_partial_bar = serve_partial_bar
        self.live = (live_price if live_price is not None
                     else float(frame["close"].iloc[-1]))
        self.orders: list[dict] = []
        self.bar_requests: list[dict] = []

    # -- reads --------------------------------------------------------------

    def account(self):
        return {"equity": str(self.equity),
                "buying_power": str(self.buying_power),
                "cash": str(self.equity), "status": "ACTIVE"}

    def clock(self):
        if self.clock_raises:
            raise RuntimeError("alpaca /v2/clock -> 503 upstream")
        sd = self.session_date
        if self.is_open:
            ts = f"{sd}T10:00:00-04:00"
            nxt = f"{sd + timedelta(days=1)}T09:30:00-04:00"
        else:
            ts = f"{sd - timedelta(days=1)}T18:00:00-04:00"
            nxt = f"{sd}T09:30:00-04:00"
        return {"is_open": self.is_open, "timestamp": ts, "next_open": nxt,
                "next_close": f"{sd}T16:00:00-04:00"}

    def position(self, symbol):
        return self._position

    def positions(self):
        return [self._position] if self._position else []

    def bars(self, symbol, timeframe="1Day", limit=1000, start=None):
        self.bar_requests.append({"timeframe": timeframe, "limit": limit,
                                  "start": start})
        if start is None:
            # VERIFIED LIVE 2026-07-25: Alpaca answers a daily-bar request
            # with no start date with "bars": null. Not an error, not an
            # empty list — null. The fake reproduces that exactly, so a
            # future edit that drops the start date fails HERE instead of
            # silently reading as "no history at all" on the real venue.
            return []
        out = []
        for _, r in self.frame.iterrows():
            out.append({"t": r["timestamp"].isoformat(), "o": float(r["open"]),
                        "h": float(r["high"]), "l": float(r["low"]),
                        "c": float(r["close"]), "v": float(r["volume"])})
        if self.serve_partial_bar:
            # Alpaca really does serve TODAY'S still-forming bar during the
            # session. It carries a deliberately absurd close so any test
            # that accidentally acts on it fails loudly.
            out.append({"t": f"{self.session_date}T00:00:00-04:00",
                        "o": 9_999.0, "h": 9_999.0, "l": 9_999.0,
                        "c": 9_999.0, "v": 1.0})
        return out[-limit:]

    def last_trade(self, symbol):
        return {"p": self.live}

    # -- the only write, and it is never actually sent anywhere -------------

    def market_order(self, symbol, side, qty, client_order_id=None):
        self.orders.append({"symbol": symbol, "side": side, "qty": float(qty),
                            "client_order_id": client_order_id})
        return {"id": f"fake-{len(self.orders)}",
                "client_order_id": client_order_id, "status": "accepted",
                "filled_avg_price": None}

    def close_position(self, symbol):
        raise AssertionError("sp500.py must never call close_position — every "
                             "order goes through send_market_order so it "
                             "carries the CBOT_ tag")


class FakeVenueWithCalendar(FakeVenue):
    """A venue that DOES answer with its own session calendar, so the
    'ask the venue first' branch of venue_sessions is exercised too."""

    def calendar(self, start, end):
        s = date.fromisoformat(str(start)[:10])
        e = date.fromisoformat(str(end)[:10])
        return [{"date": str(d), "open": "09:30", "close": "16:00"}
                for d in S._computed_sessions(s, e)]


def make_state(open_trade=None, last_bar_day=None, trades=None,
               rules_stood_down=None) -> dict:
    return {"virtual_equity": 100_000.0, "goal": 200_000.0, "lessons": [],
            S.STATE_KEY: {"open_trade": open_trade,
                          "last_bar_day": last_bar_day,
                          "trades": list(trades or []),
                          "realized_pnl_total": 0.0,
                          "rules_stood_down": dict(rules_stood_down or {}),
                          "stand_down_history": [], "deferred": None}}


def closed_trade(when: str, rule: str, reason: str, pnl: float) -> dict:
    return {"rule": rule, "entry_time": when, "entry_price": 400.0,
            "qty": 10.0, "exit_price": 390.0, "pnl": pnl, "reason": reason,
            "exit_time": when}


def held_tom_trade(entry_session: date, stop: float = 350.0,
                   entry_price: float = 410.0, qty: float = 20.0) -> dict:
    return {"rule": "turn_of_month", "direction": 1, "qty": qty,
            "entry_price": entry_price, "entry_time": "2026-07-28 13:35:00 UTC",
            "entry_session": str(entry_session), "stop_level": stop,
            "anchor_swing": stop, "fallback_pct_of_price": 4.24,
            "stop_distance_pct_of_price": 14.6, "leverage_at_entry": 0.5,
            "planned_sessions": S.TOM_HOLD_SESSIONS, "memory_at_entry": {},
            "client_order_id": "CBOT_SPY_turnofmonth_buy_x_001"}


# ---------------------------------------------------------------------------
# (a) turn-of-month fires when it should, and not when it should not
# ---------------------------------------------------------------------------

def test_a_turn_of_month_fires_only_on_its_own_session():
    d = build_frame(TOM_SIGNAL_DAY)

    # the fixture really is the validated setup: four sessions left in the
    # month, price above its 200-day average
    sess = S._computed_sessions(date(2026, 6, 1), date(2026, 8, 31))
    assert S.trading_days_left_in_month(TOM_SIGNAL_DAY, sess) == \
        S.TOM_DAYS_BEFORE_MONTH_END
    close = float(d["close"].iloc[-1])
    assert close > float(d["close"].rolling(S.TREND_SMA).mean().iloc[-1])

    sig = S.rule_turn_of_month(d, {"trading_days_left_in_month": 4})
    assert sig is not None and sig.rule == "turn_of_month"
    assert sig.direction == 1
    assert sig.stop_level < close, "a long's stop must sit below the entry"
    assert sig.context["hold_sessions"] == S.TOM_HOLD_SESSIONS == 8
    assert S.TOM_DAYS_BEFORE_MONTH_END == 4, \
        "E and H are step362_results.md's own pair and are not re-tuned here"

    # wrong day in the month: nothing
    for left in (0, 1, 2, 3, 5, 6, 12):
        assert S.rule_turn_of_month(d, {"trading_days_left_in_month": left}) \
            is None, f"turn-of-month must not fire with {left} sessions left"

    # the calendar could not be counted -> no signal, never a guess
    assert S.rule_turn_of_month(d, {"trading_days_left_in_month": None}) is None
    assert S.rule_turn_of_month(d, {}) is None

    # below the 200-day average: the filter blocks it even on the right day
    falling = d.copy()
    falling.loc[falling.index[-1], "close"] = float(
        falling["close"].rolling(S.TREND_SMA).mean().iloc[-1]) - 5.0
    assert S.rule_turn_of_month(falling,
                                {"trading_days_left_in_month": 4}) is None


# ---------------------------------------------------------------------------
# (b) the deep-dip buy fires on a real dip, not otherwise, and is SPY only
# ---------------------------------------------------------------------------

def test_b_dip_buy_fires_only_on_a_deep_dip_and_only_on_spy():
    d = build_frame(QUIET_DAY, drop=DIP_DROP)
    close = float(d["close"].iloc[-1])
    r = float(rsi(d["close"], S.RSI_LEN).iloc[-1])
    assert r < S.RSI_BUY_BELOW, f"the dip fixture must be deep, gauge was {r}"
    assert close > float(d["close"].rolling(S.TREND_SMA).mean().iloc[-1])

    sig = S.rule_rsi2_dip_buy(d, {"symbol": "SPY"})
    assert sig is not None and sig.rule == "rsi2_dip_buy"
    assert sig.stop_level < close

    # SPY ONLY. Round 362 placed the futures version 78.5th out of 100
    # against a coin flip, so this rule must refuse to travel.
    for other in ("QQQ", "ES", "SPXL", "spy_futures"):
        assert S.rule_rsi2_dip_buy(d, {"symbol": other}) is None, \
            f"the dip-buy must not fire on {other} — it is SPY only"

    # a quiet market: no dip, no trade
    quiet = build_frame(QUIET_DAY)
    assert float(rsi(quiet["close"], S.RSI_LEN).iloc[-1]) >= S.RSI_BUY_BELOW
    assert S.rule_rsi2_dip_buy(quiet, {"symbol": "SPY"}) is None

    # the same dip BELOW the 200-day average is refused by the filter
    below = d.copy()
    below.loc[below.index[-1], "close"] = float(
        below["close"].rolling(S.TREND_SMA).mean().iloc[-1]) - 1.0
    assert S.rule_rsi2_dip_buy(below, {"symbol": "SPY"}) is None

    # the exit is round 60's, unchanged
    assert S.RSI_EXIT_ABOVE == 65.0 and S.DIP_EXIT_SMA == 5


# ---------------------------------------------------------------------------
# (c) the market-hours check refuses to send outside the session
# ---------------------------------------------------------------------------

def test_c_market_hours_check_refuses_to_send_when_shut():
    d = build_frame(TOM_SIGNAL_DAY)

    # -- c1: the gate reads the clock and reports the session it would act in
    open_venue = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
    g = S.market_gate(open_venue)
    assert g["open"] is True and g["session_date"] == TOM_ENTRY_SESSION

    shut_venue = FakeVenue(d, TOM_ENTRY_SESSION, is_open=False)
    g_shut = S.market_gate(shut_venue)
    assert g_shut["open"] is False
    assert g_shut["session_date"] == TOM_ENTRY_SESSION, \
        "with the market shut the bot acts in the session that opens NEXT"

    # -- c2: A CLOCK THAT CANNOT BE READ COUNTS AS SHUT
    broken = FakeVenue(d, TOM_ENTRY_SESSION, clock_raises=True)
    g_broken = S.market_gate(broken)
    assert g_broken["open"] is False and g_broken["clock_ok"] is False
    assert "not knowing" in g_broken["why"]

    # -- c3: send_market_order REFUSES rather than letting Alpaca reject it
    for bad in (g_shut, g_broken):
        try:
            S.send_market_order(shut_venue, "buy", 10.0, "turn_of_month", bad)
            raise AssertionError("an order was sent with the market shut")
        except S.MarketClosed:
            pass
    assert not shut_venue.orders and not broken.orders

    # and it DOES send when the session is open
    o = S.send_market_order(open_venue, "buy", 10.0, "turn_of_month", g)
    assert len(open_venue.orders) == 1
    assert open_venue.orders[0]["side"] == "buy"
    assert o["client_order_id"].startswith("CBOT_")

    # -- c4: there is exactly ONE door to the venue in the whole file
    src = open(os.path.join(HERE, "sp500.py")).read()
    calls = re.findall(r"\.market_order\(", src)
    assert len(calls) == 1, \
        f"every order must go through send_market_order; found {len(calls)} " \
        f"direct market_order calls"
    assert ".close_position(" not in src, \
        "close_position cannot carry a client order id, so it must not be used"

    # -- c5: a whole cycle with the market shut sends NOTHING
    S.NEW_ENTRIES_ENABLED = True
    try:
        v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=False)
        st = make_state()
        r = S.run_sp500(v, st)
        assert r["action"] == "deferred_market_shut", r
        assert r["kind"] == "entry" and r["rule"] == "turn_of_month"
        assert not v.orders, "no order may leave the file with the market shut"
        # AND the bar is NOT marked processed, or the trade would be lost
        assert st[S.STATE_KEY]["last_bar_day"] is None, \
            "a deferred decision must not mark the bar processed"
        assert st[S.STATE_KEY]["deferred"]["kind"] == "entry"

        # the next cycle, inside the session, takes it
        v2 = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
        r2 = S.run_sp500(v2, st)
        assert r2["action"] == "entered", r2
        assert len(v2.orders) == 1 and v2.orders[0]["side"] == "buy"
    finally:
        S.NEW_ENTRIES_ENABLED = False


# ---------------------------------------------------------------------------
# (d) the stop is chart structure, per trade — never a fixed percentage
# ---------------------------------------------------------------------------

def test_d_the_stop_is_per_trade_structure_not_a_fixed_percentage():
    d_tom = build_frame(TOM_SIGNAL_DAY)
    d_dip = build_frame(QUIET_DAY, drop=DIP_DROP)

    tom = S.rule_turn_of_month(d_tom, {"trading_days_left_in_month": 4})
    dip = S.rule_rsi2_dip_buy(d_dip, {"symbol": "SPY"})
    assert tom is not None and dip is not None

    def distance_pct(sig, frame):
        c = float(frame["close"].iloc[-1])
        return (c - sig.stop_level) / c * 100.0

    a, b = distance_pct(tom, d_tom), distance_pct(dip, d_dip)
    assert a > 0 and b > 0
    assert abs(a - b) > 0.25, (
        f"two entries produced the same stop distance ({a:.2f}% and "
        f"{b:.2f}% of price) — that is a swept percentage, not structure")

    # the stop IS the confirmed swing low the entry rests on
    i = len(d_tom) - 1
    swing = S.anchor_swing(d_tom, i, float(d_tom["close"].iloc[i]))
    assert swing is not None
    assert abs(tom.stop_level - swing) < 1e-6, (tom.stop_level, swing)
    assert tom.context["anchor_swing"] == swing

    # the stop does NOT move once the trade is on — round 362 measured a
    # level fixed at entry, not bitcoin.py's ratcheting floor
    for later in range(i - 20, i + 1):
        lvl, _ = S.structure_stop(d_tom.iloc[:later + 1].reset_index(drop=True),
                                  min(i - 20, later),
                                  float(d_tom["close"].iloc[i - 20]), 4.24)
        assert lvl > 0

    # with no confirmed swing under the entry, the fallback is the measured
    # middle distance for that rule, not an invented number
    rising = build_frame(TOM_SIGNAL_DAY, n=260, seed=3)
    entry = float(rising["low"].min()) * 0.5     # below every swing on record
    lvl, sw = S.structure_stop(rising, len(rising) - 1, entry,
                               S.FALLBACK_STOP_PCT_TOM)
    assert sw is None
    assert abs(lvl - entry * (1 - S.FALLBACK_STOP_PCT_TOM / 100)) < 1e-9
    assert S.FALLBACK_STOP_PCT_DIP == 2.26 and S.FALLBACK_STOP_PCT_TOM == 4.24

    # THE STOP IS NOT ALLOWED TO BE RE-TIGHTENED. Round 60 killed a ~1.3%
    # of price stop; these are structure distances and the file says so.
    src = open(os.path.join(HERE, "sp500.py")).read()
    assert "DO NOT RE-TIGHTEN" in src
    assert "1.3% of price" in src


# ---------------------------------------------------------------------------
# (e) the size comes from the stop, and leverage is an output
# ---------------------------------------------------------------------------

def test_e_size_comes_from_the_stop():
    equity, bp, price = 100_000.0, 200_000.0, 400.0

    # round 362's own measured middle stop distances with the 5-bar swings
    # this file uses: 2.26% of price for the dip-buy, 4.24% for turn-of-month
    tight = S.size_from_risk(equity, bp, price, 400.0 * (1 - 0.0226))
    wide = S.size_from_risk(equity, bp, price, 400.0 * (1 - 0.0424))

    # the dollars at risk are the same; only the share count changes
    assert abs(tight["risk_usd"] - equity * S.RISK_PCT / 100) < 1e-6
    assert abs(wide["risk_usd"] - tight["risk_usd"]) < 1e-6
    assert wide["qty"] < tight["qty"], \
        "a wider stop must buy FEWER shares for the same dollars risked"

    # size really is dollars risked / stop distance
    expected = tight["risk_usd"] / (price - 400.0 * (1 - 0.0226))
    assert abs(tight["qty"] - expected) < 0.01, (tight["qty"], expected)
    assert tight["capped_by"] is None, \
        "neither cap should bind at round 362's own measured distances"

    # leverage is an OUTPUT and lands where round 362 said it would:
    # about 0.9 times the account for the dip-buy, 0.5 for turn-of-month,
    # both UNDER 1x, so this bot never borrows
    assert 0.8 < tight["leverage"] < 1.0, tight["leverage"]
    assert 0.4 < wide["leverage"] < 0.6, wide["leverage"]

    # the caps SHRINK the position, they never widen the risk budget
    tiny_stop = S.size_from_risk(equity, bp, price, price * 0.999)
    assert tiny_stop["notional"] <= equity + 1e-6
    assert tiny_stop["capped_by"] and "never borrows" in tiny_stop["capped_by"]
    assert abs(tiny_stop["risk_usd"] - equity * S.RISK_PCT / 100) < 1e-6

    poor = S.size_from_risk(equity, 1_000.0, price, price * 0.98)
    assert poor["notional"] <= 1_000.0 + 1e-6
    assert "buying power" in (poor["capped_by"] or "")

    # fractional shares, rounded DOWN so the risk budget is never overspent
    assert abs(tight["qty"] * 1000 - round(tight["qty"] * 1000)) < 1e-6
    assert tight["qty"] <= expected + 1e-9

    # a nonsense stop buys nothing rather than something enormous
    assert S.size_from_risk(equity, bp, price, price)["qty"] == 0.0
    assert S.size_from_risk(equity, bp, price, price * 1.1)["qty"] == 0.0


# ---------------------------------------------------------------------------
# (f) the position is HELD ACROSS NIGHTS — the whole edge depends on it
# ---------------------------------------------------------------------------

def test_f_the_position_is_held_across_nights():
    """Round 370 measured the turn-of-month lift at +0.0468% of price in
    the closed hours against +0.0176% of price inside the session. So the
    bot must sit through the close, the night, the weekend and a holiday,
    and only come out when the 8-session hold is complete."""
    # entered at the open of 2026-07-28; the 8-session hold ends at the
    # open of 2026-08-07, so every session before that must be a HOLD.
    for decision_day, session_day in ((date(2026, 7, 28), date(2026, 7, 29)),
                                      (date(2026, 7, 30), date(2026, 7, 31)),
                                      (date(2026, 7, 31), date(2026, 8, 3)),
                                      (date(2026, 8, 5), date(2026, 8, 6))):
        d = build_frame(decision_day)
        t = held_tom_trade(TOM_ENTRY_SESSION)
        st = make_state(open_trade=t)
        for is_open in (True, False):
            v = FakeVenue(d, session_day, is_open=is_open,
                          position={"qty": "20", "avg_entry_price": "410",
                                    "market_value": "8300",
                                    "unrealized_pl": "100", "side": "long"})
            r = S.run_sp500(v, st)
            assert r["action"] == "hold", (decision_day, session_day, is_open, r)
            assert not v.orders, \
                "nothing may be sold before the hold is complete — closing " \
                "at the bell throws away the overnight edge"
            assert st[S.STATE_KEY]["open_trade"] is not None
        # the weekend costs the trade no sessions: Friday to Monday is one
        assert r["sessions_held"] < S.TOM_HOLD_SESSIONS

    # Friday -> Monday really is ONE session, not three days
    sess = S._computed_sessions(date(2026, 7, 1), date(2026, 8, 31))
    assert S.sessions_between(date(2026, 7, 31), date(2026, 8, 3), sess) == 1
    # and a holiday is skipped too: 2026-07-03 is the observed Independence
    # Day holiday, so 2026-07-02 to 2026-07-06 is one session
    assert date(2026, 7, 3) in S.us_market_holidays(2026)
    assert S.sessions_between(date(2026, 7, 2), date(2026, 7, 6), sess) == 1

    # the 8th session: NOW it comes out
    d = build_frame(date(2026, 8, 6))
    st = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION))
    v = FakeVenue(d, date(2026, 8, 7), is_open=True,
                  position={"qty": "20", "avg_entry_price": "410",
                            "market_value": "8300", "unrealized_pl": "100",
                            "side": "long"})
    r = S.run_sp500(v, st)
    assert r["action"] == "exited" and r["reason"] == "held_the_planned_sessions"
    assert r["sessions_held"] == S.TOM_HOLD_SESSIONS
    assert len(v.orders) == 1 and v.orders[0]["side"] == "sell"

    # NOTHING IN THIS FILE FLATTENS AT A TIME OF DAY. If any of these ever
    # appears, the overnight edge has been engineered out of the bot.
    src = open(os.path.join(HERE, "sp500.py")).read().lower()
    for banned in ("before the close", "flatten_at_close", "eod_flat",
                   "close_before_bell", "next_close", "intraday exit"):
        assert banned not in src, \
            f"'{banned}' appears in sp500.py — the edge lives overnight"


# ---------------------------------------------------------------------------
# (g) exits reconcile against the venue
# ---------------------------------------------------------------------------

def test_g_exits_reconcile_against_the_venue():
    d = build_frame(date(2026, 7, 30))

    # -- g1: the venue shows no position but the bot had one recorded ->
    #        the record is closed and a lesson is written
    st = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION))
    v = FakeVenue(d, date(2026, 7, 31), is_open=True, position=None,
                  live_price=415.0)
    r = S.run_sp500(v, st)
    assert r["action"] == "reconciled_exit", r
    assert r["reason"] == "position_gone_at_venue"
    assert st[S.STATE_KEY]["open_trade"] is None
    assert st["lessons"], "a reconciled close still writes its lesson"
    assert not v.orders, "reconciling must not send an order"

    # -- g2: the entry price converges on the VENUE'S own average entry,
    #        because Alpaca does not return a fill price on a market order
    t = held_tom_trade(TOM_ENTRY_SESSION, entry_price=410.0)
    st2 = make_state(open_trade=t)
    v2 = FakeVenue(d, date(2026, 7, 31), is_open=True,
                   position={"qty": "20", "avg_entry_price": "411.37",
                             "market_value": "8300", "unrealized_pl": "1",
                             "side": "long"})
    S.run_sp500(v2, st2)
    assert abs(st2[S.STATE_KEY]["open_trade"]["entry_price"] - 411.37) < 1e-6

    # -- g3: a position the bot did not open is NOT adopted and NOT
    #        flattened. The account has had zero orders ever, so anything
    #        here that this file did not open belongs to a human.
    st3 = make_state()
    v3 = FakeVenue(d, date(2026, 7, 31), is_open=True,
                   position={"qty": "5", "avg_entry_price": "400",
                             "market_value": "2000", "unrealized_pl": "0",
                             "side": "long"})
    r3 = S.run_sp500(v3, st3)
    assert not v3.orders, "an unclaimed position must never be traded against"
    assert st3[S.STATE_KEY]["open_trade"] is None
    assert st3[S.STATE_KEY].get("unclaimed_alerted") is True
    assert r3["action"] in ("no_signal", "stand_down", "stood_down",
                            "deferred_market_shut"), r3

    # -- g4: the structure stop takes the trade out, checked against the
    #        last session's LOW as well as the live price
    low = float(d["low"].iloc[-1])
    st4 = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION,
                                               stop=low + 1.0))
    v4 = FakeVenue(d, date(2026, 7, 31), is_open=True,
                   position={"qty": "20", "avg_entry_price": "410",
                             "market_value": "8300", "unrealized_pl": "-100",
                             "side": "long"},
                   live_price=low + 5.0)
    r4 = S.run_sp500(v4, st4)
    assert r4["action"] == "exited" and r4["reason"] == "structure_stop", r4
    assert len(v4.orders) == 1 and v4.orders[0]["side"] == "sell"

    # -- g5: an exit that comes due with the market SHUT is deferred, never
    #        sent, and does not mark the bar processed
    st5 = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION,
                                               stop=low + 1.0))
    v5 = FakeVenue(d, date(2026, 7, 31), is_open=False,
                   position={"qty": "20", "avg_entry_price": "410",
                             "market_value": "8300", "unrealized_pl": "-100",
                             "side": "long"})
    r5 = S.run_sp500(v5, st5)
    assert r5["action"] == "deferred_market_shut" and r5["kind"] == "exit"
    assert not v5.orders
    assert st5[S.STATE_KEY]["open_trade"] is not None, \
        "a deferred exit still holds the position; it does not vanish"
    assert st5[S.STATE_KEY]["last_bar_day"] is None


# ---------------------------------------------------------------------------
# (h) the memory loop gates
# ---------------------------------------------------------------------------

def test_h_the_memory_loop_gates():
    # -- h1: two consecutive losses FLAG a rule; it can still be taken, but
    #        never silently
    losses2 = [closed_trade("2026-07-01 20:00:00 UTC", "turn_of_month",
                            "structure_stop", -400.0),
               closed_trade("2026-07-02 20:00:00 UTC", "turn_of_month",
                            "held_the_planned_sessions", -120.0)]
    st = make_state(trades=losses2)
    mem = S.load_memory(st)
    assert mem["rules"]["turn_of_month"]["status"] == "flagged", mem["rules"]
    assert mem["rules"]["turn_of_month"]["consecutive_losses"] == 2

    d = build_frame(TOM_SIGNAL_DAY)
    sig = S.rule_turn_of_month(d, {"trading_days_left_in_month": 4})
    v = S.arbitrate([sig], mem)
    assert v.action == "enter"
    assert v.memory_note, "a flagged rule must never be taken silently"

    # -- h2: three losses that all ended the SAME way STAND IT DOWN, and it
    #        latches into state until a human clears it
    losses3 = [closed_trade(f"2026-07-0{i} 20:00:00 UTC", "turn_of_month",
                            "structure_stop", -300.0) for i in (1, 2, 3)]
    st3 = make_state(trades=losses3)
    mem3 = S.load_memory(st3)
    assert mem3["rules"]["turn_of_month"]["status"] == "stood_down"
    newly = S.apply_memory_stand_downs(st3, mem3)
    assert newly == ["turn_of_month"]
    assert "turn_of_month" in st3[S.STATE_KEY]["rules_stood_down"]

    v3 = S.arbitrate([sig], mem3)
    assert v3.action == "stand_down", v3
    assert v3.signal is None

    # a later WIN must not quietly bring back a rule a person parked
    st3[S.STATE_KEY]["trades"].append(
        closed_trade("2026-07-10 20:00:00 UTC", "turn_of_month",
                     "held_the_planned_sessions", +900.0))
    assert S.load_memory(st3)["rules"]["turn_of_month"]["status"] == "stood_down"

    # only a human clears it
    assert S.clear_rule_stand_down(st3, "turn_of_month", who="wallace") is True
    assert S.clear_rule_stand_down(st3, "turn_of_month") is False
    assert S.load_memory(st3)["rules"]["turn_of_month"]["status"] == "clear"

    # -- h3: three losses ending DIFFERENT ways only flag, never stand down
    mixed = [closed_trade("2026-07-01 20:00:00 UTC", "rsi2_dip_buy",
                          "structure_stop", -100.0),
             closed_trade("2026-07-02 20:00:00 UTC", "rsi2_dip_buy",
                          "dip_recovered", -80.0),
             closed_trade("2026-07-03 20:00:00 UTC", "rsi2_dip_buy",
                          "structure_stop", -60.0)]
    m = S.load_memory(make_state(trades=mixed))["rules"]["rsi2_dip_buy"]
    assert m["status"] == "flagged", m

    # -- h4: a stood-down rule blocks the whole cycle, no order sent
    S.NEW_ENTRIES_ENABLED = True
    try:
        st4 = make_state(trades=losses3)
        v4 = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
        r = S.run_sp500(v4, st4)
        assert r["action"] == "stand_down", r
        assert not v4.orders
    finally:
        S.NEW_ENTRIES_ENABLED = False

    # -- h5: the thresholds are the ones the plan states
    assert S.FLAG_AFTER_LOSSES == 2 and S.STAND_DOWN_AFTER_LOSSES == 3


# ---------------------------------------------------------------------------
# (i) a lesson is written on EVERY close, wins included
# ---------------------------------------------------------------------------

def test_i_a_lesson_is_written_on_every_close():
    for exit_price, reason in ((430.0, "held_the_planned_sessions"),
                               (395.0, "structure_stop"),
                               (418.0, "dip_recovered"),
                               (390.0, "position_gone_at_venue")):
        st = make_state()
        t = held_tom_trade(TOM_ENTRY_SESSION)
        before = len(st["lessons"])
        pnl = S.close_trade(st, t, exit_price, reason, sessions_held=8)
        assert len(st["lessons"]) == before + 1, \
            f"no lesson was written for {reason}"
        L = st["lessons"][-1]
        # the schema export_journal.write_learnings() renders
        for key in ("date", "trigger", "trade", "conditions", "why"):
            assert L.get(key), f"lesson is missing {key}"
        assert L["trigger"] == "turn_of_month"
        assert isinstance(pnl, float)
        assert st[S.STATE_KEY]["open_trade"] is None
        assert st[S.STATE_KEY]["trades"][-1]["reason"] == reason

    # a win writes a lesson too, and it is not the loss text
    st = make_state()
    S.close_trade(st, held_tom_trade(TOM_ENTRY_SESSION), 450.0,
                  "held_the_planned_sessions", sessions_held=8)
    assert "paid" in st["lessons"][-1]["why"]

    # the round-trip cost is the VENUE'S, not BloFin's
    assert S.ROUND_TRIP_COST_PCT == 0.04
    st2 = make_state()
    t2 = held_tom_trade(TOM_ENTRY_SESSION, entry_price=400.0, qty=10.0)
    pnl = S.close_trade(st2, t2, 400.0, "held_the_planned_sessions")
    assert abs(pnl + 400.0 * 10.0 * 0.0004) < 0.01, pnl

    # and the lesson is rendered by the existing exporter without changes
    import export_journal
    cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    try:
        os.chdir(tmp)
        export_journal.write_learnings(st2)
        text = open(os.path.join("data", "learnings.md")).read()
        assert st2["lessons"][-1]["why"] in text
        parsed = S._parse_learnings_md(os.path.join("data", "learnings.md"))
        assert parsed and parsed[-1]["trigger"] == "turn_of_month"
    finally:
        os.chdir(cwd)


# ---------------------------------------------------------------------------
# (j) every order carries the CBOT_ tag
# ---------------------------------------------------------------------------

def test_j_every_order_carries_the_cbot_tag():
    assert S.ORDER_TAG == "CBOT"
    a = S.make_client_order_id("turn_of_month", "buy")
    b = S.make_client_order_id("turn_of_month", "buy")
    assert a.startswith("CBOT_") and b.startswith("CBOT_")
    assert a != b, "two orders must never share an id"
    assert len(a) <= 128 and re.fullmatch(r"[A-Za-z0-9_]+", a)

    S.NEW_ENTRIES_ENABLED = True
    try:
        d = build_frame(TOM_SIGNAL_DAY)
        v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
        st = make_state()
        r = S.run_sp500(v, st)
        assert r["action"] == "entered", r
        assert len(v.orders) == 1
        assert v.orders[0]["client_order_id"].startswith("CBOT_")
        assert "turnofmonth" in v.orders[0]["client_order_id"]
        assert st[S.STATE_KEY]["open_trade"]["client_order_id"].startswith(
            "CBOT_")

        # the exit carries one too
        st[S.STATE_KEY]["open_trade"]["entry_session"] = str(TOM_ENTRY_SESSION)
        d2 = build_frame(date(2026, 8, 6))
        v2 = FakeVenue(d2, date(2026, 8, 7), is_open=True,
                       position={"qty": str(st[S.STATE_KEY]["open_trade"]["qty"]),
                                 "avg_entry_price": "420",
                                 "market_value": "1000", "unrealized_pl": "1",
                                 "side": "long"})
        r2 = S.run_sp500(v2, st)
        assert r2["action"] == "exited", r2
        assert v2.orders[-1]["client_order_id"].startswith("CBOT_")
        assert v2.orders[-1]["side"] == "sell"
    finally:
        S.NEW_ENTRIES_ENABLED = False


# ---------------------------------------------------------------------------
# (k) NOTHING happens with the flag off — and a held trade still closes
# ---------------------------------------------------------------------------

def test_k_nothing_happens_with_the_flag_off():
    S.NEW_ENTRIES_ENABLED = False

    # -- k1: a firing signal is priced, logged and refused, with no order
    #        and no unbound-name crash (the exact bug that took the Diver
    #        down live on 2026-07-25)
    d = build_frame(TOM_SIGNAL_DAY)
    v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
    st = make_state()
    r = S.run_sp500(v, st)
    assert r["action"] == "stood_down", r
    assert r["reason"] == "new_entries_disabled"
    assert r["rule"] == "turn_of_month" and r["qty"] > 0
    assert not v.orders, "the flag is off — nothing may reach the venue"
    assert st[S.STATE_KEY]["open_trade"] is None

    # -- k2: A HELD POSITION STILL CLOSES with the flag off. Standing the
    #        bot down must never strand a position.
    d2 = build_frame(date(2026, 8, 6))
    st2 = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION))
    v2 = FakeVenue(d2, date(2026, 8, 7), is_open=True,
                   position={"qty": "20", "avg_entry_price": "410",
                             "market_value": "8300", "unrealized_pl": "100",
                             "side": "long"})
    r2 = S.run_sp500(v2, st2)
    assert r2["action"] == "exited", r2
    assert len(v2.orders) == 1 and v2.orders[0]["side"] == "sell"
    assert st2["lessons"], "a close with the flag off still learns"

    # -- k3: and a held position that is NOT due still holds, not strands
    d3 = build_frame(date(2026, 7, 30))
    st3 = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION))
    v3 = FakeVenue(d3, date(2026, 7, 31), is_open=True,
                   position={"qty": "20", "avg_entry_price": "410",
                             "market_value": "8300", "unrealized_pl": "100",
                             "side": "long"})
    assert S.run_sp500(v3, st3)["action"] == "hold"
    assert not v3.orders

    # -- k4: the gate sits AFTER reconcile and AFTER every exit path, which
    #        is test_stand_down_gates.py's own invariant
    src = inspect.getsource(S.run_sp500)
    assert "STAND-DOWN GATE" in src
    assert src.index("STAND-DOWN GATE") > src.index("reconcile"), \
        "the gate runs BEFORE reconcile — a held position could be stranded"
    # the gate's actual CODE, not its mention in the docstring, has to sit
    # below every path that can close a position
    gate_at = src.index("if not NEW_ENTRIES_ENABLED:")
    for path in ('return {"action": "reconciled_exit"',
                 'return {"action": "exited"',
                 'return {"action": "deferred_market_shut", "kind": "exit"',
                 'return {"action": "hold"'):
        assert gate_at > src.index(path), \
            f"the gate runs BEFORE {path} — a held position could be stranded"

    # -- k5: the file ships OFF
    on_disk = open(os.path.join(HERE, "sp500.py")).read()
    assert re.search(r"^NEW_ENTRIES_ENABLED = False$", on_disk, re.M), \
        "sp500.py must ship with new entries switched off"


# ---------------------------------------------------------------------------
# (l) the calendar, and the still-forming bar
# ---------------------------------------------------------------------------

def test_l_the_calendar_and_the_still_forming_bar():
    # -- l1: known market holidays, computed
    h2026 = S.us_market_holidays(2026)
    for d in (date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16),
              date(2026, 4, 3), date(2026, 5, 25), date(2026, 6, 19),
              date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26),
              date(2026, 12, 25)):
        assert d in h2026, d
    assert date(2026, 7, 4) not in S._computed_sessions(date(2026, 7, 1),
                                                        date(2026, 7, 10))
    # Good Friday, the one that is not a fixed rule
    assert S._easter(2026) == date(2026, 4, 5)
    assert S._easter(2025) == date(2025, 4, 20)
    assert date(2025, 4, 18) in S.us_market_holidays(2025)
    # the weekend rule: Christmas 2027 falls on a Saturday -> Friday the
    # 24th; Independence Day 2027 falls on a Sunday -> Monday the 5th
    assert date(2027, 12, 24) in S.us_market_holidays(2027)
    assert date(2027, 7, 5) in S.us_market_holidays(2027)

    # -- l2: counting the sessions LEFT in a month
    sess = S._computed_sessions(date(2026, 6, 1), date(2026, 8, 31))
    assert S.trading_days_left_in_month(date(2026, 7, 31), sess) == 0
    assert S.trading_days_left_in_month(date(2026, 7, 27), sess) == 4
    # a session list that does not reach the month end must answer None
    # rather than under-count and fire the rule on the wrong day
    short = S._computed_sessions(date(2026, 7, 1), date(2026, 7, 20))
    assert S.trading_days_left_in_month(date(2026, 7, 15), short) is None

    # -- l3: the venue's own calendar is asked FIRST, and the source is named
    d = build_frame(TOM_SIGNAL_DAY)
    days, src = S.venue_sessions(FakeVenue(d, TOM_ENTRY_SESSION),
                                 date(2026, 7, 1), date(2026, 7, 31))
    assert src == "computed NYSE calendar" and len(days) == 22
    days2, src2 = S.venue_sessions(FakeVenueWithCalendar(d, TOM_ENTRY_SESSION),
                                   date(2026, 7, 1), date(2026, 7, 31))
    assert src2 == "venue calendar" and days2 == days

    # -- l4: TODAY'S STILL-FORMING BAR IS DROPPED. Alpaca serves it during
    #        the session and acting on it would be reading a price that has
    #        not happened yet. The fake serves one at an absurd 9,999.
    v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True, serve_partial_bar=True)
    frame = S.load_daily(v, TOM_ENTRY_SESSION)
    assert frame["day"].iloc[-1] == TOM_SIGNAL_DAY, frame["day"].iloc[-1]
    assert float(frame["close"].max()) < 9_000.0, \
        "the still-forming bar reached the decision — that is lookahead"
    assert (frame["day"] < TOM_ENTRY_SESSION).all()

    # -- l5: the history is asked for BY DATE. Verified live on 2026-07-25:
    #        Alpaca answers a daily-bar request with no start date with
    #        "bars": null, so a request without one reads as no history at
    #        all — and a start plus a count returns the OLDEST bars from
    #        that date, not the newest.
    req = v.bar_requests[-1]
    assert req["start"], \
        "the bar request carried no start date — the live venue answers " \
        "that with no bars at all"
    start = date.fromisoformat(str(req["start"])[:10])
    span_sessions = len(S._computed_sessions(start, TOM_ENTRY_SESSION))
    assert span_sessions > S.TREND_SMA + S.K_SWING, (
        f"the window only covers {span_sessions} sessions — not enough to "
        f"warm the {S.TREND_SMA}-day average")
    assert req["limit"] > span_sessions, \
        "the count must never bind before the date window does, or the " \
        "venue returns the OLDEST bars and the frame stops short of today"


# ---------------------------------------------------------------------------
# (m) the language rules
# ---------------------------------------------------------------------------

def test_m_the_language_rules():
    src = open(os.path.join(HERE, "sp500.py")).read()

    # -- m1: it says "bot", never "book"
    assert "book" not in src.lower(), \
        "sp500.py says bot, not book: " + str(
            [src[m.start() - 30:m.start() + 30]
             for m in re.finditer("book", src, re.I)][:3])
    assert "bot" in src

    # -- m2: NO BARE PERCENTAGE. Every one says what it is a percentage OF.
    allowed = ("of price", "of the position", "of the account", "of position")
    offenders = []
    for m in re.finditer(r"\}%", src):
        tail = src[m.start():m.start() + 40]
        if not any(a in tail for a in allowed):
            offenders.append(tail.splitlines()[0])
    assert not offenders, (
        "these percentages do not say what they are a percentage OF:\n  "
        + "\n  ".join(offenders))

    # the three helpers label themselves
    assert S.price_move_pct(100.0, 105.0) == "+5.00% of price"
    assert S.position_value_pct(0.5947) == "+0.5947% of the position's own value"
    assert S.account_pct(2.0) == "+2.00% of the account"
    assert S.price_move_pct(0.0, 5.0) == "n/a"

    # -- m3: the excluded rules are named, with the reason, in the file
    for phrase in ("DEMOTED", "REJECTED", "NOT CONFIRMED", "CANDIDATE",
                   "drawdown blanket", "78.5th"):
        assert phrase in src, f"sp500.py should say why: {phrase!r} missing"

    # -- m4: the overnight finding is written down where it matters
    assert "0.0468% of price" in src and "0.0176% of price" in src
    assert "must never be one" in src or "must never" in src


# ---------------------------------------------------------------------------
# (n) the memory really reads the journal files back off disk
# ---------------------------------------------------------------------------

def test_n_memory_reads_the_journal_files_back():
    tmp = tempfile.mkdtemp()
    ledger = os.path.join(tmp, "ledger.csv")
    learnings = os.path.join(tmp, "learnings.md")

    with open(ledger, "w") as f:
        f.write("timestamp,symbol,action,price,quantity,reason,mode,outcome,pnl\n")
        for i in (1, 2, 3):
            f.write(f"2026-07-0{i}T20:00:00+00:00,SPY,SELL,400,10,"
                    f"turn_of_month:structure_stop,paper,loss,-250\n")
    with open(learnings, "w") as f:
        f.write("# LEARNINGS\n\n## Trade reviews (newest first)\n\n"
                "### 2026-07-03 20:00:00 UTC — turn_of_month\n"
                "- long $400.00 -> structure_stop $390.00\n"
                "- conditions: stop sat on the confirmed swing low 390.00\n"
                "- **lesson:** the level broke three times running\n")

    st = make_state()
    mem = S.load_memory(st, ledger_path=ledger, learnings_path=learnings)
    assert mem["n_ledger_rows"] == 3
    assert mem["rules"]["turn_of_month"]["consecutive_losses"] == 3
    assert mem["rules"]["turn_of_month"]["status"] == "stood_down"
    assert mem["n_lessons"] == 1
    assert "three times running" in mem["lessons"][0]["why"]

    # a missing diary is an empty memory, never an exception: a bot must
    # not refuse to trade because its diary is gone
    empty = S.load_memory(make_state(), ledger_path="no/such/file.csv",
                          learnings_path="no/such/file.md")
    assert empty["n_closed"] == 0 and empty["n_lessons"] == 0
    assert all(m["status"] == "clear" for m in empty["rules"].values())


# ---------------------------------------------------------------------------
# (o) idempotency, and the two rules never both trade at once
# ---------------------------------------------------------------------------

def test_o_idempotency_and_one_position_at_a_time():
    S.NEW_ENTRIES_ENABLED = True
    try:
        d = build_frame(TOM_SIGNAL_DAY)
        v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
        st = make_state()
        r1 = S.run_sp500(v, st)
        assert r1["action"] == "entered"
        assert len(v.orders) == 1

        # the position is closed elsewhere WITHOUT the daily bar moving on
        st[S.STATE_KEY]["open_trade"] = None
        r2 = S.run_sp500(v, st)
        assert r2["action"] == "noop_already_processed", r2
        assert len(v.orders) == 1, \
            "the same closed bar must never produce a second entry"

        # both rules firing on one bar is ONE trade: turn-of-month wins on
        # priority and only one order is ever sent
        tom = S.rule_turn_of_month(d, {"trading_days_left_in_month": 4})
        dip = S.rule_rsi2_dip_buy(build_frame(QUIET_DAY, drop=DIP_DROP),
                                  {"symbol": "SPY"})
        mem = S.load_memory(make_state())
        verdict = S.arbitrate([dip, tom], mem)
        assert verdict.action == "enter"
        assert verdict.signal.rule == "turn_of_month", \
            "turn-of-month has the lower priority number and must win"
        assert S.arbitrate([], mem).action == "no_signal"
    finally:
        S.NEW_ENTRIES_ENABLED = False


# ---------------------------------------------------------------------------
# (p) dry mode changes nothing at all
# ---------------------------------------------------------------------------

def test_p_dry_mode_changes_nothing():
    S.NEW_ENTRIES_ENABLED = True
    try:
        d = build_frame(TOM_SIGNAL_DAY)
        v = FakeVenue(d, TOM_ENTRY_SESSION, is_open=True)
        st = make_state()
        r = S.run_sp500(v, st, dry=True)
        assert r["action"] == "would_enter", r
        assert not v.orders
        assert st[S.STATE_KEY]["open_trade"] is None
        assert st[S.STATE_KEY]["last_bar_day"] is None
        assert not st["lessons"]

        d2 = build_frame(date(2026, 8, 6))
        st2 = make_state(open_trade=held_tom_trade(TOM_ENTRY_SESSION))
        v2 = FakeVenue(d2, date(2026, 8, 7), is_open=True,
                       position={"qty": "20", "avg_entry_price": "410",
                                 "market_value": "8300",
                                 "unrealized_pl": "100", "side": "long"})
        r2 = S.run_sp500(v2, st2, dry=True)
        assert r2["action"] == "would_exit", r2
        assert not v2.orders
        assert st2[S.STATE_KEY]["open_trade"] is not None
        assert not st2["lessons"]
    finally:
        S.NEW_ENTRIES_ENABLED = False


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def main():
    tests = [test_a_turn_of_month_fires_only_on_its_own_session,
             test_b_dip_buy_fires_only_on_a_deep_dip_and_only_on_spy,
             test_c_market_hours_check_refuses_to_send_when_shut,
             test_d_the_stop_is_per_trade_structure_not_a_fixed_percentage,
             test_e_size_comes_from_the_stop,
             test_f_the_position_is_held_across_nights,
             test_g_exits_reconcile_against_the_venue,
             test_h_the_memory_loop_gates,
             test_i_a_lesson_is_written_on_every_close,
             test_j_every_order_carries_the_cbot_tag,
             test_k_nothing_happens_with_the_flag_off,
             test_l_the_calendar_and_the_still_forming_bar,
             test_m_the_language_rules,
             test_n_memory_reads_the_journal_files_back,
             test_o_idempotency_and_one_position_at_a_time,
             test_p_dry_mode_changes_nothing]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("THE S&P BOT TESTS")
    print("=" * 72)
    for name, ok, tb in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if tb:
            print("          " + tb.replace("\n", "\n          "))
    n = sum(1 for _, ok, _ in results if ok)
    print("-" * 72)
    print(f"  {n}/{len(results)} passed")
    print("=" * 72)
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
