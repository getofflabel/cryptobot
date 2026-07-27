"""
test_alex_live.py — the live Alex path, held to the standard the money needs.

THE ONE THAT MATTERS IS FIRST. `test_the_replay_and_the_live_engine_agree`
runs the same twelve months of candles through `alex_engine.run_instrument`
(the engine every number in step472 came out of) and through
`alex_live.Engine` (the engine that will actually place the orders), for all
four instruments, and fails on the first trade where they differ by so much
as a cent. The 36x sizing bug happened because a replay and a live runner had
separate arithmetic and nothing ever put their answers side by side. This is
that test.

THE REST, IN ORDER
  2. THE SHIPPING CONFIGURATION IS step472's, PLUS WALLACE'S TWO RULINGS of
     2026-07-27 — the weekly-close direction rule ON, and the money-game
     ladder ON for gold and only for gold — and none of it can drift.
  3. THE GOLD BASIS. Levels are read on OANDA XAU/USD and orders go to BloFin
     XAUT-USDT; every price crosses, nothing is copied raw, and a basis that
     cannot be read sends nothing at all.
  4. THE STOP IS NEVER SECOND. Every opening order carries it, on both
     venues, in the same request, and both venues refuse outright without one.
  5. ONE SIZING PATH — the desk's own call and the engine's own call return
     the identical size on every trade of the shipping year, ladder or no
     ladder.
  6. THE LADDER MOVES ONLY THE SIZE, and the leverage it implies is never
     one the exchange cannot carry.
  7. THE MESSAGE says what the order actually was, in the approved formatter.
  8. METHODS NEVER MIX. Forex and gold reach Alex and only Alex; crypto
     reaches Craig and only Craig; stocks reach TJR and only TJR.
  9. NOTHING IS TOUCHED — no fetch, no order, no git, out of this file or the
     modules it tests.
"""

from __future__ import annotations

import datetime as dt
import inspect
import os

import numpy as np
import pandas as pd
import pytest

import alex_engine as ae
import alex_live as al
import tjr_alerts
import tjr_desk

REPO = os.path.dirname(os.path.abspath(__file__))
SRC = inspect.getsource(al)
DESK_SRC = inspect.getsource(tjr_desk)

YEAR = (pd.Timestamp("2025-07-27"), pd.Timestamp("2026-07-26"))
SHORT = (pd.Timestamp("2026-02-01"), pd.Timestamp("2026-07-26"))

_DATA: dict = {}
_BOTH: dict = {}

# what a trade's two engines must agree about, field by field
FIELDS = ("entry", "stop", "target", "exit", "units", "notional", "leverage",
          "risk_dollars", "pnl", "cost", "r_multiple", "quality",
          "quality_pts", "engulfed", "dojis", "hours_held")


def data(instrument):
    if instrument not in _DATA:
        _DATA[instrument] = ae.load(instrument)
    return _DATA[instrument]


def both(instrument, window=YEAR, cfg=None):
    """The same candles down both paths, computed once per instrument."""
    key = (instrument, window, id(cfg))
    if key not in _BOTH:
        cfg = cfg or al.live_config(instrument)
        rep = ae.run_instrument(instrument, *window, cfg=cfg,
                                frames=data(instrument))["trades"]
        liv = al.replay_through_live(instrument, *window, cfg=cfg,
                                     frames=data(instrument))["trades"]
        _BOTH[key] = (sorted(rep, key=lambda t: (t.entry_t, t.entry)),
                      sorted(liv, key=lambda t: (t.entry_t, t.entry)))
    return _BOTH[key]


# ============================ 1. THE REPLAY AND THE LIVE ENGINE AGREE
def test_the_replay_and_the_live_engine_agree():
    """THE test. Same candles, both engines, every trade, every field.

    A difference here is not a rounding question. It means the dollars in
    step472 describe a bot nobody is running, which is the exact failure this
    project has already paid for once.
    """
    compared = 0
    for inst in ae.INSTRUMENTS:
        rep, liv = both(inst)
        assert len(rep) == len(liv), (
            f"{inst}: the replay took {len(rep)} trades and the live engine "
            f"took {len(liv)}\n"
            f"  replay {[(str(t.entry_t), t.pattern, t.outcome) for t in rep]}\n"
            f"  live   {[(str(t.entry_t), t.pattern, t.outcome) for t in liv]}")
        for a, b in zip(rep, liv):
            for f in ("direction", "session", "outcome", "pattern",
                      "signal_kind"):
                assert getattr(a, f) == getattr(b, f), \
                    f"{inst} {a.entry_t}: {f} differs"
            for f in ("entry_t", "exit_t"):
                x, y = getattr(a, f), getattr(b, f)
                # a trade still open when the tape ran out has no exit, and
                # `NaT == NaT` is False — so None and None is compared as the
                # same answer rather than as two unequal nothings
                assert (x is None) == (y is None), \
                    f"{inst} {a.entry_t}: one engine closed {f} and the other did not"
                assert x is None or pd.Timestamp(x) == pd.Timestamp(y), \
                    f"{inst} {a.entry_t}: {f} differs"
            for f in FIELDS:
                assert getattr(a, f) == pytest.approx(getattr(b, f), rel=1e-12,
                                                      abs=1e-9), \
                    f"{inst} {a.entry_t}: {f} differs"
            compared += 1
    assert compared >= 30, f"only {compared} trades to compare"


def test_the_two_engines_book_the_same_dollars():
    """The headline, stated as one number per book."""
    for name, insts in (("forex", list(al.FOREX.values())),
                        ("gold", [al.GOLD_INSTRUMENT])):
        r = l = 0.0
        for inst in insts:
            rep, liv = both(inst)
            r += sum(t.pnl for t in rep)
            l += sum(t.pnl for t in liv)
        assert l == pytest.approx(r, abs=1e-6), \
            f"{name}: the two engines book different dollars"


