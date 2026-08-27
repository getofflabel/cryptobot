"""
step486_cfm_commission.py - ROUND 486

WHAT DOES THE ACCOUNT PAY, NOT THE EXCHANGE?   (QUEUE ITEM 10)

Research only. No orders. No account opened. No live file touched, imported or
modified. Nothing here is deployed under any outcome. No slice is read, no cell
is qualified, NO LOOK IS CONSUMED and none could be.

QUEUE ITEM 10, VERBATIM IN SPIRIT
  R481 declared the cost side finished and R482 reopened it: the exchange fee is
  the SMALLER half. Coinbase Financial Markets bills a percentage of notional on
  top of CDE's $0.10/side, and the only public figure is a marketing floor ("as
  low as 0.02%"). At that floor alone the commission exceeds the whole exchange
  fee; the standing volume-tier table is unpublished and coinbase.com 403s every
  unauthenticated request. Every "net" number in this log is an exchange-fee-only
  floor, optimistic by AT LEAST 0.04% of price a round trip.
  Deliverable, cheapest first:
    (a) A published CFM fee schedule from a non-Coinbase channel - the NFA BASIC
        record, an FCM disclosure document, a CFTC Form 1-FR, an introducing
        broker's rate card, or Coinbase's own investor materials.
    (b) Failing that, state the BREAK-EVEN commission - the CFM rate at which the
        method goes negative on the full window and on the 2026 stub - so the
        unsourced number has a bar to clear rather than a guess attached.
  "Reading documents. No account, no order, no money."

WHAT THIS ROUND FOUND FIRST, AND IT IS A CORRECTION TO THE ITEM'S OWN PREMISE
  The item assumes CFM's percentage sits ON TOP of CDE's $0.10/side. Coinbase's
  own launch announcement says it does not. The fee is INCLUSIVE, and it carries
  a per-contract MINIMUM that the item never knew about. Both are sourced in
  Section 1. The consequence runs both ways: the increment over the exchange fee
  is SMALLER than the item feared on two coins of three, and the minimum is a
  FIXED DOLLAR AMOUNT, which makes the whole cost question a question about
  contract notional - i.e. about the PRICE OF THE COIN - in a way no round in
  this log has treated it.

OWNER RULE THAT GOVERNS THE OUTPUT (2026-07-25)
  Costs are charged for honest P&L and used for NOTHING ELSE. They never decline
  a trade, gate a strategy or rank an instrument. "The signal is smaller than the
  transaction" is a finding about SIZE. "Fees make this fail our bar" is a retired
  sentence and does not appear in this round's verdict.

WHY NO LOOK IS CONSUMED
  Section 4 re-reads step481's 68,992-entry population - the WHOLE window, fully
  published in R476/R481/R485, with no sealed slice left anywhere on this family -
  and solves an equation on its published mean. It proposes no partition, sweeps
  no parameter, qualifies no cell and could not qualify one. It is arithmetic on
  a number already in the log.

USAGE
  python3 step486_cfm_commission.py
"""

import json
import statistics
import sys
import urllib.request

import numpy as np
import pandas as pd

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

ENTRIES = f"{REPO}/step481_entries_funding.csv"
OUT_JSON = f"{REPO}/step486_cfm_breakeven.json"

LINE = "=" * 100

# =========================================================================
# SECTION 1 CONSTANTS - THE SOURCED SCHEDULE
# =========================================================================
# PRIMARY SOURCE, and it is Coinbase's own words rather than a press rewrite:
#   Coinbase, "Perpetual futures have arrived in the U.S.", coinbase.com/blog,
#   published 2025-07-21. www.coinbase.com returns 403 to every unauthenticated
#   request (R482 recorded this and it is still true), so the page was read from
#   the Internet Archive:
#     http://web.archive.org/web/20251117042013/
#       https://www.coinbase.com/blog/perpetual-futures-have-arrived-in-the-us
#
# Verbatim, body:
#   "Low trading fees: We're making derivatives trading more accessible with
#    fees as low as 0.02%* per contract."
# Verbatim, the asterisk footnote, and it is the whole finding:
#   "*Trading fees are inclusive of exchange, clearing, and NFA fees. A minimum
#    of $0.15 is charged per contract to cover these fixed costs."
#
# So the account-level charge is NOT additive to CDE's $0.10/side. It is
#     per side  =  max( rate x notional , $0.15 )
# with CDE's $0.10 living INSIDE it. Where the minimum binds, CFM's own take is
# exactly $0.05/side over the exchange fee it collects on Coinbase's behalf.
CFM_RATE_FLOOR = 0.0002          # 0.02%, the "as low as" tier FLOOR, per side
CFM_MIN_PER_CONTRACT = 0.15      # USD, per contract, "to cover these fixed costs"
CFM_INCLUSIVE = True             # of exchange + clearing + NFA fees
CFM_SOURCE = ("Coinbase blog 'Perpetual futures have arrived in the U.S.' "
              "(2025-07-21), read via Internet Archive snapshot 20251117042013")

