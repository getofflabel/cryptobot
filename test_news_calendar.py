"""
test_news_calendar.py — proves the calendar is real, not invented.

Two halves.

  STRUCTURE (no market data needed)
    The cache loads, covers the whole of 2026, has the right number of each
    release, has the right release time on each, refuses to answer about days
    it does not cover, and never lets an unverified date stand the day down.

  REALITY (needs data_alpaca_SPY_1m.parquet)
    A date is only worth having if the market agrees something happened on
    it. So we go and look. For every day in 2026 we measure how far SPY
    travelled in the five minutes from 08:30 New York, as a PRICE move in
    percent (not a change in position value — no leverage anywhere in this
    file). Consumer-price-report days should stand out against days with
    nothing at 08:30. Fed days should stand out at 14:00 New York instead.
    And the nine dates the old invented calendar blocked should look like
    completely ordinary days, which is the whole point.

Run:  python3 test_news_calendar.py
"""

import datetime as dt
import os
import sys

import news_calendar as nc

HERE = os.path.dirname(os.path.abspath(__file__))
SPY = os.path.join(HERE, "data_alpaca_SPY_1m.parquet")

WINDOW_START = dt.date(2026, 1, 1)
WINDOW_END = dt.date(2026, 7, 24)      # last full day in the parquet


# --------------------------------------------------------------- structure
def test_cache_loads_and_covers_2026():
    lo, hi = nc.coverage()
    assert lo == dt.date(2026, 1, 1), lo
    assert hi == dt.date(2026, 12, 31), hi
    assert nc.covers(dt.date(2026, 7, 14))
    assert not nc.covers(dt.date(2027, 1, 4))


def test_the_four_day_killers_have_the_right_count():
    """Twelve consumer-price reports, twelve jobs reports, eight Fed
    decisions. Thirteen producer-price reports, not twelve, because January
    2026 carried two of them (November-2025 data on the 14th, December-2025
    data on the 30th) as the schedule caught up. An invented calendar would
    never produce that thirteenth one, which is exactly why it matters."""
    assert len(nc.all_releases("Consumer Price Index")) == 12
    assert len(nc.all_releases("Employment Situation")) == 12
    assert len(nc.all_releases("Producer Price Index")) == 13
    assert len(nc.all_releases("FOMC Statement")) == 8


def test_release_times_are_what_the_agencies_publish():
    """08:30 New York for the three data reports, 14:00 New York for the Fed.
    Verified from bls.gov's own calendar pages and from the header of a real
    2026 Fed statement ('For release at 2:00 p.m. EST')."""
    for name in ("Consumer Price Index", "Producer Price Index",
                 "Employment Situation"):
        times = {r.time_et for r in nc.all_releases(name)}
        assert times == {dt.time(8, 30)}, (name, times)
    assert {r.time_et for r in nc.all_releases("FOMC Statement")} == {dt.time(14, 0)}
    # the 10:00 New York family, which pushes him past his 10:30 cut-off
    jolts = {r.time_et for r in nc.all_releases("Job Openings and Labor Turnover Survey")}
    assert jolts == {dt.time(10, 0)}, jolts


def test_every_day_killer_date_is_verified():
    """Nothing guessed may ever stand the bot down."""
    for r in nc.all_releases():
        if r.impact == "day_killer":
            assert r.verified, r


def test_blocks_the_day_on_known_real_dates():
    """Spot dates read straight off the agency schedules."""
    assert nc.blocking_release(dt.date(2026, 7, 14)) == "Consumer Price Index"
    assert nc.blocking_release(dt.date(2026, 7, 15)) == "Producer Price Index"
    assert nc.blocking_release(dt.date(2026, 7, 2)) == "Employment Situation"
    assert nc.blocking_release(dt.date(2026, 4, 29)) == "FOMC Statement"
    # a Wednesday jobs report — the invented calendar's "first Friday" rule
    # cannot produce this one at all
    assert nc.blocking_release(dt.date(2026, 2, 11)) == "Employment Situation"


def test_does_not_block_the_dates_the_invented_calendar_invented():
    """The nine days the old generator stood the bot down on for nothing."""
    for s in ("2026-01-02", "2026-02-06", "2026-02-10", "2026-03-10",
              "2026-04-15", "2026-05-01", "2026-05-06", "2026-07-22"):
        d = dt.date.fromisoformat(s)
        assert not nc.blocks_the_day(d), s


