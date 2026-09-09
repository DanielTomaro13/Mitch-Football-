"""
Demo: what a finished match report looks like.

Generates a synthetic but realistic match (Wyscout-style coordinates, 0-100 on
both axes, attacking goal at x=100) and renders the report pages the planned
tool will produce: cover + team comparison, shot maps + xG race, pass networks,
territory + progressive passes, player tables + radars, notes.

Outputs a multi-page PDF and one PNG per page into demo/output/.
All data here is invented and labelled as such on every page.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
from mplsoccer import Pitch, VerticalPitch, Radar

OUT = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ styling
plt.rcParams.update({
    "font.family": ["Avenir Next", "Helvetica Neue", "DejaVu Sans"],
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
PAGE = (11.69, 8.27)  # A4 landscape, inches


@dataclass
class Team:
    name: str
    short: str
    colour: str
    colour_light: str
    formation: str


HOME = Team("Sydney FC", "SYD", "#3F8FCC", "#D6E7F5", "4-3-3")
AWAY = Team("Melbourne Victory", "MVC", "#1B2A4A", "#D9DDE6", "4-2-3-1")
MATCH = dict(
    competition="A-League Men · Round 7",
    date="Saturday 22 November 2026",
    venue="Allianz Stadium",
    score_home=2,
    score_away=1,
    ht="1-0 at half time",
    headline="Sydney win the xG battle and hold on after a nervy last twenty minutes",
)

rng = np.random.default_rng(7)

# ------------------------------------------------------------------ synthetic data
HOME_XI = [
    ("Redmayne", "GK", 6, 50), ("Grant", "RB", 26, 18), ("Rodwell", "CB", 22, 38),
    ("Burgess", "CB", 22, 62), ("Girdwood-Reich", "LB", 27, 84), ("Caceres", "CM", 44, 50),
    ("Lolley", "RM", 56, 26), ("Kucharski", "LM", 55, 72), ("Segecic", "RW", 74, 20),
    ("Teague", "ST", 80, 50), ("Brattan", "LW", 73, 80),
]
AWAY_XI = [
    ("Izzo", "GK", 6, 50), ("Vidosic", "RB", 24, 18), ("Geria", "CB", 20, 38),
    ("Roderick", "CB", 20, 62), ("Neyder", "LB", 26, 84), ("Arslan", "DM", 40, 40),
    ("Brimmer", "DM", 40, 62), ("Rojas", "RW", 62, 22), ("Bacus", "AM", 60, 50),
    ("Kalifa", "LW", 62, 78), ("Chiba", "ST", 78, 50),
]


def make_players(xi, team, strength):
    rows = []
    for name, pos, x, y in xi:
        mins = 90 if rng.random() > 0.3 else int(rng.integers(58, 84))
        passes = int(rng.integers(18, 70) * (1.15 if pos in ("CM", "DM", "CB", "AM") else 0.9))
        acc = np.clip(rng.normal(0.84 if pos != "GK" else 0.72, 0.06), 0.55, 0.97)
        rows.append(dict(
            Player=name, Team=team.name, Pos=pos, Min=mins,
            Passes=passes, PassAcc=round(acc * 100),
            KeyPasses=int(rng.poisson(1.1 if pos in ("AM", "RW", "LW", "CM") else 0.4)),
            ProgPasses=int(rng.poisson(3.5 if pos in ("CM", "DM", "CB", "AM") else 1.8)),
            Duels=int(rng.integers(4, 16)),
            DuelsWon=0, Recoveries=int(rng.poisson(5 if pos in ("CB", "DM", "CM", "RB", "LB") else 2.5)),
            xG=0.0, Shots=0, Goals=0, Assists=0, avg_x=x, avg_y=y,
        ))
    df = pd.DataFrame(rows)
    df["DuelsWon"] = (df["Duels"] * np.clip(rng.normal(0.52 + strength, 0.1, len(df)), 0.2, 0.85)).round().astype(int)
    return df


home_players = make_players(HOME_XI, HOME, 0.03)
away_players = make_players(AWAY_XI, AWAY, -0.02)


def make_shots(team, players, n, goals_at):
    """Shots in attacking coordinates for `team` (goal at x=100)."""
    attackers = players[players.Pos.isin(["ST", "RW", "LW", "AM", "CM", "RM", "LM"])]
    shots = []
    for i in range(n):
        x = np.clip(rng.normal(87, 6), 68, 98.5)
        y = np.clip(rng.normal(50, 12), 18, 82)
        dist = np.hypot(100 - x, (50 - y) * 0.68)
        xg = float(np.clip(0.9 * np.exp(-dist / 9) + rng.normal(0, 0.03), 0.02, 0.78))
        shots.append(dict(team=team.name, player=attackers.sample(1, random_state=int(rng.integers(1e9))).Player.iloc[0],
                          minute=int(rng.integers(2, 93)), x=x, y=y, xG=round(xg, 2),
                          on_target=bool(rng.random() < 0.45), goal=False))
    shots = pd.DataFrame(shots).sort_values("minute").reset_index(drop=True)
    # Replace a few shots with the actual goals (scorer, minute, position, xG)
    for idx, (scorer, minute, gx, gy, gxg) in enumerate(goals_at):
        k = shots.index[idx * 3 % len(shots)]
        shots.loc[k, ["player", "minute", "x", "y", "xG"]] = [scorer, minute, gx, gy, gxg]
        shots.loc[k, ["goal", "on_target"]] = [True, True]
    return shots.sort_values("minute").reset_index(drop=True)


home_shots = make_shots(HOME, home_players, 14, goals_at=[("Teague", 31, 91.5, 46, 0.34), ("Teague", 67, 86, 60, 0.28)])
away_shots = make_shots(AWAY, away_players, 9, goals_at=[("Bacus", 74, 89, 42, 0.21)])

for shots, players in ((home_shots, home_players), (away_shots, away_players)):
    agg = shots.groupby("player").agg(xG=("xG", "sum"), Shots=("xG", "size"), Goals=("goal", "sum"))
    for p, r in agg.iterrows():
        m = players.Player == p
        players.loc[m, "xG"] = round(r.xG, 2)
        players.loc[m, "Shots"] = int(r.Shots)
        players.loc[m, "Goals"] = int(r.Goals)
# assists: give to a creative teammate
home_players.loc[home_players.Player == "Caceres", "Assists"] = 1
home_players.loc[home_players.Player == "Segecic", "Assists"] = 1
away_players.loc[away_players.Player == "Bacus", "Assists"] = 1


def make_pass_links(players, total_passes):
    """Pass counts between starters, weighted by proximity."""
    names = players.Player.tolist()
    xs, ys = players.avg_x.values, players.avg_y.values
    links = []
    for i, a in enumerate(names):
        for j, b in enumerate(names):
            if i == j:
                continue
            d = np.hypot(xs[i] - xs[j], (ys[i] - ys[j]) * 0.7)
            w = np.exp(-d / 18)
            links.append((a, b, w))
    links = pd.DataFrame(links, columns=["passer", "receiver", "w"])
    links["count"] = rng.poisson(links.w / links.w.sum() * total_passes * 0.55)
    return links[links["count"] > 0]


home_links = make_pass_links(home_players, 470)
away_links = make_pass_links(away_players, 360)


def make_touches(players, n, bias):
    """Touch locations for territory heatmap (attacking coordinates)."""
    idx = rng.integers(0, len(players), n)
    x = np.clip(players.avg_x.values[idx] + rng.normal(bias, 14, n), 1, 99)
    y = np.clip(players.avg_y.values[idx] + rng.normal(0, 13, n), 1, 99)
    return x, y


home_touch = make_touches(home_players, 650, 4)
away_touch = make_touches(away_players, 520, -2)


def make_prog_passes(players, n):
    passers = players[players.Pos.isin(["CB", "CM", "DM", "RB", "LB", "AM"])]
    rows = []
    for _ in range(n):
        p = passers.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
        x0 = np.clip(p.avg_x + rng.normal(0, 8), 10, 70)
        y0 = np.clip(p.avg_y + rng.normal(0, 10), 5, 95)
        x1 = np.clip(x0 + rng.uniform(15, 35), 30, 96)
        y1 = np.clip(y0 + rng.normal(0, 14), 5, 95)
        rows.append(dict(player=p.Player, x=x0, y=y0, end_x=x1, end_y=y1, accurate=rng.random() < 0.72))
    return pd.DataFrame(rows)


home_prog = make_prog_passes(home_players, 34)
away_prog = make_prog_passes(away_players, 24)

TEAM_STATS = pd.DataFrame({
    "metric": ["xG", "Shots", "Shots on target", "Possession %", "Field tilt %", "Passes into box",
               "xT", "PPDA", "High recoveries", "Crosses", "Corners", "Fouls"],
    HOME.name: [round(home_shots.xG.sum(), 2), len(home_shots), int(home_shots.on_target.sum()), 56, 61, 14,
                1.42, 9.1, 8, 17, 6, 11],
    AWAY.name: [round(away_shots.xG.sum(), 2), len(away_shots), int(away_shots.on_target.sum()), 44, 39, 8,
                0.96, 13.4, 4, 11, 3, 14],
})
LOWER_IS_BETTER = {"PPDA", "Fouls"}


# ------------------------------------------------------------------ page furniture
def new_page():
    fig = plt.figure(figsize=PAGE, facecolor=BG)
    return fig


def header(fig, title, subtitle=None):
    """Compact match header used on every page after the cover."""
    fig.text(0.04, 0.955, f"{HOME.name} {MATCH['score_home']} – {MATCH['score_away']} {AWAY.name}",
             fontsize=15, weight="bold", color=INK, va="center")
    fig.text(0.04, 0.925, f"{MATCH['competition']}  ·  {MATCH['date']}", fontsize=9, color=INK2, va="center")
    fig.text(0.96, 0.955, title, fontsize=15, weight="bold", color=INK, va="center", ha="right")
    if subtitle:
        fig.text(0.96, 0.925, subtitle, fontsize=9, color=INK2, va="center", ha="right")
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.90, 0.90], color=LINE, lw=0.8))


def footer(fig, n):
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.055, 0.055], color=LINE, lw=0.8))
    fig.text(0.04, 0.035, "Match Report Generator · DEMO with synthetic data · Wyscout-style event model",
             fontsize=7.5, color=INK3, va="center")
    fig.text(0.96, 0.035, f"Page {n}", fontsize=7.5, color=INK3, va="center", ha="right")


def team_pitch(vertical=False, half=False):
    cls = VerticalPitch if vertical else Pitch
    return cls(pitch_type="wyscout", half=half, pitch_color=BG, line_color=PITCH_LINE, linewidth=1,
               pad_top=2, pad_bottom=2, pad_left=2, pad_right=2)


# ------------------------------------------------------------------ page 1: cover + comparison
def page_cover(pdf):
    fig = new_page()
    # score band
    band = fig.add_axes([0.04, 0.70, 0.92, 0.24]); band.axis("off")
    band.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.02",
                                  fc="#FFFFFF", ec=LINE, lw=0.8, transform=band.transAxes))
    band.add_patch(plt.Rectangle((0.0, 0), 0.012, 1, fc=HOME.colour, transform=band.transAxes))
    band.add_patch(plt.Rectangle((0.988, 0), 0.012, 1, fc=AWAY.colour, transform=band.transAxes))
    band.text(0.05, 0.78, MATCH["competition"].upper(), fontsize=9, color=INK2, transform=band.transAxes, weight="bold")
    band.text(0.05, 0.66, f"{MATCH['date']}  ·  {MATCH['venue']}", fontsize=9, color=INK3, transform=band.transAxes)
    band.text(0.05, 0.36, HOME.name, fontsize=24, weight="bold", color=HOME.colour, transform=band.transAxes)
    band.text(0.95, 0.36, AWAY.name, fontsize=24, weight="bold", color=AWAY.colour, transform=band.transAxes, ha="right")
    band.text(0.5, 0.36, f"{MATCH['score_home']}  –  {MATCH['score_away']}", fontsize=44, weight="bold",
              color=INK, transform=band.transAxes, ha="center", va="center")
    band.text(0.5, 0.10, MATCH["ht"], fontsize=9, color=INK3, transform=band.transAxes, ha="center")
    band.text(0.05, 0.12, f"{HOME.formation}", fontsize=10, color=INK2, transform=band.transAxes)
    band.text(0.95, 0.12, f"{AWAY.formation}", fontsize=10, color=INK2, transform=band.transAxes, ha="right")

    fig.text(0.04, 0.655, MATCH["headline"], fontsize=13, color=INK, style="italic")

    # key stat tiles
    tiles = [("xG", f"{TEAM_STATS.iloc[0, 1]:.2f}", f"{TEAM_STATS.iloc[0, 2]:.2f}"),
             ("Shots (on target)", f"{int(TEAM_STATS.iloc[1, 1])} ({int(TEAM_STATS.iloc[2, 1])})", f"{int(TEAM_STATS.iloc[1, 2])} ({int(TEAM_STATS.iloc[2, 2])})"),
             ("Possession", "56%", "44%"), ("Field tilt", "61%", "39%"), ("PPDA", "9.1", "13.4")]
    for i, (lab, h, a) in enumerate(tiles):
        ax = fig.add_axes([0.04 + i * 0.186, 0.53, 0.176, 0.10]); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0,rounding_size=0.04", fc="#FFFFFF", ec=LINE, lw=0.8, transform=ax.transAxes))
        ax.text(0.5, 0.78, lab.upper(), fontsize=7.5, color=INK3, ha="center", transform=ax.transAxes, weight="bold")
        ax.text(0.28, 0.32, h, fontsize=15, color=HOME.colour, ha="center", transform=ax.transAxes, weight="bold")
        ax.text(0.72, 0.32, a, fontsize=15, color=AWAY.colour, ha="center", transform=ax.transAxes, weight="bold")
        ax.text(0.5, 0.32, "·", fontsize=15, color=INK3, ha="center", transform=ax.transAxes)

    # comparison butterfly
    ax = fig.add_axes([0.10, 0.08, 0.80, 0.42])
    ax.set_facecolor(BG)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks([]); ax.set_yticks([])
    metrics = TEAM_STATS.iloc[::-1]
    ymax = len(metrics)
    ax.set_xlim(-1.15, 1.15); ax.set_ylim(-0.6, ymax - 0.4)
    for k, (_, r) in enumerate(metrics.iterrows()):
        h, a = r[HOME.name], r[AWAY.name]
        mx = max(h, a) or 1
        hw, aw = h / mx, a / mx
        hb = r.metric not in LOWER_IS_BETTER and h >= a or r.metric in LOWER_IS_BETTER and h <= a
        ax.barh(k, -hw, height=0.55, color=HOME.colour if hb else HOME.colour_light, left=-0.06)
        ax.barh(k, aw, height=0.55, color=AWAY.colour if not hb else AWAY.colour_light, left=0.06)
        ax.text(0, k, r.metric, ha="center", va="center", fontsize=8.5, color=INK2,
                bbox=dict(fc=BG, ec="none", pad=1.5))
        ax.text(-0.06 - hw - 0.02, k, f"{h:g}", ha="right", va="center", fontsize=9, color=INK, weight="bold")
        ax.text(0.06 + aw + 0.02, k, f"{a:g}", ha="left", va="center", fontsize=9, color=INK, weight="bold")
    ax.text(-1.15, ymax - 0.1, HOME.name, color=HOME.colour, fontsize=10, weight="bold", ha="left")
    ax.text(1.15, ymax - 0.1, AWAY.name, color=AWAY.colour, fontsize=10, weight="bold", ha="right")
    ax.text(0, ymax - 0.1, "Team comparison · darker bar = better on that metric", color=INK3, fontsize=8, ha="center")
    footer(fig, 1)
    save(pdf, fig, "01_cover_team_comparison")


# ------------------------------------------------------------------ page 2: shot maps + xG race
def shot_map(ax, shots, team):
    pitch = team_pitch(vertical=True, half=True)
    pitch.draw(ax=ax)
    miss = shots[~shots.goal & ~shots.on_target]
    ont = shots[~shots.goal & shots.on_target]
    goal = shots[shots.goal]
    size = lambda s: 80 + s.xG * 900
    pitch.scatter(miss.x, miss.y, s=size(miss), ax=ax, fc="none", ec=team.colour, lw=1.4, alpha=0.8)
    pitch.scatter(ont.x, ont.y, s=size(ont), ax=ax, fc=team.colour, ec=team.colour, alpha=0.55, lw=1)
    pitch.scatter(goal.x, goal.y, s=size(goal) * 1.3, ax=ax, fc="#F2C744", ec=INK, lw=1.2, marker="*", zorder=5)
    for k, (_, g) in enumerate(goal.iterrows()):
        pitch.annotate(f"{g.player} {g.minute}'  ({g.xG:.2f} xG)", (g.x, g.y), ax=ax, xytext=(0, 16 if k % 2 == 0 else -18),
                       textcoords="offset points", ha="center", fontsize=7.5, color=INK, weight="bold",
                       bbox=dict(fc="#FFFFFF", ec="none", alpha=0.85, pad=1.5), zorder=6)
    n_goals = int(shots.goal.sum())
    ax.set_title(f"{team.name}  ·  {len(shots)} shots, {shots.xG.sum():.2f} xG, {n_goals} goal{'s' if n_goals != 1 else ''}",
                 fontsize=10, color=team.colour, weight="bold", pad=6)


def page_shots(pdf):
    fig = new_page()
    header(fig, "Shots and expected goals", "Circle size = xG · filled = on target · star = goal")
    ax1 = fig.add_axes([0.06, 0.42, 0.40, 0.43]); shot_map(ax1, home_shots, HOME)
    ax2 = fig.add_axes([0.54, 0.42, 0.40, 0.43]); shot_map(ax2, away_shots, AWAY)

    ax = fig.add_axes([0.08, 0.13, 0.86, 0.24]); ax.set_facecolor(BG)
    for team, shots in ((HOME, home_shots), (AWAY, away_shots)):
        m = np.concatenate([[0], shots.minute.values, [95]])
        c = np.concatenate([[0], shots.xG.cumsum().values, [shots.xG.sum()]])
        ax.step(m, c, where="post", color=team.colour, lw=2.2, label=team.name)
        g = shots[shots.goal]
        gc = shots.xG.cumsum()[shots.goal]
        ax.scatter(g.minute, gc, s=110, marker="*", fc="#F2C744", ec=INK, lw=1, zorder=5)
        for mm, cc, p in zip(g.minute, gc, g.player):
            ax.annotate(f"{p} {mm}'", (mm, cc), xytext=(4, 6), textcoords="offset points", fontsize=7.5, color=team.colour, weight="bold")
    ax.axvline(45, color=LINE, lw=1, ls="--"); ax.text(45.5, ax.get_ylim()[1] * 0.02, "HT", fontsize=7, color=INK3)
    ax.set_xlim(0, 95); ax.set_xticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_xlabel("Minute", fontsize=8); ax.set_ylabel("Cumulative xG", fontsize=8)
    ax.tick_params(labelsize=8); ax.grid(axis="y", color=LINE, lw=0.6)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    ax.set_title("xG race", fontsize=10, weight="bold", loc="left", color=INK)
    footer(fig, 2)
    save(pdf, fig, "02_shot_maps_xg_race")


# ------------------------------------------------------------------ page 3: pass networks
def pass_network(ax, players, links, team, min_count=3):
    pitch = team_pitch()
    pitch.draw(ax=ax)
    pos = players.set_index("Player")[["avg_x", "avg_y"]]
    touches = players.set_index("Player").Passes
    strong = links[links["count"] >= min_count]
    for _, l in strong.iterrows():
        x0, y0 = pos.loc[l.passer]; x1, y1 = pos.loc[l.receiver]
        pitch.lines(x0, y0, x1, y1, ax=ax, lw=0.6 + l["count"] * 0.45, color=team.colour, alpha=0.35, zorder=1)
    pitch.scatter(pos.avg_x, pos.avg_y, s=120 + touches.loc[pos.index] * 6, ax=ax, fc=team.colour, ec="#FFFFFF", lw=1.5, zorder=3)
    for name, (x, y) in pos.iterrows():
        pitch.annotate(name, (x, y), ax=ax, xytext=(0, -13), textcoords="offset points", ha="center", fontsize=7, color=INK, weight="bold")
    ax.set_title(f"{team.name}  ·  {team.formation}  ·  {int(links['count'].sum())} passes between starters",
                 fontsize=10, color=team.colour, weight="bold", pad=6)


def combos_text(fig, x, links, team):
    top = links.sort_values("count", ascending=False).head(5)
    fig.text(x, 0.26, "MOST FREQUENT COMBINATIONS", fontsize=7.5, weight="bold", color=team.colour)
    for i, (_, l) in enumerate(top.iterrows()):
        fig.text(x, 0.225 - i * 0.028, f"{l.passer}  →  {l.receiver}", fontsize=8.5, color=INK)
        fig.text(x + 0.40, 0.225 - i * 0.028, f"{int(l['count'])}", fontsize=8.5, color=INK, ha="right", weight="bold")


def page_networks(pdf):
    fig = new_page()
    header(fig, "Pass networks", "Node = average position, size = passes made · line width = passes between pair (3+)")
    ax1 = fig.add_axes([0.03, 0.30, 0.46, 0.56]); pass_network(ax1, home_players, home_links, HOME)
    ax2 = fig.add_axes([0.51, 0.30, 0.46, 0.56]); pass_network(ax2, away_players, away_links, AWAY)
    combos_text(fig, 0.06, home_links, HOME)
    combos_text(fig, 0.54, away_links, AWAY)
    fig.text(0.5, 0.075, "Both teams shown attacking left to right", fontsize=8, color=INK3, ha="center")
    footer(fig, 3)
    save(pdf, fig, "03_pass_networks")


# ------------------------------------------------------------------ page 4: territory + progressive passes
def page_territory(pdf):
    fig = new_page()
    header(fig, "Territory and progression", "Touch heatmaps · progressive passes (15m+ towards goal)")
    from matplotlib.colors import LinearSegmentedColormap
    for i, (team, touch, prog) in enumerate(((HOME, home_touch, home_prog), (AWAY, away_touch, away_prog))):
        cmap = LinearSegmentedColormap.from_list("t", [BG, team.colour_light, team.colour])
        ax = fig.add_axes([0.03 + i * 0.48, 0.49, 0.46, 0.36])
        pitch = team_pitch(); pitch.draw(ax=ax)
        pitch.kdeplot(touch[0], touch[1], ax=ax, fill=True, levels=40, thresh=0.02, cmap=cmap, alpha=0.9, zorder=0)
        pitch.draw(ax=ax)  # redraw lines on top
        thirds = np.histogram(touch[0], bins=[0, 33.3, 66.6, 100])[0] / len(touch[0]) * 100
        ax.set_title(f"{team.name} touches  ·  own third {thirds[0]:.0f}%  ·  middle {thirds[1]:.0f}%  ·  final third {thirds[2]:.0f}%",
                     fontsize=9.5, color=team.colour, weight="bold", pad=6)

        ax = fig.add_axes([0.03 + i * 0.48, 0.09, 0.46, 0.36])
        pitch = team_pitch(); pitch.draw(ax=ax)
        ok, ko = prog[prog.accurate], prog[~prog.accurate]
        pitch.arrows(ok.x, ok.y, ok.end_x, ok.end_y, ax=ax, color=team.colour, width=1.6, headwidth=5, headlength=5, alpha=0.9)
        pitch.arrows(ko.x, ko.y, ko.end_x, ko.end_y, ax=ax, color=INK3, width=1.2, headwidth=5, headlength=5, alpha=0.5)
        top = prog[prog.accurate].player.value_counts().head(2)
        ax.set_title(f"{len(ok)} of {len(prog)} progressive passes completed  ·  most: {', '.join(f'{p} ({n})' for p, n in top.items())}",
                     fontsize=9, color=team.colour, weight="bold", pad=6)
    footer(fig, 4)
    save(pdf, fig, "04_territory_progression")


# ------------------------------------------------------------------ page 5: players + radars
def player_table(ax, players, team):
    ax.axis("off")
    cols = ["Player", "Pos", "Min", "Goals", "xG", "Assists", "Shots", "Passes", "PassAcc", "KeyPasses", "ProgPasses", "DuelsWon", "Recoveries"]
    labels = ["Player", "Pos", "Min", "G", "xG", "A", "Sh", "Pass", "Acc%", "KP", "Prog", "Duels W", "Rec"]
    df = players.sort_values(["Goals", "xG", "ProgPasses"], ascending=False)[cols]
    df = df.assign(DuelsWon=[f"{w}/{d}" for w, d in zip(players.loc[df.index].DuelsWon, players.loc[df.index].Duels)])
    cell = [[str(v) if not isinstance(v, float) else f"{v:.2f}" for v in row] for row in df.values]
    tbl = ax.table(cellText=cell, colLabels=labels, loc="upper left", cellLoc="center",
                   colWidths=[0.22, 0.07] + [0.065] * 11)
    tbl.auto_set_font_size(False); tbl.set_fontsize(7.2); tbl.scale(1, 1.25)
    for (r, c), cellobj in tbl.get_celld().items():
        cellobj.set_edgecolor(LINE); cellobj.set_linewidth(0.5)
        if r == 0:
            cellobj.set_facecolor(team.colour); cellobj.get_text().set_color("#FFFFFF"); cellobj.get_text().set_weight("bold")
        elif r % 2 == 0:
            cellobj.set_facecolor("#FFFFFF")
        else:
            cellobj.set_facecolor(BG)
        if c == 0:
            cellobj.get_text().set_ha("left"); cellobj.PAD = 0.05
    ax.set_title(f"{team.name} · starters", fontsize=10, color=team.colour, weight="bold", loc="left", pad=4)


def radar(ax, player_row, players_all, team):
    params = ["xG", "Shots", "Key passes", "Prog. passes", "Pass acc %", "Duels won", "Recoveries"]
    vals = [player_row.xG, player_row.Shots, player_row.KeyPasses, player_row.ProgPasses, player_row.PassAcc,
            player_row.DuelsWon, player_row.Recoveries]
    lo = [0, 0, 0, 0, 50, 0, 0]
    hi = [max(players_all.xG.max(), 0.5), players_all.Shots.max() or 1, players_all.KeyPasses.max() or 1,
          players_all.ProgPasses.max() or 1, 100, players_all.DuelsWon.max() or 1, players_all.Recoveries.max() or 1]
    r = Radar(params, lo, hi, num_rings=4, ring_width=1, center_circle_radius=1)
    r.setup_axis(ax=ax, facecolor=BG)
    r.draw_circles(ax=ax, facecolor="#FFFFFF", edgecolor=LINE)
    r.draw_radar(vals, ax=ax, kwargs_radar=dict(facecolor=team.colour, alpha=0.55), kwargs_rings=dict(facecolor=team.colour_light, alpha=0.5))
    r.draw_range_labels(ax=ax, fontsize=6, color=INK3)
    r.draw_param_labels(ax=ax, fontsize=7, color=INK2)
    ax.set_title(f"{player_row.Player}  ·  {player_row.Pos}  ·  {player_row.Min}'", fontsize=9.5, color=team.colour, weight="bold", pad=2)


def page_players(pdf):
    fig = new_page()
    header(fig, "Players", "Sorted by goals, xG, progressive passes · radars scaled to the best value in this match")
    all_players = pd.concat([home_players, away_players])
    ax1 = fig.add_axes([0.04, 0.44, 0.60, 0.42]); player_table(ax1, home_players, HOME)
    ax2 = fig.add_axes([0.04, 0.02, 0.60, 0.42]); player_table(ax2, away_players, AWAY)
    top_h = home_players.sort_values(["Goals", "xG"], ascending=False).iloc[0]
    top_a = away_players.sort_values(["ProgPasses", "KeyPasses"], ascending=False).iloc[0]
    ax3 = fig.add_axes([0.66, 0.50, 0.32, 0.36]); radar(ax3, top_h, all_players, HOME)
    ax4 = fig.add_axes([0.66, 0.09, 0.32, 0.36]); radar(ax4, top_a, all_players, AWAY)
    footer(fig, 5)
    save(pdf, fig, "05_players_radars")


# ------------------------------------------------------------------ page 6: notes
def page_notes(pdf):
    fig = new_page()
    header(fig, "Analyst notes", "Free text typed into the app before generating")
    import textwrap
    hxg, axg = home_shots.xG.sum(), away_shots.xG.sum()
    teague = home_players[home_players.Player == "Teague"].iloc[0]
    notes = [
        ("What decided it", f"Sydney generated {hxg:.2f} xG to Victory's {axg:.2f} and won the field-tilt battle 61 to 39. Victory's best spell came after the 65th minute when they pushed both full backs high; Bacus's goal at 74' came from that pressure."),
        ("Pressing", "PPDA of 9.1 shows Sydney pressed high and early. Eight high recoveries, four of which led to shots within ten seconds."),
        ("Set pieces", "Six corners for Sydney produced 0.31 xG. Victory defended zonally and conceded nothing from the first phase, but two second-phase shots came from cleared corners."),
        ("Individual", f"Teague led the line with {int(teague.Goals)} goals from {teague.xG:.2f} xG. Caceres had the most progressive passes on either side and set the tempo. Bacus was Victory's most influential player between the lines."),
        ("For next week", "Victory's left side was exposed in transition; Segecic found space there repeatedly. Review whether the 4-3-3 press can be sustained for a full 90 against a team that plays through the middle."),
    ]
    y = 0.84
    for title, body in notes:
        fig.text(0.06, y, title.upper(), fontsize=8.5, weight="bold", color=HOME.colour)
        fig.text(0.06, y - 0.03, textwrap.fill(body, 125), fontsize=10, color=INK, va="top", linespacing=1.5)
        y -= 0.15
    footer(fig, 6)
    save(pdf, fig, "06_notes")


# ------------------------------------------------------------------ save helpers
def save(pdf, fig, name):
    pdf.savefig(fig, facecolor=BG)
    fig.savefig(os.path.join(OUT, f"{name}.png"), dpi=150, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    pdf_path = os.path.join(OUT, "demo_match_report.pdf")
    with PdfPages(pdf_path) as pdf:
        page_cover(pdf)
        page_shots(pdf)
        page_networks(pdf)
        page_territory(pdf)
        page_players(pdf)
        page_notes(pdf)
    print("wrote", pdf_path)
