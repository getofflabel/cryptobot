"""step340_donchian_audit.py — Round 340 (gold): push the one survivor.

RESEARCH ONLY. No live orders, no live bot file touched.

Gold's single validated family is the donchian channel breakout with an
EMA20-close exit (round 48, sealed-passed on GLD and GC=F). This script
does three things to it, in order:

  JOB 1a — AUDIT AGAINST WHAT A PRACTITIONER ACTUALLY REQUIRES.
    Four conditions practitioners call mandatory on a channel breakout:
      (1) a CONFIRMED CLOSE beyond the channel, not a wick poking through
      (2) a filter on the direction of the LONGER trend
      (3) a MINIMUM CHANNEL WIDTH (do not buy the break of a dead-flat range)
      (4) NO ENTRY ON THE SIGNAL BAR ITSELF
    Our version already satisfies (1) and (4) — see step48_tradfi_trend.
    donchian_ema_exit (compares CLOSE to the prior N-bar high, and
    backtest.run_backtest fills at the NEXT bar's open). It requires
    neither (2) nor (3). This script adds them, one at a time and together,
    and re-runs.

  JOB 1b — THE ENTRY-VERSUS-EXIT CONTROL (the round-117 control).
    Random entry bars, the SAME exit rule, the SAME window, the SAME costs.
    Gold has been in a strong rise; if random entries with this exit match
    the breakout entries, then the profit is the exit riding a rising gold
    market and the entry rule is doing nothing.

  JOB 1c — REPLAY THE UNCHANGED CONFIGURATION ON THE OTHER INSTRUMENT.
    Any volatility-derived threshold is RE-DERIVED on the new instrument
    from its own price behaviour, never copied across.

Discipline: execution="taker" (market orders, the expensive kind)
everywhere. 60/20/20 in date order. Every choice made on the first 60%
only. The middle 20% is read exactly once, at the end. The final 20% is
never loaded by this file at all.

Costs (both of these are RESEARCH-instrument costs, and they are cheap —
the live gold venue is charged separately in the results table):
  GLD  (an exchange-traded fund): 0.01% fee + 0.01% slippage each side
       = 0.04% for a round trip.
  GC=F (the gold future): 0.005% + 0.005% each side = 0.02% round trip.
  BloFin XAUT market order (what the bot would REALLY pay live):
       0.06% fee + 0.01% half-spread + 0.02% slippage each side
       = 0.18% for a round trip.
  Funding is set to zero explicitly on every cost model here: exchange-
  traded funds and dated futures do not pay perpetual funding, and the
  engine charges a default unless told otherwise (round 48's catch).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step48_tradfi_trend import donchian_ema_exit
from strategy import _hysteresis

RNG_SEED = 340
N_DRAWS = 500
MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8

# round-trip cost of one trade, as a percent of the full position size
COST_PCT = {"GLD": 0.04, "GC=F": 0.02}
LIVE_VENUE_COST_PCT = 0.18          # BloFin XAUT, market order, round trip

FILES = {"GLD": "data_tradfi_GLD_1d.parquet",
         "GC=F": "data_tradfi_GCF_1d.parquet"}


def costs_for(symbol: str) -> CostModel:
    if symbol == "GLD":
        return CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                         slippage_bps=1.0, funding_bps_8h=0.0)
    return CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                     slippage_bps=0.5, funding_bps_8h=0.0)


def load(symbol: str) -> pd.DataFrame:
    d = pd.read_parquet(FILES[symbol])
    return d.reset_index(drop=True)


def split_points(d: pd.DataFrame):
    n = len(d)
    return n, int(n * 0.6), int(n * 0.8)


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def per_trade_pct(res) -> float:
    """Average profit per trade as a percent of the FULL SIZE OF THE
    POSITION (not of margin). Scale-free, so it is comparable across
    windows and instruments in a way that dollar figures are not."""
    if not res.trades:
        return 0.0
    vals = [t.pnl / abs(t.entry_price * t.units) * 100.0 for t in res.trades]
    return float(np.mean(vals))


def run_window(d, sig, costs, lo, hi):
    return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                        sig.iloc[lo:hi].reset_index(drop=True),
                        costs=costs, execution="taker")


def score(d, sig, costs, i_tr, i_va):
    return run_window(d, sig, costs, 0, i_tr), run_window(d, sig, costs, i_tr, i_va)


def years_of(d, lo, hi) -> float:
    t = pd.DatetimeIndex(d["timestamp"])
    return max(1e-9, (t[hi - 1] - t[lo]).total_seconds() / (365.25 * 24 * 3600))


def verdict(tr, va) -> str:
    if len(tr.trades) < MIN_TRAIN_TRADES or len(va.trades) < MIN_VAL_TRADES:
        return "NOT ENOUGH TRADES"
    if tr.expectancy > 0 and va.expectancy > 0:
        return "SURVIVOR"
    return "FAIL"


def mk_row(symbol, family, cfg, d, i_tr, i_va, tr, va):
    c = COST_PCT[symbol]
    tr_pct, va_pct = per_trade_pct(tr), per_trade_pct(va)
    return {
        "symbol": symbol, "family": family, "config": cfg,
        "train_n": len(tr.trades),
        "train_dollars_per_trade": round(tr.expectancy, 2),
        "train_pct_of_position": round(tr_pct, 4),
        "train_x_research_cost": round(tr_pct / c, 2),
        "train_x_live_venue_cost": round(tr_pct / LIVE_VENUE_COST_PCT, 2),
        "val_n": len(va.trades),
        "val_dollars_per_trade": round(va.expectancy, 2),
        "val_pct_of_position": round(va_pct, 4),
        "val_x_research_cost": round(va_pct / c, 2),
        "val_x_live_venue_cost": round(va_pct / LIVE_VENUE_COST_PCT, 2),
        "trades_per_year_train": round(len(tr.trades) / years_of(d, 0, i_tr), 2),
        "trades_per_year_val": round(len(va.trades) / years_of(d, i_tr, i_va), 2),
        "verdict": verdict(tr, va),
    }


# ---------------------------------------------------------------------------
# the four practitioner conditions
# ---------------------------------------------------------------------------

def channel_width_pct(d: pd.DataFrame, n: int) -> pd.Series:
    """Width of the donchian channel that the breakout is breaking, as a
    percent of price. Shifted one bar so the breaking bar is never part of
    the channel it breaks."""
    hi = d["high"].rolling(n).max().shift(1)
    lo = d["low"].rolling(n).min().shift(1)
    return (hi - lo) / d["close"] * 100.0


def donchian_filtered(d: pd.DataFrame, n: int, ema_n: int = 20,
                      trend_ma: int | None = None,
                      min_width_pct: float | None = None) -> pd.Series:
    """The incumbent breakout with the two missing practitioner conditions
    made optional.

    Unchanged from step48: entry needs the bar's CLOSE above the prior
    n-bar high (a confirmed close, never a wick), exit is the first close
    below the 20-bar exponential moving average, and the engine fills at
    the NEXT bar's open so nothing is ever bought on the signal bar.

    Added here:
      trend_ma       — only take the breakout when the close is also above
                       its own trend_ma-bar simple moving average.
      min_width_pct  — only take the breakout when the channel being broken
                       is at least this wide, as a percent of price. The
                       number is re-derived per instrument on that
                       instrument's own first-60% slice. Never copied.
    """
    hi = d["high"].rolling(n).max().shift(1)
    enter = d["close"] > hi
    if trend_ma is not None:
        enter = enter & (d["close"] > d["close"].rolling(trend_ma).mean())
    if min_width_pct is not None:
        enter = enter & (channel_width_pct(d, n) >= min_width_pct)
    ema = d["close"].ewm(span=ema_n, adjust=False).mean()
    exit_ = d["close"] < ema
    return _hysteresis(enter.fillna(False), exit_.fillna(False))


# ---------------------------------------------------------------------------
# JOB 1b — the entry-versus-exit control
# ---------------------------------------------------------------------------

def random_entry_signal(n_bars: int, entry_bars: np.ndarray,
                        exit_mask: np.ndarray) -> pd.Series:
    """Same exit rule, same number of trades, entries scattered at random.

    Enter long on a drawn bar if flat; leave on the first bar whose close
    is below the 20-bar exponential moving average. Identical state
    machine to _hysteresis, so the only thing that differs from the real
    strategy is WHICH bars start a trade."""
    sig = np.zeros(n_bars)
    want = np.zeros(n_bars, dtype=bool)
    want[entry_bars] = True
    in_pos = False
    for i in range(n_bars):
        if in_pos:
            if exit_mask[i]:
                in_pos = False
        elif want[i]:
            in_pos = True
        sig[i] = 1.0 if in_pos else 0.0
    return pd.Series(sig)


def random_entry_control(d, costs, lo, hi, n_trades, ema_n=20, warmup=220,
                         eligible_mask=None, draws=N_DRAWS, seed=RNG_SEED):
    """Returns the distribution of average profit per trade produced by
    random entries with the real exit, over the same window and costs."""
    sl = d.iloc[lo:hi].reset_index(drop=True)
    ema = sl["close"].ewm(span=ema_n, adjust=False).mean()
    exit_mask = (sl["close"] < ema).to_numpy()
    n = len(sl)
    pool = np.arange(warmup, n - 2)
    if eligible_mask is not None:
        em = eligible_mask.iloc[lo:hi].reset_index(drop=True).to_numpy()
        pool = np.array([i for i in pool if em[i]])
    rng = np.random.default_rng(seed)
    out_dollars, out_pct, out_n = [], [], []
    for _ in range(draws):
        k = min(n_trades, len(pool))
        picks = rng.choice(pool, size=k, replace=False)
        sig = random_entry_signal(n, np.sort(picks), exit_mask)
        res = run_backtest(sl, sig, costs=costs, execution="taker")
        if res.trades:
            out_dollars.append(res.expectancy)
            out_pct.append(per_trade_pct(res))
            out_n.append(len(res.trades))
    return np.array(out_dollars), np.array(out_pct), np.array(out_n)


def buy_and_hold_pct(d, lo, hi) -> float:
    sl = d.iloc[lo:hi]
    return float((sl["close"].iloc[-1] / sl["open"].iloc[0] - 1) * 100.0)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    rows = []
    store = {}

    print("=" * 78)
    print("ROUND 340 — GOLD: pushing the donchian channel breakout")
    print("Market orders throughout (execution=taker). Final 20% never loaded.")
    print("=" * 78)

    for symbol in ("GLD", "GC=F"):
        d = load(symbol)
        n, i_tr, i_va = split_points(d)
        costs = costs_for(symbol)
        t = pd.DatetimeIndex(d["timestamp"])
        store[symbol] = dict(d=d, i_tr=i_tr, i_va=i_va, costs=costs)
        print(f"\n{symbol}: {n} daily bars  {t[0]:%Y-%m-%d} -> {t[-1]:%Y-%m-%d}")
        print(f"  first 60% (choose here): {t[0]:%Y-%m-%d} -> {t[i_tr-1]:%Y-%m-%d}")
        print(f"  middle 20% (read once):  {t[i_tr]:%Y-%m-%d} -> {t[i_va-1]:%Y-%m-%d}")
        print(f"  final 20% (untouched):   {t[i_va]:%Y-%m-%d} -> {t[-1]:%Y-%m-%d}")

        # --- re-derive the channel-width numbers on THIS instrument's own
        #     first 60%. These are never carried across instruments.
        for N in (20, 55):
            w = channel_width_pct(d, N).iloc[:i_tr].dropna()
            store[symbol][f"w{N}_med"] = float(w.median())
            store[symbol][f"w{N}_p75"] = float(w.quantile(0.75))
            print(f"  donchian{N} channel width on its own first 60%: "
                  f"median {w.median():.2f}% of price, "
                  f"upper quarter starts at {w.quantile(0.75):.2f}%")

        # --- daily swing size, re-derived, for the record
        tr_rng = ((d["high"] - d["low"]) / d["close"] * 100).iloc[:i_tr]
        print(f"  daily high-to-low range on its own first 60%: "
              f"median {tr_rng.median():.2f}% of price")

    # -----------------------------------------------------------------
    # 1a. reproduce the incumbent, then add the missing conditions
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("JOB 1a — the incumbent, then the practitioner conditions added")
    print("=" * 78)

    for symbol in ("GLD", "GC=F"):
        s = store[symbol]
        d, i_tr, i_va, costs = s["d"], s["i_tr"], s["i_va"], s["costs"]

        for N in (20, 55):
            # incumbent, imported unchanged from round 48
            sig = donchian_ema_exit(d, N, ema_n=20)
            tr, va = score(d, sig, costs, i_tr, i_va)
            rows.append(mk_row(symbol, "incumbent",
                               f"donchian{N} + EMA20 exit (round 48, unchanged)",
                               d, i_tr, i_va, tr, va))

            for trend_ma in (None, 100, 200):
                for wname, wval in (("none", None),
                                    ("width>=own median", s[f"w{N}_med"]),
                                    ("width>=own upper quarter", s[f"w{N}_p75"])):
                    if trend_ma is None and wval is None:
                        continue        # that is the incumbent, already done
                    sig = donchian_filtered(d, N, 20, trend_ma, wval)
                    tr, va = score(d, sig, costs, i_tr, i_va)
                    tname = "no trend filter" if trend_ma is None else f"close>SMA{trend_ma}"
                    cfg = f"donchian{N} + EMA20 exit | {tname} | {wname}"
                    if wval is not None:
                        cfg += f" ({wval:.2f}% of price)"
                    rows.append(mk_row(symbol, "filtered", cfg, d, i_tr, i_va, tr, va))

    tbl = pd.DataFrame(rows)
    tbl.to_csv("step340_table.csv", index=False)

    def show(df, title):
        print(f"\n{title}")
        cols = ["config", "train_n", "train_dollars_per_trade",
                "train_pct_of_position", "train_x_research_cost",
                "val_n", "val_dollars_per_trade", "val_pct_of_position",
                "val_x_research_cost", "trades_per_year_train", "verdict"]
        print(df[cols].to_string(index=False))

    for symbol in ("GLD", "GC=F"):
        show(tbl[tbl.symbol == symbol].sort_values("train_pct_of_position",
                                                   ascending=False),
             f"--- {symbol} (sorted by profit per trade on the first 60% only) ---")

    # -----------------------------------------------------------------
    # 1b. entry-versus-exit control
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("JOB 1b — ENTRY-VERSUS-EXIT CONTROL (round 117's control)")
    print("Random entry bars, identical exit rule, identical window, identical")
    print("costs, 500 draws. If random matches the breakout, the entry is not")
    print("what is making the money.")
    print("=" * 78)

    control_rows = []
    for symbol in ("GLD", "GC=F"):
        s = store[symbol]
        d, i_tr, i_va, costs = s["d"], s["i_tr"], s["i_va"], s["costs"]
        for N in (20, 55):
            sig = donchian_ema_exit(d, N, ema_n=20)
            for wlabel, lo, hi in (("first 60%", 0, i_tr), ("middle 20%", i_tr, i_va)):
                res = run_window(d, sig, costs, lo, hi)
                if not res.trades:
                    continue
                real_pct = per_trade_pct(res)
                dol, pct, cnt = random_entry_control(d, costs, lo, hi,
                                                     len(res.trades))
                p = float((pct < real_pct).mean() * 100)
                bh = buy_and_hold_pct(d, lo, hi)
                yrs = years_of(d, lo, hi)
                print(f"\n{symbol} donchian{N} — {wlabel} "
                      f"({yrs:.1f} years, gold's own price rose {bh:+.1f}% "
                      f"over this window)")
                print(f"  real breakout entries : {len(res.trades)} trades, "
                      f"{real_pct:+.3f}% of position per trade, "
                      f"${res.expectancy:+.2f} per trade")
                print(f"  random entries, same exit: mean {pct.mean():+.3f}% "
                      f"of position per trade (5th pct {np.percentile(pct,5):+.3f}, "
                      f"95th pct {np.percentile(pct,95):+.3f}), "
                      f"median {np.median(cnt):.0f} completed trades")
                print(f"  the real entry sits at the {p:.1f}th percentile of "
                      f"what luck alone produces")
                control_rows.append(dict(
                    symbol=symbol, config=f"donchian{N}+EMA20exit", window=wlabel,
                    years=round(yrs, 2), price_move_pct=round(bh, 2),
                    real_n=len(res.trades),
                    real_pct_of_position=round(real_pct, 4),
                    random_mean_pct=round(float(pct.mean()), 4),
                    random_p05=round(float(np.percentile(pct, 5)), 4),
                    random_p95=round(float(np.percentile(pct, 95)), 4),
                    real_percentile_vs_luck=round(p, 1),
                    random_median_trades=int(np.median(cnt)),
                ))

    # The second control, and the more searching one: if the winning added
    # condition is "close above the 200-bar average", is the gain coming
    # from the BREAKOUT, or merely from being in the market during rising
    # stretches? Draw the random entries ONLY from bars that already pass
    # the trend filter. Now random and real face the same regime.
    print("\n" + "-" * 78)
    print("Second control: random entries drawn ONLY from bars that already pass")
    print("the close-above-200-day-average filter. This asks whether the breakout")
    print("itself adds anything once you hold the trend regime constant.")
    print("-" * 78)
    for symbol in ("GLD", "GC=F"):
        s = store[symbol]
        d, i_tr, i_va, costs = s["d"], s["i_tr"], s["i_va"], s["costs"]
        trend_ok = d["close"] > d["close"].rolling(200).mean()
        for N in (20, 55):
            sig = donchian_filtered(d, N, 20, trend_ma=200, min_width_pct=None)
            for wlabel, lo, hi in (("first 60%", 0, i_tr), ("middle 20%", i_tr, i_va)):
                res = run_window(d, sig, costs, lo, hi)
                if not res.trades:
                    continue
                real_pct = per_trade_pct(res)
                dol, pct, cnt = random_entry_control(d, costs, lo, hi,
                                                     len(res.trades),
                                                     eligible_mask=trend_ok)
                p = float((pct < real_pct).mean() * 100)
                print(f"\n{symbol} donchian{N} + close>SMA200 — {wlabel}")
                print(f"  real breakout entries : {len(res.trades)} trades, "
                      f"{real_pct:+.3f}% of position per trade")
                print(f"  random entries INSIDE the same trend regime, same exit: "
                      f"mean {pct.mean():+.3f}% of position per trade "
                      f"(5th {np.percentile(pct,5):+.3f}, 95th {np.percentile(pct,95):+.3f})")
                print(f"  the real entry sits at the {p:.1f}th percentile of luck")
                control_rows.append(dict(
                    symbol=symbol, config=f"donchian{N}+SMA200+EMA20exit",
                    window=wlabel + " (random drawn inside trend regime)",
                    years=round(years_of(d, lo, hi), 2),
                    price_move_pct=round(buy_and_hold_pct(d, lo, hi), 2),
                    real_n=len(res.trades),
                    real_pct_of_position=round(real_pct, 4),
                    random_mean_pct=round(float(pct.mean()), 4),
                    random_p05=round(float(np.percentile(pct, 5)), 4),
                    random_p95=round(float(np.percentile(pct, 95)), 4),
                    real_percentile_vs_luck=round(p, 1),
                    random_median_trades=int(np.median(cnt)),
                ))

    pd.DataFrame(control_rows).to_csv("step340_table_control.csv", index=False)

    # -----------------------------------------------------------------
    # 1c. cross-instrument replay is already in the main table: the same
    #     configuration appears for both GLD and GC=F, with the width
    #     threshold re-derived on each instrument's own first 60%.
    # -----------------------------------------------------------------
    print("\n" + "=" * 78)
    print("JOB 1c — SAME RULE, OTHER INSTRUMENT (thresholds re-derived, never copied)")
    print("=" * 78)
    keys = sorted({c.split(" (")[0] for c in tbl["config"]})
    for cfg_key in keys:
        sub = tbl[[c.startswith(cfg_key) for c in tbl["config"]]]
        if len(sub) < 2:
            continue
        v = dict(zip(sub.symbol, sub.verdict))
        if v.get("GLD") == "SURVIVOR" and v.get("GC=F") == "SURVIVOR":
            g = sub[sub.symbol == "GLD"].iloc[0]
            f = sub[sub.symbol == "GC=F"].iloc[0]
            print(f"BOTH INSTRUMENTS AGREE | {cfg_key}")
            print(f"   GLD  first60% {g.train_pct_of_position:+.3f}% x{g.train_n}t "
                  f"({g.train_x_research_cost:.1f} times research cost) | "
                  f"middle20% {g.val_pct_of_position:+.3f}% x{g.val_n}t "
                  f"({g.val_x_research_cost:.1f}x, live venue "
                  f"{g.val_x_live_venue_cost:.1f}x)")
            print(f"   GC=F first60% {f.train_pct_of_position:+.3f}% x{f.train_n}t "
                  f"({f.train_x_research_cost:.1f} times research cost) | "
                  f"middle20% {f.val_pct_of_position:+.3f}% x{f.val_n}t "
                  f"({f.val_x_research_cost:.1f}x, live venue "
                  f"{f.val_x_live_venue_cost:.1f}x)")

    print("\nwrote step340_table.csv and step340_table_control.csv")


if __name__ == "__main__":
    main()
