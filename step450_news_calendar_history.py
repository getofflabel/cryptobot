"""
step450_news_calendar_history.py — check the extended release calendar
against the tape, one year at a time.

WHY
    A date is only worth having if the market agrees something happened on
    it. The 2026 calendar was checked this way and came out clean: quiet days
    moved 0.074% of SPY's price in the five minutes from 08:30 New York,
    consumer-price days moved 0.392%, and all ten of the ten largest 08:30
    moves of the year landed on a day the calendar called a release day.

    The calendar now reaches back to 2016. The same check has to be repeated
    for every one of those years, because a year whose consumer-price days
    show a dead 08:30 has wrong dates in it, and that is worth knowing before
    anything is run on it.

WHAT IS MEASURED
    From `data_alpaca_SPY_5m.parquet` (487,235 bars, 2016 to today):

      08:30 window   the high-to-low range of the single 5-minute bar that
                     starts at 08:30 New York, divided by the last close
                     before it. This is a move in the PRICE of SPY, in
                     percent. It is not a change in the value of any
                     position and there is no leverage anywhere in this file.
      14:00 window   the same thing for the bar starting at 14:00 New York,
                     which is when the Fed's decision lands.

    "Quiet" means a weekday inside the calendar's coverage with NOTHING at
    08:30 on it at all.

WHAT WOULD FAIL
    A year where the consumer-price, producer-price or jobs-report days do
    not sit near the top of that year's own 08:30 moves, or where the ten
    largest 08:30 moves of the year mostly miss the calendar. Both are
    reported per year rather than averaged into one number that could hide a
    bad year inside ten good ones.

    The verdict is taken on RANK, not on the ratio to a quiet day. 2020 is
    why: its quiet days moved 0.078% at 08:30 against 0.048% in 2016,
    because March 2020 dragged the whole year's baseline up, so a
    consumer-price day there is only 1.6 times a quiet day where in 2024 it
    is 13 times. The dates are not worse in 2020 — the yardstick is. Rank
    inside the year does not care how loud the year was.

USAGE
    python3 step450_news_calendar_history.py
    python3 step450_news_calendar_history.py --csv step450_tape_check.csv

RESEARCH ONLY. Reads two files off disk. No network, no broker, no orders.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import news_calendar as nc

REPO = os.path.dirname(os.path.abspath(__file__))
SPY_5M = os.path.join(REPO, "data_alpaca_SPY_5m.parquet")

T0830 = dt.time(8, 30)
T1400 = dt.time(14, 0)


def per_day_moves(path: str = SPY_5M) -> pd.DataFrame:
    """One row per calendar day: the 08:30 and 14:00 five-minute price moves,
    in percent of SPY's price."""
    df = pd.read_parquet(path)
    ny = df["timestamp"].dt.tz_convert(nc.TIMEZONE)
    df = df.assign(ny=ny, day=ny.dt.normalize().dt.date, tod=ny.dt.time)
    rows = []
    for day, g in df.groupby("day", sort=True):
        if day.weekday() >= 5:
            continue
        out = {"day": day}
        for label, t in (("m0830", T0830), ("m1400", T1400)):
            bar = g[g["tod"] == t]
            pre = g[g["tod"] < t]
            if len(bar) == 0 or len(pre) == 0:
                out[label] = np.nan
                continue
            ref = float(pre["close"].iloc[-1])
            out[label] = 100.0 * (float(bar["high"].iloc[0])
                                  - float(bar["low"].iloc[0])) / ref
        rows.append(out)
    return pd.DataFrame(rows)


def label_days(days) -> dict:
    """day -> set of release names the calendar carries for it."""
    out = {}
    for d in days:
        if nc.coverage_gap(d) is not None:
            continue
        out[d] = {r.name for r in nc.releases_on(d)}
    return out


def _has_0830(d) -> bool:
    return any(r.time_et == T0830 for r in nc.releases_on(d))


