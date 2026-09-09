"""Page: pass networks for both teams with the most frequent combinations."""
from __future__ import annotations

import pandas as pd

from src.charts import events as E
from src.charts.style import INK, INK3, Ctx, Team, empty_note, footer, header, new_page, pitch

MIN_LINK = 3


def _network(ax, ev_team: pd.DataFrame, ps_team: pd.DataFrame, team: Team, max_players: int = 11) -> pd.DataFrame:
    p = pitch()
    p.draw(ax=ax)
    if ps_team.empty or ps_team["recipient"].isna().all():
        empty_note(ax, f"{team.name}: passes need a recipient (or an ordered events list) to draw a network.")
        return pd.DataFrame()
    # starters ~ the players with the most on-ball events
    counts = ev_team["player"].value_counts()
    keep = counts.head(max_players).index
    pos = ev_team[ev_team.player.isin(keep)].groupby("player")[["x", "y"]].mean()
    made = ps_team[ps_team.player.isin(keep)].groupby("player").size().reindex(pos.index).fillna(0)
    links = (ps_team[ps_team.player.isin(keep) & ps_team.recipient.isin(keep)]
             .groupby(["player", "recipient"]).size().reset_index(name="count"))
    strong = links[links["count"] >= MIN_LINK]
    for _, l in strong.iterrows():
        x0, y0 = pos.loc[l.player]; x1, y1 = pos.loc[l.recipient]
        p.lines(x0, y0, x1, y1, ax=ax, lw=0.6 + l["count"] * 0.45, color=team.colour, alpha=0.35, zorder=1)
    p.scatter(pos.x, pos.y, s=120 + made * 6, ax=ax, fc=team.colour, ec="#FFFFFF", lw=1.5, zorder=3)
    for name, (x, y) in pos.iterrows():
        p.annotate(name, (x, y), ax=ax, xytext=(0, -13), textcoords="offset points", ha="center", fontsize=7, color=INK, weight="bold")
    ax.set_title(f"{team.name}  ·  {int(links['count'].sum())} passes between the {len(pos)} most involved players",
                 fontsize=10, color=team.colour, weight="bold", pad=6)
    return links


def _combos(fig, x, links: pd.DataFrame, team: Team) -> None:
    if links.empty:
        return
    top = links.sort_values("count", ascending=False).head(5)
    fig.text(x, 0.26, "MOST FREQUENT COMBINATIONS", fontsize=7.5, weight="bold", color=team.colour)
    for i, (_, l) in enumerate(top.iterrows()):
        fig.text(x, 0.225 - i * 0.028, f"{l.player}  →  {l.recipient}", fontsize=8.5, color=INK)
        fig.text(x + 0.40, 0.225 - i * 0.028, f"{int(l['count'])}", fontsize=8.5, color=INK, ha="right", weight="bold")


def page(ctx: Ctx, ev: pd.DataFrame, page_no: int):
    fig = new_page()
    header(fig, ctx, "Pass networks", f"Node = average position, size = passes made · line width = passes between pair ({MIN_LINK}+)")
    ps = E.passes(ev)
    tc = E.touches(ev)
    for i, team in enumerate((ctx.home, ctx.away)):
        ax = fig.add_axes([0.03 + i * 0.48, 0.30, 0.46, 0.56])
        links = _network(ax, tc[tc.team == team.name], ps[ps.team == team.name], team)
        _combos(fig, 0.06 + i * 0.48, links, team)
    fig.text(0.5, 0.075, "Both teams shown attacking left to right", fontsize=8, color=INK3, ha="center")
    footer(fig, ctx, page_no)
    return fig
