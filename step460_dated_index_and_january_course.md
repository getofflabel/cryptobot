# Step 460 — every source dated, and the January 2026 course re-extracted

Wallace: *"careful with the we already have 13 of 16, a man changes a lot in 3 years."*

He was right, and the check came back worse than the warning. Until now this project
decided which of his contradictory statements governed by reading tea leaves — playlist
position, shared vocabulary, how detailed a lesson was. Every one of those proxies is now
replaced by an actual upload date pulled from YouTube.

**The headline: Boot Camp 2.0 was filmed in August and September 2023. Boot Camp 1.0 was
filmed in May, June and July 2023.** Both are 2023. The Path to Profitability course ran
daily from 2026-01-01 to 2026-01-17. So the risk-management rules this bot runs today are
**two years and five months older** than the risk-management lesson sitting unread in
`tjr_transcripts/`.

`step452` opens with *"Boot Camp 2.0 is the newer teaching."* It is not. It is among the
oldest material we hold.

---

## 0. How the dates were obtained, and what is solid

`yt-dlp --print "%(upload_date)s"` against each video id, one at a time. Where YouTube's
bot check blocked the default extraction path, `--extractor-args "youtube:player_client=mweb"
--ignore-no-formats-error` got through; the date is the same field either way.

Three claims this project has been making on inference are now settled on evidence:

1. **`playlist3` file numbers are chronological, with four exceptions in 103 files.**
   `step454` §0.1 argued this from internal references. It holds as a trend and should not
   be used as a tiebreaker between neighbours. The four inversions:

   | pair | dates |
   |---|---|
   | 001 → 002 → 003 | 2023-11-02, 2023-09-27, **2023-09-05** — the first three run backwards |
   | 060 → 061 | 2025-01-10 → 2024-08-12, a five-month step back |
   | 102 → 103 | 2025-10-11 → 2025-10-09 |

   Two of those touch conclusions this project already drew, and both survive. **003 is not
   the third-oldest — it is the oldest video in the playlist**, which strengthens rather
   than weakens `step454` §0.2's ruling on "prominent high". And 103, the video `step456`
   §3.3 cites for a 1-minute SMT entry, is 2025-10-09 — two days *older* than the file
   number implies, and in any case older than the January course.
2. **`tjr_transcripts/path/HIS_TEACHING_ORDER.md` is exactly right, video for video.** The
   sixteen-step order it reconstructed matches the upload dates one-for-one, with a single
   footnote: there is no 2026-01-15 video, because he says so himself at the top of the
   risk lesson — *"I'm sorry I completely forgot to film this yesterday."* That is why 15
   videos carry 16 slots.
3. **`step454` §0.3's inference that Boot Camp 2.0 is old was correct**, and it undershot.
   It placed 2.0 near video 003 of playlist3 (2023-09-05). The true date is 2023-08-24 to
   2023-09-12 — the same fortnight.

**What is NOT solid, and must be said plainly:** the January course is the newest complete
*course*, but it is not the newest material we hold. Thirteen videos are newer, and where
they speak they still govern:

| Newer than the January course | Date | Words |
|---|---|---|
| `only_liquidity_guide.txt` — The ONLY Liquidity Guide | **2026-07-21** | 9,706 |
| `Trading_Psychology_9_Years.txt` | **2026-07-13** | 6,580 |
| `UPDATED_Day_Trading_Strategy_2026.txt` | **2026-06-05** | 10,615 |
| `full_tutorial_2026.txt` — How To Start Day Trading In 2026 | **2026-05-07** | **82,772** |
| `playlist3/120` I Took A Trader From Broke To Rich | 2026-04-20 | |
| five live-session recaps (`75210`, `48305`, `80k`, `103k`, `60630`) | 2026-04-06 to 04-17 | |
| `playlist3/119` The Mindset That Turned Me | 2026-02-16 | |
| `playlist3/118` 6 Rules From 6 Years | 2026-02-10 | |
| `playlist3/116` The ONLY Equilibrium Video | 2026-02-03 | |
| `playlist3/115` $1,000,000+ From One Simple Confluence (SMT) | 2026-01-27 | |

That matters repeatedly below, and every time it cuts the same way: **the February through
July 2026 videos agree with the January course and disagree with the November 2025 material
we built from.** There is no case in this document where the January course is overruled by
something newer. The 82,772-word May 2026 tutorial is the strongest single test of that,
because it re-teaches the whole method from scratch — and it contains the same narrow
confluence menu the January capstone gives.

---

## 1. THE DATED INDEX

Newest first. `#` is the `playlist3` file number where one exists.

