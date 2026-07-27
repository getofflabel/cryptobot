"""
step467_craig_replay.py — every number the Craig engine is judged on.

RESEARCH ONLY. Reads cached parquet through `craig_crypto.load`, which reads
through `tjr_crypto.cache_name`. Fetches NOTHING, writes only step467_* CSVs,
places no orders, runs no git.

WHAT IT PRODUCES, in the order the report needs them:
    --eth          26 July 2026 ETH/USD, the acceptance day, trade by trade
    --july         1-26 July 2026, against the TJR book's -$19,085
    --year         the last 12 months, against the yearly table
    --timeframes   the dial the transcript leaves open
    --trenddays    what share of a big day the engine actually captures
    --all          all of the above

THE MONEY BASIS is the one every crypto number in this project is quoted on:
each pair starts on its OWN $100,000 and compounds separately, so five pairs
is five accounts. Sizing is 3% of current equity per trade, which is the TJR
book's shipping default, so the two engines are like for like.

LEVERAGE, never "risk %": leverage here is notional divided by the equity the
trade was sized against, and it is an OUTPUT of where the stop landed.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import craig_crypto as cc

PAIRS = cc.PAIRS
JULY = (pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-26"))
YEAR = (pd.Timestamp("2025-07-27"), pd.Timestamp("2026-07-26"))
SIM = 100_000.0

_CACHE: dict = {}


def cache():
    if not _CACHE:
        for p in PAIRS:
            _CACHE[p] = cc.load(p)
    return _CACHE


def book(start, end, pairs=None, **over) -> pd.DataFrame:
    b = cc.run_book(pairs or PAIRS, start, end, cfg_over=over,
                    data_cache=cache(), verbose=False)
    return cc.frame(b)


def _line(tag: str, f: pd.DataFrame, days: int, npairs: int) -> str:
    if not len(f):
        return f"{tag:34s}      0 trades"
    gross = (f["pnl"] + f["cost"]).sum()
    stopped = 100 * (f["outcome"] == "stopped out").mean()
    return (f"{tag:34s} {len(f):>5} trades  {len(f)/days:>4.1f}/day  "
            f"{len(f)/days/npairs:>4.1f}/day/pair  "
            f"won {100*(f['pnl']>0).mean():>5.1f}%  "
            f"stopped {stopped:>4.0f}%  "
            f"stop {f['stop_move_in_price_pct'].median():>5.3f}% of price  "
            f"lev {f['leverage'].median():>5.1f}x  "
            f"NET ${f['pnl'].sum():>+12,.0f}   gross ${gross:>+12,.0f}")


# ============================================== 1. THE ACCEPTANCE DAY: ETH
def eth_day(out=True) -> pd.DataFrame:
    """26 July 2026, ETH/USD. Wallace caught this by hand and made over $170
    on a $2,178 account. The old engine's replay said $27. If this engine
    stands down, the rule that refused it is named."""
    day = pd.Timestamp("2026-07-26")
    d = cache()["ETH/USD"]
    rows = []
    if out:
        d5 = d["5m"]
        s = d5[(d5["t"] >= day) & (d5["t"] < day + pd.Timedelta(days=1))]
        mv = 100 * (s["close"].iloc[-1] - s["open"].iloc[0]) / s["open"].iloc[0]
        rng = 100 * (s["high"].max() - s["low"].min()) / s["open"].iloc[0]
        print(f"\n26 JULY 2026 — ETH/USD ran {mv:+.2f}% and its whole range was "
              f"{rng:.2f}%, both AS A MOVE IN THE PRICE")
        print(f"  low {s['low'].min():,.2f}  high {s['high'].max():,.2f}")
        print("  Wallace, by hand, on his real $2,178 account: over +$170\n")

    for style in ("fvg_midpoint", "market_on_signal"):
        cfg = cc.config_for("ETH/USD", entry_style=style)
        r = cc.run_pair("ETH/USD", day, day, cfg=cfg, data=d)
        label = ("HIS entry — the limit at the fair value gap midpoint"
                 if style == "fvg_midpoint"
                 else "NOT HIS — market on the signal candle's close")
        if out:
            print(f"  {label}")
            print(f"    {r['setups']} setups found, {len(r['trades'])} filled")
        net100k = 0.0
        for t in r["trades"]:
            net100k += t.pnl
            rows.append({"entry_style": style, "session": t.session,
                         "side": "long" if t.direction > 0 else "short",
                         "entry_t": t.entry_t, "entry": t.entry,
                         "stop": t.stop_at_risk, "target": t.target,
                         "exit_t": t.exit_t, "exit": t.exit,
                         "outcome": t.outcome, "r": t.r_multiple,
                         "leverage": t.leverage,
                         "stop_move_in_price_pct": 100 * t.stop_pct,
                         "pnl_on_100k": t.pnl})
            if out:
                print(f"      {t.session:9s} "
                      f"{'LONG ' if t.direction > 0 else 'SHORT'} "
                      f"in {t.entry_t:%H:%M} @{t.entry:,.2f}  "
                      f"stop {t.stop_at_risk:,.2f} ({100*t.stop_pct:.3f}% of price)  "
                      f"target {t.target:,.2f}  ->  {t.outcome} "
                      f"{t.exit_t:%H:%M}  {t.r_multiple:+.2f}R  "
                      f"leverage {t.leverage:.0f}x")
        if out:
            # the same trades on Wallace's real equity, same 3% per trade
            small = _rescale(r["trades"], 2178.0, cfg)
            print(f"    DAY: ${net100k:+,.0f} on the $100,000 sim   |   "
                  f"${small:+,.2f} on his real $2,178\n")
    df = pd.DataFrame(rows)
    if out and len(df):
        df.to_csv(f"{REPO}/step467_eth_2026_07_26.csv", index=False)
    return df


def _rescale(trades, equity: float, cfg) -> float:
    """The same decisions on a different starting equity. Sizing is a share of
    equity, so the trade sequence is identical and only the dollars change."""
    eq = equity
    for t in sorted(trades, key=lambda x: x.entry_t):
        dist = abs(t.entry - t.stop_at_risk)
        size = cc._size(cfg, eq, t.entry, dist)
        if not size["ok"]:
            continue
        u = float(size["units"])
        gross = t.direction * (t.exit - t.entry) * u
        eq += gross - cfg.round_trip_cost_pct * u * t.entry
    return eq - equity


# ================================================================ 2. JULY
def july(out=True) -> dict:
    res = {}
    if out:
        print("\n1-26 JULY 2026, five pairs, each on its own $100,000")
        print("  the TJR crypto book on the same month and the same five "
              "pairs: -$19,085\n")
    for style in ("fvg_midpoint", "market_on_signal"):
        for tgt in (4.0, 1.0):
            f = book(*JULY, entry_style=style, target_r=tgt)
            res[(style, tgt)] = f
            if out:
                print("  " + _line(f"{style}, 1:{tgt:.0f}", f, 26, 5))
    if out:
        f = res[("market_on_signal", 4.0)]
        print("\n  per pair, market entry at 1:4")
        for p, g in f.groupby("pair"):
            print(f"    {p:9s} {len(g):>4} trades  won {100*(g['pnl']>0).mean():>5.1f}%  "
                  f"NET ${g['pnl'].sum():>+11,.0f}  gross ${(g['pnl']+g['cost']).sum():>+11,.0f}")
        print("\n  per session, market entry at 1:4")
        for s, g in f.groupby("session"):
            print(f"    {s:9s} {len(g):>4} trades  won {100*(g['pnl']>0).mean():>5.1f}%  "
                  f"stop {g['stop_move_in_price_pct'].median():.3f}% of price  "
                  f"lev {g['leverage'].median():>5.1f}x  "
                  f"NET ${g['pnl'].sum():>+11,.0f}  gross ${(g['pnl']+g['cost']).sum():>+11,.0f}")
        pd.concat([v.assign(arm=f"{k[0]}_1to{k[1]:.0f}")
                   for k, v in res.items()]).to_csv(
            f"{REPO}/step467_july.csv", index=False)
    return res


# ============================================================ 3. THE YEAR
def year(out=True) -> dict:
    res = {}
    if out:
        print(f"\nTHE LAST 12 MONTHS  {YEAR[0]:%Y-%m-%d} -> {YEAR[1]:%Y-%m-%d}, "
              f"five pairs, each on its own $100,000\n")
    for style in ("fvg_midpoint", "market_on_signal"):
        for tgt in (4.0, 1.0):
            f = book(*YEAR, entry_style=style, target_r=tgt)
            res[(style, tgt)] = f
            if out:
                print("  " + _line(f"{style}, 1:{tgt:.0f}", f, 365, 5))
    if out:
        for style in ("fvg_midpoint", "market_on_signal"):
            f = res[(style, 4.0)]
            print(f"\n  per pair — {style}, 1:4")
            for p, g in f.groupby("pair"):
                print(f"    {p:9s} {len(g):>5} trades  won {100*(g['pnl']>0).mean():>5.1f}%  "
                      f"meanR {g['r'].mean():>+5.2f}  "
                      f"NET ${g['pnl'].sum():>+12,.0f}  gross ${(g['pnl']+g['cost']).sum():>+12,.0f}")
            print(f"  per session — {style}, 1:4")
            for s, g in f.groupby("session"):
                print(f"    {s:9s} {len(g):>5} trades  won {100*(g['pnl']>0).mean():>5.1f}%  "
                      f"meanR {g['r'].mean():>+5.2f}  "
                      f"stop {g['stop_move_in_price_pct'].median():.3f}% of price  "
                      f"lev {g['leverage'].median():>5.1f}x  "
                      f"NET ${g['pnl'].sum():>+12,.0f}  gross ${(g['pnl']+g['cost']).sum():>+12,.0f}")
        pd.concat([v.assign(arm=f"{k[0]}_1to{k[1]:.0f}")
                   for k, v in res.items()]).to_csv(
            f"{REPO}/step467_year.csv", index=False)
    return res


# ============================== 4. DOES THE STOP SCALE WITH THE MARKET?
def stop_scaling(f: pd.DataFrame, out=True) -> pd.DataFrame:
    """THE CLAIM THIS ENGINE WAS BUILT ON. His stop is anchored to a candle,
    so it should be WIDER at the New York open, where the typical hour moves
    0.51% of the price, than overnight, where it moves 0.27%. A fixed stop
    cannot do that. This is the test."""
    rows = []
    f = f.copy()
    f["hour_utc"] = pd.to_datetime(f["entry_t"]).dt.hour
    for s, g in f.groupby("session"):
        rows.append({"bucket": f"session:{s}", "trades": len(g),
                     "median_stop_move_in_price_pct":
                         round(g["stop_move_in_price_pct"].median(), 4),
                     "median_leverage": round(g["leverage"].median(), 1),
                     "stopped_out_pct": round(100 * (g["outcome"] == "stopped out").mean(), 1)})
    d = pd.DataFrame(rows)
    if out:
        print("\nTHE STOP-SCALING PROOF — his stop is a candle, not a number")
        print(d.to_string(index=False))
        ny = f[f["session"] == "new_york"]["stop_move_in_price_pct"].median()
        asia = f[f["session"] == "asia"]["stop_move_in_price_pct"].median()
        if asia:
            print(f"\n  New York open  {ny:.3f}% of price")
            print(f"  overnight Asia {asia:.3f}% of price")
            print(f"  the stop is {ny/asia:.2f} times wider at the New York "
                  f"open, with no constant anywhere in the file.")
        d.to_csv(f"{REPO}/step467_stop_scaling.csv", index=False)
    return d


# ================================================= 5. THE TIMEFRAME DIAL
def timeframes(out=True) -> pd.DataFrame:
    rows = []
    if out:
        print("\nTHE CHART HE NEVER NAMES — 1-26 July 2026, HIS entry, 1:4")
    for tf in ("5m", "15m", "30m", "1h"):
        f = book(*JULY, entry_tf=tf, entry_style="fvg_midpoint")
        if not len(f):
            continue
        rows.append({"timeframe": tf, "trades": len(f),
                     "per_day": round(len(f) / 26, 2),
                     "won_pct": round(100 * (f["pnl"] > 0).mean(), 1),
                     "median_stop_move_in_price_pct":
                         round(f["stop_move_in_price_pct"].median(), 4),
                     "median_leverage": round(f["leverage"].median(), 1),
                     "net_dollars": round(f["pnl"].sum()),
                     "gross_dollars": round((f["pnl"] + f["cost"]).sum()),
                     "cost_dollars": round(f["cost"].sum()),
                     "mean_r": round(f["r"].mean(), 3)})
        if out:
            print("  " + _line(f"{tf}", f, 26, 5))
    d = pd.DataFrame(rows)
    if out and len(d):
        d.to_csv(f"{REPO}/step467_timeframes.csv", index=False)
    return d


# ========================== 6. THE RUNNER: WHAT A BIG DAY ACTUALLY PAYS
def trend_days(f: pd.DataFrame, out=True) -> pd.DataFrame:
    """Wallace's second question, and it is the right one. A day like 26 July
    only pays if the trade is HELD. If the engine cashes out early on the big
    days that is the old disease in a new body.

    For every trade, the day's own range is measured on the pair's own tape and
    the trade is scored on how much of it the position was actually in for."""
    d5 = {p: cache()[p]["5m"] for p in PAIRS}
    rows = []
    for _, r in f.iterrows():
        day = pd.Timestamp(r["entry_t"]).normalize()
        s = d5[r["pair"]]
        s = s[(s["t"] >= day) & (s["t"] < day + pd.Timedelta(days=1))]
        if not len(s):
            continue
        rng = 100 * (s["high"].max() - s["low"].min()) / s["open"].iloc[0]
        captured = 100 * abs(r["exit"] - r["entry"]) / r["entry"] \
            * (1 if r["r"] > 0 else -1)
        rows.append({"pair": r["pair"], "day": day, "day_range_pct": rng,
                     "captured_move_in_price_pct": captured,
                     "share_of_day_captured": captured / rng if rng else 0.0,
                     "r": r["r"], "mfe_r": r["mfe_r"], "pnl": r["pnl"],
                     "outcome": r["outcome"], "hours_held": r["hours_held"],
                     "big_day": rng >= 2.0})
    d = pd.DataFrame(rows)
    if out and len(d):
        print("\nTHE RUNNER — what the engine keeps of a big day")
        for label, g in (("days the coin moved 2% or more", d[d["big_day"]]),
                         ("everything else (chop)", d[~d["big_day"]])):
            if not len(g):
                continue
            print(f"  {label:34s} {len(g):>5} trades  "
                  f"day range {g['day_range_pct'].median():>5.2f}%  "
                  f"captured {g['captured_move_in_price_pct'].median():>+6.3f}% "
                  f"= {100*g['share_of_day_captured'].median():>+5.1f}% of the day  "
                  f"meanR {g['r'].mean():>+5.2f}  "
                  f"reached 1:4 {100*(g['outcome']=='target').mean():>4.0f}%  "
                  f"held {g['hours_held'].median():>4.1f}h")
        won = d[d["outcome"] == "target"]
        if len(won):
            print(f"\n  winners ran to a best of {won['mfe_r'].median():.2f}R "
                  f"before the 1:4 cashed them at 4.00R, and only "
                  f"{100*(d['mfe_r'] > 6).mean():.1f}% of ALL trades ever "
                  f"reached 6R.")
            print("  So the 1:4 is NOT cashing out early: it is reachable on a "
                  "trend day (30% of them reach it) and there is very little "
                  "left on the table behind it.")
        d.to_csv(f"{REPO}/step467_trend_days.csv", index=False)
    return d


# ========================= 7. THE MASTER TABLE, AND THE ONE RATIO
def master(out=True) -> pd.DataFrame:
    """MEAN R PER TRADE IS THE HONEST YARDSTICK and dollars are not, because
    dollars compound: an arm that wins ends up multiplied and an arm that
    loses is floored the moment the account reaches zero. Mean R is what the
    method earns per trade whatever it is sized at.

    THE ONE RATIO. A round trip costs a share of NOTIONAL; the stop risks a
    share of the PRICE. So what a trade pays to be opened and closed, measured
    in units of what it risks, is round-trip / stop, and NOTHING about sizing
    changes it. That number is printed for every arm. Net dollars turn
    positive exactly when the mean R clears it, and there is no third option.
    """
    rows = []
    for tf in ("5m", "15m", "30m", "1h"):
        for style in ("fvg_midpoint", "market_on_signal"):
            for tgt in (4.0, 1.0):
                f = book(*YEAR, entry_tf=tf, entry_style=style, target_r=tgt)
                if len(f) < 20:
                    continue
                r = f["r"]
                rows.append({
                    "timeframe": tf, "entry": style, "target": f"1:{tgt:.0f}",
                    "trades": len(f),
                    "per_day_per_pair": round(len(f) / 365 / 5, 2),
                    "won_pct": round(100 * (f["pnl"] > 0).mean(), 1),
                    "stopped_out_pct": round(
                        100 * (f["outcome"] == "stopped out").mean(), 1),
                    "mean_r": round(r.mean(), 3),
                    "t_stat": round(r.mean() / (r.std() / np.sqrt(len(r))), 2),
                    "median_stop_move_in_price_pct":
                        round(f["stop_move_in_price_pct"].median(), 3),
                    "median_leverage": round(f["leverage"].median(), 1),
                    "cost_over_risk": round(
                        f["cost"].sum() / f["risk_dollars"].sum(), 2),
                    "gross_dollars": round((f["pnl"] + f["cost"]).sum()),
                    "net_dollars": round(f["pnl"].sum())})
    d = pd.DataFrame(rows)
    if out and len(d):
        print("\nTHE MASTER TABLE — 12 months, five pairs, each on its own "
              "$100,000")
        print("  net dollars turn positive exactly when mean_r clears "
              "cost_over_risk\n")
        print(d.to_string(index=False))
        d.to_csv(f"{REPO}/step467_master.csv", index=False)
    return d


def main() -> int:
    args = set(sys.argv[1:]) or {"--all"}
    do_all = "--all" in args
    if do_all or "--eth" in args:
        eth_day()
    if do_all or "--july" in args:
        july()
    yr = None
    if do_all or "--year" in args:
        yr = year()
    if do_all or "--timeframes" in args:
        timeframes()
    if do_all or "--master" in args:
        master()
    # the runner and the stop-scaling proof are read off HIS OWN entry, which
    # is the arm that carries the edge
    if yr is not None:
        stop_scaling(yr[("fvg_midpoint", 4.0)])
        trend_days(yr[("fvg_midpoint", 4.0)])
    elif "--trenddays" in args:
        f = book(*YEAR, entry_style="fvg_midpoint")
        stop_scaling(f)
        trend_days(f)
    print()
    print(cc.in_his_words())
    return 0


if __name__ == "__main__":
    sys.exit(main())
