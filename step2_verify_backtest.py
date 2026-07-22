"""
step2_verify_backtest.py — prove the engine's math before trusting it.

We feed the backtester synthetic price data where the correct answer is
computable BY HAND, then check it produces exactly that answer. If an engine
cannot pass tests like these, every number it ever prints about a real
strategy is noise.

Run:  python3 step2_verify_backtest.py
"""

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest

PASS = FAIL = 0


def check(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    mark = "PASS" if ok else "FAIL"
    PASS += ok
    FAIL += not ok
    print(f"  [{mark}] {name}" + (f"  ({detail})" if detail else ""))


def make_candles(prices, start="2026-01-01 01:00"):
    """Bars where open=high=low=close=price. Starts at 01:00 so no funding
    timestamp (00/08/16 UTC) lands inside short tests unless we want it."""
    ts = pd.date_range(start, periods=len(prices), freq="1h", tz="UTC")
    p = np.asarray(prices, dtype=float)
    return pd.DataFrame({"timestamp": ts, "open": p, "high": p,
                         "low": p, "close": p, "volume": np.ones(len(p))})


COSTS = CostModel(fee_bps=6.0, half_spread_bps=1.0, slippage_bps=2.0,
                  funding_bps_8h=1.0)


print("=" * 64)
print("STEP 2 VERIFICATION — hand-checkable answers only")
print("=" * 64)

# ---- Test 1: flat signal means nothing happens -------------------------
print("\n[1] A flat strategy must change nothing")
c = make_candles([100] * 10)
r = run_backtest(c, pd.Series([0] * 10), COSTS, initial_equity=10_000)
check("zero trades", len(r.trades) == 0)
check("equity untouched", float(r.equity_curve.iloc[-1]) == 10_000)

# ---- Test 2: one round trip at constant price = exactly the cost hurdle -
print("\n[2] Round trip at constant $100 must lose EXACTLY the cost hurdle")
# Hand computation:
#   round trip hurdle = 2 x (6 + 1 + 2) = 18 bps of ~$10,000 notional = $18
#   buy 100 units:  fill 100 x 1.0003 = 100.03 -> cost 10,003 + fee 6.0018
#   sell 100 units: fill 100 x 0.9997 =  99.97 -> get  9,997  - fee 5.9982
#   net loss = 30 (friction) + 12 (fees) = $42? No: 10,003-9,997=6 spread+slip
#   on notional 10k: friction 2x3bps=6bps=$6... careful:
#   loss = (100.03 - 99.97) x 100 units + 6.0018 + 5.9982 = 6 + 12 = $18. Yes.
# Signal drops to 0 at index 2, so the exit fills at bar 3's open: the
# position is held through bars 1 and 2 = 2 hours of funding accrual
# = 2 x (1/8) x 1bp x $10k = $0.25 on top of the $18 hurdle.
signal = pd.Series([1, 1, 0, 0, 0])
c = make_candles([100] * 5)
r = run_backtest(c, signal, COSTS, initial_equity=10_000)
check("exactly one trade", len(r.trades) == 1)
expected_loss = -18.25
got = r.trades[0].pnl
check("trade pnl == -$18.25 (18 bps hurdle + 2h funding)",
      abs(got - expected_loss) < 0.01, f"got {got:+.4f}")
check("expectancy equals that single trade's pnl",
      abs(r.expectancy - got) < 1e-9)
check("final equity = 10,000 - 18.25",
      abs(float(r.equity_curve.iloc[-1]) - 9_981.75) < 0.01)

# ---- Test 3: no lookahead ----------------------------------------------
print("\n[3] A signal on bar N must fill at bar N+1's open, not bar N's price")
# Bar 0 trades at 100; bar 1 gaps up to 110. Signal fires on bar 0.
# A cheating engine buys at ~100. An honest one pays ~110 plus costs.
c = make_candles([100, 110, 110, 110])
r = run_backtest(c, pd.Series([1, 1, 1, 1]), COSTS, initial_equity=10_000)
entry = r.trades[0].entry_price
check("entry price is at the gapped-up open (~110.033), not 100",
      abs(entry - 110 * 1.0003) < 0.001, f"got {entry:.4f}")

# ---- Test 4: profits are net of costs, and costs are itemized -----------
print("\n[4] A winning trade must still pay full costs")
# Signal fires on bar 0, so it fills at BAR 1's open = 105 (no lookahead —
# the first version of this test forgot that and hand-computed entry at 100).
#   units      = 10,000 / 105 = 95.2381
#   entry fill = 105 x 1.0003 = 105.0315   exit fill = 120 x 0.9997 = 119.964
#   gross move = 95.2381 x (119.964 - 105.0315)          = $1,422.14
#   fees       = 6bps x (10,003.00 + 11,424.19)          = $12.86
#   friction   = 95.2381 x (0.0315 + 0.036)              = $6.43
#   funding    = held bars 1-3, 1bp/8 on closes 105/112/120 = $0.40
#   net        = 1,422.14 - 12.86 - 0.40                 = $1,408.89
c = make_candles([100, 105, 112, 120, 120])
r = run_backtest(c, pd.Series([1, 1, 1, 0, 0]), COSTS, initial_equity=10_000)
t = r.trades[0]
check("net pnl == $1,408.89", abs(t.pnl - 1_408.89) < 0.05,
      f"got {t.pnl:+.4f}")
check("fees itemized correctly (~$12.86)",
      abs(r.total_fees - 12.86) < 0.05, f"got {r.total_fees:.4f}")
check("friction itemized correctly (~$6.43)",
      abs(r.total_friction - 6.43) < 0.05, f"got {r.total_friction:.4f}")

# ---- Test 5: funding accrues with time held -----------------------------
print("\n[5] Holding a position must accrue funding in proportion to time")
# Enter at bar 1's open; the signal's final 0 lands on the last bar so the
# engine force-closes at the final close -> held through bars 1-19,
# i.e. 19 hourly bars x (1h/8h) x 1 bps of $10k = $2.375.
c = make_candles([100] * 20)
sig = pd.Series([1] * 19 + [0])
r = run_backtest(c, sig, COSTS, initial_equity=10_000)
check("19 held hours -> $2.375 funding",
      abs(r.total_funding - 2.375) < 0.02, f"got {r.total_funding:.4f}")
# The same bars relabeled as 4-hour bars = 76 held hours -> exactly 4x the
# funding ($9.50). This catches the old bug: per-timestamp charging that
# undercharged long-timeframe holds ~3x.
ts4 = pd.date_range("2026-01-01 01:00", periods=20, freq="4h", tz="UTC")
c4 = c.copy(); c4["timestamp"] = ts4
r4 = run_backtest(c4, sig, COSTS, initial_equity=10_000)
check("76 held hours on 4h bars -> $9.50 funding",
      abs(r4.total_funding - 9.5) < 0.05, f"got {r4.total_funding:.4f}")

# ---- Test 6: the engine refuses to run cost-free ------------------------
print("\n[6] There must be NO cost-free mode")
try:
    CostModel(fee_bps=0.0)
    check("CostModel(fee_bps=0) raises", False)
except ValueError:
    check("CostModel(fee_bps=0) raises", True)

# ---- Test 7: expectancy decomposition is internally consistent ----------
print("\n[7] expectancy == win_rate x avg_win - loss_rate x avg_loss")
# Mixed sequence of trades on varied prices.
prices = [100, 104, 99, 103, 108, 102, 106, 101, 105, 110, 103, 100]
sig = pd.Series([1, 0, 1, 1, 0, -1, -1, 0, 1, 0, -1, 0])
r = run_backtest(make_candles(prices), sig, COSTS, initial_equity=10_000)
lhs = r.expectancy
rhs = r.win_rate * r.avg_win - (1 - r.win_rate) * r.avg_loss
check("decomposition matches", abs(lhs - rhs) < 1e-6,
      f"{lhs:+.4f} vs {rhs:+.4f}, over {len(r.trades)} trades")

# ---- Test 8: maker execution -------------------------------------------
print("\n[8] Maker execution: limit fills, misses, and the chase")
# Flat market at 100: limits always touch (low == limit). Round trip pays
# maker fee both ways: 2 x 2bps of $10k = $4, plus 2 bars funding $0.25.
c = make_candles([100] * 5)
r = run_backtest(c, pd.Series([1, 1, 0, 0, 0]), COSTS,
                 initial_equity=10_000, execution="maker")
check("maker round trip at flat price loses exactly $4.25",
      abs(r.trades[0].pnl - (-4.25)) < 0.01, f"got {r.trades[0].pnl:+.4f}")
check("no friction booked on maker fills",
      r.total_friction == 0.0, f"got {r.total_friction:.4f}")

# Runaway market: signal on bar0 close (100), bar1 gaps to 110 and its low
# (110) never touches our 100 limit -> chase: taker at bar1 CLOSE 110 with
# spread+slip (110 x 1.0003) and 6bps fee. A cheating model would fill us
# at 100.
gap = make_candles([100, 110, 110, 110])
gap.loc[1, "low"] = 109                       # never came back to 100
r2 = run_backtest(gap, pd.Series([1, 1, 1, 1]), COSTS,
                  initial_equity=10_000, execution="maker")
check("missed limit chases at taker close (110.033), not the limit (100)",
      abs(r2.trades[0].entry_price - 110 * 1.0003) < 0.01,
      f"got {r2.trades[0].entry_price:.4f}")

# ---- Test 9: real funding cashflows -------------------------------------
print("\n[9] Real funding: longs pay positive rates, shorts COLLECT them")
# Constant price 100, real rate +2 bps/8h, 1h bars. A short held through
# bars 1-19 = 19 hours -> RECEIVES 19/8 x 2bps x $10k = +$4.75.
# Same maths for a long -> PAYS $4.75. The engine's default (always pay)
# would charge both. Costs use maker fills at flat price ($4 fees round
# trip) so funding is isolated cleanly:
#   short trade pnl = -4 fees + 4.75 funding = +$0.75
#   long  trade pnl = -4 fees - 4.75 funding = -$8.75
c = make_candles([100] * 20)
rate = pd.Series([2.0] * 20)
sig_short = pd.Series([-1] * 19 + [0])
rs = run_backtest(c, sig_short, COSTS, initial_equity=10_000,
                  execution="maker", funding_series=rate)
check("short at +2bps funding NETS +$0.75 (collects $4.75)",
      abs(rs.trades[0].pnl - 0.75) < 0.02, f"got {rs.trades[0].pnl:+.4f}")
sig_long = pd.Series([1] * 19 + [0])
rl = run_backtest(c, sig_long, COSTS, initial_equity=10_000,
                  execution="maker", funding_series=rate)
check("long at +2bps funding nets -$8.75 (pays $4.75)",
      abs(rl.trades[0].pnl - (-8.75)) < 0.02, f"got {rl.trades[0].pnl:+.4f}")

# ---- summary ------------------------------------------------------------
print("\n" + "=" * 64)
print(f"RESULT: {PASS} passed, {FAIL} failed")
print("=" * 64)
if FAIL == 0:
    print("The engine's arithmetic is trustworthy. Numbers it prints about")
    print("a real strategy now mean something.")
else:
    print("DO NOT USE the engine until every test passes.")
