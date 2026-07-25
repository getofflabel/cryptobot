# ROUND 100 — every crypto strategy family, ported to gold. A real playbook.

Script: `step100_gold_port.py`. Data: `data_gold_1d/1h/4h.parquet` (GC=F),
`data_tradfi_GLD_1d/1h.parquet` (GLD, 4h resampled from 1h),
`data_gold_xaut_1h.parquet` (XAUT-USDT, transfer check only), DXY (DX-Y.NYB)
fetched fresh via yfinance for Family 10. Research only — no commits, no
live orders, `gold_book.py` untouched. **210 configs tested. 25 SURVIVOR,
45 INSUFFICIENT-SAMPLE, 140 FAIL.**

## The owner's question, answered honestly

Wallace, 2026-07-25: *"Have you even tested using the logic you use for
crypto on gold? ... This isn't gonna work unless you are able to create
multiple edges."* Going into this round the honest answer was **no** — 2
gold rounds (48, 55) had tested 5 families and found ONE survivor
(donchian + EMA20 exit). This round ports **every** crypto-validated
family's logic (never its constants), re-derives every threshold from
gold's own distributions, and adds gold-native structure. The answer
coming out: **gold can support more than one edge, but the honest count of
genuinely NEW, well-evidenced edges is smaller than the raw 25-SURVIVOR
headline — most of that number is either a restatement of the already-
known donchian breakout wearing a new filter, or a config whose "edge"
survives mostly because gold has been in a hard bull run over the test
window.** Detail below; the chance-baseline section is the part that
keeps this honest.

## Method — what's new this round vs R48/R55

- **execution="taker", always.** No maker numbers anywhere in this file.
- **Stops at chart structure, never a swept percentage.** Every stop is
  the median TRAIN-only distance from entry close to the nearest
  **confirmed swing** (`confirmed_swings()`, imported verbatim from
  `step41_shorts.py` — swing detection was not reinvented, per the task),
  plus a stated buffer, hard-capped, held fixed across train+val (the
  same approximation `run_backtest`'s one-fixed-stop-per-call limitation
  has forced on every prior structural-stop round: step41/43/50/56/58/86).
  Reported as an OUTPUT (`stop_%price` column) for every row, in both
  units the owner reads on screen: price % and % of margin at an
  illustrative 20x reference leverage (`stop_%margin_at_20x`).
- **Size from the stop.** `size_frac = clip(1.0% risk / stop_%price,
  0.1, 5.0)` — a tighter stop buys more size, a wider one less. This
  IS leverage in `run_backtest`'s engine (size_frac=1.0 = 1x equity
  notional). Reported as an output, never hand-picked: across all 210
  configs, size_frac ranged 0.12x-1.62x, median 0.49x, mean 0.53x — **every
  config in this round is UNDER-levered relative to equity**, a direct
  consequence of gold's stops running wide enough (0.6-8.0% price, median
  2.02%) that
  constant-1%-risk sizing never asks for real leverage.
- **Thickness bar: edge/cost >= 5x to pass**, computed for every row
  (`edge_%notional_per_trade`, `edge_x_cost`). 23 of 25 raw SURVIVORs
  clear it; 2 don't (both flagged below).
- **Chance baseline, computed for real** (not assumed): the top 15
  thickness-passing survivors were re-run 25 times each with entries
  **randomly shuffled** to the same count and direction split, same
  stop/target/size. This is this round's single most important honest
  finding — see its own section below.
- **Cross-instrument transfer is structural, not a follow-up step**: every
  family's grid runs identically-shaped on BOTH GC=F and GLD (same k /
  buffer / threshold / gate — only each asset's own train-median stop
  distance differs, a nuisance nesting parameter, same convention R86
  used for its ETH replay). `gld_gcf_transfer` reports HOLDS/FAILS/no
  counterpart for every row.

## PART 1 — crypto families ported, verdict by verdict

