"""
blofin_private.py — the authenticated client for BloFin DEMO trading.

SAFETY, STATED ONCE AND ENFORCED IN CODE:
This class hardcodes the demo-trading host. It cannot be pointed at the live
exchange by any config value, environment variable, or constructor argument,
because the capability to talk to real money simply does not exist in this
file. When the day comes to trade real funds (a separate decision, made
deliberately), that will be a new, deliberate piece of code — not a flag flip.

HOW BLOFIN AUTHENTICATION WORKS (so the code below isn't magic)

Every private request carries five headers:
  ACCESS-KEY        your API key (identifies you)
  ACCESS-TIMESTAMP  milliseconds since 1970 (rejects replayed requests)
  ACCESS-NONCE      a unique random string per request (same purpose)
  ACCESS-PASSPHRASE the passphrase you chose when creating the key
  ACCESS-SIGN       the signature — proof you hold the SECRET without
                    ever sending the secret itself

The signature: concatenate  path + method + timestamp + nonce + body,
HMAC-SHA256 it with your secret, hex-encode, then base64 that hex string.
(The hex-then-base64 double encoding is a BloFin quirk — most exchanges
base64 the raw digest. Getting this wrong yields "signature invalid".)

The server performs the same computation with its copy of your secret; if
the results match, the request is genuinely yours and untampered.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid

import requests


def load_env(path: str = ".env") -> dict:
    """Credentials from a local .env file, overlaid with real environment
    variables (which win). Locally the .env file supplies everything; in
    the cloud (Render) there is no file and the platform injects the same
    keys as environment variables. One loader, both worlds.
    """
    env: dict[str, str] = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip("'\"")
    for key, val in os.environ.items():
        if key.startswith(("BLOFIN_", "CRYPTOBOT_")):
            env[key] = val
    return env


class BlofinDemoPrivate:
    """Authenticated access to the BloFin DEMO trading account."""

    # Hardcoded on purpose. See the safety note at the top of this file.
    BASE_URL = "https://demo-trading-openapi.blofin.com"

    def __init__(self, api_key: str, api_secret: str, passphrase: str,
                 timeout: int = 30):
        if not (api_key and api_secret and passphrase):
            raise ValueError(
                "Missing credentials. Create demo API keys in BloFin and put "
                "them in cryptobot/.env — see .env.example for the format."
            )
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.timeout = timeout
        self._session = requests.Session()

    # -- signing ------------------------------------------------------------

    def _headers(self, method: str, path: str, body: str) -> dict:
        ts = str(int(time.time() * 1000))
        nonce = str(uuid.uuid4())
        prehash = f"{path}{method}{ts}{nonce}{body}"
        digest_hex = hmac.new(self.api_secret.encode(), prehash.encode(),
                              hashlib.sha256).hexdigest().encode()
        sign = base64.b64encode(digest_hex).decode()
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts,
            "ACCESS-NONCE": nonce,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    def _call(self, method: str, path: str, params: dict | None = None,
              body: dict | None = None) -> dict | list:
        # The signed path must include the query string, byte for byte.
        if params:
            from urllib.parse import urlencode
            path = f"{path}?{urlencode(params)}"
        body_str = json.dumps(body, separators=(",", ":")) if body else ""

        r = self._session.request(
            method, f"{self.BASE_URL}{path}",
            headers=self._headers(method, path, body_str),
            data=body_str or None,
            timeout=self.timeout,
        )
        if "html" in r.headers.get("content-type", "").lower():
            raise RuntimeError("Got an HTML page (edge throttle). Try again.")
        payload = r.json()
        if str(payload.get("code")) != "0":
            raise RuntimeError(
                f"BloFin demo API error on {path}: "
                f"code={payload.get('code')} msg={payload.get('msg')}"
            )
        return payload.get("data", [])

    # -- account ------------------------------------------------------------

    def futures_balance(self) -> dict:
        """USDT balance in the demo futures account."""
        data = self._call("GET", "/api/v1/asset/balances",
                          {"accountType": "futures"})
        for row in data:
            if row.get("currency") == "USDT":
                return row
        raise RuntimeError("No USDT balance found in demo futures account")

    def positions(self, symbol: str | None = None) -> list[dict]:
        params = {"instId": symbol} if symbol else None
        return self._call("GET", "/api/v1/account/positions", params)

    def net_position_contracts(self, symbol: str) -> float:
        """Current net position in contracts. Positive long, negative short.

        We always read our position FROM the exchange rather than tracking it
        locally. If the bot restarts, local state is gone but the exchange
        still knows the truth. One source of truth, and it's not us.
        """
        total = 0.0
        for p in self.positions(symbol):
            size = float(p.get("positions", 0) or 0)
            total += size
        return total

    def set_leverage(self, symbol: str, leverage: int = 3,
                     margin_mode: str = "cross"):
        """Set account leverage for the symbol. We size positions well under
        1x exposure; the 3x setting just guarantees margin headroom so a
        market order is never rejected for a few dollars of fees."""
        self._call("POST", "/api/v1/account/set-leverage",
                   body={"instId": symbol, "leverage": str(leverage),
                         "marginMode": margin_mode})

    # -- trading ------------------------------------------------------------

    def market_order(self, symbol: str, side: str, contracts: float,
                     reduce_only: bool = False,
                     margin_mode: str = "cross") -> str:
        """Place a market order for `contracts`. Returns the order id.

        side is "buy" or "sell". reduce_only=True marks an order that may
        only shrink an existing position — the standard guard that prevents
        an intended exit from accidentally opening a fresh position the
        other way.

        margin_mode MUST match the existing position's mode ("cross" or
        "isolated") or BloFin rejects the order. When closing, always read
        the mode off the position rather than assuming.
        """
        body = {
            "instId": symbol,
            "marginMode": margin_mode,
            "positionSide": "net",
            "side": side,
            "orderType": "market",
            "size": f"{contracts:.1f}",
        }
        if reduce_only:
            body["reduceOnly"] = "true"
        data = self._call("POST", "/api/v1/trade/order", body=body)
        if isinstance(data, list) and data:
            first = data[0]
            if str(first.get("code", "0")) != "0":
                raise RuntimeError(f"Order rejected: {first}")
            return str(first.get("orderId"))
        raise RuntimeError(f"Unexpected order response: {data}")

    def post_only_order(self, symbol: str, side: str, contracts: float,
                        price: float, reduce_only: bool = False) -> str:
        """Place a post-only limit order: it either rests in the book as a
        MAKER order (2 bps fee instead of 6, zero spread cost) or, if the
        price would cross the book and take liquidity, the exchange rejects
        it rather than filling it as taker. That guarantee is the point."""
        body = {
            "instId": symbol,
            "marginMode": "cross",
            "positionSide": "net",
            "side": side,
            "orderType": "post_only",
            "price": f"{price:.1f}",
            "size": f"{contracts:.1f}",
        }
        if reduce_only:
            body["reduceOnly"] = "true"
        data = self._call("POST", "/api/v1/trade/order", body=body)
        if isinstance(data, list) and data:
            first = data[0]
            if str(first.get("code", "0")) != "0":
                raise RuntimeError(f"post-only rejected: {first}")
            return str(first.get("orderId"))
        raise RuntimeError(f"Unexpected order response: {data}")

    def pending_orders(self, symbol: str) -> list[dict]:
        return self._call("GET", "/api/v1/trade/orders-pending",
                          {"instId": symbol})

    def cancel_order(self, symbol: str, order_id: str):
        self._call("POST", "/api/v1/trade/cancel-order",
                   body={"instId": symbol, "orderId": order_id})

    def place_tpsl(self, symbol: str, position_side_close: str,
                   contracts: float, tp_price: float | None,
                   sl_price: float, margin_mode: str = "cross") -> str:
        """Attach a take-profit / stop-loss bracket to a position.

        position_side_close: "sell" to close a long, "buy" to close a short.
        tp/sl trigger at the given prices and execute at MARKET (-1), the
        standard choice: in a fast move you want OUT, not a resting limit
        the market may skip over.

        This is what makes the position 'projected' in the BloFin app — the
        TP and SL lines show on the position card and the chart.
        """
        body = {
            "instId": symbol,
            "marginMode": margin_mode,
            "positionSide": "net",
            "side": position_side_close,
            "size": f"{contracts:.1f}",
            "slTriggerPrice": f"{sl_price:.1f}",
            "slOrderPrice": "-1",
            "reduceOnly": "true",
        }
        if tp_price is not None:
            # Optional: round 11 measured our +5% TP truncating the big
            # winners the strategy lives on (test return 32% -> 10%).
            # Stop-loss-only brackets are now the default.
            body["tpTriggerPrice"] = f"{tp_price:.1f}"
            body["tpOrderPrice"] = "-1"
        data = self._call("POST", "/api/v1/trade/order-tpsl", body=body)
        if isinstance(data, dict):
            return str(data.get("tpslId", data))
        if isinstance(data, list) and data:
            return str(data[0].get("tpslId", data[0]))
        return str(data)

    def pending_tpsl(self, symbol: str) -> list[dict]:
        """Active TP/SL brackets for a symbol."""
        return self._call("GET", "/api/v1/trade/orders-tpsl-pending",
                          {"instId": symbol})

    def cancel_tpsl(self, symbol: str, tpsl_id: str):
        self._call("POST", "/api/v1/trade/cancel-tpsl",
                   body=[{"instId": symbol, "tpslId": tpsl_id}])

    def fills(self, symbol: str, order_id: str | None = None) -> list[dict]:
        """Recent fills — the prices we ACTUALLY traded at. Comparing these
        against the price we expected is how we measure real slippage."""
        params = {"instId": symbol}
        if order_id:
            params["orderId"] = order_id
        return self._call("GET", "/api/v1/trade/fills-history", params)
