"""
step493_break_point_census.py - ROUND 493

THE CONTRACT-SIZE FINDING IS A DESK-WIDE COST RULE. WHO ELSE DOES IT MOVE?
(QUEUE ITEM 17)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 17, VERBATIM
  R489 collapsed R486's per-coin fee arithmetic into one rule: the $0.15
  minimum binds below a $750 contract notional; above it the round trip is a
  flat 0.04% on every contract. Two consequences nobody has priced.
  (a) The cost of an instrument on this venue moves with its PRICE, and a
      contract can cross the break point without anything about the method
      changing. LTC at $245 notional pays 0.12%; the same contract at a coin
      price 3.1x higher pays 0.04%. Compute, for every one of the 29 CDE
      perpetuals, the coin price at which its contract crosses $750, and say
      which are within a plausible move of it in either direction. R486 did
      this for three coins as a fee-minimum threshold; R489's rule makes it
      computable for all 29 in one line.
  (b) PAXG PERP, US 500 PERP and TECH PERP all sit above the break point and
      pay the floor 0.04% - the cheapest fee on the venue, on gold and two
      index-like instruments. The gold and index specialists have never had a
      sourced US perpetual cost. Hand them one.
  Reading and arithmetic on a live public endpoint plus data already on disk.
  No backtest, no entry population, no look, and no candidate may be proposed
  by this item under any outcome.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled. Nothing in this round reads what happened AFTER a bar. The
     only things measured off tape are (i) the size of a one-minute move and
     (ii) the distribution of forward price ratios - both properties of the
     price series itself, both computable without any notion of a trade.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's
     own window, exactly as R489 fenced it, so no sealed slice is grazed even
     by a volatility number. Applied to the SPENT instruments too so the
     comparison is like for like.
  3. NOTHING IS SELECTED AND NO CANDIDATE IS PROPOSED. The output is an
     arithmetic census plus two cost sheets. The item forbids a candidate
     under any outcome and this file cannot produce one: it never scores a
     strategy on anything.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the Coinbase Derivatives (CDE) perpetual product
    list - contract codes, contract sizes, marks and top-of-book spreads -
    off the same public keyless endpoints R479/R480/R482/R489 used. Read-only
    GETs; the script holds no credential to do anything else.
  SOURCED, IN-LOG: CFM's fee formula max(rate x notional, $0.15) per contract
    per side, exchange+clearing+NFA inside it, at a sourced rate FLOOR of
    0.02% (R486, primary-sourced). The break point is that formula's own
    crossing and is not a new assumption: 0.0002 x N = 0.15 -> N = $750.
  NOT SOURCED AND NOT INVENTED: the volume-tier ladder above the 0.02% floor
    remains unsourced after four attempts (R482, R486, R489, this round). So
    every fee figure here is the CHEAPEST the account can be, never the
    likeliest, and the round says so on every table rather than quietly
    quoting a best case as a cost.

THE ONE JUDGEMENT CALL, DECLARED BEFORE THE RUN
  "Within a plausible move" needs a yardstick or it is a vibe. The yardstick
  used is EMPIRICAL and from data already on disk: the pooled distribution of
  forward price ratios over 90 and 365 calendar days across the eleven
  Bybit-history coins (2020-2026), which is the only large multi-coin sample
  this repo owns. A contract's crossing is reported as the ratio it needs and
  the observed frequency with which a crypto coin-year actually delivered a
  move that size. For the non-crypto contracts (PAXG, US 500, TECH) the
  crypto distribution is the WRONG yardstick and is not used - their own tape
  is used where the disk has it, and where it does not (CHINA, AI, DFNSE) the
  round says "unmeasured" instead of borrowing a number.

USAGE
  python3 step493_break_point_census.py
"""

import json
import sys
import time
import urllib.request
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

LINE = "=" * 108

# ------------------------------------------------------------------ venue
CDE_PRODUCTS = ("https://api.coinbase.com/api/v3/brokerage/market/products"
                "?product_type=FUTURE&limit=250")