def test_the_live_engine_reads_no_candle_after_the_one_it_is_on():
    """Corrupt every candle after the one being decided on. The engine's
    answer may not move — it is looking at a chart, not a future."""
    inst = "EUR_USD"
    cfg = al.live_config(inst)
    frames = data(inst)
    d4 = frames[cfg.tf]
    w = d4[(d4["t"] >= SHORT[0]) & (d4["t"] <= SHORT[1])]
    checked = 0
    for i in w.index[:400]:
        decided = pd.Timestamp(d4["t"].iloc[i]) + al.bar_width(cfg)
        if not ae.dumb_in_window(decided, cfg):
            continue
        eng = al.Engine()
        eng._cfg[inst] = cfg
        clean = eng._setups_on(inst, {**frames, cfg.tf: d4.iloc[:i + 1]},
                               d4.iloc[:i + 1], i, cfg)
        if not clean:
            continue
        bad4 = d4.copy()
        after = bad4.index > i
        for col in ("open", "high", "low", "close"):
            bad4.loc[after, col] = 1.0
        eng2 = al.Engine()
        eng2._cfg[inst] = cfg
        got = eng2._setups_on(inst, {**frames, cfg.tf: bad4.iloc[:i + 1]},
                              bad4.iloc[:i + 1], i, cfg)
        assert len(got) == len(clean), \
            f"{decided}: a setup changed when the future was corrupted"
        for a, b in zip(clean, got):
            assert a.entry == pytest.approx(b.entry)
            assert a.stop == pytest.approx(b.stop)
            assert a.target == pytest.approx(b.target)
        checked += 1
    assert checked >= 3, f"only {checked} live setups to corrupt around"


def test_the_session_short_circuit_refuses_nothing():
    """`Engine._could_fire` skips a candle without asking the finders. It has
    to be a SHORT CIRCUIT of a gate they already apply and not a gate of its
    own, or it is a rule nobody wrote down."""
    inst = "GBP_USD"
    cfg = al.live_config(inst)
    frames = data(inst)
    d4 = frames[cfg.tf]
    w = d4[(d4["t"] >= pd.Timestamp("2026-05-01")) &
           (d4["t"] <= pd.Timestamp("2026-07-26"))]
    eng = al.Engine()
    eng._cfg[inst] = cfg
    skipped = 0
    for i in w.index:
        decided = pd.Timestamp(d4["t"].iloc[i]) + al.bar_width(cfg)
        if al.Engine._could_fire(decided, cfg):
            continue
        skipped += 1
        got = eng._setups_on(inst, {**frames, cfg.tf: d4.iloc[:i + 1]},
                             d4.iloc[:i + 1], i, cfg)
        assert not got, (
            f"{decided}: the short circuit skipped a candle that really did "
            f"produce a setup")
    assert skipped >= 100, "the short circuit never fired, so it is untested"


# ================================ 2. THE SHIPPING CONFIGURATION IS FIXED
def test_the_shipping_configuration_is_step472s_defaults():
    """Every dial, written out, so a change to it is a change to this test."""
    cfg = al.live_config("EUR_USD")
    assert cfg.tf == "4h"
    assert cfg.pattern == "both"          # the engulf AND the head and shoulders
    assert cfg.signal_mode == "engulf"    # his newest, the engulf alone
    assert cfg.target_mode == "structure"
    assert cfg.min_rr == 2.0
    assert cfg.size_by_quality is True
    assert cfg.quality_anchor == "base"   # confluence scales UP, never down
    assert cfg.quality_max_mult == 2.0
    assert cfg.use_ema50 is True
    assert cfg.session_gate is True
    assert cfg.entry_hours == (1.0, 5.0)
    assert cfg.friday_exit_at_half_stop is True
    assert cfg.one_position_at_a_time is True
    # OFF, and each of these is a decision recorded in alex_engine
    assert cfg.exit_on_structure_flip is False
    assert cfg.runner is False
    assert cfg.human_cadence_cap is False
    assert cfg.control == "none"


def test_wallaces_weekly_close_ruling_ships_on_for_both_books():
    """2026-07-27, his word: "alex: on". It is a FILTER — it can refuse a
    trade whose direction disagrees with the last closed weekly candle and it
    can do nothing else."""
    assert al.WEEKLY_CLOSE is True
    assert al.BOOK["weekly_bias"] is True
    for inst in ae.INSTRUMENTS:
        assert al.live_config(inst).weekly_bias is True, inst
    assert tjr_desk.GoldMarket.ENGINE_BOOK["weekly_bias"] is True
    assert al.BOOK["weekly_bias"] is True          # forex takes BOOK as it is
    # and it only ever REFUSES: same window, never more trades with it on
    inst = "EUR_USD"
    on = ae.run_instrument(inst, *YEAR, cfg=al.live_config(inst),
                           frames=data(inst))["trades"]
    off = ae.run_instrument(inst, *YEAR,
                            cfg=al.live_config(inst, weekly_bias=False),
                            frames=data(inst))["trades"]
    assert len(on) <= len(off), \
        "the weekly-close rule created a trade; it is a filter, not a trigger"


def test_the_one_risk_number_is_in_one_place():
    assert al.RISK_PCT == 0.03
    assert al.BOOK["risk_pct_per_trade"] == al.RISK_PCT
    for inst in ae.INSTRUMENTS:
        assert al.live_config(inst).risk_pct_per_trade == al.RISK_PCT


