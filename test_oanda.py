"""
test_oanda.py — the currency venue, proved without a token and without a
network.

WHAT IS PROVED HERE, AND WHY EACH ONE IS WORTH A TEST

  1. A PIP IS NOT ONE NUMBER. 0.0001 on the dollar majors, 0.01 on a yen
     cross, and gold different again — read from the broker, never assumed.
     A wrong pip is wrong by a factor of a hundred, not a rounding error.
  2. A PRICE AT THE WRONG PRECISION IS A DIFFERENT PRICE. Eleven pips on
     EUR/USD, or an outright rejection on GBP/JPY.
  3. THE STOP RIDES IN WITH THE ENTRY, in ONE request, on market AND limit.
     This is the bug this project already shipped once and must not ship
     again, so the test asserts the request COUNT, not just the contents.
  4. NO STOP, NO TRADE. Nothing is sent at all.
  5. THE CBOT_ TAG IS ON EVERY ORDER, so attribution.py's rule holds here.
  6. THE BOT ONLY TOUCHES WHAT IT OPENED. A foreign trade blocks opening,
     blocks closing, and blocks the stop — and the sealed client raises if
     anything reaches past the guard.
  7. THERE IS ONE SIZING FUNCTION. Not two. Two disagreed by 36 times once.
  8. THE REAL-MONEY GUARD. oanda-live is registered real money and cannot be
     built without the exact phrase.
  9. NO COST FILTERING. Nothing declines or ranks a trade on the spread.
 10. NO METHOD LEAKS IN. The venue is plumbing; it has no session, no
     window, no setup, no opinion about when to trade.

Repo style: plain asserts, a TESTS list, a main() runner. Also collects
cleanly under pytest. NO NETWORK — every OANDA call is a stand-in built in
memory, and a test that reached the real broker would be a test that could
place an order.
"""

from __future__ import annotations

import inspect
import sys
import traceback

sys.path.insert(0, "/Users/wallacechen/cryptobot")

import attribution
import blofin_private as bp
import oanda_api as ox
import venue as venue_mod

PRACTICE_ACCT = "101-001-1234567-001"
LIVE_ACCT = "001-011-5838423-001"

# EVERY resolve() IN THIS FILE CARRIES THIS, and it is not optional.
#
# The guard tests below deliberately ask for a real-money venue and expect to
# be dropped onto paper. Paper is a REAL engine with real state on disk, so a
# resolve() without these two writes paper_state.json and paper_fills.jsonl
# into the repo — which, if a paper week were running, means a test just
# wrote into live trading records. test_paper.py has a test whose whole job
# is to fail when that happens, and it caught this file doing it.
NO_DISK = {"state_path": None, "log_path": None}


