"""
test_daily_pick.py — offline tests for daily_pick.py. NO NETWORK.

Reuses the codebase's own fake/neutralization convention (see
test_book_attribution.py): a FakePrivate that never makes an HTTP call and
records every order/cancel/bracket call, fake candle/instrument feeds, and
notify/log_event/save_state monkeypatched to no-ops on EVERY module whose
own bound name would otherwise be called (daily_pick.py directly, AND
step5_paper_trade.py — record_trade_outcome/write_lesson live there and
call ITS OWN module-level log_event/notify, not daily_pick's copy).

Seven intents (per the build brief):
  a) scoring math on synthetic candles produces expected component sums
  b) staleness skip
  c) BTC guard — never opposes net, never picks BTC when a BTC book is active
  d) already-held-symbol skip walks to the next-ranked candidate
  e) boredom pick fires at half size when all convictions < 40
  f) once-per-day idempotency
  g) reconcile books a TP exit with correct PnL and updates the
     conviction_ledger bucket

Run with:  python3 test_daily_pick.py
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

import pandas as pd

import daily_pick as dp
import step5_paper_trade as s5
from strategy import rsi as _rsi_check


# ---------------------------------------------------------------------------
# Fakes — no network, ever.
# ---------------------------------------------------------------------------

class FakePrivate:
    """Stands in for BlofinDemoPrivate. Records every order/cancel/bracket
    call. `net_by_symbol` is a plain dict (unlike test_book_attribution's
    single-symbol FakePrivate, this book trades many symbols at once)."""

    def __init__(self, net_by_symbol: dict | None = None,
                fill_price: float | None = None):
        self.net_by_symbol = dict(net_by_symbol or {})
        self.fill_price = fill_price
        self.orders: list[dict] = []
        self.tpsl_calls: list[dict] = []
        self.cancels: list[dict] = []
        self.leverage_calls: list[tuple] = []
        self._tpsl_counter = 0

    def net_position_contracts(self, symbol):
        return self.net_by_symbol.get(symbol, 0.0)

    def ensure_leverage(self, symbol, leverage, margin_mode="cross"):
        self.leverage_calls.append((symbol, leverage))
        return True

    def post_only_order(self, symbol, side, contracts, price, reduce_only=False):
        oid = f"post{len(self.orders) + 1}"
        self.orders.append({"kind": "post_only", "symbol": symbol,
                            "side": side, "contracts": contracts,
                            "price": price, "reduce_only": reduce_only,
                            "id": oid})
        return oid

    def market_order(self, symbol, side, contracts, reduce_only=False,
                     margin_mode="cross"):
        oid = f"mkt{len(self.orders) + 1}"
        self.orders.append({"kind": "market", "symbol": symbol, "side": side,
                            "contracts": contracts, "reduce_only": reduce_only,
                            "id": oid})
        return oid

    def pending_orders(self, symbol):
        return []                  # nothing resting -> maker "fills" instantly

    def cancel_order(self, symbol, order_id):
        self.cancels.append(("order", symbol, order_id))

    def place_tpsl(self, symbol, close_side, contracts, tp, sl,
                   margin_mode="cross"):
        self._tpsl_counter += 1
        tid = f"tpsl{self._tpsl_counter}"
        self.tpsl_calls.append({"symbol": symbol, "close_side": close_side,
                                "contracts": contracts, "tp": tp, "sl": sl,
                                "id": tid})
        return tid

    def pending_tpsl(self, symbol):
        return [{"tpslId": "tpsl1"}]     # a bracket exists (no re-arm noise)

    def cancel_tpsl(self, symbol, tpsl_id):
        self.cancels.append(("tpsl", symbol, tpsl_id))

    def fills(self, symbol, order_id=None):
        if self.fill_price is None:
            return []
        return [{"fillPrice": str(self.fill_price)}]


class FakeLiveFeed:
    """Stands in for config.make_exchange("live") — public PROD market
    data. Candles are installed per (symbol, timeframe) explicitly; funding
    is a plain per-symbol bps dict (None = unavailable, matching BloFin's
    funding endpoint contract used by current_funding_bps)."""

    def __init__(self):
        self.candles: dict[str, dict[str, pd.DataFrame]] = {}
        self.funding: dict[str, float] = {}

    def set_candles(self, symbol, timeframe, df):
        self.candles.setdefault(symbol, {})[timeframe] = df

    def get_candles(self, symbol, timeframe, limit=300, end_ms=None):
        d = self.candles.get(symbol, {}).get(timeframe)
        if d is None:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"])
        return d.tail(limit).reset_index(drop=True)

    def _get(self, path, params=None):
        sym = (params or {}).get("instId")
        bps = self.funding.get(sym)
        if bps is None:
            return []
        return [{"fundingRate": str(bps / 10_000)}]


class FakeDemoFeed:
    """Stands in for config.make_exchange("demo"). `available` gates the
    universe-probe candle fetch; `specs` gates guard (d)'s instrument-spec
    fetch — a symbol can be probe-available but spec-dead (TSLA-USDT's
    real quirk, see daily_pick.py's module docstring)."""

    def __init__(self, available=None, specs=None, tickers=None):
        self.available = set(available or [])
        self.specs = dict(specs or {})
        self.tickers = dict(tickers or {})

    def get_candles(self, symbol, timeframe, limit=300, end_ms=None):
        if symbol not in self.available:
            raise RuntimeError(f"{symbol}: Parameter instId error.")
        return pd.DataFrame({
            "timestamp": [pd.Timestamp("2026-07-23", tz="UTC")],
            "open": [1.0], "high": [1.0], "low": [1.0], "close": [1.0],
            "volume": [1.0],
        })

    def get_instrument(self, symbol):
        if symbol not in self.specs:
            raise RuntimeError(f"{symbol}: invalid symbol")
        return self.specs[symbol]

    def get_ticker(self, symbol):
        px = self.tickers.get(symbol, 100.0)
        class _T:
            pass
        t = _T()
        t.last, t.bid, t.ask = px, px, px
        return t


DEFAULT_SPEC = {"contractValue": "1", "minSize": "0.01", "lotSize": "0.01",
                "tickSize": "0.01", "maxLeverage": "100"}


def make_state(**overrides) -> dict:
    state = {"virtual_equity": 1000.0, "goal": 2000.0, "open_trade": None,
             "tactical": {"open_trade": None},
             "shorts_lab": {"open_trade": None},
             "newsdesk": {"open_trade": None}}
    state.update(overrides)
    return state


class _FrozenDatetime(datetime):
    """Freezes daily_pick's notion of 'now' without a mocking library —
    datetime.now(tz) returns a fixed instant; strptime etc. are inherited
    unmodified from the real datetime class."""
    _frozen: datetime | None = None

    @classmethod
    def now(cls, tz=None):
        return cls._frozen


def _freeze(iso_dt: str):
    dp.datetime = _FrozenDatetime
    _FrozenDatetime._frozen = datetime.strptime(
        iso_dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _unfreeze():
    dp.datetime = datetime


# ---------------------------------------------------------------------------
# Neutralize every side effect that would otherwise touch the network or
# real local files — on BOTH daily_pick (its own direct calls) and
# step5_paper_trade (record_trade_outcome / write_lesson live there and
# call ITS OWN bound log_event/notify, not daily_pick's copy).
# ---------------------------------------------------------------------------

def _noop(*a, **kw):
    pass


for _mod in (dp, s5):
    _mod.notify = _noop
    _mod.log_event = _noop
    _mod.save_state = _noop

s5.CLOUD_STATE = False
s5.time.sleep = _noop      # execute_maker_or_chase's maker-poll wait
dp.time.sleep = _noop      # _ensure_bracket's hardened double-read wait


# ---------------------------------------------------------------------------
# candle builders
# ---------------------------------------------------------------------------

def _mk(closes, opens=None, highs=None, lows=None, volumes=None,
       start="2026-01-01", freq="1h"):
    n = len(closes)
    opens = opens if opens is not None else closes
    highs = highs if highs is not None else [max(o, c) for o, c in zip(opens, closes)]
    lows = lows if lows is not None else [min(o, c) for o, c in zip(opens, closes)]
    volumes = volumes if volumes is not None else [1.0] * n
    ts = pd.date_range(start, periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"timestamp": ts, "open": opens, "high": highs,
                         "low": lows, "close": closes, "volume": volumes})


def _flat_1d(n=55, price=100.0):
    return _mk([price] * n, freq="1d")


def _flat_1h(n=3, price=50.0):
    return _mk([price] * n, freq="1h")


def _quiet_1h(n=150, price=100.0, eps=0.0002):
    """A 1h series that is deliberately BORING (near-zero score) but NOT
    stale: two values strictly alternate, so the last 3 closes are never
    identical (passes the staleness guard), yet MA20/MA100 converge to the
    exact same mean (n even -> trend_1h stays silent), the ~symmetric
    +-eps deltas keep RSI3 near 50 (washout stays silent), momentum over 4
    bars is ~eps << 1% (silent), and volume is constant (no shock)."""
    if n % 2:
        n += 1
    a, b = price, price * (1 + eps)
    closes = [a if i % 2 == 0 else b for i in range(n)]
    return _mk(closes, freq="1h")


# ===========================================================================
# (a) scoring math on synthetic candles produces expected component sums
# ===========================================================================

def test_a_scoring_components():
    # -- trend_1d (+15) + trend_1h (+10), both LONG, isolated -------------
    # 1d: EXACTLY 55 bars -> rolling(55).max()/.min() shift(1) is NaN at
    # the last row (needs 55 prior bars, only 54 exist) -> breakout can
    # NEVER fire regardless of shape. 35 flat@100 + 20-bar ramp 105..200.
    c1d = _flat_1d(35, 100.0)
    ramp1d = _mk([105 + 5 * i for i in range(20)], freq="1d",
                start=c1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d = pd.concat([c1d, ramp1d], ignore_index=True)
    assert len(c1d) == 55

    # 1h: 100 bars, MA20 (last20) > MA100 (all100) by construction; last 5
    # bars flat so momentum_4h stays silent; volume constant so no shock.
    c1h = _flat_1h(80, 50.0)
    ramp1h = _mk([52 + 2 * i for i in range(15)], freq="1h",
                start=c1h["timestamp"].iloc[-1] + pd.Timedelta(hours=1))
    tail1h = _flat_1h(5, 80.0)
    tail1h["timestamp"] = pd.date_range(
        ramp1h["timestamp"].iloc[-1] + pd.Timedelta(hours=1), periods=5, freq="1h", tz="UTC")
    c1h = pd.concat([c1h, ramp1h, tail1h], ignore_index=True)
    assert len(c1h) == 100

    sc = dp.score_instrument(c1h, c1d, funding_bps=None)
    assert sc["long_score"] == 25.0, sc
    assert sc["short_score"] == 0.0, sc
    assert sc["conviction"] == 25.0, sc
    assert sc["direction"] == "long", sc
    names = {c["name"] for c in sc["components"]}
    assert names == {"trend_1d", "trend_1h"}, names
    by_name = {c["name"]: c for c in sc["components"]}
    assert by_name["trend_1d"]["long"] == 15.0
    assert by_name["trend_1h"]["long"] == 10.0

    # -- breakout THROUGH (+20) co-firing with trend_1d (+15) --------------
    # 56 bars: 55 flat@100 (a full, valid 55-bar window) then one spike to
    # 130 -> close > hi55(100) -> +20; the same spike also satisfies the
    # lagging-SMA trend condition -> +15. Both are legitimate, expected.
    c1d2 = _flat_1d(55, 100.0)
    spike = _mk([130.0], freq="1d",
               start=c1d2["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d2 = pd.concat([c1d2, spike], ignore_index=True)
    assert len(c1d2) == 56
    c1h2 = _flat_1h(3, 50.0)     # too short for any 1h-based component

    sc2 = dp.score_instrument(c1h2, c1d2, funding_bps=None)
    assert sc2["long_score"] == 35.0, sc2
    assert sc2["short_score"] == 0.0, sc2
    assert sc2["direction"] == "long", sc2
    names2 = {c["name"] for c in sc2["components"]}
    assert names2 == {"trend_1d", "breakout"}, names2
    by_name2 = {c["name"]: c for c in sc2["components"]}
    assert by_name2["breakout"]["long"] == 20.0

    # -- washout LONG (+20) co-firing with trend_1d (+15) and momentum
    #    SHORT (+8): a sharp 1h decline drives RSI3 well under 10 (washout
    #    needs a 1d UPtrend, supplied separately) AND necessarily also
    #    trips the 4h-momentum check the other way -- both are legitimate,
    #    hand-computed below. ---------------------------------------------
    c1d3 = c1d.copy()   # reuse the same clean 55-bar uptrend from above
    closes_1h3 = [100] * 10 + [90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
    c1h3 = _mk(closes_1h3, freq="1h", volumes=[1000.0] * 20)
    r3 = float(_rsi_check(pd.Series(closes_1h3), 3).iloc[-1])
    assert r3 < 10, f"fixture precondition failed: r3={r3}"

    sc3 = dp.score_instrument(c1h3, c1d3, funding_bps=None)
    assert sc3["long_score"] == 35.0, sc3          # 15 trend_1d + 20 washout
    assert sc3["short_score"] == 8.0, sc3           # 8 momentum_4h
    assert sc3["direction"] == "long", sc3
    names3 = {c["name"] for c in sc3["components"]}
    assert names3 == {"trend_1d", "washout", "momentum_4h"}, names3
    by_name3 = {c["name"]: c for c in sc3["components"]}
    assert by_name3["washout"]["long"] == 20.0
    assert by_name3["momentum_4h"]["short"] == 8.0

    # -- funding extreme, isolated, both directions -------------------------
    c1d_flat, c1h_flat = _flat_1d(55, 100.0), _flat_1h(3, 50.0)
    sc4 = dp.score_instrument(c1h_flat, c1d_flat, funding_bps=2.5)
    assert sc4["long_score"] == 0.0 and sc4["short_score"] == 8.0, sc4
    assert sc4["direction"] == "short", sc4
    assert sc4["components"] == [{"name": "funding", "long": 0.0, "short": 8.0}]

    sc5 = dp.score_instrument(c1h_flat, c1d_flat, funding_bps=-3.0)
    assert sc5["long_score"] == 8.0 and sc5["short_score"] == 0.0, sc5
    assert sc5["direction"] == "long", sc5

    sc6 = dp.score_instrument(c1h_flat, c1d_flat, funding_bps=1.0)
    assert sc6["long_score"] == 0.0 and sc6["short_score"] == 0.0, sc6
    assert sc6["components"] == [], "1.0bp is inside the +-2bp neutral band"

    # -- momentum_4h isolated (no washout: 1d flat -> trend_1d is None, so
    #    washout's own trend-alignment precondition can never be met even
    #    though this exact price path also drives RSI3 to 0) ---------------
    c1h6 = _mk([100, 100, 100, 100, 100, 90], freq="1h")
    sc7 = dp.score_instrument(c1h6, c1d_flat, funding_bps=None)
    assert sc7["long_score"] == 0.0 and sc7["short_score"] == 8.0, sc7
    assert sc7["components"] == [{"name": "momentum_4h", "long": 0.0, "short": 8.0}]

    # -- volume shock continuation (+15) co-firing with momentum (+8) -------
    closes8 = [100.0, 100.1] * 24 + [100.0, 106.0]     # 49 tiny-noise + 1 shock
    volumes8 = [100.0] * 49 + [1000.0]
    c1h8 = _mk(closes8, volumes=volumes8, freq="1h")
    assert len(c1h8) == 50
    sc8 = dp.score_instrument(c1h8, c1d_flat, funding_bps=None)
    assert sc8["long_score"] == 23.0, sc8          # 15 volume_shock + 8 momentum
    assert sc8["short_score"] == 0.0, sc8
    names8 = {c["name"] for c in sc8["components"]}
    assert names8 == {"volume_shock", "momentum_4h"}, names8


# ===========================================================================
# (b) staleness skip
# ===========================================================================

def test_b_staleness_skip():
    feed = FakeLiveFeed()
    # SYM-STALE: last 3 closed 1h bars share the exact same close
    feed.set_candles("SYM-STALE", "1h",
                     _mk([100, 100, 100, 100, 100], freq="1h"))
    feed.set_candles("SYM-STALE", "1d", _flat_1d(60, 100.0))
    # SYM-OK: a real, non-stale instrument
    c1d_up = _flat_1d(35, 100.0)
    ramp = _mk([105 + 5 * i for i in range(20)], freq="1d",
              start=c1d_up["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    feed.set_candles("SYM-OK", "1d", pd.concat([c1d_up, ramp], ignore_index=True))
    feed.set_candles("SYM-OK", "1h", _mk([50, 51, 52, 53, 54, 55], freq="1h"))

    analysis = dp.analyze_universe(feed, universe=["SYM-STALE", "SYM-OK"])
    by_sym = {a["symbol"]: a for a in analysis}
    assert by_sym["SYM-STALE"]["ok"] is True
    assert by_sym["SYM-STALE"]["stale"] is True
    assert by_sym["SYM-OK"]["stale"] is False
    assert by_sym["SYM-OK"]["ok"] is True

    # select_pick must never rank the stale one, even if it "scored" fine
    private = FakePrivate()
    demo = FakeDemoFeed(available=["SYM-STALE", "SYM-OK"],
                        specs={"SYM-OK": DEFAULT_SPEC})
    state = make_state()
    chosen, boredom, skips = dp.select_pick(analysis, private, demo, state)
    assert chosen is not None
    assert chosen[0]["symbol"] == "SYM-OK", chosen

    # a fetch failure behaves the same way (ok=False)
    class _BrokenFeed(FakeLiveFeed):
        def get_candles(self, symbol, timeframe, limit=300, end_ms=None):
            if symbol == "SYM-BROKEN":
                raise RuntimeError("Parameter instId error.")
            return super().get_candles(symbol, timeframe, limit, end_ms)

    bfeed = _BrokenFeed()
    bfeed.set_candles("SYM-OK", "1d", pd.concat([c1d_up, ramp], ignore_index=True))
    bfeed.set_candles("SYM-OK", "1h", _mk([50, 51, 52, 53, 54, 55], freq="1h"))
    analysis2 = dp.analyze_universe(bfeed, universe=["SYM-BROKEN", "SYM-OK"])
    by_sym2 = {a["symbol"]: a for a in analysis2}
    assert by_sym2["SYM-BROKEN"]["ok"] is False
    assert by_sym2["SYM-BROKEN"]["error"] is not None


# ===========================================================================
# (c) BTC guard — never opposes net, never picks BTC when a BTC book active
# ===========================================================================

def test_c_btc_guard():
    up_cand = {"symbol": "BTC-USDT", "conviction": 80.0, "direction": "long",
              "components": [], "long_score": 80, "short_score": 0}
    down_cand = {"symbol": "BTC-USDT", "conviction": 80.0, "direction": "short",
                "components": [], "long_score": 0, "short_score": 80}
    demo = FakeDemoFeed(specs={"BTC-USDT": DEFAULT_SPEC})

    # (i) a BTC book has an open trade -> BTC never even considered,
    #     regardless of direction or net.
    state = make_state()
    state["shorts_lab"]["open_trade"] = {"direction": -1, "contracts": 5.0}
    private = FakePrivate(net_by_symbol={"BTC-USDT": -5.0})
    ok, info = dp._guard_check(up_cand, private, demo, state)
    assert ok is False and "BTC book" in info, info

    # (ii) newsdesk has an ARMED PENDING (no position yet) -> still skip
    state2 = make_state()
    state2["newsdesk"]["pending"] = {"headline": "x"}
    private2 = FakePrivate(net_by_symbol={"BTC-USDT": 0.0})
    ok2, info2 = dp._guard_check(up_cand, private2, demo, state2)
    assert ok2 is False and "pending" in info2, info2

    # (iii) no BTC book active, but the exchange net OPPOSES the candidate's
    #       direction -> skip (direction gate, like newsdesk's own).
    state3 = make_state()
    private3 = FakePrivate(net_by_symbol={"BTC-USDT": 12.0})   # net LONG
    ok3, info3 = dp._guard_check(down_cand, private3, demo, state3)  # wants SHORT
    assert ok3 is False and "oppose" in info3, info3

    private3b = FakePrivate(net_by_symbol={"BTC-USDT": -12.0})  # net SHORT
    ok3b, info3b = dp._guard_check(up_cand, private3b, demo, state3)  # wants LONG
    assert ok3b is False and "oppose" in info3b, info3b

    # (iv) no BTC book active, net flat -> BTC clears every guard
    state4 = make_state()
    private4 = FakePrivate(net_by_symbol={"BTC-USDT": 0.0})
    ok4, spec4 = dp._guard_check(up_cand, private4, demo, state4)
    assert ok4 is True and spec4["contract_value"] == 1.0, (ok4, spec4)

    # (v) full select_pick walk: BTC ranks #1 but a BTC book is active ->
    #     the walk skips it and picks the next-ranked candidate instead.
    other_cand = {"symbol": "ETH-USDT", "ok": True, "stale": False,
                 "conviction": 60.0, "direction": "long", "components": [],
                 "long_score": 60, "short_score": 0, "atr_pct_1h": 1.0,
                 "last_close": 2000.0, "funding_bps": None}
    up_cand_full = dict(up_cand, ok=True, stale=False, atr_pct_1h=1.0,
                        last_close=65000.0, funding_bps=None)
    state5 = make_state()
    state5["tactical"]["open_trade"] = {"contracts": 3.0}   # a BTC book active
    private5 = FakePrivate(net_by_symbol={"BTC-USDT": 3.0, "ETH-USDT": 0.0})
    demo5 = FakeDemoFeed(specs={"BTC-USDT": DEFAULT_SPEC, "ETH-USDT": DEFAULT_SPEC})
    chosen, boredom, skips = dp.select_pick([up_cand_full, other_cand],
                                            private5, demo5, state5)
    assert chosen is not None and chosen[0]["symbol"] == "ETH-USDT", chosen
    assert any(s[0] == "BTC-USDT" for s in skips), skips


# ===========================================================================
# (d) already-held-symbol skip walks to the next-ranked candidate
# ===========================================================================

def test_d_already_held_skip():
    top = {"symbol": "ETH-USDT", "ok": True, "stale": False,
          "conviction": 70.0, "direction": "long", "components": [],
          "long_score": 70, "short_score": 0, "atr_pct_1h": 1.0,
          "last_close": 2000.0, "funding_bps": None}
    second = {"symbol": "SOL-USDT", "ok": True, "stale": False,
             "conviction": 55.0, "direction": "long", "components": [],
             "long_score": 55, "short_score": 0, "atr_pct_1h": 1.0,
             "last_close": 100.0, "funding_bps": None}
    state = make_state()
    # ETH is already held on the exchange (e.g. the gold-book-style "some
    # other process already has this symbol" case) -> must be skipped even
    # though it ranks highest, and SOL (guard-clean) gets picked instead.
    private = FakePrivate(net_by_symbol={"ETH-USDT": 4.2, "SOL-USDT": 0.0})
    demo = FakeDemoFeed(specs={"ETH-USDT": DEFAULT_SPEC, "SOL-USDT": DEFAULT_SPEC})
    chosen, boredom, skips = dp.select_pick([top, second], private, demo, state)
    assert chosen is not None and chosen[0]["symbol"] == "SOL-USDT", chosen
    assert boredom is False
    assert any(s[0] == "ETH-USDT" and "position" in s[1] for s in skips), skips


# ===========================================================================
# (e) boredom pick fires at half size when all convictions < 40
# ===========================================================================

def test_e_boredom_pick_half_size():
    weak_top = {"symbol": "ETH-USDT", "ok": True, "stale": False,
               "conviction": 25.0, "direction": "long", "components": [],
               "long_score": 25, "short_score": 0, "atr_pct_1h": 1.0,
               "last_close": 2000.0, "funding_bps": None}
    weak_second = {"symbol": "SOL-USDT", "ok": True, "stale": False,
                  "conviction": 18.0, "direction": "short", "components": [],
                  "long_score": 0, "short_score": 18, "atr_pct_1h": 1.0,
                  "last_close": 100.0, "funding_bps": None}
    state = make_state()
    private = FakePrivate(net_by_symbol={"ETH-USDT": 0.0, "SOL-USDT": 0.0})
    demo = FakeDemoFeed(specs={"ETH-USDT": DEFAULT_SPEC, "SOL-USDT": DEFAULT_SPEC})
    chosen, boredom, skips = dp.select_pick([weak_top, weak_second], private,
                                            demo, state)
    assert boredom is True, (chosen, boredom)
    assert chosen[0]["symbol"] == "ETH-USDT", chosen   # best-guarded, even <40

    plan_boredom = dp._build_entry_plan(chosen[0], chosen[1], 1000.0, True)
    plan_normal = dp._build_entry_plan(chosen[0], chosen[1], 1000.0, False)
    assert plan_boredom["alloc"] == dp.PICK_ALLOC * 0.5, plan_boredom
    assert plan_normal["alloc"] == dp.PICK_ALLOC, plan_normal
    assert abs(plan_boredom["notional"] - plan_normal["notional"] / 2) < 1e-6, \
        (plan_boredom["notional"], plan_normal["notional"])

    # end-to-end through run_daily_pick(dry=True): the "would_enter" result
    # must carry boredom_pick=True and half the normal contract count.
    feed = FakeLiveFeed()
    ramp1d = _flat_1d(35, 100.0)
    up = _mk([105 + 5 * i for i in range(20)], freq="1d",
            start=ramp1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d_weak = pd.concat([ramp1d, up], ignore_index=True)
    # both instruments deliberately score under 40 on real fetch, matched
    # to the fake pair above by giving them boring-but-not-stale data
    feed.set_candles("ETH-USDT", "1h", _quiet_1h(150, 2000.0))
    feed.set_candles("ETH-USDT", "1d", _flat_1d(60, 2000.0))
    feed.set_candles("SOL-USDT", "1h", _quiet_1h(150, 100.0))
    feed.set_candles("SOL-USDT", "1d", _flat_1d(60, 100.0))
    real_universe = dp._probe_universe
    dp._active_universe_cache = None
    demo2 = FakeDemoFeed(available=["ETH-USDT", "SOL-USDT"],
                         specs={"ETH-USDT": DEFAULT_SPEC, "SOL-USDT": DEFAULT_SPEC})
    orig_universe = dp.UNIVERSE
    dp.UNIVERSE = ["ETH-USDT", "SOL-USDT"]
    state2 = make_state()
    _freeze("2026-07-23 13:30:00")
    try:
        result = dp.run_daily_pick(private, feed, demo2, state2, dry=True)
    finally:
        _unfreeze()
        dp.UNIVERSE = orig_universe
        dp._active_universe_cache = None
    assert result["action"] == "would_enter", result
    assert result["boredom_pick"] is True, result
    assert result["conviction"] < dp.CONVICTION_FLOOR, result


# ===========================================================================
# (f) once-per-day idempotency
# ===========================================================================

def test_f_once_per_day_idempotency():
    feed = FakeLiveFeed()
    ramp1d = _flat_1d(35, 100.0)
    up = _mk([105 + 5 * i for i in range(20)], freq="1d",
            start=ramp1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d_up = pd.concat([ramp1d, up], ignore_index=True)
    for sym, px in (("BTC-USDT", 65000.0), ("ETH-USDT", 2000.0),
                    ("SOL-USDT", 100.0), ("XAUT-USDT", 4000.0),
                    ("TSLA-USDT", 300.0)):
        feed.set_candles(sym, "1d", c1d_up if sym == "ETH-USDT" else _flat_1d(60, px))
        feed.set_candles(sym, "1h", _quiet_1h(150, px))

    private = FakePrivate(net_by_symbol={s: 0.0 for s in dp.UNIVERSE},
                          fill_price=None)
    demo = FakeDemoFeed(available=set(dp.UNIVERSE),
                        specs={s: DEFAULT_SPEC for s in dp.UNIVERSE})
    state = make_state()
    dp._active_universe_cache = None

    _freeze("2026-07-23 13:15:00")
    try:
        r1 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r1["action"] == "entered", r1
        assert state["daily_pick"]["last_pick_date"] == "2026-07-23"
        n_orders_after_first = len(private.orders)
        # the fake private doesn't simulate a live exchange position by
        # itself (unlike the real BloFin, whose net stays put until a
        # bracket actually fires) -- mirror the entry onto net_by_symbol so
        # the next cycle's reconcile correctly sees "still open", exactly
        # like the real exchange would.
        signed = r1["contracts"] if r1["direction"] == "long" else -r1["contracts"]
        private.net_by_symbol[r1["symbol"]] = signed

        # same day, later cycle (still >=13:00 UTC): must NOT pick again.
        # (the open trade also isn't due for a time-exit yet, so this
        # exercises the "already open, not due" holding path too.)
        r2 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r2["action"] == "holding", r2
        assert len(private.orders) == n_orders_after_first, \
            "a second same-day cycle must place zero new entry orders"

        # force the book flat again and re-run the picking path directly
        # to double check the DATE gate itself (not just the open-trade
        # short-circuit above)
        state["daily_pick"]["open_trade"] = None
        r3 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r3["action"] == "waiting", r3
        assert len(private.orders) == n_orders_after_first, \
            "last_pick_date must block a same-day re-pick even when flat"
    finally:
        _unfreeze()
        dp._active_universe_cache = None


# ===========================================================================
# (g) reconcile books a TP exit with correct PnL and updates the
#     conviction_ledger bucket
# ===========================================================================

def test_g_reconcile_tp_exit_and_ledger_bucket():
    entry, exit_price, contracts, contract_value = 100.0, 97.5, 10.0, 1.0
    t = {"symbol": "SOL-USDT", "direction": -1, "contracts": contracts,
        "entry_price": entry, "entry_fee_bps": 6.0,
        "entry_time": s5.now_utc(), "tp_price": 97.6, "sl_price": 101.2,
        "tpsl_id": "tpsl-x", "max_hold_h": 24.0, "conviction": 52.0,
        "boredom_pick": False, "top_component": "breakout",
        "leverage": 10.0, "contract_value": contract_value,
        "ctx": {"atr_pct": 1.2, "funding_bps": None, "components": [],
               "explain": "breakout +20"}}
    state = make_state()
    state["daily_pick"] = dp._fresh_dp()
    state["daily_pick"]["open_trade"] = t

    private = FakePrivate(net_by_symbol={"SOL-USDT": 0.0},
                          fill_price=exit_price)

    _freeze("2026-07-23 05:00:00")   # well before pick time -> reconcile only
    try:
        result = dp.run_daily_pick(private, FakeLiveFeed(), FakeDemoFeed(),
                                   state, dry=False)
    finally:
        _unfreeze()

    assert result["action"] == "holding" or state["daily_pick"]["open_trade"] is None
    assert state["daily_pick"]["open_trade"] is None, "the exit must be booked"

    size = contracts * contract_value
    gross = -1 * (exit_price - entry) * size
    fees = (entry * 6.0 + exit_price * 2.0) * size / 10_000    # TP -> maker
    expected_pnl = round(gross - fees, 2)
    assert expected_pnl > 0, "sanity: a short profiting on a fall is positive"
    assert state["virtual_equity"] == round(1000.0 + expected_pnl, 2), \
        (state["virtual_equity"], round(1000.0 + expected_pnl, 2))

    bucket = dp._bucket(52.0)
    assert bucket == "45-59", bucket
    ledger = state["daily_pick"]["conviction_ledger"][bucket]
    assert ledger["n"] == 1, ledger
    assert ledger["wins"] == 1, ledger
    assert abs(ledger["pnl"] - expected_pnl) < 1e-6, ledger

    assert state["trigger_stats"]["daily_pick"]["n"] == 1
    assert abs(state["trigger_stats"]["daily_pick"]["pnl"] - expected_pnl) < 1e-6
    assert state["trigger_stats"]["pick_breakout"]["n"] == 1
    assert abs(state["trigger_stats"]["pick_breakout"]["pnl"] - expected_pnl) < 1e-6


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_a_scoring_components,
        test_b_staleness_skip,
        test_c_btc_guard,
        test_d_already_held_skip,
        test_e_boredom_pick_half_size,
        test_f_once_per_day_idempotency,
        test_g_reconcile_tp_exit_and_ledger_bucket,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("DAILY PICK TEST SUMMARY")
    print("=" * 72)
    n_pass = 0
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        print(f"  [{status}] {name}")
        if not ok:
            for line in err.splitlines():
                print(f"          {line}")
    print("-" * 72)
    print(f"  {n_pass}/{len(results)} passed")
    print("=" * 72 + "\n")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
