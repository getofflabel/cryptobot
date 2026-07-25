# STEP 300 — CONSOLIDATION: six BTC books become one, named `bitcoin`

**Written 2026-07-25. NOTHING IN THIS PLAN HAS BEEN EXECUTED.** `bitcoin.py`
and `test_bitcoin.py` exist, are tested, and are INERT
(`NEW_ENTRIES_ENABLED = False`). Every edit listed below is a human's to
make. No book was modified, no file was deleted, nothing was deployed, no
git command was run.

## THE DIRECTIVE

Wallace, 2026-07-25:

> "we will get rid of the shorts lab and news desk and all that bullshit
> because it's deceiving, it doesn't work. what you will do is simply
> combine them into one bot and the bot is whatever what you're trading is
> called."

One book. Named after the market. Sole owner of BTC-USDT.

---

## 1. WHAT ACTUALLY OWNS BTC-USDT TODAY

The brief named six books. There are **seven** claimants, and the seventh
is the one that makes this migration harder than it looks.

| # | Book | File / entrypoint | State key | New entries today | Notes |
|---|---|---|---|---|---|
| 1 | The Ride | `step5_paper_trade.decide_and_trade` | `state["open_trade"]` | **LIVE, ungated** | Owns the one surviving edge. Its strategy is what `bitcoin.py` inherits. |
| 2 | The Strikes (BTC slot) | `tactical.tactical_cycle` | `state["tactical"]` | stood down | `NEW_ENTRIES_ENABLED = False` |
| 3 | The Shorts Lab | `shorts_lab.run_lab` | `state["shorts_lab"]` | **LIVE, ungated** | Has **no stand-down flag at all**. See §6, finding 2. |
| 4 | The Newsdesk | `newsdesk.run_newsdesk` | `state["newsdesk"]` | stood down | also carries a `"pending"` armed state |
| 5 | The Diver | `diver.run_diver` | `state["diver"]` | stood down | |
| 6 | The Breakout Book | `breakout_book.run_breakout_book` | `state["breakout_book"]` | `ENABLED = False` | returns before reconcile — see §6, finding 3 |
| 7 | **Daily Pick** | `daily_pick.run_daily_pick` | `state["daily_pick"]["open_trades"]` | **LIVE** | `UNIVERSE` includes `BTC-USDT`. **Not in `book_ledger.py` at all.** See §6, finding 1. |

Also present but NOT part of this consolidation, because they are different
symbols or different accounts entirely, and must not be touched:

- `tactical.amplifier_cycle` — **ETH-USDT**, state key `state["tactical_eth"]`
- `gold_book.py` — XAUT-USDT
- `spx_book.py`, `tradfi_engine.py` — internal paper ledgers, no BloFin orders
- `daily_pick.py`'s ETH / SOL / XAUT slots — those stay; only its BTC slot goes

---

## 2. WHAT GETS RETIRED, AND WHAT "RETIRED" MEANS

**Retired = new entries permanently off, exit and reconcile paths left
running, file kept on disk.** Nothing is deleted in this cutover. Deleting a
book is a separate, later decision, and it must not happen while that book
can still be holding a position.

| Book | Action | Mechanism |
|---|---|---|
| The Ride | retire | its strategy MOVES to `bitcoin.py`; see §3 step 4 |
| The Strikes (BTC) | retire | already gated; leave gate, stop calling it once flat |
| The Shorts Lab | retire | **add a `NEW_ENTRIES_ENABLED` gate first** (§3 step 1) |
| The Newsdesk | retire | already gated |
| The Diver | retire | already gated |
| The Breakout Book | retire | already off; fix the gate placement (§6, finding 3) |
| Daily Pick | **BTC slot only** | remove `"BTC-USDT"` from `UNIVERSE`; book survives on ETH/SOL/XAUT |

### Open positions must close normally — never orphaned

This is the single most dangerous part of the cutover, and this repo has
already broken it once. On 2026-07-25 a stand-down gate was placed above
the exit logic and the Diver crashed **every cycle** live with
`cannot access local variable 'direction'`; a book that crashes every cycle
silently MISSES trades, which biases the live record because it can still
take losers while crashing through winners. `test_stand_down_gates.py` was
written that same hour and encodes the two invariants:

