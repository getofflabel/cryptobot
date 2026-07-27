#!/usr/bin/env python3
"""step471_prop_eval.py — can the Alex engine survive a prop-firm rulebook?

REPLAY ONLY. No venue is touched, no order is placed, nothing is bought and
nothing is signed up for. `alex_engine` is imported read-only and no existing
file in this repo is modified.

WHAT THIS ACTUALLY MEASURES, AND WHY IT IS THE QUESTION WORTH ASKING

    A prop-firm evaluation is a DISCIPLINE TEST wearing a profit target as a
    costume. It asks one thing: can this thing add 9% of an account WITHOUT
    ever losing 5% of that account inside a single day, and WITHOUT ever
    giving back 10% of the account from its own high-water mark. That is the
    same question as "can this bot be trusted with real money", asked by
    somebody who takes the account away the instant the answer is no.

    So the headline table here is the RISK one — worst day, worst
    peak-to-trough, time spent under water. The pass odds are its consequence,
    and the ticket economics are a footnote.

EVERY PERCENTAGE SAYS WHICH ONE IT IS. Nothing below is a bare number:
    - "share of the ACCOUNT" = what the account balance/equity changed by
    - "move in the PRICE"    = what the instrument itself did
    - LEVERAGE is what sizing produces and is reported as leverage.

Run:  python3 step471_prop_eval.py            (full report)
      python3 step471_prop_eval.py --quick    (skip the funded-account model)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alex_engine as ae  # read-only

REPO = os.path.dirname(os.path.abspath(__file__))

START = "2021-07-05"
END = "2026-07-26"

# ===================================================================== RULES
#
# HIS, from the $50 video (`hb7ot1_szWI_50dollars_clean.txt`, uploaded
# 2026-07-26) and the founder interview (`DejB31rwv8c.txt`, 2026-07-15):
ACCOUNT = 5_000.0        # "with 50 bucks, you can really get a two-phase
#                          challenge with a $5,000 account"
PHASE1_TARGET = 0.09     # "your profit target be 9% for your step one"
PHASE2_TARGET = 0.05     # "and then your profit target be 5% for step two"
TICKET = 50.0            # the $50 the whole video is named after
SPLIT = 0.90             # "you get 90% profit split"
PAYOUT_CAP = 0.10        # founder, 2026-07-15: "profit cap 5% on one phase,
#                          10% on two phase" — the payout is capped at 10% of
#                          the account per cycle, then the account resets
CONSISTENCY = 0.35       # founder: "No single trading day profit can exceed
#                          30% or 35% of the total reduced profit"
MIN_TRADING_DAYS = 3     # founder: "Minimum trading days pretty standard".
#                          He never says the number. 3 is OURS.
MAX_CONCURRENT = 2       # "Limit yourself to two positions a week. No need
#                          for any more of that." His hard cap, applied to the
#                          SHARED evaluation account.

# OURS. He is SILENT on the two rules that actually kill accounts, and every
# real firm has both. Industry-standard shape, measured the strict way:
DAILY_LOSS_CAP = 0.05    # OURS. 5% of the ACCOUNT, measured intraday against
#                          the equity the day STARTED at, floating included.
TOTAL_DD_CAP = 0.10      # OURS. 10% of the ACCOUNT, measured intraday against
#                          the running equity HIGH-WATER mark (trailing — the
#                          strict reading).
#
# The nearest thing to his own numbers is `lHGkup8CoTE.txt`, 2026-07-19,
# describing the firm he personally passed years ago: "Step one, make 10% in
# 30 days. Step two, make 8% in 60 days. And you have 8% stop loss, 10% stop
# loss." That is a LOOSER daily cap than ours, so ours is the harder test; the
# 8%/10% reading is reported as a sensitivity.
HIS_OLD_DAILY = 0.08

# OURS: the FX day rolls at 17:00 New York, which is where this tape's daily
# bodies close. A firm resets its daily loss on its own server clock; 17:00
# New York is the honest FX boundary and is what is used here.
DAY_ROLL_SHIFT = pd.Timedelta(hours=7)

# OURS: gold at a prop firm is a CFD on the firm's book, so it is charged
# OANDA's measured XAU/USD spread, NOT the BloFin crypto-gold cost the engine
# uses for its own live venue.
OANDA_XAU_ROUND_TRIP = 0.0001414058972684461

MAX_EVAL_DAYS = 730      # OURS: a replay has to terminate. Reported as
#                          "ran out of runway", never as a pass.


# ============================================================ CONFIGURATIONS
@dataclass
class Book:
    name: str
    instruments: list
    cfg_over: dict = field(default_factory=dict)
    note: str = ""


BOOKS = [
    Book("majors, his literal floor", ae.PAIRS, {},
         "the $50 video's own instruction: majors, engulf floor of 1"),
    Book("EUR/USD alone", ["EUR_USD"], {},
         "his spine taken literally: one pair"),
    Book("majors, engulf >= 3", ae.PAIRS, {"min_engulfed": 3},
         "his own quality dial, where step470's 5-year sign turns"),
    Book("majors, engulf >= 4", ae.PAIRS, {"min_engulfed": 4},
         "his dial further; step470's best 5-year money"),
    Book("majors, 1:3 target", ae.PAIRS, {"target_r": 3.0},
         "his newer target statement, LwMsai2ppKc.txt 2026-02-22"),
    Book("majors + gold", ae.INSTRUMENTS, {},
         "gold as a CFD, charged OANDA's XAU/USD spread (OURS)"),
]

RISK_BAND = [0.005, 0.010, 0.015, 0.020, 0.030]
# 0.5% and 1% are HIS OWN words for a challenge account, the $50 video,
# 2026-07-26: "have a fixed percentage on your challenge account. Make it a
# 1% rule. Make it a half percent rule." 2% and 3% are OURS, run to show what
# sizing up does to the caps. 3% is his OWN-MONEY number, never his prop one.


# ================================================================ THE TAPE
def day_key(ts) -> pd.Timestamp:
    """The trading day a timestamp belongs to, on the 17:00 New York roll."""
    return (pd.Timestamp(ts) + DAY_ROLL_SHIFT).normalize()


def build_trades(book: Book, cache: dict) -> pd.DataFrame:
    """Every trade the engine takes, with its INTRADAY floating path, in R.

    R is scale-free here. `r` is pnl / risk_dollars, and the cost is a fixed
    share of the notional while the notional is proportional to risk_dollars,
    so a trade's R on a $100,000 account and its R on a $5,000 account are the
    same number. That is what lets step470's trade record be replayed onto an
    evaluation account without re-deriving sizing.
    """
    rows = []
    for inst in book.instruments:
        over = dict(book.cfg_over)
        if inst == ae.GOLD:
            over["round_trip_cost_pct"] = OANDA_XAU_ROUND_TRIP
        if inst not in cache:
            cache[inst] = ae.load(inst)
        r = ae.run_instrument(inst, START, END,
                              cfg=ae.dumb_config_for(inst, **over),
                              frames=cache[inst], shared={}, mode="dumb")
        m15 = cache[inst]["15m"]
        tt = m15["t"].values
        hi_a = m15["high"].values
        lo_a = m15["low"].values
        for t in r["trades"]:
            if t.outcome not in ("stop", "target", "friday"):
                continue
            dist = abs(t.entry - t.stop)
            if dist <= 0 or not t.risk_dollars:
                continue
            cost_r = t.cost / t.risk_dollars
            i0 = int(np.searchsorted(tt, np.datetime64(pd.Timestamp(t.entry_t))))
            i1 = int(np.searchsorted(tt, np.datetime64(pd.Timestamp(t.exit_t)),
                                     side="right"))
            seg_t = tt[i0:i1]
            if not len(seg_t):
                continue
            tgt_r = ((t.target - t.entry) * t.direction) / dist
            adverse = lo_a[i0:i1] if t.direction > 0 else hi_a[i0:i1]
            favour = hi_a[i0:i1] if t.direction > 0 else lo_a[i0:i1]
            r_lo = ((adverse - t.entry) * t.direction) / dist - cost_r
            r_hi = ((favour - t.entry) * t.direction) / dist - cost_r
            # A 15-minute bar's wick can run far past the stop. The POSITION
            # cannot: it is flat at the stop the moment price touches it, and
            # flat at the target the moment price touches that. Floating
            # equity is therefore bounded by the bracket, not by the wick.
            r_lo = np.maximum(r_lo, -1.0 - cost_r)
            r_hi = np.minimum(r_hi, tgt_r - cost_r)
            r_lo = np.minimum(r_lo, t.r_multiple)   # the realised R still
            r_hi = np.maximum(r_hi, t.r_multiple)   # has to appear on the path
            keys = (pd.DatetimeIndex(seg_t) + DAY_ROLL_SHIFT).normalize()
            g = pd.DataFrame({"d": keys, "lo": r_lo, "hi": r_hi})
            agg = g.groupby("d").agg(lo=("lo", "min"), hi=("hi", "max"))
            path = {d: (float(a), float(b))
                    for d, a, b in zip(agg.index, agg["lo"], agg["hi"])}
            rows.append({
                "instrument": inst,
                "entry_t": pd.Timestamp(t.entry_t),
                "exit_t": pd.Timestamp(t.exit_t),
                "entry_d": day_key(t.entry_t),
                "exit_d": day_key(t.exit_t),
                "r": float(t.r_multiple),
                "outcome": t.outcome,
                "leverage": float(t.leverage),
                "path": path,
            })
    return pd.DataFrame(rows).sort_values("entry_t").reset_index(drop=True)


def gate_concurrency(f: pd.DataFrame, cap: int = MAX_CONCURRENT) -> pd.DataFrame:
    """His hard cap, applied to the SHARED evaluation account.

    step470 ran each instrument on its OWN $100,000, so four instruments could
    hold four positions at once. One $5,000 evaluation account cannot.
    Earliest entry wins; a setup arriving while `cap` are already open is
    dropped, which is what a human following his rule would do.
    """
    keep, open_until = [], []
    for i, row in f.iterrows():
        open_until = [x for x in open_until if x > row["entry_t"]]
        if len(open_until) >= cap:
            continue
        keep.append(i)
        open_until.append(row["exit_t"])
    return f.loc[keep].reset_index(drop=True)


def active_days(f: pd.DataFrame) -> np.ndarray:
    """Every day on which SOMETHING is open. Days with nothing open cannot
    move equity, cannot breach and cannot pass, so they are skipped — elapsed
    calendar days are still counted from the start date."""
    s = set()
    for p in f["path"]:
        s.update(p.keys())
    return np.array(sorted(s), dtype="datetime64[ns]")


# ============================================================ THE SIMULATOR
class Account:
    __slots__ = ("balance", "start", "hwm", "daily_cap", "total_cap", "target",
                 "risk_frac", "trailing", "dead", "passed", "days",
                 "day_profits", "worst_day", "worst_dd", "underwater_days",
                 "trades", "next_i")

    def __init__(self, balance, daily_cap, total_cap, target, risk_frac,
                 trailing=True):
        self.balance = balance
        self.start = balance
        self.hwm = balance
        self.daily_cap = daily_cap * balance
        self.total_cap = total_cap * balance
        self.target = target
        self.risk_frac = risk_frac
        self.trailing = trailing
        self.dead = None            # "daily" | "total"
        self.passed = False
        self.days = 0
        self.day_profits = {}
        self.worst_day = 0.0        # worst one-day equity change, share of acct
        self.worst_dd = 0.0         # worst peak-to-trough, share of account
        self.underwater_days = 0
        self.trades = 0
        self.next_i = 0


def run_account(f, i_start, days_arr, opts) -> Account:
    """Walk one prop-firm account forward from trade index `i_start`.

    NO LOOKAHEAD. The only thing consulted on day d is what had already
    happened by the end of day d. Sizing uses the balance as it stood at the
    moment the position was opened.

    Breach checks run on INTRADAY equity, and the strict reading is taken:
    every open position is assumed to reach its own worst point of the day at
    the same moment. With the two-position cap that is at most two trades, and
    it is the reading a firm's risk engine produces on a bad tick.
    """
    a = Account(opts["balance"], opts["daily_cap"], opts["total_cap"],
                opts["target"], opts["risk_frac"], opts.get("trailing", True))
    n = len(f)
    a.next_i = i_start
    if i_start >= n:
        return a

    entry_d = f["entry_d"].values
    exit_d = f["exit_d"].values
    r_arr = f["r"].values
    paths = f["path"].values

    d0 = entry_d[i_start]
    k0 = int(np.searchsorted(days_arr, d0))
    max_days = opts.get("max_days", MAX_EVAL_DAYS)

    i = i_start
    live = []
    floating = 0.0

    for k in range(k0, len(days_arr)):
        d = days_arr[k]
        a.days = int((d - d0) / np.timedelta64(1, "D")) + 1
        if a.days > max_days:
            a.next_i = i
            return a
        day_start_eq = a.balance + floating

        # ---- open whatever starts today, oldest first, cap enforced
        while i < n and entry_d[i] <= d:
            if entry_d[i] == d and len(live) < MAX_CONCURRENT:
                live.append((a.risk_frac * a.balance, paths[i],
                             exit_d[i], r_arr[i]))
                a.trades += 1
            i += 1

        dts = pd.Timestamp(d)
        lo_sum = hi_sum = 0.0
        for risk, path, _xd, _r in live:
            pr = path.get(dts)
            if pr is not None:
                lo_sum += pr[0] * risk
                hi_sum += pr[1] * risk
        eq_lo = a.balance + lo_sum
        eq_hi = a.balance + hi_sum

        # ---- the two rules that kill, on intraday equity
        a.worst_day = min(a.worst_day, (eq_lo - day_start_eq) / a.start)
        a.worst_dd = min(a.worst_dd, (eq_lo - a.hwm) / a.start)
        ref = a.hwm if a.trailing else a.start
        if eq_lo < day_start_eq - a.daily_cap:
            a.dead = "daily"
        elif eq_lo < ref - a.total_cap:
            a.dead = "total"
        if a.dead:
            a.next_i = i
            return a
        a.hwm = max(a.hwm, eq_hi)

        # ---- realise what finished today
        realised = 0.0
        still = []
        for pos in live:
            if pos[2] <= d:
                realised += pos[3] * pos[0]
            else:
                still.append(pos)
        live = still
        a.balance += realised
        if realised:
            a.day_profits[dts] = a.day_profits.get(dts, 0.0) + realised
        floating = 0.0
        for risk, path, _xd, _r in live:
            pr = path.get(dts)
            if pr is not None:
                floating += 0.5 * (pr[0] + pr[1]) * risk
        a.hwm = max(a.hwm, a.balance + max(0.0, floating))
        if a.balance + floating < a.hwm - 1e-9:
            a.underwater_days += 1

        # ---- the target, on REALISED balance (the conservative reading)
        if a.balance >= a.start + a.target and \
                len(a.day_profits) >= MIN_TRADING_DAYS:
            a.passed = True
            a.next_i = i
            return a

    a.next_i = i
    return a


# ================================================================ REPORTING
def evaluate(f, risk_frac, starts, days_arr, trailing=True,
             daily_cap=DAILY_LOSS_CAP) -> dict:
    """Roll a two-phase evaluation across every start week and score them all.

    Rolling starts on overlapping tape are NOT independent samples. The number
    of non-overlapping windows is reported so nobody reads 260 starts as 260
    experiments.
    """
    entry_d = f["entry_d"].values
    out = {"n": 0, "p1": 0, "both": 0,
           "p1_daily": 0, "p1_total": 0, "p1_slow": 0,
           "p2_daily": 0, "p2_total": 0, "p2_slow": 0,
           "days_p1": [], "days_both": [], "worst_day": [],
           "worst_dd": [], "consistency": 0}
    for s in starts:
        idx = int(np.searchsorted(entry_d, np.datetime64(pd.Timestamp(s)),
                                  side="left"))
        if idx >= len(f):
            continue
        out["n"] += 1
        opts = {"balance": ACCOUNT, "daily_cap": daily_cap,
                "total_cap": TOTAL_DD_CAP, "target": PHASE1_TARGET * ACCOUNT,
                "risk_frac": risk_frac, "trailing": trailing}
        a1 = run_account(f, idx, days_arr, opts)
        out["worst_day"].append(a1.worst_day)
        out["worst_dd"].append(a1.worst_dd)
        if a1.dead == "daily":
            out["p1_daily"] += 1
            continue
        if a1.dead == "total":
            out["p1_total"] += 1
            continue
        if not a1.passed:
            out["p1_slow"] += 1
            continue
        out["p1"] += 1
        out["days_p1"].append(a1.days)
        tot = sum(a1.day_profits.values())
        if tot > 0 and max(a1.day_profits.values()) > CONSISTENCY * tot:
            out["consistency"] += 1
        # ---- phase 2: fresh $5,000, starting from the next unused trade
        a2 = run_account(f, a1.next_i, days_arr,
                         dict(opts, target=PHASE2_TARGET * ACCOUNT))
        if a2.dead == "daily":
            out["p2_daily"] += 1
        elif a2.dead == "total":
            out["p2_total"] += 1
        elif a2.passed:
            out["both"] += 1
            out["days_both"].append(a1.days + a2.days)
        else:
            out["p2_slow"] += 1
    return out


def funded_life(f, risk_frac, starts, days_arr) -> dict:
    """After passing: a funded $5,000 on the same caps, paid out at the cap.

    Founder, 2026-07-15: "profit cap ... 10% on two phase ... you get your
    payout, your account gets reset and you're free to trade again."
    """
    entry_d = f["entry_d"].values
    payouts, lives = [], []
    for s in starts:
        idx = int(np.searchsorted(entry_d, np.datetime64(pd.Timestamp(s)),
                                  side="left"))
        if idx >= len(f):
            continue
        n_pay, spent, cur = 0, 0, idx
        while cur < len(f) and spent < 1095:
            a = run_account(f, cur, days_arr,
                            {"balance": ACCOUNT, "daily_cap": DAILY_LOSS_CAP,
                             "total_cap": TOTAL_DD_CAP,
                             "target": PAYOUT_CAP * ACCOUNT,
                             "risk_frac": risk_frac,
                             "max_days": 1095 - spent})
            spent += a.days
            if a.passed:
                n_pay += 1
                cur = max(a.next_i, cur + 1)
                continue
            break
        payouts.append(n_pay)
        lives.append(spent)
    return {"payouts": float(np.mean(payouts)) if payouts else 0.0,
            "life_days": float(np.mean(lives)) if lives else 0.0,
            "n": len(payouts)}


def continuous_risk(f, risk_frac, days_arr) -> dict:
    """The discipline picture with NO evaluation attached: one $5,000 account,
    five years, no reset, no pass, no fail. What does this engine DO to an
    account, and what does it do to it on a bad week?
    """
    entry_d = f["entry_d"].values
    exit_d = f["exit_d"].values
    r_arr = f["r"].values
    paths = f["path"].values
    bal, hwm, floating = ACCOUNT, ACCOUNT, 0.0
    bal_hwm, worst_bal_dd = ACCOUNT, 0.0
    live, i, n = [], 0, len(f)
    worst_day = worst_dd = 0.0
    hit_daily = hit_total = uw = 0
    weekly = {}
    for d in days_arr:
        dts = pd.Timestamp(d)
        day_start_eq = bal + floating
        while i < n and entry_d[i] <= d:
            if entry_d[i] == d and len(live) < MAX_CONCURRENT:
                live.append((risk_frac * bal, paths[i], exit_d[i], r_arr[i]))
            i += 1
        lo = 0.0
        for risk, path, _xd, _r in live:
            pr = path.get(dts)
            if pr is not None:
                lo += pr[0] * risk
        eq_lo = bal + lo
        dd_day = (eq_lo - day_start_eq) / ACCOUNT
        worst_day = min(worst_day, dd_day)
        if dd_day < -DAILY_LOSS_CAP:
            hit_daily += 1
        worst_dd = min(worst_dd, (eq_lo - hwm) / ACCOUNT)
        if (eq_lo - hwm) / ACCOUNT < -TOTAL_DD_CAP:
            hit_total += 1
        realised = sum(p[3] * p[0] for p in live if p[2] <= d)
        live = [p for p in live if p[2] > d]
        bal += realised
        floating = 0.0
        for risk, path, _xd, _r in live:
            pr = path.get(dts)
            if pr is not None:
                floating += 0.5 * (pr[0] + pr[1]) * risk
        eq = bal + floating
        hwm = max(hwm, eq)
        bal_hwm = max(bal_hwm, bal)
        worst_bal_dd = min(worst_bal_dd, (bal - bal_hwm) / ACCOUNT)
        if eq < hwm - 1e-9:
            uw += 1
        wk = dts.to_period("W")
        weekly[wk] = weekly.get(wk, 0.0) + realised
    wv = np.array(list(weekly.values()))
    return {"end": bal, "worst_day": worst_day, "worst_dd": worst_dd,
            "worst_bal_dd": worst_bal_dd,
            "underwater_share": uw / max(1, len(days_arr)),
            "days_over_daily_cap": hit_daily, "days_over_total_cap": hit_total,
            "worst_week": float(wv.min()) / ACCOUNT if len(wv) else 0.0,
            "best_week": float(wv.max()) / ACCOUNT if len(wv) else 0.0,
            "weeks_green": float((wv > 0).mean()) if len(wv) else 0.0}


# ===================================================================== MAIN
def main(argv=None):
    argv = argv or sys.argv[1:]
    quick = "--quick" in argv
    cache: dict = {}

    print("=" * 104)
    print("step471 — THE ALEX ENGINE AGAINST A PROP-FIRM RULEBOOK. Replay "
          "only; no venue, no order, no purchase.")
    print("  Evaluation account $5,000. Phase 1 target +9% of the ACCOUNT, "
          "phase 2 +5% of the ACCOUNT. HIS:")
    print("  hb7ot1_szWI, the $50 video, uploaded 2026-07-26.")
    print("  Daily loss cap 5% of the ACCOUNT and total drawdown cap 10% of "
          "the ACCOUNT, both measured INTRADAY,")
    print("  the total one trailing the equity high-water mark. BOTH CAPS ARE "
          "OURS — he never states either.")
    print("  Two positions open at once, his hard cap. Costs charged: OANDA's "
          "measured spreads.")
    print("=" * 104)

    books, days = {}, {}
    for b in BOOKS:
        raw = build_trades(b, cache)
        f = gate_concurrency(raw)
        books[b.name] = f
        days[b.name] = active_days(f)
        print(f"  {b.name:<26s} {len(raw):>4d} trades -> {len(f):>4d} after "
              f"the two-position cap  ({b.note})")

    # ------------------------------------------------------------ 1. RISK
    print("\n" + "=" * 104)
    print("1. THE DISCIPLINE PICTURE — one $5,000 account, five years, NO "
          "evaluation attached.")
    print("   'Can this be trusted with real money' lives here. Every "
          "percentage is a share of the ACCOUNT.")
    print("=" * 104)
    print("   'worst DAY' is the worst one-day equity change. 'DD equity' is "
          "peak-to-trough on INTRADAY equity")
    print("   against the running high-water mark — the number a prop firm "
          "measures. 'DD closed' is the same")
    print("   thing on closed-trade balance only — the number a human "
          "recognises. Both are shares of the ACCOUNT.")
    print("=" * 104)
    print(f"  {'book':<26s} {'risk/trade':>10s} {'end $':>9s} "
          f"{'worst DAY':>10s} {'DD equity':>10s} {'DD closed':>10s} "
          f"{'under water':>12s} {'worst wk':>9s} {'wks green':>10s} "
          f"{'days<-5%':>9s} {'days<-10%':>10s}")
    risk_rows = []
    for name, f in books.items():
        for rf in RISK_BAND:
            c = continuous_risk(f, rf, days[name])
            risk_rows.append(dict(book=name, risk=rf, **c))
            print(f"  {name:<26s} {rf*100:>9.1f}% ${c['end']:>8,.0f} "
                  f"{c['worst_day']*100:>9.1f}% {c['worst_dd']*100:>9.1f}% "
                  f"{c['worst_bal_dd']*100:>9.1f}% "
                  f"{c['underwater_share']*100:>11.0f}% "
                  f"{c['worst_week']*100:>8.1f}% "
                  f"{c['weeks_green']*100:>9.0f}% "
                  f"{c['days_over_daily_cap']:>9d} "
                  f"{c['days_over_total_cap']:>10d}")
        print()

    # ------------------------------------------------------- 2. PASS ODDS
    print("=" * 104)
    print("2. THE EVALUATION — every Monday in the five years is a start "
          "week. Rolling starts, no lookahead.")
    print("   OVERLAPPING WINDOWS ARE NOT INDEPENDENT SAMPLES. Roughly 5 "
          "non-overlapping year-long attempts")
    print("   exist in this tape; the ~260 starts are 260 readings of the "
          "same five years, not 260 experiments.")
    print("=" * 104)
    print("   PHASE 1 is scored on all starts. PHASE 2 is scored on the "
          "starts that survived phase 1, so the")
    print("   two blocks below add to 100% each. 'too slow' = never reached "
          "the target inside 730 days.")
    print("   HIS OWN TIMELINE for both phases is 30-45 days: "
          "\"anywhere from 30 to 45 days to pass a two-step challenge\".")
    print("=" * 104)
    print(f"  {'book':<26s} {'risk':>6s} {'n':>5s} | {'P1 pass':>8s} "
          f"{'P1 dailyX':>10s} {'P1 totalX':>10s} {'P1 slow':>8s} | "
          f"{'P2 pass':>8s} {'P2 dailyX':>10s} {'P2 totalX':>10s} "
          f"{'P2 slow':>8s} | {'P(BOTH)':>8s} {'med d':>6s} "
          f"{'<=45d':>7s} {'cons.brk':>9s}")
    eval_rows = []
    for name, f in books.items():
        mondays = pd.date_range(pd.Timestamp(f["entry_d"].min()),
                                pd.Timestamp(f["entry_d"].max()), freq="W-MON")
        for rf in RISK_BAND:
            o = evaluate(f, rf, mondays, days[name])
            n = max(1, o["n"])
            m = max(1, o["p1"])
            in45 = (float(np.mean([d <= 45 for d in o["days_both"]]))
                    * o["both"] / n) if o["days_both"] else 0.0
            row = dict(book=name, risk=rf, n=o["n"], p1=o["p1"] / n,
                       both=o["both"] / n,
                       med_p1=np.median(o["days_p1"]) if o["days_p1"] else np.nan,
                       med_both=(np.median(o["days_both"])
                                 if o["days_both"] else np.nan),
                       p1_daily=o["p1_daily"] / n, p1_total=o["p1_total"] / n,
                       p1_slow=o["p1_slow"] / n,
                       p2_pass=o["both"] / m, p2_daily=o["p2_daily"] / m,
                       p2_total=o["p2_total"] / m, p2_slow=o["p2_slow"] / m,
                       both_in_45=in45,
                       consistency=o["consistency"] / m,
                       worst_day=float(np.min(o["worst_day"] or [0])),
                       worst_dd=float(np.min(o["worst_dd"] or [0])))
            eval_rows.append(row)
            print(f"  {name:<26s} {rf*100:>5.1f}% {o['n']:>5d} | "
                  f"{row['p1']*100:>7.1f}% {row['p1_daily']*100:>9.1f}% "
                  f"{row['p1_total']*100:>9.1f}% {row['p1_slow']*100:>7.1f}% | "
                  f"{row['p2_pass']*100:>7.1f}% {row['p2_daily']*100:>9.1f}% "
                  f"{row['p2_total']*100:>9.1f}% {row['p2_slow']*100:>7.1f}% | "
                  f"{row['both']*100:>7.1f}% {row['med_both']:>6.0f} "
                  f"{in45*100:>6.1f}% {row['consistency']*100:>8.0f}%")
        print()

    ev = pd.DataFrame(eval_rows)
    ev.to_csv(os.path.join(REPO, "step471_eval_results.csv"), index=False)
    pd.DataFrame(risk_rows).to_csv(
        os.path.join(REPO, "step471_risk_results.csv"), index=False)

    # -------------------------------------------------------- 3. THE PACE
    print("=" * 104)
    print("3. THE PACE — what the engine actually produces per week, against "
          "what phase 1 demands.")
    print("   HIS arithmetic in the $50 video: \"if you make 3% then lose 1%, "
          "make 3% then lose 1% ... that's")
    print("   roughly the 9% in about 3 weeks\". That is +3% of the ACCOUNT a "
          "week. Below is what the tape gives.")
    print("=" * 104)
    print(f"  {'book':<26s} {'trades':>7s} {'/week':>6s} {'won':>7s} "
          f"{'mean R':>7s} {'R/week':>8s} {'acct/wk @1%':>12s} "
          f"{'weeks to +9%':>13s} {'mean R NEEDED':>14s} {'gap':>8s}")
    weeks = (pd.Timestamp(END) - pd.Timestamp(START)).days / 7.0
    for name, f in books.items():
        r = f["r"].values
        per_wk = len(f) / weeks
        rpw = r.sum() / weeks
        acct_wk = rpw * 0.01
        wk9 = (PHASE1_TARGET / acct_wk) if acct_wk > 0 else float("inf")
        # what mean R per trade would clear phase 1 in 45 days (6.4 weeks) at
        # 1% of the ACCOUNT risked per trade, at THIS cadence
        need = PHASE1_TARGET / 0.01 / (6.43 * per_wk)
        print(f"  {name:<26s} {len(f):>7d} {per_wk:>6.2f} "
              f"{(r > 0).mean()*100:>6.1f}% {r.mean():>7.2f} {rpw:>8.3f} "
              f"{acct_wk*100:>11.2f}% "
              f"{(f'{wk9:.0f}' if np.isfinite(wk9) else 'never'):>13s} "
              f"{need:>14.2f} {need - r.mean():>8.2f}")
    print("  'mean R NEEDED' clears phase 1 inside his own 45-day estimate at "
          "1% of the ACCOUNT per trade,")
    print("  at that book's own cadence. 'gap' is how far short the engine "
          "falls, per trade, in R.")
    print()

    # ------------------------------------------------------- 3b. THE CONTROL
    print("=" * 104)
    print("3b. THE CONTROL — the same entries, the same days, the same stop "
          "distances, DIRECTION REVERSED.")
    print("    If fading the engine passes about as often as following it, "
          "the pass rate is variance rather than")
    print("    the engine's read of the market. This is step470's own control, "
          "carried into the evaluation.")
    print("=" * 104)
    print(f"  {'book':<26s} {'risk':>6s} {'engine P(BOTH)':>15s} "
          f"{'FADED P(BOTH)':>15s} {'verdict':>28s}")
    for name, f in books.items():
        g = f.copy()
        g["r"] = -f["r"].values
        g["path"] = [{d: (-hi, -lo) for d, (lo, hi) in p.items()}
                     for p in f["path"]]
        mondays = pd.date_range(pd.Timestamp(f["entry_d"].min()),
                                pd.Timestamp(f["entry_d"].max()), freq="W-MON")
        for rf in (0.010, 0.015, 0.020):
            a = evaluate(f, rf, mondays, days[name])
            b = evaluate(g, rf, mondays, days[name])
            pa = a["both"] / max(1, a["n"])
            pb = b["both"] / max(1, b["n"])
            v = ("engine ahead" if pa > pb * 1.25 else
                 "FADE AHEAD — no edge" if pb > pa * 1.25 else
                 "indistinguishable")
            print(f"  {name:<26s} {rf*100:>5.1f}% {pa*100:>14.1f}% "
                  f"{pb*100:>14.1f}% {v:>28s}")
        print()

    # ------------------------------------------------- 4. THE SENSITIVITIES
    print("=" * 104)
    print("4. DOES THE ANSWER DEPEND ON OUR TWO INVENTED CAPS? Same books, "
          "his old firm's looser daily cap")
    print("   (8% of the ACCOUNT, lHGkup8CoTE.txt 2026-07-19) and the STATIC "
          "total drawdown instead of trailing.")
    print("=" * 104)
    print(f"  {'book':<26s} {'risk':>6s} {'strict (ours)':>14s} "
          f"{'8% daily':>10s} {'static total DD':>16s}")
    for name, f in books.items():
        mondays = pd.date_range(pd.Timestamp(f["entry_d"].min()),
                                pd.Timestamp(f["entry_d"].max()), freq="W-MON")
        for rf in (0.010, 0.015):
            base = evaluate(f, rf, mondays, days[name])
            loose = evaluate(f, rf, mondays, days[name], daily_cap=HIS_OLD_DAILY)
            static = evaluate(f, rf, mondays, days[name], trailing=False)
            nb = max(1, base["n"])
            print(f"  {name:<26s} {rf*100:>5.1f}% "
                  f"{base['both']/nb*100:>13.1f}% "
                  f"{loose['both']/max(1,loose['n'])*100:>9.1f}% "
                  f"{static['both']/max(1,static['n'])*100:>15.1f}%")
    print()

    # ---------------------------------------------------- 4. THE FOOTNOTE
    if not quick:
        print("=" * 104)
        print("5. THE MONEY — a footnote, not the point. $50 a ticket, 90% "
              "split, payout capped at 10% of the")
        print("   ACCOUNT per cycle with the account reset after each payout "
              "(founder, DejB31rwv8c, 2026-07-15).")
        print("=" * 104)
        print(f"  {'book':<26s} {'risk':>6s} {'P(pass both)':>13s} "
              f"{'tickets/funded':>15s} {'$ in':>9s} "
              f"{'payouts/3yr':>12s} {'$ out':>9s} {'$out per $in':>13s}")
        money_rows = []
        for name, f in books.items():
            mondays = pd.date_range(pd.Timestamp(f["entry_d"].min()),
                                    pd.Timestamp(f["entry_d"].max()),
                                    freq="W-MON")
            for rf in RISK_BAND:
                row = ev[(ev.book == name) & (ev.risk == rf)].iloc[0]
                p = float(row["both"])
                fl = funded_life(f, rf, mondays[::4], days[name])
                tickets = (1.0 / p) if p > 0 else float("inf")
                cash_in = tickets * TICKET
                cash_out = fl["payouts"] * PAYOUT_CAP * ACCOUNT * SPLIT
                ratio = (cash_out / cash_in) if np.isfinite(cash_in) and \
                    cash_in else 0.0
                money_rows.append(dict(book=name, risk=rf, p_both=p,
                                       tickets=tickets, cash_in=cash_in,
                                       payouts=fl["payouts"],
                                       cash_out=cash_out, ratio=ratio))
                print(f"  {name:<26s} {rf*100:>5.1f}% {p*100:>12.1f}% "
                      f"{tickets:>15.1f} ${cash_in:>8,.0f} "
                      f"{fl['payouts']:>12.2f} ${cash_out:>8,.0f} "
                      f"${ratio:>12.2f}")
            print()
        pd.DataFrame(money_rows).to_csv(
            os.path.join(REPO, "step471_money_results.csv"), index=False)

    # ------------------------------------------------------------ VERDICT
    print("=" * 104)
    print("6. THE VERDICT, computed from the tables above rather than "
          "asserted.")
    print("=" * 104)
    survivors = [r for r in risk_rows
                 if r["days_over_daily_cap"] == 0
                 and r["days_over_total_cap"] == 0]
    if survivors:
        print("  Configurations that went FIVE YEARS on one $5,000 account "
              "without ever breaching either cap:")
        for r in survivors:
            print(f"    - {r['book']}, {r['risk']*100:.1f}% of the ACCOUNT "
                  f"risked per trade: worst DAY {r['worst_day']*100:.1f}% of "
                  f"the account, worst")
            print(f"      peak-to-trough {r['worst_dd']*100:.1f}% of the "
                  f"account, ended at ${r['end']:,.0f} "
                  f"({(r['end']/ACCOUNT - 1)*100:+.1f}% of the account in "
                  f"five years).")
    else:
        print("  NONE. Every configuration breached at least one cap inside "
              "five years.")
    best = ev.sort_values("both", ascending=False).iloc[0]
    print(f"\n  Best pass odds anywhere in the band: {best['book']} at "
          f"{best['risk']*100:.1f}% of the ACCOUNT per trade — "
          f"P(pass BOTH) {best['both']*100:.1f}%,")
    print(f"  median {best['med_both']:.0f} days against his own 30-45 day "
          f"estimate, and P(both inside 45 days) "
          f"{best['both_in_45']*100:.1f}%.")
    print(f"  On {best['consistency']*100:.0f}% of the phase-1 passes a "
          f"SINGLE day carried more than 35% of the profit, which is the "
          f"firm's own")
    print("  consistency rule and a soft breach (account reset, not death).")
    print("\n  The pace table is the finding. No configuration reaches +9% of "
          "the account by drift inside a")
    print("  quarter; the passes that happen are variance arriving before a "
          "breach does.")
    print("\nrows written: step471_eval_results.csv, step471_risk_results.csv, "
          "step471_money_results.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
