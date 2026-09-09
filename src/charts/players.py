"""Page: player tables for both teams and a radar for a standout player each."""
from __future__ import annotations

import numpy as np
import pandas as pd
from mplsoccer import Radar

from src.charts.style import BG, INK2, INK3, LINE, Ctx, Team, empty_note, footer, header, new_page

TABLE_COLS = [  # (field, short header, is float)
    ("player", "Player", False), ("position", "Pos", False), ("minutes", "Min", False), ("goals", "G", False),
    ("xg", "xG", True), ("assists", "A", False), ("xa", "xA", True), ("shots", "Sh", False), ("passes", "Pass", False),
    ("pass_accuracy", "Acc%", False), ("key_passes", "KP", False), ("progressive_passes", "Prog", False),
    ("duels_won_pct", "Duels%", False), ("recoveries", "Rec", False), ("dribbles", "Drb", False),
]
RADAR_PARAMS = [  # (field, label, low value)
    ("xg", "xG", 0), ("shots", "Shots", 0), ("key_passes", "Key passes", 0), ("progressive_passes", "Prog. passes", 0),
    ("pass_accuracy", "Pass acc %", 50), ("duels_won_pct", "Duels won %", 0), ("recoveries", "Recoveries", 0),
    ("dribbles", "Dribbles", 0), ("assists", "Assists", 0), ("xa", "xA", 0),
]


def _sorted(df: pd.DataFrame) -> pd.DataFrame:
    keys = [k for k in ("goals", "xg", "progressive_passes", "minutes") if k in df]
    return df.sort_values(keys, ascending=False) if keys else df


def table(ax, df: pd.DataFrame, team: Team) -> None:
    ax.axis("off")
    cols = [(f, h, fl) for f, h, fl in TABLE_COLS if f in df and df[f].notna().any()]
    d = _sorted(df).head(18)
    cells = []
    for _, r in d.iterrows():
        row = []
        for f, _, fl in cols:
            v = r[f]
            if pd.isna(v):
                row.append("–")
            elif fl:
                row.append(f"{float(v):.2f}")
            elif isinstance(v, (int, float, np.integer, np.floating)):
                row.append(f"{float(v):g}")
            else:
                row.append(str(v))
        cells.append(row)
    other = (1 - 0.22) / max(len(cols) - 1, 1)
    widths = [0.22 if f == "player" else other for f, _, _ in cols]
    tbl = ax.table(cellText=cells, colLabels=[h for _, h, _ in cols], loc="upper left", cellLoc="center", colWidths=widths)
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.2 if len(d) <= 14 else 6.4); tbl.scale(1, 1.25 if len(d) <= 14 else 1.05)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(LINE); cell.set_linewidth(0.5)
        if r == 0:
            cell.set_facecolor(team.colour); cell.get_text().set_color("#FFFFFF"); cell.get_text().set_weight("bold")
        else:
            cell.set_facecolor("#FFFFFF" if r % 2 == 0 else BG)
        if c == 0:
            cell.get_text().set_ha("left"); cell.PAD = 0.05
    ax.set_title(f"{team.name}", fontsize=10, color=team.colour, weight="bold", loc="left", pad=4)


def radar(ax, row: pd.Series, everyone: pd.DataFrame, team: Team) -> None:
    params = [(f, l, lo) for f, l, lo in RADAR_PARAMS if f in everyone and everyone[f].notna().any()][:8]
    if len(params) < 4:
        empty_note(ax, "Radar needs at least four of: xG, shots, key passes, progressive passes, pass accuracy, duels won, recoveries, dribbles.")
        return
    vals = [float(row[f]) if not pd.isna(row[f]) else 0.0 for f, _, _ in params]
    lo = [l for _, _, l in params]
    hi = [max(float(everyone[f].max()), l + 1) if f != "pass_accuracy" else 100 for f, _, l in params]
    r = Radar([l for _, l, _ in params], lo, hi, num_rings=4, ring_width=1, center_circle_radius=1)
    r.setup_axis(ax=ax, facecolor=BG)
    r.draw_circles(ax=ax, facecolor="#FFFFFF", edgecolor=LINE)
    r.draw_radar(vals, ax=ax, kwargs_radar=dict(facecolor=team.colour, alpha=0.55), kwargs_rings=dict(facecolor=team.light, alpha=0.5))
    r.draw_range_labels(ax=ax, fontsize=6, color=INK3)
    r.draw_param_labels(ax=ax, fontsize=7, color=INK2)
    pos = f"  ·  {row['position']}" if "position" in row and not pd.isna(row["position"]) else ""
    mins = f"  ·  {float(row['minutes']):g}'" if "minutes" in row and not pd.isna(row["minutes"]) else ""
    ax.set_title(f"{row['player']}{pos}{mins}", fontsize=9.5, color=team.colour, weight="bold", pad=2)


def _standout(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None
    score = pd.Series(0.0, index=df.index)
    for f, w in (("goals", 3), ("assists", 2), ("xg", 2), ("key_passes", 0.7), ("progressive_passes", 0.4), ("recoveries", 0.2)):
        if f in df:
            score += df[f].fillna(0) * w
    return df.loc[score.idxmax()]


def page(ctx: Ctx, pl: pd.DataFrame, page_no: int):
    fig = new_page()
    header(fig, ctx, "Players", "Sorted by goals, xG, progressive passes · radars scaled to the best value in this match")
    ph, pa = pl[pl.team == ctx.home.name], pl[pl.team == ctx.away.name]
    if ph.empty and pa.empty and pl.team.nunique() >= 2:   # names differ from the form: use file order
        teams = pl.team.unique()
        ph, pa = pl[pl.team == teams[0]], pl[pl.team == teams[1]]
    ax1 = fig.add_axes([0.04, 0.44, 0.60, 0.42]); table(ax1, ph, ctx.home)
    ax2 = fig.add_axes([0.04, 0.02, 0.60, 0.42]); table(ax2, pa, ctx.away)
    for i, (df, team) in enumerate(((ph, ctx.home), (pa, ctx.away))):
        ax = fig.add_axes([0.66, 0.50 - i * 0.41, 0.32, 0.36])
        star = _standout(df)
        if star is None:
            empty_note(ax, f"No players found for {team.name}.")
        else:
            radar(ax, star, pl, team)
    footer(fig, ctx, page_no)
    return fig
