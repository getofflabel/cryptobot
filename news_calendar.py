"""
news_calendar.py — the REAL US economic release calendar, 2016 to 2026.

WHY THIS FILE EXISTS
    tjr_bot.NewsCalendar invents its release dates. It assumes the jobs
    report is always the first Friday, that the inflation report lands on
    the first Tuesday/Wednesday/Thursday on or after the 10th, and that the
    Fed decides on a fixed nth-Wednesday. None of that is true in 2026: the
    December-2025 jobs report came out on Friday 9 January, the January-2026
    jobs report came out on a WEDNESDAY (11 February), and the producer-price
    report was released twice in January. A guessed calendar stands the bot
    down on quiet days and lets it trade straight into a release, which is
    strictly worse than having no gate at all.

    Everything in here comes from the agency that publishes the number.

WHY IT COVERS ELEVEN YEARS AND NOT ONE
    The first cut of this file cached 2026 only, and every caller treated
    "I have no calendar for that date" as "stand down". Running the method
    over 2024 or 2025 therefore produced ZERO trades and a wall of
    "no release calendar for this date". That was a configuration hole
    wearing a strategy decision's clothes. His rule is the opposite of a
    default stand-down: a day with nothing red on it is an ordinary trading
    day, and he always has the calendar in front of him. So the calendar was
    extended to cover every year the 5-minute bar file covers, and the
    unknown-date behaviour was made LOUD instead of silent — see
    `coverage_gap` and `blocks_the_day` below.

SOURCES (all official, all free, all fetched by `--refresh` below)
    Bureau of Labor Statistics, one full-year release schedule per year
        https://www.bls.gov/schedule/<YYYY>/home.htm      (2016 .. 2026)
        A single page per year listing every BLS release with its date, its
        US Eastern release time, and the month the data is for, plus the
        federal holidays. This is the same data as the per-month pages
        (.../MM_sched.htm) — checked release-for-release against them for
        2026, 165 rows on both, zero differences — and it is the only form
        that exists before 2020, when the per-month pages 404.
        The pages state: "All times on calendar are Eastern Time."
    Federal Reserve, FOMC calendar (2021 onward)
        https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
        Eight two-day meetings a year. The DECISION lands on the SECOND day.
        We do not infer that second day from the "27-28" text when we can
        avoid it: the Fed's own statement link for each meeting is
        /newsevents/pressreleases/monetary<YYYYMMDD>a.htm, so the decision
        date is read straight out of the Fed's own URL.
    Federal Reserve, archived FOMC year pages (2016 .. 2020)
        https://www.federalreserve.gov/monetarypolicy/fomchistorical<YYYY>.htm
        Same trick, same URL pattern. Each meeting is a panel headed
        "January 26-27 Meeting - 2016" with its statement linked inside, so
        the decision date is again the Fed's own URL rather than our
        arithmetic. Panels headed "(unscheduled)", "(notation vote)" or
        "(cancelled)" are NOT rate decisions and are handled separately —
        see UNSCHEDULED FED STATEMENTS below.
    Federal Reserve, an actual 2026 statement page
        https://www.federalreserve.gov/newsevents/pressreleases/monetary20260128a.htm
        Header reads "For release at 2:00 p.m. EST" — this is where the
        14:00 New York decision time is verified rather than assumed.
    Bureau of Economic Analysis, release schedule
        https://www.bea.gov/news/schedule
        GDP and the PCE inflation measure ("Personal Income and Outlays"),
        08:30 New York. NOTE: BEA only publishes the schedule FORWARD. The
        January-to-July 2026 BEA dates could NOT be verified from BEA and are
        therefore ABSENT rather than guessed. See UNVERIFIED below.
    Department of Labor, weekly unemployment claims
        https://oui.doleta.gov/unemploy/claims.asp and the DOL statement that
        the weekly claims release goes out "each week on Thursday morning at
        8:30am" New York time, with exceptions when that Thursday is a
        federal holiday.
    University of Michigan, Surveys of Consumers
        http://www.sca.isr.umich.edu/ — the site itself states the release
        time: "Next data release: Friday, July 31, 2026 for Final July data
        at 10am ET". That verifies the 10:00 New York time.

TIMES
    Every time in this file is US EASTERN (America/New_York), because that is
    how BLS, the Fed, BEA and DOL publish them. Nothing here is UTC. The
    helper `release_datetime()` returns a timezone-aware timestamp if you
    want one.

    Verified from the sources above:
        08:30 New York  consumer price report, producer price report,
                        jobs report, employment cost index, import/export
                        prices, weekly unemployment claims, GDP, PCE
        10:00 New York  job openings report (JOLTS), consumer sentiment,
                        state and metro employment
        14:00 New York  the Fed's rate decision

UNSCHEDULED FED STATEMENTS
    2020 has seven scheduled rate decisions, not eight: the 17-18 March
    meeting was CANCELLED and the cut came out on Sunday 15 March instead.
    2019, 2020 and 2025 also carry statements from unscheduled meetings,
    notation votes and the framework review. Those are all in the cache under
    the name "FOMC Statement (unscheduled)" with impact "low", so they are
    visible as facts but can never stand a day down. That is deliberate and
    it is the causality rule, not squeamishness: nobody standing at his desk
    at 09:50 on 3 March 2020 had an emergency cut on their calendar, so
    blocking that day would be reading tomorrow's newspaper.

WHAT IS VERIFIED AND WHAT IS NOT
    Every release carries a `verified` flag and a `source` string.
        verified = True   the exact date came off the publishing agency's own
                          2026 schedule page.
        verified = False  we have the agency's published RULE but not a
                          per-date listing (weekly unemployment claims), or
                          the agency does not publish past dates and we only
                          have the release's usual rhythm (consumer
                          sentiment). These are marked, never silently mixed
                          in with the real ones.
    The four releases that stand the whole day down are ALL verified=True.
    Nothing unverified can block a day — see `blocks_the_day`.

UNVERIFIED / MISSING, stated plainly so nobody assumes coverage we do not have
    - BEA GDP and PCE, every year before the current one. BEA's schedule page
      only shows FUTURE releases and its news archive needs a form POST we
      did not drive. Those dates are NOT in the file. Neither release is a
      day-killer, so their absence changes no decision.
    - ISM manufacturing and services (10:00 New York). ismworld.org blocks
      automated fetching, so no date is claimed at all.
    - Census retail sales (08:30 New York). census.gov's calendar is drawn by
      JavaScript; the .ics and .json endpoints both return the HTML shell.
      No date is claimed rather than a guessed one.
    - Conference Board consumer confidence (10:00 New York). No machine-
      readable official schedule found.
    - University of Michigan consumer sentiment: the 10:00 New York time IS
      verified, and a handful of 2026 dates are confirmed on the official
      site, but no year is published in machine-readable form. Every
      sentiment date carries verified=False and 2016-2025 are absent.
    - Weekly unemployment claims before and after federal holidays. DOL
      publishes the RULE (Thursdays 08:30 New York) and not a per-date list,
      so every claims entry is verified=False and a holiday Thursday emits
      nothing at all rather than a guess about which way it shifted.

NO NETWORK AT TRADE TIME
    Importing this module reads one JSON file off disk. It never opens a
    socket. `--refresh` is the only thing that touches the network, and it is
    run by hand, never by the bot.

USAGE
    import news_calendar as nc
    nc.blocks_the_day(datetime.date(2026, 7, 14))   -> True  (consumer prices)
    nc.releases_on(datetime.date(2026, 7, 14))      -> [Release, Release]
    nc.release_time(datetime.date(2026, 7, 14), "Consumer Price Index")
                                                    -> datetime.time(8, 30)

REBUILD
    python3 news_calendar.py --refresh              re-fetch 2016..2026 and
                                                    rewrite the cache
    python3 news_calendar.py --refresh --years=2016-2027
    python3 news_calendar.py                        print what is cached
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

_HERE = os.path.dirname(os.path.abspath(__file__))

# The cache. Same shape as the 2026-only file it replaces — same keys, same
# per-release fields — so nothing downstream had to change when the window
# grew. The old single-year file is left on disk untouched as a record.
DATA_FILE = os.path.join(_HERE, "news_calendar_2016_2026.json")
LEGACY_DATA_FILE = os.path.join(_HERE, "news_calendar_2026.json")

TIMEZONE = "America/New_York"          # every time in this module, no exceptions

# The four that stand the whole trading day down (his rule, step434 3B).
# These are the BLS/Fed names exactly as the agencies print them.
DAY_KILLERS = (
    "Consumer Price Index",      # the consumer inflation report  (08:30 NY)
    "Producer Price Index",      # the producer inflation report  (08:30 NY)
    "Employment Situation",      # the monthly jobs report        (08:30 NY)
    "FOMC Statement",            # the Fed's rate decision        (14:00 NY)
)

# Releases that do not stand the day down but do mean: wait 15-20 minutes,
# then trade at reduced size only if the move was not violent. This set is
# OUR judgement about which releases move an index, not a fact any agency
# publishes — it is kept separate from the verified dates for that reason.
HIGH_IMPACT = (
    "Unemployment Insurance Weekly Claims",
    "Job Openings and Labor Turnover Survey",
    "Employment Cost Index",
    "U.S. Import and Export Price Indexes",
    "Consumer Sentiment (Preliminary)",
    "Consumer Sentiment (Final)",
    "GDP",
    "Personal Income and Outlays",
)
# Deliberately NOT here: Real Earnings (08:30, but it is a rewrite of the
# consumer price report and always lands the same morning, so the day is
# already blocked), and every state/metro/annual BLS release, which nobody
# trades off. Calling those high-impact would inflate the gate.


class CalendarCoverageError(LookupError):
    """Asked about a day the cached calendar does not cover."""


@dataclass(frozen=True)
class Release:
    date: dt.date
    name: str
    time_et: dt.time | None      # US Eastern. None only if the agency gave none.
    period: str                  # e.g. "June 2026" — which month the data is for
    impact: str                  # "day_killer" | "high" | "low"
    source: str                  # which agency page it came from
    verified: bool               # True = the exact date came off that page

    def __str__(self) -> str:
        t = self.time_et.strftime("%H:%M") if self.time_et else "--:--"
        mark = "" if self.verified else "  [UNVERIFIED DATE]"
        return f"{self.date} {t} New York  {self.name} ({self.impact}){mark}"


# ------------------------------------------------------------------ loading
_CACHE: dict | None = None


def _load() -> dict:
    global _CACHE
    if _CACHE is None:
        path = DATA_FILE if os.path.exists(DATA_FILE) else LEGACY_DATA_FILE
        with open(path) as fh:
            raw = json.load(fh)
        by_day: dict[dt.date, list[Release]] = {}
        for r in raw["releases"]:
            d = dt.date.fromisoformat(r["date"])
            t = dt.time.fromisoformat(r["time_et"]) if r.get("time_et") else None
            by_day.setdefault(d, []).append(Release(
                date=d, name=r["name"], time_et=t, period=r.get("period", ""),
                impact=r["impact"], source=r["source"], verified=r["verified"]))
        for v in by_day.values():
            v.sort(key=lambda x: (x.time_et or dt.time(0, 0), x.name))
        raw["_by_day"] = by_day
        raw["_start"] = dt.date.fromisoformat(raw["coverage"]["start"])
        raw["_end"] = dt.date.fromisoformat(raw["coverage"]["end"])
        raw["_holidays"] = {dt.date.fromisoformat(h["date"]): h["name"]
                            for h in raw["holidays"]}
        _CACHE = raw
    return _CACHE


def coverage() -> tuple[dt.date, dt.date]:
    """First and last day the cached calendar knows about, inclusive."""
    c = _load()
    return c["_start"], c["_end"]


_WARNED: set = set()


def coverage_gap(day) -> str | None:
    """None when the calendar covers `day`. Otherwise a sentence that says,
    in words nobody can mistake for a trading decision, that this is a HOLE
    IN THE DATA.

    THE DEFAULT THIS FILE GOT WRONG THE FIRST TIME
        A day inside the covered window with nothing on it is an ordinary
        trading day and MUST trade. That is his rule, in his words: the
        yellow-folder releases "don't really affect the market... so I get
        rid of those", and only the four red ones stand a day down. Nowhere
        does he say "if I do not know what is on the calendar, I sit out" —
        he always has the calendar open, so the case never arises for him.

        A day OUTSIDE the covered window is different, and it still refuses:
        there the file genuinely knows nothing, and trading blind into an
        unknown consumer-price report is the one outcome worse than sitting
        out. But it must refuse LOUDLY and by name, because the failure the
        first time round was not the caution. It was that a missing config
        file and a working method standing aside produced the same quiet
        line in the log, so two years of backtest silently evaporated and
        looked like a result.
    """
    day = _as_date(day)
    lo, hi = coverage()
    if lo <= day <= hi:
        return None
    side = "before" if day < lo else "after"
    return (f"CALENDAR GAP, NOT A TRADING DECISION: no US release calendar is "
            f"cached for {day} ({side} the cached window {lo}..{hi}). The "
            f"method did not stand this day down — the data did. Fix it with "
            f"`python3 news_calendar.py --refresh --years={day.year}-{day.year}`.")


def covers(day: dt.date) -> bool:
    """True when the cache knows about `day`.

    A False answer also SHOUTS once per missing date on stderr. Callers such
    as tjr_bot.NewsCalendar turn a False into their own short stand-down
    string; without this the only trace of a two-year hole in the cache was
    that short string, which reads exactly like the method choosing to sit
    out. It is not. It is a missing file.
    """
    gap = coverage_gap(day)
    if gap is None:
        return True
    d = _as_date(day)
    if d not in _WARNED:
        _WARNED.add(d)
        print(gap, file=sys.stderr)
    return False


# ------------------------------------------------------------------- the API
def releases_on(day: dt.date) -> list[Release]:
    """Everything published on `day`, earliest first, times in New York.

    An empty list means "the calendar covers this day and nothing is on it".
    Outside coverage this raises rather than lying with an empty list.
    """
    day = _as_date(day)
    if not covers(day):
        raise CalendarCoverageError(coverage_gap(day))
    return list(_load()["_by_day"].get(day, ()))


def blocks_the_day(day: dt.date, on_missing: str = "block") -> bool:
    """True when the consumer price report, the producer price report, the
    Fed's rate decision, or the monthly jobs report lands on `day`. Those four
    stand his whole trading day down.

    A day inside the covered window with none of those four on it returns
    False and is an ordinary trading day. Only VERIFIED dates can ever return
    True. A guessed date must never stand the bot down — that is the exact
    bug this file replaces.

    `on_missing` decides what happens for a day OUTSIDE the cached calendar,
    where the file knows nothing at all:
        "block"  (default) return True AND print the gap to stderr by name,
                 via `covers`. Safe for a live bot: it never throws at 09:49
                 and it never trades blind into an unknown release, but it
                 also never lets a missing cache masquerade as the method
                 sitting out. Read `coverage_gap` for why that distinction
                 cost two years of backtest.
        "allow"  return False.
        "raise"  raise CalendarCoverageError, quoting the gap. Use this in
                 backtests so a replay can never quietly run past the data.
    """
    day = _as_date(day)
    if not covers(day):                       # `covers` does the shouting
        if on_missing == "allow":
            return False
        if on_missing == "raise":
            raise CalendarCoverageError(coverage_gap(day))
        return True
    return blocking_release(day) is not None


def blocking_release(day: dt.date) -> str | None:
    """The name of the release that stands the day down, or None.

    Use this instead of `blocks_the_day` when you want to write the reason
    into the log, e.g. "stand down: Consumer Price Index at 08:30 New York".
    """
    day = _as_date(day)
    if not covers(day):
        return None
    for r in releases_on(day):
        if r.impact == "day_killer" and r.verified:
            return r.name
    return None


def stand_down_reason(day) -> tuple[str, str] | None:
    """One call that never lets a data hole look like a trading decision.

    Returns None when the day is tradeable, otherwise (kind, why) where kind
    is exactly one of:
        "release"       one of the four red releases lands today. This is the
                        method working. `why` is the release name.
        "calendar_gap"  we have no calendar for this date at all. This is a
                        broken cache. `why` is the full `coverage_gap` shout.
    Count the two separately. A run that "stood down 250 days" means nothing
    until you know which bucket they fell in.
    """
    day = _as_date(day)
    gap = coverage_gap(day)
    if gap is not None:
        return ("calendar_gap", gap)
    who = blocking_release(day)
    return ("release", who) if who else None


def release_time(day: dt.date, name: str) -> dt.time | None:
    """The US Eastern release time for `name` on `day`, or None if that
    release is not on that day. Matching is case-insensitive and accepts a
    prefix, so "Consumer Price" finds "Consumer Price Index".
    """
    day = _as_date(day)
    want = name.strip().lower()
    for r in releases_on(day):
        if r.name.lower() == want or r.name.lower().startswith(want):
            return r.time_et
    return None


def high_impact_on(day: dt.date) -> list[Release]:
    """Releases that are not day-killers but do mean wait-then-half-size."""
    return [r for r in releases_on(day) if r.impact == "high"]


def derisks_the_day(day: dt.date) -> bool:
    """True when the day carries a high-impact release but is not blocked.
    Only verified dates count, same reason as `blocks_the_day`."""
    day = _as_date(day)
    if not covers(day) or blocks_the_day(day, on_missing="allow"):
        return False
    return any(r.verified for r in high_impact_on(day))


def first_tradeable_time(day: dt.date) -> dt.time | None:
    """The earliest New York time the day is clean, under his own rules:
    wait 15 minutes after an 08:30 release, 15 minutes after a 10:00 one.
    Returns None when the day is blocked outright.

    A 10:00 release pushes this to 10:15, and since he will not open anything
    after 10:30 that leaves a 15-minute window — which is why he treats the
    10:00 releases as effectively killing the day too.
    """
    day = _as_date(day)
    if blocks_the_day(day, on_missing="allow"):
        return None
    latest = dt.time(0, 0)
    for r in high_impact_on(day):
        if not (r.verified and r.time_et):
            continue
        after = (dt.datetime.combine(day, r.time_et)
                 + dt.timedelta(minutes=15)).time()
        latest = max(latest, after)
    return latest


def holidays() -> dict[dt.date, str]:
    """US federal holidays, taken off the BLS calendar pages (which mark them
    on the calendar next to the releases)."""
    return dict(_load()["_holidays"])


def all_releases(name: str | None = None,
                 verified_only: bool = False) -> list[Release]:
    """Flat list across the whole cached window, optionally one release name."""
    out: list[Release] = []
    for day in sorted(_load()["_by_day"]):
        for r in _load()["_by_day"][day]:
            if name and r.name.lower() != name.lower():
                continue
            if verified_only and not r.verified:
                continue
            out.append(r)
    return out


def release_datetime(r: Release):
    """`r` as a timezone-aware New York timestamp, for lining up against bar
    data. Returns None when the agency published no time."""
    if r.time_et is None:
        return None
    try:
        from zoneinfo import ZoneInfo
    except ImportError:                                   # pragma: no cover
        return dt.datetime.combine(r.date, r.time_et)
    return dt.datetime.combine(r.date, r.time_et, ZoneInfo(TIMEZONE))


def blocked_days(start: dt.date, end: dt.date) -> list[tuple[dt.date, str]]:
    """Every day in [start, end] the four day-killers stand down, with which
    one it was. Weekends are included if a release ever lands on one (none
    do), so filter by weekday yourself if you want trading days only."""
    out = []
    d = _as_date(start)
    end = _as_date(end)
    while d <= end:
        if coverage_gap(d) is None:      # silent: a scan is not a decision
            who = blocking_release(d)
            if who:
                out.append((d, who))
        d += dt.timedelta(days=1)
    return out


def _as_date(day) -> dt.date:
    if isinstance(day, dt.datetime):
        return day.date()
    if isinstance(day, dt.date):
        return day
    if isinstance(day, str):
        return dt.date.fromisoformat(day)
    # pandas.Timestamp and anything else with .date()
    if hasattr(day, "date"):
        return day.date()
    raise TypeError(f"cannot read a date out of {day!r}")


# ========================================================================
#  REFRESH — the only part of this file that touches the network.
#  Never called by the bot. Run by hand: python3 news_calendar.py --refresh
# ========================================================================
_UA = "cryptobot-news-calendar/1.0 (research; wallacechen23@gmail.com)"

# One page per year, every year from 2016 to next year. This replaces the
# twelve per-month pages the first cut used: the month pages only exist from
# 2020 onward, the year page exists for every year back to 2000, and for 2026
# the two parse to exactly the same 165 releases and 11 holidays.
BLS_YEAR_URL = "https://www.bls.gov/schedule/{year}/home.htm"
BLS_MONTH_URL = "https://www.bls.gov/schedule/{year}/{month:02d}_sched.htm"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_HISTORICAL_URL = ("https://www.federalreserve.gov/monetarypolicy/"
                       "fomchistorical{year}.htm")
BEA_URL = "https://www.bea.gov/news/schedule"

_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}


def _get(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()


# ------------------------------------------------------------------- BLS
_BLS_ROW = re.compile(
    r'<td class="date-cell">\s*<p>(.*?)</p>\s*</td>\s*'
    r'<td class="time-cell">\s*<p>(.*?)</p>\s*</td>\s*'
    r'<td class="desc-cell">\s*<p>(.*?)</p>\s*</td>', re.S)


def _parse_bls_year(page: str, year: int):
    """One BLS year page -> (releases, holidays).

    The markup is a plain three-column table and self-labelling:
        <td class="date-cell"><p>Wednesday, January 20, 2016</p></td>
        <td class="time-cell"><p>08:30 AM</p></td>
        <td class="desc-cell"><p><strong>Consumer Price Index</strong>
                               for December 2015</p></td>
    A federal holiday is the same row with an empty time cell and the holiday
    name where the release name goes. Anything we cannot read is reported and
    dropped, never guessed.
    """
    releases, hols, bad = [], [], []
    for d_raw, t_raw, desc_raw in _BLS_ROW.findall(page):
        d_s = _text(d_raw)
        try:
            date = dt.datetime.strptime(d_s, "%A, %B %d, %Y").date()
        except ValueError:
            bad.append(d_s)
            continue
        if date.year != year:
            continue
        m = re.match(r"\s*<strong>(.*?)</strong>(.*)$", desc_raw, re.S)
        if not m:
            bad.append(_text(desc_raw))
            continue
        name = _text(m.group(1))
        period = re.sub(r"^for\s+", "", _text(m.group(2)))
        time_s = _text(t_raw)
        if not time_s:                       # empty time cell = a holiday row
            hols.append({"date": date.isoformat(), "name": name})
            continue
        releases.append({
            "date": date.isoformat(),
            "name": name,
            "time_et": _to_iso_time(time_s),
            "period": period,
            "source": "bls.gov/schedule/%d/home.htm" % year,
            "verified": True,
        })
    if bad:
        print(f"    BLS {year}: {len(bad)} unreadable rows DROPPED: {bad[:3]}")
    return releases, hols


def _parse_bls_month(page: str, year: int, month: int):
    """The per-month BLS page (2020 onward only). Kept because it is the page
    the first version of this file was built and verified against, and it is
    the independent check that `_parse_bls_year` reads the same schedule.
    Not used by `refresh`."""
    releases, hols = [], []
    for cell in re.finditer(r'<td([^>]*)id="d(\d{2})(\d{2})"[^>]*>(.*?)</td>',
                            page, re.S):
        attrs, mm, dd, body = (cell.group(1), int(cell.group(2)),
                               int(cell.group(3)), cell.group(4))
        if mm != month:
            continue                       # spill-over cells from the next month
        date = dt.date(year, mm, dd)
        is_holiday_cell = "holiday" in attrs
        for p in re.finditer(r"<p[^>]*>(.*?)</p>", body, re.S):
            inner = p.group(1)
            m = re.match(r"\s*<strong>(.*?)<br\s*/?>\s*</strong>(.*)$", inner, re.S)
            if not m:
                continue                   # the <p class="day">14</p> cell
            name = _text(m.group(1))
            rest = re.sub(r"<br\s*/?>", "|", m.group(2))
            parts = [x for x in (_text(y) for y in rest.split("|")) if x]
            period = parts[0] if parts else ""
            time_s = ""
            for x in parts:
                if re.fullmatch(r"\d{1,2}:\d{2}\s*(AM|PM)", x, re.I):
                    time_s = x
            if is_holiday_cell or period.lower() == "holiday":
                hols.append({"date": date.isoformat(), "name": name})
                continue
            releases.append({
                "date": date.isoformat(),
                "name": name,
                "time_et": _to_iso_time(time_s),
                "period": period,
                "source": "bls.gov/schedule/%d/%02d_sched.htm" % (year, month),
                "verified": True,
            })
    return releases, hols


def _to_iso_time(s: str) -> str | None:
    if not s:
        return None
    return dt.datetime.strptime(s.upper().replace(" ", ""),
                                "%I:%M%p").time().isoformat("minutes")


# ------------------------------------------------------------------- Fed
_STATEMENT = r"/newsevents/pressreleases/monetary(%s\d{4})a\.htm"


def _fomc_entry(date: dt.date, scheduled: bool, source: str) -> dict:
    """One Fed statement. A SCHEDULED two-day meeting's second day is the rate
    decision and stands the day down. Anything else — an emergency cut, a
    notation vote, the framework review — is recorded but cannot block,
    because it was not on anybody's calendar that morning."""
    return {
        "date": date.isoformat(),
        "name": "FOMC Statement" if scheduled else "FOMC Statement (unscheduled)",
        "time_et": "14:00" if scheduled else None,
        "period": ("rate decision, day 2 of the meeting" if scheduled else
                   "unscheduled statement, notation vote or cancelled meeting "
                   "— NOT on the calendar in advance, so it never blocks"),
        "source": source,
        "verified": True,
    }


