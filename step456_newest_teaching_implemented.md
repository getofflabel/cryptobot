# Step 456 — the three things his newest videos say he uses, built and switchable

Implements the three priority items from `step454_newest_corpus_delta.md`, under the
standing rule from `step436_spec_conflicts_resolved.md`: **where his newer teaching
contradicts the older, the newer governs.** The playlist is in chronological order and
step454 proves it, so a higher file number is newer teaching.

Files changed: `tjr_bot.py`, `tjr_crypto.py`, `test_tjr_bot.py`, `test_tjr_crypto.py`.
New: `step456_baseline.py`, `step456_baseline.json`, `step456_before_after.py`, this file.
Nothing else was touched. **No orders were placed, no git command was run, and
`daemon.py`, `venue.py` and `tjr_desk.py` were not opened.**

---

## 0. The shape of it: one binary, two halves

Wallace asked for "a before and after of that playlist ran on the past year". So every
rule below is a **named switch on `Config`, and every one of them ships OFF**. With all of
them off `tjr_bot.py` decides exactly what it decided on 2026-07-26 — trade for trade,
field for field. `Config.newest_teaching()` turns the lot on in one call.

```python
Config()                      # BEFORE — his older teaching, what we shipped yesterday
Config.newest_teaching()      # AFTER  — the three things below, all on
```

**Nothing else moves between the two halves.** The levels, the stops, the sizing, the day
budget, the target ladder and the both-indexes-agree veto are byte-for-byte what step453
left. `test_every_step456_switch_ships_off` fails if `newest_teaching()` ever changes one
of them.

---

## 1. SMT DIVERGENCE — it did not exist in the codebase at all

`step436` item 12 listed *"Divergence between correlated markets — dropped from the
current strategy"*. That is wrong. **115** is the fifth-newest video in the corpus,
titled "$1,000,000+ From One Simple Confluence", and opens:

> "This is going to be the only SMT divergence video that you guys will ever need. This
> has been one of the key confluences to help me make seven figures over the past couple
> years trading."

### 1.1 What it is NOT — and this decided the whole shape of the build

**120**, coaching, and the switches are laid out to honour this sentence literally:

> "SMT divergence just strengthens our bias... me personally I use it to determine what
> index I should take the trade off of... **It doesn't tell me to take a trade. It doesn't
> tell me to execute. It just helps strengthen my bias.**"

So SMT has three jobs and each one is its own switch, because they are three different
claims and they should be measurable apart.

| Switch | Job | Whose words |
|---|---|---|
| `smt_enabled` | compute it; it counts as one more confluence and nothing else | 120: *"just strengthens our bias"* |
| `smt_picks_the_instrument` | it chooses WHICH of the two charts gets the order | 120: *"I use it to determine what index I should take the trade off of"* |
| `smt_in_confirmation_menu` | it is one of 112's four interchangeable confluences | 112, 103 — see section 3 |

The first two are section 1's mandate: **a bias input and an instrument chooser, never an
entry trigger.** The third belongs to section 3 and is switched separately precisely so
"bias input" and "menu option" never get conflated in a result.

### 1.2 Which two instruments

Exactly two positively correlated ones, and he names them and rejects the alternatives
himself. **115:**

> "we are using the S&P 500 and the NASDAQ. And this is when we choose two positively
> correlated assets... I know that some people use EuroUSD and GBPUSD. I know sometimes
> people use gold and silver. **I haven't seen as much correlation between those commodity
> and those currency pairs** than I've seen when using indexes."

And flatly, in the five-hour beginner guide (**068**):

> "if you guys are trading **anything besides the S&P 500 in NASDAQ this is not going to
> apply to you**... this only applies to indexes."

On crypto specifically, **044**:

> "crypto sometimes you can use this with BTC and eth but **I wouldn't necessarily
> recommend it**... I haven't back tested it as much as I have with these indexes."

**In code:** `TjrBot._smt` returns None unless it is handed exactly two symbols. Crypto's
`run_pair` hands `run_day` one pair, so a divergence **cannot form there at all** — it is
structural, not a switch. `crypto_config` also pins all four SMT switches False with the
quotes above, so nobody can turn it on from somewhere else.
(`test_a_divergence_is_structurally_impossible_on_a_crypto_run`.)

