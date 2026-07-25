"""
step400b_other_gates.py — ROUND 400, part 2: does the round-352 artifact
actually bite the OTHER gate studies on this desk, and what do the affected
believed results say when re-measured like-for-like?

THE DISTINCTION THIS FILE EXISTS TO SETTLE
Not every gate is wired the same way, and the wiring decides whether the
artifact applies at all.

  SHAPE 1 — the gate lives INSIDE a signal's state machine (strategy.py's
  vol_gated_ma / vol_filtered_ma, and any `entry_mask & condition` fed to
  step43's day_trade_signal). The machine stays flat while the condition is
  false and enters LATER when it becomes true, or a suppressed trigger frees
  the slot for a different trigger downstream. This DELAYS and RESCHEDULES
  trades. Worst case for the artifact. Round 400 part 1 measured 30-57%
  contamination on the live Bitcoin ride this way.

  SHAPE 2 — the gate suppresses a WHOLE excursion of an already-continuous
  indicator signal (step86's volume_gate_entry, aliased in step100 as
  gate_entry). The excursions are fixed by price and indicators alone, and
  backtest.run_backtest blocks re-entry after a stop until the signal itself
  resets to flat. So a suppressed excursion cannot be replaced by a later
  one — the filtered run should be a STRICT SUBSET of the unfiltered run's
  trades.

"Should be" is a claim, not a measurement. This file checks it trade by
trade, on entry timestamps, for the two believed studies that use shape 2:
R100's gold session filter and R86's volume-gated breakout.

Then, for the one of those that is still believed and undeployed — gold's
session filter — it runs the like-for-like partition anyway, because even a
strict subset makes filtered-vs-unfiltered the WRONG comparison: it compares
the passing group against the whole population (which contains it) instead
of against the failing group, and run_backtest compounds equity, so removing
an early loser silently resizes every later position.

DISCIPLINE: train+val only, sealed slices never loaded (both step100 and
step86 cut them in their own loaders). Costs, execution and stops are each
study's own, imported rather than retyped, so this measures the comparison
shape and nothing else.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

N_SHUFFLES = 2_000
SEED = 400


def entry_keys(res) -> list:
    return [pd.Timestamp(t.entry_time) for t in res.trades]


def subset_check(label, base_res, gated_res):
    b, g = set(entry_keys(base_res)), set(entry_keys(gated_res))
    novel = sorted(g - b)
    frac = len(novel) / len(g) if g else 0.0
    print(f"  {label}: unfiltered {len(b)} trades | filtered {len(g)} trades | "
          f"filtered trades the unfiltered run NEVER took: {len(novel)} "
          f"({frac*100:.0f}%)")
    if novel[:3]:
        print(f"      first novel entries: "
              f"{', '.join(f'{t:%Y-%m-%d %H:%M}' for t in novel[:3])}")
    return dict(label=label, unfiltered_n=len(b), filtered_n=len(g),
                novel_n=len(novel), novel_frac_pct=round(frac * 100, 1))


def shuffle_gap(pnls, n_a, draws=N_SHUFFLES, seed=SEED):
    rng = np.random.default_rng(seed)
    pnls = np.asarray(pnls, dtype=float)
    obs = pnls[:n_a].mean() - pnls[n_a:].mean()
    idx = np.arange(len(pnls))
    gaps = np.empty(draws)
    for i in range(draws):
        rng.shuffle(idx)
        p = pnls[idx]
        gaps[i] = p[:n_a].mean() - p[n_a:].mean()
    return float(obs), float((gaps < obs).mean() * 100)


def partition_by(res, cond_fn, name_in, name_out, bar):
    """Split ONE realized trade population by a per-trade label.

    `bar` is the timeframe's bar length. run_backtest fills at the bar AFTER
    the signal bar, so a trade's entry_time is one bar later than the bar the
    gate actually inspects. The label must sit on the SIGNAL bar or the two
    methods are testing conditions an hour apart — which at a 2-hour session
    window is most of the window."""
    def sig_bar(t):
        return pd.Timestamp(t.entry_time) - bar
    a = [t.pnl for t in res.trades if cond_fn(sig_bar(t))]
    b = [t.pnl for t in res.trades if not cond_fn(sig_bar(t))]
    if not a or not b:
        print(f"    one group empty ({name_in} {len(a)} / {name_out} {len(b)})"
              " — no comparison possible")
        return None
    obs, pct = shuffle_gap(a + b, len(a))
    print(f"    {name_in}: {len(a):3d} trades ${np.mean(a):+8,.2f}/trade  |  "
          f"{name_out}: {len(b):3d} trades ${np.mean(b):+8,.2f}/trade  |  "
          f"gap ${obs:+8,.2f}  |  {pct:.1f}th percentile of "
          f"{N_SHUFFLES} label shuffles")
    print(f"      medians: {name_in} ${np.median(a):+8,.2f}  "
          f"{name_out} ${np.median(b):+8,.2f}")
    return dict(in_n=len(a), in_avg=round(float(np.mean(a)), 2),
                out_n=len(b), out_avg=round(float(np.mean(b)), 2),
                gap=round(obs, 2), pctile=round(pct, 1))


# ===========================================================================
# R100 — gold's session filter (SHAPE 2)
# ===========================================================================

def gold_session():
    import step100_gold_port as G
    rows = []
    print("=" * 74)
    print("R100 — gold session filter on the donchian breakout")
    print("=" * 74)
    sessions = {"London(08:00 UTC)": 8.0, "NY(13:30 UTC)": 13.5}
    for asset in ("GLD", "GC=F"):
        d = G.FRAMES[asset]["1h"]
        m = G.META[asset]["1h"]
        i_tr, i_va = m["i_tr"], m["i_va"]
        base = G.donchian_ema_exit(d, 20)
        long_e, short_e = G.fresh_entries(base)
        stop_pct = G.structural_stop_for_signal(d, i_tr, long_e, short_e, k=8,
                                                buffer_pct=0.15, cap=8.0, floor=0.3)
        if stop_pct is None:
            continue
        size_frac = G.size_frac_from_stop(stop_pct)
        b_tr, b_va = G.score(d, base, G.COSTS_BY_ASSET[asset], i_tr, i_va,
                             stop_pct=stop_pct, size_frac=size_frac)
        print(f"\n{asset} 1h donchian20+EMA20exit, UNFILTERED baseline: "
              f"train {len(b_tr.trades)} trades ${b_tr.expectancy:+,.2f}/trade | "
              f"val {len(b_va.trades)} trades ${b_va.expectancy:+,.2f}/trade")

        for sess_name, sess_hour in sessions.items():
            for window_h in (2, 4):
                cond = G.hours_since_session_open(d, sess_hour) < window_h
                gated = G.gate_entry(base, cond)
                g_tr, g_va = G.score(d, gated, G.COSTS_BY_ASSET[asset], i_tr,
                                     i_va, stop_pct=stop_pct, size_frac=size_frac)
                tag = f"{asset} {sess_name}+{window_h}h"
                print(f"\n  --- {tag} ---")
                print(f"  SEPARATE-RUN comparison (the shape R100 used): "
                      f"train ${b_tr.expectancy:+,.2f} -> ${g_tr.expectancy:+,.2f} | "
                      f"val ${b_va.expectancy:+,.2f} -> ${g_va.expectancy:+,.2f}")
                a1 = subset_check(f"{tag} train", b_tr, g_tr)
                a2 = subset_check(f"{tag} val  ", b_va, g_va)
                rows += [dict(study="R100-gold-session", **a1),
                         dict(study="R100-gold-session", **a2)]

        # like-for-like partition of the ONE unfiltered population
        for sess_name, sess_hour in sessions.items():
            for window_h in (2, 4):
                def in_sess(ts, h=sess_hour, w=window_h):
                    return ((ts.hour + ts.minute / 60.0 - h) % 24) < w
                print(f"\n  LIKE-FOR-LIKE partition, {asset} {sess_name}+{window_h}h:")
                for split, res in (("train", b_tr), ("val", b_va)):
                    print(f"   {split}:")
                    r = partition_by(res, in_sess, "in-session", "out-of-session",
                                     pd.Timedelta(hours=1))
                    if r:
                        rows.append(dict(study="R100-gold-session-partition",
                                         label=f"{asset} {sess_name}+{window_h}h {split}",
                                         **r))
    return rows


# ===========================================================================
# R86 — the volume-gated Bollinger breakout (SHAPE 2)
# ===========================================================================

def volume_gate():
    import step86_specified as S
    rows = []
    print("\n" + "=" * 74)
    print("R86 — volume gate on the Bollinger breakout")
    print("=" * 74)
    for asset, symbol in (("BTC", "BTCUSDT"), ("ETH", "ETHUSDT")):
        frames, funding = S.load_frames(symbol)
        meta = S.build_meta(frames)
        tf = "1h"                                   # family C's own timeframe
        d, f, m = frames[tf], funding[tf], meta[tf]
        i_tr, i_va = m["i_tr"], m["i_va"]
        base = S.bollinger_breakout_signal(d)
        vol_avg20 = d["volume"].rolling(20).mean().shift(1)
        b_tr, b_va = S.score(d, base, f, i_tr, i_va, execution="maker")
        print(f"\n{asset} 1h Bollinger 20/2.5 BARE: train {len(b_tr.trades)} "
              f"${b_tr.expectancy:+,.2f}/trade | val {len(b_va.trades)} "
              f"${b_va.expectancy:+,.2f}/trade")
        for vmult in (1.2, 1.5):
            vol_ok = d["volume"] >= vmult * vol_avg20
            gated = S.volume_gate_entry(base, vol_ok)
            g_tr, g_va = S.score(d, gated, f, i_tr, i_va, execution="maker")
            tag = f"{asset} vol>={vmult}x"
            print(f"\n  --- {tag} ---")
            print(f"  SEPARATE-RUN comparison (the shape R86 used): "
                  f"train ${b_tr.expectancy:+,.2f} -> ${g_tr.expectancy:+,.2f} | "
                  f"val ${b_va.expectancy:+,.2f} -> ${g_va.expectancy:+,.2f}")
            a1 = subset_check(f"{tag} train", b_tr, g_tr)
            a2 = subset_check(f"{tag} val  ", b_va, g_va)
            rows += [dict(study="R86-volume-gate", **a1),
                     dict(study="R86-volume-gate", **a2)]
        # like-for-like: split the BARE population by the breakout bar's volume
        for vmult in (1.2, 1.5):
            ok = (d["volume"] >= vmult * vol_avg20)
            ts_ok = set(pd.DatetimeIndex(d.loc[ok.fillna(False), "timestamp"]))

            def passes(ts, s=ts_ok):
                return ts in s
            print(f"\n  LIKE-FOR-LIKE partition, {asset} vol>={vmult}x "
                  "(label = volume on the trade's own entry bar):")
            for split, res in (("train", b_tr), ("val", b_va)):
                print(f"   {split}:")
                r = partition_by(res, passes, "high-volume", "low-volume",
                                 pd.Timedelta(hours=1))
                if r:
                    rows.append(dict(study="R86-volume-gate-partition",
                                     label=f"{asset} vol>={vmult}x {split}", **r))
    return rows


def main():
    rows = []
    try:
        rows += gold_session()
    except Exception as e:
        print(f"gold_session failed: {type(e).__name__}: {e}")
    try:
        rows += volume_gate()
    except Exception as e:
        print(f"volume_gate failed: {type(e).__name__}: {e}")
    if rows:
        pd.DataFrame(rows).to_csv("step400b_table.csv", index=False)
        print("\nwrote step400b_table.csv")


if __name__ == "__main__":
    main()
