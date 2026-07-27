# Step 444: Where we can trade crypto BOTH directions

Research only. No account was created, nothing was signed, no email, phone,
credential or payment method was entered anywhere, and no terms were accepted.
Everything below is public documentation plus read-only public API calls.

**The problem in one line:** Alpaca reports `shortable: false` on every crypto
pair, and 190 of the 324 setups we measured were shorts. 59% of what the method
finds cannot be placed. We need a venue that takes both directions.

**The short answer:** there are now **three** venues open to a US person that
can short all ten of our pairs, all of them onshore and CFTC-connected. The
best fit is **Kraken spot margin on Kraken Pro**. It shorts all ten, it is
available to US retail clients as of this year, it sizes fractionally, and it
runs on the same public REST API Kraken has had for a decade. Coinbase
Financial Markets is a strong second. Nothing here requires pretending to be
somewhere Wallace is not.

Everything marked **verified** below was read directly from the venue's own
public API with no key and no account.

---

## 1. Open to US persons for real money

### 1a. Kraken spot margin (Kraken Pro): RECOMMENDED for real money

**Legal basis.** Kraken's own eligibility page, last updated 6 May 2026, says
plainly: **"US retail clients: Margin trading is now available to all eligible
US retail clients on Kraken Pro."** This is not the old Eligible Contract
Participant carve-out that required self-certifying as a large trader. That
still exists separately for the international product, but the retail route no
longer needs it. In the US the service is provided through **NinjaTrader
Clearing, LLC doing business as Kraken Derivatives US, a CFTC-registered
futures commission merchant and NFA member, NFA ID 0309379**, with financing
from Payward Accredited LLC.

- https://support.kraken.com/articles/4402532394260
- https://support.kraken.com/articles/getting-started-us-margin
- https://www.kraken.com/features/short-selling

**Coverage, verified.** I pulled `GET /0/public/AssetPairs` from
`api.kraken.com` with no key. Every one of our ten pairs carries a
`leverage_sell` list, which is Kraken's field for how much leverage is
available **to sell short**:

| Our pair | Kraken pair | Max leverage short | Max leverage long |
|---|---|---|---|
| BTC | `XXBTZUSD` | 10x | 10x |
| ETH | `XETHZUSD` | 10x | 10x |
| SOL | `SOLUSD` | 10x | 10x |
| XRP | `XXRPZUSD` | 10x | 10x |
| DOGE | `XDGUSD` | 10x | 10x |
| LINK | `LINKUSD` | 10x | 10x |
| AVAX | `AVAXUSD` | 10x | 10x |
| LTC | `XLTCZUSD` | 10x | 10x |
| ADA | `ADAUSD` | 10x | 10x |
| DOT | `DOTUSD` | 5x | 5x |

Ten for ten, and unlike a futures contract the leverage is symmetric: shorts
are not penalised relative to longs.

**Why this fits our method better than anything else on the list:**

1. **Same instrument as our bars.** We compute levels and structure on spot
   bars. Here we also trade the spot book. There is no futures basis sitting
   between where the level is and where the stop rests.
2. **Fractional sizing.** Position size is risk dollars divided by stop
   distance, which lands on a fractional answer. Spot lets us place that
   fractional answer. Every futures venue below forces whole contracts.
3. **Exchange-side stops, confirmed in the docs.** `AddOrder` accepts
   `stop-loss`, `stop-loss-limit`, `trailing-stop`, `reduce_only`, a `leverage`
   parameter, and, the important one, **conditional close orders**, which
   attach a stop to the entry so it is triggered by the entry's own execution.
   Our stop rests at Kraken. A process restart cannot leave a position naked.
4. **A mature, plain REST API.** `api.kraken.com`, ten years old, fully
   documented, with `AddOrder`, `OpenPositions`, `Balance`, `TradeBalance`,
   `OHLC`. Nothing exotic.
5. **24/7.** No clock.

