# Round 114 — EIA-Continuation Costed Strategy (train+val only)

**Result: FAIL. And it resolves round 78's flagged conflict rather than
deepening it.**

Built the actual strategy version of step111's "EIA release-hour reaction
persists (continuation), not fades" diagnostic: trade in the direction of
the release-hour bar's own move, real structural stop
(`exits.stop_structure`), 2R target, 4h max hold, taker cost, train+val
only (100 EIA events in the train+val window; sealed test never touched
— round 78 already spent 2 sealed looks on EIA topics, so a third wasn't
appropriate here regardless of the train/val outcome).

- TRAIN: n=75, **-$95.02/trade** (50.7% win)
- VAL: n=25, **-$43.76/trade** (40.0% win), thickness **-1.18x** cost
- Chance baseline (100 random-entry draws, same apparatus): val real
  result (-$43.76) sits ABOVE the random mean (-$56.44) — i.e. it beats
  chance, but chance itself is also negative here (the exit geometry/cost
  structure alone loses money on this instrument at 4h holds — a useful
  side-finding about the geometry, not about EIA specifically).

**Reconciliation with round 78:** round 78's sealed-tested "EIA reversal"
config also FAILED (CL -$4.99/t, BZ -$4.16/t). This round's "EIA
continuation" config also FAILS (-$43.76/t val). Two opposite-direction
strategies built around the same event both losing money is not a
contradiction — it means the raw directional tendency step111 measured
in price is real but too small, relative to the stop/cost/slippage
structure a tradeable strategy has to carry, to survive as an actual
edge either way. **The conflict is resolved: EIA release-hour reaction is
real as a price phenomenon (step111) but does not clear the bar as a
tradeable strategy in either direction (round 78's reversal, this round's
continuation).**

Also logged to the family map: two explicit **NOT TESTED / NOT TESTABLE**
entries per the round's own honesty standard —
- OPEC meeting reactions: no reliable local meeting-date calendar exists
  in this repo; fabricating dates from memory was rejected as a real
  risk of a wrong calendar posing as a real one.
- Contango/backwardation: only a single front-month CL=F/BZ=F series is
  cached; no second contract month or curve data exists to compute an
  honest term-structure signal.

Full trade table: `step114_table.csv`.
