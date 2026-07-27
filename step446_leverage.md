# Step 446: How much leverage a US person can lawfully get, and whether it matters

**Nothing was created, connected, signed or funded.** No account, no wallet, no
email, no phone, no credential, no payment method, no terms accepted, no funds
moved. Everything below is public documentation plus unauthenticated public API
calls.

---

## The answer, first line

**10x is the ceiling for a US person, and it is the law, not the venue.**

Every venue a US person may lawfully use lands at 10x or below on our pairs.
Every venue offering 20x, 40x, 100x, 150x or 1000x bars US persons in its own
terms. That is true of the centralised exchanges **and it is equally true of
every on-chain perpetual venue I checked, without exception.** Going on-chain
does not raise the ceiling. It changes who holds the money; it does not change
what a US person is permitted to trade.

And the second finding, which matters more:

**At 1% of the account risked per trade, the 10x ceiling costs us almost
nothing: it clips one setup in five, by 5% of its size.** The ceiling only
becomes a real constraint if the risk per trade goes up. The numbers are in
section 1, before any venue talk, because they decide whether the venue
question is worth answering at all.

---

## 1. What 10x actually clips

Position size is dollars risked divided by the distance to the stop. Leverage
is whatever falls out of that. It is an output, never a dial.

### 1a. At 1% of the account per trade, using the stop distances measured on live Kraken data

| Setup | Stop distance (price move) | Leverage that falls out | Leverage we can use | Size vs intended | Risk actually taken |
|---|---|---|---|---|---|
| BTC 1-hour | 0.095% | 10.53x | 10.00x | **95.0%** | 0.950% of account |
| ETH 1-hour | 0.118% | 8.47x | 8.47x | 100% | 1.000% |
| BTC 4-hour | 0.160% | 6.25x | 6.25x | 100% | 1.000% |
| SOL 4-hour | 0.470% | 2.13x | 2.13x | 100% | 1.000% |
| ETH 4-hour | 1.318% | 0.76x | 0.76x | 100% | 1.000% |

**One setup of five is clipped, and it is clipped by 5.0% of its size.** On a
$33,000 account that is the difference between risking $330 and risking $313.50
on the tightest BTC 1-hour trades. That is the whole cost of the 10x ceiling at
our current risk setting.

The same test against the 22 real logged trades in `step440_trades.csv` (those
are the SPY/QQQ index trades, not crypto, so treat them as a second opinion on
the shape rather than the same market): **1 of 22 clipped at 1% risk.** Median
leverage that fell out of those trades was 1.77x. The single clipped trade
needed 14.73x.

To fully deliver 1% risk on the tightest setup we have measured, the ceiling
would need to be **10.5x**. We have 10x. That is the entire gap.

### 1b. At 3% of the account per trade

The trader we copy states his own band as 1% to 3% of the account per trade. We
run 1%. Here is what 3% does at the same 10x ceiling.

| Setup | Leverage that falls out at 3% | Leverage we can use | Size vs intended | Risk actually taken |
|---|---|---|---|---|
| BTC 1-hour | 31.58x | 10.00x | 31.7% | 0.950% |
| ETH 1-hour | 25.42x | 10.00x | 39.3% | 1.180% |
| BTC 4-hour | 18.75x | 10.00x | 53.3% | 1.600% |
| SOL 4-hour | 6.38x | 6.38x | 100% | 3.000% |
| ETH 4-hour | 2.28x | 2.28x | 100% | 3.000% |

**Three of five are clipped at 3%.** Against the 22 logged index trades, 6 of 22
clip at 3%; the worst needed 44.2x.

### 1c. The two choices side by side — this is the actual decision

Risk actually delivered per trade, at a 10x ceiling:

| Setup | Running 1% | Running 3% | What 3% buys | What 3% would buy with no ceiling |
|---|---|---|---|---|
| BTC 1-hour | 0.950% | 0.950% | **nothing** | 3.0% |
| ETH 1-hour | 1.000% | 1.180% | 1.18x | 3.0% |
| BTC 4-hour | 1.000% | 1.600% | 1.60x | 3.0% |
| SOL 4-hour | 1.000% | 3.000% | 3.00x | 3.0% |
| ETH 4-hour | 1.000% | 3.000% | 3.00x | 3.0% |

Read the two rows that matter:

- **On the tightest BTC 1-hour setups, moving from 1% to 3% buys literally
  nothing.** The 10x cap binds identically either way, so the position is the
  same size. Those are exactly the trades a higher ceiling would help.
- **On the wide-stop setups (SOL 4-hour, ETH 4-hour) moving to 3% delivers the
  full 3x, today, on Kraken, with no new venue and no new anything.** The
  ceiling never binds there.

So the two levers are not substitutes, they act on opposite ends of the book of
setups:

