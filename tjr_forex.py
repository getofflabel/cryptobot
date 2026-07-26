"""
tjr_forex.py — RETIRED 2026-07-25. NOT IMPORTED, NOT WATCHED, NOT TRADED.

WHY IT IS RETIRED

Wallace, 2026-07-25:

    "honestly, I dont like this, lets leave forex behind, lets do stocks with
     alpaca on trading view and crypto on blofin, both ran by api."

Currencies were the one market in this build with no venue behind them. The
whole file was written around that gap: no broker in the project can send a
currency order, so the output was a message to his phone and he placed the
trade by hand. He has now decided against running a market that way. The bot
trades two venues by API — stocks on Alpaca, crypto on BloFin — and a market
that needs a human in the middle is not one of them.

WHAT WAS DONE, EXACTLY
  - tjr_desk.py no longer builds a CurrencyMarket. The desk does not fetch
    currency bars, does not call live_step below, and cannot alert on a pair.
  - No currency alerts of any kind are sent.
  - The Twelve Data key this file names as the fix for Yahoo's weakness on
    GBP/USD is NOT needed and should not be bought.
  - No Yahoo currency feed runs.

WHAT WAS NOT DONE, DELIBERATELY
  Nothing was deleted. This file, its tests (test_tjr_forex.py), and its
  cached bars all still sit where they were. The method here is sound work
  and the measurements in it are real; if he ever names a venue that takes a
  currency order by API, this is a starting point rather than a rewrite. It
  is retired, not wrong.

  Importing it still works, and running it directly still prints its own
  numbers. That is on purpose: a retired file that crashes on import teaches
  nobody anything six months from now.

EVERYTHING BELOW THIS LINE IS THE ORIGINAL FILE, UNCHANGED.
================================================================ ORIGINAL ==

tjr_forex.py — the same trader's method, pointed at currencies. Alert only.

WALLACE'S INSTRUCTION, WHICH IS THE WHOLE SPEC
    "if tjr trades forex and the api doesnt support then for forex only just
     send me the notification through telegram on the trade I should take and
     I will manually take it"

    He is right that the broker has no currencies. The trader we copy watches
    four markets — "I trade GBP USD and GBP JPY... I trade gold and then I
    also trade the S P 500" — and the bot covered one. This is the pair of
    currencies, and because no order can be sent, the whole output is a
    message to his phone with every number already worked out.

    Two pairs, the two he names: GBP/USD and GBP/JPY.

THE FEED. Alpaca has no currencies at all, so this is the one market where a
price has to come from somewhere else. Four were tested; what each actually
returned is written down in feed_report() and summarised here.

    YAHOO  — the live default, and what runs today.
        No account, no key, no signup of any kind, and this repo already
        reads it elsewhere. Gives 5-minute bars 60 days back and 1-hour bars
        730 days back on GBPUSD=X and GBPJPY=X, covering all 24 hours of
        every weekday. No published rate limit; polled once a minute it has
        never refused us.

        ONE MEASURED FLAW, ON ONE PAIR, AND IT IS NOT SMALL. Yahoo samples
        GBP/USD once a minute instead of aggregating it: of 7,195 one-minute
        bars pulled, 7,099 had a high equal to their low, and the 5-minute
        high was exactly the highest of five such samples on all 1,422
        overlapping bars checked. Measured against 5,401 of the bank's own
        5-minute candles over the same minutes, Yahoo's candle spans 65% of
        the true high-to-low distance, and once a constant 0.85-pip level
        offset is taken out it understates the high on 88.8% of bars and the
        low on 88.1%.

        That is the wrong error twice over for this method, which trades
        price running PAST a marked level and coming back and then puts the
        stop just beyond how far it ran: runs past a level go unseen, and the
        stops that do get set sit too close. GBP/JPY is clean on Yahoo (26
        flat bars out of 7,195) — this is one pair, not both.

        SO: Yahoo runs the alerts today and it is honest about GBP/JPY. The
        free Twelve Data key below is what makes GBP/USD trustworthy, and it
        is the one thing worth Wallace's two minutes.

    TWELVE DATA — the upgrade, and it is one line away.
        True tick-aggregated bars, real-time forex on the free plan, 8
        requests a minute and 800 a day. Free, and the signup takes an email
        and no payment method. THIS IS THE ONE THING WALLACE HAS TO DO: make
        the free key at twelvedata.com and put it in .env as
        TWELVEDATA_API_KEY. Nothing else changes — this file picks it up on
        its own. I have not created the account and will not.
        The 800-a-day allowance is enough: two pairs polled once a minute
        inside the only window this method enters in (09:30 to 10:30 New York)
        costs 120 requests a day, and even polling the whole New York session
        costs about 480.

    DUKASCOPY — the history, and it is already working.
        A bank's own tick data, aggregated to 1-minute candles with real
        highs and lows, back to 2003, free and with no key or signup at all.
        Bid and ask are published separately, which is where the spread this
        file CHARGES is measured from rather than guessed. Verified: 26 of
        the last 30 calendar days returned a full file and the four that did
        not were all Saturdays, when currencies are shut.
        WHY IT IS NOT THE LIVE FEED: the day's file is published after the
        day, not during it. Checked — the current day answers 404. It is an
        archive, so it is what the setups-per-day count below is measured on
        and it can never raise an alert.

    OANDA's practice API — real bank rates, free, and the same shape of venue
        he would actually execute on. NOT USED, because it needs an account
        created before a token exists and creating accounts is not mine to
        do. If Wallace ever wants the best possible live feed here, that is
        the one to ask for; the feed layer below takes a fourth source
        without anything else moving.

FOREX KEEPS THE CLOCK. CRYPTO THREW IT AWAY; THIS DOES NOT.
    "keep his trading methods just throw away the times for crypto thats all"
    — for CRYPTO. Currencies run around the clock on weekdays but the London
    and New York hours are real and he names them, with the times:

        "Asian session ... starts at 1800, and it goes till 3:00 ... London
         session goes from 3:00 till 8:30 ... New York pre-market opens at
         8:30 ... we go from 8:30, which is pre-market, to 9:30, which is
         market open. And then, we go from 9:30 all the way to 1700."

    So every session window is his, in New York time, unchanged from the
    stock instrument. His entry window is his too: nothing before 09:50,
    nothing new after 10:30, because the resolved specification's reading of
    his own day is "New York 09:30-10:30: the trading window. Everything he
    takes lives here." He trades all four of his markets in that one morning
    routine, so the currencies get the same morning.

    THE ONE THING THAT IS NOT HIS, AND IT IS A DECISION, NOT AN OMISSION:
    where one currency day is cut from the next. He never says, because on
    the markets he shows the venue decides it for him. Currencies roll at
    17:00 New York — every broker's daily candle, every swap charge, every
    chart a currency trader opens is cut there — so that is the boundary. The
    same reasoning crypto used for UTC midnight: the previous day's high is
    only a draw on liquidity because other people are looking at the same
    line. And he says the number himself, in the quote above: "all the way to
    1700".

    There is no closing bell, so there is no going home flat at 15:55 in the
    stock sense; the position is closed at the 17:00 roll instead.

COSTS ARE CHARGED AND NEVER CONSULTED
    The spread is measured from Dukascopy's own bid and ask files and
    subtracted from every closed trade so the money stays honest. NOTHING in
    this file declines a trade, prefers a pair, or moves a threshold because
    of what trading costs. test_tjr_forex.py reads this file's own source and
    proves it.

HOW IT IS JUDGED
    Not by backtest profit. He does not count historical replay as evidence
    and neither do we. The replay here produces one number nothing else can:
    how many setups a day each pair makes. Trade count is the constraint.

WHO SENDS THE MESSAGE
    Not this file. tjr_desk.py watches every market on one loop and calls the
    `live_step` below once a minute. This file's job stops at the decision
    and at the price feed.

SAFETY
    This module places no orders and imports nothing that can. It reads price
    frames and returns decisions. There is no order path in this file at all,
    which is the correct shape for a market the broker cannot reach.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import lzma
import os
import statistics
import struct
import time

import numpy as np
import pandas as pd

import tjr_alerts
import tjr_bot
from tjr_bot import (Bar, Config, Instrument, NewsCalendar, TjrBot,
                     TrendTracker)

REPO = os.path.dirname(os.path.abspath(__file__))

# The two he names, and nothing else.
PAIRS = ["GBP/USD", "GBP/JPY"]

# How each pair is spelled by each source. Read these; never build them by
# string surgery at the call site, which is how a slash ends up in a URL.
SYMBOLS = {
    "GBP/USD": {"yahoo": "GBPUSD=X", "dukascopy": "GBPUSD",
                "twelvedata": "GBP/USD", "digits": 5},
    "GBP/JPY": {"yahoo": "GBPJPY=X", "dukascopy": "GBPJPY",
                "twelvedata": "GBP/JPY", "digits": 3},
}

DERIVED_PATH = f"{REPO}/step443_forex_thresholds.json"
_UA = {"User-Agent": "Mozilla/5.0"}


def cache_name(pair: str, tf: str) -> str:
    """GBP/USD -> data_fx_GBPUSD_et_1m.parquet. The slash dies here, at the
    filename, and again in every source's own symbol table above."""
    return f"{REPO}/data_fx_{pair.replace('/', '')}_et_{tf}.parquet"


