# step63 results — round 63: GRAVEYARD REHABILITATION (BTC)

Companion to `step63_rehab.py`. Research only — no live orders, no commits.
Standard costs (CostModel defaults: 6bps taker/2bps maker, 1bp half-spread,
2bp slippage), execution="maker", real funding via `align_funding`. This
round has **no sealed test** — chronological 60/20/20 train/val/test split
on BTC 1h (55,451 bars, 2020-03-25 → 2026-07-22; train ends 2024-01-10, val
ends 2025-04-16), but this script only ever computes train (0:i_tr) and val
(i_tr:i_va); the final 20% is never touched. Gauntlet floor is **this
round's own numbers**: MIN_TRAIN_TRADES=15, MIN_VAL_TRADES=8 (looser than
the repo's usual 30/8, per the owner's explicit instruction — scenario
cells are inherently smaller samples).

**The owner's mandate, verbatim spirit**: "the known indicators are known
for a reason. You can't say they didn't help — you just haven't found the
RIGHT SCENARIO to use them. Go back in time and find those scenarios."
Seven tools that FAILED unconditional testing in earlier rounds (G1–G7) are
retried CONDITIONALLY inside 14 market-scenario cells each — same entry
rule, same costs, same stop/target geometry as their original burial; the
ONLY new variable is a scenario gate ANDed onto each tool's ENTRIES (an
open position is still managed by the tool's own exit/stop/target — the
same "the gate only guards the door" contract `strategy.vol_gated_ma` uses
for its own `entry_filter`).

This is an independent round: `step62_*` (the concurrent "scenario router"
agent, working from the same scenario brief) was never read, imported, or
touched. The classifier below is reimplemented from scratch in this file.

**Mid-round addition**: after the first pass of this round completed (6
rehabilitations found across 4 axes / 140 cell evaluations), a peer agent
relayed a mandatory owner addition — a 5th axis, SESSION — plus a required
new output: a marginal session-only cut for every one of the 10
tool-variants. Both were added and the full script re-run; this document
reflects the complete, final 5-axis picture. The original 6 rehabilitations
are unchanged (identical numbers, re-verified byte-for-byte on rerun);
SESSION added 6 more and flipped two tools from "stays buried" to
"rehabilitated" (G1-LONG, G7-donchian20 — see Sections 3/4).

---

## 1. The 5-axis scenario classifier, as actually implemented

**TREND** — 4h `vol_gated_ma(fast=20, slow=100, min_atr_pct=1.5,
allow_short=True)` sign AGREEING with the 4h BOS-chain (`bos_chain`,
imported from `step56_smc_toolkit.py`, k=8 — the same fixed "bias" k
step56's own `bias_series_4h` uses for this exact purpose; not swept, since
here TREND is a classification input, not the primary signal under test)
→ **trending-up** (champ=long AND BOS-chain bullish), **trending-down**
(champ=short AND BOS-chain bearish), **ranging** (everything else —
disagreement or flat). Read onto 1h with the standard "visible only at the
4h bar's CLOSE" `merge_asof` pattern (`champ_aligned`'s own convention: a
4h bar's label becomes visible at open_time + 4h, never before).

**VOL** — ATR%(14) vs its OWN trailing 365-day rolling median. Window =
`max(30, hours_to_bars(d, 365*24))` bars, `min_periods = max(30,
window//10)`, and the window **excludes the current bar** (`.shift(1)`,
same convention step57's Bollinger-bandwidth squeeze uses for its own
trailing-365d threshold) — no lookahead: only bars strictly before the
current one feed the median. Exact breakpoints: **quiet** (ratio <
0.67×), **normal** (0.67×–1.5×), **violent** (> 1.5×, the owner's mandated
breakpoint; 0.67 is this script's own reasonable choice for the quiet/
normal split — roughly the inverse of 1.5, stated plainly as a judgment
call, not derived). Computed natively on the 1h frame — every tool in this
round trades 1h, so no cross-timeframe VOL alignment is needed.

**NEWS-HEAT** — a WatcherGuru headline with `ai_relevant == True`
(`data_watcherguru_ai_tags.parquet` joined to `data_watcherguru_history.
parquet` on `message_id`) landing in the 2-hour window `(bar_time − 2h,
bar_time]` → **hot**. WatcherGuru's harvested history spans **2025-06-18 →
2026-07-23** (~13 months), verified programmatically at load time (printed
by the script). The "hot" cell is explicitly ANDed with that span; **no
"not-hot" cell is ever scored** — pre-span bars simply never qualify for
the hot cell, which is the honest behavior (they are never claimed to be a
real "not hot" measurement).

⚠️ **Critical limitation, discovered only once the script ran (see Section
5b)**: the WatcherGuru span (2025-06-18 → 2026-07-23) starts *after* this
round's val window ends (val ends 2025-04-16) and sits almost entirely
inside the **sealed 20% test region this script never touches**. The
practical result: the `news-hot(13mo-span)` cell has **zero train events
for every single tool** — NEWS-HEAT could not be evaluated for
rehabilitation in this round at all, despite being fully defined and
implemented. This is reported honestly below rather than glossed over.

**CROWD** — funding_bps (`align_funding`, `step11_round6.py`, native 8h
cadence) → **crowded-long** (≥ +1.5 bps/8h), **crowded-short** (≤ −0.5
bps/8h), **neutral** (otherwise).

**SESSION** (5th axis, added mid-round) — pure UTC calendar fact off each
bar's own timestamp, zero lookahead concern: **asia** (00:00–07:00 UTC),
**london** (07:00–13:00 UTC), **newyork** (13:00–21:00 UTC), **off-hours**
(21:00–24:00 UTC), with a **weekend override**: Sat/Sun UTC calendar day →
"weekend" regardless of clock hour, applied AFTER (and overriding) the
four clock buckets.

### Cell enumeration — 19 cells, identical set for every tool-variant

| # | Cell | Rationale |
|---|---|---|
| 1–9 | TREND(3) × VOL(3) | the core grid a trader reasons about first |
| 10 | crowded-long × violent | |
| 11 | crowded-short × violent | crowd positioning crossed with the vol regime, per the owner's "CROWD crossed with VOL" instruction |
| 12 | neutral-crowd × violent | |
| 13 | news-hot (13mo span) | see limitation above — always n=0 this round |
| 14 | ALL-violent (VOL=violent alone, any trend/crowd) | tests the owner's literal "violent-cell" hypothesis (G5, G7) as its own pooled cell, not crossed with anything |
| 15–19 | SESSION alone (asia/london/newyork/off-hours/weekend) | added mid-round. Each cell is simultaneously (a) a scenario cell in this same enumeration and (b) BY CONSTRUCTION the required "marginal session-only cut" — the tool's unconditional entry rule, all other axes pooled/ignored, split only by session — since it gates on session alone with no other condition ANDed in. One computation serves both asks; see the consolidated table in Section 2.5. |

