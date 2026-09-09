"""
PIN gate for the app.

- The PIN is read from Streamlit secrets (APP_PIN) or the APP_PIN environment
  variable. It is never written into the code or the repository.
- Unlock state lives in the browser session only (st.session_state).
- Per-session lockout: 5 wrong attempts -> locked for 15 minutes.
- Process-wide brake: if 20 wrong attempts arrive from any sessions within
  15 minutes, every session is locked for 15 minutes. This blunts guessing
  by someone who keeps opening new tabs.
- Idle timeout: 30 minutes without activity re-locks the session.
"""
from __future__ import annotations

import hmac
import os
import time

import streamlit as st

MAX_ATTEMPTS = 5
LOCK_SECONDS = 15 * 60
IDLE_SECONDS = 30 * 60
GLOBAL_MAX_FAILURES = 20

# Timestamps of failed attempts across all sessions in this server process.
_global_failures: list[float] = []


# ----------------------------------------------------------------- helpers
def get_pin() -> str | None:
    """Return the configured PIN, or None if it has not been set up."""
    pin = None
    try:
        pin = st.secrets.get("APP_PIN")
    except Exception:  # no secrets file at all
        pin = None
    if not pin:
        pin = os.environ.get("APP_PIN")
    return str(pin).strip() if pin else None


def _prune_global() -> None:
    now = time.time()
    _global_failures[:] = [t for t in _global_failures if now - t < LOCK_SECONDS]


def _global_locked_for() -> int:
    """Seconds remaining on the process-wide lock, or 0."""
    _prune_global()
    if len(_global_failures) < GLOBAL_MAX_FAILURES:
        return 0
    return int(LOCK_SECONDS - (time.time() - _global_failures[-GLOBAL_MAX_FAILURES]))


def _session_locked_for() -> int:
    """Seconds remaining on this session's lock, or 0."""
    until = st.session_state.get("locked_until", 0)
    remaining = int(until - time.time())
    if remaining <= 0 and until:
        st.session_state.pop("locked_until", None)
        st.session_state["pin_attempts"] = 0
    return max(remaining, 0)


def _minutes(seconds: int) -> str:
    m = max(1, -(-seconds // 60))  # ceiling
    return f"{m} minute{'s' if m != 1 else ''}"


# ----------------------------------------------------------------- public API
def is_authenticated() -> bool:
    ss = st.session_state
    if not ss.get("authed"):
        return False
    if time.time() - ss.get("last_seen", 0) > IDLE_SECONDS:
        logout()
        ss["idle_message"] = "You were logged out after 30 minutes of inactivity."
        return False
    ss["last_seen"] = time.time()
    return True


def logout() -> None:
    for key in ("authed", "last_seen", "uploads"):
        st.session_state.pop(key, None)


def check_pin(entered: str) -> bool:
    """Compare in constant time. Records failures for lockout."""
    expected = get_pin()
    if not expected:
        return False
    ok = hmac.compare_digest(entered.strip().encode(), expected.encode())
    if ok:
        st.session_state["pin_attempts"] = 0
        st.session_state["authed"] = True
        st.session_state["last_seen"] = time.time()
        return True
    _global_failures.append(time.time())
    attempts = st.session_state.get("pin_attempts", 0) + 1
    st.session_state["pin_attempts"] = attempts
    if attempts >= MAX_ATTEMPTS:
        st.session_state["locked_until"] = time.time() + LOCK_SECONDS
    return False


def render_pin_screen() -> None:
    """Full-page PIN prompt. Call st.stop() after this."""
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)
        st.markdown("## ⚽ Match Report Generator")
        st.caption("Internal tool. Enter the team PIN to continue.")

        if not get_pin():
            st.error(
                "The app has no PIN set up yet. Add `APP_PIN = \"1234\"` to the app's "
                "secrets (Streamlit Cloud: app settings → Secrets; locally: "
                "`.streamlit/secrets.toml`). See the README."
            )
            return

        if msg := st.session_state.pop("idle_message", None):
            st.info(msg)

        locked = max(_session_locked_for(), _global_locked_for())
        if locked:
            st.warning(f"Too many wrong attempts. Try again in {_minutes(locked)}.")
            return

        with st.form("pin_form", border=True):
            entered = st.text_input(
                "PIN", type="password", max_chars=12, placeholder="• • • •",
                label_visibility="collapsed", autocomplete="off",
            )
            submitted = st.form_submit_button("Unlock", type="primary", use_container_width=True)

        if submitted:
            if not entered:
                st.warning("Type the PIN first.")
            elif check_pin(entered):
                st.rerun()
            else:
                left = MAX_ATTEMPTS - st.session_state.get("pin_attempts", 0)
                if left <= 0:
                    st.error(f"Wrong PIN. Locked for {_minutes(LOCK_SECONDS)}.")
                else:
                    st.error(f"Wrong PIN. {left} attempt{'s' if left != 1 else ''} left.")

        st.markdown("")
        st.caption(
            "🔒 Nothing you upload is stored. Files are read in memory for this "
            "browser session only and disappear when you close the tab."
        )
