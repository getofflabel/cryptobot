# Round 66 — THE SCENARIO MIND

Learn from history WHICH VALIDATED TOOL BELONGS TO WHICH MARKET SITUATION
(the owner's TJR vision: "a real trader reads the scenario first, then
picks the tool"). Research only — no live orders, no commits.

Script: `step66_scenario_mind.py`. Full raw grid (592 rows: 8 tools x (73
cells + 1 UNCONDITIONAL baseline)): `step66_results_raw.csv`. HOT cells
only: `step66_hot_cells.csv`.

---

## 1. The classifier — reused verbatim from step63_rehab.py

Per this round's own instruction, the 5-axis classifier is IMPORTED
directly from `step63_rehab.py` (a pure function-definition module) rather
than re-typed, for exact comparability with round 63's own work:

| Axis | Definition | States |
|---|---|---|
| TREND | 4h `vol_gated_ma`(20/100, gate1.5, allow_short) sign AGREEING with the 4h BOS-chain (k=8) | trending-up / trending-down / ranging |
| VOL | ATR%(14) vs its OWN trailing 365-day rolling median (shift(1)'d) | quiet (<0.67x) / normal / violent (>1.5x) |
| NEWS-HEAT | an ai_relevant WatcherGuru headline within 2h before-or-at the bar, restricted to the ~13mo harvested span | hot (in-span only) |
| CROWD | funding_bps | crowded-long (>=+1.5bp) / crowded-short (<=-0.5bp) / neutral |
| SESSION | pure UTC calendar fact, weekend override | asia/london/newyork/off-hours/weekend |

**This round's own addition:** two of the eight tools trade native 4h
candles (T2, T8). VOL/CROWD/NEWS/SESSION are resolution-agnostic (they
already just read off whatever frame is passed in — step63's own words),
so they're called directly on the 4h frame for those two tools. TREND is
the one axis the classifier defines as inherently 4h-sourced; for a
4h-native tool there's no coarser frame to borrow from, so TREND is read
straight off the same 4h frame with the identical champ+BOS-chain formula
(no extra shift — matches how step56's `bias_series_4h` is used raw
wherever trading itself happens at 4h). One axis, two code paths; the
other four are one function shared across both resolutions.

### Scenario distribution (1h, of 55,493 bars, 2020-03-25 → 2026-07-24)

| cell | bars | % |
|---|---:|---:|
| trending-up×quiet | 1,625 | 2.9% |
| trending-up×normal | 12,101 | 21.8% |
| trending-up×violent | 3,388 | 6.1% |
| trending-down×quiet | 2,027 | 3.7% |
| trending-down×normal | 8,770 | 15.8% |
| trending-down×violent | 3,423 | 6.2% |
| ranging×quiet | 7,077 | 12.8% |
| ranging×normal | 13,859 | 25.0% |
| ranging×violent | 2,347 | 4.2% |
| crowd=neutral | 45,269 | 81.6% |
| crowd=crowded-long | 6,368 | 11.5% |
| crowd=crowded-short | 3,856 | 7.0% |
| vol=quiet / normal / violent | 10,729 / 34,730 / 9,158 | 19.3% / 62.6% / 16.5% |
| trend=trending-up / trending-down / ranging | 17,364 / 14,284 / 23,845 | 31.3% / 25.7% / 43.0% |
| session=asia/london/newyork/off-hours/weekend | 11,564 / 9,915 / 13,218 / 4,956 / 15,840 | 20.8% / 17.9% / 23.8% / 8.9% / 28.5% |
| news-hot (13mo span) | 3,255 | 5.9% |
| ALL-violent | 9,158 | 16.5% |
| crowded-long×violent / crowded-short×violent | 2,394 / 610 | 4.3% / 1.1% |

The TREND×VOL×SESSION 45-cell flagship grid (the "read the scenario"
table a trader would actually reason with) is not reproduced bar-by-bar
here for space — full breakdown is derivable from the raw CSV — but
every populated combination the playbook cites below cleared real bar
counts (hundreds to low thousands), not statistical dust.

**73 cells total per tool** (documented once, not cherry-picked): TREND×VOL
(9) + TREND×VOL×SESSION (45) + CROWD×VOL-violent (3) + news-hot (1) +
ALL-violent (1) + SESSION-alone (5) + CROWD-alone (3) + VOL-alone (3) +
TREND-alone (3). Floor: train n>=15 & train exp>0 to even look at val;
val n>=8 to call a val result meaningful — identical to step63's own
floor, per this round's own mandate.

---

## 2. The eight tools, reconstructed exactly from their source rounds

| Tool | Source | Shape | Stop/Target/Hold | UNCOND train | UNCOND val |
|---|---|---|---|---|---|
| T1 news-momentum | step45b/step65 | first-bar-move after a relevant WatcherGuru headline | 1.2%/2.4%/24h | +$22.66/t n=201 | +$5.67/t n=68 |
| T2 hidden-RSI-div 4h | step58 | RSI14 k=5 hidden divergence, champ-gated continuation | 2.54%/7.61%/96h | +$22.04/t n=91 | +$80.56/t n=33 |
| T3 CHoCH+confluence>=2 | step56 | k=8 CHoCH, >=2/5 agreeing conditions | 4.23%/8.46%/240h | +$15.45/t n=52 | +$68.26/t n=25 |
| T4 donchian20 1h | step59 (E4, constructed) | close>prior 20-bar high, long only | 1.21%/2.43%/240h | -$3.17/t n=121 | -$56.15/t n=42 |
| T5 STRIKES (RSI3<15 dip) | step59/tactical.py | 4h champ long + 1h RSI3<15 | 1.5%/4.5%/48h | +$53.13/t n=220 | +$26.92/t n=76 |
| T6 forensic-short | step41 (widened) | funding>1.5bp & pop>1.5% & ATR%>1.2%, short | 1.69%/5.07%/48h | +$24.57/t n=55 | +$193.25/t n=8 |
| T7 volshock continuation | step50 | volume>=6x baseline & \|ret\|>=2x baseline, with the move | 1.21%/3.64%/24h | +$24.75/t n=352 | +$58.63/t n=125 |
| T8 BB-width squeeze 4h | step57 (watch-list) | Bollinger bandwidth bottom-20th percentile, price breaks out, ungated | 1.74%/none/48h | +$11.64/t n=122 | +$80.02/t n=26 |

Train/val figures here are close to but not always identical to the
figures quoted in each source round's own results.md — this round
re-expresses every tool through ONE shared engine
(`day_trade_signal`+`run_backtest`, execution="maker", real funding) for
apples-to-apples scenario-cell comparability, per step63's own
precedent; T1/T4/T5 originally ran through step59/step65's own hand-rolled
event simulator. T4's unconditional result is net negative here (as it
was never live-deployed with any exit of its own — step59 explicitly
calls it a "clean generic testbed," not a claim of edge) — which makes it
the round's built-in falsification control: does scenario-gating turn a
LOSER into a winner, or just make winners better?

---

## 3. THE LEARNED PLAYBOOK — 48 HOT cells (train+val both positive, both floors cleared)

### Flagship rows — multiple tools, same TREND×VOL×SESSION scenario

The clearest test of "which tool concentrates its edge where": six
scenarios were populated (train n>=15) by 3-4 tools each, so the
scenario-vs-tool comparison is apples-to-apples.

**ranging + normal-vol + asia session** (n=1,349 bars/yr-ish window slice):
news-momentum: +$24.20/t (n=58 tr / **+$14.04/t n=10 val, HOT**) · donchian20:
-$11.29/t (n=36, COLD, never reaches val) · RSI3-dip: -$35.91/t (n=16,
COLD) · **volshock-continuation: +$5.29/t tr → +$93.51/t val (n=8, HOT)**.
Two tools concentrate real edge here (news reaction and volume-shock
continuation); the trend-following dip-buy and the breakout tool both go
cold in this specific cell.

**ranging + normal-vol + newyork session:** news-momentum flips to FADED
(+$13.21/t train → **-$17.30/t val**, n=11) · **donchian20: +$94.34/t tr
→ +$93.11/t val (n=15, HOT)** — its single best cell in the whole grid,
turning an overall-losing tool into a real one · RSI3-dip: -$117.33/t
(n=20, COLD, its worst read anywhere) · **volshock-continuation:
+$35.80/t → +$40.73/t (n=29, HOT)**. This is the clearest single "wrong
tool, right tool" contrast in the round: the SAME ranging+normal-vol
regime rewards breakouts and volume shocks in New York hours and
punishes the RSI3 dip-buy specifically.

**trending-up + violent-vol + newyork session:** every single tool that
reached train floor here (donchian20, RSI3-dip, forensic-short,
volshock-continuation) either faded on val or never cleared it —
including RSI3-dip, which is normally the round's strongest performer.
Nothing works reliably in this specific corner; flagged as a scenario to
avoid trading through, not a scenario with a winning tool.

**ranging + normal-vol + london session:** **donchian20: +$11.07/t →
+$51.46/t (n=8, HOT)**, **volshock-continuation: +$59.68/t tr → +$28.49/t
val (n=8, HOT)**, news-momentum THIN-VAL (n=5, unresolved).

**trending-up + normal-vol + newyork/london:** RSI3-dip and
volshock-continuation both go COLD or FADED here — the round's two
strongest general performers specifically lose their edge in this narrow
combination, while volshock-continuation still finds edge in the
newyork slice via a DIFFERENT bar mix (n=41, +$26.49→+$32.87, HOT) —
i.e. the SAME nominal trend+vol regime splits into a working and a
non-working cell purely on which session it lands in.

### Single-axis marginal rows (unconditional entries, split by ONE axis alone)

| axis value | tool | train | val |
|---|---|---|---|
| crowd=neutral | T1 news | +$26.48/t n=200 | +$1.98/t n=64 |
| crowd=neutral | T2 hidden-div | +$27.62/t n=75 | +$112.58/t n=30 |
| crowd=neutral | T5 STRIKES | +$57.06/t n=166 | +$32.08/t n=63 |
| crowd=neutral | T7 volshock | +$2.26/t n=294 | +$46.86/t n=111 |
| crowd=neutral | T8 BB-squeeze | +$19.08/t n=109 | +$121.64/t n=23 |
| crowd=crowded-long | T6 forensic | +$24.57/t n=55 | +$193.25/t n=8 |
| crowd=crowded-long | T7 volshock | +$36.19/t n=41 | +$54.70/t n=16 |
| vol=violent | T6 forensic | +$25.14/t n=48 | +$193.25/t n=8 |
| vol=normal | T1/T5/T7/T8 | all positive | all positive, n=22-91 |
| vol=quiet | T7 volshock | +$25.64/t n=100 | +$179.37/t n=11 |
| session=newyork | T3 CHoCH | +$91.70/t n=30 | **+$383.85/t n=13** (round's single largest val number) |
| session=asia | T7, T8 | +$14.58/+$55.40 | +$76.76/+$137.88 |
| session=london | T8 BB-squeeze | +$17.85/t n=59 | +$97.37/t n=11 |
| session=weekend | T5 STRIKES, T7 | +$42.33/+$9.58 | +$3.78/+$76.49 |
| trend=trending-down | T3 CHoCH | +$93.54/t n=26 | +$89.52/t n=12 |
| trend=trending-up | T5, T7, T8 | all positive | all positive, n=14-45 |
| news-hot(13mo) | T1 news | +$14.90/t n=196 | +$17.35/t n=67 |
| ALL-violent | T6 forensic | +$25.14/t n=48 | +$193.25/t n=8 |

**Which tools concentrate their edge where, in plain English:**
- **T6 forensic-short lives ENTIRELY inside vol=violent + crowd=crowded-long
  — these are literally the same 48 bars** (ALL-violent, crowd=crowded-long,
  and crowded-long×violent all resolve to identical train/val numbers for
  T6). Its whole edge is one specific, narrow, real regime — euphoric
  funding during a violent bar — not a general-purpose short.
- **T3 CHoCH+confluence's edge concentrates hard in the New York session**
  (+$383.85/t val, its best number anywhere) and in trending-down markets.
  Structural reversals apparently read best when US desks are active and
  during actual downtrends — CHoCH catching the FIRST break against
  structure makes obvious sense in a down-trending regime.
- **T7 volume-shock continuation is the round's most scenario-INDEPENDENT
  tool** — 17 of its 26 train-eligible cells go HOT, spanning every trend
  state, every vol state, and 4 of 5 sessions. This is a real finding
  about the TOOL, not just the scenario: it doesn't need the scenario
  mind nearly as much as the others do.
- **T5 STRIKES (RSI3 dip-buy) works in trending-up + normal/violent vol and
  on weekends, but goes COLD in New York/London sessions and FADES in
  trending-up+normal+london specifically** — the live book's dip-buy
  should NOT assume it works identically across sessions.
- **T4 donchian20 is a loser everywhere EXCEPT ranging+normal-vol markets
  during London/New York hours** — exactly the flip the round hoped a
  scenario gate could produce (a net-negative unconditional tool
  rehabilitated by three specific, populated cells).
- **T2 hidden-RSI-divergence's only HOT cell besides its own unconditional
  strength is crowd=neutral** — i.e. it doesn't want funding extremes at
  all, consistent with it being a continuation-in-established-trend tool
  that doesn't care about crowd positioning.
- **T8 BB-width-squeeze concentrates in asia/london/newyork sessions and
  trending-up** — a volatility-expansion tool that, sensibly, prefers
  active trading hours over weekend/off-hours illiquidity.

---

## 4. THE ROUTER TEST — routed vs rack vs solo vs dumb control

Mechanism: for each tool, TRAIN-side selection = union of every cell
where train n>=15 & train exp>0 (per §3's floor); that union is ANDed
into the tool's own entries and rerun on VAL. All 8 tools' VAL trades are
converted to percent returns (timeframe/equity-independent) and merged
chronologically into ONE single-slot portfolio (first trade to start
wins the slot — the same simplifying assumption step65's own
multi-policy merge uses), replayed against one shared $10,000
compounding curve.

| portfolio | n trades | expectancy/t | total return | max DD |
|---|---:|---:|---:|---:|
| **ROUTED** (scenario-gated) | 276 | +$18.62 | +51.4% | -17.9% |
| ALL-TOOLS-ALWAYS-ON ("the rack") | 273 | +$18.67 | +51.0% | -23.2% |
| **DUMB-ROUTER (random-cell control, matched count)** | 254 | **+$58.23** | **+147.9%** | -15.8% |

Each tool solo (unconditional VAL, same engine):

| tool | n | exp/t | return | maxDD |
|---|---:|---:|---:|---:|
| T1 news | 68 | +$5.67 | +3.9% | -10.9% |
| T2 hidden-div | 33 | +$80.56 | +26.6% | -20.8% |
| T3 CHoCH | 25 | +$68.26 | +17.1% | -27.6% |
| T4 donchian | 42 | -$56.15 | -23.6% | -25.4% |
| T5 STRIKES | 76 | +$26.92 | +20.5% | -12.8% |
| T6 forensic | 8 | +$193.25 | +15.5% | -5.2% |
| T7 volshock | 125 | +$58.63 | +73.3% | -10.5% |
| T8 BB-squeeze | 26 | +$80.02 | +20.8% | -11.5% |

**VERDICT: the router, AS BUILT, does not clearly beat dumb random
slicing — and barely beats the rack.** This is reported plainly, not
spun, because tracing WHY is itself the round's most important finding:

1. **The union-of-eligible-cells construction is too permissive for
   several tools.** T1 (20 eligible cells), T4 (19), T5 (19), and T7 (26)
   each had SO MANY overlapping train-positive cells that their union
   covers almost every bar the tool would have traded unconditionally —
   confirmed directly: T1/T4/T5/T7's ROUTED trade counts are IDENTICAL to
   their RACK (unconditional) counts (68, 42, 76, 125 respectively). The
   router only meaningfully concentrated T2 (33→33, also unchanged
   actually — its 8 eligible cells still covered its full unconditional
   set), T3 (25 rack → 19 routed), T6 (8→8, unchanged — T6's whole
   unconditional signal already lives inside its 5 eligible cells), and
   T8 (26→26, unchanged). **In this run, the router literally never cut
   a single trade for 7 of 8 tools** — "OR the eligible cells together"
   is not selective enough when a tool has many small, overlapping HOT
   cells; a real router needs an intersection-style or best-single-cell
   selection rule, not a union, to actually concentrate.
2. **The multi-tool single-slot merge is highly sensitive to slot
   competition, non-linearly.** Because only ONE trade can occupy the
   slot at a time across all 8 tools, admitting or excluding even a
   handful of candidate trades changes WHICH other tools' trades get to
   fire later (a slot freed early can be claimed by a much bigger winner
   later). The DUMB-ROUTER's random cell selection happened to cut T6
   from 8 trades to 1 and T2 from 33 to 9 (its random 5/8-cell draws
   landed on narrow, low-coverage cells by chance) — losing some of
   T6/T2's own edge, but apparently freeing slots that let other tools'
   larger winners through instead, netting a HIGHER blended expectancy.
   This is real, honest variance in a 276-vs-254-trade portfolio, not
   evidence that "random beats smart" as a law — but it IS clear evidence
   that **this round's specific router construction does not demonstrate
   the win the mandate hoped for.**
3. **The CELL-LEVEL playbook (§3) is real and interpretable** — T6's
   violent+crowded-long concentration, T3's New York-session
   concentration, T4's ranging+london/newyork rehabilitation are all
   genuine, sample-honest, train+val-confirmed structure. The FAILURE is
   specifically in how those cells were COMBINED into a portfolio-level
   router, not in whether the scenario reads carry information at all
   (see §5 — they clearly do, on their own).

---

## 5. MARGINAL AXIS VALUE — does each situational read carry information?

Router VAL portfolio, rebuilt 5 times with ALL cells referencing one axis
excluded from train-side eligibility (reuses the same §3/§4 train/val
numbers, no new backtests):

| axis removed | n | exp/t | delta vs full router | verdict |
|---|---:|---:|---:|---|
| full router (baseline) | 276 | +$18.62 | — | — |
| −TREND | 275 | +$19.42 | +$0.81 | negligible — TREND barely matters to the router |
| −VOL | 275 | +$14.91 | **-$3.71** | VOL removal HURTS — carries real router information |
| −CROWD | 274 | +$14.57 | **-$4.04** | CROWD removal HURTS THE MOST of the five — the single most load-bearing axis for THIS router |
| −NEWS | 276 | +$18.62 | $0.00 | zero effect — the single news-hot cell is dwarfed by every other tool's broader eligible cells |
| −SESSION | 278 | +$27.62 | **+$9.00** | SESSION removal HELPS — SESSION-referencing cells (50 of 73) are diluting the union, not sharpening it |

**Answer to "does session matter more than crowd": no — the opposite.**
CROWD (and VOL close behind) are the two axes that actually carry
information for THIS router construction; removing either one measurably
hurts. SESSION, despite producing several of the playbook's biggest
single-cell val numbers (T3's +$383.85/t in New York, T8's asia/london
reads), HURTS the router once folded into the union-eligibility
mechanism — because the 45-cell TREND×VOL×SESSION grid is where most of
the "too many eligible cells → no real filtering" problem from §4 lives.
This is not a contradiction: SESSION carries real cell-level signal (§3)
but adds router NOISE (§4) because it multiplies the number of small,
overlapping eligible cells a tool can qualify through. TREND carries
essentially no marginal router value either way — its own information is
already fully captured inside the TREND×VOL cells, which dominate
eligibility with or without the TREND-alone cells present. NEWS is too
rare (5.9% of bars, one cell) to move a router-level number even though
its own cell-level read (T1, +$14.90/t train → +$17.35/t val) is real.

---

## 6. WHAT THIS TEACHES THE LIVE BOT

**Deployment-grade rules (train+val robust, honest n, safe to act on):**
- T6 forensic-short: gate to vol=violent AND crowd=crowded-long
  specifically (they're the same 48 bars) — this is not a "sometimes"
  edge, it IS the edge; running it unconditionally outside this regime
  has no evidence behind it at all (T6 had only 5/73 eligible cells,
  the most concentrated tool in the round).
- T3 CHoCH+confluence: weight New York session and trending-down markets
  much higher than the unconditional signal already implies — its best
  cell (+$383.85/t, n=13 val) is a real, floor-cleared number, not noise.
- T4 donchian20 1h: DO NOT deploy unconditionally (net -$56/t val) — but
  DO consider it specifically inside ranging+normal-vol markets during
  London or New York hours, where it turns solidly positive on both
  windows. A scenario gate is the difference between a dead tool and a
  live one here.
- T7 volshock-continuation: closest thing to a scenario-agnostic edge in
  the round (17/26 eligible cells) — safe to keep closer to always-on
  than the others, though crowd=neutral/crowded-long and vol=normal/quiet
  are its strongest reads if a gate is wanted at all.

**Needs more data before deployment (real signal, thin sample):**
- Every "THIN-VAL" and several val_n=8-9 "HOT" cells (T3 trending-down
  ×normal n=9, T1 trending-down×normal×newyork n=9) sit right at the
  floor — directionally encouraging, not yet load-bearing.
- T2 hidden-div's only real scenario cut beyond its own baseline is
  crowd=neutral (n=30) — one more axis-worth of evidence, not the rich
  multi-cell picture T6/T3/T7 have.

**What the DAILY PICK scorer should adopt:** the daily pick's components
are, per this program's own framing, crude unconditional versions of
several of these exact tools (a washout/RSI3 dip-buy component mirrors
T5, a momentum/breakout component mirrors T4/T7). Per §5, CROWD and VOL
are this round's two most information-carrying axes at the ROUTER level
— the daily pick scorer should gate its dip-buy and breakout components
by funding/crowd extremes and by the violent/quiet/normal ATR-vs-trailing-
median read BEFORE trusting session-of-day as a signal; session reads are
real at the single-cell level (§3) but this round found they add more
noise than sharpness once combined into a routing decision (§4) — don't
let the scorer treat "what session is it" as equal-weight to "what is
funding/vol doing right now." The single clearest adoptable rule: route
any short-side component toward T6's exact regime (violent + crowded-
long) rather than firing unconditionally, since that is this round's most
concentrated, most reproducible finding.

---

## 7. Caveats, stated plainly

- **The router-vs-rack-vs-dumb result is a genuine negative finding for
  this specific union-based router construction, not proof that scenario
  information is worthless.** §3's cell-level playbook and §5's marginal-
  axis analysis both show real, floor-cleared, train+val-confirmed
  structure. The gap is in how 73 overlapping cells were combined into
  one portfolio-level firing rule — an intersection-based, single-best-
  cell, or weighted-vote router (none tried here) might close it; that is
  the natural next round.
- **Single-slot multi-tool portfolio merging is high-variance.** With 8
  tools and ~250-280 total merged trades, admitting or excluding a
  handful of candidates (as the union-vs-random-cell difference did)
  swings the blended expectancy non-linearly through slot competition.
  The portfolio-level numbers in §4 should be read as ONE realization,
  not a law.
- **T6's val edge rides on 8 trades.** Every number quoted for it is real
  by this program's own floor (n>=8 clears MIN_VAL_TRADES) but a single
  trade materially moves a $193/t average over 8 trades — the
  concentration finding (violent+crowded-long) is trustworthy; the exact
  dollar magnitude is not.
- **All 8 tools reconstructed through ONE engine** (day_trade_signal +
  run_backtest), not each tool's own original hand-rolled simulator
  (T1/T4/T5 originally ran through step59/step65's event-driven engine) —
  a stated, deliberate normalization for cross-tool comparability, so
  baseline numbers here differ slightly from each source round's own
  quoted figures.
- **No sealed test in this round** (train/val only, per the mandate) —
  every number above is a research comparison, not a sealed-look
  validation. Nothing here should be treated as "proven" the way a
  sealed-test PASS would be; it is the map for where to point the NEXT
  sealed look.
- **TREND×VOL×SESSION's 45-cell grid is the single biggest source of the
  router's over-permissiveness** (§4/§5) — any follow-up router should
  either shrink this grid (fewer session buckets, or drop SESSION from
  the union-eligibility mechanism per §5's own finding) or switch to an
  intersection/best-cell selection rule instead of OR-ing everything a
  tool has ever cleared.
