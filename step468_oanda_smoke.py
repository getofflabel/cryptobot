#!/usr/bin/env python3
"""
step468_oanda_smoke.py — "did the OANDA token work", answered in one command.

    python3 step468_oanda_smoke.py
    python3 oanda_api.py --smoke          # the same thing, shorter to type

IT PLACES NOTHING. NOT ONE ORDER, EVER.

    No market order, no limit order, no stop, no cancel, no modification.
    Every call it makes is a GET. It does not even construct the venue's
    sealed client, so there is no code path from here to an order even if
    something went wrong. You can run it on a Sunday, twice, with a position
    open, and nothing about the account changes.

    Wallace's account ends the night with zero orders placed by us. This
    script is how that stays true while still proving the plumbing works.

WHAT IT CHECKS, IN ORDER, STOPPING AT THE FIRST THING THAT IS NOT TRUE

  1. the two keys are present: OANDA_API_TOKEN and OANDA_ACCOUNT_ID
  2. the token authenticates
  3. this is a PRACTICE account, proved twice over — the host we are pointed
     at says so AND the account number agrees. A disagreement stops here.
  4. the account summary reads back: balance, net asset value, open trades
  5. all four instruments exist, and each one's pip size, price precision,
     minimum size and size step read back FROM THE BROKER. A pip is 0.0001
     on the dollar majors and 0.01 on a yen cross; nothing may trade an
     instrument whose spec could not be read.
  6. candles come back for all four instruments at every timeframe
  7. how far back the archive actually reaches, measured rather than assumed

IT CREATES NO ACCOUNT AND NO KEY. That part is Wallace's, and .env.example
has the exact steps.
"""

from __future__ import annotations

import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oanda_api as ox                                         # noqa: E402

PAIRS = ["GBP/JPY", "GBP/USD", "EUR/USD", "XAU/USD"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

OK, BAD, MEH = "  ok  ", " FAIL ", " note "

# The two names, spelled once here and read from the client module, so this
# message and the code can never drift apart.
RENDER_VARS = (ox.TOKEN_KEY, ox.ACCOUNT_KEY)


def line(mark: str, text: str) -> None:
    print(f"[{mark}] {text}", flush=True)


def _keys_help() -> None:
    print()
    print("  Set them in TWO places, not one:")
    print("    LOCAL   ~/cryptobot/.env")
    for name in RENDER_VARS:
        print(f"                {name}=...")
    print("            (.env.example has the exact signup steps)")
    print()
    print("    RENDER  dashboard -> the cryptobot service -> Environment")
    print("            -> Add Environment Variable -> Save (this redeploys)")
    for name in RENDER_VARS:
        print(f"                {name}")
    print()
    print("  Keys that existed only on the laptop have silently broken the")
    print("  cloud worker twice. Both places, same values, every time.")


def smoke() -> int:
    print("=" * 74)
    print("  OANDA PRACTICE — SMOKE TEST. Reads only. Places nothing.")
    print("=" * 74)

    missing = ox.missing_keys()
    if missing:
        line(BAD, f"not configured: {', '.join(missing)} is not set")
        _keys_help()
        return 1
    line(OK, f"{ox.TOKEN_KEY} and {ox.ACCOUNT_KEY} are set locally")
    line(MEH, "this cannot see Render. Confirm the SAME two values are in "
              "the Render dashboard under Environment before trusting the "
              "cloud worker.")

    cli = ox.from_env(practice=True)
    if cli is None:
        line(BAD, "the client would not build from the environment")
        _keys_help()
        return 1

    env = cli.environment_check()
    if not env["agrees"]:
        line(BAD, env["note"])
        line(BAD, f"host = {env['host']} ({env['client_says']}), "
                  f"account {env['account_id']} = {env['account_id_says']}")
        print("\n  Nothing trades until that is resolved. An account number")
        print("  starting 001- is a LIVE account and the wrong one here; a")
        print("  practice account starts 101-.")
        return 1
    line(OK, f"practice confirmed twice over: host {env['host']}, account "
             f"{env['account_id']} (site 101 = practice)")

    try:
        s = cli.summary()
    except ox.OandaError as e:
        line(BAD, f"the token did not authenticate: {str(e)[:200]}")
        return 1
    line(OK, f"the token works. Balance {float(s.get('balance') or 0):,.2f} "
             f"{s.get('currency')}, net asset value "
             f"{float(s.get('NAV') or 0):,.2f}, "
             f"{int(s.get('openTradeCount') or 0)} open trade(s), "
             f"hedging {'ON' if s.get('hedgingEnabled') else 'off'}")
    if int(s.get("openTradeCount") or 0):
        line(MEH, "there are open trades on this account. The bot will treat "
                  "every one of them as HIS and refuse to open on those "
                  "instruments — that is the attribution rule working, not a "
                  "fault.")

    bad = 0
    print()
    print("  THE FOUR INSTRUMENTS, AND THEIR CONVENTIONS, FROM THE BROKER:")
    for pair in PAIRS:
        inst = ox.INSTRUMENTS[pair]
        try:
            spec = cli.spec(inst)
        except ox.OandaError as e:
            line(BAD, f"{pair}: {str(e)[:140]}")
            bad += 1
            continue
        if not spec:
            line(BAD, f"{pair}: the instrument spec could not be read, so "
                      f"nothing may trade it")
            bad += 1
            continue
        line(OK, f"{pair} -> {inst}: one pip is {spec['pip']:g}, prices go to "
                 f"{spec['display_precision']} decimals, smallest size "
                 f"{spec['minimum_units']:g} units, size step "
                 f"10^-{spec['units_precision']}")

    print()
    print("  CANDLES, AT EVERY TIMEFRAME:")
    for pair in PAIRS:
        inst = ox.INSTRUMENTS[pair]
        got = []
        for tf in TIMEFRAMES:
            try:
                f = cli.frame(inst, ox.GRANULARITY[tf], count=200)
            except ox.OandaError as e:
                line(BAD, f"{pair} {tf}: {str(e)[:140]}")
                bad += 1
                continue
            if not len(f):
                line(BAD, f"{pair} {tf}: no candles came back")
                bad += 1
                continue
            got.append(f"{tf}={len(f)}")
        if got:
            line(OK, f"{pair}: {', '.join(got)} bars")

    print()
    print("  HOW FAR BACK THE ARCHIVE REACHES (measured, not assumed):")
    for tf in ("1m", "5m", "1h", "1d"):
        try:
            f = cli.frame(ox.INSTRUMENTS["GBP/USD"], ox.GRANULARITY[tf],
                          start=dt.datetime(2005, 1, 3), count=5)
        except ox.OandaError as e:
            print(f"    GBP/USD {tf:>3}: could not be read ({str(e)[:80]})")
            continue
        if len(f):
            print(f"    GBP/USD {tf:>3}: back to {f['t'].iloc[0]} New York")
        else:
            print(f"    GBP/USD {tf:>3}: nothing that far back")

    print()
    print("=" * 74)
    if bad:
        print(f"  {bad} check(s) failed. Nothing should trade currencies "
              f"until they pass.")
        print("=" * 74)
        return 1
    print("  Everything the venue needs is present. NO ORDER WAS PLACED.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    raise SystemExit(smoke())
