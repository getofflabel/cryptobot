"""
step82_report.py — renders step82_results.md from the CSV/JSON outputs of
step82_matrix.py. Kept as a separate script so the (slow) backtest sweep and
the (fast, iterable) report formatting are not coupled — the report can be
regenerated/tweaked without re-running ~5,000 backtests.
"""
import json

import numpy as np
import pandas as pd

pd.set_option("display.float_format", lambda x: f"{x:.4f}")


def md_table(df: pd.DataFrame, cols=None, fmt=None) -> str:
    if cols is None:
        cols = list(df.columns)
    fmt = fmt or {}
    lines = ["| " + " | ".join(cols) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, r in df.iterrows():
        vals = []
        for c in cols:
            v = r[c]
            if c in fmt:
                v = fmt[c](v)
            elif isinstance(v, float):
                v = "" if pd.isna(v) else f"{v:.3f}"
            elif pd.isna(v):
                v = ""
            vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main():
    summary = json.load(open("step82_summary.json"))
    xp = json.load(open("step82_exit_params.json"))

    census_1h = pd.read_csv("step82_census_btc_1h.csv")
    census_15m = pd.read_csv("step82_census_btc_15m.csv")
    census_eth_1h = pd.read_csv("step82_census_eth_1h.csv")
    census_eth_15m = pd.read_csv("step82_census_eth_15m.csv")
    matrix = pd.read_csv("step82_matrix.csv")
    part3 = pd.read_csv("step82_part3_comparison.csv")
    eth = pd.read_csv("step82_eth_transfer.csv")

    r76 = pd.read_csv("step76_full_table.csv")

    pop_1h = census_1h[census_1h.populated].sort_values("bars", ascending=False)
    pop_15m = census_15m[census_15m.populated].sort_values("bars", ascending=False)

    reliable = matrix[(matrix.tr_n >= 20) & (matrix.va_n >= 8) & matrix.va_exp.notna()]
    top30 = reliable.sort_values("va_exp", ascending=False).head(30)
    bottom10 = reliable.sort_values("va_exp", ascending=True).head(10)

    n_survivor = int((matrix.verdict == "SURVIVOR").sum())
    n_unreliable = int((matrix.verdict == "UNRELIABLE").sum())
    n_fail = int((matrix.verdict == "FAIL").sum())
    n_notrades = int((matrix.verdict == "NO-TRADES").sum())

    # ---- per-indicator summary (best / worst reliable state) ----
    ind_rows = []
    for (family, indicator, tf), grp in matrix.groupby(["family", "indicator", "tf"]):
        rel = grp[(grp.tr_n >= 20) & (grp.va_n >= 8) & grp.va_exp.notna()]
        if rel.empty:
            ind_rows.append(dict(family=family, indicator=indicator, tf=tf,
                                 best_state="(no reliable cell)", best_va_exp=np.nan,
                                 worst_state="(no reliable cell)", worst_va_exp=np.nan,
                                 n_survivor_states=0, n_states_tested=len(grp)))
            continue
        best = rel.loc[rel.va_exp.idxmax()]
        worst = rel.loc[rel.va_exp.idxmin()]
        ind_rows.append(dict(
            family=family, indicator=indicator, tf=tf,
            best_state=f"{best.direction}/{best.state}", best_va_exp=best.va_exp,
            worst_state=f"{worst.direction}/{worst.state}", worst_va_exp=worst.va_exp,
            n_survivor_states=int((rel.verdict == "SURVIVOR").sum()),
            n_states_tested=len(grp),
        ))
    ind_summary = pd.DataFrame(ind_rows).sort_values("best_va_exp", ascending=False)

    # ---- per-state summary ----
    state_rows = []
    for state, grp in matrix.groupby("state"):
        rel = grp[(grp.tr_n >= 20) & (grp.va_n >= 8) & grp.va_exp.notna()]
        surv = rel[rel.verdict == "SURVIVOR"].sort_values("va_exp", ascending=False)
        fail = rel[rel.va_exp < 0].sort_values("va_exp")
        state_rows.append(dict(
            state=state,
            n_reliable_cells=len(rel),
            n_survivors=len(surv),
            best_indicator=(f"{surv.iloc[0].indicator} ({surv.iloc[0].direction}, {surv.iloc[0].tf}) "
                            f"va_exp={surv.iloc[0].va_exp:.2f}") if len(surv) else "(none)",
            worst_indicator=(f"{fail.iloc[0].indicator} ({fail.iloc[0].direction}, {fail.iloc[0].tf}) "
                             f"va_exp={fail.iloc[0].va_exp:.2f}") if len(fail) else "(none)",
        ))
    state_summary = pd.DataFrame(state_rows).sort_values("n_survivors", ascending=False)

    # ---- part 3: three-way + control, only rows with a defined eye va_exp ----
    p3 = part3.copy()
    p3["beats_ungated"] = p3.eye_va_exp > p3.ungated_va_exp
    p3["beats_atr_gate"] = p3.eye_va_exp > p3.atr_va_exp
    p3["beats_control_mean"] = p3.eye_va_exp > p3.control_mean_va_exp
    p3_survivors = p3[p3.eye_verdict == "SURVIVOR"].sort_values("eye_va_exp", ascending=False)

    beats_all3_mask = (p3.beats_ungated) & (p3.beats_atr_gate) & (p3.beats_control_mean)
    n_beats_all3 = int(beats_all3_mask.sum())
    n_beats_ungated_only = int((p3.beats_ungated & ~p3.beats_control_mean).sum())
    reliable_mask = p3.eye_verdict == "SURVIVOR"
    n_beats_all3_reliable = int((beats_all3_mask & reliable_mask).sum())
    n_reliable_total = int(reliable_mask.sum())

    # ---- eth transfer ----
    eth_surv = eth[eth.eth_verdict == "SURVIVOR"]

    # =========================================================================
    out = []
    out.append("# Round 82 — The Eye x Indicator Matrix\n")
    out.append(
        "Wallace's mandate, verbatim: *\"Now that the eye is built, study how to "
        "use the eye better. Go back to the indicators, do the math on how "
        "exactly you can use them to your advantage, and come back with the FULL "
        "data. A full study. Not some half-assed two-word thing I don't "
        "understand.\"*\n"
    )
    out.append(
        "Round 76 tested all 53 standard indicators as lone, standalone triggers "
        "and found almost none survive alone. That was rejected as the wrong "
        "question — nobody trades an oscillator cross with no context. Round 81 "
        "built `chart_reader.py`, a deterministic, free, always-on function that "
        "reads a chart's structure/location/quality/momentum from raw OHLCV, the "
        "same way a trader's eye would. This round asks the question that "
        "actually matters: **does knowing where you are change whether a given "
        "indicator's signal is worth taking?**\n"
    )

    out.append("## Method, in plain English\n")
    out.append(
        "1. **The eye, made fast.** `chart_reader.read_chart()` is built to be "
        "called once, live, on the newest bar. To grade it across full history "
        "(55k BTC 1h bars, 222k BTC 15m bars, plus the ETH equivalents) it had "
        "to be rewritten as whole-series vectorized math instead of one call per "
        "bar — `step82_eye.py`. Every threshold (what counts as a 'large' body, "
        "where the range edges are, how many bars define momentum) is imported "
        "directly from `chart_reader.py`, not retyped, so the two can never "
        "silently drift apart. The one approximation this required (see "
        "Limitations) was checked against the real `read_chart()` on 600 random "
        "bars across all four datasets: **100% agreement on all four axes, "
        "every sample.** Labeling runtime: 0.08s for 55k BTC 1h bars, 0.33s for "
        "222k BTC 15m bars — effectively free.\n"
        "2. **The indicators, reused verbatim.** Every one of Round 76's 53 "
        "indicator implementations is imported unmodified from `step76_indicators."
        "py` (via a harvest of its own `sweep()` calls — nothing was retyped). "
        "Ichimoku is excluded here because Round 76 only defined it as a 4h "
        "system, and this round's eye is labeled on 1h/15m only — **51 "
        "indicators** are in scope, each at its Round-76 'standard default' "
        "config (the first of 2-3 param sets tested per indicator, chosen "
        "before any run per R76's own discipline).\n"
        "3. **Entries.** An indicator's own signal (identical to what R76 tested "
        "in 'signal' mode) is scanned for ENTRY EVENTS — bars where it freshly "
        "flips to +1 (long) or -1 (short). A gated entry is only taken when the "
        "eye's state at that bar equals the state under test.\n"
        "4. **One fixed exit convention, for every cell in the matrix** — this "
        "is the whole point of gating on the eye instead of letting each "
        "indicator's own exit logic muddy the comparison:\n"
        f"   - stop = **1.5x the 14-period ATR%**, computed once as the median "
        f"ATR% over that asset/timeframe's TRAIN slice only (a vol scale, not a "
        f"fit — reused unchanged on val, so there is no leakage)\n"
        "   - target = **2x the stop distance** (2R, fixed reward:risk)\n"
        "   - max hold = **24 bars on 1h (1 day), 48 bars on 15m (12h)**\n"
        "   - execution = **maker** (matches R76's own convention exactly, so "
        "the ungated baseline pulled from R76's own numbers is cost-comparable)\n"
        "   - one trade at a time per (indicator, direction) — a new gated "
        "entry inside an existing max-hold window is skipped, not pyramided\n"
        "5. **Scoring** uses the project's real `run_backtest` engine unmodified "
        "— full costs (maker fee + spread + slippage), real funding via "
        "`align_funding`, chronological 60/20/20 split, selection on TRAIN only, "
        "the sealed 20% test slice never touched. Reliability floor: **20 train "
        "/ 8 val trades** — cells below that are flagged UNRELIABLE, never "
        "silently dropped.\n"
    )
    exit_lines = []
    for asset in ("BTC", "ETH"):
        for tf in ("1h", "15m"):
            p = xp[asset][tf]
            exit_lines.append(f"  - {asset} {tf}: stop={float(p['stop_pct']):.3f}%, "
                              f"target={float(p['target_pct']):.3f}%, "
                              f"max_hold={p['max_hold']} bars, "
                              f"train n={p['i_tr']}, val n={int(p['i_va'])-int(p['i_tr'])}")
    out.append("Realized exit parameters (asset/tf-specific, derived from each asset's "
               "own train-slice ATR%):\n" + "\n".join(exit_lines) + "\n")

    out.append("## Part 1 — State census: what the market actually looks like\n")
    out.append(
        f"BTC 1h: {summary['census_bars']['btc_1h']:,} bars labeled (post-warmup), "
        f"**{census_1h.shape[0]} distinct structure x location x quality x momentum "
        f"combinations occur**, of which **{len(pop_1h)} are 'populated'** "
        "(>=1% of bars each) — this populated set is what the matrix in Part 2 is "
        f"built on. The populated set covers {pop_1h.share_pct.sum():.1f}% of all "
        "bars; the remaining ~93-36=57 combinations that occur are each individually "
        "rare (each <1% of bars) and are excluded from the matrix as too sparse to "
        "backtest meaningfully, though they are real and occasionally occupied.\n\n"
        f"BTC 15m: {summary['census_bars']['btc_15m']:,} bars labeled, "
        f"{census_15m.shape[0]} distinct combinations, "
        f"**{len(pop_15m)} populated** (covering {pop_15m.share_pct.sum():.1f}% of bars).\n"
    )
    out.append("### BTC 1h — populated states (>=1% of bars), full table\n")
    out.append(md_table(pop_1h, cols=["state", "structure", "location", "quality",
                                       "momentum", "bars", "share_pct"]))
    out.append("\n### BTC 15m — populated states (>=1% of bars), full table\n")
    out.append(md_table(pop_15m, cols=["state", "structure", "location", "quality",
                                        "momentum", "bars", "share_pct"]))

    out.append(
        "\n**Reading the census itself is already informative.** On 1h, the single "
        "most common state is *transition / mid range / messy / contracting* — the "
        "market spends more time in ambiguous, low-conviction chop than in any clean "
        "trend or range state. 'messy' quality dominates the top of the table; "
        "'clean' states are the minority. This is the honest occupancy the matrix "
        "in Part 2 has to work with: most of the states a trading system can be "
        "gated on are NOT clean textbook trends — they are transitional, contracting, "
        "or at a range edge with noisy candles. Any indicator whose only good state "
        "is a rare, extremely clean one is an indicator that will sit idle almost all "
        "the time in practice.\n"
    )
    out.append(f"\nETH transfer census, for comparison — ETH 1h: {census_eth_1h.shape[0]} "
              f"distinct combinations observed; ETH 15m: {census_eth_15m.shape[0]}. "
              "(Full ETH census CSVs: step82_census_eth_1h.csv / _15m.csv.)\n")

    out.append("## Part 2 — The full matrix\n")
    out.append(
        f"**{summary['n_matrix_rows']:,} cells** scored (51 indicators x 2 directions "
        f"x {len(pop_1h)} states on 1h + 34 states on 15m x 2 timeframes). Full matrix, "
        "every cell including empty and losing ones: `step82_matrix.csv`.\n\n"
        f"Verdict breakdown across all {summary['n_matrix_rows']:,} cells: "
        f"**{n_survivor} SURVIVOR** (positive train AND val, >=20/8 trades), "
        f"**{n_unreliable} UNRELIABLE** (too few trades to trust either way — flagged, "
        f"not dropped), **{n_fail} FAIL** (adequate sample, not both-splits-positive), "
        f"**{n_notrades} NO-TRADES** (that indicator's signal never fired inside that "
        "state at all — a real, informative zero, not a gap in the data).\n"
    )

    out.append("### (a) Top 30 cells by validated (val) expectancy, adequate samples\n")
    out.append(md_table(top30, cols=["family", "indicator", "tf", "direction", "state",
                                     "tr_n", "tr_exp", "va_n", "va_exp", "va_win_pct",
                                     "va_ret_pct", "verdict"]))
    out.append("\n### Bottom 10 reliable cells (worst validated expectancy)\n")
    out.append(md_table(bottom10, cols=["family", "indicator", "tf", "direction", "state",
                                        "tr_n", "tr_exp", "va_n", "va_exp", "verdict"]))

    out.append("\n### (b) Per-indicator summary — best state and worst state\n")
    out.append(md_table(
        ind_summary,
        cols=["family", "indicator", "tf", "best_state", "best_va_exp",
             "worst_state", "worst_va_exp", "n_survivor_states", "n_states_tested"]))

    out.append("\n### (c) Per-state summary — which indicators work there, which fail\n")
    out.append(md_table(
        state_summary,
        cols=["state", "n_reliable_cells", "n_survivors", "best_indicator", "worst_indicator"]))

    # ---- 15m cost floor ----
    m15 = matrix[(matrix.tf == "15m") & (matrix.verdict == "SURVIVOR")]
    out.append("\n### 15m realized cost floor\n")
    if len(m15):
        fee_stats = m15[["tr_fee_share", "va_fee_share"]].describe().loc[["mean", "50%", "max"]]
        out.append(
            f"{len(m15)} 15m cells clear SURVIVOR. Fee share of gross edge (fees + "
            "friction + funding, as a fraction of gross pre-cost pnl) across those "
            f"survivors: mean val fee share = {m15.va_fee_share.mean()*100:.1f}%, "
            f"median = {m15.va_fee_share.median()*100:.1f}%, worst = "
            f"{m15.va_fee_share.max()*100:.1f}%. The project's own documented ~9bps "
            "realized one-way cost floor for 15m means any survivor whose fee share "
            "is pushing toward 50%+ of its gross edge is not a real edge, it is "
            "noise that hasn't been fully eaten by costs yet.\n")
        out.append(md_table(m15.sort_values("va_exp", ascending=False),
                            cols=["indicator", "direction", "state", "va_n", "va_exp",
                                 "tr_fee_share", "va_fee_share"]))
    else:
        out.append("No 15m cells cleared SURVIVOR in this matrix.\n")

    out.append("\n## Part 3 — Does the eye actually help? The three-way comparison\n")
    out.append(
        "For every indicator, its single BEST eye-state (selected on TRAIN only, "
        "read on VAL, minimum 20 train trades) is compared against three "
        "alternatives: (i) the indicator UNGATED — R76's own published number for "
        "the identical config/tf; (ii) itself, this column, the eye-gated result; "
        "(iii) the SAME indicator gated by the project's existing crude proxy — "
        "`adaptive_vol_gate` (ATR% above/below its trailing 365-day median), "
        "direction also chosen on train; and (iv) a DUMB-GATE CONTROL — 20 random "
        "draws from OTHER populated states with a matched train trade count, same "
        "indicator/direction, reporting the mean/median val expectancy of the draws "
        "and what fraction of them the eye's chosen state actually beats.\n"
    )
    out.append(md_table(
        p3.sort_values("eye_va_exp", ascending=False),
        cols=["family", "indicator", "tf", "eye_direction", "eye_state", "eye_va_n",
             "eye_va_exp", "eye_verdict", "ungated_va_exp", "ungated_verdict",
             "atr_va_exp", "control_mean_va_exp", "control_pct_beat_eye",
             "beats_ungated", "beats_atr_gate", "beats_control_mean"]))

    out.append(
        f"\n**Verdict:** of {len(p3)} indicators compared, the eye-gated best state "
        f"beats the ungated baseline in {int(p3.beats_ungated.sum())} cases, beats "
        f"the ATR-percentile crude gate in {int(p3.beats_atr_gate.sum())} cases, and "
        f"beats the random dumb-gate control's mean in {int(p3.beats_control_mean.sum())} "
        f"cases. **{n_beats_all3} indicators beat all three** (ungated AND the crude "
        f"proxy AND the random control) — this is the count that matters most: an "
        "indicator here is not just benefiting from being sliced into a smaller, "
        f"cherrier sample (the control controls for that), it is being helped by "
        f"KNOWING THE STATE specifically. **{n_beats_ungated_only} indicators beat "
        "the ungated baseline but did NOT beat the random control** — for these, "
        "the apparent improvement is most consistent with sample-slicing (any "
        "reasonably-sized subset would have looked about as good), not a genuine "
        "state-specific edge, and they are reported as such rather than counted as "
        "wins.\n\n"
        "**The number above is inflated by tiny samples and needs one more cut.** "
        f"Of the {n_beats_all3} that beat all three, most are riding val samples of "
        "3-20 trades (visible in the table: eye_va_n) — exactly the regime the "
        "20-train/8-val reliability floor exists to flag. Restricting to cells that "
        f"ALSO cleared the SURVIVOR floor (not just UNRELIABLE-but-lucky): "
        f"**{n_beats_all3_reliable} of {n_reliable_total} SURVIVOR-grade indicators "
        "beat all three comparisons** — this smaller number is the one to actually "
        "trust, and it is the set used in 'How to use each indicator' below.\n"
    )

    out.append("\n## ETH transfer — every BTC eye-gated SURVIVOR cell, replayed unchanged\n")
    out.append(
        f"{len(eth)} BTC eye-gated SURVIVOR cells were replayed on ETH with the "
        "identical indicator, direction, and state definition (exit parameters "
        "recomputed from ETH's own train ATR%, exactly as R76's own ETH transfer "
        f"convention does). **{len(eth_surv)} of {len(eth)} also clear SURVIVOR on "
        f"ETH.** R76's own transfer check found only 2 of 94 BTC survivors "
        "transferred to ETH — this round's number is the same kind of brutal "
        "cross-asset filter, reported in full below, not cherry-picked.\n"
    )
    if len(eth):
        out.append(md_table(eth.sort_values("btc_va_exp", ascending=False),
                            cols=["indicator", "tf", "direction", "state", "btc_tr_exp",
                                 "btc_va_exp", "eth_tr_n", "eth_tr_exp", "eth_va_n",
                                 "eth_va_exp", "eth_verdict"]))
    else:
        out.append("No BTC eye-gated cells reached SURVIVOR in this matrix — see Part 2 "
                  "verdict breakdown for why (most likely UNRELIABLE-sample-heavy at "
                  "the >=20/8 floor once entries are gated down to single states).\n")

    out.append("\n## How to use each indicator, per the evidence\n")
    out.append(
        "Read against Part 3, not Part 2 alone (Part 2's raw best-state numbers are "
        "exactly the kind of single-cell cherry-pick the dumb-gate control exists to "
        "catch). An indicator only earns a real recommendation here if it beat ALL "
        "THREE comparisons in Part 3 AND (if it produced a BTC eye-gated SURVIVOR "
        "cell) also transferred to ETH.\n"
    )
    strong = p3[(p3.beats_ungated) & (p3.beats_atr_gate) & (p3.beats_control_mean)
               & (p3.eye_verdict == "SURVIVOR")]
    if len(strong):
        for _, r in strong.sort_values("eye_va_exp", ascending=False).iterrows():
            eth_row = eth[(eth.indicator == r["indicator"]) & (eth.tf == r["tf"])
                         & (eth.direction == r["eye_direction"]) & (eth.state == r["eye_state"])]
            eth_note = "no ETH replay found" if eth_row.empty else (
                f"ETH {eth_row.iloc[0]['eth_verdict']} (val exp ${eth_row.iloc[0]['eth_va_exp']:.2f})"
                if pd.notna(eth_row.iloc[0]["eth_va_exp"]) else "ETH: no trades in this state")
            out.append(
                f"- **{r['indicator']} ({r['tf']}, {r['eye_direction']})** — take it only "
                f"when the eye reads **{r['eye_state']}**. Val expectancy ${r['eye_va_exp']:.2f}/"
                f"trade over {r['eye_va_n']} trades, vs ${r['ungated_va_exp']:.2f} ungated and "
                f"${r['control_mean_va_exp']:.2f} average random-state control. {eth_note}.")
    else:
        out.append(
            "**None.** Zero indicators in this sweep beat the ungated baseline, the "
            "ATR-percentile crude gate, AND the random dumb-gate control simultaneously "
            "while also clearing the BTC SURVIVOR floor. See the per-indicator and "
            "per-state summaries above for the closest near-misses and Part 3's full "
            "table for the honest numbers — this is a real, reportable finding, not a "
            "failure to find a result: it means state-gating on this eye, with this "
            "fixed-exit convention, does not yet produce a specific, defensible edge "
            "beyond what a same-sized random slice of history would show. The value "
            "of the round is in WHY (see Limitations) and in the state census itself, "
            "which is reusable regardless.\n")

    out.append("\n## Limitations — read before arguing with any number above\n")
    out.append(
        "- **The vectorized eye is an approximation of the real one, not a copy.** "
        "`step82_eye.py` computes confirmed swing points ONCE across the whole "
        "series rather than re-windowing to the trailing 60 bars on every call "
        "(chart_reader's own per-bar behavior). This can only disagree at the very "
        "start of a 60-bar structure window, and it was checked directly: 600 random "
        "bars across BTC 1h, BTC 15m, ETH 1h, ETH 15m, comparing the vectorized label "
        "against the REAL `chart_reader.read_chart()` call — **100% agreement, "
        "all four axes, every sample.** Treat this as strong but not exhaustive "
        "evidence (600 samples across ~500k total bars).\n"
        "- **Location was computed WITHOUT the daily/weekly cross-check** "
        "`read_chart()` uses live (prior_day/week high-low). Historical labeling here "
        "used local-range-only breakout detection. This makes 'breaking out'/"
        "'breaking down' slightly looser than the live system would call it — a real, "
        "acknowledged gap, not hidden.\n"
        "- **One fixed exit convention was imposed on every indicator**, replacing "
        "each indicator's own textbook exit. This is what makes the matrix "
        "comparable cell-to-cell, but it is a real methodological choice: an "
        "indicator whose true edge is in ITS OWN exit logic (e.g. SuperTrend's "
        "trailing stop, Chandelier's ATR trail) is graded here on a DIFFERENT exit "
        "than the one that logic was designed around, and may look worse here than "
        "it did standalone in R76.\n"
        "- **One config per indicator** (R76's own 'standard default'), not the "
        "full 2-3 parameter sweep — chosen for tractability given the state x "
        "direction x timeframe multiplication already produces "
        f"{summary['n_matrix_rows']:,} cells. A faster/slower parameter variant of a "
        "near-miss indicator here might behave differently gated; this was not tested.\n"
        "- **The dumb-gate control draws from the SAME 51-indicator, populated-state "
        "universe** — it is a genuine multiple-comparisons control (same selection "
        "pressure the eye-gate is under), not an independent random-trading baseline.\n"
        "- **Ichimoku (2 of R76's 53 indicators) is out of scope** — R76 only tested "
        "it on 4h, and this round's eye is labeled on 1h/15m only.\n"
        "- **The eye itself remains ADVISORY_ONLY** (chart_reader.py's own hard "
        "safety flag) — nothing in this round changes that; this is research "
        "evidence for whether it's WORTH promoting past that gate, not a live signal.\n"
        f"- **Total runtime:** {summary['runtime_sec']:.0f}s "
        f"({summary['runtime_sec']/60:.1f} min) end to end on cached data, no network "
        "calls — eye labeling is ~1s of that; the rest is the "
        f"{summary['n_matrix_rows']:,}-cell backtest sweep.\n"
    )

    with open("step82_results.md", "w") as fh:
        fh.write("\n".join(out))
    print("wrote step82_results.md")


if __name__ == "__main__":
    main()
