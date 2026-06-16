# Reproducible Manim render with the cursive font baked in.
# The scene uses Text() (Pango), so the base image is enough — no LaTeX needed.
FROM manimcommunity/manim:stable

USER root

# Install the cursive font so Manim's Text() can resolve "Great Vibes"
COPY fonts/GreatVibes-Regular.ttf /usr/share/fonts/truetype/greatvibes/
RUN fc-cache -f -v

USER manimuser
