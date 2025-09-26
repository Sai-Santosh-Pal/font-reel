"""
font_reel.py
Create a vertical "reel" (1080x1920) MP4 where the SAME text is displayed
while the font family changes (Google Fonts). White text on black background.

This script auto-installs its dependencies:
    pillow, requests, imageio[ffmpeg]
"""

import os, sys, subprocess, shutil
from pathlib import Path

# ---- Auto-install required packages ----
REQUIRED = ["pillow", "requests", "imageio[ffmpeg]"]
for pkg in REQUIRED:
    try:
        __import__(pkg.split("[")[0])  # import pillow, requests, imageio
    except ImportError:
        print(f"Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

# ---- Now safe to import ----
import requests
import imageio.v3 as iio
from PIL import Image, ImageDraw, ImageFont


# ---- Configuration ----
TEXT = "YOUR TEXT HERE"
OUTPUT = "font_reel_1080x1920.mp4"
WIDTH, HEIGHT = 1080, 1920
FPS = 30
SECONDS_PER_FONT = 2
FONTS_DIR = Path("downloaded_fonts")

GOOGLE_FONTS = [
    ("Roboto", "roboto/Roboto-Regular.ttf"),
    ("Montserrat", "montserrat/Montserrat-Regular.ttf"),
    ("Poppins", "poppins/Poppins-Regular.ttf"),
    ("Lora", "lora/Lora-Regular.ttf"),
    ("Oswald", "oswald/Oswald-Regular.ttf"),
    ("PlayfairDisplay", "playfairdisplay/PlayfairDisplay-Regular.ttf"),
]

GITHUB_RAW = "https://github.com/google/fonts/raw/main/ofl"
# ---- End configuration ----


def download_font(relative_path: str, dest_dir: Path):
    url = f"{GITHUB_RAW}/{relative_path}"
    local = dest_dir / Path(relative_path).name
    if local.exists():
        return str(local)
    r = requests.get(url, stream=True, timeout=30)
    if r.status_code == 200:
        dest_dir.mkdir(parents=True, exist_ok=True)
        with open(local, "wb") as f:
            f.write(r.content)
        return str(local)
    return None


def fit_font(draw, text, font_path, max_width, max_height):
    lo, hi = 6, 400
    best = None
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            f = ImageFont.truetype(font_path, mid)
        except:
            return None
        w, h = draw.textsize(text, font=f)
        if w <= max_width and h <= max_height:
            best = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def create_frame(text, font_path):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
    draw = ImageDraw.Draw(img)
    max_w = int(WIDTH * 0.9)
    max_h = int(HEIGHT * 0.5)
    font = fit_font(draw, text, font_path, max_w, max_h)
    if font is None:
        font = ImageFont.load_default()
    w, h = draw.textsize(text, font=font)
    x = (WIDTH - w) // 2
    y = (HEIGHT - h) // 2
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    return img


def main():
    font_files = []
    for family, relpath in GOOGLE_FONTS:
        local = download_font(relpath, FONTS_DIR)
        if local:
            font_files.append(local)

    if not font_files:
        print("No fonts downloaded, aborting.")
        return

    frames = []
    frames_per_font = SECONDS_PER_FONT * FPS

    for font_path in font_files:
        for _ in range(frames_per_font):
            img = create_frame(TEXT, font_path)
            frames.append(img)

    # Convert PIL images to numpy arrays for imageio
    frames_np = [iio.asarray(f) for f in frames]

    print(f"Writing video with {len(frames)} frames...")
    iio.imwrite(
        OUTPUT,
        frames_np,
        fps=FPS,
        codec="libx264",
        quality=8,
    )
    print(f"✅ Saved {OUTPUT}")


if __name__ == "__main__":
    main()
