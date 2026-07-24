"""
step49_ai_classifier.py — round 49: does an AI (Claude) classifier beat the
crude KEYWORD classifier behind round 45B's news-momentum strategy — the
program's ONE proven, sealed-test-passing edge (see RESEARCH_LOG.md,
"ROUND 45B — NEWS-EVENT day trades — FIRST SEALED-TEST SURVIVOR")?

Research only. Touches ONLY:
  - step49_ai_classifier.py          (this file)
  - data_watcherguru_ai_tags.parquet (AI tags, joined to message_id)
  - step49_results.md                (written by hand from this script's output)
No live orders, no commits, no other repo file read-only-imported (step45b_
news_events.py, step43_daytrade.py, step7_deep_search.py, step11_round6.py,
backtest.py are IMPORTED, never edited).

THREE PHASES
  1. AI TAGGING — every post in data_watcherguru_history.parquet is sent to
     `claude -p ... --model sonnet` in BATCHES (not one call per headline).
     The model judges ONLY from the headline text, "as if reading it live,"
     and returns relevant(bool) / direction(BULLISH|BEARISH|NEUTRAL) /
     magnitude(HIGH|MED|LOW) per headline. Parsed defensively; a batch that
     fails to parse is retried once, then marked UNPARSED and skipped (never
     crashes the run). Results are checkpointed to
     data_watcherguru_ai_tags.parquet incrementally, so a crash/timeout never
     loses progress and a re-run only re-attempts unparsed/missing posts.

  2. AGREEMENT — keyword classifier (step45b.classify_headline, imported
     verbatim, never re-implemented) vs AI tags: relevance agreement %,
     direction agreement on the overlap, tag-count breakdowns, and 10
     concrete disagreement examples printed verbatim.

  3. SAME GAUNTLET, THREE WAYS — reusing step45b's exact machinery
     (align_events, event_study, run_family, day_trade_signal, score,
     verdict_for — all IMPORTED, not reimplemented) on the SAME chronological
     60/20/20 split of the SAME BTC 1h/15m candle frames:
       A. keyword-relevant events   (round 45B baseline — reproduction check)
       B. AI-relevant events        (all AI-tagged relevant=True)
       C. AI-relevant AND magnitude HIGH/MED  ("AI thinks this actually
          matters" filter)
     For each: the A-news-momentum family, FIRST-BAR-MOVE direction (the
     shape that actually passed the sealed test in 45B), the EXACT validated
     geometry (stop 1.2% / target 2.4% / hold 24h) plus step45b's own small
     stop/target/hold grid (STOP_OPTS x TARGET_MULT x MAX_HOLD_H, imported).
     Also the event study per variant (ratio vs baseline) to see whether AI
     filtering concentrates the energy on fewer, higher-quality events.

  HINDSIGHT-RISK CHECK — the AI tags are computed TODAY on headlines dated
  2025-06 -> 2026-07; Claude's training data may "remember" what famous
  headlines preceded. To quantify suspicion, the event-study ratio-vs-
  baseline is computed SEPARATELY on the TRAIN slice (older, more likely
  inside any model's training distribution) and the VAL slice (newer, right
  up against Sonnet's stated Jan-2026 knowledge cutoff) for each classifier.
  If the AI's edge over keyword is much bigger on TRAIN than VAL, that is
  evidence of hindsight leakage; if it holds up (or is bigger) on VAL, that
  is reassuring — a model can't "remember" news it postdates.

GAUNTLET DISCIPLINE (identical to step45b): chronological 60/20/20 of the
news-span-sliced candle frames; >=30 train / >=8 val trades required for a
SURVIVOR verdict; the final 20% (test) slice is NEVER touched, computed, or
looked at anywhere in this script — that sealed look belongs to the lead
agent, not this research round.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

import numpy as np
import pandas as pd

# --- make the `claude` CLI (installed under the owner's npm-global prefix)
# reachable from this subprocess environment, exactly as instructed. ---
_NPM_BIN = os.path.expanduser("~/.npm-global/bin")
if _NPM_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _NPM_BIN + os.pathsep + os.environ.get("PATH", "")

from backtest import CostModel
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from step43_daytrade import (HARD_STOP_CAP, MIN_TRAIN_TRADES, MIN_VAL_TRADES,
                             day_trade_signal, hours_to_bars, mk_row, score,
                             split_points, verdict_for)
from step45b_news_events import (MAX_HOLD_H, STOP_OPTS, TARGET_MULT,
                                 align_events, classify_frame, event_study,
                                 make_bool_array, run_family)

HISTORY_PATH = "data_watcherguru_history.parquet"
AI_TAGS_PATH = "data_watcherguru_ai_tags.parquet"
RESULTS_PATH = "step49_results.md"

CLI_MODEL = "sonnet"
CLI_MAX_TURNS = 3          # empirically: 1 truncates mid-batch; 3 completes cleanly
CLI_TIMEOUT_S = 240
BATCH_SIZE = 90             # ~40 calls for ~3500 posts — batched, not per-headline
DISALLOWED_TOOLS = ("Bash Read Write Edit Glob Grep WebSearch WebFetch "
                    "Task NotebookEdit")
CHECKPOINT_EVERY = 3        # batches between incremental parquet saves
MAX_RETRIES_PER_BATCH = 2   # 1 try + 1 retry, per the mandate

VALID_DIRECTIONS = {"BULLISH", "BEARISH", "NEUTRAL"}
MAGNITUDE_MAP = {"HIGH": "HIGH", "MED": "MED", "MEDIUM": "MED", "LOW": "LOW"}


# ===========================================================================
# PHASE 1 — AI TAGGING
# ===========================================================================

PROMPT_HEADER = (
    "You are a financial-news classifier feeding a Bitcoin trading research "
    "study. For each numbered headline below, judge ONLY from the headline "
    "text itself, as if you were reading it live the moment it was posted, "
    "with NO knowledge of what happened in markets afterward. Do not use "
    "hindsight about how BTC actually moved after similar real headlines — "
    "score purely on what a live reader could infer from the words.\n\n"
    "For each headline decide: would this plausibly move BTC price within "
    "a few hours?\n\n"
    "Return STRICT JSON ONLY: a single JSON array with exactly one object "
    "per headline number, in this exact shape, no markdown fences, no "
    "commentary before or after:\n"
    '[{"id": 1, "relevant": true, "direction": "BULLISH", "magnitude": "HIGH"}, ...]\n\n'
    "Field rules:\n"
    '- "id": the headline number as given below (integer)\n'
    '- "relevant": true/false — would this plausibly move BTC within hours\n'
    '- "direction": one of "BULLISH", "BEARISH", "NEUTRAL" for BTC specifically\n'
    '- "magnitude": one of "HIGH", "MED", "LOW" — how large a plausible BTC '
    'reaction, regardless of relevance (use "LOW" for irrelevant headlines)\n\n'
    "Headlines:\n"
)


def _clean_text(t):
    t = (t or "").replace("\n", " ").replace("\r", " ").strip()
    if not t:
        return "(no text - media-only post)"
    return t[:600]


def build_prompt(batch_df):
    lines = [f"{i}. {_clean_text(row.text)}"
             for i, row in enumerate(batch_df.itertuples(index=False), start=1)]
    return PROMPT_HEADER + "\n".join(lines)


def _extract_json_array(raw):
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON array bracket pair found in output")
    chunk = raw[start:end + 1]
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        # one light repair pass: strip trailing commas before ] or }
        repaired = re.sub(r",\s*([\]}])", r"\1", chunk)
        return json.loads(repaired)


def call_claude_batch(batch_df):
    """One CLI call classifying an entire batch. Returns (list_of_dicts,
    raw_stdout). Raises on any failure (timeout, non-JSON, empty)."""
    prompt = build_prompt(batch_df)
    proc = subprocess.run(
        ["claude", "-p", prompt, "--model", CLI_MODEL,
         "--max-turns", str(CLI_MAX_TURNS),
         "--disallowedTools", DISALLOWED_TOOLS],
        capture_output=True, text=True, timeout=CLI_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
    )
    raw = proc.stdout.strip()
    if not raw:
        raise ValueError(f"empty stdout; rc={proc.returncode} "
                         f"stderr={proc.stderr.strip()[:200]}")
    arr = _extract_json_array(raw)
    if not isinstance(arr, list) or len(arr) == 0:
        raise ValueError("parsed JSON is not a non-empty array")
    return arr, raw


def _normalize_item(o):
    relevant = bool(o.get("relevant", False))
    direction = str(o.get("direction", "NEUTRAL")).strip().upper()
    if direction not in VALID_DIRECTIONS:
        direction = "NEUTRAL"
    magnitude = str(o.get("magnitude", "LOW")).strip().upper()
    magnitude = MAGNITUDE_MAP.get(magnitude, "LOW")
    return relevant, direction, magnitude


def classify_all_ai(news, batch_size=BATCH_SIZE, tags_path=AI_TAGS_PATH):
    """Tags every message_id in `news` that isn't ALREADY successfully
    tagged in the on-disk checkpoint. Resumable: re-running the script only
    re-attempts posts missing or previously UNPARSED."""
    existing = {}
    if os.path.exists(tags_path):
        prev = pd.read_parquet(tags_path)
        for r in prev.itertuples(index=False):
            existing[int(r.message_id)] = {
                "message_id": int(r.message_id),
                "ai_relevant": r.ai_relevant, "ai_direction": r.ai_direction,
                "ai_magnitude": r.ai_magnitude, "ai_unparsed": bool(r.ai_unparsed),
            }
        n_done = sum(1 for v in existing.values() if not v["ai_unparsed"])
        print(f"  resuming from checkpoint: {len(existing)} rows cached, "
              f"{n_done} already successfully parsed.")

    todo_ids = [int(mid) for mid in news["message_id"]
                if int(mid) not in existing or existing[int(mid)]["ai_unparsed"]]
    todo = news[news["message_id"].isin(todo_ids)].sort_values(
        "message_id").reset_index(drop=True)
    print(f"  {len(todo)} posts need AI classification "
          f"(of {len(news)} total).")

    n_calls = 0
    n_batches = 0
    unparsed_batch_ranges = []
    n_batch_total = (len(todo) + batch_size - 1) // batch_size or 0

    for start in range(0, len(todo), batch_size):
        batch = todo.iloc[start:start + batch_size]
        n_batches += 1
        batch_ok = False
        last_err = None
        for attempt in range(MAX_RETRIES_PER_BATCH):
            t0 = time.time()
            try:
                arr, raw = call_claude_batch(batch)
                n_calls += 1
                dt = time.time() - t0
                by_id = {}
                for o in arr:
                    try:
                        by_id[int(o["id"])] = o
                    except (KeyError, TypeError, ValueError):
                        continue
                coverage = len(by_id) / len(batch)
                if coverage < 0.5:
                    raise ValueError(f"only {len(by_id)}/{len(batch)} "
                                     f"ids parsed (coverage {coverage:.0%})")
                for i, row in enumerate(batch.itertuples(index=False), start=1):
                    o = by_id.get(i)
                    if o is None:
                        existing[int(row.message_id)] = {
                            "message_id": int(row.message_id),
                            "ai_relevant": None, "ai_direction": None,
                            "ai_magnitude": None, "ai_unparsed": True,
                        }
                        continue
                    relevant, direction, magnitude = _normalize_item(o)
                    existing[int(row.message_id)] = {
                        "message_id": int(row.message_id),
                        "ai_relevant": relevant, "ai_direction": direction,
                        "ai_magnitude": magnitude, "ai_unparsed": False,
                    }
                batch_ok = True
                print(f"  batch {n_batches}/{n_batch_total}: "
                      f"{len(batch)} headlines, {coverage:.0%} coverage, "
                      f"{dt:.0f}s (call #{n_calls})")
                break
            except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as e:
                n_calls += 1
                last_err = e
                print(f"  batch {n_batches}/{n_batch_total} attempt "
                      f"{attempt + 1}/{MAX_RETRIES_PER_BATCH} FAILED: "
                      f"{str(e)[:150]}")
                time.sleep(3)
        if not batch_ok:
            print(f"  batch {n_batches}/{n_batch_total}: giving up after "
                  f"{MAX_RETRIES_PER_BATCH} attempts — marking UNPARSED "
                  f"({len(batch)} posts). last error: {str(last_err)[:150]}")
            for row in batch.itertuples(index=False):
                existing[int(row.message_id)] = {
                    "message_id": int(row.message_id),
                    "ai_relevant": None, "ai_direction": None,
                    "ai_magnitude": None, "ai_unparsed": True,
                }
            unparsed_batch_ranges.append((start, start + len(batch)))

        if n_batches % CHECKPOINT_EVERY == 0:
            _save_ai_tags(existing, tags_path)
            print(f"    [checkpoint saved: {len(existing)} rows]")

    tags_df = _save_ai_tags(existing, tags_path)
    return tags_df, n_calls, unparsed_batch_ranges


def _save_ai_tags(rows_dict, path):
    df = (pd.DataFrame(list(rows_dict.values()))
          .sort_values("message_id").reset_index(drop=True))
    df.to_parquet(path)
    return df


# ===========================================================================
# PHASE 2 — AGREEMENT ANALYSIS
# ===========================================================================

def agreement_analysis(news_kw, tags_df):
    """news_kw: full history + keyword `relevant`/`tag`. tags_df: AI tags.
    Returns (summary_dict, disagreement_examples_df)."""
    m = news_kw.merge(tags_df, on="message_id", how="left")
    parsed = m[~m["ai_unparsed"].fillna(True)].copy()

    relevance_agree = (parsed["relevant"] == parsed["ai_relevant"]).mean()

    both_relevant = parsed[parsed["relevant"] & parsed["ai_relevant"].fillna(False)]
    # only compare direction on headlines the KEYWORD classifier itself
    # tagged with a directional call (BULLISH/BEARISH) — MIXED/NEUTRAL carry
    # no keyword-side directional claim to agree or disagree with.
    kw_directional = both_relevant[both_relevant["tag"].isin(["BULLISH", "BEARISH"])]
    direction_agree = ((kw_directional["tag"] == kw_directional["ai_direction"])
                       .mean() if len(kw_directional) else float("nan"))

    summary = {
        "n_total": len(m),
        "n_parsed": len(parsed),
        "n_unparsed": len(m) - len(parsed),
        "kw_relevant_n": int(m["relevant"].sum()),
        "ai_relevant_n": int(parsed["ai_relevant"].sum()),
        "relevance_agreement_pct": relevance_agree * 100,
        "both_relevant_n": len(both_relevant),
        "kw_directional_overlap_n": len(kw_directional),
        "direction_agreement_pct": (direction_agree * 100
                                    if not np.isnan(direction_agree) else float("nan")),
        "ai_magnitude_counts": parsed["ai_magnitude"].value_counts().to_dict(),
        "ai_direction_counts": parsed["ai_direction"].value_counts().to_dict(),
        "kw_tag_counts": m["tag"].value_counts().to_dict(),
    }

    # disagreement examples: relevance flips (both directions), sampled
    # across the span for variety rather than clustered at one end.
    kw_yes_ai_no = parsed[parsed["relevant"] & ~parsed["ai_relevant"].fillna(False)]
    kw_no_ai_yes = parsed[~parsed["relevant"] & parsed["ai_relevant"].fillna(False)]
    dir_flip = kw_directional[kw_directional["tag"] != kw_directional["ai_direction"]]

    def _sample(df, n):
        if len(df) <= n:
            return df
        idx = np.linspace(0, len(df) - 1, n).astype(int)
        return df.iloc[idx]

    examples = pd.concat([
        _sample(kw_yes_ai_no, 4).assign(disagreement="keyword=RELEVANT, AI=NOT"),
        _sample(kw_no_ai_yes, 3).assign(disagreement="keyword=NOT, AI=RELEVANT"),
        _sample(dir_flip, 3).assign(disagreement="direction flip"),
    ], ignore_index=True)[
        ["disagreement", "utc_timestamp", "text", "relevant", "tag",
         "ai_relevant", "ai_direction", "ai_magnitude"]
    ]
    return summary, examples, m


# ===========================================================================
# PHASE 3 — SAME GAUNTLET, THREE WAYS
# ===========================================================================

def build_momentum_grid(frames, funding, relevant_ts, variant_label):
    """A-news-momentum family, FIRST-BAR-MOVE direction ONLY (the shape that
    passed the 45B sealed test) — step45b's own small stop/target/hold grid,
    on the SAME chronological 60/20/20 split, for a given set of relevant-
    event timestamps. `run_family`/`align_events`/`day_trade_signal`/`score`/
    `verdict_for` are IMPORTED from step45b_news_events / step43_daytrade,
    never reimplemented."""
    rows = []
    for tf in ("15m", "1h"):
        d, f = frames[tf], funding[tf]
        n, i_tr, i_va = split_points(d)
        d, f = d.iloc[:n].reset_index(drop=True), f.iloc[:n].reset_index(drop=True)
        floor_rel, trad_rel, valid_rel = align_events(d, relevant_ts)
        trad_rel = trad_rel[valid_rel]
        trad_rel = trad_rel[trad_rel < len(d)]
        opens, closes = d["open"].to_numpy(), d["close"].to_numpy()
        move_sign = np.sign(closes[trad_rel] - opens[trad_rel])
        up_idx = trad_rel[move_sign > 0]
        down_idx = trad_rel[move_sign < 0]
        run_family(rows, "A-news-momentum", tf, d, f, i_tr, i_va,
                  long_idx=up_idx, short_idx=down_idx,
                  n_events_note=f"{variant_label} first_bar_move "
                                f"n_up={len(up_idx)} n_down={len(down_idx)}")
    return pd.DataFrame(rows)


def event_study_by_split(frames, relevant_ts, horizons_bars):
    """Event study computed SEPARATELY on the train slice and val slice of
    each timeframe (test never touched) — the hindsight-risk probe: does the
    classifier's edge over baseline look bigger on the OLDER (train, inside
    any LLM's plausible training distribution) slice than the NEWER (val,
    right up against the stated knowledge cutoff) slice?"""
    out = []
    for tf in ("15m", "1h"):
        d = frames[tf]
        n, i_tr, i_va = split_points(d)
        d = d.iloc[:n].reset_index(drop=True)
        floor_idx, trading_idx, valid = align_events(d, relevant_ts)
        for split_name, lo, hi in (("train", 0, i_tr), ("val", i_tr, i_va)):
            in_split = (trading_idx >= lo) & (trading_idx < hi)
            mask = valid & in_split
            d_slice = d.iloc[lo:hi].reset_index(drop=True)
            trading_idx_slice = trading_idx - lo
            tag_masks = {"RELEVANT": np.ones(mask.sum(), dtype=bool)}
            # event_study expects trading_idx/valid indexed into `d_slice`
            study = event_study(d_slice, trading_idx_slice[mask],
                                pd.Series(np.ones(mask.sum(), dtype=bool)),
                                tag_masks, horizons_bars[tf])
            study.insert(0, "split", split_name)
            study.insert(0, "tf", tf)
            out.append(study)
    return pd.concat(out, ignore_index=True)


# ===========================================================================
# main
# ===========================================================================

def main():
    print("=" * 78)
    print("ROUND 49 — AI (Claude) classifier vs KEYWORD classifier, "
          "same gauntlet")
    print("=" * 78)

    print("\nLoading harvested WatcherGuru history...")
    news_raw = pd.read_parquet(HISTORY_PATH)
    news_raw = news_raw.sort_values("message_id").reset_index(drop=True)
    print(f"  {len(news_raw)} posts, "
          f"{news_raw['utc_timestamp'].min():%Y-%m-%d} -> "
          f"{news_raw['utc_timestamp'].max():%Y-%m-%d}")

    print("\n" + "=" * 78)
    print("PHASE 1 — AI TAGGING (claude -p, batched CLI calls)")
    print("=" * 78)
    t0 = time.time()
    tags_df, n_calls, unparsed_ranges = classify_all_ai(news_raw)
    dt_total = time.time() - t0
    n_unparsed = int(tags_df["ai_unparsed"].sum())
    print(f"\nAI tagging complete: {len(tags_df)} rows tagged, "
          f"{n_unparsed} UNPARSED, {n_calls} total CLI calls, "
          f"{dt_total / 60:.1f} min wall time.")

    print("\n" + "=" * 78)
    print("PHASE 1b — KEYWORD CLASSIFICATION (reused verbatim from step45b)")
    print("=" * 78)
    news_kw = classify_frame(news_raw)
    print(f"keyword relevant: {news_kw['relevant'].sum()} "
          f"({news_kw['relevant'].mean() * 100:.1f}%)")

    print("\n" + "=" * 78)
    print("PHASE 2 — AGREEMENT ANALYSIS")
    print("=" * 78)
    summary, examples, merged = agreement_analysis(news_kw, tags_df)
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print("\nDisagreement examples:")
    for _, r in examples.iterrows():
        print(f"  [{r['disagreement']}] {r['utc_timestamp']} :: "
              f"kw=(relevant={r['relevant']}, tag={r['tag']}) "
              f"ai=(relevant={r['ai_relevant']}, dir={r['ai_direction']}, "
              f"mag={r['ai_magnitude']})\n    {r['text'][:180]}")

    print("\n" + "=" * 78)
    print("COST FLOOR (reused verbatim from step45b)")
    print("=" * 78)
    cm = CostModel()
    print(f"  taker round trip (worst case): {cm.round_trip_bps():.1f} bps")
    print(f"  maker round trip (best case): {2 * cm.maker_fee_bps:.1f} bps")
    print("  prior-round REALIZED blended maker/chase cost: ~9 bps round trip")

    print("\n" + "=" * 78)
    print("PHASE 3 — SAME GAUNTLET, THREE WAYS")
    print("=" * 78)
    print("Loading cached BTC candles (no network calls)...")
    frames_full = {tf: fetch_bybit_deep(tf, "BTCUSDT") for tf in ("15m", "1h")}
    funding_hist = fetch_funding_history("BTCUSDT")

    news_min = news_raw["utc_timestamp"].min()
    news_max = news_raw["utc_timestamp"].max()
    print(f"News sample span: {news_min:%Y-%m-%d} -> {news_max:%Y-%m-%d} "
          f"({(news_max - news_min).days} days)")

    frames, funding = {}, {}
    for tf in ("15m", "1h"):
        dfull = frames_full[tf]
        mask = (dfull["timestamp"] >= news_min - pd.Timedelta(hours=24)) & \
               (dfull["timestamp"] <= news_max + pd.Timedelta(hours=24))
        d = dfull[mask].reset_index(drop=True)
        fu = align_funding(d, funding_hist)
        frames[tf], funding[tf] = d, fu
        n, i_tr, i_va = split_points(d)
        print(f"  {tf}: {n} bars sliced to news span "
              f"({d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d}) | "
              f"train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")

    # --- the three relevant-event sets ---
    kw_relevant = news_kw[news_kw["relevant"]]
    ai_parsed = merged[~merged["ai_unparsed"].fillna(True)]
    ai_relevant = ai_parsed[ai_parsed["ai_relevant"].fillna(False)]
    ai_relevant_high = ai_relevant[ai_relevant["ai_magnitude"].isin(["HIGH", "MED"])]

    print(f"\nEvent-set sizes: keyword-relevant={len(kw_relevant)}, "
          f"AI-relevant(all)={len(ai_relevant)}, "
          f"AI-relevant & HIGH/MED={len(ai_relevant_high)}")

    horizons_bars = {"15m": {"1h": 4, "4h": 16}, "1h": {"1h": 1, "4h": 4}}

    print("\n--- EVENT STUDY (whole news span, per variant) ---")
    tag_masks_full = {
        "ALL_RELEVANT": np.ones(0, dtype=bool),  # placeholder, filled per-variant below
    }
    variant_sets = {
        "A_keyword": kw_relevant["utc_timestamp"],
        "B_ai_all": ai_relevant["utc_timestamp"],
        "C_ai_high_med": ai_relevant_high["utc_timestamp"],
    }
    event_study_rows = []
    for label, ts in variant_sets.items():
        for tf in ("15m", "1h"):
            d = frames[tf]
            floor_idx, trading_idx, valid = align_events(d, ts)
            mask_all = np.ones(int(valid.sum()), dtype=bool)
            study = event_study(d, trading_idx[valid], pd.Series(mask_all),
                                {"RELEVANT": mask_all}, horizons_bars[tf])
            study.insert(0, "tf", tf)
            study.insert(0, "variant", label)
            event_study_rows.append(study)
    event_study_df = pd.concat(event_study_rows, ignore_index=True)
    print(event_study_df.to_string(index=False,
                                   float_format=lambda x: f"{x:,.4f}"))

    print("\n--- HINDSIGHT-RISK PROBE: event-study ratio, TRAIN vs VAL ---")
    hindsight_rows = []
    for label, ts in variant_sets.items():
        study = event_study_by_split(frames, ts, horizons_bars)
        study.insert(0, "variant", label)
        hindsight_rows.append(study)
    hindsight_df = pd.concat(hindsight_rows, ignore_index=True)
    print(hindsight_df.to_string(index=False,
                                 float_format=lambda x: f"{x:,.4f}"))

    print("\n--- STRATEGY GRID: A-news-momentum, FIRST-BAR-MOVE, three ways ---")
    grid_results = {}
    for label, ts in variant_sets.items():
        print(f"\n  variant: {label} (n_events={len(ts)})")
        df_grid = build_momentum_grid(frames, funding, ts, label)
        grid_results[label] = df_grid
        print(df_grid[["family", "config", "tf", "tr_n", "tr_exp", "va_n",
                       "va_exp", "verdict"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    all_grid = pd.concat(
        [df.assign(variant=label) for label, df in grid_results.items()],
        ignore_index=True)

    survivors = all_grid[all_grid["verdict"] == "SURVIVOR"]
    print(f"\nTotal SURVIVOR configs across all 3 variants: {len(survivors)}")
    if len(survivors):
        print(survivors[["variant", "family", "config", "tf", "tr_n",
                         "tr_exp", "va_n", "va_exp", "med_hold_h"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    # --- reproduction check: the EXACT round-45B config, keyword baseline ---
    print("\n--- REPRODUCTION CHECK: exact 45B config "
          "(A-news-momentum, first_bar_move, 1h, stop1.2/tgt2.4x2.0/hold24h) ---")
    kw_1h = all_grid[(all_grid["variant"] == "A_keyword") &
                     (all_grid["tf"] == "1h") &
                     (all_grid["stop%"] == 1.2) &
                     (all_grid["target%"] == 2.4) &
                     (all_grid["max_hold_h"] == 24)]
    if len(kw_1h):
        row = kw_1h.iloc[0]
        print(f"  reproduced: train n={row['tr_n']} exp={row['tr_exp']:.2f} | "
              f"val n={row['va_n']} exp={row['va_exp']:.2f} | "
              f"verdict={row['verdict']}")
        print("  round-45B logged numbers (RESEARCH_LOG.md): "
              "train +$23.74/t x200, val +$7.11/t x67")
    else:
        print("  WARNING: exact config row not found in grid output.")

    print("\n" + "=" * 78)
    print(f"DONE. CLI calls made this run: {n_calls}. "
          f"UNPARSED posts: {n_unparsed}.")
    print("=" * 78)

    return {
        "news_raw": news_raw, "tags_df": tags_df, "n_calls": n_calls,
        "n_unparsed": n_unparsed, "unparsed_ranges": unparsed_ranges,
        "agreement_summary": summary, "disagreement_examples": examples,
        "event_study_df": event_study_df, "hindsight_df": hindsight_df,
        "all_grid": all_grid, "survivors": survivors,
        "variant_sets": {k: len(v) for k, v in variant_sets.items()},
        "kw_relevant_n": len(kw_relevant), "ai_relevant_n": len(ai_relevant),
        "ai_relevant_high_n": len(ai_relevant_high),
    }


if __name__ == "__main__":
    main()
