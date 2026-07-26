"""
tjr_desk.py — the one process that watches the markets, PLACES THE TRADES,
and tells Wallace what it did.

THE DECISION IT IMPLEMENTS — CHANGED 2026-07-25

    "honestly, I dont like this, lets leave forex behind, lets do stocks with
     alpaca on trading view and crypto on blofin, both ran by api."

    So the alert-only build is over. The bot trades, on two venues, by API.
    The messages that used to be instructions for him are now NOTIFICATIONS
    ABOUT WHAT THE BOT DID: it entered, it took half off, it is out. Nothing
    on his phone asks him to do anything.

    CURRENCIES ARE GONE. tjr_forex.py is retired (its own header says why)
    and no currency is fetched, decided on, or alerted here.

TWO VENUES, AND NOTHING IN THIS FILE KNOWS WHICH IS WHICH
    Every order goes through venue.py. This file names a venue exactly once
    per market, in the table below, and after that it only ever calls the
    seven methods on the interface. Switching where a market trades is one
    string.

        crypto    blofin-demo   ten pairs, isolated margin, market in,
                                stop resting AT THE EXCHANGE
        S&P 500   alpaca-paper  SPY and QQQ
        gold      alpaca-paper  GLD, with IAU as its second chart

    HIS CHARTS NEED NOTHING FROM US. His Alpaca account is already linked to
    TradingView, so the fills show up on his charts by themselves.

THE SAFETY RULE THAT OUTRANKS EVERYTHING ELSE HERE
    He trades the BloFin demo account personally, and a bot in this project
    closed one of his own trades on 2026-07-25. So: THE BOT MAY ONLY EVER
    TOUCH A POSITION IT OPENED ITSELF. That is not enforced in this file —
    it is enforced in attribution.py and in venue.BlofinVenue, underneath
    every call this file makes, so no amount of carelessness up here can
    reach one of his positions. A position the bot did not open does not
    appear in positions(), is not counted toward exposure, and cannot be
    reduced, closed, or stopped. Ambiguity resolves to hands off, always.

ARMING, WHICH IS HOW A VENUE GOES LIVE
    A market only sends orders when it is ARMED. An unarmed market does
    everything else exactly as it would live — decides, sizes, records, and
    messages — and simply does not send. The Alpaca account has never had a
    single order placed on it and STAYS THAT WAY until Wallace says
    otherwise, so stocks and gold ship unarmed. See ARMED_DEFAULT below.

WHAT IT WATCHES
    crypto       ten pairs, decided by tjr_crypto.live_step
    S&P 500      SPY and QQQ, decided by tjr_bot.live_step
    gold         GLD with IAU as its second chart, by tjr_gold.live_step

    THE METHOD IS NOT REIMPLEMENTED HERE and none of those files is edited.
    This file fetches bars, hands them to whichever decision function owns
    that market, sends what comes back to that market's venue, and says what
    happened. That is the whole job.

WHERE THE LIVE BARS COME FROM, and why each choice
    crypto      Alpaca's crypto endpoints. Twenty-four hours a day, no delay
                and no restriction on the account. Nothing else needed.
    S&P, gold   YAHOO, not Alpaca. This data plan refuses stock bars from the
                last fifteen minutes — it answers 403, not an empty list —
                and this method's entire entry window is forty minutes long,
                so fifteen-minute-old bars are useless for it. Yahoo was
                checked against Alpaca's own consolidated bars over 390
                minutes each of SPY, QQQ and GLD: the high-to-low distance
                matched exactly on the median bar, and the largest
                disagreement on any closing price was three cents on SPY,
                eleven on QQQ and nothing at all on GLD. Alpaca stays as the
                deep history underneath.
    NOTE. Alpaca and BloFin are where the ORDERS go. Where the BARS come
    from is a separate question and always has been — reading a price from
    Yahoo and sending the order to Alpaca is not a mismatch, it is the same
    arrangement the build has had since the data plan's fifteen-minute delay
    was measured.

DO NOT SPAM HIM. Three rules, all enforced below.
    1. Several symbols in one market firing on the same minute is ONE
       message with a block each, not one message each. Ten crypto pairs
       move together; three of them turning on the same idea in the same
       minute is one idea.
    2. A signal already sent is never sent twice, however many times the
       decision function keeps reporting it.
    3. Nothing is sent when nothing happens. No heartbeat, no "still
       watching", no end-of-day summary. Silence has to keep meaning
       silence or he will stop reading the phone.

SAFETY
    Paper and demo only. venue.py's real-money guard stays exactly as built:
    an unknown name, an unreadable config, a missing config — every one of
    them resolves to paper, and a real-money venue additionally needs a
    confirmation phrase nobody types by accident. No git. daemon.py is
    untouched.

USAGE
    python3 tjr_desk.py --dry-run     # decide and print; sends no order
    python3 tjr_desk.py --once        # one pass over every market, then exit
    python3 tjr_desk.py --status      # what each venue holds, and whose it is
    python3 tjr_desk.py --samples     # a real sample message for each market
    python3 tjr_desk.py --volume      # setups a day, per market
    python3 tjr_desk.py --derive-size # re-measure the set size's one input
    python3 tjr_desk.py               # watch, trade, and report
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time

import pandas as pd

import tjr_alerts
import tjr_bot
import tjr_crypto
import tjr_gold
import venue as venue_mod

ACCOUNT = 100_000.0        # what one percent is one percent OF. Only a
                           # fallback: the desk reads the venue's own equity
                           # at startup and every entry, and uses that.

# WHICH MARKETS MAY SEND AN ORDER.
#
# Crypto is armed. The BloFin demo account is a demo account, the attribution
# rule underneath it is built and tested, and that is the venue he named.
#
# Stocks and gold are NOT armed. The Alpaca account has never had a single
# order placed on it in its life and it stays that way until Wallace says
# otherwise. Unarmed does not mean half-built: the market decides, sizes,
# records and messages exactly as it would live. It just does not send.
#
# To arm them:  CRYPTOBOT_ARM=crypto,sp500,gold
ARMED_DEFAULT = "crypto"

_UA = {"User-Agent": "Mozilla/5.0"}


def armed_markets() -> set:
    raw = os.environ.get("CRYPTOBOT_ARM", ARMED_DEFAULT)
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


# ===================================================== LIVE BARS PER MARKET
def yahoo_frames(yahoo_symbol: str, minutes_5: int = 60,
                 minutes_1: int = 7) -> dict:
    """{"5m": frame, "1m": frame} with `t` the bar's START in New York."""
    import requests

    def pull(interval: str, days: int) -> pd.DataFrame:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}",
            params={"interval": interval, "range": f"{days}d"},
            headers=_UA, timeout=25)
        res = (r.json().get("chart") or {}).get("result") or []
        if not res:
            return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
        j = res[0]
        q = j["indicators"]["quote"][0]
        d = pd.DataFrame({"t": pd.to_datetime(j["timestamp"], unit="s", utc=True),
                          "open": q["open"], "high": q["high"],
                          "low": q["low"], "close": q["close"]}).dropna()
        d["t"] = d["t"].dt.tz_convert("America/New_York").dt.tz_localize(None)
        return d.sort_values("t").drop_duplicates("t").reset_index(drop=True)

    return {"5m": pull("5m", minutes_5), "1m": pull("1m", minutes_1)}