1. **the gate sits AFTER `reconcile` and after every exit branch** — asserted
   textually (`src.index("STAND-DOWN GATE") > src.index("reconcile")`)
2. **the book's own tests still run with the gate in its production state**
   (flag OFF) without raising `NameError` / `UnboundLocalError`

`bitcoin.py` already satisfies both — verified by
`test_bitcoin.test_h_runs_correctly_with_the_enable_flag_off`, and by
running `test_stand_down_gates._run_with_gate_off("bitcoin", "test_bitcoin")`
directly: 16 tests ran, 0 crashes.

**Concretely, per retired book:** it keeps being called by `daemon.py` on
every cycle until its own `open_trade` is `None` AND the exchange shows its
slice flat. Only then is its `_run_book(...)` line removed. A book is never
un-wired while it might still hold something — the wire is what closes it.

---

## 3. THE ORDER OF OPERATIONS

Every step is independently revertible, and after every step the full suite
must be green. Do not batch these.

**Step 0 — baseline.** Run the full suite. Expect **212 passing across 20
files** (196 pre-existing + 16 in `test_bitcoin.py`). Run
`test_live_imports.py` on its own. Record the current BloFin BTC-USDT net
position and which books claim it.

**Step 1 — gate the Shorts Lab.** Add `NEW_ENTRIES_ENABLED = False` to
`shorts_lab.py` and a `STAND-DOWN GATE` block inside `run_lab`, placed after
reconcile and after every exit branch, with all of `direction` /
`contracts` / `ref_price` already bound. Add `("shorts_lab",
"test_shorts_lab")` to `test_stand_down_gates.GATED_BOOKS` — note there is
currently **no `test_shorts_lab.py`**, so either write one or gate the lab
via the same pattern and accept it is not covered by that guard. *Nothing
else changes in this step.* The lab is the only ungated aggressive book on
the symbol and it must stop opening new positions before a seventh book
joins the account.

**Step 2 — register the new book in the shared accounting.** In
`book_ledger.py`:

```python
out = {"ride": 0.0, "tact": 0.0, "lab": 0.0, "apprentice": 0.0,
       "newsdesk": 0.0, "diver": 0.0, "breakout": 0.0,
       "bitcoin": 0.0, "daily_pick": 0.0}     # <- both new
...
btc = state.get("bitcoin", {}).get("open_trade")
if btc:
    direction = btc.get("direction", 0) or 0
    sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
    out["bitcoin"] = sign * abs(float(btc.get("contracts", 0) or 0))

# daily_pick keeps a LIST keyed by symbol, not a single open_trade
for t in state.get("daily_pick", {}).get("open_trades", []) or []:
    if t.get("symbol") != "BTC-USDT":
        continue
    direction = t.get("direction", 0) or 0
    sign = 1 if direction > 0 else (-1 if direction < 0 else 0)
    out["daily_pick"] += sign * abs(float(t.get("contracts", 0) or 0))
```

Update `book_ledger.py`'s docstring to list both, and extend
`test_book_attribution.py` to cover them. `bitcoin.py` needs **no change**
when this lands: its `_recorded_all()` shim reads `recorded_book_positions()`
first and only fills in what is missing, so it produces the identical answer
before and after. Delete the shim later if you want, not now.

**Step 3 — teach Daily Pick about the new book, then take BTC off it.**
`daily_pick._btc_books_active()` iterates `recorded_book_positions()`, so
step 2 already makes it see `bitcoin`. Then remove `"BTC-USDT"` from
`daily_pick.UNIVERSE`. Its own BTC slot, if one is open at that moment,
still closes through `_book_exit` on its normal path — removing a symbol
from `UNIVERSE` only stops NEW picks (`analyze_universe` / `select_pick`);
`open_trades` is reconciled independently, by symbol.

**Step 4 — wire `bitcoin.py` in, still stood down.** In `daemon.py`'s
`full_cycle`:

