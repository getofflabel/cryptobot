"""
tjr_gold.py — the same trader's method, pointed at gold. Not a second bot.

WALLACE'S INSTRUCTION
    The trader we are copying watches four markets: "I trade GBP USD and GBP
    JPY... I trade gold and then I also trade the S P 500." The bot covered
    one of the four. This is the second, traded automatically.

WHICH GOLD, AND WHY — the short version, measured in step443_gold_route.py
    Two ways to hold gold on this broker: PAXG/USD, a gold-backed token on
    the crypto endpoints that never closes, and GLD, the gold fund, US market
    hours only. The token's never-closing day looks like the better fit for a
    method with no bell. Measured over 150 days it is not, and the reason is
    not that it is expensive — it is that its chart is not a chart of gold.

        real gold (GC=F)  1-hour candle, median height   0.42% of price
        GLD               1-hour candle, median height   0.40%   <- gold
        PAXG/USD          1-hour candle, median height   1.26%   <- not gold

    PAXG's measured bid-ask spread is 1.26% of price. Its hourly candle is
    1.26% tall. Those are the same number because they are the same thing:
    the highs and lows on that chart are the ask and the bid being printed as
    trades, not gold going anywhere. Every "sweep" of a level the method
    would read there is the spread flipping sides. Its 5-minute chart is also
    24% holes and 16% candles that never moved, and tjr_bot's own two-candle
    swing finds 35 swings per 100 candles on it against GLD's 45.

    THIS IS NOT A COST FILTER, and the distinction matters because cost
    filters are banned here. Nothing declines or ranks a trade on spread. The
    finding is about whether the CHART EXISTS: on PAXG the structure the
    method reads is an artefact of the quote, so there is nothing to read.
    We would reach the same conclusion if the spread were free.

    GLD also tracks gold more closely hour by hour (0.987 against 0.968) and
    sits closer to it (typically 0.17% away against 0.25%), and its 5-minute
    history is dense back to August 2025 where PAXG's only starts in February
    2026.

WHAT WE GIVE UP, STATED
    The bell. GLD trades roughly 04:00-20:00 US Eastern on weekdays and gold
    keeps moving overnight without us. That costs less than it sounds: the
    method only ever enters between 09:50 and 10:30 US Eastern, a window that
    exists on GLD and would have had to be invented on a 24-hour token. The
    overnight move arrives as the opening gap and the pre-market sweep, both
    of which the method already reads.

THE TWIN, AND WHY GOLD KEEPS THE VETO CRYPTO HAD TO DROP
    "if the S&P 500 and the NASDAQ on the five minute are not aligned, I do
    not want to be taking a trade." Crypto had to switch that off because ten
    pairs have no natural partner. Gold has one: GLD and IAU are two funds
    holding the same bars of the same metal, which is the SPY/QQQ
    relationship in a purer form. Measured, the two agree on the direction of
    the 5-minute candle 86.9% of the time — often enough to be a real check,
    rarely enough that the remaining 13% is a filter rather than a blockade.

    So the veto is ON. IAU is loaded as a CHART ONLY and is never traded: its
    own 5-minute record is 21% holes and 21% dead candles, which is fine for
    reading a direction and not fine for placing an order into.

COSTS ARE CHARGED AND NEVER CONSULTED
    GLD's measured round-trip is 0.0109% of price. It is subtracted from
    every closed trade so the money stays honest. Nothing in this file
    declines a trade, moves a threshold or prefers a route because of it.

HOW IT IS JUDGED
    Not by backtest profit. He does not count historical replay as evidence.
    What the replay here is for is one number nothing else can give: how many
    setups a day gold produces. Trade count is the constraint, so
    `setups_per_day()` reports it and it is the only thing this file claims.

HOW A RUNNER WIRES THIS UP, since gold is the half that trades by itself
    Once a minute, with the stock market open:
        data = {"GLD": tjr_gold.load("GLD"), "IAU": tjr_gold.load("IAU")}
              (live, ending at the last CLOSED 1-minute bar, `t` in New York)
        out  = tjr_gold.live_step(data, now, account=<the broker's equity>,
                                  buying_power=<the broker's own figure>,
                                  clock=<Alpaca's /v2/clock>)
    and when out["action"] == "enter", send a bracket on out["symbol"] for
    out["shares"] with out["stop"] and out["targets"]. Every field the order
    needs is on that dictionary and none of it has to be recomputed.

    THAT SENDING IS NOT WIRED HERE, deliberately. The Alpaca account has
    never had an order placed on it and this file is not the thing that
    changes that. daemon.py is untouched.

SAFETY
    This module places no orders and imports nothing that can. It reads price
    frames and returns decisions, exactly like tjr_bot.py and tjr_crypto.py.
    `live_step` returns an intention a runner may act on; it never sends.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics

import numpy as np
import pandas as pd

import tjr_bot
from tjr_bot import (Bar, Config, Instrument, NewsCalendar, TjrBot,
                     TrendTracker, US_INDEX_ETF)

REPO = os.path.dirname(os.path.abspath(__file__))

# The one we trade, and the one we only look at.
TRADED = "GLD"
TWIN = "IAU"
SYMBOLS = (TRADED, TWIN)

DERIVED_PATH = f"{REPO}/step443_gold_thresholds.json"


def cache_name(symbol: str, tf: str) -> str:
    return f"{REPO}/data_alpaca_{symbol}_{tf}.parquet"


# ====================================================== THE INSTRUMENT
#
# EVERY CLOCK FIELD IS SET, and set to his, which is the whole difference
# between this file and tjr_crypto.py. Gold on this route trades a US
# session, so it keeps the US session rules rather than having them stripped:
# the 09:30 open, the 09:50 end of the manipulation window, the 10:30 hard
# cut-off, flat by 15:55. He trades gold in the same morning routine as the
# indexes and narrates it on the same clock (bootcamp Day 49 is a gold read
# inside the index morning), so this is his clock, not one we chose.
#
# The three session windows — Asia 18:00-03:00, London 03:00-08:30, New York
# 08:30-18:00 — are his too, verbatim, and they stay. Gold's overnight is
# real and the previous London high is a real draw on liquidity even though
# our fund was shut while it formed. GLD's extended-hours bars from 04:00
# cover most of London, so those levels are marked from bars we actually have
# rather than inferred.

GOLD_ETF = Instrument(
    name="gold_etf",
    # measured, charged, never consulted. Replaced by the measured value in
    # gold_config() when step443_gold_thresholds.json exists.
    round_trip_cost_pct=0.000109,
    open_t=dt.time(9, 30), manip_end_t=dt.time(9, 50),
    entry_ideal_end_t=dt.time(10, 10), cutoff_t=dt.time(10, 30),
    flat_t=dt.time(15, 55), close_t=dt.time(16, 0),
    prior_session_window=(3, 8.5), early_session_window=(18, 3),
    own_session_window=(8.5, 18), day_boundary_hour=18, has_closing_bell=True,
    level_minutes=(60, 240), working_minutes=5, trigger_minutes=1,
    continuation_minutes=15, target1_minutes=15,
    # The futures-session anchor, same as the index instrument. Gold's own
    # futures session opens at 18:00 US Eastern and his 4-hour candles hang
    # off the 17:00 grid he draws every chart on. A midnight grid would make
    # the last completed 4-hour candle at the bell one built out of thin
    # overnight prints.
    candle_anchor_hour=17)


def load_derived() -> dict:
    if os.path.exists(DERIVED_PATH):
        with open(DERIVED_PATH) as f:
            return json.load(f)
    return {}


def gold_config(account_start: float = 100_000.0,
                spread_pct: float | None = None,
                derived: dict | None = None) -> Config:
    """The method's Config with every SPY-measured number replaced by gold's
    own, and the twin veto deliberately left ON.

    Nothing here is a new rule. Each line is one of his rules with the number
    re-measured on the instrument it is about to be applied to, which is the
    same thing the crypto file does and for the same reason: SPY's normal
    move and gold's are different numbers permanently.
    """
    derived = derived if derived is not None else load_derived()
    row = derived.get(TRADED) or {}
    if spread_pct is None:
        spread_pct = row.get("spread_pct", GOLD_ETF.round_trip_cost_pct)
    ceiling = row.get("sweep_max_age_bars") or 12

    inst = dataclass_replace(GOLD_ETF, round_trip_cost_pct=float(spread_pct))

    cfg = Config(
        instrument=inst,
        account_start=account_start,

        # -- RE-DERIVED #1: the stop buffer ------------------------------
        # HIS rule: clear your broker's spread. The stock config carries
        # 0.0001 because that is SPY's spread. Gold's measured spread is its
        # own number and this is it.
        stop_buffer_pct_of_price=float(spread_pct),

        # -- RE-DERIVED #2: how long a taken level stays pending ---------
        # Twice this instrument's own measured median sweep-to-signal gap,
        # which is the rule the stock number came from.
        sweep_max_age_bars=ceiling,

        # -- NOT re-derived, and why -------------------------------------
        # buying_power_multiple stays at the stock 4x because GLD IS a stock:
        # it is marginable and the broker reports day-trade buying power on
        # it the same way it does on SPY. Live, the caller passes the
        # broker's own figure and this default is never reached.

        # -- THE TWIN VETO: ON, deliberately -----------------------------
        # See the module docstring. GLD and IAU are two wrappers on one
        # market, so a disagreement between them is a contradiction about one
        # thing — exactly what the veto is for.
        enforce_index_agreement=True,

        # -- THE PRE-MARKET CARVE-OUT: ON --------------------------------
        # There IS a pre-market here and gold moves all night, so the sweep
        # that already happened before the bell is the day's sweep. This is
        # the rule crypto had to drop for having no bell to carry it across.
        premarket_sweep_carries_forward=True,
    )
    # Charts loaded for the veto that must never be traded. Read by the
    # SymbolDay shim below. Set as an attribute rather than a Config field so
    # tjr_bot.py is not edited while another agent holds it.
    cfg.check_only = (TWIN,)
    return cfg


def dataclass_replace(inst: Instrument, **kw) -> Instrument:
    """A copy of an Instrument with fields replaced. Written out rather than
    imported so this file has no opinion about how tjr_bot builds them."""
    import dataclasses
    return dataclasses.replace(inst, **kw)


# ================================================ THE CHECK-ONLY SHIM
#
# WHY A SHIM AND NOT AN EDIT. tjr_bot.py is being edited by someone else on
# exit logic. This wraps one class and leaves the file alone, the same way
# tjr_crypto.py wraps session_levels. Fold it in when that file is free.
#
# WHAT IT DOES. tjr_bot.run_day reads EVERY loaded symbol's 5-minute trend
# for the veto but will only trade the ones that have not stood down. A
# symbol named in cfg.check_only is marked stood-down at construction, so it
# feeds the veto and can never take a trade. Without this, IAU — whose own
# 5-minute record is 21% holes — could be the chart an order got placed
# against.
#
# It is INERT for every other caller: cfg.check_only is absent on the stock
# and crypto configs, so the branch is never taken there.

_ORIGINAL_SYMBOL_DAY = tjr_bot.SymbolDay
_INSTALLED = False


class _CheckOnlyAware(_ORIGINAL_SYMBOL_DAY):
    def __init__(self, symbol, d5_hist, d1_hist, day, cfg, news, escalated):
        super().__init__(symbol, d5_hist, d1_hist, day, cfg, news, escalated)
        if symbol in tuple(getattr(cfg, "check_only", ()) or ()):
            self.ctx.stand_down = ("loaded as a second opinion only — this "
                                   "chart is never traded")


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    tjr_bot.SymbolDay = _CheckOnlyAware
    _INSTALLED = True


install()


# ================================================ DATA: FETCH AND CACHE
def _bars_between(cli, symbol: str, code: str, start: str, end: str) -> list:
    """Stock bars for a bounded window, EVERY PAGE of them.

    `limit` caps the rows in one response, not the rows you asked for. A
    next_page_token left unfollowed silently truncates history, and truncated
    history looks like a short market rather than a short download.

    This data plan also refuses stock bars from the last fifteen minutes and
    answers 403 rather than an empty list, so callers keep `end` behind now.
    """
    import alpaca as _a
    params = {"timeframe": code, "limit": 10000, "adjustment": "split",
              "start": start, "end": end}
    rows, token, pages = [], None, 0
    while pages < 200:
        if token:
            params["page_token"] = token
        out = cli._get(f"/v2/stocks/{symbol}/bars", params, base=_a.DATA_URL) or {}
        rows += out.get("bars") or []
        token = out.get("next_page_token")
        pages += 1
        if not token:
            break
    return rows


def to_et_frame(rows: list) -> pd.DataFrame:
    """Alpaca stock JSON -> the frame tjr_bot walks, `t` the bar's START in
    US Eastern. The same conversion the index path does, in the same place
    and for the same reason: every `.normalize()` downstream then cuts on his
    clock rather than on UTC."""
    if not rows:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
    d = pd.DataFrame(rows)
    ts = pd.to_datetime(d["t"], utc=True, format="mixed")
    out = pd.DataFrame({
        "t": ts.dt.tz_convert("America/New_York").dt.tz_localize(None),
        "open": d["o"].astype(float), "high": d["h"].astype(float),
        "low": d["l"].astype(float), "close": d["c"].astype(float)})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def fetch(start_5m: str = "2025-09-01", start_1m: str = "2026-03-01",
          verbose: bool = True) -> None:
    """Download and cache both charts for both symbols. Read-only against the
    venue; writes parquet next to the other caches."""
    import alpaca
    cli = alpaca.from_env()
    if cli is None:
        raise RuntimeError("ALPACA keys are not in .env")
    stop = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
    for sym in SYMBOLS:
        for tf, code, start in (("5m", "5Min", start_5m),
                                ("1m", "1Min", start_1m)):
            got, cur = [], dt.date.fromisoformat(start)
            while cur < stop.date():
                nxt = min(cur + dt.timedelta(days=20), stop.date())
                end_s = (str(nxt) if nxt < stop.date()
                         else stop.strftime("%Y-%m-%dT%H:%M:%SZ"))
                got += _bars_between(cli, sym, code, str(cur), end_s)
                cur = nxt
            d = to_et_frame(got)
            d.to_parquet(cache_name(sym, f"et_{tf}"))
            if verbose:
                span = f"{d['t'].min()} .. {d['t'].max()}" if len(d) else "empty"
                print(f"  {sym:4s} {tf:3s} {len(d):>7,} bars   {span}")


def load(symbol: str = TRADED) -> dict:
    """{"5m": frame, "1m": frame}, `t` in US Eastern."""
    return {tf: pd.read_parquet(cache_name(symbol, f"et_{tf}"))
            for tf in ("5m", "1m")}


def load_both() -> dict:
    return {s: load(s) for s in SYMBOLS}


# ======================================================= DERIVATION
def measure_spread_pct(cli, symbol: str, days: int = 12,
                       per_day: int = 3000) -> float | None:
    """The real bid-ask spread as a share of the mid, MEASURED.

    Sampled across separate days rather than off one snapshot, and reported
    as the MEDIAN so one dislocated quote cannot move the number the account
    is charged. Sampled inside the regular session, which is when the method
    actually trades.

    This is the number we CHARGE. It is not consulted anywhere.
    """
    import alpaca as _a
    base = dt.date.today() - dt.timedelta(days=4)
    rel = []
    for k in range(days):
        day = base - dt.timedelta(days=7 * k)
        if day.weekday() >= 5:
            day -= dt.timedelta(days=day.weekday() - 4)
        try:
            out = cli._get(f"/v2/stocks/{symbol}/quotes",
                           {"start": f"{day}T15:00:00Z", "end": f"{day}T15:10:00Z",
                            "limit": per_day}, base=_a.DATA_URL) or {}
        except Exception:
            continue
        for r in out.get("quotes") or []:
            ap, bp = float(r["ap"]), float(r["bp"])
            mid = (ap + bp) / 2.0
            if mid > 0 and ap > bp:
                rel.append((ap - bp) / mid)
    return float(statistics.median(rel)) if rel else None


def measure_sweep_to_signal(d5: pd.DataFrame, cfg: Config,
                            lookback_days: int = 200) -> dict:
    """How long a taken level stays pending here before the 5-minute turns.

    tjr_bot ships `sweep_max_age_bars = 12` and says why: SPY's median
    sweep-to-signal gap measured 6 five-minute bars and the ceiling is twice
    the median. The RULE is "twice the median". The 6 is SPY's. This
    re-measures the median on gold's own bars and applies the same rule.

    Causal throughout: levels are marked from bars completed before the day
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
        session = d5[(d5["t"] >= day + pd.Timedelta(hours=inst.open_t.hour,
                                                    minutes=inst.open_t.minute)) &
                     (d5["t"] < day + pd.Timedelta(hours=inst.close_t.hour))]
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


