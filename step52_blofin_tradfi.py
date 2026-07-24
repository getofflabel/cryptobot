"""
step52_blofin_tradfi.py — Round 52: BloFin's SYNTHETIC TRADFI PERPS, censused
and backtested for deployment on the owner's actual venue (BloFin, live
account or demo — see the venue-availability finding below, which is not
what the task brief assumed).

RESEARCH ONLY. Public market-data endpoints only. No live orders. Does not
touch gold_book.py / daemon.py / hourly.py (another agent owns those).

WHAT THIS SCRIPT DOES
  PHASE 1 — venue census: instrument specs, funding, 24h volume, max
    available history (1d + 1h) via exchange.py's BlofinExchange adapter,
    and TRACKING FIDELITY (BloFin perp vs the real underlying via yfinance):
    daily-return correlation, mean/max basis deviation, weekend behavior.
  PHASE 2a — gold TRANSFER CHECK: the already-validated donchian55+EMA20
    champion (round 48, sealed PASS on GLD/GC=F) run on XAU-USDT's own
    (short) BloFin history, trade dates compared side-by-side with GLD.
  PHASE 2b — silver FULL GAUNTLET: 20y SLV/SI=F daily, donchian20/55+EMA20
    and the MA trend family, 60/20/20 split, train/val only.
  PHASE 2c — SINGLE STOCKS FULL GAUNTLET: 7 megacaps, 20y yfinance daily,
    same two families, decade-by-decade consistency (train+val only) and
    an honest buy-and-hold comparison over the same window.
  PHASE 2d — oil: census/tracking only. Round 48 already killed oil
    strategies; we do not re-run dead configs.

A CRITICAL VENUE-AVAILABILITY FINDING SURFACES IN PHASE 1, STATED UP FRONT
SO IT ISN'T BURIED: BloFin's DEMO (paper) environment does NOT list most of
these instruments at all. XAU, XAG, MSFT, AAPL, GOOGL, NVDA, META, COIN,
AMZN, MSTR, HOOD return "Parameter instId error" on demo. Only SPX-USDT and
TSLA-USDT are fully queryable on demo; WTIOIL-USDT returns a live ticker on
demo but ZERO candle history. Every instrument this round covers is fully
live and historied on PROD (openapi.blofin.com) — that's where all data
below comes from, via public unauthenticated endpoints, matching the task's
"public market-data endpoints only" constraint. If the owner wants to
paper-test any of these before risking real money, BloFin's own demo book
currently can't do it for 11 of 14 symbols.

A SECOND CRITICAL FINDING: SPX-USDT IS NOT THE S&P 500. Its instrument spec
marks assetClass="Crypto" (not "Stocks"), it trades at ~$0.33-$1.30 while
the real S&P 500 index trades at ~7,400+ over the same dates, and its price
history (Sept 2025 - present) matches the known range of the SPX6900
memecoin (ticker SPX), not an equity index tracker. Every other stock/
commodity perp censused here (XAU, XAG, WTIOIL, and all 10 single names)
DOES track its real underlying tightly (see PHASE 1 correlation table) —
SPX-USDT is the one mislabeled listing in the bunch, and it is flagged, not
backtested against ^GSPC, because doing so would compare two unrelated
assets.

COSTS: per task spec, these trade like crypto perps on BloFin regardless of
what they synthetically track — repo default CostModel() UNCHANGED (taker
6bps/maker 2bps/1bp half-spread/2bp slippage/funding 1bp per 8h), unlike
round 48's TradFi scripts which zeroed funding for real ETFs/futures. Silver
and the 7 stocks use round 48's ETF/futures cost convention (yfinance data,
not a BloFin perp, so no perp-style funding applies) — see costs_for_etf()/
costs_for_future() below, copied verbatim from step48_tradfi_trend.py's
ASSET_CLASS convention.
"""

from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd
import yfinance as yf

sys.path.insert(0, "/Users/wallacechen/cryptobot")

from backtest import CostModel, run_backtest
from exchange import BlofinExchange
from strategy import atr, buy_and_hold, vol_gated_ma
from step48_tradfi_trend import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES,
    adaptive_vol_gate, days_to_bars, decade_breakdown, donchian_ema_exit,
    gap_stats_summary, print_decade_breakdown,
    score as score48, split_points, trend_signal, verdict_for,
)

