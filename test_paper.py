"""
test_paper.py — proof that our engine does not flatter us.

WHAT THIS FILE HAS TO ESTABLISH, in order of how badly it would hurt to be
wrong about it:

  1. THE STOP FILLS WORSE THAN ITS LEVEL. A record where stops fill at the
     level is the single most common way a paper week lies. There are tests
     here for a long, for a short, and for a bar that gapped clean through.
  2. THE SAME-BAR TIE GOES TO THE STOP. Both inside one bar, always the stop,
     never a coin flip.
  3. NO LOOKAHEAD. A fill offered a bar the decision could not have seen is
     refused, and the refusal says so.
  4. BUYS PAY THE ASK, SELLS RECEIVE THE BID, AND NOTHING FILLS AT THE
     MIDPOINT — including the bar-driven path, where the open IS a midpoint.
  5. A MISSING OR STALE PRICE MEANS NO FILL AND A NAMED REASON, not a
     swallowed failure that looks like the strategy standing down.
  6. COST NEVER FILTERS. An absurd commission still fills. The source is read
     to prove no cost value ever reaches a condition.
  7. SHORTS ARE FIRST-CLASS and the money moves the right way.
  8. STATE SURVIVES A RESTART, and the whole thing is reconstructible from
     the fill log alone.
  9. THE VENUE DEFAULTS TO PAPER and real money cannot be reached by
     accident.

Repo style: plain asserts, a TESTS list, a main() runner. Works under pytest
too. No network — every quote here is injected.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, "/Users/wallacechen/cryptobot")

import paper
import venue
from paper import PaperBroker, Quote

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC)


class Clock:
    """A clock we own, so staleness is a fact in the test rather than a race."""

    def __init__(self, t=T0):
        self.t = t

    def __call__(self):
        return self.t

    def tick(self, seconds):
        self.t = self.t + dt.timedelta(seconds=seconds)
        return self.t


class Feed:
    """A quote source we own. `set` puts a bid and ask on the board; anything
    not on the board is genuinely missing, which is what the miss tests need.
    """

    def __init__(self, clock):
        self.clock = clock
        self.book: dict[str, Quote] = {}
        self.calls = 0

    def set(self, symbol, bid, ask, ts=None):
        self.book[symbol] = Quote(symbol, bid, ask, ts or self.clock(), "test")

    def drop(self, symbol):
        self.book.pop(symbol, None)

    def __call__(self, symbols):
        self.calls += 1
        return {s: self.book[s] for s in symbols if s in self.book}


def make(tmp=None, **kw):
    """A broker with a clock and a feed we control. No disk unless asked."""
    clock = kw.pop("clock", None) or Clock()
    feed = kw.pop("feed", None) or Feed(clock)
    kw.setdefault("state_path", os.path.join(tmp, "state.json") if tmp else None)
    kw.setdefault("log_path", os.path.join(tmp, "fills.jsonl") if tmp else None)
    kw.setdefault("spread_pct", {"BTC/USD": 0.001})
    b = PaperBroker(quotes=feed, now=clock, **kw)
    return b, clock, feed


def bar(t, o, h, l, c):
    return {"t": t, "o": o, "h": h, "l": l, "c": c}


# ===================================================== 1. THE PRICE WE FILL AT
def test_a_buy_pays_the_ask_and_a_sell_receives_the_bid():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_200.0)
    got = b.market_order("BTC/USD", "buy", 0.1)
    assert got["status"] == "filled", got
    assert got["price"] == 100_200.0, "a buy must pay the ASK"
    assert got["price"] != 100_100.0, "never the midpoint"

    feed.set("ETH/USD", 3_000.0, 3_006.0)
    got = b.market_order("ETH/USD", "sell", 1.0)
    assert got["price"] == 3_000.0, "a sell must receive the BID"
    assert got["price"] != 3_003.0, "never the midpoint"


def test_nothing_ever_fills_at_the_midpoint_including_off_a_bar():
    """The bar-driven path is where a midpoint would sneak in: a bar's open
    IS a midpoint. Half the measured spread has to be added or taken off."""
    b, clock, feed = make()
    o = 100_000.0
    nb = bar(T0 + dt.timedelta(minutes=1), o, o + 50, o - 50, o + 10)
    buy = b.market_order("BTC/USD", "buy", 0.1, decided_at=T0, next_bar=nb)
    assert buy["status"] == "filled", buy
    assert buy["price"] > o, "a buy off a bar must pay more than the open"
    assert abs(buy["price"] - o * 1.0005) < 1e-6, buy["price"]

    sell = b.market_order("BTC/USD", "sell", 0.05, decided_at=T0, next_bar=nb)
    assert sell["price"] < o, "a sell off a bar must receive less than the open"
    assert abs(sell["price"] - o * 0.9995) < 1e-6, sell["price"]


def test_the_spread_we_paid_is_recorded_on_every_fill():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_200.0)
    got = b.market_order("BTC/USD", "buy", 0.5)
    # paid 100,200 against a 100,100 midpoint, on half a coin: 50 dollars
    assert abs(got["spread_cost"] - 50.0) < 1e-6, got["spread_cost"]


# ============================================================== 2. THE STOP
def test_a_stop_fills_worse_than_its_level_on_a_long():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    # the bar trades down to 98,500 — well through the stop
    res = b.on_bar("BTC/USD", bar(T0, 99_500, 99_600, 98_500, 99_200))
    assert res["action"] == "stopped", res
    assert res["price"] == 98_500.0, "the fill must be the WORST price in the bar"
    assert res["price"] < 99_000.0, "a stop that fills at its level is a lie"
    assert res["fill"]["slippage_versus_the_stop_level"] == 500.0


def test_a_stop_fills_worse_than_its_level_on_a_short():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "sell", 1.0)          # a SHORT, not an error
    b.place_stop("BTC/USD", 101_000.0)
    res = b.on_bar("BTC/USD", bar(T0, 100_500, 102_400, 100_400, 101_800))
    assert res["action"] == "stopped", res
    assert res["price"] == 102_400.0, "covering a short fills at the bar HIGH"
    assert res["price"] > 101_000.0


def test_a_bar_that_gaps_through_the_stop_fills_at_the_gap():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    # opens BELOW the stop and never trades near it again
    res = b.on_bar("BTC/USD", bar(T0, 96_000, 96_500, 95_800, 96_200))
    assert res["price"] == 95_800.0, res
    acct = b.account(refresh=False)
    assert acct["equity"] < 100_000 - 4_000, "the gap must actually cost us"


def test_the_same_bar_tie_goes_to_the_stop():
    """Stop and target both inside one bar. The data cannot say which came
    first, so it is the stop. Every time."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    res = b.on_bar("BTC/USD", bar(T0, 100_000, 102_000, 98_900, 101_500),
                   target=101_000.0)
    assert res["action"] == "stopped", "the tie must go to the stop"
    assert res["target_also_in_this_bar"] is True
    assert res["price"] == 98_900.0
    assert b.position("BTC/USD") is None