def derive_all(verbose: bool = True) -> dict:
    """Measure every re-derived threshold from gold's own bars and quotes and
    write them down. Read-only against the venue."""
    import alpaca
    cli = alpaca.from_env()
    out = {}
    for sym in SYMBOLS:
        sp = measure_spread_pct(cli, sym)
        row = {"spread_pct": None if sp is None else round(sp, 8),
               "spread_pct_of_price": None if sp is None else round(100 * sp, 5)}
        try:
            d5 = pd.read_parquet(cache_name(sym, "et_5m"))
            m = measure_sweep_to_signal(d5, gold_config(derived={}))
            row.update({"sweep_median_bars": m["median"],
                        "sweep_max_age_bars": m["ceiling"], "sweep_n": m["n"]})
        except FileNotFoundError:
            row.update({"sweep_median_bars": None, "sweep_max_age_bars": None,
                        "sweep_n": 0})
        out[sym] = row
        if verbose:
            print(f"  {sym:4s} spread {row['spread_pct_of_price']}% of price   "
                  f"sweep-to-signal median {row['sweep_median_bars']} bars   "
                  f"ceiling {row['sweep_max_age_bars']} (n={row['sweep_n']})")
    with open(DERIVED_PATH, "w") as f:
        json.dump(out, f, indent=2)
    return out


