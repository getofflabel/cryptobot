# Round 132 — crypto/gold family-shape ports on SPX

Script: `step132_crypto_gold_ports.py`. Tables:
`step132_table_partA_donchian_transfer.csv`, `partB_divergence.csv`,
`partC_rsi3.csv`, `partD_volgate.csv`. Full narrative in
`step130_family_map.md` rows 10-13.

Before writing this script, `step48_tradfi_trend.py` and
`step77_spx_playbook.py` were read in full so nothing here repeats
settled ground — see this script's own module docstring for the exact
accounting (CHoCH+confluence and trend+vol-gate were already tested and
are cited, not re-run).

## Results

- **Donchian20/55 + EMA20-exit** (gold's shape, R48's exact function
  reused unmodified): SPY/QQQ reproduce R48's own numbers to two decimal
  places (good sanity check). **ES=F, the one leg R48 never tested,
  FAILS** — negative on train itself for both N=20 and N=55, despite a
  noisy positive val number that was never earned by a positive train
  read. DEAD on the futures leg; the SPY/QQQ result stands as already
  validated by R48, unchanged.
- **RSI hidden/regular divergence, confirmation-gated by SMA200 trend**
  (BTC's shape, re-derived with an SPX-native trend gate): DEAD, 14/16
  FAIL, 2 INSUFFICIENT-SAMPLE. Extends R77's "the SMC/divergence toolkit
  does not transfer to the index" finding into oscillator-divergence
  territory.
- **RSI(3) dip-buy** (R60 only gridded RSI(2)): **SURVIVOR**,
  cross-instrument-confirmed on the no-stop variant at rsi3<15 (SPY
  28.0x/10.0x thickness, ES 28.1x/7.1x). Answers this program's standing
  question — is the dip-buy edge a broad plateau or a lucky spike on
  RSI(2) specifically — with a clean "plateau": RSI period 2 AND 3 both
  work, same shape, same exit, no re-tuning beyond the period itself.
- **Volume-gated donchian20 breakout** (new axis vs R77's ATR%-percentile
  gates): DEAD. On SPY the gate just shrinks the sample without helping;
  on QQQ it actively kills an already-working edge. Matches the repeated
  "vol/regime gate cuts sample, doesn't add edge" pattern from R77
  family 4b/5b.

## Chance baselines

50/50 long-short for divergence; the already-validated R60 RSI2 baseline
and R48 SPY/QQQ donchian baseline as the direct comparison points for
parts C and A/D respectively.