### 1.3 Which timeframe

Both the working chart and the trigger chart, and he names each.

- **5-minute**, 044: *"I prefer to keep it on the 5 minute for entry"*, and 112 lists
  *"a 5minute SMT divergence"* on the confirmation menu.
- **1-minute**, 112: the 1-minute stage uses *"the same exact confirmation confluence"*,
  and 103 takes an entry off one — quoted in full in section 3.
- 096 gives his preference order and it is a caution rather than a ban: *"I do not like to
  use SMT divergence on the one minute. Typically my SMT divergence is going to be on the
  5m minute or the 15minute."* **Newer governs**: 112 and 103 put it on the 1-minute, so it
  is on both charts and each is switched by the same flag.

**In code:** `smt5` and `smt1`, computed on `Instrument.working_minutes` and
`Instrument.trigger_minutes`. The 15-minute is not computed — nothing in our sequence reads
a 15-minute confluence, so it would have nowhere to go.

### 1.4 What counts as a divergence

**115**, the definition, both sides:

> "**a bearish SMT divergence is formed when we are in an uptrend and one index forms a
> high then a lower high. Okay, and the other index forms a high then a higher high.**"
> "It's when one index makes a low, then a lower low, and the other index makes a low, then
> a higher low."
> "it's just comparing and contrasting highs and lows between these two indexes."

One side at a time, from the nine-hour guide (**096**):

> "**When we're looking for bullish SMT, we're only using the lows. And when we're looking
> for bearish SMT, we're only looking for highs.**"

The two swing points have to be simultaneous, and he says it twice —
`SMT_Divergence_Explained`:

> "**this high was formed at the same time that this one was, but then this one forms a
> higher high at the same time that this lower high was getting formed.**"

and with the clock on screen (**068**):

> "it's literally happening at the exact same time **935 935** — the S&P 500 makes a lower
> high while NASDAQ is making a higher high"

**In code:** `SwingLog` keeps each chart's last 40 two-candle swings with the time each was
stamped; `smt_between` compares the newest two on the side being tested and requires both
pairs to line up in time.

- `smt_alignment_bars: int = 2` — **OURS, NOT HIS, and a guess.** He times them to the same
  bar. Our two-candle swing is stamped on the SECOND candle of its pair, so one doji on one
  chart and not the other moves the stamp by a bar; two bars absorbs that at both ends. Set
  it to 0 for his literal words.

### 1.5 Two gates that stop it firing everywhere

**It has to sit on a sweep.** `SMT_Divergence_Explained`:

> "It's specifically going to be useful when we are actively sweeping out draws and
> liquidity... **outside of sweeping out draws and liquidity, these things will show up all
> the time and will be pretty much like useless to us.**"

**It has to agree with the day's bias.** **044**:

> "let's say our daily bias is bullish but we see a bearish smt Divergence **are we going to
> want to take that? No** because our overall bias is bullish"

**In code:** `SymbolDay.smt_live()`. Three conditions — the divergence points the way the
daily bias points, the sequence has actually registered a sweep, and the divergence formed
no earlier than that sweep. It is the only place any switch consults a divergence.

### 1.6 Which instrument gets the order — and the mechanical test step454 wanted

step454 filed *"NEEDS VIDEO for the mechanical test of 'leading'"*. **It is stated, and
mechanically.** 115:

> "**Why is this index the leading index? Because this index is telling us the future of
> what this index is eventually going to do... This is the lagging index because it's
> continuing the current trend that it was in.**"

`SMT_Divergence_Explained` puts the same thing in terms of the swing itself:

> "it's the leading index in the downward move **because it's making a lower high**... Why
> is it lagging? **because it's continuing the uptrend** while ES is forming a new downtrend."

**So: leading = the chart whose second swing BROKE the trend. Lagging = the one that
carried it on.** That is the same comparison the divergence already is, so it costs nothing
and it is not a judgement call.

He dates his own reversal, **100**:

> "That's why we always take the **leading** index. **Before I used to take the lagging
> index, but I changed that around** like when was that like two and a half to three months
> ago."

Live, **112**: *"we don't want to be trading on NASDAQ because NASDAQ is the lagging
index."* Coaching, **120**: *"I would much rather you take the trade on ES just because it's
the more bearish index. This is the leading index on the bearish side."* And **103** is the
counter-example he names as the error: *"we kind of should have taken the trade on ES. I
was just panicking a little bit because price started moving so fast."*

**In code:** `SymbolDay.smt_forbids_this_chart()`, applied at the entry gate.
**It can only ever refuse.** It never opens a position and never changes a size.

### 1.7 The index-agreement veto SURVIVES, and the lagging chart is still watched

step454 checked this specifically and it survives, so nothing was removed. The two tests
measure different things: **the agreement gate is about the two charts' 5-minute TREND
STATE; a divergence is about a single swing point taken on one chart and not the other.**
120, in the same coaching session that explains SMT: *"we want both to be confirmed."*

And the lagging chart is not ignored, it is simply not traded — **101**:

> "I'm mainly looking at the S&P 500 for my entry on Nasdaq... **I wasn't willing to take the
> trade entry because ES was still down here and didn't give us confirmation to the upside
> yet.**"

That watching *is* `enforce_index_agreement`. It stays True in both halves.
(`test_the_index_agreement_veto_survives_smt`.)

### 1.8 The completion rule — computed, recorded, and deliberately not traded on

**115:**

> "**We look for the lows that are attached to the highs that are formed on the SMT
> divergence. And in order for the SMT divergence to be completed, we need to take out the
> lows that are attached to the highs.**"
> "this high has already been taken out. So it would be this high right here."

`SwingLog.completion_target()` computes it, including his step-back past a draw already
taken out, and it lands on the trade record as `smt_completion`. **It is NOT fed to
`build_targets`.** The exit ladder was rebuilt in step453 and this round does not touch it.
`test_a_divergence_never_reaches_a_size_a_stop_or_a_target` reads the source of
`size_position`, `build_targets`, `building_blocks`, `target_fractions`, `manage_step` and
`_manage` and fails if any of them ever learns the word.

---

## 2. THE 79% EXTENSION — never dropped, and the anchor question is answered

`step436` item 12 also listed *"The 79% extension — dropped"*. It appears in fourteen files
from 066 through 112. It is in **112's current cheat sheet**, it is in **099's** confirmation
list, and in **106** its ABSENCE is the stated reason he took no trade:

> "we need this to close underneath the 79% extension or else we're going to have to wait
> another freaking five minutes... **we didn't close underneath the 79% extension.** It's
> already 10. I don't know, bros... **I think that I'm just going to call it here.**"

**Switch: `extension_79_enabled`.** Number: `extension_79_ratio = 0.79`, **HIS**, and there
is only ever one of it — 78.6, 70.5, 61.8 and 0.79 were all searched for across the whole
transcript tree including `bootcamp/` and `bootcamp2/`, and none occurs.

### 2.1 Which two points

**099**, bearish:

> "we take it from the **low up to the high** and we just wait for a candlestick closure
> **underneath** the 79% extension"

and bullish, same video:

> "**Take it from this high down to this low.** Did we close **above** the 79% extension?"

### 2.2 Whether it sits inside the leg or beyond it — the one thing he never says in words

He demonstrates it on screen and never describes where it sits. Four things settle it, and
the first is decisive because it names a level we already compute.

**It is the same tool, the same anchors, the same drawing as equilibrium**, and equilibrium
is unambiguously the midpoint of the leg. **082:**

> "this is the 79% extension disrespection. So you pretty much draw it just like a regular
> Fibonacci. So you take it from the high down to the low **as if you guys are drawing a
> equilibrium**."

**066:** *"all we do is we draw it out **just like we were to draw out equilibrium**."*

Three more, all consistent: he calls the triggering candle *"such a **deep** close"* (099);
with price near the top of an up-leg the level is far away, *"Still **pretty far from** the
79% extension. I think we can move higher"* (110); and he once calls it by the other name,
*"we can also use the **Fibonacci retracement**... you guys would have entered when this
candlestick broke above the 79% extension"* (099).

