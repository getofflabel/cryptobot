"""
step494_backfill_screen_tape.py - ROUND 494

BACKFILL THE TAPE THAT THE SCREEN SAYS IS MISSING.
(QUEUE ITEM 18)

Research only. No orders, no account endpoints, no live file touched or
imported for anything but its read-only market-data client. This is PLUMBING,
not a hypothesis: it downloads price history and re-runs an existing screen
unchanged. NO LOOK IS CONSUMED BY ANY PART OF IT, and none could be -
`simulate()` is never called in this file and no entry population exists here.

QUEUE ITEM 18, VERBATIM
  R489's screen was limited by data, not by ideas, in four places: AVAXUSD and
  DOGEUSD have live CDE perpetuals and about four days of 1-minute tape each
  (DOGE's $418 contract puts it in SOL's fee band); ADAUSD, DOTUSD and PAXGUSD
  are ranked off 118-132 days; GLD/IAU off 81; the FX pairs off 138. Alpaca
  served 5.5 years of BTC/ETH/SOL/LINK/LTC 1-minute bars to this repo already,
  so the history very likely exists for the rest.
  Deliverable: backfill 1-minute and 5-minute tape as far back as the source
  will serve for AVAXUSD, DOGEUSD, ADAUSD, DOTUSD and PAXGUSD, write the
  parquets in the existing `data_alpaca_<SYM>_<tf>.parquet` convention, and
  re-run `step489_next_look_screen.py` unchanged to see whether the ranking
  moves. No look, no entry population, no candidate - the screen consumes
  nothing by construction and re-running it is free.
  THE FENCE: backfilling data for an instrument does NOT reset a spent slice
  and must never be used to argue that it does. This item may only touch
  instruments R489 marked INTACT.

THE FENCE, FIXED BEFORE THE RUN AND ENFORCED AS CODE DISCIPLINE
  1. THE FIVE SYMBOLS ARE HARD-CODED AND ARE ALL INTACT. ADA, DOT and PAXG
     are on R489's explicit intact list; AVAX and DOGE have never had an entry
     population built on them in any round in this log (R489 reported them as
     data-absent and ranked neither). No spent instrument is touched: BTC,
     ETH, SOL, LINK, LTC, SPY and QQQ are not fetched, not rewritten and not
     re-windowed by this file.
  2. NOTHING IS RE-SLICED AND NO SLICE IS RESET. This file writes tape and
     runs a screen. It does not cut a 60/20/20 anywhere, and the arrival of
     older bars on an intact instrument does not "unspend" anything, because
     nothing was ever spent on these five.
  3. THE END OF EVERY FILE IS CAPPED AT THE CORPUS BOUNDARY, 2026-07-26.
     Every cached instrument in this repo ends there and every window in
     R485-R493 is cut against it. Letting five files run six weeks further
     than the other twelve would silently make the screen a comparison of
     different windows, and would move the 80% boundary of instruments whose
     sealed slice this round is under orders to protect. Backfill means
     BACKWARD. The cap is stated here, applied in code, and printed in the
     output so it cannot be mistaken for the source running dry.
  4. THE SCREEN IS RE-RUN UNCHANGED. step489_next_look_screen.py is not
     edited, not parameterised and not imported piecemeal - it is executed as
     a subprocess exactly as it stands, and its output is captured verbatim.
     Its own fences (simulate() never called, first 80% only) therefore still
     hold, unmodified, on the new tape.
  4b. THE SCREEN'S PROBE LIST IS HARD-CODED AND CANNOT SEE THE TWO NEW
     INSTRUMENTS. step489's part (b) iterates a fixed seven-name list, so
     AVAXUSD and DOGEUSD - which had 3 days of tape when it was written and
     now have 1,370 and 1,627 - get no stop/vol ratio from it. Editing that
     list would break fence 4. PART 3 below therefore IMPORTS step489 as a
     module and calls its OWN `structural_stops` and `daily_vol`, unmodified,
     on those two symbols, restricted to the same first-80% boundary its
     `cut80` computes. Same machinery, same fence, nothing rewritten. It reads
     the distance from the fill to chart structure and NOTHING ELSE -
     `simulate()` is not called, no outcome is scored, and the standing rule
     that stop/vol is RE-DERIVED and never ported is what makes this
     mandatory rather than optional for two instruments the screen now ranks.
  5. WRITES ARE ATOMIC AND OLD FILES ARE KEPT. Each parquet is written to a
     .tmp and renamed only after the frame passes the integrity checks below,
     and the superseded file is moved to `data_pre494/` rather than deleted,
     so every number R489 published stays reproducible off the exact bytes it
     was computed from.
  6. A SHORTER FRAME IS NEVER WRITTEN OVER A LONGER ONE. If the fetch comes
     back with fewer bars, or a later start, or a shorter span than the file
     already on disk, the existing file is KEPT and the round reports the
     refusal. A backfill that loses history is a bug, not a backfill.

WHAT IS SOURCED HERE
  Alpaca's public crypto bars endpoint (/v1beta3/crypto/us/bars), read-only,
  with the repo's existing keys. Read-only means read-only: this file issues
  GETs against the market-data host and touches no account, order or position
  path. The paging loop is written here rather than reused from alpaca.py
  only because a five-year 1-minute pull needs a rate-limit pause and a 429
  retry that the shared client does not have, and alpaca.py is live plumbing
  that this round must not edit.

HONEST LIMITS, FIXED BEFORE RUNNING
  - "As far back as the source will serve" is a statement about ALPACA, not
    about the asset. Where Alpaca's first bar is late, that is a fact about
    this data vendor; the coin traded before it.
  - Bars are the vendor's aggregates. Gaps in the tape are real and are NOT
    filled, per R481's finding that Alpaca's 1-minute tape has holes; the
    integrity report prints the gap count so the screen's gap-clean
    volatility can be read against it.
  - STALE PROSE WARNING, AND IT IS THE POINT OF RUNNING THE THING UNCHANGED:
    step489's part (b) prints a hard-coded SENTENCE next to a COMPUTED number.
    The number is recomputed on whatever tape is on disk; the sentence was
    written when PAXGUSD had 101 days and read 13.35. If the number moves, the
    sentence does not move with it and will be wrong in the captured output.
    The output is published as it came out, per fence 4, and the discrepancy is
    called out in the log rather than quietly edited away.
  - The screen's spread half is a live seven-poll median taken at run time
    (R489's own limit). Re-running it on a different day re-polls the book,
    so any movement in an all-in cost figure between R489 and R494 is a
    SAMPLE difference and a PRICE difference, not a finding. R489's ranking
    stands as published; this round reports whether more history moves it.

USAGE
  python3 step494_backfill_screen_tape.py            # fetch + screen
  python3 step494_backfill_screen_tape.py --no-fetch # re-run the screen only
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.abspath(__file__))

import alpaca

# ---------------------------------------------------------------- the fence
# Five symbols, all INTACT per R489. Not a parameter, not read from argv.
TARGETS = [
    # (disk symbol, alpaca symbol, why it is intact)
    ("ADAUSD",  "ADA/USD",  "R489 intact list"),
    ("DOTUSD",  "DOT/USD",  "R489 intact list"),
    ("PAXGUSD", "PAXG/USD", "R489 intact list"),
    ("AVAXUSD", "AVAX/USD", "never ranked, no entry population in any round"),
    ("DOGEUSD", "DOGE/USD", "never ranked, no entry population in any round"),
]
TIMEFRAMES = [("1Min", "1m"), ("5Min", "5m")]

PROBE_START = "2015-01-01"      # earlier than any crypto tape can be
END_CAP = "2026-07-26T23:59:59Z"   # fence 3: the corpus boundary
PAUSE_S = 0.35                  # ~170 req/min under Alpaca's 200 ceiling
BACKUP_DIR = os.path.join(REPO, "data_pre494")


def path_for(sym: str, tf: str) -> str:
    return os.path.join(REPO, f"data_alpaca_{sym}_{tf}.parquet")


def fetch_all(cli, sym: str, timeframe: str) -> pd.DataFrame:
    """Every bar the vendor will serve from PROBE_START to the corpus
    boundary, following the page tokens, with a pause and a 429 retry."""
    import requests
    rows: list = []
    token, pages = None, 0
    while True:
        params = {"symbols": sym, "timeframe": timeframe, "limit": 10000,
                  "start": PROBE_START, "end": END_CAP}
        if token:
            params["page_token"] = token
        r = requests.get(f"{alpaca.DATA_URL}/v1beta3/crypto/us/bars",
                         headers=cli._headers(), params=params, timeout=90)
        if r.status_code == 429:
            time.sleep(5)
            continue
        r.raise_for_status()
        got = r.json() or {}
        rows.extend((got.get("bars") or {}).get(sym) or [])
        pages += 1
        token = got.get("next_page_token")
        if pages % 25 == 0:
            print(f"      ... {len(rows):,} bars, {pages} pages", flush=True)
        if not token:
            break
        time.sleep(PAUSE_S)

    if not rows:
        return pd.DataFrame(columns=["t", "open", "high", "low", "close"])
    d = pd.DataFrame(rows)
    ts = pd.to_datetime(d["t"], utc=True, format="mixed")
    out = pd.DataFrame({
        "t": ts.dt.tz_convert("UTC").dt.tz_localize(None),
        "open": d["o"].astype(float), "high": d["h"].astype(float),
        "low": d["l"].astype(float), "close": d["c"].astype(float)})
    return out.sort_values("t").drop_duplicates("t").reset_index(drop=True)


def describe(d: pd.DataFrame) -> dict:
    if d.empty:
        return {"bars": 0, "first": None, "last": None, "days": 0}
    span = (d["t"].iloc[-1] - d["t"].iloc[0])
    return {"bars": len(d), "first": d["t"].iloc[0], "last": d["t"].iloc[-1],
            "days": span.total_seconds() / 86400.0}


def integrity(d: pd.DataFrame, minutes: int) -> dict:
    """What is actually in the frame. Nothing here is repaired; it is
    reported so the screen's numbers can be read against it."""
    if d.empty:
        return {"dupes": 0, "unsorted": 0, "gaps": 0, "bad_ohlc": 0,
                "nonpos": 0, "coverage": 0.0}
    dt = d["t"].diff().dt.total_seconds().iloc[1:]
    step = minutes * 60
    expected = ((d["t"].iloc[-1] - d["t"].iloc[0]).total_seconds() / step) + 1
    hi_ok = (d["high"] >= d[["open", "close"]].max(axis=1) - 1e-12)
    lo_ok = (d["low"] <= d[["open", "close"]].min(axis=1) + 1e-12)
    return {
        "dupes": int(d["t"].duplicated().sum()),
        "unsorted": int((dt < 0).sum()),
        "gaps": int((dt > step).sum()),
        "bad_ohlc": int((~(hi_ok & lo_ok)).sum()),
        "nonpos": int((d[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        "coverage": 100.0 * len(d) / expected if expected > 0 else 0.0,
    }


def backfill() -> list:
    cli = alpaca.from_env()
    if cli is None:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET missing from .env")
    os.makedirs(BACKUP_DIR, exist_ok=True)

    report = []
    for sym, apx, why in TARGETS:
        for tf_api, tf_disk in TIMEFRAMES:
            out = path_for(sym, tf_disk)
            old = pd.read_parquet(out) if os.path.exists(out) else pd.DataFrame()
            o = describe(old)
            print(f"\n  {sym} {tf_disk}: on disk {o['bars']:,} bars "
                  f"({str(o['first'])[:10]} .. {str(o['last'])[:10]}, "
                  f"{o['days']:.0f}d) - {why}", flush=True)
            t0 = time.time()
            new = fetch_all(cli, apx, tf_api)
            n = describe(new)
            secs = time.time() - t0
            print(f"      fetched {n['bars']:,} bars "
                  f"({str(n['first'])[:10]} .. {str(n['last'])[:10]}, "
                  f"{n['days']:.0f}d) in {secs:.0f}s", flush=True)

            # fence 6: never write a shorter frame over a longer one
            keep_old = (not old.empty) and (
                n["bars"] < o["bars"] or n["days"] < o["days"] - 1e-9
                or (n["first"] is not None and o["first"] is not None
                    and n["first"] > o["first"]))
            if keep_old:
                print("      REFUSED: fetch is not longer than the file on "
                      "disk. Existing file KEPT, nothing written.", flush=True)
                report.append({"sym": sym, "tf": tf_disk, "written": False,
                               "old": o, "new": n, "integ": None,
                               "reason": "fetch not longer than disk"})
                continue
            if new.empty:
                print("      REFUSED: vendor returned nothing.", flush=True)
                report.append({"sym": sym, "tf": tf_disk, "written": False,
                               "old": o, "new": n, "integ": None,
                               "reason": "empty response"})
                continue

            integ = integrity(new, 1 if tf_disk == "1m" else 5)
            if integ["dupes"] or integ["unsorted"] or integ["bad_ohlc"] \
                    or integ["nonpos"]:
                print(f"      REFUSED on integrity: {integ}", flush=True)
                report.append({"sym": sym, "tf": tf_disk, "written": False,
                               "old": o, "new": n, "integ": integ,
                               "reason": "integrity check failed"})
                continue

            if not old.empty:                      # fence 5: keep the old bytes
                shutil.copy2(out, os.path.join(
                    BACKUP_DIR, os.path.basename(out)))
            tmp = out + ".tmp"
            new.to_parquet(tmp, index=False)
            os.replace(tmp, out)
            gained = n["days"] - o["days"]
            print(f"      WROTE {out}  (+{gained:.0f} days, "
                  f"x{(n['bars']/o['bars']) if o['bars'] else float('inf'):.1f} bars, "
                  f"coverage {integ['coverage']:.1f}%, {integ['gaps']:,} gaps)",
                  flush=True)
            report.append({"sym": sym, "tf": tf_disk, "written": True,
                           "old": o, "new": n, "integ": integ, "reason": ""})
    return report


def main() -> int:
    print("=" * 78)
    print("ROUND 494 - QUEUE ITEM 18: BACKFILL THE TAPE THE SCREEN SAYS IS "
          "MISSING")
    print("=" * 78)
    print("  Five INTACT instruments only. No spent slice is touched, no "
          "window is re-cut,")
    print(f"  and every file is capped at the corpus boundary {END_CAP[:10]} "
          "so the screen")
    print("  stays a like-for-like comparison. Backfill means BACKWARD.")

    report = []
    if "--no-fetch" not in sys.argv:
        print("\n" + "-" * 78)
        print("PART 1 - THE FETCH")
        print("-" * 78)
        report = backfill()

        print("\n" + "-" * 78)
        print("PART 1 SUMMARY - WHAT THE TAPE LOOKS LIKE NOW")
        print("-" * 78)
        print(f"  {'symbol':9s} {'tf':4s} {'was (days)':>11s} "
              f"{'now (days)':>11s} {'gained':>8s} {'bars now':>11s} "
              f"{'cover%':>7s} {'gaps':>8s}  status")
        for r in report:
            st = "written" if r["written"] else f"KEPT ({r['reason']})"
            cov = f"{r['integ']['coverage']:.1f}" if r["integ"] else "-"
            gp = f"{r['integ']['gaps']:,}" if r["integ"] else "-"
            print(f"  {r['sym']:9s} {r['tf']:4s} {r['old']['days']:>11.0f} "
                  f"{r['new']['days']:>11.0f} "
                  f"{r['new']['days'] - r['old']['days']:>+8.0f} "
                  f"{r['new']['bars']:>11,} {cov:>7s} {gp:>8s}  {st}")

    print("\n" + "-" * 78)
    print("PART 2 - RE-RUN step489_next_look_screen.py UNCHANGED")
    print("-" * 78)
    print("  Executed as a subprocess, byte for byte as it stands on disk.")
    print("  Its own fences (simulate() never called, first 80% only) hold "
          "unmodified.\n", flush=True)
    src = os.path.join(REPO, "step489_next_look_screen.py")
    before = os.path.getmtime(src)
    p = subprocess.run([sys.executable, src], cwd=REPO, text=True,
                       capture_output=True)
    after = os.path.getmtime(src)
    sys.stdout.write(p.stdout)
    if p.stderr.strip():
        sys.stderr.write(p.stderr[-4000:])
    print(f"\n  [screen exited {p.returncode}; step489 mtime unchanged: "
          f"{before == after}]")

    print("\n" + "-" * 78)
    print("PART 3 - stop/vol ON THE TWO INSTRUMENTS THE SCREEN'S PROBE LIST "
          "CANNOT SEE")
    print("-" * 78)
    print("  step489's part (b) iterates a hard-coded seven-name list written "
          "when AVAX and DOGE")
    print("  held three days of tape. Editing it would break fence 4, so its "
          "OWN structural_stops")
    print("  and daily_vol are imported and called unchanged, on the same "
          "first-80% boundary its")
    print("  own cut80 computes. NO OUTCOME IS READ - simulate() is not "
          "called. The ratio is")
    print("  RE-DERIVED here because the standing rule (R89/R100/R170/R190) "
          "forbids porting it,")
    print("  and R489's gold row is the reason that rule exists.\n")
    import numpy as np
    import step489_next_look_screen as S
    paths = {sym: pth for sym, pth, _, _ in S.UNIVERSE}
    print(f"  {'instrument':<11}{'entries':>9}{'days':>7}{'stopmed%':>10}"
          f"{'vol%med':>9}{'stop/vol':>10}{'p25':>8}{'p75':>8}")
    for sym in ("AVAXUSD", "DOGEUSD", "PAXGUSD", "DOTUSD"):
        f = S.tape(paths[sym])
        t80, _, _ = S.cut80(f)
        e = S.structural_stops(sym, t80)
        if len(e) < 50:
            print(f"  {sym:<11}{len(e):>9}  too few entries to read a ratio")
            continue
        dv = S.daily_vol(f[f["t"] < t80], gap_clean=True)
        e["vol"] = dv.reindex(e["day"]).to_numpy()
        e = e[np.isfinite(e["vol"]) & (e["vol"] > 0)]
        pr = (e["stop_pct"] / e["vol"]).replace(
            [np.inf, -np.inf], float("nan")).dropna()
        print(f"  {sym:<11}{len(e):>9}{e['day'].nunique():>7}"
              f"{e['stop_pct'].median():>10.4f}{e['vol'].median():>9.4f}"
              f"{pr.median():>10.2f}{pr.quantile(.25):>8.2f}"
              f"{pr.quantile(.75):>8.2f}")
    print("\n  PAXGUSD and DOTUSD are printed as CONTROLS: they appear in "
          "step489's own table")
    print("  above, so these two rows must reproduce it exactly. If they do, "
          "the two rows that")
    print("  do NOT appear there were computed by the same machinery.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
