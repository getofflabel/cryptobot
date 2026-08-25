"""STEP 484 — WHY THE FOREX BOOK HAS NEVER PLACED A TRADE.

THE FACT THIS EXISTS TO EXPLAIN. OANDA practice account 101-001-39901192-001
was created 2026-07-27T00:26:41Z and on 2026-08-25 it still reads NAV
$100,000.00, balance $100,000.00, 0 open trades, 0 open positions, 0 pending
orders and lastTransactionID 3. Not one order in its life. The forex book has
been armed on it for four weeks.

WHAT THIS FILE DOES AND WHAT IT REFUSES TO DO. It reads. It fetches candles
from OANDA's practice host with the READ-ONLY client, it walks `alex_engine`'s
own gates over them, and it drives a real `alex_live.Engine` minute by minute
through the four weeks. It never builds a venue, never imports the order path
and cannot place anything.

IT REPRODUCES RENDER'S VIEW, NOT THE LAPTOP'S. `.gitignore` holds
`*.parquet`, so not one `data_oanda_*.parquet` is in the repository and the
worker has never had a cache. `tjr_desk.cached` therefore returns None on
Render for every frame and `join_bars` gets the live half alone. This file
fetches the same way — `LIVE_BARS` counts, `complete_only=True`, no cache
underneath — so the frames it reasons over are the frames the worker has.

THE THREE QUESTIONS, IN ORDER.

  1. WAS THERE ANYTHING TO TRADE. Walk every 4-hour candle whose close falls
     in the armed window through `find_setups_dumb`'s gates in the order the
     function itself applies them, and name the FIRST gate that said no. That
     is the date x pair x reason table.

  2. WOULD THE LIVE LAYER HAVE CAUGHT IT. Poll a real `alex_live.Engine` once
     a minute across the whole window with the frames truncated to the bars
     that had actually closed by that minute — the desk's own decision path,
     including `last_bar`, `seen`, `ENTRY_FRESHNESS` and the session short
     circuit. Anything the finder produced and the engine did not enter is a
     plumbing bug.

  3. HOW SURPRISING IS ZERO. step472 measured the cadence. Given it, work out
     how likely four silent weeks are if the build is correct.

THE VERDICT, 2026-08-25. LEGITIMATE METHOD SILENCE, NOT A BUG.

  * 108 four-hour candles closed inside his entry window across the three
    pairs in the four weeks. Every one of them was refused by the method
    itself: 43 because the last CLOSED weekly candle disagreed with 4-hour
    structure (Wallace's own ruling of 2026-07-27), 61 because no engulfing
    candle formed in the direction of structure, and 4 — the near misses —
    because no structure point to the left paid his 1:2.
  * the same 500-bar cache-less frame and a 5-year frame give BYTE-IDENTICAL
    gate answers on all 129 candles per pair, so data depth blocked nothing.
  * a real `alex_live.Engine` polled 30,961 times per pair across the window
    produced 0 setups, 0 adopted-as-stale and 0 entries, matching the finder
    exactly. There was nothing for the live layer to drop.
  * the last setup the method produced anywhere was GBP/JPY 2026-07-23 01:00,
    four days BEFORE the account was opened. The drought started before the
    book was armed.
  * a silent 28 days is a 1-in-10 event on the measured cadence and has
    happened 16 times in five years. See `droughts`.
  * the order path was proved live: replaying the 2026-07-23 GBP/JPY setup
    through `ForexMarket.decide` produced a fully dressed signal — yen
    conversion 0.006280, the broker's margin cap cutting the size to 90% of
    what the stop asked for, 20x as the leverage that implies — and stopped
    only at `is_armed`.

WHAT WAS ACTUALLY BROKEN, AND IT IS NOT WHY THE MONTH WAS QUIET. The desk
could not have told Wallace the difference. Fixed in `tjr_desk`:

  1. `AlexMarket.decide` never set `last_reason`, so the evening card said
     "forex — no setup" every night whatever had happened — a book whose
     candles never arrived read identically to a book whose method said no.
     It now carries the real answer and names any pair it could not look at.
  2. AN EMPTY WEEKLY FRAME SILENTLY REFUSED EVERY TRADE, FOREVER.
     `weekly_bias_table` on an empty frame builds a table with no rows, every
     setup then fails the last-closed-weekly test on `j < 0`, and no
     exception is raised. On Render there is no parquet cache, so that frame
     is one live OANDA request per pair per poll and `bars()` swallows a
     failed one into an empty frame. `decide` now refuses out loud.
  3. A BOOK THAT NEVER BUILT was invisible to the evening card, which only
     ever walks the books that DID build. `MISSING_BOOKS` now reaches it —
     render.yaml warned about exactly this: "keys that existed only on the
     laptop have silently broken this worker twice, and both times it looked
     exactly like the strategy deciding not to trade."

Run:  python3 step484_forex_audit.py            (fetch, walk, replay, report)
      python3 step484_forex_audit.py --offline  (reuse the snapshot on disk)
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

import alex_engine as ae
import alex_live
import tjr_desk

REPO = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(REPO, "step484_forex_audit_frames.json")
TABLE = os.path.join(REPO, "step484_forex_audit.csv")

# THE ARMED WINDOW. The account was created 2026-07-27T00:26Z; the audit runs
# to the moment the account was read.
ARMED_FROM = pd.Timestamp("2026-07-27 00:00")
ARMED_TO = pd.Timestamp("2026-08-25 12:00")

PAIRS = ("EUR/USD", "GBP/USD", "GBP/JPY")


# ============================================================== THE CANDLES
def fetch(offline: bool = False) -> dict:
    """The frames the Render worker sees: live OANDA, no cache underneath.

    Snapshotted to disk so the walk and the replay reason over ONE set of
    candles and a re-run cannot quietly move a gate.
    """
    if offline and os.path.exists(SNAP):
        raw = json.load(open(SNAP))
        return {sym: {tf: _thaw(d) for tf, d in frames.items()}
                for sym, frames in raw.items()}
    import oanda_api
    cli = oanda_api.from_env(practice=True)
    if cli is None:
        raise SystemExit("OANDA is not configured; nothing can be read.")
    gran = {"4h": "H4", "15m": "M15", "1w": "W"}
    out, cold = {}, {}
    for sym in PAIRS:
        inst = alex_live.instrument_for(sym)
        frames = {}
        for tf, want in tjr_desk.AlexMarket.LIVE_BARS.items():
            # EXACTLY `AlexMarket.bars` WITH THE CACHE ABSENT, which is what
            # `cached()` returns on a worker whose repo has no parquet.
            fresh = cli.frame(inst, gran[tf], count=want, complete_only=True)
            frames[tf] = tjr_desk.join_bars(None, fresh)
        out[sym] = frames
        cold[sym] = {tf: _freeze(d) for tf, d in frames.items()}
    json.dump(cold, open(SNAP, "w"))
    return out


def _freeze(d: pd.DataFrame) -> dict:
    return {"t": [str(x) for x in d["t"]],
            **{c: [float(v) for v in d[c]] for c in
               ("open", "high", "low", "close")}}


def _thaw(d: dict) -> pd.DataFrame:
    f = pd.DataFrame(d)
    f["t"] = pd.to_datetime(f["t"])
    return f


# ======================================================= 1. THE GATE WALK
#
# THE ORDER IS THE FUNCTION'S OWN ORDER. `find_setups_dumb` checks the session
# window, then the ATR, then 4-hour structure, then Wallace's weekly-close
# rule, then the trigger candle, then the stop, then the target. Reporting a
# later gate's answer as the reason a trade did not happen would be a
# different claim from the one the engine makes, so the first NO wins and the
# ones behind it are recorded as "not reached".

REASONS = {
    "session": "outside his entry window (only the 01:00 and 05:00 New York "
               "4-hour closes, Monday to Thursday)",
    "flat": "4-hour structure was flat, so there was no side to take",
    "weekly": "the last CLOSED weekly candle disagreed with 4-hour structure",
    "trigger": "no engulfing candle in the direction of structure",
    "stop": "the stop would have sat the wrong side of the entry",
    "target": "no structure point left paid his 1:2, so the setup was refused",
    "SETUP": "A SETUP FIRED",
}


def walk(sym: str, frames: dict) -> pd.DataFrame:
    """Every 4-hour candle in the armed window and the first gate that
    refused it. Uses `alex_engine`'s own primitives, never a copy of them."""
    inst = alex_live.instrument_for(sym)
    cfg = alex_live.live_config(inst)
    d = frames[cfg.tf]
    st = ae.trend_series(d)
    a = ae.atr(d, cfg.atr_len)
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    t = d["t"].to_numpy()
    sh, sl = ae.two_candle_swings(d)
    bsh, bsl = ae.two_candle_swings(ae.body_frame(d))
    wk = ae.weekly_bias_table(frames)
    wk_at = wk["known_at"].to_numpy()
    step = pd.Timedelta(minutes=ae._TF_MINUTES[cfg.tf])

    rows = []
    for i in range(cfg.atr_len + 3, len(d)):
        decided = pd.Timestamp(t[i]) + step
        if not (ARMED_FROM <= decided <= ARMED_TO):
            continue
        direction = int(st[i])
        j = int(np.searchsorted(wk_at, np.datetime64(decided), "right")) - 1
        wdir = int(wk["dir"].iloc[j]) if j >= 0 else 0
        eaten = (ae.engulfed_count(o, h, lo, c, i, direction)
                 if direction else 0)
        row = {"pair": sym, "decided": decided,
               "day": decided.strftime("%a %Y-%m-%d"),
               "close_ny": decided.strftime("%H:%M"),
               "structure_4h": {1: "up", -1: "down", 0: "flat"}[direction],
               "weekly": {1: "up", -1: "down", 0: "flat"}[wdir],
               "agree": bool(direction and wdir == direction),
               "engulfed": int(eaten)}

        if cfg.session_gate and not ae.dumb_in_window(decided, cfg):
            rows.append(dict(row, gate="session"))
            continue
        if np.isnan(a[i]) or a[i] <= 0:
            rows.append(dict(row, gate="atr"))
            continue
        if direction == 0:
            rows.append(dict(row, gate="flat"))
            continue
        if wdir != direction:
            rows.append(dict(row, gate="weekly"))
            continue
        if eaten < cfg.min_engulfed:
            rows.append(dict(row, gate="trigger"))
            continue
        buf = cfg.stop_buffer_atr * a[i]
        entry = float(c[i])
        back = max(0, i - max(eaten, 1) - 1)
        if direction < 0:
            rec = sh[back:i + 1]
            rec = rec[~np.isnan(rec)]
            struct = max(float(h[back:i + 1].max()),
                         float(rec.max()) if len(rec) else -np.inf)
            stop = struct + buf
            bad = stop <= entry
        else:
            rec = sl[back:i + 1]
            rec = rec[~np.isnan(rec)]
            struct = min(float(lo[back:i + 1].min()),
                         float(rec.min()) if len(rec) else np.inf)
            stop = struct - buf
            bad = stop >= entry
        if bad:
            rows.append(dict(row, gate="stop"))
            continue
        target = ae.target_for(cfg, bsh, bsl, i, entry, stop, direction, a[i])
        if target is None:
            rows.append(dict(row, gate="target"))
            continue
        rows.append(dict(row, gate="SETUP", entry=entry, stop=float(stop),
                         target=float(target)))
    return pd.DataFrame(rows)


