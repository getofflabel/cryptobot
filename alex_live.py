"""alex_live.py — Alex Gonzalez's method, driving the live FOREX and GOLD books.

THE DECISION THIS FILE IMPLEMENTS

    Wallace, 2026-07-26: "trade gold as xauusdt on blofin", and forex on the
    OANDA practice account. Alex drives both — his own words put gold on the
    same method as a currency pair: "I'm taking this trade as if it were to be
    a foreign exchange currency pair ... based off market structure, not for
    the commodity that it is."

    So there are TWO BOOKS in this file and ONE METHOD behind them:

        forex   EUR/USD, GBP/USD, GBP/JPY on OANDA practice
        gold    XAUT-USDT on BloFin demo, decided on OANDA XAU/USD candles

    METHODS NEVER MIX. Nothing here reads a TJR level, bias or session, and
    nothing here reads anything of Craig's. The old TJR/GLD gold path
    (`tjr_gold.py`) is retired from live duty and left importable for replay,
    exactly as `tjr_crypto.py` was when Craig took crypto.

WHAT SHIPS — THE step472 DEFAULTS, EXACTLY AND WITHOUT A DIAL TOUCHED

    `alex_engine.DumbConfig()` as it stands after step472 (67 tests green) is
    what runs. Written out so the list can be checked rather than trusted:

        chart          the 4 hour, and only it (his June-2026 spine)
        setups         BOTH of his patterns — the engulfing candle in the
                       direction of 4-hour structure, and the head and
                       shoulders at its neckline retest
        trigger        the engulfing candle alone (`signal_mode="engulf"`);
                       his rejection/doji half is built and OFF
        target         the nearest structure point that still pays 1:2
                       (`target_mode="structure"`), 1:2 itself being the
                       validity filter — no level that pays it, no trade
        stop           at structure, a quarter of the average range beyond it
        session        his pre-London/London window, so the only 4-hour
                       closes that can ever fire are the 01:00 and the 05:00
                       New York ones, Monday to Thursday
        size           quality-weighted, scaling UP from the base — never a
                       cap on an ordinary trade
        weekly close   ON    — WALLACE'S RULING, 2026-07-27: "alex: on". It
                       overrides newest-governs, which had it off. See
                       `WEEKLY_CLOSE` for the evidence and the conflict.
        structure-shift exit OFF
        cadence cap    OFF   (Wallace, 2026-07-27: "if you see the setup, take
                       the trade. its a demo at the end of the day")

    THE BASE RISK SHARE IS `RISK_PCT` BELOW: 0.03 of the account per trade,
    the bottom of his own-money 3-5% band and the top of Wallace's standing
    "do the 1-3%" ruling. It is the same number for both books and it is set
    in one place.

    AND THE MONEY-GAME LADDER SITS ON TOP OF IT FOR GOLD — WALLACE'S RULING
    of the same day: "ladder on gold too". Gold shares his $2,178 BloFin
    stake with the Craig book, so both books read the venue's LIVE equity
    when they size and one book's loss shrinks the other's next bet instead
    of each of them betting the whole stake. Forex is not eligible for it and
    that is Alex's own rule rather than a choice: the OANDA account holds
    $100,000 and "anything over $25,000 is where you should focus on the
    percentage game". See `GOLD_BOOK` and `in_our_words()`.

ONE DECISION PATH, SO REPLAY AND LIVE CANNOT DRIFT

    The 36x sizing bug in this project happened because a replay and a live
    runner each had their own arithmetic, so every backtest described a bot
    nobody was running. So this file does not re-implement one line of the
    method:

      * setups come from `alex_engine.find_setups_dumb` and
        `alex_engine.find_setups_hs` — the same two functions step472
        measured — called on the same frame with the window narrowed to the
        4-hour candle that has just closed;
      * the trade's whole life comes from `alex_engine.manage`, RE-RUN FROM
        THE ENTRY ON EVERY POLL against the 15-minute bars that have closed
        so far. It is the replay's own function, not a live copy of it, so a
        stop, a target, his Friday exit and the 30-day cap all resolve at the
        identical bar and the identical price in both;
      * the size comes from `tjr_bot.size_position` through
        `tjr_alerts.position_size`, the one place in this project that turns
        a stop into a number of units;
      * `test_alex_live.py::test_the_replay_and_the_live_engine_agree` runs
        the same five years of candles through `alex_engine.run_instrument`
        and through this Engine and fails on the first trade that differs.

THE GOLD BASIS, WHICH IS THE ONE GENUINELY NEW PIECE OF PLUMBING

    The gold CHART is OANDA XAU/USD. The gold ORDER is BloFin XAUT-USDT.
    Those are two different prices for the same metal and they are not equal:
    measured 2026-07-27, XAU/USD mid was 4,088.85 and XAUT-USDT marked at
    4,077.60 — XAUT eleven dollars and twenty-five cents BELOW spot, which is
    0.275% of the price. A stop on this book is typically about 1.5% of the
    price, so copying a level across raw would move the stop by about a fifth
    of its own width. That is not a rounding error.

    So every price crosses explicitly, through `gold_basis` and `convert`:

        basis = the BloFin mark divided by the OANDA mid, both read in the
                same second
        entry, stop and target are all MULTIPLIED by it

    A RATIO AND NOT A SUBTRACTION, on purpose. Multiplying leaves the stop's
    distance as a SHARE OF THE PRICE unchanged, and that share is what sets
    the leverage, the margin and the liquidation distance on a perpetual. A
    fixed dollar offset would leave the dollars alone and move the percentage,
    which is the number the exchange actually acts on.

    IF EITHER PRICE CANNOT BE READ, NOTHING IS SENT. There is no fallback to
    1.0 and no copying the level across raw — that is the yen-rate mistake in
    a different coat. Same for a basis further than `MAX_BASIS_DRIFT` from
    parity, which does not mean gold moved, it means one of the two feeds is
    wrong.

SAFETY

    THIS MODULE PLACES NO ORDER BY ITSELF. It returns ACTIONS and the desk
    executes them through venue.py, which asks attribution.py first — so even
    here the bot can only ever touch a position it opened. It writes exactly
    one file, its own measured stop floors, and only when asked.

    THE STOP RIDES IN WITH THE ENTRY ON BOTH VENUES. OANDA attaches it inside
    the same request; BloFin attaches it inside the same request. Neither
    book has a moment where a position exists with nothing under it, and
    neither venue will accept an opening order without one.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

import alex_engine as ae

REPO = os.path.dirname(os.path.abspath(__file__))

# ============================================================ THE TWO BOOKS
#
# The desk spells a pair with a slash because that is what `tjr_alerts` writes
# messages about and what `venue.py` translates. The engine spells it with an
# underscore because that is what OANDA calls it and what the parquet on disk
# is named. The translation lives HERE and nowhere else.

FOREX = {"EUR/USD": "EUR_USD", "GBP/USD": "GBP_USD", "GBP/JPY": "GBP_JPY"}

GOLD_SYMBOL = "XAU/USD"          # what the message and the chart call it
GOLD_INSTRUMENT = "XAU_USD"      # the OANDA tape the decision is read off
GOLD_VENUE_SYMBOL = "XAUT-USDT"  # the BloFin contract the order goes to

SYMBOLS = dict(FOREX)
SYMBOLS[GOLD_SYMBOL] = GOLD_INSTRUMENT


def instrument_for(symbol: str) -> str:
    """"EUR/USD" -> "EUR_USD". Unknown symbols pass through so the failure is
    a missing parquet with the name in it rather than a silent wrong tape."""
    return SYMBOLS.get(symbol, symbol)


def symbol_for(instrument: str) -> str:
    for k, v in SYMBOLS.items():
        if v == instrument:
            return k
    return instrument


# ===================================================== THE ONE CONFIG VALUE
#
# HIS OWN-MONEY BAND: "I'm risking anywhere from 1 to 3% of my account per
# trade" and, on his own money, 3-5% (VzMlFZbWA0Y.txt 00:08:48, 2024-01-28).
# WALLACE'S STANDING RULING: "do the 1-3%". The bottom of his own-money band
# and the top of Wallace's are the same number, so that is the number.
#
# IT IS A SHARE OF THE ACCOUNT LOST IF THE STOP IS HIT. Not a price move and
# not a share of the margin. The quality dial scales it UP from here on the
# setups that carry his confluence, exactly as step472 measured.
RISK_PCT = 0.03


# ============================== THE WEEKLY CLOSE — WALLACE'S RULING, 2026-07-27
#
# HIS WORD, IN FULL: "alex: on".
#
# THE CONFLICT THIS SETTLES. Alex's June-2026 "spine" is a deliberate
# back-to-basics restatement — "one pair, one time frame, one session, and one
# entry signal" — and under newest-governs it overruled the higher-timeframe
# rules in every older video, including his weekly-close direction rule from
# 2026-05-25: "those candlesticks opening and closing dictate the direction of
# the following week." step472 shipped it OFF for that reason and measured it
# on, and it was flagged to Wallace as a decision that was his and not ours.
#
# HE MADE IT. The June simplification is what Alex tells a BEGINNER to do; the
# weekly rule is what he does. On the deep window the difference is the single
# largest number step472 produced:
#
#   five years, the four-instrument book, costs already inside every figure
#     spine alone, weekly OFF      -$85,748
#     with his weekly-close rule  +$116,028
#     mean R  +0.17  against its own fade at  -0.26
#
# That last line is the one that makes it evidence rather than a good year:
# the same entries with the direction REVERSED lose, so the rule's direction
# call is real and not an artefact of a rising tape.
#
# IT IS A FILTER AND NOTHING ELSE. It cannot create a trade, it can only
# refuse one whose direction disagrees with the last closed weekly candle.
# Every entry, stop and target below it is untouched.
WEEKLY_CLOSE = True

BOOK = {"risk_pct_per_trade": RISK_PCT, "weekly_bias": WEEKLY_CLOSE}


# ================== THE MONEY-GAME LADDER ON GOLD — WALLACE'S RULING, 2026-07-27
#
# HIS WORD, IN FULL: "ladder on gold too".
#
# WHOSE IDEA THE LADDER IS: ALEX GONZALEZ'S, which is why this book is where
# it always belonged. "when you have anything over ... $25,000 is where you
# should focus on the percentage game ... Anything below $25,000, it's all the
# money game", and the base is set so "you have at least four or five trades
# in you before you would obviously lose the account"
# (ag_transcripts/LwMsai2ppKc_growsmall_clean.txt, 2026-02-22). Wallace on the
# stake: "This is why I even have it set at 2178 ... its how much I would be
# willing to lose to even start."
#
# THE CURVE IS NOT REWRITTEN HERE. `craig_live.money_game_share` is imported
# and called. It is the same function the Craig crypto book sizes on, it is
# already tested against both of Alex's anchors, and a second implementation
# of one curve is a second thing to keep in step. That the function lives in a
# file named after Craig is an accident of which book needed it first — the
# rule inside it is Alex's, and this is it going home.
#
# WHAT A SHARED STAKE MEANS, because this is the part that has to be right.
# The Craig crypto book and this gold book are ONE BloFin account and ONE
# $2,178 stake. Both read the venue's LIVE equity at the moment they size, so:
#
#   * a drawdown in either book shrinks the NEXT bet in both. That is the
#     intended behaviour and it is what makes one ladder on a shared stake
#     coherent rather than two books each betting the whole of it;
#   * a WIN in either book grows both, and the ladder steps the share down as
#     it does, exactly as he asks: "as you start creating a bigger account,
#     you LOWER that risk";
#   * they still contend for MARGIN, and nothing here mediates that — the
#     exchange does. See `gold_leverage` and the report.
#
# THE PERCENTAGE GAME IS WHERE FOREX ALREADY IS. The OANDA account holds
# $100,000, which is four times his own $25,000 threshold, so forex is on the
# flat 3% and the ladder never touches it. That is his rule, not a choice.
GOLD_BOOK = {"money_game_ladder": True, "money_game_stake": 2178.0}

# the two keys above are not fields of `alex_engine.DumbConfig` and must never
# become ones: the ladder is a SIZE and the engine's config is the METHOD.
LADDER_KEYS = ("money_game_ladder", "money_game_stake")


def money_game_share(equity: float, stake: float) -> float:
    """Alex's ladder, through the one implementation of it in this project."""
    import craig_live
    return craig_live.money_game_share(equity, stake)