pd.set_option("display.width", 240)
pd.set_option("display.max_columns", None)

# ---------------------------------------------------------------------------
# universe
# ---------------------------------------------------------------------------

BLOFIN_PROD = "https://openapi.blofin.com"

# task's full perp list, with the yfinance ticker each is supposed to track
PERPS = {
    "XAU-USDT":    {"class": "commodity", "underlying": "GC=F", "underlying2": "GLD"},
    "XAG-USDT":    {"class": "commodity", "underlying": "SI=F", "underlying2": "SLV"},
    "WTIOIL-USDT": {"class": "commodity", "underlying": "CL=F", "underlying2": "USO"},
    "SPX-USDT":    {"class": "index(?)",  "underlying": "^GSPC", "underlying2": None},
    "MSFT-USDT":   {"class": "stock", "underlying": "MSFT", "underlying2": None},
    "AAPL-USDT":   {"class": "stock", "underlying": "AAPL", "underlying2": None},
    "GOOGL-USDT":  {"class": "stock", "underlying": "GOOGL", "underlying2": None},
    "NVDA-USDT":   {"class": "stock", "underlying": "NVDA", "underlying2": None},
    "META-USDT":   {"class": "stock", "underlying": "META", "underlying2": None},
    "COIN-USDT":   {"class": "stock", "underlying": "COIN", "underlying2": None},
    "AMZN-USDT":   {"class": "stock", "underlying": "AMZN", "underlying2": None},
    "MSTR-USDT":   {"class": "stock", "underlying": "MSTR", "underlying2": None},
    "HOOD-USDT":   {"class": "stock", "underlying": "HOOD", "underlying2": None},
    "TSLA-USDT":   {"class": "stock", "underlying": "TSLA", "underlying2": None},
}

STOCK_SYMBOLS = ["NVDA-USDT", "TSLA-USDT", "AAPL-USDT", "MSFT-USDT",
                  "AMZN-USDT", "META-USDT", "GOOGL-USDT"]

# BloFin's demo (paper) environment: which of these are even queryable there.
# Measured empirically (see module docstring), not assumed.
DEMO_STATUS = {
    "XAU-USDT": "NOT ON DEMO (instId error)",
    "XAG-USDT": "NOT ON DEMO (instId error)",
    "WTIOIL-USDT": "ticker OK, 0 candles (unusable)",
    "SPX-USDT": "full (ticker+candles) — but see memecoin flag",
    "MSFT-USDT": "NOT ON DEMO (instId error)",
    "AAPL-USDT": "NOT ON DEMO (instId error)",
    "GOOGL-USDT": "NOT ON DEMO (instId error)",
    "NVDA-USDT": "NOT ON DEMO (instId error)",
    "META-USDT": "NOT ON DEMO (instId error)",
    "COIN-USDT": "NOT ON DEMO (instId error)",
    "AMZN-USDT": "NOT ON DEMO (instId error)",
    "MSTR-USDT": "NOT ON DEMO (instId error)",
    "HOOD-USDT": "NOT ON DEMO (instId error)",
    "TSLA-USDT": "full (ticker+candles)",
}

_ex = BlofinExchange(demo=False)   # PROD adapter — public data only, no keys


# ---------------------------------------------------------------------------
# PHASE 1a — BloFin candle fetch (repo's own adapter, paginated to max span)
# ---------------------------------------------------------------------------

def fetch_blofin_max(symbol: str, tf: str, use_cache: bool = True,
                      max_iters: int = 80) -> pd.DataFrame:
    fname = f"data_blofin_{symbol}_{tf}.parquet"
    if use_cache:
        try:
            cached = pd.read_parquet(fname)
            if len(cached):
                print(f"  cached {fname}: {len(cached)} bars "
                      f"{cached['timestamp'].iloc[0]:%Y-%m-%d %H:%M} -> "
                      f"{cached['timestamp'].iloc[-1]:%Y-%m-%d %H:%M}")
                return cached
        except FileNotFoundError:
            pass

    frames = []
    end_ms = None
    for _ in range(max_iters):
        d = _ex.get_candles(symbol, tf, limit=1440, end_ms=end_ms)
        if d.empty:
            break
        frames.append(d)
        oldest = d["timestamp"].iloc[0]
        new_end_ms = int(oldest.timestamp() * 1000)
        if end_ms is not None and new_end_ms >= end_ms:
            break
        end_ms = new_end_ms
        if len(d) < 2:
            break
        time.sleep(0.05)   # be polite to the public endpoint

    if not frames:
        out = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    else:
        out = (pd.concat(frames)
               .drop_duplicates(subset="timestamp")
               .sort_values("timestamp")
               .reset_index(drop=True))
    out.to_parquet(fname)
    if len(out):
        print(f"  saved {fname}: {len(out)} bars "
              f"{out['timestamp'].iloc[0]:%Y-%m-%d %H:%M} -> "
              f"{out['timestamp'].iloc[-1]:%Y-%m-%d %H:%M}")
    else:
        print(f"  saved {fname}: EMPTY (no candle history returned)")
    return out