def test_the_same_bar_tie_goes_to_the_stop_on_a_short_too():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "sell", 1.0)
    b.place_stop("BTC/USD", 101_000.0)
    res = b.on_bar("BTC/USD", bar(T0, 100_000, 101_500, 98_000, 99_000),
                   target=99_000.0)
    assert res["action"] == "stopped", res
    assert res["price"] == 101_500.0


def test_a_target_alone_is_reported_and_not_filled():
    """How much comes off at a target is the method's call. The venue reports
    the touch and does nothing else."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    res = b.on_bar("BTC/USD", bar(T0, 100_000, 102_000, 99_500, 101_500),
                   target=101_000.0)
    assert res["action"] == "target_touched", res
    assert b.position("BTC/USD")["qty"] == 1.0, "nothing may be closed here"


def test_a_stop_only_covers_what_is_still_open():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    b.close_position("BTC/USD", 0.5)
    res = b.on_bar("BTC/USD", bar(T0, 99_500, 99_600, 98_800, 99_000))
    assert res["fill"]["qty"] == 0.5, "the stop covers the runner, not the original"


# ========================================================== 3. NO LOOKAHEAD
def test_a_bar_at_or_before_the_decision_is_refused():
    b, clock, feed = make()
    same = bar(T0, 100_000, 100_100, 99_900, 100_050)
    got = b.market_order("BTC/USD", "buy", 1.0, decided_at=T0, next_bar=same)
    assert got["status"] == "rejected", got
    assert "lookahead" in got["reason"], got["reason"]

    earlier = bar(T0 - dt.timedelta(minutes=5), 100_000, 1, 1, 1)
    got = b.market_order("BTC/USD", "buy", 1.0, decided_at=T0, next_bar=earlier)
    assert got["status"] == "rejected"
    assert "lookahead" in got["reason"]


def test_the_next_bar_is_accepted():
    b, clock, feed = make()
    nxt = bar(T0 + dt.timedelta(minutes=1), 100_000, 100_100, 99_900, 100_050)
    got = b.market_order("BTC/USD", "buy", 0.5, decided_at=T0, next_bar=nxt)
    assert got["status"] == "filled", got


def test_a_bar_with_no_timestamp_cannot_prove_it_is_after_the_decision():
    b, clock, feed = make()
    nameless = {"o": 100_000, "h": 1, "l": 1, "c": 1}
    got = b.market_order("BTC/USD", "buy", 1.0, decided_at=T0, next_bar=nameless)
    assert got["status"] == "rejected", got
    assert "lookahead" in got["reason"]


# ==================================================== 4. MISSES, NAMED OUT LOUD
def test_a_missing_price_is_a_miss_and_never_an_invented_fill():
    b, clock, feed = make()
    got = b.market_order("BTC/USD", "buy", 1.0)
    assert got["status"] == "rejected"
    assert got["price"] is None
    assert "no quote" in got["reason"]
    assert b.position("BTC/USD") is None
    assert b.misses() and b.misses()[-1]["reason"] == got["reason"]


def test_a_stale_price_is_a_miss():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_200.0)
    clock.tick(600)                                  # ten minutes later
    got = b.market_order("BTC/USD", "buy", 1.0)
    assert got["status"] == "rejected", got
    assert "stale price" in got["reason"], got["reason"]
    assert "600 seconds old" in got["reason"], got["reason"]


def test_a_fresh_enough_price_still_fills():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_200.0)
    clock.tick(30)
    assert b.market_order("BTC/USD", "buy", 0.5)["status"] == "filled"


def test_a_crossed_or_zero_quote_is_a_miss():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_200.0, 100_000.0)        # bid above ask
    got = b.market_order("BTC/USD", "buy", 1.0)
    assert got["status"] == "rejected" and "unusable" in got["reason"], got

    feed.set("BTC/USD", 0.0, 100_000.0)
    got = b.market_order("BTC/USD", "buy", 1.0)
    assert got["status"] == "rejected", got


def test_a_gap_too_wide_to_be_a_market_is_a_miss_and_not_a_cost_filter():
    """SPY really quoted 716.44 by 760.82 at 23:00 on a Saturday. That is the
    venue saying it is shut, and buying at 760 for something worth 738 is
    noise, not honesty. This refuses because there is no market — it never
    compares a cost against a profit."""
    b, clock, feed = make()
    feed.set("SPY", 716.44, 760.82)
    got = b.market_order("SPY", "buy", 1.0)
    assert got["status"] == "rejected", got
    assert "too wide to be a real market" in got["reason"], got["reason"]

    # a normal wide-ish market still fills: this must not become a cost gate
    feed.set("SOL/USD", 100.0, 100.5)                # 0.5% of the price
    assert b.market_order("SOL/USD", "buy", 1.0)["status"] == "filled"

    # and it can be switched off entirely
    b2, c2, f2 = make(max_spread_pct_of_price=None)
    f2.set("SPY", 716.44, 760.82)
    assert b2.market_order("SPY", "buy", 1.0)["status"] == "filled"


def test_not_enough_buying_power_is_a_named_miss():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    got = b.market_order("BTC/USD", "buy", 5.0)      # half a million on 100k
    assert got["status"] == "rejected"
    assert "buying power" in got["reason"], got["reason"]
    assert "$500,000.00" in got["reason"], got["reason"]


def test_closing_is_never_blocked_by_buying_power():
    """A position we cannot exit is how a paper account becomes a fantasy."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    feed.set("BTC/USD", 40_000.0, 40_000.0)          # wiped most of the equity
    assert b.buying_power() >= 0
    got = b.close_position("BTC/USD")
    assert got["status"] == "filled", got


