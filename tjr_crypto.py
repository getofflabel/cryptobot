"""
tjr_crypto.py — the same trader's method, pointed at crypto. Not a second bot.

WALLACE'S INSTRUCTION, WHICH IS THE WHOLE SPEC
    "I need you to trade crypto as well."
    "keep his trading methods just throw away the times for crypto thats all."

So everything in tjr_bot.py that is METHOD is imported and used untouched:
the two-candle swing, levels off the 1-hour and 4-hour only, a level taken
out staying pending until a break of structure confirms it, the confirmation
sequence, fair value gaps and equilibrium as the pullback, side must match
the daily bias, stop beyond the sweep, his set size drawn against the DAY's
risk budget, first target at the next pool one timeframe up with half off and
the stop to break even, and the losing-streak rule that tightens the filter
instead of stopping.

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
PAIRS = ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOT/USD"]

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
    # Wallace, 2026-07-26: "fuck link and fuck ada and ltc". Measured on
    # 1-26 July 2026, these three carried 75% of the whole crypto loss:
    #   LINK  34 trades, 21% won, -$21,261
    #   ADA   27 trades, 30% won, -$19,142
    #   LTC   38 trades, 29% won, -$17,079
    # -$57,482 of a -$76,566 month, from three of eight coins. They are also
    # the three worst win rates in the book. Note the whole book was measured
    # with stops far too tight for crypto, so this is not proof the coins are
    # untradeable — it is his call, and the reason it is an easy one.
    "LINK/USD": "Wallace, 2026-07-26 — worst win rate in the book, 21%",
    "ADA/USD":  "Wallace, 2026-07-26 — 30% won, second-largest loser",
    "LTC/USD":  "Wallace, 2026-07-26 — 29% won, third-largest loser",
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


# ==================================== STEP466: THE DAY MAY MARK, NEVER CUT
#
# WALLACE, 2026-07-26, verbatim and this is the whole instruction:
#     "crypto runs 24/7, then let it run 24/7. dont cut shit."
#
# The session clock was already gone — no 09:50, no 10:30, `past_cutoff`
# returns False at every hour. What survived the strip was the boundary above,
# and it was doing two very different jobs under one name:
#
#   A LINE ON THE CHART, which is fine. "Yesterday's high" needs a yesterday,
#   and every crypto chart in the world cuts it at 00:00 UTC, so the level is
#   a real draw on liquidity because other people defend it. Nothing about a
#   marked line closes a position.
#
#   A BELL, which is not fine and is what he told us to stop. `tjr_bot.run_day`
#   walks ONE day's bars and force-flats anything still open when they run
#   out. On a market with a real close that is the close. Here it was an
#   imaginary bell: every trade that needed longer than the rest of a UTC day
#   to reach its target was booked at whatever it happened to be worth at
#   midnight. The asymmetry is the damage — a loser always has time to reach
#   its stop because the stop is close, a winner needs room and time, so the
#   bell cut the winners and left the losers whole.
#
# WHAT CHANGED HERE: the bell, and only the bell. `_force_flat` is shimmed so
# that a market with no close closes nothing, and `run_pair` carries the open
# position forward over the following days' bars until it reaches its stop or
# its targets — exactly what `manage_step` already does on the live path,
# which never had this bug. The marked lines, the sweep, the break of
# structure, equilibrium, the fair value gaps and the stop at chart structure
# are all untouched.
#
# WHAT DID NOT CHANGE, AND IS REPORTED RATHER THAN FIXED: see
# `where_the_invented_day_still_bites()` below. Picking a smarter hour is
# still picking, so no hour was picked.


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

        # -- SMT DIVERGENCE: OFF, AND HE IS THE ONE WHO SAYS SO ---------------
        # step456 put SMT divergence into tjr_bot.py. It does not come here,
        # and the reason is his own words rather than an architectural one.
        # 044: "unfortunately Forex crypto guys — well crypto, sometimes you
        # can use this with BTC and ETH but I WOULDN'T NECESSARILY RECOMMEND
        # IT... I haven't back tested it as much as I have with these
        # indexes." The five-hour beginner guide is blunter: "if you guys are
        # trading anything besides the S&P 500 in NASDAQ this is not going to
        # apply to you... THIS ONLY APPLIES TO INDEXES."
        #
        # It is also structurally impossible here and that is worth saying
        # twice: `run_pair` hands `run_day` ONE pair, and a divergence needs
        # exactly two charts, so `TjrBot._smt` returns None before the switch
        # is ever consulted. Pinning it False is belt and braces, and it means
        # nobody can turn it on for crypto by editing one line somewhere else.
        #
        # The same argument that retired the index veto here applies word for
        # word — see why_no_index_veto(). Bitcoin and Ethereum are not two
        # views of one market, and picking a partner for each pair would be a
        # rule of ours filling a slot that only exists because the S&P happens
        # to have a twin.
        smt_enabled=False,
        smt_picks_the_instrument=False,
        smt_in_confirmation_menu=False,
        smt_in_continuation_menu_after_2b=False,

        # -- THE 79% EXTENSION AND THE 1-MINUTE GAP: OFF, as everywhere -------
        # Neither is a clock rule and neither is index-specific, so unlike SMT
        # there is no reason of his to keep them out. They ship off because
        # EVERY step456 switch ships off — the before/after has to be able to
        # produce both halves — and turning them on for crypto is a config
        # change here, not a code change.
        extension_79_enabled=False,
        trigger_menu_1m_gap_inversion=False,

        # -- STEP 2B: OFF, AND IT IS A CLOCK RULE -----------------------------
        # 112's 2B exists because "when New York market opens, new money is
        # coming into the market". There is no open on a 24/7 market, so there
        # is no new money arriving at a time, and there is nothing for the
        # gate to hang on. It is also inert here anyway: it only fires off the
        # pre-market carry-forward, which is already False below.
        require_fresh_5m_sweep_after_open=False,
        invalidate_on_close_beyond_continuation=False,

        # -- THE CLOCK RULE THAT IS A CLOCK RULE ------------------------------
        # "no pre-market rule". There is no pre-market on a 24/7 market, so the
        # carve-out that carries a pre-market sweep across the bell has no bell
        # to carry it across.
        premarket_sweep_carries_forward=False,
    )


def where_the_invented_day_still_bites() -> str:
    """EVERY PLACE THE INVENTED DAY IS STILL LOAD-BEARING, enumerated so the
    list is a decision and not an oversight. Step466 removed exactly one of
    them — the bell — because that is the one Wallace named.

    1. THE BELL. FIXED. `run_day` slices the bars to [day, day+24h) and
       force-flats anything still open at the end. Every crypto trade needing
       longer than the rest of a UTC day to reach its target was booked at
       whatever it was worth at midnight, and the asymmetry ran one way: a
       loser always had time to reach its stop, a winner needed room. See
       `install()` and `run_pair`. Measured in step466_truncation.py.

    2. THE DAILY BIAS. NOT FIXED, AND NOT PATCHED EITHER. The bias is method —
       "can we go against daily bias no" — but the twenty-four hours it is
       measured over are not. `tjr_bot.daily_bars` cuts a crypto daily candle
       at `t.dt.normalize()`, plain UTC midnight, and note that it does NOT
       consult `day_boundary_hour` at all when there is no closing bell, so
       the constant above is not even the thing setting it. `build_context`
       reads the trend off that stack once, at 00:00, and then forbids the
       opposite side for the next 24 hours.

       MEASURED, step466_bias_boundary.py, across 11,443 pair-days: the daily
       trend read agrees with UTC midnight's only 83.5% of the time, all 24
       possible boundaries agree on just 50.6% of days, and ON 49.4% OF DAYS
       TWO EQUALLY ARBITRARY BOUNDARIES WOULD TAKE OPPOSITE SIDES. On roughly
       half of all days the side this bot is permitted to trade is decided by
       which hour we picked, not by the market.

       NOTHING IS CHANGED ON THE STRENGTH OF THAT. Picking a smarter hour is
       still picking, and a rule of his is not deleted because a measurement
       of ours is uncomfortable. It is reported to Wallace and it is his call.

    3. THE MARKED POOL IS FROZEN FOR 24 HOURS. `ctx.levels` is built once, in
       `build_context`, from bars completed before the boundary, and is never
       refreshed inside the day. On a 6.5-hour session a level is at worst
       6.5 hours stale. Here a 1-hour swing that forms at 00:30 UTC is not on
       the board until 00:00 the next day. FIXING IT MEANS EDITING
       tjr_bot.py — the refresh would have to happen inside `run_day`'s walk —
       so it is reported, not done.

    4. THE SEQUENCE RESETS AT MIDNIGHT. `run_day` builds a fresh `SymbolDay`
       per day with an empty `SeqState`, so a level swept at 23:40 that is
       waiting for its 5-minute break of structure is thrown away at 00:00 and
       has to form again from nothing. The 5-minute trend and gap book restart
       from a 3-day seed and the 1-minute trend from a 90-minute one. THIS
       HITS THE LIVE PATH TOO: `live_step` calls `run_day` with
       `day=now.normalize()`, so at 00:05 UTC the live bot is looking at five
       minutes of chart. Same reason as 3 — it lives in `run_day` — so it is
       reported, not done.

    5. WEEKS. The losing-streak escalation anchors weeks at Monday 00:00
       (`refresh_escalation`), and `crypto_session_levels` marks the previous
       week off the same anchor. A market with no days has no weeks either.
       The previous-week HIGH AND LOW are marked lines and stay; the
       escalation clock is the same class of invention as the day and is
       flagged here rather than moved.

    6. AGE MEASURED IN DAYS. `level_lookback_days=10`, `dir_lookback_days=90`,
       `seed_days=3`, `gap_max_age_bars=288`, `regime_ma_days=50`. Four of
       these five are ROLLING DURATIONS — `day - Timedelta(days=N)` — which on
       a 24/7 market is an honest N x 24 hours and not a cut at all; the only
       artefact is that the window is re-cut once a day instead of
       continuously, so a level ages out in 24-hour steps. `regime_ma_days` is
       the exception: it averages 50 of the arbitrary daily candles from 2.

    7. THE CANDLE GRID. `candle_anchor_hour` is left at its default 0, so the
       1-hour and 4-hour candles the levels are marked off hang from midnight
       UTC — the 4-hour grid is 00/04/08/12/16/20. The stock instrument hangs
       its grid from 17:00 Eastern because that is the futures open and it is
       the grid his own 4-hour chart is drawn on. Crypto has no such anchor,
       so this is the same unforced choice as the day boundary, one timeframe
       down. Stated, not moved.

    8. THE PREVIOUS DAY'S HIGH AND LOW. Left exactly as they are, and this one
       is deliberate rather than deferred. It is a MARKED LINE, not a bell —
       nothing about it closes a position — and every crypto exchange's daily
       candle, every funding interval and every chart a crypto trader opens is
       cut at 00:00 UTC, so the line is defended by other people's orders.
       That is the whole reason a previous-day level is a draw on liquidity.

    9. THIS FILE'S OWN `measure_sweep_to_signal`, which sets
       `sweep_max_age_bars`, rebuilds the level pool once per UTC day and
       re-seeds its trend tracker at each boundary, so a sweep that crosses
       midnight is dropped from the median. It biases the measured ceiling
       slightly short. Small, and named.
    """
    return where_the_invented_day_still_bites.__doc__


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
_ORIGINAL_FORCE_FLAT = tjr_bot.TjrBot._force_flat
_INSTALLED = False


def _force_flat_only_where_there_is_a_close(self, tr, index, budget=None):
    """A market with no close closes nothing. THE STEP466 CHANGE.

    `TjrBot.run_day` walks one day's bars and calls this on anything still
    open when they run out. On SPY, on GLD and on forex — every one of which
    sets `open_t` — that is a real bell and the original runs unchanged. On
    crypto `open_t` is None, there is no bell, and this returns without
    touching the trade: it stays open, with its ladder state, its part-filled
    targets and its stop exactly where they were, and `run_pair` walks it
    forward over the following days until it reaches its stop or its targets.

    Leaving `tr.outcome` empty is what makes that safe. `run_day` adds
    `tr.pnl` to the account right after this, and an open trade's pnl is 0.0,
    so nothing is booked for a position that has not closed. `run_pair` books
    it at the minute it actually closes, which is also what keeps the account
    causal: money that has not been made yet cannot size tomorrow's trade.
    """
    if self.cfg.instrument.open_t is None:
        return
    return _ORIGINAL_FORCE_FLAT(self, tr, index, budget)


def install() -> None:
    """Teach tjr_bot to mark levels the crypto way, and to stop closing crypto
    positions at a bell it does not have, WITHOUT changing what it does for
    stocks.

    WHY A SHIM AND NOT AN EDIT. tjr_bot.py is being edited by someone else on
    sizing right now. This adds one dispatch in front of one function and one
    guard in front of another, and leaves the file alone. Both branch on
    `inst.open_t is None`, which is true only for a market with no bell, so
    the index path, the gold path and the forex path all take the original
    code unchanged. `test_tjr_crypto.py` proves the stock levels are
    byte-identical with the shim installed and that the stock force-flat still
    fires. Fold both into tjr_bot.py when that file is free.
    """
    global _INSTALLED
    if _INSTALLED:
        return

    def dispatch(d5, day, inst=tjr_bot.US_INDEX_ETF):
        if inst.open_t is not None:
            return _ORIGINAL_SESSION_LEVELS(d5, day, inst)
        return crypto_session_levels(d5, day, inst)

    tjr_bot.session_levels = dispatch
    tjr_bot.TjrBot._force_flat = _force_flat_only_where_there_is_a_close
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
# ONE PAIR PER run_day CALL. run_day now shares ONE DAY'S RISK BUDGET across
# every symbol it is handed, which is right for two charts of one market —
# they are two views of the same read and one budget is what he spends on the
# day. It is wrong for ten separate assets: handing it all ten would make the
# first pair to fire spend budget the other nine then could not draw on, so
# whichever pair happened to move first would silence the rest. Each pair gets
# its own call, its own account clone, its own day budget and its own
# losing-streak state. That is also what makes the index veto structurally
# absent rather than merely switched off.
#
# STATED PLAINLY, because it is a real gap: ten pairs each running their own
# day budget is ten days' budgets, not one. He trades a handful of markets and
# never says what happens across ten. Sizing the book as a whole is a question
# for the desk, not for this file, and it is not answered here.

def _reword(why: str) -> str:
    """tjr_bot's stand-down sentences end in "before 10:30" because that is
    hardcoded English in `_why_no_trade`, not because a cut-off ran. No
    cut-off exists here — `past_cutoff` returns False at every hour, and the
    entries in the replay land all over the clock, which is a test. This only
    fixes the sentence so a reader is not told about a rule that was never
    applied."""
    return why.replace(" before 10:30", " at all that day")


RAN_OUT = "still open when the record ran out"


def _one_minute_trend(d1: pd.DataFrame, day: pd.Timestamp) -> TrendTracker:
    """The 1-minute trend EXACTLY as `SymbolDay` had it at the end of `day`.

    Reconstructed rather than reached into, because `run_day` does not hand
    the legs back. `SymbolDay.__init__` seeds `t1` on the 90 minutes before
    the day starts and `on_1m` then feeds it every 1-minute bar of the day
    unconditionally, so replaying those same bars into a fresh tracker gives
    the same object. That matters: the runner comes off on this chart's break
    of structure, and a carried position must keep reading the same trend it
    was being managed against a minute earlier rather than a fresh one.
    """
    t1 = TrendTracker()
    lo = day - pd.Timedelta(hours=1, minutes=30)
    hi = day + pd.Timedelta(days=1)
    for r in d1[(d1["t"] >= lo) & (d1["t"] < hi)].itertuples():
        t1.update(Bar(r.t, r.open, r.high, r.low, r.close))
    return t1


class _Carry:
    """One day's still-open positions and the 1-minute trend they are managed
    against, carried over the boundary together.

    Nothing here is a new rule. `bot._manage` is the same call `run_day` makes
    on every bar inside a day — his ladder, the stop to break even after
    target one, the runner off the 1-minute break of structure. The only thing
    that changed is that the bars keep coming.
    """

    def __init__(self, trades: list, t1: TrendTracker):
        self.trades, self.t1 = list(trades), t1

    def advance(self, bot: TjrBot, bars: pd.DataFrame) -> list:
        """Walk these bars forward. Returns whatever closed on them."""
        closed = []
        for r in bars.itertuples():
            if not self.trades:
                break
            b = Bar(r.t, r.open, r.high, r.low, r.close)
            bos1 = self.t1.update(b)
            for tr in list(self.trades):
                bot._manage(tr, b, None, bos1)
                if tr.outcome:
                    self.trades.remove(tr)
                    closed.append(tr)
        return closed


def _weeks(closed: list) -> dict:
    """The week ledger the losing-streak rule reads, built only from trades
    that have actually CLOSED. Same Monday anchor `run_day` uses."""
    out: dict = {}
    for tr in closed:
        d = pd.Timestamp(tr.day)
        wk = (d - pd.Timedelta(days=d.weekday())).normalize()
        out[wk] = out.get(wk, 0.0) + tr.pnl
    return out


def run_pair(pair: str, start=None, end=None, cfg: Config | None = None,
             data: dict | None = None, verbose: bool = False,
             carry_past_the_boundary: bool = True) -> dict:
    """Walk one pair, day by day, strictly forward. Returns the trades, the
    stand-down reasons, and the day count.

    THE LIMITATION THIS USED TO CARRY IS GONE (step466). It used to say:
    `run_day` closes anything still open when a day's bars run out, so a
    crypto outcome of "flat by the close" meant only that the UTC day ended
    and the replay's outcomes were truncated versions of what happened. That
    was true, it was the biggest thing wrong with this book, and Wallace's
    instruction was "crypto runs 24/7, then let it run 24/7. dont cut shit."

    Now the position runs. `install()` stops `_force_flat` firing on a market
    with no close, and the loop below walks each still-open trade through the
    following days' bars with `bot._manage` — the same management call, the
    same ladder, the same stop — until it reaches its stop or its targets.
    Only the last positions still open when the DATA runs out are closed, and
    they are labelled `RAN_OUT` so nobody mistakes the end of the record for
    the end of a day.

    THE ACCOUNT STAYS CAUSAL. A day sizes off the money already in the
    account, and a position that is still running has made nothing yet, so its
    profit is booked at the minute it actually closes and not before. The
    losing-streak ledger reads the same closed trades. Nothing a day does can
    see money a later day makes.

    `carry_past_the_boundary=False` restores the old imaginary bell exactly,
    which is what the before/after in step466 is measured against.
    """
    cfg = cfg or crypto_config(pair)
    data = data or load(pair)
    news = NewsCalendar(rules=False)      # no US news-day blocks. Crypto has no CPI.
    bot = TjrBot(cfg, news)
    days = days_in(data, start, end)
    d1_all = data["1m"]
    trades, reasons, skipped = [], {}, 0
    carries: list[_Carry] = []
    closed: list = []
    equity = cfg.account_start
    last_row = None

    for day in days:
        day = pd.Timestamp(day)
        session1 = d1_all[(d1_all["t"] >= day) &
                          (d1_all["t"] < day + pd.Timedelta(days=1))]
        if len(session1) == 0:
            skipped += 1
            continue          # no price, so nothing moves and nothing closes
        last_row = session1.iloc[-1]
        win = slice_for(data, day, cfg)

        # the account this day is allowed to size from, and the week ledger the
        # losing-streak rule reads: closed trades only, all of them from before
        # today. This is the whole causality guarantee of the carry.
        bot.account = equity
        bot.week_pnl = _weeks(closed)

        res = bot.run_day({pair: win}, day)
        trades += res["trades"]
        for why in res["stand_down"].values():
            why = _reword(why)
            reasons[why] = reasons.get(why, 0) + 1

        # 1) positions carried in from earlier days, walked through today
        for c in list(carries):
            closed += c.advance(bot, session1)
            if not c.trades:
                carries.remove(c)

        # 2) today's own trades. Whatever `run_day` finished stays finished;
        #    whatever it left open is carried rather than cut.
        closed += [t for t in res["trades"] if t.outcome]
        still_open = [t for t in res["trades"] if not t.outcome]
        if still_open:
            if carry_past_the_boundary:
                carries.append(_Carry(still_open, _one_minute_trend(d1_all, day)))
            else:
                idx = {r.t: Bar(r.t, r.open, r.high, r.low, r.close)
                       for r in session1.itertuples()}
                for tr in still_open:
                    _ORIGINAL_FORCE_FLAT(bot, tr, idx, None)
                closed += still_open

        equity = cfg.account_start + sum(t.pnl for t in closed)
        if verbose:
            for tr in res["trades"]:
                side = "long" if tr.direction > 0 else "short"
                print(f"  {day:%Y-%m-%d} {pair:9s} {side:5s} off the "
                      f"{tr.level_tf} level at {tr.level_price:,.4f} -> "
                      f"{tr.outcome or 'still running'}")

    # the RECORD ran out, which is not a bell and is not called one
    for c in carries:
        for tr in c.trades:
            if last_row is None:
                continue
            bot._close(tr, float(last_row["close"]), last_row["t"], RAN_OUT, None)
            closed.append(tr)

    # the equity curve, in the order the money actually landed
    closed.sort(key=lambda t: pd.Timestamp(t.exit_t))
    acct = cfg.account_start
    for tr in closed:
        acct += tr.pnl
        tr.account_after = acct

    crossed = sum(1 for t in trades
                  if t.entry_t is not None and t.exit_t is not None
                  and pd.Timestamp(t.exit_t).normalize()
                  > pd.Timestamp(t.entry_t).normalize())
    return {"pair": pair, "days": len(days) - skipped, "trades": trades,
            "reasons": reasons, "account": acct,
            "crossed_the_boundary": crossed}


def setups_per_day(pairs=None, start=None, end=None, verbose: bool = True) -> dict:
    """THE NUMBER THIS EXERCISE EXISTS TO PRODUCE.

    Trade count is the constraint, so what we most need to know about crypto
    is how many setups a day it actually produces, per pair. This reports it
    and nothing else — no profit claim, because he does not count replay as
    evidence and neither do we.

    A "setup" here is a completed sequence that reached an entry: a marked
    level pushed through, a 5-minute confirmation, a pullback into the
    midpoint or a fair value gap, and a 1-minute trigger with the trade.

    IT IS NO LONGER CAPPED AT ONE PER PAIR PER DAY. Boot Camp 2.0 Day 8 and
    Day 9 make more than one trade a day the method rather than an edge case,
    and what ends the day is the risk budget, not a count — "we took three
    trades today" (Day 9), four on Day 12. So a pair can now show more than
    one setup on a day and this number can exceed 1.000.
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
    # THE TRADE THAT MATTERS IS THE ONE THAT FIRED ON THIS MINUTE, not the
    # first of the day. Since the day budget went in, a pair can take more
    # than one, and reading res["trade"] would silently ignore every one
    # after the first.
    fired = [t for t in res["trades"]
             if t.entry_t == now - pd.Timedelta(minutes=1)]
    if not fired:
        if not res["trades"]:
            why = "; ".join(f"{k}: {v}" for k, v in res["stand_down"].items())
            return {"action": "wait", "escalated": res["escalated"],
                    "reason": why or "the sequence has not completed yet"}
        last = res["trades"][-1]
        return {"action": "wait",
                "reason": f"the entry fired at {last.entry_t}, already handled"}
    tr = fired[0]

    out = {"action": "enter", "symbol": pair, "direction": tr.direction,
           "side": "buy" if tr.direction > 0 else "sell",
           "reference_price": tr.entry, "stop": tr.stop, "qty": tr.shares,
           "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
           "target_fractions": tjr_bot.target_fractions(len(tr.targets), cfg),
           "runner_fraction": tjr_bot.runner_fraction(len(tr.targets), cfg),
           "partial_fraction": cfg.partial_fraction,
           "budget_share": tr.budget_share,
           "second_setup_expected": tr.second_setup_expected,
           "size_basis": tr.size_basis,
           # the exact three inputs the size was worked out from — see the
           # note on the same three in tjr_bot.live_step
           "sizing_account": tr.sizing_account,
           "buying_power_used": tr.sizing_buying_power,
           "outer_allowance": tr.sizing_outer_allowance,
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
