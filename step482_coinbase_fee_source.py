"""
R482 - WHAT DOES COINBASE DERIVATIVES ACTUALLY CHARGE?
=======================================================
RESEARCH_QUEUE.md item 7, opened by R479, extended by R480.

THE ITEM, VERBATIM IN SPIRIT:
  R478 leaned its whole venue table on Kraken Derivatives US because that fee
  schedule was primary-sourced, and flagged Coinbase's per-contract component
  ($0.10-$0.15, plus a promotional 0.00%/0.03%) as SECONDARY. R479 then measured
  the books and found Coinbase is the better venue on both spread and depth, by
  a wide margin - which makes the one number nobody has sourced properly the
  number the decision now rests on.

  Deliverable: Coinbase Derivatives' fee schedule for the CDE perps (BIP/ETP/SLP),
  primary-sourced, with the promotional component separated from the standing one
  and its expiry stated. Re-run step479 --report with the corrected fee so the
  all-in table stops carrying Kraken's rate as a stand-in.
  R480 addition, same page-read: capture the trading-hours schedule properly too.

  "Reading a fee page. No account, no order, no money."

WHAT THIS ROUND IS NOT:
  It is not a backtest. It reads no slice, consumes no look, qualifies nothing
  and could not qualify anything. It replaces one quoted number with a sourced
  one and re-runs the arithmetic that number feeds.

PROVENANCE RULE FOR THIS FILE:
  Every fee figure below carries its source and its tier. Anything that could
  not be sourced is marked UNSOURCED and is NOT silently given a value.
"""

import json
import os
import statistics
import subprocess
import sys
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BOOK = os.path.join(HERE, "data_usperp_book.jsonl")
OUT_JSON = os.path.join(HERE, "step482_cde_fee_table.json")

# =========================================================================
# SECTION 1 - THE SOURCED FEE SCHEDULE
# =========================================================================
# PRIMARY SOURCE, and it is a regulatory filing rather than a marketing page:
#   Coinbase Derivatives, LLC, CFTC Regulation 40.6(a) self-certification,
#   Submission #2025-75, "Modifications to the Fee Schedule", filed with the
#   Commission 2025-11-26, Appendix A (Clean).
#   https://www.cftc.gov/sites/default/files/filings/orgrules/25/11/rules11262533688.pdf
#
# Verbatim from Appendix A:
#   "Effective Trade Date December 15, 2025. Coinbase Derivatives, LLC charges
#    fees according to the below schedule. Fees are charged per side (both the
#    buy and the sell side) per contract."
#
# The schedule has exactly TWO product bands. Band 1 is the full-size contracts
# (BTI/ETI/SLC/XRL). Band 2 is the nano and perp-style contracts, and every
# contract this desk would trade sits in it: nano Bitcoin Perp Style BIP,
# nano Ether Perp Style ETP, nano Solana Perp Style SLP.
#
# BAND 2, fees charged PER SIDE PER CONTRACT:
#     Market Maker        electronic $0.07   block $0.05
#     Non-Professional    electronic $0.10   block $0.05
#     Professional        electronic $0.10   block $0.05
#
# CORROBORATION, independent of Coinbase: Lincoln Park Financial, an unaffiliated
# introducing broker, publishes "Exchange Fee: $0.10/contract" on its nano Bitcoin
# Perp (BIP) contract page. Two independent sources, same number.
CDE_EXCHANGE_FEE_PER_SIDE = 0.10      # USD per contract per side, electronic
CDE_FEE_EFFECTIVE = "2025-12-15"
CDE_FEE_SOURCE = "CFTC submission #2025-75, filed 2025-11-26, Appendix A (Clean)"

# THE PROMOTIONAL COMPONENT THE ITEM ASKED ABOUT: it does not exist in this
# schedule. Submission #2025-75 contains no promotional line, no waiver and no
# expiry for the perp-style band. R478's remembered "promotional 0.00%/0.03%" is
# not a CDE exchange fee at all - see Section 3. There is nothing to separate,
# because the whole $0.10 is standing.
CDE_PROMOTIONAL = None