def test_a_bar_fill_without_a_measured_spread_is_refused():
    b, clock, feed = make(spread_pct={})
    nxt = bar(T0 + dt.timedelta(minutes=1), 100_000, 1, 1, 1)
    got = b.market_order("XAU/USD", "buy", 1.0, decided_at=T0, next_bar=nxt)
    assert got["status"] == "rejected"
    assert "no measured spread" in got["reason"], got["reason"]


def test_bad_input_comes_back_named():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    assert b.market_order("BTC/USD", "hold", 1.0)["reason"] == paper.MISS_BAD_SIDE
    assert b.market_order("BTC/USD", "buy", 0)["reason"] == paper.MISS_BAD_QTY
    assert b.market_order("BTC/USD", "buy", -1)["reason"] == paper.MISS_BAD_QTY
    assert b.close_position("NOPE/USD")["reason"] == paper.MISS_NO_POSITION
    assert b.place_stop("NOPE/USD", 1.0)["reason"] == paper.MISS_NO_POSITION
    b.market_order("BTC/USD", "buy", 0.1)
    assert "larger than" in b.close_position("BTC/USD", 9.0)["reason"]


# ============================================================== 5. SHORTS
def test_a_sell_with_no_position_opens_a_short():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_100.0)
    got = b.market_order("BTC/USD", "sell", 0.5)
    assert got["status"] == "filled", got
    pos = b.position("BTC/USD")
    assert pos["qty"] == -0.5 and pos["side"] == "short"
    assert b.cash == 100_000.0 + 0.5 * 100_000.0, "shorting credits the proceeds"


