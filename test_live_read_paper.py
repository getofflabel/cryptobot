"""
test_live_read_paper.py — offline tests for THE VISIBLE PAPER DESK
(live_read.py's `paper` block: surfacing tradfi_engine.py's and
spx_book.py's internal-paper ledgers on the dashboard/HUD).

Run with:  python3 test_live_read_paper.py

NO NETWORK. Only live_read.py's pure helper functions are exercised here
(_build_paper, _tradfi_book_entry, _spx_book_entry, _build_symbols'
OIL-PAPER/SPX-PAPER entries, _fmt_candles_compact, _resample_4h,
_24h_window_stats, _liq_price, _break_even_price, _fee_block) — none of
them ever call yfinance or Supabase themselves; write_live_read (the one
function that does reach out to yfinance) is intentionally NOT exercised
here since it needs a real/faked live_feed + BTC candles that belong to
the existing write_live_read test surface, not this paper-desk-focused
file. What matters for this file is that live_read.py NEVER imports
tradfi_engine or spx_book (checked directly below) and that the paper
block's shape holds under every state shape those two modules can hand it.

v4 (2026-07-24, BloFin-clone paper desk) added intents:
  i) multi-timeframe candle shape — all 5 timeframes present, COMPACT
     [t,o,h,l,c] arrays (not objects), capped to PAPER_CANDLE_CAP
  j) 4h resampling — bucket math + label convention
  k) 24h window stats — change/high/low, degrades to None under 2 bars
  l) position math hand-verified — margin, liq price both directions,
     break-even with fees, fee block
  m) empty/flat position math never raises

Original six intents:
  a) shape — both books open: every documented key present, correct types,
     the open dict's side/entry/stop/target/contracts_or_notional/opened_at
     all populated from the source trade dict
  b) shape — both books flat: `open` is None, record/pnl still computed
     from historical daybook/trades
  c) trade lists are capped to PAPER_TRADE_LOG_CAP (20), newest-first
  d) missing-state degradation: no "tradfi_engine"/"spx_book" KEYS in state
     at all -> paper block present, books == [], never an exception
  e) partial/malformed state (present key, missing sub-fields) never
     raises — degrades that one book, never the whole paper block
  f) module isolation — live_read.py's source never imports tradfi_engine
     or spx_book (the module docstring's explicit promise)
"""

from __future__ import annotations

import sys
import traceback
import pandas as pd

import live_read as lr


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _tradfi_state(oil_open=True, spy_open=False):
    open_trades = []
    if oil_open:
        open_trades.append({
            "symbol": "CL=F", "direction": 1, "entry_price": 89.00,
            "shares": 12.3, "notional": 1095.0, "leverage": 5.2,
            "stop_price": 88.10, "target_price": 90.50,
            "entry_time": "2026-07-24 15:00:00 UTC", "conviction": 61,
        })
    if spy_open:
        open_trades.append({
            "symbol": "SPY", "direction": -1, "entry_price": 738.0,
            "shares": 5.0, "notional": 3690.0, "leverage": 3.0,
            "stop_price": 742.0, "target_price": 730.0,
            "entry_time": "2026-07-24 16:00:00 UTC", "conviction": 55,
        })
    daybook = []
    for i in range(25):
        daybook.append({
            "date": f"2026-07-{(i % 28) + 1:02d}", "symbol": "CL=F",
            "dir": "long" if i % 2 == 0 else "short", "conviction": 50,
            "components": [], "outcome_pnl": 5.0 if i % 3 else -3.0,
            "hold_min": 60, "setup": "trend",
        })
    return {
        "ledger_equity": 2143.50,
        "open_trades": open_trades,
        "daybook": daybook,
        "last_slot_ts": None, "last_recap_date": None,
        "last_stopouts": {}, "picks": [],
    }


def _spx_state(open_trade=True):
    return {
        "virtual_equity": 2050.25,
        "peak_equity": 2100.0,
        "open_trade": ({
            "entry_date": "2026-07-24", "entry_price": 733.20,
            "shares": 8.4, "notional": 6158.9,
            "entry_time": "2026-07-24 13:00:00 UTC", "rsi2_at_entry": 3.1,
        } if open_trade else None),
        "last_bar_date": "2026-07-24",
        "trades": [
            {"entry_date": "2026-07-20", "entry_price": 700.0,
             "exit_date": "2026-07-21", "exit_price": 705.0,
             "shares": 2.5, "pnl": 12.5, "reason": "sma5_reclaim"}
            for _ in range(25)
        ],
        "realized_pnl_total": 312.5,
        "n": 25, "wins": 15, "crash_alerted": False,
    }


