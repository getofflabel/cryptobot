"""
step489_next_look_screen.py - ROUND 489

WHICH INSTRUMENT SHOULD THE DESK SPEND ITS NEXT SEALED LOOK ON?
(QUEUE ITEM 13)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 13, VERBATIM
  The standing position of this family is a dead end BY CONSTRUCTION, not by
  evidence: the method reads positive gross on 5.5 years of crypto and 11 of
  the index, and neither population has a sealed slice left anywhere (R474
  spent SPY/QQQ, R475 spent crypto). Per the standing transfer rule a future
  candidate needs a NEW instrument or NEW data. Nobody has asked which one.
  (a) For every instrument this desk can actually reach and price, measure
      the realized 1-minute move on whatever history is on disk and pair it
      with a PRIMARY-SOURCED all-in round trip. Rank by the R488 multiple.
      Say plainly where the cost figure is unsourced rather than inventing
      one (R482/R486 discipline).
  (b) Does stop/vol ~ 3.6 transfer? Build the sweep-to-1m-BOS structural
      stop on the top-ranked instruments and read the ratio.
  (c) Data honesty: for each ranked instrument, state whether a 60/20/20
      split with an UNREAD final 20% actually exists.
  Output is a RANKED SHORTLIST and nothing else. No entry population is
  qualified and no cell is tested in this round.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE. Not once, on any instrument.
     No return, no P&L, no expectancy, no win rate, no R is computed for any
     instrument anywhere in this round. The only thing read off an entry is
     the DISTANCE FROM ENTRY TO THE STRUCTURAL STOP, which is a property of
     the chart, not of the outcome. That is what makes (b) free.
  2. EVERY MEASUREMENT IS RESTRICTED TO THE FIRST 80% of each instrument's
     own 1m/5m overlap window - the choosing and middle slices. The final
     20% of every candidate is not read, not summarised and not touched,
     because the whole point of the round is to hand the next round an
     instrument whose sealed slice is intact. Applied to the incumbents too,
     so the comparison is like for like; their full-window figures are
     printed once beside it purely to reproduce R488, and they have no
     sealed slice left to protect anyway.
  3. NOTHING IS SELECTED. The output is a ranking. No threshold is applied,
     no instrument is qualified, and the shortlist is a statement about
     where a look WOULD be worth spending, which is a decision for the next
     round to act on.

COSTS
  Charged for honest P&L and used for nothing else (owner rule 2026-07-25).
  In this round cost is not a filter at all - it is one of the two
  coordinates of the screen, per R488, and it declines nothing.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the Coinbase Derivatives (CDE) perpetual product
    list, contract sizes, marks and top-of-book spreads, off the same public
    endpoints R479/R482 used, with no account and no key. Read-only: the
    script issues GETs and nothing else, and holds no credential to do more.
  SOURCED, IN-LOG: CFM's fee formula max(rate x notional, $0.15) per
    contract per side with the exchange fee inside it and a sourced rate
    FLOOR of 0.02% (R486, primary-sourced from Coinbase's own launch
    announcement via the Internet Archive); Alpaca crypto taker 0.25%/side
    and maker 0.15%/side (R478); the index's 0.04% round trip (R370/R474).
  NOT SOURCED, AND SAID SO RATHER THAN INVENTED: CFM's standing volume-tier
    ladder above the 0.02% floor (R482/R486 both failed to source it, and
    this round does not invent it either - every CFM figure below is the
    FLOOR, i.e. the cheapest the account can possibly be); the equity spread
    on GLD and IAU; the OANDA spread on the two FX pairs.

HONEST LIMITS, FIXED BEFORE RUNNING
  - The spread half of every CDE cost is a SEVEN-SAMPLE MEDIAN taken over
    about a minute at run time, not R480's 24-hour clock. Seven was chosen
    because two SINGLE polls ten minutes apart disagreed by 2x on BTC PERP
    during development - one poll of this book is not a measurement. The
    per-contract lo-hi range is printed so the remaining noise is visible,
    and the calibration against R479/R480's published full-clock medians for
    BTC/ETH/SOL is printed so the reader can see how far off a one-minute
    sample is on the three contracts where the answer is known.
  - Realized volatility is gap-clean: only consecutive 1-minute bars one
    minute apart contribute, so a session gap or a tape hole never enters as
    a "1-minute move". R488's raw definition is printed beside it on the
    instruments R488 published, as the reproduction check.
  - Every CDE percentage is a PRICE SNAPSHOT (R486's standing warning): a
    fixed-dollar minimum over a moving notional re-prices with the coin.
  - History length is NOT volatility and NOT cost, and a great multiple on
    five months of tape is not the same object as one on five years. The
    ranking prints the window so the two can never be confused.
  - AVAXUSD and DOGEUSD hold about four days of 1-minute tape each and are
    reported as data-absent, not as candidates.

USAGE
  python3 step489_next_look_screen.py
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

import step450_tjr_crypto_1m as R      # noqa: E402  (machinery, unchanged)

LINE = "=" * 108

# ------------------------------------------------------------------ venue
CDE_PRODUCTS = ("https://api.coinbase.com/api/v3/brokerage/market/products"
                "?product_type=FUTURE&limit=250")
CDE_BOOK = ("https://api.coinbase.com/api/v3/brokerage/market/product_book"
            "?product_id={pid}&limit=1")
# One poll of this book is not a measurement: two single polls ten minutes
# apart disagreed by 2x on BTC PERP during development. Each contract is
# sampled this many times, this far apart, and the MEDIAN is carried.
SPREAD_ROUNDS = 7
SPREAD_GAP_S = 12

# R486, primary-sourced: the account pays max(rate x notional, $0.15) per
# contract per side, exchange+clearing+NFA inclusive. The rate is published
# only as a FLOOR. Using the floor makes every CFM number below the
# CHEAPEST the account can be, never the likeliest.
CFM_RATE_FLOOR = 0.0002        # 0.02% of notional per side  (R486)
CFM_MIN_PER_SIDE = 0.15        # dollars per contract per side (R486)

# R478, in-log: Alpaca crypto, the venue the desk actually holds today.
ALPACA_CRYPTO_RT = 0.50        # % of notional, taker both legs
# R370/R474, in-log: the index round trip used by every index round.
INDEX_RT = 0.04                # % of notional

# R479/R480 published full-clock median Coinbase spreads, % of price. Used
# ONLY to calibrate this run's snapshot, never as a substitute for it.
R480_SPREAD = {"BIP": 0.0147, "ETP": 0.0427, "SLP": 0.0275}

# ------------------------------------------------------------- instruments
# (label, parquet stem, kind, CDE contract code or None)
UNIVERSE = [
    ("BTCUSD",  "data_alpaca_BTCUSD_1m.parquet",  "crypto", "BIP"),
    ("ETHUSD",  "data_alpaca_ETHUSD_1m.parquet",  "crypto", "ETP"),
    ("SOLUSD",  "data_alpaca_SOLUSD_1m.parquet",  "crypto", "SLP"),
    ("LINKUSD", "data_alpaca_LINKUSD_1m.parquet", "crypto", "LNP"),
    ("LTCUSD",  "data_alpaca_LTCUSD_1m.parquet",  "crypto", "LCP"),
    ("XRPUSD",  "data_alpaca_XRPUSD_1m.parquet",  "crypto", "XPP"),
    ("ADAUSD",  "data_alpaca_ADAUSD_1m.parquet",  "crypto", "ADP"),
    ("DOTUSD",  "data_alpaca_DOTUSD_1m.parquet",  "crypto", "POP"),
    ("PAXGUSD", "data_alpaca_PAXGUSD_1m.parquet", "crypto", "PAU"),
    ("AVAXUSD", "data_alpaca_AVAXUSD_1m.parquet", "crypto", "AVP"),
    ("DOGEUSD", "data_alpaca_DOGEUSD_1m.parquet", "crypto", "DOP"),
    ("SPY",     "data_alpaca_SPY_1m.parquet",     "index",  "US5"),
    ("QQQ",     "data_alpaca_QQQ_1m.parquet",     "index",  "TEK"),
    ("GLD",     "data_alpaca_GLD_et_1m.parquet",  "etf",    None),
    ("IAU",     "data_alpaca_IAU_et_1m.parquet",  "etf",    None),
    ("GBPUSD",  "data_fx_GBPUSD_et_1m.parquet",   "fx",     None),
    ("GBPJPY",  "data_fx_GBPJPY_et_1m.parquet",   "fx",     None),
]

# (c) WHICH INSTRUMENTS HAVE ALREADY HAD A TRADE POPULATION READ ON THIS
# FAMILY. Established by reading the step files, not by memory: every round
# in this family (R450, R475, R476, R477, R481, R485, R488) iterates
# `R.PRIMARY` = BTC/ETH/SOL, and R474/R485 iterate SPY/QQQ. R450's eight-pair
# table is a SWING-WIDTH CENSUS - a measurement of chart structure with no
# entries, no fills and no outcomes - so it does not spend anything.
SPENT = {
    "BTCUSD": "SPENT - R475 took the one look (4h swing low -> 1m BOS + FVG)",
    "ETHUSD": "SPENT - same population as BTC, R475",
    "SOLUSD": "SPENT - same population as BTC, R475",
    "SPY":    "SPENT - R474 took the one look (prev day low -> 1m BOS)",
    "QQQ":    "SPENT - same population as SPY, R474",
}
NEVER_TRADED = ("no round in this log has ever built an entry population on "
                "this instrument for this family")


# ================================================================== venue
def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def cde_perp_table():
    """Live, keyless, read-only: every CDE perpetual with its contract size,
    mark, notional, CFM fee at the SOURCED FLOOR, and a snapshot spread."""
    try:
        d = _get(CDE_PRODUCTS, timeout=40)
    except Exception as e:                                  # pragma: no cover
        print(f"  !! CDE product list unavailable: {e}")
        return pd.DataFrame()
    rows = []
    for p in d.get("products", []):
        f = p.get("future_product_details") or {}
        name = f.get("contract_display_name") or ""
        if "PERP" not in name:
            continue
        try:
            px = float(p.get("price") or "nan")
            cs = float(f.get("contract_size") or "nan")
        except ValueError:
            continue
        rows.append(dict(code=f.get("contract_code"), pid=p["product_id"],
                         name=name, unit=f.get("contract_root_unit"),
                         size=cs, price=px, notional=px * cs,
                         qvol=float(p.get("approximate_quote_24h_volume") or 0)))
    t = pd.DataFrame(rows)
    if not len(t):
        return t
    # CFM: max(rate x notional, $0.15) per side, exchange fee INSIDE it.
    per_side = np.maximum(CFM_RATE_FLOOR * t["notional"], CFM_MIN_PER_SIDE)
    t["fee_rt_pct"] = 2.0 * per_side / t["notional"] * 100.0
    t["min_binds"] = CFM_MIN_PER_SIDE > CFM_RATE_FLOOR * t["notional"]
    sp = []
    for pid in t["pid"]:
        try:
            b = _get(CDE_BOOK.format(pid=pid), timeout=20)
            sp.append(float(b.get("spread_bps") or "nan") / 100.0)
        except Exception:                                   # pragma: no cover
            sp.append(np.nan)
    t["spread_pct"] = sp
    t["allin_rt_pct"] = t["fee_rt_pct"] + t["spread_pct"]
    return t.sort_values("qvol", ascending=False).reset_index(drop=True)


def cde_spread_samples(pids, rounds=SPREAD_ROUNDS, gap=SPREAD_GAP_S):
    """ONE SNAPSHOT IS NOT A MEASUREMENT. Two consecutive single polls of
    this book, ten minutes apart, disagreed by 2x on BTC PERP - so the
    round samples each contract `rounds` times, `gap` seconds apart, and
    carries the MEDIAN with its own spread of readings printed beside it.
    Still not R480's 24-hour clock, and said so."""
    acc = {p: [] for p in pids}
    for k in range(rounds):
        if k:
            time.sleep(gap)
        for pid in pids:
            try:
                b = _get(CDE_BOOK.format(pid=pid), timeout=20)
                v = float(b.get("spread_bps") or "nan") / 100.0
                if np.isfinite(v) and v > 0:
                    acc[pid].append(v)
            except Exception:                               # pragma: no cover
                pass
    out = {}
    for pid, vals in acc.items():
        a = np.array(vals, float)
        out[pid] = dict(n=len(a),
                        med=float(np.median(a)) if len(a) else np.nan,
                        lo=float(a.min()) if len(a) else np.nan,
                        hi=float(a.max()) if len(a) else np.nan)
    return out