def test_a_short_that_wins_makes_money_and_one_that_loses_costs_it():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "sell", 1.0)
    feed.set("BTC/USD", 90_000.0, 90_000.0)
    b.close_position("BTC/USD")
    assert abs(b.equity() - 110_000.0) < 1e-6, b.equity()

    b2, clock2, feed2 = make()
    feed2.set("BTC/USD", 100_000.0, 100_000.0)
    b2.market_order("BTC/USD", "sell", 1.0)
    feed2.set("BTC/USD", 105_000.0, 105_000.0)
    b2.close_position("BTC/USD")
    assert abs(b2.equity() - 95_000.0) < 1e-6, b2.equity()


def test_a_short_marks_at_the_ask_and_a_long_at_the_bid():
    """Marking at the midpoint would show half a spread of profit that does
    not exist."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    feed.set("BTC/USD", 99_000.0, 101_000.0)         # a wide market
    pos = b.positions()[0]
    assert pos["mark"] == 99_000.0, "a long marks at the bid"

    b2, clock2, feed2 = make()
    feed2.set("ETH/USD", 3_000.0, 3_000.0)
    b2.market_order("ETH/USD", "sell", 1.0)
    feed2.set("ETH/USD", 2_900.0, 3_100.0)
    assert b2.positions()[0]["mark"] == 3_100.0, "a short marks at the ask"


# ============================================== 6. PARTIALS AND BREAK EVEN
def test_half_off_then_the_stop_to_break_even():
    """The method's actual shape: half off at the first target, stop to break
    even, and the runner stopped at break even is a NORMAL outcome."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)

    feed.set("BTC/USD", 101_000.0, 101_000.0)
    half = b.close_position("BTC/USD", 0.5, reason="target 1: half off")
    assert half["status"] == "filled" and half["qty"] == 0.5
    assert abs(half["realised_on_this_fill"] - 500.0) < 1e-6

    b.place_stop("BTC/USD", 100_000.0, reason="break even")
    pos = b.position("BTC/USD")
    assert pos["qty"] == 0.5 and pos["stop"] == 100_000.0
    assert pos["avg_entry"] == 100_000.0, "a partial must not move the entry"

    res = b.on_bar("BTC/USD", bar(T0, 100_500, 100_600, 99_800, 100_000))
    assert res["action"] == "stopped"
    # stopped at 99,800 rather than the 100,000 level: the runner lost a
    # little instead of exactly nothing, which is the honest version
    assert res["price"] == 99_800.0
    assert abs(b.equity() - (100_000.0 + 500.0 - 100.0)) < 1e-6, b.equity()


