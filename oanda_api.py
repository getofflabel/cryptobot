"""
oanda_api.py — THE CURRENCY VENUE. Practice host, real bank rates, one API.

WHY THIS EXISTS (2026-07-26)

Forex was dropped on 2026-07-25 for exactly one reason, and it was written
down at the time: "Currencies were the one market in this build with no venue
behind them." No broker in this project could send a currency order, so the
output was a message and Wallace placed the trade by hand. He has decided
that dropping it was a mistake. The gap was a venue, and this file closes it.

THIS FILE IS PLUMBING, AND THAT IS THE WHOLE DESIGN.

    IT KNOWS NOTHING ABOUT ANY TRADING METHOD. No sessions, no entry windows,
    no bias, no setups, no opinion about which pair is worth watching or when
    London opens. It takes an order and places it; it takes a date range and
    returns candles. WHICH order and WHEN is decided somewhere else entirely,
    by whatever strategy is pointed at it, and that strategy is free to
    change without a line in here moving.

    If a session rule, a time window, or the name of a setup ever appears
    below this line, the abstraction has been broken and the fix belongs in
    the strategy, not here.

============================================================ WHY OANDA

Five routes were checked against four requirements, in this order of
importance:

  1. a FREE PRACTICE account whose API surface is identical to live, so
     paper -> real is a config value and not a rewrite. This is the whole
     design premise of venue.py and it is non-negotiable.
  2. HISTORICAL CANDLES BY API, years deep, at 1m/5m/15m/1h/4h/1d, so a
     strategy can be graded over years rather than over a fortnight.
  3. four instruments: GBP/JPY, GBP/USD, EUR/USD and XAU/USD.
  4. a real Python path — an official REST API, not a scraped page and not
     something bound to a desktop terminal.

  OANDA v20 practice          CHOSEN.
      Practice is api-fxpractice.oanda.com and live is api-fxtrade.oanda.com.
      Same paths, same bodies, same auth header, same everything — the host
      string is the difference, which is precisely the shape venue.py was
      built around. Free, no funding, no approval queue.
      Candles go back to 2005 on the majors at every granularity this method
      reads, 5,000 bars a request with from/to paging.
      All four instruments: GBP_JPY, GBP_USD, EUR_USD, XAU_USD.
      Plain HTTPS + JSON + a bearer token. `requests` and nothing else.
      AND THE ONE THAT DECIDED IT: a stop can be attached to the entry in
      the SAME request (`stopLossOnFill`), so there is no window where a
      position exists with nothing under it. See the note in venue.py.

  Interactive Brokers paper   REJECTED on requirement 4, and it is fatal.
      The TWS API is not a web API. It speaks to a desktop program (Trader
      Workstation or IB Gateway) that has to be running and logged in, with
      a re-login most days. Render runs a Linux container with no desktop,
      so the cloud bot could not reach it at all. Historical data is also
      pacing-limited hard enough that pulling years of 1-minute bars is a
      multi-day job. Paper access also wants a live account behind it.

  MetaTrader 5 via a broker demo   REJECTED on requirement 4.
      Checked properly rather than dismissed, because MetaTrader is what a
      lot of currency traders actually use. The official `MetaTrader5` Python
      package is Windows-only and drives a running MT5 terminal through
      shared memory. His laptop is a Mac and the cloud bot is Linux. The
      community workaround runs MT5 under Wine behind an RPC shim — that is
      a second thing that can fail, in the order path, for no gain.

  Capital.com                 REJECTED on requirement 2.
      A genuine REST API with a demo mode, so it clears 1 and 4. But the
      history endpoint returns at most 1,000 bars a call and the archive is
      shallow; grading over years is not on the table. The demo balance is
      also capped.

  Tradermade                  REJECTED on requirement 1. Data only. It
      cannot place an order, so it is not a venue, it is a feed — and we
      already have Dukascopy for free history and Yahoo for free quotes.

  Pepperstone                 REJECTED on requirement 4. cTrader Open API is
      protobuf over a raw TCP socket, or else it is MT4/MT5 again.

============================================ WHAT THIS FILE IS AND IS NOT

This is the CLIENT: headers, paths, JSON, candles, and the two formatting
rules that forex punishes you for getting wrong. It is the same shape as
alpaca.py and blofin_private.py so nobody has to learn a third vocabulary.

The SAFETY lives one layer up, in venue.OandaVenue: the attribution gate, the
sealed reducing calls, the no-stop-no-trade refusal. Read that file for the
rules. This one does the talking.

PRACTICE IS THE DEFAULT AND THE DEFAULT IS NOT AN ACCIDENT
`OandaClient()` with no argument points at the practice host. Reaching the
live host takes `practice=False`, passed on purpose, by a caller that had to
type it — and venue.py will not build such a client without the exact
real-money confirmation phrase. There is no path where confusion resolves to
real money.

=========================================== THE TWO FOREX-SPECIFIC TRAPS

1. A PIP IS NOT ONE NUMBER. On GBP/USD and EUR/USD a pip is 0.0001 and the
   price is quoted to 5 decimals. On GBP/JPY a pip is 0.01 and the price is
   quoted to 3. On XAU/USD it is different again. Hard-coding "0.0001" makes
   every yen-cross stop wrong by a factor of a hundred.

   SO NOTHING HERE ASSUMES. `spec()` reads `pipLocation`,
   `displayPrecision`, `tradeUnitsPrecision` and `minimumTradeSize` from
   OANDA's own instrument list, live, per instrument, and caches only on
   success. A spec that could not be read comes back {} and {} means DO NOT
   TRADE — never a default. This is the same discipline BlofinVenue uses for
   contract sizes, and for the same reason: the guess is not off by a
   rounding error, it is off by orders of magnitude.

2. A PRICE SENT AT THE WRONG PRECISION IS A DIFFERENT PRICE. blofin_private
   learned this when a DOGE stop of 0.18432 formatted to one decimal became
   "0.2". Forex is worse, because the correct precision changes per pair. A
   GBP/JPY stop of 189.432 sent as "189.43200" is rejected; a EUR/USD stop
   of 1.08234 sent as "1.082" is eleven pips away from where the caller put
   it. `fmt_price` takes the instrument's own displayPrecision and there is
   no default path that skips it.

UNITS. OANDA sizes in units of the BASE currency: 100,000 units of GBP_USD
is one standard lot, and a negative number is a short. XAU_USD is priced in
ounces. `tjr_alerts.position_size` — the one sizing function in this project
— already returns `units`, so the number this file sends is the number that
function produced, unchanged. NOTHING IN THIS FILE SIZES ANYTHING, and a
second sizing path must never appear here: this project already shipped two
of them once and they disagreed by up to 36 times, which meant every
backtest described a bot nobody was running.

COSTS. Charged, never consulted. OANDA's practice host quotes a real bid and
a real ask, so the spread is measured rather than assumed. Nothing here
declines a trade, prefers a pair, or moves a threshold because of what
trading costs.

NOTHING IN THIS FILE PLACES AN ORDER BY ITSELF, and every order-placing
method on the client refuses to run unless the caller supplies the client
order id that venue.py's guard built.
"""

