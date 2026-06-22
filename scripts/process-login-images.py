"""Убрать клетку/фон, обрезать и сжать PNG персонажей для страницы входа."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "frontend" / "images"
MAX_SIDE = 1200
PADDING = 8


def is_background_pixel(r: int, g: int, b: int, a: int) -> bool:
    if a < 20:
        return True
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    # Белый, серый, клетка прозрачности
    if max_c - min_c < 35 and max_c > 120:
        return True
    # Светло-серые оттенки клетки
    if abs(r - g) < 20 and abs(g - b) < 20 and min_c > 100:
        return True
    return False


def process_image(path: Path) -> None:
    img = Image.open(path).convert("RGBA")
    pixels = img.load()
    width, height = img.size

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if is_background_pixel(r, g, b, a):
                pixels[x, y] = (r, g, b, 0)

    bbox = img.getbbox()
    if not bbox:
        raise RuntimeError(f"Не осталось видимых пикселей: {path.name}")

    left, top, right, bottom = bbox
    left = max(0, left - PADDING)
    top = max(0, top - PADDING)
    right = min(width, right + PADDING)
    bottom = min(height, bottom + PADDING)
    img = img.crop((left, top, right, bottom))

    w, h = img.size
    scale = min(1.0, MAX_SIDE / max(w, h))
    if scale < 1.0:
        new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    img.save(path, format="PNG", optimize=True)
    print(f"{path.name}: {w}x{h} -> {img.size[0]}x{img.size[1]}, {path.stat().st_size // 1024} KB")


def main() -> int:
    names = ["login-character-small.png", "login-character-large.png"]
    for name in names:
        path = IMAGES_DIR / name
        if not path.exists():
            print(f"Файл не найден: {path}", file=sys.stderr)
            return 1
        process_image(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
