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

## Deploy

In the GitHub repo: **Settings → Pages → Source → "GitHub Actions"**. Each push
to `main` publishes `web/`. The intro plays on every visit (client-side); adjust
`PLAY_FREQUENCY` in `web/index.html` to change that.