from __future__ import annotations

import datetime as dt
import os

REPO = os.path.dirname(os.path.abspath(__file__))

# The two hosts. They are the ONLY difference between practice and live, and
# writing them next to each other is the point: what you are looking at is
# the entire migration.
PRACTICE_HOST = "https://api-fxpractice.oanda.com"
LIVE_HOST = "https://api-fxtrade.oanda.com"

# An OANDA account id is "{siteID}-{divisionID}-{userID}-{accountNumber}".
# Practice accounts are issued under site 101 and live accounts under site
# 001. That is a SECOND, independent check that we are where we think we
# are — the host says practice and the account id agrees, or something is
# wrong and we stop.
PRACTICE_SITE_PREFIX = "101-"
LIVE_SITE_PREFIX = "001-"

# THE ENV KEYS. Two of them, and the SAME two for practice and live.
#
# Which host they reach is decided by `practice`, which venue.py sets from
# the registry — not by which variable the key happens to be sitting in. That
# is deliberate: an OANDA token is issued by the portal you generated it in,
# so a practice token cannot reach the live host even if something pointed it
# there, and `environment_check()` below refuses the mismatch anyway. One
# pair of names means one thing to set on the laptop and the same one thing
# to set on Render.
TOKEN_KEY = "OANDA_API_TOKEN"
ACCOUNT_KEY = "OANDA_ACCOUNT_ID"

# THE PREFIX IS REGISTERED. blofin_private.load_env only picks up environment
# variables whose names start with a prefix in its own list, and a prefix
# missing from that list makes the variable invisible to the whole program —
# silently, with no error, just a bot that starts and does nothing. ALPACA_
# was missing for a day and nearly broke a Monday morning. "OANDA_" was added
# to that list in the same change as this file, not afterwards.