**Bars, verified.** `GET /0/public/OHLC` supports `interval` of 1, 5, 15, 30,
60, 240 and 1440 minutes, so **1-minute, 5-minute, 1-hour and 4-hour are all
native**, no resampling. The catch is depth: it returns at most 720 bars per
call and Kraken does not serve deep history publicly, so 1-minute reaches back
about 12 hours and 4-hour about four months. That is fine for live operation
and useless for research. Research history keeps coming from the Alpaca spot
bars we already hold.

**What it costs, for the record** (not a ranking input; Wallace has ruled
twice that fees are not a decision input). Three separate charges:

- The ordinary spot trade fee on the opening volume and again on the closing
  volume.
- A **margin opening fee** of roughly 0.020% to 0.025% of the borrowed amount,
  charged once when the position opens. (AVAX is 0.024%, most assets 0.020%.)
- A **rollover fee at the same rate, charged every 4 hours** on the borrowed
  amount for as long as the position stays open. Six charges a day, so roughly
  0.12% to 0.15% of the borrowed amount per day if a position is held around
  the clock. The rate is locked at execution and shown on the order form.
- If a position is force-liquidated, a **3% liquidation fee**.

**Is shorting charged?** Yes. This is a borrow, and it is charged to the short
the same way it is charged to the long. Unlike a perpetual futures funding
rate, it never pays you. For an intraday method the first rollover does not hit
until hour four, so most setups pay the opening fee and little else; anything
held overnight accrues meaningfully.

- Fee detail: https://support.kraken.com/articles/206161568-What-are-the-fees-opening-and-rollover-for-margin-trading-

**Two things Wallace should confirm before we build against it:**

1. **Does the US retail margin product work through the same `api.kraken.com`
   keys and `AddOrder` leverage parameter?** The API docs describe leverage
   generically; they do not carve out the US retail product. Highly likely yes,
   since it is the same Kraken Pro spot engine, but it is the one assumption
   the whole adapter rests on, so it is worth one message to Kraken support.
2. **The state list.** Kraken's eligibility pages say "eligible US retail
   clients" without publishing a clean state table I could retrieve, and
   secondary sources mention New York and Washington being treated differently.
   Ask Kraken directly rather than trusting a third-party list.

---

### 1b. Coinbase Financial Markets: strong second, and the best free data source

**Legal basis.** Coinbase Financial Markets, Inc. is a CFTC-registered futures
commission merchant and NFA member with a public NFA BASIC profile. The
contracts are listed on Coinbase Derivatives, LLC, a CFTC-designated contract
market. US persons are the intended customers.

- https://www.coinbase.com/blog/coinbase-financial-markets-inc-secures-fcm-approval-to-bring-regulated
- https://www.coinbase.com/legal/futures-account-agreement
- https://www.nfa.futures.org/BasicNet/basic-profile.aspx?nfaid=LwP0Tg5Wck0%3D

**Coverage, verified.** I pulled the public product list with no key. All ten
pairs have a live US perpetual-style contract on the FCM venue. Each reports
`twenty_four_by_seven: true`, a `funding_interval` of 3600 seconds and a live
funding rate, with expiry 2030-12-20, a five-year dated contract with a
funding payment holding it to spot, which is how a perpetual is made to fit
CFTC rules. (Some published write-ups still say only BTC, ETH, SOL and XRP have
perpetual-style contracts and the rest are dated futures. That is out of date;
the API says otherwise for all ten today.)

| Our pair | Contract | Contract size | ~Notional per contract |
|---|---|---|---|
| BTC | `BIP-20DEC30-CDE` | 0.01 BTC | ~$643 |
| ETH | `ETP-20DEC30-CDE` | 0.1 ETH | ~$187 |
| SOL | `SLP-20DEC30-CDE` | 5 SOL | ~$372 |
| XRP | `XPP-20DEC30-CDE` | 500 XRP | ~$550 |
| DOGE | `DOP-20DEC30-CDE` | 5,000 DOGE | ~$360 |
| LINK | `LNP-20DEC30-CDE` | 50 LINK | ~$419 |
| AVAX | `AVP-20DEC30-CDE` | 10 AVAX | ~$68 |
| LTC | `LCP-20DEC30-CDE` | 5 LTC | ~$233 |
| ADA | `ADP-20DEC30-CDE` | 1,000 ADA | ~$165 |
| DOT | `POP-20DEC30-CDE` | 100 DOT | ~$82 |

