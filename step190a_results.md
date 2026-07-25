# step190a — SOL third-asset transfer test of BTC's five validated edges

Run: `python3 step190a_btc_edge_transfer_sol.py` (14.2s, cached data only, no network calls).
Data: `data_bybit_SOLUSDT_{1h,4h,1d,funding}.parquet` (Bybit-sourced backtest history,
the repo-wide convention — BLOFIN_API_REFERENCE.md governs live position/account
fields, not backtest OHLCV history). SOL 1h/4h span 2021-10-15 -> 2026-07-23,
chronological 60/20/20: train ends 2024-08-25, val ends 2025-08-08, **test (the
final 20%, 2025-08-08 onward) was never sliced, computed, or looked at anywhere
in this script.**

**Execution: taker, always** (SOL round-trip cost = 18.0bps: 2 x (6bps fee +
1bp half-spread + 2bp slippage), read via `config.fee_bps()` ->
`BlofinExchange.TAKER_FEE_BPS`, BloFin's published standard-account taker rate,
same across BloFin perpetuals including SOL — not computed). This is a
**stricter** bar than the source BTC rounds cleared: step43/45b/54/56/58 all
used `execution="maker"` (2bps/side) as their repo-wide day-trade convention.
A config that survives here would have survived more easily under the
original maker convention, never the reverse.

Chance baseline (families 1/2/4/5): 100-draw random-entry null — same
long/short trade counts, same stop/target/max-hold geometry, same taker costs,
random bar picks — reported as the percentile of random draws the actual
result beats. Family 3 (trend state-machine, not fixed-hold entries) reports
gate-open-share and time-in-market instead, since the random-entry-count null
doesn't fit a position that persists on trend.

## Results table

| # | edge | tf | config (UNCHANGED from BTC) | train n/exp | val n/exp | combined | chance pctile | thickness | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | CHoCH k8 + confluence>=2 | 1h | tgt2x, train-median structural stop | 51t / $165.11 | 20t / $356.22 | **$218.95/t** (71t) | **95th** | **8.4x cost** | **SURVIVOR (train+val)** |
| 2 | 4h hidden RSI(14) divergence | 4h | k8, buf0.35%, tgt3x, hold48h | 55t / -$13.13 | 17t / $95.82 | $12.59/t (72t) | 72nd | 0.6x cost | FAIL |
| 3 | 4h vol-gated trend | 4h | fast20/slow100, gate1.5%, -8%SL | 40t / -$72.13 | 12t / $103.02 | -$31.71/t (52t) | n/a (state machine) | reject (loser) | FAIL |
| 4 | 1h RSI3<10 washout dip-buy | 1h | 1d-trend gate, turn-guard, hold4h | 22t / -$84.06 | 5t / $91.72 | -$51.51/t (27t) | **1st** | reject (loser) | FAIL |
| 5 | 1h news momentum first-bar-move | 1h | stop1.2%/tgt2.4%/hold24h | 201t / -$5.99 | 67t / -$29.33 | -$11.82/t (268t) | 66th | reject (loser) | FAIL |

Full row detail (notional, worst realized move, etc.) in `step190a_table.csv`.

## Edge-by-edge read

**1. CHoCH+confluence>=2 (1h) — the one real positive, unsealed.** SOL's
version is genuinely striking: $218.95/t combined over 71 trades, both windows
positive (train $165.11/71t train share, val even stronger at $356.22), 8.4x
the 18bps round-trip taker cost (clears the 5x thickness bar with room), and
it beats 95 of 100 random-entry draws under the identical stop/target/hold
geometry — real information, not just favorable cost math. The train-median
structural stop hit SOL's 6% hard cap (vs BTC's tighter-running distances) —
**a direct, measured confirmation of the desk's "SOL's tail is fatter, never
inherit BTC's stop geometry" rule**: the same 6%-cap/0.25%-floor constants
(unchanged from step56) still bound the config, but the median distance
itself landed at the ceiling rather than mid-range. **Caveat, stated plainly:
this is a two-window (train+val) result. The sealed 20% test slice was never
touched by this script** — per the repo's look-spending discipline, that is a
separate decision (erosion accounting, neighbor-cluster check), not something
this transfer test spends automatically. Recommend: neighbor-threshold
robustness check (k=5, threshold=1/3) before any sealed look is spent, and
flag to morgan as this round's one live candidate.

**2. 4h hidden RSI divergence — FAILS the transfer, train goes negative.**
BTC's sealed number was +$52.03/t; SOL's identical config nets $12.59/t
combined and is train-negative (-$13.13/t) — it does not even clear the
minimum bar to be scored a survivor (needs both windows positive). Chance
pctile 72 is unremarkable. Thickness 0.6x — nowhere near the 5x floor even
before the verdict. **This edge does not transfer to SOL.**