19 cells were examined per tool-variant, every time, with no cherry-picking
after the fact — this list (14 original + 5 SESSION, added mid-round per
the owner's mandatory instruction) was fixed before any tool was rescored.

---

## 2. Per-tool results

Every tool's stop_pct/target_pct is derived ONCE from its UNCONDITIONAL
train-only reconstruction and held FIXED across the baseline and all 14
cells — re-deriving the stop per cell would be a second new variable
beyond the scenario gate, which would break the round's central discipline.

### G1 — Pin bars + engulfing at context levels
*Source: `step57_price_action.py`, `pin_bar_signals`/`engulfing_signals`
(imported, not reimplemented). step57_results.md: families 2a+2b, 112
configs, 0 survivors.*

Reconstruction note: step57's family2a/2b run BOTH directions pooled in
one `run_backtest` call per config, so "best-of-family for LONGS" and "for
SHORTS" aren't directly readable from step57_results.md. This script
re-ran step57's exact grid (wick_mult∈{2,3} × context∈{roll20,roll55,
sma50,none} × stop_mult∈{1.0,1.5} × target_mult∈{2.0,3.0} for pin bars;
context × stop_mult × target_mult for engulfing — **1h only**, since every
other graveyard tool in this round trades 1h and the scenario classifier
is single-timeframe; step57's original grid also swept 4h, that half is
not carried into this round, stated as a scoping simplification) **scored
LONG-only and SHORT-only separately** (96 train-only scans) and picked the
single best (highest/least-bad train expectancy) of each side.

- **G1-LONG** = engulfing, ctx=roll55, stop=1.5×ATR (1.21%), tgt=3.0×stop
  (3.64%), hold 24h. Unconditional: train **+$17.30/t** n=191, val
  **−$41.72/t** n=77 (train looked positive, val collapsed — a textbook
  false-positive-on-train tool, exactly why it was buried).
- **G1-SHORT** = pin bar, wick=3×, ctx=roll20, stop=1.5×ATR (1.21%),
  tgt=2.0×stop (2.43%), hold 24h. Unconditional: train **−$3.21/t** n=408,
  val **−$20.60/t** n=144.

**G1-LONG cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 4 | $61.32 | — | — | UNRELIABLE |
| trending-up×normal | 41 | $6.17 | 31 | −$24.95 | FAIL-VAL |
| trending-up×violent | 3 | $192.00 | — | — | UNRELIABLE |
| trending-down×quiet | 13 | −$41.20 | — | — | UNRELIABLE |
| trending-down×normal | 31 | $32.23 | 15 | −$88.12 | FAIL-VAL |
| trending-down×violent | 9 | −$29.17 | — | — | UNRELIABLE |
| ranging×quiet | 45 | $8.08 | 4 | −$130.52 | INSUFFICIENT-VAL-SAMPLE |
| ranging×normal | 54 | $28.17 | 16 | −$12.57 | FAIL-VAL |
| ranging×violent | 5 | −$129.37 | — | — | UNRELIABLE |
| crowded-long×violent | 4 | $108.44 | — | — | UNRELIABLE |
| crowded-short×violent | 0 | $0.00 | — | — | UNRELIABLE |
| neutral-crowd×violent | 14 | −$31.16 | — | — | UNRELIABLE |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 17 | −$21.63 | — | — | FAIL-TRAIN |
| session=asia | 54 | $18.01 | 28 | −$42.76 | FAIL-VAL |
| session=london | 62 | $6.69 | 21 | −$72.87 | FAIL-VAL |
| session=newyork | 72 | −$9.62 | — | — | FAIL-TRAIN |
| **session=off-hours** | **23** | **$48.96** | **13** | **$32.42** | **REHABILITATED** |
| session=weekend | 45 | $27.82 | 15 | −$82.35 | FAIL-VAL |

**G1-LONG verdict (UPDATED by SESSION): REHABILITATED in session=off-hours**
(train $48.96/t n=23, val $32.42/t n=13 — both floors cleared). Every
other cell that cleared the train floor still failed val (the tool's core
train/val disconnect persists in 4 of 5 sessions and every TREND×VOL cell),
but the thin 21:00–24:00 UTC window is a genuine exception. Dumb-cell
control (hour-parity, n=134): train **+$13.58/t** (also positive — this
tool's baseline is already train-positive, so a same-sized random
subsample looks decent on train too) but val **−$25.04/t** (FAIL-VAL) —
same weaker-evidence pattern as G7's two rehabilitations below: the dumb
split's apparent edge didn't survive to val, the real off-hours cell did.
Flag this one with real caution — off-hours is also the thinnest-volume
session (only 8.9% of bars), and n=13 on val is not a lot of trades.

**G1-SHORT cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 16 | −$43.78 | — | — | FAIL-TRAIN |
| trending-up×normal | 87 | −$9.90 | — | — | FAIL-TRAIN |
| trending-up×violent | 19 | −$4.24 | — | — | FAIL-TRAIN |
| trending-down×quiet | 31 | $17.89 | 10 | −$8.12 | FAIL-VAL |
| trending-down×normal | 68 | −$14.88 | — | — | FAIL-TRAIN |
| trending-down×violent | 6 | −$70.01 | — | — | UNRELIABLE |
| ranging×quiet | 98 | −$9.08 | — | — | FAIL-TRAIN |
| ranging×normal | 103 | $3.52 | 37 | −$55.68 | FAIL-VAL |
| ranging×violent | 8 | $152.82 | — | — | UNRELIABLE |
| crowded-long×violent | 15 | $30.57 | 5 | $16.99 | INSUFFICIENT-VAL-SAMPLE |
| crowded-short×violent | 1 | $238.14 | — | — | UNRELIABLE |
| neutral-crowd×violent | 17 | −$2.37 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| **ALL-violent** | **33** | **$20.14** | **19** | **$3.62** | **REHABILITATED** |
| **session=asia** | **98** | **$10.53** | **34** | **$15.75** | **REHABILITATED** |
| session=london | 99 | −$10.94 | — | — | FAIL-TRAIN |
| session=newyork | 116 | −$19.77 | — | — | FAIL-TRAIN |
| session=off-hours | 66 | −$24.99 | — | — | FAIL-TRAIN |
| session=weekend | 149 | −$0.82 | — | — | FAIL-TRAIN |

**G1-SHORT verdict (SESSION adds a SECOND rehabilitation): REHABILITATED
in ALL-violent** (train $20.14/t n=33, val $3.62/t n=19) **AND in
session=asia** (train $10.53/t n=98, val $15.75/t n=34 — the largest
sample of any G1-SHORT rehabilitation, and the only session bucket that
clears train at all). Dumb-cell control (hour-parity, n=255, shared by
both claims): train −$4.53/t (FAIL-TRAIN, val never attempted) — a random
equal-ish-sized subsample does NOT look good for either claim, so both the
violent-regime and Asia-session signals appear real rather than sampling
illusions. Caveat: ALL-violent's val magnitude is thin ($3.62/t, n=19);
session=asia is the stronger of the two (larger n on both windows, bigger
val number).

---

### G2 — Order blocks, base 50%-touch
*Source: `step57_price_action.py`, `order_block_engine` (imported).
step57_results.md: order-block section, 64 configs, 0/64 survivors.*

Reconstruction: grepping `family1_order_blocks`'s base+touch=50pct rows in
step57_results.md, the best (least-bad) train expectancy among them is
**1h, X2×/1bar impulse, touch=50pct, target=3×stop, hold 48h**
(tr_exp=−$9.73 n=462 — reproduced HERE exactly, confirming the
reconstruction: this script's own rerun gives train **−$9.73/t n=462**,
val **−$21.25/t n=157**, byte-identical to step57_results.md's published
row). stop=0.55%, target=1.65% (train-median distance to the block's far
edge, capped at STOP_CAP_PCT=3.0%).