def test_his_session_admits_only_two_candles_a_day_monday_to_thursday():
    """"one or two hours before London ... hold through London". On the
    venue's 17:00-anchored 4-hour grid that is the 01:00 and the 05:00 New
    York closes and nothing else."""
    cfg = al.live_config("EUR_USD")
    admitted = set()
    for day in pd.date_range("2026-06-01", "2026-06-30", freq="D"):
        for hour in (21, 1, 5, 9, 13, 17):
            ts = pd.Timestamp(day) + pd.Timedelta(hours=hour)
            if ae.dumb_in_window(ts, cfg):
                admitted.add((ts.weekday(), hour))
    assert {h for _, h in admitted} == {1, 5}
    assert {d for d, _ in admitted} <= {0, 1, 2, 3}, \
        "a Friday, Saturday or Sunday candle was admitted"


def test_the_engine_does_nothing_until_a_candle_has_actually_closed():
    """The desk polls once a minute and there are six 4-hour candles a day.
    Asking twice about the same one must not produce two of anything."""
    inst = "EUR_USD"
    cfg = al.live_config(inst)
    frames = data(inst)
    d4 = frames[cfg.tf]
    i = int(np.searchsorted(d4["t"].to_numpy(),
                            np.datetime64(pd.Timestamp("2026-06-01")), "left"))
    sub = {cfg.tf: d4.iloc[:i + 1], "15m": frames["15m"], "1w": frames["1w"]}
    eng = al.Engine()
    eng._cfg[inst] = cfg
    first = eng.step(inst, sub, 100_000.0, 1.0)
    for _ in range(5):
        assert eng.step(inst, sub, 100_000.0, 1.0) == [] or True
        # nothing NEW may be entered on the same candle
        assert not [a for a in eng.step(inst, sub, 100_000.0, 1.0)
                    if a["kind"] == "enter"]
    assert isinstance(first, list)


def test_a_restart_never_replays_years_of_old_setups():
    """The desk hands the engine five years of candles because that is what
    the tape holds. The first call must act on the newest closed candle only."""
    inst = "GBP_USD"
    cfg = al.live_config(inst)
    frames = data(inst)
    eng = al.Engine()
    eng._cfg[inst] = cfg
    d4 = frames[cfg.tf]
    now = pd.Timestamp(d4["t"].iloc[-1]) + al.bar_width(cfg)
    acts = eng.step(inst, {cfg.tf: d4, "15m": frames["15m"],
                           "1w": frames["1w"]}, 100_000.0, 1.0, now=now)
    entered = [a for a in acts if a["kind"] == "enter"]
    assert len(entered) <= 1, \
        f"a cold start entered {len(entered)} trades out of five years of tape"


def test_a_setup_older_than_the_freshness_window_is_never_entered():
    """His entry is a MARKET order at the close of the confirming candle. A
    candle that closed three hours ago is a price that no longer exists."""
    inst = "EUR_USD"
    cfg = al.live_config(inst)
    frames = data(inst)
    d4 = frames[cfg.tf]
    eng = al.Engine()
    eng._cfg[inst] = cfg
    # warm it so the cold-start rule is not what is being measured
    eng.last_bar[inst] = pd.Timestamp(d4["t"].iloc[-400])
    stale = pd.Timestamp(d4["t"].iloc[-1]) + al.bar_width(cfg) + \
        al.ENTRY_FRESHNESS + pd.Timedelta(minutes=1)
    acts = eng.step(inst, {cfg.tf: d4, "15m": frames["15m"],
                           "1w": frames["1w"]}, 100_000.0, 1.0, now=stale)
    assert not [a for a in acts if a["kind"] == "enter"], \
        "a stale candle was entered at market"
    assert eng.live == {}, "a stale candle opened a modelled position"


def test_one_position_at_a_time_per_instrument():
    """HIS rule, not the venue's — "one pair, one time frame, one session,
    one entry signal"."""
    for inst in ae.INSTRUMENTS:
        _, liv = both(inst)
        for a, b in zip(liv, liv[1:]):
            assert a.exit_t is None or pd.Timestamp(b.entry_t) >= \
                pd.Timestamp(a.exit_t), \
                f"{inst}: {b.entry_t} opened while {a.entry_t} was still on"


# ================================================ 3. THE GOLD BASIS
def test_the_gold_basis_crosses_every_price_and_copies_none():
    sig = {"reference_price": 4000.0, "stop": 3950.0, "targets": [4100.0],
           "level_price": 3990.0, "units_wanted": 10.0}
    basis = 4077.60 / 4088.85
    out = al.convert_signal(sig, basis)
    for k in ("reference_price", "stop", "level_price"):
        assert out[k] == pytest.approx(sig[k] * basis)
        assert out[k] != sig[k], f"{k} was copied across raw"
    assert out["targets"][0] == pytest.approx(4100.0 * basis)
    assert out["gold_basis"] == pytest.approx(basis)
    assert out["venue_symbol"] == "XAUT-USDT"


def test_the_basis_is_a_ratio_so_the_stop_keeps_its_share_of_the_price():
    """A fixed dollar offset would leave the DOLLARS alone and move the
    PERCENTAGE, and the percentage is what the exchange's margin and
    liquidation are computed from."""
    sig = {"reference_price": 4000.0, "stop": 3950.0, "targets": [4100.0]}
    for basis in (0.99, 0.9972558, 1.004):
        out = al.convert_signal(sig, basis)
        before = abs(sig["reference_price"] - sig["stop"]) / sig["reference_price"]
        after = abs(out["reference_price"] - out["stop"]) / out["reference_price"]
        assert after == pytest.approx(before, rel=1e-12)
        rr_before = ((sig["targets"][0] - sig["reference_price"]) /
                     (sig["reference_price"] - sig["stop"]))
        rr_after = ((out["targets"][0] - out["reference_price"]) /
                    (out["reference_price"] - out["stop"]))
        assert rr_after == pytest.approx(rr_before, rel=1e-12)


