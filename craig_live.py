"""
craig_live.py — Craig Percoco's method, driving the live crypto desk.

THE DECISION THIS FILE IMPLEMENTS
    Wallace, 2026-07-26: "if craig is profitable for crypto then change it to
    that."

    It is. On the 1-HOUR chart, his own entry (a resting limit at the fair
    value gap midpoint) and his own 1:4, the last twelve months on the five
    surviving pairs made +$21,944 — each pair on its own $100,000, the
    measured round trip charged on every closed trade. That is the ONLY
    net-positive crypto configuration this project has ever measured. Every
    other arm of step467's master table loses money, and the TJR method
    pointed at crypto has never had a profitable year at all.

    So crypto's decision engine is Craig's, from here. STOCKS AND GOLD DO NOT
    MOVE. They stay on the TJR method, in their own files, untouched. Methods
    never mix: nothing in this file reads a TJR level, bias or session, and
    nothing in the TJR files reads anything here.

WHAT SHIPS, EXACTLY — step467's row, and nothing near it
    chart          the 1-hour candle
    entry          a RESTING LIMIT at the midpoint of the fair value gap
    stop           outside the candle that produced that gap, ATTACHED to the
                   entry order so the position is never alive without it
    target         1:4 of the risk actually taken
    break even     the stop moves to the entry once a candle CLOSES beyond a
                   swing in the trade's favour
    sessions       all three opens — Asia, London, New York. Crypto is 24/7
                   and the desk evaluates on every 1-hour close, around the
                   clock, not only at New York hours.
    limit life     24 candles, which on this chart is 24 hours, then the order
                   is cancelled
    size           3% of equity per trade; leverage falls out of the stop

AND ONE THING ON TOP OF IT, FOR THE BLOFIN BOOK ONLY — THE MONEY-GAME LADDER
    Alex Gonzalez: "Anything below $25,000, it's all the money game", and the
    base is set so "you have at least four or five trades in you before you
    would obviously lose the account". Wallace: "This is why I even have it
    set at 2178 ... its how much I would be willing to lose to even start."

    So the BloFin book risks equity / 4.5 a trade at the stake — $484 on
    $2,178, 22.2% OF THE ACCOUNT — stepping down to 1% of the account by
    $25,000. See `money_game_share`.

    IT IS A SIZE AND NOTHING ELSE. It changes no entry, no stop, no target and
    no decision about which setups are taken; `SHIPPING` alone is still what
    every replay and every step467 number is measured on, and
    `test_the_ladder_moves_only_the_size` runs the year both ways and fails on
    the first trade where anything but the coins differs.

NOTHING HERE LIMITS HOW OFTEN IT TRADES
    Wallace, 2026-07-26: "if you see the setup, take the trade. its a demo at
    the end of the day." A cap on trades per day is there so a HUMAN does not
    overtrade on emotion, and the bot has none. The only bounds are the
    method's own — the hunt window after a session open, the 24-candle life of
    the limit, a setup dying at its stop before it fills — plus one of the
    exchange's, that BloFin nets a symbol into ONE position.

ONE DECISION PATH, ONE WINDOW, ONE SIZE — AND THAT IS THE WHOLE POINT
    The 36x sizing bug in this project happened because a replay and a live
    runner each had their own arithmetic, so every backtest described a bot
    nobody was running. So:

      * setups come from `craig_crypto.session_setups`, the same function the
        replay calls, with the window shortened to the candle that has just
        closed;
      * the size comes from `tjr_alerts.position_size`, which forwards to
        `tjr_bot.size_position`, the one place in this project that turns a
        stop into a number of units;
      * `Engine` models fills, stops, targets and break-even with the same
        rules `craig_crypto.manage` applies, and
        `test_craig_live.py::test_the_replay_and_the_live_engine_agree` runs
        the same candles through both and fails on the first trade that
        differs.

SAFETY
    This module places no order by itself. It returns ACTIONS and the desk
    executes them through venue.py, which asks attribution.py first — so even
    here the bot can only ever touch a position it opened. It fetches nothing
    and writes exactly one file, its own measured stop floors, and only when
    asked.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import craig_crypto as cc
import tjr_alerts

REPO = os.path.dirname(os.path.abspath(__file__))

PAIRS = cc.PAIRS

# ============================================== THE SHIPPING CONFIGURATION
#
# step467_master.csv, the 12-month table, five pairs, each on its own
# $100,000, the measured round trip charged on every closed trade:
#
#   chart  entry             target   trades  mean R   net dollars
#   5m     fvg_midpoint      1:4      1118    +0.556      -525,743
#   15m    fvg_midpoint      1:4       687    +0.368      -393,893
#   30m    fvg_midpoint      1:4       297    +0.394      -142,566
#   1h     fvg_midpoint      1:4       140    +0.413      +21,944   <-- this
#
# The reason the 1-hour wins is in the same table and it is not the win rate,
# which barely moves: it is the ratio of what a round trip costs to what the
# trade risks. That ratio is the round trip as a share of the notional divided
# by the stop as a share of the price, and NOTHING about sizing changes it. On
# the 5-minute the stop is 0.144% as a move in the price and the round trip
# eats 1.83 times the risk; on the 1-hour the stop is 0.539% and the round trip
# eats 0.33 times it. The method earns +0.41R a trade on both charts. Only one
# of them keeps it.
#
# THIS IS NOT A DIAL. Nothing in the live path may change it without a fresh
# 12-month measurement.
SHIPPING = {
    "entry_tf": "1h",
    "entry_style": "fvg_midpoint",     # HIS entry: the resting limit
    "target_r": 4.0,                   # HIS target: 1:4
    "risk_pct_per_trade": 0.03,        # the crypto dial as it stands
}

# WHAT THE BLOFIN BOOK ACTUALLY RUNS: the shipping method, plus the
# money-game ladder on top of it. `SHIPPING` alone is what step467 measured
# and what every replay reproduces; `BOOK` is what the desk sends. The
# difference between the two is a SIZE and nothing else — see the ladder
# below, and `test_the_ladder_moves_only_the_size`.
BOOK = {
    # 2026-08-10: THE LADDER COMES OFF THIS BOOK. It was Alex Gonzalez's
    # money-game doctrine applied to Craig Percoco's method — which breaks
    # Wallace's own first law (methods never mix), and ten live days showed
    # what the mix does: $400-600 losses on a $2,178 stake (three of them,
    # −42% of the stake), and refusal cards whenever a pair's leverage cap
    # could not carry a position ~40x the account. Craig states his OWN
    # small-account sizing, 2026-07-05 video: "if you're trying to risk $50
    # per trade and you can use 25x leverage". Fixed dollars, moderate
    # leverage. His book now runs his number — mid-band $75 a trade.
    "money_game_ladder": False,
    "money_game_stake": 2178.0,
    "fixed_risk_dollars": 75.0,     # HIS: "$50 to $100" — mid-band
}


def bar_width(cfg: cc.CraigConfig) -> pd.Timedelta:
    """How long one candle of the working chart lasts. A bar is stamped with
    the minute it STARTED, so its close — the only moment its decision is
    knowable — is this much later."""
    return pd.Timedelta(minutes=cc._TF_MINUTES[cfg.entry_tf])


def live_config(pair: str, **over) -> cc.CraigConfig:
    """The config a live Craig trade is decided on. `over` exists for tests
    and for the replay-agreement harness, never for the desk."""
    return cc.config_for(pair, **{**SHIPPING, **over})


def book_config(pair: str, **over) -> cc.CraigConfig:
    """The config the BloFin book is actually traded on: `live_config` plus
    the money-game ladder. This is what `tjr_desk.CryptoMarket` runs."""
    return live_config(pair, **{**BOOK, **over})


# ==================================================== THE WORKING CHART
def working_chart(frames: dict, cfg: cc.CraigConfig) -> pd.DataFrame:
    """The CLOSED candles of the working chart, built from the desk's own
    cached 5-minute frame. Nothing is fetched here.

    A HALF-BUILT CANDLE IS NOT A CANDLE. The live 5-minute feed's last row is
    very often the one still forming, and resampling it into an hour produces
    an hour that has not happened yet — its high, its low and above all its
    CLOSE will all move. Every rule in this method is read off a close, so
    acting on that bar would be acting on a number that is about to change.
    Only hours whose last 5-minute candle is present and closed survive.
    """
    d5 = frames.get("5m")
    if d5 is None or not len(d5):
        return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
    d = cc.bars({"5m": d5.copy()}, cfg.entry_tf)
    if not len(d):
        return d
    width = pd.Timedelta(minutes=cc._TF_MINUTES[cfg.entry_tf])
    # the last moment the 5-minute tape actually covers
    covered = pd.Timestamp(d5["t"].iloc[-1]) + pd.Timedelta(minutes=5)
    return d[d["t"] + width <= covered].reset_index(drop=True)


# ============================================================ THE STATE
@dataclass
class Working:
    """A resting limit order at the gap midpoint, with its stop attached.

    It is alive for `entry_valid_bars` candles of the working chart and then
    it dies. It also dies the moment price reaches where its stop belongs —
    at that point the structure the setup was built on is already broken and
    there is nothing left to buy.
    """
    pair: str
    session: str
    direction: int
    setup: cc.Setup
    entry: float                 # the limit price: the gap's midpoint
    stop: float
    target: float
    placed_t: pd.Timestamp
    last_look_i: int             # the last candle index the limit may fill on
    equity_at_signal: float
    units: float                 # what was SENT, sized off the limit price
    risk_dollars: float
    # WHAT THE SIZE WAS WORKED OUT UNDER, carried so the message and the
    # record can both say it without re-deriving it. `cap_note` is empty
    # unless the exchange's own leverage ceiling cut the size, and then it is
    # a sentence saying by how much.
    risk_share: float = 0.0
    cap_note: str = ""
    order: dict = field(default_factory=dict)

    @property
    def stop_pct(self) -> float:
        return abs(self.entry - self.stop) / self.entry if self.entry else 0.0


@dataclass
class Position:
    """A filled Craig trade, as the engine models it."""
    pair: str
    session: str
    direction: int
    setup: cc.Setup
    entry_t: pd.Timestamp
    entry: float
    stop: float                  # moves to the entry at break even
    stop_at_risk: float          # the original, kept for the record
    target: float
    units: float
    notional: float
    risk_dollars: float
    equity_at_entry: float
    fill_i: int
    deadline: pd.Timestamp
    be_ref: float | None
    sent_units: float            # what the resting order actually carried
    moved_to_breakeven: bool = False
    best_r: float = 0.0
    exit_t: pd.Timestamp | None = None
    exit: float | None = None
    outcome: str = ""
    pnl: float = 0.0
    cost: float = 0.0
    r_multiple: float = 0.0

    @property
    def leverage(self) -> float:
        return self.notional / self.equity_at_entry if self.equity_at_entry else 0.0


# ============================================================ THE ENGINE
class Engine:
    """Craig's method as a state machine over closed candles.

    ONE CALL PER PAIR PER CLOSED CANDLE. `step` is a no-op until a candle of
    the working chart has actually closed, which is what lets the desk keep
    polling once a minute, around the clock, without the engine acting twice
    on the same hour or acting on half of one.

    It returns ACTIONS. It sends nothing and knows nothing about a venue.
    """

    def __init__(self, cfg_over: dict | None = None):
        self._over = dict(cfg_over or {})
        self._cfg: dict = {}
        self.working: dict = {}        # pair -> [Working]
        self.live: dict = {}           # pair -> [Position]
        self.closed: dict = {}         # pair -> [Position]
        self.seen: set = set()         # (pair, session, choch_t) already taken
        self.last_bar: dict = {}       # pair -> the last candle acted on
        # OPENS ONLY INSIDE THIS WINDOW, when one is set. The live desk never
        # sets it; the agreement harness does, because `craig_crypto.run_pair`
        # bounds which session opens it takes and the two must be bounded the
        # same way or they are not being asked the same question.
        self.window: tuple | None = None

    # ------------------------------------------------------------ config
    def cfg(self, pair: str) -> cc.CraigConfig:
        if pair not in self._cfg:
            self._cfg[pair] = live_config(pair, **self._over)
        return self._cfg[pair]

    # ------------------------------------------------------------- driving
    def step(self, pair: str, d: pd.DataFrame, equity: float) -> list:
        """Every candle of `d` that has closed since the last call.

        Normally that is one candle, once an hour. Between those calls this
        returns an empty list however often it is asked, which is what lets
        the desk keep polling once a minute without the engine ever acting
        twice on the same hour.

        TWO THINGS IT DELIBERATELY DOES NOT DO, and both of them are about
        starting up.

        IT DOES NOT REPLAY HISTORY. The desk hands it ninety-five days of
        candles because that is what the feed returns, and on the first call
        of a process's life there is no record of what has already been acted
        on. Walking all of it would place orders for setups that formed in
        April. So the first call acts on the NEWEST CLOSED CANDLE ONLY and
        adopts the rest as history.

        IT DOES NOT CATCH UP ON A SETUP THAT IS ALREADY DEAD. After a gap in
        the feed, or a redeploy, the candles in between are walked in order —
        a setup is not less real because the process was asleep when it formed
        — but only as far back as a resting limit could still be alive. A
        setup older than that would produce an order that expired before it
        was placed.
        """
        if d is None or len(d) < 4:
            return []
        t = d["t"].to_numpy()
        last = self.last_bar.get(pair)
        if last is None:
            start = len(d) - 1
        else:
            start = int(np.searchsorted(
                t, np.datetime64(pd.Timestamp(last)), "right"))
            start = max(start, len(d) - 1 - int(self.cfg(pair).entry_valid_bars))
        acts = []
        for i in range(max(0, start), len(d)):
            acts.extend(self.on_bar(pair, d, i, equity))
        self.last_bar[pair] = pd.Timestamp(t[-1])
        return acts

    # ------------------------------------------------------------ one bar
    def on_bar(self, pair: str, d: pd.DataFrame, i: int,
               equity: float) -> list:
        """ONE CLOSED CANDLE, in the order `craig_crypto.manage` reads it.

        The order is not cosmetic and the agreement test is what holds it:
          1. the resting limits — die, or fill;
          2. the positions — stop, target, break even, the hold cap. A
             position filled on THIS candle is checked on it too, for the
             stop but never for the target, because the candle we filled
             inside also holds the price action before we were in it.
          3. the new setups this candle stamps, which rest from the NEXT one.
        """
        cfg = self.cfg(pair)
        o = d["open"].to_numpy(float)
        h = d["high"].to_numpy(float)
        lo = d["low"].to_numpy(float)
        c = d["close"].to_numpy(float)
        t = d["t"].to_numpy()
        acts: list = []

        # ------------------------------------------- 1. the resting limits
        still, fresh = [], []
        for wk in list(self.working.get(pair, [])):
            up = wk.direction > 0
            if i <= wk.setup.choch_i:
                still.append(wk)                 # placed on this candle's close
                continue
            if i > wk.last_look_i:
                acts.append(self._cancel(
                    wk, t[i], f"the limit had its {cfg.entry_valid_bars} "
                              f"candles and price never came back to it"))
                continue
            if (lo[i] <= wk.stop) if up else (h[i] >= wk.stop):
                acts.append(self._cancel(
                    wk, t[i], "price reached where the stop belonged before "
                              "the limit filled, so the structure the setup "
                              "was built on is already broken"))
                continue
            if cfg.cancel_on_close_beyond_stop and (
                    (c[i] < wk.stop) if up else (c[i] > wk.stop)):
                acts.append(self._cancel(
                    wk, t[i], "the candle closed beyond where the stop "
                              "belonged, so there is nothing left to trade"))
                continue

            fill = None
            if up:
                if o[i] <= wk.entry:
                    fill = float(o[i])           # opened through it: better
                elif lo[i] <= wk.entry <= h[i]:
                    fill = float(wk.entry)
            else:
                if o[i] >= wk.entry:
                    fill = float(o[i])
                elif lo[i] <= wk.entry <= h[i]:
                    fill = float(wk.entry)
            if fill is None:
                still.append(wk)
                continue

            pos = self._fill(wk, fill, i, t, cfg)
            if pos is None:
                continue
            fresh.append(pos)
            acts.append({"kind": "filled", "pair": pair, "symbol": pair,
                         "at": pd.Timestamp(t[i]), "price": fill,
                         "position": pos, "working": wk})
        self.working[pair] = still

        # ------------------------------------------------ 2. the positions
        held = list(self.live.get(pair, [])) + fresh
        keep = []
        for pos in held:
            act = self._watch(pos, d, o, h, lo, c, t, i, cfg)
            if act is not None:
                acts.append(act)
            if pos.exit_t is None:
                keep.append(pos)
            else:
                self.closed.setdefault(pair, []).append(pos)
        self.live[pair] = keep

        # ------------------------------------------------ 3. the new setups
        #
        # EQUITY IS READ HERE, NOT AT THE TOP OF THE BAR. A trade that closed
        # a moment ago on this same candle is money the account already has,
        # and `craig_crypto.run_pair` counts it — it sizes each setup on
        # "every trade that had CLOSED by this setup's own timestamp". Reading
        # it before the exits above would size the next trade on stale equity.
        eq = float(equity() if callable(equity) else equity)
        for s in self._setups_on(pair, d, t, i, cfg):
            key = (pair, s.session, pd.Timestamp(s.choch_t))
            if key in self.seen:
                continue
            self.seen.add(key)
            wk = self._place(pair, s, i, eq, cfg, t)
            if wk is None:
                continue
            self.working.setdefault(pair, []).append(wk)
            acts.append({"kind": "enter", "pair": pair, "symbol": pair,
                         "at": pd.Timestamp(t[i]), "working": wk,
                         "signal": self.signal(wk, eq)})
        return acts

    # -------------------------------------------------------- the pieces
    def _setups_on(self, pair, d, t, i, cfg) -> list:
        """Every setup this candle stamps, through the replay's own window
        arithmetic with the future removed."""
        now = pd.Timestamp(t[i])
        out = []
        for name in cfg.sessions:
            for ts in cc.session_opens(now - pd.Timedelta(days=2), now, name):
                if ts > now or now >= ts + pd.Timedelta(minutes=cfg.hunt_minutes):
                    continue
                if self.window is not None and not (
                        self.window[0] <= ts <= self.window[1]):
                    continue
                for s in cc.session_setups(d, t, ts, name, cfg, pair=pair,
                                           upto_i=i):
                    if s.choch_i == i:
                        out.append(s)
        return out

    def _place(self, pair, s: cc.Setup, i, equity, cfg, t) -> Working | None:
        """Size the resting order off the LIMIT price, which is the only
        price that exists when the order is sent."""
        dist = abs(s.entry - s.stop)
        if dist <= 0:
            return None
        size = size_for(pair, equity, s.entry, dist, cfg)
        if not size["ok"] or size["units"] <= 0:
            return None
        return Working(
            pair=pair, session=s.session, direction=s.direction, setup=s,
            entry=float(s.entry), stop=float(s.stop), target=float(s.target),
            placed_t=pd.Timestamp(t[i]),
            last_look_i=int(s.choch_i) + int(cfg.entry_valid_bars),
            equity_at_signal=float(equity), units=float(size["units"]),
            risk_dollars=float(size["risk_dollars"]),
            risk_share=float(size.get("risk_share_used") or 0.0),
            cap_note=str(size.get("leverage_cap_note") or ""))

    def _fill(self, wk: Working, px: float, i, t, cfg) -> Position | None:
        """THE PLAN IS RE-DRAWN OFF THE PRICE ACTUALLY PAID — the same rule
        `craig_crypto.manage` applies. A limit that fills at the open because
        the candle opened past it is filled BETTER than planned, so the real
        distance to the stop is smaller and 1:4 of it is nearer.

        Measured over the shipping year: 1 fill in 140 came in better than the
        limit, by 0.065% AS A MOVE IN THE PRICE. The units cannot change, the
        order is already resting with them — so that one trade risks slightly
        LESS than its 3% share of equity, never more.
        """
        s = wk.setup
        dirn = wk.direction
        dist = abs(px - s.stop)
        if dist <= 0:
            return None
        target = px + dirn * cfg.target_r * dist
        size = size_for(wk.pair, wk.equity_at_signal, px, dist, cfg)
        if not size["ok"] or size["units"] <= 0:
            return None
        units = float(size["units"])
        be_ref = s.be_level if (
            (px < s.be_level) if dirn > 0 else (px > s.be_level)) else None
        return Position(
            pair=wk.pair, session=wk.session, direction=dirn, setup=s,
            entry_t=pd.Timestamp(t[i]), entry=px, stop=float(s.stop),
            stop_at_risk=float(s.stop), target=float(target), units=units,
            notional=units * px, risk_dollars=float(size["risk_dollars"]),
            equity_at_entry=float(wk.equity_at_signal), fill_i=int(i),
            deadline=pd.Timestamp(t[i]) + pd.Timedelta(hours=cfg.max_hold_hours),
            be_ref=be_ref, sent_units=float(wk.units))

    def _watch(self, pos: Position, d, o, h, lo, c, t, i, cfg):
        """One candle against one open position — `manage`'s loop body."""
        up = pos.direction > 0
        dist = abs(pos.entry - pos.stop_at_risk)
        ts = pd.Timestamp(t[i])
        fav = (h[i] - pos.entry) if up else (pos.entry - lo[i])
        pos.best_r = max(pos.best_r, fav / dist if dist else 0.0)

        hit_stop = (lo[i] <= pos.stop) if up else (h[i] >= pos.stop)
        hit_tgt = (i > pos.fill_i) and (
            (h[i] >= pos.target) if up else (lo[i] <= pos.target))

        if hit_stop:
            why = "break even" if pos.moved_to_breakeven and \
                abs(pos.stop - pos.entry) < 1e-12 else "stopped out"
            return self._close(pos, pos.stop, ts, why, dist, cfg)
        if hit_tgt:
            return self._close(pos, pos.target, ts, "target", dist, cfg)

        # HIS BREAK EVEN. "waiting for a candle to close over this most recent
        # swing up before our entry ... reduce this risk all the way to break
        # even." On the CLOSE, never a wick, and only on a swing price has not
        # already passed.
        if cfg.breakeven_on_swing_close and not pos.moved_to_breakeven:
            if pos.be_ref is not None and (
                    (c[i] > pos.be_ref) if up else (c[i] < pos.be_ref)):
                pos.stop = pos.entry
                pos.moved_to_breakeven = True
                return {"kind": "breakeven", "pair": pos.pair,
                        "symbol": pos.pair, "at": ts, "level": pos.entry,
                        "position": pos,
                        "why": (f"a 1-hour candle closed "
                                f"{'above' if up else 'below'} "
                                f"{pos.be_ref:,.6g}, the swing the move made "
                                f"before we got in, so the stop goes to your "
                                f"entry and the trade cannot cost anything "
                                f"from here")}
            if pos.be_ref is None:
                sh, sl = _swings_at(o, h, lo, c, i)
                cand = sh if up else sl
                if cand is not None and (
                        (cand > pos.entry) if up else (cand < pos.entry)):
                    pos.be_ref = float(cand)

        if ts >= pos.deadline:
            return self._close(pos, float(c[i]), ts, "held to the cap",
                               dist, cfg)
        return None

    def _close(self, pos: Position, px, ts, why, dist, cfg):
        pos.exit, pos.exit_t, pos.outcome = float(px), pd.Timestamp(ts), why
        gross = pos.direction * (float(px) - pos.entry) * pos.units
        pos.cost = cfg.round_trip_cost_pct * pos.units * pos.entry
        pos.pnl = gross - pos.cost
        pos.r_multiple = (pos.direction * (float(px) - pos.entry)) / dist
        return {"kind": "exit", "pair": pos.pair, "symbol": pos.pair,
                "at": pos.exit_t, "price": pos.exit, "outcome": why,
                "position": pos}

    @staticmethod
    def _cancel(wk: Working, when, why: str) -> dict:
        return {"kind": "cancel", "pair": wk.pair, "symbol": wk.pair,
                "at": pd.Timestamp(when), "working": wk, "why": why}

    # ------------------------------------------------------- the signal
    def signal(self, wk: Working, equity: float) -> dict:
        """The dict the desk already consumes, for one Craig entry.

        Same keys, same meanings. `order_type` is the one addition and it is
        the whole difference between the two methods at the venue: TJR fires
        on a candle closing and goes in at market; Craig waits for price to
        come back to him, so his entry is a LIMIT that rests.
        """
        cfg = self.cfg(wk.pair)
        return {
            "market": "crypto",
            "symbol": wk.pair,
            "direction": wk.direction,
            "side": "buy" if wk.direction > 0 else "sell",
            "order_type": "limit",
            "reference_price": wk.entry,      # the resting limit's own price
            "limit_price": wk.entry,
            "stop": wk.stop,
            "targets": [wk.target],
            "target_sources": ["1:4 of the risk this trade actually takes"],
            "target_fractions": [1.0],
            "runner_fraction": 0.0,
            "partial_fraction": 1.0,
            "single_exit": True,
            "budget_share": 1.0,
            "derisk": False,
            "entry_t": wk.placed_t,
            "session": wk.session,
            "engine": "craig",
            "why": why_line(wk.setup),
            # ------------------------------------------------------ sizing
            # The three inputs the size was worked out from, forwarded so the
            # desk's own call reproduces it exactly rather than re-deriving.
            #
            # WHEN THE LADDER IS ON THESE ARE THE LADDER'S DOLLARS, and that
            # is the whole of how it reaches the order. `tjr_desk._size_for`
            # works its risk share back out of `risk_wanted / equity` and
            # spends `outer_allowance` exactly, so the desk's own call and
            # the engine's land on the same units without the desk having to
            # know the ladder exists.
            # `test_the_desk_and_the_engine_size_the_ladder_identically`
            # fails on the first trade where they do not.
            "risk_wanted": risk_share_for(float(equity), cfg) * float(equity),
            "outer_allowance": risk_share_for(float(equity), cfg) * float(equity),
            "buying_power_used": None,
            # HIS SIZE IS SPENT, NOT HELD STILL. Craig states the arithmetic
            # himself — "500 divided by $18 ... that's going to give us the
            # amount of units that we need in order to risk exactly $500" —
            # so the size falls out of TODAY'S stop and the allowance is
            # spent exactly. That is `hold_size_still=False`, and it is the
            # rule every number in step467 was measured under.
            "hold_size_still": False,
            "tightest_stop_pct": tightest_stop_pct(wk.pair),
            "units_wanted": wk.units,
            "risk_dollars": wk.risk_dollars,
            "sizing_account": equity,
            # THE LADDER, SAID OUT LOUD ON EVERY SIGNAL. Not a new message
            # shape — nothing renders these — but the record and the console
            # both carry which rule sized this trade and whether the
            # exchange's ceiling cut it.
            "money_game_ladder": bool(getattr(cfg, "money_game_ladder", False)),
            "money_game_stake": float(getattr(cfg, "money_game_stake", 0.0)),
            "risk_share_used": wk.risk_share,
            "leverage_cap_note": wk.cap_note,
            # WHAT THE EXCHANGE WILL ACTUALLY SET, so the message states the
            # leverage and the margin his BloFin screen will show rather than
            # the one a 10%-of-the-account margin budget implies. Under the
            # ladder those two are far apart: an ETH position 60 times the
            # account would need 602x on a 10% margin, and this instrument
            # stops at 150x — so the exchange posts four times the margin
            # instead. Saying 602x would be saying a number that cannot exist.
            "leverage_ceiling": leverage_ceiling(wk.pair),
            # what the message says the stop sits on, in his own words
            "level_tf": cfg.entry_tf,
            "level_price": wk.setup.broken_level,
            "stop_anchor": wk.setup.stop_from,
            "expires_after_bars": cfg.entry_valid_bars,
        }


