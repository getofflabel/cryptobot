"""
backtest.py — the harness that tells you the truth about a strategy.

THE THREE RULES THIS FILE IS BUILT AROUND

1. NO COST-FREE MODE EXISTS.
   There is no flag to turn costs off. Every simulated trade pays fees,
   crosses the spread, suffers slippage, and pays funding while it holds.
   A cost-free backtest is not a simplification, it is a lie that flatters.

2. NO LOOKAHEAD.
   A signal computed on bar N's close is filled at bar N+1's OPEN.
   You cannot trade a price that had already finished printing by the time
   you saw it. Most "amazing" hobby backtests die right here.

3. EXPECTANCY IS THE METRIC.
   expectancy = (win rate x avg win) - (loss rate x avg loss)
              = the average net dollars you earn per trade taken.
   A 90% win rate with tiny wins and huge losses has NEGATIVE expectancy.
   Win rate is how it feels; expectancy is whether you get paid.

HOW A TRADE FLOWS THROUGH THE ENGINE

  bar N close : strategy sees data up to here, emits target position
  bar N+1 open: we trade to that target at open, ADJUSTED for costs:
                  buying  -> pay open * (1 + (half_spread + slippage)/10^4)
                  selling -> receive open * (1 - (half_spread + slippage)/10^4)
                plus a fee of notional * taker_bps/10^4 on every fill
  while held  : at every 8h funding timestamp (00/08/16 UTC) the position
                pays |notional| * funding_bps/10^4
  round trip  : entry -> exit (or flip) is one TRADE; its net PnL includes
                every cost above. Expectancy averages these net numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config


# ---------------------------------------------------------------------------
# The cost model
# ---------------------------------------------------------------------------


@dataclass
class CostModel:
    """Everything the market charges you, in one auditable place.

    fee_bps        exchange taker fee per fill (BloFin: 6 bps = 0.06%).
                   We assume TAKER (market orders) deliberately: it is the
                   conservative choice, and Step 5's simple executor will
                   use market orders anyway.
    half_spread_bps  crossing the spread costs half the quoted spread per
                   fill (you buy at ask, mid is half a spread below you).
    slippage_bps   how far past the touch your order actually fills.
                   Unknowable in advance, so we charge a conservative flat
                   estimate; Step 5 will MEASURE it for real.
    funding_bps_8h perpetual futures charge funding every 8h. The sign
                   whipsaws with market mood, so we make the conservative
                   choice: ALWAYS pay, never receive. If the strategy only
                   survives by collecting funding, we want it to fail here.
    """

    fee_bps: float = config.fee_bps()                  # 6.0 for BloFin taker
    maker_fee_bps: float = config.fee_bps(maker=True)   # 2.0 for BloFin maker
    half_spread_bps: float = config.DEFAULT_SPREAD_BPS  # 1.0
    slippage_bps: float = config.DEFAULT_SLIPPAGE_BPS   # 2.0
    funding_bps_8h: float = 1.0                         # ~0.01%, typical

    def __post_init__(self):
        # Refuse to exist with costs zeroed out. Rule 1 is enforced, not advised.
        if self.fee_bps <= 0:
            raise ValueError("fee_bps must be > 0. There is no cost-free mode.")

    @property
    def _adverse_frac(self) -> float:
        """Price adjustment per fill: half-spread + slippage, as a fraction."""
        return (self.half_spread_bps + self.slippage_bps) / 10_000

    def fill_price(self, bar_open: float, side: int) -> float:
        """The price you actually transact at. side: +1 buy, -1 sell."""
        return bar_open * (1 + side * self._adverse_frac)

    def fee(self, notional: float) -> float:
        """Exchange fee on one fill, in dollars."""
        return abs(notional) * self.fee_bps / 10_000

    def funding(self, notional: float) -> float:
        """One 8h funding payment on a held position, in dollars. Always a cost."""
        return abs(notional) * self.funding_bps_8h / 10_000

    def round_trip_bps(self) -> float:
        """Total cost of one entry+exit, in bps of notional (excl. funding).
        This is the hurdle every trade must clear before it earns a cent."""
        return 2 * (self.fee_bps + self.half_spread_bps + self.slippage_bps)


# ---------------------------------------------------------------------------
# Results containers
# ---------------------------------------------------------------------------


@dataclass
class Trade:
    """One completed round trip, with every cost already deducted."""

    direction: int              # +1 long, -1 short
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float          # actual fill, costs included
    exit_price: float
    units: float                # position size in base currency (BTC)
    fees: float                 # total exchange fees, both fills
    funding: float              # funding paid while held
    pnl: float                  # NET profit in dollars, after everything

    @property
    def is_win(self) -> bool:
        return self.pnl > 0


@dataclass
class BacktestResult:
    trades: list[Trade]
    equity_curve: pd.Series             # equity at each bar close
    initial_equity: float
    costs: CostModel
    total_fees: float = 0.0
    total_funding: float = 0.0
    total_friction: float = 0.0         # spread+slippage drag in dollars

    # ---- the three numbers Wallace asked for ----

    @property
    def expectancy(self) -> float:
        """Average NET dollars per trade. The number that decides everything."""
        if not self.trades:
            return 0.0
        return float(np.mean([t.pnl for t in self.trades]))

    @property
    def max_drawdown_pct(self) -> float:
        """Worst peak-to-trough fall of the equity curve, as % of the peak.
        This is the pain you must sit through without abandoning the system."""
        eq = self.equity_curve.values
        peaks = np.maximum.accumulate(eq)
        dd = (eq - peaks) / peaks
        return float(dd.min() * 100)

    @property
    def total_return_pct(self) -> float:
        end = float(self.equity_curve.iloc[-1])
        return (end / self.initial_equity - 1) * 100

    # ---- supporting stats ----

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(t.is_win for t in self.trades) / len(self.trades)

    @property
    def avg_win(self) -> float:
        wins = [t.pnl for t in self.trades if t.is_win]
        return float(np.mean(wins)) if wins else 0.0

    @property
    def avg_loss(self) -> float:
        losses = [-t.pnl for t in self.trades if not t.is_win]
        return float(np.mean(losses)) if losses else 0.0

    def report(self, title: str = "BACKTEST RESULT") -> str:
        n = len(self.trades)
        lines = [
            "=" * 64,
            title,
            "=" * 64,
            f"  bars tested        : {len(self.equity_curve)}",
            f"  period             : {self.equity_curve.index[0]:%Y-%m-%d} to "
            f"{self.equity_curve.index[-1]:%Y-%m-%d}",
            f"  trades completed   : {n}",
            "",
            "  AFTER ALL COSTS (there is no other kind of number here):",
            f"  expectancy/trade   : ${self.expectancy:+,.2f}",
            f"  total return       : {self.total_return_pct:+.2f}%",
            f"  max drawdown       : {self.max_drawdown_pct:.2f}%",
            f"  final equity       : ${float(self.equity_curve.iloc[-1]):,.2f} "
            f"(started ${self.initial_equity:,.0f})",
            "",
            "  expectancy decomposed:",
            f"  win rate {self.win_rate * 100:5.1f}% x avg win  ${self.avg_win:8,.2f}   "
            f"= +{self.win_rate * self.avg_win:,.2f}",
            f"  loss rate {(1 - self.win_rate) * 100:4.1f}% x avg loss ${self.avg_loss:8,.2f}   "
            f"= -{(1 - self.win_rate) * self.avg_loss:,.2f}",
            "",
            "  what the market charged you:",
            f"  exchange fees      : ${self.total_fees:,.2f}",
            f"  spread + slippage  : ${self.total_friction:,.2f}",
            f"  funding            : ${self.total_funding:,.2f}",
            f"  cost hurdle        : {self.costs.round_trip_bps():.1f} bps per "
            f"round trip before any profit",
            "=" * 64,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------


def run_backtest(
    candles: pd.DataFrame,
    signal: pd.Series,
    costs: CostModel | None = None,
    initial_equity: float = config.INITIAL_EQUITY,
    size_frac: float = 1.0,
    execution: str = "taker",
    funding_series: pd.Series | None = None,
) -> BacktestResult:
    """Simulate trading `signal` over `candles`, charging full costs.

    candles : DataFrame from exchange.get_candles() — timestamp/open/high/
              low/close/volume, oldest first, closed bars only.
    signal  : one value per bar, aligned to candles' index:
                +1 want to be long, -1 want to be short, 0 want to be flat.
              The value at bar N must be computed from data up to and
              including bar N's CLOSE. The engine handles the rest of the
              no-lookahead discipline by filling at bar N+1's open.
              NaN (e.g. an indicator's warmup period) is treated as 0.
    size_frac : fraction of current equity deployed per position (1.0 = all
              of it, no leverage). Compounds as equity grows or shrinks.
    funding_series : optional REAL funding rates (bps per 8h settlement),
              one value per bar (the most recent settled rate). When given,
              funding becomes a SIGNED cashflow — longs pay positive rates
              and collect negative ones, shorts the reverse — exactly like
              a real perp account. When omitted, the engine keeps its
              conservative default: every held position always PAYS the
              flat rate. (We discovered in round 7 that the conservative
              default is specifically unfair to short strategies that
              enter during high-funding periods, which would really be
              getting paid to hold. This parameter is the honest fix.)
    execution : "taker"  — market orders at next bar's open, full costs.
              "maker"  — post-only limit at the signal bar's CLOSE. It fills
              only if the next bar actually trades through that price
              (buy: bar low <= limit; sell: bar high >= limit), at maker
              fee with NO spread/slippage. If price runs away without
              touching the limit, we CHASE: taker fill at that bar's close,
              full taker costs, typically a worse price. Missed fills are
              the true cost of passive execution and are modeled, not
              wished away.
    """
    if costs is None:
        costs = CostModel()
    if execution not in ("taker", "maker"):
        raise ValueError(f"unknown execution mode {execution!r}")
    if len(candles) != len(signal):
        raise ValueError("signal must have exactly one value per candle")

    # Signals may now be FRACTIONAL: +0.5 means "be long at half size".
    # This is what lets a strategy size with conviction instead of all-or-
    # nothing. -1..0..+1 only; anything outside that range is a bug upstream.
    target = signal.fillna(0).to_numpy(dtype=float)
    if ((target < -1) | (target > 1)).any():
        raise ValueError("signal values must lie in [-1, +1]")

    # Rebalance threshold: resizing an open position pays real fees, so we
    # ignore size drifts smaller than this fraction of full size. Direction
    # changes (including full exits) always trade regardless.
    REBALANCE_MIN = 0.25

    opens = candles["open"].to_numpy()
    highs = candles["high"].to_numpy()
    lows = candles["low"].to_numpy()
    closes = candles["close"].to_numpy()
    times = pd.DatetimeIndex(candles["timestamp"])

    # Funding accrues with TIME HELD, not with bar count. Perpetuals charge
    # every 8 hours, so a 1h bar carries 1/8 of a funding event and a 1d bar
    # carries 3 full events. (The first version charged per timestamp-match,
    # which silently undercharged daily bars 3x — flattering exactly the
    # slow strategies that hold longest.)
    if len(times) > 1:
        bar_hours = (times[1:] - times[:-1]).total_seconds().min() / 3600
    else:
        bar_hours = 1.0
    funding_events_per_bar = bar_hours / config.FUNDING_INTERVAL_HOURS

    if funding_series is not None:
        if len(funding_series) != len(candles):
            raise ValueError("funding_series must have one value per candle")
        real_funding = funding_series.fillna(0).to_numpy()
    else:
        real_funding = None

    cash = initial_equity
    units = 0.0                     # current position in BTC; sign = direction
    equity_curve = np.empty(len(candles))

    trades: list[Trade] = []
    total_fees = total_funding = total_friction = 0.0

    # Open-trade bookkeeping
    t_entry_time = t_entry_price = t_entry_equity = None
    t_fees = t_funding = 0.0

    def execute(i: int, new_units: float):
        """Trade from `units` to `new_units` at bar i's open, paying costs."""
        nonlocal cash, units, total_fees, total_friction
        nonlocal t_entry_time, t_entry_price, t_entry_equity, t_fees, t_funding

        delta = new_units - units
        if delta == 0:
            return
        # Snapshot BEFORE this fill's costs hit. A trade's PnL must be
        # measured from the equity you had walking in, or the entry fee
        # silently vanishes from every trade and expectancy flatters you.
        # (Found by test [2]: a constant-price round trip lost $12 instead
        # of the full $18 hurdle.)
        cash_before = cash
        units_before = units
        side = 1 if delta > 0 else -1

        if execution == "maker" and i > 0:
            # post-only limit at the signal bar's close, working during bar i
            limit = closes[i - 1]
            touched = (lows[i] <= limit) if side > 0 else (highs[i] >= limit)
            if touched:
                price = limit                     # we were the passive side:
                fee = abs(delta) * price * costs.maker_fee_bps / 10_000
                friction = 0.0                    # no spread, no slippage
            else:
                # price ran away — chase with a market order at bar close
                price = closes[i] * (1 + side * costs._adverse_frac)
                fee = costs.fee(abs(delta) * price)
                friction = abs(delta) * abs(price - closes[i])
        else:
            price = costs.fill_price(opens[i], side)
            fee = costs.fee(abs(delta) * price)
            # friction = what spread+slippage cost vs the raw open
            friction = abs(delta) * abs(price - opens[i])

        cash -= delta * price       # buying spends cash, selling raises it
        cash -= fee
        total_fees += fee
        total_friction += friction

        closing = (units != 0) and (new_units == 0 or np.sign(new_units) != np.sign(units))
        opening = (new_units != 0) and (units == 0 or closing)

        if closing:
            # Trade PnL = equity change over the round trip. This automatically
            # includes both fills' fees, friction, and funding paid while held.
            equity_now = cash + new_units * price
            trades.append(Trade(
                direction=int(np.sign(units)),
                entry_time=t_entry_time,
                exit_time=times[i],
                entry_price=t_entry_price,
                exit_price=price,
                units=abs(units),
                fees=t_fees + fee,
                funding=t_funding,
                pnl=equity_now - t_entry_equity,
            ))
            t_entry_time = t_entry_price = t_entry_equity = None
            t_fees = t_funding = 0.0

        if opening:
            t_entry_time = times[i]
            t_entry_price = price
            # Pre-fill equity: cash before paying, plus any position we held
            # walking in (zero in practice — the loop always flattens first).
            t_entry_equity = cash_before + units_before * price
            t_fees = fee
            t_funding = 0.0

        units = new_units

    current_frac = 0.0                  # the fractional target we now hold

    for i in range(len(candles)):
        # 1. Fill yesterday's decision at today's open (Rule 2, no lookahead).
        if i > 0:
            desired = target[i - 1]
            sign_change = np.sign(desired) != np.sign(current_frac)
            resize = (not sign_change
                      and abs(desired - current_frac) >= REBALANCE_MIN)

            if sign_change:
                if current_frac != 0.0:
                    execute(i, 0.0)              # flatten first
                if desired != 0.0:
                    equity_now = cash            # flat, so equity is all cash
                    execute(i, desired * equity_now * size_frac / opens[i])
                current_frac = desired
            elif resize:
                # same direction, meaningfully different size: adjust the
                # position without closing the trade
                equity_now = cash + units * opens[i]
                execute(i, desired * equity_now * size_frac / opens[i])
                current_frac = desired

        # 2. Funding accrues on whatever we hold, in proportion to bar length.
        if units != 0:
            if real_funding is not None:
                # signed: `units * rate` makes longs pay positive rates and
                # shorts RECEIVE them, with no abs() anywhere — the sign
                # falls out of the multiplication, like on a real account
                pay = (units * closes[i] * real_funding[i] / 10_000
                       * funding_events_per_bar)
            else:
                pay = costs.funding(units * closes[i]) * funding_events_per_bar
            cash -= pay
            total_funding += pay
            t_funding += pay

        # 3. Mark to market at the close.
        equity_curve[i] = cash + units * closes[i]

    # Force-close any open position at the final close so its PnL is realized
    # and counted. An unfinished trade you never score is a hidden result.
    if units != 0:
        execute(len(candles) - 1, 0.0)
        equity_curve[-1] = cash

    return BacktestResult(
        trades=trades,
        equity_curve=pd.Series(equity_curve, index=times),
        initial_equity=initial_equity,
        costs=costs,
        total_fees=total_fees,
        total_funding=total_funding,
        total_friction=total_friction,
    )
