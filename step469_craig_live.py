"""
step469_craig_live.py — every number the live Craig wiring is judged on.

READ ONLY. It replays cached parquet through `craig_crypto` and through
`craig_live`, renders one message, and prints. It fetches nothing, places
nothing, runs no git, and writes only step469_* CSVs.

WHAT IT PRODUCES
    --agree     the replay and the live engine, trade by trade, on the same
                twelve months. The test that catches drift.
    --ladder    THE SURVIVAL TABLE. The money-game ladder replayed over that
                same twelve-month trade record on the $2,178 stake: what
                fraction of paths are still alive after a month, how many
                double, how many reach $25,000, and the median outcome —
                against the same at half the base.
    --leverage  what the 1-hour stops imply, in both readings, and what the
                exchange would actually set on the real demo balance
    --message   the exact Telegram message a Craig setup sends
    --book      the shipping year: per pair, per session, per outcome
    --all       all of the above

LEVERAGE, NEVER "RISK %". Two different numbers are printed and each says
which it is: the position's face value as a MULTIPLE OF THE ACCOUNT, and the
LEVERAGE THE EXCHANGE SETS, which is the face value over the margin actually
posted. On this desk one trade posts 10% of the account as margin, so the
second number is ten times the first — and the second is the one on his
BloFin screen.
"""

from __future__ import annotations

import math
import os
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import craig_crypto as cc
import craig_live as cl
import tjr_alerts
import tjr_desk

YEAR = (pd.Timestamp("2025-07-27"), pd.Timestamp("2026-07-26"))

# WHAT THE EXCHANGE ITSELF SAYS, read from BloFin's own instrument spec on
# 2026-07-26 and written down here so this report needs no network. The live
# order path never uses this table — `venue.BlofinVenue.spec` reads the
# numbers fresh from the exchange every time, and a spec it cannot read means
# DO NOT TRADE, never a default.
EXCHANGE = {
    "BTC/USD": {"max_leverage": 150, "contract_value": 0.001, "lot": 0.1},
    "ETH/USD": {"max_leverage": 150, "contract_value": 0.01, "lot": 0.1},
    "SOL/USD": {"max_leverage": 75, "contract_value": 1.0, "lot": 0.01},
    "XRP/USD": {"max_leverage": 50, "contract_value": 100.0, "lot": 0.1},
    "DOT/USD": {"max_leverage": 75, "contract_value": 1.0, "lot": 0.1},
}

# The BloFin demo balance on 2026-07-26, read once. Only used to say what the
# exchange would DO with these trades on the money that is actually there.
DEMO_EQUITY = 2259.04

_CACHE: dict = {}


def data(pair):
    if pair not in _CACHE:
        _CACHE[pair] = cc.load(pair)
    return _CACHE[pair]


def both(pair):
    cfg = cl.live_config(pair)
    rep = cc.run_pair(pair, *YEAR, cfg=cfg, data=data(pair))["trades"]
    liv = cl.replay_through_live(pair, *YEAR, cfg=cfg,
                                 data=data(pair))["trades"]
    return (sorted(rep, key=lambda t: (t.entry_t, t.entry)),
            sorted(liv, key=lambda t: (t.entry_t, t.entry)))