# ===================================================== THE STAND-IN BROKER
class FakeOanda:
    """Everything OandaVenue reads or calls, recording instead of trading.

    It answers the way OANDA answers, including the awkward part: a REFUSAL
    comes back as a normal response containing a cancel transaction, not as
    an error. A stand-in that always succeeded would let the venue's
    "did it actually fill" check rot.
    """

    SPECS = {
        # pipLocation -4, prices to 5 decimals. The dollar majors.
        "GBP_USD": {"pip_location": -4, "display_precision": 5,
                    "units_precision": 0, "minimum_units": 1.0},
        "EUR_USD": {"pip_location": -4, "display_precision": 5,
                    "units_precision": 0, "minimum_units": 1.0},
        # pipLocation -2, prices to 3 decimals. THE YEN CROSS.
        "GBP_JPY": {"pip_location": -2, "display_precision": 3,
                    "units_precision": 0, "minimum_units": 1.0},
        # gold: its own conventions again, and it is not a currency pair.
        "XAU_USD": {"pip_location": -2, "display_precision": 3,
                    "units_precision": 2, "minimum_units": 1.0},
    }

    def __init__(self, practice=True, trades=None, fail_open_trades=False,
                 refuse=None, account_id=None):
        self.practice = practice
        self.account_id = account_id or (PRACTICE_ACCT if practice else LIVE_ACCT)
        self.host = ox.PRACTICE_HOST if practice else ox.LIVE_HOST
        self.name = "oanda-practice" if practice else "oanda-live"
        self._trades = list(trades or [])
        self._fail_open_trades = fail_open_trades
        self._refuse = refuse
        self.calls = []                 # every write call, in order

    # -- identity -----------------------------------------------------------
    def environment_check(self):
        return ox.OandaClient.environment_check(self)

    # -- reads --------------------------------------------------------------
    def summary(self):
        return {"NAV": "100000.0", "balance": "100000.0",
                "marginAvailable": "98000.0", "currency": "USD",
                "openTradeCount": len(self._trades), "hedgingEnabled": False}

    def spec(self, instrument):
        raw = self.SPECS.get(instrument)
        if not raw:
            return {}
        d = dict(raw)
        d["instrument"] = instrument
        d["pip"] = ox.pip_size(d["pip_location"])
        return d

    def pricing(self, instruments):
        book = {"GBP_USD": 1.27431, "EUR_USD": 1.08234, "GBP_JPY": 189.432,
                "XAU_USD": 2412.55, "USD_JPY": 145.10}
        out = {}
        for i in instruments:
            if i in book:
                mid = book[i]
                out[i] = {"bid": mid - 0.0001, "ask": mid + 0.0001,
                          "mid": mid, "spread": 0.0002, "tradeable": True}
        return out

    def usd_per_quote(self, instrument):
        return ox.OandaClient.usd_per_quote(self, instrument)

    def open_trades(self):
        if self._fail_open_trades:
            raise ox.OandaError("the connection dropped")
        return list(self._trades)

    # -- writes (recorded, never real) --------------------------------------
    def market_order(self, instrument, units, **kw):
        return self._entry("MARKET", instrument, units, **kw)

    def limit_order(self, instrument, units, *, limit_price, **kw):
        return self._entry("LIMIT", instrument, units,
                           limit_price=limit_price, **kw)

    def _entry(self, kind, instrument, units, **kw):
        # Build the body the way the real client does, so the test sees the
        # exact JSON that would go on the wire — that is the only way an
        # assertion about "the stop was in the SAME request" means anything.
        if not kw.get("stop_price"):
            raise ValueError("an opening order must carry its stop")
        order = {"type": kind, "instrument": instrument, "units": str(units),
                 "clientExtensions": {"id": kw["client_order_id"]},
                 "tradeClientExtensions": {"id": kw["trade_client_order_id"]},
                 "stopLossOnFill": {"price": str(kw["stop_price"]),
                                    "timeInForce": "GTC"}}
        if kind == "LIMIT":
            order["price"] = str(kw["limit_price"])
        if kw.get("take_profit"):
            order["takeProfitOnFill"] = {"price": str(kw["take_profit"])}
        self.calls.append(("create_order", order))
        if self._refuse:
            return {"orderCancelTransaction": {"reason": self._refuse}}
        if kind == "LIMIT":
            return {"orderCreateTransaction": {"id": "9001"}}
        return {"orderFillTransaction": {
            "id": "9002", "price": "1.27431", "units": str(units),
            "tradeOpened": {"tradeID": "77"}}}

    def set_trade_stop(self, trade_id, stop_price, **kw):
        self.calls.append(("set_trade_stop", trade_id, stop_price))
        return {"stopLossOrderTransaction": {"id": "9003"}}

    def close_trade(self, trade_id, units="ALL"):
        self.calls.append(("close_trade", trade_id, units))
        return {"orderFillTransaction": {"id": "9004"}}

    def cancel_order(self, order_id):
        self.calls.append(("cancel_order", order_id))
        return {}


def ours_trade(tid="77", inst="GBP_USD", units="10000", price="1.27431",
               stop=None):
    coid = bp.make_client_order_id("forex")
    t = {"id": tid, "instrument": inst, "currentUnits": units,
         "initialUnits": units, "price": price, "unrealizedPL": "12.5",
         "clientExtensions": {"id": coid}}
    if stop:
        t["stopLossOrder"] = {"price": str(stop)}
    return t


def his_trade(tid="88", inst="GBP_USD", units="5000"):
    """A trade Wallace placed by hand. OANDA returns no clientExtensions at
    all on those, which is exactly the case attribution must call HIS."""
    return {"id": tid, "instrument": inst, "currentUnits": units,
            "initialUnits": units, "price": "1.2700", "unrealizedPL": "-3.0"}


def build(**kw):
    fake = FakeOanda(**kw)
    return venue_mod.OandaVenue(client=fake), fake


def sig(**over):
    d = {"stop": 1.27000, "reference_price": 1.27431, "targets": [1.28000]}
    d.update(over)
    return d


# =============================== 1. A PIP IS NOT ONE NUMBER
def test_a_pip_is_read_from_the_broker_and_differs_per_pair():
    """The single fact that makes forex different from every other market
    this project trades, and the one that is wrong by a hundred if guessed."""
    assert ox.pip_size(-4) == 0.0001, "the dollar majors"
    assert ox.pip_size(-2) == 0.01, "every yen cross"

    v, _ = build()
    assert v.spec("GBP/USD")["pip"] == 0.0001
    assert v.spec("EUR/USD")["pip"] == 0.0001
    assert v.spec("GBP/JPY")["pip"] == 0.01, (
        "a yen cross was given the dollar-major pip. Every stop distance on "
        "it would be off by a factor of 100.")
    assert v.spec("XAU/USD")["pip"] == 0.01, "gold has its own convention"


def test_nothing_hardcodes_a_pip_size():
    """The number must come from the broker's own instrument list. A literal
    0.0001 in the order path is the bug wearing a disguise."""
    src = inspect.getsource(ox)
    body = src.split("class OandaClient")[1]
    assert "0.0001" not in body, (
        "a pip size is hardcoded in the client. It has to be read from "
        "pipLocation, per instrument, live.")


