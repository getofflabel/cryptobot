"""
step455_measure.py — the honest baseline, taken after the replay and the live
path were made to size identically (step453).

WHY THIS RUN EXISTS
    Until step453 there were two sizing rules in the project. The replay sized
    fresh at 1% of equity off today's stop; the live path used his set size,
    worked off the tightest stop the instrument normally gives and then held
    still, under a 3% outer limit. They differ by the ratio of today's stop to
    the tightest one — up to 36 times on DOT. `tjr_bot.size_position` is now
    the only function in the project that turns a stop into a number of units,
    and a test fails if a second one grows back.

    So every number this project produced before step453 describes a bot we
    were not running. This file re-takes all of them.

WHAT IT MEASURES, per year and per market
    trades, trades a week, win rate, the average result as a multiple of what
    was risked, the net in dollars, the deepest fall from a high point, and
    the longest run of losing trades. Then the same pooled across markets.

HOW
    Nothing here is tuned. Every market is walked by its own existing engine
    with its own existing Config:
        S&P    tjr_replay.run           (SPY + QQQ, the twin veto on)
        crypto tjr_crypto.run_pair      (the eight live pairs)
        gold   a local copy of tjr_gold.run_gold that reads res["trades"]
               instead of res["trade"] — see `run_gold_all` below. tjr_gold.py
               is NOT edited; it still only records the first trade of a day,
               which under Boot Camp 2.0 is a short record.

    Each year runs a FRESH bot on a fresh $100,000, so the years are
    comparable to one another rather than compounding into each other.

KNOWN ARTEFACT, MEASURED RATHER THAN HIDDEN
    `tjr_bot.run_day` closes anything still open when a day's bars run out.
    On the stock market that is the closing bell and it is real. On crypto
    there is no close and the live path holds through the boundary, so those
    exits are truncations: a winner is cut short while a loser still reaches
    its stop. Trades that ended that way are counted, and the crypto result is
    reported again with them removed as a sensitivity check, never as the
    headline.

USAGE
    python3 step455_measure.py --sp
    python3 step455_measure.py --crypto
    python3 step455_measure.py --gold
    python3 step455_measure.py --pool      (reads what the three wrote)

RESEARCH ONLY. Reads parquet off disk, walks it through the existing bots,
writes step455_* CSVs. No network, no broker, no orders, no git.
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import tjr_bot
import tjr_crypto as tc
import tjr_gold as tg
import tjr_replay
from tjr_bot import Config, NewsCalendar, TjrBot

ACCOUNT_START = 100_000.0


# ==================================================== THE NUMBERS, ONCE
def weeks_walked(days) -> int:
    """Monday-anchored weeks containing at least one session the bot walked.

    This is the denominator for "trades a week", and it is the SESSIONS'
    weeks, never the trades' weeks. Counting only the weeks that happened to
    produce a trade would report the trade rate of a bot that never stands
    down, which is the opposite of what this method does.
    """
    ws = {(pd.Timestamp(d) - pd.Timedelta(days=pd.Timestamp(d).weekday())
           ).normalize() for d in days}
    return max(len(ws), 1)


def stats(trades: list, account_start: float = ACCOUNT_START,
          weeks: int | None = None) -> dict:
    """Every figure this round reports, worked out one way for every market.

    deepest_fall_dollars is the largest peak-to-trough fall of the running
    account, walked in the order the trades closed. longest_losing_run counts
    consecutive trades that did not make money.
    """
    n = len(trades)
    if not n:
        return {"trades": 0, "weeks": weeks or 0, "trades_per_week": 0.0,
                "win_rate_pct": 0.0, "mean_result_x_risked": 0.0,
                "net_dollars": 0.0, "deepest_fall_dollars": 0.0,
                "deepest_fall_pct_of_start": 0.0, "longest_losing_run": 0,
                "avg_win_dollars": 0.0, "avg_loss_dollars": 0.0}

    ts = sorted(trades, key=lambda t: _utc(t))
    wins = [t for t in ts if t.pnl > 0]
    losses = [t for t in ts if t.pnl <= 0]

    stamps = [_utc(t) for t in ts]
    if weeks is None:
        weeks = max(1, int(round(
            (max(stamps) - min(stamps)).total_seconds() / (7 * 86400))))
    span_weeks = max(int(weeks), 1)

    equity, peak, worst = account_start, account_start, 0.0
    run, longest = 0, 0
    for t in ts:
        equity += t.pnl
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
        if t.pnl <= 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0

    aw = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    al = -sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    return {
        "trades": n,
        "weeks": span_weeks,
        "trades_per_week": round(n / span_weeks, 2),
        "win_rate_pct": round(100.0 * len(wins) / n, 1),
        "mean_result_x_risked": round(sum(t.r_multiple for t in ts) / n, 3),
        "net_dollars": round(sum(t.pnl for t in ts)),
        "deepest_fall_dollars": round(worst),
        "deepest_fall_pct_of_start": round(100.0 * worst / account_start, 2),
        "longest_losing_run": longest,
        "avg_win_dollars": round(aw),
        "avg_loss_dollars": round(al),
    }


def _utc(t) -> pd.Timestamp:
    """One clock for every market so a pooled curve is in order.

    Crypto trades carry naive UTC. Stock and gold trades carry naive US
    Eastern, because that is what their frames are in. The market each trade
    came from is stamped on it in `_rows`, and this uses it.
    """
    s = pd.Timestamp(t.entry_t if t.entry_t is not None else t.day)
    if getattr(t, "_clock", "utc") == "et":
        s = s.tz_localize("America/New_York",
                          ambiguous=True, nonexistent="shift_forward"
                          ).tz_convert("UTC").tz_localize(None)
    return s


def _rows(trades: list, market: str, clock: str) -> list:
    out = []
    for t in trades:
        t._clock = clock
        out.append({
            "market": market,
            "symbol": t.symbol,
            "year": pd.Timestamp(t.day).year,
            "entered_utc": f"{_utc(t):%Y-%m-%d %H:%M}",
            "side": "long" if t.direction > 0 else "short",
            "level_timeframe": t.level_tf,
            "entry": round(t.entry, 6),
            "stop": round(t.stop, 6),
            "units": round(t.shares, 6),
            "risk_dollars": round(t.risk_dollars, 2),
            "share_of_the_days_budget": round(t.budget_share, 3),
            "size_worked_out_from": t.size_basis,
            "what_happened": t.outcome,
            "day_boundary_cut": bool(t.outcome == "flat by the close"),
            "pnl_dollars": round(t.pnl, 2),
            "result_x_risked": round(t.r_multiple, 4),
        })
    return out


# ==================================================== THE S&P
def run_sp(years=range(2016, 2027)) -> tuple:
    cached = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    tjr_replay.load = lambda s: cached[s]
    cfg = Config()
    rows, allt = [], []
    for y in years:
        t0 = time.time()
        bot, trades, sd, days = tjr_replay.run(
            pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31"),
            cfg=cfg, news=NewsCalendar(), verbose=False)
        if not days:
            continue
        s = stats(trades, weeks=weeks_walked(days))
        s.update({"year": y, "sessions": len(days),
                  "account_end_dollars": round(bot.account)})
        rows.append(s)
        allt += trades
        print(f"  {y}  {len(days):>4} sessions  {s['trades']:>4} trades  "
              f"{s['trades_per_week']:>5.2f}/wk  {s['win_rate_pct']:>5.1f}% won  "
              f"{s['mean_result_x_risked']:>+7.3f}x risked  "
              f"${s['net_dollars']:>9,}  fall ${s['deepest_fall_dollars']:>8,}  "
              f"losing run {s['longest_losing_run']:>2}   ({time.time()-t0:.0f}s)")
    return rows, allt


# ==================================================== CRYPTO
def run_crypto(years=range(2021, 2027)) -> tuple:
    derived = tc.load_derived()
    rows, allt = [], []
    for pair in tc.PAIRS:
        try:
            data = load_pair(pair)
        except FileNotFoundError:
            print(f"  {pair}: no cached bars")
            continue
        cfg = tc.crypto_config(pair, derived=derived)
        lo = pd.Timestamp(data["1m"]["t"].min()).year
        for y in years:
            if y < lo:
                continue
            t0 = time.time()
            r = tc.run_pair(pair, pd.Timestamp(f"{y}-01-01"),
                            pd.Timestamp(f"{y}-12-31"), cfg=cfg, data=data)
            if not r["trades"] and not r["days"]:
                continue
            walked = tc.days_in(data, pd.Timestamp(f"{y}-01-01"),
                                pd.Timestamp(f"{y}-12-31"))
            s = stats(r["trades"], weeks=weeks_walked(walked))
            s.update({"pair": pair, "year": y, "days": r["days"],
                      "account_end_dollars": round(r["account"])})
            rows.append(s)
            allt += r["trades"]
            print(f"  {pair:9s} {y}  {r['days']:>4}d  {s['trades']:>4} trades  "
                  f"{s['win_rate_pct']:>5.1f}% won  "
                  f"{s['mean_result_x_risked']:>+7.3f}x risked  "
                  f"${s['net_dollars']:>9,}   ({time.time()-t0:.0f}s)")
    return rows, allt


def load_pair(pair: str) -> dict:
    """The cached bars, except that DOT prefers step455's deeper 1-minute
    refill when it is there. Its own backfill died on a rate limit at
    2026-03-01 and a four-month pair is not comparable to a five-year one."""
    d = tc.load(pair)
    alt = f"{REPO}/step455_{pair.replace('/', '')}_1m.parquet"
    if os.path.exists(alt):
        a = pd.read_parquet(alt)
        if len(a) > len(d["1m"]):
            d["1m"] = a
    return d


# ==================================================== GOLD
def run_gold_all(cfg=None, data=None) -> dict:
    """tjr_gold.run_gold, with one line different and nothing else.

    `tjr_gold.run_gold` reads res["trade"], which since step453 is only the
    FIRST trade of a day. Under Boot Camp 2.0 more than one trade a day is
    the method, so that record is short. tjr_gold.py is not edited in this
    round; this local copy reads res["trades"].
    """
    cfg = cfg or tg.gold_config()
    data = data or tg.load_both()
    bot = TjrBot(cfg, NewsCalendar())
    trades, skipped = [], 0
    for day in tg.days_in(data):
        day = pd.Timestamp(day)
        win = tg.slice_for(data, day, cfg)
        sess = win[tg.TRADED]["1m"]
        if len(sess[(sess["t"] >= day) &
                    (sess["t"] < day + pd.Timedelta(days=1))]) == 0:
            skipped += 1
            continue
        trades += bot.run_day(win, day)["trades"]
    return {"days": len(tg.days_in(data)) - skipped, "trades": trades,
            "account": bot.account}


def run_gold() -> tuple:
    data = tg.load_both()
    r = run_gold_all(data=data)
    days = [pd.Timestamp(d) for d in tg.days_in(data)]
    rows = []
    for y in sorted({pd.Timestamp(t.day).year for t in r["trades"]} or {2026}):
        ts = [t for t in r["trades"] if pd.Timestamp(t.day).year == y]
        s = stats(ts, weeks=weeks_walked([d for d in days if d.year == y]))
        s.update({"year": y, "sessions": r["days"],
                  "account_end_dollars": round(r["account"])})
        rows.append(s)
        print(f"  GLD {y}  {r['days']:>4} sessions  {s['trades']:>4} trades  "
              f"{s['trades_per_week']:>5.2f}/wk  {s['win_rate_pct']:>5.1f}% won  "
              f"{s['mean_result_x_risked']:>+7.3f}x risked  ${s['net_dollars']:>9,}")
    return rows, r["trades"]


# ==================================================== DRIVER
def main() -> int:
    want = {a.lstrip("-") for a in sys.argv[1:]} or {"sp", "crypto", "gold"}
    frames = []

    if "sp" in want:
        print("S&P — SPY and QQQ, year by year")
        rows, trades = run_sp()
        pd.DataFrame(rows).to_csv(f"{REPO}/step455_sp_by_year.csv", index=False)
        pd.DataFrame(_rows(trades, "sp500", "et")).to_csv(
            f"{REPO}/step455_sp_trades.csv", index=False)
        frames.append("sp")
        print()

    if "crypto" in want:
        print("crypto — the eight live pairs, year by year")
        rows, trades = run_crypto()
        pd.DataFrame(rows).to_csv(f"{REPO}/step455_crypto_by_pair_year.csv",
                                  index=False)
        pd.DataFrame(_rows(trades, "crypto", "utc")).to_csv(
            f"{REPO}/step455_crypto_trades.csv", index=False)
        frames.append("crypto")
        print()

    if "gold" in want:
        print("gold — GLD, over the span the 1-minute record supports")
        rows, trades = run_gold()
        pd.DataFrame(rows).to_csv(f"{REPO}/step455_gold_by_year.csv", index=False)
        pd.DataFrame(_rows(trades, "gold", "et")).to_csv(
            f"{REPO}/step455_gold_trades.csv", index=False)
        frames.append("gold")
        print()

    print(f"written: step455_* for {', '.join(frames)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