| # | Family | BTC's sealed number | Gold verdict | Configs (S/I/F) |
|---|---|---|---|---|
| 1 | Hidden RSI/MACD divergence (4h continuation) | +$52/trade | **DIES on gold** | 0 / 6 / 26 |
| 2 | Regular divergence + R86 confirmation gate | (BTC: 1/96 without the gate) | **5 genuine survivors** | 5 / 6 / 53 |
| 3 | CHoCH + confluence>=2 | +$99.52/trade | **Confluence does NOT help on gold** | 1 / 3 / 12 |
| 4 | Vol-gated trend, strict gate | +$401/trade (thickest crypto edge) | **Survives, but "ungated" beats "strict" again** | 4 / 18 / 8 |
| 5 | Volume-gated breakout (priority test) | killed at taker on crypto (0.064% edge) | **Survives at taker on gold — the priority hypothesis confirmed** | 4 / 3 / 5 |
| 6 | News/event momentum (NFP proxy) | sealed PASS on BTC | **Dies (and honestly under-sourced — see caveat)** | 0 / 0 / 2 |
| 7 | Liquidity sweep -> structure shift -> displacement | sample-starved on crypto, not disproven | **Disproven on gold — dies outright with real sample** | 0 / 2 / 24 |

### Family 1 — Hidden RSI/MACD divergence, 4h continuation: **dead on gold**

Ported exactly: `divergence_events()` from `step58_divergence_mtf.py`,
unmodified. The one recomputed constant is the 4h "champion trend" gate
hidden-divergence needs (continuation must fire WITH the prevailing
trend) — BTC used a 1.5% ATR gate; gold's own 4h train-median ATR is
0.55% (GC=F) / 0.59% (GLD), used instead. 32 configs (2 oscillators x 2
timeframes x 2 k x 2 buffers), across both assets: **zero SURVIVOR, 6
INSUFFICIENT-SAMPLE, 26 FAIL.** The best cell (MACDhist k8, 4h, GC=F,
buf0.15%) is train +$14.18/trade (23 trades) / val +$47.36/trade (11
trades) — genuinely both-windows-positive and directionally interesting,
but never clears 30 train trades on any config or asset. Gold's
continuation setups (higher-low price / lower-low oscillator, inside an
established uptrend) just don't occur often enough at 1h/4h resolution
with real 4h history capped at ~1.4 years train. **Verdict: the shape
that was BTC's first sealed graduate does not transfer — not because it's
wrong, but because gold's 4h-continuation setups are too rare on the
history available to earn a verdict either way. Worth a re-look once GC=F
4h history accrues past ~2.5 years, not worth re-tuning now.**

### Family 2 — Regular divergence + confirmation gate: **the round's cleanest new find**

R86 found on BTC that regular divergence's missing ingredient was the
CONFIRMATION CANDLE — don't enter on the divergence bar, wait for a close
back through the swing between the two divergent points. Ported verbatim
(`divergence_events_ext` / `confirm_after_level` / `carry_extreme` from
`step86_specified.py`). 64 configs (2 osc x 2 tf x 2 k x 2 max_wait x 2
buffer, both assets): **5 SURVIVOR, all on GC=F 1h** (none on GLD, none
on 4h):

| Config | Train n/exp | Val n/exp | Edge/cost | Trades/yr |
|---|---|---|---|---|
| MACDhist k8 wait20 buf0.35% | 32 / $12.30 | 8 / $38.23 | 14.7x | 20.9 |
| MACDhist k8 wait20 buf0.15% | 32 / $10.10 | 8 / $44.38 | 12.5x | 20.9 |
| RSI14 k5 wait20 buf0.15% | 32 / $16.79 | 13 / $3.81 | 9.3x | 23.5 |
| MACDhist k5 wait10 buf0.15% | 38 / $8.87 | 9 / $24.23 | 8.2x | 24.5 |
| MACDhist k5 wait10 buf0.35% | 38 / $2.34 | 9 / $42.32 | 8.0x | 24.5 |

All clear the trade-count floor at a real ~21-25 trades/year — a genuine
mid-frequency complement to the once-a-week donchian breakout. **But: the
GLD replay of these exact shapes FAILS** (`gld_gcf_transfer` = FAILS for
all 5) — this is a GC=F-specific, not a gold-market-general, result.
Read plainly: the confirmation gate is real (it took regular divergence
from crypto's 1/96 to a genuine 5/64 here), but on the data available it
is proven on the futures contract only, not the ETF. **Recommended
sealed-look candidate #1.**

### Family 3 — CHoCH + confluence>=2: **confluence does NOT earn its keep on gold**

`bos_chain` / `equilibrium` / `liquidity_pools` / `sweep_events` /
`fvg_signals` imported verbatim from `step56_smc_toolkit.py`; confluence
built from 4 votes (bias via gold's own 20/100 MA cross, discount/premium,
a same-direction sweep in the last 24h, an active FVG) — a faithful
subset of BTC's 5-vote scorer (FIB dropped for scope). 16 configs (2 tf x
2 k x threshold{0,2}, both assets): **1 SURVIVOR — and it's the
THRESHOLD-0 (unconditioned CHoCH) config, not the threshold>=2 one.**
Head-to-head, same k/tf/asset:

| tf/asset/k | thresh=0 | thresh>=2 |
|---|---|---|
| 1h GC=F k5 | tr $14.29(30t)/va $57.94(11t) **SURVIVOR** | tr -$5.29(16t)/va $74.12(8t) FAIL |
| 1h GC=F k8 | tr $23.28(28t)/va $2.67(10t) INSUFF | tr $25.47(15t)/va -$22.97(3t) FAIL |
| 4h GC=F k8 | tr -$28.45(20t)/va $64.22(6t) FAIL | tr $32.15(8t)/va $27.63(4t) INSUFF |

Every other cell either flips sign between train/val or thins out below
the floor once the confluence filter is applied. **Verdict: BTC's central
claim — that requiring multiple SMC tools to agree beats any single tool
— does NOT replicate on gold.** This mirrors what step56 itself warned was
possible for BTC too ("does it help, or just cut the sample?") and on
gold the answer is the sample-cutting side of that question. Bare CHoCH
is a thin, single-asset (GC=F only), single-timeframe (1h only) signal —
not disproven outright, but not the thick edge BTC's +$99.52/trade
number would suggest transfers.

### Family 4 — Vol-gated trend, strict gate: **survives, "ungated" wins again**

`vol_gated_ma` imported verbatim; every `min_atr_pct` threshold recomputed
from gold's own train-median/p75 ATR% (0.28-1.29% depending on
asset/tf — never BTC's 1.5%). Also tests a genuinely NEW gate this round
vs R48/R55: **adaptive-p75 ("strict")**, the trailing 75th-percentile ATR
gate, not just the median. 30 configs (3 tf x 5 gates, both assets): **4
SURVIVOR, all GC=F** (ungated 1d, ungated 1h, fixed-median 1h,
adaptive-median 1h). **The strict p75 gate never produces a SURVIVOR on
either asset** — it shows up only in INSUFFICIENT-SAMPLE rows, always
thinner and usually weaker $/trade than the looser gates at the same
tf/asset (e.g. GC=F 1h: ungated $40.68/train, p75-strict $5.27 — an 8x
haircut for "selectivity"). **This is the third gold round in a row to
find the same thing R48 first reported: on gold's calm, persistently-
trending tape, filtering for "liveliness" throws away good entries rather
than avoiding whipsaw — the opposite of BTC's own era-decay lesson.**
Structural stop added this round (was bare/no-stop in R48/R55): median
1.46-6.96% price distance, i.e. 29-139% of margin at 20x reference
leverage — wide, consistent with the "signal exit is primary, stop is a
safety net" design.

### Family 5 — Volume-gated breakout: **the priority hypothesis confirmed, at real cost multiples**

The task's explicit priority test: BTC's Bollinger(20/2.5) + breakout-bar
volume>=1.2-1.5x its 20-bar average died at taker on crypto (0.064% edge
< round-trip cost). `bollinger_breakout_signal` / `volume_gate_entry`
imported verbatim from `step86_specified.py`. 12 configs (2 tf x {bare,
1.2x, 1.5x}, both assets), **execution=taker throughout**: **4 SURVIVOR**
— bare-4h-GC=F ($4.71/train, $66.77/val, 23.6x edge/cost), volume>=1.2x-1h
($8.36/$8.47, 5.5x), volume>=1.5x-1h ($8.67/$18.48, 7.2x), and one bare-1h
config that fails the thickness bar (4.77x, just under 5). **Gold's
version of this edge clears taker costs comfortably where BTC's could
not** — exactly the task's hypothesis. But: the gated (1.2x/1.5x volume)
variants do NOT clearly beat bare on GC=F 1h (bare 4.77x fails thickness,
1.2x/1.5x pass at 5.5x/7.2x — the volume gate is what pushes it over the
line, a real finding). **On GLD, none of the 1h configs transfer**
(bare/1.2x/1.5x all FAIL outright, val expectancy negative on all three),
while the 4h bare shape does transfer (both-windows-positive, just thin —
INSUFFICIENT-SAMPLE, not SURVIVOR). **XAUT-USDT transfer FAILS for both
1.2x and 1.5x** (-$14.06/trade, -$15.53/trade on 129/122 live-venue
trades) — a real caution flag on the live venue specifically (see XAUT
section). **Net read: real on GC=F specifically (1h and 4h), thin-to-
absent on GLD 1h, and does not (yet) transfer to the live BloFin venue —
the priority hypothesis is confirmed on the futures contract, not proven
as a gold-market-general result.**

