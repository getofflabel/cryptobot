"""
test_blofin_private.py — the clientOrderId tagging + contract-value-read
infrastructure the 2026-07-25 "stop computing what the exchange already
reports" change added.

WHY: Wallace, 2026-07-25 — "any math that you're currently doing in your
system that could be replaced by the API, don't do the math." Two new
pieces of infrastructure exist now and had zero test coverage:

  1. blofin_private.make_client_order_id() / the client_order_id kwarg on
     market_order/post_only_order/place_tpsl — how every book tags its own
     orders so the exchange's own record can tell a bot trade from one
     Wallace placed by hand (verified live against the real BloFin demo
     API on 2026-07-25 — see BLOFIN_API_REFERENCE.md for the empirical
     format facts this file's assertions are built on).
  2. step5_paper_trade.contract_value() — replaces the hardcoded
     CONTRACT_BTC = 0.001 constant (step98_api_audit.md CRITICAL finding
     #1) with a cached read off BloFin's own instruments endpoint.
  3. live_read._merge_exchange_risk() — overlays BloFin's own
     liquidationPrice/marginRatio/unrealizedPnlRatio onto a position card
     (step98_api_audit.md finding #6: this was never displayed anywhere).

No network calls anywhere in this file — every exchange response is a
fake, exactly like the rest of this repo's test suite.
"""

from __future__ import annotations

import sys
import traceback

import blofin_private as bp
import bot_pnl
import live_read as lr
import step5_paper_trade as s5


# ---------------------------------------------------------------------------
# (a) make_client_order_id — format facts verified live 2026-07-25
# ---------------------------------------------------------------------------

def test_a_client_order_id_shape():
    coid = bp.make_client_order_id("dp")
    assert coid.startswith("CBOT_dp_"), coid
    assert len(coid) <= 32, f"BloFin rejects anything over 32 chars: {coid}"
    # BloFin error 152009, verified live: letters, digits, underscores ONLY
    # — no hyphens. Every character here must be alnum or underscore.
    assert all(c.isalnum() or c == "_" for c in coid), coid


def test_b_client_order_id_rejects_bad_tags():
    for bad_tag in ("has-dash", "has space", "way_too_long_a_tag_for_this",
                    "", "semi;colon"):
        try:
            bp.make_client_order_id(bad_tag)
            raise AssertionError(f"should have rejected tag {bad_tag!r}")
        except ValueError:
            pass


def test_c_client_order_id_unique_even_same_millisecond():
    # the in-process counter is the collision guard when the millisecond
    # timestamp alone would tie two calls made back-to-back (entry
    # immediately followed by its own TP/SL bracket, say).
    seen = {bp.make_client_order_id("cr") for _ in range(50)}
    assert len(seen) == 50, "collisions under rapid-fire generation"


def test_d_max_tag_length_stays_under_32_total():
    # BOOK_TAGS's longest real entry ("tce") plus the fixed prefix/millis/
    # counter must never approach the 32-char ceiling — assert the margin
    # explicitly so nobody silently breaks it by lengthening a tag later.
    longest = max(bp.BOOK_TAGS.values(), key=len)
    coid = bp.make_client_order_id(longest)
    assert len(coid) <= 32, (longest, coid)


# ---------------------------------------------------------------------------
# (b) client_order_id actually reaches the request body
# ---------------------------------------------------------------------------

class _FakeSession:
    """Captures the JSON body of every _call() without hitting the network."""
    def __init__(self):
        self.bodies = []

    def request(self, method, url, headers=None, data=None, timeout=None):
        import json
        self.bodies.append(json.loads(data) if data else {})
        class _R:
            headers = {"content-type": "application/json"}
            def json(self_inner):
                return {"code": "0", "data": [{"orderId": "1", "code": "0"}]}
        return _R()


def _fake_client():
    c = bp.BlofinDemoPrivate("k", "s", "p")
    c._session = _FakeSession()
    return c


def test_e_market_order_forwards_client_order_id():
    c = _fake_client()
    coid = bp.make_client_order_id("cr")
    c.market_order("BTC-USDT", "buy", 1.0, client_order_id=coid)
    body = c._session.bodies[-1]
    assert body["clientOrderId"] == coid, body


def test_f_market_order_omits_field_when_not_given():
    c = _fake_client()
    c.market_order("BTC-USDT", "buy", 1.0)
    body = c._session.bodies[-1]
    assert "clientOrderId" not in body, (
        "must not send an empty/None clientOrderId — omit the field "
        "entirely, matching every other optional field's convention here")


def test_g_place_tpsl_forwards_client_order_id():
    c = _fake_client()
    coid = bp.make_client_order_id("gb")
    c.place_tpsl("XAUT-USDT", "sell", 10.0, None, 4000.0,
                 client_order_id=coid)
    body = c._session.bodies[-1]
    assert body["clientOrderId"] == coid, body


