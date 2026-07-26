"""
test_tjr_desk.py — the desk TRADES now, so what gets tested is the sizing,
the messages, and the fact that every order leaves through the one door.

CHANGED 2026-07-25. Wallace: "lets do stocks with alpaca on trading view and
crypto on blofin, both ran by api." The old rule tested here was "no order
path anywhere in the alerting files". That rule is gone, replaced by a
stricter one that is easier to break by accident and so is worth more:
NOTHING OUTSIDE venue.py MAY NAME A VENUE OR AN EXCHANGE ENDPOINT. The desk
calls the interface; the interface decides where the order goes.

The safety rule that outranks all of this — the bot may only touch a position
it opened itself — is proved in test_attribution.py, not here.

WHAT IS PROVED HERE
    1. THE SET SIZE IS HIS RULE, NOT THE OBVIOUS ONE. Size is worked out once
       off the tightest stop the instrument normally gives, so that stop
       costs one percent of the account — and then HELD. A wider stop that
       day risks two or three percent and the size does not shrink. Checked
       by hand, on all four markets.
    2. THE TIGHTEST STOP IS EACH INSTRUMENT'S OWN. Never carried across.
    3. EVERY PERCENTAGE IS LABELLED as a move in the price or a share of the
       account, on every market, in every message.
    4. NO JARGON reaches the phone, on any market.
    5. NO SPAM. Several symbols firing together is one message; a signal
       already sent is never sent twice; nothing at all is sent when nothing
       happens.
    6. NO FILE OUTSIDE venue.py NAMES A VENUE or reaches an exchange
       endpoint directly, so switching where a market trades stays one
       string and never becomes a rewrite.
    7. AN UNARMED MARKET SENDS NOTHING while doing everything else.

Repo style: plain asserts, a TESTS list, a main() runner. No pytest, no
network — the desk is driven with stand-in markets built in memory.
"""

from __future__ import annotations

import datetime as dt
import inspect
import re
import sys
import traceback

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_alerts
import tjr_desk

ACC = 100_000.0


def sig(market, symbol, direction=-1, entry=100.0, stop=101.0,
        targets=(98.0, 96.0), tightest=0.005, risk_wanted=1000.0):
    return {"market": market, "symbol": symbol, "direction": direction,
            "reference_price": entry, "stop": stop, "targets": list(targets),
            "target_sources": ["a 15-minute draw on liquidity",
                               "a prev_day draw on liquidity"],
            "level_tf": "prev_day", "level_price": stop,
            "confirmed_by": "5-minute break of structure",
            "pullback_into": "the midpoint",
            "risk_dollars": 1000.0, "risk_wanted": risk_wanted,
            "tightest_stop_pct": tightest,
            # what the ORDER path reads, on top of what the message reads
            "side": "buy" if direction > 0 else "sell",
            "partial_fraction": 0.5}


# ============================================ 1. THE SET SIZE, BY HAND
def test_the_size_is_set_off_the_tightest_stop_not_off_todays_stop():
    """His rule, worked by hand. A fund at $400 whose tightest stop is 0.25%
    of price: that stop is $1.00, so one percent of a $100,000 account buys
    1,000 shares. THAT is the size, and it does not move.

    Today's stop is $2.00 — twice as wide. The size stays at 1,000 shares, so
    this trade risks $2,000, which is two percent OF THE ACCOUNT. Sizing per
    trade would have given 500 shares and one percent, and that is precisely
    the thing his rule rejects.
    """
    tight = tjr_alerts.position_size("gold", "GLD", ACC, 400.0, 1.00, 0.0025)
    assert abs(tight["units"] - 1000.0) < 1e-6, tight
    assert abs(tight["risk_dollars"] - 1000.0) < 1e-6
    assert abs(tight["risk_share_pct"] - 1.0) < 1e-9

    wide = tjr_alerts.position_size("gold", "GLD", ACC, 400.0, 2.00, 0.0025)
    assert abs(wide["units"] - tight["units"]) < 1e-9, \
        "the size shrank when the stop got wider — that is not his rule"
    assert abs(wide["risk_dollars"] - 2000.0) < 1e-6
    assert abs(wide["risk_share_pct"] - 2.0) < 1e-9
    assert abs(wide["wider"] - 2.0) < 1e-9


def test_a_three_percent_day_is_the_rule_working_and_is_said_out_loud():
    s = sig("gold", "GLD", entry=400.0, stop=403.0, tightest=0.0025)
    _, msg = tjr_alerts.entry_message(s, ACC)
    assert "3.00% OF THE ACCOUNT" in msg
    assert "MORE THAN ONE PERCENT ON PURPOSE" in msg, \
        "he would have discovered the three percent instead of being told"
    assert "Do not shrink it" in msg