def test_an_instrument_the_account_cannot_trade_is_refused_even_though_its_candles_read():
    """MEASURED ON THE REAL ACCOUNT, 2026-07-26. Wallace's OANDA practice
    account carries 68 instruments and every one of them is a CURRENCY —
    XAU_USD is not among them, because a US-regulated retail forex account
    may not hold spot metals.

    The trap is that CANDLES FOR XAU_USD COME BACK FINE. That endpoint is
    account-independent, so gold looks perfectly available right up until an
    order is sent. A venue that read the price and assumed it could trade it
    would place an order that fails at the broker with a live signal on the
    table.

    The spec-is-{}-means-do-not-trade rule catches it, which is the whole
    reason that rule exists. This test pins the behaviour so it stays caught.
    """
    class NoGold(FakeOanda):
        SPECS = {k: v for k, v in FakeOanda.SPECS.items() if k != "XAU_USD"}

    fake = NoGold()
    v = venue_mod.OandaVenue(client=fake)
    assert v.spec("XAU/USD") == {}
    r = v.market_order("XAU/USD", "buy", 10,
                       stop=2400.0, reference_price=2412.55)
    assert r["status"] == "rejected"
    assert fake.calls == [], "it sent an order for an instrument it cannot trade"
    # and the pairs it CAN trade are unaffected
    assert v.spec("GBP/USD")["pip"] == 0.0001


def test_an_unreadable_spec_means_do_not_trade_not_a_default():
    v, fake = build()
    assert v.spec("XXX/YYY") == {}, "an unknown instrument must return {}"
    r = v.market_order("XXX/YYY", "buy", 10000, **sig())
    assert r["status"] == "rejected"
    assert "guess" in r["reason"]
    assert fake.calls == [], "it sent an order without knowing the pip size"


# ======================= 2. A PRICE AT THE WRONG PRECISION IS A DIFFERENT PRICE
def test_prices_are_formatted_at_each_instruments_own_precision():
    assert ox.fmt_price(1.082341, 5) == "1.08234", "EUR/USD wants 5 decimals"
    assert ox.fmt_price(189.4321, 3) == "189.432", "GBP/JPY wants 3"
    assert ox.fmt_price(2412.5512, 3) == "2412.551", "gold wants 3"
    # And the failure this prevents, stated as a number: formatting a
    # EUR/USD price to 3 places moves it 3.4 pips, as a MOVE IN THE PRICE.
    wrong = float(ox.fmt_price(1.082341, 3))
    assert abs(wrong - 1.082341) / 0.0001 > 3.0


def test_the_stop_goes_out_at_the_pairs_own_precision():
    v, fake = build()
    v.market_order("GBP/JPY", "buy", 10000,
                   **sig(stop=189.1234, reference_price=189.432,
                         targets=[190.5]))
    order = fake.calls[0][1]
    assert order["stopLossOnFill"]["price"] == "189.123", (
        f"the yen-cross stop went out as "
        f"{order['stopLossOnFill']['price']!r}, which this broker rejects")


def test_units_snap_down_never_up_and_refuse_below_the_minimum():
    """Down, never up: rounding up puts more on the line than the size that
    was worked out, and the size was worked out against a stop."""
    assert ox.fmt_units(10000.9, 0, 1.0) == "10000"
    assert ox.fmt_units(-10000.9, 0, 1.0) == "-10000"
    assert ox.fmt_units(0.4, 0, 1.0) is None, "it rounds to nothing"
    assert ox.fmt_units(5.0, 0, 10.0) is None, "it is under the minimum"
    assert ox.fmt_units(1.257, 2, 1.0) == "1.25", "gold trades in hundredths"


# ================ 3. THE STOP RIDES IN WITH THE ENTRY, IN ONE REQUEST
def test_the_stop_is_in_the_same_request_as_the_market_entry():
    """THE BUG WE ALREADY SHIPPED ONCE. A separate second call leaves a
    window in which the position exists with nothing under it. The assertion
    is on the request COUNT, because that is the thing that was wrong."""
    v, fake = build()
    r = v.market_order("GBP/USD", "buy", 10000, **sig())
    assert r["status"] == "filled"
    assert len(fake.calls) == 1, (
        f"the entry took {len(fake.calls)} requests. The stop must ride in "
        f"with the entry, not follow it.")
    kind, order = fake.calls[0]
    assert kind == "create_order"
    assert order["type"] == "MARKET"
    assert order["stopLossOnFill"]["price"] == "1.27000"
    assert r["stop_attached_to_entry"] is True