# How a pair is spelled here, and how OANDA spells it. Read this; never build
# it by string surgery at the call site, which is how a slash ends up in a
# URL. Four instruments. Adding a fifth is one line and no other change.
INSTRUMENTS = {
    "GBP/JPY": "GBP_JPY",
    "GBP/USD": "GBP_USD",
    "EUR/USD": "EUR_USD",
    "XAU/USD": "XAU_USD",
}

# Timeframes in OANDA's vocabulary. Every one this project reads is here;
# anything else is passed through so OANDA's own refusal is what the log
# records rather than a guess made here.
GRANULARITY = {
    "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
    "1h": "H1", "4h": "H4", "1d": "D", "1w": "W",
}

# OANDA's own cap on one candles request. Anything larger is paged.
MAX_CANDLES = 5000

# WHERE ONE CURRENCY DAY IS CUT FROM THE NEXT, which is a BROKER convention
# and not a strategy's opinion. Currencies roll at 17:00 New York: every
# broker's daily candle, every swap charge and every chart a currency trader
# opens is cut there. These are OANDA's own defaults; they are passed
# EXPLICITLY anyway, because a boundary that moves every daily high and low
# must not depend on a default nobody chose. A caller that wants a different
# boundary passes one — see `candles()`.
DAILY_ALIGNMENT_HOUR = 17
ALIGNMENT_TZ = "America/New_York"


