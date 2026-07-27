# The cockpit

The phone tells you a trade exists. This puts the same thing on the chart
while you place it, next to the live price and what is actually in the
account.

**It is a display. Nothing in here can place, change or cancel an order.**

---

## Start it

Three things, three terminals. All of them are on your machine and none of
them talks to a broker.

```
cd ~/cryptobot

python3 -m cockpit.service            # 1. the local service the panel reads
python3 -m cockpit.desk_recorder      # 2. the desk — this replaces tjr_desk.py
python3 -m cockpit.telegram_balance   # 3. listens for  balance 105000
```

Then load the extension: Chrome → `chrome://extensions` → Developer mode on
→ **Load unpacked** → `~/cryptobot/cockpit/extension`. Open a TradingView
chart and the panel is in the top right. Drag it by the word `drag`; `hide`
folds it away and it stays folded until you say otherwise.

### Run the recorder INSTEAD OF tjr_desk.py, not alongside it

`cockpit/desk_recorder.py` is `tjr_desk.Desk` with a notebook next to it. It
watches the same markets, makes the same decisions and sends the same
messages — it just also writes down what it sent, which is where the panel
gets the signal from. Running both would message you twice for every setup.

---

## The balance, which is the part that matters

Position size is worked out FROM the balance. A balance that is quietly
wrong makes every size after it quietly wrong, so nothing here ever invents
one. When it is not known, the alert says *"Size COULD NOT BE WORKED OUT —
do not take this one"* and the panel says why. That is the intended
behaviour.

Two ways in. Whichever was taken more recently is the one used.

**Text it.** Send the bot `balance 105000`. It answers with the number and
the time it was noted. Send just `balance` and it reads back what it has and
how old it is. Only your own chat can set it.

**Read it off TradingView.** Once:

```
python3 -m cockpit.tv_balance --login    # you sign in yourself
```

That opens a Chrome window on a profile under `cockpit/state`. Sign in by
hand — this never asks for, types or stores a password. Open the Trading
Panel at the bottom of the chart, connect Paper Trading, and leave that
panel open. Then, whenever you want a reading:

```
python3 -m cockpit.tv_balance --read
python3 -m cockpit.tv_balance --watch    # every five minutes
```

**It never clicks anything.** Not one click, anywhere. The Buy and Sell
buttons live in the same panel as the balance, and the only way to be sure a
script will never hit one is for it to have no way to hit anything. The cost
is that you have to leave the Trading Panel open yourself — if it is
collapsed, the reader says so and stores nothing.

When the session eventually expires it says **LOGGED OUT** in plain words
and writes nothing. It does not guess, and the stored number keeps its
original timestamp, so the panel starts saying how old it is getting.

---

## What is on the panel

**PRICE** — two numbers, both labelled with the job they do.
TradingView's own, read off the chart, is what you would be filled near. The
bot's feed underneath is what the alert was measured on. The gap between
them is stated rather than smoothed over. Every price says how old it is in
seconds; past thirty seconds it is drained of colour and marked STALE.

On US stocks the feed is **IEX only** — our data plan is refused the
combined feed of every exchange, and asking for it answers 403. So that
number is one exchange's last trade, not the market's, and it says so.

**ACCOUNT** — the balance, which route it came from, and when. Then what the
current signal risks, in dollars and as a share of the account, always
labelled `OF THE ACCOUNT` so it cannot be read as a move in the price. Over
a day old and it says so on its face.

**THE SIGNAL** — the same thing your phone got. Symbol, direction, entry,
the stop and the chart feature it sits on, every target, the size, the
one-line reason, and when it fired. `show the message that went to your
phone` prints the message itself.

The panel does not re-derive any of it: it calls the same functions in
`tjr_alerts` on the same stored signal with the same balance, and then
checks that every price it is about to draw actually appears in the message
that was sent. If one does not, it says *"THESE NUMBERS DO NOT MATCH THE
MESSAGE SENT TO YOUR PHONE"* rather than showing them.

A setup older than an hour is dimmed and labelled **has been and gone** —
the entry window is about forty minutes wide, so yesterday's alert is not a
trade to place this morning.

**OPEN** — what the bot believes you are in, with the stops. It cannot see
your broker. If you skipped one, it is wrong, and it says that too.

**The bottom line** says whether the desk is actually watching. Silence
means nothing is setting up — but only while something is running, and a
stopped recorder must never look like a quiet market.

---

## How it behaves when things break

| what broke | what you see |
|---|---|
| the service is not running | a red band, and every age on the panel keeps climbing |
| a price is 40 seconds old | `40 seconds old · STALE`, in grey |
| the balance was never set | `I do not know what is in the account` and no size anywhere |
| the balance is two days old | the number, and `THAT BALANCE IS MORE THAN A DAY OLD` |
| the desk recorder died | `THE BOT IS NOT WATCHING` |
| one market threw on the last sweep | `CRYPTO COULD NOT BE CHECKED — silence from it means nothing` |
| the bot restarted after an alert | the open list says it may be missing what you are still holding |
| a signal fired but could not be sized | `WHAT THIS SIGNAL RISKS IS UNKNOWN` — never `$0` |
| the chart stopped updating | `it last changed 6 minutes ago` |
| a symbol the bot does not watch | `the bot does not watch AAPL` and no price |
| the panel and the phone disagree | it says so and tells you to trust the phone |

Nothing shows a zero for something unknown, and nothing keeps drawing the
last value it saw as though it were current.

## Check it yourself

```
python3 step448_cockpit_check.py
```

Twenty-eight checks, including: the panel's numbers are found inside the
Telegram message that was sent; with no balance, no size is stated
anywhere; every price carries the exchange's own timestamp; no unknown comes
back as a zero; a dead desk reads differently from a quiet one; and no file
under `cockpit/` contains an order call or a click.
