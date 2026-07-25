"""
breakout_book.py — THE BREAKOUT BOOK: real BloFin DEMO orders on BTC-USDT,
running round 87's SEALED-PASSED volume-gated Bollinger breakout — the one
strategy of round 86-94's whole overnight sweep that survived a true sealed
test on real, untouched-before data. Structural template: diver.py (BTC-
USDT, bidirectional, book_ledger attribution, hardened double-read
_ensure_bracket) crossed with gold_book.py's "recompute everything fresh
every cycle, mark the bar processed on every branch" idempotency style,
since here BOTH entry and exit are driven by the same recomputed per-bar
signal (diver's exit is time-based and doesn't need that).

THE VALIDATED RULE — FROZEN, SEALED-PASSED, DO NOT ALTER
  step86_specified.py FAMILY C, "Bollinger breakout 20/2.5" + volume gate
  1.2x, reproduced and sealed-tested verbatim in step87_sealed_breakout.py.
  Imported here, never reimplemented: bollinger_breakout_signal() and
  volume_gate_entry() from step86_specified.py, bb_bands() from
  step76_indicators.py (only for the informational band values in
  logs/dry-mode — the signal itself never reads them separately).

    Symbol:      BTC-USDT only (see SCOPE below — round 89 killed the
                 expansion story)
    Timeframe:   1h, CLOSED bars only (enforced by the exchange adapter's
                 own "confirmed" flag — see gold_book.py's DATA section for
                 the exact mechanism; not reimplemented here either)
    Entry LONG:  close > upper Bollinger Band (period 20, 2.5 std) AND that
                 bar's volume >= 1.2x its trailing 20-bar average volume
    Entry SHORT: close < lower band, same volume condition
    Exit:        close back through the band midline (the 20-period SMA).
                 No fixed take-profit — the midline IS the exit.

  Sealed results (round 87, BTC, never re-derive — record only):
    train +$14.87/trade -> val +$5.21/trade -> SEALED +$6.97/trade on 242
    trades, ~191 trades/year, 36.4% win rate, avg win +$196.81, avg loss
    -$101.51 (step87_results.md / step87_table.csv).

  DO NOT ADD FILTERS. DO NOT ADD AN EYE GATE (round 83 shipped one, round
  88 had to rip it out). DO NOT ADD A TAKE-PROFIT. Every deviation from the
  config above invalidates the sealed test — this file exists to run it
  EXACTLY, not to improve it.

SCOPE — BTC ONLY, ON PURPOSE
  Round 87 sealed-passed BTC AND ETH. Round 89 replayed the frozen config
  with zero tuning on nine more assets (SOL, XRP, DOGE, BNB, ADA, LINK,
  AVAX, LTC, DOT) and found it does NOT generalize: 6 of 9 fail outright,
  and the one apparent survivor (AVAX) is exactly what chance predicts
  from nine coin-flip windows (~1.1 expected by luck, 1 observed — no
  evidence). Round 89 also found altcoin single-trade adverse moves of
  16%-32% against entry, vs BTC's tightest-in-the-field 3.93% — a
  completely different risk geometry that a shared stop distance could
  never safely cover. ETH stayed flagged fragile (two consecutive halving
  cycles baked into its "edge") even though it sealed-passed. This file
  trades BTC-USDT ONLY. Extending it to ETH or anything else is a new,
  separate decision this file does not make.

THE 6% DISASTER STOP — required for live safety, calibrated to be
non-binding
  This strategy has NO fixed stop by design (the midline is the only
  planned exit) — unsafe live on its own, because a worker outage leaves a
  naked position with nothing watching it. Round 89 measured the worst
  adverse excursion across all 242 sealed BTC trades: **-3.93%** (see
  step89_results.md, "worst single-trade adverse move"). A stop at **6%**
  sits outside every trade in the tested sample, so it can never fire on
  behaviour the sealed test actually produced — it changes nothing about
  the validated result. It exists purely so a crash or an outage between
  decision cycles has a floor under it. It is placed as a REAL exchange-
  side stop order (place_tpsl, no tp_price) at entry — never a book-
  computed close-based exit executed after the fact — so protection lives
  on BloFin's own matching engine even if this process is down.
  DO NOT TIGHTEN THIS NUMBER because it "never fires in backtest" — that
  is the point of it, not a sign it is wasted. It is disaster insurance,
  not a working part of the edge.

LEVERAGE & SIZING
  Expectancy is 0.0641% of notional per trade (+$6.97 / 242 trades on the
  contract-notional scale step87's cost model uses). Notional is sized at
  LEVERAGE (2.0x) times the CURRENT shared book equity
  (state["virtual_equity"]) — full equity, not a fractional allocation
  like the other books' ALLOC constants; there is no separate ALLOC here
  on purpose, this book gets the whole ledger's leverage dial to itself.
  At 2x, the strategy's own historical worst drawdown (round 89: -23.3%
  max drawdown on the sealed BTC sample, computed here as ~24.7% of one
  position's own notional under this book's cost/sizing assumptions)
  scales to roughly 49% of account equity in the worst historical case.
  That is a DEMO-phase choice, made knowingly aggressive so the edge is
  visible on a small demo account — it is NOT a real-money sizing
  recommendation and MUST be revisited (almost certainly down) before this
  book is ever pointed at a funded account. Isolated margin. Market orders
  only (execute_market_clips — see step5_paper_trade.py's OWNER'S LAW
  docstring: a buy/sell order only ever exists when we truly want it NOW,
  never resting).

THE COLLISION PROBLEM — why this book uses book_ledger.py, not its own math
  daily_pick.py ALSO trades BTC-USDT on this same netted BloFin account
  (its UNIVERSE is BTC/ETH/SOL/XAUT), and five other books already share
  this exact symbol (the ride, the strikes, the shorts lab, the
  apprentice, the newsdesk, the diver). Two books quietly fighting over
  one netted symbol is exactly what caused this project's 2026-07-23
  incident (see book_ledger.py's own module docstring) and the gold
  false-alarm loop that followed it. Unlike gold_book.py (whose symbol,
  XAUT-USDT, is exclusive to it plus one carved-out exception it checks by
  hand), BTC-USDT is inherently, permanently multi-book — so this file
  registers itself as book_ledger.py's "breakout" key
  (recorded_book_positions, edited alongside this file) and reconciles
  through the SAME shared functions diver.py already uses:
  attributed_position(net, state, "breakout") is this book's own slice of
  the netted exchange position (net minus every OTHER book's own recorded
  claim); unexplained_position(net, state) is whatever's left once EVERY
  book's claim, including this one, is subtracted out.

  OWNERSHIP HANDSHAKE: a net position fully explained by another book's
  own recorded claim (unexplained ~= 0) is left completely alone — never
  flattened, never adjusted, not even logged as a concern. This book only
  ever acts on ITS OWN recorded trade. If that trade's own attributed
  slice goes to ~0 while the book's own record still says "open", the 6%
  disaster stop fired (or someone closed it by hand) — reconciled as an
  exit, exactly gold_book's "book says open, exchange shows it gone"
  pattern. If NO book's claim explains some slice of the net, that slice
  is a genuine anomaly — alerted ONCE per episode (state["breakout_book"]
  ["unexplained_alerted"], cleared the moment it resolves), mirroring
  gold_book's "alert once, not every cycle" discipline exactly. UNLIKE
  gold_book, an unexplained slice does NOT halt this book's own trading
  for the cycle: on gold_book's near-exclusive symbol an unexplained
  position is itself surprising and worth standing down over, but BTC-USDT
  having other books' exposure on it is the ordinary, everyday case here,
  not an anomaly — diver.py already established this precedent (it warns
  and keeps operating). This book's own _direction_gate (below) is the
  real safety net: it independently refuses to open a position that would
  physically oppose whatever the raw exchange net currently is, regardless
  of whether that net is "explained" or not, so a genuine anomaly can
  never be quietly deepened by a fresh order on top of it.

DIRECTION GATE (mirrors diver.py's exactly, same reasoning): LONG requires
  net not already materially short; SHORT requires net not already
  materially long, AND that no other BTC-USDT book is currently open or
  armed (book_ledger.recorded_book_positions, "breakout" itself excluded,
  plus newsdesk's own "pending" armed state) — the same asymmetry diver.py
  chose: every long-side sniper on this account already leans long, so
  shorts are where multiple aggressive books stacking margin on one demo
  account gets genuinely risky, and this book's short side simply stands
  down rather than piling onto whatever else already owns BTC's short
  side.

ENTRY SEMANTICS — why this is a bar-over-bar TRANSITION check, not a plain
  "is price outside the band right now" check
  bollinger_breakout_signal() is a persistent hysteresis state machine
  (stays +1/-1 from the breakout bar until the midline-cross exit bar,
  0 otherwise) and volume_gate_entry() gates ONLY the exact 0->nonzero
  transition bar — if that one bar's volume fails the 1.2x test, the
  WHOLE excursion is suppressed until price returns to 0 (a fresh midline
  touch) and re-attempts; later bars inside an already-blocked excursion
  do NOT get a second, independent volume check. This file recomputes
  BOTH functions fresh, over the FULL pulled candle series, every single
  cycle (no incremental state carried between calls — the same discipline
  gold_book.py's _decision()/_compute_trail_floor() and diver.py's
  _decision() already use, for the same reason: recomputed-fresh can never
  desync from a stored approximation of itself). The live entry decision
  then reads exactly two numbers off that recomputed series: gated[-1]
  (now) and gated[-2] (one bar ago). A fresh entry fires ONLY when
  gated[-2] == 0 and gated[-1] != 0 — the literal transition bar, matching
  volume_gate_entry()'s own definition exactly, not a looser "price is
  currently outside a band" reimplementation (see step87_sealed_breakout's
  own comment: the entry gate is checked "only at the flat->nonzero
  transition bar" — this file's whole reason for existing is to run that
  rule, not a paraphrase of it).

  DELIBERATE CONSEQUENCE: if this process is down across the actual
  transition bar (a crash, a redeploy, an outage), this book does NOT
  retroactively chase that excursion once it comes back — gated[-1] would
  still read nonzero, but gated[-2] would also already be nonzero (not a
  fresh transition relative to THIS bar), so no entry fires. That
  excursion is simply missed, permanently, for that one occurrence — a
  conservative, safe choice: it never enters at a worse price on a bar it
  never actually evaluated the volume gate on live, and it can never
  double up if it comes back mid-excursion. The exit side of the same
  signal has no equivalent gap: while HOLDING, this book compares
  gated[-1] against its own recorded direction every cycle (not a
  transition check), so a held position is always correctly exited on the
  first live cycle after the midline cross, outage or not.

RECONCILIATION / IDEMPOTENCY: state["breakout_book"]["last_bar_ts"]
  records the 1h bar timestamp this book last decided on (entered, stood
  down, saw no signal, or exited) — gold_book's "every bar exactly once"
  discipline, generalized here to also cover the exit branch (unlike
  diver.py, whose exit is time-based and does not need this). Every
  terminal branch marks it before returning, so a second call within the
  same still-forming bar (the daemon's shock-triggered full_cycle stacking
  on top of the hourly one, for example) is always a clean no-op.

DRY MODE: run_breakout_book(..., dry=True) computes and prints the full
  decision every cycle would make (reconcile, signal, gate, sizing, the
  disaster-stop preview) with NO orders placed and NO state/log/notify
  side effects — same contract as gold_book.py's and diver.py's dry modes.

WIRING: called from daemon.py's full_cycle and hourly.py's backstop loop,
  same handoff pattern as gold_book/diver (daemon owns it when alive;
  hourly.py only runs it when the daemon heartbeat is stale). Safe to call
  every cycle: idempotent per 1h bar, reconciles against the exchange's
  own position every time before deciding anything.
"""

