"""
Helpers that pull shots, passes and touches out of a standardised events frame.

Coordinates are Wyscout style: 0-100 on both axes, each team attacking
towards x = 100 from its own perspective.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BOX_X, BOX_Y0, BOX_Y1 = 84, 19, 81          # opposition penalty area in Wyscout units
PROGRESS_MIN = 15                            # units towards goal for a "progressive" pass


def _lower(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower()


def order(ev: pd.DataFrame) -> pd.DataFrame:
    """Sort by period, minute, second so 'next event' logic works."""
    keys = [k for k in ("period", "minute", "second") if k in ev]
    return ev.sort_values(keys, kind="stable").reset_index(drop=True) if keys else ev


def shots(ev: pd.DataFrame) -> pd.DataFrame:
    t = _lower(ev["type"])
    mask = t.isin(["shot", "penalty"])
    if "secondary" in ev:
        mask |= _lower(ev["secondary"]).str.contains("free_kick_shot|head_shot", na=False)
    if "shot_xg" in ev:
        mask |= ev["shot_xg"].notna()
    out = ev[mask].copy()
    if "shot_xg" not in out:
        out["shot_xg"] = np.nan
    out["shot_xg"] = out["shot_xg"].fillna(0.0)
    for col in ("is_goal", "on_target"):
        if col not in out:
            out[col] = False
        out[col] = out[col].fillna(False).astype(bool)
    return out


def passes(ev: pd.DataFrame) -> pd.DataFrame:
    """Passes with a known end location. Adds `recipient` if it can be inferred."""
    t = _lower(ev["type"])
    mask = t.isin(["pass", "free_kick", "corner", "throw_in", "goal_kick"])
    if "end_x" in ev:
        mask &= ev["end_x"].notna() & ev["end_y"].notna()
    else:
        return ev.iloc[0:0].copy()
    ev = order(ev)
    out = ev[mask].copy()
    if "pass_accurate" not in out:
        out["pass_accurate"] = True
    out["pass_accurate"] = out["pass_accurate"].fillna(False).astype(bool)
    if "recipient" not in out or out["recipient"].replace("", np.nan).isna().all():
        # Infer: the next event by the same team after an accurate pass
        nxt_player = ev.groupby("team")["player"].shift(-1)
        out["recipient"] = nxt_player.loc[out.index].where(out["pass_accurate"])
    out["recipient"] = out["recipient"].replace({"": np.nan, "nan": np.nan, "None": np.nan})
    out["progression"] = out["end_x"] - out["x"]
    return out


def progressive(p: pd.DataFrame) -> pd.DataFrame:
    if "secondary" in p and _lower(p["secondary"]).str.contains("progressive", na=False).any():
        return p[_lower(p["secondary"]).str.contains("progressive", na=False)]
    return p[(p["progression"] >= PROGRESS_MIN) & (p["x"] < BOX_X)]


def into_box(p: pd.DataFrame) -> pd.DataFrame:
    return p[(p["end_x"] >= BOX_X) & p["end_y"].between(BOX_Y0, BOX_Y1) & (p["x"] < BOX_X)]


def touches(ev: pd.DataFrame) -> pd.DataFrame:
    """Every on-ball event with a location."""
    return ev[ev["x"].notna() & ev["y"].notna()]


def team_summary(ev: pd.DataFrame, teams: list[str]) -> pd.DataFrame:
    """A team-summary frame (kind A shape) derived from events, for when no kind A file was uploaded."""
    sh, ps, tc = shots(ev), passes(ev), touches(ev)
    rows = []
    total_passes = max(len(ps), 1)
    for team in teams:
        s, p, t = sh[sh.team == team], ps[ps.team == team], tc[tc.team == team]
        acc = p["pass_accurate"].mean() * 100 if len(p) else np.nan
        rows.append({
            "team": team,
            "xg": round(float(s["shot_xg"].sum()), 2),
            "goals": int(s["is_goal"].sum()),
            "shots": int(len(s)),
            "shots_on_target": int(s["on_target"].sum()),
            "pass_share": round(len(p) / total_passes * 100, 1),
            "passes": int(len(p)),
            "pass_accuracy": round(acc, 1) if not np.isnan(acc) else np.nan,
            "progressive_passes": int(len(progressive(p))),
            "passes_into_box": int(len(into_box(p))),
            "final_third_share": round((t["x"] >= 66.6).mean() * 100, 1) if len(t) else np.nan,
        })
    df = pd.DataFrame(rows)
    other = df.set_index("team")
    df["xga"] = [other.loc[[t for t in teams if t != row.team][0], "xg"] if len(teams) > 1 else np.nan for row in df.itertuples()]
    df["goals_conceded"] = [other.loc[[t for t in teams if t != row.team][0], "goals"] if len(teams) > 1 else np.nan for row in df.itertuples()]
    df.attrs["kind"] = "team"
    df.attrs["derived"] = True
    return df
