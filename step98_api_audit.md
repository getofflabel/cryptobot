# step98_api_audit.md — hand-rolled math vs BloFin's own API fields

Audit requested after Wallace: *"you're gonna have to start studying what's
actually built into this API... you're trying to do a lot of simple math
that you're not really doing right by yourself."* Written against
`BLOFIN_API_REFERENCE.md` (read first, as instructed). No code changed, no
git commands run, no orders placed, no private mutating endpoints called —
every check below was static reading of the repo.

**Scope discipline applied throughout:** backtests (`backtest.py`,
`step*_*.py` research/sealed-test scripts) legitimately compute their own
PnL — there is no exchange to ask about a historical bar — and are excluded
below unless noted. `news_book.py` and the `spx_book.py` / `tradfi_engine.py`
paper books are also legitimately hand-computed: they trade instruments
BloFin does not offer (S&P, oil, etc. — no `unrealizedPnlRatio`,
`liquidationPrice`, or `contractValue` exists for them to read), and their
own code comments already say so explicitly. Only **live paths** — real
BloFin demo-account order flow, sizing, reconciliation, and the dashboard —
are graded for severity below.

---

## Part 1 — prioritized findings

| # | File : line | What it computes by hand | Should read instead | Severity |
|---|---|---|---|---|
| 1 | `step5_paper_trade.py:79` `CONTRACT_BTC = 0.001` — imported and reused by `diver.py`, `newsdesk.py`, `shorts_lab.py`, `tactical.py` (BTC slot), `breakout_book.py`. Six live books size every real order (`contracts = notional / price / CONTRACT_BTC / LOT`) off ONE hardcoded constant, never the exchange. | `demo_feed.get_instrument(symbol)["contractValue"]` — the exact call `daily_pick.py:603` and `gold_book.py` already make successfully. | **CRITICAL** |
| 2 | `tactical.py:53-59` `SLOTS = {"BTC-USDT": {"contract": 0.001, ...}, "ETH-USDT": {"contract": 0.01, ...}}` | Same — `get_instrument()` per symbol, not a static dict literal. | **CRITICAL** |
| 3 | `step5_paper_trade.py:434,698,798`; `diver.py:370,515,564`; `newsdesk.py:532,693`; `shorts_lab.py:206,415`; `tactical.py:99,297,407,445`; `breakout_book.py:417,618,665` — every live entry/exit sizing and realized-PnL calc built on findings #1/#2 | Same instrument field | **CRITICAL** (this is the blast radius of #1/#2 — one BloFin contract-spec change silently mis-sizes and mis-books PnL on all six live books at once, with no error thrown) |
| 4 | `daily_pick.py:1220` `contract_value = t.get("contract_value", 0.001)` — fallback used only when a trade record predates the field (line 1388 shows new trades DO store the real spec value) | Should never fall back silently; if the field is missing, treat as a data-integrity error (log/alert) rather than assuming BTC's value for a book that trades many symbols (XRP contract=100, DOGE=1000) | **MEDIUM** (dead path for new trades, but a landmine for any legacy/corrupted record on a non-BTC symbol) |
| 5 | Nowhere in the repo is `unrealizedPnlRatio` ever read. `bot_pnl.py` and `flatten.py` read `unrealizedPnl` (dollars) correctly, but no live file reads the exchange's own margin-fraction PnL%. | `positions()[i]["unrealizedPnlRatio"]` | **MEDIUM** (not wrong math — it's an unused API field — but it's the exact field the whole audit exists because of, and nothing in the live path surfaces it) |
| 6 | Nowhere in the repo is `liquidationPrice` or `marginRatio` ever read from `positions()`, despite the exchange returning both per position. `live_read.py`'s `_liq_price()`/margin-ratio math is fine (it's for non-BloFin tradfi/SPX paper books only), but there is currently **no live display anywhere** of the real BTC-USDT books' actual exchange-reported liquidation price or margin ratio. | `positions()[i]["liquidationPrice"]`, `positions()[i]["marginRatio"]` | **MEDIUM** (gap, not a wrong calculation — but it means the dashboard shows closed-trade history for the real books, never their live liquidation/margin health, so if anyone DID want that number today they'd have to derive it by hand, recreating the exact mistake `BLOFIN_API_REFERENCE.md` was written to prevent) |
| 7 | `dashboard/index.html:2049-2076` `positionPnl()` — hand-computes `dollars`, `pct` (fraction of margin, correct convention), `maintMargin`, `marginRatioPct` for the paper (Oil / S&P 500) position cards | LEGITIMATE per the rules above — no BloFin instrument exists for Oil/SPY, own comment says so (`live_read.py:132` `MAINT_MARGIN_RATE_ASSUMED — OUR assumption, not a published BloFin figure`). Listed here only because the UI label doesn't say "assumed," see Part 2 #1. | **LOW** (display-only, non-crypto market, already self-documented as an assumption) |
| 8 | `dashboard/index.html:2262,2294-2296` `mmrPct` / "est. liq price / margin ratio assume a 0.5% maintenance margin rate — OUR assumption" | Same as #7 — already labeled correctly in the UI itself, model example of how to do this right | **LOW** (informational; flagged as the pattern to copy, not a problem) |