def _parse_fomc(page: str, year: int):
    """Fed rate-decision dates off the current calendar page (2021 onward).

    Preferred: read the decision date straight out of the Fed's own statement
    link, /newsevents/pressreleases/monetary<YYYYMMDD>a.htm. That is the Fed
    telling us the exact day the statement went out, so no inference at all.

    Fallback for meetings that have not happened yet (no statement link):
    take the SECOND day of the "27-28" range, which is where the decision
    lands for a two-day meeting.

    Only rows whose date cell is a RANGE are rate decisions. 2025 carries a
    ninth row, "August 22", which is the framework-review statement out of
    Jackson Hole and not a decision on rates; a single-day row is never
    treated as one.
    """
    m = re.search(rf"{year} FOMC Meetings(.*?)(?:\d{{4}} FOMC Meetings|</table>|$)",
                  page, re.S)
    if not m:
        raise RuntimeError(f"no {year} panel on the FOMC calendar page")
    panel = m.group(1)
    out = []
    # Two variants on the page: class="row fomc-meeting" and
    # class="fomc-meeting--shaded row fomc-meeting" (the shaded rows are the
    # four meetings that also publish projections). Split on both or half the
    # year goes missing.
    blocks = re.split(r'<div class="[^"]*row fomc-meeting"', panel)[1:]
    for b in blocks:
        mon = re.search(r'fomc-meeting__month[^>]*>\s*(?:<strong>)?([A-Za-z/]+)', b)
        days = re.search(r'fomc-meeting__date[^>]*>\s*([0-9*\-– ]+)', b)
        if not mon or not days:
            continue
        day_text = days.group(1).strip()
        stmt = re.search(_STATEMENT % year, b)
        if not re.search(r"\d\s*[-–]\s*\d", day_text):
            if stmt:                     # e.g. 2025 Jackson Hole, 22 August
                out.append(_fomc_entry(
                    dt.datetime.strptime(stmt.group(1), "%Y%m%d").date(), False,
                    "federalreserve.gov/monetarypolicy/fomccalendars.htm "
                    "— single-day row, not a two-day meeting"))
            continue
        if stmt:
            date = dt.datetime.strptime(stmt.group(1), "%Y%m%d").date()
            src = ("federalreserve.gov statement URL monetary%s"
                   % date.strftime("%Y%m%d"))
        else:
            month_name = mon.group(1).split("/")[-1]
            if month_name not in _MONTHS:
                continue
            nums = re.findall(r"\d+", day_text)
            if not nums:
                continue
            date = dt.date(year, _MONTHS[month_name], int(nums[-1]))
            src = "federalreserve.gov/monetarypolicy/fomccalendars.htm"
        out.append(_fomc_entry(date, True, src))
    n = sum(1 for r in out if r["name"] == "FOMC Statement")
    if n != 8:
        raise RuntimeError(f"expected 8 FOMC rate decisions in {year}, parsed {n}")
    return out