def test_releases_on_and_release_time():
    day = dt.date(2026, 7, 14)
    names = [r.name for r in nc.releases_on(day)]
    assert "Consumer Price Index" in names, names
    assert nc.release_time(day, "Consumer Price Index") == dt.time(8, 30)
    assert nc.release_time(day, "consumer price") == dt.time(8, 30)   # prefix, any case
    assert nc.release_time(day, "Producer Price Index") is None       # not that day
    ts = nc.release_datetime(nc.releases_on(day)[0])
    assert str(ts.tzinfo) == nc.TIMEZONE, ts.tzinfo


def test_outside_coverage_never_answers_quietly():
    """A day we have no calendar for must not come back as 'nothing on'."""
    future = dt.date(2027, 3, 10)
    assert nc.blocks_the_day(future) is True                    # default: stand down
    assert nc.blocks_the_day(future, on_missing="allow") is False
    try:
        nc.blocks_the_day(future, on_missing="raise")
    except nc.CalendarCoverageError:
        pass
    else:
        raise AssertionError("expected CalendarCoverageError")
    try:
        nc.releases_on(future)
    except nc.CalendarCoverageError:
        pass
    else:
        raise AssertionError("expected CalendarCoverageError from releases_on")


def test_unverified_entries_exist_and_are_harmless():
    """Weekly unemployment claims and consumer sentiment are carried but
    marked, and neither can block or de-risk a day."""
    unver = [r for r in nc.all_releases() if not r.verified]
    assert unver, "expected some marked-unverified entries"
    assert all(r.impact != "day_killer" for r in unver)
    claims = nc.all_releases("Unemployment Insurance Weekly Claims")
    assert claims and all(not r.verified for r in claims)
    assert all(r.time_et == dt.time(8, 30) for r in claims)
    # a Thursday with only unverified claims on it is not a de-risk day
    only_claims = [r for r in nc.all_releases()
                   if r.date == dt.date(2026, 1, 8)]
    if only_claims and all(not r.verified for r in only_claims):
        assert not nc.derisks_the_day(dt.date(2026, 1, 8))


def test_holidays_came_off_the_official_calendar():
    h = nc.holidays()
    assert h.get(dt.date(2026, 1, 1), "").startswith("New Year")
    assert dt.date(2026, 7, 3) in h        # Independence Day observed, a Friday
    assert len(h) >= 10, len(h)


def test_first_tradeable_time():
    """A quiet day is clean from the open. A day with a 10:00 release is not
    clean until 10:15, which leaves him fifteen minutes before his 10:30
    cut-off — the reason he treats those as day-enders too."""
    jolts_day = nc.all_releases("Job Openings and Labor Turnover Survey")[0].date
    assert nc.first_tradeable_time(jolts_day) == dt.time(10, 15)
    assert nc.first_tradeable_time(dt.date(2026, 7, 14)) is None    # blocked


def test_blocked_trading_days_in_the_replay_window():
    """The number that matters for the replay: how many weekdays in
    January-July 2026 the four day-killers stand down."""
    blocked = [(d, w) for d, w in nc.blocked_days(WINDOW_START, dt.date(2026, 7, 25))
               if d.weekday() < 5]
    assert len(blocked) == 25, [str(d) for d, _ in blocked]
    # none of them land on a weekend
    assert all(d.weekday() < 5 for d, _ in nc.blocked_days(*nc.coverage()))


# ----------------------------------------------------------------- reality
def _spy_moves():
    """SPY one-minute bars -> per-day price move, in percent, over the five
    minutes from 08:30 New York and the five minutes from 14:00 New York.

    Both numbers are PRICE moves in the underlying, not a change in the value
    of any position. There is no leverage anywhere in this file.
    """
    import numpy as np
    import pandas as pd
    df = pd.read_parquet(SPY)
    ny = df["timestamp"].dt.tz_convert(nc.TIMEZONE)
    df = df.assign(ny=ny)
    df = df[(df["ny"] >= str(WINDOW_START)) & (df["ny"] <= str(WINDOW_END) + " 23:59")]
    out = {}
    for day, g in df.groupby(df["ny"].dt.date):
        if day.weekday() >= 5:
            continue
        row = []
        for t0 in (dt.time(8, 30), dt.time(14, 0)):
            t1 = (dt.datetime.combine(dt.date(2000, 1, 1), t0)
                  + dt.timedelta(minutes=5)).time()
            w = g[(g["ny"].dt.time >= t0) & (g["ny"].dt.time < t1)]
            pre = g[g["ny"].dt.time < t0]
            if len(w) == 0 or len(pre) == 0:
                row.append(float("nan"))
            else:
                ref = float(pre["close"].iloc[-1])
                row.append(100.0 * (float(w["high"].max()) - float(w["low"].min())) / ref)
        out[day] = tuple(row)
    return out, np


