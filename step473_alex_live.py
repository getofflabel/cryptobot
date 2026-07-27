#!/usr/bin/env python3
"""step473_alex_live.py — the Alex engine wired into the live desk, and what
that wiring actually implies. Replay only; NO ORDER ON ANY VENUE.

WHAT THIS FILE IS FOR

    step472 measured the METHOD. This one measures the WIRING: that the
    engine which will place the orders books the identical trades as the
    engine every step472 number came out of, and what the two books' sizes
    mean on the two real accounts they will run on.

    Nothing here fetches, writes a parquet, or reaches an order path. The
    BloFin and OANDA prices it quotes are the ones measured on 2026-07-27 and
    they are constants in this file, so it runs on a machine with no
    credentials at all.

WHAT SHIPS, AND WHOSE DECISION EACH PIECE IS

    step472 defaults, untouched          the method
    weekly-close direction rule ON       WALLACE, 2026-07-27: "alex: on"
    money-game ladder ON for gold        WALLACE, 2026-07-27: "ladder on gold
                                         too" — gold only; forex is over his
                                         own $25,000 percentage-game line
    3% base risk per trade               his own-money band's floor, and the
                                         top of Wallace's standing 1-3%
    structure-shift exits OFF            step472's default
    cadence cap OFF                      Wallace, 2026-07-27

LANGUAGE

    LEVERAGE, never "risk %". Every percentage says which one it is: a move
    in the PRICE, a share of the ACCOUNT, or a share of the MARGIN. Costs are
    charged and never shown as a line item — they are inside every net dollar.

Run:  python3 step473_alex_live.py               everything
      python3 step473_alex_live.py --agreement   replay vs live, both books
      python3 step473_alex_live.py --weekly      what Wallace's ruling did
      python3 step473_alex_live.py --leverage    the band each book implies
      python3 step473_alex_live.py --margin      the shared BloFin stake
      python3 step473_alex_live.py --samples     the two Telegram messages
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alex_engine as ae
import alex_live as al

REPO = os.path.dirname(os.path.abspath(__file__))

CLOSED = ["stop", "target", "friday", "flip",
          "runner_stop", "runner_flip", "runner_friday", "runner_cap"]

YEAR = ("2025-07-27", "2026-07-26")
FIVE = ("2021-07-05", "2026-07-26")

# Measured live 2026-07-27. Constants here so this file needs no credentials.
OANDA_XAU_MID = 4088.85          # OANDA XAU/USD mid
BLOFIN_XAUT_MARK = 4077.60       # BloFin XAUT-USDT mark
BLOFIN_EQUITY = 2258.62          # the shared stake, as the exchange reported it
OANDA_NAV = 100_000.00
XAUT_MAX_LEVERAGE = 50.0         # BloFin's own ceiling for the contract
# OANDA's margin rate per instrument on this account, read from the broker
OANDA_MARGIN_RATE = {"EUR_USD": 0.02, "GBP_USD": 0.05, "GBP_JPY": 0.05}

FOREX = list(al.FOREX.values())
GOLD = al.GOLD_INSTRUMENT

_CACHE: dict = {}


def frames(inst):
    if inst not in _CACHE:
        _CACHE[inst] = ae.load(inst)
    return _CACHE[inst]


def book(over, window, instruments=None, control="none"):
    out = {}
    for inst in (instruments or ae.INSTRUMENTS):
        cfg = ae.dumb_config_for(inst, **dict(over, control=control))
        out[inst] = ae.run_instrument(inst, *window, cfg=cfg,
                                      frames=frames(inst))
    return out


def stats(f: pd.DataFrame) -> dict:
    d = f[f["outcome"].isin(CLOSED)]
    n = len(d)
    return {"n": n, "net": d["pnl"].sum(),
            "won": 100.0 * (d["pnl"] > 0).mean() if n else 0.0,
            "r": d["r"].mean() if n else 0.0,
            "lev_med": d["leverage"].median() if n else 0.0,
            "lev_hi": d["leverage"].max() if n else 0.0,
            "frame": d}


# ================================================ 1. REPLAY vs LIVE
def agreement(window=YEAR) -> int:
    print("\n" + "=" * 100)
    print("1. THE REPLAY AND THE LIVE ENGINE, SAME CANDLES, EVERY FIELD")
    print("   `alex_engine.run_instrument` is the engine step472 measured.")
    print("   `alex_live.Engine` is the engine that will place the orders.")
    print("   The 36x sizing bug happened because nothing ever put the two "
          "side by side.")
    print("=" * 100)
    fields = ("entry", "stop", "target", "exit", "units", "notional",
              "leverage", "risk_dollars", "pnl", "cost", "r_multiple",
              "quality", "hours_held")
    bad = 0
    print(f"  {'instrument':<10s} {'replay':>7s} {'live':>7s} "
          f"{'differences':>12s}   net (each on its own $100,000)")
    for inst in ae.INSTRUMENTS:
        cfg = al.live_config(inst)
        rep = ae.run_instrument(inst, *window, cfg=cfg,
                                frames=frames(inst))["trades"]
        liv = al.replay_through_live(inst, *window, cfg=cfg,
                                     frames=frames(inst))["trades"]
        rep = sorted(rep, key=lambda t: (t.entry_t, t.entry))
        liv = sorted(liv, key=lambda t: (t.entry_t, t.entry))
        diffs = 0 if len(rep) == len(liv) else 9999
        for a, b in zip(rep, liv):
            for f in fields:
                x, y = getattr(a, f), getattr(b, f)
                if x is None or y is None:
                    diffs += (x is not y)
                elif abs(float(x) - float(y)) > 1e-9:
                    diffs += 1
            diffs += (a.outcome != b.outcome)
            diffs += (pd.Timestamp(a.entry_t) != pd.Timestamp(b.entry_t))
        bad += diffs
        print(f"  {inst:<10s} {len(rep):>7d} {len(liv):>7d} {diffs:>12d}   "
              f"${sum(t.pnl for t in rep):>+11,.0f}")
    print(f"\n  VERDICT: {'ZERO DIFFERENCES — the two engines are one engine'
                          if bad == 0 else f'{bad} DIFFERENCES — DO NOT ARM'}")
    return bad


# ============================================ 2. WALLACE'S WEEKLY RULING
def weekly(window=FIVE) -> None:
    print("\n" + "=" * 100)
    print("2. THE WEEKLY-CLOSE DIRECTION RULE — WALLACE'S RULING, 2026-07-27:"
          " \"alex: on\"")
    print("   His own rule (2026-05-25): \"those candlesticks opening and "
          "closing dictate the direction")
    print("   of the following week.\" The June-2026 spine is newer and says "
          "one timeframe only, so")
    print("   newest-governs had it OFF. The owner overruled that. It is a "
          "FILTER: it can refuse a")
    print("   trade whose direction disagrees with the last CLOSED weekly "
          "candle, and nothing else.")
    print("=" * 100)
    print(f"  {'':<26s} {'n':>5s} {'won':>7s} {'mean R':>8s} "
          f"{'fade R':>8s} {'net $':>13s}")
    for name, over in (("spine alone (weekly OFF)", {"risk_pct_per_trade": 0.03}),
                       ("weekly-close ON  (SHIPS)", dict(al.BOOK))):
        f = ae.frame(book(over, window))
        g = ae.frame(book(over, window, control="reversed"))
        s, t = stats(f), stats(g)
        print(f"  {name:<26s} {s['n']:>5d} {s['won']:>6.1f}% {s['r']:>+8.2f} "
              f"{t['r']:>+8.2f} ${s['net']:>+12,.0f}")
    print("\n  The fade column is what makes it evidence rather than a good "
          "five years: the same")
    print("  entries with the DIRECTION REVERSED lose money, so the rule's "
          "direction call is real.")
    f = ae.frame(book(dict(al.BOOK), window))
    d = f[f["outcome"].isin(CLOSED)]
    print("\n  per instrument, each on its own $100,000:")
    for inst in ae.INSTRUMENTS:
        s = d[d["instrument"] == inst]
        print(f"    {inst:<10s} {len(s):>4d} trades   "
              f"${s['pnl'].sum():>+11,.0f}")


# ================================================== 3. THE LEVERAGE BAND
def leverage(window=FIVE) -> None:
    print("\n" + "=" * 100)
    print("3. THE LEVERAGE EACH BOOK IMPLIES — an OUTPUT of the stop, never "
          "a dial")
    print("   Leverage is the position divided by the account. Nothing here "
          "picks one: the size")
    print("   comes out of the stop and the leverage is whatever that size "
          "implies.")
    print("=" * 100)
    f = ae.frame(book(dict(al.BOOK), window))
    d = f[f["outcome"].isin(CLOSED)]

    print("\n  FOREX — OANDA practice, $100,000, flat 3% base risk scaled up "
          "by his quality dial")
    print(f"  {'':<10s} {'lev med':>9s} {'lev max':>9s} {'stop move':>11s} "
          f"{'broker ceiling':>15s} {'trades cut':>11s}")
    for inst in FOREX:
        s = d[d["instrument"] == inst]
        rate = OANDA_MARGIN_RATE[inst]
        ceiling = 1.0 / rate
        cut = int((s["leverage"] > ceiling).sum())
        print(f"  {inst:<10s} {s['leverage'].median():>8.1f}x "
              f"{s['leverage'].max():>8.1f}x "
              f"{s['stop_move_in_price_pct'].median():>10.2f}% "
              f"{ceiling:>14.0f}x {cut:>7d}/{len(s):<4d}")
    print("\n  The broker's ceiling is OANDA's own margin rate — 2% of a "
          "EUR/USD position and 5% of")
    print("  both pounds pairs on this account. When the stop asks for more "
          "than that will hold, the")
    print("  ALLOWANCE is scaled down so the size fits, and the message says "
          "so. It never grows one.")

    print("\n  GOLD — BloFin XAUT-USDT. The leverage on the CHART is one "
          "number; on the real")
    print(f"  ${BLOFIN_EQUITY:,.2f} stake with the money-game ladder on it is "
          f"another. Both are below.")
    s = d[d["instrument"] == GOLD]
    print(f"    on $100,000 at the flat 3%   "
          f"{s['leverage'].median():>5.1f}x median, "
          f"{s['leverage'].max():.1f}x max")
    share = al.money_game_share(BLOFIN_EQUITY, 2178.0)
    print(f"    the ladder at ${BLOFIN_EQUITY:,.2f}      "
          f"{100*share:.1f}% OF THE ACCOUNT per trade before his quality dial,"
          f" which is")
    print(f"    {' ':<32s}{share/al.RISK_PCT:.1f} times the flat 3% — so "
          f"{share/al.RISK_PCT*s['leverage'].median():.0f}x median leverage, "
          f"{share/al.RISK_PCT*s['leverage'].max():.0f}x at the top.")


# ============================================ 4. THE SHARED BLOFIN STAKE
def margin(window=FIVE) -> None:
    print("\n" + "=" * 100)
    print("4. ONE STAKE, TWO BOOKS — what the money-game ladder on gold "
          "costs in MARGIN")
    print("   The Craig crypto book and the gold book are ONE BloFin account "
          "and ONE $2,178 stake.")
    print("   Both read the venue's LIVE equity when they size, so a loss in "
          "either shrinks the next")
    print("   bet in both. What they cannot share is MARGIN, and the "
          "exchange is what mediates that.")
    print("=" * 100)
    import venue as vm
    share = vm.BlofinVenue.PER_TRADE_MARGIN_SHARE
    safety = vm.BlofinVenue.LIQUIDATION_SAFETY
    basis = BLOFIN_XAUT_MARK / OANDA_XAU_MID
    cfg = al.live_config(GOLD)

    print(f"\n  THE RULE THE EXCHANGE APPLIES, in one line: a position must "
          f"post enough margin that")
    print(f"  BloFin cannot liquidate it before the stop is reached, with "
          f"{safety:.0f}x room. That reduces")
    print(f"  to MARGIN >= {safety:.0f} x THE DOLLARS AT RISK, whatever the "
          f"stop's width.")

    r = ae.run_instrument(GOLD, *window, cfg=cfg, frames=frames(GOLD))
    for name, eng in (("ladder ON  (SHIPS)",
                       al.Engine(cfg_over=al.book_config(GOLD))),
                      ("flat 3%, for contrast", al.Engine(cfg_over=al.BOOK))):
        eng._cfg[GOLD] = cfg
        refused, margins, risks = 0, [], []
        for s in r["setups"]:
            cfgt = eng.cfg_at(GOLD, BLOFIN_EQUITY)
            tr = ae.manage(s, frames(GOLD)["15m"], cfgt, BLOFIN_EQUITY, 1.0)
            if tr is None:
                continue
            entry, stop = tr.entry * basis, tr.stop * basis
            units = tr.units / basis
            sm = abs(entry - stop) / entry
            lev = al.gold_leverage(BLOFIN_EQUITY, units * entry, sm,
                                   XAUT_MAX_LEVERAGE, share, safety)
            risks.append(tr.risk_dollars)
            if lev is None:
                refused += 1
            else:
                margins.append(units * entry / lev)
        n = len(r["setups"])
        print(f"\n  {name}")
        print(f"    median dollars at risk   ${np.median(risks):>8,.0f}  "
              f"({100*np.median(risks)/BLOFIN_EQUITY:.1f}% OF THE ACCOUNT)")
        if margins:
            print(f"    median margin posted     "
                  f"${np.median(margins):>8,.0f}  "
                  f"({100*np.median(margins)/BLOFIN_EQUITY:.0f}% OF THE "
                  f"ACCOUNT, range "
                  f"{100*np.min(margins)/BLOFIN_EQUITY:.0f}-"
                  f"{100*np.max(margins)/BLOFIN_EQUITY:.0f}%)")
        print(f"    setups the stake cannot carry  {refused:>3d} of {n} "
              f"({100*refused/n:.0f}%)")

    print("\n  WHAT THAT MEANS WHEN BOTH BOOKS WANT A POSITION AT ONCE.")
    print(f"  ONE BIG POSITION AT A TIME, and that is already the venue's own "
          f"stated trade-off rather")
    print(f"  than anything this book introduced. `venue.BlofinVenue."
          f"PER_TRADE_MARGIN_SHARE` is {share:.2f}, so")
    print(f"  ANY position on this account — the Craig book's or gold's — "
          f"posts up to {100*share:.0f}% of the")
    print(f"  stake as margin. While one is open there is not enough free "
          f"margin for a second, and")
    print("  nothing in this project arbitrates that. Nothing should: the "
          "exchange refuses the second")
    print("  order for lack of margin, the desk reports the refusal with the "
          "reason, and the setup is")
    print("  still decided, sized and recorded. FIRST SETUP GETS THE STAKE.")
    print("\n  WHAT THE LADDER ITSELF COSTS, separately from that: it is the "
          "refusal rate above. The")
    print(f"  ladder risks about {100*al.money_game_share(BLOFIN_EQUITY, 2178.0):.0f}"
          f"% OF THE ACCOUNT per trade before his quality dial, the dial "
          f"scales")
    print(f"  that up to twice, and the exchange needs {safety:.0f} times the "
          f"risk as margin — so past a quality")
    print(f"  of about {1.0/(safety*al.money_game_share(BLOFIN_EQUITY, 2178.0)):.2f} "
          f"the margin needed is more than the whole stake and the trade "
          f"cannot be")
    print("  held at all. That is the trade-off Wallace bought with \"ladder "
          "on gold too\", stated as a")
    print("  number rather than left to be discovered on a Tuesday morning.")


# ==================================================== 5. THE MESSAGES
def samples() -> None:
    print("\n" + "=" * 100)
    print("5. THE TWO MESSAGES, through the approved formatter, from setups "
          "that really fired")
    print("=" * 100)
    import tjr_desk
    for symbol in ("EUR/USD", "XAU/USD"):
        try:
            print("\n" + tjr_desk.alex_sample(symbol))
        except Exception as e:                               # noqa: BLE001
            print(f"\n  {symbol} sample unavailable: {str(e)[:200]}")


# ========================================================== THE DRIVER
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pick = [a for a in argv if a.startswith("--")]
    deep = "--deep" in argv
    window = FIVE if deep else YEAR

    print("=" * 100)
    print("step473 — THE ALEX ENGINE WIRED INTO THE LIVE DESK.")
    print("forex -> OANDA practice (EUR/USD, GBP/USD, GBP/JPY)   "
          "gold -> BloFin XAUT-USDT")
    print("Replay only. No order on any venue, no fetch, no write.")
    print("=" * 100)

    ran = False
    if not pick or "--agreement" in pick:
        agreement(window)
        ran = True
    if not pick or "--weekly" in pick:
        weekly()
        ran = True
    if not pick or "--leverage" in pick:
        leverage()
        ran = True
    if not pick or "--margin" in pick:
        margin()
        ran = True
    if not pick or "--samples" in pick:
        samples()
        ran = True
    if not ran:
        print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
