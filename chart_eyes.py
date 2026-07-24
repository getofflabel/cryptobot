"""
chart_eyes.py — give the machine actual VISUAL perception of market state.

Wallace, 2026-07-24: "you don't know what you're visually looking at at that
time. Your strategy isn't fully there." He is right. Every decision this
project makes today is computed from NUMBERS about a chart (ATR percentile,
trend sign, indicator values). Nothing ever LOOKS at the chart. A trader
perceives the picture first — "clean range, price at the top", "trend taking
a breath", "chop, stay out" — and only THEN reaches for a tool. That
perception step did not exist anywhere in this project. This module builds
it.

And then, mid-build, the sharper version of the ask: "I'm talking about
knowing what the red candle looks like, the green candle, the exact candle
at that second looks like." Structure-level reads (uptrend/range/chop) are
not enough — a real trader's judgment lives at the CANDLE. So the read
schema below has two layers: the higher-level picture (structure, location,
momentum, ...) AND a candle-level block (the last 5 closed candles in plain
English, plus a full breakdown of the bar forming right now). The renderer's
job is to make sure a vision model looking at the PNGs can actually resolve
individual candle bodies and wicks — that is why every timeframe gets both a
wide "full" image (~120 bars, the structure) and a "zoom" companion (~30
bars, where bodies/wicks stop being a blur) — and why the currently-forming,
unclosed bar is marked with a dashed outline and a "forming" label, so nobody
(human or model) mistakes an in-progress bar for a finished one.

THREE PIECES:
  1. render_market()        — pure rendering + our own data sources (BloFin
                               for crypto/XAUT, yfinance for tradfi). No
                               trading logic. No network in the tests below —
                               render_candles_png() is the network-free core
                               they exercise directly on synthetic frames.
  2. visual_read_prompt() /
     store_visual_read() /
     get_visual_read()       — the schema, the exact question set a
                               vision-capable reader must answer, and a small
                               rolling-history store in state["visual_reads"]
                               so the machine accumulates a memory of what it
                               saw over time.
  3. run_visual_cycle()      — orchestration: render, then hand the file
                               paths to an INJECTED `reader` callable. That
                               injection point is the whole design: there is
                               no vision API key anywhere in this project, so
                               the "reader" is meant to be a SCHEDULED AGENT
                               (a Claude session with real vision, run on a
                               cron) that opens the PNGs, fills in the
                               schema, and returns it. Plain-Python code
                               never has to see a pixel; it just calls
                               run_visual_cycle(..., reader=that_agent_call)
                               and consumes whatever lands in
                               state["visual_reads"][symbol].

HARD SAFETY — read this before wiring anything else to this module:

    ADVISORY_ONLY = True

No book (daily_pick, gold_book, tradfi_engine, diver, ...) may use a stored
visual read to open, size, or skip a trade. Not yet. This module only
PERCEIVES and RECORDS. The store exists so a validation round can later
measure, empirically, whether visual reads actually improve outcomes before
anything is allowed to act on them — same discipline as every other gate in
this project: prove it before you trade it.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")          # headless — never try to open a display
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

import pandas as pd

from exchange import TIMEFRAME_MS

# ---------------------------------------------------------------------------
# HARD SAFETY (see module docstring)
# ---------------------------------------------------------------------------

ADVISORY_ONLY = True


# ---------------------------------------------------------------------------
# vocabulary — the ONLY values a read is allowed to use. Strict on purpose:
# a free-text field drifts into a thousand synonyms for "kind of trendy" and
# becomes useless to compare over time. A fixed, small vocabulary is what
# lets us later ask "how often did 'clean' + 'expanding' actually pay?"
# ---------------------------------------------------------------------------

VALID_STRUCTURE = {"uptrend", "downtrend", "range", "chop", "transition"}
VALID_LOCATION = {
    "at range low", "mid range", "at range high",
    "breaking out", "breaking down", "pulling back in trend",
}
VALID_QUALITY = {"clean", "messy"}
VALID_MOMENTUM = {"expanding", "contracting", "stalling"}
VALID_BEST_TOOL = {"trend-follow", "range-fade", "breakout", "stand aside"}

VALID_CANDLE_COLOR = {"green", "red"}
VALID_BODY = {"large", "average", "small", "doji"}
VALID_WICKS = {"long upper", "long lower", "both", "none"}
VALID_CLOSE_POSITION = {"near high", "upper half", "middle", "lower half", "near low"}

REQUIRED_TF_FIELDS = (
    "structure", "location", "quality", "momentum", "key_levels",
    "tradeable", "best_tool", "one_line", "recent_candles", "current_candle",
)
REQUIRED_CANDLE_FIELDS = ("color", "body", "wicks", "close_position", "tells")

# the example object baked into visual_read_prompt() — a single source of
# truth so the prompt can never drift out of sync with validate_*() below.
_SCHEMA_TEMPLATE = {
    "structure": "uptrend|downtrend|range|chop|transition",
    "location": ("at range low|mid range|at range high|breaking out|"
                 "breaking down|pulling back in trend"),
    "quality": "clean|messy",
    "momentum": "expanding|contracting|stalling",
    "key_levels": [0.0, 0.0],
    "tradeable": True,
    "best_tool": "trend-follow|range-fade|breakout|stand aside",
    "one_line": "<what a trader would say out loud>",
    "recent_candles": [
        "<phrase for candle -5>", "<phrase for candle -4>", "<phrase for candle -3>",
        "<phrase for candle -2>", "<phrase for candle -1, the last CLOSED candle>",
    ],
    "current_candle": {
        "color": "green|red",
        "body": "large|average|small|doji",
        "wicks": "long upper|long lower|both|none",
        "close_position": "near high|upper half|middle|lower half|near low",
        "tells": "<what this specific candle is saying — e.g. 'sellers rejected "
                 "the push, price closed back inside the range'>",
    },
}


# ---------------------------------------------------------------------------
# small time helpers (no cross-module import — keep this file self-contained
# per the "FILES YOU OWN" boundary)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_display() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ===========================================================================
# 1. RENDERING
# ===========================================================================

DEFAULT_TIMEFRAMES = ("15m", "1h", "4h", "1d")
DEFAULT_BARS = 120
ZOOM_BARS = 30
MA_WARMUP = 60      # extra bars fetched (not displayed) so SMA50 has history

UP_COLOR = "#26d07c"
DOWN_COLOR = "#ef4444"
FORMING_EDGE = "#facc15"
BG_COLOR = "#0b0f14"
GRID_COLOR = "#1f2937"
TEXT_COLOR = "#e5e7eb"
MA_COLORS = {20: "#60a5fa", 50: "#f472b6"}
LEVEL_COLOR = "#94a3b8"
LAST_PRICE_COLOR = "#facc15"

FIGSIZE = (14.0, 8.0)     # x DPI=100 -> 1400x800px, per the brief
DPI = 100


def _safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "-").replace("=", "_").replace(" ", "_")


def _pick_x_ticks(n: int, want: int = 6) -> list[int]:
    if n <= want:
        return list(range(n))
    step = max(1, n // want)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return idx


def _attach_smas(df: pd.DataFrame, periods=(20, 50)) -> pd.DataFrame:
    """Compute SMAs on the FULL (with-warmup) series before any trimming, so
    a zoomed/trimmed window still shows a continuity-correct moving average
    instead of a mostly-NaN stub."""
    df = df.copy()
    closes = df["close"].astype(float)
    for p in periods:
        df[f"sma{p}"] = closes.rolling(p, min_periods=max(2, p // 4)).mean()
    return df


def render_candles_png(df: pd.DataFrame, symbol: str, timeframe: str, out_path,
                        *, n_closed: int | None = None, levels: dict | None = None,
                        as_of: str | None = None, zoom: bool = False,
                        sma_periods=(20, 50)) -> Path:
    """Pure, network-free rendering core. Draws `df` (columns: timestamp,
    open, high, low, close, volume[, sma20, sma50]) as a clean dark-theme
    candlestick PNG and writes it to out_path.

    n_closed: how many of the LEADING rows are closed bars. Any row at index
    >= n_closed is drawn as the currently-FORMING (unclosed) candle — dashed
    outline + a "forming" label, so it is never mistaken for a finished bar.
    Defaults to "every row is closed" when omitted.

    This is what the offline tests exercise directly on synthetic frames —
    it never touches the network, an exchange, or yfinance.
    """
    if df is None or len(df) == 0:
        raise ValueError("chart_eyes: cannot render an empty candle frame")

    df = df.reset_index(drop=True)
    n = len(df)
    if n_closed is None:
        n_closed = n

    smas = {}
    for p in sma_periods:
        col = f"sma{p}"
        if col in df.columns:
            smas[p] = df[col].astype(float)
        else:
            smas[p] = df["close"].astype(float).rolling(
                p, min_periods=max(2, p // 4)).mean()

    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)

    # gridlines: horizontal-only, faint — never fighting the candles
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5, alpha=0.5)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)

    body_w = 0.62
    for i in range(n):
        o = float(df.at[i, "open"]); h = float(df.at[i, "high"])
        l = float(df.at[i, "low"]);  c = float(df.at[i, "close"])
        up = c >= o
        color = UP_COLOR if up else DOWN_COLOR
        forming = i >= n_closed

        ax.add_line(Line2D([i, i], [l, h], color=color, linewidth=1.1,
                            solid_capstyle="round", zorder=2))

        y0, height = (o, c - o) if up else (c, o - c)
        if height <= 0:
            # doji / dead-flat bar — still needs a visible sliver
            span = h - l
            height = max(span * 0.015, abs(c) * 0.0006, 1e-9)
            y0 = (o + c) / 2 - height / 2

        edge = FORMING_EDGE if forming else color
        lw = 1.6 if forming else 0.0
        ls = (0, (3, 2)) if forming else "-"
        rect = Rectangle((i - body_w / 2, y0), body_w, height,
                          facecolor=color, edgecolor=edge, linewidth=lw,
                          linestyle=ls, zorder=3)
        ax.add_patch(rect)
        if forming:
            ax.text(i, h + (h - l) * 0.10 + 1e-9, "forming", ha="center",
                    va="bottom", fontsize=7, color=FORMING_EDGE, zorder=5)

    for p, series in smas.items():
        color = MA_COLORS.get(p, TEXT_COLOR)
        ax.plot(range(n), series.values, color=color, linewidth=1.0, zorder=4)
        last_valid = series.last_valid_index()
        if last_valid is not None:
            ax.text(last_valid + 0.6, series.iloc[last_valid], f"MA{p}",
                    color=color, fontsize=8, va="center", zorder=5)

    if levels:
        for label, price in levels.items():
            price = float(price)
            ax.axhline(price, color=LEVEL_COLOR, linewidth=0.8,
                       linestyle="--", zorder=1)
            ax.text(n - 1 + 0.6, price, f" {label} {price:g}",
                    color=LEVEL_COLOR, fontsize=8, va="center", zorder=5)

    last_price = float(df["close"].iloc[-1])
    ax.axhline(last_price, color=LAST_PRICE_COLOR, linewidth=0.7,
               linestyle=":", zorder=1)
    ax.text(n - 1 + 0.6, last_price, f" {last_price:,.4g}",
            color=LAST_PRICE_COLOR, fontsize=9, va="center",
            fontweight="bold", zorder=6)

    tick_idx = _pick_x_ticks(n)
    fmt = "%m-%d %H:%M" if timeframe in ("15m", "1h", "4h") else "%Y-%m-%d"
    ax.set_xticks(tick_idx)
    labels = []
    for i in tick_idx:
        ts = df["timestamp"].iloc[i]
        labels.append(ts.strftime(fmt) if hasattr(ts, "strftime") else str(ts))
    ax.set_xticklabels(labels, rotation=25, ha="right", color=TEXT_COLOR,
                       fontsize=8)
    ax.set_xlim(-1, n - 1 + 3.2)

    ax.tick_params(axis="y", colors=TEXT_COLOR, labelsize=9)
    ax.set_ylabel("price", color=TEXT_COLOR, fontsize=10)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)

    zoom_txt = f" · zoom (last {n})" if zoom else ""
    ax.set_title(f"{symbol}  ·  {timeframe}{zoom_txt}  ·  as of {as_of or _now_display()}",
                color=TEXT_COLOR, fontsize=12, loc="left", pad=10)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# data sources — network-touching. render_market() is the only public entry
# point that calls these; the tests never do.
# ---------------------------------------------------------------------------

_YF_TICKERS = {"SPY", "QQQ", "GLD", "USO", "GC=F", "DIA", "IWM"}


def _use_yfinance(symbol: str) -> bool:
    s = symbol.upper()
    return s.endswith("=F") or s in _YF_TICKERS


def _fetch_blofin_candles(symbol: str, timeframe: str, bars: int):
    from config import make_exchange     # local import: keep this module
    ex, _ = make_exchange("live")        # importable even if config/exchange
    df = ex.get_candles(symbol, timeframe=timeframe, limit=bars)
    last_price = None
    try:
        last_price = ex.get_ticker(symbol).last
    except Exception:
        pass                              # forming candle just gets skipped
    return df, last_price


_YF_INTERVAL = {"15m": "15m", "1h": "60m", "1d": "1d"}
_YF_PERIOD = {"15m": "60d", "1h": "730d", "1d": "5y"}


def _fetch_yfinance_candles(symbol: str, timeframe: str, bars: int):
    try:
        import yfinance as yf              # local import, try/except per the brief
    except ImportError as e:
        raise RuntimeError(
            f"chart_eyes: yfinance is not installed, cannot render {symbol}"
        ) from e

    base = "60m" if timeframe == "4h" else _YF_INTERVAL.get(timeframe)
    period = _YF_PERIOD.get("1h" if timeframe == "4h" else timeframe)
    if base is None:
        raise ValueError(f"chart_eyes: unsupported timeframe {timeframe!r} for yfinance")

    hist = yf.Ticker(symbol).history(period=period, interval=base, auto_adjust=False)
    if hist is None or hist.empty:
        raise RuntimeError(f"chart_eyes: yfinance returned no data for {symbol} {timeframe}")

    hist = hist.rename(columns={"Open": "open", "High": "high", "Low": "low",
                                "Close": "close", "Volume": "volume"})
    hist.index = pd.to_datetime(hist.index, utc=True)
    hist = hist[["open", "high", "low", "close", "volume"]].reset_index()
    hist = hist.rename(columns={hist.columns[0]: "timestamp"})

    if timeframe == "4h":
        hist = (hist.set_index("timestamp")
                    .resample("4h")
                    .agg({"open": "first", "high": "max", "low": "min",
                          "close": "last", "volume": "sum"})
                    .dropna()
                    .reset_index())

    df = hist.tail(bars).reset_index(drop=True)
    last_price = float(df["close"].iloc[-1]) if not df.empty else None
    return df, last_price


def _append_forming_candle(df: pd.DataFrame, timeframe: str, last_price):
    """Exchange candle feeds return CLOSED bars only. If we have a live
    ticker price, synthesize the bar forming right now so the render — and
    the eye looking at it — sees the in-progress candle, clearly marked, not
    just the frozen closed history."""
    n_closed = len(df)
    if df.empty or last_price is None:
        return df, n_closed
    interval_ms = TIMEFRAME_MS.get(timeframe)
    if interval_ms is None:
        return df, n_closed
    last_row = df.iloc[-1]
    next_ts = last_row["timestamp"] + pd.Timedelta(milliseconds=interval_ms)
    open_ = float(last_row["close"])
    close_ = float(last_price)
    forming = pd.DataFrame([{
        "timestamp": next_ts, "open": open_, "high": max(open_, close_),
        "low": min(open_, close_), "close": close_, "volume": 0.0,
    }])
    return pd.concat([df, forming], ignore_index=True), n_closed


def _fetch_candles_for_symbol(symbol: str, timeframe: str, bars: int):
    fetch_bars = bars + MA_WARMUP
    if _use_yfinance(symbol):
        df, last_price = _fetch_yfinance_candles(symbol, timeframe, fetch_bars)
        source = "yfinance"
    else:
        df, last_price = _fetch_blofin_candles(symbol, timeframe, fetch_bars)
        source = "blofin"
    if df is None or df.empty:
        raise RuntimeError(f"chart_eyes: no candle data for {symbol} {timeframe} ({source})")
    df, n_closed = _append_forming_candle(df, timeframe, last_price)
    return df, n_closed, source


def render_market(symbol: str, timeframes=DEFAULT_TIMEFRAMES, bars: int = DEFAULT_BARS,
                   out_dir="visual_reads", levels: dict | None = None,
                   zoom_bars: int = ZOOM_BARS) -> dict:
    """Render clean candlestick PNGs for `symbol` across every timeframe in
    `timeframes`, from the repo's own data sources (BloFin for crypto/XAUT
    via config.make_exchange("live"), yfinance for tradfi like CL=F/SPY).

    For each timeframe this writes TWO images:
      - "<symbol>_<tf>.png"       the full ~`bars`-bar structure view
      - "<symbol>_<tf>_zoom.png"  the last ~`zoom_bars` bars, large enough
                                   that individual candle bodies/wicks are
                                   unambiguous to a vision model

    `levels`, if given, is {label: price} and is drawn as labelled dashed
    horizontal lines on every timeframe (e.g. entry/stop/target, or a range
    high/low).

    Returns {tf: {"full": path, "zoom": path, "source": "blofin"|"yfinance",
                  "as_of": str, "bars": int}} — timeframes that fail to fetch
    (network hiccup, unsupported symbol, ...) are skipped with a printed
    warning rather than aborting the whole symbol.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    safe = _safe_symbol(symbol)
    as_of = _now_display()
    results = {}

    for tf in timeframes:
        try:
            df, n_closed, source = _fetch_candles_for_symbol(symbol, tf, bars)
        except Exception as e:
            print(f"  [chart_eyes] skipping {symbol} {tf}: {e}")
            continue

        df = _attach_smas(df)
        display = df.tail(bars).reset_index(drop=True)
        trimmed = len(df) - len(display)
        display_n_closed = max(0, n_closed - trimmed)

        full_path = out_path / f"{safe}_{tf}.png"
        render_candles_png(display, symbol, tf, full_path,
                           n_closed=display_n_closed, levels=levels, as_of=as_of)

        zoom_n = min(zoom_bars, len(df))
        zoom_display = df.tail(zoom_n).reset_index(drop=True)
        zoom_trimmed = len(df) - len(zoom_display)
        zoom_n_closed = max(0, n_closed - zoom_trimmed)
        zoom_path = out_path / f"{safe}_{tf}_zoom.png"
        render_candles_png(zoom_display, symbol, tf, zoom_path,
                           n_closed=zoom_n_closed, levels=levels, as_of=as_of,
                           zoom=True)

        results[tf] = {"full": str(full_path), "zoom": str(zoom_path),
                       "source": source, "as_of": as_of, "bars": len(display)}

    return results


