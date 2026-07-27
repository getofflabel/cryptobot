# Step 439 — the real economic calendar replaces the invented one

`news_calendar.py` + `news_calendar_2026.json` + `test_news_calendar.py`.
Nothing else was touched. `tjr_bot.py` was **not** edited — the swap
instructions are in section 4 and are yours to apply.

---

## 1. What was wrong

`tjr_bot.NewsCalendar` did not have a calendar. It had a rhythm generator:

- the jobs report is the **first Friday** of the month
- the consumer price report is the first Tuesday/Wednesday/Thursday **on or
  after the 10th**
- the producer price report is the **next business day** after that
- the Fed decides on a **fixed nth Wednesday**, eight times a year

In 2026 every one of those rules is wrong somewhere:

| what really happened | what the rule said |
|---|---|
| December-2025 jobs report, **Friday 9 January** | Friday 2 January |
| January-2026 jobs report, **Wednesday 11 February** | Friday 6 February |
| June-2026 jobs report, **Thursday 2 July** | Friday 3 July — a day the market was shut |
| **two** producer price reports in January (the 14th, then the 30th) | one, on the 14th |
| Fed decisions 28 Jan, 18 Mar, 29 Apr, 17 Jun | 28 Jan, 18 Mar, **6 May**, 17 Jun |

The 2026 schedule is irregular because the release calendar was still
catching up from the late-2025 shutdown backlog — the producer price report
was published twice in January, and the jobs report drifted off Friday
entirely. A rhythm generator cannot produce any of that.

## 2. Where the dates come from

Every date is fetched from the agency that publishes the number. No
aggregators, no Forex Factory scrape, no LLM recall.

| what | source | verified |
|---|---|---|
| consumer price report, producer price report, jobs report, employment cost index, import/export prices, job-openings report, and every other BLS release, each with its own time | `bls.gov/schedule/2026/MM_sched.htm` (all 12 months). The pages state "All times on calendar are Eastern Time." | yes, exact dates |
| Fed rate decision dates | `federalreserve.gov/monetarypolicy/fomccalendars.htm`. For meetings that already happened the date is read out of the Fed's own statement URL (`/newsevents/pressreleases/monetary20260128a.htm` → 28 Jan 2026), so it is the Fed stating the day, not us inferring it. For meetings still ahead, the second day of the published two-day range. | yes, exact dates |
| the 14:00 New York decision time | the header of a real 2026 statement page: "For release at 2:00 p.m. EST" | yes |
| GDP and the PCE inflation measure | `bea.gov/news/schedule` | yes, but **forward only** — see section 6 |
| weekly unemployment claims | DOL's published rule: Thursdays 08:30 New York, exceptions on federal holidays | rule yes, **individual dates no** |
| consumer sentiment 10:00 New York time | `sca.isr.umich.edu`: "Next data release: Friday, July 31, 2026 for Final July data at 10am ET" | time yes, **most dates no** |
| US federal holidays | marked on the BLS calendar pages themselves | yes |

**Times confirmed, all US Eastern (America/New_York), never UTC:**

- **08:30** consumer prices, producer prices, jobs report, employment cost
  index, import/export prices, weekly unemployment claims, GDP, PCE
- **10:00** job-openings report, consumer sentiment, state and metro employment
- **14:00** the Fed's rate decision

So his teaching checks out on all three counts.

## 3. What the module gives you

```python
import news_calendar as nc
import datetime as dt

nc.blocks_the_day(dt.date(2026, 7, 14))      # True  — consumer prices
nc.blocking_release(dt.date(2026, 7, 14))    # "Consumer Price Index"
nc.releases_on(dt.date(2026, 7, 14))         # [Release, Release, ...] time-ordered
nc.release_time(dt.date(2026, 7, 14), "Consumer Price Index")   # time(8, 30)
nc.high_impact_on(day)                       # wait-then-half-size releases
nc.derisks_the_day(day)                      # True when the day carries one
nc.first_tradeable_time(day)                 # time(10, 15) after a 10:00 release, None if blocked
nc.holidays()                                # {date: name}
nc.coverage()                                # (2026-01-01, 2026-12-31)
nc.blocked_days(start, end)                  # [(date, which release), ...]
```

Every `Release` carries `verified: bool` and a `source` string.

Three rules built into the module, worth knowing before you wire it:

1. **Nothing unverified can ever stand the bot down.** `blocks_the_day` only
   returns True on a date that came off an agency schedule page. That is the
   whole point of the exercise.