# ---------------------------------------------------------------------------
# PHASE 1b — instrument specs / funding / volume
# ---------------------------------------------------------------------------

def instrument_spec(symbol: str) -> dict:
    spec = _ex.get_instrument(symbol)
    ticker = _ex.get_ticker(symbol)
    funding = _ex._get("/api/v1/market/funding-rate", {"instId": symbol})
    frate = float(funding[0]["fundingRate"]) if funding else float("nan")
    raw = _ex._request(f"{_ex.base_url}/api/v1/market/tickers", {"instId": symbol})
    row24 = raw["data"][0]
    return {
        "symbol": symbol,
        "asset_class_blofin": spec["assetClass"],
        "contract_value": float(spec["contractValue"]),
        "min_size": float(spec["minSize"]),
        "lot_size": float(spec["lotSize"]),
        "tick_size": float(spec["tickSize"]),
        "max_leverage": float(spec["maxLeverage"]),
        "list_time": pd.to_datetime(int(spec["listTime"]), unit="ms", utc=True),
        "last": ticker.last,
        "vol24h_base": float(row24["vol24h"]),
        "vol24h_notional_usdt": float(row24["vol24h"]) * float(spec["contractValue"]) * ticker.last,
        "funding_rate_pct_8h": frate * 100,
    }


# ---------------------------------------------------------------------------
# PHASE 1c — tracking fidelity vs real underlying (yfinance)
# ---------------------------------------------------------------------------

_YF_CACHE: dict[str, pd.DataFrame] = {}

def yf_daily(ticker: str, period: str = "max") -> pd.DataFrame:
    if ticker in _YF_CACHE:
        return _YF_CACHE[ticker]
    raw = None
    for attempt in range(3):
        try:
            raw = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
            if raw is not None and len(raw):
                break
        except Exception as e:
            print(f"    yfinance retry {ticker}: {e}")
        time.sleep(1)
    if raw is None or not len(raw):
        raise RuntimeError(f"no yfinance data for {ticker}")
    df = raw.reset_index()
    tcol = "Date" if "Date" in df.columns else "Datetime"
    out = pd.DataFrame({
        "timestamp": pd.to_datetime(df[tcol], utc=True).dt.normalize(),
        "open": df["Open"].astype(float), "high": df["High"].astype(float),
        "low": df["Low"].astype(float), "close": df["Close"].astype(float),
        "volume": df["Volume"].astype(float),
    }).dropna().drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    _YF_CACHE[ticker] = out
    return out


def tracking_fidelity(blofin_1d: pd.DataFrame, underlying_ticker: str) -> dict:
    """Correlation of daily returns + basis deviation over the overlapping
    window. Returns NaNs if there's no yfinance mapping (memecoin case is
    still called but the result is honestly reported as garbage)."""
    yf_df = yf_daily(underlying_ticker)
    b = blofin_1d.copy()
    b["date"] = pd.DatetimeIndex(b["timestamp"]).normalize()
    b = b.groupby("date", as_index=False).last()   # 1 row/day, safety
    y = yf_df.copy()
    y["date"] = pd.DatetimeIndex(y["timestamp"]).normalize()
    m = pd.merge(b[["date", "close"]], y[["date", "close"]], on="date",
                 suffixes=("_blofin", "_underlying")).sort_values("date")
    if len(m) < 5:
        return {"n_overlap": len(m), "corr": float("nan"),
                "mean_basis_pct": float("nan"), "max_basis_pct": float("nan")}
    ret_b = m["close_blofin"].pct_change().dropna()
    ret_u = m["close_underlying"].pct_change().dropna()
    corr = float(np.corrcoef(ret_b, ret_u)[0, 1]) if len(ret_b) > 2 else float("nan")
    # basis: only meaningful when price SCALES match (contract_value=1 assets
    # like stocks/commodities priced 1:1). SPX-USDT fails this by 4 orders of
    # magnitude and is reported as such, not silently normalized away.
    basis = (m["close_blofin"] - m["close_underlying"]) / m["close_underlying"] * 100
    return {"n_overlap": len(m), "corr": corr,
            "mean_basis_pct": float(basis.mean()), "max_basis_pct": float(basis.abs().max())}