from __future__ import annotations

import time

import pandas as pd

from book_ledger import (attributed_position, recorded_book_positions,
                         unexplained_position)
from step5_paper_trade import (CONTRACT_BTC, LOT, execute_market_clips,
                               log_event, notify, now_utc,
                               record_trade_outcome, save_state)
from step76_indicators import bb_bands
from step86_specified import bollinger_breakout_signal, volume_gate_entry

SYMBOL = "BTC-USDT"
TIMEFRAME = "1h"

# -- the validated rule's exact config (step86 FAMILY C / step87 sealed
#    exam — see module docstring) -------------------------------------------
BB_N = 20              # Bollinger period
BB_K = 2.5             # Bollinger std multiplier
VOL_N = 20             # trailing volume average window
VOL_MULT = 1.2         # breakout-bar volume gate, x trailing 20-bar average

# ~50 days of 1h bars — well over the ~191 trades/year (roughly one every
# 2 days) this edge fires at, so the persistent hysteresis signal (see
# ENTRY SEMANTICS above) has many full trade cycles to self-correct away
# from the cold-start "assume flat" default before reaching the latest
# bar. Kept comfortably under BloFin's own 1440-bars/request cap
# (exchange.py BlofinExchange.MAX_CANDLES_PER_REQUEST) — no pagination
# needed.
CANDLE_BARS = 1200