def test_half_size_on_a_news_day_is_carried_through():
    s = sig("sp500", "SPY", entry=500.0, stop=502.0, tightest=0.002,
            risk_wanted=500.0)
    full = tjr_alerts.position_size("sp500", "SPY", ACC, 500.0, 2.0, 0.002, 1.0, 0.01)
    half = tjr_alerts.position_size("sp500", "SPY", ACC, 500.0, 2.0, 0.002, 1.0, 0.005)
    assert abs(half["units"] - full["units"] / 2) < 1e-9
    _, msg = tjr_alerts.entry_message(s, ACC)
    assert "HALF SIZE today" in msg


def test_the_yen_pair_converts_before_it_sizes():
    """GBP/JPY pays in yen. With GBP/USD at 1.34 and GBP/JPY at 200 a dollar
    per yen is 0.0067. A tightest stop of 0.06% of a price of 200 is 0.12
    yen, so one percent of $100,000 buys 1,000 / (0.12 x 0.0067) = 1,243,781
    pounds. Skipping the conversion would be out by the yen rate."""
    upq = 1.34 / 200.0
    s = tjr_alerts.position_size("currencies", "GBP/JPY", ACC, 200.0, 0.12,
                                 0.0006, upq)
    assert abs(s["units"] - 1_243_781.09) < 1.0, s
    assert abs(s["risk_dollars"] - 1000.0) < 0.01
    # every pip must be worth risk / stop-in-pips
    assert abs(s["per_step"] * 12 - 1000.0) < 0.01


def test_a_missing_tightest_stop_refuses_rather_than_guessing():
    """Sizing off another market's number is the one thing the rule forbids,
    so a market that has never been measured must produce no size at all."""
    s = tjr_alerts.position_size("crypto", "BTC/USD", ACC, 60000.0, 300.0, 0.0)
    assert s["ok"] is False
    _, msg = tjr_alerts.entry_message(sig("crypto", "BTC/USD", tightest=0.0), ACC)
    assert "COULD NOT BE WORKED OUT" in msg
    assert "do not take this one" in msg


def test_the_tightest_stop_is_measured_per_instrument_and_never_shared():
    floors = tjr_desk.stop_floors()
    assert floors, "no stop floors measured — run: python3 tjr_desk.py --derive-size"
    for sym in ("SPY", "BTC/USD", "GLD"):
        assert sym in floors, f"{sym} has no measured tightest stop"
    vals = {s: floors[s]["tightest_stop_pct"] for s in
            ("SPY", "BTC/USD", "GLD")}
    assert len(set(round(v, 6) for v in vals.values())) == len(vals), \
        f"two markets share a tightest stop, so one was ported: {vals}"
    for s, v in floors.items():
        assert 0 < v["tightest_stop_pct"] <= v["median_stop_pct"] <= \
            v["widest_stop_pct"], f"{s}: the tightest stop is not the tightest"


def test_the_size_only_changes_when_equity_or_the_measurement_does():
    """Not per trade. Two different stops on the same day give one size; a
    different account gives a proportionally different one."""
    # cap_share=0 switches OUR ceiling off, so this is his rule alone.
    a = tjr_alerts.position_size("crypto", "BTC/USD", ACC, 60000.0, 300.0,
                                 0.0035, cap_share=0)
    b = tjr_alerts.position_size("crypto", "BTC/USD", ACC, 60000.0, 900.0,
                                 0.0035, cap_share=0)
    assert abs(a["units"] - b["units"]) < 1e-9
    c = tjr_alerts.position_size("crypto", "BTC/USD", 200_000.0, 60000.0,
                                 300.0, 0.0035, cap_share=0)
    assert abs(c["units"] - 2 * a["units"]) < 1e-6


def test_the_cap_is_ours_and_it_says_so():
    """OUR ceiling on what one trade may risk, defaulting to 3% OF THE
    ACCOUNT — the top of the band he himself states. It must not touch an
    ordinary trade, it must bind on the tail, and when it binds BOTH numbers
    have to survive so nothing is quietly swapped."""
    ordinary = tjr_alerts.position_size("crypto", "BTC/USD", ACC, 60000.0,
                                        420.0, 0.0035)
    assert not ordinary["capped"], "the cap bound on an ordinary 2% trade"

    tail = tjr_alerts.position_size("crypto", "DOT/USD", ACC, 4.0,
                                    4.0 * 0.209, 0.00578)
    assert tail["capped"], "a stop 36x the tightest was not capped"
    assert tail["risk_share_pct"] <= 3.0 + 1e-9
    assert tail["uncapped_risk_share_pct"] > 30.0, tail
    lines = "\n".join(tjr_alerts.size_lines("crypto", "DOT/USD", tail, 4.0, ACC))
    assert "OURS" in lines and "CRYPTOBOT_MAX_RISK_PCT" in lines


