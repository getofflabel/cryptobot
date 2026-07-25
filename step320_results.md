# step320_results.md — ROUND 320: Ethereum gets its own map

Ethereum specialist, 2026-07-25. Files: `step320_derive.py`,
`step321_eth_engine.py`, `step322_eth_shape_tests.py`,
`step323_eth_diagnostics.py`, `step324_eth_gate_ladder.py`.
Tables: `step320_derivation_table.csv`, `step320_table.csv`,
`step320_picks.csv`, `step320_chance_baseline.csv`,
`step320_gate_ladder_table.csv`.

## What this round did

Took five shapes that have survived somewhere else on this desk, rebuilt
each one on Ethereum, and re-derived every threshold from Ethereum's own
price behaviour instead of copying the number across.

| shape | where it survived |
|---|---|
| A volatility-gated trend rule | Bitcoin, 4h bars |
| B donchian channel breakout | gold, daily bars |
| C short-lookback RSI dip-buy | the S&P 500 tracker, daily bars |
| D flag touch (dip to the trend line) | Bitcoin, 2h bars |
| E turn of the month | the S&P 500 tracker, daily bars |

Conditions, every cell: market orders both ways (costs more), the stop is
a level off Ethereum's own confirmed swings via `exits.py` and never a
swept percentage, position size = dollars risked / distance to that stop
so leverage is an output, real funding, history split 60/20/20 in date
order, every choice made on the first 60%, the middle 20% read once, the
final untouched slice never loaded.

## The dials: what the number was, what it became

Full table in `step320_derivation_table.csv`.

| dial | in its home market | on Ethereum | why it moved |
|---|---|---|---|
| minimum 14-bar range to allow a trend entry | 1.50% of price on Bitcoin 4h | **1.80% on Ethereum 4h**, **0.83% on Ethereum 1h** | Ethereum's 4h range runs a median 2.09% of price against Bitcoin's 1.74%. Copying 1.50% would have left the door open on 76.4% of Ethereum's 4h bars and 18.4% of its 1h bars instead of matching Bitcoin's own 63.2%. |
| trailing-stop buffer | 1.50% on Bitcoin 4h | **1.80% on 4h, 0.84% on 1h** | 1.50% was 0.86 of one of Bitcoin's own 4h ranges. The same fraction of Ethereum's range is a different number on each timeframe. |
| donchian channel length | 20 daily bars on gold | **15 bars on Ethereum daily and 4h, 10 bars on 1h** | Gold's rule holds a position 34.2% of the time at 5.4 entries a year. These are the lengths that put Ethereum in the market for the same share of the time. |
| RSI(2) entry trigger | below 5 on the S&P daily | **below 5.30 daily, 4.01 on 4h, 4.42 on 1h** | "Below 5" fires on 5.05% of the S&P's days. On Ethereum's 4h bars the same number fires on 6.28% — 1.24x less picky. |
| RSI(2) exit trigger | above 65 on the S&P daily | **above 59.3 daily, 57.9 on 4h** | The S&P's exit is true on 44.8% of its days; these reproduce that on Ethereum. |
| trend filter behind the dip-buy | 200-day average on the S&P | **100 bars daily, 50 on 4h, 150 on 1h** | The S&P sits above its 200-day average 66.2% of the time. Ethereum sits above its own 200-bar average only 45.7% of the time on daily bars, so the ported filter is a far harsher gate than the one that was validated. Both the ported and the matched filter were tested. |
| flag-touch stop | 1.85 x Bitcoin's 1.19% 2h range = 2.20% | replaced entirely by a per-trade chart level; the equivalent figure on Ethereum would have been **1.81% on 1h, 3.87% on 4h** | recorded only to show how far the ported constant sat from Ethereum's own geometry. |
| turn-of-month window | 3 trading days either side (33.5% of the S&P's bars) | **3 and 5 calendar days either side (23.0% and 36.1% of Ethereum's bars)** | Ethereum trades every calendar day, so the same labelled window is a different slice of the year. Both widths tested. |

### A correction to the desk's own note on Bitcoin's gate

"Bitcoin's 1.5% volatility gate" is not one selectivity. Measured on
Bitcoin's own 4h bars, that constant let entries through on **63.2%** of
the first 60% of its history, **53.5%** of the middle 20%, and **24.3%**
of the final fifth. Bitcoin's volatility decayed across its own history,
so the constant grew steadily pickier over time without anyone changing
it. Round 170's notes record 18.7%, which matches none of those windows.
Because "match Bitcoin's selectivity" therefore has four defensible
answers, all four were tested as a declared ladder (`step324`).

## Results

49 unique cells. Verdicts by family, using the pre-registered rule (the
cell with the best average profit per trade on the first 60% that also
has at least 30 trades there, then one reading of the middle 20%):