def test_the_stop_is_in_the_same_request_as_a_limit_entry_too():
    """It matters MORE on a limit, not less: a resting order can fill at
    three in the morning with nothing watching it, and the broker puts the
    stop on at the instant of the fill."""
    v, fake = build()
    r = v.market_order("GBP/USD", "buy", 10000,
                       **sig(limit_price=1.26500, stop=1.26000))
    assert len(fake.calls) == 1, "a limit entry took more than one request"
    order = fake.calls[0][1]
    assert order["type"] == "LIMIT"
    assert order["price"] == "1.26500"
    assert order["stopLossOnFill"]["price"] == "1.26000"
    assert r["status"] == "resting", (
        "a limit that has not filled was recorded as something else. Calling "
        "it filled makes the bot manage a position it does not hold; calling "
        "it rejected loses an order that is live at the broker.")
    assert r["stop_attached_to_entry"] is True


def test_the_client_itself_refuses_to_build_an_entry_with_no_stop():
    """The venue refuses first, but the layer underneath refuses too. One
    guard is a promise; two is a design."""
    cli = ox.OandaClient("tok", PRACTICE_ACCT)
    for kind in ("MARKET", "LIMIT"):
        try:
            cli._entry_order(kind, "GBP_USD", "1000", client_order_id="CBOT_fx_1",
                             trade_client_order_id="CBOT_fx_2", stop_price="",
                             limit_price="1.2")
            raise AssertionError(f"a {kind} order was built with no stop")
        except ValueError as e:
            assert "stop" in str(e)


# ============================================ 4. NO STOP, NO TRADE
def test_an_opening_order_with_no_stop_is_not_sent_at_all():
    v, fake = build()
    r = v.market_order("GBP/USD", "buy", 10000, reference_price=1.27431)
    assert r["status"] == "rejected"
    assert r["refused_by"] == "no stop"
    assert fake.calls == [], "a naked position was opened"


def test_a_stop_on_the_wrong_side_is_not_sent_at_all():
    v, fake = build()
    r = v.market_order("GBP/USD", "buy", 10000,
                       **sig(stop=1.28000, reference_price=1.27431))
    assert r["status"] == "rejected"
    assert r["refused_by"] == "stop on the wrong side"
    assert fake.calls == []

    v2, fake2 = build()
    r2 = v2.market_order("GBP/USD", "sell", 10000,
                         **sig(stop=1.26000, reference_price=1.27431))
    assert r2["status"] == "rejected"
    assert fake2.calls == []


def test_a_size_that_rounds_to_nothing_is_not_sent():
    v, fake = build()
    r = v.market_order("GBP/USD", "buy", 0.4, **sig())
    assert r["status"] == "rejected"
    assert "Too small" in r["reason"]
    assert fake.calls == []


# ================================================ 5. THE CBOT_ TAG
def test_every_order_carries_the_cbot_tag_that_attribution_reads():
    v, fake = build()
    v.market_order("GBP/USD", "buy", 10000, **sig())
    order = fake.calls[0][1]
    for where in ("clientExtensions", "tradeClientExtensions"):
        coid = order[where]["id"]
        assert coid.startswith("CBOT_"), f"{where} is not tagged: {coid!r}"
        assert attribution.is_ours_coid(coid), (
            f"attribution.py would not recognise {coid!r} as ours, so the "
            f"bot could never close what it just opened")
    assert attribution.tag_of(order["clientExtensions"]["id"]) == "fx"
    assert attribution.book_for_tag("fx") == "forex"


def test_the_two_ids_are_distinct():
    """The order and the trade get their own ids. A broker that rejects a
    duplicate client id would refuse the whole entry."""
    v, fake = build()
    v.market_order("GBP/USD", "buy", 10000, **sig())
    o = fake.calls[0][1]
    assert o["clientExtensions"]["id"] != o["tradeClientExtensions"]["id"]


def test_the_client_refuses_an_untagged_order():
    cli = ox.OandaClient("tok", PRACTICE_ACCT)
    try:
        cli._extensions("")
        raise AssertionError("an untagged order was allowed")
    except ValueError as e:
        assert "attribution" in str(e)


# ============ 6. THE BOT ONLY EVER TOUCHES WHAT IT OPENED
def test_his_trade_blocks_opening_on_that_instrument():
    """OANDA nets unless hedging is on, so an order the other way would
    CLOSE his trade rather than open beside it. That is the 2026-07-25
    incident in a new market."""
    v, fake = build(trades=[his_trade()])
    r = v.market_order("GBP/USD", "buy", 10000, **sig())
    assert r["status"] == "rejected"
    assert r["refused_by"] == "attribution"
    assert fake.calls == [], "it opened on top of his position"


def test_his_trade_is_invisible_to_positions_and_named_in_foreign():
    v, _ = build(trades=[his_trade()])
    assert v.positions() == [], "his trade showed up as ours"
    assert v.position("GBP/USD") is None
    foreign = v.foreign_positions()
    assert len(foreign) == 1
    assert "did not open it" in foreign[0]["why_not_ours"]


