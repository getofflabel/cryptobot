"""
shadow15.py — THE 15-MINUTE SYSTEM, live in shadow mode.

Wallace's wide-stop 15m strategy (the only 15m config ever to win two
evidence windows: train +$15/trade, val +$26/trade over 252 trades):

  ENTRY : 4h trend UP (the champion state) + 15m tape lively (ATR above
          1.5x its long-run median) + 6h momentum positive, on a closed
          15m bar
  GEOMETRY: stop -1.5%, target +4.5% (his "let it breathe" insight,
          measured and vindicated), hard exit after 24h

WHY SHADOW: it failed the 2025-26 sealed test (-$31/t) — the same modern
grind that killed every fast candle strategy. So it trades a SHADOW ledger:
every signal detected on real bars, every fill/stop/target simulated at
bar prices, every result logged — zero real orders. PROMOTION RULE, fixed
in advance: 30+ shadow trades with positive expectancy on FORWARD data
(data that didn't exist when the config was frozen) and it earns a real
slot. If the regime still kills it, the shadow bleeds instead of the
ledger, and we'll have watched it fail for free.

Runs inside the hourly heartbeat: each run replays the last hour's four
closed 15m bars, so no extra cloud minutes and no missed signals.
"""

from __future__ import annotations

from datetime import datetime, timezone

from step5_paper_trade import log_event, notify, save_state
from strategy import atr, vol_gated_ma

STOP_PCT, TGT_PCT = 1.5, 4.5
MAX_HOLD_BARS = 96                     # 24h of 15m bars
ATR_FLOOR = 0.54                       # 1.5 x the 6yr train median (0.361%)
SHADOW_STAKE = 1000.0                  # hypothetical $ per trade, 1x


def _champ_state_now(live_feed) -> int:
    c4 = live_feed.get_candles("BTC-USDT", "4h", 300)
    s = vol_gated_ma(c4, fast=20, slow=100, min_atr_pct=1.5)
    v = s.iloc[-1]
    return int(v) if v == v else 0


def shadow15_cycle(live_feed, state: dict):
    """Replay the last hour's 15m bars for the shadow book."""
    book = state.setdefault("shadow15", {
        "equity": 1000.0, "open": None, "trades": 0, "wins": 0,
        "realized": 0.0})

    c = live_feed.get_candles("BTC-USDT", "15m", 60)
    if len(c) < 40:
        return
    atrp = (atr(c, 14) / c["close"] * 100)
    ret6h = c["close"].pct_change(24) * 100
    recent = c.iloc[-4:]                       # the last hour's closed bars

    t = book.get("open")
    # -- manage an open shadow trade against the new bars ------------------
    if t:
        for _, bar in recent.iterrows():
            t["bars_held"] = t.get("bars_held", 0) + 1
            stop_px = t["entry"] * (1 - STOP_PCT / 100)
            tgt_px = t["entry"] * (1 + TGT_PCT / 100)
            hit_stop = bar["low"] <= stop_px
            hit_tgt = bar["high"] >= tgt_px and not hit_stop   # stop wins ties
            exit_px, reason = None, None
            if hit_stop:
                exit_px, reason = stop_px * 0.9997, "SL"      # slip modeled
            elif hit_tgt:
                exit_px, reason = tgt_px, "TP"                # maker limit
            elif t["bars_held"] >= MAX_HOLD_BARS:
                exit_px, reason = float(bar["close"]), "time"
            if exit_px:
                gross = (exit_px / t["entry"] - 1)
                fees = 0.0002 + (0.0002 if reason == "TP" else 0.0006)
                pnl = round(SHADOW_STAKE * (gross - fees), 2)
                book["equity"] = round(book["equity"] + pnl, 2)
                book["realized"] = round(book["realized"] + pnl, 2)
                book["trades"] += 1
                book["wins"] += pnl > 0
                book["open"] = None
                t = None
                exp = book["realized"] / book["trades"]
                print(f"  [S15 ] shadow {reason}: ${pnl:+,.2f} | "
                      f"{book['trades']} trades, exp ${exp:+,.2f}")
                log_event({"action": "shadow15_exit", "reason": reason,
                           "pnl": pnl, "shadow_equity": book["equity"],
                           "n": book["trades"]})
                if (book["trades"] >= 30 and exp > 0):
                    notify("🕒 15m SYSTEM: promotion case building",
                           f"{book['trades']} fwd trades, exp ${exp:+.2f} — "
                           f"review for real orders")
                break

    # -- new shadow entry on the freshest closed bar -----------------------
    if book.get("open") is None:
        bar = c.iloc[-1]
        i = len(c) - 1
        lively = float(atrp.iloc[i]) > ATR_FLOOR
        mom = float(ret6h.iloc[i]) > 1 if ret6h.iloc[i] == ret6h.iloc[i] else False
        champ = _champ_state_now(live_feed)
        fired = champ == 1 and lively and mom
        if fired:
            book["open"] = {"entry": float(bar["close"]),
                            "time": datetime.now(timezone.utc).isoformat(),
                            "bars_held": 0}
            print(f"  [S15 ] SHADOW ENTRY @ {bar['close']:,.1f} "
                  f"(champ up, ATR {atrp.iloc[i]:.2f}%, 6h {ret6h.iloc[i]:+.1f}%)")
            log_event({"action": "shadow15_enter",
                       "price": float(bar["close"])})
    save_state(state)