# WHICH TIER APPLIES TO WALLACE, and why it does not matter.
# The filing defines Non-Professional as an account that is, among other things,
# "(C) Not using a fully automated order generating computer system". A bot
# disqualifies him, so he is a Professional Trader by the exchange's definition.
# Band 2 charges Professional and Non-Professional the SAME $0.10 electronic.
# The disqualification is free. Recorded because it is the kind of thing that
# is expensive to discover later and costs nothing to know now.
TIER_APPLIED = "Professional (bot = not Non-Professional; identical $0.10 in band 2)"

# R478's Kraken Derivatives US figure, quoted, never re-derived. Applies to the
# Bitnomial-listed contracts, which is the venue Kraken US's perps live on.
KRAKEN_US_FEE_PER_SIDE = 0.15

# R480's full-clock median spreads, % of mid, quoted from the log, not re-derived.
R480_SPREAD = {
    "bitnomial_krakenUS": {"BTC": 0.0444, "ETH": 0.0539, "SOL": 0.0511},
    "coinbase_CDE":       {"BTC": 0.0147, "ETH": 0.0427, "SOL": 0.0275},
}
# R476's signal and its own structural stops. Quoted, never re-derived.
R476_SIGNAL_FULL = 0.1435     # gross mean per entry, 2021-2026, % of price
R476_SIGNAL_2026 = 0.0387     # the 2026 stub, the number deciding this family
R476_STOP = {"BTC": 0.185, "ETH": 0.239, "SOL": 0.341}

# =========================================================================
# SECTION 2 - LIVE CONTRACT SPECS, so a per-contract fee becomes a percentage
# =========================================================================
# A $0.10 fee is meaningless until it is divided by the contract's notional, and
# notional is contract_size x price. Both are read live off Coinbase's PUBLIC
# product endpoint - no key, no account, no order. Never hardcoded: R478's whole
# error was carrying one venue's contract sizes onto another's.
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
        out[CDE_PERPS[root]] = {
            "product_id": p["product_id"],
            "contract_size": cs,
            "price": px,
            "notional": cs * px,
            "funding_rate": f.get("funding_rate"),
            "funding_interval": f.get("funding_interval"),
            "intraday_margin": f.get("intraday_margin_rate"),
            "overnight_margin": f.get("overnight_margin_rate"),
            "open_interest": f.get("open_interest"),
        }
    missing = [c for c in CDE_PERPS.values() if c not in out]
    if missing:
        raise SystemExit(f"CDE perp specs missing for {missing} - refusing to guess")
    return out


def rt_pct(fee_per_side, notional):
    """Per-contract fee, both legs, as a % of price. Round trip = 2 sides."""
    return 200.0 * fee_per_side / notional


