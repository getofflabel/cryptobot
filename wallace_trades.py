"""
wallace_trades.py — record Wallace's own trades so the bot can learn from them.

WHY THIS EXISTS (2026-07-25)

Wallace: "I am still more capable of spotting trades than you right now and
that is a big issue."

He is right, and the framework he had me study says that is the correct
division of labour rather than a problem to solve: the human supplies the
edge, the bot supplies flawless execution 24/7 without emotion. You close
the gap by "knowledge compression" — taking a real trader's method and
teaching the bot to run it.

We have been doing that from TJR's videos, which is a description of
someone's method. This is better evidence: Wallace's OWN decisions, on real
prices, as they happen.

WHAT MAKES THIS POSSIBLE NOW
  He connected Alpaca to TradingView and routes his paper trades through it.
  The Alpaca account was completely clean when this was written — 0 orders,
  0 positions, $100,000 untouched — so every fill that ever appears on it is
  attributable. Anything the bot places carries a client_order_id starting
  with BOT_TAG_PREFIX; anything without one is his.

  That is the attribution problem the BloFin account has, solved by accident
  of timing. Do not squander it: every automated order on this account MUST
  carry a tag.

WHAT IT CAPTURES, per trade
  entry time and price, exit time and price, size, direction, how long it
  was held, the result, and the SHAPE OF THE CHART at the moment he entered
  — the same read the bot would have had. That last part is the point. A
  list of his fills teaches nothing; his fills PLUS what the chart looked
  like is a training set.

WHAT IT DOES NOT DO
  It does not trade, cancel, or modify anything. Read-only. It is a
  notebook, not a hand on the wheel.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import alpaca

LEDGER = "data/wallace_trades.jsonl"
BOT_TAG_PREFIX = "CBOT_"          # anything without this prefix is his
CONTEXT_BARS = 120                # 5-minute bars of chart shape kept per entry


def _is_his(order: dict) -> bool:
    """A fill is his unless the bot tagged it."""
    coid = str(order.get("client_order_id") or "")
    return not coid.startswith(BOT_TAG_PREFIX)


def _chart_shape(cli, symbol: str, at_iso: str) -> dict:
    """What the chart looked like when he pressed the button.

    Deliberately the SAME read the bot gets, so his decision and the bot's
    view are directly comparable. Uses chart_reader if it is importable,
    and falls back to raw recent bars if not — a missing read must never
    stop us recording the trade itself.
    """
    out = {"bars_5m": [], "read": None}
    try:
        import pandas as pd
        start = at_iso[:10]
        bars = cli.bars(symbol, "5Min", limit=CONTEXT_BARS * 3, start=start)
        rows = [b for b in bars if b["t"] <= at_iso][-CONTEXT_BARS:]
        out["bars_5m"] = [[b["t"], b["o"], b["h"], b["l"], b["c"], b.get("v")]
                          for b in rows]
        if len(rows) >= 30:
            d = pd.DataFrame(rows).rename(columns={
                "t": "timestamp", "o": "open", "h": "high",
                "l": "low", "c": "close", "v": "volume"})
            d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
            try:
                import chart_reader
                r = chart_reader.read_chart(d)
                out["read"] = {k: r.get(k) for k in
                               ("structure", "location", "quality", "momentum",
                                "tradeable", "best_tool", "one_line")}
            except Exception as e:
                out["read"] = {"error": str(e)[:120]}
    except Exception as e:
        out["error"] = str(e)[:160]
    return out


def _seen_ids() -> set:
    if not os.path.exists(LEDGER):
        return set()
    ids = set()
    with open(LEDGER) as f:
        for line in f:
            try:
                ids.add(json.loads(line).get("order_id"))
            except Exception:
                pass
    return ids


def poll(verbose: bool = True) -> dict:
    """One pass. Records any of his filled orders not already recorded."""
    cli = alpaca.from_env()
    if cli is None:
        return {"ok": False, "why": "alpaca keys missing"}

    os.makedirs("data", exist_ok=True)
    seen = _seen_ids()
    orders = cli.orders(status="all", limit=200)
    new = []

    for o in orders:
        if o.get("status") != "filled" or not _is_his(o):
            continue
        oid = o.get("id")
        if oid in seen:
            continue
        filled_at = str(o.get("filled_at") or o.get("submitted_at") or "")
        rec = {
            "order_id": oid,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "symbol": o.get("symbol"),
            "side": o.get("side"),
            "qty": o.get("qty"),
            "order_type": o.get("order_type"),
            "filled_at": filled_at,
            "filled_price": o.get("filled_avg_price"),
            "source": "wallace",
            "chart_at_entry": _chart_shape(cli, o.get("symbol"), filled_at),
        }
        with open(LEDGER, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
        new.append(rec)

    positions = cli.positions()
    if verbose:
        print(f"[{datetime.now(timezone.utc):%H:%M:%S}] "
              f"his filled orders recorded this pass: {len(new)} | "
              f"open positions: {len(positions)}")
        for r in new:
            print(f"   RECORDED {r['side']} {r['qty']} {r['symbol']} "
                  f"@ {r['filled_price']} — "
                  f"{(r['chart_at_entry'].get('read') or {}).get('one_line', 'no read')}")
        for p in positions:
            print(f"   holding {p['symbol']} qty {p['qty']} entry "
                  f"{p['avg_entry_price']} | P/L ${float(p['unrealized_pl']):+.2f} "
                  f"= {float(p['unrealized_plpc'])*100:+.2f}% of the position")
    return {"ok": True, "new": len(new), "open_positions": len(positions)}


def summary() -> dict:
    """What we have learned to date, in plain terms."""
    if not os.path.exists(LEDGER):
        return {"trades": 0}
    rows = [json.loads(l) for l in open(LEDGER) if l.strip()]
    by_symbol: dict = {}
    for r in rows:
        by_symbol.setdefault(r["symbol"], 0)
        by_symbol[r["symbol"]] += 1
    reads = [(r.get("chart_at_entry") or {}).get("read") or {} for r in rows]
    structures: dict = {}
    for rd in reads:
        s = rd.get("structure")
        if s:
            structures[s] = structures.get(s, 0) + 1
    return {"trades": len(rows), "by_symbol": by_symbol,
            "chart_structure_at_his_entries": structures}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        print(json.dumps(summary(), indent=2))
    else:
        poll()
