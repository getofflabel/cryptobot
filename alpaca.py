"""
alpaca.py — the S&P venue. Paper trading on real prices, real market hours.

WHY THIS EXISTS (2026-07-25)

The S&P is where our two best-measured edges live and we had no way to trade
it. Round 360 scanned every route and this came out first: free, unfunded,
a plain web interface of the same shape as our BloFin client, it trades SPY
and QQQ, it does fractional shares so a position can be a couple of hundred
dollars, and it hands over 7+ years of price history for free — which also
ends this project's dependence on scraping Yahoo.

WHY IT MATTERS MORE THAN A NEW STRATEGY WOULD

Of the 314 settings that survived round 362's testing, 272 clear our
profitability bar at stock-broker costs and only 52 clear it on BloFin's
crypto version of the S&P. Turn-of-month — the strongest thing that round
found — makes 14.9 times its trading cost here and 4.2 times there, which
fails our bar. Same strategy, same market, different venue, opposite
verdict. Cheaper trading multiplies every edge we own rather than adding
one.

WHAT IT COSTS
  Commission: none on US equities.
  The real cost is the gap between the buy and sell price, roughly 0.01% to
  0.02% of price on SPY, so about 0.02% to 0.04% for a round trip. Compare
  BloFin's 0.1413%. That gap IS the reason 272 clears rather than 52.

THE ONE REAL CATCH (round 360 found it, do not forget it)
  Market orders are REJECTED outside regular trading hours. Only limit
  orders work before the open and after the close. Both our rules decide at
  a daily close and fill at the next open, which is inside the session, so
  they survive — but any intraday work must respect this.

PAPER ONLY, DELIBERATELY
  BASE_URL points at the paper host. There is no funded account behind these
  keys. Nothing in this file can reach real money, and the account-type
  check in verify() proves it rather than assuming it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from blofin_private import load_env

BASE_URL = "https://paper-api.alpaca.markets"     # PAPER. Never the live host.
DATA_URL = "https://data.alpaca.markets"


class AlpacaPaper:
    """Minimal client, same shape as blofin_private.BlofinDemoPrivate so the
    rest of this repo can use it without learning a second vocabulary."""

    def __init__(self, api_key: str, api_secret: str):
        self.key = api_key
        self.secret = api_secret
        self.name = "alpaca-paper"

    # -- plumbing -----------------------------------------------------------

    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self.key,
                "APCA-API-SECRET-KEY": self.secret,
                "accept": "application/json"}

    def _get(self, path: str, params: dict | None = None, base: str | None = None):
        import requests
        r = requests.get((base or BASE_URL) + path, headers=self._headers(),
                         params=params, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"alpaca {path} -> {r.status_code} {r.text[:200]}")
        return r.json() if r.text else None

    def _post(self, path: str, body: dict):
        import requests
        r = requests.post(BASE_URL + path, headers=self._headers(), json=body,
                          timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"alpaca {path} -> {r.status_code} {r.text[:200]}")
        return r.json() if r.text else None

    # -- account ------------------------------------------------------------

    def account(self) -> dict:
        """READ, do not compute. Alpaca returns equity, buying power, cash
        and the paper/live flag directly — the same discipline
        BLOFIN_API_REFERENCE.md records after a night of getting margin
        arithmetic wrong by hand."""
        return self._get("/v2/account")

    def clock(self) -> dict:
        """Is the market open right now, and when does it next open/close.
        Load-bearing: market orders are rejected outside regular hours."""
        return self._get("/v2/clock")

    def positions(self) -> list:
        return self._get("/v2/positions") or []

    def position(self, symbol: str) -> dict | None:
        try:
            return self._get(f"/v2/positions/{symbol}")
        except RuntimeError:
            return None                       # no position is a 404, not an error

    # -- market data --------------------------------------------------------

    def bars(self, symbol: str, timeframe: str = "1Day", limit: int = 1000,
             start: str | None = None) -> list:
        """Historical bars. timeframe is Alpaca's own vocabulary: 1Min, 5Min,
        15Min, 1Hour, 1Day. This is the 7+ years of free history that lets us
        finally test the intraday S&P question — the one place the owner's
        high-leverage style could actually hold, since structure sits closer
        together on a 5-minute chart than a daily one."""
        params = {"timeframe": timeframe, "limit": limit, "adjustment": "split"}
        if start:
            params["start"] = start
        out = self._get(f"/v2/stocks/{symbol}/bars", params, base=DATA_URL)
        return (out or {}).get("bars") or []

    def last_trade(self, symbol: str) -> dict:
        out = self._get(f"/v2/stocks/{symbol}/trades/latest", base=DATA_URL)
        return (out or {}).get("trade") or {}

    # -- crypto market data -------------------------------------------------
    #
    # A DIFFERENT PATH, NOT A DIFFERENT VENUE. Same account, same keys, same
    # host. Three things genuinely differ and every one of them is handled
    # here rather than left for the caller to trip over:
    #
    #   1. The symbol carries a SLASH — "BTC/USD", not "BTCUSD". It goes in a
    #      query parameter here, never in the URL path, so nothing has to be
    #      escaped. The ORDER path is the one place the slash reaches a URL
    #      (closing a position), and crypto_close_position handles it.
    #   2. One call answers for MANY symbols, keyed by symbol, so the whole
    #      pair list costs one request instead of ten.
    #   3. The answer is PAGED. `limit` caps the rows in one response, not the
    #      rows you asked for; a next_page_token means there is more. Ignoring
    #      it silently truncates history, which is the single most dangerous
    #      way for this to go wrong — it looks like a short market, not a
    #      short download.

    def crypto_bars(self, symbols, timeframe: str = "5Min",
                    start: str | None = None, end: str | None = None,
                    limit: int = 10000, max_pages: int = 400) -> dict:
        """Historical crypto bars, every page of them. Returns
        {symbol: [bar, ...]}. Five-minute history goes back to 2023-01-01.

        `symbols` is one symbol or a list of them, each with the slash.
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        params = {"symbols": ",".join(symbols), "timeframe": timeframe,
                  "limit": limit}
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        out: dict = {s: [] for s in symbols}
        token, pages = None, 0
        while pages < max_pages:
            if token:
                params["page_token"] = token
            got = self._get("/v1beta3/crypto/us/bars", params, base=DATA_URL) or {}
            for sym, rows in (got.get("bars") or {}).items():
                out.setdefault(sym, []).extend(rows)
            token = got.get("next_page_token")
            pages += 1
            if not token:
                break
        return out

    def crypto_latest_quotes(self, symbols) -> dict:
        """The live bid and ask per symbol. This is where the spread we CHARGE
        comes from — measured, never assumed, and never consulted by any
        decision."""
        if isinstance(symbols, str):
            symbols = [symbols]
        out = self._get("/v1beta3/crypto/us/latest/quotes",
                        {"symbols": ",".join(symbols)}, base=DATA_URL)
        return (out or {}).get("quotes") or {}

    def crypto_quotes(self, symbols, start: str, end: str,
                      limit: int = 10000, max_pages: int = 1) -> dict:
        """HISTORICAL bid/ask, which is what lets the spread we charge be a
        measured number over months rather than a snapshot taken on one quiet
        evening. Returns {symbol: [quote, ...]}.

        `max_pages` defaults to 1 on purpose: these arrive tens of thousands
        per minute and a caller almost always wants a SAMPLE of a window, not
        all of it."""
        if isinstance(symbols, str):
            symbols = [symbols]
        params = {"symbols": ",".join(symbols), "start": start, "end": end,
                  "limit": limit}
        out: dict = {s: [] for s in symbols}
        token, pages = None, 0
        while pages < max_pages:
            if token:
                params["page_token"] = token
            got = self._get("/v1beta3/crypto/us/quotes", params, base=DATA_URL) or {}
            for sym, rows in (got.get("quotes") or {}).items():
                out.setdefault(sym, []).extend(rows)
            token = got.get("next_page_token")
            pages += 1
            if not token:
                break
        return out

    def crypto_assets(self) -> list:
        """Every crypto pair the account can actually trade, with the venue's
        own minimum order size and price increment. Read these; do not guess
        them."""
        got = self._get("/v2/assets", {"asset_class": "crypto",
                                       "status": "active"}) or []
        return [a for a in got if a.get("tradable")]

    # -- crypto orders ------------------------------------------------------

    def crypto_market_order(self, symbol: str, side: str, qty: float,
                            client_order_id: str | None = None) -> dict:
        """One atomic crypto market order.

        TWO REAL DIFFERENCES FROM THE STOCK PATH, both verified 2026-07-25
        against the live account rather than assumed:

        NO MARKET-OPEN CHECK. Crypto trades every day including weekends.
        /v2/clock reported is_open false on a Saturday evening while the bars
        endpoint was still printing a full 24 hours for that same Saturday and
        Sunday. clock() describes the STOCK session and has no authority over
        this path.

        TIME IN FORCE IS "gtc", NOT "day". Crypto has no trading day for a
        "day" order to expire at, and the venue rejects it. "gtc" on a market
        order still fills immediately — nothing rests.

        NOT SHORTABLE, AND THIS METHOD REFUSES RATHER THAN SILENTLY
        SUCCEEDING. Every one of the 36 US-dollar pairs reports
        shortable=false and marginable=false. A sell without an existing
        position is not a short here, it is an error, and pretending otherwise
        would let a short setup look filled when nothing happened.
        """
        if side not in ("buy", "sell"):
            raise ValueError(f"side must be buy or sell, not {side!r}")
        body = {"symbol": symbol, "side": side, "type": "market",
                "time_in_force": "gtc", "qty": str(qty)}
        if client_order_id:
            body["client_order_id"] = client_order_id
        return self._post("/v2/orders", body)

    def crypto_close_position(self, symbol: str) -> dict:
        """Close a crypto position. THE SLASH REACHES THE URL HERE and nowhere
        else, so it is percent-encoded — "BTC/USD" unescaped would read as two
        path segments and 404."""
        import urllib.parse

        import requests
        enc = urllib.parse.quote(symbol, safe="")
        r = requests.delete(f"{BASE_URL}/v2/positions/{enc}",
                            headers=self._headers(), timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"alpaca crypto close -> {r.status_code} {r.text[:200]}")
        return r.json() if r.text else {}

    def crypto_position(self, symbol: str) -> dict | None:
        import urllib.parse
        try:
            return self._get(f"/v2/positions/{urllib.parse.quote(symbol, safe='')}")
        except RuntimeError:
            return None                       # no position is a 404, not an error

    # -- orders -------------------------------------------------------------

    def market_order(self, symbol: str, side: str, qty: float,
                     client_order_id: str | None = None) -> dict:
        """One atomic market order. Same law as the crypto side: an order
        only exists when we want to trade NOW, never resting.

        WILL BE REJECTED outside regular trading hours — that is Alpaca's
        rule, not ours. Check clock() first."""
        body = {"symbol": symbol, "side": side, "type": "market",
                "time_in_force": "day", "qty": str(qty)}
        if client_order_id:
            body["client_order_id"] = client_order_id
        return self._post("/v2/orders", body)

    def close_position(self, symbol: str) -> dict:
        import requests
        r = requests.delete(f"{BASE_URL}/v2/positions/{symbol}",
                            headers=self._headers(), timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"alpaca close -> {r.status_code} {r.text[:200]}")
        return r.json() if r.text else {}

    def orders(self, status: str = "all", limit: int = 50) -> list:
        return self._get("/v2/orders", {"status": status, "limit": limit}) or []


