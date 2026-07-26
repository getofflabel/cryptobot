"""
sp500.py — THE S&P BOT. One market, one venue, two validated rules.

WHAT THIS IS
  The S&P side of the desk, trading SPY on Alpaca's paper account
  (alpaca.py, paper host only, $100,000, real prices, real market hours).
  It holds ONE position at a time and it is the sole owner of that
  position.

WHAT IT TRADES, AND WHERE EVERY NUMBER CAME FROM
  Only the two things round 362 actually validated. Nothing else, and
  neither of them is re-tuned here. There is no parameter sweep in this
  file and there is not going to be one.

  RULE 1 — turn-of-month (`turn_of_month`)
    Buy at the close 4 trading days before the month ends, hold 8 trading
    days, only while price is above its 200-day average.
    step362_results.md, Family B, SPY's best cell: +0.5947% of the
    position's own value per trade, 158 trades, 14.9 times the cost of
    trading; the middle slice read once gave +0.2601% of the position's
    own value over 71 trades.
    It was that round's best result and the only rule that beat a coin
    flip on all three instruments, on both scoreboards, in both pools.
    51 of 70 settings survived on SPY, so this is a broad plateau and not
    a spike.

  RULE 2 — the 2-day RSI deep-dip buy (`rsi2_dip_buy`). SPY ONLY.
    Buy when the 2-day RSI closes below 5 while price is above its
    200-day average. Leave when the close gets back above the 5-day
    average or the 2-day RSI snaps above 65 (round 60's exit, carried
    through round 362 unchanged as step362_spx_round2.dipbuy_exit).
    +0.8803% of the position's own value per trade, 22 times the cost of
    trading, and 100th out of 100 against the coin flip in both pools.
    It is a plateau, not a spike: 0.921% of the position at threshold 2,
    0.880% at 5, 0.765% at 8, falling smoothly.
    THE "SPY ONLY" IS LOAD-BEARING. Round 362 placed the futures version
    78.5th out of 100 against the coin flip, so round 60's "12 of 12 on
    both instruments" was one real edge on the tracker and one exit
    riding a rising market on the futures. Do not port this rule to
    ES=F, and do not assume it holds on QQQ without its own round.

WHERE THE EDGE ACTUALLY LIVES: THE CLOSED HOURS, NOT THE SESSION
  Round 370 split the turn-of-month lift into the part earned while the
  market is open and the part earned while it is shut:

                          open to close        close to next open
    SPY turn-of-month     +0.0176% of price    +0.0468% of price
                          = 0.44x a round trip = 1.17x a round trip
    QQQ turn-of-month     +0.0181% of price    +0.0807% of price
                          = 0.45x              = 2.02x

  The lift is 2.7 times larger in the closed hours than in the session on
  SPY, and 4.5 times larger on QQQ. That is WHY the validated rule works
  by holding 7 to 8 days: it is collecting overnight windows, not trading
  days. Three consequences, and all three are structural to this file:

    1. THIS BOT MUST HOLD ACROSS NIGHTS. There is no flatten-before-the-
       close anywhere in here and there must never be one — closing at
       the bell would throw away the entire edge and keep only the 0.44x
       part, which does not pay for the trade.
    2. It has to be robust to the market being shut. It decides at a
       close and acts at the next open, and a decision that comes due
       while the market is shut is deferred to the next session rather
       than dropped.
    3. NO INTRADAY BEHAVIOUR. Round 370 also measured the whole session,
       open to close, at 0.41 times the cost of a single round trip. So
       trading around the position inside the day cannot pay for itself.
       There is nothing intraday in this file on purpose.

WHAT IS DELIBERATELY NOT IN HERE
  - The "stay long above the 200-day average" regime rule. DEMOTED by
    round 362: per trade it loses to a coin flip on all three markets and
    places 6.8th out of 100 on SPY, because entering exactly at the cross
    eats every whipsaw. It is a drawdown blanket, not an entry edge. It
    survives in this file only as a FILTER on the two rules above, which
    is the shape round 362 validated it inside.
  - The volatility-gated trend ported from Bitcoin. REJECTED: 79.8th /
    40.2th / 16.2th against the coin flip. Very few, very long trades in
    a market that went up.
  - The breakout shape ported from gold. NOT CONFIRMED: it passes on
    profit per trade and fails on total growth on all three markets. A
    split verdict is not a pass.
  - Hidden bullish divergence. A CANDIDATE, not validated: it beats the
    coin flip on all three markets, but SPY's middle slice is +0.0113% of
    the position's own value over 21 trades, which is barely positive.
    IT IS THE FIRST THING THAT GETS ADDED if it clears another round —
    see the note at ENTRY_RULES where it would be appended.

WHAT IT COSTS HERE, AND WHY THE VENUE IS THE POINT
  No commission on US equities. The real cost is the gap between the buy
  and sell price, roughly 0.01% to 0.02% of price per fill on SPY, so
  0.02% to 0.04% of the position's own value for a round trip. BloFin's
  SPY perpetual charges 0.1413%. Same rules, same market, opposite
  verdict: turn-of-month makes 14.9 times its trading cost here and 4.2
  times there, which fails the desk's bar. The crypto cost model is NOT
  inherited into this file.

STOPS — chart structure, computed per trade, never a swept percentage
  exits.stop_structure(k=5, n_back=1, use="wick") on the daily frame: the
  last confirmed swing low under the entry, defined by the same fractal
  pivots step41_shorts.confirmed_swings() uses. Two entries produce two
  different stop distances. There is no fixed percentage stop in here.

SIZING — the stop decides the size, leverage is an OUTPUT
  size = dollars risked / stop distance. Dollars risked is 2.0% of the
  account's equity, read from the venue rather than computed. Round 362
  measured where that lands: about 0.9 times the account for the dip-buy
  and 0.5 times for turn-of-month, both under 1x, so this bot never
  borrows. Two caps shrink the position instead of widening the risk
  budget: never more than the account's own equity, and never more than
  the buying power the venue reports. Fractional shares are supported, so
  the size that falls out of the stop is taken as-is down to 0.001 of a
  share.

THE MARKET-HOURS GUARD
  Round 360 found that Alpaca REJECTS market orders outside regular
  trading hours. Both rules decide at a daily close and fill at the next
  open, which is inside the session, so the strategy survives — but this
  bot must never learn the rule by having an order bounced. Every order
  goes through send_market_order(), which refuses to send when
  market_gate() says the session is shut, and a clock that cannot be read
  counts as shut. Not knowing is not a reason to fire.

ATTRIBUTION
  The account has had ZERO orders ever. Every order this file sends
  carries a client_order_id beginning "CBOT_", built by
  make_client_order_id(), which is the only place an id is made. That
  keeps a perfect line between this bot and any manual trade placed later
  from the app. A position this file did not record is NOT adopted and
  NOT flattened: it alerts once and keeps operating.

THE MEMORY LOOP
  Same shape as bitcoin.py, same two files. Before deciding, load_memory()
  reads the last 20 closed trades out of data/ledger.csv, this bot's own
  closed trades out of state, and every lesson in data/learnings.md plus
  state["lessons"]. Two consecutive losses on a rule FLAG it (the arbiter
  may still take it but must attach the note to the record). Three
  consecutive losses that all ended the same way STAND IT DOWN, latched
  in state until a human calls clear_rule_stand_down(). One plain-English
  lesson is written on every close, wins included.
  Be honest about what that is: it reads, it counts, and it gates. It
  does not learn and nothing in this file is called intelligence.

SHIPS OFF
  NEW_ENTRIES_ENABLED is False. The gate sits inside run_sp500 AFTER
  reconcile and after every exit path, so a held position can never be
  stranded by standing the bot down. That placement is not a style
  choice — a gate above the exit logic orphans live positions and a gate
  that touches names bound only on one branch crashes the live path.
  Both have already happened in this repo (test_stand_down_gates.py).

DRY MODE: run_sp500(venue, state, dry=True) computes and prints the whole
  decision with no orders, no state writes, no log lines and no alerts.
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

import exits as E
from step41_shorts import confirmed_swings
from step5_paper_trade import (log_event, notify, now_utc,
                               record_trade_outcome, save_state)
from strategy import rsi

# ===========================================================================
# 1. CONSTANTS — the two rules, the venue's real cost, the risk budget
# ===========================================================================

SYMBOL = "SPY"
VENUE_NAME = "alpaca-paper"
STATE_KEY = "sp500"          # the ONLY state key this file writes, besides
                             # the two shared ledger fields every bot updates
ORDER_TAG = "CBOT"           # every client_order_id starts with this
NY = ZoneInfo("America/New_York")

# -- rule 1, turn-of-month. step362_results.md Family B, SPY's best cell.
# E and H are that cell's exact pair and are NOT re-tuned here.
TOM_DAYS_BEFORE_MONTH_END = 4    # buy at the close with 4 sessions left
TOM_HOLD_SESSIONS = 8            # then out, 8 trading sessions later

# -- rule 2, the 2-day RSI deep-dip buy. step362_results.md Families A & C.
RSI_LEN = 2
RSI_BUY_BELOW = 5.0              # the round's own cell; 2 / 5 / 8 all work
RSI_EXIT_ABOVE = 65.0            # round 60's exit, unchanged
DIP_EXIT_SMA = 5                 # or the close back above the 5-day average

# -- the filter both rules sit inside (a filter, NOT an entry rule of its own)
TREND_SMA = 200

# -- what a round trip really costs at this venue -------------------------
# No commission on US equities. The cost is the gap between the buy and the
# sell price: roughly 0.01% to 0.02% of price per fill on SPY, so 0.02% to
# 0.04% of the position's own value for a round trip. The pessimistic end is
# used. THIS IS NOT BLOFIN'S 0.1413% — the crypto cost model does not travel
# to a stock broker, and the whole reason this venue exists is that it does
# not (step362_results.md, Family E).
ROUND_TRIP_COST_PCT = 0.04       # of the position's own value

# -- the stop, and the size that falls out of it --------------------------
K_SWING = 5                      # confirmed-swing fractal lookback; exits.py's
                                 # own default and what round 362 measured the
                                 # wider of its two stop distributions at
# Fallbacks used ONLY when no confirmed swing low exists under the entry yet.
# These are round 362's own measured middle distances with 5-bar swings, so
# the fallback is the same magnitude the mechanism itself produces rather
# than an invented number.
FALLBACK_STOP_PCT_DIP = 2.26     # of price, under entry
FALLBACK_STOP_PCT_TOM = 4.24     # of price, under entry
#
# DO NOT RE-TIGHTEN THESE. What died in round 60 was a tight stop at one
# times the average daily range, about 1.3% of price, and that verdict
# stands. A structure stop is not that. Round 362 measured the overnight
# gap against these levels directly: the overnight move ALONE exceeded the
# 1.84%-of-price dip-buy distance (3-bar swings) on 1.3% of days and the
# 3.12%-of-price turn-of-month distance on 0.2% of days; with the 5-bar
# swings this file uses it is 0.8% and 0.1%. The index's own chart gives
# these trades enough room to survive their own overnight window. Narrowing
# the stop to "protect" against the gap re-creates the exact failure round
# 60 already paid for.

RISK_PCT = 2.0                   # of the account's equity, risked per trade
QTY_STEP = 0.001                 # Alpaca supports fractional shares
MIN_QTY = 0.001

# THE BAR REQUEST. Two things about Alpaca's history endpoint that cost an
# afternoon to find, both verified live on 2026-07-25:
#   1. Asking for daily bars with NO `start` returns "bars": null. Not an
#      error, not an empty list — null. A request without a start date
#      silently reads as "no history at all".
#   2. `start` plus `limit` returns the OLDEST `limit` bars from that date
#      forward, not the newest. Asking for 800 bars from 2023-01-01 hands
#      back 2023-01-03 to 2026-03-12 and stops four months short of today.
# So the window is asked for by DATE, wide enough that `limit` never binds,
# and the tail is taken here. About 640 calendar days is roughly 440
# sessions: deep enough to warm the 200-day average twice over and to keep
# an open trade's own entry bar in the window far longer than an 8-session
# hold.
DAILY_LOOKBACK_DAYS = 640
DAILY_BARS = 1000                # the request cap, deliberately never binding

# -- the memory loop ------------------------------------------------------
LEDGER_CSV = os.path.join("data", "ledger.csv")
LEARNINGS_MD = os.path.join("data", "learnings.md")
MEMORY_TRADES_N = 20             # closed trades read back before deciding
FLAG_AFTER_LOSSES = 2            # consecutive losses on a rule -> FLAGGED
STAND_DOWN_AFTER_LOSSES = 3      # three that all ended the same way -> down
MAX_LESSONS_ON_RECORD = 6        # lessons copied onto a trade's own record


# ===========================================================================
# 2. THE STAND-DOWN GATE
# ===========================================================================
# This file ships OFF. It is written, tested and inert. Wiring it into
# daemon.py and flipping this flag are a human's job, in that order.
#
# The gate itself lives inside run_sp500 AFTER reconcile and AFTER every
# exit path, so a held position always still closes normally with the flag
# off. Do not move it up: a gate above the exit logic orphans live
# positions, and a gate placed where it reads names that are only bound on
# one branch crashes the live path on an unbound name. Both have already
# happened in this repo, which is why test_stand_down_gates.py exists.
NEW_ENTRIES_ENABLED = False


# ===========================================================================
# 3. FORMATTING — every percentage carries its base, always
# ===========================================================================

def price_move_pct(from_price: float, to_price: float) -> str:
    """A move in PRICE, labelled as such."""
    if not from_price:
        return "n/a"
    return f"{(to_price / from_price - 1) * 100:+.2f}% of price"


def position_value_pct(value: float) -> str:
    """A profit or loss as a share of the FULL size of the position — the
    number round 362 measured every rule in, and the number that has to
    beat the cost of trading."""
    if value is None:
        return "n/a"
    return f"{value:+.4f}% of the position's own value"


def account_pct(value: float) -> str:
    """A share of the whole account's equity."""
    if value is None:
        return "n/a"
    return f"{value:+.2f}% of the account"


