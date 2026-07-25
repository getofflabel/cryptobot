"""step341_gold_family_ports.py — Round 341 (gold): widen the map.

RESEARCH ONLY. No live orders, no live bot file touched.

Gold has the thinnest map of tested strategy families on the desk. This
script adds FIVE families, four of them SHAPES that survived somewhere
else on this desk and one of them native to gold. Every number is
re-derived from gold's own price behaviour. The original number and
gold's own number are both printed, side by side, every time.

  FAMILY 1 — volume-gated Bollinger-band breakout.
     Where it comes from: round 87, the desk's first sealed-tested
     strategy that trades often (Bitcoin and Ethereum, hourly bars).
     Died on crypto only because the profit per trade was too thin to
     clear the cost of trading. Gold's profit per trade may be much
     thicker.
  FAMILY 2 — turn of the month.
     Where it comes from: round 130 on the S&P, the strongest calendar
     signal found anywhere in this program, and it survived on three
     instruments there.
  FAMILY 3 — very-short-term dip-buy, PROPERLY SPECIFIED.
     Where it comes from: round 60 on the S&P. Note this is a DIFFERENT
     shape from the crypto dip-buy that already died on gold in round 48:
     that one had a fixed hold and a fixed target and NO longer-trend
     condition. This one requires the price to be above its own 200-day
     average and exits on a condition, not a clock. Round 86's lesson was
     exactly this — a family can be wrongly buried because the version we
     measured was missing the condition practitioners call mandatory.
  FAMILY 4 — trend with a volatility gate.
     Where it comes from: round 54 on Bitcoin. Bitcoin's gate is a fixed
     1.5% average-true-range threshold. Round 48 already showed that
     number produces ZERO trades on gold. So the gate here is gold's own
     trailing median, recomputed on gold's own bars.
  FAMILY 5 — the overnight gap as a tradeable event. Gold's own, never
     tested. Buy or sell at the open after a gap, flat at the close. This
     family is interesting for a second reason: it holds nothing
     overnight, so gold's defining risk (the overnight gap blowing through
     a stop) cannot touch it.

Discipline: execution="taker" (market orders, the expensive kind).
60/20/20 in date order. Choices made on the first 60% only, the middle
20% read once at the end, the final 20% never loaded by this file.
At least 30 trades in the first slice and 8 in the middle slice, or the
cell is reported as NOT ENOUGH TRADES.

Costs: GLD and IAU 0.04% for a round trip, GC=F 0.02%. The live gold
venue (a market order on BloFin's XAUT) costs 0.18% for a round trip and
every profit figure is ALSO expressed as a multiple of that, because that
is what the bot would really pay.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import CostModel, run_backtest
from step48_tradfi_trend import adaptive_vol_gate
from strategy import _hysteresis, atr, rsi, vol_gated_ma

MIN_TRAIN_TRADES = 30
MIN_VAL_TRADES = 8
LIVE_VENUE_COST_PCT = 0.18

FILES = {"GLD": "data_tradfi_GLD_1d.parquet",
         "GC=F": "data_tradfi_GCF_1d.parquet",
         "IAU": "data_tradfi_IAU_1d.parquet"}
COST_PCT = {"GLD": 0.04, "GC=F": 0.02, "IAU": 0.04}

ROWS = []


def costs_for(symbol: str) -> CostModel:
    if symbol == "GC=F":
        return CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                         slippage_bps=0.5, funding_bps_8h=0.0)
    return CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                     slippage_bps=1.0, funding_bps_8h=0.0)


def load(symbol):
    d = pd.read_parquet(FILES[symbol]).reset_index(drop=True)
    n = len(d)
    return d, int(n * 0.6), int(n * 0.8)


def per_trade_pct(res) -> float:
    if not res.trades:
        return 0.0
    return float(np.mean([t.pnl / abs(t.entry_price * t.units) * 100.0
                          for t in res.trades]))


def years_of(d, lo, hi):
    t = pd.DatetimeIndex(d["timestamp"])
    return max(1e-9, (t[hi - 1] - t[lo]).total_seconds() / (365.25 * 24 * 3600))


def record(symbol, family, cfg, d, i_tr, i_va, tr_n, tr_pct, tr_dol,
           va_n, va_pct, va_dol, note=""):
    c = COST_PCT[symbol]
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        v = "NOT ENOUGH TRADES"
    elif tr_pct > 0 and va_pct > 0:
        v = "SURVIVOR"
    else:
        v = "FAIL"
    row = dict(symbol=symbol, family=family, config=cfg,
               train_n=tr_n, train_dollars_per_trade=round(tr_dol, 2),
               train_pct_of_position=round(tr_pct, 4),
               train_x_research_cost=round(tr_pct / c, 2),
               train_x_live_venue_cost=round(tr_pct / LIVE_VENUE_COST_PCT, 2),
               val_n=va_n, val_dollars_per_trade=round(va_dol, 2),
               val_pct_of_position=round(va_pct, 4),
               val_x_research_cost=round(va_pct / c, 2),
               val_x_live_venue_cost=round(va_pct / LIVE_VENUE_COST_PCT, 2),
               trades_per_year_train=round(tr_n / years_of(d, 0, i_tr), 2),
               trades_per_year_val=round(va_n / years_of(d, i_tr, i_va), 2),
               verdict=v, note=note)
    ROWS.append(row)
    return row


def score_signal(symbol, family, cfg, d, i_tr, i_va, sig, note=""):
    costs = costs_for(symbol)

    def run(lo, hi):
        return run_backtest(d.iloc[lo:hi].reset_index(drop=True),
                            sig.iloc[lo:hi].reset_index(drop=True),
                            costs=costs, execution="taker")

    tr, va = run(0, i_tr), run(i_tr, i_va)
    return record(symbol, family, cfg, d, i_tr, i_va,
                  len(tr.trades), per_trade_pct(tr), tr.expectancy,
                  len(va.trades), per_trade_pct(va), va.expectancy, note)


def bb(close, n, k):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)
    return mid - k * sd, mid, mid + k * sd


def gate_entries(sig: pd.Series, ok: pd.Series) -> pd.Series:
    """Only allow a fresh entry when `ok` is true on the very bar the
    signal turns on. If blocked, the whole excursion is skipped (copied
    in spirit from step86_specified.volume_gate_entry, which is how the
    Bitcoin version of this family was gated)."""
    s = sig.fillna(0).to_numpy()
    v = ok.fillna(False).to_numpy()
    out = np.zeros(len(s))
    blocked, prev = False, 0.0
    for i in range(len(s)):
        if s[i] != 0.0 and prev == 0.0:
            blocked = not v[i]
        if s[i] == 0.0:
            blocked = False
        out[i] = 0.0 if (s[i] != 0.0 and blocked) else s[i]
        prev = s[i]
    return pd.Series(out, index=sig.index)


# ===========================================================================
# FAMILY 1 — volume-gated Bollinger-band breakout (Bitcoin's round-87 shape)
# ===========================================================================

def family1(symbols=("GLD", "IAU")):
    print("\n" + "=" * 78)
    print("FAMILY 1 — volume-gated Bollinger-band breakout")
    print("Original (round 87, Bitcoin/Ethereum hourly): bands 20 bars wide at")
    print("2.5 standard deviations, entry only when that bar's volume is at")
    print("least 1.2x or 1.5x its own 20-bar average volume.")
    print("Gold's own numbers are re-derived below. The gold FUTURE is excluded")
    print("from this family: its volume series from the data provider has 382")
    print("zero-volume days inside the first 60% and a median of 78 contracts,")
    print("which is front-month roll noise, not real traded volume. A second")
    print("gold exchange-traded fund (IAU) stands in as the transfer check, and")
    print("that is a weaker check than the future because both funds hold the")
    print("same metal.")
    print("=" * 78)

    for symbol in symbols:
        d, i_tr, i_va = load(symbol)
        ratio = (d["volume"] / d["volume"].rolling(20).mean().shift(1)).iloc[:i_tr].dropna()
        print(f"\n{symbol}: volume against its own 20-day average, first 60% only — "
              f"median {ratio.median():.2f}x, 70th percentile {ratio.quantile(.70):.2f}x, "
              f"85th percentile {ratio.quantile(.85):.2f}x")
        print(f"  Bitcoin's 1.2x gate keeps the top "
              f"{(ratio >= 1.2).mean()*100:.0f}% of {symbol} days; "
              f"its 1.5x gate keeps the top {(ratio >= 1.5).mean()*100:.0f}%. "
              f"Gold's own equivalents are {ratio.quantile(.70):.2f}x and "
              f"{ratio.quantile(.85):.2f}x.")

        vol_avg = d["volume"].rolling(20).mean().shift(1)
        vratio = d["volume"] / vol_avg

        for k in (2.0, 2.5):
            lo, mid, up = bb(d["close"], 20, k)
            enter = d["close"] > up
            exit_ = d["close"] < mid
            base = _hysteresis(enter.fillna(False), exit_.fillna(False))
            score_signal(symbol, "1-volume-gated Bollinger breakout",
                         f"bands 20/{k} std, long only, no volume gate",
                         d, i_tr, i_va, base)
            for label, thr in (("gold's own 70th percentile", ratio.quantile(.70)),
                               ("gold's own 85th percentile", ratio.quantile(.85)),
                               ("Bitcoin's literal 1.2x (for comparison only)", 1.2)):
                sig = gate_entries(base, vratio >= thr)
                score_signal(symbol, "1-volume-gated Bollinger breakout",
                             f"bands 20/{k} std, long only, volume >= {thr:.2f}x "
                             f"20-day average ({label})",
                             d, i_tr, i_va, sig)

        # the short mirror, one row, because gold shorts have died 0/56 so far
        lo, mid, up = bb(d["close"], 20, 2.5)
        short = _hysteresis(pd.Series(False, index=d.index),
                            (d["close"] > mid).fillna(False),
                            short_enter=(d["close"] < lo).fillna(False))
        score_signal(symbol, "1-volume-gated Bollinger breakout",
                     "bands 20/2.5 std, SHORT mirror, no volume gate",
                     d, i_tr, i_va, short)


# ===========================================================================
# FAMILY 2 — turn of the month (the S&P's round-130 shape)
# ===========================================================================

def turn_of_month_mask(d, before=3, after=3):
    t = pd.DatetimeIndex(d["timestamp"])
    month_id = t.year * 12 + t.month
    mask = np.zeros(len(d), dtype=bool)
    idx = np.arange(len(d))
    for m in np.unique(month_id):
        sel = idx[month_id == m]
        if before > 0:
            mask[sel[-before:]] = True   # last N trading days of the month
        if after > 0:
            mask[sel[:after]] = True     # first N trading days of the month
    return pd.Series(mask, index=d.index)


def family2(symbols=("GLD", "GC=F", "IAU")):
    print("\n" + "=" * 78)
    print("FAMILY 2 — turn of the month")
    print("Original (round 130, S&P): long from 3 trading days before month end")
    print("through 3 trading days into the new month. This is a CALENDAR rule —")
    print("there is no volatility number in it, so there is nothing to re-derive.")
    print("The window widths are tested on gold's own bars anyway, in case gold's")
    print("month-end flows have a different shape from the index's.")
    print("=" * 78)
    for symbol in symbols:
        d, i_tr, i_va = load(symbol)
        for before, after in ((3, 3), (1, 3), (4, 4), (3, 1), (1, 1)):
            sig = turn_of_month_mask(d, before, after).astype(float)
            score_signal(symbol, "2-turn of the month",
                         f"long from {before} trading days before month end "
                         f"through {after} trading days into the new month",
                         d, i_tr, i_va, sig)


# ===========================================================================
# FAMILY 3 — properly specified very-short-term dip-buy (S&P's round-60 shape)
# ===========================================================================

def family3(symbols=("GLD", "GC=F", "IAU")):
    print("\n" + "=" * 78)
    print("FAMILY 3 — very-short-term dip-buy, properly specified")
    print("Original (round 60, S&P): buy when the 2-day relative-strength")
    print("reading drops under 5 AND the price is above its own 200-day average;")
    print("leave when the close gets back above its own 5-day average or the")
    print("2-day reading rises above 65. NO fixed target, NO fixed clock.")
    print("The crypto dip-buy already buried on gold in round 48 was a different")
    print("shape: it had a fixed hold, a fixed target, and no longer-trend")
    print("condition. The relative-strength thresholds are re-derived on gold's")
    print("own bars below, because how often a market gets that oversold depends")
    print("on how much it moves.")
    print("=" * 78)
    for symbol in symbols:
        d, i_tr, i_va = load(symbol)
        r2, r3 = rsi(d["close"], 2), rsi(d["close"], 3)
        tr2 = r2.iloc[:i_tr].dropna()
        print(f"\n{symbol}: the 2-day relative-strength reading on its own first 60% — "
              f"5th percentile {tr2.quantile(.05):.1f}, 10th percentile "
              f"{tr2.quantile(.10):.1f}, 15th percentile {tr2.quantile(.15):.1f}. "
              f"The S&P's literal 'under 5' threshold fires on "
              f"{(tr2 < 5).mean()*100:.1f}% of {symbol} days.")
        sma200 = d["close"].rolling(200).mean()
        sma5 = d["close"].rolling(5).mean()
        for name, osc, thr in (("2-day reading under 5 (S&P's literal number)", r2, 5),
                               ("2-day reading under gold's own 5th percentile", r2,
                                float(tr2.quantile(.05))),
                               ("2-day reading under gold's own 10th percentile", r2,
                                float(tr2.quantile(.10))),
                               ("3-day reading under 15 (S&P's other survivor)", r3, 15)):
            for gate_label, gate in (("above its own 200-day average",
                                      d["close"] > sma200),
                                     ("no longer-trend condition (the round-48 mistake)",
                                      pd.Series(True, index=d.index))):
                enter = (osc < thr) & gate
                exit_ = (d["close"] > sma5) | (osc > 65)
                sig = _hysteresis(enter.fillna(False), exit_.fillna(False))
                score_signal(symbol, "3-short-term dip-buy",
                             f"{name} (threshold {thr:.1f}), {gate_label}",
                             d, i_tr, i_va, sig)


# ===========================================================================
# FAMILY 4 — trend with a volatility gate (Bitcoin's round-54 shape)
# ===========================================================================

def family4(symbols=("GLD", "GC=F", "IAU")):
    print("\n" + "=" * 78)
    print("FAMILY 4 — moving-average trend with a volatility gate")
    print("Original (round 54, Bitcoin): 4-hour trend, entry allowed only when")
    print("the average true range is above a FIXED 1.5% of price. Round 48")
    print("already proved that exact number produces ZERO trades on gold, whose")
    print("daily range is smaller. So the gate used here is gold's OWN trailing")
    print("one-year median average true range, recomputed bar by bar on gold's")
    print("own data, never a number carried over from Bitcoin.")
    print("=" * 78)
    for symbol in symbols:
        d, i_tr, i_va = load(symbol)
        a_pct = (atr(d, 14) / d["close"] * 100).iloc[:i_tr].dropna()
        print(f"\n{symbol}: average true range on its own first 60% — median "
              f"{a_pct.median():.2f}% of price (25th {a_pct.quantile(.25):.2f}%, "
              f"75th {a_pct.quantile(.75):.2f}%). Bitcoin's fixed 1.5% gate would "
              f"be open on {(a_pct > 1.5).mean()*100:.1f}% of {symbol}'s days.")
        gate_above, _ = adaptive_vol_gate(d, direction="above")
        gate_below, _ = adaptive_vol_gate(d, direction="below")
        for fast, slow in ((20, 100), (50, 200)):
            for gname, g in (("no volatility gate", None),
                             ("only when the range is ABOVE gold's own trailing "
                              "one-year median", gate_above),
                             ("only when the range is BELOW gold's own trailing "
                              "one-year median", gate_below)):
                if g is None:
                    sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0)
                else:
                    sig = vol_gated_ma(d, fast, slow, min_atr_pct=0.0, entry_filter=g)
                sig = sig.clip(lower=0.0)
                score_signal(symbol, "4-trend with a volatility gate",
                             f"{fast}/{slow} average cross, long only, {gname}",
                             d, i_tr, i_va, sig)


# ===========================================================================
# FAMILY 5 — the overnight gap as a tradeable event (gold's own)
# ===========================================================================

def family5(symbols=("GLD", "GC=F", "IAU")):
    """Enter at today's open, leave at today's close. Nothing is held
    overnight, so gold's defining risk cannot reach this family.

    This needs its own simulator: the shared engine deliberately fills at
    the NEXT bar's open, which makes a same-day trade impossible to express.
    The simulator below uses a FLAT position size of $10,000 with no
    compounding, so the dollar figures here are not comparable with the
    dollar figures produced by the shared engine elsewhere in this round.
    Only the percent-of-position figures, the verdicts and the cost
    multiples are comparable. Costs are charged as the full round trip for
    the instrument, taken out of the trade's profit.
    """
    print("\n" + "=" * 78)
    print("FAMILY 5 — the overnight gap as a tradeable event (gold's own family)")
    print("Buy or sell at the open the morning after a gap, flat at the close.")
    print("Nothing held overnight. Gap thresholds are re-derived on gold's own")
    print("gap distribution — the S&P's own gap work used 0.3%/0.5%/0.8% of")
    print("price, which are the S&P's numbers, not gold's.")
    print("=" * 78)
    NOTIONAL = 10_000.0
    for symbol in symbols:
        d, i_tr, i_va = load(symbol)
        gap = (d["open"] / d["close"].shift(1) - 1) * 100
        g_tr = gap.iloc[:i_tr].dropna()
        print(f"\n{symbol}: overnight gap on its own first 60% — median size "
              f"{g_tr.abs().median():.3f}% of price, 75th percentile "
              f"{g_tr.abs().quantile(.75):.3f}%, 90th percentile "
              f"{g_tr.abs().quantile(.90):.3f}%. Days gapping more than the S&P's "
              f"0.5% threshold: {(g_tr.abs() > 0.5).mean()*100:.1f}%.")
        day_ret = (d["close"] / d["open"] - 1) * 100
        cost = COST_PCT[symbol]
        thresholds = [("gold's own median gap", float(g_tr.abs().median())),
                      ("gold's own 75th percentile gap", float(g_tr.abs().quantile(.75))),
                      ("gold's own 90th percentile gap", float(g_tr.abs().quantile(.90)))]
        for tlabel, thr in thresholds:
            for gap_dir, shape in (("up", "continuation"), ("up", "reversal"),
                                   ("down", "continuation"), ("down", "reversal")):
                hit = (gap >= thr) if gap_dir == "up" else (gap <= -thr)
                side = 1.0
                if gap_dir == "up" and shape == "reversal":
                    side = -1.0
                if gap_dir == "down" and shape == "continuation":
                    side = -1.0
                pnl_pct = side * day_ret - cost
                res = {}
                for wname, lo, hi in (("train", 0, i_tr), ("val", i_tr, i_va)):
                    m = hit.iloc[lo:hi].fillna(False)
                    p = pnl_pct.iloc[lo:hi][m].dropna()
                    res[wname] = (len(p), float(p.mean()) if len(p) else 0.0)
                direction = "long" if side > 0 else "short"
                record(symbol, "5-overnight gap",
                       f"gap {gap_dir} at least {thr:.3f}% of price ({tlabel}), "
                       f"{shape}: go {direction} at the open, flat at the close",
                       d, i_tr, i_va,
                       res["train"][0], res["train"][1],
                       res["train"][1] / 100 * NOTIONAL,
                       res["val"][0], res["val"][1],
                       res["val"][1] / 100 * NOTIONAL,
                       note="flat $10,000 position, not compounded; "
                            "nothing held overnight")


# ===========================================================================
# FAMILY 6 — the one proven shape, moved to intraday bars (the frequency test)
# ===========================================================================

INTRADAY_FILES = {"GLD 1-hour": ("data_tradfi_GLD_1h.parquet", 0.04),
                  "gold future 1-hour": ("data_tradfi_GCF_1h.parquet", 0.02),
                  "gold future 4-hour": ("data_gold_4h.parquet", 0.02)}


def family6():
    """Gold's one validated family fires about 5 times a year on daily bars.
    That is not a bot, it is a hobby. The obvious question nobody has run:
    does the SAME shape pay on faster bars, where it would fire far more
    often? Round 55 built these signals and then correctly declined to look
    at them because the hourly history is thin. It is still thin. Every
    result here is therefore reported with the trade counts in plain view
    and marked NOT ENOUGH HISTORY where it applies — this is a lead, not a
    verdict."""
    print("\n" + "=" * 78)
    print("FAMILY 6 — the proven breakout shape moved to intraday bars")
    print("This is the direct attack on gold's real constraint: the validated")
    print("daily breakout fires about 5 times a year. Hourly gold history only")
    print("goes back about 3 years, so these are LEADS, not verdicts, and the")
    print("windows are stated in years next to every row.")
    print("=" * 78)
    for label, (fname, cost) in INTRADAY_FILES.items():
        try:
            d = pd.read_parquet(fname).reset_index(drop=True)
        except FileNotFoundError:
            print(f"  {label}: no data file, skipped")
            continue
        n = len(d)
        i_tr, i_va = int(n * 0.6), int(n * 0.8)
        t = pd.DatetimeIndex(d["timestamp"])
        COST_PCT[label] = cost
        FILES[label] = fname
        yrs_tr, yrs_va = years_of(d, 0, i_tr), years_of(d, i_tr, i_va)
        print(f"\n{label}: {n} bars, {t[0]:%Y-%m-%d} -> {t[-1]:%Y-%m-%d}. "
              f"First 60% is only {yrs_tr:.2f} years, middle 20% only "
              f"{yrs_va:.2f} years.")
        a_pct = (atr(d, 14) / d["close"] * 100).iloc[:i_tr].dropna()
        print(f"  average true range per bar on its own first 60%: median "
              f"{a_pct.median():.3f}% of price. Bitcoin's hourly figure runs "
              f"about 0.45%; the desk's stated gold hourly range is 0.28-0.72%.")
        for N in (20, 55, 100):
            hi = d["high"].rolling(N).max().shift(1)
            ema = d["close"].ewm(span=20, adjust=False).mean()
            sig = _hysteresis((d["close"] > hi).fillna(False),
                              (d["close"] < ema).fillna(False))
            score_signal(label, "6-breakout on intraday bars",
                         f"break of the prior {N}-bar high on a close, "
                         f"leave on a close below the 20-bar average",
                         d, i_tr, i_va, sig,
                         note=f"first 60% is {yrs_tr:.2f} years — thin")


def main():
    print("=" * 78)
    print("ROUND 341 — GOLD: five new strategy families")
    print("Market orders throughout (execution=taker). Final 20% never loaded.")
    print("=" * 78)
    for s in ("GLD", "GC=F", "IAU"):
        d, i_tr, i_va = load(s)
        t = pd.DatetimeIndex(d["timestamp"])
        print(f"{s}: {len(d)} daily bars | choose on {t[0]:%Y-%m-%d}..{t[i_tr-1]:%Y-%m-%d} "
              f"| read once {t[i_tr]:%Y-%m-%d}..{t[i_va-1]:%Y-%m-%d} "
              f"| untouched {t[i_va]:%Y-%m-%d}..{t[-1]:%Y-%m-%d}")

    family1()
    family2()
    family3()
    family4()
    family5()
    family6()

    tbl = pd.DataFrame(ROWS)
    tbl.to_csv("step341_table.csv", index=False)

    cols = ["symbol", "config", "train_n", "train_pct_of_position",
            "train_x_live_venue_cost", "val_n", "val_pct_of_position",
            "val_x_live_venue_cost", "trades_per_year_train", "verdict"]
    for fam in sorted(tbl.family.unique()):
        sub = tbl[tbl.family == fam].sort_values(
            ["symbol", "train_pct_of_position"], ascending=[True, False])
        print(f"\n\n########## {fam} ##########")
        print(sub[cols].to_string(index=False))

    print("\n\n########## CROSS-INSTRUMENT: same rule, does it hold up elsewhere ##########")
    for cfg in sorted(tbl.config.unique()):
        sub = tbl[tbl.config == cfg]
        v = dict(zip(sub.symbol, sub.verdict))
        if len(v) < 2:
            continue
        surv = [k for k, x in v.items() if x == "SURVIVOR"]
        if len(surv) >= 2:
            fam = sub.iloc[0].family
            print(f"\n[{fam}] {cfg}")
            for _, r in sub.iterrows():
                print(f"   {r.symbol:5s} {r.verdict:18s} first60% {r.train_pct_of_position:+.3f}% "
                      f"x{r.train_n}t ({r.train_x_live_venue_cost:.1f} times the LIVE venue cost) | "
                      f"middle20% {r.val_pct_of_position:+.3f}% x{r.val_n}t "
                      f"({r.val_x_live_venue_cost:.1f}x) | {r.trades_per_year_train:.1f} trades a year")

    print("\nwrote step341_table.csv")


if __name__ == "__main__":
    main()