```python
def _bitcoin():
    from bitcoin import run_bitcoin
    from step5_paper_trade import load_state
    run_bitcoin(private, live_feed, demo_feed, load_state())

_run_book("The Bitcoin Book", _bitcoin)
```

Place it FIRST among the BTC books, so it reconciles before any legacy book
acts in the same cycle. Mirror the same call in `hourly.py`'s backstop
section, in the same position, guarded by the same stale-heartbeat check the
other books use. Add `"bitcoin"` to `test_live_imports.LIVE_MODULES`
(verified: it imports clean under the research-package blocker — `exits.py`
and `step41_shorts.py` pull in nothing outside `requirements.txt`). Add
`("bitcoin", "test_bitcoin")` to `test_stand_down_gates.GATED_BOOKS`
(verified: 16 tests, 0 crashes with the gate off).

With `NEW_ENTRIES_ENABLED = False` this step trades nothing. It runs a full
cycle every 4h, reconciles, loads the memory, evaluates the rule, and logs
exactly what it WOULD have taken. **Leave it here for at least a few days
and read those `bitcoin_stood_down` log lines against what the Ride actually
does.** If the two ever disagree about whether the champion fired, stop and
find out why before going further.

**Step 5 — register the order tag.** Add `"bitcoin": "btc"` to
`blofin_private.BOOK_TAGS`. `make_client_order_id` does not validate against
that dict (it only checks the character class), so the tag already works —
this is for the orders-history filtering that makes BloFin's own record
per-book attributable. `test_blofin_private.py` computes the longest tag
dynamically (`max(BOOK_TAGS.values(), key=len)`), and `"btc"` ties `"tce"` at
3 characters, so nothing there needs touching.

**Step 6 — hand over the edge.** This is the only step that changes who
trades. In order:

1. wait until `state["open_trade"]` is `None` (the Ride is flat) — do not
   force it flat, let its own signal exit close it
2. add `NEW_ENTRIES_ENABLED = False` + a `STAND-DOWN GATE` to
   `step5_paper_trade.decide_and_trade`, after the reconcile block and after
   the exit path, before the entry block at `if desired_dir != 0:`
3. flip `bitcoin.NEW_ENTRIES_ENABLED = True`

The Ride and the Bitcoin book must **never both be armed**. They run the
same signal on the same symbol; two of them would double the position and
each would read the other's contracts as its own. Between (2) and (3) BTC is
untraded, which is the correct state to pass through.

**Step 7 — extend the journal so the memory loop keeps its teeth.** In
`export_journal.write_ledger`, add this book's events:

```python
elif a == "bitcoin_enter":
    rows.append([e.get("logged_at", ""), "BTC-USDT", "BUY",
                 e.get("fill_price", ""), e.get("contracts", ""),
                 e.get("rule", "bitcoin"), "demo", "open", ""])
elif a == "bitcoin_exit":
    pnl = e.get("realized_pnl", "")
    outcome = "win" if isinstance(pnl, (int, float)) and pnl > 0 else "loss"
    rows.append([e.get("logged_at", ""), "BTC-USDT", "SELL",
                 e.get("exit_price", ""), "",
                 f"{e.get('rule', 'bitcoin')}:{e.get('reason', '')}",
                 "demo", outcome, pnl])
```

The `rule:reason` shape in the SELL row is deliberate and
`bitcoin._split_reason()` already parses it. Without it, `data/ledger.csv`
carries only an exit reason and cannot attribute a close to the rule that
took it, so the ledger read-back can count recent closes but cannot move a
rule's counters. `write_learnings` needs **no change** — `bitcoin.py` writes
lessons in exactly the five-key schema it already renders.

**Step 8 — unwire the retired books, one at a time, once each is flat.**
Remove its `_run_book(...)` line from `daemon.py` and its section from
`hourly.py` only after its own `open_trade` is `None` and the exchange
agrees. Keep the file, keep its tests green.

---

## 4. WHAT CHANGES, FILE BY FILE

