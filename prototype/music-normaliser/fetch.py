# /// script
# dependencies = ["httpx", "beautifulsoup4"]
# ///
"""PROTOTYPE, throwaway. Fetch program-music cells from EN Wikipedia for whole event fields.

Writes cache/*.json (raw parse HTML, wipe me) and cells.json (one row per program-table cell).
Run: uv run fetch.py
"""
import json, re, time
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

UA = "iceskatesong-prototype/0.1 (+https://github.com/gantover/iceskatesong.com)"
API = "https://en.wikipedia.org/w/api.php"
EVENTS = [  # whole fields, so shared music can show up as duplicates
    "2006 World Figure Skating Championships",
    "2015 World Junior Figure Skating Championships",
    "2024 World Figure Skating Championships",
]
SEGMENT_COLS = re.compile(r"short|free|rhythm|original|compulsory|exhibition", re.I)
HERE = Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
client = httpx.Client(headers={"User-Agent": UA}, timeout=30)


def parse(title):
    f = CACHE / (re.sub(r"[^\w]+", "_", title) + ".json")
    if not f.exists():
        r = client.get(API, params={"action": "parse", "page": title, "prop": "text",
                                    "format": "json", "formatversion": 2, "redirects": 1})
        f.write_text(r.text)
        time.sleep(0.3)  # serial + polite
    d = json.loads(f.read_text())
    return d.get("parse", {}).get("text", "")


def entrant_links(event):
    s = BeautifulSoup(parse(event), "html.parser")
    out = []
    for t in s.select("table.wikitable"):
        for a in t.select("td a[href^='/wiki/']"):
            href = a["href"][6:]
            if ":" in href or "Figure_Skating" in href or "_Championships" in href:
                continue
            out.append(href.replace("_", " ").split("#")[0])
    # drop country / federation links: they appear with a flag icon next to them
    flags = {a["href"][6:].replace("_", " ") for a in s.select("span.flagicon + a, .flagicon a")}
    return [x for x in dict.fromkeys(out) if x not in flags]


def expand_rowspans(table):
    """Return the table as a grid of <td>/<th> elements with rowspans resolved."""
    grid, pending = [], {}
    for tr in table.find_all("tr"):
        row, cells, col = [], tr.find_all(["td", "th"], recursive=False), 0
        it = iter(cells)
        while True:
            if col in pending and pending[col][1] > 0:
                row.append(pending[col][0]); pending[col][1] -= 1; col += 1; continue
            c = next(it, None)
            if c is None:
                break
            for _ in range(int(c.get("colspan", 1) or 1)):
                rs = int(re.sub(r"\D", "", c.get("rowspan", "1")) or 1)
                if rs > 1:
                    pending[col] = [c, rs - 1]
                row.append(c); col += 1
        grid.append(row)
    return grid


def program_cells(article):
    s = BeautifulSoup(parse(article), "html.parser")
    for t in s.select("table.wikitable"):
        grid = expand_rowspans(t)
        if not grid:
            continue
        hdr = [c.get_text(" ", strip=True) for c in grid[0]]
        if not hdr or not hdr[0].lower().startswith("season") or not any(SEGMENT_COLS.search(h) for h in hdr[1:]):
            continue
        for row in grid[1:]:
            if len(row) != len(hdr):
                continue
            season = row[0].get_text(" ", strip=True).split("[")[0].strip()
            for h, c in zip(hdr[1:], row[1:]):
                if SEGMENT_COLS.search(h) and c.get_text(strip=True):
                    yield {"article": article, "season": season, "segment": h, "html": str(c)}


if __name__ == "__main__":
    cells, seen = [], set()
    for ev in EVENTS:
        people = entrant_links(ev)
        print(ev, len(people), "linked entrants")
        for p in people:
            for c in program_cells(p):
                # partners' articles repeat the same Program; keep one copy
                k = (c["season"], c["segment"], BeautifulSoup(c["html"], "html.parser").get_text(" ", strip=True))
                if k not in seen:
                    seen.add(k); cells.append(c)
    (HERE / "cells.json").write_text(json.dumps(cells, ensure_ascii=False, indent=1))
    print(len(cells), "cells from", len({c['article'] for c in cells}), "articles")
