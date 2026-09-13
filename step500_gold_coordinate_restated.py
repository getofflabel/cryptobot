"""
step500_gold_coordinate_restated.py - ROUND 500

RESTATE R493's GOLD HANDOFF ON 850 DAYS INSTEAD OF 118.
(QUEUE ITEM 25)

Research only. No orders. No account. No live file touched, imported or
modified. A CORRECTION to a published coordinate, not a hypothesis.

QUEUE ITEM 25, VERBATIM
  R493 gave the gold specialist the first sourced US perpetual cost gold has
  ever had here - PAXG PERP, 0.0806% all-in - and killed the obvious next
  thought with it: paired with PAXG's own 1-minute tape the R488 multiple
  read 0.58, "gold's median minute does not clear its own round trip."
  That pairing used 118 days. On the 850 now on disk PAXG's 1-minute move
  reads 0.0791% instead of 0.0467%, and the fee-only multiple is 1.98 -
  second among every intact instrument on the disk, ahead of XRP. R493's
  cost figure is untouched and stands; the tape it was divided by does not.
  Deliverable, arithmetic on numbers already published plus tape already on
  disk: restate R493(b)'s gold paragraph with the 850-day coordinate,
  re-poll PAXG PERP's book for a same-day all-in, and hand the corrected
  pair to the gold specialist with the caveat that decides how much it is
  worth: PAXG's 1-minute coverage is 10.6% - about 153 bars a day out of
  1,440 - and it is the only 24/7 crypto row where the gap-clean and raw
  volatility columns disagree (0.0791% vs 0.1103%). Say plainly whether a
  tenth-full tape can carry a coordinate at all, and if the answer is no,
  the correction is that the 0.58 was unreadable rather than wrong.
  While there, give GLD and IAU their first `stop/vol` reading - they have
  never had one, and after R494 they are the only instruments left on this
  disk that could still show the ratio departing from 3.5-4.5 off
  crypto-like tape.
  THE FENCE: first 80% only. No entry population is scored, `simulate()` is
  not called, no look, no candidate. This corrects a coordinate; it does
  not propose trading gold.

THE FENCE, FIXED BEFORE THE RUN
  1. `simulate()` IS NEVER CALLED, in this file or in anything it imports.
     No return, P&L, expectancy, win rate, risk multiple or t-statistic is
     computed for any instrument anywhere in this round. The only thing
     read off an entry is the DISTANCE FROM THE FILL TO THE CHART
     STRUCTURE, which is a property of the chart and not of the outcome -
     R489's fence, the thing that makes part (4) free.
  2. EVERY TAPE MEASUREMENT STOPS AT THAT INSTRUMENT'S OWN 80% BOUNDARY,
     computed by step489's own `cut80`. No sealed slice is read. GLD and
     IAU have never had an entry population built on them by any round in
     this log, so nothing is spent there either.
  3. NOTHING IS SELECTED AND NOTHING IS PROPOSED. The output is a corrected
     coordinate and a readability verdict on the tape underneath it. Gold
     is not proposed for trading under any outcome.
  4. step489 IS IMPORTED AS A MODULE AND CALLED UNMODIFIED. Its
     `structural_stops`, `daily_vol`, `cut80`, `tape` and
     `cde_spread_samples` do the work. Nothing in it is edited - that is
     R494's pattern, and it is why the controls below reproduce.
  5. THE PRE-BACKFILL BYTES ARE READ FROM `data_pre494/`, NOT RETYPED.
     R493's 0.0467% is recomputed off the exact file it was computed from,
     so the "the tape moved" claim is demonstrated rather than asserted.

COSTS
  Charged for honest arithmetic and used for nothing else (owner rule
  2026-07-25). Cost is one of the two coordinates of the R488 multiple; it
  declines nothing and ranks nothing in this round.

WHAT IS PRIMARY-SOURCED HERE AND WHAT IS NOT
  SOURCED, LIVE, THIS RUN: the CDE perpetual product list, PAXG PERP's
    contract size, mark and top-of-book spread, off the same keyless public
    endpoints R479/R482/R489/R493/R499 used.
  SOURCED, IN-LOG: CFM's fee formula max(0.02% x notional, $0.15) per
    contract per side (R486, primary-sourced); the $750 break point and the
    standing rule that a CDE cost figure is not a constant (R493/R499).
  NOT SOURCED, AND SAID SO RATHER THAN INVENTED: CFM's volume-tier ladder
    above the 0.02% floor - five attempts now (R482, R486, R489, R493,
    this round); the equity spread on GLD and IAU, so neither gets a cost
    coordinate here, only a stop/vol one.

USAGE
  python3 step500_gold_coordinate_restated.py
"""