| File | Change | Step |
|---|---|---|
| `shorts_lab.py` | add `NEW_ENTRIES_ENABLED` + gate after reconcile/exit | 1 |
| `book_ledger.py` | add `"bitcoin"` and `"daily_pick"` keys + docstring | 2 |
| `test_book_attribution.py` | cover both new keys | 2 |
| `daily_pick.py` | drop `"BTC-USDT"` from `UNIVERSE` | 3 |
| `daemon.py` | add `_bitcoin()` + `_run_book("The Bitcoin Book", ...)` first among BTC books; later remove retired books' lines | 4, 8 |
| `hourly.py` | mirror the same call in the backstop | 4 |
| `test_live_imports.py` | `LIVE_MODULES += ["bitcoin"]` | 4 |
| `test_stand_down_gates.py` | `GATED_BOOKS += [("bitcoin", "test_bitcoin")]` | 4 |
| `blofin_private.py` | `BOOK_TAGS["bitcoin"] = "btc"` | 5 |
| `step5_paper_trade.py` | `NEW_ENTRIES_ENABLED` + gate in `decide_and_trade` | 6 |
| `bitcoin.py` | flip `NEW_ENTRIES_ENABLED = True` | 6 |
| `export_journal.py` | map `bitcoin_enter` / `bitcoin_exit` | 7 |

**Not touched:** `exits.py`, `step41_shorts.py`, `strategy.py`, `tactical.py`'s
ETH amplifier, `gold_book.py`, `spx_book.py`, `tradfi_engine.py`.

---

## 5. ROLLBACK

Every step reverses cleanly, and the two that matter are trivial:

- **any step before 6** — nothing traded differently; revert the edit
- **step 6** — set `bitcoin.NEW_ENTRIES_ENABLED = False` and
  `step5_paper_trade.NEW_ENTRIES_ENABLED = True`. Whichever book is holding
  at that moment keeps holding and closes through its own exit path; neither
  flag touches an open position, by construction.
- **a stood-down rule inside `bitcoin.py`** — `clear_rule_stand_down(state,
  "vol_gated_trend", who="wallace")`. There is no automatic re-enable and
  there should not be one.

---

## 6. WHAT MAKES THIS HARDER THAN IT LOOKS

Seven findings, in descending order of how much they can cost.

### Finding 1 — Daily Pick is a seventh BTC book, and the shared accounting has never known about it
`daily_pick.py`'s `UNIVERSE` is `["BTC-USDT", "ETH-USDT", "SOL-USDT",
"XAUT-USDT"]`, so it can and does hold BTC-USDT. But
`book_ledger.recorded_book_positions()` covers only ride / tact / lab /
apprentice / newsdesk / diver / breakout — **`daily_pick` is not in it**, and
it cannot be added by copy-paste because it is the one book that keeps a
LIST (`open_trades`, keyed by symbol) instead of a single `open_trade`.

The live consequence today: a Daily Pick BTC position is invisible to the
shared accounting, so `attributed_position(net, state, "<any book>")`
silently hands that position to whichever book asks. Every BTC book on the
account currently over-counts its own slice by exactly Daily Pick's BTC
size. This is the same class of fault as the 2026-07-23 incident, still
open, and it has nothing to do with the consolidation — the consolidation
just walks straight into it.

`bitcoin.py` refuses to inherit it: `_daily_pick_btc()` reads the list
itself, filters to BTC-USDT, and folds it into `_recorded_all()`. That keeps
THIS book honest. It does not fix the other six, and step 2 above is the
real fix.

### Finding 2 — the Shorts Lab is fully live and has no stand-down flag
Four books are described as "already stood down". The Shorts Lab is not one
of them: `grep -n "NEW_ENTRIES_ENABLED" shorts_lab.py` returns nothing. It
has situational stand-downs (it refuses to short while the 4h champion is
long, and while the exchange shows net long) but no master switch, and it is
the only *aggressive, opposite-direction* book on the symbol. It must be
gated in step 1, before anything else, or the cutover adds a seventh book to
an account where an ungated short book is still opening positions.

### Finding 3 — the Breakout Book's `ENABLED` flag returns BEFORE reconcile
`breakout_book.run_breakout_book` starts with:

```python
if not ENABLED:
    return {"action": "stood_down", ...}
