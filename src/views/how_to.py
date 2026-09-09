"""How to use – plain-language help inside the app."""
import streamlit as st


def render() -> None:
    st.title("How to use")

    st.markdown("#### Making a report")
    st.markdown(
        """
1. **Open the link** on a laptop or phone. No install needed.
2. **Enter the PIN.** The app stays unlocked until you close the tab, click **Lock the app**, or leave it idle for 30 minutes.
3. **Upload your file** on the *Upload and preview* page. CSV or Excel exports from Wyscout or the Best11 app both work.
4. **Check the green tick.** If something is missing the app names the column so you can fix the file.
5. **Click Generate** (coming in phase 3), preview the report and **Download** it as a PDF.
"""
    )

    st.markdown("#### Privacy")
    st.markdown(
        """
- Files are read in memory for your browser session only. They are never written to disk and there is no database.
- Close the tab and the data is gone. Nobody else can see what you uploaded.
- Usage statistics are switched off.
"""
    )

    st.markdown("#### Changing the PIN")
    st.markdown(
        """
The PIN is not in the code. It lives in the app's **Secrets**:

- **On Streamlit Community Cloud:** open the app dashboard → **Settings** → **Secrets**, change the line `APP_PIN = "1234"`, and save. The app restarts with the new PIN within a minute.
- **Running locally:** edit `.streamlit/secrets.toml` and restart the app.

Wrong PIN five times locks that browser for 15 minutes. Twenty wrong attempts from anywhere lock everyone out for 15 minutes.
"""
    )

    st.markdown("#### Something not working?")
    st.markdown(
        """
- **"The app has no PIN set up yet"** – add `APP_PIN` to the secrets as described above.
- **File will not read** – open it in Excel and re-save as CSV (UTF-8) or .xlsx.
- **The page looks stuck** – refresh the browser. You will need to enter the PIN again.
"""
    )
