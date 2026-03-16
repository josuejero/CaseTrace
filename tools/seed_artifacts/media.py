\"\"\"Media helpers to synthesize photo artifacts.\"\"\"
from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw

from tools.seed_artifacts.data import PHOTOS


def create_photos(case_dir: Path) -> None:
    media_dir = case_dir / "files" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    for file_name, timestamp, summary, lat, lon, device, orientation in PHOTOS:
        img = Image.new("RGB", (640, 480), color=(230, 240, 255))
        draw = ImageDraw.Draw(img)
        draw.text((24, 36), file_name, fill=(0, 0, 0))
        draw.text((24, 100), summary, fill=(30, 30, 30))
        img_path = media_dir / file_name
        exif = img.getexif()
        exif[306] = timestamp.replace("T", " ").replace("Z", "")
        exif[36867] = exif[306]
        exif[271] = "Google"
        exif[272] = device
        exif[274] = orientation
        gps_info = {
            1: "N" if lat >= 0 else "S",
            2: _to_dms(lat),
            3: "E" if lon >= 0 else "W",
            4: _to_dms(abs(lon)),
        }
        exif[34853] = gps_info
        img.save(img_path, exif=exif)


def _to_dms(value: float):
    degrees = int(value)
    minutes_full = (value - degrees) * 60
    minutes = int(minutes_full)
    seconds = round((minutes_full - minutes) * 60 * 100)
    return (
        Fraction(degrees, 1),
        Fraction(minutes, 1),
        Fraction(seconds, 100),
    )