# ---------------------------------------------------------------------------
# a) both books open
# ---------------------------------------------------------------------------

def test_a_shape_both_open():
    state = {"tradfi_engine": _tradfi_state(oil_open=True, spy_open=True),
             "spx_book": _spx_state(open_trade=True)}
    paper = lr._build_paper(state)
    assert set(paper.keys()) == {"books", "candles", "updated"}
    assert isinstance(paper["updated"], str) and paper["updated"]
    assert len(paper["books"]) == 3

    by_name = {b["name"]: b for b in paper["books"]}
    oil = by_name["TradFi Engine · Oil"]
    assert oil["market"] == "Oil" and oil["symbol"] == "CL=F"
    assert oil["ledger_equity"] == 2143.50
    oil_open = oil["open"]
    # base fields unchanged from v3
    base = {
        "side": "LONG", "entry": 89.00, "stop": 88.10, "target": 90.50,
        "contracts_or_notional": 12.3, "notional": 1095.0, "leverage": 5.2,
        "opened_at": "2026-07-24 15:00:00 UTC",
    }
    for k, v in base.items():
        assert oil_open[k] == v, f"oil open[{k}] = {oil_open[k]!r}, want {v!r}"
    # v4 BloFin-column math — hand-verified against the module's own
    # formulas (fee_bps not set on this fixture -> falls back to
    # TRADFI_FEE_BPS["CL=F"] == 2.0)
    assert oil_open["fee_bps"] == 2.0
    assert oil_open["margin"] == round(1095.0 / 5.2, 2)
    assert oil_open["margin_mode"] == "isolated"
    assert oil_open["entry_fee"] == round(89.00 * (2.0 / 10000) * 12.3, 4)
    assert oil_open["liq_price"] == round(89.00 * (1 - 1/5.2 + 0.005), 4)
    fee_rate = 2.0 / 10000
    assert oil_open["break_even"] == round(89.00 * (1 + fee_rate) / (1 - fee_rate), 4)
    assert oil_open["mmr_assumed"] == lr.MAINT_MARGIN_RATE_ASSUMED == 0.005
    assert set(oil["record"].keys()) == {"w", "l"}
    assert oil["record"]["w"] + oil["record"]["l"] == 25
    assert isinstance(oil["today_pnl"], (int, float))
    assert isinstance(oil["all_time_pnl"], (int, float))
    assert isinstance(oil["trades"], list)
    assert oil["fees"] == {"maker_pct": 0.02, "taker_pct": 0.02,
                           "fee_bps": 2.0, "note": oil["fees"]["note"]}
    # candles are NOT embedded per-book (v4) — they live once per symbol
    # in paper["candles"], keyed by book["symbol"]; this fixture calls
    # _build_paper with no market_data, so the top-level dict is empty
    assert "candles_by_tf" not in oil and "stale_by_tf" not in oil
    assert paper["candles"] == {}

    spy_tradfi = by_name["TradFi Engine · S&P 500"]
    assert spy_tradfi["market"] == "S&P 500" and spy_tradfi["symbol"] == "SPY"
    assert spy_tradfi["ledger_equity"] == 2143.50   # SAME shared ledger as oil
    assert spy_tradfi["open"]["side"] == "SHORT"
    assert spy_tradfi["open"]["entry"] == 738.0
    # short liq/break-even formulas
    spy_open = spy_tradfi["open"]
    assert spy_open["fee_bps"] == 1.0   # falls back to TRADFI_FEE_BPS["SPY"]
    assert spy_open["liq_price"] == round(738.0 * (1 + 1/3.0 - 0.005), 4)
    fee_rate_spy = 1.0 / 10000
    assert spy_open["break_even"] == round(
        738.0 * (1 - fee_rate_spy) / (1 + fee_rate_spy), 4)
    assert spy_tradfi["fees"]["maker_pct"] == spy_tradfi["fees"]["taker_pct"] == 0.01

    dipbuy = by_name["S&P Dip-Buy"]
    assert dipbuy["market"] == "S&P 500" and dipbuy["symbol"] == "SPY"
    assert dipbuy["ledger_equity"] == 2050.25       # its OWN, separate ledger
    dipbuy_open = dipbuy["open"]
    base2 = {
        "side": "LONG", "entry": 733.20, "stop": None, "target": None,
        "contracts_or_notional": 8.4, "notional": 6158.9,
        "leverage": lr.SPX_DIPBUY_LEVERAGE,
        "opened_at": "2026-07-24 13:00:00 UTC",
    }
    for k, v in base2.items():
        assert dipbuy_open[k] == v, f"dipbuy open[{k}] = {dipbuy_open[k]!r}, want {v!r}"
    assert dipbuy_open["fee_bps"] == lr.SPX_DIPBUY_FEE_BPS == 1.0
    assert dipbuy_open["margin"] == round(6158.9 / 4.0, 2)
    assert dipbuy["record"] == {"w": 15, "l": 10}
    assert dipbuy["fees"]["fee_bps"] == 1.0


