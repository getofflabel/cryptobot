# step471 — The Alex engine against a prop-firm rulebook

Built 2026-07-26/27. **Replay only. No venue was touched, no order was placed,
nothing was purchased and nothing was signed up for.** `alex_engine.py` was
imported read-only. No existing file in the repo was modified. New files:
`step471_prop_eval.py`, `step471_test_prop_eval.py`, this document, and three
result CSVs.

Run it: `python3 step471_prop_eval.py` (12 seconds).
Tests: `python3 -m pytest step471_test_prop_eval.py -q` → **15 passed.**

---

## THE ONE LINE

**Today the engine can be trusted with an account it is allowed to sit still
on — at half a percent to one percent of the account risked per trade it never
loses 5% of an account in a day, not once in five years — and on a bad week it
costs about 1% to 4.5% of the account. What it cannot be trusted to do is
GROW. It adds under a tenth of one percent of the account a week, so the +9%
an evaluation demands only ever arrives by luck, and the luck usually shows up
after the 10% trailing drawdown has already killed the ticket.**

Discipline: yes, at his sizing. Earning power: no. That is the whole finding.

---

## 1. HIS RULES, WITH QUOTES AND DATES

Everything below comes from his own material. Where he is silent, it is marked
**OURS** with the reason.

### From the $50 video — `ag_transcripts/hb7ot1_szWI_50dollars_clean.txt`, uploaded **2026-07-26** (today)

| rule | his words |
|---|---|
| the firm | "A Capital is a prop firm. I flew out to Australia, met the CEO in person." Discount code **AlexG20**, 20% off. |
| the ticket | "with 50 bucks, you can really get a two-phase challenge with a **$5,000 account**" |
| **phase 1 target** | "You need to have your **profit target be 9%** for your step one" |
| **phase 2 target** | "and then your **profit target be 5%** for step two" |
| timeline | "I always estimate it should take you anywhere from **30 to 45 days** to pass a two-step challenge simply because you should be taking one to two trades a week." |
| his arithmetic | "if you make 3% then lose 1%, make 3% then lose 1% … that's roughly the **9% in about 3 weeks**" |
| **the split** | "you get **90% profit split**" |
| what funded pays | "once you are funded with that $5,000 challenge, let's say for that next month you would make 10%. You would essentially keep **nearly 450 bucks**" |
| position cap | "**Limit yourself to two positions a week.** No need for any more of that." |
| **sizing on a challenge** | "have a fixed percentage on your challenge account. **Make it a 1% rule. Make it a half percent rule.** This is a marathon, not a sprint." |
| and again, later | "I'm just risking **1% on my 5K challenge** with my 50 bucks" |
| risk-to-reward | "have a **minimum of a 1:2** risk to reward" |
| instruments | "you want to dedicate this to **the majors** … these are the Euro USDs of the world, GBP USDs of the world" |
| the one-phase variant | "the other one-phase challenge … it's a **total profit of 10%** and then you have a funded account" |
| the custom / instant-funded variant | "you start with a **$10,000 starting balance**. Whether you decide to risk 50 bucks, 300 bucks, 500 bucks … 1 hour, 2-hour, 4-hour, or 8-hour challenge … **you pass it, you get paid, you do it again**. There's no evaluation process, there is no profit split, there is no continuation." |
| custom variant numbers | "2x of what you risked, all you have to do is make **$99** on the $10,000 account without losing more than **$67** … 5x where you would get 250 bucks, you have to make **133 bucks without losing 47** … you have to make **239 without losing 40**" |
| the honest warning | "you can probably make a total of 5 to 6% where you're profitable, but you enter a losing streak or you just **break a small rule** … and then you lose your account" |
| his own path | "I would personally start with attempting to pass a challenge, get funded, get that payout, **use those profits to go and trade my personal account.** I would not go and use that to go get a bigger challenge." |

**A note the brief got backwards, and it matters:** the brief said his prop-firm
sizing is 1–1.5% of the account. His actual words in this video are **1% or
0.5%**. 0.5% is therefore in the tested band, and it is the safest and the
slowest cell in every table.

