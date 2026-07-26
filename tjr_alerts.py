"""
tjr_alerts.py — the message that lands on Wallace's phone. It is now the
whole output of the system, so it is the product.

THE DECISION THIS FILE SERVES
    The bot ALERTS on every market and Wallace places every trade himself.
    Nothing anywhere sends an order. The reason is on record: this week is a
    test of whether the method produces good trades, and automating the
    execution would add a second thing that can fail — after a bad week we
    could not tell whether the method was wrong or our order handling was.
    He can also refuse a signal he does not like, which we want.

    So a message that is unclear is not a cosmetic problem. It is the
    product failing.

THE LANGUAGE RULES, WHICH ARE NOT STYLE
    1. "bot", never "book".
    2. Write the definition, not the jargon. "the price ran past the high and
       came straight back", never "swept liquidity". "the level that proves
       the idea wrong", never "invalidation".
    3. NEVER a bare percentage. Every one says what it is a percentage OF —
       a move in the PRICE, or a share of the ACCOUNT. Those differ by more
       than tenfold on a leveraged position and confusing them is the
       difference between "nothing happened" and "you are nearly out".
    4. No abbreviation he would have to decode. Distances are given in the
       price AND in whatever unit that market counts in.
    5. Sizes are in the units he will actually type, and every alert says
       WHICH INSTRUMENT the size assumes, because most of these markets can
       be traded three different ways and the three do not size alike.
    6. The market is the first thing on the message. At three in the morning
       he has to know what he is looking at in one glance.

WHAT IS SENT, AND WHEN
    ENTRY   the moment the sequence completes. Never on a schedule.
    MANAGE  again when the first target is reached and the stop should move,
            and again when the trade should be closed. A signal he cannot
            manage is half a signal.
    NOTHING else. No heartbeat, no "still watching", no daily summary.
    Silence means nothing is happening, and that has to stay true or he will
    start ignoring the phone.

SAFETY
    This file sends messages. It places no orders and imports nothing that
    can. `send` reuses step5_paper_trade.notify — the one alert path that
    already has his Telegram bot's credentials on the live server — rather
    than opening a second one.
"""

from __future__ import annotations

import datetime as dt
import math
import os

# ======================================================== THE MARKETS
#
# Everything that is TRUE OF A MARKET rather than true of the method. The
# message builder below never branches on which market it is writing about;
# it reads these.
#
#   label        what goes at the top of the message
#   size_unit    the word for one unit of the thing he will type
#   instrument   WHICH of the several tradeable versions the size assumes.
#                This sentence is not optional: gold can be a fund, a
#                futures contract or spot metal, and a size worked out on
#                one is wrong on the others.
#   whole_units  True where a fraction of a unit is awkward to type

MARKETS = {
    "crypto": {
        "label": "CRYPTO",
        "size_unit": "coins",
        "instrument": ("the size is in COINS, worked out for SPOT. If you take "
                       "it as a perpetual instead, the number of coins is the "
                       "same — leverage changes the margin you post, not what "
                       "this trade risks, as long as the size and the stop are "
                       "the ones below."),
        "whole_units": False,
    },
    "sp500": {
        "label": "S&P 500",
        "size_unit": "shares",
        "instrument": ("the size is in SHARES OF THE FUND named above, not the "
                       "index and not a futures contract. Those move in "
                       "different units and this size is wrong on them."),
        "whole_units": True,
    },
    "gold": {
        "label": "GOLD",
        "size_unit": "shares",
        "instrument": ("the size is in SHARES OF GLD, the gold fund. These "
                       "prices are the fund's, not the price of gold — if you "
                       "place this on spot gold the numbers will not line up."),
        "whole_units": True,
    },
    "currencies": {
        "label": "CURRENCIES",
        "size_unit": "standard lots",
        "instrument": ("the size is in STANDARD LOTS of the spot pair. One "
                       "standard lot is 100,000 of the first currency named."),
        "whole_units": False,
    },
}

# The pairs that need their own price format and their own smallest step.
# Everything else gets the magnitude rule in `decimals()`, which is right
# from Bitcoin at sixty thousand to Dogecoin at twelve cents.
PAIR_SPEC = {
    "GBP/USD": {"pip": 0.0001, "decimals": 5, "base_name": "pounds"},
    "GBP/JPY": {"pip": 0.01, "decimals": 3, "base_name": "pounds"},
}

