# PINNED FENCES — every published sealed-slice boundary, as a DATE

**Committed 2026-09-18 by R505 (queue item 40). Read this before any `fetch`.**

## Why this file exists

`step489.cut80` computes a fence as `t0 + (t1 − t0) × 0.80` **off whatever span
the file has at the moment it runs**. Every sealed-slice boundary this log has
published sits on that formula, so every boundary was a FUNCTION OF THE FILE
and not a date. R504 priced the exposure: appending the real bars that already
exist past the corpus boundary moves **every fence on the disk by 0.8 of a day
per day appended** — six weeks of R492's LINK SEALED region becomes readable
again, and six weeks of what R492 READ as XRP's train/val becomes part of
XRP's "sealed" slice.

The dates below are pinned. `step505_pinned_fences.fenced_at(sym)` returns
them without touching the file, and falls back to `cut80` only for
instruments no round has ever fenced. **`cut80` itself is unedited** — the pin
wraps it.

## How to use it

```python
from step505_pinned_fences import fenced_at, fenced_window, fenced_frame
t80          = fenced_at("XRPUSD")        # the pinned date, file never read
t80, t0, t1  = fenced_window("XRPUSD")    # step489.cut80's own signature
f, t0, t1    = fenced_frame("XRPUSD")     # R501's fenced(), through the pin
```

A round that wants a **new** boundary on a pinned instrument does not edit this
file quietly: it says so in RESEARCH_LOG.md, states which published slice it
moves, and adds a row rather than overwriting one.

## The pin — 17 instruments

| instrument | fence (pinned, full precision) | file window | file bars | published by | what it locks |
|---|---|---|---|---|---|
| BTC | `2025-06-15 06:33:36` | 2021-01-01 → 2026-07-26 | 2,597,036 | R489 (2026-09-01) | POOLED CALENDAR. R502/R503/R504 measure A1 against BTC's fenced window; moving it moves every era factor. Also the crypto arm's own 80% boundary. |
| ETH | `2025-06-15 06:35:12` | 2021-01-01 → 2026-07-26 | 2,538,368 | R489 (2026-09-01) | ranking row; sealed slice SPENT by R475. |
| SOL | `2025-06-15 06:35:36` | 2021-01-01 → 2026-07-26 | 1,955,709 | R489 (2026-09-01) | ranking row, contested top three (R503); sealed slice SPENT by R475. |
| LINK | `2025-06-15 06:42:24` | 2021-01-01 → 2026-07-26 | 2,325,622 | R489 (2026-09-01) | **R492 SPENT the slice that starts here** (2025-06-15 -> 2026-07-26, 406d). Moving this boundary un-spends six weeks of a spent slice. |
| LTC | `2025-06-15 06:46:24` | 2021-01-01 → 2026-07-26 | 2,110,763 | R489 (2026-09-01) | ranking row (7th, stable since R500). |
| XRP | `2026-01-20 06:38:24` | 2024-01-01 → 2026-07-26 | 770,145 | R489 (2026-09-01) | **R492 published 2026-01-20 -> 2026-07-26 as INTACT and never read it.** This is the family's last clean window on an instrument with real history. Moving it forward pre-contaminates the slice with six weeks R492 already READ. |
| ADA | `2026-06-24 07:11:36` | 2026-02-13 → 2026-07-26 | 168,115 | R489 (2026-09-01) | ranking row, unplaced by R503; INTACT. |
| DOT | `2025-12-24 07:23:48` | 2023-08-18 → 2026-07-26 | 1,256,982 | R494 (2026-09-06) | ranking row, unplaced by R503; INTACT. R489's pre-backfill fence (2026-06-26) is superseded. |
| PAXG | `2025-06-15 11:06:00` | 2021-01-01 → 2026-07-26 | 311,292 | R494 (2026-09-06) | ranking row, contested top three (R503); INTACT and unread. R489's pre-backfill fence (2026-06-26) is superseded. |
| AVAX | `2025-08-18 16:58:24` | 2021-11-18 → 2026-07-26 | 1,980,264 | R494 (2026-09-06) | ranking row, unplaced by R503; INTACT. Data-absent in R489 (3 days of tape). |
| DOGE | `2025-06-15 10:46:36` | 2021-01-01 → 2026-07-26 | 2,373,535 | R494 (2026-09-06) | ranking row (5th, stable since R500); INTACT. Data-absent in R489 (3 days of tape). |
| SPY | `2024-06-13 09:35:24` | 2016-01-01 → 2026-07-24 | 2,114,524 | R474 (2026-07-27) | **R474 SPENT the slice that starts here** (2024-06 -> 2026-07, 371 trades / 155 days) and that cell is the one AWAITING DEPLOYMENT REVIEW. |
| QQQ | `2024-06-13 09:35:12` | 2016-01-01 → 2026-07-24 | 2,036,866 | R474 (2026-07-27) | same spent slice as SPY (R474). |
| GLD | `2026-06-25 21:34:24` | 2026-03-02 → 2026-07-24 | 76,899 | R489 (2026-09-01) | R489(a2) vol% row; 81 days, queue item 35. |
| IAU | `2026-06-25 21:35:12` | 2026-03-02 → 2026-07-24 | 55,190 | R489 (2026-09-01) | R489(a2) vol% row; 81 days, queue item 35. |
| GBPUSD | `2026-06-14 17:23:12` | 2026-01-05 → 2026-07-24 | 206,225 | R489 (2026-09-01) | R489(a2) vol% row. |
| GBPJPY | `2026-06-14 17:23:12` | 2026-01-05 → 2026-07-24 | 206,346 | R489 (2026-09-01) | R489(a2) vol% row. |

