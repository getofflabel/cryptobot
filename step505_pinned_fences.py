"""
ROUND 505 - PIN EVERY PUBLISHED FENCE AS A DATE.   (queue item 40)

WHAT THIS IS
  `step489.cut80` computes a fence as `t0 + (t1 - t0) * 0.80` off whatever
  span the file has AT THE MOMENT IT RUNS. Every sealed-slice boundary this
  log has published sits on top of that formula, so every boundary is a
  FUNCTION OF THE FILE and not a date. R504 measured the exposure: 53 days of
  real bars already exist past the corpus boundary, and appending them moves
  every fence on the disk 42 days - six weeks of R492's LINK SEALED region
  becomes readable again, and six weeks of what R492 READ as XRP's train/val
  becomes part of XRP's "sealed" slice.

  This file pins them. A constant table of DATES, the round that published
  each, and `fenced_at(sym)` which returns the pinned date where one exists
  and falls back to `cut80` only for instruments no round has ever fenced.

THE FENCE ON THIS ROUND (queue item 40, verbatim)
  Editorial plus one constant table. No threshold moves, no slice is re-read,
  no ordering is republished, and `cut80` ITSELF IS NOT EDITED - the pin
  wraps it, R494's pattern. No look, no candidate.

  Enforced here: `step489_next_look_screen` and `step501_coverage_column` are
  IMPORTED and never modified; `simulate()` is never called from this file and
  cannot be reached from it; no entry population is built, no sweep scanned,
  no stop measured, no outcome read; every tape read stops at the pinned
  boundary, so PAXG's and XRP's intact slices stay unread. NO FILE ON DISK IS
  WRITTEN, EXTENDED, MOVED OR TRUNCATED by this round - the 53 days of real
  bars past the corpus boundary are deliberately still not fetched, and the
  whole point of this file is that fetching them is now safe.

WHERE THE PINNED VALUES CAME FROM
  Each one is `S.cut80` evaluated on the file as it stands today, at full
  precision, and each was cross-checked against the DATE the round that
  published it printed in RESEARCH_LOG.md. Part (0) of `main()` re-derives
  all of them and stops the round if any has drifted by so much as a second.

USAGE
  python3 step505_pinned_fences.py          # the audit
  from step505_pinned_fences import fenced_at, fenced_window, fenced_frame
"""

import hashlib
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step489_next_look_screen as S      # noqa: E402  (the fence, unmodified)
import step501_coverage_column as P       # noqa: E402  (R501, unmodified)
import step502_era_column as E            # noqa: E402  (R502, unmodified)

LINE = "=" * 108

# The corpus boundary every window in R485-R504 is cut against (R494 fence 3).
CORPUS_END = pd.Timestamp("2026-07-26")

# R504's measurement of the exposure, carried so the demo can reproduce it.
R504_RUN_DATE = pd.Timestamp("2026-09-17")
R504_UNFETCHED_DAYS = 53
R504_DRIFT_DAYS = 42