STANDARD_LOT = 100_000

SET_SIZE_NOTE = ("               this is your SET size for this market — "
                 "worked out once, not per trade, and it does not move")


# ------------------------------------------------------------- formatting
def decimals(symbol: str, price: float) -> int:
    """How many decimal places this price is worth writing to.

    An explicit number where we have one, and otherwise a rule based on how
    large the price is, so that Bitcoin near sixty thousand gets two places
    and Dogecoin near twelve cents gets six. A table of every symbol would
    go stale the first time a new pair was added.
    """
    if symbol in PAIR_SPEC:
        return PAIR_SPEC[symbol]["decimals"]
    if price <= 0:
        return 2
    return int(min(8, max(2, 6 - math.floor(math.log10(abs(price))))))


def fmt_price(symbol: str, p: float) -> str:
    return f"{p:,.{decimals(symbol, p)}f}"


def pip_size(pair: str) -> float:
    return PAIR_SPEC[pair]["pip"]


def to_pips(pair: str, price_distance: float) -> float:
    return abs(price_distance) / pip_size(pair)


def distance_phrase(market: str, symbol: str, price_distance: float,
                    entry: float) -> str:
    """How far away something is, in the unit that market counts in.

    Currencies count in pips and he thinks in pips. Everything else counts
    in the price itself, and a share of the price is added because a
    two-dollar stop means something different on a four-hundred-dollar fund
    and on a twelve-cent coin. That share is always labelled as A MOVE IN THE
    PRICE so it can never be read as a change in what the position is worth.
    """
    d = abs(price_distance)
    if market == "currencies":
        return (f"{to_pips(symbol, d):.0f} pips, "
                f"{d:.{decimals(symbol, entry)}f} on the price")
    share = 100.0 * d / entry if entry else 0.0
    return (f"{d:,.{decimals(symbol, entry)}f} away, which is a "
            f"{share:.2f}% MOVE IN THE PRICE")


# ------------------------------------------------------------------ sizing
#
# THE ONE CAP, AND IT IS OURS, NOT HIS — HE HAS NOT ANSWERED ON IT YET.
#
# His rule sets the size once off the tightest stop an instrument normally
# gives and then holds it still, so a wider stop on the day risks more. On
# stocks and gold that produces the one-to-three-percent-of-the-account band
# he describes and everything is fine.
#
# On crypto it does not stay in that band. Measured from the pairs' own
# setups: DOT's WIDEST stop is 36 times its tightest. Held to a fixed size,
# a wide-stop DOT signal would put 36% OF THE ACCOUNT on one trade. That is
# not a percentage move in the price — it is more than a third of the money,
# gone, on a single stop being hit.
#
# We are not resolving that on his behalf. The cap below is a CEILING ON
# WHAT ONE TRADE MAY RISK, set to 3% of the account, which is the top of the
# band he himself states ("risking two percent... or three"). So the default
# enforces his own words rather than overriding them, and it only ever binds
# on the tail his words did not anticipate.
#
# It is loud when it binds: the message says so in plain words, and the order
# path logs it. To switch it off entirely, set it to None or 0 — either here
# or with CRYPTOBOT_MAX_RISK_PCT in the environment (a share, so "0.03").
MAX_RISK_SHARE_OF_ACCOUNT = 0.03


def max_risk_share() -> float:
    """The cap as a share of the account, or 0 when it is switched off."""
    raw = os.environ.get("CRYPTOBOT_MAX_RISK_PCT")
    if raw not in (None, ""):
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return float(MAX_RISK_SHARE_OF_ACCOUNT or 0.0)