**3. 4h vol-gated trend, fixed 1.5% ATR gate — FAILS, and the FAILURE MODE
matters as much as the number.** On BTC, the whole point of this edge (per
MARKET_PLAYBOOKS: "the gate's selectivity IS the edge in grinds") is that the
fixed 1.5% ATR threshold is SELECTIVE — it's open only ~18.7% of recent BTC
4h bars, ~53.5% historically. Ported unchanged to SOL, **the same 1.5%
threshold is open 96.7% of ALL SOL 4h bars** (SOL's own median train ATR% is
3.069%, roughly 2-4x BTC's 0.4-0.9% train-window range cited in
MARKET_PLAYBOOKS). The "strict vol gate" is not strict at all on SOL — it
degenerates into an almost-always-on MA-20/100 crossover system, which loses
money here (-$31.71/t combined, -8%SL getting hit hard: worst realized move
-8.03%, i.e. essentially every stop-out prints near the full stop). **This is
exactly the kind of finding a blind constant-port produces: the mechanism
that makes the edge real on BTC (selectivity) evaporates on a more volatile
asset when the number is not re-derived.** A SOL-native gate (re-derived from
SOL's own ATR% distribution, e.g. its own trailing median/quantile rather
than BTC's fixed 1.5%) is a legitimate, cheap follow-up — flagged, not yet
run, to keep this deliverable an honest unchanged-config replay first.

**4. 1h RSI3<10 washout dip-buy — CONFIRMS round 88, now under this desk's
taker standard, and it's worse than random.** This is `daily_pick.py`'s
actual live washout spec (`step83_eye_filter.build_B`, ground truth per that
file's own docstring: RSI3<10, 1d-trend gate, turn-candle guard, ATR-scaled
1.0x/cap1.0%/floor0.05% stop, 1.5x target, 4h max hold). Round 88 already
replayed this exact config on SOL at maker execution: -$47.13/t x27 raw,
-$35.35/t after the (now-removed) chart-read veto, both losers, 68th
percentile against a random-skip control (no information content — this is
what got the veto pulled from production hours after it shipped). This
script reproduces it fresh under taker execution: **-$51.51/t combined across
the identical 27 trades (22 train/5 val), and — new information beyond round
88 — a chance percentile of 1**, meaning the RSI3<10 entries are worse than
99 of 100 random-entry portfolios run through the exact same stop/target/hold
box. Round 88 asked "does the eye's veto add information to this signal on
SOL" and found no; this asks "does the entry signal itself add information
to SOL" and the answer is **actively harmful, not neutral** — buying SOL's
RSI3 washouts times entries into worse outcomes than chance on this history.
**Second independent confirmation SOL does not carry this edge.**

**5. 1h news momentum, first-bar-move — FAILS, unlike BTC's sealed pass.**
Same WatcherGuru event set as BTC (the feed is macro/crypto-general, not
asset-specific — only the candle reaction differs per asset), same exact
geometry (stop1.2%/tgt2.4%/hold24h). BTC's sealed test: +$20.81/t x67,
+13.9%, 52.2% win — the first strategy ever to pass this program's sealed
test. SOL's train+val replay: -$11.82/t combined across 268 events (201
train/67 val), both windows negative, chance pctile 66 (statistically
unremarkable, not even a strong anti-signal like edge 4). MARKET_PLAYBOOKS'
own round-47 finding was that this edge's home is "the 24/7-ness" of crypto
vs TradFi's session gaps — SOL is equally 24/7, so 24/7-ness alone is not
sufficient; something about BTC specifically (deepest liquidity, the actual
subject of most WatcherGuru posts, tightest link between the feed's content
and the traded instrument) carries the edge that a fast, thinner, more
narrative-driven altcoin does not inherit for free. **Third failed transfer.**

## Bottom line for morgan

**1 of 5 BTC edges shows real, thick, two-window positive information on SOL
(CHoCH+confluence, unsealed). The other 4 fail the unchanged-config replay —
two of them (vol-gated trend, RSI3 washout) fail for reasons that are
independently informative**: the vol gate's selectivity mechanism doesn't
survive contact with SOL's structurally higher ATR without re-derivation, and
the washout dip-buy is actively anti-correlated with good outcomes on SOL
(not merely neutral), a second independent confirmation (after round 88)
that this specific edge is BTC/ETH-fitted rather than a general crypto
mechanism. This is exactly the third-asset-check role stated plainly: BTC and
ETH agreeing was never evidence on its own, and four of five "validated"
edges did not survive contact with a genuinely different, faster, thinner
market.

## Files
- `/Users/wallacechen/cryptobot/step190a_btc_edge_transfer_sol.py`
- `/Users/wallacechen/cryptobot/step190a_results.md` (this file)
- `/Users/wallacechen/cryptobot/step190a_table.csv`
- `/Users/wallacechen/cryptobot/step190_common.py` (shared scoring/chance-baseline/thickness helpers, reused by step190b+)