# PER SIDE OR PER CONTRACT-ROUND-TURN? The blog says "per contract" without
# saying per side. Three things put the base case at PER SIDE:
#   - CDE's own exchange fee, which this figure is INCLUSIVE of, is explicitly
#     "charged per side (both the buy and the sell side) per contract"
#     (CFTC submission #2025-75 Appendix A, sourced in R482). A fee that
#     contains a per-side fee cannot itself be charged less often than per side.
#   - Coinbase's US futures developer documentation describes the older CFM
#     futures fee as "per contract, per side".
#   - It is the conservative reading.
# Section 3 reports the per-round-turn reading as an explicit sensitivity, at
# exactly half. It is NOT quietly assumed away.
FEE_IS_PER_SIDE = True

# WHAT IS STILL UNSOURCED, AND IT IS NAMED RATHER THAN GUESSED:
#   the STANDING VOLUME-TIER LADDER above the 0.02% floor. "As low as" is a
#   floor. No value is invented for the tiers above it anywhere in this file.
CFM_TIER_LADDER = None

# R482's sourced exchange fee, quoted, never re-derived.
CDE_EXCHANGE_FEE_PER_SIDE = 0.10

# R482's published all-in and fee-only round trips, % of price, quoted as
# published. Their DIFFERENCE is the spread component this log has been
# charging, and Section 3 keeps that component untouched: this round changes
# the FEE term and nothing else.
R482_ALLIN_RT = {"BTC": 0.0432, "ETH": 0.1126, "SOL": 0.0724}
R482_FEEONLY_RT = {"BTC": 0.0276, "ETH": 0.0859, "SOL": 0.0460}
# R480's full-clock median spreads on Coinbase, quoted, used as a sensitivity.
R480_SPREAD_FULLCLOCK = {"BTC": 0.0147, "ETH": 0.0427, "SOL": 0.0275}

SYM2COIN = {"BTCUSD": "BTC", "ETHUSD": "ETH", "SOLUSD": "SOL"}

# Live CDE perp specs, read off Coinbase's PUBLIC product endpoint. No key, no
# account, no order. Never hardcoded - R478's whole error was carrying one
# venue's contract sizes onto another's.
PRODUCTS = ("https://api.coinbase.com/api/v3/brokerage/market/products"
            "?product_type=FUTURE&limit=250")
CDE_PERPS = {"BIP": "BTC", "ETP": "ETH", "SLP": "SOL"}


def fetch_specs():
    req = urllib.request.Request(PRODUCTS, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    out = {}
    for p in d.get("products", []):
        root = p["product_id"].split("-")[0]
        if root not in CDE_PERPS:
            continue
        f = p.get("future_product_details") or {}
        if not f.get("contract_size"):
            raise SystemExit(f"no contract_size for {p['product_id']} - refusing to guess")
        cs = float(f["contract_size"])
        px = float(p["price"])
        out[CDE_PERPS[root]] = dict(product_id=p["product_id"], contract_size=cs,
                                    price=px, notional=cs * px)
    missing = [c for c in CDE_PERPS.values() if c not in out]
    if missing:
        raise SystemExit(f"CDE perp specs missing for {missing} - refusing to guess")
    return out


def per_side_usd(notional, rate=CFM_RATE_FLOOR):
    """What the ACCOUNT pays per contract per side, inclusive, at a given rate."""
    return max(rate * notional, CFM_MIN_PER_CONTRACT)


def rt_pct(usd_per_side, notional):
    """A per-side dollar fee as a round-trip % of price."""
    return 200.0 * usd_per_side / notional


def tstat_by_day(vals, days):
    s = pd.Series(np.asarray(vals, float))
    dm = s.groupby(np.asarray(days)).mean().to_numpy()
    dm = dm[np.isfinite(dm)]
    if len(dm) < 3:
        return float("nan"), len(dm)
    return float(dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))), len(dm)