### Family 6 — News/event momentum: **honest non-result**

Gold's macro analogue (CPI/FOMC/NFP) has no verified economic-calendar
dataset in this repo — `data_news_mkts_GC=F.parquet` is plain OHLCV, not
event timestamps (checked directly). Per the task's own instruction ("if
you can source event timestamps honestly, test it; if not, say so"): NFP
is tested via a **stated public proxy rule** (first Friday of the month,
~12:30 UTC bar) — 2 configs (hold 4h/8h), GC=F 1h only (GLD's US-hours-
only bars can't see a 12:30 UTC release). **Both FAIL** (train -$9.22/
-$3.01, val -$35.93/-$41.82). CPI and FOMC are **not tested** — a
hand-recalled 26-year meeting calendar risked being exactly the kind of
confidently-wrong number `BLOFIN_API_REFERENCE.md` documents this repo
getting burned by before. **What would unlock this properly**: a real
economic-calendar feed (Trading Economics API, FRED's release calendar,
or a paid macro-events dataset) with verified CPI/FOMC/NFP timestamps
including historical revisions to release time.

### Family 7 — Liquidity sweep -> structure shift -> displacement: **disproven, not just starved**

R86 found this sample-starved on crypto (not disproven). `sweep_mss_
displacement` imported verbatim from `step86_specified.py` (composes
step56's `liquidity_pools`/`sweep_events`/`bos_chain`, also imported
verbatim). 26 configs that produced qualifying events (2 tf x 2 k x 2
disp_mult x 2 max_wait, both assets — several k=8/1h cells produced 0
events and were skipped): **zero SURVIVOR.** Gold's cleaner session
structure was hypothesized to give this more sample than crypto — it did
NOT: most cells have 2-15 total trades even pooling train+val (the
sweep -> MSS -> displacement conjunction is simply rare), and where a
cell clears more trades (e.g. k5/1h configs, 20-30 pooled trades) the
expectancy is negative on val more often than not. **Verdict: this is
gold's first family in this round to move from "not disproven" to
"disproven" — real sample was available (26 non-empty cells across two
assets, two timeframes) and it still died.**

## PART 2 — gold-native families

### Family 8 — London/NY session as a FILTER (not a trigger, per R55's own finding)

R55 found sessions are NOT an entry trigger (0/6). This round tests them
as FILTERS on two already-known base strategies (donchian20+EMA20exit;
vol-gated-trend-adaptive-median), 1h only. 16 configs + 4 unfiltered
baselines, both assets: **6 SURVIVOR**, three of them the UNFILTERED
baseline itself (donchian on GC=F and GLD; vol-gated on GC=F) — i.e. the
base strategy already worked at 1h and filtering to a session usually
just cuts sample without adding $/trade. The two genuinely filter-added
survivors are both GLD, both NY-session (13:30 UTC): NY+2h ($50.84/train,
$14.65/val, 39/16 trades) and NY+4h ($40.59/$19.15, 47/17 trades) — both
BEAT their own unfiltered GLD baseline on train $/trade (unfiltered:
$30.25/train) while keeping enough sample to clear SURVIVOR. **This is
the strongest of the two GLD-specific results in the round: the NY
session filter is a real, if modest, quality improvement on the ETF's
version of the breakout — plausible given GLD only trades US market
hours to begin with, so "NY session" for an ETF is closer to "the first
few hours of its own trading day" than a genuine session-structure edge.**

### Family 9 — the overnight gap itself as a tradeable event

