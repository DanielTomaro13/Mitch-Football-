"""Home screen: what the tool does and where things stand."""
import os

import streamlit as st

DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "demo", "output")


def render() -> None:
    st.title("Match Report Generator")
    st.markdown(
        "Upload a match CSV, click **Generate**, download a report. "
        "Nothing you upload is saved anywhere."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 1 · Upload")
        st.markdown("Drop in a CSV or Excel file exported from Wyscout or the Best11 app.")
    with c2:
        st.markdown("#### 2 · Check")
        st.markdown("The app works out what kind of file it is and tells you if anything is missing.")
    with c3:
        st.markdown("#### 3 · Generate")
        st.markdown("Preview the report on screen, then download it as a PDF.")

    st.divider()

    st.markdown("#### Build status")
    st.markdown(
        """
| Phase | What it gives you | Status |
|---|---|---|
| 1 · Foundation and PIN gate | Working link, PIN screen, nothing stored | ✅ Done |
| 2 · Upload, detect, validate | File checks, templates, column matching | ⏳ Next |
| 3 · Charts and report pages | Shot maps, xG race, pass networks, player tables | Planned |
| 4 · Export and polish | One-click PDF, per-chart PNG | Planned |
| 5 · Wyscout API (optional) | Pick a match from a list, no upload needed | Planned |
"""
    )

    st.divider()
    st.markdown("#### What a finished report looks like")
    st.caption("Demo built from invented data. The real thing will use your files.")
    pdf = os.path.join(DEMO_DIR, "demo_match_report.pdf")
    if os.path.exists(pdf):
        with open(pdf, "rb") as f:
            st.download_button(
                "Download the demo report (PDF)", f, file_name="demo_match_report.pdf",
                mime="application/pdf", icon=":material/download:",
            )
    pages = [
        ("01_cover_team_comparison.png", "Cover and team comparison"),
        ("02_shot_maps_xg_race.png", "Shot maps and xG race"),
        ("03_pass_networks.png", "Pass networks"),
        ("04_territory_progression.png", "Territory and progression"),
        ("05_players_radars.png", "Players and radars"),
    ]
    cols = st.columns(2)
    for i, (fname, label) in enumerate(pages):
        path = os.path.join(DEMO_DIR, fname)
        if os.path.exists(path):
            cols[i % 2].image(path, caption=label, use_container_width=True)