**So the level is 79% of the way back from the extreme toward the origin — a deep
retracement INSIDE the leg, 21% of the leg away from where the leg started.** Never a
projection past either end. `extension_79_level()` carries all four quotes.

This makes it a **shallower, earlier version of a break of structure**, which is exactly how
he uses it: 099, *"I don't think you guys would have had to wait for the breakup structure
because we can also use the Fibonacci retracement."*

**The one honest caveat:** this is the only part of step456 that rests on inference rather
than a sentence. If a future run makes it look wrong, the single alternative worth trying is
the mirror convention (79% measured up from the origin) — but that fires on nearly every
pullback, which cannot be squared with him waiting minutes for it and standing down when it
does not print.

### 2.3 A body close, never a wick

**080**, and it is the cleanest statement of it in the corpus:

> "**We poked underneath the 79% extension.** I would love to see NASDAQ **close** underneath
> that. We close underneath it on ES. But NASDAQ... **I want to see it fully close underneath
> here.**"

`closed_past_79()` tests `bar.c` and nothing else.

### 2.4 What he does with the number

A confirmation confluence on the 5-minute and a trigger on the 1-minute. **Never a target** —
086: *"we're not just taking profits off of random draws, okay? **We're not just taking
profits off of Fibonacci extensions.**"* And **never a stop**: the stop stays beyond the
sweep, which step453 fixed and this round does not touch.
(`test_the_79_percent_is_never_a_target_and_never_a_stop`.)

**In code, the anchors:**

- **5-minute** — `SeqState.leg_origin` up to `SeqState.sweep_extreme`, the leg that made the
  sweep. It is his "from these lows up to these highs" (110), and it **moves as the sweep
  extends**, which is why he re-reads it live: *"Still pretty far from the 79% extension. I
  think we can move higher."*
- **1-minute** — the 1-minute's own two most recent swings, which are the same two points its
  equilibrium uses. That is 066 and 082 word for word: *"draw it out just like we were to
  draw out equilibrium."*

He ranks it last himself, **066**: *"I rarely use this one... you guys can very well do
without this."* So it **widens a menu and never gates anything** —
`test_the_79_percent_only_ever_adds_trades` fails if it ever removes one.

---

## 3. THE CURRENT ENTRY IS SIX STEPS, NOT FOUR

**112** is taught as current — *"if you guys are new here"* — promotes a live event on
*"November 8th, 9th, and 10th"*, and looks ahead to *"going into 2026"*. `step434` filed it
as superseded by UPDATED-2026; it sits at position 112 of 120. **It is not old.**

### 3.1 The full sequence, in his words

| # | Step | His words | What we had |
|---|---|---|---|
| 1 | Sweep a high-timeframe draw | *"every single trade that I take is going to be off of a high time frame liquidity sweep... 1 hour highs and lows, 4hour highs and lows, session highs and lows"* | **have it** |
| 2 | 5-minute **confirmation** confluence — any ONE of four | *"break of structure inverse for value gap, a 79% extension closure, and a 5minute SMT divergence"* | **had two of four** |
| 2B | if step 1 happened pre-market, a fresh 5-minute sweep after the open | *"if that happens, we have to wait for a low time frame manipulation on the 5minut time frame when New York market opens"* | **had nothing** |
| 3 | 5-minute **continuation** confluence | *"equilibrium fair value gaps or if 2B happens then an SMT divergence. And that's only if 2B happens."* | **had the first two** |
| 4 | the same four-option menu again on the **1-minute** | *"via the same exact confirmation confluence that we had had before"* | **had ONE of four** |
| 5 | enter, stop beyond the sweep | *"We're entering right here. We're putting our stop loss above these highs"* | **have it** |
| 6 | target the other draws in the trade's direction | *"we're targeting the other draws on liquidity that are in our direction"* | **have it** |

He numbers 1, 2, 2B, 3 and 6 out loud and never numbers the 1-minute stage or the entry, so
the labels 4 and 5 are ours; the order is his.