def test_open_risk_is_labelled_as_the_level_and_says_the_truth_is_worse():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 0.5)
    b.place_stop("BTC/USD", 99_500.0)
    risk = b.open_risk()
    assert risk["dollars_if_stops_fill_at_their_level"] == 250.0
    assert "worse than this" in risk["note"]
    acct = b.account(refresh=False)
    assert acct["open_risk"] == 250.0


def test_a_position_with_no_stop_is_reported_as_unprotected():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    assert b.open_risk()["unprotected_positions"] == ["BTC/USD"]


# =========================================================== 7. COST NEVER GATES
def test_an_absurd_cost_still_fills():
    """Wallace has ruled on this twice. Cost is recorded, never a condition."""
    b, clock, feed = make(commission_pct=0.10)       # 10% of notional, absurd
    feed.set("BTC/USD", 1_000.0, 1_000.0)
    got = b.market_order("BTC/USD", "buy", 1.0)
    assert got["status"] == "filled", "cost may never decline a trade"
    assert abs(got["commission"] - 100.0) < 1e-9
    assert "declines, ranks or filters" in got["cost_note"]


def test_the_source_never_puts_a_cost_value_in_a_condition():
    """Read the file, the way test_tjr_crypto reads its own. Every line that
    mentions a cost must be arithmetic or a record, never an if."""
    words = ("commission", "spread_cost", "cost", "fee", "slippage")
    bad = []
    for fname in ("paper.py", "venue.py"):
        src = open(os.path.join(paper.REPO, fname)).read().splitlines()
        for i, line in enumerate(src, 1):
            s = line.strip()
            if s.startswith("#") or s.startswith('"') or s.startswith("'"):
                continue
            # the CONDITION, and only the condition. An assignment whose value
            # happens to be a cost is arithmetic; a branch taken because of one
            # is a filter, and there must not be a single one.
            cond = ""
            if s.startswith("if ") or s.startswith("elif ") or s.startswith("while "):
                cond = s.split(" ", 1)[1]
            elif " if " in s and " else " in s:
                cond = s.split(" if ", 1)[1].split(" else ", 1)[0]
            if not cond:
                continue
            for w in words:
                if w in cond:
                    bad.append(f"{fname}:{i}: {s}")
                    break
    assert not bad, "a cost value reached a decision:\n" + "\n".join(bad)


