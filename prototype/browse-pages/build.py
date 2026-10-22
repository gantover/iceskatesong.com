"""PROTOTYPE, throwaway. Join real data into data.js for index.html:
  Performances  <- "Detailed results" tables of cached EN Wikipedia skater articles (ISU-looking events only)
  Programs      <- parsed music rows (results.json from the music-normaliser prototype)
  Videos        <- newest official ISU uploads (cache/*.json from fetch_videos.py), matched by surname + event + Segment
Run: python3 build.py <music-normaliser cache dir> <results.json>
"""
import json, pathlib, re, sys
from collections import defaultdict
from bs4 import BeautifulSoup

CACHE, RESULTS = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
HERE = pathlib.Path(__file__).parent
MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}
ISU = re.compile(r"World|Europe|Four Continents|Olymp|Grand Prix|JGP|Skate America|Skate Canada|NHK|Cup of China|Rostelecom|Cup of Russia|Trophée|Trophee|Bompard|Finland|Helsinki|Espoo|Team Trophy|Worlds|Europeans|\bGP\b|\bCS\b", re.I)
SEG = {"SP": "SP", "FS": "FS", "SD": "RD", "RD": "RD", "FD": "FD", "OD": "OD", "CD": "CD"}

def seg_of(name):  # Program segment label -> code
    n = name.lower()
    if "short dance" in n or "rhythm" in n: return "RD"
    if "original" in n: return "OD"
    if "free dance" in n: return "FD"
    if "short" in n: return "SP"
    if "free" in n: return "FS"

def grid(table):  # expand rowspan/colspan into a rectangular list of text rows
    out, carry = [], {}
    for tr in table.find_all("tr"):
        row, col = [], 0
        cells = tr.find_all(["th", "td"], recursive=False)
        while cells or col in carry:
            if col in carry:
                txt, left = carry[col]
                row.append(txt); carry[col] = (txt, left - 1)
                if left - 1 == 0: del carry[col]
                col += 1; continue
            c = cells.pop(0); txt = c.get_text(" ", strip=True)
            rs, cs = (int(m.group()) if (m := re.match(r"\d+", c.get(a) or "1")) else 1 for a in ("rowspan", "colspan"))
            for k in range(cs):
                row.append(txt)
                if rs > 1: carry[col] = (txt, rs - 1)
                col += 1
        out.append(row)
    return out

def season_of(date):
    m = re.search(r"([A-Za-z]{3})", date); ys = re.findall(r"(\d{4})", date)  # "Aug 2–5, 2017" or "21–24 March 2018"
    if not m or not ys or m.group(1).lower() not in MONTHS: return None, ""
    mo, y = MONTHS[m.group(1).lower()], int(ys[0])
    s = y if mo >= 7 else y - 1
    return f"{s}–{str(s + 1)[2:]}", f"{y:04d}-{mo:02d}"

def performances(html):  # per-season "Date | Event | SP | FS | Total" tables, rank+score split or as "1 82.98"
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for t in soup.find_all("table"):
        g = grid(t)
        hi = next((i for i, r in enumerate(g[:2]) if "Event" in r and "Date" in r and any(c in SEG for c in r)), None)
        if hi is None: continue
        h0 = g[hi]; sub = len(g) > hi + 1 and "P" in g[hi + 1]
        ev, dt = h0.index("Event"), h0.index("Date")
        segs = [(SEG[h0[i]], i) for i in range(len(h0)) if h0[i] in SEG and (not sub or g[hi + 1][i] == "P")]
        for r in g[hi + 1 + sub:]:
            if len(r) != len(h0): continue
            event = re.sub(r"\s*\[\s*\d+\s*\]", "", r[ev])
            if not ISU.search(event): continue
            season, ym = season_of(r[dt])
            if not season or season < "2004–05": continue
            for code, i in segs:
                cell = r[i] + (" " + r[i + 1] if sub and i + 1 < len(r) else "")
                m = re.match(r"(\d+)\s+([\d.]+)", cell)
                if m: out.append(dict(season=season, ym=ym, date=r[dt], event=event, seg=code, rank=int(m.group(1)), score=m.group(2)))
    return out

MONTH_GUESS = [("JGP Final", 12), ("JGP", 9), ("GP Final", 12), ("GP", 11), ("Europe", 1), ("Four", 2), ("Olymp", 2), ("Junior World", 3), ("World", 3)]