# ===================================================== 2. THE LIVE REPLAY
def replay(frames: dict, every_minutes: int = 1) -> dict:
    """Drive a real `alex_live.Engine` minute by minute across the window.

    THE FRAMES ARE TRUNCATED TO WHAT HAD CLOSED, which is the only honest way
    to ask this question: the engine's `ENTRY_FRESHNESS` and its `last_bar`
    bookkeeping both exist to handle a tape that arrives late, and handing it
    the finished tape would hide exactly the bug we are hunting.

    NEVER CUT FROM THE LEFT. `AlexMarket.bars` says his 50 EMA is a running
    average whose value depends on where the series began; the truncation
    here only ever drops bars from the RIGHT.
    """
    out = {}
    for sym in PAIRS:
        inst = alex_live.instrument_for(sym)
        eng = alex_live.Engine(cfg_over=dict(alex_live.BOOK))
        d4, m15, w1 = frames[sym]["4h"], frames[sym]["15m"], frames[sym]["1w"]
        t4 = (d4["t"] + pd.Timedelta(hours=4)).to_numpy()
        t15 = (m15["t"] + pd.Timedelta(minutes=15)).to_numpy()
        tw = (w1["t"] + pd.Timedelta(days=7)).to_numpy()
        acts, seen_polls = [], 0
        now = ARMED_FROM
        while now <= ARMED_TO:
            # THE CURRENCY WEEK, the same gate `AlexMarket.open_now` applies,
            # written against the simulated clock instead of the wall one.
            if _fx_open(now):
                i4 = int(np.searchsorted(t4, np.datetime64(now), "right"))
                i15 = int(np.searchsorted(t15, np.datetime64(now), "right"))
                iw = int(np.searchsorted(tw, np.datetime64(now), "right"))
                if i4 and i15:
                    seen_polls += 1
                    got = eng.step(inst,
                                   {"4h": d4.iloc[:i4], "15m": m15.iloc[:i15],
                                    "1w": w1.iloc[:iw]},
                                   100_000.0, 1.0, now=now)
                    for g in got:
                        acts.append({"kind": g["kind"], "at": g["at"],
                                     "symbol": g["symbol"]})
            now += pd.Timedelta(minutes=every_minutes)
        out[sym] = {"actions": acts, "polls": seen_polls,
                    "adopted": len(eng.adopted.get(inst, [])),
                    "seen": len(eng.seen)}
    return out