# =================================================== 8. STATE AND THE FILL LOG
def test_state_survives_a_restart():
    tmp = tempfile.mkdtemp()
    try:
        clock = Clock()
        feed = Feed(clock)
        feed.set("BTC/USD", 100_000.0, 100_000.0)
        feed.set("ETH/USD", 3_000.0, 3_000.0)
        b, _, _ = make(tmp, clock=clock, feed=feed)
        b.market_order("BTC/USD", "buy", 0.5)
        b.place_stop("BTC/USD", 99_000.0)
        b.market_order("ETH/USD", "sell", 2.0)       # a short must survive too
        b.place_stop("ETH/USD", 3_100.0)
        before = (b.cash, {k: dict(v) for k, v in b._pos.items()})

        # the server redeploys
        del b
        again = PaperBroker(state_path=os.path.join(tmp, "state.json"),
                            log_path=os.path.join(tmp, "fills.jsonl"),
                            quotes=feed, now=clock)
        assert again.cash == before[0], "cash must come back"
        assert again._pos.keys() == before[1].keys()
        assert again.position("BTC/USD")["stop"] == 99_000.0, "the stop must come back"
        assert again.position("ETH/USD")["qty"] == -2.0, "the short must come back"
        # and the reloaded object still works
        res = again.on_bar("BTC/USD", bar(T0, 99_500, 99_600, 98_000, 99_100))
        assert res["action"] == "stopped" and res["price"] == 98_000.0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_the_write_is_atomic_and_leaves_no_half_file():
    tmp = tempfile.mkdtemp()
    try:
        b, clock, feed = make(tmp)
        feed.set("BTC/USD", 100_000.0, 100_000.0)
        b.market_order("BTC/USD", "buy", 0.25)
        path = os.path.join(tmp, "state.json")
        # a crash mid-write would leave a dot-tmp file behind and the real
        # file untouched. Prove the real file is always complete JSON.
        with open(path) as f:
            json.load(f)
        leftovers = [f for f in os.listdir(tmp) if f.endswith(".tmp")]
        assert not leftovers, leftovers
        # simulate the crash: a torn temporary file must not be readable as
        # state and must not affect the good one
        with open(os.path.join(tmp, ".state.json.999.tmp"), "w") as f:
            f.write('{"cash": 1')
        again = PaperBroker(state_path=path, log_path=None, quotes=feed,
                            now=clock)
        assert again.position("BTC/USD")["qty"] == 0.25
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_an_unreadable_state_file_refuses_rather_than_resetting_to_100k():
    """Silently starting again at $100,000 would erase open positions and
    print a beautiful week that never happened."""
    tmp = tempfile.mkdtemp()
    try:
        path = os.path.join(tmp, "state.json")
        with open(path, "w") as f:
            f.write("{not json at all")
        try:
            PaperBroker(state_path=path, log_path=None, quotes=lambda s: {})
        except RuntimeError as e:
            assert "rebuild" in str(e), str(e)
        else:
            raise AssertionError("it reset the account instead of refusing")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_everything_is_reconstructible_from_the_fill_log_alone():
    """The whole engine, rebuilt from nothing but the append-only log."""
    tmp = tempfile.mkdtemp()
    try:
        clock = Clock()
        feed = Feed(clock)
        b, _, _ = make(tmp, clock=clock, feed=feed)
        feed.set("BTC/USD", 100_000.0, 100_050.0)
        feed.set("ETH/USD", 3_000.0, 3_002.0)
        b.market_order("BTC/USD", "buy", 0.4)
        b.place_stop("BTC/USD", 99_000.0)
        b.market_order("ETH/USD", "sell", 3.0)       # short
        b.place_stop("ETH/USD", 3_150.0)
        clock.tick(60)
        feed.set("BTC/USD", 101_000.0, 101_050.0)
        b.close_position("BTC/USD", 0.2, reason="half off")
        b.place_stop("BTC/USD", 100_050.0, reason="break even")
        b.market_order("BTC/USD", "buy", 0.1)        # add back, to stress it
        b.cancel_stop("ETH/USD")
        b.on_bar("BTC/USD", bar(T0, 100_500, 100_600, 98_000, 99_000))

        rebuilt = PaperBroker.rebuild_from_log(os.path.join(tmp, "fills.jsonl"))
        assert abs(rebuilt.cash - b.cash) < 1e-9, (rebuilt.cash, b.cash)
        assert abs(rebuilt.realised - b.realised) < 1e-9
        assert set(rebuilt._pos) == set(b._pos), (rebuilt._pos.keys(), b._pos.keys())
        for sym, p in b._pos.items():
            r = rebuilt._pos[sym]
            assert abs(r["qty"] - p["qty"]) < 1e-12, sym
            assert abs(r["avg_entry"] - p["avg_entry"]) < 1e-9, sym
            assert r["stop"] == p["stop"], (sym, r["stop"], p["stop"])
        assert len(rebuilt.fills()) == len(b.fills())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_torn_last_log_line_does_not_stop_the_rebuild():
    tmp = tempfile.mkdtemp()
    try:
        clock = Clock()
        feed = Feed(clock)
        b, _, _ = make(tmp, clock=clock, feed=feed)
        feed.set("BTC/USD", 100_000.0, 100_000.0)
        b.market_order("BTC/USD", "buy", 1.0)
        with open(os.path.join(tmp, "fills.jsonl"), "a") as f:
            f.write('{"event": "fill", "symb')          # the crash
        rebuilt = PaperBroker.rebuild_from_log(os.path.join(tmp, "fills.jsonl"))
        assert rebuilt._pos["BTC/USD"]["qty"] == 1.0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_every_record_carries_the_venue():
    """A fill log can never be ambiguous about whether the money was real."""
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    b.place_stop("BTC/USD", 99_000.0)
    b.market_order("NOPE/USD", "buy", 1.0)           # a miss
    for rec in b.orders():
        assert rec.get("venue") == "paper", rec
        assert rec.get("real_money") is False, rec