# ================================================= 1. THE AGREEMENT
def agree(out=True) -> pd.DataFrame:
    """The replay and the live engine, on the same candles, trade by trade."""
    rows, diffs = [], 0
    FIELDS = ("entry_t", "exit_t", "entry", "stop_at_risk", "target", "exit",
              "units", "notional", "risk_dollars", "pnl", "cost",
              "r_multiple", "outcome", "direction", "session",
              "equity_at_entry", "moved_to_breakeven")
    for pair in cl.PAIRS:
        rep, liv = both(pair)
        same = len(rep) == len(liv)
        bad = 0 if same else abs(len(rep) - len(liv))
        for a, b in zip(rep, liv):
            for f in FIELDS:
                x, y = getattr(a, f), getattr(b, f)
                ok = (abs(x - y) <= 1e-9 * max(1.0, abs(x))
                      if isinstance(x, float) else x == y)
                if not ok:
                    bad += 1
                    if out:
                        print(f"    DIFFERENCE {pair} {a.entry_t} {f}: "
                              f"{x!r} vs {y!r}")
        diffs += bad
        rows.append({"pair": pair, "replay_trades": len(rep),
                     "live_trades": len(liv),
                     "replay_net": round(sum(t.pnl for t in rep), 2),
                     "live_net": round(sum(t.pnl for t in liv), 2),
                     "fields_compared": len(rep) * len(FIELDS),
                     "differences": bad})
    d = pd.DataFrame(rows)
    if out:
        print("\nTHE REPLAY AND THE LIVE ENGINE, SAME CANDLES, SAME TWELVE "
              "MONTHS")
        print(d.to_string(index=False))
        print(f"\n  {int(d['replay_trades'].sum())} trades compared across "
              f"{len(FIELDS)} fields each — "
              f"{int(d['fields_compared'].sum()):,} comparisons")
        print(f"  DIFFERENCES: {diffs}")
        print(f"  replay net ${d['replay_net'].sum():+,.2f}   "
              f"live net ${d['live_net'].sum():+,.2f}")
        d.to_csv(f"{REPO}/step469_agreement.csv", index=False)
    return d


# ================================================= 2. THE LEVERAGE
def leverage(out=True) -> pd.DataFrame:
    """What the 1-hour stops imply, in both readings, and what the exchange
    would set on the money that is actually in the demo account.

    THE ARITHMETIC, so nothing here is a black box. The size is
    3% of equity divided by the stop's distance in the price, so the face
    value of the position is 3% of equity divided by the stop AS A SHARE OF
    THE PRICE. A 0.54% stop therefore buys a position worth 5.6 times the
    account — and the exchange's own leverage number is that face value over
    the MARGIN POSTED, which on this desk is 10% of the account, so 56x.
    """
    rows = []
    for pair in cl.PAIRS:
        spec = EXCHANGE[pair]
        _, liv = both(pair)
        for t in liv:
            stop_pct = abs(t.entry - t.stop_at_risk) / t.entry
            # the same trade, sized on the real demo balance
            units = 0.03 * DEMO_EQUITY / abs(t.entry - t.stop_at_risk)
            face = units * t.entry
            need = face / (0.10 * DEMO_EQUITY)
            lev = min(max(1, int(need + 0.999)), spec["max_leverage"])
            margin = face / lev
            rows.append({
                "pair": pair, "session": t.session, "entry_t": t.entry_t,
                "stop_move_in_price_pct": 100 * stop_pct,
                "face_value_times_account": t.notional / t.equity_at_entry,
                "exchange_leverage_wanted": need,
                "exchange_leverage_set": lev,
                "capped_by_the_exchange": need > spec["max_leverage"],
                "margin_posted_dollars": margin,
                "margin_share_of_account_pct": 100 * margin / DEMO_EQUITY,
                "position_dollars": face,
                "contracts": units / spec["contract_value"],
                "below_min_lot": (units / spec["contract_value"]) < spec["lot"],
                "liquidation_move_pct": 100.0 / lev,
                "guard_needs_pct": 100 * 3 * stop_pct,
            })
    f = pd.DataFrame(rows)
    if out:
        print("\nWHAT THE 1-HOUR STOPS IMPLY")
        print(f"  the stop, AS A MOVE IN THE PRICE: median "
              f"{f['stop_move_in_price_pct'].median():.3f}%, "
              f"5th-95th {f['stop_move_in_price_pct'].quantile(.05):.3f}% to "
              f"{f['stop_move_in_price_pct'].quantile(.95):.3f}%")

        def band(col, label, unit="x"):
            s = f[col]
            print(f"  {label:38s} min {s.min():7.1f}{unit}  median "
                  f"{s.median():7.1f}{unit}  95th {s.quantile(.95):7.1f}{unit}"
                  f"  max {s.max():7.1f}{unit}")

        band("face_value_times_account", "position as a MULTIPLE of the account")
        band("exchange_leverage_set", "LEVERAGE THE EXCHANGE SETS")
        band("margin_share_of_account_pct",
             "margin posted, % OF THE ACCOUNT", "%")
        print(f"\n  on the real demo balance of ${DEMO_EQUITY:,.2f}, one trade "
              f"risks ${0.03*DEMO_EQUITY:,.2f}")
        print(f"  trades the exchange's own ceiling clamps: "
              f"{int(f['capped_by_the_exchange'].sum())} of {len(f)} — the "
              f"size does not change when it clamps, only the margin posted "
              f"goes up")
        print(f"  trades too small for the symbol's minimum lot: "
              f"{int(f['below_min_lot'].sum())}")
        refused = int((f["liquidation_move_pct"] < f["guard_needs_pct"]).sum())
        print(f"  trades the venue's liquidation guard would refuse: {refused}"
              f"  (it wants the liquidation price at least 3 times the stop's "
              f"distance away; the tightest headroom in the year is "
              f"{(f['liquidation_move_pct']/f['guard_needs_pct']).min():.2f} "
              f"times what it asks)")
        print("\n  per pair")
        for p, g in f.groupby("pair"):
            print(f"    {p:9s} exchange ceiling {EXCHANGE[p]['max_leverage']:3d}x   "
                  f"clamped {int(g['capped_by_the_exchange'].sum()):3d}/{len(g):3d}   "
                  f"median leverage set {g['exchange_leverage_set'].median():5.0f}x   "
                  f"median margin ${g['margin_posted_dollars'].median():7.2f} "
                  f"({g['margin_share_of_account_pct'].median():4.1f}% of the "
                  f"account)")
        peak = _peak_margin(f)
        print(f"\n  most margin ever tied up at one moment in the year: "
              f"${peak:,.2f}, {100*peak/DEMO_EQUITY:.1f}% OF THE ACCOUNT")
        f.to_csv(f"{REPO}/step469_leverage.csv", index=False)
    return f