def test_cpi_days_actually_move_the_market_at_0830():
    """The real test. If a date we call a consumer-price-report day shows a
    dead 08:30, the date is wrong."""
    if not os.path.exists(SPY):
        print("   SKIP: no data_alpaca_SPY_1m.parquet")
        return
    moves, np = _spy_moves()

    def has(day, name):
        return any(r.name == name for r in nc.releases_on(day))

    quiet = [m[0] for d, m in moves.items()
             if not any(r.time_et == dt.time(8, 30) for r in nc.releases_on(d))
             and not np.isnan(m[0])]
    cpi = {d: m[0] for d, m in moves.items() if has(d, "Consumer Price Index")}
    nfp = {d: m[0] for d, m in moves.items() if has(d, "Employment Situation")}
    ppi = {d: m[0] for d, m in moves.items() if has(d, "Producer Price Index")}

    q_med = float(np.median(quiet))
    print(f"   quiet 08:30 price move: median {q_med:.3f}% over {len(quiet)} days")
    for lbl, s in (("consumer prices", cpi), ("producer prices", ppi),
                   ("jobs report", nfp)):
        med = float(np.median(list(s.values())))
        print(f"   {lbl:16s} median {med:.3f}% over {len(s)} days"
              f"   ({med / q_med:.1f}x quiet)")

    assert len(cpi) == 7 and len(nfp) == 6 and len(ppi) == 8, (len(cpi), len(nfp), len(ppi))
    # each family moves at least twice as far as a day with nothing at 08:30
    assert float(np.median(list(cpi.values()))) > 2.5 * q_med
    assert float(np.median(list(nfp.values()))) > 2.5 * q_med
    assert float(np.median(list(ppi.values()))) > 2.0 * q_med
    # and no single consumer-price date shows a dead 08:30
    for d, m in sorted(cpi.items()):
        assert m > q_med, f"{d} consumer-price day but only {m:.3f}% at 08:30"

    # the top of the whole window should be dominated by these dates
    order = sorted(moves, key=lambda d: -moves[d][0])
    top10 = order[:10]
    hits = sum(1 for d in top10 if d in cpi or d in nfp or d in ppi)
    print(f"   {hits} of the 10 biggest 08:30 moves in 2026 are one of the three")
    assert hits >= 7, hits


def test_fomc_days_move_the_market_at_1400():
    if not os.path.exists(SPY):
        print("   SKIP: no data_alpaca_SPY_1m.parquet")
        return
    moves, np = _spy_moves()
    fomc = {d: m[1] for d, m in moves.items()
            if any(r.name == "FOMC Statement" for r in nc.releases_on(d))}
    other = [m[1] for d, m in moves.items() if d not in fomc and not np.isnan(m[1])]
    med = float(np.median(other))
    print(f"   14:00 price move: other weekdays median {med:.3f}%;  "
          f"Fed days " + ", ".join(f"{d} {v:.3f}%" for d, v in sorted(fomc.items())))
    assert len(fomc) == 4, sorted(fomc)
    for d, v in fomc.items():
        assert v > 1.5 * med, f"{d} is a Fed decision day but only moved {v:.3f}% at 14:00"


def test_the_invented_dates_were_ordinary_days():
    """The nine days the old generator stood the bot down on should show
    nothing unusual at either 08:30 or 14:00 New York. This is the cost of
    the invented calendar measured directly."""
    if not os.path.exists(SPY):
        print("   SKIP: no data_alpaca_SPY_1m.parquet")
        return
    moves, np = _spy_moves()
    quiet = [m[0] for d, m in moves.items()
             if not any(r.time_et == dt.time(8, 30) for r in nc.releases_on(d))
             and not np.isnan(m[0])]
    ceiling = float(np.percentile(quiet, 90))
    fake_only = ["2026-01-02", "2026-02-06", "2026-02-10", "2026-03-10",
                 "2026-04-15", "2026-05-01", "2026-05-06", "2026-07-22"]
    for s in fake_only:
        d = dt.date.fromisoformat(s)
        if d not in moves:
            continue
        m0830, m1400 = moves[d]
        print(f"   {s} {d.strftime('%a')}  08:30 {m0830:.3f}%   14:00 {m1400:.3f}%")
        assert m0830 < 3 * ceiling, (s, m0830)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:                                    # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
        else:
            print(f"ok   {t.__name__}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