def to_et(ts_utc) -> pd.Series:
    """Naive UTC -> `t` as the bar's START in New York, which is the clock
    every session rule in this file is written in."""
    s = pd.to_datetime(ts_utc, utc=True)
    return s.dt.tz_convert("America/New_York").dt.tz_localize(None)


# ============================================================ THE FEEDS
#
# Three sources behind one shape. Each returns a frame with columns
# t / open / high / low / close, `t` being the bar's START in New York.


class DukascopyArchive:
    """A bank's own tick data as 1-minute candles. Free, no key, no signup.

    Published PER DAY, AFTER the day. That single fact is why this is the
    history and never the alert: the current day's file answers 404.

    Bid and ask are separate files, which is what lets the spread this file
    charges be measured rather than assumed.
    """

    HOST = "https://datafeed.dukascopy.com/datafeed"

    def url(self, pair: str, day: dt.date, side: str = "BID") -> str:
        sym = SYMBOLS[pair]["dukascopy"]
        # the month in this path is zero-based. It is not a typo and it is
        # the single easiest thing to get wrong here.
        return (f"{self.HOST}/{sym}/{day.year:04d}/{day.month - 1:02d}/"
                f"{day.day:02d}/{side}_candles_min_1.bi5")

    def day(self, pair: str, day: dt.date, side: str = "BID",
            tries: int = 4) -> pd.DataFrame | None:
        """One day of 1-minute candles, or None when there is no file — which
        on a Saturday is the correct answer, not a failure.

        A DROPPED CONNECTION IS NOT AN EMPTY DAY, and the difference matters
        more here than almost anywhere: a network blip swallowed silently
        would leave a hole in the history that looks exactly like a market
        that was shut, and every level marked near that hole would be wrong.
        So a transport failure is retried, and if it still will not come it
        is RAISED rather than returned as None. The caller counts absent
        files and failed downloads separately and says so out loud.
        """
        import requests
        last = None
        for k in range(tries):
            try:
                r = requests.get(self.url(pair, day, side), headers=_UA, timeout=40)
            except Exception as e:            # dropped connection, TLS, DNS
                last = e
                time.sleep(1.5 * (k + 1))
                continue
            if r.status_code == 404:
                return None                   # the market was shut. Correct.
            if r.status_code != 200 or not r.content:
                last = RuntimeError(f"{r.status_code} with {len(r.content)} bytes")
                time.sleep(1.5 * (k + 1))
                continue
            try:
                raw = lzma.LZMADecompressor().decompress(r.content)
            except lzma.LZMAError as e:
                last = e
                time.sleep(1.5 * (k + 1))
                continue
            break
        else:
            raise RuntimeError(f"{pair} {day} would not download after {tries} "
                               f"tries: {last}")
        n = len(raw) // 24
        if n == 0:
            return None
        scale = 10.0 ** SYMBOLS[pair]["digits"]
        # each record: seconds from midnight UTC, then open / close / low /
        # high as integers of the smallest price step, then the volume.
        rows = [struct.unpack(">5if", raw[i * 24:(i + 1) * 24]) for i in range(n)]
        base = dt.datetime(day.year, day.month, day.day)
        d = pd.DataFrame({
            "t": [base + dt.timedelta(seconds=r_[0]) for r_ in rows],
            "open": [r_[1] / scale for r_ in rows],
            "close": [r_[2] / scale for r_ in rows],
            "low": [r_[3] / scale for r_ in rows],
            "high": [r_[4] / scale for r_ in rows],
            "volume": [r_[5] for r_ in rows]})
        # A record with no volume is a minute in which nothing traded. Keeping
        # it would put a flat candle on the chart that never happened, and a
        # flat candle can be half of no two-candle swing — it would quietly
        # thin out every level the method marks.
        d = d[d["volume"] > 0].reset_index(drop=True)
        if len(d) == 0:
            return None
        d["t"] = to_et(d["t"])
        return d[["t", "open", "high", "low", "close"]]

    def history(self, pair: str, days: int = 200, end: dt.date | None = None,
                verbose: bool = False, pause: float = 0.0) -> pd.DataFrame:
        end = end or (dt.date.today() - dt.timedelta(days=1))
        out, misses, failed = [], 0, []
        for k in range(days):
            d = end - dt.timedelta(days=k)
            try:
                f = self.day(pair, d)
            except RuntimeError as e:
                failed.append(str(d))
                if verbose:
                    print(f"    {pair}: {e}")
                continue
            if f is None:
                misses += 1
            else:
                out.append(f)
            if pause:
                time.sleep(pause)
        if verbose:
            print(f"    {pair}: {days - misses - len(failed)} days present, "
                  f"{misses} absent (weekends and holidays — currencies are "
                  f"shut), {len(failed)} would not download")
        if failed:
            print(f"    {pair}: HOLES IN THE HISTORY on {', '.join(failed)} — "
                  f"levels marked near those dates are not trustworthy. "
                  f"Re-run --fetch to fill them.")
        if not out:
            return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
        return (pd.concat(out).sort_values("t")
                .drop_duplicates("t").reset_index(drop=True))

    def spread_pct(self, pair: str, days: int = 8,
                   end: dt.date | None = None) -> float | None:
        """The measured bid-ask spread as a share of the mid price.

        Taken from whole days of separate weeks rather than one snapshot, and
        reported as the MEDIAN so a single dislocated minute cannot move the
        number the account is charged.

        This is the number we CHARGE. It is not consulted anywhere.
        """
        end = end or (dt.date.today() - dt.timedelta(days=3))
        rel = []
        for k in range(days):
            d = end - dt.timedelta(days=7 * k)
            bid, ask = self.day(pair, d, "BID"), self.day(pair, d, "ASK")
            if bid is None or ask is None:
                continue
            j = bid.merge(ask, on="t", suffixes=("_b", "_a"))
            mid = (j["close_a"] + j["close_b"]) / 2.0
            ok = (j["close_a"] > j["close_b"]) & (mid > 0)
            rel += list(((j["close_a"] - j["close_b"]) / mid)[ok])
        return float(statistics.median(rel)) if rel else None


