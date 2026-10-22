# /// script
# dependencies = ["httpx", "beautifulsoup4", "rapidfuzz", "anthropic", "pydantic"]
# ///
"""PROTOTYPE, throwaway. Raw Wikipedia music cells -> Pieces / Arrangements / Sources.

Tiers, cheapest first: rules -> Wikidata QID of the title wikilink -> fuzzy title match
(guarded by composer + Source) -> LLM for leftovers. Every entry records the tier that decided it.

Run: uv run normalise.py [--model claude-haiku-5-5|claude-opus-5-5] [--no-llm]
Reads cells.json (from fetch.py), writes out/<model>/results.json + results.html.
"""
import json, os, re, sys, random, unicodedata, time
from collections import defaultdict
from pathlib import Path
import httpx
from bs4 import BeautifulSoup, NavigableString
from rapidfuzz import fuzz, process
from pydantic import BaseModel

HERE = Path(__file__).parent
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "claude-haiku-5-5"
USE_LLM = "--no-llm" not in sys.argv
AGGR = "--aggressive" in sys.argv  # LLM parses every entry; every near-miss pair goes to the LLM
PRICE = {"claude-haiku-5-5": (0.10, 0.50), "claude-opus-5-5": (4.00, 20.00)}  # $/MTok in, out
SPEND_CAP = 3.00  # dollars, per run
OUT = HERE / "out" / ((MODEL + ("-aggressive" if AGGR else "")) if USE_LLM else "no-llm")
OUT.mkdir(parents=True, exist_ok=True)

# ---------- rules ----------
STYLE_WORDS = {  # parenthetical / performer hints -> Style
    "piano": "piano", "orchestral": "orchestral", "orchestra": "orchestral", "remix": "remix",
    "acoustic": "acoustic", "string quartet": "string-quartet cover", "quartet": "string-quartet cover",
    "cover": "vocal cover", "ballad": "ballad", "violin": "violin", "cello": "cello", "guitar": "guitar",
    "a cappella": "a cappella", "instrumental": "instrumental", "live": "live",
}
SKIP_SEG = re.compile(r"exhibition|pro-am|gala", re.I)
RHYTHM = re.compile(r"^((?:slow )?foxtrot|quickstep|tango|waltz|paso doble|rhumba|rumba|samba|cha[- ]cha(?: cha)?|"
                    r"blues|swing|hip[- ]hop|funk|flamenco|polka|march|jive|mambo|salsa|merengue|polonaise|"
                    r"mazurka|charleston|disco|rock(?:'n'| and | n )roll|bolero|lindy hop|finnstep|midnight blues)"
                    r"\s*(?:\d+)?\s*[:\-–]\s*", re.I)
