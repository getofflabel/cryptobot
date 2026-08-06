"""
step478_venue_cost_table.py - ROUND 478

WHAT A CRYPTO ROUND TRIP ACTUALLY COSTS, VENUE BY VENUE.

Research only. No orders. No live file touched. No account is opened and no
money moves. This is a written table for Wallace to decide from.

READ THIS BEFORE THE NUMBERS: THIS ROUND CONSUMES NO LOOK
  This is not a backtest. It fits nothing, sweeps nothing and reads no
  out-of-sample slice. It is arithmetic on published fee schedules against
  numbers RESEARCH_LOG.md already established. No test window is touched, so
  no look is spent and nothing here can qualify or disqualify a strategy on
  its own. What it can do is change which venue the desk would run a
  qualified strategy on, and that is the whole point of the queue item.

QUEUE ITEM 4, VERBATIM
  "WHAT A CRYPTO ROUND TRIP ACTUALLY COSTS, VENUE BY VENUE. Not a backtest -
   a table. R476 promoted this to the only thing standing between the desk
   and a measured edge. Measured over 5.5 years, three coins and 71,073
   entries, his signal is 0.1435% of price per entry against a 0.50% Alpaca
   round trip: the transaction is 3.5x the size of the thing it collects, or
   2.07 stop distances charged before the trade moves. The method does not
   need to get better, the venue needs to get cheaper by roughly a factor of
   four.
   Deliverable: taker and maker rates, US-person availability, and the 10x
   legal leverage ceiling, for every venue a US person can actually use."

THE PREMISE OF THE QUEUE ITEM HAS CHANGED UNDER IT
  The item was written assuming the US menu is spot venues charging tens of
  basis points, with a 10x legal ceiling on leverage. Both halves are now
  out of date, and the change runs in the desk's favour:

  1. CFTC-regulated crypto PERPETUAL futures now exist onshore. Coinbase
     Financial Markets listed nano perpetual-style futures for US persons on
     2025-07-21, and Kraken Derivatives US launched Bitnomial-listed perps on
     2026-06-15. These are US-person-legal, CFTC-regulated, and they are not
     spot: they are futures, and they are priced like futures.
  2. Futures are billed PER CONTRACT, not as a percentage of notional. That
     single fact is what closes the gap the queue item describes, and it is
     why the answer is not "shop for a lower percentage".

  The published US perp fee is a FLAT $0.15 per contract per side. Whether
  that is cheap or ruinous depends entirely on how much notional one contract
  carries, which is why this file computes cost as a share of notional rather
  than quoting the rate.

SOURCES, ALL PRIMARY, ALL FETCHED 2026-08-06
  Alpaca crypto spot tiers   docs.alpaca.markets/us/docs/crypto-fees
  Kraken US futures fees     support.kraken.com/articles/us-futures-fees
  Kraken US contract specs   support.kraken.com/articles/contract-specifications
  Kraken intl derivatives    support.kraken.com/articles/360048917612-fee-schedule
  Coinbase perp guide        docs.cdp.coinbase.com/.../guides/perpetual
  Bitnomial PBUC rulebook    bitnomial.com/exchange/rulebook/product/bitcoin/pbuc/

  Secondary, and flagged as such wherever it is load-bearing: Coinbase's
  US per-contract fixed component and its promotional percentage rate.

THE ONE DISTINCTION THIS FILE REFUSES TO BLUR
  Kraken runs TWO different perpetual products and they are not the same
  venue. The 0.02%/0.05% schedule and the 50x-to-100x leverage headlines
  belong to KRAKEN DERIVATIVES (international, PF_XBTUSD / PF_ETHUSD,
  multi-collateral). A US person cannot trade those. The US product is
  KRAKEN DERIVATIVES US, Bitnomial-listed, PBTCUCZ50 / PETHIUZ50 /
  PSOLUZ50, flat $0.15 per contract per side. Every US number below is the
  second one. Anyone who quotes 100x leverage or a 0.05% taker rate for a US
  account has read the wrong page.
"""

# ----------------------------------------------------------------- constants

# Spot marks, 2026-08-06, Coinbase spot API. The flat-fee venues' cost as a
# SHARE of notional moves inversely with price, so the mark is part of the
# result and is stated with it, not hidden in it.
PX = {"BTC": 64771.195, "ETH": 1911.195, "SOL": 73.985}
PX_ASOF = "2026-08-06"

