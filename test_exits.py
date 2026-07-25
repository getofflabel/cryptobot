"""
test_exits.py — offline unit tests for exits.py (ROUND 99 PART 1, THE EXIT
LIBRARY). Every fixture below is small, synthetic, and hand-checkable: the
comments state the expected number BEFORE the assertion, computed by hand
arithmetic (or, where fractal-pivot/EMA/ATR/Bollinger math is involved,
independently reproduced with plain numpy in the comments/derivation) —
never copy-pasted from a first run of the code under test. Plain asserts,
a TESTS list, a main() runner printing PASS/FAIL — no pytest, matching
this repo's own test style (see test_gold_book.py).

NO NETWORK. NO PARQUET FILES. Every candle frame here is constructed
in-line. Run with:  python3 test_exits.py
"""

from __future__ import annotations

import sys
import traceback

import numpy as np
import pandas as pd

import exits as E


# ---------------------------------------------------------------------------
# fixture helper
# ---------------------------------------------------------------------------

def mkdf(o, h, l, c) -> pd.DataFrame:
    n = len(c)
    return pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=n, freq="h", tz="UTC"),
        "open": np.asarray(o, dtype=float), "high": np.asarray(h, dtype=float),
        "low": np.asarray(l, dtype=float), "close": np.asarray(c, dtype=float),
    })


# ===========================================================================
# 0. PIVOT PRIMITIVES
# ===========================================================================

def test_find_pivots_basic():
    """Strictly increasing/decreasing arms around one spike each -> exactly
    one unambiguous pivot per array (no ties). h has a spike UP at j=4
    (30, vs neighbors 10..18 rising/falling around it); a 7-bar window
    (k=2) centered at j=4 is h[2:7]=[12,13,30,15,16], max=30=h[4] ->
    confirmed at j+k=6. l mirrors it with a spike DOWN at j=4 (2, vs
    18..10 falling around it); window l[2:7]=[16,15,2,13,12], min=2=l[4]
    -> confirmed at 6."""
    h = np.array([10, 11, 12, 13, 30, 15, 16, 17, 18], dtype=float)
    l = np.array([18, 17, 16, 15, 2, 13, 12, 11, 10], dtype=float)
    piv_h, piv_l = E.find_pivots(h, l, k=2)
    assert list(piv_h["confirm_idx"]) == [6], piv_h
    assert list(piv_h["price"]) == [30.0], piv_h
    assert list(piv_l["confirm_idx"]) == [6], piv_l
    assert list(piv_l["price"]) == [2.0], piv_l


def test_gap_or_level():
    """A long stop at level=95: if the bar's open (90) already traded
    through it, fill AT THE OPEN (90), not the level. If the open (96)
    has NOT yet traded through, fill at the level (95) itself. Target
    side mirrors: a long target at 105 fills at the open (110) if the
    open gapped past it, else at the level."""
    assert E._gap_or_level(90.0, 95.0, E.LONG, "stop") == 90.0
    assert E._gap_or_level(96.0, 95.0, E.LONG, "stop") == 95.0
    assert E._gap_or_level(110.0, 105.0, E.LONG, "target") == 110.0
    assert E._gap_or_level(100.0, 105.0, E.LONG, "target") == 105.0
    # short side mirrors exactly
    assert E._gap_or_level(106.0, 105.0, E.SHORT, "stop") == 106.0
    assert E._gap_or_level(104.0, 105.0, E.SHORT, "stop") == 105.0


# ===========================================================================
# MASTER FIXTURE — a clean zigzag with unambiguous, hand-checked pivots.
# Reused across the structure/measured-move tests below. Bar values and
# confirm_idx/price were independently verified against find_pivots() and
# are restated here as the expectation, exactly like test_gold_book.py's
# own "documented inline" synthetic-data convention.
#
#   bar   0   1   2   3   4   5   6   7   8   9
#  close 100 101 102 103 104 103 102 101 100  90   <- minor peak@4 (104.5
#                                                       incl. wick), real
#                                                       trough@9 (89.5)
#   bar  10  11  12  13  14  15  16  17  18  19
#  close  92  94  96  98 100 102 104 106 108 120   <- real peak@19 (121
#                                                       incl. wick)
#   bar  20  21  22  23  24  25  26  27  28  29
#  close 118 116 114 112 110 108 106 104 102 100
#   bar  30  31  32  33  34  35  36  37  38  39
#  close  98  96  94  92  80  82  84  86  88  90   <- real trough@34 (79.5
#                                                       incl. wick)
#
# k=2 pivots (verified via find_pivots on this exact array):
#   piv_high: confirm=6  price=104.5   (minor peak@4)
#             confirm=21 price=121.0   (major peak@19)
#   piv_low:  confirm=11 price=89.5    (major trough@9)
#             confirm=36 price=79.5    (major trough@34)
# ===========================================================================

