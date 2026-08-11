"""
step479b_book_validation.py - ROUND 479, the check on the measurement

The recorder in step479 maintains the Bitnomial book INCREMENTALLY: one
snapshot on subscribe, then level updates applied on top. A bug in that
apply loop would not crash anything - it would quietly produce a stale book
and therefore a made-up spread, which is the worst possible failure for a
round whose entire output is a spread.

This opens a SECOND, INDEPENDENT websocket, takes a fresh snapshot, and
compares its top of book to what the running recorder just wrote. Agreement
within a few ticks (the price moves between the two reads) means the apply
loop is sound. Read-only. No account, no order.
"""
import asyncio, json, websockets

SPEC = {"PBTCUCZ50": 5.0, "PETHUIZ50": 0.2, "PSOLUSZ50": 0.01}

async def fresh():
    out = {}
    async with websockets.connect("wss://bitnomial.com/exchange/ws", open_timeout=20) as ws:
        await ws.send(json.dumps({"type":"subscribe","product_codes":[],
            "channels":[{"name":"book","product_codes":list(SPEC)}]}))
        while len(out) < 3:
            d = json.loads(await asyncio.wait_for(ws.recv(), timeout=25))
            if d.get("type") == "book" and d.get("symbol") in SPEC:
                t = SPEC[d["symbol"]]
                b = max(p for p,q in d["bids"] if q>0) * t
                a = min(p for p,q in d["asks"] if q>0) * t
                out[d["symbol"]] = (b, a)
    return out

f = asyncio.run(fresh())
rows = [json.loads(l) for l in open("data_usperp_book.jsonl")][-40:]
last = {}
for r in rows:
    if r["venue"] == "bitnomial_krakenUS":
        last[r["symbol"]] = (r["bid"], r["ask"], r["ts"])
print(f"{'symbol':12s} {'fresh bid/ask':>22s} {'recorder bid/ask':>22s}  agree?")
for s in SPEC:
    fb, fa = f[s]
    rb, ra, ts = last.get(s, (0,0,'-'))
    print(f"{s:12s} {fb:10.4f}/{fa:<10.4f} {rb:10.4f}/{ra:<10.4f}  "
          f"{'YES' if (abs(fb-rb)<=3*SPEC[s] and abs(fa-ra)<=3*SPEC[s]) else 'DRIFT'}  ({ts})")