def main():
    print("=" * 100)
    print("R482 - WHAT COINBASE DERIVATIVES ACTUALLY CHARGES")
    print("Queue item 7. A page read and the arithmetic it feeds. No slice, no look, no order.")
    print("=" * 100)

    specs = fetch_specs()

    # ---------------------------------------------------------------- 1
    print("\n" + "=" * 100)
    print("1. THE EXCHANGE FEE, PRIMARY-SOURCED")
    print("=" * 100)
    print(f"  source     : {CDE_FEE_SOURCE}")
    print(f"  effective  : trade date {CDE_FEE_EFFECTIVE}")
    print(f"  basis      : charged PER SIDE (buy and sell) PER CONTRACT")
    print(f"  band 2     : nano + perp-style, incl. BIP / ETP / SLP")
    print(f"  electronic : Market Maker $0.07 | Non-Professional $0.10 | Professional $0.10")
    print(f"  block      : $0.05 across all three tiers")
    print(f"  tier used  : {TIER_APPLIED}")
    print(f"  promotional: {CDE_PROMOTIONAL if CDE_PROMOTIONAL else 'NONE IN THIS SCHEDULE'}")
    print("  corroborated independently by Lincoln Park Financial's BIP contract page ($0.10).")
    print(f"\n  R478 carried Kraken US at ${KRAKEN_US_FEE_PER_SIDE:.2f}/side as the stand-in.")
    print(f"  The sourced Coinbase number is ${CDE_EXCHANGE_FEE_PER_SIDE:.2f}/side - a third cheaper PER CONTRACT.")

    # ---------------------------------------------------------------- 2
    print("\n" + "=" * 100)
    print("2. THE SAME FEE AS A PERCENTAGE, ON LIVE NOTIONAL")
    print("A per-contract fee is only cheap if the contract is big. These are read live.")
    print("=" * 100)
    print(f"{'coin':5s} {'product':18s} {'size':>10s} {'price':>12s} {'notional':>11s} "
          f"{'CDE fee RT':>11s} {'R478 Kraken':>12s}")
    cde_fee_rt, kraken_fee_rt = {}, {}
    for coin in ("BTC", "ETH", "SOL"):
        s = specs[coin]
        cde = rt_pct(CDE_EXCHANGE_FEE_PER_SIDE, s["notional"])
        # R478's Kraken figures came off ITS OWN contract sizes (0.01/0.5/5).
        # Quoted as published; not recomputed on Coinbase's sizes.
        kr = {"BTC": 0.0463, "ETH": 0.0314, "SOL": 0.0811}[coin]
        cde_fee_rt[coin], kraken_fee_rt[coin] = cde, kr
        print(f"{coin:5s} {s['product_id']:18s} {s['contract_size']:>10.4g} "
              f"{s['price']:>12,.2f} {s['notional']:>11,.2f} {cde:>10.4f}% {kr:>11.4f}%")
    avg_cde = statistics.mean(cde_fee_rt.values())
    avg_kr = statistics.mean(kraken_fee_rt.values())
    print(f"\n  average round trip: Coinbase CDE {avg_cde:.4f}%   Kraken US (R478) {avg_kr:.4f}%")
    print("  THE AVERAGES ARE NEARLY IDENTICAL AND THE PER-COIN ORDER IS REVERSED.")
    print("  Coinbase's ETH contract is 0.1 ETH against Kraken's 0.5 ETH - five times smaller,")
    print("  so the same flat fee lands on a fifth of the notional. ETH goes from R478's")
    print("  CHEAPEST coin to this table's most expensive. R478's average survived by")
    print("  coincidence; every per-coin number it attached to Coinbase was wrong.")

    # ---------------------------------------------------------------- 3
    print("\n" + "=" * 100)
    print("3. THE PART R478 GOT STRUCTURALLY WRONG: THE EXCHANGE IS NOT THE ONLY BILLER")
    print("=" * 100)
    print("  R478's headline claim was that 'futures bill PER CONTRACT, not as a percentage'.")
    print("  For the EXCHANGE that is true and now sourced. For the RETAIL PATH it is false.")
    print()
    print("  A US person does not face CDE directly. Derivatives balances are held with")
    print("  Coinbase Financial Markets (CFM), a CFTC-registered FCM and NFA member, and CFM")
    print("  charges its own commission ON TOP of the exchange fee. Every public Coinbase")
    print("  statement about US perp pricing quotes CFM's number, and CFM's number is a")
    print("  PERCENTAGE OF NOTIONAL: 'fees as low as 0.02%' (Coinbase launch communications,")
    print("  2025-07-21; repeated across coverage).")
    print()
    print("  'AS LOW AS' IS A VOLUME-TIER FLOOR, NOT A RATE. The standing retail tier table")
    print("  for US perps is behind coinbase.com, which refuses unauthenticated requests")
    print("  (HTTP 403 on the fee page, the overview page and the product page). It is")
    print("  therefore UNSOURCED, and this round does not invent a value for it.")
    print("  R478's remembered 'promotional 0.00%/0.03%' belongs to the INTERNATIONAL (INTX)")
    print("  perp book, which a US person cannot trade. It was never a CDE rate.")
    print()
    print("  What that does to the arithmetic, and it is not small:")
    for name, commission in (("exchange fee only (floor, unreachable)", 0.0),
                             ("+ CFM at its advertised 0.02% floor", 0.02),
                             ("+ CFM at 0.05%", 0.05),
                             ("+ CFM at 0.10%", 0.10)):
        tot = {c: cde_fee_rt[c] + 2 * commission for c in cde_fee_rt}
        print(f"    {name:38s} avg RT {statistics.mean(tot.values()):.4f}%  "
              f"(BTC {tot['BTC']:.4f} ETH {tot['ETH']:.4f} SOL {tot['SOL']:.4f})")
    print("\n  Read the second line against the first: at CFM's own advertised FLOOR the")
    print("  commission is LARGER than the entire exchange fee it sits on top of. The number")
    print("  R478 sourced, and the number this round sourced better, is the SMALLER HALF of")
    print("  what a retail account pays. The decision does not rest on the exchange fee.")

    # ---------------------------------------------------------------- 4
    print("\n" + "=" * 100)
    print("4. THE CORRECTED ALL-IN TABLE (exchange fee + R480 full-clock median spread)")
    print("Venue-correct at last: CDE rows carry CDE's fee, Bitnomial rows carry Kraken US's.")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'fee RT':>9s} {'spread':>9s} {'ALL-IN':>9s} "
          f"{'in stops':>9s} {'vs full':>9s} {'vs 2026':>9s}")
    allin_tbl = {}
    for venue in ("bitnomial_krakenUS", "coinbase_CDE"):
        for coin in ("BTC", "ETH", "SOL"):
            fee = cde_fee_rt[coin] if venue == "coinbase_CDE" else kraken_fee_rt[coin]
            spread = R480_SPREAD[venue][coin]
            allin = fee + spread
            allin_tbl[(venue, coin)] = allin
            print(f"{venue:22s} {coin:4s} {fee:9.4f} {spread:9.4f} {allin:9.4f} "
                  f"{allin / R476_STOP[coin]:8.2f}x "
                  f"{R476_SIGNAL_FULL - allin:+9.4f} {R476_SIGNAL_2026 - allin:+9.4f}")
    print("\n  'vs full' / 'vs 2026' are NET % of price per entry: R476's gross minus all-in.")
    print("  EXCHANGE FEE ONLY. Add CFM's commission (Section 3) before believing any of it.")
    cb = statistics.mean([allin_tbl[("coinbase_CDE", c)] for c in ("BTC", "ETH", "SOL")])
    print(f"  Coinbase average all-in, exchange fee + spread: {cb:.4f}% of price.")
    print(f"  With CFM at its 0.02% floor on both legs:       {cb + 0.04:.4f}%.")
    print(f"  R476's 2026 stub, the number that decides:      {R476_SIGNAL_2026:.4f}%.")

    # ---------------------------------------------------------------- 5
    print("\n" + "=" * 100)
    print("5. THE TRADING-HOURS SCHEDULE, PRIMARY-SOURCED (R480's addendum)")
    print("  source: docs.cdp.coinbase.com/derivatives/introduction/market-hours")
    print("=" * 100)
    print("  24x7 participants   : open Sunday 17:00 CT -> Friday 16:00 CT, continuous.")
    print("  WEEKLY HALT         : Friday 16:00-16:50 CT, ALL MARKETS CLOSED. Pre-open 16:50,")
    print("                        no-cancel window 16:59:30, reopen 17:00 CT.")
    print("                        R480 had this secondary. It is now primary and CONFIRMED.")
    print("  NON-24x7 PARTICIPANTS: one-hour break EVERY DAY, 16:00-17:00 CT.")
    print("                        = 21:00-22:00 UTC in CDT, 22:00-23:00 UTC in CST.")
    print("                        THIS IS R480'S MEASURED HOLE, EXACTLY. Mechanism confirmed:")
    print("                        the market stays open, a class of participant goes home.")
    print("  QUARTERLY MAINTENANCE: a 3-4 hour weekend window, announced in advance.")
    print("  Trade date rolls Mon-Fri 16:00 CT for all participants.")
    print("  NOTE THE DST TRAP: the hole is fixed in CHICAGO time, so it MOVES BY AN HOUR IN")
    print("  UTC twice a year. R480 measured it in August (CDT) and recorded it as a UTC fact.")
    print("  Any rule written against 21:00 UTC will be an hour wrong for four months a year.")

    # ---------------------------------------------------------------- 6
    print("\n" + "=" * 100)
    print("6. FOUND ON THE SAME PAGE-READ, NOT ASKED FOR, AND BOTH MATTER")
    print("=" * 100)
    print("  (a) FUNDING ON CDE SETTLES HOURLY, NOT 8-HOURLY.")
    for coin in ("BTC", "ETH", "SOL"):
        s = specs[coin]
        fr = float(s["funding_rate"])
        print(f"      {coin}: funding_rate {fr:.6f} per {s['funding_interval']} "
              f"= {fr*100:.4f}% per hour, {fr*2400:.4f}% per day")
    print("      R481 modelled Bybit's 8-hourly cadence and a once-daily US mark, and reported")
    print("      that 68.4% of entries straddle NO settlement at all. On an HOURLY clock that")
    print("      statistic is simply false for this venue: a 43-minute median hold straddles")
    print("      roughly one, and the 9.7% that run the 24h cap straddle twenty-four.")
    print("      R481'S CONCLUSION SURVIVES ANYWAY, and for the reason R481 gave: the book is")
    print("      49.6% long / 50.4% short, so the charge and the credit cancel whatever the")
    print("      cadence. The cadence changes the VARIANCE, not the mean. But R481's straddle")
    print("      census is a Bybit fact wearing a Coinbase label, and it is corrected here.")
    print("      R481's standing warning is now sharper, not softer: any variant that leans")
    print("      one way pays this hourly, not three times a day.")
    print()
    print("  (b) THE 10x CAP IS AN INTRADAY CAP. OVERNIGHT IS ROUGHLY 4x, AND SOL IS 5x ALL DAY.")
    print(f"      {'coin':5s} {'intraday long':>14s} {'= leverage':>11s} {'overnight long':>15s} {'= leverage':>11s}")
    for coin in ("BTC", "ETH", "SOL"):
        s = specs[coin]
        di = float(s["intraday_margin"]["long_margin_rate"])
        do = float(s["overnight_margin"]["long_margin_rate"])
        print(f"      {coin:5s} {di:>13.2%} {1/di:>10.2f}x {do:>14.2%} {1/do:>10.2f}x")
    print("      R478 established the method needs 2.9x SOL / 4.2x ETH / 5.4x BTC at 1% risked,")
    print("      off its own structural stops, and called that 'comfortably inside the 10x US")
    print("      ceiling'. IT IS NOT COMFORTABLY INSIDE THE OVERNIGHT CEILING. BTC needs 5.4x")
    print("      and gets ~4.1x overnight; ETH needs 4.2x and gets ~4.1x. Both are BELOW the")
    print("      requirement, not above it.")
    print("      This bites exactly the 9.7% of positions that run the 24-hour cap - which is,")
    print("      per R481, the tail that produces the ENTIRE +0.1309% gross at +4.13% each.")
    print("      The margin schedule is hostile to the only positions that make the money.")
    print("      Not a verdict. A constraint nobody had written down, on the record now.")

    # ---------------------------------------------------------------- persist
    payload = {
        "round": "R482",
        "queue_item": 7,
        "exchange_fee_per_side_usd": CDE_EXCHANGE_FEE_PER_SIDE,
        "effective_trade_date": CDE_FEE_EFFECTIVE,
        "source": CDE_FEE_SOURCE,
        "promotional_component": CDE_PROMOTIONAL,
        "tier_applied": TIER_APPLIED,
        "specs": specs,
        "cde_fee_roundtrip_pct": cde_fee_rt,
        "kraken_us_fee_roundtrip_pct_R478": kraken_fee_rt,
        "allin_fee_plus_spread_pct": {f"{v}|{c}": a for (v, c), a in allin_tbl.items()},
        "cfm_commission": "UNSOURCED - percentage of notional, 'as low as 0.02%' floor only",
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(f"\n  persisted -> {os.path.basename(OUT_JSON)}")

    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    print("  ITEM 7 IS ANSWERED. The exchange fee is $0.10 per contract per side, electronic,")
    print("  standing (no promotional component exists), effective 2025-12-15, primary-sourced")
    print("  from a CFTC filing and independently corroborated.")
    print()
    print("  IT IS ALSO THE WRONG NUMBER, AND THAT IS THE ROUND'S REAL OUTPUT. The retail path")
    print("  runs through CFM, CFM bills a PERCENTAGE, and at its own advertised floor that")
    print("  percentage exceeds the entire exchange fee. R478's 'futures bill per contract,")
    print("  not as a percentage' is true of the exchange and false of the account.")
    print()
    print("  NOTHING PROPOSED FOR DEPLOYMENT. NO LOOK CONSUMED. NO ORDER. NO ACCOUNT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
