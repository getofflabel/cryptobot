"""
exchange.py — the ONLY file that knows how a specific exchange talks.

Why this file exists:
Everything else in this project (backtester, strategy, live trader) talks to
the small, boring interface defined here. If you want to swap exchanges, you
write one new class in this file and nothing else in the project changes.

That is not a theoretical benefit. It already paid for itself: we built this
project against BloFin, then BloFin geo-blocked us mid-session. Swapping to
Bybit cost one class, not a rewrite. That is why we did it this way.

Python concepts used here, briefly:
  - @dataclass            : a class whose only job is to hold data. Python
                            writes __init__ and __repr__ for you.
  - ABC / abstractmethod  : an "abstract base class", a contract. It says
                            "every exchange MUST have these methods" and
                            refuses to be instantiated directly.
  - type hints (-> float) : notes for humans and editors, not enforced at
                            runtime.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd
import requests


# ---------------------------------------------------------------------------
# Canonical vocabulary
# ---------------------------------------------------------------------------
# Every exchange invents its own name for "one hour" ("1H", "60", "1h", "3600").
# The rest of our code should never have to care. We define OUR names here and
# each adapter translates. This is the heart of staying exchange-agnostic.

TIMEFRAME_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "2h": 7_200_000,
    "4h": 14_400_000,
    "6h": 21_600_000,
    "12h": 43_200_000,
    "1d": 86_400_000,
    "1w": 604_800_000,
}


# ---------------------------------------------------------------------------
# The shapes of data we pass around
# ---------------------------------------------------------------------------


@dataclass
class Ticker:
    """A snapshot of the market right now.

    `bid` is the best price someone will BUY from you at.
    `ask` is the best price someone will SELL to you at.
    `ask` is always >= `bid`. The gap between them is the SPREAD, and it is a
    real cost you pay on every round trip. We capture it here so Step 2 can
    charge us for it.
    """

    symbol: str
    last: float
    bid: float
    ask: float
    timestamp: datetime

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    @property
    def spread(self) -> float:
        """Absolute spread in quote currency (e.g. dollars)."""
        return self.ask - self.bid

    @property
    def spread_bps(self) -> float:
        """Spread in basis points (1 bp = 0.01%).

        bps is how professionals quote trading costs, because it is comparable
        across assets. A $0.10 spread on $65,000 BTC is nothing; the same
        $0.10 on a $2 altcoin is enormous. bps captures that automatically.
        """
        if self.mid <= 0:
            return 0.0
        return (self.spread / self.mid) * 10_000


class _TransientBlock(Exception):
    """A failure we expect to clear on its own, so it is worth retrying.

    Covers rate limits, 5xx errors, and the HTML interstitial an exchange
    edge serves when it is throttling a region.
    """


class Exchange(ABC):
    """The contract every exchange adapter must satisfy.

    Deliberately tiny. Right now we only READ the market. Order placement
    arrives in Step 5, not before.
    """

    name: str = "unknown"

    # Published fee rates in basis points, so the backtester can charge us
    # the REAL numbers instead of a guess. Overridden per exchange.
    TAKER_FEE_BPS: float = 0.0
    MAKER_FEE_BPS: float = 0.0

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """Current best bid/ask/last for one symbol."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str = "1h",
                    limit: int = 300, end_ms: int | None = None) -> pd.DataFrame:
        """Historical OHLCV bars, OLDEST FIRST, closed bars only.

        Returns a DataFrame with columns:
            timestamp (UTC tz-aware), open, high, low, close, volume

        end_ms: fetch bars ending at this millisecond timestamp. This is what
                lets us paginate backwards through years of history.
        """


# ---------------------------------------------------------------------------
# Shared HTTP plumbing
# ---------------------------------------------------------------------------