def weekend_behavior(blofin_1h: pd.DataFrame) -> dict:
    """Does the perp actually move on Sat/Sun (real 24/7 crypto-style
    trading) or does it freeze / drift with dead ticks while the real
    underlying market is closed?"""
    if blofin_1h.empty:
        return {"weekday_range_pct": float("nan"), "weekend_range_pct": float("nan"),
                "weekend_zero_range_frac": float("nan"), "n_weekend_bars": 0}
    d = blofin_1h.copy()
    dow = pd.DatetimeIndex(d["timestamp"]).dayofweek   # 5=Sat, 6=Sun
    rng_pct = (d["high"] - d["low"]) / d["close"] * 100
    is_weekend = dow.isin([5, 6])
    wk = rng_pct[is_weekend]
    wd = rng_pct[~is_weekend]
    return {
        "weekday_range_pct": float(wd.mean()) if len(wd) else float("nan"),
        "weekend_range_pct": float(wk.mean()) if len(wk) else float("nan"),
        "weekend_zero_range_frac": float((wk == 0).mean()) if len(wk) else float("nan"),
        "n_weekend_bars": int(is_weekend.sum()),
    }


def run_census():
    print("=" * 100)
    print("PHASE 1 — VENUE CENSUS (BloFin PROD, public endpoints only)")
    print("=" * 100)

    rows = []
    frames = {}
    for symbol in PERPS:
        print(f"\n--- {symbol} ---")
        spec = instrument_spec(symbol)
        d1d = fetch_blofin_max(symbol, "1d")
        d1h = fetch_blofin_max(symbol, "1h")
        frames[symbol] = {"1d": d1d, "1h": d1h}

        underlying = PERPS[symbol]["underlying"]
        try:
            fid = tracking_fidelity(d1d, underlying)
        except Exception as e:
            fid = {"n_overlap": 0, "corr": float("nan"),
                   "mean_basis_pct": float("nan"), "max_basis_pct": float("nan")}
            print(f"    tracking check vs {underlying} failed: {e}")
        wknd = weekend_behavior(d1h)

        span_1d = (f"{len(d1d)}b {d1d['timestamp'].iloc[0]:%Y-%m-%d}->"
                   f"{d1d['timestamp'].iloc[-1]:%Y-%m-%d}") if len(d1d) else "NO DATA"
        span_1h = (f"{len(d1h)}b {d1h['timestamp'].iloc[0]:%Y-%m-%d}->"
                   f"{d1h['timestamp'].iloc[-1]:%Y-%m-%d}") if len(d1h) else "NO DATA"

        row = {
            "symbol": symbol, "class": PERPS[symbol]["class"],
            "vs": underlying, "demo_status": DEMO_STATUS[symbol],
            "span_1d": span_1d, "span_1h": span_1h,
            "contract_value": spec["contract_value"], "min_size": spec["min_size"],
            "max_leverage": spec["max_leverage"], "last": spec["last"],
            "vol24h_usdt": spec["vol24h_notional_usdt"],
            "funding_pct_8h": spec["funding_rate_pct_8h"],
            "corr_daily_ret": fid["corr"], "n_overlap_days": fid["n_overlap"],
            "mean_basis_pct": fid["mean_basis_pct"], "max_basis_pct": fid["max_basis_pct"],
            "weekday_range_pct": wknd["weekday_range_pct"],
            "weekend_range_pct": wknd["weekend_range_pct"],
            "weekend_zero_frac": wknd["weekend_zero_range_frac"],
        }
        rows.append(row)
        print(f"  1d: {span_1d} | 1h: {span_1h}")
        print(f"  contractValue={spec['contract_value']} minSize={spec['min_size']} "
              f"maxLev={spec['max_leverage']}x last={spec['last']} "
              f"24hVolUSDT=${spec['vol24h_notional_usdt']:,.0f} "
              f"funding={spec['funding_rate_pct_8h']:+.4f}%/8h")
        print(f"  vs {underlying}: corr(daily ret)={fid['corr']:.3f} "
              f"n_overlap={fid['n_overlap']}d mean_basis={fid['mean_basis_pct']:+.2f}% "
              f"max_basis={fid['max_basis_pct']:.2f}%")
        print(f"  weekend behavior (1h bars): weekday avg range={wknd['weekday_range_pct']:.3f}% "
              f"weekend avg range={wknd['weekend_range_pct']:.3f}% "
              f"({wknd['n_weekend_bars']} weekend bars, "
              f"{wknd['weekend_zero_range_frac']*100:.1f}% dead/zero-range)")

    df = pd.DataFrame(rows)
    print("\n\nCENSUS TABLE:")
    print(df.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
    return df, frames


# ---------------------------------------------------------------------------
# PHASE 2a — gold transfer check
# ---------------------------------------------------------------------------

def gold_transfer_check(frames):
    print("\n" + "=" * 100)
    print("PHASE 2a — GOLD TRANSFER CHECK (donchian55+EMA20, validated round-48 champion)")
    print("=" * 100)

    xau = frames["XAU-USDT"]["1d"]
    if len(xau) < 76:   # 55 + 20 warmup, minimum for even one signal
        print(f"  XAU-USDT has only {len(xau)} daily bars "
              f"({xau['timestamp'].iloc[0]:%Y-%m-%d} -> {xau['timestamp'].iloc[-1]:%Y-%m-%d} "
              f"if any) — below the ~76-bar warmup the donchian55/EMA20 shape needs before "
              f"it can emit a single signal. TRANSFER CHECK IS DATA-STARVED, not a strategy "
              f"failure: this is a venue-history limitation, honestly reported.")
        return

    gld = yf_daily("GLD")
    costs = CostModel()   # crypto-perp convention per task spec (funding included)

    sig_xau = donchian_ema_exit(xau, 55, ema_n=20)
    res_xau = run_backtest(xau, sig_xau, costs=costs, execution="taker")

    overlap_start = xau["timestamp"].iloc[0]
    gld_overlap = gld[gld["timestamp"] >= overlap_start].reset_index(drop=True)
    sig_gld = donchian_ema_exit(gld_overlap, 55, ema_n=20)
    costs_gld = CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                           slippage_bps=1.0, funding_bps_8h=0.0)
    res_gld = run_backtest(gld_overlap, sig_gld, costs=costs_gld, execution="taker")

    print(f"  overlap window: {overlap_start:%Y-%m-%d} -> now "
          f"({len(xau)} XAU-USDT bars, {len(gld_overlap)} GLD bars)")
    print(f"  XAU-USDT trades in window: {len(res_xau.trades)}")
    for t in res_xau.trades:
        print(f"    XAU  {t.entry_time:%Y-%m-%d} -> {t.exit_time:%Y-%m-%d}  pnl=${t.pnl:+,.2f}")
    print(f"  GLD   trades in window: {len(res_gld.trades)}")
    for t in res_gld.trades:
        print(f"    GLD  {t.entry_time:%Y-%m-%d} -> {t.exit_time:%Y-%m-%d}  pnl=${t.pnl:+,.2f}")

    if res_xau.trades and res_gld.trades:
        xau_dates = {t.entry_time.date() for t in res_xau.trades}
        gld_dates = {t.entry_time.date() for t in res_gld.trades}
        near_matches = sum(1 for xd in xau_dates
                            if any(abs((xd - gd).days) <= 3 for gd in gld_dates))
        print(f"  entry-date agreement (within 3 days): {near_matches}/{len(xau_dates)} "
              f"XAU entries have a matching GLD entry nearby")
    print(f"  XAU-USDT expectancy/trade: ${res_xau.expectancy:+,.2f}  "
          f"GLD expectancy/trade: ${res_gld.expectancy:+,.2f}  "
          f"(both tiny-n, informational only — NOT a sealed look)")