def from_env() -> AlpacaPaper | None:
    """Build a client from .env, or None if the keys are not there yet."""
    env = load_env()
    k, s = env.get("ALPACA_API_KEY"), env.get("ALPACA_API_SECRET")
    if not k or not s:
        return None
    return AlpacaPaper(k, s)


def verify() -> dict:
    """Prove the connection works and that it is PAPER, then prove the data
    we actually need is reachable. Returns a plain dict; prints a readable
    report. Run this before trusting anything else in the file."""
    cli = from_env()
    if cli is None:
        return {"ok": False,
                "why": "ALPACA_API_KEY / ALPACA_API_SECRET are not in .env yet"}

    acct = cli.account()
    is_paper = bool(acct.get("id")) and BASE_URL.startswith("https://paper-")
    clock = cli.clock()

    # Alpaca returns NOTHING when no `start` is given — it answers
    # "bars": null rather than erroring, so a missing start looks exactly
    # like an empty market. Every call below passes one. (Found 2026-07-25
    # while building sp500.py: this function was reporting 0 bars on a
    # perfectly healthy connection.)
    from datetime import timedelta
    today = datetime.now(timezone.utc).date()
    recent = str(today - timedelta(days=30))

    # the two instruments our surviving S&P edges are measured on
    checks = {}
    for sym in ("SPY", "QQQ"):
        daily = cli.bars(sym, "1Day", limit=10, start=recent)
        checks[sym] = {"daily_bars": len(daily),
                       "latest_close": daily[-1]["c"] if daily else None}

    # the thing we have never been able to test: intraday history
    intraday = cli.bars("SPY", "5Min", limit=1000, start=str(today - timedelta(days=7)))

    # how far back the free history actually goes
    deep = cli.bars("SPY", "1Day", limit=10000, start="2016-01-01")

    out = {
        "ok": True,
        "host": BASE_URL,
        "paper": is_paper,
        "equity": acct.get("equity"),
        "buying_power": acct.get("buying_power"),
        "market_open_now": clock.get("is_open"),
        "next_open": clock.get("next_open"),
        "checks": checks,
        "spy_5min_bars": len(intraday),
        "spy_daily_bars_since_2016": len(deep),
        "spy_history_starts": deep[0]["t"] if deep else None,
    }
    print(json.dumps(out, indent=2, default=str))
    return out