def splice(old: pd.DataFrame, fresh: pd.DataFrame) -> pd.DataFrame:
    """Cached history underneath, live bars on top, joined at one level.

    Two feeds rarely quote the same side of the market, and a step where they
    meet would sit in the middle of the chart as a jump in price that never
    happened — and a jump is one of the things this method actually trades.
    So the OLD half is shifted onto the live half by the median difference
    across the bars they share, measured fresh each time. Shifting the old
    side leaves the live prices exactly as they are, which is right: the
    trigger and the stop are read off those.
    """
    if fresh is None or len(fresh) == 0:
        return old
    if old is None or len(old) == 0:
        return fresh
    shared = old.merge(fresh[["t", "close"]], on="t", suffixes=("_o", "_n"))
    keep = old[old["t"] < fresh["t"].min()].copy()
    if len(shared) >= 20:
        shift = float((shared["close_n"] - shared["close_o"]).median())
        for c in ("open", "high", "low", "close"):
            keep[c] = keep[c] + shift
    return (pd.concat([keep, fresh])[["t", "open", "high", "low", "close"]]
            .sort_values("t").drop_duplicates("t", keep="last")
            .reset_index(drop=True))


def cached(path: str) -> pd.DataFrame | None:
    try:
        return pd.read_parquet(path)
    except (FileNotFoundError, OSError):
        return None


def stock_frames(symbol: str, cache_prefix: str) -> dict:
    """A US fund, live off Yahoo with the cached Alpaca history underneath."""
    live = yahoo_frames(symbol)
    out = {}
    for tf in ("5m", "1m"):
        old = cached(f"{tjr_gold.REPO}/{cache_prefix}_{tf}.parquet")
        if old is not None and "t" in old and len(old):
            # the index caches are stored in UTC; the gold ones already in
            # New York. Both are normalised here rather than at four call
            # sites, because a chart half in one clock is worse than no chart.
            if old["t"].dt.hour.max() >= 20 and "et_" not in cache_prefix:
                old = tjr_bot.to_et_frame(old)
        out[tf] = splice(old, live[tf])
    return out


def crypto_frames(cli, pair: str) -> dict:
    """One crypto pair, live from Alpaca. No clock and no restriction here."""
    start_5 = (dt.datetime.now(dt.timezone.utc) -
               dt.timedelta(days=95)).strftime("%Y-%m-%d")
    start_1 = (dt.datetime.now(dt.timezone.utc) -
               dt.timedelta(days=3)).strftime("%Y-%m-%d")
    out = {}
    for tf, code, start in (("5m", "5Min", start_5), ("1m", "1Min", start_1)):
        rows = cli.crypto_bars(pair, code, start=start).get(pair) or []
        out[tf] = tjr_crypto.to_utc_frame(rows)
    return out


# ============================================================== THE MARKETS
#
# Each entry says only what is TRUE OF THAT MARKET: which symbols, whose
# decision function owns it, where the bars come from, and whether it is
# open. Nothing below branches on the name of a market.

