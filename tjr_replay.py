"""
tjr_replay.py — walk real SPY and QQQ sessions through tjr_bot, bar by bar,
strictly causally, and write down what a week of trading his way looks like.

WHAT IT DOES
    Loads the cached Alpaca 1-minute and 5-minute bars, converts them to US
    Eastern, and hands each session to `TjrBot.run_day`. The bot never sees a
    bar it has not reached; this file only feeds it and records the answers.

WHAT IT RECORDS
    For every trade: the date and time, which level was swept and what
    timeframe it came from, what confirmed it, the entry, where the stop went
    and which chart feature it rests on, both targets, what actually
    happened, and the result in dollars and as a percent of the account.
    For every day with NO trade: why. Those days are the method working.

HIS OWN STANDARD, RECORDED HONESTLY
    He does not count replay as evidence at all — only live and demo. This
    file exists so the shape of a week is visible, not to prove anything.

USAGE
    python3 tjr_replay.py                 # the last 4 trading weeks
    python3 tjr_replay.py 2026-06-01 2026-07-24
    python3 tjr_replay.py --weeks 12

RESEARCH ONLY. No orders. Nothing here can reach a broker.
"""

from __future__ import annotations

import sys

import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
from tjr_bot import Config, NewsCalendar, TjrBot, to_et_frame

REPO = "/Users/wallacechen/cryptobot"
SYMBOLS = ["SPY", "QQQ"]


def load(symbol: str) -> dict:
    d5 = to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_5m.parquet"))
    d1 = to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_{symbol}_1m.parquet"))
    return {"5m": d5, "1m": d1}


def trading_days(data: dict, start, end) -> list:
    days = set()
    for s in data:
        t = data[s]["1m"]["t"]
        d = t[(t >= start) & (t < end + pd.Timedelta(days=1))]
        tt = d[(d.dt.time >= tjr_bot.OPEN_T) & (d.dt.time < tjr_bot.CLOSE_T)]
        days |= set(tt.dt.normalize().unique())
    return sorted(days)


def slice_for(data: dict, day: pd.Timestamp, cfg: Config) -> dict:
    """Only the history the bot could possibly need, so a session is cheap.
    Bars AFTER the session end are cut too — the bot never reads them, and
    cutting them makes that visible."""
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    out = {}
    for s, f in data.items():
        out[s] = {tf: f[tf][(f[tf]["t"] >= lo) & (f[tf]["t"] < hi)]
                  .reset_index(drop=True) for tf in ("5m", "1m")}
    return out


def run(start, end, cfg: Config | None = None, news: NewsCalendar | None = None,
        verbose: bool = True):
    cfg = cfg or Config()
    news = news or NewsCalendar()
    data = {s: load(s) for s in SYMBOLS}
    days = trading_days(data, start, end)
    bot = TjrBot(cfg, news)

    trades, stand_downs = [], []
    for day in days:
        res = bot.run_day(slice_for(data, day, cfg), day)
        if res["trades"]:
            trades += res["trades"]
            for tr in res["trades"]:
                if not verbose:
                    continue
                share = (f"{100*tr.budget_share:.0f}% of the day's budget"
                         if tr.budget_share < 0.999 else "the day's budget")
                print(f"{day:%Y-%m-%d} TRADE  {tr.symbol} "
                      f"{'long' if tr.direction > 0 else 'short'} "
                      f"{tr.level_tf} level {tr.level_price:.2f} swept "
                      f"{tr.swept_at:%H:%M} -> in {tr.entry_t:%H:%M} @ "
                      f"{tr.entry:.2f}, stop {tr.stop:.2f} "
                      f"({tr.risk_per_share:.2f}/share), {tr.shares:,.0f} sh "
                      f"on {share}, {tr.outcome} -> ${tr.pnl:,.0f} "
                      f"({tr.pct_of_account:+.2f}% of the account)")
        else:
            why = "; ".join(f"{k}: {v}" for k, v in res["stand_down"].items())
            stand_downs.append({"day": day, "why": why,
                                "escalated": res["escalated"]})
            if verbose:
                print(f"{day:%Y-%m-%d} stand down  {why}")
    return bot, trades, stand_downs, days