MEDLEY = re.compile(r"\s/\s|medley|selections? (from|of)|;|\s\+\s", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\bno\.\s*", "no ", s)
    s = re.sub(r"[\"'“”‘’«»]", "", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^(the|a|an|la|le|el|il) ", "", s.strip())
    return re.sub(r"\s+", " ", s).strip()


def surname(name):
    n = norm(re.sub(r"\(.*?\)", "", name))
    return n.split()[-1] if n else ""


def lines_of(li):
    """Split an <li> (or a whole free-text cell) into text lines, keeping the first wikilink per line."""
    lines, cur, link = [], [], None
    for el in li.descendants:
        if getattr(el, "name", None) == "br":
            lines.append(("".join(cur).strip(), link)); cur, link = [], None
        elif getattr(el, "name", None) == "a" and link is None and el.get("href", "").startswith("/wiki/"):
            link = (el.get_text(strip=True), el["href"][6:].split("#")[0])
        elif isinstance(el, NavigableString) and not (el.parent.name == "sup" or el.find_parent("sup")):
            cur.append(str(el))
    lines.append(("".join(cur).strip(), link))
    return [(re.sub(r"\s+", " ", t).strip(), l) for t, l in lines if t.strip()]


def split_people(s):
    s = re.sub(r"\[\d+\]", "", s)
    return [p.strip(" .") for p in re.split(r",\s*(?:and\s+)?|\s+and\s+|\s*&\s*", s) if p.strip(" .")]


def template_entries(soup):
    """{{Figure skating program list}} cells: title div (or <ol> items) + a <ul> of credit lines."""
    box = soup.select_one("div[style*='padding-top:0.2em']")
    def credits(ul):
        return [(re.sub(r"\s+", " ", li.get_text(" ", strip=True)), None)
                for li in (ul.find_all("li", recursive=False) if ul else []) if li.get_text(strip=True)]
    def first_link(el):
        a = el.find("a", href=re.compile("^/wiki/"))
        return (a.get_text(strip=True), a["href"][6:].split("#")[0]) if a else None
    out = []
    ol = box.find("ol")
    shared = credits(box.find("ul", recursive=True) if not ol else ol.find_next_sibling("ul"))
    if ol:
        for li in ol.find_all("li", recursive=False):
            ul = li.find("ul")
            t = "".join(x.get_text(" ") if hasattr(x, "get_text") else str(x)
                        for x in li.contents if getattr(x, "name", None) != "ul").strip()
            out.append([(re.sub(r"\s+", " ", t), first_link(li))] + credits(ul) + shared)
    else:
        td = box.find("div", style=re.compile("line-height"))
        out.append([(td.get_text(" ", strip=True), first_link(td))] + shared)
    return out


def parse_entry(ls):
    """Rules tier on a list of (text, link) lines. Returns dict or None (None/flags -> LLM)."""
    if not ls:
        return None
    title, link = ls[0]
    e = {"title": title, "title_link": link, "composers": [], "source": None, "source_link": None,
         "performer": None, "arranger": None, "flags": []}
    rest, choreo = ls[1:], False
    # inline "Title by Composer" on the first line
    m = re.match(r"^(.*?)\s+(?:composed |written )?by\s+(.+)$", title)
    if m:
        e["title"] = m.group(1); rest = [(f"by {m.group(2)}", None)] + rest
    # inline "Title (from Source)"
    m = re.match(r"^(.*?)\s*\(from (.+)\)$", e["title"])
    if m:
        e["title"] = m.group(1); rest = [(f"(from {m.group(2)})", None)] + rest
    for t, l in rest:
        t = re.sub(r"^(all|both|medley of versions|music)\s+", "", t, flags=re.I)
        tl = t.lower()
        if choreo and not re.match(r"^\(?(from|by|performed|arr|composed)", tl):
            continue  # wrapped choreographer list
        if re.match(r"^([ivx]+\.|part \d|mvt|movement|\d+\. )", tl):
            e["title"] += ": " + t; continue
        if tl.startswith("(from") or tl.startswith("from "):
            e["source"] = re.sub(r"^\(?from\s+|\)$", "", t, flags=re.I).strip(); e["source_link"] = l
        elif tl.startswith("performed by") or tl.startswith("perf. by") or tl.startswith("sung by"):
            e["performer"] = re.sub(r"^\S+ by\s+", "", t, flags=re.I)
        elif re.match(r"^(arr\.|arranged) by", tl):
            e["arranger"] = re.sub(r"^\S+ by\s+", "", t, flags=re.I)
        elif tl.startswith("choreo") or tl.startswith("choreographed"):
            choreo = True
        elif re.match(r"^(composed |written )?by ", tl):
            body = re.sub(r"^(composed |written )?by\s+", "", t, flags=re.I)
            m = re.match(r"(.*?),?\s+(?:arr\.|arranged) by\s+(.*)", body)
            if m:
                body, e["arranger"] = m.group(1), m.group(2)
            m = re.match(r"(.*?),?\s+performed by\s+(.*)", body)
            if m:
                body, e["performer"] = m.group(1), m.group(2)
            e["composers"] += split_people(body)
        elif t.startswith("(") and t.endswith(")"):
            e["title"] += " " + t  # translation / version note on its own line
        else:
            e["flags"].append("unparsed line: " + t[:60])
    e["title"] = e["title"].strip().strip('"“”').strip()
    m = RHYTHM.match(e["title"])
    if m and e["title"][m.end():].strip():
        e["rhythm"], e["title"] = m.group(1), e["title"][m.end():].strip().strip('"“”')
    # Style from title parentheticals and arranger/performer
    e["style"] = "original"
    for p in re.findall(r"\(([^)]*)\)", e["title"]):
        for w, st in STYLE_WORDS.items():
            if w in p.lower():
                e["style"] = st
                e["title"] = e["title"].replace(f"({p})", "").strip()
    if e["style"] == "original" and e["arranger"]:
        e["style"] = "arrangement"
    if not e["performer"] and e["arranger"]:
        e["performer"] = e["arranger"]
    if MEDLEY.search(e["title"]):
        e["flags"].append("medley/multi-piece title")
    if len(e["title"]) > 70:
        e["flags"].append("long title")
    if not e["title"]:
        e["flags"].append("no title")
    return e


def entries_from_cells(cells):
    out = []
    for c in cells:
        if SKIP_SEG.search(c["segment"]):
            continue
        if not re.match(r"20(0[4-9]|[12]\d)", c["season"]):  # 2004-05 onwards
            continue
        if "padding-top:0.2em" in c["html"]:
            for ls in template_entries(BeautifulSoup(c["html"], "html.parser")):
                raw = " · ".join(t for t, _ in ls if not t.lower().startswith("choreo"))
                out.append({"id": len(out), "article": c["article"], "season": c["season"],
                            "segment": c["segment"], "program": 0, "raw": raw, "lines": ls})
            continue
        programs = re.split(r"<hr\s*/?>", c["html"])  # <hr> = mid-season music change
        for pi, ph in enumerate(programs):
            soup = BeautifulSoup(ph, "html.parser")
            lis = soup.find_all("li") or [soup]
            for li in lis:
                raw = li.get_text(" ", strip=True)
                if not raw or raw in ("—", "-", "N/A"):
                    continue
                out.append({"id": len(out), "article": c["article"], "season": c["season"],
                            "segment": c["segment"], "program": pi, "raw": raw, "lines": lines_of(li)})
    return out


# ---------- Wikidata ----------
def qids_for(titles):
    f = HERE / "cache" / "qids.json"
    cache = json.loads(f.read_text()) if f.exists() else {}
    todo = [t for t in dict.fromkeys(titles) if t not in cache]
    cl = httpx.Client(headers={"User-Agent": "iceskatesong-prototype/0.1 (+https://github.com/gantover/iceskatesong.com)"})
    for i in range(0, len(todo), 50):
        chunk = todo[i:i + 50]
        r = cl.get("https://en.wikipedia.org/w/api.php", params={
            "action": "query", "prop": "pageprops", "ppprop": "wikibase_item", "redirects": 1,
            "titles": "|".join(t.replace("_", " ") for t in chunk), "format": "json", "formatversion": 2}).json()
        q = r["query"]
        back = {x["to"]: x["from"] for x in q.get("normalized", []) + q.get("redirects", [])}
        back2 = {x["to"]: x["from"] for x in q.get("normalized", [])}
        for p in q["pages"]:
            t = p["title"]
            orig = back.get(t, t); orig = back2.get(orig, orig)
            cache[orig] = {"qid": p.get("pageprops", {}).get("wikibase_item"), "page": t}
        for t in chunk:  # anything unmatched
            cache.setdefault(t.replace("_", " "), {"qid": None, "page": None})
        time.sleep(0.2)
    f.write_text(json.dumps(cache, indent=0))
    return cache


# ---------- LLM tier ----------
class LPiece(BaseModel):
    title: str
    composers: list[str]
    source: str | None
    performer: str | None
    style: str


class LEntry(BaseModel):
    id: int
    pieces: list[LPiece]
    unsure: bool


class LBatch(BaseModel):
    entries: list[LEntry]


LLM_PROMPT = """You normalise figure-skating program music strings scraped from Wikipedia.
For each entry, return the musical Pieces it names, in order. A Piece is a musical work at the most
specific grain named: an aria, song or film cue, else the whole work. Medleys ("A / B", "selections")
become several Pieces. For each Piece give: canonical English title (no quotes, no version notes),
composers/songwriters (full names, never performers), source (the film, musical, ballet, opera, album or
franchise it comes from, or null), performer (credited performing artist of this version, or null),
style (one of: original, orchestral, piano, ballad, remix, vocal cover, string-quartet cover, acoustic,
instrumental, arrangement, other). Set unsure=true if you are guessing at any field.
Entries (JSON):
"""


STATS_F = OUT / "llm_stats.json"  # cumulative over runs, so cached re-runs still report the real cost
STATS = json.loads(STATS_F.read_text()) if STATS_F.exists() else {}
_client = None
import threading
from concurrent.futures import ThreadPoolExecutor
_lock = threading.Lock()


def ask(kind, prompt, schema):
    global _client
    if _client is None:
        import anthropic
        for line in (HERE.parents[1] / ".env").read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ.setdefault("ANTHROPIC_API_KEY", line.split("=", 1)[1].strip().strip('"'))
        _client = anthropic.Anthropic(max_retries=10)
    r = _client.messages.parse(model=MODEL, max_tokens=16000, output_config={"effort": "low"},
                               messages=[{"role": "user", "content": prompt}], output_format=schema)
    with _lock:
        st = STATS.setdefault(kind, {"calls": 0, "input_tokens": 0, "output_tokens": 0, "items": 0})
        st["calls"] += 1; st["input_tokens"] += r.usage.input_tokens; st["output_tokens"] += r.usage.output_tokens
        STATS_F.write_text(json.dumps(STATS))
    return r.parsed_output


def dollars(st):
    return (st["input_tokens"] * PRICE[MODEL][0] + st["output_tokens"] * PRICE[MODEL][1]) / 1e6


def spent():
    return sum(dollars(v) for v in STATS.values())


def llm_resolve(entries):
    cache_f = OUT / "llm_cache.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    todo = [e for e in entries if str(e["id"]) not in cache]
    batches = [todo[i:i + 25] for i in range(0, len(todo), 25)]
    def run(batch):
        if spent() > SPEND_CAP:
            return batch, None
        payload = json.dumps([{"id": e["id"], "text": e["raw"]} for e in batch], ensure_ascii=False)
        return batch, ask("parse", LLM_PROMPT + payload, LBatch)
    with ThreadPoolExecutor(4) as ex:
        for n, (batch, out) in enumerate(ex.map(run, batches), 1):
            if out is None:
                print("spend cap hit, batch skipped"); continue
            STATS["parse"]["items"] += len(batch)
            for le in out.entries:
                cache[str(le.id)] = le.model_dump()
            cache_f.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
            print(f"  parse batch {n}/{len(batches)}: ${spent():.4f}", flush=True)
    return cache


class LPair(BaseModel):
    id: str
    same_piece: bool


class LPairs(BaseModel):
    pairs: list[LPair]


PAIR_PROMPT = """Figure-skating program music. Each pair shows two groups of raw credits (title | credited
names | source film/ballet/etc.). Credited names may be composers OR performers. Decide whether both groups
name the same musical Piece: the same work at the same grain (an aria/song/film cue, else the whole work).
Different versions/covers/arrangements of one work ARE the same Piece. A whole work and one excerpt,
movement, aria or number from it are DIFFERENT Pieces (Romeo and Juliet ballet vs Dance of the Knights;
The Four Seasons vs Winter); two names for the same number are the same Piece. Same title by different composers is
NOT (e.g. Romeo and Juliet by Prokofiev vs by Tchaikovsky). A film soundtrack named as a whole and the same film
named as a whole are the same Piece. Pairs (JSON):
"""


def adjudicate(pairs):
    """pairs: list of {id, a: [variants], b: [variants]}. Returns {id: bool}."""
    cache_f = OUT / "pair_cache.json"
    cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    todo = [p for p in pairs if p["id"] not in cache]
    batches = [todo[i:i + 40] for i in range(0, len(todo), 40)]
    def run(batch):
        if spent() > SPEND_CAP:
            return batch, None
        return batch, ask("pairs", PAIR_PROMPT + json.dumps(batch, ensure_ascii=False), LPairs)
    with ThreadPoolExecutor(4) as ex:
        for n, (batch, out) in enumerate(ex.map(run, batches), 1):
            if out is None:
                print("spend cap hit, batch skipped"); continue
            STATS["pairs"]["items"] += len(batch)
            for x in out.pairs:
                cache[x.id] = x.same_piece
            cache_f.write_text(json.dumps(cache, indent=0))
            print(f"  pair batch {n}/{len(batches)}: ${spent():.4f}", flush=True)
    return cache


# ---------- clustering ----------
def compatible(a, b):
    """Composer guard: surnames overlap (fuzzy for transliterations), or a side is unknown."""
    if not a or not b:
        return None  # unknown
    return any(fuzz.ratio(x, y) >= 85 for x in a for y in b)


def src_compatible(a, b):
    if not a or not b:
        return None
    return fuzz.token_set_ratio(a, b) >= 85


def cluster(pieces_in):
    """pieces_in: list of dicts with ntitle, csur (set), nsource, qid. Assign piece_id + how."""
    pieces = []  # {id, ntitle, csur, nsource, qid, members}
    by_qid, near = {}, []
    titles = []
    for p in pieces_in:
        # a title link often points at the play/film (Source), so a shared QID still needs the composer guard
        if p["qid"] and p["qid"] in by_qid and compatible(p["csur"], by_qid[p["qid"]]["csur"]) is not False:
            pc = by_qid[p["qid"]]; pc["members"].append(p); p["piece"] = pc["id"]; p["how"] = "qid"
            pc["csur"] |= p["csur"]; continue
        best, how = None, None
        if titles:
            for t, score, idx in process.extract(p["ntitle"], titles, scorer=fuzz.ratio, limit=8, score_cutoff=70):
                pc = pieces[idx]
                comp, src = compatible(p["csur"], pc["csur"]), src_compatible(p["nsource"], pc["nsource"])
                if p["qid"] and pc["qid"] and p["qid"] != pc["qid"]:
                    if score >= 92: near.append((p, pc, score, "different QIDs"))
                    continue
                if score >= 92 and comp is not False and src is not False:
                    if comp or src or (p["qid"] and p["qid"] == pc["qid"]):
                        best, how = pc, "fuzzy"
                    elif score == 100 and not AGGR:
                        best, how = pc, "weak (title only)"  # no composer/source either side
                    else:
                        near.append((p, pc, score, "title close, nothing else to compare"))
                        continue
                    break
                elif score >= 92:
                    near.append((p, pc, score, "composer differs" if comp is False else "source differs"))
                elif score >= 85 and comp:
                    near.append((p, pc, score, "title similar, composer shared"))
                elif AGGR and score >= 80:
                    near.append((p, pc, score, "title similar"))
        if best:
            best["members"].append(p); p["piece"] = best["id"]; p["how"] = how
            best["csur"] |= p["csur"]
            if p["qid"] and not best["qid"]:
                best["qid"] = p["qid"]; by_qid[p["qid"]] = best
        else:
            pc = {"id": len(pieces), "ntitle": p["ntitle"], "csur": set(p["csur"]), "nsource": p["nsource"],
                  "qid": p["qid"], "members": [p]}
            pieces.append(pc); titles.append(p["ntitle"]); p["piece"] = pc["id"]; p["how"] = "new"
            if p["qid"]:
                by_qid[p["qid"]] = pc
    return pieces, near


# ---------- main ----------
def main():
    cells = json.loads((HERE / "cells.json").read_text())
    entries = entries_from_cells(cells)
    print(len(entries), "entries (one per listed Piece line) from", len(cells), "cells")
    for e in entries:
        e["parsed"] = parse_entry(e.pop("lines"))
    links = [e["parsed"]["title_link"][1] for e in entries if e["parsed"] and e["parsed"]["title_link"]]
    links += [e["parsed"]["source_link"][1] for e in entries if e["parsed"] and e["parsed"]["source_link"]]
    qmap = qids_for([l.replace("_", " ") for l in links])

    flagged = [e for e in entries if not e["parsed"] or e["parsed"]["flags"]]
    no_anchor = [e for e in entries if e["parsed"] and not e["parsed"]["flags"] and not e["parsed"]["composers"]
                 and not e["parsed"]["title_link"] and not e["parsed"]["source"]]
    to_llm = entries if AGGR else flagged + no_anchor
    llm = {}
    if USE_LLM:
        print(len(to_llm), "entries to the LLM tier")
        llm = llm_resolve(to_llm)
    llm_ids = {e["id"] for e in to_llm}

    # flatten to piece-occurrences
    occ = []
    for e in entries:
        p = e["parsed"]
        if e["id"] in llm_ids and str(e["id"]) in llm:
            le = llm[str(e["id"])]
            e["tier"] = "llm"; e["unsure"] = le["unsure"]
            # keep the title wikilink's QID when the LLM agrees on a single Piece with that title
            tl = p and p["title_link"]
            lq = (qmap.get(tl[1].replace("_", " "), {}).get("qid")
                  if tl and len(le["pieces"]) == 1 and fuzz.token_set_ratio(norm(tl[0]), norm(le["pieces"][0]["title"])) >= 85
                  else None)
            for k, lp in enumerate(le["pieces"]):
                occ.append({"entry": e["id"], "k": k, "title": lp["title"], "composers": lp["composers"],
                            "source": lp["source"], "performer": lp["performer"], "style": lp["style"],
                            "qid": lq, "source_qid": None})
            continue
        e["tier"] = "rules-unresolved" if e["id"] in llm_ids else "rules"
        if not p:
            continue
        tl = p["title_link"]
        qid = None
        if tl and fuzz.token_set_ratio(norm(tl[0]), norm(p["title"])) >= 85:
            qid = qmap.get(tl[1].replace("_", " "), {}).get("qid")
            if qid: e["tier"] = "rules+qid"
        sq = qmap.get(p["source_link"][1].replace("_", " "), {}).get("qid") if p["source_link"] else None
        occ.append({"entry": e["id"], "k": 0, "title": p["title"], "composers": p["composers"],
                    "source": p["source"], "performer": p["performer"], "style": p["style"],
                    "qid": qid, "source_qid": sq})
    for o in occ:
        o["ntitle"] = norm(re.sub(r"\(.*?\)", "", o["title"])) or norm(o["title"])
        o["csur"] = {surname(c) for c in o["composers"] if surname(c)}
        o["nsource"] = norm(o["source"])
    pieces, near = cluster(occ)

    # pair tier: near-miss Piece pairs go to the LLM as "same Piece?"; yes -> merge (union-find)
    def variants(pc):
        return sorted({f"{m['title']} | {', '.join(m['composers'])} | {m['source'] or ''}" for m in pc["members"]})[:4]
    pairs, seen = [], set()
    for p, pc, score, why in near:
        k = tuple(sorted((p["piece"], pc["id"])))
        if k[0] != k[1] and k not in seen:
            seen.add(k)
            pairs.append({"id": f"{k[0]}-{k[1]}", "why": why, "score": round(score),
                          "a": variants(pieces[k[0]]), "b": variants(pieces[k[1]])})
    verdict = adjudicate([{"id": x["id"], "a": x["a"], "b": x["b"]} for x in pairs]) if USE_LLM else {}
    parent = list(range(len(pieces)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    comps = {pc["id"]: set(pc["csur"]) for pc in pieces}  # composer surnames per root
    for x in sorted(pairs, key=lambda x: -x["score"]):  # most similar first
        x["same"] = verdict.get(x["id"])
        if x["same"]:
            a, b = map(int, x["id"].split("-")); ra, rb = find(a), find(b)
            if ra == rb:
                continue
            # chaining guard: never join two clusters whose known composers don't overlap,
            # else "Overture" (no composer) links every Overture together
            if comps[ra] and comps[rb] and compatible(comps[ra], comps[rb]) is False:
                x["blocked"] = True; continue
            parent[rb] = ra; comps[ra] |= comps.pop(rb)
    for o in occ:
        root = find(o["piece"])
        if root != o["piece"]:
            o["piece"], o["how"] = root, "llm pair"
    groups = defaultdict(list)
    for o in occ:
        groups[o["piece"]].append(o)
    pieces = [{"id": k, "qid": pieces[k]["qid"], "members": v} for k, v in groups.items()]

    # Sources: QID first, else normalised name
    src_ids = {}
    for o in occ:
        if o["source"]:
            k = o["source_qid"] or norm(o["source"])
            o["source_key"] = src_ids.setdefault(k, len(src_ids))
    # Arrangements = (Piece, Style, performer)
    arr = {}
    for o in occ:
        o["arrangement"] = arr.setdefault((o["piece"], o["style"], norm(o["performer"]) or None), len(arr))

    by_entry = defaultdict(list)
    for o in occ:
        by_entry[o["entry"]].append(o)
    rows = []
    for e in entries:
        rows.append({"id": e["id"], "article": e["article"], "season": e["season"], "segment": e["segment"],
                     "raw": e["raw"], "tier": e.get("tier"), "unsure": e.get("unsure", False),
                     "flags": (e["parsed"] or {}).get("flags", []),
                     "pieces": [{"title": o["title"], "composers": o["composers"], "source": o["source"],
                                 "performer": o["performer"], "style": o["style"], "piece": o["piece"],
                                 "how": o["how"], "qid": o["qid"], "arrangement": o["arrangement"]}
                                for o in by_entry[e["id"]]]})

    # review-needed: what a human (corrections.yaml in R1, Review Queue from R2) would see
    review = []
    for r in rows:
        why = []
        if r["tier"] == "rules-unresolved": why.append("rules flagged, no LLM answer")

        if any(p["how"] == "weak (title only)" for p in r["pieces"]): why.append("title-only merge")
        if not r["pieces"]: why.append("nothing parsed")
        if why: review.append({"id": r["id"], "why": why})
    near_out = pairs

    piece_out = []
    for pc in pieces:
        variants = sorted({(m["title"], ", ".join(m["composers"]), m["source"] or "") for m in pc["members"]})
        piece_out.append({"id": pc["id"], "title": pc["members"][0]["title"], "qid": pc["qid"],
                          "uses": len(pc["members"]), "variants": variants,
                          "hows": sorted({m["how"] for m in pc["members"]})})
    n = len(rows)
    tiers = defaultdict(int)
    for r in rows: tiers[r["tier"]] += 1
    summary = {"model": MODEL if USE_LLM else None, "entries": n, "cells": len(cells), "tiers": dict(tiers),
               "pieces": len(pieces), "arrangements": len(arr), "sources": len(src_ids),
               "piece_occurrences": len(occ), "merged_pieces": sum(1 for p in piece_out if len(p["variants"]) > 1),
               "review_needed": len(review), "review_per_100": round(100 * len(review) / n, 1),
               "pairs_judged": len(pairs), "pairs_said_same": sum(1 for x in pairs if x["same"]),
               "pairs_blocked_by_composer_guard": sum(1 for x in pairs if x.get("blocked")),
               "llm_unsure_rows": sum(1 for r in rows if r["unsure"]),
               "llm": {k: {**v, "dollars": round(dollars(v), 4)} for k, v in STATS.items()},
               "llm_dollars_total": round(spent(), 4),
               "llm_dollars_per_entry": round(spent() / n, 6),
               "llm_share": round(100 * len(to_llm) / n, 1)}
    data = {"summary": summary, "rows": rows, "pieces": piece_out, "near": near_out, "review": review}
    (OUT / "results.json").write_text(json.dumps(data, ensure_ascii=False, indent=0))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
