"""
news_calendar.py — the REAL US economic release calendar.

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

SOURCES (all official, all free, all fetched by `--refresh` below)
    Bureau of Labor Statistics, 2026 release schedule
        https://www.bls.gov/schedule/2026/MM_sched.htm
        Gives the consumer price report (CPI), the producer price report
        (PPI), the jobs report ("Employment Situation"), and every other BLS
        release, each with its own release time. The pages state: "All times
        on calendar are Eastern Time."
    Federal Reserve, FOMC calendar
        https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
        Eight two-day meetings a year. The DECISION lands on the SECOND day.
        We do not infer that second day from the "27-28" text when we can
        avoid it: the Fed's own statement link for each meeting is
        /newsevents/pressreleases/monetary<YYYYMMDD>a.htm, so the decision
        date is read straight out of the Fed's own URL.
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
    - BEA GDP and PCE for January to July 2026. BEA's schedule page only
      shows future releases and its news archive needs a form POST we did not
      drive. Those dates are NOT in the file. If the bot needs them, they have
      to be fetched from BEA's archive by hand.
    - ISM manufacturing and services (10:00 New York). ismworld.org blocks
      automated fetching, so no date is claimed at all.
    - Census retail sales (08:30 New York). census.gov's calendar is drawn by
      JavaScript and returns no dates to a plain fetch.
    - Conference Board consumer confidence (10:00 New York). No machine-
      readable official schedule found.
    - University of Michigan consumer sentiment: the 10:00 New York time IS
      verified, and a handful of 2026 dates are confirmed on the official
      site, but the full year is not published in machine-readable form.
      Every unconfirmed sentiment date is verified=False.

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
    python3 news_calendar.py --refresh     re-fetch every source, rewrite
                                           news_calendar_2026.json
    python3 news_calendar.py               print a summary of what is cached
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "news_calendar_2026.json")

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
        with open(DATA_FILE) as fh:
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


def covers(day: dt.date) -> bool:
    lo, hi = coverage()
    return lo <= day <= hi


# ------------------------------------------------------------------- the API
def releases_on(day: dt.date) -> list[Release]:
    """Everything published on `day`, earliest first, times in New York.

    An empty list means "the calendar covers this day and nothing is on it".
    Outside coverage this raises rather than lying with an empty list.
    """
    day = _as_date(day)
    if not covers(day):
        raise CalendarCoverageError(
            f"{day} is outside the cached calendar {coverage()[0]}..{coverage()[1]}. "
            f"Run `python3 news_calendar.py --refresh` for a wider year.")
    return list(_load()["_by_day"].get(day, ()))


def blocks_the_day(day: dt.date, on_missing: str = "block") -> bool:
    """True when the consumer price report, the producer price report, the
    Fed's rate decision, or the monthly jobs report lands on `day`. Those four
    stand his whole trading day down.

    Only VERIFIED dates can ever return True. A guessed date must never stand
    the bot down — that is the exact bug this file replaces.

    `on_missing` decides what happens for a day outside the cached calendar:
        "block"  (default) return True — no calendar means do not trade.
                 This is the safe default for a live bot: it never throws at
                 09:49 and it never trades blind into an unknown release.
        "allow"  return False.
        "raise"  raise CalendarCoverageError. Use this in backtests so a
                 replay can never quietly run past the end of the data.
    """
    day = _as_date(day)
    if not covers(day):
        if on_missing == "allow":
            return False
        if on_missing == "raise":
            raise CalendarCoverageError(
                f"{day} is outside the cached calendar "
                f"{coverage()[0]}..{coverage()[1]}")
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
        if covers(d):
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

BLS_MONTH_URL = "https://www.bls.gov/schedule/{year}/{month:02d}_sched.htm"
FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _text(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()


def _parse_bls_month(page: str, year: int, month: int):
    """One BLS calendar page -> (releases, holidays).

    Cell markup is stable and self-labelling:
        <td id="d0714"><p class="day">14</p>
            <p><strong>Consumer Price Index<br></strong>June 2026<br>08:30 AM</p>
    A holiday cell carries class="holiday" and the word Holiday in place of a
    reference period.
    """
    releases, hols = [], []
    for cell in re.finditer(r'<td([^>]*)id="d(\d{2})(\d{2})"[^>]*>(.*?)</td>',
                            page, re.S):
        attrs, mm, dd, body = cell.group(1), int(cell.group(2)), int(cell.group(3)), cell.group(4)
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
    return dt.datetime.strptime(s.upper().replace(" ", ""), "%I:%M%p").time().isoformat("minutes")


def _parse_fomc(page: str, year: int):
    """Fed rate-decision dates.

    Preferred: read the decision date straight out of the Fed's own statement
    link, /newsevents/pressreleases/monetary<YYYYMMDD>a.htm. That is the Fed
    telling us the exact day the statement went out, so no inference at all.

    Fallback for meetings that have not happened yet (no statement link):
    take the SECOND day of the "27-28" range, which is where the decision
    lands for a two-day meeting.
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
    if len(blocks) != 8:
        raise RuntimeError(f"expected 8 FOMC meetings in {year}, parsed {len(blocks)}")
    for b in blocks:
        mon = re.search(r'fomc-meeting__month[^>]*>\s*(?:<strong>)?([A-Za-z/]+)', b)
        days = re.search(r'fomc-meeting__date[^>]*>\s*([0-9*\-– ]+)', b)
        if not mon or not days:
            continue
        stmt = re.search(rf"/newsevents/pressreleases/monetary({year}\d{{4}})a\.htm", b)
        verified_exact = False
        if stmt:
            date = dt.datetime.strptime(stmt.group(1), "%Y%m%d").date()
            verified_exact = True
        else:
            month_name = mon.group(1).split("/")[-1]
            if month_name not in _MONTHS:
                continue
            nums = re.findall(r"\d+", days.group(1))
            if not nums:
                continue
            date = dt.date(year, _MONTHS[month_name], int(nums[-1]))
        out.append({
            "date": date.isoformat(),
            "name": "FOMC Statement",
            "time_et": "14:00",
            "period": "rate decision, day 2 of the meeting",
            "source": ("federalreserve.gov statement URL monetary%s"
                       % date.strftime("%Y%m%d")) if verified_exact
                      else "federalreserve.gov/monetarypolicy/fomccalendars.htm",
            "verified": True,
        })
    return out


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


