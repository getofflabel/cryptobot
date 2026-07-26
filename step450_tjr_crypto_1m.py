"""
step450_tjr_crypto_1m.py - ROUND 450
TJR'S SWEEP -> BREAK OF STRUCTURE, ON THE MARKET THE DESK IS ACTUALLY ARMED
IN, WITH THE 1-MINUTE ENTRY TRIGGER HE ACTUALLY SPECIFIES.

Research only. No orders. No live file touched. Nothing here is deployed by
this script under any outcome.

WHY THIS ROUND EXISTS
  Round 370 ran a TJR-shaped sweep-then-break-of-structure on 5-minute SPY
  and rejected it 72 cells out of 72. It closed with one honest limit, in
  its own words: his confirmation is on the 5-minute and his ENTRY TRIGGER
  is on the 1-MINUTE (step431 section 0, step436 section 4), and the project
  held no 1-minute data, so the trigger was collapsed onto the 5-minute
  confirmation bar. It also ran on the S&P, which is not the market the desk
  has armed.

  Both gaps are now closed for crypto. We hold Alpaca 1-minute bars from
  2026-03-01 on eight pairs, and crypto is the ONE book that is armed.

  So this is not "does his method work" - that is not a question this desk
  is allowed to ask (professionals are instruction). It is WHERE it applies:
  on the instrument we trade, at the resolution he trades it.

WHAT IS FAITHFUL TO HIM, AND WHAT IS OURS
  faithful:
    - the two-candle swing (step431 s2 / step436 s2), used for structure on
      every timeframe, never a fractal
    - levels marked on the HIGH timeframes only - previous day, session
      highs and lows, 1-hour and 4-hour swings (step431 s5, s0)
    - a level traded through is NOT a sweep until price reacts; the reaction
      IS the break of structure (step431 s4b). No reaction, no trade, ever.
    - break of structure = a candle BODY CLOSE beyond the most recent
      confirmed swing, not a wick
    - the sweep is hunted on the 5-minute, never on the 1-minute (he is
      explicit), and the ENTRY is triggered on the 1-minute
    - the stop is chart structure: the extreme price traded between the
      sweep and the entry. Never a swept percentage. Size = risk / stop
      distance, so leverage is an OUTPUT and is reported, never chosen.
  ours, and labelled as ours:
    - the UTC midnight day boundary, which is the LIVE desk's decision
      (tjr_crypto.py DAY_BOUNDARY_HOUR_UTC) - on a 24/7 market nothing
      decides it for us
    - a pending sweep expires after 2 hours with no break of structure.
      He never gives a number. 2 hours is stated, fixed before running, and
      NOT swept as a parameter.
    - a 24-hour hold cap. He goes flat at the session end on an instrument
      that has one; crypto has none.
    - session windows read on the New York clock (Asia 18:00-03:00, London
      03:00-08:30, New York 09:30-17:00) because those are real-world
      trading hours, while the DAY is cut at UTC per the live desk.

COSTS
  Charged, always, so the P&L is honest - and used for NOTHING else. They
  do not gate a cell, decline a trade or rank an instrument (owner rule,
  2026-07-25). Headline is 0.50% of notional for a round trip: Alpaca
  crypto taker at 0.25% a side. Gross is reported beside every net number
  so the venue cost can be separated from the method.

PROTOCOL
  60% choosing / 20% middle read once / final 20% NEVER OPENED unless a
  cell qualifies. Floors 30 choosing / 8 middle trades.
  Qualify = positive NET mean on choosing AND middle, pooled across the
  three primary assets, AND positive on at least 2 of the 3 individually,
  AND beating the same-machinery random-entry control. Then ONE test look,
  for at most one cell.
  Expected-by-chance is printed in the same breath as any survivor count
  (rule earned R88/R100).
"""

import sys
import numpy as np
import pandas as pd

REPO = "/Users/wallacechen/cryptobot"
NY = "America/New_York"

