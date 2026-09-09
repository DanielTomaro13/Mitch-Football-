"""
Write sample files in the three accepted formats into samples/.

They reuse the invented match from make_demo_report.py, with headers in the
styles people will actually meet:
  A · team   – Best11 / Griffis "Football Match Reports" column names
  B · player – Wyscout "Export to Excel" style names (", %" suffixes)
  C · events – Wyscout API v3 events flattened with dotted keys
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
import make_demo_report as demo  # noqa: E402  (generates the match data on import)

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)

# ------------------------------------------------------------ A · team match summary
label = f"{demo.HOME.name} {demo.MATCH['score_home']}-{demo.MATCH['score_away']} {demo.AWAY.name}"
ts = demo.TEAM_STATS.set_index("metric")
team_rows = []
for t, other, goals, conceded in ((demo.HOME, demo.AWAY, 2, 1), (demo.AWAY, demo.HOME, 1, 2)):
    team_rows.append({
        "Team": t.name, "xG": ts.loc["xG", t.name], "xGA": ts.loc["xG", other.name],
        "Open Play xG": round(ts.loc["xG", t.name] * 0.82, 2), "Set Piece xG": round(ts.loc["xG", t.name] * 0.18, 2),
        "npxG": ts.loc["xG", t.name], "Goals": goals, "Goals Conceded": conceded,
        "Possession": ts.loc["Possession %", t.name], "Field Tilt": ts.loc["Field tilt %", t.name],
        "xT": ts.loc["xT", t.name], "Passes into Box": ts.loc["Passes into box", t.name],
        "Shots": ts.loc["Shots", t.name], "Shots on Target": ts.loc["Shots on target", t.name],
        "PPDA": ts.loc["PPDA", t.name], "High Recoveries": ts.loc["High recoveries", t.name],
        "Crosses": ts.loc["Crosses", t.name], "Corners": ts.loc["Corners", t.name], "Fouls": ts.loc["Fouls", t.name],
        "Match": label, "Date": "2026-11-22",
    })
pd.DataFrame(team_rows).to_csv(os.path.join(OUT, "team_match_summary.csv"), index=False)

# ------------------------------------------------------------ B · player match stats
players = pd.concat([demo.home_players, demo.away_players], ignore_index=True)
player_df = pd.DataFrame({
    "Player": players.Player, "Team": players.Team, "Position": players.Pos,
    "Minutes played": players.Min, "Goals": players.Goals, "xG": players.xG, "Assists": players.Assists,
    "xA": (players.KeyPasses * 0.09).round(2), "Shots": players.Shots, "Passes": players.Passes,
    "Accurate passes, %": players.PassAcc, "Key passes": players.KeyPasses, "Progressive passes": players.ProgPasses,
    "Duels": players.Duels, "Duels won, %": (players.DuelsWon / players.Duels * 100).round(0).astype(int),
    "Recoveries": players.Recoveries,
})
player_df.to_csv(os.path.join(OUT, "player_match_stats.csv"), index=False)

# ------------------------------------------------------------ C · match events (flattened Wyscout API style)
rows = []
eid = 100000


def add(team, player, minute, second, primary, secondary, x, y, end=None, accurate=None, xg=None, goal=None, on_target=None):
    global eid
    eid += 1
    rows.append({
        "id": eid, "matchPeriod": "1H" if minute < 45 else "2H", "minute": minute, "second": second,
        "type.primary": primary, "type.secondary": secondary,
        "team.name": team.name, "player.name": player,
        "location.x": round(float(x), 1), "location.y": round(float(y), 1),
        "pass.endLocation.x": None if end is None else round(float(end[0]), 1),
        "pass.endLocation.y": None if end is None else round(float(end[1]), 1),
        "pass.accurate": accurate, "shot.xg": xg, "shot.isGoal": goal, "shot.onTarget": on_target,
    })


for team, shots in ((demo.HOME, demo.home_shots), (demo.AWAY, demo.away_shots)):
    for _, s in shots.iterrows():
        add(team, s.player, int(s.minute), int(rng.integers(0, 60)), "shot", "goal" if s.goal else "",
            s.x, s.y, xg=float(s.xG), goal=bool(s.goal), on_target=bool(s.on_target))

for team, players_df, links, prog in ((demo.HOME, demo.home_players, demo.home_links, demo.home_prog),
                                      (demo.AWAY, demo.away_players, demo.away_links, demo.away_prog)):
    pos = players_df.set_index("Player")[["avg_x", "avg_y"]]
    for _, l in links.iterrows():
        for _ in range(int(l["count"])):
            x0, y0 = pos.loc[l.passer] + rng.normal(0, 6, 2)
            x1, y1 = pos.loc[l.receiver] + rng.normal(0, 6, 2)
            add(team, l.passer, int(rng.integers(1, 91)), int(rng.integers(0, 60)), "pass", "short_or_medium_pass",
                np.clip(x0, 1, 99), np.clip(y0, 1, 99), end=(np.clip(x1, 1, 99), np.clip(y1, 1, 99)), accurate=True)
    for _, p in prog.iterrows():
        add(team, p.player, int(rng.integers(1, 91)), int(rng.integers(0, 60)), "pass", "progressive_pass",
            p.x, p.y, end=(p.end_x, p.end_y), accurate=bool(p.accurate))

for team, touch in ((demo.HOME, demo.home_touch), (demo.AWAY, demo.away_touch)):
    players_df = demo.home_players if team is demo.HOME else demo.away_players
    names = players_df.Player.tolist()
    for x, y in zip(touch[0][::3], touch[1][::3]):
        add(team, names[int(rng.integers(0, len(names)))], int(rng.integers(1, 91)), int(rng.integers(0, 60)),
            "touch", "", x, y)

events = pd.DataFrame(rows).sort_values(["minute", "second"]).reset_index(drop=True)
events.to_csv(os.path.join(OUT, "match_events.csv"), index=False)

for f in ("team_match_summary.csv", "player_match_stats.csv", "match_events.csv"):
    print(f, os.path.getsize(os.path.join(OUT, f)), "bytes")