def _weekly_claims(year: int, hol_dates: set[dt.date]):
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
    machine-readable form, so only the handful confirmed on sca.isr.umich.edu
    carry verified=True... and even those we keep at verified=False, because a
    10:00 release does not block the day and nothing downstream should ever
    treat a partially-confirmed list as a real calendar. The usual rhythm
    (preliminary on the second Friday, final on the last Friday) is NOT
    generated here. Only the confirmed dates are listed.
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
                  "official site; date confirmed there but the full-year "
                  "schedule is not published, so most months are MISSING",
        "verified": False,
    } for d, n in confirmed]


def _impact(name: str) -> str:
    if name in DAY_KILLERS:
        return "day_killer"
    if name in HIGH_IMPACT:
        return "high"
    return "low"


def refresh(year: int = 2026, path: str = DATA_FILE) -> dict:
    """Re-fetch every source and rewrite the cache. Network. By hand only."""
    releases, hols = [], []
    for month in range(1, 13):
        page = _get(BLS_MONTH_URL.format(year=year, month=month))
        r, h = _parse_bls_month(page, year, month)
        releases += r
        hols += h
        print(f"  BLS {year}-{month:02d}: {len(r)} releases, {len(h)} holidays")

    fomc = _parse_fomc(_get(FOMC_URL), year)
    print(f"  FOMC {year}: {len(fomc)} rate decisions")
    releases += fomc

    bea = _parse_bea(_get(BEA_URL), year)
    print(f"  BEA {year}: {len(bea)} GDP/PCE releases (forward-looking only)")
    releases += bea

    hol_dates = {dt.date.fromisoformat(h["date"]) for h in hols}
    claims = _weekly_claims(year, hol_dates)
    print(f"  DOL weekly claims {year}: {len(claims)} Thursdays (rule-derived)")
    releases += claims

    sent = _consumer_sentiment(year)
    print(f"  UMich consumer sentiment: {len(sent)} confirmed dates only")
    releases += sent

    for r in releases:
        r["impact"] = _impact(r["name"])
    releases.sort(key=lambda r: (r["date"], r["time_et"] or "00:00", r["name"]))

    doc = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "timezone": TIMEZONE,
        "note": "Every time in this file is US Eastern (America/New_York), "
                "which is how BLS, the Federal Reserve, BEA and DOL publish "
                "them. Never UTC.",
        "coverage": {"start": f"{year}-01-01", "end": f"{year}-12-31"},
        "day_killers": list(DAY_KILLERS),
        "sources": {
            "bls": BLS_MONTH_URL.format(year=year, month=1) + " (and 02..12)",
            "fomc": FOMC_URL,
            "fomc_time": "https://www.federalreserve.gov/newsevents/pressreleases/"
                         "monetary20260128a.htm — 'For release at 2:00 p.m. EST'",
            "bea": BEA_URL,
            "dol_claims": "https://oui.doleta.gov/unemploy/claims.asp",
            "umich": "http://www.sca.isr.umich.edu/",
        },
        "not_covered": [
            "BEA GDP and PCE for Jan-Jul 2026 (BEA publishes the schedule "
            "forward only; past dates are absent, not guessed)",
            "ISM manufacturing and services, 10:00 New York (ismworld.org "
            "blocks automated fetching)",
            "Census retail sales, 08:30 New York (calendar is JavaScript-only)",
            "Conference Board consumer confidence, 10:00 New York",
            "Most University of Michigan consumer sentiment dates",
        ],
        "holidays": sorted({(h["date"], h["name"]) for h in hols}.__iter__(),
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
        times = sorted({(r.time_et.strftime('%H:%M') if r.time_et else '--') for r in rs})
        print(f"{name:24s} {len(rs):3d} dates   at {', '.join(times)} New York")
    today = dt.date.today()
    win_end = min(today, hi)
    blocked = blocked_days(lo, win_end)
    weekday = [(d, w) for d, w in blocked if d.weekday() < 5]
    print(f"\n{lo} .. {win_end}: {len(weekday)} weekdays blocked by the four")
    for d, w in weekday:
        print(f"   {d} {d.strftime('%a')}  {w}")


if __name__ == "__main__":
    if "--refresh" in sys.argv:
        refresh()
    _summary()