def live_config(instrument: str, **over) -> ae.DumbConfig:
    """The config a live Alex trade is DECIDED on: step472's shipping
    defaults, plus Wallace's weekly-close ruling, plus the one risk number.

    The ladder is deliberately not in here. It is a SIZE, it changes no entry,
    no stop, no target and no decision about which setups are taken, and every
    replay and every agreement run is measured on this config alone —
    `test_the_ladder_moves_only_the_size` runs the year both ways and fails on
    the first trade where anything but the ounces differs.
    """
    over = {k: v for k, v in over.items() if k not in LADDER_KEYS}
    return ae.dumb_config_for(instrument, **{**BOOK, **over})


def book_config(instrument: str, **over) -> dict:
    """What the GOLD book is actually traded on: `live_config` plus the
    money-game ladder. Returned as the override dict `Engine` takes, because
    the ladder is not a field of the engine's config and must not become one.
    """
    return {**BOOK, **GOLD_BOOK, **over}


def bar_width(cfg: ae.DumbConfig) -> pd.Timedelta:
    """How long one candle of the working chart lasts. A bar is stamped with
    the minute it STARTED, so its close — the only moment its decision is
    knowable — is this much later."""
    return pd.Timedelta(minutes=ae._TF_MINUTES[cfg.tf])


# ===================================================== HOW STALE IS TOO OLD
#
# OURS, AND IT IS A LIVE RULE ONLY — the engine models a setup whether or not
# the desk was awake for it, and the replay never sees this at all.
#
# His entry is a MARKET order at the close of the confirming candle. A 4-hour
# candle that closed three hours ago is a price that no longer exists, and
# sending a market order into it is not his trade at a worse price, it is a
# different trade. So after a restart, or a gap in the feed, a candle older
# than this is ADOPTED AS HISTORY: its setups are recorded, marked seen, and
# never entered.
ENTRY_FRESHNESS = pd.Timedelta(minutes=30)


# ================================================== ALEX'S OWN STOP FLOORS
#
# HIS RULE'S ONE INPUT, MEASURED FROM HIS OWN SETUPS AND NOBODY ELSE'S.
#
# `tjr_desk.tightest_stop_pct` reads floors measured from the TJR method's
# 5-minute setups and `craig_live` reads floors measured from Craig's 1-hour
# setups. Alex is a third method on a third chart and may borrow neither:
# "sizing off another market's number is exactly what his rule forbids", and
# another METHOD's number is further away still.
#
# WHAT IT IS ACTUALLY USED FOR, stated plainly: this engine spends the
# allowance exactly off today's stop (`hold_size_still=False`), so this number
# changes no unit count at all — `test_the_stop_floor_moves_no_size` proves
# it. It exists because `tjr_alerts.position_size` REFUSES to state a size for
# an instrument whose tightest stop has never been measured, and the honest
# answer to that refusal is to measure it, not to switch it off.
STOP_FLOOR_PATH = f"{REPO}/step473_alex_stop_floors.json"
STOP_FLOOR_PERCENTILE = 10

_FLOORS: dict = {}


def stop_floors() -> dict:
    global _FLOORS
    if not _FLOORS:
        try:
            with open(STOP_FLOOR_PATH) as fh:
                _FLOORS = json.load(fh)
        except (FileNotFoundError, OSError, ValueError):
            _FLOORS = {}
    return _FLOORS


def tightest_stop_pct(symbol: str) -> float:
    """Keyed by the DESK's spelling ("EUR/USD"), because that is what the
    signal carries and what `tjr_desk` looks up."""
    return float((stop_floors().get(symbol) or {}).get("tightest_stop_pct") or 0.0)


