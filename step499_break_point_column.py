"""
step499_break_point_column.py - ROUND 499

THE BREAK-POINT DISTANCE BELONGS ON EVERY COST TABLE THIS DESK WRITES.
(QUEUE ITEM 23)

Research only. No orders. No account. No live file touched, imported or
modified. Nothing here is deployed by this script under any outcome.

QUEUE ITEM 23, VERBATIM
  R493 showed that a CDE cost figure is not a constant: BTC PERP is 6% of
  price from paying more, XRP PERP is 6% from paying less, and on the pooled
  crypto base rate both of those happen in roughly 40-46% of 90-day windows.
  Every cost number in R478 through R492 was written down as though it were a
  property of the instrument. It is a property of the instrument AT THAT
  DAY'S PRICE.
  Deliverable, purely editorial and on numbers already published: add a
  standing `break px / need / base rate` column to the cost tables this desk
  reuses, and write the one-paragraph rule that any future round quoting a
  CDE cost must state the coin price it was quoted at and how far that price
  is from $750 of notional. Re-state R489's ranking with the column attached
  so the top-two flip it already reported is visible as a price fact rather
  than a spread-sample artifact.
  THE FENCE: this re-reads published numbers and re-runs the live endpoint.
  No verdict in this log may be re-interpreted by it - R489's ranking stands
  as published and this adds a column to it, nothing more. No entry
  population, no look, no candidate.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. `simulate()` IS NEVER CALLED IN THIS FILE, and neither is any entry
     builder. No sweep is scanned, no break of structure is detected, no fill
     is modelled, no stop is measured. Nothing here reads what happened AFTER
     a bar. The only thing read off tape is the SIZE OF A ONE-MINUTE MOVE,
     which is a property of the price series and is computable with no notion
     of a trade. It is recomputed here ONLY as a reproduction control against
     R494's published column; the ranking is R489/R494's, restated.
  2. EVERY TAPE MEASUREMENT STOPS AT THE 80% BOUNDARY of that instrument's
     own window, exactly as R489/R493/R494/R497 fenced it. Applied to the
     SPENT instruments too so the comparison stays like for like. XRPUSD,
     DOGEUSD, AVAXUSD and DOTUSD's sealed slices are not loaded into any
     frame in this file.
  3. NOTHING IS SELECTED, NOTHING IS RE-INTERPRETED. R489's ranking and
     R494's correction of it stand exactly as published. This round attaches
     a column to them and writes down a bookkeeping rule. It cannot produce a
     candidate: it never scores a strategy on anything.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the Coinbase Derivatives (CDE) perpetual product
    list - contract codes, contract sizes, marks, session state and
    top-of-book spreads - off the same public keyless endpoints
    R479/R480/R482/R489/R493/R498 used. Read-only GETs; the script holds no
    credential to do anything else.
  SOURCED, IN-LOG: CFM's fee formula max(rate x notional, $0.15) per contract
    per side, exchange+clearing+NFA inside it, at a sourced rate FLOOR of
    0.02% (R486). The break point is that formula's own crossing and is not a
    new assumption: 0.0002 x N = 0.15 -> N = $750.
  PUBLISHED, IN-LOG, READ OFF DISK RATHER THAN RETYPED: R493's census table
    (parsed from step493_output.txt) supplies the prices this desk quoted its
    last full cost sheet at, so the price DRIFT since then is arithmetic on
    published numbers rather than on memory.
  NOT SOURCED AND NOT INVENTED: CFM's volume-tier ladder above the 0.02%
    floor, unsourced after six attempts (R482, R486, R489, R493, R498, this
    round). Every fee figure here is the CHEAPEST the account can be, never
    the likeliest, and every table says so.

USAGE
  python3 step499_break_point_column.py
"""

import re
import sys
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

# R493's machinery, imported UNCHANGED rather than retyped: the live product
# poll, the spread sampler, the pooled crypto yardstick, the 80% fence and
# the gap-clean 1-minute move. Importing the module runs its constants only;
# its main() is guarded.
import step493_break_point_census as R493      # noqa: E402

LINE = "=" * 108

CFM_RATE_FLOOR = R493.CFM_RATE_FLOOR           # 0.0002 per side  (R486)
CFM_MIN_PER_SIDE = R493.CFM_MIN_PER_SIDE       # $0.15 per side   (R486)
BREAK_NOTIONAL = R493.BREAK_NOTIONAL           # $750, exactly
FLOOR_RT_PCT = R493.FLOOR_RT_PCT               # 0.04% round trip

