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

import tjr_bot

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
    # GOLD CHANGED INSTRUMENT ON 2026-07-27, on Wallace's own instruction:
    # "trade gold as xauusdt on blofin". It was shares of the GLD fund on
    # Alpaca; it is now TETHER GOLD, XAUT-USDT, a perpetual on BloFin sized
    # in ounces. Those are different things and a size worked out on one is
    # wrong on the other, which is exactly what this sentence exists to say.
    # The levels are still read on the OANDA XAU/USD chart and converted into
    # XAUT's own prices before anything is sent — see alex_live.convert.
    "gold": {
        "label": "GOLD",
        "size_unit": "ounces of Tether Gold",
        "instrument": ("the size is in OUNCES OF TETHER GOLD (XAUT-USDT) on "
                       "BloFin, not shares of a gold fund and not a futures "
                       "contract. Those move in different units and this size "
                       "is wrong on them."),
        "whole_units": False,
    },
    # FOREX CAME BACK ON 2026-07-27, on OANDA's practice host, driven by ALEX
    # GONZALEZ's method. It is a separate row from "currencies" rather than a
    # rename of it: "currencies" is the old TJR alert-only book's vocabulary
    # and its messages are still reachable, and a header that changed
    # underneath an existing book would make two different things look like
    # one. The units and the words are the same because the instrument is.
    "forex": {
        "label": "FOREX",
        "size_unit": "standard lots",
        "instrument": ("the size is in STANDARD LOTS of the spot pair on "
                       "OANDA. One standard lot is 100,000 of the first "
                       "currency named."),
        "whole_units": False,
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
    # Added 2026-07-26 with the OANDA venue. He names EUR/USD and gold in the
    # same breath as the two above in his pre-market read, so the message
    # layer has to be able to write about them.
    #
    # A PIP IS NOT ONE NUMBER, and that is the whole reason this table
    # exists. It is 0.0001 on the dollar majors and 0.01 on every yen cross
    # and on spot gold. Hard-coding either makes the other wrong by a factor
    # of a hundred. These four agree with what OANDA reports as pipLocation,
    # and venue.OandaVenue reads that number LIVE for anything it actually
    # sends — this table is for the message, the broker's own answer is for
    # the order.
    "EUR/USD": {"pip": 0.0001, "decimals": 5, "base_name": "euros"},
    "XAU/USD": {"pip": 0.01, "decimals": 3, "base_name": "ounces of gold"},
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
    if market in ("currencies", "forex"):
        return (f"{to_pips(symbol, d):.0f} pips, "
                f"{d:.{decimals(symbol, entry)}f} on the price")
    share = 100.0 * d / entry if entry else 0.0
    return (f"{d:,.{decimals(symbol, entry)}f} away, which is a "
            f"{share:.2f}% MOVE IN THE PRICE")


# ------------------------------------------------------------------ sizing
#
# THE OUTER LIMIT, AND IT IS HIS — AND IT IS ON THE DAY, NOT ON ONE TRADE.
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
# gone, on a single stop being hit. So a ceiling is needed, and it used to be
# ours because he had not answered.
#
# HE HAS NOW ANSWERED, AND THE UNIT WAS WRONG. Boot Camp 2.0 Day 8: "I only
# lost 50 percent of what I was willing to risk ON THE DAY, that's better
# than a full you know like one percent down ON THE DAY, two percent down or
# three percent down ON THE DAY." The 3% is the top of a band that belongs to
# the DAY. Applied per trade, as it was here until 2026-07-26, it let a single
# position spend the entire outer limit — precisely what Day 8 and Day 9 warn
# against. It now lives in tjr_bot.Config.max_day_risk_share and is enforced
# by tjr_bot.DayBudget across every trade the day takes.
#
# What is left here is the same number for the single-trade case, so an alert
# built without a day ledger still cannot state a size outside his band. It is
# loud when it binds: the message says so in plain words, and the order path
# logs it. CRYPTOBOT_MAX_RISK_PCT still switches it off (a share, so "0.03").
MAX_DAY_RISK_SHARE_OF_ACCOUNT = 0.03
# the old name, kept so nothing importing it breaks. Same number, and the
# number was never the thing that was wrong.
MAX_RISK_SHARE_OF_ACCOUNT = MAX_DAY_RISK_SHARE_OF_ACCOUNT


def max_risk_share() -> float:
    """The day's outer limit as a share of the account, or 0 when it is
    switched off."""
    raw = os.environ.get("CRYPTOBOT_MAX_RISK_PCT")
    if raw not in (None, ""):
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return float(MAX_DAY_RISK_SHARE_OF_ACCOUNT or 0.0)


def margin_share() -> float:
    """How much of the account is set aside per trade to hold a position.

    HE NEVER SPECIFIES THIS — it is not part of his method, because forex
    and futures do not have a leverage dial. So it is ours, and round 449
    measured it: anything from 5% to 20% gives an identical result because
    the capital is never the binding constraint. Above that it starts
    costing trades (at 50% only two positions fit and 9 of 32 setups this
    week were missed, turning a +14% week into +4%).
    """
    import os
    try:
        return float(os.environ.get("CRYPTOBOT_MARGIN_SHARE", "0.10"))
    except ValueError:
        return 0.10


def position_size(market: str, symbol: str, account: float, entry: float,
                  stop_distance: float, tightest_stop_pct: float,
                  usd_per_quote: float = 1.0, risk_pct: float = 0.01,
                  cap_share: float | None = None,
                  buying_power: float | None = None,
                  outer_allowance: float | None = None,
                  hold_size_still: bool | None = None) -> dict:
    """THE ARITHMETIC HE SHOULD NEVER HAVE TO DO — AND IT IS NOT DONE HERE.

    THIS FUNCTION NO LONGER SIZES ANYTHING. It translates a market's units and
    then calls `tjr_bot.size_position`, which is the one place in this project
    that turns a stop into a number of units.

    WHY THAT MATTERS MORE THAN IT SOUNDS. Until 2026-07-26 there were two
    sizing rules. This one — his set size, worked out off the tightest stop
    the instrument normally gives and then held still — is what the orders
    that actually went out used. `tjr_bot.TjrBot._open` sized fresh at 1% of
    equity on every trade, and that is what every replay and every backtest
    number this project has ever produced came out of. The two disagree by
    the ratio of today's stop to the tightest stop, which on DOT is up to 36
    times. So every backtest described a bot nobody was running. There is now
    one function, both paths call it, and
    `test_tjr_bot.test_the_replay_and_the_live_path_size_identically` fails if
    they can ever drift apart again.

    `risk_pct` is WHAT THIS TRADE MAY COST, as a share of the account. step465
    made that a per-trade number and nothing else: `Config.risk_pct_per_trade`,
    halved on a news day or a holiday, the same for the day's first trade and
    its fourth. The caller reads it off `risk_wanted`. (With
    `size_per_trade=False` it is instead a share of a DAY budget, halved again
    when a second setup was already forming.) The double-size tier stays
    disabled: he forbids it to anyone without a proven record and we have
    none.

    `tightest_stop_pct` is that instrument's own tightest stop as a SHARE OF
    THE PRICE — never carried across from another market. Bitcoin's tightest
    stop and SPY's are permanently different numbers.

    `usd_per_quote` is 1 everywhere except a yen pair, where the profit
    arrives in yen and has to become dollars before the size means anything.
    Getting that wrong would be off by about the yen rate — a factor of some
    145, not a rounding error.

    `outer_allowance`, when the caller has a day ledger, is the DOLLARS the
    day has left under the top of his band. Without one it falls back to the
    single-trade reading of the same 3%, which is what an alert built outside
    a session has to assume.
    """
    cap = max_risk_share() if cap_share is None else float(cap_share or 0.0)
    if outer_allowance is None:
        outer_allowance = cap * account if cap > 0 else None
    # step465. WHICH OF THE TWO SIZING RULES — AND THE CALLER HAS TO SAY.
    #
    # It cannot be read off `tjr_bot.Config()` here, because four books call
    # this function and they no longer agree: the INDEX book ships per-trade
    # sizing, while gold, currencies and crypto are each pinned to the old day
    # budget until their own round measures the change. A default that
    # followed the index book would silently re-size the other three.
    #
    # So the default is the rule that was here before, which is the rule the
    # three pinned books still run, and `tjr_bot.TjrBot._open` passes the flag
    # explicitly from its own Config.
    #
    # THE ONE OPEN SEAM, STATED RATHER THAN HIDDEN. `tjr_desk._size_for` calls
    # this without the flag, so an INDEX order re-sized by the desk would use
    # the held-still rule while the replay used per-trade. It can only ever
    # come in AT or UNDER the replay's size, never over, because the desk also
    # forwards `outer_allowance` and per-trade sizing sets that equal to the
    # allowance itself — `test_the_desk_can_only_ever_under_size` holds that
    # bound. Closing it properly means the desk forwarding one more field,
    # which is a change to a file step465 was told not to open.
    if hold_size_still is None:
        hold_size_still = True

    out = tjr_bot.size_position(
        account=account, entry=entry, stop_distance=stop_distance,
        risk_allowance=float(risk_pct) * float(account),
        tightest_stop_pct=tightest_stop_pct, usd_per_quote=usd_per_quote,
        buying_power=buying_power, outer_allowance=outer_allowance,
        hold_size_still=hold_size_still)
    if not out["ok"]:
        return out
    if not out["measured"]:
        # THE ONE POLICY ON TOP OF THE ARITHMETIC, AND IT IS HIS. The bot will
        # size off today's own stop for research when an instrument's tightest
        # stop has never been measured. An ORDER may not: "sizing off another
        # market's number is exactly what his rule forbids", and a size that
        # is not the set size is not the size his rule produces. So the alert
        # refuses to state one rather than inventing it.
        out["ok"] = False
        out["units"] = 0.0
        return out

    out["lots"] = out["units"] / STANDARD_LOT
    out["cap_share_pct"] = 100.0 * cap
    if market in ("currencies", "forex"):
        out["per_step"] = out["units"] * pip_size(symbol) * usd_per_quote
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

    if market in ("currencies", "forex"):
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
    # one the set size produced, and hiding that would be the worst kind of
    # quiet change. Both numbers, and which rule did it.
    if size.get("capped"):
        lines.append(
            f"               SIZE CUT TO KEEP THE DAY INSIDE HIS BAND. Held "
            f"to the set size this trade would have risked "
            f"${size['uncapped_risk_dollars']:,.0f}, which is "
            f"{size['uncapped_risk_share_pct']:.1f}% OF THE ACCOUNT — today's "
            f"stop is {size['wider']:.0f} times wider than the tightest this "
            f"market gives. It was cut to hold the DAY at "
            f"{size['cap_share_pct']:.0f}% of the account, the top of the "
            f"band he states: \"one percent down on the day, two percent down "
            f"or three percent down on the day\". Switch it off with "
            f"CRYPTOBOT_MAX_RISK_PCT=0.")

    face = size["units"] * entry * usd_per_quote
    if face > 0 and account > 0:
        times = face / account
        lines.append(f"Face value     ${face:,.0f}"
                     + (f", which is {times:.1f} times the account — if your "
                        f"broker will not allow that much, take what it does"
                        if times > 1.05 else ""))

        # MARGIN AND RISK, BOTH IN DOLLARS, BOTH ON THE MESSAGE.
        #
        # Wallace, 2026-07-26: "I thought margin and risk to you was the
        # same." They sound identical and they are not, and the difference
        # is the whole reason a $6,000 position can only cost $20:
        #
        #   MARGIN is what is set aside to hold the position. It comes back
        #          when the trade closes.
        #   RISK   is what is actually lost if the stop is hit.
        #
        # They differ only because the stop is CLOSE. Put them side by side
        # in dollars so the gap is visible rather than something he has to
        # work out from a percentage.
        marg = account * margin_share()
        if marg > 0:
            lines.append(
                f"Money down     ${marg:,.2f} of margin to hold it "
                f"(that comes back when the trade closes)")
            lines.append(
                f"Money at risk  ${size['risk_dollars']:,.2f} if the stop is "
                f"hit — that is what you actually lose, "
                f"{size['risk_share_pct']:.2f}% OF THE ACCOUNT")
            if marg > 0 and size["risk_dollars"] > 0:
                lines.append(
                    f"               so ${marg:,.2f} down controls "
                    f"${face:,.0f}, and being wrong costs "
                    f"${size['risk_dollars']:,.2f} of it")
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

    A SIGNAL MAY WRITE ITS OWN. Everything below rewrites the TJR method's
    vocabulary — a liquidity grab, a break of structure, a gap inversion — and
    that is the only vocabulary it knows. Crypto is decided by Craig's method
    now (craig_live.py), whose sentence is about a different set of things
    entirely, so it arrives already written and in plain words. A signal that
    carries no `why` is a TJR signal and reads exactly as it always has.
    """
    if sig.get("why"):
        return str(sig["why"])
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
    """One symbol's numbers, COMPACT.

    Wallace, 2026-07-26: "instead of all these words, just do tp($,%) if
    theres only 1, if theres more than one just do tp1, tp2. and same for
    sl($,%). just say 203.71 margin (xxx% of account)."

    The long form said the right things and said too many of them. This is
    the same information as a table he can read in one glance on a phone.

    THE PERCENTAGE RULE IS NOT BROKEN, IT IS HOISTED. Every number in the
    money column is a share of the ACCOUNT, and the block says so once at the
    top rather than repeating it on nine lines. A percentage that appears
    beside a PRICE is still labelled as a move in the price, because those
    two are the pair that gets confused.
    """
    market, sym = sig["market"], sig["symbol"]
    spec = MARKETS[market]
    entry = float(sig["reference_price"])
    stop = float(sig["stop"])
    dist = abs(entry - stop)
    side = "BUY" if sig["direction"] > 0 else "SELL SHORT"

    risk_pct = 0.01
    if account > 0 and sig.get("risk_wanted"):
        risk_pct = float(sig["risk_wanted"]) / account
    # THE TWO HALVINGS ARE DIFFERENT THINGS AND MUST NOT BE CONFLATED. One is
    # the news-day half size. The other is Day 8's split, which gives THIS
    # trade half of a full-size day because a second setup was already
    # forming. Reading the trade's share alone said "HALF SIZE today — news or
    # a holiday" on an ordinary day with two setups on it, which is simply
    # false.
    #
    # step465: the bot now SAYS which it is rather than leaving this to infer
    # it from a threshold. `derisk` comes straight off the news calendar in
    # `tjr_bot.live_step`. The old inference is kept only for a signal built
    # before that key existed, and it was never reliable — it assumed the
    # full-size number was one per cent, which is no longer true now that the
    # size is set per trade.
    share = float(sig.get("budget_share") or 1.0)
    day_pct = risk_pct / share if share > 0 else risk_pct
    if "derisk" in sig:
        half_size_day = bool(sig["derisk"])
    else:
        half_size_day = day_pct < 0.0075

    # WHICH SIZING RULE — THE SIGNAL SAYS, AND THE MESSAGE MUST NOT GUESS.
    # A message that states a different size from the one the order carried
    # is worse than no message: he would reconcile his screen against it and
    # find they disagree. The desk's order path (`tjr_desk._size_for`) reads
    # this same key off this same signal, so the two cannot drift. A signal
    # that does not carry it is a TJR signal and gets the old default, which
    # position_size resolves from None to the held-still rule.
    # AND WHICH OUTER LIMIT — SAME REASON, AND IT IS THE CRAIG PATH ONLY.
    #
    # Left alone this call takes the single-trade fallback ceiling above, 3%
    # OF THE ACCOUNT, which is right for every book that has one and is what
    # every TJR message still gets.
    #
    # A CRAIG SIGNAL FROM THE BLOFIN BOOK CARRIES ITS OWN, and it has to be
    # honoured here or this message states a size the order does not carry.
    # That book runs the MONEY-GAME LADDER — Alex Gonzalez's "anything below
    # $25,000, it's all the money game", four or five trades in you, which on
    # Wallace's $2,178 stake is 22% OF THE ACCOUNT on one trade. The desk's
    # order path (`tjr_desk._size_for`) already forwards `outer_allowance`
    # from the signal, so without this line the order would go out at 22% and
    # the message would say 3%, and he would reconcile his BloFin screen
    # against a number nothing ever sent.
    #
    # Narrowed to `engine == "craig"` on purpose: nothing else on the desk
    # changes, and no message shape changes either — the same lines, with the
    # size the order actually carried.
    #
    # AND `engine == "alex"` FROM 2026-07-27, for the identical reason. The
    # forex and gold books scale the size UP on his confluence — "you can
    # risk more on low-risk trades" — so a setup with every confluence he
    # names asks for twice the base 3%, which is over the single-trade
    # fallback ceiling below. Without this line the order would go out at the
    # bigger size and the message would state the smaller one.
    outer = (sig.get("outer_allowance")
             if sig.get("engine") in ("craig", "alex") else None)
    size = position_size(market, sym, account, entry, dist,
                         float(sig.get("tightest_stop_pct") or 0.0),
                         usd_per_quote, risk_pct, outer_allowance=outer,
                         hold_size_still=sig.get("hold_size_still"))

    marg = account * margin_share()

    # THE MARGIN THE EXCHANGE WILL ACTUALLY ASK FOR, when the signal knows
    # what that exchange's ceiling is. Everything else on the desk keeps the
    # flat margin share above.
    #
    # `margin_share()` is a BUDGET — how much of the account we set aside to
    # hold one position — and the leverage falls out of it. That works while
    # the leverage it implies is a number the exchange will accept. The
    # money-game ladder breaks that: a position 60 times the account on a 10%
    # margin implies 602x, and BloFin's ETH ceiling is 150x. The exchange does
    # not refuse — it posts FOUR TIMES THE MARGIN instead. So a message built
    # on the budget would state a leverage that cannot exist and a margin four
    # times smaller than the one that will actually be tied up, and every
    # "% OF THE MARGIN" underneath it would be wrong by the same factor.
    #
    # This is exactly what `venue.BlofinVenue._leverage_for` does, and only
    # ever in the direction of MORE margin, never less.
    ceiling = float(sig.get("leverage_ceiling") or 0.0)
    ceiling_binds = False
    if ceiling > 0 and marg > 0 and size.get("ok"):
        face_now = (size.get("units") or 0.0) * entry * (usd_per_quote or 1.0)
        if face_now > ceiling * marg:
            marg = face_now / ceiling
            ceiling_binds = True

    def money(d):
        """A dollar amount and what it is AS A SHARE OF THE MARGIN.

        Wallace, 2026-07-26: "change it to the % of the margin. so like my
        recent eth trade that i tp for 35% and made 176 dollars, my margin
        was like 500."

        That is the number the exchange puts on his screen — BloFin's
        unrealizedPnlRatio is profit over the margin posted, not over the
        account. Showing a share of the ACCOUNT here made every trade look
        tiny (1% instead of 10%) and did not match anything he could see
        while the trade was running.
        """
        pct = (100.0 * d / marg) if marg > 0 else 0.0
        return f"${d:,.2f} ({pct:.1f}%)"

    lines = [f"{side} {sym}", ""]
    if not size.get("ok"):
        lines.append("SIZE COULD NOT BE WORKED OUT — do not take this one")
        lines.append(f"  no measured tightest stop for {sym}, and borrowing "
                     f"another market's number is the one thing his rule "
                     f"forbids")
        lines += ["", "Why:", "  " + plain_reason(sig)]
        return lines

    lines.append("money below: dollars, and the % OF THE MARGIN "
                 "(what the exchange shows you)")
    lines.append(f"Entry   {fmt_price(sym, entry)}"
                 + ("   RESTING LIMIT — it fills only if price comes back to it"
                    if sig.get("order_type") == "limit" else ""))

    tgts = [float(t) for t in (sig.get("targets") or [])][:4]
    srcs = list(sig.get("target_sources") or [])
    units = size.get("units") or 0.0

    lost = units * dist * (usd_per_quote or 1.0)
    lines.append(f"SL      {fmt_price(sym, stop)}   -{money(lost)}   "
                 f"{100.0 * dist / entry:.2f}% move in the price")

    # HIS LADDER, from the bot, never re-derived here. Half at the first
    # target, half of what is still open at the second, and the last quarter
    # is a runner that sits on no target at all. This used to spread the tail
    # evenly across every target, which was ours and a guess; Day 9 answered
    # it — "another fifty percent of the OPEN position".
    fracs = list(sig.get("target_fractions")
                 or tjr_bot.target_fractions(len(tgts), tjr_bot.Config()))
    runner = float(sig.get("runner_fraction")
                   or tjr_bot.runner_fraction(len(tgts), tjr_bot.Config()))
    running = 0.0
    for i, tp in enumerate(tgts):
        frac = fracs[i] if i < len(fracs) else 0.0
        made = units * frac * abs(tp - entry) * (usd_per_quote or 1.0)
        running += made
        name = "TP " if len(tgts) == 1 else f"TP{i + 1}"
        if frac <= 0:
            lines.append(f"{name}     {fmt_price(sym, tp)}   nothing comes "
                         f"off here — the last piece rides through it")
            continue
        tail = f"   running +{money(running)}" if len(tgts) > 1 else ""
        lines.append(f"{name}     {fmt_price(sym, tp)}   +{money(made)}"
                     f"   {100*frac:.0f}% off{tail}")
    if not tgts:
        lines.append("TP      none on the chart ahead — run it to the stop")

    whole = spec["whole_units"]
    if market in ("currencies", "forex"):
        # A CURRENCY SIZE IS NOT THE UNIT COUNT AND MUST NEVER BE PRINTED AS
        # ONE. `units` here is units of the BASE currency — 805,446 euros —
        # and a standard lot is 100,000 of them. Printing "805,446 standard
        # lots" is not a formatting slip: it is a size a hundred thousand
        # times too large, on the one line he would copy into a ticket.
        u = f"{units / STANDARD_LOT:,.2f}"
        base = PAIR_SPEC.get(sym, {}).get("base_name", "units")
        tail = f"  ({units:,.0f} {base})"
    else:
        u = f"{units:,.0f}" if whole else f"{units:,.6f}".rstrip("0").rstrip(".")
        tail = ""
    face = units * entry * (usd_per_quote or 1.0)
    lines.append(f"Size    {u} {spec['size_unit']}  =  "
                 f"${face:,.0f} position{tail}")
    lev = (face / marg) if marg > 0 else 0.0
    lines.append(f"Margin  ${marg:,.2f}   Leverage {lev:.0f}x")
    if ceiling_binds:
        # SAID OUT LOUD, NOT QUIETLY APPLIED. He will see this margin on his
        # exchange screen and it is bigger than the desk's usual share of the
        # account, so the message says why before he asks.
        #
        # THE REASON IS NOT ALWAYS THE SAME REASON, so a signal that knows its
        # own may say it. On the crypto book the ceiling is the INSTRUMENT'S —
        # ETH stops at 150x whatever you ask for. On the gold book it is the
        # LIQUIDATION — the position posts enough margin that the exchange
        # cannot close it before the stop is reached. Both hold more margin
        # than the usual share and both leave the size and the stop alone,
        # which is what the second half of the sentence says either way.
        why = sig.get("leverage_note") or \
            f"{sym} stops at {ceiling:.0f}x on this exchange"
        lines.append(f"{why}, so it holds ${marg:,.2f} of the account as "
                     f"margin — {100*marg/account:.0f}% OF THE ACCOUNT. That "
                     f"margin comes back when the trade closes; the size and "
                     f"the stop are unchanged.")

    if half_size_day:
        lines.append("HALF SIZE today — news or a holiday")
    if size.get("wider", 1.0) > 1.6:
        # The one place the ACCOUNT share has to be said out loud. Everything
        # else on the message is a share of the margin, which is what the
        # exchange shows — but a day where his rule quietly risks three
        # percent of the whole account instead of one is the day he should
        # be told in account terms, not left to convert it.
        # SAY IT IN LEVERAGE, NOT IN "RISK". Wallace, 2026-07-26: "dont
        # ever use that term again and just stick with leverage... on that
        # blofin screen i see leverage, I hope you know that." The account
        # share still appears because a day that quietly costs three percent
        # of everything instead of one has to be said in those terms — but
        # leverage leads, because leverage is what he can see.
        lines.append(f"Today's stop is {size['wider']:.1f}x wider than this "
                     f"market's tightest, and the size does not shrink for "
                     f"it — that is his rule, on purpose. So this one is "
                     f"carrying more than usual: {size['risk_share_pct']:.2f}% "
                     f"OF THE ACCOUNT if the stop is hit, against the "
                     f"{100*risk_pct:.2f}% this trade drew from today's "
                     f"budget.")
    if size.get("capped"):
        lines.append(f"Size cut to hold THE DAY inside "
                     f"{size['cap_share_pct']:.0f}% of the account, which is "
                     f"the top of his band. Switch off with "
                     f"CRYPTOBOT_MAX_RISK_PCT=0.")

    if share < 0.999:
        lines.append(f"This one takes {100*share:.0f}% of today's risk "
                     f"budget, not all of it"
                     + (" — a second setup was already forming"
                        if sig.get("second_setup_expected") else ""))

    if len(tgts) > 1:
        lines.append("Half comes off at TP1 and the stop moves to your entry. "
                     "Half of what is left comes off at TP2.")
        if runner > 0:
            lines.append(f"The last {100*runner:.0f}% has no target on it. It "
                         f"comes off when the 1-minute chart breaks back "
                         f"against you, and otherwise it stops at your entry "
                         f"price and costs nothing.")

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

    # THE HEADER MUST SAY WHAT ACTUALLY HAPPENED. 2026-07-26.
    #
    # This said "take this one by hand" on EVERY message, left over from the
    # hours when the plan was Wallace executing from alerts. The bot places
    # its own orders now. On 26 July it opened a DOT short, could not put the
    # stop on because price had already run past where the stop belonged, so
    # it correctly closed the position one second later — and then sent a
    # message headed "take this one by hand". He read that as being told to
    # go and place a trade the bot had just refused on safety grounds.
    #
    # A message that tells him to do something the bot deliberately would not
    # do is worse than no message. The header is now derived from the order's
    # real outcome, and only a market HE executes may ever say "by hand".
    placed = [s.get("placed") or {} for s in sigs]
    states = {p.get("status") for p in placed}
    by_hand = any(p.get("human_executes") for p in placed)

    n = len(sigs)
    many = f"{n} setups at once — " if n > 1 else ""

    if by_hand:
        what = "take them by hand" if n > 1 else "take this one by hand"
    elif states and states <= {"resting"}:
        # A RESTING LIMIT IS NOT A POSITION AND THE HEADER MAY NOT IMPLY ONE.
        # Craig's entry waits for price to come back to the middle of the gap,
        # so at this moment the bot owns an ORDER, not a trade, and it may
        # never own more than that. Saying "the bot took this one" here would
        # have him open the app looking for a position that is not there.
        what = ("the bot placed the orders and is waiting for the price"
                if n > 1 else
                "the bot placed the order and is waiting for the price")
    elif states and states <= {"unwound"}:
        what = "OPENED AND CLOSED AGAIN. NOTHING FOR YOU TO DO."
    elif states and states <= {"not_sent", "rejected", "cannot_send"}:
        what = "NOT TAKEN. NOTHING FOR YOU TO DO."
    elif "filled" in states:
        what = "the bot took them" if n > 1 else "the bot took this one"
    else:
        what = "setups found" if n > 1 else "setup found"

    head = f"{spec['label']} — {many}{what}"

    body = [head, "=" * 46, ""]
    for i, sig in enumerate(sigs):
        if i:
            body += ["", "-" * 46, ""]
        body += trade_block(sig, account, upq(sig["symbol"]))

    body += ["", spec["instrument"]]
    if any(s.get("single_exit") for s in sigs):
        # ONE EXIT, NOT A LADDER. Craig's method has a single target at four
        # times the risk and takes the whole position off there; there is no
        # half at the first target and no runner behind it. The ladder
        # paragraph below is the TJR method's and would be an instruction to
        # do something this trade has no provision for.
        # ONE EXIT, AND WHOSE ONE EXIT IT IS. Craig's single target has a
        # break-even rule behind it and his entry is an order that may never
        # fill; Alex's has neither — "set and forget", "I am not a break even
        # trader", and the entry is taken at market the second the candle
        # closes. Telling him the stop will move to his entry on a book where
        # it never does is telling him something that will not happen, so a
        # signal that knows its own management says it.
        own = [s.get("exit_note") for s in sigs if s.get("exit_note")]
        body += ["", own[0] if own else
                 "There is nothing to do at any point. The whole position "
                 "comes off at the target, the stop is already resting at the "
                 "exchange, and the bot moves that stop to your entry price "
                 "the moment a 1-hour candle closes past the last swing in "
                 "your favour — from then on the trade cannot cost anything. "
                 "If price never comes back to the entry, the order is "
                 "cancelled and I will tell you.",
                 "",
                 "I will message you when it fills, when the stop moves, and "
                 "when it is out." if not own else
                 "I will message you when it is out, and not before."]
    elif any(s.get("targets") for s in sigs):
        body.append("")
        body.append("When the first target is reached: take HALF off and move "
                    "the stop to your entry price. At the second target take "
                    "HALF OF WHAT IS STILL OPEN. The last quarter has no "
                    "target on it and comes off when the 1-minute chart "
                    "breaks back against you. I will message you at each of "
                    "those points.")
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
        "From here the trade cannot lose money. Half of what is still open "
        "comes off at the second target, and the last quarter comes off when "
        "the 1-minute chart breaks back against you.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: half off, move the stop", msg


def filled_message(market: str, symbol: str, price: float, stop: float,
                   target: float, when: dt.datetime | None = None) -> tuple:
    """A RESTING LIMIT HAS FILLED — the bot now owns a position it did not own
    a minute ago.

    Added 2026-07-26 with Craig's method. It has no TJR equivalent because a
    TJR entry goes in at market and the entry message IS the fill message. A
    limit that rests for up to a day and then fills while he is asleep is a
    different event and it needs its own line, or the first he hears of the
    trade is the message telling him it is over.
    """
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"FILLED at {fmt_price(symbol, price)}. The order you were told about "
        f"earlier is now a position.",
        "",
        f"Stop   {fmt_price(symbol, stop)}   already resting at the exchange",
        f"Target {fmt_price(symbol, target)}",
        "",
        "Nothing for you to do.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: filled", msg


def breakeven_message(market: str, symbol: str, entry: float, why: str,
                      when: dt.datetime | None = None) -> tuple:
    """THE STOP HAS MOVED TO THE ENTRY. Not "half off, move the stop" — that
    is the TJR ladder and Craig has no ladder. The whole position is still on;
    all that changed is that it can no longer cost anything."""
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"The stop is now at {fmt_price(symbol, entry)}, your entry price. "
        f"The whole position is still on and it can no longer lose money.",
        "", why, "",
        "Nothing for you to do.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: stop at break even", msg


def order_cancelled_message(market: str, symbol: str, price: float, why: str,
                            when: dt.datetime | None = None) -> tuple:
    """A RESTING ENTRY DIED WITHOUT EVER FILLING. No position was ever opened
    and no money moved.

    It is sent because silence here would be the wrong kind: he was told the
    bot had placed an order, and an order that quietly disappears is exactly
    the sort of thing that makes him stop trusting the messages.
    """
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"The resting order at {fmt_price(symbol, price)} is cancelled. It "
        f"never filled, so nothing was ever opened and this cost nothing.",
        "", why, "",
        "Nothing for you to do.",
        "",
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: order cancelled", msg


def close_message(market: str, symbol: str, price: float, why: str,
                  when: dt.datetime | None = None, account: str = "") -> tuple:
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"Close it now, around {fmt_price(symbol, price)}.",
        "", why, "",
        *( [account, ""] if account else [] ),
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: close it", msg


def stopped_message(market: str, symbol: str, price: float,
                    when: dt.datetime | None = None, account: str = "") -> tuple:
    when = when or dt.datetime.now()
    msg = "\n".join([
        f"{MARKETS[market]['label']} — {symbol}",
        "=" * 46, "",
        f"Your stop at {fmt_price(symbol, price)} should have been hit.",
        "",
        "Check the position is closed. Nothing else to do — this one was "
        "wrong and it cost exactly what it was set up to cost.",
        "",
        *( [account, ""] if account else [] ),
        f"{when:%H:%M} New York time."])
    return f"{MARKETS[market]['label']} · {symbol}: stopped out", msg


def account_line(venue, market: str = "") -> str:
    """Where the account stands, read from the venue, for the end of a
    close message.

    Wallace, 2026-07-26: "after a trade is done just give me an update on my
    account equity on telegram."

    READ IT, DO NOT COMPUTE IT. The exchange's own equity already has the
    fees and the realised profit inside it, and this project has twice put a
    wrong number in front of him by modelling something the venue was already
    willing to state. If the read fails, SAY it failed — an equity figure
    that is quietly stale is worse than none, because he would act on it.
    """
    try:
        acct = venue.account() or {}
        eq = float(acct.get("equity") or 0.0)
        if eq <= 0:
            return "Account: could not be read just now."
        return f"Account now ${eq:,.2f}"
    except Exception as e:                                   # noqa: BLE001
        return f"Account: could not be read just now ({str(e)[:60]})."


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
