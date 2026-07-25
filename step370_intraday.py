"""
step370_intraday.py - ROUND 370, PART 2
INTRADAY SETUPS ON 5-MINUTE S&P BARS

Research only. No orders, paper or otherwise. No live file touched.
Paper-only book: Alpaca paper is the first venue that could hold any of
this, and nothing here has been near it.

RULES OBEYED HERE
  - Market orders only, and only inside regular trading hours, because
    Alpaca rejects market orders outside them (round 360). Every fill is
    the OPEN of the bar AFTER the signal bar. If a signal lands on the
    last bar of a session it is dropped, not carried.
  - Stops sit at chart structure, per trade, read off the chart. Never a
    swept percentage. Size = dollars risked / stop distance, so leverage
    is an output and is reported, never chosen.
  - Every position is FLAT by the session close. Part 1 measured that an
    intraday-sized stop is gapped through on 41.5% of sessions if held
    overnight, so holding one overnight is not a strategy, it is a
    different and much worse strategy.
  - Costs on both ends, always. 0.04% of notional for a round trip is
    the headline number (SPY at a US broker: no commission, a penny
    spread and a little slippage). 0.02% is also reported.
  - THE ROUND-400 LESSON. A filter is never tested by re-running the
    whole engine with the filter on and comparing totals, because in a
    one-position engine dropping an entry frees the slot for a different
    trade later. Here EVERY candidate signal is scored independently, so
    a filtered set is a strict subset of the same trade population by
    construction, and the script asserts that the entry timestamps of
    the filtered set are a subset of the unfiltered set.
  - Chance baseline: for each family, the same stop-and-exit machinery
    run on EVERY eligible bar in the same clock window. That is what
    entering at a random eligible moment would have produced.

Slices: 60% choosing / 20% middle read once / final 20% never opened.
Floors: 30 trades in the choosing slice, 8 in the middle slice.
"""

import sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/Users/wallacechen/cryptobot")
from step370_structure import load_rth, tjr_swings, split_60_20_20

REPO = "/Users/wallacechen/cryptobot"
COST_RT = 0.04          # % of notional, round trip, headline
COST_RT_LOW = 0.02      # % of notional, round trip, optimistic
MIN_TR, MIN_VA = 30, 8


# ------------------------------------------------------------ prep
def prep(symbol="SPY", tf="5m"):
    full, d = load_rth(symbol, tf)
    d = d.reset_index(drop=True)
    n = len(d)
    sess = d["date"].to_numpy()
    new_sess = np.r_[True, sess[1:] != sess[:-1]]
    sid = np.cumsum(new_sess) - 1
    d["sid"] = sid
    # last bar index of each session
    last_of_sess = pd.Series(np.arange(n)).groupby(sid).transform("max").to_numpy()
    d["last_idx"] = last_of_sess

    sh, sl = tjr_swings(d)
    # most recent confirmed TJR swing level as of each bar, forward filled,
    # then shifted one bar so a close is never compared to a level that
    # contains that same bar's own high/low.
    d["mr_sh"] = sh.ffill().shift(1)
    d["mr_sl"] = sl.ffill().shift(1)
    d["sh_raw"] = sh
    d["sl_raw"] = sl

    # previous session RTH high/low
    g = d.groupby("sid")
    hi = g["high"].max()
    lo = g["low"].min()
    d["pdh"] = d["sid"].map(hi.shift(1))
    d["pdl"] = d["sid"].map(lo.shift(1))

    # overnight (extended-hours) high/low between the previous RTH close
    # and today's open, taken from the FULL tape including pre-market
    full = full.copy()
    full["is_rth"] = (full["mins"] >= 570) & (full["mins"] <= 955)
    on_hi, on_lo = {}, {}
    fdates = full["date"].to_numpy()
    fmins = full["mins"].to_numpy()
    fh, fl = full["high"].to_numpy(), full["low"].to_numpy()
    # bars before 09:30 on day X, plus bars after 16:00 on the prior day
    pre = full[(full["mins"] < 570)]
    for dt, grp in pre.groupby("date"):
        on_hi[dt] = grp["high"].max()
        on_lo[dt] = grp["low"].min()
    d["onh"] = d["date"].map(on_hi)
    d["onl"] = d["date"].map(on_lo)

    # opening range, first 30 minutes (bars stamped 09:30..09:55)
    for orm, tag in ((30, "or30"), (60, "or60"), (15, "or15")):
        mask = d["mins"] < 570 + orm
        gg = d[mask].groupby("sid")
        d[tag + "h"] = d["sid"].map(gg["high"].max())
        d[tag + "l"] = d["sid"].map(gg["low"].min())

    # daily trend context: 200-session simple average of session closes
    sc = g["close"].last()
    sma200 = sc.rolling(200).mean().shift(1)
    d["above_sma200"] = d["sid"].map(sc.shift(1) > sma200)

    # session realised range as a volatility bucket, previous session
    rng = ((hi - lo) / g["close"].last() * 100.0)
    d["prev_rng"] = d["sid"].map(rng.shift(1))
    return d


