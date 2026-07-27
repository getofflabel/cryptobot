"""
step474_tjr_index_1m.py - ROUND 474
DOES R450'S 1-MINUTE-TRIGGER FINDING TRANSFER TO THE INDEX?

Research only. No orders. No live file touched, imported or modified.
Nothing here is deployed by this script under any outcome.

THE ONE QUESTION
  Round 450 found that moving TJR's entry trigger from the 5-minute bar to
  the 1-minute bar - the resolution he actually specifies (step431 s0,
  step436 s4) - flips the gross sign on crypto: -0.0352% to +0.0551% of
  price per trade, t = 2.76 for the difference between the arms and
  t = 3.05 against a random control.

  Round 370 rejected the SAME SHAPE 72 cells out of 72 on 5-minute SPY, and
  closed by naming this exact limit as the reason its rejection might be
  wrong: it held no 1-minute bars, so the trigger was collapsed onto the
  5-minute confirmation bar.

  We now hold `data_alpaca_SPY_1m.parquet` and `data_alpaca_QQQ_1m.parquet`,
  2016-2026. So the limit round 370 named can be closed on the instrument
  round 370 actually tested.

  If the sign flips on the index too, the trigger resolution is a general
  fact about his method and round 370's verdict is formally overturned.
  If it does not, R450's result is crypto-specific and must be said so.

  NOTHING IS RE-TUNED. Arm A and arm B are R450's, unchanged. The report is
  the difference between the arms, its t, and the random control.

WHAT CHANGES FROM R450, AND WHY - ALL FORCED BY THE INSTRUMENT
  - REGULAR HOURS ONLY. Market orders are rejected outside them (R360), and
    R370 part 1 measured that an intraday-sized stop is gapped straight
    through on 41.5% of nights. Entries live in 09:30-16:00 New York.
  - ENTRY NO EARLIER THAN 09:50 (step436 s4 - he does not touch the first
    twenty minutes). Applied to the FILL bar, not the signal bar.
  - FLAT BY THE CLOSE. R450's 24-hour hold cap is meaningless on an
    instrument with a session end. Every position is force-exited at the
    close of the last bar of its own session, and a pending sweep that has
    not resolved by the close dies there rather than carrying overnight.
  - COST IS THE INDEX COST: 0.04% of notional round trip (R370's headline -
    SPY at a US broker, no commission, a penny spread and a little
    slippage), 0.02% also carried. Charged so the P&L is honest and used
    for nothing else (owner rule, 2026-07-25). Gross is reported beside
    every net number.
  - STRUCTURE IS READ WITHIN THE SESSION. The two-candle swing never pairs
    a 15:55 bar with the next 09:30 bar, and the most-recent-confirmed
    swing does not carry across the overnight gap. OURS, fixed before the
    run, never swept. It follows from being flat by the close: structure we
    would not still be trading against is not structure.

WHAT IS UNCHANGED FROM R450 AND FROM HIM
  - the two-candle swing everywhere, confirmed one bar late (step431 s2)
  - levels marked on the HIGH timeframes only: previous day, session highs
    and lows, 1-hour and 4-hour swings (step431 s5, s0). The overnight
    Asia and London sessions ARE marked - SPY trades 4,400-5,800 Asia and
    12,000-13,400 London 5-minute bars a year in this data - because
    marking overnight levels and trading them in the session is his
    procedure, not a liberty.
  - a level traded through is NOT a sweep until price reacts; the reaction
    IS the break of structure (step431 s4b). No reaction, no trade.
  - break of structure = a body close beyond the most recent confirmed
    swing, never a wick.
  - the sweep is hunted on the 5-minute, never the 1-minute; the ENTRY is
    triggered on the 1-minute (arm B) or collapsed onto the 5-minute
    confirmation (arm A, round 370's construction).
  - the stop is chart structure: the extreme price traded between the sweep
    and the entry. Size = risk / stop distance, so leverage is an OUTPUT
    and is reported, never chosen.
  - the 2-hour pending-sweep expiry (24 five-minute bars). OURS, carried
    over from R450 unchanged so the two rounds are comparable, and NOT
    swept as a parameter here either.

PROTOCOL
  60% choosing / 20% middle read once / final 20% NEVER OPENED unless a
  cell qualifies. Floors 30 choosing / 8 middle trades.
  Qualify = positive NET mean on choosing AND middle, pooled across SPY and
  QQQ, AND positive on BOTH assets individually, AND beating the
  same-machinery random-entry control. Then ONE test look, one cell at most.
  Expected-by-chance is printed in the same breath as any survivor count
  (rule earned R88/R100).
"""

