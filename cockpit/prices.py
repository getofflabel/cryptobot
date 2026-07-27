"""
cockpit/prices.py — the live price, and how old it is, and where it came
from. All three, always, or none of them.

THE ONE FAILURE THIS FILE EXISTS TO PREVENT
    A stale price shown as if it were live. Everything else here is detail.

    So every quote that leaves this file carries the exchange's OWN
    timestamp — never the moment we happened to fetch it — and the panel
    counts the age from that. A price we cannot date is not returned as a
    price; it is returned as an error with the reason in words.

WHERE EACH MARKET'S PRICE COMES FROM, AND WHY IT IS LABELLED ON SCREEN
    crypto        Alpaca's crypto quote endpoint. Live, around a second
                  old in practice, twenty-four hours a day.
    US stocks     Alpaca, IEX ONLY. Our data plan does not include the
                  consolidated feed — asking for it answers 403, in so many
                  words: "subscription does not permit querying recent SIP
                  data". IEX is one exchange out of many, so its last trade
                  is a real trade but it is not the whole market's price.
                  That sentence goes ON THE PANEL, next to the number. The
                  panel also shows TradingView's own on-screen price beside
                  it, because his eyes are on that one and the two differing
                  is information, not an error to hide.
    currencies    Yahoo's 1-minute bar, which is the same feed tjr_forex
                  already trades off, so the cockpit and the bot cannot
                  disagree about what a pound is worth.

    There is no fourth source and no silent fallback between them. If the
    one source for a market is down, that market has no price and the panel
    says so.
"""

from __future__ import annotations

import datetime as dt
import re
import time

# ------------------------------------------------- what he is looking at
#
# TradingView writes a symbol as EXCHANGE:TICKER — "BINANCE:BTCUSDT",
# "AMEX:SPY", "OANDA:GBPUSD". The bot writes the same instruments as
# "BTC/USD", "SPY", "GBP/USD". This is the whole translation, kept in one
# place so the panel and the alert can never end up talking about different
# instruments.

CRYPTO_BASES = ("BTC", "ETH", "SOL", "XRP", "DOGE", "LINK", "AVAX", "LTC",
                "ADA", "DOT")
STOCKS = ("SPY", "QQQ", "GLD", "IAU")
FX = {"GBPUSD": "GBP/USD", "GBPJPY": "GBP/JPY"}

# What Yahoo calls a currency pair.
YAHOO_FX = {"GBP/USD": "GBPUSD=X", "GBP/JPY": "GBPJPY=X"}


def read_symbol(tv_symbol: str) -> dict:
    """Turn what is on his screen into what the bot calls it.

    Answers `{"kind", "symbol"}` where kind is crypto / stock / currencies,
    or `{"kind": "unknown"}`. Unknown is a real answer and the panel prints
    it — the cockpit watches four markets and he may well have a fifth chart
    open, and pretending we know that price would be the lie this file is
    built to avoid.
    """
    raw = (tv_symbol or "").strip().upper()
    ticker = raw.split(":")[-1]
    ticker = re.sub(r"[^A-Z0-9./]", "", ticker)

    if "/" in ticker:                              # already BTC/USD shaped
        base, _, quote = ticker.partition("/")
        if base in CRYPTO_BASES:
            return {"kind": "crypto", "symbol": f"{base}/USD"}
        if f"{base}{quote}" in FX:
            return {"kind": "currencies", "symbol": FX[f"{base}{quote}"]}
        return {"kind": "unknown", "symbol": ticker}

    if ticker in FX:
        return {"kind": "currencies", "symbol": FX[ticker]}
    if ticker in STOCKS:
        return {"kind": "stock", "symbol": ticker}

    for base in CRYPTO_BASES:
        # BTCUSDT on Binance, BTCUSD on Coinbase, BTCUSDC — the bot prices
        # all of them off its own BTC/USD, and the difference between a
        # dollar and a dollar-stablecoin is smaller than the spread he is
        # trading through. It is still a different instrument, which the
        # panel says next to the price.
        if ticker.startswith(base) and ticker[len(base):] in ("USD", "USDT",
                                                              "USDC", "PERP",
                                                              "USDTPERP", ""):
            return {"kind": "crypto", "symbol": f"{base}/USD",
                    "as_shown": ticker}
    return {"kind": "unknown", "symbol": ticker or "(no symbol on screen)"}


# ------------------------------------------------------------- the quotes
_cache: dict = {}
_CACHE_SECONDS = 1.5          # one call a second from the panel must not
                              # become one call a second to the exchange


def _cached(key, fn):
    hit = _cache.get(key)
    if hit and (time.time() - hit[0]) < _CACHE_SECONDS:
        return hit[1]
    out = fn()
    _cache[key] = (time.time(), out)
    return out