def highlights(html, segs_by_season):  # fallback: season x event placement grid, one Performance per Program Segment
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for t in soup.find_all("table"):
        g = grid(t)
        hi = next((i for i, r in enumerate(g[:3]) if r and r[0] in ("Event", "Season") and any(re.fullmatch(r"(\d\d)?\d\d–\d\d", c) for c in r)), None)
        if hi is None: continue
        head, section = g[hi], ""
        for r in g[hi + 1:]:
            if len(set(r)) == 1: section = r[0]; continue
            if "National" in section or not ISU.search(r[0]): continue
            for i, c in enumerate(r[1:len(head)], 1):
                m = re.match(r"(\d+)", c); sh = head[i]
                if not m or not re.fullmatch(r"(\d\d)?\d\d–\d\d", sh): continue
                y = int(sh[-5:-3]); y += 2000 if y < 50 else 1900
                season = f"{y}–{sh[-2:]}"
                if season < "2004–05": continue
                mo = next((mo for k, mo in MONTH_GUESS if k in r[0]), 11)
                ym = f"{y if mo >= 7 else y + 1:04d}-{mo:02d}"
                for code in segs_by_season.get(season, ["SP", "FS"]):
                    out.append(dict(season=season, ym=ym, date="", event=f"{r[0]} {season}", seg=code, rank=int(m.group(1)), score="", approx=True))
    return out

def grade(p):
    if p.get("qid"): return "identified"
    if p.get("composers") or p.get("source"): return "credited"
    return "title only"

res = json.load(open(RESULTS))
by_article = defaultdict(list)
for r in res["rows"]: by_article[r["article"]].append(r)
pieces_meta = {p["id"]: p for p in res["pieces"]}

skaters, perfs, programs, used = [], [], [], set()
for f in sorted(CACHE.glob("*.json")):
    d = json.load(open(f))
    if "parse" not in d: continue
    name = d["parse"]["title"]
    if name not in by_article: continue  # event articles etc.
    sid = len(skaters)
    pf = performances(d["parse"]["text"])
    if not pf:
        sbs = defaultdict(list)
        for r in by_article[name]:
            c = seg_of(r["segment"])
            se = r["season"][:5] + r["season"][-2:]
            if c and c not in sbs[se]: sbs[se].append(c)
        pf = highlights(d["parse"]["text"], sbs)
    skaters.append(dict(id=sid, name=re.sub(r" \(.*\)", "", name), article=name))
    for p in pf: perfs.append(dict(s=sid, **p))
    for r in by_article[name]:
        code = seg_of(r["segment"])
        if not code: continue
        ys = [int(y) for y in re.findall(r"\d{4}", r["season"])] or [int(r["season"][:4])]
        seasons = [f"{y}–{(y + 1) % 100:02d}" for y in range(min(ys), max(max(ys), min(ys) + 1))]  # "2010–2012" spans two Seasons
        music = [dict(piece=p["piece"], title=p["title"], composers=p["composers"], source=p["source"], performer=p["performer"], style=p["style"], grade=grade(p)) for p in r["pieces"] if p.get("piece") is not None]
        used.update(m["piece"] for m in music)
        for season in seasons: programs.append(dict(s=sid, season=season, seg=code, raw=r["raw"], music=[dict(m) for m in music]))

# merge several rows of one Program cell (Wikipedia lists one entry per line)
merged = {}
for p in programs:
    k = (p["s"], p["season"], p["seg"])
    if k in merged:
        merged[k]["raw"] += " / " + p["raw"]; merged[k]["music"] += p["music"]
    else: merged[k] = p
programs = list(merged.values())

# official videos: surname in CAPS + segment words + event words + year
videos = json.load(open(HERE / "cache/skating_isu.json")) + json.load(open(HERE / "cache/jgp.json"))
TSEG = [("Short Program", "SP"), ("Free Skating", "FS"), ("Rhythm Dance", "RD"), ("Free Dance", "FD")]
TEVENT = [("World Championships", "World Championships"), ("World Junior", "World Junior"), ("Four Continents", "Four Continents"), ("European", "European"), ("Grand Prix Final", "Grand Prix Final"), ("Olympic", "Olympic")]
by_skater = defaultdict(list)
for p in perfs: by_skater[p["s"]].append(p)
linked = 0
for v in videos:
    t = v["title"]
    seg = next((c for w, c in TSEG if w in t), None)
    evw = next((e for w, e in TEVENT if w in t), None)
    if not seg or not evw or "Junior" in t and evw != "World Junior": continue
    year = v["published"][:4]
    for s in skaters:
        sur = s["name"].split()[-1].upper()
        if not re.search(rf"\b{re.escape(sur)}\b", t): continue
        for p in by_skater[s["id"]]:
            if p["seg"] == seg and evw.lower() in p["event"].lower() and p["ym"][:4] == year:
                p.setdefault("videos", []).append(dict(yt=v["id"], kind="clip", origin="official", title=t))
                linked += 1

data = dict(skaters=skaters, perfs=perfs, programs=programs,
            pieces={i: dict(title=pieces_meta[i]["title"], qid=pieces_meta[i]["qid"], uses=pieces_meta[i]["uses"]) for i in used})
(HERE / "data.js").write_text("window.DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";")
print(f"skaters {len(skaters)} performances {len(perfs)} programs {len(programs)} pieces {len(used)} videos linked {linked}")
print(f"skaters with performances: {sum(1 for s in skaters if by_skater[s['id']])}")