Selling short is just selling the contract. No borrow, no locate.

**The API.** Advanced Trade REST: `GET /api/v3/brokerage/cfm/balance_summary`,
`GET /cfm/positions`, `GET /cfm/positions/{product_id}`,
`POST /cfm/sweeps/schedule`, `POST /cfm/intraday/margin_setting`, and
`POST /api/v3/brokerage/orders` for entry. Limit, market, stop-limit and
bracket orders are supported, so the stop can rest at the venue.
https://docs.cdp.coinbase.com/coinbase-app/advanced-trade-apis/rest-api

**Bars.** Candle granularities include `ONE_MINUTE`, `FIVE_MINUTE`, `ONE_HOUR`
and `FOUR_HOUR` natively, 350 bars per request.

**Cost, for the record.** Gap between buy and sell price, measured live from
the public order book, as a share of the contract price:

| Pair | Best bid | Best ask | Gap as % of price |
|---|---|---|---|
| BTC | 64,330.0 | 64,345.0 | 0.023% |
| ETH | 1,873.0 | 1,874.5 | 0.080% |
| LTC | 46.46 | 46.50 | 0.086% |
| XRP | 1.0991 | 1.1001 | 0.091% |
| SOL | 74.31 | 74.38 | 0.094% |
| LINK | 8.369 | 8.378 | 0.108% |
| ADA | 0.1649 | 0.1651 | 0.121% |
| DOT | 0.816 | 0.817 | 0.123% |
| AVAX | 6.78 | 6.79 | 0.147% |
| DOGE | 0.07189 | 0.07200 | 0.153% |

Commission starts around 0.02% of traded value per contract, plus NFA,
exchange and clearing fees per contract.

**Does shorting carry a funding charge?** It swings both ways, settled hourly.
Positive means longs pay shorts. Read live, as a share of the position's
notional value per year:

| Pair | Funding, % of notional per year | Who pays |
|---|---|---|
| LINK | +13.1% | longs pay shorts (we collect when short) |
| ADA | +11.4% | longs pay shorts |
| ETH | +7.9% | longs pay shorts |
| BTC | +2.6% | longs pay shorts |
| XRP | +0.9% | longs pay shorts |
| SOL / DOT | 0.0% | neither |
| AVAX | −4.4% | **shorts pay longs** |
| DOGE | −9.6% | **shorts pay longs** |
| LTC | −27.2% | **shorts pay longs** |

Sometimes being short is paid here, which Kraken's borrow never is. LTC at
−27% a year is not a rounding error on a multi-day hold.

**Margin, and an asymmetry that matters.** As a share of notional value:

| Pair | Intraday long / short | Overnight long / short |
|---|---|---|
| BTC | 10.0% / 10.0% | 24.6% / 30.6% |
| ETH | 10.0% / 10.0% | 24.5% / 33.5% |
| SOL | 20.0% / 20.0% | 36.6% / 56.0% |
| XRP | 20.0% / 20.0% | 37.3% / 56.6% |
| LINK | 20.0% / 20.0% | 32.1% / 43.9% |
| AVAX | 20.0% / 20.0% | 32.4% / 44.4% |
| ADA | 20.0% / 20.0% | 28.1% / 41.8% |
| DOT | 20.0% / 20.0% | 57.7% / 80.8% |
| DOGE | 25.0% / 25.0% | 52.0% / 91.6% |
| LTC | 25.0% / 25.0% | 40.0% / 58.8% |

Intraday is symmetric; **overnight, shorts cost meaningfully more margin than
longs**. DOGE needs 91.6% of notional to hold a short overnight against 52.0%
for a long. With 59% of our setups on the short side, buying power binds
harder than a symmetric model predicts.

**What Wallace would have to do:** verified Coinbase spot account, then a
separate futures application with a financial-background questionnaire, then
USD funding.

---

### 1c. Kraken Derivatives US perpetual futures: same shop, different product