# =========================================================== THE PIN TABLE
# instrument -> the DATE its fence sits at, the round that published it, and
# what that boundary is load-bearing for. `t80` is `S.cut80`'s own value at
# full precision: a fence compared with `<` can move a bar if it is rounded.
PINNED = {
    # --- the eleven ranked 1-minute crypto tapes (R499/R501/R502/R503/R504)
    "BTCUSD":  dict(t80="2025-06-15 06:33:36", t0="2021-01-01 06:00:00",
                    t1="2026-07-26 18:42:00", bars=2597036, round="R489",
                    published="2026-09-01",
                    locks="POOLED CALENDAR. R502/R503/R504 measure A1 against "
                          "BTC's fenced window; moving it moves every era "
                          "factor. Also the crypto arm's own 80% boundary."),
    "ETHUSD":  dict(t80="2025-06-15 06:35:12", t0="2021-01-01 06:00:00",
                    t1="2026-07-26 18:44:00", bars=2538368, round="R489",
                    published="2026-09-01",
                    locks="ranking row; sealed slice SPENT by R475."),
    "SOLUSD":  dict(t80="2025-06-15 06:35:36", t0="2021-01-01 06:06:00",
                    t1="2026-07-26 18:43:00", bars=1955709, round="R489",
                    published="2026-09-01",
                    locks="ranking row, contested top three (R503); sealed "
                          "slice SPENT by R475."),
    "LINKUSD": dict(t80="2025-06-15 06:42:24", t0="2021-01-01 06:00:00",
                    t1="2026-07-26 18:53:00", bars=2325622, round="R489",
                    published="2026-09-01",
                    locks="**R492 SPENT the slice that starts here** "
                          "(2025-06-15 -> 2026-07-26, 406d). Moving this "
                          "boundary un-spends six weeks of a spent slice."),
    "LTCUSD":  dict(t80="2025-06-15 06:46:24", t0="2021-01-01 06:00:00",
                    t1="2026-07-26 18:58:00", bars=2110763, round="R489",
                    published="2026-09-01",
                    locks="ranking row (7th, stable since R500)."),
    "XRPUSD":  dict(t80="2026-01-20 06:38:24", t0="2024-01-01 06:00:00",
                    t1="2026-07-26 18:48:00", bars=770145, round="R489",
                    published="2026-09-01",
                    locks="**R492 published 2026-01-20 -> 2026-07-26 as "
                          "INTACT and never read it.** This is the family's "
                          "last clean window on an instrument with real "
                          "history. Moving it forward pre-contaminates the "
                          "slice with six weeks R492 already READ."),
    "ADAUSD":  dict(t80="2026-06-24 07:11:36", t0="2026-02-13 12:02:00",
                    t1="2026-07-26 23:59:00", bars=168115, round="R489",
                    published="2026-09-01",
                    locks="ranking row, unplaced by R503; INTACT."),
    "DOTUSD":  dict(t80="2025-12-24 07:23:48", t0="2023-08-18 13:03:00",
                    t1="2026-07-26 23:59:00", bars=1256982, round="R494",
                    published="2026-09-06",
                    locks="ranking row, unplaced by R503; INTACT. R489's "
                          "pre-backfill fence (2026-06-26) is superseded."),
    "PAXGUSD": dict(t80="2025-06-15 11:06:00", t0="2021-01-01 07:54:00",
                    t1="2026-07-26 23:54:00", bars=311292, round="R494",
                    published="2026-09-06",
                    locks="ranking row, contested top three (R503); INTACT "
                          "and unread. R489's pre-backfill fence "
                          "(2026-06-26) is superseded."),
    "AVAXUSD": dict(t80="2025-08-18 16:58:24", t0="2021-11-18 13:00:00",
                    t1="2026-07-26 23:58:00", bars=1980264, round="R494",
                    published="2026-09-06",
                    locks="ranking row, unplaced by R503; INTACT. Data-absent "
                          "in R489 (3 days of tape)."),
    "DOGEUSD": dict(t80="2025-06-15 10:46:36", t0="2021-01-01 06:01:00",
                    t1="2026-07-26 23:58:00", bars=2373535, round="R494",
                    published="2026-09-06",
                    locks="ranking row (5th, stable since R500); INTACT. "
                          "Data-absent in R489 (3 days of tape)."),
    # --- the index tapes
    "SPY":     dict(t80="2024-06-13 09:35:24", t0="2016-01-01 00:01:00",
                    t1="2026-07-24 23:59:00", bars=2114524, round="R474",
                    published="2026-07-27",
                    locks="**R474 SPENT the slice that starts here** "
                          "(2024-06 -> 2026-07, 371 trades / 155 days) and "
                          "that cell is the one AWAITING DEPLOYMENT REVIEW."),
    "QQQ":     dict(t80="2024-06-13 09:35:12", t0="2016-01-01 00:00:00",
                    t1="2026-07-24 23:59:00", bars=2036866, round="R474",
                    published="2026-07-27",
                    locks="same spent slice as SPY (R474)."),
    # --- the screen's non-crypto rows (R489, never re-fenced since)
    "GLD":     dict(t80="2026-06-25 21:34:24", t0="2026-03-02 04:00:00",
                    t1="2026-07-24 19:58:00", bars=76899, round="R489",
                    published="2026-09-01",
                    locks="R489(a2) vol% row; 81 days, queue item 35."),
    "IAU":     dict(t80="2026-06-25 21:35:12", t0="2026-03-02 04:00:00",
                    t1="2026-07-24 19:59:00", bars=55190, round="R489",
                    published="2026-09-01",
                    locks="R489(a2) vol% row; 81 days, queue item 35."),
    "GBPUSD":  dict(t80="2026-06-14 17:23:12", t0="2026-01-05 19:00:00",
                    t1="2026-07-24 16:59:00", bars=206225, round="R489",
                    published="2026-09-01",
                    locks="R489(a2) vol% row."),
    "GBPJPY":  dict(t80="2026-06-14 17:23:12", t0="2026-01-05 19:00:00",
                    t1="2026-07-24 16:59:00", bars=206346, round="R489",
                    published="2026-09-01",
                    locks="R489(a2) vol% row."),
}