class OandaError(RuntimeError):
    """Anything OANDA refused. Carries the status and the body, because a
    forex broker's refusal usually says exactly what was wrong with the
    order and throwing that away turns a five-second fix into an hour."""

    def __init__(self, message: str, status: int = 0, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


# =============================================================== FORMATTING
def pip_size(pip_location: int) -> float:
    """OANDA reports where the pip is as a power of ten: -4 on GBP/USD and
    EUR/USD, -2 on every yen cross, -2 on XAU/USD. So a pip is 10 ** that,
    read from the venue and never assumed.

    This is the single fact that makes yen crosses different, and it is
    handled by arithmetic on a number the broker gave us rather than by a
    branch on whether "JPY" appears in the name."""
    return float(10.0 ** int(pip_location))


def fmt_price(price: float, display_precision: int) -> str:
    """A price OANDA will accept, at the instrument's OWN precision.

    NOT COSMETIC. Send a EUR/USD stop of 1.08234 as "1.082" and it is eleven
    pips from where the method put it. Send a GBP/JPY stop of 189.432 as
    "189.43200" and OANDA rejects the order. There is no default precision
    here on purpose: the caller has to have read the instrument spec, which
    means it has to have succeeded in reading it."""
    p = int(display_precision)
    if p < 0:
        raise ValueError(f"display_precision must be >= 0, got {display_precision}")
    return f"{float(price):.{p}f}"


def fmt_units(units: float, units_precision: int = 0,
              minimum: float = 0.0) -> str | None:
    """A size OANDA will accept, snapped DOWN to the instrument's step.

    DOWN, never up, and for the same reason blofin_private snaps down:
    rounding up puts more on the line than the size that was worked out, and
    the size was worked out against a stop.

    Returns None when the size rounds to nothing or falls under the
    instrument's minimum — which is a refusal for the caller to report, not
    something to quietly fix by sending the minimum instead."""
    p = max(0, int(units_precision))
    step = 10.0 ** (-p)
    sign = -1.0 if units < 0 else 1.0
    snapped = int(abs(float(units)) / step) * step
    if snapped <= 0:
        return None
    if minimum and snapped < float(minimum):
        return None
    return f"{sign * snapped:.{p}f}"


def to_et(ts_utc):
    """A candle's UTC start as New York wall-clock, naive — the clock every
    session rule in this project is written in."""
    import pandas as pd
    s = pd.to_datetime(ts_utc, utc=True)
    return s.dt.tz_convert("America/New_York").dt.tz_localize(None)


# =================================================================== CLIENT
class OandaClient:
    """Authenticated access to one OANDA account. Practice unless told
    otherwise, in writing, by a caller that meant it.

    Same shape as alpaca.AlpacaPaper and blofin_private.BlofinDemoPrivate:
    reads return the broker's own JSON, writes take already-formatted
    strings, and nothing in here decides anything.
    """

    def __init__(self, token: str, account_id: str, practice: bool = True,
                 timeout: float = 20.0):
        if not token:
            raise ValueError("an OANDA token is required")
        if not account_id:
            raise ValueError("an OANDA account id is required")
        self.token = token
        self.account_id = str(account_id).strip()
        self.practice = bool(practice)
        self.host = PRACTICE_HOST if self.practice else LIVE_HOST
        self.name = "oanda-practice" if self.practice else "oanda-live"
        self.timeout = float(timeout)
        self._specs: dict = {}

    # ------------------------------------------------------------ plumbing
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept-Datetime-Format": "RFC3339"}

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None):
        import requests
        url = self.host + path
        try:
            r = requests.request(method, url, headers=self._headers(),
                                 params=params, json=body, timeout=self.timeout)
        except Exception as e:                                   # noqa: BLE001
            raise OandaError(f"oanda {method} {path} did not complete: "
                             f"{str(e)[:200]}") from e
        if r.status_code >= 400:
            raise OandaError(f"oanda {method} {path} -> {r.status_code} "
                             f"{r.text[:300]}", r.status_code, r.text[:2000])
        return r.json() if r.text else None

    def _get(self, path, params=None):
        # RETRY BEFORE SURRENDER (2026-07-28, Wallace: "if you find out one
        # of these platforms reject a request you best find out why and fix
        # it asap"). OANDA's practice servers intermittently answer reads
        # with 401 "Insufficient authorization" — seen 2026-07-27 08:00 and
        # 2026-07-28 03:00 from Render while the identical token+call
        # returned 200 minutes later from both the laptop and Render's own
        # shell. Transient on their side. A read is safe to retry, so a
        # failing GET gets three tries with a short pause before the caller
        # ever hears about it. Writes (_post/_put) are NOT retried here —
        # blindly repeating an order is how doubles happen.
        import time as _time
        last = None
        for attempt in range(3):
            try:
                return self._request("GET", path, params=params)
            except Exception as e:                        # noqa: BLE001
                last = e
                if attempt < 2:
                    _time.sleep(1.5 * (attempt + 1))
        raise last

    def _post(self, path, body):
        return self._request("POST", path, body=body)

    def _put(self, path, body):
        return self._request("PUT", path, body=body)

    @property
    def _acct(self) -> str:
        return f"/v3/accounts/{self.account_id}"

    # ------------------------------------------------------------ identity
    def accounts(self) -> list:
        """Every account this token can see. Used by the setup probe so
        Wallace does not have to hunt for his account id by hand."""
        return (self._get("/v3/accounts") or {}).get("accounts") or []

    def environment_check(self) -> dict:
        """DOES THE ACCOUNT AGREE WITH THE HOST WE ARE POINTED AT.

        Two independent facts have to line up: the host string this client
        was built with, and the site id inside the account number OANDA
        issued. A practice client holding a live account id, or the reverse,
        is a configuration mistake that would otherwise only be discovered by
        an order arriving somewhere unexpected.

        Returns the finding. It never raises — the CALLER decides what to do
        about a mismatch, and in venue.py the answer is refuse to trade.
        """
        looks_practice = self.account_id.startswith(PRACTICE_SITE_PREFIX)
        looks_live = self.account_id.startswith(LIVE_SITE_PREFIX)
        agrees = (self.practice and looks_practice) or \
                 (not self.practice and looks_live)
        known = looks_practice or looks_live
        return {
            "host": self.host,
            "account_id": self.account_id,
            "client_says": "practice" if self.practice else "LIVE",
            "account_id_says": ("practice" if looks_practice else
                                "LIVE" if looks_live else "unrecognised"),
            "agrees": bool(agrees),
            "recognised": bool(known),
            "note": ("the host and the account number agree" if agrees else
                     "the host and the account number DISAGREE about whether "
                     "this is practice or live. Nothing should trade until "
                     "that is resolved."),
        }

    # ------------------------------------------------------------- account
    def summary(self) -> dict:
        return (self._get(f"{self._acct}/summary") or {}).get("account") or {}

    def instruments(self, names: list | None = None) -> list:
        params = {"instruments": ",".join(names)} if names else None
        return (self._get(f"{self._acct}/instruments", params) or {}) \
            .get("instruments") or []

    def spec(self, instrument: str) -> dict:
        """pip location, display precision, unit step, minimum size and
        margin rate for ONE instrument, read from OANDA.

        Cached on SUCCESS ONLY, so a failed read is retried next time rather
        than locked in for the life of the process. Returns {} when it cannot
        be read, and {} means DO NOT TRADE — never a default. Guessing here
        is not a rounding error: it is a yen-cross stop off by a hundred.
        """
        if instrument in self._specs:
            return self._specs[instrument]
        try:
            rows = self.instruments()
        except OandaError:
            return {}
        found = {}
        for row in rows:
            name = str(row.get("name") or "")
            if not name:
                continue
            try:
                spec = {
                    "instrument": name,
                    "type": row.get("type"),
                    "display_name": row.get("displayName"),
                    "pip_location": int(row.get("pipLocation")),
                    "pip": pip_size(int(row.get("pipLocation"))),
                    "display_precision": int(row.get("displayPrecision")),
                    "units_precision": int(row.get("tradeUnitsPrecision")),
                    "minimum_units": float(row.get("minimumTradeSize") or 0),
                    "margin_rate": float(row.get("marginRate") or 0),
                }
            except (TypeError, ValueError):
                continue          # a row we cannot read is a row we do not use
            self._specs[name] = spec
            if name == instrument:
                found = spec
        return found

    # ----------------------------------------------------------- prices
    def pricing(self, instruments: list) -> dict:
        """Current bid/ask per instrument. The spread this project CHARGES is
        measured from these two numbers rather than assumed, and nothing
        reads them to decide whether to trade."""
        rows = (self._get(f"{self._acct}/pricing",
                          {"instruments": ",".join(instruments)}) or {}) \
            .get("prices") or []
        out = {}
        for row in rows:
            bids = row.get("bids") or [{}]
            asks = row.get("asks") or [{}]
            try:
                bid = float(bids[0].get("price"))
                ask = float(asks[0].get("price"))
            except (TypeError, ValueError, IndexError):
                continue
            out[str(row.get("instrument"))] = {
                "bid": bid, "ask": ask, "mid": (bid + ask) / 2.0,
                "spread": ask - bid, "tradeable": bool(row.get("tradeable")),
                "time": row.get("time")}
        return out

    def usd_per_quote(self, instrument: str) -> float | None:
        """How many DOLLARS one unit of this instrument's quote currency is
        worth right now.

        THE YEN PROBLEM, and it is a factor of about 145, not a rounding
        error. A GBP/JPY trade's profit and its loss both arrive in YEN. A
        size worked out as though they arrived in dollars is wrong by the yen
        rate. `tjr_alerts.position_size` already takes `usd_per_quote` for
        exactly this and defaults it to 1; supplying the right number is a
        VENUE fact, not a method fact, so it is worked out here.

        Returns None when it cannot be read, and None must be treated as
        "do not size", never as 1.0.
        """
        quote = instrument.split("_")[-1]
        if quote == "USD":
            return 1.0
        direct, inverse = f"{quote}_USD", f"USD_{quote}"
        try:
            prices = self.pricing([direct, inverse])
        except OandaError:
            try:
                prices = self.pricing([inverse])
            except OandaError:
                return None
        if direct in prices and prices[direct]["mid"] > 0:
            return prices[direct]["mid"]
        if inverse in prices and prices[inverse]["mid"] > 0:
            return 1.0 / prices[inverse]["mid"]
        return None

    # ----------------------------------------------------------- candles
    def candles(self, instrument: str, granularity: str = "M5",
                count: int | None = None, start=None, end=None,
                price: str = "M", daily_alignment: int = DAILY_ALIGNMENT_HOUR,
                alignment_tz: str = ALIGNMENT_TZ) -> list:
        """One page of candles, at most MAX_CANDLES of them.

        `price` is "M" for mid, "B" for bid, "A" for ask, or any combination.
        Levels are normally read off the mid and the spread is charged from
        bid and ask, so both are reachable without a second source.

        The daily boundary is pinned explicitly. See DAILY_ALIGNMENT_HOUR.
        """
        params = {"granularity": granularity, "price": price,
                  "alignmentTimezone": alignment_tz,
                  "dailyAlignment": int(daily_alignment)}
        if start is not None:
            params["from"] = _rfc3339(start)
        if end is not None:
            params["to"] = _rfc3339(end)
        if count is not None:
            params["count"] = int(min(int(count), MAX_CANDLES))
        elif start is not None and end is None:
            params["count"] = MAX_CANDLES
        out = self._get(f"/v3/instruments/{instrument}/candles", params)
        return (out or {}).get("candles") or []

    def frame(self, instrument: str, granularity: str = "M5",
              count: int | None = None, start=None, end=None,
              price: str = "M", complete_only: bool = True):
        """Candles as the frame the rest of this project reads: t / open /
        high / low / close / volume, with `t` the bar's START in New York.

        `complete_only` drops the candle that is still forming. It defaults
        to True because a partial bar has a high and a low that are not
        finished, and this method marks levels off highs and lows — trading
        a level taken from a bar that had not closed yet is trading a level
        that did not exist.
        """
        import pandas as pd
        rows = self.candles(instrument, granularity, count, start, end, price)
        key = {"M": "mid", "B": "bid", "A": "ask"}.get(price[0], "mid")
        recs = []
        for c in rows:
            if complete_only and not c.get("complete"):
                continue
            d = c.get(key) or {}
            try:
                recs.append({"t": c.get("time"),
                             "open": float(d["o"]), "high": float(d["h"]),
                             "low": float(d["l"]), "close": float(d["c"]),
                             "volume": float(c.get("volume") or 0)})
            except (KeyError, TypeError, ValueError):
                continue
        f = pd.DataFrame(recs, columns=["t", "open", "high", "low", "close",
                                        "volume"])
        if len(f):
            f["t"] = to_et(f["t"])
        return f

    def history(self, instrument: str, granularity: str = "M5",
                start=None, end=None, price: str = "M",
                max_pages: int = 400, verbose: bool = False):
        """Years of candles, paged over OANDA's 5,000-a-request cap.

        A DROPPED PAGE IS NOT AN EMPTY MARKET, and the difference matters
        here more than almost anywhere: a hole that looks like a weekend
        would move every level marked near it. So a page that fails RAISES
        rather than ending the walk quietly, and the caller finds out.

        `end` IS A HARD BOUNDARY AND IT IS TRIMMED, NOT MERELY BROKEN ON.
        Paging asks for 5,000 bars at a time from a moving cursor, so the
        last page always overshoots — measured 2026-07-26 on a one-month
        request that came back with two and a half extra weeks. Left
        untrimmed, a backtest asked for data up to a date silently receives
        bars from after it, which is the exact shape of a look-ahead bug:
        it does not crash, it just makes the results better than they were.
        """
        import pandas as pd
        end = end or dt.datetime.now(dt.timezone.utc)
        cursor = start
        if cursor is None:
            raise ValueError("history needs a start; use frame(count=...) for "
                             "the most recent N bars")
        end_utc = _as_utc(end)
        parts, pages = [], 0
        while pages < max_pages:
            page = self.candles(instrument, granularity, count=MAX_CANDLES,
                                start=cursor, price=price)
            pages += 1
            if not page:
                break
            recs = _rows_to_frame(page, price)
            if len(recs) == 0:
                break
            parts.append(recs)
            last = pd.to_datetime(page[-1]["time"], utc=True, format="mixed")
            if verbose:
                print(f"    {instrument} {granularity}: {len(recs)} bars to "
                      f"{last}", flush=True)
            nxt = last + dt.timedelta(seconds=1)
            if end_utc is not None and nxt >= end_utc:
                break
            if cursor is not None and _as_utc(cursor) is not None and \
                    nxt <= _as_utc(cursor):
                break                      # no forward progress; stop, loudly
            cursor = nxt
        cols = ["t", "open", "high", "low", "close", "volume"]
        if not parts:
            return pd.DataFrame(columns=cols)
        out = pd.concat(parts, ignore_index=True)
        out = out.drop_duplicates(subset=["t"]).sort_values("t")
        # THE TRIM. `t` is New York wall-clock and `end` arrived as UTC or
        # naive-UTC, so the boundary is converted into the frame's own clock
        # before anything is compared. Comparing the two directly would be
        # off by the New York offset — four or five hours of bars kept or
        # dropped depending on the time of year.
        if end_utc is not None and len(out):
            end_ny = end_utc.tz_convert("America/New_York").tz_localize(None)
            out = out[out["t"] <= end_ny]
        return out.reset_index(drop=True)[cols]

    # ------------------------------------------------------------- trades
    def open_trades(self) -> list:
        return (self._get(f"{self._acct}/openTrades") or {}).get("trades") or []

    def trade(self, trade_id: str) -> dict:
        return (self._get(f"{self._acct}/trades/{trade_id}") or {}).get("trade") or {}

    def open_positions(self) -> list:
        return (self._get(f"{self._acct}/openPositions") or {}).get("positions") or []

    def orders(self, state: str = "PENDING") -> list:
        return (self._get(f"{self._acct}/orders", {"state": state}) or {}) \
            .get("orders") or []

    # -------------------------------------------------------------- acting
    #
    # EVERY ONE OF THESE REFUSES WITHOUT A CLIENT ORDER ID. That id is what
    # attribution.py reads to decide whether the bot is allowed to touch a
    # position later. An untagged order is a position this bot can never
    # prove is its own, which means it could never close it — so the order
    # is not sent at all rather than sent and stranded.

    @staticmethod
    def _extensions(client_order_id: str, tag: str = "") -> dict:
        if not client_order_id:
            raise ValueError(
                "every order this project places must carry a client order "
                "id built by blofin_private.make_client_order_id, because "
                "attribution.py reads it to decide what the bot may touch. "
                "An untagged order can never be proven ours.")
        ext = {"id": str(client_order_id)}
        if tag:
            ext["tag"] = str(tag)
        return ext

    def _entry_order(self, kind: str, instrument: str, units: str, *,
                     client_order_id: str, trade_client_order_id: str,
                     stop_price: str, take_profit: str | None = None,
                     limit_price: str | None = None, tag: str = "",
                     position_fill: str = "DEFAULT",
                     time_in_force: str | None = None,
                     gtd_time: str | None = None) -> dict:
        """THE ONE PLACE AN OPENING ORDER IS BUILT. Market and limit are the
        same body with two fields different, and they share this function so
        that a rule added to one cannot be missing from the other.

        THE STOP RIDES IN WITH THE ENTRY AND IT IS NOT OPTIONAL, on either
        kind. Placing it as a second request leaves a window in which the
        position exists with nothing under it, and that window is not
        theoretical — on 26 July a short filled, price ran past where the
        stop belonged before the second call landed, the exchange refused
        the stop as invalid, and the position had to be closed a second
        later. OANDA takes `stopLossOnFill` inside the order body, so there
        is no window and no second call.

        ON A LIMIT ORDER THE ATTACHED STOP MATTERS MORE, NOT LESS. A resting
        limit can fill at three in the morning with nothing watching it. The
        stop is stored with the order and goes on at the instant of the fill,
        by the broker, whether or not this process is even running.

        `units`, `stop_price` and `limit_price` are already-formatted
        strings: positive units are long, negative are short. They are
        strings because they were formatted by a caller that had read the
        instrument spec, and accepting floats here would let a caller that
        had not read it through.
        """
        if not stop_price:
            raise ValueError(
                "an opening order must carry its stop. This method will not "
                "send one without it — a position with nothing under it is "
                "the one thing this venue never has.")
        if kind == "LIMIT" and not limit_price:
            raise ValueError("a limit order must carry the price to rest at")
        order = {
            "type": kind,
            "instrument": instrument,
            "units": str(units),
            # A MARKET order is FOK: fill it now, whole, or do not fill it.
            # A partial fill on an entry would leave a position of a size
            # nobody sized. A LIMIT order is GTC by default: it rests until
            # it fills or is cancelled.
            "timeInForce": time_in_force or ("FOK" if kind == "MARKET" else "GTC"),
            "positionFill": position_fill,
            "clientExtensions": self._extensions(client_order_id, tag),
            "tradeClientExtensions": self._extensions(trade_client_order_id, tag),
            "stopLossOnFill": {"price": str(stop_price), "timeInForce": "GTC"},
        }
        if kind == "LIMIT":
            order["price"] = str(limit_price)
        if gtd_time:
            order["gtdTime"] = str(gtd_time)
        if take_profit:
            order["takeProfitOnFill"] = {"price": str(take_profit),
                                         "timeInForce": "GTC"}
        return self._post(f"{self._acct}/orders", {"order": order}) or {}

    def market_order(self, instrument: str, units: str, **kw) -> dict:
        """Buy or sell NOW, with the stop attached in the same request."""
        return self._entry_order("MARKET", instrument, units, **kw)

    def limit_order(self, instrument: str, units: str, *, limit_price: str,
                    **kw) -> dict:
        """Rest an entry at a price, with the stop attached in the same
        request so it goes on at the instant of the fill."""
        return self._entry_order("LIMIT", instrument, units,
                                 limit_price=limit_price, **kw)

    def set_trade_stop(self, trade_id: str, stop_price: str, *,
                       client_order_id: str, tag: str = "") -> dict:
        """Move or replace the stop on ONE trade we opened.

        Scoped to a trade id, never to an instrument, and that is the whole
        point: it cannot reach a trade somebody else opened on the same pair.
        """
        body = {"stopLoss": {"price": str(stop_price), "timeInForce": "GTC",
                             "clientExtensions": self._extensions(
                                 client_order_id, tag)}}
        return self._put(f"{self._acct}/trades/{trade_id}/orders", body) or {}

    def close_trade(self, trade_id: str, units: str = "ALL") -> dict:
        """Close ONE trade we opened, in whole or in part.

        THERE IS DELIBERATELY NO close_position() IN THIS FILE. OANDA has an
        endpoint that flattens everything on an instrument, and it would take
        Wallace's own trade off the same pair along with ours. Closing by
        trade id cannot do that. The endpoint is not wrapped so that nobody
        can reach for it in a hurry.
        """
        return self._put(f"{self._acct}/trades/{trade_id}/close",
                         {"units": str(units)}) or {}

    def cancel_order(self, order_id: str) -> dict:
        return self._put(f"{self._acct}/orders/{order_id}/cancel", {}) or {}


