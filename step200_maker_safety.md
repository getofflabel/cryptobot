# step200 — is a MAKER (post-only limit) entry safe on this system today?

Evidence only. The OWNER'S LAW (market orders only, `step5_paper_trade.py`
`execute_market_clips`) is unchanged. No execution code was modified.

## Bottom line

**DO NOT RECOMMEND switching entries to maker yet — not because the maker
edge is fake, but because live-testing tonight found a live, reproducible
bug in the existing `execute_maker_or_chase` polling logic that the
question never anticipated: it cannot tell a post-only order that was
CANCELLED by the exchange apart from one that FILLED, and will silently
book a trade that never happened.** That bug is orthogonal to "resting
orders vs deploys" — it would misfire even on a system with zero deploys
and zero crashes. Fix it first; then the deploy/crash question below is
the one that actually gates a maker rollout.

Separately, and this DOES matter for the "is it worth it" case: the
2026-07-23 and 2026-07-24 incidents that produced the OWNER'S LAW were
root-caused to book misattribution and clip-loop rate-limiting, both of
which now have real fixes (`book_ledger.py`, atomic single-order
`execute_market_clips`). Neither of those specific fixes covers `THE RIDE`
today, because **`THE RIDE` (`step5_paper_trade.py::decide_and_trade`)
never migrated off `execute_maker_or_chase` — it is the one book still
resting orders and still clip-splitting at >5 ct, live, right now.**

## 1. What `execute_maker_or_chase` actually is, and what's still calling it

`step5_paper_trade.py` defines two live-order paths:

- `execute_market_clips` (line 541) — the OWNER'S LAW path. ONE atomic
  market order, 3 retries, never rests. Used for **entries** by
  `breakout_book.py`, `diver.py`, `daily_pick.py`, `tactical.py`,
  `newsdesk.py`, `shorts_lab.py`.
- `execute_maker_or_chase` (line 599) — the pre-OWNER'S-LAW path. Posts a
  post-only limit, polls every `MAKER_POLL_S=20s` for up to
  `MAKER_PATIENCE_S=600s` (10 minutes), then cancels and chases at market.
  Orders above `MAX_CLIP=5.0` contracts are **split into 5-ct clips**, each
  going through the same maker-then-chase cycle — this is the identical
  clip shape that caused the 2026-07-24 "XAUT orphan" (see §2).

`tactical.py` and `newsdesk.py` **import** `execute_maker_or_chase` but, per
grep, only ever call `execute_market_clips` — the import looks like a dead
leftover, not a live call site.

**`step5_paper_trade.py::decide_and_trade` (THE RIDE) is different: it
calls `execute_maker_or_chase` directly, for both entry (line 870) and exit
(line 836), with no comment anywhere explaining why the RIDE was exempted
from the OWNER'S LAW.** Real trade evidence from `trades_log.jsonl` shows
RIDE entries at 13.7 contracts — well above `MAX_CLIP + LOT/2 = 5.05` — so
the 5-ct clip-splitting loop is not a theoretical edge case for the RIDE,
it is the normal path for a normal-sized trade.

## 2. The two incidents, disambiguated (per `RESEARCH_LOG.md`, `book_ledger.py`,
   `step5_paper_trade.py` docstrings, and `trades_log.jsonl`)

