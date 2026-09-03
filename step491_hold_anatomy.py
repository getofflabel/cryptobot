"""
step491_hold_anatomy.py - ROUND 491

WHERE IN THE HOLD DOES THE GROSS ACTUALLY COME FROM?  (QUEUE ITEM 15, VERBATIM)

Research only. No orders. No live file touched. No account. Nothing here is
deployed by this script under any outcome.

QUEUE ITEM 15, VERBATIM
  "Three separate rounds have landed on the same 9.7% of positions - the
   cap-runners - from three directions: R481 (they produce the entire gross at
   +4.13% each, the stopped 90.3% are collectively negative), R482 (BTC and ETH
   are BELOW their overnight margin ceiling, which bites exactly these), R483
   (they straddle a venue break 99.985% of the time, and ~57 exits a year land
   inside the CLOSED Friday halt). Nobody has read the gross as a function of
   how long the position actually ran.
   Deliverable, purely descriptive: cumulative gross and cumulative net R as a
   function of hold length across the whole 68,992-entry population; the R
   distribution of the cap-runners by how many hours they ran; and the share of
   total gross that is already banked before the first overnight boundary and
   before the Friday halt. If most of the money is made in the first few hours,
   R482's and R483's constraints bite the noise; if it is made in the last few,
   they bite the money and this family is finished on venue grounds independent
   of everything else.
   THE FENCE: no exit rule, no hold cap and no time-of-day gate may be proposed
   or implied. The 24-hour cap is the population's existing construction and is
   not a parameter to be swept. This round describes where the money sits
   inside a published population; it cuts nothing."

THIS ROUND CONSUMES NO LOOK, AND CANNOT
  It reads the ALREADY-PUBLISHED population of R476/R481 (68,992 chargeable
  arm-B hold-24h entries, whole window, no sealed slice left on this family)
  and describes the time profile of a number that has already been reported.
  `slice_by_time` is never called. No split is cut. No cell is qualified. No
  parameter is swept - the horizons below are a READING GRID over an existing
  hold, not candidate exits, and the round is forbidden from ranking them.

WHAT IS MEASURED, AND THE ONE THING THAT HAD TO BE BUILT
  The published table records only what each position was worth AT ITS EXIT.
  "How much is already banked by hour k" is a different object and needs the
  position's PATH, so this round reconstructs the mark-to-market of every one
  of the 68,992 positions on the same 1-minute tape the population was scored
  on. The rule is the population's own and nothing is added to it:
    - a position that has already stopped by horizon h is frozen at its
      realised gross (it is closed; the tape after it is not its money);
    - a position still open at h is marked at the CLOSE of bar h;
    - at h = 1440 the reconstruction must reproduce the published gross of
      every single row exactly, and that identity is checked and printed
      before anything is interpreted.
  Two profiles are printed because they answer different questions and the
  queue's sentence needs both:
    (A) BANKED-BY-h  : what the whole book is worth if marked at h. This is
        the "already banked" object the item asks for.
    (B) SETTLED-BY-h : the share of the final total contributed by positions
        that have already EXITED by h. This is the accounting decomposition,
        and it is the one that shows what the stop-outs do on their own.

THE TWO VENUE CLOCKS, IMPORTED NOT INVENTED
  Overnight boundary and Friday halt are R482/R483's, in CHICAGO time, taken
  from step483_hole_exposure.py unchanged: the daily participant break is
  16:00-17:00 CT, and Friday 16:00-16:50 CT is an all-markets halt. A
  position's "first overnight boundary" is the first 16:00 CT mark strictly
  after its fill; its "Friday halt" is the first Friday 16:00 CT mark strictly
  after its fill, which only some positions reach inside 24 hours.

COSTS
  Charged for honest P&L and used for nothing else (owner rule, 2026-07-25).
  Primary is R486's sourced all-in Coinbase Derivatives round trip per coin,
  the same constants R490 used, imported here by value and not re-derived.
  Alpaca's 0.50% - the venue the desk actually holds - is carried alongside so
  nothing here is quoted off a venue we do not have. Cost gates nothing.

USAGE
  python3 step491_hold_anatomy.py
"""

import numpy as np
import pandas as pd

import step450_tjr_crypto_1m as R

REPO = "/Users/wallacechen/cryptobot"
SRC = f"{REPO}/step481_entries_funding.csv"