def _peak_margin(f: pd.DataFrame) -> float:
    """How much margin was tied up at the busiest moment. Positions on a
    pair cannot overlap (the exchange nets them), but two pairs can."""
    liv = {}
    for pair in cl.PAIRS:
        _, t = both(pair)
        liv[pair] = t
    ev = []
    for pair, ts in liv.items():
        g = f[f["pair"] == pair].reset_index(drop=True)
        for i, t in enumerate(ts):
            m = float(g.loc[i, "margin_posted_dollars"])
            ev.append((pd.Timestamp(t.entry_t), +m))
            ev.append((pd.Timestamp(t.exit_t), -m))
    ev.sort()
    cur = peak = 0.0
    for _, dlt in ev:
        cur += dlt
        peak = max(peak, cur)
    return peak


# ================================================= 2b. THE SURVIVAL TABLE
#
# THE ODDS HE SEES BEFORE THE LADDER SHIPS.
#
# The ladder is Alex Gonzalez's money game and Wallace's stake. At the stake
# it risks one part in 4.5 of the balance on every trade — his own
# "at least four or five trades in you before you would obviously lose the
# account" — and 72.1% of the shipping year's trades were losers, because the
# method makes its money at 1:4 rather than by being right often. Those two
# facts together mean some paths die. Wallace has said so explicitly: it is
# his stake, on the demo venue, and it is "how much I would be willing to lose
# to even start". The ladder ships ON. He sees this first.
#
# HOW THIS IS BUILT, so nothing here is a black box.
#
#   THE TRADES ARE REAL. Every draw comes from the 140 trades the live engine
#   actually booked over the twelve months, each carrying what it made or lost
#   as a MULTIPLE OF WHAT IT RISKED after its round trip, and how far away its
#   stop sat AS A MOVE IN THE PRICE. Nothing is invented and no distribution
#   is fitted.
#
#   THE ORDER IS RESAMPLED. The one historical ordering is a single path, and
#   a single path cannot answer "how often". So the 140 outcomes are drawn
#   with replacement into 20,000 twelve-month paths. The historical ordering
#   is ALSO run, on its own, and printed beside them.
#
#   STREAKS ARE CHECKED SEPARATELY. Drawing one trade at a time throws away
#   any tendency for losses to arrive together, and losing streaks are exactly
#   what kills these paths. So the same table is also run drawing BLOCKS of
#   five consecutive trades, which keeps the record's own clustering.
#
#   ONE TRADE AT A TIME. The real desk can hold up to five pairs at once, so
#   two trades can be sized on the same balance before either closes. Modelled
#   sequentially this is slightly OPTIMISTIC about the down side, because the
#   second trade in a pair of concurrent losers is sized on a balance that has
#   not yet taken the first loss. Said out loud rather than buried.
#
#   DEAD MEANS THE STAKE IS GONE. The ladder risks a SHARE of what is left, so
#   arithmetically the balance never reaches zero — it just halves and halves.
#   "Dead" here is down 90% from the stake, $217.80 left, which is the point
#   where the money he was willing to lose is gone in every way that matters.
LADDER_PATHS = 20_000
LADDER_BLOCK = 5
RUIN_SHARE_OF_STAKE = 0.10
STAKE = 2178.0
MONTH_ONE_TRADES = 12          # 140 trades / 12 months, rounded up