# ===========================================================================
# 2. THE READ SCHEMA, THE PROMPT, AND THE STORE
# ===========================================================================

def visual_read_prompt(symbol: str, tf_files: dict) -> str:
    """Return the EXACT question set a vision-capable reader (a scheduled
    agent with real image perception) must answer for `symbol`, given the
    file paths render_market() produced. This is the single source of truth
    for the schema shown to the reader — it is built from the same
    VALID_* / _SCHEMA_TEMPLATE constants that validate_*() enforces below,
    so the prompt can never quietly drift out of sync with what is accepted.
    """
    lines = [
        f"CHART EYES — visual read request for {symbol}",
        "",
        "You are looking at rendered candlestick charts, not computing indicators. "
        "Answer only from what you SEE in the images below — open every one first.",
        "",
        "IMAGES:",
    ]
    for tf, entry in tf_files.items():
        lines.append(f"  {tf}:")
        lines.append(f"    full (structure, ~120 bars): {entry.get('full')}")
        lines.append(f"    zoom (candle detail, ~30 bars): {entry.get('zoom')}")
    lines += [
        "",
        "The bar with a dashed/outlined edge and a 'forming' label (if present) is the "
        "CURRENTLY FORMING, UNCLOSED bar — read it as live-in-progress. Never mistake it "
        "for a completed candle, and never include it in recent_candles.",
        "",
        "For EACH timeframe, answer this exact schema. Use ONLY the listed vocabulary for "
        "every enum field — do not invent new terms:",
        json.dumps(_SCHEMA_TEMPLATE, indent=2),
        "",
        f"structure options: {sorted(VALID_STRUCTURE)}",
        f"location options: {sorted(VALID_LOCATION)}",
        f"quality options: {sorted(VALID_QUALITY)}",
        f"momentum options: {sorted(VALID_MOMENTUM)}",
        f"best_tool options: {sorted(VALID_BEST_TOOL)}",
        f"current_candle.color options: {sorted(VALID_CANDLE_COLOR)}",
        f"current_candle.body options: {sorted(VALID_BODY)}",
        f"current_candle.wicks options: {sorted(VALID_WICKS)}",
        f"current_candle.close_position options: {sorted(VALID_CLOSE_POSITION)}",
        "",
        "recent_candles: the last 5 CLOSED candles on that timeframe (from the zoom image), "
        "newest last, one short plain-English phrase each — free text, e.g. 'big green body, "
        "closed near its high' or 'small red doji, long lower wick'.",
        "",
        "current_candle: a full breakdown of the bar forming RIGHT NOW — the single most "
        "decision-relevant object on the screen. 'tells' is free text: say what THIS candle "
        "is saying, e.g. 'sellers rejected the push, price closed back inside the range'.",
        "",
        "Return ONE JSON object shaped like:",
        '{"as_of": "<ISO-8601 UTC>", '
        '"per_timeframe": {"<tf>": <the schema above>, ...}, '
        '"summary": "<one or two plain-English sentences synthesizing every timeframe into '
        'the single picture a trader would carry into the day>"}',
        "",
        "ADVISORY ONLY: this read is stored to build an evidence base. It is NOT consumed by "
        "any live trading logic yet — see chart_eyes.ADVISORY_ONLY.",
    ]
    return "\n".join(lines)