# ---------------------------------------------------------------------------
# b) both books flat
# ---------------------------------------------------------------------------

def test_b_shape_both_flat():
    state = {"tradfi_engine": _tradfi_state(oil_open=False, spy_open=False),
             "spx_book": _spx_state(open_trade=False)}
    paper = lr._build_paper(state)
    assert len(paper["books"]) == 3
    for b in paper["books"]:
        assert b["open"] is None
        # historical record/pnl still computed even though flat right now
        assert b["record"]["w"] + b["record"]["l"] > 0 or b["name"] == "TradFi Engine · S&P 500"


# ---------------------------------------------------------------------------
# c) trade lists capped at 20, newest-first
# ---------------------------------------------------------------------------

def test_c_trade_log_capped_newest_first():
    state = {"tradfi_engine": _tradfi_state(),
             "spx_book": _spx_state()}
    paper = lr._build_paper(state)
    by_name = {b["name"]: b for b in paper["books"]}

    oil = by_name["TradFi Engine · Oil"]
    assert len(oil["trades"]) == lr.PAPER_TRADE_LOG_CAP == 20
    # the fixture's daybook cycles dates 01..25 -> the newest appended
    # (index 24, date "2026-07-25 % 28 + 1" -> 25) must be trades[0]
    assert oil["trades"][0]["closed_date"] == "2026-07-25"

    dipbuy = by_name["S&P Dip-Buy"]
    assert len(dipbuy["trades"]) == 20
    assert dipbuy["trades"][0]["pnl"] == 12.5
    assert dipbuy["trades"][0]["entry"] == 700.0
    assert dipbuy["trades"][0]["exit"] == 705.0


# ---------------------------------------------------------------------------
# d) missing state keys entirely -> present but empty, never an exception
# ---------------------------------------------------------------------------

def test_d_missing_state_degrades_to_empty():
    paper = lr._build_paper({})
    assert paper == {"books": [], "candles": {}, "updated": paper["updated"]}
    assert isinstance(paper["updated"], str)

    # one present, one missing
    paper2 = lr._build_paper({"tradfi_engine": _tradfi_state()})
    names2 = [b["name"] for b in paper2["books"]]
    assert "S&P Dip-Buy" not in names2
    assert "TradFi Engine · Oil" in names2

    paper3 = lr._build_paper({"spx_book": _spx_state()})
    names3 = [b["name"] for b in paper3["books"]]
    assert names3 == ["S&P Dip-Buy"]

    # compute_live_read itself must also degrade cleanly with no paper
    # state at all (full pipeline, not just _build_paper in isolation)
    idx = pd.date_range("2026-01-01", periods=120, freq="h")
    c1h = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0,
                        "close": 100.0, "volume": 10.0}, index=idx)
    c4h = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0,
                        "close": 100.0, "volume": 10.0},
                       index=pd.date_range("2026-01-01", periods=120, freq="4h"))
    c1d = pd.DataFrame({"open": 100.0, "high": 101.0, "low": 99.0,
                        "close": 100.0, "volume": 10.0},
                       index=pd.date_range("2026-01-01", periods=400, freq="D"))
    snap = lr.compute_live_read(c1h, c4h, c1d, 0.5, {})
    assert snap["paper"] == {"books": [], "candles": {},
                             "updated": snap["paper"]["updated"]}
    assert "symbols" in snap and "OIL-PAPER" in snap["symbols"]
    assert snap["symbols"]["OIL-PAPER"]["position"] is None