def _swings_at(o, h, lo, c, i):
    """`tjr_bot.two_candle_swings` for one index, which is all a live bar
    needs. An up candle then a down candle stamps a high at the higher of the
    two wicks; the mirror stamps a low. It reads candle i-1 and candle i and
    nothing else, so it is knowable the moment candle i closes."""
    if i < 1:
        return None, None
    up_prev, dn_prev = c[i - 1] > o[i - 1], c[i - 1] < o[i - 1]
    up_now, dn_now = c[i] > o[i], c[i] < o[i]
    sh = max(h[i - 1], h[i]) if (up_prev and dn_now) else None
    sl = min(lo[i - 1], lo[i]) if (dn_prev and up_now) else None
    return sh, sl


# ================================================== THE MONEY-GAME LADDER
#
# WHOSE IDEA THIS IS
#
# Alex Gonzalez, 2026-02-22, `ag_transcripts/LwMsai2ppKc_growsmall_clean.txt`:
#
#   "when you have anything over ... $25,000 is where you should focus on the
#    percentage game ... Anything below $25,000, it's all the money game."
#   "risk management when you're scaling a small account is no longer
#    percentage. It's the money game."
#   "you have to make sure that you have at least FOUR OR FIVE TRADES IN YOU
#    before you would obviously lose the account."
#   "as you start creating a bigger account, you LOWER that risk so you're not
#    prone to blowing this account."
#
# And Wallace, 2026-07-26, on where the stake itself comes from:
#
#   "This is why I even have it set at 2178 ... its how much I would be
#    willing to lose to even start."
#
# WHAT IS HIS AND WHAT IS OURS, stated so it can never be blurred later:
#
#   HIS   four or five trades in you           -> the base is equity / 4.5
#   HIS   the percentage game starts at $25,000
#   HIS   the percentage game is 1% of equity
#   HIS   the stake is $2,178
#   OURS  the SHAPE of the step-down between those two anchors. He says only
#         that the risk comes down as the account grows; he never draws the
#         curve. One function, below, and it is the only thing here anyone
#         may argue about.
#
# WHAT IT IS NOT. It is not part of Craig's method and it touches nothing in
# it: not an entry, not a stop, not a target, not which setups are taken.
# It sets ONE number — the dollars a trade may cost — and everything else in
# this file is identical with it on and with it off.
# `test_the_ladder_moves_only_the_size` runs the shipping year both ways and
# fails if a single entry, stop, target or outcome differs.