- **A higher ceiling** only helps the tight-stop trades, and at 1% risk it is
  worth 5% of one trade in five.
- **Higher risk per trade** only helps the wide-stop trades, needs no new venue,
  and is inside the band the trader we copy states for himself.
- To get the full 3% on *every* setup we have measured, the ceiling would have
  to be **31.6x**. No venue a US person may lawfully use offers that.

I am not recommending between them. Both numbers are above; the choice is
yours.

---

## 2. Centralised venues — for the record, one table, then moving on

You have said you do not want to trade on a centralised exchange. Recording the
ceilings anyway so nobody re-opens this.

All figures below pulled live from each venue's own public API today, no key, no
account.

| Venue | Legal status for US retail | Max leverage on our pairs | Notes |
|---|---|---|---|
| **Kraken spot margin** | Open to US retail | **10x** on nine of ten, **5x** DOT | Verified live from `AssetPairs`; 10x is Kraken's global maximum across all 47 marginable pairs, not a per-pair choice |
| **Coinbase Financial Markets** (CFTC-registered FCM) | Open to US retail | **10x intraday** BTC and ETH; **5x** SOL, XRP, LINK, AVAX, ADA, DOT; **4x** DOGE, LTC | Verified live: intraday margin 10.00% on BTC/ETH, 20% or 25% on the rest. Overnight is far worse, 24.6% to 91.6% of notional, i.e. **4.1x down to 1.1x**, and shorts pay more margin than longs overnight |
| **Kraken Derivatives US** (Bitnomial-listed perps) | Open to US retail | Not published. Kraken's own docs describe intraday vs initial margin but publish no figures outside the logged-in trade screen | Same clearing plumbing as Coinbase's FCM route; no documented public REST API for the US perps |
| **Bitnomial direct** | DCM/DCO; retail routes via Botanical | Not published publicly | Sandbox is an onboarding environment, not self-serve paper trading |
| **CME crypto futures via a broker** | Open to US retail | Roughly **2x to 4x**. Micro Bitcoin (MBT, 0.1 BTC ≈ $6,440 notional) carries about $1,730 day-trade margin at TradeStation = 3.7x | Far *below* 10x, not above. Also no DOGE, LTC or DOT contract exists |
| **Kalshi BTCPERP** (CFTC-approved, May 2026) | Open to US retail, application + education gate | **~10x** | First true perpetual approved on a US registered exchange. Confirms the ceiling rather than breaking it |

**Eligible Contract Participant gating:** none of the above requires it. The old
ECP carve-out (several million dollars of assets) still exists for Kraken's
*international* product, but the US retail routes at Kraken, Coinbase and Kalshi
do not use it. So "retail can't get it" is not the reason for the 10x. The
reason is that 10x is where the CFTC-regulated perimeter has settled.

**One curiosity, recorded because it is real and it touches the index trades in
`step440_trades.csv`:** on Coinbase's US FCM venue, equity-index perpetual-style
futures (AI PERP, TECH PERP, CHINA PERP, DFNSE PERP) carry **5.0% intraday
margin = 20x**, and PAXG PERP (gold) also 5.0% = 20x. Lawful, US retail, 20x. Not
crypto pairs, and not SPY or QQQ, so it does not solve this round's problem, but
it is the only above-10x thing a US person can lawfully touch that I found.

---

## 3. On-chain perpetual venues

### 3a. The leverage, and what each one lists

| Venue | Chain | Max leverage | Asset classes | Programmatic route | Currencies? |
|---|---|---|---|---|---|
| **Gains Network / gTrade** | Arbitrum, Polygon, Base, MegaETH | **1000x** forex majors · 750x forex minors · 500x forex exotics · **150x** crypto (500x "DEGEN" BTC/ETH/SOL/BNB) · 250x gold, silver, copper · 150x oil, platinum · 100x indices (SPY, QQQ, IWM, DIA) · 50x stocks | crypto, forex, commodities, indices, stocks | TypeScript SDK, documented contracts, documented "agent wallet / backend signer" delegated-trading path | **Yes** — EUR/USD, USD/JPY, GBP/USD, USD/CAD live; GBP/JPY, GBP/CAD, EUR/AUD live as minors |
| **Ostium** | Arbitrum, USDC collateral | **up to 200x** on select markets; caps vary by asset and time of day | 75 pairs: stocks, ETFs, commodities, indices, **forex**, crypto | **Official Python SDK** (`ostium-python-sdk`, published on PyPI by the protocol team) | **Yes** — forex is a headline asset class |
| **Hyperliquid** | own L1 | **40x** crypto | crypto only | full REST/WebSocket API, mature | no |
| **Jupiter Perps** | Solana | **100x** on SOL, ETH, wBTC; select pairs to 250x | crypto only, very few markets | documented API | no |
| **dYdX v4** | own chain | **25x** BTC/ETH | crypto only | full API, indexer | no |
| **GMX V2** | Arbitrum, Avalanche, Botanix, MegaETH | **100x** majors | crypto only | TypeScript SDK; orders created on-chain, executed by keepers via Chainlink Data Streams | no |
| **Vertex** | Arbitrum (and Ink) | **20x** | crypto | API | no |
| **Drift** | Solana | **10x** cross-margin per its own docs | crypto, prediction markets | TypeScript and Python SDKs | no |
| **Aevo** | own L2 | perps + options on one venue; per-asset caps not published in what I could retrieve | crypto | API | no |
| **Synthetix Perps** | Base / Ethereum | not published cleanly in current docs; roadmap language only | crypto (forex synths existed in older versions) | contracts, SDK | historically yes, not confirmed today |

