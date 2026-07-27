"""
step440_runway.py — HOW MUCH FURTHER DID PRICE RUN AFTER WE GOT OUT?

THE QUESTION
    Our winners are the same size as our losers. His are bigger. If the moves
    genuinely die where we exit, the exit is fine and the problem is
    elsewhere. If price keeps running after we leave, we are leaving money on
    the table and the exit is the leak.

WHAT THIS MEASURES, PER TRADE
    Replay the same session forward from the moment we exited, on the same
    1-minute bars, and record how much further price travelled in the
    trade's favour before it would have hit the level that proves the idea
    wrong (the original stop). Reported as a price move in percent, and as a
    multiple of what was risked per share.

    Also: the counterfactual results of holding the same trade under
    different exit rules, so the cost of each exit defect is in dollars per
    dollar risked rather than in adjectives.

THIS FILE READS BARS AFTER THE EXIT ON PURPOSE.
    It is a measurement, not a rule. Nothing here feeds a decision. The bot
    itself is untouched by this file and its truncation tests still hold.

RESEARCH ONLY. No orders. Nothing here can reach a broker.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
import tjr_bot
import tjr_replay
from tjr_bot import Config

REPO = "/Users/wallacechen/cryptobot"
START = pd.Timestamp("2026-01-01")
END = pd.Timestamp("2026-07-24")


def session_1m(data: dict, symbol: str, day: pd.Timestamp) -> pd.DataFrame:
    """The 1-minute bars of one regular session, 09:30 up to 16:00."""
    f = data[symbol]["1m"]
    lo = day + pd.Timedelta(hours=9, minutes=30)
    hi = day + pd.Timedelta(hours=16)
    return f[(f["t"] >= lo) & (f["t"] < hi)].reset_index(drop=True)


def favourable(px: float, entry: float, d: int, rps: float) -> float:
    """How far in our favour, as a multiple of what was risked per share."""
    return d * (px - entry) / rps


def run_forward(bars: pd.DataFrame, tr, from_t, stop: float) -> dict:
    """Walk from `from_t` (exclusive) to the end of the session.

    Returns the best price reached in the trade's favour before `stop` was
    touched, and whether the stop was touched at all. Within a single bar we
    never take the good side of an ambiguous bar: if the bar's range contains
    both the stop and a new best, the stop is treated as hit first.
    """
    d = tr.direction
    after = bars[bars["t"] > from_t]
    best = None
    stop_hit = False
    stop_t = None
    for r in after.itertuples():
        touched = (r.low <= stop) if d > 0 else (r.high >= stop)
        if touched:
            stop_hit, stop_t = True, r.t
            break
        px = r.high if d > 0 else r.low
        if best is None or (px > best if d > 0 else px < best):
            best = px
    return {"best": best, "stop_hit": stop_hit, "stop_t": stop_t,
            "last_close": after["close"].iloc[-1] if len(after) else None,
            "last_t": after["t"].iloc[-1] if len(after) else None}


# ------------------------------------------------------------ counterfactuals
def sim(bars: pd.DataFrame, tr, plan: str, targets: list[float],
        fracs: list[float], move_be: bool, flat_t=None) -> dict:
    """Replay ONE trade from its entry under a stated exit rule.

    targets/fracs: price levels and the fraction of the ORIGINAL position
    taken off at each. Whatever is left runs to the flat time or the stop.
    move_be:       after the first target fills, the stop goes to the entry.
    Same bar-order rule as the bot: the stop is checked before the target.
    """
    d, entry, rps = tr.direction, tr.entry, tr.risk_per_share
    stop = tr.stop
    open_frac, realised_r, filled = 1.0, 0.0, 0
    exit_t, exit_kind = None, ""
    walk = bars[bars["t"] >= tr.entry_t]
    for r in walk.itertuples():
        if (r.low <= stop) if d > 0 else (r.high >= stop):
            realised_r += open_frac * favourable(stop, entry, d, rps)
            open_frac, exit_t = 0.0, r.t
            exit_kind = "stopped at break even" if filled and move_be else "stopped out"
            break
        while filled < len(targets):
            tp = targets[filled]
            if (r.high >= tp) if d > 0 else (r.low <= tp):
                part = min(fracs[filled], open_frac)
                realised_r += part * favourable(tp, entry, d, rps)
                open_frac -= part
                filled += 1
                if move_be:
                    stop = entry
                continue
            break
        if open_frac <= 1e-9:
            exit_t, exit_kind = r.t, f"all {filled} targets reached"
            break
        if flat_t is not None and r.t.time() >= flat_t:
            realised_r += open_frac * favourable(r.close, entry, d, rps)
            open_frac, exit_t, exit_kind = 0.0, r.t, "flat by the close"
            break
    if open_frac > 1e-9:
        last = walk.iloc[-1]
        realised_r += open_frac * favourable(last["close"], entry, d, rps)
        exit_t, exit_kind = last["t"], "flat, out of bars"
    cost_r = (tjr_bot.US_INDEX_ETF.round_trip_cost_pct * tr.shares * entry
              / tr.risk_dollars) if tr.risk_dollars else 0.0
    return {"plan": plan, "gross_r": realised_r, "net_r": realised_r - cost_r,
            "exit_t": exit_t, "kind": exit_kind}


def main() -> int:
    cfg = Config()
    print(f"replaying {START:%Y-%m-%d} to {END:%Y-%m-%d} to rebuild the trades\n")
    bot, trades, sd, days = tjr_replay.run(START, END, cfg, verbose=False)
    data = {s: tjr_replay.load(s) for s in tjr_replay.SYMBOLS}
    print(f"{len(trades)} trades over {len(days)} sessions\n")

    rows = []
    for tr in trades:
        bars = session_1m(data, tr.symbol, tr.day)
        d, rps = tr.direction, tr.risk_per_share
        won = tr.pnl > 0

        # what we captured, and the best the trade ever showed before we left
        upto = bars[(bars["t"] >= tr.entry_t) & (bars["t"] <= tr.exit_t)]
        mfe_before = max(favourable(r.high if d > 0 else r.low, tr.entry, d, rps)
                         for r in upto.itertuples()) if len(upto) else 0.0

        # the runway: from the exit forward, before the original stop
        fwd = run_forward(bars, tr, tr.exit_t, tr.stop)
        if fwd["best"] is None:
            further_pct, further_r, best_after_r = 0.0, 0.0, None
        else:
            further_pct = 100.0 * d * (fwd["best"] - tr.exit_price) / tr.exit_price
            further_r = d * (fwd["best"] - tr.exit_price) / rps
            best_after_r = favourable(fwd["best"], tr.entry, d, rps)

        rows.append({
            "date": f"{tr.day:%Y-%m-%d}", "symbol": tr.symbol,
            "side": "long" if d > 0 else "short",
            "what_happened": tr.outcome,
            "won": won,
            "we_made_per_dollar_risked": round(tr.r_multiple, 3),
            "best_it_showed_before_we_left": round(mfe_before, 3),
            "exit_at": f"{tr.exit_t:%H:%M}",
            "further_move_pct_of_price": round(further_pct, 4),
            "further_move_per_dollar_risked": round(further_r, 3),
            "best_after_exit_per_dollar_risked":
                None if best_after_r is None else round(best_after_r, 3),
            "orig_stop_touched_after": fwd["stop_hit"],
            "minutes_held": int((tr.exit_t - tr.entry_t).total_seconds() // 60),
        })

    out = pd.DataFrame(rows)
    out.to_csv(f"{REPO}/step440_runway.csv", index=False)

    def desc(x):
        x = np.array(x, dtype=float)
        if len(x) == 0:
            return "  (none)"
        q = np.percentile(x, [10, 25, 50, 75, 90])
        return (f"  n={len(x):<3} median {np.median(x):+.3f}   mean {x.mean():+.3f}\n"
                f"       10th {q[0]:+.3f}  25th {q[1]:+.3f}  50th {q[2]:+.3f}  "
                f"75th {q[3]:+.3f}  90th {q[4]:+.3f}")

    print("=" * 74)
    print("HOW MUCH FURTHER DID PRICE RUN AFTER WE GOT OUT")
    print("(measured from the exit price to the best price reached before the")
    print(" original stop was touched, same session, 1-minute bars)")
    print("=" * 74)
    for label, sel in (("ALL TRADES", out),
                       ("WINNERS", out[out["won"]]),
                       ("LOSERS", out[~out["won"]])):
        print(f"\n{label}")
        print("  further move as a PRICE MOVE, percent of price")
        print(desc(sel["further_move_pct_of_price"]))
        print("  further move as a multiple of what was risked per share")
        print(desc(sel["further_move_per_dollar_risked"]))
    print()
    print(out[["date", "symbol", "side", "what_happened", "exit_at",
               "we_made_per_dollar_risked", "best_it_showed_before_we_left",
               "further_move_pct_of_price", "further_move_per_dollar_risked",
               "orig_stop_touched_after"]].to_string(index=False))

    print("\n" + "=" * 74)
    print("WHAT DIFFERENT EXIT RULES WOULD HAVE PAID, SAME ENTRIES, SAME STOPS")
    print("(net of the same measured cost; 'per $1 risked' throughout)")
    print("=" * 74)
    flat = tjr_bot.FLAT_T
    plans = []
    for tr in trades:
        bars = session_1m(data, tr.symbol, tr.day)
        tg = list(tr.targets)
        fr = tjr_bot.target_fractions(len(tg), cfg)
        plans.append({
            "date": f"{tr.day:%Y-%m-%d}", "symbol": tr.symbol,
            "as_built": sim(bars, tr, "as built: half at target 1, the rest "
                            "spread over the targets after it, break even "
                            "from the first fill", tg, fr, True, flat),
            "no_be": sim(bars, tr, "same scale-out, but the stop STAYS at the "
                         "original level", tg, fr, False, flat),
            "hold_all": sim(bars, tr, "no partials at all, original stop, out at "
                            "the close", [], [], False, flat),
            "first_only": sim(bars, tr, "half at target 1, break even, the whole "
                              "runner out at target 2", tg[:2],
                              [0.5, 0.5][:len(tg[:2])], True, flat),
        })
    for key in ("as_built", "no_be", "hold_all", "first_only"):
        rs = [p[key]["net_r"] for p in plans]
        wins = [r for r in rs if r > 0]
        losses = [r for r in rs if r <= 0]
        aw = np.mean(wins) if wins else 0.0
        al = -np.mean(losses) if losses else 0.0
        print(f"\n{plans[0][key]['plan']}")
        print(f"  right {100*len(wins)/len(rs):.0f} out of 100     "
              f"makes ${aw/al if al else float('nan'):.2f} for every $1 risked     "
              f"mean result {np.mean(rs):+.3f} per $1 risked     "
              f"total {np.sum(rs):+.2f}")

    pd.DataFrame([{"date": p["date"], "symbol": p["symbol"],
                   **{k: round(p[k]["net_r"], 3)
                      for k in ("as_built", "no_be", "hold_all", "first_only")}}
                  for p in plans]).to_csv(f"{REPO}/step440_exit_plans.csv", index=False)
    print(f"\nwritten: {REPO}/step440_runway.csv, {REPO}/step440_exit_plans.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