Launched mid-June 2026 and described by Kraken as the first CFTC-regulated
perpetual futures available to US traders. Brokerage by NinjaTrader Clearing,
LLC dba Kraken Derivatives US (CFTC-registered FCM, NFA ID 0309379); contracts
listed on **Bitnomial Exchange, LLC**, a CFTC-designated contract market that
Kraken's parent Payward acquired.

16 contracts at launch, including **all ten of ours**: PBTCUC (BTC), PETHUI
(ETH), PSOLUS (SOL), PXRPUH (XRP), PDOGUK (DOGE), PLNKUD (LINK), PAVXUD (AVAX),
PLTCUS (LTC), PADAUK (ADA), PDOTUH (DOT). Trades 24/7 subject to maintenance
windows. USD collateral only. Funding accrues continuously and settles as one
cash adjustment daily at 3:00pm CT, lumpier than Coinbase's hourly settlement.
Fees are an exchange fee plus an NFA fee plus a clearing fee plus a flat
per-contract commission, and $10 if a perpetual-only position is liquidated.

**Why it is not the pick: no documented REST API for it.** Kraken's developer
site describes exactly two trading engines: Spot at `api.kraken.com` and
Derivatives at `futures.kraken.com`. `futures.kraken.com` is the **non-US**
perpetuals platform. The US perpetuals live inside Kraken Pro alongside CME
contracts, and there is no public REST documentation covering them. Bitnomial
itself has a full REST API with `prod` and `sandbox` environments at
`https://bitnomial.com/exchange/api/v1/{env}`, but that path is exchange
membership and clearing onboarding, not a retail key.

- https://support.kraken.com/articles/us-perpetual-futures

Worth asking Kraken about in the same message as the spot-margin API question.

---

### 1d. CME crypto futures through a futures broker: narrower than we need

CFTC-regulated and unambiguously open to US persons through any registered FCM
(Interactive Brokers, Tradovate, NinjaTrader, Kraken Derivatives US).

The hours objection is weaker than it used to be: **CME Bitcoin futures moved
to 24/7 Globex trading effective 28 May 2026**, leaving roughly a two-hour
maintenance pause on Saturdays. That is reported rather than confirmed from
CME's own page, and I could **not** confirm the same schedule applies to CME's
ether, solana or XRP contracts, some may still carry the old Sunday-evening to
Friday-afternoon schedule. Confirm per product before relying on it.

The coverage objection stands and is fatal: CME lists single-name futures on
**BTC, ETH, SOL, XRP, ADA, LINK and AVAX**, and **has no DOGE, LTC or DOT
product at all**. There is a Nasdaq CME Crypto Index future covering a basket,
but a basket is not a per-pair setup. Keep this as the most conservative venue
available, not the home for this method.

---

### 1e. Bitnomial / Botanical: the exchange underneath Kraken's US perps

CFTC-registered DCM, DCO and FCM, Chicago. First DCM to self-certify perpetual
futures onshore. Full REST API with a documented sandbox. Catches: the sandbox
is for testing and certification of onboarding participants rather than
self-serve paper trading, the position REST API is documented as not yet
available in the test environment, and sandbox market hours run 5:00pm–4:00pm
CPT Monday to Friday, so the sandbox is not 24/7 even though the live product
is. Retail access routes through their Botanical platform. Worth watching; not
a plug-in answer today.

---

### 1f. The indirect route on Alpaca: inverse funds. Covers 2 of 10, and the clock breaks it.

Checked against Alpaca's own asset list rather than a web page. Across all
14,137 active US equities Alpaca lists, there are exactly **five** inverse
crypto funds and every one is BTC or ETH:

| Ticker | Fund | Exposure | Tradable on Alpaca | Fractional |
|---|---|---|---|---|
| BITI | ProShares Short Bitcoin ETF | −1x BTC, daily | yes | yes |
| SBIT | ProShares UltraShort Bitcoin ETF | −2x BTC, daily | yes | yes |
| BTCZ | T-Rex 2X Inverse Bitcoin Daily Target ETF | −2x BTC, daily | yes | no |
| SETH | ProShares Short Ether ETF | −1x ETH, daily | yes | no |
| ETHD | ProShares UltraShort Ether ETF | −2x ETH, daily | yes | yes |