def test_our_trade_is_visible_and_signed():
    v, _ = build(trades=[ours_trade(units="-10000")])
    pos = v.position("GBP/USD")
    assert pos is not None
    assert pos["qty"] == -10000.0, "a short must come back signed negative"
    assert pos["trade_ids"] == ["77"]


def test_closing_his_trade_is_refused_and_nothing_is_sent():
    v, fake = build(trades=[his_trade()])
    r = v.close_position("GBP/USD")
    assert r["status"] == "rejected"
    assert r["refused_by"] == "attribution"
    assert fake.calls == [], "it reached his position"


def test_putting_a_stop_on_his_trade_is_refused():
    """Touching his stop changes what happens to his money even though it
    closes nothing by itself."""
    v, fake = build(trades=[his_trade()])
    r = v.place_stop("GBP/USD", 1.26)
    assert r["status"] == "rejected"
    assert r["refused_by"] == "attribution"
    assert fake.calls == []


def test_a_failed_read_resolves_to_hands_off():
    """AMBIGUITY RESOLVES TO HANDS OFF. A read that did not happen is not
    evidence that a trade is ours."""
    v, fake = build(trades=[ours_trade()], fail_open_trades=True)
    assert v.positions() == []
    assert v.close_position("GBP/USD")["status"] == "rejected"
    assert v.market_order("GBP/USD", "buy", 10000, **sig())["status"] == "rejected"
    assert fake.calls == []


def test_the_sealed_client_raises_if_anything_reaches_past_the_guard():
    """A runtime wall, not a convention. A future edit that skips the guard
    crashes loudly in a test instead of quietly trading."""
    v, _ = build(trades=[ours_trade()])
    for call, args in (("close_trade", ("77", "ALL")),
                       ("set_trade_stop", ("77", "1.26")),
                       ("cancel_order", ("9001",))):
        try:
            getattr(v._cli, call)(*args)
            raise AssertionError(f"{call} ran without the attribution guard")
        except venue_mod.NotOurs as e:
            assert "guard" in str(e)


def test_the_door_shuts_again_even_when_the_action_raises():
    v, _ = build(trades=[ours_trade()])

    def boom(_ours):
        raise RuntimeError("something went wrong mid-close")
    try:
        v._guarded_reduce("GBP/USD", "close", boom)
    except RuntimeError:
        pass
    assert object.__getattribute__(v._cli, "open_for") is None, (
        "the guard was left open after a failure. Everything after this "
        "point could reduce a position without being checked.")


def test_closing_goes_by_trade_id_never_by_instrument():
    """OANDA has an endpoint that flattens a whole instrument and it would
    take his trade off with ours. It is not wrapped at all."""
    assert not hasattr(ox.OandaClient, "close_position"), (
        "a flatten-the-instrument call was added to the client. It cannot "
        "tell our trade from his.")
    src = inspect.getsource(ox)
    assert "/positions/" not in src, "the position-level endpoint is reachable"

    v, fake = build(trades=[ours_trade()])
    r = v.close_position("GBP/USD")
    assert r["status"] == "filled"
    assert fake.calls == [("close_trade", "77", "ALL")]


def test_a_partial_close_is_first_class():
    v, fake = build(trades=[ours_trade(units="10000")])
    r = v.close_position("GBP/USD", 4000, reason="first target")
    assert r["status"] == "filled"
    assert fake.calls == [("close_trade", "77", "4000")]
    assert r["qty"] == 4000.0


def test_the_stop_call_says_it_was_already_on_from_the_entry():
    """It is a confirmation here, not the first protection, and the record
    must not imply otherwise."""
    v, fake = build(trades=[ours_trade(stop=1.27000)])
    r = v.place_stop("GBP/USD", 1.27000)
    assert r["status"] == "placed"
    assert fake.calls == [], "it replaced a stop that was already correct"
    assert r["trades"][0]["already_there"] is True
    assert "never a moment without one" in r["note"]


def test_moving_the_stop_does_reach_the_broker():
    v, fake = build(trades=[ours_trade(stop=1.27000)])
    r = v.place_stop("GBP/USD", 1.27431)
    assert r["status"] == "placed"
    assert fake.calls == [("set_trade_stop", "77", "1.27431")]


# ==================================== 7. THERE IS ONE SIZING FUNCTION
def test_sizing_goes_through_the_one_sizing_function():
    """Until 2026-07-26 this project had two and they disagreed by up to 36
    times, which meant every backtest described a bot nobody was running."""
    import tjr_alerts
    v, _ = build()
    seen = {}
    sentinel = {"ok": True, "units": 12345.0, "_sentinel": True}

    def spy(**kw):
        seen.update(kw)
        return sentinel
    real = tjr_alerts.position_size
    tjr_alerts.position_size = spy
    try:
        out = v.size_for("GBP/USD", 100000.0, 1.27431, 1.27000, 0.0015)
    finally:
        tjr_alerts.position_size = real
    assert out is sentinel, "size_for did not return what position_size gave it"
    assert seen["market"] == "currencies"
    assert abs(seen["stop_distance"] - 0.00431) < 1e-9