def _record() -> pd.DataFrame:
    """The twelve-month trade record, in the order it happened, with the two
    numbers a sizing rule needs: what each trade paid as a multiple of what it
    risked, and how wide its stop was."""
    rows = []
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            rows.append({
                "pair": pair, "entry_t": pd.Timestamp(t.entry_t),
                "net_r": t.pnl / t.risk_dollars if t.risk_dollars else 0.0,
                "stop_pct": abs(t.entry - t.stop_at_risk) / t.entry,
                "outcome": t.outcome,
            })
    return pd.DataFrame(rows).sort_values("entry_t").reset_index(drop=True)


def _share(equity: float, base_divisor: float) -> float:
    """The ladder's share of the account, with the BASE left open so the
    comparison arm can be run.

    `base_divisor` is his "four or five trades in you" number. 4.5 is HIS and
    at that value this function IS `craig_live.money_game_share` — the assert
    below holds it — so the shipping rule has exactly one definition and this
    is only a knob for the table. 9.0 is OURS, for comparison, and everything
    else about the curve, including the 1% at $25,000, stays his.
    """
    base = 1.0 / base_divisor
    equity = float(equity)
    if equity <= 0:
        return 0.0
    if equity <= STAKE:
        return base
    if equity >= cl.PERCENTAGE_GAME_AT:
        return cl.PERCENTAGE_GAME_SHARE
    progress = np.log(equity / STAKE) / np.log(cl.PERCENTAGE_GAME_AT / STAKE)
    return float(base * (cl.PERCENTAGE_GAME_SHARE / base) ** progress)


assert abs(_share(7_000.0, 4.5) - cl.money_game_share(7_000.0, STAKE)) < 1e-12


def _risk_dollars(equity: float, base_divisor: float, stop_pct: float,
                  ceiling: float) -> float:
    """What one trade may cost at this balance, under the ladder — and cut to
    what the exchange can actually carry."""
    want = _share(equity, base_divisor) * equity
    if stop_pct <= 0 or ceiling <= 0:
        return want
    most = ceiling * equity * stop_pct        # the ceiling, in risk dollars
    return min(want, most)


def _walk(seq_r, seq_stop, seq_ceiling, base_divisor: float) -> dict:
    """One path. Returns what happened to it."""
    eq = STAKE
    ruin = RUIN_SHARE_OF_STAKE * STAKE
    alive_month_one = True
    doubled = reached = False
    dead_at = None
    for i in range(len(seq_r)):
        risk = _risk_dollars(eq, base_divisor, seq_stop[i], seq_ceiling[i])
        eq += risk * seq_r[i]
        if eq >= 2 * STAKE and not doubled and dead_at is None:
            doubled = True
        if eq >= 25_000.0 and not reached and dead_at is None:
            reached = True
        if eq <= ruin and dead_at is None:
            dead_at = i
            eq = min(eq, ruin)
            break
    if dead_at is not None and dead_at < MONTH_ONE_TRADES:
        alive_month_one = False
    return {"final": eq, "dead": dead_at is not None,
            "alive_month_one": alive_month_one, "doubled": doubled,
            "reached_25k": reached}


