"""
test_craig_live.py — the live Craig path, held to the standard the money needs.

THE ONE THAT MATTERS IS FIRST. `test_the_replay_and_the_live_engine_agree`
runs the same twelve months of candles through `craig_crypto.run_pair` (the
engine every number in step467 came out of) and through `craig_live.Engine`
(the engine that will actually place the orders), and fails on the first trade
where they differ by so much as a cent. The 36x sizing bug happened because a
replay and a live runner had separate arithmetic and nothing ever put their
answers side by side. This is that test.

THE REST, IN ORDER
  2. THE SHIPPING CONFIGURATION IS step467'S ROW and cannot drift: the 1-hour
     chart, his resting limit, his 1:4, all three session opens, 3% of equity.
  3. THE ORDER HAS A LIFE — 24 candles, then it dies; and it dies at once if
     price reaches where its stop belongs before it fills.
  4. THE STOP IS NEVER SECOND. Every opening order carries it, the venue
     refuses outright without it, and it is never sent as a separate call.
  5. ONE SIZING PATH — the desk's own call and the engine's own call return
     the identical number of coins on every trade of the shipping year.
  6. THE MESSAGE says what the order actually was.
  7. METHODS NEVER MIX. Crypto reaches Craig and only Craig; stocks and gold
     reach the TJR method and only that.
  8. NOTHING IS TOUCHED — no fetch, no order, no git, out of this file or the
     module it tests.
"""

from __future__ import annotations

import datetime as dt
import inspect
import os

import numpy as np
import pandas as pd
import pytest

import craig_crypto as cc
import craig_live as cl
import tjr_alerts
import tjr_desk

REPO = os.path.dirname(os.path.abspath(__file__))
SRC = inspect.getsource(cl)

YEAR = (pd.Timestamp("2025-07-27"), pd.Timestamp("2026-07-26"))
SHORT = (pd.Timestamp("2026-04-01"), pd.Timestamp("2026-07-26"))
PAIR = "BTC/USD"

_DATA: dict = {}
_BOTH: dict = {}


def data(pair):
    if pair not in _DATA:
        _DATA[pair] = cc.load(pair)
    return _DATA[pair]


def both(pair, window=YEAR):
    """The same candles down both paths, computed once per pair."""
    key = (pair, window)
    if key not in _BOTH:
        cfg = cl.live_config(pair)
        rep = cc.run_pair(pair, *window, cfg=cfg, data=data(pair))["trades"]
        liv = cl.replay_through_live(pair, *window, cfg=cfg,
                                     data=data(pair))["trades"]
        _BOTH[key] = (sorted(rep, key=lambda t: (t.entry_t, t.entry)),
                      sorted(liv, key=lambda t: (t.entry_t, t.entry)))
    return _BOTH[key]


def mk(rows, start="2026-03-02 00:00", minutes=60) -> pd.DataFrame:
    base = pd.Timestamp(start)
    return pd.DataFrame([{"t": base + pd.Timedelta(minutes=minutes * i),
                          "open": o, "high": h, "low": l, "close": c}
                         for i, (o, h, l, c) in enumerate(rows)])


# ============================ 1. THE REPLAY AND THE LIVE ENGINE AGREE
def test_the_replay_and_the_live_engine_agree():
    """THE test. Same candles, both engines, every trade, every field.

    A difference here is not a rounding question. It means the dollars in
    step467 describe a bot nobody is running, which is the exact failure this
    project has already paid for once.
    """
    compared = 0
    for pair in cl.PAIRS:
        rep, liv = both(pair)
        assert len(rep) == len(liv), (
            f"{pair}: the replay took {len(rep)} trades and the live engine "
            f"took {len(liv)}")
        for a, b in zip(rep, liv):
            for f in ("direction", "session", "outcome"):
                assert getattr(a, f) == getattr(b, f), \
                    f"{pair} {a.entry_t}: {f} differs"
            for f in ("entry_t", "exit_t"):
                assert pd.Timestamp(getattr(a, f)) == pd.Timestamp(getattr(b, f)), \
                    f"{pair} {a.entry_t}: {f} differs"
            for f in ("entry", "stop_at_risk", "target", "exit", "units",
                      "notional", "risk_dollars", "pnl", "cost", "r_multiple",
                      "equity_at_entry"):
                assert getattr(a, f) == pytest.approx(getattr(b, f), rel=1e-12,
                                                      abs=1e-9), \
                    f"{pair} {a.entry_t}: {f} differs"
            assert a.moved_to_breakeven == b.moved_to_breakeven, \
                f"{pair} {a.entry_t}: break even differs"
            compared += 1
    assert compared >= 100, f"only {compared} trades to compare"


def test_the_two_engines_book_the_same_dollars():
    """The headline, stated as one number: step467's +$21,944 on the shipping
    configuration, and the live engine reaches it to the cent."""
    r = l = 0.0
    for pair in cl.PAIRS:
        rep, liv = both(pair)
        r += sum(t.pnl for t in rep)
        l += sum(t.pnl for t in liv)
    assert l == pytest.approx(r, abs=1e-6)
    assert r > 0, "the shipping configuration is not the profitable one"
    assert round(r) == 21944, f"the shipping year moved: ${r:,.2f}"


def test_the_live_engine_reads_no_candle_after_the_one_it_is_on():
    """Corrupt every candle after the one being decided on. The engine's
    answer may not move — it is looking at a chart, not a future."""
    pair = PAIR
    cfg = cl.live_config(pair)
    d = cc.bars(data(pair), cfg.entry_tf)
    w = d[(d["t"] >= SHORT[0]) & (d["t"] <= SHORT[1])].reset_index(drop=True)
    clean = cl.Engine()
    clean._cfg[pair] = cfg
    checked = 0
    for i in range(cfg.context_bars, len(w)):
        acts = clean.on_bar(pair, w, i, 100_000.0)
        made = [a for a in acts if a["kind"] == "enter"]
        if not made:
            continue
        bad = w.copy()
        after = bad.index > i
        for col in ("open", "high", "low", "close"):
            bad.loc[after, col] = 1.0
        again = cl.Engine()
        again._cfg[pair] = cfg
        got = []
        for j in range(cfg.context_bars, i + 1):
            got += [a for a in again.on_bar(pair, bad, j, 100_000.0)
                    if a["kind"] == "enter"]
        assert got, f"{w['t'].iloc[i]}: the setup vanished with the future gone"
        assert got[-1]["working"].entry == pytest.approx(
            made[-1]["working"].entry), \
            f"{w['t'].iloc[i]}: the entry moved when the future was corrupted"
        checked += 1
    assert checked >= 5, f"only {checked} live signals to corrupt around"


# ================================ 2. THE SHIPPING CONFIGURATION IS FIXED
def test_the_shipping_configuration_is_step467s_profitable_row():
    assert cl.SHIPPING["entry_tf"] == "1h", "the chart moved off the 1-hour"
    assert cl.SHIPPING["entry_style"] == "fvg_midpoint", \
        "the entry moved off his resting limit at the gap midpoint"
    assert cl.SHIPPING["target_r"] == 4.0, "the target moved off 1:4"
    assert cl.SHIPPING["risk_pct_per_trade"] == 0.03, "the crypto dial moved"
    cfg = cl.live_config(PAIR)
    assert cfg.entry_tf == "1h" and cfg.target_r == 4.0
    assert cfg.entry_style == "fvg_midpoint"
    assert cfg.risk_pct_per_trade == 0.03
    assert cfg.buying_power_multiple is None, \
        "a buying-power cap was borrowed from a venue this engine does not use"


def test_all_three_session_opens_ship_and_crypto_runs_round_the_clock():
    cfg = cl.live_config(PAIR)
    assert set(cfg.sessions) == {"asia", "london", "new_york"}
    hours = set()
    for pair in cl.PAIRS:
        _, liv = both(pair)
        hours |= {pd.Timestamp(t.entry_t).hour for t in liv}
    assert len(hours) >= 8, \
        f"the live book only ever fires in {sorted(hours)} — this is not 24/7"
    assert tjr_desk.CryptoMarket.open_now(
        tjr_desk.CryptoMarket.__new__(tjr_desk.CryptoMarket),
        dt.datetime(2026, 7, 26, 3, 17)), "crypto has a bell it should not have"


