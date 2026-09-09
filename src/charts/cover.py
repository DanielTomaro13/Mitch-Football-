"""Page: cover with score, headline, key stats and the team comparison bars."""
from __future__ import annotations

import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from src.charts.style import BG, INK, INK2, INK3, LINE, Ctx, draw_badge, footer, new_page

# (field, label, lower is better)
METRICS = [
    ("xg", "xG", False), ("shots", "Shots", False), ("shots_on_target", "Shots on target", False),
    ("possession", "Possession %", False), ("pass_share", "Pass share %", False), ("field_tilt", "Field tilt %", False),
    ("final_third_share", "Touches in final third %", False),
    ("passes_into_box", "Passes into box", False), ("progressive_passes", "Progressive passes", False),
    ("pass_accuracy", "Pass accuracy %", False), ("xt", "xT", False), ("ppda", "PPDA", True),
    ("high_recoveries", "High recoveries", False), ("crosses", "Crosses", False), ("corners", "Corners", False),
    ("fouls", "Fouls", True),
]
TILE_ORDER = ["xg", "shots", "possession", "pass_share", "field_tilt", "ppda", "xt", "passes_into_box"]


def _rows(team_df: pd.DataFrame, ctx: Ctx) -> tuple[pd.Series | None, pd.Series | None]:
    by = team_df.set_index("team")
    h = by.loc[ctx.home.name] if ctx.home.name in by.index else None
    a = by.loc[ctx.away.name] if ctx.away.name in by.index else None
    if h is None and a is None and len(by) >= 2:   # names in the form differ from the file: fall back to row order
        h, a = by.iloc[0], by.iloc[1]
    return h, a


def _fmt(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    if isinstance(v, float) and v != int(v):
        s = f"{v:.2f}"                      # 2.92 stays 2.92; 9.10 becomes 9.1
        return s[:-1] if s.endswith("0") else s
    return f"{v:g}"


def _tile(fig, x, label, hv, av, ctx):
    ax = fig.add_axes([x, 0.53, 0.176, 0.10]); ax.axis("off")
    ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc="#FFFFFF", ec=LINE, lw=0.8, transform=ax.transAxes))
    ax.text(0.5, 0.78, label.upper(), fontsize=7.5, color=INK3, ha="center", transform=ax.transAxes, weight="bold")
    ax.text(0.28, 0.32, hv, fontsize=15, color=ctx.home.colour, ha="center", transform=ax.transAxes, weight="bold")
    ax.text(0.72, 0.32, av, fontsize=15, color=ctx.away.colour, ha="center", transform=ax.transAxes, weight="bold")
    ax.text(0.5, 0.32, "·", fontsize=15, color=INK3, ha="center", transform=ax.transAxes)