```

That is above the reconcile block and above every exit branch. It is
harmless *right now* because the book was switched off while flat — but it
is exactly the shape `test_stand_down_gates.test_every_gate_sits_after_the_exit_logic`
forbids, and `breakout_book` is not in `GATED_BOOKS`, so nothing catches it.
If that book is ever switched off while holding, its position is orphaned:
no exit path, no reconcile, no stop management. Fix it when you touch the
file; do not switch it on and off casually before then.

### Finding 4 — the retest and the live book run two different function names
Round 150 validated Edge 3 through `strategy.vol_gated_ma(fast=20, slow=100,
min_atr_pct=1.5)`. The live Ride runs `strategy.vol_filtered_ma` with the
same three numbers. They are the same long-only state machine written two
ways and they agree bar-for-bar on every fixture tested, but nothing in the
repo asserted that, so an edit to either one could silently have made the
live book a strategy nobody validated.
`test_bitcoin.test_k_live_signal_matches_the_validated_one` now asserts the
equality on three different frames. `bitcoin.py` imports `vol_filtered_ma`
(the live one) and imports `FAST` / `SLOW` / `MIN_ATR_PCT` from
`step5_paper_trade` so the two books cannot drift apart on parameters
either.

### Finding 5 — the validated numbers came from ONE stop mechanism, and the live one has to be TWO
`exits.stop_structure_trailing` is `style="intrabar_or_close"`: in the
backtest it fires the instant price trades through the floor intrabar **or**
closes beyond it, whichever comes first. Live, only half of that can live on
BloFin — a `place_tpsl` stop order handles the intrabar half. The
close-confirmed half has to be a book-side market exit on the next cycle
(`structure_broken` in `run_bitcoin`). So the live exit is two mechanisms
reproducing one backtested one, and the book-side half is only as timely as
the cycle that runs it. The 4h timeframe makes that gap small and the
exchange-side stop is always the tighter of the two, but it is a real
difference between what was measured and what will happen, and it should be
stated in any future report of this book's live numbers rather than
discovered later.

### Finding 6 — the memory loop is only as good as the journal, and the journal is rebuilt from cloud state
`data/ledger.csv` and `data/learnings.md` are not appended to — they are
REWRITTEN from scratch by `export_journal.py`, from Supabase state, on the
hourly job. Two things follow. First, until step 7 lands, this book's closes
do not appear in `ledger.csv` at all, so the per-rule counters run on the
book's own `state["bitcoin"]["trades"]` only. Second, `write_learnings`
renders `state["lessons"]`, which is capped at the last 50 entries across
ALL books — so a lesson can age out of the diary while the book's own trade
record still remembers the loss. `bitcoin.py` therefore counts on its own
trade records and treats the files as the readable, human-facing surface
plus a secondary source. That is the honest division; do not let a future
change make the file the only source.

### Finding 7 — this is a rules-and-counters memory, and it must never be described as more
`load_memory` reads, counts consecutive losses, and latches a boolean. There
is no model, no inference, nothing that learns. The gating is real and
useful — a rule that loses three times the same way stops trading until a
person says otherwise, which is more discipline than most live books have —
but if this ever gets written up as the bot "learning from its mistakes",
that sentence will be wrong. Nothing in `bitcoin.py` is named "AI" anything,
and nothing should be.

---

## 7. VERIFICATION ALREADY DONE (nothing deployed)

- `test_bitcoin.py` — 16/16 passing
- full repo suite — **212 passing across 20 files** (196 pre-existing, all
  still green, plus the 16 new)
- `test_live_imports.py` — 2/2, and `bitcoin` added to `LIVE_MODULES`
  simulated in a fresh subprocess under the research-package blocker:
  `{"sentinel_ok": true, "failures": []}`
- `test_stand_down_gates._run_with_gate_off("bitcoin", "test_bitcoin")` —
  16 tests ran with `NEW_ENTRIES_ENABLED = False`, 0 unbound-name crashes
- `data/ledger.csv` and `data/learnings.md` — untouched (the one test that
  exercises `export_journal`'s writer does it inside a temp working
  directory)
- no live order placed, no git command run, no existing file modified
