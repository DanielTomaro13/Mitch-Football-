"""Headless Streamlit checks: the screens render and the Generate button builds a report."""
import os
import sys

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import ingest  # noqa: E402

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _uploads():
    out = {}
    for f in ("team_match_summary.csv", "player_match_stats.csv", "match_events.csv"):
        with open(os.path.join(SAMPLES, f), "rb") as fh:
            df = ingest.read_upload(f, fh.read())
        det = ingest.detect(df)
        out[det.kind.key] = {"name": f, "df": ingest.standardise(df, det)}
    return out


def _generate_app():
    def app():
        import sys as _s
        _s.path.insert(0, ".")
        from src.views import generate
        generate.render()
    return AppTest.from_function(app, default_timeout=120)


def test_generate_page_without_files_points_to_upload():
    at = _generate_app().run()
    assert not at.exception
    assert any("Upload and preview" in i.value for i in at.info)


def test_generate_button_builds_report():
    at = _generate_app()
    at.session_state["uploads"] = _uploads()
    at.session_state["match"] = {"home": "Sydney FC", "away": "Melbourne Victory", "home_goals": 2, "away_goals": 1,
                                 "date": None, "competition": "A-League Men", "venue": "", "headline": ""}
    at.run()
    assert not at.exception
    at.button(key=None)  # no-op lookup guard
    generate_btn = next(b for b in at.button if b.label == "Generate report")
    generate_btn.click().run()
    assert not at.exception, at.exception
    assert any("Report ready" in s.value for s in at.success)
    rep = at.session_state["report"]
    assert len(rep["pages"]) == 5 and rep["pdf"][:4] == b"%PDF"


def test_upload_page_renders_samples_and_form():
    def app():
        import sys as _s
        _s.path.insert(0, ".")
        from src.views import upload
        upload.render()
    at = AppTest.from_function(app, default_timeout=60).run()
    assert not at.exception
    next(b for b in at.button if b.label == "Team match summary").click().run()
    assert not at.exception
    assert any("Recognised as" in s.value for s in at.success)
    assert "team" in at.session_state["uploads"]
