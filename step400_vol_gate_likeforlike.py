"""
step400_vol_gate_likeforlike.py — ROUND 400, the audit of the measurement
artifact round 352 found, applied to the ONE live Bitcoin edge.

WHAT ROUND 352 FOUND (step350_results.md, part 3)
The engines in this repo hold ONE position at a time. So when a study measures
a filter by running "with the filter" against "without the filter", removing an
entry does not merely delete that trade — it frees the slot, and a different,
LATER trade gets taken instead. On oil, 16-17% of the filtered run's trades
were trades the unfiltered run never took at all. The two runs are therefore
two different trade populations, and the difference between them is partly the
filter and partly which trades got to exist.

WHY THE LIVE RIDE IS EXPOSED TO EXACTLY THIS
`bitcoin.py`'s rule_vol_gated_trend is a 4h SMA20/100 long-only trend with a
1.5%-of-price minimum-ATR gate (strategy.vol_filtered_ma / vol_gated_ma,
MIN_ATR_PCT = 1.5), stopped by exits.stop_structure_trailing(buffer_pct=1.5,
fallback_pct=8.0). The gate is built INTO the signal's state machine: while the
trend points up but the market is quiet the machine stays FLAT, and it enters
on the first bar the market becomes lively. So the gate does not skip a trade,
it DELAYS it — the gated run's entry for a given trend leg is a bar the ungated
run was never at liberty to take, because the ungated run was already in the
position. That is the worst case for the artifact, not the mildest.

Round 54 measured this gate as FIXED 1.5 (8 trades, +$401.30/t) against
ADAPTIVE 1.0x (11 trades, +$137.19/t) — two separate runs, different trade
counts, the contaminated shape. This file re-measures it like-for-like.

WHAT THIS FILE DOES — three parts, no live file touched, no sealed data loaded.

PART A — quantify the artifact. Run the gated (live) arm and the ungated arm
and count how many of the gated arm's realized trades entered on a bar the
ungated arm never entered on. That is the fraction of the "improvement" that
is a different trade population rather than the same trades filtered.

PART B — the like-for-like PARTITION, the direct analogue of round 352 part 3.
Take ONE trade population (the ungated run: every SMA20/100 long crossover,
same structural trailing stop, same taker costs), label each realized trade by
whether the market was lively (ATR >= 1.5% of price) at its own signal bar, and
compare the two groups. Then shuffle the labels 2,000 times to state what luck
alone produces.

PART C — the MATCHED-PAIR test, which is the sharper question the live rule
actually poses. The gate never removes a trend leg; it changes WHEN the leg is
entered. So enumerate every long leg of the ungated crossover and, on the same
leg, compare entering immediately at the crossover against entering at the
first lively bar (exactly what the gate does). Legs where the market never
became lively are reported separately — those are the only legs the gate truly
skips. Paired by leg, so no slot is ever freed and no trade population differs.

DISCIPLINE
- execution "taker" always; every stop is exits.py chart structure (the live
  ratcheting floor), never a swept percentage. Size = risk dollars / stop
  distance, leverage an output, capped at the desk's 20x ceiling.
- Train+val only. The final 20% of history is truncated inside load() before
  any other code sees it and is never loaded by this file.
- Parts B and C evaluate each trade from the SAME starting equity so a
  per-trade average is not distorted by which arm happened to compound first.
  Stated rather than buried: this makes the per-trade figures here comparable
  ACROSS arms, and slightly different from a sequential run's own figures.
- Honest sample floors: the ride is a deliberately low-frequency edge
  (~6.5 entries/yr). Small groups are reported with their counts attached and
  are not dressed up.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

import exits as E
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, vol_gated_ma
from step150_common import (INITIAL_EQUITY, chance_baseline, mask_to_events,
                            run_edge, split_points, trade_stats)

FAST, SLOW = 20, 100
MIN_ATR_PCT = 1.5          # the live gate, bitcoin.py -> step5_paper_trade.MIN_ATR_PCT
TRAIL_BUFFER_PCT = 1.5     # the live stop's buffer, bitcoin.py TRAIL_BUFFER_PCT
FALLBACK_PCT = 8.0         # backstop only, for a leg with no confirmed swing yet
K = 5                      # pivot lookback, exits.py default
N_SHUFFLES = 2_000
SEED = 400


# ----------------------------------------------------------------- plumbing

def stop_builder(tc):
    return E.stop_structure_trailing(buffer_pct=TRAIL_BUFFER_PCT,
                                     fallback_pct=FALLBACK_PCT)


def make_target_builder(signal_arr):
    def target_builder(stop):
        return E.target_opposite_signal(signal_arr, treat_zero_as_exit=True)
    return target_builder


def rising_edges(sig01: pd.Series) -> pd.Series:
    prev = sig01.shift(1).fillna(0.0)
    return (sig01 == 1) & (prev != 1)


def load():
    """Train+val only. The sealed final 20% is cut here and never returned."""
    d_full = fetch_bybit_deep("4h", "BTCUSDT")
    f_full = align_funding(d_full, fetch_funding_history("BTCUSDT"))
    n, i_tr, i_va = split_points(d_full)
    d = d_full.iloc[:i_va].reset_index(drop=True)
    f = f_full.iloc[:i_va].reset_index(drop=True)
    print(f"4h BTCUSDT: {n} bars total | train->{i_tr} val->{i_va} | "
          f"sealed {n - i_va} bars NEVER LOADED")
    print(f"window kept: {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
          f"{d['timestamp'].iloc[-1]:%Y-%m-%d}")
    return d, f, i_tr, i_va


def legs_of(sig01: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous runs where the long-only signal is 1 -> (first_bar, last_bar)."""
    out, start = [], None
    for i, v in enumerate(sig01):
        if v == 1 and start is None:
            start = i
        elif v != 1 and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(sig01) - 1))
    return out


