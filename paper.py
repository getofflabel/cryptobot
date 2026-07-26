"""
paper.py — OUR OWN PAPER-TRADING ENGINE. It must never flatter us.

WHY THIS EXISTS (2026-07-25)

Wallace: "so cant you just build that tool yourself". He is right. A broker's
demo account had been the blocker all evening and every one of its blocks was
the VENUE's limit, not the METHOD's. Alpaca cannot short crypto — every pair
reports shortable=false — and 190 of the 324 crypto setups the bot found were
shorts. It rejects orders outside stock market hours. It has no currencies at
all. Our own engine removes all of that at once: shorts work, all ten crypto
pairs work, gold works, currencies work. The method gets judged on the method.

This is one implementation of the interface in venue.py, not a simulator
sitting beside the broker. The same call sites drive paper and drive live.


THE FILL RULES. THEY ARE THE WHOLE VALUE OF THIS FILE.

A simulator that fills at a friendly price produces a beautiful week that
does not exist, and then real money gets risked on a fantasy. So:

  1. BUYS FILL AT THE ASK. SELLS FILL AT THE BID. Never the midpoint, never
     the last trade price. The real quote at the moment of the decision. The
     midpoint is computed in exactly one place, for REPORTING what the spread
     cost, and no fill ever uses it.

  2. A STOP FILLS AT THE WORST PRICE IN THE BAR THAT TRIGGERED IT, not at
     the stop level. For a long that is the bar's low; for a short, the
     bar's high. Stops slip, and pretending they do not is the single most
     common way a paper record lies. A bar that GAPS through the stop fills
     at the gap, not at the level.

  3. IF THE STOP AND THE TARGET SIT INSIDE THE SAME BAR and the data cannot
     say which came first, THE STOP HIT. Always. No exceptions, no coin
     flips, no "the open was closer to the target".

  4. THE REAL SPREAD AND ANY REAL COMMISSION ARE CHARGED. Cost is recorded
     for honesty ONLY. Nothing in this file declines, ranks or filters a
     trade on cost. Wallace has ruled on that twice. Search this file for
     `cost` and every hit is arithmetic or a record, never a condition.

  5. NO LOOKAHEAD, EVER. Decide on bar N, fill on bar N+1's opening price or
     on the live quote. A fill offered a bar the decision could not have seen
     is REFUSED, not quietly accepted.

  6. A STALE OR MISSING PRICE MEANS NO FILL AND A RECORDED MISS. A missed
     trade is honest; an invented fill is not. The real reason comes back —
     stale price, no quote, insufficient buying power, lookahead — rather
     than being swallowed into a generic failure. A bid and ask so far apart
     that they are not a market (see MAX_SPREAD_PCT_OF_PRICE) is a miss for
     the same reason. That is a "there is no market here" test, NOT a cost
     filter: nothing anywhere compares a cost against a profit to decide
     whether a trade is worth doing.

SHORTS ARE FIRST-CLASS. A sell with no position opens a short here. That was
the venue's rule, never his.

STATE SURVIVES A RESTART. Positions, resting stops, cash and the fill history
go to disk and reload. The server redeploys; a paper account that forgets its
open positions on every deploy is worthless. Writes are atomic — a temporary
file in the same directory, flushed and fsynced, then os.replace — so a crash
mid-write leaves the previous good state exactly where it was.

EVERYTHING IS RECONSTRUCTIBLE FROM THE FILL LOG ALONE. The log is append-only
JSON lines carrying fills, stop placements and stop cancellations.
`PaperBroker.rebuild_from_log` replays it from the opening balance and must
produce the same cash, the same positions and the same stops as the live
object. test_paper.py asserts exactly that.

STARTING EQUITY IS $100,000, matching the account we have been measuring
against, so the numbers stay comparable.

LANGUAGE. Bot, never book. No bare percentage anywhere: every percentage key
says what it is a percentage of, because a move in the price and a change in
the position's value differ by the leverage between them.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import threading
import uuid

from venue import Venue

REPO = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(REPO, "paper_state.json")
LOG_PATH = os.path.join(REPO, "paper_fills.jsonl")

STARTING_EQUITY = 100_000.0

# How old a quote may be and still be filled against. Ninety seconds is not a
# guess dressed as a rule: our fastest chart is the 1-minute bar, so a quote
# older than a bar and a half is describing a market that has already moved.
MAX_QUOTE_AGE_S = 90.0

# A gap between the bid and the ask this wide is not a market, it is a venue
# telling us it is shut. Measured, not guessed: BTC's real gap is 0.09% of the
# price and SPY's is 0.01% inside the session — but SPY quoted 716.44 by
# 760.82 at 23:00 on a Saturday, a 6% gap, and filling a buy at 760 for
# something worth 738 is not honesty, it is noise. Set to None to fill against
# anything at all.
MAX_SPREAD_PCT_OF_PRICE = 5.0

# A position smaller than this is gone, not a rounding artefact hanging around
# forever and quietly re-triggering stops.
DUST = 1e-12

# ------------------------------------------------------- the refusal reasons
# Real reasons, exposed. A swallowed failure looks exactly like a strategy
# that decided not to trade, and that is the most expensive kind of bug here.
MISS_NO_QUOTE = "no quote: the price source returned nothing for this symbol"
MISS_STALE = "stale price: the newest quote is older than we will fill against"
MISS_CROSSED = "the quote is unusable: bid, ask or both are non-positive or crossed"
MISS_TOO_WIDE = ("the gap between the bid and the ask is too wide to be a real "
                 "market: this venue is shut, not offering us a price")
MISS_NO_SPREAD = ("no measured spread for this symbol: a bar's opening price is "
                  "a midpoint, and filling at it would flatter us")
MISS_LOOKAHEAD = ("lookahead refused: the bar offered for the fill is not after "
                  "the moment of the decision")
MISS_BUYING_POWER = "insufficient buying power for this size"
MISS_NO_POSITION = "no open position in this symbol"
MISS_TOO_BIG = "the close is larger than the open position"
MISS_BAD_QTY = "the quantity is not a positive, finite number"
MISS_BAD_SIDE = "side must be 'buy' or 'sell'"
MISS_BAD_LEVEL = "the stop level is not a positive, finite number"


# ================================================================== PLUMBING
def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _as_utc(ts) -> dt.datetime | None:
    """Anything time-shaped into an aware UTC datetime, or None."""
    if ts is None:
        return None
    if isinstance(ts, dt.datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=dt.timezone.utc)
    if isinstance(ts, (int, float)):
        return dt.datetime.fromtimestamp(float(ts), dt.timezone.utc)
    s = str(ts).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        out = dt.datetime.fromisoformat(s)
    except ValueError:
        try:                                   # pandas Timestamp and friends
            out = dt.datetime.fromisoformat(str(ts)[:26])
        except ValueError:
            return None
    return out if out.tzinfo else out.replace(tzinfo=dt.timezone.utc)


def _iso(ts) -> str | None:
    t = _as_utc(ts)
    return None if t is None else t.isoformat()


def _finite_positive(x) -> bool:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(x) and x > 0


def _atomic_write_json(path: str, obj) -> None:
    """Write so that a crash mid-write cannot corrupt the file.

    The temporary file lives in the SAME directory as the target, because
    os.replace is only atomic within one filesystem. Flush and fsync before
    the replace, or the rename can land ahead of the bytes and leave a
    truncated file that reads as an empty account."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    tmp = os.path.join(d, f".{os.path.basename(path)}.{os.getpid()}.tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2, sort_keys=True, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _bar_fields(bar) -> dict:
    """A bar as a dict, an object with .t/.o/.h/.l/.c, or a pandas row. One
    reader so no caller has to care which shape it holds."""
    if bar is None:
        return {}
    if isinstance(bar, dict):
        g = bar.get
    else:
        def g(k, default=None):
            return getattr(bar, k, default)
    out = {}
    for short, longs in (("t", ("t", "time", "timestamp")),
                         ("o", ("o", "open")), ("h", ("h", "high")),
                         ("l", ("l", "low")), ("c", ("c", "close"))):
        for k in longs:
            v = g(k, None)
            if v is not None:
                out[short] = v
                break
    return out