_FOMC_PANEL = re.compile(
    r'<div class="panel panel-default panel-padded">(.*?)'
    r'(?=<div class="panel panel-default panel-padded">|$)', re.S)


def _parse_fomc_historical(page: str, year: int):
    """Fed statements off an archived year page (2016 .. 2020).

    Each meeting is its own panel:
        <h5 class="panel-heading...">January 26-27 Meeting - 2016</h5>
        ... <p><a href="/newsevents/pressreleases/monetary20160127a.htm">
                Statement</a></p>
    The decision date is once again the Fed's own statement URL.

    A panel is a scheduled rate decision only when its heading is a two-day
    range AND carries none of "(unscheduled)", "(notation vote)",
    "(cancelled)". 2020 is why: its 17-18 March meeting was CANCELLED and the
    cut went out on Sunday 15 March, so 2020 has SEVEN scheduled decisions,
    not eight. An 8-per-year assumption would have quietly invented one.
    """
    out, scheduled = [], 0
    for m in _FOMC_PANEL.finditer(page):
        body = m.group(1)
        h = re.search(r"<h5[^>]*>(.*?)</h5>", body, re.S)
        if not h:
            continue
        head = _text(h.group(1))
        stmt = re.search(_STATEMENT % year, body)
        if not stmt:                       # cancelled meeting, no statement
            continue
        date = dt.datetime.strptime(stmt.group(1), "%Y%m%d").date()
        two_day = bool(re.match(r"^[A-Za-z/]+ \d{1,2}\s*[-–]\s*\d{1,2} Meeting", head))
        odd = any(w in head.lower() for w in
                  ("unscheduled", "notation vote", "cancelled", "canceled"))
        is_decision = two_day and not odd
        scheduled += is_decision
        out.append(_fomc_entry(
            date, is_decision,
            "federalreserve.gov statement URL monetary%s (archived page "
            "fomchistorical%d.htm, panel %r)"
            % (date.strftime("%Y%m%d"), year, head)))
    if not 7 <= scheduled <= 8:
        raise RuntimeError(
            f"expected 7 or 8 scheduled FOMC decisions in {year}, parsed {scheduled}")
    return out


