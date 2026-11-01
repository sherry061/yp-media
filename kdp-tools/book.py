"""Builds KDP paperback interiors (8.5x11) as HTML, then prints to PDF with Chromium."""
import html, math, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = f"file://{HERE}/fonts"
IMPRINT = "Snug Corner Puzzles"
YEAR = 2026

CSS = f"""
@font-face {{ font-family: 'Atk'; src: url('{FONTS}/AtkinsonHyperlegible-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'Atk'; src: url('{FONTS}/AtkinsonHyperlegible-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: 'Lilita'; src: url('{FONTS}/LilitaOne-Regular.ttf'); }}
@page {{ size: 8.5in 11in; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; font-family: 'Atk'; color: #111; }}
.page {{ width: 8.5in; height: 11in; padding: 0.6in 0.75in 0.55in; position: relative; page-break-after: always; overflow: hidden; display: flex; flex-direction: column; }}
.page:last-child {{ page-break-after: auto; }}
.folio {{ position: absolute; bottom: 0.32in; left: 0; right: 0; text-align: center; font-size: 12pt; color: #444; }}
.kicker {{ font-size: 13pt; letter-spacing: 0.12em; text-transform: uppercase; color: #555; text-align: center; font-weight: 700; }}
h1.pt {{ font-family: 'Lilita'; font-weight: 400; font-size: 30pt; margin: 0.04in 0 0.14in; text-align: center; line-height: 1.05; }}
.rule {{ height: 3px; background: #111; width: 1.2in; margin: 0 auto 0.18in; border-radius: 2px; }}
.grid {{ display: block; margin: 0 auto; }}
.words {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.06in 0.2in; margin-top: 0.22in; font-size: 16pt; font-weight: 700; }}
.words div {{ display: flex; align-items: center; gap: 0.1in; }}
.words div::before {{ content: ''; width: 0.16in; height: 0.16in; border: 1.6px solid #555; border-radius: 3px; flex: none; }}
.sol-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0.22in 0.3in; margin-top: 0.1in; }}
.sol-grid .cap {{ text-align: center; font-weight: 700; font-size: 12pt; margin-bottom: 0.04in; }}
.center {{ text-align: center; }}
.front h1 {{ font-family: 'Lilita'; font-weight: 400; font-size: 44pt; line-height: 1.05; margin: 1.6in 0 0.25in; text-align: center; }}
.front h2 {{ font-size: 20pt; font-weight: 400; text-align: center; margin: 0 0 0.4in; }}
.front .imp {{ position: absolute; bottom: 1in; left: 0; right: 0; text-align: center; font-size: 16pt; font-weight: 700; letter-spacing: 0.08em; }}
.prose {{ font-size: 16pt; line-height: 1.5; }}
.prose h2 {{ font-family: 'Lilita'; font-weight: 400; font-size: 28pt; margin: 0.3in 0 0.2in; }}
.small {{ font-size: 12pt; line-height: 1.5; color: #222; }}
"""


def esc(s):
    return html.escape(s, quote=True)


def page(inner, folio=None, cls=""):
    f = f'<div class="folio">{folio}</div>' if folio else ""
    return f'<section class="page {cls}">{inner}{f}</section>'


# ------------------------------------------------------------------ SVG grids
def letter_grid_svg(grid, size_in, font_pt, placements=None, stroke=1.0):
    n = len(grid)
    W = size_in * 72.0
    pad = W / (n + 0.8) * 0.4
    cell = (W - 2 * pad) / n
    parts = [f'<svg class="grid" width="{size_in}in" height="{size_in}in" viewBox="{-pad:.2f} {-pad:.2f} {W:.2f} {W:.2f}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<rect x="{-pad + 1:.2f}" y="{-pad + 1:.2f}" width="{W - 2:.2f}" height="{W - 2:.2f}" rx="{cell * 0.45:.2f}" fill="none" stroke="#111" stroke-width="{stroke * 1.6:.2f}"/>')
    if placements:
        for cells in placements.values():
            (y0, x0), (y1, x1) = cells[0], cells[-1]
            parts.append(f'<line x1="{(x0 + .5) * cell:.2f}" y1="{(y0 + .5) * cell:.2f}" x2="{(x1 + .5) * cell:.2f}" y2="{(y1 + .5) * cell:.2f}" '
                         f'stroke="#bdbdbd" stroke-width="{cell * 0.72:.2f}" stroke-linecap="round" stroke-opacity="0.85"/>')
    for r in range(n):
        for c in range(n):
            parts.append(f'<text x="{(c + .5) * cell:.2f}" y="{(r + .5) * cell:.2f}" font-family="Atk" font-weight="700" font-size="{font_pt}pt" '
                         f'text-anchor="middle" dominant-baseline="central">{esc(grid[r][c])}</text>')
    parts.append('</svg>')
    return "".join(parts)


