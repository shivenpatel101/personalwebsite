# personalwebsite

Personal site with a Fourier-series name intro (Manim) that plays on every
visit, then docks the wordmark to the corner and reveals the page.

## Layout

```
render/            Generates the intro video
  TwoLetters.py      Manim scene (FullName_FFTReveal) — draws "Shiven Patel"
  Dockerfile         Manim image with the Great Vibes font baked in
  Makefile           render -> ffmpeg optimize -> copy to ../web/assets
  fonts/             Great Vibes (used by the render)

web/               Deployable static site (served by GitHub Pages)
  index.html         Intro overlay + blue-themed homepage
  assets/            Committed intro.mp4/.webm, poster, and the font

.github/workflows/
  deploy.yml         Deploys web/ to GitHub Pages on push to main
```

Python project config (`pyproject.toml`, `uv.lock`, `.python-version`) lives at
the root.

## Rebuild the intro video

Requires Docker and ffmpeg:

```bash
cd render
make            # build image, render at 1080p60, optimize, copy to ../web/assets
```

Then commit the updated files in `web/assets/` and push — GitHub Pages
redeploys automatically.

## Deploy (live site) — GitHub Actions

This repo uses the **official GitHub Actions Pages workflow** (not a `gh-pages`
branch). The workflow uploads `web/` and deploys it with `deploy-pages`.

### One-time setup (do this first)

1. **Enable Pages for GitHub Actions**
   - Open https://github.com/shivenpatel101/personalwebsite/settings/pages
   - Under **Build and deployment → Source**, select **GitHub Actions** (not
     "Deploy from a branch")
   - Save if prompted

2. **Run the deploy workflow**
   - Open https://github.com/shivenpatel101/personalwebsite/actions
   - Click **Deploy site to GitHub Pages** → **Run workflow** → **Run workflow**
   - Wait for a green checkmark (~1 minute)

3. **Open the live site**
   - https://shivenpatel101.github.io/personalwebsite/

### If the workflow fails — what to check

| Step that failed | What it usually means | What to do |
|------------------|----------------------|------------|
| **Configure Pages** | Pages is not set to **GitHub Actions** | Settings → Pages → Source → **GitHub Actions** |
| **Deploy to GitHub Pages** | `github-pages` environment missing or blocked | Settings → Environments → ensure **github-pages** exists; allow deployments from `main` |
| **Upload site** | `web/` missing or empty in the repo | Confirm `web/index.html` and `web/assets/` are committed on `main` |
| Workflow does not run | Wrong branch or Actions disabled | Push to `main`; Settings → Actions → General → allow workflows |

**Configure Pages** error text to look for:
`Get Pages site failed` → almost always means step 1 above was skipped.

Every push to `main` redeploys automatically after setup. The intro plays on every
visit (client-side); adjust `PLAY_FREQUENCY` in `web/index.html` to change that.

## Run locally

```bash
cd web
python3 -m http.server 8000
```

Open http://localhost:8000
