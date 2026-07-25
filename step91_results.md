# ROUND 91 -- backtesting a working pro's actual read

Source: the owner's followed analyst ("Prof Michael", The Real World), Friday end-of-day review. Every checkable descriptive claim in that review verified against real market data (SPY squeeze-to-744-then-reversal, QQQ new lows into the close, BTC's 3 red closes / close below 65K / retrace to Monday's low, oil and dollar reads). This round formalizes his STATED reasoning pattern into a mechanical, no-lookahead rule and tests whether it is profitable after costs -- descriptive accuracy and predictive edge are different skills, and this tests the second one.

## Mechanical rule tested

1. Rally's daily high tags a confirmed prior swing high (k=10, ~21-day window) within 1.5% -- "into resistance."
2. N consecutive red daily closes follow (swept N in [2,3,4]), counted from the day after the tag; once reached, the setup stays armed.
3. The most recent MINOR swing low formed during that rally leg (k=3, ~7-day window -- the "interim structure") breaks: CLOSED-basis (his stated discipline) tested head-to-head against a WICK-basis variant that is otherwise identical.
4. Forecast: does a confirmed lower minor swing high form below resistance before price closes back above it ("lower high before new high")?
5. Invalidation: a daily CLOSE above resistance x (1+3.0%) kills the setup -- the mechanical mirror of his own closed-basis invalidation framing ("unless BTC starts closing below 63.5").

Trade: SHORT at the bar after the trigger's open. Stop above resistance, target at the rally's origin swing low ("next major level"). Both distances are the TRAIN-only median % from entry close to that level (+0.5% stop buffer), fixed across train+val, capped at 8.0%/30.0% -- the engine's documented one-stop-per-run limitation, same approximation every prior round uses. MAX_HOLD=45 days.

## Data & split

BTC: bitstamp daily spot, 5439 bars, 2011-09-02 to 2026-07-23 (14.9y -- chosen over the shorter bybit perp cache because this is a rare daily pattern and it needs history to clear the trade floors). Train ends 2020-08-08, val ends 2023-08-01. Test (final 20%) is SEALED, never sliced by this script. Spot has no real funding history; the engine's conservative flat-funding default is used (same simplification step74 stated for this same cache).

ETH (mandatory transfer): bybit ETHUSDT daily perp, 1957 bars, 2021-03-15 to 2026-07-23, with REAL funding via align_funding (cache hit).

## BTC results, all cells

| asset   |   N_red | basis   |   n_events |   hit_rate% |   resolved_n |   inconclusive_n |   stop% |   target% |   tr_n |   tr_exp |   tr_win% |   tr_ret% |   tr_dd% |   va_n |   va_exp |   va_win% |   va_ret% |   va_dd% |   med_hold_h |   trades/yr | verdict             |
|:--------|--------:|:--------|-----------:|------------:|-------------:|-----------------:|--------:|----------:|-------:|---------:|----------:|----------:|---------:|-------:|---------:|----------:|----------:|---------:|-------------:|------------:|:--------------------|
| BTC     |       2 | close   |          3 |     +100.00 |            3 |                0 |   +8.00 |     +7.25 |      1 |  -920.40 |     +0.00 |     -9.20 |   -11.59 |      2 |  +714.18 |   +100.00 |    +14.28 |    -3.75 |      +408.00 |       +0.25 | INSUFFICIENT-SAMPLE |
| BTC     |       2 | wick    |          5 |     +100.00 |            5 |                0 |   +7.96 |    +18.33 |      2 |  +344.26 |    +50.00 |     +6.89 |   -12.31 |      2 |  +360.73 |    +50.00 |     +7.21 |   -16.52 |      +576.00 |       +0.34 | INSUFFICIENT-SAMPLE |
| BTC     |       3 | close   |          3 |     +100.00 |            3 |                0 |   +8.00 |     +7.25 |      1 |  -920.40 |     +0.00 |     -9.20 |   -11.59 |      2 |  +714.18 |   +100.00 |    +14.28 |    -3.75 |      +408.00 |       +0.25 | INSUFFICIENT-SAMPLE |
| BTC     |       3 | wick    |          4 |     +100.00 |            4 |                0 |   +8.00 |    +13.10 |      2 |  +106.64 |    +50.00 |     +2.13 |   -11.59 |      2 |  +146.72 |    +50.00 |     +2.93 |   -16.56 |      +504.00 |       +0.34 | INSUFFICIENT-SAMPLE |
| BTC     |       4 | close   |          2 |     +100.00 |            2 |                0 |   +8.00 |    +30.00 |      0 |    +0.00 |     +0.00 |     +0.00 |    +0.00 |      2 |  -824.21 |     +0.00 |    -16.48 |   -23.06 |      +396.00 |       +0.17 | INSUFFICIENT-SAMPLE |
| BTC     |       4 | wick    |          3 |     +100.00 |            3 |                0 |   +8.00 |    +18.96 |      1 |  -115.98 |     +0.00 |     -1.16 |   -13.23 |      2 |  +384.36 |    +50.00 |     +7.69 |   -16.56 |      +624.00 |       +0.25 | INSUFFICIENT-SAMPLE |


## Closed-basis vs wick-basis -- the discipline priced in dollars

Same N, same resistance/interim/target levels, same costs -- the ONLY difference is whether the interim structure must break on a CLOSE (his stated rule) or merely get wicked through intrabar. Pooled train+val, BTC:

|   N_red |   closed_total_$ |   closed_n |   closed_exp |   wick_total_$ |   wick_n |   wick_exp |   closed_minus_wick_$ |
|--------:|-----------------:|-----------:|-------------:|---------------:|---------:|-----------:|----------------------:|
|   +2.00 |          +507.95 |      +3.00 |      +169.32 |       +1409.97 |    +4.00 |    +352.49 |               -902.02 |
|   +3.00 |          +507.95 |      +3.00 |      +169.32 |        +506.72 |    +4.00 |    +126.68 |                 +1.23 |
|   +4.00 |         -1648.41 |      +2.00 |      -824.21 |        +652.74 |    +3.00 |    +217.58 |              -2301.15 |


## Forecast: "lower high before new high" hit rate (train+val, BTC)

| N_red | basis | events | resolved | hit rate | inconclusive |
|---|---|---|---|---|---|
| 2 | close | 3 | 3 | 100.0% | 0 |
| 2 | wick | 5 | 5 | 100.0% | 0 |
| 3 | close | 3 | 3 | 100.0% | 0 |
| 3 | wick | 4 | 4 | 100.0% | 0 |
| 4 | close | 2 | 2 | 100.0% | 0 |
| 4 | wick | 3 | 3 | 100.0% | 0 |


## Verdict counts

SURVIVOR: 0 | INSUFFICIENT-SAMPLE: 6 | FAIL: 0

No cell cleared both TRAIN-positive AND VAL-positive expectancy with the minimum trade floors. No ETH transfer to run -- there is nothing to transfer.


## Plain verdict

**The mechanical version of this method does NOT show a profitable edge after costs on either asset, in the cells tested.** His descriptive read of Friday's tape was accurate; that is a different skill from this specific mechanical translation of his method having positive expectancy. See per-cell numbers above for exactly where it failed (train sign, val sign, or sample size) before concluding the method itself is broken versus this particular operationalization of it.