def _fx_open(now: pd.Timestamp) -> bool:
    """Sunday 17:00 New York to Friday 17:00 — `AlexMarket.open_now`."""
    wd, hh = now.weekday(), now.hour + now.minute / 60.0
    if wd == 5:
        return False
    if wd == 6:
        return hh >= 17.0
    if wd == 4:
        return hh < 17.0
    return True


# =============================================== 3. HOW SURPRISING IS ZERO
#
# NOT AN ASSUMED RATE — A COUNTED ONE. `cadence()` replays the shipping config
# over five years of cached candles and counts the entries; `droughts()` then
# asks the only question that matters, which is not "what does a Poisson say"
# but "how often did this actually happen". Measured 2026-08-25:
#
#   158 entries in 263.9 weeks across the three pairs = 0.599 a week, which is
#   step472's figure to three decimals
#   EUR/USD 0.201   GBP/USD 0.243   GBP/JPY 0.155  entries a week
#
#   of the 1,820 rolling 28-day windows in that stretch, 185 held ZERO entries
#   across all three pairs — 10.2%, against the Poisson's 9.0%
#   the longest real drought across all three pairs was 66 days
#   16 of the 157 gaps between consecutive entries ran 28 days or longer
#
# A SILENT MONTH IS A ONE-IN-TEN MONTH AND IT HAS HAPPENED SIXTEEN TIMES IN
# FIVE YEARS. It is not evidence of anything being broken.
def cadence(start="2021-07-05", end="2026-07-26") -> pd.DataFrame:
    """Every entry the shipping config would have taken, from the cached
    candles. One row per entry."""
    rows = []
    for sym, inst in alex_live.FOREX.items():
        r = ae.run_instrument(inst, pd.Timestamp(start), pd.Timestamp(end),
                              cfg=alex_live.live_config(inst),
                              frames=ae.load(inst), mode="dumb")
        rows += [{"pair": sym, "t": pd.Timestamp(t.entry_t)}
                 for t in r["trades"]]
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)