def _fmt(v, nd: int = 2) -> str:
    return f"{v:,.{nd}f}" if v is not None else "n/a"


def _fmt_day(d) -> str:
    return f"{pd.Timestamp(d):%Y-%m-%d}"


# ===========================================================================
# 4. THE MEMORY — read, count, gate. Not a model. Not learning.
# ===========================================================================

@dataclass
class RuleMemory:
    """What the counters say about one entry rule, right now."""
    rule: str
    attempts: int = 0
    consecutive_losses: int = 0
    identical_failures: int = 0      # leading losses that share one reason
    last_reason: str | None = None
    status: str = "clear"            # "clear" | "flagged" | "stood_down"
    note: str = ""

    def as_dict(self) -> dict:
        return {"rule": self.rule, "attempts": self.attempts,
                "consecutive_losses": self.consecutive_losses,
                "identical_failures": self.identical_failures,
                "last_reason": self.last_reason, "status": self.status,
                "note": self.note}


def _norm_time(value) -> str:
    """One comparable timestamp string out of the two formats this repo
    writes: data/ledger.csv stores ISO-8601 with an offset, this bot's own
    records store now_utc()'s 'YYYY-MM-DD HH:MM:SS UTC'. Normalised to the
    minute, which is all deduplication needs."""
    try:
        return f"{pd.Timestamp(str(value).replace(' UTC', '+00:00')):%Y-%m-%d %H:%M}"
    except Exception:
        return str(value)[:16]


def _split_reason(raw: str) -> tuple[str, str]:
    """Pull a rule name out of a data/ledger.csv `reason` cell.

    The SELL rows in that file carry an EXIT reason, not a rule name, so on
    its own the shared ledger cannot attribute a close to the rule that
    took it. Two shapes are understood:
      "turn_of_month:structure_stop" -> ("turn_of_month", "structure_stop")
      "turn_of_month"                -> ("turn_of_month", "turn_of_month")
      "TP/SL"                        -> ("", "TP/SL")
    Anything unattributable still counts as a recent close; it just does not
    move any rule's counters, which is the honest outcome rather than a
    guess."""
    raw = (raw or "").strip()
    if ":" in raw:
        rule, _, reason = raw.partition(":")
        return rule.strip(), reason.strip() or rule.strip()
    known = {r.name for r in ENTRY_RULES}
    return (raw, raw) if raw in known else ("", raw)


def read_ledger_trades(path: str = LEDGER_CSV,
                       n: int = MEMORY_TRADES_N) -> list[dict]:
    """The last `n` CLOSED trades out of data/ledger.csv — the file
    export_journal.py has been writing since the beginning.

    Its header is fixed (timestamp, symbol, action, price, quantity,
    reason, mode, outcome, pnl) and closes are the rows whose `action` is
    SELL. Returned OLDEST FIRST. A missing or malformed file is an empty
    memory, never an exception: a bot must not refuse to trade because its
    diary is missing, it should trade knowing it has none."""
    out: list[dict] = []
    try:
        with open(path, newline="") as f:
            for row in csv.DictReader(f):
                if (row.get("action") or "").strip().upper() != "SELL":
                    continue
                try:
                    pnl = float(row.get("pnl") or 0.0)
                except (TypeError, ValueError):
                    pnl = 0.0
                rule, reason = _split_reason(row.get("reason", ""))
                out.append({"time": _norm_time(row.get("timestamp", "")),
                            "symbol": row.get("symbol", ""),
                            "rule": rule, "reason": reason, "pnl": pnl,
                            "outcome": (row.get("outcome") or "").strip().lower(),
                            "source": "ledger.csv"})
    except Exception:
        return []
    out.sort(key=lambda r: r["time"])
    return out[-n:] if n else out


_LESSON_HEAD_RE = re.compile(r"^###\s+(?P<date>.+?)\s+—\s+(?P<trigger>.+?)\s*$")


def _parse_learnings_md(path: str) -> list[dict]:
    """Parse data/learnings.md's 'Trade reviews' section back into lesson
    dictionaries. The format is export_journal.write_learnings()'s own and
    is matched exactly:

        ### <date> — <trigger>
        - <trade>
        - conditions: <conditions>
        - **lesson:** <why>

    That file is written newest-first; this returns oldest-first so it
    composes with everything else here. An unreadable file is no lessons."""
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except Exception:
        return []

    out, cur = [], None
    for raw in lines:
        line = raw.rstrip()
        m = _LESSON_HEAD_RE.match(line)
        if m:
            if cur:
                out.append(cur)
            cur = {"date": m.group("date").strip(),
                   "trigger": m.group("trigger").strip(),
                   "trade": "", "conditions": "", "why": "",
                   "source": "learnings.md"}
            continue
        if cur is None:
            continue
        if line.startswith("- **lesson:**"):
            cur["why"] = line[len("- **lesson:**"):].strip()
        elif line.startswith("- conditions:"):
            cur["conditions"] = line[len("- conditions:"):].strip()
        elif line.startswith("- ") and not cur["trade"]:
            cur["trade"] = line[2:].strip()
    if cur:
        out.append(cur)
    out.reverse()
    return out