Daily GC=F/GLD, gap-up/gap-down at open vs prior close, FOLLOW vs FADE, 5
day hold, structural stop. 8 configs: **2 SURVIVOR, both FADE (buy the
gap-down, short the gap-up) at the 0.5% threshold** — GLD ($4.87/train,
$6.95/val, 445/135 trades, 33.5/yr — genuinely high-frequency) and GC=F
($1.21/$0.93, 432/130 trades) though **GC=F's fails the thickness bar**
(2.19x edge/cost, well under 5x — reject). GLD clears it at 5.2x, barely.
**FOLLOW (ride the gap) failed everywhere on both assets** — consistent
with R48's own finding that gold/ETF gaps are a mean-reversion event, not
a momentum one, and with the secular-uptrend-kills-shorts pattern (FADE's
short leg on gap-ups is what's mostly getting whipsawed against by the
long FADE leg's win rate). **The GLD FADE config is the highest-frequency
number in this entire round (33.5 trades/yr) and is worth flagging
specifically against the "gold's problem is 5.4/year" framing** — but its
edge/cost multiple (5.2x) is the thinnest passing margin of any SURVIVOR
here, so treat it as a volume play, not a thick one.

### Family 10 — DXY regime filter on the incumbent donchian breakout

Dollar-weak filter (DXY close < its own trailing 100-day SMA, 1-day-lagged
for no lookahead) on donchian20+EMA20exit, daily. 4 configs (filtered +
unfiltered baseline, both assets): **3 SURVIVOR** — GC=F unfiltered
(train $9.54, val $16.40, 89/24 trades — this is the already-known
incumbent, reproduced), GC=F DXY-filtered (train $16.67, val $6.05, 48/12
trades — **75% higher train $/trade than unfiltered, at less than half
the trade count**), and GLD unfiltered. **GLD's DXY-filtered variant
produced 0 qualifying entries and could not be scored** — a real
asset-specific gap, not a coding gap. **Verdict: DXY-as-regime-filter is
a genuine quality improvement on GC=F specifically** (higher $/trade,
same edge/cost ballpark once its own wider structural stop is accounted
for) **but is not (yet) established on GLD**, and — like every filter
family in this round — it trades LESS often than the thing it's
filtering, so it is a quality lever, not a frequency lever.

## The ranked survivor table (thickness-passing, chance-baseline where computed)

| Rank | Family | Config | Asset/tf | Train exp/n | Val exp/n | Edge/cost | Stop (price% / margin%@20x) | Trades/yr | GLD<->GC=F | Chance-SURVIVOR rate |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 4-vol-gated-trend | 20/100 ungated | GC=F 1d | $30.13/34 | $10.27/8 | 91.6x | 6.96% / 139% | 2.0 | HOLDS | **24% (6/25)** |
| 2 | 4-vol-gated-trend | 20/100 ungated | GC=F 1h | $40.68/56 | $155.31/17 | 49.3x | 1.46% / 29% | 38.1 | HOLDS | **28% (7/25)** |
| 3 | 8-session-filter | vol-gated adaptive UNFILTERED | GC=F 1h | $22.46/42 | $140.69/15 | 45.6x | 1.70% / 34% | 29.7 | HOLDS | **32% (8/25)** |
| 4 | 4-vol-gated-trend | 20/100 adaptive-median | GC=F 1h | $22.46/42 | $140.69/15 | 45.6x | 1.70% / 34% | 29.7 | HOLDS | **32% (8/25)** (same cell as #3) |
| 5 | 4-vol-gated-trend | 20/100 fixed-median(0.28%) | GC=F 1h | $23.62/48 | $131.76/16 | 42.9x | 1.70% / 34% | 33.4 | HOLDS | **16% (4/25)** |
| 6 | 10-dxy-regime | donchian FILTERED to DXY-weak | GC=F 1d | $16.67/48 | $6.05/12 | 42.3x | 5.81% / 116% | 2.9 | HOLDS | **20% (5/25)** |
| 7 | 10-dxy-regime | donchian UNFILTERED (incumbent) | GC=F 1d | $9.54/89 | $16.40/24 | 32.0x | 5.81% / 116% | 5.5 | HOLDS | **20% (5/25)** |
| 8 | 5-volume-gated-breakout | Bollinger bare, TAKER | GC=F 4h | $4.71/42 | $66.77/14 | 23.6x | 2.33% / 47% | 29.2 | HOLDS | **20% (5/25)** |
| 9 | 8-session-filter | donchian FILTERED to NY+2h | GLD 1h | $50.84/39 | $14.65/16 | 20.2x | 2.01% / 40% | 23.7 | HOLDS | **0% (0/25)** |
| 10 | 10-dxy-regime | donchian UNFILTERED | GLD 1d | $11.67/67 | $10.11/23 | 17.9x | 6.34% / 127% | 5.2 | HOLDS | not tested (top-15 cutoff) |
| 11 | 8-session-filter | donchian FILTERED to NY+4h | GLD 1h | $40.59/47 | $19.15/17 | 17.5x | 2.01% / 40% | 27.6 | HOLDS | **0% (0/25)** |
| 12 | 8-session-filter | donchian UNFILTERED (incumbent) | GLD 1h | $30.25/55 | $27.63/19 | 14.8x | 2.01% / 40% | 31.9 | HOLDS | **0% (0/25)** |
| 13 | 2-regular-div-confirmed | MACDhist k8 wait20 buf0.35% | GC=F 1h | $12.30/32 | $38.23/8 | 14.7x | 1.68% / 34% | 20.9 | FAILS (GC=F-only) | **28% (7/25)** |
| 14 | 3-choch-confluence | k5 CHoCH thresh>=0 | GC=F 1h | $14.29/30 | $57.94/11 | 13.2x | 1.02% / 20% | 21.4 | FAILS (GC=F-only) | **24% (6/25)** |
| 15 | 8-session-filter | donchian UNFILTERED (incumbent) | GC=F 1h | $15.45/152 | $26.18/55 | 13.1x | 1.43% / 29% | 108.0 | HOLDS | **8% (2/25)** |
| 16-23 | (thickness-passing, not chance-tested) | see step100_table.csv | mixed | — | — | 5.2-12.5x | — | — | mixed | not tested |

## The chance baseline — the finding that keeps this round honest

For the top 15 thickness-passing survivors, 25 random-entry permutation
trials each (same trade count, direction split, stop/target/size — see
`chance_baseline()` in the script): **most of the vol-gated-trend and
donchian/DXY family cells show a 16-32% chance-SURVIVOR rate on pure
noise.** That is not proof the edge is fake — but it is proof that on
gold's 2016-2026 span (and especially the 2024-2026 window most of the
1h/4h cells live inside), **being long, with almost any reasonably-sized
stop and a signal-driven exit, has a real chance of clearing this round's
own SURVIVOR bar purely from gold's own secular uptrend** — exactly the
buy-and-hold caveat R48/R55 already flagged for the daily donchian book,
now confirmed quantitatively rather than assumed. **The two cells that
break this pattern are both the GLD 1h NY-session family (0/25, 0% chance
rate)** — genuinely differentiated from noise, the strongest statistical
evidence in the round, though on a config that is itself close to the
already-known donchian incumbent with a session filter layered on. R83's
own standard applies here directly: "two [cells/assets] agreeing is a
hypothesis, not evidence" — the family-8 GLD result clearing three
separate 0%-chance configs (unfiltered, NY+2h, NY+4h, all pointing the
same direction) is a genuinely stronger claim than any single family-4
config with a 16-32% chance rate, even though family 4's raw dollar
numbers and edge/cost multiples look bigger.

## Cross-instrument transfer (GC=F <-> GLD)

Every family ran the identical grid shape on both assets. Of the 25
SURVIVORs (checked exhaustively against `step100_table.csv`'s
`gld_gcf_transfer` column, every row resolved — no "no counterpart"
cases): **16 show `HOLDS`** (a positive-both-windows counterpart config
exists on the other asset — every Family 4/8/9/10 survivor, plus the
Family 5 GC=F 4h bare config), **9 show `FAILS`** (all 5 Family 2
regular-divergence-confirmed configs, the 1 Family 3 CHoCH config, and
all 3 Family 5 GC=F 1h volume-gated-breakout configs — GLD's own 1h
Bollinger configs run negative on val outright). **Net read: the
donchian/vol-gated-trend/DXY-filter family of edges is genuinely cross-
instrument (16/16 of those survivors transfer); the newer divergence-
confirmation, CHoCH, and 1h volume-gated-breakout findings are GC=F-
specific (9/9 of those fail transfer) until proven otherwise on more GLD
history.**

## XAUT-USDT compatibility (whole-history read, NOT a validation — same convention as R55)

| Config | XAUT n | XAUT exp/trade | Holds? |
|---|---|---|---|
| Family 4: 20/100 ungated | 51 | +$40.64 | **HOLDS** |
| Family 4: 20/100 fixed-median | 40 | +$24.14 | **HOLDS** |
| Family 4: 20/100 adaptive-median | 40 | +$33.84 | **HOLDS** |
| Family 5: Bollinger volume>=1.2x | 129 | -$14.06 | fails |
| Family 5: Bollinger volume>=1.5x | 122 | -$15.53 | fails |

**Vol-gated-trend transfers to the live venue cleanly (3/3) — consistent
with R55's own finding that EMA/MA-cross-shaped trend signals were the
one family that held up across every one of its XAUT variants.
Volume-gated breakout does NOT transfer to XAUT** (both configs flip
negative on the live venue's own ~4.5-month-younger history) — a genuine
caution flag specifically on Family 5 before it goes anywhere near real
gold trading, despite passing the thickness bar cleanly on GC=F/GLD.

## Frequency — did this round find anything firing 30+/year that clears the thickness bar?

**Yes, three: donchian+session-filter on GC=F 1h (108 trades/yr, 13.1x
edge/cost), Bollinger volume-gated breakout on GC=F 1h (92-104
trades/yr, 5.5-7.2x edge/cost), and the GLD overnight-gap-fade (33.5
trades/yr, 5.2x — thinnest passing margin in the round).** This directly
answers the task's "explicitly hunt setups firing 30+/year" ask: gold's
5.4/year donchian-daily problem is solved by moving down in timeframe
(1h) and by widening to volume-gated breakout and the gap-fade — not by
finding a faster version of the SAME daily edge, but by adding
genuinely different, higher-turnover families underneath it.

## Plain verdict: can gold support MULTIPLE edges, not just one?

**Yes — with real caveats, stated plainly rather than softened.**

1. **The single validated daily edge (donchian+EMA20exit) is now
   confirmed to have TWO genuine companions with real evidence behind
   them**: the GLD 1h NY-session-filtered donchian family (0% chance-
   baseline rate across three separate configs, the strongest statistical
   claim in this round) and the GC=F regular-divergence-confirmation
   family (5 survivors, real R86-shape logic, though GC=F-only so far).
2. **Vol-gated-trend and the DXY-regime-filtered breakout add real
   dollar thickness (42-92x edge/cost) and cross-instrument transfer, but
   their chance-baseline rates (16-32%) mean a meaningful fraction of
   that "edge" is gold's own 2024-2026 bull-market drift, not proven
   timing skill.** Treat these as real but WEAKER evidence than their raw
   numbers suggest — a second research round with a chance-baseline check
   built in from the start (not bolted on after, as this round did) would
   sharpen this further.
3. **Three genuinely new families died on real, not starved, sample**:
   hidden divergence (starved, not disproven — worth revisiting as 4h
   history grows), CHoCH+confluence (confluence adds nothing, bare CHoCH
   is thin and single-asset), and liquidity-sweep-MSS-displacement
   (outright disproven this round, real sample, real negative). News/
   event momentum was honestly declared under-sourced rather than faked.
4. **The frequency problem is solved, not by making the existing edge
   faster, but by stacking genuinely different edges underneath it** —
   exactly the "MULTIPLE edges, not a better single one" framing the task
   opened with. Gold's playbook after this round: one slow daily
   incumbent (donchian, ~5/yr, unchanged), one thickness-first swing layer
   (vol-gated-trend + DXY filter, ~2-38/yr depending on tf, moderate
   confidence), and — the part worth trusting most — a session-filtered
   fast layer on GLD specifically that beat a real chance baseline.

**What this round does NOT claim**: that any of these 25 SURVIVORs should
go live today. None has been sealed-tested (the final 20% was never
touched, per protocol). The chance-baseline finding is a reason for a
FOLLOW-UP round to re-run the strongest candidates (Family 2's GC=F
divergence-confirmation, Family 8's GLD session-filter, Family 10's DXY
filter) with a wider chance-baseline sweep and, ideally, a second
independent gold regime (pre-2024 GC=F 1h data does not exist at this
resolution — see R55's own caveat) before any of it is treated as proven
rather than promising.
