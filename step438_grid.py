"""
step438_grid.py — what each change is worth, one at a time and together.
Research only. No orders. Nothing here is tuned; every switch below maps to a
line of his teaching quoted in tjr_bot.Config.
"""

from __future__ import annotations

import dataclasses
import sys

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import step438_funnel as F
import tjr_replay
from tjr_bot import Config, NewsCalendar


def main() -> int:
    data = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    base = Config()

    rows = [
        ("as it stands now", base, NewsCalendar()),
        ("...the 1-hour taken back out of the direction",
         dataclasses.replace(base, use_1h_in_direction=False), NewsCalendar()),
        ("...the daily-bias side rule taken back out",
         dataclasses.replace(base, enforce_daily_bias_side=False), NewsCalendar()),
        ("...the pre-market carve-out taken back out",
         dataclasses.replace(base, premarket_sweep_carries_forward=False),
         NewsCalendar()),
        ("...the news gate removed entirely", base, NewsCalendar(rules=False)),
        ("...both-index agreement removed",
         dataclasses.replace(base, enforce_index_agreement=False), NewsCalendar()),
        ("the whole of step437, for comparison",
         dataclasses.replace(base, use_1h_in_direction=False,
                             enforce_daily_bias_side=False,
                             premarket_sweep_carries_forward=False),
         NewsCalendar()),
    ]
    for tag, cfg, news in rows:
        bot, trades, reasons, days, _ = F.walk(cfg=cfg, news=news, data=data)
        print(F.line(tag, F.stats(bot, trades, days)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
