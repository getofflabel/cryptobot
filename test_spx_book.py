"""
test_spx_book.py — offline tests for spx_book.py, THE S&P PAPER BOOK
(round-60 sealed RSI2 dip-buy edge, run on an internal virtual ledger — see
spx_book.py's module docstring for why this book never places a real
order). NO NETWORK: yfinance is never called — every test injects a fake
`fetch` callable returning hand-built synthetic OHLC data, and every
Telegram/log/state side effect on step5_paper_trade is monkeypatched to a
no-op (or a list-capturing spy), exactly like test_gold_book.py.

ORACLE: spx_book._rsi / spx_book._sma ARE the deployed strategy (Wilder's
RSI + a plain rolling mean, the R60 sealed shape, ported verbatim from
step70_replay.rsi2_dipbuy_sealed's own oracle). Rather than trust that
implementation blindly, test (a) hand-traces the RSI recursion for two tiny
series (worked by hand in the comments) AND cross-checks against a second,
independent, pure-Python (no pandas) re-implementation of the same Wilder
recursion — two different code paths, one formula, same answer.

Six intents (the task's lettered list, re-lettered a-f to match this file's
own numbering):
  a) signal math on synthetic series — hand-verified RSI2/SMA cases, plus
     a full 257-bar dip-buy/recovery scenario's entry/exit flags
  b) idempotency — same bar processed twice = no duplicate trade/side effects
  c) entry/exit ledger math incl. fees — hand-computed against the sizing
     formula (95% alloc x 4x leverage) and 1bp/leg fee model
  d) the never-orders guard — a source-scan proving no order call exists
     anywhere in spx_book.py, AND a runtime check that passing an
     order-capable object raises immediately, before any state mutation
  e) dry mode — zero state writes / zero notify / zero log_event, in both
     the would-enter and the would-hold cases
  f) crash-abort — the emergency 10%-off-peak ledger insurance (documented
     in spx_book.py as being BEYOND the sealed config, which has none)
     fires exactly once per drawdown episode and re-arms on recovery

Run with:  python3 test_spx_book.py
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import spx_book
import step5_paper_trade as s5


def _noop(*a, **kw):
    pass


# ---------------------------------------------------------------------------
# fixed "now" for the live-path due-check (weekday, >= 21:30 UTC) — self-
# checking so a bad hardcoded date can never silently break every test
# ---------------------------------------------------------------------------

DUE_NOW = datetime(2026, 7, 20, 21, 45, tzinfo=timezone.utc)
assert DUE_NOW.weekday() < 5, "DUE_NOW must be a weekday for the live-path tests"
assert (DUE_NOW.hour, DUE_NOW.minute) >= (spx_book.DUE_HOUR_UTC,
                                          spx_book.DUE_MINUTE_UTC)

NOT_DUE_NOW = datetime(2026, 7, 20, 10, 0, tzinfo=timezone.utc)   # same day, too early
WEEKEND_NOW = datetime(2026, 7, 18, 22, 0, tzinfo=timezone.utc)   # Saturday
assert WEEKEND_NOW.weekday() >= 5


# ---------------------------------------------------------------------------
# independent (pure-python, no pandas) Wilder RSI cross-check oracle
# ---------------------------------------------------------------------------

def _manual_wilder_rsi_last(closes, n):
    """Hand-traceable recursion: alpha=1/n, seeded at the first delta,
    y[t] = alpha*x[t] + (1-alpha)*y[t-1] — matches pandas' ewm(adjust=False)
    semantics exactly, but computed with a plain python loop, not pandas,
    so this is a genuinely separate code path from spx_book._rsi. Returns
    only the LAST value (None if undefined, i.e. no down-move has ever
    occurred yet)."""
    alpha = 1.0 / n
    u_prev = d_prev = None
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        u = max(delta, 0.0)
        d = max(-delta, 0.0)
        if u_prev is None:
            u_prev, d_prev = u, d
        else:
            u_prev = alpha * u + (1 - alpha) * u_prev
            d_prev = alpha * d + (1 - alpha) * d_prev
    if d_prev is None or d_prev == 0:
        return None if d_prev is None else 0.0 if u_prev == 0 else float("inf")
    rs = u_prev / d_prev
    return 100 - 100 / (1 + rs)


def build_dipbuy_series():
    """A 257-bar synthetic SPY series: a clean linear uptrend (150 -> 250,
    so SMA200 always trails well below price — a textbook 'long uptrend
    holds' backdrop), a 2-day -1.5%/-1.5% panic dip at bars 254-255, then a
    sharp bounce to 250.0 at bar 256.

    INDEPENDENTLY VERIFIED (both by the manual recursion above and by a
    throwaway numeric check during authoring — the values below are pinned
    to 2 decimal places so a regression in spx_book._rsi/_sma would fail
    this test):
        bar 254 (1st down day):  close 243.97, RSI2  9.41 -> NO entry yet
        bar 255 (2nd down day):  close 240.31, RSI2  3.38 -> ENTRY
                                  (SMA200 ~210.0, price still way above it)
        bar 256 (bounce to 250): close 250.00, RSI2 78.01, SMA5 245.85
                                  -> EXIT (both legs true: RSI2>65 AND
                                  close>SMA5 — the reason branch in
                                  spx_book picks sma5_reclaim first)
    """
    n = 257
    base = np.linspace(150.0, 250.0, 260)[:n]
    closes = base.copy()
    closes[254] = closes[253] * 0.985
    closes[255] = closes[254] * 0.985
    closes[256] = 250.0
    ts = pd.bdate_range(start="2015-01-01", periods=n)
    return pd.DataFrame({"timestamp": ts, "open": closes, "high": closes,
                         "low": closes, "close": closes})


# ---------------------------------------------------------------------------
# a) signal math — hand-verified RSI2/SMA cases
# ---------------------------------------------------------------------------

def test_a_signal_math_hand_verified():
    # 1) simple 6-bar uptrend, hand-traced by hand (alpha=0.5):
    #      delta:  _   +2   -1   +4   -1   +6
    #      up:     _    2    0    4    0    6      down:  _  0  1  0  1  0
    #      u_ewm:  _    2   1.0  2.5  1.25 3.625    d_ewm: _  0  0.5 0.25 0.625 0.3125
    #    RSI(last) = 100 - 100/(1 + 3.625/0.3125) = 100 - 100/12.6 = 92.0635
    closes6 = [100.0, 102.0, 101.0, 105.0, 104.0, 110.0]
    r = spx_book._rsi(pd.Series(closes6), 2)
    assert abs(r.iloc[-1] - 92.063492) < 1e-4, r.iloc[-1]
    manual = _manual_wilder_rsi_last(closes6, 2)
    assert abs(manual - r.iloc[-1]) < 1e-9, (manual, r.iloc[-1])

    # 2) monotonic decline -> up-EWM is exactly zero the entire way, so
    #    RSI2 == 0.0 exactly (rs = 0/positive = 0 -> RSI = 100-100/1 = 0)
    closes_down = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0]
    r_down = spx_book._rsi(pd.Series(closes_down), 2)
    assert r_down.iloc[-1] == 0.0, r_down.iloc[-1]
    assert _manual_wilder_rsi_last(closes_down, 2) == 0.0

    # 3) monotonic rise -> down-EWM is exactly zero -> RSI2 undefined
    #    (NaN), by spx_book._rsi's own div-by-zero guard (down.replace(0,
    #    nan)) — never silently reported as a false 100
    closes_up = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    r_up = spx_book._rsi(pd.Series(closes_up), 2)
    assert pd.isna(r_up.iloc[-1]), r_up.iloc[-1]

    # 4) SMA is a plain rolling mean — checked directly against np.mean
    s = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0])
    sma5 = spx_book._sma(s, 5)
    assert abs(sma5.iloc[-1] - np.mean([30.0, 40.0, 50.0, 60.0, 70.0])) < 1e-9
    sma3 = spx_book._sma(s, 3)
    assert abs(sma3.iloc[2] - np.mean([10.0, 20.0, 30.0])) < 1e-9

    # 5) the full 257-bar dip-buy/recovery scenario (see build_dipbuy_series)
    d = build_dipbuy_series()
    dec254 = spx_book._decision(d.iloc[:255].reset_index(drop=True))
    dec255 = spx_book._decision(d.iloc[:256].reset_index(drop=True))
    dec256 = spx_book._decision(d.iloc[:257].reset_index(drop=True))

    assert abs(dec254["rsi2"] - 9.414) < 0.01, dec254["rsi2"]
    assert dec254["entry_signal"] is False, "1st down day alone must not fire"

    assert abs(dec255["rsi2"] - 3.3808) < 0.01, dec255["rsi2"]
    assert dec255["entry_signal"] is True, "2nd down day, RSI2<5, price>SMA200"
    assert dec255["close"] > dec255["sma200"]

    assert dec256["rsi2"] > spx_book.RSI_EXIT_MIN, dec256["rsi2"]
    assert dec256["close"] > dec256["sma5"], (dec256["close"], dec256["sma5"])
    assert dec256["exit_signal"] is True

    print(f"  [a] OK — RSI2 hand-cases match (92.0635 up-case, 0.0 down-"
          f"case, NaN up-only-case); dip-buy scenario: day254 RSI2="
          f"{dec254['rsi2']:.2f} no-entry, day255 RSI2={dec255['rsi2']:.2f} "
          f"ENTRY, day256 RSI2={dec256['rsi2']:.2f} EXIT")


# ---------------------------------------------------------------------------
# shared rig
# ---------------------------------------------------------------------------

STARTING_EQUITY = 2000.0


def install_offline():
    s5.notify = _noop
    s5.log_event = _noop
    s5.save_state = _noop
    s5.CLOUD_STATE = False


class Spy:
    """Captures calls to a step5_paper_trade function while still no-op'ing
    it (so tests can assert on WHAT was sent, not just count)."""
    def __init__(self):
        self.calls = []

    def __call__(self, *a, **kw):
        self.calls.append((a, kw))


class FakeFetch:
    """Returns a growing prefix of a full synthetic frame — day_idx bars
    'available', simulating the book watching a real feed one new daily
    bar at a time. Mirrors test_gold_book.FakeLiveFeed's day_idx knob."""
    def __init__(self, full_df: pd.DataFrame, day_idx: int):
        self.full = full_df
        self.day_idx = day_idx

    def __call__(self):
        return self.full.iloc[:self.day_idx + 1].reset_index(drop=True)


def expected_shares(equity: float, price: float) -> float:
    notional = equity * spx_book.ALLOC_FRAC * spx_book.LEVERAGE
    return notional / price


def expected_fees(entry_price: float, exit_price: float, shares: float) -> float:
    return ((entry_price * spx_book.FEE_BPS_PER_LEG
            + exit_price * spx_book.FEE_BPS_PER_LEG) * shares / 10_000)


def make_state() -> dict:
    return {}


def new_rig():
    install_offline()
    full = build_dipbuy_series()
    state = make_state()
    return full, state


# ---------------------------------------------------------------------------
# b) idempotency — same bar processed twice = no-op the second time
# ---------------------------------------------------------------------------

def test_b_idempotency():
    full, state = new_rig()
    notify_spy, log_spy, save_spy = Spy(), Spy(), Spy()
    s5.notify, s5.log_event, s5.save_state = notify_spy, log_spy, save_spy

    fetch = FakeFetch(full, 255)     # entry-day bar available
    r1 = spx_book.run_spx_book(None, state, dry=False, now=DUE_NOW, fetch=fetch)
    assert r1["action"] == "entered", r1
    assert state["spx_book"]["open_trade"] is not None
    calls_after_first = (len(notify_spy.calls), len(log_spy.calls), len(save_spy.calls))
    assert calls_after_first[0] >= 1, "entry should have notified"

    # second call, SAME bar still the newest available -> must be a clean
    # no-op: no new trade, no new notify/log/save
    r2 = spx_book.run_spx_book(None, state, dry=False, now=DUE_NOW, fetch=fetch)
    assert r2["action"] == "noop_already_processed", r2
    assert len(notify_spy.calls) == calls_after_first[0], "must not re-notify"
    assert len(log_spy.calls) == calls_after_first[1], "must not re-log"
    assert len(save_spy.calls) == calls_after_first[2], "must not re-save"
    assert state["spx_book"]["open_trade"]["entry_date"] == r1["bar_date"]

    # also idempotent when NOT due (weekend) / too early — pure no-op,
    # never even reads the book
    r3 = spx_book.run_spx_book(None, state, dry=False, now=NOT_DUE_NOW, fetch=fetch)
    assert r3["action"] == "not_due", r3
    r4 = spx_book.run_spx_book(None, state, dry=False, now=WEEKEND_NOW, fetch=fetch)
    assert r4["action"] == "not_due", r4

    print(f"  [b] OK — 2nd call on the same bar = noop_already_processed, "
          f"0 extra side effects; off-hours/weekend calls = not_due")


# ---------------------------------------------------------------------------
# c) entry/exit ledger math incl. fees
# ---------------------------------------------------------------------------

def test_c_entry_exit_ledger_math():
    full, state = new_rig()
    s5.notify, s5.log_event, s5.save_state = _noop, _noop, _noop

    fetch = FakeFetch(full, 255)      # entry day
    r_enter = spx_book.run_spx_book(None, state, dry=False, now=DUE_NOW, fetch=fetch)
    assert r_enter["action"] == "entered", r_enter
    sb = state["spx_book"]
    entry_price = sb["open_trade"]["entry_price"]
    exp_shares = expected_shares(STARTING_EQUITY, r_enter["close"])
    # open_trade["shares"] is stored rounded to 4dp (see run_spx_book) —
    # compare at that precision, not full float precision
    assert abs(sb["open_trade"]["shares"] - round(exp_shares, 4)) < 1e-6, (
        sb["open_trade"]["shares"], exp_shares)
    # sizing formula: 95% alloc x 4x leverage on the book's OWN ledger,
    # never the shared BloFin ledger
    assert spx_book.ALLOC_FRAC == 0.95 and spx_book.LEVERAGE == 4.0
    exp_notional = STARTING_EQUITY * 0.95 * 4.0
    assert abs(sb["open_trade"]["notional"] - exp_notional) < 1.0, (
        sb["open_trade"]["notional"], exp_notional)

    fetch.day_idx = 256               # exit/bounce day
    r_exit = spx_book.run_spx_book(None, state, dry=False, now=DUE_NOW, fetch=fetch)
    assert r_exit["action"] == "exited", r_exit
    assert sb["open_trade"] is None

    exit_price = r_exit["close"]
    shares = round(exp_shares, 4)   # matches the stored, rounded open_trade shares
    gross = shares * (exit_price - entry_price)
    fees = expected_fees(entry_price, exit_price, shares)
    exp_realized = round(gross - fees, 2)
    assert abs(r_exit["pnl"] - exp_realized) < 0.01, (r_exit["pnl"], exp_realized)
    assert abs(sb["virtual_equity"] - round(STARTING_EQUITY + exp_realized, 2)) < 0.01
    assert sb["n"] == 1 and sb["wins"] == 1, "the bounce trade is a winner"
    assert sb["trades"][-1]["pnl"] == r_exit["pnl"]
    assert sb["trades"][-1]["reason"] == "sma5_reclaim"

    # this book's ledger must be its OWN, isolated key — never touching the
    # shared BloFin fields sync_ledger_to_account/book_ledger read
    assert "virtual_equity" not in state or "open_trade" not in state, (
        "spx_book must never write the SHARED top-level open_trade/"
        "virtual_equity keys other books read")

    print(f"  [c] OK — entry {shares:.3f} sh @ ${entry_price:.2f} "
          f"(${exp_notional:,.0f} notional), exit @ ${exit_price:.2f}, "
          f"fees ${fees:.4f}, pnl ${exp_realized:+.2f}, ledger "
          f"${sb['virtual_equity']:,.2f}")


# ---------------------------------------------------------------------------
# d) the never-orders guard
# ---------------------------------------------------------------------------

FORBIDDEN_SUBSTRINGS = [
    "market_order(", "place_tpsl(", "cancel_tpsl(", "ensure_leverage(",
    ".buy(", ".sell(", "BlofinDemoPrivate(", "private.", "net_position_contracts(",
]


def test_d_never_orders_guard():
    # (i) STATIC source scan: no order-placing call exists anywhere in the
    #     deployed file, full stop.
    with open("spx_book.py") as f:
        src = f.read()
    for bad in FORBIDDEN_SUBSTRINGS:
        assert bad not in src, f"forbidden order-call substring found: {bad!r}"

    # (ii) RUNTIME guard: an order-capable object passed as live_feed_unused
    #      must raise IMMEDIATELY, before any state read/write/notify.
    full, state = new_rig()
    notify_spy, log_spy, save_spy = Spy(), Spy(), Spy()
    s5.notify, s5.log_event, s5.save_state = notify_spy, log_spy, save_spy

    class FakeOrderCapable:
        def market_order(self, *a, **kw):
            raise AssertionError("should never be called")

    fetch = FakeFetch(full, 255)
    threw = False
    try:
        spx_book.run_spx_book(FakeOrderCapable(), state, dry=False,
                              now=DUE_NOW, fetch=fetch)
    except AssertionError as e:
        threw = True
        assert "simulation-only" in str(e) or "NEVER" in str(e), str(e)
    assert threw, "guard must raise when given an order-capable client"
    assert state == {}, "guard must fire BEFORE any state mutation"
    assert len(notify_spy.calls) == 0
    assert len(log_spy.calls) == 0
    assert len(save_spy.calls) == 0

    # also true in dry mode — the guard is unconditional
    threw = False
    try:
        spx_book.run_spx_book(FakeOrderCapable(), state, dry=True,
                              now=DUE_NOW, fetch=fetch)
    except AssertionError:
        threw = True
    assert threw, "guard must fire in dry mode too"

    # a plain None (the documented call convention) and an inert object
    # must NOT trip the guard
    class Inert:
        pass
    spx_book.run_spx_book(None, {}, dry=True, now=DUE_NOW, fetch=fetch)
    spx_book.run_spx_book(Inert(), {}, dry=True, now=DUE_NOW, fetch=fetch)

    print(f"  [d] OK — source scan clean of {len(FORBIDDEN_SUBSTRINGS)} "
          f"forbidden order-call substrings; runtime guard raises "
          f"immediately (zero state/notify/log/save) for an order-capable "
          f"client, in both live and dry mode; None/inert clients pass")


# ---------------------------------------------------------------------------
# e) dry mode — zero writes
# ---------------------------------------------------------------------------

def test_e_dry_mode_zero_side_effects():
    full, _ = new_rig()
    notify_spy, log_spy, save_spy = Spy(), Spy(), Spy()
    s5.notify, s5.log_event, s5.save_state = notify_spy, log_spy, save_spy

    # would-enter case (day 255)
    state_a = {}
    import copy
    before_a = copy.deepcopy(state_a)
    fetch_a = FakeFetch(full, 255)
    r_a = spx_book.run_spx_book(None, state_a, dry=True, now=DUE_NOW, fetch=fetch_a)
    assert r_a["action"] == "would_enter", r_a
    assert state_a == before_a, "dry mode must never write state"
    exp_shares = expected_shares(STARTING_EQUITY, r_a["close"])
    assert abs(r_a["shares"] - exp_shares) < 1e-6

    # would-hold case: pre-seed an open trade "by hand" (never via a live
    # call) and confirm dry mode still writes nothing
    state_b = {"spx_book": {"virtual_equity": STARTING_EQUITY,
                            "peak_equity": STARTING_EQUITY,
                            "open_trade": {"entry_date": "2015-01-01",
                                          "entry_price": 100.0, "shares": 10.0,
                                          "notional": 1000.0},
                            "last_bar_date": "2000-01-01", "trades": [],
                            "realized_pnl_total": 0.0, "n": 0, "wins": 0,
                            "crash_alerted": False}}
    before_b = copy.deepcopy(state_b)
    fetch_b = FakeFetch(full, 254)     # exit_signal False on day 254
    r_b = spx_book.run_spx_book(None, state_b, dry=True, now=DUE_NOW, fetch=fetch_b)
    assert r_b["action"] == "would_hold", r_b
    assert state_b == before_b, "dry mode must never write state (holding case)"

    assert len(notify_spy.calls) == 0, "dry mode must never notify"
    assert len(log_spy.calls) == 0, "dry mode must never log"
    assert len(save_spy.calls) == 0, "dry mode must never save"

    print(f"  [e] OK — dry would_enter ({r_a['shares']:.3f} sh est.) and "
          f"dry would_hold both leave state byte-identical, 0 notify/log/"
          f"save calls")


# ---------------------------------------------------------------------------
# f) crash-abort — fires once per >=10%-off-peak episode, re-arms on recovery
# ---------------------------------------------------------------------------

def test_f_crash_abort():
    notify_spy, log_spy, save_spy = Spy(), Spy(), Spy()
    s5.notify, s5.log_event, s5.save_state = notify_spy, log_spy, save_spy

    sb = spx_book._fresh_book()
    state = {"spx_book": sb}

    # a big loser: 20 sh, entry 100 -> exit 70 (-30%), well past -10% of
    # a $2000 ledger on its own
    t = {"entry_date": "2015-01-01", "entry_price": 100.0, "shares": 20.0}
    realized = spx_book._finish_exit(state, sb, t, 70.0, "2015-01-02", "rsi2_snapback")
    assert realized < -200.0, realized       # well past 10% of 2000
    assert sb["crash_alerted"] is True
    crash_notifies = [c for c in notify_spy.calls
                      if "crash" in c[0][0].lower() or "10%" in c[0][1]]
    assert len(crash_notifies) == 1, notify_spy.calls
    assert "paper" in crash_notifies[0][0][1].lower()

    # a SECOND loss while still deep in the hole must NOT re-fire (no spam)
    t2 = {"entry_date": "2015-01-03", "entry_price": 70.0, "shares": 5.0}
    spx_book._finish_exit(state, sb, t2, 68.0, "2015-01-04", "rsi2_snapback")
    crash_notifies2 = [c for c in notify_spy.calls
                       if "crash" in c[0][0].lower() or "10%" in c[0][1]]
    assert len(crash_notifies2) == 1, "must not re-alert while still in the same episode"

    # recovery back within 5% of peak re-arms the alert
    t3 = {"entry_date": "2015-01-05", "entry_price": 68.0, "shares": 5.0}
    spx_book._finish_exit(state, sb, t3, 500.0, "2015-01-06", "sma5_reclaim")
    assert sb["crash_alerted"] is False, "must re-arm after recovering near peak"

    # a fresh breach after re-arming fires again
    sb["peak_equity"] = 10_000.0
    sb["virtual_equity"] = 10_000.0
    t4 = {"entry_date": "2015-01-07", "entry_price": 100.0, "shares": 200.0}
    spx_book._finish_exit(state, sb, t4, 40.0, "2015-01-08", "rsi2_snapback")
    assert sb["crash_alerted"] is True
    crash_notifies3 = [c for c in notify_spy.calls
                       if "crash" in c[0][0].lower() or "10%" in c[0][1]]
    assert len(crash_notifies3) == 2, "a NEW episode after re-arming must alert again"

    print(f"  [f] OK — crash-abort fires once per >=10%-off-peak episode "
          f"(1st breach alerted, 2nd loss in same episode silent, re-armed "
          f"on recovery, fired again on a fresh breach)")


TESTS = [
    ("a) signal math — hand-verified RSI2/SMA cases", test_a_signal_math_hand_verified),
    ("b) idempotency — same bar twice = no-op, off-hours = not_due", test_b_idempotency),
    ("c) entry/exit ledger math incl. fees", test_c_entry_exit_ledger_math),
    ("d) never-orders guard (source scan + runtime)", test_d_never_orders_guard),
    ("e) dry mode — zero writes", test_e_dry_mode_zero_side_effects),
    ("f) crash-abort — fires at -10%, re-arms on recovery", test_f_crash_abort),
]


def main():
    print("=" * 78)
    print("test_spx_book.py — THE S&P PAPER BOOK (round-60 sealed RSI2 dip-buy)")
    print("=" * 78)
    failed = 0
    for name, fn in TESTS:
        print(f"\n-- {name} --")
        try:
            fn()
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