def droughts(entries: pd.DataFrame, start="2021-07-05",
             end="2026-07-26", days: int = 28) -> dict:
    """How often a stretch this long really did hold no entry at all."""
    t = entries["t"].to_numpy()
    win = pd.Timedelta(days=days)
    at = pd.date_range(pd.Timestamp(start), pd.Timestamp(end) - win, freq="D")
    n = np.array([int(((t >= np.datetime64(d))
                       & (t < np.datetime64(d + win))).sum()) for d in at])
    gaps = np.diff(np.sort(t)).astype("timedelta64[D]").astype(int)
    return {"windows": len(n), "mean_per_window": float(n.mean()),
            "empty": int((n == 0).sum()),
            "share_empty": float((n == 0).mean()),
            "longest_gap_days": int(gaps.max()),
            "gaps_over_window": int((gaps >= days).sum()), "gaps": len(gaps),
            "last_entry": pd.Timestamp(t.max())}


def probability_of_silence(trades_per_week: float, weeks: float,
                           pairs: int = 1) -> float:
    """P(no trade at all) if entries arrive at the measured rate.

    A Poisson count with the measured mean. It is the right shape for this:
    the entries are rare, independent-ish arrivals on a continuous clock, and
    the question is only whether the count was zero.
    """
    return float(np.exp(-trades_per_week * weeks * pairs))


