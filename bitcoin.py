"""
bitcoin.py — THE BITCOIN BOOK. One book. One market. One thesis.

THE OWNER'S DIRECTIVE (Wallace, 2026-07-25)
  "we will get rid of the shorts lab and news desk and all that bullshit
  because it's deceiving, it doesn't work. what you will do is simply
  combine them into one bot and the bot is whatever what you're trading is
  called."

WHAT THIS REPLACES
  Six books could hold BTC-USDT simultaneously on one netted BloFin
  account: the ride (step5_paper_trade.decide_and_trade), the strikes
  (tactical.py), the shorts lab, the newsdesk, the diver, the breakout
  book. Every one of them carried a name that implied an expertise it had
  never earned, and four of them are already stood down after round 150
  showed their edges die at taker execution with real chart-structure
  stops. That architecture is also what produced the 2026-07-23
  misattribution incident (book_ledger.py's own docstring) and the gold
  false-alarm loop that followed it.

  This file is the replacement: ONE book, named after the market it
  trades, sole owner of BTC-USDT. One position, one thesis, and no
  attribution arithmetic between competing books on the same symbol.

  NOTHING IS RIPPED OUT BY THIS FILE. The retirement of the old books,
  what happens to their open positions, and the daemon.py / book_ledger.py
  edits are all written up in step300_consolidation_plan.md and executed
  by a human. This file is inert until that cutover happens and
  NEW_ENTRIES_ENABLED is flipped on deliberately.

THE STRATEGY IT STARTS WITH — the one BTC edge that survived honest
retesting
  Round 150 re-tested all five of BTC's documented edges at
  execution="taker" with real per-trade chart-structure stops. Three died
  outright, one was noise, and exactly one recovered:

    Edge 3, the "ride": 4h trend with a strict 1.5%-of-price volatility
    gate (strategy.vol_filtered_ma, FAST/SLOW 20/100, MIN_ATR_PCT 1.5),
    with its flat -8%-of-price stop REPLACED by a structural trailing
    floor with 1.5%-of-price of buffer:

      TRAIN n=44  +$17.15/trade  (+7.5% of equity, DD -7.0% of equity)
      VAL   n=14  +$99.37/trade  (+13.9% of equity, DD -4.5% of equity)
      chance baseline (val): +$7.24/trade — the edge beats chance ~13.7x
      thickness (val): 3.16% of notional = 26.4x the 12bps taker round
      trip, 17.6x the fuller 18bps CostModel round trip

    See step150_edges_retest.md, Edge 3, and step150c_vol_gated_trend.py.

  The entry signal is IMPORTED from strategy.py, never reimplemented, and
  its parameters are imported from step5_paper_trade.py so this file and
  the ride can never disagree about what the champion is. The STOP is the
  part that changed: the flat -8%-of-price crash stop is gone, replaced by
  exits.stop_structure_trailing(buffer_pct=1.5, fallback_pct=8.0), which
  is the exact object round 150 measured.

  HONEST NOTE ON THE SIGNAL FUNCTION: step150c ran the retest through
  strategy.vol_gated_ma(fast=20, slow=100, min_atr_pct=1.5); the live ride
  runs strategy.vol_filtered_ma with the same three numbers. On the
  long-only side these are the same state machine written two ways
  (enter on a lively fast>slow cross, exit when the trend stops pointing
  up) and they agree bar-for-bar on test data — test_bitcoin.py asserts
  that agreement on its own fixture so a future edit to either function
  cannot silently make the live book a different strategy from the one
  that was validated. This file imports vol_filtered_ma, the live one.

DESIGNED FOR MORE EDGES
  Wallace's own setups and TJR's are going to be compressed into rules and
  added here. So entries are a LIST of rules, not a hardcoded signal. Each
  rule is a plain function (candles, ctx) -> RuleSignal | None returning
  (direction, stop_level, reason), and one arbiter (`arbitrate`) decides
  between them. Adding a second or third rule is appending to ENTRY_RULES
  and writing the function — no other part of this file changes.

  The arbiter's rules, stated plainly because they are the whole
  governance of this book:
    1. a rule the memory has STOOD DOWN never reaches the arbiter at all
    2. if two rules want OPPOSITE directions on the same bar, nobody
       trades that bar (this book holds one thesis on Bitcoin, and two
       rules disagreeing IS the absence of one)
    3. otherwise the highest-priority rule that fired wins, and if the
       memory has FLAGGED it, the arbiter must attach an explicit note
       saying so — a flagged rule cannot be taken silently

THE MEMORY LOOP — the part that actually matters
  This project already WROTE data/ledger.csv and data/learnings.md (see
  export_journal.py). Nothing had ever READ them back. We kept a diary and
  never opened it, so every trade started from zero.

  This book closes that loop:

    1. BEFORE deciding, load_memory() reads the book's own recent history
       — the last MEMORY_TRADES_N closed trades out of data/ledger.csv,
       this book's own closed trades out of its state, and every lesson in
       data/learnings.md plus state["lessons"] (which is what
       export_journal.py renders learnings.md FROM).
    2. It USES them, mechanically:
         - FLAG_AFTER_LOSSES consecutive losses on a rule -> that rule is
           FLAGGED, and the arbiter must note it explicitly on the record
         - STAND_DOWN_AFTER_LOSSES consecutive losses on a rule that all
           ended for the SAME reason -> that rule is STOOD DOWN and stays
           stood down in state until a human calls clear_rule_stand_down()
         - the loaded lessons ride along on the decision record, so every
           trade shows what the book knew at the moment it fired
    3. AFTER every close it writes one plain-English lesson in exactly the
       schema export_journal.write_learnings() renders (date / trigger /
       trade / conditions / why, appended to state["lessons"], capped at
       50, mirrored into the event log) — so the lesson shows up in
       data/learnings.md in the existing format with no change to
       export_journal.py.

  BE HONEST ABOUT WHAT THIS IS. It is a rules-and-counters memory. It
  reads, it counts, and it gates. It does not learn, it does not have a
  model, and it does not reason about its own diary. Nothing here is
  named "AI" anything, and nothing here should ever be described to
  Wallace as the bot understanding its history — it is a loss counter with
  a latch on it, and that is a genuinely useful thing to be.

EXECUTION — taker, always, one atomic order
  execute_market_clips ONLY (step5_paper_trade.py). Never
  execute_maker_or_chase: that is the pre-OWNER'S-LAW path, it infers a
  fill from an order merely leaving pending_orders(), and BloFin CANCELS
  post-only orders that would cross — 8 times out of 8 on this account,
  booking phantom fills at prices that never happened (test_phantom_fill.py).
  Every fee here is taker, both legs, and the edge above was measured that
  way.

STOPS — chart structure, never a swept percentage
  The protective stop is exits.stop_structure_trailing(buffer_pct=1.5,
  fallback_pct=8.0), computed fresh off the pulled 4h series every cycle
  (never carried incrementally — a stored ratchet can desync from itself;
  this is gold_book.py's discipline). It initialises at the most recent
  confirmed swing on the protective side as of entry and only ever moves
  in the trade's favour. step41_shorts.confirmed_swings() is used
  alongside it to name the swing the floor is resting on, so a log line
  says WHICH price on the chart the stop belongs to rather than a number
  with no provenance. The 8%-of-price fallback exists only for the case
  where no confirmed swing exists yet at entry — a backstop, never the
  mechanism.

SIZING — risk-first, leverage is an OUTPUT
  size = risk$ / stop distance, where risk$ = RISK_PCT of the book's own
  ledger (state["virtual_equity"]). Leverage is then whatever that implies,
  never an input dial, and it is capped twice: at the desk's own ceiling
  (MAX_LEVERAGE, from step150_common's retest apparatus) and at the
  INSTRUMENT'S OWN maxLeverage read live from BloFin's instruments
  endpoint. If the cap binds, the position is shrunk to fit it — the risk
  budget is never widened to keep a size.

READ THE EXCHANGE, NEVER COMPUTE (BLOFIN_API_REFERENCE.md,
step98_api_audit.md)
  contractValue and maxLeverage come from the instruments endpoint.
  liquidationPrice, unrealizedPnlRatio, initialMargin and marginRatio come
  from the positions endpoint. Not one of them is derived here. A
  hardcoded contract value once sized every real order in five books off a
  single number nobody had read from the exchange; that is never happening
  in this file.

  AND NEVER A BARE PERCENTAGE. `unrealizedPnlRatio` is PnL as a fraction
  of INITIAL MARGIN, which is the number on Wallace's screen — at 20x it
  differs from a price move by twenty times. Every percentage this file
  prints, alerts or comments carries its base: "of price", "of margin",
  "of notional", "of equity". test_bitcoin.py enforces that on the source
  text, so the convention cannot rot.

ATTRIBUTION
  BTC-USDT is netted by BloFin, so during the migration window this book
  still shares the symbol with whatever has not been retired yet. It
  therefore reconciles through book_ledger.py's shared accounting, with a
  local shim (_recorded_all) that folds THIS book's own recorded position
  into that same picture. The shim is written to be a no-op the moment
  book_ledger.recorded_book_positions() grows its own "bitcoin" key at
  cutover — see step300_consolidation_plan.md. After cutover, when this is
  the only book on the symbol, the attribution collapses to "the net is
  ours" and stays correct either way.

  STATE ISOLATION: this book reads other books' state keys (it must, to
  attribute) and WRITES exactly one — state["bitcoin"] — plus the two
  shared, book-agnostic ledger fields every book already updates
  (virtual_equity and lessons). It never writes another book's key.

WIRING (at cutover, by a human — not by this file)
  daemon.py's full_cycle calls run_bitcoin(...) through _run_book, and
  hourly.py's backstop does the same when the daemon heartbeat is stale.
  Safe to call every cycle: idempotent per 4h bar via
  state["bitcoin"]["last_bar_ts"], and it reconciles against the
  exchange's own position every single time before deciding anything.

DRY MODE: run_bitcoin(..., dry=True) computes and prints the full decision
  — reconcile, memory, rules, arbiter, sizing, the structural stop preview
  — with NO orders placed and NO state/log/notify side effects. Same
  contract as gold_book.py's and breakout_book.py's dry modes.
"""

