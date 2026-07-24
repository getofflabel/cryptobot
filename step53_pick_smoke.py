"""
step53_pick_smoke.py — REAL BloFin smoke test for daily_pick.py.

READ-ONLY + DRY: pulls REAL candles (config.make_exchange("live"), the PROD
market-data host — full history for the whole named universe regardless of
demo availability), probes the REAL demo host for which symbols are
actually tradeable there, reads the REAL current account state (positions,
other books), then:

  1. prints the FULL ranked scoreboard — every instrument in UNIVERSE, both
     long/short scores, every component that fired, conviction, direction
     (this ALWAYS runs, independent of the 13:00 UTC pick-time gate, so the
     scoreboard is visible no matter what time this script happens to run)
  2. shows what select_pick() would choose RIGHT NOW, guards and all
  3. runs daily_pick.run_daily_pick(private, live_feed, demo_feed, state,
     dry=True) — the actual per-cycle decision (reconcile / holding /
     waiting / would_enter, whichever applies at the moment this runs),
     proving dry mode makes zero orders and zero state writes

Places NO orders, sets NO leverage, makes NO state/log/notify side effect.

Run:  python3 step53_pick_smoke.py
"""

from __future__ import annotations

import copy

import config
from blofin_private import BlofinDemoPrivate, load_env


