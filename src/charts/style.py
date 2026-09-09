"""
Shared look and page furniture for every report page.

A4 landscape, warm off-white ground, team colours carried through every chart.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as _date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mplsoccer import Pitch, VerticalPitch

plt.rcParams.update({
    "font.family": ["Avenir Next", "Helvetica Neue", "Source Sans 3", "DejaVu Sans"],
    "axes.edgecolor": "#C9D1C8",
    "axes.labelcolor": "#4A5A50",
    "xtick.color": "#4A5A50",
    "ytick.color": "#4A5A50",
    "text.color": "#17231C",
})

BG = "#FAFBF8"
INK = "#17231C"
INK2 = "#4A5A50"
INK3 = "#8A968D"
LINE = "#D7DFD8"
PITCH_LINE = "#B9C4BB"
GOLD = "#F2C744"
PAGE = (11.69, 8.27)  # A4 landscape, inches


def tint(colour: str, amount: float = 0.78) -> str:
    """Mix a colour with white. amount=0 -> colour, 1 -> white."""
    r, g, b = to_rgb(colour)
    r, g, b = (c + (1 - c) * amount for c in (r, g, b))
    return f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"


@dataclass
class Team:
    name: str
    colour: str

    @property
    def light(self) -> str:
        return tint(self.colour)


@dataclass
class Ctx:
    """Everything a page needs to know about the match besides the data."""
    home: Team
    away: Team
    home_goals: int | None = None
    away_goals: int | None = None
    date: _date | None = None
    competition: str = ""
    venue: str = ""
    headline: str = ""
    notes: list[tuple[str, str]] = field(default_factory=list)
    source: str = "Data: uploaded match files"

    @property
    def score(self) -> str:
        if self.home_goals is None or self.away_goals is None:
            return "v"
        return f"{self.home_goals} – {self.away_goals}"

    @property
    def date_text(self) -> str:
        return self.date.strftime("%A %d %B %Y") if self.date else ""

    @property
    def subline(self) -> str:
        return "  ·  ".join(p for p in (self.competition, self.date_text, self.venue) if p)


def new_page():
    return plt.figure(figsize=PAGE, facecolor=BG)


def header(fig, ctx: Ctx, title: str, subtitle: str | None = None) -> None:
    fig.text(0.04, 0.955, f"{ctx.home.name} {ctx.score} {ctx.away.name}", fontsize=15, weight="bold", color=INK, va="center")
    fig.text(0.04, 0.925, ctx.subline, fontsize=9, color=INK2, va="center")
    fig.text(0.96, 0.955, title, fontsize=15, weight="bold", color=INK, va="center", ha="right")
    if subtitle:
        fig.text(0.96, 0.925, subtitle, fontsize=9, color=INK2, va="center", ha="right")
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.90, 0.90], color=LINE, lw=0.8))


def footer(fig, ctx: Ctx, n: int) -> None:
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.055, 0.055], color=LINE, lw=0.8))
    fig.text(0.04, 0.035, f"Match Report Generator  ·  {ctx.source}", fontsize=7.5, color=INK3, va="center")
    fig.text(0.96, 0.035, f"Page {n}", fontsize=7.5, color=INK3, va="center", ha="right")


def pitch(vertical: bool = False, half: bool = False):
    cls = VerticalPitch if vertical else Pitch
    return cls(pitch_type="wyscout", half=half, pitch_color=BG, line_color=PITCH_LINE, linewidth=1,
               pad_top=2, pad_bottom=2, pad_left=2, pad_right=2)


def empty_note(ax, text: str) -> None:
    """Shown inside an axes when there is not enough data to draw a chart."""
    ax.axis("off")
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=9, color=INK3, transform=ax.transAxes, wrap=True)
