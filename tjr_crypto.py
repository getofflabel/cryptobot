"""
tjr_crypto.py — the same trader's method, pointed at crypto. Not a second bot.

WALLACE'S INSTRUCTION, WHICH IS THE WHOLE SPEC
    "I need you to trade crypto as well."
    "keep his trading methods just throw away the times for crypto thats all."

So everything in tjr_bot.py that is METHOD is imported and used untouched:
the two-candle swing, levels off the 1-hour and 4-hour only, a level taken
out staying pending until a break of structure confirms it, the confirmation
sequence, fair value gaps and equilibrium as the pullback, side must match
the daily bias, stop beyond the sweep, size = 1% of equity / stop distance,
first target at the next pool one timeframe up with half off and the stop to
break even, and the losing-streak rule that tightens the filter instead of
stopping.

Everything in tjr_bot.py that is A CLOCK is absent. Not replaced — absent.
`Instrument` was already built so every time rule defaults to None, so the
crypto instrument simply does not set one. There is no crypto session hour
anywhere in this file, deliberately, because inventing one would be
substituting our clock for his and he did not teach ours.

COSTS ARE CHARGED AND NEVER CONSULTED
    Wallace, twice: "if I told you dont worry about fees then dont worry
    about fees, if you keep worrying you might as well not trade at all.
    guess what, taxes are like 50%."
    The measured bid-ask spread per pair is subtracted from every closed
    trade so the money is honest. NOTHING in this file declines a trade,
    prefers a pair, or moves a threshold because of what trading costs.
    `test_tjr_crypto.py` reads this file's own source and proves it.

HOW IT IS JUDGED
    Not by backtest profit. He does not count historical replay as evidence
    and Wallace agrees — "if tjr doesn't believe in backtest then fuck
    backtesting." What the replay here is FOR is one number he cannot get any
    other way: how many setups a day each pair produces. Trade count is the
    constraint, so that is what `setups_per_day()` reports and it is the only
    thing this file claims.

SAFETY
    This module places no orders. It reads price frames and returns
    decisions, exactly like tjr_bot.py. `live_step` returns an intention that
    a runner may act on; it never sends. No git, no daemon, no live orders.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import json
import os
import statistics

import numpy as np
import pandas as pd

import tjr_bot
from tjr_bot import (Bar, Config, Instrument, Level, NewsCalendar, TjrBot,
                     TrendTracker, completed_before, resample_tf)

REPO = os.path.dirname(os.path.abspath(__file__))


# ============================================================ THE PAIRS
# Wallace named ten in order, and said all 36 US-dollar pairs are available
# "if the structure reads cleanly on more".
#
# AVAX REMOVED 2026-07-25 on his call: "avax is not something that was ever
# good to me". That is his own trading experience and it outranks anything
# here. The week's numbers happened to agree — it had the widest gap between
# its buy and sell price of the ten (0.65% of price) and produced the single
# largest loss of the week, most of which was the cost of trading rather
# than the market moving.
#
# This list is HIS to set. Anything he says has never worked for him comes
# out, and it does not go back in on the strength of a backtest.
PAIRS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD",
         "LINK/USD", "LTC/USD", "ADA/USD", "DOT/USD"]

# Named so the reason survives, and so nothing quietly re-adds them.
#
# DOGE went out knowing exactly what it cost us: it produced three of the
# six crypto trades in the week to 25 July and two of the three winners,
# including the best trade of the week (+1.04% of the account, all three
# targets reached). It comes out anyway. He will not trade it, and a bot
# trading something its owner would not is a bot he cannot judge.
RETIRED_PAIRS = {
    "AVAX/USD": "Wallace, 2026-07-25 — never worked for him",
    "DOGE/USD": "Wallace, 2026-07-25 — would not trade it",
}


def cache_name(pair: str, tf: str) -> str:
    """BTC/USD -> data_alpaca_BTCUSD_5m.parquet. The slash is the one thing
    the stock path never had to think about; it dies here, at the filename,
    and again in alpaca.crypto_close_position, at the URL."""
    return f"{REPO}/data_alpaca_{pair.replace('/', '')}_{tf}.parquet"


# ============================================ THE DAY BOUNDARY: A DECISION
#
# The previous-day and previous-week levels are method — he marks them and
# trades off them. WHERE ONE DAY IS CUT FROM THE NEXT IS NOT METHOD, because
# on the markets he teaches the venue decides it for him and on a 24/7 market
# nothing does.
#
# THE DECISION: UTC MIDNIGHT. Reasons, in order of weight:
#   1. It is the boundary the market itself already uses. Every crypto
#      exchange's daily candle, every funding interval, and every chart a
#      crypto trader opens is cut at 00:00 UTC. The previous day's high is
#      only a draw on liquidity because other people are looking at the same
#      line; a boundary nobody else uses draws a line nobody else defends.
#   2. It needs no timezone rule. The stock instrument cuts at 18:00 US
#      Eastern, which moves twice a year against UTC. A market with no bell
#      should not inherit a daylight-saving rule.
#   3. It is the only choice that makes `has_closing_bell=False` honest: the
#      daily candle is then the literal 24 hours, not a slice of one.
#
# WHAT IT COSTS US, said plainly: a US trader's "yesterday" ends at 20:00
# Eastern, not midnight UTC. On a 24/7 market there is no correct answer
# here, only a stated one.
#
# CONSEQUENCE, also stated: tjr_bot's build_context marks a 15-minute
# continuation pool on days where a marked level was taken in the hour before
# the boundary. On stocks that hour is the pre-market. Here it is just the
# last hour of the previous UTC day, and which days get the extra pool is a
# consequence of choosing this boundary. It is not an invented session.
DAY_BOUNDARY_HOUR_UTC = 0


def to_utc_frame(rows: list) -> pd.DataFrame:
    """Alpaca crypto JSON -> the frame shape tjr_bot walks, with `t` as the
    bar's START in NAIVE UTC.

    This one line IS the boundary decision, made operational: every
    `.normalize()` and every `.floor("240min")` downstream now cuts at UTC.
    The stock path converts to US Eastern in exactly the same place and for
    exactly the same reason."""
    if not rows:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
    d = pd.DataFrame(rows)
    ts = pd.to_datetime(d["t"], utc=True, format="mixed")
    out = pd.DataFrame({
        "t": ts.dt.tz_convert("UTC").dt.tz_localize(None),
        "open": d["o"].astype(float), "high": d["h"].astype(float),
        "low": d["l"].astype(float), "close": d["c"].astype(float)})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


# ================================================ RE-DERIVED, NOT PORTED
#
# "Every threshold comes from the instrument's own recent bars — Bitcoin's
# normal move and SPY's are different numbers permanently."
#
# Four numbers in tjr_bot's Config were measured on SPY. Each is re-measured
# here from the pair's own bars and quotes. Nothing is scaled from the stock
# number; the stock number is quoted only to show what the old value meant.

# Measured 2026-07-25 by derive_all(). Regenerate with:
#     python3 tjr_crypto.py --derive
# and paste the result back. Kept in the file rather than in a side JSON so a
# reader can see the number and the rule it feeds in one place.
DERIVED_PATH = f"{REPO}/step442_derived_thresholds.json"


def measure_spread_pct(cli, pair: str, days: list, per_day: int = 3000) -> float:
    """The real bid-ask spread as a fraction of the mid, MEASURED.

    Sampled across many separate days rather than read off one snapshot,
    because a spread taken on a single quiet evening is not the spread the
    trade pays. Returns the MEDIAN, not the mean: one dislocated quote in a
    sample of thousands should not move the number the account is charged.

    This is the number we CHARGE. It is not consulted anywhere.
    """
    rel = []
    for day in days:
        try:
            q = cli.crypto_quotes(pair, f"{day}T12:00:00Z", f"{day}T12:20:00Z",
                                  limit=per_day)
        except RuntimeError:
            continue
        for r in q.get(pair) or []:
            ap, bp = float(r["ap"]), float(r["bp"])
            mid = (ap + bp) / 2.0
            if mid > 0 and ap > bp:
                rel.append((ap - bp) / mid)
    if not rel:
        return float("nan")
    return float(statistics.median(rel))


def measure_sweep_to_signal(d5: pd.DataFrame, level_minutes=(60, 240),
                            lookback_days: int = 120) -> dict:
    """How long a taken level stays pending before the 5-minute turns.

    tjr_bot ships `sweep_max_age_bars = 12`, and the note says why: round 430
    measured the median sweep-to-signal gap on SPY at 6 five-minute bars, and
    12 is a generous ceiling at twice that. The RULE is "twice the median".
    The 6 is SPY's. This re-measures the median on the pair's own bars and
    applies the same rule, so the crypto ceiling is crypto's number.

    Returns {"n": ..., "median": ..., "ceiling": ...}. Causal throughout:
    levels are marked from completed higher-timeframe bars only and the walk
    is forward.
    """
    if len(d5) == 0:
        return {"n": 0, "median": None, "ceiling": None}
    end = d5["t"].max()
    d5 = d5[d5["t"] >= end - pd.Timedelta(days=lookback_days)].reset_index(drop=True)
    if len(d5) < 500:
        return {"n": 0, "median": None, "ceiling": None}

    # the marked pool, rebuilt once per day from bars completed by that day
    gaps = []
    days = sorted(set(d5["t"].dt.normalize()))
    for day in days:
        hist = d5[d5["t"] < day]
        if len(hist) < 288 * 3:
            continue
        hist = hist[hist["t"] >= day - pd.Timedelta(days=10)]
        pool = []
        for m in level_minutes:
            pool += tjr_bot.swing_levels(hist, m, day, f"{m // 60}h")
        pool = tjr_bot._unswept(pool, hist, day)
        if not pool:
            continue
        session = d5[(d5["t"] >= day) & (d5["t"] < day + pd.Timedelta(days=1))]
        t5 = TrendTracker()
        for r in hist.tail(288 * 3).itertuples():
            t5.update(Bar(r.t, r.open, r.high, r.low, r.close))
        pending = None      # (trade_dir, bars_since)
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


def load_derived() -> dict:
    if os.path.exists(DERIVED_PATH):
        with open(DERIVED_PATH) as f:
            return json.load(f)
    return {}


# ====================================================== THE INSTRUMENT
def crypto_instrument(pair: str, spread_pct: float) -> Instrument:
    """One pair, as an Instrument. EVERY CLOCK FIELD IS LEFT AT None.

    Read the list of what is NOT set here, because that list is the entire
    difference between this and the stock instrument:
        open_t            — there is no open
        manip_end_t       — there is no 09:50
        entry_ideal_end_t — there is no ideal window
        cutoff_t          — there is no 10:30
        flat_t / close_t  — there is no going home flat
        prior_session_window / early_session_window / own_session_window
                          — no London, no Asia, no New York. A market with no
                            bell does not get invented session hours.
        has_closing_bell  — False, so the daily candle is the whole 24 hours

    What IS set is method, and it is identical to the stock instrument:
    levels off the 1-hour and the 4-hour only, the 5-minute as the working
    chart, the 1-minute as the trigger only, the 15-minute as the pool one
    timeframe up.
    """
    return Instrument(
        name=pair,
        round_trip_cost_pct=spread_pct,   # measured, charged, never consulted
        day_boundary_hour=DAY_BOUNDARY_HOUR_UTC,
        has_closing_bell=False,
        level_minutes=(60, 240),
        working_minutes=5,
        trigger_minutes=1,
        continuation_minutes=15,
        target1_minutes=15)


def crypto_config(pair: str, spread_pct: float | None = None,
                  account_start: float = 100_000.0,
                  derived: dict | None = None) -> Config:
    """The method's Config with the four SPY-measured numbers replaced by the
    pair's own, and the two vetoes decided deliberately."""
    derived = derived if derived is not None else load_derived()
    row = (derived.get(pair) or {})
    if spread_pct is None:
        spread_pct = row.get("spread_pct")
        if spread_pct is None:
            raise RuntimeError(
                f"no measured spread for {pair}. Run: python3 tjr_crypto.py "
                f"--derive")
    ceiling = row.get("sweep_max_age_bars") or 12

    return Config(
        instrument=crypto_instrument(pair, spread_pct),
        account_start=account_start,

        # -- RE-DERIVED #1: the stop buffer -----------------------------------
        # HIS rule: clear your broker's spread. He gives 0.5 points on an index
        # quoted near 5,000, which is 0.01% of price, and the stock config
        # carries 0.0001 for exactly that reason. The RULE is "one spread"; the
        # 0.0001 is SPY's spread. Bitcoin's measured spread is roughly 0.1% of
        # price — about thirty times SPY's — so one spread here is a different
        # number, and it is this pair's own.
        stop_buffer_pct_of_price=spread_pct,

        # -- RE-DERIVED #2: how long a taken level stays pending --------------
        # Twice the pair's own measured median sweep-to-signal gap, which is
        # the rule the stock number came from.
        sweep_max_age_bars=ceiling,

        # -- RE-DERIVED #3: buying power --------------------------------------
        # NOT a guess and NOT the stock 4x. Every one of Alpaca's 36 US-dollar
        # crypto pairs reports marginable=false, and the account reports
        # non_marginable_buying_power equal to cash. Crypto here is bought with
        # cash, so the multiple is 1.
        buying_power_multiple=1.0,

        # -- RE-DERIVED #4: a gap is never dragged forward --------------------
        # 288 five-minute bars. The stock config carries the same 288 with the
        # note "1 day of 5m", which on a market that trades 6.5 hours was
        # really 3.7 days. On a 24/7 market 288 is literally one day, which is
        # what the note always said it meant.
        gap_max_age_bars=288,

        # -- THE BOTH-INSTRUMENTS VETO: OFF, deliberately ---------------------
        # See why_no_index_veto() below. This is a decision, not an omission.
        enforce_index_agreement=False,

        # -- THE CLOCK RULE THAT IS A CLOCK RULE ------------------------------
        # "no pre-market rule". There is no pre-market on a 24/7 market, so the
        # carve-out that carries a pre-market sweep across the bell has no bell
        # to carry it across.
        premarket_sweep_carries_forward=False,
    )


