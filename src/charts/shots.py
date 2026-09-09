"""Page: shot maps for both teams and the xG race."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.charts import events as E
from src.charts.style import BG, GOLD, INK, INK3, LINE, Ctx, Team, empty_note, footer, header, new_page, pitch


def shot_map(ax, sh: pd.DataFrame, team: Team) -> None:
    p = pitch(vertical=True, half=True)
    p.draw(ax=ax)
    if sh.empty:
        ax.set_title(f"{team.name}  ·  no shots recorded", fontsize=10, color=team.colour, weight="bold", pad=6)
        return
    miss = sh[~sh.is_goal & ~sh.on_target]
    ont = sh[~sh.is_goal & sh.on_target]
    goal = sh[sh.is_goal]
    size = lambda s: 80 + s.shot_xg * 900
    p.scatter(miss.x, miss.y, s=size(miss), ax=ax, fc="none", ec=team.colour, lw=1.4, alpha=0.8)
    p.scatter(ont.x, ont.y, s=size(ont), ax=ax, fc=team.colour, ec=team.colour, alpha=0.55, lw=1)
    p.scatter(goal.x, goal.y, s=size(goal) * 1.3, ax=ax, fc=GOLD, ec=INK, lw=1.2, marker="*", zorder=5)
    for k, (_, g) in enumerate(goal.iterrows()):
        p.annotate(f"{g.player} {int(g.minute)}'  ({g.shot_xg:.2f} xG)", (g.x, g.y), ax=ax,
                   xytext=(0, 16 if k % 2 == 0 else -18), textcoords="offset points", ha="center", fontsize=7.5,
                   color=INK, weight="bold", bbox=dict(fc="#FFFFFF", ec="none", alpha=0.85, pad=1.5), zorder=6)
    n_goals = int(sh.is_goal.sum())
    ax.set_title(f"{team.name}  ·  {len(sh)} shots, {sh.shot_xg.sum():.2f} xG, {n_goals} goal{'s' if n_goals != 1 else ''}",
                 fontsize=10, color=team.colour, weight="bold", pad=6)


def xg_race(ax, sh_home: pd.DataFrame, sh_away: pd.DataFrame, ctx: Ctx) -> None:
    ax.set_facecolor(BG)
    end = max(95, int(pd.concat([sh_home, sh_away]).minute.max() or 0) + 2) if len(sh_home) + len(sh_away) else 95
    for team, sh in ((ctx.home, sh_home), (ctx.away, sh_away)):
        sh = sh.sort_values("minute")
        m = np.concatenate([[0], sh.minute.values, [end]])
        c = np.concatenate([[0], sh.shot_xg.cumsum().values, [sh.shot_xg.sum()]])
        ax.step(m, c, where="post", color=team.colour, lw=2.2, label=team.name)
        g = sh[sh.is_goal]
        gc = sh.shot_xg.cumsum()[sh.is_goal]
        ax.scatter(g.minute, gc, s=110, marker="*", fc=GOLD, ec=INK, lw=1, zorder=5)
        for mm, cc, pl in zip(g.minute, gc, g.player):
            ax.annotate(f"{pl} {int(mm)}'", (mm, cc), xytext=(4, 6), textcoords="offset points", fontsize=7.5, color=team.colour, weight="bold")
    ax.axvline(45, color=LINE, lw=1, ls="--")
    ax.set_xlim(0, end); ax.set_xticks([t for t in (0, 15, 30, 45, 60, 75, 90, 105, 120) if t <= end])
    ax.set_xlabel("Minute", fontsize=8); ax.set_ylabel("Cumulative xG", fontsize=8)
    ax.tick_params(labelsize=8); ax.grid(axis="y", color=LINE, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("xG race", fontsize=10, weight="bold", loc="left", color=INK)


def page(ctx: Ctx, ev: pd.DataFrame, page_no: int):
    fig = new_page()
    header(fig, ctx, "Shots and expected goals", "Circle size = xG · filled = on target · star = goal")
    sh = E.shots(ev)
    sh_h, sh_a = sh[sh.team == ctx.home.name], sh[sh.team == ctx.away.name]
    ax1 = fig.add_axes([0.06, 0.42, 0.40, 0.43]); shot_map(ax1, sh_h, ctx.home)
    ax2 = fig.add_axes([0.54, 0.42, 0.40, 0.43]); shot_map(ax2, sh_a, ctx.away)
    ax = fig.add_axes([0.08, 0.13, 0.86, 0.24])
    if sh.empty:
        empty_note(ax, "No shots in the events file, so there is no xG race to draw.")
    else:
        xg_race(ax, sh_h, sh_a, ctx)
    footer(fig, ctx, page_no)
    return fig