def page(ctx: Ctx, team_df: pd.DataFrame, page_no: int):
    fig = new_page()
    band = fig.add_axes([0.04, 0.70, 0.92, 0.24]); band.axis("off")
    band.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.02", fc="#FFFFFF", ec=LINE, lw=0.8, transform=band.transAxes))
    band.add_patch(FancyBboxPatch((0.0, 0), 0.012, 1, boxstyle="square,pad=0", fc=ctx.home.colour, ec="none", transform=band.transAxes))
    band.add_patch(FancyBboxPatch((0.988, 0), 0.012, 1, boxstyle="square,pad=0", fc=ctx.away.colour, ec="none", transform=band.transAxes))
    band.text(0.05, 0.78, (ctx.competition or "Match report").upper(), fontsize=9, color=INK2, transform=band.transAxes, weight="bold")
    band.text(0.05, 0.66, "  ·  ".join(p for p in (ctx.date_text, ctx.venue) if p), fontsize=9, color=INK3, transform=band.transAxes)
    hsize = 24 if max(len(ctx.home.name), len(ctx.away.name)) <= 18 else 18
    hx, ax_ = 0.05, 0.95
    if ctx.home.badge and draw_badge(band, ctx.home.badge, 0.04, 0.38, height_pt=50, ha="left"):
        hx = 0.125
    if ctx.away.badge and draw_badge(band, ctx.away.badge, 0.96, 0.38, height_pt=50, ha="right"):
        ax_ = 0.875
    band.text(hx, 0.36, ctx.home.name, fontsize=hsize, weight="bold", color=ctx.home.colour, transform=band.transAxes)
    band.text(ax_, 0.36, ctx.away.name, fontsize=hsize, weight="bold", color=ctx.away.colour, transform=band.transAxes, ha="right")
    band.text(0.5, 0.36, ctx.score.replace("–", " – ") if ctx.score != "v" else "v", fontsize=44, weight="bold", color=INK, transform=band.transAxes, ha="center", va="center")
    if ctx.headline:
        fig.text(0.04, 0.655, ctx.headline, fontsize=13, color=INK, style="italic")

    h, a = _rows(team_df, ctx)
    if h is None or a is None:
        fig.text(0.5, 0.35, "Team comparison needs one row per team with matching team names.", ha="center", color=INK3)
        footer(fig, ctx, page_no)
        return fig

    # key stat tiles: first five available
    tiles = []
    for key in TILE_ORDER:
        if key in team_df and not (pd.isna(h[key]) or pd.isna(a[key])):
            label = next(m[1] for m in METRICS if m[0] == key)
            hv, av = _fmt(h[key]), _fmt(a[key])
            if key == "shots" and "shots_on_target" in team_df and not pd.isna(h["shots_on_target"]):
                label, hv, av = "Shots (on target)", f"{h['shots']:g} ({h['shots_on_target']:g})", f"{a['shots']:g} ({a['shots_on_target']:g})"
            tiles.append((label, hv, av))
        if len(tiles) == 5:
            break
    for i, (label, hv, av) in enumerate(tiles):
        _tile(fig, 0.04 + i * 0.186, label, hv, av, ctx)

    # comparison bars
    metrics = [(k, lab, low) for k, lab, low in METRICS if k in team_df and not (pd.isna(h[k]) or pd.isna(a[k]))]
    ax = fig.add_axes([0.10, 0.08, 0.80, 0.42]); ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    n = len(metrics)
    ax.set_xlim(-1.15, 1.15); ax.set_ylim(-0.6, n - 0.4)
    for k, (key, label, lower) in enumerate(reversed(metrics)):
        hv, av = float(h[key]), float(a[key])
        mx = max(abs(hv), abs(av)) or 1
        hw, aw = abs(hv) / mx, abs(av) / mx
        home_better = (hv <= av) if lower else (hv >= av)
        ax.barh(k, -hw, height=0.55, color=ctx.home.colour if home_better else ctx.home.light, left=-0.06)
        ax.barh(k, aw, height=0.55, color=ctx.away.colour if not home_better else ctx.away.light, left=0.06)
        ax.text(0, k, label, ha="center", va="center", fontsize=8.5, color=INK2, bbox=dict(fc=BG, ec="none", pad=1.5))
        ax.text(-0.06 - hw - 0.02, k, _fmt(hv), ha="right", va="center", fontsize=9, color=INK, weight="bold")
        ax.text(0.06 + aw + 0.02, k, _fmt(av), ha="left", va="center", fontsize=9, color=INK, weight="bold")
    ax.text(-1.15, n - 0.1, ctx.home.name, color=ctx.home.colour, fontsize=10, weight="bold", ha="left")
    ax.text(1.15, n - 0.1, ctx.away.name, color=ctx.away.colour, fontsize=10, weight="bold", ha="right")
    note = "Team comparison · darker bar = better on that metric"
    if team_df.attrs.get("derived"):
        note += " · worked out from the events file"
    ax.text(0, n - 0.1, note, color=INK3, fontsize=8, ha="center")
    footer(fig, ctx, page_no)
    return fig
