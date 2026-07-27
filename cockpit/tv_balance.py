"""
cockpit/tv_balance.py — route A for the balance: read it off his own
TradingView trading panel. READ-ONLY, and read-only in a way that is
structural rather than promised.

WHAT IT DOES
    Opens a Chrome window on a profile that lives under cockpit/state, goes
    to his chart, and reads the equity out of the trading panel's text.

WHAT IT CANNOT DO, AND WHY THAT IS NOT JUST A PROMISE
    IT NEVER CLICKS ANYTHING. Not one click, anywhere, ever — there is no
    call to click, press, fill, tap or drag in this file. It navigates and
    it reads text. The Buy and Sell buttons sit inside the same panel as
    the balance, and the only way to be certain a script will not hit one is
    for the script to have no way to hit anything.

    The cost of that is one thing he has to do once: leave the Trading Panel
    open at the bottom of the chart. If it is collapsed, this says so and
    stores nothing.

HIS PASSWORD IS NOT OURS TO TOUCH
    This never asks for, types, stores or reads a password. `--login` opens
    a browser and waits while HE signs in by hand, in his own window. The
    session then persists in the profile directory, and later reads reuse
    it. When it eventually expires, `--read` says LOGGED OUT in plain words
    and writes nothing — it does not guess, and it does not keep serving the
    last number it saw, because store.py only ever hands out what was
    actually recorded, with the time on it.

USAGE
    python3 -m cockpit.tv_balance --login    # he signs in by hand, once
    python3 -m cockpit.tv_balance --read     # read the equity, store it
    python3 -m cockpit.tv_balance --watch    # read it every few minutes
    python3 -m cockpit.tv_balance --dump     # print what the panel says,
                                             # for when TradingView moves it
"""

from __future__ import annotations

import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cockpit import store                                      # noqa: E402

PROFILE = os.path.join(store.STATE, "chrome-profile")
CHART_URL = "https://www.tradingview.com/chart/"

# The labels TradingView puts next to the number, most specific first. Equity
# is preferred over Balance because equity includes what open positions are
# currently worth, and that is the number a position size should be worked
# out from.
LABELS = ("Equity", "Total equity", "Account value", "Balance",
          "Account balance")

MONEY = r"([-−]?\$?\s?[0-9][0-9,\s]*(?:\.[0-9]{1,2})?)"


def _amount(raw: str) -> float | None:
    s = (raw or "").replace("−", "-").replace("$", "").replace(",", "")
    s = re.sub(r"\s+", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def find_equity(panel_text: str) -> dict:
    """Pull the equity out of the panel's text.

    Text rather than CSS selectors on purpose: TradingView renames its
    classes without warning, but the word "Equity" next to a number is what
    the panel is FOR, so it is the most durable thing on the page. If the
    word is not there, this refuses — it never takes "the biggest number in
    the panel" or anything else of that shape.
    """
    text = panel_text or ""
    for label in LABELS:
        # the number may sit on the same line or the line under it
        m = re.search(rf"\b{re.escape(label)}\b[^\S\n]*[:\n][^\S\n]*{MONEY}",
                      text, re.I)
        if not m:
            m = re.search(rf"\b{re.escape(label)}\b[^\S\n]{{1,4}}{MONEY}",
                          text, re.I)
        if m:
            n = _amount(m.group(1))
            if n and n > 0:
                return {"ok": True, "equity": n, "label": label}
    return {"ok": False,
            "why": ("none of the words " + ", ".join(LABELS) +
                    " appeared next to a number in the trading panel")}


# ------------------------------------------------------------ the browser
def _context(pw, headless: bool):
    os.makedirs(PROFILE, exist_ok=True)
    return pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE, channel="chrome", headless=headless,
        viewport={"width": 1500, "height": 950},
        args=["--disable-blink-features=AutomationControlled"])


def _page_text(page) -> dict:
    """Everything the trading panel says, as text. No clicks, no selectors
    that could match a button."""
    return page.evaluate("""() => {
        const pick = document.querySelector(
            '[class*="accountManager"], [class*="account-manager"], ' +
            '[class*="bottom-widgetbar-content"], [class*="tv-account"]');
        // NO FALLBACK TO THE WHOLE PAGE. If the trading panel is not there,
        // this comes back empty and the read refuses. Scanning the entire
        // document for the word "Balance" would eventually find one in a
        // banner or a menu and store it as his equity, which is precisely
        // the class of quiet wrongness this file exists to rule out.
        return {
            panel: pick ? (pick.innerText || '') : '',
            found_panel: !!pick,
            whole: (document.body.innerText || '').slice(0, 20000),
            title: document.title,
            href: location.href
        };
    }""")