def _check_enum(value, allowed: set, field: str, tf: str = "") -> None:
    if value not in allowed:
        where = f" (timeframe {tf!r})" if tf else ""
        raise ValueError(
            f"chart_eyes: invalid value {value!r} for {field!r}{where}. "
            f"Allowed: {sorted(allowed)}"
        )


def validate_timeframe_read(read: dict, tf: str = "") -> None:
    """Raise ValueError if `read` (one timeframe's worth of the schema) uses
    any value outside the fixed vocabulary, or is missing a required field."""
    if not isinstance(read, dict):
        raise ValueError(f"chart_eyes: timeframe read must be a dict, got {type(read).__name__}")

    for field in REQUIRED_TF_FIELDS:
        if field not in read:
            where = f" for timeframe {tf!r}" if tf else ""
            raise ValueError(f"chart_eyes: timeframe read missing required field {field!r}{where}")

    _check_enum(read["structure"], VALID_STRUCTURE, "structure", tf)
    _check_enum(read["location"], VALID_LOCATION, "location", tf)
    _check_enum(read["quality"], VALID_QUALITY, "quality", tf)
    _check_enum(read["momentum"], VALID_MOMENTUM, "momentum", tf)
    _check_enum(read["best_tool"], VALID_BEST_TOOL, "best_tool", tf)

    if not isinstance(read["tradeable"], bool):
        raise ValueError(f"chart_eyes: 'tradeable' must be a bool (timeframe {tf!r})")

    key_levels = read["key_levels"]
    if not isinstance(key_levels, list) or not all(isinstance(x, (int, float)) for x in key_levels):
        raise ValueError(f"chart_eyes: 'key_levels' must be a list of numbers (timeframe {tf!r})")

    one_line = read["one_line"]
    if not isinstance(one_line, str) or not one_line.strip():
        raise ValueError(f"chart_eyes: 'one_line' must be a non-empty string (timeframe {tf!r})")

    recent = read["recent_candles"]
    if not isinstance(recent, list) or not all(isinstance(x, str) and x.strip() for x in recent):
        raise ValueError(
            f"chart_eyes: 'recent_candles' must be a list of non-empty strings (timeframe {tf!r})"
        )

    cc = read["current_candle"]
    if not isinstance(cc, dict):
        raise ValueError(f"chart_eyes: 'current_candle' must be a dict (timeframe {tf!r})")
    for field in REQUIRED_CANDLE_FIELDS:
        if field not in cc:
            raise ValueError(
                f"chart_eyes: current_candle missing required field {field!r} (timeframe {tf!r})"
            )
    _check_enum(cc["color"], VALID_CANDLE_COLOR, "current_candle.color", tf)
    _check_enum(cc["body"], VALID_BODY, "current_candle.body", tf)
    _check_enum(cc["wicks"], VALID_WICKS, "current_candle.wicks", tf)
    _check_enum(cc["close_position"], VALID_CLOSE_POSITION, "current_candle.close_position", tf)
    if not isinstance(cc["tells"], str) or not cc["tells"].strip():
        raise ValueError(f"chart_eyes: current_candle.tells must be a non-empty string (timeframe {tf!r})")