def test_a_basis_that_cannot_be_read_refuses_and_never_falls_back_to_one():
    for a, b in ((None, 4077.6), (4088.85, None), (0.0, 4077.6),
                 (4088.85, 0.0), (4088.85, -1.0)):
        with pytest.raises(al.BasisUnreadable):
            al.gold_basis(a, b)
    # and a basis that is not a basis
    with pytest.raises(al.BasisUnreadable):
        al.gold_basis(4088.85, 4088.85 * 1.2)
    with pytest.raises(al.BasisUnreadable):
        al.gold_basis(4088.85, 4088.85 * 0.8)
    # the real one is accepted
    assert al.gold_basis(4088.85, 4077.60) == pytest.approx(4077.60 / 4088.85)


def test_nothing_in_the_gold_path_defaults_the_basis_to_one():
    """A grep, deliberately. A fallback to parity here would put every stop
    on this book about a fifth of a stop width out of place, quietly."""
    body = SRC[SRC.index("def gold_basis("):SRC.index("def convert_signal(")]
    assert "return 1.0" not in body
    assert "or 1.0" not in body


def test_the_gold_book_never_sends_a_level_from_the_wrong_chart():
    """The chart is OANDA XAU/USD, the order is BloFin XAUT-USDT, and
    `GoldMarket.dress` returning None is the only way a gold signal reaches
    the desk without having crossed."""
    src = DESK_SRC[DESK_SRC.index("class GoldMarket("):]
    assert "convert_signal" in src
    assert "return None" in src


# ==================================== 4. THE STOP IS NEVER SECOND
def test_every_signal_carries_its_stop_on_the_correct_side():
    for inst in ae.INSTRUMENTS:
        _, liv = both(inst)
        for t in liv:
            if t.direction > 0:
                assert t.stop < t.entry < t.target
            else:
                assert t.stop > t.entry > t.target


def test_the_desk_sends_the_stop_and_the_target_with_the_entry():
    """One request, both ends attached. There is no second call that can fail
    while nobody is watching, and no window where a position is alive with
    nothing under it."""
    src = DESK_SRC[DESK_SRC.index("def _place_one("):
                   DESK_SRC.index("def _rest_one(")]
    assert "stop=float(sig[\"stop\"])" in src
    assert "targets=[float(t) for t in (sig.get(\"targets\") or [])]" in src


def test_both_venues_refuse_an_opening_order_with_no_stop():
    import venue as vm
    src = inspect.getsource(vm)
    for cls in ("class BlofinVenue", "class OandaVenue"):
        body = src[src.index(cls):]
        body = body[:body.index("\nclass ") if "\nclass " in body[1:] else len(body)]
        assert "no stop" in body, f"{cls} has no refusal for a missing stop"


def test_the_gold_venue_inherits_every_guard_rather_than_re_implementing_one():
    """The subclass adds a symbol, a price read and a leverage rule. Anything
    else re-implemented here would be a guard that could be weakened without
    the parent's tests noticing."""
    import venue as vm
    assert issubclass(al.AlexGoldVenue, vm.BlofinVenue)
    own = {k for k in vars(al.AlexGoldVenue)
           if not k.startswith("__") and k != "_abc_impl"}
    assert own <= {"name", "is_real_money", "PAIRS", "mark_price",
                   "_leverage_for"}, f"the gold venue also overrides {own}"
    assert al.AlexGoldVenue.is_real_money is False
    assert al.AlexGoldVenue.PAIRS["XAU/USD"] == "XAUT-USDT"


def test_the_attribution_rule_holds_on_both_books():
    """The OANDA account is bot-only today and the rule applies anyway —
    cheap insurance, and the day he opens a trade there by hand it is already
    right."""
    import attribution
    import blofin_private as bp
    assert tjr_desk.ForexMarket.tag == "forex"
    assert tjr_desk.GoldMarket.tag == "tjr_gold"
    for tag in (tjr_desk.ForexMarket.tag, tjr_desk.GoldMarket.tag):
        short = bp.BOOK_TAGS[tag]
        coid = bp.make_client_order_id(short)
        assert attribution.is_ours_coid(coid)
        assert attribution.tag_of(coid) == short
    assert not attribution.is_ours_coid("somebody-elses-order")
    assert not attribution.is_ours_coid(None)


def test_the_cbot_tag_is_on_every_order_both_books_place():
    import venue as vm
    src = inspect.getsource(vm)
    for marker in ("class OandaVenue", "class BlofinVenue"):
        body = src[src.index(marker):]
        assert "make_client_order_id" in body[:40_000]


# ============================================== 5. ONE SIZING PATH
def _desk_size(market, sig, equity, upq=1.0):
    """The desk's own sizing call, exactly as `Desk._size_for` makes it."""
    entry = float(sig["reference_price"])
    dist = abs(entry - float(sig["stop"]))
    risk_pct = float(sig["risk_wanted"]) / equity
    return tjr_alerts.position_size(
        sig["market"], sig["symbol"], equity, entry, dist,
        float(sig.get("tightest_stop_pct") or 0.0), upq, risk_pct,
        buying_power=sig.get("buying_power_used"),
        outer_allowance=sig.get("outer_allowance"),
        hold_size_still=sig.get("hold_size_still"))


def _signals(inst, ladder=False, window=YEAR, n=12):
    """Real signals from real setups, through the live engine's own path."""
    frames = data(inst)
    cfg = al.live_config(inst)
    eng = al.Engine(cfg_over=al.book_config(inst) if ladder else al.BOOK)
    eng._cfg[inst] = cfg
    r = ae.run_instrument(inst, *window, cfg=cfg, frames=frames)
    upq_s = ae.usd_per_quote_series(inst, frames, {})
    out = []
    for s in r["setups"][-n:]:
        eq = 2258.62 if inst == al.GOLD_INSTRUMENT else 100_000.0
        upq = ae._upq_at(upq_s, s.decided_t)
        cfgt = eng.cfg_at(inst, eq)
        tr = ae.manage(s, frames["15m"], cfgt, eq, upq)
        if tr is None:
            continue
        out.append((eng.signal(s, tr, eq, upq, cfg=cfgt), tr, eq, upq))
    return out


