"""PROTOTYPE, throwaway. Match official ISU YouTube uploads to Performances in the sampled ISU results.

Idea under test: don't parse the Competition out of the title. Pick candidate events by
publishedAt falling in the event's date window (fallback: title year + city), pick the Segment
by Discipline/level/Segment type, then find the entry whose surnames all appear in the title.
"""
import collections, datetime as dt, html, json, pathlib, re, unicodedata

HERE = pathlib.Path(__file__).parent
ISU = HERE / "cache" / "isu"
FOLD = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "ß": "ss", "æ": "ae", "’": "'"})


def norm(s):
    s = unicodedata.normalize("NFKD", s.translate(FOLD))
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip()


def text(h):
    h = re.sub(r"(?is)<(style|script)[^>]*>.*?</\1>", " ", h)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h).replace("&nbsp;", " "))


DISC = [("D", r"ice dance|\bdance\b"), ("P", r"\bpairs?\b"), ("W", r"\bwomen\b|\bladies\b|\bgirls\b"), ("M", r"\bmen\b|\bboys\b")]
SEG = [("FD", r"free dance|\bfd\b"), ("RD", r"rhythm dance|short dance|\brhythm\b|\bsd\b|\brd\b"), ("OD", r"original dance"),
       ("SP", r"short program|\bshort\b|\bsp\b"), ("FS", r"free skating|free skate|free program|\bfs\b|\bfree\b")]


def classify(s, table):
    s = norm(s)
    for k, rx in table:
        if re.search(rx, s):
            return k


# ---------- ISU side ----------
def load_events():
    events = []
    for idx in sorted(ISU.glob("*_index.htm")):
        code = idx.name[: -len("_index.htm")]
        h = idx.read_text(encoding="utf-8", errors="replace")
        t = text(h)
        d1, d2 = re.search(r"(\d\d\.\d\d\.\d{4}) - (\d\d\.\d\d\.\d{4})", t).groups()
        name = re.search(r"(?is)<title>(.*?)</title>", h).group(1).strip()
        name_city = re.match(r"\s*(.*?)\s+([^/]+?) / [A-Z]{3}", t[len(name) + 1:] if name else t)
        city = name_city.group(2).strip()
        name = name or name_city.group(1)
        ev = {"code": code, "name": name, "city": city, "start": dt.datetime.strptime(d1, "%d.%m.%Y").date(),
              "end": dt.datetime.strptime(d2, "%d.%m.%Y").date(), "segments": []}
        for f in sorted(ISU.glob(code + "_SEG*")):
            h = f.read_text(encoding="utf-8", errors="replace")
            head = text(h)[:400]
            m = re.search(r"((?:Junior )?(?:Men|Ladies|Women|Pairs?|Ice Dance)) - ([A-Za-z ]+?)(?= Result| Starting| Pl\.|  |$)", head)
            cat, seg = m.groups()
            entries = []
            for row in re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", h):
                b = re.search(r"(?i)isufs(\d{8})\.htm[^>]*>([^<]+)</a>\s*</td>\s*<td[^>]*>([A-Z]{3})", row)
                if b:
                    entries.append({"isu_id": b.group(1), "name": html.unescape(b.group(2).strip()), "nat": b.group(3)})
            ev["segments"].append({"page": f.name, "disc": classify(cat, DISC), "junior": cat.startswith("Junior"),
                                   "seg": classify(seg, SEG), "label": f"{cat} - {seg}", "entries": entries})
        events.append(ev)
    return events


def close(a, b):
    # one insertion/deletion/substitution apart (typos like JUSKATE for JUSKAITE)
    if abs(len(a) - len(b)) > 1 or a == b: return a == b
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    return a[i + 1:] == b[i + 1:] or a[i:] == b[i + 1:] or a[i + 1:] == b[i:]


def surnames(name):
    # ISU writes "Given SURNAME"; teams are "A B / C D"
    return [[x for w in part.split() if sum(c.isupper() for c in w) >= 2 for x in norm(w).split()] for part in name.split("/")]


def givens(name):
    return [norm(w) for part in name.split("/") for w in part.split() if sum(c.isupper() for c in w) < 2]


# ---------- YouTube side ----------
NOT_PERF = r"#shorts|\bwinners?\b|speed ?skating|short ?track|\b\d{3,5} ?m\b|relay|highlights|interview|relive|recap|press conference|medal ceremony|victory ceremony|warm ?up|preview|behind the scenes|exhibition|gala|kiss|live\b|🔴|day \d|best of|top \d"


GENERIC = set("skate isu figure skating championships championship world junior grand prix final international trophy cup of the gp jgp".split())


# one alias list per event *type* (ISU code prefix), not per event; JGP events are named by city
TYPE_ALIASES = {
    "wc": ["world championships", "world champs", "world figure skating", "worldfigure", "worlds"],
    "wjc": ["junior world", "world junior", "worldjfigure", "jr worlds", "junior worlds"],
    "ec": ["european", "euro champs", "eurofigure", "europeans"], "fc": ["four continents", "4contsfigure", "4cc"],
    "gpf": ["grand prix final", "gp final", "gp finals", "gpf"], "wtt": ["world team trophy", "wttfigure", "wtt"],
    "gpusa": ["skate america"], "gpcan": ["skate canada"], "gpchn": ["cup of china"], "gpfra": ["grand prix de france", "internationaux de france"],
    "gpjpn": ["nhk trophy"], "gpfin": ["finlandia"], "gpita": ["gran premio d italia", "grand prix of italy"],
}


def event_type(e):
    return re.sub(r"\d+$", "", e["code"].split("_")[-1])


