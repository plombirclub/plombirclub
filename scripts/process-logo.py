"""Убрать только внешний чёрный фон logo.png, сохранить цвета логотипа."""
from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LOGO = ROOT / "frontend" / "images" / "logo.png"
MAX_SIDE = 960
PADDING = 14
BLACK_MAX = 24


def is_black(r: int, g: int, b: int) -> bool:
    return max(r, g, b) <= BLACK_MAX


def is_light(r: int, g: int, b: int) -> bool:
    mx = max(r, g, b)
    mn = min(r, g, b)
    return mx >= 160 and mx - mn <= 65


def flood_outer_background(img: Image.Image) -> list[list[bool]]:
    w, h = img.size
    px = img.load()
    mask = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque()

    def push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= w or y >= h or mask[y][x]:
            return
        r, g, b, a = px[x, y]
        if a < 16 or is_black(r, g, b):
            mask[y][x] = True
            q.append((x, y))

    for x in range(w):
        push(x, 0)
        push(x, h - 1)
    for y in range(h):
        push(0, y)
        push(w - 1, y)

    while q:
        x, y = q.popleft()
        push(x - 1, y)
        push(x + 1, y)
        push(x, y - 1)
        push(x, y + 1)

    return mask


def solidify(img: Image.Image) -> None:
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 16:
                continue
            if is_light(r, g, b):
                px[x, y] = (255, 255, 255, 255)
            else:
                px[x, y] = (r, g, b, 255)


def main() -> None:
    img = Image.open(LOGO).convert("RGBA")
    px = img.load()
    w, h = img.size
    bg_mask = flood_outer_background(img)

    for y in range(h):
        for x in range(w):
            if bg_mask[y][x]:
                px[x, y] = (0, 0, 0, 0)

    solidify(img)

    bbox = img.getbbox()
    if not bbox:
        raise RuntimeError("logo.png: пустой результат")

    l, t, r, b = bbox
    img = img.crop((
        max(0, l - PADDING),
        max(0, t - PADDING),
        min(w, r + PADDING),
        min(h, b + PADDING),
    ))

    cw, ch = img.size
    scale = min(1.0, MAX_SIDE / max(cw, ch))
    if scale < 1.0:
        img = img.resize((int(cw * scale), int(ch * scale)), Image.Resampling.LANCZOS)
        solidify(img)

    img.save(LOGO, format="PNG", optimize=True)
    print(f"logo.png: {img.size[0]}x{img.size[1]}, {LOGO.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