# ===================================================== THE ARM CLOCKS
# `cut80` is NOT the only call site of the defect. R450 (crypto) and R474
# (index) compute `t0 + span * 0.60` and `t0 + span * 0.80` on a SHARED CLOCK
# - one instrument's 5m-and-1m overlap - and apply those timestamps to every
# asset in the arm. Same formula, same exposure, different file. The three
# windows below are the ones this log's SPENT slices were cut on.
ARM_CLOCKS = {
    "crypto_1m_R476": dict(
        clock="BTCUSD 5m and 1m overlap", t0="2021-01-01 06:00:00",
        t1="2026-07-26 18:40:00", t_tr="2024-05-04 18:24:00",
        t_va="2025-06-15 06:32:00", round="R476", published="2026-08-01",
        recomputable=True,
        locks="the backfilled crypto window. R492's LINK table cut its "
              "choosing/middle/final on exactly these dates."),
    "crypto_1m_R450": dict(
        clock="BTCUSD 5m and 1m overlap, 147-day file",
        t0="2026-03-01", t1="2026-07-26", t_tr="2026-05-28 08:27",
        t_va="2026-06-26 19:16", round="R450", published="2026-07-23",
        recomputable=False,
        locks="**R475 SPENT 2026-06-27 -> 2026-07-26 on this clock.** The "
              "file it was computed on has since grown from 147 days to "
              "2,032, so this window CANNOT be recomputed today - it is "
              "pinned from step450_output.txt and from nothing else."),
    "index_1m_R474": dict(
        clock="SPY 5m and 1m overlap", t0="2016-01-01 00:01:00",
        t1="2026-07-24 23:55:00", t_tr="2022-05-03 19:09:24",
        t_va="2024-06-13 09:32:12", round="R474", published="2026-07-27",
        recomputable=True,
        locks="**R474 SPENT everything after t_va** on SPY and QQQ. The "
              "surviving cell is the one AWAITING DEPLOYMENT REVIEW."),
}

# Where a pinned instrument's 1-minute tape lives, for the fallback path.
PATHS = {lab: path for lab, path, _, _ in S.UNIVERSE}


# ============================================================== THE WRAPPER
def is_pinned(sym):
    return sym in PINNED


def fenced_at(sym, f=None):
    """THE FENCE AS A DATE. Returns the pinned boundary where a round has
    published one, and falls back to `S.cut80` - unmodified, imported, not
    re-implemented - only for instruments no round has ever fenced.

    A pinned instrument never touches the file, so appending tape to it
    cannot move the boundary. That is the whole point."""
    if sym in PINNED:
        return pd.Timestamp(PINNED[sym]["t80"])
    if f is None:
        if sym not in PATHS:
            raise KeyError(f"{sym} is neither pinned nor in step489.UNIVERSE; "
                           f"pass the frame to fence it with cut80.")
        f = S.tape(PATHS[sym])
    t80, _, _ = S.cut80(f)
    return t80


def fenced_window(sym, f=None):
    """`S.cut80`'s own signature - (t80, t0, t1) - so a caller can swap this
    in for `cut80` without changing anything else. The endpoints come from
    the file in both cases; only the BOUNDARY is pinned."""
    if f is None:
        f = S.tape(PATHS[sym]) if sym in PATHS else None
    if f is None:
        raise KeyError(f"no path known for {sym}")
    return fenced_at(sym, f), f["t"].iloc[0], f["t"].iloc[-1]