class _RestExchange(Exchange):
    """Common request/retry logic. Both adapters below inherit from this."""

    def __init__(self, timeout: int = 45, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        # A Session reuses the TCP connection between calls, which makes
        # repeated requests noticeably faster than bare requests.get().
        self._session = requests.Session()

    def _request(self, url: str, params: dict | None = None) -> dict:
        """GET with retries on TRANSIENT failures.

        What counts as transient, and why:

          - timeouts / dropped connections
                Ordinary network flakiness.

          - HTTP 429 and 5xx
                Rate limiting and server-side problems. Both clear on their own.

          - an HTML page instead of JSON
                This is BloFin's "restricted region" interstitial. We assumed
                it was a permanent geo-ban and it was not: it appeared for a
                stretch, then cleared, and the very same requests went through
                at 10/10. It is an edge-level throttle that rotates. So we
                treat it as transient and retry rather than giving up.

        We never retry genuine API errors. If the exchange says "unknown
        symbol", asking three more times will not change its mind.

        Backoff is exponential (1s, 2s, 4s, ...) so we do not hammer a
        struggling server and get ourselves throttled harder than we started.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                r = self._session.get(url, params=params, timeout=self.timeout)

                ctype = r.headers.get("content-type", "")
                if "html" in ctype.lower():
                    raise _TransientBlock(
                        f"{self.name}: got an HTML interstitial instead of data. "
                        f"Usually a regional/edge throttle. Retrying."
                    )

                if r.status_code == 429 or r.status_code >= 500:
                    raise _TransientBlock(
                        f"{self.name}: HTTP {r.status_code} from {url}"
                    )

                r.raise_for_status()
                return r.json()

            except (requests.Timeout, requests.ConnectionError, _TransientBlock) as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    print(f"    [{self.name}] transient failure, retrying in {wait}s "
                          f"(attempt {attempt + 2}/{self.max_retries}): "
                          f"{type(e).__name__}")
                    time.sleep(wait)

        raise RuntimeError(
            f"{self.name}: request failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    @staticmethod
    def _to_dataframe(rows: list[dict]) -> pd.DataFrame:
        """Build the standard OHLCV frame, oldest first."""
        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
        return df.sort_values("timestamp").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Bybit  (our primary exchange)
# ---------------------------------------------------------------------------


class BybitExchange(_RestExchange):
    """Bybit V5 API adapter for USDT perpetual futures.

    Three environments, all reachable:
      mainnet  api.bybit.com          real market data, no API key needed
      testnet  api-testnet.bybit.com  fake money, free API keys
      demo     api-demo.bybit.com     fake money on real mainnet prices

    Why Bybit: it is one of the few major venues that is not blocking us, it
    offers hourly history back to March 2020, and its testnet mirrors the real
    API exactly, so Step 5 code will look almost identical to live code.
    """

    MAINNET_URL = "https://api.bybit.com"
    TESTNET_URL = "https://api-testnet.bybit.com"
    DEMO_URL = "https://api-demo.bybit.com"

    # Published standard (non-VIP) rates for USDT perpetuals, in basis points.
    TAKER_FEE_BPS = 5.5    # 0.055% — market orders always pay this
    MAKER_FEE_BPS = 2.0    # 0.020% — resting limit orders that get filled

    MAX_CANDLES_PER_REQUEST = 1000

    # Our canonical timeframe -> Bybit's interval code
    _INTERVALS = {
        "1m": "1", "3m": "3", "5m": "5", "15m": "15", "30m": "30",
        "1h": "60", "2h": "120", "4h": "240", "6h": "360", "12h": "720",
        "1d": "D", "1w": "W",
    }

    def __init__(self, env: str = "mainnet", category: str = "linear", **kwargs):
        """
        env='mainnet'  -> real prices. Use this for backtest data.
        env='testnet'  -> sandbox. Use this for paper trading in Step 5.
        env='demo'     -> Bybit's demo account on real prices.

        category='linear' means USDT-margined perpetual futures, which is the
        same instrument type BloFin offered. 'spot' also works.
        """
        super().__init__(**kwargs)
        urls = {"mainnet": self.MAINNET_URL,
                "testnet": self.TESTNET_URL,
                "demo": self.DEMO_URL}
        if env not in urls:
            raise ValueError(f"env must be one of {list(urls)}, got {env!r}")
        self.env = env
        self.base_url = urls[env]
        self.category = category
        self.name = f"bybit-{env}"

    def _get(self, path: str, params: dict) -> dict:
        """Unwrap Bybit's response envelope.

        Bybit replies look like:
            {"retCode": 0, "retMsg": "OK", "result": {...}}
        retCode 0 means success. Anything else we raise on loudly, because a
        silently-empty result in a trading system is indistinguishable from
        "no trading signal" — and that means your bot sits idle while you
        assume it is working.
        """
        payload = self._request(f"{self.base_url}{path}", params)
        if payload.get("retCode") != 0:
            raise RuntimeError(
                f"{self.name} API error on {path}: "
                f"retCode={payload.get('retCode')} retMsg={payload.get('retMsg')}"
            )
        return payload.get("result", {})

    def get_ticker(self, symbol: str = "BTCUSDT") -> Ticker:
        result = self._get("/v5/market/tickers",
                           {"category": self.category, "symbol": symbol})
        rows = result.get("list", [])
        if not rows:
            raise RuntimeError(f"No ticker returned for {symbol}")
        row = rows[0]
        return Ticker(
            symbol=row["symbol"],
            last=float(row["lastPrice"]),
            bid=float(row["bid1Price"]),
            ask=float(row["ask1Price"]),
            timestamp=datetime.now(timezone.utc),
        )

    def get_candles(self, symbol: str = "BTCUSDT", timeframe: str = "1h",
                    limit: int = 300, end_ms: int | None = None) -> pd.DataFrame:
        if timeframe not in self._INTERVALS:
            raise ValueError(
                f"{timeframe!r} is not supported. Pick one of: "
                f"{', '.join(self._INTERVALS)}"
            )
        limit = min(limit, self.MAX_CANDLES_PER_REQUEST)

        params = {
            "category": self.category,
            "symbol": symbol,
            "interval": self._INTERVALS[timeframe],
            "limit": limit,
        }
        if end_ms is not None:
            params["end"] = int(end_ms)

        result = self._get("/v5/market/kline", params)

        # Bybit rows are flat lists of strings:
        #   [startTime, open, high, low, close, volume, turnover]
        #
        # Unlike BloFin there is NO "is this bar closed" flag, so we work it
        # out ourselves. The newest bar is usually still forming: its high,
        # low and close keep changing as price moves. Acting on a forming bar
        # is a classic beginner bug, because a signal can appear and then
        # vanish before the bar ends. We drop any bar that has not fully
        # elapsed.
        bar_ms = TIMEFRAME_MS[timeframe]
        now_ms = int(time.time() * 1000)

        rows = []
        for c in result.get("list", []):
            start = int(c[0])
            if start + bar_ms > now_ms:
                continue                       # still forming, not tradeable yet
            rows.append({
                "timestamp": datetime.fromtimestamp(start / 1000, tz=timezone.utc),
                "open":   float(c[1]),
                "high":   float(c[2]),
                "low":    float(c[3]),
                "close":  float(c[4]),
                "volume": float(c[5]),
            })

        return self._to_dataframe(rows)

    def get_instrument(self, symbol: str = "BTCUSDT") -> dict:
        """Contract specs: tick size, minimum order size, leverage limits.

        We need this in Step 5. You cannot order 0.00037 BTC when the minimum
        step is 0.001, and an order that violates the spec is simply rejected.
        """
        result = self._get("/v5/market/instruments-info",
                           {"category": self.category, "symbol": symbol})
        rows = result.get("list", [])
        if not rows:
            raise RuntimeError(f"No instrument info for {symbol}")
        return rows[0]


# ---------------------------------------------------------------------------
# BloFin  (kept as proof the abstraction works — currently geo-blocked for us)
# ---------------------------------------------------------------------------


class BlofinExchange(_RestExchange):
    """BloFin adapter.

    STATUS: BloFin geo-blocks our IP. Every endpoint, including public market
    data, returns an HTML "restricted region" page. It worked for about
    twenty minutes and then cut us off.

    We are keeping this class for two reasons:
      1. If you ever access BloFin from an allowed region, it just works.
      2. It is a second, working implementation of the same Exchange contract,
         which is the clearest possible proof that the abstraction is real
         and not decorative.
    """

    PROD_URL = "https://openapi.blofin.com"
    DEMO_URL = "https://demo-trading-openapi.blofin.com"

    TAKER_FEE_BPS = 6.0    # 0.060%
    MAKER_FEE_BPS = 2.0    # 0.020%

    MAX_CANDLES_PER_REQUEST = 1440

    _INTERVALS = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1H", "2h": "2H", "4h": "4H", "6h": "6H", "12h": "12H",
        "1d": "1D", "1w": "1W",
    }

    def __init__(self, demo: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.demo = demo
        self.base_url = self.DEMO_URL if demo else self.PROD_URL
        self.name = f"blofin-{'demo' if demo else 'prod'}"

    def _get(self, path: str, params: dict | None = None) -> list:
        payload = self._request(f"{self.base_url}{path}", params)
        if payload.get("code") != "0":
            raise RuntimeError(
                f"{self.name} API error on {path}: "
                f"code={payload.get('code')} msg={payload.get('msg')}"
            )
        return payload["data"]

    def get_ticker(self, symbol: str = "BTC-USDT") -> Ticker:
        data = self._get("/api/v1/market/tickers", {"instId": symbol})
        if not data:
            raise RuntimeError(f"No ticker returned for {symbol}")
        row = data[0]
        return Ticker(
            symbol=row["instId"],
            last=float(row["last"]),
            bid=float(row["bidPrice"]),
            ask=float(row["askPrice"]),
            timestamp=datetime.fromtimestamp(int(row["ts"]) / 1000, tz=timezone.utc),
        )

    def get_candles(self, symbol: str = "BTC-USDT", timeframe: str = "1h",
                    limit: int = 300, end_ms: int | None = None) -> pd.DataFrame:
        if timeframe not in self._INTERVALS:
            raise ValueError(f"{timeframe!r} not supported by {self.name}")

        params = {
            "instId": symbol,
            "bar": self._INTERVALS[timeframe],
            "limit": min(limit, self.MAX_CANDLES_PER_REQUEST),
        }
        if end_ms is not None:
            # BloFin's "after" means "bars before this timestamp".
            # Confusing, but that is what it does. We verified it empirically.
            params["after"] = int(end_ms)

        data = self._get("/api/v1/market/candles", params)

        # BloFin DOES give us a confirmed flag (index 8), so we use it.
        rows = []
        for c in data:
            if c[8] != "1":
                continue
            rows.append({
                "timestamp": datetime.fromtimestamp(int(c[0]) / 1000, tz=timezone.utc),
                "open":   float(c[1]),
                "high":   float(c[2]),
                "low":    float(c[3]),
                "close":  float(c[4]),
                "volume": float(c[6]),
            })

        return self._to_dataframe(rows)

    def get_instrument(self, symbol: str = "BTC-USDT") -> dict:
        """Contract specs: tick size, minimum order size, leverage limits.

        Needed in Step 5. You cannot order 0.00037 BTC if the minimum step is
        0.001, and an order violating the spec is simply rejected.
        """
        data = self._get("/api/v1/market/instruments", {"instId": symbol})
        if not data:
            raise RuntimeError(f"No instrument info for {symbol}")
        return data[0]