**The loud flag you asked for:** Gains Network and Ostium both list **currencies
alongside crypto, commodities and indices, on one venue, through one
programmatic interface.** Gains also lists **SPY, QQQ, IWM and DIA at 100x** —
which is precisely the market our 22 real logged trades are in. On paper that
collapses the crypto-short problem, the forex-venue problem and the index
problem into a single integration. That is the most interesting technical
finding in this round by a distance.

It is also the finding that dies in the next section.

### 3b. What each one's own terms say about US persons

This is the part that decides it. I am reporting exactly what each venue's own
documents say. I am not proposing, designing around, or hinting at any method of
appearing to be located elsewhere; that stayed off the table for the centralised
venues and it stays off here.

| Venue | What its own terms say |
|---|---|
| **Gains Network / gTrade** | Terms of Service, in capitals: *"USE OF THE SITE FROM OR IN THE UNITED STATES OR UNITED STATES TERRITORIES, OR BY PERSONS WHO ARE US PERSONS... IS STRICTLY PROHIBITED."* Users must represent they are *"not a U.S. person as defined by any relevant U.S. laws and regulations."* The operator reserves the right to block addresses suspected of US ties, including via VPN detection. Separately, the stocks documentation states plainly: *"Stock trading is not accessible to users located in the United States or other OFAC-sanctioned regions."* |
| **Ostium** | Terms of Use: trading *"is not permitted by persons or entities who reside in, are located in, are incorporated in, have a registered office in, or have their principal place of business in"* the United States, the United Kingdom, the European Union, the Philippines, or any other restricted territory. *"There are no exceptions."* Use of a VPN or similar tool to circumvent is *"strictly prohibited."* Also bars acting on behalf of, or under the direction of, a restricted person. |
| **Hyperliquid** | US persons are Restricted Persons; geofencing enforces it on the front end; the terms forbid VPN workarounds. Established in round 444 and re-confirmed. |
| **dYdX v4** | Terms state the software is not available to persons who reside in, are citizens of, or are located in the United States. Established in round 444. (A December 2025 spot market launch is reported to have opened *spot* to US users; that is not the perpetuals product and does not change the perps position.) |
| **Jupiter** | Published terms prohibit US users from the core interface; users may not access it where doing so would be contrary to that jurisdiction's law or subject Jupiter to registration there. |
| **Drift** | *"It is strictly against the Terms of Use to use these interfaces from a Restricted Territory,"* and restricted-territory users have functions withheld. (Max 10x anyway, so no gain even if it were open.) |
| **Vertex** | Restricts US users; describes its traders as *"qualified non-US users."* |
| **Aevo** | *"The Aevo app is currently not available to U.S. or U.K. persons."* |
| **GMX** | **I could not retrieve GMX's own terms text.** The page is client-rendered and web search collides with the unrelated GMX email company. Reporting this as unverified rather than guessing. Do not treat GMX as open on the strength of its absence from this list. |
| **Synthetix** | Not retrieved cleanly. Unverified. |

### 3c. Protocol versus interface — the distinction you asked me to draw

These are two genuinely different things and they are constantly conflated:

- **The smart contracts are permissionless.** They are code on a public chain.
  They do not know or check where anyone is. Nothing in the contracts of GMX,
  Gains, Ostium, Hyperliquid or the rest excludes a US address.
- **The front-end interface and its terms of service are not permissionless.**
  They are published by an operating entity, they name the United States, and
  several of them (Gains, Ostium, Hyperliquid) explicitly bar circumvention of
  the geographic restriction by VPN or any similar tool.

The gap between those two facts is not a loophole with a known answer. Reaching
permissionless contracts through some other interface is legally unsettled, and
the CFTC has previously charged operators of decentralised derivatives protocols
for failing to register as a designated contract market or futures commission
merchant, so "decentralised" has not functioned as an automatic shield. None of
these venues holds the CFTC registration that offering leveraged perpetuals to
US persons would require.

I am reporting that accurately and stopping there. It is not my call and it is
not a technical question.

