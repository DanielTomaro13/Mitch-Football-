"""
Match Report Generator – entry point.

Flow: PIN screen -> (unlocked) -> Home / Upload and preview / How to use.
Nothing is written to disk. Uploaded files live in memory for the browser
session only and disappear when the tab is closed or the session goes idle.
"""
import streamlit as st

from src import auth
from src.views import home, how_to, upload

st.set_page_config(
    page_title="Match Report Generator",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Internal match report tool. Nothing you upload is stored."},
)

# ---- Gate: everything below only runs once the PIN has been entered ----
if not auth.is_authenticated():
    auth.render_pin_screen()
    st.stop()

pages = [
    st.Page(home.render, title="Home", icon=":material/home:", url_path="home", default=True),
    st.Page(upload.render, title="Upload and preview", icon=":material/upload_file:", url_path="upload"),
    st.Page(how_to.render, title="How to use", icon=":material/help:", url_path="how-to"),
]

with st.sidebar:
    st.markdown("### ⚽ Match Report Generator")
    st.caption("Nothing you upload is stored. Close the tab and it is gone.")
    if st.button("Lock the app", icon=":material/lock:", use_container_width=True):
        auth.logout()
        st.rerun()
    st.divider()

st.navigation(pages).run()
