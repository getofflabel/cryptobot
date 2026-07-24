"""
test_live_read_paper.py — offline tests for THE VISIBLE PAPER DESK
(live_read.py's `paper` block: surfacing tradfi_engine.py's and
spx_book.py's internal-paper ledgers on the dashboard/HUD).

Run with:  python3 test_live_read_paper.py

NO NETWORK. Only live_read.py's pure helper functions are exercised here
(_build_paper, _tradfi_book_entry, _spx_book_entry, _build_symbols'
OIL-PAPER/SPX-PAPER entries, _fmt_candles) — none of them ever call
yfinance or Supabase themselves; write_live_read (the one function that
does reach out to yfinance) is intentionally NOT exercised here since it
needs a real/faked live_feed + BTC candles that belong to the existing
write_live_read test surface, not this paper-desk-focused file. What
matters for this file is that live_read.py NEVER imports tradfi_engine or
spx_book (checked directly below) and that the paper block's shape holds
under every state shape those two modules can hand it.

Six intents:
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
    assert set(paper.keys()) == {"books", "updated"}
    assert isinstance(paper["updated"], str) and paper["updated"]
    assert len(paper["books"]) == 3

    by_name = {b["name"]: b for b in paper["books"]}
    oil = by_name["TradFi Engine · Oil"]
    assert oil["market"] == "Oil" and oil["symbol"] == "CL=F"
    assert oil["ledger_equity"] == 2143.50
    assert oil["open"] == {
        "side": "LONG", "entry": 89.00, "stop": 88.10, "target": 90.50,
        "contracts_or_notional": 12.3, "notional": 1095.0, "leverage": 5.2,
        "opened_at": "2026-07-24 15:00:00 UTC",
    }
    assert set(oil["record"].keys()) == {"w", "l"}
    assert oil["record"]["w"] + oil["record"]["l"] == 25
    assert isinstance(oil["today_pnl"], (int, float))
    assert isinstance(oil["all_time_pnl"], (int, float))
    assert isinstance(oil["trades"], list)

    spy_tradfi = by_name["TradFi Engine · S&P 500"]
    assert spy_tradfi["market"] == "S&P 500" and spy_tradfi["symbol"] == "SPY"
    assert spy_tradfi["ledger_equity"] == 2143.50   # SAME shared ledger as oil
    assert spy_tradfi["open"]["side"] == "SHORT"
    assert spy_tradfi["open"]["entry"] == 738.0

    dipbuy = by_name["S&P Dip-Buy"]
    assert dipbuy["market"] == "S&P 500" and dipbuy["symbol"] == "SPY"
    assert dipbuy["ledger_equity"] == 2050.25       # its OWN, separate ledger
    assert dipbuy["open"] == {
        "side": "LONG", "entry": 733.20, "stop": None, "target": None,
        "contracts_or_notional": 8.4, "notional": 6158.9, "leverage": None,
        "opened_at": "2026-07-24 13:00:00 UTC",
    }
    assert dipbuy["record"] == {"w": 15, "l": 10}


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
    assert paper == {"books": [], "updated": paper["updated"]}
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
    assert snap["paper"] == {"books": [], "updated": snap["paper"]["updated"]}
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
# h) _fmt_candles — normalization + cap
# ---------------------------------------------------------------------------

def test_h_fmt_candles():
    idx = pd.date_range("2026-07-01", periods=200, freq="h", tz="America/New_York")
    df = pd.DataFrame({
        "Open": range(200), "High": [x + 1 for x in range(200)],
        "Low": [x - 1 for x in range(200)], "Close": range(200),
    }, index=idx)
    out = lr._fmt_candles(df)
    assert len(out) == lr.PAPER_CANDLE_BARS == 120
    assert out[0]["o"] == 80.0   # tail(120) of 0..199 starts at 80
    assert out[-1]["c"] == 199.0
    assert out[0]["t"].endswith("+00:00") or out[0]["t"].endswith("Z")

    assert lr._fmt_candles(None) == []
    assert lr._fmt_candles(pd.DataFrame()) == []


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
        test_h_fmt_candles,
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
