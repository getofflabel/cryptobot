# Round 56 — The Trader's Toolkit: Smart-Money/ICT concept family (BTC)

Formalizing and gauntlet-testing the owner's own named toolkit, verbatim
spirit: *"you have to know liquidity identification, break of structure,
fair value gaps, equilibrium levels, fib retracement, context, bias, and
confluence — in different situations you use different weapons."* Every
concept is written as a pure, shift-disciplined function (see
`step56_smc_toolkit.py`'s module docstring for the exact definitions used —
summarized again below), gauntleted both as its own single-tool baseline
AND as an input to a confluence scorer — the owner's central claim under
test: does requiring multiple tools to agree beat any single tool alone,
or does it just cut the sample?

Script: `step56_smc_toolkit.py`. Full raw grid: `step56_results_raw.csv`
(274 rows). Research only — no commits, no live orders, no file touched
outside `step56_smc_toolkit.py` / `step56_results.md`.

Data: cached BTC 1h / 4h / 15m parquets (Bybit, no network calls needed),
real funding via `align_funding`, ~6 years, 2020-03-25 → 2026-07-22/23.
Gauntlet: chronological 60/20/20 per timeframe — train ends 2024-01-10,
val ends 2025-04-16, **test (final 20%) never touched, never sliced,
never computed** — that window is left entirely for the lead agent to
spend sealed looks against. Selection by TRAIN expectancy only.

---

## 1. Concept formalization — exact definitions used

| Concept | Definition (as coded) | No-lookahead argument |
|---|---|---|
| **Swings** | k-bar fractal high/low, confirmed k bars AFTER its own extreme (`confirmed_swings`, reused unmodified from step41) | value at bar t reflects an extreme at t-k |
| **Liquidity pool** | >=2 confirmed swing highs (or lows) within tol% {0.05%, 0.1%} of each other; pool level recomputed fresh each bar from the two MOST RECENT confirmed swing points — no separate "consumed" bookkeeping (stated simplification) | causal — only uses confirmed (already-shifted) swing prices |
| **Sweep** | wick pierces the pool by <= depth% {0.3%, 0.6%} but CLOSES back inside → fade the raid. Sweep of equal LOWS = LONG, equal HIGHS = SHORT | uses only the signal bar's own already-closed high/low/close |
| **BOS** | LSH/LSL = last confirmed swing high/low. Chain state (1 up / -1 down / 0 undetermined) updates on HH+HL → 1, LH+LL → -1, else persists. BOS-UP = close edge-crosses above LSH (fires once per breach) | LSH/LSL are causal ffills of already-confirmed swing prices |
| **BOS-continuation** | a BOS event in the SAME direction as the already-prevailing chain | — |
| **CHoCH** | the FIRST BOS event AGAINST the prevailing chain (or with none established) — the structural shift | — |
| **FVG** | 3-candle imbalance (bar1.high < bar3.low = bullish gap). Entry = first return into the gap to fill_frac depth {0.5, 1.0}, traded WITH the impulse (continuation, not fade). Only the nearest unfilled gap per direction tracked; expires after `expire_bars` untouched | gap only knowable once bar3 closes; entries fire strictly after formation |
| **Equilibrium / premium-discount** | active range = LSH↔LSL (same pair as BOS); eq = 50% midpoint. Filter, not standalone — gates longs to discount, shorts to premium | uses the same causal LSH/LSL |
| **Fib retracement** | the LAST BOS-CONFIRMED impulse leg (locked in at BOS confirmation — a stated simplification vs. a leg that keeps extending). Entry zone {0.618-0.705, 0.705-0.79} pullback WITH the leg; stop past 0.9 retrace; target {2x, 3x} stop OR the leg's 1.272 extension | leg only exists once its own BOS has fired |
| **Context/bias (4h)** | vol_gated_ma's sign (allow_short=True) AND the 4h BOS chain direction must AGREE, else neutral. Read onto 1h via the repo's existing close-of-bar availability convention (`champ_aligned`) | 4h bar's read only visible at its own close + 4h, merge_asof backward |
| **Confluence scorer** | for a candidate entry from a base tool (BOS-cont, CHoCH, FIB, FVG, or their union "ANY"), count how many of 5 conditions agree: bias-aligned, discount/premium-correct, inside a broad 0.618-0.79 fib zone, a same-direction pool sweep in the last 24h, a same-direction FVG currently unfilled. Test thresholds >=1/>=2/>=3 against threshold-0 (ungated) | — |