class YahooLive:
    """The live default. No account, no key, no signup, works today.

    Read the flaw in the module docstring before trusting a GBP/USD wick from
    here. It is measured, it is real, and TwelveDataLive is the fix.
    """

    name = "yahoo"
    needs_key = False

    def available(self) -> bool:
        return True

    def bars(self, pair: str, minutes: int, days: int) -> pd.DataFrame:
        import requests
        iv = {1: "1m", 5: "5m", 60: "60m"}[minutes]
        rng = f"{days}d"
        sym = SYMBOLS[pair]["yahoo"]
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
                         params={"interval": iv, "range": rng},
                         headers=_UA, timeout=25)
        j = (r.json().get("chart") or {}).get("result") or []
        if not j:
            return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
        res = j[0]
        q = res["indicators"]["quote"][0]
        d = pd.DataFrame({"t": pd.to_datetime(res["timestamp"], unit="s", utc=True),
                          "open": q["open"], "high": q["high"],
                          "low": q["low"], "close": q["close"]}).dropna()
        d["t"] = d["t"].dt.tz_convert("America/New_York").dt.tz_localize(None)
        return d.sort_values("t").drop_duplicates("t").reset_index(drop=True)

    def live(self, pair: str) -> dict:
        """{"5m": frame, "1m": frame} ready for the bot, freshest last."""
        return {"5m": self.bars(pair, 5, 60), "1m": self.bars(pair, 1, 7)}

    def last_price(self, pair: str) -> float:
        d = self.bars(pair, 5, 5)
        return float(d["close"].iloc[-1]) if len(d) else 0.0


class TwelveDataLive:
    """The upgrade. True tick-aggregated bars, real-time currencies on the
    free plan, 8 requests a minute and 800 a day.

    THE KEY IS NOT MADE HERE. Creating accounts is not mine to do. Wallace
    makes the free key (an email, no payment method) and puts it in .env as
    TWELVEDATA_API_KEY; this class then reports available() and the live path
    prefers it over Yahoo with nothing else changed.
    """

    name = "twelvedata"
    needs_key = True
    HOST = "https://api.twelvedata.com/time_series"

    def key(self) -> str:
        import os as _os
        k = _os.environ.get("TWELVEDATA_API_KEY")
        if k:
            return k
        try:
            from blofin_private import load_env
            return (load_env() or {}).get("TWELVEDATA_API_KEY", "")
        except Exception:
            return ""

    def available(self) -> bool:
        return bool(self.key())

    def bars(self, pair: str, minutes: int, size: int = 1500) -> pd.DataFrame:
        import requests
        iv = {1: "1min", 5: "5min", 60: "1h"}[minutes]
        r = requests.get(self.HOST, timeout=25, params={
            "symbol": SYMBOLS[pair]["twelvedata"], "interval": iv,
            "outputsize": size, "timezone": "UTC", "apikey": self.key()})
        j = r.json()
        if str(j.get("status")) == "error" or "values" not in j:
            raise RuntimeError(f"twelvedata said: {j.get('message', j)}")
        d = pd.DataFrame(j["values"])
        out = pd.DataFrame({
            "t": to_et(pd.to_datetime(d["datetime"], utc=True)),
            "open": d["open"].astype(float), "high": d["high"].astype(float),
            "low": d["low"].astype(float), "close": d["close"].astype(float)})
        return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)

    def live(self, pair: str) -> dict:
        return {"5m": self.bars(pair, 5), "1m": self.bars(pair, 1)}

    def last_price(self, pair: str) -> float:
        d = self.bars(pair, 5, size=5)
        return float(d["close"].iloc[-1]) if len(d) else 0.0


