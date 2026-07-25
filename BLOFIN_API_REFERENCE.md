# BLOFIN API — WHAT THE EXCHANGE ACTUALLY GIVES US

Written 2026-07-25 after Wallace: *"you're gonna have to start studying
what's actually built into this API because it seems like you are trying
to do a lot of simple math that you're not really doing right by yourself."*

He was right. I spent an hour deriving margin, leverage and liquidation
numbers by hand, got the units wrong repeatedly, and told him his own
screen meant something it did not. **Every number I was computing is
already returned by the API.** This file exists so nothing in this repo
ever re-derives one of them again.

**RULE: if a field below exists, READ IT. Do not compute it.**

---

## THE ONE THAT CAUSED ALL THE CONFUSION

`unrealizedPnlRatio` is **profit and loss as a fraction of INITIAL MARGIN**,
not of price. It is exactly the percentage shown on the BloFin screen.

Verified live on the open BTC short:

| field | value |
|---|---|
| `unrealizedPnl` | -$10.87 |
| `initialMargin` | $204.52 |
| `unrealizedPnlRatio` | **-0.0533 → -5.33%** |
| check: -10.87 / 204.52 | -5.31% ✓ |

**So "down 5%" on screen = 5% of the margin posted, NOT a 5% price move.**
At 20x those differ by twenty times. A 5% screen loss on a $200 slot is
$10, from a 0.25% price move. It is not close to liquidation.

**WRITING CONVENTION, mandatory in all output and all reports:**
always give both, never one alone —

> "5% of margin = 0.25% price move at 20x"

---

## POSITION OBJECT — every field, verified live

From `GET /api/v1/account/positions`:

| field | meaning | do NOT recompute |
|---|---|---|
| `positions` | signed size in CONTRACTS (negative = short) | |
| `availablePositions` | closable size | |
| `averagePrice` | entry | |
| `markPrice` | exchange mark, drives PnL and liquidation | never use last-trade price instead |
| `breakEvenPrice` | entry adjusted for fees already paid | stop deriving this |
| `unrealizedPnl` | dollars | |
| `unrealizedPnlRatio` | **fraction of initial margin** (see above) | THE screen number |
| `initialMargin` | dollars posted | |
| `maintenanceMargin` | dollars required to keep it open | |
| `marginRatio` | exchange's own health number, higher = safer | |
| `liquidationPrice` | **the exchange tells us this outright** | NEVER estimate it |
| `leverage` | actual applied leverage | |
| `marginMode` | `cross` or `isolated`, PER POSITION | |
| `adl` | auto-deleverage queue rank 1-5 | |
| `realizedPnl` | closed portion | |
| `positionId`, `createTime`, `updateTime` | | |

Measured maintenance margin rate: **0.300% of notional** on BTC-USDT.

---

## INSTRUMENT SPEC — `GET /api/v1/market/instruments?instType=SWAP`

| field | BTC-USDT | why it matters |
|---|---|---|
| `contractValue` | 0.001 | **contracts x contractValue x price = notional.** Getting this wrong misprices everything |
| `minSize` / `lotSize` | 0.1 / 0.1 | order size must be a multiple of lotSize |
| `tickSize` | 0.1 | price must be a multiple of this |
| `maxLeverage` | 150 | BTC 150x, XRP and DOGE only 50x |
| `maxMarketSize` | 100,000 | a single market order can be this big. The old 5-contract clipping was superstition |
| `maxLimitSize` | 171,100 | |
| `state` | live | |

Contract values differ wildly per symbol: BTC 0.001, XRP 100, DOGE 1000.
**Never assume; always read `contractValue`.**

---

## BALANCE — `GET /api/v1/account/balance`

`balance` (total), `available` (free), `frozen`, `bonus`. Live: balance
$1,338.95, available $1,123.53.

---

## MARGIN MODE — measured, not assumed

Tested empirically on 2026-07-25 by opening a real 0.1-contract position:

| mode | leverage | liquidation distance (price) | in screen terms |
|---|---|---|---|
| **isolated** (XRP test) | 20x | **4.32%** | about -86% of margin |
| **isolated** (ETH, Wallace) | 20x | **4.66%** | about -93% of margin |
| **cross** (BTC, live) | 20x | **32.34%** | about -647% of margin |

Isolated walls the position off with its own margin, so liquidation sits
just past where the margin is exhausted. Cross lets the whole free balance
defend it, so the distance depends on how much of the account is
uncommitted — with a mostly-idle balance it is enormous.

**`_mode_for()` in blofin_private.py keeps whatever mode an EXISTING
position already has** (the exchange rejects changing it under a live
position) and only applies `MARGIN_MODE = "isolated"` when the symbol is
flat. That is why the live BTC short is `cross` while a fresh ETH entry is
`isolated`. Working as written, not a bug.

---

## WHAT THIS CHANGES IN THE CODE

Anywhere we currently derive one of these, replace it with the field:

- liquidation distance -> `liquidationPrice`
- position PnL % -> `unrealizedPnlRatio`
- margin posted -> `initialMargin`
- how close to death -> `marginRatio` / `maintenanceMargin`
- notional -> `contracts * contractValue * markPrice`
- max order size -> `maxMarketSize`

Any risk or sizing calculation that does not read from these is guessing,
and this repo has now demonstrated twice in one night that guessing
produces confident wrong answers.