# What RESEARCH_LOG.md already established. Nothing here is re-derived.
SIGNAL_PCT = 0.1435      # R476: gross % of price per entry, 71,073 entries,
                         # 3 coins, 2021-2026, 1-minute sweep -> BOS.
SIGNAL_2021 = 0.2908     # R476: the effect DECAYS. First year...
SIGNAL_2026 = 0.0387     # ...and the 2026 stub. Both matter below.
STOP_MEDIAN = 0.242      # R476: median structural stop, % of price, pooled.
STOP_BY_COIN = {"BTC": 0.185, "ETH": 0.239, "SOL": 0.341}   # R476
ALPACA_RT_OLD = 0.50     # what every backtest in this log has been charged

# Kraken Derivatives US, Bitnomial-listed perpetual futures.
# $0.15/contract/side all-in = $0.03 commission + $0.10 exchange/clearing
# + $0.02 NFA. Published, per side; round turn is double.
KRAKEN_US_PER_CONTRACT = 0.15
KRAKEN_US_SIZE = {"BTC": 0.01, "ETH": 0.5, "SOL": 5.0}   # units per contract

# Coinbase Financial Markets nano perpetual-style futures. Contract size is
# published (0.01 BTC); the fee is a promotional percentage plus a per-
# contract fixed component. The fixed component is SECONDARY-sourced, so it
# is carried as a range and the conclusion is not allowed to rest on it.
CB_SIZE = {"BTC": 0.01, "ETH": 0.10}
CB_TAKER_PCT = 0.03      # promotional, 0.00% maker / 0.03% taker
CB_FIXED_LO, CB_FIXED_HI = 0.10, 0.15


def pct_of_notional(dollars_per_side, units, px):
    """Flat per-contract fee expressed as % of notional, per side."""
    return 100.0 * dollars_per_side / (units * px)


def rule(ch="-", n=74):
    print(ch * n)


# ----------------------------------------------------------------- section 1
print("=" * 74)
print("ROUND 478 - WHAT A CRYPTO ROUND TRIP COSTS, VENUE BY VENUE")
print("=" * 74)
print(f"marks as of {PX_ASOF}: "
      + ", ".join(f"{k} ${v:,.2f}" for k, v in PX.items()))
print()
print("SECTION 1 - THE US PERPETUAL VENUES, COST AS A SHARE OF NOTIONAL")
rule()
print("Kraken Derivatives US charges $0.15 per contract per side, flat. What")
print("that IS, as a percentage, depends on contract notional:")
print()
print(f"{'coin':<5} {'per contract':>14} {'notional':>12} "
      f"{'per side':>10} {'round trip':>12}")
rule()

kraken_rt = {}
for c in ("BTC", "ETH", "SOL"):
    units = KRAKEN_US_SIZE[c]
    notional = units * PX[c]
    side = pct_of_notional(KRAKEN_US_PER_CONTRACT, units, PX[c])
    kraken_rt[c] = 2 * side
    print(f"{c:<5} {units:>10} {c:<3} ${notional:>10,.2f} "
          f"{side:>9.4f}% {kraken_rt[c]:>11.4f}%")

kraken_avg = sum(kraken_rt.values()) / len(kraken_rt)
rule()
print(f"{'equal-weight average round trip':<44} {kraken_avg:>11.4f}%")
print()
print("The contracts are deliberately sized to land in a $370-$960 notional")
print("band, which is what keeps a flat $0.15 small. This is the mechanism.")
print("It is also the fragility: the percentage moves inversely with price.")
print("If BTC halves from here, the BTC round trip doubles to "
      f"{2*kraken_rt['BTC']:.4f}%.")
print()

# ----------------------------------------------------------------- section 2
print("SECTION 2 - AGAINST THE VENUE THE DESK ACTUALLY USES")
rule()
print(f"{'venue / execution':<38} {'round trip':>11} {'vs Alpaca taker':>16}")
rule()
rows = [
    ("Alpaca crypto spot, TAKER (base tier)", 0.50),
    ("Alpaca crypto spot, MAKER (base tier)", 0.30),
    ("Kraken Derivatives US perp, SOL", kraken_rt["SOL"]),
    ("Kraken Derivatives US perp, BTC", kraken_rt["BTC"]),
    ("Kraken Derivatives US perp, ETH", kraken_rt["ETH"]),
    ("Kraken Derivatives US perp, 3-coin avg", kraken_avg),
]
for name, rt in rows:
    print(f"{name:<38} {rt:>10.4f}% {ALPACA_RT_OLD/rt:>14.1f}x cheaper")
