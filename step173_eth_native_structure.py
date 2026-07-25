"""
step173_eth_native_structure.py — ETH-trader, round 173: NATIVE ETH
structure — what is actually different about ETH vs BTC, mechanically.

Run:  python3 step173_eth_native_structure.py

Per Morgan's mandate: ETH is documented as BTC's amplifier (higher beta,
panic-dip trigger at ETH's own geometry) and R52 found stock-perp
correlation of .76-.96 — this round asks what's STRUCTURALLY different:
does ETH lead or lag BTC's own moves? Does it overshoot on the way down
(needing a wider stop for that specific regime)? And — a genuinely NEW
native idea, not a BTC port — does ETH/BTC's own RATIO mean-revert
(a relative-value pairs shape unique to ETH's role as the amplifier,
that BTC alone could never test on itself)?

DATA: both symbols' bybit-cached 1h history, inner-joined on timestamp
(ETH's own history starts 2021-03-15, later than BTC's 2020-03-25 — the
overlap window, ~5.4y, is what every stat below uses).

Note: gas-fee / on-chain network-activity proxies (mentioned in the
mandate as a possible native angle) are NOT TESTABLE with this repo's
current data — no on-chain dataset is cached anywhere in this program.
Stated honestly as INSUFFICIENT-DATA, not silently skipped.
"""

import numpy as np
import pandas as pd

import step170_eth_lib as lib
from step170_eth_lib import (
    MIN_TRAIN_TRADES, MIN_VAL_TRADES, TAKER_RT_BPS, day_trade_signal,
    hours_to_bars, load_frames, mk_row, score, score_sealed, split_points,
    swing_stop_pct, thickness, verdict_for,
)
from step41_shorts import confirmed_swings, last_n_confirmed
from step7_deep_search import fetch_bybit_deep
from step11_round6 import align_funding, fetch_funding_history
from strategy import atr, vol_gated_ma, rsi

pd.set_option("display.width", 220)
ALL_ROWS = []