def breakevens(g):
    """The two break-even round-trip costs, in % of price.

    (1) MEAN NET %  - the statistic this log has quoted for years. Net goes to
        zero when the uniform round-trip cost equals the mean gross.
              c*  =  mean(gross_i)

    (2) PER-TRADE NET R - the statistic a book sized off each trade's OWN stop
        actually earns, and the one R485 showed disagrees in SIGN with (1).
              mean_i (gross_i - c)/stop_i = 0
          =>  c*  =  mean(gross_i/stop_i) / mean(1/stop_i)
        i.e. the gross weighted by 1/stop. Always the smaller of the two here,
        because the tight-stop entries that dominate the weighting are the ones
        that cannot pay for themselves.
    """
    inv = 1.0 / g["stop_pct"]
    return (float(g["gross_pct"].mean()),
            float((g["gross_pct"] / g["stop_pct"]).mean() / inv.mean()))


def load_crypto():
    d = pd.read_csv(ENTRIES, usecols=["sig_t", "stop_pct", "gross_pct", "sym", "reason"])
    d["sig_t"] = pd.to_datetime(d["sig_t"])
    d["y"] = d["sig_t"].dt.year
    d["day"] = d["sig_t"].dt.floor("D")
    d["coin"] = d["sym"].map(SYM2COIN)
    return d


# =========================================================================
def section1():
    print(LINE)
    print("1. THE SCHEDULE, SOURCED - AND THE ITEM'S PREMISE IS WRONG")
    print(LINE)
    print(f"  source      : {CFM_SOURCE}")
    print( "  verbatim    : \"fees as low as 0.02%* per contract\"")
    print( "  verbatim    : \"*Trading fees are inclusive of exchange, clearing, and")
    print( "                 NFA fees. A minimum of $0.15 is charged per contract to")
    print( "                 cover these fixed costs.\"")
    print()
    print( "  THE ITEM ASSUMED : account cost = CDE $0.10/side  +  CFM % of notional")
    print( "  WHAT IT ACTUALLY : account cost = max( rate x notional , $0.15 ) per side,")
    print( "                     with CDE's $0.10 INSIDE it.")
    print()
    print(f"  sourced floor rate      : {CFM_RATE_FLOOR*100:.2f}% per side  (an 'as low as' FLOOR)")
    print(f"  sourced minimum         : ${CFM_MIN_PER_CONTRACT:.2f} per contract per side")
    print(f"  inclusive of exch/clr/NFA: {CFM_INCLUSIVE}")
    print(f"  standing tier ladder    : {CFM_TIER_LADDER if CFM_TIER_LADDER else 'UNSOURCED - no value invented for it'}")
    print()
    print( "  Where the $0.15 minimum binds, CFM's own take over the exchange fee it")
    print( "  contains is exactly $0.05 per contract per side. That is the number the")
    print( "  item was trying to bound, and it is a nickel, not a percentage.")


def section2():
    print("\n" + LINE)
    print("2. THE DOCUMENT HUNT - EVERY CHANNEL THE ITEM NAMED, AND WHAT IT GAVE")
    print(LINE)
    rows = [
        ("Coinbase blog (launch announcement)", "web.archive.org snapshot 20251117042013",
         "HIT. Rate floor + the $0.15 minimum + the INCLUSIVE footnote. Section 1."),
        ("CFTC Rule 1.55(k) FCM Specific Disclosure",
         "assets.ctfassets.net PDF dated 2026-05-21, 12 pages",
         "NO FEE SCHEDULE. Fetched and text-extracted in full; the only 'charged' "
         "in the document is interest on account balances. The FCM's mandatory "
         "public disclosure does not carry a rate card."),
        ("NFA BASIC record for CFM", "nfa.futures.org profile",
         "Registration and disciplinary record only. BASIC does not publish fees."),
        ("Introducing broker rate card (Lincoln Park Financial, BIP page)",
         "lpfutures.com/nano-bitcoin-perp-futures-contract/",
         "Publishes the EXCHANGE fee ($.10/contract, corroborating R482) and "
         "margins. Publishes no FCM commission."),
        ("Introducing broker (Tradovate, CDE nano page)", "info.tradovate.com",
         "Says only 'Exchange, clearing and NFA fees still apply' - a DIFFERENT "
         "FCM's structure, in which the fee is additive rather than inclusive. "
         "Its own commission is not on the page."),
        ("Coinbase developer documentation (US futures)",
         "docs.cdp.coinbase.com/coinbase-app/.../futures",
         "'the same fee structure [as Advanced Trade]. During the introductory "
         "beta period, we are only charging 0.05% (the lowest Advanced Trade "
         "tier).' Older CFM futures, not the perps. Kept as the one published "
         "CFM percentage ABOVE the floor - Section 4 measures it against the bar."),
        ("Coinbase developer documentation (perpetuals)",
         "docs.cdp.coinbase.com/coinbase-business/.../perpetual",
         "'0.00% maker and 0.03% taker' AND a '10 USDC min notional' - the "
         "INTERNATIONAL book. Independently re-confirms R482's strike of that "
         "figure from the US table."),
        ("www.coinbase.com/fcm and help.coinbase.com", "direct fetch",
         "403 to every unauthenticated request, both hosts. R482's finding, "
         "unchanged. This is why the archive was used."),
    ]
    for chan, where, got in rows:
        print(f"\n  {chan}")
        print(f"    where : {where}")
        print(f"    got   : {got}")
    print("\n  DELIVERABLE (a): PARTIALLY MET, and by a Coinbase channel rather than a")
    print("  third-party one. The floor rate, the minimum and the inclusive basis are")
    print("  sourced. The STANDING TIER LADDER is not published anywhere reachable")
    print("  without an account, and the FCM's own regulatory disclosure does not")
    print("  carry it. That part of the item's fallback clause is now answered: the")
    print("  full schedule is not knowable before signing up. Deliverable (b) below")
    print("  is therefore the operative half of this round.")