def sudoku_svg(puz, size_in, font_pt, sol=None):
    W = size_in * 72.0
    cell = W / 9
    p = [f'<svg class="grid" width="{size_in}in" height="{size_in}in" viewBox="-2 -2 {W + 4:.2f} {W + 4:.2f}" xmlns="http://www.w3.org/2000/svg">']
    for i in range(10):
        w = 3.2 if i % 3 == 0 else 0.9
        if sol is not None:
            w = 1.8 if i % 3 == 0 else 0.5
        p.append(f'<line x1="{i * cell:.2f}" y1="0" x2="{i * cell:.2f}" y2="{W:.2f}" stroke="#111" stroke-width="{w}" stroke-linecap="square"/>')
        p.append(f'<line x1="0" y1="{i * cell:.2f}" x2="{W:.2f}" y2="{i * cell:.2f}" stroke="#111" stroke-width="{w}" stroke-linecap="square"/>')
    for i in range(81):
        r, c = divmod(i, 9)
        v = puz[i]
        if v:
            p.append(f'<text x="{(c + .5) * cell:.2f}" y="{(r + .5) * cell:.2f}" font-family="Atk" font-weight="700" font-size="{font_pt}pt" text-anchor="middle" dominant-baseline="central">{v}</text>')
        elif sol is not None:
            p.append(f'<text x="{(c + .5) * cell:.2f}" y="{(r + .5) * cell:.2f}" font-family="Atk" font-weight="400" font-size="{font_pt}pt" fill="#666" text-anchor="middle" dominant-baseline="central">{sol[i]}</text>')
    p.append('</svg>')
    return "".join(p)


# ------------------------------------------------------------------ common pages
def title_page(title, subtitle):
    return page(f'<h1>{esc(title)}</h1><h2>{esc(subtitle)}</h2><div class="imp">{IMPRINT.upper()}</div>', cls="front")


def copyright_page(title):
    return page(f'''<div style="margin-top:auto" class="small">
<p><b>{esc(title)}</b></p>
<p>Copyright &copy; {YEAR} {IMPRINT}. All rights reserved.</p>
<p>No part of this book may be reproduced or distributed in any form without written permission from the publisher, except for brief quotations in reviews. Puzzle pages may be copied for the buyer's personal use.</p>
<p>Every puzzle in this book was checked by computer to have exactly one solution, and every answer in the solutions section was checked against its puzzle.</p>
<p>First edition, {YEAR}.</p></div>''')


def belongs_page():
    return page('<div style="margin:auto 0;text-align:center"><div style="font-family:Lilita;font-size:34pt">This book belongs to</div>'
                '<div style="border-bottom:2px solid #111;width:5in;margin:0.6in auto 0;height:0.5in"></div></div>')


def thanks_page():
    return page('''<div class="prose" style="margin:auto 0;text-align:center"><h2>Thank you!</h2>
<p>We hope these puzzles brought you some quiet, happy hours.</p>
<p>If you enjoyed this book, a short review on Amazon helps other puzzle fans find it, and it means a lot to a small publisher like us.</p></div>''')


def blank_page():
    return page("")


def render_pdf(pages, out_pdf):
    doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{''.join(pages)}</body></html>"
    html_path = out_pdf.replace(".pdf", ".html")
    open(html_path, "w").write(doc)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page()
        pg.goto(f"file://{html_path}")
        pg.wait_for_timeout(500)
        pg.evaluate("document.fonts.ready")
        pg.pdf(path=out_pdf, width="8.5in", height="11in", print_background=True, prefer_css_page_size=True)
        b.close()
    return out_pdf
