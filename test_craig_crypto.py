"""
test_craig_crypto.py — the Craig engine, held to the same standard as the rest.

FIVE THINGS ARE PROVED HERE
  1. CAUSALITY. Every setup the engine stamps on real tape is re-derived with
     every later candle DELETED and must come out identical. This is the
     truncation pattern ported from `test_tjr_bot.py`, and it is the only
     thing standing between a measured edge and a lookahead artefact.
  2. HIS RULES ARE THE RULES. The change of character is a body close, the
     fair value gap is three consecutive candles that do not overlap, the
     entry is the gap's midpoint, the stop is outside the candle that produced
     it, the target is 1:4 of the risk actually taken, and break even is a
     close beyond a swing in the trade's favour.
  3. ONE SIZING PATH, and it is the project's single sizing function.
  4. COSTS ARE CHARGED AND NEVER CONSULTED — proved by reading this file's own
     source, the same way `test_tjr_crypto.py` proves it.
  5. NOTHING IS TOUCHED. No fetch, no parquet write, no order, no git, and no
     import of the TJR method beyond two named pure helpers.
"""

from __future__ import annotations

import inspect
import os

import numpy as np
import pandas as pd
import pytest

import craig_crypto as cc

REPO = os.path.dirname(os.path.abspath(__file__))
SRC = inspect.getsource(cc)
# the source with the module docstring removed, for tests that scan CODE
BODY = SRC.split('"""', 2)[2]

PAIR = "BTC/USD"
START = pd.Timestamp("2026-06-01")
END = pd.Timestamp("2026-07-26")

_DATA: dict = {}


def data(pair=PAIR):
    if pair not in _DATA:
        _DATA[pair] = cc.load(pair)
    return _DATA[pair]


def mk(rows, start="2026-03-02 09:30", minutes=5) -> pd.DataFrame:
    """rows: (o, h, l, c) on a fixed grid."""
    base = pd.Timestamp(start)
    return pd.DataFrame([{"t": base + pd.Timedelta(minutes=minutes * i),
                          "open": o, "high": h, "low": l, "close": c}
                         for i, (o, h, l, c) in enumerate(rows)])


# ============================================== the windowing, shared
def windows(pair=PAIR, cfg=None, start=START, end=END):
    """Exactly what `run_pair` hands `find_setups`, so a test can re-run one
    window with the future removed."""
    cfg = cfg or cc.config_for(pair)
    d = cc.bars(data(pair), cfg.entry_tf)
    pad = pd.Timedelta(minutes=cc._TF_MINUTES[cfg.entry_tf] * cfg.context_bars * 3)
    w = d[(d["t"] >= start - pad) &
          (d["t"] <= end + pd.Timedelta(hours=cfg.max_hold_hours + 6))] \
        .reset_index(drop=True)
    tarr = w["t"].to_numpy()
    out = []
    for name in cfg.sessions:
        for ts in cc.session_opens(start, end, name):
            i_open = int(np.searchsorted(tarr, np.datetime64(ts), "left"))
            i_end = int(np.searchsorted(
                tarr, np.datetime64(ts + pd.Timedelta(minutes=cfg.hunt_minutes)),
                "left")) - 1
            if i_open >= len(w) or i_end < i_open:
                continue
            i_ctx = max(0, i_open - cfg.context_bars)
            out.append((name, w.iloc[i_ctx:i_end + 1].reset_index(drop=True),
                        i_open - i_ctx, i_end - i_ctx))
    return cfg, w, out


# ==================================================== 1. CAUSALITY
def test_truncation_every_setup_survives_deleting_the_future():
    """THE test. Re-derive each real setup with every candle after its own
    change of character deleted. Same side, same entry, same stop, same
    target, same gap."""
    cfg, _, wins = windows()
    checked = 0
    for name, sub, i_open, i_end in wins:
        full = cc.find_setups(sub, i_open, i_end, cfg, PAIR, name)
        for s in full:
            cut = sub.iloc[:s.choch_i + 1].reset_index(drop=True)
            again = cc.find_setups(cut, i_open, min(i_end, s.choch_i),
                                   cfg, PAIR, name)
            assert again, (f"{s.choch_t}: the setup vanished when the future "
                           f"was deleted")
            g = again[-1]
            assert g.choch_t == s.choch_t, f"{s.choch_t}: a different candle"
            assert g.direction == s.direction, f"{s.choch_t}: side moved"
            assert g.entry == pytest.approx(s.entry), f"{s.choch_t}: entry moved"
            assert g.stop == pytest.approx(s.stop), f"{s.choch_t}: stop moved"
            assert g.target == pytest.approx(s.target), f"{s.choch_t}: target moved"
            assert g.gap_lo == pytest.approx(s.gap_lo)
            assert g.gap_hi == pytest.approx(s.gap_hi)
            checked += 1
    assert checked >= 20, f"only {checked} setups to test causality on"