# ---------------------------------------------------------------------------
# PHASE 2b/2c — full gauntlet (silver + stocks), reusing step48 plumbing
# ---------------------------------------------------------------------------

def costs_for_etf() -> CostModel:
    return CostModel(fee_bps=1.0, maker_fee_bps=1.0, half_spread_bps=0.0,
                      slippage_bps=1.0, funding_bps_8h=0.0)


def costs_for_future() -> CostModel:
    return CostModel(fee_bps=0.5, maker_fee_bps=0.5, half_spread_bps=0.0,
                      slippage_bps=0.5, funding_bps_8h=0.0)


def mk_row(family, config, symbol, market, tf, tr, va) -> dict:
    """Same shape as step48_tradfi_trend.mk_row, but takes `market` directly
    instead of looking it up in step48's own SYMBOL-keyed MARKET_TAG dict
    (which only knows GLD/QQQ/SPY/USO/GC=F/CL=F, not SLV/SI=F/single stocks).
    verdict_for() is reused verbatim from step48."""
    return {
        "family": family, "config": config, "symbol": symbol,
        "market": market, "tf": tf,
        "tr_n": len(tr.trades), "tr_exp": tr.expectancy,
        "tr_win%": tr.win_rate * 100, "tr_dd%": tr.max_drawdown_pct,
        "tr_ret%": tr.total_return_pct,
        "va_n": len(va.trades), "va_exp": va.expectancy,
        "va_win%": va.win_rate * 100, "va_dd%": va.max_drawdown_pct,
        "va_ret%": va.total_return_pct,
        "verdict": verdict_for(tr, va),
    }