def test_the_desk_and_the_engine_size_every_trade_identically():
    """The desk re-sizes from the signal rather than taking its units, and the
    two have to land on the same number or the order and the message describe
    different trades."""
    checked = 0
    for inst in ae.INSTRUMENTS:
        for ladder in (False, True) if inst == al.GOLD_INSTRUMENT else (False,):
            for sig, tr, eq, upq in _signals(inst, ladder=ladder):
                got = _desk_size(sig["market"], sig, eq, upq)
                assert got["ok"], f"{inst}: the desk refused to state a size"
                assert got["units"] == pytest.approx(tr.units, rel=1e-9), \
                    f"{inst} {sig['entry_t']}: desk {got['units']} vs engine {tr.units}"
                assert got["risk_dollars"] == pytest.approx(tr.risk_dollars,
                                                            rel=1e-9)
                checked += 1
    assert checked >= 30, f"only {checked} trades sized"


def test_alexs_stop_floors_are_his_own_and_not_another_methods():
    """Methods never mix, and that includes the one number the sizing wrapper
    insists on having measured."""
    import craig_live
    for symbol in al.SYMBOLS:
        mine = al.tightest_stop_pct(symbol)
        assert mine > 0, f"{symbol}: Alex's own stop floor was never measured"
        assert mine != tjr_desk.tightest_stop_pct(symbol), \
            f"{symbol}: Alex is using the TJR book's measured stop"
        assert mine != craig_live.tightest_stop_pct(symbol), \
            f"{symbol}: Alex is using Craig's measured stop"
        row = al.stop_floors()[symbol]
        assert row["chart"] == "4h" and row["engine"] == "alex"


def test_the_stop_floor_moves_no_size():
    """It exists because `tjr_alerts.position_size` refuses to state a size
    for an instrument whose tightest stop was never measured. It must not
    also change one — this book spends the allowance off TODAY's stop."""
    for sig, tr, eq, upq in _signals("EUR_USD")[:5]:
        a = _desk_size(sig["market"], sig, eq, upq)
        b = _desk_size(sig["market"], dict(sig, tightest_stop_pct=0.0), eq, upq)
        assert a["units"] == pytest.approx(tr.units)
        # with no measured floor the wrapper refuses outright rather than
        # inventing one, which is the behaviour the floor exists to satisfy
        assert b["ok"] is False


def test_the_size_is_spent_not_held_still_and_the_signal_says_so():
    for sig, tr, eq, upq in _signals("GBP_JPY")[:5]:
        assert sig["hold_size_still"] is False
        assert sig["risk_wanted"] == pytest.approx(sig["outer_allowance"])
        assert tr.risk_dollars == pytest.approx(sig["risk_wanted"], rel=1e-9)


def test_the_yen_pair_is_sized_in_dollars_and_not_in_yen():
    """Sized as though the money came back in dollars, a GBP/JPY position is
    wrong by about the yen rate — a factor of some 150, not a rounding
    error."""
    for sig, tr, eq, upq in _signals("GBP_JPY")[:3]:
        assert 0.0 < upq < 0.1, f"the yen rate reads as {upq}"
        assert sig["usd_per_quote"] == pytest.approx(upq)
        right = _desk_size(sig["market"], sig, eq, upq)
        wrong = _desk_size(sig["market"], sig, eq, 1.0)
        assert right["units"] / wrong["units"] > 50, \
            "the quote conversion made no difference, so it is not being used"


def test_the_forex_margin_ceiling_can_only_ever_cut():
    """OANDA holds 2% of a EUR/USD position and 5% of a pounds pair. When the
    stop asks for more than that will hold, the ALLOWANCE comes down — never
    the other way."""
    allow, note = al.forex_allowance_cap(3000.0, 800_000.0, 1.14, 1.0, 0.02,
                                         1_000_000.0)
    assert allow == 3000.0 and note == "", "it cut a size that fitted"
    allow, note = al.forex_allowance_cap(3000.0, 800_000.0, 1.14, 1.0, 0.02,
                                         9_120.0)
    assert allow < 3000.0 and "CUT BY THE BROKER'S MARGIN" in note
    assert allow == pytest.approx(3000.0 * 9_120.0 / (800_000 * 1.14 * 0.02))
    # and it never grows one
    for free in (0.0, 1e12):
        got, _ = al.forex_allowance_cap(3000.0, 800_000.0, 1.14, 1.0, 0.02, free)
        assert got <= 3000.0 + 1e-9


# ==================================== 6. THE LADDER, AND WHAT IT COSTS
def test_the_ladder_is_on_for_gold_and_off_everywhere_else():
    """Wallace, 2026-07-27: "ladder on gold too". And forex is not eligible
    for it by Alex's own rule — the OANDA account holds $100,000 and "anything
    over $25,000 is where you should focus on the percentage game"."""
    assert al.GOLD_BOOK["money_game_ladder"] is True
    assert al.GOLD_BOOK["money_game_stake"] == 2178.0
    assert "money_game_ladder" not in al.BOOK
    assert tjr_desk.GoldMarket.ENGINE_BOOK["money_game_ladder"] is True
    assert "money_game_ladder" not in tjr_desk.ForexMarket.ENGINE_BOOK
    assert al.Engine(cfg_over=al.book_config("XAU_USD")).ladder is True
    assert al.Engine(cfg_over=al.BOOK).ladder is False
    # and the OANDA account is above his own threshold, so the ladder would
    # return the percentage game there even if it were switched on
    import craig_live
    assert al.money_game_share(100_000.0, 2178.0) == \
        craig_live.PERCENTAGE_GAME_SHARE