### What was checked and found clean (no rederivation)

- `blofin_private.py` — pure API client; no risk math anywhere in it.
- `book_ledger.py` — pure contract-count attribution/bookkeeping (net minus other books' recorded slices), never touches margin/PnL%/liquidation.
- `gold_book.py` — reads `contractValue`/`lotSize`/`tickSize`/`maxLeverage` from the real instruments endpoint (`_instrument_spec`, lines 347-365); no hand-rolled liquidation or margin-ratio math.
- `daily_pick.py` — reads `contractValue`/`minSize`/`lotSize`/`tickSize`/`maxLeverage` from `demo_feed.get_instrument()` (`_demo_spec`, lines 592-614) and correctly incorporates `spec["max_leverage"]` into its leverage cap (line 813) instead of assuming one. This file is the model to copy for findings #1-#3.
- `flatten.py` — reads `marginMode`, `leverage`, `unrealizedPnl` straight off the position object; computes nothing.
- `exchange.py` — market-data/order plumbing only; the `get_instrument()` method other files should be calling already lives here.
- `daemon.py`, `situation_room.py`, `morning_read.py`, `audit.py`, `export_journal.py`, `collector.py`, `chart_eyes.py`, `chart_reader.py`, `video_vision.py` — no risk/margin/PnL-ratio math found.
- `spx_book.py`, `tradfi_engine.py`, `news_book.py` — hand-computed PnL/leverage/notional, but LEGITIMATE: no BloFin instrument exists for these underlyings, and each file says so in its own docstring.
- Position-sizing formulas that size a NEW order before it exists (`daily_pick.py`'s `position_notional = RISK_PCT * equity / (stop_pct/100)`, and the `notional = equity * ALLOC * LEV` pattern repeated across `diver.py`/`newsdesk.py`/`shorts_lab.py`/`tactical.py`/`breakout_book.py`) are LEGITIMATE — there is no API field for "how big should my next order be," that is a risk-policy decision this bot has to make itself. Only the **contract-value conversion inside** those formulas (findings #1-#3) is the problem, not the sizing logic itself.

---

## Part 2 — ambiguous percentages (the highest-value part of this audit)

Every place a percentage is shown without saying whether it's a **PRICE
move** or a **fraction of MARGIN**, with the corrected wording using the
mandatory convention.

| # | Location | Exact current wording | Problem | Corrected wording |
|---|---|---|---|---|
| 1 | `dashboard/index.html`, paper-book positions table (`buildPositionsTableHtml`, `~line 2283`) | Column header **"PnL (PnL%)"**, cell shows e.g. `-$10.87 (-5.33%)` | The `%` here IS fraction-of-margin (`positionPnl()` computes `dollars/margin*100`, matching BloFin's own convention) but the column header never says "of margin." A reader who doesn't already know the convention will read it exactly the way Wallace's screen was misread the first time. | Header: **"PnL (% of margin)"**. Optionally add the price-move number alongside per the mandatory convention, e.g. tooltip/sub-label: `"5.33% of margin = 0.27% price move at 20x"` (computed from `t.leverage`, already available on `t`). |
| 2 | `dashboard/index.html`, `Margin Ratio` column (`~line 2291,2333`) | Cell shows e.g. `320%` with header **"Margin Ratio"**, no basis stated | `marginRatioPct = equity / maintMargin * 100` — BloFin's own health metric, correctly modeled, but nothing on the UI says higher-is-safer or what 100% would mean (imminent liquidation on this simplified model). | Add the sub-label already used elsewhere in the file (`est. liq price / margin ratio assume a 0.5% maintenance margin rate`) directly next to the number, not just in a footnote most users won't read: `"Margin Ratio 320% (of maintenance requirement; <100% = liquidation zone)"`. |
| 3 | `dashboard/index.html`, stop/target distance (`stopDistPct`, `targetDistPct`, `~line 2260-2261,2301,2304`) | e.g. `"stop 61,200 (-1.20%)"` | This one IS a pure price-move %, computed correctly (`(t.stop - mark) / mark * 100`) and is fine as-is — listed here only so it's not mistaken for the margin-fraction number two columns over in the same row. No change needed beyond the header fix in #1 making the distinction between columns unambiguous by contrast. | (no change needed — included for completeness) |
| 4 | `daily_pick.py:1298-1305,1321-1325` `"conviction {X}%"`, `"risking {risk_pct*100}% of equity"` | Both already explicitly say what they're a percentage OF ("of equity"; conviction is a self-contained score 0-100). | Not ambiguous. Listed to confirm it was checked, not skipped. | No change needed. |
| 5 | `tactical.py:293-294` comment: *"each trigger runs at the max its stop geometry allows under BloFin's ~4.5% liquidation distance at 20x"* | A code comment, not a runtime value — but it's a bare "4.5%" with no PRICE-vs-MARGIN qualifier next to it, and it's the exact kind of number that gets copy-pasted into a Slack message or spoken out loud later without its qualifier. | *"...under BloFin's measured ~4.5% PRICE-move liquidation distance at 20x isolated (100% of margin, by definition, at liquidation) — see BLOFIN_API_REFERENCE.md"* |
| 6 | `news_book.py:37` *"A 1.2% adverse move is thus ~4.8% of equity."* | Already states both sides of the convention correctly (price move first, then equity fraction). | Model example — no change needed, included to show the convention IS achievable and this file already does it. |
| 7 | `bot_pnl.py:39,50` `bot_pnl_pct = (equity - start) / start * 100` | Labeled "BOT PnL" against a stated starting balance (`bot_baseline.json`) — this is account-level ROI since a fixed date, not a per-position screen number, and the basis (`start_equity`) is printed on the line above it. | Not ambiguous by the audit's PRICE-vs-MARGIN definition (it's neither — it's ROI vs a dollar baseline) but worth a one-word tighten for absolute clarity: `"BOT PnL since {start_local}: +3.21% of starting equity"` instead of bare `%`. |

### The single most dangerous finding

**#1/#2/#3 combined (Part 1): `CONTRACT_BTC = 0.001` hardcoded once in
`step5_paper_trade.py` and imported into five other live books, plus
`tactical.py`'s separate hardcoded `SLOTS[...]["contract"]` dict for BTC
and ETH.** Every dollar of real order sizing and every realized-PnL number
booked to `virtual_equity` across all six live books runs through this one
unread-from-the-exchange constant. The values happen to be correct today
(0.001 for BTC matches `BLOFIN_API_REFERENCE.md`'s verified figure), which
is exactly what makes it dangerous rather than obviously broken: nothing
will look wrong until BloFin changes a contract spec, or someone copies
this pattern onto a new symbol without also hand-updating the constant —
at which point every order size and every "realized PnL" printed to the
ledger silently corrupts, with no error, no exception, and no alert. This
is the identical failure shape as the `unrealizedPnlRatio` confusion that
prompted this audit: a number that is confidently reported and quietly
wrong. `daily_pick.py` and `gold_book.py` already prove the fix is cheap
— `demo_feed.get_instrument(symbol)["contractValue"]` — and is a drop-in
replacement for the constant.