class Market:
    name = ""
    label = ""
    symbols: tuple = ()
    venue_name = "paper"     # named ONCE, here. Nothing below reads it again.
    tag = "tjr_crypto"       # which part of the bot owns the orders it places

    def __init__(self, venue=None):
        self.venue = venue

    def open_now(self, now: dt.datetime) -> bool:
        return True

    def frames(self) -> dict:
        raise NotImplementedError

    def decide(self, frames: dict, now: pd.Timestamp, account: float) -> list:
        raise NotImplementedError

    def usd_per_quote(self, symbol: str, frames: dict) -> float:
        return 1.0


class CryptoMarket(Market):
    """Ten pairs. No bell, no session, one call per pair — which is
    tjr_crypto's own rule and the reason ten pairs do not cap each other at
    one trade a day between them."""
    name = "crypto"
    symbols = tuple(tjr_crypto.PAIRS)
    venue_name = "blofin-demo"
    tag = "tjr_crypto"

    def __init__(self, venue=None):
        super().__init__(venue)
        import alpaca
        # Alpaca is the PRICE FEED for crypto and nothing else. The orders go
        # to BloFin. Twenty-four hours a day, no delay, no restriction on the
        # account — which is why it stays the feed even though it is not the
        # venue.
        self.cli = alpaca.from_env()

    def frames(self) -> dict:
        return {p: crypto_frames(self.cli, p) for p in self.symbols}

    def decide(self, frames, now, account):
        out = []
        for pair in self.symbols:
            d = frames.get(pair)
            if not d or len(d["1m"]) == 0:
                continue
            at = pd.Timestamp(d["1m"]["t"].iloc[-1]) + pd.Timedelta(minutes=1)
            r = tjr_crypto.live_step(pair, d, at, account)
            # "cannot_send" WAS ALPACA'S LIMIT, AND ALPACA IS NO LONGER THE
            # VENUE HERE. tjr_crypto raises it because every US-dollar pair on
            # Alpaca reports shortable=false. BloFin futures short perfectly
            # well, so on this desk the refusal is spent and the signal is
            # taken as the ordinary entry it always was. tjr_crypto.py is not
            # edited for this — the venue's limits belong to the venue.
            if r.get("action") in ("enter", "cannot_send"):
                out.append(dict(r, action="enter", market=self.name,
                                fired_at=at))
        return out


class IndexMarket(Market):
    """SPY and QQQ, and both charts always loaded, because the check that one
    must agree with the other is the method's own and needs both."""
    name = "sp500"
    symbols = ("SPY", "QQQ")
    venue_name = "alpaca-paper"
    tag = "tjr_stocks"
    YAHOO = {"SPY": "SPY", "QQQ": "QQQ"}

    def open_now(self, now):
        return now.weekday() < 5 and dt.time(9, 30) <= now.time() < dt.time(16, 0)

    def frames(self):
        return {s: stock_frames(self.YAHOO[s], f"data_alpaca_{s}")
                for s in self.symbols}

    def decide(self, frames, now, account):
        if any(len(frames[s]["1m"]) == 0 for s in self.symbols):
            return []
        at = max(pd.Timestamp(frames[s]["1m"]["t"].iloc[-1])
                 for s in self.symbols) + pd.Timedelta(minutes=1)
        r = tjr_bot.live_step(frames, at, account, clock={"is_open": True})
        if r.get("action") != "enter":
            return []
        return [dict(r, market=self.name, fired_at=at)]


class GoldMarket(Market):
    """Gold, which he named as one of the four markets he trades and which he
    did not name when he dropped currencies. GLD is a US fund and Alpaca
    trades it like any other, so it rides the stock venue. If he wants it
    gone too, it goes the same way currencies did — take it out of
    build_markets() and give this file's header a line saying why."""

    name = "gold"
    symbols = (tjr_gold.TRADED,)
    venue_name = "alpaca-paper"
    tag = "tjr_gold"

    def open_now(self, now):
        return now.weekday() < 5 and dt.time(9, 30) <= now.time() < dt.time(16, 0)

    def frames(self):
        return {s: stock_frames(s, f"data_alpaca_{s}_et")
                for s in (tjr_gold.TRADED, tjr_gold.TWIN)}

    def decide(self, frames, now, account):
        if len(frames[tjr_gold.TRADED]["1m"]) == 0:
            return []
        at = pd.Timestamp(frames[tjr_gold.TRADED]["1m"]["t"].iloc[-1]) + \
            pd.Timedelta(minutes=1)
        r = tjr_gold.live_step(frames, at, account, clock={"is_open": True})
        if r.get("action") != "enter":
            return []
        return [dict(r, market=self.name, fired_at=at)]


# CURRENCIES USED TO BE A MARKET HERE AND ARE NOT ANYMORE.
#
# Wallace, 2026-07-25: "lets leave forex behind". tjr_forex.py is retired in
# place — nothing imports it, nothing fetches a currency bar, nothing alerts
# on one, and the Twelve Data key it names is not needed. The file and its
# tests are still on disk with a header saying so, because the work in it is
# sound and deleting it would only make it expensive to revive.


