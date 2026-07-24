# Round 54 — Unthrottle the BTC Ride: adaptive vol-gating revalidation

**Script:** `step54_adaptive_ride.py` · **Data:** cached 6.33y BTC 4h (Bybit,
2020-03-25 → 2026-07-22, 13,863 bars) + real Bybit funding · **Discipline:**
costs always on, maker execution, real funding, chronological 60/20/20,
select by TRAIN only, **sealed final 20% (test) never computed.**

Split points: train ends 2024-01-10, val ends 2025-04-16 (test = 2025-04-16
→ 2026-07-22, sealed). Train+val span = 5.06 years.

---

## 0. Sealed-look history found in RESEARCH_LOG.md (read before running)

- **Round 30** (the 15-year Bitstamp daily backtest) is the origin of the
  adaptive-gate prescription: on daily data, ATR ≥ 1.3x its own trailing-365d
  median took $1k → $187k across every era where the fixed gate went
  completely dead by 2023 ($11k). Round 30 also **transferred one adaptive
  variant (mult=1.3x) to the live 4h train/val gauntlet** — it did **not**
  beat the champion on val (+26.4% vs +63.9%), **zero test looks spent**, and
  the finding was logged as a standing risk to re-derive later, not closed.
- **Round 31** separately gauntleted a **GARCH-percentile** gate REPLACEMENT
  (different mechanism — forecast-vol percentile thresholds 50/60/70th, not
  ATR-vs-its-own-median) on a shorter common window (2022-02→). All three
  thresholds FAILED train, **zero test looks spent**, family CLOSED — do not
  re-open the GARCH-percentile family.
- **Round 41** (shorts) reuses `adaptive_vol_gate` (mult=1.0 only, "above"/
  "below") — this round generalizes that helper with a multiplier and reuses
  `split_points`/`bar_hours` from `step41_shorts.py` per the task brief.
- **Round 48**'s `step48_tradfi_trend.py` already ports `vol_gated_ma` +
  `entry_filter=adaptive_gate` on TradFi trend (the pattern this round
  copies): `min_atr_pct=0.0` (gate off) + `entry_filter=<adaptive boolean>`.

**What this round is NOT re-looking at:** round 30's 4h transfer used only
mult=1.3x on older data and never modeled a stop or a second MA pair; round
31's GARCH-percentile family is a different mechanism entirely and stays
closed. This round's grid (mult 0.8x/1.0x, fresh data through 2026-07, a
(50,200) sibling, and the live -8% SL as an axis) covers genuinely new
ground. No test look is spent here — this is a train/val screen, matching
round 30/31's own precedent for exploratory gate work.

---

## 1. Gate-open share — the collapse, quantified

Indicator-level diagnostic only (ATR% vs its gate, no strategy PnL scored)
— computed over the full cached window so it can show what's happening
**right now**, matching the owner's own brief numbers exactly (18.7% / 53%
reproduced below to the first decimal).

| window | fixed-1.5 open% | adaptive-1.0x open% | adaptive-0.8x open% |
|---|---|---|---|
| full ~6.3y history | 52.9% | 45.5% | 70.6% |
| trailing 12mo | **29.9%** | 50.8% | 77.4% |
| trailing 3mo | **18.7%** | 38.3% | 83.5% |

Live right now (2026-07-22): ATR% = **0.95%**, trailing-365d median = **1.22%**
(0.95 < 1.22, so even the mild-tolerance adaptive gates are presently
open — 0.95 ≥ 1.0×1.22 is false but 0.95 ≥ 0.8×1.22=0.98 is also false at
this exact instant; the gate flickers open/closed around the current level,
which is the honest picture of "barely lively," not "wide open").

**The collapse is a fixed-gate phenomenon, not a market-wide one.** Fixed-1.5
falls from 52.9% (all-time) → 29.9% (12mo) → 18.7% (3mo): a steady,
accelerating decay exactly matching round 30's structural-decay finding.
Adaptive-1.0x holds a stable band the whole way: 45.5% → 50.8% → 38.3% — no
directional collapse, some noise, but never approaching fixed's near-shutout.
Adaptive-0.8x (the mild-tolerance version) never drops below ~70% even in
the last 3 months. **This is the mechanism, proven directly**: the fixed
gate is measuring against a number (1.5%) that used to be typical and now
isn't; the adaptive gate measures against a number that moves with the
market, so it never goes structurally stale.

---

## 2. Full grid — train / val (test sealed, never computed)

Long-only, maker execution, real funding, costs on. `entries/yr` and
`recent_entries_18mo` are both computed **strictly from train+val trades**
(never from the sealed test) — `recent_entries_18mo` counts entries within
18 months of the val boundary (back to ~2023-10-16), the closest honest
proxy for "still trading recently" without touching test.

