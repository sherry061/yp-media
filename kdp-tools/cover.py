"""Full-wrap KDP paperback covers (8.5x11 trim, white paper, 0.125in bleed). Usage: python3 cover.py"""
import json, math, os, random
from playwright.sync_api import sync_playwright
import book as B
import puzzles as P

OUT = os.path.join(B.HERE, "out")
TRIM_W, TRIM_H, BLEED = 8.5, 11.0, 0.125
PAGE_IN = 0.002252  # white paper, black ink


def dims(pages):
    spine = pages * PAGE_IN
    return spine, 2 * TRIM_W + spine + 2 * BLEED, TRIM_H + 2 * BLEED


def snowflake(x, y, r, op=0.18, col="#fff"):
    arms = []
    for k in range(6):
        a = math.pi / 3 * k
        ex, ey = x + r * math.cos(a), y + r * math.sin(a)
        arms.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ex:.1f}" y2="{ey:.1f}"/>')
        for t in (0.55,):
            bx, by = x + r * t * math.cos(a), y + r * t * math.sin(a)
            for s in (-1, 1):
                b = a + s * 0.7
                arms.append(f'<line x1="{bx:.1f}" y1="{by:.1f}" x2="{bx + r * 0.32 * math.cos(b):.1f}" y2="{by + r * 0.32 * math.sin(b):.1f}"/>')
    return f'<g stroke="{col}" stroke-opacity="{op}" stroke-width="{r * 0.09:.1f}" stroke-linecap="round">{"".join(arms)}</g>'


def grid_card(chars, n, cell, highlights, font, fill="#fff", ink="#1a1a1a", hl="#f2c14e", hl_op=0.9, radius=18):
    """SVG group: a puzzle card with letters and highlight capsules. highlights: list of ((r0,c0),(r1,c1))."""
    W = n * cell + cell
    g = [f'<rect x="0" y="0" width="{W}" height="{W}" rx="{radius}" fill="{fill}"/>']
    off = cell / 2
    for (r0, c0), (r1, c1), col in highlights:
        g.append(f'<line x1="{off + (c0 + .5) * cell}" y1="{off + (r0 + .5) * cell}" x2="{off + (c1 + .5) * cell}" y2="{off + (r1 + .5) * cell}" '
                 f'stroke="{col}" stroke-width="{cell * 0.78}" stroke-linecap="round" stroke-opacity="{hl_op}"/>')
    for r in range(n):
        for c in range(n):
            g.append(f'<text x="{off + (c + .5) * cell}" y="{off + (r + .5) * cell}" font-family="{font}" font-weight="700" font-size="{cell * 0.62}" '
                     f'fill="{ink}" text-anchor="middle" dominant-baseline="central">{chars[r][c]}</text>')
    return W, "".join(g)


def ornament(x, y, r, col, string_len):
    return (f'<line x1="{x}" y1="0" x2="{x}" y2="{y - r - 10}" stroke="#f7e3a3" stroke-width="3" stroke-opacity="0.8"/>'
            f'<rect x="{x - r * 0.28}" y="{y - r - 14}" width="{r * 0.56}" height="{r * 0.3}" rx="3" fill="#e0b84c"/>'
            f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>'
            f'<path d="M{x - r * 0.95},{y - r * 0.15} Q{x},{y + r * 0.25} {x + r * 0.95},{y - r * 0.15}" stroke="#fff" stroke-opacity="0.45" stroke-width="{r * 0.12}" fill="none"/>'
            f'<circle cx="{x - r * 0.38}" cy="{y - r * 0.4}" r="{r * 0.16}" fill="#fff" fill-opacity="0.55"/>')


CSS = f"""
@font-face {{ font-family: 'Atk'; src: url('{B.FONTS}/AtkinsonHyperlegible-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: 'Atk'; src: url('{B.FONTS}/AtkinsonHyperlegible-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: 'Lilita'; src: url('{B.FONTS}/LilitaOne-Regular.ttf'); }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Atk'; }}
.wrap {{ position: relative; overflow: hidden; }}
.panel {{ position: absolute; top: 0; height: 100%; }}
.abs {{ position: absolute; }}
"""