# ================================================================ THE DESK
class Desk:
    """Every market, once a minute. It trades what fires, manages what it
    holds, and says what it did. Silence still means nothing happened."""

    def __init__(self, account: float = ACCOUNT, dry_run: bool = False,
                 markets=None, armed=None):
        self.account = float(account)
        self.dry_run = dry_run
        self.armed = armed_markets() if armed is None else set(armed)
        self.markets = markets if markets is not None else build_markets()
        self.open_trades: dict = {}     # (market, symbol) -> what the bot did
        self.sent: set = set()          # (market, symbol, entry time) handled

    # -------------------------------------------------------------- arming
    def is_armed(self, m: Market) -> bool:
        """An unarmed market decides, sizes, records and messages exactly as
        it would live. It just does not send. That is the difference between
        a market that is off and a market that is not yet switched on."""
        return m.name in self.armed and not self.dry_run

    def equity_for(self, m: Market) -> float:
        """One percent is one percent OF THE VENUE'S OWN EQUITY. Read it, do
        not compute it, and do not carry one venue's number to another — the
        BloFin demo balance and the Alpaca paper balance are different
        accounts holding different money."""
        try:
            eq = float((m.venue.account() or {}).get("equity") or 0.0)
            if eq > 0:
                return eq
        except Exception as e:                               # noqa: BLE001
            print(f"  {m.name}: could not read the account ({str(e)[:100]}), "
                  f"falling back to ${self.account:,.0f}")
        return self.account

    # ---------------------------------------------------------- one pass
    def poll_market(self, m: Market, now: dt.datetime | None = None) -> list:
        now = now or dt.datetime.now()
        if not m.open_now(now):
            return []
        frames = m.frames()
        equity = self.equity_for(m)
        fresh = []
        for sig in m.decide(frames, now, equity):
            key = (m.name, sig["symbol"], str(sig.get("entry_t") or sig["fired_at"]))
            if key in self.sent:
                continue            # rule 2: never the same signal twice
            self.sent.add(key)
            sig["usd_per_quote"] = m.usd_per_quote(sig["symbol"], frames)
            # HIS SIZING RULE'S ONE INPUT: the tightest stop this instrument
            # normally gives, measured from its own setups. Everything refuses
            # to state a size at all when it is missing, rather than sizing per
            # trade — which is the thing the rule specifically rejects.
            sig["tightest_stop_pct"] = tightest_stop_pct(sig["symbol"])
            sig["account"] = equity
            # THE DECISION FILES DO NOT ALL SPEAK THE SAME WORD FOR THIS.
            # tjr_crypto returns "side"; tjr_bot (which the index and gold
            # both run on) returns only "direction". Normalising it here is
            # the desk's job, and it is done ONCE rather than at every call
            # site that would otherwise have to remember.
            sig.setdefault("side", "buy" if sig["direction"] > 0 else "sell")
            sig.setdefault("partial_fraction", 0.5)
            fresh.append(sig)
        self._manage(m, frames)
        if fresh:
            self._enter(m, fresh, equity)
        return fresh                # rule 3: an empty list sends nothing

    # ------------------------------------------------------------- entries
    def _enter(self, m: Market, sigs: list, equity: float) -> None:
        """Place each entry, put its stop where the method says, and then
        send ONE message per market saying what the bot did.

        THE ORDER OF THE TWO ORDERS IS NOT ARBITRARY. The entry goes in
        first and the stop immediately after, because a stop cannot rest on a
        position that does not exist yet. The window between them is the one
        genuinely unprotected moment in the trade's life, so if the stop
        fails to go on, the position is closed again straight away rather
        than left naked — and the message says that is what happened.
        """
        for s in sigs:
            s["placed"] = self._place_one(m, s, equity)

        when = max(pd.Timestamp(s["fired_at"]) for s in sigs).to_pydatetime()
        upq = {s["symbol"]: s.get("usd_per_quote", 1.0) for s in sigs}
        title, msg = tjr_alerts.entry_message(sigs, equity, upq, when)
        title = f"the bot entered — {title}" if not self.dry_run else title
        msg = self._what_happened(m, sigs) + "\n\n" + msg
        self._push(title, msg)

        for s in sigs:
            if (s.get("placed") or {}).get("status") == "filled":
                self.open_trades[(m.name, s["symbol"])] = {
                    "sig": s, "half_off": False}

    def _size_for(self, m: Market, sig: dict, equity: float) -> dict:
        """His set size, and the one cap we added on top of it. Both numbers
        come back so a message can state what the rule asked for as well as
        what was sent."""
        entry = float(sig["reference_price"])
        stop_distance = abs(entry - float(sig["stop"]))
        risk_pct = 0.01
        if equity > 0 and sig.get("risk_wanted"):
            risk_pct = float(sig["risk_wanted"]) / equity
        return tjr_alerts.position_size(
            m.name, sig["symbol"], equity, entry, stop_distance,
            float(sig.get("tightest_stop_pct") or 0.0),
            float(sig.get("usd_per_quote") or 1.0), risk_pct)

    def _place_one(self, m: Market, sig: dict, equity: float) -> dict:
        size = self._size_for(m, sig, equity)
        sig["size"] = size
        if not size["ok"]:
            return {"status": "not_sent",
                    "reason": "the set size could not be worked out — this "
                              "instrument's tightest stop has never been "
                              "measured, and sizing off another market's "
                              "number is exactly what his rule forbids"}
        if size.get("capped"):
            print(f"  [CAP] {sig['symbol']}: the set size would have risked "
                  f"${size['uncapped_risk_dollars']:,.0f} "
                  f"({size['uncapped_risk_share_pct']:.1f}% OF THE ACCOUNT); "
                  f"cut to ${size['risk_dollars']:,.0f} "
                  f"({size['risk_share_pct']:.1f}% of the account). Today's "
                  f"stop is {size['wider']:.0f}x the tightest this market "
                  f"gives. This ceiling is OURS, not his.")
        if not self.is_armed(m):
            return {"status": "not_sent",
                    "reason": f"the {m.name} market is not armed, so nothing "
                              f"was sent. Everything else about this trade is "
                              f"real. Arm it with CRYPTOBOT_ARM."}

        rec = m.venue.market_order(
            sig["symbol"], sig["side"], size["units"],
            reference_price=float(sig["reference_price"]),
            stop=float(sig["stop"]), reason=f"{m.name} entry")
        if rec.get("status") != "filled":
            return rec

        stop = m.venue.place_stop(sig["symbol"], float(sig["stop"]),
                                  reason=f"{m.name} entry stop")
        rec["stop_order"] = stop
        if stop.get("status") not in ("placed", "filled"):
            # NOT LEFT NAKED. A position with no stop is the one thing this
            # method never has, so it comes straight back off.
            undo = m.venue.close_position(
                sig["symbol"], reason="the protective stop would not go on, "
                                      "so the position was closed rather than "
                                      "left with nothing under it")
            rec["status"] = "unwound"
            rec["unwound"] = undo
            rec["reason"] = (f"the stop could not be placed "
                             f"({str(stop.get('reason'))[:140]}), so the "
                             f"position was closed again immediately")
        return rec

    def _what_happened(self, m: Market, sigs: list) -> str:
        """The first thing on the message: what the BOT DID. He is being told,
        not asked."""
        out = []
        for s in sigs:
            p = s.get("placed") or {}
            sym, side = s["symbol"], s["side"].upper()
            st = p.get("status")
            if st == "filled":
                line = (f"DONE — the bot {('bought' if s['side'] == 'buy' else 'sold short')} "
                        f"{sym} and its stop is resting at the exchange. "
                        f"Nothing for you to do.")
            elif st == "unwound":
                line = (f"OPENED AND CLOSED AGAIN — {sym}. {p.get('reason')}")
            elif st == "not_sent":
                line = f"NOT SENT — {side} {sym}. {p.get('reason')}"
            else:
                line = (f"REFUSED — {side} {sym}. "
                        f"{str(p.get('reason'))[:220]}")
            out.append(line)
        return "\n".join(out)

    # ---------------------------------------------- managing what it holds
    def _manage(self, m: Market, frames: dict) -> None:
        """Move the stop, take half off, be out. The bot does all three, and
        the message afterwards says which one it did.

        A NOTE ON THE STOP, BECAUSE THE TWO LAYERS ARE EASY TO CONFUSE. The
        real stop RESTS AT THE EXCHANGE, and if this process dies the
        position is still protected by it. What this loop does is notice the
        stop was hit so the bot's own record catches up — it is bookkeeping,
        not protection. The targets are the opposite: nothing at the exchange
        knows about them, so this loop is the only thing that acts on them.
        """
        for sym in list(m.symbols):
            key = (m.name, sym)
            t = self.open_trades.get(key)
            if t is None:
                continue
            d = frames.get(sym) or frames.get(m.symbols[0])
            if not d or len(d["1m"]) == 0:
                continue
            bar = d["1m"].iloc[-1]
            at = (pd.Timestamp(bar["t"]) + pd.Timedelta(minutes=1)).to_pydatetime()
            sig = t["sig"]
            up = sig["direction"] > 0
            hi, lo = float(bar["high"]), float(bar["low"])
            entry, stop = float(sig["reference_price"]), float(sig["stop"])
            tgts = [float(x) for x in (sig.get("targets") or [])]
            units = float((sig.get("size") or {}).get("units") or 0.0)

            if (lo <= stop) if up else (hi >= stop):
                # The exchange's own stop did this. The bot closes anything
                # left over (normally nothing) and lets go of the record.
                self._act(m, sym, None, "the stop was hit")
                self._push(*tjr_alerts.stopped_message(m.name, sym, stop, at))
                self.open_trades.pop(key, None)
                continue

            if tgts and not t["half_off"]:
                if (hi >= tgts[0]) if up else (lo <= tgts[0]):
                    frac = float(sig.get("partial_fraction") or 0.5)
                    self._act(m, sym, units * frac, "the first target was hit")
                    self._restop(m, sym, entry)
                    self._push(*tjr_alerts.first_target_message(
                        m.name, sym, entry, tgts[0], at))
                    t["half_off"] = True
                    t["sig"] = dict(sig, stop=entry)   # break even from here
                    continue

            if len(tgts) > 1:
                if (hi >= tgts[1]) if up else (lo <= tgts[1]):
                    self._act(m, sym, None, "the second target was hit")
                    self._push(*tjr_alerts.close_message(
                        m.name, sym, tgts[1],
                        "The second target is reached. That is the trade.", at))
                    self.open_trades.pop(key, None)
                    continue

            flat = getattr(_config_for(m), "instrument", None)
            flat_t = getattr(flat, "flat_t", None) if flat else None
            if flat_t is not None and at.time() >= flat_t:
                self._act(m, sym, None, "this market closes shortly and he "
                                        "does not hold through it")
                self._push(*tjr_alerts.close_message(
                    m.name, sym, float(bar["close"]),
                    "This market closes shortly and he does not hold through "
                    "it, so the bot closed what was left at market.", at))
                self.open_trades.pop(key, None)

    def _act(self, m: Market, symbol: str, qty, reason: str) -> dict:
        """Close all of it, or part of it. Every one of these goes through the
        venue, which asks attribution first — so even here, the bot cannot
        reach a position it did not open."""
        if not self.is_armed(m):
            return {"status": "not_sent", "reason": "market not armed"}
        try:
            return m.venue.close_position(symbol, qty, reason=reason)
        except Exception as e:                               # noqa: BLE001
            print(f"  {m.name} {symbol}: close failed — {str(e)[:160]}")
            return {"status": "error", "reason": str(e)[:200]}

    def _restop(self, m: Market, symbol: str, level: float) -> dict:
        """Move the resting stop to break even after half is off. The old one
        comes off first — and cancel_stops only ever removes brackets the bot
        itself placed, which is the exact thing that went wrong on
        2026-07-23 when a blanket cancel stripped somebody else's protection."""
        if not self.is_armed(m):
            return {"status": "not_sent", "reason": "market not armed"}
        try:
            if hasattr(m.venue, "cancel_stops"):
                m.venue.cancel_stops(symbol, reason="moving the stop to break even")
            return m.venue.place_stop(symbol, level, reason="break even")
        except Exception as e:                               # noqa: BLE001
            print(f"  {m.name} {symbol}: stop move failed — {str(e)[:160]}")
            return {"status": "error", "reason": str(e)[:200]}

    def _push(self, title: str, message: str) -> None:
        if self.dry_run:
            print("\n" + "=" * 70)
            print(title)
            print("-" * 70)
            print(message)
            print("=" * 70)
            return
        tjr_alerts.send(title, message)

    # -------------------------------------------------------- the loop
    def once(self, now: dt.datetime | None = None) -> dict:
        out = {}
        for m in self.markets:
            try:
                out[m.name] = self.poll_market(m, now)
            except Exception as e:
                print(f"  {m.name}: {str(e)[:160]}")
                out[m.name] = []
        return out

    def watch(self) -> None:
        """Look once a minute, ON the minute. The entry trigger is a
        1-minute candle, so the first moment a setup can be true is the
        second that candle closes — this wakes a beat after each minute
        turns rather than sleeping a fixed sixty seconds and drifting."""
        print(self.startup_banner())
        while True:
            self.once()
            time.sleep(max(2.0, 62.0 - (time.time() % 60.0)))

    # ------------------------------------------------------------ reporting
    def startup_banner(self) -> str:
        """Printed once, and it has to be impossible to misread. Which
        markets, which venue each one sends to, which of them may actually
        send, and what is sitting on each account that the bot considers
        HIS."""
        bar = "=" * 74
        lines = [bar, "  THE DESK IS UP", bar]
        for m in self.markets:
            state = "ARMED — it will place orders" if self.is_armed(m) else \
                    "not armed — it decides and reports, and sends nothing"
            v = getattr(m.venue, "name", "?")
            lines.append(f"  {m.name:8s} -> {v:14s} {state}")
            lines.append(f"           {len(m.symbols)} symbol(s): "
                         f"{', '.join(m.symbols)}")
            try:
                eq = float((m.venue.account() or {}).get("equity") or 0.0)
                lines.append(f"           account equity ${eq:,.2f}")
            except Exception as e:                           # noqa: BLE001
                lines.append(f"           account unreadable: {str(e)[:80]}")
            for p in self._foreign(m):
                lines.append(
                    f"           HIS, NOT TOUCHED: {p['symbol']} "
                    f"{p.get('contracts', p.get('qty')):+,.2f} — "
                    f"{str(p.get('why_not_ours'))[:90]}")
        cap = tjr_alerts.max_risk_share()
        lines.append(f"  one trade may risk at most {100*cap:.1f}% OF THE "
                     f"ACCOUNT (our ceiling, not his — he has not ruled on it)"
                     if cap > 0 else
                     "  NO CEILING on what one trade may risk — his set-size "
                     "rule runs unmodified")
        lines.append(bar)
        return "\n".join(lines)

    @staticmethod
    def _foreign(m: Market) -> list:
        """Positions on this market's venue that the bot did not open. Read
        only. Nothing in the order path looks at this."""
        try:
            return m.venue.foreign_positions()
        except Exception:                                    # noqa: BLE001
            return []

    def status(self) -> dict:
        out = {"armed": sorted(self.armed),
               "cap_share_of_account_pct": 100 * tjr_alerts.max_risk_share(),
               "markets": {}}
        for m in self.markets:
            try:
                acct = m.venue.account()
            except Exception as e:                           # noqa: BLE001
                acct = {"error": str(e)[:200]}
            out["markets"][m.name] = {
                "venue": getattr(m.venue, "name", "?"),
                "armed": self.is_armed(m),
                "symbols": list(m.symbols),
                "equity": acct.get("equity"),
                "ours": [{"symbol": p["symbol"], "qty": p.get("qty"),
                          "unrealised": p.get("unrealised")}
                         for p in (m.venue.positions() or [])],
                "his_not_touched": [
                    {"symbol": p["symbol"], "qty": p.get("qty"),
                     "why": p.get("why_not_ours")}
                    for p in self._foreign(m)],
            }
        return out


