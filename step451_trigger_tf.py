"""
step451_trigger_tf.py — WHICH TIMEFRAME SHOULD THE CRYPTO ENTRY TRIGGER USE?

THE QUESTION, IN WALLACE'S WORDS
    "and who said crypto entries need 1 minute bars?"

Nobody did. `tjr_crypto.crypto_instrument` carries `trigger_minutes=1`, which
came across from the index instrument and was never derived for crypto. The
trader we copy uses a 1-minute trigger on the S&P because he works inside a
forty-minute window — a 5-minute pullback would eat most of it, so the last
step has to be finer than the pullback. CRYPTO HAS NO WINDOW. He does not
trade crypto and says nothing about it, so this is one of the few places
where measurement decides rather than his teaching.

It is also the exact mistake this project has a standing rule against: never
port a constant into a market it was not measured on. That rule was applied
to the stop buffer, the spread, the sweep age and the day boundary. It was
never applied to the timeframes.

WHAT IS HELD CONSTANT
    levels off the 1-hour and the 4-hour       (level_minutes)
    the 5-minute working chart                 (working_minutes)
    the 15-minute pool one timeframe up        (continuation/target1)
    the stop, the targets, the sizing, the pairs, the spread charged,
    the sweep ceiling, the day boundary, the losing-streak escalation.
ONLY `trigger_minutes` moves: 1, 3, 5, 15.

MANAGEMENT STAYS ON 1-MINUTE BARS AT EVERY SETTING, deliberately. Once a
position is open, the stop and the targets are checked on the finest bars we
have no matter what the trigger was. Otherwise a 15-minute trigger would also
be buying a coarser exit and the comparison would be measuring two changes at
once. At trigger_minutes=1 this is what the shipped code already does, so the
1-minute column here IS the shipped bot, unchanged — and `--selftest` proves
it reproduces `tjr_crypto.run_pair` trade for trade.

CAUSALITY
    Every higher timeframe is still truncated to its last COMPLETED candle by
    `tjr_bot.completed_before`. The trigger frame is resampled from 1-minute
    bars with `tjr_bot.resample_tf`, which stamps each bar with its own
    `close_t`, and a trigger bar is handed to the walk only at its close. A
    5-minute working bar closing inside a trigger bar is delivered at the
    first trigger close at or after it, never before it. `--selftest` runs a
    truncation probe: replaying with `stop_at` set to any point must produce
    exactly the decision the full walk had made by that point.

SAFETY
    Reads parquet, returns numbers. Places no orders, touches no venue, runs
    no git. Does not import or modify daemon.py, venue.py or tjr_bot.py's
    behaviour — `TriggerBot` subclasses `TjrBot` and overrides two methods.
"""

from __future__ import annotations

import json
import os
import statistics
import sys

import pandas as pd

import tjr_bot
import tjr_crypto
from tjr_bot import (Bar, Config, NewsCalendar, SymbolDay, TjrBot,
                     past_cutoff, session_start, too_early)

REPO = os.path.dirname(os.path.abspath(__file__))

TRIGGERS = (1, 3, 5, 15)