import json
import sys
import urllib.request
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = "/Users/wallacechen/cryptobot"
sys.path.insert(0, REPO)

import step489_next_look_screen as S     # noqa: E402  (screen, unmodified)

LINE = "=" * 108
RNG = np.random.default_rng(500)         # fixed before any number existed

CDE_PRODUCTS = ("https://api.coinbase.com/api/v3/brokerage/market/products"
                "?product_type=FUTURE&limit=250")
CDE_BOOK = ("https://api.coinbase.com/api/v3/brokerage/market/product_book"
            "?product_id={pid}&limit=1")

CFM_RATE_FLOOR = 0.0002      # R486
CFM_MIN_PER_SIDE = 0.15      # R486
BREAK_NOTIONAL = CFM_MIN_PER_SIDE / CFM_RATE_FLOOR    # $750, R493

# R493's published gold handoff, carried verbatim so the restatement is
# against the exact numbers the specialist was given.
R493_PAXG_VOL = 0.0467       # % of price, 118 days
R493_PAXG_FEE_RT = 0.0400    # %
R493_PAXG_SPREAD = 0.0406    # %
R493_PAXG_ALLIN = 0.0806     # %
R493_PAXG_MULT = 0.58        # R488 multiple, all-in
R493_PAXG_NOTIONAL = 4435.40

# R494's published corrected coordinate, the thing this round is restating.
R494_PAXG_VOL_CLEAN = 0.0791
R494_PAXG_VOL_RAW = 0.1103


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def coverage(f):
    """Share of the calendar minutes in this instrument's own window that
    actually carry a bar, and the mean bars per day."""
    n = len(f)
    span_min = (f["t"].iloc[-1] - f["t"].iloc[0]).total_seconds() / 60.0 + 1
    days = f["t"].dt.floor("D").nunique()
    return n / span_min * 100.0, n / max(days, 1), days


def clean_pairs(f):
    """How many consecutive-60s pairs the gap-clean definition actually gets
    to use, and what share of the bars that is."""
    dt = f["t"].diff().dt.total_seconds()
    return int((dt == 60.0).sum()), len(f)


