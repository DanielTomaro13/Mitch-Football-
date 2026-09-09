"""
Recognise, check and standardise uploaded match files.

Three kinds of file are understood (see PLAN.md):
  A · team    – one row per team for a match (xG, possession, PPDA ...)
  B · player  – one row per player for a match (minutes, goals, xG, passes ...)
  C · events  – one row per event with pitch coordinates (Wyscout style, 0-100)

Column names are matched loosely: case, spaces and punctuation are ignored, and
each field has a list of synonyms, so "Accurate passes, %", "Pass accuracy" and
"pass_acc" all land on the same field. When a required column cannot be found
the caller can show a mapper and pass an explicit mapping in.

Everything here works on in-memory DataFrames. Nothing is written to disk.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Iterable

import pandas as pd


# ----------------------------------------------------------------- helpers
def norm(name: object) -> str:
    """'Accurate passes, %' -> 'accuratepasses'; 'type.primary' -> 'typeprimary'."""
    return re.sub(r"[^a-z0-9]+", "", str(name).lower().replace("%", "pct")).replace("pct", "")


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    synonyms: tuple[str, ...] = ()
    required: bool = True
    numeric: bool = False
    example: str = ""

    def matches(self, column: object) -> bool:
        n = norm(column)
        return n == norm(self.label) or n == norm(self.key) or n in {norm(s) for s in self.synonyms}


@dataclass(frozen=True)
class Kind:
    key: str
    code: str
    label: str
    description: str
    source: str
    fields: tuple[Field, ...]
    unlocks: tuple[str, ...]

    @property
    def required(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if f.required)

    @property
    def optional(self) -> tuple[Field, ...]:
        return tuple(f for f in self.fields if not f.required)

    def field(self, key: str) -> Field:
        return next(f for f in self.fields if f.key == key)


# ----------------------------------------------------------------- the three kinds
TEAM = Kind(
    key="team", code="A", label="Team match summary",
    description="One row per team for the match: xG, possession, shots, pressing and territory numbers.",
    source="Best11 'Football Match Reports' data, a Wyscout team export, or the template filled in by hand.",
    fields=(
        Field("team", "Team", ("squad", "team name", "club"), example="Sydney FC"),
        Field("match", "Match", ("fixture", "game", "match name", "label"), required=False, example="Sydney FC 2-1 Melbourne Victory"),
        Field("date", "Date", ("match date", "kick off"), required=False, example="2026-11-22"),
        Field("xg", "xG", ("expected goals", "xg for"), numeric=True, example="2.92"),
        Field("xga", "xGA", ("xg against", "xg conceded", "expected goals against"), numeric=True, example="1.88"),
        Field("goals", "Goals", ("goals for", "gf", "goals scored", "score"), numeric=True, example="2"),
        Field("goals_conceded", "Goals conceded", ("goals against", "ga"), numeric=True, required=False, example="1"),
        Field("possession", "Possession %", ("possession", "ball possession", "possession pct"), numeric=True, example="56"),
        Field("shots", "Shots", ("total shots", "shots total"), numeric=True, example="14"),
        Field("shots_on_target", "Shots on target", ("sot", "on target"), numeric=True, required=False, example="9"),
        Field("open_play_xg", "Open play xG", ("open play xg", "op xg"), numeric=True, required=False, example="2.40"),
        Field("set_piece_xg", "Set piece xG", ("set piece xg", "sp xg"), numeric=True, required=False, example="0.52"),
        Field("npxg", "npxG", ("non penalty xg", "non-penalty xg"), numeric=True, required=False, example="2.92"),
        Field("field_tilt", "Field tilt %", ("field tilt", "territory"), numeric=True, required=False, example="61"),
        Field("ppda", "PPDA", ("passes per defensive action",), numeric=True, required=False, example="9.1"),
        Field("xt", "xT", ("expected threat",), numeric=True, required=False, example="1.42"),
        Field("passes_into_box", "Passes into box", ("passes into penalty area", "passes to penalty area", "box entries"), numeric=True, required=False, example="14"),
        Field("high_recoveries", "High recoveries", ("recoveries in opposition half", "high turnovers"), numeric=True, required=False, example="8"),
        Field("crosses", "Crosses", (), numeric=True, required=False, example="17"),
        Field("corners", "Corners", ("corner kicks",), numeric=True, required=False, example="6"),
        Field("fouls", "Fouls", ("fouls committed",), numeric=True, required=False, example="11"),
    ),
    unlocks=("Cover", "Team comparison"),
)

PLAYER = Kind(
    key="player", code="B", label="Player match stats",
    description="One row per player for the match: minutes, goals, xG, passes, duels and more.",
    source="Wyscout 'Export to Excel' for a match, a Best11 player download, or the template filled in by hand.",
    fields=(
        Field("player", "Player", ("player name", "name", "short name"), example="Teague"),
        Field("team", "Team", ("squad", "club", "team name"), example="Sydney FC"),
        Field("position", "Position", ("pos", "main position", "role"), required=False, example="ST"),
        Field("minutes", "Minutes played", ("minutes", "mins", "min", "time played"), numeric=True, example="90"),
        Field("goals", "Goals", ("g",), numeric=True, example="2"),
        Field("xg", "xG", ("expected goals",), numeric=True, example="1.11"),
        Field("assists", "Assists", ("a",), numeric=True, required=False, example="0"),
        Field("xa", "xA", ("expected assists",), numeric=True, required=False, example="0.10"),
        Field("shots", "Shots", ("total shots",), numeric=True, example="4"),
        Field("passes", "Passes", ("total passes", "passes attempted"), numeric=True, required=False, example="38"),
        Field("pass_accuracy", "Accurate passes %", ("accurate passes", "pass accuracy", "pass completion", "passing accuracy", "pass acc"), numeric=True, required=False, example="83"),
        Field("key_passes", "Key passes", ("kp", "shot assists"), numeric=True, required=False, example="1"),
        Field("progressive_passes", "Progressive passes", ("prog passes", "progressive passes completed"), numeric=True, required=False, example="1"),
        Field("duels", "Duels", ("total duels", "duels total"), numeric=True, required=False, example="13"),
        Field("duels_won_pct", "Duels won %", ("duels won", "duel success"), numeric=True, required=False, example="54"),
        Field("recoveries", "Recoveries", ("ball recoveries",), numeric=True, required=False, example="1"),
        Field("dribbles", "Dribbles", ("successful dribbles", "take ons"), numeric=True, required=False, example="2"),
    ),
    unlocks=("Players table", "Top performers", "Player radars"),
)

EVENTS = Kind(
    key="events", code="C", label="Match events",
    description="One row per event (pass, shot, duel ...) with pitch coordinates from 0 to 100.",
    source="Wyscout API events flattened to a table (the app does this itself in phase 5), or the template.",
    fields=(
        Field("minute", "Minute", ("min", "match minute"), numeric=True, example="31"),
        Field("second", "Second", ("sec", "seconds"), numeric=True, required=False, example="12"),
        Field("period", "Period", ("match period", "half"), required=False, example="1H"),
        Field("team", "Team", ("team name", "team.name", "squad"), example="Sydney FC"),
        Field("player", "Player", ("player name", "player.name", "player.shortName"), example="Teague"),
        Field("type", "Type", ("type.primary", "primary type", "event", "event name", "event type"), example="shot"),
        Field("secondary", "Secondary type", ("type.secondary", "sub event name", "tags"), required=False, example="head_shot"),
        Field("x", "X", ("location.x", "start x", "pos x", "x start"), numeric=True, example="91.5"),
        Field("y", "Y", ("location.y", "start y", "pos y", "y start"), numeric=True, example="46"),
        Field("end_x", "End X", ("pass.endLocation.x", "end location x", "pass end x", "carry.endLocation.x"), numeric=True, required=False, example="95"),
        Field("end_y", "End Y", ("pass.endLocation.y", "end location y", "pass end y", "carry.endLocation.y"), numeric=True, required=False, example="50"),
        Field("pass_accurate", "Pass accurate", ("pass.accurate", "accurate", "successful", "completed"), required=False, example="True"),
        Field("shot_xg", "Shot xG", ("shot.xg", "xg"), numeric=True, required=False, example="0.34"),
        Field("is_goal", "Is goal", ("shot.isGoal", "goal"), required=False, example="True"),
        Field("on_target", "On target", ("shot.onTarget",), required=False, example="True"),
    ),
    unlocks=("Shot maps", "xG race", "Pass networks", "Territory and progression"),
)

KINDS: dict[str, Kind] = {k.key: k for k in (TEAM, PLAYER, EVENTS)}


# ----------------------------------------------------------------- detection
@dataclass
class Detection:
    kind: Kind
    mapping: dict[str, str]                 # field key -> column name in the file
    missing_required: list[Field] = field(default_factory=list)
    missing_optional: list[Field] = field(default_factory=list)
    unmatched_columns: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_required

    @property
    def score(self) -> float:
        req = self.kind.required
        hit = sum(1 for f in req if f.key in self.mapping)
        bonus = 0.01 * sum(1 for f in self.kind.optional if f.key in self.mapping)
        return hit / len(req) + bonus


def match_columns(columns: Iterable[object], kind: Kind, overrides: dict[str, str] | None = None) -> Detection:
    """Map a kind's fields onto the file's columns. `overrides` wins over guessing."""
    cols = [str(c) for c in columns]
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for f in kind.fields:
        chosen = (overrides or {}).get(f.key)
        if chosen and chosen in cols:
            mapping[f.key] = chosen
            used.add(chosen)
            continue
        for c in cols:
            if c not in used and f.matches(c):
                mapping[f.key] = c
                used.add(c)
                break
    return Detection(
        kind=kind,
        mapping=mapping,
        missing_required=[f for f in kind.required if f.key not in mapping],
        missing_optional=[f for f in kind.optional if f.key not in mapping],
        unmatched_columns=[c for c in cols if c not in used],
    )


def detect(df: pd.DataFrame, force_kind: str | None = None, overrides: dict[str, str] | None = None) -> Detection:
    """Pick the best-fitting kind. A complete match always beats a partial one."""
    if force_kind:
        return match_columns(df.columns, KINDS[force_kind], overrides)
    candidates = [match_columns(df.columns, k) for k in KINDS.values()]
    complete = [c for c in candidates if c.ok]
    if complete:
        # If several kinds fit completely, prefer the most specific (most fields matched).
        return max(complete, key=lambda c: (len(c.mapping), c.score))
    return max(candidates, key=lambda c: c.score)


# ----------------------------------------------------------------- reading and standardising
def read_upload(name: str, data: bytes) -> pd.DataFrame:
    """CSV or Excel bytes -> DataFrame. utf-8-sig strips the BOM Excel/Wyscout add."""
    if name.lower().endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(io.BytesIO(data), encoding="latin-1")
    return pd.read_excel(io.BytesIO(data))


def _to_number(series: pd.Series) -> pd.Series:
    """'56%', '1,234', ' 0.42 ' -> numbers. Anything unreadable becomes NaN."""
    if pd.api.types.is_numeric_dtype(series):
        return series
    cleaned = series.astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned, errors="coerce")


def _to_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series
    truthy = {"true", "1", "yes", "y", "t"}
    return series.astype(str).str.strip().str.lower().isin(truthy)


def standardise(df: pd.DataFrame, det: Detection) -> pd.DataFrame:
    """Return a copy with canonical column names and clean types."""
    out = pd.DataFrame(index=df.index)
    for f in det.kind.fields:
        col = det.mapping.get(f.key)
        if col is None:
            continue
        s = df[col]
        if f.numeric:
            s = _to_number(s)
        elif f.key in ("pass_accurate", "is_goal", "on_target"):
            s = _to_bool(s)
        elif f.key == "date":
            s = pd.to_datetime(s, errors="coerce").dt.date
        else:
            s = s.astype(str).str.strip()
        out[f.key] = s
    out.attrs["kind"] = det.kind.key
    return out.reset_index(drop=True)


# ----------------------------------------------------------------- match details from the file
_SCORE_RE = re.compile(r"^(?P<home>.+?)\s+(?P<hg>\d+)\s*[-–:]\s*(?P<ag>\d+)\s+(?P<away>.+?)$")


def parse_match_label(label: str) -> dict | None:
    """'Auckland 1-0 Sydney' -> home/away names and goals."""
    m = _SCORE_RE.match(str(label).strip())
    if not m:
        return None
    return {"home": m["home"].strip(), "away": m["away"].strip(), "home_goals": int(m["hg"]), "away_goals": int(m["ag"])}


def match_details(std: pd.DataFrame) -> dict:
    """Best guess at home/away/score/date from a standardised frame. Blanks where unknown."""
    d = {"home": "", "away": "", "home_goals": None, "away_goals": None, "date": None, "competition": ""}
    teams = [t for t in std["team"].dropna().unique().tolist()] if "team" in std else []
    if "match" in std and std["match"].notna().any():
        parsed = parse_match_label(std["match"].dropna().iloc[0])
        if parsed:
            d.update(parsed)
    if not d["home"] and teams:
        d["home"] = teams[0]
        d["away"] = teams[1] if len(teams) > 1 else ""
    if std.attrs.get("kind") == "team" and "goals" in std and d["home_goals"] is None and len(teams) >= 2:
        by_team = std.set_index("team")["goals"]
        d["home_goals"] = int(by_team.get(d["home"], 0) or 0)
        d["away_goals"] = int(by_team.get(d["away"], 0) or 0)
    if std.attrs.get("kind") == "events" and "is_goal" in std and d["home_goals"] is None and len(teams) >= 2:
        goals = std[std["is_goal"] == True].groupby("team").size()  # noqa: E712
        d["home_goals"], d["away_goals"] = int(goals.get(d["home"], 0)), int(goals.get(d["away"], 0))
    if "date" in std and std["date"].notna().any():
        d["date"] = std["date"].dropna().iloc[0]
    return d


# ----------------------------------------------------------------- templates
def template_csv(kind: Kind) -> str:
    """A CSV with the recognised headers and two example rows, for people to fill in."""
    headers = [f.label for f in kind.fields]
    row1 = [f.example for f in kind.fields]
    row2 = list(row1)
    # make the second row read as the other team / another player
    for i, f in enumerate(kind.fields):
        if f.key == "team":
            row2[i] = "Melbourne Victory"
        elif f.key == "player":
            row2[i] = "Bacus"
    return pd.DataFrame([row1, row2], columns=headers).to_csv(index=False)
