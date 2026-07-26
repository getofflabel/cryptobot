"""
venue.py — ONE INTERFACE, MANY VENUES. The bot never learns which one.

WHY THIS FILE EXISTS (2026-07-25)

Wallace: "this build has to be able to work when we switch to real trading
too, so basically you are building alpaca but it works for everything."

So the paper engine is not a simulator bolted on beside the broker. It is
ONE IMPLEMENTATION of the interface below, and the real venues are others.
Switching venue is a config value and nothing else.

    paper          our own engine (paper.py) — fills, stops, shorts, state
    alpaca-paper   Alpaca's paper host, through the existing alpaca.py
    alert          places nothing; messages Wallace the trade and keeps the
                   record as if filled, so a market we cannot trade
                   programmatically is just another implementation instead of
                   a special case threaded through the strategy
    <crypto>       whatever venue ends up handling crypto shorts (later)

THE POINT, WHICH IS BIGGER THAN IT LOOKS
A week of paper trading is only evidence if THE CODE THAT RUNS ON PAPER IS
THE CODE THAT RUNS LIVE. If going real means a rewrite, the paper week
tested something else. Same call sites, same order flow, same stop handling,
same position tracking. Only the thing at the bottom changes.

    NO BRANCH IN tjr_bot.py, tjr_crypto.py, tjr_gold.py OR tjr_forex.py MAY
    NAME A VENUE. If the strategy has to know where it is trading, the
    abstraction is wrong and the fix belongs here, not there.

THE REAL-MONEY GUARD
Real money has to be impossible to reach by accident. Today a bot in this
project already placed trades on an account it should not have touched. So:

  1. The venue DEFAULTS TO PAPER. Absent config, unreadable config, a
     misspelled name, a name we do not know — every one of those resolves to
     paper. There is no path where confusion resolves to real money.
  2. A real-money venue additionally requires an exact confirmation phrase
     that can only have been typed on purpose. Not a truthy value, not a 1,
     not "true". The literal string in LIVE_CONFIRM_PHRASE.
  3. resolve() records WHY it chose what it chose, and announce() prints it
     as a banner nobody can miss in a deploy log and pushes it to Telegram.
  4. Every order record carries the venue name, so a fill log can never be
     ambiguous about whether the money was real.

Nothing in this file places an order by itself.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

REPO = os.path.dirname(os.path.abspath(__file__))

# The config keys, in the order they are consulted.
VENUE_KEYS = ("CRYPTOBOT_VENUE", "VENUE")

# The one string that unlocks a real-money venue. Deliberately unguessable by
# accident and impossible to arrive at from a default, a flag or a "1".
LIVE_CONFIRM_KEY = "CRYPTOBOT_REAL_MONEY"
LIVE_CONFIRM_PHRASE = "yes-trade-real-money"

DEFAULT_VENUE = "paper"


# ============================================================ THE INTERFACE
class Venue(ABC):
    """What every venue must be able to do. Seven calls, one vocabulary.

    Implementations must set `name` and `is_real_money`. `is_real_money` is
    read by resolve() BEFORE the venue is built, from the registry, so a
    class cannot lie its way past the guard after construction.

    UNITS AND SIGNS, one convention everywhere:
      qty is always POSITIVE in a call and SIGNED in a position (a short is a
      negative quantity). side is "buy" or "sell". Prices are in the quote
      currency of the symbol. Every percentage returned says what it is a
      percentage OF, in its key name.
    """

    name: str = "unnamed"
    is_real_money: bool = False

    # -- reading ------------------------------------------------------------
    @abstractmethod
    def account(self) -> dict:
        """{"venue","equity","cash","buying_power","open_risk", ...}.

        `open_risk` is dollars that would be lost if every resting stop
        filled AT ITS LEVEL. Stops slip, so the real number is worse; the
        key name says level, and the note beside it says so too."""

    @abstractmethod
    def positions(self) -> list:
        """Open positions, signed, with a live unrealised profit or loss."""

    @abstractmethod
    def position(self, symbol: str) -> dict | None:
        """One position, or None. No position is not an error."""

    # -- acting -------------------------------------------------------------
    @abstractmethod
    def market_order(self, symbol: str, side: str, qty: float, **kw) -> dict:
        """Buy or sell now. A sell with no position is a SHORT, not an error.

        Returns an order record. It always comes back: a fill has
        status "filled", a refusal has status "rejected" and a `reason` that
        says what actually stopped it."""

    @abstractmethod
    def place_stop(self, symbol: str, level: float, **kw) -> dict:
        """A resting stop on an open position, checked on every bar."""

    @abstractmethod
    def close_position(self, symbol: str, qty: float | None = None, **kw) -> dict:
        """Close all of it, or part of it. Partial is first-class: the method
        takes half off at the first target and leaves a runner."""

    # -- the audit trail ----------------------------------------------------
    @abstractmethod
    def orders(self) -> list:
        """Every order attempt, filled and refused alike."""

    @abstractmethod
    def fills(self) -> list:
        """Every fill. The engine must be reconstructible from these alone."""

    def misses(self) -> list:
        """Every order that did NOT fill, and the real reason. A default is
        provided because a venue that cannot tell us is worse than one that
        can, but not every venue exposes it."""
        return [o for o in self.orders() if o.get("status") == "rejected"]


# ============================================================== THE REGISTRY
class _Spec:
    __slots__ = ("name", "factory", "real_money", "note")

    def __init__(self, name, factory, real_money, note):
        self.name, self.factory = name, factory
        self.real_money, self.note = bool(real_money), note


_REGISTRY: dict[str, _Spec] = {}


def register(name: str, factory, real_money: bool = False, note: str = "") -> None:
    """Add a venue. `factory(**kwargs) -> Venue`. `real_money` is declared
    HERE, next to the name, so the guard can read it without constructing
    anything."""
    _REGISTRY[name.strip().lower()] = _Spec(name.strip().lower(), factory,
                                            real_money, note)


def registered() -> dict:
    return {k: {"real_money": s.real_money, "note": s.note}
            for k, s in sorted(_REGISTRY.items())}


def _paper_factory(**kw):
    import paper
    return paper.PaperBroker(**kw)


def _alpaca_paper_factory(**kw):
    return AlpacaVenue(**kw)


def _alert_factory(**kw):
    return AlertVenue(**kw)


def _blofin_demo_factory(**kw):
    return BlofinVenue(**kw)


register("paper", _paper_factory, real_money=False,
         note="our own engine: fills at the far side of the quote, stops fill "
              "at the worst price in the triggering bar, shorts first-class")
register("alpaca-paper", _alpaca_paper_factory, real_money=False,
         note="Alpaca's PAPER host through alpaca.py. Cannot short crypto and "
              "rejects market orders outside stock hours; those are the "
              "venue's limits, not the method's")
register("alert", _alert_factory, real_money=False,
         note="places nothing. Messages Wallace the trade and keeps the "
              "record as if filled. HE executes it by hand, so the money is "
              "real even though this program never touches it")
register("blofin-demo", _blofin_demo_factory, real_money=False,
         note="BloFin's DEMO futures host through blofin_private.py. Isolated "
              "margin, market entries, stops resting at the exchange. It can "
              "only ever touch a position it opened itself — see "
              "attribution.py, and BlofinVenue below")

# NOTE FOR WHOEVER ADDS THE FIRST REAL VENUE. Register it with
# real_money=True. That single word is what forces the confirmation phrase.
# Do not add a real venue with real_money=False to "make testing easier".


# ================================================================= RESOLVING
def _read_config(env: dict | None = None) -> dict:
    """Config from the process environment first, then .env. Read straight
    from os.environ rather than through blofin_private.load_env's prefix
    list, deliberately: the guard must not be able to fail because somebody
    forgot to add a prefix. A guard with a silent off-switch is not a guard.
    """
    if env is not None:
        return dict(env)
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
            pass                     # unreadable config resolves to paper
    out.update(os.environ)           # the real environment always wins
    return out


def resolve(name: str | None = None, env: dict | None = None, **kwargs):
    """Build the venue the config asks for. Returns (venue, decision).

    `decision` is the whole story: what was asked for, what was chosen, and
    why they differ when they do. Every path that is not an explicit,
    confirmed, registered real-money venue ends at paper.
    """
    cfg = _read_config(env)
    asked = name
    if asked is None:
        for key in VENUE_KEYS:
            if cfg.get(key):
                asked = cfg[key]
                break
    asked_raw = asked
    asked = (asked or "").strip().lower()

    decision = {"asked_for": asked_raw, "chosen": DEFAULT_VENUE,
                "real_money": False, "why": "", "warnings": []}

    if not asked:
        decision["why"] = ("no venue configured, so paper. Absent config is "
                           "never live.")
        spec = _REGISTRY[DEFAULT_VENUE]
    elif asked not in _REGISTRY:
        decision["warnings"].append(
            f"{asked_raw!r} is not a venue we know. Falling back to paper "
            f"rather than guessing. Known: {', '.join(sorted(_REGISTRY))}")
        decision["why"] = "unknown venue name, so paper"
        spec = _REGISTRY[DEFAULT_VENUE]
    else:
        spec = _REGISTRY[asked]
        if spec.real_money and cfg.get(LIVE_CONFIRM_KEY, "") != LIVE_CONFIRM_PHRASE:
            decision["warnings"].append(
                f"{asked!r} trades REAL MONEY and {LIVE_CONFIRM_KEY} is not "
                f"set to the exact phrase {LIVE_CONFIRM_PHRASE!r}. Refusing "
                f"it and using paper.")
            decision["why"] = "real-money venue without the confirmation phrase, so paper"
            spec = _REGISTRY[DEFAULT_VENUE]
        else:
            decision["why"] = ("real money, confirmed by the exact phrase"
                               if spec.real_money else "paper venue, as configured")

    decision["chosen"] = spec.name
    decision["real_money"] = spec.real_money
    decision["note"] = spec.note
    venue = spec.factory(**kwargs)
    # The class must agree with the registry. A mismatch means somebody
    # registered a real venue as safe, or the reverse. Stop rather than trade.
    if bool(getattr(venue, "is_real_money", False)) != spec.real_money:
        raise RuntimeError(
            f"venue {spec.name!r} declares is_real_money="
            f"{getattr(venue, 'is_real_money', None)} but is registered as "
            f"real_money={spec.real_money}. Refusing to trade on a "
            "contradiction.")
    return venue, decision


def banner(decision: dict) -> str:
    """The line nobody can miss in a deploy log."""
    bar = "=" * 74
    money = ("REAL MONEY. THIS PLACES ORDERS THAT COST ACTUAL DOLLARS."
             if decision.get("real_money") else
             "PAPER. No real money can be reached from here.")
    lines = [bar, f"  VENUE: {str(decision.get('chosen')).upper()}", f"  {money}",
             f"  why: {decision.get('why')}"]
    for w in decision.get("warnings") or []:
        lines.append(f"  WARNING: {w}")
    if decision.get("note"):
        lines.append(f"  what it is: {decision['note']}")
    lines.append(bar)
    return "\n".join(lines)


def announce(decision: dict, notify=None, to_phone: bool = True) -> str:
    """Print the banner and push it to his phone. Called once at startup.

    A push that fails must never stop the bot, but it must never fail
    silently either."""
    text = banner(decision)
    print(text, flush=True)
    if to_phone:
        try:
            send = notify
            if send is None:
                from step5_paper_trade import notify as send   # the one live path
            send(f"venue: {decision.get('chosen')}",
                 ("REAL MONEY" if decision.get("real_money") else "paper") +
                 f" — {decision.get('why')}")
        except Exception as e:                    # noqa: BLE001
            print(f"  venue announcement push failed: {str(e)[:120]}", flush=True)
    return text


# ====================================================== ADAPTER: ALPACA PAPER
class AlpacaVenue(Venue):
    """The existing alpaca.py, wearing the interface.

    NOT EXERCISED. The real Alpaca account has zero orders ever placed and
    that stays true, so this adapter's order path has been written but never
    run. It is here so the interface has a second implementation and so the
    switch is a config value today rather than a rewrite later. Run it
    against the paper host deliberately before trusting it.

    TWO OF THE VENUE'S OWN LIMITS, STATED NOT HIDDEN: it cannot short crypto
    (every US-dollar pair reports shortable=false), and it rejects stock
    market orders outside regular hours. Those refusals come back as
    status "rejected" with the real reason, never as a silent success.
    """

    name = "alpaca-paper"
    is_real_money = False

    def __init__(self, client=None, **_ignored):
        if client is None:
            import alpaca
            client = alpaca.from_env()
            if client is None:
                raise RuntimeError("ALPACA_API_KEY / ALPACA_API_SECRET are not set")
        self.cli = client
        self._orders: list = []

    @staticmethod
    def _is_crypto(symbol: str) -> bool:
        return "/" in symbol

    def account(self) -> dict:
        a = self.cli.account()
        return {"venue": self.name, "real_money": self.is_real_money,
                "equity": float(a.get("equity") or 0.0),
                "cash": float(a.get("cash") or 0.0),
                "buying_power": float(a.get("buying_power") or 0.0),
                "cash_buying_power": float(a.get("non_marginable_buying_power") or 0.0),
                "open_risk": None,
                "open_risk_note": "the venue does not report it; the runner "
                                  "knows its own stops",
                "raw": a}

    def positions(self) -> list:
        out = []
        for p in self.cli.positions():
            qty = float(p.get("qty") or 0.0)
            if (p.get("side") or "long") == "short":
                qty = -abs(qty)
            out.append({"symbol": p.get("symbol"), "qty": qty,
                        "avg_entry": float(p.get("avg_entry_price") or 0.0),
                        "mark": float(p.get("current_price") or 0.0),
                        "unrealised": float(p.get("unrealized_pl") or 0.0),
                        "venue": self.name, "raw": p})
        return out

    def position(self, symbol: str) -> dict | None:
        for p in self.positions():
            if p["symbol"] in (symbol, symbol.replace("/", "")):
                return p
        return None

    def _record(self, rec: dict) -> dict:
        rec["venue"] = self.name
        rec["real_money"] = self.is_real_money
        self._orders.append(rec)
        return rec

    def market_order(self, symbol: str, side: str, qty: float, **kw) -> dict:
        reason = kw.get("reason", "")
        if self._is_crypto(symbol):
            if side == "sell" and self.position(symbol) is None:
                return self._record({
                    "status": "rejected", "symbol": symbol, "side": side,
                    "qty": qty, "reason": "this venue cannot short crypto: "
                    "every US-dollar pair reports shortable=false", "note": reason})
            try:
                r = self.cli.crypto_market_order(symbol, side, qty,
                                                 kw.get("client_order_id"))
            except Exception as e:                 # noqa: BLE001
                return self._record({"status": "rejected", "symbol": symbol,
                                     "side": side, "qty": qty,
                                     "reason": str(e)[:300], "note": reason})
        else:
            try:
                r = self.cli.market_order(symbol, side, qty,
                                          kw.get("client_order_id"))
            except Exception as e:                 # noqa: BLE001
                return self._record({"status": "rejected", "symbol": symbol,
                                     "side": side, "qty": qty,
                                     "reason": str(e)[:300], "note": reason})
        return self._record({"status": "filled", "symbol": symbol, "side": side,
                             "qty": qty, "id": r.get("id"), "raw": r,
                             "note": reason})

    def place_stop(self, symbol: str, level: float, **kw) -> dict:
        """A RESTING stop order at the venue. Alpaca holds it; we do not walk
        bars for it. Same call, different mechanism — which is the whole
        point of the interface."""
        pos = self.position(symbol)
        if pos is None or not pos["qty"]:
            return self._record({"status": "rejected", "symbol": symbol,
                                 "level": level,
                                 "reason": "no open position to protect"})
        side = "sell" if pos["qty"] > 0 else "buy"
        body = {"symbol": symbol, "side": side, "type": "stop",
                "stop_price": str(level), "qty": str(abs(pos["qty"])),
                "time_in_force": "gtc" if self._is_crypto(symbol) else "day"}
        try:
            r = self.cli._post("/v2/orders", body)
        except Exception as e:                     # noqa: BLE001
            return self._record({"status": "rejected", "symbol": symbol,
                                 "level": level, "reason": str(e)[:300]})
        return self._record({"status": "placed", "kind": "stop",
                             "symbol": symbol, "level": level, "raw": r})

    def close_position(self, symbol: str, qty: float | None = None, **kw) -> dict:
        pos = self.position(symbol)
        if pos is None or not pos["qty"]:
            return self._record({"status": "rejected", "symbol": symbol,
                                 "reason": "no open position"})
        if qty is None or abs(qty) >= abs(pos["qty"]) - 1e-12:
            try:
                r = (self.cli.crypto_close_position(symbol)
                     if self._is_crypto(symbol) else
                     self.cli.close_position(symbol))
            except Exception as e:                 # noqa: BLE001
                return self._record({"status": "rejected", "symbol": symbol,
                                     "reason": str(e)[:300]})
            return self._record({"status": "filled", "kind": "close",
                                 "symbol": symbol, "qty": abs(pos["qty"]),
                                 "raw": r})
        side = "sell" if pos["qty"] > 0 else "buy"
        return self.market_order(symbol, side, abs(qty),
                                 reason=kw.get("reason", "partial close"))

    def orders(self) -> list:
        return list(self._orders)

    def fills(self) -> list:
        return [o for o in self._orders if o.get("status") == "filled"]


# ================================================ ADAPTER: THE PHONE "VENUE"
class AlertVenue(Venue):
    """A market we cannot trade programmatically, made into an ordinary venue.

    Alpaca has no currencies. Wallace: "if tjr trades forex and the api
    doesnt support then for forex only just send me the notification through
    telegram on the trade I should take and I will manually take it."

    This places nothing. It messages him and then keeps the record through
    the paper engine exactly as if the order had filled, so the strategy code
    above it is byte-identical to the crypto and stock paths. A market he
    executes by hand is an IMPLEMENTATION, not a special case threaded
    through the method.

    HONESTY NOTE, and it is not small: this engine's record is what SHOULD
    have happened, at the quote the engine could see. What his broker
    actually gave him will differ. The record says so — every fill from here
    carries "human_executes": True — so nobody later mistakes this for a
    machine-verified fill.
    """

    name = "alert"
    is_real_money = False        # this program places nothing. He does.

    def __init__(self, notify=None, engine=None, **kw):
        import paper
        kw.setdefault("state_path", os.path.join(REPO, "alert_state.json"))
        kw.setdefault("log_path", os.path.join(REPO, "alert_fills.jsonl"))
        kw.setdefault("venue_label", self.name)
        self.engine = engine if engine is not None else paper.PaperBroker(**kw)
        self._notify = notify

    def _push(self, title: str, message: str) -> None:
        try:
            send = self._notify
            if send is None:
                from step5_paper_trade import notify as send
            send(title, message)
        except Exception as e:                     # noqa: BLE001
            print(f"  alert push failed: {str(e)[:120]}", flush=True)

    def account(self):
        a = self.engine.account()
        a["venue"] = self.name
        a["human_executes"] = True
        return a

    def positions(self):
        return self.engine.positions()

    def position(self, symbol):
        return self.engine.position(symbol)

    def market_order(self, symbol, side, qty, **kw):
        rec = self.engine.market_order(symbol, side, qty, **kw)
        rec["human_executes"] = True
        if rec.get("status") == "filled":
            self._push(f"{side.upper()} {symbol}",
                       f"{qty} {symbol} around {rec['price']:.6f}. "
                       f"Take this one by hand.")
        else:
            self._push(f"could not record {side.upper()} {symbol}",
                       str(rec.get("reason", ""))[:300])
        return rec

    def place_stop(self, symbol, level, **kw):
        rec = self.engine.place_stop(symbol, level, **kw)
        if rec.get("status") == "placed":
            self._push(f"stop for {symbol}",
                       f"Put the stop at {level:.6f}. It is not on any "
                       f"exchange until you place it.")
        return rec

    def close_position(self, symbol, qty=None, **kw):
        rec = self.engine.close_position(symbol, qty, **kw)
        rec["human_executes"] = True
        if rec.get("status") == "filled":
            self._push(f"CLOSE {symbol}",
                       f"Close {rec['qty']} of {symbol} around "
                       f"{rec['price']:.6f}. {rec.get('reason', '')}")
        return rec

    def orders(self):
        return self.engine.orders()

    def fills(self):
        return self.engine.fills()

    def misses(self):
        return self.engine.misses()


# ====================================================== ADAPTER: BLOFIN DEMO
#
# THE SAFETY RULE THIS CLASS EXISTS TO ENFORCE
#
# Wallace trades the BloFin demo account by hand. On 2026-07-25 a bot in this
# project closed a position HE had opened. Everything below is built so that
# cannot happen again, and built so it cannot QUIETLY stop being true either.
#
# The rule: THE BOT MAY ONLY EVER TOUCH A POSITION IT OPENED ITSELF.
#
# It is enforced in three layers, on purpose, because one layer is a promise
# and three is a design:
#
#   1. attribution.py decides. It is pure, it reads the exchange's own
#      records, and every uncertain case it can reach returns "his".
#   2. _guarded_reduce() is the ONLY method in this class that may shrink,
#      close, or protect a position. It asks attribution first and returns a
#      refusal record if the answer is no.
#   3. The exchange client is SEALED (_SealedClient below). Its reducing
#      calls — a reduce-only order, a stop bracket, a cancel — physically
#      raise unless _guarded_reduce has opened the door for that one call.
#      So a future edit that reaches past the guard does not silently trade;
#      it crashes, loudly, in a test.
#
# There is also a rule about OPENING, which matters just as much and is
# easier to miss: BloFin nets everything on a symbol into ONE position. If he
# is long ETH and the bot buys more ETH, there are not two positions, there
# is one — and from that moment neither of us can act on our own share
# without moving the other's. So the bot REFUSES TO OPEN on any symbol that
# already carries a position it cannot attribute to itself.

class NotOurs(RuntimeError):
    """Raised only when something tried to reach the exchange's reducing
    calls without going through the attribution guard. It is a programming
    error, not a market condition, and it should stop the process."""


class _SealedClient:
    """The exchange client with its dangerous calls behind a door.

    Reads pass straight through. The calls that can shrink, close, or alter
    protection on a position — a reduce-only order, a stop/take-profit
    bracket, any cancel — only run while `open_for` holds the token that
    _guarded_reduce created for this one action. Anything else raises.

    This is deliberately a runtime wall rather than a convention. A comment
    saying "call the guard first" is obeyed until somebody is in a hurry.
    """

    SEALED = ("place_tpsl", "cancel_tpsl", "cancel_order")

    def __init__(self, raw):
        object.__setattr__(self, "_raw", raw)
        object.__setattr__(self, "open_for", None)

    def _check(self, what: str) -> None:
        if object.__getattribute__(self, "open_for") is None:
            raise NotOurs(
                f"{what} was called without the attribution guard open. Every "
                f"reduce, close, or stop must go through "
                f"BlofinVenue._guarded_reduce, which proves the position was "
                f"opened by this bot before anything touches it.")

    def __getattr__(self, name):
        raw = object.__getattribute__(self, "_raw")
        attr = getattr(raw, name)
        if name in _SealedClient.SEALED:
            def sealed(*a, **kw):
                self._check(name)
                return attr(*a, **kw)
            return sealed
        if name in ("market_order", "post_only_order"):
            def maybe_sealed(*a, **kw):
                if kw.get("reduce_only"):
                    self._check(f"{name}(reduce_only=True)")
                return attr(*a, **kw)
            return maybe_sealed
        return attr


class BlofinVenue(Venue):
    """BloFin's DEMO futures host, wearing the interface.

    THE STANDING RULES ON THIS VENUE, all of them his:
      - ISOLATED margin. Each trade's worst case is capped at its own margin
        instead of pledging the whole account behind every position.
      - MARKET orders in. The method's trigger is a candle closing; a resting
        limit that never fills is a signal missed, not a signal saved.
      - STOPS REST AT THE EXCHANGE. Not in this process. If this process
        dies, the stop is still there. That is the entire reason.
      - NO COST FILTERING. Fees and the spread are charged and reported so
        the figures are honest. Nothing declines or ranks a trade on them.

    WHAT `qty` MEANS HERE. Every call in and out of this class speaks in
    COINS, because that is what the method computes. BloFin trades CONTRACTS,
    and one contract is worth 0.001 of a Bitcoin, 0.01 of an Ether and a
    THOUSAND Doge. That conversion happens here and nowhere else, read live
    from the exchange's own instrument spec — never assumed.
    """

    name = "blofin-demo"
    is_real_money = False

    # The method names its pairs the way the price feed does. The exchange
    # names them its own way. The translation lives here, which is the only
    # place allowed to know a venue's vocabulary.
    PAIRS = {
        "BTC/USD": "BTC-USDT", "ETH/USD": "ETH-USDT", "SOL/USD": "SOL-USDT",
        "XRP/USD": "XRP-USDT", "DOGE/USD": "DOGE-USDT", "LINK/USD": "LINK-USDT",
        "AVAX/USD": "AVAX-USDT", "LTC/USD": "LTC-USDT", "ADA/USD": "ADA-USDT",
        "DOT/USD": "DOT-USDT",
    }

    # How much of the account's own money backs one trade's margin. The
    # leverage needed is worked out FROM this and from the size, never picked.
    PER_TRADE_MARGIN_SHARE = 0.10

    # Liquidation must sit well beyond the stop or the stop is decoration.
    # The leverage chosen is refused if the exchange would kill the position
    # before the stop was reached, with this much room to spare.
    LIQUIDATION_SAFETY = 3.0

    def __init__(self, client=None, tag: str = "tjr_crypto", **_ignored):
        if client is None:
            import blofin_private as bp
            env = bp.load_env(os.path.join(REPO, ".env"))
            client = bp.BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                          env["BLOFIN_DEMO_API_SECRET"],
                                          env["BLOFIN_DEMO_PASSPHRASE"])
        import blofin_private as bp
        self._raw = client                  # reads only
        self._cli = _SealedClient(client)   # everything else
        self._bp = bp
        self._tag = bp.BOOK_TAGS.get(tag, tag)
        self._orders: list = []
        self._specs: dict = {}
        self._verdicts: dict = {}
        self._stops: dict = {}              # symbol -> the stop we placed

    # ----------------------------------------------------------- symbols
    def venue_symbol(self, symbol: str) -> str:
        """"BTC/USD" -> "BTC-USDT". An unknown symbol is returned unchanged
        so the exchange's own refusal is what the log records, rather than a
        guess made here."""
        return self.PAIRS.get(symbol, symbol)

    def spec(self, symbol: str) -> dict:
        """contractValue, lotSize, tickSize and maxLeverage for one symbol,
        read from the exchange. Cached on success only, so a failed read is
        retried next time instead of being locked in for the process's life.
        Returns {} when it cannot be read — and a caller about to place an
        order treats {} as DO NOT TRADE, never as a default."""
        inst = self.venue_symbol(symbol)
        if inst in self._specs:
            return self._specs[inst]
        try:
            for row in self._raw.instruments("SWAP") or []:
                iid = str(row.get("instId") or "")
                if not iid:
                    continue
                self._specs[iid] = {
                    "contract_value": float(row.get("contractValue") or 0),
                    "lot": float(row.get("lotSize") or 0),
                    "tick": float(row.get("tickSize") or 0),
                    "max_leverage": float(row.get("maxLeverage") or 0),
                    "state": row.get("state"),
                }
        except Exception:                                    # noqa: BLE001
            return {}
        return self._specs.get(inst, {})

    # ---------------------------------------------------------- reading
    def account(self) -> dict:
        try:
            b = self._raw.account_balance() or {}
            equity = float(b.get("totalEquity") or 0.0)
        except Exception as e:                               # noqa: BLE001
            return {"venue": self.name, "real_money": False, "equity": 0.0,
                    "cash": 0.0, "buying_power": 0.0, "open_risk": None,
                    "error": str(e)[:200]}
        free = 0.0
        try:
            bal = self._raw.futures_balance() or {}
            free = float(bal.get("available") or 0.0)
        except Exception:                                    # noqa: BLE001
            pass
        return {"venue": self.name, "real_money": False,
                "equity": equity, "cash": free, "buying_power": free,
                "open_risk": self.open_risk(),
                "open_risk_note": "dollars lost if every stop the BOT placed "
                                  "filled AT ITS LEVEL. Stops slip, so the "
                                  "real number is worse. His own positions "
                                  "are not in it — they are not ours to "
                                  "count.",
                "raw": b}

    def open_risk(self) -> float:
        """Dollars lost if every stop THE BOT PLACED filled at its level.

        It walks self._stops rather than every open position on purpose.
        account() is called once a minute per market, and attributing a
        position costs an order-history read each — so asking "what have I
        got at risk" must not turn into ten API calls a minute when the
        answer is almost always zero. His positions cannot appear here at
        all: the bot never placed a stop on one, so it is never in _stops.
        """
        if not self._stops:
            return 0.0
        risk = 0.0
        marks = {str(r.get("instId")): r for r in self._rows()}
        for symbol, level in self._stops.items():
            row = marks.get(self.venue_symbol(symbol))
            if not row:
                continue
            cv = (self.spec(symbol) or {}).get("contract_value") or 0.0
            qty = abs(float(row.get("positions") or 0) * cv)
            risk += qty * abs(float(row.get("markPrice") or 0) - float(level))
        return risk

    def _rows(self) -> list:
        try:
            return [r for r in (self._raw.positions() or [])
                    if float(r.get("positions") or 0) != 0]
        except Exception:                                    # noqa: BLE001
            return []

    def _view(self, row: dict, verdict) -> dict:
        inst = str(row.get("instId") or "")
        pair = next((k for k, v in self.PAIRS.items() if v == inst), inst)
        cv = (self.spec(pair) or {}).get("contract_value") or 0.0
        contracts = float(row.get("positions") or 0)
        return {"symbol": pair, "venue_symbol": inst,
                "contracts": contracts,
                "qty": contracts * cv,          # in coins, the method's units
                "avg_entry": float(row.get("averagePrice") or 0),
                "mark": float(row.get("markPrice") or 0),
                "unrealised": float(row.get("unrealizedPnl") or 0),
                # NEVER a bare percentage: this one is a share of the MARGIN
                # posted, which is the number his BloFin screen shows, and it
                # is not a move in the price.
                "pnl_share_of_margin_pct": 100.0 * float(
                    row.get("unrealizedPnlRatio") or 0),
                "liquidation_price": float(row.get("liquidationPrice") or 0),
                "leverage": float(row.get("leverage") or 0),
                "margin_mode": row.get("marginMode"),
                "venue": self.name, "attributed_to": verdict.tag,
                "raw": row}

    def positions(self) -> list:
        """ONLY the positions the bot opened. His are not here — not as a
        flag, not as a zero, not at all. A position the bot cannot see is a
        position it cannot reason itself into touching."""
        out = []
        for row in self._rows():
            v = self._verdict_for_row(row)
            if v.ours:
                out.append(self._view(row, v))
        return out

    def foreign_positions(self) -> list:
        """HIS positions, for saying so in a report and for nothing else.
        Nothing in the order path reads this."""
        out = []
        for row in self._rows():
            v = self._verdict_for_row(row)
            if not v.ours:
                d = self._view(row, v)
                d["why_not_ours"] = v.reason
                out.append(d)
        return out

    def position(self, symbol: str) -> dict | None:
        inst = self.venue_symbol(symbol)
        for row in self._rows():
            if str(row.get("instId")) == inst:
                v = self._verdict_for_row(row)
                return self._view(row, v) if v.ours else None
        return None

    # ------------------------------------------------- THE ATTRIBUTION GATE
    def _verdict_for_row(self, row: dict):
        import attribution
        inst = str(row.get("instId") or "")
        try:
            orders = self._raw.orders_history(inst, limit=100) or []
        except Exception as e:                               # noqa: BLE001
            return attribution.Verdict(
                False, f"the order history could not be read ({str(e)[:100]}), "
                       f"so this position cannot be attributed and is his",
                inst)
        v = attribution.attribute_position(row, orders, page_limit=100)
        self._verdicts[inst] = v
        return v

    def _require_ours(self, symbol: str):
        """The question every reduce, close and stop has to answer first:
        did the bot open this? Reads the exchange fresh every time — a cached
        yes from a minute ago is not proof about now."""
        import attribution
        v = attribution.attribute_symbol(self._raw, self.venue_symbol(symbol))
        self._verdicts[self.venue_symbol(symbol)] = v
        return v

    def _guarded_reduce(self, symbol: str, what: str, action) -> dict:
        """THE ONLY DOOR. Every path in this class that shrinks, closes, or
        places protection on a position comes through here, asks
        attribution, and does nothing at all if the answer is no.

        `action(verdict)` runs only on a yes, and only for as long as it
        takes — the door shuts in the `finally` whether it succeeded, failed,
        or raised.
        """
        verdict = self._require_ours(symbol)
        if not verdict.ours:
            return self._record({
                "status": "rejected", "kind": what, "symbol": symbol,
                "refused_by": "attribution",
                "reason": f"the bot did not open this position, so it does "
                          f"not touch it. {verdict.reason}",
                "verdict": verdict.to_dict()})
        token = object()
        object.__setattr__(self._cli, "open_for", token)
        try:
            return action(verdict)
        finally:
            object.__setattr__(self._cli, "open_for", None)

    # ---------------------------------------------------------- recording
    def _record(self, rec: dict) -> dict:
        rec["venue"] = self.name
        rec["real_money"] = self.is_real_money
        self._orders.append(rec)
        return rec

    # ------------------------------------------------------------ acting
    def market_order(self, symbol: str, side: str, qty: float, **kw) -> dict:
        """Open (or add to) a position, sized in COINS.

        Two refusals live here and both are safety, not preference:
          - the symbol already holds a position the bot cannot prove is its
            own. BloFin nets everything on a symbol into one position, so
            opening here would fuse the bot's trade to his and neither could
            be managed after that.
          - the instrument spec could not be read, so the coins-to-contracts
            conversion would be a guess. A guess here is wrong by a factor
            of up to a million.
        """
        reason = kw.get("reason", "")
        if kw.get("reduce_only"):
            return self.close_position(symbol, abs(qty), reason=reason)

        inst = self.venue_symbol(symbol)
        spec = self.spec(symbol)
        cv, lot = spec.get("contract_value") or 0.0, spec.get("lot") or 0.0
        tick = spec.get("tick") or 0.0
        if cv <= 0:
            return self._record({
                "status": "rejected", "symbol": symbol, "side": side,
                "qty": qty, "reason": "the exchange's instrument spec could "
                "not be read, so coins cannot be turned into contracts "
                "without guessing. Not trading on a guess.", "note": reason})

        for row in self._rows():
            if str(row.get("instId")) == inst:
                v = self._verdict_for_row(row)
                if not v.ours:
                    return self._record({
                        "status": "rejected", "symbol": symbol, "side": side,
                        "qty": qty, "refused_by": "attribution",
                        "reason": f"there is already a position on {inst} that "
                                  f"the bot did not open. This exchange nets "
                                  f"everything on a symbol into ONE position, "
                                  f"so opening here would merge the bot's "
                                  f"trade into his and neither could be "
                                  f"managed afterwards. {v.reason}",
                        "verdict": v.to_dict(), "note": reason})

        contracts = abs(qty) / cv
        if lot > 0 and contracts < lot:
            return self._record({
                "status": "rejected", "symbol": symbol, "side": side,
                "qty": qty, "reason": f"the size works out to {contracts:.4f} "
                f"contracts and this symbol's smallest tradeable amount is "
                f"{lot}. Too small to place.", "note": reason})

        lev = kw.get("leverage")
        if lev is None:
            lev = self._leverage_for(symbol, qty, kw.get("stop"),
                                     kw.get("reference_price"))
        if isinstance(lev, dict):                 # a refusal came back
            return self._record(dict(lev, symbol=symbol, side=side, qty=qty,
                                     note=reason))
        if not self._raw.ensure_leverage(inst, lev, self._bp.MARGIN_MODE):
            return self._record({
                "status": "rejected", "symbol": symbol, "side": side,
                "qty": qty, "reason": "the leverage could not be set on this "
                "symbol, and placing the order anyway is how the 2026-07-23 "
                "silent-rejection bug happened.", "note": reason})

        coid = self._bp.make_client_order_id(self._tag)
        # THE PROTECTION RIDES IN WITH THE ENTRY. Wallace, 2026-07-26:
        # "stops can literally be placed with the order together, it doesnt
        # have to be after" ... "stop and take profit by the way".
        #
        # Placing the stop as a SECOND request leaves a window where the
        # position exists with nothing under it. That window is not
        # theoretical: on 26 July a DOT short filled, price ran past where
        # the stop belonged before the second call landed, the exchange
        # refused the stop as invalid, and the position had to be closed a
        # second later. Attached, there is no window and no second call.
        #
        # The attached take profit is the LAST target, not the first — his
        # method takes half off at the first and lets the rest run, and an
        # attached bracket covers the whole position. So this is the "if we
        # lose contact with this entirely, get out somewhere sensible" order.
        # The staged partial exits are still worked bar by bar.
        targets = kw.get("targets") or []
        try:
            oid = self._cli.market_order(inst, side, contracts,
                                         margin_mode=self._bp.MARGIN_MODE,
                                         client_order_id=coid, lot_size=lot,
                                         stop_price=kw.get("stop"),
                                         take_profit=(float(targets[-1])
                                                      if targets else None),
                                         tick_size=tick)
        except Exception as e:                               # noqa: BLE001
            return self._record({"status": "rejected", "symbol": symbol,
                                 "side": side, "qty": qty,
                                 "client_order_id": coid,
                                 "reason": str(e)[:300], "note": reason})
        return self._record({"status": "filled", "symbol": symbol,
                             "venue_symbol": inst, "side": side, "qty": qty,
                             "contracts": contracts, "leverage": lev,
                             "margin_mode": self._bp.MARGIN_MODE,
                             "id": oid, "client_order_id": coid,
                             "tag": self._tag, "note": reason})

    def _leverage_for(self, symbol: str, qty: float, stop, entry):
        """Leverage is an OUTPUT, never a dial. It is the smallest whole
        number that lets this size's margin fit the per-trade budget — and if
        that number would put the exchange's liquidation price nearer than the
        stop, the trade is refused rather than quietly taken with a stop that
        could never be reached."""
        spec = self.spec(symbol)
        max_lev = spec.get("max_leverage") or 50.0
        try:
            # The balance endpoint straight, not account() — this runs inside
            # the order path and must not drag a whole attribution sweep
            # along behind it.
            equity = float((self._raw.account_balance() or {})
                           .get("totalEquity") or 0.0)
            price = float(entry or 0.0)
        except Exception:                                    # noqa: BLE001
            return {"status": "rejected",
                    "reason": "the account equity could not be read"}
        if equity <= 0 or price <= 0:
            return {"status": "rejected",
                    "reason": "the account equity or the entry price is "
                              "missing, so leverage cannot be worked out"}
        notional = abs(qty) * price
        budget = equity * self.PER_TRADE_MARGIN_SHARE
        need = max(1.0, notional / budget) if budget > 0 else max_lev
        lev = min(max(1, int(need + 0.999)), int(max_lev))

        if stop:
            stop_move = abs(price - float(stop)) / price
            liq_move = 1.0 / lev              # roughly, on isolated margin
            if stop_move > 0 and liq_move < stop_move * self.LIQUIDATION_SAFETY:
                return {"status": "rejected",
                        "reason": (
                            f"at {lev}x the exchange would liquidate about "
                            f"{100*liq_move:.2f}% away as a MOVE IN THE PRICE, "
                            f"and the stop sits {100*stop_move:.2f}% away as a "
                            f"move in the price. The stop has to be reached "
                            f"before the exchange steps in, with room to "
                            f"spare, so this one is not taken.")}
        return lev

    def place_stop(self, symbol: str, level: float, **kw) -> dict:
        """A stop RESTING AT THE EXCHANGE, on a position the bot opened.

        It goes through the guard because putting a stop on his position is
        touching his position — it changes what happens to his money — even
        though it never closes anything by itself.
        """
        def action(verdict):
            pos = self.position(symbol)
            if pos is None or not pos["contracts"]:
                return self._record({"status": "rejected", "kind": "stop",
                                     "symbol": symbol, "level": level,
                                     "reason": "no position of ours to protect"})
            inst = pos["venue_symbol"]
            spec = self.spec(symbol)
            side = "sell" if pos["contracts"] > 0 else "buy"
            coid = self._bp.make_client_order_id(self._tag)
            try:
                tid = self._cli.place_tpsl(
                    inst, side, abs(pos["contracts"]), None, float(level),
                    margin_mode=pos["margin_mode"], client_order_id=coid,
                    lot_size=spec.get("lot"), tick_size=spec.get("tick"))
            except Exception as e:                           # noqa: BLE001
                return self._record({"status": "rejected", "kind": "stop",
                                     "symbol": symbol, "level": level,
                                     "client_order_id": coid,
                                     "reason": str(e)[:300]})
            self._stops[symbol] = float(level)
            return self._record({"status": "placed", "kind": "stop",
                                 "symbol": symbol, "venue_symbol": inst,
                                 "level": level, "tpsl_id": tid,
                                 "client_order_id": coid,
                                 "rests_at_exchange": True,
                                 "verdict": verdict.to_dict()})

        return self._guarded_reduce(symbol, "stop", action)

    def close_position(self, symbol: str, qty: float | None = None,
                       **kw) -> dict:
        """Close all of it, or part of it — on a position the bot opened.

        `qty` is in COINS, like everything else in this class. Partial is
        first-class: the method takes half off at the first target and lets
        the rest run.
        """
        def action(verdict):
            pos = self.position(symbol)
            if pos is None or not pos["contracts"]:
                return self._record({"status": "rejected", "kind": "close",
                                     "symbol": symbol,
                                     "reason": "no position of ours to close"})
            inst = pos["venue_symbol"]
            spec = self.spec(symbol)
            cv, lot = spec.get("contract_value") or 0.0, spec.get("lot") or 0.0
            have = abs(pos["contracts"])
            want = have if qty is None or cv <= 0 else min(have, abs(qty) / cv)
            if lot > 0:
                want = int(want / lot) * lot
            if want <= 0:
                return self._record({"status": "rejected", "kind": "close",
                                     "symbol": symbol,
                                     "reason": f"the amount to close rounds to "
                                     f"nothing at this symbol's smallest "
                                     f"tradeable amount ({lot})"})
            side = "sell" if pos["contracts"] > 0 else "buy"
            coid = self._bp.make_client_order_id(self._tag)
            try:
                oid = self._cli.market_order(
                    inst, side, want, reduce_only=True,
                    margin_mode=pos["margin_mode"], client_order_id=coid,
                    lot_size=lot)
            except Exception as e:                           # noqa: BLE001
                return self._record({"status": "rejected", "kind": "close",
                                     "symbol": symbol,
                                     "client_order_id": coid,
                                     "reason": str(e)[:300]})
            if want >= have - 1e-12:
                self._stops.pop(symbol, None)
            return self._record({"status": "filled", "kind": "close",
                                 "symbol": symbol, "venue_symbol": inst,
                                 "side": side, "contracts": want,
                                 "qty": want * cv, "id": oid,
                                 "client_order_id": coid,
                                 "reason": kw.get("reason", ""),
                                 "verdict": verdict.to_dict()})

        return self._guarded_reduce(symbol, "close", action)

    def cancel_stops(self, symbol: str, **kw) -> dict:
        """Take OUR resting stop off a position the bot opened.

        This one is in the guard for the reason the 2026-07-23 incident gave
        us: the old bot did a blanket cancel of every bracket on a symbol and
        stripped the protection off a live position somebody else owned.
        Cancelling a stop is not a small act. It leaves money unprotected.
        """
        def action(verdict):
            inst = self.venue_symbol(symbol)
            try:
                pending = self._raw.pending_tpsl(inst) or []
            except Exception as e:                           # noqa: BLE001
                return self._record({"status": "rejected", "kind": "cancel_stop",
                                     "symbol": symbol, "reason": str(e)[:300]})
            import attribution
            killed, skipped = [], []
            for row in pending:
                # Even inside the guard, each bracket is checked one at a
                # time. A bracket HE placed on a position the bot opened is
                # still his instruction, and it is left alone.
                if not attribution.is_ours_coid(row.get("clientOrderId")):
                    skipped.append(str(row.get("tpslId")))
                    continue
                try:
                    self._cli.cancel_tpsl(inst, str(row.get("tpslId")))
                    killed.append(str(row.get("tpslId")))
                except Exception:                            # noqa: BLE001
                    skipped.append(str(row.get("tpslId")))
            self._stops.pop(symbol, None)
            return self._record({"status": "done", "kind": "cancel_stop",
                                 "symbol": symbol, "cancelled": killed,
                                 "left_alone": skipped,
                                 "verdict": verdict.to_dict()})

        return self._guarded_reduce(symbol, "cancel_stop", action)

    # -------------------------------------------------------- audit trail
    def orders(self) -> list:
        return list(self._orders)

    def fills(self) -> list:
        return [o for o in self._orders if o.get("status") == "filled"]

    def refusals(self) -> list:
        """Every order the attribution rule stopped. Worth reading on its
        own: a long list here means the bot is repeatedly finding positions
        it does not own, which is information, not noise."""
        return [o for o in self._orders if o.get("refused_by") == "attribution"]


if __name__ == "__main__":
    import json as _json
    v, d = resolve()
    announce(d, to_phone=False)
    print(_json.dumps({"registered": registered(), "decision": d}, indent=2))
