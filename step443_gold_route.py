"""
step443_gold_route.py — which gold do we actually trade: PAXG/USD or GLD?

THE QUESTION, AS ASKED
    Two ways to hold gold on this broker. PAXG/USD is a gold-backed token
    that trades every hour of every day on the crypto endpoints. GLD is the
    gold fund, US market hours only, on the stock endpoints. The method has
    no closing bell in it, so the token's never-closing day is attractive on
    its face. That is not evidence, so this measures four things instead:

      1. TRACKING     — how closely does each follow the actual gold price
                        (front-month gold futures, GC=F)?
      2. MOVEMENT     — how far does each travel in a typical hour and a
                        typical four hours, as a share of its own price?
                        A market that does not move cannot pay a stop.
      3. READABILITY  — does the chart the method needs actually exist?
                        Bars present out of bars expected at 5-minute,
                        1-hour and 4-hour, and how many of the two-candle
                        swings the whole method is built on get found.
      4. SUPPLY       — how much 5-minute history is there to mark levels
                        off, and how far back does it stay dense?

    None of these four is a profit claim. He does not count historical
    replay as evidence and neither do we. These are facts about the
    instrument, which is a different kind of question from "does it pay".

COSTS ARE CHARGED, NEVER CONSULTED
    The spread is measured and reported so the money stays honest. Nothing
    in this file ranks, prefers or declines either route on what it costs.

SAFETY
    Read-only. No orders, no writes outside this repo's own parquet cache.

USAGE
    python3 step443_gold_route.py            # the full comparison
    python3 step443_gold_route.py --fetch    # refresh the cached bars first
"""

from __future__ import annotations

import datetime as dt
import json
import os
import statistics
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))

PAXG = "PAXG/USD"
GLD = "GLD"
# The twin. Two funds holding the same bars of metal, which is the SPY/QQQ
# relationship in a purer form — see twin_agreement() at the bottom.
IAU = "IAU"
STOCKS = (GLD, IAU)

# The trailing window every number below is measured over. Kept short and
# recent on purpose: PAXG's older history is thin (see supply()), and an
# instrument's liquidity today is what a trade placed today meets.
WINDOW_DAYS = 150


# --------------------------------------------------------------- caches
def paxg_cache(tf: str) -> str:
    return f"{REPO}/data_alpaca_PAXGUSD_{tf}.parquet"


def stock_cache(symbol: str, tf: str) -> str:
    return f"{REPO}/data_alpaca_{symbol}_{tf}.parquet"


def spot_cache() -> str:
    return f"{REPO}/data_gold_spot_1h.parquet"


# ------------------------------------------------------------- fetching
def fetch(verbose: bool = True) -> None:
    """Refresh every cache this file reads. Read-only against both venues."""
    import alpaca
    import tjr_crypto

    cli = alpaca.from_env()
    if cli is None:
        raise RuntimeError("ALPACA keys are not in .env")

    for tf, code, start in (("5m", "5Min", "2025-09-01"),
                            ("1m", "1Min", "2026-03-01")):
        rows = cli.crypto_bars(PAXG, code, start=start).get(PAXG) or []
        d = tjr_crypto.to_utc_frame(rows)
        d.to_parquet(paxg_cache(tf))
        if verbose:
            print(f"  PAXG/USD {tf:3s} {len(d):>7,} bars  "
                  f"{d['t'].min() if len(d) else '-'} .. "
                  f"{d['t'].max() if len(d) else '-'}")

    # GLD: the stock bars endpoint caps a response and does NOT page, so the
    # window is walked in month-sized chunks. Ignoring that would look like a
    # short market rather than a short download — the same trap the crypto
    # path documents.
    for sym in STOCKS:
        for tf, code, start in (("5m", "5Min", "2025-09-01"),
                                ("1m", "1Min", "2026-03-01")):
            got: list = []
            cur = dt.date.fromisoformat(start)
            # a full hour behind now, clear of the fifteen-minute wall
            stop = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
            while cur < stop.date():
                nxt = min(cur + dt.timedelta(days=20), stop.date())
                end_s = (str(nxt) if nxt < stop.date()
                         else stop.strftime("%Y-%m-%dT%H:%M:%SZ"))
                got += _bars_between(cli, sym, code, str(cur), end_s)
                cur = nxt
            d = _stock_frame(got)
            d.to_parquet(stock_cache(sym, tf))
            if verbose:
                print(f"  {sym:8s} {tf:3s} {len(d):>7,} bars  "
                      f"{d['t'].min() if len(d) else '-'} .. "
                      f"{d['t'].max() if len(d) else '-'}")

    # Spot gold, for the tracking test. GC=F is the front-month futures
    # contract, which is the price both instruments are supposed to be a
    # wrapper around.
    import yfinance as yf
    sp = yf.download("GC=F", interval="60m", period="730d",
                     progress=False, auto_adjust=False)
    if isinstance(sp.columns, pd.MultiIndex):
        sp.columns = [c[0] for c in sp.columns]
    sp = sp.reset_index()
    sp.columns = [str(c).lower() for c in sp.columns]
    tcol = "datetime" if "datetime" in sp.columns else "date"
    sp = pd.DataFrame({"t": pd.to_datetime(sp[tcol], utc=True).dt.tz_localize(None),
                       "open": sp["open"].astype(float),
                       "high": sp["high"].astype(float),
                       "low": sp["low"].astype(float),
                       "close": sp["close"].astype(float)})
    sp.to_parquet(spot_cache())
    if verbose:
        print(f"  GC=F     1h  {len(sp):>7,} bars  {sp['t'].min()} .. {sp['t'].max()}")