def validate_full_read(read: dict) -> None:
    """Validate a whole store-shaped read: {as_of?, per_timeframe: {...}, summary}."""
    if not isinstance(read, dict):
        raise ValueError(f"chart_eyes: read must be a dict, got {type(read).__name__}")

    per_tf = read.get("per_timeframe")
    if not isinstance(per_tf, dict) or not per_tf:
        raise ValueError("chart_eyes: read must have a non-empty 'per_timeframe' dict")
    for tf, tf_read in per_tf.items():
        validate_timeframe_read(tf_read, tf)

    summary = read.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("chart_eyes: read must have a non-empty 'summary' string")


VISUAL_READ_HISTORY_CAP = 20   # rolling cap per symbol — a memory, not an archive


def store_visual_read(state: dict, symbol: str, read_dict: dict) -> dict:
    """Validate and persist one visual read into state["visual_reads"][symbol],
    a rolling list capped at VISUAL_READ_HISTORY_CAP entries (oldest dropped
    first) — this is how the machine accumulates a memory of what it saw.
    Returns the stored entry (== read_dict, with 'as_of' filled in only if
    the caller omitted it)."""
    validate_full_read(read_dict)
    entry = dict(read_dict)
    entry.setdefault("as_of", _now_iso())

    bucket = state.setdefault("visual_reads", {})
    history = bucket.setdefault(symbol, [])
    history.append(entry)
    del history[:-VISUAL_READ_HISTORY_CAP]
    return entry