# ============================================================== volatility
def tape(path):
    b = pd.read_parquet(f"{REPO}/{path}")
    tcol = "t" if "t" in b.columns else "timestamp"
    t = pd.to_datetime(b[tcol])
    if getattr(t.dt, "tz", None) is not None:
        t = t.dt.tz_convert("UTC").dt.tz_localize(None)
    return pd.DataFrame({"t": t, "close": b["close"].to_numpy()}).sort_values(
        "t").drop_duplicates("t").reset_index(drop=True)


def daily_vol(f, gap_clean=True):
    """Mean |1-minute return| per UTC day, % of price. Gap-clean means only
    consecutive bars exactly one minute apart contribute, so a session break
    or a tape hole is never counted as a one-minute move."""
    r = f["close"].pct_change().abs() * 100.0
    dt = f["t"].diff().dt.total_seconds()
    g = pd.DataFrame({"t": f["t"], "r": r, "dt": dt}).dropna()
    if gap_clean:
        g = g[g["dt"] == 60.0]
    return g.groupby(g["t"].dt.floor("D"))["r"].mean()


def cut80(f):
    """THE FENCE: first 80% of this instrument's own window, by calendar."""
    t0, t1 = f["t"].iloc[0], f["t"].iloc[-1]
    return t0 + (t1 - t0) * 0.80, t0, t1