def main():
    print("=" * 78)
    print("DAILY PICK SMOKE TEST — REAL BloFin data, dry run, zero orders")
    print("=" * 78)

    env = load_env()
    live_feed, _ = config.make_exchange("live")     # PROD market data
    demo_feed, _ = config.make_exchange("demo")      # DEMO market data + specs
    private = BlofinDemoPrivate(env["BLOFIN_DEMO_API_KEY"],
                                env["BLOFIN_DEMO_API_SECRET"],
                                env["BLOFIN_DEMO_PASSPHRASE"])

    import daily_pick as dp
    from step5_paper_trade import load_state

    print(f"\nUNIVERSE: {dp.UNIVERSE}")
    print("(see daily_pick.py's module docstring for why this list is "
          "short — a BloFin DEMO-host availability limit, censused live, "
          "not a design choice)")

    # -- 0. universe probe: what's actually tradeable on demo right now -----
    print("\n-- universe probe (real DEMO candle fetch per symbol) --")
    dp._active_universe_cache = None
    active = dp._probe_universe(demo_feed)
    for sym in dp.UNIVERSE:
        tag = "ACTIVE" if sym in active else "DROPPED (demo unavailable)"
        print(f"  {sym:12s} {tag}")

    # -- 1. FULL ranked scoreboard, unconditionally -------------------------
    print("\n" + "=" * 78)
    print("FULL SCOREBOARD (real PROD candles, every named instrument)")
    print("=" * 78)
    analysis = dp.analyze_universe(live_feed, dp.UNIVERSE)
    ranked = sorted(analysis,
                    key=lambda a: (a["ok"] and not a["stale"],
                                   a["conviction"] if a["conviction"] is not None else -1),
                    reverse=True)
    header = (f"{'symbol':12s} {'status':8s} {'conv':>6s} {'dir':6s} "
             f"{'long':>6s} {'short':>6s} {'funding':>9s}  components")
    print(header)
    print("-" * len(header))
    for a in ranked:
        if not a["ok"]:
            print(f"{a['symbol']:12s} {'FETCH-X':8s} {'':>6s} {'':6s} "
                  f"{'':>6s} {'':>6s} {'':>9s}  {a['error']}")
            continue
        if a["stale"]:
            print(f"{a['symbol']:12s} {'STALE':8s} {'':>6s} {'':6s} "
                  f"{'':>6s} {'':>6s} {'':>9s}  frozen last-3 1h closes")
            continue
        fb = f"{a['funding_bps']:+.2f}bp" if a["funding_bps"] is not None else "n/a"
        comp_str = ", ".join(
            f"{dp.COMPONENT_LABEL.get(c['name'], c['name'])}"
            f"(+{c['long']:.0f}L/+{c['short']:.0f}S)"
            for c in a["components"]) or "(none fired)"
        print(f"{a['symbol']:12s} {'ok':8s} {a['conviction']:6.1f} "
              f"{a['direction']:6s} {a['long_score']:6.1f} "
              f"{a['short_score']:6.1f} {fb:>9s}  {comp_str}")

    # -- 2. what select_pick() would choose right now ------------------------
    print("\n" + "=" * 78)
    print("SELECTION WALK (guards a-d)")
    print("=" * 78)
    chosen, boredom, skips = dp.select_pick(analysis, private, demo_feed,
                                            load_state())
    for sym, reason in skips:
        print(f"  SKIP {sym}: {reason}")
    if chosen is None:
        print("\n>>> RIGHT NOW: nothing clears every guard — the book would "
              "book NOTHING this cycle (retries next cycle). <<<")
    else:
        cand, spec = chosen
        state_now = load_state()
        plan = dp._build_entry_plan(cand, spec, state_now.get("virtual_equity", 0.0),
                                    boredom)
        explain = dp._explain(cand)
        print(f"\n>>> RIGHT NOW this book WOULD PICK: "
              f"{cand['direction'].upper()} {cand['symbol']} "
              f"({dp.NICE_NAMES.get(cand['symbol'], cand['symbol'])}) — "
              f"conviction {cand['conviction']:.0f}%"
              f"{' [BOREDOM PICK, half size]' if boredom else ''}")
        print(f"    why: {explain}")
        print(f"    sizing: {plan['contracts']:.4g} ct (~${plan['notional']:,.0f} "
              f"notional, {plan['leverage']:.0f}x leverage, "
              f"{plan['alloc']*100:.1f}% of equity)")
        print(f"    ref price ~{plan['ref_price']:,.4f} | est TP "
              f"{plan['tp_ref']:,.4f} | est SL {plan['sl_ref']:,.4f} | "
              f"stop {plan['stop_pct']:.2f}% / target {plan['target_pct']:.2f}%")
        print(f"    instrument spec: contract_value={spec['contract_value']} "
              f"min_size={spec['min_size']} lot_size={spec['lot_size']} "
              f"max_leverage={spec['max_leverage']}")

    # -- 3. current book state + the real dry-mode cycle ----------------------
    state = load_state()
    dp_state_before = state.get("daily_pick")
    print("\n" + "=" * 78)
    print("CURRENT daily_pick STATE")
    print("=" * 78)
    print(f"  last_pick_date   : {(dp_state_before or {}).get('last_pick_date')}")
    print(f"  open_trade       : {(dp_state_before or {}).get('open_trade')}")
    print(f"  conviction_ledger: {(dp_state_before or {}).get('conviction_ledger')}")
    print(f"  picks logged     : {len((dp_state_before or {}).get('picks', []))}")
    print(f"  shared virtual_equity: ${state.get('virtual_equity', 0):,.2f}")

    # snapshot BEFORE the call: run_daily_pick does an unconditional
    # state.setdefault("daily_pick", ...) up front (exactly like every
    # other book's run_* — see newsdesk.py's identical `nd = state.setdefault(...)`
    # pattern) even in dry mode, which harmlessly populates the IN-MEMORY
    # dict with fresh defaults. That's not a persisted write; comparing a
    # deep-copied snapshot of the true PRE-call value against what actually
    # got persisted (state_after, freshly reloaded from disk/cloud) is the
    # real proof, not comparing live-mutated dict identity.
    dp_snapshot_before = copy.deepcopy(state.get("daily_pick"))

    print("\n" + "=" * 78)
    print("run_daily_pick(private, live_feed, demo_feed, state, dry=True)")
    print("=" * 78)
    result = dp.run_daily_pick(private, live_feed, demo_feed, state, dry=True)
    print(f"\nDECISION SUMMARY: {result}")

    # -- 4. prove dry mode made no PERSISTED state changes ---------------------
    state_after = load_state()
    unchanged = dp_snapshot_before == state_after.get("daily_pick")
    print(f"\nstate unchanged by dry run: {'YES' if unchanged else 'NO -- BUG'}")


if __name__ == "__main__":
    main()