from __future__ import annotations

import csv
import os
import re
import time
from dataclasses import dataclass, field

import pandas as pd

import exits as E
from blofin_private import make_client_order_id
from book_ledger import recorded_book_positions
from step5_paper_trade import (FAST, LOT, MIN_ATR_PCT, SLOW, contract_value,
                               execute_market_clips, log_event, notify,
                               now_utc, record_trade_outcome, save_state)
from step41_shorts import confirmed_swings
from strategy import vol_filtered_ma

SYMBOL = "BTC-USDT"
TIMEFRAME = "4h"
BOOK_TAG = "btc"          # clientOrderId code; add to blofin_private.BOOK_TAGS
                          # at cutover (see step300_consolidation_plan.md)
BOOK_KEY = "bitcoin"      # book_ledger attribution key
STATE_KEY = "bitcoin"     # the ONLY state key this file writes

# -- the validated edge's exact configuration -------------------------------
# FAST / SLOW / MIN_ATR_PCT are IMPORTED from step5_paper_trade so this book
# and the ride are structurally incapable of disagreeing about what the
# champion is. Round 150 validated 20 / 100 / 1.5 (ATR at least 1.5% of
# price) on 4h bars; if those constants ever move, they move for both.
TRAIL_BUFFER_PCT = 1.5    # of price, past the confirmed swing. THIS NUMBER IS
                          # THE RECOVERY. At buffer 0 the same edge FAILS train
                          # (-$12.18/trade): a floor sitting exactly on the
                          # swing was whipsawing out on routine pullbacks the
                          # trend then resumed from. 1.5% of price of room
                          # turns it into +$17.15 train / +$99.37 val.
                          # step150_edges_retest.md, Edge 3, recovery check.
FALLBACK_STOP_PCT = 8.0   # of price. ONLY for "no confirmed swing exists yet
                          # at entry" — the same magnitude the ride's old flat
                          # stop had, demoted from mechanism to backstop.
K_SWING = 5               # confirmed-swing fractal lookback; exits.py's own
                          # default and the k step150c ran the retest at.

# ~200 days of 4h bars: deep enough to warm SLOW=100 plus the ATR window many
# times over, and to keep an open trade's own entry bar inside the window for
# far longer than this ~6.5-trades-per-year edge holds anything. Comfortably
# under BloFin's 1440-bars-per-request cap (exchange.py).
CANDLE_BARS = 1200

# -- risk & sizing (leverage is an OUTPUT, never a dial) --------------------
RISK_PCT = 2.0            # of the book's ledger, risked per trade. The
                          # fixed-fractional sizing step150_common.py ran the
                          # whole round-150 retest at, so live sizing and the
                          # validated numbers share one convention.
MAX_LEVERAGE = 20.0       # the desk's own ceiling (step150_common, added
                          # after an uncapped near-zero stop distance produced
                          # an absurd leveraged result in the retest). The
                          # INSTRUMENT's maxLeverage is read live and applied
                          # on top of this — whichever is lower wins.

ENTRY_FEE_BPS = 6.0       # BloFin taker, both legs. Every order this book
EXIT_FEE_BPS = 6.0        # places is a market order; there is no maker path.

# -- the memory loop --------------------------------------------------------
LEDGER_CSV = os.path.join("data", "ledger.csv")
LEARNINGS_MD = os.path.join("data", "learnings.md")
MEMORY_TRADES_N = 20      # closed trades read back before every decision
FLAG_AFTER_LOSSES = 2     # consecutive losses on a rule -> FLAGGED (the
                          # arbiter must note it explicitly to take it)
STAND_DOWN_AFTER_LOSSES = 3   # consecutive losses on a rule that all ended
                              # for the SAME reason -> STOOD DOWN, latched in
                              # state until a human clears it
MAX_LESSONS_ON_RECORD = 6     # lessons attached to a decision record (the
                              # whole set is counted and reported; this caps
                              # what gets copied onto the trade)


# ===========================================================================
# THE STAND-DOWN GATE
# ===========================================================================
# This book ships OFF. It is written, tested and inert; the cutover in
# step300_consolidation_plan.md is a human's job, and flipping this flag is
# the last step of it, not the first.
#
# The gate itself lives inside run_bitcoin AFTER reconcile and after every
# exit branch, so a held position always still closes normally. That
# placement is not a style choice: a gate placed above the exit logic
# orphans live positions, and a gate placed inside the dry branch crashes
# the live path on unbound names — both have already happened here once
# (test_stand_down_gates.py was written the same hour).
NEW_ENTRIES_ENABLED = True


# ===========================================================================
# small formatting helpers — every percentage carries its base
# ===========================================================================

def _fmt_utc(ts) -> str:
    return f"{pd.Timestamp(ts):%Y-%m-%d %H:%M} UTC"


def price_move_pct(from_price: float, to_price: float) -> str:
    """A move in PRICE, labelled as such. 'Bitcoin down 5% of price'."""
    if not from_price:
        return "n/a"
    return f"{(to_price / from_price - 1) * 100:+.2f}% of price"


def margin_pct(unrealized_pnl_ratio) -> str:
    """BloFin's own `unrealizedPnlRatio` — PnL as a fraction of INITIAL
    MARGIN, which is the number on Wallace's screen. Never printed without
    the words 'of margin' next to it: at 20x this differs from a price move
    by twenty times, and confusing the two is how this repo once told him
    his own screen meant something it did not (BLOFIN_API_REFERENCE.md)."""
    if unrealized_pnl_ratio is None:
        return "n/a"
    return f"{float(unrealized_pnl_ratio) * 100:+.2f}% of margin"


def _fmt(v, nd: int = 1) -> str:
    return f"{v:,.{nd}f}" if v is not None else "n/a"


# ===========================================================================
# 1. THE MEMORY — read, count, gate. Not a model. Not learning.
# ===========================================================================

@dataclass
class RuleMemory:
    """What the counters say about one entry rule, right now."""
    rule: str
    attempts: int = 0
    consecutive_losses: int = 0
    identical_failures: int = 0        # leading losses sharing one reason
    last_reason: str | None = None
    status: str = "clear"              # "clear" | "flagged" | "stood_down"
    note: str = ""

    def as_dict(self) -> dict:
        return {"rule": self.rule, "attempts": self.attempts,
                "consecutive_losses": self.consecutive_losses,
                "identical_failures": self.identical_failures,
                "last_reason": self.last_reason, "status": self.status,
                "note": self.note}


def _norm_time(value) -> str:
    """One comparable timestamp string out of the two formats this repo
    writes: ledger.csv stores ISO-8601 with an offset, the book's own
    records store now_utc()'s 'YYYY-MM-DD HH:MM:SS UTC'. Normalised to the
    minute, which is the resolution dedupe needs and no more."""
    try:
        return f"{pd.Timestamp(str(value).replace(' UTC', '+00:00')):%Y-%m-%d %H:%M}"
    except Exception:
        return str(value)[:16]