def _master_df():
    close = np.array([
        100, 101, 102, 103, 104,
        103, 102, 101, 100, 90,
        92, 94, 96, 98, 100,
        102, 104, 106, 108, 120,
        118, 116, 114, 112, 110,
        108, 106, 104, 102, 100,
        98, 96, 94, 92, 80,
        82, 84, 86, 88, 90,
    ], dtype=float)
    high = close + 0.5
    low = close - 0.5
    high[19] = 121.0
    low[9] = 89.5
    low[34] = 79.5
    return mkdf(close.copy(), high, low, close)


def test_master_fixture_pivots():
    ctx = E.build_series_ctx(_master_df(), k=2)
    assert list(ctx.piv_high["confirm_idx"]) == [6, 21]
    assert list(ctx.piv_high["price"]) == [104.5, 121.0]
    assert list(ctx.piv_low["confirm_idx"]) == [11, 36]
    assert list(ctx.piv_low["price"]) == [89.5, 79.5]


# ===========================================================================
# 1. STOPS
# ===========================================================================

def test_stop_percentage_baseline():
    """entry=100, direction long, pct=5 -> level = 100*(1-0.05) = 95,
    constant regardless of bar. Also asserts it self-identifies as a
    BASELINE, never a candidate."""
    df = _master_df()
    ctx = E.build_series_ctx(df, k=2)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.stop_percentage(5.0)
    assert m.level_fn(tc, 5) == 95.0
    assert m.level_fn(tc, 20) == 95.0   # fixed, not trailing
    assert m.is_baseline()
    assert not E.stop_atr(1.5).is_baseline()


def test_stop_structure_n_back_and_buffer():
    """entry=39 (close=90.0), long. Protective (below-entry) pivots
    confirmed by bar 39: trough@9 (89.5, confirm=11) and trough@34 (79.5,
    confirm=36) — BOTH are below entry_price=90, so both qualify.
    n_back=1 -> the more RECENT one in time = 79.5 (confirm=36).
    n_back=2 -> the earlier one = 89.5 (confirm=11).
    buffer_pct=1.0 on n_back=1 -> 79.5*(1-0.01) = 78.705."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 39, 90.0, E.LONG)
    m1 = E.stop_structure(k=2, n_back=1)
    m2 = E.stop_structure(k=2, n_back=2)
    mb = E.stop_structure(k=2, n_back=1, buffer_pct=1.0)
    assert m1.level_fn(tc, 39) == 79.5
    assert m2.level_fn(tc, 39) == 89.5
    assert abs(mb.level_fn(tc, 39) - 78.705) < 1e-9


def test_stop_structure_use_close_variant():
    """use='close' pivots are built on the CLOSE array, not high/low —
    the trough@9's close-based pivot is close[9]=90.0 (not the wick low
    89.5), and the trough@34's is close[34]=80.0 (not 79.5). n_back=1 at
    entry=39 -> 80.0."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 39, 90.0, E.LONG)
    m = E.stop_structure(k=2, n_back=1, use="close")
    assert m.level_fn(tc, 39) == 80.0