# ======================================================= THE REPLAY
def days_in(data: dict, start=None, end=None) -> list:
    t = data[TRADED]["1m"]["t"]
    if start is not None:
        t = t[t >= pd.Timestamp(start)]
    if end is not None:
        t = t[t < pd.Timestamp(end) + pd.Timedelta(days=1)]
    return sorted(t.dt.normalize().unique())


def slice_for(data: dict, day: pd.Timestamp, cfg: Config) -> dict:
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    return {s: {tf: data[s][tf][(data[s][tf]["t"] >= lo) & (data[s][tf]["t"] < hi)]
                .reset_index(drop=True) for tf in ("5m", "1m")}
            for s in data}


def run_gold(start=None, end=None, cfg: Config | None = None,
             data: dict | None = None, verbose: bool = False) -> dict:
    """Walk gold day by day, strictly forward. Both charts are loaded so the
    twin veto is real; only GLD can take a trade."""
    cfg = cfg or gold_config()
    data = data or load_both()
    news = NewsCalendar()          # gold has US news days and it keeps them
    bot = TjrBot(cfg, news)
    trades, reasons, skipped = [], {}, 0
    days = days_in(data, start, end)
    for day in days:
        day = pd.Timestamp(day)
        win = slice_for(data, day, cfg)
        sess = win[TRADED]["1m"]
        if len(sess[(sess["t"] >= day) & (sess["t"] < day + pd.Timedelta(days=1))]) == 0:
            skipped += 1
            continue
        res = bot.run_day(win, day)
        if res["trade"] is not None:
            trades.append(res["trade"])
        for sym, why in res["stand_down"].items():
            if sym == TWIN:
                continue           # its permanent "chart only" note is not a reason
            reasons[why] = reasons.get(why, 0) + 1
        if verbose and res["trade"] is not None:
            tr = res["trade"]
            side = "buy" if tr.direction > 0 else "sell"
            print(f"  {day:%Y-%m-%d} gold {side:4s} off the {tr.level_tf} level "
                  f"at {tr.level_price:,.2f} -> {tr.outcome}")
    return {"days": len(days) - skipped, "trades": trades,
            "reasons": reasons, "account": bot.account}


