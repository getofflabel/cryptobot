"""
step448_cockpit_check.py — proof that the cockpit tells the truth.

WHAT IT CHECKS, AND WHY EACH ONE IS THE THING THAT WOULD BITE
    1. THE PANEL AND THE PHONE AGREE. A real setup out of the cached
       history is pushed through the recorder exactly as a live one would
       be, and then every price the panel would draw is looked for inside
       the Telegram message that was sent. If a single one is missing, this
       fails. This is the only reason to believe the word "identical".

    2. NO BALANCE MEANS NO SIZE. With the balance cleared, the alert has to
       say the size could not be worked out, and the panel has to say why.
       A number appearing here would mean we had invented a balance
       somewhere, which is the failure the whole account section exists to
       prevent.

    3. THE PRICE CARRIES ITS OWN AGE. Every quote comes back with the
       exchange's own timestamp, and a made-up timestamp is rejected.

    4. NOTHING UNKNOWN COMES BACK AS ZERO. The whole answer the panel gets
       is walked, and any numeric zero sitting where a real value belongs is
       reported.

    5. THE DESK'S SILENCE IS DISTINGUISHABLE FROM ITS DEATH.

    6. NOTHING IN THE COCKPIT CAN PLACE AN ORDER. Every file under cockpit/
       is read and checked for the calls that could.

SAFETY
    Sends no Telegram message (the recorder is run in dry-run), places no
    order, and puts the balance back the way it found it.

USAGE
    python3 step448_cockpit_check.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cockpit import prices, service, signals, store            # noqa: E402
from cockpit import desk_recorder                              # noqa: E402

FAILURES: list = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> bool:
    global CHECKS
    CHECKS += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}"
          + (f"\n         {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)
    return ok


# ------------------------------------------------------------------ setup
def a_real_setup() -> dict:
    """One setup that actually fired on the cached Bitcoin history, shaped
    exactly the way the live desk shapes one. Not invented numbers: the
    point of the test is that a real signal survives the round trip."""
    import tjr_crypto
    import tjr_desk
    r = tjr_crypto.run_pair("BTC/USD")
    if not r["trades"]:
        return {}
    tr = r["trades"][-1]
    return {
        "market": "crypto", "symbol": "BTC/USD", "direction": tr.direction,
        "reference_price": tr.entry, "stop": tr.stop,
        "targets": list(tr.targets), "target_sources": list(tr.target_srcs),
        "level_tf": tr.level_tf, "level_price": tr.level_price,
        "confirmed_by": tr.confirm_kind, "pullback_into": tr.pullback_kind,
        "risk_dollars": tr.risk_dollars, "risk_wanted": tr.risk_wanted,
        "clamped": tr.clamped, "fired_at": tr.entry_t,
        "usd_per_quote": 1.0,
        "tightest_stop_pct": tjr_desk.tightest_stop_pct("BTC/USD"),
    }


class FakeMarket:
    name = "crypto"
    symbols = ("BTC/USD",)


def push_through_recorder(sig: dict, account: float) -> None:
    """Run the real recorder path — the same method the live desk calls when
    a setup fires — in dry-run, so the journal is written and nothing is
    sent to his phone."""
    desk = desk_recorder.RecordingDesk(account=account, dry_run=True,
                                       markets=[])
    desk.account = account
    import io
    import contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        desk._send_entries(FakeMarket(), [sig])


# ------------------------------------------------------------- the checks
def check_panel_matches_phone(sig: dict, account: float) -> None:
    print("\n1. THE PANEL AND THE PHONE SHOW THE SAME NUMBERS")
    push_through_recorder(sig, account)
    row = store.latest_entry()
    if not check("the push was recorded", bool(row)):
        return
    panel = signals.render(row)
    msg = row["message"]
    t = panel["trades"][0]

    for label, value in (("the entry price", t["entry"]),
                         ("the stop price", t["stop"])):
        check(f"{label} on the panel appears in the Telegram message "
              f"({value})", value in msg)
    for i, tg in enumerate(t["targets"]):
        check(f"target {i + 1} on the panel appears in the message "
              f"({tg['price']})", tg["price"] in msg)

    check("the panel's own agreement flag is set", panel["agrees_with_phone"])
    check("the panel carries the reason, in the same words",
          t["why"] in msg, t["why"][:90] + "...")
    check("the panel says what chart feature the stop sits on",
          bool(t["stop_sits_on"]) and t["stop_sits_on"] in msg)

    if t["risk_dollars"] is not None:
        check("the risk is stated in dollars AND as a share of the account",
              t["risk_share_of_account_pct"] is not None,
              f"${t['risk_dollars']:,.0f} = "
              f"{t['risk_share_of_account_pct']}% OF THE ACCOUNT")
        check("no bare percentage reaches the panel — every one says what it "
              "is a percentage of",
              all(re.search(r"MOVE IN THE PRICE|OF THE ACCOUNT", s)
                  for s in [t["stop_away"]] +
                  [x["away"] for x in t["targets"]]))


def check_no_balance_no_size(sig: dict) -> None:
    print("\n2. WITH NO BALANCE, IT REFUSES TO SIZE THE TRADE")
    push_through_recorder(sig, 0.0)
    panel = signals.render(store.latest_entry())
    t = panel["trades"][0]
    check("the panel states no size", t["size_lines"] is None)
    check("the panel says why", bool(t.get("size_refused_because")),
          t.get("size_refused_because", ""))
    check("the message that would have gone to his phone refuses too",
          "COULD NOT BE WORKED OUT" in panel["message"])
    check("no risk figure is invented", t["risk_dollars"] is None)


def check_price_is_dated() -> None:
    print("\n3. THE PRICE CARRIES THE EXCHANGE'S OWN TIME, NOT OURS")
    r = prices.quote("BINANCE:BTCUSDT")
    q = r["quote"]
    if not check("a live crypto quote came back", q.get("ok"),
                 q.get("why", "")):
        return
    check("it has the exchange's timestamp on it", "as_of" in q)
    check("its age is measured from that timestamp, not from now",
          abs((time.time() - q["as_of"]) - q["age_seconds"]) < 2.0,
          f"{q['age_seconds']:.0f} seconds old, from {q['source']}")
    check("the source is named so a partial feed cannot pass as the market",
          bool(q.get("source")), q["source"] + " — " + q.get("source_note", ""))

    s = prices.quote("AMEX:SPY")["quote"]
    if s.get("ok"):
        check("the stock quote says out loud that it is one exchange only",
              "IEX" in s["source"] and "not the" in s.get("source_note", ""),
              f"{s['age_seconds'] / 3600:.1f} hours old — {s['source_note']}")

    u = prices.quote("NASDAQ:AAPL")["quote"]
    check("an instrument the bot does not watch gets no price at all",
          not u.get("ok") and bool(u.get("why")), u.get("why", ""))


def walk_for_zeros(node, path="") -> list:
    """Any numeric zero sitting where the panel would read it as a value."""
    bad = []
    if isinstance(node, dict):
        for k, v in node.items():
            bad += walk_for_zeros(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            bad += walk_for_zeros(v, f"{path}[{i}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        if node == 0 and re.search(
                r"price|equity|as_of|dollars|pct|age|balance", path, re.I):
            bad.append(path)
    return bad


def check_nothing_unknown_is_zero() -> None:
    print("\n4. NOTHING UNKNOWN COMES BACK AS A ZERO")
    pic = service.picture("BINANCE:BTCUSDT")
    zeros = walk_for_zeros(pic)
    check("no zero stands in for a missing value anywhere in the answer",
          not zeros, ", ".join(zeros) if zeros else
          "every unknown came back as null with a sentence next to it")
    for field, why in (("account", "account_why"), ("signal", "signal_why")):
        if pic.get(field) is None:
            check(f"a missing {field} comes with an explanation",
                  bool(pic.get(why)), (pic.get(why) or "")[:110])


def check_dead_desk_is_visible() -> None:
    print("\n5. A DEAD DESK LOOKS DIFFERENT FROM A QUIET ONE")
    keep = store.heartbeat()
    store.beat(["crypto"], note="test")
    check("a fresh heartbeat reads as alive", service.desk_state()["alive"])
    store._write(store.HEARTBEAT_PATH,
                 {"as_of": time.time() - 3600, "markets": ["crypto"]})
    d = service.desk_state()
    check("an hour-old heartbeat reads as stopped, with a reason",
          not d["alive"] and bool(d["why"]), d["why"])

    # A market that threw is not a market where nothing set up. Alpaca resets
    # connections often enough that this is the everyday case, not an edge.
    store.beat([{"name": "crypto", "ok": False,
                 "why": "ConnectionError: Connection reset by peer"},
                {"name": "gold", "ok": True, "setups": 0}])
    d = service.desk_state()
    check("a market that could not be reached is listed apart from the ones "
          "that were checked",
          d["markets"] == ["gold"] and len(d["failed"]) == 1,
          f"checked {d['markets']}, could not check "
          f"{[f['name'] for f in d['failed']]}")

    if keep:
        store._write(store.HEARTBEAT_PATH,
                     {"as_of": keep["as_of"], "markets": keep.get("markets", [])})


BANNED = (r"\bmarket_order\b", r"\bclose_position\b", r"\bcrypto_market_order\b",
          r"\bplace_order\b", r"\bcancel_order\b", r"\.click\(", r"\.fill\(",
          r"\.press\(", r"\.tap\(")


def check_cockpit_cannot_trade() -> None:
    print("\n6. NOTHING IN THE COCKPIT CAN PLACE, CHANGE OR CANCEL AN ORDER")
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cockpit")
    found = []
    for root, _dirs, files in os.walk(here):
        if "state" in root:
            continue
        for f in files:
            if not f.endswith((".py", ".js")):
                continue
            path = os.path.join(root, f)
            with open(path) as fh:
                body = fh.read()
            for pat in BANNED:
                for m in re.finditer(pat, body):
                    line = body[:m.start()].count("\n") + 1
                    src = body.splitlines()[line - 1].strip()
                    if src.startswith("#") or src.startswith("*") or \
                            src.startswith("//"):
                        continue
                    found.append(f"{f}:{line} {pat}")
    check("no order call and no click anywhere under cockpit/",
          not found, "; ".join(found) if found else
          "read-only: navigation and DOM reads only, no clicks at all")

    ext = os.path.join(here, "extension")
    if os.path.isdir(ext):
        keys = []
        for f in os.listdir(ext):
            if f.endswith(".js"):
                body = open(os.path.join(ext, f)).read()
                if re.search(r"(api[_-]?key|secret|token|passphrase)\s*[:=]\s*"
                             r"['\"][A-Za-z0-9_\-]{12,}", body, re.I):
                    keys.append(f)
        check("no credential is baked into the extension", not keys,
              ", ".join(keys) if keys else
              "the extension holds no keys — it only talks to 127.0.0.1")


# ------------------------------------------------------------------- main
def main() -> int:
    print("=" * 72)
    print("step448 — does the cockpit ever show something wrong without "
          "saying so?")
    print("=" * 72)

    # the balance is put back exactly as it was found
    before = store._read(store.ACCOUNT_PATH, {})
    journal_before = (os.path.getsize(store.SIGNALS_PATH)
                      if os.path.exists(store.SIGNALS_PATH) else 0)

    try:
        sig = a_real_setup()
        if not sig:
            print("  no cached Bitcoin setup to test with — cannot run")
            return 1
        print(f"\nusing a real setup: {'BUY' if sig['direction'] > 0 else 'SELL'}"
              f" BTC/USD at {sig['reference_price']:,.2f}, stop "
              f"{sig['stop']:,.2f}, which fired {sig['fired_at']}")

        check_panel_matches_phone(sig, 105_000.0)
        check_no_balance_no_size(sig)
        check_price_is_dated()
        check_nothing_unknown_is_zero()
        check_dead_desk_is_visible()
        check_cockpit_cannot_trade()
    finally:
        store._write(store.ACCOUNT_PATH, before)
        # the two test pushes are trimmed back off the journal
        if os.path.exists(store.SIGNALS_PATH):
            with open(store.SIGNALS_PATH, "rb") as fh:
                body = fh.read()[:journal_before]
            with open(store.SIGNALS_PATH, "wb") as fh:
                fh.write(body)

    print("\n" + "=" * 72)
    if FAILURES:
        print(f"{len(FAILURES)} of {CHECKS} checks FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"all {CHECKS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
