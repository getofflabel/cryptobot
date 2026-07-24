"""
step82_matrix.py — ROUND 82: THE EYE x INDICATOR MATRIX.

Wallace's mandate (verbatim): "Now that the eye is built, study how to use
the eye better. Go back to the indicators, do the math on how exactly you
can use them to your advantage, and come back with the FULL data."

step76 tested all 53 indicators as LONE, standalone triggers and (correctly,
per the lead's review) concluded almost none survive alone — but that
conclusion answered the wrong question: nobody trades a lone oscillator
cross with no context. This round asks the right one: does knowing WHERE
you are (the eye's structure/location/quality/momentum read, from
step82_eye.py) change whether a given indicator's signal is worth taking?

METHOD, in one paragraph: reuse every step76 indicator computation
VERBATIM (imported, not retyped, via a harvest of step76_indicators.
run_all_btc()'s own sweep() calls). For each indicator's default/textbook
config, detect ENTRY EVENTS (bars where its own signal freshly flips to
+1/-1) — these are identical to what step76 already tested. Gate: only
take an entry if step82_eye's vectorized eye-state at that bar equals the
state under test. Exit on ONE fixed, sensible, uniform convention across
every cell (documented below) instead of each indicator's own state
machine, so every cell in the matrix is graded on the same terms. Score
with the project's real run_backtest (full costs, real funding, chronological
60/20/20, train-only selection) — the same engine, same discipline, as
every other step*.

EXIT CONVENTION (fixed across the whole matrix, chosen before any cell was
scored):
  stop_pct   = 1.5 x (14-period ATR%, median over that asset/tf's TRAIN
               slice only — a vol SCALE, not a fit, computed once and reused
               for both train and val so there is no leakage)
  target_pct = 2 x stop_pct  (2R fixed reward:risk)
  max_hold   = 24 bars on 1h (1 trading day), 48 bars on 15m (12h) — long
               enough for a real move, short enough that state-gating can't
               quietly turn into buy-and-hold.
  execution  = "maker" (matches step76's own convention exactly, so the
               PART 3 (i) ungated baseline — pulled straight from step76's
               own published numbers — is comparable on identical cost terms).
  A new gated entry is ignored while a prior gated entry from the same
  (indicator, direction) is still within its max_hold window — one clean
  trade at a time, no pyramiding, no churn.

RESEARCH ONLY. Writes only step82_* files. Does not touch step79/80/81 or
anything else. No commits, no live orders.
"""

import json
import sys
import time
import warnings
from collections import deque

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

import step76_indicators as R76
import step82_eye as EYE
from backtest import run_backtest, CostModel
from step41_shorts import split_points, adaptive_vol_gate
from strategy import atr as atr_

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:8.1f}s]", *a, flush=True)


# ===========================================================================
# 1. HARVEST — capture step76's own indicator registry, verbatim, without
#    re-running its ~500 backtests. Monkeypatch sweep()/run_and_record() to
#    record (family, indicator, archetype, compute_fn, default params,
#    extra, tf) instead of executing. load_data()/run_all_btc() are step76's
#    OWN functions, untouched — this just intercepts what they call.
# ===========================================================================

CAPTURED = []


def _fake_sweep(family, indicator, archetype, tf_list, param_sets, compute_fn,
                base_sig_1h, fixed_extra=None, filter_it=True):
    entry = param_sets[0]   # first config = step76's own "standard default"
    if archetype == "oscillator":
        label, params, lower, upper, exit_mid = entry
        extra = {"lower": lower, "upper": upper, "exit_mid": exit_mid}
    else:
        label, params = entry
        extra = dict(fixed_extra or {})
    for tf in tf_list:
        if tf not in ("1h", "15m"):
            continue   # this round's eye is labeled on 1h/15m only (Ichimoku is 4h-only in R76 -> excluded)
        CAPTURED.append(dict(family=family, indicator=indicator, archetype=archetype,
                             compute_fn=compute_fn, params=params, extra=extra,
                             tf=tf, label=label))