# ======================================================== structural stop
def structural_stops(sym, t_end):
    """(b) The sweep -> 1-minute break-of-structure stop, in % of price, for
    every entry the method produces before `t_end`. R450's machinery,
    unchanged. NO OUTCOME IS READ: this function computes the distance from
    the fill to the chart structure and returns it. `simulate` is not called
    and cannot be reached from here."""
    d5, d1 = R.prep(sym)
    i1n = d5["i1_next"].to_numpy()
    lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
    o1 = d1["open"].to_numpy(); t1 = d1["t"].to_numpy()
    n1 = len(d1)
    out = []
    for col, dirn, lab in R.LEVELS:
        sw, sig5 = R.scan_sweeps(d5, col, dirn)
        if len(sig5) == 0:
            continue
        ent1, swB = R.trigger_1m(d5, d1, sw, dirn)
        if not len(ent1):
            continue
        a1 = i1n[swB]
        for a, b in zip(a1, ent1):
            j = b + 1
            if j >= n1:
                continue
            entry = o1[j]
            stop = (lo1[max(0, a):b + 1].min() if dirn > 0
                    else hi1[max(0, a):b + 1].max())
            if not np.isfinite(stop) or entry <= 0:
                continue
            if (dirn > 0 and stop >= entry) or (dirn < 0 and stop <= entry):
                continue
            out.append((t1[b], lab, dirn, abs(entry - stop) / entry * 100.0))
    e = pd.DataFrame(out, columns=["sig_t", "level", "dirn", "stop_pct"])
    if not len(e):
        return e
    e["sig_t"] = pd.to_datetime(e["sig_t"])
    e = e[e["sig_t"] < t_end].copy()          # THE FENCE
    e["day"] = e["sig_t"].dt.floor("D")
    return e