def test_the_cap_can_be_switched_off():
    off = tjr_alerts.position_size("crypto", "DOT/USD", ACC, 4.0,
                                   4.0 * 0.209, 0.00578, cap_share=0)
    assert not off["capped"]
    assert off["risk_share_pct"] > 30.0


# ================================================ 2. THE MESSAGE ITSELF
def every_market_sample():
    return [sig("crypto", "BTC/USD", 1, 64000.0, 63700.0, (64400.0, 64700.0), 0.0035),
            sig("sp500", "SPY", -1, 745.0, 746.8, (741.7, 741.2), 0.002),
            sig("gold", "GLD", 1, 380.5, 376.7, (383.0, 386.0), 0.0025)]


def test_every_market_carries_everything_he_needs():
    for s in every_market_sample():
        title, msg = tjr_alerts.entry_message(s, ACC)
        label = tjr_alerts.MARKETS[s["market"]]["label"]
        assert msg.startswith(label), "the market is not the first thing he sees"
        assert label in title
        for must in ("Enter around", "Stop", "it sits", "First target",
                     "Second target", "Size", "OF THE ACCOUNT", "Why:",
                     "New York time"):
            assert must in msg, f"{s['market']} alert is missing: {must}"
        assert "the size is in" in msg, \
            f"{s['market']} does not say which instrument the size assumes"


def test_no_percentage_anywhere_is_left_unlabelled():
    ok = ("OF THE ACCOUNT", "MOVE IN THE PRICE", "of the account",
          "more than one percent")
    msgs = [tjr_alerts.entry_message(s, ACC)[1] for s in every_market_sample()]
    msgs.append(tjr_alerts.entry_message(
        sig("gold", "GLD", entry=400.0, stop=403.0, tightest=0.0025), ACC)[1])
    for msg in msgs:
        for line in msg.splitlines():
            if "%" in line:
                assert any(k in line for k in ok), \
                    f"a bare percentage reached the phone: {line!r}"


def test_no_jargon_reaches_the_phone_on_any_market():
    banned = ("invalidation", "bos", "fvg", "smt", "displacement", "poi",
              "ote", "liquidity", "equilibrium", "sweep", "swept", "book",
              "expectancy", "inducement")
    for s in every_market_sample():
        _, msg = tjr_alerts.entry_message(s, ACC)
        words = set(re.findall(r"[a-z]+", msg.lower()))
        for j in banned:
            assert j not in words, f"{s['market']}: jargon reached the phone: {j}"


def test_the_manage_messages_exist_for_every_market():
    for m in tjr_alerts.MARKETS:
        _, a = tjr_alerts.first_target_message(m, "X", 100.0, 105.0)
        assert "HALF" in a and "100" in a
        _, b = tjr_alerts.close_message(m, "X", 99.0, "because.")
        assert "Close it now" in b
        _, c = tjr_alerts.stopped_message(m, "X", 101.0)
        assert "stop" in c.lower()


# ==================================================== 3. NO SPAM
class _FakeVenue:
    """A venue that records instead of trading. It exists so the desk can be
    driven end to end with nothing on a network — and so a test can assert
    the strongest thing available, which is that nothing was sent."""

    name = "fake"
    is_real_money = False

    def __init__(self, equity=ACC):
        self._equity = equity
        self.sent: list = []

    def account(self):
        return {"venue": self.name, "equity": self._equity, "cash": self._equity}

    def positions(self):
        return []

    def foreign_positions(self):
        return []

    def position(self, symbol):
        return None

    def market_order(self, symbol, side, qty, **kw):
        self.sent.append(("market_order", symbol, side, qty))
        return {"status": "filled", "symbol": symbol, "side": side, "qty": qty}

    def place_stop(self, symbol, level, **kw):
        self.sent.append(("place_stop", symbol, level))
        return {"status": "placed", "symbol": symbol, "level": level}

    def close_position(self, symbol, qty=None, **kw):
        self.sent.append(("close_position", symbol, qty))
        return {"status": "filled", "symbol": symbol, "qty": qty}

    def cancel_stops(self, symbol, **kw):
        self.sent.append(("cancel_stops", symbol))
        return {"status": "done"}

    def orders(self):
        return []

    def fills(self):
        return []