**Full cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 15 | −$6.13 | — | — | FAIL-TRAIN |
| trending-up×normal | 136 | −$19.12 | — | — | FAIL-TRAIN |
| trending-up×violent | 60 | −$16.78 | — | — | FAIL-TRAIN |
| trending-down×quiet | 22 | $5.74 | 3 | −$65.67 | INSUFFICIENT-VAL-SAMPLE |
| trending-down×normal | 101 | −$7.76 | — | — | FAIL-TRAIN |
| trending-down×violent | 41 | −$30.97 | — | — | FAIL-TRAIN |
| ranging×quiet | 39 | −$8.08 | — | — | FAIL-TRAIN |
| ranging×normal | 142 | −$10.89 | — | — | FAIL-TRAIN |
| ranging×violent | 40 | −$25.36 | — | — | FAIL-TRAIN |
| crowded-long×violent | 54 | −$19.38 | — | — | FAIL-TRAIN |
| crowded-short×violent | 16 | −$36.80 | — | — | FAIL-TRAIN |
| neutral-crowd×violent | 94 | −$18.71 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 131 | −$20.06 | — | — | FAIL-TRAIN |
| session=asia | 175 | −$12.23 | — | — | FAIL-TRAIN |
| session=london | 191 | −$19.57 | — | — | FAIL-TRAIN |
| session=newyork | 287 | −$14.46 | — | — | FAIL-TRAIN |
| session=off-hours | 100 | $9.22 | 39 | −$2.67 | FAIL-VAL |
| session=weekend | 149 | −$11.73 | — | — | FAIL-TRAIN |

**G2 verdict (unchanged by SESSION): stays buried everywhere**, in all 19
cells. Only two cells ever cleared train positive (trending-down×quiet,
which fell into INSUFFICIENT-VAL-SAMPLE at n=3; and session=off-hours,
which cleared the train floor at n=100 but failed val at −$2.67/t). No
scenario — across any of the 5 axes — rescues order blocks. No dumb-cell
control needed (nothing to defend).

---

