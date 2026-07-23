"""
situation_room.py — AI judgment on breaking news, with EARNED authority.

Runs only on news-triggered wake-ups. A real Claude session (Sonnet, on
Wallace's subscription — his call: Sonnet 5 / Opus 4.8 for this job, never
Fable in the hot path) reads the fresh headlines plus live market state and
issues a structured judgment. THE AUTHORITY LADDER (pre-registered):

  Stage 1 (NOW)    : judgments are logged and auto-graded. Zero authority.
  Stage 2 (EARNED) : >=30 graded calls at >=60% accuracy -> eligible for
                     VETO power (block new longs during judged danger).
                     Promotion is a reviewed decision, not automatic.
  Stage 3 (EARNED+): initiative — only with a longer proven record.

Grading: each judgment records BTC's price. 4 hours later the hourly cycle
scores it — risk_off + price fell = HIT, risk_on + price rose = HIT,
neutral = ungraded. The record is public in every monthly report. This is
how judgment earns what the checkbox strategies earned: with evidence.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from step5_paper_trade import (CLOUD_STATE, _sb_rpc, _SB_SECRET, log_event,
                               notify, save_state)

# Wallace's requirement: don't ASSUME which model judges better — race
# them. Both read every event; both get graded; the standings decide who
# ever earns authority. (Fable never runs in the hot path — his rule.)
MODELS = ["sonnet", "opus"]
GRADE_AFTER_H = 4


def _fresh_headlines(n=6):
    if not CLOUD_STATE:
        return []
    try:
        return _sb_rpc("cryptobot_recent_news",
                       {"secret": _SB_SECRET, "n": n}) or []
    except Exception:
        return []


def run_situation_room(live_feed, symbol, state):
    """One judgment on the current situation. Called on news wake-ups."""
    heads = _fresh_headlines()
    if not heads:
        return
    px = live_feed.get_ticker(symbol).last
    c4 = live_feed.get_candles(symbol, "4h", 30)
    chg24 = (c4["close"].iloc[-1] / c4["close"].iloc[-7] - 1) * 100

    prompt = (
        "You are the situation reader for a Bitcoin trading system. "
        "Fresh headlines (newest first):\n"
        + "\n".join(f"- {h}" for h in heads)
        + f"\n\nMarket: BTC ${px:,.0f}, {chg24:+.1f}% over 24h.\n"
        "Judge the next 4-24 hours for crypto. Respond with ONLY this JSON: "
        '{"stance": "risk_on|risk_off|neutral", "confidence": "low|medium|high", '
        '"reasoning": "<one plain-English sentence>"}'
    )
    sr = state.setdefault("situation_room",
                          {"models": {}, "calls": []})
    for model in MODELS:
        try:
            out = subprocess.run(
                ["claude", "-p", prompt, "--model", model,
                 "--max-turns", "1"],
                capture_output=True, text=True, timeout=120)
            raw = out.stdout.strip()
            j = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
            stance = j.get("stance", "neutral")
            conf = j.get("confidence", "low")
            why = str(j.get("reasoning", ""))[:200]
        except Exception as e:
            err = ""
            try:
                err = f" | rc={out.returncode} err={out.stderr.strip()[:150]}"
            except Exception:
                pass
            print(f"  [SITROOM] {model} judgment failed: {str(e)[:80]}{err}")
            continue
        rec = {"at": datetime.now(timezone.utc).isoformat(), "model": model,
               "stance": stance, "confidence": conf, "reasoning": why,
               "price": px, "graded": None}
        sr["calls"].append(rec)
        print(f"  [SITROOM] {model}: {stance} ({conf}) — {why}")
        log_event({"action": "situation_judgment", "model": model,
                   "stance": stance, "confidence": conf,
                   "reasoning": why, "price": px})
        if stance == "risk_off" and conf in ("medium", "high"):
            m = sr["models"].get(model, {"n": 0, "hits": 0})
            notify(f"🧠 {model} reads RISK-OFF",
                   f"{why} (no authority yet — record {m['hits']}/{m['n']})")
    del sr["calls"][:-200]
    save_state(state)


def grade_judgments(live_feed, symbol, state):
    """Score matured judgments (>=4h old). Called every hourly cycle."""
    sr = state.get("situation_room")
    if not sr or not sr.get("calls"):
        return
    now = datetime.now(timezone.utc)
    px = None
    changed = False
    for rec in sr["calls"]:
        if rec.get("graded") is not None or rec.get("stance") == "neutral":
            continue
        age_h = (now - datetime.fromisoformat(rec["at"])).total_seconds() / 3600
        if age_h < GRADE_AFTER_H:
            continue
        if px is None:
            px = live_feed.get_ticker(symbol).last
        move = (px / rec["price"] - 1) * 100
        model = rec.get("model", "sonnet")
        m = sr.setdefault("models", {}).setdefault(model, {"n": 0, "hits": 0})
        if abs(move) <= 0.15:
            rec["graded"] = "flat-ungraded"
            changed = True
            continue
        hit = (move > 0.15) if rec["stance"] == "risk_on" else (move < -0.15)
        rec["graded"] = "hit" if hit else "miss"
        m["n"] += 1
        m["hits"] += hit
        changed = True
        acc = m["hits"] / m["n"] * 100
        print(f"  [SITROOM] {model} graded {rec['stance']}: {rec['graded']} "
              f"({model} record {m['hits']}/{m['n']} = {acc:.0f}%)")
        if m["n"] >= 30 and acc >= 60 and not m.get("stage2_flagged"):
            m["stage2_flagged"] = True
            notify(f"🧠 {model.upper()} EARNED ITS RECORD",
                   f"{m['hits']}/{m['n']} = {acc:.0f}% over 30+ graded calls "
                   f"— eligible for veto power; review to promote")
    if changed:
        save_state(state)