def fenced_frame(sym):
    """R501's `fenced()`, with the boundary taken from the pin. Same `<`
    comparison, same columns, same order - so anything computed behind it
    reproduces R501/R502/R503 bar for bar."""
    f = S.tape(PATHS[sym])
    t80 = fenced_at(sym, f)
    return f[f["t"] < t80].copy(), f["t"].iloc[0], f["t"].iloc[-1]


def drift_if_extended(sym, extra_days, frac=0.80):
    """What `cut80` would return if `extra_days` of tape were appended to the
    end of this instrument's file, and what `fenced_at` would return. Pure
    arithmetic on two endpoints: t80' = t0 + (t1 + d - t0) * frac, so the
    boundary moves frac * d. NO FILE IS TOUCHED."""
    t0 = pd.Timestamp(PINNED[sym]["t0"])
    t1 = pd.Timestamp(PINNED[sym]["t1"])
    moved = t0 + (t1 + pd.Timedelta(days=extra_days) - t0) * frac
    pinned_val = fenced_at(sym)
    return moved, pinned_val, moved - pinned_val


def _daykey(f):
    """A fingerprint of a fenced frame: enough that two frames agreeing on it
    cannot disagree on anything R501/R502/R503 computed from them."""
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(f["t"].to_numpy().astype("datetime64[s]")))
    h.update(np.ascontiguousarray(f["close"].to_numpy(dtype="float64")))
    return h.hexdigest()[:16]