rule()
print()
print("Two separate findings sit in that table and they should not be merged.")
print()
print("FINDING A, and it costs nothing to act on: Alpaca's own MAKER rate is")
print("0.15% a side, not 0.25%. Every backtest in this log has been charged")
print(f"{ALPACA_RT_OLD:.2f}% round trip - taker on both legs. Posting both legs on")
print(f"the SAME venue the desk already trades takes the round trip to 0.30%,")
print(f"a {ALPACA_RT_OLD/0.30:.2f}x cut, with no new account and no new venue. It is not")
print("free: a post-only entry that does not fill is a missed trade, and")
print("backtest.py already models exactly that (execution='maker' chases at")
print("the close on a miss). This is a change to how the desk fills, and it")
print("is available today.")
print()
print("FINDING B, and it is the one the queue was asking for: the US")
print(f"perpetual venues charge {kraken_avg:.4f}% round trip against Alpaca taker's")
print(f"0.50%. The queue asked for a factor of four. This is a factor of")
print(f"{ALPACA_RT_OLD/kraken_avg:.1f}.")
print()

# ----------------------------------------------------------------- section 3
print("SECTION 3 - WHAT THAT DOES TO THE MEASURED SIGNAL")
rule()
print(f"R476's signal is {SIGNAL_PCT}% of price per entry, gross, pooled over")
print("71,073 entries. Charging each venue against it:")
print()
print(f"{'venue / execution':<38} {'cost':>9} {'net/entry':>11} {'cost/signal':>12}")
rule()
for name, rt in rows:
    net = SIGNAL_PCT - rt
    flag = "  <-- POSITIVE" if net > 0 else ""
    print(f"{name:<38} {rt:>8.4f}% {net:>10.4f}% "
          f"{rt/SIGNAL_PCT:>11.2f}x{flag}")
rule()
print()
print("At Alpaca the transaction is 3.5x the thing it collects, which is the")
print("number the queue item already carried. At the US perp venues the")
print(f"signal is {SIGNAL_PCT/kraken_avg:.1f}x the transaction. The sign of the average entry")
print("flips from deeply negative to clearly positive on the venue change")
print("alone, with no change whatsoever to the method.")
print()

# ----------------------------------------------------------------- section 4
print("SECTION 4 - THE CATCH, AND IT IS A REAL ONE")
rule()
print("R476 also established that this effect DECAYS. Charging the same")
print("venues against the FIRST year and the LAST year of the same signal:")
print()
print(f"{'venue / execution':<38} {'2021 net':>11} {'2026 net':>11}")
rule()
for name, rt in rows:
    print(f"{name:<38} {SIGNAL_2021-rt:>10.4f}% {SIGNAL_2026-rt:>10.4f}%")
rule()
print()
print(f"The 2026 stub of the signal is {SIGNAL_2026}% of price. The cheapest US")
print(f"perp round trip measured here is {min(kraken_rt.values()):.4f}% (ETH) and the")
print(f"3-coin average is {kraken_avg:.4f}%. So on the MOST RECENT year of data,")
print("the signal and the new cost are the same size, and the average entry")
print("is at or below break-even even after the venue is fixed.")
print()
print("Stated plainly, because this is the sentence that matters:")
print("  The venue change is worth roughly 0.45% of price per entry and it")
print("  is by far the largest single improvement available to this desk.")
print("  It does NOT by itself make the 1-minute sweep-to-BOS family")
print("  tradeable, because the family's recent behaviour is already at the")
print("  scale of the new, cheaper cost. It removes the cost objection. It")
print("  does not answer the decay objection, and nothing in this file was")
print("  designed to.")
print()