def harvest():
    R76.sweep = _fake_sweep
    R76.run_and_record = lambda *a, **k: {}
    R76.load_data()
    R76.run_all_btc()
    log(f"harvested {len(CAPTURED)} indicator x tf entries "
       f"({len(set((c['family'], c['indicator']) for c in CAPTURED))} distinct indicators)")
    return R76.FRAMES, R76.FUND


# ===========================================================================
# 2. EYE LABELING + STATE CENSUS
# ===========================================================================

def census(labeled: pd.DataFrame, warmup: int, min_share: float = 0.01):
    sub = labeled.iloc[warmup:]
    n = len(sub)
    vc = sub["state"].value_counts()
    pop = vc[vc / n >= min_share]
    rows = []
    for state, cnt in vc.items():
        structure, location, quality, momentum = state.split("|")
        rows.append(dict(state=state, structure=structure, location=location,
                         quality=quality, momentum=momentum,
                         bars=int(cnt), share_pct=round(cnt / n * 100, 3),
                         populated=bool(state in pop.index)))
    return pd.DataFrame(rows).sort_values("bars", ascending=False).reset_index(drop=True), n


# ===========================================================================
# 3. EXIT CONVENTION PARAMS
# ===========================================================================

MAX_HOLD = {"1h": 24, "15m": 48}
STOP_ATR_MULT = 1.5
TARGET_R_MULT = 2.0


def exit_params(d: pd.DataFrame, i_tr: int, tf: str):
    a_pct = (atr_(d, 14) / d["close"] * 100).iloc[:i_tr]
    med = float(a_pct.median())
    stop_pct = STOP_ATR_MULT * med
    target_pct = TARGET_R_MULT * stop_pct
    return stop_pct, target_pct, MAX_HOLD[tf]


# ===========================================================================
# 4. ENTRY-EVENT EXTRACTION + FIXED-EXIT GATED SIGNAL CONSTRUCTION
# ===========================================================================

def entry_events(sig: pd.Series):
    s = sig.fillna(0).to_numpy()
    prev = np.concatenate([[0.0], s[:-1]])
    entry_long = (s == 1.0) & (prev != 1.0)
    entry_short = (s == -1.0) & (prev != -1.0)
    return entry_long, entry_short


def build_gated_signal(entry_flags: np.ndarray, direction: float, max_hold: int, n: int):
    desired = np.zeros(n)
    pos_until = -1
    for i in np.flatnonzero(entry_flags):
        if i < pos_until:
            continue
        end = min(n, i + max_hold)
        desired[i:end] = direction
        pos_until = end
    return desired


def run_cell(d, f, desired, i_tr, i_va, stop_pct, target_pct, execution="maker"):
    sig = pd.Series(desired, index=d.index)

    def _run(lo, hi):
        return run_backtest(
            d.iloc[lo:hi].reset_index(drop=True),
            sig.iloc[lo:hi].reset_index(drop=True),
            execution=execution,
            funding_series=f.iloc[lo:hi].reset_index(drop=True),
            stop_pct=stop_pct, target_pct=target_pct,
        )
    return _run(0, i_tr), _run(i_tr, i_va)


MIN_TRAIN_TRADES = 20
MIN_VAL_TRADES = 8


def verdict_for(tr_n, tr_exp, va_n, va_exp):
    if tr_exp > 0 and va_exp > 0:
        if tr_n >= MIN_TRAIN_TRADES and va_n >= MIN_VAL_TRADES:
            return "SURVIVOR"
        return "UNRELIABLE"
    if tr_n < MIN_TRAIN_TRADES or va_n < MIN_VAL_TRADES:
        return "UNRELIABLE"
    return "FAIL"