# ==================================================================== QUOTES
class Quote:
    """One venue quote. The bid and the ask, and when they were taken.

    `mid` exists so a fill's spread cost can be REPORTED. Nothing fills at it.
    """

    __slots__ = ("symbol", "bid", "ask", "ts", "source")

    def __init__(self, symbol, bid, ask, ts=None, source="unknown"):
        self.symbol = symbol
        self.bid = float(bid)
        self.ask = float(ask)
        self.ts = _as_utc(ts) or _utcnow()
        self.source = source

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid + self.ask)

    @property
    def spread(self) -> float:
        return self.ask - self.bid

    @property
    def spread_pct_of_price(self) -> float:
        m = self.mid
        return 100.0 * self.spread / m if m else float("nan")

    def usable(self) -> bool:
        return (math.isfinite(self.bid) and math.isfinite(self.ask)
                and self.bid > 0 and self.ask > 0 and self.ask >= self.bid)

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "bid": self.bid, "ask": self.ask,
                "ts": _iso(self.ts), "source": self.source}

    def __repr__(self):
        return f"Quote({self.symbol} {self.bid}/{self.ask} @{_iso(self.ts)})"


def coerce_quote(symbol: str, q) -> Quote | None:
    """A Quote, a dict from any of our sources, or None."""
    if q is None:
        return None
    if isinstance(q, Quote):
        return q
    if isinstance(q, dict):
        bid = q.get("bid", q.get("bp"))
        ask = q.get("ask", q.get("ap"))
        if bid is None or ask is None:
            return None
        return Quote(symbol, bid, ask, q.get("ts", q.get("t")),
                     q.get("source", "dict"))
    return None


# ---------------------------------------------------- THE ONE PRICE FUNCTION
#
# Every price the engine fills against comes through here, so adding a
# currency feed later is one branch in one function and touches nothing else.
def live_quotes(symbols, client=None) -> dict:
    """{symbol: Quote} for whatever we can get. Missing symbols are simply
    absent — the engine turns an absence into a recorded miss, which is the
    honest outcome, rather than inventing a price.

    Crypto and stocks come from Alpaca's data API, which is free and which we
    can read WITHOUT trading through it. Currencies have no feed here yet and
    say so rather than returning something wrong.
    """
    if isinstance(symbols, str):
        symbols = [symbols]
    symbols = list(symbols)
    if not symbols:
        return {}

    crypto = [s for s in symbols if "/" in s]
    stocks = [s for s in symbols if "/" not in s]
    out: dict[str, Quote] = {}

    if client is None:
        import alpaca
        client = alpaca.from_env()
    if client is None:
        return out                     # no keys is no quotes, not a fake price

    if crypto:
        try:
            got = client.crypto_latest_quotes(crypto) or {}
            for sym, q in got.items():
                if q.get("bp") and q.get("ap"):
                    out[sym] = Quote(sym, q["bp"], q["ap"], q.get("t"),
                                     "alpaca-crypto")
        except Exception as e:                    # noqa: BLE001
            print(f"  crypto quotes unavailable: {str(e)[:120]}")
    if stocks:
        for sym in stocks:
            try:
                got = client._get(f"/v2/stocks/{sym}/quotes/latest",
                                  base="https://data.alpaca.markets") or {}
                q = got.get("quote") or {}
                if q.get("bp") and q.get("ap"):
                    out[sym] = Quote(sym, q["bp"], q["ap"], q.get("t"),
                                     "alpaca-stocks")
            except Exception as e:                # noqa: BLE001
                print(f"  quote unavailable for {sym}: {str(e)[:120]}")
    return out