def fomc_for_year(year: int, calendars_page: str | None = None):
    """Whichever Fed page holds `year`. The current calendar page carries the
    last few years and the next one; everything older lives on its own
    archived page."""
    if calendars_page and re.search(rf"{year} FOMC Meetings", calendars_page):
        return _parse_fomc(calendars_page, year)
    return _parse_fomc_historical(
        _get(FOMC_HISTORICAL_URL.format(year=year)), year)


# ------------------------------------------------------------------- BEA
def _parse_bea(page: str, year: int):
    """BEA publishes its schedule FORWARD only, so this returns whatever is
    still upcoming. Past BEA dates are simply absent — see the module
    docstring. Rows read: <date> <time> <News|Data> <title>."""
    body = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    txt = re.sub(r"<[^>]+>", "|", body)
    txt = html.unescape(txt)
    txt = re.sub(r"[|\s]*\|[|\s]*", "|", txt)
    out = []
    pat = re.compile(
        r"\|([A-Z][a-z]+ \d{1,2})\|(\d{1,2}:\d{2} [AP]M)\|[^|]*\|?([ND])\|(?:ews|ata)\|([^|]+)\|")
    for m in pat.finditer(txt):
        month_day, time_s, kind, title = m.groups()
        if kind != "N":
            continue
        try:
            when = dt.datetime.strptime(f"{month_day} {year}", "%B %d %Y").date()
        except ValueError:
            continue
        title = title.strip()
        if title.startswith("GDP"):
            name = "GDP"
        elif title.startswith("Personal Income and Outlays"):
            name = "Personal Income and Outlays"
        else:
            continue                          # trade balance etc: not our fight
        out.append({
            "date": when.isoformat(),
            "name": name,
            "time_et": _to_iso_time(time_s),
            "period": title,
            "source": "bea.gov/news/schedule",
            "verified": True,
        })
    return out