def derive_stop_floors(start=None, end=None, verbose: bool = True) -> dict:
    """Measure the tightest stop each instrument's Alex setups normally give,
    on the shipping chart. Reads cached parquet, writes one JSON file, touches
    no venue and places nothing.

    THE TENTH PERCENTILE, NOT THE SMALLEST, for the reason `tjr_desk` gives:
    "what's USUALLY the lowest your stop loss will be", not the lowest it has
    ever been. One freak candle is not a rule.
    """
    end = pd.Timestamp(end or "2026-07-26")
    start = pd.Timestamp(start or (end - pd.Timedelta(days=364 * 5)))
    out = dict(stop_floors())
    for symbol, inst in SYMBOLS.items():
        cfg = live_config(inst)
        r = ae.run_instrument(inst, start, end, cfg=cfg, mode="dumb")
        pct = [abs(t.entry - t.stop) / t.entry for t in r["trades"] if t.entry]
        if not pct:
            continue
        out[symbol] = {
            "tightest_stop_pct": float(np.percentile(pct, STOP_FLOOR_PERCENTILE)),
            "median_stop_pct": float(np.median(pct)),
            "widest_stop_pct": float(np.max(pct)),
            "setups_measured": len(pct),
            "chart": cfg.tf, "engine": "alex", "instrument": inst,
        }
        if verbose:
            v = out[symbol]
            print(f"  {symbol:9s} tightest {100*v['tightest_stop_pct']:.3f}% of "
                  f"price   typical {100*v['median_stop_pct']:.3f}%   widest "
                  f"{100*v['widest_stop_pct']:.3f}%   "
                  f"(from {v['setups_measured']} trades on the "
                  f"{v['chart']} chart)")
    with open(STOP_FLOOR_PATH, "w") as fh:
        json.dump(out, fh, indent=2)
    global _FLOORS
    _FLOORS = out
    return out


# ============================================================== THE STATE
@dataclass
class Live:
    """One open Alex trade, as the engine models it.

    The SETUP and the EQUITY AT ENTRY are frozen the moment the trade opens;
    everything else about the trade is re-derived from them on every poll by
    `alex_engine.manage`, which is the replay's own function. That is what
    makes a live trade and a replayed one the same object rather than two
    implementations of one idea.
    """
    instrument: str
    setup: ae.Setup
    equity_at_entry: float
    usd_per_quote: float
    trade: ae.Trade
    # THE CONFIG THIS TRADE WAS SIZED ON, frozen with the rest of it. Under
    # the ladder the risk share is a function of the equity at the moment of
    # entry, so a later poll that re-derived it from a changed balance would
    # quietly re-size a position that is already open.
    cfg: ae.DumbConfig | None = None
    sent: bool = False              # did an order actually reach a venue
    order: dict = field(default_factory=dict)