def _bars_between(cli, symbol: str, code: str, start: str, end: str) -> list:
    """Stock bars for a bounded window, EVERY PAGE of them.

    Two things this has to get right and alpaca.bars does not expose:

      PAGING. `limit` caps the rows in one response, not the rows you asked
      for. A next_page_token left unfollowed silently truncates history, and
      truncated history looks like a short market rather than a short
      download — the single most dangerous way for this to go wrong.

      THE FIFTEEN-MINUTE WALL. This data plan refuses stock bars from the
      last fifteen minutes ("subscription does not permit querying recent SIP
      data") and answers 403, not an empty list. The caller caps `end` well
      behind now; this is the note saying why.
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


def _stock_frame(rows: list) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
    d = pd.DataFrame(rows)
    ts = pd.to_datetime(d["t"], utc=True, format="mixed")
    out = pd.DataFrame({"t": ts.dt.tz_localize(None),
                        "open": d["o"].astype(float), "high": d["h"].astype(float),
                        "low": d["l"].astype(float), "close": d["c"].astype(float)})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def load(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


# ------------------------------------------------------------ resampling
def to_tf(d5: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """5-minute bars -> a `minutes` chart, midnight grid. Only used for the
    descriptive numbers below; the bot itself uses tjr_bot.resample_tf."""
    if len(d5) == 0:
        return d5
    g = d5.groupby(d5["t"].dt.floor(f"{minutes}min"))
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(),
                        "low": g["low"].min(), "close": g["close"].last()})
    out.index.name = "t"
    return out.reset_index()


def recent(d: pd.DataFrame, days: int = WINDOW_DAYS) -> pd.DataFrame:
    if len(d) == 0:
        return d
    return d[d["t"] >= d["t"].max() - pd.Timedelta(days=days)].reset_index(drop=True)


# ------------------------------------------------------- 1. TRACKING
def tracking(inst: pd.DataFrame, spot: pd.DataFrame) -> dict:
    """How closely the instrument follows real gold, on 1-hour closes.

    Two numbers, because they answer two different questions:

      match of hour-by-hour moves — do the two charts turn at the same time?
        Reported as a correlation of one-hour percentage price changes. This
        is the one that matters to a method that reads structure: a level
        broken on the instrument's chart has to be a level broken on gold's.

      typical gap between the two prices — does the wrapper drift away from
        what it wraps? Reported as the median absolute difference between the
        two, in percent of the gold price, after removing the constant
        conversion factor (a fund share is a tenth of an ounce; the token is
        one ounce).
    """
    # Both sides are collapsed to ONE row per hour BEFORE the join. Merging
    # 5-minute rows onto a floored hour would match twelve instrument rows to
    # one gold row and quietly compare a step function against a real one —
    # it reads as a tracking failure when nothing is wrong.
    a = (inst.assign(t=inst["t"].dt.floor("60min"))
         .groupby("t", as_index=False).agg(close=("close", "last")))
    b = (spot.assign(t=spot["t"].dt.floor("60min"))
         .groupby("t", as_index=False).agg(close=("close", "last")))
    j = a.merge(b, on="t", suffixes=("_i", "_s")).dropna()
    if len(j) < 100:
        return {"hours_compared": len(j), "move_match": None, "typical_gap_pct": None}
    ri = j["close_i"].pct_change()
    rs = j["close_s"].pct_change()
    ok = ri.notna() & rs.notna()
    corr = float(np.corrcoef(ri[ok], rs[ok])[0, 1])
    ratio = j["close_i"] / j["close_s"]
    k = float(ratio.median())                    # the constant conversion factor
    gap = (ratio / k - 1.0).abs() * 100.0
    return {"hours_compared": int(len(j)),
            "move_match": round(corr, 4),
            "conversion_factor": round(k, 5),
            "typical_gap_pct": round(float(gap.median()), 4),
            "worst_gap_pct": round(float(gap.quantile(0.99)), 4)}


# ------------------------------------------------------- 2. MOVEMENT
def movement(d5: pd.DataFrame) -> dict:
    """How far this thing travels, as a share of its own price.

    Reported as the median high-to-low range of a candle divided by that
    candle's own price — a PRICE MOVE, not a change in any position's value.
    A stop has to sit outside the noise, so a market whose hourly candle is
    a tenth the size of another's needs a proportionally tighter stop to risk
    the same money, and its levels sit proportionally closer together.
    """
    out = {}
    for label, minutes in (("1h", 60), ("4h", 240)):
        tf = to_tf(d5, minutes)
        if len(tf) == 0:
            out[label] = None
            continue
        rng = (tf["high"] - tf["low"]) / tf["close"] * 100.0
        out[label] = {"bars": int(len(tf)),
                      "median_range_pct_of_price": round(float(rng.median()), 4),
                      "busy_bar_range_pct_of_price": round(float(rng.quantile(0.9)), 4)}
    return out


# ------------------------------------------------------ 3. READABILITY
def readability(d5: pd.DataFrame) -> dict:
    """Does the chart the method needs actually exist?

    THE TEST THAT MATTERS. The whole method rests on the two-candle swing —
    an up candle then a down candle makes a high, the reverse makes a low —
    and on levels marked off the 1-hour and the 4-hour. If a chart is full of
    holes, or full of candles that never moved, those swings are not there to
    be found and the method has nothing to read.

    NOTHING HERE ASSUMES A SESSION. Holes are counted inside each day's OWN
    span, from that day's first bar to its last, so an instrument is never
    penalised for being shut and never credited for being open. `hours_a_day`
    reports that span separately, which is the honest place for the "it never
    closes" claim to either show up or not.

    Per timeframe:
      hours_a_day      — median hours from the day's first bar to its last
      holes_pct        — slots with no bar, inside that same span
      dead_bar_pct     — candles whose open and close are identical, so the
                         candle has no direction and can be half of no swing
      swings_per_100   — two-candle swing highs and lows found per hundred
                         candles, using tjr_bot's own function, not a copy
    """
    import tjr_bot
    out = {}
    for label, minutes in (("5m", 5), ("1h", 60), ("4h", 240)):
        tf = d5 if minutes == 5 else to_tf(d5, minutes)
        if len(tf) < 10:
            out[label] = None
            continue
        spans, holes, slots = [], 0, 0
        for _, g in tf.groupby(tf["t"].dt.normalize()):
            if len(g) < 2:
                continue
            span = (g["t"].max() - g["t"].min()).total_seconds() / 60.0
            spans.append(span / 60.0)
            want = int(span // minutes) + 1
            slots += want
            holes += max(want - len(g), 0)
        dead = float((tf["open"] == tf["close"]).mean() * 100.0)
        hi, lo = tjr_bot.two_candle_swings(tf)
        n_sw = int(np.isfinite(hi).sum() + np.isfinite(lo).sum())
        out[label] = {
            "bars": int(len(tf)),
            "hours_a_day": round(float(np.median(spans)), 2) if spans else None,
            "holes_pct": round(100.0 * holes / slots, 2) if slots else None,
            "dead_bar_pct": round(dead, 2),
            "swings_per_100_candles": round(100.0 * n_sw / len(tf), 1)}
    return out


# ---------------------------------------------------------- 4. SUPPLY
def supply(d5: pd.DataFrame, expected_bars_per_day: float) -> dict:
    """How far back the 5-minute chart stays dense enough to mark levels off.

    Walks backwards month by month and reports the first month where fewer
    than 60% of the expected bars are present. Levels are marked off ten days
    of 1-hour and 4-hour history, so a chart that goes thin two months back
    is still usable today — but it is not usable for measuring how often the
    setup fires, and that distinction is worth having in writing.
    """
    if len(d5) == 0:
        return {"first_bar": None, "dense_since": None}
    end = d5["t"].max()
    dense_since = None
    for k in range(0, 40):
        hi = end - pd.Timedelta(days=30 * k)
        lo = hi - pd.Timedelta(days=30)
        seg = d5[(d5["t"] >= lo) & (d5["t"] < hi)]
        want = 30 * expected_bars_per_day
        if len(seg) < 0.60 * want:
            break
        dense_since = lo
    return {"first_bar": str(d5["t"].min()),
            "last_bar": str(d5["t"].max()),
            "total_5m_bars": int(len(d5)),
            "dense_since": str(dense_since) if dense_since is not None else None}


# ------------------------------------------------------------- SPREAD
def paxg_spread_pct(days: int = 12) -> float | None:
    """The measured bid-ask spread on PAXG as a share of the mid price.
    Charged, never consulted. Median across separate days so one dislocated
    quote cannot move the number the account is charged."""
    import alpaca
    cli = alpaca.from_env()
    if cli is None:
        return None
    base = dt.date.today() - dt.timedelta(days=3)
    rel = []
    for k in range(days):
        day = base - dt.timedelta(days=12 * k)
        try:
            q = cli.crypto_quotes(PAXG, f"{day}T12:00:00Z", f"{day}T12:20:00Z",
                                  limit=3000)
        except Exception:
            continue
        for r in q.get(PAXG) or []:
            ap, bp = float(r["ap"]), float(r["bp"])
            mid = (ap + bp) / 2.0
            if mid > 0 and ap > bp:
                rel.append((ap - bp) / mid)
    return float(statistics.median(rel)) if rel else None


def _days_a_week(d5: pd.DataFrame) -> float:
    """Calendar days a week this instrument prints bars on. Measured, so the
    "it never closes" claim is a number rather than a sentence."""
    if len(d5) == 0:
        return 0.0
    days = d5["t"].dt.normalize().nunique()
    weeks = (d5["t"].max() - d5["t"].min()).total_seconds() / (7 * 86400.0)
    return round(days / weeks, 2) if weeks > 0 else 0.0


# ------------------------------------------------------------- REPORT
def twin_agreement() -> dict:
    """How often the two gold funds tell the same story on the 5-minute.

    WHY THIS IS HERE. The one veto in the method that could not follow the
    bot into crypto was "if the S&P and the NASDAQ on the five minute are not
    aligned, I do not want to be taking a trade" — because ten crypto pairs
    have no natural partner and picking one would be inventing a rule. Gold
    is not in that position. GLD and IAU are two funds holding the same bars
    of the same metal, which is the SPY/QQQ relationship in a purer form: if
    those two charts disagree on the 5-minute they are not describing two
    markets, they are contradicting each other about ONE. So the veto has a
    real partner here and this measures whether it would fire often enough to
    be a filter and rarely enough not to be a blockade.

    Reported as the share of 5-minute candles where both funds close in the
    same direction as their own previous close.
    """
    a = recent(load(stock_cache(GLD, "5m")))
    b = recent(load(stock_cache(IAU, "5m")))
    j = a[["t", "close"]].merge(b[["t", "close"]], on="t", suffixes=("_a", "_b"))
    if len(j) < 100:
        return {"bars_compared": len(j), "agree_pct": None}
    da = np.sign(j["close_a"].diff())
    db = np.sign(j["close_b"].diff())
    live = (da != 0) & (db != 0) & da.notna() & db.notna()
    return {"bars_compared": int(live.sum()),
            "agree_pct": round(100.0 * float((da[live] == db[live]).mean()), 2)}


def compare(verbose: bool = True) -> dict:
    spot = load(spot_cache())
    px5 = recent(load(paxg_cache("5m")))

    # Bars a full day of this instrument SHOULD hold, at 5 minutes, used only
    # by supply() to judge when the history goes thin:
    #   PAXG trades every hour of every day                -> 288
    #   the funds trade roughly 04:00-20:00 ET on weekdays -> 192, 5 days in 7
    px_per_day = 288.0
    fund_per_day = 192.0 * 5.0 / 7.0

    out = {
        "window_days": WINDOW_DAYS,
        "PAXG/USD": {
            "tracking": tracking(px5, spot),
            "movement": movement(px5),
            "readability": readability(px5),
            "supply": supply(load(paxg_cache("5m")), px_per_day),
            "days_a_week_with_bars": _days_a_week(px5),
        },
    }
    for sym in STOCKS:
        d5 = recent(load(stock_cache(sym, "5m")))
        out[sym] = {
            "tracking": tracking(d5, spot),
            "movement": movement(d5),
            "readability": readability(d5),
            "supply": supply(load(stock_cache(sym, "5m")), fund_per_day),
            "days_a_week_with_bars": _days_a_week(d5),
        }

    # What real gold itself does in an hour, so the instruments' numbers have
    # something true to be compared against rather than only each other.
    sp_recent = recent(spot)
    rng = (sp_recent["high"] - sp_recent["low"]) / sp_recent["close"] * 100.0
    out["GC=F (real gold, the yardstick)"] = {
        "movement": {"1h": {
            "bars": int(len(sp_recent)),
            "median_range_pct_of_price": round(float(rng.median()), 4),
            "busy_bar_range_pct_of_price": round(float(rng.quantile(0.9)), 4)}}}

    sp = paxg_spread_pct()
    out["PAXG/USD"]["measured_spread_pct_of_price"] = \
        None if sp is None else round(100 * sp, 4)
    out["GLD vs IAU, the twin check"] = twin_agreement()

    if verbose:
        print(json.dumps(out, indent=2, default=str))
    return out


VERDICT = """
THE ROUTE IS GLD, WITH IAU AS ITS SECOND CHART. PAXG/USD IS REFUSED.