def read_lessons(state: dict, path: str = LEARNINGS_MD) -> list[dict]:
    """Every lesson this desk has written to itself.

    Two sources, deliberately: state["lessons"] is the canonical store (it
    is what export_journal.write_learnings RENDERS learnings.md from), and
    the file itself is parsed as well so lessons that only survive on disk
    — an older export, a state reset — are not lost to the loop. Deduped on
    (date, lesson text). Oldest first."""
    lessons: list[dict] = []
    for L in state.get("lessons", []) or []:
        if not isinstance(L, dict):
            continue
        lessons.append({"date": L.get("date", ""),
                        "trigger": L.get("trigger", ""),
                        "trade": L.get("trade", ""),
                        "conditions": L.get("conditions", ""),
                        "why": L.get("why", ""), "source": "state"})
    lessons += _parse_learnings_md(path)

    seen, deduped = set(), []
    for L in lessons:
        key = (L.get("date", ""), L.get("why", ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(L)
    return deduped


def _own_closed_trades(state: dict) -> list[dict]:
    """This bot's OWN closed trades out of its state — the authoritative
    per-rule record, since the shared ledger only carries whatever
    export_journal happens to map. Oldest first."""
    out = []
    for rec in (state.get(STATE_KEY, {}) or {}).get("trades", []) or []:
        if not isinstance(rec, dict):
            continue
        pnl = float(rec.get("pnl", 0.0) or 0.0)
        out.append({"time": _norm_time(rec.get("exit_time")
                                       or rec.get("entry_time") or ""),
                    "symbol": SYMBOL, "rule": rec.get("rule", ""),
                    "reason": rec.get("reason", ""), "pnl": pnl,
                    "outcome": "win" if pnl > 0 else "loss",
                    "source": "sp500"})
    out.sort(key=lambda r: r["time"])
    return out


def _merge_closed(own: list[dict], ledger: list[dict]) -> list[dict]:
    """One timeline out of both sources, deduped. The same close can appear
    in both, so it is identified by (timestamp to the minute, profit or
    loss to the cent); this bot's own record wins because it carries the
    rule name."""
    merged = list(own)
    seen = {(r["time"], round(r["pnl"], 2)) for r in own}
    for r in ledger:
        key = (r["time"], round(r["pnl"], 2))
        if key in seen:
            continue
        seen.add(key)
        merged.append(r)
    merged.sort(key=lambda r: r["time"])
    return merged


def _count_rule(closed: list[dict], rule: str) -> RuleMemory:
    """Walk this rule's closes NEWEST FIRST and count the leading run of
    losses, plus the leading run of losses that all ended for the same
    reason. Pure counting — there is no inference here and none intended."""
    mine = [r for r in closed if (r.get("rule") or "") == rule]
    mem = RuleMemory(rule=rule, attempts=len(mine))
    streak_reason = None
    for r in reversed(mine):
        if r.get("pnl", 0.0) > 0:
            break
        mem.consecutive_losses += 1
        reason = (r.get("reason") or "").strip()
        if mem.consecutive_losses == 1:
            streak_reason = reason
            mem.last_reason = reason
        if reason and reason == streak_reason:
            mem.identical_failures += 1
        else:
            streak_reason = None
    return mem


def load_memory(state: dict, ledger_path: str | None = None,
                learnings_path: str | None = None) -> dict:
    """EVERYTHING THIS BOT KNOWS ABOUT ITSELF, loaded before it decides.

    Latched stand-downs stored in state[STATE_KEY]["rules_stood_down"] are
    applied on top and always win: once a rule is stood down it STAYS stood
    down, even if the counters would now read clear, until a human calls
    clear_rule_stand_down(). A later winning trade must not quietly bring
    back a rule a person deliberately parked.

    Both paths are resolved at CALL time, not import time, so a caller or a
    test can point the loop at a different journal without reaching inside
    it."""
    ledger_path = LEDGER_CSV if ledger_path is None else ledger_path
    learnings_path = LEARNINGS_MD if learnings_path is None else learnings_path
    ledger_trades = read_ledger_trades(ledger_path, MEMORY_TRADES_N)
    own = _own_closed_trades(state)
    closed = _merge_closed(own, ledger_trades)
    lessons = read_lessons(state, learnings_path)
    latched = (state.get(STATE_KEY, {}) or {}).get("rules_stood_down", {}) or {}

    rules: dict[str, dict] = {}
    for rule in [r.name for r in ENTRY_RULES]:
        mem = _count_rule(closed, rule)
        if rule in latched:
            mem.status = "stood_down"
            mem.note = (f"STOOD DOWN since {latched[rule].get('since', '?')} — "
                        f"{latched[rule].get('why', 'repeated identical failures')}. "
                        f"A human must clear this.")
        elif (mem.identical_failures >= STAND_DOWN_AFTER_LOSSES
              and mem.last_reason):
            mem.status = "stood_down"
            mem.note = (f"{mem.identical_failures} losses in a row all ending "
                        f"'{mem.last_reason}' — standing this rule down until "
                        f"a human clears it")
        elif mem.consecutive_losses >= FLAG_AFTER_LOSSES:
            mem.status = "flagged"
            mem.note = (f"the last {mem.consecutive_losses} attempts all lost "
                        f"(most recent ended '{mem.last_reason}') — taking "
                        f"this setup anyway, noted on the record")
        rules[rule] = mem.as_dict()

    return {"rules": rules, "closed_trades": closed, "n_closed": len(closed),
            "n_ledger_rows": len(ledger_trades), "n_own_trades": len(own),
            "lessons": lessons, "n_lessons": len(lessons),
            "latched_stand_downs": sorted(latched)}


def apply_memory_stand_downs(state: dict, memory: dict) -> list[str]:
    """Persist any NEW stand-down the counters just produced, so it latches
    across restarts and needs a human to clear. Returns the rules newly
    latched this cycle. Writes only state[STATE_KEY]."""
    rec = _record(state)
    latched = rec.setdefault("rules_stood_down", {})
    newly = []
    for rule, m in memory["rules"].items():
        if m["status"] != "stood_down" or rule in latched:
            continue
        latched[rule] = {"since": now_utc(), "why": m["note"],
                         "consecutive_losses": m["consecutive_losses"],
                         "reason": m["last_reason"], "cleared_by": None}
        newly.append(rule)
    return newly


def clear_rule_stand_down(state: dict, rule: str, who: str = "human") -> bool:
    """THE HUMAN'S RELEASE VALVE. A stood-down rule only ever comes back
    through this function — there is no automatic re-enable and there is
    not going to be one. True if something was actually cleared."""
    rec = _record(state)
    latched = rec.setdefault("rules_stood_down", {})
    if rule not in latched:
        return False
    entry = latched.pop(rule)
    history = rec.setdefault("stand_down_history", [])
    history.append({**entry, "cleared_by": who, "cleared_at": now_utc()})
    rec["stand_down_history"] = history[-50:]
    log_event({"action": "sp500_stand_down_cleared", "rule": rule,
               "cleared_by": who})
    return True


# ===========================================================================
# 5. THE TRADING CALENDAR — turn-of-month needs to know the FUTURE
# ===========================================================================
# "Four trading days before the month ends" cannot be counted out of price
# history alone: it needs to know how many sessions are still LEFT in the
# month, holidays included. So the venue's own calendar is asked first and a
# computed New York Stock Exchange calendar is the fallback. Which source
# answered is named in the log, every cycle, so a wrong count is traceable.

def _easter(year: int) -> date:
    """Western (Gregorian) Easter Sunday. Good Friday is two days earlier
    and it is the one market holiday that is not on a fixed rule."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month = (h + ll - 7 * m + 114) // 31
    day = ((h + ll - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The n-th `weekday` (Monday=0) of a month."""
    d = date(year, month, 1)
    shift = (weekday - d.weekday()) % 7
    return d + timedelta(days=shift + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = (date(year + 1, 1, 1) if month == 12
         else date(year, month + 1, 1)) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date | None:
    """The New York Stock Exchange's weekend rule for a fixed-date holiday:
    a Saturday holiday is taken on the Friday before, a Sunday holiday on
    the Monday after. New Year's Day is the exception — a Saturday New
    Year's is simply not observed, because the market does not close on the
    last day of the previous year for it."""
    if d.weekday() == 5:
        return None if (d.month == 1 and d.day == 1) else d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def us_market_holidays(year: int) -> set:
    """The days the New York Stock Exchange is shut, computed. Used as the
    fallback when the venue's own calendar is unavailable."""
    out = set()
    for d in (date(year, 1, 1), date(year, 7, 4), date(year, 12, 25)):
        o = _observed(d)
        if o is not None:
            out.add(o)
    if year >= 2022:                       # Juneteenth, a market holiday
        o = _observed(date(year, 6, 19))   # from 2022
        if o is not None:
            out.add(o)
    out.add(_nth_weekday(year, 1, 0, 3))   # Martin Luther King Jr Day
    out.add(_nth_weekday(year, 2, 0, 3))   # Washington's Birthday
    out.add(_last_weekday(year, 5, 0))     # Memorial Day
    out.add(_nth_weekday(year, 9, 0, 1))   # Labor Day
    out.add(_nth_weekday(year, 11, 3, 4))  # Thanksgiving
    out.add(_easter(year) - timedelta(days=2))   # Good Friday
    return out


def _computed_sessions(start: date, end: date) -> list:
    """Every weekday between start and end that is not a market holiday."""
    holidays = set()
    for y in range(start.year, end.year + 1):
        holidays |= us_market_holidays(y)
    out, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            out.append(d)
        d += timedelta(days=1)
    return out


def venue_sessions(venue, start: date, end: date) -> tuple[list, str]:
    """Every trading session between two dates, and WHERE the answer came
    from. The venue is asked first because it knows about early closes and
    unscheduled closures that no computed calendar can predict; the
    computed New York Stock Exchange calendar is the fallback. Returns
    (sorted dates, source name)."""
    fn = getattr(venue, "calendar", None)
    if callable(fn):
        try:
            rows = fn(str(start), str(end)) or []
            days = sorted({date.fromisoformat(str(r["date"])[:10])
                           for r in rows if r.get("date")})
            if days:
                return days, "venue calendar"
        except Exception:
            pass
    # alpaca.py does not expose a calendar method today. Its generic reader
    # is used opportunistically rather than modifying that file; if it is
    # absent or errors, the computed calendar answers and says so.
    getter = getattr(venue, "_get", None)
    if callable(getter):
        try:
            rows = getter("/v2/calendar",
                          {"start": str(start), "end": str(end)}) or []
            days = sorted({date.fromisoformat(str(r["date"])[:10])
                           for r in rows if r.get("date")})
            if days:
                return days, "venue calendar"
        except Exception:
            pass
    return _computed_sessions(start, end), "computed NYSE calendar"


def trading_days_left_in_month(day: date, sessions: list) -> int | None:
    """How many trading sessions come AFTER `day` inside its own calendar
    month. 0 means `day` is the month's last session. This is the number
    round 362's turn-of-month rule is defined on (step362_spx_round2.
    month_position: days_left == E). None when the session list does not
    reach the end of that month, because an under-count here would fire the
    rule on the wrong day."""
    month_end = (date(day.year + 1, 1, 1) if day.month == 12
                 else date(day.year, day.month + 1, 1)) - timedelta(days=1)
    if not sessions or max(sessions) < month_end:
        return None
    return sum(1 for s in sessions
               if s.year == day.year and s.month == day.month and s > day)


def sessions_between(start: date, end: date, sessions: list) -> int:
    """How many trading sessions separate two session dates — 0 if they are
    the same session, 1 for consecutive sessions. This is how a hold is
    counted, in SESSIONS, so a weekend or a holiday in the middle never
    shortens or lengthens the trade."""
    inside = [s for s in sessions if start <= s <= end]
    return max(0, len(inside) - 1)


# ===========================================================================
# 6. THE RULES
# ===========================================================================

@dataclass
class RuleSignal:
    """What a rule returns when it wants a trade. `stop_level` is a PRICE on
    the chart, never a percentage: the rule says where structure proves it
    wrong, and the size falls out of that."""
    rule: str
    direction: int                 # +1 long. Both validated rules are long.
    stop_level: float
    reason: str
    context: dict = field(default_factory=dict)


@dataclass
class EntryRule:
    """One entry rule. `fn(d, ctx) -> RuleSignal | None`. `priority` breaks
    ties between rules that fire on the same bar — lower is stronger."""
    name: str
    fn: object
    priority: int
    description: str


def anchor_swing(d: pd.DataFrame, entry_idx: int,
                 entry_price: float) -> float | None:
    """WHICH price on the chart the stop belongs to — the most recent
    CONFIRMED swing low under the entry as of `entry_idx`, via
    step41_shorts.confirmed_swings(). Provenance only: a stop level in a log
    line should point at a swing a human can find on the chart, not be a
    number that appeared from nowhere. None when no confirmed swing low
    exists yet, which is the case the fallback distance covers."""
    _, sl_price = confirmed_swings(d, K_SWING)
    window = sl_price.iloc[:entry_idx + 1].dropna()
    below = window[window < entry_price]
    return float(below.iloc[-1]) if not below.empty else None


def structure_stop(d: pd.DataFrame, entry_idx: int, entry_price: float,
                   fallback_pct: float) -> tuple[float, float | None]:
    """THE STOP: the last confirmed swing low under the entry, computed per
    trade off the daily frame with exits.stop_structure(k=5, n_back=1,
    use="wick"). That is the object round 362 measured, called directly
    rather than reimplemented.

    NO TRAILING. bitcoin.py's ratcheting floor and its 1.5%-of-price buffer
    were validated on Bitcoin's 4-hour bars. Round 362 measured a stop that
    sits at the structure level as of entry and stays there. Constants do
    not travel between markets, and neither do mechanisms.

    Returns (stop price, the swing it rests on or None if the fallback was
    used). The fallback distance is round 362's own measured middle
    distance for this rule, so it is the same magnitude the mechanism
    produces."""
    swing = anchor_swing(d, entry_idx, entry_price)
    s = E.build_series_ctx(d, k=K_SWING)
    tc = E.build_trade_ctx(s, entry_idx, entry_price, 1)
    level = E.stop_structure(k=K_SWING, n_back=1, use="wick").level_fn(tc,
                                                                      entry_idx)
    if level is None or float(level) >= entry_price:
        return entry_price * (1 - fallback_pct / 100.0), None
    return float(level), swing


def _sma(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n).mean()


def rule_turn_of_month(d: pd.DataFrame, ctx: dict) -> RuleSignal | None:
    """RULE 1 — turn-of-month. Round 362's best result and the only rule
    that beat a coin flip on all three instruments, both scoreboards, both
    pools.

    Buy at the close of the session with TOM_DAYS_BEFORE_MONTH_END trading
    days still to come in the month, while price is above its 200-day
    average. Hold TOM_HOLD_SESSIONS trading sessions, then out. The order
    fills at the NEXT open, which is the same convention backtest.py used
    to measure it (bar N's signal, bar N+1's open).

    That 8-session hold is the edge. Round 370 measured the lift as
    +0.0468% of price in the closed hours against +0.0176% of price inside
    the session, so most of what this rule collects is earned while the
    market is shut. Shortening the hold, or closing before the bell,
    throws the edge away."""
    i = len(d) - 1
    close = float(d["close"].iloc[i])
    trend = _sma(d["close"], TREND_SMA).iloc[i]
    if pd.isna(trend) or close <= float(trend):
        return None

    left = ctx.get("trading_days_left_in_month")
    if left is None or int(left) != TOM_DAYS_BEFORE_MONTH_END:
        return None

    stop, swing = structure_stop(d, i, close, FALLBACK_STOP_PCT_TOM)
    where = (f"resting on the confirmed swing low {swing:,.2f}" if swing
             else f"no confirmed swing low yet, so the stop fell back to "
                  f"{FALLBACK_STOP_PCT_TOM:.2f}% of price under entry")
    return RuleSignal(
        rule="turn_of_month", direction=1, stop_level=stop,
        reason=(f"{TOM_DAYS_BEFORE_MONTH_END} trading days left in the month "
                f"and price is above its {TREND_SMA}-day average — buying at "
                f"this close to hold {TOM_HOLD_SESSIONS} trading sessions "
                f"across the nights in between; stop at structure, {where}"),
        context={"anchor_swing": swing, "close": close,
                 "trading_days_left_in_month": int(left),
                 "trend_avg": float(trend),
                 "hold_sessions": TOM_HOLD_SESSIONS,
                 "fallback_pct_of_price": FALLBACK_STOP_PCT_TOM})


def rule_rsi2_dip_buy(d: pd.DataFrame, ctx: dict) -> RuleSignal | None:
    """RULE 2 — the 2-day RSI deep-dip buy. SPY ONLY.

    Buy when the 2-day RSI closes below 5 while price is above its 200-day
    average. 100th out of 100 against the coin flip in both pools, +0.8803%
    of the position's own value per trade, 22 times the cost of trading.

    THIS RULE IS NOT PORTABLE AND THE GUARD BELOW IS DELIBERATE. Round 362
    placed the futures version 78.5th out of 100 against the coin flip: on
    ES=F it is not distinguishable from luck, and what looked like the same
    edge on two instruments was one real edge on the tracker and one exit
    riding a rising market on the futures. If this file is ever pointed at
    another symbol, this rule must not come along without its own round."""
    if str(ctx.get("symbol", SYMBOL)).upper() != "SPY":
        return None

    i = len(d) - 1
    close = float(d["close"].iloc[i])
    trend = _sma(d["close"], TREND_SMA).iloc[i]
    if pd.isna(trend) or close <= float(trend):
        return None

    r = rsi(d["close"], RSI_LEN).iloc[i]
    if pd.isna(r) or float(r) >= RSI_BUY_BELOW:
        return None

    stop, swing = structure_stop(d, i, close, FALLBACK_STOP_PCT_DIP)
    where = (f"resting on the confirmed swing low {swing:,.2f}" if swing
             else f"no confirmed swing low yet, so the stop fell back to "
                  f"{FALLBACK_STOP_PCT_DIP:.2f}% of price under entry")
    return RuleSignal(
        rule="rsi2_dip_buy", direction=1, stop_level=stop,
        reason=(f"the 2-day strength gauge closed at {float(r):.1f}, under "
                f"{RSI_BUY_BELOW:.0f}, while price is still above its "
                f"{TREND_SMA}-day average — a deep dip inside an uptrend; "
                f"stop at structure, {where}"),
        context={"anchor_swing": swing, "close": close,
                 "rsi": float(r), "trend_avg": float(trend),
                 "fallback_pct_of_price": FALLBACK_STOP_PCT_DIP})


# THE RULE REGISTRY. Only what round 362 validated is in it.
#
# THE NEXT ADDITION, IF IT EVER CLEARS: hidden bullish divergence — price
# makes a higher low while the 7-day strength gauge makes a lower low,
# inside an uptrend, over a 40-day lookback. Round 362 has it beating the
# coin flip on all three markets (99.8th / 100th on SPY), but SPY's middle
# slice is +0.0113% of the position's own value over 21 trades, which is
# barely positive. It is a CANDIDATE. It gets appended here, and nowhere
# else in this file changes, once another round clears it.
ENTRY_RULES: list[EntryRule] = [
    EntryRule(name="turn_of_month", fn=rule_turn_of_month, priority=1,
              description="buy at the close with 4 trading days left in the "
                          "month, hold 8 trading sessions, only above the "
                          "200-day average (step362_results.md Family B: "
                          "+0.5947% of the position's own value per trade, "
                          "158 trades, 14.9 times the cost of trading)"),
    EntryRule(name="rsi2_dip_buy", fn=rule_rsi2_dip_buy, priority=2,
              description="buy when the 2-day strength gauge closes under 5 "
                          "above the 200-day average, SPY only "
                          "(step362_results.md Families A and C: +0.8803% of "
                          "the position's own value per trade, 22 times the "
                          "cost of trading, 100th out of 100 against a coin "
                          "flip)"),
]


def evaluate_rules(d: pd.DataFrame, ctx: dict) -> list[RuleSignal]:
    """Run every entry rule over the same bar. A rule that raises is a bug
    in that rule, not a reason to stop trading the others — it is caught,
    reported and skipped."""
    out = []
    for rule in ENTRY_RULES:
        try:
            sig = rule.fn(d, ctx)
        except Exception as e:
            print(f"  [SP500] rule {rule.name} raised, skipping it: "
                  f"{str(e)[:100]}")
            log_event({"action": "sp500_rule_error", "rule": rule.name,
                       "error": str(e)[:200]})
            continue
        if sig is not None:
            out.append(sig)
    return out


# ===========================================================================
# 7. THE ARBITER — one decision, memory-aware, never silent about a flag
# ===========================================================================

@dataclass
class Verdict:
    action: str                    # "enter" | "stand_down" | "no_signal"
    signal: RuleSignal | None = None
    reason: str = ""
    memory_note: str = ""
    considered: list = field(default_factory=list)


def arbitrate(signals: list[RuleSignal], memory: dict) -> Verdict:
    """Decide between the rules that fired. Pure — no reads, no writes.

    1. A rule the memory has STOOD DOWN never gets considered at all.
    2. If what is left wants opposite directions, nobody trades this bar.
       This bot holds one position on SPY, and two rules disagreeing is the
       absence of a thesis rather than a reason to pick a favourite.
    3. Otherwise the lowest priority number wins. If the memory has FLAGGED
       it, the verdict carries an explicit note and that note is required —
       a flagged rule is never taken silently."""
    considered, live = [], []
    for s in signals:
        m = memory["rules"].get(s.rule, {"status": "clear", "note": ""})
        considered.append({"rule": s.rule, "direction": s.direction,
                           "status": m["status"], "note": m.get("note", "")})
        if m["status"] == "stood_down":
            continue
        live.append((s, m))

    if not live:
        if considered:
            blocked = ", ".join(c["rule"] for c in considered)
            return Verdict(action="stand_down", considered=considered,
                           reason=f"every rule that fired is stood down by "
                                  f"the memory ({blocked})",
                           memory_note="; ".join(c["note"] for c in considered
                                                 if c["note"]))
        return Verdict(action="no_signal", considered=considered,
                       reason="no rule fired on this bar")

    if len({s.direction for s, _ in live}) > 1:
        return Verdict(action="stand_down", considered=considered,
                       reason="the rules disagree on direction — this bot "
                              "holds ONE position on SPY, so nobody trades "
                              "this bar")

    prio = {r.name: r.priority for r in ENTRY_RULES}
    live.sort(key=lambda pair: prio.get(pair[0].rule, 99))
    chosen, mem = live[0]
    note = mem.get("note", "") if mem["status"] == "flagged" else ""
    if mem["status"] == "flagged" and not note:
        note = (f"{chosen.rule} is flagged by the memory "
                f"({mem.get('consecutive_losses', '?')} losses in a row)")
    return Verdict(action="enter", signal=chosen, considered=considered,
                   reason=chosen.reason, memory_note=note)


# ===========================================================================
# 8. STATE AND VENUE READS — read the venue, never compute what it reports
# ===========================================================================

def _fresh_record() -> dict:
    return {"open_trade": None, "last_bar_day": None, "trades": [],
            "realized_pnl_total": 0.0, "rules_stood_down": {},
            "stand_down_history": [], "deferred": None}


def _record(state: dict) -> dict:
    rec = state.setdefault(STATE_KEY, _fresh_record())
    for k, v in _fresh_record().items():
        rec.setdefault(k, v)
    return rec


def account_snapshot(venue) -> dict:
    """Equity, buying power and cash READ from the venue. Not one of them
    is derived here — the same discipline BLOFIN_API_REFERENCE.md records
    after a night of getting margin arithmetic wrong by hand."""
    try:
        a = venue.account() or {}
    except Exception as e:
        return {"ok": False, "why": str(e)[:120], "equity": 0.0,
                "buying_power": 0.0, "cash": 0.0}
    def _f(key):
        try:
            return float(a.get(key) or 0.0)
        except (TypeError, ValueError):
            return 0.0
    return {"ok": True, "equity": _f("equity"),
            "buying_power": _f("buying_power"), "cash": _f("cash"),
            "status": a.get("status")}


def position_snapshot(venue, symbol: str = SYMBOL) -> dict | None:
    """Shares, average entry, market value and unrealized profit, straight
    from the venue. None means the venue reports no position at all."""
    try:
        p = venue.position(symbol)
    except Exception:
        return None
    if not p:
        return None
    def _f(key):
        try:
            return float(p.get(key) or 0.0)
        except (TypeError, ValueError):
            return 0.0
    qty = _f("qty")
    if abs(qty) < MIN_QTY / 2:
        return None
    return {"qty": qty, "avg_entry_price": _f("avg_entry_price"),
            "market_value": _f("market_value"),
            "unrealized_pl": _f("unrealized_pl"),
            "side": p.get("side", "long")}


def last_price(venue, symbol: str = SYMBOL, fallback: float = 0.0) -> float:
    """The venue's own latest trade price, with the last closed bar's close
    as the fallback when the quote cannot be read."""
    try:
        t = venue.last_trade(symbol) or {}
        px = float(t.get("p") or 0.0)
        return px if px > 0 else fallback
    except Exception:
        return fallback


def load_daily(venue, session_date: date, symbol: str = SYMBOL,
               bars: int = DAILY_BARS) -> pd.DataFrame:
    """CLOSED daily bars only, oldest first, in this repo's column names.

    Alpaca serves TODAY'S PARTIAL BAR during the session. Acting on it
    would be reading a price that has not happened yet, so any bar dated on
    the session we are about to act in is dropped. What is left ends at
    yesterday's close, which makes every decision here "decide on the last
    close, fill at the next open" — the exact convention backtest.py
    measured these rules with.

    THE WINDOW IS ASKED FOR BY DATE, NOT BY COUNT. See DAILY_LOOKBACK_DAYS:
    a request with no start date comes back empty, and a start plus a count
    returns the OLDEST bars from that date rather than the newest."""
    start = (session_date - timedelta(days=DAILY_LOOKBACK_DAYS)).isoformat()
    raw = venue.bars(symbol, "1Day", limit=bars, start=start) or []
    rows = []
    for b in raw:
        try:
            ts = pd.Timestamp(b["t"])
        except Exception:
            continue
        day = ts.tz_convert(NY).date() if ts.tzinfo else ts.date()
        if day >= session_date:
            continue                     # the still-forming bar, dropped
        rows.append({"timestamp": ts, "day": day, "open": float(b["o"]),
                     "high": float(b["h"]), "low": float(b["l"]),
                     "close": float(b["c"]), "volume": float(b.get("v") or 0)})
    d = pd.DataFrame(rows)
    if d.empty:
        return d
    return d.sort_values("timestamp").reset_index(drop=True)


# ===========================================================================
# 9. THE MARKET-HOURS GATE — one door to the venue, and it can be shut
# ===========================================================================

class MarketClosed(RuntimeError):
    """Raised instead of sending an order the venue would reject."""


def market_gate(venue) -> dict:
    """Is the session open right now, and which session would we act in.

    Round 360 found that Alpaca REJECTS market orders outside regular
    trading hours. This is the check that stops that being discovered by
    having an order bounced.

    A CLOCK THAT CANNOT BE READ COUNTS AS SHUT. Not knowing is not a reason
    to fire.

    `session_date` is the session this bot would act in: today when the
    market is open, otherwise the day the market next opens. That is what
    makes a hold length countable in sessions and what tells load_daily
    which partial bar to drop."""
    try:
        c = venue.clock() or {}
    except Exception as e:
        today = datetime.now(timezone.utc).astimezone(NY).date()
        return {"open": False, "why": f"the venue clock could not be read "
                                      f"({str(e)[:80]}) — treating the market "
                                      f"as shut, because not knowing is not a "
                                      f"reason to send an order",
                "next_open": None, "session_date": today, "clock_ok": False}
    is_open = bool(c.get("is_open"))
    next_open = c.get("next_open")
    try:
        now_ny = pd.Timestamp(c.get("timestamp")).tz_convert(NY)
    except Exception:
        now_ny = pd.Timestamp(datetime.now(timezone.utc)).tz_convert(NY)
    if is_open:
        session_date = now_ny.date()
    else:
        try:
            session_date = pd.Timestamp(next_open).tz_convert(NY).date()
        except Exception:
            session_date = now_ny.date()
    return {"open": is_open, "clock_ok": True, "next_open": next_open,
            "session_date": session_date,
            "why": ("the market is open" if is_open else
                    f"the market is shut — it next opens {next_open}")}


_ORDER_SEQ = [0]


def make_client_order_id(rule: str, side: str) -> str:
    """THE ONLY PLACE AN ORDER ID IS MADE. Every id starts with "CBOT_".

    The account has had zero orders ever, so this tag is a perfect line
    between what this bot did and anything placed by hand from the app
    later. Do not squander that by sending an untagged order."""
    _ORDER_SEQ[0] += 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    short = re.sub(r"[^A-Za-z0-9]", "", rule)[:16] or "unknown"
    return f"{ORDER_TAG}_{SYMBOL}_{short}_{side}_{stamp}_{_ORDER_SEQ[0]:03d}"


def send_market_order(venue, side: str, qty: float, rule: str,
                      gate: dict) -> dict:
    """THE ONE DOOR TO THE VENUE. There is no second path in this file.

    Refuses to send when the gate says the session is shut, rather than
    letting the venue reject it. Every order that goes through here carries
    a client_order_id beginning "CBOT_"."""
    if not gate.get("open"):
        raise MarketClosed(f"refusing to send a {side} order for {qty:.4f} "
                           f"shares of {SYMBOL}: {gate.get('why')}")
    if qty < MIN_QTY:
        raise ValueError(f"{qty:.6f} shares is below the smallest order this "
                         f"venue accepts ({MIN_QTY})")
    coid = make_client_order_id(rule, side)
    order = venue.market_order(SYMBOL, side, round(qty, 3),
                               client_order_id=coid) or {}
    order["client_order_id"] = order.get("client_order_id") or coid
    return order


# ===========================================================================
# 10. SIZING — size = dollars risked / stop distance, leverage is an OUTPUT
# ===========================================================================

def size_from_risk(equity: float, buying_power: float, entry_price: float,
                   stop_level: float) -> dict:
    """The stop decides the size. Nothing else does.

    Dollars risked is RISK_PCT of the account's equity, read from the
    venue. Shares = dollars risked / the distance from entry down to the
    structure stop, so a wide stop buys fewer shares and a tight one buys
    more, and the dollars at risk are the same either way.

    Two caps, and BOTH shrink the position rather than widening the risk
    budget: the position is never worth more than the account's own equity
    (so this bot never borrows) and never more than the buying power the
    venue reports. Round 362 measured where this lands unconstrained —
    about 0.9 times the account for the dip-buy and 0.5 times for
    turn-of-month — so in normal conditions neither cap binds."""
    distance = entry_price - stop_level
    if distance <= 0 or entry_price <= 0 or equity <= 0:
        return {"qty": 0.0, "notional": 0.0, "stop_distance": distance,
                "risk_usd": 0.0, "leverage": 0.0, "capped_by": "bad_inputs",
                "stop_distance_pct_of_price": 0.0}

    risk_usd = equity * RISK_PCT / 100.0
    qty = risk_usd / distance
    notional = qty * entry_price
    capped_by = None

    if notional > equity:
        qty = equity / entry_price
        capped_by = "the account's own equity (this bot never borrows)"
    if buying_power > 0 and qty * entry_price > buying_power:
        qty = buying_power / entry_price
        capped_by = "the buying power the venue reports"

    # Round DOWN to the fractional-share step, never up: rounding a
    # risk-sized position up spends more than the risk budget authorised.
    qty = int(qty / QTY_STEP) * QTY_STEP
    notional = qty * entry_price
    return {"qty": round(qty, 3), "notional": notional,
            "stop_distance": distance, "risk_usd": risk_usd,
            "leverage": (notional / equity) if equity > 0 else 0.0,
            "capped_by": capped_by,
            "stop_distance_pct_of_price": distance / entry_price * 100.0}


# ===========================================================================
# 11. THE CLOSE — one plain-English lesson, every single time
# ===========================================================================

def write_lesson(state: dict, t: dict, pnl: float, exit_price: float,
                 reason: str) -> dict:
    """ONE PLAIN-ENGLISH LESSON, ON EVERY CLOSE. No exceptions, wins
    included.

    The schema is export_journal.write_learnings()'s exactly — date,
    trigger, trade, conditions, why — appended to state["lessons"] and
    capped at 50, which is what makes it render into data/learnings.md in
    the existing format with no change to export_journal.py."""
    won = pnl > 0
    rule = t.get("rule", "unknown_rule")
    entry = float(t.get("entry_price") or 0.0)
    move = price_move_pct(entry, exit_price)
    notional = entry * float(t.get("qty") or 0.0)
    share = (pnl / notional * 100.0) if notional else None

    obs = []
    if t.get("anchor_swing"):
        obs.append(f"stop sat on the confirmed swing low "
                   f"{t['anchor_swing']:,.2f}")
    else:
        obs.append(f"no confirmed swing low at entry, so the stop used the "
                   f"{t.get('fallback_pct_of_price', 0):.2f}% of price "
                   f"fallback distance")
    if t.get("stop_distance_pct_of_price") is not None:
        obs.append(f"the stop sat "
                   f"{t['stop_distance_pct_of_price']:.2f}% of price under "
                   f"the entry")
    if t.get("leverage_at_entry") is not None:
        obs.append(f"sized off the stop, which came out at "
                   f"{t['leverage_at_entry']:.2f} times the account")
    if t.get("sessions_held") is not None:
        obs.append(f"held {t['sessions_held']} trading sessions, and the "
                   f"nights in between")
    prior = (t.get("memory_at_entry") or {}).get("consecutive_losses")
    if prior:
        obs.append(f"the memory already had {prior} losses in a row on this "
                   f"setup when it fired")

    if won and reason == "structure_stop":
        why = ("won even though the structure stop took it out — the level "
               "held long enough to pay; leave the stop where the chart "
               "puts it")
    elif won and rule == "turn_of_month":
        why = ("the turn-of-month hold paid, and most of what it collected "
               "came from the closed hours rather than the sessions — keep "
               "holding across the nights, do not shorten this")
    elif won:
        why = ("the deep dip inside an uptrend recovered the way the rule "
               "says it should — keep taking this setup")
    elif reason == "structure_stop" and prior:
        why = (f"lost on this setup again ({prior + 1} in a row now), stopped "
               f"out where the chart said the idea was wrong — do not take it "
               f"again without checking the swing it rests on is holding")
    elif reason == "structure_stop":
        why = ("stopped out at real structure — the level broke, so the idea "
               "was wrong; this is the normal cost of the strategy and there "
               "is nothing to fix")
    elif rule == "turn_of_month":
        why = ("the turn-of-month window closed lower than it opened — this "
               "rule loses roughly four times in ten and is still ahead over "
               "158 trades; only worth acting on if it repeats")
    else:
        why = ("the dip kept going before it recovered — the rule pays over "
               "many trades, not on any one; only worth acting on if it "
               "repeats")

    lesson = {
        "date": now_utc(), "trigger": rule,
        "trade": f"long ${entry:,.2f} -> {reason} ${exit_price:,.2f} "
                 f"({move}), {'made' if won else 'lost'} ${abs(pnl):,.2f}"
                 + (f" = {position_value_pct(share)}" if share is not None
                    else ""),
        "conditions": "; ".join(obs) if obs else "context not captured",
        "why": why,
    }
    lessons = state.setdefault("lessons", [])
    lessons.append(lesson)
    del lessons[:-50]
    log_event({"action": "lesson", **lesson})
    return lesson


def close_trade(state: dict, t: dict, exit_price: float, reason: str,
                sessions_held: int | None = None) -> float:
    """Record this bot's close on its own line, write the lesson, and update
    the shared per-rule stats."""
    entry = float(t.get("entry_price") or 0.0)
    qty = float(t.get("qty") or 0.0)
    notional = entry * qty
    gross = (exit_price - entry) * qty
    # The cost of trading at this venue is the gap between the buy and the
    # sell price, charged once per round trip against the position's own
    # value. There is no commission on US equities.
    cost = notional * ROUND_TRIP_COST_PCT / 100.0
    realized = round(gross - cost, 2)
    if sessions_held is not None:
        t["sessions_held"] = sessions_held

    state["virtual_equity"] = round(
        float(state.get("virtual_equity", 0.0)) + realized, 2)
    rec = _record(state)
    row = {"rule": t.get("rule", "unknown_rule"),
           "entry_time": t.get("entry_time"),
           "entry_session": t.get("entry_session"),
           "entry_price": entry, "qty": qty,
           "exit_price": round(exit_price, 2), "pnl": realized,
           "reason": reason, "sessions_held": t.get("sessions_held"),
           "exit_time": now_utc()}
    rec.setdefault("trades", []).append(row)
    rec["trades"] = rec["trades"][-200:]
    rec["realized_pnl_total"] = round(
        rec.get("realized_pnl_total", 0.0) + realized, 2)
    rec["open_trade"] = None

    lesson = write_lesson(state, t, realized, exit_price, reason)
    save_state(state)

    share = (realized / notional * 100.0) if notional else None
    print(f"  [SP500] {reason}: ${realized:+,.2f} "
          f"({price_move_pct(entry, exit_price)}, "
          f"{position_value_pct(share)})")
    print(f"  [SP500] lesson written: {lesson['why']}")
    log_event({"action": "sp500_exit", "reason": reason, "rule": row["rule"],
               "symbol": SYMBOL, "exit_price": exit_price,
               "realized_pnl": realized,
               "sessions_held": t.get("sessions_held")})
    record_trade_outcome(state, row["rule"], realized)
    notify(f"📈 S&P bot {reason}: ${realized:+,.2f}",
           f"{row['rule']} closed on {SYMBOL} — "
           f"{price_move_pct(entry, exit_price)} — "
           f"{position_value_pct(share)} (paper)")
    return realized


# ===========================================================================
# 12. EXIT LOGIC — what makes a held trade come out
# ===========================================================================

def exit_due(d: pd.DataFrame, t: dict, sessions_held: int,
             live_price: float) -> tuple[str, str] | None:
    """Should the held trade come out, and why. Returns (reason, plain
    English) or None.

    THE STOP IS EVALUATED BY THIS BOT, NOT BY THE VENUE. On BloFin the stop
    sits on the exchange and survives this process being dead; alpaca.py
    exposes market orders and position-close only, so here the stop fires
    on the next cycle that runs inside a session. It is checked against
    BOTH the last closed bar's LOW (so a level touched during a session
    still counts) and the live price. The exposure that leaves was measured
    in round 362: the overnight move alone cleared these distances on 0.1%
    to 1.3% of days. Small, measured, and not zero. The first improvement
    to make is a native stop order at the venue, which needs one new method
    on alpaca.py.

    THERE IS NO TIME-OF-DAY EXIT HERE AND THERE MUST NEVER BE ONE. Round
    370 measured the turn-of-month lift at +0.0468% of price in the closed
    hours against +0.0176% of price inside the session; flattening before
    the bell would throw away the larger part of the edge."""
    stop = float(t.get("stop_level") or 0.0)
    if stop > 0:
        bar_low = float(d["low"].iloc[-1]) if len(d) else None
        if bar_low is not None and bar_low <= stop:
            return ("structure_stop",
                    f"the last session traded down to {bar_low:,.2f}, through "
                    f"the structure stop at {stop:,.2f}")
        if live_price and live_price <= stop:
            return ("structure_stop",
                    f"price is {live_price:,.2f}, at or under the structure "
                    f"stop at {stop:,.2f}")

    rule = t.get("rule")
    if rule == "turn_of_month":
        if sessions_held >= TOM_HOLD_SESSIONS:
            return ("held_the_planned_sessions",
                    f"the {TOM_HOLD_SESSIONS}-session turn-of-month hold is "
                    f"complete ({sessions_held} sessions held)")
        return None

    if rule == "rsi2_dip_buy":
        close = float(d["close"].iloc[-1])
        avg5 = _sma(d["close"], DIP_EXIT_SMA).iloc[-1]
        r = rsi(d["close"], RSI_LEN).iloc[-1]
        if not pd.isna(avg5) and close > float(avg5):
            return ("dip_recovered",
                    f"the close {close:,.2f} is back above the "
                    f"{DIP_EXIT_SMA}-day average {float(avg5):,.2f}")
        if not pd.isna(r) and float(r) > RSI_EXIT_ABOVE:
            return ("dip_recovered",
                    f"the 2-day strength gauge snapped to {float(r):.1f}, "
                    f"over {RSI_EXIT_ABOVE:.0f}")
        return None
    return None


# ===========================================================================
# 13. THE CYCLE
# ===========================================================================

def run_sp500(venue, state: dict, dry: bool = False) -> dict:
    """ONE DECISION CYCLE for the S&P bot. Returns a summary dictionary.

    Order of operations, and none of it is rearrangeable:
      1. read the venue clock — a clock that cannot be read counts as shut
      2. read the account and the position, and reconcile against them
      3. load the memory and latch any new stand-down
      4. manage a held trade: hold it, or take it out
      5. THE STAND-DOWN GATE, after reconcile and after every exit path so
         a held position can never be stranded
      6. run the rules, arbitrate, size off the stop, and enter

    A decision that comes due while the market is shut is DEFERRED: it is
    logged and alerted, the bar is NOT marked processed, and the next cycle
    inside a session takes it. Marking the bar processed on a deferral
    would silently skip the trade forever."""
    rec = _record(state)
    t = rec.get("open_trade")
    tag = " DRY" if dry else ""

    # -- 1. the clock, first ------------------------------------------------
    gate = market_gate(venue)
    session_date = gate["session_date"]
    print(f"  [SP500{tag}] {VENUE_NAME}: {gate['why']} | acting in the "
          f"{_fmt_day(session_date)} session")

    # -- 2. the account and the position, read from the venue ---------------
    acct = account_snapshot(venue)
    pos = position_snapshot(venue)
    print(f"  [SP500{tag}] account: equity ${_fmt(acct['equity'])}, buying "
          f"power ${_fmt(acct['buying_power'])} | venue position: "
          + (f"{pos['qty']:.3f} shares from ${_fmt(pos['avg_entry_price'])}"
             if pos else "none"))

    # -- 2b. reconcile ------------------------------------------------------
    if t and pos is None:
        # our position is gone: someone closed it at the venue, or a
        # position we thought we held never existed. Record it at the last
        # price we can see and write the lesson rather than losing the trade.
        exit_price = last_price(venue, SYMBOL,
                                fallback=float(t.get("entry_price") or 0.0))
        print(f"  [SP500{tag}] the venue shows no position but this bot had "
              f"one recorded — closing the record at {exit_price:,.2f}")
        if dry:
            return {"action": "would_reconcile_exit",
                    "reason": "position_gone_at_venue",
                    "exit_price": exit_price}
        realized = close_trade(state, t, exit_price, "position_gone_at_venue")
        return {"action": "reconciled_exit", "reason": "position_gone_at_venue",
                "exit_price": exit_price, "pnl": realized}

    if t and pos is not None:
        # Alpaca returns a market order with filled_avg_price empty, so the
        # entry was recorded at the reference price we saw. Correct it to
        # the venue's own average entry, so the record converges on what the
        # venue says rather than on what we guessed.
        venue_entry = float(pos.get("avg_entry_price") or 0.0)
        if venue_entry > 0 and abs(venue_entry - float(t.get("entry_price") or 0)) > 1e-6:
            old = float(t.get("entry_price") or 0.0)
            t["entry_price"] = venue_entry
            print(f"  [SP500{tag}] entry price corrected to the venue's own "
                  f"average entry {venue_entry:,.2f} (recorded {old:,.2f})")
            if not dry:
                save_state(state)
        if abs(float(pos["qty"]) - float(t.get("qty") or 0.0)) > MIN_QTY:
            t["qty"] = float(pos["qty"])
            if not dry:
                save_state(state)

    if not t and pos is not None:
        # NOT ours to adopt and NOT ours to flatten. The account has had
        # zero orders ever, so anything here that this bot did not open was
        # placed by a human, and it stays theirs.
        print(f"  [SP500{tag}] ⚠️ {pos['qty']:.3f} shares of {SYMBOL} that "
              f"this bot did not open — not adopting it, not flattening it")
        if not dry:
            log_event({"action": "sp500_unclaimed_position",
                       "symbol": SYMBOL, "qty": pos["qty"]})
            if not rec.get("unclaimed_alerted"):
                rec["unclaimed_alerted"] = True
                save_state(state)
                notify("⚠️ An S&P position this bot did not open (paper)",
                       f"{pos['qty']:.3f} shares of {SYMBOL} on the paper "
                       f"account that the bot has no record of. It will not "
                       f"touch it. (One alert per episode.)")
    elif rec.get("unclaimed_alerted") and pos is None:
        rec.pop("unclaimed_alerted", None)
        if not dry:
            save_state(state)

    # -- 3. the memory, loaded BEFORE anything is decided -------------------
    memory = load_memory(state)
    newly_stood_down = [] if dry else apply_memory_stand_downs(state, memory)
    if newly_stood_down and not dry:
        save_state(state)
        for rule in newly_stood_down:
            m = memory["rules"][rule]
            print(f"  [SP500] 🛑 STAND DOWN {rule}: {m['note']}")
            log_event({"action": "sp500_rule_stood_down", "rule": rule,
                       "consecutive_losses": m["consecutive_losses"],
                       "reason": m["last_reason"]})
            notify(f"🛑 S&P bot: {rule} stood down (paper)",
                   f"{m['consecutive_losses']} losses in a row, all ending "
                   f"'{m['last_reason']}'. No new entries on this rule until "
                   f"a human clears it.")
    statuses = ", ".join(f"{r}={m['status']}"
                         for r, m in memory["rules"].items())
    print(f"  [SP500{tag}] memory: {memory['n_closed']} closed trades read "
          f"back ({memory['n_ledger_rows']} from the shared ledger), "
          f"{memory['n_lessons']} lessons | {statuses}")

    # -- 4. the daily frame and the calendar --------------------------------
    d = load_daily(venue, session_date)
    if d.empty or len(d) < TREND_SMA + K_SWING:
        print(f"  [SP500{tag}] only {len(d)} closed daily bars — not enough "
              f"history to compute the {TREND_SMA}-day average, standing "
              f"still")
        return {"action": "not_enough_history", "bars": len(d)}

    decision_day = d["day"].iloc[-1]
    close = float(d["close"].iloc[-1])
    live = last_price(venue, SYMBOL, fallback=close)

    cal_start = min(decision_day, session_date) - timedelta(days=40)
    cal_end = max(decision_day, session_date) + timedelta(days=95)
    sessions, cal_source = venue_sessions(venue, cal_start, cal_end)
    days_left = trading_days_left_in_month(decision_day, sessions)
    print(f"  [SP500{tag}] decision bar {_fmt_day(decision_day)} close "
          f"{close:,.2f} | live {live:,.2f} | {days_left} trading days left "
          f"in the month (source: {cal_source})")

    # -- 5. a held trade ----------------------------------------------------
    if t:
        entry_session = t.get("entry_session")
        try:
            entry_day = date.fromisoformat(str(entry_session)[:10])
        except Exception:
            entry_day = decision_day
        sessions_held = sessions_between(entry_day, session_date, sessions)
        due = exit_due(d, t, sessions_held, live)
        print(f"  [SP500{tag}] holding {float(t.get('qty') or 0):.3f} shares "
              f"of {SYMBOL} from ${float(t.get('entry_price') or 0):,.2f} "
              f"({price_move_pct(float(t.get('entry_price') or 0), live)}) | "
              f"stop at structure {float(t.get('stop_level') or 0):,.2f} | "
              f"{sessions_held} of {t.get('planned_sessions', '-')} sessions "
              f"held, across the nights in between")

        if due is None:
            if dry:
                return {"action": "would_hold", "sessions_held": sessions_held,
                        "decision_day": str(decision_day)}
            rec["last_bar_day"] = str(decision_day)
            save_state(state)
            return {"action": "hold", "sessions_held": sessions_held,
                    "stop_level": float(t.get("stop_level") or 0),
                    "decision_day": str(decision_day)}

        reason, plain = due
        print(f"  [SP500{tag}] exit due — {plain}")
        if dry:
            return {"action": "would_exit", "reason": reason,
                    "sessions_held": sessions_held,
                    "decision_day": str(decision_day)}

        if not gate["open"]:
            # DEFERRED, never sent. The bar is deliberately NOT marked
            # processed: an exit blocked by a shut market has to be taken by
            # the next cycle inside a session, not silently skipped.
            print(f"  [SP500] exit DEFERRED — {gate['why']}. The position is "
                  f"held across the close and taken out at the next open.")
            rec["deferred"] = {"kind": "exit", "reason": reason,
                               "plain": plain, "since": now_utc()}
            save_state(state)
            log_event({"action": "sp500_exit_deferred", "reason": reason,
                       "why": gate["why"], "symbol": SYMBOL})
            notify("⏸ S&P bot exit waiting for the open (paper)",
                   f"{plain}. The market is shut, so nothing was sent. The "
                   f"position comes out at the next open.")
            return {"action": "deferred_market_shut", "kind": "exit",
                    "reason": reason, "decision_day": str(decision_day)}

        try:
            order = send_market_order(venue, "sell", float(t["qty"]),
                                      t.get("rule", "unknown_rule"), gate)
        except Exception as e:
            print(f"  [SP500] EXIT ORDER FAILED: {str(e)[:120]}")
            log_event({"action": "sp500_exit_failed", "error": str(e)[:200]})
            notify("⚠️ S&P bot could not close its position (paper)",
                   f"the sell order was refused: {str(e)[:100]}. The position "
                   f"is still open — check the account.")
            return {"action": "exit_failed", "error": str(e)[:150],
                    "decision_day": str(decision_day)}

        rec["deferred"] = None
        realized = close_trade(state, t, live, reason,
                               sessions_held=sessions_held)
        rec["last_bar_day"] = str(decision_day)
        save_state(state)
        return {"action": "exited", "reason": reason, "pnl": realized,
                "order_id": order.get("client_order_id"),
                "sessions_held": sessions_held,
                "decision_day": str(decision_day)}

    # -- 6. flat: run the rules and let the arbiter decide -------------------
    ctx = {"symbol": SYMBOL, "decision_day": decision_day,
           "session_date": session_date, "close": close,
           "trading_days_left_in_month": days_left, "memory": memory}
    signals = evaluate_rules(d, ctx)
    verdict = arbitrate(signals, memory)
    considered = ", ".join(f"{c['rule']}({c['status']})"
                           for c in verdict.considered) or "none"
    print(f"  [SP500{tag}] rules fired: {considered} -> {verdict.action}"
          + (f" — {verdict.reason}" if verdict.reason else ""))
    if verdict.memory_note:
        print(f"  [SP500{tag}] MEMORY NOTE: {verdict.memory_note}")

    if verdict.action != "enter":
        if dry:
            return {"action": f"would_{verdict.action}",
                    "reason": verdict.reason,
                    "decision_day": str(decision_day),
                    "memory_note": verdict.memory_note}
        if rec.get("last_bar_day") != str(decision_day):
            rec["last_bar_day"] = str(decision_day)
            save_state(state)
        return {"action": verdict.action, "reason": verdict.reason,
                "decision_day": str(decision_day),
                "memory_note": verdict.memory_note}

    chosen = verdict.signal
    ref_price = live if live > 0 else close
    sizing = size_from_risk(acct["equity"], acct["buying_power"], ref_price,
                            chosen.stop_level)
    print(f"  [SP500{tag}] {chosen.rule}: BUY | stop at structure "
          f"{chosen.stop_level:,.2f} "
          f"({price_move_pct(ref_price, chosen.stop_level)} away) | risking "
          f"${sizing['risk_usd']:,.2f} ({account_pct(RISK_PCT)}) -> "
          f"{sizing['qty']:.3f} shares, ~${sizing['notional']:,.0f}, which is "
          f"{sizing['leverage']:.2f} times the account (an output of the stop"
          + (f", shrunk by {sizing['capped_by']}" if sizing["capped_by"]
             else "") + ")")

    # -- 7. THE STAND-DOWN GATE ---------------------------------------------
    # Placed HERE deliberately: after the reconcile, after every exit path,
    # and after the rule, the reference price and the size are all bound. A
    # held trade still closes normally with the gate shut, the bot still
    # logs exactly what it WOULD have taken, and the gate itself cannot
    # raise on a name that is not bound. Do not move this up.
    if not NEW_ENTRIES_ENABLED:
        print(f"  [SP500] {chosen.rule} would have bought {sizing['qty']:.3f} "
              f"shares but new entries are SWITCHED OFF in this file "
              f"(NEW_ENTRIES_ENABLED is False — a human turns it on after "
              f"wiring it in)")
        if not dry:
            log_event({"action": "sp500_stood_down", "rule": chosen.rule,
                       "qty": sizing["qty"], "entry_ref": ref_price,
                       "stop": chosen.stop_level,
                       "decision_day": str(decision_day),
                       "memory_note": verdict.memory_note})
            rec["last_bar_day"] = str(decision_day)
            save_state(state)
        return {"action": "stood_down", "reason": "new_entries_disabled",
                "rule": chosen.rule, "qty": sizing["qty"],
                "stop_level": chosen.stop_level,
                "decision_day": str(decision_day),
                "memory_note": verdict.memory_note}

    if sizing["qty"] < MIN_QTY:
        print(f"  [SP500{tag}] the size that falls out of the stop is "
              f"{sizing['qty']:.4f} shares, under the venue's minimum — "
              f"not entering")
        if not dry:
            rec["last_bar_day"] = str(decision_day)
            save_state(state)
        return {"action": "entry_skipped", "reason": "size_below_minimum",
                "decision_day": str(decision_day)}

    if dry:
        print("  [SP500 DRY] WOULD ENTER — no order placed")
        return {"action": "would_enter", "rule": chosen.rule,
                "qty": sizing["qty"], "stop_level": chosen.stop_level,
                "decision_day": str(decision_day),
                "memory_note": verdict.memory_note}

    if not gate["open"]:
        # DEFERRED, never sent, and the bar is deliberately NOT marked
        # processed. Alpaca rejects market orders outside regular trading
        # hours, and both of these rules decide at a close and fill at the
        # next open anyway — so this is the normal path, not an error.
        print(f"  [SP500] entry DEFERRED to the next open — {gate['why']}")
        rec["deferred"] = {"kind": "entry", "rule": chosen.rule,
                           "stop_level": chosen.stop_level,
                           "decision_day": str(decision_day),
                           "since": now_utc()}
        save_state(state)
        log_event({"action": "sp500_entry_deferred", "rule": chosen.rule,
                   "why": gate["why"], "decision_day": str(decision_day)})
        return {"action": "deferred_market_shut", "kind": "entry",
                "rule": chosen.rule, "decision_day": str(decision_day)}

    # idempotency: this exact closed bar was already decided on
    if rec.get("last_bar_day") == str(decision_day):
        print(f"  [SP500] {_fmt_day(decision_day)} already decided on — "
              f"no-op")
        return {"action": "noop_already_processed",
                "decision_day": str(decision_day)}

    try:
        order = send_market_order(venue, "buy", sizing["qty"], chosen.rule,
                                  gate)
    except Exception as e:
        print(f"  [SP500] ENTRY FAILED: {str(e)[:120]}")
        log_event({"action": "sp500_entry_failed", "error": str(e)[:200]})
        notify("⚠️ S&P bot entry failed (paper)",
               f"the buy order was refused: {str(e)[:100]}. Nothing opened.")
        rec["last_bar_day"] = str(decision_day)
        save_state(state)
        return {"action": "entry_failed", "error": str(e)[:150],
                "decision_day": str(decision_day)}

    planned = (TOM_HOLD_SESSIONS if chosen.rule == "turn_of_month"
               else None)
    rec["deferred"] = None
    rec["open_trade"] = {
        "rule": chosen.rule, "direction": 1, "qty": sizing["qty"],
        # Alpaca does not return a fill price on a market order, so this is
        # the reference price we saw. The next cycle corrects it to the
        # venue's own average entry.
        "entry_price": ref_price, "entry_price_is_reference": True,
        "entry_time": now_utc(), "entry_session": str(session_date),
        "decision_day": str(decision_day),
        "stop_level": round(float(chosen.stop_level), 4),
        "anchor_swing": chosen.context.get("anchor_swing"),
        "fallback_pct_of_price": chosen.context.get("fallback_pct_of_price"),
        "stop_distance_pct_of_price": sizing["stop_distance_pct_of_price"],
        "leverage_at_entry": sizing["leverage"],
        "risk_usd": round(sizing["risk_usd"], 2),
        "capped_by": sizing["capped_by"],
        "planned_sessions": planned,
        "entry_reason": chosen.reason,
        "client_order_id": order.get("client_order_id"),
        # WHAT THIS BOT KNEW WHEN IT FIRED, attached to the trade itself, so
        # no trade can ever be reviewed without it.
        "memory_at_entry": memory["rules"].get(chosen.rule, {}),
        "memory_note": verdict.memory_note,
        "lessons_known": [L.get("why", "") for L in
                          memory["lessons"][-MAX_LESSONS_ON_RECORD:]],
        "n_lessons_known": memory["n_lessons"],
        "n_closed_trades_known": memory["n_closed"],
    }
    rec["last_bar_day"] = str(decision_day)
    save_state(state)

    log_event({"action": "sp500_enter", "rule": chosen.rule, "symbol": SYMBOL,
               "qty": sizing["qty"], "entry_ref": ref_price,
               "stop": chosen.stop_level,
               "client_order_id": order.get("client_order_id"),
               "decision_day": str(decision_day),
               "memory_note": verdict.memory_note,
               "n_lessons_known": memory["n_lessons"],
               "n_closed_trades_known": memory["n_closed"]})
    notify(f"📈 THE S&P BOT BOUGHT {SYMBOL} (paper)",
           f"{chosen.rule}: {sizing['qty']:.3f} shares near ${ref_price:,.2f} "
           f"| stop at structure ${chosen.stop_level:,.2f} "
           f"({price_move_pct(ref_price, chosen.stop_level)} away) | risking "
           f"{account_pct(RISK_PCT)}"
           + (f" | MEMORY: {verdict.memory_note}" if verdict.memory_note
              else ""))
    return {"action": "entered", "rule": chosen.rule, "qty": sizing["qty"],
            "entry_ref": ref_price, "stop_level": chosen.stop_level,
            "order_id": order.get("client_order_id"),
            "decision_day": str(decision_day),
            "memory_note": verdict.memory_note}
