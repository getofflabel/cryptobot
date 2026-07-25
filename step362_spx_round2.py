"""
step362_spx_round2.py — the S&P bot's SECOND research round.

The index has had exactly one round. Bitcoin has had fifty. This closes
part of that gap and, more importantly, runs the Round-117 gate on the two
things we already believed.

RESEARCH ONLY. No orders. No live bot file is touched.

WHAT THIS ROUND DOES

  FAMILY A — the honesty check on what we already believe.
    The index has spent most of its history going up. So an "edge" whose
    exit simply rides a rising market will look profitable even if the
    entry rule picks moments at random. Round 117 killed two strategies on
    other markets with exactly this test. We run it here on both of the
    S&P bot's existing edges: the RSI2 deep-dip buy and the "stay long
    while price is above the 200-day average" rule.
    Method: keep the exit, the dates, the costs and the number of entries
    identical, but choose the entry days at random. 400 draws. If the real
    rule cannot beat what random entry timing produces, the entry rule is
    decoration.
    Two random pools, because they answer different questions:
      "anywhere"  = entries drawn from any day in the window.
      "uptrend"   = entries drawn only from days when price is already
                    above the 200-day average. This is the harsh one: it
                    asks whether the DIP part adds anything on top of the
                    TREND part.

  FAMILY B — turn-of-month, built into an actual strategy for the first
    time. Round 60 only measured it (average daily move about 3x the rest
    of the month). Measuring is not trading. Here it is a costed rule:
    buy at the close E trading days before month end, hold H trading days,
    market orders both ends. Swept over E and H, with and without the
    above-the-200-day-average filter. Random-entry control on every
    survivor, using the same hold length.

  FAMILY C — is the dip-buy a broad plateau or one lucky spike? Round 60
    tested one RSI setting. Here the whole neighbourhood is mapped: RSI
    length 2/3/4, threshold 2 through 20, trend filter 100-day or 200-day
    average or none.

  FAMILY D — shapes that survived on OTHER markets, re-derived here.
    Every constant is recomputed from the S&P's own price behaviour and
    both the original and the re-derived number are printed. The S&P's
    average daily range is about 1.32% of price; Bitcoin's HOURLY range is
    0.45-0.9% and gold's hourly is 0.28-0.72%. Porting a constant across
    that gap is how you get a strategy that never triggers or never stops
    triggering.
      D1 vol-gated trend  (Bitcoin, 4-hour bars, gate at 1.5% range)
      D2 breakout         (gold, daily, 20-day channel, exit on 20-day average)
      D3 hidden bullish divergence (Bitcoin, 4-hour bars)

  FAMILY E — does it still work on a different market? Every survivor
    replays unchanged on the Nasdaq tracker (QQQ) and the S&P futures
    (ES=F), and is re-priced at the cost of the ONE venue that could
    actually trade it today (BloFin's SPY-USDT perpetual, measured
    2026-07-25), not just at stock-broker costs.

SPLITS: 60% of history to choose on, the next 20% read exactly once, the
final 20% never loaded this round.
MINIMUMS: 30 trades in the first slice, 8 in the middle slice, else the
cell is reported as NOT ENOUGH TRADES.
EXECUTION: market orders on every fill, every time (execution="taker").

PAPER ONLY. There is no account anywhere that can place these trades
today. That does not lower the bar; it decides what is worth a venue.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from strategy import atr, rsi
from step43_daytrade import MIN_TRAIN_TRADES, MIN_VAL_TRADES, split_points
from step48_tradfi_trend import event_long

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------------------
# costs — three different worlds, stated in plain percent
# ---------------------------------------------------------------------------
# A "bp" is one hundredth of one percent. Every number below is also given
# as a plain percent of the full size of the position, both fills included.

# US stock broker on the ETF: 0.04% of position size for a round trip.
ETF_COSTS = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                      slippage_bps=1.0, funding_bps_8h=0.0)
# CME futures: 0.02% of position size for a round trip.
FUT_COSTS = CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                      slippage_bps=0.5, funding_bps_8h=0.0)
# BloFin's SPY-USDT perpetual, the only venue on earth that lists an
# S&P tracker our bot's existing code could reach. Measured live
# 2026-07-25: quoted spread 0.0013% of price (so half of it is 0.00065%),
# BloFin market-order fee 0.06% per fill. Slippage charged at 0.01% per
# fill as a conservative guess because we have never filled there.
# Round trip = 0.1413% of position size, three and a half times the ETF.
PERP_COSTS = CostModel(fee_bps=6.0, maker_fee_bps=2.0, half_spread_bps=0.065,
                       slippage_bps=1.0, funding_bps_8h=0.0)

COSTS = {"SPY": ETF_COSTS, "ES": FUT_COSTS, "QQQ": ETF_COSTS}
RT = {k: v.round_trip_bps() / 100.0 for k, v in
      {"SPY": ETF_COSTS, "ES": FUT_COSTS, "QQQ": ETF_COSTS}.items()}
PERP_RT = PERP_COSTS.round_trip_bps() / 100.0

DRAWS = 400          # random-entry draws per control
RNG_SEED = 20260725


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def load(tag: str) -> pd.DataFrame:
    return pd.read_parquet(f"/Users/wallacechen/cryptobot/data_spx_{tag}_1d.parquet")


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


# ---------------------------------------------------------------------------
# scoring helpers
# ---------------------------------------------------------------------------

def run_slice(d, sig, costs, lo, hi, stop_pct=None):
    return run_backtest(
        d.iloc[lo:hi].reset_index(drop=True),
        sig.iloc[lo:hi].reset_index(drop=True),
        costs=costs, execution="taker", stop_pct=stop_pct,
    )


def pct_of_position(res) -> float:
    """Average profit per trade, losers included, as a percent of the FULL
    size of the position. This is the number that has to beat the cost of
    trading."""
    if not res.trades:
        return 0.0
    return float(np.mean([t.pnl / (t.entry_price * t.units) * 100
                          for t in res.trades]))


def verdict(tr, va) -> str:
    if tr.expectancy > 0 and va.expectancy > 0:
        if len(tr.trades) >= MIN_TRAIN_TRADES and len(va.trades) >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "NOT ENOUGH TRADES"
    return "FAIL"


def row(family, config, symbol, tr, va, rt_pct, extra=None):
    tr_pct = pct_of_position(tr)
    va_pct = pct_of_position(va)
    r = {
        "family": family, "config": config, "symbol": symbol,
        "train_trades": len(tr.trades),
        "train_$per_trade": round(tr.expectancy, 2),
        "train_pct_of_position": round(tr_pct, 4),
        "train_cost_multiple": round(tr_pct / rt_pct, 2) if rt_pct else np.nan,
        "train_win_pct": round(tr.win_rate * 100, 1),
        "train_worst_drop_pct": round(tr.max_drawdown_pct, 1),
        "val_trades": len(va.trades),
        "val_$per_trade": round(va.expectancy, 2),
        "val_pct_of_position": round(va_pct, 4),
        "val_cost_multiple": round(va_pct / rt_pct, 2) if rt_pct else np.nan,
        "val_win_pct": round(va.win_rate * 100, 1),
        "verdict": verdict(tr, va),
    }
    if extra:
        r.update(extra)
    return r


# ---------------------------------------------------------------------------
# THE ROUND-117 GATE: random entries, same exit, same dates, same costs
# ---------------------------------------------------------------------------

def random_entry_control(d, exit_cond, n_entries, pool_mask, lo, hi, costs,
                         max_hold=0, draws=DRAWS, seed=RNG_SEED, stop_pct=None):
    """Replace the entry rule with coin flips and keep everything else.

    n_entries : how many entry days to draw, matched to how many the real
                rule fired in this window.
    pool_mask : which days are allowed to be drawn.
    Returns the distribution of average profit per trade (dollars), the
    average number of trades a draw produced, and the same in percent of
    the full position size.
    """
    rng = np.random.default_rng(seed)
    pool = np.flatnonzero(pool_mask.to_numpy()[lo:hi]) + lo
    if len(pool) < 5 or n_entries < 1:
        return None
    k = min(n_entries, len(pool))
    dollars, pcts, counts, totals = [], [], [], []
    for _ in range(draws):
        picks = rng.choice(pool, size=k, replace=False)
        enter = pd.Series(False, index=d.index)
        enter.iloc[picks] = True
        sig = event_long(d, enter, exit_cond, max_hold)
        res = run_slice(d, sig, costs, lo, hi, stop_pct=stop_pct)
        if not res.trades:
            continue
        dollars.append(res.expectancy)
        pcts.append(pct_of_position(res))
        counts.append(len(res.trades))
        totals.append(res.total_return_pct)
    if not dollars:
        return None
    return {"dollars": np.array(dollars), "pcts": np.array(pcts),
            "totals": np.array(totals), "mean_trades": float(np.mean(counts))}


def control_report(name, real_res, ctrl, rt_pct):
    """One line of plain English plus the numbers."""
    if ctrl is None:
        print(f"    {name}: control could not be built")
        return None
    real_d = real_res.expectancy
    real_p = pct_of_position(real_res)
    real_t = real_res.total_return_pct
    d, t = ctrl["dollars"], ctrl["totals"]
    pct_rank = float((d < real_d).mean() * 100)
    tot_rank = float((t < real_t).mean() * 100)
    print(f"    {name}:")
    print(f"      real rule     {real_d:+9.2f} $/trade  "
          f"({real_p:+.4f}% of position, {real_p / rt_pct:5.2f}x the cost of trading), "
          f"{len(real_res.trades)} trades, {real_t:+.1f}% grown over the window")
    print(f"      random entry  {d.mean():+9.2f} $/trade average  "
          f"({ctrl['pcts'].mean():+.4f}% of position), "
          f"{ctrl['mean_trades']:.0f} trades per draw, "
          f"{t.mean():+.1f}% grown, {len(d)} draws")
    print(f"      random spread per trade   5th {np.percentile(d, 5):+8.2f}  "
          f"50th {np.percentile(d, 50):+8.2f}  95th {np.percentile(d, 95):+8.2f}")
    print(f"      random spread total grown 5th {np.percentile(t, 5):+8.1f}%  "
          f"50th {np.percentile(t, 50):+8.1f}%  95th {np.percentile(t, 95):+8.1f}%")
    print(f"      PER TRADE:  real sits at the {pct_rank:.1f}th place out of 100 "
          f"random tries -> {'BEATS CHANCE' if pct_rank >= 95 else 'DOES NOT BEAT CHANCE'}")
    print(f"      TOTAL GROWN: real sits at the {tot_rank:.1f}th place out of 100 "
          f"random tries -> {'BEATS CHANCE' if tot_rank >= 95 else 'DOES NOT BEAT CHANCE'}")
    print("      (the two can disagree when the coin-flip rule ends up taking a")
    print("       very different NUMBER of trades; total grown is the fair one then)")
    return {"real_dollars": real_d, "real_pct": real_p, "real_total_pct": real_t,
            "random_mean_dollars": float(d.mean()),
            "random_mean_pct": float(ctrl["pcts"].mean()),
            "random_mean_total_pct": float(t.mean()),
            "random_5th": float(np.percentile(d, 5)),
            "random_50th": float(np.percentile(d, 50)),
            "random_95th": float(np.percentile(d, 95)),
            "random_total_5th": float(np.percentile(t, 5)),
            "random_total_50th": float(np.percentile(t, 50)),
            "random_total_95th": float(np.percentile(t, 95)),
            "percentile_of_real_per_trade": pct_rank,
            "percentile_of_real_total": tot_rank,
            "real_trades": len(real_res.trades),
            "random_mean_trades": ctrl["mean_trades"]}


# ---------------------------------------------------------------------------
# the two things we already believe
# ---------------------------------------------------------------------------

def dipbuy_exit(d):
    """Round 60's exit, unchanged: close back above the 5-day average, or
    the 2-day RSI snaps above 65."""
    return ((d["close"] > sma(d["close"], 5)) | (rsi(d["close"], 2) > 65)).fillna(False)


def build_rsi2_dip(d, thresh=5, trend=200):
    close = d["close"]
    enter = ((rsi(close, 2) < thresh) & (close > sma(close, trend))).fillna(False)
    return enter, dipbuy_exit(d)


def build_regime(d, trend=200):
    close = d["close"]
    above = (close > sma(close, trend)).fillna(False)
    return above, (~above)


def family_a(frames, splits, out_rows, out_ctrl):
    print("\n" + "=" * 78)
    print("FAMILY A — THE HONESTY CHECK on the two edges we already believe")
    print("=" * 78)
    print("The index rose for most of its history. An exit that just sits in a")
    print("rising market makes money on its own. So: keep the exit, keep the")
    print("dates, keep the costs, keep the number of entries, and choose the")
    print("entry days by coin flip instead. If the rule cannot beat that, the")
    print("rule is decoration.\n")

    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]
        i_tr, i_va = splits[tag]["i_tr"], splits[tag]["i_va"]
        costs, rt = COSTS[tag], RT[tag]
        close = d["close"]
        above200 = (close > sma(close, 200)).fillna(False)
        warm = pd.Series(np.arange(len(d)) >= 220, index=d.index)

        print(f"\n  {tag}: choosing window = first {i_tr} days "
              f"({d.timestamp.iloc[0]:%Y-%m-%d} to {d.timestamp.iloc[i_tr - 1]:%Y-%m-%d}), "
              f"cost of a round trip {rt:.4f}% of position size")

        # --- edge 1: the RSI2 deep-dip buy -------------------------------
        enter, exit_c = build_rsi2_dip(d, 5, 200)
        sig = event_long(d, enter, exit_c, 0)
        tr = run_slice(d, sig, costs, 0, i_tr)
        va = run_slice(d, sig, costs, i_tr, i_va)
        out_rows.append(row("A-existing-edge", "RSI2<5 dip buy, above 200-day avg",
                            tag, tr, va, rt))
        n_ent = int(enter.iloc[:i_tr].sum())
        print(f"\n  [1] RSI2 below 5 while above the 200-day average "
              f"({n_ent} entry days fired in the choosing window)")
        for pool_name, pool in (("random day anywhere", warm),
                                ("random day, already above the 200-day avg",
                                 above200 & warm)):
            ctrl = random_entry_control(d, exit_c, n_ent, pool, 0, i_tr, costs)
            rep = control_report(pool_name, tr, ctrl, rt)
            if rep:
                rep.update({"symbol": tag, "edge": "RSI2<5 dip buy",
                            "pool": pool_name, "slice": "train"})
                out_ctrl.append(rep)

        # --- edge 2: stay long above the 200-day average ------------------
        above, below = build_regime(d, 200)
        sig2 = event_long(d, above, below, 0)
        tr2 = run_slice(d, sig2, costs, 0, i_tr)
        va2 = run_slice(d, sig2, costs, i_tr, i_va)
        out_rows.append(row("A-existing-edge", "long while above 200-day avg",
                            tag, tr2, va2, rt))
        n_ent2 = max(len(tr2.trades), 1)
        print(f"\n  [2] Long the whole time price is above the 200-day average "
              f"({len(tr2.trades)} trades in the choosing window)")
        ctrl2 = random_entry_control(d, below, n_ent2, above & warm, 0, i_tr, costs)
        rep = control_report("random day, already above the 200-day avg", tr2, ctrl2, rt)
        if rep:
            rep.update({"symbol": tag, "edge": "long above 200-day avg",
                        "pool": "random day above 200-day avg", "slice": "train"})
            out_ctrl.append(rep)

        # buy and hold, for scale
        hold = pd.Series(1.0, index=d.index)
        bh = run_slice(d, hold, costs, 0, i_tr)
        print(f"      for scale, buying once and never selling over the same "
              f"window returned {bh.total_return_pct:+.1f}% "
              f"with a worst fall of {bh.max_drawdown_pct:.1f}%; "
              f"the rule returned {tr2.total_return_pct:+.1f}% "
              f"with a worst fall of {tr2.max_drawdown_pct:.1f}%")


# ---------------------------------------------------------------------------
# FAMILY B — turn of month, as a real strategy
# ---------------------------------------------------------------------------

def month_position(d):
    """For each day: how many trading days remain in its calendar month
    (0 = it is the last trading day of the month), and which trading day
    of the month it is (0 = first)."""
    ts = d["timestamp"].dt.tz_convert("America/New_York")
    per = ts.dt.to_period("M")
    grp = per.to_numpy()
    df = pd.DataFrame({"g": grp})
    day_of_month = df.groupby("g").cumcount()
    size = df.groupby("g")["g"].transform("size").to_numpy()
    days_left = pd.Series(size - 1 - day_of_month.to_numpy(), index=d.index)
    return days_left, pd.Series(day_of_month.to_numpy(), index=d.index)


def family_b(frames, splits, out_rows, out_ctrl):
    print("\n" + "=" * 78)
    print("FAMILY B — TURN OF MONTH, built into a strategy for the first time")
    print("=" * 78)
    print("Round 60 measured it and stopped. Measuring is not trading. Rule:")
    print("buy at the close E trading days before the month ends, hold H")
    print("trading days, market order both ends, full costs.\n")

    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]
        i_tr, i_va = splits[tag]["i_tr"], splits[tag]["i_va"]
        costs, rt = COSTS[tag], RT[tag]
        days_left, _ = month_position(d)
        close = d["close"]
        above200 = (close > sma(close, 200)).fillna(False)
        warm = pd.Series(np.arange(len(d)) >= 220, index=d.index)
        no_exit = pd.Series(False, index=d.index)

        print(f"\n  {tag}  (cost of a round trip {rt:.4f}% of position size)")
        best = None
        for E in (1, 2, 3, 4, 5):
            for H in (2, 3, 4, 5, 6, 7, 8):
                for fname, filt in (("no filter", warm),
                                    ("only above 200-day avg", above200 & warm)):
                    enter = ((days_left == E) & filt).fillna(False)
                    sig = event_long(d, enter, no_exit, H)
                    tr = run_slice(d, sig, costs, 0, i_tr)
                    va = run_slice(d, sig, costs, i_tr, i_va)
                    cfg = f"buy {E} days before month end, hold {H} days, {fname}"
                    r = row("B-turn-of-month", cfg, tag, tr, va, rt,
                            extra={"E": E, "H": H, "filter": fname})
                    out_rows.append(r)
                    if r["verdict"] == "SURVIVOR" and (
                            best is None or r["train_pct_of_position"] >
                            best[0]["train_pct_of_position"]):
                        best = (r, enter, H, tr, va, filt)

        surv = [r for r in out_rows
                if r["family"] == "B-turn-of-month" and r["symbol"] == tag]
        n_s = sum(1 for r in surv if r["verdict"] == "SURVIVOR")
        print(f"    {len(surv)} settings tested, {n_s} kept working on the middle slice")
        top = sorted([r for r in surv if r["verdict"] == "SURVIVOR"],
                     key=lambda r: -r["train_pct_of_position"])[:5]
        for r in top:
            print(f"      {r['config']:58s} "
                  f"choose-slice {r['train_$per_trade']:+7.2f}$/t "
                  f"({r['train_pct_of_position']:+.4f}% of position, "
                  f"{r['train_cost_multiple']:.1f}x cost, n={r['train_trades']})  "
                  f"middle-slice {r['val_$per_trade']:+7.2f}$/t "
                  f"({r['val_pct_of_position']:+.4f}%, n={r['val_trades']})")

        if best is not None:
            r, enter, H, tr, va, filt = best
            print(f"\n    Round-117 gate on the best one ({r['config']}):")
            n_ent = int(enter.iloc[:i_tr].sum())
            for pool_name, pool in (("random day anywhere", warm),
                                    ("random day, already above the 200-day avg",
                                     above200 & warm)):
                ctrl = random_entry_control(d, no_exit, n_ent, pool, 0, i_tr,
                                            costs, max_hold=H)
                rep = control_report(pool_name, tr, ctrl, rt)
                if rep:
                    rep.update({"symbol": tag, "edge": r["config"],
                                "pool": pool_name, "slice": "train"})
                    out_ctrl.append(rep)


# ---------------------------------------------------------------------------
# FAMILY C — is the dip buy a plateau or a spike?
# ---------------------------------------------------------------------------

def family_c(frames, splits, out_rows):
    print("\n" + "=" * 78)
    print("FAMILY C — IS THE DIP BUY A BROAD PLATEAU OR ONE LUCKY SETTING?")
    print("=" * 78)
    print("Round 60 tested one RSI setting and called it the cleanest edge of")
    print("the round. If only that one setting works, it is luck. If the whole")
    print("neighbourhood works, it is real.\n")

    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]
        i_tr, i_va = splits[tag]["i_tr"], splits[tag]["i_va"]
        costs, rt = COSTS[tag], RT[tag]
        close = d["close"]
        exit_c = dipbuy_exit(d)
        grid = {}
        for n in (2, 3, 4):
            r_n = rsi(close, n)
            for th in (2, 5, 8, 10, 15, 20):
                for tname, tfilt in (("200-day", (close > sma(close, 200))),
                                     ("100-day", (close > sma(close, 100))),
                                     ("none", pd.Series(True, index=d.index))):
                    enter = ((r_n < th) & tfilt).fillna(False)
                    sig = event_long(d, enter, exit_c, 0)
                    tr = run_slice(d, sig, costs, 0, i_tr)
                    va = run_slice(d, sig, costs, i_tr, i_va)
                    cfg = f"RSI{n} below {th}, trend filter {tname}"
                    r = row("C-dipbuy-family", cfg, tag, tr, va, rt,
                            extra={"rsi_n": n, "thresh": th, "filter": tname})
                    out_rows.append(r)
                    grid[(n, th, tname)] = r

        print(f"\n  {tag} — average profit per trade in the choosing window, "
              f"as a percent of the full size of the position")
        for tname in ("200-day", "100-day", "none"):
            print(f"    trend filter: {tname}")
            print("      RSI len |" + "".join(f"{th:>9d}" for th in (2, 5, 8, 10, 15, 20)))
            for n in (2, 3, 4):
                cells = []
                for th in (2, 5, 8, 10, 15, 20):
                    g = grid[(n, th, tname)]
                    mark = "" if g["train_trades"] >= MIN_TRAIN_TRADES else "*"
                    cells.append(f"{g['train_pct_of_position']:>8.3f}{mark}")
                print(f"      {n:>7d} |" + "".join(cells))
            print("      (* = fewer than 30 trades, not enough to judge)")


# ---------------------------------------------------------------------------
# FAMILY D — shapes borrowed from other markets, constants re-derived
# ---------------------------------------------------------------------------

def hidden_bull_divergence(d, rsi_n=14, lookback=20, trend=100):
    """Price makes a HIGHER low while the RSI makes a LOWER low, inside an
    uptrend. Bitcoin runs this on 4-hour bars; here it is daily bars."""
    close, low = d["close"], d["low"]
    r = rsi(close, rsi_n)
    prior_low = low.shift(1).rolling(lookback).min()
    prior_rsi_low = r.shift(1).rolling(lookback).min()
    is_local_low = (low == low.rolling(5, center=False).min())
    enter = (is_local_low & (low > prior_low) & (r < prior_rsi_low)
             & (close > sma(close, trend))).fillna(False)
    return enter


def family_d(frames, splits, out_rows, out_ctrl):
    print("\n" + "=" * 78)
    print("FAMILY D — SHAPES THAT WORKED ON OTHER MARKETS, NUMBERS RE-DERIVED")
    print("=" * 78)

    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]
        i_tr, i_va = splits[tag]["i_tr"], splits[tag]["i_va"]
        costs, rt = COSTS[tag], RT[tag]
        close = d["close"]
        atr_pct = (atr(d, 14) / close * 100)
        med_atr = float(atr_pct.iloc[:i_tr].median())
        warm = pd.Series(np.arange(len(d)) >= 260, index=d.index)
        above200 = (close > sma(close, 200)).fillna(False)

        print(f"\n  {tag}: the S&P's own average daily range in the choosing "
              f"window is {med_atr:.3f}% of price.")
        print(f"    Bitcoin's vol gate was 1.5% on FOUR-HOUR bars and gold's "
              f"hourly range runs 0.28-0.72%. Porting 1.5% onto daily S&P bars "
              f"would gate on a level this market clears "
              f"{float((atr_pct.iloc[:i_tr] > 1.5).mean()) * 100:.0f}% of days, "
              f"which is a different rule entirely. So the gate is re-derived "
              f"as multiples of {med_atr:.3f}%.")

        # ---- D1 vol-gated trend ----------------------------------------
        for fast, slow in ((20, 100), (50, 200)):
            for mult in (0.0, 0.8, 1.0, 1.25, 1.5):
                gate_level = mult * med_atr
                trend_up = (sma(close, fast) > sma(close, slow))
                lively = (atr_pct >= gate_level)
                want = (trend_up & lively & warm).fillna(False)
                sig = event_long(d, want, ~want, 0)
                tr = run_slice(d, sig, costs, 0, i_tr)
                va = run_slice(d, sig, costs, i_tr, i_va)
                cfg = (f"D1 trend {fast}/{slow} day avgs, only when daily range "
                       f"above {gate_level:.3f}% ({mult:g}x this market's own median)")
                out_rows.append(row("D1-vol-gated-trend", cfg, tag, tr, va, rt,
                                    extra={"gate_pct": round(gate_level, 4),
                                           "orig_constant": "1.5% on BTC 4-hour bars"}))

        # ---- D2 breakout (gold's edge) ----------------------------------
        for lb in (10, 20, 30, 40, 55):
            for exit_ma in (10, 20, 40):
                hi = close.shift(1).rolling(lb).max()
                enter = ((close > hi) & warm).fillna(False)
                exit_c = (close < sma(close, exit_ma)).fillna(False)
                sig = event_long(d, enter, exit_c, 0)
                tr = run_slice(d, sig, costs, 0, i_tr)
                va = run_slice(d, sig, costs, i_tr, i_va)
                cfg = (f"D2 buy a new {lb}-day high, sell when price drops "
                       f"below the {exit_ma}-day average")
                out_rows.append(row("D2-breakout", cfg, tag, tr, va, rt,
                                    extra={"lookback": lb, "exit_ma": exit_ma,
                                           "orig_constant": "20-day channel, "
                                                            "20-day exit on gold daily"}))

        # ---- D3 hidden bullish divergence -------------------------------
        for rsi_n in (7, 14):
            for lb in (10, 20, 40):
                enter = hidden_bull_divergence(d, rsi_n, lb, 100) & warm
                exit_c = dipbuy_exit(d)
                sig = event_long(d, enter.fillna(False), exit_c, 0)
                tr = run_slice(d, sig, costs, 0, i_tr)
                va = run_slice(d, sig, costs, i_tr, i_va)
                cfg = (f"D3 higher low in price with a lower low in RSI{rsi_n} "
                       f"over {lb} days, inside an uptrend")
                out_rows.append(row("D3-hidden-divergence", cfg, tag, tr, va, rt,
                                    extra={"rsi_n": rsi_n, "lookback": lb,
                                           "orig_constant": "BTC 4-hour bars"}))

        for fam in ("D1-vol-gated-trend", "D2-breakout", "D3-hidden-divergence"):
            sub = [r for r in out_rows if r["family"] == fam and r["symbol"] == tag]
            good = [r for r in sub if r["verdict"] == "SURVIVOR"]
            print(f"    {fam}: {len(good)} of {len(sub)} settings still worked "
                  f"on the middle slice")
            for r in sorted(good, key=lambda r: -r["train_pct_of_position"])[:3]:
                print(f"       {r['config'][:72]:72s} "
                      f"{r['train_pct_of_position']:+.4f}% of position "
                      f"({r['train_cost_multiple']:.1f}x cost, n={r['train_trades']}) "
                      f"-> middle {r['val_pct_of_position']:+.4f}% (n={r['val_trades']})")

        # Round-117 gate on the best setting of EACH borrowed shape
        for fam in ("D1-vol-gated-trend", "D2-breakout", "D3-hidden-divergence"):
            borrowed = [r for r in out_rows
                        if r["family"] == fam and r["symbol"] == tag
                        and r["verdict"] == "SURVIVOR"]
            if not borrowed:
                print(f"\n    {fam}: nothing survived on {tag}, no control needed")
                continue
            b = max(borrowed, key=lambda r: r["train_pct_of_position"])
            print(f"\n    Round-117 gate on {tag}'s best {fam}: {b['config']}")
            if fam == "D2-breakout":
                lb, ema = b["lookback"], b["exit_ma"]
                hi = close.shift(1).rolling(lb).max()
                enter = ((close > hi) & warm).fillna(False)
                exit_c = (close < sma(close, ema)).fillna(False)
                n_ent = int(enter.iloc[:i_tr].sum())
            elif fam == "D3-hidden-divergence":
                enter = (hidden_bull_divergence(d, b["rsi_n"], b["lookback"], 100)
                         & warm).fillna(False)
                exit_c = dipbuy_exit(d)
                n_ent = int(enter.iloc[:i_tr].sum())
            else:
                # D1 is a STATE ("in the trend and lively"), not an event.
                # Its coin-flip twin enters on a random day and holds until
                # that same state ends. Because the state is off most days,
                # a random entry made while the state is already off exits
                # the very next day, so the coin-flip version racks up many
                # tiny trades. That is why the per-trade comparison is
                # meaningless here and only the total-grown one is read.
                gate = b["gate_pct"]
                fast, slow = (20, 100) if "20/100" in b["config"] else (50, 200)
                want = ((sma(close, fast) > sma(close, slow))
                        & (atr_pct >= gate) & warm).fillna(False)
                enter, exit_c = want, (~want)
                n_ent = max(b["train_trades"], 1)
            sig = event_long(d, enter, exit_c, 0)
            tr = run_slice(d, sig, costs, 0, i_tr)
            pools = (("random day anywhere", warm),
                     ("random day, already above the 200-day avg", above200 & warm))
            if fam == "D1-vol-gated-trend":
                # only draw from days the state is ON, so the coin-flip
                # version takes trades of a comparable length
                pools = (("random day while the trend state is on", enter),)
            for pool_name, pool in pools:
                ctrl = random_entry_control(d, exit_c, n_ent, pool, 0, i_tr, costs)
                rep = control_report(pool_name, tr, ctrl, rt)
                if rep:
                    rep.update({"symbol": tag, "edge": b["config"],
                                "family": fam, "pool": pool_name, "slice": "train"})
                    out_ctrl.append(rep)


# ---------------------------------------------------------------------------
# FAMILY E — re-price the survivors at the only venue that could trade them
# ---------------------------------------------------------------------------

def family_f(frames, splits, out_rows):
    """Where does the stop go, and can it survive the overnight gap?

    House rule: the stop goes where the chart says the idea is wrong, which
    for a long is under the last confirmed swing low. The backtest engine
    only accepts ONE stop distance as a percent, not a per-trade price, so
    we do the honest next-best thing: measure, on the choosing slice only,
    how far the last confirmed swing low actually sat below the entry price
    on the days this rule fires, and use the middle of that distribution as
    the stop distance. The distance is therefore READ OFF THE CHART, not
    swept for the best answer.

    Then the hard part for a stock: the ETF is dark for about 17.5 hours
    every night. We count how often the overnight move alone was bigger
    than that stop, because a stop that the gap jumps straight over is not
    a stop.
    """
    from step41_shorts import confirmed_swings

    print("\n" + "=" * 78)
    print("FAMILY F — WHERE THE STOP GOES, AND WHETHER THE OVERNIGHT GAP EATS IT")
    print("=" * 78)

    for tag in ("SPY", "ES", "QQQ"):
        d = frames[tag]
        i_tr, i_va = splits[tag]["i_tr"], splits[tag]["i_va"]
        costs, rt = COSTS[tag], RT[tag]
        close = d["close"]
        above200 = (close > sma(close, 200)).fillna(False)
        warm = pd.Series(np.arange(len(d)) >= 220, index=d.index)
        days_left, _ = month_position(d)
        no_exit = pd.Series(False, index=d.index)

        # overnight gap size, in percent of price
        gap_pct = ((d["open"] - close.shift(1)).abs() / close.shift(1) * 100)
        gap_dn = ((close.shift(1) - d["open"]) / close.shift(1) * 100)

        for k in (3, 5):
            _, swing_low = confirmed_swings(d, k)
            last_low = swing_low.ffill()
            dist = (close - last_low) / close * 100     # percent below entry

            for rule_name, enter in (
                    ("RSI2 below 5 while above the 200-day average",
                     ((rsi(close, 2) < 5) & above200).fillna(False)),
                    ("buy 4 days before month end",
                     ((days_left == 4) & warm).fillna(False))):
                sel = dist.iloc[:i_tr][enter.iloc[:i_tr]].dropna()
                sel = sel[sel > 0]
                if len(sel) < 10:
                    continue
                stop_pct = float(sel.median())
                gapped = float((gap_dn.iloc[:i_tr] > stop_pct).mean() * 100)
                print(f"\n  {tag} | {rule_name} | swing window {k} bars")
                print(f"    the last confirmed swing low sat a middle distance of "
                      f"{stop_pct:.2f}% below the entry price "
                      f"(quarter-way {sel.quantile(0.25):.2f}%, "
                      f"three-quarter-way {sel.quantile(0.75):.2f}%), n={len(sel)}")
                print(f"    on {gapped:.1f}% of all days in the choosing window the "
                      f"overnight fall ALONE was bigger than that stop distance, "
                      f"so the stop would have been jumped over, not filled")
                print(f"    average overnight move: {gap_pct.iloc[:i_tr].mean():.2f}% "
                      f"of price; days the overnight move exceeded 0.3%: "
                      f"{float((gap_pct.iloc[:i_tr] > 0.3).mean() * 100):.1f}%")

                exit_c = (dipbuy_exit(d) if rule_name.startswith("RSI2") else no_exit)
                hold = 0 if rule_name.startswith("RSI2") else 8
                for label, sp in (("no stop", None),
                                  (f"stop {stop_pct:.2f}% below entry", stop_pct)):
                    sig = event_long(d, enter, exit_c, hold)
                    tr = run_slice(d, sig, costs, 0, i_tr, stop_pct=sp)
                    va = run_slice(d, sig, costs, i_tr, i_va, stop_pct=sp)
                    r = row("F-structure-stop", f"{rule_name} | swing{k} | {label}",
                            tag, tr, va, rt)
                    out_rows.append(r)
                    print(f"      {label:34s} choosing slice "
                          f"{r['train_pct_of_position']:+.4f}% of position "
                          f"({r['train_cost_multiple']:5.1f}x cost, n={r['train_trades']})"
                          f"  middle slice {r['val_pct_of_position']:+.4f}% "
                          f"(n={r['val_trades']})  {r['verdict']}")

                # what leverage that stop implies, stated as an OUTPUT
                for risk in (1.0, 2.0):
                    lev = risk / stop_pct
                    print(f"      risking {risk:.0f}% of the account on this trade "
                          f"means a position {lev:.1f} times the account, because "
                          f"size = dollars risked divided by stop distance")


def family_e(out_rows):
    print("\n" + "=" * 78)
    print("FAMILY E — WHAT SURVIVES AT THE COST OF THE ONLY REACHABLE VENUE")
    print("=" * 78)
    print(f"A US stock broker charges about {RT['SPY']:.4f}% of position size for a")
    print(f"round trip on the ETF. CME futures cost about {RT['ES']:.4f}%. BloFin's")
    print(f"SPY-USDT perpetual, measured live on 2026-07-25, costs about "
          f"{PERP_RT:.4f}%")
    print("of position size for a round trip, which is three and a half times the")
    print("ETF. Profit must still be at least five times the cost of trading.\n")
    print(f"  A survivor therefore needs at least "
          f"{5 * RT['SPY']:.4f}% of position size per trade at a stock broker,")
    print(f"  and at least {5 * PERP_RT:.4f}% per trade on the BloFin perpetual.\n")

    surv = [r for r in out_rows if r["verdict"] == "SURVIVOR"]
    print(f"  {len(surv)} settings survived the choosing and middle slices in total.")
    thick_etf = [r for r in surv if r["train_cost_multiple"] >= 5]
    print(f"  {len(thick_etf)} of them make at least 5x the cost of trading "
          f"at stock-broker costs.")
    thick_perp = [r for r in surv
                  if r["train_pct_of_position"] >= 5 * PERP_RT]
    print(f"  {len(thick_perp)} of them make at least 5x the cost of trading "
          f"on the BloFin perpetual.\n")
    for r in sorted(thick_perp, key=lambda r: -r["train_pct_of_position"])[:20]:
        mult_perp = r["train_pct_of_position"] / PERP_RT
        print(f"    {r['symbol']:4s} {r['config'][:64]:64s} "
              f"{r['train_pct_of_position']:+.4f}% of position  "
              f"stock broker {r['train_cost_multiple']:5.1f}x  "
              f"BloFin perp {mult_perp:5.1f}x  n={r['train_trades']}")
    return thick_perp


# ---------------------------------------------------------------------------

def main():
    print("=" * 78)
    print("ROUND 362 — THE S&P BOT'S SECOND RESEARCH ROUND")
    print("=" * 78)
    print("Paper only. No account anywhere can place these trades today.")
    print("Market orders on every fill. 60% chosen on, 20% read once, final")
    print("20% never loaded.\n")

    frames, splits = {}, {}
    for tag in ("SPY", "ES", "QQQ"):
        d = load(tag)
        n, i_tr, i_va = split_points(d)
        frames[tag] = d
        splits[tag] = {"n": n, "i_tr": i_tr, "i_va": i_va}
        print(f"  {tag}: {n} daily bars {d.timestamp.iloc[0]:%Y-%m-%d} -> "
              f"{d.timestamp.iloc[-1]:%Y-%m-%d} | choose on the first {i_tr} "
              f"| middle slice {i_tr}..{i_va} | final {n - i_va} days untouched")

    rows, ctrl = [], []
    family_a(frames, splits, rows, ctrl)
    family_b(frames, splits, rows, ctrl)
    family_c(frames, splits, rows)
    family_d(frames, splits, rows, ctrl)
    family_f(frames, splits, rows)
    family_e(rows)

    df = pd.DataFrame(rows)
    df.to_csv("/Users/wallacechen/cryptobot/step362_table.csv", index=False)
    pd.DataFrame(ctrl).to_csv(
        "/Users/wallacechen/cryptobot/step362_random_control_table.csv", index=False)
    print(f"\nwrote step362_table.csv ({len(df)} settings) and "
          f"step362_random_control_table.csv ({len(ctrl)} controls)")


if __name__ == "__main__":
    main()