def position_size(market: str, symbol: str, account: float, entry: float,
                  stop_distance: float, tightest_stop_pct: float,
                  usd_per_quote: float = 1.0, risk_pct: float = 0.01,
                  cap_share: float | None = None) -> dict:
    """THE ARITHMETIC HE SHOULD NEVER HAVE TO DO — and it is HIS arithmetic,
    which is not the obvious one.

    THE RULE, from the bootcamp day he gives entirely to position size:

        "you're going to set your stop loss in points — what's usually the
         LOWEST your stop loss will be during a trade. For me it's usually
         400. We calculate that, boom, 25 lots. That is going to be our SET
         lot size. And you're probably saying, well that doesn't make any
         sense — well it does, because that means I'm going to be risking one
         percent if price hits stop right here. That also means I'll be
         risking two percent of my account if we have a larger stop loss."

    So the size is worked out ONCE, off the TIGHTEST stop that instrument
    normally gives, such that THAT stop would cost one percent of the
    account. Then it is held fixed. A wider stop on the day therefore risks
    two percent, or three. That is not a leak in the rule — it is the rule.
    The size does not shrink to hold the risk at one percent, and the one-to-
    three-percent band is an OUTPUT of holding the size still, never a dial.

        set size = (one percent of the account)
                   / (the tightest stop x dollars per unit of the quote currency)

    `tightest_stop_pct` is that stop as a SHARE OF THE PRICE, measured from
    the instrument's own recent setups — never carried across from another
    market. Bitcoin's tightest stop and SPY's are permanently different
    numbers, and as a share of price they stay comparable when the price
    itself moves.

    `usd_per_quote` is 1 everywhere except a yen pair, where the profit
    arrives in yen and has to become dollars before the size means anything.
    Getting that wrong would be off by about the yen rate — a factor of some
    145, not a rounding error.

    `risk_pct` is one percent normally and half of one percent on a news day
    or a holiday, which is his rule too. The double-size tier stays disabled:
    he forbids it to anyone without a proven record and we have none.
    """
    baseline = float(tightest_stop_pct) * float(entry)
    if baseline <= 0 or stop_distance <= 0 or usd_per_quote <= 0 or account <= 0:
        return {"units": 0.0, "lots": 0.0, "per_step": 0.0, "ok": False,
                "risk_dollars": 0.0, "risk_share_pct": 0.0, "wider": 1.0}
    units = (risk_pct * account) / (baseline * usd_per_quote)
    risk_dollars = units * stop_distance * usd_per_quote

    # THE CAP. See the block comment above MAX_RISK_SHARE_OF_ACCOUNT: this is
    # ours, pending his answer, and it is a ceiling on what ONE trade may put
    # at risk. It does not touch the set size in the ordinary case — it only
    # binds on the tail where a stop is many times wider than the tightest
    # this instrument gives. When it binds, BOTH numbers are reported, so
    # what the rule asked for is never hidden behind what was taken.
    cap = max_risk_share() if cap_share is None else float(cap_share or 0.0)
    uncapped_units, uncapped_risk = units, risk_dollars
    capped = False
    if cap > 0 and risk_dollars > cap * account:
        units = units * (cap * account) / risk_dollars
        risk_dollars = units * stop_distance * usd_per_quote
        capped = True

    out = {"units": units, "lots": units / STANDARD_LOT, "ok": True,
           "baseline_stop": baseline,
           "risk_dollars": risk_dollars,
           "risk_share_pct": 100.0 * risk_dollars / account,
           # how much wider today's stop is than the one the size was set on
           "wider": stop_distance / baseline,
           "capped": capped,
           "cap_share_pct": 100.0 * cap,
           "uncapped_units": uncapped_units,
           "uncapped_risk_dollars": uncapped_risk,
           "uncapped_risk_share_pct": 100.0 * uncapped_risk / account}
    if market == "currencies":
        out["per_step"] = units * pip_size(symbol) * usd_per_quote
    else:
        out["per_step"] = units * usd_per_quote          # per 1.00 of price
    return out