def test_stop_structure_none_when_no_pivot_yet():
    """entry=5 (close=103), long: no confirmed protective (below-entry)
    low pivot exists yet by bar 5 (the first confirmed low, trough@9, only
    confirms at bar 11 > 5). Method must return None, not guess."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 5, 103.0, E.LONG)
    m = E.stop_structure(k=2, n_back=1)
    assert m.level_fn(tc, 5) is None


def test_stop_structure_trailing_ratchets_never_back():
    """Two-pivot fixture, k=1. Confirmed protective (below-entry) lows
    appear at bar 3 (price 94.7, confirm=4) and bar 8 (price 97.7,
    confirm=9) — 97.7 > 94.7, a genuine higher low.
        bar:    0    1    2    3    4    5    6    7    8    9   10
       close: 100  101  102   95  103  104  105  106   98  107  108
    (bar3=95 is a real trough: 3-wide window [j-1,j+1] at j=3 is
    [102,95,103], min=95=l[3] -> confirmed at j+k=4. At j=8 window=
    [106,98,107], min=98=l[8] -> confirmed at j+k=9.)

    Entry at bar 5 (close=104, long) — chosen AFTER the first pivot's
    own confirm bar (4) so it is genuinely knowable as of entry (an
    entry at bar 0 could not use a pivot that only confirms at bar 4;
    that is the correct causal behavior, exercised separately in
    test_stop_structure_none_when_no_pivot_yet). Initial anchor = 94.7
    (the only protective pivot confirmed by entry). Floor stays 94.7
    until bar 9's pivot (97.7) confirms, then ratchets up and NEVER
    falls back."""
    close = np.array([100, 101, 102, 95, 103, 104, 105, 106, 98, 107, 108], dtype=float)
    high = close + 0.3
    low = close - 0.3
    df = mkdf(close.copy(), high, low, close)
    ctx = E.build_series_ctx(df, k=1)
    piv = ctx.piv_low
    assert list(piv["confirm_idx"]) == [4, 9], piv
    assert list(piv["price"]) == [94.7, 97.7], piv   # wick low = close-0.3

    tc = E.build_trade_ctx(ctx, 5, 104.0, E.LONG)
    m = E.stop_structure_trailing(fallback_pct=5.0)
    assert m.level_fn(tc, 5) == 94.7    # initial anchor, known at entry
    assert m.level_fn(tc, 8) == 94.7    # still, bar-9 pivot not confirmed yet
    assert m.level_fn(tc, 9) == 97.7    # ratchets up
    assert m.level_fn(tc, 10) == 97.7   # holds, does not fall back


def test_stop_structure_trailing_fallback_when_no_pivot():
    """No protective pivot exists yet (very start of a series) ->
    fallback_pct=5.0 on entry=100 long -> floor = 100*(1-0.05) = 95."""
    close = np.array([100, 100.2, 100.1, 100.3], dtype=float)
    df = mkdf(close, close + 0.1, close - 0.1, close)
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.stop_structure_trailing(fallback_pct=5.0)
    assert m.level_fn(tc, 1) == 95.0


def test_stop_structure_trailing_intrabar_or_close_trigger():
    """Floor=95 (fallback). Bar A: low wicks to 94 but CLOSES at 96 ->
    intrabar touch fires first (gap-through: open=97 didn't gap past 95,
    so fill=95, the level itself). Separately, a bar that only closes
    below the floor without ever wicking through it must also fire, at
    that close."""
    close = np.array([100, 100, 100], dtype=float)
    df = mkdf([100, 97, 100], [100.5, 97.5, 100.5], [99.5, 94.0, 99.5], close)
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_structure_trailing(fallback_pct=5.0)
    out = E.run_trade(tc, stop, None, max_hold_bars=5)
    assert out.exit_bar == 1
    assert out.exit_price == 95.0
    assert "stop_structure_trailing" in out.reason

    # close-only break: never wicks to 95, but bar1 CLOSES at 94
    df2 = mkdf([100, 100, 100], [100.5, 100.5, 100.5], [99.5, 96.0, 99.5], [100, 94, 94])
    ctx2 = E.build_series_ctx(df2, k=1)
    tc2 = E.build_trade_ctx(ctx2, 0, 100.0, E.LONG)
    out2 = E.run_trade(tc2, stop, None, max_hold_bars=5)
    assert out2.exit_bar == 1
    assert out2.exit_price == 94.0   # fills at the close, not the floor


def test_stop_atr_fixed_at_entry():
    """Constructed so True Range = high-low = 2.0 on EVERY bar (each
    bar-to-bar close move stays inside the prior bar's own +-1.0 wick
    band, so the cross-bar TR terms never exceed the plain H-L term) ->
    ATR(14) is EXACTLY 2.0 at every bar (an EWM of a constant series is
    that constant). entry at bar 5 (close=101.0), mult=1.5, long ->
    level = 101.0 - 1.5*2.0 = 98.0. FIXED at entry — must be unchanged
    at a later bar."""
    close = [100, 100.5, 101, 100.7, 101.2, 101.0, 101.5, 101.3, 101.8, 101.6]
    high = [c + 1.0 for c in close]
    low = [c - 1.0 for c in close]
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=2, atr_n=14)
    assert np.allclose(ctx.atr_arr, 2.0)
    tc = E.build_trade_ctx(ctx, 5, 101.0, E.LONG)
    m = E.stop_atr(mult=1.5)
    assert m.level_fn(tc, 5) == 98.0
    assert m.level_fn(tc, 8) == 98.0    # fixed, not trailing


def test_stop_chandelier_ratchets_and_freezes_on_pullback():
    """Constructed so TR=1.0 on every bar (half-range 0.3->0.5 with close
    moves capped at 0.5) -> ATR(14)=1.0 exactly at every bar. mult=2.0.
    highs: [100.5,101.0,101.5,101.5,101.7,101.7,101.9,101.9] (running max
    after each bar, since close = [100,100.5,101,100.7,101.2,100.9,101.4,
    101.1] and high=close+0.5). Expected level = running_max_high - 2.0:
    [98.5, 99.0, 99.5, 99.5(pullback bar3: high=101.2 < running max 101.5,
    so UNCHANGED), 99.7, 99.7(pullback), 99.9, 99.9(pullback)]."""
    close = [100.0, 100.5, 101.0, 100.7, 101.2, 100.9, 101.4, 101.1]
    high = [c + 0.5 for c in close]
    low = [c - 0.5 for c in close]
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=1, atr_n=14)
    assert np.allclose(ctx.atr_arr, 1.0)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.stop_chandelier(mult=2.0)
    expect = [98.5, 99.0, 99.5, 99.5, 99.7, 99.7, 99.9, 99.9]
    got = [m.level_fn(tc, i) for i in range(8)]
    for i, (g, e) in enumerate(zip(got, expect)):
        assert abs(g - e) < 1e-9, f"bar {i}: got {g} expected {e}"
    # monotonic non-decreasing — the ratchet property, explicitly
    assert all(got[i + 1] >= got[i] - 1e-9 for i in range(len(got) - 1))


def test_stop_bollinger():
    """n=5, k=2.0. At bar 7, rolling(5) window = close[3:8] =
    [102,98,103,97,104]. mean=100.8, std(ddof=1, pandas default)~3.114 ->
    upper=100.8+2*std, lower=100.8-2*std. Independently computed with
    numpy and asserted equal to the SeriesCtx's own bands (a correctness
    check on the Bollinger construction), then stop_bollinger('opposite_
    band') for a LONG must equal the LOWER band (the far side from an
    upward-biased entry)."""
    close = [100, 101, 99, 102, 98, 103, 97, 104]
    high = [c + 0.2 for c in close]
    low = [c - 0.2 for c in close]
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=1, boll_n=5, boll_k=2.0)
    window = np.array(close[3:8])
    mid = window.mean()
    std = window.std(ddof=1)
    assert abs(ctx.boll_mid[7] - mid) < 1e-9
    assert abs(ctx.boll_upper[7] - (mid + 2 * std)) < 1e-9
    assert abs(ctx.boll_lower[7] - (mid - 2 * std)) < 1e-9

    tc = E.build_trade_ctx(ctx, 2, close[2], E.LONG)
    m_band = E.stop_bollinger(use="opposite_band")
    m_mid = E.stop_bollinger(use="midline")
    assert abs(m_band.level_fn(tc, 7) - (mid - 2 * std)) < 1e-9
    assert abs(m_mid.level_fn(tc, 7) - mid) < 1e-9


def test_stop_moving_average_ema_and_close_cross():
    """EMA(3), alpha=2/(3+1)=0.5. close=[100,102,101,105,103,107].
    EMA recursion: e0=100, e1=0.5*102+0.5*100=101, e2=0.5*101+0.5*101=101,
    e3=0.5*105+0.5*101=103, e4=0.5*103+0.5*103=103, e5=0.5*107+0.5*103=105.
    style='close': a long's stop fires when CLOSE < EMA. At bar2,
    close=101 == ema=101 -> NOT strictly below, no fire. Construct a
    dedicated cross case separately."""
    close = [100, 102, 101, 105, 103, 107]
    high = [c + 0.1 for c in close]
    low = [c - 0.1 for c in close]
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=1)
    expect_ema = [100.0, 101.0, 101.0, 103.0, 103.0, 105.0]
    assert np.allclose(ctx.ema(3), expect_ema)

    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.stop_moving_average(n=3)
    assert m.level_fn(tc, 5) == 105.0

    # explicit cross: close drops below its EMA -> fires at that close
    close2 = [100, 102, 104, 90]   # bar3 crashes well below its own EMA(3)
    df2 = mkdf(close2, [c + 0.1 for c in close2], [c - 0.1 for c in close2], close2)
    ctx2 = E.build_series_ctx(df2, k=1)
    tc2 = E.build_trade_ctx(ctx2, 0, 100.0, E.LONG)
    out = E.run_trade(tc2, m, None, max_hold_bars=5)
    assert out.exit_bar == 3
    assert out.exit_price == 90.0


def test_stop_breakeven_after_r():
    """base = stop_percentage(5) on entry=100 -> initial stop=95, R=5.
    close is pinned at 100 throughout (only the WICK moves) so MFE is
    driven purely by the high array: highs = [100.5,101.5,103.5,106.0,
    106.5,104.5] -> MFE = high-100 = [0.5,1.5,3.5,6.0,6.5,4.5]. 1R=5, so
    MFE first reaches 1R at bar 3 (6.0>=5). Expect: level=95 for bars
    0-2, level=100 (breakeven) for bars 3-5, and NEVER 95 again even
    though bar5's high (104.5) is below bar4's (106.5) — breakeven only
    ratchets forward, never back."""
    close = [100, 100, 100, 100, 100, 100]
    high = [100.5, 101.5, 103.5, 106.0, 106.5, 104.5]
    low = [c - 0.5 for c in close]
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    base = E.stop_percentage(5.0)
    be = E.stop_breakeven_after_r(base, r_multiple=1.0)
    expect = [95.0, 95.0, 95.0, 100.0, 100.0, 100.0]
    got = [be.level_fn(tc, i) for i in range(6)]
    assert got == expect, got


def test_stop_time_event():
    """n_bars=3: fires (returns True) only once i-entry_idx>=3, never
    before."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.stop_time(3)
    assert [m.event_fn(tc, i) for i in range(6)] == [False, False, False, True, True, True]
    # target_time() is the documented alias, identical mechanic
    mt = E.target_time(3)
    assert [mt.event_fn(tc, i) for i in range(6)] == [False, False, False, True, True, True]