def _signed_in(whole: str) -> bool:
    """A logged-out TradingView shows Sign in / Get started and no account
    panel at all. Getting this wrong in the optimistic direction is the
    failure that matters, so the test is for evidence of being IN, not for
    the absence of evidence of being out."""
    return not re.search(r"\bSign in\b", whole or "", re.I)


def read(headless: bool = False, require_paper: bool = True,
         dump: bool = False) -> dict:
    """One read. Stores nothing unless it is sure."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"ok": False, "why": "Playwright is not installed here"}

    with sync_playwright() as pw:
        try:
            ctx = _context(pw, headless)
        except Exception as e:
            return {"ok": False,
                    "why": f"Chrome would not start: {str(e)[:160]}"}
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto(CHART_URL, wait_until="domcontentloaded", timeout=60_000)
            # the trading panel loads after the chart; give it a moment
            # rather than clicking anything to hurry it along
            page.wait_for_timeout(9_000)
            got = _page_text(page)
        except Exception as e:
            return {"ok": False, "why": f"the page did not load: {str(e)[:160]}"}
        finally:
            try:
                ctx.close()
            except Exception:
                pass

    if dump:
        print("---- trading panel text ----")
        print(got["panel"][:4000])
        print("---- page title ----")
        print(got["title"])

    if not _signed_in(got["whole"]):
        return {"ok": False, "logged_out": True,
                "why": ("LOGGED OUT of TradingView. Nothing was read and "
                        "nothing was stored. Run:  python3 -m "
                        "cockpit.tv_balance --login   and sign in by hand.")}

    is_paper = bool(re.search(r"paper\s*trading", got["whole"], re.I))
    if require_paper and not is_paper:
        return {"ok": False,
                "why": ("the words 'Paper Trading' are not on the page, so I "
                        "cannot confirm this is the paper account and I will "
                        "not store a number that might be a different "
                        "account's. Connect Paper Trading in the Trading "
                        "Panel, or run with --any-broker if you know what "
                        "account is showing.")}

    if not got.get("found_panel"):
        return {"ok": False,
                "why": ("the trading panel is not on the page — it is either "
                        "collapsed or not connected. Open the Trading Panel at "
                        "the bottom of the chart and leave it open; this never "
                        "clicks anything to open it for you. Nothing stored.")}

    hit = find_equity(got["panel"])
    if not hit["ok"]:
        return {"ok": False,
                "why": hit["why"] + ". Nothing stored — the panel was found "
                                    "but no labelled figure was in it."}

    detail = f"{hit['label']} on the TradingView trading panel"
    if not is_paper:
        detail += " — NOT confirmed to be the paper account"
    store.record_balance("tradingview", hit["equity"], detail=detail)
    return {"ok": True, "equity": hit["equity"], "label": hit["label"],
            "paper_confirmed": is_paper}


def login() -> None:
    """Open a browser and get out of the way. He signs in himself; this
    file never sees a password and never types into the page."""
    from playwright.sync_api import sync_playwright
    print("Opening TradingView. Sign in yourself, then open the Trading Panel\n"
          "at the bottom of the chart and connect Paper Trading. Leave that\n"
          "panel OPEN. Come back here and press Enter when you are done.\n"
          "I will not type anything into that window.")
    with sync_playwright() as pw:
        ctx = _context(pw, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(CHART_URL, wait_until="domcontentloaded", timeout=60_000)
        try:
            input("\npress Enter once you are signed in... ")
        except EOFError:
            time.sleep(180)
        ctx.close()
    print("session saved. Now run:  python3 -m cockpit.tv_balance --read")


def main(argv):
    if "--login" in argv:
        login()
        return
    headless = "--headless" in argv
    require_paper = "--any-broker" not in argv
    r = read(headless=headless, require_paper=require_paper,
             dump="--dump" in argv)
    if r.get("ok"):
        print(f"  equity ${r['equity']:,.2f}  (from '{r['label']}')"
              + ("" if r["paper_confirmed"] else "  NOT CONFIRMED PAPER"))
    else:
        print("  COULD NOT READ THE BALANCE — nothing stored.")
        print("  " + r["why"])
    if "--watch" in argv:
        while True:
            time.sleep(300)
            r = read(headless=headless, require_paper=require_paper)
            print(time.strftime("%H:%M"),
                  f"${r['equity']:,.2f}" if r.get("ok") else r["why"][:120])


if __name__ == "__main__":
    main(sys.argv)