2. **A day outside the cached year never comes back as "nothing on".**
   `blocks_the_day` defaults to `on_missing="block"` — no calendar means do
   not trade, which is the safe way round for a live bot and never throws at
   09:49. Pass `on_missing="raise"` in backtests so a replay cannot quietly
   run past the end of the data. `releases_on` always raises.
3. **No network, ever, at trade time.** Importing reads one JSON file.
   `python3 news_calendar.py --refresh` is the only thing that opens a socket
   and it is run by hand.

## 4. The swap — exactly what to change in `tjr_bot.py`

**Replace the class `NewsCalendar`** (the one whose docstring says "HONEST
LIMIT: he reads Forex Factory... generated from their published rhythms").
Delete its `_nth_weekday` and `_year` methods entirely. Keep the class name
so nothing else has to change: it is referenced in `TjrBot.__init__`
(`self.news = news or NewsCalendar()`), in the `news: NewsCalendar | None`
parameter of `build_context`, `replay` and the other entry points, and its
two methods are called from `build_context` (`news.blocks(day.date())`) and
`TjrBot.run_day` (`self.news.derisks(day.date())`).

Drop-in body, same two methods, same return types:

```python
import news_calendar as _nc


class NewsCalendar:
    """CPI, PPI, FOMC and NFP block the whole day (step434 section 3B).

    Dates come from news_calendar.py, which reads them off the BLS, Federal
    Reserve and BEA release schedules. Nothing is generated from a rhythm.
    `extra_block` / `extra_derisk` still take a live feed if we ever add one.
    """

    def __init__(self, extra_block=None, extra_derisk=None, rules: bool = True):
        self.extra_block = set(extra_block or ())
        self.extra_derisk = set(extra_derisk or ())
        self.rules = rules          # False = calendar off, for A/B runs

    def blocks(self, day: dt.date) -> str | None:
        if day in self.extra_block:
            return "high-impact release"
        if not self.rules:
            return None
        if not _nc.covers(day):
            return "no release calendar for this date"   # stand down, do not guess
        return _nc.blocking_release(day)                 # e.g. "Consumer Price Index"

    def derisks(self, day: dt.date) -> bool:
        if day in self.extra_derisk:
            return True
        return self.rules and _nc.covers(day) and _nc.derisks_the_day(day)
```

- `blocks()` returns the same thing it did before: `None`, or a short string
  that `build_context` interpolates into
  `f"news gate: {blocked} blocks the whole day"`. The string is now the
  agency's own release name, so the log line reads
  `news gate: Consumer Price Index blocks the whole day`.
- `derisks()` returns the same bool, feeding `cfg.risk_pct_derisk`.
- The `rules` flag is preserved so `NewsCalendar(rules=False)` still turns the
  gate off for an A/B run.

Nothing else in `tjr_bot.py` needs to change. No call site, no signature, no
config field.

### One thing you may want on top

`first_tradeable_time(day)` is new and has no home in the bot yet. On a day
carrying a 10:00 release it returns 10:15, and since he will not open
anything after 10:30 that leaves a fifteen-minute window. Seven trading days
in January–July 2026 look like that. Whether those days should be blocked
outright or just left alone is a decision for you, not something the calendar
should assume — so `blocks_the_day` does **not** block them today.

## 5. How many days are actually blocked

Window: **2 January – 30 June 2026**, the replay's own window, 123 SPY
sessions.

| | days blocked | symbol-days (SPY + QQQ) |
|---|---|---|
| the invented calendar | 21 | 42 |
| **the real calendar** | **21** | **42** |
| dates they agree on | 14 | 28 |

**The count is the same. The dates are not.** The invented calendar happened
to land on the right *number* of blocked days — one consumer-price, one
producer-price and one jobs report a month plus eight Fed days is the right
rhythm — while getting a third of the actual dates wrong in both directions:
seven days stood down for nothing, seven days traded blind into a release.

Over the wider **1 January – 24 July 2026** window (140 SPY sessions) it is
24 blocked days each way, agreeing on 16. The eight the old calendar got
wrong each way:

*Stood the bot down and nothing was released:* 2 Jan, 6 Feb, 10 Feb, 10 Mar,
15 Apr, 1 May, 6 May, 22 Jul.

*Let the bot trade straight into a release:* 9 Jan (jobs), 30 Jan (producer
prices), 13 Feb (consumer prices), 27 Feb (producer prices), 10 Apr (consumer
prices), 29 Apr (Fed), 8 May (jobs), 2 Jul (jobs).

One more thing that only a real calendar shows: **the March jobs report was
released Friday 3 April at 08:30 New York, and the US stock market was closed
that day for Good Friday.** It is a genuine blocked day that costs an index
bot nothing, and would cost a 24/7 crypto bot a real day.

> **This does not explain the under-trading.** The replay produced 2.2 trades
> a month against his 7–15, and swapping this calendar in changes the number
> of blocked days by zero. It removes a real bug — the bot was standing down
> on seven quiet days and trading into seven live releases — but the
> over-filtering is somewhere else. The replay's own funnel points at the
> daily/4-hour disagreement (91 symbol-days) and the 10:30 clock, not the
> news gate.

## 6. What is NOT in here

Stated plainly so nobody assumes coverage that does not exist. None of these
are guessed and filled in; they are simply absent.

- **BEA GDP and PCE for January–July 2026.** BEA publishes its schedule
  forward only and its news archive needs a form POST we did not drive. The
  file has BEA from 30 July 2026 onward and nothing before. If the bot needs
  the earlier ones they have to be pulled from BEA's archive by hand.
- **ISM manufacturing and services**, 10:00 New York. `ismworld.org` blocks
  automated fetching, so no date is claimed at all.
- **Census retail sales**, 08:30 New York. The Census calendar is drawn by
  JavaScript and returns no dates to a plain fetch.
- **Conference Board consumer confidence**, 10:00 New York. No
  machine-readable official schedule found.
- **Most University of Michigan consumer sentiment dates.** The 10:00 New
  York time is verified on the official site and four 2026 dates are
  confirmed there, but the full year is not published in machine-readable
  form. All four are marked `verified=False` and none of them gate anything.
- **Weekly unemployment claims dates.** DOL publishes the rule (Thursdays
  08:30 New York, exceptions on federal holidays) but not a fetchable
  per-date list. All 51 are marked `verified=False`. When a Thursday *is* a
  federal holiday the entry is omitted rather than shifted to a guessed day.
- **Anything outside 2026.** `--refresh` takes a year argument; BLS publishes
  the following year around the preceding autumn.

## 7. The reality check, run

`test_news_calendar.py` — 15 tests, plain asserts, `main()` runner, no
pytest. Eleven check structure. Four go and look at
`data_alpaca_SPY_1m.parquet` (128,543 one-minute bars, 2026-01-01 to
2026-07-24) and measure how far SPY travelled in the five minutes from a
release, as a **price move in percent of price** — not a change in the value
of any position, and no leverage anywhere in the file.

```
$ python3 test_news_calendar.py
   quiet 08:30 price move: median 0.074% over 86 days
   consumer prices  median 0.392% over 7 days   (5.3x quiet)
   producer prices  median 0.230% over 8 days   (3.1x quiet)
   jobs report      median 0.305% over 6 days   (4.1x quiet)
   10 of the 10 biggest 08:30 moves in 2026 are one of the three

   14:00 price move: other weekdays median 0.084%;
   Fed days 2026-01-28 0.231%, 2026-03-18 0.145%, 2026-04-29 0.191%, 2026-06-17 0.780%

   2026-01-02 Fri  08:30 0.038%   14:00 0.106%     <- the eight dates the
   2026-02-06 Fri  08:30 0.087%   14:00 0.065%        invented calendar
   2026-02-10 Tue  08:30 0.138%   14:00 0.069%        blocked. Ordinary days,
   2026-03-10 Tue  08:30 0.148%   14:00 0.067%        every one of them.
   2026-04-15 Wed  08:30 0.062%   14:00 0.205%
   2026-05-01 Fri  08:30 0.036%   14:00 0.064%
   2026-05-06 Wed  08:30 0.069%   14:00 0.036%
   2026-07-22 Wed  08:30 0.082%   14:00 0.068%

15/15 passed
```

**All ten of the ten largest 08:30 moves of 2026 land on a date this calendar
calls a release day.** Not one consumer-price date shows a dead 08:30 — the
weakest is 10 April at 0.204%, still 2.8x a quiet day. Two dates are milder
than the rest and are worth naming rather than hiding: 14 January (producer
prices, 0.117%, rank 54 of 140) was the *November-2025* data arriving seven
weeks late, and 8 May (jobs, 0.105%, rank 61) was simply a quiet print. Both
are real, scheduled, correctly-dated releases that the market shrugged at.

All four Fed days move more at 14:00 than a normal weekday does — between
1.7x and 9.3x the median.

## 8. Rebuilding

```
python3 news_calendar.py --refresh     # re-fetch every source, rewrite the JSON
python3 news_calendar.py               # print what is cached, no network
python3 test_news_calendar.py          # 15 tests including the market check
```

`--refresh` fails loudly rather than half-writing: if the Fed page does not
yield exactly eight meetings it raises instead of silently producing four,
which is a bug this file already had once and now cannot have again.