# ------------------------------------------------- rule-derived, unverified
def _weekly_claims(year: int, hol_dates: set):
    """Weekly unemployment claims. DOL publishes the RULE, not a per-date
    listing we could fetch, so every one of these is verified=False and none
    of them can block a day. The rule (oui.doleta.gov): released each Thursday
    at 08:30 New York, with exceptions when that Thursday is a federal
    holiday. When Thursday IS a holiday we emit NOTHING rather than guess
    which way the release shifted."""
    out = []
    d = dt.date(year, 1, 1)
    while d.year == year:
        if d.weekday() == 3 and d not in hol_dates:      # Thursday
            out.append({
                "date": d.isoformat(),
                "name": "Unemployment Insurance Weekly Claims",
                "time_et": "08:30",
                "period": "week ending prior Saturday",
                "source": "DOL published rule: Thursdays 08:30 New York "
                          "(oui.doleta.gov/unemploy/claims.asp) — rule verified, "
                          "individual dates NOT verified per-date",
                "verified": False,
            })
        d += dt.timedelta(days=1)
    return out


def _consumer_sentiment(year: int):
    """University of Michigan consumer sentiment, 10:00 New York.

    The TIME is verified on the official site. The DATES are not published in
    machine-readable form for ANY year, so only the handful confirmed on
    sca.isr.umich.edu appear at all... and even those carry verified=False,
    because a 10:00 release does not block the day and nothing downstream
    should ever treat a partially-confirmed list as a real calendar. The usual
    rhythm (preliminary on the second Friday, final on the last Friday) is NOT
    generated here. 2016 to 2025 have no sentiment dates at all.
    """
    confirmed = [
        # (date, which report) — read off data.sca.isr.umich.edu report list
        # and the sca.isr.umich.edu front page. Everything else is absent.
        ("2026-05-22", "Consumer Sentiment (Final)"),
        ("2026-06-12", "Consumer Sentiment (Preliminary)"),
        ("2026-06-26", "Consumer Sentiment (Final)"),
        ("2026-07-31", "Consumer Sentiment (Final)"),
    ]
    return [{
        "date": d,
        "name": n,
        "time_et": "10:00",
        "period": "",
        "source": "sca.isr.umich.edu — 10:00 New York time VERIFIED on the "
                  "official site; date confirmed there but no full-year "
                  "schedule is published, so most months are MISSING",
        "verified": False,
    } for d, n in confirmed if d.startswith(str(year))]