def one_trade(candles, funding, sig_arr, sig_idx):
    """Evaluate a SINGLE entry from a fixed starting equity, so per-trade
    figures are comparable across arms rather than reflecting compounding."""
    tr, skipped = run_edge(candles, [(sig_idx, 1)], stop_builder,
                           make_target_builder(sig_arr), len(candles),
                           funding_bps=funding, k=K,
                           initial_equity=INITIAL_EQUITY)
    return (tr[0] if tr else None), skipped


def shuffle_gap(pnls: np.ndarray, n_a: int, draws: int, seed: int) -> dict:
    """Percentile of the OBSERVED group gap among `draws` random relabellings
    of the same trades into the same two group sizes. This is what luck alone
    produces."""
    rng = np.random.default_rng(seed)
    obs = pnls[:n_a].mean() - pnls[n_a:].mean()
    gaps = np.empty(draws)
    idx = np.arange(len(pnls))
    for i in range(draws):
        rng.shuffle(idx)
        p = pnls[idx]
        gaps[i] = p[:n_a].mean() - p[n_a:].mean()
    pct = float((gaps < obs).mean() * 100)
    return dict(observed_gap=float(obs), pctile=pct,
                shuffle_mean=float(gaps.mean()), shuffle_sd=float(gaps.std()),
                draws=draws)


# ----------------------------------------------------------------- the round