MONEY_GAME_TRADES_IN_YOU = 4.5      # HIS: "at least four or five trades in you"
PERCENTAGE_GAME_AT = 25_000.0       # HIS: "$25,000 is where you should focus
                                    #       on the percentage game"
PERCENTAGE_GAME_SHARE = 0.01        # HIS: "that's just risking 1%"


def money_game_share(equity: float, stake: float) -> float:
    """What share of the account ONE TRADE may cost, at this balance.

    Two anchors, both his:

        at the stake ($2,178)   1 / 4.5  = 22.2% of the account, which is
                                "four or five trades in you before you would
                                obviously lose the account"
        at $25,000              1% of the account, "the percentage game"

    OURS, NOT HIS — THE SHAPE BETWEEN THEM, and this is the whole of it. The
    share moves GEOMETRICALLY: every time the account multiplies by the same
    factor, the share it risks divides by the same factor. It is the only
    simple curve that hits both of his anchors, never jumps, and never turns
    back up — and the dollars it risks fall the whole way, from about $484 at
    the stake to $250 at $25,000, which is exactly the "as you start creating
    a bigger account, you lower that risk" he asks for. A straight line
    between the two anchors does NOT do that: it would have the dollars at
    risk climb to about $1,500 around $10,000 before collapsing to $250, and
    a rule that risks three times more at $10,000 than at $2,178 is not a
    step-down.
    """
    base = 1.0 / MONEY_GAME_TRADES_IN_YOU
    stake = float(stake or 0.0)
    equity = float(equity)
    if equity <= 0:
        return 0.0
    if stake <= 0 or stake >= PERCENTAGE_GAME_AT:
        return PERCENTAGE_GAME_SHARE
    if equity <= stake:
        return base
    if equity >= PERCENTAGE_GAME_AT:
        return PERCENTAGE_GAME_SHARE
    progress = np.log(equity / stake) / np.log(PERCENTAGE_GAME_AT / stake)
    return float(base * (PERCENTAGE_GAME_SHARE / base) ** progress)