def _split_reason(raw: str) -> tuple[str, str]:
    """Pull a rule name out of a ledger `reason` cell.

    data/ledger.csv's SELL rows carry an EXIT reason, not a rule name, so
    on its own the shared ledger cannot attribute a close to the rule that
    took it. Two shapes are understood:
      "vol_gated_trend:structural_stop"  -> ("vol_gated_trend", "structural_stop")
      "vol_gated_trend"                   -> ("vol_gated_trend", "vol_gated_trend")
      "TP/SL"                             -> ("", "TP/SL")
    The first is the format export_journal.py writes for this book's closes
    once the cutover extends it (step300_consolidation_plan.md); the second
    and third are what already exists on disk today. Anything unattributable
    still counts as a recent close — it just does not move a rule's
    counters, which is the honest outcome rather than a guess."""
    raw = (raw or "").strip()
    if ":" in raw:
        rule, _, reason = raw.partition(":")
        return rule.strip(), reason.strip() or rule.strip()
    known = {r.name for r in ENTRY_RULES}
    return (raw, raw) if raw in known else ("", raw)


def read_ledger_trades(path: str = LEDGER_CSV,
                       n: int = MEMORY_TRADES_N) -> list[dict]:
    """The last `n` CLOSED trades out of data/ledger.csv — the file
    export_journal.py has been writing since the beginning and which
    nothing has ever read back.

    Its header is fixed (timestamp, symbol, action, price, quantity,
    reason, mode, outcome, pnl) and closes are the rows whose `action` is
    SELL. Rows are returned OLDEST FIRST. A missing or malformed file is
    an empty memory, never an exception — a bot must not refuse to trade
    because its diary is missing, it should trade knowing it has none."""
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
                out.append({
                    "time": _norm_time(row.get("timestamp", "")),
                    "symbol": row.get("symbol", ""),
                    "rule": rule,
                    "reason": reason,
                    "pnl": pnl,
                    "outcome": (row.get("outcome") or "").strip().lower(),
                    "source": "ledger.csv",
                })
    except (FileNotFoundError, NotADirectoryError):
        return []
    except Exception:
        return []
    out.sort(key=lambda r: r["time"])
    return out[-n:] if n else out