COST_RT = 0.50          # % of notional, round trip: Alpaca crypto taker x2
COST_RT_LOW = 0.30      # % of notional, maker in / taker out
MIN_TR, MIN_VA = 30, 8
PENDING_BARS_5M = 24    # 2 hours - OURS, fixed before running
MAX_HOLD_MIN = 24 * 60  # 24 hours - OURS
PRIMARY = ["BTCUSD", "ETHUSD", "SOLUSD"]
TRANSFER = ["LINKUSD", "LTCUSD", "DOTUSD", "XRPUSD", "ADAUSD"]


# ------------------------------------------------------------------ data
def load(sym, tf):
    """The parquet stores `t` as the bar START in NAIVE UTC - the live
    desk's convention (tjr_crypto.to_utc_frame). Kept exactly."""
    d = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_{tf}.parquet")
    d = d[["t", "open", "high", "low", "close"]].copy()
    d["t"] = pd.to_datetime(d["t"])
    d = d.sort_values("t").drop_duplicates("t").reset_index(drop=True)
    ny = d["t"].dt.tz_localize("UTC").dt.tz_convert(NY)
    d["ny_mins"] = ny.dt.hour * 60 + ny.dt.minute
    d["ny_date"] = ny.dt.date
    d["utc_day"] = d["t"].dt.normalize()
    return d


def tjr_swings(o, h, l, c):
    """His two-candle swing, confirmed one bar late and stamped at that bar.

    high = up candle then down candle, level = the higher of the two WICKS.
    low  = down candle then up candle, level = the lower of the two WICKS.
    Nothing after bar t is used.
    """
    up, dn = c > o, c < o
    n = len(o)
    sh = np.full(n, np.nan)
    sl = np.full(n, np.nan)
    is_h = up[:-1] & dn[1:]
    is_l = dn[:-1] & up[1:]
    sh[1:] = np.where(is_h, np.maximum(h[:-1], h[1:]), np.nan)
    sl[1:] = np.where(is_l, np.minimum(l[:-1], l[1:]), np.nan)
    return sh, sl


def ffill_shift(x):
    """Most recent confirmed value as of the PREVIOUS bar, so a close is
    never compared against a level built out of that same bar."""
    s = pd.Series(x).ffill().shift(1)
    return s.to_numpy()


def resample(d, minutes):
    """Build a higher timeframe out of the 5-minute bars, on a UTC grid -
    the same boundary the live crypto desk uses."""
    g = d.set_index("t").resample(f"{minutes}min")
    out = pd.DataFrame({
        "open": g["open"].first(), "high": g["high"].max(),
        "low": g["low"].min(), "close": g["close"].last()}).dropna()
    return out.reset_index()


def htf_levels(d5, minutes):
    """The most recent CONFIRMED two-candle swing on the `minutes` chart,
    mapped onto every 5-minute bar. A higher-timeframe candle is only known
    once it has closed, so the level is stamped at the close of the
    confirming candle and read on the 5-minute bars after that instant."""
    htf = resample(d5, minutes)
    sh, sl = tjr_swings(htf["open"].to_numpy(), htf["high"].to_numpy(),
                        htf["low"].to_numpy(), htf["close"].to_numpy())
    known_at = htf["t"] + pd.Timedelta(minutes=minutes)   # candle close time
    lv = pd.DataFrame({"t": known_at, "sh": sh, "sl": sl}).dropna(how="all")
    m = pd.merge_asof(d5[["t"]], lv.sort_values("t"), on="t",
                      direction="backward")
    # carry each side forward independently
    hi = pd.merge_asof(d5[["t"]], lv[["t", "sh"]].dropna().sort_values("t"),
                       on="t", direction="backward")["sh"].to_numpy()
    lo = pd.merge_asof(d5[["t"]], lv[["t", "sl"]].dropna().sort_values("t"),
                       on="t", direction="backward")["sl"].to_numpy()
    del m
    return hi, lo