**The strategy in this video is the head and shoulders on the 4-hour, not the
engulfing candle.** "the pattern that we're going to be looking for … is going
to be the famous head and shoulders … the only pattern that you are going to
execute." The engine trades the engulfing-candle spine from
`KPVVOa6c6dY_dumb_clean.txt` (2026-06-14). Both are 4-hour majors, both wait
for a structure shift and a retest, and neither is the other. **Nothing here
measures his head and shoulders — that pattern is not implemented anywhere in
this repo.** Flagged, not hidden.

### From the founder interview — `ag_transcripts/DejB31rwv8c.txt`, uploaded **2026-07-15**

This is the only place in 198 uploads where the firm's own rulebook is read out
loud on camera. Alex asks for "every single rule" and the founder hands over
"our rules on a page":

| rule | the words |
|---|---|
| **the consistency rule** | "Profit distribution. **No single trading day profit can exceed 30% or 35% of the total reduced profit.**" — a soft breach: "your account will get reset back to the beginning and you'll get a warning" |
| **the payout cap** | "up to 90% profit share, **profit cap 5% on one phase, 10% on two phase** … you get your payout, your account gets reset and you're free to trade again" |
| minimum trading days | "Minimum trading days pretty standard." **He never says the number.** |
| news | "10 minutes" around news |
| what is allowed | "We allow HFT. We allow EAs. We allow scalping. We allow swing trading and day trading and weekend trading." |
| what is not | grid trading, copy-trading someone else's account, account management |
| the custom challenge's extra rule | "the **profit allocation rule** … you can't win all your money on gold, for example. You have to trade **gold and forex**" |

**The founder never states a daily-loss cap or a maximum drawdown on camera,
and neither does Alex, in any of the 54 transcripts.** That is the gap.

### From `ag_transcripts/lHGkup8CoTE.txt`, uploaded **2026-07-19**

The closest he ever comes to a drawdown number, describing the firm he
personally passed years ago:

> "Two steps. Step one, make 10% in 30 days. Step two, make 8% in 60 days. And
> you have **8% stop loss, 10% stop loss**, and that is it."

Looser than the industry default, so it is run as a sensitivity, not as the
base case.

### OURS, and why

| ours | value | reason |
|---|---|---|
| **maximum daily loss** | **5% of the ACCOUNT**, intraday, against the equity the day started at | He is silent; every real firm has one; 5% is the industry shape. His own old-firm number (8%) is run beside it. |
| **maximum total drawdown** | **10% of the ACCOUNT**, intraday, **trailing the equity high-water mark** | He is silent. Trailing is the strict reading. The static reading (against the $5,000 start) is run beside it and is materially easier. |
| minimum trading days | 3 | "pretty standard", number never given. |
| the trading day boundary | 17:00 New York | Where this tape's daily bodies close and where the FX day actually rolls. |
| costs on the evaluation | OANDA's measured spreads — EUR/USD 0.0138%, GBP/USD 0.0141%, GBP/JPY 0.0156% of the price, round trip | The firm's fill quality is unknown; OANDA's is measured. Charged on every trade and consulted by nothing. |
| gold's cost | OANDA XAU/USD, 0.0141% of the price round trip | A prop firm trades gold as a CFD, not as BloFin's XAUT-USDT. The engine's own gold cost (0.1249%) is nine times higher and would be wrong here. |
| the 730-day cap per phase | ours | A replay has to terminate. Reported as "ran out of runway", **never as a pass.** |

### Gold: included, as a clearly-labelled sensitivity

The $50 video says majors. His corpus says gold is traded "as if it were to be
a foreign exchange currency pair" (`ig6Z2Gbk_LE_gold_clean.txt`, 2025-11-09),
and the firm's own custom challenge **requires** gold alongside forex. So
pairs-only is the primary book and majors+gold is run beside it.

---

## 2. THE DISCIPLINE PICTURE — the table that answers the real question

One $5,000 account. Five years. No evaluation attached, no reset, no pass, no
fail. Two positions at once, his cap. Every percentage is a **share of the
ACCOUNT**.

