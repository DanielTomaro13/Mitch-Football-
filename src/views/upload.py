"""
Upload and preview.

Phase 1: accept CSV / Excel files, read them in memory, show a preview.
Phase 2 will add file-kind detection, validation and column matching here.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

ACCEPTED = ["csv", "xlsx", "xls"]


def _read(file) -> pd.DataFrame:
    """Read an uploaded file into a DataFrame without touching the disk."""
    name = file.name.lower()
    data = file.getvalue()
    if name.endswith(".csv"):
        # utf-8-sig strips the BOM that Excel and Wyscout exports often add
        return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
    return pd.read_excel(io.BytesIO(data))


def render() -> None:
    st.title("Upload and preview")
    st.markdown(
        "Drop in one or more files. They are read in memory for this browser "
        "session only and are never saved."
    )

    files = st.file_uploader(
        "CSV or Excel files", type=ACCEPTED, accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not files:
        st.info("No files yet. Drag a CSV or Excel export here, or click **Browse files**.", icon=":material/upload_file:")
        return

    for file in files:
        with st.container(border=True):
            st.markdown(f"**{file.name}**  ·  {file.size / 1024:.0f} KB")
            try:
                df = _read(file)
            except Exception as err:  # noqa: BLE001 - show the user something useful
                st.error(f"Could not read this file. Is it a normal CSV or Excel export? ({err})")
                continue

            st.success(f"Read {len(df):,} rows and {len(df.columns)} columns.", icon=":material/check_circle:")
            st.caption("Columns found: " + ", ".join(f"`{c}`" for c in map(str, df.columns)))
            st.dataframe(df.head(25), use_container_width=True, hide_index=True)
            st.caption("Phase 2 will recognise the file type here and tell you which report pages it unlocks.")
