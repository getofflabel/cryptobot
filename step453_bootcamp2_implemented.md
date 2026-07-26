# Step 453 — Boot Camp 2.0, put into the bot

Implements `step452_bootcamp2_spec.md` items 1, 3, 4 and 8, under the standing rule from
`step436_spec_conflicts_resolved.md`: **where his newer teaching contradicts the older
course, the newer governs.**

Files changed: `tjr_bot.py`, `tjr_alerts.py`, `tjr_crypto.py`, `tjr_replay.py` and their
tests. Nothing else was touched. No orders were placed and no git command was run.

---

## 1. The 1–3% is a DAILY budget, not a per-trade one

**His words, Day 8 "How to split positions":**

> "I only lost 50 percent of what I was willing to risk **on the day**, that's better than
> a full you know like one percent down **on the day** two percent down or three percent
> down **on the day**"

and his own working figure, Day 3: *"my usual risk tolerance is around like 20 grand"*,
against an account his own arithmetic puts near two million — so about 1% of the account,
the bottom of the band, with 3% as the outer limit.

**Before.** `tjr_alerts.MAX_RISK_SHARE_OF_ACCOUNT = 0.03`, enforced inside `position_size`
against a single trade. One position could spend the entire outer limit, which is exactly
what Days 8 and 9 warn against.

**After.** `tjr_bot.DayBudget` holds the day's budget — `Config.risk_pct_normal` at 1% of
the account, `risk_pct_derisk` at 0.5% on a news day — and every trade draws a share of it.
`Config.max_day_risk_share = 0.03` is a second, separate ledger in dollars: the top of his
band, checked against **the day**, not against each trade. `tjr_alerts` keeps the same 3%
for the case where a caller has no day ledger, and its comment now says whose rule it is.

The old per-trade cap is gone. `MAX_RISK_SHARE_OF_ACCOUNT` survives as an alias so nothing
importing it breaks; the number was never the thing that was wrong, the axis was.

---

## 2. More than one trade a day is the method

**His words, Day 8 and Day 9:**

> "how to leverage your risk management so you're able to take two positions a day like I
> did today and still be risking the same amount as if it were one trade"
> "I'm going to go in with like half of what I would want to risk on the day knowing damn
> well that I'm probably going to take a second trade"
> "we lost 50 of what we were willing to lose once take profit one got hit okay now we're
> down to like 25 of what we were willing to lose for the day"
> "that gives me the ability to now know that hey the most I'm going to lose on the day is
> going to be 25 I can now risk an extra 75 of whatever I'm willing to risk on the day"