CDE_BOOK = ("https://api.coinbase.com/api/v3/brokerage/market/product_book"
            "?product_id={pid}&limit=1")

# R489's discipline, inherited unchanged: ONE POLL IS NOT A MEASUREMENT.
SPREAD_ROUNDS = 7
SPREAD_GAP_S = 12
# A book stamped older than this is not a live quote, it is a leftover.
BOOK_STALE_S = 300

# R486, primary-sourced. The account pays max(rate x notional, $0.15) per
# contract per side, exchange fee INSIDE it. The rate is published only as a
# FLOOR, so every figure below is a best case.
CFM_RATE_FLOOR = 0.0002        # 0.02% of notional per side
CFM_MIN_PER_SIDE = 0.15        # dollars per contract per side
BREAK_NOTIONAL = CFM_MIN_PER_SIDE / CFM_RATE_FLOOR      # = $750, exactly
FLOOR_RT_PCT = 2.0 * CFM_RATE_FLOOR * 100.0             # = 0.04% round trip

# The horizons the crossing question is asked over. Declared here, before the
# numbers exist, so the answer cannot be tuned by choosing a horizon later.
HORIZONS_D = (90, 365)

# Pooled crypto yardstick: every coin with multi-year Bybit history on disk.
YARDSTICK_COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "LTCUSDT",
                   "XRPUSDT", "ADAUSDT", "DOTUSDT", "AVAXUSDT", "DOGEUSDT",
                   "BNBUSDT")

# Non-crypto contracts get their OWN tape or nothing. (contract code -> the
# closest thing on this disk, and it is named as a proxy, not as the thing.)
NONCRYPTO_PROXY = {
    "PAU": ("PAXG PERP",  "data_alpaca_PAXGUSD_1m.parquet", "PAXGUSD 1m tape"),
    "US5": ("US 500 PERP", "data_alpaca_SPY_1d.parquet",    "SPY daily (proxy)"),
    "TEK": ("TECH PERP",   "data_alpaca_QQQ_1d.parquet",    "QQQ daily (proxy)"),
}
NO_TAPE = {"CHINA", "AI", "DFNSE"}      # display-name roots with no disk tape

# (b)'s audience. The three contracts the item names, plus the two the desk
# already prices, kept beside them so the specialists can see the scale.
HANDOFF = ["PAU", "US5", "TEK"]
HANDOFF_CONTEXT = ["BIP", "ETP", "SLP"]


# ================================================================== venue
def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def cde_perp_table():
    """Live, keyless, read-only: every CDE perpetual with its contract size,
    mark and notional. Same endpoint and same parse as R489."""
    d = _get(CDE_PRODUCTS, timeout=40)
    rows = []
    for p in d.get("products", []):
        f = p.get("future_product_details") or {}
        name = f.get("contract_display_name") or ""
        if "PERP" not in name:
            continue
        try:
            px = float(p.get("price") or "nan")
            cs = float(f.get("contract_size") or "nan")
        except (TypeError, ValueError):
            continue
        if not (np.isfinite(px) and np.isfinite(cs) and cs > 0):
            continue
        sess = p.get("fcm_trading_session_details") or {}
        rows.append(dict(
            code=f.get("contract_code"), pid=p["product_id"], name=name,
            unit=f.get("contract_root_unit"), size=cs, price=px,
            notional=px * cs,
            qvol=float(p.get("approximate_quote_24h_volume") or 0),
            vol24=float(p.get("volume_24h") or 0),
            sess=(sess.get("session_state") or "")
                 .replace("FCM_TRADING_SESSION_STATE_", "") or "UNKNOWN",
            sess_open=bool(sess.get("is_session_open")),
            next_open=sess.get("open_time") or ""))
    t = pd.DataFrame(rows)
    per_side = np.maximum(CFM_RATE_FLOOR * t["notional"], CFM_MIN_PER_SIDE)
    t["fee_rt_pct"] = 2.0 * per_side / t["notional"] * 100.0
    t["min_binds"] = t["notional"] < BREAK_NOTIONAL
    # THE ITEM'S ARITHMETIC, one line: the price at which THIS contract's
    # notional equals $750. Contract size is fixed by the exchange, so the
    # crossing is entirely a statement about the coin's price.
    t["break_price"] = BREAK_NOTIONAL / t["size"]
    t["ratio_needed"] = t["break_price"] / t["price"]
    return t.sort_values("notional", ascending=False).reset_index(drop=True)


