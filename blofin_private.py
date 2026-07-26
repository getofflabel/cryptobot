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
import itertools
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

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
    # WHICH KEYS GET PICKED UP FROM THE ENVIRONMENT — read before editing.
    #
    # This prefix list is the ONLY route credentials take in the cloud. A
    # prefix missing from it means the variable is invisible to the whole
    # program, silently: no error, no warning, just a None where a key
    # should be, and a bot that starts up and does nothing.
    #
    # That nearly happened on 2026-07-25. ALPACA_ was absent while the new
    # build was being pointed at Alpaca. The keys were correctly set on
    # Render and would have read back as missing on Monday morning, which
    # would have looked exactly like the strategy deciding not to trade.
    #
    # Add the prefix HERE whenever a new service is introduced.
    ENV_PREFIXES = (
        "BLOFIN_",      # retired 2026-07-25, kept so old tools still parse
        "CRYPTOBOT_",   # state store
        "ALPACA_",      # the venue the new build trades
        "TELEGRAM_",    # alerts — a silent alerter is worse than none
    )
    for key, val in os.environ.items():
        if key.startswith(ENV_PREFIXES):
            env[key] = val
    return env


# MARGIN MODE (Wallace, 2026-07-24: "why are you trading cross instead of
# ISO anyway?"). He is right and cross was an inherited default, never a
# decision. Every position this bot opens carries an exchange-side stop
# ~0.6-1% away, while cross-mode liquidation sits 24-62% away — so the
# cushion cross buys is never touched. What cross COSTS is real: it pledges
# the WHOLE account as collateral for every book's position, so one gap
# through a stop, or one stop that failed to place, can reach across and
# take the other books down with it. ISOLATED caps each trade's worst case
# at its own margin — which is exactly the per-trade risk budget the engine
# already sizes to. After a week of orphaned positions and failed brackets,
# that containment beats an unused cushion.
#
# THE HARD CONSTRAINT: a symbol's margin mode cannot change while it holds a
# position, and an order whose marginMode disagrees with the live position is
# REJECTED (that mismatch is exactly the 2026-07-23 "all operations failed"
# bug). So nothing is ever forced: _mode_for() reads the live position's own
# mode when one exists and only uses the preferred mode when flat. Open
# cross positions therefore live out their lives as cross; every NEW position
# opens isolated as its symbol goes flat.
MARGIN_MODE = "isolated"


# CLIENT-ORDER-ID TAGGING (Wallace, 2026-07-25: "the exchange's own record
# can't tell a BOT trade from one you placed by hand"). Verified live against
# the BloFin demo API on 2026-07-25 (see BLOFIN_API_REFERENCE.md):
#   - clientOrderId accepts only letters, digits, and underscores, max 32
#     chars (BloFin error 152009 on anything else — no hyphens, no colons).
#   - It round-trips through GET /api/v1/trade/orders-history for plain
#     orders AND through GET /api/v1/trade/orders-tpsl-pending for TP/SL
#     brackets — both endpoints accept the SAME "clientOrderId" body field
#     on POST /api/v1/trade/order and POST /api/v1/trade/order-tpsl.
#   - It is NOT present on fills-history rows — book/order attribution has
#     to go through orders-history, never fills-history.
#   - Neither orders-history's clientOrderId= nor orderId= query params
#     filter server-side (confirmed empirically — both return the same full
#     page regardless of the value passed), so callers must filter the
#     returned rows themselves. fills-history's orderId= DOES filter
#     server-side (confirmed) — prefer it when you already have an order id.
CLIENT_TAG_PREFIX = "CBOT"
_CLIENT_TAG_RE = re.compile(r"^[A-Za-z0-9]{1,16}$")
_coid_counter = itertools.count()

# Every order placed before this moment carries clientOrderId == "" — the
# field was empty on 100% of pre-existing orders-history rows we inspected.
# From this timestamp forward, every order this codebase places is tagged,
# so BloFin's own orders-history becomes the authoritative per-book record
# from here on. BEFORE this timestamp, only the local event log
# (trades_log.jsonl / the cloud state mirror) can tell a bot trade from one
# Wallace placed by hand — do not treat pre-cutover exchange history as
# attributable to any book. See BLOFIN_API_REFERENCE.md.
#
# Set to the moment this change was written (2026-07-25 06:25 UTC). If the
# ACTUAL deploy to the live Render worker happens meaningfully later than
# that, bump this forward to match the real deploy time — this constant
# should reflect when tagged orders genuinely started flowing to the
# exchange, not when the code was written.
TAGGING_CUTOVER_UTC = datetime(2026, 7, 25, 6, 25, 0, tzinfo=timezone.utc)