def render(html_body, w_in, h_in, out_pdf, png_front=None, front_box=None):
    doc = f"<!doctype html><html><head><meta charset='utf-8'><style>@page {{ size: {w_in}in {h_in}in; margin: 0; }} {CSS}</style></head><body>{html_body}</body></html>"
    hp = out_pdf.replace(".pdf", ".html")
    open(hp, "w").write(doc)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": int(w_in * 96), "height": int(h_in * 96)})
        pg.goto(f"file://{hp}")
        pg.wait_for_timeout(600)
        pg.pdf(path=out_pdf, width=f"{w_in}in", height=f"{h_in}in", print_background=True)
        if png_front:
            x, y, w, h = front_box
            pg.screenshot(path=png_front, clip={"x": x * 96, "y": y * 96, "width": w * 96, "height": h * 96})
        pg.screenshot(path=out_pdf.replace(".pdf", "-full.png"), full_page=False)
        b.close()
    # Chromium rounds odd page sizes; set the boxes to the exact KDP size (the trimmed sliver is outside the bleed)
    import pypdf
    r = pypdf.PdfReader(out_pdf)
    w = pypdf.PdfWriter()
    pgx = r.pages[0]
    box = pypdf.generic.RectangleObject([0, 0, round(w_in * 72, 3), round(h_in * 72, 3)])
    pgx.mediabox = box
    pgx.cropbox = box
    w.add_page(pgx)
    w.write(out_pdf)


def build_cover(key, pages, front_svg, bg, title_lines, sub, badges, back_html, accent, spine_title, title_color="#fff"):
    spine, W, H = dims(pages)
    back_x, spine_x, front_x = 0, BLEED + TRIM_W, BLEED + TRIM_W + spine
    pw, ph = TRIM_W + BLEED, H
    show_spine_text = pages >= 100
    t_html = "".join(f'<div style="font-family:Lilita;font-size:{sz}pt;line-height:0.98;color:{c}">{t}</div>' for t, sz, c in title_lines)
    badge_html = "".join(f'<span style="display:inline-block;border:2.5px solid {title_color};color:{title_color};border-radius:40px;padding:0.07in 0.2in;margin:0 0.06in;font-size:15pt;font-weight:700;letter-spacing:0.04em">{b}</span>' for b in badges)
    body = f'''<div class="wrap" style="width:{W}in;height:{H}in;background:{bg}">
  <div class="panel" style="left:{front_x}in;width:{pw}in">
    {front_svg}
    <div class="abs" style="left:0.55in;right:0.68in;top:0.75in;text-align:center">
      <div style="display:inline-block;background:{accent};color:#111;font-weight:700;font-size:20pt;letter-spacing:0.14em;padding:0.08in 0.3in;border-radius:8px">LARGE PRINT</div>
      <div style="margin-top:0.18in">{t_html}</div>
      <div style="margin-top:0.16in;font-size:21pt;font-weight:700;color:{title_color}">{sub}</div>
    </div>
    <div class="abs" style="left:0.4in;right:0.53in;bottom:1.05in;text-align:center">{badge_html}</div>
    <div class="abs" style="left:0;right:0.125in;bottom:0.5in;text-align:center;color:{title_color};font-size:13pt;font-weight:700;letter-spacing:0.22em;opacity:0.9">{B.IMPRINT.upper()}</div>
  </div>
  <div class="panel" style="left:{spine_x}in;width:{spine}in;background:rgba(0,0,0,0.18)">
    {f'<div class="abs" style="left:50%;top:50%;transform:translate(-50%,-50%) rotate(90deg);white-space:nowrap;color:#fff;font-weight:700;font-size:{min(15, spine * 72 * 0.5):.1f}pt;letter-spacing:0.06em">{spine_title}</div>' if show_spine_text else ''}
  </div>
  <div class="panel" style="left:0;width:{pw}in">
    <div class="abs" style="left:0.75in;right:0.6in;top:0.85in;color:{title_color}">{back_html}</div>
    <div class="abs" style="right:0.375in;bottom:0.375in;width:2.1in;height:1.3in;background:#fff;border-radius:4px"></div>
  </div>
</div>'''
    meta = B_META[key]
    out = os.path.join(OUT, meta + "-cover.pdf")
    render(body, round(W, 4), round(H, 4), out, png_front=os.path.join(OUT, meta + "-front.png"), front_box=(front_x, 0, pw, ph))
    return out, spine, W, H