def why_no_index_veto() -> str:
    """The both-instruments-agree veto DOES NOT APPLY TO CRYPTO. The reason,
    written down so it is a decision and not an accident.

    WHAT THE VETO IS FOR ON STOCKS. "if the S&P 500 and the NASDAQ on the five
    minute are not aligned, I do not want to be taking a trade." SPY and QQQ
    are two funds holding overlapping baskets of the same US large-cap market
    — QQQ's largest holdings sit inside SPY. When those two charts disagree on
    the 5-minute, they are not telling you two things about two markets. They
    are contradicting each other about ONE market, and a contradiction is
    evidence the read is wrong. That is the whole logic: it is a consistency
    check on a single read, not a correlation filter.

    WHY IT DOES NOT TRANSFER. Bitcoin and Ethereum move together, but they are
    not two views of one thing. They are separate assets with separate supply,
    separate flows and separate news. When BTC turns up on the 5-minute and
    ETH does not, nothing is contradicted — one asset moved and the other did
    not, which is an ordinary relative move and happens constantly. Vetoing
    the BTC trade on it would be discarding a valid read because a different
    asset disagreed.

    AND MECHANICALLY IT HAS NO PARTNER. The stock veto works because there are
    exactly two charts and each is the other's check. Ten pairs have no
    natural partner. Picking one — "ETH checks BTC" — would be a rule he never
    taught, invented by us, to fill a slot that only existed because the S&P
    happens to have a twin.

    SO: each pair is judged on its own chart, and `enforce_index_agreement` is
    False in crypto_config. Every pair runs in its own `run_day` call, so the
    two charts never meet at all.

    WHAT WE GIVE UP, stated: the veto removed real trades on stocks, and some
    of those were losers. Crypto does not get that filter. The losing-streak
    escalation — which tightens the pullback to the midpoint AND a gap after
    two losing weeks — is still on, and it is the filter that remains.
    """
    return why_no_index_veto.__doc__