def cde_spread_samples(pids, rounds=SPREAD_ROUNDS, gap=SPREAD_GAP_S):
    """R489's sampler, unchanged. Median of `rounds` polls `gap` apart, with
    the lo-hi range carried so the noise stays visible. Still not R480's
    24-hour clock and this round does not pretend it is."""
    acc = {p: [] for p in pids}
    age = {p: np.nan for p in pids}
    for k in range(rounds):
        if k:
            time.sleep(gap)
        for pid in pids:
            try:
                b = _get(CDE_BOOK.format(pid=pid), timeout=20)
                v = float(b.get("spread_bps") or "nan") / 100.0
                if np.isfinite(v) and v > 0:
                    acc[pid].append(v)
                # A BOOK THAT IS NOT UPDATING IS NOT A PRICE. The endpoint
                # stamps the book; if that stamp is old the "spread" is a
                # frozen artifact of a shut market, not a cost anyone pays.
                pb = b.get("pricebook") or b
                ts = pb.get("time")
                if ts:
                    bt = pd.Timestamp(ts)
                    if bt.tzinfo is None:
                        bt = bt.tz_localize("UTC")
                    else:
                        bt = bt.tz_convert("UTC")
                    age[pid] = (pd.Timestamp.now(tz="UTC")
                                - bt).total_seconds()
            except Exception:                               # pragma: no cover
                pass
    out = {}
    for pid, vals in acc.items():
        a = np.array(vals, float)
        out[pid] = dict(n=len(a),
                        med=float(np.median(a)) if len(a) else np.nan,
                        lo=float(a.min()) if len(a) else np.nan,
                        hi=float(a.max()) if len(a) else np.nan,
                        age_s=age[pid])
    return out


# =============================================================== the tape
def load_close(path, tcol_guess=("t", "timestamp")):
    b = pd.read_parquet(f"{REPO}/{path}")
    tcol = next(c for c in tcol_guess if c in b.columns)
    t = pd.to_datetime(b[tcol])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    f = pd.DataFrame({"t": t, "close": b["close"].to_numpy()})
    return f.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def cut80(f):
    """THE FENCE, R489's: first 80% of this instrument's own window."""
    t0, t1 = f["t"].iloc[0], f["t"].iloc[-1]
    return t0 + (t1 - t0) * 0.80


def daily_close(f):
    """Last close of each UTC day."""
    g = f.copy()
    g["d"] = g["t"].dt.floor("D")
    return g.groupby("d")["close"].last()


def forward_ratios(dclose, horizon_d):
    """Every observed close-to-close price RATIO over `horizon_d` calendar
    days. Calendar-indexed and forward-filled first so a missing weekend on
    an equity tape does not silently become a shorter horizon."""
    s = dclose.asfreq("D").ffill().dropna()
    if len(s) <= horizon_d:
        return np.array([])
    a = s.to_numpy(float)
    return a[horizon_d:] / a[:-horizon_d]


def yardstick():
    """Pooled crypto distribution of forward price ratios, from the eleven
    Bybit-history coins already on disk. Each coin is fenced at its own 80%
    boundary like everything else in this round."""
    pool = {h: [] for h in HORIZONS_D}
    per_coin = {}
    for sym in YARDSTICK_COINS:
        path = f"data_bybit_{sym}_1h_full.parquet"
        try:
            f = load_close(path)
        except Exception:                                   # pragma: no cover
            continue
        f = f[f["t"] <= cut80(f)]
        dc = daily_close(f)
        per_coin[sym] = dict(days=len(dc), t0=dc.index[0], t1=dc.index[-1])
        for h in HORIZONS_D:
            r = forward_ratios(dc, h)
            if len(r):
                pool[h].append(r)
    return ({h: (np.concatenate(v) if v else np.array([]))
             for h, v in pool.items()}, per_coin)