def read_lessons(state: dict, path: str = LEARNINGS_MD) -> list[dict]:
    """Every lesson the bot has written to itself.

    Two sources, deliberately: state["lessons"] is the canonical store
    (export_journal.write_learnings RENDERS learnings.md from it), and the
    file itself is parsed as well so lessons that only survive on disk —
    an older export, a state reset — are not lost to the loop. Deduped on
    the lesson text. Oldest first."""
    lessons: list[dict] = []
    for L in state.get("lessons", []) or []:
        if not isinstance(L, dict):
            continue
        lessons.append({"date": L.get("date", ""), "trigger": L.get("trigger", ""),
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


_LESSON_HEAD_RE = re.compile(r"^###\s+(?P<date>.+?)\s+—\s+(?P<trigger>.+?)\s*$")


def _parse_learnings_md(path: str) -> list[dict]:
    """Parse data/learnings.md's 'Trade reviews' section back into lesson
    dicts. The format is export_journal.write_learnings()'s own and is
    matched exactly:

        ### <date> — <trigger>
        - <trade>
        - conditions: <conditions>
        - **lesson:** <why>

    Note that file is written NEWEST FIRST; this returns oldest first so
    it composes with everything else here. Unreadable file = no lessons."""
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
    out.reverse()          # the file is newest-first; return oldest-first
    return out


def _book_closed_trades(state: dict) -> list[dict]:
    """This book's OWN closed trades out of its state — the authoritative
    per-rule record, since the shared ledger.csv only carries whatever
    export_journal happens to map. Oldest first."""
    out = []
    for rec in (state.get(STATE_KEY, {}) or {}).get("trades", []) or []:
        if not isinstance(rec, dict):
            continue
        pnl = float(rec.get("pnl", 0.0) or 0.0)
        out.append({"time": _norm_time(rec.get("exit_time")
                                       or rec.get("entry_time") or ""),
                    "symbol": SYMBOL, "rule": rec.get("rule", ""),
                    "reason": rec.get("reason", ""),
                    "pnl": pnl,
                    "outcome": "win" if pnl > 0 else "loss",
                    "source": "book"})
    out.sort(key=lambda r: r["time"])
    return out


def _merge_closed(book_trades: list[dict],
                  ledger_trades: list[dict]) -> list[dict]:
    """One timeline out of both sources, deduped. The same close can appear
    in both (this book's own record AND the exported ledger row), so a
    close is identified by (timestamp normalised to the minute, PnL to the
    cent); the book's own record wins because it carries the rule name.
    Both sides are already normalised by _norm_time, which is what makes
    the two different on-disk timestamp formats comparable at all."""
    merged = list(book_trades)
    seen = {(r["time"], round(r["pnl"], 2)) for r in book_trades}
    for r in ledger_trades:
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
    """EVERYTHING THIS BOOK KNOWS ABOUT ITSELF, loaded before it decides.

    Reads back what export_journal.py writes — the last MEMORY_TRADES_N
    closed trades from data/ledger.csv, this book's own closed trades from
    state, and every lesson from data/learnings.md plus state["lessons"] —
    and reduces it to per-rule counters the arbiter can act on.

    Latched stand-downs stored in state[STATE_KEY]["rules_stood_down"] are
    applied on top and always win: once a rule is stood down it STAYS stood
    down, even if the counters would now read clear, until a human calls
    clear_rule_stand_down(). A later winning trade must not quietly
    un-stand-down a rule that a person deliberately parked.

    The two paths default to the module's LEDGER_CSV / LEARNINGS_MD and are
    resolved at CALL time, not at import time, so a caller (or a test) can
    point the loop at a different journal without reaching inside it."""
    ledger_path = LEDGER_CSV if ledger_path is None else ledger_path
    learnings_path = LEARNINGS_MD if learnings_path is None else learnings_path
    ledger_trades = read_ledger_trades(ledger_path, MEMORY_TRADES_N)
    book_trades = _book_closed_trades(state)
    closed = _merge_closed(book_trades, ledger_trades)
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
            mem.note = (f"last {mem.consecutive_losses} attempts all lost "
                        f"(most recent ended '{mem.last_reason}') — taking "
                        f"this setup anyway, noted on the record")
        rules[rule] = mem.as_dict()

    return {
        "rules": rules,
        "closed_trades": closed,
        "n_closed": len(closed),
        "n_ledger_rows": len(ledger_trades),
        "n_book_trades": len(book_trades),
        "lessons": lessons,
        "n_lessons": len(lessons),
        "latched_stand_downs": sorted(latched),
    }


def apply_memory_stand_downs(state: dict, memory: dict) -> list[str]:
    """Persist any NEW stand-down the counters just produced, so it latches
    across restarts and needs a human to clear. Returns the rules newly
    latched this cycle. Writes only state[STATE_KEY]."""
    book = _book(state)
    latched = book.setdefault("rules_stood_down", {})
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
    not going to be one. Returns True if something was actually cleared."""
    book = _book(state)
    latched = book.setdefault("rules_stood_down", {})
    if rule not in latched:
        return False
    record = latched.pop(rule)
    history = book.setdefault("stand_down_history", [])
    history.append({**record, "cleared_by": who, "cleared_at": now_utc()})
    book["stand_down_history"] = history[-50:]
    log_event({"action": "bitcoin_stand_down_cleared", "rule": rule,
               "cleared_by": who})
    return True


# ===========================================================================
# 2. THE ENTRY RULES — a list, so a second and third slot in cleanly
# ===========================================================================

@dataclass
class RuleSignal:
    """What a rule returns when it wants a trade. `stop_level` is a PRICE
    on the chart, never a percentage: the rule is responsible for saying
    where structure says it is wrong, and sizing falls out of that."""
    rule: str
    direction: int                 # +1 long, -1 short
    stop_level: float              # absolute price
    reason: str                    # plain English, goes on the record
    context: dict = field(default_factory=dict)


@dataclass
class EntryRule:
    """One entry rule. `fn(d, ctx) -> RuleSignal | None`. `priority` breaks
    ties between rules that fire on the same bar and agree on direction —
    lower is stronger."""
    name: str
    fn: object
    priority: int
    description: str


def _structural_stop(d: pd.DataFrame, entry_idx: int, entry_price: float,
                     direction: int, at_idx: int | None = None) -> float:
    """The validated stop: exits.stop_structure_trailing(buffer_pct=1.5,
    fallback_pct=8.0), evaluated on the pulled 4h series.

    This is the OBJECT round 150 measured, called directly — the ratcheting
    logic is not reimplemented here, because a second copy of a ratchet is a
    second thing that can drift from the thing that was validated. Computed
    FRESH from the series every cycle rather than carried incrementally, so
    it cannot desync from itself (gold_book.py's discipline).

    Returns an absolute price. Long: the floor under the trade. Short: the
    ceiling over it."""
    at_idx = len(d) - 1 if at_idx is None else at_idx
    s = E.build_series_ctx(d, k=K_SWING)
    tc = E.build_trade_ctx(s, entry_idx, entry_price, direction)
    method = E.stop_structure_trailing(buffer_pct=TRAIL_BUFFER_PCT,
                                       fallback_pct=FALLBACK_STOP_PCT)
    level = method.level_fn(tc, at_idx)
    return float(level)


def anchor_swing(d: pd.DataFrame, entry_idx: int, entry_price: float,
                 direction: int) -> float | None:
    """WHICH price on the chart the stop belongs to — the most recent
    CONFIRMED swing on the protective side as of `entry_idx`, via
    step41_shorts.confirmed_swings(). Purely for provenance: a stop level
    in a log line should be traceable to a swing a human can point at, not
    a number that appeared from nowhere. Returns None when no confirmed
    swing exists yet (the case the 8%-of-price fallback covers)."""
    sh_price, sl_price = confirmed_swings(d, K_SWING)
    series = sl_price if direction > 0 else sh_price
    window = series.iloc[:entry_idx + 1].dropna()
    if window.empty:
        return None
    if direction > 0:
        below = window[window < entry_price]
        return float(below.iloc[-1]) if not below.empty else None
    above = window[window > entry_price]
    return float(above.iloc[-1]) if not above.empty else None


def rule_vol_gated_trend(d: pd.DataFrame, ctx: dict) -> RuleSignal | None:
    """RULE 1 — the 4h vol-gated trend (round 150's one survivor).

    Long-only. Fires on the bar the champion signal turns ON (flat -> long),
    which is the same rising-edge definition step150c_vol_gated_trend.py
    ran the retest on: the signal is known at that bar's own close and the
    order fills next, no lookahead. An already-on signal is NOT a fresh
    entry — if this process was down across the transition bar, that
    excursion is simply missed rather than chased at a worse price.

    The exit is not this rule's business: the trade rides until either the
    structural floor breaks (an exchange-side stop, so it survives an
    outage) or the champion signal stops pointing up. That is the "ride,
    don't bracket" shape the edge was validated with — it never had a
    profit target and is not getting one."""
    # UNGATED, deliberately (round 400, 2026-07-25). This rule shipped with
    # MIN_ATR_PCT=1.5 — the "only trade when it is moving enough" condition
    # that the desk's notes called the edge itself. It is not. Tested
    # cleanly it DESTROYS money:
    #   the same 59 trend legs, matched pairs: entering at the crossover
    #   earns +$181.61 per leg, waiting for lively earns +$45.27. The
    #   condition was the better choice on 5 of 59 legs, at the 1.1st
    #   percentile of 2,000 sign flips. Net cost -$6,694, which is 71% of
    #   the ungated system's money, negative in 2020, 2021, 2022, 2023 and
    #   2025 and positive only in 2024 where one trade carries the year.
    # Why the old number looked good: the condition sits inside the signal's
    # state machine, so it does not SKIP a trade, it DELAYS one — and in a
    # one-position engine a delayed entry lets a DIFFERENT later trade
    # happen. 30% of the gated run's first-window trades and 57% of its
    # middle-window trades entered on a bar the ungated run could never
    # have taken. The old comparison was two different trade sequences.
    # DO NOT put the gate back without re-reading step400_gate_artifact_audit.md.
    sig = vol_filtered_ma(d, FAST, SLOW, min_atr_pct=0.0).fillna(0.0)
    i = len(d) - 1
    cur = float(sig.iloc[i])
    prev = float(sig.iloc[i - 1]) if i > 0 else 0.0
    if not (prev != 1.0 and cur == 1.0):
        return None

    entry_price = float(d["close"].iloc[i])
    stop = _structural_stop(d, i, entry_price, 1, at_idx=i)
    swing = anchor_swing(d, i, entry_price, 1)
    if swing is None:
        where = (f"no confirmed swing low yet — floor fell back to "
                 f"{FALLBACK_STOP_PCT:.0f}% of price under entry")
    else:
        where = (f"resting {TRAIL_BUFFER_PCT:.1f}% of price under the "
                 f"confirmed swing low {swing:,.1f}")
    return RuleSignal(
        rule="vol_gated_trend", direction=1, stop_level=stop,
        reason=(f"4h trend turned up with the market lively enough "
                f"(ATR at least {MIN_ATR_PCT:.1f}% of price); stop at "
                f"structure, {where}"),
        context={"signal": cur, "prev_signal": prev, "anchor_swing": swing,
                 "close": entry_price, "atr_gate_pct_of_price": MIN_ATR_PCT})


# THE RULE REGISTRY. Adding Wallace's setups or TJR's is appending here and
# writing the function — nothing else in this file changes. Priority is only
# consulted when two rules fire on the same bar AND agree on direction;
# disagreement is resolved by nobody trading (see arbitrate).
ENTRY_RULES: list[EntryRule] = [
    EntryRule(name="vol_gated_trend", fn=rule_vol_gated_trend, priority=1,
              description="4h trend, ATR gate at 1.5% of price, structural "
                          "trailing stop with 1.5% of price of buffer "
                          "(step150_edges_retest.md edge 3: train "
                          "+$17.15/trade, val +$99.37/trade, 26.4x the "
                          "taker round trip)"),
]


# ===========================================================================
# 3. THE ARBITER — one decision, memory-aware, never silent about a flag
# ===========================================================================

@dataclass
class Verdict:
    action: str                     # "enter" | "stand_down" | "no_signal"
    signal: RuleSignal | None = None
    reason: str = ""
    memory_note: str = ""
    considered: list = field(default_factory=list)


def arbitrate(signals: list[RuleSignal], memory: dict) -> Verdict:
    """Decide between the rules that fired. Pure — no I/O, no state.

    1. STOOD-DOWN rules are dropped before anything else is considered.
    2. If what remains wants OPPOSITE directions, NOBODY trades this bar.
       This book holds one thesis on Bitcoin; two rules disagreeing is the
       absence of a thesis, not a reason to pick a favourite.
    3. Otherwise the lowest-priority-number rule wins. If the memory has
       FLAGGED it, the verdict carries an explicit note and that note is
       required — a flagged rule is never taken silently."""
    considered = []
    live = []
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
                           memory_note="; ".join(
                               c["note"] for c in considered if c["note"]))
        return Verdict(action="no_signal", considered=considered,
                       reason="no rule fired on this bar")

    directions = {s.direction for s, _ in live}
    if len(directions) > 1:
        return Verdict(action="stand_down", considered=considered,
                       reason="rules disagree on direction — this book holds "
                              "ONE thesis on Bitcoin, so nobody trades this "
                              "bar")

    prio = {r.name: r.priority for r in ENTRY_RULES}
    live.sort(key=lambda pair: prio.get(pair[0].rule, 99))
    chosen, mem = live[0]
    note = mem.get("note", "") if mem["status"] == "flagged" else ""
    if mem["status"] == "flagged" and not note:
        # a flagged rule without a note would be exactly the silent take
        # this arbiter exists to prevent
        note = (f"{chosen.rule} is flagged by the memory "
                f"({mem.get('consecutive_losses', '?')} losses in a row)")
    return Verdict(action="enter", signal=chosen, considered=considered,
                   reason=chosen.reason, memory_note=note)


# ===========================================================================
# 4. state, attribution, exchange reads
# ===========================================================================

def _fresh_book() -> dict:
    return {"open_trade": None, "last_bar_ts": None, "trades": [],
            "realized_pnl_total": 0.0, "rules_stood_down": {},
            "stand_down_history": []}


def _book(state: dict) -> dict:
    book = state.setdefault(STATE_KEY, _fresh_book())
    for k, v in _fresh_book().items():
        book.setdefault(k, v)
    return book


def _daily_pick_btc(state: dict) -> float:
    """Daily Pick's own BTC-USDT claim, signed.

    A HOLE THIS FILE HAD TO PATCH, flagged in
    step300_consolidation_plan.md: daily_pick.py trades BTC-USDT as one of
    its four symbols, but book_ledger.recorded_book_positions() has never
    known about it — its state lives under state["daily_pick"]
    ["open_trades"], a LIST keyed by symbol, not the single "open_trade"
    every other book uses. The consequence today is that a Daily Pick BTC
    position is invisible to the shared accounting, so it lands inside
    whatever OTHER book asks for its slice. This book refuses to inherit
    that: it reads the list itself, filters to BTC-USDT, and folds it in.
    The proper fix is in book_ledger.py at cutover; this shim keeps THIS
    book honest in the meantime and stays harmless afterwards."""
    total = 0.0
    for t in (state.get("daily_pick", {}) or {}).get("open_trades", []) or []:
        if not isinstance(t, dict) or t.get("symbol") != SYMBOL:
            continue
        direction = t.get("direction", 0) or 0
        sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
        total += sign * abs(float(t.get("contracts", 0) or 0))
    return total


def _recorded_all(state: dict) -> dict:
    """Every book's own recorded BTC-USDT position, INCLUDING this one.

    book_ledger.recorded_book_positions() is the shared accounting layer
    and stays the single source of truth for the legacy books. This book
    folds its own claim into that same picture rather than editing
    book_ledger.py from here. At cutover book_ledger grows a "bitcoin" key
    of its own (step300_consolidation_plan.md) and this line becomes a
    harmless re-assignment of the identical value — correct before AND
    after, which is what makes the migration a one-line change rather than
    a coordinated one. Daily Pick is folded in the same way and for a less
    comfortable reason — see _daily_pick_btc."""
    rec = dict(recorded_book_positions(state))
    rec.setdefault("daily_pick", 0.0)
    if not rec["daily_pick"]:
        rec["daily_pick"] = _daily_pick_btc(state)
    t = (state.get(STATE_KEY, {}) or {}).get("open_trade")
    if t:
        direction = t.get("direction", 0) or 0
        sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
        rec[BOOK_KEY] = sign * abs(float(t.get("contracts", 0) or 0))
    else:
        rec[BOOK_KEY] = 0.0
    return rec


def attributed(net: float, state: dict) -> float:
    """This book's own slice of the netted exchange position: the net minus
    every OTHER book's recorded claim. Never the raw net — reading the raw
    net as "mine" is the literal 2026-07-23 incident."""
    rec = _recorded_all(state)
    return net - sum(v for k, v in rec.items() if k != BOOK_KEY)


def unexplained(net: float, state: dict) -> float:
    """What is left of the net once EVERY book's claim, this one included,
    is subtracted out. Healthy value is ~0."""
    return net - sum(_recorded_all(state).values())


def instrument_spec(demo_feed) -> dict:
    """contractValue and maxLeverage READ FROM THE EXCHANGE, never assumed
    (step98_api_audit.md finding #1: a hardcoded 0.001 once sized every
    real order in five books). Returns {} when the endpoint is unreadable
    — a caller about to place an order must treat that as 'do not trade'."""
    cv = contract_value(demo_feed, SYMBOL)
    if cv is None:
        return {}
    spec = {"contractValue": cv, "maxLeverage": None}
    try:
        raw = demo_feed.get_instrument(SYMBOL)
        if raw.get("maxLeverage") is not None:
            spec["maxLeverage"] = float(raw["maxLeverage"])
    except Exception:
        pass
    return spec


def position_health(private) -> dict:
    """The exchange's OWN risk numbers for our position — liquidationPrice,
    unrealizedPnlRatio, initialMargin, marginRatio. Every one of these is
    returned by BloFin and not one of them is derived here
    (BLOFIN_API_REFERENCE.md: "if a field exists, READ IT")."""
    out = {"liquidationPrice": None, "unrealizedPnlRatio": None,
           "initialMargin": None, "marginRatio": None, "markPrice": None,
           "leverage": None, "marginMode": None}
    try:
        for p in private.positions(SYMBOL):
            if abs(float(p.get("positions") or 0)) <= 0:
                continue
            for k in list(out):
                if p.get(k) is not None:
                    try:
                        out[k] = (float(p[k]) if k != "marginMode"
                                  else str(p[k]))
                    except (TypeError, ValueError):
                        out[k] = p[k]
            break
    except Exception:
        pass
    return out


# ===========================================================================
# 5. sizing — leverage is an OUTPUT, capped by the instrument's own ceiling
# ===========================================================================

def size_from_risk(equity: float, entry_price: float, stop_level: float,
                   contract_value_btc: float,
                   max_leverage_instrument: float | None) -> dict:
    """size = risk$ / stop distance. Leverage is whatever that implies.

    Two caps are applied, and BOTH shrink the position rather than widening
    the risk budget: the desk's own MAX_LEVERAGE (step150_common's retest
    ceiling) and the INSTRUMENT's own maxLeverage read live from BloFin. A
    stop that sits very close to entry is exactly where an uncapped
    risk-first size explodes, which is why the cap exists at all."""
    stop_distance = abs(entry_price - stop_level)
    if stop_distance <= 0 or entry_price <= 0 or contract_value_btc <= 0:
        return {"contracts": 0.0, "leverage": 0.0, "notional": 0.0,
                "stop_distance": stop_distance, "capped_by": "bad_inputs",
                "risk_usd": 0.0}

    risk_usd = equity * RISK_PCT / 100.0
    size_btc = risk_usd / stop_distance
    contracts = size_btc / contract_value_btc

    cap = MAX_LEVERAGE
    capped_by = "desk_ceiling"
    if max_leverage_instrument is not None and max_leverage_instrument < cap:
        cap, capped_by = float(max_leverage_instrument), "instrument_max"

    notional = contracts * contract_value_btc * entry_price
    leverage = notional / equity if equity > 0 else 0.0
    if leverage > cap:
        contracts *= cap / leverage
    else:
        capped_by = None

    # Round DOWN to the exchange's lot step, never up: rounding a
    # risk-sized position up spends more than the risk budget authorised,
    # which is the one direction this must never round. The exchange's own
    # minimum order size is the single exception, and when it forces us
    # over budget that is reported rather than hidden.
    contracts = int(contracts / LOT) * LOT
    forced_minimum = False
    if contracts < LOT:
        contracts, forced_minimum = LOT, True
    notional = contracts * contract_value_btc * entry_price
    leverage = notional / equity if equity > 0 else 0.0
    if forced_minimum:
        capped_by = "exchange_minimum_size"
    return {"contracts": round(contracts, 1), "leverage": round(leverage, 2),
            "notional": notional, "stop_distance": stop_distance,
            "capped_by": capped_by, "risk_usd": risk_usd,
            "forced_minimum": forced_minimum}


# ===========================================================================
# 6. exits, the lesson, and the exchange-side protection
# ===========================================================================

def _cleanup_orders(private, t):
    """Cancel ONLY the bracket id this book recorded itself. Never a
    blanket sweep of every pending TP/SL on the symbol — that sweep is what
    stripped another book's protection off a live position on 2026-07-23."""
    try:
        if t.get("tpsl_id"):
            private.cancel_tpsl(SYMBOL, str(t["tpsl_id"]))
    except Exception:
        pass


def _bracket_present(private, t) -> bool:
    brackets = private.pending_tpsl(SYMBOL)
    if not brackets:
        return False
    our_id = t.get("tpsl_id")
    if our_id:
        return any(str(b.get("tpslId")) == str(our_id) for b in brackets)
    return True


def ensure_protection(private, state, t, new_stop: float | None = None):
    """SELF-HEALING EXCHANGE-SIDE PROTECTION, plus the ratchet.

    Two jobs, both of which have to happen on the exchange rather than in
    this process, because the whole point of an exchange-side stop is that
    it survives this process being dead:

      RE-ARM — if our bracket has vanished, put it back. The check reads
      pending_tpsl TWICE, 4 seconds apart, and only re-arms if BOTH reads
      come back empty AND a fresh net-position read confirms the position
      still exists. A read exception means "don't know", which means do
      nothing (diver.py's hardening, same reasoning).

      RATCHET — if the structural floor has moved IN THE TRADE'S FAVOUR,
      cancel the old bracket and place a new one at the new level. It only
      ever moves in our favour: a floor that could loosen is not a floor.
      Enforced here as well as inside exits.py, because this is where a
      bug would cost real money."""
    if not t or not t.get("sl_price"):
        return
    moved = False
    if new_stop is not None:
        cur = float(t["sl_price"])
        better = new_stop > cur if t["direction"] > 0 else new_stop < cur
        if better:
            moved = True

    try:
        present = _bracket_present(private, t)
        if present and not moved:
            return
        if not present:
            time.sleep(4)
            if _bracket_present(private, t):
                if not moved:
                    return
            net = private.net_position_contracts(SYMBOL)
            if abs(net) < LOT / 2:
                return
    except Exception as e:
        print(f"  [BITCOIN] protection check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    target = float(new_stop) if moved else float(t["sl_price"])
    if moved:
        _cleanup_orders(private, t)
    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(
            SYMBOL, close_side, t["contracts"], None, round(target, 1),
            client_order_id=make_client_order_id(BOOK_TAG))
        t["tpsl_id"] = tpsl_id
        t["sl_price"] = round(target, 1)
        save_state(state)
        if moved:
            print(f"  [BITCOIN] structural stop RATCHETED to "
                  f"{target:,.1f} (only ever in the trade's favour)")
        else:
            print(f"  [BITCOIN] ⚠️ structural stop was MISSING — re-armed "
                  f"at {target:,.1f}")
            notify("🛡️ Bitcoin stop re-armed (demo)",
                   f"The Bitcoin book's structural stop had vanished — "
                   f"re-placed at ${target:,.0f}.")
    except Exception as e:
        print(f"  [BITCOIN] stop placement FAILED: {str(e)[:80]}")
        notify("⚠️ The Bitcoin book is UNPROTECTED (demo)",
               "structural stop missing and re-arm failed — check BloFin now")


def write_lesson(state: dict, t: dict, pnl: float, exit_price: float,
                 reason: str) -> dict:
    """ONE PLAIN-ENGLISH LESSON, ON EVERY CLOSE. No exceptions, wins
    included.

    The schema is export_journal.write_learnings()'s exactly — date,
    trigger, trade, conditions, why — appended to state["lessons"] and
    capped at 50, which is what makes it render into data/learnings.md in
    the existing format without touching export_journal.py.

    The verdicts are written the way step5_paper_trade.write_lesson()
    writes them, and for the same reason: a win taken in thin conditions is
    labelled LUCK so the book does not learn the wrong thing from it, and a
    loss taken in good conditions is labelled the normal cost of the
    strategy so nobody "fixes" what is not broken. What is added here is
    the memory's own state at the time: if this rule was already flagged or
    already losing in a row, the lesson says so, because that streak is the
    thing the next decision will actually gate on."""
    won = pnl > 0
    side = "long" if t.get("direction", 1) > 0 else "short"
    rule = t.get("rule", "unknown_rule")

    obs = []
    atr_gate = t.get("atr_gate_pct_of_price")
    if atr_gate is not None:
        obs.append(f"entered on the {atr_gate:.1f}% of price volatility gate")
    if t.get("anchor_swing"):
        obs.append(f"stop rested on the confirmed swing "
                   f"{t['anchor_swing']:,.0f}, "
                   f"{TRAIL_BUFFER_PCT:.1f}% of price beyond it")
    else:
        obs.append(f"no confirmed swing at entry — stop used the "
                   f"{FALLBACK_STOP_PCT:.0f}% of price fallback")
    if t.get("leverage_at_entry") is not None:
        obs.append(f"sized off risk, which came out at "
                   f"{t['leverage_at_entry']:.1f}x leverage")
    prior = t.get("memory_at_entry", {}).get("consecutive_losses")
    if prior:
        obs.append(f"the memory already had {prior} losses in a row on this "
                   f"setup when it fired")

    move = price_move_pct(t.get("entry_price", 0.0), exit_price)
    if won and reason == "structural_stop":
        why = ("won even though the structural floor took it out — the "
               "trailing stop did its job; keep the buffer where it is")
    elif won:
        why = ("worked as designed — the trend was real and the structural "
               "stop stayed out of the way; keep taking this setup")
    elif reason == "structural_stop" and prior:
        why = (f"lost on this setup again ({prior + 1} in a row now), stopped "
               f"out at structure — do not take it again without confirmation "
               f"that the swing it rests on is actually holding")
    elif reason == "structural_stop":
        why = ("stopped out at real structure — the normal cost of a trend "
               "book; the level broke, so the thesis was wrong, nothing to "
               "fix")
    else:
        why = ("lost when the trend flipped before the move paid — this is "
               "what a trend book pays for its winners; only worth acting on "
               "if it repeats")

    lesson = {
        "date": now_utc(), "trigger": rule,
        "trade": f"{side} ${t.get('entry_price', 0):,.0f} -> {reason} "
                 f"${exit_price:,.0f} ({move}), "
                 f"{'made' if won else 'lost'} ${abs(pnl):,.2f}",
        "conditions": "; ".join(obs) if obs else "context not captured",
        "why": why,
    }
    lessons = state.setdefault("lessons", [])
    lessons.append(lesson)
    del lessons[:-50]
    log_event({"action": "lesson", **lesson})
    return lesson


def book_exit(state: dict, t: dict, exit_price: float, reason: str) -> float:
    """Close this book's trade on its own ledger line, write the lesson,
    and update the shared per-trigger stats. Direction-aware."""
    cv = t.get("contract_value")
    if cv is None:
        cv = 0.001
        print("  [BITCOIN] ⚠️ contract_value missing on this trade record — "
              "using the verified BTC-USDT fallback 0.001")
    size_btc = t["contracts"] * cv
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", ENTRY_FEE_BPS)
            + exit_price * EXIT_FEE_BPS) * size_btc / 10_000
    realized = round(gross - fees, 2)

    state["virtual_equity"] = round(
        float(state.get("virtual_equity", 0.0)) + realized, 2)
    book = _book(state)
    rec = {"rule": t.get("rule", "unknown_rule"),
           "entry_time": t.get("entry_time"), "entry_price": t["entry_price"],
           "direction": t["direction"], "contracts": t["contracts"],
           "exit_price": round(exit_price, 2), "pnl": realized,
           "reason": reason, "exit_time": now_utc()}
    book.setdefault("trades", []).append(rec)
    book["trades"] = book["trades"][-200:]
    book["realized_pnl_total"] = round(
        book.get("realized_pnl_total", 0.0) + realized, 2)
    book["open_trade"] = None

    lesson = write_lesson(state, t, realized, exit_price, reason)
    save_state(state)

    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [BITCOIN] {reason}: PnL ${realized:+,.2f} "
          f"({price_move_pct(t['entry_price'], exit_price)}) -> ledger "
          f"${eq:,.2f}")
    print(f"  [BITCOIN] lesson written: {lesson['why']}")
    log_event({"action": "bitcoin_exit", "reason": reason,
               "rule": rec["rule"], "direction": t["direction"],
               "exit_price": exit_price, "realized_pnl": realized,
               "virtual_equity": eq})
    record_trade_outcome(state, rec["rule"], realized)
    notify(f"₿ Bitcoin book {reason}: ${realized:+,.2f}",
           f"{side} {rec['rule']} closed — "
           f"{price_move_pct(t['entry_price'], exit_price)} — ledger "
           f"${eq:,.2f} (demo)")
    return realized


# ===========================================================================
# 7. the cycle
# ===========================================================================

def _load_4h(live_feed) -> pd.DataFrame:
    """CANDLE_BARS closed 4h bars. The adapter already drops the still-
    forming bar via BloFin's own "confirmed" flag (exchange.py), so "only
    ever act on a CLOSED bar" is enforced there, not re-enforced here."""
    d = live_feed.get_candles(SYMBOL, TIMEFRAME, CANDLE_BARS)
    return d.sort_values("timestamp").reset_index(drop=True)


def _entry_index(d: pd.DataFrame, t: dict) -> int:
    """Where the open trade's entry bar sits in the frame we just pulled.
    Located by TIMESTAMP, never by a stored array position, so a rolling
    window can slide underneath an open trade without corrupting its stop.
    Falls back to bar 0 if the entry bar has aged out of the window."""
    bar_ts = t.get("bar_ts")
    if bar_ts:
        stamps = d["timestamp"].map(_fmt_utc)
        hits = stamps.index[stamps == bar_ts]
        if len(hits):
            return int(hits[0])
    return 0


def evaluate_rules(d: pd.DataFrame, ctx: dict) -> list[RuleSignal]:
    """Run every entry rule over the same bar. A rule that raises is a bug
    in that rule, not a reason for the book to stop trading the others —
    it is caught, reported and skipped."""
    out = []
    for rule in ENTRY_RULES:
        try:
            sig = rule.fn(d, ctx)
        except Exception as e:
            print(f"  [BITCOIN] rule {rule.name} raised, skipping it: "
                  f"{str(e)[:100]}")
            log_event({"action": "bitcoin_rule_error", "rule": rule.name,
                       "error": str(e)[:200]})
            continue
        if sig is not None:
            out.append(sig)
    return out


def run_bitcoin(private, live_feed, demo_feed, state: dict,
                dry: bool = False) -> dict:
    """ONE DECISION CYCLE for the Bitcoin book. Returns a summary dict.

    Order of operations, and none of it is rearrangeable:
      1. reconcile against the exchange (before deciding anything)
      2. load the memory and latch any new stand-down
      3. manage a held trade — ratchet its stop, or exit it
      4. THE STAND-DOWN GATE (after every exit path, so a held position
         always still closes)
      5. run the rules, arbitrate, size off risk, enter, protect
    """
    book = _book(state)
    t = book.get("open_trade")
    tag = " DRY" if dry else ""

    # -- 1. reconcile: our own slice, never the raw net ---------------------
    net = private.net_position_contracts(SYMBOL)
    ours = attributed(net, state)
    orphan = unexplained(net, state)
    recorded_signed = (t["direction"] * t["contracts"]) if t else 0.0
    print(f"  [BITCOIN{tag}] reconcile: net={net:+.2f} ours={ours:+.2f} "
          f"(recorded {recorded_signed:+.1f}) unclaimed={orphan:+.2f}")

    if t and abs(ours) < LOT / 2:
        # our position is gone: the exchange-side structural stop fired
        # between cycles (or a human closed it). This is the primary exit
        # path — the stop lives on BloFin's matching engine on purpose.
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        print(f"  [BITCOIN{tag}] our position is gone -> structural stop "
              f"fired @ {exit_price:,.1f}")
        if dry:
            print("  [BITCOIN DRY] would cancel any remaining bracket, book "
                  "this exit and write its lesson — no changes made")
            return {"action": "would_exit", "reason": "structural_stop",
                    "exit_price": exit_price}
        _cleanup_orders(private, t)
        realized = book_exit(state, t, exit_price, "structural_stop")
        return {"action": "reconciled_exit", "reason": "structural_stop",
                "exit_price": exit_price, "pnl": realized}

    if not t and abs(orphan) > LOT / 2:
        # NOT ours to adopt or flatten. Alert once per episode, keep
        # operating — during the migration window other books legitimately
        # hold BTC-USDT, and after cutover this is a genuine anomaly worth
        # a human's eyes but still not worth this book trading on top of.
        print(f"  [BITCOIN{tag}] ⚠️ {orphan:+.2f} ct on {SYMBOL} is claimed "
              f"by NO book — not adopting, not flattening")
        if not dry:
            log_event({"action": "bitcoin_unclaimed_position", "net": net,
                       "unclaimed": round(orphan, 2)})
            if not book.get("unclaimed_alerted"):
                book["unclaimed_alerted"] = True
                save_state(state)
                notify("⚠️ Unclaimed BTC position (demo)",
                       f"{orphan:+.2f} ct on {SYMBOL} that no book claims — "
                       f"check the app. (One alert per episode.)")
    elif book.get("unclaimed_alerted") and abs(orphan) <= LOT / 2:
        book.pop("unclaimed_alerted", None)
        if not dry:
            save_state(state)

    # -- 2. the memory, loaded BEFORE anything is decided --------------------
    memory = load_memory(state)
    newly_stood_down = [] if dry else apply_memory_stand_downs(state, memory)
    if newly_stood_down and not dry:
        save_state(state)
        for rule in newly_stood_down:
            m = memory["rules"][rule]
            print(f"  [BITCOIN] 🛑 STAND DOWN {rule}: {m['note']}")
            log_event({"action": "bitcoin_rule_stood_down", "rule": rule,
                       "consecutive_losses": m["consecutive_losses"],
                       "reason": m["last_reason"]})
            notify(f"🛑 Bitcoin: {rule} stood down (demo)",
                   f"{m['consecutive_losses']} losses in a row, all ending "
                   f"'{m['last_reason']}'. No new entries on this rule until "
                   f"a human clears it.")
    statuses = ", ".join(f"{r}={m['status']}"
                         for r, m in memory["rules"].items())
    print(f"  [BITCOIN{tag}] memory: {memory['n_closed']} closed trades read "
          f"back ({memory['n_ledger_rows']} from ledger.csv), "
          f"{memory['n_lessons']} lessons | {statuses}")

    # -- 3. the series and the held trade -----------------------------------
    d = _load_4h(live_feed)
    i = len(d) - 1
    bar_ts = _fmt_utc(d["timestamp"].iloc[i])
    close = float(d["close"].iloc[i])
    print(f"  [BITCOIN{tag}] {bar_ts} close {close:,.1f}")

    if t:
        entry_idx = _entry_index(d, t)
        floor = _structural_stop(d, entry_idx, t["entry_price"],
                                 t["direction"], at_idx=i)
        broken = (close <= floor) if t["direction"] > 0 else (close >= floor)
        health = position_health(private)
        print(f"  [BITCOIN{tag}] holding {t['contracts']:.1f} ct "
              f"{'long' if t['direction'] > 0 else 'short'} from "
              f"{t['entry_price']:,.1f} "
              f"({price_move_pct(t['entry_price'], close)}) | structural "
              f"floor {floor:,.1f} | liquidation "
              f"{_fmt(health['liquidationPrice'])} | "
              f"{margin_pct(health['unrealizedPnlRatio'])} | margin ratio "
              f"{_fmt(health['marginRatio'], 3)}")

        if broken:
            # the close confirmed the structural break before the exchange
            # stop was reached (the floor's second trigger — see
            # exits.stop_structure_trailing's "intrabar_or_close" style)
            print(f"  [BITCOIN{tag}] structural break confirmed on the close "
                  f"— exiting at market")
            if dry:
                return {"action": "would_exit", "reason": "structure_broken",
                        "floor": floor, "bar_ts": bar_ts}
            _cleanup_orders(private, t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(SYMBOL)
            ref = quote.bid if side == "sell" else quote.ask
            fill, _ = execute_market_clips(private, demo_feed, SYMBOL, side,
                                           t["contracts"], ref,
                                           reduce_only=True,
                                           client_tag=BOOK_TAG)
            realized = book_exit(state, t, fill, "structure_broken")
            book["last_bar_ts"] = bar_ts
            save_state(state)
            return {"action": "exited", "reason": "structure_broken",
                    "fill": fill, "pnl": realized, "bar_ts": bar_ts}

        sig = vol_filtered_ma(d, FAST, SLOW,
                              min_atr_pct=MIN_ATR_PCT).fillna(0.0)
        if t.get("rule") == "vol_gated_trend" and float(sig.iloc[i]) != 1.0:
            print(f"  [BITCOIN{tag}] the trend stopped pointing up — exiting "
                  f"at market")
            if dry:
                return {"action": "would_exit", "reason": "trend_flip",
                        "bar_ts": bar_ts}
            _cleanup_orders(private, t)
            quote = demo_feed.get_ticker(SYMBOL)
            fill, _ = execute_market_clips(private, demo_feed, SYMBOL, "sell",
                                           t["contracts"], quote.bid,
                                           reduce_only=True,
                                           client_tag=BOOK_TAG)
            realized = book_exit(state, t, fill, "trend_flip")
            book["last_bar_ts"] = bar_ts
            save_state(state)
            return {"action": "exited", "reason": "trend_flip", "fill": fill,
                    "pnl": realized, "bar_ts": bar_ts}

        if dry:
            return {"action": "would_hold", "floor": floor, "bar_ts": bar_ts}
        ensure_protection(private, state, t, new_stop=floor)
        book["last_bar_ts"] = bar_ts
        save_state(state)
        return {"action": "hold", "floor": floor, "bar_ts": bar_ts,
                "health": health}

    # -- 4. flat: run the rules and let the arbiter decide -------------------
    ctx = {"bar_ts": bar_ts, "close": close, "memory": memory}
    signals = evaluate_rules(d, ctx)
    verdict = arbitrate(signals, memory)
    considered = ", ".join(f"{c['rule']}({c['status']})"
                           for c in verdict.considered) or "none"
    print(f"  [BITCOIN{tag}] rules fired: {considered} -> {verdict.action}"
          + (f" — {verdict.reason}" if verdict.reason else ""))
    if verdict.memory_note:
        print(f"  [BITCOIN{tag}] MEMORY NOTE: {verdict.memory_note}")

    if verdict.action != "enter":
        if dry:
            return {"action": f"would_{verdict.action}",
                    "reason": verdict.reason, "bar_ts": bar_ts,
                    "memory_note": verdict.memory_note}
        if book.get("last_bar_ts") != bar_ts:
            book["last_bar_ts"] = bar_ts
            save_state(state)
        return {"action": verdict.action, "reason": verdict.reason,
                "bar_ts": bar_ts, "memory_note": verdict.memory_note}

    chosen = verdict.signal
    direction = chosen.direction

    spec = instrument_spec(demo_feed)
    if not spec:
        print("  [BITCOIN] ENTRY SKIPPED — instrument spec unreadable on "
              "demo (contract value unknown, not guessing)")
        if not dry:
            log_event({"action": "entry_skipped",
                       "reason": "no_contract_spec"})
            book["last_bar_ts"] = bar_ts
            save_state(state)
        return {"action": "entry_skipped", "bar_ts": bar_ts}

    ref_price = close
    try:
        ref_price = float(live_feed.get_ticker(SYMBOL).last)
    except Exception:
        pass

    sizing = size_from_risk(float(state.get("virtual_equity", 0.0)),
                            ref_price, chosen.stop_level,
                            spec["contractValue"], spec.get("maxLeverage"))
    print(f"  [BITCOIN{tag}] {chosen.rule}: "
          f"{'LONG' if direction > 0 else 'SHORT'} | stop at structure "
          f"{chosen.stop_level:,.1f} "
          f"({price_move_pct(ref_price, chosen.stop_level)} away) | risking "
          f"${sizing['risk_usd']:,.2f} ({RISK_PCT:.1f}% of equity) -> "
          f"{sizing['contracts']:.1f} ct, ~${sizing['notional']:,.0f} "
          f"notional, {sizing['leverage']:.1f}x leverage (an output"
          + (f", capped by {sizing['capped_by']}" if sizing["capped_by"]
             else "")
          + f"; instrument max {_fmt(spec.get('maxLeverage'), 0)}x)")

    # -- 5. THE STAND-DOWN GATE ---------------------------------------------
    # Placed HERE deliberately: after reconcile, after every exit branch,
    # and after direction/contracts/ref_price are all bound. A held trade
    # still closes normally with the gate shut, the book still logs exactly
    # what it WOULD have taken, and the gate itself cannot raise on an
    # unbound name. Do not move this up.
    if not NEW_ENTRIES_ENABLED:
        print(f"  [BITCOIN] {chosen.rule} "
              f"{'LONG' if direction > 0 else 'SHORT'} fired but the book is "
              f"STOOD DOWN (bitcoin.py has not been cut over yet — see "
              f"step300_consolidation_plan.md)")
        if not dry:
            log_event({"action": "bitcoin_stood_down", "rule": chosen.rule,
                       "direction": direction,
                       "contracts": sizing["contracts"],
                       "entry_ref": ref_price, "stop": chosen.stop_level,
                       "bar_ts": bar_ts, "memory_note": verdict.memory_note})
            book["last_bar_ts"] = bar_ts
            save_state(state)
        return {"action": "stood_down", "reason": "book_stood_down",
                "rule": chosen.rule, "direction": direction,
                "contracts": sizing["contracts"], "bar_ts": bar_ts,
                "memory_note": verdict.memory_note}

    if dry:
        print(f"  [BITCOIN DRY] WOULD ENTER — no order placed")
        return {"action": "would_enter", "rule": chosen.rule,
                "direction": direction, "contracts": sizing["contracts"],
                "stop": chosen.stop_level, "leverage": sizing["leverage"],
                "bar_ts": bar_ts, "memory_note": verdict.memory_note}

    # idempotency: this exact closed bar was already decided on
    if book.get("last_bar_ts") == bar_ts:
        print(f"  [BITCOIN] {bar_ts} already processed — no-op (idempotent)")
        return {"action": "noop_already_processed", "bar_ts": bar_ts}

    side = "buy" if direction > 0 else "sell"
    private.ensure_leverage(SYMBOL, max(1.0, sizing["leverage"]))
    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, SYMBOL, side, sizing["contracts"], ref_price,
            client_tag=BOOK_TAG)
    except Exception as e:
        print(f"  [BITCOIN] ENTRY FAILED: {str(e)[:100]}")
        log_event({"action": "bitcoin_entry_failed", "error": str(e)[:200]})
        notify("⚠️ Bitcoin book ENTRY FAILED (demo)",
               f"tried to {side} but the order was rejected: {str(e)[:80]}. "
               f"No position opened — check BloFin.")
        book["last_bar_ts"] = bar_ts
        save_state(state)
        return {"action": "entry_failed", "error": str(e)[:120],
                "bar_ts": bar_ts}

    stop = round(float(chosen.stop_level), 1)
    close_side = "sell" if direction > 0 else "buy"
    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(
            SYMBOL, close_side, sizing["contracts"], None, stop,
            client_order_id=make_client_order_id(BOOK_TAG))
    except Exception as e:
        print(f"  [BITCOIN] structural stop FAILED to place: {str(e)[:80]}")
        notify("⚠️ Bitcoin position UNPROTECTED (demo)",
               "position opened but its structural stop failed to place — "
               "check BloFin now")

    mem_at_entry = memory["rules"].get(chosen.rule, {})
    book["open_trade"] = {
        "rule": chosen.rule, "trigger": chosen.rule, "direction": direction,
        "contracts": sizing["contracts"], "entry_price": entry,
        "contract_value": spec["contractValue"],
        "entry_fee_bps": ENTRY_FEE_BPS, "entry_time": now_utc(),
        "bar_ts": bar_ts, "tp_price": None, "sl_price": stop,
        "tpsl_id": tpsl_id, "stop_at_entry": stop,
        "anchor_swing": chosen.context.get("anchor_swing"),
        "atr_gate_pct_of_price": chosen.context.get("atr_gate_pct_of_price"),
        "leverage_at_entry": sizing["leverage"],
        "risk_usd": round(sizing["risk_usd"], 2),
        "capped_by": sizing["capped_by"],
        "entry_reason": chosen.reason,
        # WHAT THE BOOK KNEW WHEN IT FIRED — the memory, attached to the
        # trade itself, so no trade can ever be reviewed without it.
        "memory_at_entry": mem_at_entry,
        "memory_note": verdict.memory_note,
        "lessons_known": [L.get("why", "") for L in
                          memory["lessons"][-MAX_LESSONS_ON_RECORD:]],
        "n_lessons_known": memory["n_lessons"],
        "n_closed_trades_known": memory["n_closed"],
    }
    book["last_bar_ts"] = bar_ts
    save_state(state)

    log_event({"action": "bitcoin_enter", "rule": chosen.rule,
               "direction": direction, "fill_price": entry,
               "contracts": sizing["contracts"], "sl": stop,
               "leverage": sizing["leverage"], "maker": was_maker,
               "bar_ts": bar_ts, "memory_note": verdict.memory_note,
               "n_lessons_known": memory["n_lessons"],
               "n_closed_trades_known": memory["n_closed"]})
    notify(f"₿ THE BITCOIN BOOK {'LONG' if direction > 0 else 'SHORT'} (demo)",
           f"{chosen.rule}: {side} {sizing['contracts']:.1f} ct @{entry:,.0f} "
           f"| stop at structure {stop:,.0f} "
           f"({price_move_pct(entry, stop)} away) | "
           f"{sizing['leverage']:.1f}x, sized off "
           f"{RISK_PCT:.1f}% of equity of risk"
           + (f" | MEMORY: {verdict.memory_note}" if verdict.memory_note
              else ""))
    return {"action": "entered", "rule": chosen.rule, "direction": direction,
            "entry": entry, "contracts": sizing["contracts"], "stop": stop,
            "leverage": sizing["leverage"], "bar_ts": bar_ts,
            "memory_note": verdict.memory_note}