def setups_per_day(start=None, end=None, verbose: bool = True) -> dict:
    """THE NUMBER THIS EXERCISE EXISTS TO PRODUCE.

    A "setup" is a completed sequence that reached an entry: a marked level
    pushed through, a 5-minute confirmation, both gold charts agreeing, a
    pullback into the midpoint or a fair value gap, and a 1-minute trigger.
    One per day at most, which is the bot's own rule.

    No profit claim. He does not count replay as evidence and neither do we.
    """
    cfg = gold_config()
    r = run_gold(start, end, cfg=cfg)
    n, days = len(r["trades"]), max(r["days"], 1)
    longs = sum(1 for t in r["trades"] if t.direction > 0)
    out = {"market": "gold (GLD, with IAU as the second chart)",
           "days": r["days"], "setups": n, "per_day": round(n / days, 3),
           "one_every_n_days": round(days / n, 1) if n else None,
           "buys": longs, "sells": n - longs,
           "cost_charged_pct_of_price": round(
               100 * cfg.instrument.round_trip_cost_pct, 5),
           "sweep_max_age_bars": cfg.sweep_max_age_bars,
           "top_stand_down": sorted(r["reasons"].items(), key=lambda kv: -kv[1])[:4]}
    if verbose:
        print(f"  gold  {out['days']:>4} days   {n:>3} setups   "
              f"{out['per_day']:.3f}/day   {longs} buys / {n - longs} sells")
    return out