# ---------------------------------------------------------------------------
# e) malformed / partial sub-state never raises
# ---------------------------------------------------------------------------

def test_e_malformed_state_never_raises():
    # engine present but every sub-key missing (pre-migration shape)
    paper = lr._build_paper({"tradfi_engine": {}, "spx_book": {}})
    assert len(paper["books"]) == 3
    for b in paper["books"]:
        assert b["ledger_equity"] == lr.PAPER_START_EQUITY_FALLBACK
        assert b["open"] is None
        assert b["record"] == {"w": 0, "l": 0}
        assert b["trades"] == []

    # open_trades entries missing expected keys
    bad_state = {"tradfi_engine": {
        "ledger_equity": 500.0,
        "open_trades": [{"symbol": "CL=F"}],   # no direction/entry/etc.
        "daybook": [{"symbol": "CL=F"}],        # no outcome_pnl/date
    }}
    paper2 = lr._build_paper(bad_state)
    oil = next(b for b in paper2["books"] if b["symbol"] == "CL=F")
    assert oil["open"]["side"] == "LONG"      # direction defaults to 1
    assert oil["open"]["entry"] is None
    assert oil["record"] == {"w": 0, "l": 1}  # missing outcome_pnl treated as 0 (not a win)
    # v4 math degrades to None (never a fabricated number) when the
    # inputs it needs (entry/leverage/notional/qty) aren't present
    assert oil["open"]["margin"] is None
    assert oil["open"]["entry_fee"] is None
    assert oil["open"]["liq_price"] is None
    assert oil["open"]["break_even"] is None
    # missing fee_bps still falls back to the CL=F constant, never None
    assert oil["open"]["fee_bps"] == lr.TRADFI_FEE_BPS["CL=F"] == 2.0

    # totally garbage types (string instead of dict) must not crash
    # _build_paper — it's wrapped per-book, so this should still return a
    # valid (if degraded) structure rather than raising.
    try:
        paper3 = lr._build_paper({"tradfi_engine": "not a dict",
                                  "spx_book": "also not a dict"})
        assert isinstance(paper3["books"], list)
    except Exception as e:
        raise AssertionError(f"_build_paper raised on garbage input: {e}")


# ---------------------------------------------------------------------------
# f) module isolation — never imports tradfi_engine or spx_book
# ---------------------------------------------------------------------------

def test_f_never_imports_tradfi_or_spx():
    with open("live_read.py") as f:
        src = f.read()
    assert "import tradfi_engine" not in src
    assert "from tradfi_engine" not in src
    assert "import spx_book" not in src
    assert "from spx_book" not in src


# ---------------------------------------------------------------------------
# g) HUD symbols map — OIL-PAPER / SPX-PAPER, existing symbols untouched
# ---------------------------------------------------------------------------

def test_g_hud_paper_symbols_and_existing_keys_untouched():
    state = {"tradfi_engine": _tradfi_state(oil_open=True, spy_open=True),
             "spx_book": _spx_state(open_trade=True)}
    symbols = lr._build_symbols(state, None, {}, [], None, None)

    assert "OIL-PAPER" in symbols and "SPX-PAPER" in symbols
    oil_pos = symbols["OIL-PAPER"]["position"]
    assert oil_pos["side"] == "LONG" and oil_pos["entry"] == 89.00
    assert oil_pos["stop"] == 88.10 and oil_pos["target"] == 90.50

    # spx_book's own dedicated position wins over the TradFi S&P slot when
    # both happen to be open at once (see _build_symbols' documented
    # priority) — its stop/target degrade to None (signal exit).
    spx_pos = symbols["SPX-PAPER"]["position"]
    assert spx_pos["book"] == "S&P Dip-Buy"
    assert spx_pos["entry"] == 733.20
    assert spx_pos["stop"] is None and spx_pos["target"] is None

    # every pre-existing symbol key is still there, untouched shape
    for key in ("BTC-USDT", "XAUT-USDT", "ETH-USDT", "SOL-USDT", "TSLA-USDT"):
        assert key in symbols
        assert "display" in symbols[key]

    # flat/missing paper state -> SPX-PAPER falls back to the rotation
    # status, never an exception
    symbols2 = lr._build_symbols({}, None, {}, [], None, None)
    assert symbols2["OIL-PAPER"]["position"] is None
    assert symbols2["OIL-PAPER"]["status"]["mode"] == "rotation"
    assert symbols2["SPX-PAPER"]["position"] is None


