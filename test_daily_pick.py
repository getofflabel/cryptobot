"""
test_daily_pick.py — offline tests for daily_pick.py. NO NETWORK.

2026-07-24 LEARNING-ENGINE UPGRADE: daily_pick.py went from a once-a-day,
one-position book to a 2-hour-slot, up-to-3-concurrent-position book (see
daily_pick.py's module docstring for the full design). This file covers
both the pieces that stayed the same (scoring math, staleness, the BTC
guard, the already-held-elsewhere guard) and the new mechanics (2h slot
idempotency, the 3-concurrent/different-symbols cap, half-risk low-
conviction sizing, the 4h time exit, the daybook + daily recap, and
auto-bench actually silencing a component type in scoring).

Reuses the codebase's own fake/neutralization convention (see
test_book_attribution.py): a FakePrivate that never makes an HTTP call and
records every order/cancel/bracket call, fake candle/instrument feeds, and
notify/log_event/save_state monkeypatched to no-ops on EVERY module whose
own bound name would otherwise be called (daily_pick.py directly, AND
step5_paper_trade.py — record_trade_outcome/write_lesson live there and
call ITS OWN module-level log_event/notify, not daily_pick's copy).

Eleven intents:
  a) scoring math on synthetic candles produces expected component sums
  b) staleness skip
  c) BTC guard — never opposes net, never picks BTC when a BTC book is active
  d) already-held-elsewhere (exchange net) skip walks to the next candidate
  e) low-conviction pick fires at HALF RISK when conviction < floor
  f) 2h slot idempotency — no re-pick within a slot, a fresh pick on the
     next slot, routed around a still-open symbol (slots recycle)
  g) 3-concurrent cap + different-symbols rule (own open_trades)
  h) 4h time exit (reduce-only, forced regardless of slot cadence)
  i) reconcile books a TP exit with correct PnL, updates the
     conviction_ledger bucket, AND appends a daybook entry
  j) the daily recap notify fires once per new UTC day, off yesterday's
     daybook, and never twice the same day
  k) an auto-benched "pick_<tag>" trigger makes that component type stop
     contributing to scoring entirely; other components are unaffected

Run with:  python3 test_daily_pick.py
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta, timezone

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
    # HORIZON COHERENCE (2026-07-24): the daily trend no longer votes
    # direction — the intraday trend_1h leads (+10) and the agreeing daily
    # adds only the +5 alignment bonus.
    assert sc["long_score"] == 15.0, sc
    assert sc["short_score"] == 0.0, sc
    assert sc["conviction"] == 15.0, sc
    assert sc["direction"] == "long", sc
    names = {c["name"] for c in sc["components"]}
    assert names == {"trend_1d_align", "trend_1h"}, names
    by_name = {c["name"]: c for c in sc["components"]}
    assert by_name["trend_1d_align"]["long"] == 5.0
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
    assert sc2["long_score"] == 25.0, sc2      # breakout 20 + align bonus 5
    assert sc2["short_score"] == 0.0, sc2
    assert sc2["direction"] == "long", sc2
    names2 = {c["name"] for c in sc2["components"]}
    assert names2 == {"trend_1d_align", "breakout"}, names2
    by_name2 = {c["name"]: c for c in sc2["components"]}
    assert by_name2["breakout"]["long"] == 20.0

    # -- washout LONG (+20) co-firing with trend_1d (+15) and momentum
    #    SHORT (+8): a sharp 1h decline drives RSI3 well under 10 (washout
    #    needs a 1d UPtrend, supplied separately) AND necessarily also
    #    trips the 4h-momentum check the other way -- both are legitimate,
    #    hand-computed below. ---------------------------------------------
    c1d3 = c1d.copy()   # reuse the same clean 55-bar uptrend from above
    # KNIFE-CATCH GUARD (2026-07-24): a straight decline (no turn candle)
    # must NOT fire washout anymore — oversold alone is not a buy.
    closes_knife = [100] * 10 + [90, 80, 70, 60, 50, 40, 30, 20, 10, 0]
    c1h_knife = _mk(closes_knife, freq="1h", volumes=[1000.0] * 20)
    sc_knife = dp.score_instrument(c1h_knife, c1d3, funding_bps=None)
    assert all(c["name"] != "washout" for c in sc_knife["components"]), sc_knife

    # ...but the same washout WITH a small green turn bar (close > open and
    # > prior close, RSI3 still deeply oversold) DOES fire.
    closes_1h3 = [100] * 10 + [90, 80, 70, 60, 50, 40, 30, 20, 10, 10.5]
    c1h3 = _mk(closes_1h3, freq="1h", volumes=[1000.0] * 20)
    # _mk builds doji bars (open == close); the turn candle needs a real
    # green body, so hand-set the final bar's open below its close.
    c1h3.loc[c1h3.index[-1], "open"] = 10.0
    r3 = float(_rsi_check(pd.Series(closes_1h3), 3).iloc[-1])
    assert r3 < 10, f"fixture precondition failed: r3={r3}"

    sc3 = dp.score_instrument(c1h3, c1d3, funding_bps=None)
    assert sc3["long_score"] == 25.0, sc3    # 20 washout + 5 align bonus
    assert sc3["short_score"] == 8.0, sc3    # 8 momentum_4h
    assert sc3["direction"] == "long", sc3
    names3 = {c["name"] for c in sc3["components"]}
    assert names3 == {"trend_1d_align", "washout", "momentum_4h"}, names3
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
    chosen, low_conv, skips = dp.select_pick(analysis, private, demo, state)
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
    chosen, low_conv, skips = dp.select_pick([up_cand_full, other_cand],
                                             private5, demo5, state5)
    assert chosen is not None and chosen[0]["symbol"] == "ETH-USDT", chosen
    assert any(s[0] == "BTC-USDT" for s in skips), skips


# ===========================================================================
# (d) already-held-elsewhere (exchange net) skip walks to the next candidate
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
    chosen, low_conv, skips = dp.select_pick([top, second], private, demo, state)
    assert chosen is not None and chosen[0]["symbol"] == "SOL-USDT", chosen
    assert low_conv is False
    assert any(s[0] == "ETH-USDT" and "position" in s[1] for s in skips), skips


# ===========================================================================
# (e) low-conviction pick fires at HALF RISK when conviction < floor
# ===========================================================================

def test_e_low_conviction_half_risk():
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
    chosen, low_conv, skips = dp.select_pick([weak_top, weak_second], private,
                                             demo, state)
    assert low_conv is True, (chosen, low_conv)
    assert chosen[0]["symbol"] == "ETH-USDT", chosen   # best-guarded, even <40

    plan_low = dp._build_entry_plan(chosen[0], chosen[1], 1000.0, True)
    plan_normal = dp._build_entry_plan(chosen[0], chosen[1], 1000.0, False)
    assert plan_low["risk_pct"] == dp.RISK_PCT * dp.LOW_CONV_RISK_MULT, plan_low
    assert plan_normal["risk_pct"] == dp.RISK_PCT, plan_normal
    assert abs(plan_low["notional"] - plan_normal["notional"] / 2) < 1e-6, \
        (plan_low["notional"], plan_normal["notional"])

    # end-to-end through run_daily_pick(dry=True): the "would_enter" result
    # must carry low_conviction=True and half the normal contract count.
    feed = FakeLiveFeed()
    feed.set_candles("ETH-USDT", "1h", _quiet_1h(150, 2000.0))
    feed.set_candles("ETH-USDT", "1d", _flat_1d(60, 2000.0))
    feed.set_candles("SOL-USDT", "1h", _quiet_1h(150, 100.0))
    feed.set_candles("SOL-USDT", "1d", _flat_1d(60, 100.0))
    dp._active_universe_cache = None
    demo2 = FakeDemoFeed(available=["ETH-USDT", "SOL-USDT"],
                         specs={"ETH-USDT": DEFAULT_SPEC, "SOL-USDT": DEFAULT_SPEC})
    orig_universe = dp.UNIVERSE
    dp.UNIVERSE = ["ETH-USDT", "SOL-USDT"]
    state2 = make_state()
    _freeze("2026-07-23 14:15:00")
    try:
        result = dp.run_daily_pick(private, feed, demo2, state2, dry=True)
    finally:
        _unfreeze()
        dp.UNIVERSE = orig_universe
        dp._active_universe_cache = None
    assert result["due"] is True, result
    assert result["entry"]["action"] == "would_enter", result
    assert result["entry"]["low_conviction"] is True, result
    assert result["entry"]["conviction"] < dp.CONVICTION_FLOOR, result
    # dry mode: zero persisted side effects
    assert state2["daily_pick"]["last_slot_ts"] is None, state2["daily_pick"]
    assert state2["daily_pick"]["open_trades"] == [], state2["daily_pick"]


# ===========================================================================
# (f) 2h slot idempotency — no re-pick within a slot, a fresh pick on the
#     next slot, routed around a still-open symbol (slots recycle)
# ===========================================================================

def test_f_slot_idempotency_and_recycling():
    feed = FakeLiveFeed()
    ramp1d = _flat_1d(35, 100.0)
    up = _mk([105 + 5 * i for i in range(20)], freq="1d",
            start=ramp1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d_up = pd.concat([ramp1d, up], ignore_index=True)
    # HORIZON COHERENCE (2026-07-24): the daily trend no longer votes, so
    # ETH's edge in this fixture must live on the INTRADAY chart — give it
    # a 1h uptrend (MA20>MA100) alongside the 1d one (align bonus).
    eth_1h = _quiet_1h(130, 1800.0)
    eth_ramp = _mk([1810 + 12 * i for i in range(20)], freq="1h",
                  start=eth_1h["timestamp"].iloc[-1] + pd.Timedelta(hours=1))
    eth_1h_up = pd.concat([eth_1h, eth_ramp], ignore_index=True)
    for sym, px in (("BTC-USDT", 65000.0), ("ETH-USDT", 2000.0),
                    ("SOL-USDT", 100.0), ("XAUT-USDT", 4000.0),
                    ("TSLA-USDT", 300.0)):
        feed.set_candles(sym, "1d", c1d_up if sym == "ETH-USDT" else _flat_1d(60, px))
        feed.set_candles(sym, "1h",
                        eth_1h_up if sym == "ETH-USDT" else _quiet_1h(150, px))

    private = FakePrivate(net_by_symbol={s: 0.0 for s in dp.UNIVERSE},
                          fill_price=None)
    demo = FakeDemoFeed(available=set(dp.UNIVERSE),
                        specs={s: DEFAULT_SPEC for s in dp.UNIVERSE})
    state = make_state()
    dp._active_universe_cache = None

    try:
        _freeze("2026-07-23 14:15:00")
        r1 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r1["due"] is True, r1
        assert r1["entry"]["action"] == "entered", r1
        assert r1["entry"]["symbol"] == "ETH-USDT", r1   # the only real uptrend
        assert state["daily_pick"]["last_slot_ts"] == "2026-07-23T14:00 UTC", \
            state["daily_pick"]["last_slot_ts"]
        n_orders_after_first = len(private.orders)

        # mirror the entry onto net_by_symbol so the next cycle's reconcile
        # correctly sees "still open", exactly like the real exchange would
        # (the fake private doesn't simulate a live exchange position by
        # itself, unlike real BloFin whose net stays put until a bracket
        # actually fires).
        signed = (r1["entry"]["contracts"] if r1["entry"]["direction"] == "long"
                 else -r1["entry"]["contracts"])
        private.net_by_symbol["ETH-USDT"] = signed

        # same slot (14:00-15:59 window), a later cycle: must NOT pick
        # again even though capacity remains (1/3 used) — the slot
        # idempotency key blocks it outright (due=False).
        _freeze("2026-07-23 15:45:00")
        r2 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r2["due"] is False, r2
        assert r2["entry"] is None, r2
        assert len(private.orders) == n_orders_after_first, \
            "a second same-slot cycle must place zero new entry orders"
        assert any(h["symbol"] == "ETH-USDT" for h in r2["holding"]), r2

        # the NEXT slot (16:00-17:59 window): due again, capacity remains
        # -> a SECOND, DIFFERENT-symbol pick fires ("slots recycle").
        _freeze("2026-07-23 16:05:00")
        r3 = dp.run_daily_pick(private, feed, demo, state, dry=False)
        assert r3["due"] is True, r3
        assert r3["entry"]["action"] == "entered", r3
        assert r3["entry"]["symbol"] != "ETH-USDT", \
            "the different-symbols rule must route around the still-open pick"
        assert state["daily_pick"]["last_slot_ts"] == "2026-07-23T16:00 UTC", \
            state["daily_pick"]["last_slot_ts"]
        assert len(state["daily_pick"]["open_trades"]) == 2, \
            state["daily_pick"]["open_trades"]
    finally:
        _unfreeze()
        dp._active_universe_cache = None


# ===========================================================================
# (g) 3-concurrent cap + different-symbols rule
# ===========================================================================

def test_g_three_concurrent_cap_and_different_symbols():
    # (i) guard: a candidate for a symbol we ALREADY hold ourselves is
    #     rejected before any network read — the different-symbols rule.
    state = make_state()
    state["daily_pick"] = dp._fresh_dp()
    state["daily_pick"]["open_trades"] = [
        {"symbol": "BTC-USDT", "direction": 1, "contracts": 1.0},
        {"symbol": "ETH-USDT", "direction": -1, "contracts": 2.0},
    ]
    cand_dupe = {"symbol": "BTC-USDT", "conviction": 80.0, "direction": "long",
                "components": [], "long_score": 80, "short_score": 0}
    demo = FakeDemoFeed(specs={"BTC-USDT": DEFAULT_SPEC})
    private = FakePrivate(net_by_symbol={"BTC-USDT": 1.0, "ETH-USDT": -2.0})
    ok, info = dp._guard_check(cand_dupe, private, demo, state)
    assert ok is False and "own open slots" in info, info

    # a THIRD, different symbol still clears every guard fine
    cand_new = {"symbol": "SOL-USDT", "conviction": 60.0, "direction": "long",
               "components": [], "long_score": 60, "short_score": 0}
    demo2 = FakeDemoFeed(specs={"BTC-USDT": DEFAULT_SPEC, "ETH-USDT": DEFAULT_SPEC,
                                "SOL-USDT": DEFAULT_SPEC})
    ok2, spec2 = dp._guard_check(cand_new, private, demo2, state)
    assert ok2 is True, spec2

    # (ii) full cycle: 3 concurrent slots already open -> a due slot must
    #      report "at_capacity" and place ZERO new orders, but still stamp
    #      last_slot_ts (idempotency preserved even on a no-trade slot).
    try:
        _freeze("2026-07-23 14:15:00")
        frozen_now = dp.datetime.now(timezone.utc)
        entry_time_str = f"{frozen_now:%Y-%m-%d %H:%M:%S} UTC"

        def _open(symbol):
            return {"symbol": symbol, "direction": 1, "contracts": 1.0,
                    "entry_price": 100.0, "entry_time": entry_time_str,
                    "tp_price": 110.0, "sl_price": 95.0, "tpsl_id": "tpsl1",
                    "max_hold_h": 4.0, "conviction": 60.0,
                    "low_conviction": False, "top_component": "trend",
                    "contract_value": 1.0}

        state2 = make_state()
        state2["daily_pick"] = dp._fresh_dp()
        state2["daily_pick"]["open_trades"] = [
            _open("BTC-USDT"), _open("ETH-USDT"), _open("SOL-USDT")]
        private2 = FakePrivate(net_by_symbol={"BTC-USDT": 1.0, "ETH-USDT": 1.0,
                                              "SOL-USDT": 1.0})
        demo3 = FakeDemoFeed(available=set(dp.UNIVERSE),
                             specs={s: DEFAULT_SPEC for s in dp.UNIVERSE})
        result = dp.run_daily_pick(private2, FakeLiveFeed(), demo3, state2,
                                   dry=False)
    finally:
        _unfreeze()

    assert result["due"] is True, result
    assert result["open_count"] == 3, result
    assert result["entry"]["action"] == "at_capacity", result
    assert len(private2.orders) == 0, "at capacity: zero new orders"
    assert state2["daily_pick"]["last_slot_ts"] == dp._slot_ts(frozen_now)


# ===========================================================================
# (h) 4h time exit (reduce-only, forced regardless of slot cadence)
# ===========================================================================

def test_h_four_hour_time_exit():
    entry_price, contracts, contract_value = 100.0, 5.0, 1.0
    try:
        _freeze("2026-07-23 05:00:00")
        frozen_now = dp.datetime.now(timezone.utc)
        entry_dt = frozen_now - timedelta(hours=4, minutes=5)   # just over 4h
        entry_time_str = f"{entry_dt:%Y-%m-%d %H:%M:%S} UTC"
        t = {"symbol": "SOL-USDT", "direction": 1, "contracts": contracts,
            "entry_price": entry_price, "entry_fee_bps": 6.0,
            "entry_time": entry_time_str, "tp_price": 110.0, "sl_price": 90.0,
            "tpsl_id": "tpsl1", "max_hold_h": dp.MAX_HOLD_H,
            "conviction": 55.0, "low_conviction": False,
            "top_component": "momentum", "contract_value": contract_value,
            "ctx": {"atr_pct": 0.8, "funding_bps": None, "components": [],
                   "explain": "momentum +8"}}
        state = make_state()
        state["daily_pick"] = dp._fresh_dp()
        # not due this cycle — isolate the time-exit mechanic
        state["daily_pick"]["last_slot_ts"] = dp._slot_ts(frozen_now)
        state["daily_pick"]["open_trades"] = [t]
        # exchange still shows the position live (net == contracts) -> not
        # a bracket exit; must be forced by the 4h clock, not by due-ness
        private = FakePrivate(net_by_symbol={"SOL-USDT": contracts},
                              fill_price=None)
        demo = FakeDemoFeed(tickers={"SOL-USDT": 101.5})
        result = dp.run_daily_pick(private, FakeLiveFeed(), demo, state,
                                   dry=False)
    finally:
        _unfreeze()

    assert result["due"] is False, result
    assert state["daily_pick"]["open_trades"] == [], "4h time exit must close it"
    assert any(o["reduce_only"] for o in private.orders), \
        "the time exit must be reduce-only"
    assert result["exits"] and result["exits"][0]["action"] == "time_exit", result

    daybook = state["daily_pick"]["daybook"]
    assert len(daybook) == 1, daybook
    rec = daybook[0]
    assert rec["symbol"] == "SOL-USDT"
    assert rec["dir"] == "long"
    assert rec["hold_min"] > 240, rec   # just over 4h
    assert rec["setup"] == "momentum"


# ===========================================================================
# (i) reconcile books a TP exit with correct PnL, updates the
#     conviction_ledger bucket, AND appends a daybook entry
# ===========================================================================

def test_i_reconcile_tp_exit_ledger_and_daybook():
    entry, exit_price, contracts, contract_value = 100.0, 97.5, 10.0, 1.0
    try:
        _freeze("2026-07-23 05:00:00")
        frozen_now = dp.datetime.now(timezone.utc)
        entry_time_str = f"{frozen_now - timedelta(minutes=37):%Y-%m-%d %H:%M:%S} UTC"
        t = {"symbol": "SOL-USDT", "direction": -1, "contracts": contracts,
            "entry_price": entry, "entry_fee_bps": 6.0,
            "entry_time": entry_time_str, "tp_price": 97.6, "sl_price": 101.2,
            "tpsl_id": "tpsl-x", "max_hold_h": 4.0, "conviction": 52.0,
            "low_conviction": False, "top_component": "breakout",
            "contract_value": contract_value,
            "ctx": {"atr_pct": 1.2, "funding_bps": None, "components": [],
                   "explain": "breakout +20"}}
        state = make_state()
        state["daily_pick"] = dp._fresh_dp()
        state["daily_pick"]["last_slot_ts"] = dp._slot_ts(frozen_now)   # not due
        state["daily_pick"]["open_trades"] = [t]

        private = FakePrivate(net_by_symbol={"SOL-USDT": 0.0},
                              fill_price=exit_price)
        result = dp.run_daily_pick(private, FakeLiveFeed(), FakeDemoFeed(),
                                   state, dry=False)
    finally:
        _unfreeze()

    assert result["due"] is False, result
    assert state["daily_pick"]["open_trades"] == [], "the exit must be booked"
    assert result["exits"] and result["exits"][0]["action"] == "exit", result

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

    daybook = state["daily_pick"]["daybook"]
    assert len(daybook) == 1, daybook
    rec = daybook[0]
    assert rec["symbol"] == "SOL-USDT"
    assert rec["dir"] == "short"
    assert rec["conviction"] == 52.0
    assert rec["setup"] == "breakout"
    assert rec["low_conviction"] is False
    assert abs(rec["outcome_pnl"] - expected_pnl) < 1e-6
    assert 30 <= rec["hold_min"] <= 40, rec   # ~37 minutes held
    assert rec["date"] == "2026-07-23", rec


# ===========================================================================
# (j) the daily recap notify fires once per new UTC day, off yesterday's
#     daybook, and never twice the same day
# ===========================================================================

def test_j_daily_recap_trigger():
    state = make_state()
    state["daily_pick"] = dp._fresh_dp()
    state["daily_pick"]["daybook"] = [
        {"date": "2026-07-22", "symbol": "ETH-USDT", "dir": "long",
         "conviction": 60.0, "components": [], "outcome_pnl": 12.5,
         "hold_min": 90.0, "setup": "breakout", "low_conviction": False},
        {"date": "2026-07-22", "symbol": "SOL-USDT", "dir": "short",
         "conviction": 45.0, "components": [], "outcome_pnl": -4.0,
         "hold_min": 130.0, "setup": "breakout", "low_conviction": False},
        {"date": "2026-07-22", "symbol": "BTC-USDT", "dir": "long",
         "conviction": 20.0, "components": [], "outcome_pnl": -6.0,
         "hold_min": 200.0, "setup": None, "low_conviction": True},
        {"date": "2026-07-21", "symbol": "XAUT-USDT", "dir": "long",
         "conviction": 70.0, "components": [], "outcome_pnl": 999.0,
         "hold_min": 60.0, "setup": "trend", "low_conviction": False},
    ]

    notified = []
    orig_notify = dp.notify
    dp.notify = lambda title, message: notified.append((title, message))
    dp._active_universe_cache = None
    demo = FakeDemoFeed()   # empty universe -> "slot passed", recap still fires
    try:
        _freeze("2026-07-23 00:15:00")
        r1 = dp.run_daily_pick(FakePrivate(), FakeLiveFeed(), demo, state,
                               dry=False)
        assert r1["due"] is True, r1
        assert state["daily_pick"]["last_recap_date"] == "2026-07-23", \
            state["daily_pick"]
        assert len(notified) == 1, notified
        title, msg = notified[0]
        assert "recap" in title.lower(), title
        assert "3 trades" in msg, msg              # only 2026-07-22's 3 rows
        assert "1W/2L" in msg, msg
        assert "999" not in msg, "must never leak 07-21's data into the recap"
        assert "breakout" in msg, msg

        # a second due slot the SAME day must NOT re-fire the recap
        notified.clear()
        state["daily_pick"]["last_slot_ts"] = None   # force another due slot
        r2 = dp.run_daily_pick(FakePrivate(), FakeLiveFeed(), demo, state,
                               dry=False)
        assert r2["due"] is True, r2
        assert notified == [], "recap must fire once per day, not per slot"
    finally:
        dp.notify = orig_notify
        _unfreeze()
        dp._active_universe_cache = None


# ===========================================================================
# (k) an auto-benched "pick_<tag>" trigger makes that component type stop
#     contributing to scoring entirely; other components are unaffected
# ===========================================================================

def test_k_benched_component_stops_firing():
    c1d = _flat_1d(35, 100.0)
    ramp1d = _mk([105 + 5 * i for i in range(20)], freq="1d",
                start=c1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d = pd.concat([c1d, ramp1d], ignore_index=True)
    c1h = _flat_1h(80, 50.0)
    ramp1h = _mk([52 + 2 * i for i in range(15)], freq="1h",
                start=c1h["timestamp"].iloc[-1] + pd.Timedelta(hours=1))
    tail1h = _mk([80.0, 80.1, 80.0, 80.1, 80.0], freq="1h",
                start=ramp1h["timestamp"].iloc[-1] + pd.Timedelta(hours=1))
    c1h = pd.concat([c1h, ramp1h, tail1h], ignore_index=True)

    # unbenched: trend_1h (+10) leads, agreeing 1d adds the +5 align bonus
    sc_normal = dp.score_instrument(c1h, c1d, funding_bps=None)
    assert sc_normal["long_score"] == 15.0, sc_normal

    # "pick_trend" benched -> BOTH trend_1d and trend_1h (they share the
    # "trend" tag, see COMPONENT_TAG) stop contributing, entirely.
    sc_benched = dp.score_instrument(c1h, c1d, funding_bps=None,
                                     benched=["pick_trend"])
    assert sc_benched["long_score"] == 0.0, sc_benched
    assert sc_benched["short_score"] == 0.0, sc_benched
    assert sc_benched["components"] == [], sc_benched
    assert sc_benched["conviction"] == 5.0, sc_benched   # floor, nothing fired

    # a DIFFERENT component type (funding) is unaffected by benching
    # "pick_trend" — the engine keeps scoring on everything still healthy.
    c1d_flat, c1h_flat = _flat_1d(55, 100.0), _flat_1h(3, 50.0)
    sc_other = dp.score_instrument(c1h_flat, c1d_flat, funding_bps=2.5,
                                   benched=["pick_trend"])
    assert sc_other["short_score"] == 8.0, sc_other

    # analyze_universe forwards `benched` through to score_instrument
    feed = FakeLiveFeed()
    feed.set_candles("X-USDT", "1d", c1d)
    feed.set_candles("X-USDT", "1h", c1h)
    analysis = dp.analyze_universe(feed, ["X-USDT"], benched=["pick_trend"])
    assert analysis[0]["conviction"] == 5.0, analysis[0]


# ===========================================================================
# THE MISSED-TRADE LEDGER (2026-07-24 upgrade) — six more intents:
#   l) select_pick logs every skip (all 5 reason tags) to passed_log with
#      the SAME stop/target geometry a real entry would have used
#   m) score_passed_trades replays the tight-zone bracket against real
#      candles correctly — hand-verified stop-hit, target-hit, and
#      4h-time-exit cases, plus the "too young to judge yet" gate
#   n) once an entry is scored it is NEVER re-fetched/re-simulated
#   o) passed_log is capped at PASSED_LOG_CAP, oldest dropped first
#   p) the recap's missed-trade lines render correctly from a seeded,
#      already-scored passed_log/gate_scoreboard, never leaking a
#      different day's numbers in
# ===========================================================================

def _cf_entry(symbol, direction, conviction, reason, ref_price, stop_pct,
             target_pct, ts="2026-07-23T10:00 UTC"):
    """A hand-built passed_log entry, bypassing select_pick, so
    score_passed_trades() tests can control geometry/timing exactly."""
    return {"ts": ts, "symbol": symbol, "direction": direction,
            "conviction": conviction, "reason": reason, "ref_price": ref_price,
            "stop_pct": stop_pct, "target_pct": target_pct, "scored": False}


def _row_candles(rows):
    return pd.DataFrame(rows)


# ===========================================================================
# (l) select_pick logs every skip to passed_log with correct geometry
# ===========================================================================

def test_l_passed_log_geometry():
    def _clean_cand(symbol, direction, conviction, regime="normal", atr=1.0):
        return {"symbol": symbol, "ok": True, "stale": False,
               "conviction": conviction, "direction": direction,
               "components": [], "long_score": conviction if direction == "long" else 0,
               "short_score": conviction if direction == "short" else 0,
               "atr_pct_1h": atr, "last_close": 2000.0 if symbol == "ETH-USDT"
               else (50.0 if symbol == "SOL-USDT" else 65000.0),
               "funding_bps": None, "regime": regime}

    # -- guard fail: ETH already held on the exchange -----------------------
    top = _clean_cand("ETH-USDT", "long", 70.0)
    second = _clean_cand("SOL-USDT", "long", 55.0)
    state = make_state()
    private = FakePrivate(net_by_symbol={"ETH-USDT": 4.2, "SOL-USDT": 0.0})
    demo = FakeDemoFeed(specs={"ETH-USDT": DEFAULT_SPEC, "SOL-USDT": DEFAULT_SPEC})
    try:
        _freeze("2026-07-23 14:15:00")
        chosen, low_conv, skips = dp.select_pick([top, second], private, demo, state)
    finally:
        _unfreeze()
    assert chosen is not None and chosen[0]["symbol"] == "SOL-USDT", chosen
    log = state["daily_pick"]["passed_log"]
    assert len(log) == 1, log
    entry = log[0]
    assert entry["symbol"] == "ETH-USDT"
    assert entry["direction"] == "long"
    assert entry["conviction"] == 70.0
    assert entry["reason"] == "guard"
    assert entry["ref_price"] == 2000.0
    assert entry["scored"] is False
    exp_stop, exp_target = dp._stop_target_pct(1.0)
    assert entry["stop_pct"] == exp_stop and entry["target_pct"] == exp_target, entry
    assert entry["ts"] == "2026-07-23T14:00 UTC", entry

    # -- calm-regime gate: below-floor conviction in a calm regime ----------
    calm_cand = _clean_cand("SOL-USDT", "long", 20.0, regime="calm")
    state2 = make_state()
    private2 = FakePrivate(net_by_symbol={"SOL-USDT": 0.0})
    demo2 = FakeDemoFeed(specs={"SOL-USDT": DEFAULT_SPEC})
    try:
        _freeze("2026-07-23 14:15:00")
        chosen2, _, _ = dp.select_pick([calm_cand], private2, demo2, state2)
    finally:
        _unfreeze()
    assert chosen2 is None, chosen2
    log2 = state2["daily_pick"]["passed_log"]
    assert len(log2) == 1 and log2[0]["reason"] == "calm_gate", log2

    # -- cooldown: a recent loss on the exact same (symbol, direction) ------
    cool_cand = _clean_cand("SOL-USDT", "long", 50.0)
    state3 = make_state()
    private3 = FakePrivate(net_by_symbol={"SOL-USDT": 0.0})
    demo3 = FakeDemoFeed(specs={"SOL-USDT": DEFAULT_SPEC})
    try:
        _freeze("2026-07-23 14:15:00")
        frozen_now = dp.datetime.now(timezone.utc)
        state3["daily_pick"] = dp._fresh_dp()
        state3["daily_pick"]["last_stopouts"] = {
            "SOL-USDT:long": {"ts": (frozen_now - timedelta(hours=1)).isoformat(),
                              "conviction": 50.0}}
        chosen3, _, _ = dp.select_pick([cool_cand], private3, demo3, state3)
    finally:
        _unfreeze()
    assert chosen3 is None, chosen3
    log3 = state3["daily_pick"]["passed_log"]
    assert len(log3) == 1 and log3[0]["reason"] == "cooldown", log3

    # -- one-thesis: the crypto cluster is MIXED (both directions open) -----
    thesis_cand = _clean_cand("SOL-USDT", "long", 50.0)
    state4 = make_state()
    private4 = FakePrivate(net_by_symbol={"BTC-USDT": 1.0, "ETH-USDT": -1.0,
                                          "SOL-USDT": 0.0})
    demo4 = FakeDemoFeed(specs={"SOL-USDT": DEFAULT_SPEC})
    try:
        _freeze("2026-07-23 14:15:00")
        chosen4, _, _ = dp.select_pick([thesis_cand], private4, demo4, state4)
    finally:
        _unfreeze()
    assert chosen4 is None, chosen4
    log4 = state4["daily_pick"]["passed_log"]
    assert len(log4) == 1 and log4[0]["reason"] == "one_thesis", log4

    # -- correlation: opposes the cluster's clean lean -----------------------
    corr_cand = _clean_cand("SOL-USDT", "short", 50.0)
    state5 = make_state()
    private5 = FakePrivate(net_by_symbol={"BTC-USDT": 1.0, "ETH-USDT": 0.0,
                                          "SOL-USDT": 0.0})
    demo5 = FakeDemoFeed(specs={"SOL-USDT": DEFAULT_SPEC})
    try:
        _freeze("2026-07-23 14:15:00")
        chosen5, _, _ = dp.select_pick([corr_cand], private5, demo5, state5)
    finally:
        _unfreeze()
    assert chosen5 is None, chosen5
    log5 = state5["daily_pick"]["passed_log"]
    assert len(log5) == 1 and log5[0]["reason"] == "correlation", log5


# ===========================================================================
# (m) score_passed_trades replays the bracket correctly — hand-verified
#     stop-hit, target-hit, and time-exit cases, plus the age gate
# ===========================================================================

def test_m_score_passed_trades_bracket_outcomes():
    feed = FakeLiveFeed()

    # (A) LONG stop-hit: SOL-USDT ref 100, stop 1.0% (sl 99) target 1.5% (tp 101.5)
    feed.set_candles("SOL-USDT", "1h", _row_candles([
        {"timestamp": pd.Timestamp("2026-07-23 11:00", tz="UTC"),
         "open": 100.0, "high": 100.2, "low": 98.5, "close": 99.0, "volume": 1.0},
    ]))
    # (B) SHORT target-hit: ETH-USDT ref 2000, stop 1.0% (sl 2020) target 1.5% (tp 1970)
    feed.set_candles("ETH-USDT", "1h", _row_candles([
        {"timestamp": pd.Timestamp("2026-07-23 11:00", tz="UTC"),
         "open": 2000.0, "high": 2005.0, "low": 1965.0, "close": 1970.0, "volume": 1.0},
    ]))
    # (C) LONG time-exit: BTC-USDT ref 50000, stop 0.5% (sl 49750) target 0.75% (tp 50375)
    #     — every bar in the window stays inside the band, so it's a clean
    #     4h close-out, not a bracket hit.
    feed.set_candles("BTC-USDT", "1h", _row_candles([
        {"timestamp": pd.Timestamp("2026-07-23 11:00", tz="UTC"),
         "open": 50000.0, "high": 50100.0, "low": 49900.0, "close": 50050.0, "volume": 1.0},
        {"timestamp": pd.Timestamp("2026-07-23 12:00", tz="UTC"),
         "open": 50050.0, "high": 50150.0, "low": 49950.0, "close": 50080.0, "volume": 1.0},
        {"timestamp": pd.Timestamp("2026-07-23 13:00", tz="UTC"),
         "open": 50080.0, "high": 50120.0, "low": 49980.0, "close": 50090.0, "volume": 1.0},
        {"timestamp": pd.Timestamp("2026-07-23 14:00", tz="UTC"),
         "open": 50090.0, "high": 50110.0, "low": 50000.0, "close": 50100.0, "volume": 1.0},
    ]))

    state = make_state()
    state["daily_pick"] = dp._fresh_dp()
    state["daily_pick"]["passed_log"] = [
        _cf_entry("SOL-USDT", "long", 70.0, "calm_gate", 100.0, 1.0, 1.5),
        _cf_entry("ETH-USDT", "short", 30.0, "cooldown", 2000.0, 1.0, 1.5),
        _cf_entry("BTC-USDT", "long", 60.0, "guard", 50000.0, 0.5, 0.75),
        # logged only 1h before "now" below — too young to judge (< MAX_HOLD_H)
        _cf_entry("XAUT-USDT", "long", 50.0, "correlation", 4000.0, 0.5, 0.75,
                  ts="2026-07-23T14:00 UTC"),
    ]

    try:
        _freeze("2026-07-23 15:00:00")   # the first three entries are 5h old
        n_scored = dp.score_passed_trades(feed, state)
    finally:
        _unfreeze()

    assert n_scored == 3, n_scored   # the too-young entry must NOT be counted
    log = state["daily_pick"]["passed_log"]
    by_sym = {e["symbol"]: e for e in log}

    sol = by_sym["SOL-USDT"]
    assert sol["scored"] is True and sol["exit_kind"] == "stop", sol
    assert sol["counterfactual_pnl"] == -22.4, sol   # 0.02*1000*(-1.12/1.0)

    eth = by_sym["ETH-USDT"]
    assert eth["exit_kind"] == "target", eth
    assert eth["counterfactual_pnl"] == 13.8, eth    # 0.01*1000*(1.38/1.0)

    btc = by_sym["BTC-USDT"]
    assert btc["exit_kind"] == "time", btc
    assert btc["counterfactual_pnl"] == 3.2, btc     # 0.02*1000*(0.08/0.5)

    xaut = by_sym["XAUT-USDT"]
    assert xaut["scored"] is False, "too young to judge — must stay unscored"

    board = state["daily_pick"]["gate_scoreboard"]
    assert board["calm_gate"] == {"passed_n": 1, "cf_pnl": -22.4}, board
    assert board["cooldown"] == {"passed_n": 1, "cf_pnl": 13.8}, board
    assert board["guard"] == {"passed_n": 1, "cf_pnl": 3.2}, board
    assert "correlation" not in board, board


# ===========================================================================
# (n) once-scored-never-rescored
# ===========================================================================

def test_n_scored_never_rescored():
    feed = FakeLiveFeed()
    feed.set_candles("SOL-USDT", "1h", _row_candles([
        {"timestamp": pd.Timestamp("2026-07-23 11:00", tz="UTC"),
         "open": 100.0, "high": 100.2, "low": 98.5, "close": 99.0, "volume": 1.0},
    ]))
    state = make_state()
    state["daily_pick"] = dp._fresh_dp()
    state["daily_pick"]["passed_log"] = [
        _cf_entry("SOL-USDT", "long", 70.0, "calm_gate", 100.0, 1.0, 1.5),
    ]
    try:
        _freeze("2026-07-23 15:00:00")
        n1 = dp.score_passed_trades(feed, state)
        first_pnl = state["daily_pick"]["passed_log"][0]["counterfactual_pnl"]
        assert n1 == 1 and first_pnl == -22.4, (n1, first_pnl)
        board_before = dict(state["daily_pick"]["gate_scoreboard"]["calm_gate"])

        # mutate the feed so a re-score (if one happened) would produce a
        # DIFFERENT number entirely — proves the entry is never re-fetched.
        feed.set_candles("SOL-USDT", "1h", _row_candles([
            {"timestamp": pd.Timestamp("2026-07-23 11:00", tz="UTC"),
             "open": 100.0, "high": 200.0, "low": 100.0, "close": 150.0,
             "volume": 1.0},
        ]))
        n2 = dp.score_passed_trades(feed, state)
    finally:
        _unfreeze()

    assert n2 == 0, n2
    assert state["daily_pick"]["passed_log"][0]["counterfactual_pnl"] == -22.4
    assert state["daily_pick"]["gate_scoreboard"]["calm_gate"] == board_before


# ===========================================================================
# (o) passed_log rolling cap — oldest dropped first
# ===========================================================================

def test_o_passed_log_rolling_cap():
    state = make_state()
    cand = {"symbol": "SOL-USDT", "direction": "long", "conviction": 50.0,
           "atr_pct_1h": 1.0, "last_close": 100.0}
    total = dp.PASSED_LOG_CAP + 25
    for i in range(total):
        dp._log_passed_trade(state, cand, "guard", f"slot-{i}")
    log = state["daily_pick"]["passed_log"]
    assert len(log) == dp.PASSED_LOG_CAP, len(log)
    assert log[0]["ts"] == "slot-25", log[0]                    # oldest 25 dropped
    assert log[-1]["ts"] == f"slot-{total - 1}", log[-1]        # newest kept


# ===========================================================================
# (p) the recap's missed-trade lines render from a seeded, already-scored
#     passed_log/gate_scoreboard — and never leak a different day's numbers
# ===========================================================================

def test_p_recap_missed_trade_lines():
    state = make_state()
    dp_state = dp._fresh_dp()
    dp_state["passed_log"] = [
        {"ts": "2026-07-22T10:00 UTC", "symbol": "SOL-USDT", "direction": "long",
         "conviction": 70.0, "reason": "calm_gate", "ref_price": 100.0,
         "stop_pct": 1.0, "target_pct": 1.5, "scored": True,
         "counterfactual_pnl": -22.4, "exit_kind": "stop"},
        {"ts": "2026-07-22T12:00 UTC", "symbol": "ETH-USDT", "direction": "short",
         "conviction": 30.0, "reason": "cooldown", "ref_price": 2000.0,
         "stop_pct": 1.0, "target_pct": 1.5, "scored": True,
         "counterfactual_pnl": 13.8, "exit_kind": "target"},
        {"ts": "2026-07-22T14:00 UTC", "symbol": "BTC-USDT", "direction": "long",
         "conviction": 60.0, "reason": "guard", "ref_price": 50000.0,
         "stop_pct": 0.5, "target_pct": 0.75, "scored": True,
         "counterfactual_pnl": 3.2, "exit_kind": "time"},
        # unscored yesterday entry -> must be ignored entirely
        {"ts": "2026-07-22T18:00 UTC", "symbol": "XAUT-USDT", "direction": "long",
         "conviction": 50.0, "reason": "correlation", "ref_price": 4000.0,
         "stop_pct": 0.5, "target_pct": 0.75, "scored": False},
        # a scored entry from a DIFFERENT day must never leak into the recap
        {"ts": "2026-07-21T10:00 UTC", "symbol": "SOL-USDT", "direction": "long",
         "conviction": 70.0, "reason": "calm_gate", "ref_price": 100.0,
         "stop_pct": 1.0, "target_pct": 1.5, "scored": True,
         "counterfactual_pnl": 999.0, "exit_kind": "target"},
    ]

    msg = dp._build_recap_message(dp_state, state, "2026-07-23")
    assert "Passed 3 trades yesterday" in msg, msg
    assert "gates saved $22.40" in msg, msg       # only SOL's -22.4 is a loss avoided
    assert "cost $17.00" in msg, msg              # ETH 13.8 + BTC 3.2 left on the table
    assert "net $-5.40" in msg, msg               # -22.4 + 13.8 + 3.2 = -5.4
    assert ("Biggest miss: ETH-USDT short (cooldown) would've made $13.80"
           in msg), msg
    assert "999" not in msg, "must never leak a different day's data into the recap"

    # no daybook trades AND no passed_log at all -> the plain "quiet 24h"
    # message, with no missed-trade lines appended.
    empty_dp = dp._fresh_dp()
    quiet_msg = dp._build_recap_message(empty_dp, state, "2026-07-23")
    assert quiet_msg == "Learning engine yesterday: no trades logged (quiet 24h)."


# ===========================================================================
# (q) REGRESSION GUARD: washout must NOT be gated on the chart reader.
#     Round 83 shipped exactly that gate; round 88 attacked it and it did
#     not hold (only 1 of 3 new assets passed, SOL — a symbol this book
#     trades — showed no information content, and across 122 cells the eye
#     was actively harmful nearly as often as it helped). This test exists
#     so the gate cannot quietly come back without someone redoing the work.
# ===========================================================================

def test_q_washout_is_not_eye_gated():
    c1d = _flat_1d(35, 100.0)
    ramp1d = _mk([105 + 5 * i for i in range(20)], freq="1d",
                start=c1d["timestamp"].iloc[-1] + pd.Timedelta(days=1))
    c1d = pd.concat([c1d, ramp1d], ignore_index=True)

    # deep washout + turn candle: RSI3 < 10, 1d uptrend, green turn bar.
    # The real chart reader calls this collapse "messy" (asserted below), so
    # if any eye gate were wired in, washout would go silent here.
    closes = [100] * 10 + [90, 80, 70, 60, 50, 40, 30, 20, 10, 10.5]
    c1h = _mk(closes, freq="1h", volumes=[1000.0] * 20)
    c1h.loc[c1h.index[-1], "open"] = 10.0

    import chart_reader as CR
    assert CR.read_chart(c1h)["quality"] == "messy", \
        "fixture precondition: the real eye must call this tape messy, " \
        "otherwise this test cannot detect a re-added gate"

    sc = dp.score_instrument(c1h, c1d, funding_bps=None)
    names = {c["name"] for c in sc["components"]}
    assert "washout" in names, \
        f"washout must fire on its own rule regardless of the chart read: {sc}"
    assert sc["long_score"] == 25.0, sc      # 20 washout + 5 align bonus
    assert not any("veto" in n or "eye" in n for n in names), \
        f"no eye-gate component may appear in the score: {names}"

    # daily_pick must not even import the chart reader on the live path —
    # it pulls matplotlib's module tree in and buys nothing (round 88).
    assert not hasattr(dp, "chart_reader"), \
        "daily_pick should not import chart_reader; the eye gate was removed"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_a_scoring_components,
        test_b_staleness_skip,
        test_c_btc_guard,
        test_d_already_held_skip,
        test_e_low_conviction_half_risk,
        test_f_slot_idempotency_and_recycling,
        test_g_three_concurrent_cap_and_different_symbols,
        test_h_four_hour_time_exit,
        test_i_reconcile_tp_exit_ledger_and_daybook,
        test_j_daily_recap_trigger,
        test_k_benched_component_stops_firing,
        test_l_passed_log_geometry,
        test_m_score_passed_trades_bracket_outcomes,
        test_n_scored_never_rescored,
        test_o_passed_log_rolling_cap,
        test_p_recap_missed_trade_lines,
        test_q_washout_is_not_eye_gated,
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