# Short, stable codes for every order-placing book — used to build
# clientOrderIds and to filter orders-history by book once tagged orders
# exist. Keep these short; make_client_order_id() has headroom to spare
# but there is no reason to spend it.
BOOK_TAGS = {
    "daily_pick": "dp",
    "gold_book": "gb",
    "diver": "dv",
    "newsdesk": "nd",
    "shorts_lab": "sl",
    "tactical": "tc",
    "tactical_eth": "tce",   # the amplifier slot inside tactical.py
    "breakout_book": "bo",
    "core_ride": "cr",       # step5_paper_trade.py's own book
    "flatten": "fl",         # emergency stray-position cleanup, still bot-initiated
    # The 2026-07-25 rebuild: one method, three markets, two venues. Only the
    # crypto one places orders here — the stock and gold tags exist so a fill
    # log is unambiguous about which market a row came from even though those
    # two go to Alpaca.
    "tjr_crypto": "tjc",
    "tjr_stocks": "tjs",
    "tjr_gold": "tjg",
}


def fmt_size(size: float, lot: float | None = None) -> str:
    """An order size the exchange will accept.

    Lot sizes are NOT the same across symbols (verified live: LINK-USDT
    trades in whole contracts, SOL and LTC in hundredths, everything else in
    tenths). A size that is not a multiple of the symbol's own lotSize is
    rejected, so the size is snapped DOWN to the lot — down, never up,
    because rounding up puts more on the line than the size that was worked
    out. Pass lot=None to keep the old one-decimal behaviour."""
    if lot and lot > 0:
        size = int(abs(size) / lot) * lot * (1 if size >= 0 else -1)
    places = 1
    if lot and lot > 0:
        s = f"{lot:.10f}".rstrip("0")
        places = max(1, len(s.split(".")[1])) if "." in s else 0
    return f"{size:.{places}f}"


def fmt_price(price: float, tick: float | None = None) -> str:
    """A price the exchange will accept.

    THIS MATTERS MORE THAN IT LOOKS. Tick sizes run from 0.1 on Bitcoin to
    0.00001 on DOGE. Formatting every price to one decimal — which this file
    used to do everywhere — turns a DOGE stop of 0.18432 into "0.2", which is
    not a rounding error, it is a completely different stop. Pass tick=None
    to keep the old behaviour for the callers that only ever see Bitcoin."""
    if tick and tick > 0:
        s = f"{tick:.12f}".rstrip("0")
        places = len(s.split(".")[1]) if "." in s else 0
        return f"{round(price / tick) * tick:.{places}f}"
    return f"{price:.1f}"