# ===================================================== THE TRIGGER FRAME
def trigger_frame(d1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """The entry chart, built from 1-minute bars.

    minutes == 1 returns the 1-minute frame itself rather than a resample of
    it, so the baseline column is not merely equivalent to the shipped bot but
    literally the same input.
    """
    if minutes == 1:
        return d1
    return tjr_bot.resample_tf(d1, minutes, 0)


# ========================================================= THE WALK
class TriggerBot(TjrBot):
    """tjr_bot's TjrBot with the entry trigger's timeframe made a variable.

    Two methods are overridden and NOTHING else changes:

    `run_day` — the shipped version hardcodes the trigger cadence in two
    places: `close_t = t + 1 minute`, which is how a 5-minute working bar
    finds the iteration it belongs to, and the assumption that one iteration
    of the trigger loop is also one step of position management. Both are
    generalised here. For trigger_minutes == 1 the generalisation collapses
    onto the original line for line.

    `_open` — the shipped version dates the target search at
    `entry bar start + 1 minute`, meaning the entry bar's CLOSE. Generalised
    to `+ trigger_minutes`, which is the same instant for a 1-minute trigger.
    """

    #: None = the shipped warm-up (the 90 minutes of bars before the day
    #: starts, written when the trigger was always the 1-minute chart, so it
    #: is 90 bars at 1m but only 6 bars at 15m). An integer re-warms the
    #: trigger tracker on that many BARS instead, so a coarse trigger is not
    #: judged on a cold tracker. Used only by the fairness check — the headline
    #: numbers are produced with the shipped warm-up.
    warm_trigger_bars: int | None = None

    def _rewarm(self, leg, trig_hist, day):
        n = self.warm_trigger_bars
        if not n:
            return
        open_t = session_start(day, self.cfg.instrument)
        hist = trig_hist[trig_hist["t"] < open_t].tail(n)
        leg.t1 = tjr_bot.TrendTracker()
        for r in hist.itertuples():
            leg.t1.update(Bar(r.t, r.open, r.high, r.low, r.close))

    def _open(self, leg, b1, day, risk_pct, d5_hist):
        trig = self.cfg.instrument.trigger_minutes
        shifted = b1._replace(t=b1.t + pd.Timedelta(minutes=trig - 1))
        tr = super()._open(leg, shifted, day, risk_pct, d5_hist)
        if tr is not None:
            tr.entry_t = b1.t              # the bar's START, as everywhere else
        return tr

    def run_day(self, data: dict, day: pd.Timestamp, stop_at=None) -> dict:
        """One UTC day, one pair, strictly forward.

        data: {symbol: {"5m": frame, "1m": frame, "trig": frame}}
        """
        cfg = self.cfg
        inst = cfg.instrument
        trig = pd.Timedelta(minutes=inst.trigger_minutes)
        work = pd.Timedelta(minutes=inst.working_minutes)

        self.refresh_escalation(day)
        derisk = self.news.derisks(day.date())
        risk_pct = cfg.risk_pct_derisk if derisk else cfg.risk_pct_normal

        syms = list(data.keys())
        legs = {s: SymbolDay(s, data[s]["5m"], data[s]["trig"], day, cfg,
                             self.news, self.escalated) for s in syms}
        for s in syms:
            self._rewarm(legs[s], data[s]["trig"], day)
        result = {"day": day, "escalated": self.escalated, "derisk": derisk,
                  "trade": None, "stand_down": {}, "notes": {},
                  "context": {s: legs[s].ctx for s in syms}}
        for s in syms:
            if legs[s].ctx.stand_down:
                result["stand_down"][s] = legs[s].ctx.stand_down
        live = [s for s in syms if legs[s].ctx.stand_down is None]
        if not live:
            return result

        open_t = session_start(day, inst)
        end_t = day + pd.Timedelta(hours=24 if inst.close_t is None
                                   else inst.close_t.hour)
        dT = {s: data[s]["trig"][(data[s]["trig"]["t"] >= open_t) &
                                 (data[s]["trig"]["t"] < end_t)] for s in syms}
        d5 = {s: data[s]["5m"][(data[s]["5m"]["t"] >= open_t) &
                               (data[s]["5m"]["t"] < end_t)] for s in syms}
        d1 = {s: data[s]["1m"][(data[s]["1m"]["t"] >= open_t) &
                               (data[s]["1m"]["t"] < end_t)] for s in syms}
        if any(len(dT[s]) == 0 for s in live):
            for s in live:
                result["stand_down"].setdefault(s, "no session bars — market shut")
            return result

        idxT = {s: {r.t: Bar(r.t, r.open, r.high, r.low, r.close)
                    for r in dT[s].itertuples()} for s in syms}
        # keyed by the working bar's CLOSE, which is the only moment it exists
        rows5 = {s: {r.t + work: Bar(r.t, r.open, r.high, r.low, r.close)
                     for r in d5[s].itertuples()} for s in syms}
        # management runs on the finest bars at every setting
        idx1 = {s: {r.t: Bar(r.t, r.open, r.high, r.low, r.close)
                    for r in d1[s].itertuples()} for s in syms}
        stamps = sorted({t for s in live for t in idxT[s]})
        stamps5 = {s: sorted(rows5[s]) for s in syms}
        cursor5 = {s: 0 for s in syms}

        trade = None
        for t in stamps:
            close_t = t + trig
            if stop_at is not None and close_t > stop_at:
                break

            # the cut-off: past_cutoff is False at every hour on a market with
            # no bell, and this line is kept only so the two paths stay the same
            if past_cutoff(t, inst):
                break

            # 1) every working bar that has CLOSED at or before this trigger
            #    bar's close and has not been delivered yet. On a 1-minute
            #    trigger this is exactly one bar every fifth iteration, which
            #    is what the shipped code does; on a 15-minute trigger it is
            #    the three 5-minute bars inside it, in order.
            fired5 = False
            for s in syms:
                while (cursor5[s] < len(stamps5[s]) and
                       stamps5[s][cursor5[s]] <= close_t):
                    legs[s].on_5m(rows5[s][stamps5[s][cursor5[s]]])
                    cursor5[s] += 1
                    fired5 = True
            if fired5:
                for s in live:
                    others = [legs[o].t5.state for o in syms if o != s]
                    legs[s].check_index_gate(others[0] if others else legs[s].t5.state)

            # 2) the trigger bar itself
            for s in live:
                bT = idxT[s].get(t)
                if bT is None:
                    continue
                if not legs[s].on_1m(bT) or trade is not None:
                    continue
                if too_early(t, inst):
                    legs[s].notes.append(
                        f"{t:%H:%M} the trigger landed inside the manipulation "
                        f"window — no entry")
                    continue
                trade = self._open(legs[s], bT, day, risk_pct, legs[s].d5_hist)
            if trade is not None:
                break

        # 3) management, on 1-minute bars, from the entry bar's close onward
        if trade is not None:
            entry_close = trade.entry_t + trig
            book = idx1[trade.symbol]
            for t1 in sorted(book):
                if t1 < entry_close:
                    continue
                if stop_at is not None and t1 + pd.Timedelta(minutes=1) > stop_at:
                    break
                self._manage(trade, book[t1])
                if trade.outcome:
                    break

        for s in syms:
            result["notes"][s] = legs[s].notes
            if legs[s].ctx.stand_down is None and trade is None:
                result["stand_down"].setdefault(s, self._why_no_trade(legs[s]))

        if trade is not None:
            if not trade.outcome:
                self._force_flat(trade, idx1[trade.symbol])
            self.account = trade.account_after
        wk = (day - pd.Timedelta(days=day.weekday())).normalize()
        self.week_pnl[wk] = self.week_pnl.get(wk, 0.0) + (trade.pnl if trade else 0.0)
        result["trade"] = trade
        return result


# ==================================================== ONE PAIR, ONE SETTING
def _slice(data: dict, day: pd.Timestamp, cfg: Config) -> dict:
    """The 95 days of history one replayed day is allowed to see.

    Sliced by position off the sorted timestamp column rather than by a
    boolean mask, because a mask over five years of 1-minute bars, taken once
    per replayed day, is the difference between minutes and hours. Identical
    output — `--selftest` compares it against the shipped path's masks.
    """
    lo = day - pd.Timedelta(days=cfg.dir_lookback_days + 5)
    hi = day + pd.Timedelta(days=1)
    out = {}
    for tf in ("5m", "1m", "trig"):
        d, ts = data[tf], data[f"_t_{tf}"]
        a = int(ts.searchsorted(lo.to_datetime64(), "left"))
        b = int(ts.searchsorted(hi.to_datetime64(), "left"))
        out[tf] = d.iloc[a:b].reset_index(drop=True)
    return out


def load_pair(pair: str, minutes: int, start=None, end=None) -> dict:
    d5 = pd.read_parquet(tjr_crypto.cache_name(pair, "5m"))
    d1 = pd.read_parquet(tjr_crypto.cache_name(pair, "1m"))
    if start is not None:
        lo = pd.Timestamp(start) - pd.Timedelta(days=120)
        d5, d1 = d5[d5["t"] >= lo], d1[d1["t"] >= lo]
    if end is not None:
        hi = pd.Timestamp(end) + pd.Timedelta(days=1)
        d5, d1 = d5[d5["t"] < hi], d1[d1["t"] < hi]
    d5 = d5.sort_values("t").reset_index(drop=True)
    d1 = d1.sort_values("t").reset_index(drop=True)
    out = {"5m": d5, "1m": d1, "trig": trigger_frame(d1, minutes)}
    for tf in ("5m", "1m", "trig"):
        out[f"_t_{tf}"] = out[tf]["t"].values
    return out


def run_pair(pair: str, minutes: int, start=None, end=None,
             data: dict | None = None, cfg: Config | None = None,
             warm_trigger_bars: int | None = None) -> dict:
    """Walk one pair at one trigger setting. Same shape as
    tjr_crypto.run_pair, plus the trigger the run used."""
    import dataclasses
    cfg = cfg or tjr_crypto.crypto_config(pair)
    cfg = dataclasses.replace(
        cfg, instrument=dataclasses.replace(cfg.instrument,
                                            trigger_minutes=minutes))
    data = data if data is not None else load_pair(pair, minutes, start, end)
    bot = TriggerBot(cfg, NewsCalendar(rules=False))
    bot.warm_trigger_bars = warm_trigger_bars
    t = data["1m"]["t"]
    if start is not None:
        t = t[t >= pd.Timestamp(start)]
    if end is not None:
        t = t[t < pd.Timestamp(end) + pd.Timedelta(days=1)]
    days = sorted(t.dt.normalize().unique())
    trades, skipped, reasons = [], 0, {}
    for day in days:
        day = pd.Timestamp(day)
        win = _slice(data, day, cfg)
        if len(win["1m"][(win["1m"]["t"] >= day) &
                         (win["1m"]["t"] < day + pd.Timedelta(days=1))]) == 0:
            skipped += 1
            continue
        res = bot.run_day({pair: win}, day)
        if res["trade"] is not None:
            trades.append(res["trade"])
        for why in res["stand_down"].values():
            why = tjr_crypto._reword(why)
            reasons[why] = reasons.get(why, 0) + 1
    return {"pair": pair, "trigger_minutes": minutes,
            "days": len(days) - skipped, "trades": trades, "reasons": reasons,
            "first_day": str(days[0])[:10] if days else None,
            "last_day": str(days[-1])[:10] if days else None}


# ================================================== WHAT GETS REPORTED
def trade_row(tr, pair: str) -> dict:
    """Everything the comparison needs out of one trade, with every
    percentage told what it is a percentage OF."""
    conf = tr.confirmed_at
    gap = None
    if conf is not None:
        gap = (pd.Timestamp(tr.entry_t) - pd.Timestamp(conf)).total_seconds() / 60.0
    return {
        "pair": pair,
        "entry_t": pd.Timestamp(tr.entry_t),
        "day": pd.Timestamp(tr.entry_t).normalize(),
        "direction": int(tr.direction),
        # the setup's identity, so two settings can be asked whether they took
        # THE SAME trade rather than merely a trade on the same day
        "level_price": float(tr.level_price),
        "level_tf": tr.level_tf,
        "swept_at": pd.Timestamp(tr.swept_at) if tr.swept_at is not None else None,
        "confirmed_at": (pd.Timestamp(conf) if conf is not None else None),
        "entry": float(tr.entry),
        "stop": float(tr.stop),
        # the number that decides it: how far the stop sits from the entry,
        # as a MOVE IN THE PRICE
        "stop_move_pct_of_price": 100.0 * abs(tr.entry - tr.stop) / tr.entry,
        "confirm_to_entry_min": gap,
        "r_multiple": float(tr.r_multiple),
        "pnl": float(tr.pnl),
        "exit_t": pd.Timestamp(tr.exit_t) if tr.exit_t is not None else None,
        "outcome": tr.outcome,
        "notional": float(tr.notional),
        "shares": float(tr.shares),
    }


def summarise(rows: list[dict], days: int, account_start: float,
              n_pairs: int) -> dict:
    if not rows:
        return {"trades": 0}
    d = pd.DataFrame(rows).sort_values("exit_t")
    wins = int((d["r_multiple"] > 0).sum())
    eq = d["pnl"].cumsum()
    peak = eq.cummax()
    dd = float((peak - eq).max())
    capital = account_start * n_pairs
    return {
        "trades": int(len(d)),
        "trades_per_day": round(len(d) / max(days, 1), 4),
        "win_rate_pct_of_trades": round(100.0 * wins / len(d), 1),
        "avg_r_multiple": round(float(d["r_multiple"].mean()), 3),
        "median_r_multiple": round(float(d["r_multiple"].median()), 3),
        "net_dollars": round(float(d["pnl"].sum()), 2),
        "net_pct_of_starting_capital": round(100.0 * d["pnl"].sum() / capital, 3),
        "max_drawdown_dollars": round(dd, 2),
        "max_drawdown_pct_of_starting_capital": round(100.0 * dd / capital, 3),
        "median_confirm_to_entry_min": (
            round(float(d["confirm_to_entry_min"].median()), 1)
            if d["confirm_to_entry_min"].notna().any() else None),
        "median_stop_move_pct_of_price": round(
            float(d["stop_move_pct_of_price"].median()), 4),
        "mean_stop_move_pct_of_price": round(
            float(d["stop_move_pct_of_price"].mean()), 4),
    }


def compare(pairs=None, start=None, end=None, triggers=TRIGGERS,
            verbose: bool = True) -> dict:
    pairs = list(pairs or tjr_crypto.PAIRS)
    out = {"window": {"start": start, "end": end}, "pairs": pairs, "runs": {}}
    for m in triggers:
        rows, days = [], 0
        spans = []
        for pair in pairs:
            try:
                r = run_pair(pair, m, start, end)
            except FileNotFoundError:
                if verbose:
                    print(f"    {pair}: no cached bars")
                continue
            days = max(days, r["days"])
            spans.append((r["first_day"], r["last_day"]))
            rows += [trade_row(tr, pair) for tr in r["trades"]]
        s = summarise(rows, days, 100_000.0, len(pairs))
        s["span"] = (min(x[0] for x in spans) if spans else None,
                     max(x[1] for x in spans) if spans else None)
        s["days_longest_pair"] = days
        out["runs"][m] = {"summary": s,
                          "entries": sorted({(r["pair"], str(r["entry_t"]))
                                             for r in rows}),
                          "rows": rows}
        if verbose:
            print(f"  trigger {m:>2}m: {s.get('trades', 0)} trades, "
                  f"avg {s.get('avg_r_multiple')}R, stop "
                  f"{s.get('median_stop_move_pct_of_price')}% of price")
    return out


def population_diff(out: dict, base: int = 1) -> dict:
    """Changing the trigger changes WHICH trades happen, not just how they are
    sized. This measures how much, so the comparison is never quietly treated
    as a clean subset when it is not."""
    runs = out["runs"]
    if base not in runs:
        return {}
    b = set(tuple(x) for x in runs[base]["entries"])
    d = {}
    for m, r in runs.items():
        e = set(tuple(x) for x in r["entries"])
        shared_days = {(p, t[:10]) for p, t in e} & {(p, t[:10]) for p, t in b}
        d[m] = {
            "trades": len(e),
            "not_in_base": len(e - b),
            "not_in_base_pct_of_this_run": round(100.0 * len(e - b) / max(len(e), 1), 1),
            "base_trades_missing_here": len(b - e),
            "same_pair_same_day_as_a_base_trade": len(shared_days),
        }
    return d


# ========================================================== SELF TEST
def selftest(pair: str = "BTC/USD", start="2026-06-01", end="2026-06-30") -> bool:
    """Two things must hold before any number here is worth reading.

    1. AT trigger_minutes == 1 THIS IS THE SHIPPED BOT. Same trades, same
       entries, same stops, same outcomes as tjr_crypto.run_pair.
    2. CAUSALITY. Replaying a day with `stop_at` set must never produce a
       decision the full walk had not already made by that instant.
    """
    ok = True
    print("selftest 1: trigger=1 reproduces tjr_crypto.run_pair")
    a = tjr_crypto.run_pair(pair, start, end)
    b = run_pair(pair, 1, start, end)
    ka = [(str(t.entry_t), round(t.entry, 6), round(t.stop, 6), t.outcome,
           round(t.pnl, 6)) for t in a["trades"]]
    kb = [(str(t.entry_t), round(t.entry, 6), round(t.stop, 6), t.outcome,
           round(t.pnl, 6)) for t in b["trades"]]
    print(f"  shipped: {len(ka)} trades   step451@1m: {len(kb)} trades")
    if ka != kb:
        ok = False
        print("  MISMATCH")
        for x, y in zip(ka, kb):
            if x != y:
                print(f"    {x}\n    {y}")
        for x in set(map(str, ka)) ^ set(map(str, kb)):
            print(f"    only one side: {x}")
    else:
        print("  identical")

    print("selftest 2: truncation — a stopped walk decides nothing extra")
    import dataclasses
    for m in TRIGGERS:
        data = load_pair(pair, m, start, end)
        cfg = tjr_crypto.crypto_config(pair)
        cfg = dataclasses.replace(
            cfg, instrument=dataclasses.replace(cfg.instrument,
                                                trigger_minutes=m))
        bad = 0
        days = sorted(pd.Series(data["1m"]["t"])[
            data["1m"]["t"] >= pd.Timestamp(start)].dt.normalize().unique())[:12]
        for day in days:
            day = pd.Timestamp(day)
            win = _slice(data, day, cfg)
            full = TriggerBot(cfg, NewsCalendar(rules=False)).run_day(
                {pair: win}, day)
            tr = full["trade"]
            for hh in (6, 12, 18):
                cut = day + pd.Timedelta(hours=hh)
                part = TriggerBot(cfg, NewsCalendar(rules=False)).run_day(
                    {pair: win}, day, stop_at=cut)
                p = part["trade"]
                if p is None:
                    continue
                if tr is None or pd.Timestamp(p.entry_t) != pd.Timestamp(tr.entry_t) \
                        or round(p.entry, 8) != round(tr.entry, 8) \
                        or round(p.stop, 8) != round(tr.stop, 8):
                    bad += 1
                    print(f"  {m}m {day:%Y-%m-%d} @{hh}h: truncated walk "
                          f"invented a different entry")
        print(f"  trigger {m:>2}m: {len(days)} days probed at 3 cut points — "
              f"{'clean' if not bad else str(bad) + ' FAILURES'}")
        ok = ok and not bad
    return ok


def main(argv):
    if "--selftest" in argv:
        ok = selftest()
        print("\nSELFTEST", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    start = end = None
    pairs = None
    for a in argv[1:]:
        if a.startswith("--start="):
            start = a.split("=", 1)[1]
        elif a.startswith("--end="):
            end = a.split("=", 1)[1]
        elif a.startswith("--pairs="):
            pairs = a.split("=", 1)[1].split(",")
    out = compare(pairs, start, end)
    print(json.dumps({"summary": {m: r["summary"] for m, r in out["runs"].items()},
                      "populations": population_diff(out)},
                     indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