WHAT DECIDED IT, in one line: PAXG's candles are made of the quote, not of
gold.

    real gold (GC=F)  1-hour candle, median height   0.42% of price
    GLD               1-hour candle, median height   0.40%   <- gold
    IAU               1-hour candle, median height   0.37%   <- gold
    PAXG/USD          1-hour candle, median height   1.26%   <- not gold

PAXG's measured bid-ask spread is 1.26% of price and its hourly candle is
1.26% tall. Those are the same number because they are the same thing: the
high is the ask being printed and the low is the bid. Reading a level being
pushed through on that chart is reading the quote flip sides.

THIS IS NOT A COST FILTER, and that distinction is the whole point. Nothing
here declines or ranks a trade on what it costs, and the old "profit must
beat its cost" bar is retired. The finding is that the CHART DOES NOT EXIST
on PAXG — we would refuse it identically if the spread were free.

The rest of the record, same 150-day window:

                                     PAXG/USD      GLD       IAU
    follows gold hour by hour          0.968      0.987     0.978
    typical distance from gold         0.247%     0.173%    0.169%   (of the gold price)
    5-minute bars missing              24.3%       5.9%     21.3%
    5-minute candles that never moved  16.3%       6.5%     20.9%
    two-candle swings per 100 candles   34.9       44.9      34.5
    5-minute history dense since     2026-02-25 2025-08-28 2025-08-28
    days a week with bars               7.05       4.99      4.99

