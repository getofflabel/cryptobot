# step99_exit_library.md — ROUND 99 PART 1: THE EXIT LIBRARY

Written 2026-07-25. Wallace's mandate: research every way to take a stop
loss and a take profit, build a library thorough enough to test all of
them "until you find every single way that for every single different
scenario it works in", and do it right rather than fast. His correction,
which governs every method below:

> "The stop loss is not supposed to be placed depending on thirty percent
> or fifty percent. It's supposed to be stopped based on the CHART.
> There's targets on the chart such as a higher high or higher low, where
> you're like, okay, if it crosses this line it's probably gonna continue
> going down. That's where you cut the trade."

**This round builds the library, not the verdict.** No backtest engine,
no costs, no "which exit wins" lives here — that is round 99 part 2. This
file's only job was: every stop and target method, implemented once,
correctly, with no lookahead, unit-tested, and freely composable.

Files written (and ONLY these — no live file touched, no git command
run, no order placed):

- `exits.py` — the library.
- `test_exits.py` — 37 unit tests, all passing.
- `step99_exit_library.md` — this file.

---

## THE METHOD LIST

All signatures return an `ExitMethod` (a `level_fn(trade_ctx, i) ->
price|None` plus a trigger `style`), except `simulate_partial_scale`,
which is inherently two-legged and returns an `ExitOutcome` directly.
Every constructor lives in `exits.py`; line references below are to that
file's section numbering, not literal line numbers.

### STOPS

| method | signature | shape |
|---|---|---|
| `stop_percentage` | `(pct)` | **BASELINE ONLY** — entry ∓ pct%. Not a candidate; see below. |
| `stop_structure` | `(k, n_back=1, buffer_pct=0.0, use="wick"\|"close")` | beyond the confirmed swing the entry rests on; N-th swing back, buffer, wick-vs-close all parameterised |
| `stop_structure_trailing` | `(buffer_pct=0.0, fallback_pct=5.0)` | ratcheting floor at each new confirmed swing, never back — gold_book.py's LIVE exit, generalized to both directions |
| `stop_atr` | `(mult=1.5)` | entry ∓ mult × ATR(n), fixed at entry |
| `stop_chandelier` | `(mult=3.0)` | highest-high-since-entry ∓ mult × ATR(n), ratcheting |
| `stop_bollinger` | `(use="opposite_band"\|"midline")` | volatility band, opposite side or midline |
| `stop_moving_average` | `(n=20)` | close crosses an EMA(n) — the shape of gold_book's original (pre-round-59) EMA20 exit |
| `stop_breakeven_after_r` | `(base, r_multiple=1.0)` | **composer** — wraps ANY stop, shifts it to entry once MFE ≥ r_multiple × that stop's own R |
| `stop_time` / `target_time` | `(n_bars)` | flatten after N bars regardless of price — one clock, usable in either slot |
| `stop_liquidity_pool` | `(buffer_pct=0.0)` | beyond the pool a sweep-and-reverse entry just traded against |

### TARGETS

| method | signature | shape |
|---|---|---|
| `target_fixed_r` | `(stop, r_multiple)` | R multiple of the PAIRED stop's own distance — 1R/1.5R/2R/3R all fall out of this with different r_multiple |
| `target_structure` | `(n_ahead=1, buffer_pct=0.0, use="wick"\|"close")` | the next opposing swing ahead of entry |
| `target_liquidity_pool` | `(tol_pct=0.1)` | the next equal-highs/equal-lows pool ahead of entry |
| `target_measured_move` | `(extension=1.0)` | height of the preceding leg, projected from entry |
| `target_trail_only` | `()` | no target — ride the paired stop (or pass `target=None`) |
| `target_opposite_signal` | `(signal_arr, treat_zero_as_exit=False)` | out when the caller's own entry rule flips |
| `simulate_partial_scale` | `(tc, stop, final_target, max_hold_bars, r_multiple=1.0, frac=0.5, move_to_breakeven=True)` | take `frac` at r_multiple×R, move stop to breakeven, let the rest run to `final_target` (or trail) |

