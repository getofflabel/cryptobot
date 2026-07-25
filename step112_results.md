# Round 112 — Oil Family Sweep 1: Ported Crypto/Gold/SPX Shapes

Full detail per family is logged in `step110_family_map.md` (the running
family map Morgan reads). Summary here.

**Engine:** `step150_common.run_edge` (Morgan's own taker+structure-stop
harness, built the same night for the BTC re-test) — reused unchanged.
Every entry pays taker costs; every stop is a real per-trade level from
`exits.py` (structure, ATR, or chandelier — never a swept percentage);
chance baseline is a same-apparatus random-entry draw; thickness is
reported both as %notional and as a multiple of round-trip cost, with
the house 5x-reject line applied by hand where the harness's own
SURVIVOR label didn't check for it (see the correction note in the
family map — `step150_common.verdict_for` checks sign+floor only, not
thickness).

**Result: 0 survivors in this batch, 2 REJECTs worth a follow-up
(thin-but-real edge), 4 INSUFFICIENT SAMPLE, 3 clean FAILs.**

| # | Family | TF | Verdict | Val | Thickness |
|---|---|---|---|---|---|
| 1 | CHoCH k8 + confluence>=2 | 1h/4h | INSUFFICIENT SAMPLE | n=2 | n/a |
| 2 | 4h hidden RSI(14) divergence | 4h | INSUFFICIENT SAMPLE | n=2 | n/a |
| 3 | 4h vol-gated trend (chandelier exit) | 4h | INSUFFICIENT SAMPLE | n=6 | n/a |
| 4 | 1h RSI3 washout dip-buy (pure ATR stop) | 1h | INSUFFICIENT SAMPLE | n=1 | n/a |
| 5 | Donchian(20) + structure-trail | 1d | REJECT (thin) | n=30, +$6.04/t | 1.64x |
| 5 | Donchian(55) + structure-trail | 1d | REJECT (thin) | n=20, +$7.35/t | 2.36x |
| 5 | Donchian(20) + structure-trail | 1h | FAIL | n=72, -$45.65/t | -2.65x |
| 6 | RSI2<5 dip-buy above SMA200 | 1d | FAIL | n=19, -$120.78/t | -6.45x |

**Read on this batch:** the ported crypto shock/divergence-style entries
(CHoCH, hidden divergence, RSI3 washout) simply don't fire often enough
on oil's ~2.4y of 1h/4h history under a calm-regime-comparable gate —
that scarcity is itself informative: whatever produces BTC's trigger
density does not carry over to oil's own volatility clustering. The one
real, sample-adequate, both-windows-positive result is the DAILY
Donchian breakout + gold_book.py's live structure-trailing exit (both
20 and 55-bar lookbacks) — consistent with round 78's original finding
("directionally real on oil DAILY... fires 3.4/yr") — but at 1.64x-2.36x
the round-trip cost, it sits under the house 5x-reject line. It is the
best lead this batch produced and is queued for an exit-variation round
(different stop/target pairing from `exits.py`'s composable library) to
see whether a wider-target or different-stop combination clears 5x
before it's written off.

The 1h version of the same Donchian shape (round 78 also flagged this)
is confirmed dead again here, and the SPX RSI2 shape is confirmed dead a
second time (round 78's original + this round's structural-stop
re-confirmation both FAIL).

Full trade-level output: `step112_table.csv`.