def main():
    rows = []
    d, f, i_tr, i_va = load()
    atr_pct = (atr(d, 14) / d["close"] * 100).to_numpy()

    gated = vol_gated_ma(d, fast=FAST, slow=SLOW,
                         min_atr_pct=MIN_ATR_PCT).fillna(0.0)
    ungated = vol_gated_ma(d, fast=FAST, slow=SLOW,
                           min_atr_pct=0.0).fillna(0.0)
    print(f"\ntime in market: gated {(gated == 1).mean()*100:.1f}%  |  "
          f"ungated {(ungated == 1).mean()*100:.1f}%")
    print(f"bars passing the 1.5% liveliness gate: "
          f"{np.nanmean(atr_pct >= MIN_ATR_PCT)*100:.1f}%")

    slices = [("train", 0, i_tr), ("val", i_tr, i_va)]

    # CONVENTION, matching step150c/step150f exactly: rising edges and legs are
    # computed ONCE on the whole train+val frame and only THEN split by slice.
    # Computing them on an already-sliced signal manufactures a phantom entry at
    # the val slice's first bar whenever the signal was already on at the
    # boundary — verified against round 150's own published val figure.
    edges = {arm: mask_to_events(rising_edges(sig), 1)
             for arm, sig in (("gated", gated), ("ungated", ungated))}

    def slice_events(arm, lo, hi):
        return [(i - lo, dr) for i, dr in edges[arm] if lo <= i < hi]

    # ---------------------------------------------------------------- PART A
    print("\n" + "=" * 74)
    print("PART A — the artifact: how many of the GATED run's trades never "
          "existed ungated")
    print("=" * 74)
    art = {}
    seq = {}
    for name, lo, hi in slices:
        cnd = d.iloc[lo:hi].reset_index(drop=True)
        fnd = f.iloc[lo:hi].reset_index(drop=True)
        out = {}
        for arm, sig in (("gated", gated), ("ungated", ungated)):
            s_loc = sig.iloc[lo:hi].reset_index(drop=True)
            ents = slice_events(arm, lo, hi)
            trades, skip = run_edge(cnd, ents, stop_builder,
                                    make_target_builder(s_loc.to_numpy()),
                                    len(cnd), funding_bps=fnd, k=K)
            out[arm] = trades
            st = trade_stats(trades)
            seq[(name, arm)] = st
            print(f"  {name:5s} {arm:8s}: {st['n']:3d} trades  "
                  f"avg ${st['expectancy']:+9,.2f}/trade  "
                  f"win {st['win_rate']*100:4.1f}%  skipped(no structure)={skip}")
        g_bars = {t["entry_idx"] for t in out["gated"]}
        u_bars = {t["entry_idx"] for t in out["ungated"]}
        novel = sorted(g_bars - u_bars)
        art[name] = dict(n_gated=len(g_bars), n_ungated=len(u_bars),
                         n_novel=len(novel),
                         frac=len(novel) / len(g_bars) if g_bars else 0.0)
        print(f"  {name:5s} -> {len(novel)} of {len(g_bars)} gated trades "
              f"({art[name]['frac']*100:.0f}%) entered on a bar the ungated "
              f"run never entered on")
        rows.append(dict(part="A", slice=name, gated_trades=len(g_bars),
                         ungated_trades=len(u_bars), novel_trades=len(novel),
                         novel_frac_pct=round(art[name]["frac"] * 100, 1),
                         gated_avg=round(seq[(name, "gated")]["expectancy"], 2),
                         ungated_avg=round(seq[(name, "ungated")]["expectancy"], 2)))

    # ---------------------------------------------------------------- PART B
    print("\n" + "=" * 74)
    print("PART B — like-for-like PARTITION of ONE population (every "
          "crossover, ungated)")
    print("=" * 74)
    pool = []
    for name, lo, hi in slices:
        cnd = d.iloc[lo:hi].reset_index(drop=True)
        fnd = f.iloc[lo:hi].reset_index(drop=True)
        s_loc = ungated.iloc[lo:hi].reset_index(drop=True)
        ents = slice_events("ungated", lo, hi)
        trades, _ = run_edge(cnd, ents, stop_builder,
                             make_target_builder(s_loc.to_numpy()), len(cnd),
                             funding_bps=fnd, k=K)
        for t in trades:
            g_sig = lo + t["entry_idx"] - 1          # the bar the signal fired
            t["slice"] = name
            t["atr_pct_at_signal"] = float(atr_pct[g_sig])
            t["lively"] = bool(atr_pct[g_sig] >= MIN_ATR_PCT)
            pool.append(t)

    for label, subset in (("train", [t for t in pool if t["slice"] == "train"]),
                          ("val", [t for t in pool if t["slice"] == "val"]),
                          ("pooled", pool)):
        liv = [t["pnl"] for t in subset if t["lively"]]
        qui = [t["pnl"] for t in subset if not t["lively"]]
        if not liv or not qui:
            print(f"  {label}: one group empty (lively {len(liv)} / "
                  f"quiet {len(qui)}) — no comparison possible")
            continue
        pn = np.array(liv + qui, dtype=float)
        sh = shuffle_gap(pn, len(liv), N_SHUFFLES, SEED)
        print(f"  {label:6s}: LIVELY {len(liv):3d}t ${np.mean(liv):+9,.2f}/t  |  "
              f"QUIET {len(qui):3d}t ${np.mean(qui):+9,.2f}/t  |  "
              f"gap ${sh['observed_gap']:+9,.2f}  |  "
              f"{sh['pctile']:.1f}th percentile of {N_SHUFFLES} label shuffles")
        # heavy-tail check: trend PnL is dominated by a few enormous rides, so
        # state the median and the average with each group's single biggest
        # winner removed, rather than let one trade carry the verdict.
        tl, tq = sorted(liv)[:-1], sorted(qui)[:-1]
        print(f"          median  LIVELY ${np.median(liv):+9,.2f}  "
              f"QUIET ${np.median(qui):+9,.2f}   |   "
              f"best winner removed: LIVELY ${np.mean(tl):+9,.2f}  "
              f"QUIET ${np.mean(tq):+9,.2f}")
        rows.append(dict(part="B", slice=label, lively_n=len(liv),
                         lively_avg=round(float(np.mean(liv)), 2),
                         quiet_n=len(qui),
                         quiet_avg=round(float(np.mean(qui)), 2),
                         gap=round(sh["observed_gap"], 2),
                         shuffle_pctile=round(sh["pctile"], 1)))

    # ---------------------------------------------------------------- PART C
    print("\n" + "=" * 74)
    print("PART C — MATCHED PAIRS on the same trend legs: enter at the "
          "crossover vs wait for lively")
    print("=" * 74)
    all_legs = legs_of(ungated.to_numpy())        # computed on the whole frame
    pairs, skipped_legs = [], []
    for name, lo, hi in slices:
        cnd = d.iloc[lo:hi].reset_index(drop=True)
        fnd = f.iloc[lo:hi].reset_index(drop=True)
        s_arr = ungated.iloc[lo:hi].reset_index(drop=True).to_numpy()
        for (ga, gb) in all_legs:
            if not (lo <= ga < hi):
                continue                          # leg belongs to the other slice
            a = ga - lo
            b = min(gb, hi - 1) - lo              # a straddling leg is truncated
            if a + 1 >= len(cnd):
                continue
            live_bars = [j for j in range(a, b + 1)
                         if atr_pct[lo + j] >= MIN_ATR_PCT and j + 1 < len(cnd)]
            imm, _ = one_trade(cnd, fnd, s_arr, a)
            if imm is None:
                continue
            if not live_bars:
                skipped_legs.append(dict(slice=name, pnl=imm["pnl"],
                                         leg_bars=b - a + 1))
                continue
            gat, _ = one_trade(cnd, fnd, s_arr, live_bars[0])
            if gat is None:
                continue
            pairs.append(dict(slice=name, leg_start=ga,
                              delay_bars=live_bars[0] - a,
                              immediate=imm["pnl"], gated=gat["pnl"]))

    for label in ("train", "val", "pooled"):
        sub = pairs if label == "pooled" else [p for p in pairs
                                              if p["slice"] == label]
        if not sub:
            continue
        imm = np.array([p["immediate"] for p in sub])
        gat = np.array([p["gated"] for p in sub])
        diff = gat - imm
        rng = np.random.default_rng(SEED)
        # sign-flip test: if waiting carried no information, the per-leg
        # difference is as likely to point either way
        flips = np.array([np.mean(diff * rng.choice([-1.0, 1.0], size=len(diff)))
                          for _ in range(N_SHUFFLES)])
        pct = float((flips < diff.mean()).mean() * 100)
        print(f"  {label:6s}: {len(sub):3d} matched legs  |  "
              f"enter-at-crossover ${imm.mean():+9,.2f}/leg  |  "
              f"wait-for-lively ${gat.mean():+9,.2f}/leg  |  "
              f"gate adds ${diff.mean():+9,.2f}/leg  |  "
              f"{pct:.1f}th percentile of {N_SHUFFLES} sign flips  |  "
              f"gate better on {int((diff > 0).sum())}/{len(diff)} legs")
        print(f"          median per-leg difference ${np.median(diff):+9,.2f}  |  "
              f"median wait before entry "
              f"{np.median([p['delay_bars'] for p in sub]):.0f} bars "
              f"({np.median([p['delay_bars'] for p in sub])*4:.0f} hours)")
        rows.append(dict(part="C", slice=label, matched_legs=len(sub),
                         immediate_avg=round(float(imm.mean()), 2),
                         gated_avg=round(float(gat.mean()), 2),
                         gate_adds=round(float(diff.mean()), 2),
                         signflip_pctile=round(pct, 1),
                         legs_gate_better=int((diff > 0).sum()),
                         median_delay_bars=float(np.median(
                             [p["delay_bars"] for p in sub]))))

    if skipped_legs:
        sk = np.array([s["pnl"] for s in skipped_legs])
        print(f"\n  legs the gate SKIPPED entirely (never became lively): "
              f"{len(sk)}  |  they would have averaged ${sk.mean():+,.2f}/leg "
              f"entered at the crossover")
        rows.append(dict(part="C", slice="legs_gate_skipped_entirely",
                         matched_legs=len(sk),
                         immediate_avg=round(float(sk.mean()), 2)))
    else:
        print("\n  legs the gate SKIPPED entirely: 0")

    # ------------------------------------------------------- chance baseline
    print("\n" + "=" * 74)
    print("FLOOR — what random entry timing earns in the same window, same "
          "exits, same costs")
    print("=" * 74)
    for name, lo, hi in slices:
        cnd = d.iloc[lo:hi].reset_index(drop=True)
        fnd = f.iloc[lo:hi].reset_index(drop=True)
        s_loc = ungated.iloc[lo:hi].reset_index(drop=True)
        n_ev = len(slice_events("gated", lo, hi))
        cb = chance_baseline(cnd, n_ev, 1.0, stop_builder,
                             make_target_builder(s_loc.to_numpy()), len(cnd),
                             fnd, "next_open", k=K, draws=100)
        print(f"  {name:5s}: {cb['n_draws']} draws of {cb['sample_events']} "
              f"random long entries -> ${cb['mean_exp']:+,.2f}/trade")
        rows.append(dict(part="floor", slice=name, draws=cb["n_draws"],
                         random_avg=round(cb["mean_exp"], 2)))

    pd.DataFrame(rows).to_csv("step400_table.csv", index=False)
    pd.DataFrame(pairs).to_csv("step400_matched_pairs.csv", index=False)
    print("\nwrote step400_table.csv, step400_matched_pairs.csv")


if __name__ == "__main__":
    main()