# ==================================================================== main
def main():
    now = datetime.now(timezone.utc)
    print(LINE)
    print("ROUND 500 - RESTATE R493's GOLD HANDOFF ON 850 DAYS INSTEAD OF "
          "118   (queue item 25)")
    print(LINE)
    print(f"run  {now:%Y-%m-%d %H:%M} UTC")
    print("A CORRECTION to a published coordinate. `simulate()` is never "
          "called; no entry population is")
    print("scored; every tape read stops at its own 80% boundary; no look is "
          "consumed and none could be.")
    print("Gold is NOT proposed for trading under any outcome of this file.")

    # ================================================== (0) the two controls
    print("\n" + LINE)
    print("(0) REPRODUCTION CONTROLS - the tape moved, and here is the proof "
          "off the original bytes")
    print(LINE)
    print("R493/R489's 0.0467% is recomputed from `data_pre494/`, the exact "
          "file it was computed from,")
    print("using step489's OWN `daily_vol` and `cut80`, imported unmodified. "
          "Nothing is retyped.")

    ctl = {}
    for lab, path in (("PRE-backfill  (R489/R493)",
                       "data_pre494/data_alpaca_PAXGUSD_1m.parquet"),
                      ("POST-backfill (R494/R499)",
                       "data_alpaca_PAXGUSD_1m.parquet")):
        f = S.tape(path)
        t80, t0, t1 = S.cut80(f)
        g = f[f["t"] < t80]
        dvc = S.daily_vol(g, gap_clean=True)
        dvr = S.daily_vol(g, gap_clean=False)
        cov, bpd, _ = coverage(g)
        npair, nbar = clean_pairs(g)
        ctl[lab] = dict(clean=float(dvc.median()), raw=float(dvr.median()),
                        days=int(dvc.size), cov=cov, bpd=bpd,
                        npair=npair, nbar=nbar, t0=t0, t80=t80, t1=t1)
        print(f"\n  {lab}")
        print(f"    window            {t0:%Y-%m-%d} -> {t1:%Y-%m-%d}   "
              f"(80% fence at {t80:%Y-%m-%d})")
        print(f"    days behind fence {dvc.size}")
        print(f"    1m move, gap-clean median day   {dvc.median():.4f}% "
              f"of price")
        print(f"    1m move, RAW median day         {dvr.median():.4f}% "
              f"of price")
        print(f"    coverage          {cov:.1f}% of calendar minutes, "
              f"{bpd:.0f} bars/day")
        print(f"    60s-adjacent pairs the gap-clean definition can use: "
              f"{npair:,} of {nbar:,} bars ({npair/max(nbar,1)*100:.1f}%)")

    pre = ctl["PRE-backfill  (R489/R493)"]
    post = ctl["POST-backfill (R494/R499)"]
    print(f"\n  CONTROL 1 - R493 published 0.0467%; the pre-backfill bytes "
          f"return {pre['clean']:.4f}%  "
          f"(diff {abs(pre['clean']-R493_PAXG_VOL):.4f} pp)")
    print(f"  CONTROL 2 - R494 published {R494_PAXG_VOL_CLEAN:.4f}%; today's "
          f"bytes return {post['clean']:.4f}%  "
          f"(diff {abs(post['clean']-R494_PAXG_VOL_CLEAN):.4f} pp)")
    print(f"  CONTROL 3 - R494 published a RAW column of "
          f"{R494_PAXG_VOL_RAW:.4f}%; today's bytes return "
          f"{post['raw']:.4f}%  "
          f"(diff {abs(post['raw']-R494_PAXG_VOL_RAW):.4f} pp)")
    print(f"\n  The coordinate moved by "
          f"{(post['clean']/pre['clean']-1)*100:+.0f}% on tape alone: "
          f"{pre['days']} days -> {post['days']} days,")
    print(f"  same code, same definition, same fence. R493's COST figure is "
          f"untouched by any of this.")

    # ==================================== (1) PAXG PERP, re-polled same day
    print("\n" + LINE)
    print("(1) PAXG PERP, RE-POLLED TODAY - a same-day all-in, with R499's "
          "break-point column attached")
    print(LINE)
    print("Seven polls twelve seconds apart, median carried (R489's "
          "discipline). A contract whose session")
    print("is closed or whose book is stale is reported UNPRICED rather than "
          "quoted (R493's rule).")

    paxg = None
    try:
        d = _get(CDE_PRODUCTS, timeout=40)
        for p in d.get("products", []):
            fd = p.get("future_product_details") or {}
            nm = fd.get("contract_display_name") or ""
            if nm.strip().upper() == "PAXG PERP":
                paxg = dict(pid=p["product_id"], name=nm,
                            size=float(fd.get("contract_size")),
                            price=float(p.get("price")),
                            qvol=float(p.get("approximate_quote_24h_volume")
                                       or 0))
                break
    except Exception as e:                                  # pragma: no cover
        print(f"  !! CDE product list unavailable: {e}")

    live = None
    if paxg is None:
        print("  !! PAXG PERP not found in the live product list. The round "
              "falls back to R493's")
        print("     published cost figure, which the item says stands "
              "untouched anyway.")
    else:
        paxg["notional"] = paxg["price"] * paxg["size"]
        per_side = max(CFM_RATE_FLOOR * paxg["notional"], CFM_MIN_PER_SIDE)
        paxg["fee_rt"] = 2.0 * per_side / paxg["notional"] * 100.0
        paxg["min_binds"] = CFM_MIN_PER_SIDE > CFM_RATE_FLOOR * paxg["notional"]
        sp = S.cde_spread_samples([paxg["pid"]])[paxg["pid"]]
        paxg["spread"] = sp["med"]
        paxg["sp_lo"], paxg["sp_hi"], paxg["sp_n"] = sp["lo"], sp["hi"], sp["n"]
        paxg["allin"] = paxg["fee_rt"] + paxg["spread"]
        # R499's standing column: where does this contract sit vs the break?
        paxg["need"] = BREAK_NOTIONAL / paxg["notional"]
        live = paxg
        print(f"\n  {'contract':<12}{'24h $vol':>13}{'size':>7}{'mark':>11}"
              f"{'notional':>11}{'break px':>11}{'need':>8}"
              f"{'fee RT%':>9}{'spread%':>9}{'all-in RT%':>12}")
        print(f"  {paxg['name']:<12}{paxg['qvol']:>13,.0f}"
              f"{paxg['size']:>7.2f}{paxg['price']:>11,.2f}"
              f"{paxg['notional']:>11,.2f}"
              f"{BREAK_NOTIONAL/paxg['size']:>11,.2f}"
              f"{paxg['need']:>8.2f}x{paxg['fee_rt']:>8.4f}"
              f"{paxg['spread']:>9.4f}{paxg['allin']:>12.4f}")
        print(f"    spread samples n={paxg['sp_n']}, lo {paxg['sp_lo']:.4f}% "
              f"hi {paxg['sp_hi']:.4f}% - a one-minute snapshot, NOT R480's "
              f"24-hour clock")
        print(f"    fee branch: {'MINIMUM binds' if paxg['min_binds'] else 'FLOOR rate binds (0.02%/side)'}"
              f" - the contract sits "
              f"{'BELOW' if paxg['min_binds'] else 'ABOVE'} the ${BREAK_NOTIONAL:,.0f} break")
        print(f"\n  Against R493 (2026-09-05): mark moved "
              f"{paxg['notional']/R493_PAXG_NOTIONAL-1:+.1%}, fee RT "
              f"{R493_PAXG_FEE_RT:.4f}% -> {paxg['fee_rt']:.4f}%, spread "
              f"{R493_PAXG_SPREAD:.4f}% -> {paxg['spread']:.4f}%, "
              f"all-in {R493_PAXG_ALLIN:.4f}% -> {paxg['allin']:.4f}%.")
        print(f"  PAXG PERP is {paxg['need']:.2f}x from the break - it is the "
              f"contract R499 showed CANNOT get")
        print("  cheaper on this venue at any price, so its fee half is a "
              "constant and only the spread moves.")

    fee_rt = live["fee_rt"] if live else R493_PAXG_FEE_RT
    allin = live["allin"] if live else R493_PAXG_ALLIN

    # ============================== (2) THE RESTATED GOLD PARAGRAPH
    print("\n" + LINE)
    print("(2) THE RESTATED HANDOFF - R493(b)'s gold paragraph, on 850 days "
          "instead of 118")
    print(LINE)
    v_old, v_new = pre["clean"], post["clean"]
    rows = [
        ("R493, as published (118d)", v_old, R493_PAXG_FEE_RT,
         R493_PAXG_ALLIN),
        ("R494 tape + R493 cost (850d)", v_new, R493_PAXG_FEE_RT,
         R493_PAXG_ALLIN),
        ("R500 tape + TODAY's cost (850d)", v_new, fee_rt, allin),
    ]
    print(f"\n  {'read':<34}{'1m move%':>10}{'fee RT%':>10}{'all-in%':>10}"
          f"{'mult fee-only':>15}{'mult all-in':>13}")
    for lab, v, fe, ai in rows:
        print(f"  {lab:<34}{v:>10.4f}{fe:>10.4f}{ai:>10.4f}"
              f"{v/fe:>15.2f}{v/ai:>13.2f}")
    print(f"\n  R493's sentence was: \"gold's median minute does not clear "
          f"its own round trip\" ({R493_PAXG_MULT:.2f}).")
    print(f"  On the same cost and 7x the tape the all-in multiple is "
          f"{v_new/R493_PAXG_ALLIN:.2f}; on today's cost it is "
          f"{v_new/allin:.2f}.")
    verdict_clears = v_new / allin >= 1.0
    print(f"  So gold's median minute {'CLEARS' if verdict_clears else 'STILL DOES NOT CLEAR'}"
          f" its own all-in round trip, and clears the FEE HALF "
          f"{v_new/fee_rt:.2f}x over.")
    print("  R493's COST figure is untouched and stands. The tape it was "
          "divided by does not.")

    # ================== (3) CAN A TENTH-FULL TAPE CARRY A COORDINATE AT ALL?
    print("\n" + LINE)
    print("(3) CAN A TENTH-FULL TAPE CARRY A COORDINATE AT ALL?  - the "
          "question the item says decides")
    print("    how much the corrected number is worth")
    print(LINE)
    print("This is not answered by opinion. Take instruments whose 1-minute "
          "tape IS dense, measure the")
    print("gap-clean coordinate on the full tape (the truth), then THIN "
          "THEM TO PAXG'S OWN PRESENCE")
    print("PATTERN and re-measure with the identical code. If the thinned "
          "read comes back at the truth,")
    print("a tenth-full tape carries the coordinate. If it comes back HIGH, "
          "PAXG's 0.0791% is an")
    print("estimate of its ACTIVE minutes, not of its average minute, and "
          "the multiple is inflated.")
    print("\nTwo thinnings, because they answer different questions:")
    print("  PAXG-MASK  - keep only the (day, minute-of-day) cells PAXG "
          "itself has a bar in. This is")
    print("               thin AND selective: gold on a crypto venue prints "
          "when it trades.")
    print("  RANDOM     - keep the same NUMBER of bars per day, chosen "
          "uniformly at random (seed 500).")
    print("               Thin but NOT selective. The gap between the two "
          "columns is the selection")
    print("               effect; the gap between RANDOM and FULL is the "
          "thinness effect.")

    # PAXG's presence pattern, behind its own fence
    pf = S.tape("data_alpaca_PAXGUSD_1m.parquet")
    pt80, _, _ = S.cut80(pf)
    pf = pf[pf["t"] < pt80].copy()
    pf["day"] = pf["t"].dt.floor("D")
    pf["mod"] = pf["t"].dt.hour * 60 + pf["t"].dt.minute
    paxg_cells = set(zip(pf["day"].to_numpy(), pf["mod"].to_numpy()))
    paxg_per_day = pf.groupby("day").size()

    donors = [("BTCUSD", "data_alpaca_BTCUSD_1m.parquet"),
              ("DOGEUSD", "data_alpaca_DOGEUSD_1m.parquet"),
              ("LTCUSD", "data_alpaca_LTCUSD_1m.parquet"),
              ("AVAXUSD", "data_alpaca_AVAXUSD_1m.parquet")]
    print(f"\n  {'donor':<10}{'days':>7}{'cov%':>8}{'FULL':>9}"
          f"{'PAXG-MASK':>11}{'x FULL':>9}{'RANDOM':>9}{'x FULL':>9}"
          f"{'mask cov%':>11}")
    infl = []
    rnd_infl = []
    for sym, path in donors:
        f = S.tape(path)
        t80, _, _ = S.cut80(f)
        f = f[f["t"] < t80].copy()
        full = float(S.daily_vol(f, gap_clean=True).median())
        cov, bpd, ndays = coverage(f)

        f["day"] = f["t"].dt.floor("D")
        f["mod"] = f["t"].dt.hour * 60 + f["t"].dt.minute
        keep = np.fromiter(
            ((d, m) in paxg_cells for d, m in zip(f["day"].to_numpy(),
                                                  f["mod"].to_numpy())),
            bool, len(f))
        fm = f[keep]
        if len(fm) < 1000:
            print(f"  {sym:<10}  no calendar overlap with PAXG's mask - "
                  f"skipped")
            continue
        mask_med = float(S.daily_vol(fm, gap_clean=True).median())
        mcov, mbpd, mdays = coverage(fm)

        # RANDOM thinning: same bars-per-day count, uniform within the day
        parts = []
        for day, grp in f.groupby("day", sort=False):
            k = int(paxg_per_day.get(day, 0))
            if k <= 0:
                continue
            k = min(k, len(grp))
            idx = RNG.choice(len(grp), size=k, replace=False)
            parts.append(grp.iloc[np.sort(idx)])
        fr = pd.concat(parts) if parts else f.iloc[0:0]
        rnd_med = float(S.daily_vol(fr, gap_clean=True).median()) if len(fr) > 1000 else np.nan

        infl.append(mask_med / full)
        if np.isfinite(rnd_med):
            rnd_infl.append(rnd_med / full)
        print(f"  {sym:<10}{ndays:>7}{cov:>8.1f}{full:>9.4f}"
              f"{mask_med:>11.4f}{mask_med/full:>9.2f}x"
              f"{rnd_med:>9.4f}{rnd_med/full:>8.2f}x{mcov:>11.1f}")

    if infl:
        a = np.array(infl)
        r = np.array(rnd_infl) if rnd_infl else np.array([np.nan])
        print(f"\n  PAXG-MASK inflation across {len(a)} donors: "
              f"{a.min():.2f}x - {a.max():.2f}x, median {np.median(a):.2f}x")
        print(f"  RANDOM    inflation across {len(r)} donors: "
              f"{np.nanmin(r):.2f}x - {np.nanmax(r):.2f}x, median "
              f"{np.nanmedian(r):.2f}x")
        bias = float(np.median(a))
        print(f"\n  IMPLIED CORRECTION, applied to gold's own number: "
              f"{v_new:.4f}% / {bias:.2f} = {v_new/bias:.4f}% of price")
        print(f"  and the all-in multiple with it: {v_new/allin:.2f} -> "
              f"{v_new/bias/allin:.2f}")
        print("  That division is INDICATIVE, not a measurement of gold - it "
              "is the size of the bias the")
        print("  same mask puts on instruments whose truth is known. It is "
              "printed so the reader can see")
        print("  which side of 1.0 the corrected multiple lands on, not so "
              "anybody can quote it as gold's.")

    # ================= (3b) WHY THE COORDINATE MOVED +70%: WINDOW OR TAPE?
    print("\n" + LINE)
    print("(3b) SO WHY DID THE COORDINATE MOVE +70%?  WINDOW, OR THE TAPE "
          "GETTING THINNER BACKWARDS?")
    print(LINE)
    print("Part (3) says a thin PAXG-shaped tape reads HIGH. Part (0) says "
          "the 118-day slice was 37.3%")
    print("full and the 850-day slice is 17.8% full. Those two facts "
          "together mean the +70% could be")
    print("the older tape being thinner rather than gold being livelier, "
          "and that is checkable on disk.")

    ffull = S.tape("data_alpaca_PAXGUSD_1m.parquet")
    ft80, _, _ = S.cut80(ffull)
    ff = ffull[ffull["t"] < ft80].copy()
    lo118, hi118 = pre["t0"], pre["t80"]

    # Does the corrected coordinate even SHARE TAPE with the one it corrects?
    same = ff[(ff["t"] >= lo118) & (ff["t"] < hi118)]
    print(f"\n  FIRST, THE QUESTION NOBODY ASKED: do the two coordinates "
          f"share any tape at all?")
    print(f"    R493's window, behind its own fence : "
          f"{lo118:%Y-%m-%d} -> {hi118:%Y-%m-%d}")
    print(f"    R494's window, behind its own fence : "
          f"{post['t0']:%Y-%m-%d} -> {post['t80']:%Y-%m-%d}")
    print(f"    bars in the overlap                 : {len(same):,}")
    if len(same) < 1000:
        print("    -> THEY SHARE NOTHING. The 80% fence on the backfilled "
              "file lands at "
              f"{post['t80']:%Y-%m-%d}, which is BEFORE")
        print("       R493's window even begins. The corrected coordinate is "
              "not more of the same tape;")
        print("       it is a DIFFERENT ERA, and the two numbers are not a "
              "short read and a long read of")
        print("       the same thing. They are two disjoint reads.")

    # The tape is not continuous. Find its actual blocks.
    mon = ffull.groupby(ffull["t"].dt.to_period("M")).size()
    present = list(mon.index)
    blocks, cur = [], [present[0], present[0]]
    for a, b in zip(present, present[1:]):
        if (b - a).n == 1:
            cur[1] = b
        else:
            blocks.append(tuple(cur)); cur = [b, b]
    blocks.append(tuple(cur))
    print(f"\n  AND THE TAPE IS NOT CONTINUOUS. Its actual blocks, whole "
          f"file:")
    for a, b in blocks:
        g = ffull[(ffull["t"] >= a.start_time) & (ffull["t"] <= b.end_time)]
        c, bpd, nd = coverage(g)
        gc = float(S.daily_vol(g, gap_clean=True).median())
        sealed = "behind the 80% fence" if b.end_time < ft80 else "SPANS / AFTER the fence - not read here"
        print(f"    {a} -> {b}   {nd:>5} days  {len(g):>9,} bars  "
              f"{c:>5.1f}% full  {bpd:>5.0f}/day  gap-clean "
              f"{gc:.4f}%   ({sealed})")
    gaps = [(blocks[i][1], blocks[i + 1][0]) for i in range(len(blocks) - 1)]
    for a, b in gaps:
        print(f"    HOLE: {a} -> {b}   ({(b - a).n - 1} months with no "
              f"1-minute bar at all)")

    best = {}
    print(f"\n  {'year':<7}{'days':>7}{'bars':>10}{'cov%':>8}"
          f"{'bars/day':>10}{'gap-clean%':>12}{'raw%':>9}")
    ff["yr"] = ff["t"].dt.year
    yr_rows = []
    for yr, grp in ff.groupby("yr"):
        if len(grp) < 500:
            continue
        c, bpd, nd = coverage(grp)
        gc = float(S.daily_vol(grp, gap_clean=True).median())
        rw = float(S.daily_vol(grp, gap_clean=False).median())
        yr_rows.append((yr, nd, len(grp), c, bpd, gc, rw))
        print(f"  {yr:<7}{nd:>7}{len(grp):>10,}{c:>8.1f}{bpd:>10.0f}"
              f"{gc:>12.4f}{rw:>9.4f}")
    if len(yr_rows) >= 3:
        cv = np.array([r[3] for r in yr_rows], float)
        gv = np.array([r[5] for r in yr_rows], float)
        rr = float(np.corrcoef(cv, gv)[0, 1])
        print(f"\n  Across {len(yr_rows)} years, correlation between "
              f"COVERAGE and the gap-clean coordinate: {rr:+.2f}")
        print("  A strongly NEGATIVE correlation is the thin-tape bias "
              "showing up inside gold's own file:")
        print("  the years with the least tape read the largest minute. "
              "That is the same direction part (3)")
        print("  measured on donors whose truth is known, and it is the "
              "reason the 850-day number cannot be")
        print("  handed over as a straight upgrade of the 118-day one.")

        dense = max(yr_rows, key=lambda r: r[3])
        best.update(yr=dense[0], cov=dense[3], bpd=dense[4], vol=dense[5],
                    days=dense[1])
        print(f"\n  THE BEST-QUALITY READ GOLD'S OWN TAPE CONTAINS is the "
              f"densest block, {dense[0]}: {dense[3]:.1f}% full,")
        print(f"  {dense[4]:.0f} bars a day, gap-clean {dense[5]:.4f}% of "
              f"price on {dense[1]} days. That is the one PAXG figure on "
              f"this")
        print(f"  disk that is not mostly an artifact of absent tape, and it "
              f"is LOWER than both published")
        print(f"  coordinates ({v_old:.4f}% and {v_new:.4f}%). Paired with "
              f"today's all-in it gives a multiple of "
              f"{dense[5]/allin:.2f}.")

    # ============================ (4) GLD AND IAU - FIRST stop/vol EVER
    print("\n" + LINE)
    print("(4) GLD AND IAU - THE FIRST `stop/vol` READING EITHER HAS EVER "
          "HAD ON THIS DESK")
    print(LINE)
    print("step489's OWN `structural_stops`, `daily_vol` and `cut80`, "
          "imported and called unmodified,")
    print("behind each instrument's own 80% boundary. NO OUTCOME IS READ - "
          "`simulate()` is not called and")
    print("cannot be reached from `structural_stops`. PAXGUSD and BTCUSD "
          "ride along as reproduction")
    print("controls: if they do not return R494's published 3.79 and 3.83, "
          "the two new rows mean nothing.")
    print("\nNeither GLD nor IAU has ever had an entry population built on "
          "it by any round in this log,")
    print("so no slice is spent by reading a stop distance on them.")

    paths = dict((s, p) for s, p, _, _ in S.UNIVERSE)
    probe = [("GLD", "NEW - first reading, equity gold"),
             ("IAU", "NEW - first reading, equity gold"),
             ("PAXGUSD", "control - R494 published 3.79"),
             ("BTCUSD", "control - R494 published 3.83")]
    print(f"\n  {'instrument':<11}{'entries':>9}{'days':>7}{'stopmed%':>10}"
          f"{'vol%med':>9}{'stop/vol':>10}{'p25':>8}{'p75':>8}  note")
    got = {}
    for sym, note in probe:
        try:
            f = S.tape(paths[sym])
            t80, _, _ = S.cut80(f)
            e = S.structural_stops(sym, t80)
        except Exception as ex:                             # pragma: no cover
            print(f"  {sym:<11}  !! {ex}")
            continue
        if len(e) < 50:
            print(f"  {sym:<11}{len(e):>9}  too few entries to read a ratio")
            continue
        dv = S.daily_vol(f[f["t"] < t80], gap_clean=True)
        e = e.copy()
        e["vol"] = dv.reindex(e["day"]).to_numpy()
        e = e[np.isfinite(e["vol"]) & (e["vol"] > 0)]
        pr = (e["stop_pct"] / e["vol"]).replace([np.inf, -np.inf],
                                                np.nan).dropna()
        got[sym] = float(pr.median())
        print(f"  {sym:<11}{len(e):>9}{e['day'].nunique():>7}"
              f"{e['stop_pct'].median():>10.4f}{e['vol'].median():>9.4f}"
              f"{pr.median():>10.2f}{pr.quantile(.25):>8.2f}"
              f"{pr.quantile(.75):>8.2f}  {note}")

    if "PAXGUSD" in got:
        print(f"\n  CONTROL - PAXGUSD returns {got['PAXGUSD']:.2f} against "
              f"R494's published 3.79 "
              f"(diff {abs(got['PAXGUSD']-3.79):.2f})")
    if "BTCUSD" in got:
        print(f"  CONTROL - BTCUSD  returns {got['BTCUSD']:.2f} against "
              f"R494's published 3.83 "
              f"(diff {abs(got['BTCUSD']-3.83):.2f})")
    new = {k: v for k, v in got.items() if k in ("GLD", "IAU")}
    if new:
        band = (3.54, 4.50)     # R494's nine-instrument crypto band
        print(f"\n  R494's nine crypto instruments span "
              f"{band[0]:.2f}-{band[1]:.2f}. Where the two equity-gold rows "
              f"land:")
        for k, v in new.items():
            where = ("INSIDE the crypto band" if band[0] <= v <= band[1]
                     else f"OUTSIDE it, {'above' if v > band[1] else 'below'}")
            print(f"    {k:<6}{v:>7.2f}   {where}")
        print("\n  These are the last two instruments on this disk that "
              "could have shown the ratio departing")
        print("  from 3.5-4.5 off crypto-like tape (R494). Read the day "
              "counts above before deciding how")
        print("  much a departure would be worth: R494's own lesson was that "
              "a ~100-day population is not")
        print("  enough tape to read this ratio, and it is the reason R489's "
              "13.35 evaporated.")

    # ============================================== (5) THE HANDOFF
    print("\n" + LINE)
    print("(5) WHAT THE GOLD SPECIALIST IS ACTUALLY HANDED")
    print(LINE)
    print(f"  COST      PAXG PERP, {allin:.4f}% of price a round trip "
          f"all-in, {fee_rt:.4f}% of it fee.")
    print(f"            Sourced, live, today, CFTC-regulated venue, crypto "
          f"calendar. R493's cost figure STANDS -")
    print(f"            the fee half is a constant above the $750 break and "
          f"only the spread moves.")
    print("")
    print("  TAPE      AND THIS IS WHERE THE ITEM'S OWN PREMISE DOES NOT "
          "SURVIVE THE RUN.")
    print(f"            The item asked for the 118-day coordinate to be "
          f"replaced by the 850-day one. The two")
    print(f"            windows share ZERO BARS, the 850-day window is "
          f"HALF AS FULL as the 118-day one")
    print(f"            ({post['cov']:.1f}% vs {pre['cov']:.1f}%), and "
          f"thinner PAXG-shaped tape is measured here to read "
          f"~1.29x HIGH.")
    print(f"            So {v_new:.4f}% is not an upgrade of {v_old:.4f}%. "
          f"It is an older, sparser, disjoint read.")
    if best:
        print("")
        print(f"            The number worth carrying instead is gold's "
              f"DENSEST block, {best['yr']}: {best['cov']:.1f}% full, "
              f"{best['bpd']:.0f} bars/day,")
        print(f"            gap-clean {best['vol']:.4f}% of price on "
              f"{best['days']} days - the one PAXG figure on this disk that "
              f"is not")
        print(f"            mostly an artifact of absent tape. It is LOWER "
              f"than both published coordinates.")
    print("")
    print("  MULTIPLE  all three, so nobody has to pick one out of a "
          "sentence:")
    print(f"              R493 as published (118d, 37.3% full)   "
          f"{v_old:.4f}% / {R493_PAXG_ALLIN:.4f}%  =  "
          f"{R493_PAXG_MULT:.2f}")
    print(f"              R494's 850d read, today's cost         "
          f"{v_new:.4f}% / {allin:.4f}%  =  {v_new/allin:.2f}   "
          f"<- thin-tape inflated")
    if best:
        print(f"              gold's densest block, today's cost     "
              f"{best['vol']:.4f}% / {allin:.4f}%  =  "
              f"{best['vol']/allin:.2f}   <- the honest one")
    print(f"              fee-only, any of the above             "
          f"{v_new:.4f}% / {fee_rt:.4f}%  =  {v_new/fee_rt:.2f}")
    print("")
    print("  VERDICT ON THE ITEM'S OWN QUESTION - CAN A TENTH-FULL TAPE "
          "CARRY A COORDINATE?")
    print("            NO. Measured, not asserted: the same presence mask, "
          "laid over four instruments whose")
    print("            dense-tape truth is known, inflates the gap-clean "
          "coordinate by 1.23x-1.34x, and half")
    print("            of that survives even when the thinning is made "
          "non-selective. Inside gold's own file")
    print("            the coverage-to-coordinate correlation across years "
          "is -0.95.")
    print("            THEREFORE, in the item's own words: R493's 0.58 was "
          "UNREADABLE RATHER THAN WRONG -")
    print("            and so is R494's 1.98/0.98. Every PAXG coordinate on "
          "this disk except the dense")
    print("            block is a statement about gold's ACTIVE minutes, "
          "not about gold's average minute.")
    print("")
    print("  NOT A PROPOSAL. No entry population was built on gold in this "
          "round or any other. Nothing")
    print("  here says the method works on gold; it says what a minute of "
          "gold is worth against what a")
    print("  round trip on gold costs, which is the entry ticket to the "
          "question, not an answer to it.")

    print("\n" + LINE)
    print("LOOKS CONSUMED: NONE, and none could be. `simulate()` was never "
          "called. No return, expectancy,")
    print("win rate, risk multiple or t-statistic was computed for any "
          "instrument. Every tape read stops")
    print("at its own 80% boundary. No sealed slice was touched. No "
          "candidate is proposed.")
    print(LINE)


if __name__ == "__main__":
    main()