# -- disaster stop & leverage (see module docstring for the full reasoning) -
DISASTER_STOP_PCT = 6.0   # % from entry — outside every one of the 242
                          # sealed trades' worst adverse move (-3.93%,
                          # measured directly off step87_table.csv's BTC
                          # test rows: for each trade, the worst high/low
                          # excursion against entry while it was open).
                          # DO NOT TIGHTEN: "never fires in
                          # backtest" is this number working as intended,
                          # not evidence it is wasted. It exists to survive
                          # an outage or a gap, nothing else.
LEVERAGE = 2.0            # DEMO-phase sizing dial (2026-07-24). Notional =
                          # virtual_equity * LEVERAGE (full book equity,
                          # 2x leveraged — no separate ALLOC fraction here,
                          # unlike the other books). At 2x, this strategy's
                          # own historical worst drawdown (peak-to-trough
                          # -$2,686 on the 242 sealed BTC trades = 24.7% of
                          # the $10,870 average notional they were sized
                          # at; step87_results.md quotes -23.3% from a
                          # running-equity base, same event, two bases)
                          # scales to roughly 49% of account equity in the
                          # worst historical case. Knowingly aggressive for
                          # a small DEMO account — MUST be revisited
                          # (almost certainly down) before real money.

ENTRY_FEE_BPS = 6.0        # BloFin taker fee — every order here is a plain
EXIT_FEE_BPS = 6.0         # market order, always taker-side (entry AND
                           # exit — the exit is either this book's own
                           # reduce-only market close on a midline cross,
                           # or the disaster stop firing at market; neither
                           # is ever a maker fill)


