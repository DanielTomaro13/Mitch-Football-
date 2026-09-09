"""Page: analyst notes typed into the app."""
from __future__ import annotations

import textwrap

from src.charts.style import INK, Ctx, footer, header, new_page


def page(ctx: Ctx, page_no: int):
    fig = new_page()
    header(fig, ctx, "Analyst notes")
    y = 0.84
    for title, body in ctx.notes[:6]:
        if title:
            fig.text(0.06, y, title.upper(), fontsize=8.5, weight="bold", color=ctx.home.colour)
            y -= 0.03
        wrapped = textwrap.fill(body, 125)
        fig.text(0.06, y, wrapped, fontsize=10, color=INK, va="top", linespacing=1.5)
        y -= 0.04 + 0.032 * (wrapped.count("\n") + 1)
    footer(fig, ctx, page_no)
    return fig
