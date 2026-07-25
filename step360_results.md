# STEP 360 — CAN THE BOT TRADE THE S&P AT ALL? (venue scan, 2026-07-25)

Research and reporting only. **No account was created, nothing was signed
up for, no terms were accepted, no credentials were entered, and no order
was placed anywhere.** Everything below about BloFin was read from its
public price endpoints by `step360_venue_scan.py` and
`step361_spy_usdt_probe.py`. Everything about other venues came from a
web research pass and is labelled by how well it was verified.

The bot cannot trade the S&P today. This file says exactly what it would
take, and ranks the options.

---

## 1. WHAT IS SPX-USDT? SETTLED.

**It is the SPX6900 memecoin. It is not the S&P 500. It never was.**

Read live from BloFin on 2026-07-25:

| | SPX-USDT | the real S&P tracker |
|---|---|---|
| price | **$0.3366** | SPY closed $738.18 on 2026-07-23 |
| contract size | 10 tokens | |
| price step | $0.0001 | |
| smallest order | 0.1 contracts | |
| most leverage allowed | 75x | |
| first listed | 2024-10-30 | |
| on the practice host? | **yes** | |
| turnover in 24h | $294,022 real host / $2,107,117 practice host | |

Our own file `data_blofin_SPX-USDT_1d.parquet` (632 daily bars back to
2024-10-30) shows a price that has only ever moved between about $0.33 and
$0.96. The S&P 500 has never traded under a dollar. The file is a
memecoin's price history and nothing in this bot should ever point a
strategy at it.

**One letter apart, completely different instrument. SPX is the memecoin,
SPY is the index tracker.**

---

## 2. WHAT BLOFIN ACTUALLY LISTS

The real host lists 503 contracts. The practice host lists **88**, and
every single one of the 88 is also on the real host (nothing is
practice-only).

**The 88 practice contracts are all crypto, plus exactly one other thing:
XAUT-USDT, which is tokenized gold. There is no S&P contract, no Nasdaq
contract, and no stock of any kind on the practice host.** That is the
whole blocker in one sentence.

On the **real host** there are three index trackers, measured live
2026-07-25:

| | SPY-USDT | QQQ-USDT | IWM-USDT |
|---|---|---|---|
| tracks | S&P 500 | Nasdaq 100 | US small caps |
| price | 742.25 | 688.12 | 291.30 |
| contract size | 0.01 | 0.01 | 0.01 |
| one contract is worth | **$7.42** | $6.88 | $2.91 |
| price step | $0.01 | $0.01 | $0.01 |
| smallest order | 1 contract | 1 contract | 1 contract |
| most leverage allowed | 20x | 20x | 20x |
| biggest single market order | 20,000 contracts (about $148,000) | 20,000 | 50,000 |
| turnover in 24h | **$652,638** | $180,721 | $23,467 |
| gap between the buy and sell price | **0.0013% of price** | 0.0015% | **0.1065%** |
| first listed | 2026-03-05 | 2026-03-05 | 2026-04-08 |
| on the practice host? | **no** | no | no |

Does SPY-USDT really track the index? Yes. It printed 742.25 while the
real SPY tracker last closed at 738.18 two sessions earlier, and an
earlier check on 2026-07-24 put the two 0.08% apart in price. It is the
real thing.

IWM-USDT is unusable: the gap between its buy and sell price is 0.1065% of
price, which is **eighty times wider** than SPY-USDT's, and only $23,467
changes hands a day.

### The finding that actually matters: SPY-USDT never closes

I pulled 500 hourly bars covering 2026-07-04 to 2026-07-25 and checked
which ones traded.

**All 500 traded. All 24 hours of the day traded. All 140 weekend hours
traded.**

This is a big deal and it changes the S&P playbook. The whole reason the
stock tracker is awkward to trade is that it goes dark for about 17.5
hours every night, and the price gaps by more than 0.3% on 46.6% of days
across that dark window. **BloFin's SPY-USDT has no dark window at all.**
It is a continuous instrument wearing the ETF's name, structurally closer
to the futures than to the stock. Any stop-placement worry that came from
the overnight gap simply does not apply on this venue.

### What it costs to hold there

BloFin charges a market-order fee of 0.06% of position size per fill.
With the measured 0.0013% price gap and a conservative 0.01% per fill for
slippage, **a round trip on SPY-USDT costs about 0.1413% of the full
position size.** A US stock broker costs about 0.04% and CME futures about
0.02%, so this venue is about three and a half times a stock broker.

There is also a holding charge that runs three times a day. Over the last
100 settlements it averaged **minus 0.0182% per period**, and the minus
sign means the people who are long get PAID rather than charged, at about
0.055% of position size per day, which annualises near +20%. If that sign
holds it is a real subsidy for a long-only bot. **It is only 100
settlements, about 33 days.** Do not build anything on it until we have a
year of it.

---

## 3. THE PROBLEM WITH THE BLOFIN PATH

BloFin's own terms of service prohibit US persons from opening accounts or
trading. Wallace is a US person. The Costa Rica connection does not solve
that, because venues match on the identity collected when the account was
opened, not on the address the connection appears to come from.

The documented consequences when a venue decides an account belongs to a
restricted person are: trading switched off, the account put into
withdrawal-only mode, or funds frozen while under review. This pattern is
well reported across offshore venues. It is not quantified anywhere
official, and this is a factual report, not legal advice.