### G3 — Regular (reversal) RSI divergence, k8 config
*Source: `step58_divergence_mtf.py`, `divergence_events`/
`family1_divergences` (imported). step58_results.md/raw.csv: REGULAR
(reversal) flavor was 1/96 survivors — NOT the hidden/continuation flavor
(that one is this repo's validated 4h edge).*

Reconstruction: among RSI14-k8-regular rows in step58_results_raw.csv, the
best train expectancy is **buf0.15%, tgt2×, hold48h, 1h** (tr_exp=−$15.80
n=260 — reproduced exactly here: train **−$15.80/t n=260**, val
**−$38.34/t n=89**, matching step58_results_raw.csv row-for-row). stop
computed via the entry-weighted train-median swing-distance (long/short
blended) = 1.97%, target = 2×stop = 3.93%.

**Full cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 7 | $136.75 | — | — | UNRELIABLE |
| trending-up×normal | 60 | −$34.80 | — | — | FAIL-TRAIN |
| trending-up×violent | 26 | −$34.90 | — | — | FAIL-TRAIN |
| trending-down×quiet | 11 | $91.58 | — | — | UNRELIABLE |
| trending-down×normal | 45 | −$2.34 | — | — | FAIL-TRAIN |
| trending-down×violent | 17 | −$34.34 | — | — | FAIL-TRAIN |
| ranging×quiet | 34 | −$45.04 | — | — | FAIL-TRAIN |
| ranging×normal | 71 | −$35.82 | — | — | FAIL-TRAIN |
| ranging×violent | 15 | −$46.07 | — | — | FAIL-TRAIN |
| crowded-long×violent | 16 | $18.28 | 6 | −$192.22 | INSUFFICIENT-VAL-SAMPLE |
| crowded-short×violent | 4 | −$61.49 | — | — | UNRELIABLE |
| neutral-crowd×violent | 40 | −$47.95 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 58 | −$35.00 | — | — | FAIL-TRAIN |
| session=asia | 96 | $6.27 | 30 | −$45.50 | FAIL-VAL |
| session=london | 67 | −$14.52 | — | — | FAIL-TRAIN |
| session=newyork | 68 | −$43.35 | — | — | FAIL-TRAIN |
| session=off-hours | 46 | −$40.14 | — | — | FAIL-TRAIN |
| session=weekend | 72 | −$24.01 | — | — | FAIL-TRAIN |

**G3 verdict (unchanged by SESSION): stays buried everywhere**, in all 19
cells. Deeply negative in nearly every cell (worse than the already-bad
unconditional baseline in most of them). A few thin cells (trending-up×
quiet, trending-down×quiet) show large positive train numbers, but are
UNRELIABLE at n<15 — never checked on val, never a claim; session=asia
cleared train (n=96) but failed val hard (−$45.50/t). Regular/reversal RSI
divergence does not work anywhere tried, across any axis, conditional or
not.

---

### G4 — EMA 20/50 cross long, 1h
*Source: fresh reconstruction (`ema_crossover`, `step55_gold_system.py`,
`fast=20, slow=50, allow_short=False`). No exact prior buried BTC row was
located — this is a fresh unconditional run establishing its own baseline,
per the round brief. Connection: this is also "the gold watch-list shape"
— step55_gold_system.py's EMA20/50 family and RESEARCH_LOG.md's Round 55
entry sent 1h EMA20/50 long on GOLD to a watch list after a thin sealed
fail; the BTC test here is the one that matters for this round.*

Shape: enter long when EMA20>EMA50 (flat otherwise, long-only, no short),
gated at ENTRY only (an open position rides the crossover, same
`vol_gated_ma`-style `entry_filter` contract). stop = min(1.2×train-median
ATR%, 1.7% hard cap) = 0.97%; target = 2.5×train-median ATR% = 2.02% (one
consistent choice from the mandate's stated 1.0–1.5×/2–3× ranges).
Unconditional: train **−$11.05/t** n=311, val **−$19.30/t** n=103 — buried
both windows, as expected for a tool that never had a prior citation.

**Full cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 35 | $9.55 | 14 | −$97.14 | FAIL-VAL |
| trending-up×normal | 103 | −$2.76 | — | — | FAIL-TRAIN |
| trending-up×violent | 39 | −$23.09 | — | — | FAIL-TRAIN |
| trending-down×quiet | 52 | −$42.54 | — | — | FAIL-TRAIN |
| trending-down×normal | 93 | −$22.67 | — | — | FAIL-TRAIN |
| trending-down×violent | 23 | −$28.17 | — | — | FAIL-TRAIN |
| **ranging×quiet** | **88** | **$1.88** | **11** | **$6.31** | **REHABILITATED** |
| ranging×normal | 117 | −$8.38 | — | — | FAIL-TRAIN |
| ranging×violent | 32 | $2.48 | 17 | −$36.72 | FAIL-VAL |
| crowded-long×violent | 34 | −$28.61 | — | — | FAIL-TRAIN |
| crowded-short×violent | 17 | $17.73 | 5 | −$47.17 | INSUFFICIENT-VAL-SAMPLE |
| neutral-crowd×violent | 70 | −$17.72 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 81 | −$15.51 | — | — | FAIL-TRAIN |
| session=asia | 239 | −$8.55 | — | — | FAIL-TRAIN |
| session=london | 239 | −$7.31 | — | — | FAIL-TRAIN |
| session=newyork | 245 | −$1.09 | — | — | FAIL-TRAIN |
| session=off-hours | 218 | $14.07 | 75 | −$8.27 | FAIL-VAL |
| session=weekend | 166 | −$12.31 | — | — | FAIL-TRAIN |

**G4 verdict (unchanged by SESSION): REHABILITATED only in ranging×quiet**
(train $1.88/t n=88, val $6.31/t n=11 — both floors cleared, but the
THINNEST rehabilitation of the twelve: train expectancy is barely above
zero and val n=11 clears the floor by only 3 trades). SESSION does NOT
rescue this tool anywhere — session=off-hours looked the most promising
(train $14.07/t n=218, a real sample) but failed val at −$8.27/t. Owner's
"folklore" that EMA crosses are session-dependent did NOT pan out for this
config. Dumb-cell control on the one real claim: hour-parity gate (n=306):
train −$9.63/t (FAIL-TRAIN) — a random subsample does not look good, so
the ranging+quiet signal is not pure sample-size noise, but the magnitude
here is genuinely marginal and should not be oversold.

---

### G5 — Momentum burst, sealed-failed X1.8 1h config
*Source: `step43_daytrade.py` `momentum_burst_entries`/`day_trade_signal`;
exact byte-for-byte reconstruction per `step43c_test_look.py`. Config:
1h, X≥1.8% impulse, CHAMP-gated, stop=min(1.0×train-median ATR%, 1.7%),
target=3×train-median ATR%, max_hold=24h.*

This config **SURVIVED train/val** (per step43_results.md) — reproduced
exactly here: train **+$7.20/t n=257**, val **+$8.74/t n=61** — but
**FAILED its one sealed look**: test **−$2.68/t x36**
(`RESEARCH_LOG.md`, Round 43). **That sealed failure is final and this
script does not re-touch or re-litigate it.** This is a scenario-conditional
RETEST of the family on train/val only — a legitimately different (smaller,
conditional) question, not an appeal of the sealed verdict.

The owner specifically flagged **violent + news-hot** cells as the
hypothesis to check. News-hot could not be tested this round (see Section
1's limitation). Every violent cell is shown below alongside the rest for
honesty.

**Full cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 1 | −$92.47 | — | — | UNRELIABLE |
| **trending-up×normal** | **49** | **$14.11** | **12** | **$16.78** | **REHABILITATED** |
| trending-up×violent | 45 | −$13.33 | — | — | FAIL-TRAIN |
| trending-down×quiet | 0 | $0.00 | — | — | UNRELIABLE |
| trending-down×normal | 41 | $29.69 | 5 | −$6.19 | INSUFFICIENT-VAL-SAMPLE |
| trending-down×violent | 47 | −$8.33 | — | — | FAIL-TRAIN |
| ranging×quiet | 2 | −$91.63 | — | — | UNRELIABLE |
| **ranging×normal** | **52** | **$21.60** | **8** | **$93.61** | **REHABILITATED** |
| ranging×violent | 33 | −$12.91 | — | — | FAIL-TRAIN |
| crowded-long×violent | 44 | −$11.96 | — | — | FAIL-TRAIN |
| crowded-short×violent | 15 | −$26.37 | — | — | FAIL-TRAIN |
| neutral-crowd×violent | 81 | −$3.20 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE (span unreachable this round) |
| **ALL-violent** | **120** | **−$14.93** | — | — | **FAIL-TRAIN** |
| **session=asia** | **76** | **$1.96** | **15** | **$17.23** | **REHABILITATED** |
| session=london | 64 | −$4.01 | — | — | FAIL-TRAIN |
| **session=newyork** | **122** | **$0.51** | **37** | **$3.74** | **REHABILITATED** |
| session=off-hours | 37 | $1.12 | 8 | −$89.03 | FAIL-VAL |
| session=weekend | 55 | −$30.26 | — | — | FAIL-TRAIN |

**G5 verdict (SESSION adds TWO more rehabilitations, four total for this
tool): the owner's specific "violent" hypothesis was WRONG** — every
violent cell (trending-up×violent, trending-down×violent, ranging×
violent, and the pooled ALL-violent) FAILS TRAIN outright; if anything,
momentum bursts get WORSE, not better, in violent regimes (they likely
chase exhaustion moves). **Four cells across two axes genuinely
rehabilitate**: trending-up×normal (train $14.11/t n=49, val $16.78/t
n=12), ranging×normal (train $21.60/t n=52, val **$93.61/t n=8** — val n=8
sits exactly at the floor and the dollar figure is large for that few
trades, flag as fragile), **session=asia** (train $1.96/t n=76, val
$17.23/t n=15 — train margin is thin but n is solid and val holds up
cleanly), and **session=newyork** (train $0.51/t n=122, val $3.74/t n=37 —
the largest sample of any G5 cell, train expectancy is barely positive but
n=122/37 is by far the most convincing sample size here). Owner's
"folklore" that momentum bursts are session-dependent is DIRECTLY
CONFIRMED by this pair — Asia and New York sessions both work, London and
weekend both fail outright, off-hours fails val. Dumb-cell control
(hour-parity, n=160, shared across all four claims): train −$6.50/t
(FAIL-TRAIN) — a random subsample of this size does not look good for any
of the four, supporting that "normal vol regime" and "Asia/NY session,
not London/weekend" both carry real signal for this tool, even though the
owner's specific volatility-axis guess was wrong.

---

### G6 — Session/VWAP fade
*Source: `step43_daytrade.py` `family4_vwap_fade`/`rolling_vwap`
(imported). Both configs (k=1.5×ATR, k=2.5×ATR) FAILED at train/val
already (no sealed look was ever spent) — reproduced exactly here: k=1.5
train −$7.94/t n=629, val −$4.61/t n=215; k=2.5 train −$14.91/t n=333, val
−$3.74/t n=115 — byte-identical to step43_results.md.*

The owner flagged **ranging+quiet** as the hypothesis to check for this
tool. All 19 cells (14 original + 5 SESSION) shown for both k values for
honesty.

**G6-k1.5 cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 19 | −$31.26 | — | — | FAIL-TRAIN |
| trending-up×normal | 146 | −$15.97 | — | — | FAIL-TRAIN |
| trending-up×violent | 46 | −$27.07 | — | — | FAIL-TRAIN |
| trending-down×quiet | 39 | $43.76 | 12 | −$22.03 | FAIL-VAL |
| trending-down×normal | 131 | −$11.90 | — | — | FAIL-TRAIN |
| trending-down×violent | 40 | −$1.13 | — | — | FAIL-TRAIN |
| **ranging×quiet (owner's hypothesis)** | 114 | −$16.32 | — | — | FAIL-TRAIN |
| ranging×normal | 173 | −$8.85 | — | — | FAIL-TRAIN |
| ranging×violent | 34 | −$28.39 | — | — | FAIL-TRAIN |
| crowded-long×violent | 46 | −$45.33 | — | — | FAIL-TRAIN |
| crowded-short×violent | 19 | −$72.29 | — | — | FAIL-TRAIN |
| neutral-crowd×violent | 82 | −$5.59 | — | — | FAIL-TRAIN |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 117 | −$16.90 | — | — | FAIL-TRAIN |
| session=asia | 296 | −$10.38 | — | — | FAIL-TRAIN |
| session=london | 281 | −$21.85 | — | — | FAIL-TRAIN |
| session=newyork | 358 | −$12.75 | — | — | FAIL-TRAIN |
| session=off-hours | 214 | −$18.19 | — | — | FAIL-TRAIN |
| session=weekend | 192 | $3.45 | 65 | −$15.29 | FAIL-VAL |

**G6-k1.5 verdict (unchanged by SESSION): stays buried everywhere**,
including the owner's own hypothesized cell (ranging×quiet: train
−$16.32/t) and every session bucket (weekend cleared train at n=192 but
failed val at −$15.29/t — its sister config k=2.5 rehabilitates in this
exact session, k=1.5 does not).

**G6-k2.5 cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 7 | $0.06 | — | — | UNRELIABLE |
| trending-up×normal | 71 | −$38.05 | — | — | FAIL-TRAIN |
| trending-up×violent | 27 | −$9.76 | — | — | FAIL-TRAIN |
| trending-down×quiet | 14 | $22.87 | — | — | UNRELIABLE |
| trending-down×normal | 63 | −$34.32 | — | — | FAIL-TRAIN |
| **trending-down×violent** | **19** | **$33.99** | **15** | **$47.23** | **REHABILITATED** |
| **ranging×quiet (owner's hypothesis)** | 56 | −$9.55 | — | — | FAIL-TRAIN |
| ranging×normal | 96 | −$25.17 | — | — | FAIL-TRAIN |
| ranging×violent | 22 | −$62.98 | — | — | FAIL-TRAIN |
| crowded-long×violent | 25 | −$58.64 | — | — | FAIL-TRAIN |
| crowded-short×violent | 12 | $19.05 | — | — | UNRELIABLE |
| neutral-crowd×violent | 40 | $0.30 | 31 | −$1.32 | FAIL-VAL |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| ALL-violent | 66 | −$13.25 | — | — | FAIL-TRAIN |
| session=asia | 129 | −$22.93 | — | — | FAIL-TRAIN |
| session=london | 138 | −$36.99 | — | — | FAIL-TRAIN |
| session=newyork | 170 | −$21.04 | — | — | FAIL-TRAIN |
| session=off-hours | 88 | −$27.90 | — | — | FAIL-TRAIN |
| **session=weekend** | **84** | **$11.40** | **27** | **$9.21** | **REHABILITATED** |

**G6-k2.5 verdict (SESSION adds a SECOND rehabilitation): the owner's
specific hypothesis (ranging+quiet) was WRONG for this config** (train
−$9.55/t, still negative). **Two different cells genuinely rehabilitate
instead: trending-down×violent** (train $33.99/t n=19, val $47.23/t n=15 —
a strong swing from the −$14.91/−$3.74 unconditional baseline) **and
session=weekend** (train $11.40/t n=84, val $9.21/t n=27 — the largest
sample of the two, weekend crypto trading with thinner liquidity giving
VWAP overextensions more room to actually mean-revert). Owner's "folklore"
that VWAP fades are session-dependent is CONFIRMED, just for weekend
rather than any weekday session. Trading logic check on
trending-down×violent: a fade-toward-VWAP entry that requires the
CHAMPION to already be flat/short (champ_al==0) fires more cleanly in
violent downtrends where overextensions actually mean-revert hard, versus
the choppy "ranging+quiet" case where VWAP itself barely moves and there's
nothing real to fade. Dumb-cell control (hour-parity, n=276, shared by
both claims): train −$17.62/t (FAIL-TRAIN) — a random subsample looks
nothing like either real cell, supporting both the trending-down×violent
and weekend signals as real, not illusory.

---

### G7 — Oscillator gates, ADX≥25 on donchian base, violent-cell hypothesis
*Source: `step58_divergence_mtf.py` `donchian_filtered`/
`family2_oscillator_overlays`/`adx` (imported). ADX≥20 partially survived
unconditionally; ADX≥25 (the actual graveyard tool here — "the tighter
filter that just cut samples") FAILED both donchian bases unconditionally
— reproduced exactly here: donchian10 train $31.06/t n=264, val −$17.59/t
n=99; donchian20 train $15.80/t n=228, val −$33.36/t n=82, byte-identical
to step58_results.md.*

The owner explicitly asked to restrict this retry to **VIOLENT-vol cells
only**. This script ran all 19 cells anyway (same "no cherry-picking on
train" discipline applied to every tool this round) and highlights the
violent cells specifically below, per the owner's instruction. No
stop_pct/target_pct — same as the original reconstruction, exit is the
donchian channel itself (signal-managed), execution="maker".

**G7-donchian10 cell table** (SESSION adds no new rehabilitation here —
every session bucket that cleared train failed val, listed for
completeness):

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 7 | −$100.10 | — | — | UNRELIABLE |
| trending-up×normal | 74 | −$10.39 | — | — | FAIL-TRAIN |
| **trending-up×violent (owner's hypothesis)** | 31 | $11.38 | 11 | −$88.98 | FAIL-VAL |
| trending-down×quiet | 10 | $217.36 | — | — | UNRELIABLE |
| trending-down×normal | 47 | $51.81 | 27 | −$86.89 | FAIL-VAL |
| **trending-down×violent (owner's hypothesis)** | 18 | −$112.34 | — | — | FAIL-TRAIN |
| ranging×quiet | 31 | $202.06 | 4 | $97.04 | INSUFFICIENT-VAL-SAMPLE |
| **ranging×normal** | **86** | **$41.96** | **26** | **$50.14** | **REHABILITATED** |
| **ranging×violent (owner's hypothesis)** | 17 | −$45.72 | — | — | FAIL-TRAIN |
| crowded-long×violent | 25 | −$37.98 | — | — | FAIL-TRAIN |
| crowded-short×violent | 9 | −$138.12 | — | — | UNRELIABLE |
| neutral-crowd×violent | 39 | $9.57 | 25 | −$65.06 | FAIL-VAL |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| **ALL-violent (owner's hypothesis)** | 63 | −$26.58 | — | — | FAIL-TRAIN |
| session=asia | 89 | $9.18 | 24 | −$32.49 | FAIL-VAL |
| session=london | 78 | −$0.82 | — | — | FAIL-TRAIN |
| session=newyork | 147 | $18.35 | 61 | −$27.76 | FAIL-VAL |
| session=off-hours | 58 | −$1.80 | — | — | FAIL-TRAIN |
| session=weekend | 77 | $15.96 | 24 | −$43.64 | FAIL-VAL |

**G7-donchian20 cell table:**

| cell | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| trending-up×quiet | 7 | −$199.62 | — | — | UNRELIABLE |
| trending-up×normal | 67 | −$33.89 | — | — | FAIL-TRAIN |
| **trending-up×violent** | 30 | −$51.36 | — | — | FAIL-TRAIN |
| trending-down×quiet | 10 | $124.79 | — | — | UNRELIABLE |
| trending-down×normal | 44 | $0.86 | 24 | −$89.54 | FAIL-VAL |
| **trending-down×violent** | 18 | −$116.17 | — | — | FAIL-TRAIN |
| ranging×quiet | 27 | $218.86 | 4 | $53.30 | INSUFFICIENT-VAL-SAMPLE |
| ranging×normal | 80 | −$2.29 | — | — | FAIL-TRAIN |
| **ranging×violent** | 16 | −$1.81 | — | — | FAIL-TRAIN |
| crowded-long×violent | 24 | −$101.73 | — | — | FAIL-TRAIN |
| crowded-short×violent | 9 | −$164.85 | — | — | UNRELIABLE |
| neutral-crowd×violent | 36 | $2.97 | 24 | −$102.07 | FAIL-VAL |
| news-hot(13mo-span) | 0 | $0.00 | — | — | UNRELIABLE |
| **ALL-violent** | 58 | −$41.67 | — | — | FAIL-TRAIN |
| session=asia | 82 | $70.51 | 22 | −$51.44 | FAIL-VAL |
| **session=london** | **75** | **$25.07** | **23** | **$125.77** | **REHABILITATED** |
| session=newyork | 134 | $26.69 | 55 | −$32.42 | FAIL-VAL |
| session=off-hours | 57 | −$50.84 | — | — | FAIL-TRAIN |
| session=weekend | 74 | $9.29 | 23 | −$18.43 | FAIL-VAL |

**G7 verdict (SESSION flips donchian20 from "stays buried" to
"rehabilitated"): the owner's specific hypothesis (violent) was WRONG for
BOTH donchian bases** — every single violent cell (trending-up×violent,
trending-down×violent, ranging×violent, ALL-violent) is FAIL-TRAIN or
FAIL-VAL for both donchian10 and donchian20; violent regimes make ADX≥25's
already-thin edge worse, not better. **donchian10 REHABILITATES in
ranging×normal** (train $41.96/t n=86, val $50.14/t n=26 — a solid
sample, clean positive on both windows); SESSION doesn't add anything for
donchian10 (every session bucket that cleared train failed val instead).
**donchian20 REHABILITATES in session=london** (train $25.07/t n=75, val
**$125.77/t n=23** — the single largest val expectancy of all twelve
rehabilitations this round; London-session breakouts on a 20-bar donchian
exit, filtered to real trend strength, is a genuinely strong result on a
real sample). Owner's "folklore" that EMA crosses/VWAP fades/momentum
bursts are session-dependent didn't explicitly name donchian breakouts,
but this is the strongest session-cut result found regardless.

Dumb-cell control for **donchian10/ranging×normal** (hour-parity, n=201):
train **+$45.04/t** (ALSO positive — because donchian10's unconditional
baseline was already train-positive at $31.06/t, so almost any subsample
looks decent on train) but val **−$29.09/t** (FAIL-VAL) — the dumb
subsample's apparent train edge did NOT survive to val, unlike the real
ranging×normal cell, which passed both. Dumb-cell control for
**donchian20/session=london** (hour-parity, n=178): train **+$22.79/t**
(ALSO positive, same pattern — donchian20's own baseline was train-
positive too) but val **−$41.30/t** (FAIL-VAL) — again, the dumb split's
train-looking edge collapsed on val while the real session=london cell
held up, and held up spectacularly ($125.77/t). Both G7 rehabilitations
share this same weaker-but-still-discriminating evidence pattern (the
dumb control isn't obviously worse on train, only on val) — a real but
less clean-cut signal than G1-SHORT/G4/G5/G6-k2.5's controls, which fail
the dumb split outright on train.

---

## 2.5. Marginal SESSION-only cuts — required first-class check, all 10 tool-variants

Per the owner's mandatory mid-round addition: for every tool, its
UNCONDITIONAL entry rule split ONLY by session (all other axes pooled/
ignored). These are the exact `session=*` rows already shown in each
tool's cell table above, consolidated here into one view since this was
explicitly requested as its own output. REHABILITATED cells are **bold**.

| Tool | asia | london | newyork | off-hours | weekend |
|---|---|---|---|---|---|
| G1-LONG | tr $18.01/t n=54, va −$42.76/t n=28 (FAIL-VAL) | tr $6.69/t n=62, va −$72.87/t n=21 (FAIL-VAL) | tr −$9.62/t n=72 (FAIL-TRAIN) | **tr $48.96/t n=23, va $32.42/t n=13 (REHAB)** | tr $27.82/t n=45, va −$82.35/t n=15 (FAIL-VAL) |
| G1-SHORT | **tr $10.53/t n=98, va $15.75/t n=34 (REHAB)** | tr −$10.94/t n=99 (FAIL-TRAIN) | tr −$19.77/t n=116 (FAIL-TRAIN) | tr −$24.99/t n=66 (FAIL-TRAIN) | tr −$0.82/t n=149 (FAIL-TRAIN) |
| G2 | tr −$12.23/t n=175 (FAIL-TRAIN) | tr −$19.57/t n=191 (FAIL-TRAIN) | tr −$14.46/t n=287 (FAIL-TRAIN) | tr $9.22/t n=100, va −$2.67/t n=39 (FAIL-VAL) | tr −$11.73/t n=149 (FAIL-TRAIN) |
| G3 | tr $6.27/t n=96, va −$45.50/t n=30 (FAIL-VAL) | tr −$14.52/t n=67 (FAIL-TRAIN) | tr −$43.35/t n=68 (FAIL-TRAIN) | tr −$40.14/t n=46 (FAIL-TRAIN) | tr −$24.01/t n=72 (FAIL-TRAIN) |
| G4 | tr −$8.55/t n=239 (FAIL-TRAIN) | tr −$7.31/t n=239 (FAIL-TRAIN) | tr −$1.09/t n=245 (FAIL-TRAIN) | tr $14.07/t n=218, va −$8.27/t n=75 (FAIL-VAL) | tr −$12.31/t n=166 (FAIL-TRAIN) |
| G5 | **tr $1.96/t n=76, va $17.23/t n=15 (REHAB)** | tr −$4.01/t n=64 (FAIL-TRAIN) | **tr $0.51/t n=122, va $3.74/t n=37 (REHAB)** | tr $1.12/t n=37, va −$89.03/t n=8 (FAIL-VAL) | tr −$30.26/t n=55 (FAIL-TRAIN) |
| G6-k1.5 | tr −$10.38/t n=296 (FAIL-TRAIN) | tr −$21.85/t n=281 (FAIL-TRAIN) | tr −$12.75/t n=358 (FAIL-TRAIN) | tr −$18.19/t n=214 (FAIL-TRAIN) | tr $3.45/t n=192, va −$15.29/t n=65 (FAIL-VAL) |
| G6-k2.5 | tr −$22.93/t n=129 (FAIL-TRAIN) | tr −$36.99/t n=138 (FAIL-TRAIN) | tr −$21.04/t n=170 (FAIL-TRAIN) | tr −$27.90/t n=88 (FAIL-TRAIN) | **tr $11.40/t n=84, va $9.21/t n=27 (REHAB)** |
| G7-donchian10 | tr $9.18/t n=89, va −$32.49/t n=24 (FAIL-VAL) | tr −$0.82/t n=78 (FAIL-TRAIN) | tr $18.35/t n=147, va −$27.76/t n=61 (FAIL-VAL) | tr −$1.80/t n=58 (FAIL-TRAIN) | tr $15.96/t n=77, va −$43.64/t n=24 (FAIL-VAL) |
| G7-donchian20 | tr $70.51/t n=82, va −$51.44/t n=22 (FAIL-VAL) | **tr $25.07/t n=75, va $125.77/t n=23 (REHAB)** | tr $26.69/t n=134, va −$32.42/t n=55 (FAIL-VAL) | tr −$50.84/t n=57 (FAIL-TRAIN) | tr $9.29/t n=74, va −$18.43/t n=23 (FAIL-VAL) |

**Pattern**: the owner's "folklore" (momentum bursts, VWAP fades, and EMA
crosses are session-dependent) is a **mixed but real** result — momentum
burst (G5) shows a genuine, clean Asia/New-York-vs-London/weekend split
(2 rehabilitations, the clearest session story of the round); VWAP fade
(G6-k2.5) rehabilitates specifically on weekends; but EMA cross (G4) shows
NO session rehabilitation at all — every session bucket either fails train
outright or fails val. The single strongest session result in the whole
round belongs to a tool the owner didn't name in the folklore at all:
G7-donchian20 in session=london ($125.77/t val).

---

## 3. REHABILITATED LIST

12 claims across 7 tool-variants (up from 6 claims / 5 tool-variants
before SESSION was added). All cells examined = 19 for every claim (the
full, fixed enumeration — every claim below was checked against the same
19-cell set, not a subset picked after the fact).

| Tool | Scenario | Train $/t (n) | Val $/t (n) | vs unconditional baseline | Axis |
|---|---|---|---|---|---|
| G1-LONG (engulfing ctx=roll55) | session=off-hours | +$48.96 (23) | +$32.42 (13) | baseline was train +$17.30/val −$41.72 | SESSION |
| G1-SHORT (pin bar wick3x ctx=roll20) | ALL-violent | +$20.14 (33) | +$3.62 (19) | baseline was train −$3.21/val −$20.60 | VOL |
| G1-SHORT (pin bar wick3x ctx=roll20) | session=asia | +$10.53 (98) | +$15.75 (34) | same baseline | SESSION |
| G4 (EMA20/50 long) | ranging×quiet | +$1.88 (88) | +$6.31 (11) | baseline was train −$11.05/val −$19.30 | TREND×VOL |
| G5 (momentum burst X1.8 champ) | trending-up×normal | +$14.11 (49) | +$16.78 (12) | baseline was train +$7.20/val +$8.74 (already positive; this cell improves it, but see G5's own sealed-test caveat) | TREND×VOL |
| G5 (momentum burst X1.8 champ) | ranging×normal | +$21.60 (52) | +$93.61 (8) | same baseline; val n=8 exactly at floor, flag as fragile | TREND×VOL |
| G5 (momentum burst X1.8 champ) | session=asia | +$1.96 (76) | +$17.23 (15) | same baseline; train margin thin but n is solid | SESSION |
| G5 (momentum burst X1.8 champ) | session=newyork | +$0.51 (122) | +$3.74 (37) | same baseline; largest sample (n=122/37) of any G5 cell | SESSION |
| G6-k2.5 (VWAP fade) | trending-down×violent | +$33.99 (19) | +$47.23 (15) | baseline was train −$14.91/val −$3.74 | TREND×VOL |
| G6-k2.5 (VWAP fade) | session=weekend | +$11.40 (84) | +$9.21 (27) | same baseline | SESSION |
| G7-donchian10 (ADX≥25) | ranging×normal | +$41.96 (86) | +$50.14 (26) | baseline was train +$31.06/val −$17.59 (unconditional train was already positive; val failed unconditionally, passes here) | TREND×VOL |
| G7-donchian20 (ADX≥25) | session=london | +$25.07 (75) | **+$125.77 (23)** | baseline was train +$15.80/val −$33.36; largest val expectancy of the round | SESSION |

**Notable pattern**: in most of these (G4, G5, G6-k2.5, G7-donchian10, and
G1-LONG/G7-donchian20's session wins), the scenario the owner explicitly
guessed at (violent/news-hot for G5/G7, ranging+quiet for G6) was WRONG —
the actual rescuing cell was a DIFFERENT one the data pointed to instead.
The one exception is the owner's mid-round "folklore" about SESSION:
momentum burst (G5, Asia+NY) and VWAP fade (G6-k2.5, weekend) both DID
turn out to be genuinely session-dependent, exactly as guessed in spirit
(the specific session wasn't named, but the hypothesis "session matters
for this tool" was right for 2 of the 3 named tools). EMA cross (G4) was
the one named tool where session added nothing. The owner was right that
scenarios exist; right more often than not that SOME axis category
(volatility, session) mattered for a given tool; wrong, more often than
not, about the exact cell within that category.

---

## 4. STAYS-BURIED LIST

Down to 3 tool-variants (from 5 before SESSION was added — G1-LONG and
G7-donchian20 both moved to the REHABILITATED list once SESSION was
folded in).

| Tool | Verdict |
|---|---|
| G2 (order blocks, base 50%-touch) | Buried in all 19 cells across all 5 axes — negative in 17/19, the other two (trending-down×quiet n=3; session=off-hours) never cleared val. |
| G3 (RSI14 k8 regular divergence) | Buried in all 19 cells across all 5 axes — deeply negative almost everywhere; a few thin train-positive cells (n<15) never reached val, session=asia cleared train but failed val hard. |
| G6-k1.5 (VWAP fade, tighter k) | Buried in all 19 cells across all 5 axes, including the owner's own ranging×quiet hypothesis and every session bucket (weekend cleared train but failed val — its sister config k=2.5 rehabilitates in that exact session, k=1.5 does not, isolating the effect to the wider ATR multiple). |

---

## 5. Controls

### 5a. Dumb-cell control (full detail)

For every REHABILITATED claim (12, after SESSION was added — up from 6),
the same tool with the same fixed stop/target/hold was gated by an
arbitrary, non-market-structural rule instead of a scenario cell: **bar
hour is even (hour % 2 == 0)** — a fixed, size-comparable, deliberately
dumb split. Note the dumb control is the SAME for every claim from the
same tool (it depends only on the tool's fixed entry rule, not on which
cell is being defended), so G5's four claims share one dumb result, as do
G1-SHORT's two and G6-k2.5's two.

| Tool / real cell | Real train $/t (n) | Real val $/t (n) | Dumb train $/t (n) | Dumb val $/t (n) | Dumb verdict |
|---|---|---|---|---|---|
| G1-LONG / session=off-hours | +$48.96 (23) | +$32.42 (13) | +$13.58 (134) | −$25.04 (45) | FAIL-VAL |
| G1-SHORT / ALL-violent | +$20.14 (33) | +$3.62 (19) | −$4.53 (255) | not attempted | FAIL-TRAIN |
| G1-SHORT / session=asia | +$10.53 (98) | +$15.75 (34) | −$4.53 (255) | not attempted | FAIL-TRAIN |
| G4 / ranging×quiet | +$1.88 (88) | +$6.31 (11) | −$9.63 (306) | not attempted | FAIL-TRAIN |
| G5 / trending-up×normal | +$14.11 (49) | +$16.78 (12) | −$6.50 (160) | not attempted | FAIL-TRAIN |
| G5 / ranging×normal | +$21.60 (52) | +$93.61 (8) | −$6.50 (160) | not attempted | FAIL-TRAIN |
| G5 / session=asia | +$1.96 (76) | +$17.23 (15) | −$6.50 (160) | not attempted | FAIL-TRAIN |
| G5 / session=newyork | +$0.51 (122) | +$3.74 (37) | −$6.50 (160) | not attempted | FAIL-TRAIN |
| G6-k2.5 / trending-down×violent | +$33.99 (19) | +$47.23 (15) | −$17.62 (276) | not attempted | FAIL-TRAIN |
| G6-k2.5 / session=weekend | +$11.40 (84) | +$9.21 (27) | −$17.62 (276) | not attempted | FAIL-TRAIN |
| G7-donchian10 / ranging×normal | +$41.96 (86) | +$50.14 (26) | **+$45.04 (201)** | **−$29.09 (84)** | FAIL-VAL |
| G7-donchian20 / session=london | +$25.07 (75) | +$125.77 (23) | **+$22.79 (178)** | **−$41.30 (70)** | FAIL-VAL |

**Verdict: 9 of 12 rehabilitations pass the dumb-cell control cleanly** —
a same-sized arbitrary subsample doesn't just fail to replicate the edge,
it outright loses money on train, so those nine don't look like a
sample-size illusion. **3 of 12 are weaker (G1-LONG/session=off-hours,
G7-donchian10/ranging×normal, G7-donchian20/session=london)**: in all
three cases the tool's own unconditional baseline was already close to or
above train-positive, so the dumb subsample ALSO looks decent on train —
it only reveals itself as noise once val is checked (all three dumb
controls FAIL-VAL, while the real scenario cells hold up on both windows,
in G7-donchian20's case spectacularly at $125.77/t). The discriminating
evidence for these three specific claims rests more heavily on val
holding where the dumb split didn't, rather than the dumb split failing
outright — a real but genuinely thinner form of evidence than the other
nine.

### 5b. Multiplicity note

**190 total scenario-cell evaluations** were run this round (up from 140
before the SESSION addition): 10 tool-variants (G1-LONG, G1-SHORT, G2, G3,
G4, G5, G6-k1.5, G6-k2.5, G7-donchian10, G7-donchian20) × 19 cells each (14
original + 5 SESSION, added mid-round). A separate 96 train-only scans
were spent up front on G1's exploratory best-of-family search (config
selection only — picking which single long/short config to carry forward
— not itself part of the scenario-cell multiplicity, since no val/
rehabilitation claim was ever made from that search).

At even a generous ~5% false-positive rate per independent train-then-val
look, several of 190 cells are expected to look train-positive by chance
alone — and indeed 106 of 190 were FAIL-TRAIN, 36 were UNRELIABLE (n<15,
never checked on val — this is the actual firewall: over a fifth of the
190 cells never got far enough to be a real claim because they didn't
clear 15 trades), 28 were FAIL-VAL (train looked good, val didn't —
exactly the multiplicity signature the val-confirmation requirement exists
to catch), 8 were INSUFFICIENT-VAL-SAMPLE (positive on both windows but
val n<8, logged, never claimed), and only **12 (6.3% of 190)** cleared
every bar: train positive AND n≥15, val positive AND n≥8. That 6.3%
survival rate — up from 4.3% (6/140) before SESSION was added, i.e.
SESSION's 5 extra cells per tool were NOT diluted noise, they pulled MORE
than their weight: 6 of the 50 new SESSION-cell evaluations rehabilitated
(12.0%), nearly triple the 4.3% base rate — after a firewall that already
threw out most of the noise (36 UNRELIABLE + 28 FAIL-VAL = 64 cells that
"looked"
promising on train alone but got filtered before or at the val stage), is
consistent with a mix of a handful of real, narrow effects and ordinary
multiplicity — which is exactly why the dumb-cell control in 5a is the
last line of defense, not the val requirement alone. The requirement of
BOTH train (n≥15) AND val (n≥8) positivity is what actually gates every
claim in Section 3; per-cell examination counts for each specific claim
are listed in that table (19 cells each, since every claim was drawn from
the same fixed 19-cell set run against every tool).

---

## 6. Was the owner right or wrong?

**Directionally right, mechanistically wrong more often than not — and
notably MORE right once SESSION was added.** Five of the seven graveyard
tools (G1, G4, G5, G6, G7 — all except order blocks and regular RSI
divergence) found at least one scenario cell — TREND×VOL or SESSION —
where the buried edge came back to life with both train and val holding
up: a real result in the owner's favor, and a genuine rebuke to "these
tools just don't work." 7 of the 10 tool-variants tracked rehabilitated
somewhere (G1-LONG, G1-SHORT, G4, G5, G6-k2.5, G7-donchian10,
G7-donchian20 — note G1 and G7 rehabilitate on BOTH of their sub-configs,
G6 only on its k=2.5 config, and G2/G3/G6-k1.5 never do). But when the
owner named a SPECIFIC scenario to check (violent/news-hot for G5,
ranging+quiet for G6, violent-only for G7), that specific guess was WRONG
in every one of those three original cases — the tool that did
rehabilitate found its life in a different cell than predicted. The
mid-round SESSION addition flipped that pattern partially: two of the
three tools named in the owner's SESSION "folklore" (momentum bursts, VWAP
fades) turned out to be genuinely session-dependent, exactly as guessed in
spirit, even though the specific session wasn't named up front.

- **G5 (momentum burst) works in calm trends, not violent ones — and
  specifically in the Asia and New York sessions, not London or
  weekend**: "buy the burst when the market is quietly trending"
  ($14–22/trade in trending-up×normal and ranging×normal, $2–4/trade but
  on much larger samples in session=asia/newyork), not "buy the burst
  when things are already crazy" (violent regimes made it actively worse,
  −$14.93/t pooled) and not in London or on weekends (both fail outright).
  The owner had the volatility axis backwards for this tool, but was
  RIGHT that session matters — this is the cleanest session story of the
  round, with four independent rehabilitating cells across two axes for
  the same underlying tool.
- **G6 (VWAP fade, k=2.5) works fading a violent downtrend AND on
  weekends, not a quiet weekday range**: a rejection-of-overextension
  trade needs something real to fade — a quiet range barely moves off
  VWAP at all, so "ranging+quiet" starved the tool of any edge to find
  (still −$9.55/t there). A violent downtrend gives it real distance to
  mean-revert against ($33.99→$47.23/trade), and so does the thinner
  weekend liquidity ($11.40→$9.21/trade, on a solid n=84/27 sample) — the
  owner's session folklore was right for this tool too, just not on the
  specific weekday sessions one might first guess.
- **G7 (ADX≥25 donchian breakout) works in calm, range-bound markets, not
  violent ones — and the 20-bar-exit variant works specifically during
  London hours, producing the single biggest number in the whole round**:
  "ranging×normal" (donchian10) is close to the opposite of "violent" — a
  strong trend-strength filter helps most when the broader regime ISN'T
  already trending hard (every violent cell failed both donchian bases
  outright). Separately, donchian20 — which rehabilitated NOWHERE on
  TREND/VOL/CROWD — comes alive specifically in the London session
  ($25.07/t train, **$125.77/t val** on a real n=75/23 sample). Neither of
  these was the owner's named hypothesis (violent-only); both are
  legitimate, data-found scenarios instead.
- **G1-SHORT (pin bar) rehabilitates in violent markets AND specifically
  in the Asia session** — "sharp rejection wicks mean more when the
  market is already moving hard" (violent, $20.14/train $3.62/val) is the
  one case that matched the owner's original intuition; session=asia adds
  a second, larger-sample confirmation ($10.53/train $15.75/val, n=98/34).
- **G1-LONG (engulfing), previously fully buried, is rescued ONLY by
  SESSION** — specifically the thin off-hours window (21:00–24:00 UTC,
  8.9% of all bars): $48.96/t train, $32.42/t val on n=23/13. This is the
  weakest-evidenced claim in the round (the dumb control also passes
  train, only failing on val) and the thinnest-volume session — flag with
  real caution rather than confidence.
- **G4 (EMA cross) is a genuine but marginal rehabilitation, and SESSION
  found nothing more for it**: quiet, range-bound markets ("ranging×
  quiet") are exactly where a slow trend filter should do the least
  damage — not because it catches trends there, but because it mostly
  stays flat and avoids the whipsaw that kills it everywhere else. Every
  session bucket either failed train outright or failed val; the owner's
  SESSION folklore, right for momentum bursts and VWAP fades, did NOT
  extend to this third named tool.
- **G2 and G3 stay buried everywhere, honestly, even after adding a 5th
  axis.** No scenario — trend, vol, crowd, session, or (unreachable) news
  — rescues order blocks or regular RSI divergence in this data. These
  are not "found the right scenario" cases; they are cases where the
  tool's underlying logic just doesn't hold up, and no amount of
  conditioning changes that. Reporting this plainly, no spin: two of the
  seven graveyard tools remain exactly where they were buried, across
  every axis tried.

The one honest asterisk on the whole exercise: **NEWS-HEAT, the axis the
owner may have been most curious about given the WatcherGuru feed's
novelty in this repo, could not be tested at all** — its harvested span
sits almost entirely inside this round's sealed test window, which this
script never touches by design. That question is still open; answering it
would need either a longer-harvested WatcherGuru history or a version of
this round's split that treats the WatcherGuru window as its own
train/val slice rather than reusing the BTC-history-wide 60/20/20 split.
SESSION, by contrast, was fully testable (pure calendar fact, no data-span
limitation) and turned out to be the single highest-yield axis added this
round: 6 rehabilitations from 50 new cell evaluations (12.0% hit rate,
nearly triple the round's overall 6.3%), including the round's single
strongest number (G7-donchian20/session=london, $125.77/t val).
