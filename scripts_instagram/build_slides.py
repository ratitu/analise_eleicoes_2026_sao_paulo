#!/usr/bin/env python3
"""Compose the 4-slide Instagram carousel (1080x1350) from the raw captures.

Slide 1 : cover + QR that opens the published site.
Slide 2 : Governador choropleth, full-bleed, with a composed headline band.
Slide 3 : Presidente choropleth, full-bleed, with a composed headline band.
Slide 4 : the 26 split-ticket districts, full-bleed, with a composed headline band.

Every number written into the artwork comes from the verified pipeline outputs
(see output/distritos_vencedor_2026.csv and the presidente equivalent); nothing
is estimated or rounded differently here.

Usage:  python3 scripts_instagram/build_slides.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "output" / "instagram" / "raw"
OUT_DIR = REPO / "output" / "instagram"
QR_PNG = OUT_DIR / "qr_url.png"

W, H = 1080, 1350
PAD = 72

# ---------------------------------------------------------------- palette ---
INK = (18, 22, 28)
INK_SOFT = (74, 82, 92)
MUTED = (100, 108, 120)   # 4.69:1 on PAPER (WCAG AA)
PAPER = (242, 241, 237)
WHITE = (255, 255, 255)
HAIRLINE = (214, 212, 206)
BLUE = (31, 95, 191)      # Tarcísio / Bolsonaro
RED = (217, 43, 43)       # Haddad / Lula

FONT_DIR = Path("/usr/share/fonts/truetype/lato")
F_BLACK = FONT_DIR / "Lato-Black.ttf"
F_BOLD = FONT_DIR / "Lato-Bold.ttf"
F_SEMI = FONT_DIR / "Lato-Semibold.ttf"
F_REG = FONT_DIR / "Lato-Regular.ttf"

# ------------------------------------------------------------ primitives ---
_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    key = (str(path), size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(str(path), size)
    return _font_cache[key]


def text_w(draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont) -> float:
    return draw.textlength(s, font=f)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    s: str,
    f: ImageFont.FreeTypeFont,
    fill,
    tracking: float = 0.0,
) -> float:
    """Draw text with extra letter-spacing; returns the end x."""
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=f, fill=fill)
        x += text_w(draw, ch, f) + tracking
    return x - tracking


def wrap(
    draw: ImageDraw.ImageDraw, s: str, f: ImageFont.FreeTypeFont, max_w: float
) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and text_w(draw, trial, f) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def fit_size(
    draw: ImageDraw.ImageDraw,
    s: str,
    path: Path,
    start: int,
    max_w: float,
    floor: int = 20,
) -> int:
    size = start
    while size > floor and text_w(draw, s, font(path, size)) > max_w:
        size -= 1
    return size


def paragraph(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    s: str,
    f: ImageFont.FreeTypeFont,
    fill,
    max_w: float,
    line_h: int,
) -> int:
    """Draw a wrapped paragraph; returns the y after the last line."""
    x, y = xy
    for line in wrap(draw, s, f, max_w):
        draw.text((x, y), line, font=f, fill=fill)
        y += line_h
    return y


# ------------------------------------------------------------------ cover ---
def slide_cover(index: int) -> Image.Image:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # top rule
    d.rectangle([PAD, 100, W - PAD, 103], fill=INK)

    eyebrow = "ELEIÇÕES 2026 · 1º TURNO · 04/10/2026"
    draw_tracked(d, (PAD, 132), eyebrow, font(F_BOLD, 24), MUTED, tracking=2.4)

    headline = "São Paulo dividiu o voto entre governador e presidente"
    size = fit_size(d, "São Paulo dividiu o voto", F_BLACK, 76, W - 2 * PAD)
    fh = font(F_BLACK, size)
    y = 186
    for line in wrap(d, headline, fh, W - 2 * PAD):
        d.text((PAD, y), line, font=fh, fill=INK)
        y += int(size * 1.12)

    y += 10
    sub = (
        "Veja no mapa como os 96 distritos da capital votaram nas duas "
        "eleições — e onde a disputa se inverteu."
    )
    y = paragraph(d, (PAD, y), sub, font(F_REG, 30), INK_SOFT, W - 2 * PAD, 42)

    # separator above the numbers
    d.rectangle([PAD, 604, W - PAD, 605], fill=HAIRLINE)

    col_w = (W - 2 * PAD - 56) // 2
    left_x = PAD
    right_x = PAD + col_w + 56
    top = 648

    # vertical divider between the two races
    d.rectangle([left_x + col_w + 28, top, left_x + col_w + 29, top + 218], fill=HAIRLINE)

    def race_block(x: int, title: str, rows, note: str) -> None:
        yy = top
        draw_tracked(d, (x, yy), title, font(F_BOLD, 23), MUTED, tracking=2.2)
        yy += 44
        for name, pct, color in rows:
            chip_y = yy + 12
            d.rectangle([x, chip_y, x + 15, chip_y + 15], fill=color)
            f_name = font(F_SEMI, 33)
            f_pct = font(F_BLACK, 33)
            d.text((x + 27, yy), name, font=f_name, fill=INK)
            pw = text_w(d, pct, f_pct)
            d.text((x + col_w - pw, yy), pct, font=f_pct, fill=INK)
            yy += 52
        yy += 6
        for i, line in enumerate(wrap(d, note, font(F_REG, 24), col_w)):
            if i == 0:
                d.text((x + 27, yy), line, font=font(F_REG, 24), fill=MUTED)
            else:
                d.text((x, yy), line, font=font(F_REG, 24), fill=MUTED)
            yy += 33

    race_block(
        left_x,
        "GOVERNADOR",
        [("Tarcísio", "52,70%", BLUE), ("Haddad", "46,04%", RED)],
        "Venceu em 70 dos 96 distritos; Haddad, em 26.",
    )
    race_block(
        right_x,
        "PRESIDENTE",
        [("Lula", "46,58%", RED), ("Bolsonaro", "42,13%", BLUE)],
        "Lula em 52 distritos, Bolsonaro em 43 e 1 empate.",
    )

    # QR card
    card_top, card_bottom = 966, 1298
    d.rounded_rectangle(
        [PAD, card_top, W - PAD, card_bottom], radius=26, fill=WHITE,
        outline=HAIRLINE, width=2,
    )
    qr = Image.open(QR_PNG).convert("RGB")
    qr_side = 268
    qr = qr.resize((qr_side, qr_side), Image.LANCZOS)
    qx, qy = PAD + 34, card_top + 32
    img.paste(qr, (qx, qy))
    d.rectangle([qx - 1, qy - 1, qx + qr_side, qy + qr_side], outline=HAIRLINE, width=1)

    tx = qx + qr_side + 40
    t_w = W - PAD - 34 - tx
    d.text((tx, card_top + 54), "Aponte a câmera", font=font(F_BLACK, 46), fill=INK)
    paragraph(
        d, (tx, card_top + 118),
        "Mapa interativo, distrito por distrito",
        font(F_REG, 27), INK_SOFT, t_w, 36,
    )
    d.text((tx, card_top + 198), "ratitu.github.io/", font=font(F_BOLD, 22), fill=BLUE)
    d.text((tx, card_top + 226), "analise_eleicoes_2026_sao_paulo", font=font(F_BOLD, 22), fill=BLUE)

    foot = "Fonte: TSE — 1º turno 2026 · 2.057 locais de votação geocodificados (OSM)"
    f_foot = font(F_REG, 21)
    d.text(((W - text_w(d, foot, f_foot)) / 2, 1316), foot, font=f_foot, fill=MUTED)

    return img


# ------------------------------------------------------------- map slides ---
BAND_TOP = 1118
BAND_ACCENT = 6


def slide_map(
    index: int,
    src: Path,
    eyebrow: str,
    headline: str,
    result_chips: list[tuple[str, tuple[int, int, int]]],
    note: str,
    accent: tuple[int, int, int],
) -> Image.Image:
    base = Image.open(src).convert("RGB")
    # The captures are exact 2x renders; keep full-bleed geometry.
    if base.size != (W * 2, H * 2):
        base = base.resize((W * 2, H * 2), Image.LANCZOS)
    base = base.resize((W, H), Image.LANCZOS)

    d = ImageDraw.Draw(base)
    d.rectangle([0, BAND_TOP, W, H], fill=PAPER)
    d.rectangle([0, BAND_TOP, W, BAND_TOP + BAND_ACCENT], fill=accent)

    y = BAND_TOP + 34
    draw_tracked(d, (PAD, y), eyebrow, font(F_BOLD, 23), MUTED, tracking=2.2)
    y += 44

    size = fit_size(d, headline, F_BLACK, 50, W - 2 * PAD, floor=30)
    lines = wrap(d, headline, font(F_BLACK, size), W - 2 * PAD)
    # Cap at two lines so the band never overflows.
    if len(lines) > 2:
        lines = lines[:2]
    for line in lines:
        d.text((PAD, y), line, font=font(F_BLACK, size), fill=INK)
        y += int(size * 1.14)

    y += 14
    chip_x, chip_y = PAD, y
    f_chip = font(F_BOLD, 24)
    for label, color in result_chips:
        tw = text_w(d, label, f_chip)
        if chip_x + tw + 30 > W - PAD:
            break
        d.rectangle([chip_x, chip_y, chip_x + tw + 30, chip_y + 40], fill=color)
        d.text((chip_x + 15, chip_y + 7), label, font=f_chip, fill=WHITE)
        chip_x += tw + 42
    y = chip_y + 40

    if note:
        y = paragraph(d, (PAD, y + 12), note, font(F_REG, 22), MUTED, W - 2 * PAD, 30)

    return base


# --------------------------------------------------------------------- io ---
def main() -> int:
    if not QR_PNG.exists():
        print(f"missing QR: {QR_PNG} — run make_qr.py first", file=sys.stderr)
        return 1

    jobs = [
        (
            "slide1_cover.png",
            None,
            None,
        ),
        (
            "slide2_governador.png",
            RAW / "s2_governador.png",
            {
                "eyebrow": "GOVERNADOR DE SP · 1º TURNO 2026",
                "headline": "Tarcísio venceu em 70 dos 96 distritos",
                "chips": [("Tarcísio 52,70%", BLUE), ("Haddad 46,04%", RED)],
                "note": "Cor = margem assinada (Tarcísio menos Haddad), em pontos percentuais.",
                "accent": BLUE,
            },
        ),
        (
            "slide3_presidente.png",
            RAW / "s3_presidente.png",
            {
                "eyebrow": "PRESIDENTE · 1º TURNO 2026",
                "headline": "Lula venceu em 52 distritos, Bolsonaro em 43",
                # grey chip darkened for 4.83:1 white-on-grey (WCAG AA)
                "chips": [("Lula 46,58%", RED), ("Bolsonaro 42,13%", BLUE), ("1 empate", (110, 114, 121))],
                "note": "Empate declarado quando a margem fica abaixo de 0,05 ponto percentual.",
                "accent": RED,
            },
        ),
        (
            "slide4_divergentes.png",
            RAW / "s4_divergentes.png",
            {
                "eyebrow": "VOTO CRUZADO · 26 DISTRITOS",
                "headline": "Onde SP votou Lula e Tarcísio na mesma urna",
                "chips": [("Lula (Presidente)", RED), ("Tarcísio (Governador)", BLUE)],
                "note": "Distritos que escolheram Lula para presidente e Tarcísio para governador.",
                "accent": INK,
            },
        ),
    ]

    for name, src, cfg in jobs:
        if src is None:
            img = slide_cover(1)
        else:
            if not src.exists():
                print(f"missing capture: {src}", file=sys.stderr)
                return 1
            img = slide_map(
                1, src, cfg["eyebrow"], cfg["headline"], cfg["chips"], cfg["note"], cfg["accent"]
            )
        assert img.size == (W, H), img.size
        out = OUT_DIR / name
        img.save(out, format="PNG", optimize=True)
        print(f"wrote {out}  {img.size[0]}x{img.size[1]}  {out.stat().st_size / 1024:.0f} KB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