def _impact(name: str) -> str:
    if name in DAY_KILLERS:
        return "day_killer"
    if name in HIGH_IMPACT:
        return "high"
    return "low"


NOT_COVERED = [
    "BEA GDP and PCE for any year before the current one (BEA publishes its "
    "schedule forward only; past dates are absent, not guessed). Neither is a "
    "day-killer, so nothing is decided differently because of it.",
    "ISM manufacturing and services, 10:00 New York (ismworld.org blocks "
    "automated fetching)",
    "Census retail sales, 08:30 New York (the calendar is JavaScript-only; "
    "the .ics and .json endpoints both return the page shell)",
    "Conference Board consumer confidence, 10:00 New York",
    "University of Michigan consumer sentiment for 2016-2025 entirely, and "
    "most of 2026 — the 10:00 New York time is verified, the dates are not "
    "published machine-readably",
    "Weekly unemployment claims on federal-holiday weeks: the release shifts "
    "and DOL does not publish the shifted date, so nothing is emitted",
]


def refresh(years=range(2016, 2027), path: str = DATA_FILE) -> dict:
    """Re-fetch every source for every year and rewrite the cache. Network.
    By hand only — the bot never calls this and never opens a socket."""
    years = sorted(years)
    releases, hols = [], []
    calendars_page = _get(FOMC_URL)

    for year in years:
        r, h = _parse_bls_year(_get(BLS_YEAR_URL.format(year=year)), year)
        releases += r
        hols += h
        killers = sum(1 for x in r if x["name"] in DAY_KILLERS)
        print(f"  BLS {year}: {len(r)} releases ({killers} of the four), "
              f"{len(h)} holidays")

        fomc = fomc_for_year(year, calendars_page)
        dec = [x for x in fomc if x["name"] == "FOMC Statement"]
        print(f"  FOMC {year}: {len(dec)} rate decisions"
              + (f", {len(fomc) - len(dec)} unscheduled statements"
                 if len(fomc) > len(dec) else ""))
        releases += fomc

        hol_dates = {dt.date.fromisoformat(x["date"]) for x in h}
        releases += _weekly_claims(year, hol_dates)
        releases += _consumer_sentiment(year)

    bea = _parse_bea(_get(BEA_URL), dt.date.today().year)
    print(f"  BEA: {len(bea)} GDP/PCE releases (forward-looking only)")
    releases += [b for b in bea
                 if years[0] <= dt.date.fromisoformat(b["date"]).year <= years[-1]]

    for r in releases:
        r["impact"] = _impact(r["name"])
    releases.sort(key=lambda r: (r["date"], r["time_et"] or "00:00", r["name"]))

    doc = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "timezone": TIMEZONE,
        "note": "Every time in this file is US Eastern (America/New_York), "
                "which is how BLS, the Federal Reserve, BEA and DOL publish "
                "them. Never UTC.",
        "coverage": {"start": f"{years[0]}-01-01", "end": f"{years[-1]}-12-31"},
        "day_killers": list(DAY_KILLERS),
        "sources": {
            "bls": BLS_YEAR_URL.format(year=years[0])
                   + f" (one page per year, {years[0]}..{years[-1]})",
            "bls_cross_check": BLS_MONTH_URL.format(year=2026, month=1)
                               + " (and 02..12) — the per-month pages, which "
                                 "exist only from 2020 and which parse to the "
                                 "identical 165 releases for 2026",
            "fomc": FOMC_URL,
            "fomc_historical": FOMC_HISTORICAL_URL.format(year=2016)
                               + " (and 2017..2020)",
            "fomc_time": "https://www.federalreserve.gov/newsevents/pressreleases/"
                         "monetary20260128a.htm — 'For release at 2:00 p.m. EST'",
            "bea": BEA_URL,
            "dol_claims": "https://oui.doleta.gov/unemploy/claims.asp",
            "umich": "http://www.sca.isr.umich.edu/",
        },
        "not_covered": list(NOT_COVERED),
        "holidays": sorted({(h["date"], h["name"]) for h in hols},
                           key=lambda x: x[0]),
        "releases": releases,
    }
    doc["holidays"] = [{"date": d, "name": n} for d, n in doc["holidays"]]
    with open(path, "w") as fh:
        json.dump(doc, fh, indent=1)
    print(f"wrote {path}: {len(releases)} releases, {len(doc['holidays'])} holidays")
    global _CACHE
    _CACHE = None
    return doc