## The arm clocks — the OTHER two call sites of the same formula

`cut80` is not alone. `step450.main` (crypto) and `step474.main` (index)
compute `t0 + span × 0.60` and `× 0.80` on a **shared clock** — one
instrument's 5-minute-and-1-minute overlap — and apply those timestamps to
every asset in the arm. **Those two cut the SPENT slices**, so pinning `cut80`
alone would have left R474's and R475's spent windows exposed.

| arm | clock | t0 | t_tr (60%) | t_va (80%) | published by | recomputable today | what it locks |
|---|---|---|---|---|---|---|---|
| `crypto_1m_R476` | BTCUSD 5m and 1m overlap | 2021-01-01 06:00:00 | 2024-05-04 18:24:00 | 2025-06-15 06:32:00 | R476 (2026-08-01) | yes | the backfilled crypto window. R492's LINK table cut its choosing/middle/final on exactly these dates. |
| `crypto_1m_R450` | BTCUSD 5m and 1m overlap, 147-day file | 2026-03-01 | 2026-05-28 08:27 | 2026-06-26 19:16 | R450 (2026-07-23) | **NO** | **R475 SPENT 2026-06-27 -> 2026-07-26 on this clock.** The file it was computed on has since grown from 147 days to 2,032, so this window CANNOT be recomputed today - it is pinned from step450_output.txt and from nothing else. |
| `index_1m_R474` | SPY 5m and 1m overlap | 2016-01-01 00:01:00 | 2022-05-03 19:09:24 | 2024-06-13 09:32:12 | R474 (2026-07-27) | yes | **R474 SPENT everything after t_va** on SPY and QQQ. The surviving cell is the one AWAITING DEPLOYMENT REVIEW. |

`crypto_1m_R450` is **not recomputable** — the 147-day file it was cut on has
since grown to 2,032 days. **That is the defect, already realised**, on the
clock that cut R475's spent slice. It is pinned from `step450_output.txt` and
from nothing else.

## What R505 verified before committing this

- Every pinned date equals `S.cut80` on today's file **to the second**; zero
  drift on 17 of 17, zero bar-count mismatches.
- The fenced FRAME is byte-identical through the pin and through `cut80` —
  same bar counts and same SHA-256 fingerprint on 17 of 17.
- R499's `vol%` column recomputed behind the pinned fence: max absolute
  difference **0.0000 pp**. R501's `xSAME` column, R501's own functions:
  **0.000x**. R502/R503 take their inputs from these exact frames, so the
  published ordering is unchanged by construction.
- Both recomputable arm clocks reproduce their pinned `t_tr` and `t_va`
  exactly.

Full output: `step505_output.txt`.