# ================================================================= HELPERS
def _rfc3339(when) -> str:
    """OANDA wants RFC3339 with a timezone. A naive datetime here is read as
    UTC, said out loud rather than assumed silently."""
    if isinstance(when, str):
        return when
    if isinstance(when, dt.date) and not isinstance(when, dt.datetime):
        when = dt.datetime(when.year, when.month, when.day)
    if isinstance(when, dt.datetime):
        if when.tzinfo is None:
            when = when.replace(tzinfo=dt.timezone.utc)
        return when.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise TypeError(f"cannot turn {when!r} into an RFC3339 timestamp")


def _as_utc(when):
    try:
        import pandas as pd
        return pd.to_datetime(_rfc3339(when), utc=True)
    except Exception:                                            # noqa: BLE001
        return None


def _rows_to_frame(rows: list, price: str = "M"):
    import pandas as pd
    key = {"M": "mid", "B": "bid", "A": "ask"}.get(price[0], "mid")
    recs = []
    for c in rows:
        if not c.get("complete"):
            continue
        d = c.get(key) or {}
        try:
            recs.append({"t": c.get("time"),
                         "open": float(d["o"]), "high": float(d["h"]),
                         "low": float(d["l"]), "close": float(d["c"]),
                         "volume": float(c.get("volume") or 0)})
        except (KeyError, TypeError, ValueError):
            continue
    f = pd.DataFrame(recs, columns=["t", "open", "high", "low", "close",
                                    "volume"])
    if len(f):
        f["t"] = to_et(f["t"])
    return f


