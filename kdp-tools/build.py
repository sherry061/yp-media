"""Build the three books. Usage: python3 build.py [ws|ns|su|all]"""
import json, os, random, string, sys
import puzzles as P
import book as B
from themes_christmas import THEMES

OUT = os.path.join(B.HERE, "out")
os.makedirs(OUT, exist_ok=True)

BOOKS = {
    "ws": {"title": "Large Print Christmas Word Search", "sub": "60 Festive Puzzles for Adults and Seniors", "file": "christmas-word-search"},
    "ns": {"title": "Large Print Number Search", "sub": "80 Relaxing Puzzles for Adults and Seniors", "file": "number-search"},
    "su": {"title": "Large Print Sudoku", "sub": "120 Easy, Medium and Hard Puzzles for Adults and Seniors", "file": "sudoku"},
}


def chunks(xs, k):
    return [xs[i:i + k] for i in range(0, len(xs), k)]


def search_book(key, items, how_to, grid_n, font_pt, alphabet, dir_for, word_cols_css=""):
    meta = BOOKS[key]
    pages = [B.title_page(meta["title"], meta["sub"]), B.copyright_page(meta["title"]), B.page(how_to), B.belongs_page()]
    sols = []
    for idx, (title, entries) in enumerate(items, 1):
        p = P.search_puzzle(entries, grid_n, dir_for(idx), alphabet, seed=idx * 7919 + len(key))
        P.verify_search(p, entries)
        sols.append((idx, title, p))
        words = "".join(f"<div>{B.esc(d)}</div>" for d, _ in sorted(entries, key=lambda e: int(e[1]) if key == "ns" else e[0]))
        kick = "Number Search" if key == "ns" else f"Puzzle {idx}"
        head = f"Puzzle {idx}" if key == "ns" else title
        inner = (f'<div class="kicker">{kick}</div><h1 class="pt">{B.esc(head)}</h1><div class="rule"></div>'
                 f'{B.letter_grid_svg(p["grid"], 6.6, font_pt)}<div class="words" style="{word_cols_css}">{words}</div>')
        pages.append(B.page(inner, folio=len(pages) + 1))
    for group in chunks(sols, 4):
        cells = "".join(f'<div><div class="cap">{("Puzzle " + str(i)) if key == "ns" else (str(i) + ". " + B.esc(t))}</div>{B.letter_grid_svg(p["grid"], 3.25, 8.5, p["placements"], 0.6)}</div>' for i, t, p in group)
        pages.append(B.page(f'<div class="kicker">Solutions</div><div class="sol-grid">{cells}</div>', folio=len(pages) + 1))
    pages.append(B.thanks_page())
    if len(pages) % 2:
        pages.append(B.blank_page())
    out = B.render_pdf(pages, os.path.join(OUT, meta["file"] + "-interior.pdf"))
    json.dump({"pages": len(pages)}, open(os.path.join(OUT, meta["file"] + ".json"), "w"))
    return out, len(pages)


HOW_WS = '''<div class="prose"><h2>How to play</h2>
<p>Each puzzle has a list of 15 words hidden in the grid of letters. Find each word and circle it, then tick it off the list.</p>
<p>Words run in a straight line. In puzzles 1 to 20 they read left to right, top to bottom, or diagonally down to the right. From puzzle 21 they can also run diagonally upward, and from puzzle 41 they can run in any direction, including backwards.</p>
<p>Words made of two parts, like NORTH POLE, appear in the grid without the space. Letters can be shared by two words where they cross.</p>
<p>Every word appears exactly once in its grid. The solutions start after puzzle 60.</p>
<p>Take your time and enjoy the season!</p></div>'''

HOW_NS = '''<div class="prose"><h2>How to play</h2>
<p>Each puzzle has a list of numbers hidden in a grid of digits. Find each number and circle it, then tick it off the list.</p>
<p>Numbers run in a straight line. In puzzles 1 to 40 they read left to right, top to bottom, or diagonally down to the right. From puzzle 41 they can run in any direction, including backwards and upward.</p>
<p>Digits can be shared by two numbers where they cross. Every number appears exactly once in its grid, and the list is in order from smallest to largest to help you keep track.</p>
<p>The solutions start after puzzle 80.</p></div>'''

