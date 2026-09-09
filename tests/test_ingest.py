"""Checks for file recognition, column matching and standardising. Run: .venv/bin/python -m pytest -q"""
import io
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import ingest  # noqa: E402

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _read(name):
    with open(os.path.join(SAMPLES, name), "rb") as f:
        return ingest.read_upload(name, f.read())


def test_samples_are_recognised():
    for fname, kind in (("team_match_summary.csv", "team"), ("player_match_stats.csv", "player"), ("match_events.csv", "events")):
        det = ingest.detect(_read(fname))
        assert det.kind.key == kind, (fname, det.kind.key, det.missing_required)
        assert det.ok, (fname, [f.label for f in det.missing_required])


def test_templates_round_trip():
    for kind in ingest.KINDS.values():
        df = pd.read_csv(io.StringIO(ingest.template_csv(kind)))
        det = ingest.detect(df)
        assert det.kind.key == kind.key and det.ok, (kind.key, [f.label for f in det.missing_required])
        assert not det.missing_optional


def test_loose_header_matching():
    df = pd.DataFrame({"PLAYER NAME": ["A"], "Squad": ["X"], "Mins": [90], "G": [1], "Expected goals": [0.4], "Total shots": [2],
                       "Accurate passes, %": ["83%"], "Duels won, %": [55]})
    det = ingest.detect(df)
    assert det.kind.key == "player" and det.ok
    std = ingest.standardise(df, det)
    assert std["pass_accuracy"].iloc[0] == 83  # percent sign stripped
    assert std["duels_won_pct"].iloc[0] == 55


def test_missing_required_is_named_and_overrides_fix_it():
    df = pd.DataFrame({"Team": ["A", "B"], "Expected": [1.2, 0.8], "xGA": [0.8, 1.2], "Goals": [1, 0], "Possession": [55, 45], "Shots": [10, 8]})
    det = ingest.detect(df)
    assert det.kind.key == "team" and not det.ok
    assert [f.key for f in det.missing_required] == ["xg"]
    fixed = ingest.detect(df, force_kind="team", overrides={"xg": "Expected"})
    assert fixed.ok and fixed.mapping["xg"] == "Expected"


def test_match_details_from_label_and_teams():
    team = ingest.standardise(_read("team_match_summary.csv"), ingest.detect(_read("team_match_summary.csv")))
    d = ingest.match_details(team)
    assert d["home"] == "Sydney FC" and d["away"] == "Melbourne Victory"
    assert (d["home_goals"], d["away_goals"]) == (2, 1)
    assert str(d["date"]) == "2026-11-22"

    ev = ingest.standardise(_read("match_events.csv"), ingest.detect(_read("match_events.csv")))
    d = ingest.match_details(ev)
    assert {d["home"], d["away"]} == {"Sydney FC", "Melbourne Victory"}
    assert d["home_goals"] + d["away_goals"] == 3


def test_parse_match_label_variants():
    assert ingest.parse_match_label("Auckland 1-0 Sydney")["away"] == "Sydney"
    assert ingest.parse_match_label("Western Sydney Wanderers 2 – 2 Perth Glory")["home_goals"] == 2
    assert ingest.parse_match_label("Sydney v Perth") is None


def test_excel_and_bom_csv_read():
    df = pd.DataFrame({"Team": ["A"], "xG": [1.0]})
    buf = io.BytesIO(); df.to_excel(buf, index=False)
    assert list(ingest.read_upload("x.xlsx", buf.getvalue()).columns) == ["Team", "xG"]
    csv = "﻿Team,xG\nA,1.0\n".encode("utf-8")
    assert list(ingest.read_upload("x.csv", csv).columns) == ["Team", "xG"]
