#!/usr/bin/env python3
"""alex_engine.py — ALEX GONZALEZ'S METHOD, ONE ENGINE, TWO VENUES.

WHOSE METHOD THIS IS, AND WHOSE IT IS NOT

    Alex Gonzalez, @fxalexg__ on YouTube, 1.31M subscribers, "Set and Forget".
    The corpus is `ag_transcripts/` and the read of it is
    `step464_alex_gonzalez_corpus.md`. Every rule below carries a verbatim
    quote, a source file and an upload date, and where his material is silent
    it says so and the choice is listed in `in_his_words()`.

    METHODS DO NOT MIX. TJR drives stocks. Craig drives crypto. Alex drives
    FOREX AND GOLD, and nothing in this file is imported from either of the
    other two men's judgement. The only things reached out of `tjr_bot` are
    two pure helpers with no opinion in them — a swing definition and the
    project's single sizing function — and a test asserts that stays true.

    Gold is here because he put it here, in his own words:

        "I'm taking this trade as if it were to be a foreign exchange currency
         pair ... based off market structure, not for the commodity that it
         is."
        — ag_transcripts/ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09

TWO VENUES, ONE METHOD

    His currency pairs would trade on OANDA practice. Gold would trade as
    XAUT-USDT (Tether Gold) on BloFin demo, which is why gold's costs are
    BloFin's and the pairs' costs are OANDA's. Gold REPLAYS on OANDA XAU/USD
    candles because that is the deepest clean gold tape we can read; OANDA is
    never asked to trade it.

    THIS FILE PLACES NO ORDERS ON ANY VENUE. It does not import a venue, does
    not fetch, and does not write. It reads parquet that
    `step470_fetch_oanda.py` already pulled and it returns trades.

============================================================ THE SPINE

THE NEWEST TEACHING GOVERNS, AND IT IS A SIMPLER STRATEGY THAN THE OLDER ONES

    `ag_transcripts/KPVVOa6c6dY_dumb_clean.txt` — "How Trading Dumb Made Me a
    Millionaire Trader (You Can Too)", uploaded **2026-06-14**. Six weeks old
    at the time of writing and the newest teaching in a 198-upload corpus.
    Wallace sent it specifically for forex. Under newest-governs it outranks
    everything below it, and it is a deliberate back-to-basics restatement of
    the whole method rather than a lesson on one piece:

        "We're going to remove everything that you know about trading, throw
         it into the bin, and start from scratch with a simple approach ...
         And you're going to stick to this approach until you are consistently
         profitable with this approach."

    ITS WHOLE CONTENT IS FOUR CHOICES:

        "This is literally one time frame, one setup, one entry rule, and one
         session. That is it."
        "It's going to be one pair, one time frame, one session, and one entry
         signal."

    S1. ONE PAIR — EUR/USD.
        "if I were to have to pick one market out of all of these markets
         right here ... it would be EuroUSD. EuroUSD might be slower moving in
         terms of pips, but I can get great risk-to-reward and it's extremely
         predictable patterns."

    S2. ONE TIMEFRAME — THE 4 HOUR, AND ONLY IT.
        "what I found to be the perfect time frame to trade on one specific
         pair would be the 4hour time frame. The 4hour time frame is that
         perfect medium from the higher time frame and that lower time frame
         where you get that stronger confirmation but you can also still get
         that high pacing move"

        And he throws out top-down analysis BY NAME for this strategy:

        "top down analysis is how you trade all of these time frames together,
         which is a different approach, which is more advanced. And it's not
         what this video is about. This video is picking ONE TIME FRAME ONLY,
         which keeps things a lot simpler and will probably even make you more
         successful"

        >>> THIS CONFLICTS WITH THE OLDER TOP-DOWN RULE (rule 1 below,
        >>> grw58BIzotU.txt 04:40:37, 2025-09-28, and pD1vAUMbSjw.txt
        >>> 00:02:36, 2026-02-02). NEWEST GOVERNS: the shipping engine reads
        >>> the 4 hour and nothing else. The top-down path is kept in this
        >>> file as `find_setups_topdown` so the conflict is recorded rather
        >>> than deleted, and both are measured.

    S3. ONE SESSION — PRE-LONDON AND LONDON.
        "I would look to take a trade either one or two hours before London
         session. So it'd be right around here like 1 2 in the morning my time
         zone EST. Hold the position throughout all of London session and then
         as soon as New York and London session have this crossover, this is
         where you would have the most volatility"
        "I would suggest to always stick to London session."

        On a 4-hour grid anchored at OANDA's 17:00 New York day boundary the
        bars close at 21:00, 01:00, 05:00, 09:00, 13:00 and 17:00 New York.
        His window admits exactly TWO of those six — the 01:00 and the 05:00
        closes — which is precisely "one or two hours before London" and
        through London. That is not a parameter we chose; it falls out of his
        sentence and the venue's own grid.

        >>> THIS NARROWS THE OLDER 01:00-10:30 WINDOW (rule 9 below). Both are
        >>> his; the newer is tighter and it is what ships.

    S4. ONE ENTRY SIGNAL — THE ENGULFING CANDLE, AND NOTHING ELSE.
        "If I were to recommend you an entry signal and an approach to stick
         to every single time, no matter what, doesn't matter what day it is,
         what week it is, what pair it is, what session it is, it would come
         down to these entry confirmations. And that is going to be THE
         BULLISH AND BEARISH ENGULFING CANDLESTICK confirmations."

        And he grades them, which is a quality dial in his own words:

        "The more candlestick it engulfs, the better."
        "This right here is probably my favorite type of engulfing candlestick
         simply because what you have here is one candlestick that has eaten
         the last 10 candlesticks. has struggled significantly to break
         through this area."
        "This looks like a bullish candle, but it didn't really engulf
         anything other than this small candle ... this is NOT a bullish
         engulfing candlestick."

        >>> THIS CONFLICTS WITH THE THREE-CONFIRMATION MENU (rule 5 below,
        >>> BcWxqfcjk9A.txt 2026-04-16 and grw58BIzotU.txt 2025-09-28, which
        >>> also allow rejection candles and morning/evening stars). NEWEST
        >>> GOVERNS: the shipping engine takes engulfing candles only.

    S5. DIRECTION IS 4-HOUR MARKET STRUCTURE, READ THE SAME WAY AS EVER.
        "This at one point was the higher high ... and then this right here
         was the higher low ... Then we broke below that higher low, shifting
         that market to now being bearish. So, this market structure is now
         bearish. Perfect. I've identified that this market structure is
         bearish. Now, I need to be looking for sells."

        And the summary of the whole strategy, in one sentence:

        "You're just watching the direction of the market. You're following
         that direction of the markets and you're waiting for your engulfing
         candlestick in the direction that you have identified already. It
         quite really is that simple."

    S6. THE STOP IS AT STRUCTURE, THE TARGET IS 1:2 AT THE STRUCTURE POINT
        TO THE LEFT.
        "You would have had your stop loss be somewhere above this right
         shoulder and then your takerit could have been right at this neckline
         right here for the 1 to2."
        "My stop loss right here. And then my take profit could be this next
         structure point that's running around right here to the left."

    S7. THE ENTRY TIMEFRAME AND THE TARGET TIMEFRAME MAY NOT BE MIXED.
        "if you're taking a day trade entry, you stick to a day trade takerit.
         If you're taking a scalp or an intraday trade, you stick to a scalp
         or an intraday takerit. Don't crossorrelate both of them because what
         will end up happening is you'll let a massive winning position for
         your time frame that you're trading turn into a losing position
         because you're looking for too much profit."

    S8. A NEW RULE THAT IS NOT IN ANY OLDER VIDEO — THE FRIDAY EXIT.
        "Do you hold a position that you entered in London session throughout
         Sydney and Tokyo if it has not reached to your takerit? Yes and no.
         Yes, if the market is giving you all the possible indications that it
         could still continue to go to your takerit ... NO, IF YOU'RE IN A
         LOSING POSITION AND THE WEEKEND IS COMING UP AND YOU'RE HALFWAY
         THROUGH YOUR STOP LOSS, I WOULD PROBABLY CLOSE BEFORE THE MARKET
         CLOSES because when market opens on Sunday when the spreads are quite
         high, that could simply take you out at a loss because of the spread."

        >>> THIS IS NOT A BREAK EVEN AND IT IS NOT A TRAIL. It is a flat-out
        >>> close before the weekend, and ONLY when the trade is more than
        >>> halfway to its stop. It does not contradict "I am not a break even
        >>> trader" — a break-even exit is at the entry price and this one is
        >>> at a loss. It is implemented, gated on his own two conditions, and
        >>> it is measured with and without.

    S9. AND HE HOLDS A LOSER THAT IS STILL REJECTING.
        "If the trade is halfway through your stop loss but it's still
         rejecting, I would still also continue to hold."
        SILENT on what "still rejecting" means mechanically. Not implemented,
        and the omission makes our Friday exit MORE eager than his.

    WHAT THE SPINE DOES NOT MENTION AT ALL: areas of interest, the three-touch
    rule, the weekly, the daily, news, correlation. "Trading like an idiot,
    you don't take any of that into account."

================================================ H. THE HEAD AND SHOULDERS

HIS GO-TO PATTERN, AND THE ONE THIS ENGINE WAS MISSING UNTIL step472

    It is not a footnote in his material. It is the pattern he names when he
    is asked how to grow a small account, in his NEWEST upload of all
    (hb7ot1_szWI.txt, "How to Start Trading with Just $50", 2026-07-26), and
    the master course gives it its own hour.

    H1. IT IS THE ONLY REVERSAL PATTERN HE USES.
        "my favorites and the only reversal pattern that you're going to need
         is going to be this head and shoulders pattern ... This is my go-to
         pattern. Like this is my [censored] right here. I use this every
         single day in the market."
        — grw58BIzotU.txt 06:49:00, 2025-09-28

    H2. IT IS DRAWN ON BODIES. WICKS ARE NOT STRUCTURE.
        "this head and shoulders pattern is done to the market structure ...
         that is done to the BODIES of the candlestick. WE ARE NOT INCLUDING
         THE WICKS AT NO POINT when identifying a head and shoulders."
        — grw58BIzotU.txt 06:51:10, 2025-09-28

    H3. THE NECKLINE IS THE BROKEN STRUCTURE POINT, NOT A DIAGONAL.
        "the neckline is going to be based off of the previous structure
         points which is basically where the HIGHER LOW AND THE SHIFT HAS BEEN
         CREATED which would be right here. This is the neckline. The neckline
         is not going to be this imaginary line."
        — grw58BIzotU.txt 06:55:37, 2025-09-28

        And the pattern does not exist until that line breaks:

        "The head and shoulders will only be valid ONCE WE BREAK THE NECKLINE.
         If we have not broken the neckline, we cannot count it as a head and
         shoulders cuz it's not a confirmed head and shoulders."
        — grw58BIzotU.txt 06:56:50, 2025-09-28

        The break IS the change of character, in his own equivalence:

        "That is a shift of structure. That is a change of character. That is
         a break of structure. This is now bearish."
        — grw58BIzotU.txt 06:52:27, 2025-09-28

    H4. THE NECKLINE IS ALSO AN AREA OF INTEREST, AND THE PATTERN HAS TO SIT
        SOMEWHERE THAT MATTERS.
        "It's always going to be at an area of interest as well. So the
         neckline of the head and shoulders is going to be the retest of an
         area of interest."
        — grw58BIzotU.txt 06:56:02, 2025-09-28

        "You want to make sure that you're getting this head and shoulders
         pattern at a resistance. If you're looking to sell, you want to make
         sure you can have it at a support. If you're looking to buy."
        — grw58BIzotU.txt 07:04:36, 2025-09-28

    H5. THE ENTRY IS THE RETEST, AND A CLOSED CANDLE ON THAT RETEST.
        "us as traders, WE DO NOT ENTER THE TRADE ON THE BREAKOUT OF THE
         NECKLINE. We have to wait for price to come back into this area and
         then retest. And then once it retests, then you look for those
         candlestick formations here. Since you're looking to sell, you look
         for a bearish shooting star and then a bearish engulfing candlestick."
        — grw58BIzotU.txt 07:02:12, 2025-09-28

    H6. THE RIGHT-SHOULDER ENTRY EXISTS AND HE TELLS YOU NOT TO TAKE IT.
        "you can either sell at the right shoulder or sell at the break and
         retest. SELLING AT THE RIGHT SHOULDER IS EXTREMELY HIGH RISK. I DON'T
         RECOMMEND IT unless you are an experienced trader. Selling at the
         break and retest of the head and shoulders is where it is the proper
         reversal trade confirmation."
        — grw58BIzotU.txt 06:54:46, 2025-09-28
        >>> Built, and OFF by default, because he says not to take it.

    H7. THE STOP GOES ABOVE THE WICK OF THE RIGHT SHOULDER.
        "This market closed below. We shifted, retested, entered this position
         with MY STOP LOSS ABOVE THE WICK, my take profit to the next
         structure point."
        — hb7ot1_szWI.txt 00:28:46, 2026-07-26
        "I simply place my stop loss above the area where if it gets hit, it
         should break above it."
        — 1fGzVHI7rN0.txt 00:14:51, 2026-04-21
        >>> Note the wick, not the body. Bodies draw the PATTERN (H2); the
        >>> wick sets the STOP. Both are his, in the same breath, and they are
        >>> implemented separately for exactly that reason.

    H8. THE TARGET IS THE NEXT STRUCTURE POINT — see T below.

    H9. IT IS UGLY IN REAL LIFE AND HE SAYS SO.
        "The head and shoulders is NEVER going to be a beautiful textbook head
         and shoulders pattern like this. Does it happen? Yes. But I will
         never aim to always have a perfect one. The head and shoulders
         pattern is valid as long as it breaks the neckline."
        — grw58BIzotU.txt 06:52:01, 2025-09-28
        >>> Which is why the detector's only hard shape test is the neckline
        >>> break, and why the shoulders are not required to be symmetric.

=========================================== T. THE TARGET IS STRUCTURE

THE FLAT 1:2 WAS OURS, NOT HIS, AND IT WAS MEASURED AND FOUND WANTING

    step470 exited every trade at exactly twice the risk. That was OUR
    simplification of a floor he states for ACCEPTING a trade. What he
    actually does is target a level.

    T1. "my take profit to the NEXT STRUCTURE POINT. That is it."
        — hb7ot1_szWI.txt 00:28:46, 2026-07-26 (his newest)
        "Our take profits are based off of structure points."
        — 7dcJ2WZYDDQ.en.vtt, 2023-10-01
        "I literally just set and forget, put my stop loss above the structure
         point, put my take profit at the previous lower low point."
        — mBFVeLagITA.en.vtt 00:12:59, 2024-07-07

    T2. AND A LITTLE SHORT OF IT.
        "I simply place my takeprofit A LITTLE BIT BELOW THE NEXT STRUCTURE
         POINT where I believe that daily time frame is destined to go."
        — E3lYZsy8nYE.txt 00:24:25, 2025-06-09

    T3. THE 1:2 IS A FILTER ON WHICH SETUPS ARE WORTH TAKING.
        "I always place my take profit where I can have a reaction from that
         area. THE CLOSER THE BETTER and always at a minimum of a 1:2."
        — DsPLtzjTONI.txt 00:10:50, 2026-06-22
        "Do not take a trade that is not worth the risk."
        — hb7ot1_szWI.txt 00:33:38, 2026-07-26
        >>> So: take the NEAREST structure point that still pays 1:2 or more,
        >>> and if no structure point within reach pays 1:2, DO NOT TAKE THE
        >>> TRADE. Both halves of that sentence are his.

    T4. AND HE LEAVES ROOM ABOVE IT.
        "I always attempted to have every single trade setup always be a
         minimum of a one to two risk-to-reward ... But I would always aim for
         the trade to have a potential of a one to 4 risk-to-reward because
         I'm essentially getting another trade for free."
        — grw58BIzotU.txt 08:38:10, 2025-09-28

============================================ D. THE OTHER HALF OF THE TRIGGER

    D1. THE REJECTION / DOJI IS A CONFIRMATION IN ITS OWN RIGHT, AND STACKING
        THEM IS A QUALITY DIAL LIKE THE ENGULF COUNT.
        "the two types of confirmation we look for is EITHER A REJECTION, A
         DOJI, OR A BULLISH ENGULFING or a bearish engulfing ... But IF YOU
         HAVE BOTH OF THESE COMBINED, THEY WOULD BE A LOT MORE POWERFUL. THE
         MORE DOJIS THAT YOU WOULD HAVE, THE MORE POWERFUL. If you have
         several dojis like this set in place at a support level and then you
         get a bullish engulfing candlestick, even better."
        — BcWxqfcjk9A.txt 00:03:18, 2026-04-16

    D2. AND THE CANDLE MUST BE CLOSED. HIS WORDS, EMPHATICALLY.
        "as soon as that candlestick closes, it is a confirmation. 1 second
         before it closes, it is an entire anticipation. I've seen
         candlesticks in the last 5 seconds before closing completely change
         direction."
        — BcWxqfcjk9A.txt 00:02:53, 2026-04-16
        >>> Every read in this file is at a bar's close already. D2 is the
        >>> reason, in his own voice, and a test asserts it.

============================================ W. THE WEEKLY CLOSE SETS THE WEEK

    W1. "you need to wait for those weekly candlesticks to close ... And those
         candlesticks OPENING AND CLOSING DICTATE THE DIRECTION OF THE
         FOLLOWING WEEK. So, for example, let's say you're looking to buy on
         the weekly time frame ... and it closes bullish in that direction. If
         next week it closed bullish and you're still looking for more buys,
         why would you want to cut your winning position short?"
        — 1dL3xmxA2e0.txt 00:06:12, 2026-05-25

        Implemented as a direction bias: once a weekly candle has CLOSED, the
        following week's trades must agree with it (close above open = buys).
        It is OFF by default because the June spine is one timeframe and newer,
        and it is measured on so the layering is a number, not a belief.

============================================ C. THE TOP-DOWN LAYERS

    C1. "we go weekly, daily and then we stop at the 4 hour ... for the swing
         entries." — pD1vAUMbSjw.txt, 2026-02-02, and the same order in
        grw58BIzotU.txt 04:40:37, 2025-09-28.

        RECONCILED BY DATE, NOT BY PREFERENCE: the June 2026 spine is one
        timeframe and it is the newest, so IT is the default. But the spine is
        explicitly the beginner floor ("top down analysis ... is a different
        approach, which is MORE ADVANCED"). So the layers ship as an option
        and BOTH are measured: spine alone, and spine plus weekly/daily
        context. Nothing is asserted about which is better.

============================================ Q. SIZE FOLLOWS QUALITY

    Q1. "High risk in trading does not equal high reward ... LOW RISK EQUALS
         HIGH REWARD because the odds of you losing a trade that has a low
         risk of losing means that you have a high reward. So meaning YOU CAN
         RISK MORE ON LOW-RISK TRADES because it can make you more money."
        — LwMsai2ppKc.txt 00:22:34, 2026-02-22
        "if a trade has eight confluences for example that makes that a very
         low-risk trade ... So it makes more sense to risk more money on that."
        — grw58BIzotU.txt 07:36:32, 2025-09-28

        His quality inputs, each with its own quote above: how many candles
        the engulf ate (S4), how many dojis stacked into it (D1), whether both
        appeared together (D1), and whether the higher timeframes agree (C1,
        W1). The LADDER from those points to a position size is OURS and is
        declared in `in_his_words()`. The floor for VALIDITY is unchanged and
        is still his: one candle engulfed.

        >>> CONFLICT, OLDER, OVERRULED: "You pick one percentage that you
        >>> decide to take and every single trade is exactly the same. You do
        >>> not modify the percentage more or less." (tQ7pUImfYlY.en.vtt,
        >>> 2024-06-13). Two later videos (2025-09-28 and 2026-02-22) both
        >>> teach sizing by confluence. Newest governs.

============================================ X. WHY THERE IS NO SWEEP LOGIC

    NOT AN OMISSION. DOCTRINE, IN HIS OWN WORDS.

        "this right here is what many would call a LIQUIDITY SWEEP, a fake
         out, an institutional grab ... the banks are taking out the retail
         stop losses. And to me, I've been trading for the last 7 and 1/2
         years now, IT REALLY IS ALMOST A BIG HOAX. It's almost like the
         aliens ... there's no like real hardcore evidence."
        — Rua24ytuHuY.txt 00:06:29, 2026-06-04

    The TJR book in this repo is built on sweeps. NONE OF IT MAY EVER BE
    IMPORTED HERE. A test asserts that this file contains no sweep, liquidity,
    stop-hunt or judas machinery, and this quote is the reason.

============================================================ THE OLDER RULES

Everything below is from earlier uploads. It is kept because most of it is not
contradicted by the spine and fills in mechanics the spine leaves unstated —
sizing, the day-of-week gate, no-break-even, no-partials, the gold reading.
Where a rule below IS contradicted, the conflict is marked at the top of this
docstring and the newer statement is what ships.

1. TOP-DOWN, WEEKLY / DAILY / 4H FOR DIRECTION, 1H FOR THE TRIGGER
   *** SUPERSEDED for the shipping engine by S2. Kept as `find_setups_topdown`
   *** and measured beside it.

    "we will be using the weekly, the daily and the 4 hour. All of these three
     time frames, these are going to be used to identify the trend. So these
     are used to identify trend and area of interest slash support or
     resistance."
    — grw58BIzotU.txt 04:40:37, 2025-09-28

    "The weekly time frame will let you know obviously where markets can go
     for the next two to three weeks, the daily for the next couple of days
     and the 4 hour for the next couple of days."
    — LwMsai2ppKc.txt 00:23:51, 2026-02-22

    "The lowest time frame I go is the 15."
    — grw58BIzotU.txt 00:57:18, 2025-09-28

2. STRUCTURE SHIFTS ON THE BODY CLOSE, NEVER THE WICK

    "you only confirm that this market is bearish once we have body
     candlestick closed below ... It is only confirmed shifting structure once
     this candlestick has closed below."
    — grw58BIzotU.txt 04:02:48, 2025-09-28

    "If we have not body closed above or below, we are not shifting structure.
     Very simple."
    — grw58BIzotU.txt 03:44:23, 2025-09-28

3. AN AREA OF INTEREST NEEDS A MINIMUM OF THREE TOUCHES

    "We need to have a minimum of three touches for it to be considered an
     area of interest. You can have two touches that are resistance, one touch
     that is support, whatever the case is."
    — MhWSZp4yS2c.txt 00:24:10, 2026-06-28

    "We all know an area of interest needs a minimum of three touches. This
     only has one."
    — ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09  (rejecting a daily level for gold)

    Highs and lows count toward the SAME area — that is why the touches are
    clustered without regard to which side of price they formed on.

4. HE WAITS FOR THE MARKET TO CONFIRM THE REJECTION. HE DOES NOT ANTICIPATE

    "I like to wait for the market to show me its hand first on the higher
     time frames. I like to wait for weekly and daily rejections. If I'm going
     to enter a trade at a daily area of interest, for example, why would I
     enter the trade on the first hour rejection candlestick that I get? ...
     Give me the confirmation you're actually going in that direction and all
     I have to do is hop in that direction. I don't want to predict the
     perfect bottom or the perfect top."
    — 6E99Y-c-BjE.txt 00:36:38, 2026-05-10

    And he accepts the worse price that costs him:

    "I'd really rather get an entry down here, but it have the confirmation
     that it's actually pushing to the downside."
    — ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09

5. THE CONFIRMATION IS A REJECTION CANDLE, AN ENGULFING CANDLE, OR A STAR

    "that is going to consist of two types of candlesticks, either a rejection
     candlestick or a engulfing candlestick."
    — BcWxqfcjk9A.txt 00:01:58, 2026-04-16

    "As long as the candlestick engulfs the last two, you have a beautiful
     formation where you have a combination of a shooting star and an
     engulfing candlestick."
    — grw58BIzotU.txt 06:36:17, 2025-09-28   (the evening / morning star)

    On the gold trade he names the exact two he took:

    "What I really like is a two-hour clean two-hour bearish engulfing one
     hour clean 1 hour evening star formation."
    — ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09

6. THE STOP IS AT STRUCTURE. THE SIZE FALLS OUT OF IT

    "I put my stop loss a little bit right above this level because if we
     pretty much break above this, the trade [is invalid]"
    — grw58BIzotU.txt 09:09:09, 2025-09-28

    "this lot size here has to be directly predetermined before you enter the
     trade ... That goes based off of your stop loss and how much you're going
     to have on your stop loss."
    — grw58BIzotU.txt 01:40:34, 2025-09-28

7. 1:2 IS THE FLOOR

    "I always attempted to have every single trade setup, always be a minimum
     of a one to two risk-to-reward. This is always going to be the minimum of
     every single trade that I'm going to take."
    — grw58BIzotU.txt 08:37:45, 2025-09-28

8. NO BREAK EVEN. NO PARTIALS. NO TRAILING. THIS IS THE HARD ONE

    "I am not a break even trader. I am either going to have my trade hit my
     stop loss or have my trade hit my takerit. There's no in between."
    — ig6Z2Gbk_LE.txt 00:18:54, 2025-11-09

    "don't go to break even, you don't tra[il] your stop losses, you don't do
     any of that [expletive]"
    — 2pEtH0g0z1o.txt 00:17:14, 2024-12-19

    Q: "At what point is best to take partial profits?"
    A: "Never. You never take partials. ... I only close full position."
    — v3aPSZkVQYA.txt 00:19:14, 2025-10-26

    THERE IS NO BREAK-EVEN MECHANIC IN THIS FILE and a test asserts the word
    does not appear in the management code.

9. THE SESSION GATE — ENTRIES ONLY, AND IT IS NOT AN EXIT

    "You can only get involved in the market from 1 in the morning all the way
     up to around 10:30 in the morning."
    — grw58BIzotU.txt 01:11:50, 2025-09-28

    "I think it's been 4 years since I have taken a trade past 10:30 in the
     morning."
    — grw58BIzotU.txt 01:13:30, 2025-09-28

    "I like to enter my trades either pre-London session or during London
     session. So then the trade has good volatility ... and then once New York
     session kicks in, it just adds more fuel to the fire"
    — grw58BIzotU.txt 01:10:53, 2025-09-28

    "Sydney and Tokyo session are going to be the sessions that you are not
     going to be trading."
    — grw58BIzotU.txt 01:09:38, 2025-09-28

    He held the line on gold live rather than take a setup out of session:

    "right now we have the rejection that we've been looking for from gold,
     but there's a [expletive] problem and that is that we are out of session
     or about to be out of session. So, I'm going to be very interested in
     taking this trade come London session"
    — ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09

    NOTHING CLOSES A POSITION AT A CLOCK TIME. 10:30 stops new entries. An
    open trade runs for days and through weekends. This is the sharpest single
    difference between his method and TJR's, and getting it backwards would
    turn his method into someone else's.

10. DAY OF WEEK

    "no trades on Sundays. No trades from Thursday on ... if you do not enter
     your trade by 8 in the morning or latest 9 in the morning Thursday you
     cannot take a trade ... So your main focus is Monday through technically
     Wednesday London session."
    — LwMsai2ppKc.txt 00:34:43-00:36:34, 2026-02-22

11. HE TAKES FEW TRADES

    "the max amount of trades that you want to take in a week is anywhere from
     one to two trades."
    — LwMsai2ppKc.txt 00:04:21, 2026-02-22

    "a swing trader takes anywhere from four or five trades a month"
    — grw58BIzotU.txt 00:30:51, 2025-09-28

    IF THIS ENGINE FIRES DAILY, THE ENGINE IS WRONG, NOT HIM. The trade count
    is a correctness check, not an outcome.

12. HE DOES NOT GATE ON NEWS

    "There's no way that I am going to modify my trading approach simply
     because of a news event that actually has an impact one or two times a
     month."
    — grw58BIzotU.txt 03:01:55, 2025-09-28

    So there is no news calendar in this file, deliberately.

13. SIZING IS A SHARE OF THE ACCOUNT, FIXED FOR A MONTH AT A TIME

    "it can be anywhere from 3 to 5% of your account"
    — VzMlFZbWA0Y.txt 00:08:48, 2024-01-28  (his own money, not a prop account)

    "at the beginning of every single month I risk a percentage that I'm going
     to choose for the month so let's say I'm going to risk 3% I risk 3% for
     the whole entire month and I stick to it"
    — VzMlFZbWA0Y.txt 00:09:39, 2024-01-28

    That 3% is SHARE OF THE ACCOUNT LOST IF THE STOP IS HIT. It is not a price
    move and it is not a share of margin. Leverage is the OUTPUT.

============================================================ COSTS

Charged, never consulted. Wallace's standing rule: "if I told you dont worry
about fees then dont worry about fees." No cost figure below reaches an `if`,
a comparison, or a return, and a test reads this file's own source to prove it.

    pairs — OANDA's measured spread, one round trip, from
            `step470_spreads.json`, median during his own 01:00-10:30 window.
    gold  — BloFin's 0.06% a side (`cost_truth.FEE_PER_SIDE`, measured) twice,
            plus the XAUT-USDT spread measured at 0.0049% of the price.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd

from tjr_bot import size_position, two_candle_swings

REPO = os.path.dirname(os.path.abspath(__file__))

# His pairs, plus gold. Gold's live venue is BloFin XAUT-USDT; OANDA XAU/USD
# is the chart only.
PAIRS = ["GBP_JPY", "GBP_USD", "EUR_USD"]
GOLD = "XAU_USD"
INSTRUMENTS = PAIRS + [GOLD]

_TF_MINUTES = {"15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}

# BloFin, measured. 0.06% a side, and the XAUT-USDT spread measured tonight at
# 0.0049% of the price.
BLOFIN_FEE_PER_SIDE = 0.0006
XAUT_SPREAD_SHARE = 0.000049


def _oanda_spreads() -> dict:
    p = os.path.join(REPO, "step470_spreads.json")
    if not os.path.exists(p):
        return {}
    with open(p) as f:
        return (json.load(f) or {}).get("spread_share_of_price") or {}


def round_trip_cost_share(instrument: str) -> float:
    """What one full round trip costs, as a share of the notional.

    Gold's answer is BloFin's because gold would trade on BloFin. Everything
    else is OANDA's measured spread because that is where it would trade.
    """
    if instrument == GOLD:
        return 2.0 * BLOFIN_FEE_PER_SIDE + XAUT_SPREAD_SHARE
    return float(_oanda_spreads().get(instrument, 0.0))


# ============================================================== THE CONFIG
@dataclass
class AlexConfig:
    """Every field is either HIS with a quote in the module docstring, or
    OURS with the reason recorded in `in_his_words()`."""

    instrument: str = ""

    # ---- HIS
    trend_tfs: tuple = ("1w", "1d", "4h")   # rule 1
    direction_tf: str = "1d"                # the daily calls the direction
    agree_tf: str = "4h"                    # and the 4 hour has to agree
    area_tfs: tuple = ("1d", "4h")          # rule 1 / rule 3
    confirm_tf: str = "1h"                  # rule 5
    min_touches: int = 3                    # rule 3
    target_r: float = 2.0                   # rule 7, his stated floor
    entry_from_hour: float = 1.0            # rule 9, New York
    entry_to_hour: float = 10.5             # rule 9, 10:30 New York
    no_sunday: bool = True                  # rule 10
    last_entry_weekday: int = 3             # rule 10, Thursday (Mon=0)
    thursday_cutoff_hour: float = 9.0       # rule 10
    risk_pct_per_trade: float = 0.03        # rule 13, his own-money 3%
    account_start: float = 100_000.0

    # ---- OURS. All declared in `in_his_words()`.
    swing_rule: str = "two_candle"
    touch_tol_atr: float = 0.50     # how near a level counts as the same area
    area_lookback: int = 200        # bars of the area timeframe searched
    area_max_width_atr: float = 1.5  # a zone wider than this is not a level
    approach_bars: int = 12         # hours price may have been in the zone
    stop_buffer_atr: float = 0.25   # "a little bit right above this level"
    atr_len: int = 14
    max_hold_days: float = 30.0     # he states NO cap; this one is ours
    one_position_at_a_time: bool = True
    reentry_cooldown_bars: int = 24

    # cost, charged and never consulted
    round_trip_cost_pct: float = 0.0

    def __post_init__(self):
        if self.instrument and not self.round_trip_cost_pct:
            self.round_trip_cost_pct = round_trip_cost_share(self.instrument)


@dataclass
class DumbConfig:
    """THE SPINE — `KPVVOa6c6dY_dumb_clean.txt`, 2026-06-14, his newest.

    "one pair, one time frame, one session, and one entry signal. That is it."

    Every field is either HIS with a quote in the module docstring's SPINE
    section, or OURS with the reason in `in_his_words()`.
    """

    instrument: str = "EUR_USD"     # S1. "it would be EuroUSD"

    # ---- HIS
    tf: str = "4h"                  # S2. one timeframe, and top-down is out
    entry_hours: tuple = (1.0, 5.0)  # S3. the 01:00 and 05:00 New York closes
    signal: str = "engulfing"       # S4. one entry signal, nothing else
    min_engulfed: int = 1           # S4. "the more candlestick it engulfs,
    #                                 the better" — his own quality dial
    target_r: float = 2.0           # S6. "for the 1 to 2"
    friday_exit_at_half_stop: bool = True   # S8. his weekend rule
    no_sunday: bool = True                  # older, uncontradicted
    last_entry_weekday: int = 3             # older, uncontradicted
    thursday_cutoff_hour: float = 9.0       # older, uncontradicted
    risk_pct_per_trade: float = 0.03        # older, uncontradicted
    account_start: float = 100_000.0

    # ---- HIS, step472. Each has its quote in the docstring section named.
    pattern: str = "both"           # "engulf" | "hs" | "both"   — H1..H9
    #   He trades both setups. step470 shipped only the first one.
    signal_mode: str = "engulf"     # "engulf" | "rejection" | "either" — D1
    #   D1 offers both triggers — "either a rejection, a doji, or a bullish
    #   engulfing ... if you have both of these combined, they would be a lot
    #   more powerful" (BcWxqfcjk9A.txt, 2026-04-16) — but the JUNE 2026 spine
    #   is two months NEWER and cuts it back to the engulf alone. Newest
    #   governs, so "engulf" ships. The rejection half is fully built, gated
    #   on a level the way he shows it (see `rejection_needs_area`), and
    #   measured; it is not defaulted on merely because it exists.
    target_mode: str = "structure"     # "structure" | "filtered_2r" | "fixed_r"
    #   T1. "my take profit to the next structure point. That is it."
    #   T5. And in the SAME breath, on the SAME trade, the newest video:
    #   "my take profit to the next structure point ... But I DECIDED TO CLOSE
    #   AT MY 1 TO 2 RISK-TO-REWARD." — hb7ot1_szWI.txt 00:28:46, 2026-07-26.
    #   Two readings of one sentence. `structure` takes the RULE he states —
    #   "take profit to the next structure point. THAT IS IT" — and rides the
    #   level. `filtered_2r` takes the aside — structure decides whether the
    #   trade is worth taking, 1:2 decides where it closes. `fixed_r` is
    #   step470's flat 1:2 with no structure test at all. All three are
    #   measured; the RULE he states is the default, and it is also the one
    #   that measures best, in that order.
    rejection_needs_area: bool = True   # D3. his dojis are never in mid-air:
    #   "If you have several dojis like this set in place AT A SUPPORT LEVEL
    #   and then you get a bullish engulfing candlestick, even better."
    #   — BcWxqfcjk9A.txt 00:03:18, 2026-04-16. A rejection candle on its own,
    #   with no level under it, is not a setup he describes anywhere.
    area_lookback: int = 200           # the three-touch machinery, his rule 3
    touch_tol_atr: float = 0.50
    area_max_width_atr: float = 1.5
    min_touches: int = 3
    quality_anchor: str = "base"       # "base" | "top" — see quality_weight
    quality_max_mult: float = 2.0
    min_rr: float = 2.0             # T3. his floor for ACCEPTING a setup
    target_lookback: int = 120      # OURS: bars searched for that structure
    target_buffer_atr: float = 0.25  # T2. "a little bit below the next
    #                                  structure point"
    weekly_bias: bool = False       # W1. "those candlesticks opening and
    #   closing dictate the direction of the following week" — 2026-05-25.
    #   OFF by default because the June spine is one timeframe; measured on.
    context_tfs: tuple = ()         # C1. top-down layers, ("1w","1d").
    #   Empty is the June spine alone. Measured with the layers on.
    use_ema50: bool = True          # his one named indicator, confluence
    ema_len: int = 50               #   only — "length is 50, source is closed"
    runner_cap_r: float = 4.0       # "once you get to a one to four, you're
    #   at your home run, TRADE IS DONE." — M8wDlKjaQRk.txt 00:15:07,
    #   2026-04-05. The runner's own ceiling, in his words.
    size_by_quality: bool = True    # Q1. "you can risk more on low-risk
    #   trades" + "the more candlestick it engulfs, the better"
    quality_floor_share: float = 1.0 / 3.0   # OURS: the ladder, not the dial

    # ---- HIS, but his stated purpose is EMOTION, so it ships OFF.
    #   "Do not overtrade ... Limit yourself to two positions a week."
    #   — hb7ot1_szWI.txt 00:04:16, 2026-07-26.
    #   WALLACE'S RULING, 2026-07-27, verbatim: "tjr and alex do that because
    #   they dont want to over trade and let emotions in their way. if you see
    #   the setup, take the trade. its a demo at the end of the day." The cap
    #   is emotion management for a human; a bot has no emotions and this is a
    #   demo venue. It is built, defaulted OFF, and measured both ways so the
    #   cost of his cap is a number rather than an assumption. Nothing that
    #   defines whether a setup is VALID was loosened with it.
    human_cadence_cap: bool = False
    max_positions_per_week: int = 2

    # ---- HEAD AND SHOULDERS, all HIS unless marked
    hs_confirm_at_retest: bool = True    # H5. "we do not enter the trade on
    #   the breakout of the neckline. We have to wait for price to come back"
    hs_allow_right_shoulder: bool = False  # H6. "extremely high risk. I don't
    #   recommend it unless you are an experienced trader."
    hs_require_area_neckline: bool = True  # H4. "It's always going to be at
    #   an area of interest as well."
    hs_head_at_area: bool = True         # H4b, a SEPARATE rule from the one
    #   above and it was missing from the first build: "You want to make sure
    #   that you can get this reversal pattern on AREAS THAT IT ACTUALLY WILL
    #   HAVE A SIGNIFICANT IMPACT. You want to make sure that you're getting
    #   this head and shoulders pattern AT A RESISTANCE. If you're looking to
    #   sell, you want to make sure you can have it AT A SUPPORT. If you're
    #   looking to buy." — grw58BIzotU.txt 07:04:36, 2025-09-28. The neckline
    #   being a level is not the same claim as the HEAD being at one, and he
    #   makes both.
    hs_min_touches: int = 3              # rule 3, three touches
    hs_retest_bars: int = 18             # OURS: how long we wait for the
    #   retest before the pattern is dropped. He gives no clock.
    session_gate: bool = True            # S3 / rule 9, his entry window. It
    #   is a rule about WHEN YOU PULL THE TRIGGER ("Anything after 10 in the
    #   morning I have not taken a trade after that time" — grw58BIzotU.txt
    #   01:13:30, 2025-09-28), and a DAILY candle closes at 17:00 New York,
    #   outside it. So a daily-timeframe reading has to switch this off; it is
    #   a real departure from him and it is reported as one.
    hs_lookback: int = 60                # OURS: bars searched for the
    #   shoulders and the head behind a neckline break.
    hs_touch_tol_atr: float = 0.50       # OURS: how near a level counts as
    #   the same area. The same share of the average range the older
    #   `AlexConfig` uses, so there is one answer in this file, not two.

    # ---- OURS
    swing_rule: str = "two_candle"
    stop_buffer_atr: float = 0.25
    atr_len: int = 14
    max_hold_days: float = 30.0
    one_position_at_a_time: bool = True
    reentry_cooldown_bars: int = 2          # 4-hour bars
    require_retest: bool = False            # his illustration, not his summary
    exit_on_structure_flip: bool = False    # X1. OURS in its mechanism, his
    #   in its idea. Ships OFF because "set and forget" is his own words.
    runner: bool = False                    # X2. "leave this one run"
    runner_share: float = 0.5               # OURS: how much is left running
    control: str = "none"                   # "none" | "reversed" | "coinflip"
    control_seed: int = 470
    round_trip_cost_pct: float = 0.0

    def __post_init__(self):
        if self.instrument and not self.round_trip_cost_pct:
            self.round_trip_cost_pct = round_trip_cost_share(self.instrument)


def dumb_config_for(instrument: str, **over) -> DumbConfig:
    cfg = DumbConfig(instrument=instrument)
    for k, v in (over or {}).items():
        if not hasattr(cfg, k):
            raise AttributeError(f"DumbConfig has no field {k!r}")
        setattr(cfg, k, v)
    if not over.get("round_trip_cost_pct"):
        cfg.round_trip_cost_pct = round_trip_cost_share(instrument)
    return cfg


def config_for(instrument: str, **over) -> AlexConfig:
    cfg = AlexConfig(instrument=instrument)
    for k, v in (over or {}).items():
        if not hasattr(cfg, k):
            raise AttributeError(f"AlexConfig has no field {k!r}")
        setattr(cfg, k, v)
    if not over.get("round_trip_cost_pct"):
        cfg.round_trip_cost_pct = round_trip_cost_share(instrument)
    return cfg


# ================================================================== DATA
def cache_name(instrument: str, tf: str) -> str:
    return os.path.join(REPO, f"data_oanda_{instrument}_{tf}.parquet")


def load(instrument: str, tfs=("15m", "1h", "4h", "1d", "1w")) -> dict:
    """The cached bars. READS ONLY. `t` is the bar's START in New York wall
    clock, and the daily boundary is OANDA's 17:00 New York — which is where
    the currency day actually rolls and where his own daily bodies close."""
    return {tf: pd.read_parquet(cache_name(instrument, tf)) for tf in tfs}


def atr(d: pd.DataFrame, n: int = 14) -> np.ndarray:
    """Average true range, causal: the value at bar i uses bars <= i."""
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    pc = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return pd.Series(tr).rolling(n, min_periods=2).mean().to_numpy()


def bar_minutes(tf: str) -> int:
    return _TF_MINUTES[tf]


def closes_at(d: pd.DataFrame, tf: str) -> np.ndarray:
    """When each bar of `d` finished. A bar is invisible until it closes —
    that is rule 2, and it is also the whole of causality."""
    return (d["t"] + pd.Timedelta(minutes=_TF_MINUTES[tf])).to_numpy()


# =========================================================== TREND STATE
def trend_series(d: pd.DataFrame) -> np.ndarray:
    """+1 / -1 / 0 per bar, as of that bar's CLOSE.

    HIS RULE (2): structure only shifts on a BODY CLOSE beyond the last swing.
    A wick does nothing. The state PERSISTS until a body close the other way —
    which is what he means by "we are still bearish" through four candles that
    came close and did not close beyond.

    OURS: the swing definition itself. He draws swings constantly and never
    defines one, so this uses the project's two-candle rule, the same
    definition every other book here uses, imported rather than re-invented.
    """
    sh, sl = two_candle_swings(d)
    c = d["close"].to_numpy(float)
    n = len(d)
    out = np.zeros(n, dtype=int)
    state = 0
    mrh = mrl = np.nan
    for i in range(n):
        # the swing stamped ON this bar is known at its close, but it cannot
        # be broken by the same bar that formed it
        if state >= 0 and not np.isnan(mrl) and c[i] < mrl:
            state = -1
        elif state <= 0 and not np.isnan(mrh) and c[i] > mrh:
            state = +1
        out[i] = state
        if not np.isnan(sh[i]):
            mrh = sh[i]
        if not np.isnan(sl[i]):
            mrl = sl[i]
    return out


# ======================================================= AREAS OF INTEREST
@dataclass
class Area:
    """A price zone that has been touched at least three times.

    Stamped as of the close of one bar of the area timeframe and using no bar
    after it.
    """
    lo: float
    hi: float
    touches: int
    tf: str
    known_at: pd.Timestamp        # when this zone became knowable

    @property
    def mid(self) -> float:
        return 0.5 * (self.lo + self.hi)

    def contains(self, px: float) -> bool:
        return self.lo <= px <= self.hi

    def overlaps(self, lo: float, hi: float) -> bool:
        return not (hi < self.lo or lo > self.hi)


def _cluster(levels: np.ndarray, tol: float, max_width: float) -> list:
    """Group levels that sit within `tol` of one another.

    HIS RULE (3): three touches minimum, and highs and lows count toward the
    same area — "You can have two touches that are resistance, one touch that
    is support". So nothing here cares which side of price a level formed on.

    OURS: `tol`. He never says how near is near enough, so it is a share of
    that timeframe's own average range rather than a number of pips, which
    would mean a different thing on gold than on EUR/USD.
    """
    if len(levels) == 0:
        return []
    lv = np.sort(levels)
    groups, cur = [], [lv[0]]
    for x in lv[1:]:
        if x - cur[-1] <= tol:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)
    out = []
    for g in groups:
        if len(g) < 1:
            continue
        width = g[-1] - g[0]
        if width > max_width:
            continue
        out.append((float(g[0]), float(g[-1]), len(g)))
    return out


def areas_at(d: pd.DataFrame, i: int, cfg: AlexConfig, tf: str,
             a: np.ndarray) -> list:
    """Every area of interest knowable at the close of bar `i` of `d`.

    HIS DEFINITION, and it is the single most-repeated object in the ten-hour
    course — 272 mentions:

        "Area of interest is a support and resistance. It's a supply and
         demand zone and it's an order block."
        — grw58BIzotU.txt 05:07:57, 2025-09-28

        "an area of interest is only valid once we have a minimum of three
         touches ... Anything less than three touches, it is no longer a valid
         area of interest."
        — grw58BIzotU.txt 05:14:39 / 05:17:32

    DRAWN ON THE BODIES, NOT THE WICKS — he calls the body turns "elbows":

        "These are the elbows. THE ELBOWS ARE BASED OFF OF THE BODIES OF THE
         CANDLESTICKS. AT NO POINT ARE WE INCLUDING WICKS HERE."
        "At no point am I doing this area of interest to the wicks or am I
         making the box big enough to include the wicks. No, I'm doing this to
         the structure points, to the elbows."
        — grw58BIzotU.txt 05:19:58 / 05:20:34, 2025-09-28

    AND IT HAS TO SIT INSIDE THE CURRENT STRUCTURE:

        "YOU CAN ONLY HAVE AN AREA OF INTEREST WITHIN THE HIGHER HIGH AND THE
         HIGHER LOW. Having an area of interest below the higher low
         completely defeats the purpose of having identified if it's bullish
         or bearish ... if we go below the higher low, guess what happens? We
         are then bearish, making this NO LONGER A VALID AREA OF INTEREST."
        — grw58BIzotU.txt 05:25:22 / 05:41:51, 2025-09-28

    That last rule is also his ONLY stated invalidation: a zone dies when the
    structure it sits inside breaks, not with age and not from being tapped.
    He is explicit that a zone is NOT spent by use — "Even if this one has a
    100 touches and this one only has three, the market can have the reaction
    from both or from none" (05:43:15) — so nothing here tracks freshness.

    Uses bars 0..i and nothing after. `a` is the precomputed ATR of `d`.
    """
    if i < 5 or np.isnan(a[i]) or a[i] <= 0:
        return []
    lo_i = max(0, i - cfg.area_lookback + 1)
    sub = body_frame(d.iloc[lo_i:i + 1])        # elbows, not wicks
    sh, sl = two_candle_swings(sub)
    levels = np.concatenate([sh[~np.isnan(sh)], sl[~np.isnan(sl)]])
    # the zone must live between the most recent swing low and swing high —
    # his "only within the higher high and the higher low"
    hi_b = sh[~np.isnan(sh)]
    lo_b = sl[~np.isnan(sl)]
    if len(hi_b) and len(lo_b):
        top, bot = float(hi_b[-1]), float(lo_b[-1])
        if bot > top:
            top, bot = bot, top
        levels = levels[(levels >= bot) & (levels <= top)]
    tol = cfg.touch_tol_atr * a[i]
    out = []
    for lo, hi, n in _cluster(levels, tol, cfg.area_max_width_atr * a[i]):
        if n < cfg.min_touches:
            continue
        out.append(Area(lo=lo, hi=hi, touches=int(n), tf=tf,
                        known_at=pd.Timestamp(d["t"].iloc[i])
                        + pd.Timedelta(minutes=_TF_MINUTES[tf])))
    return out


# ==================================================== CONFIRMATION CANDLES
def confirmation(o, h, lo, c, i: int, direction: int) -> str:
    """Which of his three confirmations bar `i` is, or "" for none.

    Reads bars i, i-1 and i-2 and NOTHING after i. `direction` is +1 for a
    buy, -1 for a sell.

    engulfing  — "When something engulfs something, it means that it has eaten
                 the candlestick to the left." (MhWSZp4yS2c.txt 00:48:48,
                 2026-06-28). Body against body, and the new body has to be
                 the bigger one.
    rejection  — his doji / shooting star / hammer: a wick against the trade
                 at least twice the body, and the close on the right side.
                 ("multiple dogees or an engulfing candlestick which will be
                 my entry signal" — pD1vAUMbSjw.txt 00:30:08, 2026-02-02)
    star       — "As long as the candlestick engulfs the last two"
                 (grw58BIzotU.txt 06:36:17, 2025-09-28), with the middle
                 candle the small-bodied one.

    OURS: the arithmetic. "Twice the body", "the bigger body", and "the middle
    candle is the smaller one" are our numbers; he shows these shapes on a
    chart and never quantifies one.
    """
    if i < 2:
        return ""
    body = abs(c[i] - o[i])
    rng = h[i] - lo[i]
    if rng <= 0:
        return ""
    right_way = (c[i] > o[i]) if direction > 0 else (c[i] < o[i])

    # --- star: engulfs the last TWO, middle candle small
    if right_way:
        prev2_body = abs(c[i - 2] - o[i - 2])
        mid_body = abs(c[i - 1] - o[i - 1])
        two_lo = min(o[i - 1], c[i - 1], o[i - 2], c[i - 2])
        two_hi = max(o[i - 1], c[i - 1], o[i - 2], c[i - 2])
        if mid_body < 0.5 * prev2_body and body > 0:
            if direction > 0 and o[i] <= two_lo and c[i] >= two_hi:
                return "morning_star"
            if direction < 0 and o[i] >= two_hi and c[i] <= two_lo:
                return "evening_star"

    # --- engulfing: eats the candle to its left
    if right_way and body > abs(c[i - 1] - o[i - 1]):
        p_lo, p_hi = min(o[i - 1], c[i - 1]), max(o[i - 1], c[i - 1])
        if direction > 0 and o[i] <= p_lo and c[i] >= p_hi:
            return "bullish_engulfing"
        if direction < 0 and o[i] >= p_hi and c[i] <= p_lo:
            return "bearish_engulfing"

    # --- rejection: the wick against us is the story
    upper = h[i] - max(o[i], c[i])
    lower = min(o[i], c[i]) - lo[i]
    if direction > 0 and lower >= 2.0 * body and lower >= 0.5 * rng:
        return "rejection"
    if direction < 0 and upper >= 2.0 * body and upper >= 0.5 * rng:
        return "rejection"
    return ""


def engulfed_count(o, h, lo, c, i: int, direction: int) -> int:
    """HOW MANY CANDLES TO THE LEFT THIS ONE ATE. 0 means it is not one.

    S4, and the grading is his, not ours:

        "When it's bigger, the next candlestick in order for you to enter the
         position needs to engulf the last candlestick. THE MORE CANDLESTICK
         IT ENGULFS, THE BETTER."
        "This looks like a bullish candle, but it didn't really engulf
         anything other than this small candle ... this is NOT a bullish
         engulfing candlestick."
        "one candlestick that has eaten the last 10 candlesticks"

    Reads bars <= i and nothing after. Counting is body-against-body, walking
    left while the new body still covers each earlier body, which is exactly
    what he does out loud on the chart ("engulfed the last 1 2 3 four
    candlesticks").
    """
    if i < 1:
        return 0
    right_way = (c[i] > o[i]) if direction > 0 else (c[i] < o[i])
    if not right_way:
        return 0
    body_lo, body_hi = min(o[i], c[i]), max(o[i], c[i])
    if body_hi <= body_lo:
        return 0
    n = 0
    for k in range(i - 1, -1, -1):
        k_lo, k_hi = min(o[k], c[k]), max(o[k], c[k])
        if body_lo <= k_lo and body_hi >= k_hi:
            n += 1
        else:
            break
    return n


def body_frame(d: pd.DataFrame) -> pd.DataFrame:
    """The same bars with the BODY extremes standing in for high and low.

    H2, and he could not be blunter about it:

        "that is done to the BODIES of the candlestick. WE ARE NOT INCLUDING
         THE WICKS AT NO POINT when identifying a head and shoulders."
        — grw58BIzotU.txt 06:51:10, 2025-09-28

    Structure — swings, the neckline, the shift — is read off this frame. The
    STOP is read off the real wicks (H7), which is his rule too and the reason
    the two frames are kept apart instead of one replacing the other.
    """
    out = d.copy()
    o = d["open"].to_numpy(float)
    c = d["close"].to_numpy(float)
    out["high"] = np.maximum(o, c)
    out["low"] = np.minimum(o, c)
    return out


def is_rejection_candle(o, h, lo, c, i: int, direction: int) -> bool:
    """D1's other half: the rejection / doji candle, on its own.

        "the two types of confirmation we look for is EITHER A REJECTION, A
         DOJI, OR A BULLISH ENGULFING or a bearish engulfing."
        — BcWxqfcjk9A.txt 00:03:18, 2026-04-16

    OURS: the arithmetic — the wick against the trade is at least twice the
    body and at least half the candle's range. Identical to the `rejection`
    branch of `confirmation()` on purpose; a second definition of a rejection
    candle in one file would be a bug waiting.
    """
    if i < 0:
        return False
    body = abs(c[i] - o[i])
    rng = h[i] - lo[i]
    if rng <= 0:
        return False
    upper = h[i] - max(o[i], c[i])
    lower = min(o[i], c[i]) - lo[i]
    if direction > 0:
        return lower >= 2.0 * body and lower >= 0.5 * rng
    return upper >= 2.0 * body and upper >= 0.5 * rng


def doji_stack(o, h, lo, c, i: int) -> int:
    """How many small-bodied candles sit immediately to the left of bar `i`.

        "THE MORE DOJIS THAT YOU WOULD HAVE, THE MORE POWERFUL. If you have
         several dojis like this set in place at a support level and then you
         get a bullish engulfing candlestick, even better."
        — BcWxqfcjk9A.txt 00:03:18, 2026-04-16

    Reads bars < i only. OURS: "small-bodied" is a body under a third of the
    candle's range. He draws dojis and never measures one.
    """
    n = 0
    for k in range(i - 1, -1, -1):
        rng = h[k] - lo[k]
        if rng <= 0:
            break
        if abs(c[k] - o[k]) <= 0.35 * rng:
            n += 1
        else:
            break
    return n


def ema(d: pd.DataFrame, n: int = 50) -> np.ndarray:
    """HIS ONE INDICATOR, with his own settings.

        "I currently have a 50 EMA. So, the length is 50, the source is
         closed, offset is zero ... This 50 EMA is very significant to the
         trade because it is USED AS A DYNAMIC LEVEL OF SUPPORT AND
         RESISTANCE."
        — A8ncoQCPjF8.txt 00:06:49 / 00:08:18, 2025-11-02

    And its rank in his own method, which is why it can only ever move the
    SIZE of a trade here and never whether one is taken:

        "My indicators are simply an ADDED CONFLUENCE to the trade that I'm
         going to be taking. IT DOES NOT DETERMINE MY WHOLE ENTIRE TRADE."
        — A8ncoQCPjF8.txt 00:01:18, 2025-11-02

    Causal by construction. (His other named indicator, "no gap candles", is a
    drawing preference that fills weekend gaps on the chart; there is nothing
    to implement and OANDA's tape has no gaps to fill.)
    """
    return d["close"].ewm(span=n, adjust=False).mean().to_numpy()


# ====================================================== QUALITY -> SIZE
def quality_points(n_eaten: int, rejection: bool, dojis: int,
                   context_agrees: bool | None,
                   ema_ok: bool | None = None) -> tuple:
    """His confluence count, and how many points were available to score.

    Every input is his, each with its quote in the docstring (S4, D1, C1/W1).
    The MAPPING from points to a position size is OURS and is declared in
    `in_his_words()`. Nothing here changes whether a setup is VALID — that
    floor is still his one engulfed candle.
    """
    pts = 0
    if n_eaten >= 2:
        pts += 1                       # S4 "the more candlestick it engulfs"
    if n_eaten >= 3:
        pts += 1
    if n_eaten >= 1 and rejection:
        pts += 1                       # D1 "both of these combined"
    if dojis >= 2:
        pts += 1                       # D1 "the more dojis ... the more"
    avail = 4
    if context_agrees is not None:
        avail += 1
        if context_agrees:
            pts += 1                   # C1 / W1, and Q1's "risk more"
    if ema_ok is not None:
        avail += 1
        if ema_ok:
            pts += 1                   # his 50 EMA, confluence only
    return pts, avail


def quality_weight(pts: int, avail: int, floor_share: float,
                   anchor: str = "base", max_mult: float = 2.0) -> float:
    """The share of a normal position a setup of this quality gets.

    OURS, entirely — he gives a dial and never a ladder. But the ANCHOR is not
    a free choice, and the first version of it was measurably wrong: his
    sentence is "YOU CAN RISK MORE ON LOW-RISK TRADES"
    (LwMsai2ppKc.txt 00:22:34, 2026-02-22), which scales the good setups UP
    from a normal position. Anchoring at the top instead — full size only at
    perfect confluence — silently shrinks EVERY ordinary trade, which is a
    different instruction and not one he gives.

        "base" — a plain valid setup gets the configured risk, and confluence
                 scales it up to `max_mult` times that. HIS SENTENCE.
        "top"  — full size at perfect confluence, `floor_share` at none.
                 What step472 tried first, kept so the difference is a number.
    """
    if avail <= 0:
        return 1.0
    frac = max(0, min(pts, avail)) / avail
    if anchor == "top":
        f = max(0.0, min(1.0, float(floor_share)))
        return f + (1.0 - f) * frac
    return 1.0 + (float(max_mult) - 1.0) * frac


# ===================================================== STRUCTURE TARGETS
def next_structure_target(sh, sl, i: int, entry: float, stop: float,
                          direction: int, atr_i: float, cfg) -> float | None:
    """T. THE NEAREST STRUCTURE POINT THAT STILL PAYS HIS MINIMUM.

        "my take profit to the NEXT STRUCTURE POINT. That is it."
        — hb7ot1_szWI.txt 00:28:46, 2026-07-26

        "I always place my take profit where I can have a reaction from that
         area. THE CLOSER THE BETTER and always at a minimum of a 1:2."
        — DsPLtzjTONI.txt 00:10:50, 2026-06-22

    So the candidates are the swing levels already on the chart in the trade's
    direction, taken NEAREST FIRST, and the first one that pays `min_rr` or
    better is the target. If none of them pays it, this returns None and the
    SETUP IS NOT TAKEN — "Do not take a trade that is not worth the risk."
    (hb7ot1_szWI.txt 00:33:38, 2026-07-26).

    T2 puts the exit a little short of the level: "I simply place my takeprofit
    A LITTLE BIT BELOW THE NEXT STRUCTURE POINT" (E3lYZsy8nYE.txt 00:24:25,
    2025-06-09). That shortfall is `target_buffer_atr` of the average range.

    Reads swings at index <= i and nothing after.
    """
    dist = abs(entry - stop)
    if dist <= 0:
        return None
    j0 = max(0, i - int(cfg.target_lookback) + 1)
    buf = float(cfg.target_buffer_atr) * float(atr_i)
    src = sl if direction < 0 else sh
    lv = src[j0:i + 1]
    lv = lv[~np.isnan(lv)]
    if not len(lv):
        return None
    if direction < 0:
        cand = np.sort(lv[lv < entry])[::-1]      # nearest below first
        for level in cand:
            tgt = float(level) + buf              # stop a little short of it
            if tgt >= entry:
                continue
            if (entry - tgt) / dist >= cfg.min_rr:
                return tgt
    else:
        cand = np.sort(lv[lv > entry])            # nearest above first
        for level in cand:
            tgt = float(level) - buf
            if tgt <= entry:
                continue
            if (tgt - entry) / dist >= cfg.min_rr:
                return tgt
    return None


def target_for(cfg, sh, sl, i, entry, stop, direction, atr_i):
    """T. WHERE THE TRADE IS CLOSED, in his three readings.

    `filtered_2r` is the default and it is the newest video, in one sentence
    describing one trade: "my take profit to the NEXT STRUCTURE POINT ... But
    I DECIDED TO CLOSE AT MY 1 TO 2 RISK-TO-REWARD" (hb7ot1_szWI.txt 00:28:46,
    2026-07-26). The structure point has to be there and has to pay his
    minimum, or there is no trade; the exit itself is the 1:2.
    """
    dist = abs(entry - stop)
    flat = entry + direction * cfg.target_r * dist
    if cfg.target_mode == "fixed_r":
        return flat
    lvl = next_structure_target(sh, sl, i, entry, stop, direction, atr_i, cfg)
    if lvl is None:
        return None                     # "Do not take a trade that is not
        #                                  worth the risk."
    return flat if cfg.target_mode == "filtered_2r" else lvl


# ================================================ HIGHER-TIMEFRAME LAYERS
def weekly_bias_table(frames: dict) -> pd.DataFrame:
    """W1. The direction each CLOSED weekly candle hands to the week after it.

        "those candlesticks OPENING AND CLOSING DICTATE THE DIRECTION OF THE
         FOLLOWING WEEK."
        — 1dL3xmxA2e0.txt 00:06:12, 2026-05-25

    Stamped at the weekly candle's own close, so a week's bias is only ever
    read by the week that follows it.
    """
    w = frames["1w"]
    o = w["open"].to_numpy(float)
    c = w["close"].to_numpy(float)
    d = np.where(c > o, 1, np.where(c < o, -1, 0))
    return pd.DataFrame({
        "known_at": pd.to_datetime(w["t"]) + pd.Timedelta(minutes=_TF_MINUTES["1w"]),
        "dir": d})


def _state_at(states: np.ndarray, closes: np.ndarray, ts) -> int:
    """The last state of some timeframe that had already CLOSED by `ts`."""
    j = int(np.searchsorted(closes, np.datetime64(pd.Timestamp(ts)), "right")) - 1
    return int(states[j]) if j >= 0 else 0


def context_layers(frames: dict, cfg: DumbConfig) -> dict:
    """C1. Weekly and daily state, each snapshotted at its OWN bar close."""
    out = {}
    for tf in (cfg.context_tfs or ()):
        d = frames[tf]
        out[tf] = (trend_series(d), closes_at(d, tf))
    return out


def find_setups_dumb(inst: str, frames: dict, cfg: DumbConfig,
                     start, end) -> list:
    """THE SPINE. One pair, one timeframe, one session, one entry signal.

    His own one-sentence summary of the whole thing:

        "You're just watching the direction of the market. You're following
         that direction of the markets and you're waiting for your engulfing
         candlestick in the direction that you have identified already. It
         quite really is that simple."
        — KPVVOa6c6dY_dumb_clean.txt, 2026-06-14

    So: 4-hour market structure gives the side, a 4-hour engulfing candle in
    that side is the trigger, and the bar has to close in his session. There is
    no area of interest here, no three-touch rule, no daily and no weekly —
    "Trading like an idiot, you don't take any of that into account."

    Everything is stamped at the CLOSE of the engulfing candle and uses no bar
    after it.
    """
    d = frames[cfg.tf]
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    st = trend_series(d)
    a = atr(d, cfg.atr_len)
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    t = d["t"].to_numpy()
    step = pd.Timedelta(minutes=_TF_MINUTES[cfg.tf])

    i0 = int(np.searchsorted(t, np.datetime64(start), "left"))
    i1 = int(np.searchsorted(t, np.datetime64(end), "right"))
    sh, sl = two_candle_swings(d)
    bsh, bsl = two_candle_swings(body_frame(d))   # structure = bodies (H2)
    wk = weekly_bias_table(frames) if cfg.weekly_bias else None
    wk_at = wk["known_at"].to_numpy() if wk is not None else None
    ctx = context_layers(frames, cfg)
    em = ema(d, cfg.ema_len) if cfg.use_ema50 else None
    out = []
    for i in range(max(i0, cfg.atr_len + 3), min(i1, len(d))):
        decided = pd.Timestamp(t[i]) + step
        if cfg.session_gate and not dumb_in_window(decided, cfg):
            continue
        if np.isnan(a[i]) or a[i] <= 0:
            continue
        direction = int(st[i])
        if direction == 0:
            continue

        # ---- W1. the closed weekly candle dictates the week that follows
        if wk is not None:
            j = int(np.searchsorted(wk_at, np.datetime64(decided), "right")) - 1
            if j < 0 or int(wk["dir"].iloc[j]) != direction:
                continue

        # ---- C1. the top-down layers, when they are switched on
        agrees = None
        if ctx:
            states = [_state_at(s, cl, decided) for s, cl in ctx.values()]
            if any(s == -direction for s in states):
                continue                       # a layer is against the trade
            agrees = all(s == direction for s in states)

        # ---- S4 + D1. the trigger: engulf, rejection, or both
        n_eaten = engulfed_count(o, h, lo, c, i, direction)
        has_engulf = n_eaten >= cfg.min_engulfed
        rej = is_rejection_candle(o, h, lo, c, i, direction)
        if cfg.signal_mode == "engulf":
            fired = has_engulf
        elif cfg.signal_mode == "rejection":
            fired = rej
        else:
            fired = has_engulf or rej
        if not fired:
            continue
        kind = ("engulf+rejection" if (has_engulf and rej)
                else ("engulfing" if has_engulf else "rejection"))
        # D3. A REJECTION WITH NOTHING UNDER IT IS NOT A SETUP HE DESCRIBES.
        # Every doji he shows is "set in place AT A SUPPORT LEVEL"
        # (BcWxqfcjk9A.txt 00:03:18, 2026-04-16), and the engulfing candle is
        # the one he says stands on its own. So a rejection-only trigger has
        # to land in an area of interest — his own three-touch, body-drawn
        # zone. This is a quality bar, not a loosening: it REFUSES trades.
        if (not has_engulf) and cfg.rejection_needs_area:
            px = float(c[i])
            if not any(ar.contains(px) or ar.overlaps(float(lo[i]), float(h[i]))
                       for ar in areas_at(d, i, cfg, cfg.tf, a)):
                continue
        dojis = doji_stack(o, h, lo, c, i)

        buf = cfg.stop_buffer_atr * a[i]
        entry = float(c[i])
        # S6. the stop sits beyond the structure the entry candle came out of
        # — the candle's own extreme, or the last swing that way, whichever is
        # further. Both are known at this candle's close.
        back = max(0, i - max(n_eaten, 1) - 1)
        if direction < 0:
            recent = sh[back:i + 1]
            recent = recent[~np.isnan(recent)]
            struct = max(float(h[back:i + 1].max()),
                         float(recent.max()) if len(recent) else -np.inf)
            stop = struct + buf
            if stop <= entry:
                continue
        else:
            recent = sl[back:i + 1]
            recent = recent[~np.isnan(recent)]
            struct = min(float(lo[back:i + 1].min()),
                         float(recent.min()) if len(recent) else np.inf)
            stop = struct - buf
            if stop >= entry:
                continue

        # ---- T. the target
        target = target_for(cfg, bsh, bsl, i, entry, stop, direction, a[i])
        if target is None:
            continue                       # no level pays his 1:2 — no trade

        ema_ok = None if em is None else bool((c[i] - em[i]) * direction > 0)
        pts, avail = quality_points(n_eaten, rej, dojis, agrees, ema_ok)
        out.append(Setup(
            instrument=inst, session=session_of(decided), direction=direction,
            signal_t=pd.Timestamp(t[i]), signal_i=i, decided_t=decided,
            entry=entry, stop=float(stop), target=float(target),
            area_lo=float(min(o[i], c[i])), area_hi=float(max(o[i], c[i])),
            area_tf=cfg.tf, touches=n_eaten, confirm=kind,
            trend_w=0, trend_d=0, trend_4h=direction,
            pattern="engulf", signal_kind=kind, engulfed=n_eaten,
            dojis=dojis, quality_pts=pts, quality_avail=avail,
            quality=quality_weight(pts, avail, cfg.quality_floor_share,
                                   cfg.quality_anchor, cfg.quality_max_mult)
            if cfg.size_by_quality else 1.0))
    return out


# ================================================ THE HEAD AND SHOULDERS
def find_setups_hs(inst: str, frames: dict, cfg: DumbConfig,
                   start, end) -> list:
    """H. HIS GO-TO PATTERN, BUILT FROM HIS OWN DESCRIPTION OF IT.

    The whole detector is four of his sentences in order:

      1. structure is drawn on BODIES, never wicks                  (H2)
      2. the neckline IS the higher low whose break shifted the
         structure — "where the higher low and the shift has been
         created ... This is the neckline"                          (H3)
      3. nothing is a head and shoulders until that line breaks     (H3)
      4. "we do not enter the trade on the breakout of the neckline.
         We have to wait for price to come back into this area and
         then retest", and then a closed candle confirms it         (H5)

    Then the stop goes above the WICK of the right shoulder (H7) and the
    target is the next structure point (T).

    NO LOOKAHEAD ANYWHERE. The neckline is a level that already existed and
    was already broken; the shoulders are counted only from bars left of the
    break; the retest and the confirming candle are later bars read one at a
    time; and every price used is from a bar that has closed.
    """
    d = frames[cfg.tf]
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    bf = body_frame(d)
    bsh, bsl = two_candle_swings(bf)          # H2 — the pattern's structure
    a = atr(d, cfg.atr_len)
    o = d["open"].to_numpy(float)
    h = d["high"].to_numpy(float)
    lo = d["low"].to_numpy(float)
    c = d["close"].to_numpy(float)
    t = d["t"].to_numpy()
    n = len(d)
    step = pd.Timedelta(minutes=_TF_MINUTES[cfg.tf])
    wk = weekly_bias_table(frames) if cfg.weekly_bias else None
    wk_at = wk["known_at"].to_numpy() if wk is not None else None
    ctx = context_layers(frames, cfg)
    em = ema(d, cfg.ema_len) if cfg.use_ema50 else None

    i_end = int(np.searchsorted(t, np.datetime64(end), "right"))
    i_beg = int(np.searchsorted(t, np.datetime64(start), "left"))

    # ---- pass one: every neckline break, in time order, causally
    state, mrh, mrl = 0, np.nan, np.nan
    breaks = []
    for i in range(n):
        if state >= 0 and not np.isnan(mrl) and c[i] < mrl:
            state = -1
            breaks.append((i, -1, float(mrl)))
        elif state <= 0 and not np.isnan(mrh) and c[i] > mrh:
            state = +1
            breaks.append((i, +1, float(mrh)))
        if not np.isnan(bsh[i]):
            mrh = bsh[i]
        if not np.isnan(bsl[i]):
            mrl = bsl[i]

    out = []
    for i_brk, direction, neck in breaks:
        if i_brk < cfg.atr_len + 3 or i_brk >= i_end:
            continue
        if np.isnan(a[i_brk]) or a[i_brk] <= 0:
            continue
        tol = cfg.hs_touch_tol_atr * a[i_brk]

        # ---- the shoulders and the head, from bars LEFT of the break only
        j0 = max(0, i_brk - cfg.hs_lookback)
        peaks = bsh[j0:i_brk] if direction < 0 else bsl[j0:i_brk]
        peaks = peaks[~np.isnan(peaks)]
        peaks = peaks[peaks > neck] if direction < 0 else peaks[peaks < neck]
        if len(peaks) < 2:            # a left shoulder and a head, minimum
            continue
        head = float(peaks.max()) if direction < 0 else float(peaks.min())

        # ---- H4. the neckline has to be an area of interest
        lv = np.concatenate([bsh[j0:i_brk], bsl[j0:i_brk]])
        lv = lv[~np.isnan(lv)]
        if cfg.hs_require_area_neckline:
            if int((np.abs(lv - neck) <= tol).sum()) < cfg.hs_min_touches:
                continue
        # ---- H4b. and the HEAD has to sit at a level worth reversing from.
        # "You want to make sure that you're getting this head and shoulders
        # pattern AT A RESISTANCE ... at a support if you're looking to buy."
        if cfg.hs_head_at_area:
            if int((np.abs(lv - head) <= tol).sum()) < cfg.hs_min_touches:
                continue

        # ---- H5. wait for the retest, then for a closed candle on it
        touched = not cfg.hs_confirm_at_retest
        for j in range(i_brk + 1, min(i_brk + 1 + cfg.hs_retest_bars, n)):
            # the pattern dies if structure climbs back past the head
            if (direction < 0 and c[j] > head) or (direction > 0 and c[j] < head):
                break
            back_in = (h[j] >= neck - tol) if direction < 0 \
                else (lo[j] <= neck + tol)
            if not touched:
                if not back_in:
                    continue
                touched = True
                # the touching bar may itself be the confirming candle —
                # "once it retests, then you look for those candlestick
                # formations here" (H5) — so it is not skipped.
            decided = pd.Timestamp(t[j]) + step
            if decided < start or decided > end:
                continue
            if cfg.session_gate and not dumb_in_window(decided, cfg):
                continue
            if np.isnan(a[j]) or a[j] <= 0:
                continue

            n_eaten = engulfed_count(o, h, lo, c, j, direction)
            has_engulf = n_eaten >= cfg.min_engulfed
            rej = is_rejection_candle(o, h, lo, c, j, direction)
            if cfg.hs_allow_right_shoulder:
                fired = True                       # H6, and he says don't
            elif cfg.signal_mode == "engulf":
                fired = has_engulf
            elif cfg.signal_mode == "rejection":
                fired = rej
            else:
                fired = has_engulf or rej
            if not fired:
                continue

            # ---- W1 / C1, same gates as the spine
            if wk is not None:
                k = int(np.searchsorted(wk_at, np.datetime64(decided),
                                        "right")) - 1
                if k < 0 or int(wk["dir"].iloc[k]) != direction:
                    break
            agrees = None
            if ctx:
                states = [_state_at(s, cl, decided) for s, cl in ctx.values()]
                if any(s == -direction for s in states):
                    break
                agrees = all(s == direction for s in states)

            # H5 again, and it is a real filter: the entry is the RETEST OF
            # THE NECKLINE, so the confirming candle has to close AT that line
            # or through it, not fifty pips back inside the old range. Price
            # that has recovered far past the neckline is not retesting it.
            if direction < 0 and c[j] > neck + tol:
                continue
            if direction > 0 and c[j] < neck - tol:
                continue

            # ---- H7. above the WICK of the right shoulder
            buf = cfg.stop_buffer_atr * a[j]
            entry = float(c[j])
            if direction < 0:
                stop = float(h[i_brk:j + 1].max()) + buf
                if stop <= entry:
                    continue
            else:
                stop = float(lo[i_brk:j + 1].min()) - buf
                if stop >= entry:
                    continue

            target = target_for(cfg, bsh, bsl, j, entry, stop, direction, a[j])
            if target is None:
                continue

            dojis = doji_stack(o, h, lo, c, j)
            ema_ok = None if em is None else bool((c[j] - em[j]) * direction > 0)
            pts, avail = quality_points(n_eaten, rej, dojis, agrees, ema_ok)
            kind = ("engulf+rejection" if (has_engulf and rej)
                    else ("engulfing" if has_engulf
                          else ("rejection" if rej else "area_touch")))
            out.append(Setup(
                instrument=inst, session=session_of(decided),
                direction=direction, signal_t=pd.Timestamp(t[j]), signal_i=j,
                decided_t=decided, entry=entry, stop=float(stop),
                target=float(target),
                area_lo=float(neck - tol), area_hi=float(neck + tol),
                area_tf=cfg.tf, touches=n_eaten, confirm=kind,
                trend_w=0, trend_d=0, trend_4h=direction,
                pattern="hs", signal_kind=kind, engulfed=n_eaten,
                dojis=dojis, quality_pts=pts, quality_avail=avail,
                quality=quality_weight(pts, avail, cfg.quality_floor_share,
                                       cfg.quality_anchor, cfg.quality_max_mult)
                if cfg.size_by_quality else 1.0,
                neckline=float(neck), head=float(head),
                break_t=pd.Timestamp(t[i_brk]) + step))
            break          # one trade per pattern

    # Two patterns whose retests overlap can land on the SAME candle. That is
    # one trade, not two, and the one he would be looking at is the one whose
    # neckline broke most recently — the older pattern has already been and
    # gone. Keeping both would also make the answer depend on which was found
    # first, which is exactly the kind of thing the truncation test catches.
    best: dict = {}
    for s in out:
        cur = best.get(s.decided_t)
        if cur is None or s.break_t > cur.break_t:
            best[s.decided_t] = s
    out = sorted(best.values(), key=lambda s: s.decided_t)
    return out


def apply_control(setups: list, cfg) -> list:
    """THE CONTROL. Same entry times, same stop distances, DIRECTION REPLACED.

    step471 made this the standard and it is carried here unchanged: a pattern
    whose FADE beats it is noise, whatever its net dollars say. `reversed`
    takes the exact opposite of every call; `coinflip` takes a fixed-seed coin.
    The entry price, the moment, the distance to the stop and the reward
    multiple are all held identical — only the side changes.
    """
    mode = getattr(cfg, "control", "none")
    if mode in ("none", "", None):
        return setups
    rng = np.random.default_rng(int(getattr(cfg, "control_seed", 470)))
    out = []
    for s in setups:
        dist = abs(s.entry - s.stop)
        rr = abs(s.target - s.entry) / dist if dist > 0 else 0.0
        if mode == "reversed":
            nd = -s.direction
        elif mode == "coinflip":
            nd = 1 if rng.random() < 0.5 else -1
        else:
            raise ValueError(f"unknown control {mode!r}")
        s2 = replace(s, direction=nd,
                     stop=s.entry + dist * (1 if nd < 0 else -1),
                     target=s.entry - dist * rr * (1 if nd < 0 else -1),
                     trend_4h=nd)
        out.append(s2)
    return out


def dumb_in_window(ts, cfg: DumbConfig) -> bool:
    """S3. "one or two hours before London session ... like 1 2 in the morning
    my time zone EST", held through London.

    On the venue's 17:00-anchored 4-hour grid this admits the 01:00 and 05:00
    New York closes and nothing else. The day-of-week gate is the older rule,
    which the spine does not contradict.
    """
    t = pd.Timestamp(ts)
    hh = t.hour + t.minute / 60.0
    if not (cfg.entry_hours[0] <= hh <= cfg.entry_hours[1]):
        return False
    wd = t.weekday()
    if cfg.no_sunday and wd == 6:
        return False
    if wd > cfg.last_entry_weekday:
        return False
    if wd == cfg.last_entry_weekday and hh > cfg.thursday_cutoff_hour:
        return False
    return True


# ================================================================ SESSIONS
def session_of(ts) -> str:
    """His two tradeable sessions, by his own hours (rule 9). New York clock.

    01:00-06:00 is pre-London and London. 06:00-10:30 is where New York takes
    over and he stops at 10:30. Sydney and Tokyo are not sessions he trades.
    """
    t = pd.Timestamp(ts)
    hh = t.hour + t.minute / 60.0
    if 1.0 <= hh < 6.0:
        return "london"
    if 6.0 <= hh <= 10.5:
        return "new_york"
    return ""


def in_entry_window(ts, cfg: AlexConfig) -> bool:
    """HIS RULE 9 AND 10, TOGETHER, ON ENTRIES ONLY.

    This function is never consulted about an exit and there is no exit that
    consults a clock. A trade entered under this gate runs for days.
    """
    t = pd.Timestamp(ts)
    hh = t.hour + t.minute / 60.0
    if not (cfg.entry_from_hour <= hh <= cfg.entry_to_hour):
        return False
    wd = t.weekday()                    # Mon=0 .. Sun=6
    if cfg.no_sunday and wd == 6:
        return False
    if wd > cfg.last_entry_weekday:     # Friday, Saturday
        return False
    if wd == cfg.last_entry_weekday and hh > cfg.thursday_cutoff_hour:
        return False
    return True


# ================================================================== SETUP
@dataclass
class Setup:
    instrument: str
    session: str
    direction: int
    signal_t: pd.Timestamp      # START of the confirmation candle
    signal_i: int               # its index on the 1h frame
    decided_t: pd.Timestamp     # when that candle CLOSED — the decision moment
    entry: float
    stop: float
    target: float
    area_lo: float
    area_hi: float
    area_tf: str
    touches: int
    confirm: str
    trend_w: int
    trend_d: int
    trend_4h: int
    # ---- step472. Which of his two setups this is, how it triggered, and
    # how much confluence it carried into the sizing function.
    pattern: str = "engulf"
    signal_kind: str = ""
    engulfed: int = 0
    dojis: int = 0
    quality_pts: int = 0
    quality_avail: int = 0
    quality: float = 1.0
    neckline: float = float("nan")
    head: float = float("nan")
    break_t: pd.Timestamp | None = None   # when the neckline actually broke


@dataclass
class Trade:
    instrument: str
    session: str
    direction: int
    signal_t: pd.Timestamp
    entry_t: pd.Timestamp
    entry: float
    stop: float
    target: float
    area_lo: float
    area_hi: float
    area_tf: str
    touches: int
    confirm: str
    units: float = 0.0
    notional: float = 0.0
    leverage: float = 0.0
    risk_dollars: float = 0.0
    stop_share_of_price: float = 0.0
    usd_per_quote: float = 1.0
    exit_t: pd.Timestamp | None = None
    exit: float | None = None
    outcome: str = ""
    pnl: float = 0.0
    cost: float = 0.0
    r_multiple: float = 0.0
    hours_held: float = 0.0
    same_bar_resolved: bool = False
    # ---- step472
    pattern: str = "engulf"
    signal_kind: str = ""
    engulfed: int = 0
    dojis: int = 0
    quality: float = 1.0
    quality_pts: int = 0
    quality_avail: int = 0
    runner_share: float = 0.0
    target_t: pd.Timestamp | None = None


# ============================================================ THE SEARCH
def find_setups_topdown(inst: str, frames: dict, cfg: AlexConfig,
                        start, end) -> list:
    """Every setup between `start` and `end`, each stamped at the close of the
    1-hour candle that confirmed it and using NO candle after it.

    THE ORDER IS HIS ORDER (rule 1 then 3 then 4 then 5):
        direction off the daily, with the 4 hour agreeing
     -> an area of interest with three touches, on the daily or the 4 hour
     -> price has gone INTO that area
     -> a 1-hour rejection, engulfing or star pushing back OUT of it
     -> and only then, is it inside his hours
    """
    h1 = frames[cfg.confirm_tf]
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    # -------- higher-timeframe state, each snapshotted at ITS OWN bar close
    trends, tcloses = {}, {}
    for tf in cfg.trend_tfs:
        d = frames[tf]
        trends[tf] = trend_series(d)
        tcloses[tf] = closes_at(d, tf)

    area_snaps, area_closes, area_atr = {}, {}, {}
    for tf in cfg.area_tfs:
        d = frames[tf]
        area_atr[tf] = atr(d, cfg.atr_len)
        area_closes[tf] = closes_at(d, tf)

    h1_t = h1["t"].to_numpy()
    h1_close_t = closes_at(h1, cfg.confirm_tf)
    o = h1["open"].to_numpy(float)
    h = h1["high"].to_numpy(float)
    lo = h1["low"].to_numpy(float)
    c = h1["close"].to_numpy(float)
    a1 = atr(h1, cfg.atr_len)

    i0 = int(np.searchsorted(h1_t, np.datetime64(start), "left"))
    i1 = int(np.searchsorted(h1_t, np.datetime64(end), "right"))
    out = []
    area_cache: dict = {}

    for i in range(max(i0, cfg.atr_len + 3), min(i1, len(h1))):
        decided = pd.Timestamp(h1_close_t[i])
        # HIS HOURS. Checked on the moment the decision is made, which is the
        # close of the confirmation candle.
        if not in_entry_window(decided, cfg):
            continue
        if np.isnan(a1[i]) or a1[i] <= 0:
            continue

        # ---- direction: the daily calls it, the 4 hour has to agree
        st = {}
        for tf in cfg.trend_tfs:
            j = int(np.searchsorted(tcloses[tf],
                                    np.datetime64(decided), "right")) - 1
            st[tf] = int(trends[tf][j]) if j >= 0 else 0
        direction = st[cfg.direction_tf]
        if direction == 0 or st[cfg.agree_tf] != direction:
            continue

        # ---- an area of interest, three touches, on the daily or the 4 hour
        picked = None
        for tf in cfg.area_tfs:
            j = int(np.searchsorted(area_closes[tf],
                                    np.datetime64(decided), "right")) - 1
            if j < 0:
                continue
            key = (tf, j)
            if key not in area_cache:
                area_cache[key] = areas_at(frames[tf], j, cfg, tf,
                                           area_atr[tf])
            for ar in area_cache[key]:
                # in a downtrend we sell resistance ABOVE us; in an uptrend we
                # buy support BELOW us. He is explicit that the area has to be
                # the thing price is turning away from.
                if direction < 0 and ar.hi < c[i]:
                    continue
                if direction > 0 and ar.lo > c[i]:
                    continue
                # price has actually gone INTO it in the last few hours
                k0 = max(0, i - cfg.approach_bars + 1)
                if not ar.overlaps(float(lo[k0:i + 1].min()),
                                   float(h[k0:i + 1].max())):
                    continue
                # and the daily zone wins over the 4 hour when both are there
                if picked is None or ar.touches > picked.touches:
                    picked = ar
            if picked is not None:
                break
        if picked is None:
            continue

        # ---- the confirmation candle
        kind = confirmation(o, h, lo, c, i, direction)
        if not kind:
            continue

        # ---- the stop, at structure, "a little bit right above this level"
        buf = cfg.stop_buffer_atr * a1[i]
        if direction < 0:
            struct = max(picked.hi, float(h[max(0, i - 2):i + 1].max()))
            stop = struct + buf
            entry = float(c[i])
            if stop <= entry:
                continue
            target = entry - cfg.target_r * (stop - entry)
        else:
            struct = min(picked.lo, float(lo[max(0, i - 2):i + 1].min()))
            stop = struct - buf
            entry = float(c[i])
            if stop >= entry:
                continue
            target = entry + cfg.target_r * (entry - stop)

        out.append(Setup(
            instrument=inst, session=session_of(decided), direction=direction,
            signal_t=pd.Timestamp(h1_t[i]), signal_i=i, decided_t=decided,
            entry=entry, stop=float(stop), target=float(target),
            area_lo=picked.lo, area_hi=picked.hi, area_tf=picked.tf,
            touches=picked.touches, confirm=kind,
            trend_w=st.get("1w", 0), trend_d=st.get("1d", 0),
            trend_4h=st.get("4h", 0)))
    return out


# =========================================================== MANAGEMENT
def _is_last_bar_of_the_week(ts) -> bool:
    """The final 15-minute bar before the currency week closes at 17:00 New
    York on Friday. This is the one and only wall-clock read in the exit path
    and it exists because S8 is his rule."""
    t = pd.Timestamp(ts)
    return t.weekday() == 4 and t.hour == 16 and t.minute >= 45


def manage(s: Setup, m15: pd.DataFrame, cfg: AlexConfig,
           equity: float, usd_per_quote: float,
           structure: tuple | None = None) -> Trade | None:
    """SET AND FORGET. Stop or target, and nothing else.

    THERE IS NO BREAK EVEN HERE, no partial, no trail, and NO CLOCK. Rule 8
    and rule 9. The only reason this function can end a trade other than at
    one of the two prices is `max_hold_days`, which is OURS and declared —
    he states no cap at all.

    The 15-minute frame is used for one job: when an hour touches both the
    stop and the target, the 15-minute bars inside it say which came first. A
    15-minute bar that still touches both is scored as the LOSS.
    """
    dist = abs(s.entry - s.stop)
    if dist <= 0:
        return None
    # Q1. SIZE FOLLOWS QUALITY. The weakest VALID setup — his own floor, one
    # candle engulfed — still trades, at a third of a position. A setup with
    # every confluence he names trades at a full one. "you can risk more on
    # low-risk trades" (LwMsai2ppKc.txt 00:22:34, 2026-02-22). The dial is
    # his, the ladder is ours, and it flows through the SAME single sizing
    # function every book in this repo uses. Nothing below changes what
    # counts as a valid setup.
    q = float(getattr(s, "quality", 1.0) or 1.0)
    allow = cfg.risk_pct_per_trade * equity * q
    sz = size_position(
        account=equity, entry=s.entry, stop_distance=dist,
        risk_allowance=allow,
        tightest_stop_pct=0.0,          # never measured; never borrowed
        usd_per_quote=usd_per_quote,
        buying_power=None,
        outer_allowance=allow,
        hold_size_still=False)
    if not sz["ok"] or sz["units"] <= 0:
        return None

    units = float(sz["units"])
    notional = units * s.entry * usd_per_quote
    tr = Trade(
        instrument=s.instrument, session=s.session, direction=s.direction,
        signal_t=s.signal_t, entry_t=s.decided_t, entry=s.entry,
        stop=s.stop, target=s.target, area_lo=s.area_lo, area_hi=s.area_hi,
        area_tf=s.area_tf, touches=s.touches, confirm=s.confirm,
        pattern=getattr(s, "pattern", "engulf"),
        signal_kind=getattr(s, "signal_kind", ""),
        engulfed=getattr(s, "engulfed", 0), dojis=getattr(s, "dojis", 0),
        quality=q, quality_pts=getattr(s, "quality_pts", 0),
        quality_avail=getattr(s, "quality_avail", 0),
        units=units, notional=notional,
        leverage=(notional / equity if equity > 0 else 0.0),
        risk_dollars=float(sz["risk_dollars"]),
        stop_share_of_price=(dist / s.entry if s.entry else 0.0),
        usd_per_quote=usd_per_quote)

    t15 = m15["t"].to_numpy()
    j0 = int(np.searchsorted(t15, np.datetime64(s.decided_t), "left"))
    hh = m15["high"].to_numpy(float)
    ll = m15["low"].to_numpy(float)
    cc = m15["close"].to_numpy(float)
    tt = m15["t"].to_numpy()
    deadline = np.datetime64(s.decided_t + pd.Timedelta(days=cfg.max_hold_days))

    # S8. HIS FRIDAY RULE, and it is the ONLY clock this function reads.
    #
    #   "if you're in a losing position and the weekend is coming up and
    #    you're halfway through your stop loss, I would probably close before
    #    the market closes because when market opens on Sunday when the
    #    spreads are quite high, that could simply take you out at a loss"
    #   — KPVVOa6c6dY_dumb_clean.txt, 2026-06-14
    #
    # NOT a break even — a break-even exit is at the entry price and this one
    # is at a loss, so "I am not a break even trader" is untouched. The stop
    # itself never moves anywhere in this function. Both of his conditions are
    # required: it must be Friday's last bar AND the trade must be more than
    # halfway to its stop.
    friday_rule = bool(getattr(cfg, "friday_exit_at_half_stop", False))
    half = 0.5 * dist

    # X1. THE STRUCTURE-SHIFT EXIT. The reason for the trade was that market
    # structure pointed this way; when structure turns the other way, in his
    # own definition of a turn, the reason is gone.
    #
    #   "Change of character is when the market shifts. When you changes from
    #    bullish to bearish. Simple. Break of structure is when this was the
    #    previous structure and we break it."
    #   — grw58BIzotU.txt 06:09:21, 2025-09-28
    #
    # OURS: applying it to an OPEN trade. He teaches change of character as an
    # ENTRY concept and his stated management is the opposite of this —
    # "once you enter a trade you pretty much just have to set and forget ...
    # You either let the trade hit your stop loss or let the trade hit your
    # takeprofit" (grw58BIzotU.txt 02:47:06). So this ships OFF and is
    # measured on, never assumed. It reads the SAME 4-hour trend state the
    # entry read, snapshotted at each 4-hour close and never before it.
    flip_rule = bool(getattr(cfg, "exit_on_structure_flip", False))
    st_states, st_closes = (structure if structure else (None, None))

    def _flipped(ts) -> bool:
        if st_states is None:
            return False
        return _state_at(st_states, st_closes, ts) == -s.direction

    # X2. THE RUNNER. "Once your trade gets to your original take profit,
    # close this trade fully and then LEAVE THIS ONE RUN because you want to
    # be greedy" (o1T6dLoywTw.en.vtt 00:06:25, 2023-03-26), and "I would
    # always aim for the trade to have a potential of a one to 4"
    # (grw58BIzotU.txt 08:38:10, 2025-09-28). The remainder keeps the ORIGINAL
    # stop — he is not a break-even trader and nothing here moves a stop.
    runner_on = bool(getattr(cfg, "runner", False))
    run_share = float(getattr(cfg, "runner_share", 0.5)) if runner_on else 0.0
    cap_r = float(getattr(cfg, "runner_cap_r", 0.0) or 0.0)
    cap_px = (s.entry + s.direction * cap_r * dist) if (runner_on and cap_r) \
        else None

    exit_px, exit_t, why = None, None, ""
    booked_at_target = False
    for j in range(j0, len(m15)):
        if tt[j] > deadline:
            exit_px, exit_t, why = None, pd.Timestamp(tt[j]), "held_out"
            break
        if s.direction < 0:
            hit_stop, hit_tgt = hh[j] >= s.stop, ll[j] <= s.target
        else:
            hit_stop, hit_tgt = ll[j] <= s.stop, hh[j] >= s.target
        if hit_stop and hit_tgt:
            tr.same_bar_resolved = True
            exit_px, exit_t, why = s.stop, pd.Timestamp(tt[j]), \
                ("runner_stop" if booked_at_target else "stop")
            break
        if hit_stop:
            exit_px, exit_t, why = s.stop, pd.Timestamp(tt[j]), \
                ("runner_stop" if booked_at_target else "stop")
            break
        if hit_tgt and not booked_at_target:
            if not runner_on:
                exit_px, exit_t, why = s.target, pd.Timestamp(tt[j]), "target"
                break
            booked_at_target = True
            tr.target_t = pd.Timestamp(tt[j])
            continue
        if booked_at_target and cap_px is not None and (
                (ll[j] <= cap_px) if s.direction < 0 else (hh[j] >= cap_px)):
            # "once you get to a one to four, you're at your home run, TRADE
            # IS DONE." — M8wDlKjaQRk.txt 00:15:07, 2026-04-05
            exit_px, exit_t, why = cap_px, pd.Timestamp(tt[j]), "runner_cap"
            break
        if booked_at_target and _flipped(tt[j]):
            exit_px, exit_t, why = float(cc[j]), pd.Timestamp(tt[j]), \
                "runner_flip"
            break
        if (not booked_at_target) and flip_rule and _flipped(tt[j]):
            exit_px, exit_t, why = float(cc[j]), pd.Timestamp(tt[j]), "flip"
            break
        if friday_rule and _is_last_bar_of_the_week(tt[j]) and \
                (cc[j] - s.entry) * s.direction <= -half:
            exit_px, exit_t, why = float(cc[j]), pd.Timestamp(tt[j]), \
                ("runner_friday" if booked_at_target else "friday")
            break

    if why == "":
        tr.outcome = "open"
        return tr
    if why == "held_out":
        # the tape ran past our own cap. Marked, not scored as either.
        tr.outcome = "held_out"
        tr.exit_t = exit_t
        return tr

    tr.exit, tr.exit_t, tr.outcome = float(exit_px), exit_t, why
    if booked_at_target:
        # the first slice left at his target, the rest at whatever ended it
        tr.runner_share = run_share
        gross = (units * (1.0 - run_share) * (s.target - s.entry)
                 + units * run_share * (tr.exit - s.entry)) \
            * s.direction * usd_per_quote
    else:
        gross = units * (tr.exit - s.entry) * s.direction * usd_per_quote
    # COST. Charged here, consulted nowhere.
    tr.cost = notional * cfg.round_trip_cost_pct
    tr.pnl = gross - tr.cost
    tr.r_multiple = tr.pnl / tr.risk_dollars if tr.risk_dollars else 0.0
    tr.hours_held = (pd.Timestamp(exit_t) - pd.Timestamp(s.decided_t)) \
        .total_seconds() / 3600.0
    return tr


# ================================================================ THE RUN
def usd_per_quote_series(instrument: str, frames: dict,
                         cache: dict | None = None):
    """USD per unit of the QUOTE currency, per day.

    1.0 for EUR/USD, GBP/USD and XAU/USD — the quote already is dollars. For
    GBP/JPY the profit arrives in yen, and USD-per-JPY is GBPUSD / GBPJPY,
    both of which are already on disk. Getting this wrong would be off by
    about the yen rate — a factor of some 150, not a rounding error.
    """
    if instrument != "GBP_JPY":
        return None
    cache = cache if cache is not None else {}
    if "gbpusd_d" not in cache:
        cache["gbpusd_d"] = pd.read_parquet(cache_name("GBP_USD", "1d"))
    gu = cache["gbpusd_d"][["t", "close"]].rename(columns={"close": "gu"})
    gj = frames["1d"][["t", "close"]].rename(columns={"close": "gj"})
    m = gu.merge(gj, on="t", how="inner")
    m["upq"] = m["gu"] / m["gj"]
    return m[["t", "upq"]].reset_index(drop=True)


def _upq_at(series, ts, default=1.0) -> float:
    if series is None or not len(series):
        return default
    j = int(np.searchsorted(series["t"].to_numpy(),
                            np.datetime64(pd.Timestamp(ts)), "right")) - 1
    if j < 0:
        return float(series["upq"].iloc[0])
    return float(series["upq"].iloc[j])


def run_instrument(instrument: str, start, end, cfg=None,
                   frames: dict | None = None, shared: dict | None = None,
                   mode: str = "dumb") -> dict:
    """One instrument, one $100,000 account, in time order.

    `mode` picks which reading of him is being run:
        "dumb"    — THE SPINE, his newest teaching (2026-06-14). The default.
        "topdown" — the older multi-timeframe reading, kept so the conflict
                    between the two is measured rather than asserted.

    Equity at the moment of entry counts only trades that had already CLOSED
    by then — which is what a live account would have shown. His trades run
    for days, so this matters more here than it does on an intraday book.
    """
    if cfg is None:
        cfg = dumb_config_for(instrument) if mode == "dumb" \
            else config_for(instrument)
    frames = frames or load(instrument)
    shared = shared if shared is not None else {}
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    structure = None
    if isinstance(cfg, DumbConfig):
        pat = getattr(cfg, "pattern", "engulf")
        setups = []
        if pat in ("engulf", "both"):
            setups += find_setups_dumb(instrument, frames, cfg, start, end)
        if pat in ("hs", "both"):
            setups += find_setups_hs(instrument, frames, cfg, start, end)
        if pat not in ("engulf", "hs", "both"):
            raise ValueError(f"unknown pattern {pat!r}")
        setups.sort(key=lambda s: (s.decided_t, s.pattern))
        cool = pd.Timedelta(minutes=cfg.reentry_cooldown_bars
                            * _TF_MINUTES[cfg.tf])
        d4 = frames[cfg.tf]
        structure = (trend_series(d4), closes_at(d4, cfg.tf))
    else:
        setups = find_setups_topdown(instrument, frames, cfg, start, end)
        cool = pd.Timedelta(minutes=cfg.reentry_cooldown_bars
                            * _TF_MINUTES[cfg.confirm_tf])
    setups = apply_control(setups, cfg)
    upq = usd_per_quote_series(instrument, frames, shared)
    m15 = frames["15m"]

    # HIS CADENCE CAP, OFF BY DEFAULT. See `DumbConfig.human_cadence_cap` for
    # Wallace's ruling and the reason: the cap's stated purpose in his own
    # material is not to over-trade and not to let emotion in, and a bot on a
    # demo venue has neither. Built so the cost of his cap is measurable.
    cap_on = bool(getattr(cfg, "human_cadence_cap", False))
    cap_n = int(getattr(cfg, "max_positions_per_week", 2))
    week_count: dict = {}
    cap_skipped = 0

    trades, closed = [], []
    busy_until = None
    for s in setups:
        if cfg.one_position_at_a_time and busy_until is not None \
                and s.decided_t < busy_until:
            continue
        if cap_on:
            key = pd.Timestamp(s.decided_t).to_period("W")
            if week_count.get(key, 0) >= cap_n:
                cap_skipped += 1
                continue
        eq = cfg.account_start + sum(
            t.pnl for t in closed
            if t.exit_t is not None and t.exit_t <= s.decided_t)
        tr = manage(s, m15, cfg, eq, _upq_at(upq, s.decided_t),
                    structure=structure)
        if tr is None:
            continue
        if cap_on:
            week_count[key] = week_count.get(key, 0) + 1
        trades.append(tr)
        if tr.exit_t is not None:
            closed.append(tr)
            closed.sort(key=lambda x: x.exit_t)
            busy_until = tr.exit_t + cool
        else:
            busy_until = pd.Timestamp.max

    weeks = max(1.0, (end - start).days / 7.0)
    return {"instrument": instrument, "setups": setups, "trades": trades,
            "account": cfg.account_start + sum(t.pnl for t in trades),
            "weeks": weeks, "config": cfg, "start": start, "end": end,
            "cap_skipped": cap_skipped}


def run_book(instruments=None, start=None, end=None, cfg_over: dict | None = None,
             cache: dict | None = None, verbose: bool = True,
             mode: str = "dumb") -> dict:
    """Every instrument on its OWN $100,000. Four instruments is four
    accounts, not one — the basis every number in this project is quoted on.

    `mode` defaults to "dumb" — the spine, his newest teaching. Note that HIS
    OWN spine is ONE PAIR, EUR/USD: running it across four instruments is
    already a departure from him and it is declared in `in_his_words()`.
    """
    cache = cache if cache is not None else {}
    shared: dict = {}
    out = {}
    for inst in (instruments or INSTRUMENTS):
        if inst not in cache:
            cache[inst] = load(inst)
        cfg = (dumb_config_for(inst, **(cfg_over or {})) if mode == "dumb"
               else config_for(inst, **(cfg_over or {})))
        r = run_instrument(inst, start, end, cfg=cfg, frames=cache[inst],
                           shared=shared, mode=mode)
        out[inst] = r
        if verbose:
            ts = [t for t in r["trades"] if t.outcome in ("stop", "target")]
            wins = sum(1 for t in ts if t.pnl > 0)
            print(f"  {inst:8s} {len(ts):>4} trades  "
                  f"{(wins / len(ts) * 100 if ts else 0):>5.1f}% won  "
                  f"net ${sum(t.pnl for t in ts):>+11,.0f}  "
                  f"{len(ts) / r['weeks']:.2f}/week")
    return out


def frame(book: dict) -> pd.DataFrame:
    rows = []
    for inst, r in book.items():
        for t in r["trades"]:
            rows.append({
                "instrument": inst, "session": t.session,
                "side": "long" if t.direction > 0 else "short",
                "signal_t": t.signal_t, "entry_t": t.entry_t,
                "exit_t": t.exit_t, "entry": t.entry, "stop": t.stop,
                "target": t.target, "exit": t.exit, "outcome": t.outcome,
                "confirm": t.confirm, "area_tf": t.area_tf,
                "touches": t.touches, "pattern": t.pattern,
                "signal_kind": t.signal_kind, "engulfed": t.engulfed,
                "dojis": t.dojis, "quality": t.quality,
                "quality_pts": t.quality_pts,
                "share_of_full_size": t.quality,
                "stop_move_in_price_pct": 100.0 * t.stop_share_of_price,
                "leverage": t.leverage, "units": t.units,
                "notional": t.notional, "risk_dollars": t.risk_dollars,
                "pnl": t.pnl, "cost": t.cost, "r": t.r_multiple,
                "hours_held": t.hours_held,
                "same_bar_resolved": t.same_bar_resolved,
            })
    return pd.DataFrame(rows)


# ======================================================== OURS, NOT HIS
def in_his_words() -> str:
    """Every choice this file made that HE DID NOT MAKE, in one place, so the
    list is a decision and not an oversight."""
    return "\n".join([
        "THE SPINE IS HIS NEWEST TEACHING and it governs where it conflicts:",
        "  KPVVOa6c6dY_dumb_clean.txt, 2026-06-14 — 'one pair, one time frame,",
        "  one session, and one entry signal.' Three older rules are OVERRULED",
        "  by it and both readings are measured rather than asserted:",
        "    - ONE TIMEFRAME (the 4 hour) beats top-down weekly/daily/4H+1H.",
        "      'This video is picking one time frame only.' (2026-06-14) over",
        "      grw58BIzotU.txt 04:40:37 (2025-09-28).",
        "    - THE ENGULFING CANDLE ALONE beats the three-confirmation menu.",
        "      (2026-06-14) over BcWxqfcjk9A.txt 00:01:58 (2026-04-16), which",
        "      also allowed rejection candles and stars.",
        "    - PRE-LONDON AND LONDON ONLY beats the wider 01:00-10:30 window.",
        "      (2026-06-14) over grw58BIzotU.txt 01:11:50 (2025-09-28).",
        "  And one rule is NEW in it, with no older counterpart: the FRIDAY",
        "  EXIT when a trade is more than halfway to its stop. That is not a",
        "  break even — a break-even exit is at the entry price, this one is",
        "  at a loss — so 'I am not a break even trader' still holds.",
        "",
        "OURS, NOT HIS — every decision his material does not contain:",
        "  0. HIS SPINE IS ONE PAIR, EUR/USD. Running it on four instruments",
        "     is OUR extension, not his instruction, and it is the first thing",
        "     a reader of the numbers has to know. EUR/USD is reported on its",
        "     own everywhere so his own configuration can be read separately.",
        "  0b. MIN_ENGULFED DEFAULTS TO 1, his literal floor ('needs to engulf",
        "     the last candlestick'). His stated PREFERENCE is much stronger",
        "     ('the more candlestick it engulfs, the better'; his favourite",
        "     eats ten), and that preference is swept and reported rather than",
        "     silently made the default, because a setting picked for its",
        "     result is fitting and a setting picked for his sentence is not.",
        "  0c. 'STILL REJECTING' — he holds a half-stopped loser into the",
        "     weekend if it is 'still rejecting' and never defines it. NOT",
        "     implemented, which makes our Friday exit MORE eager than his.",
        "  1. A SWING POINT is an up candle then a down candle, level at the",
        "     higher of the two wicks (and the mirror for a low). He draws",
        "     swings on every chart and never once defines one. Imported from",
        "     tjr_bot.two_candle_swings rather than re-invented, because a",
        "     second definition of a swing in this repo is a bug waiting.",
        "  2. HOW NEAR IS A TOUCH. Three touches is HIS (MhWSZp4yS2c.txt",
        "     00:24:10, 2026-06-28). How close two swings must be to count as",
        "     the same area is SILENT, so it is half that timeframe's own",
        "     average true range — a share of the market's own movement, not",
        "     a number of pips that would mean different things on gold and",
        "     on EUR/USD.",
        "  3. THE AREA LIVES ON THE DAILY OR THE 4 HOUR, searched 200 bars",
        "     back, and the daily zone wins when both are present. He names",
        "     weekly, daily and 4-hour areas and gives no lookback at all.",
        "  4. THE DAILY CALLS THE DIRECTION AND THE 4 HOUR MUST AGREE; the",
        "     weekly is recorded and does NOT gate. This is the reading that",
        "     admits his own gold trade, which was a sell into an all-time",
        "     high after the DAILY shifted bearish — 'this is the higher low",
        "     and now we have shifted below it making this bearish'",
        "     (ig6Z2Gbk_LE_gold_clean.txt, 2025-11-09). Requiring the weekly",
        "     would have refused the one trade we have him on tape taking.",
        "  5. ENTRY IS THE CLOSE OF THE CONFIRMATION CANDLE, at market. He",
        "     says to wait for the confirmation and never says what price he",
        "     pays for it.",
        "  6. THE CONFIRMATION ARITHMETIC. 'Engulfs' is body-past-body with",
        "     the bigger body; a rejection wick is at least twice the body and",
        "     half the candle's range; a star's middle candle is under half",
        "     the body of the one before it. He shows these shapes and",
        "     quantifies none of them.",
        "  7. THE STOP BUFFER is a quarter of the hour's average true range",
        "     beyond the structure. His words are 'a little bit right above",
        "     this level' (grw58BIzotU.txt 09:09:09, 2025-09-28).",
        "  8. THE TARGET IS EXACTLY 1:2. That is his stated FLOOR, not his",
        "     habit — he also says 1:3 minimum (LwMsai2ppKc.txt 00:07:24,",
        "     2026-02-22) and books 1:4 and 1:5 on tape. Using the floor is",
        "     the conservative choice and it is ours.",
        "  9. ONE POSITION AT A TIME per instrument, with a 24-hour wait after",
        "     an exit. Concurrency is SILENT in his material.",
        " 10. A 30-DAY CAP on a held trade. He states NO cap; this exists so",
        "     a replay terminates, and any trade that reaches it is reported",
        "     as 'held_out' and scored as neither a win nor a loss.",
        " 11. SAME-BAR TIES GO TO THE LOSS. When a 15-minute bar touches both",
        "     the stop and the target, the stop is taken. Conservative, ours,",
        "     and counted so the reader can see how often it happened.",
        " 12. 3% OF THE ACCOUNT RISKED PER TRADE. His own-money band is 3-5%",
        "     (VzMlFZbWA0Y.txt 00:08:48, 2024-01-28); we take the bottom of",
        "     it. That is share of ACCOUNT lost if the stop is hit — not a",
        "     price move and not a share of margin.",
        " 13. NO BUYING-POWER CLAMP is passed to the sizing function, because",
        "     its clamp divides by the entry price without the quote",
        "     conversion, which is wrong for a yen pair. Leverage is reported",
        "     instead and never capped here.",
        " 14. GOLD REPLAYS ON OANDA XAU/USD and would TRADE on BloFin",
        "     XAUT-USDT. Same metal, two tapes. Gold's costs are BloFin's;",
        "     the pairs' are OANDA's measured spread.",
        "",
        "",
        "step472 — THE FOUR PIECES OF HIM step470 DID NOT HAVE, AND WHAT IS",
        "OURS INSIDE EACH OF THEM:",
        " 15. THE HEAD AND SHOULDERS is his, whole. What is OURS in the",
        "     detector: that a valid pattern needs at least TWO body swings",
        "     beyond the neckline (a left shoulder and a head) — he draws",
        "     three and says the only hard test is the neckline break; the",
        "     60-bar window those shoulders are counted in; the 18-bar wait",
        "     for the retest before the pattern is dropped; and the rule that",
        "     when two patterns' retests land on the SAME candle the more",
        "     recent neckline wins. He gives no clock and no count for any of",
        "     those. Everything else — bodies not wicks, the neckline being",
        "     the broken structure point, no pattern before the break, the",
        "     entry at the retest, the stop above the wick, the head sitting",
        "     at a level, the right-shoulder entry being off — is quoted.",
        " 16. THE STRUCTURE TARGET picks the NEAREST swing level in the trade",
        "     direction that still pays his 1:2, searched 120 bars back, and",
        "     stops a quarter of the average range short of it. 'The next",
        "     structure point', 'the closer the better' and 'a minimum of a",
        "     1:2' are all his sentences; the 120 bars and the quarter-range",
        "     shortfall are ours. A setup with no such level is NOT TAKEN,",
        "     which is his sentence too.",
        " 17. THE STRUCTURE-SHIFT EXIT and the RUNNER are OURS IN MECHANISM.",
        "     He teaches change of character as an ENTRY idea and his stated",
        "     management is the opposite of both — 'set and forget ... You",
        "     either let the trade hit your stop loss or let the trade hit",
        "     your takeprofit'. Both ship OFF and are measured on. The",
        "     runner's 1:4 ceiling IS his ('once you get to a one to four,",
        "     you're at your home run, trade is done', M8wDlKjaQRk.txt",
        "     00:15:07, 2026-04-05); the half-and-half split is ours.",
        " 18. THE QUALITY LADDER. The DIAL is his in every input — how many",
        "     candles the engulf ate, how many dojis stacked, both triggers",
        "     together, the higher timeframes agreeing, his 50 EMA. The",
        "     LADDER from those to a position size is entirely ours, and so",
        "     is the ANCHOR: a plain valid setup gets the configured risk and",
        "     confluence scales it UP to twice that, because his sentence is",
        "     'you can risk more on low-risk trades' and not 'risk less on",
        "     ordinary ones'. THE FLOOR FOR VALIDITY IS UNCHANGED AND STILL",
        "     HIS: one candle engulfed.",
        " 19. HIS CADENCE CAP — 'Limit yourself to two positions a week' —",
        "     is BUILT AND DEFAULTED OFF on Wallace's ruling of 2026-07-27:",
        "     its stated purpose in his own material is not over-trading and",
        "     not letting emotion in, and a bot on a demo venue has neither.",
        "     It is measured both ways. Nothing that defines whether a setup",
        "     is VALID was loosened alongside it.",
        " 20. THE REJECTION TRIGGER IS GATED ON A LEVEL. He shows dojis 'set",
        "     in place at a support level'; a rejection candle in mid-air is",
        "     not a setup he describes anywhere. The gate is his; that it is",
        "     implemented as his three-touch area of interest is ours.",
        " 21. THE 50 EMA moves SIZE and never validity, because that is the",
        "     rank he gives it: 'My indicators are simply an added confluence",
        "     ... It does not determine my whole entire trade.'",
        " 22. RUNNING THE HEAD AND SHOULDERS ON THE 4 HOUR is the spine's",
        "     timeframe, not a claim of his. He says the higher the timeframe",
        "     the stronger the pattern, and a daily reading needs the session",
        "     gate off because a daily candle closes at 17:00 New York. Both",
        "     are switchable and both are measured.",
        "",
        "SILENT IN HIS MATERIAL, AND LEFT SILENT:",
        "  - what makes him close a winner early ('you have to know when to",
        "    set and forget and when to not', grw58BIzotU.txt 09:20:44,",
        "    2025-09-28). No testable definition exists, so this engine does",
        "    not do it at all. It is the single biggest gap between what he",
        "    does and what any bot of his method can do.",
        "  - a maximum number of concurrent positions.",
        "  - correlation rules between open positions.",
        "  - weekend gap handling beyond 'no trades on Sundays'.",
    ])