import numpy as np
import pandas as pd

REPO = "/Users/wallacechen/cryptobot"
NY = "America/New_York"

COST_RT = 0.04          # % of notional, round trip: index at a US broker
COST_RT_LOW = 0.02      # % of notional, optimistic
MIN_TR, MIN_VA = 30, 8
PENDING_BARS_5M = 24    # 2 hours - OURS, carried from R450 unchanged
ENTRY_MIN_NY = 9 * 60 + 50      # 09:50, step436 s4 - applied to the FILL bar
RTH_OPEN, RTH_LAST_5M, RTH_LAST_1M = 9 * 60 + 30, 15 * 60 + 55, 15 * 60 + 59
ASSETS = ["SPY", "QQQ"]


# ------------------------------------------------------------------ data
def load(sym, tf):
    """Alpaca index parquet stores `timestamp` tz-aware UTC. Converted to a
    naive-UTC `t` so every downstream function matches step450's shape."""
    d = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_{tf}.parquet")
    d["timestamp"] = pd.to_datetime(d["timestamp"], utc=True)
    d = d.sort_values("timestamp").drop_duplicates("timestamp")
    ny = d["timestamp"].dt.tz_convert(NY)
    out = d[["open", "high", "low", "close"]].copy()
    out["t"] = d["timestamp"].dt.tz_localize(None)
    out["ny_mins"] = ny.dt.hour * 60 + ny.dt.minute
    out["ny_date"] = ny.dt.normalize().dt.tz_localize(None)
    return out[["t", "open", "high", "low", "close", "ny_mins",
                "ny_date"]].reset_index(drop=True)


def rth_only(d, last_min):
    m = d["ny_mins"].to_numpy()
    return d[(m >= RTH_OPEN) & (m <= last_min)].reset_index(drop=True)


def tjr_swings(o, h, l, c):
    """His two-candle swing, confirmed one bar late and stamped at that bar.
    high = up candle then down candle, level = the higher of the two WICKS.
    low  = down candle then up candle, level = the lower of the two WICKS.
    Nothing after bar t is used."""
    up, dn = c > o, c < o
    n = len(o)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    is_h = up[:-1] & dn[1:]
    is_l = dn[:-1] & up[1:]
    sh[1:] = np.where(is_h, np.maximum(h[:-1], h[1:]), np.nan)
    sl[1:] = np.where(is_l, np.minimum(l[:-1], l[1:]), np.nan)
    return sh, sl


def session_swings(d):
    """Two-candle swings that never pair the last bar of one session with
    the first bar of the next, then carried forward WITHIN the session and
    read as of the previous bar. OURS (see module docstring)."""
    sh, sl = tjr_swings(d["open"].to_numpy(), d["high"].to_numpy(),
                        d["low"].to_numpy(), d["close"].to_numpy())
    sess = d["ny_date"].to_numpy()
    crosses = np.empty(len(d), dtype=bool)
    crosses[0] = True
    crosses[1:] = sess[1:] != sess[:-1]
    sh[crosses] = np.nan
    sl[crosses] = np.nan
    key = d["ny_date"]
    out = []
    for x in (sh, sl):
        s = pd.Series(x)
        out.append(s.groupby(key).ffill().groupby(key).shift(1).to_numpy())
    return out[0], out[1]


def resample(d, minutes):
    """Higher timeframe built from the 5-minute bars on a UTC grid."""
    g = d.set_index("t").resample(f"{minutes}min")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last()}).dropna()
    return out.reset_index()