### 3.2 It is an OR, and he says so

> "**we don't need every single one of these to happen. We just need one** because each one
> of these confluences signifies the same thing that we swept liquidity."

**099 gives the identical four-item menu**, so 112 is not a one-off:

> "our confirmation confluences... this comes in the form of breakup structure, inverse for
> value gap, SMT divergence, and a 79% extension closure on the Fibonacci."

### 3.3 What we were missing, and the switch for each

**On the 5-minute (step 2)** we accepted a break of structure and a gap inversion. The other
two arrive with `extension_79_enabled` and `smt_in_confirmation_menu`. Both are tested
**last** in `on_5m`, so on a bar where an old route and a new one both fire the old label
wins and a run with the switches off is untouched.

**On the 1-minute (step 4)** we accepted **one** of his four — a break of structure. All
three others are now reachable:

- `trigger_menu_1m_gap_inversion` — **the inverse fair value gap on the trigger chart, which
  we had never computed at all.** A `GapBook` on the 1-minute, built only when the switch is
  on.
- `extension_79_enabled` — the 79% on the 1-minute.
- `smt_in_confirmation_menu` — a 1-minute divergence, which he takes an entry off in **103**:

> "**why did I go short before seeing a one minute inverse for value gap or a one minute
> break of structure to the downside? Because we had this one minute bearish SMT.**"

`SeqState.trigger_kind` and `Trade.trigger_kind` now record which of the four fired. Before
this round there was only ever one of them, so it was not worth writing down.

**Step 2B** — `require_fresh_5m_sweep_after_open`. His reason: *"when New York market opens,
**new money** is coming into the market. And when new money comes into the market, there's
almost always going to be some form of manipulation."* And his own exclusion: *"**the only
time that we use 2B** is if the high time frame form of manipulation happens **before** market
opens."* So it hangs off our pre-market carry-forward and nothing else. It only ever removes
trades.

step454 recorded step 2B as already covered by `premarket_sweep_carries_forward`. **It is
not.** Our carry-forward takes a pre-market sweep and delivers it into the *confirmed* state;
112 says that state still owes a fresh 5-minute manipulation after the bell before the
continuation stage may begin. That is a gate we did not have.

**Step 3's conditional** — `smt_in_continuation_menu_after_2b`. He enforces the exclusion
himself on the next worked example: *"**2B didn't happen**, at least for the bearish case.
Okay? So, **we're not able to use** an SMT divergence."* He promises to explain why 2B unlocks
it and never does; that stays **NEEDS VIDEO**.

### 3.4 One more thing 112 has that we did not — the continuation confluence must HOLD

Not on step454's list, found while establishing the menu. **112**, walking a worked example:

> "Price comes into equilibrium. Okay, we're looking for a break of structure to the
> downside. Oh, wait. It's going higher. It's going higher and **we close above equilibrium.
> Oh, so that invalidates step number three.**"

Our code treats the continuation confluence as a zone to touch. He treats it as a level that
has to hold on a closing basis. **Switch: `invalidate_on_close_beyond_continuation`.**

**OURS, NOT HIS:** it is judged on bars **after** the one that stamped the pullback. His "it's
going higher" is the candles that follow the touch, and applying it to the touching candle
itself would kill the stage on the bar that created it. The rule is his; that choice is ours.

**This is the single most expensive switch in the set** — see section 5.

---

## 4. Proof that everything-off reproduces today's behaviour, trade for trade

`step456_baseline.json` was written by the binary **before** `tjr_bot.py` was edited. It is a
photograph of the old bot over **251 real SPY/QQQ sessions, 2025-07-25 to 2026-07-24** — every
trade, and for each one all 29 fields that an entry-logic change could move: the level and its
timeframe, what confirmed it, the entry time and price, the stop, risk per share, share count,
notional, dollars risked, the share of the day's budget, which rule sized it, every target and
its source, the regime, the exit, the outcome, the money, and the account after.

```
$ python3 step456_baseline.py --check
identical
```