def names_event(t, e):
    words = set(t.split())
    year_ok = any(str(y) in words for y in (e["start"].year, e["end"].year)) or not re.search(r"\b(19|20)\d\d\b", t)
    if year_ok and any(re.search(rf"\b{a}\b", t) for a in TYPE_ALIASES.get(event_type(e), [])):
        return True
    return any(w in words for w in norm(e["city"] + " " + e["name"]).split() if len(w) > 3 and w not in GENERIC and not w.isdigit())


def candidates_for(video, events):
    pub = dt.date.fromisoformat(video["published"][:10])
    by_date = [e for e in events if e["start"] - dt.timedelta(days=2) <= pub <= e["end"] + dt.timedelta(days=10)]
    if by_date:
        return by_date, "date"
    t = norm(video["title"])
    by_city = [e for e in events if any(w in t.split() for w in norm(e["city"]).split() if len(w) > 3)
               and str(e["start"].year) in t]
    return by_city, "city+year"


def match(video, events):
    title = video["title"]
    t = norm(title)
    if re.search(NOT_PERF, title, re.I):
        return {"status": "skipped: not a single Performance"}
    disc, seg = classify(title, DISC), classify(title, SEG)
    if disc == "D" and seg in ("FS", "SP"):
        seg = {"FS": "FD", "SP": "RD"}[seg]
    if not disc:
        return {"status": "skipped: not figure skating"}
    junior = True if (video["channel"] == "jgp" or re.search(r"\bjunior\b|\bjr\b", t)) else None
    evs, how = candidates_for(video, events)
    if not evs:
        return {"status": "outside sample"}
    words = set(t.split())
    hits = []
    for fuzzy in (False, True):
      if hits: break
      for e in evs:
        for s in e["segments"]:
            if s["disc"] != disc or (seg and s["seg"] != seg and not {s["seg"], seg} <= {"RD", "SP"}):
                continue
            if junior is not None and s["junior"] != junior:
                continue
            for en in s["entries"]:
                sn = surnames(en["name"])
                if sn and all(p and all(w in words or (fuzzy and len(w) > 4 and any(close(w, x) for x in words)) for w in p) for p in sn):
                    score = 2 + sum(g in words for g in givens(en["name"])) + (en["nat"].lower() in words)
                    hits.append((score, e, s, en))
    if not hits:
        # is there a skater name at all? per-skater titles carry "(NAT)" or "NAT |"
        named = re.search(r"\((?:[A-Z]{3}|AIN ?\d?)\)|\b[A-Z]{3} \|", title)
        return {"status": "no entry match" if named else "segment-level (no skater named)", "how": how,
                "events": [e["code"] for e in evs]}
    hits.sort(key=lambda h: -h[0])
    top = [h for h in hits if h[0] == hits[0][0]]
    if len({(h[1]["code"], h[2]["page"], h[3]["isu_id"]) for h in top}) > 1:
        return {"status": "ambiguous", "how": how, "options": [f'{h[1]["code"]} {h[2]["label"]} {h[3]["name"]}' for h in top]}
    _, e, s, en = hits[0]
    city_ok = names_event(t, e)
    return {"status": "matched" if city_ok else "unverified (date+name only)", "how": how, "event": e["code"], "segment": s["label"], "entry": en["name"],
            "isu_id": en["isu_id"], "entry_nat": en["nat"], "title_names_event": city_ok, "seg_in_title": bool(seg)}


def main():
    events = load_events()
    videos = [dict(v, channel=ch) for ch in ("skating_isu", "jgp") for v in json.load(open(HERE / "cache" / f"{ch}.json"))]
    out = [dict(v, **match(v, events)) for v in videos]
    for o in out:
        pub = dt.date.fromisoformat(o["published"][:10])
        o["names_sampled"] = any(names_event(norm(o["title"]), e) and abs((pub - e["start"]).days) < 365 for e in events)
    (HERE / "out").mkdir(exist_ok=True)
    (HERE / "out" / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))

    print("events:", len(events), "| segments:", sum(len(e["segments"]) for e in events),
          "| entries:", sum(len(s["entries"]) for e in events for s in e["segments"]))
    print("videos:", len(videos))
    print(collections.Counter(o["status"] for o in out).most_common())
    inside = [o for o in out if o["status"] in ("matched", "ambiguous", "no entry match", "unverified (date+name only)")]
    m = [o for o in inside if o["status"] == "matched"]
    print(f"\nper-skater videos in sampled events: {len(inside)}, matched {len(m)} ({len(m)/max(1,len(inside)):.0%})")
    named = [o for o in inside if o.get("names_sampled")]
    nm = [o for o in named if o["status"] == "matched"]
    print(f"RECALL on per-skater videos whose title names a sampled event: {len(nm)}/{len(named)} ({len(nm)/max(1,len(named)):.0%})")
    print("  misses:", collections.Counter(o["status"] for o in named if o["status"] != "matched"))
    print("matched via:", collections.Counter(o["how"] for o in m), "| title names the event:",
          collections.Counter(o["title_names_event"] for o in m))
    # coverage: Performances in sample vs Performances with >=1 video
    perfs = {(e["code"], s["page"], en["isu_id"]) for e in events for s in e["segments"] for en in s["entries"]}
    seen = collections.Counter((o["event"], next(s["page"] for e in events if e["code"] == o["event"] for s in e["segments"] if s["label"] == o["segment"]), o["isu_id"]) for o in m)
    print(f"Performances in sample: {len(perfs)}, with a video: {len(seen)}, with >1 video: {sum(c > 1 for c in seen.values())}")
    for e in events:
        n = sum(1 for k in perfs if k[0] == e["code"]); k = sum(1 for k in seen if k[0] == e["code"])
        print(f'  {e["code"]:28} {e["start"]} {n:4} perfs {k:4} with video ({k/max(1,n):.0%})')


if __name__ == "__main__":
    main()