def _fmt_utc(ts) -> str:
    return f"{pd.Timestamp(ts):%Y-%m-%d %H:%M} UTC"


# ===========================================================================
# signal — imported functions only, never reimplemented (see module
# docstring's THE VALIDATED RULE section)
# ===========================================================================

def _load_1h(live_feed) -> pd.DataFrame:
    """CANDLE_BARS 1h bars from the repo's own BloFin adapter. get_candles
    already discards the still-forming bar via BloFin's own "confirmed"
    flag (see exchange.py) — "only ever act on a CLOSED bar" is enforced by
    the adapter, not by anything here, same guarantee gold_book.py and
    diver.py rely on."""
    d = live_feed.get_candles(SYMBOL, TIMEFRAME, CANDLE_BARS)
    return d.sort_values("timestamp").reset_index(drop=True)


def _decision(d: pd.DataFrame) -> dict:
    """Pure: recomputes the imported bollinger_breakout_signal() and
    volume_gate_entry() fresh over the FULL series `d` and reads the
    latest CLOSED bar's state. No state mutation, no stored hysteresis —
    dry mode and the live path call this exact same function, so they can
    never drift apart. See the module docstring's ENTRY SEMANTICS section
    for exactly what "entry_direction" means (a bar-over-bar transition
    check, not "is price outside the band right now")."""
    base_sig = bollinger_breakout_signal(d)
    vol_avg20 = d["volume"].rolling(VOL_N).mean().shift(1)
    vol_ok = d["volume"] >= VOL_MULT * vol_avg20
    gated = volume_gate_entry(base_sig, vol_ok)
    _, lo, mid, up = bb_bands(d, BB_N, BB_K)

    i = len(d) - 1
    cur = float(gated.iloc[i])
    prev = float(gated.iloc[i - 1]) if i > 0 else 0.0
    fresh_transition = (prev == 0.0 and cur != 0.0)
    entry_direction = int(cur) if fresh_transition else 0

    vol_avg_v = vol_avg20.iloc[i]
    mid_v, up_v, lo_v = mid.iloc[i], up.iloc[i], lo.iloc[i]
    return {
        "bar_ts": _fmt_utc(d["timestamp"].iloc[i]),
        "close": float(d["close"].iloc[i]),
        "mid": float(mid_v) if pd.notna(mid_v) else None,
        "upper": float(up_v) if pd.notna(up_v) else None,
        "lower": float(lo_v) if pd.notna(lo_v) else None,
        "volume": float(d["volume"].iloc[i]),
        "vol_avg20": float(vol_avg_v) if pd.notna(vol_avg_v) else None,
        "vol_ok": bool(vol_ok.iloc[i]) if pd.notna(vol_avg_v) else False,
        "base_sig": float(base_sig.iloc[i]),
        "prev_gated": prev,
        "gated": cur,
        "entry_direction": entry_direction,
    }


# ===========================================================================
# direction gate (mirrors diver.py's exactly — see module docstring)
# ===========================================================================

def _other_btc_book_active(state: dict) -> bool:
    """True if ANY other BTC-USDT book (via book_ledger's shared
    accounting, "breakout" itself excluded) holds a position, or newsdesk
    has an armed-but-not-yet-filled pending trade."""
    recorded = recorded_book_positions(state)
    if any(abs(v) > LOT / 2 for k, v in recorded.items() if k != "breakout"):
        return True
    if state.get("newsdesk", {}).get("pending"):
        return True
    return False


