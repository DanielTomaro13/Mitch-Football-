"""Page: touch heatmaps and progressive passes for both teams."""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from src.charts import events as E
from src.charts.style import BG, INK3, Ctx, Team, empty_note, footer, header, new_page, pitch


def heatmap(ax, tc: pd.DataFrame, team: Team) -> None:
    p = pitch()
    p.draw(ax=ax)
    if len(tc) < 20:
        empty_note(ax, f"{team.name}: not enough located events for a heatmap.")
        return
    cmap = LinearSegmentedColormap.from_list("t", [BG, team.light, team.colour])
    p.kdeplot(tc.x, tc.y, ax=ax, fill=True, levels=40, thresh=0.02, cmap=cmap, alpha=0.9, zorder=0)
    p.draw(ax=ax)
    thirds = np.histogram(tc.x, bins=[0, 33.3, 66.6, 100.01])[0] / len(tc) * 100
    ax.set_title(f"{team.name} touches  ·  own third {thirds[0]:.0f}%  ·  middle {thirds[1]:.0f}%  ·  final third {thirds[2]:.0f}%",
                 fontsize=9.5, color=team.colour, weight="bold", pad=6)


def progression(ax, ps: pd.DataFrame, team: Team) -> None:
    p = pitch()
    p.draw(ax=ax)
    prog = E.progressive(ps)
    if prog.empty:
        ax.set_title(f"{team.name}  ·  no progressive passes found", fontsize=9, color=team.colour, weight="bold", pad=6)
        return
    ok, ko = prog[prog.pass_accurate], prog[~prog.pass_accurate]
    if len(ok):
        p.arrows(ok.x, ok.y, ok.end_x, ok.end_y, ax=ax, color=team.colour, width=1.6, headwidth=5, headlength=5, alpha=0.9)
    if len(ko):
        p.arrows(ko.x, ko.y, ko.end_x, ko.end_y, ax=ax, color=INK3, width=1.2, headwidth=5, headlength=5, alpha=0.5)
    top = ok.player.value_counts().head(2)
    most = ", ".join(f"{pl} ({n})" for pl, n in top.items())
    ax.set_title(f"{len(ok)} of {len(prog)} progressive passes completed" + (f"  ·  most: {most}" if most else ""),
                 fontsize=9, color=team.colour, weight="bold", pad=6)


def page(ctx: Ctx, ev: pd.DataFrame, page_no: int):
    fig = new_page()
    header(fig, ctx, "Territory and progression", "Touch heatmaps · progressive passes (15+ units towards goal), grey = incomplete")
    tc, ps = E.touches(ev), E.passes(ev)
    for i, team in enumerate((ctx.home, ctx.away)):
        ax = fig.add_axes([0.03 + i * 0.48, 0.49, 0.46, 0.36]); heatmap(ax, tc[tc.team == team.name], team)
        ax = fig.add_axes([0.03 + i * 0.48, 0.09, 0.46, 0.36]); progression(ax, ps[ps.team == team.name], team)
    footer(fig, ctx, page_no)
    return fig
