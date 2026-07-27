"""Every trade this week, run through every margin/risk combination.

He never specifies leverage or how much margin to commit, so this is ours to
settle with data. What actually varies:
  risk %      -> how much each trade makes or loses. Real.
  margin %    -> how much capital each trade ties up, so how many can be
                 open at once. Trades that do not fit are SKIPPED.
  leverage    -> an output of the two. Never an input.
"""
import pandas as pd, tjr_crypto as T

START, END = pd.Timestamp("2026-07-19"), pd.Timestamp("2026-07-26")
EQ0 = 2037.10
T.install()

trades = []
for p in T.PAIRS + ["DOGE/USD", "AVAX/USD"]:
    try:
        r = T.run_pair(p, start=START, end=END, cfg=T.crypto_config(p), verbose=False)
        trades += list(r.get("trades", []))
    except Exception:
        pass
trades.sort(key=lambda t: t.entry_t)
print(f"{len(trades)} crypto setups this week\n")

def run(risk_pct, margin_pct):
    eq, open_pos, taken, skipped = EQ0, [], 0, 0
    for t in trades:
        open_pos = [o for o in open_pos if o[0] > t.entry_t]     # expire closed
        used = sum(o[1] for o in open_pos)
        marg = eq * margin_pct
        if used + marg > eq:                       # no capital free
            skipped += 1
            continue
        # his rule scales the result with risk; margin does not touch it
        pl = eq * (t.pct_of_account / 100.0) * (risk_pct / 0.01)
        eq += pl
        open_pos.append((t.exit_t, marg))
        taken += 1
    return eq, taken, skipped

print(f"{'risk':>6} {'margin':>8} {'max open':>9} {'taken':>6} {'skipped':>8} "
      f"{'equity after':>14} {'return':>9}")
print("-"*68)
best = None
for risk in (0.01, 0.02, 0.03):
    for margin in (0.05, 0.10, 0.20, 0.25, 0.50):
        eq, taken, skipped = run(risk, margin)
        ret = (eq/EQ0 - 1) * 100
        flag = ""
        if best is None or eq > best[0]:
            best = (eq, risk, margin); flag = ""
        print(f"{risk*100:5.0f}% {margin*100:7.0f}% {int(1/margin):9} {taken:6} "
              f"{skipped:8} {eq:14,.2f} {ret:+8.2f}%")
print("-"*68)
print(f"\nbest: risk {best[1]*100:.0f}% of the account, margin {best[2]*100:.0f}% "
      f"a trade -> ${best[0]:,.2f}")