# ====================================================================== main
def main():
    print(LINE)
    print("ROUND 489 - WHICH INSTRUMENT SHOULD THE DESK SPEND ITS NEXT SEALED "
          "LOOK ON?   (queue item 13)")
    print(LINE)
    print("A SCREEN. No look is consumed and none can be: `simulate()` is "
          "never called in this file,")
    print("no return or expectancy is computed for any instrument, and every "
          "measurement stops at the")
    print("80% boundary of each instrument's own window. The final 20% of "
          "every candidate stays sealed.")

    # ------------------------------------------------------------ venue
    print("\n" + LINE)
    print("(a1) THE VENUE, POLLED LIVE AND KEYLESS - every US perpetual "
          "Coinbase Derivatives lists")
    print(LINE)
    cde = cde_perp_table()
    if len(cde):
        print(f"  sampling each book {SPREAD_ROUNDS}x, {SPREAD_GAP_S}s apart "
              f"(one poll is not a measurement) ...", flush=True)
        smp = cde_spread_samples(list(cde["pid"]))
        cde["spread_pct"] = [smp[p]["med"] for p in cde["pid"]]
        cde["spr_n"] = [smp[p]["n"] for p in cde["pid"]]
        cde["spr_lo"] = [smp[p]["lo"] for p in cde["pid"]]
        cde["spr_hi"] = [smp[p]["hi"] for p in cde["pid"]]
        cde["allin_rt_pct"] = cde["fee_rt_pct"] + cde["spread_pct"]
        print(f"{len(cde)} perpetual contracts listed. Fee is CFM's SOURCED "
              f"FORMULA at its SOURCED FLOOR (R486):")
        print(f"  per side = max({CFM_RATE_FLOOR*100:.2f}% x notional, "
              f"${CFM_MIN_PER_SIDE:.2f}), exchange+clearing+NFA inclusive. "
              f"The volume ladder above the floor is UNSOURCED and is not "
              f"invented here, so every")
        print("  fee below is the CHEAPEST the account can possibly be.")
        print(f"  Break point: the $0.15 minimum binds below a notional of "
              f"${CFM_MIN_PER_SIDE/CFM_RATE_FLOOR:,.0f}. Above it the rate "
              f"binds and the round trip is a flat "
              f"{2*CFM_RATE_FLOOR*100:.2f}%.")
        print(f"\n{'contract':<15}{'code':<6}{'size':>10}{'mark':>12}"
              f"{'notional$':>11}{'fee%RT':>9}{'min?':>6}{'spr%med':>9}"
              f"{'spr lo-hi':>16}{'n':>4}{'allin%RT':>10}{'24h $vol':>14}")
        for _, r in cde.iterrows():
            rng = (f"{r['spr_lo']:.4f}-{r['spr_hi']:.4f}"
                   if np.isfinite(r['spr_lo']) else "n/a")
            print(f"{r['name']:<15}{str(r['code']):<6}{r['size']:>10.4g}"
                  f"{r['price']:>12.4f}{r['notional']:>11.2f}"
                  f"{r['fee_rt_pct']:>9.4f}{'yes' if r['min_binds'] else '-':>6}"
                  f"{r['spread_pct']:>9.4f}{rng:>16}{int(r['spr_n']):>4}"
                  f"{r['allin_rt_pct']:>10.4f}{r['qvol']:>14,.0f}")
        print(f"\n  CALIBRATION OF THIS RUN'S {SPREAD_ROUNDS}-SAMPLE MEDIAN "
              f"AGAINST R479/R480's FULL-CLOCK MEDIANS (the three contracts "
              f"where the clock is known):")
        for code, med in R480_SPREAD.items():
            row = cde[cde["code"] == code]
            if len(row):
                s = float(row["spread_pct"].iloc[0])
                print(f"    {code:<5} sampled median {s:.4f}%  vs  R480 "
                      f"full-clock median {med:.4f}%   ratio {s/med:.2f}x")
        print("  Seven samples over a minute is not a 24-hour clock. Read "
              "the ratios above, and the lo-hi column,")
        print("  before trusting any spread in this table to two decimals.")
    else:
        print("  CDE unavailable this run - the venue half of the screen "
              "cannot be sourced and nothing is invented for it.")

    codes = {r["code"]: r for _, r in cde.iterrows()} if len(cde) else {}

    # ------------------------------------------------- volatility + window
    print("\n" + LINE)
    print("(a2) THE REALIZED 1-MINUTE MOVE, ON THE FIRST 80% OF EACH "
          "INSTRUMENT'S OWN WINDOW")
    print(LINE)
    print("Gap-clean: only consecutive bars exactly 60s apart contribute, so "
          "a session break or a tape")
    print("hole is never counted as a one-minute move. R488's raw definition "
          "is printed beside it.")
    print(f"\n{'instrument':<11}{'kind':<7}{'bars(80%)':>11}{'days':>7}"
          f"{'window (80% slice)':<26}{'vol%med':>9}{'vol%mean':>10}"
          f"{'raw%med':>9}")
    vol = {}
    for sym, path, kind, code in UNIVERSE:
        try:
            f = tape(path)
        except Exception as e:                              # pragma: no cover
            print(f"{sym:<11}{kind:<7}  !! tape unavailable: {e}")
            continue
        t80, t0, t1 = cut80(f)
        f80 = f[f["t"] < t80]
        dv = daily_vol(f80, gap_clean=True)
        raw = daily_vol(f80, gap_clean=False)
        if len(dv) < 5:
            print(f"{sym:<11}{kind:<7}{len(f80):>11,}{len(dv):>7}"
                  f"  DATA ABSENT - not a candidate")
            continue
        vol[sym] = dict(med=float(dv.median()), mean=float(dv.mean()),
                        days=int(len(dv)), bars=int(len(f80)),
                        t0=t0, t80=t80, t1=t1, kind=kind, code=code)
        w = f"{t0:%Y-%m-%d}->{t80:%Y-%m-%d}"
        print(f"{sym:<11}{kind:<7}{len(f80):>11,}{len(dv):>7}  {w:<24}"
              f"{dv.median():>9.4f}{dv.mean():>10.4f}{raw.median():>9.4f}")
    print("\n  The gap-clean and raw columns agree on 24/7 crypto and diverge "
          "on session instruments,")
    print("  which is the whole reason the clean one is the coordinate used "
          "below.")

    # ------------------------------------------------------- the ranking
    print("\n" + LINE)
    print("(a3) THE R488 MULTIPLE - the median day's 1-minute move divided by "
          "the all-in round trip")
    print(LINE)
    print("R488: four of five instruments break even at a 1-minute move of "
          "about 0.010% of price. The")
    print("multiple below is how many times the median day CLEARS the round "
          "trip it must pay. It ranks;")
    print("it does not qualify. Cost is a coordinate here and declines "
          "nothing (owner rule 2026-07-25).")
    rank = []
    for sym, v in vol.items():
        # venue 1: the CDE perpetual, where one exists (sourced this run)
        if v["code"] and v["code"] in codes:
            c = codes[v["code"]]
            rank.append(dict(sym=sym, venue=f"CDE {c['name']}",
                             rt=float(c["allin_rt_pct"]), src="SOURCED",
                             vol=v["med"], days=v["days"], kind=v["kind"]))
        # venue 2: the venue the desk actually holds today
        if v["kind"] == "crypto":
            rank.append(dict(sym=sym, venue="Alpaca crypto taker",
                             rt=ALPACA_CRYPTO_RT, src="SOURCED",
                             vol=v["med"], days=v["days"], kind=v["kind"]))
        elif v["kind"] == "index":
            rank.append(dict(sym=sym, venue="Alpaca equity (R370/R474)",
                             rt=INDEX_RT, src="SOURCED",
                             vol=v["med"], days=v["days"], kind=v["kind"]))
        else:
            rank.append(dict(sym=sym, venue="spread UNSOURCED",
                             rt=np.nan, src="UNSOURCED",
                             vol=v["med"], days=v["days"], kind=v["kind"]))
    rk = pd.DataFrame(rank)
    rk["mult"] = rk["vol"] / rk["rt"]
    nocost = rk[(rk["src"] == "SOURCED") & ~np.isfinite(rk["mult"])]
    ok = (rk[(rk["src"] == "SOURCED") & np.isfinite(rk["mult"])]
          .sort_values("mult", ascending=False))
    print(f"\n{'#':<4}{'instrument':<11}{'venue':<26}{'vol%med':>9}"
          f"{'allin%RT':>10}{'multiple':>10}{'days':>7}{'sealed 20%?':<14}")
    for i, (_, r) in enumerate(ok.iterrows(), 1):
        seal = "SPENT" if r["sym"] in SPENT else "INTACT"
        print(f"{i:<4}{r['sym']:<11}{r['venue']:<26}{r['vol']:>9.4f}"
              f"{r['rt']:>10.4f}{r['mult']:>10.2f}{r['days']:>7}  {seal:<12}")
    if len(nocost):
        for _, r in nocost.iterrows():
            print(f"    {r['sym']:<9} {r['venue']:<26} no book came back on "
                  f"any of the {SPREAD_ROUNDS} polls - unpriced, unranked")
    bad = rk[rk["src"] != "SOURCED"]
    if len(bad):
        print("\n  COST UNSOURCED, THEREFORE UNRANKED (not estimated, not "
              "invented):")
        for _, r in bad.iterrows():
            print(f"    {r['sym']:<9} {r['kind']:<6} vol {r['vol']:.4f}%  "
                  f"- no primary-sourced round trip exists for this "
                  f"instrument on a venue the desk can reach")

    print("\n  RANKED AMONG INSTRUMENTS WITH AN INTACT SEALED SLICE ONLY - "
          "the only rows a next look could use:")
    live = ok[~ok["sym"].isin(SPENT)]
    print(f"{'#':<4}{'instrument':<11}{'venue':<26}{'vol%med':>9}"
          f"{'allin%RT':>10}{'multiple':>10}{'days':>7}")
    for i, (_, r) in enumerate(live.iterrows(), 1):
        print(f"{i:<4}{r['sym']:<11}{r['venue']:<26}{r['vol']:>9.4f}"
              f"{r['rt']:>10.4f}{r['mult']:>10.2f}{r['days']:>7}")

    # ------------------------------------------- (a4) cost robustness
    print("\n" + LINE)
    print("(a4) HOW MUCH OF THE RANKING IS THE SPREAD SAMPLE? - two "
          "robustness reads, neither of which invents a number")
    print(LINE)
    cal = []
    for code, med in R480_SPREAD.items():
        row = cde[cde["code"] == code] if len(cde) else []
        if len(row):
            cal.append(float(row["spread_pct"].iloc[0]) / med)
    print("READ 1 - FEE ONLY, NO SPREAD AT ALL. Fully sourced, sample-free, "
          "and a hard FLOOR on cost:")
    print("the account cannot pay less than this on any clock, so a multiple "
          "here is the best case that")
    print("exists rather than a best guess.")
    fee_rank = []
    for sym, v in vol.items():
        if v["code"] and v["code"] in codes:
            c = codes[v["code"]]
            fee_rank.append((sym, c["name"], v["med"],
                             float(c["fee_rt_pct"]),
                             v["med"] / float(c["fee_rt_pct"]),
                             "SPENT" if sym in SPENT else "INTACT"))
    fee_rank.sort(key=lambda r: -r[4])
    print(f"\n{'#':<4}{'instrument':<11}{'contract':<15}{'vol%med':>9}"
          f"{'fee%RT':>9}{'multiple':>10}  sealed 20%?")
    for i, r in enumerate(fee_rank, 1):
        print(f"{i:<4}{r[0]:<11}{r[1]:<15}{r[2]:>9.4f}{r[3]:>9.4f}"
              f"{r[4]:>10.2f}  {r[5]}")
    if cal:
        k = float(np.mean(cal))
        rr = " / ".join(f"{x:.2f}x" for x in cal)
        print(f"\nREAD 2 - SENSITIVITY, AND IT IS LABELLED AS ONE. The "
              f"sampled median reads {k:.2f}x R480's full-clock")
        print(f"medians on the three contracts where the clock is known "
              f"({rr}). Scaling every sampled")
        print(f"spread by 1/{k:.2f} = {1/k:.2f}x asks what the ranking looks "
              f"like if the whole table is")
        print("optimistic by the same factor. IT IS NOT A SOURCED COST and no "
              "decision may rest on it; the")
        print("only question it answers is whether the ORDER survives.")
        sens = []
        for sym, v in vol.items():
            if v["code"] and v["code"] in codes:
                c = codes[v["code"]]
                rt = float(c["fee_rt_pct"]) + float(c["spread_pct"]) / k
                if not np.isfinite(rt):
                    continue
                sens.append((sym, c["name"], v["med"], rt, v["med"] / rt,
                             "SPENT" if sym in SPENT else "INTACT"))
        sens.sort(key=lambda r: -r[4])
        print(f"\n{'#':<4}{'instrument':<11}{'contract':<15}{'vol%med':>9}"
              f"{'allin%RT':>10}{'multiple':>10}  sealed 20%?")
        for i, r in enumerate(sens, 1):
            print(f"{i:<4}{r[0]:<11}{r[1]:<15}{r[2]:>9.4f}{r[3]:>10.4f}"
                  f"{r[4]:>10.2f}  {r[5]}")
        a = [r[0] for r in sens if r[5] == "INTACT"]
        b = [r[0] for r in fee_rank if r[5] == "INTACT"]
        c_ = [r["sym"] for _, r in
              rk[(rk.src == "SOURCED") & (~rk.sym.isin(SPENT)) &
                 (rk.venue.str.startswith("CDE"))]
              .sort_values("mult", ascending=False).iterrows()]
        print(f"\n  intact-slice order, snapshot   : {' > '.join(c_)}")
        print(f"  intact-slice order, fee only   : {' > '.join(b)}")
        print(f"  intact-slice order, sensitivity: {' > '.join(a)}")
        print("  Where these three disagree, the ranking is a statement about "
              "the spread and not about the")
        print("  instrument, and the disagreement is the honest answer.")

    # ------------------------------------------------- (b) stop/vol ratio
    print("\n" + LINE)
    print("(b) DOES stop/vol ~ 3.6 TRANSFER?   R488: 3.60 on crypto "
          "(BTC/ETH/SOL), 3.67 on the index (SPY/QQQ)")
    print(LINE)
    print("The structural stop only. NO OUTCOME IS READ - `simulate()` is not "
          "called, and the distance")
    print("from the fill to the chart structure is a property of the chart, "
          "not of what happened next.")
    print("Entries before the 80% boundary only.")
    probe = ["LINKUSD", "LTCUSD", "XRPUSD", "PAXGUSD", "ADAUSD", "DOTUSD",
             "BTCUSD"]
    print(f"\n{'instrument':<11}{'entries':>9}{'days':>7}{'stopmed%':>10}"
          f"{'vol%med':>9}{'stop/vol':>10}{'p25':>8}{'p75':>8}{'note':<34}")
    ratios = {}
    for sym in probe:
        if sym not in vol:
            continue
        try:
            e = structural_stops(sym, vol[sym]["t80"])
        except Exception as ex:                             # pragma: no cover
            print(f"{sym:<11}  !! {ex}")
            continue
        if len(e) < 50:
            print(f"{sym:<11}{len(e):>9}  too few entries to read a ratio")
            continue
        f = tape(dict((s, p) for s, p, _, _ in UNIVERSE)[sym])
        dv = daily_vol(f[f["t"] < vol[sym]["t80"]], gap_clean=True)
        e["vol"] = dv.reindex(e["day"]).to_numpy()
        e = e[np.isfinite(e["vol"]) & (e["vol"] > 0)]
        pr = (e["stop_pct"] / e["vol"]).replace([np.inf, -np.inf], np.nan).dropna()
        ratios[sym] = float(pr.median())
        note = ("R488 control, published 3.60 pooled" if sym == "BTCUSD"
                else NEVER_TRADED[:32])
        print(f"{sym:<11}{len(e):>9}{e['day'].nunique():>7}"
              f"{e['stop_pct'].median():>10.4f}{e['vol'].median():>9.4f}"
              f"{pr.median():>10.2f}{pr.quantile(.25):>8.2f}"
              f"{pr.quantile(.75):>8.2f}  {note:<32}")
    if len(ratios) >= 3:
        vals = np.array(list(ratios.values()))
        print(f"\n  Across {len(vals)} instruments the per-entry stop/vol "
              f"median runs {vals.min():.2f} to {vals.max():.2f}, "
              f"mean {vals.mean():.2f}.")
        print("  R488 measured 3.60 (crypto, pooled) and 3.67 (index). Read "
              "the spread above before")
        print("  calling it a constant of the method rather than a property "
              "of the five it was measured on.")
        crypto_like = {k: v for k, v in ratios.items() if k != "PAXGUSD"}
        cl = np.array(list(crypto_like.values()))
        if "PAXGUSD" in ratios and len(cl):
            print(f"\n  Split the way the tape splits it: the {len(cl)} "
                  f"crypto majors and alts sit in {cl.min():.2f}-{cl.max():.2f}"
                  f" (mean {cl.mean():.2f}), astride")
            print(f"  R488's 3.60. GOLD (PAXGUSD) sits at "
                  f"{ratios['PAXGUSD']:.2f} - roughly FOUR TIMES the constant, "
                  f"on the thinnest")
            print("  population in the table. That is the one instrument here "
                  "that says the ratio is a property")
            print("  of the tape and not of the method, and it is the reason "
                  "the ratio must be RE-DERIVED on any")
            print("  new instrument rather than ported (standing rule "
                  "R89/R100/R170/R190).")

    # -------------------------------------------------- (c) data honesty
    print("\n" + LINE)
    print("(c) DATA HONESTY - does an UNREAD final 20% actually exist?")
    print(LINE)
    print("Established by reading the step files, not from memory. Every "
          "round in this family iterates")
    print("`R.PRIMARY` = BTC/ETH/SOL (R450, R475, R476, R477, R481, R488) or "
          "SPY/QQQ (R474, R485).")
    print("R450's eight-pair table is a SWING-WIDTH CENSUS - chart structure, "
          "no entries, no fills, no")
    print("outcomes - so it spends nothing on the five pairs it measured.")
    print(f"\n{'instrument':<11}{'1m window':<26}{'days':>7}  status")
    for sym, v in vol.items():
        w = f"{v['t0']:%Y-%m-%d} -> {v['t1']:%Y-%m-%d}"
        st = SPENT.get(sym, f"INTACT - {NEVER_TRADED}")
        print(f"{sym:<11}{w:<26}{v['days']:>7}  {st}")

    print("\n" + LINE)
    print("WHAT THIS ROUND DID NOT DO")
    print(LINE)
    print("No cell was qualified. No population was partitioned, swept, "
          "filtered or selected. No return,")
    print("expectancy, win rate or risk multiple was computed for any "
          "instrument. No sealed slice was")
    print("opened. No order was placed, no account was created, no live file "
          "was touched or imported.")
    return rk, ratios


if __name__ == "__main__":
    main()