def htf_levels(full5, target_t, minutes):
    """Most recent CONFIRMED two-candle swing on the `minutes` chart, mapped
    onto `target_t`. A higher-timeframe candle is only known once it has
    closed, so the level is stamped at the close of the confirming candle.
    Built from the FULL tape - the chart does not stop overnight."""
    htf = resample(full5, minutes)
    sh, sl = tjr_swings(htf["open"].to_numpy(), htf["high"].to_numpy(),
                        htf["low"].to_numpy(), htf["close"].to_numpy())
    known = htf["t"] + pd.Timedelta(minutes=minutes)
    lv = pd.DataFrame({"t": known, "sh": sh, "sl": sl})
    tgt = pd.DataFrame({"t": target_t})
    hi = pd.merge_asof(tgt, lv[["t", "sh"]].dropna().sort_values("t"),
                       on="t", direction="backward")["sh"].to_numpy()
    lo = pd.merge_asof(tgt, lv[["t", "sl"]].dropna().sort_values("t"),
                       on="t", direction="backward")["sl"].to_numpy()
    return hi, lo


def session_levels(full5, target_t):
    """Asia / London / New York highs and lows on the New York clock, from
    the most recently COMPLETED session, read off the FULL tape. His
    procedure exactly: the highest and lowest traded price inside the
    window, not a pivot."""
    mins = full5["ny_mins"].to_numpy()
    day = full5["ny_date"]
    asia = (mins >= 18 * 60) | (mins < 3 * 60)
    lon = (mins >= 3 * 60) & (mins < 8 * 60 + 30)
    nyk = (mins >= 9 * 60 + 30) & (mins < 16 * 60)
    # Asia runs 18:00 -> 03:00 and crosses midnight: stamp the whole block
    # to the day it STARTED on so it is one session.
    asia_day = day - pd.to_timedelta((mins < 3 * 60).astype(int), unit="D")
    rows = []
    for mask, k in ((asia, asia_day), (lon, day), (nyk, day)):
        sub = full5[mask]
        agg = pd.DataFrame({"hi": sub.groupby(k[mask])["high"].max(),
                            "lo": sub.groupby(k[mask])["low"].min(),
                            "end": sub.groupby(k[mask])["t"].max()}).reset_index(drop=True)
        agg["known"] = agg["end"] + pd.Timedelta(minutes=5)
        rows.append(agg[["known", "hi", "lo"]])
    allr = pd.concat(rows).sort_values("known").reset_index(drop=True)
    tgt = pd.DataFrame({"t": target_t})
    hi = pd.merge_asof(tgt, allr[["known", "hi"]].rename(columns={"known": "t"}),
                       on="t", direction="backward")["hi"].to_numpy()
    lo = pd.merge_asof(tgt, allr[["known", "lo"]].rename(columns={"known": "t"}),
                       on="t", direction="backward")["lo"].to_numpy()
    return hi, lo


def prev_day_levels(rth5):
    """Previous REGULAR SESSION high and low - what a trader means by PDH
    and PDL on an index. Known at the open, uses no bar of today."""
    g = rth5.groupby("ny_date")
    hi = g["high"].max().shift(1)
    lo = g["low"].min().shift(1)
    return (rth5["ny_date"].map(hi).to_numpy(),
            rth5["ny_date"].map(lo).to_numpy())


def prep(sym):
    full5 = load(sym, "5m")
    d5 = rth_only(full5, RTH_LAST_5M)
    d1 = rth_only(load(sym, "1m"), RTH_LAST_1M)
    t0 = max(d5["t"].iloc[0], d1["t"].iloc[0])
    d5 = d5[d5["t"] >= t0].reset_index(drop=True)
    d1 = d1[d1["t"] >= t0].reset_index(drop=True)

    d5["mr_sh"], d5["mr_sl"] = session_swings(d5)
    d1["mr_sh"], d1["mr_sl"] = session_swings(d1)

    d5["pdh"], d5["pdl"] = prev_day_levels(d5)
    d5["sesh"], d5["sesl"] = session_levels(full5, d5["t"])
    for mins, tag in ((60, "h1"), (240, "h4")):
        d5[tag + "h"], d5[tag + "l"] = htf_levels(full5, d5["t"], mins)

    # index of the 1-minute bar at or after each 5-minute bar's close
    d5["i1_next"] = np.searchsorted(
        d1["t"].to_numpy(), (d5["t"] + pd.Timedelta(minutes=5)).to_numpy(),
        side="left")

    # last bar index of each session, on both tapes - "flat by the close"
    d5["sess_end"] = _session_end_idx(d5)
    d1["sess_end"] = _session_end_idx(d1)
    return d5, d1