def gauntlet_symbol(symbol: str, d: pd.DataFrame, costs: CostModel, market_tag: str) -> list[dict]:
    """FAMILY 1 (trend champion port) + FAMILY 3 (donchian breakout), daily
    only — exactly step48's family1/family3 shapes, reused via import."""
    rows = []
    n, i_tr, i_va = split_points(d)

    for fast, slow in ((20, 100), (50, 200)):
        for gate_mode in ("adaptive", "fixed1.0", "fixed1.5", "ungated"):
            sig = trend_signal(d, fast, slow, gate_mode)
            tr, va = score48(d, sig, costs, i_tr, i_va)
            rows.append(mk_row("1-trend", f"{fast}/{slow} {gate_mode}",
                                symbol, market_tag, "1d", tr, va))

    for N in (20, 55):
        sig = donchian_ema_exit(d, N, ema_n=20)
        tr, va = score48(d, sig, costs, i_tr, i_va)
        rows.append(mk_row("3-breakout", f"donchian{N} EMA20exit",
                            symbol, market_tag, "1d", tr, va))

    return rows


def buy_hold_row(symbol: str, d: pd.DataFrame, costs: CostModel, i_va: int) -> dict:
    d_bh = d.iloc[:i_va].reset_index(drop=True)
    sig = buy_and_hold(d_bh)
    res = run_backtest(d_bh, sig, costs=costs, execution="taker")
    years = (d_bh["timestamp"].iloc[-1] - d_bh["timestamp"].iloc[0]).days / 365.25
    return {"symbol": symbol, "years": years, "total_return_pct": res.total_return_pct,
            "max_dd_pct": res.max_drawdown_pct,
            "cagr_pct": ((1 + res.total_return_pct / 100) ** (1 / years) - 1) * 100 if years > 0 else float("nan")}