| date | corpus | # | title |
|---|---|---|---|
| **2026-07-21** | standalone |  | The ONLY Liquidity Guide You’ll Ever Need |
| **2026-07-13** | standalone |  | 9 Years of Trading Psychology in 37 Minutes |
| **2026-06-05** | p2p / standalone |  | My UPDATED Day Trading Strategy (2026) |
| **2026-05-07** | standalone |  | How To Start Day Trading In 2026 [Full Tutorial] |
| **2026-04-20** | playlist3 | 120 | I Took A Trader From Broke To Rich In 30 Days |
| **2026-04-17** | standalone |  | $75,210 in One Day Trading Live (Full Breakdown) |
| **2026-04-16** | standalone |  | How I Turned One Setup Into $48,305 Live on Stream |
| **2026-04-08** | standalone |  | Learn From My $80K Mistake |
| **2026-04-07** | standalone |  | The Only Setup That Mattered Today ($103K) |
| **2026-04-06** | standalone |  | How I Pulled $60,630 From One Setup |
| **2026-02-16** | playlist3 | 119 | The Mindset That Turned Me From Unprofitable To Millionaire |
| **2026-02-10** | playlist3 | 118 | 6 Rules I've Learned From 6 Years of Trading |
| **2026-02-03** | playlist3 | 116 | The ONLY Equilibrium Video You’ll Ever Need |
| **2026-01-27** | playlist3 | 115 | $1,000,000+ From One Simple Confluence |
| **2026-01-17** | p2p / standalone |  | Path to Profitability: TJR's Strategy Explained |
| **2026-01-16** | p2p / standalone |  | Path to Profitability: Risk Management & Psychology |
| **2026-01-14** | p2p / standalone |  | Path to Profitability: How To Find Daily Bias |
| **2026-01-13** | path |  | Path to Profitability: Funded Accounts Explained |
| **2026-01-12** | p2p / standalone |  | Path to Profitability: Time Theory Explained |
| **2026-01-11** | p2p / standalone |  | Path to Profitability: SMT Divergence Explained |
| **2026-01-10** | p2p / standalone |  | Path to Profitability: Equilibrium Explained |
| **2026-01-09** | p2p / standalone |  | Path to Profitability: Inverse Fair Value Gaps Explained |
| **2026-01-08** | path |  | Path to Profitability: Advanced Imbalance Concepts |
| **2026-01-07** | p2p / standalone |  | Path to Profitability: Fair Value Gaps Explained |
| **2026-01-06** | p2p / standalone |  | Path to Profitability: Break of Structure Explained |
| **2026-01-05** | p2p / standalone |  | Advanced Liquidity Concepts (Path to Profitability) |
| **2026-01-04** | p2p / standalone |  | Path to Profitability: Liquidity Explained |
| **2026-01-03** | path |  | Path to Profitability: How to Read a Candlestick Chart |
| **2026-01-02** | path |  | Path to Profitability: What is Trading |
| **2026-01-01** | path |  | Path to Profitability: One Day or Day One |
| **2025-12-03** | playlist3 | 114 | Liquidity Is The Easiest Way To Become Profitable FAST |
| **2025-11-26** | playlist3 | 113 | 6 Years of Brutally Honest Trading Lessons For 2026 |
| **2025-11-04** | p2p / standalone | 112 | This Data-Backed Strategy Works Everyday (Stupid Simple And Proven) |
| **2025-10-28** | playlist3 | 111 | Live Day Trading Losing 80,450 (MY WORST TRADING MONTH EVER) |
| **2025-10-27** | playlist3 | 110 | Live Day Trading Losing 151,020 (DOWN 350K THIS MONTH) |
| **2025-10-23** | playlist3 | 109 | How To Pass A Funded Account In 2026 |
| **2025-10-22** | playlist3 | 108 | Live Day Trading Losing $234,060 (WORST TRADING DAY EVER) |
| **2025-10-20** | playlist3 | 107 | Easiest Way To Start Day Trading From Scratch (Exactly What I Did) |
| **2025-10-20** | playlist3 | 106 | Live Day Trading Making $67,180 (67?!) |
| **2025-10-15** | playlist3 | 105 | Live Day Trading Losing $152,060 (I MARRIED MY BIAS) |
| **2025-10-11** | playlist3 | 102 | $5,000,000 With Day Trading At 23 |
| **2025-10-09** | playlist3 | 103 | Live Day Trading Losing $52,660 (MADE DUMB MISTAKES) |
| **2025-10-08** | playlist3 | 101 | Live Day Trading Making $35,827 (HOW TO TAKE CONTINUATION TRADES) |
| **2025-10-07** | playlist3 | 100 | Live Day Trading Making $45,180 (HOW TO HIT FULL TAKE PROFITS) |
| **2025-10-06** | p2p / standalone | 099 | How I Made $1,047,984 In 6 Months Of Day Trading (Strategy Revealed) |
| **2025-10-01** | p2p / standalone | 098 | The ONLY Break Of Structure Video You’ll Ever Need |
| **2025-09-25** | playlist3 | 096 | How To Start Day Trading As A Beginner In 2026 (9 hours) |
| **2025-09-17** | p2p / standalone | 095 | The Stupid Simple Strategy That Makes Me $156,943/Month (Backtested Results) |
| **2025-09-04** | playlist3 | 094 | Brutally Honest Advice To My Younger Unprofitable Self |
| **2025-08-28** | playlist3 | 093 | 6 Years Of Trading Knowledge In 20 Minutes |
| **2025-08-11** | playlist3 | 092 | How I Reprogrammed My Mind to Make $5,000 Everyday |
| **2025-07-23** | playlist3 | 091 | 7 Trading Rules That Changed My Life |
| **2025-07-17** | playlist3 | 090 | How I Went From $0 to $20 Million at 23 |
| **2025-07-10** | playlist3 | 089 | +$1,000,000 From One Simple Strategy |
| **2025-06-30** | p2p / standalone | 088 | How To Find Daily Bias (Step By Step) |
| **2025-06-23** | playlist3 | 087 | How To Unf*ck Your Mindset (So Trading Becomes Easy) |
| **2025-06-16** | p2p / standalone | 086 | The ONLY Liquidity Sweeps Video You’ll Ever Need |
| **2025-06-10** | playlist3 | 085 | POV: You’re a 23 y/o Millionaire Entrepreneur in Miami |
| **2025-06-02** | playlist3 | 083 | Live Day Trading Making $0 (TODAY WAS BRUTAL) |
| **2025-05-26** | p2p / standalone | 082 | The Science Based Trading Strategy That Made Me $291,456 This Month |
| **2025-05-22** | playlist3 | 081 | Live Day Trading Making $0 (HOW TO TRADE CHOPPY PRICE ACTION) |
| **2025-05-21** | playlist3 | 080 | Live Day Trading Losing $3,650 (HOW TO KEEP LOSSES SMALL) |
| **2025-05-21** | playlist3 | 078 | Live Day Trading Making $18,541 (HOW TO MAKE WINS BIGGER THAN LOSSES) |
| **2025-05-19** | playlist3 | 077 | Live Day Trading Losing $8,720 (I TRADED AGAINST THE TREND) |
| **2025-05-16** | playlist3 | 076 | Live Day Trading Making $6,510 (I MADE 69K THIS WEEK) |
| **2025-05-15** | playlist3 | 075 | Live Day Trading Making $159,786 (EXPLAINING MY NEW STRATEGY) |
| **2025-05-15** | playlist3 | 074 | Live Day Trading Losing $97,220 (I GOT EMOTIONAL) |
| **2025-05-12** | playlist3 | 073 | Beginners Guide To Get Funded In 2026 |
| **2025-04-14** | playlist3 | 072 | This Simple Strategy Made Me My First $100k |
| **2025-04-08** | playlist3 | 071 | My Honest Thoughts On The $11 Trillion Dollar Market Crash (how to profit) |
| **2025-03-24** | playlist3 | 070 | How To Make 'F*ck You' Money With Day Trading |
| **2025-03-18** | playlist3 | 069 | Day Trading For Beginners: The Complete Starter Guide 2025 |
| **2025-03-07** | playlist3 | 068 | Beginners Guide To Start Day Trading In 2026 (5 hours) |
| **2025-02-26** | playlist3 | 067 | I Made $100K In A Day & Spent It All On A New Hellcat |
| **2025-02-20** | p2p / standalone | 066 | Order Flow Explained |
| **2025-02-17** | playlist3 | 065 | POV: You’re Flying To Miami As a 22 y/o Millionaire |
| **2025-02-12** | playlist3 | 064 | How To Start Day Trading With $0 |
| **2025-02-03** | playlist3 | 063 | Fair Value Gaps Explained |
| **2025-01-30** | playlist3 | 062 | POV: You’re a 22 y/o Millionaire In Miami For a Weekend |
| **2025-01-10** | playlist3 | 060 | Easiest Way To Start Day Trading in 2026 |
| **2025-01-01** | playlist3 | 059 | Brutally Honest Advice To My Younger Broke Self |
| **2024-11-19** | playlist3 | 058 | Break of Structure Explained |
| **2024-11-12** | playlist3 | 057 | POV: Day In The Life Of A Millionaire Day Trader In Miami |
| **2024-11-04** | playlist3 | 056 | Liquidity Sweeps Explained |
| **2024-10-22** | playlist3 | 054 | I Made $500,000 Day Trading & Spent It All On A Rolls Royce |
| **2024-10-14** | playlist3 | 052 | How To Start Day Trading In 2026 (Step by Step) |
| **2024-09-27** | playlist3 | 050 | Teaching My Friend How To Day Trade |
| **2024-08-15** | playlist3 | 048 | How To Become A Disciplined Trader |
| **2024-08-12** | playlist3 | 061 | pov: you’re a 22 y/o day trader making an average persons salary in a day |
| **2024-08-09** | playlist3 | 047 | How To Start Day Trading With Only $100 |
| **2024-08-01** | playlist3 | 046 | 16 Minutes of The Best Trading Advice |
| **2024-07-29** | playlist3 | 044 | DO NOT Trade Without This Confluence (SMT Divergence) |
| **2024-07-16** | playlist3 | 042 | How This 20 Year Old Trader Went From Unprofitable To $93k In 90 Days |
| **2024-06-24** | playlist3 | 040 | How I Turned $1k To $10k in Less Than A Week (LIVE TRADING) |
| **2024-06-12** | playlist3 | 038 | My Multi Millionaire Morning Routine |
| **2024-06-05** | playlist3 | 036 | How I Went From LOSING Thousands to Making MILLIONS in Day Trading |
| **2024-06-03** | playlist3 | 035 | Q&A with a Multi Million Dollar Day Trader |
| **2024-05-29** | playlist3 | 034 | The Truth about being a Day Trader in Your 20s |
| **2024-05-27** | playlist3 | 033 | How To Pass A Funded Account 101 |
| **2024-05-24** | playlist3 | 032 | Day in the Life of a Millionaire Day Trader (Realistic) |
| **2024-05-22** | playlist3 | 031 | How To Become an Emotionless Trader (this will turn you profitable) |
| **2024-05-20** | playlist3 | 030 | How I Would Start Day Trading With $0 |
| **2024-05-13** | playlist3 | 028 | Advice I Wish I Had When I Started Trading (Brutally Honest) |
| **2024-04-08** | playlist3 | 027 | What I Spend In A Month As A 21 Year Old Millionaire |
| **2024-04-01** | playlist3 | 026 | How I Went from -$2k in My Bank Account to $1 Million |
| **2024-03-19** | playlist3 | 025 | I Spent $60k On Suga Sean |
| **2024-03-15** | playlist3 | 024 | My $250K Closet Tour |
| **2024-03-11** | playlist3 | 023 | Day In The Life Of A 21 Year Old Millionaire |
| **2024-02-15** | playlist3 | 022 | A Realistic Day In The Life Of A Millionaire Day Trader |
| **2023-12-28** | playlist3 | 020 | Increase Your Win Rate Instantly |
| **2023-12-26** | playlist3 | 019 | How To Manifest Profitability |
| **2023-12-19** | playlist3 | 018 | Watch This Before Going All In To Trading |
| **2023-12-14** | playlist3 | 017 | How I Spend My 6 Figure Trading Profits |
| **2023-12-07** | playlist3 | 016 | 5 Things That Turned Me Into A Millionaire |
| **2023-12-05** | playlist3 | 015 | AI Is Taking Over Trading (Turn Profitable Before It's Too Late) |
| **2023-12-02** | playlist3 | 014 | Reprogram Your Mind To Be Profitable In 11 Steps! |
| **2023-11-30** | playlist3 | 013 | How To Become A 6 Figure Trader |
| **2023-11-28** | playlist3 | 012 | Banned Funded Account Strategy: How To Pass A Funded Account Every Time Pt. 3 |
| **2023-11-25** | playlist3 | 011 | Banned Funded Account Strategy: How To Pass A Funded Account Every Time Pt. 2 |
| **2023-11-23** | playlist3 | 010 | Banned Funded Account Strategy: How To Pass A Funded Account Every Time Pt. 1 |
| **2023-11-18** | playlist3 | 009 | How To Manage Your Time Like A Millionaire |
| **2023-11-16** | playlist3 | 008 | Interviewing Co-Founders of a $100 Million Dollar Business |
| **2023-11-11** | playlist3 | 007 | I Made $4,000 While Getting Tattooed?! |
| **2023-11-10** | playlist3 | 006 | This One Trading Skill Will Turn You Profitable |
| **2023-11-04** | playlist3 | 004 | Making $3,000 In A Lazy River |
| **2023-11-02** | playlist3 | 001 | How I Make $68k Working Only 2 Hours A Day |
| **2023-09-27** | playlist3 | 002 | Day in the Life of a Millionaire Trader |
| **2023-09-12** | bootcamp2 |  | Boot Camp 2.0 Day 13: I Made $ on a Bad Trade |
| **2023-09-11** | bootcamp2 |  | Boot Camp 2.0 Day 12: Red Day |
| **2023-09-08** | bootcamp2 |  | Boot Camp 2.0 Day 11: Where to Take Profit |
| **2023-09-07** | bootcamp2 |  | Boot Camp 2.0 Day 10: Trade Recaps |
| **2023-09-05** | playlist3 | 003 | My "New" Day Trading Strategy Revealed |
| **2023-09-05** | bootcamp2 |  | Boot Camp 2.0 Day 9: Leveraging Risk |
| **2023-08-31** | bootcamp2 |  | Boot Camp 2.0 Day 8: How to split positions |
| **2023-08-30** | bootcamp2 |  | Boot Camp 2.0 Day 7: Risk Management and Probabilities |
| **2023-08-29** | bootcamp2 |  | Boot Camp 2.0 Day 6: Best Loss to Take |
| **2023-08-28** | bootcamp2 |  | Boot Camp 2.0 Day 5: How to find Trade Bias |
| **2023-08-28** | bootcamp2 |  | Boot Camp 2.0 Day 5.5: Second Trade |
| **2023-08-26** | bootcamp2 |  | Boot Camp 2.0 Day 4: Best Forex Broker |
| **2023-08-25** | bootcamp2 |  | Boot Camp 2.0 Day 3: Risk |
| **2023-08-24** | bootcamp2 |  | Boot Camp 2.0 Day 2: How to handle emotions |
| **2023-08-24** | bootcamp2 |  | Boot Camp 2.0 |
| **2023-07-25** | bootcamp 1.0 |  | Boot Camp Day 55: THE END |
| **2023-07-06** | bootcamp 1.0 |  | Boot Camp Day 41: Learn from Losses |
| **2023-07-05** | bootcamp 1.0 |  | Boot Camp Day 40: Help me help you |
| **2023-07-04** | bootcamp 1.0 |  | Boot Camp Day 39: Calculating Lot Size |
| **2023-06-29** | bootcamp 1.0 |  | Boot Camp Day 34: Daily Bias |
| **2023-06-24** | bootcamp 1.0 |  | Boot Camp Day 29: Trading Plan |
| **2023-06-07** | bootcamp 1.0 |  | Boot Camp Day 13: Risk Management |
| **2023-05-26** | bootcamp 1.0 |  | Boot Camp Day 1: Take Action |

*150 videos dated.*

---

## 2. RULES WE BUILT FROM A SOURCE NOW KNOWN TO BE OLDER

Seven of them. For each: what we run, where it actually came from, that source's real
date, and what the newer teaching says.

### 2.1 Position size is set off the tightest stop and then held still — even when the stop widens

**What we run.** `tjr_bot.py` `size_position()` (line 2192). The docstring quotes the
whiteboard lesson and the rule is stated in `step436` §7 as four numbered steps, of which
step 3 is: *"**Hold that size.** A wider stop that day therefore risks 2% or 3%. Do not
resize down."*

**Where it came from.** Boot Camp Day 39, "Calculating Lot Size" — **2023-07-04**.

**What the newer source says.** Risk Management & Psychology, **2026-01-16**. He confirms
the set-size half and then adds an exception the 2023 lesson does not contain:

> "I would like to preface one thing. If I do have — there's a couple times when I change
> the contract size. So, one time is **if the stop-loss is like very drastically larger
> than usual, then I'm going to just cut the contract size in half.**"

**CONTRADICTS.** Our step 3 says never resize down. His current teaching says cut it in
half when today's stop is drastically wider than normal. `size_position()` already computes
exactly the quantity this needs — it returns `wider`, the ratio of today's stop to the
stop the size was calibrated on — and then does nothing with it.

**Also from the same video, the calibration is two-sided and ours is one-sided.** We take
the narrowest stop the instrument gives and size so that stop costs 1% of the account. He
sizes off the tight stop and then *checks the wide one before accepting the number*:

> "what's my typical stop-loss size? So on this trade that I took today ... my stop-loss
> size on ES was around 16 ticks ... And then I can look back to another short position ...
> on this trade, it was 34 ticks. And then on another trade, it was like 28 ticks. So, I can
> say, okay, on this trade, we had a relatively tight stop-loss. So on this position, you
> know, we're going to be risking whatever, three contracts ... And then if I'm risking three
> contracts on this, **how much am I going to lose when it hits a 35 tick stop-loss? And then
> as long as I'm comfortable with both of those numbers** ..."

Three real numbers, 16 / 28 / 34 ticks, and the acceptance test is on the pair.

### 2.2 The 1%-to-3% band is a budget for the DAY

**What we run.** `tjr_alerts.py` `MAX_DAY_RISK_SHARE_OF_ACCOUNT = 0.03`, enforced across
the day by `tjr_bot.DayBudget`. Renamed from a per-trade cap on 2026-07-26 specifically
because Boot Camp 2.0 was read as the newer source.

**Where it came from.** Boot Camp 2.0 Day 8, "How to split positions" — **2023-08-31**.

**What the newer source says.** Risk Management & Psychology, **2026-01-16**. The band is
back on the trade, and the top of it is soft:

> "Usually the sweet spot is anywhere between like **1 to 3%**."

> "us going up to, you know, 35 ticks, that **could potentially be risking like 3 or 4% of
> the account, but I'm willing to do that** because again, if I'm risking 3 to 4% of the
> account and then I'm only getting like a 1:1 risk-to-reward ratio, you know, I'm still
> able to get a 3% gain on this and then if I lose, doesn't really matter that much."

Every one of those is a share of the **account** lost if the stop is hit, not a move in the
price.

**CONTRADICTS, on the axis.** In the 2026 lesson the words "on the day" never appear, and
neither does a day budget of any kind. One trade at 3-4% of the account is stated as
acceptable. Our day ceiling of 3% would refuse that trade outright on a wide-stop morning.

### 2.3 Half the day's budget on the first trade, released back at break-even

**What we run.** `tjr_bot.DayBudget` — the first trade takes half the day's budget when a
second setup looks plausible, and a trade whose stop has moved to break-even after target 1
stops consuming budget.

**Where it came from.** Boot Camp 2.0 Day 8 and Day 9 — **2023-08-31** and **2023-09-05**.
`step452` §4 calls it "THE BIGGEST FILL IN THIS COURSE."

**What the newer source says.** Nothing. The 2026-01-16 risk lesson has no budget, no
splitting, no release-at-break-even, and no mention of taking more than one trade.

**Not a contradiction — an absence.** The mechanism is not disproven, it is unsupported by
anything newer than 2023. It is the single largest piece of machinery in the bot resting
entirely on the oldest layer of the corpus, and that is worth knowing before it is defended
again.

### 2.4 Daily bias comes from classifying what London did

**What we run.** `tjr_bot.py` `london_profile()` (line 1115) and `build_context()` — the
three daily profiles (`consolidation` / `manipulation` / `manipulation_reversal`), with the
direction taken from which one fired.

**Where it came from.** `How_To_Find_Daily_Bias_Step_By_Step.txt` — **2025-06-30**.
`step434` §1A calls it "current, primary"; `step436` §10 calls it "the current taught
method."

**What the newer source says.** How To Find Daily Bias, **2026-01-14**, is 6½ months newer
and teaches something else entirely. Word counts, whole transcript:

| term | 2025-06-30 lesson | 2026-01-14 lesson |
|---|---|---|
| "daily profile" | 20 | **0** |
| "consolidation" | 12 | **0** |

It is also absent from the newest video we hold, `UPDATED_Day_Trading_Strategy_2026`
(2026-06-05): zero occurrences of "profile" or "consolidat".

**CONTRADICTS.** Full replacement procedure in §3.2.

### 2.5 The daily and the 4-hour must agree or the day stands down

**What we run.** `build_context()` computes `daily_dir` and `h4_dir` and requires agreement.

**Where it came from.** Boot Camp Days 34-36 — Day 34 is **2023-06-29** — reinforced by the
live mornings in the same 2023 course. `step436` §10 kept it as a veto on top of the
profile method, reasoning that "it only ever REMOVES trades."

**What the newer source says.** On 2026-01-14 he hits exactly this conflict and **resolves
it instead of standing down**:

> "high time frame, what are we in? We are in an uptrend, believe it or not, right? We have
> a high, then we have a higher high. And you're probably saying, 'Oh, well, no, we made a
> lower low.' Well, that is the case. We did make a lower low. However, **this low is
> actually coming down and it's sweeping out this low right here. And on top of that, we
> are yet to break structure to the downside.**"

That is the two rules he actually applies: a low that swept a prior low is a liquidity
event, not a trend change; and trend only flips on a body close through the tracked swing.
Neither is "stand down."

**CONTRADICTS.** The veto is 2023 material with no support in anything from 2026.

### 2.6 The step-2 confirmation menu has four options

**What we run.** `tjr_bot.py` `on_5m` (line 1723) and `on_1m` (line 1878) — break of
structure, gap inversion, 79% extension close, SMT divergence. Built in `step456` §3.

**Where it came from.** `playlist3/112`, "This Data-Backed Strategy Works Everyday" —
**2025-11-04**. Along with it came step 2B (`require_fresh_5m_sweep_after_open`) and the
continuation-invalidation rule (`invalidate_on_close_beyond_continuation`).

**What the newer sources say.** Three of them, all newer, all giving **two**:

- Inverse Fair Value Gaps, **2026-01-09**: *"So, now we know two confirmation confluences.
  We have break of structure and inverse fair value gaps. And right now we have one
  continuation confluence which is fair value gaps."*
- TJR's Strategy Explained, **2026-01-17**: *"the change in order flow or the change in
  structure could have been seen in two ways, either via break of structure or an inverse
  fair value gap."*
- The ONLY Equilibrium Video, **2026-02-03**: *"we can scale down to a lower time frame and
  we can see a change in order flow on that, whether it's a break of structure or an inverse
  fair value gap."*

**The 79% extension appears nowhere in any of them.** Every occurrence of the string "79"
was checked by hand across everything newer than 2025-11-04: all sixteen January videos,
`playlist3` 114-120, the 2026-06-05 strategy video, the 2026-07-21 liquidity guide, and the
**82,772-word** May 2026 full tutorial. The only hits anywhere are dollar amounts — a $79
challenge fee and a $279 reset fee in the funded-account section. **Its newest genuine
appearance in the whole corpus is 2025-11-04.**

**CONTRADICTS by absence**, which is weaker evidence than a retirement sentence and is
labelled as such. But it is absence across roughly thirty consecutive newer videos including
**three** that re-teach the confirmation step from scratch — the January capstone, the
February equilibrium video, and an eight-hour tutorial. `step456` §5 also already measured
`smt_in_confirmation_menu` as the worst switch of the seven (48.1% win rate, −$2,016 against
a −$1,067 baseline, +8 trades).

### 2.7 News is handled by release time relative to the open

**What we run.** `news_calendar.py` `derisks()` / `blocks()`, and `step452` §6's proposed
refinement to split by clock time.

**Where it came from.** Boot Camp 2.0 Days 5, 7 and 13 — **2023-08-28** to **2023-09-12**.

**What the newer sources say.** Two things, and they point in different directions from
each other.

Risk Management & Psychology, **2026-01-16** — the response is a size cut, not a stand-down:

> "if we look and we see, hey, today there's — there was PPI news data. So the market is
> going to be a little bit more choppy and I'm not so sure about how the market's looking
> today ... **I'm just going to cut my contract size in half.**"

Advanced Liquidity Concepts, **2026-01-05** — news candles are *levels to trade*, which we
do not compute at all:

> "the highs of the news candles and the lows of the news candles are very very beneficial
> for us and serve as high probability draws in liquidity ... We would mark out the high and
> the low of the news data candle."

**REFINES.** The half-size response is confirmed and is what we already do. The stand-down
half has no 2026 support, and a whole level type is missing.

---

## 3. DELTAS FROM THE JANUARY 2026 COURSE

Read in his order, 1 through 16. Everything already correct in `step431`-`step457` is
omitted. Each item is marked CONFIRMS, REFINES or CONTRADICTS.

### 3.1 Risk Management & Psychology — 2026-01-16 (slot 15)

**a. The set size, confirmed and now dated 2026.** — **CONFIRMS**

> "for my risk management, like I used to do the whole thing of like calculate 1% of your
> balance and then I'm going to only risk 1% of my account balance per trade ... but I
> moved away from doing like, hey, I'm going to be risking only 1% of my account balance
> per trade, and **I just went to I'm going to risk this amount of contracts per trade.**"

`step436` §7's reversed resolution — build the fixed size, not the recompute-every-trade
size — was the right call and is now supported by 2026 material rather than 2023 material.
Wallace's instruction that produced that reversal was correct.

**b. The size is per instrument and stated as such.** — **CONFIRMS**

> "whenever I press buy, whenever I press sell, it's going to be the same amount of
> contracts for NASDAQ and then I have the number of contracts on ES that I'm going to be
> using."

Two instruments, two separate set sizes. `size_position()`'s per-instrument
`tightest_stop_pct` is right.

**c. Cut the size in half when the stop is drastically wider than usual.** — **CONTRADICTS**
(quote in §2.1). This is new machinery, not a tuning change.

**d. 1-3% per trade, 3-4% tolerated.** — **CONTRADICTS** (quotes in §2.2).

**e. Sub-1% is practice, not a trade.** — **REFINES**

Boot Camp 2.0 Day 3 said *"anything lower than a one percent trade I'm like all right, like
we're just doing this to get reps in."* The 2026 lesson keeps a hard floor on the other
side and names the failure it prevents:

> "that doesn't mean you're risking 10% of your account balance per trade. That doesn't mean
> you're risking freaking 20% ... That doesn't mean that you're risking 5% of your account
> balance."

5% of the account on one trade is explicitly out. Our day cap of 3% enforces something
stricter than that; his own stated ceiling for a single trade is nearer 4%.

**f. Psychology is not a mechanism.** — **CONFIRMS**

> "psychology is literally just discipline ... It's the discipline to be able to stick to
> your strategy. Only take trades when your strategy presents itself and stick to your risk
> management plan."

There is no stand-down rule, no loss-streak rule and no red-day rule anywhere in the 2026
risk lesson. Our `losing_weeks_to_escalate = 2` survives untouched, and is now known to rest
on Boot Camp Day 41, **2023-07-06**, with nothing newer either way.

**g. Prop-firm risk is per-firm and cannot be generalised.** — **REFINES**

> "every single prop firm is going to be very, very different when it comes to using correct
> risk management. So, you're just going to have to look ... yourself at the rules on what
> account you are trading on."

Relevant only if a funded account is ever put behind this bot. Real numbers from the funded
lesson (2026-01-13) are in §3.7.

### 3.2 How To Find Daily Bias — 2026-01-14 (slot 14)

This is the largest single delta in the document. The procedure is four steps and none of
them is a session profile.

**Step 1 — the high-timeframe trend, from the swing sequence.**

> "What are we in? We are in an obvious downtrend, right? We are making a high, then a low,
> lower high, lower low, lower high, lower low ... So, what did we expect coming into market
> open? We were probably going to deliver a lower low."

**Step 2 — where the unswept draws are stacked.**

> "why did we assume that we were going to deliver a lower low? We have all of this low
> resistance draws and liquidity stacked up. We have a low right here, a low right here ...
> A whole bunch of lows all stacked up throughout here."

**Step 3 — the bias is the two together.**

> "coming into today, my bias was bearish. Why? **Because on the high time frame, we had a
> whole bunch of draws and liquidity to the downside. And on the high time frame, we were
> forming a downtrend.**"

**Step 4 — the high-timeframe continuation confluence is a live test, and it can flip the
bias.** This is the part with no counterpart in our code at all. He marks the hourly or
4-hour fair value gap that the trend has to respect, and then watches it:

> "on the hourly time frame, we were coming into this hourly fair value gap. So, awesome. If
> this is going to continue being a downtrend, I am going to safely assume — or we need to
> see price come into this fair value gap and respect it. If that gets respected, where is
> price going to draw? Down to all of these high time frame, low resistance draws and
> liquidity."

and the flip:

> "we disrespect this fair value gap, which means to me, hey, we're probably no longer going
> to be in bearish price action. Because if we were going to be in bearish price action, we
> would have respected this gap and we would have continued lower ... **It closed above this
> gap, signaling to me, hey, price wants to go higher.**"

**REFINES into CONTRADICTS: the bias is revisable intraday, and the targets move with it.**
Stated in the plainest possible way:

> "if price invalidates this gap, what then am I going to be targeting for the day? I'm going
> to be targeting this low, this low, this low, right? **even though my bias is bullish.**"

And the capstone two days later says the same thing about the whole morning's read:

> "you're probably saying, 'I thought you had a bullish bias going into the day.' Yes, that's
> correct. I did have a bullish bias today, but what did the market do? **The market proved
> me wrong** and instead did what it wanted to do ... **We can let the market prove us wrong
> and we can still make money.**"

Our bot fixes the bias before 09:30 in `build_context()` and gates every entry on it for the
rest of the day. He does not. A pre-open read that the market invalidates costs him nothing
and costs us the session.

**The market model underneath it, which is worth having because it explains the rest.**

> "how does a trend move? It moves from boom high. Okay. Down to fair value gap equilibrium.
> Then back up to what? High ... **It moves from external to internal. External to internal.**"

External = highs and lows. Internal = gaps and equilibrium. Advanced Liquidity Concepts
(2026-01-05) says it as a target taxonomy: *"price is always either looking to take out
external liquidity, which is highs and lows, or fill imbalances, which is internal
liquidity."*

### 3.3 TJR's Strategy Explained — 2026-01-17 (slot 16, the capstone)

**a. The strategy is four stages, and he states it four times in one video.** — **CONFIRMS**
our `SeqState` shape, **CONTRADICTS** the widened menu.

> "We need the opportunity to fill orders. We need confirmation that that opportunity was
> actually taken by seeing orders get filled through **a change in structure via break of
> structure or an inverse fair value gap.** From there, I want to see a continuation of the
> new trend that is formed off the orders getting filled **via equilibrium or fair value
> gap.** And then from there, I want to exit the position where we are going to be able to
> liquidate the orders that were filled."

Two confirmation options. Two continuation options. That is the whole menu.

**b. The 1-minute stage is an OPTIONAL better entry, not a required gate.** — **REFINES**

> "you can wait for one of two options here. **You can either wait for just the following
> 5-minute candle to close bearish** to prove like, hey, we filled this continuation
> confluence and the market is showing that we want to move down off of this. **Or you can do
> what I do** and what the majority of other people do is you can scale down to the 1-minute
> time frame."

His reason is entry price, quantified on the chart:

> "notice this is going to be a lot better entry than if we wait for the next 5-minute
> candlestick to close ... while my take profit one is getting hit, you guys are just now
> entering."

Our `on_1m` trigger is mandatory. In his own words the 5-minute close is a legitimate
alternative. That is a route we do not have, and it can only add trades — worth knowing
given `step456` §5's finding that this bot trades roughly a third as often as he does.

**c. Do not press buy on the touch. Wait for the reaction out of it.** — **CONFIRMS**

> "it's one thing just for price to push into equilibrium, but price easily could have just
> gone all the way up. Right? So, if we just press sell right when equilibrium gets pushed
> into, then why do we even draw equilibrium in the first place?"

**d. He states, unprompted, that a rigid step-by-step is the wrong shape for this.** —
worth recording, not actionable.

> "if we wanted to just make some sort of trading bot that automated our strategy, that ...
> gave us like 100% profitable results over a long period of time, then awesome. Everybody
> would be able to get rich."

> "there might be one day where I, instead of scaling down to the 5-minute, I scale down to
> the 1-minute and I try and take a lower time frame trade. Or instead of waiting for this
> confirmation, I wait for another confirmation."

Not a reason to stop building. It is a reason to expect his real trade count to sit above
any fixed rule set's, and it is a second explanation for the gap `step456` §5 flagged.

### 3.4 Time Theory — 2026-01-12 (slot 12)

Everything in `Instrument` (lines 100-150) checks out against this video, and the video is
now the newest source for it. — **CONFIRMS**

| our field | his words, 2026-01-12 |
|---|---|
| `open_t = 09:30` | "we have open, right, which is at 9:30 a.m. Eastern time" |
| `manip_end_t = 09:50` | "our manipulation time frame, which is from 9:30 to 9:50" |
| `entry_ideal_end_t = 10:10` | "from 9:50 to 10:10, we have our entry period ... That's called the macro" |
| `cutoff_t = 10:30` | "if I can't find a trade by 10:30, I'm done for the day, because that's when the market tends to slow down" |
| Asia 18:00-03:00 | "Asian session ... starts at 1800, and it goes till 3:00" |
| London 03:00-08:30 | "London session goes from 3:00 till 8:30 ... we want to end all of these sessions when the next one is opening" |
| New York 08:30-17:00 | "from 8:30, which is pre-market, to 9:30, which is market open ... And then, we go from 9:30 all the way to 1700" |

The 10:30 cut-off is independently restated in the newest video of all,
`UPDATED_Day_Trading_Strategy_2026` (2026-06-05): *"By 10:30, I'm done for the freaking
day."*

**One thing we do not have.** — **REFINES**

> "the gap between 1700 and 1800 is what we call **spread hour**, where there is no market
> that is open ... you will see the spreads on every single pair get very, very large."

Nothing in the bot avoids 17:00-18:00 New York. It does not bind on the US index path,
which is flat long before then. It does bind on the 24-hour crypto path, where
`tjr_crypto.py` has no clock at all by design.

**And one soft edge worth honouring.** — **REFINES**

> "this doesn't have to be point-blank period, like we can only look to enter at 9:50 to
> 10:10. That's not the case. **I take trades at 10:20 sometimes. I take trades at 9:45
> sometimes.**"

`manip_end_t` is currently a hard floor at 09:50. He goes earlier.

### 3.5 SMT Divergence — 2026-01-11 (slot 11)

**a. Leading vs lagging, and it is the leading chart that gets the order.** — **CONFIRMS**
`step456` §1.6 and `smt_picks_the_instrument`.

> "it's the leading index in the downward move **because it's making a lower high** ... Why
> is it lagging? because it's continuing the uptrend."

> "I'm going to want to be taking the trade on the leading index ... I want to be taking the
> trade on the index that is leading the charge and not the one that's behind."

**Leading = the chart that FAILED to extend.** Same test `step456` coded.

**b. It must sit on a liquidity sweep or it is noise.** — **CONFIRMS** `SymbolDay.smt_live()`.

> "outside of sweeping out draws and liquidity, these things will show up all the time and
> will be pretty much like useless to us."

**c. The two swing points must be simultaneous.** — **CONFIRMS**, and tightens.

> "this high was formed at the same time that this one was, but then this one forms a higher
> high at the same time that this lower high was getting formed."

He times them to the same bar. `smt_alignment_bars = 2` is ours and is documented as a
guess; the newest source still says same-bar.

**d. Which instruments — and one thing we asserted that he does not say.** — **REFINES**

> "for the **Forex and Commodities** people, unfortunately, this is not going to be as
> beneficial for you guys because this is specifically talking about the divergence between
> the S&P 500 and the NASDAQ."

The 2026-01-11 lesson excludes forex and commodities. **It never mentions crypto, Bitcoin,
Ethereum, gold or silver.** `step456` §1.2 pins crypto's SMT switches off citing
`playlist3/044`, which is **2024-07-29**. That is fine — the structural block in `run_pair`
means a divergence cannot form on a crypto run anyway — but the citation should not be
described as his current word on crypto, because he has not given one.

**e. On whether SMT can trigger an entry, he hedges, and the capstone does not.** —
**REFINES**

The SMT lesson itself leaves a door open: *"this is a good example of how you could look for
an entry or potentially use it as a confluence"* — immediately undercut by *"**even though my
strategy doesn't show up here**"*. Six days later the capstone uses SMT purely as a bias
input and a chart chooser:

> "we had a bearish SMT divergence, so **that strengthens my bearish bias**."
> "I'm going to want to focus my targets on the S&P 500 ... **Because it's the leading
> index.**"

So `smt_enabled` and `smt_picks_the_instrument` are confirmed by the newest course.
`smt_in_confirmation_menu` is not — it came from `playlist3/112` (2025-11-04) and 103.

**f. No completion rule here — but the completion rule survives anyway.** `SwingLog.completion_target()`
was built from `playlist3/115`, which dates to **2026-01-27**, ten days *after* the course.
It is the newest word on SMT we hold. Leave it alone.

### 3.6 Equilibrium — 2026-01-10 (slot 10), plus 2026-02-03

**a. Most recent swing low to most recent swing high, and nothing else.** — **CONFIRMS**
`step436` §6.

> "The most recent low to the most recent high. If there's a low right here that's connected
> to this high, do we draw equilibrium from this low up to this high? **No. No. No, we
> don't.**"

**b. A wick touch is enough. He never says "close."** — **REFINES**

Every worked example is penetration:

> "We come down, poke our head underneath the discounted price range. Now, we're getting
> continuation higher."
> "we made equal lows right here with the equilibrium. But regardless on this candlestick, we
> end up pushing right underneath the equilibrium."

The word "close" does not appear once in relation to equilibrium in the 2026-01-10
transcript. If our pullback stage tests a close beyond equilibrium anywhere, it is stricter
than he is. Note the asymmetry, which he is consistent about: **break of structure and gap
inversion need a body close; equilibrium and a fair value gap are entered on a touch.**

**c. Order blocks and breaker blocks: retired, and the retirement is now dated.** —
**CONFIRMS** `step436` §1.

The quote `step436` built on is from `playlist3/116`, **2026-02-03** — newer than the whole
January course and the newest statement on it in the corpus:

> "I no longer use order blocks. I no longer use breaker blocks. The only continuation
> confluences that I need and that I use are equilibrium and fair value gaps."

Independent confirmation: **zero** occurrences of "order block", "breaker block",
"prominent" or "accumulation" across all sixteen January videos.

**And a second nail in "prominent high".** `step452` PART D flagged it as load-bearing and
NEEDS VIDEO; `step454` §0.2 traced it to video 003 alone and said do not build it. The
January course, which re-teaches liquidity and structure from nothing across five videos,
never uses the word. That is the third confirmation. It stays dead.

### 3.7 The rest of the toolkit — mostly CONFIRMS, with four real refinements

**Break of Structure, 2026-01-06.** — **CONFIRMS**, with one precision we should check.

> "We need the candle body to close underneath **the lowest point of the most recent low**."

The comparison is body close against the pivot's **wick**, and equality does not count — he
walks a case where the body sits exactly level with the low and rules it out. Also: in an
uptrend only lows are tracked. *"We're still in an uptrend even though we end up making a
lower high and a lower low."*

**Fair Value Gaps, 2026-01-07.** — **CONFIRMS** `step436` §5 exactly: three candles, boxed
between wick of the first and wick of the third, only the middle candle's colour matters,
overlapping wicks means no gap, killed by a body close through it and never by a wick, never
dragged forward. One addition:

> "once we push above the high in a bullish scenario, then we no longer need to have these
> fair value gaps on our chart."

A whole stack expires together once price makes a new extreme past it — including members
that were never touched.

**Inverse Fair Value Gaps, 2026-01-09.** — **CONFIRMS** the bottom-gap rule and quantifies
it again:

> "It's going to be the **bottom** fair value gap when we are looking for inverses to the
> downside ... because this is the last fair value gap that is holding up the trend."

> "That's an extra 68 ticks." / "That's 123 ticks that we literally are chopping off."

And ranks it above break of structure by frequency: *"I use this confluence almost every
single day almost more than break of structure because more often than not it happens
before break of structure even does."*

**Advanced Liquidity Concepts, 2026-01-05.** — **REFINES**. Seven named tiers of draw, and
we compute four of them. Missing:

1. **News-data candle highs and lows.** *"We would mark out the high and the low of the news
   data candle."* Sourced from Forex Factory red folders — the same feed `news_calendar.py`
   already reads, used today only to stand down.
2. **Relative equal highs and lows**, with the only numeric tolerance he ever gives:
   *"Literally 50 cents apart"* on the S&P. Ranked above a lone pivot because
   *"there's four times the amount of buy orders."*
3. **Previous day high and low defined as an 18:00-to-18:00 block**, not a calendar day:
   *"we're looking at all of those sessions combined, finding the highest point and the
   lowest point of all three of those sessions combined."*

**Advanced Imbalance Concepts, 2026-01-08.** — **REFINES**, and settles one open NEEDS VIDEO
while creating a smaller one. `step454` §2.2 filed new-day / new-week opening gaps as
unbuildable because their construction was unknown. It is stated:

- New day opening gap = the skipped 17:00-18:00 hour. *"the daily candle closed right here
  at 1700 and then the new day candle opened up here at 1800."*
- New week opening gap = Friday close to Sunday open, and he prefers it: *"typically the new
  week opening gaps are going to be a little bit larger."*
- **New candle opening gaps: explicitly binned.** *"it's [expletive] useless ... you're never
  going to use it again."* Do not build.
- He also warns the day gap is an Asia-session fill: *"this is during Asian session. So, I'm
  really never looking for these trades to be taken."*

`step454` §2.3's "imbalanced price range" is also defined — he calls it a BPR: *"a swift move
up through imbalanced price action and then a swift move down through imbalanced price
action ... we can just identify this entire range as imbalanced price."* Still NEEDS VIDEO
for the exact overlap boundaries.

**Funded Accounts, 2026-01-13.** Not a strategy lesson. Recorded because the numbers are
concrete and this bot may end up on a funded account: 8% profit target on $100k, $3,500 max
drawdown measured on equity or balance, 10 contracts maximum per trade, minimum 2 trading
days, 50% consistency rule (no more than half the profit from one trade, so ≥3 winners),
holding through news permitted.

---

## 4. THE ORDER ITSELF — `HIS_TEACHING_ORDER.md` confirmed, one inference corrected

The sixteen-step order it reconstructed is **exactly right**, and the upload dates prove it
independently of the playlist's display order. Nothing to correct in the sequence.

Its inference about daily bias is wrong, and he says why in his own words.

`HIS_TEACHING_ORDER.md` currently reads:

> "**Daily bias is 14th, nearly last.** He teaches the whole toolkit BEFORE teaching which
> way to lean. Our bot computes bias first and gates everything on it. Not necessarily wrong,
> but worth knowing the reading order is the reverse."

He opens the bias video with the opposite claim:

> "**I want to cover daily bias first because without daily bias, you don't know where the
> market's going to go.** So, how are you going to be able to look for an entry? ... if that's
> the case, then why the [expletive] are we entering in the first place if we don't know where
> the market wants to go?"

and the risk video with the matching one:

> "**So that's why we're doing risk management before strategy.**"

So the real shape is **tools (1-13) → bias (14) → risk (15) → assembly (16)**, and 14 and 15
are placed *immediately before* execution deliberately, because he considers both
prerequisites to it. Bias first is his order, not ours. The bot computing bias before
anything else is **CONFIRMED**, not contrary.

What the order does still tell us, and this part of the file stands: liquidity precedes
structure, structure precedes the gaps, SMT sits late at 11, and the strategy is a synthesis
of the twelve pieces rather than a thing that stands alone.

**One correction to make in the file itself:** it lists "Funded Accounts Explained" at slot
13 with no date, and lists SMT at 11 and Time Theory at 12 — all correct. The only edit
needed is the daily-bias paragraph above, plus a note that there is no 2026-01-15 video.

---

## 5. CODE CHANGES, IN PRIORITY ORDER

Nothing below was built. No bot file was opened for writing, no test was run, no order was
placed, no git command was issued.

Ordered by what it costs to have wrong, not by effort.

### 1. `tjr_bot.py` `build_context()` (lines 1273-1290) and `london_profile()` (line 1115)

**Replaces:** daily bias computed from the three London session profiles
(`consolidation` / `manipulation` / `manipulation_reversal`), fixed before 09:30 and used to
gate every entry for the day.

**With:** the 2026-01-14 procedure. Bias = high-timeframe trend state (which
`TrendTracker` already gives) plus the side carrying the stacked unswept draws (which
`_unswept()` already gives). Then mark the higher-timeframe continuation confluence the
trend has to respect, and **re-read the bias when a body closes through it.**

Source: How To Find Daily Bias, 2026-01-14, quoted in §3.2. This retires `london_profile()`
and the 2025-06-30 lesson it came from.

**The riskiest change in the list**, because bias feeds everything downstream — but it is
also the one where our source is furthest out of date, and the current method survives in
zero videos after 2025-06-30.

### 2. `tjr_bot.py` — the bias must be allowed to flip intraday

**Replaces:** `DayContext` set once before the open and never revised, with entries gated on
it for the whole session.

**With:** a bias that inverts when the higher-timeframe gap holding the trend is closed
through, and targets that move with it. Source: 2026-01-14, *"even though my bias is
bullish"*; capstone 2026-01-17, *"The market proved me wrong ... We can let the market prove
us wrong and we can still make money."*

Separate from change 1 on purpose. Change 1 alters how the morning read is formed; this one
alters whether the read is binding. Either is testable without the other.

### 3. `tjr_bot.py` `Config` — retire `extension_79_enabled` and `smt_in_confirmation_menu`

**Replaces:** a four-option confirmation menu on both the 5-minute (line 1723) and the
1-minute (line 1878).

**With:** the two he names in every 2026 source — break of structure and inverse fair value
gap. Source: 2026-01-09, 2026-01-17 and 2026-02-03, quoted in §2.6.

Both ship `False` today, so this is a documentation-and-deletion change, not a behaviour
change. It matters because `Config.newest_teaching()` turns them **on**, and that constructor
is named for a claim the dates no longer support.

`smt_enabled` and `smt_picks_the_instrument` stay. They are confirmed by 2026-01-11 and by
the capstone.

### 4. `tjr_bot.py` `size_position()` (line 2192) — halve the size on a drastically wider stop

**Replaces:** step 3 of `step436` §7, *"Hold that size. Do not resize down."*

**With:** cut the contract count in half when today's stop is drastically wider than the one
the size was calibrated on. Source: 2026-01-16, *"if the stop-loss is like very drastically
larger than usual, then I'm going to just cut the contract size in half."*

The function already computes the trigger quantity — `wider`, today's stop over the baseline
stop — and currently only reports it. **"Drastically" is not a number he gives: NEEDS
VIDEO**, or a swept threshold. Do not invent one quietly; make it a named `Config` field
marked OURS, the way `smt_alignment_bars` is.

### 5. `tjr_bot.py` `Config.max_day_risk_share` / `tjr_alerts.MAX_DAY_RISK_SHARE_OF_ACCOUNT`

**Replaces:** 3% of the account as a ceiling on the DAY, from Boot Camp 2.0 (2023-08-31).

**With:** a decision, because the two sources genuinely conflict and both are his. The 2023
lesson puts 1-3% on the day; the 2026-01-16 lesson puts 1-3% on the trade and accepts 3-4%.
Newer-governs says the trade. **This is a profitability-affecting change and should be gated
on Wallace before it is built.**

Recommended shape either way: keep the day ledger, raise the per-trade allowance to his
stated band, and record which source each number came from in the field comment.

### 6. `tjr_bot.py` `session_levels()` — three missing draw types

**Adds** (does not replace anything). Source: Advanced Liquidity Concepts, 2026-01-05, §3.7.

- News-data candle high and low. The calendar feed is already wired for the stand-down
  path; this uses the same events as levels.
- Relative equal highs and lows, tolerance stated as ~50 cents on the S&P — **his only
  numeric tolerance anywhere**, and it needs re-deriving per instrument the way stop floors
  are, never ported.
- Previous day high and low measured 18:00-to-18:00 New York rather than calendar day.

Also from 2026-01-08: new day opening gap (17:00-18:00 skip) and new week opening gap
(Friday close to Sunday open). Both now have a stated construction, which closes
`step454` §2.2's NEEDS VIDEO. New *candle* opening gaps: he bins them by name — do not build.

### 7. `tjr_bot.py` `on_5m` — add the 5-minute-close entry route

**Adds:** the alternative he names, where the confirmation is the next 5-minute candle
closing in the trade's direction out of the continuation confluence, instead of a 1-minute
trigger. Source: capstone 2026-01-17, *"you can either wait for just the following 5-minute
candle to close bearish ... or you can do what I do."*

It can only add trades, and `step456` §5 found this bot trading roughly a third as often as
he does. Worth measuring for that reason alone. Ship it off, like everything in `step456`.

### 8. `tjr_bot.py` — equilibrium on a touch, not a close

**Check first, then change if needed.** The 2026-01-10 lesson never uses the word "close"
about equilibrium; every example is a wick poke. If the pullback stage requires a close
beyond equilibrium anywhere, it is stricter than he is and is costing trades. Break of
structure and gap inversion keep the body-close test — he is deliberately asymmetric.

### 9. `Instrument` — soften the 09:50 floor, add spread hour

**Adds:** he takes trades at 09:45 (*"I take trades at 9:45 sometimes"*), so `manip_end_t` as
a hard floor is stricter than his practice. And 17:00-18:00 New York is a no-trade window on
spread grounds — irrelevant to the index path, live on the crypto path.

Lowest priority in the list, and the smallest.

### 10. Documentation, no code

- `step452` line 8: *"Boot Camp 2.0 is the newer teaching"* — **false.** August-September
  2023.
- `step436` §10: the daily-bias resolution rests on a 2025-06-30 source that nothing after
  it repeats. Superseded by §3.2 above.
- `step436` §7 step 3: *"Do not resize down"* — superseded by 2026-01-16.
- `step434` §1A: "current, primary" is no longer true of the profile method.
- `HIS_TEACHING_ORDER.md`: the daily-bias inference, per §4.
- `Config.newest_teaching()`: the name asserts something the dates disprove for two of its
  seven switches.

---

## 6. STILL NEEDS VIDEO

Reduced from the standing list, with two closed and two added.

**Closed by the January course:**
- New day / new week opening gap construction (`step454` §2.2) — stated 2026-01-08.
- Whether "prominent high" survives (`step452` PART D) — absent from all sixteen January
  videos, third independent confirmation. Dead.

**Still open:**
- **"Drastically larger than usual" stop** (2026-01-16). No number attached. Change 4 above
  cannot be built honestly without one.
- **The exact boundaries of a BPR** (2026-01-08). He draws the range on screen and describes
  it as "a swift move up ... then a swift move down", but never names the two prices.
- **How he chooses which higher-timeframe gap is the one holding the trend** (2026-01-14).
  He points at it. Change 1 needs a selection rule, and the fair-value-gap lesson's
  bottom-of-the-stack rule is the obvious candidate but he does not say so.
