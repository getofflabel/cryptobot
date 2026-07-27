"""
step430_t1_sessions.py - TEST 1 of round 430.

THE CLAIM (TJR, restated in step422_liquidity_framework.md):
  "The New York open frequently takes out the London session high or low
   FIRST, and then makes the day's move in the other direction."
  He says it happens almost every single day.

WHAT WE MEASURE
  Sessions on the New York clock, exactly as stated:
      Asia 18:00-03:00, London 03:00-08:30, New York 09:30-17:00.
  For every session day:
      LH, LL   = the London window's high and low
      first sweep = the first New York bar whose high exceeds LH, or whose
                    low falls below LL
      after that bar's close, the rest of the New York session's biggest
      up move and biggest down move
  "Made the move the other way" = the bigger of the two remaining
  excursions is on the opposite side of the swept level.

THE CHANCE BASELINES, both stated up front
  (a) FREQUENCY.  A placebo level sitting the SAME relative distance from
      the 09:30 open, but borrowed from a DIFFERENT randomly chosen day.
      If a placebo level is taken out about as often as the real London
      level, then what is being measured is "the market moves this far in
      a day", not "London liquidity".
  (b) DIRECTION.  50%.  From any point in a driftless walk, the chance
      that the larger remaining excursion is up rather than down is one
      half, wherever you are standing.  So a 50% reversal rate is nothing.

UNITS: every % here is a PRICE move, not a change in position value.
RESEARCH ONLY.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step430_lib import REPO, load_5m, tag_sessions, wilson

LON_START, LON_END = 180, 510      # 03:00 - 08:30
NY_START, NY_END = 570, 1020       # 09:30 - 17:00
OPEN_WINDOW = 60                   # "the New York open" = first 60 minutes


def day_table(d: pd.DataFrame, lon_start=LON_START, lon_end=LON_END,
              ny_start=NY_START, ny_end=NY_END, min_lon_bars=20,
              min_ny_bars=60) -> pd.DataFrame:
    d = tag_sessions(d)
    m = d["mins"].to_numpy()
    lon = d[(m >= lon_start) & (m < lon_end)]
    ny = d[(m >= ny_start) & (m < ny_end)]
    lg = lon.groupby("sday").agg(LH=("high", "max"), LL=("low", "min"),
                                 nlon=("high", "size"))
    lg = lg[lg["nlon"] >= min_lon_bars]
    rows = []
    for sday, blk in ny.groupby("sday"):
        if sday not in lg.index or len(blk) < min_ny_bars:
            continue
        LH = lg.at[sday, "LH"]; LL = lg.at[sday, "LL"]
        hi = blk["high"].to_numpy(); lo = blk["low"].to_numpy()
        cl = blk["close"].to_numpy(); op = blk["open"].to_numpy()
        mins = blk["mins"].to_numpy()
        o0 = op[0]
        up_hit = np.where(hi > LH)[0]
        dn_hit = np.where(lo < LL)[0]
        i_up = int(up_hit[0]) if len(up_hit) else -1
        i_dn = int(dn_hit[0]) if len(dn_hit) else -1
        rows.append(dict(sday=sday, LH=LH, LL=LL, o0=o0,
                         i_up=i_up, i_dn=i_dn, nny=len(blk),
                         first_min=mins[0],
                         hi=hi, lo=lo, cl=cl, mins=mins,
                         ts=blk["timestamp"].iloc[0]))
    return pd.DataFrame(rows)


def classify(row):
    i_up, i_dn = row["i_up"], row["i_dn"]
    if i_up < 0 and i_dn < 0:
        return "neither", -1
    if i_up >= 0 and i_dn < 0:
        return "high", i_up
    if i_dn >= 0 and i_up < 0:
        return "low", i_dn
    if i_up < i_dn:
        return "high", i_up
    if i_dn < i_up:
        return "low", i_dn
    return "same-bar", i_up


def after_sweep(row, side, s):
    """Biggest up move and biggest down move left in the session, measured
    from the close of the sweep bar.  Returns (up_pct, dn_pct, net_pct,
    reversed_bool) - all PRICE moves in percent."""
    hi, lo, cl = row["hi"], row["lo"], row["cl"]
    if s + 1 >= len(hi):
        return np.nan, np.nan, np.nan, np.nan
    ref = cl[s]
    up = (hi[s + 1:].max() / ref - 1.0) * 100.0
    dn = (1.0 - lo[s + 1:].min() / ref) * 100.0
    net = (cl[-1] / ref - 1.0) * 100.0
    if side == "high":
        rev = dn > up
    elif side == "low":
        rev = up > dn
    else:
        rev = np.nan
    return up, dn, net, rev


def placebo_levels(tab: pd.DataFrame, seed=430, vol_matched=False):
    """Two chance baselines.

    PLAIN: the same relative distances from the 09:30 open, borrowed whole
    from another randomly chosen day.  Keeps the distance distribution but
    also destroys the fact that a wide London range and a wide New York
    range are the same day's volatility.  That mismatch alone lowers the
    hit rate, so this baseline is too easy to beat.

    VOL-MATCHED: keeps TODAY's actual London range width exactly, and
    borrows only WHERE INSIDE IT the 09:30 open sits.  Same volatility,
    same distance budget, different level.  This is the honest baseline
    for "would a level that close to the open be taken out anyway".
    """
    rng = np.random.default_rng(seed)
    o0 = tab["o0"].to_numpy()
    dH = (tab["LH"].to_numpy() - o0) / o0
    dL = (o0 - tab["LL"].to_numpy()) / o0
    n = len(tab)
    perm = rng.permutation(n)
    bad = perm == np.arange(n)
    perm[bad] = (perm[bad] + 1) % n
    if not vol_matched:
        return o0 * (1 + dH[perm]), o0 * (1 - dL[perm])
    tot_o = dH[perm] + dL[perm]
    frac = np.where(tot_o > 0, dH[perm] / np.where(tot_o > 0, tot_o, 1), 0.5)
    tot = dH + dL                      # today's own London range, kept
    return o0 * (1 + frac * tot), o0 * (1 - (1 - frac) * tot)


def run_side(tab: pd.DataFrame, PH=None, PL=None, only_open=None,
             require_inside=True):
    """One pass over the day table.  PH/PL override the levels (placebo).
    only_open limits the sweep search to the first N minutes of New York.
    require_inside keeps only days where the 09:30 open sits INSIDE the
    London range, which is the only case where taking a level out means
    anything - a level already behind price is taken out for free."""
    out = []
    LHs = tab["LH"].to_numpy() if PH is None else PH
    LLs = tab["LL"].to_numpy() if PL is None else PL
    for k, row in enumerate(tab.itertuples()):
        LH, LL = LHs[k], LLs[k]
        hi, lo, cl, mins = row.hi, row.lo, row.cl, row.mins
        if require_inside and not (LL < row.o0 < LH):
            continue
        lim = len(hi)
        if only_open is not None:
            lim = int(np.searchsorted(mins, mins[0] + only_open, "right"))
        up_hit = np.where(hi[:lim] > LH)[0]
        dn_hit = np.where(lo[:lim] < LL)[0]
        i_up = int(up_hit[0]) if len(up_hit) else -1
        i_dn = int(dn_hit[0]) if len(dn_hit) else -1
        r = dict(sday=row.sday, i_up=i_up, i_dn=i_dn)
        side, s = classify(r)
        rec = dict(sday=row.sday, side=side, s=s,
                   mins_in=np.nan if s < 0 else int(mins[s] - mins[0]),
                   range_pct=(LH - LL) / row.o0 * 100.0)
        if side in ("high", "low"):
            up, dn, net, rev = after_sweep(
                dict(hi=hi, lo=lo, cl=cl), side, s)
            sgn = -1.0 if side == "high" else 1.0
            rec.update(up_pct=up, dn_pct=dn, net_pct=net, reversed_=rev,
                       edge_pct=sgn * (up - dn),
                       net_rev=(sgn * net) > 0,
                       net_signed_pct=sgn * net)
        out.append(rec)
    return pd.DataFrame(out)


def report(name, res, fh):
    n = len(res)
    swept = res[res["side"].isin(["high", "low"])]
    p_any = len(swept) / n if n else np.nan
    lo, hi = wilson(len(swept), n)
    line = (f"  {name:<34} days={n:<5} first-sweep happened on "
            f"{p_any*100:5.1f}% [{lo*100:.1f}-{hi*100:.1f}]")
    print(line); fh.write(line + "\n")
    if len(swept) == 0:
        return dict(n=n, p_any=p_any, n_rev=0, p_rev=np.nan)
    rev = swept["reversed_"].dropna().astype(bool).to_numpy()
    k = int(rev.sum()); m = len(rev)
    rl, rh = wilson(k, m)
    med_edge = swept["edge_pct"].median()
    edge = swept["edge_pct"].dropna().to_numpy()
    te = (edge.mean() / (edge.std(ddof=1) / np.sqrt(len(edge)))
          if len(edge) > 2 else np.nan)
    nrev = swept["net_rev"].dropna().astype(bool).to_numpy()
    nk, nm = int(nrev.sum()), len(nrev)
    nl, nh = wilson(nk, nm)
    line = (f"      bigger REMAINING move was the other way: {k}/{m} = "
            f"{k/m*100:5.1f}% [{rl*100:.1f}-{rh*100:.1f}]  (chance 50.0%)")
    print(line); fh.write(line + "\n")
    line = (f"      session CLOSED the other way:            {nk}/{nm} = "
            f"{nk/nm*100:5.1f}% [{nl*100:.1f}-{nh*100:.1f}]  (chance 50.0%)")
    print(line); fh.write(line + "\n")
    line = (f"      mean edge {edge.mean():+.4f}% of price  t={te:+5.2f}   "
            f"median {med_edge:+.4f}%   "
            f"median minutes into NY = {swept['mins_in'].median():.0f}")
    print(line); fh.write(line + "\n")
    return dict(n=n, p_any=p_any, n_rev=m, p_rev=k / m, med_edge=med_edge,
                mean_edge=edge.mean(), t_edge=te, p_net_rev=nk / nm, n_net=nm)


def main():
    fh = open(f"{REPO}/step430_t1_out.txt", "w")
    W = lambda s: (print(s), fh.write(s + "\n"))
    W("=" * 78)
    W("TEST 1 - does the New York open take out the London high or low")
    W("         first, and then move the other way?")
    W("=" * 78)

    allrows = []
    specs = [("SPY", "alpaca", LON_START), ("QQQ", "alpaca", LON_START),
             ("BTCUSDT", "bybit", LON_START)]
    for sym, src, lon0 in specs:
        d = load_5m(sym, src)
        cover = d.groupby(d["et"].dt.hour).size()
        first_hr = int(cover[cover > len(d) * 0.002].index.min())
        W("")
        W(f"### {sym} ({src})   bars={len(d):,}   "
          f"{d['et'].min().date()} .. {d['et'].max().date()}   "
          f"earliest New-York-clock hour with data: {first_hr:02d}:00")
        eff_lon0 = max(lon0, first_hr * 60)
        if eff_lon0 != lon0:
            W(f"    NOTE: no data before {first_hr:02d}:00 New York time, so the "
              f"London window measured is {eff_lon0//60:02d}:00-08:30, not 03:00-08:30.")
        tab = day_table(d, lon_start=eff_lon0)
        n = len(tab)
        i_val, i_seal = int(n * 0.60), int(n * 0.80)
        W(f"    session days usable: {n}   "
          f"(first 60% = choose on, next 20% = read once, last 20% never opened)")

        for wname, sl in [("first 60%", slice(0, i_val)),
                          ("middle 20%", slice(i_val, i_seal))]:
            sub = tab.iloc[sl].reset_index(drop=True)
            W(f"  -- {wname}  ({sub['sday'].iloc[0]} .. {sub['sday'].iloc[-1]})")
            PH, PL = placebo_levels(sub)
            VH, VL = placebo_levels(sub, vol_matched=True)
            runs = [
                ("real_full", "REAL London level, whole NY session",
                 dict()),
                ("real_open60", "REAL London level, first 60 min only",
                 dict(only_open=OPEN_WINDOW)),
                ("placebo_full", "PLACEBO plain (other day), whole NY",
                 dict(PH=PH, PL=PL)),
                ("placebo_open60", "PLACEBO plain, first 60 min only",
                 dict(PH=PH, PL=PL, only_open=OPEN_WINDOW)),
                ("volmatch_full", "PLACEBO vol-matched, whole NY",
                 dict(PH=VH, PL=VL)),
                ("volmatch_open60", "PLACEBO vol-matched, first 60 min",
                 dict(PH=VH, PL=VL, only_open=OPEN_WINDOW)),
            ]
            for tag, label, kw in runs:
                r = report(label, run_side(sub, **kw), fh)
                allrows.append(dict(symbol=sym, window=wname, variant=tag, **r))
            # how often is the open already outside the London range
            o0 = sub["o0"].to_numpy()
            outside = ((o0 >= sub["LH"].to_numpy()) |
                       (o0 <= sub["LL"].to_numpy())).mean()
            W(f"      days excluded because the 09:30 open was already outside "
              f"the London range: {outside*100:.1f}%")

    pd.DataFrame(allrows).to_csv(f"{REPO}/step430_t1_sessions.csv", index=False)
    W("")
    W("wrote step430_t1_sessions.csv")
    fh.close()


if __name__ == "__main__":
    main()