# ------------------------------------------------------- simulator
def simulate(d, idx, direction, stop_px, target_px, max_hold=None,
             cost=COST_RT):
    """Score each candidate signal INDEPENDENTLY. No shared position slot.

    idx        : integer positions of SIGNAL bars (decision at that close)
    direction  : +1 long, -1 short
    stop_px    : stop price per signal, read from the chart
    target_px  : target price per signal, or NaN for none
    Fill is the OPEN of bar idx+1. Exit is stop touch, target touch, a
    hold cap, or the session's last bar close, whichever comes first.
    If a bar touches both stop and target, the STOP is assumed first.
    """
    o = d["open"].to_numpy(); h = d["high"].to_numpy()
    l = d["low"].to_numpy();  c = d["close"].to_numpy()
    lastix = d["last_idx"].to_numpy()
    ts = d["et"].to_numpy()

    recs = []
    for k, i in enumerate(idx):
        j = i + 1
        if j > lastix[i]:            # signal on the session's final bar
            continue
        entry = o[j]
        sp = stop_px[k]
        tp = target_px[k] if target_px is not None else np.nan
        if not np.isfinite(sp):
            continue
        if direction > 0 and sp >= entry:
            continue
        if direction < 0 and sp <= entry:
            continue
        stop_dist = abs(entry - sp) / entry * 100.0
        end = lastix[i]
        if max_hold is not None:
            end = min(end, j + max_hold - 1)
        exit_px, reason, bars = None, None, 0
        for t in range(j, end + 1):
            bars = t - j + 1
            if direction > 0:
                if l[t] <= sp:
                    exit_px, reason = sp, "stop"; break
                if np.isfinite(tp) and h[t] >= tp:
                    exit_px, reason = tp, "target"; break
            else:
                if h[t] >= sp:
                    exit_px, reason = sp, "stop"; break
                if np.isfinite(tp) and l[t] <= tp:
                    exit_px, reason = tp, "target"; break
        if exit_px is None:
            exit_px, reason = c[end], "flat_at_close"
        gross = direction * (exit_px - entry) / entry * 100.0
        net = gross - cost
        recs.append((i, ts[i], entry, exit_px, stop_dist, gross, net,
                     net / stop_dist if stop_dist > 0 else np.nan, reason, bars))
    return pd.DataFrame(recs, columns=[
        "sig_i", "sig_time", "entry", "exit", "stop_dist_pct", "gross_pct",
        "net_pct", "net_R", "reason", "bars_held"])


def report(name, tr, va, extra=""):
    if len(tr) < MIN_TR or len(va) < MIN_VA:
        return dict(name=name, verdict="INSUFFICIENT SAMPLE",
                    n_tr=len(tr), n_va=len(va))
    m_tr, m_va = tr["net_pct"].mean(), va["net_pct"].mean()
    thick = m_tr / COST_RT
    lev1 = 1.0 / tr["stop_dist_pct"].mean()
    return dict(name=name, n_tr=len(tr), n_va=len(va),
                mean_tr=m_tr, mean_va=m_va,
                R_tr=tr["net_R"].mean(), R_va=va["net_R"].mean(),
                win_tr=(tr["net_pct"] > 0).mean() * 100,
                stop_tr=tr["stop_dist_pct"].mean(),
                lev_at_1pct=lev1,
                thick_x=thick,
                verdict=("SURVIVES" if (m_tr > 0 and m_va > 0 and thick >= 5)
                         else "reject"),
                extra=extra)