B_META = {"ws": "christmas-word-search", "ns": "number-search", "su": "sudoku"}


def mini_page(kind, seed=1):
    """A small 'look inside' page mockup as inline SVG (2.5in x 3.2in)."""
    rng = random.Random(seed)
    w, h = 180, 230
    g = [f'<rect x="0" y="0" width="{w}" height="{h}" rx="6" fill="#fff"/>']
    if kind == "su":
        n, cell, x0, y0 = 9, 17, 13, 40
        for i in range(10):
            sw = 1.6 if i % 3 == 0 else 0.5
            g.append(f'<line x1="{x0 + i * cell}" y1="{y0}" x2="{x0 + i * cell}" y2="{y0 + 9 * cell}" stroke="#222" stroke-width="{sw}"/><line x1="{x0}" y1="{y0 + i * cell}" x2="{x0 + 9 * cell}" y2="{y0 + i * cell}" stroke="#222" stroke-width="{sw}"/>')
        for r in range(9):
            for c in range(9):
                if rng.random() < 0.42:
                    g.append(f'<text x="{x0 + c * cell + cell / 2}" y="{y0 + r * cell + cell / 2 + 0.5}" font-family="Atk" font-weight="700" font-size="11" text-anchor="middle" dominant-baseline="central" fill="#222">{rng.randint(1, 9)}</text>')
        title = "Puzzle 1 &#183; Easy"
    else:
        n = 12 if kind == "ws" else 11
        cell, x0, y0 = 12.5, 15, 42
        chars = "ABCDEFGHIJKLMNOPRSTUWY" if kind == "ws" else "0123456789"
        g.append(f'<rect x="{x0 - 4}" y="{y0 - 4}" width="{n * cell + 8}" height="{n * cell + 8}" rx="6" fill="none" stroke="#222" stroke-width="1"/>')
        for r in range(n):
            for c in range(n):
                g.append(f'<text x="{x0 + c * cell + cell / 2}" y="{y0 + r * cell + cell / 2}" font-family="Atk" font-weight="700" font-size="8.5" text-anchor="middle" dominant-baseline="central" fill="#222">{rng.choice(chars)}</text>')
        for k in range(9):
            g.append(f'<rect x="{18 + (k % 3) * 52}" y="{y0 + n * cell + 14 + (k // 3) * 11}" width="38" height="4.5" rx="2" fill="#bbb"/>')
        title = "Santa&#8217;s Workshop" if kind == "ws" else "Puzzle 1"
    g.append(f'<text x="{w / 2}" y="24" font-family="Lilita" font-size="15" text-anchor="middle" fill="#222">{title}</text>')
    return (f'<div style="margin-top:0.35in;display:flex;align-items:center;gap:0.3in"><svg width="2.5in" height="3.2in" viewBox="0 0 {w} {h}" style="transform:rotate(-3deg);filter:drop-shadow(4px 6px 0 rgba(0,0,0,0.25))">{"".join(g)}</svg>'
            f'<div style="font-family:Lilita;font-size:22pt;line-height:1.1">Look inside:<br>one big puzzle<br>on every page</div></div>')


def back_block(blurb, bullets, title_color, kind="ws"):
    lis = "".join(f'<li style="margin:0.06in 0">{b}</li>' for b in bullets)
    return (f'<div style="font-family:Lilita;font-size:30pt;line-height:1.05;margin-bottom:0.25in">{blurb[0]}</div>'
            f'<div style="font-size:16pt;line-height:1.5;margin-bottom:0.25in">{blurb[1]}</div>'
            f'<ul style="font-size:16pt;line-height:1.35;padding-left:0.3in;font-weight:700">{lis}</ul>' + mini_page(kind))