`test_everything_off_reproduces_the_recorded_baseline_trade_for_trade` re-runs the same 251
sessions with `Config()` and compares trade by trade, field by field, plus the closing account
and every stand-down reason with its count.

**251 sessions · 44 trades · account $100,000 → $98,933.12 · identical.**

Four things make that a real claim rather than a tautology:

1. **The baseline predates the edit.** It cannot have been re-derived from the new code.
2. **The new machinery is not merely ignored, it is never built.** `SwingLog`, the 1-minute
   `GapBook` and every divergence are constructed only when their switch is on, so an off run
   does not walk the new code at all.
3. **Every new route is tested LAST** in `on_5m` and `on_1m`, after every route that already
   existed, so no old label can be displaced.
4. **The comparison is against the old field set.** Four fields step456 added
   (`trigger_kind`, `smt`, `smt_role`, `smt_completion`) are stripped before comparing — a
   field that did not exist in the old binary cannot be evidence the old binary behaved
   differently. With the switches off `trigger_kind` reads "1-minute break of structure" on
   every trade, because that was the only trigger there was.

**Crypto is untouched too.** `test_step456_did_not_move_the_crypto_setup_count` pins the
recorded BTC/USD 55 and ETH/USD 41 setups over the 54 sessions to 2026-07-24.

### Causality, with the switches ON

Every existing truncation test still passes, but all of them run with the switches OFF, so
none of them touches a divergence, a 79% level or a 1-minute gap. Two new ones cover the new
code:

- `test_truncation_the_new_rules_cannot_see_the_future_either` re-runs **the** test with
  `Config.newest_teaching()`: every entry bar re-decided with every later bar deleted, same
  symbol, side, entry, stop and swept level. The two things that could have gone wrong were a
  divergence read off a swing not yet stamped, and a 79% level anchored on a sweep extreme
  that had not happened yet.
- `test_truncation_a_divergence_is_never_read_before_its_swing_is_stamped` holds a `SwingLog`
  fed the whole day against one stopped short, and demands identical swings up to the cut —
  none early, none revised after stamping.

The design reason both hold: `SwingLog` is fed one CLOSED bar at a time, forward only; a
swing is stamped on the second candle of its pair using that candle's own wick; and
`smt_between` reads nothing but already-stamped swings. `run_day` advances the logs before
`on_5m` rather than after, so the divergence describes the bar being decided instead of the
one before it, and `SwingLog.update` ignores a bar it has already seen so `on_5m` calling it
again is free.

---

## 5. The before and after, over the past year

`python3 step456_before_after.py` — 251 SPY/QQQ sessions, 2025-07-25 to 2026-07-24,
$100,000 start.

### The two halves

| | trades | days traded | share of sessions | days/month | win rate | net |
|---|---|---|---|---|---|---|
| **BEFORE** — every switch off | 44 | 37 | 15% | 3.1 | 52.3% | −$1,067 |
| **AFTER** — every switch on | 32 | 27 | 11% | 2.3 | 65.6% | +$13,612 |

### Each rule on its own, against BEFORE

| rule | switch | trades | days/month | win rate | net | vs before |
|---|---|---|---|---|---|---|
| SMT, bias only | `smt_enabled` | 44 | 3.1 | 52.3% | −$1,067 | **±0** |
| SMT picks the chart | `+ smt_picks_the_instrument` | 40 | 2.8 | 57.5% | +$1,515 | **−4** |
| SMT joins the menu | `+ smt_in_confirmation_menu` | 52 | 3.6 | 48.1% | −$2,016 | **+8** |
| the 79% extension | `extension_79_enabled` | 56 | 3.8 | 53.6% | +$6,876 | **+12** |
| the 1-minute inverse gap | `trigger_menu_1m_gap_inversion` | 49 | 3.3 | 55.1% | +$5,468 | **+5** |
| step 2B | `require_fresh_5m_sweep_after_open` | 44 | 3.1 | 52.3% | −$1,067 | **±0** |
| the continuation must hold | `invalidate_on_close_beyond_continuation` | 24 | 1.8 | 62.5% | +$360 | **−20** |