# ============================================================ LIVE
def live_step(data: dict, now: pd.Timestamp, account: float,
              buying_power: float | None = None, clock: dict | None = None,
              cfg: Config | None = None, week_pnl: dict | None = None) -> dict:
    """The one call a live gold runner makes. Returns an intention, never an
    order.

    data         : {"GLD": {"5m": frame, "1m": frame},
                    "IAU": {...}} with `t` in US Eastern, ending at the last
                   CLOSED 1-minute bar. BOTH charts, or the veto is not real.
    now          : the CLOSE time of that bar, US Eastern
    account      : the broker's own equity. Read it, do not compute it.
    buying_power : the broker's own day-trade buying power.
    clock        : Alpaca's /v2/clock. Missing, or shut, and this refuses —
                   gold on this route has a bell and the refusal is correct.

    Returns {"action": "stand_down" | "wait" | "enter", ...}.
    """
    cfg = cfg or gold_config()
    if TWIN not in data:
        return {"action": "stand_down",
                "reason": "the second gold chart is missing, so the two-chart "
                          "agreement check cannot be made"}
    out = tjr_bot.live_step(data, now, account, buying_power=buying_power,
                            clock=clock, cfg=cfg, news=NewsCalendar(),
                            week_pnl=week_pnl)
    if out.get("action") == "enter":
        out["market"] = "gold"
    return out


def main(argv):
    if "--fetch" in argv:
        print("fetching gold bars (read-only against the venue)")
        fetch()
        return
    if "--derive" in argv:
        print("re-deriving every threshold from gold's own bars and quotes")
        derive_all()
        return
    start = argv[1] if len(argv) > 1 and not argv[1].startswith("-") else None
    end = argv[2] if len(argv) > 2 and not argv[2].startswith("-") else None
    print("=" * 78)
    print("gold: setups per day — the number trade count is constrained by")
    print("=" * 78)
    print(json.dumps(setups_per_day(start, end), indent=2, default=str))


if __name__ == "__main__":
    import sys
    main(sys.argv)