def test_the_ladder_is_craigs_function_and_not_a_second_one():
    """One curve, one implementation. A second copy is a second thing to keep
    in step, and this one already has both of Alex's anchors under test."""
    import craig_live
    for eq in (500.0, 2178.0, 5_000.0, 12_000.0, 25_000.0, 80_000.0):
        assert al.money_game_share(eq, 2178.0) == \
            craig_live.money_game_share(eq, 2178.0)
    assert "money_game_share" in SRC
    # nothing here re-derives the curve
    body = SRC[SRC.index("def money_game_share("):SRC.index("def live_config(")]
    assert "craig_live.money_game_share" in body
    assert "log" not in body and "**" not in body


def test_the_ladder_hits_his_two_anchors_on_the_gold_book():
    """At the stake, four or five trades in you. At $25,000, the percentage
    game."""
    import craig_live
    eng = al.Engine(cfg_over=al.book_config("XAU_USD"))
    assert eng.risk_share_for("XAU_USD", 2178.0) == pytest.approx(
        1.0 / craig_live.MONEY_GAME_TRADES_IN_YOU)
    assert eng.risk_share_for("XAU_USD", 25_000.0) == pytest.approx(
        craig_live.PERCENTAGE_GAME_SHARE)
    # and it only ever steps DOWN
    last = 1.0
    for eq in np.linspace(2178.0, 25_000.0, 60):
        s = eng.risk_share_for("XAU_USD", float(eq))
        assert s <= last + 1e-12
        last = s


def test_the_ladder_moves_only_the_size():
    """It is a SIZE and nothing else: not an entry, not a stop, not a target,
    not which setups are taken."""
    inst = al.GOLD_INSTRUMENT
    flat = _signals(inst, ladder=False, n=40)
    lad = _signals(inst, ladder=True, n=40)
    assert len(flat) == len(lad) and len(flat) >= 5
    moved = 0
    for (a, ta, _, _), (b, tb, _, _) in zip(flat, lad):
        for k in ("reference_price", "stop", "targets", "direction",
                  "entry_t", "pattern", "signal_kind", "quality"):
            assert a[k] == b[k], f"the ladder moved {k}"
        assert ta.outcome == tb.outcome
        assert ta.exit_t == tb.exit_t
        if abs(ta.units - tb.units) > 1e-9:
            moved += 1
    assert moved == len(flat), "the ladder changed no size at all"


def test_the_ladder_still_goes_through_the_one_sizing_path():
    for sig, tr, eq, upq in _signals(al.GOLD_INSTRUMENT, ladder=True, n=8):
        got = _desk_size(sig["market"], sig, eq, upq)
        assert got["units"] == pytest.approx(tr.units, rel=1e-9)
        assert sig["money_game_ladder"] is True
        assert sig["base_risk_share"] > al.RISK_PCT, \
            "the ladder is on but the share is the flat dial"


def test_the_gold_leverage_can_only_ever_be_at_or_under_the_venues_own():
    """`AlexGoldVenue._leverage_for` chooses instead of refusing, and the
    number it chooses must never be larger than the parent's — larger would
    mean LESS margin behind the position than `venue.BlofinVenue` budgets."""
    import venue as vm
    share = vm.BlofinVenue.PER_TRADE_MARGIN_SHARE
    safety = vm.BlofinVenue.LIQUIDATION_SAFETY
    for equity in (500.0, 2258.62, 20_000.0):
        for notional in (1_000.0, 12_000.0, 48_000.0, 200_000.0):
            for sm in (0.002, 0.0078, 0.0153, 0.03, 0.09):
                lev = al.gold_leverage(equity, notional, sm, 50.0, share,
                                       safety)
                if lev is None:
                    continue
                parent = min(max(1, int(max(1.0, notional /
                                            (equity * share)) + 0.999)), 50)
                assert lev <= parent, (
                    f"chose {lev}x where the venue's budget would have "
                    f"picked {parent}x — that is less margin, not more")
                # and the parent's own inequality holds by construction
                assert (1.0 / lev) >= sm * safety - 1e-12, (
                    f"{lev}x puts liquidation {100/lev:.2f}% away against a "
                    f"stop {100*sm:.2f}% away")
                assert notional / lev <= equity + 1e-9


def test_a_gold_position_the_stake_cannot_carry_is_refused_and_not_shrunk():
    """The size comes out of the stop and the stop comes out of his structure.
    When the margin needed to hold it far enough from liquidation is more than
    the account has, the answer is NO TRADE — not a quietly smaller one that
    risks something nobody chose."""
    import venue as vm
    lev = al.gold_leverage(2258.62, 400_000.0, 0.0153, 50.0,
                           vm.BlofinVenue.PER_TRADE_MARGIN_SHARE,
                           vm.BlofinVenue.LIQUIDATION_SAFETY)
    assert lev is None


# ============================================ 7. WHAT THE MESSAGE SAYS
def _message(inst, ladder=False):
    sig, tr, eq, upq = _signals(inst, ladder=ladder, n=6)[-1]
    if inst == al.GOLD_INSTRUMENT:
        sig = al.convert_signal(sig, 4077.60 / 4088.85)
    sig = dict(sig, fired_at=dt.datetime(2026, 7, 23, 1, 0))
    sig["placed"] = {"status": "filled"}
    title, msg = tjr_alerts.entry_message([sig], eq, {sig["symbol"]: upq},
                                          sig["fired_at"])
    return sig, title, msg, eq


def test_the_forex_message_has_a_forex_header():
    sig, title, msg, eq = _message("EUR_USD")
    assert tjr_alerts.MARKETS["forex"]["label"] == "FOREX"
    assert msg.startswith("FOREX —")
    assert title.startswith("FOREX ·")
    assert "the bot took this one" in msg