4h bias distribution (read onto 1h): **bullish 31.3% / bearish 25.8% /
neutral 42.9%** of bars — a genuinely selective read, not "on" most of the
time, which is what you want from a real bias filter.

One definitional discovery worth flagging up front: **the equilibrium
filter is logically degenerate when applied to BOS entries.** Equilibrium
and BOS both derive eq/LSH/LSL from the identical confirmed-swing pair, so
"close above LSH" (a BOS-up event) is *mathematically guaranteed* to also
be above eq — a BOS-continuation long can never be in "discount" by this
construction. Every `eqfilt=True` config in FAMILY 2 (BOS) produced **zero
qualifying train entries** and was dropped (32 of the planned 64 BOS
configs never printed a row — visible as the gap in the config count
below). The eq filter DOES work as intended on FAMILY 4 (fib), because a
fib pullback happens *inside* the range before the breakout — there it
produced real ablation rows (24 of them), it just didn't rescue fib (see
§3). Lesson for future rounds: equilibrium is a filter for pullback/
mean-reversion-shaped entries, not for breakout-shaped ones sharing the
same range definition.

---

## 2. Event-frequency table — how often does a clean event actually print?

Representative configs, counted over train+val only (~1,848.5 days /
5.06yr, sealed test excluded):

| concept | tf | events (train+val) | ~1 event every |
|---|---|---|---|
| sweep (k5, tol0.05%, depth0.3%) | 1h | 51 | 36.3 days |
| sweep (k5, tol0.05%, depth0.3%) | 4h | 4 | 462.1 days |
| sweep (k5, tol0.05%, depth0.3%) | 15m | 1,155 | 1.60 days |
| FVG (fill0.5, expire7d) | 1h | 4,905 | 0.38 days (~9h) |
| FVG (fill0.5, expire7d) | 4h | 1,145 | 1.61 days |
| FVG (fill0.5, expire7d) | 15m | 23,575 | 0.08 days (~2h) |
| BOS-continuation (k8) | 1h | 952 | 1.94 days |
| CHoCH (k8) | 1h | 1,025 | 1.80 days |
| BOS-continuation (k8) | 4h | 210 | 8.80 days |
| CHoCH (k8) | 4h | 268 | 6.90 days |
| fib (k5, zone 0.618-0.705) | 1h | 842 | 2.20 days |
| fib (k5, zone 0.618-0.705) | 4h | 190 | 9.73 days |

Two honest surprises: **FVG is NOT sparse** — it's the densest event of
the entire toolkit (a 3-candle imbalance is a common print, not a rare
one; ~1 every 2h on 15m, ~1 every 9h even on 1h). The mandate's hope that
"sweep/FVG events are sparse and may clear [the cost] floor" only holds
for sweep, and even sweep isn't THAT sparse at 1h/15m — only genuinely
rare at 4h (4-17 events across 5+ years, too thin to trust any number off
it, see §3).

---

## 3. Per-family autopsies

### FAMILY 1 — Liquidity sweep (fade the raid): 0 survivors, 4 insufficient-sample, 92 fail — DEAD as formalized

96 configs (tf {1h,4h,15m} x k {5,8} x tol {0.05%,0.1%} x depth {0.3%,0.6%}
x target {2x,3x} x hold {3d,7d}). **1h and 15m fail uniformly** — every
single config on both timeframes lost money in both train and val, no
exceptions, regardless of tolerance/depth/target/hold. 15m event counts
are moderate (700-2,410 train+val) so this isn't a sample-size problem —
the "stop-hunt then reclaim" shape simply doesn't carry a real edge on BTC
at these tolerances once real costs and funding are charged. **4h** is a
separate failure mode: the equal-highs/lows tolerance is so restrictive at
4h resolution that it only found 4-17 qualifying events across the entire
5+ year train+val window — a few configs show huge headline numbers
(+$64.63/trade train) purely because n=5, and those are correctly bucketed
INSUFFICIENT-SAMPLE, not survivors. Verdict: as pure equal-highs/lows
sweep-fade, this tool did not earn its keep in this round's formalization.

### FAMILY 2 — Break of structure (continuation + CHoCH): 2 survivors, 30 fail — a narrow, real parameter island

32 configs actually ran (of 64 planned — the other 32 were the degenerate
`eqfilt=True` cells explained in §1). Both survivors sit at the SAME exact
coordinates: **1h, k=8, target=3x stop, hold=5 days**:

| config | tf | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | med_hold_h |
|---|---|---|---|---|---|---|---|---|
| k8 cont eqfilt=False tgt3x hold5d | 1h | 189 | +$2.15 | 34.4% | 63 | +$7.69 | 47.6% | 70.5h |
| k8 choch eqfilt=False tgt3x hold5d | 1h | 198 | +$1.83 | 36.4% | 64 | +$40.65 | 42.2% | 67.5h |

Everything ONE dimension away fails: k=5 (same tf/target/hold) is
uniformly negative on train; target=2x fails; hold=15d fails. 4h BOS is
its own cautionary tale — several configs show wild train/val sign flips
(e.g. `k5 cont tgt3x hold5d 4h`: train **+$160.93/trade x135** but val
**-$105.86/trade x42** — a textbook overfitting/regime-break pattern, not
a real edge, correctly bucketed FAIL). Read plainly: BOS/CHoCH on 1h with
an 8-bar swing lookback and a patient 3x-stop target and a real multi-day
hold is a genuine, if narrow, structural edge; the same concept 4 hours
coarser is not stable enough to trust.

### FAMILY 3 — Fair value gap fill: 0 survivors, 0 near-misses — DEAD as formalized

24 configs (tf {1h,4h,15m} x fill_frac {0.5,1.0} x expire {7d,14d} x
target {2x,3x}). Every single row on every timeframe is net negative in
train, val, or both — no exceptions. The "buy the pullback into the
imbalance, ride the impulse" continuation shape does not carry an edge on
BTC at any of the tested fill depths, despite the concept printing
constantly (see §2 — this is the densest, most liquid signal in the whole
toolkit and it's still a loser after costs).

### FAMILY 4 — Fib retracement: 0 survivors, 0 near-misses — DEAD as formalized

48 configs (tf {1h,4h} x k {5,8} x zone {0.618-0.705, 0.705-0.79} x
eq_filter {off,on} x target {2xstop, 3xstop, ext1.272}). The eq filter
worked mechanically here (unlike family 2) but did not rescue anything —
best row (`k5 zone0.705-0.79 eqfilt=True tgt=ext1.272 4h`) shows train
+$7.90/trade but val **-$47.10/trade**, a clear train-only fluke, not a
survivor. Pulling back into the classic 0.618-0.79 "golden zone" of a
freshly-confirmed impulse leg, entered with the trend, does not carry a
standalone edge on BTC as formalized here.

### FAMILY 5 — Confluence scorer head-to-head: 3 survivors — the owner's central claim, tool-specific and non-universal

See §4 for the full head-to-head. Short version: confluence gating turned
two genuine losers into genuine winners (CHoCH k8, and BOS-cont k5), did
nothing for a third that never worked either way (FIB, FVG), and the
pooled "ANY tool" union — trade whichever tool fires, gated by total
agreement — **never survived at any threshold**, meaning stacking every
weapon together diluted the signal rather than concentrating it.

---

## 4. Confluence head-to-head — does agreement beat the single tool?

Full apples-to-apples comparison, same k / same target multiple, only the
`threshold` column changes (0 = ungated single-tool baseline):

**CHoCH, k=8, target=2x, 1h** — clean, MONOTONIC improvement:

| threshold | tr_n | tr_exp | tr_win% | va_n | va_exp | va_win% | verdict |
|---|---|---|---|---|---|---|---|
| 0 (ungated) | 115 | -$29.82 | 33.0% | 39 | -$77.04 | 28.2% | FAIL |
| >=1 | 107 | +$1.54 | 36.4% | 36 | +$7.64 | 36.1% | SURVIVOR |
| >=2 | 52 | +$15.45 | 40.4% | 24 | +$72.51 | 41.7% | SURVIVOR |
| >=3 | 3 | +$387 | 100% | 2 | +$84 | 50% | insufficient-sample |

Every additional agreeing condition moves both train AND val in the same
direction, in a large, clean way, right up until sample size collapses at
threshold 3. This is the single cleanest piece of evidence in the whole
round for the owner's thesis: more agreement really did mean a better
trade here, not just a smaller one.

**BOS-continuation, k=5, target=2x, 1h** — partial, NON-monotonic:

| threshold | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| 0 (ungated) | 120 | -$26.33 | 41 | -$7.18 | FAIL |
| >=1 | 114 | -$7.63 | 39 | -$81.52 | FAIL (val got WORSE) |
| >=2 | 61 | +$2.94 | 24 | +$19.53 | SURVIVOR |

Threshold 1 is a step BACKWARD on val before threshold 2 recovers —
confluence helped here too, but not smoothly, and the win is narrower
(smaller train edge, and the SAME tool at k=8 never survives at any
threshold — see below). Treat this one as real but fragile.

**BOS-continuation, k=8** — confluence does NOT rescue it at any threshold:

| threshold | tr_n | tr_exp | va_n | va_exp | verdict |
|---|---|---|---|---|---|
| 0 | 112 | -$15.99 | 38 | +$2.76 | FAIL |
| >=1 | 106 | +$55.78 | 38 | -$56.04 | FAIL |
| >=2 | 58 | +$43.47 | 24 | -$174.40 | FAIL |

Train looks tempting at >=1/>=2 but val gets catastrophically worse each
step — the opposite of the CHoCH story, and a reminder that "more
confluence" is not a universal law even within the SAME base tool, just a
different k.

**FIB and FVG as base tools** — confluence never turns them positive at
any threshold, on either k, on any target multiple (all 2x8x2=32 FIB rows
and all 2x8x2=32 FVG rows in the confluence family are FAIL). A dead tool
stays dead when you gate it harder; confluence is not a repair mechanism.

**ANY (pooled union of all four structural tools)** — every single
threshold x k x target cell FAILS, train AND val, with the deepest losses
of the whole family5 table at low thresholds (train as low as -$19.4/trade
at k8/thresh1). Trading "whatever fires, as long as enough things agree"
is worse than trading the ONE tool that actually works with ITS OWN right
threshold. This directly answers the owner's "different situations,
different weapons" framing: the data agrees with the "different weapons"
half (BOS-cont-k5 and CHoCH-k8 each need their OWN specific gate) and
rejects the "throw them all in one bucket" reading.

**Bottom line on the central claim: PARTIALLY CONFIRMED, tool- and
k-specific.** Confluence is not a universal amplifier. It is a genuine,
large, monotonic edge-creator for CHoCH-k8, a real but noisier edge-
creator for BOS-cont-k5, useless for BOS-cont-k8/FIB/FVG, and actively
harmful when tools are pooled instead of used individually.

---

## 5. 15m cost-floor analysis (sweep + FVG only, per mandate)

Realized cost (fees + friction + funding, pooled train+val, ~repo
convention since round 43/50) vs. gross edge (net expectancy + realized
cost added back), in bps of starting notional. Best 10 by gross edge:

| family | config | realized cost (bps) | gross edge (bps) | net tr_exp |
|---|---|---|---|---|
| 3-fvg | fill1.0 expire14d tgt3x | 8.74 | **3.37** | -$6.70 |
| 3-fvg | fill0.5 expire7d tgt3x | 8.67 | 2.58 | -$6.36 |
| 3-fvg | fill1.0 expire14d tgt2x | 8.20 | 1.94 | -$7.62 |
| 1-sweep | k8 tol0.10% depth0.3% tgt3x hold7d | 9.11 | 1.92 | -$4.29 |
| 1-sweep | k8 tol0.10% depth0.6% tgt2x hold7d | 8.49 | 0.89 | -$6.10 |
| 1-sweep | k8 tol0.10% depth0.3% tgt2x hold7d | 8.43 | 0.72 | -$6.37 |
| 1-sweep | k5 tol0.10% depth0.3% tgt3x hold3d | 8.42 | 0.70 | -$8.10 |
| 3-fvg | fill1.0 expire7d tgt2x | 8.09 | 0.62 | -$7.92 |
| 3-fvg | fill0.5 expire14d tgt3x | 8.85 | 0.55 | -$10.66 |
| 1-sweep | k5 tol0.05% depth0.3% tgt3x hold3d | 8.55 | 0.35 | -$6.84 |

Realized cost sits at a steady **~8.1-9.1bps per round trip** across every
15m config — consistent with the repo's established ~9.2bps 15m floor
(round 43/50). The BEST case anywhere in this table (FVG fill1.0/expire14d/
tgt3x) shows a gross edge of only +3.37bps against an 8.74bps cost — **the
gross edge never once clears the cost floor**, so net expectancy is
negative everywhere, honestly. Every remaining 15m config (not shown) is
worse than this top-10. The mandate's speculation that sweep/FVG's
sparsity might let them clear the floor did NOT pan out: FVG turned out to
be the densest signal in the toolkit (not sparse at all, see §2) and
sweep, while genuinely sparser, still shows a near-zero-to-negative gross
edge before costs even enter the picture — this isn't a costs problem, the
underlying signal itself is close to noise at 15m resolution.

---

## 6. Full config table

274 configs total (96 sweep + 32 BOS + 24 FVG + 48 fib + 74 confluence —
short of the ~300-400 target range because `stop_pct is None` /
`n_events==0` guards correctly dropped data-starved cells rather than
faking a stop distance off zero qualifying entries; see §1 note on the
degenerate eqfilt=True BOS cells for the largest chunk of the gap).
Verdict counts:

| verdict | count |
|---|---|
| FAIL | 259 |
| INSUFFICIENT-SAMPLE | 10 |
| SURVIVOR | 5 |

Full grid: `step56_results_raw.csv`. All 5 survivors, all 10
insufficient-sample rows, and the full confluence/cost-floor tables are
reproduced in §3-§5 above; nothing else in the 274-row grid needs a second
look.

---

## 7. Ranked sealed-look candidates (for the lead to spend)

1. **`5-confluence k8 CHoCH thresh>=2 tgt2x`, 1h.** Train 52t +$15.45/t
   (40.4% win), val 24t **+$72.51/t** (41.7% win). Strongest candidate in
   the round: clean monotonic confluence story (threshold 0→1→2 all move
   the same direction, see §4), both windows comfortably clear the trade
   floor. Caveat: val/train ratio is large (~4.7x) — flag as possibly a
   favorable val-window regime, not proof the $72 number repeats, but the
   SIGN and the monotonic mechanism behind it are the real finding.
2. **`5-confluence k8 CHoCH thresh>=1 tgt2x`, 1h.** Train 107t +$1.54/t,
   val 36t +$7.64/t. Same tool/k/target as #1, weaker gate, more sample —
   supporting evidence for the same discovery rather than an independent
   bet; a look here is redundant with #1 unless the lead wants the larger-
   n, smaller-edge version specifically.
3. **`2-bos k8 choch eqfilt=False tgt3x hold5d`, 1h.** Train 198t
   +$1.83/t, val 64t +$40.65/t. The UNGATED baseline for the same
   underlying tool (CHoCH, k=8, 1h) at a different target/hold. That this
   ALSO survives independently is convergent evidence CHoCH-k8-1h is a
   real, if modest, structural edge — not an artifact of the confluence
   filter's specific threshold.
4. **`2-bos k8 cont eqfilt=False tgt3x hold5d`, 1h.** Train 189t +$2.15/t,
   val 63t +$7.69/t. BOS-continuation's own ungated 1h/k8 baseline —
   smaller edge than CHoCH's version but the same parameter island,
   worth a look as the trend-following sibling of #3.
5. **`5-confluence k5 BOS-cont thresh>=2 tgt2x`, 1h.** Train 61t +$2.94/t,
   val 24t +$19.53/t. Weakest of the five: non-monotonic across
   thresholds (threshold 1 was WORSE than ungated before threshold 2
   recovered) and the SAME tool at k=8 fails badly at every threshold
   (§4). Real numbers, positive both windows, clears the trade floor —
   but the most fragile story here. Lowest priority; consider deferring
   until/unless one of the above confirms.

---

## 8. Which of the owner's tools earned a live slot?

| tool | standalone | as confluence input | verdict |
|---|---|---|---|
| Liquidity sweep | 0/96 survive | n/a (not used as a base tool in family5, only as a confluence check) | did not earn a slot as formalized |
| BOS-continuation | 2/32 survive (k8, 1h) | rescues k5 (1 survivor); does NOT rescue k8 | earned a narrow slot — 1h/k8 ungated, or 1h/k5 confluence-gated thresh>=2 |
| CHoCH | (same 32-config family as BOS above) 1 survivor (k8, 1h) | **rescues k8 cleanly and monotonically** — the round's best result | earned the strongest slot of the round: 1h/k8, gated or ungated |
| FVG | 0/24 survive | 0/32 confluence cells survive | did not earn a slot — dead, despite being the most common event in the whole toolkit |
| Fib retracement | 0/48 survive | 0/32 confluence cells survive | did not earn a slot |
| Equilibrium/premium-discount | filter only, no independent verdict | one design flaw found (degenerate on BOS, see §1); worked as intended on fib but didn't rescue it | not independently tradeable, and needs a different range definition than BOS's own LSH/LSL if reused on breakout entries |
| Context/bias (4h) | filter only | one of the 5 confluence ingredients behind the CHoCH-k8 win | contributed to the round's best result, not tested standalone |
| Confluence (>=2 agreeing) | n/a | **beat the single tool for CHoCH-k8 and BOS-cont-k5; did not for BOS-cont-k8/FIB/FVG; pooling ALL tools (ANY) never worked** | tool-specific amplifier, not a universal law — validated for exactly the two configs above |