def to_csv(trades, path: str) -> pd.DataFrame:
    rows = []
    for t in trades:
        rows.append({
            "date": f"{t.day:%Y-%m-%d}", "symbol": t.symbol,
            "side": "long" if t.direction > 0 else "short",
            "level_timeframe": t.level_tf, "level_price": round(t.level_price, 4),
            "swept_at": f"{t.swept_at:%H:%M}",
            "confirmed_by": t.confirm_kind,
            "confirmed_at": f"{t.confirmed_at:%H:%M}",
            "pullback_into": t.pullback_kind,
            "entry_at": f"{t.entry_t:%H:%M}", "entry": round(t.entry, 4),
            "stop": round(t.stop, 4), "stop_rests_on": t.stop_anchor,
            "risk_per_share": round(t.risk_per_share, 4),
            "shares": round(t.shares, 2), "notional": round(t.notional, 2),
            "risk_wanted_dollars": round(t.risk_wanted, 2),
            "risk_taken_dollars": round(t.risk_dollars, 2),
            "risk_pct_of_account": round(100 * t.risk_pct_used, 3),
            "share_of_the_days_budget": round(t.budget_share, 3),
            "halved_for_a_second_setup": t.second_setup_expected,
            "size_worked_out_from": t.size_basis,
            "size_clamped_by_buying_power": t.clamped,
            "targets": " | ".join(f"{p:.4f}" for p in t.targets),
            "targets_from": " | ".join(t.target_srcs),
            "how_many_targets": len(t.targets),
            "targets_price_reached": t.targets_filled,
            "target1": round(t.tp1, 4), "target1_from": t.tp1_src,
            "target2": round(t.tp2, 4), "target2_from": t.tp2_src,
            "exit_at": f"{t.exit_t:%H:%M}" if t.exit_t is not None else "",
            "exit_price": round(t.exit_price, 4),
            "what_happened": t.outcome,
            "pnl_dollars": round(t.pnl, 2),
            "pnl_pct_of_account": round(t.pct_of_account, 3),
            "reward_vs_risk": round(t.r_multiple, 3),
            "regime": t.regime,
            "cost_dollars": round(t.cost, 2),
            "filter_escalated": t.escalated,
        })
    d = pd.DataFrame(rows)
    d.to_csv(path, index=False)
    return d


def summarise(bot, trades, stand_downs, days, cfg) -> str:
    n = len(trades)
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    wr = 100.0 * len(wins) / n if n else 0.0
    aw = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
    al = -sum(t.pnl for t in losses) / len(losses) if losses else 0.0
    rr = (aw / al) if al else float("nan")
    weeks = sorted({(d - pd.Timedelta(days=d.weekday())).normalize() for d in days})
    months = sorted({(d.year, d.month) for d in days})
    per_month = n / len(months) if months else 0.0
    by_day: dict = {}
    for t in trades:
        by_day[t.day] = by_day.get(t.day, 0) + 1
    multi = sum(1 for v in by_day.values() if v > 1)
    busiest = max(by_day.values()) if by_day else 0
    lines = [
        f"sessions walked          {len(days)}",
        f"trades taken             {n}   ({100*len(by_day)/len(days):.0f}% of "
        f"sessions had at least one)" if days else "trades taken 0",
        f"days with more than one  {multi}   (his Day 9 ran three, Day 12 four)",
        f"most in one day          {busiest}",
        f"days stood aside         {len(stand_downs)}",
        f"trades per month         {per_month:.1f}   (his stated 7 to 15)",
        f"trades per week          {n/len(weeks):.1f}" if weeks else "",
        f"win rate                 {wr:.2f}%   (his stated 64.29%)",
        f"average win / average loss  1 : {rr:.3f}   (his stated 1 : 1.233)",
        f"average win              ${aw:,.0f}",
        f"average loss             ${al:,.0f}",
        f"net                      ${sum(t.pnl for t in trades):,.0f}",
        f"account                  ${cfg.account_start:,.0f} -> ${bot.account:,.0f}",
    ]
    lines.append("")
    lines.append("reward against risk, split by the regime the day opened in")
    lines.append("(raw volatility cancels under size = risk / stop distance; what")
    lines.append(" does not cancel is how far price runs before structure stops it)")
    by = {}
    for t in trades:
        by.setdefault(t.regime, []).append(t)
    for regime, ts in sorted(by.items()):
        w2 = [t for t in ts if t.pnl > 0]
        l2 = [t for t in ts if t.pnl <= 0]
        a = sum(t.pnl for t in w2) / len(w2) if w2 else 0.0
        b = -sum(t.pnl for t in l2) / len(l2) if l2 else 0.0
        r = f"1 : {a/b:.3f}" if b else "no losses"
        avg_r = sum(t.r_multiple for t in ts) / len(ts)
        lines.append(f"  {regime:<14} {len(ts):>3} trades   "
                     f"win rate {100*len(w2)/len(ts):5.1f}%   "
                     f"avg win/avg loss {r:<12} "
                     f"mean result {avg_r:+.3f}x what was risked")
    return "\n".join(x for x in lines if x != "")


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    weeks = 4
    for a in sys.argv[1:]:
        if a.startswith("--weeks"):
            weeks = int(a.split("=", 1)[1]) if "=" in a else weeks
    if len(args) >= 2:
        start, end = pd.Timestamp(args[0]), pd.Timestamp(args[1])
    else:
        d1 = to_et_frame(pd.read_parquet(f"{REPO}/data_alpaca_SPY_1m.parquet"))
        end = d1["t"].iloc[-1].normalize()
        start = end - pd.Timedelta(weeks=weeks)
    print(f"replaying {start:%Y-%m-%d} to {end:%Y-%m-%d}\n")
    cfg = Config()
    bot, trades, sd, days = run(start, end, cfg)
    print()
    print(summarise(bot, trades, sd, days, cfg))
    # a previous step's record is a record; each round writes its own file
    out = f"{REPO}/step453_trades.csv"
    to_csv(trades, out)
    print(f"\ntrades written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