def live_feed():
    """The best live source that is actually switched on right now.

    Twelve Data when its free key is in .env, Yahoo otherwise. Never
    Dukascopy — that one is an archive and cannot see today.
    """
    td = TwelveDataLive()
    return td if td.available() else YahooLive()


def feed_report() -> dict:
    """What each source actually gives, so the choice is a fact and not a
    preference. Every number in here was measured, not read off a page."""
    return {
        "chosen_live": live_feed().name,
        "yahoo": {
            "signup": "none — no account, no key, no payment method",
            "rate_limit": "none published; polled once a minute it has not refused",
            "5_minute_history_days": 60,
            "1_hour_history_days": 730,
            "hours_covered": "all 24, every weekday",
            "measured_flaw": (
                "GBP/USD ONLY, and it is not small. Yahoo samples that pair once "
                "a minute instead of aggregating it: 7,099 of 7,195 one-minute "
                "bars had a high equal to their low, and the 5-minute high was "
                "the highest of five such samples on all 1,422 bars checked. "
                "Against 5,401 of the bank's own 5-minute candles over the same "
                "minutes, Yahoo's candle spans 65% OF THE TRUE HIGH-TO-LOW "
                "RANGE (a distance, not a share of anything else) and, once a "
                "constant 0.85-pip level offset is removed, it understates the "
                "high on 88.8% of bars and the low on 88.1% of bars."),
            "why_that_matters": (
                "this method trades price running PAST a marked level and coming "
                "back, and puts the stop just beyond how far it ran. A wick that "
                "is a third too short is exactly the wrong error in both places: "
                "runs past a level go unseen, and the stops that do get set sit "
                "too close."),
            "gbp_jpy_is_clean": "26 flat bars out of 7,195 — this affects one pair, not both",
            "enough_to_run_continuously": True,
        },
        "twelvedata": {
            "signup": "free key, email only, NO payment method",
            "wallace_must": "make the key at twelvedata.com, put TWELVEDATA_API_KEY in .env",
            "rate_limit": "8 requests a minute, 800 a day",
            "budget": ("two pairs once a minute across the 09:30-10:30 New York "
                       "entry window = 120 requests a day; the whole New York "
                       "session = about 480. Both fit inside 800."),
            "enough_to_run_continuously": True,
            "switched_on": TwelveDataLive().available(),
        },
        "dukascopy": {
            "signup": "none at all",
            "rate_limit": "none published; about 1.3 seconds per day-file",
            "history": "1-minute candles with real highs and lows, back to 2003",
            "bid_and_ask": "published separately — this is where the charged spread is measured",
            "why_not_live": ("the day's file appears after the day. The current "
                             "day answers 404, verified."),
            "enough_to_run_continuously": False,
        },
        "oanda_practice": {
            "signup": "an account must be created before a token exists",
            "status": "NOT USED — creating accounts is not the bot's to do",
            "note": ("the best live quality of the four, and the same shape of "
                     "venue he would execute on. Ask for it if Yahoo's GBP/USD "
                     "wicks ever prove to matter."),
        },
    }


# ================================================== THE DAY-ROLL SHIM
#
# WHY A SHIM AND NOT AN EDIT. tjr_bot.py is held by someone else. This puts
# one dispatch in front of one function and leaves the file alone, the same
# way tjr_crypto.py wraps session_levels.
#
# WHAT IT FIXES. tjr_bot.daily_bars cuts one daily candle from the next at
# midnight when a market has no closing bell — right for crypto, which
# genuinely rolls at midnight, and wrong for currencies, which roll at 17:00
# New York. The daily candle is what the direction read is taken from, so
# getting its boundary wrong moves the bias itself.
#
# THE DISPATCH is structural, not a name check: a market with NO BELL but a
# day boundary that is not midnight is exactly and only this case. Crypto
# carries boundary 0 and takes the original; every stock has a bell and takes
# the original.

_ORIGINAL_DAILY_BARS = tjr_bot.daily_bars
_INSTALLED = False


def rolled_daily_bars(d5: pd.DataFrame, inst: Instrument) -> pd.DataFrame:
    """One candle per currency day, cut at the instrument's own roll hour.

    `close_t` is when the candle FINISHES, which is the only moment the bot
    is allowed to know it exists — the same causality rule as everywhere.
    """
    cols = ["t", "open", "high", "low", "close", "close_t"]
    if len(d5) == 0:
        return pd.DataFrame(columns=cols)
    off = pd.Timedelta(hours=inst.day_boundary_hour)
    g = d5.groupby((d5["t"] - off).dt.normalize() + off)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "t"
    out = out.reset_index()
    out["close_t"] = out["t"] + pd.Timedelta(days=1)
    return out


# ============================================ THE MONDAY HOLE, AND ITS FIX
#
# WHAT WOULD HAVE GONE WRONG, SILENTLY. tjr_bot marks "the previous day" and
# "the previous New York session" off the last calendar day that had any bars
# at all. On a market that is shut all weekend and opens again on SUNDAY
# EVENING, that last day is Sunday — and Sunday's own currency day, the
# window from Saturday five o'clock to Sunday five o'clock, is empty because
# nothing traded in it. So on every Monday morning the bot would have marked
# NO previous-day high, NO previous-day low and NO previous New York levels,
# and it would have said nothing about it. Roughly one morning in five would
# have been quietly running on a thinner pool than every other morning.
#
# THE FIX is not a new rule, it is the same rule read correctly: "the
# previous day" means the last currency day that actually traded. On a Monday
# that is Friday's, which ran from Thursday five o'clock to Friday five
# o'clock. This walks back until it finds one instead of giving up after one
# step.
#
# Everything else in his level list is untouched: Asia, London, New York and
# this morning's pre-market are marked exactly as the original marks them,
# off the same windows, in the same New York hours.

def _last_non_empty(d5: pd.DataFrame, first_end, span: pd.Timedelta,
                    not_after=None, back: int = 10):
    """Walk back a day at a time from `first_end` until the window of length
    `span` ending there actually contains bars. Returns (start, end) or None.

    `not_after` is the causality guard and it is not optional in spirit: a
    window is only allowed if it had already CLOSED by then. Without it the
    walk would happily start at a window ending this evening, which has not
    happened yet — it would only look empty because the history handed in
    stops at this morning, and that is luck, not a rule.
    """
    if not_after is not None:
        while first_end > not_after:
            first_end = first_end - pd.Timedelta(days=1)
    for k in range(back):
        end = first_end - pd.Timedelta(days=k)
        start = end - span
        if len(d5[(d5["t"] >= start) & (d5["t"] < end)]) > 0:
            return start, end
    return None