def money_game_risk_dollars(equity: float, stake: float) -> float:
    """The dollars one trade may cost at this balance. HIS number, in dollars,
    because dollars are what the money game is played in."""
    return money_game_share(equity, stake) * float(equity)


def risk_share_for(equity: float, cfg: cc.CraigConfig) -> float:
    """The share of the account one trade may cost — ONE function, so the
    engine, the desk and the report cannot drift apart about it.

    Priority order, each level a professional's own stated rule:
      1. `fixed_risk_dollars` — Craig's own small-account sizing ("risk $50
         per trade... 25x leverage"), expressed as the share of the CURRENT
         account that his fixed dollars amount to.
      2. the money-game ladder (Alex's doctrine) where a book runs it.
      3. the flat dial otherwise."""
    fixed = float(getattr(cfg, "fixed_risk_dollars", 0.0) or 0.0)
    if fixed > 0 and equity > 0:
        return min(fixed / float(equity), 0.25)
    if not getattr(cfg, "money_game_ladder", False):
        return float(cfg.risk_pct_per_trade)
    return money_game_share(equity, getattr(cfg, "money_game_stake", 0.0))


# ==================================== THE EXCHANGE'S OWN LEVERAGE CEILING
#
# BloFin's maximum leverage per instrument, read from its instrument spec on
# 2026-07-26. THE LIVE ORDER PATH DOES NOT USE THIS TABLE — `venue.BlofinVenue`
# reads the spec fresh from the exchange on every order and a spec it cannot
# read means DO NOT TRADE, never a default. This copy exists so the size the
# engine MODELS is the size the exchange can actually carry, which is the
# difference between reporting a truncation and discovering one.
LEVERAGE_CEILING = {
    "BTC/USD": 150.0, "ETH/USD": 150.0,
    "SOL/USD": 75.0, "DOT/USD": 75.0, "XRP/USD": 50.0,
}


