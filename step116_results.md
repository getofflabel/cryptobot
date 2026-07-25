# Round 116 — Exit Variation on the Donchian(55) Near-Miss

**Result: a real train+val PASS on BZ=F (thickness 15.87x, beats chance)
— but it does NOT transfer unchanged to CL=F/WTI, which is the actual
live venue. Flagged as a promising lead, NOT a validated edge.**

## Method

Same Donchian(55) breakout entry (unchanged) that produced the family
map's one near-miss (families 5-1d-55 / 14), screened against 9
stop/target pairings from `exits.py`'s composable library (trail-only,
chandelier at 2 multiples, chandelier+fixed-R, ATR+fixed-R, Bollinger,
structure-trail+fixed-R, structure-trail+measured-move). **Selection is
TRAIN-only** — best-by-train-expectancy among configs clearing the
30-trade train floor and positive — **VAL is read exactly once** for
that one selected config, never grid-searched. Sealed 20% never touched.

## CL=F: no improvement

Best train config (`chandelier2.5_r3`, i.e. chandelier(2.5x ATR) stop +
3R target) trains at $+56.66/t (n=105) but reads $+37.12/t on val (n=35),
thickness **3.92x** — still under the 5x bar, and the real result sits
BELOW its own chance baseline ($47.99/t). No CL config in this grid
clears the house standard.

## BZ=F: a real pass, with two caveats

Best train config on Brent is `chandelier3.5_trail` (chandelier(3.5x
ATR), trail-only, no fixed target): trains at **$+160.34/t** (n=47),
reads **$+101.13/t** on val (n=17) — both floors cleared, both windows
positive, thickness **15.87x** (well above the 5x bar), and it beats the
chance baseline ($87.88/t random-entry mean).

**Caveat 1 — multiple comparisons.** This is the best of 9 TRAIN-screened
candidates on Brent specifically. Selecting-the-best-of-9 on train and
then reading val once is the correct discipline (not val-tuned), but a
9-way screen still carries real look-elsewhere risk. This is why the
verdict is "train+val PASS, sealed look NOT spent" and not "validated" —
spending the sealed test is Morgan's call.

**Caveat 2 — does NOT transfer to WTI, and WTI is what's actually live.**
The exact same unchanged config (chandelier(3.5x) trail, Donchian(55))
replayed on CL=F is already NEGATIVE on CL's own TRAIN window
(-$14.65/trade, n=74 — visible directly in this round's own CL grid, no
extra script needed to see it fail). The live/paper venue this desk
actually trades is WTI (CL=F research proxy, WTIOIL-USDT on BloFin) —
not Brent. So this is a real, well-evidenced BRENT-specific result, not
(yet) a WTI-tradeable one. Whether a WTI-specific exit variant exists
that clears the same bar is an open question for a follow-up round, not
answered here.

## Bottom line for Morgan

Not a green light to trade anything yet. It IS the strongest single
number this entire family map has produced (15.87x thickness beating a
9-way train screen and a chance baseline), and it's worth knowing about
even though it's Brent, not the live WTI venue. Two honest paths forward:
(1) run the same 9-config exit screen against WTI specifically (rather
than assuming a Brent winner should also win on WTI) to see if a
WTI-side equivalent exists, or (2) if Brent itself becomes tradeable on
this desk at some point, this is a concrete, disciplined candidate for
a sealed look. Neither is done here — this round's job was to find and
honestly caveat the lead, not to spend the look.

Full config grid for both instruments: `step116_table.csv`.