# ---------------------------------------------------------------------------
# h) _fmt_candles_compact — normalization + cap + COMPACT array shape
# ---------------------------------------------------------------------------

def test_h_fmt_candles_compact():
    idx = pd.date_range("2026-07-01", periods=200, freq="h", tz="America/New_York")
    df = pd.DataFrame({
        "Open": range(200), "High": [x + 1 for x in range(200)],
        "Low": [x - 1 for x in range(200)], "Close": range(200),
    }, index=idx)
    out = lr._fmt_candles_compact(df)
    assert len(out) == lr.PAPER_CANDLE_CAP == 150
    # each row is a bare [t, o, h, l, c] ARRAY, not a {t,o,h,l,c} object
    assert isinstance(out[0], list) and len(out[0]) == 5
    assert out[0][1] == 50.0   # tail(150) of 0..199 starts at 50
    assert out[-1][4] == 199.0
    assert isinstance(out[0][0], int)   # epoch seconds, not an ISO string
    assert out[0][0] > 1_700_000_000    # sane 2023+ epoch value

    assert lr._fmt_candles_compact(None) == []
    assert lr._fmt_candles_compact(pd.DataFrame()) == []


# ---------------------------------------------------------------------------
# i) multi-timeframe shape via PAPER_TIMEFRAMES — every label present
# ---------------------------------------------------------------------------

def test_i_paper_timeframes_shape():
    labels = [tf[0] for tf in lr.PAPER_TIMEFRAMES]
    assert labels == ["5m", "15m", "1h", "4h", "1d"]
    # exactly one timeframe (4h) is resample-only, no yfinance interval
    resample_only = [tf for tf in lr.PAPER_TIMEFRAMES if tf[1] is None]
    assert len(resample_only) == 1 and resample_only[0][0] == "4h"
    # every fetched timeframe (not 4h) carries a concrete yfinance period
    for label, interval, period in lr.PAPER_TIMEFRAMES:
        if label != "4h":
            assert interval and period


# ---------------------------------------------------------------------------
# j) _resample_4h — bucket math + label convention
# ---------------------------------------------------------------------------

def test_j_resample_4h():
    # 8 hourly bars starting at a clean 4h boundary -> exactly 2x 4h bars
    idx = pd.date_range("2026-07-01T00:00:00Z", periods=8, freq="h")
    df = pd.DataFrame({
        "Open": [10, 11, 12, 13, 20, 21, 22, 23],
        "High": [15, 16, 17, 18, 25, 26, 27, 28],
        "Low":  [9, 9, 9, 9, 19, 19, 19, 19],
        "Close": [11, 12, 13, 14, 21, 22, 23, 24],
    }, index=idx)
    out = lr._resample_4h(df)
    assert len(out) == 2
    # first 4h bucket = hours 00-03: open=first open, close=last close
    assert out["Open"].iloc[0] == 10 and out["Close"].iloc[0] == 14
    assert out["High"].iloc[0] == 18 and out["Low"].iloc[0] == 9
    # label='left' -> the bucket is named by its START time (00:00, not 04:00)
    assert out.index[0].hour == 0
    assert out.index[1].hour == 4
    # second bucket = hours 04-07
    assert out["Open"].iloc[1] == 20 and out["Close"].iloc[1] == 24

    assert lr._resample_4h(None) is None
    assert lr._resample_4h(pd.DataFrame()) is None


# ---------------------------------------------------------------------------
# k) _24h_window_stats — change/high/low off a real elapsed-time window
# ---------------------------------------------------------------------------