(T-Rex's inverse ether fund ETQ exists but Alpaca reports `tradable: false`.)

**There is no inverse fund for SOL, XRP, DOGE, LINK, AVAX, LTC, ADA or DOT.**
Eight of our ten pairs have no short-side proxy at all.

Three further problems, worst first:

1. **Market hours, and the stop dies with them.** Regular hours are
   09:30 to 16:00 ET Monday to Friday: 32.5 of the 168 hours in a week, **19.3%
   of the clock**. Alpaca's extended sessions (04:00 to 20:00 ET) would raise
   that to 47.6%, except Alpaca's documentation is explicit that **only limit orders
   are accepted in extended hours; stop and stop-limit orders are rejected**.
   So the requirement that our stop rest at the venue fails outside regular
   hours, and no stop can rest across a weekend at all. For a method with no
   clock that is disqualifying on its own.
2. **Tracking error from the daily reset.** These target −1x or −2x of the
   **daily** move. Held longer than a day the result is path-dependent and is
   not −1x or −2x of the total move; choppy tape erodes it either way. They
   hold futures internally, so there is a roll cost on top.
3. **Cost.** Roughly 0.95%–1.01% of the amount invested per year in expenses
   plus internal roll. One point in favour: you **buy** these to be short, so
   there is no borrow fee and no locate.

Verdict: not a route to running the method. At most a way to express a BTC or
ETH short by hand during US market hours. It does not solve the 59%.

---

## 2. Testnet / demo only: usable now, dead-ends for real money

### Kraken Futures demo: the one clean demo a US person can use

`https://demo-futures.kraken.com`. Kraken's current developer documentation
still lists it as the self-service sandbox for the Derivatives engine, and the
REST and WebSocket surfaces are documented as matching production, so code
written against it ports unchanged. Sign-up is email and password with no
verification (Kraken's support note says emails are disabled in that
environment, so the address need not be real or reachable).

The demo's own user agreement (Payward Brokers Pte Ltd, Singapore) gates it on
age only: the demo account "may be made available to users who are over the age
of 18," then notes separately that "eligibility to use a real trade account on
futures.kraken.com may vary." **There is no US-person exclusion in the demo
agreement itself.**

**Why it dead-ends:** the real platform it demonstrates is Kraken Derivatives
(non-US perpetuals) at `futures.kraken.com`, and US persons are routed instead
to Kraken Derivatives US, a different system with a different API story. The
demo would teach us an order path we cannot then use with real money.

One caution: Kraken published a notice that this environment was being
decommissioned on 14 July with a replacement provided, while the current
developer docs still list it. Treat the URL as needing a live check.

### Interactive Brokers paper trading: real fills, but not a no-signup option

Genuinely US-legal and a real simulated-fill environment with real market data,
and it supports futures and the TWS API. Two things rule it out as the
immediate answer: **you must open a live IBKR account first** (identity
verification; the paper account is provisioned off the back of it), so it is
not an email-only signup, and CME's product list has no DOGE, LTC or DOT, so it
could never cover more than seven of our ten pairs.

### Everything else on the testnet list is a terms problem, not a demo option

Binance Futures Testnet, Bybit testnet and demo, OKX demo trading, Hyperliquid
testnet and dYdX v4 testnet are all technically excellent and all free, and
all operated by venues whose terms exclude US persons, with no testnet
carve-out in the text. They are in section 3, not here.

For the record, because it is the best technical fit and it is worth knowing
what we are declining: Binance's testnet carries all ten pairs as
USDT-margined perpetuals, supports `STOP_MARKET`, `TAKE_PROFIT_MARKET` and
`TRAILING_STOP_MARKET` orders that rest server-side, and has 1-minute bars back
to 2019. It is excluded on terms, and that is the end of it.

---

## 3. Excluded: terms prohibit US persons

Marked excluded, not worked around. A venue we cannot lawfully use is not an
option regardless of how good the API is.

| Venue | What its terms say | Source |
|---|---|---|
| **Binance (global)** | Terms of Use state Binance is unable to provide services to any US person; geofenced, circumvention by VPN or proxy expressly barred. No testnet carve-out. | https://www.binance.com/en/terms |
| **Bybit** | Service Agreement lists the United States among its Excluded Jurisdictions; Bybit holds none of the US licences that would be required. Same entity operates testnet and demo. | https://www.bybit.com/en/help-center/article/Service-Restricted-Countries |
| **OKX (global)** | Restricted Locations include the United States and its territories. The global platform is the one with perpetual swaps and demo trading. | https://www.okx.com/help/terms-of-service |
| **Hyperliquid** | Restricted Persons include persons resident, located or incorporated in the United States, "strictly prohibited from accessing or using the Interface." VPN and location-masking expressly banned. No testnet exemption. | https://app.hyperliquid.xyz/terms |
| **dYdX (v4)** | "...NOT AVAILABLE TO...ALL PERSONS OR ENTITIES WHO RESIDE IN, ARE CITIZENS OF, ARE LOCATED IN...ANY JURISDICTION WHERE THE DYDX PERPETUALS TRADING SOFTWARE IS INELIGIBLE FOR USE INCLUDING WITHOUT LIMITATION THE UNITED STATES OF AMERICA..." | https://dydx.exchange/v4-terms |
| **BloFin** | Established previously on this project: terms prohibit US persons. | prior finding, RESEARCH_LOG |
| **Coinbase International Exchange** | Coinbase's non-US venue; excludes US persons by design, which is why CFM exists. Separately being retired September 2026 and migrated to a Deribit-powered gateway. |, |
| **Kraken Derivatives (non-US)** | The perpetuals platform at futures.kraken.com; US persons are routed to Kraken Derivatives US instead. | https://support.kraken.com/articles/360023786632-kraken-derivatives-eligibility |
| **Deribit** | Terms block the US, UK and Canada, on testnet as well as mainnet. |, |

**Binance.US** is a separate lawful US entity but not a solution: spot only, no
futures, no perpetuals, no crypto margin, so there is no way to be short there.
**OKX US** (OKCoin USA Inc.) likewise offers spot buy, sell and convert only , 
no derivatives, no demo, and excludes New York, Texas, Nevada and Kentucky
among others.

---

## 4. Recommendations

### Paper trading, starting now: shadow mode against the live venue

There is no full-featured paper environment for any venue we would actually
trade. Coinbase's Advanced Trade sandbox returns **static mocked responses**:
fixed payloads in the production shape, no market, no fills; useful for
checking that our JSON parses and nothing else. Kraken has no spot-margin demo
at all. Every crypto testnet with a live matching engine belongs to a venue
whose terms exclude US persons.

So the honest move is to paper trade the real venue's real market with our own
fill logic. Both Kraken's and Coinbase's market data need **no account, no API
key and no payment method**. Every number in this document was pulled with
unauthenticated HTTP requests.

That gives us, today:

- all ten pairs, both directions, on the exact books we would go live on
- real 1-minute, 5-minute, 1-hour and 4-hour bars, all native on both venues
- the real gap between buy and sell price to charge simulated fills, per pair,
  refreshed live rather than assumed
- the real borrow rate (Kraken) or funding rate (Coinbase) to charge held
  positions
- the real margin rules, so we can test whether buying power actually supports
  4.56 setups a day

**What it takes to wire it:**

1. A `kraken.py` market-data adapter next to `alpaca.py`, hitting
   `https://api.kraken.com/0/public/`, `AssetPairs`, `Depth`, `OHLC`. No
   credentials. Map our ten symbols to the Kraken pair codes in 1a.
2. An order-simulation layer that charges the live gap between buy and sell
   price, applies the margin opening fee at entry and the rollover fee every
   four hours on the borrowed amount, and enforces the 10x (5x for DOT) cap.
3. Keep research history on the Alpaca spot bars we already hold, Kraken's
   public bars only reach back 720 intervals.
4. When the live adapter goes in, use `AddOrder` with `leverage` plus a
   **conditional close** stop so the stop is created at Kraken by the entry's
   own execution. Then prove it: place an entry with an attached stop, kill the
   process, and confirm from a fresh session that the stop is still resting.
   That test is the whole point of the exchange-side-stop requirement.
5. Optionally in parallel, a Kraken Futures demo account purely to exercise a
   real futures order path end to end. It dead-ends for real money but it is the
   only free way to watch a real matching engine handle our order flow.

### Real money later: Kraken spot margin on Kraken Pro

Legal basis is clean and domestic: margin trading is offered to US retail
clients on Kraken Pro, provided through NinjaTrader Clearing, LLC dba Kraken
Derivatives US, a CFTC-registered futures commission merchant and NFA member,
NFA ID 0309379. Nothing about it depends on where Wallace appears to be.

It is the only candidate that shorts all ten pairs, sizes fractionally, trades
the same instrument our bars are built from, rests stops at the venue, runs
24/7, and does it all through a plain public REST API that has existed for a
decade. Coinbase Financial Markets is the fallback and is genuinely close. It
loses on whole-contract sizing and on futures bars too sparse to trade from,
and it wins on sometimes paying us to be short.

Two questions to settle with Kraken support before building: whether the US
retail margin product is reachable through the standard `api.kraken.com` keys
and the `AddOrder` leverage parameter, and the current state eligibility list.

---

## 5. What would block either

1. **The Kraken API question is load-bearing.** If US retail margin turns out
   not to be reachable through the public REST API, the whole 1a recommendation
   collapses to Coinbase. This is the single thing to confirm first, before any
   code is written. One support message answers it.

2. **Coinbase's perpetual contracts are too thinly traded to generate signals
   from.** Counting actual 1-minute bars returned in a recent 60-minute window
   on the perpetuals: BTC 39, ETH 37, SOL 17, AVAX 17, XRP 10, DOGE 9, DOT 8,
   LTC 7, ADA 7, **LINK 1**. Candles are trade-based, so a minute with no trade
   produces no bar. History is short too: BTC's perpetual reaches back roughly
   12 to 15 months, DOGE's and DOT's only 6 to 9. If we go the Coinbase route,
   signals must run on spot bars while the stop rests on a futures contract, so
   the two can differ by the basis at the moment of the trigger, and that gap
   needs measuring before real money. **This is the main reason Kraken spot is
   the first pick: the problem does not exist there.**

3. **Borrow cost is real on the Kraken route and it never pays us.** Roughly
   0.02% of the borrowed amount at entry and again every four hours. Intraday
   setups barely feel it; anything held for days accrues. It has to be charged
   in the simulator, not bolted on later.

4. **Whole-contract sizing, if we end up on Coinbase.** One BTC contract is
   about $643 of notional and one XRP contract about $550. Risk-based sizing
   lands on fractions; on a small account the rounding is a large share of the
   intended risk, and for some pairs the smallest possible position may already
   exceed the risk budget. Needs a quantisation rule and a "too big to take"
   skip.

5. **Short-side overnight margin is heavier than long-side on Coinbase.** DOGE
   needs 91.6% of notional overnight for a short against 52.0% for a long. With
   59% of setups short, buying power binds sooner than a symmetric model
   suggests. Kraken's spot margin does not have this asymmetry.

6. **No true paper environment for either venue.** Order rejects, stop
   behaviour at the matching engine, partial fills and margin calls only show up
   with real money. Mitigate by going live at the smallest size that clears the
   minimum, purely to exercise the order path, before the method is allowed to
   size up.

7. **Opening the account is Wallace's step and it is not free.** Identity
   verification and funding, on either venue. There is no no-payment-method
   version of a real venue. The no-payment-method work is the shadow-mode paper
   trading above, which needs nothing at all.

8. **Alpaca stays where it is.** It remains right for stocks: free, fractional,
   cheap, ten years of data. Nothing here proposes moving stocks. What it
   cannot do is short crypto, and no inverse fund fixes that for eight of our
   ten pairs.
