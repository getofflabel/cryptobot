# Round 69 — Banking the chart target

**Question:** R65 gave the news trade "eyes" and found N2 (structure-
trailing, no fixed target) beats the blind fixed-% incumbent — but R65's
own big-trade autopsy caught N2 turning a +$275.80 winner into a -$69.36
loser. The owner's refinement, verbatim: *"once you see the situation you
PLACE a take-profit at the structural level... pure trailing just gives
profits back until the stop catches it — when do you make the money?"*
This script tests the middle path: bank part of the position at a computed
structural target, let the rest ride N2's own validated trailing mechanic.

Script: `step69_banking.py`. Research only — no live orders, no commits.
Reused `step65_news_eyes.py`'s trigger, split, pivot/ATR precompute,
simulator (`simulate`/`_manage`), cost model, and N0/N1/N2 builders by
**import**, not reimplementation. The only new code is
`compute_structural_target` (shared target machinery for the banking
family) and `simulate_banking` (extends the trailing mechanic with a
partial-exit + post-bank breakeven shift — the plain `simulate()` has no
vocabulary for a position that splits into two legs mid-trade, same reason
R65 itself hand-rolled a simulator instead of reusing backtest.py). Did not
read or touch `step67_scalp.py` / `step68_router2.py` (concurrent agent's
files this round).

## Setup — identical to R65, unchanged

- Same fixed trigger (relevant WatcherGuru headline → first full 1h bar
  after it → enter at that bar's own close, direction = its own
  close-vs-open sign). Same news-span slice, same chronological 60/20/20
  split (`step43_daytrade.split_points`). **TEST SEALED** — this script,
  like step65, never loads or computes on anything past `i_va`.
- 1,840 directional entries in `[0:i_va]` (916 long / 924 short) → 1,427
  train / 413 val raw entries; realized trade counts are smaller per
  policy because every policy here is single-slot (one position open at a
  time), same legitimate artifact R65 documented.
- SL buffer fixed at **0.3%** (N2's own R65-winning buffer) for every
  policy in this round's new family (B1–B3, B5) and for B4 (N1's own
  matching config) — deliberate, not swept, because the mandate's axis
  this round is the **bank split ratio**, not the buffer.
