"""
Assemble the report: decide which pages the uploaded files allow, draw them,
and turn them into PNGs and a PDF. Everything stays in memory.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from src.charts import cover, events as E, network, notes, players, shots, territory
from src.charts.style import BG, Ctx, Team


@dataclass
class Page:
    title: str
    png: bytes


def parse_notes(text: str) -> list[tuple[str, str]]:
    """Lines starting with '#' become headings; the paragraphs under them are the body."""
    out: list[tuple[str, str]] = []
    title, body = "", []
    for line in (text or "").splitlines():
        if line.strip().startswith("#"):
            if body:
                out.append((title, " ".join(body)))
            title, body = line.strip("# ").strip(), []
        elif line.strip():
            body.append(line.strip())
        elif body:
            out.append((title, " ".join(body))); title, body = "", []
    if body:
        out.append((title, " ".join(body)))
    return out


def pages_available(uploads: dict[str, pd.DataFrame]) -> list[str]:
    out = []
    if "team" in uploads or "events" in uploads:
        out.append("Cover and team comparison")
    if "events" in uploads:
        out += ["Shots and xG race", "Pass networks", "Territory and progression"]
    if "player" in uploads:
        out.append("Players and radars")
    out.append("Analyst notes")
    return out


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, facecolor=BG)
    return buf.getvalue()


def build(ctx: Ctx, uploads: dict[str, pd.DataFrame], progress=None) -> tuple[list[Page], bytes]:
    """Draw every page the data allows. Returns (pages as PNG, whole report as PDF).

    `progress(title)` is called before each page is drawn, for a status display.
    """
    steps: list[tuple[str, object]] = []   # (title, callable that draws the page)
    team_df = uploads.get("team")
    if team_df is None and "events" in uploads:
        team_df = E.team_summary(uploads["events"], [ctx.home.name, ctx.away.name])
    if team_df is not None:
        steps.append(("Cover and team comparison", lambda n: cover.page(ctx, team_df, n)))
    if "events" in uploads:
        ev = uploads["events"]
        steps.append(("Shots and xG race", lambda n: shots.page(ctx, ev, n)))
        steps.append(("Pass networks", lambda n: network.page(ctx, ev, n)))
        steps.append(("Territory and progression", lambda n: territory.page(ctx, ev, n)))
    if "player" in uploads:
        steps.append(("Players and radars", lambda n: players.page(ctx, uploads["player"], n)))
    if ctx.notes:
        steps.append(("Analyst notes", lambda n: notes.page(ctx, n)))

    pdf_buf = io.BytesIO()
    pages: list[Page] = []
    meta = {"Title": f"{ctx.home.name} {ctx.score} {ctx.away.name}", "Subject": ctx.subline,
            "Creator": "Match Report Generator", "Author": "Match Report Generator"}
    with PdfPages(pdf_buf, metadata=meta) as pdf:
        for n, (title, draw) in enumerate(steps, start=1):
            if progress:
                progress(title)
            fig = draw(n)
            pdf.savefig(fig, facecolor=BG)
            pages.append(Page(title, _png(fig)))
            plt.close(fig)
    return pages, pdf_buf.getvalue()


def ctx_from_session(match: dict, colours: tuple[str, str], notes_text: str, uploads: dict[str, pd.DataFrame],
                     badges: tuple[bytes | None, bytes | None] = (None, None)) -> Ctx:
    """Build the drawing context from what the user saved on the Upload page."""
    home, away = match.get("home", ""), match.get("away", "")
    if (not home or not away) and uploads:
        first = next(iter(uploads.values()))
        teams = list(first["team"].dropna().unique()) if "team" in first else []
        home = home or (teams[0] if teams else "Home")
        away = away or (teams[1] if len(teams) > 1 else "Away")
    return Ctx(
        home=Team(home, colours[0], badges[0]), away=Team(away, colours[1], badges[1]),
        home_goals=match.get("home_goals"), away_goals=match.get("away_goals"),
        date=match.get("date"), competition=match.get("competition", ""), venue=match.get("venue", ""),
        headline=match.get("headline", ""), notes=parse_notes(notes_text),
        source="Data: " + ", ".join(sorted(uploads)) + " file" + ("s" if len(uploads) > 1 else ""),
    )