def _session_end_idx(d):
    """Positional index of the LAST bar of each row's own session."""
    idx = pd.Series(np.arange(len(d)))
    return idx.groupby(d["ny_date"].to_numpy()).transform("max").to_numpy()


# -------------------------------------------------------- the sequence
def scan_sweeps(d5, level_col, direction):
    """Per confirmed sweep: the 5-minute index of the sweep bar and of the
    bar whose BODY closed through structure the other way.

    LONG: a bar's LOW trades below the marked level (a wick is enough) ->
    pending. Then a bar CLOSES above the most recent confirmed 5-minute
    swing high - the reaction, which is what turns a level being traded
    through into a sweep (step431 s4b). Pending dies after
    PENDING_BARS_5M bars, at the session close, or on a fresh sweep."""
    lo = d5["low"].to_numpy(); hi = d5["high"].to_numpy()
    c = d5["close"].to_numpy()
    lvl = d5[level_col].to_numpy()
    mr_sh = d5["mr_sh"].to_numpy(); mr_sl = d5["mr_sl"].to_numpy()
    sess = d5["ny_date"].to_numpy()
    n = len(d5)
    sweeps, sigs = [], []
    pend = -1
    for t in range(n):
        if pend >= 0 and (t - pend > PENDING_BARS_5M or sess[t] != sess[pend]):
            pend = -1
        L = lvl[t]
        if not np.isfinite(L):
            continue
        if direction > 0:
            if lo[t] < L:
                pend = t if pend < 0 else pend
                continue
            if pend >= 0 and np.isfinite(mr_sh[t]) and c[t] > mr_sh[t]:
                sweeps.append(pend); sigs.append(t); pend = -1
        else:
            if hi[t] > L:
                pend = t if pend < 0 else pend
                continue
            if pend >= 0 and np.isfinite(mr_sl[t]) and c[t] < mr_sl[t]:
                sweeps.append(pend); sigs.append(t); pend = -1
    return np.array(sweeps, dtype=int), np.array(sigs, dtype=int)