def fee_share(res):
    net = sum(t.pnl for t in res.trades)
    costs = res.total_fees + res.total_friction + res.total_funding
    gross = net + costs
    if gross <= 0:
        return None
    return round(costs / gross, 4)


def row_from_result(tr, va, extra: dict, tf: str):
    row = dict(extra)
    row.update(dict(
        tr_n=len(tr.trades), tr_exp=round(tr.expectancy, 4),
        tr_win_pct=round(tr.win_rate * 100, 2), tr_ret_pct=round(tr.total_return_pct, 2),
        va_n=len(va.trades), va_exp=round(va.expectancy, 4),
        va_win_pct=round(va.win_rate * 100, 2), va_ret_pct=round(va.total_return_pct, 2),
        va_dd_pct=round(va.max_drawdown_pct, 2),
    ))
    row["verdict"] = verdict_for(row["tr_n"], row["tr_exp"], row["va_n"], row["va_exp"])
    if tf == "15m":
        row["tr_fee_share"] = fee_share(tr)
        row["va_fee_share"] = fee_share(va)
    else:
        row["tr_fee_share"] = None
        row["va_fee_share"] = None
    return row


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    FRAMES, FUND = harvest()

    # ---- eye labeling ----
    labeled = {}
    warmup = EYE.WARMUP_BARS
    for asset in ("BTC", "ETH"):
        labeled[asset] = {}
        for tf in ("1h", "15m"):
            labeled[asset][tf] = EYE.label_eye_states(FRAMES[asset][tf])
            log(f"labeled {asset} {tf}: {len(FRAMES[asset][tf])} bars")

    census_btc_1h, n_btc_1h = census(labeled["BTC"]["1h"], warmup)
    census_btc_15m, n_btc_15m = census(labeled["BTC"]["15m"], warmup)
    census_eth_1h, n_eth_1h = census(labeled["ETH"]["1h"], warmup)
    census_eth_15m, n_eth_15m = census(labeled["ETH"]["15m"], warmup)
    census_btc_1h.to_csv("step82_census_btc_1h.csv", index=False)
    census_btc_15m.to_csv("step82_census_btc_15m.csv", index=False)
    census_eth_1h.to_csv("step82_census_eth_1h.csv", index=False)
    census_eth_15m.to_csv("step82_census_eth_15m.csv", index=False)
    log("census written")

    populated_states = {
        "1h": census_btc_1h[census_btc_1h.populated]["state"].tolist(),
        "15m": census_btc_15m[census_btc_15m.populated]["state"].tolist(),
    }
    for tf in ("1h", "15m"):
        log(f"populated states {tf}: {len(populated_states[tf])}")

    # ---- exit params per (asset, tf), from TRAIN slice only ----
    XP = {}
    for asset in ("BTC", "ETH"):
        XP[asset] = {}
        for tf in ("1h", "15m"):
            d = FRAMES[asset][tf]
            n, i_tr, i_va = split_points(d)
            sp, tp, mh = exit_params(d, i_tr, tf)
            XP[asset][tf] = dict(stop_pct=sp, target_pct=tp, max_hold=mh,
                                 i_tr=i_tr, i_va=i_va, n=n)
            log(f"{asset} {tf} exit params: stop={sp:.3f}% target={tp:.3f}% "
               f"max_hold={mh} (train n={i_tr}, val n={i_va - i_tr})")

    with open("step82_exit_params.json", "w") as fh:
        json.dump(XP, fh, indent=2, default=str)

    # ---- PART 2: full matrix on BTC ----
    matrix_rows = []
    n_indicators = len(set((c["family"], c["indicator"]) for c in CAPTURED))
    done_indicators = 0
    seen_indicators = set()

    for cap in CAPTURED:
        family, indicator, tf = cap["family"], cap["indicator"], cap["tf"]
        d, f = FRAMES["BTC"][tf], FUND["BTC"][tf]
        xp = XP["BTC"][tf]
        n_bars = xp["n"]

        sig, gate = R76.construct(cap["archetype"], cap["compute_fn"], cap["params"],
                                  cap["extra"], d)
        entry_long, entry_short = entry_events(sig)
        eye_state = labeled["BTC"][tf]["state"].to_numpy()

        for state in populated_states[tf]:
            state_mask = (eye_state == state)
            for direction, entries in ((1.0, entry_long), (-1.0, entry_short)):
                gated_entries = entries & state_mask
                n_ev = int(gated_entries.sum())
                if n_ev == 0:
                    row = dict(family=family, indicator=indicator, tf=tf,
                              direction="long" if direction == 1 else "short",
                              state=state, tr_n=0, tr_exp=np.nan, tr_win_pct=np.nan,
                              tr_ret_pct=np.nan, va_n=0, va_exp=np.nan, va_win_pct=np.nan,
                              va_ret_pct=np.nan, va_dd_pct=np.nan, verdict="NO-TRADES",
                              tr_fee_share=None, va_fee_share=None)
                    matrix_rows.append(row)
                    continue
                desired = build_gated_signal(gated_entries, direction, xp["max_hold"], n_bars)
                tr, va = run_cell(d, f, desired, xp["i_tr"], xp["i_va"],
                                  xp["stop_pct"], xp["target_pct"])
                extra = dict(family=family, indicator=indicator, tf=tf,
                            direction="long" if direction == 1 else "short", state=state)
                matrix_rows.append(row_from_result(tr, va, extra, tf))

        done_indicators += 1
        key = (family, indicator)
        if key not in seen_indicators:
            seen_indicators.add(key)
        if done_indicators % 10 == 0:
            log(f"...{done_indicators}/{len(CAPTURED)} indicator x tf entries scored "
               f"({len(matrix_rows)} matrix rows so far)")

    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df.to_csv("step82_matrix.csv", index=False)
    log(f"wrote step82_matrix.csv: {len(matrix_df)} rows")

    # ---- PART 3(i): ungated baseline, pulled straight from step76's own numbers ----
    r76 = pd.read_csv("step76_full_table.csv")
    r76_signal_btc = r76[(r76["mode"] == "signal") & (r76["asset"] == "BTC")]

    ungated = {}
    for cap in CAPTURED:
        key = (cap["family"], cap["indicator"], cap["tf"])
        rows = r76_signal_btc[(r76_signal_btc["family"] == cap["family"])
                              & (r76_signal_btc["indicator"] == cap["indicator"])
                              & (r76_signal_btc["tf"] == cap["tf"])
                              & (r76_signal_btc["config"] == cap["label"])]
        if len(rows):
            ungated[key] = rows.iloc[0].to_dict()

    # ---- PART 3(ii): eye-gated best state per indicator (select on TRAIN, read VAL) ----
    part3_rows = []
    rng = np.random.default_rng(82)

    for (family, indicator, tf), grp in matrix_df.groupby(["family", "indicator", "tf"]):
        eligible = grp[(grp["tr_n"] >= MIN_TRAIN_TRADES) & (grp["tr_exp"].notna())]
        if eligible.empty:
            continue
        best = eligible.loc[eligible["tr_exp"].idxmax()]

        base_key = (family, indicator, tf)
        base = ungated.get(base_key, {})

        # ---- (iii) ATR-percentile regime gate, same indicator+direction,
        #      direction of the crude gate ("above"/"below") also selected on TRAIN ----
        d, f = FRAMES["BTC"][tf], FUND["BTC"][tf]
        xp = XP["BTC"][tf]
        cap = next(c for c in CAPTURED if c["family"] == family and c["indicator"] == indicator
                  and c["tf"] == tf)
        sig, gate = R76.construct(cap["archetype"], cap["compute_fn"], cap["params"],
                                  cap["extra"], d)
        entry_long, entry_short = entry_events(sig)
        direction = 1.0 if best["direction"] == "long" else -1.0
        entries = entry_long if direction == 1.0 else entry_short

        atr_best = None
        for gdir in ("above", "below"):
            g, _ = adaptive_vol_gate(d, direction=gdir)
            g_np = g.to_numpy()
            gated_entries = entries & g_np
            n_ev = int(gated_entries.sum())
            if n_ev == 0:
                continue
            desired = build_gated_signal(gated_entries, direction, xp["max_hold"], xp["n"])
            tr, va = run_cell(d, f, desired, xp["i_tr"], xp["i_va"], xp["stop_pct"], xp["target_pct"])
            cand = dict(gate_dir=gdir, tr_n=len(tr.trades), tr_exp=tr.expectancy,
                       va_n=len(va.trades), va_exp=va.expectancy,
                       va_win_pct=va.win_rate * 100, va_ret_pct=va.total_return_pct)
            if atr_best is None or cand["tr_exp"] > atr_best["tr_exp"]:
                atr_best = cand

        # ---- (iv) dumb-gate control: 20 random populated states w/ matched
        #      train trade count (nearest by count among eligible rows,
        #      excluding the eye's own chosen state) ----
        pool = eligible[eligible["state"] != best["state"]].copy()
        control_draws = []
        if len(pool) > 0:
            target_n = best["tr_n"]
            pool["dist"] = (pool["tr_n"] - target_n).abs()
            pool_sorted = pool.sort_values("dist")
            near_pool = pool_sorted.head(max(5, len(pool_sorted) // 2))  # nearest half by count
            draw_idx = rng.choice(len(near_pool), size=min(20, len(near_pool) * 4), replace=True)
            for i in draw_idx:
                r = near_pool.iloc[i % len(near_pool)]
                control_draws.append(dict(state=r["state"], tr_n=r["tr_n"], tr_exp=r["tr_exp"],
                                          va_n=r["va_n"], va_exp=r["va_exp"]))

        ctl_va_exp = [c["va_exp"] for c in control_draws if pd.notna(c["va_exp"])]
        ctl_summary = dict(
            n_draws=len(control_draws),
            mean_va_exp=float(np.mean(ctl_va_exp)) if ctl_va_exp else None,
            median_va_exp=float(np.median(ctl_va_exp)) if ctl_va_exp else None,
            pct_beat_eye=float(np.mean([v > best["va_exp"] for v in ctl_va_exp])) if ctl_va_exp and pd.notna(best["va_exp"]) else None,
            pct_beat_ungated=(float(np.mean([v > base.get("va_exp", -1e18) for v in ctl_va_exp]))
                              if ctl_va_exp and base else None),
        )

        part3_rows.append(dict(
            family=family, indicator=indicator, tf=tf,
            eye_direction=best["direction"], eye_state=best["state"],
            eye_tr_n=best["tr_n"], eye_tr_exp=best["tr_exp"],
            eye_va_n=best["va_n"], eye_va_exp=best["va_exp"],
            eye_va_win_pct=best["va_win_pct"], eye_va_ret_pct=best["va_ret_pct"],
            eye_verdict=best["verdict"],
            ungated_tr_n=base.get("tr_n"), ungated_tr_exp=base.get("tr_exp"),
            ungated_va_n=base.get("va_n"), ungated_va_exp=base.get("va_exp"),
            ungated_verdict=base.get("verdict"),
            atr_gate_dir=atr_best["gate_dir"] if atr_best else None,
            atr_tr_n=atr_best["tr_n"] if atr_best else None,
            atr_tr_exp=atr_best["tr_exp"] if atr_best else None,
            atr_va_n=atr_best["va_n"] if atr_best else None,
            atr_va_exp=atr_best["va_exp"] if atr_best else None,
            control_n_draws=ctl_summary["n_draws"],
            control_mean_va_exp=ctl_summary["mean_va_exp"],
            control_median_va_exp=ctl_summary["median_va_exp"],
            control_pct_beat_eye=ctl_summary["pct_beat_eye"],
            control_pct_beat_ungated=ctl_summary["pct_beat_ungated"],
        ))
        log(f"part3: {family} / {indicator} ({tf}) done")

    part3_df = pd.DataFrame(part3_rows)
    part3_df.to_csv("step82_part3_comparison.csv", index=False)
    log(f"wrote step82_part3_comparison.csv: {len(part3_df)} rows")

    # ---- ETH TRANSFER: every eye-gated cell in the BTC matrix that is a SURVIVOR ----
    survivors = matrix_df[matrix_df["verdict"] == "SURVIVOR"]
    eth_rows = []
    for _, r in survivors.iterrows():
        family, indicator, tf, direction, state = (
            r["family"], r["indicator"], r["tf"], r["direction"], r["state"])
        cap = next((c for c in CAPTURED if c["family"] == family and c["indicator"] == indicator
                   and c["tf"] == tf), None)
        if cap is None or tf not in FRAMES["ETH"]:
            continue
        d, f = FRAMES["ETH"][tf], FUND["ETH"][tf]
        xp = XP["ETH"][tf]
        sig, gate = R76.construct(cap["archetype"], cap["compute_fn"], cap["params"],
                                  cap["extra"], d)
        entry_long, entry_short = entry_events(sig)
        direction_val = 1.0 if direction == "long" else -1.0
        entries = entry_long if direction_val == 1.0 else entry_short
        eth_state = labeled["ETH"][tf]["state"].to_numpy()
        gated_entries = entries & (eth_state == state)
        n_ev = int(gated_entries.sum())
        if n_ev == 0:
            eth_rows.append(dict(family=family, indicator=indicator, tf=tf, direction=direction,
                                 state=state, btc_tr_exp=r["tr_exp"], btc_va_exp=r["va_exp"],
                                 eth_tr_n=0, eth_tr_exp=np.nan, eth_va_n=0, eth_va_exp=np.nan,
                                 eth_verdict="NO-TRADES"))
            continue
        desired = build_gated_signal(gated_entries, direction_val, xp["max_hold"], xp["n"])
        tr, va = run_cell(d, f, desired, xp["i_tr"], xp["i_va"], xp["stop_pct"], xp["target_pct"])
        eth_rows.append(dict(
            family=family, indicator=indicator, tf=tf, direction=direction, state=state,
            btc_tr_exp=r["tr_exp"], btc_va_exp=r["va_exp"],
            eth_tr_n=len(tr.trades), eth_tr_exp=round(tr.expectancy, 4),
            eth_va_n=len(va.trades), eth_va_exp=round(va.expectancy, 4),
            eth_verdict=verdict_for(len(tr.trades), tr.expectancy, len(va.trades), va.expectancy),
        ))
    eth_df = pd.DataFrame(eth_rows)
    eth_df.to_csv("step82_eth_transfer.csv", index=False)
    log(f"wrote step82_eth_transfer.csv: {len(eth_df)} rows "
       f"({len(survivors)} BTC eye-gated survivors identified)")

    summary = dict(
        n_indicators=n_indicators,
        n_captured=len(CAPTURED),
        n_matrix_rows=len(matrix_df),
        n_survivors_eye_gated=int((matrix_df["verdict"] == "SURVIVOR").sum()),
        n_survivors_eth_transfer=int((eth_df["eth_verdict"] == "SURVIVOR").sum()) if len(eth_df) else 0,
        census_bars={"btc_1h": n_btc_1h, "btc_15m": n_btc_15m,
                    "eth_1h": n_eth_1h, "eth_15m": n_eth_15m},
        populated_state_counts={"1h": len(populated_states["1h"]),
                                "15m": len(populated_states["15m"])},
        runtime_sec=round(time.time() - T0, 1),
    )
    with open("step82_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    log("DONE:", json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