| book | risk/trade | end $ | worst DAY | worst peak-to-trough (equity) | worst WEEK | weeks green | days below the 5% daily line | days below the 10% trailing line |
|---|---|---|---|---|---|---|---|---|
| majors, his literal floor | **0.5%** | $5,062 | −1.4% | −15.4% | −2.4% | 40% | **0** | 454 |
| majors, his literal floor | **1.0%** | $4,998 | −2.8% | −30.6% | −4.4% | 40% | **0** | 793 |
| majors, his literal floor | 2.0% | $4,524 | −5.7% | −59.9% | −7.5% | 41% | 5 | 872 |
| majors, his literal floor | 3.0% | $3,716 | −8.8% | −91.1% | −12.0% | 41% | 68 | 917 |
| EUR/USD alone | 0.5% | $4,726 | −0.9% | −16.0% | −1.1% | 31% | **0** | 163 |
| EUR/USD alone | 1.0% | $4,429 | −2.0% | −31.6% | −2.2% | 31% | **0** | 272 |
| **majors, engulf ≥ 3** | **0.5%** | $5,236 | −1.4% | **−7.3%** | −1.1% | 33% | **0** | **0** |
| majors, engulf ≥ 3 | 1.0% | $5,451 | −2.8% | −15.6% | −2.4% | 33% | **0** | 29 |
| **majors, engulf ≥ 4** | **0.5%** | $5,384 | −1.4% | **−4.4%** | −1.1% | 31% | **0** | **0** |
| **majors, engulf ≥ 4** | **1.0%** | $5,779 | −3.0% | **−9.1%** | −2.3% | 31% | **0** | **0** |
| majors, engulf ≥ 4 | 3.0% | $7,427 | −11.7% | −30.0% | −8.5% | 31% | 25 | 120 |
| majors, 1:3 target | 1.0% | $3,803 | −3.7% | −45.7% | −4.6% | 34% | **0** | 828 |
| majors + gold | 0.5% | $5,627 | −1.5% | −11.3% | −2.1% | 44% | **0** | 23 |
| majors + gold | 1.0% | $6,170 | −3.3% | −22.3% | −4.0% | 44% | **0** | 464 |

Full grid in `step471_risk_results.csv`.

**What this table says, in order of importance:**

1. **At his own sizing the daily-loss rule is never the problem.** Zero days
   below the 5% daily line, on every book, over five years, at both 0.5% and
   1% of the account per trade. His "make it a 1% rule, make it a half percent
   rule" is doing exactly the job he says it does. The daily cap only starts
   biting at 2% and becomes fatal at 3% — which is his **own-money** number,
   never his prop-firm one.

2. **The 10% trailing drawdown is what kills, and it is the engine's own
   grinding losing streaks that trigger it**, not any single bad day. The
   literal-floor book spends **793 of its five years below that line** at 1% of
   the account per trade. Not "touches it" — lives under it.

3. **Three configurations went five years without ever touching either cap:**
   engulf ≥ 3 at 0.5%, engulf ≥ 4 at 0.5%, and **engulf ≥ 4 at 1.0%**. That
   last one is the best cell in the file: worst day −3.0% of the account, worst
   peak-to-trough −9.1% of the account, worst week −2.3% of the account,
   finishing five years at **+15.6% of the account**. It is fully disciplined
   and it earns 3% of the account a year.

4. **A bad week costs 1% to 4.5% of the account** at his sizing. That is the
   number to hold onto. It is small. It is also small in the other direction.

---

## 3. THE PACE — why the evaluation is out of reach

Phase 1 wants **+9% of the account**. He estimates 3 weeks for it, 30–45 days
for both phases. Here is what the tape actually produces over five years,
after costs, with his two-position cap applied.