class _FakeMarket(tjr_desk.Market):
    name = "crypto"
    symbols = ("BTC/USD", "ETH/USD")

    def __init__(self, sigs, venue=None):
        super().__init__(venue if venue is not None else _FakeVenue())
        self._sigs = sigs

    def frames(self):
        return {s: {"5m": pd.DataFrame(), "1m": pd.DataFrame()}
                for s in self.symbols}

    def decide(self, frames, now, account):
        return [dict(s, fired_at=pd.Timestamp("2026-07-24 10:00"),
                     entry_t=pd.Timestamp("2026-07-24 09:59"))
                for s in self._sigs]


class _Recorder(tjr_desk.Desk):
    """dry_run keeps it unarmed, so it decides, sizes, records and messages
    and sends nothing. Pass armed={"crypto"} with dry_run off to watch it
    trade against the fake venue."""

    def __init__(self, market, dry_run=True, armed=()):
        super().__init__(markets=[market], dry_run=dry_run, armed=set(armed))
        self.pushed = []

    def _push(self, title, message):
        self.pushed.append((title, message))


def test_two_symbols_firing_together_are_one_message():
    m = _FakeMarket([sig("crypto", "BTC/USD", 1, 64000.0, 63700.0,
                         (64400.0, 64700.0), 0.0035),
                     sig("crypto", "ETH/USD", 1, 3400.0, 3380.0,
                         (3450.0, 3500.0), 0.004)])
    d = _Recorder(m)
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    assert len(d.pushed) == 1, f"his phone buzzed {len(d.pushed)} times for one idea"
    body = d.pushed[0][1]
    assert "BTC/USD" in body and "ETH/USD" in body, "a symbol was dropped"
    assert "2 setups at once" in body


def test_the_same_signal_is_never_sent_twice():
    m = _FakeMarket([sig("crypto", "BTC/USD", 1, 64000.0, 63700.0,
                         (64400.0, 64700.0), 0.0035)])
    d = _Recorder(m)
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 1))
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 2))
    assert len(d.pushed) == 1, "the same setup was sent more than once"


def test_nothing_at_all_is_sent_when_nothing_happens():
    d = _Recorder(_FakeMarket([]))
    for k in range(5):
        d.poll_market(d.markets[0], dt.datetime(2026, 7, 24, 10, k))
    assert d.pushed == [], "the bot made noise on a quiet morning"


def test_a_shut_market_is_not_even_polled():
    class Shut(_FakeMarket):
        def open_now(self, now):
            return False

        def frames(self):
            raise AssertionError("a shut market was asked for bars")

    d = _Recorder(Shut([sig("crypto", "BTC/USD")]))
    assert d.poll_market(d.markets[0], dt.datetime(2026, 7, 25, 10, 0)) == []
    assert d.pushed == []


# ================================================ 4. NOTHING CAN ORDER
def test_nothing_but_the_desk_table_names_a_venue():
    """THE INVARIANT THAT REPLACED "no order path anywhere".

    The desk may name a venue exactly once per market, in the table at the
    top of the file, because something has to. The DECISION files may not
    reach an order path at all — if the method has to know where it is
    trading, the abstraction is wrong and the fix belongs in venue.py.

    WHERE THE PRICES COME FROM IS A DIFFERENT QUESTION and is deliberately
    not covered here. tjr_crypto reads its bars and its spreads from Alpaca
    while its orders go to BloFin; that is not a leak, it is the feed and the
    venue being separate things, which they have always been.
    """
    import tjr_bot
    import tjr_crypto
    import tjr_gold
    for mod in (tjr_bot, tjr_crypto, tjr_gold, tjr_alerts):
        src = inspect.getsource(mod)
        for bad in ("market_order", "submit_order", "place_tpsl",
                    "crypto_market_order", "BlofinDemoPrivate",
                    "/api/v1/trade/", "/v2/orders"):
            assert bad not in src, (
                f"{mod.__name__} reaches an order path ({bad}). "
                f"Only venue.py may.")


def test_the_desk_names_each_venue_once_and_only_in_the_table():
    src = inspect.getsource(tjr_desk)
    for name in ("blofin-demo", "alpaca-paper"):
        assert src.count(f'venue_name = "{name}"') >= 1
        assert f'"{name}"' not in src.split("class Desk:")[1], (
            f"{name} is named below the market table — the Desk must not "
            f"know which venue it is talking to")