def test_the_account_opens_at_one_hundred_thousand():
    b, clock, feed = make()
    acct = b.account(refresh=False)
    assert acct["equity"] == 100_000.0
    assert acct["cash"] == 100_000.0
    assert acct["starting_equity"] == 100_000.0
    assert paper.STARTING_EQUITY == 100_000.0


def test_no_percentage_is_reported_without_saying_what_it_is_a_percentage_of():
    b, clock, feed = make()
    feed.set("BTC/USD", 100_000.0, 100_000.0)
    b.market_order("BTC/USD", "buy", 1.0)
    keys = list(b.account(refresh=False)) + list(b.positions()[0])
    for k in keys:
        if "pct" in k or "percent" in k:
            assert ("_pct_of_" in k or k.endswith("_value_pct")), (
                f"{k!r} is a bare percentage: say whether it is a move in the "
                f"price or a change in the position's value")


# ================================================ 9. THE REAL-MONEY GUARD
#
# NOWHERE. Every resolve() below passes state_path=None and log_path=None. A
# test suite that wrote to the real paper_state.json would be reaching into a
# paper week in progress, which is the thing this whole engine exists to keep
# honest.
NO_DISK = {"state_path": None, "log_path": None}


def test_the_default_venue_is_paper():
    v, d = venue.resolve(env={}, **NO_DISK)
    assert d["chosen"] == "paper", d
    assert d["real_money"] is False
    assert v.is_real_money is False


def test_an_unreadable_or_unknown_venue_resolves_to_paper():
    for env in ({}, {"CRYPTOBOT_VENUE": ""}, {"CRYPTOBOT_VENUE": "alpacaa"},
                {"CRYPTOBOT_VENUE": "live"}, {"VENUE": "real"},
                {"CRYPTOBOT_VENUE": "1"}, {"CRYPTOBOT_VENUE": "true"}):
        v, d = venue.resolve(env=env, **NO_DISK)
        assert d["chosen"] == "paper", (env, d)
        assert d["real_money"] is False, (env, d)


def test_the_tests_never_touch_the_real_paper_account():
    """If this ever fails, a test just wrote into a live paper week."""
    for p in (paper.STATE_PATH, paper.LOG_PATH):
        assert not os.path.exists(p), (
            f"{p} exists during the test run. Something resolved a venue "
            f"without state_path=None.")