def leverage_ceiling(pair: str) -> float:
    """The most leverage this instrument allows. Missing means unknown, and
    unknown means no truncation is claimed — the venue still refuses on its
    own if the number turns out to be smaller."""
    return float(LEVERAGE_CEILING.get(pair) or 0.0)


# ================================================================ SIZING
def size_for(pair: str, equity: float, entry: float, dist: float,
             cfg: cc.CraigConfig) -> dict:
    """THE ONE SIZING PATH, through the desk's own front door.

    `tjr_alerts.position_size` translates the market's units and then calls
    `tjr_bot.size_position`, which is the one place in this project that turns
    a stop into a number of units. Going through the wrapper rather than
    around it is what makes the number the desk sends and the number the
    replay books provably the same one — `test_craig_live.py` asserts they are
    equal on every trade of the shipping year.

    `hold_size_still=False` is Craig's own arithmetic and it is why the
    wrapper can be used at all: with it, the tightest stop is not what the
    size is worked out from, so the two paths cannot disagree about it.

    THE LADDER IS A WRAPPER AND NOTHING MORE. When it is on, the only thing
    that changes is the DOLLARS handed to that same call. The position still
    comes out of the same function, off the same stop.

    THE EXCHANGE'S CEILING IS RESPECTED AND SAID OUT LOUD. A position bigger
    than `max leverage x the whole account` cannot be carried on this venue at
    any margin, so it is cut to what can be — and the answer carries
    `truncated_by_leverage_cap` and a sentence saying so, rather than a
    quietly smaller number nobody would ever notice.
    """
    equity = float(equity)
    risk_pct = risk_share_for(equity, cfg)
    allowance = risk_pct * equity
    out = tjr_alerts.position_size(
        "crypto", pair, equity, float(entry), float(dist),
        tightest_stop_pct(pair), 1.0, risk_pct,
        buying_power=None, outer_allowance=allowance, hold_size_still=False)
    out["risk_share_used"] = risk_pct
    out["money_game_ladder"] = bool(getattr(cfg, "money_game_ladder", False))
    out["truncated_by_leverage_cap"] = False
    out["leverage_cap_note"] = ""
    if not out.get("ok"):
        return out

    ceiling = leverage_ceiling(pair)
    if ceiling <= 0 or equity <= 0 or entry <= 0:
        return out
    wanted_units = float(out["units"])
    wanted_face = wanted_units * float(entry)
    most = ceiling * equity                      # the whole account as margin
    if wanted_face <= most:
        return out
    units = most / float(entry)
    out["uncapped_units"] = wanted_units
    out["uncapped_risk_dollars"] = float(out["risk_dollars"])
    out["units"] = units
    out["risk_dollars"] = units * float(dist)
    out["risk_share_pct"] = 100.0 * out["risk_dollars"] / equity
    out["truncated_by_leverage_cap"] = True
    out["leverage_cap_note"] = (
        f"CUT BY THE EXCHANGE'S CEILING — the ladder asked for a "
        f"{pair} position worth ${wanted_face:,.0f}, which is "
        f"{wanted_face / equity:.0f} times the account, and this instrument "
        f"tops out at {ceiling:.0f}x leverage even with the whole balance "
        f"posted as margin. It was cut to ${most:,.0f}, so this trade risks "
        f"${out['risk_dollars']:,.2f} instead of "
        f"${out['uncapped_risk_dollars']:,.2f}.")
    return out