def size_lines(market: str, symbol: str, size: dict, entry: float,
               account: float, usd_per_quote: float = 1.0,
               half_size: bool = False) -> list:
    """The block he copies into the ticket, in that market's own units, plus
    what it costs him if the stop is hit — always as dollars AND as a share
    of the ACCOUNT, never as a bare number."""
    spec = MARKETS[market]
    lines = []
    if not size["ok"]:
        return ["Size           COULD NOT BE WORKED OUT — do not take this one"]

    if market == "currencies":
        base = PAIR_SPEC[symbol]["base_name"]
        lines.append(f"Size           {size['lots']:.2f} standard lots")
        lines.append(f"               = {size['units']:,.0f} {base}")
        lines.append(f"               = {size['units'] / 10_000:.1f} mini lots, "
                     f"if that is what your ticket asks for")
        lines.append(SET_SIZE_NOTE)
        lines.append(f"Every pip is worth about ${size['per_step']:,.2f}")
    elif spec["whole_units"]:
        # Round DOWN. A part share is awkward to type, and rounding up puts
        # more at risk than the set size says.
        whole = math.floor(size["units"])
        lines.append(f"Size           {whole:,} {spec['size_unit']}")
        lines.append(f"               (the exact figure is {size['units']:,.1f} "
                     f"— round down, never up)")
        lines.append(SET_SIZE_NOTE)
        lines.append(f"Every $1.00 the price moves is worth about "
                     f"${whole * usd_per_quote:,.2f}")
    else:
        u = size["units"]
        places = 6 if u < 1 else (4 if u < 100 else 2)
        lines.append(f"Size           {u:,.{places}f} {spec['size_unit']}")
        lines.append(SET_SIZE_NOTE)
        lines.append(f"Every $1.00 the price moves is worth about "
                     f"${size['per_step']:,.2f}")

    if half_size:
        lines.append("               HALF SIZE today — there is a news release "
                     "or a holiday, and he halves it on those.")

    risk, share = size["risk_dollars"], size["risk_share_pct"]
    lines.append(f"If the stop is hit you lose ${risk:,.0f}, which is "
                 f"{share:.2f}% OF THE ACCOUNT (not a move in the price)")

    # HE SHOULD SEE THE TWO-PERCENT DAY, NOT DISCOVER IT. The size is fixed
    # off the tightest stop this market normally gives, so a wider stop today
    # costs proportionally more. That is the rule working exactly as he
    # describes it, and saying so is the difference between a rule and a
    # surprise.
    if share >= 1.6:
        lines.append(f"               THAT IS MORE THAN ONE PERCENT ON PURPOSE. "
                     f"Today's stop is {size['wider']:.1f} times wider than the "
                     f"tightest this market gives, and the size stays put — so "
                     f"this one costs {share:.1f}% OF THE ACCOUNT if it is "
                     f"wrong. Do not shrink it.")

    # WHEN THE CAP BINDS, SAY SO IN FULL. The size that came back is NOT the
    # one his rule produced, and hiding that would be the worst kind of quiet
    # change. Both numbers, and whose decision it was.
    if size.get("capped"):
        lines.append(
            f"               SIZE CUT BY OUR CAP, NOT BY HIS RULE. Held to "
            f"the set size this trade would have risked "
            f"${size['uncapped_risk_dollars']:,.0f}, which is "
            f"{size['uncapped_risk_share_pct']:.1f}% OF THE ACCOUNT — today's "
            f"stop is {size['wider']:.0f} times wider than the tightest this "
            f"market gives. The size was cut to hold it at "
            f"{size['cap_share_pct']:.0f}% of the account, the top of the "
            f"band he states. THIS CEILING IS OURS AND HE HAS NOT RULED ON "
            f"IT. Switch it off with CRYPTOBOT_MAX_RISK_PCT=0.")

    face = size["units"] * entry * usd_per_quote
    if face > 0 and account > 0:
        times = face / account
        lines.append(f"Face value     ${face:,.0f}"
                     + (f", which is {times:.1f} times the account — if your "
                        f"broker will not allow that much, take what it does"
                        if times > 1.05 else ""))
    return lines


# ----------------------------------------------------------- plain english
TF_NAME = {
    "1m": "1-minute", "5m": "5-minute", "15m": "15-minute",
    "1h": "1-hour", "4h": "4-hour",
    "prev_day": "previous day's", "prev_week": "previous week's",
    "asia": "Asia hours'", "london": "London hours'",
    "new_york": "New York hours'",
    "premarket_ny": "pre-market",
}


def tf_name(tag) -> str:
    """The chart feature's name in words. The bot's tags are short machine
    labels — "prev_day", "premarket_ny" — and none of them goes to his phone
    as it is written."""
    return TF_NAME.get(str(tag), str(tag))


def target_source_name(src, direction: int) -> str:
    """What a target is sitting on, in words.

    The bot labels its targets in the method's own vocabulary — "a 15-minute
    draw on liquidity", "the far side of a 15-minute fair value gap". Both
    are terms he would have to translate mid-trade, so neither reaches the
    phone. A "draw on liquidity" is a high or a low that other people's stops
    sit behind; a "fair value gap" is a stretch of price the market jumped
    over and left empty.
    """
    s, hl = str(src), ("high" if direction > 0 else "low")
    if "fair value gap" in s:
        mid = s.replace("the far side of a ", "").replace(" fair value gap", "")
        return f"the far side of a stretch the market jumped on the {mid} chart"
    if "draw on liquidity" in s:
        mid = s.replace("a ", "", 1).replace(" draw on liquidity", "")
        return f"the {TF_NAME.get(mid, mid)} {hl} ahead of it"
    return s


