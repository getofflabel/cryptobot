"""
cost_truth.py — what a round trip ACTUALLY cost, from the exchange's own record.

WHY THIS EXISTS (2026-07-26)

Wallace: "theres a simple way to check this, and that is literally going
blofin and checking the realized pnl after a trade, it includes after fees."

He is right, and modelling the cost had already been wrong twice in one
night in two different directions:

  1. Crypto costs were measured against ALPACA's retail book while the
     trades execute on BLOFIN. Alpaca's crypto spread is 3 to 5 times wider
     — LTC was charged 0.699% when the real cost is nearer 0.14%. That one
     error turned a +$5,194 month into a -$11,794 one.
  2. Re-measuring against BloFin's book fixed the size of the error but not
     its nature: sampling the book five times and taking the MEDIAN says
     what the spread usually is, and you do not trade the usual spread. You
     trade whatever is there the moment you hit it. Checked against a real
     DOT round trip: modelled 0.242%, actually 0.363%.

BTC matched to three decimals both times, which is exactly why the error
survived — the pair we look at most is the pair with almost no spread.

THE RULE THIS FILE ENFORCES
    The exchange's own fill record is the truth. A modelled cost is a
    placeholder used only until real fills exist for that pair, and it is
    always labelled as such.

WHAT BLOFIN GIVES US, verified live 2026-07-26
    fee      charged per fill, EXACTLY 0.0600% of the position, every
             symbol, every size, no exceptions. Both sides, so 0.12% a
             round trip — which is the number the trader we copy quotes.
    fillPnl  realised profit on the closing fill, BEFORE fees.

So the true cost of a round trip is the fees on both fills plus whatever the
spread took out of the price, and both are in the record.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
FEE_PER_SIDE = 0.0006          # measured, not assumed. 0.06% each way.


def round_trips(client, symbol: str, contract_value: float) -> list[dict]:
    """Every completed in-and-out on `symbol`, with what it really cost.

    Pairs each closing fill with the opening fill before it. Only matched
    sizes are counted — a partial exit is not a round trip and guessing at
    one would put invented numbers into the very place we came here to stop
    inventing numbers.
    """
    fills = client.fills(symbol) or []
    out = []
    for i in range(len(fills) - 1):
        close, open_ = fills[i], fills[i + 1]        # newest first
        if close.get("side") == open_.get("side"):
            continue
        size = float(open_.get("fillSize") or 0)
        if not size or size != float(close.get("fillSize") or 0):
            continue
        p_in = float(open_["fillPrice"])
        p_out = float(close["fillPrice"])
        notional = p_in * size * contract_value
        if notional <= 0:
            continue
        fees = abs(float(open_.get("fee") or 0)) + abs(float(close.get("fee") or 0))
        moved = (p_out - p_in) * size * contract_value
        if open_.get("side") == "sell":
            moved = -moved
        out.append({
            "symbol": symbol,
            "size": size,
            "in": p_in,
            "out": p_out,
            "notional": notional,
            "fees": fees,
            "fees_pct": fees / notional * 100,
            "price_moved": moved,
            # the cost floor: fees always, plus the spread when the price
            # went against us in the moment it took to get in and out
            "cost": fees + (-moved if moved < 0 else 0.0),
            "cost_pct": (fees + (-moved if moved < 0 else 0.0)) / notional * 100,
        })
    return out


def measured_costs(client, pairs: dict) -> dict:
    """{pair: what its round trips really cost, as a share of the position}.

    `pairs` maps our name to (venue symbol, contract value). A pair with no
    completed round trips is ABSENT from the result rather than defaulted —
    the caller must fall back to a modelled number and say that it did.
    """
    got = {}
    for name, (sym, cv) in pairs.items():
        trips = round_trips(client, sym, cv)
        if not trips:
            continue
        pcts = sorted(t["cost_pct"] for t in trips)
        got[name] = {
            "round_trips": len(trips),
            "worst_pct": pcts[-1],
            "median_pct": pcts[len(pcts) // 2],
            # what we CHARGE: the worse half, because a cost model that is
            # right on average is wrong on exactly the trades that hurt
            "charge_pct": pcts[int(len(pcts) * 0.75)] if len(pcts) > 3 else pcts[-1],
            "source": "blofin fills, real",
        }
    return got


if __name__ == "__main__":
    from blofin_private import BlofinDemoPrivate, load_env
    env = load_env()
    c = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                          env["BLOFIN_DEMO_API_SECRET"],
                          env["BLOFIN_DEMO_PASSPHRASE"])
    specs = {"BTC/USD": ("BTC-USDT", 0.001), "DOT/USD": ("DOT-USDT", 1.0)}
    for name, (sym, cv) in specs.items():
        print(f"\n=== {name} ===")
        for t in round_trips(c, sym, cv):
            print(f"  {t['size']:>7.1f} @ {t['in']:<11.4f} -> {t['out']:<11.4f}  "
                  f"fees {t['fees_pct']:.4f}%   TOTAL COST {t['cost_pct']:.3f}% "
                  f"of the position")
    print("\nwhat we should charge:")
    print(json.dumps(measured_costs(c, specs), indent=1))
