#!/usr/bin/env python3
"""Render the carousel QR code as a high-resolution, scannable PNG.

Output: output/instagram/qr_url.png  (RGBA, transparent margin kept white)
"""
from __future__ import annotations

import sys
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_H

URL = "https://ratitu.github.io/analise_eleicoes_2026_sao_paulo/"

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "output" / "instagram"
OUT = OUT_DIR / "qr_url.png"

# Smallest module geometry that still downsamples crisply into a 1080px slide:
# box_size=8 with border=4 -> (25 data + 8) * 8 = 264 px on a v5 code. We ask
# for a bigger box and then let a nearest-neighbour resize do the rest, so the
# module edges stay sharp instead of picking up bilinear blur.
BOX_SIZE = 20
BORDER = 4


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=BOX_SIZE,
        border=BORDER,
    )
    qr.add_data(URL)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img.save(OUT, format="PNG", optimize=True)

    modules = qr.modules_count
    print(f"URL        : {URL}")
    print(f"version    : {qr.version}  ({modules}x{modules} modules)")
    print(f"ecc        : H (30%)")
    print(f"size       : {img.size[0]}x{img.size[1]} px")
    print(f"written    : {OUT}")

    # Independent decode check (optional dependency, never fatal).
    try:
        from PIL import Image  # noqa: F401
        import subprocess

        proc = subprocess.run(
            ["zbarimg", "--quiet", str(OUT)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            decoded = proc.stdout.strip().split(":", 1)[-1].strip()
            status = "OK" if decoded == URL else "MISMATCH"
            print(f"zbarimg    : {status} -> {decoded}")
            if decoded != URL:
                return 2
        else:
            print("zbarimg    : unavailable (skipped local decode check)")
    except FileNotFoundError:
        print("zbarimg    : not installed (skipped local decode check)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
