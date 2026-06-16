# One-command pipeline: Docker render -> ffmpeg optimize -> web assets.
#
#   make            # build image, render, optimize, copy web assets
#   make image      # build the Docker image (font baked in)
#   make render     # render the scene at 1080p60 via Docker
#   make optimize   # produce web-ready mp4 / webm / poster
#   make assets     # copy optimized files into web/assets/
#   make clean      # remove generated media + optimized files

IMAGE       := name-intro
SCRIPT      := TwoLetters.py
SCENE       := FullName_FFTReveal
QUALITY     := -qh
RENDER_OUT  := media/videos/TwoLetters/1080p60/$(SCENE).mp4

.PHONY: all image render optimize assets clean

all: image render optimize assets
	@echo "Done. Web assets are in web/assets/"

image:
	docker build -t $(IMAGE) .

render: image
	docker run --rm -v "$(PWD):/manim" $(IMAGE) \
		manim $(QUALITY) $(SCRIPT) $(SCENE)

# Web-streaming MP4 (+faststart), transparent WebM, and a first-frame poster.
optimize: $(RENDER_OUT)
	ffmpeg -y -i "$(RENDER_OUT)" \
		-vcodec libx264 -crf 23 -preset slow -pix_fmt yuv420p -movflags +faststart \
		intro.mp4
	ffmpeg -y -i "$(RENDER_OUT)" -c:v libvpx-vp9 -pix_fmt yuva420p intro.webm
	ffmpeg -y -i intro.mp4 -frames:v 1 intro-poster.png

assets: optimize
	mkdir -p web/assets
	cp intro.mp4 intro.webm intro-poster.png web/assets/
	cp fonts/GreatVibes-Regular.ttf web/assets/

clean:
	rm -rf media intro.mp4 intro.webm intro-poster.png web/assets/*.mp4 web/assets/*.webm web/assets/*.png