def forex_session_levels(d5: pd.DataFrame, day: pd.Timestamp,
                         inst: Instrument) -> list:
    """Asia, London, New York, this morning's pre-market, and the previous
    currency day — his list, with the previous day found by walking back to
    one that traded rather than by stepping back exactly one calendar day.

    The `formed` stamp on every level is the moment its window CLOSED, which
    is the first moment the level could be known. Same causality rule as
    everywhere else in this bot.
    """
    Level = tjr_bot.Level
    b = pd.Timedelta(hours=inst.day_boundary_hour)
    day = pd.Timestamp(day).normalize()
    open_t = tjr_bot.session_start(day, inst)
    windows = []

    # THE PREVIOUS CURRENCY DAY: the last 24 hours between rolls that had
    # both already finished by this morning's open AND actually traded. On a
    # Tuesday that is Monday five o'clock back to Sunday five o'clock. On a
    # Monday the roll at five o'clock last night starts TODAY's currency day,
    # not yesterday's, and the two rolls before that bracket a shut weekend —
    # so the walk keeps going and lands on Friday's, which is right.
    prev = _last_non_empty(d5, day + b, pd.Timedelta(days=1), not_after=open_t)
    if prev is not None:
        windows.append(("prev_day", prev[0], prev[1]))

    if inst.early_session_window:
        e0, e1 = inst.early_session_window
        windows.append(("asia", day - pd.Timedelta(days=1) + pd.Timedelta(hours=e0),
                        day + pd.Timedelta(hours=e1)))
    if inst.prior_session_window:
        p0, p1 = inst.prior_session_window
        windows.append(("london", day + pd.Timedelta(hours=p0),
                        day + pd.Timedelta(hours=p1)))
    if inst.own_session_window:
        n0, n1 = inst.own_session_window
        ny = _last_non_empty(d5, day + pd.Timedelta(hours=n1),
                             pd.Timedelta(hours=n1 - n0), not_after=open_t)
        if ny is not None:
            windows.append(("new_york", ny[0], ny[1]))
        windows.append(("premarket_ny", day + pd.Timedelta(hours=n0), open_t))

    out = []
    for tag, start, end in windows:
        h, l = tjr_bot._window_extremes(d5, start, end)
        if h is not None:
            out.append(Level(h, +1, tag, end))
            out.append(Level(l, -1, tag, end))
    return out


_ORIGINAL_SESSION_LEVELS = tjr_bot.session_levels


def install() -> None:
    """Two dispatches, both branching on a structural property of the market
    rather than on its name: NO BELL, but a day boundary that is not
    midnight. Currencies are the only instrument on this desk in that
    position — crypto rolls at midnight and every stock has a bell — so both
    the crypto path and the index path take the original function unchanged.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    def is_forex(inst) -> bool:
        return (not inst.has_closing_bell) and inst.day_boundary_hour != 0

    prev_daily = tjr_bot.daily_bars
    prev_levels = tjr_bot.session_levels

    def daily_dispatch(d5, inst=tjr_bot.US_INDEX_ETF):
        if is_forex(inst):
            return rolled_daily_bars(d5, inst)
        return prev_daily(d5, inst)

    def level_dispatch(d5, day, inst=tjr_bot.US_INDEX_ETF):
        if is_forex(inst):
            return forex_session_levels(d5, day, inst)
        return prev_levels(d5, day, inst)

    tjr_bot.daily_bars = daily_dispatch
    tjr_bot.session_levels = level_dispatch
    _INSTALLED = True


install()


# ====================================================== THE INSTRUMENT
FX_DAY_ROLL_HOUR_ET = 17          # see the module docstring; his "1700"


def forex_instrument(pair: str, spread_pct: float) -> Instrument:
    """One currency pair, as an Instrument.

    EVERY SESSION FIELD IS SET, and every one of them is his, in New York
    time, quoted in the module docstring:
        Asia    18:00 -> 03:00
        London  03:00 -> 08:30
        New York 08:30 -> 18:00
    and his entry window on top of them: nothing before 09:50, nothing new
    after 10:30.

    What is NOT set is `has_closing_bell`. There is no bell in currencies, so
    the daily candle is the whole day between rolls rather than a slice of
    one, and the shim above cuts it at 17:00 rather than at midnight.
    """
    return Instrument(
        name=f"forex_{pair.replace('/', '')}",
        round_trip_cost_pct=spread_pct,    # measured, charged, never consulted
        day_boundary_hour=FX_DAY_ROLL_HOUR_ET,
        open_t=dt.time(9, 30),             # New York's open: where new money arrives
        manip_end_t=dt.time(9, 50),
        entry_ideal_end_t=dt.time(10, 10),
        cutoff_t=dt.time(10, 30),          # HARD: "if I can't find a trade by 10:30, I'm done"
        flat_t=dt.time(16, 55),            # out before the roll, not at a bell
        close_t=dt.time(17, 0),            # the roll itself
        prior_session_window=(3, 8.5),     # London, his hours
        early_session_window=(18, 3),      # Asia, his hours
        own_session_window=(8.5, 18),      # New York, his hours
        has_closing_bell=False,
        level_minutes=(60, 240),
        working_minutes=5,
        trigger_minutes=1,
        continuation_minutes=15,
        target1_minutes=15,
        # Currencies have no futures-session open of their own to hang the
        # higher-timeframe grid on, and the day already rolls at 17:00, so
        # the 4-hour candles sit on that same roll.
        candle_anchor_hour=FX_DAY_ROLL_HOUR_ET)


def load_derived() -> dict:
    if os.path.exists(DERIVED_PATH):
        with open(DERIVED_PATH) as f:
            return json.load(f)
    return {}


def forex_config(pair: str, spread_pct: float | None = None,
                 account_start: float = 100_000.0,
                 derived: dict | None = None) -> Config:
    """The method's Config with every SPY-measured number replaced by the
    pair's own, and both vetoes decided deliberately."""
    derived = derived if derived is not None else load_derived()
    row = derived.get(pair) or {}
    if spread_pct is None:
        spread_pct = row.get("spread_pct")
        if spread_pct is None:
            raise RuntimeError(
                f"no measured spread for {pair}. Run: python3 tjr_forex.py --derive")
    ceiling = row.get("sweep_max_age_bars") or 12

    return Config(
        instrument=forex_instrument(pair, float(spread_pct)),
        account_start=account_start,

        # -- RE-DERIVED #1: the stop buffer ------------------------------
        # HIS rule: clear your broker's spread. The stock config carries
        # 0.0001 because that is SPY's spread. This pair's spread is its own
        # number and this is it, measured from the bank's own bid and ask.
        stop_buffer_pct_of_price=float(spread_pct),

        # -- RE-DERIVED #2: how long a taken level stays pending ---------
        # Twice this pair's own measured median gap between a level being
        # taken and the 5-minute turning, which is the rule the stock number
        # came from.
        sweep_max_age_bars=ceiling,

        # -- RE-DERIVED #3: how large a position the account may hold -----
        # NOT the stock 4x, and this one would have gone wrong silently. The
        # 4x is what a US stock broker reports for day trading, and on a
        # currency pair quoted near 1.34 it would have capped the position at
        # about 299,000 pounds — smaller than what one percent of the account
        # asks for at an ordinary stop, on nearly every trade. The alert
        # would then have quietly told him to take a smaller trade than his
        # own rule wants, and said nothing about why.
        #
        # 50 is the ceiling a US retail account is allowed on a major
        # currency pair. It is an outside number, not a guess about his
        # account, and it is an UPPER bound: if his own broker allows less,
        # his ticket will say so and the alert's face-value line tells him
        # what he is being asked to hold before he gets there.
        #
        # At 50 the limit does not bind on either pair at any ordinary stop,
        # which IS the intended result: we are not the venue here and should
        # not be quietly shrinking his trade on a limit we cannot read. Every
        # alert says the money at risk and the face value out loud, so the
        # one thing that can refuse the size is his own broker, in front of
        # him, rather than this file, behind him.
        buying_power_multiple=50.0,

        # -- THE BOTH-CHARTS VETO: OFF, and it is a decision -------------
        # "if the S&P 500 and the NASDAQ on the five minute are not aligned,
        # I do not want to be taking a trade." That works on two funds
        # holding overlapping baskets of ONE market, where a disagreement is
        # a contradiction. GBP/USD and GBP/JPY share the pound and nothing
        # else: when GBP/USD turns up and GBP/JPY does not, that is the
        # dollar and the yen doing different things, which is an ordinary
        # move and not a contradiction. Vetoing on it would discard a valid
        # read because a different market disagreed. Each pair runs in its
        # own call, so the two charts never meet.
        enforce_index_agreement=False,

        # -- THE PRE-MARKET CARVE-OUT: ON --------------------------------
        # Currencies trade all night and the London hours before the New
        # York open are the most active of the day. If a marked level was
        # already taken and price is already reacting off it, that was the
        # day's grab — the exact case he describes.
        premarket_sweep_carries_forward=True,
    )


