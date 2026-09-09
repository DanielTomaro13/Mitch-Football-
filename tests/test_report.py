"""The report builds from the sample files in every combination of inputs."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import ingest, report  # noqa: E402

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _uploads():
    out = {}
    for f in ("team_match_summary.csv", "player_match_stats.csv", "match_events.csv"):
        with open(os.path.join(SAMPLES, f), "rb") as fh:
            df = ingest.read_upload(f, fh.read())
        det = ingest.detect(df)
        out[det.kind.key] = ingest.standardise(df, det)
    return out


def _build(uploads, notes=""):
    src = next(uploads[k] for k in ("team", "events", "player") if k in uploads)
    ctx = report.ctx_from_session(ingest.match_details(src), ("#3F8FCC", "#1B2A4A"), notes, uploads)
    return report.build(ctx, uploads)


def test_full_report_has_every_page():
    pages, pdf = _build(_uploads(), notes="# Heading\nBody text.")
    assert [p.title for p in pages] == ["Cover and team comparison", "Shots and xG race", "Pass networks",
                                        "Territory and progression", "Players and radars", "Analyst notes"]
    assert pdf[:4] == b"%PDF" and all(p.png[:8] == b"\x89PNG\r\n\x1a\n" for p in pages)


def test_events_only_derives_team_summary():
    up = _uploads()
    pages, _ = _build({"events": up["events"]})
    assert pages[0].title == "Cover and team comparison" and len(pages) == 4


def test_player_only_and_team_only():
    up = _uploads()
    assert [p.title for p in _build({"player": up["player"]})[0]] == ["Players and radars"]
    assert [p.title for p in _build({"team": up["team"]})[0]] == ["Cover and team comparison"]


def test_parse_notes():
    notes = report.parse_notes("# One\nfirst line\nsecond line\n\n# Two\nbody\n\nno heading para")
    assert notes == [("One", "first line second line"), ("Two", "body"), ("", "no heading para")]