def test_the_engine_does_nothing_until_an_hour_has_actually_closed():
    """The desk polls once a minute. The engine may act once an hour."""
    pair = PAIR
    cfg = cl.live_config(pair)
    d = cc.bars(data(pair), cfg.entry_tf)
    w = d[(d["t"] >= SHORT[0]) & (d["t"] <= SHORT[1])].reset_index(drop=True)
    eng = cl.Engine()
    eng._cfg[pair] = cfg
    eng.step(pair, w.iloc[:200].reset_index(drop=True), 100_000.0)
    acted, hours = 0, range(201, 900)
    for n in hours:
        got = eng.step(pair, w.iloc[:n].reset_index(drop=True), 100_000.0)
        acted += len(got)
        # asked again with nothing new, it must say nothing at all
        for _ in range(2):
            assert eng.step(pair, w.iloc[:n].reset_index(drop=True),
                            100_000.0) == [], \
                "the engine acted twice on the same candle"
    assert acted > 0, \
        f"the engine never acted at all across {len(hours)} closed hours"


def test_a_restart_never_replays_three_months_of_old_setups():
    """The feed hands back ninety-five days of candles. A process that has
    just started has no record of what it already acted on, and walking all
    of it would place orders for setups that formed in April."""
    pair = PAIR
    cfg = cl.live_config(pair)
    d = cc.bars(data(pair), cfg.entry_tf)
    w = d[(d["t"] >= SHORT[0]) & (d["t"] <= SHORT[1])].reset_index(drop=True)
    eng = cl.Engine()
    eng._cfg[pair] = cfg
    got = eng.step(pair, w, 100_000.0)
    for a in got:
        assert pd.Timestamp(a["at"]) == pd.Timestamp(w["t"].iloc[-1]), \
            (f"a fresh process acted on {a['at']}, which is "
             f"{(pd.Timestamp(w['t'].iloc[-1]) - pd.Timestamp(a['at'])).days} "
             f"days of history it should have adopted, not traded")