**`smt_enabled` alone moves nothing, and that is the design working.** On its own a
divergence only enters `confluence_count`, which can never let a trade in or keep one out —
it only breaks a tie between two setups that have both already qualified, and over a whole
year no tie turned on it. That is 120 implemented literally: *"It doesn't tell me to take a
trade."*

**Step 2B also moves nothing over this year.** The pre-market carry-forward is rare, and on
the days it fired a fresh 5-minute sweep followed the open anyway. The gate is real and it
is his; it simply did not bind. Worth knowing before anyone concludes it is dead code.

**Every one of his eight routes actually fires**, which is the check that the menu is wider
in the market and not just on paper:

- 5-minute confirmation: break of structure 13, **79% extension 8**, gap inversion 4, close
  back through the sweep origin 4, pre-bell break of structure 1, **SMT divergence 2**
- 1-minute trigger: **79% extension 15**, **gap inversion 8**, break of structure 5,
  **SMT divergence 4**
- a divergence was live on 7 of the 32 trades — 4 as the trigger, 3 strengthening the bias

### Read it this way, and not the other way

**The money is not the point and is not evidence.** He does not count replay as evidence and
step454 section 4a is blunt: his own year is roughly a 60-65% win rate at a reward-to-risk a
little above 1:1, and **"beating any of them in a replay is a bug report, not a success."**
The AFTER half's 65.6% sits just at the top of his own band, which is the right side of
"suspicious" but not comfortably so, and it comes off 32 trades — far too few to mean
anything on its own.

**The trade count is the point.** step436 item 11 has him trading **7 to 15 days a month**,
and step454's warning on the widened menu was that if our trade count rises above that, the
menu is too wide. It does not. **BEFORE trades 3.1 days a month and AFTER trades 2.3.** The
widest single switch, the 79% extension on its own, reaches 3.8. Every configuration is
**well under half his floor**, so the menu widening did not push us past him — the opposite
worry applies, and it is the honest headline here:

> **This bot trades roughly a third as often as he does, and the newest teaching made that
> gap wider rather than narrower.** Three of the seven switches remove trades and two of
> those remove a lot. Whatever is keeping us off his pace is not the confirmation menu,
> because opening the menu all the way still leaves us at 3.8 days a month against his 7 to
> 15. That is the next thing worth chasing, and it is not in this round's scope.

### One number to distrust deliberately

`invalidate_on_close_beyond_continuation` removes **20 of 44 trades**, nearly half. It is
quoted straight out of 112 and it only ever removes, so it cannot manufacture a win — but
its effect is far larger than a rule he mentions once in passing ought to have, and the
"judge it on bars after the touch" choice inside it is OURS. **Treat that switch as the least
trustworthy of the seven** until there is a second video for it.

---

## 5a. Test status, stated plainly

- **Every `tjr_*` test passes.** 121 in `test_tjr_bot.py` + `test_tjr_crypto.py` (73 + 48),
  of which **24 are new in this round** — 19 in the bot, 5 in crypto. 262 pass across the
  whole tjr surface plus `test_tjr_desk.py`, `test_tjr_gold.py`, `test_tjr_forex.py`,
  `test_live_imports.py`, `test_stand_down_gates.py`, `test_exits.py` and
  `test_news_calendar.py`. Every pre-existing truncation test still passes.
- **The full repo run is 573 passed, 11 failed.** All 11 are in `test_breakout_book.py`,
  `test_diver.py`, `test_newsdesk_exit.py`, `test_newsdesk_timing.py` and
  `test_state_save.py` — the retired bots. **They are pre-existing and cannot be ours:
  importing all five of those test files loads no `tjr_*` module at all**, directly or
  transitively, so nothing this round changed is reachable from them. The failures are the
  retired books reporting `stood_down` where the test still expects `entered`, which is the
  2026-07-25 retirement showing through tests that were never updated for it.

---

## 6. What is in step454 and is NOT built, with the reason

