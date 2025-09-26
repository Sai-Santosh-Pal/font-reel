#!/usr/bin/env python3
"""
font_reel.py
Create a vertical "reel" (1080x1920) MP4 where the SAME text is displayed
while the font family changes (Google Fonts). White text on black background.

Usage: python font_reel.py
"""

import os
import sys
import math
import shutil
from pathlib import Path

# ---- Configuration ----
TEXT = "YOUR TEXT HERE"  # change this to what you want displayed
OUTPUT = "font_reel_1080x1920.mp4"
WIDTH, HEIGHT = 1080, 1920  # reel format (9:16)
FPS = 30
SECONDS_PER_FONT = 2.0  # how long each font stays on-screen
FONTS_DIR = Path("downloaded_fonts")
TEMP_FRAMES_DIR = Path("frames_temp")
# Google Fonts families and the ttf file names we will download from Google Fonts GitHub.
# NOTE: filenames are case-sensitive on some systems.
GOOGLE_FONTS = [
    # (family-name, relative-ttf-path)
    ("Roboto", "roboto/Roboto-Regular.ttf"),
    ("Montserrat", "montserrat/Montserrat-Regular.ttf"),
    ("Poppins", "poppins/Poppins-Regular.ttf"),
    ("Lora", "lora/Lora-Regular.ttf"),
    ("Oswald", "oswald/Oswald-Regular.ttf"),
    ("PlayfairDisplay", "playfairdisplay/PlayfairDisplay-Regular.ttf"),
    ("Merriweather", "merriweather/Merriweather-Regular.ttf"),
    ("Raleway", "raleway/Raleway-Regular.ttf"),
    ("Nunito", "nunito/Nunito-Regular.ttf"),
    ("SourceSansPro", "sourcesanspro/SourceSansPro-Regular.ttf"),
]
# Base raw URL for Google Fonts GitHub repository
GITHUB_RAW = "https://github.com/google/fonts/raw/main/ofl"

# ---- End configuration ----

def ensure_packages():
    """Install packages if missing (requests, pillow, moviepy)."""
    try:
        import requests, PIL, moviepy  # noqa: F401
    except Exception:
        print("Installing required packages (requests, pillow, moviepy)...")
        os.system(f"{sys.executable} -m pip install --upgrade pip > /dev/null")
        os.system(f"{sys.executable} -m pip install requests pillow moviepy > /dev/null")
    # re-import
    global requests, Image, ImageDraw, ImageFont, VideoClip, ImageSequenceClip
    import requests
    from PIL import Image, ImageDraw, ImageFont
    from moviepy.editor import ImageSequenceClip
    return requests, Image, ImageDraw, ImageFont, ImageSequenceClip

def download_font(relative_path: str, dest_dir: Path):
    """Download a ttf from Google Fonts GitHub raw. Returns local path or None on fail."""
    url = f"{GITHUB_RAW}/{relative_path}"
    local = dest_dir / Path(relative_path).name
    if local.exists():
        print(f"Font already downloaded: {local}")
        return str(local)
    print(f"Downloading font: {url}")
    try:
        r = requests.get(url, stream=True, timeout=30)
        if r.status_code == 200:
            dest_dir.mkdir(parents=True, exist_ok=True)
            with open(local, "wb") as f:
                shutil.copyfileobj(r.raw, f)
            print(f"Saved to {local}")
            return str(local)
        else:
            print(f"Failed to download {url} (status {r.status_code})")
            return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def fit_text_on_image(draw, text, font_path, max_width, max_height, ImageFont):
    """
    Return an ImageFont.FreeTypeFont sized such that text fits in max_width.
    We'll binary-search font size.
    """
    # binary search size
    lo, hi = 6, 320  # font size bounds
    best_font = None
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            f = ImageFont.truetype(font_path, mid)
        except OSError:
            # if font can't be loaded, break
            return None
        w, h = draw.textsize(text, font=f)
        if w <= max_width and h <= max_height:
            best_font = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best_font

def create_frame(img_w, img_h, text, font_path, Image, ImageDraw, ImageFont):
    """Create a single PIL image with centered text using the given font."""
    img = Image.new("RGB", (img_w, img_h), color=(0, 0, 0))  # black background
    draw = ImageDraw.Draw(img)

    # define margins: allow text to occupy up to ~80% width and ~50% height
    max_w = int(img_w * 0.9)
    max_h = int(img_h * 0.5)

    # fit font
    font = fit_text_on_image(draw, text, font_path, max_w, max_h, ImageFont)
    if font is None:
        # fallback to default PIL font
        font = ImageFont.load_default()

    w, h = draw.textsize(text, font=font)
    x = (img_w - w) // 2
    y = (img_h - h) // 2

    # draw white text
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    return img

def main():
    requests, Image, ImageDraw, ImageFont, ImageSequenceClip = ensure_packages()

    # Prepare directories
    FONTS_DIR.mkdir(exist_ok=True)
    if TEMP_FRAMES_DIR.exists():
        shutil.rmtree(TEMP_FRAMES_DIR)
    TEMP_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

    # Attempt to download fonts
    font_files = []
    for family, relpath in GOOGLE_FONTS:
        local = download_font(relpath, FONTS_DIR)
        if local:
            font_files.append((family, local))
        else:
            print(f"Warning: couldn't download {family}. It will be skipped.")

    # If no fonts downloaded, try some system fonts fallback by name
    if not font_files:
        print("No fonts downloaded. Trying some common system fonts as fallback.")
        fallback_systems = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for p in fallback_systems:
            if Path(p).exists():
                font_files.append(("system", p))

    if not font_files:
        print("No fonts available. Aborting.")
        return

    frames = []
    frame_count_per_font = max(1, int(round(SECONDS_PER_FONT * FPS)))

    print(f"Rendering frames: {len(font_files)} fonts x {frame_count_per_font} frames each ...")
    frame_index = 0
    for family, font_path in font_files:
        print(f"Rendering font: {family} ({font_path})")
        for i in range(frame_count_per_font):
            img = create_frame(WIDTH, HEIGHT, TEXT, font_path, Image, ImageDraw, ImageFont)
            frame_filename = TEMP_FRAMES_DIR / f"frame_{frame_index:05d}.png"
            img.save(frame_filename)
            frames.append(str(frame_filename))
            frame_index += 1

    # Use MoviePy to assemble video
    print("Assembling video with MoviePy...")
    clip = ImageSequenceClip(frames, fps=FPS)
    # MoviePy expects (w,h) same orientation; ensure size
    clip = clip.set_duration(len(frames) / FPS)
    clip.write_videofile(OUTPUT, codec="libx264", audio=False, fps=FPS, threads=4)

    print(f"Done! Saved: {OUTPUT}")
    print("Cleaning up temporary frames...")
    # optional: remove frames
    shutil.rmtree(TEMP_FRAMES_DIR)
    print("Finished.")

if __name__ == "__main__":
    main()