# ============================================================= THE ENGINE
class Engine:
    """Alex's method as a state machine over closed 4-hour candles.

    ONE CALL PER INSTRUMENT PER POLL. `step` manages what is open on every
    call — a stop, a target or his Friday exit can land on any 15-minute bar —
    and looks for a NEW setup only when a 4-hour candle has actually closed.
    That is what lets the desk keep polling once a minute without the engine
    acting twice on the same candle or acting on half of one.

    It returns ACTIONS. It sends nothing and knows nothing about a venue.
    """

    def __init__(self, cfg_over: dict | None = None):
        over = dict(cfg_over or {})
        # THE LADDER IS SPLIT OFF FROM THE METHOD'S CONFIG HERE, and that is
        # the whole of how it reaches an order. It sets the DOLLARS one trade
        # may cost and nothing else; everything below this line is identical
        # with it on and with it off.
        self.ladder = bool(over.pop("money_game_ladder", False))
        self.stake = float(over.pop("money_game_stake", 0.0) or 0.0)
        self._over = over
        self._cfg: dict = {}
        self.live: dict = {}           # instrument -> Live
        self.closed: dict = {}         # instrument -> [Trade]
        self.seen: set = set()         # setups already decided about
        self.last_bar: dict = {}       # instrument -> last 4h bar acted on
        self.busy_until: dict = {}     # instrument -> no new entry before this
        self.adopted: dict = {}        # instrument -> setups skipped as stale
        self._struct: dict = {}        # instrument -> the 4h structure state
        # ENTRIES ONLY INSIDE THIS WINDOW, when one is set. The live desk never
        # sets it; the agreement harness does, because
        # `alex_engine.run_instrument` bounds which candles may produce a
        # setup and the two must be bounded the same way or they are not being
        # asked the same question.
        self.window: tuple | None = None

    # ------------------------------------------------------------ config
    def cfg(self, instrument: str) -> ae.DumbConfig:
        if instrument not in self._cfg:
            self._cfg[instrument] = live_config(instrument, **self._over)
        return self._cfg[instrument]

    def risk_share_for(self, instrument: str, equity: float) -> float:
        """The share of the account ONE TRADE may cost, before his quality
        dial scales it. The ladder's when this book is on it, and the flat
        dial otherwise. ONE function, so the engine, the desk and the message
        cannot drift apart about it."""
        if not self.ladder:
            return float(self.cfg(instrument).risk_pct_per_trade)
        return money_game_share(float(equity), self.stake)

    def cfg_at(self, instrument: str, equity: float) -> ae.DumbConfig:
        """The method's config with the ladder's answer written into the one
        field the size comes out of.

        A COPY, NEVER A MUTATION. The shared config object is the METHOD and
        it is the same object for every trade on this instrument; the risk
        share under a ladder belongs to ONE trade, at ONE balance.
        """
        cfg = self.cfg(instrument)
        if not self.ladder:
            return cfg
        return replace(cfg, risk_pct_per_trade=self.risk_share_for(
            instrument, equity))

    # ------------------------------------------------------------ driving
    def step(self, instrument: str, frames: dict, equity,
             usd_per_quote: float = 1.0, now=None) -> list:
        """One poll for one instrument.

        `frames` needs three keys — "4h", "15m" and "1w" — and every one of
        them must hold CLOSED bars only. A half-built candle is not a candle:
        every rule in this method is read off a close, so acting on a bar
        still forming is acting on a number that is about to change. The
        weekly is there because Wallace's ruling put it there; with
        `weekly_bias` off it is never read.

        `equity` is a number or a callable. The desk passes the venue's own
        equity; the agreement harness passes a callable that reproduces
        `alex_engine.run_instrument`'s basis to the cent.

        TWO THINGS IT DELIBERATELY DOES NOT DO, and both are about starting up.

        IT DOES NOT REPLAY HISTORY. The desk hands it years of candles because
        that is what the tape holds, and on the first call of a process's life
        there is no record of what has already been acted on. Walking all of
        it would send market orders for setups that formed in April.

        IT DOES NOT CHASE A PRICE THAT IS GONE. His entry is a market order at
        the close of the confirming candle, so a candle older than
        ENTRY_FRESHNESS is adopted as history rather than traded late.
        """
        cfg = self.cfg(instrument)
        d4 = frames.get(cfg.tf)
        m15 = frames.get("15m")
        if d4 is None or not len(d4) or m15 is None or not len(m15):
            return []
        acts: list = []

        # THE 4-HOUR STRUCTURE STATE, snapshotted at each 4-hour close, which
        # is the same object `alex_engine.run_instrument` hands to `manage`.
        # Rebuilt on every poll because the frame grows; causal, so a state
        # already stamped never moves.
        #
        # BUILT ONLY WHEN SOMETHING READS IT. `manage` consults it through
        # `_flipped`, which is reached only by the structure-shift exit and
        # by the runner — both of which ship OFF. With both off the argument
        # is never looked at, and walking eleven thousand bars once a minute
        # to build something nothing reads is the single most expensive thing
        # this engine could do.
        # `test_the_structure_state_is_built_when_and_only_when_it_is_read`
        # holds both halves of that.
        if getattr(cfg, "exit_on_structure_flip", False) or \
                getattr(cfg, "runner", False):
            self._struct[instrument] = (ae.trend_series(d4),
                                        ae.closes_at(d4, cfg.tf))

        # ------------------------------------------- 1. what is already on
        acts += self._manage(instrument, m15, cfg)

        # -------------------------------------------- 2. the closed candles
        t = d4["t"].to_numpy()
        last = self.last_bar.get(instrument)
        if last is None:
            start = len(d4) - 1              # the newest closed candle only
        else:
            start = int(np.searchsorted(
                t, np.datetime64(pd.Timestamp(last)), "right"))
        step_w = bar_width(cfg)
        for i in range(max(0, start), len(d4)):
            decided = pd.Timestamp(t[i]) + step_w
            if not self._could_fire(decided, cfg):
                continue
            fresh = now is None or (
                pd.Timestamp(now) - decided) <= ENTRY_FRESHNESS
            acts += self._on_bar(instrument, frames, d4, i, decided, cfg,
                                 equity, usd_per_quote, fresh)
        self.last_bar[instrument] = pd.Timestamp(t[-1])
        return acts

    # --------------------------------------------------------- one candle
    def _on_bar(self, instrument, frames, d4, i, decided, cfg, equity,
                usd_per_quote, fresh: bool) -> list:
        acts = []
        for s in self._setups_on(instrument, frames, d4, i, cfg):
            if not self._in_window(s):
                # OUTSIDE THE HARNESS'S WINDOW, so `run_instrument` never saw
                # this setup at all. NOT marked seen, because it never
                # happened as far as this engine is concerned — and for a head
                # and shoulders that matters: the replay goes on looking for a
                # later confirming candle on the same pattern, and so must we.
                continue
            key = self._key(instrument, s)
            if key in self.seen:
                continue
            self.seen.add(key)
            if not fresh:
                # ADOPTED, NOT TAKEN. Recorded so a restart can say what it
                # walked past rather than pretending the candles never existed.
                self.adopted.setdefault(instrument, []).append(s)
                continue
            if instrument in self.live:
                continue                     # one position at a time — HIS
            hold = self.busy_until.get(instrument)
            if hold is not None and s.decided_t < hold:
                continue                     # the cooldown after an exit
            eq = float(equity() if callable(equity) else equity)
            # THE LADDER'S ONE TOUCH POINT. `cfg_at` is the method's config
            # with the risk share the ladder asks for at THIS balance written
            # into it; with the ladder off it is the very same object.
            cfg_t = self.cfg_at(instrument, eq)
            tr = ae.manage(s, frames["15m"], cfg_t, eq, usd_per_quote,
                           structure=self._struct.get(instrument))
            if tr is None:
                continue                     # the size could not be worked out
            self.live[instrument] = Live(
                instrument=instrument, setup=s, equity_at_entry=eq,
                usd_per_quote=usd_per_quote, trade=tr, cfg=cfg_t)
            acts.append({"kind": "enter", "instrument": instrument,
                         "symbol": symbol_for(instrument), "at": decided,
                         "setup": s, "trade": tr,
                         "signal": self.signal(s, tr, eq, usd_per_quote,
                                               cfg=cfg_t)})
            # a trade can open and resolve inside the same poll when the tape
            # has run on — a restart, or the agreement harness stepping a
            # closed candle at a time. Report both, in order.
            acts += self._settle(instrument, cfg)
        return acts

    def _setups_on(self, instrument, frames, d4, i, cfg) -> list:
        """Every setup THIS candle stamps, through the replay's own two
        finders with the window narrowed to this one bar.

        THE FRAME IS NOT SLICED. Both finders read only bars at or before the
        index they are stamping, and the window arguments are what bound them
        — so passing the full frame is causal and passing a shortened one
        would not be: his 50 EMA is a running average whose value depends on
        where the series began.
        """
        t0 = pd.Timestamp(d4["t"].iloc[i])
        t1 = t0 + bar_width(cfg)
        pat = getattr(cfg, "pattern", "engulf")
        out = []
        if pat in ("engulf", "both"):
            out += ae.find_setups_dumb(instrument, frames, cfg, t0, t1)
        if pat in ("hs", "both"):
            out += ae.find_setups_hs(instrument, frames, cfg, t0, t1)
        out = [s for s in out if pd.Timestamp(s.decided_t) == t1]
        out.sort(key=lambda s: (s.decided_t, s.pattern))
        return out

    @staticmethod
    def _key(instrument, s: ae.Setup) -> tuple:
        """One setup's identity.

        An engulfing candle is its own bar, so the bar identifies it. A head
        and shoulders is identified by the NECKLINE BREAK behind it, not by
        the candle that confirmed the retest: the same pattern can offer a
        second confirming candle a bar later, and taking both would be two
        orders on one idea. The replay takes the first and stops looking.
        """
        if s.pattern == "hs":
            return (instrument, "hs", pd.Timestamp(s.break_t))
        return (instrument, s.pattern, pd.Timestamp(s.signal_t))

    @staticmethod
    def _could_fire(decided, cfg) -> bool:
        """A SHORT CIRCUIT, NOT A RULE, and the difference matters.

        BOTH of `alex_engine`'s finders already refuse a setup whose candle
        closed outside his session — `dumb_in_window` is the first thing each
        of them checks. So a candle that fails it cannot produce a setup, and
        asking the finders is five hundredths of a second of work to be told
        so. On the 4-hour grid four of every six candles a day fail it, and
        so does every candle from Friday and the weekend.

        `test_the_session_short_circuit_refuses_nothing` runs a stretch with
        it and without it and fails if a single setup differs.
        """
        if not getattr(cfg, "session_gate", True):
            return True
        return ae.dumb_in_window(decided, cfg)

    def _in_window(self, s: ae.Setup) -> bool:
        """The harness's bound, mirroring `alex_engine`'s two finders exactly.

        They do not bound themselves the same way and that is not ours to
        change: the engulf finder bounds the SIGNAL CANDLE'S START and the
        head-and-shoulders finder bounds the moment the confirming candle
        CLOSED. Reproducing both is the difference between the two engines
        being asked the same question and nearly the same one.
        """
        if self.window is None:
            return True
        ref = pd.Timestamp(s.decided_t) if s.pattern == "hs" \
            else pd.Timestamp(s.signal_t)
        return self.window[0] <= ref <= self.window[1]

    # -------------------------------------------------- what is already on
    def _manage(self, instrument, m15, cfg) -> list:
        """RE-RUN THE REPLAY'S OWN `manage` FROM THE ENTRY, against the
        15-minute bars that have closed so far.

        This is the whole reason live and replay cannot drift on an exit.
        There is no second implementation of the stop, the target, his Friday
        rule or the 30-day cap — there is one function and it is called twice,
        once by the backtest with the finished tape and once by the desk with
        the tape as far as it goes. It scans forward and stops at the first
        thing that happens, so extending the tape can never change an answer
        it has already given.
        """
        pos = self.live.get(instrument)
        if pos is None:
            return []
        pos.trade = ae.manage(pos.setup, m15, pos.cfg or cfg,
                              pos.equity_at_entry, pos.usd_per_quote,
                              structure=self._struct.get(instrument))
        return self._settle(instrument, cfg)

    def _settle(self, instrument, cfg) -> list:
        pos = self.live.get(instrument)
        if pos is None or pos.trade is None or pos.trade.exit_t is None:
            return []
        tr = pos.trade
        self.live.pop(instrument, None)
        self.closed.setdefault(instrument, []).append(tr)
        cool = pd.Timedelta(minutes=cfg.reentry_cooldown_bars
                            * ae._TF_MINUTES[cfg.tf])
        self.busy_until[instrument] = pd.Timestamp(tr.exit_t) + cool
        return [{"kind": "exit", "instrument": instrument,
                 "symbol": symbol_for(instrument),
                 "at": pd.Timestamp(tr.exit_t), "price": tr.exit,
                 "outcome": tr.outcome, "setup": pos.setup, "trade": tr,
                 "why": exit_why(tr, cfg)}]

    # -------------------------------------------------------- the signal
    def signal(self, s: ae.Setup, tr: ae.Trade, equity: float,
               usd_per_quote: float = 1.0, cfg=None) -> dict:
        """The dict the desk already consumes, for one Alex entry.

        Same keys and the same meanings every other book uses. There is no
        `order_type` here and that is the difference from Craig at the venue:
        his trigger is a candle CLOSING and his entry is that close, taken at
        market, so a limit that never fills would be a signal missed.
        """
        cfg = cfg if cfg is not None else self.cfg_at(s.instrument, equity)
        symbol = symbol_for(s.instrument)
        market = "gold" if s.instrument == GOLD_INSTRUMENT else "forex"
        # THE DOLLARS THIS TRADE MAY COST, and the quality dial is already
        # inside them. `alex_engine.manage` works the size out from exactly
        # this number, so forwarding it is what makes the desk's own call and
        # the engine's land on the same units without the desk having to know
        # the dial exists — the same arrangement Craig's ladder uses.
        allow = cfg.risk_pct_per_trade * float(equity) * float(s.quality)
        return {
            "market": market,
            "symbol": symbol,
            "instrument": s.instrument,
            "direction": s.direction,
            "side": "buy" if s.direction > 0 else "sell",
            "reference_price": float(s.entry),
            "stop": float(s.stop),
            "targets": [float(s.target)],
            "target_sources": [target_source(cfg)],
            "target_fractions": [1.0],
            "runner_fraction": 0.0,
            "partial_fraction": 1.0,
            "single_exit": True,
            "budget_share": 1.0,
            "derisk": False,
            "entry_t": pd.Timestamp(s.decided_t),
            "session": s.session,
            "engine": "alex",
            "why_parts": why_parts(s),
            "why": why_line(why_parts(s)),
            "exit_note": EXIT_NOTE,
            # ------------------------------------------------------ sizing
            "risk_wanted": allow,
            "outer_allowance": allow,
            "buying_power_used": None,
            # HIS SIZE IS SPENT, NOT HELD STILL. The allowance is what this
            # trade costs when the stop is hit, full stop, and the size falls
            # out of TODAY'S stop. Every number step472 measured came out of
            # that rule.
            "hold_size_still": False,
            "tightest_stop_pct": tightest_stop_pct(symbol),
            "usd_per_quote": float(usd_per_quote),
            "units_wanted": float(tr.units),
            "risk_dollars": float(tr.risk_dollars),
            "sizing_account": float(equity),
            # THE QUALITY DIAL, SAID OUT LOUD ON EVERY SIGNAL. Nothing renders
            # these; the record and the console carry which confluences this
            # setup had and what share of a normal position they bought.
            "pattern": s.pattern,
            "signal_kind": s.signal_kind,
            "engulfed": int(s.engulfed),
            "dojis": int(s.dojis),
            "quality": float(s.quality),
            "quality_pts": int(s.quality_pts),
            "quality_avail": int(s.quality_avail),
            "risk_share_used": cfg.risk_pct_per_trade * float(s.quality),
            # THE LADDER, SAID OUT LOUD ON EVERY SIGNAL. Nothing renders these
            # — no message shape changed — but the record and the console both
            # carry which rule sized this trade.
            "money_game_ladder": bool(self.ladder),
            "money_game_stake": float(self.stake),
            "base_risk_share": float(cfg.risk_pct_per_trade),
            "weekly_close_rule": bool(getattr(cfg, "weekly_bias", False)),
            # what the message says the stop sits on, in his own words
            "level_tf": cfg.tf,
            "level_price": float(s.area_lo if s.direction > 0 else s.area_hi),
            "stop_anchor": "structure",
        }

    # ------------------------------------------------------ reading it back
    def frame(self) -> pd.DataFrame:
        """One row per closed trade, in the same words `alex_engine.frame`
        uses, so a live book and a replay book can be put side by side."""
        book = {inst: {"trades": trades}
                for inst, trades in self.closed.items()}
        return ae.frame(book)