def _config_for(m: Market):
    if m.name == "gold":
        return tjr_gold.gold_config()
    if m.name == "sp500":
        return tjr_bot.Config()
    return None                      # crypto has no bell and nothing to be flat for


def build_markets() -> list:
    """One market per line, each with its venue resolved through venue.py's
    guard. A market whose venue will not build is dropped with a reason
    printed — never silently swapped for another one."""
    out = []
    for cls in (CryptoMarket, IndexMarket, GoldMarket):
        try:
            v, decision = venue_mod.resolve(cls.venue_name, tag=cls.tag)
            if decision["chosen"] != cls.venue_name:
                print(f"  {cls.name}: asked for {cls.venue_name!r} and got "
                      f"{decision['chosen']!r} — {decision['why']}")
            out.append(cls(venue=v))
        except Exception as e:
            print(f"  {cls.name}: not available — {str(e)[:120]}")
    return out


# ================================================ THE SET SIZE'S ONE INPUT
#
# HIS RULE, from the bootcamp day he gives entirely to position size: take
# the tightest stop the instrument normally produces, work out the size that
# makes THAT stop cost one percent of the account, and then hold that size
# still. A wider stop on the day costs two percent, or three. The band is the
# output of holding the size fixed; it is not a dial.
#
# So the one number the size needs per instrument is that tightest stop. It
# is measured HERE, from each instrument's own setups, and stored as a SHARE
# OF THE PRICE so it stays meaningful when the price itself moves — Bitcoin
# at sixty thousand and at a hundred thousand should not need re-deriving.
#
# WHY THE TENTH PERCENTILE AND NOT THE SMALLEST. He says "what's USUALLY the
# lowest your stop loss will be", not "the lowest it has ever been". The
# single narrowest stop in a sample is one freak morning, and sizing off it
# would set a size that made every ordinary day a four-percent day. A tenth
# percentile is the narrowest stop that shows up regularly, which is what the
# sentence says. The whole spread is reported next to it so the reading can
# be checked rather than trusted.
#
# RE-DERIVED PERIODICALLY, NEVER PER TRADE. Running this again is what
# updates the size; nothing in the alert path recomputes it.