**2026-07-23, book misattribution** (`book_ledger.py` module docstring,
`trades_log.jsonl` `"manual_flat"` @ 20:20:44 UTC — *"multi-book conflict —
flattened to safe, halting until netting fix deployed"*): the RIDE read the
RAW exchange net position instead of its own attributed slice, saw the
Shorts Lab's -69.6ct short as "a position I don't want," and kept BUYING it
back in `execute_maker_or_chase`'s clip loop, fighting another book's
position. Its exit path also blanket-cancelled every TP/SL bracket on the
symbol, stripping the lab's protective stop.
**Root cause: misattribution, not the resting-order mechanism itself.**
**Fixed by:** `book_ledger.py` (`attributed_position`,
`unexplained_position`) — verified live tonight (§4) that a resting order
on a symbol nothing tracks does NOT get misread as a position by this
mechanism.

**2026-07-24, deploy-interrupted clip loop** (`trades_log.jsonl`
`"manual_cleanup"` @ 02:12:00 UTC — *"orphaned partial entry from
deploy-interrupted clip loop — flattened, orders cancelled, pending
cleared"*; `step5_paper_trade.py` §"2026-07-24 REWRITE" — the XAUT orphan,
361ct became 73 rapid clips, tripped the demo host's rate limiter, left a
naked partial): **root cause was CLIP COUNT / rate-limiting, empirically
confirmed** — the owner's own diagnosis notes the identical 361ct sells
fine as ONE order, and BloFin's real `maxMarketSize` (6k-150k) made the
5-ct clipping "inherited superstition," not a real constraint.
**Fixed by:** `execute_market_clips` — ONE atomic order + 3 retries — but
**only for the books that were migrated to it.** The RIDE's
`execute_maker_or_chase` still contains the exact clip-splitting shape
(`MAX_CLIP=5.0`) that produced this incident, live, today.

**So, answering the question directly asked**: the orphan risk that drove
the OWNER'S LAW was caused by clipping, and clipping IS fixed — for every
book except the RIDE. The orphan risk is not inherent to a single,
unclipped resting order in the way the two recorded incidents played out.
But a single resting order carries a different, smaller, still-real risk
that neither incident tested and nothing in the codebase currently guards
(§3, §4): a resting order that outlives the process that placed it.

## 3. Failure-mode table

| Failure mode | Covered today? | Mechanism / gap |
|---|---|---|
| Worker crash mid-clip-loop (>5ct order, ANY book) | **Fixed** for market-clip books (`execute_market_clips`: 1 order, 3 retries, atomic) | **NOT fixed for THE RIDE** — still clip-splits via `execute_maker_or_chase`, the same shape that caused the 2026-07-24 XAUT orphan |
| Render redeploy mid-cycle (hourly GH Actions journal commit → auto-deploy, confirmed in `.github/workflows/hourly.yml`: `git push` after every `hourly.py` run, `cron: "7 * * * *"`) | **Partially** — `daemon.py` runs `full_cycle(..., "startup")` on every restart, and every book re-reads `net_position_contracts()` fresh (exchange as truth) | Reconciliation only covers **positions**, never **pending orders**. Nothing in any book calls `private.pending_orders()` at startup. A resting order surviving a redeploy is invisible until it fills or someone finds it by hand. |
| Partial fill across clips | **Fixed** for market-clip books (single atomic order = no partial possible) | **NOT fixed for the RIDE's clip loop** (same as row 1) |
| No fill at all (limit sits, market never returns) | **Partially modeled** — `_execute_single`'s patience-timeout branch correctly falls through to a taker chase after 600s IF the order is still genuinely pending | **Not covered**: if the order left the book EARLY for a reason other than a fill (see next row), the code never reaches the chase branch at all |
| **Fill arriving after we stopped watching / order cancelled by the exchange, not filled** | **NOT covered — live bug, reproduced tonight** | `_execute_single`'s poll loop (`step5_paper_trade.py` ~659-669) treats "no longer in `pending_orders()`" as proof of a fill: `if not still_pending: ... return price, True`. It never checks the order's actual terminal `state`. A `cancel_by_post_only_depth` cancellation (BloFin cancelling a post-only order it decided would cross, or would sit too close to the touch — see §4) also removes the order from `pending_orders()` with zero fill. `private.fills()` then returns `[]`, so the code falls back to `price = limit_price` and reports **`was_maker=True` for a trade that never happened.** State, ledger, and `notify()` would all be told a fill occurred at a fictional price while the exchange position never moved. |
| Rate limiting (many rapid API calls) | **Fixed** for market-clip books; **live risk for the RIDE** (5-ct clip loop, same shape as the incident) | See rows 1/3 |
| `book_ledger` mistaking a resting order for a position | **Confirmed fixed, live** (§4 test) | `net_position_contracts()` and `unexplained_position()` both read 0 while an order merely rests — verified empirically tonight on XRP-USDT |
| A crashed/redeployed process losing track of state | **Mostly covered** — `save_state`'s books-only fallback (2026-07-25, `step5_paper_trade.py` ~267) keeps position records saving even when the 170KB display blob fails; `load_state` prefers cloud state so a Render restart doesn't lose the ledger | Covers **known** positions. Does not cover an order the crashed process placed but never recorded reaching a terminal state (same gap as row 2/5) |

## 4. Live test results (BloFin demo — `demo-trading-openapi.blofin.com`, paper account)

Symbol: **XRP-USDT** — confirmed via grep that no live book's `UNIVERSE`
includes it (BTC/ETH/SOL/XAUT only across `daily_pick`, `gold_book`,
`diver`, `newsdesk`, `shorts_lab`, `tactical`, `breakout_book`,
`core_ride`), so nothing here could collide with a real position. Size:
0.1 contracts (the venue minimum, ≈ $11 notional). Scripts:
`step200_live_test.py`, plus three ad-hoc follow-up probes run inline.

**Drills 1-3 (resting order, ledger safety, cancel) — PASSED:**
1. Posted a post-only BUY 15% below the bid (guaranteed to rest, not
   fill). Confirmed present in `orders-pending` with our exact
   `clientOrderId` (`CBOT_step200_...`).
2. **Confirmed `net_position_contracts()` and
   `unexplained_position()` both read `0` while the order rested.**
   book_ledger cannot mistake a resting, unfilled order for a position —
   this mechanism is sound.
3. Cancelled it; confirmed gone from `orders-pending` on the next poll.

**Drill 4 (maker fill at the touch) — did NOT get a genuine fill in this
session, and the attempt uncovered the bug in §3:**
- First naive attempt (join best bid, treat "left `pending_orders`" as
  "filled"): appeared to "fill" after 10s. Checking `orders_history`
  afterward showed the true `state` was `canceled`,
  `cancelSource: cancel_by_post_only_depth`, `cancelSourceReason: "The
  post-only order will take liquidity in taker orders"` — **zero fill,
  zero fee, but the naive check would have called this a maker fill.**
  This is exactly the bug in §3.
- Rewrote the check to confirm terminal state via `orders_history` (not
  just absence from `pending_orders`) and retried at a fresh touch price,
  6 times over ~3 minutes: **all 6 were also `cancel_by_post_only_depth`.**
- Follow-up probes, each checked against `orders_history`: 1 tick behind
  the touch → cancelled the same way in 5s. 0.3% behind the touch →
  cancelled the same way in 5s. 3% behind the touch → **also**
  cancelled the same way.
- **No fee/bps reading was obtainable** in this session — every post-only
  attempt on XRP-USDT tonight was cancelled by the exchange before it
  could fill, regardless of how far from the touch it was quoted. This
  looks like a demo-venue liquidity/protection quirk specific to a
  thinly-traded pair (XRP-USDT's `instruments` spec lists
  `thresholdX/Y/Z: 0.02/0.02/0.05`, plausibly a protection band unrelated
  to genuine order-book crossing) rather than a property of the maker
  mechanism in general — but it is exactly the kind of exchange behavior
  the current polling code has no way to tell apart from "filled."
- **Corroborating evidence from the account's own real BTC-USDT order
  history** (`orders_history('BTC-USDT', limit=100)`): of 43 post-only
  orders in the visible window, **36 (84%) were cancelled by
  `cancel_by_post_only_depth`**, 7 (16%) genuinely filled, and the
  remainder were user-cancelled limits. These specific 100 orders carry no
  `clientOrderId` (all predate `TAGGING_CUTOVER_UTC`, 2026-07-25 06:25
  UTC), so they are almost certainly earlier `exec_test.py`-style drill
  runs, not confirmed live RIDE trades — I could not find a tagged
  (post-cutover) post-only order in the most recent 100 to check whether
  THE RIDE itself has already hit this. That is an open question, not a
  ruled-out one.
- Drill 5 (close position, confirm flat): nothing to close — account
  confirmed flat and orders-clean on both XRP-USDT and (untouched)
  BTC-USDT at the end of this session.

**Fee numbers**: none obtained live tonight (every attempt was cancelled,
not filled). The known reference numbers from the task brief stand
un-contradicted by anything observed: taker 6bps/leg, maker 2bps/leg is
BloFin's published schedule (`config.py` fee constants), and historical
`order_fee()` reads on filled market orders tonight confirmed taker fees
computing to ~6bps on XRP-USDT test fills from earlier in the day (fee
0.0065424 on ~$10.90 notional = 6.0bps), consistent with the schedule.

## 5. Fill/miss rate

**Backtest-model measurement** (`step200_fill_rate.py`, reusing
`backtest.py`'s exact "touched" test verbatim — `limit = closes[i-1]`,
`touched = lows[i] <= limit` (buy) or `highs[i] >= limit` (sell) — over
the full cached history):

| Timeframe | Bars | Whole-next-bar fill rate |
|---|---|---|
| 4h (THE RIDE), 2020-03 → 2026-07 | 13,862 | **100.0%** both directions |
| 1h (breakout/tactical/daily_pick/newsdesk/diver), 2020-03 → 2026-07 | 55,492 | **100.0%** both directions |

This is not a bug in the measurement — it reflects that `closes[i-1]`
(the signal bar's close) is essentially identical to bar `i`'s open in a
continuous 24/7 perp market, so the very next bar's range trivially spans
it almost every time. **This means the backtest's maker execution
assumption (round 87's `execution="maker"` result) is not an artifact of
an optimistic fill model — historically, on this exact "limit at the
signal close" recipe, misses are close to zero over a full bar's window.**

**The caveat that matters live**: `backtest.py`'s model gives the resting
limit the WHOLE next bar (1h or 4h) to be touched. Live,
`MAKER_PATIENCE_S=600` gives it only **10 minutes** — 16.7% of a 1h bar,
4.2% of a 4h bar. A naive linear downscale would put the live fill rate
far lower than 100%, but that downscale is almost certainly too
pessimistic in the other direction: price typically revisits its own
bar's open (= the resting limit) within seconds to low minutes, not
uniformly across the bar, because the new bar's open trades right at that
level to begin with. **Neither bound is a real live-fill-rate number.**
The only real measurement available is the live test in §4, and what it
showed was not "misses because price ran away" — it was "the exchange
cancels the order before the patience window even starts to matter,"
which is a different failure mode than the one the backtest models or the
question assumed. That mechanism cannot currently be distinguished from a
fill by the code (§3), so today, the honest answer to "how often does it
fill vs need a taker chase" is: **the code cannot currently tell you,
because a cancelled-not-filled order is misreported as a filled one.**

## 6. Recommendation

**DO NOT RECOMMEND flipping any book to maker execution yet.** Not because
the maker edge is illusory — §5's whole-bar fill rate and the historical
2bps/6bps gap both support the edge being real and largely realizable —
but because two concrete, evidenced gaps sit between here and safe:

1. **Fix the fill-detection bug first** (`_execute_single`,
   `step5_paper_trade.py` ~659-669): it must check the order's actual
   terminal `state` (via `orders_history` or equivalent), not merely
   absence from `pending_orders()`, before reporting `was_maker=True`.
   Tonight's live test reproduced this exact false-positive 8/8 times on
   XRP-USDT and found the historical BTC-USDT order record is 84%
   `cancel_by_post_only_depth` among the visible (untagged, pre-cutover)
   sample. This bug exists in code that is LIVE TODAY for THE RIDE — it
   is not a hypothetical of a future maker rollout.
2. **Migrate THE RIDE off `execute_maker_or_chase`'s clip loop**, or
   explicitly decide (with a written reason, unlike today) that it stays
   exempt from the OWNER'S LAW. As-is, it is the one live path still
   splitting >5ct orders into clips — the identical shape that produced
   the 2026-07-24 XAUT orphan — with no comment anywhere explaining why
   it wasn't migrated alongside every other book.
3. **Add a pending-order sweep to startup reconciliation.** Every book
   already re-reads `net_position_contracts()` on every cycle/restart
   (exchange as truth for positions) — none of them call
   `private.pending_orders()` to catch an order that outlived the process
   that placed it. This is the one deploy/crash risk that is real and
   still open even after fixing #1 and #2: a post-only order resting when
   a redeploy or crash hits (a real, roughly-hourly event per the GitHub
   Actions journal-commit cron) is currently invisible until it either
   fills unattended or is found by hand.

With those three in place, the evidence here (book_ledger correctly
ignores resting orders; clip-loop orphaning is understood and fixable the
same way it already was for every other book; the fill-rate math favors
maker heavily on a whole-bar basis) supports revisiting maker execution.
Without them, a maker order today risks a silently fictional fill being
booked against a real account — a worse failure than the taker-fee cost
this whole investigation started from.