# ================================================ DATA: FETCH AND CACHE
def fetch(pairs=None, days: int = 200, verbose: bool = True) -> None:
    """Build the 1-minute history from the bank archive and cache it, plus
    the 5-minute chart resampled from it.

    Resampled rather than downloaded: a 5-minute candle built from real
    1-minute highs and lows has the real high and low, which is the whole
    thing Yahoo cannot give us on GBP/USD.
    """
    duka = DukascopyArchive()
    for pair in (pairs or PAIRS):
        if verbose:
            print(f"  {pair}: pulling {days} days of 1-minute candles")
        d1 = duka.history(pair, days=days, verbose=verbose)
        if len(d1) == 0:
            print(f"    {pair}: nothing came back")
            continue
        d1.to_parquet(cache_name(pair, "1m"))
        d5 = resample_from_1m(d1, 5)
        d5.to_parquet(cache_name(pair, "5m"))
        if verbose:
            print(f"    {pair}: {len(d1):,} one-minute bars, {len(d5):,} five-minute, "
                  f"{d1['t'].min()} .. {d1['t'].max()}")


def resample_from_1m(d1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    g = d1.groupby(d1["t"].dt.floor(f"{minutes}min"))
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "t"
    return out.reset_index()


def load(pair: str) -> dict:
    """{"5m": frame, "1m": frame}, `t` in New York."""
    return {tf: pd.read_parquet(cache_name(pair, tf)) for tf in ("5m", "1m")}


# ======================================================= DERIVATION
def measure_sweep_to_signal(d5: pd.DataFrame, cfg: Config,
                            lookback_days: int = 200) -> dict:
    """How long a taken level stays pending here before the 5-minute turns.

    tjr_bot ships 12 and says why: SPY's median measured 6 bars and the
    ceiling is twice the median. The RULE is "twice the median"; the 6 is
    SPY's. This measures this pair's own median and applies the same rule.
    Causal throughout: the pool is marked from bars completed before the day
    starts and the walk inside the day is forward only.
    """
    inst = cfg.instrument
    if len(d5) == 0:
        return {"n": 0, "median": None, "ceiling": None}
    end = d5["t"].max()
    d5 = d5[d5["t"] >= end - pd.Timedelta(days=lookback_days)].reset_index(drop=True)
    gaps = []
    for day in sorted(set(d5["t"].dt.normalize())):
        hist = d5[d5["t"] < day]
        if len(hist) < 500:
            continue
        hist = hist[hist["t"] >= day - pd.Timedelta(days=10)]
        pool = []
        for m in inst.level_minutes:
            pool += tjr_bot.swing_levels(hist, m, day, f"{m // 60}h")
        pool = tjr_bot._unswept(pool, hist, day)
        if not pool:
            continue
        session = d5[(d5["t"] >= day + pd.Timedelta(hours=9, minutes=30)) &
                     (d5["t"] < day + pd.Timedelta(hours=17))]
        t5 = TrendTracker()
        for r in hist.tail(300).itertuples():
            t5.update(Bar(r.t, r.open, r.high, r.low, r.close))
        pending = None
        for r in session.itertuples():
            bos = t5.update(Bar(r.t, r.open, r.high, r.low, r.close))
            if pending is not None:
                d, age = pending
                if bos == d:
                    gaps.append(age + 1)
                    pending = None
                elif bos == -d or age >= 60:
                    pending = None
                else:
                    pending = (d, age + 1)
            if pending is None:
                for lv in pool:
                    if (lv.side > 0 and r.high > lv.price) or \
                       (lv.side < 0 and r.low < lv.price):
                        pending = (-lv.side, 0)
                        break
    if not gaps:
        return {"n": 0, "median": None, "ceiling": None}
    med = float(statistics.median(gaps))
    return {"n": len(gaps), "median": med, "ceiling": int(round(2 * med))}


def derive_all(pairs=None, verbose: bool = True) -> dict:
    """Measure every re-derived threshold from each pair's own bars and the
    bank's own bid and ask, and write them down."""
    duka = DukascopyArchive()
    out = {}
    for pair in (pairs or PAIRS):
        sp = duka.spread_pct(pair)
        row = {"spread_pct": None if sp is None else round(sp, 8),
               "spread_pct_of_price": None if sp is None else round(100 * sp, 5),
               "spread_pips": (None if sp is None else
                               round(sp * _mid_guess(pair) /
                                     tjr_alerts.pip_size(pair), 2))}
        try:
            d5 = pd.read_parquet(cache_name(pair, "5m"))
            cfg = Config(instrument=forex_instrument(pair, sp or 0.0001))
            m = measure_sweep_to_signal(d5, cfg)
            row.update({"sweep_median_bars": m["median"],
                        "sweep_max_age_bars": m["ceiling"], "sweep_n": m["n"]})
        except FileNotFoundError:
            row.update({"sweep_median_bars": None, "sweep_max_age_bars": None,
                        "sweep_n": 0})
        out[pair] = row
        if verbose:
            print(f"  {pair}  spread {row['spread_pct_of_price']}% of price "
                  f"({row['spread_pips']} pips)   gap median "
                  f"{row['sweep_median_bars']} bars   ceiling "
                  f"{row['sweep_max_age_bars']} (n={row['sweep_n']})")
    with open(DERIVED_PATH, "w") as f:
        json.dump(out, f, indent=2)
    return out


def _mid_guess(pair: str) -> float:
    """The pair's own last cached close, used only to turn a spread expressed
    as a share of price into pips for the report. Never used in a decision."""
    try:
        d = pd.read_parquet(cache_name(pair, "5m"))
        return float(d["close"].iloc[-1])
    except Exception:
        return 1.0


# ======================================================= THE REPLAY
#
# ONE PAIR PER run_day CALL. tjr_bot.run_day takes at most one trade across
# every symbol handed to it, which is right for two charts of one market and
# wrong for two separate currency pairs — handing it both would cap the pair
# at one trade a day between them and let whichever fired first silence the
# other. Each pair gets its own call and its own losing-streak state. That is
# also what makes the both-charts veto structurally absent rather than merely
# switched off.

def days_in(data: dict, start=None, end=None) -> list:
    t = data["1m"]["t"]
    if start is not None:
        t = t[t >= pd.Timestamp(start)]
    if end is not None:
        t = t[t < pd.Timestamp(end) + pd.Timedelta(days=1)]
    return sorted(t.dt.normalize().unique())


def slice_for(data: dict, day: pd.Timestamp, cfg: Config) -> dict:
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    return {tf: data[tf][(data[tf]["t"] >= lo) & (data[tf]["t"] < hi)]
            .reset_index(drop=True) for tf in ("5m", "1m")}


def run_pair(pair: str, start=None, end=None, cfg: Config | None = None,
             data: dict | None = None, verbose: bool = False) -> dict:
    cfg = cfg or forex_config(pair)
    data = data or load(pair)
    # US releases move the pound against the dollar as hard as they move the
    # index, so the news calendar STAYS ON here. Crypto switched it off for
    # having no CPI; currencies very much have one.
    news = NewsCalendar()
    bot = TjrBot(cfg, news)
    trades, reasons, skipped = [], {}, 0
    days = days_in(data, start, end)
    for day in days:
        day = pd.Timestamp(day)
        win = slice_for(data, day, cfg)
        # A DAY IS ONLY A DAY IF THE SESSION HAPPENED IN IT. Currencies
        # reopen on Sunday EVENING, so a Sunday has bars — just none between
        # half past nine and five, which is the only stretch this method ever
        # enters in. Counting those Sundays as trading days would divide the
        # setup count by about fifteen percent more days than actually
        # existed and quietly understate how often the setup fires.
        i = cfg.instrument
        sess = win["1m"]
        sess = sess[(sess["t"] >= day + pd.Timedelta(hours=i.open_t.hour,
                                                     minutes=i.open_t.minute)) &
                    (sess["t"] < day + pd.Timedelta(hours=i.close_t.hour))]
        if len(sess) == 0:
            skipped += 1
            continue
        res = bot.run_day({pair: win}, day)
        if res["trade"] is not None:
            trades.append(res["trade"])
        for why in res["stand_down"].values():
            reasons[why] = reasons.get(why, 0) + 1
        if verbose and res["trade"] is not None:
            tr = res["trade"]
            print(f"  {day:%Y-%m-%d} {pair} "
                  f"{'buy' if tr.direction > 0 else 'sell':4s} off the "
                  f"{tr.level_tf} level at {tr.level_price:,.4f} -> {tr.outcome}")
    return {"pair": pair, "days": len(days) - skipped, "trades": trades,
            "reasons": reasons, "account": bot.account}


def setups_per_day(pairs=None, start=None, end=None, verbose: bool = True) -> dict:
    """THE NUMBER THIS EXERCISE EXISTS TO PRODUCE.

    A "setup" is a completed sequence that reached an entry: a marked level
    pushed through, a 5-minute confirmation, a pullback into the middle of
    that move or into a gap it left, and a 1-minute trigger. One per pair per
    day at most, which is the bot's own rule.

    No profit claim. He does not count replay as evidence and neither do we.
    """
    out, derived = {}, load_derived()
    for pair in (pairs or PAIRS):
        try:
            cfg = forex_config(pair, derived=derived)
            r = run_pair(pair, start, end, cfg=cfg)
        except FileNotFoundError:
            if verbose:
                print(f"  {pair}  no cached bars — run: python3 tjr_forex.py --fetch")
            continue
        n, days = len(r["trades"]), max(r["days"], 1)
        buys = sum(1 for t in r["trades"] if t.direction > 0)
        out[pair] = {
            "days": r["days"], "setups": n, "per_day": round(n / days, 3),
            "one_every_n_days": round(days / n, 1) if n else None,
            "buys": buys, "sells": n - buys,
            "cost_charged_pct_of_price": round(
                100 * cfg.instrument.round_trip_cost_pct, 5),
            "sweep_max_age_bars": cfg.sweep_max_age_bars,
            "top_stand_down": sorted(r["reasons"].items(),
                                     key=lambda kv: -kv[1])[:4]}
        if verbose:
            o = out[pair]
            print(f"  {pair}  {o['days']:>4} days   {n:>3} setups   "
                  f"{o['per_day']:.3f}/day   {buys} buys / {n - buys} sells")
    return out


# ============================================================ LIVE
def usd_per_quote(pair: str, gbpusd: float, gbpjpy: float) -> float:
    """Dollars per one unit of the pair's quote currency.

    GBP/USD is quoted in dollars already, so this is 1. GBP/JPY is quoted in
    yen, and dollars per yen is GBP/USD divided by GBP/JPY — worked out from
    the two prices we already have rather than from a third feed we would
    then have to keep alive.
    """
    if pair == "GBP/USD":
        return 1.0
    if gbpjpy <= 0:
        return 0.0
    return float(gbpusd) / float(gbpjpy)


def live_step(pair: str, data: dict, now: pd.Timestamp, account: float,
              cfg: Config | None = None, clock_open: bool = True,
              week_pnl: dict | None = None) -> dict:
    """The one call the forex watcher makes. Returns an intention. There is
    no order path in this file, so it can never do anything else.

    data        : {"5m": frame, "1m": frame} with `t` in New York, ending at
                  the last CLOSED 1-minute bar
    now         : the CLOSE time of that bar, New York
    account     : the equity the size is worked out from
    clock_open  : whether currencies are trading at all. Unlike the stock
                  path this is not Alpaca's clock — the broker has no
                  currencies — so it is the weekday-and-roll test below.

    Returns {"action": "stand_down" | "wait" | "enter", ...}.

    THERE IS DELIBERATELY NO SHARE COUNT IN WHAT COMES BACK, and leaving it
    out is a correctness fix rather than tidiness. tjr_bot sizes a position
    as "money risked divided by the distance to the stop", which is right
    wherever the price is quoted in dollars — a stock, and GBP/USD. On
    GBP/JPY the distance to the stop is in YEN, so that division gives a
    number that is not pounds and not lots and not anything, and it would be
    off by the yen rate: about 145 times too small. The size is worked out
    once, in tjr_alerts.position_size, where the conversion is done on
    purpose and tested by hand. The money at risk below is correct on both
    pairs and is what that function is handed.
    """
    cfg = cfg or forex_config(pair)
    if not isinstance(now, pd.Timestamp):
        return {"action": "stand_down", "reason": "the clock is unreadable"}
    if not clock_open:
        return {"action": "stand_down",
                "reason": "currencies are shut — it is the weekend"}
    inst = cfg.instrument
    if now.time() < inst.open_t:
        return {"action": "stand_down",
                "reason": "before the New York open — he never enters here"}
    if tjr_bot.past_cutoff(now, inst):
        return {"action": "stand_down",
                "reason": "past 10:30 in New York — done looking for today"}

    day = now.normalize()
    bot = TjrBot(cfg, NewsCalendar())
    bot.account = float(account)
    bot.week_pnl = dict(week_pnl or {})
    res = bot.run_day({pair: data}, day, stop_at=now)
    tr = res["trade"]
    if tr is None:
        why = "; ".join(f"{k}: {v}" for k, v in res["stand_down"].items())
        return {"action": "wait", "escalated": res["escalated"],
                "reason": why or "the sequence has not completed yet"}
    if tr.entry_t != now - pd.Timedelta(minutes=1):
        return {"action": "wait",
                "reason": f"the entry fired at {tr.entry_t}, already handled"}
    if tjr_bot.too_early(now, inst):
        return {"action": "wait",
                "reason": "still inside the first twenty minutes, where he does not enter"}
    return {"action": "enter", "symbol": pair, "direction": tr.direction,
            "side": "buy" if tr.direction > 0 else "sell",
            "reference_price": tr.entry, "stop": tr.stop,
            "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
            "target_fractions": tjr_bot.target_fractions(len(tr.targets), cfg),
            "partial_fraction": cfg.partial_fraction,
            "stop_anchor": tr.stop_anchor, "level_tf": tr.level_tf,
            "level_price": tr.level_price, "confirmed_by": tr.confirm_kind,
            "pullback_into": tr.pullback_kind,
            "risk_dollars": tr.risk_dollars, "risk_wanted": tr.risk_wanted,
            "clamped": tr.clamped, "escalated": res["escalated"],
            "entry_t": tr.entry_t}


def currencies_open(now: dt.datetime) -> bool:
    """Currencies trade from 17:00 New York on Sunday to 17:00 New York on
    Friday. That is the venue's own week and it is not ours to move."""
    wd, h = now.weekday(), now.hour
    if wd == 5:
        return False
    if wd == 6:
        return h >= FX_DAY_ROLL_HOUR_ET
    if wd == 4:
        return h < FX_DAY_ROLL_HOUR_ET
    return True


# ------------------------------------------------ WHO ACTUALLY WATCHES THIS
#
# NOT THIS FILE. tjr_desk.py watches every market on one loop, with one
# message format, and it calls the `live_step` above once a minute. A
# currency-only watcher used to live here and was removed when the desk
# arrived: two watchers means two places for the message format to drift, and
# the message IS the product now.
#
# This file's job stops at the decision and the price feed.

def main(argv):
    if "--fetch" in argv:
        print("building the currency history from the bank archive")
        fetch()
        return
    if "--derive" in argv:
        print("re-deriving every threshold from each pair's own bars and quotes")
        derive_all()
        return
    if "--feeds" in argv:
        print(json.dumps(feed_report(), indent=2))
        return
    if "--sample-alert" in argv or "--watch" in argv:
        print("the alerting lives in tjr_desk.py now, for every market at "
              "once. Try:  python3 tjr_desk.py --samples")
        return
    start = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else None
    end = argv[2] if len(argv) > 2 and not argv[2].startswith("-") else None
    print("=" * 78)
    print("currencies: setups per day, per pair — what trade count is limited by")
    print("=" * 78)
    print(json.dumps(setups_per_day(start=start, end=end), indent=2, default=str))


if __name__ == "__main__":
    import sys
    main(sys.argv)