# =============================================== CRAIG'S OWN STOP FLOORS
#
# HIS RULE'S ONE INPUT, MEASURED FROM HIS OWN SETUPS AND NOBODY ELSE'S.
#
# `tjr_desk.tightest_stop_pct` reads step443_stop_floors.json, which was
# measured from the TJR method's 5-minute setups. Those are a different
# method on a different chart and a Craig trade may not borrow one: "sizing
# off another market's number is exactly what his rule forbids", and a
# different method's number is further away still. Methods never mix.
#
# So Craig's floors live in their own file, measured from Craig's own 1-hour
# setups on the shipping configuration. WHAT IT IS ACTUALLY USED FOR, stated
# plainly: with `hold_size_still=False` the size falls out of today's stop and
# this number changes no unit count at all. It is here because
# `tjr_alerts.position_size` REFUSES to state a size for an instrument whose
# tightest stop has never been measured — and the honest answer to that
# refusal is to measure it, not to switch it off.
STOP_FLOOR_PATH = f"{REPO}/step469_craig_stop_floors.json"
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


def tightest_stop_pct(pair: str) -> float:
    return float((stop_floors().get(pair) or {}).get("tightest_stop_pct") or 0.0)


def derive_stop_floors(start=None, end=None, verbose: bool = True) -> dict:
    """Measure the tightest stop each pair's Craig setups normally give, on
    the shipping chart. Reads cached parquet, writes one JSON file, touches
    no venue and places nothing.

    THE TENTH PERCENTILE, NOT THE SMALLEST, for the reason tjr_desk gives:
    "what's USUALLY the lowest your stop loss will be", not the lowest it has
    ever been. One freak candle is not a rule.
    """
    end = pd.Timestamp(end or "2026-07-26")
    start = pd.Timestamp(start or (end - pd.Timedelta(days=364)))
    out = dict(stop_floors())
    for pair in PAIRS:
        cfg = live_config(pair)
        r = cc.run_pair(pair, start, end, cfg=cfg, data=cc.load(pair))
        pct = [abs(t.entry - t.stop_at_risk) / t.entry
               for t in r["trades"] if t.entry]
        if not pct:
            continue
        out[pair] = {
            "tightest_stop_pct": float(np.percentile(pct, STOP_FLOOR_PERCENTILE)),
            "median_stop_pct": float(np.median(pct)),
            "widest_stop_pct": float(np.max(pct)),
            "setups_measured": len(pct),
            "chart": cfg.entry_tf, "engine": "craig",
        }
        if verbose:
            v = out[pair]
            print(f"  {pair:9s} tightest {100*v['tightest_stop_pct']:.3f}% of "
                  f"price   typical {100*v['median_stop_pct']:.3f}%   widest "
                  f"{100*v['widest_stop_pct']:.3f}%   "
                  f"(from {v['setups_measured']} trades on the "
                  f"{v['chart']} chart)")
    with open(STOP_FLOOR_PATH, "w") as fh:
        json.dump(out, fh, indent=2)
    global _FLOORS
    _FLOORS = out
    return out


