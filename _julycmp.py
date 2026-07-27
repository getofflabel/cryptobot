"""July 1-26 on Wallace's REAL BloFin equity, before and after the
no-destination refusal. Every trade, both runs."""
import dataclasses, pandas as pd, tjr_crypto as T, tjr_replay as R

EQ0 = 2037.10
START, END = pd.Timestamp("2026-07-01"), pd.Timestamp("2026-07-26")

def harvest(o):
    out=[]
    def w(x,d=0):
        if d>3: return
        if hasattr(x,"entry_t") and hasattr(x,"symbol"): out.append(x); return
        if isinstance(x,dict):
            for v in x.values(): w(v,d+1)
        elif isinstance(x,(list,tuple)):
            for v in x: w(v,d+1)
        else:
            for a in ("trades","closed","done"):
                if hasattr(x,a): w(getattr(x,a),d+1)
    w(o); return out

def run(refuse: bool):
    rows=[]
    T.install()
    for p in T.PAIRS:
        c = T.crypto_config(p)
        c = dataclasses.replace(c, refuse_when_nowhere_to_go=refuse)
        try: rows += [("crypto",t) for t in harvest(
            T.run_pair(p, start=START, end=END, cfg=c, verbose=False))]
        except Exception as e: print(f"  {p}: {str(e)[:60]}")
    try:
        cfg = dataclasses.replace(R.Config(), refuse_when_nowhere_to_go=refuse) \
              if hasattr(R, "Config") else None
        rows += [("sp500",t) for t in harvest(R.run(START, END, cfg=cfg, verbose=False))]
    except Exception as e: print(f"  sp500: {str(e)[:70]}")
    rows.sort(key=lambda r: r[1].entry_t)
    return rows

for label, refuse in (("BEFORE", False), ("AFTER", True)):
    rows = run(refuse)
    eq = EQ0
    print(f"\n{'='*104}\n{label} — {'refuses trades with nowhere to go' if refuse else 'takes every valid setup'}\n{'='*104}")
    print(f"{'#':>3} {'when':17} {'symbol':9} {'dir':6} {'lev':>6} {'targets':>8} "
          f"{'held':>8} {'outcome':22} {'P/L $':>8} {'equity':>9}")
    print("-"*104)
    for i,(mkt,t) in enumerate(rows,1):
        pl = eq*(t.pct_of_account/100.0); eq += pl
        stop_pct = abs(t.entry-t.stop)/t.entry
        lev = (0.01/stop_pct)/0.10
        held = str(t.exit_t-t.entry_t).replace(" days ","d ").replace(" day ","d ")
        print(f"{i:3} {t.entry_t:%a %d %b %H:%M} {t.symbol:9} "
              f"{'SHORT' if str(t.direction)=='-1' else 'LONG':6} {lev:5.0f}x "
              f"{len(t.targets):8} {held[:8]:>8} {str(t.outcome)[:22]:22} "
              f"{pl:+8.2f} {eq:9,.2f}")
    w = sum(1 for m,t in rows if t.pct_of_account>0)
    print("-"*104)
    print(f"{len(rows)} trades, {w} won ({w/max(1,len(rows))*100:.0f}%), "
          f"${EQ0:,.2f} -> ${eq:,.2f}  ({(eq/EQ0-1)*100:+.2f}%)")