def section3(specs):
    print("\n" + LINE)
    print("3. WHAT THE ACCOUNT PAYS, AT LIVE NOTIONAL")
    print(LINE)
    print("  A fixed-dollar minimum is a percentage that moves with the price of the")
    print("  coin. Every number in this section is read live and is a SNAPSHOT.")
    print()
    hdr = (f"{'coin':5s}{'product':20s}{'size':>9s}{'price':>11s}{'notional':>10s}"
           f"{'0.02%x N':>10s}{'binds':>7s}{'$/side':>8s}{'fee RT%':>9s}"
           f"{'exch RT%':>10s}{'CFM +%':>8s}")
    print(hdr)
    print("-" * len(hdr))
    table = {}
    for coin in ("BTC", "ETH", "SOL"):
        s = specs[coin]
        n = s["notional"]
        rate_amt = CFM_RATE_FLOOR * n
        side = per_side_usd(n)
        binds = "MIN" if side > rate_amt + 1e-12 else "rate"
        fee_rt = rt_pct(side, n)
        exch_rt = rt_pct(CDE_EXCHANGE_FEE_PER_SIDE, n)
        table[coin] = dict(notional=n, price=s["price"], contract_size=s["contract_size"],
                           per_side_usd=side, binds=binds, fee_rt=fee_rt, exch_rt=exch_rt)
        print(f"{coin:5s}{s['product_id']:20s}{s['contract_size']:>9.4g}"
              f"{s['price']:>11,.2f}{n:>10,.2f}{rate_amt:>10.3f}{binds:>7s}"
              f"{side:>8.3f}{fee_rt:>9.4f}{exch_rt:>10.4f}{fee_rt-exch_rt:>8.4f}")
    print()
    print("  The MINIMUM binds on the coins with the small contracts. On those, the")
    print("  0.02% floor rate is IRRELEVANT - the account pays $0.15 whatever the rate")
    print("  says, and would pay $0.15 at a rate of zero.")
    print()
    print("  THE ITEM'S OWN BOUND, TESTED: it said every net number in this log is")
    print("  'optimistic by at least 0.04% of price a round trip'.")
    for coin in ("BTC", "ETH", "SOL"):
        t = table[coin]
        inc = t["fee_rt"] - t["exch_rt"]
        if inc < 0.035:
            verdict = "OVERSTATED by the item"
        elif inc <= 0.045:
            verdict = "the item was right on this coin"
        else:
            verdict = "the item UNDERSTATED it"
        print(f"    {coin}: the true increment is {inc:+.4f}% RT  ->  {verdict}")
    print()
    print("  SENSITIVITY, stated not buried: if the $0.15 and the 0.02% are charged")
    print("  per contract ROUND TURN rather than per side, every fee figure in this")
    print("  file halves. The base case is per side (Section 1's reasoning).")

    print("\n  ALL-IN, keeping this log's spread term EXACTLY as published (R482's")
    print("  9-day sample). Only the fee term changes.")
    hdr2 = (f"{'coin':5s}{'spread%':>10s}{'R482 all-in%':>14s}"
            f"{'R486 all-in%':>14s}{'delta':>9s}{'fullclock alt%':>16s}")
    print(hdr2)
    print("-" * len(hdr2))
    for coin in ("BTC", "ETH", "SOL"):
        spr = R482_ALLIN_RT[coin] - R482_FEEONLY_RT[coin]
        allin = table[coin]["fee_rt"] + spr
        alt = table[coin]["fee_rt"] + R480_SPREAD_FULLCLOCK[coin]
        table[coin]["spread"] = spr
        table[coin]["allin"] = allin
        table[coin]["allin_fullclock"] = alt
        print(f"{coin:5s}{spr:>10.4f}{R482_ALLIN_RT[coin]:>14.4f}"
              f"{allin:>14.4f}{allin-R482_ALLIN_RT[coin]:>+9.4f}{alt:>16.4f}")
    print("\n  NOTE, and it is not a rounding note: R482's percentages were computed at")
    print("  ITS OWN day's prices. Part of every delta above is the coin being cheaper")
    print("  today, not the fee changing. The fee CHANGE alone is the 'CFM +%' column")
    print("  in the first table; the delta here is fee change plus price move.")
    return table