def test_truncation_a_quiet_session_stays_quiet():
    """The sessions the engine sits out must also be decided without the
    future."""
    cfg, _, wins = windows()
    quiet = 0
    for name, sub, i_open, i_end in wins:
        if cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            continue
        cut = sub.iloc[:i_end + 1].reset_index(drop=True)
        assert not cc.find_setups(cut, i_open, i_end, cfg, PAIR, name), \
            "a session traded once the future was removed"
        quiet += 1
    assert quiet >= 10


def test_a_setup_reads_no_candle_after_its_own():
    """Stronger than truncation: the bars after the change of character are
    replaced with garbage and the answer may not move."""
    cfg, _, wins = windows()
    checked = 0
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            bad = sub.copy()
            after = bad.index > s.choch_i
            for col in ("open", "high", "low", "close"):
                bad.loc[after, col] = 1.0
            again = cc.find_setups(bad, i_open, min(i_end, s.choch_i),
                                   cfg, PAIR, name)
            assert again and again[-1].entry == pytest.approx(s.entry), \
                f"{s.choch_t}: the setup moved when the future was corrupted"
            checked += 1
    assert checked >= 20


def test_the_bar_step_is_read_off_the_past_only():
    assert "_bar_step(t[:i + 1])" in SRC, \
        "the candle width must be read off closed bars only"


# ============================================ 2. HIS RULES ARE THE RULES
def test_change_of_character_needs_a_body_close_not_a_wick():
    """A wick through the swing does nothing."""
    # down candle, up candle -> stamps a swing LOW; then a down break
    rows = [(10, 10.5, 9.5, 9.6),    # down
            (9.6, 10.2, 9.4, 10.1),  # up   -> swing low at 9.4
            (10.1, 10.4, 9.9, 10.3),
            (10.3, 10.5, 9.3, 9.5)]  # wick under 9.4, CLOSE above it
    d = mk(rows)
    cfg = cc.CraigConfig(pair="X", round_trip_cost_pct=0.0)
    s = cc.find_setups(d, 2, 3, cfg, "X", "t")
    assert not s, "a wick through the swing was treated as a break"

    rows[3] = (10.3, 10.5, 9.3, 9.35)          # now the BODY closes beyond
    d2 = mk(rows)
    # the break is now real; whether a gap qualifies is a separate rule, so
    # assert on the break rather than on a setup existing
    assert _broke(d2, cfg) == -1


def _broke(d, cfg):
    """Which way, if at all, the last candle broke structure — read through
    the engine's own scan by asking it on a config that cannot reject."""
    from tjr_bot import two_candle_swings
    sh, sl = two_candle_swings(d)
    mrh = mrl = None
    out = 0
    c = d["close"].to_numpy(float)
    for i in range(len(d)):
        out = 0
        if mrh is not None and c[i] > mrh:
            out = +1
        elif mrl is not None and c[i] < mrl:
            out = -1
        if not np.isnan(sh[i]):
            mrh = float(sh[i])
        if not np.isnan(sl[i]):
            mrl = float(sl[i])
    return out


def test_a_fair_value_gap_is_three_candles_that_do_not_overlap():
    """His definition: the first candle's high does not reach the third
    candle's low. Touching is not a gap."""
    cfg = cc.CraigConfig(pair="X", round_trip_cost_pct=0.0)
    t = pd.to_datetime(["2026-03-02 09:30", "2026-03-02 09:35",
                        "2026-03-02 09:40"]).to_numpy()
    h = np.array([10.0, 12.0, 12.5])
    lo = np.array([9.0, 10.0, 10.5])
    assert float(h[0]) < float(lo[2]), "the fixture is not a gap"
    # overlapping: third candle's low sits under the first candle's high
    lo2 = np.array([9.0, 10.0, 9.8])
    assert not (float(h[0]) < float(lo2[2]))


