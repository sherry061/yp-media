"""Puzzle generators with self-checks: word search, number search, sudoku."""
import random

DIRS_EASY = [(0, 1), (1, 0), (1, 1)]                       # right, down, diagonal down-right
DIRS_MED = DIRS_EASY + [(-1, 1)]                           # + diagonal up-right
DIRS_ALL = DIRS_MED + [(0, -1), (-1, 0), (-1, -1), (1, -1)]  # + backwards


def _place(grid, n, word, dirs, rng, tries=400):
    for _ in range(tries):
        dr, dc = rng.choice(dirs)
        L = len(word)
        rmin = 0 if dr >= 0 else L - 1
        rmax = n - 1 if dr <= 0 else n - L
        cmin = 0 if dc >= 0 else L - 1
        cmax = n - 1 if dc <= 0 else n - L
        if rmin > rmax or cmin > cmax:
            continue
        r, c = rng.randint(rmin, rmax), rng.randint(cmin, cmax)
        cells = [(r + dr * i, c + dc * i) for i in range(L)]
        if all(grid[y][x] in (None, word[i]) for i, (y, x) in enumerate(cells)):
            # avoid fully overlapping an already placed word in the same line
            for i, (y, x) in enumerate(cells):
                grid[y][x] = word[i]
            return cells
    return None


def count_occurrences(grid, word, dirs=DIRS_ALL):
    n = len(grid)
    hits = 0
    for r in range(n):
        for c in range(n):
            for dr, dc in dirs:
                ok = True
                for i, ch in enumerate(word):
                    y, x = r + dr * i, c + dc * i
                    if not (0 <= y < n and 0 <= x < n) or grid[y][x] != ch:
                        ok = False
                        break
                if ok:
                    hits += 1
    # a palindrome is found twice (both directions) from the same cells
    if word == word[::-1]:
        hits //= 2
    return hits


def search_puzzle(entries, n, dirs, alphabet, seed, max_attempts=200):
    """entries: list of (display, key) where key is the string placed in the grid.
    Returns dict(grid, placements{display: cells}) with every key found exactly once."""
    rng = random.Random(seed)
    order = sorted(entries, key=lambda e: -len(e[1]))
    for attempt in range(max_attempts):
        grid = [[None] * n for _ in range(n)]
        placements = {}
        ok = True
        for disp, key in order:
            cells = _place(grid, n, key, dirs, rng)
            if cells is None:
                ok = False
                break
            placements[disp] = cells
        if not ok:
            continue
        for r in range(n):
            for c in range(n):
                if grid[r][c] is None:
                    grid[r][c] = rng.choice(alphabet)
        # every key must appear exactly once in any of 8 directions
        if all(count_occurrences(grid, key) == 1 for _, key in entries):
            return {"grid": grid, "placements": placements, "n": n}
        rng.seed(seed * 1000 + attempt + 1)
    raise RuntimeError(f"could not build puzzle (seed {seed})")


def verify_search(p, entries):
    g = p["grid"]
    for disp, key in entries:
        cells = p["placements"][disp]
        assert "".join(g[y][x] for y, x in cells) == key, (disp, key)
        assert count_occurrences(g, key) == 1, (disp, key)
    return True


# ------------------------------------------------------------------ sudoku
def _candidates(b, i):
    r, c = divmod(i, 9)
    used = set(b[r * 9:(r + 1) * 9]) | set(b[c::9])
    br, bc = 3 * (r // 3), 3 * (c // 3)
    for y in range(br, br + 3):
        used |= set(b[y * 9 + bc:y * 9 + bc + 3])
    return [d for d in range(1, 10) if d not in used]


def count_solutions(b, limit=2):
    b = list(b)
    best, cands = None, None
    for i in range(81):
        if b[i] == 0:
            cs = _candidates(b, i)
            if not cs:
                return 0
            if best is None or len(cs) < len(cands):
                best, cands = i, cs
                if len(cs) == 1:
                    break
    if best is None:
        return 1
    total = 0
    for d in cands:
        b[best] = d
        total += count_solutions(b, limit - total)
        if total >= limit:
            break
    b[best] = 0
    return total


def solve(b):
    b = list(b)

    def rec():
        best, cands = None, None
        for i in range(81):
            if b[i] == 0:
                cs = _candidates(b, i)
                if not cs:
                    return False
                if best is None or len(cs) < len(cands):
                    best, cands = i, cs
        if best is None:
            return True
        for d in cands:
            b[best] = d
            if rec():
                return True
        b[best] = 0
        return False

    return b if rec() else None


UNITS = [[r * 9 + c for c in range(9)] for r in range(9)] + \
        [[r * 9 + c for r in range(9)] for c in range(9)] + \
        [[(br + y) * 9 + bc + x for y in range(3) for x in range(3)] for br in (0, 3, 6) for bc in (0, 3, 6)]


def logic_grade(b):
    """Solve with singles only. Returns 'easy' (naked singles only), 'medium' (needs hidden singles), or None if stuck."""
    b = list(b)
    used_hidden = False
    while 0 in b:
        progress = False
        for i in range(81):
            if b[i] == 0:
                cs = _candidates(b, i)
                if len(cs) == 1:
                    b[i] = cs[0]
                    progress = True
        if progress:
            continue
        for unit in UNITS:
            for d in range(1, 10):
                if d in (b[i] for i in unit):
                    continue
                spots = [i for i in unit if b[i] == 0 and d in _candidates(b, i)]
                if len(spots) == 1:
                    b[spots[0]] = d
                    progress = True
                    used_hidden = True
        if not progress:
            return None
    return "medium" if used_hidden else "easy"


def full_grid(rng):
    b = [0] * 81

    def rec(i=0):
        if i == 81:
            return True
        cs = _candidates(b, i)
        rng.shuffle(cs)
        for d in cs:
            b[i] = d
            if rec(i + 1):
                return True
        b[i] = 0
        return False

    rec()
    return b


def make_sudoku(seed, level):
    """level: easy (36-40 givens, naked singles), medium (30-34, hidden singles), hard (26-30, needs more than singles)."""
    rng = random.Random(seed)
    target = {"easy": (36, 40), "medium": (30, 34), "hard": (24, 28)}[level]
    for attempt in range(400):
        sol = full_grid(rng)
        puz = list(sol)
        cells = list(range(81))
        rng.shuffle(cells)
        givens = 81
        lo, hi = target
        goal = rng.randint(lo, hi)
        for i in cells:
            if givens <= goal:
                break
            j = 80 - i  # keep it symmetric
            if puz[i] == 0:
                continue
            saved = (puz[i], puz[j])
            puz[i] = puz[j] = 0
            removed = 1 if i == j else 2
            if count_solutions(puz) != 1:
                puz[i], puz[j] = saved
                continue
            givens -= removed
        if not (lo <= givens <= hi + 1):
            continue
        givens = sum(1 for x in puz if x)
        g = logic_grade(puz)
        hard_ok = g is None or (attempt > 150 and g == "medium" and givens <= 26)
        if (level == "easy" and g == "easy") or (level == "medium" and g == "medium") or (level == "hard" and hard_ok):
            assert solve(puz) == sol and count_solutions(puz) == 1
            return puz, sol
    raise RuntimeError(f"sudoku {level} seed {seed}")