def section4(d, table):
    print("\n" + LINE)
    print("4. DELIVERABLE (b) - THE BREAK-EVEN COMMISSION")
    print(LINE)
    print("  Two statistics, because R485 established they disagree in sign on this")
    print("  population and this log has been quoting the flattering one:")
    print("    MEAN NET %   c* = mean(gross)                       - the log's headline")
    print("    PER-TRADE R  c* = mean(gross/stop) / mean(1/stop)   - what a risk-sized")
    print("                                                          book actually earns")
    print()

    out = {"windows": {}, "per_coin": {}, "specs": {}}

    # -------------------------------------------------- windows
    print("BY WINDOW (all three coins pooled, whole population, no slice)")
    hdr = (f"{'window':<10}{'n':>8}{'days':>7}{'gross%':>9}{'t_day':>8}"
           f"{'BE mean-net%':>14}{'BE per-trade R%':>17}")
    print(hdr)
    print("-" * len(hdr))
    windows = [("FULL", d)] + [(str(y), g) for y, g in d.groupby("y")]
    for lab, g in windows:
        c_pct, c_R = breakevens(g)
        t, nd = tstat_by_day(g["gross_pct"], g["day"])
        out["windows"][lab] = dict(n=int(len(g)), days=int(nd), gross=c_pct,
                                   t_day=t, be_mean_net=c_pct, be_per_trade_R=c_R)
        print(f"{lab:<10}{len(g):>8,}{nd:>7}{g['gross_pct'].mean():>9.4f}"
              f"{t:>8.2f}{c_pct:>14.4f}{c_R:>17.4f}")
    print()
    print("  READ THIS ROW BEFORE ANY OTHER: on the PER-TRADE statistic the 2026 stub's")
    print("  break-even is HIGHER than the full window's. 2026 can afford MORE cost per")
    print("  trade than the average year of this method, not less - R485's finding that")
    print("  2026 is the second-best year in per-trade net R, arriving from the other")
    print("  side. The 'the 2026 stub cannot pay for itself' sentence in this log is a")
    print("  fact about the MEAN-NET statistic only.")

    # -------------------------------------------------- per coin, and the bar
    print("\n" + "-" * 100)
    print("PER COIN - THE BAR THE UNSOURCED TIER LADDER HAS TO CLEAR")
    print("-" * 100)
    print("  For each coin: subtract the spread from the break-even to get the FEE")
    print("  BUDGET, halve it for one side, and price that side in dollars against")
    print("  the sourced $0.15 minimum. If the budget is under $0.15, NO commission")
    print("  rate clears - not even zero - because the minimum alone exceeds it.")
    print()
    for stat, key in (("MEAN NET %", 0), ("PER-TRADE NET R", 1)):
        print(f"\n  === {stat} ===")
        hdr = (f"  {'coin':5s}{'BE all-in%':>12s}{'spread%':>9s}{'fee budget%':>13s}"
               f"{'$/side max':>12s}{'vs $0.15 min':>14s}{'max rate/side':>15s}"
               f"{'price needed':>14s}")
        print(hdr)
        print("  " + "-" * (len(hdr) - 2))
        for coin in ("BTC", "ETH", "SOL"):
            g = d[d["coin"] == coin]
            be = breakevens(g)[key]
            t = table[coin]
            budget = be - t["spread"]
            usd_side = budget / 200.0 * t["notional"]
            clears = usd_side >= CFM_MIN_PER_CONTRACT
            # the rate that exactly exhausts the budget, per side
            max_rate = budget / 2.0 if clears else float("nan")
            # the notional (hence coin price) at which the $0.15 minimum alone is payable
            need_notional = (200.0 * CFM_MIN_PER_CONTRACT / budget) if budget > 0 else float("inf")
            need_price = need_notional / t["contract_size"] if budget > 0 else float("inf")
            out["per_coin"].setdefault(coin, {})[stat] = dict(
                be_allin=be, spread=t["spread"], fee_budget=budget,
                usd_side_max=usd_side, clears_minimum=bool(clears),
                max_rate_pct_per_side=(max_rate if clears else None),
                price_needed_for_minimum=(need_price if budget > 0 else None))
            print(f"  {coin:5s}{be:>12.4f}{t['spread']:>9.4f}{budget:>13.4f}"
                  f"{usd_side:>12.3f}"
                  f"{('CLEARS' if clears else 'FAILS'):>14s}"
                  f"{(f'{max_rate:.4f}%' if clears else 'none exists'):>15s}"
                  f"{(f'{need_price:,.0f}' if budget > 0 else 'n/a'):>14s}")
        print("    'price needed' = the coin price at which the $0.15 minimum ALONE")
        print("    becomes payable out of that budget. Below it, a zero commission")
        print("    still leaves the account net-negative on this statistic.")

    # -------------------------------------------------- the one published rate above the floor
    print("\n" + "-" * 100)
    print("THE ONE PUBLISHED CFM PERCENTAGE ABOVE THE FLOOR, MEASURED AGAINST THE BAR")
    print("-" * 100)
    print("  Coinbase's US futures documentation quotes 0.05% as the lowest Advanced")
    print("  Trade tier, charged during the older futures' introductory period. It is")
    print("  not the perp schedule, but it is the only published CFM number above the")
    print("  0.02% floor and it is the right order of magnitude for a real tier.")
    print()
    hdr = (f"  {'coin':5s}{'$/side @0.02%':>15s}{'$/side @0.05%':>15s}"
           f"{'all-in @0.02%':>15s}{'all-in @0.05%':>15s}{'BE mean-net%':>14s}{'BE ptR%':>10s}")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for coin in ("BTC", "ETH", "SOL"):
        g = d[d["coin"] == coin]
        be_pct, be_R = breakevens(g)
        t = table[coin]
        s02 = per_side_usd(t["notional"], 0.0002)
        s05 = per_side_usd(t["notional"], 0.0005)
        a02 = rt_pct(s02, t["notional"]) + t["spread"]
        a05 = rt_pct(s05, t["notional"]) + t["spread"]
        out["per_coin"][coin]["at_rates"] = dict(usd_side_002=s02, usd_side_005=s05,
                                                 allin_002=a02, allin_005=a05)
        print(f"  {coin:5s}{s02:>15.3f}{s05:>15.3f}{a02:>15.4f}{a05:>15.4f}"
              f"{be_pct:>14.4f}{be_R:>10.4f}")
    print()
    print("  A cell is payable when the all-in sits UNDER the break-even in the same")
    print("  statistic. Compare the two all-in columns against the two BE columns.")

    out["specs"] = {c: {k: v for k, v in table[c].items()} for c in table}
    return out


def main():
    print(LINE)
    print("R486 - WHAT DOES THE ACCOUNT PAY, NOT THE EXCHANGE?   (QUEUE ITEM 10)")
    print("Documents and arithmetic. No slice, no look, no order, no account.")
    print(LINE)

    section1()
    section2()
    specs = fetch_specs()
    table = section3(specs)
    d = load_crypto()
    print(f"\n  population: {len(d):,} entries, step481's funding-covered set, "
          f"{d['sig_t'].min().date()} -> {d['sig_t'].max().date()}")
    out = section4(d, table)

    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\n  wrote {OUT_JSON}")
    print("\n" + LINE)
    print("NOTHING PROPOSED FOR DEPLOYMENT. NOTHING DEPLOYED. NO LOOK CONSUMED.")
    print("NO ORDER PLACED. NO ACCOUNT OPENED.")
    print(LINE)


if __name__ == "__main__":
    main()