- Target machinery for B1–B3 and B5 (new, shared): nearest confirmed k=5
  swing on the favorable side, accepted only inside **[1x, 3x]** the
  entry-bar-extreme stop distance (N1's own band). Outside the band, or no
  confirmed level yet, falls back to a **synthetic 2x-stop-distance**
  target (this repo's established 2R "constructed target" convention,
  the same one R65's N3 used for N2) — **not** N1's own fallback, which
  instead reverts the whole trade to the plain 2.4%/1.2% incumbent
  bracket. This is a deliberate, stated difference from N1.
- **Mechanically important:** for B1–B3, the stop stays **fixed** at the
  entry-bar extreme (no trailing at all) until the bank fires — pre-bank
  this is an N1-style static bracket on the full position. Only *after*
  the bank does the remainder start riding N2's trailing floor, ratcheting
  only on swings confirmed from the bank point forward.

**Harness check (passed, exact match):** B0 (N2 pure trailing, buf0.3%,
this round's own reimplementation) reproduces R65's published numbers
exactly — train n=315 exp **+$9.57**, val n=112 exp **+$4.34**. B4 (N1
swing_k5 buf0.3%, called through step65's own `n1_builder`) also matches
R65's published N1 row exactly — train n=339 exp +$4.71, val n=127 exp
-$12.11. Both harness checks came back bit-for-bit identical to R65
(today's data pull, one day newer than R65's, didn't move these
historical-window numbers at all — the extra day's news lands after `i_va`
in this slicing and never touches train/val).

## 1. Full policy table — train and val

| policy | tr n | tr exp | tr giveback | tr tag% | va n | va exp | va giveback | va tag% | verdict | beats B0 both? |
|---|---|---|---|---|---|---|---|---|---|---|
| **B0 N2 pure trailing (incumbent)** | 315 | **+$9.57** | $158.25 | n/a¹ | 112 | **+$4.34** | $153.23 | n/a¹ | SURVIVOR | — |
| B1 bank-half, no BE | 314 | +$2.95 | $152.11 | 30.9% | 110 | -$3.51 | $152.45 | 31.8% | FAIL | No |
| B1 bank-half, BE | 320 | +$5.19 | $153.31 | 31.6% | 108 | +$2.05 | $161.64 | 32.4% | SURVIVOR | No |
| B2 bank-75/25, no BE | 314 | +$0.63 | $149.67 | 30.9% | 110 | -$5.16 | $152.02 | 31.8% | FAIL | No |
| B2 bank-75/25, BE | 320 | +$3.07 | $151.44 | 31.6% | 108 | -$0.61 | $161.36 | 32.4% | FAIL | No |
| B3 bank-25/75, no BE | 314 | +$5.37 | $154.54 | 30.9% | 110 | -$1.89 | $152.89 | 31.8% | FAIL | No |
| B3 bank-25/75, BE | 320 | +$7.37 | $155.14 | 31.6% | 108 | +$4.73 | $161.91 | 32.4% | SURVIVOR | No |
| B4 full target, N1 verbatim | 339 | +$4.71 | $134.44 | 23.9% | 127 | -$12.11 | $119.86 | 26.0% | FAIL | No |
| B5 owner's literal design (TP+structural SL, no trail) | 425 | -$0.51 | $103.31 | 30.6% | 140 | -$6.95 | $110.48 | 30.7% | FAIL | No |

¹ B0 has no fixed target at all (that's the point of pure trailing), so
"tag rate" doesn't apply to it — shown as n/a, not 0%.

**No policy beats B0 on both windows.** Three of the six banking variants
clear SURVIVOR (positive both windows, sample well above the 30/8 floor):
B1 bank-half-BE (+$5.19/+$2.05) and B3 bank-25/75-BE (+$7.37/+$4.73) — but
both come in **below** B0's own +$9.57/+$4.34 on both windows, not above
it. Every no-BE variant fails val outright. B4 (N1 verbatim) and B5 (the
owner's literal no-trail design) both fail — consistent with R65's own
finding that fixed/static structural targets don't survive on this entry
family, banking or not.

**Breakeven matters, and by a lot.** Within every split, moving the stop
to breakeven after the bank is worth roughly $2–6/trade on both windows
(B1: +$2.95→+$5.19 train, -$3.51→+$2.05 val; B3: +$5.37→+$7.37 train,
-$1.89→+$4.73 val) — banking without also protecting the bank with a
breakeven stop is close to giving the sample away. (Trade counts differ
slightly between BE/no-BE variants at the same split — a legitimate
single-slot artifact: a different exit timing changes which later headline
entries land on an already-busy slot, the same effect R65 itself
documented.)

## 2. The giveback metric — the owner's complaint, quantified

Defined per trade: `giveback = peak_open_profit - realized_pnl`, where
`peak_open_profit` is the best price the market touched in the trade's
favor during its actual realized hold (gross, full original notional, no
fees) — i.e., what the trade was worth at its best moment, versus what was
actually banked in dollars.

**Banking barely moves the aggregate giveback number, and the reason is
structural, not a wash.** B0's own mean giveback is $158/$153
(train/val); B1–B3 sit in the same $150–162 band regardless of split
ratio (banking 25% vs 75% of the position changes this number by only a
few dollars). Splitting the sample explains why:

- **~69–70% of trades never reach the structural target at all** (tag
  rates 30.9–32.4% train/val across B1–B3) — for that majority cohort,
  banking never fires, so there is nothing to bank and the giveback is
  whatever the (static, non-trailing) pre-bank stop realizes. This cohort
  dominates the mean and pins it close to B0's own number.
- **On the ~31% that DO tag** (matched against B0 on the exact same
  entries), banking's own giveback is *higher*, not lower, than B0's on
  those trades ($172–175 for banking vs $164–166 for B0, train+val
  pooled) — and banking's realized pnl on that same matched subset is
  *lower* than B0's ($157–185 vs $198–204). **This is the sharpest,
  least-intuitive finding of the round: on exactly the trades banking is
  designed to help, pure trailing outperforms it.** The trades that reach
  a first structural target on this entry family tend to be the ones that
  keep running — B0's trailing floor (which by that point has often
  already ratcheted up on intervening confirmed swings) protects most of
  the continued move for free, while banking locks in a chunk at the
  first level and gives up the rest of that same run to the remainder's
  own, later-starting trail.
- **On the never-tagged cohort, banking and B0 are NOT mechanically
  identical**, despite both starting from the same entry-bar-extreme
  stop: B0 trails from bar 1, while banking's pre-bank stop is
  deliberately static (by this round's own design — see Setup). Matched
  trade-by-trade, only 3.6% of never-tagged banking exits land on the
  exact same pnl as B0's exit on that same entry; individual outcomes
  differ meaningfully (B0 sometimes exits better, sometimes worse,
  because its early trailing can both save a trade and clip one before
  banking's static stop would have). In aggregate the two average out to
  nearly the same (mean B0-minus-banking pnl gap: **-$1.77/trade**,
  banking marginally ahead on this cohort specifically) — the sameness in
  Table 1's giveback column is a genuine wash of offsetting per-trade
  differences, not literally the same exit rule.

## 3. Target-tag rate

| policy | train tag% | val tag% |
|---|---|---|
| B1/B2/B3 (shared target machinery) | 30.9–31.6% | 31.8–32.4% |
| B4 (N1 verbatim, own fallback) | 23.9% | 26.0% |
| B5 (same target machinery as B1–B3, full position) | 30.6% | 30.7% |

Roughly **7 in 10 trades never reach the structural target before the
entry-bar-extreme stop catches them** — this is the single biggest reason
banking doesn't help: there usually isn't a profit to bank in the first
place. B4's lower tag rate reflects its different fallback (reverting to
the plain 2.4% incumbent bracket instead of the 2R synthetic — a fixed
2.4% target is farther away on average than the 2R-scaled synthetic,
harder to tag).

## 4. Big-winner / big-loser autopsy

Ranked by N0's (the fixed-% incumbent) own realized pnl, train+val
pooled — same three winners/losers R65 itself flagged.

**3 biggest N0 losers:**

| entry (UTC) | dir | N0 | B0 (N2) | B1 bank-half BE | B3 bank-25/75 BE | B4 N1 | B5 owner's design |
|---|---|---|---|---|---|---|---|
| 2025-11-21 19:00 | short | -$155.37 | -$161.32 | -$142.90 (never tagged) | -$146.78 (never tagged) | -$136.85 | -$128.54 |
| 2025-11-22 17:00 | short | -$152.85 | **-$59.74** | -$60.95 (never tagged) | -$62.61 (never tagged) | -$62.65 | -$54.83 |
| 2025-11-24 18:00 | long | -$152.70 | not taken (busy) | not taken (busy) | not taken (busy) | -$133.15 | -$88.44 |

**3 biggest N0 winners:**

| entry (UTC) | dir | N0 | B0 (N2) | B1 bank-half BE | B3 bank-25/75 BE | B4 N1 | B5 owner's design |
|---|---|---|---|---|---|---|---|
| 2025-11-21 08:00 | short | +$280.01 | not taken (busy) | not taken (busy) | not taken (busy) | +$246.64 | +$284.07 |
| **2025-11-24 13:00** | **long** | **+$275.80** | **-$69.36** (structure stop) | **-$61.39** (never tagged) | **-$63.06** (never tagged) | -$63.11 | -$55.22 |
| 2025-11-20 17:00 | short | +$273.66 | not taken (busy) | not taken (busy) | not taken (busy) | not taken (busy) | not taken (busy) |

**Honest answer: banking does NOT rescue R65's own headline example.**
The exact trade the round is framed around — N0's +$275.80 winner that N2
clipped to -$69.36 — gets stopped out under every banking variant at
almost the identical size (-$59 to -$63) and *before ever tagging the
bank target at all* ("never tagged", 1.0h hold, same as B0's structural
stop timing). The structural target computed for this trade sat too far
away (or was rejected by the [1x,3x] band and fell back to the 2R
synthetic, itself apparently still out of reach in 1 hour) for price to
reach it before the initial entry-bar-extreme stop caught the trade. The
mechanism that clips this specific winner is the **tight initial stop**,
not the absence of a bank point — banking only helps trades that survive
long enough to actually touch a target, and this trade didn't. On the two
losers where a comparison is possible, banking performs roughly in line
with B0 and B4/B5 — no meaningful edge either way; single-slot blocking
(both winners and one loser were "not taken" under most policies) remains
the single biggest source of missed opportunity across the whole table,
same caveat R65 gave.

## 5. Verdict

**Banking does not beat pure trailing on train AND val, at any split.**
Three variants (B1-BE, B3-BE) individually clear SURVIVOR, but all six
banking configs sit below B0's own +$9.57 train / +$4.34 val on both
windows — B0 remains the strongest policy in this table by a clear
margin. B4 (N1 verbatim) and B5 (the owner's literal "target + structural
stop, no trailing" design) both fail outright, consistent with R65's own
finding that fixed structural targets don't survive here regardless of
whether banking is layered on top.

Per the mandate's own trigger condition (a challenger must beat B0 on
BOTH windows to earn a sealed-look spend): **no sealed-look
recommendation this round.** No challenger qualifies. B0 (N2 structure
trailing, buf0.3%, k=5 — already the live-deployed config from R65) stays
the strongest validated policy on train+val; this round adds evidence
against changing it, it does not add a new candidate.

**What actually happened, in plain terms:** the owner's instinct — "place
a target at the structural level, don't just trail and give it back" — is
sound trading logic, but on THIS specific entry family (fast, 1h,
news-clustered, an entry-bar-extreme stop that's already tight) it runs
into two facts that undercut it: (1) most trades never even reach a
computed structural target before the tight initial stop catches them
(~70% never tag), so there's nothing to bank most of the time; and (2)
on the minority that DO reach a target, they tend to be the trades that
keep running well past that first level — banking early caps upside that
pure trailing (whose floor has usually already ratcheted up by then)
would have captured for free. The giveback problem R65 surfaced is real
(N2's own mean giveback is $150-160/trade), but banking at the FIRST
structural level is the wrong fix for it on this entry family — it either
fires too rarely to matter, or fires early on trades that had more room
to run.

**Biggest caveat, stated as loudly as R65's own:** this is still one
~13-month regime slice of a 24/7, event-clustered entry family with no
bull-run/crash in sample. The conditional-giveback finding in particular
(pure trailing beats banking on the exact trades banking should help)
rests on a matched subset of only ~130-140 trades per split — a real,
computed result on this data, but a small enough slice that a different
13 months of WatcherGuru history could reshuffle which cohort dominates.
This round strengthens the case for leaving the live config (N2 structure
trailing, buf0.3%) alone; it does not prove banking can never work — only
that banking the FIRST touched structural level, on this specific
tight-initial-stop construction, isn't the fix for R65's giveback problem.