| book | trades | /week | won | mean R | account/week at 1% risk | weeks to +9% by drift | mean R **needed** for his 45 days | gap |
|---|---|---|---|---|---|---|---|---|
| majors, his literal floor | 507 | 1.92 | 34.3% | **−0.00** | −0.00% | **never** | +0.73 | **0.73 R** |
| EUR/USD alone | 184 | 0.70 | 32.6% | −0.06 | −0.04% | **never** | +2.01 | 2.06 R |
| majors, engulf ≥ 3 | 147 | 0.56 | 36.1% | +0.07 | +0.04% | **241 weeks** | +2.51 | 2.45 R |
| majors, engulf ≥ 4 | 75 | 0.28 | 40.0% | **+0.20** | +0.06% | **157 weeks** | +4.92 | 4.72 R |
| majors, 1:3 target | 460 | 1.74 | 24.6% | −0.05 | −0.09% | **never** | +0.80 | 0.85 R |
| majors + gold | 545 | 2.07 | 35.4% | +0.04 | +0.07% | **122 weeks** | +0.68 | 0.64 R |

**This is the finding, and it is not close.** His own arithmetic assumes +3% of
the account a week. The best book on this tape produces **+0.07% of the account
a week**. That is a factor of forty. Phase 1 alone, by drift, takes **two to
four and a half years** on the configurations whose drift is even positive, and
never on the ones whose drift is not.

The right-hand columns say what would close the gap. At the literal floor's
cadence of ~1.9 trades a week, phase 1 inside 45 days needs a mean of **+0.73 R
per trade**. The engine delivers −0.00. His quality dial gets mean R to +0.20
— the highest number in the file, and still 4.7 R short at that book's much
thinner cadence of one trade every 3.5 weeks.

---

## 4. PASS ODDS ACROSS THE SIZING BAND

Every Monday in the five years is a start week: ~260 rolling starts per book,
no lookahead, sizing off the balance as it stood. **Overlapping windows are not
independent samples** — five years holds about five non-overlapping year-long
attempts, so these are 260 readings of one tape, not 260 experiments. Read the
columns, not the third decimal.

Phase 1 is scored on all starts; phase 2 on the starts that survived phase 1.

| book | risk | P1 pass | P1 killed by daily | P1 killed by trailing DD | P1 too slow | **P(pass BOTH)** | median days | **P(both ≤45 days)** | single-day > 35% of profit |
|---|---|---|---|---|---|---|---|---|---|
| majors, his literal floor | 0.5% | 40.7% | **0.0%** | 26.2% | 33.1% | 2.3% | 599 | 0.0% | 0% |
| majors, his literal floor | **1.0%** | 33.5% | **0.0%** | 57.8% | 8.7% | **14.4%** | 122 | 0.0% | 68% |
| majors, his literal floor | 1.5% | 29.7% | **0.0%** | 66.2% | 4.2% | 6.1% | 66 | 1.5% | 35% |
| majors, his literal floor | 2.0% | 22.1% | 11.0% | 65.8% | 1.1% | 5.7% | 32 | 3.8% | 86% |
| majors, his literal floor | 3.0% | 7.2% | 69.6% | 22.1% | 1.1% | 0.4% | 11 | 0.4% | 100% |
| EUR/USD alone | 1.0% | 12.4% | **0.0%** | 72.0% | 15.6% | **0.0%** | — | 0.0% | — |
| EUR/USD alone | 2.0% | 19.2% | **0.0%** | 71.2% | 9.6% | 12.4% | 94 | 1.2% | 73% |
| majors, engulf ≥ 3 | 0.5% | 0.4% | **0.0%** | **0.0%** | **99.6%** | 0.0% | — | 0.0% | — |
| majors, engulf ≥ 3 | **1.0%** | 38.0% | **0.0%** | 36.1% | 25.9% | **26.6%** | 800 | 0.0% | 80% |
| majors, engulf ≥ 3 | 1.5% | 33.1% | **0.0%** | 56.3% | 10.6% | 15.2% | 289 | 0.0% | 47% |
| majors, engulf ≥ 4 | 0.5% | 0.0% | **0.0%** | **0.0%** | **100%** | 0.0% | — | 0.0% | — |
| majors, engulf ≥ 4 | 1.0% | 29.4% | **0.0%** | 4.8% | 65.9% | 0.4% | 356 | 0.0% | 0% |
| majors, engulf ≥ 4 | 1.5% | 32.9% | **0.0%** | 25.8% | 41.3% | 19.8% | 255 | 0.0% | 11% |
| majors, engulf ≥ 4 | 2.0% | 44.4% | 15.9% | 38.5% | 1.2% | **23.0%** | 222 | 0.0% | 82% |
| majors, 1:3 target | 1.0% | 21.3% | **0.0%** | 73.4% | 5.3% | 8.7% | 126 | 0.8% | 62% |
| majors + gold | 0.5% | 44.5% | **0.0%** | 16.3% | 39.2% | **27.0%** | 866 | 0.0% | 0% |
| majors + gold | 1.0% | 35.0% | **0.0%** | 52.9% | 12.2% | 12.2% | 202 | 0.0% | 62% |

