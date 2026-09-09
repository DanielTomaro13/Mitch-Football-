"""Generate: draw the report from this session's files, show it, download it."""
from __future__ import annotations

import streamlit as st

from src import ingest, report

DEFAULT_HOME = "#3F8FCC"
DEFAULT_AWAY = "#1B2A4A"


def _badge_uploader(col, label: str, key: str) -> bytes | None:
    """Optional badge image, kept in memory for the session. Returns the bytes or None."""
    ss = st.session_state
    f = col.file_uploader(label, type=["png", "jpg", "jpeg"], key=f"{key}-uploader", label_visibility="visible",
                          help="Optional. A PNG with a transparent background looks best.")
    if f is not None:
        ss[key] = f.getvalue()
    elif col.button("Remove", key=f"{key}-remove", disabled=key not in ss):
        ss.pop(key, None)
    if ss.get(key):
        col.image(ss[key], width=56)
    return ss.get(key)


def render() -> None:
    ss = st.session_state
    st.title("Generate")
    uploads = {k: v["df"] for k, v in ss.get("uploads", {}).items()}
    if not uploads:
        st.info("Nothing to draw yet. Go to **Upload and preview**, add a file (or load a sample), then come back.", icon=":material/upload_file:")
        return

    match = ss.get("match") or ingest.match_details(next(uploads[k] for k in ("team", "events", "player") if k in uploads))
    home_name, away_name = match.get("home") or "Home", match.get("away") or "Away"
    score = f"{match['home_goals']} – {match['away_goals']}" if match.get("home_goals") is not None else "v"
    st.markdown(f"**{home_name} {score} {away_name}**" + (f"  ·  {match['competition']}" if match.get("competition") else ""))
    st.caption("Files in this session: " + ", ".join(f"{ingest.KINDS[k].label} ({ss['uploads'][k]['name']})" for k in uploads)
               + ". Pages: " + " · ".join(report.pages_available(uploads)) + ".")
    if not ss.get("match"):
        st.caption("Tip: save the match details on the Upload page to set the score, date and competition on the cover.")

    with st.container(border=True):
        c1, c2 = st.columns(2)
        home_col = c1.color_picker(f"{home_name} colour", ss.get("home_colour", DEFAULT_HOME))
        away_col = c2.color_picker(f"{away_name} colour", ss.get("away_colour", DEFAULT_AWAY))
        with st.expander("Club badges (optional)"):
            b1, b2 = st.columns(2)
            home_badge = _badge_uploader(b1, f"{home_name} badge", "home_badge")
            away_badge = _badge_uploader(b2, f"{away_name} badge", "away_badge")
        notes_text = st.text_area(
            "Analyst notes (optional)", ss.get("notes_text", ""), height=140,
            placeholder="# What decided it\nSydney won the xG battle...\n\n# For next week\nWatch the left side in transition.",
            help="Start a line with # to make a heading. Leave blank to skip the notes page.",
        )
        go = st.button("Generate report", type="primary", icon=":material/auto_awesome:", use_container_width=True)

    if go:
        ss["home_colour"], ss["away_colour"], ss["notes_text"] = home_col, away_col, notes_text
        ctx = report.ctx_from_session(match, (home_col, away_col), notes_text, uploads, (home_badge, away_badge))
        with st.status("Drawing the report…", expanded=True) as status:
            try:
                pages, pdf = report.build(ctx, uploads, progress=lambda title: status.write(f"Drawing {title}…"))
            except Exception as err:  # noqa: BLE001
                status.update(label="Something went wrong", state="error")
                st.error(f"Could not draw the report: {err}")
                st.exception(err)
                return
            status.update(label=f"Done · {len(pages)} pages", state="complete", expanded=False)
        ss["report"] = {"pages": pages, "pdf": pdf, "name": f"{ctx.home.name} {ctx.score} {ctx.away.name}".replace("–", "-")}

    rep = ss.get("report")
    if not rep:
        return
    st.success(f"Report ready: {len(rep['pages'])} pages.", icon=":material/check_circle:")
    d1, _ = st.columns([1, 3])
    d1.download_button("Download PDF", rep["pdf"], file_name=f"{rep['name']}.pdf", mime="application/pdf",
                       type="primary", icon=":material/download:", use_container_width=True)
    for i, page in enumerate(rep["pages"], start=1):
        st.markdown(f"#### {i} · {page.title}")
        st.image(page.png, use_container_width=True)
        st.download_button("Download this page as PNG", page.png, file_name=f"{rep['name']} - {page.title}.png",
                           mime="image/png", key=f"png-{i}", icon=":material/image:")
