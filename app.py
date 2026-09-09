"""
Match Report Generator – entry point.

Flow: PIN screen -> (unlocked) -> Home / Upload and preview / How to use.
Nothing is written to disk. Uploaded files live in memory for the browser
session only and disappear when the tab is closed or the session goes idle.
"""
import streamlit as st

from src import auth
from src.views import generate, home, how_to, upload

st.set_page_config(
    page_title="Match Report Generator",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Internal match report tool. Nothing you upload is stored."},
)

# ---- Gate: everything below only runs once the PIN has been entered ----
if not auth.is_authenticated():
    # A hidden single-page navigation clears any page menu left in the sidebar
    # from an earlier unlocked run, so the lock screen shows nothing else.
    st.navigation([st.Page(auth.render_pin_screen, title="Unlock")], position="hidden").run()
    st.stop()

pages = [
    st.Page(home.render, title="Home", icon=":material/home:", url_path="home", default=True),
    st.Page(upload.render, title="Upload and preview", icon=":material/upload_file:", url_path="upload"),
    st.Page(generate.render, title="Generate", icon=":material/auto_awesome:", url_path="generate"),
    st.Page(how_to.render, title="How to use", icon=":material/help:", url_path="how-to"),
]

with st.sidebar:
    st.markdown("### ⚽ Match Report Generator")
    st.caption("Nothing you upload is stored. Close the tab and it is gone.")
    c1, c2 = st.columns(2)
    if c1.button("Start over", icon=":material/restart_alt:", use_container_width=True,
                 help="Forget the files, match details and report in this session."):
        for key in ("uploads", "sample_files", "overrides", "force_mapper", "match", "report",
                    "notes_text", "home_badge", "away_badge"):
            st.session_state.pop(key, None)
        st.rerun()
    if c2.button("Lock", icon=":material/lock:", use_container_width=True, help="Go back to the PIN screen."):
        auth.logout()
        st.rerun()
    st.divider()

st.navigation(pages).run()