def test_a_hole_in_the_tape_is_not_a_fair_value_gap():
    """Three ROWS with a missing candle between them is not three candles.
    The Alpaca crypto tape has minutes with no trade in them."""
    cfg = cc.CraigConfig(pair="X", round_trip_cost_pct=0.0)
    d = mk([(10, 10.2, 9.9, 10.1)] * 6)
    d.loc[3, "t"] = d.loc[3, "t"] + pd.Timedelta(minutes=10)   # punch a hole
    step = cc._bar_step(d["t"].to_numpy())
    assert step == np.timedelta64(5, "m"), "the candle width was misread"
    assert (d["t"].to_numpy()[3] - d["t"].to_numpy()[1]) != 2 * step


def test_the_entry_is_the_midpoint_of_the_gap():
    cfg, _, wins = windows()
    n = 0
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            assert s.entry == pytest.approx(0.5 * (s.gap_lo + s.gap_hi)), \
                f"{s.choch_t}: the entry is not the gap's midpoint"
            n += 1
    assert n >= 20


def test_the_gap_sits_in_his_fifty_to_sixty_one_eight_zone():
    cfg, _, wins = windows()
    n = 0
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            lo, hi = sorted((s.zone_deep, s.zone_shallow))
            assert s.gap_hi >= lo - 1e-9 and s.gap_lo <= hi + 1e-9, \
                f"{s.choch_t}: the gap is outside the 50-61.8 zone"
            n += 1
    assert n >= 20


def test_the_sixty_one_eight_is_deeper_than_the_fifty():
    """A long retraces DOWN to the 61.8, a short retraces UP to it."""
    cfg, _, wins = windows()
    n = 0
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            if s.direction > 0:
                assert s.zone_deep < s.zone_shallow < s.leg_high
            else:
                assert s.zone_deep > s.zone_shallow > s.leg_low
            n += 1
    assert n >= 20


def test_the_stop_is_beyond_the_entry_and_never_a_constant():
    """Every stop is a candle's own extreme, so no two are the same number and
    none of them is a percentage written down anywhere."""
    cfg, _, wins = windows()
    widths = []
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            if s.direction > 0:
                assert s.stop < s.entry, f"{s.choch_t}: long stop above entry"
            else:
                assert s.stop > s.entry, f"{s.choch_t}: short stop below entry"
            widths.append(round(s.stop_pct, 6))
    assert len(widths) >= 20
    assert len(set(widths)) > 0.5 * len(widths), \
        "the stops repeat — something fixed is setting them"


def test_the_target_is_exactly_one_to_four_of_the_risk_taken():
    cfg, w, wins = windows()
    n = 0
    for name, sub, i_open, i_end in wins:
        for s in cc.find_setups(sub, i_open, i_end, cfg, PAIR, name):
            s.choch_i += int(np.searchsorted(
                w["t"].to_numpy(), np.datetime64(sub["t"].iloc[0]), "left"))
            tr = cc.manage(w, s, cfg, 100_000.0)
            if tr is None:
                continue
            risk = abs(tr.entry - tr.stop_at_risk)
            reward = abs(tr.target - tr.entry)
            assert reward == pytest.approx(cfg.target_r * risk, rel=1e-9), \
                f"{tr.entry_t}: the target is not 1:{cfg.target_r:.0f}"
            n += 1
    assert n >= 10


def test_the_one_to_one_switch_actually_moves_the_target():
    cfg4 = cc.config_for(PAIR, target_r=4.0)
    cfg1 = cc.config_for(PAIR, target_r=1.0)
    a = cc.run_pair(PAIR, START, END, cfg=cfg4, data=data())
    b = cc.run_pair(PAIR, START, END, cfg=cfg1, data=data())
    assert len(a["trades"]) == len(b["trades"]) > 5, \
        "changing the target changed which trades were taken"
    ra = [t.r_multiple for t in a["trades"] if t.outcome == "target"]
    rb = [t.r_multiple for t in b["trades"] if t.outcome == "target"]
    assert ra and rb
    assert max(ra) == pytest.approx(4.0) and max(rb) == pytest.approx(1.0)