def test_there_is_no_second_sizing_path_to_fall_back_to():
    """If the one function is gone, sizing FAILS. It does not quietly
    compute a number of its own."""
    import tjr_alerts
    v, _ = build()

    def gone(**kw):
        raise RuntimeError("the one sizing function is unavailable")
    real = tjr_alerts.position_size
    tjr_alerts.position_size = gone
    try:
        v.size_for("GBP/USD", 100000.0, 1.27431, 1.27000, 0.0015)
        raise AssertionError("size_for produced a size without position_size. "
                            "There is a second sizing path.")
    except RuntimeError as e:
        assert "one sizing function" in str(e)
    finally:
        tjr_alerts.position_size = real


def test_the_yen_conversion_is_supplied_and_is_not_one():
    """A GBP/JPY trade's profit and loss both arrive in YEN. Sized as though
    they arrived in dollars the position is wrong by the yen rate — a factor
    of about 145."""
    import tjr_alerts
    v, _ = build()
    seen = {}

    def spy(**kw):
        seen.update(kw)
        return {"ok": True, "units": 1.0}
    real = tjr_alerts.position_size
    tjr_alerts.position_size = spy
    try:
        v.size_for("GBP/JPY", 100000.0, 189.432, 189.100, 0.0015)
        yen = seen["usd_per_quote"]
        v.size_for("GBP/USD", 100000.0, 1.27431, 1.27000, 0.0015)
        usd = seen["usd_per_quote"]
    finally:
        tjr_alerts.position_size = real
    assert usd == 1.0, "a dollar-quoted pair must convert at 1"
    assert abs(yen - 1.0 / 145.10) < 1e-9, (
        f"the yen rate came through as {yen}. Passing 1.0 here sizes the "
        f"position about 145 times wrong.")


def test_a_rate_that_cannot_be_read_refuses_rather_than_assuming_one():
    v, fake = build()
    fake.pricing = lambda instruments: {}
    out = v.size_for("GBP/JPY", 100000.0, 189.432, 189.100, 0.0015)
    assert out["ok"] is False
    assert "refused rather than guessed" in out["why"]


def test_the_four_pairs_all_have_a_pip_the_message_layer_can_read():
    """tjr_alerts.pip_size raises on an unknown pair, so a pair the venue can
    trade but the message layer cannot describe is a crash waiting for the
    first signal."""
    import tjr_alerts
    for pair in venue_mod.OandaVenue.PAIRS:
        assert tjr_alerts.pip_size(pair) > 0, f"{pair} has no pip on record"
    assert tjr_alerts.pip_size("GBP/JPY") == 0.01
    assert tjr_alerts.pip_size("EUR/USD") == 0.0001


# ================================================ 8. THE REAL-MONEY GUARD
def test_the_practice_venue_is_registered_as_not_real_money():
    reg = venue_mod.registered()
    assert reg["oanda-practice"]["real_money"] is False
    assert reg["oanda-live"]["real_money"] is True


def test_the_live_venue_cannot_be_built_without_the_exact_phrase():
    for env in ({}, {"CRYPTOBOT_REAL_MONEY": "true"},
                {"CRYPTOBOT_REAL_MONEY": "1"},
                {"CRYPTOBOT_REAL_MONEY": "yes-trade-real-money "}):
        cfg = dict(env, CRYPTOBOT_VENUE="oanda-live")
        v, d = venue_mod.resolve(env=cfg, **NO_DISK)
        assert d["chosen"] == "paper", (
            f"{env!r} reached a real-money venue. Only the exact phrase may.")
        assert d["real_money"] is False


def test_the_exact_phrase_does_reach_it_and_it_is_the_same_class():
    """The whole design premise: going real is a config value, not a rewrite.
    If this ever needed a different class, the practice week proved nothing."""
    cfg = {"CRYPTOBOT_VENUE": "oanda-live",
           "CRYPTOBOT_REAL_MONEY": venue_mod.LIVE_CONFIRM_PHRASE}
    v, d = venue_mod.resolve(env=cfg, client=FakeOanda(practice=False))
    assert d["chosen"] == "oanda-live"
    assert d["real_money"] is True
    assert isinstance(v, venue_mod.OandaVenue), (
        "the live venue is not the same class as the practice one, so the "
        "code that ran on practice is not the code that would run live")
    # And the ONLY thing that differs is the host. If more than that ever
    # differs, a week on practice stops being evidence about live.
    assert type(v).__mro__[1] is venue_mod.OandaVenue
    overrides = {k for k in vars(venue_mod.OandaLiveVenue)
                 if not k.startswith("__") and not k.startswith("_abc")}
    assert overrides == {"name", "is_real_money", "_PRACTICE"}, (
        f"the live venue overrides behaviour, not just the host: {overrides}. "
        f"Every method must be inherited, or the code that ran on practice "
        f"is not the code that runs live.")


