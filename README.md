# Mitch Football – Match Report Generator

An internal web tool: open a link, type the team PIN, upload a Wyscout-style CSV, click **Generate**, download a match report as a PDF. Nothing you upload is stored.

- **Plan:** [PLAN.md](PLAN.md) (phases, accepted CSV kinds, report pages)
- **Demo of the finished report:** [demo/output/demo_match_report.pdf](demo/output/demo_match_report.pdf) (invented data)
- **Current status:** Phases 1 and 2 done (PIN gate; upload, file recognition, column matching, templates, sample files, match details). Phase 3 (charts and report pages) next.
- **Sample files:** [samples/](samples/) has one invented file in each accepted format. Regenerate with `.venv/bin/python demo/make_samples.py`.
- **Tests:** `.venv/bin/python -m pytest -q`

## Non-negotiables

- **PIN at the door.** One shared 4-digit PIN kept in the hosting *Secrets*, never in the code. Five wrong attempts lock that browser for 15 minutes; 20 wrong attempts from anywhere lock everyone for 15 minutes. Idle sessions re-lock after 30 minutes.
- **Nothing stored.** Files are read in memory for the browser session only. No database, no file writes, usage statistics switched off.
- **Non-technical users.** One button, plain-language errors, downloadable templates (phase 2).

## Put it online (Streamlit Community Cloud, free)

You only do this once. After that, every push to GitHub updates the live app automatically.

1. Go to <https://share.streamlit.io> and sign in with the GitHub account that owns this repo.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Repository: `DanielTomaro13/Mitch-Football-` · Branch: `main` · Main file path: `app.py`.
4. Open **Advanced settings** → **Secrets** and paste:
   ```toml
   APP_PIN = "1234"
   ```
   (choose your own four digits).
5. Click **Deploy**. In a minute or two you get a link like `https://mitch-football.streamlit.app`. Share the link and the PIN with the team.

**Changing the PIN later:** app dashboard → **Settings** → **Secrets** → edit the line → **Save**. The app restarts on its own.

**Keeping the link private:** in the app's **Settings** → **Sharing**, leave it *unlisted* (the default) so it never appears in Streamlit's public gallery. If the data ever becomes sensitive you can switch the app to *private* and allow specific email addresses, with no code changes.

## Run it on your own computer

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # then edit the PIN
.venv/bin/streamlit run app.py
```

Then open <http://localhost:8501>.

## Rebuild the demo report

```bash
.venv/bin/python demo/make_demo_report.py
```

Outputs a six-page PDF and one PNG per page into `demo/output/`.

## Layout

```
app.py                       entry point: PIN gate, then the screens
src/auth.py                  PIN check, lockout, idle timeout
src/views/home.py            home screen and build status
src/views/upload.py          upload and in-memory preview (phase 2 adds detection)
src/views/how_to.py          help page inside the app
demo/make_demo_report.py     builds the demo report (starting point for phase 3 charts)
.streamlit/config.toml       theme, telemetry off, upload size limit
.streamlit/secrets.toml.example   what the Secrets should contain
PLAN.md                      the build plan
```