def cover_ws(pages):
    rng = random.Random(4)
    pw = (TRIM_W + BLEED) * 72
    ph = (TRIM_H + 2 * BLEED) * 72
    flakes = "".join(snowflake(rng.uniform(20, pw - 20), rng.uniform(20, ph - 20), rng.uniform(10, 26), rng.uniform(0.12, 0.28)) for _ in range(38))
    orns = ornament(70, 120, 30, "#2f8f4e", 0) + ornament(pw - 60, 150, 34, "#e0b84c", 0) + ornament(pw - 120, 70, 20, "#ffffff", 0)
    # word search card with real words
    entries = [(w, w) for w in ["SNOW", "STAR", "BELLS", "SLEIGH", "TREE", "GIFTS", "JOY", "NOEL", "ELF", "HOLLY"]]
    p = P.search_puzzle(entries, 9, P.DIRS_EASY, "AEIOURSTLNMHCDGBPKW", seed=12)
    hl_cols = ["#f2c14e", "#7fd1a1", "#f2c14e", "#9fc6f0", "#7fd1a1", "#f2a1a1", "#f2c14e", "#9fc6f0", "#7fd1a1", "#f2a1a1"]
    hls = [(cells[0], cells[-1], hl_cols[i % len(hl_cols)]) for i, cells in enumerate(p["placements"].values())]
    cw, card = grid_card(p["grid"], 9, 34, hls, "Atk")
    cx, cy = pw / 2 - cw / 2 + 4, ph * 0.40
    svg = (f'<svg class="abs" style="left:0;top:0" width="{pw}pt" height="{ph}pt" viewBox="0 0 {pw} {ph}">{flakes}{orns}'
           f'<g transform="translate({cx},{cy}) rotate(-4 {cw / 2} {cw / 2})"><rect x="8" y="12" width="{cw}" height="{cw}" rx="18" fill="#000" fill-opacity="0.25"/>{card}</g></svg>')
    back = back_block(("A merry puzzle for every winter day",
                       "Settle in with a warm drink and 60 cheerful word searches full of Christmas baking, carols, decorations, winter walks and cozy evenings by the fire."),
                      ["Big, bold 20 pt letters on one puzzle per page", "60 themed puzzles, 15 words each", "Gets gently harder as you go", "Full solutions at the back", "A thoughtful gift for parents and grandparents"], "#fff", "ws")
    return build_cover("ws", pages, svg, "#b3202a", [("Christmas", 72, "#fff"), ("Word Search", 64, "#fff")],
                       "for Adults and Seniors", ["60 Puzzles", "Solutions Included"], back, "#f2c14e", "LARGE PRINT CHRISTMAS WORD SEARCH")


def cover_ns(pages):
    pw = (TRIM_W + BLEED) * 72
    ph = (TRIM_H + 2 * BLEED) * 72
    rng = random.Random(9)
    entries = [(n, n) for n in ["2025", "8146", "37904", "551", "9620", "1738", "4402"]]
    p = P.search_puzzle(entries, 8, P.DIRS_EASY, "0123456789", seed=3)
    cols = ["#f2c14e", "#7fd1a1", "#9fc6f0", "#f2a1a1"]
    hls = [(c[0], c[-1], cols[i % 4]) for i, c in enumerate(p["placements"].values())]
    cw, card = grid_card(p["grid"], 8, 38, hls, "Atk")
    dots = "".join(f'<circle cx="{rng.uniform(0, pw):.0f}" cy="{rng.uniform(0, ph):.0f}" r="{rng.uniform(2, 6):.1f}" fill="#fff" fill-opacity="{rng.uniform(0.08, 0.2):.2f}"/>' for _ in range(90))
    bigdigits = "".join(f'<text x="{rng.uniform(0, pw):.0f}" y="{rng.uniform(0, ph):.0f}" font-family="Lilita" font-size="{rng.uniform(40, 110):.0f}" fill="#fff" fill-opacity="0.06">{rng.randint(0, 9)}</text>' for _ in range(28))
    cx, cy = pw / 2 - cw / 2 + 4, ph * 0.41
    svg = (f'<svg class="abs" style="left:0;top:0" width="{pw}pt" height="{ph}pt" viewBox="0 0 {pw} {ph}">{dots}{bigdigits}'
           f'<g transform="translate({cx},{cy}) rotate(3 {cw / 2} {cw / 2})"><rect x="8" y="12" width="{cw}" height="{cw}" rx="18" fill="#000" fill-opacity="0.25"/>{card}</g></svg>')
    back = back_block(("Relax, focus and find the numbers",
                       "Number search is the calm cousin of word search: no spelling, no vocabulary, just a gentle hunt for digits. Perfect for quiet mornings, waiting rooms and keeping the mind active."),
                      ["Big, bold 22 pt digits on one puzzle per page", "80 puzzles, 15 numbers each", "Lists sorted smallest to largest", "Easier first half, trickier second half", "Full solutions at the back"], "#fff", "ns")
    return build_cover("ns", pages, svg, "#1f5f7a", [("Number", 76, "#fff"), ("Search", 76, "#fff")],
                       "80 Relaxing Puzzles for Adults and Seniors", ["Easy to Read", "Solutions Included"], back, "#f2c14e", "LARGE PRINT NUMBER SEARCH")