def test_an_unknown_or_misspelled_venue_still_lands_on_paper():
    for name in ("oanda", "oanda-prac", "OANDA-LIVE-PLEASE", ""):
        _, d = venue_mod.resolve(env={"CRYPTOBOT_VENUE": name}, **NO_DISK)
        assert d["chosen"] == "paper", f"{name!r} did not resolve to paper"


def test_the_practice_host_is_the_default_and_live_takes_saying_so():
    assert ox.OandaClient("tok", PRACTICE_ACCT).host == ox.PRACTICE_HOST
    assert ox.OandaClient("tok", LIVE_ACCT, practice=False).host == ox.LIVE_HOST


def test_the_host_and_the_account_number_must_agree():
    """Two independent facts. A practice venue holding a live account number
    does not construct at all."""
    try:
        venue_mod.OandaVenue(client=FakeOanda(practice=True,
                                              account_id=LIVE_ACCT))
        raise AssertionError("a practice venue was built on a live account id")
    except RuntimeError as e:
        assert "DISAGREE" in str(e)

    ok = ox.OandaClient("tok", PRACTICE_ACCT).environment_check()
    assert ok["agrees"] and ok["account_id_says"] == "practice"
    bad = ox.OandaClient("tok", "999-000-1-001").environment_check()
    assert bad["agrees"] is False and bad["recognised"] is False


def test_the_class_and_the_registry_cannot_disagree():
    assert venue_mod.OandaVenue.is_real_money is False
    assert venue_mod.OandaLiveVenue.is_real_money is True
    assert venue_mod.OandaLiveVenue._PRACTICE is False


# ============================================== 9. NO COST FILTERING
def test_nothing_declines_or_ranks_a_trade_on_what_it_costs():
    """Fees and the spread are CHARGED so the money stays honest, and they
    are never consulted. Wallace: if I told you don't worry about fees then
    don't worry about fees."""
    for mod in (ox,):
        src = inspect.getsource(mod)
        for bad in ("if spread >", "if spread <", "if fee >", "if fee <",
                    "spread >", "cost >"):
            assert bad not in src, f"{mod.__name__} decides on cost ({bad})"
    block = inspect.getsource(venue_mod.OandaVenue)
    for bad in ("spread >", "spread <", "fee >", "fee <", "cost >"):
        assert bad not in block, f"OandaVenue decides on cost ({bad})"


# ======================================= 10. NO METHOD LEAKS INTO PLUMBING
def test_the_venue_holds_no_strategy_of_any_kind():
    """It takes an order and places it. It has no view on which pair, which
    hour, or what a setup looks like — so whatever drives currencies can be
    swapped out entirely without a line in here moving."""
    for src in (inspect.getsource(ox), inspect.getsource(venue_mod.OandaVenue)):
        low = src.lower()
        for bad in ("09:50", "09:30", "10:30", "london session",
                    "new york open", "premarket", "pre-market",
                    "break of structure", "liquidity sweep", "order block",
                    "fair value gap", "daily bias"):
            assert bad not in low, (
                f"a trading method leaked into the venue ({bad!r}). The venue "
                f"is plumbing; the strategy lives somewhere else.")


def test_the_venue_implements_the_whole_interface():
    """Seven calls, one vocabulary. A venue missing one is a venue the desk
    crashes on at the worst possible moment."""
    for name in ("account", "positions", "position", "market_order",
                 "place_stop", "close_position", "orders", "fills", "misses"):
        assert callable(getattr(venue_mod.OandaVenue, name, None)), name
    assert not inspect.isabstract(venue_mod.OandaVenue)
    v, _ = build(trades=[ours_trade()])
    assert isinstance(v, venue_mod.Venue)


def test_the_audit_trail_records_refusals_as_well_as_fills():
    v, _ = build(trades=[his_trade()])
    v.market_order("GBP/USD", "buy", 10000, **sig())
    assert len(v.orders()) == 1
    assert v.fills() == []
    assert len(v.misses()) == 1
    assert len(v.refusals()) == 1


def test_a_broker_refusal_is_never_read_as_a_fill():
    """OANDA answers a refusal with a normal response containing a cancel
    transaction. Read as a fill, the bot manages a position it does not
    hold."""
    v, _ = build(refuse="MARKET_HALTED")
    r = v.market_order("GBP/USD", "buy", 10000, **sig())
    assert r["status"] == "rejected"
    assert "MARKET_HALTED" in r["reason"]
    assert v.fills() == []


def test_the_account_reads_back_in_the_interfaces_vocabulary():
    v, _ = build()
    a = v.account()
    assert a["venue"] == "oanda-practice"
    assert a["real_money"] is False
    assert a["equity"] == 100000.0
    assert a["open_risk"] == 0.0
    assert "share" not in a["open_risk_note"].lower() or "dollars" in a["open_risk_note"]