def _direction_gate(direction: int, net: float, state: dict) -> str | None:
    """Returns a stand-down reason string, or None if the entry is clear."""
    if direction > 0:
        if net <= -LOT / 2:
            return f"long would oppose existing net {net:+.2f} ct"
        return None
    if net >= LOT / 2:
        return f"short would oppose existing net {net:+.2f} ct"
    if _other_btc_book_active(state):
        return "short stand-down — another BTC book is already open/armed"
    return None


# ===========================================================================
# bracket protection (hardened double-read, mirrors diver.py/newsdesk.py
# exactly, generalized to either direction)
# ===========================================================================

def _cleanup_orders(private, symbol, t):
    try:
        if t.get("tpsl_id"):
            private.cancel_tpsl(symbol, t["tpsl_id"])
    except Exception:
        pass


def _bracket_present(private, symbol, t) -> bool:
    brackets = private.pending_tpsl(symbol)
    if not brackets:
        return False
    our_id = t.get("tpsl_id")
    if our_id:
        return any(str(b.get("tpslId")) == str(our_id) for b in brackets)
    return True


def _ensure_bracket(private, symbol, state, t):
    """SELF-HEALING PROTECTION, identical hardening to diver.py's copy:
    read pending_tpsl TWICE 4s apart, only re-arm if BOTH reads come back
    empty AND a fresh net-position read confirms the position still
    exists. A read exception means 'don't know' — do nothing."""
    if not t or not t.get("sl_price"):
        return
    try:
        if _bracket_present(private, symbol, t):
            return
        time.sleep(4)
        if _bracket_present(private, symbol, t):
            return
        net = private.net_position_contracts(symbol)
        if abs(net) < LOT / 2:
            return
    except Exception as e:
        print(f"  [BREAKOUT] bracket check skipped (unreliable read): "
              f"{str(e)[:80]}")
        return

    try:
        close_side = "sell" if t["direction"] > 0 else "buy"
        tpsl_id = private.place_tpsl(symbol, close_side, t["contracts"],
                                     None, t["sl_price"])
        t["tpsl_id"] = tpsl_id
        save_state(state)
        print(f"  [BREAKOUT] ⚠️ disaster stop was MISSING — re-armed "
              f"{t['sl_price']:,.1f}")
        notify("\U0001f6e1️ Stop re-armed (demo)",
              f"The Breakout Book's disaster stop had vanished — re-placed. "
              f"Now back at ${t['sl_price']:,.0f}.")
    except Exception as e:
        print(f"  [BREAKOUT] disaster stop re-arm FAILED: {str(e)[:80]}")
        notify("⚠️ The Breakout Book UNPROTECTED (demo)",
              "disaster stop missing and re-arm failed — check BloFin now")


def _book_exit(state, t, exit_price, exit_fee_bps, reason):
    """Close the Breakout Book's trade on its own ledger line. Direction-
    aware: profit on a rise when long, on a fall when short (mirrors
    diver._book_exit exactly)."""
    size_btc = t["contracts"] * CONTRACT_BTC
    gross = t["direction"] * (exit_price - t["entry_price"]) * size_btc
    fees = (t["entry_price"] * t.get("entry_fee_bps", ENTRY_FEE_BPS)
            + exit_price * exit_fee_bps) * size_btc / 10_000
    realized = round(gross - fees, 2)
    state["virtual_equity"] = round(state["virtual_equity"] + realized, 2)
    bb = state["breakout_book"]
    rec = {"entry_time": t.get("entry_time"), "entry_price": t["entry_price"],
           "direction": t["direction"], "contracts": t["contracts"],
           "exit_price": round(exit_price, 2), "pnl": realized,
           "reason": reason, "exit_time": now_utc()}
    bb.setdefault("trades", []).append(rec)
    del bb["trades"][:-200]
    bb["realized_pnl_total"] = round(bb.get("realized_pnl_total", 0.0) + realized, 2)
    bb["open_trade"] = None
    save_state(state)
    eq = state["virtual_equity"]
    side = "LONG" if t["direction"] > 0 else "SHORT"
    print(f"  [BREAKOUT] {reason}: PnL ${realized:+,.2f} -> ledger ${eq:,.2f}")
    log_event({"action": "breakout_exit", "reason": reason,
               "direction": t["direction"], "exit_price": exit_price,
               "realized_pnl": realized, "virtual_equity": eq})
    record_trade_outcome(state, "bollinger_breakout", realized)
    notify(f"\U0001f4c8 Breakout Book {reason}: ${realized:+,.2f}",
          f"{side} bollinger-breakout trade — ledger ${eq:,.2f} (demo)")
    return realized