def test_a_half_built_candle_never_reaches_the_engine():
    """The live 5-minute feed's last row is usually the one still forming.
    Rolled into an hour it becomes an hour whose close is about to change,
    and every rule in this method is read off a close."""
    five = pd.DataFrame([
        {"t": pd.Timestamp("2026-07-26 00:00") + pd.Timedelta(minutes=5 * i),
         "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5}
        for i in range(14)])          # 00:00 .. 01:05 -> 01:00 is HALF an hour
    got = cl.working_chart({"5m": five}, cl.live_config(PAIR))
    assert list(got["t"]) == [pd.Timestamp("2026-07-26 00:00")], \
        "an hour that has not finished was handed to the engine"


# ======================================== 3. THE RESTING ORDER'S OWN LIFE
def test_the_resting_limit_lives_exactly_its_allotted_candles():
    cfg = cl.live_config(PAIR)
    assert cfg.entry_valid_bars == 24, "the limit's life moved off 24 candles"
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            bars = (pd.Timestamp(t.entry_t) - pd.Timestamp(t.setup.choch_t)) \
                / pd.Timedelta(hours=1)
            assert 1 <= bars <= cfg.entry_valid_bars, \
                f"{pair} {t.entry_t}: filled {bars} candles after the signal"


def test_an_expired_limit_is_cancelled_and_never_becomes_a_trade():
    """A setup whose limit is never reached must leave the book with a cancel
    and no position."""
    eng = cl.Engine()
    cfg = cl.live_config(PAIR)
    eng._cfg[PAIR] = cfg
    s = _fake_setup(entry=100.0, stop=98.0, target=108.0, choch_i=3)
    wk = cl.Working(pair=PAIR, session="new_york", direction=1, setup=s,
                    entry=100.0, stop=98.0, target=108.0,
                    placed_t=pd.Timestamp("2026-03-02 03:00"),
                    last_look_i=3 + cfg.entry_valid_bars,
                    equity_at_signal=100_000.0, units=1.0, risk_dollars=2.0)
    eng.working[PAIR] = [wk]
    # candles that never come back to 100 and never reach 98
    rows = [(105, 106, 101, 105)] * (5 + cfg.entry_valid_bars)
    d = mk(rows)
    acts = []
    for i in range(4, len(d)):
        acts += eng.on_bar(PAIR, d, i, 100_000.0)
    kinds = [a["kind"] for a in acts]
    assert "cancel" in kinds, "the limit was never cancelled"
    assert "filled" not in kinds and not eng.live.get(PAIR), \
        "an expired limit became a position"
    assert not eng.working.get(PAIR), "the dead order is still on the book"


def test_a_setup_dies_when_price_reaches_its_stop_before_the_limit_fills():
    eng = cl.Engine()
    cfg = cl.live_config(PAIR)
    eng._cfg[PAIR] = cfg
    s = _fake_setup(entry=100.0, stop=98.0, target=108.0, choch_i=3)
    eng.working[PAIR] = [cl.Working(
        pair=PAIR, session="new_york", direction=1, setup=s, entry=100.0,
        stop=98.0, target=108.0, placed_t=pd.Timestamp("2026-03-02 03:00"),
        last_look_i=3 + cfg.entry_valid_bars, equity_at_signal=100_000.0,
        units=1.0, risk_dollars=2.0)]
    d = mk([(105, 106, 101, 105)] * 4 + [(105, 105, 97.0, 99.0)])
    acts = eng.on_bar(PAIR, d, 4, 100_000.0)
    assert [a["kind"] for a in acts] == ["cancel"], \
        "a setup whose stop was reached first was not killed"
    assert not eng.live.get(PAIR)


def test_break_even_moves_the_stop_to_the_entry_and_never_against_the_trade():
    seen = 0
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            if not t.moved_to_breakeven:
                continue
            assert t.stop == pytest.approx(t.entry), \
                "break even did not put the stop at the entry price"
            if t.direction > 0:
                assert t.stop >= t.stop_at_risk
            else:
                assert t.stop <= t.stop_at_risk
            seen += 1
    assert seen >= 5, f"only {seen} break-even moves in the whole year"


def test_a_break_even_exit_never_books_a_loss_before_the_round_trip():
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            if t.outcome == "break even":
                assert t.r_multiple == pytest.approx(0.0, abs=1e-9)
                assert t.pnl + t.cost == pytest.approx(0.0, abs=1e-6)


def test_the_break_even_rule_is_the_replays_rule_word_for_word():
    """Live and replay must agree about WHICH candle moves the stop, not only
    that one eventually does."""
    for pair in cl.PAIRS:
        rep, liv = both(pair)
        for a, b in zip(rep, liv):
            assert a.moved_to_breakeven == b.moved_to_breakeven, \
                f"{pair} {a.entry_t}: the two engines disagree about break even"


# ============================================ 4. THE STOP IS NEVER SECOND
def test_every_signal_carries_its_stop_on_the_correct_side():
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            if t.direction > 0:
                assert t.stop_at_risk < t.entry, f"{pair} {t.entry_t}"
            else:
                assert t.stop_at_risk > t.entry, f"{pair} {t.entry_t}"


def test_the_resting_order_carries_its_stop_in_the_same_request():
    c = _FakeClient()
    v = _venue(c)
    rec = v.limit_order("BTC/USD", "buy", 0.5, 60000.0, stop=59500.0,
                        targets=[62000.0], reason="test")
    assert rec["status"] == "resting", rec
    assert len(c.limits) == 1, "the entry did not go on"
    sent = c.limits[0]
    assert sent["stop_price"] == 59500.0, \
        "the stop did not ride in with the resting entry"
    assert sent["take_profit"] == 62000.0
    assert c.brackets == [], \
        "a SECOND call placed the stop — that is the window the 26 July DOT " \
        "failure came through"
    assert str(sent["client_order_id"]).startswith("CBOT_"), \
        "the order is not tagged, so it cannot be proved to be the bot's"


def test_a_resting_entry_without_a_stop_is_not_sent():
    c = _FakeClient()
    rec = _venue(c).limit_order("BTC/USD", "buy", 0.5, 60000.0, reason="test")
    assert rec["status"] == "rejected" and rec["refused_by"] == "no stop"
    assert not c.touched_anything()


def test_a_resting_entry_with_the_stop_on_the_wrong_side_is_not_sent():
    c = _FakeClient()
    rec = _venue(c).limit_order("BTC/USD", "buy", 0.5, 60000.0, stop=60500.0)
    assert rec["status"] == "rejected"
    assert rec["refused_by"] == "stop on the wrong side"
    assert not c.touched_anything()


def test_the_resting_entry_cannot_be_sent_onto_someone_elses_position():
    """BloFin nets everything on a symbol into ONE position. Opening beside a
    position the bot cannot prove is its own would fuse the two."""
    import test_attribution as ta
    c = _FakeClient(position=ta.position_row(10.0), orders=[ta.order_row("")])
    rec = _venue(c).limit_order("BTC/USD", "buy", 0.5, 60000.0, stop=59500.0)
    assert rec["status"] == "rejected"
    assert rec["refused_by"] == "attribution"
    assert not c.touched_anything()


def test_a_cancel_only_ever_touches_an_order_the_bot_tagged():
    c = _FakeClient(pending_orders=[
        {"orderId": "ours", "clientOrderId": "CBOT_tjc_1785018742491000001"},
        {"orderId": "his", "clientOrderId": ""},
    ])
    rec = _venue(c).cancel_entry("BTC/USD", reason="expired")
    assert rec["cancelled"] == ["ours"]
    assert rec["left_alone"] == ["his"]
    assert [x["order_id"] for x in c.cancels] == ["ours"], \
        "the bot cancelled an order it did not place"


def test_the_limit_order_cannot_close_anything():
    """There is no reduce-only limit, on purpose: venue._SealedClient knows
    the reducing forms of market_order and post_only_order by name, and a
    third one it did not know about would go round the attribution guard."""
    import blofin_private as bp
    assert "reduce_only" not in inspect.signature(bp.limit_signature()).parameters \
        if hasattr(bp, "limit_signature") else True
    sig = inspect.signature(bp.BlofinDemoPrivate.limit_order)
    assert "reduce_only" not in sig.parameters, \
        "a reduce-only limit exists and the seal does not know about it"


def test_the_real_client_builds_a_resting_limit_with_its_stop_attached():
    """THE ACTUAL REQUEST BODY, from the real client class.

    Every other test on this path drives a fake client, and that is exactly
    how a NameError sat in `blofin_private.limit_order` for hours: two lines
    copied from `post_only_order` referred to a `reduce_only` argument this
    method does not have, so the very first real Craig order would have
    raised instead of resting. Nothing that mocks the client can catch that.
    This calls the real method with only the transport replaced.
    """
    import blofin_private as bp
    c = bp.BlofinDemoPrivate.__new__(bp.BlofinDemoPrivate)
    seen = {}

    def call(method, path, body=None, **kw):
        seen.update(method=method, path=path, body=body)
        return [{"code": "0", "orderId": "42"}]

    c._call = call
    c._mode_for = lambda s: "isolated"
    oid = bp.BlofinDemoPrivate.limit_order(
        c, "ETH-USDT", "buy", 12.3456, 1802.05,
        client_order_id="CBOT_tjc_1", lot_size=0.1,
        stop_price=1795.7, take_profit=1827.45, tick_size=0.01)
    assert oid == "42"
    b = seen["body"]
    assert seen["method"] == "POST" and seen["path"] == "/api/v1/trade/order"
    assert b["orderType"] == "limit" and b["price"] == "1802.05"
    # THE STOP AND THE TARGET RIDE IN WITH THE ENTRY, in one request
    assert b["slTriggerPrice"] == "1795.70" and b["slOrderPrice"] == "-1"
    assert b["tpTriggerPrice"] == "1827.45" and b["tpOrderPrice"] == "-1"
    assert b["clientOrderId"] == "CBOT_tjc_1", \
        "the order lost the tag that proves the position is the bot's"
    assert "reduceOnly" not in b, \
        "a resting entry that can shrink a position goes round the guard"


# ============================================== 5. ONE SIZING PATH
def test_the_desk_and_the_engine_size_every_trade_identically():
    """The desk's own sizing call, on the desk's own signal, must return the
    coins the engine booked. This is the drift the 36x bug came through."""
    desk = tjr_desk.Desk(dry_run=True, markets=[], armed=set())
    market = tjr_desk.CryptoMarket.__new__(tjr_desk.CryptoMarket)
    eng = cl.Engine()
    checked = 0
    for pair in cl.PAIRS:
        cfg = cl.live_config(pair)
        eng._cfg[pair] = cfg
        _, liv = both(pair)
        for t in liv[:12]:
            wk = cl.Working(
                pair=pair, session=t.session, direction=t.direction,
                setup=t.setup, entry=t.entry, stop=t.stop_at_risk,
                target=t.target, placed_t=t.setup.choch_t, last_look_i=0,
                equity_at_signal=t.equity_at_entry, units=t.units,
                risk_dollars=t.risk_dollars)
            sig = dict(eng.signal(wk, t.equity_at_entry), market="crypto",
                       usd_per_quote=1.0)
            got = desk._size_for(market, sig, t.equity_at_entry)
            assert got["ok"], f"{pair} {t.entry_t}: the desk refused to size"
            assert got["units"] == pytest.approx(t.units, rel=1e-9), \
                (f"{pair} {t.entry_t}: the desk would send {got['units']} "
                 f"coins and the replay booked {t.units}")
            checked += 1
    assert checked >= 40


def test_a_trade_risks_its_stated_share_of_the_equity_it_was_sized_on():
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            want = 0.03 * t.equity_at_entry
            assert t.units * abs(t.entry - t.stop_at_risk) == \
                pytest.approx(want, rel=1e-6), \
                f"{pair} {t.entry_t}: risked something other than 3% of equity"


def test_the_size_is_spent_not_held_still_and_the_signal_says_so():
    eng = cl.Engine()
    _, liv = both(PAIR)
    t = liv[0]
    wk = cl.Working(pair=PAIR, session=t.session, direction=t.direction,
                    setup=t.setup, entry=t.entry, stop=t.stop_at_risk,
                    target=t.target, placed_t=t.setup.choch_t, last_look_i=0,
                    equity_at_signal=t.equity_at_entry, units=t.units,
                    risk_dollars=t.risk_dollars)
    sig = eng.signal(wk, t.equity_at_entry)
    assert sig["hold_size_still"] is False, \
        "a Craig trade sized off the tightest stop instead of today's stop"
    assert sig["tightest_stop_pct"] > 0, \
        "his own stop floors were never measured, so the desk will refuse"


def test_craigs_stop_floors_are_his_own_and_not_the_tjr_books():
    """Methods never mix, and that includes the one number the sizing wrapper
    insists on having measured."""
    for pair in cl.PAIRS:
        mine = cl.tightest_stop_pct(pair)
        theirs = tjr_desk.tightest_stop_pct(pair)
        assert mine > 0, f"{pair}: Craig's own stop floor was never measured"
        assert mine != theirs, \
            f"{pair}: Craig is using the TJR book's measured stop"
        assert (cl.stop_floors()[pair]["chart"] == "1h"
                and cl.stop_floors()[pair]["engine"] == "craig")


def test_leverage_is_an_output_of_the_stop_and_never_an_input():
    """NOTHING PICKS A LEVERAGE. The size comes out of the stop and the
    leverage is whatever that size implies.

    There IS a leverage number in this module now — `LEVERAGE_CEILING`, the
    most the exchange will carry — and it is the opposite of an input: it can
    only ever make a position SMALLER than the stop asked for, never larger,
    and only when the exchange physically cannot hold the one the stop asked
    for. This test holds that direction.
    """
    # THE CEILING CAN ONLY EVER CUT. Raise it to the sky and the size does
    # not move; that is what makes it a limit rather than a dial.
    cfg = cl.book_config(PAIR)
    real = cl.size_for(PAIR, 2178.0, 100_000.0, 5_000.0, cfg)     # wide stop
    keep = dict(cl.LEVERAGE_CEILING)
    try:
        cl.LEVERAGE_CEILING[PAIR] = 1e9
        sky = cl.size_for(PAIR, 2178.0, 100_000.0, 5_000.0, cfg)
    finally:
        cl.LEVERAGE_CEILING.clear()
        cl.LEVERAGE_CEILING.update(keep)
    assert real["truncated_by_leverage_cap"] is False
    assert real["units"] == pytest.approx(sky["units"], rel=1e-12), \
        "the exchange's ceiling changed a size it was not binding on"
    # and on the shipping book it never binds at all, so no step467 number
    # was ever produced by a leverage choice
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv[:8]:
            s = cl.size_for(pair, t.equity_at_entry, t.entry,
                            abs(t.entry - t.stop_at_risk),
                            cl.live_config(pair))
            assert s["truncated_by_leverage_cap"] is False

    band = []
    for pair in cl.PAIRS:
        _, liv = both(pair)
        band += [t.leverage for t in liv]
    band = np.array(band)
    assert band.min() > 0
    assert len(set(np.round(band, 6))) > 0.5 * len(band), \
        "the leverage repeats — something fixed is setting it"


# ================================================ 6. WHAT THE MESSAGE SAYS
def test_the_message_states_the_size_the_order_actually_carried():
    sig, size = _sample_signal()
    title, msg = tjr_alerts.entry_message([sig], sig["sizing_account"],
                                          {sig["symbol"]: 1.0},
                                          dt.datetime(2026, 7, 12, 14, 0))
    u = size["units"]
    shown = f"{u:,.6f}".rstrip("0").rstrip(".")
    assert shown in msg, \
        f"the message does not state the {u} coins the order carried:\n{msg}"


def test_the_message_says_the_entry_is_a_resting_limit_and_not_a_position():
    sig, _ = _sample_signal()
    sig["placed"] = {"status": "resting", "price": sig["limit_price"]}
    title, msg = tjr_alerts.entry_message([sig], sig["sizing_account"],
                                          {sig["symbol"]: 1.0},
                                          dt.datetime(2026, 7, 12, 14, 0))
    assert "RESTING LIMIT" in msg
    assert "waiting for the price" in msg
    assert "the bot took this one" not in msg, \
        "a resting order was announced as a position"
    assert "take HALF off" not in msg, \
        "the TJR ladder reached a Craig message — he has one exit, not four"


def test_the_message_keeps_the_shape_wallace_approved():
    """Entry / SL / TP rows with dollars and share of the MARGIN, then Size,
    Margin, Leverage, then Why in plain English."""
    sig, _ = _sample_signal()
    _, msg = tjr_alerts.entry_message([sig], sig["sizing_account"],
                                      {sig["symbol"]: 1.0},
                                      dt.datetime(2026, 7, 12, 14, 0))
    order = ["Entry", "SL", "TP", "Size", "Margin", "Why:"]
    at = [msg.index(k) for k in order]
    assert at == sorted(at), f"the approved row order moved:\n{msg}"
    assert "% OF THE MARGIN" in msg
    assert "Leverage" in msg


def test_every_percentage_on_the_message_says_which_one_it_is():
    sig, _ = _sample_signal()
    _, msg = tjr_alerts.entry_message([sig], sig["sizing_account"],
                                      {sig["symbol"]: 1.0},
                                      dt.datetime(2026, 7, 12, 14, 0))
    for line in msg.splitlines():
        if "%" not in line:
            continue
        ok = ("MARGIN" in line or "move in the price" in line
              or "OF THE ACCOUNT" in line or "off" in line
              or "% of today's risk" in line)
        assert ok, f"a bare percentage reached the phone:\n  {line}"


def test_the_why_is_craigs_and_needs_no_glossary():
    sig, _ = _sample_signal()
    why = tjr_alerts.plain_reason(sig)
    assert why == sig["why"], "the message rewrote Craig's sentence as TJR's"
    for jargon in ("change of character", "fair value gap", "CHoCH", "FVG",
                   "liquidity", "break of structure", "retracement",
                   "61.8", "premium", "discount"):
        assert jargon.lower() not in why.lower(), \
            f"'{jargon}' reached the phone"


def test_the_manage_cards_exist_for_every_thing_that_can_happen_to_an_order():
    for fn in ("filled_message", "breakeven_message", "order_cancelled_message",
               "stopped_message", "close_message"):
        assert hasattr(tjr_alerts, fn), f"{fn} is missing"
    _, m = tjr_alerts.order_cancelled_message(
        "crypto", "BTC/USD", 60000.0, "it ran out of candles")
    assert "never filled" in m and "cost nothing" in m


# ============================ 6b. THE WHOLE PATH, END TO END
def test_the_desk_turns_a_craig_signal_into_a_resting_limit_with_its_stop():
    """Real candles in, a real order out — through the desk's own
    poll_market, the desk's own sizing, and the real venue class."""
    c = _FakeClient()
    m, when, t = _wired(c)
    desk = _Recorder(armed={"crypto"})
    fresh = desk.poll_market(m, when)

    assert len(fresh) == 1, f"the desk decided {len(fresh)} setups, wanted 1"
    sig = fresh[0]
    assert sig["order_type"] == "limit"
    assert len(c.limits) == 1, "no resting order reached the exchange"
    sent = c.limits[0]
    assert sent["price"] == pytest.approx(t.setup.entry), \
        "the limit did not go on at the gap midpoint"
    assert sent["stop_price"] == pytest.approx(t.setup.stop), \
        "the stop did not ride in with the resting entry"
    assert sent["take_profit"] == pytest.approx(t.setup.target)
    assert c.placed == [], "a MARKET order was sent for a resting-limit method"
    assert c.brackets == [], "the stop was sent as a second call"
    assert sig["placed"]["status"] == "resting"
    assert len(desk.pushed) == 1, "the bot did not say what it did"
    assert "waiting for the price" in desk.pushed[0][1]


def test_the_fixed_dollars_reach_the_exchange_and_the_message_says_the_size():
    """THE SHIPPING PATH, END TO END, ON CRAIG'S OWN DOLLARS. Real candles in,
    a real resting order out, and the message stating the coins that were
    sent — not a number capped somewhere else on the way to the phone.

    2026-08-10: the book stopped running Alex's money-game ladder (two men's
    doctrine in one method) and started running Craig's own stated sizing —
    "if you're trying to risk $50 per trade and you can use 25x leverage",
    2026-07-05, mid-band $75. Same end-to-end assertion, new sizing law.
    """
    c = _FakeClient()
    m, when, t = _wired(c, book=True)
    desk = _Recorder(armed={"crypto"})
    fresh = desk.poll_market(m, when)
    assert len(fresh) == 1
    sig = fresh[0]
    assert sig["money_game_ladder"] is False, \
        "Alex's ladder rode into a Craig order — methods never mix"
    eq = float(sig["sizing_account"])
    want = cl.risk_share_for(eq, cl.book_config(PAIR)) * eq
    assert want == pytest.approx(cl.BOOK["fixed_risk_dollars"], rel=1e-9), \
        f"at ${eq:,.0f} his fixed dollars came out as ${want:,.2f}"
    assert sig["risk_wanted"] == pytest.approx(want, rel=1e-9), \
        "the signal did not carry his fixed dollars"
    assert sig["size"]["risk_dollars"] == pytest.approx(want, rel=1e-6), \
        "the desk sized the order on something other than his fixed dollars"
    assert len(c.limits) == 1
    assert c.limits[0]["price"] == pytest.approx(t.setup.entry)
    assert c.limits[0]["stop_price"] == pytest.approx(t.setup.stop), \
        "the fixed-dollar sizing cost the resting entry its attached stop"
    # AND THE MESSAGE SAYS THE SAME NUMBER. This is the drift that would have
    # him reconciling his BloFin screen against a size nothing ever sent.
    said = desk.pushed[0][1]
    coins = f"{sig['size']['units']:,.6f}".rstrip("0").rstrip(".")
    assert coins in said, \
        f"the message states a different size from the order:\n{said}"
    assert "3% of the account" not in said, \
        "the desk's flat outer limit silently capped a fixed-dollar message"


def test_an_unarmed_desk_decides_sizes_and_reports_and_sends_nothing():
    c = _FakeClient()
    m, when, t = _wired(c)
    desk = _Recorder(armed=set())
    fresh = desk.poll_market(m, when)
    assert len(fresh) == 1, "an unarmed market stopped deciding"
    assert fresh[0]["size"]["ok"], "an unarmed market stopped sizing"
    assert not c.touched_anything(), "an unarmed market reached the exchange"
    assert len(desk.pushed) == 1 and "NOT SENT" in desk.pushed[0][1]


def test_nothing_is_ever_narrated_about_an_order_that_was_not_sent():
    """The engine models a setup whether or not it was sent. A later
    'FILLED' or 'stopped out' about a position that never existed would be a
    lie, and this is what stops one."""
    c = _FakeClient()
    m, when, t = _wired(c)
    desk = _Recorder(armed=set())              # nothing reaches the exchange
    desk.poll_market(m, when)
    said = len(desk.pushed)
    assert not m.real, "an unsent order was recorded as real"
    # now push the engine through the rest of that trade's life
    pos = cl.Position(
        pair=t.pair, session=t.session, direction=t.direction, setup=t.setup,
        entry_t=t.entry_t, entry=t.entry, stop=t.stop_at_risk,
        stop_at_risk=t.stop_at_risk, target=t.target, units=t.units,
        notional=t.notional, risk_dollars=t.risk_dollars,
        equity_at_entry=t.equity_at_entry, fill_i=0,
        deadline=pd.Timestamp(t.entry_t) + pd.Timedelta(hours=48),
        be_ref=None, sent_units=t.units, exit_t=t.exit_t, exit=t.exit,
        outcome="stopped out")
    m.pending = [{"kind": "filled", "symbol": t.pair, "at": t.setup.choch_t,
                  "position": pos, "working": _working_from(t)},
                 {"kind": "exit", "symbol": t.pair, "at": t.exit_t,
                  "price": t.exit, "outcome": "stopped out", "position": pos}]
    m.manage(desk, {})
    assert len(desk.pushed) == said, \
        f"the bot narrated a position it never opened: {desk.pushed[said:]}"
    assert not c.touched_anything()


def test_a_second_order_is_refused_while_the_pair_already_carries_one():
    """BloFin nets everything on a symbol into ONE position, so the setup is
    decided and reported and the SENDING is refused."""
    c = _FakeClient(pending_orders=[
        {"orderId": "ours", "clientOrderId": "CBOT_tjc_1785018742491000001"}])
    m, when, t = _wired(c)
    desk = _Recorder(armed={"crypto"})
    fresh = desk.poll_market(m, when)
    assert len(fresh) == 1, "the setup was not even decided"
    assert fresh[0]["placed"]["status"] == "not_sent"
    assert "ONE position" in fresh[0]["placed"]["reason"]
    assert c.limits == [], "a second order went on a pair that already had one"


def test_the_message_says_the_time_the_candle_closed_not_the_time_it_opened():
    c = _FakeClient()
    m, when, t = _wired(c)
    desk = _Recorder(armed={"crypto"})
    fresh = desk.poll_market(m, when)
    fired = pd.Timestamp(fresh[0]["fired_at"])
    bar = pd.Timestamp(t.setup.choch_t)
    ny = (bar + pd.Timedelta(hours=1)).tz_localize("UTC") \
        .tz_convert("America/New_York").tz_localize(None)
    assert fired == ny, \
        (f"the message is stamped {fired}; the candle it decided on closed at "
         f"{ny} New York time")
    assert pd.Timestamp(fresh[0]["entry_t"]) == bar, \
        "the record stopped using the bar's own timestamp, so live and " \
        "replay can no longer be compared"


# ================================== 6c. HOW BIG THE BOOK'S TRADES ARE
#
# TWO RULES LIVE HERE AND THEY BELONG TO TWO DIFFERENT MEN.
#
# ALEX'S LADDER, which the GOLD book runs and Craig's book no longer does.
# Alex Gonzalez, 2026-02-22: "Anything below $25,000, it's all the money
# game" ... "you have to make sure that you have at least four or five trades
# in you before you would obviously lose the account" ... "as you start
# creating a bigger account, you lower that risk".
# Wallace: "This is why I even have it set at 2178 ... its how much I would be
# willing to lose to even start."
#
# CRAIG'S OWN DOLLARS, which his book runs as of 2026-08-10. Running Alex's
# doctrine on Craig's method broke the methods-never-mix law and ten live days
# billed us for it: three losses of $400-600 on the $2,178 stake, and refusals
# wherever a leverage cap could not carry a position about forty times the
# account. Craig, 2026-07-05: "if you're trying to risk $50 per trade and you
# can use 25x leverage". `craig_live.BOOK` runs the mid-band, $75 a trade.
STAKE = 2178.0


def test_the_ladder_hits_his_two_anchors_exactly():
    """The anchors are HIS. Only the curve between them is ours, and it may
    not move either end of it."""
    assert cl.money_game_share(STAKE, STAKE) == pytest.approx(1 / 4.5), \
        "the base is no longer 'four or five trades in you'"
    assert cl.money_game_risk_dollars(STAKE, STAKE) == pytest.approx(484.0,
                                                                    abs=0.5)
    assert cl.money_game_share(25_000.0, STAKE) == pytest.approx(0.01), \
        "the percentage game no longer starts at 1% of $25,000"
    assert cl.money_game_share(60_000.0, STAKE) == pytest.approx(0.01), \
        "above $25,000 it is the percentage game and nothing else"
    # below the stake it is still the same share of what is left, which is
    # what keeps four or five trades in you all the way down
    assert cl.money_game_share(900.0, STAKE) == pytest.approx(1 / 4.5)


def test_the_ladder_only_ever_steps_down():
    """His words are 'as you start creating a bigger account, you LOWER that
    risk'. Both readings of it: the share falls, and so do the dollars."""
    xs = np.linspace(STAKE, 25_000.0, 400)
    share = np.array([cl.money_game_share(x, STAKE) for x in xs])
    dollars = share * xs
    assert np.all(np.diff(share) <= 1e-12), "the share turned back up"
    assert np.all(np.diff(dollars) <= 1e-9), "the dollars at risk turned up"
    # and it does not jump at either anchor
    assert cl.money_game_share(STAKE * 1.0001, STAKE) == \
        pytest.approx(1 / 4.5, rel=1e-3)
    assert cl.money_game_share(24_999.0, STAKE) == pytest.approx(0.01,
                                                                 rel=1e-3)


def test_the_fixed_dollars_are_on_for_the_blofin_book_and_the_ladder_is_off():
    """2026-08-10: THE LADDER CAME OFF CRAIG'S BOOK and his own number went on.

    Alex's money game on Craig's method mixed two men's doctrine, which is the
    one law this project does not bend, and ten live days showed the bill:
    three losses of $400-600 on a $2,178 stake, plus refusals wherever a
    pair's leverage cap could not carry a position about forty times the
    account. Craig states his own small-account sizing, 2026-07-05: "if you're
    trying to risk $50 per trade and you can use 25x leverage". The book runs
    the mid-band of that, $75 a trade, and no ladder.

    The other half of this test is the half that protects step467: the
    SHIPPING configuration — the one every replay number was measured on — has
    neither the fixed dollars nor the ladder, and neither does any other
    book.
    """
    assert cl.BOOK["fixed_risk_dollars"] == 75.0, \
        "Craig's own dollars moved off the mid-band of his $50-$100"
    assert cl.BOOK["money_game_ladder"] is False, \
        "Alex's ladder is back on Craig's book — methods never mix"
    cfg = cl.book_config(PAIR)
    assert cfg.fixed_risk_dollars == 75.0
    assert cfg.money_game_ladder is False
    # THE SHIPPING CONFIGURATION ALONE, so every step467 replay number still
    # means what it meant: no fixed dollars, no ladder, just the flat dial.
    assert "fixed_risk_dollars" not in cl.SHIPPING
    assert "money_game_ladder" not in cl.SHIPPING
    ship = cl.live_config(PAIR)
    assert ship.fixed_risk_dollars == 0.0, \
        "the replay's own config took the book's dollars — step467 moved"
    assert ship.money_game_ladder is False
    assert cl.risk_share_for(100_000.0, ship) == pytest.approx(0.03), \
        "the shipping config no longer sizes on the flat 3% it was measured on"
    # and neither does the method's bare default
    assert cc.CraigConfig().fixed_risk_dollars == 0.0
    assert cc.CraigConfig().money_game_ladder is False
    # NO OTHER BOOK PICKS THEM UP. Stocks run their own file, gold runs Alex's
    # off `alex_live`, and neither has ever heard of Craig's dollars.
    import alex_live
    for book in (alex_live.BOOK, alex_live.GOLD_BOOK):
        assert "fixed_risk_dollars" not in book, \
            "Craig's dollars reached a book that is not Craig's"
    stocks = inspect.getsource(tjr_desk.IndexMarket)
    assert "fixed_risk_dollars" not in stocks and "craig" not in stocks.lower()
    # and the desk turns Craig's book on in exactly one place — the crypto
    # market's own engine, and nowhere else
    src = inspect.getsource(tjr_desk)
    assert src.count("Engine(cfg_over=craig_live.BOOK)") == 1
    assert "craig_live.BOOK" in inspect.getsource(tjr_desk.CryptoMarket)


def test_the_fixed_dollars_move_only_the_size():
    """IT IS A SIZING POLICY AND NOTHING ELSE. The same twelve months, run
    with Craig's fixed dollars on (the book) and off (bare shipping): every
    entry, every stop, every target and every outcome identical, and only
    the coins different. (Renamed 2026-08-10 — the book's sizing policy is
    now Craig's $75, not Alex's ladder, and the test compares whatever the
    book runs against bare shipping.)"""
    for pair in cl.PAIRS:
        flat = cl.replay_through_live(pair, *YEAR, cfg=cl.live_config(pair),
                                      data=data(pair))["trades"]
        lad = cl.replay_through_live(pair, *YEAR, cfg=cl.book_config(pair),
                                     data=data(pair))["trades"]
        assert len(flat) == len(lad), \
            f"{pair}: the ladder changed WHICH trades were taken"
        moved = 0
        for a, b in zip(flat, lad):
            for f in ("entry_t", "exit_t", "entry", "stop_at_risk", "target",
                      "exit", "outcome", "direction", "session",
                      "moved_to_breakeven", "r_multiple"):
                x, y = getattr(a, f), getattr(b, f)
                ok = (abs(x - y) <= 1e-9 * max(1.0, abs(x))
                      if isinstance(x, float) else x == y)
                assert ok, f"{pair} {a.entry_t}: the ladder changed {f}"
            if abs(a.units - b.units) > 1e-9:
                moved += 1
        assert moved > 0, f"{pair}: the ladder changed no size at all"


def test_the_fixed_dollars_still_go_through_the_one_sizing_path():
    """IT IS A WRAPPER. Since 2026-08-10 the book sizes on Craig's own stated
    dollars — "if you're trying to risk $50 per trade and you can use 25x
    leverage", 2026-07-05, mid-band $75 — and the coins still come out of
    `tjr_alerts.position_size`, which is the desk's own front door.

    A sizing rule that quietly stopped using that door is how two paths get
    separate arithmetic, so the second half of this test takes the door away
    and insists the sizing FAILS rather than falling back to a number of its
    own.
    """
    seen = []
    real = tjr_alerts.position_size

    def spy(*a, **kw):
        seen.append((a, kw))
        return real(*a, **kw)

    cl.tjr_alerts.position_size = spy
    try:
        out = cl.size_for(PAIR, STAKE, 60_000.0, 400.0, cl.book_config(PAIR))
    finally:
        cl.tjr_alerts.position_size = real
    assert len(seen) == 1, \
        "the fixed dollars sized something without the wrapper"
    assert seen[0][1]["hold_size_still"] is False
    assert seen[0][1]["outer_allowance"] == pytest.approx(75.0), \
        "the dollars handed to the one sizing call are not Craig's $75"
    assert out["risk_dollars"] == pytest.approx(75.0, abs=1e-6)
    assert out["risk_share_used"] == pytest.approx(75.0 / STAKE)
    assert out["units"] == pytest.approx(75.0 / 400.0, rel=1e-9), \
        "the coins are not the dollars divided by the stop"
    # AND THERE IS NO SECOND DOOR. Take the one away and sizing must raise.
    gone = tjr_alerts.position_size
    del tjr_alerts.position_size
    try:
        with pytest.raises(AttributeError):
            cl.size_for(PAIR, STAKE, 60_000.0, 400.0, cl.book_config(PAIR))
    finally:
        tjr_alerts.position_size = gone


def test_the_desk_and_the_engine_size_the_fixed_dollars_identically():
    """The 36x bug's shape, under the 2026-08-10 rule. The book no longer runs
    Alex's ladder; it runs Craig's own stated sizing — "if you're trying to
    risk $50 per trade and you can use 25x leverage", 2026-07-05, mid-band
    $75. The desk knows nothing about that rule either — it reads the dollars
    off the signal — so if the two ever disagree, this fails."""
    desk = tjr_desk.Desk(dry_run=True, markets=[], armed=set())
    market = tjr_desk.CryptoMarket.__new__(tjr_desk.CryptoMarket)
    eng = cl.Engine(cfg_over=cl.BOOK)
    checked = 0
    for pair in cl.PAIRS:
        cfg = cl.book_config(pair)
        eng._cfg[pair] = cfg
        r = cl.replay_through_live(pair, *YEAR, cfg=cfg, data=data(pair))
        for t in r["trades"][:10]:
            wk = cl.Working(
                pair=pair, session=t.session, direction=t.direction,
                setup=t.setup, entry=t.setup.entry, stop=t.setup.stop,
                target=t.setup.target, placed_t=t.setup.choch_t,
                last_look_i=0, equity_at_signal=t.equity_at_entry,
                units=t.sent_units, risk_dollars=t.risk_dollars)
            sig = dict(eng.signal(wk, t.equity_at_entry), market="crypto",
                       usd_per_quote=1.0)
            assert sig["money_game_ladder"] is False, \
                "Alex's ladder is back on Craig's book"
            assert sig["risk_wanted"] == pytest.approx(75.0, rel=1e-9), \
                (f"{pair} {t.entry_t}: the signal carried "
                 f"${sig['risk_wanted']:,.2f}, not Craig's $75")
            got = desk._size_for(market, sig, t.equity_at_entry)
            assert got["ok"]
            assert got["units"] == pytest.approx(wk.units, rel=1e-9), \
                (f"{pair} {t.entry_t}: the desk would send {got['units']} "
                 f"coins and the engine sized {wk.units}")
            checked += 1
    assert checked >= 40


def test_a_size_the_exchange_cannot_carry_is_cut_and_said_out_loud():
    """UNCHANGED IN SPIRIT, rebuilt on the 2026-08-10 sizing law. Ask for
    enough dollars on a tight enough stop and the position is worth more than
    the instrument's own ceiling will carry with the WHOLE balance posted as
    margin. It is cut — and the answer says by how much rather than quietly
    shrinking.

    The book's own $75 (Craig, 2026-07-05: "if you're trying to risk $50 per
    trade and you can use 25x leverage") does NOT bind here, which is half the
    point of moving to it — the ladder's ~$484 on a $2,178 stake is what kept
    hitting these ceilings. So the cap-binding case is built on purpose, with
    a fixed-dollar figure large enough to reach it.
    """
    pair = "XRP/USD"                      # 50x, the lowest ceiling of the five
    entry, dist = 2.0, 2.0 * 0.0010       # a 0.10% stop as a MOVE IN THE PRICE
    # HIS OWN DOLLARS DO NOT REACH THE CEILING on this stop, and saying so is
    # what makes the cut below a deliberately constructed case
    assert cl.size_for(pair, STAKE, entry, dist,
                       cl.book_config(pair))["truncated_by_leverage_cap"] \
        is False, "Craig's $75 is still hitting the exchange's ceiling"
    cfg = cl.book_config(pair, fixed_risk_dollars=500.0)
    out = cl.size_for(pair, STAKE, entry, dist, cfg)
    assert out["truncated_by_leverage_cap"] is True
    assert out["units"] * entry == pytest.approx(
        cl.leverage_ceiling(pair) * STAKE, rel=1e-9), \
        "the cut did not land on the exchange's own ceiling"
    assert out["risk_dollars"] < out["uncapped_risk_dollars"]
    assert "CUT BY THE EXCHANGE'S CEILING" in out["leverage_cap_note"]
    assert "50x" in out["leverage_cap_note"]
    # and the desk prints it rather than swallowing it
    assert "[LEVERAGE CAP]" in inspect.getsource(tjr_desk.CryptoMarket.decide)


def test_the_ladder_never_reaches_the_stock_or_gold_books():
    """CRAIG'S CONFIGURATION IS CRAIG'S. Nothing else on the desk may take
    `craig_live.BOOK`, and no file every book shares may know the ladder
    exists.

    UPDATED 2026-07-27, and the reason is Wallace's, not a loosening of this
    rule. He ruled "ladder on gold too", so the GOLD book runs the ladder as
    well — through `alex_live`, off `alex_live.GOLD_BOOK`, switched on in its
    own file. The curve is imported from here rather than copied, which is
    why the two books cannot drift about it. What this test still holds is
    the thing it was written to hold: the ladder is a SIZE that lives in a
    book's own configuration, it is never wired into the shared plumbing, and
    the index book on Alpaca has no trace of it.
    """
    src = inspect.getsource(tjr_desk.IndexMarket)
    assert "money_game" not in src and "craig" not in src.lower(), \
        "the ladder or Craig's method reached the index book"
    for mod in (tjr_bot_src(), inspect.getsource(tjr_alerts)):
        assert "money_game" not in mod, \
            "the ladder leaked into a file every book shares"
    # and the gold book takes the ladder from ONE curve — this one
    import alex_live
    assert alex_live.money_game_share(2178.0, 2178.0) == \
        cl.money_game_share(2178.0, 2178.0)
    assert "money_game_ladder" not in alex_live.BOOK, \
        "the forex book took the ladder; it is over his $25,000 line"


def tjr_bot_src():
    import tjr_bot
    return inspect.getsource(tjr_bot)


# ============================== 6d. NOTHING CAPS HOW OFTEN IT TRADES
#
# Wallace, 2026-07-26: "if you see the setup, take the trade. its a demo at
# the end of the day." His reasoning: a cap on trades per day exists so a
# HUMAN does not overtrade on emotion, and the bot has none.
#
# The method's own machinery is not that and stays exactly as step467 built
# it: the hunt window after each session open, the 24-candle life of the
# resting limit, a setup dying at its stop before it fills, and the
# change-of-character that has to happen at all.
def test_nothing_in_the_wiring_caps_how_many_trades_a_day_or_a_week():
    for src in (SRC, inspect.getsource(tjr_desk.CryptoMarket)):
        low = src.lower()
        for banned in ("max_trades", "trades_today", "daybudget",
                       "day_budget", "cooldown", "max_open", "max_positions",
                       "one_per_day", "already_traded_today"):
            assert banned not in low, \
                f"a trade throttle called {banned!r} is in the Craig wiring"


def test_the_per_session_setup_cap_never_binds_on_the_one_hour_chart():
    """`max_setups_per_session` is 2, and on this chart the hunt window after
    a session open is 2 candles — so the cap and the window are the same
    number and the cap discards nothing. Raise it to 99 and not one trade of
    the shipping year moves. It is therefore not a throttle, which is why it
    stays exactly as step467 measured it rather than being edited."""
    for pair in cl.PAIRS:
        base = cc.run_pair(pair, *YEAR, cfg=cl.live_config(pair),
                           data=data(pair))["trades"]
        wide = cc.run_pair(
            pair, *YEAR, cfg=cl.live_config(pair, max_setups_per_session=99),
            data=data(pair))["trades"]
        assert len(base) == len(wide), \
            f"{pair}: the per-session cap is discarding {len(wide)-len(base)} setups"
        for a, b in zip(base, wide):
            assert a.entry_t == b.entry_t and abs(a.pnl - b.pnl) < 1e-9


def test_the_only_bound_on_a_second_entry_is_the_exchanges_own():
    """One position per pair is BloFin netting everything on a symbol, not a
    view about how often to trade — and the setup is still decided, still
    sized and still reported when it binds."""
    src = inspect.getsource(tjr_desk.Desk._rest_one)
    assert "nets" in src and "ONE position" in src
    assert "was not sent" in src or "not sent" in src


# ==================================== 7. METHODS NEVER MIX
def test_the_desks_crypto_path_reaches_craig_and_only_craig():
    src = inspect.getsource(tjr_desk.CryptoMarket)
    assert "craig_live" in src
    assert "tjr_crypto" not in src.replace('tag = "tjr_crypto"', ""), \
        "the crypto market still reaches the TJR method"


def test_the_stock_and_gold_paths_are_untouched():
    """THE STOCK PATH IS UNTOUCHED, and gold changed hands on 2026-07-27 for
    the same kind of reason crypto did — Wallace's own instruction, "trade
    gold as xauusdt on blofin", and Alex's method behind it.

    So this test now says what is actually true: the index book still runs the
    TJR method in its own file, the gold book runs Alex's, the old TJR gold
    path is left importable for replay exactly as `tjr_crypto` was, and
    NEITHER of them reaches anything of Craig's decision-making.
    """
    src = inspect.getsource(tjr_desk.IndexMarket)
    assert "tjr_bot.live_step" in src, "IndexMarket lost its method"
    assert "craig" not in src.lower(), \
        "IndexMarket reaches Craig — methods never mix"

    gold = inspect.getsource(tjr_desk.GoldMarket)
    assert "tjr_gold.live_step" not in gold, \
        "the gold book still runs the retired TJR path"
    for reaches in ("craig_live.", "craig_crypto."):
        assert reaches not in gold, \
            f"the gold book reaches {reaches} — methods never mix"
    import tjr_gold                                    # still importable
    assert hasattr(tjr_gold, "live_step")


def test_craig_never_imports_the_tjr_method():
    imports = [l for l in SRC.splitlines() if l.startswith(("import ", "from "))]
    tjr = sorted(l for l in imports if "tjr" in l)
    assert tjr == ["import tjr_alerts"], tjr
    # and tjr_alerts is only ever reached for the one sizing function and the
    # message — never for a level, a bias or a session
    body = SRC.split('"""', 2)[2]
    import re
    assert set(re.findall(r"tjr_alerts\.(\w+)", body)) == {"position_size"}


def test_the_tjr_crypto_engine_is_still_importable_for_replay_comparisons():
    import tjr_crypto
    assert hasattr(tjr_crypto, "live_step") and hasattr(tjr_crypto, "run_pair")
    assert tjr_crypto.PAIRS == cl.PAIRS


# ==================================== 8. NOTHING IS TOUCHED
def test_the_live_layer_places_no_order_by_itself():
    body = SRC.split("def _install_venue", 1)[0]
    for bad in ("requests", "urllib", "httpx", "subprocess", "os.system",
                "git ", "to_parquet"):
        assert bad not in body, f"the decision layer reaches for {bad}"


def test_the_engine_returns_actions_and_executes_nothing():
    # the CODE, with every docstring and comment stripped — the prose in this
    # class talks about venues on purpose
    code = "\n".join(l.split("#")[0] for l in
                     inspect.getsource(cl.Engine).splitlines())
    for chunk in code.split('"""')[::2]:
        for bad in (".venue", "market_order", "limit_order", "place_stop",
                    "close_position", "cancel_entry", "send("):
            assert bad not in chunk, \
                f"the engine reaches a venue ({bad}). It returns actions; " \
                f"the desk executes them."


def test_the_only_file_written_is_craigs_own_stop_floors():
    assert SRC.count("open(") == 2          # one read, one write
    assert "STOP_FLOOR_PATH" in SRC
    assert "step469_craig_stop_floors.json" in SRC


def test_the_cost_is_charged_and_never_consulted():
    for i, line in enumerate(SRC.splitlines(), 1):
        code = line.split("#")[0]
        if "round_trip_cost_pct" not in code:
            continue
        assert "pos.cost =" in code, \
            f"line {i}: the cost is being consulted, not just charged:\n{line}"


# ================================================================= FIXTURES
def _fake_setup(entry, stop, target, choch_i, direction=1):
    return cc.Setup(
        pair=PAIR, session="new_york", direction=direction, kind="choch",
        choch_t=pd.Timestamp("2026-03-02 03:00"), choch_i=choch_i,
        broken_level=entry, leg_low=stop, leg_high=target,
        zone_deep=entry, zone_shallow=entry, gap_lo=entry, gap_hi=entry,
        gap_mid_t=pd.Timestamp("2026-03-02 02:00"), entry=entry, stop=stop,
        target=target, stop_from="middle_candle",
        be_level=target if direction > 0 else stop)


def _sample_signal():
    """A real setup from the cached history, as the desk would send it."""
    eng = cl.Engine()
    _, liv = both(PAIR)
    t = liv[-1]
    account = t.equity_at_entry
    wk = cl.Working(pair=PAIR, session=t.session, direction=t.direction,
                    setup=t.setup, entry=t.setup.entry, stop=t.setup.stop,
                    target=t.setup.target, placed_t=t.setup.choch_t,
                    last_look_i=0, equity_at_signal=account,
                    units=t.sent_units, risk_dollars=t.risk_dollars)
    sig = dict(eng.signal(wk, account), market="crypto")
    size = cl.size_for(PAIR, account, wk.entry, abs(wk.entry - wk.stop),
                       cl.live_config(PAIR))
    return sig, size


class _FakeClient:
    """Stands in for BlofinDemoPrivate. Never makes an HTTP call and records
    every mutating call so a test can assert none happened."""

    def __init__(self, position=None, orders=None, pending_orders=None):
        self._position = position
        self._orders = orders or []
        self._pending_orders = pending_orders or []
        self.limits: list = []
        self.placed: list = []
        self.brackets: list = []
        self.cancels: list = []

    # reads
    def positions(self, symbol=None):
        return [] if self._position is None else [self._position]

    def orders_history(self, symbol, limit=None):
        return list(self._orders)

    def pending_orders(self, symbol):
        return list(self._pending_orders)

    def pending_tpsl(self, symbol):
        return []

    def instruments(self, inst_type="SWAP"):
        return [{"instId": "BTC-USDT", "contractValue": "0.001",
                 "lotSize": "0.1", "tickSize": "0.1", "maxLeverage": "150",
                 "state": "live"}]

    def account_balance(self):
        return {"totalEquity": "100000"}

    def futures_balance(self):
        return {"available": "100000"}

    # writes
    def ensure_leverage(self, symbol, leverage, margin_mode=None):
        return True

    def limit_order(self, symbol, side, contracts, price, margin_mode=None,
                    client_order_id=None, lot_size=None, stop_price=None,
                    take_profit=None, tick_size=None):
        self.limits.append({"symbol": symbol, "side": side, "price": price,
                            "contracts": contracts, "stop_price": stop_price,
                            "take_profit": take_profit,
                            "client_order_id": client_order_id})
        return "limit-1"

    def market_order(self, symbol, side, contracts, **kw):
        self.placed.append({"symbol": symbol, "side": side, **kw})
        return "order-1"

    def place_tpsl(self, *a, **kw):
        self.brackets.append({"a": a, "kw": kw})
        return "tpsl-1"

    def cancel_tpsl(self, symbol, tpsl_id):
        self.cancels.append({"symbol": symbol, "tpsl_id": tpsl_id})

    def cancel_order(self, symbol, order_id):
        self.cancels.append({"symbol": symbol, "order_id": order_id})

    def touched_anything(self) -> bool:
        return bool(self.limits or self.placed or self.brackets or self.cancels)


def _venue(client):
    return cl.CraigBlofinVenue(client=client, tag="tjr_crypto")


class _Recorder(tjr_desk.Desk):
    """The real Desk with its one outward path — the push to his phone —
    caught in a list instead of sent."""

    def __init__(self, armed):
        super().__init__(markets=[], armed=armed)
        self.pushed: list = []

    def _push(self, title, message):
        self.pushed.append((title, message))


def _working_from(t):
    return cl.Working(
        pair=t.pair, session=t.session, direction=t.direction, setup=t.setup,
        entry=t.setup.entry, stop=t.setup.stop, target=t.setup.target,
        placed_t=pd.Timestamp(t.setup.choch_t), last_look_i=0,
        equity_at_signal=t.equity_at_entry, units=t.units,
        risk_dollars=t.risk_dollars)


def _wired(client, pair=PAIR, book=False):
    """A CryptoMarket on a fake exchange, fed the real 5-minute tape up to the
    exact moment one real setup's candle closed — so `poll_market` has exactly
    one thing to decide.

    No Alpaca client is built: the bars are handed in, which is the only thing
    the live one would have done.
    """
    _, liv = both(pair)
    t = next(x for x in reversed(liv) if x.setup.kind)
    # `book=True` is the BLOFIN BOOK'S OWN config — what `CryptoMarket` really
    # builds, Craig's fixed dollars and all. The setups are identical either
    # way; only the size moves.
    cfg = cl.book_config(pair) if book else cl.live_config(pair)
    close = pd.Timestamp(t.setup.choch_t) + cl.bar_width(cfg)
    d5 = data(pair)["5m"]
    five = d5[(d5["t"] >= close - pd.Timedelta(days=20)) &
              (d5["t"] < close)].reset_index(drop=True)

    m = tjr_desk.CryptoMarket.__new__(tjr_desk.CryptoMarket)
    tjr_desk.Market.__init__(m, _venue(client))
    m.cli = None
    m.engine = cl.Engine()
    m.engine._cfg[pair] = cfg
    # only this pair is fed, so only this pair can decide
    m.symbols = (pair,)
    m.pending, m.placed, m.real = [], {}, set()
    m._swept = True                       # the startup sweep is its own test
    m.frames = lambda: {pair: {"5m": five, "1m": five}}
    # start the engine at the candle before the one under test, so the single
    # step below is the one that matters
    warm = cl.working_chart({"5m": five}, cfg)
    m.engine.last_bar[pair] = pd.Timestamp(warm["t"].iloc[-2])
    return m, close.to_pydatetime(), t