def show(rows, title):
    print("\n" + "-" * 100)
    print(title)
    print("-" * 100)
    print(f"{'setup':<44}{'n_tr':>6}{'n_va':>6}{'choose%':>9}{'mid%':>8}"
          f"{'R_tr':>7}{'win%':>7}{'stop%':>7}{'lev@1%':>8}{'xcost':>7}  verdict")
    for r in rows:
        if r.get("verdict") == "INSUFFICIENT SAMPLE":
            print(f"{r['name']:<44}{r['n_tr']:>6}{r['n_va']:>6}"
                  f"{'':>9}{'':>8}{'':>7}{'':>7}{'':>7}{'':>8}{'':>7}  NOT ENOUGH TRADES")
            continue
        print(f"{r['name']:<44}{r['n_tr']:>6}{r['n_va']:>6}"
              f"{r['mean_tr']:>9.4f}{r['mean_va']:>8.4f}{r['R_tr']:>7.2f}"
              f"{r['win_tr']:>7.1f}{r['stop_tr']:>7.3f}{r['lev_at_1pct']:>7.1f}x"
              f"{r['thick_x']:>7.1f}  {r['verdict']}")


# --------------------------------------------------------- families
def structure_stop_long(d, idx, lookback_low=True):
    """Stop under the low of the retrace leg: the lowest low of the run of
    bars since the most recent confirmed TJR swing low, which is exactly
    the level that says the idea was wrong."""
    return d["mr_sl"].to_numpy()[idx]


def run_family_baseline(d, i_tr, i_va, out):
    """CHANCE BASELINE. Enter long at EVERY eligible bar in a clock window,
    stop at the last confirmed 2-candle swing low, exit at the session
    close or at a multiple of the stop distance."""
    mins = d["mins"].to_numpy()
    windows = [(570, 630, "09:30-10:30"), (630, 780, "10:30-13:00"),
               (780, 930, "13:00-15:30"), (570, 955, "all session")]
    for a, b, lab in windows:
        elig = np.where((mins >= a) & (mins < b))[0]
        sl = d["mr_sl"].to_numpy()[elig]
        entry_next = d["open"].to_numpy()[np.minimum(elig + 1, len(d) - 1)]
        for rmult, rlab in ((np.nan, "flat at close"), (1.0, "target 1R"), (2.0, "target 2R")):
            tp = (entry_next + rmult * (entry_next - sl)) if np.isfinite(rmult) else np.full(len(elig), np.nan)
            res = simulate(d, elig, +1, sl, tp)
            tr = res[res.sig_i < i_tr]; va = res[(res.sig_i >= i_tr) & (res.sig_i < i_va)]
            out.append(report(f"BASELINE long any bar {lab} {rlab}", tr, va))
        # short mirror, all-session only
        if lab == "all session":
            sh = d["mr_sh"].to_numpy()[elig]
            res = simulate(d, elig, -1, sh, None)
            tr = res[res.sig_i < i_tr]; va = res[(res.sig_i >= i_tr) & (res.sig_i < i_va)]
            out.append(report(f"BASELINE short any bar {lab} flat at close", tr, va))


def run_family_orb(d, i_tr, i_va, out, pops):
    """OPENING RANGE BREAK. The opening range is the high and low of the
    first N minutes. A break is a 5-minute CLOSE beyond it (a wick does
    not count - TJR's rule and a sane one). Stop at the opposite side of
    the opening range, which is the structure that says the break failed.
    """
    mins = d["mins"].to_numpy(); c = d["close"].to_numpy()
    for orm, tag in ((15, "or15"), (30, "or30"), (60, "or60")):
        orh = d[tag + "h"].to_numpy(); orl = d[tag + "l"].to_numpy()
        after = mins >= 570 + orm
        # first close above the OR high in the session
        for direction, lab in ((+1, "long"), (-1, "short")):
            if direction > 0:
                broke = after & (c > orh)
            else:
                broke = after & (c < orl)
            df = pd.DataFrame(dict(sid=d["sid"], broke=broke, i=np.arange(len(d))))
            first = df[df.broke].groupby("sid")["i"].first().to_numpy()
            if len(first) < 20:
                continue
            stop = orl[first] if direction > 0 else orh[first]
            # variant A: stop at the far side of the opening range
            res = simulate(d, first, direction, stop, None)
            tr = res[res.sig_i < i_tr]; va = res[(res.sig_i >= i_tr) & (res.sig_i < i_va)]
            out.append(report(f"OR{orm} break {lab}, stop far side of range", tr, va))
            pops[f"OR{orm}_{lab}_farside"] = res
            # variant B: stop at the last 2-candle swing (much tighter)
            stop2 = d["mr_sl"].to_numpy()[first] if direction > 0 else d["mr_sh"].to_numpy()[first]
            res2 = simulate(d, first, direction, stop2, None)
            tr2 = res2[res2.sig_i < i_tr]; va2 = res2[(res2.sig_i >= i_tr) & (res2.sig_i < i_va)]
            out.append(report(f"OR{orm} break {lab}, stop at 2-candle swing", tr2, va2))
            pops[f"OR{orm}_{lab}_swing"] = res2