def _paths(rec: pd.DataFrame, base_divisor: float, block: int,
           n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r = rec["net_r"].to_numpy(float)
    sp = rec["stop_pct"].to_numpy(float)
    ce = np.array([cl.leverage_ceiling(p) for p in rec["pair"]], float)
    m = len(r)
    out = []
    for _ in range(n):
        if block <= 1:
            idx = rng.integers(0, m, m)
        else:
            starts = rng.integers(0, m, int(np.ceil(m / block)))
            idx = np.concatenate([(s + np.arange(block)) % m
                                  for s in starts])[:m]
        out.append(_walk(r[idx], sp[idx], ce[idx], base_divisor))
    return pd.DataFrame(out)


def ladder(out=True) -> pd.DataFrame:
    """THE SURVIVAL TABLE, led with rather than buried."""
    rec = _record()
    rows = []
    arms = [("HIS base — equity / 4.5", 4.5),
            ("half the base — equity / 9", 9.0)]
    draws = [("one trade at a time", 1), ("in blocks of five", LADDER_BLOCK)]
    for label, div in arms:
        # the one ordering that really happened
        hist = _walk(rec["net_r"].to_numpy(float),
                     rec["stop_pct"].to_numpy(float),
                     np.array([cl.leverage_ceiling(p) for p in rec["pair"]],
                              float), div)
        rows.append({"arm": label, "draw": "the year as it happened",
                     "paths": 1,
                     "survived_month_one_pct": 100.0 * hist["alive_month_one"],
                     "doubled_pct": 100.0 * hist["doubled"],
                     "reached_25k_pct": 100.0 * hist["reached_25k"],
                     "died_pct": 100.0 * hist["dead"],
                     "median_final": round(hist["final"], 2),
                     "p05_final": round(hist["final"], 2),
                     "p95_final": round(hist["final"], 2)})
        for dlabel, blk in draws:
            p = _paths(rec, div, blk, LADDER_PATHS, seed=469 + int(div) + blk)
            rows.append({
                "arm": label, "draw": dlabel, "paths": len(p),
                "survived_month_one_pct": 100.0 * p["alive_month_one"].mean(),
                "doubled_pct": 100.0 * p["doubled"].mean(),
                "reached_25k_pct": 100.0 * p["reached_25k"].mean(),
                "died_pct": 100.0 * p["dead"].mean(),
                "median_final": round(float(p["final"].median()), 2),
                "p05_final": round(float(p["final"].quantile(0.05)), 2),
                "p95_final": round(float(p["final"].quantile(0.95)), 2)})
    f = pd.DataFrame(rows)
    if out:
        print("\nTHE MONEY-GAME LADDER ON THE $2,178 STAKE — WHAT HAPPENS TO "
              "THE MONEY")
        print(f"  the record: {len(rec)} trades over twelve months, "
              f"{100*(rec['net_r'] > 0).mean():.1f}% of them made money, "
              f"{len(rec)/52:.1f} a week")
        # THE CADENCE, WITH NOTHING CAPPING IT. Wallace, 2026-07-26: "if you
        # see the setup, take the trade. its a demo at the end of the day."
        # Nothing in this wiring limits trades per day or per week; the only
        # bounds are the method's own — the two-candle hunt window after each
        # session open, the 24-candle life of the resting limit, and a setup
        # dying at its stop before it fills. This is what that produces.
        wk = rec.set_index("entry_t").resample("7D").size()
        dy = rec.set_index("entry_t").resample("1D").size()
        print(f"  THE CADENCE, NOTHING CAPPING IT: {len(rec)/52:.1f} trades a "
              f"week across all five pairs, busiest week {int(wk.max())}, "
              f"busiest day {int(dy.max())}, "
              f"{int((wk == 0).sum())} of {len(wk)} weeks with none at all")
        print(f"  the only bound the wiring adds is the exchange's: BloFin "
              f"nets a symbol into ONE position, so a second setup on a pair "
              f"already carrying one is decided and reported but not sent. "
              f"That bound hit 1 entry in {len(rec)} over the year.")
        print(f"  the ladder: ${cl.money_game_risk_dollars(STAKE, STAKE):,.0f} "
              f"on the first trade, which is "
              f"{100*cl.money_game_share(STAKE, STAKE):.1f}% OF THE ACCOUNT, "
              f"stepping down to 1% of the account at $25,000")
        print(f"  dead     = down 90% from the stake, ${RUIN_SHARE_OF_STAKE*STAKE:,.2f} left")
        print(f"  month one= the first {MONTH_ONE_TRADES} trades\n")
        show = f.copy()
        for c in ("survived_month_one_pct", "doubled_pct", "reached_25k_pct",
                  "died_pct"):
            show[c] = show[c].map(lambda v: f"{v:5.1f}%")
        for c in ("median_final", "p05_final", "p95_final"):
            show[c] = show[c].map(lambda v: f"${v:,.0f}")
        print(show.to_string(index=False))
        print("\n  every percentage in the four middle columns is a SHARE OF "
              "PATHS, not a share of money.")
        print("  the last three are DOLLARS the account ends the year on.")
        print("  'doubled' means it doubled BEFORE it died. Most of the paths "
              "that double still die afterwards.")

        # WHAT SIZE THIS RECORD ACTUALLY GROWS FASTEST AT — worked out from
        # the record itself, not from a rule anyone brought to it. It is the
        # share of the account whose average log growth per trade is highest.
        # Stated because it is the one number that explains the table: past
        # that share, betting MORE ends with LESS.
        r = rec["net_r"].to_numpy(float)
        grid = np.linspace(0.005, 0.60, 1200)
        with np.errstate(divide="ignore", invalid="ignore"):
            g = np.array([np.mean(np.log(np.clip(1 + fr * r, 1e-12, None)))
                          for fr in grid])
        best = float(grid[int(np.argmax(g))])
        base = cl.money_game_share(STAKE, STAKE)
        print(f"\n  THE SIZE THIS RECORD GROWS FASTEST AT: "
              f"{100*best:.1f}% OF THE ACCOUNT per trade.")
        print(f"  HIS base is {100*base:.1f}% OF THE ACCOUNT, which is "
              f"{base/best:.1f} times that. Half his base is "
              f"{100*base/2:.1f}% OF THE ACCOUNT, still {base/2/best:.1f} "
              f"times it. Both sit past the top of the curve, and that is the "
              f"whole reason the median path above is a dead account rather "
              f"than a small one — bigger bets, smaller end result.")
        print(f"  the flat 3% OF THE ACCOUNT the shipping replay used is "
              f"{0.03/best:.1f} times it, which is why step467's book grows "
              f"and this one does not.")
        print(f"  the average trade still MAKES money: "
              f"{rec['net_r'].mean():+.3f} times what it risked, after the "
              f"round trip. Size is what turns that into the table above.")
        f.to_csv(f"{REPO}/step469_ladder.csv", index=False)
    return f


def ladder_leverage(out=True) -> pd.DataFrame:
    """THE LEVERAGE BAND UNDER THE LADDER, on the year as it happened.

    Three different numbers and every one of them says which it is:
      * the position's FACE VALUE as a MULTIPLE OF THE ACCOUNT
      * the LEVERAGE THE EXCHANGE SETS if one trade posts 10% of the account
        as margin, which is what venue.py works it out from
      * the LEVERAGE THE EXCHANGE SETS once its own ceiling is applied, and
        the margin that then has to be posted, AS A SHARE OF THE ACCOUNT
    """
    rec = _record()
    eq = STAKE
    ruin = RUIN_SHARE_OF_STAKE * STAKE
    rows = []
    for _, t in rec.iterrows():
        ceiling = cl.leverage_ceiling(t["pair"])
        want = cl.money_game_risk_dollars(eq, STAKE)
        capped = min(want, ceiling * eq * t["stop_pct"])
        face = capped / t["stop_pct"]
        want_lev = face / (0.10 * eq)
        set_lev = min(max(1.0, math.ceil(want_lev)), ceiling)
        margin = face / set_lev
        rows.append({
            "pair": t["pair"], "entry_t": t["entry_t"],
            "equity_before": eq,
            "stop_move_in_price_pct": 100 * t["stop_pct"],
            "risk_dollars": capped,
            "risk_share_of_account_pct": 100 * capped / eq,
            "truncated_by_the_ceiling": capped < want - 1e-9,
            "face_value_times_account": face / eq,
            "exchange_leverage_wanted": want_lev,
            "exchange_leverage_set": set_lev,
            "margin_share_of_account_pct": 100 * margin / eq,
            "liquidation_move_pct": 100.0 / set_lev,
            "guard_needs_pct": 100 * 3 * t["stop_pct"],
            "guard_would_refuse": (100.0 / set_lev) < 100 * 3 * t["stop_pct"],
        })
        eq += capped * t["net_r"]
        if eq <= ruin:
            eq = ruin
            break
    f = pd.DataFrame(rows)
    if out:
        print("\nTHE LEVERAGE BAND UNDER THE LADDER — the year as it happened")

        def band(col, label, unit="x"):
            s = f[col]
            print(f"  {label:44s} min {s.min():8.1f}{unit}  median "
                  f"{s.median():8.1f}{unit}  95th {s.quantile(.95):8.1f}{unit}"
                  f"  max {s.max():8.1f}{unit}")

        band("risk_share_of_account_pct",
             "what one trade risks, % OF THE ACCOUNT", "%")
        band("face_value_times_account",
             "position face value, MULTIPLE of the account")
        band("exchange_leverage_set", "LEVERAGE THE EXCHANGE SETS")
        band("margin_share_of_account_pct",
             "margin posted, % OF THE ACCOUNT", "%")
        print(f"\n  trades the exchange's ceiling CUT THE SIZE on: "
              f"{int(f['truncated_by_the_ceiling'].sum())} of {len(f)}")
        print(f"  trades venue.py's liquidation guard would REFUSE: "
              f"{int(f['guard_would_refuse'].sum())} of {len(f)} — it wants "
              f"the liquidation price at least 3 times the stop's distance "
              f"away, and at this size the leverage is far past that")
        _refusal_rate(rec)
        f.to_csv(f"{REPO}/step469_ladder_leverage.csv", index=False)
    return f


def _refusal_rate(rec: pd.DataFrame) -> None:
    """HOW MANY OF THE YEAR'S SETUPS WOULD NEVER REACH THE EXCHANGE, at the
    ladder's base share, on all 140 rather than only the ones before the
    account died. This is the number that decides whether the book trades at
    all, so it is worked out on its own.

    NOTHING HERE CHANGES A SETTING. `venue.BlofinVenue.PER_TRADE_MARGIN_SHARE`
    and `LIQUIDATION_SAFETY` are Wallace's to move and venue.py was not
    touched. This says what they do under the new size.
    """
    print("\n  WHAT THE VENUE'S OWN GUARD DOES TO THE LADDER, all "
          f"{len(rec)} setups of the year")
    for label, share in (("the flat 3% the replay used", 0.03),
                         ("HIS base, 22.2% OF THE ACCOUNT", 1 / 4.5)):
        ref, faces = 0, []
        for _, t in rec.iterrows():
            ceiling = cl.leverage_ceiling(t["pair"])
            face = share / t["stop_pct"]                 # multiple of account
            lev = min(max(1, math.ceil(face / 0.10)), ceiling)
            faces.append(face)
            if (1.0 / lev) < 3 * t["stop_pct"]:
                ref += 1
        print(f"    {label:34s} median position {np.median(faces):6.1f}x the "
              f"account   REFUSED {ref:3d} of {len(rec)} "
              f"({100*ref/len(rec):4.0f}%)")
    print("    the guard reads: at the leverage this size needs, the exchange "
          "would liquidate nearer than the stop sits, so it does not take "
          "the trade. Nothing was changed in venue.py to make it pass.")


# ================================================= 3. THE MESSAGE
def message(out=True) -> str:
    """The message on the money that is ACTUALLY in the account.

    Rendering it on the $100,000 the replay is quoted against would show him a
    $851,000 position and a $10,000 margin, neither of which he will ever see.
    The demo balance is what his phone will show.
    """
    txt = tjr_desk.craig_sample(account=DEMO_EQUITY)
    if out:
        print(f"\nTHE EXACT MESSAGE A CRAIG SETUP SENDS, on the real demo "
              f"balance of ${DEMO_EQUITY:,.2f}")
        print("-" * 74)
        print(txt)
        print("-" * 74)
    return txt


# ================================================= 4. THE BOOK
def book(out=True) -> pd.DataFrame:
    rows = []
    for pair in cl.PAIRS:
        _, liv = both(pair)
        for t in liv:
            rows.append({
                "pair": pair, "session": t.session, "entry_t": t.entry_t,
                "exit_t": t.exit_t,
                "side": "long" if t.direction > 0 else "short",
                "outcome": t.outcome, "r": t.r_multiple, "pnl": t.pnl,
                "cost": t.cost,
                "stop_move_in_price_pct":
                    100 * abs(t.entry - t.stop_at_risk) / t.entry,
                "face_value_times_account": t.notional / t.equity_at_entry,
                "hours_held": (pd.Timestamp(t.exit_t)
                               - pd.Timestamp(t.entry_t)).total_seconds() / 3600,
                "moved_to_breakeven": t.moved_to_breakeven,
            })
    f = pd.DataFrame(rows)
    if out:
        print("\nTHE SHIPPING YEAR, THROUGH THE LIVE ENGINE — five pairs, "
              "each on its own $100,000")
        print(f"  {len(f)} trades, {len(f)/365:.2f} a day across all five, "
              f"won {100*(f['pnl']>0).mean():.1f}%, mean {f['r'].mean():+.3f}R "
              f"a trade, NET ${f['pnl'].sum():+,.0f}")
        print("\n  per pair")
        for p, g in f.groupby("pair"):
            print(f"    {p:9s} {len(g):3d} trades  won {100*(g['pnl']>0).mean():5.1f}%  "
                  f"meanR {g['r'].mean():+5.2f}  NET ${g['pnl'].sum():+11,.0f}")
        print("\n  per session")
        for s, g in f.groupby("session"):
            print(f"    {s:9s} {len(g):3d} trades  won {100*(g['pnl']>0).mean():5.1f}%  "
                  f"meanR {g['r'].mean():+5.2f}  NET ${g['pnl'].sum():+11,.0f}")
        print("\n  how they end")
        for o, g in f.groupby("outcome"):
            print(f"    {o:18s} {len(g):3d}  ({100*len(g)/len(f):4.1f}% of "
                  f"them)  NET ${g['pnl'].sum():+11,.0f}")
        print(f"\n  held: median {f['hours_held'].median():.1f} hours, "
              f"longest {f['hours_held'].max():.0f}")
        print(f"  the stop moved to break even on "
              f"{int(f['moved_to_breakeven'].sum())} of them")
        f.to_csv(f"{REPO}/step469_book.csv", index=False)
    return f


def main() -> int:
    args = set(sys.argv[1:]) or {"--all"}
    do = "--all" in args
    # THE SURVIVAL TABLE IS FIRST, deliberately. It is the number that decides
    # whether the stake is still there in a month, and it does not go under a
    # profit table.
    if do or "--ladder" in args:
        ladder()
        ladder_leverage()
    if do or "--agree" in args:
        agree()
    if do or "--book" in args:
        book()
    if do or "--leverage" in args:
        leverage()
    if do or "--message" in args:
        message()
    return 0


if __name__ == "__main__":
    sys.exit(main())