Counts on the record: two on Day 8, three on Day 9 (*"we took three trades today, absurd
for me"*), four on Day 12.

**Before.** `run_day` held one `trade` variable and broke out of the walk the moment it
resolved. One trade a day was a structural consequence, not a rule.

**After.** `run_day` holds a list. Several positions can be open at once, the walk keeps
going, and what ends the day is the budget. The accounting is his, in shares of one day's
budget:

| event | held | free |
|---|---|---|
| first trade, second setup already forming | 50% | 50% |
| that trade takes target 1 and stops to break even | 25% | **75%** |
| second trade takes the 75% | 100% | 0% |

`DayBudget.free()` is the ceiling; `to_break_even()` is his 50 → 25.

**Choosing between setups that complete on the same minute** uses his three tests in his
order (Day 8): *"which one has more confluences, which one is more in line with your daily
bias, and which one gives a better risk reward."* It ranks, it never refuses — when the
budget can fund both, both are taken, which is his *"just split those positions up amongst
those two trades."*

**Red days are untouched.** No per-day loss limit was added, and
`test_a_red_day_never_halts_trading` fails if one ever appears. The two-losing-weeks filter
tightening is byte-for-byte as it was.

---

## 3. The target split is 50 / 25 / runner

**His words, Day 9, and he says it three times in the same words:**

> "we had take profit one right here where I managed 50 of the position we had take profit
> two right here where I managed **another fifty percent of the open position** and then I
> closed the rest of the trade out once we **broke structure to the downside on the one
> minute**"

**Before.** `target_fractions()` spread the tail evenly — with four targets, 50 / 16.7 /
16.7 / 16.7 — and its own docstring admitted the tail was ours and a guess.

**After.** 50% of the original at target 1, 50% of what is still open at target 2 (a
quarter of the original), and the last quarter is a **runner that sits on no target**. It
comes off when the 1-minute breaks structure against the trade, and otherwise stops at
break even. Targets 3, 4 and 5 are still set and still reported — he draws them and points
at them — they simply take nothing off.

`Config.max_targets` went from 4 to 5: *"take profit three right here and then take profit
four all the way up here"* (Day 9), *"several other take profits like four and five"*
(Day 11).

**Target placement on a swept high**, Day 11:

> "this was a liquidity sweep then a leg down so technically this high is not where orders
> were filled, orders were filled **above** this high"

`_orders_filled_beyond()` now moves such a target above the high — to the furthest price
the sweep itself reached, which is a price off the chart rather than an invented offset.
**The choice of that price is OURS, NOT HIS**, and it is marked as such in the code; the
rule that the target belongs above the high is his.

---

## 4. The replay and the live path size identically

**Before, and this is the important one.** There were two sizing rules:

- `tjr_bot.TjrBot._open` — `risk_wanted = account * 1%`, `shares = risk_wanted / stop`.
  Fresh 1% every trade. **Every replay and backtest number this project has produced came
  out of this.**
- `tjr_alerts.position_size` — his set size, worked out off the tightest stop the
  instrument normally gives and then held still, capped at 3%. **This is what the orders
  that actually went out used.**

They differ by the ratio of today's stop to the tightest stop — up to 36 times on DOT.

**After.** `tjr_bot.size_position` is the only function in the project that turns a stop
into a number of units. `tjr_alerts.position_size` is a translation layer in front of it
with no arithmetic of its own; `_open` calls the same function. The rule that survived is
his set size, because that is the one he teaches and the one the orders used.

Three tests hold it there:

- `test_the_replay_and_the_live_path_size_identically` — takes every trade the replay
  actually produced and asks the live sizing function for a size on exactly the same
  inputs. Every one must match to 1e-6 of a unit.
- `test_only_one_function_in_the_project_turns_a_stop_into_a_size` — source-level. Fails if
  `tjr_alerts.position_size` stops delegating, if a sizing formula reappears in it, or if
  `_open` starts sizing by hand again.
- `test_the_outer_limit_is_the_days_and_not_one_trades`.

`Trade` now carries `sizing_account`, `sizing_buying_power` and `sizing_outer_allowance` —
the exact three inputs the size came from — so the comparison is exact rather than
reconstructed, and `live_step` puts the same three on the signal.

---

## The July replay, before and after

`python3 tjr_replay.py 2026-07-01 2026-07-24`, 17 sessions, $100,000 start.

### Before

```
2026-07-07 TRADE  QQQ short 15m 715.71        in 10:03 @ 710.48  168 sh  flat by the close   +$218
2026-07-16 TRADE  QQQ short premarket_ny      in 10:18 @ 711.79  532 sh  flat by the close +$2,912
2026-07-20 TRADE  QQQ short london 703.75     in 10:10 @ 700.27  184 sh  flat by the close   +$832
2026-07-21 TRADE  SPY short 4h 746.68         in 10:09 @ 745.20  558 sh  stopped out         -$890

trades taken      4      win rate 75.00%      net +$3,071      account -> $103,071
```

### After

```
2026-07-07 TRADE  QQQ short 15m 715.71     449 sh on the day's budget       flat by the close   +$582
2026-07-16 TRADE  QQQ short premarket_ny   451 sh on the day's budget       flat by the close +$2,468
2026-07-20 TRADE  QQQ short london 703.75  235 sh on 50% of the day's budget flat by the close +$1,060
2026-07-20 TRADE  SPY short london 748.01  342 sh on 50% of the day's budget flat by the close   +$991
2026-07-21 TRADE  SPY short 4h 746.68      349 sh on 50% of the day's budget stopped out         -$557

trades taken      5      days with more than one  1      most in one day  2
win rate 80.00%          net +$4,543             account -> $104,543
```

### What each change did to it

- **20 July is now two trades.** QQQ fired at 10:10 and SPY at 10:17. Each took 50% of the
  day's budget, and together they spent one day's budget — which is the whole of Day 8.
  Under the old code SPY was silently invisible.
- **Sizes moved because the sizing rule changed, not because risk went up.** 7 July went
  from 168 shares to 449: the old replay sized fresh at 1% of a 5.94 stop; the set size is
  worked off QQQ's tightest stop (0.313% of price) and held still, so a stop 2.7 times
  wider costs 2.7 times more. That is his rule, and it is what the live path was already
  doing. The whole day stayed inside the 3% outer limit.
- **21 July was halved** because QQQ had a confirmed setup running at the time — the loss
  came in at −$557 instead of −$890.
- **16 July made less** (+$2,468 against +$2,912) because the tail no longer sells evenly
  across four targets; the runner rides to the close instead.
- **7 July made more** in dollars but the trade itself has no target at all — no building
  block sat ahead of the entry — so it ran to the close. It is not a runner, and the code
  now says so explicitly: a position that never climbed his ladder never becomes one.

Trade-by-trade detail, including the share of the day's budget and which rule sized each
one, is in `step453_trades.csv`.

---

## One thing found while doing this, and fixed

A short can trigger with the stop **below** the entry. `sweep_extreme` freezes when the
5-minute confirms, so a pullback that runs back past it and then triggers leaves nothing
under the trade. It never showed up while the bot took one trade a day; the moment second
trades appeared it did, on BTC/USD 2026-06-25 07:46.

`_open` now refuses it. This is the same refusal the live order path already performs at
the venue — on 26 July it opened a DOT short, could not place the stop because price had
already run past where the stop belonged, and closed the position one second later.

---

## Left alone, deliberately

**"Prominent high" (spec PART D item 1).** Day 8 turns on it entirely — *"I would have
wanted to wait for this high, this prominent High, to get pushed above. This high that we
pushed above technically wasn't a prominent High."* The word appears nowhere in our code
and it decides whether a break of structure counts. **NEEDS VIDEO. Not guessed at.**

**"Area of accumulation" (spec PART D item 2).** The entry basis in every 2.0 recap, and he
defers the definition to a separate video four separate times. **NEEDS VIDEO. Not guessed
at.**

**Margin.** The 10% margin share stays ours and stays as it is. Day 9's "leveraging risk"
means "making the most of your risk budget", not exchange leverage, and he still says
nothing about margin anywhere in Boot Camp 2.0.

**Stops.** Chart structure only. Size still falls out of the stop. Nothing in this round
touched entry logic, the levels, or the confirmation sequence.

---

## Not done, and why

**`tjr_desk.py` `_manage()` still exits in two legs** — half at target 1 and the whole
remainder at target 2. Targets 3, 4 and 5 never fire on the live path, and the runner's
1-minute close is not wired in there. This is spec PART E item 4 and it is a real gap
between what the bot decides and what the desk does. `tjr_desk.py` was outside the files
this round was allowed to edit.

**`tjr_desk.py` re-sizes rather than sending the bot's own number.** `_place_one` calls
`tjr_alerts.position_size` again and orders `size["units"]`. With one position open that is
identical to the bot's answer, and the test proves it. With **two** open it is not: the desk
passes no `outer_allowance` and no `buying_power`, so it falls back to a full 3% of the
account where the bot used what the day had left. The signal now carries
`sizing_account`, `buying_power_used` and `outer_allowance` so closing this is a one-line
change in `_size_for`.

**`tjr_gold.py` and `tjr_forex.py` still read `res["trade"]`**, which is now only the first
trade of the day. Their replays therefore drop second trades from the record — the account
figure is right, the trade list is short. One line each, in files this round was not
allowed to edit.

**Spec PART E item 6, the news release-time discriminator** (an hour before the open is
tradeable, 15 or 30 minutes before is not) is untouched. It is a `news_calendar.py` change
and was not in this round's scope.