STOP_FLOOR_PATH = f"{tjr_gold.REPO}/step443_stop_floors.json"
STOP_FLOOR_PERCENTILE = 10


def _floor_from(trades) -> dict:
    if not trades:
        return {}
    import numpy as np
    pct = [abs(t.entry - t.stop) / t.entry for t in trades if t.entry]
    if not pct:
        return {}
    return {"tightest_stop_pct": float(np.percentile(pct, STOP_FLOOR_PERCENTILE)),
            "median_stop_pct": float(np.median(pct)),
            "widest_stop_pct": float(np.max(pct)),
            "setups_measured": len(pct)}


def derive_stop_floors(verbose: bool = True) -> dict:
    """Measure the tightest stop each instrument normally gives, from its own
    setups. Read-only against every venue; writes one JSON file.

    It starts from whatever was measured last time rather than from nothing,
    so an instrument whose run fails today keeps yesterday's number instead of
    vanishing from the file — and an instrument that is no longer measured at
    all (the currencies) keeps its history rather than being erased by a
    retirement."""
    out = dict(stop_floors())

    for pair in tjr_crypto.PAIRS:
        try:
            r = tjr_crypto.run_pair(pair)
            f = _floor_from(r["trades"])
            if f:
                out[pair] = f
        except Exception as e:
            if verbose:
                print(f"  {pair}: {str(e)[:100]}")

    try:
        import test_tjr_bot as t
        _, trades, _, _, _ = t.replay()
        for sym in ("SPY", "QQQ"):
            f = _floor_from([x for x in trades if x.symbol == sym])
            if f:
                out[sym] = f
    except Exception as e:
        if verbose:
            print(f"  SPY/QQQ: {str(e)[:100]}")

    try:
        f = _floor_from(tjr_gold.run_gold()["trades"])
        if f:
            out[tjr_gold.TRADED] = f
    except Exception as e:
        if verbose:
            print(f"  gold: {str(e)[:100]}")

    # Currencies used to be measured here too. They are retired, so they are
    # not. Their old numbers are left in the file rather than stripped out,
    # because deleting a measurement is not the same as retiring a market.

    with open(STOP_FLOOR_PATH, "w") as fh:
        json.dump(out, fh, indent=2)
    if verbose:
        for k, v in out.items():
            print(f"  {k:10s} tightest {100*v['tightest_stop_pct']:.3f}% of price"
                  f"   typical {100*v['median_stop_pct']:.3f}%"
                  f"   widest {100*v['widest_stop_pct']:.3f}%"
                  f"   (from {v['setups_measured']} setups)")
    return out