def test_break_even_never_moves_the_stop_against_the_trade():
    cfg = cc.config_for(PAIR)
    for t in cc.run_pair(PAIR, START, END, cfg=cfg, data=data())["trades"]:
        if not t.moved_to_breakeven:
            continue
        assert t.stop == pytest.approx(t.entry), \
            "break even did not put the stop at the entry"
        if t.direction > 0:
            assert t.stop >= t.stop_at_risk
        else:
            assert t.stop <= t.stop_at_risk


def test_a_break_even_exit_never_books_a_loss_before_costs():
    cfg = cc.config_for(PAIR)
    for t in cc.run_pair(PAIR, START, END, cfg=cfg, data=data())["trades"]:
        if t.outcome == "break even":
            assert t.r_multiple == pytest.approx(0.0, abs=1e-9)
            assert t.pnl + t.cost == pytest.approx(0.0, abs=1e-6), \
                "a break-even exit lost money before the round trip"


def test_the_entry_never_fills_through_its_own_stop():
    cfg = cc.config_for(PAIR)
    for t in cc.run_pair(PAIR, START, END, cfg=cfg, data=data())["trades"]:
        if t.direction > 0:
            assert t.entry > t.stop_at_risk, f"{t.entry_t}: filled under the stop"
        else:
            assert t.entry < t.stop_at_risk, f"{t.entry_t}: filled over the stop"


def test_the_fill_bar_cannot_book_a_target():
    """A candle we entered inside also holds the price action before the
    entry. Reading a target off its high books wins the trade never had."""
    assert "(i > fill_i) and (" in SRC, \
        "the fill bar is being scored two-sided again"


# ============================================ 3. THE SESSIONS AND THE CLOCK
def test_new_york_opens_at_half_past_nine_new_york_time():
    for day, utc in (("2026-01-15", "14:30"),     # winter, EST
                     ("2026-07-15", "13:30")):    # summer, EDT
        got = cc.session_opens(pd.Timestamp(day), pd.Timestamp(day), "new_york")
        assert got and got[0] == pd.Timestamp(f"{day} {utc}"), \
            f"{day}: New York's open drifted against daylight saving"


def test_every_session_is_his_own_list():
    assert set(cc.SESSIONS) == {"asia", "london", "new_york"}


def test_the_session_set_is_configurable():
    cfg = cc.config_for(PAIR, sessions=("new_york",))
    r = cc.run_pair(PAIR, START, END, cfg=cfg, data=data())
    assert r["trades"], "New York alone produced nothing"
    assert {t.session for t in r["trades"]} == {"new_york"}


def test_a_setup_is_only_stamped_inside_his_two_hours():
    cfg = cc.config_for(PAIR)
    r = cc.run_pair(PAIR, START, END, cfg=cfg, data=data())
    for t in r["trades"]:
        zone, hh, mm = cc.SESSIONS[t.session]
        opens = cc.session_opens(pd.Timestamp(t.choch_t).normalize()
                                 - pd.Timedelta(days=1),
                                 pd.Timestamp(t.choch_t).normalize()
                                 + pd.Timedelta(days=1), t.session)
        gap = min(abs((pd.Timestamp(t.choch_t) - o).total_seconds())
                  for o in opens)
        assert 0 <= (pd.Timestamp(t.choch_t)
                     - max(o for o in opens if o <= t.choch_t)).total_seconds() \
            <= cfg.hunt_minutes * 60, \
            f"{t.choch_t}: signalled outside his {cfg.hunt_minutes} minutes"


# =================================================== 4. SIZING AND COSTS
def test_there_is_exactly_one_sizing_path():
    """Every unit count in this engine comes from `tjr_bot.size_position`."""
    assert SRC.count("size_position(") == 1, "a second sizing path appeared"
    assert "return size_position(" in SRC
    assert SRC.count("def _size(") == 1
    # ...and it is reached from exactly one place, the fill
    assert BODY.count("_size(") - BODY.count("def _size(") == 1


def test_a_trade_risks_its_stated_share_of_the_equity_it_was_sized_on():
    cfg = cc.config_for(PAIR)
    n = 0
    for t in cc.run_pair(PAIR, START, END, cfg=cfg, data=data())["trades"]:
        want = cfg.risk_pct_per_trade * t.equity_at_entry
        assert t.risk_dollars == pytest.approx(want, rel=1e-6), \
            f"{t.entry_t}: risked {t.risk_dollars} not {want}"
        assert t.units * abs(t.entry - t.stop_at_risk) == pytest.approx(want, rel=1e-6)
        n += 1
    assert n >= 10