def get_visual_read(state: dict, symbol: str):
    """The most recent stored visual read for `symbol`, or None."""
    history = state.get("visual_reads", {}).get(symbol)
    return history[-1] if history else None


def get_visual_read_history(state: dict, symbol: str) -> list:
    """The full rolling history (oldest first) for `symbol` — the memory."""
    return list(state.get("visual_reads", {}).get(symbol, []))


# ===========================================================================
# 3. ORCHESTRATION — the key-free path to real perception
# ===========================================================================

def run_visual_cycle(symbols, state: dict, reader, renderer=render_market,
                      out_dir="visual_reads", timeframes=DEFAULT_TIMEFRAMES,
                      bars: int = DEFAULT_BARS) -> dict:
    """Render + read, one symbol at a time, storing whatever the reader hands
    back.

    `reader` is the whole point: it is injected, not hard-coded, because this
    project has no vision API key anywhere. The intended wiring is a
    SCHEDULED AGENT — a Claude session (run on a cron, see the `schedule`
    skill) that:
      1. gets called with (symbol, tf_files),
      2. opens the PNG paths in tf_files with real vision,
      3. answers visual_read_prompt(symbol, tf_files) — the exact schema —
      4. returns the parsed dict.
    That callable is `reader` here. Plain Python — this function, the daemon,
    any book — never has to look at a pixel; it only ever consumes the
    dict that lands in state["visual_reads"][symbol] afterward.

    For tests, `reader` is a trivial fake that returns a fixed, valid dict —
    proving the wiring without any model or network involved.
    """
    if reader is None or not callable(reader):
        raise ValueError("chart_eyes.run_visual_cycle requires a callable `reader`")

    results = {}
    for symbol in symbols:
        tf_files = renderer(symbol, timeframes=timeframes, bars=bars, out_dir=out_dir)
        read = reader(symbol, tf_files)
        stored = store_visual_read(state, symbol, read)
        results[symbol] = {"tf_files": tf_files, "read": stored}
    return results


# ===========================================================================
# demonstration — render the CURRENT charts for BTC-USDT and XAUT-USDT
# ===========================================================================

if __name__ == "__main__":
    demo_symbols = ["BTC-USDT", "XAUT-USDT"]
    print(f"chart_eyes demo — ADVISORY_ONLY={ADVISORY_ONLY}")
    for sym in demo_symbols:
        print(f"\n{sym}:")
        out = render_market(sym, out_dir="visual_reads")
        for tf, entry in out.items():
            print(f"  {tf:>3}  full: {entry['full']}")
            print(f"       zoom: {entry['zoom']}  (source={entry['source']}, bars={entry['bars']})")