# ============================================================== THE WORDS
def target_source(cfg) -> str:
    if getattr(cfg, "target_mode", "structure") == "structure":
        return "the next structure point to the left, his own take profit"
    return "1:2 of the risk this trade actually takes"


def why_parts(s: ae.Setup) -> dict:
    """The pieces `why_line` renders, WITH THE PRICES KEPT SEPARATE.

    They are separate because gold's prices cross venues. The sentence is
    written once and rendered twice — once on the chart's prices for a replay
    and once on the traded contract's for the message — and a number quoted in
    the sentence that disagrees with the number on the line above it is
    exactly the kind of thing that makes him stop trusting the messages.
    """
    return {"pattern": s.pattern, "direction": int(s.direction),
            "session": s.session, "engulfed": max(int(s.engulfed), 1),
            "entry": float(s.entry), "stop": float(s.stop),
            "target": float(s.target),
            "neckline": float(s.neckline) if s.neckline == s.neckline else None,
            "head": float(s.head) if s.head == s.head else None}


def why_line(parts) -> str:
    """WHY THIS TRADE EXISTS, in one sentence, with no term in it he would
    have to stop and translate.

    His vocabulary is "market structure", "areas of interest", "the engulfing
    candlestick", "the neckline". None of those four reaches the phone as it
    is written: market structure is which way the chart has been turning; an
    area of interest is a price the chart has turned at three times; an
    engulfing candle is one candle that swallows the ones before it; a
    neckline is the price whose break turned the chart the other way.
    """
    p = parts if isinstance(parts, dict) else why_parts(parts)
    up = p["direction"] > 0
    way = "up" if up else "down"
    other = "down" if up else "up"
    eaten = p["engulfed"]
    ate = ("one candle" if eaten == 1 else f"the last {eaten} candles")
    named = {"london": "London", "new_york": "New York"}.get(p["session"],
                                                             p["session"])
    side = "long" if up else "short"
    if p["pattern"] == "hs" and p.get("neckline") is not None:
        return (
            f"The 4-hour chart had been going {other} and then it turned: "
            f"price closed past {p['neckline']:,.6g}, the level the whole turn "
            f"was built on, and the furthest it reached before that was "
            f"{p['head']:,.6g}. Price has now come back to "
            f"{p['neckline']:,.6g} and a candle closed {way} on it, swallowing "
            f"{ate}, which is the retest he waits for rather than chasing the "
            f"break. So the trade goes {side} at {p['entry']:,.6g}, the stop "
            f"sits at {p['stop']:,.6g} beyond the furthest price reached since "
            f"the turn, and the target is {p['target']:,.6g}, the next place "
            f"the chart has already turned.")
    return (
        f"The 4-hour chart is going {way} — it keeps making "
        f"{'higher highs' if up else 'lower lows'} and it has not closed back "
        f"past the last {'low' if up else 'high'} it left behind. At the {named} "
        f"session one candle closed {way} and swallowed {ate} whole, which is "
        f"the one entry signal he says to use and nothing else. So the trade "
        f"goes {side} at {p['entry']:,.6g}, the stop sits "
        f"at {p['stop']:,.6g} just beyond the structure that candle came out "
        f"of, and the target is {p['target']:,.6g}, the next place the chart "
        f"has already turned — at least twice what the trade is risking, or "
        f"he does not take it at all.")


#: WHAT HAPPENS NEXT, and on this book the answer is nothing.
#:
#: "once you enter a trade you pretty much just have to set and forget ...
#:  You either let the trade hit your stop loss or let the trade hit your
#:  takeprofit" — grw58BIzotU.txt 02:47:06, 2025-09-28
#:  "I am not a break even trader."
#:
#: Both ends rest at the venue. There is no partial, no ladder, no runner and
#: NO BREAK EVEN — the stop does not move, ever, and telling him it will is
#: telling him about a book he is not running.
EXIT_NOTE = (
    "There is nothing to do at any point and nothing will move. The stop and "
    "the target are both already resting at the venue, so the trade is "
    "protected whether or not the bot is running. It comes off at one of the "
    "two and nowhere else — no half off, no runner, and the stop does not "
    "creep to your entry, because this method does not do that. The one "
    "exception is his own weekend rule: if it is Friday afternoon and the "
    "trade is more than halfway to its stop, the bot closes it rather than "
    "carry it through Sunday's opening spread.")


def exit_why(tr: ae.Trade, cfg) -> str:
    """What ended the trade, in words, for the message the desk sends."""
    if tr.outcome == "target":
        return ("The target is reached. That was the next place the chart had "
                "already turned, and it paid at least twice what the trade "
                "was risking. That is the whole position off. That is the "
                "trade.")
    if tr.outcome == "stop":
        return ("The stop was hit. This one was wrong and it cost exactly "
                "what it was set up to cost, not a cent more.")
    if tr.outcome in ("friday", "runner_friday"):
        return ("The currency week closes in fifteen minutes and this trade "
                "is more than halfway to its stop. He closes those before the "
                "weekend rather than carrying them through Sunday's opening "
                "spread, which can take a trade out at a loss on nothing but "
                "the gap. So it is closed here.")
    if tr.outcome in ("flip", "runner_flip"):
        return ("The 4-hour chart has turned the other way. The reason for "
                "this trade was the direction it was going, and that reason "
                "is gone, so it is closed.")
    if tr.outcome == "held_out":
        return (f"Neither the stop nor the target was reached and this one "
                f"has been open {cfg.max_hold_days:.0f} days, which is as "
                f"long as the bot holds an Alex trade. It took whatever was "
                f"there. That cap is OURS — he states none.")
    return f"The trade is closed: {tr.outcome}."