# ============================================================= THE WORDS
def why_line(s: cc.Setup) -> str:
    """WHY THIS TRADE EXISTS, in one sentence, with no term in it he would
    have to stop and translate.

    His vocabulary is "change of character", "fair value gap", "the golden
    61.8". None of those three reaches the phone. A change of character is a
    candle closing past the last turning point against the trend; a fair value
    gap is a stretch of price the market jumped over and left empty; the 61.8
    is how far back into the move price has come.
    """
    up = s.direction > 0
    turned = "up" if up else "down"
    against = "high" if up else "low"
    jumped = "up" if up else "down"
    kind = ("the first turn of the session"
            if s.kind == "choch" else "another leg the same way")
    named = {"asia": "Asia", "london": "London",
             "new_york": "New York"}.get(s.session, s.session)
    return (
        f"At the {named} open the 1-hour chart turned "
        f"{turned} — {kind}: a candle closed past {s.broken_level:,.6g}, the "
        f"last {against} the other side had made. The move {jumped} left a "
        f"stretch of price between {min(s.gap_lo, s.gap_hi):,.6g} and "
        f"{max(s.gap_lo, s.gap_hi):,.6g} that the market jumped clean over, "
        f"and that stretch sits in the middle of the move where he waits for "
        f"price to come back. So the order rests at "
        f"{s.entry:,.6g}, the middle of that stretch, the stop sits at "
        f"{s.stop:,.6g} just outside the candle that made it, and the target "
        f"is four times that distance the other way.")


# =============================================== THE VENUE, EXTENDED
#
# WHY A SUBCLASS AND NOT AN EDIT TO venue.py
#
# BlofinVenue opens at MARKET, because the TJR method's trigger is a candle
# closing and a limit that never fills is a signal missed. Craig's entry is
# the opposite instruction: he waits for price to come back to the middle of
# the gap, and a fill at any other price is not his trade. So this venue needs
# a resting LIMIT, and it needs the stop attached to it in the same request.
#
# Everything else is inherited unchanged and deliberately so — the attribution
# gate, the sealed client, the coins-to-contracts conversion, the leverage
# derivation, the liquidation check, the refusal to open on a symbol carrying
# a position the bot cannot prove is its own. None of that is re-implemented
# here, which is the only way to be sure none of it was weakened.


def _craig_blofin_factory(**kw):
    return CraigBlofinVenue(**kw)


class CraigBlofinVenue:
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
    credentials at all."""
    global CraigBlofinVenue
    try:
        import venue as venue_mod
    except Exception:                                        # noqa: BLE001
        return None

    class _CraigBlofinVenue(venue_mod.BlofinVenue):
        """BloFin's DEMO futures host with a resting limit entry."""

        name = "blofin-demo-craig"
        is_real_money = False

        # --------------------------------------------------------- opening
        def limit_order(self, symbol: str, side: str, qty: float,
                        price: float, **kw) -> dict:
            """A RESTING LIMIT with its stop attached, sized in COINS.

            THE STOP RIDES IN WITH THE ENTRY, exactly as it does for a market
            order here. Wallace, 2026-07-26: "stops can literally be placed
            with the order together, it doesnt have to be after". For a
            resting limit that matters more, not less: the order can fill at
            any moment over the next day, including while this process is
            being redeployed, and a second call cannot be made at a moment
            nobody is watching.

            NO STOP, NO ORDER. Same refusal as the market path, and the same
            reason: a caller that forgets the argument would otherwise rest an
            order that opens a naked position.
            """
            reason = kw.get("reason", "")
            inst = self.venue_symbol(symbol)
            spec = self.spec(symbol)
            cv = spec.get("contract_value") or 0.0
            lot = spec.get("lot") or 0.0
            tick = spec.get("tick") or 0.0
            if cv <= 0:
                return self._record({
                    "status": "rejected", "kind": "limit", "symbol": symbol,
                    "side": side, "qty": qty,
                    "reason": "the exchange's instrument spec could not be "
                              "read, so coins cannot be turned into contracts "
                              "without guessing. Not trading on a guess.",
                    "note": reason})

            stop = kw.get("stop")
            if stop is None:
                return self._record({
                    "status": "rejected", "kind": "limit", "symbol": symbol,
                    "side": side, "qty": qty, "refused_by": "no stop",
                    "reason": "a resting entry must carry its stop, and this "
                              "one did not. Nothing was sent.", "note": reason})
            wrong = (side == "buy" and float(stop) >= float(price)) or \
                    (side == "sell" and float(stop) <= float(price))
            if wrong:
                return self._record({
                    "status": "rejected", "kind": "limit", "symbol": symbol,
                    "side": side, "qty": qty,
                    "refused_by": "stop on the wrong side",
                    "reason": f"the stop at {float(stop):g} is on the wrong "
                              f"side of {float(price):g} for a {side}, so it "
                              f"would close the trade the instant it opened. "
                              f"Nothing was sent.", "note": reason})

            # BLOFIN NETS EVERYTHING ON A SYMBOL INTO ONE POSITION, so an
            # order that would fuse the bot's trade to one it cannot prove is
            # its own is refused before it is sent — inherited rule, applied
            # to the resting entry as well as to the market one.
            for row in self._rows():
                if str(row.get("instId")) == inst:
                    v = self._verdict_for_row(row)
                    if not v.ours:
                        return self._record({
                            "status": "rejected", "kind": "limit",
                            "symbol": symbol, "side": side, "qty": qty,
                            "refused_by": "attribution",
                            "reason": f"there is already a position on {inst} "
                                      f"that the bot did not open, and this "
                                      f"exchange nets everything on a symbol "
                                      f"into ONE position. {v.reason}",
                            "verdict": v.to_dict(), "note": reason})

            contracts = abs(qty) / cv
            if lot > 0 and contracts < lot:
                return self._record({
                    "status": "rejected", "kind": "limit", "symbol": symbol,
                    "side": side, "qty": qty,
                    "reason": f"the size works out to {contracts:.4f} "
                              f"contracts and this symbol's smallest tradeable "
                              f"amount is {lot}. Too small to place.",
                    "note": reason})

            lev = kw.get("leverage")
            if lev is None:
                lev = self._leverage_for(symbol, qty, stop, price)
            if isinstance(lev, dict):
                return self._record(dict(lev, kind="limit", symbol=symbol,
                                         side=side, qty=qty, note=reason))
            if not self._raw.ensure_leverage(inst, lev, self._bp.MARGIN_MODE):
                return self._record({
                    "status": "rejected", "kind": "limit", "symbol": symbol,
                    "side": side, "qty": qty,
                    "reason": "the leverage could not be set on this symbol, "
                              "and placing the order anyway is how the "
                              "2026-07-23 silent-rejection bug happened.",
                    "note": reason})

            targets = kw.get("targets") or []
            coid = self._bp.make_client_order_id(self._tag)
            try:
                oid = self._cli.limit_order(
                    inst, side, contracts, float(price),
                    margin_mode=self._bp.MARGIN_MODE, client_order_id=coid,
                    lot_size=lot, tick_size=tick, stop_price=float(stop),
                    take_profit=(float(targets[-1]) if targets else None))
            except Exception as e:                           # noqa: BLE001
                return self._record({"status": "rejected", "kind": "limit",
                                     "symbol": symbol, "side": side,
                                     "qty": qty, "client_order_id": coid,
                                     "reason": str(e)[:300], "note": reason})
            return self._record({"status": "resting", "kind": "limit",
                                 "symbol": symbol, "venue_symbol": inst,
                                 "side": side, "qty": qty,
                                 "contracts": contracts, "price": float(price),
                                 "stop": float(stop),
                                 "target": (float(targets[-1]) if targets
                                            else None),
                                 "leverage": lev,
                                 "margin_mode": self._bp.MARGIN_MODE,
                                 "id": oid, "client_order_id": coid,
                                 "tag": self._tag,
                                 "rests_at_exchange": True, "note": reason})

        # -------------------------------------------------------- cancelling
        def cancel_entry(self, symbol: str, order_id: str | None = None,
                         **kw) -> dict:
            """Take a RESTING ENTRY of ours off the book.

            THE PROOF HERE IS THE ORDER, NOT THE POSITION, and that is
            stronger rather than weaker. `_guarded_reduce` proves a POSITION
            was opened by the bot — but a resting entry has no position yet,
            so that question has no answer and would resolve, correctly, to
            "his". What can be proved instead is that the ORDER carries a
            clientOrderId this codebase built, which is the same proof
            `cancel_stops` applies row by row before it touches a bracket.
            Anything without our tag is left exactly where it is.
            """
            import attribution
            inst = self.venue_symbol(symbol)
            try:
                pending = self._raw.pending_orders(inst) or []
            except Exception as e:                           # noqa: BLE001
                return self._record({"status": "rejected",
                                     "kind": "cancel_entry", "symbol": symbol,
                                     "reason": str(e)[:300]})
            killed, left = [], []
            token = object()
            object.__setattr__(self._cli, "open_for", token)
            try:
                for row in pending:
                    oid = str(row.get("orderId") or "")
                    if order_id is not None and oid != str(order_id):
                        continue
                    if not attribution.is_ours_coid(row.get("clientOrderId")):
                        left.append(oid)
                        continue
                    try:
                        self._cli.cancel_order(inst, oid)
                        killed.append(oid)
                    except Exception:                        # noqa: BLE001
                        left.append(oid)
            finally:
                object.__setattr__(self._cli, "open_for", None)
            return self._record({"status": "done", "kind": "cancel_entry",
                                 "symbol": symbol, "venue_symbol": inst,
                                 "cancelled": killed, "left_alone": left,
                                 "reason": kw.get("reason", "")})

        def resting_entries(self, symbol: str) -> list:
            """Our own resting entry orders on one symbol. Read only."""
            import attribution
            try:
                rows = self._raw.pending_orders(self.venue_symbol(symbol)) or []
            except Exception:                                # noqa: BLE001
                return []
            return [r for r in rows
                    if attribution.is_ours_coid(r.get("clientOrderId"))]

    CraigBlofinVenue = _CraigBlofinVenue
    try:
        venue_mod.register(
            "blofin-demo-craig", _craig_blofin_factory, real_money=False,
            note="BloFin's DEMO futures host, driven by CRAIG's method. Same "
                 "attribution gate, sealed client and isolated margin as "
                 "blofin-demo; the one difference is that the entry is a "
                 "RESTING LIMIT at the fair value gap midpoint with its stop "
                 "attached, because his entry waits for price to come back "
                 "rather than chasing a candle close")
    except Exception:                                        # noqa: BLE001
        pass
    return CraigBlofinVenue