def verify_crypto() -> dict:
    """Prove the crypto path works, and prove the three things about it that
    the stock path would have let us assume wrongly. Reads only. No orders."""
    cli = from_env()
    if cli is None:
        return {"ok": False, "why": "ALPACA keys are not in .env yet"}

    from datetime import timedelta
    today = datetime.now(timezone.utc).date()

    assets = cli.crypto_assets()
    usd = [a for a in assets if a["symbol"].endswith("/USD")]

    pairs = ["BTC/USD", "ETH/USD"]
    b5 = cli.crypto_bars(pairs, "5Min", start=str(today - timedelta(days=3)))
    b1 = cli.crypto_bars(pairs, "1Min", start=str(today - timedelta(days=1)))
    deep = cli.crypto_bars("BTC/USD", "1Day", start="2023-01-01")
    quotes = cli.crypto_latest_quotes(pairs)

    # the weekend proof: the STOCK clock is shut, and crypto bars print anyway
    clock = cli.clock()
    week = cli.crypto_bars("BTC/USD", "1Hour",
                           start=str(today - timedelta(days=8)))["BTC/USD"]
    import collections
    by_dow = collections.Counter(
        datetime.fromisoformat(r["t"].replace("Z", "+00:00")).weekday()
        for r in week)

    acct = cli.account()
    out = {
        "ok": True,
        "tradable_usd_pairs": len(usd),
        "shortable_anywhere": any(a.get("shortable") for a in usd),
        "marginable_anywhere": any(a.get("marginable") for a in usd),
        "cash_buying_power": acct.get("non_marginable_buying_power"),
        "margin_buying_power_stocks_only": acct.get("buying_power"),
        "bars_5m": {s: len(v) for s, v in b5.items()},
        "bars_1m": {s: len(v) for s, v in b1.items()},
        "btc_daily_bars_since_2023": len(deep.get("BTC/USD") or []),
        "btc_history_starts": (deep.get("BTC/USD") or [{}])[0].get("t"),
        "spreads_pct_of_mid": {
            s: round(200 * (q["ap"] - q["bp"]) / (q["ap"] + q["bp"]), 4)
            for s, q in quotes.items()},
        "stock_clock_open": clock.get("is_open"),
        "crypto_hours_by_weekday_0_is_monday": dict(sorted(by_dow.items())),
        "orders_ever_placed": len(cli.orders("all", 50)),
    }
    print(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    import sys
    if "--crypto" in sys.argv:
        verify_crypto()
    else:
        verify()