def make_client_order_id(tag: str) -> str:
    """A clientOrderId for book `tag` that is unique and legal under
    BloFin's rules (see the block comment above). Millisecond timestamp +
    an in-process monotonic counter makes collisions impossible even for
    two orders placed in the same millisecond (e.g. entry immediately
    followed by its TP/SL bracket).

    The counter is zero-padded to 6 digits and taken mod 1,000,000 — NOT
    mod 10 (an earlier version of this function used a single trailing
    digit and a same-process test caught it colliding within a tight loop:
    two calls landing in the same millisecond with the counter's last
    digit having cycled back to the same value). A million sequential
    calls would have to land in the exact same millisecond to collide,
    which cannot happen for anything this codebase actually does."""
    if not _CLIENT_TAG_RE.match(tag):
        raise ValueError(
            f"bad client tag {tag!r} — letters/digits only, max 16 chars")
    seq = next(_coid_counter) % 1_000_000
    coid = f"{CLIENT_TAG_PREFIX}_{tag}_{int(time.time() * 1000)}{seq:06d}"
    if len(coid) > 32:
        raise ValueError(f"clientOrderId too long ({len(coid)} > 32): {coid}")
    return coid


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

    def account_balance(self) -> dict:
        """The trading-account balance endpoint — a DIFFERENT, richer read
        than futures_balance()'s /api/v1/asset/balances. This one has
        `totalEquity` and `isolatedEquity` at the top level: the exchange's
        OWN balance-plus-unrealized-PnL number, already combined. Anywhere
        that currently computes "equity = balance + unrealized" by hand
        (see the old bot_pnl.py) should read `totalEquity` from here
        instead — see BLOFIN_API_REFERENCE.md."""
        return self._call("GET", "/api/v1/account/balance")

    def instruments(self, inst_type: str = "SWAP") -> list[dict]:
        """Every tradeable contract's own spec — contractValue, lotSize,
        tickSize, maxLeverage. READ THESE, never assume them: contract values
        run from 0.001 on Bitcoin to 1000 on DOGE, so a size worked out
        against the wrong one is wrong by a factor of a million."""
        return self._call("GET", "/api/v1/market/instruments",
                          {"instType": inst_type})

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

    def _mode_for(self, symbol: str) -> str:
        """The margin mode every order/bracket on `symbol` MUST use: the live
        position's own mode when one exists (mismatch = rejection), otherwise
        the preferred MARGIN_MODE. Degrades to MARGIN_MODE if the read fails
        — never blocks a trade on a bookkeeping lookup."""
        try:
            for pos in self.positions(symbol):
                if abs(float(pos.get("positions") or 0)) > 0:
                    return str(pos.get("marginMode") or MARGIN_MODE)
        except Exception:
            pass
        return MARGIN_MODE

    def ensure_leverage(self, symbol: str, leverage: float,
                        margin_mode: str | None = None) -> bool:
        """Set the account leverage for THIS trade, right before opening it.
        Every book calls this with ITS OWN leverage (the ride 10x, the strikes
        / lab / apprentice 20x, or any per-trade value) so leverage is DYNAMIC
        per trade, never a fixed account setting. Because only one book holds a
        given symbol at a time (direction gates + one-slot rules), there is no
        conflict. The MISSING version of this call was the exact bug that
        silently rejected every order on 2026-07-23 ('all operations failed').
        Returns True on success; logs and returns False on failure (caller
        should alert loudly rather than trade unprotected)."""
        margin_mode = margin_mode or self._mode_for(symbol)
        try:
            self.set_leverage(symbol, int(round(leverage)), margin_mode)
            print(f"  leverage set {int(round(leverage))}x {margin_mode} "
                  f"on {symbol}")
            return True
        except Exception as e:
            print(f"  ⚠️ set-leverage FAILED on {symbol}: {str(e)[:100]}")
            return False

    def market_order(self, symbol: str, side: str, contracts: float,
                     reduce_only: bool = False,
                     margin_mode: str | None = None,
                     client_order_id: str | None = None,
                     lot_size: float | None = None,
                     stop_price: float | None = None,
                     take_profit: float | None = None,
                     tick_size: float | None = None) -> str:
        """Place a market order for `contracts`. Returns the order id.

        stop_price / take_profit: BOTH GO ON WITH THE ORDER, NOT AFTER IT.

            Wallace, 2026-07-26: "stops can literally be placed with the
            order together, it doesnt have to be after" ... "stop and take
            profit by the way".

            He is right and this endpoint takes both. Verified live on the
            demo account: slTriggerPrice and tpTriggerPrice on
            POST /api/v1/trade/order return code 0, and both are resting at
            the exchange the moment the position exists.

            ONE THING THIS DOES NOT SOLVE, stated so nobody assumes it does.
            The attached bracket covers the WHOLE position, and his method
            takes half off at the first target and lets the rest run. So the
            attached take profit is the LAST target, not the first — it is
            the "if we lose contact with this position entirely, get out
            somewhere sensible" order. The staged partial exits are still
            managed by the bot on each bar, and if the bot dies the position
            is left with a real stop and a real target rather than nothing.

            Why it matters more than a tidier call: placing the stop as a
            SECOND request leaves a window where the position is open with
            nothing under it, and that window is not theoretical. On 26 July
            a DOT short filled, price ran past where the stop belonged
            before the second call landed, the exchange refused the stop as
            invalid ("SL trigger price should be higher than the latest
            trading price"), and the bot had to close the position a second
            later. Attached, there is no window and no second call to fail.

            Always pass tick_size with it — an unrounded trigger price is
            rejected or, worse, truncated onto the wrong side of the market.

        side is "buy" or "sell". reduce_only=True marks an order that may
        only shrink an existing position — the standard guard that prevents
        an intended exit from accidentally opening a fresh position the
        other way.

        margin_mode MUST match the existing position's mode ("cross" or
        "isolated") or BloFin rejects the order. When closing, always read
        the mode off the position rather than assuming.

        client_order_id: pass the string from make_client_order_id() so
        this order is identifiable as OURS (and which book's) on the
        exchange's own record — see the tagging block comment near the top
        of this file. Optional only for back-compat call sites; every book
        should be passing one.
        """
        margin_mode = margin_mode or self._mode_for(symbol)
        body = {
            "instId": symbol,
            "marginMode": margin_mode,
            "positionSide": "net",
            "side": side,
            "orderType": "market",
            "size": fmt_size(contracts, lot_size),
        }
        if reduce_only:
            body["reduceOnly"] = "true"
        if client_order_id:
            body["clientOrderId"] = client_order_id
        # The protection rides IN with the entry. -1 means "when it
        # triggers, get out at market" — in a fast move you want out, not a
        # resting limit the market can skip straight over.
        if stop_price is not None:
            body["slTriggerPrice"] = fmt_price(stop_price, tick_size)
            body["slOrderPrice"] = "-1"
        if take_profit is not None:
            body["tpTriggerPrice"] = fmt_price(take_profit, tick_size)
            body["tpOrderPrice"] = "-1"
        data = self._call("POST", "/api/v1/trade/order", body=body)
        if isinstance(data, list) and data:
            first = data[0]
            if str(first.get("code", "0")) != "0":
                raise RuntimeError(f"Order rejected: {first}")
            return str(first.get("orderId"))
        raise RuntimeError(f"Unexpected order response: {data}")

    def post_only_order(self, symbol: str, side: str, contracts: float,
                        price: float, reduce_only: bool = False,
                        client_order_id: str | None = None) -> str:
        """Place a post-only limit order: it either rests in the book as a
        MAKER order (2 bps fee instead of 6, zero spread cost) or, if the
        price would cross the book and take liquidity, the exchange rejects
        it rather than filling it as taker. That guarantee is the point.

        client_order_id: see market_order() — pass a make_client_order_id()
        tag so this order is attributable on the exchange's own record."""
        body = {
            "instId": symbol,
            "marginMode": self._mode_for(symbol),
            "positionSide": "net",
            "side": side,
            "orderType": "post_only",
            "price": f"{price:.1f}",
            "size": f"{contracts:.1f}",
        }
        if reduce_only:
            body["reduceOnly"] = "true"
        if client_order_id:
            body["clientOrderId"] = client_order_id
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
                   sl_price: float, margin_mode: str | None = None,
                   client_order_id: str | None = None,
                   lot_size: float | None = None,
                   tick_size: float | None = None) -> str:
        """Attach a take-profit / stop-loss bracket to a position.

        position_side_close: "sell" to close a long, "buy" to close a short.
        tp/sl trigger at the given prices and execute at MARKET (-1), the
        standard choice: in a fast move you want OUT, not a resting limit
        the market may skip over.

        This is what makes the position 'projected' in the BloFin app — the
        TP and SL lines show on the position card and the chart.

        client_order_id: see market_order() — verified live 2026-07-25 that
        this endpoint accepts the SAME "clientOrderId" body field (it shows
        up as "clientOrderId" in orders-tpsl-pending, not a separate
        "algoClientOrderId" field, despite that field existing elsewhere)."""
        margin_mode = margin_mode or self._mode_for(symbol)
        body = {
            "instId": symbol,
            "marginMode": margin_mode,
            "positionSide": "net",
            "side": position_side_close,
            "size": fmt_size(contracts, lot_size),
            "slTriggerPrice": fmt_price(sl_price, tick_size),
            "slOrderPrice": "-1",
            "reduceOnly": "true",
        }
        if client_order_id:
            body["clientOrderId"] = client_order_id
        if tp_price is not None:
            # Optional: round 11 measured our +5% TP truncating the big
            # winners the strategy lives on (test return 32% -> 10%).
            # Stop-loss-only brackets are now the default.
            body["tpTriggerPrice"] = fmt_price(tp_price, tick_size)
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

    def order_fee(self, symbol: str, order_id: str | None) -> float | None:
        """Actual fee BloFin charged for one order, read straight from
        fills-history (its orderId filter DOES work server-side, confirmed
        live) — replaces estimating fees from an assumed maker/taker bps
        rate. Returns None (never a guess) if there is no order id or the
        fill hasn't posted yet; the caller decides the fallback."""
        if not order_id:
            return None
        try:
            rows = self.fills(symbol, order_id=order_id)
        except Exception:
            return None
        if not rows:
            return None
        try:
            return sum(float(r.get("fee", 0) or 0) for r in rows)
        except Exception:
            return None

    def orders_history(self, symbol: str, limit: int | None = None) -> list[dict]:
        """Exchange's own order-level record — `pnl`, `fee`, `clientOrderId`,
        `state` per order, straight from BloFin. This is where
        clientOrderId actually shows up (never on fills-history), so this
        is how book/order attribution is done from TAGGING_CUTOVER_UTC
        onward. NOTE (verified live): neither BloFin's clientOrderId= nor
        orderId= query params filter server-side here — this always
        returns the page of recent orders for `symbol`; filter client-side
        by clientOrderId/orderId on the result."""
        params = {"instId": symbol}
        if limit:
            params["limit"] = str(limit)
        return self._call("GET", "/api/v1/trade/orders-history", params)