HOW_SU = '''<div class="prose"><h2>How to play</h2>
<p>Fill in the grid so that every row, every column and every 3 &times; 3 box contains each of the digits 1 to 9 exactly once.</p>
<p>Some digits are already filled in to get you started. You never need to guess: every puzzle in this book has exactly one solution, and it can be reached by logic alone.</p>
<p><b>Puzzles 1&ndash;40 (Easy):</b> lots of starting digits. Look for a square where only one digit fits.<br>
<b>Puzzles 41&ndash;80 (Medium):</b> fewer starting digits. Also look for a digit that has only one possible place in a row, column or box.<br>
<b>Puzzles 81&ndash;120 (Hard):</b> the fewest starting digits. You will need to note the possible digits in each square and rule them out step by step.</p>
<p>Use a pencil so you can erase. The solutions start after puzzle 120.</p></div>'''


def build_ws():
    items = [(t, [(w, w.replace(" ", "")) for w in ws]) for t, ws in THEMES]
    # letter frequencies close to English so the grid doesn't give words away
    alphabet = "EEEEEEEAAAAAAIIIIIIOOOOOONNNNNNRRRRRRTTTTTTLLLLSSSSSSUUUDDDDGGGBBCCCMMMPPPFFHHHVVWWYYKJXQZ"
    dirs = lambda i: P.DIRS_EASY if i <= 20 else (P.DIRS_MED if i <= 40 else P.DIRS_ALL)
    return search_book("ws", items, HOW_WS, 15, 20, alphabet, dirs)


def build_ns():
    items = []
    for i in range(1, 81):
        rng = random.Random(5000 + i)
        nums = set()
        while len(nums) < 15:
            L = rng.choice([4, 5, 5, 6, 6, 6, 7, 7])
            s = str(rng.randint(10 ** (L - 1), 10 ** L - 1))
            # no number may hide inside another (forwards or backwards)
            if any(s in o or s[::-1] in o or o in s or o[::-1] in s for o in nums):
                continue
            nums.add(s)
        nums = sorted(nums, key=int)
        items.append((f"Number Search {i}", [(n, n) for n in nums]))
    dirs = lambda i: P.DIRS_EASY if i <= 40 else P.DIRS_ALL
    out = search_book("ns", [(t, e) for t, e in items], HOW_NS, 14, 22, "0123456789", dirs)
    return out


def build_su():
    meta = BOOKS["su"]
    pages = [B.title_page(meta["title"], meta["sub"]), B.copyright_page(meta["title"]), B.page(HOW_SU), B.belongs_page()]
    sols = []
    n = 0
    for level, count in (("easy", 40), ("medium", 40), ("hard", 40)):
        for k in range(count):
            n += 1
            puz, sol = P.make_sudoku(9000 + n, level)
            assert P.count_solutions(puz) == 1 and P.solve(puz) == sol
            sols.append((n, level, puz, sol))
            inner = (f'<div class="kicker">Puzzle {n} &middot; {level.title()}</div><div style="height:0.5in"></div>'
                     f'{B.sudoku_svg(puz, 6.75, 30)}')
            pages.append(B.page(inner, folio=len(pages) + 1))
    for group in chunks(sols, 6):
        cells = "".join(f'<div><div class="cap">{i}. {lv.title()}</div>{B.sudoku_svg(p, 2.75, 11, s)}</div>' for i, lv, p, s in group)
        pages.append(B.page(f'<div class="kicker">Solutions</div><div class="sol-grid" style="gap:0.12in 0.6in;justify-items:center">{cells}</div>', folio=len(pages) + 1))
    pages.append(B.thanks_page())
    if len(pages) % 2:
        pages.append(B.blank_page())
    out = B.render_pdf(pages, os.path.join(OUT, meta["file"] + "-interior.pdf"))
    json.dump({"pages": len(pages)}, open(os.path.join(OUT, meta["file"] + ".json"), "w"))
    return out, len(pages)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for k, f in (("ws", build_ws), ("ns", build_ns), ("su", build_su)):
        if which in (k, "all"):
            print(k, f())
