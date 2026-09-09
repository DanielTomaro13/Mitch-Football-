"""
Upload, recognise, check and preview match files. Then confirm match details.

Files (uploaded or sample) live in st.session_state for this browser session
only. Nothing is written to disk.
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src import ingest

ACCEPTED = ["csv", "xlsx", "xls"]
SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
SAMPLES = [
    ("Team match summary", "team_match_summary.csv"),
    ("Player match stats", "player_match_stats.csv"),
    ("Match events", "match_events.csv"),
]
NOT_IN_FILE = "— not in this file —"


# ----------------------------------------------------------------- session helpers
def _state() -> dict:
    ss = st.session_state
    ss.setdefault("sample_files", {})     # name -> bytes
    ss.setdefault("uploads", {})          # kind key -> {"name", "df"}
    ss.setdefault("overrides", {})        # file name -> {"kind": key, "mapping": {...}}
    return ss


def _load_sample(fname: str) -> None:
    path = os.path.join(SAMPLES_DIR, fname)
    with open(path, "rb") as f:
        _state()["sample_files"][fname] = f.read()


# ----------------------------------------------------------------- one file
def _mapper(name: str, df: pd.DataFrame, det: ingest.Detection) -> None:
    """Let the user pick which column is which for anything we could not find."""
    ss = _state()
    with st.expander("Match the columns yourself", expanded=True):
        st.markdown("Pick the column in your file that holds each of these. Leave optional ones blank if the file does not have them.")
        kind_key = st.selectbox(
            "This file is a…", options=list(ingest.KINDS), index=list(ingest.KINDS).index(det.kind.key),
            format_func=lambda k: f"{ingest.KINDS[k].label} (kind {ingest.KINDS[k].code})", key=f"kind-{name}",
        )
        kind = ingest.KINDS[kind_key]
        current = ingest.match_columns(df.columns, kind, ss["overrides"].get(name, {}).get("mapping"))
        options = [NOT_IN_FILE] + [str(c) for c in df.columns]
        chosen: dict[str, str] = {}
        cols = st.columns(2)
        to_show = [f for f in kind.fields if f.key not in current.mapping or f.required]
        for i, f in enumerate(to_show):
            default = current.mapping.get(f.key, NOT_IN_FILE)
            label = f"{f.label}{' (required)' if f.required else ''}"
            pick = cols[i % 2].selectbox(label, options, index=options.index(default) if default in options else 0, key=f"map-{name}-{f.key}")
            if pick != NOT_IN_FILE:
                chosen[f.key] = pick
        if st.button("Use these columns", type="primary", key=f"apply-{name}"):
            ss["overrides"][name] = {"kind": kind_key, "mapping": chosen}
            ss.setdefault("force_mapper", set()).discard(name)
            st.rerun()


def _show_file(name: str, data: bytes, is_sample: bool = False) -> None:
    ss = _state()
    with st.container(border=True):
        head = f"**{name}**  ·  {len(data) / 1024:.0f} KB"
        st.markdown(head + ("  ·  *sample file*" if is_sample else ""))
        try:
            df = ingest.read_upload(name, data)
        except Exception as err:  # noqa: BLE001
            st.error(f"Could not read this file. Is it a normal CSV or Excel export? ({err})")
            return
        if df.empty:
            st.error("The file has no rows.")
            return

        ov = ss["overrides"].get(name)
        det = ingest.detect(df, force_kind=ov["kind"] if ov else None, overrides=ov["mapping"] if ov else None)
        kind = det.kind

        if det.ok:
            st.success(f"Recognised as **{kind.label}** (kind {kind.code}). Unlocks: " + " · ".join(kind.unlocks), icon=":material/check_circle:")
            if det.missing_optional:
                st.caption("Optional columns not in this file: " + ", ".join(f.label for f in det.missing_optional) + ". The related charts will be skipped.")
            std = ingest.standardise(df, det)
            ss["uploads"][kind.key] = {"name": name, "df": std}
            st.dataframe(std.head(20), use_container_width=True, hide_index=True)
            with st.expander("Which column is which"):
                st.table(pd.DataFrame({"Report field": [kind.field(k).label for k in det.mapping], "Column in your file": list(det.mapping.values())}))
            if st.button("Try a different match-up", key=f"remap-{name}"):
                ss["overrides"][name] = {"kind": kind.key, "mapping": {}}
                ss.setdefault("force_mapper", set()).add(name)
                st.rerun()
        else:
            missing = ", ".join(f"**{f.label}**" for f in det.missing_required)
            st.warning(
                f"This looks like a **{kind.label}** (kind {kind.code}) but I could not find: {missing}. "
                "Rename the columns in your file, or match them below.", icon=":material/help:"
            )
            st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        if not det.ok or name in ss.get("force_mapper", set()):
            _mapper(name, df, det)


# ----------------------------------------------------------------- match details form
def _match_form() -> None:
    ss = _state()
    uploads = ss["uploads"]
    if not uploads:
        return
    st.divider()
    st.markdown("#### Match details")
    st.caption("Pre-filled from your file. Check and change anything that is wrong.")
    source = next(uploads[k]["df"] for k in ("team", "events", "player") if k in uploads)
    guess = ingest.match_details(source)
    saved = ss.get("match", {})
    with st.form("match_form", border=True):
        c1, c2 = st.columns(2)
        home = c1.text_input("Home team", value=saved.get("home") or guess["home"])
        away = c2.text_input("Away team", value=saved.get("away") or guess["away"])
        c3, c4, c5 = st.columns([1, 1, 2])
        hg = c3.number_input("Home goals", min_value=0, max_value=30, value=int(saved.get("home_goals") if saved.get("home_goals") is not None else (guess["home_goals"] or 0)))
        ag = c4.number_input("Away goals", min_value=0, max_value=30, value=int(saved.get("away_goals") if saved.get("away_goals") is not None else (guess["away_goals"] or 0)))
        date = c5.date_input("Date", value=saved.get("date") or guess["date"] or None, format="DD/MM/YYYY")
        c6, c7 = st.columns(2)
        comp = c6.text_input("Competition and round", value=saved.get("competition", ""), placeholder="A-League Men · Round 7")
        venue = c7.text_input("Venue", value=saved.get("venue", ""), placeholder="Allianz Stadium")
        headline = st.text_input("Headline (optional)", value=saved.get("headline", ""), placeholder="One line that sums up the match")
        if st.form_submit_button("Save match details", type="primary"):
            ss["match"] = {"home": home.strip(), "away": away.strip(), "home_goals": int(hg), "away_goals": int(ag),
                           "date": date, "competition": comp.strip(), "venue": venue.strip(), "headline": headline.strip()}
            st.success("Saved for this session. Head to **Generate** when it is ready (phase 3).", icon=":material/check_circle:")

    pages = [p for k in uploads for p in ingest.KINDS[k].unlocks]
    st.markdown("**Report pages ready:** " + " · ".join(pages))


# ----------------------------------------------------------------- templates
def _templates() -> None:
    st.divider()
    with st.expander("Templates and where to get each file"):
        st.markdown("Download a template, open it in Excel, paste your numbers under the headers, save as CSV and upload it here.")
        for kind in ingest.KINDS.values():
            c1, c2 = st.columns([3, 1])
            c1.markdown(f"**{kind.label}** (kind {kind.code}) — {kind.description}  \n*Where from:* {kind.source}  \n*Unlocks:* {' · '.join(kind.unlocks)}")
            c2.download_button(
                "Template", ingest.template_csv(kind), file_name=f"template_{kind.key}.csv", mime="text/csv",
                key=f"tpl-{kind.key}", icon=":material/download:", use_container_width=True,
            )


# ----------------------------------------------------------------- page
def render() -> None:
    ss = _state()
    st.title("Upload and preview")
    st.markdown("Drop in one or more files. They are read in memory for this browser session only and are never saved.")

    files = st.file_uploader("CSV or Excel files", type=ACCEPTED, accept_multiple_files=True, label_visibility="collapsed")

    with st.expander("No file handy? Try a sample", expanded=not files and not ss["sample_files"]):
        st.caption("Invented data in the three accepted formats. Loads into this session exactly like an upload.")
        cols = st.columns(len(SAMPLES) + 1)
        for i, (label, fname) in enumerate(SAMPLES):
            if cols[i].button(label, key=f"sample-{fname}", use_container_width=True):
                _load_sample(fname)
                st.rerun()
        if ss["sample_files"] and cols[-1].button("Clear samples", key="clear-samples", use_container_width=True):
            ss["sample_files"].clear()
            ss["uploads"].clear()
            ss.pop("match", None)
            st.rerun()

    shown = 0
    for f in files or []:
        _show_file(f.name, f.getvalue())
        shown += 1
    for name, data in ss["sample_files"].items():
        _show_file(name, data, is_sample=True)
        shown += 1

    if not shown:
        st.info("No files yet. Drag a CSV or Excel export here, click **Browse files**, or load a sample above.", icon=":material/upload_file:")
        ss["uploads"].clear()

    _match_form()
    _templates()