# ==================================================================== SAY IT
def report(offline: bool = False) -> dict:
    frames = fetch(offline=offline)
    tables = {sym: walk(sym, frames[sym]) for sym in PAIRS}
    full = pd.concat(tables.values(), ignore_index=True)
    full.to_csv(TABLE, index=False)

    print("=" * 78)
    print("THE ARMED WINDOW: 2026-07-27 to 2026-08-25, three pairs, "
          "OANDA practice")
    print("=" * 78)
    print("\nWHAT THE CANDLES LOOK LIKE ON RENDER (no parquet cache exists "
          "there):")
    for sym in PAIRS:
        for tf in ("4h", "15m", "1w"):
            d = frames[sym][tf]
            print(f"  {sym:8s} {tf:4s} {len(d):5d} bars, "
                  f"{d['t'].iloc[0]} .. {d['t'].iloc[-1]}")

    print("\n" + "-" * 78)
    print("EVERY 4-HOUR CANDLE IN HIS ENTRY WINDOW, AND WHAT REFUSED IT")
    print("-" * 78)
    inwin = full[full["gate"] != "session"]
    print(f"{'day':16s} {'close':6s} {'pair':8s} {'4h':6s} {'weekly':7s} "
          f"{'eng':4s} why")
    for _, r in inwin.sort_values(["decided", "pair"]).iterrows():
        print(f"{r['day']:16s} {r['close_ny']:6s} {r['pair']:8s} "
              f"{r['structure_4h']:6s} {r['weekly']:7s} {r['engulfed']:<4d} "
              f"{REASONS.get(r['gate'], r['gate'])}")

    print("\n" + "-" * 78)
    print("THE COUNT, PER PAIR")
    print("-" * 78)
    for sym in PAIRS:
        t = tables[sym]
        n_in = int((t["gate"] != "session").sum())
        print(f"  {sym}: {len(t)} closed 4-hour candles, {n_in} of them in "
              f"his entry window")
        for gate, n in t[t["gate"] != "session"]["gate"].value_counts().items():
            print(f"      {n:3d}  {REASONS.get(gate, gate)}")

    print("\n" + "-" * 78)
    print("WEEK BY WEEK: WHAT THE WEEKLY CANDLE SAID AND WHETHER 4-HOUR "
          "STRUCTURE EVER AGREED")
    print("-" * 78)
    full["week"] = full["decided"].dt.to_period("W-SUN").astype(str)
    for sym in PAIRS:
        t = tables[sym].copy()
        t["week"] = t["decided"].dt.to_period("W-SUN").astype(str)
        print(f"\n  {sym}")
        for wk, g in t.groupby("week"):
            gi = g[g["gate"] != "session"]
            wdirs = sorted(set(gi["weekly"])) or sorted(set(g["weekly"]))
            agreed = int(gi["agree"].sum())
            print(f"    {wk}  weekly {'/'.join(wdirs):12s} "
                  f"in-window closes {len(gi):2d}   4h agreed on "
                  f"{agreed:2d} of them")

    print("\n" + "-" * 78)
    print("THE LIVE LAYER, POLLED ONCE A MINUTE ACROSS THE SAME FOUR WEEKS")
    print("-" * 78)
    live = replay(frames)
    for sym in PAIRS:
        r = live[sym]
        ent = [a for a in r["actions"] if a["kind"] == "enter"]
        print(f"  {sym}: {r['polls']:6d} polls, {r['seen']:3d} setups seen, "
              f"{r['adopted']:2d} adopted as stale, {len(ent)} entries")
        for a in ent:
            print(f"      ENTER {a['at']}")

    fired = full[full["gate"] == "SETUP"]
    print("\n" + "-" * 78)
    print("THE TWO ANSWERS SIDE BY SIDE")
    print("-" * 78)
    print(f"  setups the METHOD produced in the window : {len(fired)}")
    print(f"  entries the LIVE LAYER would have taken  : "
          f"{sum(len([a for a in live[s]['actions'] if a['kind'] == 'enter']) for s in PAIRS)}")
    print(f"  orders the OANDA account actually holds  : 0")

    print("\n" + "-" * 78)
    print("HOW SURPRISING IS ZERO — COUNTED, NOT ASSUMED")
    print("-" * 78)
    ent = cadence()
    dr = droughts(ent)
    weeks = (pd.Timestamp("2026-07-26") - pd.Timestamp("2021-07-05")).days / 7
    for sym in PAIRS:
        n = int((ent["pair"] == sym).sum())
        print(f"  {sym}: {n:3d} entries in {weeks:.0f} weeks = "
              f"{n/weeks:.3f} a week")
    print(f"  ALL THREE: {len(ent)} entries = {len(ent)/weeks:.3f} a week "
          f"(step472 said 0.6)")
    print(f"\n  rolling 28-day windows examined      : {dr['windows']}")
    print(f"  windows that held ZERO entries       : {dr['empty']}"
          f"  = {100*dr['share_empty']:.1f}%")
    print(f"  the same number a Poisson would give : "
          f"{100*probability_of_silence(len(ent)/weeks, 4.0):.1f}%")
    print(f"  longest real drought, all three pairs: "
          f"{dr['longest_gap_days']} days")
    print(f"  gaps of 28 days or more              : "
          f"{dr['gaps_over_window']} of {dr['gaps']}")
    print(f"  the last setup before this drought   : {dr['last_entry']}")
    print("\n  A SILENT MONTH IS A ONE-IN-TEN MONTH and it has happened "
          f"{dr['gaps_over_window']} times in five years.")

    return {"table": full, "live": live, "entries": ent, "droughts": dr}


if __name__ == "__main__":
    report(offline="--offline" in sys.argv)