# ----------------------------------------------------------------- section 5
print("SECTION 5 - STOP DISTANCES, AND THE LEVERAGE CEILING QUESTION")
rule()
print("A round trip priced in stop distances is the honest unit, because it")
print("is how much the trade is behind before it moves. Per coin, using each")
print("coin's own R476 structural stop - never a pooled one:")
print()
print(f"{'coin':<5} {'stop %':>8} {'Alpaca RT':>11} {'Kraken US RT':>13} "
      f"{'lev @1% risk':>13}")
rule()
for c in ("BTC", "ETH", "SOL"):
    st = STOP_BY_COIN[c]
    print(f"{c:<5} {st:>7.3f}% {ALPACA_RT_OLD/st:>10.2f}x "
          f"{kraken_rt[c]/st:>12.2f}x {1.0/st:>12.2f}x")
rule()
print()
print("Alpaca charges 2.0-2.7 stop distances before the trade moves. The US")
print("perp venues charge 0.13-0.25. That is the same finding as section 3")
print("in the unit the book would actually feel it.")
print()
print("ON THE '10x LEGAL CEILING' IN THE QUEUE ITEM: it is not binding and")
print("it never was. Coinbase's US perps allow up to 10x and Kraken")
print("Derivatives US sets margin per contract. The method needs 2.9x on SOL,")
print("4.2x on ETH and 5.4x on BTC, read off its own structural stop at 1%")
print("risked. Every one of those fits inside 10x with room. The desk should")
print("stop treating the leverage cap as a constraint - the binding")
print("constraint was cost, and the STANDING PRIORITY's 15-20x tier is")
print("asking for leverage this method does not need and cannot justify from")
print("chart structure.")
print()

# ----------------------------------------------------------------- section 6
print("SECTION 6 - CONTRACT GRANULARITY, THE COST NOBODY QUOTES")
rule()
print("Futures trade in whole contracts. A percentage venue lets any size")
print("through; a contract venue rounds, and rounding is a real tracking")
print("error against the sized position the backtest assumed.")
print()
lev_needed = 1.0 / STOP_MEDIAN
print(f"At 1% risked and R476's pooled {STOP_MEDIAN}% stop, position notional is")
print(f"{lev_needed:.2f}x equity. Contracts that buys, by account size:")
print()
print(f"{'equity':>10} " + " ".join(f"{c:>14}" for c in ("BTC", "ETH", "SOL")))
rule()
for eq in (1_000, 5_000, 10_000, 25_000, 100_000):
    cells = []
    for c in ("BTC", "ETH", "SOL"):
        n = eq * lev_needed / (KRAKEN_US_SIZE[c] * PX[c])
        cells.append(f"{n:>10.1f} ct")
    print(f"${eq:>9,} " + " ".join(cells))
rule()
print()
worst = max(("ETH", "BTC", "SOL"),
            key=lambda c: KRAKEN_US_SIZE[c] * PX[c])
min_eq = 20 * KRAKEN_US_SIZE[worst] * PX[worst] / lev_needed
print(f"The coarsest contract is {worst} at "
      f"${KRAKEN_US_SIZE[worst]*PX[worst]:,.2f} of notional. To hold at")
print(f"least 20 contracts of it - so rounding is under ~2.5% of position -")
print(f"the account needs about ${min_eq:,.0f} of equity. Below roughly $5,000")
print("the rounding error on the coarsest leg is a larger effect than the")
print("fee saving being chased, and the venue change stops being worth it.")
print()

# ----------------------------------------------------------------- section 7
print("SECTION 7 - WHAT THIS TABLE DOES NOT MEASURE")
rule()
print("Three costs are real, unmeasured here, and every one of them cuts")
print("AGAINST the conclusion. None of them are estimated, because guessing")
print("them would be the same sin as tuning a parameter after seeing a test.")
print()
print(" 1. SPREAD. The fee is not the round trip - the spread is the other")
print("    half, and on a $370-$960 contract in a US perp market that is")
print("    weeks to months old it could be larger than the fee. R476's")
print("    signal is 0.1435% of price; a 1-tick-wide spread on a thin book")
print("    can be that on its own. THIS IS THE OPEN QUESTION and it can only")
print("    be answered by recording the book, not by reading a fee page.")
print(" 2. FUNDING. Perps pay or receive funding; spot does not. Kraken US")
print("    settles it as one cash adjustment at 3:00pm CT daily. The method")
print("    holds 24 hours, so it eats a settlement essentially every trade.")
print("    Sign unknown, magnitude unknown, and the desk already has")
print("    funding-series machinery in backtest.py that could measure it.")
print(" 3. PROMOTIONAL RATES EXPIRE. Coinbase's 0.00%/0.03% is explicitly")
print("    promotional. Kraken US's $0.15 is a standing published schedule")
print("    with a stated right to change it. The Kraken figure is the one")
print("    this file leans on for exactly that reason.")
print()