def test_h_post_only_order_forwards_client_order_id():
    c = _fake_client()
    coid = bp.make_client_order_id("tc")
    c.post_only_order("BTC-USDT", "buy", 1.0, 65000.0,
                      client_order_id=coid)
    body = c._session.bodies[-1]
    assert body["clientOrderId"] == coid, body


# ---------------------------------------------------------------------------
# (c) contract_value() — step98_api_audit.md CRITICAL finding #1's fix
# ---------------------------------------------------------------------------

class _FakeDemoFeed:
    def __init__(self, specs):
        self.specs = dict(specs)
        self.calls = 0

    def get_instrument(self, symbol):
        self.calls += 1
        if symbol not in self.specs:
            raise RuntimeError(f"no spec for {symbol}")
        return {"contractValue": self.specs[symbol]}


def test_i_contract_value_reads_the_real_spec():
    s5._contract_spec_cache.clear()
    feed = _FakeDemoFeed({"XRP-USDT": "100"})
    v = s5.contract_value(feed, "XRP-USDT")
    assert v == 100.0, v   # NOT 0.001 — the exact CRITICAL bug this fixes


def test_j_contract_value_caches_success():
    s5._contract_spec_cache.clear()
    feed = _FakeDemoFeed({"BTC-USDT": "0.001"})
    v1 = s5.contract_value(feed, "BTC-USDT")
    v2 = s5.contract_value(feed, "BTC-USDT")
    assert v1 == v2 == 0.001
    assert feed.calls == 1, "second call should hit the cache, not the feed"


def test_k_contract_value_failure_is_not_cached():
    s5._contract_spec_cache.clear()
    feed = _FakeDemoFeed({})   # every symbol 404s
    v1 = s5.contract_value(feed, "DOGE-USDT")
    assert v1 is None, "a failed read must return None, never a guess"
    feed.specs["DOGE-USDT"] = "1000"   # now becomes available
    v2 = s5.contract_value(feed, "DOGE-USDT")
    assert v2 == 1000.0, "a prior failure must not be locked in forever"


# ---------------------------------------------------------------------------
# (d) live_read._merge_exchange_risk — step98_api_audit.md finding #6's fix
# ---------------------------------------------------------------------------

class _FakePrivatePositions:
    def __init__(self, rows):
        self.rows = rows

    def positions(self, symbol):
        return self.rows


def test_l_merge_exchange_risk_overlays_real_fields():
    d = {"book": "The Ride", "entry": 65000.0}
    priv = _FakePrivatePositions([{
        "markPrice": "64500.0", "unrealizedPnl": "-10.87",
        "unrealizedPnlRatio": "-0.0533", "liquidationPrice": "58000.0",
        "marginRatio": "3.2", "initialMargin": "204.52",
        "maintenanceMargin": "0.9", "breakEvenPrice": "65010.0",
        "leverage": "20", "marginMode": "isolated",
    }])
    out = lr._merge_exchange_risk(d, priv, "BTC-USDT")
    assert out is d, "must merge into the same dict, not replace it"
    assert out["liquidation_price"] == 58000.0
    assert out["unrealized_pnl_ratio"] == -0.0533
    assert out["margin_ratio"] == 3.2
    assert out["leverage_actual"] == 20.0
    assert out["margin_mode"] == "isolated"
    # the original panel-ready fields must survive untouched
    assert out["book"] == "The Ride" and out["entry"] == 65000.0


def test_m_merge_exchange_risk_degrades_with_no_private():
    d = {"book": "The Gold Book", "entry": 4300.0}
    out = lr._merge_exchange_risk(d, None, "XAUT-USDT")
    assert out is d
    assert "liquidation_price" not in out, (
        "must never invent risk fields when there is no client to ask")


def test_n_merge_exchange_risk_degrades_on_read_failure():
    class _Blows:
        def positions(self, symbol):
            raise RuntimeError("simulated HTML edge-throttle")
    d = {"book": "The Ride", "entry": 65000.0}
    out = lr._merge_exchange_risk(d, _Blows(), "BTC-USDT")
    assert out == {"book": "The Ride", "entry": 65000.0}, (
        "a failed exchange read must never break the existing card")


def test_o_merge_exchange_risk_degrades_on_empty_positions():
    d = {"book": "The Ride", "entry": 65000.0}
    out = lr._merge_exchange_risk(d, _FakePrivatePositions([]), "BTC-USDT")
    assert "liquidation_price" not in out


def test_p_merge_exchange_risk_none_passthrough():
    priv = _FakePrivatePositions([{"markPrice": "1"}])
    assert lr._merge_exchange_risk(None, priv, "BTC-USDT") is None


# ---------------------------------------------------------------------------
# (e) account_balance() / bot_pnl() reads totalEquity instead of hand-adding
#     balance + unrealized
# ---------------------------------------------------------------------------

def test_q_account_balance_hits_the_right_endpoint():
    c = _fake_client()
    c._call = lambda method, path, params=None, body=None: (
        {"totalEquity": "1234.56", "isolatedEquity": "0"}
        if path == "/api/v1/account/balance" else (_ for _ in ()).throw(
            AssertionError(f"wrong path {path}")))
    out = c.account_balance()
    assert out["totalEquity"] == "1234.56"