def _fresh_book() -> dict:
    return {"open_trade": None, "last_bar_ts": None, "trades": [],
            "realized_pnl_total": 0.0}


# ===========================================================================
# main entrypoint
# ===========================================================================

"""STOOD DOWN 2026-07-25, hours after going live. Read this before
re-enabling anything here.

Round 87 sealed-tested this strategy with `execution="maker"` and it
passed: BTC +$6.97/trade. But this project's OWNER'S LAW (step5_paper_
trade.py, 2026-07-24) requires MARKET orders — taker fills at 6bps a leg
instead of maker's 2bps — because resting maker orders left orphaned
positions on every crash and deploy. So the strategy was validated under
fills we are not allowed to use.

Re-priced with `execution="taker"`, which is what we ACTUALLY do:

    BTC   maker train +$14.49  val  +$5.21   <- what was sealed
          taker train  -$3.66  val  -$8.15   <- what would really happen
    ETH   maker train +$39.59  val +$20.11
          taker train  +$6.78  val  +$3.09

The edge is 0.064% of notional. The maker-to-taker gap is 0.08%. The
execution cost is LARGER THAN THE ENTIRE EDGE, which is exactly why BTC
flips negative. Wallace called it before the numbers did: "$7 a trade on
a 10k position is not an edge, that's just gambling."

So this book does nothing until a variant clears the bar under TAKER
costs. Everything below is kept intact and tested so a taker-viable
version can be dropped straight in. Do NOT re-enable by flipping the flag
without a fresh train/val pass at execution="taker".

THE LESSON, recorded so it cannot repeat: every future backtest must be
run under the SAME execution model the live books use. A validated edge
that assumes fills we cannot get is not a validated edge.
"""

ENABLED = False


