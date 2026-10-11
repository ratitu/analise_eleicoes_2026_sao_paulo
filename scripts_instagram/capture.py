#!/usr/bin/env python3
"""Captura as tres telas de mapa do app (4:5, 1080x1350 @2x) via Playwright.

Le somente as paginas HTML publicadas; nao altera dados nem scripts.
Requer o servidor local rodando:  python3 -m http.server 8931 --bind 127.0.0.1
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8931"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "instagram" / "raw"
EXE = "/usr/bin/chromium"
W, H, DSF = 1080, 1350, 2

PAGES = [
    ("index_gov.html", "s2_governador"),
    ("index_pres.html", "s3_presidente"),
    ("index_disputa.html", "s4_divergentes"),
]


def expand_legend(page):
    """Abre o painel 'Legenda' (colapsado por padrao) para aparecer na captura."""
    for sel in ["div.colapsavel", "#btn-legenda", ".legenda-toggle"]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.click()
                page.wait_for_timeout(600)
                return True
        except Exception:
            continue
    return False


def wait_tiles(page):
    for _ in range(60):
        pending = page.evaluate(
            "() => document.querySelectorAll('.leaflet-tile-loading,.leaflet-tile:not(.leaflet-tile-loaded)').length"
        )
        if pending == 0:
            break
        page.wait_for_timeout(500)
    page.wait_for_timeout(1200)  # deixa o canvas/vetor assentar


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=EXE, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        for page_name, out_name in PAGES:
            page = browser.new_page(
                viewport={"width": W, "height": H}, device_scale_factor=DSF
            )
            page.goto(f"{BASE}/{page_name}", wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(2500)
            wait_tiles(page)
            expanded = expand_legend(page)
            wait_tiles(page)
            dst = OUT / f"{out_name}.png"
            page.screenshot(path=str(dst), animations="disabled")
            size = dst.stat().st_size
            print(f"[ok] {page_name:20s} -> {dst.name:20s} legenda={'aberta' if expanded else 'fechada'} {size/1024:7.1f} KB")
            page.close()
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