_install_venue()


# ======================================================= READING IT BACK
def frame(engine: Engine) -> pd.DataFrame:
    """One row per closed trade, in the same words `craig_crypto.frame` uses,
    so a live book and a replay book can be put side by side."""
    rows = []
    for pair, trades in engine.closed.items():
        for t in trades:
            rows.append({
                "pair": pair, "session": t.session,
                "choch_t": t.setup.choch_t, "entry_t": t.entry_t,
                "exit_t": t.exit_t,
                "side": "long" if t.direction > 0 else "short",
                "entry": t.entry, "stop": t.stop_at_risk, "target": t.target,
                "exit": t.exit, "outcome": t.outcome,
                "stop_move_in_price_pct":
                    100.0 * abs(t.entry - t.stop_at_risk) / t.entry,
                "leverage": t.leverage, "units": t.units,
                "sent_units": t.sent_units,
                "notional": t.notional, "risk_dollars": t.risk_dollars,
                "pnl": t.pnl, "cost": t.cost, "r": t.r_multiple,
                "mfe_r": t.best_r, "moved_to_breakeven": t.moved_to_breakeven,
                "stop_from": t.setup.stop_from,
                "hours_held": ((pd.Timestamp(t.exit_t) - pd.Timestamp(t.entry_t))
                               .total_seconds() / 3600.0
                               if t.exit_t is not None else np.nan),
            })
    return pd.DataFrame(rows).sort_values(
        ["pair", "entry_t"]).reset_index(drop=True) if rows else pd.DataFrame()


# ================================== THE REPLAY-LIVE AGREEMENT HARNESS
def replay_through_live(pair: str, start, end,
                        cfg: cc.CraigConfig | None = None,
                        data: dict | None = None) -> dict:
    """The same candles the replay reads, fed to the LIVE engine one closed
    candle at a time.

    THIS IS THE TEST THAT CATCHES DRIFT, and it is here rather than in the
    test file so it can also be run by hand from `step469_craig_live.py`. The
    36x sizing bug happened because a replay and a live runner had separate
    paths and nothing ever put their answers next to each other.

    The working frame is built exactly as `craig_crypto.run_pair` builds it,
    and the equity handed to the engine is worked out exactly as `run_pair`
    works it out: this pair's own $100,000 plus the profit of every trade that
    had already CLOSED at that moment.
    """
    cfg = cfg or live_config(pair)
    data = data or cc.load(pair)
    d = cc.bars(data, cfg.entry_tf)
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    pad_before = pd.Timedelta(
        minutes=cc._TF_MINUTES[cfg.entry_tf] * cfg.context_bars * 3)
    pad_after = pd.Timedelta(hours=cfg.max_hold_hours + 6)
    w = d[(d["t"] >= start - pad_before) & (d["t"] <= end + pad_after)] \
        .reset_index(drop=True)
    if len(w) < 100:
        return {"pair": pair, "engine": Engine(), "trades": []}

    eng = Engine()
    eng._cfg[pair] = cfg
    # the same bound `run_pair` puts on which session opens it takes
    eng.window = (start, end + pd.Timedelta(days=1))
    t = w["t"].to_numpy()

    def equity():
        """THIS PAIR'S OWN $100,000 plus every trade that has already closed
        — `run_pair`'s basis, to the cent."""
        return cfg.account_start + sum(
            p.pnl for p in eng.closed.get(pair, []) if p.exit_t is not None)

    for i in range(len(w)):
        eng.on_bar(pair, w, i, equity)
    return {"pair": pair, "engine": eng,
            "trades": list(eng.closed.get(pair, []))}


if __name__ == "__main__":
    print(__doc__)