**Bottom line for section 3: I found no on-chain perpetual venue whose own terms
permit a US person.** Not one. The on-chain route does not raise the 10x
ceiling; it just moves the same "not available to US persons" sentence from a
centralised exchange's terms page to a protocol's terms page.

---

## 4. The risks that are genuinely different on-chain

Recorded factually because they would apply if this route were ever taken, and
because they are not the same risks as a broker account.

1. **The keys are the money.** Funds sit in a wallet you control. There is no
   password reset, no support desk, no account recovery. Losing the key, or
   having it read off a machine, is total and irreversible loss of everything in
   that wallet. Our bot process would need a signing key with spending
   authority on it, which is a materially different security problem from an API
   key at a broker that can only trade.
2. **Smart-contract risk is real and it is not insurance.** The money sits in
   contracts. A bug, an exploit, or an oracle failure can take the whole pool,
   not just your position. This has happened repeatedly across the sector.
   There is no equivalent of a CFTC-registered FCM's segregated customer funds.
3. **An on-chain liquidation is not a stop at a broker.** A stop at Kraken is an
   order resting at the venue that closes your position at a price. An on-chain
   liquidation is a third party being paid a fee to seize your collateral,
   triggered by an oracle price, in a block, and it can execute during a network
   congestion event or an oracle deviation at a price you never saw on a chart.
   At 100x the distance between "fine" and "seized" is roughly 1% of price
   movement.
4. **Stops themselves.** GMX creates orders on-chain and has keepers execute
   them, and Ostium and Gains both support TP/SL, but I could not confirm from
   primary documentation, for any of them, that a stop survives independently of
   the interface the way a Kraken conditional-close order does. That is our
   standing rule and it would need proving before real money, not assuming.
5. **Operating overhead.** Each is a specific chain (Arbitrum, Solana, Base,
   or a bespoke L1), a specific wallet, a specific collateral token (USDC on
   Arbitrum for Ostium, for example), and a bridge to get money in and out. That
   is several new failure modes between us and a filled order.

---

## 5. What this leaves

1. **10x is the ceiling for a US person, and it is the law, not the venue.**
   Venue-hunting for more leverage is finished. Both the centralised and the
   on-chain lists end at the same sentence in the terms.
2. **At 1% risk the ceiling costs us 5% of one setup in five.** It is not what
   is limiting this method.
3. **The live lever is risk per trade, not leverage.** Going from 1% to 3%
   triples the position on the wide-stop setups today, on Kraken, with no new
   venue, and is inside the band the trader we copy states for himself. It buys
   nothing on the tight BTC 1-hour setups, because 10x binds there either way.
   Both numbers are in section 1c. The choice is yours.
4. **Gains Network and Ostium are worth remembering, not pursuing.** They are
   the only venues found that would put crypto, currencies and the SPY/QQQ index
   trades on one programmatic interface, and both bar US persons in their own
   terms in explicit language. If the CFTC framework for perpetuals that was
   signalled in March 2026 produces a registered US venue with these asset
   classes, that is the thing to re-check. Kalshi's approved BTCPERP is the first
   instance of that pathway working, and it landed at 10x.
5. **Nothing here blocks tonight.** Our own paper engine handles shorts at any
   leverage. This round only decides where real money eventually goes, and the
   answer it gives is: not to a new venue, and probably not to a bigger number
   after the decimal point in the leverage field.

---

## 6. Sources

Live public API, no key, no account: `api.kraken.com/0/public/AssetPairs`;
`api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE`.

- https://support.kraken.com/articles/us-perpetual-futures
- https://support.kraken.com/articles/us-futures-101
- https://support.kraken.com/articles/contract-specifications
- https://help.kalshi.com/en/articles/15357561-what-are-perpetual-futures
- https://www.coindesk.com/policy/2026/05/28/u-s-cftc-opens-crypto-perp-door-with-approval-of-first-regulated-firm
- https://www.tradestation.com/pricing/futures-margin-requirements/
- https://docs.gains.trade/gtrade-leveraged-trading/pair-list
- https://docs.gains.trade/gtrade-leveraged-trading/asset-classes/stocks
- https://gains.trade/terms-of-service
- https://docs.ostium.com/traders/welcome
- https://docs.ostium.com/legal/terms-of-use
- https://github.com/0xOstium/ostium-python-sdk
- https://docs.gmx.io/docs/trading/v2/
- https://docs.drift.trade/legal-and-regulations/terms-of-use
- https://support.jup.ag/hc/en-us/p/terms-of-use
- https://dydx.exchange/v4-terms
- https://app.hyperliquid.xyz/terms
- https://docs.aevo.xyz/
- https://onekey.so/blog/ecosystem/cftc-no-kyc-perps-enforcement/

Local: `step440_trades.csv` (22 logged trades, used for the second-opinion
clipping count in section 1a).