def test_k_24h_window_stats():
    # 30 hourly bars, price rising 100 -> 129
    idx = pd.date_range("2026-07-01T00:00:00Z", periods=30, freq="h")
    closes = [100.0 + i for i in range(30)]
    df = pd.DataFrame({
        "Open": closes, "High": [c + 2 for c in closes],
        "Low": [c - 2 for c in closes], "Close": closes,
    }, index=idx)
    stats = lr._24h_window_stats(df)
    assert stats is not None
    # last close = 129 (index 29); the 24h-ago cutoff lands within the
    # 30-bar span, so a real window (not the whole series) is used
    assert stats["change_24h_pct"] is not None
    assert stats["high_24h"] >= 129 - 2
    assert stats["low_24h"] <= 129

    # under 2 bars in the trailing 24h -> None, never a fabricated stat
    idx2 = pd.date_range("2026-07-01T00:00:00Z", periods=1, freq="h")
    df2 = pd.DataFrame({"Open": [100.0], "High": [101.0],
                        "Low": [99.0], "Close": [100.0]}, index=idx2)
    assert lr._24h_window_stats(df2) is None
    assert lr._24h_window_stats(None) is None
    assert lr._24h_window_stats(pd.DataFrame()) is None


# ---------------------------------------------------------------------------
# l) position math hand-verified — liq price both directions, break-even,
#    fee block. Independent of any state/book fixture — pure formula checks
#    against numbers worked out by hand.
# ---------------------------------------------------------------------------

def test_l_position_math_hand_verified():
    # --- liq price -----------------------------------------------------
    # long, entry=100, 10x leverage, mmr=0.5% -> 100*(1-0.1+0.005)=90.5
    assert lr._liq_price(100.0, 10.0, 1) == 90.5
    # short, entry=100, 10x leverage -> 100*(1+0.1-0.005)=109.5
    assert lr._liq_price(100.0, 10.0, -1) == 109.5
    # higher leverage -> liq price closer to entry (tighter)
    liq_5x = lr._liq_price(100.0, 5.0, 1)
    liq_20x = lr._liq_price(100.0, 20.0, 1)
    assert liq_20x > liq_5x   # 20x's long liq sits closer to the 100 entry
    # degrades to None without entry/leverage
    assert lr._liq_price(None, 10.0, 1) is None
    assert lr._liq_price(100.0, None, 1) is None
    assert lr._liq_price(100.0, 0, 1) is None

    # --- break-even ------------------------------------------------------
    # long, entry=100, fee_rate=0.0006 (6bps, BloFin taker) ->
    # 100*(1.0006)/(0.9994) — exact round-trip solve, hand-computed
    be_long = lr._break_even_price(100.0, 1, 0.0006)
    assert abs(be_long - (100.0 * 1.0006 / 0.9994)) < 1e-4   # fn rounds to 4dp
    assert be_long > 100.0   # a long needs to close ABOVE entry to break even
    be_short = lr._break_even_price(100.0, -1, 0.0006)
    assert be_short < 100.0  # a short needs to close BELOW entry
    # zero fee -> break-even collapses to entry exactly
    assert lr._break_even_price(100.0, 1, 0.0) == 100.0
    assert lr._break_even_price(None, 1, 0.0006) is None

    # --- fee block ---------------------------------------------------------
    fb = lr._fee_block(6.0)
    assert fb["maker_pct"] == fb["taker_pct"] == 0.06
    assert fb["fee_bps"] == 6.0
    assert "not BloFin" in fb["note"]


# ---------------------------------------------------------------------------
# m) empty/flat position math never raises
# ---------------------------------------------------------------------------