def sweep_reversal(d, level_col, direction, t_start, t_end, confirm="bos"):
    """TJR-SHAPED SEQUENCE, at 5-minute resolution for BOTH the
    confirmation and the trigger.

    THIS IS NOT HIS METHOD AND THE FILE SAYS SO. His confirmation is on
    5-minute bars and his ENTRY TRIGGER is on 1-minute bars
    (step301_tjr_rules.md section 4). We hold no 1-minute data, so the
    trigger here is collapsed onto the same 5-minute bar as the
    confirmation. Round 301's mismatch 10.4 is exactly this class of
    error, so it is named rather than hidden. What is faithful: the
    2-candle swing definition, the body-close break-of-structure test,
    the per-trade structural stop with no floor, the 09:30-10:30 gate,
    and liquidity levels as targets.

    Sequence for a LONG:
      1. price WICKS below the marked level (low < level) inside the
         window - the sweep. A wick is enough, no close needed.
      2. afterwards, a bar CLOSES above the most recent confirmed
         2-candle swing high - break of structure up. That is the entry
         signal bar.
      3. stop = the lowest low traded between the sweep and the signal,
         which is the swing the move broke away from.
    """
    lo = d["low"].to_numpy(); hi = d["high"].to_numpy(); c = d["close"].to_numpy()
    mins = d["mins"].to_numpy(); sid = d["sid"].to_numpy()
    lvl = d[level_col].to_numpy()
    mr_sh = d["mr_sh"].to_numpy(); mr_sl = d["mr_sl"].to_numpy()

    sigs, stops, sweeps = [], [], []
    n = len(d)
    cur_sid = -1
    swept_at = -1
    for t in range(n):
        if sid[t] != cur_sid:
            cur_sid = sid[t]; swept_at = -1
        if not (t_start <= mins[t] < t_end):
            continue
        L = lvl[t]
        if not np.isfinite(L):
            continue
        if direction > 0:
            if lo[t] < L and swept_at < 0:
                swept_at = t
                continue
            if swept_at >= 0 and np.isfinite(mr_sh[t]) and c[t] > mr_sh[t]:
                stop = lo[swept_at:t + 1].min()
                if stop < c[t]:
                    sigs.append(t); stops.append(stop); sweeps.append(swept_at)
                swept_at = -1
        else:
            if hi[t] > L and swept_at < 0:
                swept_at = t
                continue
            if swept_at >= 0 and np.isfinite(mr_sl[t]) and c[t] < mr_sl[t]:
                stop = hi[swept_at:t + 1].max()
                if stop > c[t]:
                    sigs.append(t); stops.append(stop); sweeps.append(swept_at)
                swept_at = -1
    return np.array(sigs, dtype=int), np.array(stops), np.array(sweeps, dtype=int)