# ================================================= THE GOLD BASIS, EXPLICIT
#
# See the module docstring. One ratio, measured in one second, applied to
# every price that crosses from the chart to the order.

MAX_BASIS_DRIFT = 0.05      # 5% between spot gold and Tether Gold is not the
#                             basis, it is a broken feed. Refuse, never guess.


class BasisUnreadable(RuntimeError):
    """Raised rather than returning 1.0. Falling back to parity would place a
    stop at the wrong price on every gold trade, quietly."""


def gold_basis(oanda_mid: float | None, blofin_mark: float | None) -> float:
    """XAUT-USDT divided by XAU/USD, both read in the same second.

    REFUSES rather than guessing. There is no default here and there must
    never be one: a basis of 1.0 assumed on a day when Tether Gold is trading
    a third of a percent under spot puts every stop and every target on this
    book about a fifth of a stop width out of place, and nothing would ever
    report it.
    """
    a = float(oanda_mid or 0.0)
    b = float(blofin_mark or 0.0)
    if a <= 0 or b <= 0:
        raise BasisUnreadable(
            f"the gold basis could not be measured: OANDA XAU/USD read as "
            f"{oanda_mid!r} and BloFin {GOLD_VENUE_SYMBOL} as {blofin_mark!r}. "
            f"The chart and the traded contract are two different prices for "
            f"the same metal, so nothing can cross between them without it. "
            f"Nothing was sent.")
    r = b / a
    if abs(r - 1.0) > MAX_BASIS_DRIFT:
        raise BasisUnreadable(
            f"{GOLD_VENUE_SYMBOL} marked at {b:,.2f} against XAU/USD at "
            f"{a:,.2f}, which is {100*(r-1):+.2f}% apart. Tether Gold does not "
            f"drift that far from spot, so one of the two feeds is wrong and "
            f"this is not a basis. Nothing was sent.")
    return r


def convert(price: float, basis: float) -> float:
    """One price, out of the chart's space and into the traded contract's.

    MULTIPLIED, NEVER SHIFTED. The stop's distance as a SHARE OF THE PRICE is
    what sets the leverage, the margin and how far the exchange's liquidation
    sits, and multiplying is what leaves that share alone.
    """
    return float(price) * float(basis)


def convert_signal(sig: dict, basis: float) -> dict:
    """Every price on one gold signal, crossed at once.

    THIS IS THE ONLY PLACE A GOLD PRICE CROSSES. Doing it here, on the way
    out of the engine, means the size, the message and the order all speak the
    traded contract's own prices and nothing downstream has to remember that
    gold has two of them.
    """
    out = dict(sig)
    for k in ("reference_price", "stop", "level_price"):
        if out.get(k) is not None:
            out[k] = convert(float(out[k]), basis)
    out["targets"] = [convert(float(t), basis) for t in (sig.get("targets") or [])]
    # AND THE SENTENCE, NOT ONLY THE NUMBERS. The "why" quotes the entry, the
    # stop, the target and the level the turn was built on. Left uncrossed it
    # would state the chart's prices two lines under the contract's, and he
    # would reconcile his BloFin screen against numbers nothing ever sent.
    parts = dict(sig.get("why_parts") or {})
    if parts:
        for k in ("entry", "stop", "target", "neckline", "head"):
            if parts.get(k) is not None:
                parts[k] = convert(float(parts[k]), basis)
        out["why_parts"] = parts
        out["why"] = why_line(parts)
    out["gold_basis"] = float(basis)
    out["chart_symbol"] = GOLD_SYMBOL
    out["venue_symbol"] = GOLD_VENUE_SYMBOL
    out["basis_note"] = (
        f"the levels are read on OANDA XAU/USD and the order goes to BloFin "
        f"{GOLD_VENUE_SYMBOL}, which was marking {100*(basis-1):+.3f}% away "
        f"from spot when this was sized. Every price above is the traded "
        f"contract's own, converted at that ratio, never copied across.")
    # the units the engine modelled are in the CHART's price space; the desk
    # re-sizes off the converted stop, which is the one that will be sent.
    if out.get("units_wanted"):
        out["units_wanted"] = float(out["units_wanted"]) / float(basis)
    return out


# ================================== WHAT EACH VENUE WILL ACTUALLY CARRY
#
# Two venue facts, each in ONE function, so the number the order carries, the
# number the message states and the number a test asserts are the same number.
# Neither of them is a dial: both can only ever make a position smaller or
# make the margin behind it larger.

def gold_leverage(equity: float, notional: float, stop_move: float,
                  max_leverage: float, margin_share: float,
                  safety: float) -> int | None:
    """The leverage the BloFin gold order will carry, or None if it cannot be
    carried at all.

    THE SMALLER OF TWO NUMBERS, and both of them are the exchange's:

      1. the smallest leverage that fits one trade's margin into
         `margin_share` of the account — `venue.BlofinVenue`'s own budget;
      2. the largest leverage that still leaves the exchange's liquidation
         `safety` times further away than the stop — `venue.BlofinVenue`'s own
         refusal condition, turned into a choice.

    Taking the smaller means the margin posted is at or above the budget,
    never below it, and the liquidation is always beyond the stop with the
    room this project already insists on. `max_leverage` is the exchange's
    own ceiling for the contract and it cannot be exceeded either.
    """
    equity, notional = float(equity), float(notional)
    stop_move, max_leverage = float(stop_move), float(max_leverage)
    if equity <= 0 or notional <= 0 or stop_move <= 0 or max_leverage <= 0:
        return None
    budget = equity * float(margin_share)
    if budget <= 0:
        return None
    fits_budget = min(max(1, int(max(1.0, notional / budget) + 0.999)),
                      int(max_leverage))
    liquidation_safe = int(math.floor(1.0 / (stop_move * float(safety))))
    lev = min(fits_budget, liquidation_safe)
    if lev < 1 or notional / lev > equity:
        return None
    return int(lev)


def forex_allowance_cap(allowance: float, units_wanted: float, entry: float,
                        usd_per_quote: float, margin_rate: float,
                        margin_available: float) -> tuple:
    """The broker's own margin ceiling, applied to the DOLLARS the trade may
    cost rather than to the units afterwards.

    WHY THE ALLOWANCE AND NOT THE UNITS. Three separate places work the size
    out from the allowance — the engine, `tjr_desk._size_for` and the message
    in `tjr_alerts.trade_block` — and they agree because they are given the
    same number. Cutting the UNITS at the end would leave the message stating
    a size the order does not carry, which is worse than no message.

    OANDA holds a fixed share of a position as margin: 2% on EUR/USD (fifty
    to one) and 5% on both pounds pairs (twenty to one) on this account,
    measured 2026-07-27. This method's leverage is an OUTPUT of the stop, and
    on a tight 4-hour stop it can ask for more than twenty times the account.
    When it does, the size comes down to what the broker will hold.

    Returns (allowance, note). The note is empty when nothing was cut.
    """
    allowance = float(allowance)
    need = abs(float(units_wanted)) * float(entry) * float(usd_per_quote) \
        * float(margin_rate)
    have = float(margin_available)
    if need <= 0 or have <= 0 or need <= have:
        return allowance, ""
    scale = have / need
    return allowance * scale, (
        f"CUT BY THE BROKER'S MARGIN — the stop asked for a position needing "
        f"${need:,.0f} of margin and OANDA has ${have:,.0f} free on this "
        f"account. It was cut to {100*scale:.0f}% of the size the stop asked "
        f"for. The stop and the target are unchanged.")


# ============================================= THE VENUE'S OWN LEVERAGE
def _alex_gold_factory(**kw):
    return AlexGoldVenue(**kw)


class AlexGoldVenue:
    """A placeholder, replaced by the real class below the moment venue.py
    imports. It is left NOT WORKING rather than silently harmless, because a
    venue object that does nothing would look like a venue that placed the
    order."""

    def __init__(self, *a, **kw):
        raise RuntimeError(
            "venue.py could not be imported, so there is no exchange to "
            "reach. Nothing was placed.")