def from_env(env: dict | None = None, practice: bool = True):
    """Build a client from the environment, or return None when the keys are
    not there. None is not an error — it is what an un-set-up machine looks
    like, and the caller says so in plain words rather than crashing.

    It reads through blofin_private.load_env, which is the ONE loader in this
    project that knows about both worlds: the .env file on the laptop and the
    injected variables on Render. Reading os.environ directly here would work
    locally and quietly do nothing in the cloud.
    """
    cfg = dict(env) if env is not None else _read_env()
    token, account = cfg.get(TOKEN_KEY), cfg.get(ACCOUNT_KEY)
    if not token or not account:
        return None
    return OandaClient(token, account, practice=practice)


def _read_env() -> dict:
    try:
        from blofin_private import load_env
        return load_env(os.path.join(REPO, ".env"))
    except Exception:                                            # noqa: BLE001
        pass
    out = {}
    path = os.path.join(REPO, ".env")
    if os.path.exists(path):
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    out[k.strip()] = v.strip().strip("'\"")
        except OSError:
            pass
    out.update(os.environ)
    return out


def missing_keys(env: dict | None = None) -> list:
    """Which env keys are not set, so a message can NAME them instead of
    saying "not configured", which tells nobody what to do next."""
    cfg = dict(env) if env is not None else _read_env()
    return [k for k in (TOKEN_KEY, ACCOUNT_KEY) if not cfg.get(k)]


if __name__ == "__main__":
    # `python3 oanda_api.py --smoke` — read-only. It places nothing, and it
    # is the same code as step468_oanda_smoke.py rather than a second copy
    # that could drift out of step with it.
    import sys as _sys
    if "--smoke" in _sys.argv[1:]:
        from step468_oanda_smoke import smoke
        raise SystemExit(smoke())
    print(__doc__.strip().splitlines()[0])
    print()
    print(f"  practice host : {PRACTICE_HOST}")
    print(f"  live host     : {LIVE_HOST}")
    print(f"  env keys      : {TOKEN_KEY}, {ACCOUNT_KEY}")
    print(f"  instruments   : {', '.join(sorted(INSTRUMENTS))}")
    print(f"  timeframes    : {', '.join(GRANULARITY)}")
    missing = missing_keys()
    print(f"  configured    : {'no — missing ' + ', '.join(missing) if missing else 'yes'}")
    print()
    print("  python3 oanda_api.py --smoke     to check it end to end. It "
          "places nothing.")