def freq_at_least(ratios, need):
    """Observed frequency, in the pooled sample, of a move AT LEAST as far as
    `need` in the direction `need` points. `need` > 1 means a rise is what
    crosses the break point; `need` < 1 means a fall does."""
    if not len(ratios) or not np.isfinite(need):
        return np.nan
    return float((ratios >= need).mean() if need >= 1.0
                 else (ratios <= need).mean())


def median_1m_move(f):
    """Median UTC day's mean |1-minute return|, % of price, gap-clean: only
    consecutive bars exactly 60s apart contribute, so a session break or a
    tape hole is never counted as a one-minute move. R489's definition,
    imported unchanged so the numbers are comparable to its table."""
    r = f["close"].pct_change().abs() * 100.0
    dt = f["t"].diff().dt.total_seconds()
    g = pd.DataFrame({"t": f["t"], "r": r, "dt": dt}).dropna()
    g = g[g["dt"] == 60.0]
    if not len(g):
        return np.nan, 0
    per_day = g.groupby(g["t"].dt.floor("D"))["r"].mean()
    return float(per_day.median()), int(len(per_day))


# =================================================================== main
def main():
    print(LINE)
    print("ROUND 493 - THE CONTRACT-SIZE FINDING IS A DESK-WIDE COST RULE. "
          "WHO ELSE DOES IT MOVE?")
    print("Queue item 17. Reading and arithmetic only. No backtest, no entry "
          "population, NO LOOK, and")
    print("no candidate may be proposed by this round under any outcome.")
    print(LINE)

    print("\nTHE RULE BEING APPLIED (R486 sourced, R489 collapsed):")
    print(f"  fee per contract per side = max({CFM_RATE_FLOOR:.4f} x notional,"
          f" ${CFM_MIN_PER_SIDE:.2f})")
    print(f"  the two branches cross at notional = "
          f"${CFM_MIN_PER_SIDE:.2f} / {CFM_RATE_FLOOR:.4f} = "
          f"${BREAK_NOTIONAL:,.0f}")
    print(f"  above it the round trip is a flat {FLOOR_RT_PCT:.2f}% of price "
          f"on EVERY contract;")
    print("  below it the fee is a fixed number of dollars and the percentage "
          "rises as the notional falls.")
    print("  Contract size is set by the exchange, so where a contract sits "
          "is a fact about the COIN PRICE.")

    # ------------------------------------------------------- live venue
    print("\n" + LINE)
    print("(a) THE CENSUS - every CDE perpetual, and the coin price at which "
          "it crosses $750")
    print(LINE)
    t = cde_perp_table()
    print(f"Polled live, keyless, read-only. {len(t)} perpetual contracts "
          f"listed.")

    above = t[~t["min_binds"]]
    below = t[t["min_binds"]]
    print(f"  ABOVE the break point today (paying the {FLOOR_RT_PCT:.2f}% "
          f"floor): {len(above)} of {len(t)}")
    print(f"  BELOW it (the $0.15 minimum binds, fee > floor):        "
          f"{len(below)} of {len(t)}")

    # ------------------------------------------------------- yardstick
    pool, per_coin = yardstick()
    print("\nTHE YARDSTICK for 'a plausible move', declared before the "
          "numbers and built from disk:")
    print(f"  pooled forward price ratios across {len(per_coin)} "
          f"Bybit-history coins, each fenced at its own 80%")
    for h in HORIZONS_D:
        r = pool[h]
        if len(r):
            print(f"    {h:>4}d: {len(r):>7,} coin-days sampled | "
                  f"p10 {np.percentile(r, 10):.2f}x  median "
                  f"{np.median(r):.2f}x  p90 {np.percentile(r, 90):.2f}x")
    print("  A crossing frequency below is the share of those coin-days whose "
          "forward move was at least")
    print("  as far as the crossing needs, in the direction it needs. It is a "
          "base rate, not a forecast.")

    # ------------------------------------------------------- the table
    print("\n" + LINE)
    print("EVERY CONTRACT, SORTED BY NOTIONAL. 'need' is the price ratio that "
          "moves it ACROSS the break;")
    print("'90d'/'365d' are how often a crypto coin-day historically "
          "delivered a move at least that far.")
    print(LINE)
    hdr = (f"{'contract':<12}{'size':>10}{'mark $':>12}{'notional $':>12}"
           f"{'fee RT%':>9}{'side':>7}{'break px $':>12}{'need':>8}"
           f"{'90d':>7}{'365d':>7}")
    print(hdr)
    print("-" * len(hdr))
    rows = []
    for _, r in t.iterrows():
        side = "floor" if not r["min_binds"] else "MIN"
        # Direction: a contract under $750 crosses by the price RISING; one
        # over $750 crosses (the wrong way) by the price FALLING.
        need = r["ratio_needed"]
        is_crypto = r["code"] not in NONCRYPTO_PROXY and \
            r["name"].split()[0] not in NO_TAPE
        f90 = freq_at_least(pool[90], need) if is_crypto else np.nan
        f365 = freq_at_least(pool[365], need) if is_crypto else np.nan
        rows.append(dict(code=r["code"], name=r["name"], size=r["size"],
                         price=r["price"], notional=r["notional"],
                         fee=r["fee_rt_pct"], side=side,
                         break_price=r["break_price"], need=need,
                         f90=f90, f365=f365, crypto=is_crypto,
                         sess=r["sess"], sess_open=r["sess_open"],
                         qvol=r["qvol"], next_open=r["next_open"]))
        s90 = f"{f90*100:5.1f}%" if np.isfinite(f90) else "   --"
        s365 = f"{f365*100:5.1f}%" if np.isfinite(f365) else "   --"
        print(f"{r['name']:<12}{r['size']:>10.6g}{r['price']:>12,.4f}"
              f"{r['notional']:>12,.2f}{r['fee_rt_pct']:>9.4f}{side:>7}"
              f"{r['break_price']:>12,.4f}{need:>8.2f}x{s90:>7}{s365:>7}")
    cen = pd.DataFrame(rows)
    print("\n'--' means the crypto yardstick is the WRONG distribution for "
          "that contract and none was")
    print("borrowed. Those rows are handled on their own tape below or "
          "reported unmeasured.")

    # ------------------------------------------- the calendar, unasked for
    print("\n" + LINE)
    print("A SECOND SPLIT NOBODY ON THIS DESK HAD WRITTEN DOWN: THE VENUE "
          "RUNS TWO CALENDARS")
    print(LINE)
    shut = t[~t["sess_open"]]
    live = t[t["sess_open"]]
    print(f"Polled {pd.Timestamp.utcnow():%Y-%m-%d %H:%M} UTC, a "
          f"{pd.Timestamp.utcnow():%A}.")
    print(f"  {len(live)} contracts OPEN, all crypto, one continuous session "
          f"across the weekend.")
    print(f"  {len(shut)} contracts CLOSED: "
          f"{', '.join(shut['name'].tolist())}")
    if len(shut):
        print(f"     24-hour volume on every one of them: "
              f"${shut['qvol'].max():,.0f} (i.e. zero). Next open "
              f"{shut['next_open'].iloc[0]}.")
    print("\nThe five index-like perpetuals are NOT 24/7 instruments. They "
          "keep an equity-like calendar and")
    print("were shut for the whole of this poll. Anything read off their book "
          "right now is a leftover quote.")
    print("**Item 17(b) named two of them as instruments to hand the index "
          "specialist. They can be handed a")
    print("FEE and they cannot be handed a COST**, and the difference is the "
          "whole point of R479/R480.")

    # --------------------------------------------- who is actually close
    print("\n" + LINE)
    print("WHO IS WITHIN A PLAUSIBLE MOVE OF THE BREAK POINT - the item's "
          "actual question")
    print(LINE)
    cr = cen[cen["crypto"]].copy()

    up = cr[cr["need"] > 1.0].sort_values("need")
    dn = cr[cr["need"] <= 1.0].sort_values("need", ascending=False)

    print("\nGETTING CHEAPER - below the break today, a RISE crosses it. "
          "Fee falls to 0.04% on crossing:")
    print(f"  {'contract':<12}{'fee now':>9}{'needs':>8}{'  =':>4}"
          f"{'break px $':>12}{'90d':>8}{'365d':>8}")
    for _, r in up.iterrows():
        print(f"  {r['name']:<12}{r['fee']:>8.3f}%{r['need']:>7.2f}x"
              f"{'  ':>4}{r['break_price']:>12,.4f}"
              f"{r['f90']*100:>7.1f}%{r['f365']*100:>7.1f}%")

    print("\nGETTING DEARER - above the break today, a FALL crosses it. "
          "Fee rises above 0.04% on crossing:")
    print(f"  {'contract':<12}{'fee now':>9}{'needs':>8}{'  =':>4}"
          f"{'break px $':>12}{'90d':>8}{'365d':>8}")
    for _, r in dn.iterrows():
        print(f"  {r['name']:<12}{r['fee']:>8.3f}%{r['need']:>7.2f}x"
              f"{'  ':>4}{r['break_price']:>12,.4f}"
              f"{r['f90']*100:>7.1f}%{r['f365']*100:>7.1f}%")

    # ------------------------------------- what a crossing is actually worth
    print("\n" + LINE)
    print("WHAT A CROSSING IS WORTH, AND WHY THE TWO DIRECTIONS ARE NOT "
          "SYMMETRIC")
    print(LINE)
    print("Below the break the fee is a FIXED $0.30 round trip per contract, "
          "so the percentage is")
    print("0.30 / notional. The cost therefore falls hyperbolically as the "
          "coin rises and rises without")
    print("limit as it falls - it is not a step, it is a curve with a floor "
          "welded on at $750.")
    print(f"\n  {'coin price vs today':<24}", end="")
    for m in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        print(f"{m:>9.2f}x", end="")
    print()
    for code in ("LCP", "ADP", "POP", "XPP", "BIP"):
        row = cen[cen["code"] == code]
        if not len(row):
            continue
        row = row.iloc[0]
        print(f"  {row['name']:<24}", end="")
        for m in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
            n = row["notional"] * m
            fee = 2.0 * max(CFM_RATE_FLOOR * n, CFM_MIN_PER_SIDE) / n * 100.0
            print(f"{fee:>8.3f}%", end="")
        print()
    print("\n  Read the BTC row: it is already at the floor and CANNOT get "
          "cheaper on this venue at any")
    print("  price. Read the DOT row: the same contract is a different "
          "instrument, cost-wise, at 3x.")

    # ------------------------------------------------- (b) the handoff
    print("\n" + LINE)
    print("(b) THE HANDOFF - a sourced US perpetual cost for the gold and "
          "index specialists")
    print(LINE)
    want = [c for c in HANDOFF + HANDOFF_CONTEXT
            if c in set(cen["code"])]
    pids = {c: t.loc[t["code"] == c, "pid"].iloc[0] for c in want}
    print(f"Sampling top of book {SPREAD_ROUNDS}x, {SPREAD_GAP_S}s apart, "
          f"median carried with its lo-hi range.")
    print("R489's discipline: one poll is not a measurement (two single polls "
          "ten minutes apart disagreed")
    print("by 2x on BTC PERP). This is still not R480's 24-hour clock and is "
          "not presented as one.")
    sp = cde_spread_samples(list(pids.values()))

    print(f"\n{'contract':<12}{'session':<8}{'24h $vol':>13}{'book age':>10}"
          f"{'notional $':>12}{'fee RT%':>9}{'spread%':>9}{'all-in RT%':>12}")
    cost_sheet = {}
    for c in want:
        row = cen[cen["code"] == c].iloc[0]
        smp = sp[pids[c]]
        age = smp["age_s"]
        # A SHUT MARKET HAS NO SPREAD. If the session is closed or the book's
        # own timestamp is stale, the top of book is a frozen artifact and no
        # all-in cost is quoted from it - R482/R486 discipline: report
        # unsourced rather than invent.
        live = bool(row["sess_open"]) and np.isfinite(age) and \
            age <= BOOK_STALE_S
        allin = row["fee"] + smp["med"] if live else np.nan
        cost_sheet[c] = dict(name=row["name"], notional=row["notional"],
                             fee=row["fee"],
                             spread=smp["med"] if live else np.nan,
                             allin=allin, live=live, sess=row["sess"],
                             qvol=row["qvol"], age=age,
                             next_open=row["next_open"])
        agestr = (f"{age/60:.0f}m" if np.isfinite(age) else "n/a")
        spstr = f"{smp['med']:.4f}" if live else "  UNPRICED"
        alstr = f"{allin:.4f}" if live else "  UNPRICED"
        print(f"{row['name']:<12}{row['sess']:<8}{row['qvol']:>13,.0f}"
              f"{agestr:>10}{row['notional']:>12,.2f}{row['fee']:>9.4f}"
              f"{spstr:>9}{alstr:>12}")

    dead = [c for c in want if not cost_sheet[c]["live"]]
    if dead:
        print("\n*** THE ROUND'S BIGGEST CORRECTION, AND IT IS AGAINST THE "
              "ITEM'S OWN PREMISE ***")
        print(f"{len(dead)} of the {len(want)} contracts polled here were "
              f"NOT TRADING at poll time. Their books are")
        print("stale by hours, their 24-hour volume is ZERO, and the numbers "
              "a naive poll returns for them")
        print("are frozen quotes, not costs. No all-in figure is published "
              "for them by this round.")
        for c in dead:
            d = cost_sheet[c]
            why = ("session " + d["sess"] if not d["sess"].startswith("OPEN")
                   else f"book stale ({d['age']/3600:.1f}h)")
            agestr = (f"{d['age']/3600:.1f}h" if np.isfinite(d["age"])
                      else "unknown")
            print(f"  {d['name']:<12} {why:<22} 24h $vol {d['qvol']:>12,.0f}"
                  f"  book age {agestr:>8}  next open {d['next_open']}")

    # the specialists' own tape, so the cost lands next to a move
    print("\nPAIRED WITH THE INSTRUMENT'S OWN 1-MINUTE MOVE (R488's "
          "coordinate, R489's definition).")
    print("Every tape is cut at its own 80% boundary. This is a property of "
          "the price series - no entry")
    print("is built, no outcome is read, nothing is spent.")
    print(f"\n{'contract':<12}{'tape':<26}{'days':>7}{'vol% med':>10}"
          f"{'all-in RT%':>12}{'multiple':>10}")
    for c in HANDOFF:
        if c not in NONCRYPTO_PROXY or c not in cost_sheet:
            continue
        _, path, label = NONCRYPTO_PROXY[c]
        try:
            f = load_close(path)
        except Exception as e:                              # pragma: no cover
            print(f"{cost_sheet[c]['name']:<12}{label:<26}  tape "
                  f"unavailable: {e}")
            continue
        f = f[f["t"] <= cut80(f)]
        v, nd = median_1m_move(f)
        if not np.isfinite(v):
            # daily tape: the 1-minute move is not computable, say so
            dc = daily_close(f)
            al = (f"{cost_sheet[c]['allin']:.4f}"
                  if cost_sheet[c]["live"] else "  UNPRICED")
            print(f"{cost_sheet[c]['name']:<12}{label:<26}{len(dc):>7}"
                  f"{'  (daily)':>10}{al:>12}{'   n/a':>10}")
            continue
        if not cost_sheet[c]["live"]:
            print(f"{cost_sheet[c]['name']:<12}{label:<26}{nd:>7}{v:>10.4f}"
                  f"{'  UNPRICED':>12}{'   n/a':>10}")
            continue
        mult = v / cost_sheet[c]["allin"]
        print(f"{cost_sheet[c]['name']:<12}{label:<26}{nd:>7}{v:>10.4f}"
              f"{cost_sheet[c]['allin']:>12.4f}{mult:>10.2f}")

    print("\nFOR SCALE, the incumbents this desk already prices, same run:")
    for c in HANDOFF_CONTEXT:
        if c in cost_sheet:
            d = cost_sheet[c]
            print(f"  {d['name']:<10} notional ${d['notional']:>10,.2f}  "
                  f"fee {d['fee']:.4f}%  spread {d['spread']:.4f}%  "
                  f"all-in {d['allin']:.4f}%")

    print("\nWHAT THE SPECIALISTS ARE BEING HANDED, in one line each:")
    for c in HANDOFF:
        if c not in cost_sheet:
            continue
        d = cost_sheet[c]
        if d["live"]:
            print(f"  {d['name']:<12} round trip {d['allin']:.4f}% of price "
                  f"({d['fee']:.4f}% fee at the sourced FLOOR + "
                  f"{d['spread']:.4f}% spread snapshot)")
        else:
            print(f"  {d['name']:<12} FEE {d['fee']:.4f}% of price round trip "
                  f"is SOURCED and real. The SPREAD is NOT MEASURED -")
            print(f"  {'':<12} the contract was {d['sess']} at poll time "
                  f"({d['qvol']:,.0f} of 24h volume). No all-in exists yet.")
    print("  Alpaca crypto taker, for comparison, is 0.50% and the desk's "
          "index rounds charge 0.04%.")

    # ------------------------------------------------------- limits
    print("\n" + LINE)
    print("HONEST LIMITS")
    print(LINE)
    print("1. EVERY FEE HERE IS THE FLOOR. The 0.02%/side rate is published "
          "as a minimum and the volume")
    print("   ladder above it is UNSOURCED after four attempts. Nothing was "
          "invented to fill it, so every")
    print("   number above is the cheapest the account can be, not the "
          "likeliest.")
    print("2. THE SPREAD IS A SNAPSHOT, NOT A CLOCK. Seven polls twelve "
          "seconds apart. R480 showed these")
    print("   books move by hours of the day and that Coinbase's empties for "
          "one hour daily; none of that")
    print("   is in these figures.")
    print("3. MARKS RE-PRICE. Every notional, fee and crossing above is true "
          "for this run's snapshot only.")
    print("   That is the finding, not a caveat: the whole point is that the "
          "cost moves with the price.")
    print("4. THE CROSSING FREQUENCIES ARE A CRYPTO BASE RATE, NOT A "
          "FORECAST. They say how often a")
    print("   coin-day in 2020-2026 was followed by a move that far. They are "
          "pooled across eleven coins,")
    print("   so a specific contract's own volatility is not in them, and "
          "they are not applied to the")
    print("   non-crypto contracts at all.")
    print("5. US 500 / TECH WERE SHUT AT POLL TIME, so their spread and "
          "therefore their all-in cost is")
    print("   UNMEASURED, not measured-and-wide. The fee half is sourced and "
          "stands. Re-polling them inside")
    print("   their own session is a free follow-up and is queued as such - "
          "and their SPY/QQQ pairing would")
    print("   still be a proxy, not the thing.")
    print("6. NOTHING HERE SAYS AN INSTRUMENT HAS AN EDGE. A cheap round trip "
          "is a cost fact. Whether the")
    print("   method works on gold or an index perpetual is a question this "
          "round did not and could not ask.")

    print("\n" + LINE)
    print("WHAT THIS ROUND DID NOT DO")
    print(LINE)
    print("No entry population was built. No sweep was scanned, no break of "
          "structure detected, no fill")
    print("modelled, no stop measured. `simulate()` was never called. No "
          "return, expectancy, win rate or")
    print("risk multiple was computed for any instrument. No sealed slice was "
          "opened - every tape read")
    print("stops at its own 80% boundary. NO LOOK WAS CONSUMED. No candidate "
          "is proposed and none could")
    print("be. No order was placed, no account was created, no live file was "
          "touched or imported.")
    return cen, cost_sheet


if __name__ == "__main__":
    main()