def _install_venue():
    """Built at import time, but only if venue.py is importable — so this
    module can be read, tested and replayed on a machine with no exchange
    credentials at all.

    WHY A SUBCLASS AND NOT AN EDIT TO venue.py — the same reason
    `craig_live.CraigBlofinVenue` is one. Two things about gold are facts
    about THIS BOOK and not about the exchange adapter:

      1. the symbol. "XAU/USD" is the chart; the contract is XAUT-USDT, and
         no other book on this desk trades it.
      2. the leverage. See `_leverage_for` below.

    Everything else is inherited unchanged and deliberately so — the
    attribution gate, the sealed client, the coins-to-contracts conversion
    read live from the exchange, the refusal to open without a stop, the
    refusal to open on a symbol carrying a position the bot cannot prove is
    its own. None of it is re-implemented here, which is the only way to be
    sure none of it was weakened.
    """
    global AlexGoldVenue
    try:
        import venue as venue_mod
    except Exception:                                        # noqa: BLE001
        return None

    class _AlexGoldVenue(venue_mod.BlofinVenue):
        """BloFin's DEMO futures host, carrying Tether Gold."""

        name = "blofin-demo-alex-gold"
        is_real_money = False

        PAIRS = dict(venue_mod.BlofinVenue.PAIRS)
        PAIRS[GOLD_SYMBOL] = GOLD_VENUE_SYMBOL

        def mark_price(self, symbol: str = GOLD_SYMBOL) -> float | None:
            """What the exchange says this contract is worth right now.

            READ ONLY, and it is the BloFin half of the gold basis. It goes
            through the same authenticated client every other read here uses
            because BloFin's unauthenticated market endpoints answer a
            "restricted region" page from this address.
            """
            inst = self.venue_symbol(symbol)
            for path, key in (("/api/v1/market/mark-price", "markPrice"),
                              ("/api/v1/market/tickers", "last")):
                try:
                    rows = self._raw._call("GET", path, params={"instId": inst})
                except Exception:                            # noqa: BLE001
                    continue
                for row in (rows or []):
                    try:
                        px = float(row.get(key))
                    except (TypeError, ValueError):
                        continue
                    if px > 0:
                        return px
            return None

        def _leverage_for(self, symbol: str, qty: float, stop, entry):
            """LEVERAGE IS AN OUTPUT OF THE STOP, AND HERE IT IS THE
            LIQUIDATION THAT SETS IT RATHER THAN A MARGIN BUDGET.

            The parent picks the SMALLEST leverage that fits one trade's
            margin into `PER_TRADE_MARGIN_SHARE` of the account, and then
            REFUSES the trade outright if that leverage would put the
            exchange's liquidation price nearer than the stop. Its own check
            reduces to one sentence: MARGIN POSTED MUST BE AT LEAST
            `LIQUIDATION_SAFETY` TIMES THE DOLLARS AT RISK, whatever the
            stop's width. So whether a trade is refused depends on the ratio
            of the margin budget to the risk share and not on the market at
            all — and this book's risk share is not a constant, because the
            money-game ladder moves it with the balance and his quality dial
            moves it again per setup.

            So this book does not ask for a budget and then get refused when
            the arithmetic happens not to work out. It POSTS MORE MARGIN: the
            leverage is the largest that still leaves the exchange's
            liquidation `LIQUIDATION_SAFETY` times further away than the stop,
            and never more than the parent would have chosen anyway.

            IT STILL REFUSES, and the refusal is the honest one. When even the
            whole account is not enough margin to hold the position that far
            from liquidation, the answer is NO TRADE — not a quietly smaller
            position risking something nobody chose.

            THAT IS STRICTLY SAFER, IN BOTH DIRECTIONS, AND A TEST HOLDS IT:

              - it can only ever return a leverage AT OR BELOW the parent's,
                so the margin behind a position is never smaller than the
                parent's tenth of the account, only larger;
              - every leverage it returns satisfies the parent's own
                inequality, with the parent's own constant, by construction
                rather than by being checked afterwards.

            Nothing about the size, the stop, the target or which setups are
            taken changes here. This sets the margin the exchange holds, and
            that is all it sets.
            """
            spec = self.spec(symbol)
            max_lev = spec.get("max_leverage") or 0.0
            if max_lev <= 0:
                return {"status": "rejected",
                        "reason": "the exchange's instrument spec could not "
                                  "be read, so the most leverage this "
                                  "contract allows is unknown. Not trading "
                                  "on a guess."}
            try:
                equity = float((self._raw.account_balance() or {})
                               .get("totalEquity") or 0.0)
                price = float(entry or 0.0)
            except Exception:                                # noqa: BLE001
                return {"status": "rejected",
                        "reason": "the account equity could not be read"}
            if equity <= 0 or price <= 0 or not stop:
                return {"status": "rejected",
                        "reason": "the account equity, the entry price or the "
                                  "stop is missing, so leverage cannot be "
                                  "worked out"}
            stop_move = abs(price - float(stop)) / price
            if stop_move <= 0:
                return {"status": "rejected",
                        "reason": "the stop sits on the entry price, so there "
                                  "is no distance to size against"}

            notional = abs(float(qty)) * price
            lev = gold_leverage(equity, notional, stop_move, max_lev,
                                self.PER_TRADE_MARGIN_SHARE,
                                self.LIQUIDATION_SAFETY)
            if lev is None:
                return {"status": "rejected",
                        "reason": (
                            f"this position cannot be held on this exchange "
                            f"with the stop where it is. The stop sits "
                            f"{100*stop_move:.2f}% away as a MOVE IN THE "
                            f"PRICE, and holding ${notional:,.0f} of "
                            f"{self.venue_symbol(symbol)} far enough from "
                            f"liquidation for that stop to be reached first "
                            f"would need more margin than the ${equity:,.2f} "
                            f"in the account. Nothing was sent.")}
            return lev

    AlexGoldVenue = _AlexGoldVenue
    try:
        venue_mod.register(
            "blofin-demo-alex-gold", _alex_gold_factory, real_money=False,
            note="BloFin's DEMO futures host carrying TETHER GOLD "
                 "(XAUT-USDT), driven by ALEX GONZALEZ's method. Same "
                 "attribution gate, sealed client, isolated margin and "
                 "stop-attached-to-the-entry as blofin-demo. The two "
                 "differences are the symbol, which no other book here "
                 "trades, and that the leverage is set by how far the "
                 "exchange's liquidation must sit beyond the stop rather "
                 "than by a flat margin budget — which can only ever post "
                 "MORE margin than blofin-demo would")
    except Exception:                                        # noqa: BLE001
        pass
    return AlexGoldVenue


_install_venue()