def test_open_risk_counts_only_stops_the_bot_placed():
    v, _ = build(trades=[ours_trade(units="10000", stop=1.27000)])
    assert v.open_risk() == 0.0, "nothing is at risk before the bot places one"
    v.place_stop("GBP/USD", 1.27000)
    risk = v.open_risk()
    assert risk > 0
    # 10,000 units, mark 1.27431, stop 1.27000 -> 0.00431 * 10,000 = $43.10
    assert abs(risk - 43.10) < 0.01, risk


def test_the_env_prefix_is_registered_so_render_can_see_the_keys():
    """A prefix missing from load_env's list makes the variable invisible to
    the whole program, silently. ALPACA_ was missing for a day and nearly
    broke a Monday morning."""
    src = inspect.getsource(bp.load_env)
    assert '"OANDA_"' in src, (
        "OANDA_ is not in load_env's prefix list, so the keys would read "
        "back as missing on Render no matter how they were set")
    import os as _os
    _os.environ["OANDA_API_TOKEN"] = "probe-value"
    try:
        assert bp.load_env("/nonexistent/.env").get("OANDA_API_TOKEN") == "probe-value"
        assert ox.missing_keys({"OANDA_API_TOKEN": "t"}) == ["OANDA_ACCOUNT_ID"]
        assert ox.missing_keys({"OANDA_API_TOKEN": "t",
                                "OANDA_ACCOUNT_ID": PRACTICE_ACCT}) == []
    finally:
        _os.environ.pop("OANDA_API_TOKEN", None)


def test_the_smoke_script_cannot_place_an_order():
    """Wallace's account ends the night with zero orders placed by us."""
    import step468_oanda_smoke as smoke
    src = inspect.getsource(smoke)
    for bad in ("market_order", "limit_order", "close_trade", "set_trade_stop",
                "cancel_order", "_post(", "_put("):
        assert bad not in src, f"the smoke test can reach {bad}"


def test_history_never_returns_bars_from_after_the_end_it_was_asked_for():
    """CAUGHT ON THE REAL API, 2026-07-26. Paging asks for 5,000 bars at a
    time from a moving cursor, so the last page always overshoots — a
    one-month request came back with two and a half extra weeks on it.

    Left untrimmed that is a look-ahead bug in its most dangerous form: it
    does not crash, it just quietly hands a backtest data from after the
    window it asked for, and the results come out better than they were.
    """
    import datetime as _dt
    cli = ox.OandaClient("tok", PRACTICE_ACCT)
    pages = []

    def fake_get(path, params=None):
        # Two pages of hourly bars from 1 June, deliberately running well
        # past the 8 June boundary the caller asks for.
        start = _dt.datetime(2026, 6, 1, tzinfo=_dt.timezone.utc) + \
            _dt.timedelta(hours=200 * len(pages))
        rows = [{"time": (start + _dt.timedelta(hours=i)).strftime(
                     "%Y-%m-%dT%H:%M:%S.000000000Z"),
                 "complete": True, "volume": 10,
                 "mid": {"o": "1.1", "h": "1.2", "l": "1.0", "c": "1.15"}}
                for i in range(200)]
        pages.append(rows)
        return {"candles": rows} if len(pages) <= 2 else {"candles": []}

    cli._get = fake_get
    out = cli.history("GBP_USD", "H1",
                      start=_dt.datetime(2026, 6, 1, tzinfo=_dt.timezone.utc),
                      end=_dt.datetime(2026, 6, 8, tzinfo=_dt.timezone.utc))
    assert len(out), "the walk returned nothing at all"
    # 8 June 00:00 UTC is 7 June 20:00 New York, and `t` is New York.
    limit = __import__("pandas").Timestamp("2026-06-07 20:00:00")
    assert out["t"].max() <= limit, (
        f"history returned bars up to {out['t'].max()}, past the {limit} "
        f"boundary it was asked for. That is a look-ahead bug.")
    assert out["t"].is_monotonic_increasing
    assert out["t"].duplicated().sum() == 0, "pages overlapped"


def test_history_refuses_to_walk_without_a_start():
    cli = ox.OandaClient("tok", PRACTICE_ACCT)
    try:
        cli.history("GBP_USD", "H1")
        raise AssertionError("it walked from nowhere")
    except ValueError as e:
        assert "start" in str(e)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]


def main() -> int:
    passed, failed = 0, []
    for t in TESTS:
        try:
            t()
            passed += 1
            print(f"  ok    {t.__name__}")
        except Exception:                                      # noqa: BLE001
            failed.append(t.__name__)
            print(f"  FAIL  {t.__name__}")
            traceback.print_exc()
    print(f"\n{passed} passed, {len(failed)} failed")
    for f in failed:
        print(f"  - {f}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