def test_stop_liquidity_pool_swept_pool():
    """Two confirmed lows within 0.5% of each other (95.9 @ confirm=11,
    95.95 @ confirm=16) form a step56 liquidity_pools() pool at their
    mean, 95.925 — the 'pool a sweep-and-reverse long just traded
    against'. At entry=16 (after both confirm), level must equal that
    pool exactly."""
    close = [100, 101, 102, 103, 104, 103, 102, 101, 100, 96.0,
            100, 102, 104, 106, 96.05, 100, 102, 104, 106, 108]
    high = [c + 0.3 for c in close]
    low = [c - 0.3 for c in close]
    low[9] = 95.9
    low[14] = 95.95
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=2, pool_tol_pct=0.5)
    assert abs(ctx.pool_low[16] - 95.925) < 1e-9
    tc = E.build_trade_ctx(ctx, 16, close[16], E.LONG)
    m = E.stop_liquidity_pool()
    assert abs(m.level_fn(tc, 16) - 95.925) < 1e-9


def test_stop_liquidity_pool_none_when_no_pool_yet():
    """Master fixture has no equal-lows cluster at all (its two lows,
    89.5 and 79.5, are nowhere near each other) -> None, not a guess."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 39, 90.0, E.LONG)
    m = E.stop_liquidity_pool()
    assert m.level_fn(tc, 39) is None


# ===========================================================================
# 2. TARGETS
# ===========================================================================

def test_target_fixed_r_composes_with_any_stop():
    """R = the PAIRED stop's own initial distance. stop_percentage(5) on
    entry=100 -> stop=95, R=5. target_fixed_r(r=2) -> 100+2*5=110. Re-pair
    the SAME target constructor with stop_atr instead (R=1.5*ATR=3.0 in
    the constant-TR=2.0 fixture) -> target = 100+2*3.0=106 — proving the
    target genuinely reads whichever stop it's given, not a hardcoded
    number."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop_pct = E.stop_percentage(5.0)
    t1 = E.target_fixed_r(stop_pct, r_multiple=2.0)
    assert t1.level_fn(tc, 0) == 110.0

    close = [100, 100.5, 101, 100.7, 101.2, 101.0]
    high = [c + 1.0 for c in close]
    low = [c - 1.0 for c in close]
    df = mkdf(close, high, low, close)
    ctx2 = E.build_series_ctx(df, k=1, atr_n=14)
    tc2 = E.build_trade_ctx(ctx2, 0, 100.0, E.LONG)
    stop_atr = E.stop_atr(mult=1.5)
    t2 = E.target_fixed_r(stop_atr, r_multiple=2.0)
    assert abs(t2.level_fn(tc2, 0) - 106.0) < 1e-9