# R489's universe, the rows the ranking is made of. (label, parquet, CDE code)
# Copied from step489 so this file is self-describing; the CODES are what the
# live poll is joined on.
RANKED = [
    ("BTCUSD",  "data_alpaca_BTCUSD_1m.parquet",  "BIP"),
    ("ETHUSD",  "data_alpaca_ETHUSD_1m.parquet",  "ETP"),
    ("SOLUSD",  "data_alpaca_SOLUSD_1m.parquet",  "SLP"),
    ("LINKUSD", "data_alpaca_LINKUSD_1m.parquet", "LNP"),
    ("LTCUSD",  "data_alpaca_LTCUSD_1m.parquet",  "LCP"),
    ("XRPUSD",  "data_alpaca_XRPUSD_1m.parquet",  "XPP"),
    ("ADAUSD",  "data_alpaca_ADAUSD_1m.parquet",  "ADP"),
    ("DOTUSD",  "data_alpaca_DOTUSD_1m.parquet",  "POP"),
    ("PAXGUSD", "data_alpaca_PAXGUSD_1m.parquet", "PAU"),
    ("AVAXUSD", "data_alpaca_AVAXUSD_1m.parquet", "AVP"),
    ("DOGEUSD", "data_alpaca_DOGEUSD_1m.parquet", "DOP"),
]

# R489's (c), unchanged. Which instruments have already had a trade
# population read on this family. LINKUSD joined them in R492.
SPENT = {"BTCUSD", "ETHUSD", "SOLUSD", "SPY", "QQQ", "LINKUSD"}

# R494's PUBLISHED column, for the reproduction control only. These are the
# numbers this round is restating; if the recomputation does not land on
# them, the restatement is of something else and the round says so.
R494_VOL = {"BTCUSD": 0.0546, "ETHUSD": 0.0687, "SOLUSD": 0.1059,
            "LINKUSD": 0.1037, "LTCUSD": 0.0923, "XRPUSD": 0.0829,
            "ADAUSD": 0.0794, "DOTUSD": 0.0842, "PAXGUSD": 0.0791,
            "AVAXUSD": 0.0973, "DOGEUSD": 0.1007}
# R494's published fee-only multiple, same purpose.
R494_FEE_MULT = {"LINKUSD": 2.12, "PAXGUSD": 1.98, "XRPUSD": 1.96,
                 "SOLUSD": 1.88, "DOGEUSD": 1.51, "BTCUSD": 1.37,
                 "LTCUSD": 0.84, "ADAUSD": 0.58, "ETHUSD": 0.57,
                 "DOTUSD": 0.27, "AVAXUSD": 0.25}


# ============================================================ published in
def parse_r493_census(path=f"{REPO}/step493_output.txt"):
    """Read R493's published census straight off its own output file, so the
    prices this desk last quoted a full cost sheet at are READ, not retyped.
    Format: '<NAME> PERP  <size>  <mark>  <notional>  <fee>  <side>  ...'"""
    rows = {}
    pat = re.compile(
        r"^(?P<name>[A-Z0-9]+ PERP)\s+"
        r"(?P<size>[\d.eE+-]+)\s+"
        r"(?P<mark>[\d,]+\.\d+)\s+"
        r"(?P<notional>[\d,]+\.\d+)\s+"
        r"(?P<fee>[\d.]+)\s+"
        r"(?P<side>floor|MIN)\s+")
    with open(path) as fh:
        for ln in fh:
            m = pat.match(ln.strip())
            if not m:
                continue
            nm = m.group("name")
            if nm in rows:
                continue                     # first table only
            rows[nm] = dict(
                size=float(m.group("size")),
                mark=float(m.group("mark").replace(",", "")),
                notional=float(m.group("notional").replace(",", "")),
                fee=float(m.group("fee")), side=m.group("side"))
    return rows


# ================================================================ the tape
def vol_fenced(parquet):
    """R493's gap-clean median 1-minute move, on the first 80% of the
    instrument's own window. Reproduction control only."""
    f = R493.load_close(parquet)
    f = f[f["t"] <= R493.cut80(f)]
    v, ndays = R493.median_1m_move(f)
    return v, ndays


# ================================================================ the rule
def fee_rt_pct(notional):
    """The whole cost rule in one line (R486 sourced, R489 collapsed)."""
    return 2.0 * max(CFM_RATE_FLOOR * notional, CFM_MIN_PER_SIDE) \
        / notional * 100.0