def test_a_real_money_venue_is_refused_without_the_exact_phrase():
    class Fake(venue.Venue):
        name = "fake-live"
        is_real_money = True
        def account(self): return {}
        def positions(self): return []
        def position(self, s): return None
        def market_order(self, s, side, q, **k): return {}
        def place_stop(self, s, lvl, **k): return {}
        def close_position(self, s, q=None, **k): return {}
        def orders(self): return []
        def fills(self): return []

    venue.register("fake-live", lambda **k: Fake(), real_money=True,
                   note="test only")
    try:
        for bad in ({}, {"CRYPTOBOT_REAL_MONEY": "1"},
                    {"CRYPTOBOT_REAL_MONEY": "true"},
                    {"CRYPTOBOT_REAL_MONEY": "yes"},
                    {"CRYPTOBOT_REAL_MONEY": "YES-TRADE-REAL-MONEY"}):
            env = {"CRYPTOBOT_VENUE": "fake-live", **bad}
            v, d = venue.resolve(env=env, **NO_DISK)
            assert d["chosen"] == "paper", (bad, d)
            assert d["real_money"] is False, (bad, d)
            assert any("REAL MONEY" in w for w in d["warnings"]), d

        good = {"CRYPTOBOT_VENUE": "fake-live",
                "CRYPTOBOT_REAL_MONEY": venue.LIVE_CONFIRM_PHRASE}
        v, d = venue.resolve(env=good)
        assert d["chosen"] == "fake-live" and d["real_money"] is True, d
        assert "REAL MONEY" in venue.banner(d)
    finally:
        venue._REGISTRY.pop("fake-live", None)


def test_a_venue_that_disagrees_with_its_registration_refuses_to_trade():
    class Liar(venue.Venue):
        name = "liar"
        is_real_money = True                 # claims real
        def account(self): return {}
        def positions(self): return []
        def position(self, s): return None
        def market_order(self, s, side, q, **k): return {}
        def place_stop(self, s, lvl, **k): return {}
        def close_position(self, s, q=None, **k): return {}
        def orders(self): return []
        def fills(self): return []

    venue.register("liar", lambda **k: Liar(), real_money=False)  # registered safe
    try:
        try:
            venue.resolve(env={"CRYPTOBOT_VENUE": "liar"})
        except RuntimeError as e:
            assert "contradiction" in str(e)
        else:
            raise AssertionError("it traded on a contradiction")
    finally:
        venue._REGISTRY.pop("liar", None)


def test_the_paper_engine_satisfies_the_interface():
    b, clock, feed = make()
    assert isinstance(b, venue.Venue)
    for m in ("account", "positions", "position", "market_order", "place_stop",
              "close_position", "orders", "fills", "misses"):
        assert callable(getattr(b, m)), m


def test_the_strategy_files_never_name_a_venue():
    """If tjr_bot has to know where it is trading, the abstraction is wrong."""
    import re
    for fname in ("tjr_bot.py", "tjr_crypto.py"):
        path = os.path.join(paper.REPO, fname)
        if not os.path.exists(path):
            continue
        for i, line in enumerate(open(path).read().splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or not s:
                continue
            if re.match(r"^(if|elif|while)\b", s) and re.search(
                    r"\b(alpaca|blofin|paper|venue|broker)\b", s, re.I):
                raise AssertionError(f"{fname}:{i} branches on a venue: {s}")


def test_the_alert_venue_records_but_never_places():
    """The forex answer: a market he executes by hand is an implementation,
    not a special case threaded through the method."""
    sent = []
    clock = Clock()
    feed = Feed(clock)
    feed.set("GBP/USD", 1.2700, 1.2702)
    eng = PaperBroker(state_path=None, log_path=None, quotes=feed, now=clock,
                      venue_label="alert")
    v = venue.AlertVenue(notify=lambda t, m: sent.append((t, m)), engine=eng)
    got = v.market_order("GBP/USD", "buy", 10_000)
    assert got["status"] == "filled"
    assert got["price"] == 1.2702, "still the ask, even here"
    assert got["human_executes"] is True, "nobody may mistake this for a machine fill"
    assert sent and "BUY GBP/USD" in sent[0][0]
    assert v.is_real_money is False


# ================================================================== RUNNER
TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main():
    passed, failed = 0, []
    for t in TESTS:
        try:
            t()
            passed += 1
            print(f"  ok    {t.__name__}")
        except Exception as e:                        # noqa: BLE001
            failed.append((t.__name__, e))
            print(f"  FAIL  {t.__name__}: {e}")
    print(f"\n{passed}/{len(TESTS)} passed")
    if failed:
        print("\nfailures:")
        for name, e in failed:
            print(f"  {name}: {type(e).__name__} {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