def test_r_bot_pnl_uses_total_equity_not_hand_sum():
    class _FakeAcct:
        def futures_balance(self):
            return {"balance": "1000.0"}
        def positions(self, symbol):
            return [{"positions": "1", "unrealizedPnl": "999.0"}]
        def account_balance(self):
            # deliberately NOT balance+unrealized (2000.0) so the test
            # fails if bot_pnl() silently falls back to the old hand sum
            return {"totalEquity": "1055.5"}

    orig_cls = bot_pnl.BlofinDemoPrivate
    orig_env = bot_pnl.load_env
    bot_pnl.BlofinDemoPrivate = lambda *a, **k: _FakeAcct()
    bot_pnl.load_env = lambda: {"BLOFIN_DEMO_API_KEY": "k",
                                "BLOFIN_DEMO_API_SECRET": "s",
                                "BLOFIN_DEMO_PASSPHRASE": "p"}
    try:
        r = bot_pnl.bot_pnl()
    finally:
        bot_pnl.BlofinDemoPrivate = orig_cls
        bot_pnl.load_env = orig_env
    assert r["equity_now"] == 1055.5, (
        "must read totalEquity from account_balance(), not hand-sum "
        f"balance+unrealized: got {r['equity_now']}")


def test_s_bot_pnl_falls_back_when_account_balance_fails():
    class _FakeAcctBroken:
        def futures_balance(self):
            return {"balance": "1000.0"}
        def positions(self, symbol):
            return [{"positions": "1", "unrealizedPnl": "50.0"}]
        def account_balance(self):
            raise RuntimeError("simulated outage")

    orig_cls = bot_pnl.BlofinDemoPrivate
    orig_env = bot_pnl.load_env
    bot_pnl.BlofinDemoPrivate = lambda *a, **k: _FakeAcctBroken()
    bot_pnl.load_env = lambda: {"BLOFIN_DEMO_API_KEY": "k",
                                "BLOFIN_DEMO_API_SECRET": "s",
                                "BLOFIN_DEMO_PASSPHRASE": "p"}
    try:
        r = bot_pnl.bot_pnl()
    finally:
        bot_pnl.BlofinDemoPrivate = orig_cls
        bot_pnl.load_env = orig_env
    assert r["equity_now"] == 1050.0, (
        "an account_balance() outage must degrade to the hand sum, "
        f"never crash the report: got {r['equity_now']}")


def test_cloud_env_prefixes_include_every_live_service():
    """A credential prefix missing from load_env's list is invisible in the
    cloud — silently. No error, just a None where a key should be and a bot
    that starts up and does nothing.

    That nearly shipped on 2026-07-25: ALPACA_ was absent while the build
    was being pointed at Alpaca, so correctly-set keys would have read back
    as missing on Monday morning and looked like the strategy standing down.

    This runs the cloud path exactly: no .env file, keys only in os.environ.
    """
    import os
    import blofin_private

    marks = {
        "ALPACA_API_KEY": "sentinel-alpaca-key",
        "ALPACA_API_SECRET": "sentinel-alpaca-secret",
        "TELEGRAM_BOT_TOKEN": "sentinel-telegram",
        "CRYPTOBOT_STATE_SECRET": "sentinel-state",
    }
    saved = {k: os.environ.get(k) for k in marks}
    try:
        os.environ.update(marks)
        env = blofin_private.load_env(path="/nonexistent/.env")
        for key, want in marks.items():
            assert env.get(key) == want, (
                f"{key} is INVISIBLE in the cloud — add its prefix to "
                f"load_env's ENV_PREFIXES")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def main():
    tests = [
        test_cloud_env_prefixes_include_every_live_service,
        test_a_client_order_id_shape,
        test_b_client_order_id_rejects_bad_tags,
        test_c_client_order_id_unique_even_same_millisecond,
        test_d_max_tag_length_stays_under_32_total,
        test_e_market_order_forwards_client_order_id,
        test_f_market_order_omits_field_when_not_given,
        test_g_place_tpsl_forwards_client_order_id,
        test_h_post_only_order_forwards_client_order_id,
        test_i_contract_value_reads_the_real_spec,
        test_j_contract_value_caches_success,
        test_k_contract_value_failure_is_not_cached,
        test_l_merge_exchange_risk_overlays_real_fields,
        test_m_merge_exchange_risk_degrades_with_no_private,
        test_n_merge_exchange_risk_degrades_on_read_failure,
        test_o_merge_exchange_risk_degrades_on_empty_positions,
        test_p_merge_exchange_risk_none_passthrough,
        test_q_account_balance_hits_the_right_endpoint,
        test_r_bot_pnl_uses_total_equity_not_hand_sum,
        test_s_bot_pnl_falls_back_when_account_balance_fails,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception:
            results.append((fn.__name__, False, traceback.format_exc()))
    print("=" * 72)
    print("BLOFIN_PRIVATE / CONTRACT_VALUE / EXCHANGE-RISK TESTS")
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
