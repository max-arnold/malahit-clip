import argparse
import datetime
import platform
import stat
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from platformdirs import user_cache_dir
from PIL import Image, ImageDraw, ImageFont


APP_NAME = "malahit-clip"
FONT_URLS = {
    "https://github.com/googlefonts/roboto-3-classic/releases/download/v3.015/Roboto_v3.015.zip": (
        "hinted/static/Roboto-Regular.ttf",
    ),
}
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
FFMPEG_URLS = {
    "linux-amd64": {
        "https://ffmpeg.martin-riedl.de/download/linux/amd64/1774550169_8.1/ffmpeg.zip": (
            "ffmpeg",
        ),
        "https://ffmpeg.martin-riedl.de/download/linux/amd64/1774550169_8.1/ffprobe.zip": (
            "ffprobe",
        ),
    },
    "linux-arm64": {
        "https://ffmpeg.martin-riedl.de/download/linux/arm64/1774548896_8.1/ffmpeg.zip": (
            "ffmpeg",
        ),
        "https://ffmpeg.martin-riedl.de/download/linux/arm64/1774548896_8.1/ffprobe.zip": (
            "ffprobe",
        ),
    },
    "darwin-amd64": {
        "https://ffmpeg.martin-riedl.de/download/macos/amd64/1774556648_8.1/ffmpeg.zip": (
            "ffmpeg",
        ),
        "https://ffmpeg.martin-riedl.de/download/macos/amd64/1774556648_8.1/ffprobe.zip": (
            "ffprobe",
        ),
    },
    "darwin-arm64": {
        "https://ffmpeg.martin-riedl.de/download/macos/arm64/1774549676_8.1/ffmpeg.zip": (
            "ffmpeg",
        ),
        "https://ffmpeg.martin-riedl.de/download/macos/arm64/1774549676_8.1/ffprobe.zip": (
            "ffprobe",
        ),
    },
    "windows-amd64": {
        "https://github.com/GyanD/codexffmpeg/releases/download/8.1.1/ffmpeg-8.1.1-essentials_build.zip": (
            "ffmpeg.exe",
            "ffprobe.exe",
        ),
    },
    "windows-arm64": {
        "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-n8.1-latest-winarm64-lgpl-8.1.zip": (
            "ffmpeg.exe",
            "ffprobe.exe",
        ),
    },
}


def fetch_and_extract(url, dst, members):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    try:
        print(f"Downloading {url} to {tmp.name}")
        parsed = urlparse(url)
        request = urllib.request.Request(
            url,
            headers={
                "Referer": f"{parsed.scheme}://{parsed.netloc}/",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(request) as response, open(tmp.name, "wb") as out:
            out.write(response.read())
        with zipfile.ZipFile(tmp.name) as z:
            for member in members:
                name = (
                    member
                    if member in z.namelist()
                    else next(
                        n for n in z.namelist() if Path(n).name == Path(member).name
                    )
                )
                with z.open(name) as src, open(dst / Path(member).name, "wb") as out:
                    out.write(src.read())
    finally:
        Path(tmp.name).unlink(missing_ok=True)


def ensure_assets(target_platform=None, force=False):
    cache = Path(user_cache_dir(APP_NAME))
    cache.mkdir(parents=True, exist_ok=True)
    system = platform.system().lower()
    arch = "arm64" if platform.machine().lower() in {"aarch64", "arm64"} else "amd64"
    target_platform = target_platform or f"{system}-{arch}"
    exe = ".exe" if target_platform.startswith("windows-") else ""
    paths = {
        "ffmpeg": cache / f"ffmpeg{exe}",
        "ffprobe": cache / f"ffprobe{exe}",
        "roboto": cache / "Roboto-Regular.ttf",
    }
    if force or not all(p.exists() for p in paths.values()):
        for url, members in FFMPEG_URLS[target_platform].items():
            fetch_and_extract(url, cache, members)
        for url, members in FONT_URLS.items():
            fetch_and_extract(url, cache, members)
        for path in (paths["ffmpeg"], paths["ffprobe"]):
            path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return paths


def get_wrapped_text(text, font, line_length):
    lines = [""]
    for word in text.split():
        line = f"{lines[-1]} {word}".strip()
        if font.getlength(line) <= line_length:
            lines[-1] = line
        else:
            lines.append(word)
    return "\n".join(lines)


def make_clip(args):
    assets = ensure_assets()
    canvas = Image.new("RGB", (720, 352))
    draw = ImageDraw.Draw(canvas)
    draw.line(
        [(10, 11), (501, 11), (501, 341), (10, 341), (10, 11), (501, 11)],
        fill="#9d9781",
        width=7,
        joint="curve",
    )
    draw.line(
        [(512, 8), (710, 8), (710, 344), (512, 344), (512, 8)], fill="#9d9781", width=1
    )

    image = Path(args.image)
    dt = datetime.datetime.fromtimestamp(image.stat().st_mtime).strftime(
        "%Y-%m-%d %H:%M"
    )
    img = Image.open(image)
    if img.size[0] > 480 or img.size[1] > 320:
        img = img.resize(
            (480, int(img.size[1] * (480 / img.size[0]))), Image.Resampling.LANCZOS
        )
    canvas.paste(img, (16, 17))

    font_label = ImageFont.truetype(assets["roboto"], 12)
    font_text = ImageFont.truetype(assets["roboto"], 18)
    font_desc = ImageFont.truetype(assets["roboto"], 16)
    for y, label, value in [
        (13, "Recorded with:", args.receiver),
        (63, "Antenna:", args.antenna),
        (113, "Location:", args.location),
        (163, "Date and time:", dt),
    ]:
        draw.text((520, y), label, fill="#9d9781", font=font_label)
        draw.text((520, y + 16), value, fill="#ffffff", font=font_text)
    draw.text((520, 213), "Description:", fill="#9d9781", font=font_label)
    draw.multiline_text(
        (520, 229),
        get_wrapped_text(args.description, font_desc, 182),
        fill="#ffffff",
        font=font_desc,
    )

    cover = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    cover.close()
    try:
        canvas.save(cover.name, "PNG")
        subprocess.run(
            [
                assets["ffmpeg"],
                "-loop",
                "1",
                "-framerate",
                "10",
                "-i",
                cover.name,
                "-i",
                args.audio,
                "-map",
                "0",
                "-map",
                "1:a",
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-preset",
                "ultrafast",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-max_interleave_delta",
                "100M",
                "-vf",
                "fps=10,format=yuv420p",
                "-shortest",
                "-y",
                args.output,
            ],
            check=True,
        )
    finally:
        Path(cover.name).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    fetch_assets = subparsers.add_parser("fetch-assets")
    fetch_assets.add_argument("--platform", choices=FFMPEG_URLS)
    fetch_assets.add_argument("--force", action="store_true")
    make = subparsers.add_parser("make")
    make.add_argument("-i", "--image", required=True)
    make.add_argument("-a", "--audio", required=True)
    make.add_argument("-d", "--description", required=True)
    make.add_argument("-o", "--output", required=True)
    make.add_argument("--receiver", default="MALAHIT DSP3")
    make.add_argument("--antenna", default="")
    make.add_argument("--location", default="")
    args = parser.parse_args()
    if args.command == "fetch-assets":
        for key, path in ensure_assets(args.platform, args.force).items():
            print(f"{key}: {path}")
    elif args.command == "make":
        make_clip(args)