### REGIME CLASSIFIER

`classify_regime(candles, i, atr_n=14, vol_lookback=14, expand_ratio=1.2,
contract_ratio=0.8) -> dict` — causal, no-lookahead. `structure` ∈
{uptrend, downtrend, range-consolidation, transition} (reuses
`chart_reader.read_chart()`'s own structure/quality/momentum read,
collapsed to the mandate's 4 states); `volatility` ∈ {expanding,
contracting, flat} (current ATR vs its value `vol_lookback` bars earlier
— computed fresh, NOT chart_reader's candle-body "momentum", a related
but distinct concept).

### DISTANCE REPORTING

`describe_distance(entry_price, level_price, leverage=20.0) -> dict` —
every distance in both units, per `BLOFIN_API_REFERENCE.md`'s convention
("5% of margin = 0.25% price move at 20x"). `price_pct × leverage =
margin_pct` exactly (linear scaling of `unrealizedPnlRatio`'s own
definition — verified in that file against a live position).

### THE ENGINE

`run_trade(trade_ctx, stop, target, max_hold_bars) -> ExitOutcome` — the
ONE generic walker. ANY `ExitMethod` built for a stop slot pairs with ANY
`ExitMethod` built for a target slot; nothing hardcodes a pairing table
the way `step59_exit_science.py`'s X0-X5 did. Stop is checked first every
bar and wins same-bar ties (this repo's standing convention). `target=
None` = trail-only. Gap-through fills (`_gap_or_level`) reused verbatim
from step59/step48's convention.

---

## WHY THE COUNT IS WHAT IT IS

10 stops, 7 targets (one of which, `simulate_partial_scale`, is really a
whole second small engine, not a plain level method), a regime
classifier, and a distance reporter — 24 unit-tested public surfaces.
Every combination of the 9 real (non-baseline) stops × 6 real (non-
partial-scale) targets is a valid pairing the round-99-part-2 backtester
can try — 54 pairings before even touching parameters like k, mult,
r_multiple, or n_back/n_ahead, which is the actual point: the mandate
asked for a library thorough enough to search, not a pre-picked
shortlist.

---

## WHAT WAS REUSED VS WRITTEN NEW

**Adapted, not imported** (see `exits.py`'s module docstring for the full
reasoning — the short version: `step59_exit_science.py` pulls in
`backtest.py`, `step45b_news_events.py`, and a news classifier at import
time, appropriate for a one-off research script, wrong for a shared
library every future round will import):

- `find_pivots()` — copied verbatim from `step59_exit_science.py`'s
  `find_pivots()`.
- `_gap_or_level()` — copied verbatim from `step59_exit_science.py`
  (itself step48's convention).
- `_nth_pivot()` — generalizes `step59_exit_science.py`'s
  `most_recent_favorable_pivot()` / `most_recent_protective_pivot()`
  (both were `n_back=1` special cases) to any N-th swing back, per the
  mandate's "parameterise WHICH swing" requirement.
- `_nearest_liquidity_cluster()` — adapted from
  `step59_exit_science.py`'s `nearest_liquidity_cluster()`, generalized
  with a `side` parameter so one function serves `target_liquidity_pool`
  and would serve a protective-side liquidity stop too.
- `stop_structure_trailing()` — the SAME ratcheting-floor design
  `step59_exit_science.py`'s X3 sealed-validated (GOLD +$440.81/t vs the
  EMA20 incumbent's +$56.44/t) and that **gold_book.py runs LIVE right
  now** via `_compute_trail_floor()`/`_find_swing_lows()` (K_SWING=5).
  Generalized here to short trades — gold_book's live version is
  long-only by design (that book never shorts); this function's long
  branch matches it pivot-for-pivot. This is the literal "IMPORT/adapt
  it, do not rewrite from scratch" instruction, done.

**Imported, unmodified:**

- `liquidity_pools()` from `step56_smc_toolkit.py` — used verbatim
  inside `stop_liquidity_pool()`. This is the mandate's other explicit
  instruction ("step56_smc_toolkit has pool detection — reuse it"), done
  literally: `stop_liquidity_pool()` calls step56's function directly, no
  reimplementation.
- `atr()` from `strategy.py` — the repo's one true ATR, unmodified.

**Reused pattern, new code:**

- `classify_regime()` calls `chart_reader.py`'s `read_chart()` wholesale
  (not a re-derivation of structure/quality/momentum) — per the mandate's
  "chart_reader.py already computes structure, quality and momentum
  reads — reuse it rather than inventing a parallel vocabulary."
- `self_test_causality()` follows `step84_blind_drill.py`'s
  `self_test_causality()` pattern exactly (render/compute from the full
  series and from a series truncated one bar past the decision point,
  assert identical output) — adapted from PNG-byte comparison to
  price-level comparison, same proof shape.
- `_FAR_FUTURE` "now" sentinel for `chart_reader.read_chart()`'s
  forming-bar suppression — the exact convention `step84_blind_drill.py`'s
  `eye_read_at()` already uses.

**New this round, no prior version existed:** the whole
`SeriesCtx`/`TradeCtx`/`ExitMethod`/`run_trade` composition architecture;
`stop_atr`, `stop_chandelier`, `stop_bollinger`, `stop_moving_average`,
`stop_breakeven_after_r`, `stop_time`/`target_time`, `target_fixed_r`,
`target_measured_move`, `target_opposite_signal`, `target_trail_only`,
`simulate_partial_scale`, `describe_distance`, and `classify_regime`'s
volatility-state calculation.

---

## THE CAUSALITY PROOF

Two layers, both passing:

1. **`exits.py`'s own `self_test_causality()`** (run via `python3
   exits.py`) — builds a `SeriesCtx` from a full synthetic series and a
   second from the series truncated to `[:decision_idx+1]`, and asserts
   `stop_structure_trailing()`'s level at `decision_idx` (the hardest
   case — it scans pivot history) is byte-identical between the two.
   Passes.

2. **`test_exits.py::test_causality_truncation_all_methods`** — the
   exhaustive version. Same truncate-and-compare proof, run across
   EVERY level-based method in the library (`stop_structure` at two
   different `n_back` values, `stop_structure_trailing`, `stop_atr`,
   `stop_chandelier`, both `stop_bollinger` variants,
   `stop_moving_average`, `stop_liquidity_pool`, `target_structure`,
   `target_liquidity_pool`, `target_measured_move`, plus two composed
   methods — `target_fixed_r` and `stop_breakeven_after_r` — which read
   another method's level internally, so the proof covers composition
   too, not just atomic methods). All 12 base methods and both composed
   methods return identical levels with and without future bars
   available. Passes.

**Why this is a structural proof, not a promise:** every `level_fn` in
`exits.py` is written as a pure function of `(trade_ctx, i)` that only
ever indexes `trade_ctx`'s arrays at positions `<= i` (directly, or via
pivot dictionaries gated by `confirm_idx <= i`, which encodes the exact
same causal guarantee find_pivots documents). There is no per-trade
mutable state threaded across bars that could accidentally leak a
future value in — even the ratcheting methods (`stop_structure_
trailing`, `stop_chandelier`, `stop_breakeven_after_r`) recompute their
answer from scratch from `[entry_idx:i+1]` on every call. That's what
makes the truncation test meaningful instead of coincidental: there is
no code path left that COULD read past `i`.

---

## UNIT TESTS

`test_exits.py` — 37 tests, plain asserts, `TESTS` list, `main()` runner
printing PASS/FAIL (this repo's own style, no pytest). Run: `python3
test_exits.py`. Current result: **ALL 37 TESTS PASSED**.

Every fixture is small and hand-checkable — the docstring above each test
states the expected number BEFORE the assertion, derived by explicit
arithmetic (fractal-pivot windows, EMA recursion, constant-ATR
construction so True Range is provably 2.0 or 1.0 on every bar, Bollinger
bands cross-checked against an independent numpy calculation), not
copy-pasted from a first run of the code under test. Coverage:

- pivot primitives (`find_pivots`, gap-through fill) — 2 tests
- every stop method (baseline, structure ×3, structure-trailing ×3, ATR,
  chandelier, Bollinger, moving-average ×2, breakeven composer, time,
  liquidity-pool ×2) — 16 tests
- every target method (fixed-R composing with two different stops,
  structure, liquidity-pool, measured-move, trail-only, opposite-signal)
  — 6 tests
- the generic engine (stop-wins-tie, gap-through, time-cap, target=None
  trail-only, short-direction mirror) — 4 tests
- partial scaling (two-leg happy path with blended price, stop-before-
  partial single-leg collapse, undefined-R returns None) — 3 tests
- regime classifier (uptrend, range-consolidation, volatility expanding/
  contracting) — 3 tests
- distance reporting — 1 test
- causality — 2 tests (the exhaustive multi-method truncation proof, and
  `exits.py`'s own smoke-test function)

A real-data smoke run (not part of the test suite, done for this report
only): `build_series_ctx` on 3,000 real BTC-USDT 1h bars takes ~18ms;
352 (entry × direction × stop × target) trade walks across 4 stops × 4
targets × 22 entries × both directions complete in ~70ms with every
result landing on a sane bar/price. No crashes, no NaN leaks, on real
market data — the synthetic fixtures aren't hiding a real-data-only bug.

---

## WHAT I THINK IS MISSING FROM THE TAXONOMY

Things I noticed while building this that the mandate didn't name, worth
a look before or during round 99 part 2:

1. **Bollinger as a TARGET, not just a stop.** The mandate lists
   Bollinger only under STOPS, but "opposite band as a mean-reversion
   take-profit" is a completely standard use in a range/consolidation
   regime — `stop_bollinger`'s level_fn already works fine dropped into
   the target slot (nothing in `run_trade` restricts a method to one
   role), it just isn't offered under a `target_` name. Cheap to add
   later if part 2 wants it — flagging rather than building it now to
   stay inside this round's scope.
2. **A volatility-contraction ("squeeze") ENTRY-side stop tightener.**
   Not built — this file has no opinion on entries — but worth noting:
   `classify_regime`'s volatility state is exactly the signal a
   "tighten stops going into a squeeze, widen coming out of one" rule
   would key off. That's a part-2 (or later) composition, not a new
   primitive.
3. **A pure day-of-week / session-time exit** (e.g., "flatten before the
   weekend" or "flatten before a scheduled macro print") — genuinely
   common in real trading, distinct from a plain bar-count time stop.
   Not built; would need a caller-supplied timestamp predicate, the same
   shape as `target_opposite_signal`'s caller-supplied array. Easy to
   add as `target_scheduled_time(predicate)` if part 2 wants it.
4. **Correlated-asset invalidation** (e.g., exit a BTC long if ETH
   breaks its own structure first) — mentioned nowhere in the mandate,
   but the "chart proves the idea wrong" principle applies just as much
   across assets as within one. Out of scope for a single-asset
   `TradeCtx`; would need a second `SeriesCtx` passed alongside. Flagging
   only.
5. **`stop_structure`'s buffer_pct is signed the same way for both
   stops and targets** (always widens away from entry) — I did NOT add
   a symmetric buffer to every target constructor, only where it felt
   natural (`target_structure`). Worth a second pass if part 2 finds a
   target that needs it and doesn't have it.

None of these block part 2 — they're notes for it, not gaps in what was
asked for this round.
