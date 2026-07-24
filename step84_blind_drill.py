"""
step84_blind_drill.py — ROUND 84: THE BLIND CHART DRILL.

Wallace's exact method, mechanized: "Take different screenshots throughout
time and study them. Look at that chart, blur the second half, and ask
yourself: based on this setup, what kind of trade would I place? Then
imagine the trade taking place, and unblur to see if you were right or
wrong."

This module builds the HARNESS only. It does not itself judge a chart —
that's the point. A human (or a vision-capable model looking at the
rendered PNGs with real eyes, one at a time, in the discipline order below)
supplies the call; this file supplies everything around that: picking fair,
stratified historical moments, rendering the before/after images honestly
(no future leakage in the "before" picture), and resolving a structured
call against what candles actually did afterward.

THREE PHASES, run as three separate CLI subcommands so a human reviewer
can never accidentally see an outcome before recording a call:

  generate   picks decision points stratified across market states (via
             step82_eye's vectorized labeler), renders ONLY the "before"
             image for each, computes chart_reader.read_chart() at the
             decision bar (the "computed eye" side of the head-to-head),
             and writes step84_drills.csv with call_* columns blank.

  reveal     for drills that now have a call recorded (call_action is
             non-blank), renders the "after" image (before + horizon bars,
             decision bar marked) and scores the call with score_call().
             Never renders an after-image for a drill without a call yet
             — that ordering IS the causality/discipline guarantee.

  record     small CLI to write one drill's call into the CSV
             (used by the reviewer, one drill at a time, immediately after
             looking at that drill's before-image and BEFORE looking at
             any after-image — including other drills' after-images).

CAUSALITY, verified explicitly (see also the assert in render_before()):
the "before" renderer is only ever handed candles.iloc[:decision_idx+1] —
it has no parameter through which a future bar could reach it, and its
y-axis is computed from nanmin/nanmax of exactly that slice (+ padding).
There is therefore no code path by which the before-image's axis range,
candle pixels, or moving averages could differ depending on what happens
after the decision bar. self_test_causality() below proves this on real
data: it renders the same decision point twice, once with the true future
data available in the cache and once with the DataFrame truncated one bar
past the decision bar, and asserts the two PNGs are byte-identical.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

import numpy as np
import pandas as pd

import chart_reader as CR
import step82_eye as EYE
from step7_deep_search import fetch_bybit_deep

# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

IMG_DIR = Path("step84_drill_images")
CSV_PATH = Path("step84_drills.csv")
LOOKBACK = 120          # bars shown in the "before" image
STRUCTURES = ["uptrend", "downtrend", "range", "chop", "transition"]
QUALITIES = ["clean", "messy"]

SERIES = [   # (label, symbol_for_cache, timeframe, n_target, horizon)
    ("BTC-USDT", "BTCUSDT", "1h", 14, 24),
    ("BTC-USDT", "BTCUSDT", "15m", 13, 48),
    ("ETH-USDT", "ETHUSDT", "1h", 13, 24),
]

FIELDS = [
    "drill_id", "symbol", "tf", "horizon", "decision_idx", "decision_ts",
    "decision_close",
    "structure", "location", "quality", "momentum",
    "eye_structure", "eye_location", "eye_quality", "eye_momentum",
    "eye_tradeable", "eye_best_tool", "eye_one_line", "eye_current_candle",
    "before_png", "after_png",
    "call_action", "call_entry", "call_stop", "call_target", "call_reasoning",
    "outcome", "entered", "fill_offset", "exit_price", "exit_offset", "R", "risk",
]

# ---------------------------------------------------------------------------
# data loading
# ---------------------------------------------------------------------------

def load_series(cache_symbol: str, tf: str) -> pd.DataFrame:
    df = fetch_bybit_deep(tf, cache_symbol)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# rendering — dark theme, candles + MA20/MA50, matches chart_reader's look
# ---------------------------------------------------------------------------

BG_COLOR = "#0b0f14"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#e5e7eb"
UP_COLOR = "#26d07c"
DOWN_COLOR = "#ef4444"
MA20_COLOR = "#60a5fa"
MA50_COLOR = "#f59e0b"
DECISION_COLOR = "#facc15"
REVEAL_COLOR = "#a78bfa"
FIGSIZE = (14.0, 8.0)
DPI = 100


def _pick_x_ticks(n: int, want: int = 8) -> list:
    if n <= want:
        return list(range(n))
    step = max(1, n // want)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


def _draw_candles(ax, df: pd.DataFrame, ma20: pd.Series, ma50: pd.Series,
                   decision_pos: int | None, reveal_start_pos: int | None):
    n = len(df)
    body_w = 0.62
    for i in range(n):
        o = float(df.at[i, "open"]); h = float(df.at[i, "high"])
        l = float(df.at[i, "low"]);  c = float(df.at[i, "close"])
        up = c >= o
        color = UP_COLOR if up else DOWN_COLOR
        ax.add_line(Line2D([i, i], [l, h], color=color, linewidth=1.1,
                            solid_capstyle="round", zorder=2))
        y0, height = (o, c - o) if up else (c, o - c)
        if height <= 0:
            span = h - l
            height = max(span * 0.015, abs(c) * 0.0006, 1e-9)
            y0 = (o + c) / 2 - height / 2
        rect = Rectangle((i - body_w / 2, y0), body_w, height,
                          facecolor=color, edgecolor=color, linewidth=0.0,
                          zorder=3)
        ax.add_patch(rect)

    ax.plot(range(n), ma20.to_numpy(), color=MA20_COLOR, linewidth=1.1,
            label="MA20", zorder=4, alpha=0.9)
    ax.plot(range(n), ma50.to_numpy(), color=MA50_COLOR, linewidth=1.1,
            label="MA50", zorder=4, alpha=0.9)

    if decision_pos is not None:
        ax.axvline(decision_pos, color=DECISION_COLOR, linewidth=1.3,
                    linestyle=(0, (4, 2)), zorder=5)
        ax.text(decision_pos, ax.get_ylim()[1] if ax.get_ylim()[1] else 0,
                " DECISION", color=DECISION_COLOR, fontsize=9,
                fontweight="bold", va="bottom", ha="left", zorder=6)
    if reveal_start_pos is not None:
        ax.axvspan(reveal_start_pos - 0.5, n - 0.5, color=REVEAL_COLOR, alpha=0.06, zorder=1)


def _finish_ax(ax, fig, df: pd.DataFrame, title: str, ymin: float, ymax: float):
    n = len(df)
    pad = (ymax - ymin) * 0.06 if ymax > ymin else max(abs(ymax) * 0.01, 1e-6)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_xlim(-1, n - 1 + 3.2)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)
    tick_idx = _pick_x_ticks(n)
    ax.set_xticks(tick_idx)
    labels = []
    for i in tick_idx:
        ts = df["timestamp"].iloc[i]
        labels.append(ts.strftime("%m-%d %H:%M"))
    ax.set_xticklabels(labels, rotation=25, ha="right", color=TEXT_COLOR, fontsize=8)
    ax.tick_params(axis="y", colors=TEXT_COLOR, labelsize=9)
    ax.set_ylabel("price", color=TEXT_COLOR, fontsize=10)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.set_title(title, color=TEXT_COLOR, fontsize=12, loc="left", pad=10)
    leg = ax.legend(loc="upper left", facecolor=BG_COLOR, edgecolor=GRID_COLOR,
                     labelcolor=TEXT_COLOR, fontsize=8, framealpha=0.6)
    fig.tight_layout()


def render_before(full_df: pd.DataFrame, decision_idx: int, lookback: int,
                   out_path: Path, symbol: str, tf: str) -> Path:
    """Renders ONLY candles.iloc[:decision_idx+1]. No parameter here can
    smuggle a future bar in — `full_df` is sliced to `causal` BEFORE any
    plotting call touches it, and every axis limit is computed from that
    sliced frame alone. This is the causality guarantee, enforced by
    construction rather than by convention."""
    causal = full_df.iloc[: decision_idx + 1].reset_index(drop=True)
    assert causal["timestamp"].iloc[-1] == full_df["timestamp"].iloc[decision_idx]
    assert len(causal) == decision_idx + 1, "before-image must stop exactly at the decision bar"

    ma20_full = full_df["close"].iloc[: decision_idx + 1].rolling(20).mean()
    ma50_full = full_df["close"].iloc[: decision_idx + 1].rolling(50).mean()

    window = causal.tail(lookback).reset_index(drop=True)
    ma20 = ma20_full.tail(lookback).reset_index(drop=True)
    ma50 = ma50_full.tail(lookback).reset_index(drop=True)

    ymin = float(window["low"].min())
    ymax = float(window["high"].max())

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    _draw_candles(ax, window, ma20, ma50, decision_pos=len(window) - 1,
                  reveal_start_pos=None)
    title = f"{symbol} {tf} · BEFORE · decision bar = last candle shown ({window['timestamp'].iloc[-1]:%Y-%m-%d %H:%M} UTC)"
    _finish_ax(ax, fig, window, title, ymin, ymax)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def render_after(full_df: pd.DataFrame, decision_idx: int, lookback: int,
                  horizon: int, out_path: Path, symbol: str, tf: str) -> Path:
    end_idx = decision_idx + horizon
    causal = full_df.iloc[: end_idx + 1].reset_index(drop=True)
    start_idx = max(0, decision_idx - lookback + 1)
    window = causal.iloc[start_idx:].reset_index(drop=True)

    ma20 = causal["close"].rolling(20).mean().iloc[start_idx:].reset_index(drop=True)
    ma50 = causal["close"].rolling(50).mean().iloc[start_idx:].reset_index(drop=True)

    decision_pos = decision_idx - start_idx
    ymin = float(window["low"].min())
    ymax = float(window["high"].max())

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    _draw_candles(ax, window, ma20, ma50, decision_pos=decision_pos,
                  reveal_start_pos=decision_pos + 1)
    title = (f"{symbol} {tf} · AFTER · decision bar marked, "
             f"+{horizon} bars revealed ({window['timestamp'].iloc[-1]:%Y-%m-%d %H:%M} UTC)")
    _finish_ax(ax, fig, window, title, ymin, ymax)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def self_test_causality(cache_symbol: str = "BTCUSDT", tf: str = "1h") -> bool:
    """Proves render_before() cannot leak the future: renders the same
    decision point from the full cached series and from a copy truncated
    one bar past the decision bar, and asserts the resulting PNG bytes are
    IDENTICAL. If they weren't, some future bar would have to be reaching
    the y-axis or the MA lines — this is the explicit verification the
    round brief asked for."""
    df = load_series(cache_symbol, tf)
    decision_idx = len(df) - 200
    a = render_before(df, decision_idx, LOOKBACK, Path("/tmp/_causal_a.png"), "T", tf)
    truncated = df.iloc[: decision_idx + 1].reset_index(drop=True)
    b = render_before(truncated, decision_idx, LOOKBACK, Path("/tmp/_causal_b.png"), "T", tf)
    ok = a.read_bytes() == b.read_bytes()
    os.remove(a); os.remove(b)
    return ok


# ---------------------------------------------------------------------------
# eye read at a historical decision bar
# ---------------------------------------------------------------------------

_FAR_FUTURE = pd.Timestamp("2099-01-01", tz="UTC")


def eye_read_at(full_df: pd.DataFrame, decision_idx: int) -> dict:
    window = full_df.iloc[: decision_idx + 1]
    return CR.read_chart(window, prior_day=None, week=None, now=_FAR_FUTURE)


# ---------------------------------------------------------------------------
# stratified decision-point selection
# ---------------------------------------------------------------------------

def select_decision_points(df: pd.DataFrame, states: pd.DataFrame, n_target: int,
                            horizon: int, lookback: int, seed: int) -> list[int]:
    rng = np.random.default_rng(seed)
    lo = max(lookback - 1, EYE.WARMUP_BARS)
    hi = len(df) - horizon - 1
    if hi <= lo:
        raise ValueError("series too short for the requested horizon/lookback")
    min_gap = max(lookback // 2, horizon)

    chosen: list[int] = []

    def far_enough(idx):
        return all(abs(idx - c) >= min_gap for c in chosen)

    # pass 1: one from each (structure, quality) combo present in range, for coverage
    combos = [(s, q) for s in STRUCTURES for q in QUALITIES]
    rng.shuffle(combos)
    for structure, quality in combos:
        if len(chosen) >= n_target:
            break
        mask = ((states["structure"].iloc[lo:hi] == structure)
                & (states["quality"].iloc[lo:hi] == quality))
        pool = states.iloc[lo:hi][mask].index.to_numpy()
        pool = pool[[far_enough(int(i)) for i in pool]] if len(pool) else pool
        if len(pool):
            chosen.append(int(rng.choice(pool)))

    # pass 2: fill remainder randomly across the whole range, balancing
    # structure counts so no single state dominates the fill
    attempts = 0
    struct_counts = {s: 0 for s in STRUCTURES}
    for c in chosen:
        struct_counts[states["structure"].iloc[c]] += 1
    all_idx = np.arange(lo, hi)
    while len(chosen) < n_target and attempts < 5000:
        attempts += 1
        cand = int(rng.choice(all_idx))
        if not far_enough(cand):
            continue
        s = states["structure"].iloc[cand]
        cap = math.ceil(n_target / len(STRUCTURES)) + 1
        if struct_counts[s] >= cap:
            continue
        chosen.append(cand)
        struct_counts[s] += 1

    # last resort: relax the structure cap if we still came up short
    while len(chosen) < n_target and attempts < 20000:
        attempts += 1
        cand = int(rng.choice(all_idx))
        if far_enough(cand):
            chosen.append(cand)

    chosen.sort()
    return chosen[:n_target]


# ---------------------------------------------------------------------------
# phase: generate
# ---------------------------------------------------------------------------

def generate(out_csv: Path = CSV_PATH, img_dir: Path = IMG_DIR, seed: int = 84) -> list[dict]:
    rows = []
    drill_n = 0
    for label, cache_symbol, tf, n_target, horizon in SERIES:
        df = load_series(cache_symbol, tf)
        states = EYE.label_eye_states(df)
        idxs = select_decision_points(df, states, n_target, horizon, LOOKBACK,
                                       seed=seed + hash((cache_symbol, tf)) % 1000)
        for decision_idx in idxs:
            drill_n += 1
            drill_id = f"d{drill_n:03d}_{cache_symbol}_{tf}"
            before_path = img_dir / f"{drill_id}_before.png"
            render_before(df, decision_idx, LOOKBACK, before_path, label, tf)

            read = eye_read_at(df, decision_idx)
            st = states.iloc[decision_idx]
            row = {
                "drill_id": drill_id, "symbol": label, "tf": tf, "horizon": horizon,
                "decision_idx": decision_idx,
                "decision_ts": df["timestamp"].iloc[decision_idx].isoformat(),
                "decision_close": df["close"].iloc[decision_idx],
                "structure": st["structure"], "location": st["location"],
                "quality": st["quality"], "momentum": st["momentum"],
                "eye_structure": read["structure"], "eye_location": read["location"],
                "eye_quality": read["quality"], "eye_momentum": read["momentum"],
                "eye_tradeable": read["tradeable"], "eye_best_tool": read["best_tool"],
                "eye_one_line": read["one_line"],
                "eye_current_candle": (f"{read['current_candle']['color']}/"
                                        f"{read['current_candle']['body']}/"
                                        f"{read['current_candle']['wicks']}/"
                                        f"{read['current_candle']['close_position']}"),
                "before_png": str(before_path), "after_png": "",
                "call_action": "", "call_entry": "", "call_stop": "",
                "call_target": "", "call_reasoning": "",
                "outcome": "", "entered": "", "fill_offset": "",
                "exit_price": "", "exit_offset": "", "R": "", "risk": "",
            }
            rows.append(row)
            print(f"  {drill_id}  {label} {tf}  {df['timestamp'].iloc[decision_idx]:%Y-%m-%d %H:%M}  "
                  f"state={st['structure']}|{st['location']}|{st['quality']}|{st['momentum']}")

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} drills to {out_csv} (before-images only, no calls, no after-images)")
    return rows


# ---------------------------------------------------------------------------
# phase: record (one call at a time, CLI-driven)
# ---------------------------------------------------------------------------

def record_call(drill_id: str, action: str, entry, stop, target, reasoning: str,
                 csv_path: Path = CSV_PATH):
    assert action in ("long", "short", "no trade")
    rows = list(csv.DictReader(open(csv_path)))
    found = False
    for r in rows:
        if r["drill_id"] == drill_id:
            if r["after_png"]:
                raise RuntimeError(f"{drill_id} already revealed — cannot record/revise a call after reveal")
            r["call_action"] = action
            r["call_entry"] = "" if entry is None else entry
            r["call_stop"] = "" if stop is None else stop
            r["call_target"] = "" if target is None else target
            r["call_reasoning"] = reasoning
            found = True
            break
    if not found:
        raise KeyError(drill_id)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def score_call(call: dict, candles: pd.DataFrame, decision_idx: int, horizon: int) -> dict:
    """Resolves a structured call {action, entry, stop, target} against what
    candles.iloc[decision_idx+1 : decision_idx+horizon+1] actually did.

    Rules:
      - "no trade" -> outcome "flat", R = 0.0, recorded but not entered.
      - entry within 0.05% of the decision bar's close is treated as an
        immediate market fill (at that close); otherwise the call is a
        resting limit/stop order and future bars are scanned in order for
        the first bar that would fill it (long: low<=entry if entry below
        close, high>=entry if above; mirrored for short). If never filled
        within the horizon: outcome "no_fill", R = 0.0.
      - once filled, stop/target are checked starting the bar AFTER the
        fill bar (never the fill bar itself, so entry and exit are never
        resolved from the same intrabar range — a deliberately
        conservative simplification, documented here rather than hidden).
      - if a single bar's range would touch BOTH stop and target, STOP
        WINS (stop-first-on-tie — the conservative assumption whenever
        intrabar sequencing is unknown).
      - no stop/target hit inside the horizon -> "time" exit at the close
        of the final horizon bar.
      - R = (exit_price - entry) / |entry - stop| * direction.
    """
    action = call["action"]
    if action == "no trade":
        return {"outcome": "flat", "entered": False, "fill_offset": None,
                "exit_price": None, "exit_offset": None, "R": 0.0, "risk": None}

    direction = 1 if action == "long" else -1
    entry = float(call["entry"]); stop = float(call["stop"]); target = float(call["target"])
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("stop cannot equal entry")

    decision_close = float(candles["close"].iloc[decision_idx])
    tol = max(abs(decision_close) * 0.0005, 1e-9)

    future = candles.iloc[decision_idx + 1: decision_idx + horizon + 1].reset_index(drop=True)
    if len(future) == 0:
        raise ValueError("no future bars available for this horizon")

    if abs(entry - decision_close) <= tol:
        fill_offset = 0
        scan_start = 0
    else:
        fill_offset = None
        for i in range(len(future)):
            bar = future.iloc[i]
            if direction == 1:
                touched = (bar["low"] <= entry) if entry <= decision_close else (bar["high"] >= entry)
            else:
                touched = (bar["high"] >= entry) if entry >= decision_close else (bar["low"] <= entry)
            if touched:
                fill_offset = i + 1
                break
        if fill_offset is None:
            return {"outcome": "no_fill", "entered": False, "fill_offset": None,
                    "exit_price": None, "exit_offset": None, "R": 0.0, "risk": risk}
        scan_start = fill_offset  # index into `future` (0-based) of the fill bar

    outcome, exit_price, exit_offset = None, None, None
    for i in range(scan_start, len(future)):
        bar = future.iloc[i]
        hit_stop = (bar["low"] <= stop) if direction == 1 else (bar["high"] >= stop)
        hit_target = (bar["high"] >= target) if direction == 1 else (bar["low"] <= target)
        if hit_stop:
            outcome, exit_price, exit_offset = "stop", stop, i + 1
            break
        if hit_target:
            outcome, exit_price, exit_offset = "target", target, i + 1
            break
    if outcome is None:
        outcome = "time"
        exit_price = float(future["close"].iloc[-1])
        exit_offset = len(future)

    R = (exit_price - entry) / risk * direction
    return {"outcome": outcome, "entered": True, "fill_offset": fill_offset,
            "exit_price": exit_price, "exit_offset": exit_offset, "R": R, "risk": risk}


# ---------------------------------------------------------------------------
# phase: reveal
# ---------------------------------------------------------------------------

def reveal(csv_path: Path = CSV_PATH, img_dir: Path = IMG_DIR):
    rows = list(csv.DictReader(open(csv_path)))
    cache = {}
    n_done = 0
    for r in rows:
        if not r["call_action"]:
            continue          # no call recorded yet — never touch it
        if r["after_png"]:
            continue          # already revealed
        key = (r["symbol"], r["tf"])
        if key not in cache:
            sym_map = {"BTC-USDT": "BTCUSDT", "ETH-USDT": "ETHUSDT"}
            cache[key] = load_series(sym_map[r["symbol"]], r["tf"])
        df = cache[key]
        decision_idx = int(r["decision_idx"])
        horizon = int(r["horizon"])

        after_path = img_dir / f"{r['drill_id']}_after.png"
        render_after(df, decision_idx, LOOKBACK, horizon, after_path, r["symbol"], r["tf"])
        r["after_png"] = str(after_path)

        call = {"action": r["call_action"],
                "entry": r["call_entry"] or None,
                "stop": r["call_stop"] or None,
                "target": r["call_target"] or None}
        result = score_call(call, df, decision_idx, horizon)
        r["outcome"] = result["outcome"]
        r["entered"] = result["entered"]
        r["fill_offset"] = "" if result["fill_offset"] is None else result["fill_offset"]
        r["exit_price"] = "" if result["exit_price"] is None else result["exit_price"]
        r["exit_offset"] = "" if result["exit_offset"] is None else result["exit_offset"]
        r["R"] = round(result["R"], 4)
        r["risk"] = "" if result["risk"] is None else round(result["risk"], 6)
        n_done += 1
        print(f"  revealed {r['drill_id']}: {r['call_action']} -> {result['outcome']}  R={r['R']}")

    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nrevealed {n_done} drills")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("generate")
    sub.add_parser("reveal")
    sub.add_parser("causality_test")

    rec = sub.add_parser("record")
    rec.add_argument("drill_id")
    rec.add_argument("action", choices=["long", "short", "no trade"])
    rec.add_argument("--entry", default=None)
    rec.add_argument("--stop", default=None)
    rec.add_argument("--target", default=None)
    rec.add_argument("--reasoning", default="")

    args = ap.parse_args()
    if args.cmd == "generate":
        generate()
    elif args.cmd == "reveal":
        reveal()
    elif args.cmd == "causality_test":
        ok = self_test_causality()
        print("causality self-test PASSED (before-image bytes identical with/without future data)"
              if ok else "causality self-test FAILED")
    elif args.cmd == "record":
        record_call(args.drill_id, args.action, args.entry, args.stop, args.target, args.reasoning)
        print(f"recorded {args.drill_id}: {args.action}")
