# step192 — always-on shorts, dead-family confirmation on SOL

Run: `python3 step192_shorts_confirmation_sol.py` (0.7s, cached data).
Shape imported unchanged from `step48_tradfi_trend.trend_short_signal`
(mirror the champion trend logic, short side only). Grid: (fast,slow) in
{(20,100),(50,200)} x gate_mode in {ungated, fixed1.0, fixed1.5, adaptive},
both 1h and 4h SOL — 16 cells. Execution: taker, always. No stop/target
(pure signal-managed, matching the source shape). 60/20/20, sealed test
never touched.

## Result: CONFIRMED DEAD on SOL too, after the thickness gate

0 of 16 cells clear this desk's full bar (both windows positive, >=30
train / >=8 val trades, AND >=5x round-trip cost). 12 of 16 cells fail
outright (train or val negative — most 4h cells lose badly, worst
-$299.46/t). **2 cells (1h 50/200 fixed1.5 and 1h 50/200 adaptive) clear
the trade-count and both-windows-positive bar but were REJECTED on
thickness** — 4.4x and 2.2x round-trip cost respectively, both under the
5x floor. This is the exact case the thickness bar exists for: a
config that "looks like a survivor" by trade-count and sign alone but
doesn't clear real costs by a comfortable margin. Full table in
`step192_table.csv`.

**Verdict for the desk: mirrored always-on shorts remain dead on SOL,
consistent with BTC's 5x-confirmed finding** — the strongest SOL cell
(4.4x) came closer to clearing than any single BTC cell reportedly did,
worth a one-line footnote (SOL's shorts are LESS uniformly bad than BTC's,
not good), but not close enough to reopen the family.

## Files
- `/Users/wallacechen/cryptobot/step192_shorts_confirmation_sol.py`
- `/Users/wallacechen/cryptobot/step192_results.md` (this file)
- `/Users/wallacechen/cryptobot/step192_table.csv`