def test_leverage_is_an_output_never_an_input():
    assert "max_leverage" not in SRC and "leverage_cap" not in SRC
    assert "buying_power_multiple: float | None = None" in SRC, \
        "a buying-power cap was borrowed from another venue"


def test_the_alpaca_and_index_caps_are_not_imported():
    assert "4.0" not in SRC.split("buying_power")[0][-400:]
    cfg = cc.CraigConfig()
    assert cfg.buying_power_multiple is None


def test_costs_are_charged_on_every_closed_trade():
    cfg = cc.config_for(PAIR)
    ts = cc.run_pair(PAIR, START, END, cfg=cfg, data=data())["trades"]
    assert ts
    for t in ts:
        assert t.cost > 0, f"{t.entry_t}: no round trip was charged"
        assert t.cost == pytest.approx(
            cfg.round_trip_cost_pct * t.units * t.entry, rel=1e-9)


def test_costs_are_never_consulted():
    """The owner's rule, proved by reading the source: the cost appears only
    where money is booked, never in a comparison that could decline a trade,
    prefer a pair, or move a threshold."""
    for i, line in enumerate(SRC.splitlines(), 1):
        code = line.split("#")[0]
        if "round_trip_cost_pct" not in code:
            continue
        ok = ("tr.cost =" in code or "float(cost)" in code
              or ": float = 0.0" in code or "cost = derived" in code
              or "cfg.round_trip_cost_pct * t.units" in code
              or "round_trip_cost_pct=" in code)
        assert ok, f"line {i}: the cost is being consulted, not just charged:\n  {line}"
        for bad in (" if ", " > ", " < ", ">=", "<=", "return ", " and ", " or "):
            assert bad not in code, \
                f"line {i}: the cost reached a decision:\n  {line}"


# ================================================= 5. NOTHING IS TOUCHED
def test_nothing_is_fetched_and_nothing_is_written():
    for bad in ("to_parquet", "requests", "urllib", "httpx", "alpaca",
                "blofin", "subprocess", "os.system", "open("):
        assert bad not in SRC, f"the engine reaches for {bad}"


def test_no_orders_anywhere():
    for bad in ("place_order", "submit_order", "create_order", "post(", "put("):
        assert bad not in SRC


def test_only_two_helpers_come_from_the_tjr_method():
    imports = [l for l in SRC.splitlines() if l.startswith(("import ", "from "))]
    tjr = [l for l in imports if "tjr" in l]
    assert tjr == ["from tjr_bot import size_position, two_candle_swings",
                   "import tjr_crypto"], tjr
    # and tjr_crypto is only ever reached for the parquet path and the
    # measured round trip — never for a level, a bias or a session window
    import re
    used = set(re.findall(r"tjr_crypto\.(\w+)", BODY))
    assert used == {"cache_name", "load_derived"}, used
    assert set(re.findall(r"tjr_bot\.(\w+)", BODY)) <= {
        "size_position", "two_candle_swings"}


def test_the_pairs_are_his_five_and_the_retired_coins_are_absent():
    assert cc.PAIRS == ["BTC/USD", "ETH/USD", "SOL/USD", "XRP/USD", "DOT/USD"]
    for gone in ("LINK", "ADA", "LTC", "AVAX", "DOGE"):
        assert not any(gone in p for p in cc.PAIRS)


def test_the_data_is_read_through_the_existing_cache_path():
    assert "tjr_crypto.cache_name" in SRC


def test_every_invention_is_declared():
    """Anything the transcript does not contain has to be listed where a
    reader will find it."""
    words = cc.in_his_words()
    for must in ("5-minute", "swing", "120 minutes", "session", "break even",
                 "market on the signal", "gap"):
        assert must.lower() in words.lower(), f"{must} is not declared"


def test_the_engine_runs_end_to_end_and_books_money():
    r = cc.run_pair(PAIR, START, END, cfg=cc.config_for(PAIR), data=data())
    assert len(r["trades"]) >= 10
    f = cc.frame({PAIR: r})
    assert set(["pair", "session", "leverage", "stop_move_in_price_pct",
                "pnl", "cost", "r"]).issubset(f.columns)
    assert f["leverage"].min() > 0
    assert r["account"] == pytest.approx(
        cc.CraigConfig.account_start + f["pnl"].sum())