def session_levels(d5):
    """Asia / London / New York highs and lows, on the New York clock, from
    the most recently COMPLETED session. His procedure exactly: the highest
    and lowest traded price inside the window, not a pivot."""
    ny = d5["t"].dt.tz_localize("UTC").dt.tz_convert(NY)
    mins = d5["ny_mins"].to_numpy()
    day = pd.to_datetime(ny.dt.date)
    # Asia runs 18:00 -> 03:00 and crosses midnight: stamp it to the day it
    # STARTED on, so the whole block is one session.
    asia = (mins >= 18 * 60) | (mins < 3 * 60)
    lon = (mins >= 3 * 60) & (mins < 8 * 60 + 30)
    nyk = (mins >= 9 * 60 + 30) & (mins < 17 * 60)
    asia_day = day - pd.to_timedelta((mins < 3 * 60).astype(int), unit="D")
    keys = {"asia": (asia, asia_day), "london": (lon, day), "ny": (nyk, day)}
    ends = {}   # (session end timestamp, high, low)
    rows = []
    for name, (mask, k) in keys.items():
        sub = d5[mask].copy()
        sub["k"] = k[mask.nonzero()[0]].to_numpy() if hasattr(k, "to_numpy") else k[mask]
        g = sub.groupby("k")
        agg = pd.DataFrame({"hi": g["high"].max(), "lo": g["low"].min(),
                            "end": g["t"].max()}).reset_index()
        agg["known"] = agg["end"] + pd.Timedelta(minutes=5)
        rows.append(agg[["known", "hi", "lo"]])
    allr = pd.concat(rows).sort_values("known").reset_index(drop=True)
    hi = pd.merge_asof(d5[["t"]], allr[["known", "hi"]].rename(
        columns={"known": "t"}), on="t", direction="backward")["hi"].to_numpy()
    lo = pd.merge_asof(d5[["t"]], allr[["known", "lo"]].rename(
        columns={"known": "t"}), on="t", direction="backward")["lo"].to_numpy()
    del ends
    return hi, lo


def prev_day_levels(d5):
    g = d5.groupby("utc_day")
    hi = g["high"].max().shift(1)
    lo = g["low"].min().shift(1)
    return (d5["utc_day"].map(hi).to_numpy(),
            d5["utc_day"].map(lo).to_numpy())


def prep(sym):
    d5 = load(sym, "5m")
    d1 = load(sym, "1m")
    # the shared window: everything runs where BOTH charts exist, so the
    # 5-minute arm and the 1-minute arm score the same tape.
    t0 = max(d5["t"].iloc[0], d1["t"].iloc[0])
    d5 = d5[d5["t"] >= t0].reset_index(drop=True)
    d1 = d1[d1["t"] >= t0].reset_index(drop=True)

    sh5, sl5 = tjr_swings(d5["open"].to_numpy(), d5["high"].to_numpy(),
                          d5["low"].to_numpy(), d5["close"].to_numpy())
    d5["mr_sh"] = ffill_shift(sh5)
    d5["mr_sl"] = ffill_shift(sl5)
    sh1, sl1 = tjr_swings(d1["open"].to_numpy(), d1["high"].to_numpy(),
                          d1["low"].to_numpy(), d1["close"].to_numpy())
    d1["mr_sh"] = ffill_shift(sh1)
    d1["mr_sl"] = ffill_shift(sl1)

    pdh, pdl = prev_day_levels(d5)
    d5["pdh"], d5["pdl"] = pdh, pdl
    sesh, sesl = session_levels(d5)
    d5["sesh"], d5["sesl"] = sesh, sesl
    for mins, tag in ((60, "h1"), (240, "h4")):
        hi, lo = htf_levels(d5, mins)
        d5[tag + "h"], d5[tag + "l"] = hi, lo

    # index of the 1-minute bar that starts at or after each 5-minute close
    d5["i1_next"] = np.searchsorted(d1["t"].to_numpy(),
                                    (d5["t"] + pd.Timedelta(minutes=5)).to_numpy(),
                                    side="left")
    return d5, d1