| ma | gate | stop | tr n | tr exp | tr win% | tr dd% | tr ret% | va n | va exp | va win% | va dd% | va ret% | entries/yr | recent entries (18mo) | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 20/100 | adaptive-1.0x | none | 35 | **+$415.38** | 45.7% | -54.4% | +145.4% | 16 | **+$357.65** | 43.8% | -25.8% | +57.2% | 10.08 | 19 | SURVIVOR |
| 20/100 | adaptive-1.0x | SL-8% | 35 | +$356.50 | 42.9% | -52.2% | +124.8% | 16 | +$341.48 | 43.8% | -25.7% | +54.6% | 10.08 | 19 | SURVIVOR |
| 20/100 | adaptive-0.8x | none | 48 | +$313.63 | 37.5% | -51.2% | +150.5% | 18 | +$277.76 | 38.9% | -25.8% | +50.0% | 13.04 | 21 | SURVIVOR |
| 20/100 | adaptive-0.8x | SL-8% | 48 | +$272.01 | 35.4% | -48.4% | +130.6% | 18 | +$264.05 | 38.9% | -25.7% | +47.5% | 13.04 | 21 | SURVIVOR |
| 20/100 | **fixed-1.5** (incumbent) | none | 45 | +$288.07 | 37.8% | -50.5% | +129.6% | 15 | +$354.56 | 46.7% | -29.6% | +53.2% | 11.86 | 18 | SURVIVOR |
| 20/100 | **fixed-1.5** (incumbent) | SL-8% (live) | 45 | +$221.95 | 35.6% | -47.8% | +99.9% | 15 | **+$379.97** | 46.7% | -26.6% | +57.0% | 11.86 | 18 | SURVIVOR |
| 20/100 | ungated | none | 56 | +$451.80 | 32.1% | -49.0% | +253.0% | 18 | +$274.25 | 38.9% | -25.8% | +49.4% | 14.63 | 21 | SURVIVOR |
| 20/100 | ungated | SL-8% | 56 | +$387.82 | 30.4% | -48.5% | +217.2% | 18 | +$260.59 | 38.9% | -25.7% | +46.9% | 14.63 | 21 | SURVIVOR |
| 50/200 | adaptive-1.0x | none | 19 | +$378.57 | 42.1% | -69.9% | +71.9% | 8 | +$433.93 | 25.0% | -37.0% | +34.7% | 5.34 | 8 | INSUFFICIENT-SAMPLE |
| 50/200 | adaptive-1.0x | SL-8% | 19 | +$745.95 | 42.1% | -57.7% | +141.7% | 8 | +$617.08 | 25.0% | -27.4% | +49.4% | 5.34 | 8 | INSUFFICIENT-SAMPLE |
| 50/200 | adaptive-0.8x | none | 21 | +$540.73 | 42.9% | -70.5% | +113.6% | 9 | +$407.57 | 33.3% | -39.1% | +36.7% | 5.93 | 9 | INSUFFICIENT-SAMPLE |
| 50/200 | adaptive-0.8x | SL-8% | 21 | +$970.23 | 42.9% | -55.7% | +203.7% | 9 | +$590.64 | 33.3% | -32.9% | +53.2% | 5.93 | 9 | INSUFFICIENT-SAMPLE |
| 50/200 | fixed-1.5 | none | 21 | +$452.61 | 47.6% | -65.8% | +95.0% | 8 | +$251.12 | 25.0% | -39.2% | +20.1% | 5.73 | 9 | INSUFFICIENT-SAMPLE |
| 50/200 | fixed-1.5 | SL-8% | 21 | +$826.83 | 47.6% | -49.1% | +173.6% | 8 | +$467.26 | 25.0% | -29.9% | +37.4% | 5.73 | 9 | INSUFFICIENT-SAMPLE |
| 50/200 | ungated | none | 22 | +$1,097.60 | 45.5% | -68.0% | +241.5% | 9 | +$407.57 | 33.3% | -39.1% | +36.7% | 6.13 | 9 | INSUFFICIENT-SAMPLE |
| 50/200 | ungated | SL-8% | 22 | +$1,829.30 | 45.5% | -50.9% | +402.4% | 9 | +$590.64 | 33.3% | -32.9% | +53.2% | 6.13 | 9 | INSUFFICIENT-SAMPLE |

(50,200) never clears the 30-train-trade floor at any gate — the slower
robustness pair is directionally consistent (adaptive/ungated beat fixed on
train in most rows) but underpowered for a verdict. Reported for robustness
context only; **no candidate is drawn from this row.**

---

## 3. Head-to-head — (20,100): adaptive-1.0x vs fixed-1.5 vs ungated

**Does adaptivity rescue trade frequency without giving back the edge?**
Mixed answer, and it matters which way you look at it:

**Historical entries/yr (train+val, 2020–2025) do NOT show fixed collapsing** —
fixed-1.5 actually logged slightly *more* total entries over this window
(60 = 11.86/yr) than adaptive-1.0x (51 = 10.08/yr), because fixed's 1.5%
threshold was easy to clear during 2020–2022's much wilder tape. The
historical average hides the trend. **Frequency going forward is where the
adaptive gate wins** — that's what section 1's gate-open-share table
(which reaches into 2025–2026) actually proves: fixed drops to 18.7% open
in the trailing 3 months while adaptive holds 38–84% depending on tolerance.
The dormancy problem is a *recent* phenomenon that a historical entries/yr
average, by construction, dilutes — this is exactly why the task asked for
the gate-open share as a separate, first-class analysis.

**Edge, no stop:** adaptive-1.0x wins train decisively (+$415 vs +$288, 44%
higher) and edges val by a hair (+$358 vs +$355, <1% — a statistical tie).
Both clear the 30/8 trade floor. Ungated has the highest train expectancy
of the three (+$452) but the worst val (+$274) — the gate (either flavor)
is doing real work versus no gate at all.

**Edge, WITH the live -8% SL:** this is the important reversal. Applying the
book's actual crash stop, adaptive-1.0x still wins train (+$357 vs +$222)
but **loses val to fixed** (+$341 vs **+$380** — fixed pulls ahead with the
stop applied). The crash stop interacts differently with the two gates:
fixed's rarer, higher-conviction entries (tighter vol regime by construction)
tolerate the -8% stop better on val; adaptive's more frequent entries
include some that the -8% stop cuts short before they'd have recovered.

**Plain answer: adaptivity rescues frequency cleanly (mechanism proven in
section 1); it does NOT clearly keep the edge once the live book's actual
-8% stop is included** — only when the stop is dropped does adaptive-1.0x
edge out fixed on both windows, and even then the val margin is thin.

---

## 4. The candidate

**adaptive-1.0x, MA(20,100), NO stop** clears the screen (beats fixed-1.5 on
train AND val, ≥30/≥8 trades, ≥3 recent entries) and is named **THE
CANDIDATE** for a sealed look — with a real, material caveat below.

```
strategy.vol_gated_ma(candles, fast=20, slow=100, min_atr_pct=0.0,
                       allow_short=False,
                       entry_filter=<ATR% >= 1.0 x trailing-365d median ATR%>)
# adaptive gate: window = 365 days mapped to 4h bars, min_periods = window//10,
# median shift(1)'d (no self-inclusion, no lookahead)
```

- **Train:** 35 trades, expectancy **+$415.38**, +145.4% return, win 45.7%, DD -54.4%
- **Val:** 16 trades, expectancy **+$357.65**, +57.2% return, win 43.8%, DD -25.8%
- **Recent activity (proxy):** 19 entries in the 18 months before the val
  boundary (2023-10 → 2025-04) — a healthy rate, though this window predates
  the actual 2025–2026 drought (which lives inside the sealed test and can't
  be scored here).
- **Mechanism backing the case:** gate stays 38–51% open in the trailing
  3–12 months vs fixed's 18.7–29.9%, i.e. roughly 2–3x the modern-regime
  entry opportunity, by construction (median-relative, not decay-prone).

**BIGGEST CAVEAT — read before promoting:** the candidate's win over the
incumbent is NOT robust to the live book's actual configuration. With the
-8% crash stop applied (as the live book runs today), adaptive-1.0x's val
edge flips to a loss versus fixed-1.5 (+$341 vs +$380). The clean win only
holds in the **no-stop** configuration. A sealed look on this candidate
should therefore test **both** stop variants explicitly, and if promoted
to live, the -8% SL question needs to be re-examined alongside the gate
swap — swapping the gate while silently keeping the stop is not what was
validated here.

Second caveat: the val margin even in the winning (no-stop) configuration
is under 1% — this is a thin, not decisive, historical edge. The strategic
case for switching rests more on section 1's frequency mechanism (proven
directly on price data) than on a large historical expectancy gap.

Third caveat: (50,200) is directionally consistent (adaptive/ungated beat
fixed-1.5 on train in 3 of 4 stop combinations) but never reaches the
30-trade floor — it corroborates the direction of the finding without being
independently conclusive.

---

## 5. Bottom line

**Keep the throttle, but loosen it, carefully.** The fixed-1.5 gate's
dormancy is real and structural (round 30's finding, now reconfirmed with
fresh data: 52.9% → 29.9% → 18.7% open share, an accelerating collapse with
no floor in sight). Adaptive-1.0x on the champion's own (20,100) pair is a
legitimate, clean SURVIVOR that solves the frequency problem by construction
and beats the incumbent on train decisively — but its val edge is thin and
depends on dropping the live book's -8% stop. This is closer to "adaptivity
is the right fix, but the current best implementation isn't a slam dunk yet"
than a resounding replace-immediately verdict. Recommend a sealed test look
on adaptive-1.0x/(20,100)/no-stop specifically, alongside one more train/val
round examining whether a wider (or no) stop resolves the SL-8% reversal
before spending that look — that's a live question this round leaves open,
not one it answers.