# ----------------------------------------------------------------- section 8
print("SECTION 8 - EVERY VENUE A US PERSON CAN ACTUALLY USE")
rule()
print("PERPETUAL FUTURES, CFTC-REGULATED, US PERSONS ELIGIBLE")
print("  Kraken Derivatives US   $0.15/contract/side all-in, flat")
print("     Bitnomial-listed. 16 perps at launch 2026-06-15. Sizes 0.01 BTC,")
print("     0.5 ETH, 5 SOL. Breakdown $0.03 commission + $0.10 exchange/")
print("     clearing + $0.02 NFA. Leverage set by per-contract margin.")
print("  Coinbase Financial Markets   0.00% maker / 0.03% taker, promotional,")
print("     plus a per-contract fixed component reported at $0.10-$0.15")
print("     (SECONDARY source - verify before sizing on it). Nano sizes")
print("     0.01 BTC, 0.10 ETH. Up to 10x. Live to US persons 2025-07-21.")
print()
print("SPOT, US PERSONS ELIGIBLE  (maker / taker, base tier, % per side)")
print("  Alpaca            0.15 / 0.25   <- what the desk uses now")
print("  Kraken Pro        0.25 / 0.40")
print("  Gemini ActiveTrader  0.00-0.20 / 0.03-0.40, volume-tiered")
print("  Coinbase Advanced 0.40 / 0.60 at the base tier - the most expensive")
print("                    retail venue on this list, not the cheapest")
print("  Robinhood         no explicit commission; paid through the spread,")
print("                    which means the cost is real but unquotable, and")
print("                    a desk that charges honest costs cannot use a")
print("                    venue that will not state them")
print()
print("NOT AVAILABLE TO US PERSONS - recorded so nobody re-proposes them")
print("  BloFin       US restricted. The desk's OLD venue. Dropped 2026-07-25.")
print("  Bybit        US an Excluded Jurisdiction, enforced through KYC.")
print("  Hyperliquid  US restricted, front-end geo-blocked.")
print("  Kraken Derivatives INTERNATIONAL (PF_XBTUSD, 0.02%/0.05%, up to")
print("               100x) - NOT the US product. Do not quote its rates.")
print("  A VPN does not make any of these available. It is a terms-of-service")
print("  breach with frozen-funds and clawback risk, and this desk trades")
print("  demo on a US-legal venue precisely so that question never arises.")
print()

# ----------------------------------------------------------------- verdict
print("=" * 74)
print("VERDICT")
print("=" * 74)
print(f"The venue can get cheaper by a factor of {ALPACA_RT_OLD/kraken_avg:.1f}, not the factor of")
print("four the queue asked for, and it can do it on a CFTC-regulated,")
print("US-person-legal venue at leverage the method's own stops justify.")
print()
print("Two things are TRUE and ACTIONABLE with no further research:")
print(f"  1. Alpaca maker-both-legs is a {ALPACA_RT_OLD/0.30:.2f}x cost cut available today on")
print("     the venue the desk already has, at the price of missed fills.")
print(f"  2. US perps are a {ALPACA_RT_OLD/kraken_avg:.1f}x cost cut, and they turn R476's average")
print(f"     entry from {SIGNAL_PCT-ALPACA_RT_OLD:+.4f}% to {SIGNAL_PCT-kraken_avg:+.4f}% of price.")
print()
print("One thing is TRUE and is NOT a green light:")
print(f"  3. The 2026 stub of that same signal is {SIGNAL_2026}%, which the new cost")
print(f"     ({kraken_avg:.4f}%) still eats. The venue removes the cost objection.")
print("     The decay objection stands, untouched, and no strategy is")
print("     proposed for deployment by this round.")
print()
print("NOTHING IS DEPLOYED. NO LOOK CONSUMED. NO ORDER PLACED.")
print("=" * 74)