def test_m_empty_flat_degradation():
    # {} (like None) is this codebase's "no trade" sentinel -> None,
    # never a fabricated zeroed-out position
    assert lr._tradfi_open_dict(None) is None
    assert lr._tradfi_open_dict({}, symbol="CL=F") is None
    assert lr._spx_open_dict(None) is None
    assert lr._spx_open_dict({}) is None

    # a PRESENT-but-incomplete trade dict (direction only, no entry/lev/
    # notional/qty) degrades every derived field to None rather than
    # raising or fabricating a number
    flat = lr._tradfi_open_dict({"direction": 1}, symbol="CL=F")
    assert flat is not None
    assert flat["entry"] is None and flat["margin"] is None
    assert flat["liq_price"] is None and flat["break_even"] is None
    assert flat["fee_bps"] == lr.TRADFI_FEE_BPS["CL=F"]

    flat2 = lr._spx_open_dict({"entry_price": None})
    assert flat2["entry"] is None and flat2["margin"] is None
    assert flat2["leverage"] == lr.SPX_DIPBUY_LEVERAGE   # always the fixed constant

    # a flat book (no open_trades at all) never crashes on an empty
    # market_data -> paper["candles"] degrades to {}, no per-book keys
    state = {"tradfi_engine": _tradfi_state(oil_open=False, spy_open=False)}
    paper = lr._build_paper(state, market_data={})
    oil = next(b for b in paper["books"] if b["symbol"] == "CL=F")
    assert oil["open"] is None
    assert "candles_by_tf" not in oil
    assert paper["candles"] == {}


# ---------------------------------------------------------------------------
# n) candles live ONCE per symbol, not duplicated across books that share
#    a symbol (TradFi-S&P and S&P Dip-Buy both trade SPY)
# ---------------------------------------------------------------------------

def test_n_candles_deduped_by_symbol_not_per_book():
    state = {"tradfi_engine": _tradfi_state(oil_open=True, spy_open=True),
             "spx_book": _spx_state(open_trade=True)}
    cl_candles = {"5m": [[1721000000, 89.0, 89.1, 88.9, 89.05]]}
    spy_candles = {"5m": [[1721000000, 738.0, 738.5, 737.5, 738.2]]}
    market_data = {
        "CL=F": {"price": 89.05, "as_of": "20:00 UTC",
                 "candles_by_tf": cl_candles, "stale_by_tf": {"5m": False}},
        "SPY": {"price": 738.2, "as_of": "20:00 UTC",
               "candles_by_tf": spy_candles, "stale_by_tf": {"5m": False}},
    }
    paper = lr._build_paper(state, market_data)
    # top-level candles dict: exactly one entry per SYMBOL (2), not per
    # book (3) — CL=F and SPY, SPY carrying ONE copy even though two
    # books (TradFi-S&P + S&P Dip-Buy) both trade it
    assert set(paper["candles"].keys()) == {"CL=F", "SPY"}
    assert paper["candles"]["SPY"]["candles_by_tf"] == spy_candles
    assert paper["candles"]["CL=F"]["candles_by_tf"] == cl_candles
    # neither book embeds its own candle copy
    for b in paper["books"]:
        assert "candles_by_tf" not in b
    # but both SPY-trading books still carry their OWN last_price (cheap
    # scalar, harmless to duplicate) so the dashboard can show it without
    # a second lookup
    by_name = {b["name"]: b for b in paper["books"]}
    assert by_name["TradFi Engine · S&P 500"]["last_price"]["price"] == 738.2
    assert by_name["S&P Dip-Buy"]["last_price"]["price"] == 738.2


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main():
    tests = [
        test_a_shape_both_open,
        test_b_shape_both_flat,
        test_c_trade_log_capped_newest_first,
        test_d_missing_state_degrades_to_empty,
        test_e_malformed_state_never_raises,
        test_f_never_imports_tradfi_or_spx,
        test_g_hud_paper_symbols_and_existing_keys_untouched,
        test_h_fmt_candles_compact,
        test_i_paper_timeframes_shape,
        test_j_resample_4h,
        test_k_24h_window_stats,
        test_l_position_math_hand_verified,
        test_m_empty_flat_degradation,
        test_n_candles_deduped_by_symbol_not_per_book,
    ]
    results = []
    for fn in tests:
        try:
            fn()
            results.append((fn.__name__, True, None))
        except Exception as e:
            results.append((fn.__name__, False, f"{e}\n{traceback.format_exc()}"))

    print("\n" + "=" * 72)
    print("LIVE_READ PAPER DESK TEST SUMMARY")
    print("=" * 72)
    n_pass = 0
    for name, ok, err in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            n_pass += 1
        print(f"  [{status}] {name}")
        if not ok:
            for line in err.splitlines():
                print(f"          {line}")
    print("-" * 72)
    print(f"  {n_pass}/{len(results)} passed")
    print("=" * 72 + "\n")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
