"""
cockpit/signals.py — the signal on the screen, built from the same code that
built the signal on the phone.

THE RULE THIS FILE ENFORCES
    If the numbers on the chart and the numbers on his phone ever differ,
    the cockpit is broken. So the panel does not re-derive anything. It
    calls the SAME functions in tjr_alerts, on the SAME stored signal, with
    the SAME account balance that was used when the message was sent — the
    balance is stored alongside the signal for exactly this reason, because
    re-reading today's balance would silently re-size a signal that was sent
    an hour ago.

    And then it checks. `render` reads back the exact Telegram text that was
    pushed and confirms that every price it is about to put on the screen
    actually appears in that message. If one does not, the panel is handed
    `agrees_with_phone: False` and says so on its face rather than showing
    numbers it cannot vouch for. That check is the only reason to trust the
    word "identical".

SAFETY
    Reads a journal file. Sends nothing, places nothing.
"""

from __future__ import annotations

import datetime as dt
import inspect
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tjr_alerts                                              # noqa: E402
from cockpit import store                                      # noqa: E402


def call(fn, **kw):
    """Call one of tjr_alerts' functions by ARGUMENT NAME rather than by
    position.

    tjr_alerts is edited often and its argument lists move — a `clamped`
    flag was taken out of size_lines on the afternoon this was written. A
    panel wired to positions would then either crash or, far worse, hand
    `usd_per_quote` to a parameter that now means something else and print a
    plausible wrong size next to a real signal.

    So the names are matched, anything the function no longer takes is
    dropped, and anything it needs and we cannot supply raises here — loudly,
    where render() turns it into "this signal could not be read back" on the
    panel — instead of quietly.
    """
    params = inspect.signature(fn).parameters
    missing = [n for n, p in params.items()
               if p.default is inspect.Parameter.empty and n not in kw
               and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
    if missing:
        raise TypeError(f"tjr_alerts.{fn.__name__} now needs "
                        f"{', '.join(missing)}, which the cockpit does not "
                        f"have — the panel will not guess it")
    return fn(**{k: v for k, v in kw.items() if k in params})


def _when(row: dict) -> float | None:
    """The moment the setup fired, as a plain epoch second so the panel can
    count its age against its own clock."""
    raw = row.get("fired_at")
    if raw is None:
        return row.get("recorded_at")
    try:
        import pandas as pd
        return float(pd.Timestamp(raw).timestamp())
    except Exception:
        return row.get("recorded_at")


def one_trade(sig: dict, account: float, usd_per_quote: float,
              message: str) -> dict:
    """One symbol's block, in the same words the phone got.

    Every price here goes through tjr_alerts.fmt_price and every distance
    through tjr_alerts.distance_phrase, so the panel cannot round a number
    differently from the message. `distance_phrase` is also the reason no
    bare percentage reaches the screen: it writes "a 0.47% MOVE IN THE
    PRICE" in full, which cannot be mistaken for a share of the account.
    """
    market, sym = sig["market"], sig["symbol"]
    entry = float(sig["reference_price"])
    stop = float(sig["stop"])
    dist = abs(entry - stop)

    risk_pct = 0.01
    if account > 0 and sig.get("risk_wanted"):
        risk_pct = float(sig["risk_wanted"]) / account
    half = risk_pct < 0.0075

    size = call(tjr_alerts.position_size, market=market, symbol=sym,
                account=account, entry=entry, stop_distance=dist,
                tightest_stop_pct=float(sig.get("tightest_stop_pct") or 0.0),
                usd_per_quote=usd_per_quote, risk_pct=risk_pct)

    targets = []
    srcs = list(sig.get("target_sources") or [])
    for i, tp in enumerate(list(sig.get("targets") or [])[:4]):
        tp = float(tp)
        targets.append({
            "price": tjr_alerts.fmt_price(sym, tp),
            "away": call(tjr_alerts.distance_phrase, market=market, symbol=sym,
                         price_distance=abs(tp - entry), entry=entry),
            "sits_on": (tjr_alerts.target_source_name(srcs[i], sig["direction"])
                        if i < len(srcs) else ""),
        })

    shown = [tjr_alerts.fmt_price(sym, entry), tjr_alerts.fmt_price(sym, stop)]
    shown += [t["price"] for t in targets]
    agrees = all(p in message for p in shown) if message else None

    out = {
        "symbol": sym,
        "market": market,
        "market_label": tjr_alerts.MARKETS[market]["label"],
        "side": "BUY" if sig["direction"] > 0 else "SELL",
        "entry": tjr_alerts.fmt_price(sym, entry),
        "stop": tjr_alerts.fmt_price(sym, stop),
        "stop_away": call(tjr_alerts.distance_phrase, market=market, symbol=sym,
                          price_distance=dist, entry=entry),
        "stop_sits_on": tjr_alerts.stop_sits_on(sig),
        "targets": targets,
        "why": tjr_alerts.plain_reason(sig),
        "venue_note": sig.get("venue_note", ""),
        "half_size": half,
        "agrees_with_phone": agrees,
    }

    # THE SIZE, OR AN HONEST REFUSAL. tjr_alerts answers ok: False when it
    # has no balance to work from or no measured stop floor for this
    # instrument, and that refusal is carried straight through to the panel
    # rather than being softened into a blank.
    if size["ok"]:
        out["size_lines"] = call(
            tjr_alerts.size_lines, market=market, symbol=sym, size=size,
            entry=entry, account=account, clamped=bool(sig.get("clamped")),
            usd_per_quote=usd_per_quote, half_size=half)
        out["risk_dollars"] = round(size["risk_dollars"], 2)
        out["risk_share_of_account_pct"] = round(size["risk_share_pct"], 2)
        out["size_wider_than_tightest"] = round(size["wider"], 2)
    else:
        out["size_lines"] = None
        out["risk_dollars"] = None
        out["risk_share_of_account_pct"] = None
        out["size_refused_because"] = (
            "we do not know the account balance, so there is no size to state"
            if account <= 0 else
            f"the tightest stop {sym} normally gives has never been measured, "
            f"so its set size cannot be worked out")
    return out


def render(row: dict | None) -> dict | None:
    """A recorded push, turned into what the panel draws."""
    if not row:
        return None
    account = float(row.get("account_used") or 0.0)
    upq = row.get("usd_per_quote") or {}
    message = row.get("message") or ""
    trades = []
    for sig in row.get("signals") or []:
        try:
            trades.append(one_trade(sig, account,
                                    float(upq.get(sig["symbol"], 1.0)), message))
        except Exception as e:
            trades.append({"symbol": sig.get("symbol", "?"),
                           "broken": f"this signal could not be read back: "
                                     f"{str(e)[:140]}"})
    return {
        "kind": row.get("kind"),
        "title": row.get("title"),
        "message": message,
        "fired_at": _when(row),
        "account_used": account or None,
        "account_used_note": (None if account > 0 else
                              "no balance was known when this fired, so it "
                              "went out without a size"),
        "trades": trades,
        "agrees_with_phone": all(t.get("agrees_with_phone") is not False
                                 for t in trades),
    }


def current() -> dict | None:
    return render(store.latest_entry())


def recent(limit: int = 6) -> list:
    """The last few pushes of every kind — entries and the manage messages —
    so he can see at a glance what the bot has said today."""
    out = []
    for row in reversed(store.signals(60)):
        when = _when(row)
        out.append({
            "kind": row.get("kind"),
            "title": row.get("title"),
            "at": when,
            "at_words": (dt.datetime.fromtimestamp(when).strftime("%H:%M")
                         if when else "unknown time"),
        })
        if len(out) >= limit:
            break
    return out