_FLOORS: dict = {}


def stop_floors() -> dict:
    global _FLOORS
    if not _FLOORS:
        try:
            with open(STOP_FLOOR_PATH) as fh:
                _FLOORS = json.load(fh)
        except FileNotFoundError:
            _FLOORS = {}
    return _FLOORS


def tightest_stop_pct(symbol: str) -> float:
    """The one input the set size needs. ZERO when it has never been measured
    for this instrument, which makes the alert refuse to state a size rather
    than invent one — sizing off another market's number is exactly what his
    rule forbids."""
    return float((stop_floors().get(symbol) or {}).get("tightest_stop_pct") or 0.0)


# ============================================================== REPORTING
def volume(verbose: bool = True) -> dict:
    """SETUPS A DAY, PER MARKET — the number trade count is limited by, and
    the only thing the replay is used for. Not a profit claim: he does not
    count historical replay as evidence and neither do we."""
    out = {}
    try:
        c = tjr_crypto.setups_per_day(verbose=False)
        n = sum(v["setups"] for v in c.values())
        d = max(max(v["days"] for v in c.values()), 1)
        out["crypto"] = {"pairs": len(c), "setups": n, "days": d,
                         "per_day": round(n / d, 3)}
    except Exception as e:
        out["crypto"] = {"error": str(e)[:120]}
    try:
        import test_tjr_bot as t
        _, trades, _, days, _ = t.replay()
        out["sp500"] = {"pairs": 2, "setups": len(trades), "days": len(days),
                        "per_day": round(len(trades) / max(len(days), 1), 3)}
    except Exception as e:
        out["sp500"] = {"error": str(e)[:120]}
    try:
        g = tjr_gold.setups_per_day(verbose=False)
        out["gold"] = {"pairs": 1, "setups": g["setups"], "days": g["days"],
                       "per_day": g["per_day"]}
    except Exception as e:
        out["gold"] = {"error": str(e)[:120]}
    per_day = sum(v.get("per_day", 0) for v in out.values())
    out["ALL THREE"] = {
        "trades_a_day": round(per_day, 2),
        "messages_a_day_including_manage": round(per_day * 3, 1),
        "note": ("each setup costs up to three messages, and every one of "
                 "them is the bot REPORTING what it did: it entered, it took "
                 "half off and moved the stop, it is out"),
    }
    if verbose:
        print(json.dumps(out, indent=2))
    return out