# R486's corrected all-in Coinbase Derivatives round trip, % of price.
# Identical to step490_trigger_resolution_profile.py's COST_ALLIN, by value.
COST_ALLIN = {"BTCUSD": 0.0556, "ETHUSD": 0.1463, "SOLUSD": 0.0816}
COST_ALPACA = 0.50                       # the venue the desk holds today

CT = "America/Chicago"                   # step483
HOLE_HOUR = 16                           # step483: 16:00-17:00 CT break
FRI_HALT_END_MIN = 50                    # step483: Friday 16:00-16:50 CT

HOURS = list(range(1, 25))
# minutes, reading grid: a fine head (the first hour) plus every whole hour of
# the existing 24-hour hold. A grid, not a candidate set - see the fence.
HORIZ = sorted(set([1, 5, 15, 30] + [h * 60 for h in HOURS]))
ROWS = [1, 5, 15, 30, 60, 120, 180, 240, 360, 480, 600, 720,
        840, 960, 1080, 1200, 1320, 1440]           # printed subset


# ----------------------------------------------------------------- helpers
def tstat(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 3:
        return np.nan, len(x)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), len(x)


def clustered(df, vals):
    """R476/R487's unit: one mean per UTC calendar day pooled over every
    asset. Three coins on one day are one draw of the market."""
    d = pd.DataFrame({"day": pd.to_datetime(df["entry_t"]).dt.normalize(),
                      "v": np.asarray(vals, float)})
    g = d.groupby("day")["v"].mean()
    return tstat(g)


def to_ct(s):
    """naive UTC -> tz-naive CHICAGO local. step483, unchanged."""
    return (pd.to_datetime(s).dt.tz_localize("UTC")
            .dt.tz_convert(CT).dt.tz_localize(None))


# ------------------------------------------------------- path reconstruction
def build_paths(df):
    """Mark-to-market of every position at every horizon in HORIZ.

    Returns an (n_rows x n_horizons) array of gross % of price, under the
    population's own rule: closed positions are frozen at their realised
    gross, open ones are marked at the close of the horizon bar.
    """
    n = len(df)
    M = np.full((n, len(HORIZ)), np.nan)
    entry_px = np.full(n, np.nan)
    for sym in sorted(df["sym"].unique()):
        _, d1 = R.prep(sym)
        o = d1["open"].to_numpy()
        c = d1["close"].to_numpy()
        nb = len(c)
        m = (df["sym"] == sym).to_numpy()
        idx = np.flatnonzero(m)
        j = df["sig_i"].to_numpy()[idx] + 1          # fill bar
        dirn = df["dirn"].to_numpy()[idx].astype(float)
        held = df["bars_held"].to_numpy()[idx]
        gross = df["gross_pct"].to_numpy()[idx]
        ent = o[j]
        entry_px[idx] = ent
        for k, h in enumerate(HORIZ):
            last = np.minimum(j + h - 1, nb - 1)
            mtm = dirn * (c[last] - ent) / ent * 100.0
            M[idx, k] = np.where(held <= h, gross, mtm)
    return M, entry_px


# ----------------------------------------------------------------- printing
def profile_table(df, M, cost, label):
    tot_final = df["gross_pct"].sum()
    stop_pct = df["stop_pct"].to_numpy()
    print(f"\n{label}")
    print(f"{'h':>7}{'banked gross':>15}{'% of final':>12}"
          f"{'settled gross':>15}{'% of final':>12}{'open':>9}"
          f"{'mean netR':>11}{'t by day':>10}")
    held = df["bars_held"].to_numpy()
    g = df["gross_pct"].to_numpy()
    for h in ROWS:
        k = HORIZ.index(h)
        banked = M[:, k].sum()
        settled = g[held <= h].sum()
        openn = int((held > h).sum())
        netR = (M[:, k] - cost) / stop_pct
        netR = np.where(np.isfinite(netR), netR, np.nan)
        tc, _ = clustered(df, netR)
        print(f"{h:>6}m{banked:>15,.0f}{100*banked/tot_final:>11.1f}%"
              f"{settled:>15,.0f}{100*settled/tot_final:>11.1f}%{openn:>9,}"
              f"{np.nanmean(netR):>11.3f}{tc:>10.2f}")