| step454 item | Status | Why |
|---|---|---|
| **Prominent high / area of accumulation / change of trend** (§0.2, §5 item 8) | **NOT BUILT, and must not be** | 003 only, out of 105 videos, and he calls the marking *"purely based off the eyes"*. This is the order-block trap a second time. |
| **§5 item 4 — the win-streak de-risk** (081, 075, 076) | **not built** | Real and quoted — *"I'll purposely de-risk like the following week or the following day after a really big day or a really good week"* — but **the depth of the cut is NEEDS VIDEO**, he never attaches a number, and it is a SIZING rule. Sizing was rebuilt in step453 and this round was told not to touch it. It belongs in the same round as the sizing, not this one. |
| **§5 item 5 — new day opening gap, new week opening gap, midnight open** (074-081, 110-111) | **not built** | Their exact construction is **NEEDS VIDEO** — which two candles form the gap, which timeframe, and whether "midnight" is 00:00 New York. They are LEVELS, and the levels were rebuilt in step453 and are out of scope here. Guessing a construction is how "prominent high" happened. |
| **§5 item 6 — the ladder can never be overridden** | **already true, nothing to do** | There is no discretionary override anywhere in `_manage` or `manage_step` and none was added. §3.0 of step454 is the reason it must stay that way. |
| **§2.3 the "imbalanced price range"** | **not built** | Marking rule is NEEDS VIDEO. It is a TARGET, and targets are out of scope. |
| **§2.4 the PM session** (096) | **not built** | A whole second trading window, i.e. a clock change, and he hedges it himself: *"don't take that as just like the golden rule."* Out of scope and low confidence. |
| **§2.5 the 1-to-3-hour holding time** (096) | **not built** | A shape check on a replay, not a rule the bot can act on. |
| **§2.6 where to sit in the 1%-to-3% band** (069) | **not built** | Sizing. Out of scope, and step454 itself leaves it flagged and unresolved. |
| **§2.7 entry in two tranches** (078) | **not built** | It contradicts `step433` §8.2's no-averaging rule and step454 filed it *"for a decision rather than built"*. That decision has not been made, and it is a sizing change. |
| **§2.8 the insurance play**, **§2.9 trading the news release**, the aggressive 1-minute entry | **NOT BUILT, deliberately** | step454 says do not build all three. The insurance play and dual-index entries appear in his two worst days; the news-release trade is what our news gate exists to keep an automated system away from; the aggressive entry's size is a discretionary conviction call he runs both large and small. |
| **§5 item 7 — correct step436 / step434 / step452** | **not done** | Documentation edits to files this round was not asked to change. The corrections are recorded here instead: `step436` item 12's two "dropped" entries are both wrong; `step436` §1's order-block retirement should be narrowed to *continuation confluences*; `step434` §5A has the leading-index rule as the older practice and it is the newer; `step434` §8's 08:00-vs-08:30 ambiguity can be struck; and step454's own claim that step 2B is covered by `premarket_sweep_carries_forward` is wrong (§3.3 above). |

### One NEEDS VIDEO closed

step454 §1.3 and §5 item 2 leave **"the mechanical test of 'leading'"** open. It is not open —
115 and `SMT_Divergence_Explained` both state it as a swing comparison, quoted in §1.6.
**Leading = the chart whose second swing broke the trend.**

### Two things found that step454 does not have

1. **112's continuation-confluence invalidation** (§3.4). Not in step454 at all.
2. **112's 1-minute menu includes an inverse fair value gap on the 1-MINUTE chart**, which we
   had never computed on any chart below the 5-minute (§3.3).

### Left alone on purpose

**"Leading" is per-timeframe and can invert.** 076: *"on ES, is the lagging high time frame
index, but on the low time frame, it's the leading one."* Our divergence is computed per
timeframe already, so a 5-minute and a 1-minute divergence can name different leaders and both
are honoured on their own chart. What is NOT built is a rule for what to do when they conflict
— he never gives one, and 105's own labels contradict his mechanical test, so 105 is not used
as a source.

**He sometimes overrides the leading-index rule on a better draw on liquidity.** 101: *"ES has
better draws on liquidity to the downside than Nasdaq... And on top of that, it's leading."*
076: *"Honestly, I'm fine trading on either one of these today."* That is discretion and it is
not built; the switch takes the leading chart every time.