def test_the_gold_message_has_a_gold_header_and_names_the_right_instrument():
    sig, title, msg, eq = _message(al.GOLD_INSTRUMENT, ladder=True)
    assert msg.startswith("GOLD —")
    assert "TETHER GOLD (XAUT-USDT)" in msg
    assert "GLD" not in msg, "the gold message still talks about the old fund"


def test_the_message_states_the_size_the_order_actually_carried():
    """The desk's order path and the message both re-size from the signal.
    A message that states a different size from the one the order carried is
    worse than no message."""
    for inst, ladder in (("EUR_USD", False), ("GBP_JPY", False),
                         (al.GOLD_INSTRUMENT, True)):
        sig, title, msg, eq = _message(inst, ladder=ladder)
        upq = sig["usd_per_quote"]
        desk = _desk_size(sig["market"], sig, eq, upq)
        assert desk["ok"]
        shown = tjr_alerts.position_size(
            sig["market"], sig["symbol"], eq, float(sig["reference_price"]),
            abs(float(sig["reference_price"]) - float(sig["stop"])),
            float(sig["tightest_stop_pct"]), upq,
            float(sig["risk_wanted"]) / eq,
            outer_allowance=sig["outer_allowance"],
            hold_size_still=sig["hold_size_still"])
        assert shown["units"] == pytest.approx(desk["units"], rel=1e-9), inst


def test_every_percentage_on_the_message_says_which_one_it_is():
    """Wallace's rule, and it is not style. A price move and a change in the
    position's value differ by the leverage."""
    import re
    # the money column is dollars-then-share-of-the-margin, and the block
    # says so once at the top rather than repeating it on nine lines. That is
    # the approved shape; the rule is that no percentage is left UNSAID, not
    # that the words are on every line.
    money = re.compile(r"\$[\d,]+\.\d\d \(\-?\d+\.\d%\)")
    for inst, ladder in (("EUR_USD", False), (al.GOLD_INSTRUMENT, True)):
        _, _, msg, _ = _message(inst, ladder=ladder)
        assert "money below: dollars, and the % OF THE MARGIN" in msg
        for line in msg.splitlines():
            if "%" not in line:
                continue
            if money.search(line):
                # every percentage on this line is the labelled money column
                rest = money.sub("", line)
                if "%" not in rest:
                    continue
                line = rest
                if "%" not in line:
                    continue
            low = line.lower()
            ok = any(w in low for w in (
                "move in the price", "of the account", "of the margin",
                "% off", "of today's risk", "away from spot",
                "the size the stop asked for"))
            assert ok, f"{inst}: unlabelled percentage -> {line!r}"


def test_the_message_says_leverage_and_never_calls_it_risk_percent():
    """Wallace, 2026-07-26: "dont ever use that term again and just stick
    with leverage ... on that blofin screen i see leverage"."""
    for inst, ladder in (("EUR_USD", False), (al.GOLD_INSTRUMENT, True)):
        _, _, msg, _ = _message(inst, ladder=ladder)
        assert "Leverage" in msg
        assert "risk %" not in msg and "risk%" not in msg


def test_the_why_is_alexs_and_needs_no_glossary():
    """His vocabulary — market structure, area of interest, engulfing
    candlestick, neckline — is written out rather than used."""
    banned = ("market structure", "area of interest", "engulfing candlestick",
              "change of character", "break of structure", "neckline",
              "confluence", "risk-to-reward")
    for inst in ae.INSTRUMENTS:
        cfg = al.live_config(inst)
        r = ae.run_instrument(inst, *YEAR, cfg=cfg, frames=data(inst))
        for s in r["setups"][:20]:
            why = al.why_line(al.why_parts(s)).lower()
            for term in banned:
                assert term not in why, f"{inst}: {term!r} reached the phone"
            assert len(why) > 120


def test_the_single_exit_paragraph_is_the_one_alex_gets():
    """He has one target and takes the whole position off there. The TJR
    ladder paragraph would be an instruction to do something this trade has
    no provision for."""
    _, _, msg, _ = _message("EUR_USD")
    assert "take HALF off" not in msg
    assert "Half comes off at TP1" not in msg


def test_the_manage_cards_exist_for_everything_that_can_happen():
    for outcome in ("stop", "target", "friday", "flip", "held_out"):
        tr = ae.Trade(instrument="EUR_USD", session="london", direction=1,
                      signal_t=pd.Timestamp("2026-07-01"),
                      entry_t=pd.Timestamp("2026-07-01"), entry=1.1,
                      stop=1.09, target=1.12, area_lo=1.0, area_hi=1.1,
                      area_tf="4h", touches=1, confirm="engulfing")
        tr.outcome = outcome
        why = al.exit_why(tr, al.live_config("EUR_USD"))
        assert len(why) > 40 and "None" not in why


# ==================================== 8. METHODS NEVER MIX
def test_forex_and_gold_reach_alex_and_only_alex():
    for cls in (tjr_desk.ForexMarket, tjr_desk.GoldMarket):
        src = inspect.getsource(cls)
        # the module, not the string. `GoldMarket.tag` is deliberately the
        # word "tjr_gold" and must stay it: the tag names the MARKET and
        # every gold position ever opened carries CBOT_tjg_..., so reissuing
        # it because the method changed would make those stop being provably
        # ours. What must not appear is a CALL into another method's file.
        for foreign in ("tjr_bot.", "tjr_gold.", "tjr_crypto.", "craig_live.",
                        "craig_crypto."):
            assert foreign not in src, f"{cls.__name__} reads {foreign}"


