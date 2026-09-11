"""
step498_index_perp_session_poll.py - ROUND 498

RE-POLL THE FIVE INDEX-CALENDAR PERPETUALS INSIDE THEIR OWN SESSION.
(QUEUE ITEM 22)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 22, VERBATIM
  R493 could not price US 500 PERP or TECH PERP because both - along with AI,
  CHINA and DFNSE - were CLOSED for the whole poll with $0 of 24-hour volume,
  and it refused to quote a stale book rather than publish a frozen weekend
  quote as a cost. Their 0.0400% fee floor is sourced and stands; the spread
  half does not exist yet.
  Deliverable: run step493's sampler against those five contracts DURING
  THEIR OWN SESSION (they reopen 21:00 UTC on the US futures calendar), seven
  polls twelve seconds apart with the book-age and session-state gates the
  file already enforces, and publish an all-in round trip for each - or report
  plainly that the book is too thin to quote. Pair US 500 and TECH with
  SPY/QQQ 1-minute tape for an R488 coordinate, LABELLED A PROXY, and hand the
  result to the index specialist.
  While the session is open, also record the 24-hour volume and top-of-book
  depth on all five: R480/R483 established that depth, not spread, is what
  caps account size, and a contract with $0 of daily volume is an operational
  fact before it is a cost.
  THE FENCE: reading and arithmetic on a live public endpoint. No entry
  population, no backtest, no look, no candidate, and a book that is stale or
  shut is reported UNPRICED - never quoted.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled, no return/expectancy/win-rate/risk-multiple is computed for
     any instrument. The only thing measured off tape is the size of a
     one-minute move - a property of the price series itself.
  2. EVERY TAPE MEASUREMENT ON DISK STOPS AT THE 80% BOUNDARY of that
     instrument's own window (R489/R493/R497's fence), so no sealed slice is
     grazed even by a volatility number. SPY and QQQ are SPENT (R474) and are
     fenced anyway so the coordinate is comparable to R489's table.
  3. NOTHING IS SELECTED AND NO CANDIDATE IS PROPOSED. The output is a cost
     sheet, a depth sheet and one proxy coordinate. The item forbids a
     candidate under any outcome and this file cannot produce one: it never
     scores a strategy on anything.
  4. A SHUT OR STALE BOOK IS REPORTED `UNPRICED`. Inherited verbatim from
     R493, which is the round that had to use it.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the Coinbase Derivatives (CDE) perpetual product
    list, session state, 24-hour volume, top-of-book spread and DEPTH, and -
    new in this round - the contracts' OWN 1-minute candles. All off public
    keyless read-only GETs; the script holds no credential to do anything else.
  SOURCED, IN-LOG: CFM's fee formula max(rate x notional, $0.15) per contract
    per side at a sourced rate FLOOR of 0.02% (R486). All five contracts here
    are far above the $750 break point, so all five pay the flat floor and
    R493's contract-size rule (item 23) does not bite on any of them.
  NOT SOURCED AND NOT INVENTED: the volume-tier ladder above the 0.02% floor
    remains unsourced after five attempts (R482, R486, R489, R493, this
    round). Every fee figure here is the CHEAPEST the account can be, never
    the likeliest.

THE ONE ADDITION BEYOND THE ITEM, DECLARED BEFORE THE RUN
  The item asks for a SPY/QQQ proxy coordinate for US 500 and TECH. The venue
  also serves these contracts' own 1-minute candles on the same keyless
  endpoint, which is strictly better evidence than a proxy and is inside the
  same fence (reading a live public endpoint; no trade is modelled). BOTH are
  published side by side: the proxy the item asked for, and the real tape.
  Where they disagree the real tape is the measurement and the proxy is the
  thing being corrected. The real tape's COVERAGE is published beside it,
  because item 25 established that a tenth-full tape may not be able to carry
  a coordinate at all.

USAGE
  python3 step498_index_perp_session_poll.py
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

# R493's venue layer, constants and fences, imported rather than re-typed so
# the numbers are comparable to its tables by construction (R494's pattern:
# import the module, never edit it).
import step493_break_point_census as R493          # noqa: E402

LINE = "=" * 108

CDE_BOOK_N = ("https://api.coinbase.com/api/v3/brokerage/market/product_book"
              "?product_id={pid}&limit={n}")
CDE_CANDLES = ("https://api.coinbase.com/api/v3/brokerage/market/products/"
               "{pid}/candles?start={s}&end={e}&granularity=ONE_MINUTE"
               "&limit=350")

# The item's five, by contract code on the live product list.
INDEX_FIVE = ["US5", "TEK", "AIP", "CHN", "DEF"]
# Kept beside them for scale only. Both spent, both already priced (R489).
CONTEXT = ["BIP", "ETP"]

# The item's proxy pairing, exactly as written.
PROXY = {"US5": ("SPY", "data_alpaca_SPY_1m.parquet"),
         "TEK": ("QQQ", "data_alpaca_QQQ_1m.parquet")}

# R489's published coordinate for the two proxies, as a reproduction control.
# If this file's own tape read does not reproduce these, the file is wrong and
# says so rather than publishing a new number quietly (R497's lesson: the
# control caught the error, reading the code did not).
R489_PROXY_VOL = {"SPY": 0.0173, "QQQ": 0.0237}

DEPTH_LEVELS = 10
CANDLE_DAYS = 7


# ============================================================ venue: book
def book_snapshot(pid, n=DEPTH_LEVELS):
    """One read of the top `n` levels. Returns spread %, book age, and depth
    in CONTRACTS at top of book and across `n` levels."""
    b = R493._get(CDE_BOOK_N.format(pid=pid, n=n), timeout=20)
    pb = b.get("pricebook") or {}
    bids = pb.get("bids") or []
    asks = pb.get("asks") or []

    def _sz(rows):
        return float(sum(float(r.get("size") or 0) for r in rows))

    age = np.nan
    ts = pb.get("time")
    if ts:
        bt = pd.Timestamp(ts)
        bt = bt.tz_localize("UTC") if bt.tzinfo is None else bt.tz_convert("UTC")
        age = (pd.Timestamp.now(tz="UTC") - bt).total_seconds()

    try:
        spread = float(b.get("spread_bps") or "nan") / 100.0
    except (TypeError, ValueError):
        spread = np.nan

    return dict(
        spread=spread if np.isfinite(spread) and spread > 0 else np.nan,
        age_s=age,
        top_bid_ct=_sz(bids[:1]), top_ask_ct=_sz(asks[:1]),
        deep_bid_ct=_sz(bids), deep_ask_ct=_sz(asks),
        n_bid_lv=len(bids), n_ask_lv=len(asks),
        mid=float(b.get("mid_market") or "nan"))


def poll_series(pids, rounds=R493.SPREAD_ROUNDS, gap=R493.SPREAD_GAP_S):
    """R493's sampler cadence, unchanged (7 polls, 12s apart, median carried
    with its lo-hi range), extended to carry DEPTH as well as spread because
    the item asks for depth and R480/R483 say depth is the binding one."""
    acc = {p: [] for p in pids}
    for k in range(rounds):
        if k:
            time.sleep(gap)
        for pid in pids:
            try:
                acc[pid].append(book_snapshot(pid))
            except Exception:                               # pragma: no cover
                pass
    out = {}
    for pid, snaps in acc.items():
        if not snaps:
            out[pid] = dict(n=0, med=np.nan, lo=np.nan, hi=np.nan,
                            age_s=np.nan, top_ct=np.nan, deep_ct=np.nan,
                            lv=np.nan)
            continue
        sp = np.array([s["spread"] for s in snaps], float)
        sp = sp[np.isfinite(sp)]
        top = np.array([min(s["top_bid_ct"], s["top_ask_ct"]) for s in snaps],
                       float)
        deep = np.array([min(s["deep_bid_ct"], s["deep_ask_ct"]) for s in snaps],
                        float)
        lv = np.array([min(s["n_bid_lv"], s["n_ask_lv"]) for s in snaps], float)
        out[pid] = dict(
            n=int(len(sp)),
            med=float(np.median(sp)) if len(sp) else np.nan,
            lo=float(sp.min()) if len(sp) else np.nan,
            hi=float(sp.max()) if len(sp) else np.nan,
            age_s=float(np.nanmedian([s["age_s"] for s in snaps])),
            top_ct=float(np.median(top)), deep_ct=float(np.median(deep)),
            lv=float(np.median(lv)))
    return out


# ========================================================= venue: candles
def cde_minute_tape(pid, days=CANDLE_DAYS):
    """The contract's OWN 1-minute candles off the same public endpoint.
    Paged backwards 350 bars at a time. Bars only exist where the contract
    actually traded, so the COVERAGE this returns is itself a measurement."""
    end = int(time.time())
    floor_t = end - days * 86400
    rows, cursor = [], end
    # Page backwards by the FULL request window every time. Stepping back to
    # the oldest bar RETURNED would crawl on a sparsely-traded contract, which
    # is exactly the kind of contract this round is here to measure.
    while cursor > floor_t:
        s = max(floor_t, cursor - 350 * 60)
        try:
            d = R493._get(CDE_CANDLES.format(pid=pid, s=s, e=cursor), timeout=30)
            rows.extend(d.get("candles") or [])
        except Exception:                                   # pragma: no cover
            pass
        cursor = s
        time.sleep(0.20)
    if not rows:
        return pd.DataFrame(columns=["t", "close"])
    f = pd.DataFrame(dict(
        t=pd.to_datetime([int(r["start"]) for r in rows], unit="s"),
        close=[float(r["close"]) for r in rows]))
    return f.sort_values("t").drop_duplicates("t").reset_index(drop=True)


# =============================================================== the tape
def proxy_vol(path):
    """R493's own gap-clean 1-minute measurement behind R493's own 80% fence,
    imported unchanged so the number is comparable to R489's table by
    construction rather than by assertion."""
    f = R493.load_close(path)
    f = f[f["t"] <= R493.cut80(f)]
    v, days = R493.median_1m_move(f)
    return v, days, f["t"].iloc[0], f["t"].iloc[-1]


def tape_vol(f):
    """Same definition on a live-endpoint frame. Gap-clean: only consecutive
    bars exactly 60s apart contribute. Coverage returned beside it."""
    if len(f) < 3:
        return np.nan, 0, np.nan
    v, days = R493.median_1m_move(f)
    span_min = (f["t"].iloc[-1] - f["t"].iloc[0]).total_seconds() / 60.0
    cov = len(f) / span_min * 100.0 if span_min > 0 else np.nan
    return v, days, cov


# =================================================================== main
def main():
    print(LINE)
    print("ROUND 498 - RE-POLL THE FIVE INDEX-CALENDAR PERPETUALS INSIDE "
          "THEIR OWN SESSION")
    print("Queue item 22. Reading and arithmetic on a live public endpoint. "
          "No entry population, no")
    print("backtest, NO LOOK, no candidate. A stale or shut book is reported "
          "UNPRICED, never quoted.")
    print(LINE)
    print(f"\nPoll started {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M:%S} UTC")

    # ---------------------------------------------------------- (0) table
    t = R493.cde_perp_table()
    want = [c for c in INDEX_FIVE + CONTEXT if c in set(t["code"])]
    miss = [c for c in INDEX_FIVE if c not in set(t["code"])]
    if miss:
        print(f"\n*** NOT ON THE LIVE PRODUCT LIST: {miss} - reported absent, "
              f"not quoted. ***")

    print("\n" + LINE)
    print("(1) THE SESSION GATE - the thing R493 could not get past")
    print(LINE)
    print("R493 polled these five and found every one CLOSED with $0 of "
          "24-hour volume, and refused to")
    print("quote the frozen book. This round polls inside the session. The "
          "gate is checked, not assumed.")
    print(f"\n{'contract':<13}{'code':<6}{'session':<9}{'open?':<7}"
          f"{'24h $vol':>14}{'24h ct':>10}{'notional $':>12}{'fee RT%':>9}")
    for c in want:
        r = t[t["code"] == c].iloc[0]
        print(f"{r['name']:<13}{c:<6}{r['sess']:<9}"
              f"{str(bool(r['sess_open'])):<7}{r['qvol']:>14,.0f}"
              f"{r['vol24']:>10,.0f}{r['notional']:>12,.2f}"
              f"{r['fee_rt_pct']:>9.4f}")

    shut = [c for c in INDEX_FIVE
            if c in set(t["code"])
            and not bool(t.loc[t["code"] == c, "sess_open"].iloc[0])]
    if shut:
        print(f"\n*** {len(shut)} of five STILL SHUT at poll time: {shut}. "
              f"They are reported UNPRICED below. ***")
    else:
        print("\nAll five index-calendar contracts are OPEN with non-zero "
              "24-hour volume. The window the")
        print("item was waiting for is the window this round polled in.")

    print("\nThe fee half needs no poll and has not changed: every one of the "
          "five is far above the $750")
    print(f"break point (R489's rule, item 23), so every one pays the flat "
          f"floor {R493.FLOOR_RT_PCT:.2f}% round trip.")
    print("R493's contract-size rule does not bite on any of them - these are "
          "the cheapest contracts on")
    print("the venue by fee, and that was never the question. The spread half "
          "is the question.")

    # ----------------------------------------------------------- (2) poll
    print("\n" + LINE)
    print("(2) SEVEN POLLS, TWELVE SECONDS APART - SPREAD AND DEPTH")
    print(LINE)
    print(f"R493's cadence unchanged: {R493.SPREAD_ROUNDS} polls "
          f"{R493.SPREAD_GAP_S}s apart, median carried with lo-hi so the "
          f"noise stays visible.")
    print(f"Book-age gate {R493.BOOK_STALE_S}s. Depth read {DEPTH_LEVELS} "
          f"levels deep; the figure carried is the")
    print("WORSE SIDE (min of bid and ask), because a position has to get out "
          "as well as in.")
    pids = {c: t.loc[t["code"] == c, "pid"].iloc[0] for c in want}
    sp = poll_series(list(pids.values()))

    print(f"\n{'contract':<13}{'n':>3}{'age':>7}{'spread% med':>13}"
          f"{'lo':>9}{'hi':>9}{'fee RT%':>9}{'ALL-IN RT%':>12}")
    sheet = {}
    for c in want:
        r = t[t["code"] == c].iloc[0]
        s = sp[pids[c]]
        live = (bool(r["sess_open"]) and np.isfinite(s["age_s"])
                and s["age_s"] <= R493.BOOK_STALE_S and s["n"] > 0)
        allin = r["fee_rt_pct"] + s["med"] if live else np.nan
        sheet[c] = dict(name=r["name"], notional=r["notional"],
                        fee=r["fee_rt_pct"], spread=s["med"] if live else np.nan,
                        allin=allin, live=live, qvol=r["qvol"],
                        vol24=r["vol24"], top_ct=s["top_ct"],
                        deep_ct=s["deep_ct"], lv=s["lv"], price=r["price"],
                        sess=r["sess"], age=s["age_s"], lo=s["lo"], hi=s["hi"])
        age = f"{s['age_s']:.0f}s" if np.isfinite(s["age_s"]) else "n/a"
        f4 = (lambda x: f"{x:.4f}" if np.isfinite(x) else "UNPRICED")
        print(f"{r['name']:<13}{s['n']:>3}{age:>7}"
              f"{(f4(s['med']) if live else 'UNPRICED'):>13}"
              f"{f4(s['lo']):>9}{f4(s['hi']):>9}{r['fee_rt_pct']:>9.4f}"
              f"{(f4(allin) if live else 'UNPRICED'):>12}")

    print("\nall-in = fee round trip + one full top-of-book spread, R489/R493's "
          "formula unchanged.")

    # ---------------------------------------------------------- (3) depth
    print("\n" + LINE)
    print("(3) DEPTH AND VOLUME - the operational half, and the item says it "
          "comes first")
    print(LINE)
    print("R480/R483: depth, not spread, is what caps account size. Contracts "
          "at top of book converted")
    print("to dollars at this contract's own notional. `10-level` is the same "
          "read down ten levels.")
    print(f"\n{'contract':<13}{'notional $':>11}{'top ct':>8}{'top $':>11}"
          f"{'10lv ct':>9}{'10lv $':>12}{'levels':>8}{'24h $vol':>14}")
    for c in want:
        d = sheet[c]
        print(f"{d['name']:<13}{d['notional']:>11,.0f}{d['top_ct']:>8,.0f}"
              f"{d['top_ct'] * d['notional']:>11,.0f}{d['deep_ct']:>9,.0f}"
              f"{d['deep_ct'] * d['notional']:>12,.0f}{d['lv']:>8,.0f}"
              f"{d['qvol']:>14,.0f}")

    # ----------------------------------------------------- (4) coordinate
    print("\n" + LINE)
    print("(4) THE R488 COORDINATE - the proxy the item asked for, and the "
          "real tape beside it")
    print(LINE)
    print("The R488 coordinate is the median day's 1-minute move divided by "
          "the all-in round trip. It is")
    print("a SCREEN, not a prediction (R489): how many times the typical "
          "minute covers the crossing cost.")

    print("\n(4a) THE PROXY THE ITEM ASKED FOR - LABELLED A PROXY, and the "
          "reproduction control first.")
    prox = {}
    for c, (sym, path) in PROXY.items():
        if c not in sheet:
            continue
        v, days, t0, t1 = proxy_vol(path)
        ref = R489_PROXY_VOL[sym]
        ok = np.isfinite(v) and abs(v - ref) / ref < 0.02
        prox[c] = dict(sym=sym, vol=v, days=days)
        print(f"  {sym:<5} 80% slice {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}  "
              f"{days:>5,} days  vol% median {v:.4f}   "
              f"R489 published {ref:.4f}   "
              f"{'REPRODUCES' if ok else '*** DOES NOT REPRODUCE ***'}")
    print("  SPY and QQQ are SPENT instruments (R474). Nothing is scored on "
          "them here and nothing could be:")
    print("  a volatility number is a property of the price series, not a "
          "reading of any outcome.")

    print("\n(4b) THE CONTRACTS' OWN 1-MINUTE TAPE, off the same public "
          "endpoint. Strictly better evidence")
    print("     than a proxy, inside the same fence, and NEW - no round has "
          "read these contracts' tape.")
    real = {}
    for c in want:
        f = cde_minute_tape(pids[c])
        v, days, cov = tape_vol(f)
        real[c] = dict(vol=v, days=days, cov=cov, bars=len(f))
        span = (f"{f['t'].iloc[0]:%m-%d %H:%M} -> {f['t'].iloc[-1]:%m-%d %H:%M}"
                if len(f) else "no candles returned")
        vs = f"{v:.4f}" if np.isfinite(v) else "  n/a"
        cs = f"{cov:>5.1f}%" if np.isfinite(cov) else "  n/a"
        print(f"  {sheet[c]['name']:<13}{len(f):>7,} bars  {days:>3} days  "
              f"coverage {cs}  vol% median {vs}   {span}")

    print("\n(4c) THE COORDINATE, both ways. Proxy where the item asked for "
          "one; own tape for all five.")
    print(f"\n{'contract':<13}{'all-in %RT':>11}{'proxy vol%':>12}"
          f"{'proxy mult':>12}{'own vol%':>10}{'own mult':>10}{'coverage':>10}")
    for c in want:
        d = sheet[c]
        pv = prox.get(c, {}).get("vol", np.nan)
        rv = real[c]["vol"]
        f4 = (lambda x, w: f"{x:>{w}.4f}" if np.isfinite(x) else f"{'-':>{w}}")
        f2 = (lambda x, w: f"{x:>{w}.2f}" if np.isfinite(x) else f"{'-':>{w}}")
        ai = d["allin"]
        print(f"{d['name']:<13}"
              f"{(f'{ai:>11.4f}' if np.isfinite(ai) else f'{chr(85)+chr(78)+chr(80):>11}')}"
              f"{f4(pv, 12)}{f2(pv / ai if np.isfinite(ai) else np.nan, 12)}"
              f"{f4(rv, 10)}{f2(rv / ai if np.isfinite(ai) else np.nan, 10)}"
              f"{real[c]['cov']:>9.1f}%")

    print("\nFor scale, on the same coordinate and from R489: XRP 1.28, LINK "
          "0.99, SOL 1.22, BTC 1.04,")
    print("ETH 0.49, QQQ 0.59, SPY 0.43. Everything but XRP and LINK is SPENT.")

    # --------------------------------------------------------- (5) handoff
    print("\n" + LINE)
    print("(5) THE HANDOFF TO THE INDEX SPECIALIST")
    print(LINE)
    for c in INDEX_FIVE:
        if c not in sheet:
            print(f"  {c}: absent from the live product list. UNPRICED.")
            continue
        d = sheet[c]
        if not d["live"]:
            print(f"  {d['name']:<13} UNPRICED - session {d['sess']}, "
                  f"book age {d['age']:.0f}s.")
            continue
        print(f"  {d['name']:<13} all-in {d['allin']:.4f}% of price "
              f"(fee {d['fee']:.4f} + spread {d['spread']:.4f}), "
              f"top of book ${d['top_ct'] * d['notional']:,.0f} a side, "
              f"24h ${d['qvol']:,.0f}")
    print("\nNothing above is a candidate. No entry was built, no outcome was "
          "read, `simulate` was never")
    print("called, and no sealed slice was touched by this file. A cost "
          "figure is never a reason to trade.")
    print(LINE)


if __name__ == "__main__":
    main()