# ================================== PREVIOUS DAY AND WEEK, RE-DERIVED
#
# tjr_bot.session_levels marks the previous day off a window that is correct
# for a boundary in the EVENING and wrong for a boundary at midnight: it uses
# [prev - 1 day + boundary, prev + boundary). With the stock boundary of
# 18:00 that spans the previous session correctly. With a boundary of 0 it
# lands one day early — it would mark the day BEFORE yesterday and call it
# yesterday. That is precisely the thing the instruction says to re-derive
# rather than port, and it is why porting would have failed silently.
#
# It also marks Asia, London and New York session windows. Those are the
# clock. They are absent here, which leaves the crypto pool thinner than the
# stock pool by three level pairs — and is why the previous WEEK is marked,
# restoring a high-power draw the sessions used to supply.

def crypto_session_levels(d5: pd.DataFrame, day: pd.Timestamp,
                          inst: Instrument) -> list[Level]:
    """Previous UTC day high and low, previous UTC week high and low.

    No sessions. The `formed` stamp on each level is the moment the window
    CLOSED, which is the first moment the level could be known — the same
    causality rule as everywhere else.
    """
    b = pd.Timedelta(hours=inst.day_boundary_hour)
    day = pd.Timestamp(day).normalize()
    week_start = (day - pd.Timedelta(days=int(day.weekday()))).normalize() + b
    windows = [
        ("prev_day", day - pd.Timedelta(days=1) + b, day + b),
        ("prev_week", week_start - pd.Timedelta(days=7), week_start),
    ]
    out: list[Level] = []
    for tag, start, end in windows:
        h, l = tjr_bot._window_extremes(d5, start, end)
        if h is not None:
            out.append(Level(h, +1, tag, end))
            out.append(Level(l, -1, tag, end))
    return out