def fee_mult_at_price(vol_pct, size, price):
    """The fee-only R488 multiple as a FUNCTION OF THE COIN PRICE. Below the
    break it is linear in price; at the break it saturates. This is the whole
    of item 23's point expressed as arithmetic."""
    return vol_pct / fee_rt_pct(size * price)


def price_where_equal(vol_a, size_a, vol_b, size_b, lo, hi_mult=8.0):
    """The coin price of instrument A at which A's fee-only multiple equals
    B's CURRENT one. Solved on the closed form, not searched: below the break
    mult = vol * size * px / 30, so px = 30 * target / (vol * size). Returns
    (price, capped) where capped means A saturates before it gets there."""
    target = vol_b / fee_rt_pct(size_b * lo)      # B's multiple at price lo
    cap = vol_a / FLOOR_RT_PCT                    # A's best possible multiple
    if target >= cap:
        return np.nan, True, cap, target
    px = 30.0 * target / (vol_a * size_a)
    return px, False, cap, target


# =================================================================== main
def main():
    print(LINE)
    print("ROUND 499 - THE BREAK-POINT DISTANCE BELONGS ON EVERY COST TABLE "
          "THIS DESK WRITES")
    print("Queue item 23. BOOKKEEPING. Reading, arithmetic and one live "
          "endpoint. No backtest, no entry")
    print("population, NO LOOK, no candidate, and NO VERDICT IN THIS LOG IS "
          "RE-INTERPRETED BY IT.")
    print(LINE)

    print("\nTHE RULE THE COLUMN COMES FROM (R486 sourced, R489 collapsed):")
    print(f"  fee per contract per side = max({CFM_RATE_FLOOR:.4f} x notional,"
          f" ${CFM_MIN_PER_SIDE:.2f})")
    print(f"  the branches cross at notional = ${BREAK_NOTIONAL:,.0f}; above "
          f"it EVERY contract pays a flat {FLOOR_RT_PCT:.2f}% round trip.")
    print("  Contract size is set by the exchange and does not move. So a "
          "CDE cost is a fact about the COIN PRICE,")
    print("  and 'break px / need / base rate' is the column that says how "
          "far today's price is from changing it.")

    # =============================================== 0. live + reproduction
    print("\n" + LINE)
    print("(0) THE LIVE POLL AND THE TWO REPRODUCTION CONTROLS")
    print(LINE)
    t = R493.cde_perp_table()
    now = pd.Timestamp.now(tz="UTC")
    print(f"Polled live, keyless, read-only at {now:%Y-%m-%d %H:%M} UTC. "
          f"{len(t)} perpetual contracts listed.")
    open_n = int(t["sess_open"].sum())
    print(f"  session state: {open_n} OPEN, {len(t) - open_n} CLOSED "
          f"(R493's two-calendar split; a shut book is never quoted here).")
    by_code = t.set_index("code")

    # --- control 1: the break prices are arithmetic and must reproduce.
    r493 = parse_r493_census()
    print(f"\nCONTROL 1 - R493's published census re-read off its own output "
          f"file: {len(r493)} contracts parsed.")
    bad = 0
    for nm, row in r493.items():
        implied = BREAK_NOTIONAL / row["size"]
        if not np.isfinite(implied):
            bad += 1
    print(f"  every parsed row yields a finite break price "
          f"(${BREAK_NOTIONAL:,.0f} / contract size): {len(r493) - bad}"
          f"/{len(r493)}.")
    # and R493's own fee column must be reproducible from its own notional
    errs = [abs(fee_rt_pct(r["notional"]) - r["fee"]) for r in r493.values()]
    print(f"  R493's fee column recomputed from its own notionals: max "
          f"absolute error {max(errs):.6f} percentage points "
          f"({'EXACT' if max(errs) < 5e-4 else 'MISMATCH'}).")

    # --- control 2: R494's volatility column, recomputed behind the fence.
    print("\nCONTROL 2 - R494's published median 1-minute move, recomputed on "
          "the first 80% of each window:")
    print(f"  {'instrument':<11}{'R494 vol%':>10}{'re-run':>10}"
          f"{'diff':>10}{'days':>8}")
    vol = {}
    for sym, pq, code in RANKED:
        try:
            v, nd = vol_fenced(pq)
        except Exception as e:                              # pragma: no cover
            print(f"  {sym:<11}  tape unavailable: {e}")
            continue
        vol[sym] = v
        pub = R494_VOL.get(sym, np.nan)
        print(f"  {sym:<11}{pub:>10.4f}{v:>10.4f}{v - pub:>+10.4f}{nd:>8}")
    d = [abs(vol[s] - R494_VOL[s]) for s in vol if s in R494_VOL]
    verdict = ("EXACT, R494's column reproduces" if max(d) < 5e-4
               else "MISMATCH - SEE NOTE")
    print(f"  max absolute difference {max(d):.4f} percentage points - "
          f"{verdict}.")
    print("  This is the ONLY tape measurement in the round and it exists to "
          "prove the restatement is of")
    print("  R494's table and not of a different one. No entry is built off "
          "it and no outcome is read.")

    # =============================================== 1. the column, all 29
    pool, per_coin = R493.yardstick()
    print("\n" + LINE)
    print("(1) THE STANDING COLUMN - every CDE perpetual, today")
    print(LINE)
    print(f"  base rate = the share of {len(per_coin)}-coin Bybit history "
          f"(fenced at each coin's own 80%) whose forward move")
    print("  over the horizon was at least as far as this contract's "
          "crossing needs. A BASE RATE, NOT A FORECAST.")
    for h in R493.HORIZONS_D:
        r = pool[h]
        if len(r):
            print(f"    {h:>4}d pool: {len(r):>7,} coin-days | p10 "
                  f"{np.percentile(r, 10):.2f}x  median {np.median(r):.2f}x  "
                  f"p90 {np.percentile(r, 90):.2f}x")
    hdr = (f"\n{'contract':<14}{'mark $':>12}{'notional $':>12}{'fee RT%':>9}"
           f"{'side':>7}{'break px $':>12}{'need':>8}{'90d':>8}{'365d':>8}"
           f"{'dist':>9}")
    print(hdr)
    print("-" * (len(hdr) - 1))
    NO_TAPE = R493.NO_TAPE
    for _, r in t.iterrows():
        is_crypto = (r["code"] not in R493.NONCRYPTO_PROXY
                     and r["name"].split()[0] not in NO_TAPE)
        need = r["ratio_needed"]
        f90 = R493.freq_at_least(pool[90], need) if is_crypto else np.nan
        f365 = R493.freq_at_least(pool[365], need) if is_crypto else np.nan
        s90 = f"{f90 * 100:6.1f}%" if np.isfinite(f90) else "     --"
        s365 = f"{f365 * 100:6.1f}%" if np.isfinite(f365) else "     --"
        dist = (need - 1.0) * 100.0
        print(f"{r['name']:<14}{r['price']:>12,.4f}{r['notional']:>12,.2f}"
              f"{r['fee_rt_pct']:>9.4f}"
              f"{'floor' if not r['min_binds'] else 'MIN':>7}"
              f"{r['break_price']:>12,.4f}{need:>7.2f}x{s90:>8}{s365:>8}"
              f"{dist:>+8.1f}%")
    print("\n'dist' is how far today's price is from the break, in per cent "
          "of price: negative means a FALL of")
    print("that much makes the contract dearer, positive means a RISE of that "
          "much makes it cheaper. '--' means")
    print("the crypto yardstick is the wrong distribution for that contract "
          "and none was borrowed (R493's rule).")

    # ================================= 2. R489/R494's ranking + the column
    print("\n" + LINE)
    print("(2) R489's RANKING (as corrected by R494), RESTATED WITH THE "
          "COLUMN ATTACHED")
    print(LINE)
    print("R489's ranking and R494's correction of it STAND AS PUBLISHED. "
          "Nothing below re-ranks them on new")
    print("evidence; the columns to the right of the multiple are the price "
          "fact that was always underneath it.")
    print("\nFEE-ONLY READ - fully sourced, sample-free, a hard FLOOR on "
          "cost, and the ONLY read that is a pure")
    print("price fact (the spread half does not follow the break point). "
          "multiple = median 1-min move / fee RT.")
    rows = []
    for sym, pq, code in RANKED:
        if sym not in vol or code not in by_code.index:
            continue
        r = by_code.loc[code]
        m = vol[sym] / r["fee_rt_pct"]
        need = r["ratio_needed"]
        is_crypto = code not in R493.NONCRYPTO_PROXY
        rows.append(dict(
            sym=sym, name=r["name"], size=r["size"], price=r["price"],
            notional=r["notional"], fee=r["fee_rt_pct"], vol=vol[sym],
            mult=m, cap=vol[sym] / FLOOR_RT_PCT, need=need,
            break_price=r["break_price"],
            f90=R493.freq_at_least(pool[90], need) if is_crypto else np.nan,
            sealed="SPENT" if sym in SPENT else "INTACT",
            pub=R494_FEE_MULT.get(sym, np.nan)))
    rk = pd.DataFrame(rows).sort_values("mult", ascending=False)
    hdr = (f"{'#':<4}{'instrument':<11}{'contract':<13}{'vol%':>8}"
           f"{'fee%RT':>9}{'mult':>7}{'R494':>7}{'cap':>7}{'break px':>14}"
           f"{'need':>8}{'90d':>7}  sealed")
    print(f"\n{hdr}")
    print("-" * (len(hdr) + 2))
    for i, (_, r) in enumerate(rk.iterrows(), 1):
        s90 = f"{r['f90'] * 100:5.1f}%" if np.isfinite(r["f90"]) else "   --"
        pub = f"{r['pub']:>7.2f}" if np.isfinite(r["pub"]) else "     --"
        print(f"{i:<4}{r['sym']:<11}{r['name']:<13}{r['vol']:>8.4f}"
              f"{r['fee']:>9.4f}{r['mult']:>7.2f}{pub}{r['cap']:>7.2f}"
              f"{r['break_price']:>14,.4f}{r['need']:>7.2f}x{s90:>7}"
              f"  {r['sealed']}")
    print("\n'cap' is the BEST fee-only multiple this contract can ever have "
          "on this venue: the one it reaches at")
    print("its break price and cannot beat, because below $0.04% a round trip "
          "the fee schedule has no lower branch.")
    print("A contract already at the floor is AT its cap. Everything else is "
          "below its own ceiling by a price move.")

    # ============================== 3. the top-two flip as a price fact
    print("\n" + LINE)
    print("(3) THE TOP-TWO FLIP, AS A PRICE FACT")
    print(LINE)
    print("R489 reported - and R494 confirmed on 8x to 700x more tape - that "
          "the top two SWAP depending on which")
    print("cost read is used: XRP first on the all-in read, LINK first "
          "fee-only. R493 then showed both sit within")
    print("one ordinary quarter of the break point. Here is the same fact as "
          "arithmetic on the coin price.")
    live = rk[rk["sealed"] == "INTACT"].copy()
    print(f"\n  {'instrument':<10}{'price $':>11}{'break px $':>12}"
          f"{'need':>8}{'mult now':>10}{'cap':>8}{'headroom':>10}")
    for _, r in live.head(6).iterrows():
        head = r["cap"] - r["mult"]
        print(f"  {r['sym']:<10}{r['price']:>11,.4f}{r['break_price']:>12,.4f}"
              f"{r['need']:>7.2f}x{r['mult']:>10.2f}{r['cap']:>8.2f}"
              f"{head:>+10.2f}")
    print("\n  Below the break the fee-only multiple is LINEAR IN THE COIN "
          "PRICE:")
    print("      mult(px) = vol% x contract size x px / 30,  saturating at "
          "vol% / 0.04 once notional passes $750.")
    print("  So every pairwise ordering in the table above has a PRICE at "
          "which it reverses, and that price is")
    print("  solvable in closed form. Against each INTACT instrument's "
          "current multiple:")
    top = live.head(5).reset_index(drop=True)
    print(f"\n  {'A':<10}{'vs B':<10}{'B mult now':>12}"
          f"{'A price to match':>18}{'= move':>10}   note")
    for i in range(len(top)):
        for j in range(len(top)):
            if i == j:
                continue
            a, b = top.iloc[i], top.iloc[j]
            if a["mult"] >= b["mult"]:
                continue                      # only report A catching up
            px, capped, cap, target = price_where_equal(
                a["vol"], a["size"], b["vol"], b["size"], b["price"])
            if capped:
                note = "IMPOSSIBLE - A's cap is below B's current multiple"
                pxs, mv = "        --", "       --"
            else:
                note = "reachable below A's own break point" \
                    if px <= a["break_price"] else \
                    "A is at the floor before this; cap binds first"
                pxs = f"{px:>18,.4f}"
                mv = f"{(px / a['price'] - 1) * 100:>+9.1f}%"
            print(f"  {a['sym']:<10}{b['sym']:<10}{b['mult']:>12.2f}"
                  f"{pxs}{mv}   {note}")
    print("\n  READ IT AS THE ITEM ASKED: the ordering of the top of R489's "
          "fee-only table is not a property of")
    print("  these instruments. It is where their coin prices happened to sit "
          "on the day the table was written.")

    # ============================== 4. what one week of price did to it
    print("\n" + LINE)
    print("(4) THE SAME CONTRACTS, R493's QUOTE DAY vs TODAY - price alone, "
          "nothing else moved")
    print(LINE)
    print("R493 quoted the desk's last full cost sheet on 2026-09-05. The "
          "venue has not changed its schedule, the")
    print("method has not changed, and no round in between touched either. "
          "Every difference below is the coin.")
    hdr = (f"{'contract':<14}{'R493 mark':>12}{'today':>12}{'move':>9}"
           f"{'R493 fee%':>11}{'fee% now':>10}{'fee move':>10}  crossed?")
    print(f"\n{hdr}")
    print("-" * (len(hdr) + 10))
    crossed = []
    for _, r in t.sort_values("notional", ascending=False).iterrows():
        old = r493.get(r["name"])
        if not old:
            continue
        mv = (r["price"] / old["mark"] - 1.0) * 100.0
        fmv = r["fee_rt_pct"] - old["fee"]
        side_now = "floor" if not r["min_binds"] else "MIN"
        did = (side_now != old["side"])
        if did:
            crossed.append((r["name"], old["side"], side_now))
        print(f"{r['name']:<14}{old['mark']:>12,.4f}{r['price']:>12,.4f}"
              f"{mv:>+8.1f}%{old['fee']:>11.4f}{r['fee_rt_pct']:>10.4f}"
              f"{fmv:>+10.4f}  {'YES ' + old['side'] + '->' + side_now if did else ''}")
    if crossed:
        print(f"\n  {len(crossed)} contract(s) CROSSED THE BREAK POINT in "
              f"that window with nothing else changing:")
        for nm, a, b in crossed:
            print(f"    {nm}: {a} -> {b}")
    else:
        print("\n  No contract crossed the break point in this window. The "
              "fee percentages still moved on every")
        print("  MIN-side contract, because a fixed $0.15 over a moving "
              "notional is a moving percentage.")

    # ============================================ 5. the standing rule
    print("\n" + LINE)
    print("(5) THE STANDING RULE - one paragraph, binding on every future "
          "round that quotes a CDE cost")
    print(LINE)
    print("""
  A CDE cost figure is not a property of an instrument. The account pays
  max(0.02% x notional, $0.15) per contract per side, so a contract whose
  notional sits above $750 pays a flat 0.04% of price a round trip and one
  below it pays a fixed number of dollars that becomes a LARGER percentage
  the further the coin falls - hyperbolically, with no lower bound. Contract
  size is fixed by the exchange; the coin price is not. THEREFORE: any round
  in this log that quotes a CDE round trip must state, in the same table, the
  COIN PRICE it was quoted at, that contract's BREAK PRICE ($750 / contract
  size), the RATIO the price must travel to cross it, and the pooled base
  rate for a move that far. A cost sheet without those four columns is a
  snapshot being passed off as a constant. Two corollaries worth stating
  because they have already bitten this desk: a contract already paying the
  0.04% floor is AT its best possible cost and every further improvement must
  come from the spread (BTC PERP), and the ORDERING of any fee-based ranking
  between two below-break contracts is a statement about where their prices
  sat on the day - it reverses at a computable price and reverses back.
  Re-run step493/step499 whenever prices have moved materially rather than
  citing an old percentage (R486's own instruction, generalised).
""")

    # ================================================ 6. what was not done
    print(LINE)
    print("WHAT THIS ROUND DID NOT DO")
    print(LINE)
    print("No entry population was built. No sweep was scanned, no break of "
          "structure detected, no fill modelled,")
    print("no stop measured. `simulate()` was never called. No return, "
          "expectancy, win rate or risk multiple was")
    print("computed for any instrument. Every tape read stops at its own 80% "
          "boundary, so XRPUSD, DOGEUSD,")
    print("AVAXUSD and DOTUSD's sealed slices are intact and unread and "
          "LINK's, crypto's and the index's stay")
    print("exactly as spent as they were. NO LOOK WAS CONSUMED. NO VERDICT "
          "WAS RE-INTERPRETED - R489's ranking")
    print("and R494's correction stand as published and this round attaches a "
          "column to them. No candidate is")
    print("proposed and none could be. No order was placed, no account "
          "exists, no live file was touched.")
    return rk


if __name__ == "__main__":
    main()