def run_breakout_book(private, live_feed, demo_feed, state: dict,
                      dry: bool = False):
    """One cycle. Returns a small summary dict, mainly for tests/smoke."""
    if not ENABLED:
        return {"action": "stood_down",
                "reason": "validated on maker fills, we trade taker — "
                          "BTC val -$8.15/trade under real execution"}
    bb = state.setdefault("breakout_book", _fresh_book())
    t = bb.get("open_trade")
    tag = " DRY" if dry else ""

    # -- reconcile (book-aware attribution, see book_ledger.py) -----------
    net = private.net_position_contracts(SYMBOL)
    attributed = attributed_position(net, state, "breakout")
    unexplained = unexplained_position(net, state)
    recorded_signed = (t["direction"] * t["contracts"]) if t else 0.0
    print(f"  [BREAKOUT{tag}] reconcile: net={net:+.2f} attributed_breakout="
          f"{attributed:+.2f} (recorded {recorded_signed:+.1f}) "
          f"unexplained={unexplained:+.2f}")

    if t and abs(attributed) < LOT / 2:
        # our position is gone — the 6% disaster stop fired (or someone
        # closed it by hand); this is the ONLY way an exit is discovered
        # here besides this book's own midline-cross exit below
        exit_price = t["entry_price"]
        try:
            fills = private.fills(SYMBOL)
            if fills:
                exit_price = float(fills[0]["fillPrice"])
        except Exception:
            pass
        reason = "disaster_stop_fired"
        print(f"  [BREAKOUT{tag}] our {'long' if t['direction'] > 0 else 'short'} "
              f"is gone -> {reason} @ {exit_price:,.1f}")
        if dry:
            print("  [BREAKOUT DRY] would cancel the remaining bracket and "
                  "book this exit — no state/order changes made")
            return {"action": "would_exit", "reason": reason,
                    "exit_price": exit_price}
        _cleanup_orders(private, SYMBOL, t)
        realized = _book_exit(state, t, exit_price, EXIT_FEE_BPS, reason)
        return {"action": "reconciled_exit", "reason": reason,
                "exit_price": exit_price, "pnl": realized}

    if not t:
        if abs(unexplained) > LOT / 2:
            # NOT ours to adopt or flatten — see the module docstring's
            # OWNERSHIP HANDSHAKE. Alert once per episode, keep operating
            # (BTC-USDT sharing exposure with other books is normal here,
            # unlike gold_book's near-exclusive symbol).
            print(f"  [BREAKOUT{tag}] ⚠️ {unexplained:+.2f} ct on "
                  f"{SYMBOL} is claimed by NO book — not adopting, not "
                  f"flattening; still watching for our own signal")
            if not dry:
                log_event({"action": "breakout_unexplained_position",
                           "net": net, "unexplained": round(unexplained, 2)})
                if not bb.get("unexplained_alerted"):
                    bb["unexplained_alerted"] = True
                    save_state(state)
                    notify("⚠️ Unexplained BTC position (demo)",
                          f"{unexplained:+.2f} ct on {SYMBOL} that no book "
                          f"claims — check the app. (One alert per "
                          f"episode.)")
        elif bb.get("unexplained_alerted"):
            bb.pop("unexplained_alerted", None)
            if not dry:
                save_state(state)

    # -- pull the closed 1h series and recompute the signal fresh ---------
    d = _load_1h(live_feed)
    dec = _decision(d)
    print(f"  [BREAKOUT{tag}] {dec['bar_ts']} close {dec['close']:,.1f} | "
          f"mid {_fmt2(dec['mid'])} band[{_fmt2(dec['lower'])}, "
          f"{_fmt2(dec['upper'])}] | vol {dec['volume']:.0f} vs "
          f"{VOL_MULT}x20avg {_fmt2(dec['vol_avg20'])} (ok={dec['vol_ok']}) "
          f"| gated={dec['gated']:+.0f} (prev {dec['prev_gated']:+.0f})")

    # -- holding: the ONLY exit this strategy has is the signal itself
    #    returning to (or flipping past) our held direction ----------------
    if t:
        if dec["gated"] != t["direction"]:
            print(f"  [BREAKOUT{tag}] signal exit — gated {dec['gated']:+.0f} "
                  f"!= held direction {t['direction']:+d} (band midline "
                  f"cross)")
            if dry:
                print(f"  [BREAKOUT DRY] would market-close "
                      f"{t['contracts']:.1f} ct now — no orders placed")
                return {"action": "would_exit", **dec}
            _cleanup_orders(private, SYMBOL, t)
            side = "sell" if t["direction"] > 0 else "buy"
            quote = demo_feed.get_ticker(SYMBOL)
            ref_price = quote.bid if side == "sell" else quote.ask
            fill, was_maker = execute_market_clips(
                private, demo_feed, SYMBOL, side, t["contracts"], ref_price,
                reduce_only=True)
            realized = _book_exit(state, t, fill, EXIT_FEE_BPS, "midline_exit")
            bb["last_bar_ts"] = dec["bar_ts"]
            save_state(state)
            return {"action": "exited", "reason": "midline_exit",
                    "fill": fill, "pnl": realized, **dec}
        if not dry:
            _ensure_bracket(private, SYMBOL, state, t)
            bb["last_bar_ts"] = dec["bar_ts"]
            save_state(state)
        print(f"  [BREAKOUT{tag}] holding {t['contracts']:.1f} ct "
              f"{'long' if t['direction'] > 0 else 'short'} from "
              f"{t['entry_price']:,.1f}, gated still {t['direction']:+d}, "
              f"disaster stop {t['sl_price']:,.1f} verified")
        return {"action": "would_hold" if dry else "hold", **dec}

    # -- flat: only a FRESH transition into a gated signal is an entry ----
    if dry:
        if dec["entry_direction"] == 0:
            print("  [BREAKOUT DRY] no fresh gated transition on the latest "
                  "closed bar — NO ORDER PLACED")
            return {"action": "would_stay_flat", **dec}
        direction = dec["entry_direction"]
        gate_reason = _direction_gate(direction, net, state)
        if gate_reason:
            print(f"  [BREAKOUT DRY] WOULD STAND DOWN — {gate_reason} — NO "
                  f"ORDER PLACED")
            return {"action": "would_stand_down", "reason": gate_reason,
                    "direction": direction, **dec}
        ref_price = dec["close"]
        try:
            ref_price = live_feed.get_ticker(SYMBOL).last
        except Exception:
            pass
        notional = float(state.get("virtual_equity", 0.0)) * LEVERAGE
        contracts = max(LOT, round(notional / ref_price / CONTRACT_BTC / LOT) * LOT)
        if direction > 0:
            sl_est = round(ref_price * (1 - DISASTER_STOP_PCT / 100), 1)
        else:
            sl_est = round(ref_price * (1 + DISASTER_STOP_PCT / 100), 1)
        print(f"  [BREAKOUT DRY] {'LONG' if direction > 0 else 'SHORT'} "
              f"WOULD FIRE — {contracts:.1f} ct (~${notional:,.0f} notional "
              f"at {LEVERAGE:.0f}x book equity) @ ~{ref_price:,.1f} | "
              f"disaster stop {sl_est:,.1f} (6% away, non-binding) | exits "
              f"on the band midline, no fixed TP — NO ORDER PLACED")
        return {"action": "would_enter", "direction": direction,
                "contracts": contracts, "entry_ref": ref_price,
                "est_sl": sl_est, **dec}

    # -- idempotency: this exact bar was already decided on ----------------
    if bb.get("last_bar_ts") == dec["bar_ts"]:
        print(f"  [BREAKOUT] {dec['bar_ts']} already processed — no-op "
              f"(idempotent)")
        return {"action": "noop_already_processed", **dec}

    if dec["entry_direction"] == 0:
        bb["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        return {"action": "no_signal", **dec}

    direction = dec["entry_direction"]
    gate_reason = _direction_gate(direction, net, state)
    if gate_reason:
        bb["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        print(f"  [BREAKOUT] STAND DOWN — {gate_reason}")
        log_event({"action": "breakout_stand_down", "reason": gate_reason,
                   "direction": direction, "net": net,
                   "bar_ts": dec["bar_ts"]})
        notify("\U0001f4c8 Breakout Book skipped (demo)",
              f"{'LONG' if direction > 0 else 'SHORT'} breakout signal "
              f"fired but stood down — {gate_reason}")
        return {"action": "stood_down", "reason": gate_reason,
                "direction": direction, **dec}

    # -- entry --------------------------------------------------------------
    ref_price = dec["close"]
    try:
        ref_price = live_feed.get_ticker(SYMBOL).last
    except Exception:
        pass
    notional = float(state.get("virtual_equity", 0.0)) * LEVERAGE
    contracts = max(LOT, round(notional / ref_price / CONTRACT_BTC / LOT) * LOT)
    side = "buy" if direction > 0 else "sell"

    print(f"  [BREAKOUT] {'LONG' if direction > 0 else 'SHORT'} SIGNAL "
          f"(bollinger_breakout) — {side} {contracts:.1f} ct "
          f"(~${notional:,.0f} notional at {LEVERAGE:.0f}x book equity)")
    private.ensure_leverage(SYMBOL, LEVERAGE)
    try:
        entry, was_maker = execute_market_clips(
            private, demo_feed, SYMBOL, side, contracts, ref_price)
    except Exception as e:
        print(f"  [BREAKOUT] ENTRY FAILED: {str(e)[:100]}")
        log_event({"action": "breakout_entry_failed", "error": str(e)[:200]})
        notify("⚠️ Breakout Book ENTRY FAILED (demo)",
              f"tried to {side} but the order was rejected: {str(e)[:80]}. "
              f"No position opened — check BloFin.")
        bb["last_bar_ts"] = dec["bar_ts"]
        save_state(state)
        return {"action": "entry_failed", "error": str(e)[:120], **dec}

    if direction > 0:
        sl = round(entry * (1 - DISASTER_STOP_PCT / 100), 1)
        close_side = "sell"
    else:
        sl = round(entry * (1 + DISASTER_STOP_PCT / 100), 1)
        close_side = "buy"

    tpsl_id = None
    try:
        tpsl_id = private.place_tpsl(SYMBOL, close_side, contracts, None, sl)
    except Exception as e:
        print(f"  [BREAKOUT] disaster stop FAILED to place: {str(e)[:80]}")
        notify("⚠️ Breakout Book position UNPROTECTED (demo)",
              "position opened but the 6% disaster stop failed to place — "
              "check BloFin now")

    bb["open_trade"] = {
        "trigger": "bollinger_breakout", "direction": direction,
        "contracts": contracts, "entry_price": entry,
        "entry_fee_bps": ENTRY_FEE_BPS, "entry_time": now_utc(),
        "tp_price": None, "sl_price": sl, "tpsl_id": tpsl_id,
        "bar_ts": dec["bar_ts"], "band_mid_at_entry": dec["mid"],
        "band_upper_at_entry": dec["upper"],
        "band_lower_at_entry": dec["lower"],
        "volume_at_entry": dec["volume"],
        "vol_avg20_at_entry": dec["vol_avg20"],
    }
    bb["last_bar_ts"] = dec["bar_ts"]
    save_state(state)
    log_event({"action": "breakout_enter", "direction": direction,
               "fill_price": entry, "contracts": contracts, "sl": sl,
               "maker": was_maker, "bar_ts": dec["bar_ts"]})
    notify(f"\U0001f4c8 THE BREAKOUT BOOK {'LONG' if direction > 0 else 'SHORT'} (demo)",
          f"{side} {contracts:.1f} ct @{entry:,.0f} | disaster stop "
          f"{sl:,.0f} (6%, non-binding) | exits on the band midline, no "
          f"fixed TP")
    return {"action": "entered", "direction": direction, "entry": entry,
           "contracts": contracts, "sl": sl, **dec}


def _fmt2(v):
    return f"{v:,.1f}" if v is not None else "n/a"