# -------------------------------------------------------- the sequence
def scan_sweeps(d5, level_col, direction):
    """Returns, per confirmed sweep, the 5-minute index of the sweep bar and
    of the 5-minute bar whose BODY closed through structure the other way.

    LONG: a 5-minute bar's LOW trades below the marked level (wick is
    enough, no close needed) -> pending. Then a bar CLOSES above the most
    recent confirmed 5-minute swing high -> the reaction, which is what
    turns a level being traded through into a sweep (step431 s4b).
    Pending dies after PENDING_BARS_5M with no reaction. It also dies if a
    fresh sweep of the same level happens first.
    """
    lo = d5["low"].to_numpy(); hi = d5["high"].to_numpy()
    c = d5["close"].to_numpy()
    lvl = d5[level_col].to_numpy()
    mr_sh = d5["mr_sh"].to_numpy(); mr_sl = d5["mr_sl"].to_numpy()
    n = len(d5)
    sweeps, sigs = [], []
    pend = -1
    for t in range(n):
        L = lvl[t]
        if pend >= 0 and t - pend > PENDING_BARS_5M:
            pend = -1
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
    1-minute swing the other way, inside the same 2-hour pending window.

    Returns (1-minute entry index, sweep 5-minute index) pairs.
    """
    c1 = d1["close"].to_numpy()
    sh1 = d1["mr_sh"].to_numpy(); sl1 = d1["mr_sl"].to_numpy()
    i1n = d5["i1_next"].to_numpy()
    n1 = len(d1)
    ent, sw = [], []
    for s in sweeps:
        a = i1n[s]
        b = min(n1 - 1, a + PENDING_BARS_5M * 5)
        if a >= n1:
            continue
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
def simulate(bars, sig_idx, direction, stop_px, r_target, max_hold_bars,
             cost=COST_RT):
    """Every candidate is scored INDEPENDENTLY - no shared position slot, so
    any filtered set is a strict subset of the same population (round 400's
    lesson). Fill is the OPEN of the bar after the signal. If one bar
    touches both stop and target, the STOP is taken first.
    """
    o = bars["open"].to_numpy(); h = bars["high"].to_numpy()
    l = bars["low"].to_numpy(); c = bars["close"].to_numpy()
    ts = bars["t"].to_numpy()
    n = len(bars)
    recs = []
    for k, i in enumerate(sig_idx):
        j = i + 1
        if j >= n:
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
        end = min(n - 1, j + max_hold_bars - 1)
        hs, ls = h[j:end + 1], l[j:end + 1]
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
            exit_px, reason, held = c[end], "time", end - j + 1
        gross = direction * (exit_px - entry) / entry * 100.0
        sd = risk / entry * 100.0
        recs.append((i, ts[i], sd, gross, gross - cost, gross - COST_RT_LOW,
                     (gross - cost) / sd if sd > 0 else np.nan, reason, held))
    return pd.DataFrame(recs, columns=[
        "sig_i", "sig_t", "stop_pct", "gross_pct", "net_pct", "net_low_pct",
        "net_R", "reason", "bars_held"])


def slice_by_time(res, t_tr, t_va):
    tr = res[res.sig_t < t_tr]
    va = res[(res.sig_t >= t_tr) & (res.sig_t < t_va)]
    te = res[res.sig_t >= t_va]
    return tr, va, te


def summarise(name, tr, va):
    if len(tr) < MIN_TR or len(va) < MIN_VA:
        return dict(name=name, n_tr=len(tr), n_va=len(va),
                    verdict="thin", mean_tr=np.nan, mean_va=np.nan,
                    gross_tr=np.nan, stop_tr=np.nan, lev=np.nan, R_tr=np.nan,
                    win_tr=np.nan)
    m_tr, m_va = tr["net_pct"].mean(), va["net_pct"].mean()
    stop = tr["stop_pct"].mean()
    return dict(name=name, n_tr=len(tr), n_va=len(va),
                mean_tr=m_tr, mean_va=m_va,
                gross_tr=tr["gross_pct"].mean(),
                gross_va=va["gross_pct"].mean(),
                R_tr=tr["net_R"].mean(),
                win_tr=(tr["net_pct"] > 0).mean() * 100,
                stop_tr=stop, lev=1.0 / stop if stop > 0 else np.nan,
                verdict="qualifies" if (m_tr > 0 and m_va > 0) else "reject")


def show(rows, title, cols=None):
    print("\n" + "-" * 108)
    print(title)
    print("-" * 108)
    print(f"{'cell':<46}{'n_tr':>6}{'n_va':>6}{'grossTR':>9}{'netTR':>9}"
          f"{'netVA':>9}{'R_tr':>7}{'win%':>7}{'stop%':>8}{'lev@1%':>8}  verdict")
    for r in rows:
        if r["verdict"] == "thin":
            print(f"{r['name']:<46}{r['n_tr']:>6}{r['n_va']:>6}"
                  f"{'':>9}{'':>9}{'':>9}{'':>7}{'':>7}{'':>8}{'':>8}  too few trades")
            continue
        print(f"{r['name']:<46}{r['n_tr']:>6}{r['n_va']:>6}"
              f"{r['gross_tr']:>9.4f}{r['mean_tr']:>9.4f}{r['mean_va']:>9.4f}"
              f"{r['R_tr']:>7.2f}{r['win_tr']:>7.1f}{r['stop_tr']:>8.3f}"
              f"{r['lev']:>7.1f}x  {r['verdict']}")


# ----------------------------------------------------------------- round
LEVELS = [("pdl", +1, "prev day low"), ("pdh", -1, "prev day high"),
          ("sesl", +1, "last session low"), ("sesh", -1, "last session high"),
          ("h1l", +1, "1h swing low"), ("h1h", -1, "1h swing high"),
          ("h4l", +1, "4h swing low"), ("h4h", -1, "4h swing high")]
TARGETS = [(None, "hold 24h"), (1.0, "target 1R"), (2.0, "target 2R"),
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
        # ARM A - round 370's construction: 5-minute confirmation IS the
        # trigger. Stop = the extreme traded between sweep and signal.
        stopA = np.array([lo5[a:b + 1].min() if dirn > 0 else hi5[a:b + 1].max()
                          for a, b in zip(sw, sig5)])
        # ARM B - HIS construction: 1-minute body close is the trigger.
        ent1, swB = trigger_1m(d5, d1, sw, dirn)
        if len(ent1):
            a1 = i1n[swB]
            stopB = np.array([lo1[max(0, a):b + 1].min() if dirn > 0
                              else hi1[max(0, a):b + 1].max()
                              for a, b in zip(a1, ent1)])
        for rt, rlab in TARGETS:
            resA = simulate(d5, sig5, dirn, stopA, rt, MAX_HOLD_MIN // 5)
            trA, vaA, teA = slice_by_time(resA, t_tr, t_va)
            nm = f"{lab} -> 5m BOS, {rlab}"
            rows.append(summarise(nm, trA, vaA))
            store.setdefault((nm, "A"), []).append((sym, resA))
            if len(ent1):
                resB = simulate(d1, ent1, dirn, stopB, rt, MAX_HOLD_MIN)
                trB, vaB, teB = slice_by_time(resB, t_tr, t_va)
                nmB = f"{lab} -> 1m BOS, {rlab}"
                rows.append(summarise(nmB, trB, vaB))
                store.setdefault((nmB, "B"), []).append((sym, resB))
    return d5, d1, rows


def control(d5, d1, t_tr, t_va, every=60):
    """CHANCE CONTROL. The same machinery entered at a random eligible
    moment: every 60th 5-minute bar, stop at the most recent confirmed
    swing, both directions, both hold styles."""
    out = []
    for dirn, lab in ((+1, "long"), (-1, "short")):
        idx = np.arange(0, len(d5) - 1, every)
        stop = (d5["mr_sl"].to_numpy() if dirn > 0 else d5["mr_sh"].to_numpy())[idx]
        for rt, rlab in ((None, "hold 24h"), (2.0, "target 2R")):
            res = simulate(d5, idx, dirn, stop, rt, MAX_HOLD_MIN // 5)
            tr, va, te = slice_by_time(res, t_tr, t_va)
            out.append(summarise(f"CONTROL random entry {lab}, {rlab}", tr, va))
    return out


def main():
    # the shared clock: use BTC's overlap to fix the slice boundaries, then
    # apply the SAME timestamps to every asset so the slices mean the same
    # calendar dates everywhere.
    b5 = load("BTCUSD", "5m"); b1 = load("BTCUSD", "1m")
    t0 = max(b5["t"].iloc[0], b1["t"].iloc[0])
    t1 = min(b5["t"].iloc[-1], b1["t"].iloc[-1])
    span = t1 - t0
    t_tr = t0 + span * 0.60
    t_va = t0 + span * 0.80
    print("=" * 108)
    print("ROUND 450 - TJR SWEEP -> BREAK OF STRUCTURE ON CRYPTO, 1-MINUTE TRIGGER")
    print("=" * 108)
    print(f"shared window {t0:%Y-%m-%d} to {t1:%Y-%m-%d} UTC  ({span.days} days)")
    print(f"choosing slice  -> {t_tr:%Y-%m-%d %H:%M}")
    print(f"middle slice    -> {t_va:%Y-%m-%d %H:%M}   read once")
    print(f"final slice     -> {t1:%Y-%m-%d}   NEVER OPENED unless a cell qualifies")
    print(f"cost charged: {COST_RT}% of notional round trip (Alpaca crypto taker "
          f"x2); {COST_RT_LOW}% also carried. Gross reported beside every net.")
    print(f"pending sweep expires after {PENDING_BARS_5M} 5-minute bars; hold cap "
          f"{MAX_HOLD_MIN//60}h. Both OURS, fixed before the run, never swept.")

    store = {}
    per_asset = {}
    for sym in PRIMARY:
        d5, d1, rows = run_asset(sym, t_tr, t_va, store)
        per_asset[sym] = rows
        show(rows, f"{sym}   5m bars {len(d5):,}   1m bars {len(d1):,}")
        if sym == "BTCUSD":
            show(control(d5, d1, t_tr, t_va),
                 "CHANCE CONTROL on BTCUSD - what a random entry with the same "
                 "stop machinery produced")

    # ---------------------------------------------------- pooled read
    print("\n" + "=" * 108)
    print("POOLED ACROSS BTC + ETH + SOL  (a cell must work on the market, not "
          "on one coin)")
    print("=" * 108)
    pooled = []
    for (nm, arm), parts in store.items():
        allr = pd.concat([r for _, r in parts])
        tr, va, te = slice_by_time(allr, t_tr, t_va)
        s = summarise(nm, tr, va)
        if s["verdict"] == "thin":
            continue
        indiv = []
        for sym, r in parts:
            t_, v_, _ = slice_by_time(r, t_tr, t_va)
            indiv.append(t_["net_pct"].mean() if len(t_) >= 10 else np.nan)
        s["n_assets_pos"] = int(np.nansum(np.array(indiv) > 0))
        s["arm"] = arm
        pooled.append(s)
    pooled.sort(key=lambda r: -(r["mean_tr"] if np.isfinite(r["mean_tr"]) else -9))
    show(pooled, "pooled cells, best choosing-slice net first")
    df = pd.DataFrame(pooled)
    df.to_csv(f"{REPO}/step450_table.csv", index=False)

    n_cells = len(pooled)
    q = df[(df.verdict == "qualifies") & (df.n_assets_pos >= 2)]
    print(f"\n{n_cells} pooled cells scored. {len(q)} are positive on BOTH the "
          f"choosing and middle slice AND positive on at least 2 of 3 assets.")
    print(f"EXPECTED BY CHANCE if there were no edge at all: a symmetric "
          f"zero-mean cell passes both slices about 1 time in 4, so roughly "
          f"{n_cells/4:.0f} of {n_cells} would pass on luck alone.")
    if len(q):
        print(q[["name", "arm", "n_tr", "n_va", "gross_tr", "mean_tr",
                 "mean_va", "n_assets_pos", "stop_tr", "lev"]].to_string(index=False))

    # ------------------------------------------------- arm A versus arm B
    print("\n" + "=" * 108)
    print("THE ROUND-370 QUESTION: DOES THE 1-MINUTE TRIGGER CHANGE THE ANSWER?")
    print("=" * 108)
    a = df[df.arm == "A"]; b = df[df.arm == "B"]
    for lab, sub in (("5-minute trigger (round 370's construction)", a),
                     ("1-MINUTE trigger (his construction)", b)):
        if not len(sub):
            continue
        print(f"{lab:<48} cells {len(sub):>3}   median net choosing "
              f"{sub.mean_tr.median():>8.4f}%   median gross "
              f"{sub.gross_tr.median():>8.4f}%   median stop "
              f"{sub.stop_tr.median():.3f}%  -> {1/sub.stop_tr.median():.1f}x "
              f"at 1% risked   positive-gross cells {int((sub.gross_tr>0).sum())}/{len(sub)}")

    return df, t_tr, t_va, store


if __name__ == "__main__":
    main()
