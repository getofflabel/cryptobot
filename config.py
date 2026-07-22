"""
config.py — every project-wide choice lives here, in one place.

Why a config file this early:
The single most common way a hobby trading bot goes wrong is that a setting
gets duplicated. The backtest charges 0.06% fees, the live trader charges
0.05%, and the numbers stop matching. Then you spend a weekend hunting a
"bug" that is really just two files disagreeing.

One file. One truth. Everything imports from here.
"""

from exchange import BlofinExchange, BybitExchange

# ---------------------------------------------------------------------------
# Which exchange are we trading?
# ---------------------------------------------------------------------------
# "blofin" = your venue.
# "bybit"  = a working reference implementation, kept only so development is
#            never blocked by one exchange being unreachable.
#
# Change this ONE string to move the whole project to another exchange.

EXCHANGE = "blofin"

SYMBOL_BY_EXCHANGE = {
    "blofin": "BTC-USDT",     # BloFin writes it with a dash
    "bybit": "BTCUSDT",       # Bybit writes it without
}

TIMEFRAME = "1h"              # canonical name; each adapter translates it


def make_exchange(env: str = "live"):
    """Build the exchange adapter this project is configured for.

    env="live"  -> real market data (used for backtest history)
    env="demo"  -> the paper-trading sandbox (used in Step 5)

    Returns (exchange, symbol) so callers never have to remember which
    naming convention the current venue uses.
    """
    if EXCHANGE == "blofin":
        ex = BlofinExchange(demo=(env == "demo"))
    elif EXCHANGE == "bybit":
        ex = BybitExchange(env="testnet" if env == "demo" else "mainnet")
    else:
        raise ValueError(
            f"EXCHANGE={EXCHANGE!r} is not recognised. "
            f"Options: {list(SYMBOL_BY_EXCHANGE)}"
        )
    return ex, SYMBOL_BY_EXCHANGE[EXCHANGE]


# ---------------------------------------------------------------------------
# Trading costs
# ---------------------------------------------------------------------------
# These are pulled from the exchange adapter so they cannot drift out of sync
# with reality. BloFin publishes 0.02% maker / 0.06% taker for standard
# (non-VIP) accounts on perpetual futures.
#
# We deliberately do NOT make these optional anywhere in the project. There is
# no "run without costs" flag, because a cost-free backtest is not a
# simplification, it is a lie that flatters you.

def fee_bps(maker: bool = False) -> float:
    """Fee in basis points for one side of a trade."""
    cls = {"blofin": BlofinExchange, "bybit": BybitExchange}[EXCHANGE]
    return cls.MAKER_FEE_BPS if maker else cls.TAKER_FEE_BPS


# Conservative defaults for the costs the exchange does not publish.
# We will justify and tune these properly in Step 2.
DEFAULT_SLIPPAGE_BPS = 2.0    # how far past the quote a market order fills
DEFAULT_SPREAD_BPS = 1.0      # assumed half-spread cost, per side

# Perpetual futures charge funding every 8 hours to holders of a position.
# For an hourly strategy that holds for days, this is a real cost, not a
# rounding error. BloFin and Bybit both use an 8-hour interval.
FUNDING_INTERVAL_HOURS = 8


# ---------------------------------------------------------------------------
# Backtest defaults
# ---------------------------------------------------------------------------

INITIAL_EQUITY = 10_000.0     # starting paper balance, in USDT