def test_target_structure_n_ahead():
    """entry=9 (close=90), long. Favorable (above-entry) high pivots
    confirmed by bar 9: only the minor peak@4 (104.5, confirm=6) — the
    major peak@19 confirms at 21, not yet known. n_ahead=1 -> 104.5."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 9, 90.0, E.LONG)
    m = E.target_structure(n_ahead=1)
    assert m.level_fn(tc, 9) == 104.5


def test_target_liquidity_pool_next_pool_ahead():
    """Two confirmed HIGH pivots within 0.5% of each other (104.1 @
    confirm=11, 104.15 @ confirm=16), entry at bar 19 far BELOW them
    (close=92) -> the nearest favorable cluster ahead = mean(104.1,
    104.15) = 104.125."""
    close = [100, 99, 98, 97, 96, 97, 98, 99, 100, 104.0,
            100, 98, 96, 94, 104.05, 100, 98, 96, 94, 92]
    high = [c + 0.3 for c in close]
    low = [c - 0.3 for c in close]
    high[9] = 104.1
    high[14] = 104.15
    df = mkdf(close, high, low, close)
    ctx = E.build_series_ctx(df, k=2, pool_tol_pct=0.5)
    tc = E.build_trade_ctx(ctx, 19, close[19], E.LONG)
    m = E.target_liquidity_pool(tol_pct=0.5)
    assert abs(m.level_fn(tc, 19) - 104.125) < 1e-9


def test_target_measured_move():
    """entry=39 (close=90), long. Favorable-side pivot as of 39 = the
    most recent above-entry high = major peak@19 (121.0, confirm=21;
    the minor peak@4/104.5 is EARLIER in time and not the 'most recent').
    Protective-side pivot = the most recent below-entry low = trough@34
    (79.5, confirm=36). leg_height = |121.0-79.5| = 41.5.
    extension=1.0 -> target = 90 + 41.5 = 131.5."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 39, 90.0, E.LONG)
    m = E.target_measured_move(extension=1.0)
    assert abs(m.level_fn(tc, 39) - 131.5) < 1e-9


def test_target_trail_only_never_fires():
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    m = E.target_trail_only()
    for i in range(1, 30):
        assert m.level_fn(tc, i) is None