def run_silver_gauntlet():
    print("\n" + "=" * 100)
    print("PHASE 2b — SILVER FULL GAUNTLET (20y SLV + SI=F daily, never tested before)")
    print("=" * 100)

    rows = []
    for symbol, ticker, costs in (("SLV", "SLV", costs_for_etf()),
                                   ("SI=F", "SI=F", costs_for_future())):
        d = yf_daily(ticker)
        n, i_tr, i_va = split_points(d)
        print(f"\n  {symbol}: {n} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed)")
        rows += gauntlet_symbol(symbol, d, costs, "silver")

    df = pd.DataFrame(rows)
    cols = ["family", "config", "symbol", "market", "tr_n", "tr_exp", "tr_win%",
            "tr_dd%", "tr_ret%", "va_n", "va_exp", "va_win%", "va_dd%", "va_ret%", "verdict"]
    print(f"\n{len(df)} silver configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())
    print("\n" + df[cols].sort_values(["symbol", "tr_exp"], ascending=[True, False])
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return df


def run_stocks_gauntlet():
    print("\n" + "=" * 100)
    print("PHASE 2c — SINGLE STOCKS FULL GAUNTLET (7 megacaps, 20y yfinance daily)")
    print("=" * 100)

    rows = []
    frames = {}
    for symbol in STOCK_SYMBOLS:
        ticker = PERPS[symbol]["underlying"]
        d = yf_daily(ticker)
        frames[symbol] = d
        n, i_tr, i_va = split_points(d)
        gaps = gap_stats_summary(d, [1.0, 2.0, 5.0, 10.0])
        print(f"\n  {ticker}: {n} bars {d['timestamp'].iloc[0]:%Y-%m-%d} -> "
              f"{d['timestamp'].iloc[-1]:%Y-%m-%d} | train->{d['timestamp'].iloc[i_tr]:%Y-%m-%d} "
              f"val->{d['timestamp'].iloc[i_va]:%Y-%m-%d} (test sealed) | gap>thresh: {gaps}")
        rows += gauntlet_symbol(symbol, d, costs_for_etf(), "single-stock")

    df = pd.DataFrame(rows)
    cols = ["family", "config", "symbol", "market", "tr_n", "tr_exp", "tr_win%",
            "tr_dd%", "tr_ret%", "va_n", "va_exp", "va_win%", "va_dd%", "va_ret%", "verdict"]
    print(f"\n{len(df)} stock configs tested. Verdict counts:")
    print(df["verdict"].value_counts().to_string())
    print("\n" + df[cols].sort_values(["symbol", "tr_exp"], ascending=[True, False])
          .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    survivors = df[df["verdict"] == "SURVIVOR"]
    near = df[df["verdict"] == "INSUFFICIENT-SAMPLE"]
    print(f"\nSURVIVORS: {len(survivors)}")
    if len(survivors):
        print(survivors[["family", "config", "symbol", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print(f"\nINSUFFICIENT-SAMPLE: {len(near)}")
    if len(near):
        print(near[["family", "config", "symbol", "tr_n", "tr_exp", "va_n", "va_exp"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))

    print("\nDecade-by-decade consistency (TRAIN+VAL only, survivors/near-misses, "
          "test window never touched):")
    daily_candidates = pd.concat([survivors, near])
    for _, row in daily_candidates.iterrows():
        symbol, family, config = row["symbol"], row["family"], row["config"]
        d = frames[symbol]
        n, i_tr, i_va = split_points(d)
        costs = costs_for_etf()
        if family == "1-trend":
            fast_slow, gate_mode = config.split(" ", 1)
            fast, slow = (int(x) for x in fast_slow.split("/"))
            sig = trend_signal(d, fast, slow, gate_mode)
        else:
            N = int(config.replace("donchian", "").split(" ")[0])
            sig = donchian_ema_exit(d, N)
        by_decade = decade_breakdown(d, sig, costs, i_va)
        print_decade_breakdown(f"{family} {config} {symbol}", by_decade)

    print("\nBuy-and-hold comparison (train+val window only, costs included):")
    for symbol in STOCK_SYMBOLS:
        d = frames[symbol]
        n, i_tr, i_va = split_points(d)
        bh = buy_hold_row(symbol, d, costs_for_etf(), i_va)
        print(f"  {symbol}: {bh['years']:.1f}y  B&H total return {bh['total_return_pct']:+.1f}%  "
              f"CAGR {bh['cagr_pct']:+.1f}%  max DD {bh['max_dd_pct']:.1f}%")

    return df


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    print("=" * 100)
    print("ROUND 52 — BloFin synthetic TradFi perps: venue census + strategy transfer")
    print("=" * 100)

    census_df, frames = run_census()
    gold_transfer_check(frames)
    silver_df = run_silver_gauntlet()
    stocks_df = run_stocks_gauntlet()

    print("\n" + "=" * 100)
    print("PHASE 2d — OIL (WTIOIL-USDT): census/tracking only, per task — round 48 already")
    print("killed oil strategies (0/many survivors on USO/CL=F). Not re-run here.")
    print("=" * 100)
    oil_row = census_df[census_df["symbol"] == "WTIOIL-USDT"]
    print(oil_row.to_string(index=False, float_format=lambda x: f"{x:,.3f}"))

    print("\nDone. No sealed-test window was ever sliced or scored above.")
    return census_df, silver_df, stocks_df


if __name__ == "__main__":
    main()
