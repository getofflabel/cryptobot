#!/usr/bin/env python3
"""step471_test_prop_eval.py — the evaluation simulator, checked not trusted.

Run:  python3 -m pytest step471_test_prop_eval.py -q
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import step471_prop_eval as pe
import alex_engine as ae


def _trade(entry_d, exit_d, r, path=None):
    e = pd.Timestamp(entry_d)
    x = pd.Timestamp(exit_d)
    if path is None:
        path = {}
        for d in pd.date_range(e, x, freq="D"):
            path[d] = (min(0.0, r), max(0.0, r))
    return {"instrument": "T", "entry_t": e, "exit_t": x, "entry_d": e,
            "exit_d": x, "r": r, "outcome": "target" if r > 0 else "stop",
            "leverage": 1.0, "path": path}


def _book(rows):
    f = pd.DataFrame(rows).sort_values("entry_t").reset_index(drop=True)
    return f, pe.active_days(f)


def _opts(target, risk=0.01, **kw):
    o = {"balance": pe.ACCOUNT, "daily_cap": pe.DAILY_LOSS_CAP,
         "total_cap": pe.TOTAL_DD_CAP, "target": target, "risk_frac": risk}
    o.update(kw)
    return o


# ------------------------------------------------------------- the two caps
def test_a_single_day_losing_more_than_five_percent_kills_the_account():
    # one trade whose intraday floating loss is 6 R at 1% of the account
    p = {pd.Timestamp("2024-01-01"): (-6.0, 0.0)}
    f, d = _book([_trade("2024-01-01", "2024-01-01", -6.0, p)])
    a = pe.run_account(f, 0, d, _opts(450.0))
    assert a.dead == "daily", a.dead
    assert not a.passed


def test_a_four_percent_day_does_not_kill_it():
    p = {pd.Timestamp("2024-01-01"): (-4.0, 0.0)}
    f, d = _book([_trade("2024-01-01", "2024-01-01", -4.0, p)])
    a = pe.run_account(f, 0, d, _opts(450.0))
    assert a.dead is None
    assert abs(a.balance - (pe.ACCOUNT - 200.0)) < 1e-6


def test_the_total_cap_trails_the_high_water_mark_not_the_start():
    """Up 8% of the account, then down 11% of the account from there. The
    balance is still above where it started, and the account is still dead."""
    rows = [_trade("2024-01-01", "2024-01-01", 8.0),
            _trade("2024-01-08", "2024-01-08", -4.0),
            _trade("2024-01-15", "2024-01-15", -4.0),
            _trade("2024-01-22", "2024-01-22", -4.0)]
    f, d = _book(rows)
    a = pe.run_account(f, 0, d, _opts(10_000.0))   # unreachable target
    assert a.dead == "total", (a.dead, a.balance)


def test_the_static_reading_lets_that_same_account_live():
    rows = [_trade("2024-01-01", "2024-01-01", 8.0),
            _trade("2024-01-08", "2024-01-08", -4.0),
            _trade("2024-01-15", "2024-01-15", -4.0),
            _trade("2024-01-22", "2024-01-22", -4.0)]
    f, d = _book(rows)
    a = pe.run_account(f, 0, d, _opts(10_000.0, trailing=False))
    assert a.dead is None, a.dead


# ------------------------------------------------------------- the target
def test_the_target_needs_the_minimum_trading_days_even_when_the_money_is_there():
    """One trade that clears +9% of the account on day one is NOT a pass."""
    f, d = _book([_trade("2024-01-01", "2024-01-01", 9.5)])
    a = pe.run_account(f, 0, d, _opts(pe.PHASE1_TARGET * pe.ACCOUNT))
    assert not a.passed
    rows = [_trade("2024-01-01", "2024-01-01", 4.0),
            _trade("2024-01-08", "2024-01-08", 4.0),
            _trade("2024-01-15", "2024-01-15", 4.0)]
    f, d = _book(rows)
    a = pe.run_account(f, 0, d, _opts(pe.PHASE1_TARGET * pe.ACCOUNT))
    assert a.passed


def test_the_target_is_scored_on_closed_balance_not_on_a_floating_high():
    """A trade that floats to +10 R and closes at +1 R has not passed."""
    p = {pd.Timestamp("2024-01-01"): (0.0, 10.0),
         pd.Timestamp("2024-01-02"): (0.0, 1.0)}
    rows = [_trade("2024-01-01", "2024-01-02", 1.0, p),
            _trade("2024-01-08", "2024-01-08", 1.0),
            _trade("2024-01-15", "2024-01-15", 1.0)]
    f, d = _book(rows)
    a = pe.run_account(f, 0, d, _opts(pe.PHASE1_TARGET * pe.ACCOUNT))
    assert not a.passed


# --------------------------------------------------------------- causality
def test_no_lookahead_deleting_the_future_cannot_change_a_settled_answer():
    """The account dies on 2024-01-01. Everything after it is deleted and the
    answer must be identical."""
    p = {pd.Timestamp("2024-01-01"): (-6.0, 0.0)}
    early = _trade("2024-01-01", "2024-01-01", -6.0, p)
    f1, d1 = _book([early])
    f2, d2 = _book([early, _trade("2024-06-01", "2024-06-01", 20.0)])
    a1 = pe.run_account(f1, 0, d1, _opts(450.0))
    a2 = pe.run_account(f2, 0, d2, _opts(450.0))
    assert (a1.dead, a1.passed, a1.balance) == (a2.dead, a2.passed, a2.balance)


def test_sizing_uses_the_balance_as_it_stood_not_as_it_ends():
    """Two winners. The second is sized off the balance AFTER the first."""
    rows = [_trade("2024-01-01", "2024-01-01", 1.0),
            _trade("2024-01-08", "2024-01-08", 1.0),
            _trade("2024-01-15", "2024-01-15", 1.0)]
    f, d = _book(rows)
    a = pe.run_account(f, 0, d, _opts(10_000.0))
    expect = pe.ACCOUNT
    for _ in range(3):
        expect += 0.01 * expect
    assert abs(a.balance - expect) < 1e-6


# --------------------------------------------------------- his own rules
def test_his_two_position_cap_is_enforced_on_the_shared_account():
    rows = [_trade("2024-01-01", "2024-02-01", 1.0),
            _trade("2024-01-02", "2024-02-01", 1.0),
            _trade("2024-01-03", "2024-02-01", 1.0)]
    f = pd.DataFrame(rows).sort_values("entry_t").reset_index(drop=True)
    g = pe.gate_concurrency(f)
    assert len(g) == pe.MAX_CONCURRENT == 2


def test_the_rules_taken_from_him_carry_his_numbers():
    assert pe.ACCOUNT == 5_000.0
    assert pe.PHASE1_TARGET == 0.09      # "9% for your step one"
    assert pe.PHASE2_TARGET == 0.05      # "5% for step two"
    assert pe.SPLIT == 0.90              # "90% profit split"
    assert pe.TICKET == 50.0
    assert pe.PAYOUT_CAP == 0.10         # founder: "10% on two phase"


def test_the_two_caps_are_declared_as_OURS_in_the_source():
    src = open(os.path.join(pe.REPO, "step471_prop_eval.py")).read()
    i = src.index("DAILY_LOSS_CAP = ")
    j = src.index("TOTAL_DD_CAP = ")
    assert "OURS" in src[i:i + 200]
    assert "OURS" in src[j:j + 200]


# ------------------------------------------------------------ the R record
def test_R_is_scale_free_which_is_what_lets_the_record_be_replayed_at_5000():
    """The claim the whole file rests on: a trade's R does not depend on the
    account it was sized against. Same trade, two account sizes, same R."""
    frames = ae.load("EUR_USD")
    a = ae.run_instrument("EUR_USD", "2024-01-01", "2024-07-01",
                          cfg=ae.dumb_config_for("EUR_USD"), frames=frames,
                          shared={}, mode="dumb")
    b = ae.run_instrument("EUR_USD", "2024-01-01", "2024-07-01",
                          cfg=ae.dumb_config_for("EUR_USD",
                                                 account_start=5_000.0),
                          frames=frames, shared={}, mode="dumb")
    ra = [t.r_multiple for t in a["trades"] if t.outcome in ("stop", "target")]
    rb = [t.r_multiple for t in b["trades"] if t.outcome in ("stop", "target")]
    assert len(ra) == len(rb) and len(ra) > 3
    assert np.allclose(ra, rb, atol=1e-9)


def test_the_floating_path_bottoms_out_at_the_stop_and_never_below():
    """A path's worst R must not be more negative than -1 minus the cost."""
    cache: dict = {}
    f = pe.build_trades(pe.BOOKS[1], cache)      # EUR/USD alone
    assert len(f) > 50
    for _, row in f.iterrows():
        lo = min(v[0] for v in row["path"].values())
        assert lo >= -1.6, (row["entry_t"], lo)
        assert lo <= row["r"] + 1e-9


def test_gold_at_a_prop_firm_is_charged_the_CFD_spread_not_blofin():
    assert pe.OANDA_XAU_ROUND_TRIP < ae.round_trip_cost_share(ae.GOLD)


def test_this_file_places_no_order_and_imports_no_venue_client():
    """Comments may NAME a venue. Code may not reach one."""
    src = open(os.path.join(pe.REPO, "step471_prop_eval.py")).read()
    code = "\n".join(ln for ln in src.splitlines()
                     if not ln.lstrip().startswith("#"))
    for bad in ("import oanda", "import blofin", "import venue",
                "import requests", "import urllib", "place_order",
                "create_order", "submit_order", ".post(", ".put("):
        assert bad not in code, bad
    assert "import alex_engine" in code
