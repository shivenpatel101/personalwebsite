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

## Deploy (live site)

One-time setup in GitHub:

1. Go to **Actions** → **Deploy site to GitHub Pages** → **Run workflow**
   (this creates the `gh-pages` branch from `web/`)
2. Open https://github.com/shivenpatel101/personalwebsite/settings/pages
3. Under **Build and deployment → Source**, choose **Deploy from a branch**
4. Set **Branch** to `gh-pages` and **Folder** to `/ (root)`, then **Save**

After the workflow finishes (about 1 minute), the site is live at:

**https://shivenpatel101.github.io/personalwebsite/**

Every push to `main` redeploys automatically. The intro plays on every visit
(client-side); adjust `PLAY_FREQUENCY` in `web/index.html` to change that.

## Run locally

```bash
cd web
python3 -m http.server 8000
```

Open http://localhost:8000