def run_family_sweep(d, i_tr, i_va, out, pops):
    combos = [("pdl", +1, "prev day low"), ("pdh", -1, "prev day high"),
              ("onl", +1, "overnight low"), ("onh", -1, "overnight high"),
              ("or30l", +1, "opening-range low"), ("or30h", -1, "opening-range high")]
    for col, dirn, lab in combos:
        for (a, b, wlab) in ((570, 630, "09:30-10:30"), (570, 720, "09:30-12:00"), (570, 955, "all session")):
            sig, stop, sw = sweep_reversal(d, col, dirn, a, b)
            if len(sig) == 0:
                continue
            side = "long" if dirn > 0 else "short"
            # exit 1: flat at session close
            res = simulate(d, sig, dirn, stop, None)
            tr = res[res.sig_i < i_tr]; va = res[(res.sig_i >= i_tr) & (res.sig_i < i_va)]
            out.append(report(f"sweep {lab} -> BOS {side} {wlab}, hold to close", tr, va))
            pops[f"sweep_{col}_{wlab}"] = res
            # exit 2 and 3: multiples of the structural stop
            entry_next = d["open"].to_numpy()[np.minimum(sig + 1, len(d) - 1)]
            for rm in (1.0, 2.0, 3.0):
                tp = entry_next + dirn * rm * abs(entry_next - stop)
                r2 = simulate(d, sig, dirn, stop, tp)
                t2 = r2[r2.sig_i < i_tr]; v2 = r2[(r2.sig_i >= i_tr) & (r2.sig_i < i_va)]
                out.append(report(f"sweep {lab} -> BOS {side} {wlab}, target {rm:.0f}R", t2, v2))


def run_filters_as_partitions(d, pops, i_tr, i_va, out):
    """A filter is a PARTITION of one trade population, never a re-run."""
    abv = d["above_sma200"].to_numpy()
    mins = d["mins"].to_numpy()
    prng = d["prev_rng"].to_numpy()
    med_rng = np.nanmedian(prng[:i_tr])
    for pname, res in pops.items():
        if len(res) < 60:
            continue
        base_times = set(res["sig_time"].tolist())
        parts = {
            "above 200-session avg": abv[res.sig_i.to_numpy()] == True,
            "below 200-session avg": abv[res.sig_i.to_numpy()] == False,
            "prev session range > median": prng[res.sig_i.to_numpy()] > med_rng,
            "prev session range < median": prng[res.sig_i.to_numpy()] <= med_rng,
            "signal before 11:00": mins[res.sig_i.to_numpy()] < 660,
            "signal after 11:00": mins[res.sig_i.to_numpy()] >= 660,
        }
        for lab, m in parts.items():
            sub = res[m]
            # strict-subset check by entry timestamp, per the round-400 lesson
            assert set(sub["sig_time"].tolist()) <= base_times, "not a subset"
            tr = sub[sub.sig_i < i_tr]; va = sub[(sub.sig_i >= i_tr) & (sub.sig_i < i_va)]
            out.append(report(f"[{pname}] {lab}", tr, va, extra="partition"))


def main():
    d = prep("SPY", "5m")
    i_tr, i_va = split_60_20_20(len(d))
    print(f"SPY 5-minute regular-hours bars: {len(d):,}  sessions {d['sid'].nunique():,}")
    print(f"choosing slice 0-{i_tr:,}  middle slice {i_tr:,}-{i_va:,}  "
          f"final 20% never opened")
    print(f"round-trip cost assumed {COST_RT}% of notional (also reported at {COST_RT_LOW}%)")

    out, pops = [], {}
    run_family_baseline(d, i_tr, i_va, out)
    show([r for r in out], "FAMILY 0 - CHANCE BASELINE: what entering at a random eligible bar produced")

    n0 = len(out)
    run_family_orb(d, i_tr, i_va, out, pops)
    show(out[n0:], "FAMILY 1 - OPENING RANGE BREAK")

    n1 = len(out)
    run_family_sweep(d, i_tr, i_va, out, pops)
    show(out[n1:], "FAMILY 2 - SWEEP OF A LIQUIDITY LEVEL THEN BREAK OF STRUCTURE (TJR-shaped, 5m trigger)")

    n2 = len(out)
    run_filters_as_partitions(d, pops, i_tr, i_va, out)
    show(out[n2:], "FAMILY 3 - FILTERS AS LIKE-FOR-LIKE PARTITIONS OF ONE TRADE POPULATION")

    df = pd.DataFrame(out)
    df.to_csv(f"{REPO}/step370_table_strategies.csv", index=False)
    ok = df[df.verdict == "SURVIVES"]
    print(f"\n{len(df)} settings tested, {len(ok)} survive both slices and clear "
          f"5x the round-trip cost.")
    if len(ok):
        print(ok[["name", "n_tr", "n_va", "mean_tr", "mean_va", "R_tr",
                  "stop_tr", "lev_at_1pct", "thick_x"]].to_string(index=False))


if __name__ == "__main__":
    main()