So SPY-USDT is **technically the easiest venue we could reach** (our
existing code already speaks this exact API) and simultaneously **the one
with the worst standing problem**. Both things are true and Wallace should
decide, not me.

---

## 4. EVERYTHING ELSE, RANKED

### Rank 1 — Alpaca paper trading. The shortest real path.

- Paper accounts are free, need no funding, and per Alpaca's own docs are
  open to anyone globally with just an email.
- Plain web API, the same shape as the BloFin client this bot already
  has. 200 requests a minute. Our two strategies fire 4 to 15 times a
  year each, so that ceiling is not remotely a constraint.
- Trades SPY and QQQ, supports fractional shares, so position size can be
  a few hundred dollars rather than a whole share count.
- Free market data includes over 7 years of historical bars, which also
  removes our dependence on the unofficial Yahoo Finance scraper.
- **The one real catch:** market orders are rejected outside regular
  trading hours. Only limit orders work in the pre-market and after-hours
  windows. Both of our strategies decide at a daily close and would fill
  at the next open, which is inside regular hours, so this is survivable.
  It must be checked on the real thing before it is trusted.
- **Blocker for me: it needs a sign-up. I did not create it and will not.
  That is Wallace's call and Wallace's hands.**

### Rank 2 — Tradier sandbox. The backup.

No account minimum. The sandbox is reached by pointing at a different web
address, with paper money and delayed prices. Simple. Delayed data makes
it worse than Alpaca for anything time-sensitive, but our signals are
daily-close decisions, so delayed data is tolerable.

### Rank 3 — Interactive Brokers paper, and micro S&P futures later.

More powerful than either of the above and the only route to real futures,
but three separate frictions:
- A live account has to exist before a paper account is provisioned.
- The API needs their gateway program running as a live process on a
  machine, unlike Alpaca's plain web API. That is a real operations job.
- Market data for US stocks costs money beyond the free non-consolidated
  feed.

On the futures themselves: the E-mini S&P is $50 per index point, so near
a 6800 index level one contract controls about **$340,000**. The Micro
E-mini is $5 per point, about **$34,000** per contract. There is nothing
smaller. Against position sizes of a few hundred to a few thousand
dollars, even the micro is far too big, so futures are not the first step
regardless of how good the API is. Futures run Sunday 6pm to Friday 5pm
Eastern with a one-hour maintenance break each day, which is why they
barely gap.

### Rank 4 — BloFin SPY-USDT on the real host.

Technically the closest thing to plug-and-play we have, 24 hours a day,
20x leverage available, and our code already talks to it. Held back by
the US-person restriction above, by there being **no practice version at
all** (any test is real money from the first order), by $652,638 a day of
turnover, and by costing three and a half times a stock broker.

### Ruled out

- **Schwab / thinkorswim** — its developer API supports live trading only.
  The paper simulator is click-only and a bot cannot reach it.
- **Robinhood** — no official API, and their terms prohibit automated
  access. Community libraries break and accounts get suspended.
- **TradeStation** — API keys reportedly require a funded live account
  around $10,000. The simulator is fine once you are past that gate; the
  gate is the problem.
- **tastytrade sandbox** — wipes every position and balance every 24
  hours. Our strategies hold 1 to 10 days. It cannot hold the trade.
- **E*TRADE sandbox** — returns canned responses, not simulated fills.
- **Every offshore crypto venue that lists an S&P product** (Bybit,
  Gate.io, MEXC, KuCoin, Hyperliquid, Backed/xStocks, Ondo's offshore
  product, Swarm) — all state that US persons are excluded.
- **Ostium** — has a genuine S&P perpetual using licensed index data, but
  it suffered an $18 million oracle-manipulation exploit on 2026-07-15
  that halted trading. Its US-person status could not be verified. Two
  strikes.

### One to look at properly another day

**Dinari** is a Delaware-registered broker-dealer and SEC-registered
transfer agent issuing tokenized US shares to US persons. It is a licensed
US path rather than an offshore workaround, which makes it different in
kind from everything in the ruled-out list. Nobody has checked whether it
has an API a bot can drive, and that is the question worth answering.

---

## 5. THE SHORTEST PATH, STATED PLAINLY

From "we have a validated S&P edge" to "the bot can take that trade":

1. **Wallace opens an Alpaca paper account.** Free, unfunded, minutes.
   I cannot do this step and did not attempt it.
2. He gives the bot the paper key.
3. Someone writes an Alpaca order adapter. It is small: our strategies
   decide at a daily close and send one market order at the next open.
   The existing BloFin client is the template.
4. Confirm on the real thing that a market order at the open behaves the
   way the backtest assumed, and that the daily bars Alpaca returns match
   the ones the research used.
5. Run both edges on paper for a few months. Both fire rarely, so this
   takes real calendar time and cannot be rushed.

Everything else on the list is either slower, gated behind money, or
gated behind a rule about who is allowed to trade there.

**One number to carry into that decision, from step 362:** at a stock
broker's 0.04% round trip, both edges clear our "profit must be at least
five times the cost of trading" bar comfortably. At BloFin's 0.1413%
round trip, the dip-buy still clears it at 6.2 times, but the
turn-of-month edge drops to 4.2 times and **fails**. The venue choice is
not cosmetic. It decides which of our two edges is tradeable.