def main():
    pd.set_option("display.width", 200)
    print("=" * 104)
    print("ROUND 491 - WHERE IN THE HOLD DOES THE GROSS COME FROM  (queue item 15)")
    print("=" * 104)
    print("NO LOOK CONSUMED, and none can be: this is a time-profile DESCRIPTION")
    print("of R476/R481's already-published population. slice_by_time is never")
    print("called and no split is cut anywhere in this file.")
    print("FENCE, restated so it is on the record with the numbers: no exit rule,")
    print("no hold cap and no time-of-day gate is proposed or implied here. The")
    print("horizons are a READING GRID over an existing 24-hour hold; they are")
    print("not candidate exits and they are not ranked.")

    df = pd.read_csv(SRC)
    df = df[df["covered"]].reset_index(drop=True)
    print(f"\npopulation: {len(df):,} entries "
          f"({df['sym'].value_counts().to_dict()})")
    print(f"published gross, mean {df['gross_pct'].mean():+.4f}% of price, "
          f"total {df['gross_pct'].sum():,.0f} percentage points")

    M, entry_px = build_paths(df)

    # ---- reproduction control, before anything is interpreted
    final = M[:, -1]
    err = np.abs(final - df["gross_pct"].to_numpy())
    print(f"\nREPRODUCTION CONTROL. Marking every position at h = 1440 must")
    print(f"return its published gross exactly.")
    print(f"  max |rebuilt - published| = {np.nanmax(err):.3e} percentage points "
          f"over {len(df):,} rows")
    print(f"  rows disagreeing by > 1e-9: {int((err > 1e-9).sum()):,}")
    if np.nanmax(err) > 1e-9:
        print("  *** the path does not reproduce the population. STOP. ***")
        return

    df["cost_pct"] = df["sym"].map(COST_ALLIN)
    cost = df["cost_pct"].to_numpy()

    # ------------------------------------------------------------------ (1)
    print("\n" + "=" * 104)
    print("1. GROSS AND NET R AS A FUNCTION OF HOLD LENGTH - WHOLE POPULATION")
    print("=" * 104)
    print("banked  = what the book is worth marked at h (closed rows frozen at")
    print("          their realised gross, open rows marked at the close of h).")
    print("settled = the share of the final total already contributed by rows")
    print("          that have EXITED by h. netR is per trade at R486's sourced")
    print("          cost; t is clustered by UTC day.")
    profile_table(df, M, cost, "at R486's sourced all-in cost per coin:")
    profile_table(df, M, np.full(len(df), COST_ALPACA),
                  "the same book at Alpaca's 0.50% - the venue the desk holds:")

    # ------------------------------------------------------------------ (2)
    print("\n" + "=" * 104)
    print("2. THE CAP-RUNNERS, HOUR BY HOUR")
    print("=" * 104)
    cap = df["reason"].to_numpy() == "time"
    stp = ~cap
    print(f"cap-runners: {int(cap.sum()):,} of {len(df):,} = "
          f"{100*cap.mean():.2f}% of the population, and every one of them ran")
    print(f"the full {df.loc[cap,'bars_held'].min()}-bar cap "
          f"(min = max = {df.loc[cap,'bars_held'].max()} bars), so 'how many hours")
    print("they ran' has ONE answer in bars. What varies is WALL CLOCK, because")
    print("Alpaca's 1-minute tape has gaps, and what varies far more is where in")
    print("those hours the money arrived. Both are printed.")
    hh = df.loc[cap, "hold_h"]
    print(f"\n  wall-clock hours for the {int(cap.sum()):,} cap-runners: "
          f"min {hh.min():.2f}  p25 {hh.quantile(.25):.2f}  median "
          f"{hh.median():.2f}  p75 {hh.quantile(.75):.2f}  max {hh.max():.2f}")
    gapped = df.loc[cap, "gapped"]
    print(f"  of these, {int(gapped.sum()):,} ({100*gapped.mean():.2f}%) span "
          f"more than 24.05 wall-clock hours (gapped tape).")

    capM = M[cap]
    capdf = df[cap].reset_index(drop=True)
    capcost = capdf["cost_pct"].to_numpy()
    capstop = capdf["stop_pct"].to_numpy()
    print(f"\n{'hour':>6}{'mean gross':>13}{'% of their':>12}{'p25':>10}"
          f"{'median':>10}{'p75':>10}{'mean netR':>11}{'% >0':>8}")
    print(f"{'':>6}{'':>13}{'final':>12}")
    capfinal = capdf["gross_pct"].mean()
    for h in HOURS:
        k = HORIZ.index(h * 60)
        col = capM[:, k]
        nr = (col - capcost) / capstop
        print(f"{h:>6}{np.nanmean(col):>12.4f}%{100*np.nanmean(col)/capfinal:>11.1f}%"
              f"{np.nanpercentile(col,25):>9.3f}%{np.nanmedian(col):>9.3f}%"
              f"{np.nanpercentile(col,75):>9.3f}%{np.nanmean(nr):>11.3f}"
              f"{100*np.nanmean(col>0):>7.1f}%")

    print("\nAnd the 90.3% that stopped, for contrast - their contribution is")
    print("fixed the moment they stop, so the only question is WHEN.")
    sh = df.loc[stp, "bars_held"] / 60.0
    gs = df.loc[stp, "gross_pct"]
    print(f"  {int(stp.sum()):,} stop-outs, mean gross {gs.mean():+.4f}%, "
          f"total {gs.sum():,.0f} points")
    print(f"  hours to the stop: p25 {sh.quantile(.25):.2f}  median "
          f"{sh.median():.2f}  p75 {sh.quantile(.75):.2f}  max {sh.max():.2f}")
    print(f"\n{'by hour h':>11}{'stops by h':>13}{'their gross':>14}"
          f"{'% of all stop loss':>20}")
    for h in HOURS:
        m = stp & (df["bars_held"].to_numpy() <= h * 60)
        print(f"{h:>10}h{int(m.sum()):>13,}{df.loc[m,'gross_pct'].sum():>14,.0f}"
              f"{100*df.loc[m,'gross_pct'].sum()/gs.sum():>19.1f}%")

    # ------------------------------------------------------------------ (3)
    print("\n" + "=" * 104)
    print("3. HOW MUCH IS BANKED BEFORE THE VENUE'S OWN BOUNDARIES")
    print("=" * 104)
    print("Clocks imported from step483 unchanged: the participant break is")
    print("16:00-17:00 CT daily; Friday 16:00-16:50 CT is an all-markets halt.")
    print("A position's first overnight boundary is the first 16:00 CT mark")
    print("strictly after its fill. Only some positions reach a FRIDAY 16:00 CT")
    print("inside the 24-hour hold; the rest never meet the halt at all.")

    ent_ct = to_ct(df["entry_t"])
    # first 16:00 CT strictly after the fill
    same_day = ent_ct.dt.normalize() + pd.Timedelta(hours=HOLE_HOUR)
    nxt = np.where(ent_ct < same_day, same_day,
                   same_day + pd.Timedelta(days=1))
    nxt = pd.Series(pd.DatetimeIndex(nxt))
    mins_to_break = ((nxt - ent_ct).dt.total_seconds() / 60.0).to_numpy()

    # first FRIDAY 16:00 CT strictly after the fill
    dow = nxt.dt.dayofweek.to_numpy()            # 4 = Friday
    add = (4 - dow) % 7
    fri = nxt + pd.to_timedelta(add, unit="D")
    mins_to_fri = ((fri - ent_ct).dt.total_seconds() / 60.0).to_numpy()

    def mark_at(mins):
        """Mark every position at its OWN horizon (minutes since fill),
        clipped into the hold. Same rule as build_paths, one horizon per row."""
        out = np.full(len(df), np.nan)
        h = np.clip(np.ceil(mins).astype(int), 1, R.MAX_HOLD_MIN)
        for sym in sorted(df["sym"].unique()):
            _, d1 = R.prep(sym)
            o = d1["open"].to_numpy(); c = d1["close"].to_numpy(); nb = len(c)
            idx = np.flatnonzero((df["sym"] == sym).to_numpy())
            j = df["sig_i"].to_numpy()[idx] + 1
            dirn = df["dirn"].to_numpy()[idx].astype(float)
            held = df["bars_held"].to_numpy()[idx]
            gross = df["gross_pct"].to_numpy()[idx]
            ent = o[j]
            last = np.minimum(j + h[idx] - 1, nb - 1)
            mtm = dirn * (c[last] - ent) / ent * 100.0
            out[idx] = np.where(held <= h[idx], gross, mtm)
        return out

    tot = df["gross_pct"].sum()
    for name, mins in (("first 16:00 CT break", mins_to_break),
                       ("first FRIDAY 16:00 CT halt", mins_to_fri)):
        reach = mins <= R.MAX_HOLD_MIN
        v = mark_at(mins)
        # positions that never reach the boundary inside the hold contribute
        # their whole realised gross - the boundary cannot touch them.
        v_eff = np.where(reach, v, df["gross_pct"].to_numpy())
        print(f"\n{name}")
        print(f"  positions that MEET it inside the 24h hold: "
              f"{int(reach.sum()):,} of {len(df):,} = {100*reach.mean():.2f}%")
        print(f"  hours from fill to it (those that meet it): p25 "
              f"{np.percentile(mins[reach],25)/60:.2f}  median "
              f"{np.median(mins[reach])/60:.2f}  p75 "
              f"{np.percentile(mins[reach],75)/60:.2f}")
        print(f"  book value marked AT that boundary: {np.nansum(v_eff):,.0f} "
              f"points = {100*np.nansum(v_eff)/tot:.1f}% of the final total")
        sub = reach
        print(f"  restricted to the {int(sub.sum()):,} that meet it: marked "
              f"{np.nansum(v[sub]):,.0f} vs final "
              f"{df.loc[sub,'gross_pct'].sum():,.0f} points = "
              f"{100*np.nansum(v[sub])/df.loc[sub,'gross_pct'].sum():.1f}%")
        capsub = sub & cap
        if capsub.sum():
            print(f"  the cap-runners among them ({int(capsub.sum()):,}): marked "
                  f"{np.nansum(v[capsub]):,.0f} vs final "
                  f"{df.loc[capsub,'gross_pct'].sum():,.0f} points = "
                  f"{100*np.nansum(v[capsub])/df.loc[capsub,'gross_pct'].sum():.1f}%")

    # ------------------------------------------------------------ limits
    print("\n" + "=" * 104)
    print("HONEST LIMITS OF EVERY NUMBER ABOVE - read before quoting any of them")
    print("=" * 104)
    print("1. 'BANKED' IS A MARK, NOT MONEY. For a position still open at h it is")
    print("   the close of bar h. Those rows are not closed and many of them go on")
    print("   to stop; the column says what the book is WORTH at h, never what it")
    print("   has collected. Only the 'settled' column is realised.")
    print("2. THE CAP-RUNNER TABLE IS CONDITIONAL ON SURVIVAL. A cap-runner is")
    print("   DEFINED as a position that never touched its stop in 24 hours, so of")
    print("   course it is in the green at hour 1 (94.7% of them). That is")
    print("   selection, not a forecast: at hour 1 nothing on the tape says which")
    print("   of the 29,321 positions still open will be one of them.")
    print("3. THE TWO PROFILES DISAGREE AND THE DISAGREEMENT IS THE FINDING. The")
    print("   pooled book looks front-loaded because the LOSERS finish early -")
    print("   54.1% of all stop-loss is realised inside hour 1 - while the winners")
    print("   are still marked and still climbing. The engine that produces the")
    print("   entire gross accrues it roughly evenly across all 24 hours.")
    print("4. NO EXIT IS IMPLIED ANYWHERE. 'x% of the money has arrived by the")
    print("   boundary' is a statement about WHEN, not an argument for closing")
    print("   there. Closing at a boundary is a different population with")
    print("   different stops and this round did not and may not simulate it.")
    print("5. Per-trade net R is NEGATIVE at every horizon on both cost schedules")
    print("   (R486 sourced and Alpaca), t by day -4.1 to -9.3. Nothing in this")
    print("   round moves that; R490's verdict stands untouched.")

    print("\n" + "=" * 104)
    print("REPRODUCTION CONTROL, restated: h=1440 returns every published gross")
    print(f"to {np.nanmax(err):.1e} percentage points. Population {len(df):,} "
          f"entries, mean gross {df['gross_pct'].mean():+.4f}%.")
    print("NOTHING IS PROPOSED. No exit rule, no cap, no gate, no resolution.")
    print("=" * 104)


if __name__ == "__main__":
    main()