def trigger_1m(d5, d1, sweeps, direction):
    """HIS actual trigger. The sweep is pending on the 5-minute; the entry
    is the first 1-MINUTE body close through the most recent confirmed
    1-minute swing the other way, inside the same 2-hour pending window AND
    the same session. Returns (1-minute entry index, sweep index) pairs."""
    c1 = d1["close"].to_numpy()
    sh1 = d1["mr_sh"].to_numpy(); sl1 = d1["mr_sl"].to_numpy()
    sess1 = d1["ny_date"].to_numpy()
    end1 = d1["sess_end"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    sess5 = d5["ny_date"].to_numpy()
    n1 = len(d1)
    ent, sw = [], []
    for s in sweeps:
        a = i1n[s]
        if a >= n1 or sess1[a] != sess5[s]:
            continue
        b = min(end1[a], a + PENDING_BARS_5M * 5)
        if direction > 0:
            m = (c1[a:b + 1] > sh1[a:b + 1]) & np.isfinite(sh1[a:b + 1])
        else:
            m = (c1[a:b + 1] < sl1[a:b + 1]) & np.isfinite(sl1[a:b + 1])
        k = np.flatnonzero(m)
        if len(k) == 0:
            continue
        ent.append(a + k[0]); sw.append(s)
    return np.array(ent, dtype=int), np.array(sw, dtype=int)


# -------------------------------------------------------------- scoring
def simulate(bars, sig_idx, direction, stop_px, r_target, cost=COST_RT):
    """Every candidate is scored INDEPENDENTLY - no shared position slot, so
    any filtered set is a strict subset of the same population (round 400's
    lesson). Fill is the OPEN of the bar after the signal, and that bar must
    be at or after 09:50 and inside the same session. If one bar touches
    both stop and target, the STOP is taken first. Anything still open at
    the last bar of the session is closed there."""
    o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
    l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    ts = bars["t"].to_numpy(); mins = bars["ny_mins"].to_numpy()
    send = bars["sess_end"].to_numpy()
    n = len(bars)
    recs = []
    for k, i in enumerate(sig_idx):
        j = i + 1
        if j >= n or j > send[i] or mins[j] < ENTRY_MIN_NY:
            continue
        entry = o[j]
        sp = stop_px[k]
        if not np.isfinite(sp) or entry <= 0:
            continue
        if direction > 0 and sp >= entry:
            continue
        if direction < 0 and sp <= entry:
            continue
        risk = abs(entry - sp)
        tp = (entry + direction * r_target * risk) if r_target else np.nan
        end = int(send[i])            # flat by the close, always
        hs, ls = h[j:end + 1], l[j:end + 1]
        if len(hs) == 0:
            continue
        if direction > 0:
            i_stop = np.flatnonzero(ls <= sp)
            i_tgt = np.flatnonzero(hs >= tp) if np.isfinite(tp) else np.array([], int)
        else:
            i_stop = np.flatnonzero(hs >= sp)
            i_tgt = np.flatnonzero(ls <= tp) if np.isfinite(tp) else np.array([], int)
        a = i_stop[0] if len(i_stop) else np.inf
        b = i_tgt[0] if len(i_tgt) else np.inf
        if a <= b and np.isfinite(a):
            exit_px, reason, held = sp, "stop", int(a) + 1
        elif np.isfinite(b):
            exit_px, reason, held = tp, "target", int(b) + 1
        else:
            exit_px, reason, held = c[end], "close", end - j + 1
        gross = direction * (exit_px - entry) / entry * 100.0
        sd = risk / entry * 100.0
        recs.append((i, ts[i], sd, gross, gross - cost, gross - COST_RT_LOW,
                     (gross - cost) / sd if sd > 0 else np.nan, reason, held))
    return pd.DataFrame(recs, columns=[
        "sig_i", "sig_t", "stop_pct", "gross_pct", "net_pct", "net_low_pct",
        "net_R", "reason", "bars_held"])


def slice_by_time(res, t_tr, t_va):
    return (res[res.sig_t < t_tr],
            res[(res.sig_t >= t_tr) & (res.sig_t < t_va)],
            res[res.sig_t >= t_va])


def summarise(name, tr, va):
    if len(tr) < MIN_TR or len(va) < MIN_VA:
        return dict(name=name, n_tr=len(tr), n_va=len(va), verdict="thin",
                    mean_tr=np.nan, mean_va=np.nan, gross_tr=np.nan,
                    gross_va=np.nan, stop_tr=np.nan, lev=np.nan, R_tr=np.nan,
                    win_tr=np.nan)
    m_tr, m_va = tr["net_pct"].mean(), va["net_pct"].mean()
    stop = tr["stop_pct"].mean()
    return dict(name=name, n_tr=len(tr), n_va=len(va), mean_tr=m_tr,
                mean_va=m_va, gross_tr=tr["gross_pct"].mean(),
                gross_va=va["gross_pct"].mean(), R_tr=tr["net_R"].mean(),
                win_tr=(tr["net_pct"] > 0).mean() * 100, stop_tr=stop,
                lev=1.0 / stop if stop > 0 else np.nan,
                verdict="qualifies" if (m_tr > 0 and m_va > 0) else "reject")


def show(rows, title):
    print("\n" + "-" * 112)
    print(title)
    print("-" * 112)
    print(f"{'cell':<46}{'n_tr':>7}{'n_va':>6}{'grossTR':>9}{'netTR':>9}"
          f"{'netVA':>9}{'R_tr':>7}{'win%':>7}{'stop%':>8}{'lev@1%':>8}  verdict")
    for r in rows:
        if r["verdict"] == "thin":
            print(f"{r['name']:<46}{r['n_tr']:>7}{r['n_va']:>6}"
                  f"{'':>9}{'':>9}{'':>9}{'':>7}{'':>7}{'':>8}{'':>8}  too few trades")
            continue
        print(f"{r['name']:<46}{r['n_tr']:>7}{r['n_va']:>6}"
              f"{r['gross_tr']:>9.4f}{r['mean_tr']:>9.4f}{r['mean_va']:>9.4f}"
              f"{r['R_tr']:>7.2f}{r['win_tr']:>7.1f}{r['stop_tr']:>8.3f}"
              f"{r['lev']:>7.1f}x  {r['verdict']}")


# ----------------------------------------------------------------- round
LEVELS = [("pdl", +1, "prev day low"), ("pdh", -1, "prev day high"),
          ("sesl", +1, "last session low"), ("sesh", -1, "last session high"),
          ("h1l", +1, "1h swing low"), ("h1h", -1, "1h swing high"),
          ("h4l", +1, "4h swing low"), ("h4h", -1, "4h swing high")]
TARGETS = [(None, "hold to close"), (1.0, "target 1R"), (2.0, "target 2R"),
           (3.0, "target 3R")]


def run_asset(sym, t_tr, t_va, store):
    d5, d1 = prep(sym)
    lo5 = d5["low"].to_numpy(); hi5 = d5["high"].to_numpy()
    lo1 = d1["low"].to_numpy(); hi1 = d1["high"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    rows = []
    for col, dirn, lab in LEVELS:
        sw, sig5 = scan_sweeps(d5, col, dirn)
        if len(sig5) == 0:
            continue
        # ARM A - round 370's construction: the 5-minute confirmation IS the
        # trigger. Stop = the extreme traded between sweep and signal.
        stopA = np.array([lo5[a:b + 1].min() if dirn > 0 else hi5[a:b + 1].max()
                          for a, b in zip(sw, sig5)])
        # ARM B - HIS construction: the 1-minute body close is the trigger.
        ent1, swB = trigger_1m(d5, d1, sw, dirn)
        if len(ent1):
            a1 = i1n[swB]
            stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                              else hi1[max(0, a):b + 1].max()
                              for a, b in zip(a1, ent1)])
        for rt, rlab in TARGETS:
            resA = simulate(d5, sig5, dirn, stopA, rt)
            trA, vaA, _ = slice_by_time(resA, t_tr, t_va)
            nm = f"{lab} -> 5m BOS, {rlab}"
            rows.append(summarise(nm, trA, vaA))
            store.setdefault((nm, "A"), []).append((sym, resA))
            if len(ent1):
                resB = simulate(d1, ent1, dirn, stopB, rt)
                trB, vaB, _ = slice_by_time(resB, t_tr, t_va)
                nmB = f"{lab} -> 1m BOS, {rlab}"
                rows.append(summarise(nmB, trB, vaB))
                store.setdefault((nmB, "B"), []).append((sym, resB))
    return d5, d1, rows