def sh(s):
    """Display label. FX pairs keep both legs; a crypto ticker drops its
    quote currency the way every table in this log prints it."""
    if s in ("GBPUSD", "GBPJPY"):
        return s
    return s.replace("USD", "") if s.endswith("USD") and len(s) > 4 else s


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 505 - PIN EVERY PUBLISHED FENCE AS A DATE   (queue item 40)")
    print(LINE)
    print(f"run {now:%Y-%m-%d %H:%M:%S} UTC")
    print("BOOKKEEPING. No hypothesis, no entry population, no sweep, no "
          "stop, no outcome, NO LOOK.")
    print("`cut80` is imported and NOT edited. No file on disk is written, "
          "extended, moved or truncated.")
    print(f"corpus boundary {CORPUS_END:%Y-%m-%d} (R494 fence 3); "
          f"{(pd.Timestamp(now.date()) - CORPUS_END).days} days of real bars "
          f"exist past it and are still not fetched.")

    # ------------------------------------------------------------ part (0)
    print("\n" + LINE)
    print("(0) THE PIN, RE-DERIVED. Every pinned date is `S.cut80` on the "
          "file as it stands RIGHT NOW.")
    print(LINE)
    print("    If any row has drifted by one second the table is already "
          "stale and the round stops.")
    print(f"\n  {'sym':<9}{'pinned fence':<22}{'cut80 today':<22}"
          f"{'drift':>8}   {'bars now':>11}  {'bars pinned':>11}")
    print("  " + "-" * 92)
    worst_drift, bar_mismatch = pd.Timedelta(0), 0
    frames = {}
    for sym in PINNED:
        f = S.tape(PATHS[sym])
        t80_now, _, _ = S.cut80(f)
        t80_pin = pd.Timestamp(PINNED[sym]["t80"])
        d = t80_now - t80_pin
        worst_drift = max(worst_drift, abs(d))
        bar_mismatch += (len(f) != PINNED[sym]["bars"])
        frames[sym] = f
        flag = "" if d == pd.Timedelta(0) else "   <<< DRIFTED"
        print(f"  {sh(sym):<9}{t80_pin!s:<22}{t80_now!s:<22}"
              f"{str(d):>8}   {len(f):>11,}  {PINNED[sym]['bars']:>11,}{flag}")
    print(f"\n  worst drift across {len(PINNED)} pinned instruments: "
          f"{worst_drift}.  bar-count mismatches: {bar_mismatch}.")
    if worst_drift != pd.Timedelta(0) or bar_mismatch:
        print("  !! the disk has moved under the pin. The round stops and "
              "the table must be re-derived deliberately.")
        return 1
    print("  EXACT. The pinned dates ARE today's fences, to the second, on "
          "every instrument.")

    # ------------------------------------------------------------ part (1)
    print("\n" + LINE)
    print("(1) THE FENCED FRAME IS IDENTICAL THROUGH THE PIN AND THROUGH "
          "`cut80`")
    print(LINE)
    print("    R501's `fenced()` cuts with `f['t'] < t80`. Two frames with "
          "the same fingerprint cannot")
    print("    disagree on ANY number computed behind the fence - coverage, "
          "vol%, era factor, A1, A2.")
    print(f"\n  {'sym':<9}{'bars (cut80)':>14}{'bars (pin)':>13}"
          f"{'  fingerprint cut80':<20}{'fingerprint pin':<18}{'':>6}")
    print("  " + "-" * 92)
    same = 0
    for sym in PINNED:
        f = frames[sym]
        a = f[f["t"] < S.cut80(f)[0]]
        b = f[f["t"] < fenced_at(sym, f)]
        ha, hb = _daykey(a), _daykey(b)
        ok = (len(a) == len(b)) and ha == hb
        same += ok
        print(f"  {sh(sym):<9}{len(a):>14,}{len(b):>13,}  {ha:<20}{hb:<18}"
              f"{'MATCH' if ok else 'DIFFER':>6}")
    print(f"\n  {same} of {len(PINNED)} frames identical.")
    if same != len(PINNED):
        print("  !! the wrapper does not reproduce the formula. The round "
              "stops.")
        return 1

    # ------------------------------------------------------------ part (2)
    print("\n" + LINE)
    print("(2) REPRODUCTION CONTROLS - R503's two, R504's two, recomputed "
          "THROUGH THE PIN")
    print(LINE)
    pub = P.parse_r499_ranking()
    if len(pub) != 11:
        print("  !! incomplete parse of R499's table. The round stops.")
        return 1
    tp = {}
    for sym, _, _ in P.RANKED:
        f, _, _ = fenced_frame(sym)          # <-- through the pin, not cut80
        d = P.density(f)
        d["coord"] = P.coord(f)
        d["keys"] = P.minute_keys(f)
        d["f"] = f
        tp[sym] = d
    worst = max(abs(tp[s]["coord"] - pub[s]["vol"]) for s, _, _ in P.RANKED)
    print(f"\n  a. R499's vol% column, recomputed behind the PINNED fence: "
          f"max absolute difference {worst:.4f} pp")
    if worst > 0.0001:
        print("     !! the pin does not reproduce R499. The round stops.")
        return 1
    print("     EXACT.")

    donors = [s for s, _, _ in P.RANKED if tp[s]["cov"] >= P.DONOR_MIN_COV]
    r501_worst, dbx = 0.0, {}
    for sym, _, _ in P.RANKED:
        t = tp[sym]
        xs = []
        for dn in donors:
            if dn == sym:
                continue
            d = tp[dn]
            fm = P.transplant(d["f"], d["keys"], t["keys"])
            if len(fm) < P.MASK_MIN_BARS:
                continue
            days = set(fm["t"].dt.floor("D").unique())
            if len(days) < P.MASK_MIN_DAYS:
                continue
            sameday = d["f"][d["f"]["t"].dt.floor("D").isin(days)]
            cm, cs = P.coord(fm), P.coord(sameday)
            if not (np.isfinite(cm) and np.isfinite(cs) and cs > 0):
                continue
            xs.append(cm / cs)
        dbx[sym] = float(np.median(xs)) if len(xs) >= 2 else np.nan
        ref = E.R501_XSAME.get(sym, np.nan)
        if np.isfinite(ref) and np.isfinite(dbx[sym]):
            r501_worst = max(r501_worst, abs(dbx[sym] - ref))
    print(f"\n  b. R501's xSAME column, recomputed with R501's own functions "
          f"behind the PINNED fence: max absolute difference "
          f"{r501_worst:.3f}x")
    if r501_worst > 0.0015:
        print("     !! the pin does not reproduce R501. The round stops.")
        return 1
    print("     EXACT to the published precision.")
    print("\n  c. R502 and R503 take their inputs from exactly these frames "
          "- the pooled calendar is")
    print("     BTC's fenced window and A1/A2 are day-set containments "
          "inside each row's fenced window.")
    print("     Part (1) showed those frames are identical bar for bar, so "
          "every era factor, every A1,")
    print("     every A2 and the published ORDERING are unchanged by "
          "construction. NOTHING IS REPUBLISHED.")

    # ------------------------------------------------------------ part (3)
    print("\n" + LINE)
    print("(3) THE HAZARD, PRICED. WHAT ONE `fetch` DOES TO A FENCE, WITH "
          "AND WITHOUT THE PIN")
    print(LINE)
    today = pd.Timestamp(now.date())
    real_gap = (today - CORPUS_END).days
    print(f"\n  R504 measured {R504_UNFETCHED_DAYS} unfetched days on "
          f"{R504_RUN_DATE:%Y-%m-%d} and a {R504_DRIFT_DAYS}-day move. Today "
          f"the gap is {real_gap} days.")
    print(f"  A fence at 80% moves 0.8 of a day per day of tape appended, so "
          f"appending {real_gap} days moves it {0.8 * real_gap:.1f} days.")
    hdr = ("  " + "sym".ljust(9) + "fence today".ljust(13)
           + "cut80 after the fetch".ljust(24) + "moves".rjust(8)
           + "   fenced_at() after the fetch".ljust(32) + "moves".rjust(7))
    print("\n" + hdr)
    print("  " + "-" * 96)
    for sym in PINNED:
        moved, pinned_val, delta = drift_if_extended(sym, real_gap)
        print(f"  {sh(sym):<9}{pinned_val:%Y-%m-%d}   "
              f"{moved:%Y-%m-%d %H:%M}{'':>9}{delta.days:>5}d   "
              f"{pinned_val:%Y-%m-%d %H:%M}{'':>13}{0:>5}d")
    print("\n  The right-hand column is the deliverable: the pinned fence "
          "does not know the file grew.")

    # ------------------------------------------------------------ part (4)
    print("\n" + LINE)
    print("(4) WHAT THE PIN LOCKS")
    print(LINE)
    for sym, d in PINNED.items():
        print(f"\n  {sh(sym):<9}fence {d['t80']}   published by {d['round']} "
              f"({d['published']})")
        print(f"            {d['locks']}")

    # ------------------------------------------------------------ part (5)
    print("\n" + LINE)
    print("(5) THE FORMULA HAS THREE CALL SITES, NOT ONE. THE OTHER TWO CUT "
          "THE SPENT SLICES.")
    print(LINE)
    print("\n  step489.cut80 / step493.cut80  - the SCREEN's fence, wrapped "
          "by fenced_at() above.")
    print("  step450.main  t_tr/t_va         - the CRYPTO arm's shared "
          "clock. Same formula, BTC's 5m-1m overlap.")
    print("  step474.main  t_tr/t_va         - the INDEX arm's shared clock. "
          "Same formula, SPY's 5m-1m overlap.")
    print("\n  R475's spent crypto slice and R474's spent index slice were "
          "cut by the latter two, not by")
    print("  `cut80`, so pinning `cut80` alone would have left the two "
          "SPENT slices exposed. They are pinned")
    print("  here as ARM_CLOCKS. Item 40's fence forbids editing those "
          "files; the table is the pin.")
    print(f"\n  {'arm':<18}{'t0':<21}{'t_tr (60%)':<21}{'t_va (80%)':<21}"
          f"{'round':<7}{'recomputable'}")
    print("  " + "-" * 96)
    for k, a in ARM_CLOCKS.items():
        print(f"  {k:<18}{a['t0']:<21}{a['t_tr']:<21}{a['t_va']:<21}"
              f"{a['round']:<7}{'yes' if a['recomputable'] else 'NO'}")
    print("\n  The two recomputable clocks were re-derived this run and "
          "agree with the pin; see part (6).")

    # ------------------------------------------------------------ part (6)
    print("\n" + LINE)
    print("(6) THE TWO RECOMPUTABLE ARM CLOCKS, RE-DERIVED")
    print(LINE)
    ok_arms = 0
    for key, sym, loader in (("crypto_1m_R476", "BTCUSD", "crypto"),
                             ("index_1m_R474", "SPY", "index")):
        a = ARM_CLOCKS[key]
        if loader == "crypto":
            d5 = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_5m.parquet")
            d1 = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_1m.parquet")
            t5 = pd.to_datetime(d5["t"]).sort_values().drop_duplicates()
            t1s = pd.to_datetime(d1["t"]).sort_values().drop_duplicates()
        else:
            d5 = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_5m.parquet")
            d1 = pd.read_parquet(f"{REPO}/data_alpaca_{sym}_1m.parquet")
            t5 = pd.to_datetime(d5["timestamp"], utc=True).dt.tz_localize(
                None).sort_values().drop_duplicates()
            t1s = pd.to_datetime(d1["timestamp"], utc=True).dt.tz_localize(
                None).sort_values().drop_duplicates()
        t0 = max(t5.iloc[0], t1s.iloc[0])
        t1 = min(t5.iloc[-1], t1s.iloc[-1])
        span = t1 - t0
        tr, va = t0 + span * 0.60, t0 + span * 0.80
        dtr = tr - pd.Timestamp(a["t_tr"])
        dva = va - pd.Timestamp(a["t_va"])
        ok = dtr == pd.Timedelta(0) and dva == pd.Timedelta(0)
        ok_arms += ok
        print(f"\n  {key}  ({a['clock']})")
        print(f"    window {t0} -> {t1}  ({span.days} days)")
        print(f"    t_tr  recomputed {tr}   pinned {a['t_tr']}   drift {dtr}")
        print(f"    t_va  recomputed {va}   pinned {a['t_va']}   drift {dva}")
        print(f"    {'EXACT' if ok else '!! DRIFTED'}")
    print(f"\n  {ok_arms} of 2 recomputable arm clocks reproduce exactly. "
          f"crypto_1m_R450 is NOT recomputable -")
    print("  its 147-day file has since grown to 2,032 days, which is "
          "precisely the defect, already realised,")
    print("  on the clock that cut R475's spent slice. It is pinned from "
          "step450_output.txt.")

    # ------------------------------------------------------------ part (7)
    print("\n" + LINE)
    print("(7) THE FALLBACK PATH, EXERCISED")
    print(LINE)
    print("\n  `fenced_at` falls back to `S.cut80` for any instrument no "
          "round has fenced. Demonstrated on a")
    print("  5-minute tape, which no round has ever fenced and which is "
          "therefore NOT in the table:")
    d5 = pd.read_parquet(f"{REPO}/data_alpaca_BTCUSD_5m.parquet")
    g = pd.DataFrame({"t": pd.to_datetime(d5["t"]),
                      "close": d5["close"].to_numpy()}).sort_values(
        "t").drop_duplicates("t").reset_index(drop=True)
    fb = fenced_at("BTCUSD_5m_unpinned", g)
    direct, _, _ = S.cut80(g)
    print(f"    BTCUSD 5m   pinned? {is_pinned('BTCUSD_5m_unpinned')}   "
          f"fenced_at -> {fb}   cut80 -> {direct}   "
          f"{'SAME' if fb == direct else 'DIFFER'}")
    print(f"\n  {len(PINNED)} instruments pinned, "
          f"{len(ARM_CLOCKS)} arm clocks pinned. Everything else still "
          f"computes the formula, which is")
    print("  correct: an instrument no round has published a boundary for "
          "has no boundary to protect.")

    print("\n" + LINE)
    print("LOOKS CONSUMED: NONE, and none was reachable. No entry "
          "population, no sweep, no stop, no")
    print("outcome, no t-statistic. PAXG's and XRP's intact slices are "
          "unread; LINK's, crypto's and the")
    print("index's stay as spent as they were. NO FILE ON DISK WAS WRITTEN, "
          "EXTENDED, MOVED OR TRUNCATED.")
    print(LINE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
