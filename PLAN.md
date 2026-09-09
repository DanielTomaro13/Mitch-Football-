# Match Report Generator – Build Plan

Internal web tool: open a link, enter a 4-digit PIN, upload a Wyscout-style CSV, click Generate, download a match report as PDF. Nothing is stored.

## Non-negotiables

- **PIN at the door.** One shared 4-digit PIN kept in the hosting secrets store (never in code or GitHub). Lockout after 5 wrong attempts.
- **Nothing stored.** Uploads are held in memory for the browser session only. No database, no file writes, no data logs, telemetry off.
- **Non-technical users.** Plain-language screens, one button, errors that name the missing column, downloadable CSV templates, column-mapping fallback.

## What the referenced tools give us

- **Best11 Scouting** (Ben Griffis, Streamlit, Wyscout data): season-level player scouting (Best XI ranks, radars, scatters, CSV downloads). Its "Football Match Reports" page uses team-level per-match CSVs whose columns (xG, xGA, npxG, Open Play/Set Piece xG, Possession, Field Tilt, PPDA, xT, Shots, Passes into Box, High Recoveries, Crosses, Corners, Fouls…) are our template for kind A. Data files: https://github.com/griffisben/Post_Match_App
- **Wyscout API v3**: basic auth (username/password from Hudl/Wyscout), 12 requests/second, paid custom-quoted licence. Endpoints we care about: `/matches/{id}/events` (minute, second, x/y, pass end location, accuracy, recipient, shot xG, post-shot xG, on target, goal), `/matches/{id}/advancedstats` and `/advancedstats/players`, `/matches/{id}/formations`. Spec mirror: https://github.com/mbochicchio/wyscout-openapi · Glossary: https://dataglossary.wyscout.com/

Assumption: no API credentials yet, so CSV upload is the primary path and the API is an optional later phase.

## User journey

1. Open the link (laptop or phone, no install).
2. Enter the PIN; stays unlocked until the tab closes.
3. Drag in the CSV(s); green tick with what was found, or "Missing column: xG".
4. Confirm match details (teams pre-filled; optional score, date, competition, colours, headline).
5. Click Generate; report renders in seconds.
6. Download PDF (or PNG per chart). Close the tab and the data is gone.

## Accepted CSV kinds

| Kind | Source | Key columns | Unlocks |
|---|---|---|---|
| A · Team match summary | Best11 match-report data, Wyscout team export, hand-filled template | Team, Match, Date, xG, xGA, npxG, Open Play xG, Set Piece xG, Goals, Possession, Field Tilt, PPDA, xT, Shots, Passes into Box, High Recoveries, Crosses, Corners, Fouls | Cover, team comparison |
| B · Player match stats | Wyscout "Export to Excel" for a match, Best11 player download | Player, Team, Position, Minutes played, Goals, xG, Assists, xA, Shots, Passes, Accurate passes %, Key passes, Duels won %, Recoveries, Progressive passes | Player tables, top performers, radars |
| C · Match events | Wyscout API events flattened to one row per event | minute, second, period, team, player, type, x, y, end_x, end_y, pass_accurate, shot_xg, is_goal, on_target | Shot maps, xG race, pass networks, heatmaps |

Wyscout coordinates are 0–100 on both axes, attacking goal at x = 100; convert to a standard pitch.

## Report pages

- Cover: teams, score, date, competition, headline, five deciding stats (A or B)
- Team comparison: side-by-side bars, open-play vs set-piece xG (A)
- Shot maps, xG race, pass network, territory/heatmaps, progressive passes (C)
- Players: sortable table, top three, radars (B)
- Notes: analyst free text (always)

## Phases

1. **Foundation and PIN gate** – repo structure, Streamlit skeleton, PIN + lockout, deploy to Streamlit Community Cloud. Done when the link works and a wrong PIN is refused.
2. **Upload, detect, validate** – multi-file upload, kind detection, friendly errors, column mapper, templates, pre-filled match form. Needs sample CSVs. Done when every real CSV uploads with a green tick.
3. **Charts and report pages** – team bars, player tables/radars, shot map, xG race, pass network, heatmaps; consistent styling. Done when a full report renders for a real match.
4. **Export and polish** – PDF of all pages, PNG per chart, mobile check, in-app how-to. Done when two non-technical colleagues produce a report unaided.
5. **Wyscout API (optional)** – pick competition and match from dropdowns; fetch events/stats/lineups; convert to kinds A/B/C internally. Credentials in secrets. Done when a dropdown choice produces the full report.

## Stack

Python + Streamlit · pandas · mplsoccer + matplotlib · matplotlib multi-page PDF (fpdf2 if text-heavy) · Streamlit Community Cloud linked to GitHub · requests with basic auth for Wyscout.

## Repo layout

```
Mitch-Football-/
  app.py                  PIN gate, then report screens
  pages/                  Upload, Generate, How to use
  src/
    auth.py               PIN check and lockout
    ingest.py             read CSV/XLSX, detect kind, validate, map columns
    wyscout_api.py        optional: fetch and flatten events and stats
    charts/               shot_map.py, xg_race.py, pass_network.py, radar.py, team_bars.py
    report.py             assemble pages, export PDF/PNG
  templates/              kind_A.csv, kind_B.csv, kind_C.csv
  samples/                anonymised example files
  .streamlit/config.toml  theme, telemetry off, upload size limit
  requirements.txt
  README.md
```

## Decisions needed

1. Sample files: one real CSV of each kind into this folder (biggest unblocker).
2. Wyscout API credentials now, or a future purchase?
3. Output: PDF only, or PDF plus per-chart PNGs? (Plan assumes both.)
4. Branding: name, colours, badge file.
5. Hosting: free Streamlit Cloud OK, or must data stay on your own server?
6. Who owns changing the PIN.