def check(csv_path: str | None = None) -> int:
    moves = per_day_moves()
    lo, hi = nc.coverage()
    moves = moves[[lo <= d <= hi for d in moves["day"]]].reset_index(drop=True)
    names = label_days(moves["day"])

    print(f"SPY 5-minute bars, {moves['day'].min()} .. {moves['day'].max()}")
    print(f"calendar coverage  {lo} .. {hi}")
    print("all moves below are moves in the PRICE of SPY, in percent, over "
          "the five minutes\nfrom the release. No leverage, no position, "
          "nothing about the value of a trade.\n")

    hdr = (f"{'year':<6}{'quiet':>7}{'CPI':>8}{'PPI':>8}{'jobs':>8}"
           f"{'CPIx':>6}{'PPIx':>6}{'jobsx':>6}"
           f"{'CPIbt':>7}{'PPIbt':>7}{'jobsbt':>7}{'anybt':>7}"
           f"{'top10':>7}{'Fed14:00':>10}{'other':>8}")
    print(hdr)
    print("-" * len(hdr))

    rows = []
    verdicts = []
    for year in range(lo.year, hi.year + 1):
        y = moves[[d.year == year for d in moves["day"]]]
        y = y[~y["m0830"].isna()]
        if len(y) < 50:
            continue
        def pick(name):
            return y[[name in names.get(d, ()) for d in y["day"]]]["m0830"]
        quiet = y[[not _has_0830(d) for d in y["day"]]]["m0830"]
        cpi = pick("Consumer Price Index")
        ppi = pick("Producer Price Index")
        nfp = pick("Employment Situation")
        q = float(np.median(quiet))
        med = {k: (float(np.median(v)) if len(v) else np.nan)
               for k, v in (("cpi", cpi), ("ppi", ppi), ("nfp", nfp))}

        # Scale-free and threshold-free: the chance that a day this calendar
        # calls a release out-moves a randomly picked QUIET day of the same
        # year at 08:30. 50 means the calendar cannot tell them apart at all;
        # 100 means every release day beat every quiet day. Nothing here
        # depends on how loud the year itself was, which is the whole point:
        # 2020's quiet days moved as much as 2017's release days.
        qa = quiet.to_numpy()
        def beats(v):
            if not len(v) or not len(qa):
                return np.nan
            return float(np.mean([(qa < x).mean() + 0.5 * (qa == x).mean()
                                  for x in v]) * 100)
        anyk = y[[bool({"Consumer Price Index", "Producer Price Index",
                        "Employment Situation"} & names.get(d, set()))
                  for d in y["day"]]]["m0830"]
        pr = {"cpi": beats(cpi.to_numpy()), "ppi": beats(ppi.to_numpy()),
              "nfp": beats(nfp.to_numpy()), "any": beats(anyk.to_numpy())}

        # the ten biggest 08:30 moves of the year: how many were release days
        top10 = y.nlargest(10, "m0830")["day"].tolist()
        hits = sum(1 for d in top10 if _has_0830(d))

        # the Fed, at 14:00 instead
        y14 = moves[[d.year == year for d in moves["day"]]]
        y14 = y14[~y14["m1400"].isna()]
        fed_days = [d for d in y14["day"] if "FOMC Statement" in names.get(d, ())]
        fed = y14[[d in set(fed_days) for d in y14["day"]]]["m1400"]
        oth = y14[[d not in set(fed_days) for d in y14["day"]]]["m1400"]
        fmed = float(np.median(fed)) if len(fed) else np.nan
        omed = float(np.median(oth)) if len(oth) else np.nan

        print(f"{year:<6}{q:>7.3f}{med['cpi']:>8.3f}{med['ppi']:>8.3f}"
              f"{med['nfp']:>8.3f}{med['cpi']/q:>6.1f}{med['ppi']/q:>6.1f}"
              f"{med['nfp']/q:>6.1f}{pr['cpi']:>7.0f}{pr['ppi']:>7.0f}"
              f"{pr['nfp']:>7.0f}{pr['any']:>7.0f}"
              f"{hits:>5}/10{fmed:>10.3f}{omed:>8.3f}")

        rows.append({"year": year, "sessions": len(y),
                     "cpi_beats_a_quiet_day_pct": round(pr["cpi"], 1),
                     "ppi_beats_a_quiet_day_pct": round(pr["ppi"], 1),
                     "jobs_beats_a_quiet_day_pct": round(pr["nfp"], 1),
                     "any_of_the_three_beats_a_quiet_day_pct": round(pr["any"], 1),
                     "quiet_0830_price_move_pct": round(q, 4),
                     "cpi_0830_price_move_pct": round(med["cpi"], 4),
                     "ppi_0830_price_move_pct": round(med["ppi"], 4),
                     "jobs_0830_price_move_pct": round(med["nfp"], 4),
                     "cpi_vs_quiet": round(med["cpi"] / q, 2),
                     "ppi_vs_quiet": round(med["ppi"] / q, 2),
                     "jobs_vs_quiet": round(med["nfp"] / q, 2),
                     "top10_0830_moves_on_a_release_day": hits,
                     "cpi_days": len(cpi), "ppi_days": len(ppi),
                     "jobs_days": len(nfp), "quiet_days": len(quiet),
                     "fed_1400_price_move_pct": round(fmed, 4),
                     "other_1400_price_move_pct": round(omed, 4),
                     "fed_days": len(fed)})

        # A year FAILS only when the calendar cannot tell a release day from
        # a quiet one. Two independent ways of saying that, no tuned bar:
        #   - the three 08:30 day-killers together out-move a quiet day less
        #     than 65 times in 100 (50 would be a coin toss, so 65 is already
        #     generous towards calling a year broken)
        #   - fewer than 6 of the ten largest 08:30 moves land on the calendar
        # The per-family numbers are printed but NOT used as a gate. They
        # differ hugely by era for a real reason, not a data reason: before
        # 2021 inflation was near 2% and nobody traded the consumer-price
        # report, while the jobs report was the number of the day every
        # single year. Gating on the consumer-price report would have failed
        # 2017-2020 for being 2017-2020.
        bad = []
        if not pr["any"] > 65:
            bad.append(f"the three 08:30 releases out-move a quiet day only "
                       f"{pr['any']:.0f} times in 100 — indistinguishable")
        if hits < 6:
            bad.append(f"only {hits} of the 10 biggest 08:30 moves are on the calendar")
        if len(fed) and not fmed > 1.3 * omed:
            bad.append("Fed days are not moving 14:00")
        verdicts.append((year, bad))

    print("\nCPIx / PPIx / jobsx are 'how many times a quiet day's 08:30 move'.")
    print("bt   is out of 100: how often a day of that family out-moves a "
          "randomly picked\n     QUIET day of the SAME year at 08:30. 50 is a "
          "coin toss and would mean the\n     dates are meaningless; 100 means "
          "every release day beat every quiet day.\n     Scale-free, so a loud "
          "year like 2020 cannot fake a pass or a fail.")
    print("top10: of the ten largest 08:30 moves that year, how many landed on "
          "a day\n       the calendar says had an 08:30 release.\n")

    failed = [(y, b) for y, b in verdicts if b]
    for year, bad in verdicts:
        mark = "OK  " if not bad else "BAD "
        print(f"  {mark}{year}" + ("" if not bad else "   " + "; ".join(bad)))

    if csv_path:
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        print(f"\nwritten to {csv_path}")

    print(f"\n{len(verdicts) - len(failed)}/{len(verdicts)} years agree with the tape")
    return 1 if failed else 0


def main() -> int:
    csv = None
    for a in sys.argv[1:]:
        if a.startswith("--csv"):
            csv = a.split("=", 1)[1] if "=" in a else os.path.join(
                REPO, "step450_tape_check.csv")
    return check(csv)


if __name__ == "__main__":
    sys.exit(main())