_ORIGINAL_SESSION_LEVELS = tjr_bot.session_levels
_INSTALLED = False


def install() -> None:
    """Teach tjr_bot to mark levels the crypto way WITHOUT changing what it
    does for stocks.

    WHY A SHIM AND NOT AN EDIT. tjr_bot.py is being edited by someone else on
    exit logic right now. This adds one dispatch in front of one function and
    leaves the file alone. The dispatch branches on `inst.open_t is None`,
    which is true only for a market with no bell, so the index path takes the
    original function unchanged. `test_tjr_crypto.py` proves the stock levels
    are byte-identical with the shim installed. Fold it into tjr_bot.py when
    that file is free.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    def dispatch(d5, day, inst=tjr_bot.US_INDEX_ETF):
        if inst.open_t is not None:
            return _ORIGINAL_SESSION_LEVELS(d5, day, inst)
        return crypto_session_levels(d5, day, inst)

    tjr_bot.session_levels = dispatch
    # Higher time frames hold higher power, and the previous week is the
    # highest-power draw on the board. Without a rank it would score 0 and
    # lose to a 1-hour swing when both are taken on the same bar.
    tjr_bot.LEVEL_RANK.setdefault("prev_week", 4)
    _INSTALLED = True


install()


# ================================================ DATA: FETCH AND CACHE
def fetch(pairs=None, start_5m: str = "2025-11-01", start_1m: str = "2026-03-01",
          verbose: bool = True) -> None:
    """Download and cache 5-minute and 1-minute bars. Read-only against the
    venue; writes parquet next to the stock caches."""
    import alpaca
    cli = alpaca.from_env()
    if cli is None:
        raise RuntimeError("ALPACA keys are not in .env")
    for pair in (pairs or PAIRS):
        for tf, code, start in (("5m", "5Min", start_5m), ("1m", "1Min", start_1m)):
            rows = cli.crypto_bars(pair, code, start=start).get(pair) or []
            d = to_utc_frame(rows)
            d.to_parquet(cache_name(pair, tf))
            if verbose:
                span = f"{d['t'].min()} .. {d['t'].max()}" if len(d) else "empty"
                print(f"  {pair:10s} {tf}  {len(d):>7,} bars   {span}")


def load(pair: str) -> dict:
    """{"5m": frame, "1m": frame}, `t` in naive UTC."""
    return {tf: pd.read_parquet(cache_name(pair, tf)) for tf in ("5m", "1m")}


def days_in(data: dict, start=None, end=None) -> list:
    """Every UTC day with 1-minute bars. No holidays, no weekends, no gaps —
    that IS the point of the market."""
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


# ======================================================= THE REPLAY
#
# ONE PAIR PER run_day CALL. tjr_bot.run_day takes at most one trade across
# every symbol it is handed, which is right for two charts of one market and
# wrong for ten separate assets — handing it all ten would cap the whole book
# at one trade a day and let whichever pair happened to fire first silence the
# other nine. Each pair gets its own call, its own account clone, and its own
# losing-streak state. That is also what makes the index veto structurally
# absent rather than merely switched off.

def _reword(why: str) -> str:
    """tjr_bot's stand-down sentences end in "before 10:30" because that is
    hardcoded English in `_why_no_trade`, not because a cut-off ran. No
    cut-off exists here — `past_cutoff` returns False at every hour, and the
    entries in the replay land all over the clock, which is a test. This only
    fixes the sentence so a reader is not told about a rule that was never
    applied."""
    return why.replace(" before 10:30", " at all that day")


def run_pair(pair: str, start=None, end=None, cfg: Config | None = None,
             data: dict | None = None, verbose: bool = False) -> dict:
    """Walk one pair, day by day, strictly forward. Returns the trades, the
    stand-down reasons, and the day count.

    ONE LIMITATION, STATED RATHER THAN HIDDEN. tjr_bot.run_day walks a single
    day and closes anything still open when that day's bars run out, labelling
    it "flat by the close". On a 24/7 market there is no close, and the LIVE
    path does not do this — `manage_step` on the crypto instrument returns
    "hold" at 23:55 and the position runs to its stop or its targets across
    the boundary. So a replay outcome of "flat by the close" means only that
    the UTC day ended, and the replay's outcomes are truncated versions of
    what would actually have happened.

    It does not touch the one number this replay is for. A setup is counted
    when the entry fires, which happens before any of this.
    """
    cfg = cfg or crypto_config(pair)
    data = data or load(pair)
    news = NewsCalendar(rules=False)      # no US news-day blocks. Crypto has no CPI.
    bot = TjrBot(cfg, news)
    days = days_in(data, start, end)
    trades, reasons, skipped = [], {}, 0
    for day in days:
        day = pd.Timestamp(day)
        win = slice_for(data, day, cfg)
        if len(win["1m"][(win["1m"]["t"] >= day) &
                         (win["1m"]["t"] < day + pd.Timedelta(days=1))]) == 0:
            skipped += 1
            continue
        res = bot.run_day({pair: win}, day)
        if res["trade"] is not None:
            trades.append(res["trade"])
        for why in res["stand_down"].values():
            why = _reword(why)
            reasons[why] = reasons.get(why, 0) + 1
        if verbose and res["trade"] is not None:
            tr = res["trade"]
            side = "long" if tr.direction > 0 else "short"
            print(f"  {day:%Y-%m-%d} {pair:9s} {side:5s} off the {tr.level_tf} "
                  f"level at {tr.level_price:,.4f} -> {tr.outcome}")
    return {"pair": pair, "days": len(days) - skipped, "trades": trades,
            "reasons": reasons, "account": bot.account}


def setups_per_day(pairs=None, start=None, end=None, verbose: bool = True) -> dict:
    """THE NUMBER THIS EXERCISE EXISTS TO PRODUCE.

    Trade count is the constraint, so what we most need to know about crypto
    is how many setups a day it actually produces, per pair. This reports it
    and nothing else — no profit claim, because he does not count replay as
    evidence and neither do we.

    A "setup" here is a completed sequence that reached an entry: a marked
    level pushed through, a 5-minute confirmation, a pullback into the
    midpoint or a fair value gap, and a 1-minute trigger with the trade. It
    is one per pair per day at most, which is the bot's own rule.
    """
    out, derived = {}, load_derived()
    for pair in (pairs or PAIRS):
        try:
            cfg = crypto_config(pair, derived=derived)
            r = run_pair(pair, start, end, cfg=cfg)
        except FileNotFoundError:
            if verbose:
                print(f"  {pair:10s}  no cached bars — run --fetch")
            continue
        n, days = len(r["trades"]), max(r["days"], 1)
        longs = sum(1 for t in r["trades"] if t.direction > 0)
        out[pair] = {
            "days": r["days"], "setups": n, "per_day": round(n / days, 3),
            "one_every_n_days": round(days / n, 1) if n else None,
            "long": longs, "short": n - longs,
            "spread_pct_charged": round(100 * cfg.instrument.round_trip_cost_pct, 4),
            "sweep_max_age_bars": cfg.sweep_max_age_bars,
            "top_stand_down": sorted(r["reasons"].items(),
                                     key=lambda kv: -kv[1])[:3],
        }
        if verbose:
            o = out[pair]
            print(f"  {pair:10s} {o['days']:>4} days   {n:>3} setups   "
                  f"{o['per_day']:.3f}/day   {longs} long / {n - longs} short")
    return out


# ============================================================ LIVE
#
# THE CRYPTO live_step. tjr_bot.live_step refuses unless Alpaca's /v2/clock
# says the stock market is open — correct there, wrong here, and the reason it
# cannot simply be reused. Verified 2026-07-25 rather than assumed: the clock
# reported is_open false while the crypto bars endpoint returned a full 24
# hours for that same Saturday and for the Sunday after it.

def live_step(pair: str, data: dict, now: pd.Timestamp, account: float,
              buying_power: float | None = None, cfg: Config | None = None,
              week_pnl: dict | None = None) -> dict:
    """The one call a live crypto runner makes. Returns an intention, never an
    order.

    data         : {"5m": frame, "1m": frame} with `t` in NAIVE UTC, ending at
                   the last CLOSED 1-minute bar
    now          : the CLOSE time of that bar, naive UTC
    account      : the broker's own equity. Read it, do not compute it.
    buying_power : the broker's own non_marginable_buying_power. Crypto is
                   cash-only here; omit it and 1x equity is assumed.

    NO CLOCK ARGUMENT AND NO CLOCK CHECK. There is no session to be outside
    of. That is the entire difference from the stock version.

    Returns {"action": "wait" | "enter" | "cannot_send", ...}.
    """
    cfg = cfg or crypto_config(pair)
    if not isinstance(now, pd.Timestamp):
        return {"action": "wait", "reason": "the timestamp is unreadable"}

    day = now.normalize()
    bot = TjrBot(cfg, NewsCalendar(rules=False))
    bot.account = float(account)
    bot.buying_power = None if buying_power is None else float(buying_power)
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

    out = {"action": "enter", "symbol": pair, "direction": tr.direction,
           "side": "buy" if tr.direction > 0 else "sell",
           "reference_price": tr.entry, "stop": tr.stop, "qty": tr.shares,
           "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
           "partial_fraction": cfg.partial_fraction,
           "stop_anchor": tr.stop_anchor, "level_tf": tr.level_tf,
           "level_price": tr.level_price, "confirmed_by": tr.confirm_kind,
           "pullback_into": tr.pullback_kind, "notional": tr.notional,
           "risk_dollars": tr.risk_dollars, "risk_wanted": tr.risk_wanted,
           "clamped": tr.clamped, "escalated": res["escalated"]}

    # THE VENUE CANNOT SHORT, AND THIS SAYS SO RATHER THAN FAILING QUIETLY.
    # All 36 US-dollar pairs report shortable=false and marginable=false. This
    # is NOT a cost filter and NOT a method change — the method still produced
    # the short and it is reported in full above. What is refused is the
    # SENDING of it, because a sell with no position is an error here, not a
    # short, and letting it through would show a filled trade where nothing
    # happened.
    if tr.direction < 0:
        out["action"] = "cannot_send"
        out["reason"] = ("the method wants a short and Alpaca crypto is "
                         "long-only: every US-dollar pair reports "
                         "shortable=false, marginable=false")
    return out


# ====================================================== DERIVATION RUN
def derive_all(pairs=None, verbose: bool = True) -> dict:
    """Measure every re-derived threshold from each pair's own bars and
    quotes, and write them down. Read-only against the venue."""
    import alpaca
    cli = alpaca.from_env()
    pairs = pairs or PAIRS
    # twelve separate days spread over five months, so the spread is not one
    # evening's snapshot
    base = dt.date(2026, 7, 20)
    days = [str(base - dt.timedelta(days=12 * k)) for k in range(12)]
    out = {}
    for pair in pairs:
        spread = measure_spread_pct(cli, pair, days)
        row = {"spread_pct": None if spread != spread else round(spread, 8),
               "spread_pct_of_price": None if spread != spread else round(100 * spread, 4)}
        try:
            d5 = pd.read_parquet(cache_name(pair, "5m"))
            m = measure_sweep_to_signal(d5)
            row.update({"sweep_median_bars": m["median"],
                        "sweep_max_age_bars": m["ceiling"], "sweep_n": m["n"]})
        except FileNotFoundError:
            row.update({"sweep_median_bars": None, "sweep_max_age_bars": None,
                        "sweep_n": 0})
        out[pair] = row
        if verbose:
            print(f"  {pair:10s} spread {row['spread_pct_of_price']}% of price   "
                  f"sweep-to-signal median {row['sweep_median_bars']} bars   "
                  f"ceiling {row['sweep_max_age_bars']} (n={row['sweep_n']})")
    with open(DERIVED_PATH, "w") as f:
        json.dump(out, f, indent=2)
    return out


def main(argv):
    if "--fetch" in argv:
        print("fetching crypto bars")
        fetch()
        return
    if "--derive" in argv:
        print("re-deriving every threshold from each pair's own bars and quotes")
        derive_all()
        return
    start = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else None
    end = argv[2] if len(argv) > 2 and not argv[2].startswith("-") else None
    print("=" * 78)
    print("setups per day, per pair — the number trade count is constrained by")
    print("=" * 78)
    out = setups_per_day(start=start, end=end)
    print()
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    import sys
    main(sys.argv)