def _summary() -> None:
    lo, hi = coverage()
    c = _load()
    print(f"news_calendar cache: {lo} .. {hi}   built {c['generated_utc']}")
    print(f"all times {TIMEZONE}\n")
    for name in DAY_KILLERS:
        rs = all_releases(name)
        times = sorted({(r.time_et.strftime('%H:%M') if r.time_et else '--')
                        for r in rs})
        print(f"{name:24s} {len(rs):3d} dates   at {', '.join(times)} New York")
    print("\nper year: how many weekdays the four stand down")
    for y in range(lo.year, hi.year + 1):
        a = max(lo, dt.date(y, 1, 1))
        b = min(hi, dt.date(y, 12, 31), dt.date.today())
        if b < a:
            continue
        blocked = [(d, w) for d, w in blocked_days(a, b) if d.weekday() < 5]
        counts = {}
        for _, w in blocked:
            counts[w] = counts.get(w, 0) + 1
        detail = ", ".join(f"{k.split()[0]} {v}" for k, v in sorted(counts.items()))
        print(f"  {y}  {a} .. {b}   {len(blocked):3d} weekdays blocked   {detail}")


def _years_arg(argv) -> range:
    for a in argv:
        if a.startswith("--years="):
            lo, _, hi = a.split("=", 1)[1].partition("-")
            return range(int(lo), int(hi or lo) + 1)
    return range(2016, 2027)


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh(_years_arg(sys.argv))
    _summary()