def cover_su(pages):
    pw = (TRIM_W + BLEED) * 72
    ph = (TRIM_H + 2 * BLEED) * 72
    puz, sol = P.make_sudoku(77, "easy")
    W = 9 * 40
    g = [f'<rect x="-14" y="-14" width="{W + 28}" height="{W + 28}" rx="18" fill="#fff"/>']
    for i in range(10):
        w = 4 if i % 3 == 0 else 1.2
        g.append(f'<line x1="{i * 40}" y1="0" x2="{i * 40}" y2="{W}" stroke="#222" stroke-width="{w}"/><line x1="0" y1="{i * 40}" x2="{W}" y2="{i * 40}" stroke="#222" stroke-width="{w}"/>')
    for i, v in enumerate(puz):
        if v:
            r, c = divmod(i, 9)
            g.append(f'<text x="{c * 40 + 20}" y="{r * 40 + 21}" font-family="Atk" font-weight="700" font-size="26" fill="#222" text-anchor="middle" dominant-baseline="central">{v}</text>')
    # a pencil-written answer in one cell
    g.append(f'<circle cx="{4 * 40 + 20}" cy="{4 * 40 + 20}" r="17" fill="#f2c14e" fill-opacity="0.7"/>' if not puz[40] else "")
    rng = random.Random(2)
    tiles = "".join(f'<rect x="{x * 54}" y="{y * 54}" width="50" height="50" rx="8" fill="#fff" fill-opacity="{rng.choice([0.04, 0.06, 0.09])}"/>' for x in range(13) for y in range(16))
    cx, cy = pw / 2 - W / 2 + 4, ph * 0.355
    svg = (f'<svg class="abs" style="left:0;top:0" width="{pw}pt" height="{ph}pt" viewBox="0 0 {pw} {ph}">{tiles}'
           f'<g transform="translate({cx},{cy}) rotate(-3 {W / 2} {W / 2})"><rect x="-6" y="-2" width="{W + 28}" height="{W + 28}" rx="18" fill="#000" fill-opacity="0.22"/>{"".join(g)}</g></svg>')
    back = back_block(("One big puzzle per page, easy on the eyes",
                       "Classic sudoku printed large and clear, with plenty of room to pencil in your notes. Start with gentle warm-ups and work your way up to real brain-stretchers."),
                      ["120 puzzles: 40 easy, 40 medium, 40 hard", "Big 30 pt digits, one puzzle per page", "Every puzzle has exactly one solution", "Solvable by logic, no guessing", "Full solutions at the back"], "#fff", "su")
    return build_cover("su", pages, svg, "#2d4a8a", [("Sudoku", 96, "#fff")],
                       "120 Puzzles for Adults and Seniors", ["Easy to Hard", "Solutions Included"], back, "#f2c14e", "LARGE PRINT SUDOKU")


if __name__ == "__main__":
    for key, fn in (("ws", cover_ws), ("ns", cover_ns), ("su", cover_su)):
        pages = json.load(open(os.path.join(OUT, B_META[key] + ".json")))["pages"]
        print(key, pages, fn(pages))