def test_target_opposite_signal():
    """signal flips to -1 (opposite a long) at bar 3 -> fires from bar 3
    onward; a return to +1 at bar 5 does NOT un-fire bar 5 itself (each
    bar is evaluated independently by the engine; run_trade() stops at
    the FIRST firing bar anyway, so only bar 3's firing actually matters
    in a real walk — this test checks the raw per-bar event, and a
    separate assertion below checks the composed walk)."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    signal = np.array([1, 1, 1, -1, -1, 1], dtype=float)
    m = E.target_opposite_signal(signal)
    assert [m.event_fn(tc, i) for i in range(6)] == [False, False, False, True, True, False]

    treat_zero = E.target_opposite_signal(np.array([1, 0, 1]), treat_zero_as_exit=True)
    assert treat_zero.event_fn(tc, 1) is True
    no_treat_zero = E.target_opposite_signal(np.array([1, 0, 1]), treat_zero_as_exit=False)
    assert no_treat_zero.event_fn(tc, 1) is False


# ===========================================================================
# 3. THE GENERIC ENGINE — composition, tie-breaking, gap-through, time-cap
# ===========================================================================

def test_run_trade_stop_wins_tie_and_gap_through():
    """entry=100 long, stop_percentage(5)->stop=95, target_fixed_r(r=1)
    ->target=105. Bar1's OPEN (90) has already gapped through the stop
    (95) BEFORE anything else on that bar happens -> the trade must exit
    at bar1, filled at the OPEN (90), via the stop — even though bar1's
    high (100.5) never even reaches the target, this specific bar
    demonstrates gap-through alone. A second, separate bar (constructed
    without a gap) demonstrates stop-wins-ties when both stop AND target
    are touchable intrabar in the same bar."""
    df = mkdf(
        o=[100, 90, 100, 100, 100],
        h=[100.5, 100.5, 106, 100.5, 100.5],
        l=[99.5, 89.5, 94, 99.5, 99.5],
        c=[100, 100, 100, 100, 100],
    )
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_percentage(5.0)
    target = E.target_fixed_r(stop, 1.0)
    out = E.run_trade(tc, stop, target, max_hold_bars=10)
    assert out.exit_bar == 1
    assert out.exit_price == 90.0
    assert out.reason.startswith("stop:")

    # same-bar BOTH touchable, no gap: low=94<=95(stop), high=106>=105
    # (target) on the SAME bar -> stop must win.
    df2 = mkdf(o=[100, 100], h=[100.5, 106], l=[99.5, 94], c=[100, 100])
    ctx2 = E.build_series_ctx(df2, k=1)
    tc2 = E.build_trade_ctx(ctx2, 0, 100.0, E.LONG)
    out2 = E.run_trade(tc2, stop, target, max_hold_bars=10)
    assert out2.exit_bar == 1
    assert out2.exit_price == 95.0
    assert out2.reason.startswith("stop:")


def test_run_trade_time_cap():
    """Neither stop (95) nor target (105) ever touched within
    max_hold_bars=3 -> force-close at the LAST allowed bar's own close,
    reason 'time_cap'."""
    df = mkdf(o=[100] * 5, h=[100.5] * 5, l=[99.5] * 5, c=[100] * 5)
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_percentage(5.0)
    target = E.target_fixed_r(stop, 1.0)
    out = E.run_trade(tc, stop, target, max_hold_bars=3)
    assert out.exit_bar == 3
    assert out.exit_price == 100.0
    assert out.reason == "time_cap"


def test_run_trade_target_none_is_trail_only():
    """target=None must behave identically to target_trail_only(): only
    the stop (or the time cap) can end the trade."""
    df = mkdf(o=[100] * 4, h=[100.5] * 4, l=[99.5, 99.5, 94, 99.5], c=[100] * 4)
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_percentage(5.0)
    out = E.run_trade(tc, stop, None, max_hold_bars=10)
    assert out.exit_bar == 2
    assert out.exit_price == 95.0
    assert out.reason.startswith("stop:")


def test_run_trade_short_direction_mirrors():
    """direction=SHORT: entry=100, stop_percentage(5) -> stop = 100*(1+
    0.05) = 105 (ABOVE entry). target_fixed_r(r=1) -> 95 (below entry).
    Bar whose high touches 105 first must exit as a stop."""
    df = mkdf(o=[100, 100], h=[100.5, 106], l=[99.5, 99.5], c=[100, 100])
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.SHORT)
    stop = E.stop_percentage(5.0)
    assert stop.level_fn(tc, 0) == 105.0
    target = E.target_fixed_r(stop, 1.0)
    assert target.level_fn(tc, 0) == 95.0
    out = E.run_trade(tc, stop, target, max_hold_bars=5)
    assert out.exit_bar == 1
    assert out.exit_price == 105.0
    assert out.reason.startswith("stop:")


# ===========================================================================
# 4. PARTIAL SCALING
# ===========================================================================

def test_simulate_partial_scale_two_legs():
    """entry=100 long, stop_percentage(5)->stop=95, R=5. r_multiple=1.0,
    frac=0.5 -> partial level = 105. final_target = target_fixed_r(stop,
    r=2.0) -> 110. Bar1's high (106) touches the partial (105) -> leg 1:
    frac=0.5 @ 105, stop moves to breakeven (100); bar1's low (100.2)
    does NOT breach breakeven, so the remainder survives into bar 2,
    whose high (111) touches the final target (110) -> leg 2: frac=0.5 @
    110. Blended price = 0.5*105+0.5*110 = 107.5."""
    df = mkdf(o=[100, 100, 100, 100], h=[100.5, 106, 111, 100.5],
             l=[99.5, 100.2, 100.5, 99.5], c=[100, 100, 100, 100])
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_percentage(5.0)
    final_target = E.target_fixed_r(stop, 2.0)
    out = E.simulate_partial_scale(tc, stop, final_target, max_hold_bars=10,
                                   r_multiple=1.0, frac=0.5)
    assert len(out.legs) == 2
    leg1, leg2 = out.legs
    assert leg1.frac == 0.5 and leg1.price == 105.0 and leg1.bar == 1
    assert leg2.frac == 0.5 and leg2.price == 110.0 and leg2.bar == 2
    assert abs(sum(l.frac for l in out.legs) - 1.0) < 1e-9
    assert abs(out.blended_price() - 107.5) < 1e-9


def test_simulate_partial_scale_stop_before_partial_is_single_leg():
    """Stop (95) is touched at bar1 BEFORE price ever reaches the 1R
    partial level (105) -> a single, full-size stop leg, exactly like a
    plain run_trade() stop-out. No phantom partial leg."""
    df = mkdf(o=[100, 100], h=[100.5, 100.5], l=[99.5, 94], c=[100, 100])
    ctx = E.build_series_ctx(df, k=1)
    tc = E.build_trade_ctx(ctx, 0, 100.0, E.LONG)
    stop = E.stop_percentage(5.0)
    final_target = E.target_fixed_r(stop, 2.0)
    out = E.simulate_partial_scale(tc, stop, final_target, max_hold_bars=10)
    assert len(out.legs) == 1
    assert out.legs[0].frac == 1.0
    assert out.legs[0].price == 95.0
    assert out.legs[0].bar == 1


def test_simulate_partial_scale_none_when_stop_undefined():
    """If the paired stop has no defined level at entry (e.g.
    stop_structure with nothing confirmed yet), there's no R to size the
    partial against -> the function must return None, not silently pick
    an arbitrary distance."""
    ctx = E.build_series_ctx(_master_df(), k=2)
    tc = E.build_trade_ctx(ctx, 5, 103.0, E.LONG)  # no protective pivot by bar 5
    stop = E.stop_structure(k=2, n_back=1)
    out = E.simulate_partial_scale(tc, stop, None, max_hold_bars=10)
    assert out is None


# ===========================================================================
# 5. REGIME CLASSIFIER
# ===========================================================================

def _staircase_uptrend(n_cycles=14):
    """A genuine zigzag: 5 bars up (+1.5 each), 3 bars down (+0.8 each) —
    a REAL pullback (each dip is a fractal local min, each peak a
    fractal local max) that nets upward every cycle, so confirmed swings
    show both higher highs AND higher lows. (A pure straight-line ramp,
    tried first, produces NO fractal pivots at all — a monotonic series
    never contains an interior local extremum — and reads as 'chop', not
    'uptrend'; this zigzag is the fixture that actually exercises
    chart_reader's swing-based structure call.)"""
    vals = [100.0]
    for _ in range(n_cycles):
        for _ in range(5):
            vals.append(vals[-1] + 1.5)
        for _ in range(3):
            vals.append(vals[-1] - 0.8)
    close = np.array(vals)
    return mkdf(close.copy(), close + 0.3, close - 0.3, close)


def test_classify_regime_uptrend():
    df = _staircase_uptrend()
    n = len(df)
    reg = E.classify_regime(df, n - 1)
    assert reg["structure"] == "uptrend"
    assert reg["structure"] in E.VALID_REGIME
    assert reg["volatility"] in E.VALID_VOLATILITY


def test_classify_regime_range_consolidation():
    """Symmetric zigzag with NO net drift (up 5 by +1.5, down 5 by -1.5,
    repeating) -> confirmed swings show neither consistent higher-highs+
    higher-lows nor lower-highs+lower-lows -> range-consolidation."""
    vals = [100.0]
    for _ in range(14):
        for _ in range(5):
            vals.append(vals[-1] + 1.5)
        for _ in range(5):
            vals.append(vals[-1] - 1.5)
    close = np.array(vals)
    df = mkdf(close.copy(), close + 0.3, close - 0.3, close)
    reg = E.classify_regime(df, len(df) - 1)
    assert reg["structure"] == "range-consolidation"


def test_classify_regime_volatility_expanding_and_contracting():
    """Same staircase-uptrend base; widen the FINAL 14 bars' true range
    sharply (expanding) vs widen everything EXCEPT the final 14 bars
    (contracting-into-the-present) — current ATR(14) vs its value
    vol_lookback=14 bars earlier."""
    df = _staircase_uptrend()
    n = len(df)
    h = df["high"].to_numpy().copy()
    l = df["low"].to_numpy().copy()
    c = df["close"].to_numpy()

    h_exp, l_exp = h.copy(), l.copy()
    h_exp[-14:] += np.linspace(0.5, 8, 14)
    l_exp[-14:] -= np.linspace(0.5, 8, 14)
    df_exp = mkdf(c.copy(), h_exp, l_exp, c)
    reg_exp = E.classify_regime(df_exp, n - 1)
    assert reg_exp["volatility"] == "expanding"

    h_con, l_con = h.copy(), l.copy()
    h_con[:-14] += np.linspace(0.2, 6, len(h_con) - 14)
    l_con[:-14] -= np.linspace(0.2, 6, len(l_con) - 14)
    df_con = mkdf(c.copy(), h_con, l_con, c)
    reg_con = E.classify_regime(df_con, n - 1)
    assert reg_con["volatility"] == "contracting"


# ===========================================================================
# 6. DISTANCE REPORTING
# ===========================================================================

def test_describe_distance_blofin_convention():
    """entry=100, stop=99.75 (a 0.25% price move) at leverage=20 ->
    margin_pct = 0.25*20 = 5.0 — the EXACT BLOFIN_API_REFERENCE.md
    example restated in the other direction ('5% of margin = 0.25% price
    move at 20x')."""
    d = E.describe_distance(100.0, 99.75, leverage=20.0)
    assert abs(d["price_pct"] - 0.25) < 1e-9
    assert abs(d["margin_pct"] - 5.0) < 1e-9
    assert d["text"] == "0.25% price = 5.0% of margin at 20x"


# ===========================================================================
# 7. CAUSALITY — THE TRUNCATION PROOF
#    For every method that scans history (the hardest, most lookahead-
#    prone cases), build a SeriesCtx from the FULL dataset and a second
#    one from the dataset truncated to [:decision_idx+1], and assert the
#    level computed AT decision_idx is IDENTICAL between the two. If any
#    method were peeking past its own decision bar, truncating the future
#    away would change its answer. Adapted from step84_blind_drill.py's
#    self_test_causality() (render the same decision point from the full
#    series and a truncated one, assert identical output).
# ===========================================================================

def _causality_dataset():
    rng = np.random.default_rng(11)
    n = 120
    close = 100 + np.cumsum(rng.normal(0, 1.2, n))
    high = close + rng.uniform(0.2, 1.5, n)
    low = close - rng.uniform(0.2, 1.5, n)
    open_ = close + rng.normal(0, 0.4, n)
    return mkdf(open_, high, low, close)


def test_causality_truncation_all_methods():
    df = _causality_dataset()
    decision_idx = 90
    entry_idx = 60
    k = 5

    full_ctx = E.build_series_ctx(df, k=k)
    trunc_df = df.iloc[: decision_idx + 1].reset_index(drop=True)
    trunc_ctx = E.build_series_ctx(trunc_df, k=k)

    entry_price = float(full_ctx.c[entry_idx])
    assert entry_price == float(trunc_ctx.c[entry_idx])   # sanity: same entry bar

    tc_full = E.build_trade_ctx(full_ctx, entry_idx, entry_price, E.LONG)
    tc_trunc = E.build_trade_ctx(trunc_ctx, entry_idx, entry_price, E.LONG)

    stop_atr_at_entry = full_ctx.atr_arr[entry_idx]
    methods = [
        E.stop_structure(k=k, n_back=1),
        E.stop_structure(k=k, n_back=2),
        E.stop_structure_trailing(fallback_pct=5.0),
        E.stop_atr(mult=1.5),
        E.stop_chandelier(mult=3.0),
        E.stop_bollinger(use="opposite_band"),
        E.stop_bollinger(use="midline"),
        E.stop_moving_average(n=20),
        E.stop_liquidity_pool(),
        E.target_structure(n_ahead=1),
        E.target_liquidity_pool(),
        E.target_measured_move(extension=1.0),
    ]
    checked = 0
    for m in methods:
        a = m.level_fn(tc_full, decision_idx)
        b = m.level_fn(tc_trunc, decision_idx)
        if a is None and b is None:
            checked += 1
            continue
        assert a is not None and b is not None, f"{m.name}: one side is None ({a=}, {b=})"
        assert abs(a - b) < 1e-9, f"{m.name}: full={a} truncated={b} DIFFER — lookahead leak"
        checked += 1
    assert checked == len(methods)

    # composed methods too (target_fixed_r reads the stop's level at
    # entry; breakeven reads MFE up to i) — same proof, one level deeper.
    stop = E.stop_atr(mult=1.5)
    composed = [
        E.target_fixed_r(stop, r_multiple=2.0),
        E.stop_breakeven_after_r(stop, r_multiple=1.0),
    ]
    for m in composed:
        a = m.level_fn(tc_full, decision_idx)
        b = m.level_fn(tc_trunc, decision_idx)
        assert (a is None) == (b is None)
        if a is not None:
            assert abs(a - b) < 1e-9, f"{m.name}: {a} vs {b}"


def test_causality_self_test_function():
    """exits.py's own self_test_causality() helper (the module's
    __main__ smoke check) must pass on a fresh random series too."""
    rng = np.random.default_rng(3)
    n = 400
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.normal(0, 0.3, n)
    df = mkdf(open_, high, low, close)
    assert E.self_test_causality(df, decision_idx=300) is True


# ===========================================================================
# runner
# ===========================================================================

TESTS = [
    (name, fn) for name, fn in list(globals().items())
    if name.startswith("test_") and callable(fn)
]


def main():
    print("=" * 78)
    print("test_exits.py — ROUND 99 PART 1: THE EXIT LIBRARY")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
            print("  PASS")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {e}")
            traceback.print_exc()
        except Exception as e:
            failed += 1
            print(f"  ERROR: {e}")
            traceback.print_exc()
    print("\n" + "=" * 78)
    if failed:
        print(f"{failed}/{len(TESTS)} TEST(S) FAILED")
        sys.exit(1)
    else:
        print(f"ALL {len(TESTS)} TESTS PASSED")


if __name__ == "__main__":
    main()
