# Malahit DSP3 SWL report clip maker

A tool to generate SWL reports from Malahit DSP3 screenshots and audio records.

<video src="swl-report.mp4" controls width="720"></video>

## Run with uvx

Install uv first:

https://github.com/astral-sh/uv#installation

Fetch ffmpeg, ffprobe, and the Roboto font into the user cache:

```bash
uvx malahit-clip fetch-assets
```

Create a clip:

```bash
uvx malahit-clip make \
  -i screenshot.bmp \
  -a recording.wav \
  -d "Station description" \
  -o report.mp4 \
  --receiver "MALAHIT DSP3" \
  --antenna "K-480WLA" \
  --location "Kemerovo"
```
