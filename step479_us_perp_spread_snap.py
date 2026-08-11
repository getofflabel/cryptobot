"""
step479_us_perp_spread_snap.py - ROUND 479

HOW WIDE IS THE BOOK ON A US PERPETUAL CONTRACT?

Research only. READ-ONLY MARKET DATA. No account is opened, no key is used,
no order is placed, no money moves. Nothing in the live bot is touched.

READ THIS BEFORE THE NUMBERS: THIS ROUND CONSUMES NO LOOK
  This is not a backtest. It fits nothing, sweeps nothing and reads no
  out-of-sample slice. It is a measurement of a live order book, recorded to
  a file. No test window is touched, so no look is spent. What it can do is
  finish the cost picture R478 deliberately left half-open.

QUEUE ITEM 5, VERBATIM
  "HOW WIDE IS THE BOOK ON A US PERPETUAL CONTRACT? R478 priced the FEE and
   deliberately refused to guess the SPREAD. On a $370-$960 contract in a US
   perp market that is weeks-to-months old, the spread can plausibly exceed
   the fee outright: a 1-tick spread on a thin book can be 0.1435% of price
   on its own - the entire signal. Every number in R478 is therefore an upper
   bound on how good the venue is.
   Deliverable: top-of-book bid/ask and depth for PBTCUCZ50 / PETHIUZ50 /
   PSOLUZ50 (and the Coinbase nano perps), sampled across the 24h clock,
   recorded to a file. Median and tail spread in % of price, beside R478's
   fee table.
   Read-only market data. No account, no order, no money. If the venue cannot
   be polled without an account, say so and stop - do not open one."

CAN THE VENUES BE POLLED WITHOUT AN ACCOUNT? YES. BOTH OF THEM.
  Bitnomial (the exchange that lists Kraken Derivatives US's perps) publishes
  an unauthenticated WebSocket at wss://bitnomial.com/exchange/ws with a
  `book` channel that sends a full book snapshot on subscribe and level
  updates after. Its REST product specs are public too. No key, no login.
  Coinbase publishes an unauthenticated REST book at
  api.coinbase.com/api/v3/brokerage/market/product_book. No key, no login.
  So the queue item's escape hatch ("if it needs an account, stop") is not
  needed. Nothing was signed up for.

ONE SYMBOL CORRECTION
  The queue wrote PETHIUZ50 / PSOLUZ50. The live symbols on Bitnomial are
  PETHUIZ50 and PSOLUSZ50 (product ids 5608 and 5609). PBTCUCZ50 is correct.
  Confirmed against the public /product/specs/ endpoint, not guessed.

WHAT IS MEASURED
  Every `--interval` seconds, for each product:
    top-of-book bid, ask, their sizes, mid, spread in ticks, spread in $,
    spread as % of mid, and the depth (contracts and USD notional) resting
    within the top 5 price levels a side.
  Written one JSON object per line to data_usperp_book.jsonl so repeated runs
  at different times of day accumulate into 24h coverage rather than
  overwriting each other.

THE THREE VENUES, AND ONE OF THEM IS A CONTROL, NOT A CANDIDATE
  US-1  Bitnomial / Kraken Derivatives US  PBTCUCZ50 PETHUIZ50 PSOLUSZ50
        The product R478 priced. CFTC-regulated, US persons eligible.
  US-2  Coinbase Derivatives (CDE) perps   BIP/ETP/SLP-*-CDE
        Also US-person-legal. R478 flagged its fee as secondary-sourced.
  REF   Kraken INTERNATIONAL  PF_XBTUSD PF_ETHUSD PF_SOLUSD
        *** NOT AVAILABLE TO US PERSONS. NOT A CANDIDATE. ***
        Recorded ONLY as a control: it is a mature, deep perp book, so it
        says how much of any US spread is "young venue" versus "this is what
        a perp costs anywhere". R478 refused to blur these two products and
        so does this file.

PRICE UNITS ON BITNOMIAL - THE ONE THING THAT WOULD SILENTLY CORRUPT THIS
  The WebSocket quotes prices as INTEGER TICKS, not dollars. PBTCUCZ50 at
  12771 with a $5 price_increment is $63,855. Multiplying by the increment
  from the public spec endpoint is the only correct read; taking the integer
  at face value would put BTC at $12,771 and make every spread look 5x too
  wide. The increments are FETCHED, never hardcoded.

USAGE
  python3 step479_us_perp_spread_snap.py --minutes 75 --interval 20
  python3 step479_us_perp_spread_snap.py --report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_usperp_book.jsonl")

BITNOMIAL_REST = "https://bitnomial.com/exchange/api/v1/prod"
BITNOMIAL_WS = "wss://bitnomial.com/exchange/ws"
BITNOMIAL_SYMS = ["PBTCUCZ50", "PETHUIZ50", "PSOLUSZ50"]
BITNOMIAL_COIN = {"PBTCUCZ50": "BTC", "PETHUIZ50": "ETH", "PSOLUSZ50": "SOL"}

COINBASE_BOOK = "https://api.coinbase.com/api/v3/brokerage/market/product_book"
COINBASE_SYMS = {
    "BIP-20DEC30-CDE": "BTC",
    "ETP-20DEC30-CDE": "ETH",
    "SLP-20DEC30-CDE": "SOL",
}

KRAKEN_INTL = "https://futures.kraken.com/derivatives/api/v3/tickers"
KRAKEN_SYMS = {"PF_XBTUSD": "BTC", "PF_ETHUSD": "ETH", "PF_SOLUSD": "SOL"}

DEPTH_LEVELS = 5


def _get(url: str, timeout: int = 20):
    req = urllib.request.Request(url, headers={"User-Agent": "cryptobot-research/479"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# specs: tick size and contract size, fetched, never hardcoded
# --------------------------------------------------------------------------

def bitnomial_specs() -> dict:
    specs = _get(f"{BITNOMIAL_REST}/product/specs/?active=true", timeout=40)
    out = {}
    for s in specs:
        sym = s.get("symbol")
        if sym in BITNOMIAL_SYMS:
            out[sym] = {
                "tick": float(s["price_increment"]),
                "contract_size": float(s["contract_size"]),
                "unit": s.get("contract_size_unit"),
                "coin": BITNOMIAL_COIN[sym],
                "product_id": s.get("product_id"),
                "name": s.get("product_name"),
            }
    missing = [s for s in BITNOMIAL_SYMS if s not in out]
    if missing:
        raise SystemExit(f"bitnomial specs missing for {missing} - refusing to guess tick size")
    return out


# --------------------------------------------------------------------------
# book maths, shared by every venue
# --------------------------------------------------------------------------

def summarise(bids, asks, contract_size):
    """bids/asks are [(price_usd, qty_contracts), ...] best-first."""
    if not bids or not asks:
        return None
    bid, bid_qty = bids[0]
    ask, ask_qty = asks[0]
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / 2.0
    spread = ask - bid
    dbid = sum(q for _, q in bids[:DEPTH_LEVELS])
    dask = sum(q for _, q in asks[:DEPTH_LEVELS])
    return {
        "bid": bid,
        "ask": ask,
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        "mid": mid,
        "spread_abs": spread,
        "spread_pct": 100.0 * spread / mid,
        "top_bid_notional": bid_qty * contract_size * bid,
        "top_ask_notional": ask_qty * contract_size * ask,
        "depth5_bid_contracts": dbid,
        "depth5_ask_contracts": dask,
        "depth5_bid_notional": dbid * contract_size * bid,
        "depth5_ask_notional": dask * contract_size * ask,
        "contract_notional": contract_size * mid,
        # per-level book, kept so a later round can walk the book for a real
        # order size instead of assuming everything fills at the top.
        "levels_bid": [[p, q] for p, q in bids[:DEPTH_LEVELS]],
        "levels_ask": [[p, q] for p, q in asks[:DEPTH_LEVELS]],
    }


# --------------------------------------------------------------------------
# Bitnomial: maintain the book from snapshot + level updates
# --------------------------------------------------------------------------

class BitnomialBook:
    def __init__(self, specs):
        self.specs = specs
        self.bids = defaultdict(dict)   # sym -> {price_ticks: qty}
        self.asks = defaultdict(dict)
        self.ack = {}                   # sym -> int ack_id of last applied
        self.ready = set()

    def on_message(self, d):
        t = d.get("type")
        sym = d.get("symbol")
        if sym not in self.specs:
            return
        if t == "book":
            self.bids[sym] = {int(p): int(q) for p, q in (d.get("bids") or [])}
            self.asks[sym] = {int(p): int(q) for p, q in (d.get("asks") or [])}
            self.ack[sym] = int(d.get("ack_id", 0))
            self.ready.add(sym)
        elif t == "level" and sym in self.ready:
            ack = int(d.get("ack_id", 0))
            if ack <= self.ack.get(sym, 0):
                return          # stale relative to the snapshot, per the docs
            self.ack[sym] = ack
            price, qty = int(d["price"]), int(d["quantity"])
            side = self.bids[sym] if d.get("side") == "Bid" else self.asks[sym]
            if qty == 0:
                side.pop(price, None)
            else:
                side[price] = qty

    def snapshot(self, sym):
        if sym not in self.ready:
            return None
        spec = self.specs[sym]
        tick = spec["tick"]
        bids = sorted(((p * tick, q) for p, q in self.bids[sym].items() if q > 0), reverse=True)
        asks = sorted((p * tick, q) for p, q in self.asks[sym].items() if q > 0)
        s = summarise(bids, asks, spec["contract_size"])
        if s is None:
            return None
        s.update(venue="bitnomial_krakenUS", symbol=sym, coin=spec["coin"],
                 tick=tick, contract_size=spec["contract_size"],
                 spread_ticks=round(s["spread_abs"] / tick),
                 us_person_eligible=True)
        return s


# --------------------------------------------------------------------------
# Coinbase + Kraken international pollers
# --------------------------------------------------------------------------

def coinbase_sample(product_id, coin, contract_size_cache):
    d = _get(f"{COINBASE_BOOK}?product_id={product_id}&limit={DEPTH_LEVELS}")
    pb = d.get("pricebook") or {}
    bids = [(float(x["price"]), float(x["size"])) for x in pb.get("bids", [])]
    asks = [(float(x["price"]), float(x["size"])) for x in pb.get("asks", [])]
    cs = contract_size_cache.get(product_id, 1.0)
    s = summarise(bids, asks, cs)
    if s is None:
        return None
    s.update(venue="coinbase_CDE", symbol=product_id, coin=coin,
             contract_size=cs, us_person_eligible=True)
    return s


def coinbase_contract_sizes():
    """Contract size per nano/perp contract, read off the public product list."""
    out = {}
    try:
        d = _get("https://api.coinbase.com/api/v3/brokerage/market/products?product_type=FUTURE&limit=250", timeout=30)
        for p in d.get("products", []):
            pid = p.get("product_id")
            if pid in COINBASE_SYMS:
                fpd = p.get("future_product_details") or {}
                size = fpd.get("contract_size")
                out[pid] = float(size) if size else 1.0
    except Exception as e:                                   # pragma: no cover
        print(f"  ! coinbase contract sizes unavailable ({e}); notional left in contracts")
    return out


def kraken_intl_samples():
    """CONTROL ONLY. Not available to US persons. Never a candidate."""
    out = []
    try:
        d = _get(KRAKEN_INTL, timeout=20)
    except Exception:
        return out
    for t in d.get("tickers", []):
        sym = t.get("symbol")
        if sym not in KRAKEN_SYMS:
            continue
        bid, ask = t.get("bid"), t.get("ask")
        if not bid or not ask:
            continue
        s = summarise([(float(bid), float(t.get("bidSize") or 0))],
                      [(float(ask), float(t.get("askSize") or 0))], 1.0)
        if s is None:
            continue
        s.update(venue="kraken_INTL_CONTROL", symbol=sym, coin=KRAKEN_SYMS[sym],
                 contract_size=1.0, us_person_eligible=False)
        out.append(s)
    return out


# --------------------------------------------------------------------------
# recorder
# --------------------------------------------------------------------------

async def record(minutes: float, interval: float):
    import websockets

    specs = bitnomial_specs()
    print("Bitnomial perp specs (fetched, not hardcoded):")
    for sym, s in specs.items():
        print(f"  {sym:12s} id {s['product_id']:5d}  {s['contract_size']} {s['unit']}"
              f"  tick ${s['tick']}  ({s['name']})")

    cb_sizes = coinbase_contract_sizes()
    print(f"Coinbase contract sizes: {cb_sizes}")

    book = BitnomialBook(specs)
    deadline = time.time() + minutes * 60.0
    next_sample = time.time()
    written = 0

    fh = open(OUT, "a")
    try:
      while time.time() < deadline:
        # A dropped socket must not end the run - it must be re-subscribed.
        # The first version of this ended the recording silently on a drop and
        # lost an hour, which is exactly the kind of gap that would quietly
        # bias a spread measurement toward whichever minutes happened to work.
        try:
          async with websockets.connect(BITNOMIAL_WS, open_timeout=30,
                                        ping_interval=20, max_queue=None) as ws:
            await ws.send(json.dumps({
                "type": "subscribe",
                "product_codes": [],
                "channels": [{"name": "book", "product_codes": BITNOMIAL_SYMS}],
            }))
            while time.time() < deadline:
                # Drain the websocket until the next sample instant. The check
                # on next_sample is load-bearing: without it, a BUSY book keeps
                # returning messages before the timeout fires and the recorder
                # never samples at all - it samples only when the market goes
                # quiet, which is precisely backwards.
                while time.time() < next_sample:
                    try:
                        msg = await asyncio.wait_for(
                            ws.recv(), timeout=max(0.05, next_sample - time.time()))
                        book.on_message(json.loads(msg))
                    except asyncio.TimeoutError:
                        break

                ts = now_iso()
                rows = []
                for sym in BITNOMIAL_SYMS:
                    s = book.snapshot(sym)
                    if s:
                        rows.append(s)
                for pid, coin in COINBASE_SYMS.items():
                    try:
                        s = coinbase_sample(pid, coin, cb_sizes)
                        if s:
                            rows.append(s)
                    except Exception:
                        pass
                rows.extend(kraken_intl_samples())

                for r in rows:
                    r["ts"] = ts
                    fh.write(json.dumps(r) + "\n")
                fh.flush()
                written += len(rows)
                next_sample += interval
                if next_sample < time.time():
                    next_sample = time.time() + interval
                left = int(deadline - time.time())
                print(f"  {ts}  +{len(rows)} rows (total {written}), {left}s left", flush=True)
        except Exception as e:
            if time.time() < deadline:
                print(f"  ! websocket dropped ({e}); reconnecting", flush=True)
                book = BitnomialBook(specs)     # snapshot is stale; start clean
                await asyncio.sleep(3)
    finally:
        fh.close()
    print(f"\nwrote {written} rows to {OUT}")


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

# R478's published fee table, round trip as % of notional. Quoted, not re-derived.
R478_FEE_RT = {"BTC": 0.0463, "ETH": 0.0314, "SOL": 0.0811}
R478_SIGNAL_FULL = 0.1435     # R476 gross mean per entry, 2021-2026, % of price
R478_SIGNAL_2026 = 0.0387     # R476's 2026 stub
# R476's own structural stop per coin, % of price. Quoted, never re-derived.
R476_STOP = {"BTC": 0.185, "ETH": 0.239, "SOL": 0.341}


def pct(vals, q):
    vals = sorted(vals)
    if not vals:
        return float("nan")
    i = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return vals[i]


def report():
    if not os.path.exists(OUT):
        raise SystemExit(f"no data at {OUT} - run the recorder first")
    rows = []
    with open(OUT) as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    print(f"{len(rows)} samples in {OUT}")

    by_key = defaultdict(list)
    hours = defaultdict(set)
    for r in rows:
        by_key[(r["venue"], r["coin"])].append(r)
        hours[r["venue"]].add(r["ts"][11:13])

    print("\nUTC hours covered per venue (24h coverage is what the queue asked for):")
    for v, hs in sorted(hours.items()):
        print(f"  {v:22s} {len(hs):2d}/24  {sorted(hs)}")

    print("\n" + "=" * 100)
    print("SPREAD, IN % OF PRICE. one full spread is charged per round trip if both legs cross.")
    print("=" * 100)
    hdr = (f"{'venue':22s} {'coin':4s} {'n':>5s} {'median':>8s} {'mean':>8s} {'p75':>8s} "
           f"{'p90':>8s} {'p99':>8s} {'max':>8s} {'min':>8s}")
    print(hdr)
    stats = {}
    for (venue, coin), rs in sorted(by_key.items()):
        sp = [r["spread_pct"] for r in rs]
        stats[(venue, coin)] = {
            "n": len(sp), "median": statistics.median(sp), "mean": statistics.fmean(sp),
            "p75": pct(sp, 0.75), "p90": pct(sp, 0.90), "p99": pct(sp, 0.99),
            "max": max(sp), "min": min(sp),
        }
        s = stats[(venue, coin)]
        print(f"{venue:22s} {coin:4s} {s['n']:5d} {s['median']:8.4f} {s['mean']:8.4f} "
              f"{s['p75']:8.4f} {s['p90']:8.4f} {s['p99']:8.4f} {s['max']:8.4f} {s['min']:8.4f}")

    print("\n" + "=" * 100)
    print("THE FLOOR: WHAT ONE TICK IS WORTH. The queue's worry was that a single tick on a")
    print("thin book could be 0.1435% of price - the whole signal. This is that number, measured.")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'tick $':>10s} {'tick % of price':>16s} {'median spread in ticks':>24s}")
    for (venue, coin), rs in sorted(by_key.items()):
        if venue.startswith("kraken_INTL"):
            continue
        mid = statistics.median([r["mid"] for r in rs])
        ticks = [r["spread_ticks"] for r in rs if "spread_ticks" in r]
        if not ticks:      # coinbase rows carry no tick field; infer from the book
            tick = min((r["spread_abs"] for r in rs), default=float("nan"))
            ticks = [r["spread_abs"] / tick for r in rs] if tick and tick == tick else []
        else:
            tick = statistics.median([r["tick"] for r in rs])
        tick_pct = 100.0 * tick / mid
        mt = statistics.median(ticks) if ticks else float("nan")
        print(f"{venue:22s} {coin:4s} {tick:10.4f} {tick_pct:15.4f}% {mt:24.1f}")
    print("  NOTE the Coinbase tick is INFERRED as the smallest spread observed, because its")
    print("  public book does not publish the increment. Bitnomial's is the published spec.")

    print("\n" + "=" * 100)
    print("DEPTH AT THE TOP OF BOOK, AND WITHIN 5 LEVELS (median USD notional)")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'contract $':>11s} {'top bid $':>11s} {'top ask $':>11s} "
          f"{'5-lvl bid $':>12s} {'5-lvl ask $':>12s}")
    for (venue, coin), rs in sorted(by_key.items()):
        if venue.startswith("kraken_INTL"):
            continue      # sizes are in coin, not contracts; not comparable
        med = lambda k: statistics.median([r.get(k, 0) or 0 for r in rs])
        print(f"{venue:22s} {coin:4s} {med('contract_notional'):11,.0f} "
              f"{med('top_bid_notional'):11,.0f} {med('top_ask_notional'):11,.0f} "
              f"{med('depth5_bid_notional'):12,.0f} {med('depth5_ask_notional'):12,.0f}")

    print("\n" + "=" * 100)
    print("HOW BIG CAN THE ACCOUNT BE BEFORE IT MOVES THE BOOK IT IS TRADING?")
    print("R478: at 1% risked on the pooled 0.242% stop, position notional is 4.13x equity.")
    print("A position that exceeds the resting depth pays more than the measured spread.")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'top-of-book $':>14s} {'-> equity $':>12s} "
          f"{'5 levels $':>12s} {'-> equity $':>12s}")
    for (venue, coin), rs in sorted(by_key.items()):
        if venue.startswith("kraken_INTL"):
            continue
        top = statistics.median([min(r["top_bid_notional"], r["top_ask_notional"]) for r in rs])
        d5 = statistics.median([min(r["depth5_bid_notional"], r["depth5_ask_notional"]) for r in rs])
        print(f"{venue:22s} {coin:4s} {top:14,.0f} {top/4.13:12,.0f} {d5:12,.0f} {d5/4.13:12,.0f}")
    print("  'equity' = the account size whose 1%-risked position exactly consumes that depth.")
    print("  Above it the fill is worse than the top of book and the spread table understates cost.")
    print("  R478's separate floor still applies: below ~$5,000 contract rounding eats the saving.")

    print("\n" + "=" * 100)
    print("THE ANSWER TO THE QUEUE ITEM: FEE + SPREAD, AGAINST THE SIGNAL")
    print("R478 priced the fee. This round prices the spread. All-in = fee + one median spread.")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'R478 fee RT':>12s} {'spread':>9s} {'ALL-IN':>9s} "
          f"{'vs full sig':>12s} {'vs 2026 sig':>12s}")
    for (venue, coin), s in sorted(stats.items()):
        if venue.startswith("kraken_INTL"):
            continue
        fee = R478_FEE_RT.get(coin, float("nan"))
        allin = fee + s["median"]
        print(f"{venue:22s} {coin:4s} {fee:12.4f} {s['median']:9.4f} {allin:9.4f} "
              f"{R478_SIGNAL_FULL - allin:+12.4f} {R478_SIGNAL_2026 - allin:+12.4f}")
    print("\n  'vs sig' columns are NET % of price per entry: signal minus all-in cost.")
    print(f"  R476 signal, whole window 2021-2026: +{R478_SIGNAL_FULL:.4f}% of price per entry.")
    print(f"  R476 signal, 2026 stub only:         +{R478_SIGNAL_2026:.4f}%.")
    print("  Coinbase's fee is quoted here at the Kraken US rate because R478 could only")
    print("  source Coinbase's per-contract component secondarily. Its SPREAD is measured.")

    print("\n" + "=" * 100)
    print("THE SAME COST IN STOP DISTANCES - the unit R478 used, and the one that decides")
    print("whether the method can be run. Stop = R476's own structural stop for that coin.")
    print("=" * 100)
    print(f"{'venue':22s} {'coin':4s} {'stop %':>8s} {'fee':>8s} {'spread':>8s} {'ALL-IN':>8s} {'in stops':>10s}")
    for (venue, coin), s in sorted(stats.items()):
        if venue.startswith("kraken_INTL"):
            continue
        fee = R478_FEE_RT.get(coin, float("nan"))
        stop = R476_STOP.get(coin, float("nan"))
        allin = fee + s["median"]
        print(f"{venue:22s} {coin:4s} {stop:8.3f} {fee:8.4f} {s['median']:8.4f} {allin:8.4f} "
              f"{allin/stop:10.2f}x")
    print("  R478 reported the fee alone at 0.13-0.25 stop distances, against Alpaca's 2.0-2.7.")
    print("  This column is the honest replacement: fee AND spread, in the same unit.")

    walk = [r for r in rows if r.get("levels_ask") and not r["venue"].startswith("kraken_INTL")]
    if walk:
        print("\n" + "=" * 100)
        print("WALKING THE BOOK: what a real order actually pays, not what the top of book quotes")
        print("Cost = volume-weighted fill vs mid, one side, doubled for a round trip. % of price.")
        print("=" * 100)
        print(f"{'venue':22s} {'coin':4s} {'$10k RT':>9s} {'$50k RT':>9s} {'$100k RT':>9s} {'unfilled':>10s}")
        wk = defaultdict(list)
        for r in walk:
            wk[(r["venue"], r["coin"])].append(r)
        for (venue, coin), rs in sorted(wk.items()):
            line = f"{venue:22s} {coin:4s}"
            short = 0
            for target in (10_000, 50_000, 100_000):
                costs = []
                for r in rs:
                    cs, mid = r["contract_size"], r["mid"]
                    need, coins = target, 0.0        # need = notional still to buy
                    for p, q in r["levels_ask"]:
                        take = min(need, p * q * cs)  # $ available at this price
                        coins += take / p
                        need -= take
                        if need <= 1e-9:
                            break
                    if need > 1e-9:
                        short += 1
                        continue
                    vwap = target / coins
                    costs.append(200.0 * (vwap - mid) / mid)   # both legs
                line += f" {statistics.median(costs):9.4f}" if costs else f" {'n/a':>9s}"
            print(line + f" {short:10d}")
        print("  'unfilled' counts samples where the order exceeded the 5 recorded levels;")
        print("  those are EXCLUDED from the medians, so this table is optimistic where it is blank.")

    ctrl = {c: st for (v, c), st in stats.items() if v.startswith("kraken_INTL")}
    us = {c: st for (v, c), st in stats.items() if v == "bitnomial_krakenUS"}
    if ctrl and us:
        print("\n" + "=" * 100)
        print("CONTROL: how much of the US spread is 'young venue' vs 'this is what a perp costs'")
        print("Kraken INTERNATIONAL is NOT available to US persons and is NOT a candidate.")
        print("=" * 100)
        for coin in sorted(us):
            if coin in ctrl:
                print(f"  {coin:4s} US {us[coin]['median']:.4f}%  vs  offshore "
                      f"{ctrl[coin]['median']:.4f}%   ratio {us[coin]['median']/max(ctrl[coin]['median'],1e-9):5.1f}x")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=60.0)
    ap.add_argument("--interval", type=float, default=20.0)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        asyncio.run(record(a.minutes, a.interval))


if __name__ == "__main__":
    main()