def _epoch(iso: str) -> float | None:
    """Alpaca's RFC3339 with nanoseconds, which datetime will not parse as
    given. Trimmed to microseconds rather than guessed at."""
    if not iso:
        return None
    s = iso.replace("Z", "+00:00")
    m = re.match(r"(.*\.\d{1,6})\d*(\+\d\d:\d\d)$", s)
    if m:
        s = m.group(1) + m.group(2)
    try:
        return dt.datetime.fromisoformat(s).timestamp()
    except ValueError:
        return None


def _client():
    import alpaca
    return alpaca.from_env()


def crypto_quote(symbol: str) -> dict:
    def go():
        cli = _client()
        if cli is None:
            return {"ok": False,
                    "why": "the Alpaca keys are not in .env, so there is no "
                           "live crypto price here"}
        try:
            got = cli.crypto_latest_quotes([symbol]).get(symbol)
        except Exception as e:
            return {"ok": False, "why": f"Alpaca did not answer: {str(e)[:120]}"}
        if not got:
            return {"ok": False,
                    "why": f"Alpaca has no live quote for {symbol}"}
        bid, ask = got.get("bp"), got.get("ap")
        at = _epoch(got.get("t"))
        if not bid or not ask or at is None:
            return {"ok": False,
                    "why": "Alpaca answered without a price or without a time "
                           "on it, so its age cannot be known"}
        return {"ok": True, "price": (float(bid) + float(ask)) / 2.0,
                "bid": float(bid), "ask": float(ask), "as_of": at,
                "source": "Alpaca crypto quote",
                "source_note": "the midpoint between the live bid and ask"}
    return _cached(("crypto", symbol), go)


def stock_quote(symbol: str) -> dict:
    """IEX only, and it says so.

    Our plan is refused the consolidated feed outright — the request comes
    back 403 rather than empty — so this is one exchange's last trade, not
    the price of the whole market. Overnight and at weekends it is also the
    last trade before the close, which can be many hours old; the age says
    exactly how many and the panel greys it.
    """
    def go():
        cli = _client()
        if cli is None:
            return {"ok": False,
                    "why": "the Alpaca keys are not in .env, so there is no "
                           "live stock price here"}
        try:
            got = (cli._get(f"/v2/stocks/{symbol}/trades/latest",
                            {"feed": "iex"},
                            base=__import__("alpaca").DATA_URL) or {})
        except Exception as e:
            return {"ok": False, "why": f"Alpaca did not answer: {str(e)[:120]}"}
        tr = got.get("trade") or {}
        at = _epoch(tr.get("t"))
        if not tr.get("p") or at is None:
            return {"ok": False,
                    "why": f"Alpaca returned no dated trade for {symbol}"}
        return {"ok": True, "price": float(tr["p"]), "as_of": at,
                "source": "Alpaca, IEX only",
                "source_note": ("the last trade on IEX alone. Our data plan is "
                                "refused the combined feed of every exchange, "
                                "so this is one exchange's price, not the "
                                "market's")}
    return _cached(("stock", symbol), go)


def currency_quote(symbol: str) -> dict:
    """Yahoo's most recent 1-minute bar — the same feed tjr_forex trades on."""
    def go():
        import requests
        y = YAHOO_FX.get(symbol)
        if not y:
            return {"ok": False, "why": f"no currency feed wired up for {symbol}"}
        try:
            r = requests.get(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{y}",
                params={"interval": "1m", "range": "1d"},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            res = (r.json().get("chart") or {}).get("result") or []
        except Exception as e:
            return {"ok": False, "why": f"Yahoo did not answer: {str(e)[:120]}"}
        if not res:
            return {"ok": False, "why": f"Yahoo returned no bars for {symbol}"}
        j = res[0]
        stamps = j.get("timestamp") or []
        closes = (j["indicators"]["quote"][0] or {}).get("close") or []
        for i in range(len(stamps) - 1, -1, -1):
            if i < len(closes) and closes[i] is not None:
                # the bar's timestamp is when it STARTED; it is a minute bar,
                # so its close is up to a minute later than that. Dating it
                # from the start would flatter the age, which is the one
                # direction this file is not allowed to err in.
                return {"ok": True, "price": float(closes[i]),
                        "as_of": float(stamps[i]) + 60.0,
                        "source": "Yahoo 1-minute bar",
                        "source_note": ("the close of the last finished "
                                        "1-minute bar, the same feed the bot "
                                        "trades currencies on")}
        return {"ok": False, "why": f"Yahoo's bars for {symbol} were all empty"}
    return _cached(("fx", symbol), go)


def quote(tv_symbol: str) -> dict:
    """One entry point. Always answers; never guesses."""
    read = read_symbol(tv_symbol)
    kind, sym = read["kind"], read["symbol"]
    if kind == "crypto":
        q = crypto_quote(sym)
    elif kind == "stock":
        q = stock_quote(sym)
    elif kind == "currencies":
        q = currency_quote(sym)
    else:
        q = {"ok": False,
             "why": (f"{sym} is not one of the instruments this bot watches, "
                     f"so there is no price for it here")}
    out = dict(read)
    out["quote"] = q
    if q.get("ok"):
        out["quote"]["age_seconds"] = time.time() - q["as_of"]
    return out
