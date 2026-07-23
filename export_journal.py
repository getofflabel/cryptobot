"""
export_journal.py — human-readable memory, the way the TradingBotV2 PDF does it.

Wallace was right: we had the memory FUNCTION (cloud JSON, auto-bench) but not
the openable FILES. This writes them, from the live cloud state + log:

  data/ledger.csv    — every trade & decision, exact PDF header, opens in Excel
  data/learnings.md  — plain-English lessons + per-trigger scorecards + the
                       AI judges' standings, readable like a diary

The hourly cloud run refreshes and commits these, so the repo always holds a
current, readable history of the bot's life.
"""

from __future__ import annotations

import csv
import json
import os

from step5_paper_trade import load_state

LOG_FILE = "trades_log.jsonl"


def _cloud_log():
    """Pull the full event log from Supabase (the cloud source of truth)."""
    try:
        import requests
        from blofin_private import load_env
        env = load_env()
        r = requests.post(
            f"{env['CRYPTOBOT_SUPABASE_URL']}/rest/v1/rpc/cryptobot_log_tail",
            headers={"apikey": env["CRYPTOBOT_SUPABASE_ANON"],
                     "Authorization": f"Bearer {env['CRYPTOBOT_SUPABASE_ANON']}",
                     "Content-Type": "application/json"},
            json={"secret": env["CRYPTOBOT_STATE_SECRET"], "n": 2000},
            timeout=20)
        return r.json() or []
    except Exception:
        # local fallback
        out = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE) as f:
                for line in f:
                    try:
                        out.append(json.loads(line))
                    except Exception:
                        pass
        return out


def write_ledger(events):
    """data/ledger.csv — the PDF's exact header."""
    os.makedirs("data", exist_ok=True)
    rows = []
    for e in events:
        a = e.get("action", "")
        if a in ("enter", "tact_enter", "amp_enter"):
            rows.append([e.get("logged_at", ""), e.get("symbol", "BTC-USDT"),
                         "BUY", e.get("fill_price", ""), e.get("contracts", ""),
                         e.get("trigger", a), "demo", "open", ""])
        elif a in ("ledger", "tact_exit", "amp_exit"):
            pnl = e.get("realized_pnl", "")
            outcome = "win" if isinstance(pnl, (int, float)) and pnl > 0 else "loss"
            rows.append([e.get("logged_at", ""), "BTC-USDT", "SELL",
                         e.get("exit_price", ""), "", e.get("reason", a),
                         "demo", outcome, pnl])
        elif a in ("sentiment_veto", "tact_veto", "memory_skip"):
            rows.append([e.get("logged_at", ""), "BTC-USDT", "SKIP", "", "",
                         a, "demo", "skipped", ""])
    with open("data/ledger.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "symbol", "action", "price", "quantity",
                    "reason", "mode", "outcome", "pnl"])
        w.writerows(rows)
    return len(rows)


def write_learnings(state):
    """data/learnings.md — the readable diary."""
    os.makedirs("data", exist_ok=True)
    lines = ["# LEARNINGS — the bot's own diary (plain English)\n",
             f"Ledger: ${state.get('virtual_equity', 0):,.2f} / "
             f"goal ${state.get('goal', 2000):,.0f}\n"]

    stats = state.get("trigger_stats", {})
    if stats:
        lines.append("\n## Scorecard by strategy (live trades)\n")
        for trig, s in stats.items():
            n, pnl, wins = s.get("n", 0), s.get("pnl", 0), s.get("wins", 0)
            exp = pnl / n if n else 0
            benched = trig in state.get("benched_triggers", [])
            lines.append(f"- **{trig}**: {n} trades, {wins}W/{n - wins}L, "
                         f"expectancy ${exp:+.2f}/trade"
                         + ("  🪑 BENCHED (proved bad live)" if benched else ""))

    sr = state.get("situation_room", {}).get("models", {})
    if sr:
        lines.append("\n## AI news judges (on probation)\n")
        for model, m in sr.items():
            n, hits = m.get("n", 0), m.get("hits", 0)
            acc = hits / n * 100 if n else 0
            lines.append(f"- **{model}**: {hits}/{n} graded calls "
                         f"({acc:.0f}% right)")

    lessons = state.get("lessons", [])
    if lessons:
        lines.append("\n## Trade reviews (newest first)\n")
        for L in reversed(lessons[-40:]):
            lines.append(f"### {L.get('date', '')} — {L.get('trigger', '')}")
            lines.append(f"- {L.get('trade', '')}")
            if L.get("conditions"):
                lines.append(f"- conditions: {L['conditions']}")
            lines.append(f"- **lesson:** {L.get('why', '')}\n")
    else:
        lines.append("\n_No completed trades yet — reviews appear here as the "
                     "bot trades. A quiet market means no forced trades._\n")

    with open("data/learnings.md", "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    state = load_state()
    events = _cloud_log()
    n = write_ledger(events)
    write_learnings(state)
    print(f"journal exported: {n} ledger rows, learnings.md refreshed")


if __name__ == "__main__":
    main()