Full grid in `step471_eval_results.csv`.

**Which sizing passes most often without breaching?** Reading the "killed by"
columns rather than the pass column: **0.5% and 1.0% of the account per trade
— his own two numbers — are the only sizings where the daily-loss rule is
literally never triggered.** At 2% the daily rule starts killing 11–16% of
attempts; at 3% it kills 60–80% of them and the whole idea collapses.

But the pass column is not a success. **The best P(pass BOTH) in the entire
file is 27.0%, and its median time to get there is 866 days — two years and
four months for a challenge he says takes 30 to 45.** The column that matters
is `P(both ≤45 days)`, and **its maximum anywhere in the file is 4.6%.**

And on 62–100% of the passes at the faster sizings, **a single trading day
carried more than 35% of the total profit** — the firm's own consistency rule.
That is a soft breach: account reset to the beginning, warning issued. So a
meaningful share of the "passes" above would not actually have been paid.

---

## 5. THE CONTROL — is the pass earned or is it luck?

Same entries, same days, same stop distances, **direction reversed**. If fading
the engine passes as often as following it, the pass rate is variance.

| book | risk | engine P(BOTH) | faded P(BOTH) | verdict |
|---|---|---|---|---|
| majors, his literal floor | 1.0% | 14.4% | 14.8% | **indistinguishable** |
| majors, his literal floor | 1.5% | 6.1% | 9.1% | **fade ahead — no edge** |
| EUR/USD alone | 1.0% | 0.0% | 51.6% | **fade ahead — no edge** |
| EUR/USD alone | 1.5% | 6.8% | 52.8% | **fade ahead — no edge** |
| majors, engulf ≥ 3 | 1.0% | **26.6%** | **0.0%** | engine ahead |
| majors, engulf ≥ 3 | 1.5% | 15.2% | 2.7% | engine ahead |
| majors, engulf ≥ 4 | 1.5% | **19.8%** | **0.0%** | engine ahead |
| majors, engulf ≥ 4 | 2.0% | 23.0% | 2.8% | engine ahead |
| majors, 1:3 target | 1.0% | 8.7% | 21.3% | **fade ahead — no edge** |
| majors + gold | 1.0% | 12.2% | 8.4% | engine ahead |

**The literal floor's evaluation passes are luck.** Fading it does as well or
better. Same for EUR/USD alone and for the 1:3 reading.

**His quality dial is where the information is.** At engulf ≥ 3 and ≥ 4 the
engine passes 15–27% of the time and its exact inverse passes 0–3%. That is a
real signal, measured the hard way, and it is the second independent
confirmation of the same sentence step470 confirmed: *"the more candlestick it
engulfs, the better."* The dial makes the engine both **safer** (three of the
only three never-breached configurations use it) and **directionally right**.
It just starves the cadence to one trade every 2–3.5 weeks, which is why the
account then dies of slowness instead of drawdown.

---

## 6. DOES THE ANSWER DEPEND ON THE TWO CAPS WE INVENTED?