def stop_sits_on(sig: dict) -> str:
    """WHICH CHART FEATURE THE STOP IS ON, in one phrase.

    The bot's own stop_anchor sentence is correct but carries its raw tag
    inside it, so it is rewritten here rather than passed through. He should
    never have to work out what "prev_day" means while a trade is live.
    """
    up = sig["direction"] > 0
    side = "below" if up else "above"
    grabbed = "low" if up else "high"
    return (f"just {side} the furthest price reached when the "
            f"{tf_name(sig.get('level_tf'))} {grabbed} was taken, with a "
            f"little clearance for the spread")


def plain_reason(sig: dict) -> str:
    """One sentence for why the trade exists. No term in it needs a glossary.
    """
    sym = sig["symbol"]
    lvl = sig.get("level_price")
    up = sig["direction"] > 0
    grabbed = "low" if up else "high"
    turned = "back up" if up else "back down"

    # The bot writes these in the method's own words. Every one of them is
    # rewritten here, because "break of structure" and "gap inversion" are
    # terms he would have to stop and translate with a trade live.
    c = str(sig.get("confirmed_by") or "")
    if "gap inversion" in c:
        confirm = ("the 5-minute chart then traded back through a stretch it "
                   "had jumped over, from the other side")
    elif "close back through" in c:
        confirm = ("the 5-minute chart then closed back through the price that "
                   "whole run started from")
    elif "break of structure" in c:
        confirm = (f"the 5-minute chart then broke {turned} through its last "
                   f"{'high' if up else 'low'}")
    else:
        confirm = f"the 5-minute chart then turned {turned}"

    pb = str(sig.get("pullback_into") or "")
    if "midpoint and" in pb:
        pull = ("price pulled back to the middle of that move AND into a "
                "stretch it had jumped over")
    elif "midpoint" in pb:
        pull = "price pulled back to the middle of that move"
    elif "fair value gap" in pb:
        pull = "price pulled back into a stretch that move had jumped over"
    else:
        pull = "price pulled back"

    where = (f"the {tf_name(sig.get('level_tf'))} {grabbed} at "
             f"{fmt_price(sym, float(lvl))}" if lvl is not None
             else f"a {tf_name(sig.get('level_tf'))} level")
    return (f"Price ran past {where} and came straight back, {confirm}, "
            f"{pull}, and the 1-minute chart turned {turned} — so the run past "
            f"that {grabbed} was a grab, not a move.")


# ------------------------------------------------------------- THE MESSAGE
def trade_block(sig: dict, account: float, usd_per_quote: float = 1.0) -> list:
    """One symbol's numbers. Used alone in a single-symbol alert and repeated
    inside a combined one, so the two can never drift apart.

    `sig["tightest_stop_pct"]` is what the set size was worked out from: the
    tightest stop this instrument normally gives, as a share of its price,
    measured from its own setups. Without it there is no set size and this
    refuses rather than quietly falling back to sizing per trade, which is
    the thing his rule specifically rejects.
    """
    market, sym = sig["market"], sig["symbol"]
    buy = sig["direction"] > 0
    entry, stop = float(sig["reference_price"]), float(sig["stop"])
    dist = abs(entry - stop)

    # one percent normally, half of one percent on a news day or holiday —
    # read from what the bot itself asked for rather than re-decided here
    risk_pct = 0.01
    if account > 0 and sig.get("risk_wanted"):
        risk_pct = float(sig["risk_wanted"]) / account
    half = risk_pct < 0.0075

    size = position_size(market, sym, account, entry, dist,
                         float(sig.get("tightest_stop_pct") or 0.0),
                         usd_per_quote, risk_pct)

    lines = [f"{'BUY' if buy else 'SELL'} {sym}", ""]
    lines.append(f"Enter around   {fmt_price(sym, entry)}")
    lines.append(f"Stop           {fmt_price(sym, stop)}   "
                 f"({distance_phrase(market, sym, dist, entry)})")
    lines.append(f"               it sits {stop_sits_on(sig)}")

    tgts = list(sig.get("targets") or [])
    srcs = list(sig.get("target_sources") or [])
    names = ["First target ", "Second target", "Third target ", "Fourth target"]
    for i, tp in enumerate(tgts[:4]):
        d = abs(float(tp) - entry)
        src = target_source_name(srcs[i], sig["direction"]) if i < len(srcs) else ""
        lines.append(f"{names[i]}  {fmt_price(sym, float(tp))}   "
                     f"({distance_phrase(market, sym, d, entry)})"
                     + (f", {src}" if src else ""))
    if not tgts:
        lines.append("Targets        the chart offers nowhere ahead that he "
                     "would take profit — run it to the stop or to the close")

    lines += [""] + size_lines(market, sym, size, entry, account,
                               usd_per_quote, half)
    lines += ["", "Why:", "  " + plain_reason(sig)]
    return lines