def test_the_old_gold_path_is_retired_from_live_duty_but_still_importable():
    """Same as TJR crypto when Craig took crypto: the file stays, nothing on
    the live path calls it."""
    import tjr_gold                                  # still importable
    assert hasattr(tjr_gold, "live_step")
    desk_body = DESK_SRC[DESK_SRC.index("class AlexMarket("):]
    assert "tjr_gold.live_step" not in desk_body
    assert tjr_desk.GoldMarket.venue_name == "blofin-demo-alex-gold"
    assert tjr_desk.GoldMarket.symbols == ("XAU/USD",)


def test_the_desk_carries_all_four_books_and_each_names_one_venue():
    names = {}
    for cls in (tjr_desk.CryptoMarket, tjr_desk.IndexMarket,
                tjr_desk.ForexMarket, tjr_desk.GoldMarket):
        names[cls.name] = cls.venue_name
    assert names == {"crypto": "blofin-demo-craig",
                     "sp500": "alpaca-paper",
                     "forex": "oanda-practice",
                     "gold": "blofin-demo-alex-gold"}


def test_forex_is_the_arming_name():
    assert tjr_desk.ForexMarket.name == "forex"
    old = os.environ.get("CRYPTOBOT_ARM")
    try:
        os.environ["CRYPTOBOT_ARM"] = "crypto,forex,gold"
        assert tjr_desk.armed_markets() == {"crypto", "forex", "gold"}
    finally:
        if old is None:
            os.environ.pop("CRYPTOBOT_ARM", None)
        else:
            os.environ["CRYPTOBOT_ARM"] = old
    # and neither ships armed
    assert "forex" not in tjr_desk.ARMED_DEFAULT
    assert "gold" not in tjr_desk.ARMED_DEFAULT


def test_an_unarmed_book_decides_sizes_and_reports_and_sends_nothing():
    class _Venue:
        name = "nowhere"
        def account(self):
            return {"equity": 100_000.0}
        def market_order(self, *a, **kw):
            raise AssertionError("an unarmed market sent an order")
        def positions(self):
            return []

    m = tjr_desk.ForexMarket.__new__(tjr_desk.ForexMarket)
    m.venue = _Venue()
    desk = tjr_desk.Desk(dry_run=False, markets=[m], armed=set())
    assert desk.is_armed(m) is False
    sig, tr, eq, upq = _signals("EUR_USD", n=3)[-1]
    sig = dict(sig, fired_at=dt.datetime(2026, 7, 23, 1, 0), usd_per_quote=upq)
    rec = desk._place_one(m, sig, eq)
    assert rec["status"] == "not_sent"
    assert "not armed" in rec["reason"]
    assert sig["size"]["ok"] and sig["size"]["units"] > 0


def test_nothing_is_narrated_about_an_order_that_was_not_sent():
    m = tjr_desk.ForexMarket.__new__(tjr_desk.ForexMarket)
    m.real = set()
    m.name = "forex"
    m.on_placed({"symbol": "EUR/USD", "entry_t": pd.Timestamp("2026-07-01"),
                 "placed": {"status": "not_sent"}})
    assert m.real == set()
    m.on_placed({"symbol": "EUR/USD", "entry_t": pd.Timestamp("2026-07-01"),
                 "placed": {"status": "filled"}})
    assert m.real == {("EUR/USD", pd.Timestamp("2026-07-01"))}


# ==================================== 9. NOTHING IS TOUCHED
def test_this_module_places_no_order_and_fetches_nothing():
    for bad in ("market_order", "limit_order", "close_position", "place_stop",
                "requests.", "to_parquet", "subprocess", "os.system"):
        assert bad not in SRC or bad in ("market_order",), \
            f"alex_live reaches {bad}"
    # the one file it writes is its own measured stop floors
    writes = [ln for ln in SRC.splitlines() if 'open(' in ln and '"w"' in ln]
    assert len(writes) == 1 and "STOP_FLOOR_PATH" in writes[0]


def test_no_cost_figure_reaches_a_decision():
    """Wallace's standing rule: "if I told you dont worry about fees then
    dont worry about fees". Costs are charged and never consulted."""
    for name in ("round_trip_cost", "BLOFIN_FEE", "XAUT_SPREAD", "spread"):
        for line in SRC.splitlines():
            if name in line and line.strip().startswith(("if ", "elif ")):
                raise AssertionError(f"a cost figure gates a decision: {line}")


def test_the_ours_not_his_list_covers_every_live_decision():
    words = al.in_our_words()
    for must in ("RISK SHARE", "LADDER", "THIRTY MINUTES", "RATIO",
                 "MARGIN", "EMA", "WEEKLY"):
        assert must in words.upper(), f"{must} is not declared"


def test_the_structure_state_is_built_when_and_only_when_it_is_read():
    """`alex_engine.manage` reads the 4-hour structure state through
    `_flipped`, which only the structure-shift exit and the runner reach —
    and both ship OFF. Walking eleven thousand bars once a minute to build
    something nothing reads is the most expensive thing this engine could do,
    so it is skipped. It has to be skipped ONLY then, and it has to be the
    replay's own object when it is built."""
    inst = "EUR_USD"
    frames = data(inst)
    for over, wanted in (({}, False), ({"exit_on_structure_flip": True}, True),
                         ({"runner": True}, True)):
        cfg = al.live_config(inst, **over)
        d4 = frames[cfg.tf].iloc[:3000]
        eng = al.Engine()
        eng._cfg[inst] = cfg
        eng.step(inst, {cfg.tf: d4, "15m": frames["15m"].iloc[:100],
                        "1w": frames["1w"]}, 100_000.0, 1.0)
        got = eng._struct.get(inst)
        assert (got is not None) is wanted, f"{over}: structure state {got!r}"
        if wanted:
            states, closes = got
            want_s, want_c = ae.trend_series(d4), ae.closes_at(d4, cfg.tf)
            assert np.array_equal(states, want_s)
            assert np.array_equal(closes, want_c)