def load_measured_spreads(path: str | None = None) -> dict:
    """The spreads this repo already MEASURED, per symbol, as a fraction of
    price. Used only when a fill has to come off a bar's opening price, where
    there is no bid and ask to take the far side of. Measured, never guessed.
    """
    out: dict[str, float] = {}
    for p in ([path] if path else
              [os.path.join(REPO, "step442_derived_thresholds.json"),
               os.path.join(REPO, "step443_gold_thresholds.json"),
               os.path.join(REPO, "step443_forex_thresholds.json")]):
        try:
            with open(p) as f:
                got = json.load(f)
        except (OSError, ValueError):
            continue
        for sym, row in (got or {}).items():
            if isinstance(row, dict) and row.get("spread_pct"):
                out[sym] = float(row["spread_pct"])
    return out


# ============================================================== THE ENGINE
class PaperBroker(Venue):
    """Our paper venue. Fills, stops, shorts, cash, and an audit trail.

    Signs: `qty` is always positive in a call and SIGNED in a position. A
    short is a negative quantity. Cash rises when a short is opened and falls
    when it is covered, which is what actually happens.
    """

    name = "paper"
    is_real_money = False

    def __init__(self, state_path: str | None = STATE_PATH,
                 log_path: str | None = LOG_PATH,
                 starting_equity: float = STARTING_EQUITY,
                 quotes=None,
                 now=None,
                 max_quote_age_s: float = MAX_QUOTE_AGE_S,
                 max_spread_pct_of_price: float | None = MAX_SPREAD_PCT_OF_PRICE,
                 commission_pct: float = 0.0,
                 spread_pct=None,
                 leverage: float = 1.0,
                 venue_label: str = "paper",
                 load: bool = True):
        """
        quotes        : callable(list_of_symbols) -> {symbol: Quote}. Defaults
                        to live_quotes. Injectable, which is how the tests
                        prove the fill rules without a network.
        now           : callable() -> aware UTC datetime. Injectable for the
                        same reason.
        commission_pct: fraction of notional, per side. Recorded, never a
                        condition.
        spread_pct    : {symbol: fraction of price} or one float, for the
                        bar-driven path only. Absent for a symbol means the
                        bar-driven fill is REFUSED rather than filled at a
                        midpoint.
        leverage      : buying power as a multiple of equity. 1.0 is cash.
        """
        self.state_path = state_path
        self.log_path = log_path
        self.starting_equity = float(starting_equity)
        self.quotes_fn = quotes if quotes is not None else live_quotes
        self.now_fn = now if now is not None else _utcnow
        self.max_quote_age_s = float(max_quote_age_s)
        self.max_spread_pct_of_price = (None if max_spread_pct_of_price is None
                                        else float(max_spread_pct_of_price))
        self.commission_pct = float(commission_pct)
        self.leverage = float(leverage)
        self.venue_label = venue_label
        if spread_pct is None:
            spread_pct = load_measured_spreads()
        self.spread_pct = (spread_pct if isinstance(spread_pct, dict)
                           else {"*": float(spread_pct)})

        self._lock = threading.RLock()
        self.cash = self.starting_equity
        self.realised = 0.0
        self._pos: dict[str, dict] = {}
        self._orders: list[dict] = []
        self._fills: list[dict] = []
        self._marks: dict[str, dict] = {}
        self.opened_at = _iso(self.now_fn())

        loaded = False
        if load and state_path and os.path.exists(state_path):
            loaded = self._load()
        if not loaded:
            self._log_event({"event": "account_opened",
                             "starting_equity": self.starting_equity,
                             "venue": self.venue_label,
                             "ts": self.opened_at})
            self._save()

    # -------------------------------------------------------------- helpers
    def _ts(self) -> dt.datetime:
        return self.now_fn()

    def _spread_for(self, symbol: str) -> float | None:
        v = self.spread_pct.get(symbol, self.spread_pct.get("*"))
        return None if v is None else float(v)

    def _get_quote(self, symbol: str, quote=None) -> tuple[Quote | None, str]:
        """The quote and, when there is not a usable one, the real reason."""
        q = coerce_quote(symbol, quote)
        if q is None:
            try:
                got = self.quotes_fn([symbol]) or {}
            except Exception as e:                # noqa: BLE001
                return None, f"{MISS_NO_QUOTE} ({str(e)[:120]})"
            q = coerce_quote(symbol, got.get(symbol))
        if q is None:
            return None, MISS_NO_QUOTE
        if not q.usable():
            return None, f"{MISS_CROSSED} (bid {q.bid}, ask {q.ask})"
        age = (self._ts() - q.ts).total_seconds()
        if age > self.max_quote_age_s:
            return None, (f"{MISS_STALE}: {age:.0f} seconds old, and we will "
                          f"not fill against anything older than "
                          f"{self.max_quote_age_s:.0f}")
        wide = self.max_spread_pct_of_price
        if wide is not None and q.spread_pct_of_price > wide:
            return None, (f"{MISS_TOO_WIDE}: the gap is "
                          f"{q.spread_pct_of_price:.2f}% of the price "
                          f"({q.bid} by {q.ask}), past the {wide:.2f}% we will "
                          f"deal inside")
        return q, ""

    # -------------------------------------------------------- marks and math
    def mark(self, symbol: str) -> dict | None:
        """What one unit is worth to US right now: a long marks at the BID
        (what selling it would get) and a short at the ASK (what covering it
        would cost). Marking at the midpoint would show an unrealised profit
        that half a spread of it does not exist."""
        return self._marks.get(symbol)

    def refresh_marks(self, symbols=None) -> dict:
        """Pull fresh quotes for the open positions and mark them the
        conservative way. Returns which symbols could NOT be freshly marked,
        so a stale equity number is visible rather than assumed."""
        syms = list(symbols if symbols is not None else self._pos.keys())
        if not syms:
            return {"marked": [], "stale": []}
        try:
            got = self.quotes_fn(syms) or {}
        except Exception as e:                    # noqa: BLE001
            print(f"  marks unavailable: {str(e)[:120]}")
            got = {}
        marked, stale = [], []
        for sym in syms:
            q = coerce_quote(sym, got.get(sym))
            pos = self._pos.get(sym)
            if q is None or not q.usable():
                stale.append(sym)
                continue
            long = (pos or {}).get("qty", 0.0) >= 0
            self._marks[sym] = {"price": q.bid if long else q.ask,
                                "basis": "bid (a long marks at what selling gets)"
                                         if long else
                                         "ask (a short marks at what covering costs)",
                                "ts": _iso(q.ts), "source": q.source,
                                "bid": q.bid, "ask": q.ask}
            marked.append(sym)
        return {"marked": marked, "stale": stale}

    def _mark_price(self, symbol: str) -> tuple[float, bool]:
        """(price, is_fresh_enough). Falls back to the last fill price and
        says so rather than pretending."""
        m = self._marks.get(symbol)
        if not m:
            pos = self._pos.get(symbol)
            return (float(pos["avg_entry"]) if pos else 0.0), False
        ts = _as_utc(m.get("ts"))
        fresh = ts is not None and (self._ts() - ts).total_seconds() <= self.max_quote_age_s
        return float(m["price"]), fresh

    def _gross_exposure(self) -> float:
        tot = 0.0
        for sym, p in self._pos.items():
            px, _ = self._mark_price(sym)
            tot += abs(p["qty"]) * px
        return tot

    def equity(self) -> float:
        eq = self.cash
        for sym, p in self._pos.items():
            px, _ = self._mark_price(sym)
            eq += p["qty"] * px          # signed: a short's market value is negative
        return eq

    def buying_power(self) -> float:
        return max(0.0, self.equity() * self.leverage - self._gross_exposure())

    def open_risk(self) -> dict:
        """Dollars at risk if EVERY resting stop filled AT ITS LEVEL.

        The real number is worse, because rule 2 of this file says stops fill
        at the worst price in the triggering bar. The key name says `level`
        and this note says the rest, so nobody reads it as a floor."""
        at_level, unprotected = 0.0, []
        for sym, p in self._pos.items():
            if p.get("stop") is None:
                unprotected.append(sym)
                continue
            at_level += abs(p["avg_entry"] - float(p["stop"])) * abs(p["qty"])
        return {"dollars_if_stops_fill_at_their_level": round(at_level, 6),
                "unprotected_positions": unprotected,
                "note": "stops fill at the worst price in the bar that "
                        "triggers them, so the real loss is worse than this"}

    # --------------------------------------------------------- the interface
    def account(self, refresh: bool = True) -> dict:
        with self._lock:
            stale = []
            if refresh and self._pos:
                stale = self.refresh_marks().get("stale", [])
            eq = self.equity()
            risk = self.open_risk()
            unreal = sum(p["qty"] * self._mark_price(s)[0] - p["qty"] * p["avg_entry"]
                         for s, p in self._pos.items())
            return {
                "venue": self.venue_label,
                "real_money": self.is_real_money,
                "equity": round(eq, 6),
                "cash": round(self.cash, 6),
                "buying_power": round(self.buying_power(), 6),
                "open_risk": risk["dollars_if_stops_fill_at_their_level"],
                "open_risk_detail": risk,
                "gross_exposure": round(self._gross_exposure(), 6),
                "realised_pnl": round(self.realised, 6),
                "unrealised_pnl": round(unreal, 6),
                "starting_equity": self.starting_equity,
                "profit_since_opening": round(eq - self.starting_equity, 6),
                "change_in_account_value_pct": round(
                    100.0 * (eq - self.starting_equity) / self.starting_equity, 6)
                if self.starting_equity else 0.0,
                "open_positions": len(self._pos),
                "symbols_we_could_not_mark_freshly": stale,
                "fills": len(self._fills),
                "misses": len([o for o in self._orders
                               if o.get("status") == "rejected"]),
            }

    def positions(self, refresh: bool = True) -> list:
        with self._lock:
            if refresh and self._pos:
                self.refresh_marks()
            out = []
            for sym in sorted(self._pos):
                out.append(self._position_view(sym))
            return out

    def position(self, symbol: str, refresh: bool = False) -> dict | None:
        with self._lock:
            if symbol not in self._pos:
                return None
            if refresh:
                self.refresh_marks([symbol])
            return self._position_view(symbol)

    def _position_view(self, symbol: str) -> dict:
        p = self._pos[symbol]
        px, fresh = self._mark_price(symbol)
        value = p["qty"] * px
        unreal = value - p["qty"] * p["avg_entry"]
        entry_notional = abs(p["qty"]) * p["avg_entry"]
        return {
            "venue": self.venue_label,
            "symbol": symbol,
            "qty": p["qty"],                      # signed: negative is short
            "direction": 1 if p["qty"] > 0 else -1,
            "side": "long" if p["qty"] > 0 else "short",
            "avg_entry": p["avg_entry"],
            "original_qty": p.get("original_qty", abs(p["qty"])),
            "stop": p.get("stop"),
            "stop_placed_at": p.get("stop_placed_at"),
            "opened_at": p.get("opened_at"),
            "mark": px,
            "mark_is_fresh": fresh,
            "mark_basis": (self._marks.get(symbol) or {}).get("basis",
                                                             "last fill price"),
            "market_value": round(value, 6),
            "unrealised_pnl": round(unreal, 6),
            "change_in_position_value_pct": round(100.0 * unreal / entry_notional, 6)
            if entry_notional else 0.0,
            "realised_pnl_on_this_symbol": round(p.get("realised", 0.0), 6),
            "costs_charged_so_far": round(p.get("costs", 0.0), 6),
        }

    # ----------------------------------------------------------- order entry
    def market_order(self, symbol: str, side: str, qty: float, *,
                     decided_at=None, next_bar=None, quote=None,
                     reason: str = "", client_order_id: str | None = None,
                     kind: str = "market") -> dict:
        """Buy or sell now. A SELL WITH NO POSITION IS A SHORT.

        Exactly one of two price paths runs:
          live quote  — buy fills at the ask, sell fills at the bid.
          next_bar    — the fill comes off bar N+1's OPEN with half the
                        measured spread added for a buy and taken off for a
                        sell, and only if that bar is strictly after
                        `decided_at`. This is the backtest-shaped path and it
                        is where lookahead would otherwise creep in.
        """
        with self._lock:
            if side not in ("buy", "sell"):
                return self._reject(symbol, side, qty, MISS_BAD_SIDE, reason, kind)
            if not _finite_positive(qty):
                return self._reject(symbol, side, qty, MISS_BAD_QTY, reason, kind)
            qty = float(qty)

            price, basis, why, used = self._fill_price(symbol, side, quote=quote,
                                                       next_bar=next_bar,
                                                       decided_at=decided_at)
            if price is None:
                return self._reject(symbol, side, qty, why, reason, kind)

            # Buying power is checked ONLY when the order increases exposure.
            # Closing must never be blocked by it — a position we cannot exit
            # is how a paper account turns into a fantasy.
            old = self._pos.get(symbol, {}).get("qty", 0.0)
            new = old + (qty if side == "buy" else -qty)
            added = (abs(new) - abs(old)) * price
            if added > 0 and added > self.buying_power() + 1e-9:
                return self._reject(
                    symbol, side, qty,
                    f"{MISS_BUYING_POWER}: it needs ${added:,.2f} and there is "
                    f"${self.buying_power():,.2f}", reason, kind)

            return self._fill(symbol, side, qty, price, basis, kind, reason,
                              client_order_id=client_order_id, quote=used)

    def _fill_price(self, symbol: str, side: str, quote=None, next_bar=None,
                    decided_at=None):
        """(price, basis, why_not, quote_used). The ONLY place in this engine
        where a fill price is chosen. Every rule that stops us flattering
        ourselves on entry lives in these thirty lines."""
        if next_bar is not None:
            b = _bar_fields(next_bar)
            if "o" not in b:
                return None, "", "the bar offered for the fill has no opening price", None
            bt = _as_utc(b.get("t"))
            d = _as_utc(decided_at)
            if d is not None:
                if bt is None:
                    return None, "", (f"{MISS_LOOKAHEAD}: the bar has no "
                                      f"timestamp, so it cannot be shown to be "
                                      f"after the decision"), None
                if bt <= d:
                    return None, "", (f"{MISS_LOOKAHEAD}: the bar opens at "
                                      f"{_iso(bt)} and the decision was made at "
                                      f"{_iso(d)}"), None
            sp = self._spread_for(symbol)
            if sp is None:
                return None, "", f"{MISS_NO_SPREAD} ({symbol})", None
            o = float(b["o"])
            half = 0.5 * sp
            # The bar's open is a midpoint. Buying at it would hand us half a
            # spread we never had, on every single trade.
            synthetic = Quote(symbol, o * (1.0 - half), o * (1.0 + half),
                              bt, "bar open plus the measured spread")
            if side == "buy":
                return (synthetic.ask,
                        "the next bar's open plus half the measured spread, "
                        "because a buy pays the ask", "", synthetic)
            return (synthetic.bid,
                    "the next bar's open minus half the measured spread, "
                    "because a sell receives the bid", "", synthetic)

        q, why = self._get_quote(symbol, quote)
        if q is None:
            return None, "", why, None
        if side == "buy":
            return q.ask, "the ask, because a buy pays the ask", "", q
        return q.bid, "the bid, because a sell receives the bid", "", q

    # ------------------------------------------------------------- the fill
    def _fill(self, symbol, side, qty, price, basis, kind, reason,
              client_order_id=None, quote=None, extra=None) -> dict:
        ts = self._ts()
        signed = qty if side == "buy" else -qty
        pos = self._pos.get(symbol)
        old_qty = pos["qty"] if pos else 0.0
        old_entry = pos["avg_entry"] if pos else 0.0
        new_qty = old_qty + signed

        realised_now = 0.0
        if old_qty and (old_qty > 0) != (signed > 0):
            closed = min(abs(signed), abs(old_qty))
            realised_now = closed * (price - old_entry) * (1 if old_qty > 0 else -1)

        # COST. Recorded, charged, and never a condition on anything.
        commission = abs(qty * price) * self.commission_pct
        q = coerce_quote(symbol, quote) if quote is not None else None
        spread_cost = abs(price - q.mid) * qty if (q is not None and q.usable()) else None

        self.cash -= signed * price
        self.cash -= commission
        self.realised += realised_now - commission

        if abs(new_qty) <= DUST:
            if pos:
                pos_realised = pos.get("realised", 0.0) + realised_now
                pos_costs = pos.get("costs", 0.0) + commission
            else:
                pos_realised, pos_costs = realised_now, commission
            self._pos.pop(symbol, None)
            new_entry = 0.0
        else:
            if pos is None:
                new_entry = price
                pos = {"symbol": symbol, "qty": 0.0, "avg_entry": price,
                       "opened_at": _iso(ts), "stop": None,
                       "stop_placed_at": None, "realised": 0.0, "costs": 0.0,
                       "original_qty": abs(new_qty)}
                self._pos[symbol] = pos
            elif (old_qty > 0) == (new_qty > 0) and abs(new_qty) > abs(old_qty):
                # adding to the same side: weighted average
                new_entry = (abs(old_qty) * old_entry + qty * price) / abs(new_qty)
            elif (old_qty > 0) != (new_qty > 0):
                new_entry = price            # flipped through zero: fresh entry
                pos["opened_at"] = _iso(ts)
                pos["stop"] = None           # the old stop protected the old side
                pos["stop_placed_at"] = None
                pos["original_qty"] = abs(new_qty)
            else:
                new_entry = old_entry        # reducing: the entry does not move
            pos["qty"] = new_qty
            pos["avg_entry"] = new_entry
            pos["realised"] = pos.get("realised", 0.0) + realised_now
            pos["costs"] = pos.get("costs", 0.0) + commission
            if abs(new_qty) > pos.get("original_qty", 0.0):
                pos["original_qty"] = abs(new_qty)
            pos_realised = pos["realised"]
            pos_costs = pos["costs"]

        self._marks[symbol] = {"price": price, "basis": "last fill price",
                               "ts": _iso(ts), "source": "fill"}

        rec = {
            "event": "fill",
            "id": client_order_id or uuid.uuid4().hex[:16],
            "ts": _iso(ts),
            "venue": self.venue_label,
            "real_money": self.is_real_money,
            "status": "filled",
            "kind": kind,
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "price_basis": basis,
            "commission": round(commission, 10),
            "spread_cost": None if spread_cost is None else round(spread_cost, 10),
            "cost_note": "recorded for honesty. Nothing in this engine "
                         "declines, ranks or filters a trade on cost.",
            "reason": reason,
            "realised_on_this_fill": round(realised_now, 10),
            "cash_after": round(self.cash, 10),
            "qty_after": round(new_qty, 12),
            "avg_entry_after": round(new_entry, 10),
            "position_realised_after": round(pos_realised, 10),
            "position_costs_after": round(pos_costs, 10),
        }
        if extra:
            rec.update(extra)
        self._fills.append(rec)
        self._orders.append(rec)
        self._log_event(rec)
        self._save()
        return rec

    def _reject(self, symbol, side, qty, why, note="", kind="market",
                extra=None) -> dict:
        rec = {"event": "miss", "id": uuid.uuid4().hex[:16], "ts": _iso(self._ts()),
               "venue": self.venue_label, "real_money": self.is_real_money,
               "status": "rejected", "kind": kind, "symbol": symbol,
               "side": side, "qty": qty, "reason": why, "note": note,
               "price": None}
        if extra:
            rec.update(extra)
        self._orders.append(rec)
        self._log_event(rec)
        return rec

    # ------------------------------------------------------------- the stop
    def place_stop(self, symbol: str, level: float, *, reason: str = "") -> dict:
        """A resting stop on an open position, checked on every bar handed to
        on_bar. It protects whatever is STILL open, so a partial close leaves
        it covering the runner without any further call."""
        with self._lock:
            pos = self._pos.get(symbol)
            if pos is None:
                return self._reject(symbol, None, None, MISS_NO_POSITION,
                                    reason, "stop")
            if not _finite_positive(level):
                return self._reject(symbol, None, None, MISS_BAD_LEVEL,
                                    reason, "stop")
            level = float(level)
            side_note = ("below the price for a long" if pos["qty"] > 0
                         else "above the price for a short")
            pos["stop"] = level
            pos["stop_placed_at"] = _iso(self._ts())
            rec = {"event": "stop_placed", "id": uuid.uuid4().hex[:16],
                   "ts": pos["stop_placed_at"], "venue": self.venue_label,
                   "real_money": self.is_real_money, "status": "placed",
                   "kind": "stop", "symbol": symbol, "level": level,
                   "protects_qty": pos["qty"], "side_note": side_note,
                   "reason": reason,
                   "fill_note": "when it triggers it fills at the worst price "
                                "in the bar that triggered it, not at this level"}
            self._orders.append(rec)
            self._log_event(rec)
            self._save()
            return rec

    def cancel_stop(self, symbol: str, *, reason: str = "") -> dict:
        with self._lock:
            pos = self._pos.get(symbol)
            if pos is None or pos.get("stop") is None:
                return self._reject(symbol, None, None,
                                    "there is no resting stop to cancel",
                                    reason, "stop")
            level = pos["stop"]
            pos["stop"] = None
            pos["stop_placed_at"] = None
            rec = {"event": "stop_cancelled", "id": uuid.uuid4().hex[:16],
                   "ts": _iso(self._ts()), "venue": self.venue_label,
                   "status": "cancelled", "kind": "stop", "symbol": symbol,
                   "level": level, "reason": reason}
            self._orders.append(rec)
            self._log_event(rec)
            self._save()
            return rec

    # ---------------------------------------------------------- closing out
    def close_position(self, symbol: str, qty: float | None = None, *,
                       decided_at=None, next_bar=None, quote=None,
                       reason: str = "close") -> dict:
        """All of it, or part of it. Partial is first-class: the method takes
        half off at the first target and moves the stop to break even, so a
        position is not a single lump."""
        with self._lock:
            pos = self._pos.get(symbol)
            if pos is None:
                return self._reject(symbol, None, qty, MISS_NO_POSITION,
                                    reason, "close")
            open_qty = abs(pos["qty"])
            want = open_qty if qty is None else float(qty)
            if not _finite_positive(want):
                return self._reject(symbol, None, qty, MISS_BAD_QTY, reason, "close")
            if want > open_qty + 1e-9:
                return self._reject(
                    symbol, None, want,
                    f"{MISS_TOO_BIG}: {want} against {open_qty} open",
                    reason, "close")
            want = min(want, open_qty)
            side = "sell" if pos["qty"] > 0 else "buy"
            return self.market_order(symbol, side, want, decided_at=decided_at,
                                     next_bar=next_bar, quote=quote,
                                     reason=reason, kind="close")

    # -------------------------------------------------- the bar-by-bar check
    def on_bar(self, symbol: str, bar, target: float | None = None) -> dict:
        """What this closed bar does to the position. Call it on every bar.

        RULE 2. A triggered stop fills at the WORST price in this bar — the
        low for a long, the high for a short — not at the stop level. A bar
        that gapped straight through fills at the gap.

        RULE 3. If the stop AND the target are both inside this bar, the STOP
        HIT. A 1-minute bar does not record the order of the ticks inside it,
        so the only honest reading is the one that costs us money.

        Returns {"action": "hold" | "stopped" | "target_touched", ...}. A
        target touch is REPORTED, not filled: how much comes off at a target
        is the method's decision, and it makes it by calling close_position.
        """
        with self._lock:
            pos = self._pos.get(symbol)
            if pos is None:
                return {"action": "hold", "reason": MISS_NO_POSITION}
            b = _bar_fields(bar)
            if not {"h", "l"} <= set(b):
                return {"action": "hold",
                        "reason": "the bar has no high and low to check against"}
            high, low = float(b["h"]), float(b["l"])
            long = pos["qty"] > 0
            stop = pos.get("stop")

            stop_hit = stop is not None and ((low <= stop) if long else (high >= stop))
            target_hit = target is not None and (
                (high >= target) if long else (low <= target))

            if stop_hit:
                # min/max rather than a bare low/high so the intent is on the
                # page: never better than the level, and worse when the bar was.
                fill = min(stop, low) if long else max(stop, high)
                why = "stopped out"
                if target_hit:
                    why = ("stopped out — the target was inside this bar too, "
                           "and the tie goes to the stop because the data "
                           "cannot say which came first")
                rec = self._fill(symbol, "sell" if long else "buy",
                                 abs(pos["qty"]), fill,
                                 "the worst price in the bar that triggered the "
                                 "stop, not the stop level", "stop", why,
                                 extra={"stop_level": stop,
                                        "bar_t": _iso(b.get("t")),
                                        "slippage_versus_the_stop_level":
                                            round(abs(fill - stop), 10),
                                        "target_also_in_this_bar": bool(target_hit)})
                return {"action": "stopped", "fill": rec, "price": fill,
                        "stop_level": stop, "reason": why,
                        "target_also_in_this_bar": bool(target_hit)}

            if target_hit:
                return {"action": "target_touched", "symbol": symbol,
                        "target": target, "bar_t": _iso(b.get("t")),
                        "reason": "the target was reached in this bar and the "
                                  "stop was not. How much comes off is the "
                                  "method's call, not the venue's."}
            return {"action": "hold"}

    def on_bars(self, bars: dict, targets: dict | None = None) -> dict:
        """on_bar for a whole set of symbols. {symbol: result}."""
        targets = targets or {}
        return {sym: self.on_bar(sym, bar, targets.get(sym))
                for sym, bar in bars.items()}

    # ------------------------------------------------------- the audit trail
    def orders(self) -> list:
        return list(self._orders)

    def fills(self) -> list:
        return list(self._fills)

    def misses(self) -> list:
        return [o for o in self._orders if o.get("status") == "rejected"]

    # ------------------------------------------------------------- the disk
    def _state(self) -> dict:
        return {"schema": 1,
                "venue": self.venue_label,
                "real_money": self.is_real_money,
                "starting_equity": self.starting_equity,
                "opened_at": self.opened_at,
                "cash": self.cash,
                "realised": self.realised,
                "positions": self._pos,
                "marks": self._marks,
                # The last 2000 only, so a long paper run does not turn every
                # save into a rewrite of the whole history. This is the
                # CONVENIENCE copy. The append-only fill log is the complete
                # record and the one everything is reconstructed from.
                "orders": self._orders[-2000:],
                "saved_at": _iso(self._ts())}

    def _save(self) -> None:
        if not self.state_path:
            return
        _atomic_write_json(self.state_path, self._state())

    def _load(self) -> bool:
        """Read the state back. A MISSING file is a fresh account. An
        UNREADABLE one is not — it raises, because silently resetting to
        $100,000 would erase open positions and print a beautiful week that
        never happened. The fill log is the recovery path; see
        rebuild_from_log."""
        try:
            with open(self.state_path) as f:
                s = json.load(f)
        except (OSError, ValueError) as e:
            raise RuntimeError(
                f"{self.state_path} is unreadable ({str(e)[:120]}). NOT "
                f"resetting the account — rebuild it from the fill log with "
                f"PaperBroker.rebuild_from_log({self.log_path!r}).") from None
        self.starting_equity = float(s.get("starting_equity", self.starting_equity))
        self.opened_at = s.get("opened_at", self.opened_at)
        self.cash = float(s.get("cash", self.starting_equity))
        self.realised = float(s.get("realised", 0.0))
        self._pos = {k: dict(v) for k, v in (s.get("positions") or {}).items()}
        self._marks = {k: dict(v) for k, v in (s.get("marks") or {}).items()}
        self._orders = list(s.get("orders") or [])
        self._fills = [o for o in self._orders if o.get("event") == "fill"]
        return True

    def _log_event(self, rec: dict) -> None:
        """Append-only. This is the record everything else is reconstructible
        from, so it is written before the state file and never rewritten."""
        if not self.log_path:
            return
        d = os.path.dirname(os.path.abspath(self.log_path)) or "."
        os.makedirs(d, exist_ok=True)
        with open(self.log_path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
            f.flush()
            os.fsync(f.fileno())

    # ---------------------------------------------- rebuild from the log only
    @classmethod
    def rebuild_from_log(cls, log_path: str = LOG_PATH,
                         starting_equity: float | None = None,
                         **kwargs):
        """Replay the log and nothing else. THE TEST OF THIS ENGINE: the
        object this returns must have the same cash, the same positions and
        the same stops as the live one. If it does not, the log is not a
        complete record and the paper week is not evidence."""
        b = cls(state_path=None, log_path=None,
                starting_equity=starting_equity or STARTING_EQUITY,
                load=False, **kwargs)
        try:
            with open(log_path) as f:
                lines = f.readlines()
        except OSError:
            return b
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue                 # a torn last line is skipped, not fatal
            ev = rec.get("event")
            if ev == "account_opened" and starting_equity is None:
                b.starting_equity = float(rec.get("starting_equity",
                                                  b.starting_equity))
                b.cash = b.starting_equity
                b.opened_at = rec.get("ts", b.opened_at)
            elif ev == "fill":
                b._replay_fill(rec)
            elif ev == "stop_placed":
                p = b._pos.get(rec["symbol"])
                if p is not None:
                    p["stop"] = float(rec["level"])
                    p["stop_placed_at"] = rec.get("ts")
            elif ev == "stop_cancelled":
                p = b._pos.get(rec["symbol"])
                if p is not None:
                    p["stop"] = None
                    p["stop_placed_at"] = None
        return b

    def _replay_fill(self, rec: dict) -> None:
        """The same arithmetic as _fill, driven by the record rather than by a
        quote. Deliberately a separate short function: it must depend on
        NOTHING except what is written in the log line."""
        symbol, side = rec["symbol"], rec["side"]
        qty, price = float(rec["qty"]), float(rec["price"])
        commission = float(rec.get("commission") or 0.0)
        signed = qty if side == "buy" else -qty
        pos = self._pos.get(symbol)
        old_qty = pos["qty"] if pos else 0.0
        old_entry = pos["avg_entry"] if pos else 0.0
        new_qty = old_qty + signed
        realised_now = 0.0
        if old_qty and (old_qty > 0) != (signed > 0):
            closed = min(abs(signed), abs(old_qty))
            realised_now = closed * (price - old_entry) * (1 if old_qty > 0 else -1)
        self.cash -= signed * price + commission
        self.realised += realised_now - commission
        if abs(new_qty) <= DUST:
            self._pos.pop(symbol, None)
        else:
            if pos is None:
                pos = {"symbol": symbol, "qty": 0.0, "avg_entry": price,
                       "opened_at": rec.get("ts"), "stop": None,
                       "stop_placed_at": None, "realised": 0.0, "costs": 0.0,
                       "original_qty": abs(new_qty)}
                self._pos[symbol] = pos
                entry = price
            elif (old_qty > 0) == (new_qty > 0) and abs(new_qty) > abs(old_qty):
                entry = (abs(old_qty) * old_entry + qty * price) / abs(new_qty)
            elif (old_qty > 0) != (new_qty > 0):
                entry = price
                pos["stop"] = None
                pos["stop_placed_at"] = None
                pos["original_qty"] = abs(new_qty)
            else:
                entry = old_entry
            pos["qty"] = new_qty
            pos["avg_entry"] = entry
            pos["realised"] = pos.get("realised", 0.0) + realised_now
            pos["costs"] = pos.get("costs", 0.0) + commission
            if abs(new_qty) > pos.get("original_qty", 0.0):
                pos["original_qty"] = abs(new_qty)
        self._marks[symbol] = {"price": price, "basis": "last fill price",
                               "ts": rec.get("ts"), "source": "fill"}
        self._fills.append(rec)
        self._orders.append(rec)


def from_env(**kwargs) -> PaperBroker:
    """The engine with this repo's defaults. Kept for symmetry with
    alpaca.from_env so the two are swapped by name and nothing else."""
    return PaperBroker(**kwargs)


if __name__ == "__main__":
    b = PaperBroker(state_path=None, log_path=None,
                    quotes=lambda syms: {})
    print(json.dumps(b.account(refresh=False), indent=2))