| book | risk | strict (ours: 5% daily, 10% trailing) | his old firm's 8% daily | 10% total measured **statically** |
|---|---|---|---|---|
| majors, his literal floor | 1.0% | 14.4% | 14.4% | **38.0%** |
| majors, his literal floor | 1.5% | 6.1% | 6.1% | 24.7% |
| majors, engulf ≥ 3 | 1.0% | 26.6% | 26.6% | 26.6% |
| majors, engulf ≥ 3 | 1.5% | 15.2% | 15.2% | **36.1%** |
| majors, engulf ≥ 4 | 1.5% | 19.8% | 19.8% | **31.7%** |
| majors + gold | 1.0% | 12.2% | 12.2% | **35.0%** |

**The daily cap is not load-bearing** — loosening it from 5% to 8% of the
account changes almost nothing, because at his sizing it was never binding.
**The trailing-versus-static reading of the total drawdown is load-bearing**:
measuring the 10% against the starting balance instead of the high-water mark
roughly doubles or triples the pass rate. If the real firm turns out to use a
static maximum loss (many CFD prop firms do), every pass number above roughly
doubles — and **the pace verdict does not move at all**, because the median
time to pass is still measured in hundreds of days.

---

## 7. THE MONEY — the footnote

$50 a ticket. 90% split. Payout capped at 10% of the account per cycle, account
reset after each payout. The funded account is modelled honestly: it trades on
the same caps until it either earns its payout or breaches, and it can breach.

| book | risk | P(pass both) | tickets per funded account | $ in | payouts in 3 years | $ out | **$ out per $1 in** |
|---|---|---|---|---|---|---|---|
| majors, his literal floor | 1.0% | 14.4% | 6.9 | $346 | 0.32 | $143 | **$0.41** |
| majors, his literal floor | 1.5% | 6.1% | 16.4 | $822 | 0.32 | $143 | $0.17 |
| majors, his literal floor | 3.0% | 0.4% | 263 | $13,150 | 0.11 | $48 | $0.00 |
| EUR/USD alone | 1.0% | 0.0% | ∞ | ∞ | 0.11 | $50 | $0.00 |
| majors, engulf ≥ 3 | 1.0% | 26.6% | 3.8 | $188 | 0.35 | $157 | **$0.83** |
| majors, engulf ≥ 3 | 1.5% | 15.2% | 6.6 | $329 | 0.38 | $170 | $0.52 |
| majors, engulf ≥ 4 | 1.5% | 19.8% | 5.0 | $252 | 0.29 | $129 | $0.51 |
| majors, engulf ≥ 4 | 2.0% | 23.0% | 4.3 | $217 | 0.54 | $243 | **$1.12** |
| majors + gold | 0.5% | 27.0% | 3.7 | $185 | 0.45 | $205 | **$1.10** |
| majors + gold | 1.0% | 12.2% | 8.2 | $411 | 0.39 | $177 | $0.43 |

### The verdict number, one line

**Across the whole band the engine returns between $0.00 and $1.12 for every
$1.00 of ticket money, with a typical cell near $0.40 — and the two cells above
$1.00 need two to three YEARS per funded account to get there. On his own
configuration at his own sizing it is $0.41 out per $1.00 in. This loses
money.**

---

## 8. THE HONEST VERDICT

### This engine cannot pass a two-phase evaluation as it stands.

