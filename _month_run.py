"""1 July -> 25 July 2026. Every market, every trade, decided causally."""
import pandas as pd, tjr_crypto as T, tjr_gold as G, tjr_replay as R

START, END = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-25")
ALL = ["BTC/USD","ETH/USD","SOL/USD","XRP/USD","DOGE/USD",
       "LINK/USD","AVAX/USD","LTC/USD","ADA/USD","DOT/USD"]
rows = []
def harvest(obj, mkt):
    out=[]
    def walk(x,d=0):
        if d>3: return
        if hasattr(x,"entry_t") and hasattr(x,"symbol"): out.append(x); return
        if isinstance(x,dict):
            for v in x.values(): walk(v,d+1)
        elif isinstance(x,(list,tuple)):
            for v in x: walk(v,d+1)
        else:
            for a in ("trades","closed","done"):
                if hasattr(x,a): walk(getattr(x,a),d+1)
    walk(obj)
    for t in out: rows.append((mkt,t))

T.install()
for p in ALL:
    try: harvest(T.run_pair(p,start=START,end=END,cfg=T.crypto_config(p),verbose=False),"crypto")
    except Exception as e: print(f"crypto {p}: {str(e)[:80]}")
G.install()
try: harvest(G.run_gold(start=START,end=END,verbose=False),"gold")
except Exception as e: print(f"gold: {str(e)[:90]}")
try: harvest(R.run(START,END,verbose=False),"sp500")
except Exception as e: print(f"sp500: {str(e)[:90]}")

rows.sort(key=lambda r: r[1].entry_t)
print(f"TRADES 1-25 JULY: {len(rows)}\n")
print(f"{'when':17} {'sym':9} {'side':6} {'risked':>8} {'cost':>8} {'P/L':>10} {'x risk':>7}")
print("-"*72)
for mkt,t in rows:
    side = "SHORT" if str(t.direction)=="-1" else "LONG"
    print(f"{t.entry_t:%a %d %b %H:%M}  {t.symbol:9} {side:6} "
          f"{t.risk_dollars:8,.0f} {t.cost:8,.0f} {t.pnl:+10,.0f} {t.r_multiple:+7.2f}")

# ---- per symbol, the thing that decides what to cut ----
import collections
by = collections.defaultdict(list)
for mkt,t in rows: by[t.symbol].append(t)
print("\n" + "="*78)
print(f"{'symbol':9} {'n':>3} {'won':>4} {'win%':>6} {'gross P/L':>11} {'cost paid':>10} {'NET':>11} {'net/trade':>10}")
print("-"*78)
tot = []
for sym, ts in sorted(by.items(), key=lambda kv: -sum(t.pnl for t in kv[1])):
    n=len(ts); w=sum(1 for t in ts if t.pnl>0)
    net=sum(t.pnl for t in ts); cost=sum(t.cost for t in ts)
    print(f"{sym:9} {n:3} {w:4} {w/n*100:5.0f}% {net+cost:+11,.0f} {cost:10,.0f} "
          f"{net:+11,.0f} {net/n:+10,.0f}")
    tot.append(net)
print("-"*78)
print(f"{'TOTAL':9} {len(rows):3} {sum(1 for m,t in rows if t.pnl>0):4} "
      f"{sum(1 for m,t in rows if t.pnl>0)/len(rows)*100:5.0f}% "
      f"{sum(t.pnl+t.cost for m,t in rows):+11,.0f} {sum(t.cost for m,t in rows):10,.0f} "
      f"{sum(tot):+11,.0f}")