GLD wins every readability measure, and the swing count is the one that
matters most: the two-candle swing is what every level, every break of
structure and every stop in this method is built out of, and PAXG offers a
fifth fewer of them per candle.

WHAT WE GIVE UP, STATED PLAINLY. The 24-hour clock. Gold moves overnight and
GLD is shut. That costs less than it sounds: the method only ever enters
between 09:50 and 10:30 New York, a window that already exists on GLD and
would have had to be invented on a token that never closes. The overnight
move arrives as the opening gap and as the pre-market sweep, both of which
the method already reads.

WHAT WE GAIN THAT CRYPTO COULD NOT HAVE. A real second chart. GLD and IAU
hold the same bars of the same metal, so his "if the two are not aligned on
the five minute, I do not want the trade" applies here in a purer form than
it does to the S&P and the NASDAQ. Measured, they agree on the direction of
the 5-minute candle 86.9% of the time — often enough to be a genuine check
and rarely enough that the other 13% is a filter and not a blockade. IAU is
loaded and never traded: its own 5-minute record is 21% holes.
"""


def main(argv):
    if "--fetch" in argv:
        print("refreshing the cached bars (read-only against both venues)")
        fetch()
        print()
    print("=" * 78)
    print("gold: PAXG/USD (24 hours, crypto endpoints) vs GLD (bell, stock endpoints)")
    print("=" * 78)
    compare()
    print(VERDICT)


if __name__ == "__main__":
    main(sys.argv)