Not "it is unlikely to". It cannot do it the way the challenge is designed to
be done. The evidence is not the pass rate, it is the pace: the engine adds
**under a tenth of one percent of the account per week** at his sizing, and the
target is **+9% of the account**. The passes that do occur in the simulation
arrive after a median of **122 to 866 days**, and **P(pass both inside his own
45-day estimate never exceeds 4.6% anywhere in the file.**

At his literal configuration — majors, the engulf floor of one, 1% of the
account per trade — fading every trade passes as often as taking them. There is
nothing there to fund.

### But the reframed question has a better answer than the money question does

Wallace's framing is the right one: this is a discipline test, and on discipline
the engine largely passes.

- At 0.5% and 1.0% of the account risked per trade — **his own two numbers** —
  the engine **never once** loses 5% of an account inside a day. Not in five
  years, not on any of six books, not on 507 trades. The daily-loss rule that
  kills most funded traders would never have touched it.
- A bad week costs **1% to 4.5% of the account**. The worst single day across
  five years at 1% sizing is **−3.0% of the account** on the best book.
- Three configurations went the full five years without breaching either cap,
  and the best of them — **majors, engulf ≥ 4, 1% of the account per trade** —
  did it with a worst peak-to-trough of **−9.1% of the account** while finishing
  **+15.6% of the account**.

**Translated: this bot will not blow up an account. It also will not move one.**
If the question is "can I hand it thousands and sleep", the answer at 0.5–1%
sizing is closer to yes than anything else in this repo. If the question is
"will it earn", it is not ready.

### What pace would be needed, and which of his own dials closes the gap

To clear phase 1 inside his own 45-day estimate at 1% of the account per trade,
at the literal book's cadence of 1.9 trades a week, the engine needs a mean of
**+0.73 R per trade**. It produces −0.00. Two of his own dials move it and
neither closes it:

1. **The engulf quality score.** Mean R goes −0.00 → +0.07 (≥3) → **+0.20**
   (≥4), the drawdown collapses from −30.6% to −9.1% of the account, and the
   direction call starts beating its own inverse 20:1 instead of tying it. This
   is the single most valuable dial in the file and it is **his sentence**, not
   a fitted parameter. Its cost is cadence: one trade every 3.5 weeks, so 66%
   of evaluations simply run out of runway. **A continuous quality SCORE rather
   than a hard floor is the obvious next build** — keep the mean-R lift, keep
   more of the cadence.
2. **Structure targets instead of a fixed 1:2.** The flat 1:3 reading is
   *worse* on every measure here — mean R −0.05, 73% of phase-1 attempts killed
   by drawdown, and its inverse beats it. So "just extend the target" is
   answered and the answer is no. What is untested is his actual instruction:
   "my take profit to the next **structure point**" — a target that varies with
   the chart rather than a fixed multiple. That has never been implemented.

Neither gets from +0.20 R to +0.73 R. The gap is his judgement, which step470
already identified and step471 has now priced: **it is worth about half an R
per trade, and that half R is the entire difference between a bot that survives
and a bot that earns.**

### What I would do next, in order

1. **Build the engulf quality SCORE** (size of the engulf against recent range,
   where it sits in the swing, how long price struggled at that level). It is
   the only dial that improved safety AND direction AND mean R simultaneously.
2. **Implement his head and shoulders.** The $50 video — his newest upload, from
   today — names it as *the* pattern for exactly this task, and nothing in this
   repo trades it. We measured the wrong pattern against his own prop-firm plan.
3. **Structure-based targets**, since the flat-multiple version of the same idea
   is now measured and rejected.
4. **Do not buy a ticket.** Not on cost grounds — costs are not a decision input
   here — but because the measurement says the money goes out and does not come
   back, and because the thing that would change that is a build, not a purchase.

---

## 9. SAFETY LEDGER

- **No order was placed on any venue. No purchase, no signup, no account was
  created.** `step471_prop_eval.py` imports `alex_engine` and nothing else that
  touches a network; `test_this_file_places_no_order_and_imports_no_venue_client`
  reads the source and fails if that changes.
- **No git command was run. No Render. No deploy.**
- **No existing file was modified.** Four new files: `step471_prop_eval.py`,
  `step471_test_prop_eval.py`, `step471_prop_eval.md`, and three result CSVs
  (`step471_eval_results.csv`, `step471_risk_results.csv`,
  `step471_money_results.csv`).
- **`alex_engine.py` is imported read-only** and its 41 tests are untouched and
  still pass.
- **No lookahead.** Rolling starts consult only what had closed by the day being
  scored; sizing uses the balance as it stood at entry; a settled outcome is
  proved unchanged when the future is deleted
  (`test_no_lookahead_deleting_the_future_cannot_change_a_settled_answer`).
- **15 new tests, all green.** The two that failed first were real bugs and both
  were fixed: a 15-minute wick was being allowed to drag floating equity past
  the stop the position would already have been closed at, and a source-scan
  test was banning a venue's *name* rather than its *import*.