def entry_message(sigs, account: float, usd_per_quote=None,
                  fired_at: dt.datetime | None = None) -> tuple:
    """The message he acts on. ONE message, even when several symbols in the
    same market fire on the same minute.

    NO SPAM IS A RULE, NOT A PREFERENCE. Ten crypto pairs run at once and
    they move together; three of them turning on the same level in the same
    minute is one idea, not three alerts. They are listed inside one message,
    each with its own numbers, so nothing is lost and his phone buzzes once.

    `sigs` is one signal dictionary or a list of them, all from the same
    market. `usd_per_quote` is 1.0 everywhere except a yen pair; pass a dict
    keyed by symbol when a batch needs different ones.
    """
    if isinstance(sigs, dict):
        sigs = [sigs]
    market = sigs[0]["market"]
    spec = MARKETS[market]
    when = fired_at or dt.datetime.now()

    def upq(sym):
        if isinstance(usd_per_quote, dict):
            return float(usd_per_quote.get(sym, 1.0))
        return 1.0 if usd_per_quote is None else float(usd_per_quote)

    head = f"{spec['label']} — take this one by hand"
    if len(sigs) > 1:
        head = (f"{spec['label']} — {len(sigs)} setups at once, "
                f"take them by hand")

    body = [head, "=" * 46, ""]
    for i, sig in enumerate(sigs):
        if i:
            body += ["", "-" * 46, ""]
        body += trade_block(sig, account, upq(sig["symbol"]))

    body += ["", spec["instrument"]]
    if any(s.get("targets") for s in sigs):
        body.append("")
        body.append("When the first target is reached: take half off and move "
                    "the stop to your entry price. I will message you at that "
                    "point, and again when it is time to be out.")
    body += ["", f"Fired {when:%H:%M} New York time, {when:%A %-d %B}."]

    syms = ", ".join(s["symbol"] for s in sigs)
    side = "BUY" if sigs[0]["direction"] > 0 else "SELL"
    title = f"{spec['label']} · {side} {syms}"
    if len({s["direction"] for s in sigs}) > 1:
        title = f"{spec['label']} · {len(sigs)} setups"
    return title, "\n".join(body)


# ------------------------------------------------------- the manage cards
def first_target_message(market: str, symbol: str, entry: float, target: float,
                         when: dt.datetime | None = None) -> tuple:
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"The first target is reached at {fmt_price(symbol, target)}.",
        "",
        "Two things now:",
        "  1. Take HALF the position off here.",
        f"  2. Move your stop to {fmt_price(symbol, entry)}, your entry price.",
        "",
        "From here the trade cannot lose money. The rest runs to the next "
        "target.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: half off, move the stop", msg


def close_message(market: str, symbol: str, price: float, why: str,
                  when: dt.datetime | None = None) -> tuple:
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"Close it now, around {fmt_price(symbol, price)}.",
        "", why, "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: close it", msg


def stopped_message(market: str, symbol: str, price: float,
                    when: dt.datetime | None = None) -> tuple:
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"Your stop at {fmt_price(symbol, price)} should have been hit.",
        "",
        "Check the position is closed. Nothing else to do — this one was "
        "wrong and it cost exactly what it was set up to cost.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: stopped out", msg


# ------------------------------------------------------------- the sending
def send(title: str, message: str) -> None:
    """One push to his phone, through the channel that already works.

    step5_paper_trade.notify sends to his Telegram bot first and falls back
    to a silent secondary. Its credentials are already on the live server.
    Reusing it rather than opening a second path means there is one place a
    push can break and one place to fix it.
    """
    from step5_paper_trade import notify
    notify(title, message)