def control_trades(d5, every=60):
    """CHANCE CONTROL. The same machinery entered at a random eligible
    moment: every 60th regular-hours 5-minute bar, stop at the most recent
    confirmed swing, both directions, flat by the close."""
    out = []
    for dirn in (+1, -1):
        idx = np.arange(0, len(d5) - 1, every)
        stop = (d5["mr_sl"].to_numpy() if dirn > 0 else d5["mr_sh"].to_numpy())[idx]
        for rt in (None, 2.0):
            out.append((dirn, rt, simulate(d5, idx, dirn, stop, rt)))
    return out


def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def main():
    # the shared clock: SPY fixes the slice boundaries, then the SAME
    # timestamps are applied to QQQ so the slices mean the same dates.
    s5, s1 = load("SPY", "5m"), load("SPY", "1m")
    t0 = max(s5["t"].iloc[0], s1["t"].iloc[0])
    t1 = min(s5["t"].iloc[-1], s1["t"].iloc[-1])
    span = t1 - t0
    t_tr, t_va = t0 + span * 0.60, t0 + span * 0.80
    del s5, s1

    print("=" * 112)
    print("ROUND 474 - DOES R450'S 1-MINUTE TRIGGER FINDING TRANSFER TO THE INDEX?")
    print("=" * 112)
    print(f"shared window {t0:%Y-%m-%d} to {t1:%Y-%m-%d} UTC  ({span.days} days)")
    print(f"choosing slice  -> {t_tr:%Y-%m-%d %H:%M}")
    print(f"middle slice    -> {t_va:%Y-%m-%d %H:%M}   read once")
    print(f"final slice     -> {t1:%Y-%m-%d}   NEVER OPENED unless a cell qualifies")
    print(f"cost charged: {COST_RT}% of notional round trip (index at a US broker); "
          f"{COST_RT_LOW}% also carried. Gross reported beside every net.")
    print("regular hours only; fill no earlier than 09:50 New York; FLAT BY THE "
          "CLOSE, every position and every pending sweep.")
    print(f"pending sweep expires after {PENDING_BARS_5M} 5-minute bars (2h), "
          "carried from R450 unchanged and never swept.")

    store, controls = {}, {}
    for sym in ASSETS:
        d5, d1, rows = run_asset(sym, t_tr, t_va, store)
        show(rows, f"{sym}   regular-hours 5m bars {len(d5):,}   1m bars {len(d1):,}")
        controls[sym] = control_trades(d5)
        crows = []
        for dirn, rt, res in controls[sym]:
            tr, va, _ = slice_by_time(res, t_tr, t_va)
            crows.append(summarise(
                f"CONTROL random entry {'long' if dirn > 0 else 'short'}, "
                f"{'hold to close' if rt is None else 'target 2R'}", tr, va))
        show(crows, f"CHANCE CONTROL on {sym} - a random entry with the same "
                    f"stop machinery")

    # ---------------------------------------------------- pooled read
    print("\n" + "=" * 112)
    print("POOLED ACROSS SPY + QQQ  (a cell must work on the market, not one ETF)")
    print("=" * 112)
    pooled = []
    for (nm, arm), parts in store.items():
        allr = pd.concat([r for _, r in parts])
        tr, va, _ = slice_by_time(allr, t_tr, t_va)
        s = summarise(nm, tr, va)
        if s["verdict"] == "thin":
            continue
        indiv = []
        for _, r in parts:
            t_, _, _ = slice_by_time(r, t_tr, t_va)
            indiv.append(t_["net_pct"].mean() if len(t_) >= 10 else np.nan)
        s["n_assets_pos"] = int(np.nansum(np.array(indiv) > 0))
        s["arm"] = arm
        pooled.append(s)
    pooled.sort(key=lambda r: -(r["mean_tr"] if np.isfinite(r["mean_tr"]) else -9))
    show(pooled, "pooled cells, best choosing-slice net first")
    df = pd.DataFrame(pooled)
    df.to_csv(f"{REPO}/step474_table.csv", index=False)

    n_cells = len(pooled)
    q = df[(df.verdict == "qualifies") & (df.n_assets_pos >= 2)]
    print(f"\n{n_cells} pooled cells scored. {len(q)} are positive on BOTH the "
          f"choosing and middle slice AND positive on BOTH assets.")
    print(f"EXPECTED BY CHANCE if there were no edge at all: a symmetric "
          f"zero-mean cell passes both slices about 1 time in 4 and both assets "
          f"about 1 in 4, so roughly {n_cells/8:.0f} of {n_cells} would pass on "
          f"luck alone.")
    if len(q):
        print(q[["name", "arm", "n_tr", "n_va", "gross_tr", "mean_tr",
                 "mean_va", "n_assets_pos", "stop_tr", "lev"]].to_string(index=False))

    # ------------------------------------------------- arm A versus arm B
    print("\n" + "=" * 112)
    print("THE WHOLE QUESTION: DOES THE 1-MINUTE TRIGGER CHANGE THE ANSWER ON "
          "THE INDEX?")
    print("=" * 112)
    print("choosing slice only. GROSS, because the question is about the method's")
    print("signal, not about what a broker charges to collect it.")

    arms = {"A": [], "B": []}
    for (nm, arm), parts in store.items():
        for _, res in parts:
            arms[arm].append(res[res.sig_t < t_tr])

    print(f"\n{'construction':<46}{'trades':>9}{'mean gross':>12}{'t':>8}"
          f"{'median stop':>14}{'lev @1% risk':>14}")
    uniq = {}
    for arm, lab in (("A", "5-minute trigger (round 370's construction)"),
                     ("B", "1-MINUTE trigger (his construction)")):
        # the four target settings score the SAME entries, so one row per
        # entry is the population for a significance test.
        u = pd.concat(arms[arm]).drop_duplicates(subset=["sig_t", "stop_pct"])
        uniq[arm] = u
        t, n = tstat(u["gross_pct"])
        s = u["stop_pct"].median()
        print(f"{lab:<46}{n:>9,}{u['gross_pct'].mean():>11.4f}%{t:>8.2f}"
              f"{s:>13.3f}%{1/s:>13.1f}x")

    ctl = pd.concat([res[res.sig_t < t_tr] for sym in ASSETS
                     for dirn, rt, res in controls[sym] if rt is None])
    t, n = tstat(ctl["gross_pct"])
    sc = ctl["stop_pct"].median()
    print(f"{'CONTROL random entry, same stop machinery':<46}{n:>9,}"
          f"{ctl['gross_pct'].mean():>11.4f}%{t:>8.2f}{sc:>13.3f}%{1/sc:>13.1f}x")

    a, b = uniq["A"], uniq["B"]
    diff = b["gross_pct"].mean() - a["gross_pct"].mean()
    se = np.sqrt(b["gross_pct"].var(ddof=1) / len(b)
                 + a["gross_pct"].var(ddof=1) / len(a))
    print(f"\ndifference, 1-minute trigger minus 5-minute trigger: "
          f"{diff:+.4f}% of price per trade, t = {diff/se:.2f}")
    dc = b["gross_pct"].mean() - ctl["gross_pct"].mean()
    sec = np.sqrt(b["gross_pct"].var(ddof=1) / len(b)
                  + ctl["gross_pct"].var(ddof=1) / len(ctl))
    print(f"difference, 1-minute trigger minus RANDOM ENTRY:      "
          f"{dc:+.4f}% of price per trade, t = {dc/sec:.2f}")
    print(f"\nR450 ON CRYPTO, for comparison: 5m arm -0.0352% (t -1.40), "
          f"1m arm +0.0551% (t +2.63),")
    print(f"                                difference +0.0903% (t 2.76), "
          f"versus random +0.1066% (t 3.05).")
    print(f"\none index round trip costs {COST_RT:.2f}% of notional. The 1-minute "
          f"arm's gross mean is {b['gross_pct'].mean()/COST_RT:.2f}x that cost. "
          f"Stated, not used to decide anything.")

    # per-asset split of the same comparison - a transfer claim needs both
    print(f"\n{'per asset, choosing slice, gross':<30}{'5m arm':>22}"
          f"{'1m arm':>22}{'difference':>16}")
    for sym in ASSETS:
        ua = pd.concat([res[res.sig_t < t_tr] for (nm, arm), parts in store.items()
                        if arm == "A" for s_, res in parts if s_ == sym]
                       ).drop_duplicates(subset=["sig_t", "stop_pct"])
        ub = pd.concat([res[res.sig_t < t_tr] for (nm, arm), parts in store.items()
                        if arm == "B" for s_, res in parts if s_ == sym]
                       ).drop_duplicates(subset=["sig_t", "stop_pct"])
        ta, _ = tstat(ua["gross_pct"]); tb, _ = tstat(ub["gross_pct"])
        d_ = ub["gross_pct"].mean() - ua["gross_pct"].mean()
        print(f"{sym:<30}{ua['gross_pct'].mean():>13.4f}% (t{ta:>5.2f})"
              f"{ub['gross_pct'].mean():>13.4f}% (t{tb:>5.2f}){d_:>15.4f}%")

    # ------------------------------------------------ stop-distance census
    print("\n" + "=" * 112)
    print("STOP-DISTANCE CENSUS ON THE INDEX - the durable half")
    print("distance from price to the structure that says the idea was wrong, as")
    print("a PRICE move (not a change in the position's value). Regular hours.")
    print("=" * 112)
    print(f"{'symbol':<10}{'5m swing':>11}{'1m swing':>11}{'ratio':>8}"
          f"{'lev@1% 5m':>12}{'lev@1% 1m':>12}")
    for sym in ASSETS:
        d5, d1 = prep(sym)
        out = []
        for dd in (d5, d1):
            c_ = dd["close"].to_numpy()
            dist = (c_ - dd["mr_sl"].to_numpy()) / c_ * 100.0
            dist = dist[np.isfinite(dist) & (dist > 0)]
            out.append(float(np.median(dist)))
        m5, m1 = out
        print(f"{sym:<10}{m5:>10.3f}%{m1:>10.3f}%{m1/m5:>8.2f}"
              f"{1/m5:>11.1f}x{1/m1:>11.1f}x")
    print("\nR370 measured the SPY 5-minute two-candle swing at 0.092% of price.")
    print("US law caps leverage at 10x regardless of what the structure permits.")

    return df, t_tr, t_va, store


if __name__ == "__main__":
    main()