def samples() -> str:
    """A real alert for each market, built from a setup that actually fired
    in the cached history. Sends nothing."""
    parts = []

    def render(market, tr, symbol, upq=1.0):
        sig = {"market": market, "symbol": symbol, "direction": tr.direction,
               "reference_price": tr.entry, "stop": tr.stop,
               "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
               "level_tf": tr.level_tf, "level_price": tr.level_price,
               "confirmed_by": tr.confirm_kind, "pullback_into": tr.pullback_kind,
               "risk_dollars": tr.risk_dollars, "risk_wanted": tr.risk_wanted,
               "clamped": tr.clamped,
               "tightest_stop_pct": tightest_stop_pct(symbol)}
        title, msg = tjr_alerts.entry_message(
            sig, ACCOUNT, upq, pd.Timestamp(tr.entry_t).to_pydatetime())
        return f"### {title}\n\n{msg}"

    try:
        r = tjr_crypto.run_pair("BTC/USD")
        if r["trades"]:
            parts.append(render("crypto", r["trades"][-1], "BTC/USD"))
    except Exception as e:
        parts.append(f"crypto sample unavailable: {str(e)[:120]}")
    try:
        import test_tjr_bot as t
        _, trades, _, _, _ = t.replay()
        if trades:
            parts.append(render("sp500", trades[-1], trades[-1].symbol))
    except Exception as e:
        parts.append(f"S&P sample unavailable: {str(e)[:120]}")
    try:
        r = tjr_gold.run_gold()
        if r["trades"]:
            parts.append(render("gold", r["trades"][-1], tjr_gold.TRADED))
    except Exception as e:
        parts.append(f"gold sample unavailable: {str(e)[:120]}")
    return "\n\n".join(parts)


def main(argv):
    if "--samples" in argv:
        print(samples())
        return
    if "--volume" in argv:
        volume()
        return
    if "--derive-size" in argv:
        print("measuring the tightest stop each instrument normally gives")
        derive_stop_floors()
        return
    desk = Desk(dry_run="--dry-run" in argv)
    if "--status" in argv:
        print(desk.startup_banner())
        print(json.dumps(desk.status(), indent=2, default=str))
        return
    if "--once" in argv:
        print(desk.startup_banner())
        got = desk.once()
        for k, v in got.items():
            print(f"  {k:11s} {len(v)} setup(s)")
        return
    desk.watch()


if __name__ == "__main__":
    main(sys.argv)