def test_an_unarmed_market_decides_everything_and_sends_nothing():
    """Unarmed is not off. It sizes, records, and messages exactly as it
    would live — it just never reaches the venue."""
    v = _FakeVenue()
    m = _FakeMarket([sig("crypto", "BTC/USD", 1, 64000.0, 63700.0,
                         (64400.0, 64700.0), 0.0035)], venue=v)
    d = _Recorder(m)                      # dry_run -> unarmed
    fresh = d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    assert len(fresh) == 1, "it did not decide"
    assert fresh[0]["size"]["ok"], "it did not size"
    assert v.sent == [], f"an unarmed market reached the venue: {v.sent}"
    assert len(d.pushed) == 1, "it did not say what it did"
    assert "NOT SENT" in d.pushed[0][1]


def test_an_armed_market_places_the_entry_and_then_its_stop():
    """In that order, and both of them. A position with nothing under it is
    the one thing this method never has."""
    v = _FakeVenue()
    m = _FakeMarket([sig("crypto", "BTC/USD", 1, 64000.0, 63700.0,
                         (64400.0, 64700.0), 0.0035)], venue=v)
    d = _Recorder(m, dry_run=False, armed={"crypto"})
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    kinds = [x[0] for x in v.sent]
    assert kinds == ["market_order", "place_stop"], v.sent
    assert v.sent[1][2] == 63700.0, "the stop did not go where the method said"


def test_a_signal_that_only_says_direction_is_still_traded():
    """THE DECISION FILES DO NOT ALL SPEAK THE SAME WORD. tjr_crypto returns
    "side"; tjr_bot — which BOTH the index and gold run on — returns only
    "direction". The desk has to normalise that, and if it ever stops doing
    so, stocks and gold break while crypto keeps working, which is the worst
    shape a bug can have."""
    v = _FakeVenue()
    raw = sig("sp500", "SPY", -1, 745.0, 746.8, (741.7, 741.2), 0.002)
    raw.pop("side")
    raw.pop("partial_fraction")

    class _StockMarket(_FakeMarket):
        name = "sp500"
        symbols = ("SPY",)

    m = _StockMarket([raw], venue=v)
    d = _Recorder(m, dry_run=False, armed={"sp500"})
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    assert [x[0] for x in v.sent] == ["market_order", "place_stop"], v.sent
    assert v.sent[0][2] == "sell", "a short was sent as a buy"


def test_a_position_whose_stop_will_not_go_on_is_closed_again():
    """The one genuinely unprotected moment in a trade's life is between the
    entry filling and the stop resting. If the stop refuses, the position
    comes straight back off rather than sitting there naked."""
    v = _FakeVenue()

    def no_stop(symbol, level, **kw):
        v.sent.append(("place_stop", symbol, level))
        return {"status": "rejected", "reason": "the venue would not take it"}

    v.place_stop = no_stop
    m = _FakeMarket([sig("crypto", "BTC/USD", 1, 64000.0, 63700.0,
                         (64400.0, 64700.0), 0.0035)], venue=v)
    d = _Recorder(m, dry_run=False, armed={"crypto"})
    d.poll_market(m, dt.datetime(2026, 7, 24, 10, 0))
    assert [x[0] for x in v.sent] == ["market_order", "place_stop",
                                      "close_position"], v.sent
    assert "OPENED AND CLOSED AGAIN" in d.pushed[0][1]


def test_the_desk_never_edits_the_four_decision_files():
    """It wraps them. Other agents are inside those files and a shim that
    reached in and rebound one of their functions would be an edit with extra
    steps."""
    src = inspect.getsource(tjr_desk)
    for bad in ("tjr_bot.TjrBot =", "tjr_crypto.live_step =",
                "tjr_bot.live_step =", "tjr_gold.live_step =",
                "write_text", "to_parquet"):
        assert bad not in src, f"the desk reaches for {bad}"


def test_the_desk_writes_exactly_one_file_and_it_is_the_measured_sizes():
    """A watcher that writes is a watcher that can corrupt something. The
    only thing this one writes is the measured tightest stop per instrument,
    and only when it is asked to re-measure."""
    src = inspect.getsource(tjr_desk)
    opens = re.findall(r"(?<![_a-z])open\(([^)]*)\)", src)
    for o in opens:
        assert "STOP_FLOOR_PATH" in o, f"the desk opens something else: {o}"


TESTS = [(k, v) for k, v in sorted(globals().items())
         if k.startswith("test_") and callable(v)]


def main():
    print("=" * 78)
    print("test_tjr_desk.py — the alert is the product, so the alert is tested")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
            print("  PASS")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
    print("\n" + "=" * 78)
    if failed:
        print(f"{failed}/{len(TESTS)} TEST(S) FAILED")
        sys.exit(1)
    print(f"ALL {len(TESTS)} TESTS PASSED")


if __name__ == "__main__":
    main()