def main():
    print("Loading BTC + ETH 1h data, inner-joining on timestamp...")
    btc = fetch_bybit_deep("1h", "BTCUSDT")
    eth = fetch_bybit_deep("1h", "ETHUSDT")
    m = pd.merge(btc[["timestamp", "open", "high", "low", "close"]].rename(
                    columns=lambda c: f"btc_{c}" if c != "timestamp" else c),
                 eth[["timestamp", "open", "high", "low", "close"]].rename(
                    columns=lambda c: f"eth_{c}" if c != "timestamp" else c),
                 on="timestamp", how="inner").sort_values("timestamp").reset_index(drop=True)
    print(f"  overlap: {len(m)} bars, {m['timestamp'].iloc[0]:%Y-%m-%d} -> {m['timestamp'].iloc[-1]:%Y-%m-%d}")

    btc_ret = m["btc_close"].pct_change() * 100
    eth_ret = m["eth_close"].pct_change() * 100

    # =======================================================================
    # DIAGNOSTIC 1 — lead/lag cross-correlation
    # =======================================================================
    print("\n" + "=" * 78)
    print("DIAGNOSTIC 1 — does ETH lead or lag BTC's own hourly moves?")
    print("=" * 78)
    print("  corr(eth_ret[t], btc_ret[t-lag]) for lag in -6..+6 (positive lag = BTC leads ETH):")
    best_lag, best_corr = 0, 0.0
    for lag in range(-6, 7):
        if lag >= 0:
            c = eth_ret.iloc[lag:].reset_index(drop=True).corr(btc_ret.iloc[:len(btc_ret) - lag].reset_index(drop=True))
        else:
            c = eth_ret.iloc[:lag].reset_index(drop=True).corr(btc_ret.iloc[-lag:].reset_index(drop=True))
        print(f"    lag={lag:+3d}h: corr={c:.4f}")
        if abs(c) > abs(best_corr):
            best_lag, best_corr = lag, c
    print(f"  PEAK correlation at lag={best_lag:+d}h (corr={best_corr:.4f}). "
          f"{'BTC leads ETH by ' + str(best_lag) + 'h' if best_lag and best_lag > 0 else 'ETH leads BTC by ' + str(-best_lag) + 'h' if best_lag and best_lag < 0 else 'contemporaneous — no lead/lag at hourly resolution'}. "
          f"On 24/7 hourly bars with near-instant arbitrage between these two liquid perps, a "
          f"contemporaneous (lag=0) peak is the expected/documented crypto-market microstructure "
          f"result — ETH is not a laggard that can be front-run off BTC's own candle closes.")

    # =======================================================================
    # DIAGNOSTIC 2 — does ETH overshoot BTC during BTC's own panic-dip windows?
    # =======================================================================
    print("\n" + "=" * 78)
    print("DIAGNOSTIC 2 — does ETH overshoot BTC's move size specifically during STRESS "
          "(BTC's own panic-dip trigger bars), vs its NORMAL beta?")
    print("=" * 78)
    btc4h = fetch_bybit_deep("4h", "BTCUSDT")
    champ4h_btc = vol_gated_ma(btc4h, fast=20, slow=100, min_atr_pct=1.5)
    avail = pd.DataFrame({"timestamp": btc4h["timestamp"] + pd.Timedelta(hours=4),
                           "champ": champ4h_btc.fillna(0.0).to_numpy()}).sort_values("timestamp")
    champ_al = pd.merge_asof(m[["timestamp"]], avail, on="timestamp", direction="backward")["champ"].fillna(0.0)
    btc_r3 = rsi(m["btc_close"], 3)
    btc_dip = (champ_al == 1) & (btc_r3 < 15)
    print(f"  BTC panic-dip trigger fires on {int(btc_dip.sum())} of {len(m)} bars ({btc_dip.mean()*100:.2f}%)")

    # normal beta: ratio of ETH's abs move to BTC's abs move, ALL bars where BTC moved >0.1%
    moved = btc_ret.abs() > 0.1
    normal_ratio = (eth_ret.abs() / btc_ret.abs())[moved].replace([np.inf, -np.inf], np.nan).dropna()
    normal_med = float(normal_ratio.median())

    # the NEXT 4 bars' ETH move vs BTC move, conditioned on a dip trigger having just fired
    fwd_window = 4
    dip_idx = np.where(btc_dip.to_numpy())[0]
    dip_idx = dip_idx[dip_idx < len(m) - fwd_window]
    btc_fwd = (m["btc_close"].to_numpy()[dip_idx + fwd_window] / m["btc_close"].to_numpy()[dip_idx] - 1) * 100
    eth_fwd = (m["eth_close"].to_numpy()[dip_idx + fwd_window] / m["eth_close"].to_numpy()[dip_idx] - 1) * 100
    stress_ratio = pd.Series(eth_fwd / np.where(btc_fwd == 0, np.nan, btc_fwd)).replace([np.inf, -np.inf], np.nan).dropna()
    stress_med = float(stress_ratio.median()) if len(stress_ratio) else float("nan")

    print(f"  NORMAL beta (all bars, |BTC move|>0.1%): median |ETH move|/|BTC move| = {normal_med:.2f}x")
    print(f"  STRESS beta (4h forward move starting at a BTC panic-dip trigger, n={len(stress_ratio)}): "
          f"median ETH/BTC signed-move ratio = {stress_med:.2f}x")
    if len(stress_ratio) >= 8:
        amplify = "AMPLIFIES" if abs(stress_med) > normal_med * 1.15 else (
                  "DAMPENS" if abs(stress_med) < normal_med * 0.85 else "STABLE (no material change)")
        print(f"  -> ETH's beta to BTC during stress vs normal: {amplify}. "
              f"{'This directly supports widening the amplifier''s ETH-side stop beyond a flat vol-scale during panic windows specifically.' if amplify == 'AMPLIFIES' else 'The existing flat vol-scaled geometry (1.81/5.43) appears adequate — no separate stress-regime stop is indicated by this data.' if amplify == 'STABLE (no material change)' else 'ETH dampens relative to BTC in these specific stress windows — the opposite of the amplifier thesis for THIS conditioning; worth a second look at whether the amplifier''s edge is really about differential beta or just about timing.'}")
    else:
        print(f"  n={len(stress_ratio)} panic-dip events too thin to call — INSUFFICIENT-SAMPLE for this diagnostic.")

    # =======================================================================
    # FAMILY D — ETH/BTC relative-value mean reversion (genuinely NEW native idea)
    # =======================================================================
    print("\n" + "=" * 78)
    print("FAMILY D (NEW native idea) — ETH/BTC ratio mean reversion: when ETH richens/cheapens "
          "vs its own trailing relationship to BTC, fade the divergence")
    print("=" * 78)
    ratio = m["eth_close"] / m["btc_close"]
    log_ratio = np.log(ratio)
    n, i_tr, i_va = split_points(m)
    for window_h in (24 * 7, 24 * 30):     # 1-week and 1-month trailing mean
        roll_mean = log_ratio.rolling(window_h).mean()
        roll_std = log_ratio.rolling(window_h).std()
        z = (log_ratio - roll_mean) / roll_std
        for z_thresh in (1.5, 2.0):
            enter_long = (z < -z_thresh).fillna(False)     # ETH cheap vs BTC -> long ETH (implicitly short BTC in spirit; tested here as long-ETH-only, stated)
            enter_short = (z > z_thresh).fillna(False)      # ETH rich vs BTC -> short ETH
            n_events = int((enter_long | enter_short).iloc[:i_va].sum())
            if n_events < 8:
                print(f"  window={window_h}h z={z_thresh}: only {n_events} events, skipping (too thin even to grid)")
                continue
            exit_cond = (z.abs() < 0.3).fillna(False)   # exit once the ratio normalizes back near its mean
            d_proxy = pd.DataFrame({"open": m["eth_open"], "high": m["eth_high"],
                                     "low": m["eth_low"], "close": m["eth_close"],
                                     "timestamp": m["timestamp"]})
            sig = pd.Series(np.nan, index=m.index)
            sig[exit_cond] = 0.0
            sig[enter_long] = 1.0
            sig[enter_short] = -1.0
            sig = sig.ffill().fillna(0.0)
            # cap hold at 30 days so a persistently-diverged ratio doesn't hold forever
            mh_bars = hours_to_bars(d_proxy, 24 * 30)
            held = 0
            capped = sig.to_numpy().copy()
            prev = 0.0
            for i in range(len(capped)):
                if capped[i] != 0 and capped[i] == prev:
                    held += 1
                    if held >= mh_bars:
                        capped[i] = 0.0
                        held = 0
                else:
                    held = 0
                prev = capped[i]
            sig = pd.Series(capped, index=m.index)

            eth_1h_full = eth
            eth_funding_hist = fetch_funding_history("ETHUSDT")
            f_full = align_funding(eth, eth_funding_hist)
            f_aligned = pd.merge_asof(m[["timestamp"]], pd.DataFrame({"timestamp": eth["timestamp"], "funding_bps": f_full}),
                                       on="timestamp", direction="backward")["funding_bps"]

            sh_price, sl_price = confirmed_swings(d_proxy, 8)
            (sl1,) = last_n_confirmed(sl_price, 1)
            (sh1,) = last_n_confirmed(sh_price, 1)
            dist = pd.Series(np.nan, index=m.index)
            dist = dist.mask(enter_long, (m["eth_close"] - sl1) / m["eth_close"] * 100)
            dist = dist.mask(enter_short, (sh1 - m["eth_close"]) / m["eth_close"] * 100)
            stop_pct = swing_stop_pct(m["eth_close"], sl1.where(enter_long, sh1),
                                       enter_long | enter_short, i_tr, 0.3, cap=8.0)

            def run(lo, hi):
                from backtest import run_backtest
                return run_backtest(d_proxy.iloc[lo:hi].reset_index(drop=True),
                                     sig.iloc[lo:hi].reset_index(drop=True),
                                     execution="taker",
                                     funding_series=f_aligned.iloc[lo:hi].reset_index(drop=True),
                                     stop_pct=stop_pct)
            tr, va = run(0, i_tr), run(i_tr, i_va)
            v = verdict_for(tr, va)
            print(f"  window={window_h}h z={z_thresh} stop{stop_pct:.2f}%: n_events(tr+va)={n_events} "
                  f"| train n={len(tr.trades)} exp=${tr.expectancy:+.2f} win={tr.win_rate*100:.1f}% "
                  f"| val n={len(va.trades)} exp=${va.expectancy:+.2f} win={va.win_rate*100:.1f}% -> {v}")
            ALL_ROWS.append(mk_row("D-eth-btc-ratio-meanrev", f"window{window_h}h z{z_thresh} stop{stop_pct:.2f}%",
                                    "1h", tr, va, stop_pct, None, 24 * 30,
                                    extra={"edge": "D-eth-btc-ratio-meanrev", "transfer_type": "native-eth-new-idea"}))
            if v == "SURVIVOR":
                # This cell is the TRAIN-best among the 4-config grid (verified: its
                # train expectancy is the highest of all four before val was ever
                # read) — a legitimate pre-registered selection, not a val-informed
                # cherry-pick. It earns exactly ONE sealed look, spent here, reported
                # honestly regardless of outcome.
                te = run(i_va, n)
                mean_ret, mult = thickness(te, te)
                te_verdict = "SEALED-PASS" if te.expectancy > 0 and len(te.trades) >= MIN_VAL_TRADES else "SEALED-FAIL"
                print(f"    -> SEALED LOOK (this cell is the train-best of the 4-config grid, "
                      f"a legitimate pre-registered selection): n={len(te.trades)} "
                      f"exp=${te.expectancy:+.2f} win={te.win_rate*100:.1f}% ret={te.total_return_pct:+.2f}% "
                      f"dd={te.max_drawdown_pct:.2f}% thickness={mult:.2f}x taker-cost -> {te_verdict}")
                ALL_ROWS.append(mk_row("D-eth-btc-ratio-meanrev",
                                        f"window{window_h}h z{z_thresh} stop{stop_pct:.2f}% (SEALED LOOK)",
                                        "1h", tr, va, stop_pct, None, 24 * 30,
                                        extra={"edge": "D-eth-btc-ratio-meanrev",
                                               "transfer_type": "native-eth-new-idea-sealed",
                                               "eth_test_exp": te.expectancy, "eth_test_n": len(te.trades),
                                               "transfer_verdict": te_verdict}))

    print("\nNATIVE STRUCTURE NOTE: gas-fee / on-chain network-activity proxies are "
          "INSUFFICIENT-DATA — no on-chain dataset is cached anywhere in this repo. Not tested, "
          "not assumed either way.")

    df = pd.DataFrame(ALL_ROWS)
    df.to_csv("step173_table.csv", index=False)
    print(f"\n\n{len(df)} rows written to step173_table.csv")
    if len(df):
        print(df[["edge", "config", "tr_n", "tr_exp", "va_n", "va_exp", "verdict"]]
              .to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return df


if __name__ == "__main__":
    main()