# ================================== THE REPLAY-LIVE AGREEMENT HARNESS
def replay_through_live(instrument: str, start, end,
                        cfg: ae.DumbConfig | None = None,
                        frames: dict | None = None) -> dict:
    """The same candles the replay reads, fed to the LIVE engine one closed
    4-hour candle at a time.

    THIS IS THE TEST THAT CATCHES DRIFT, and it is here rather than in the
    test file so it can also be run by hand from `step473_alex_live.py`. The
    36x sizing bug happened because a replay and a live runner had separate
    paths and nothing ever put their answers next to each other.

    Every input is bent to match `alex_engine.run_instrument` exactly:

      * the 15-minute frame handed to the engine at each step holds only bars
        that had CLOSED by that 4-hour candle's close, which is all a live
        desk could ever have seen;
      * the equity is this instrument's own $100,000 plus the profit of every
        trade that had already closed at that moment — `run_instrument`'s
        basis, to the cent;
      * the dollars-per-quote is the same daily series the replay reads, so
        the yen pair is not being asked two different questions;
      * nothing is stale, because `now` is each candle's own close.
    """
    cfg = cfg or live_config(instrument)
    frames = frames or ae.load(instrument)
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    d4 = frames[cfg.tf]
    m15 = frames["15m"]
    upq_series = ae.usd_per_quote_series(instrument, frames, {})
    width = bar_width(cfg)

    eng = Engine()
    eng._cfg[instrument] = cfg
    eng.window = (start, end)

    def equity():
        return cfg.account_start + sum(
            t.pnl for t in eng.closed.get(instrument, [])
            if t.exit_t is not None)

    t4 = d4["t"].to_numpy()
    t15 = m15["t"].to_numpy()
    m15_width = pd.Timedelta(minutes=ae._TF_MINUTES["15m"])
    i0 = int(np.searchsorted(t4, np.datetime64(start), "left"))
    # THE TAPE HAS TO RUN PAST `end`, far enough for the last trade opened
    # inside the window to finish — exactly as `run_instrument` lets `manage`
    # walk past its own window. `eng.window` is what stops those extra
    # candles opening anything new.
    stop_at = pd.Timestamp(end) + pd.Timedelta(days=cfg.max_hold_days + 2)
    i1 = int(np.searchsorted(t4, np.datetime64(stop_at), "right"))

    # THE ENGINE IS WARMED ON THE BAR BEFORE THE WINDOW, so that from the
    # first bar inside it the "newest closed candle only" cold-start rule is
    # behind us and every candle of the window is genuinely walked.
    for i in range(max(0, i0 - 1), min(i1, len(d4))):
        close_t = pd.Timestamp(t4[i]) + width
        j = int(np.searchsorted(t15, np.datetime64(close_t - m15_width),
                                "right"))
        sub = {cfg.tf: d4.iloc[:i + 1], "15m": m15.iloc[:j]}
        for tf in set(("1w",) + tuple(cfg.context_tfs or ())):
            if tf in frames and tf not in sub:
                sub[tf] = frames[tf]
        eng.step(instrument, sub, equity,
                 ae._upq_at(upq_series, close_t), now=close_t)

    trades = list(eng.closed.get(instrument, []))
    if instrument in eng.live:
        # A TRADE STILL OPEN WHEN THE TAPE RAN OUT IS STILL A TRADE, and
        # `run_instrument` reports it the same way — with outcome "open".
        trades.append(eng.live[instrument].trade)
    trades.sort(key=lambda t: (pd.Timestamp(t.entry_t), t.entry))
    return {"instrument": instrument, "engine": eng, "trades": trades}


# ======================================================== OURS, NOT HIS
def in_our_words() -> str:
    """Every choice the LIVE layer made that is not in `alex_engine`'s own
    OURS-NOT-HIS list, in one place, so it is a decision and not an
    oversight."""
    return "\n".join([
        "alex_live.py — OURS, NOT HIS. The method itself is unchanged from",
        "step472; `alex_engine.in_his_words()` is still the list for that.",
        "These are the LIVE decisions on top of it:",
        "",
        "  L1. THE BASE RISK SHARE IS 0.03 FOR BOTH BOOKS, in one place",
        "      (`RISK_PCT`). His own-money band is 3-5%, Wallace's standing",
        "      ruling is 1-3%; the number that satisfies both is 3%. The",
        "      quality dial still scales it UP from there, which is his",
        "      sentence and step472's measured default.",
        "",
        "  L1b. THE WEEKLY-CLOSE DIRECTION RULE IS ON, and that is WALLACE'S",
        "      ruling of 2026-07-27 — \"alex: on\" — not ours and not the",
        "      newest-governs default. It overrides the June-2026 spine's",
        "      one-timeframe simplification, which is what Alex tells a",
        "      BEGINNER rather than what he does. Five years, the four-",
        "      instrument book: -$85,748 without it, +$116,028 with it, mean",
        "      R +0.17 against its own fade at -0.26. It is a FILTER and can",
        "      only ever refuse a trade. See WEEKLY_CLOSE.",
        "",
        "  L2. THE MONEY-GAME LADDER IS ON FOR GOLD, Wallace's ruling of the",
        "      same day: \"ladder on gold too\". It is Alex's own rule and the",
        "      curve is `craig_live.money_game_share`, imported rather than",
        "      rewritten. WHAT IS OURS is how a SHARED STAKE is handled:",
        "      gold and the Craig crypto book are one BloFin account and one",
        "      $2,178 stake, and BOTH read the venue's LIVE equity at the",
        "      moment they size. So a loss in either shrinks the next bet in",
        "      both and a win in either grows both, instead of two books each",
        "      betting the whole stake. They still contend for MARGIN and",
        "      nothing in this file mediates that — the exchange does, and",
        "      what that costs is measured in step473_alex_live.py --margin.",
        "",
        "  L2b. FOREX IS NOT ELIGIBLE FOR THE LADDER, and that is his rule",
        "      rather than a choice: \"anything over $25,000 is where you",
        "      should focus on the percentage game\", and the OANDA account",
        "      holds $100,000. The ladder would return the flat 1% there even",
        "      if it were switched on.",
        "",
        "  L3. A SETUP OLDER THAN THIRTY MINUTES IS NOT ENTERED. His entry is",
        "      a market order at the close of the confirming candle. After a",
        "      restart or a gap in the feed, a 4-hour candle that closed",
        "      three hours ago is a price that no longer exists, and buying",
        "      it now is a different trade, not his at a worse fill. The",
        "      setup is recorded and adopted as history. `ENTRY_FRESHNESS`.",
        "",
        "  L4. THE GOLD BASIS IS A RATIO, NOT A DIFFERENCE. XAUT-USDT and",
        "      XAU/USD are two prices for the same metal and they sit about",
        "      a quarter of a percent apart. Multiplying leaves the stop's",
        "      distance AS A SHARE OF THE PRICE unchanged, and that share is",
        "      what the exchange's margin and liquidation are computed from.",
        "      A basis that cannot be read, or one further than 5% from",
        "      parity, sends nothing at all — there is no fallback to 1.0.",
        "",
        "  L5. GOLD'S MODELLED PROFIT IS IN THE CHART'S PRICES. The engine",
        "      walks OANDA XAU/USD bars, so the pnl it books is spot gold's.",
        "      The real fill, the real stop and the real target are all",
        "      XAUT's. They differ by the basis, which is a quarter of a",
        "      percent of the price and a few percent of the trade's own",
        "      result. The venue's own equity is the number of record, and",
        "      the message reads it from the venue rather than modelling it.",
        "",
        "  L6. THE GOLD BOOK CHOOSES ITS LEVERAGE INSTEAD OF BEING REFUSED",
        "      FOR IT. See `AlexGoldVenue._leverage_for`. The leverage is the",
        "      largest that still leaves the exchange's liquidation three",
        "      times further away than the stop — the identical inequality",
        "      `venue.BlofinVenue` checks, satisfied by construction rather",
        "      than checked and refused afterwards. It can only ever be at or",
        "      BELOW the leverage the parent would have picked, so the margin",
        "      behind a position is never smaller than the parent's, only",
        "      larger. A test holds both directions.",
        "",
        "  L6b. AND WHEN THE STAKE CANNOT CARRY IT, THE ANSWER IS NO TRADE.",
        "      A position that cannot post enough margin for its own stop to",
        "      fire before liquidation is not a smaller version of the same",
        "      trade — it is a different trade risking a number nobody chose.",
        "      Under the ladder this refuses a real share of gold setups; the",
        "      count is in step473_alex_live.py --margin and it is Wallace's",
        "      to change. It is a LOG line, not a message: a GOLD alert that",
        "      says \"not sent\" that often would train him to stop reading",
        "      the header.",
        "",
        "  L7. THE BROKER'S OWN MARGIN CEILING CUTS THE FOREX SIZE, and says",
        "      so. OANDA allows 50:1 on EUR/USD and 20:1 on the two pounds",
        "      pairs; this method's leverage is an output of the stop and on",
        "      a tight 4-hour stop it can ask for more than that. When it",
        "      does, the ALLOWANCE is scaled down so the size fits, which",
        "      keeps the desk's size, the message's size and the order's",
        "      size the same number. The engine's own replay never sees it.",
        "",
        "  L8. THE 4-HOUR AND 15-MINUTE FRAMES ARE THE CACHED PARQUET WITH",
        "      LIVE BARS ON TOP, joined at the timestamp and never shifted.",
        "      Both halves are OANDA mid candles on the same grid, so unlike",
        "      the Yahoo/Alpaca splice on the stock books there is no step",
        "      between them to smooth away. The frame is never cut from the",
        "      LEFT, because his 50 EMA is a running average whose value",
        "      depends on where the series began.",
    ])


if __name__ == "__main__":
    print(__doc__)
    print(in_our_words())