| family | pick | first 60% | middle 20% | verdict |
|---|---|---|---|---|
| A volatility-gated trend | 4h, 20/100, gate 1.80% | 33 trades, +$13.12/trade | 12 trades, +$6.40/trade | **REJECTED ON THICKNESS** — positive both windows but the profit is 0.97x the cost of trading, under the 5x bar |
| A2 gate ladder | 4h, 10/50, gate 2.86% (matched to Bitcoin's recent fifth) | 34 trades, +$55.47/trade | 7 trades, -$68.71/trade | **NOT ENOUGH TRADES** on the middle 20%, and negative there |
| B donchian breakout | 4h, 20-bar channel | 125 trades, +$29.64/trade | 43 trades, -$10.60/trade | **DIES** |
| C RSI dip-buy | 4h, RSI(2)<5 above the 200-bar average | 68 trades, -$5.43/trade | 25 trades, -$32.95/trade | **DIES** — the best cell loses money on the first 60% already |
| D flag touch | 4h, 80-hour trend line | 138 trades, -$0.51/trade | 43 trades, -$35.27/trade | **DIES** — first transfer test this shape has ever had, and its first test at market-order costs |
| E turn of the month | daily, 5 days either side | 38 trades, +$58.70/trade | 13 trades, -$74.19/trade | **DIES** |

### Compared against entering at random times

30 random-timing draws per exit shape, same number of entries, same
windows, same chart stop and market-order costs:

| shape | both windows positive by luck alone |
|---|---|
| 4h trend-shaped (trailing chart stop, ride until stopped) | **30% of draws** |
| 1h dip/flag-shaped (fixed chart stop, 3:1 target, 48h cap) | 0% of draws |
| daily calendar-shaped (fixed chart stop, 7-day hold) | 20% of draws |

Applying each cell's own control to this exact grid, **luck alone would
produce about 7.8 cells positive on both windows. The grid produced 4.**
The round came in below chance. That is the honest headline and it is the
finding, not a footnote to one.

## The four cells that were positive on both windows anyway

None is claimed. All four are inside what chance produces at this grid
size, and only one of them was the pre-registered pick.

| cell | first 60% | middle 20% | profit next to trading cost (middle 20%) |
|---|---|---|---|
| A 4h 20/100 gate 1.80% (**the pick**) | 33 trades, +$13.12 | 12 trades, +$6.40 | 0.97x — reject |
| A 4h 10/50 gate 1.80% | 74 trades, +$3.08 | 25 trades, +$37.01 | 7.45x |
| A2 4h 10/50 gate 2.01% | 67 trades, +$27.38 | 20 trades, +$5.06 | 1.12x |
| B 4h 55-bar channel (longer control) | 75 trades, +$16.90 | 17 trades, +$40.17 | 7.61x |

Only `A 4h 10/50 gate 1.80%` is positive in both windows, above both
sample floors, and above the 5x cost bar. It was second on the first 60%,
not first, so under this round's own rule it is not the pick. Reaching
for it because it looked better in the middle 20% is exactly the move the
discipline forbids. It is logged as a candidate for a pre-registered
replication on a third and fourth asset, nothing more.

## Anatomy of the one shape with any life

Family A's pick, first 60%: 33 trades, 39% of them winners, worst
drawdown 9.1% of the account. The chart stop sat a median **11.00% of
price** below entry, so risking 2% of the account produced only **0.2x
leverage** — this is a slow, lightly-sized swing trade, not a levered
one. Median time in a trade 136 hours. Winners captured +13.58% of price
on average; losers gave back -4.89% of price. (Price moves, not changes
in a position's margin — at 20x those would differ twentyfold, but this
runs at 0.2x.) 30 of 33 trades ended at the trailing chart stop for
+$26.47 average; the 3 that ended on a trend flip averaged -$120.33.

## Turn of the month: the tendency is real on the first 60% and then inverts

Measured as a plain price tendency, no costs, unlevered:

- first 60%: 270 days inside the window averaged **+0.743%** price move a
  day against **-0.027%** outside it, t = 3.01.
- middle 20%: 87 days inside the window averaged **-0.766%** against
  **+0.160%** outside it, t = **-2.10**.

The sign flips completely. This is not a costed-strategy failure, it is
the underlying tendency reversing. Ethereum does not have the S&P's
turn-of-month effect. Dead, cleanly.

## Ethereum's own personality — a hypothesis with a first measurement

Round 173 already established that Ethereum does not lead or lag Bitcoin
at hourly resolution and does not amplify Bitcoin's moves during
Bitcoin's own panic windows. This round asked a different question that
Bitcoin structurally cannot ask of itself: **does Ethereum's recent
strength relative to Bitcoin change whether Ethereum's own trend entries
pay?** Measured on the first 60% only, on family A's 4h 10/50 entries:

| trailing window | Ethereum stronger than Bitcoin | Ethereum weaker | difference |
|---|---|---|---|
| 7 days | 43 trades, +$26.65/trade | 31 trades, -$29.61/trade | t = 1.39 |
| 30 days | 38 trades, +$0.78/trade | 34 trades, -$7.58/trade | t = 0.19 |
| 90 days | 29 trades, -$44.19/trade | 38 trades, +$17.76/trade | t = **-1.56** |

The sign flips with the lookback and nothing reaches significance. **This
is not a finding.** It is a hypothesis with a first measurement attached,
and the measurement does not support it as stated. If it is pursued, it
needs a pre-specified lookback, a third and fourth asset, and its own
round.

## Open items handed forward

1. Round 170's flagged follow-up — "retest the volatility-gated trend on
   Ethereum with a looser pair of averages to clear the sample floor" —
   is now **answered**. Faster averages do clear the floor, but only at
   the least selective gate, and the profit there is about the size of
   the cost of trading. The pickier gates that look best on the first 60%
   still cannot reach 8 trades in the middle 20% even with a 10/50 pair.
2. `A 4h 10/50 gate 1.80%` and `B 4h 55-bar channel` are the only two
   cells clearing the 5x cost bar in both windows. Neither is claimed.
   Pre-registered replication on Solana and one non-crypto market is the
   next honest step.
3. Ethereum still owns **zero** validated strategies of its own beyond
   the amplifier. Rounds 170 to 173 produced none across 18 families;
   this round produced none across 5 more. That is 23 families mapped and
   nothing standing. The map is now real, and most of it is marked dead.
