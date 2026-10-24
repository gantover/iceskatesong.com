"""YouTube step: cache the official ISU channels' uploads and link their clips and streams to Performances.

Titles are a transient signal (API terms): only the YouTube ID and our link outlive the 30-day cache.
"""

import datetime as dt
import functools
import html
import http.client
import json
import re
import unicodedata
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlencode

API = "https://www.googleapis.com/youtube/v3/"
SKATING_ISU, JGP = "UCVZpqbnDjHyScSYGFPMUtYA", "UCbv3gsBXzIwotCt2JGySfJA"  # JGP: the junior channel
REFRESH_DAYS = 25
CLIP_SECONDS, STREAM_SECONDS = 100, 30 * 60
NO_MATCH = "official video with no Performance match"


@dataclass
class Video:
    youtube_id: str
    title: str
    channel_id: str
    published_at: dt.datetime
    duration_seconds: int


@dataclass
class Entry:
    performance_id: int
    name: str  # as printed: "Given SURNAME", a Team's two Skaters joined by " / "
    nation: str
    start_number: int | None


@dataclass
class Segment:
    discipline: str
    level: str
    segment_type: str
    entries: list[Entry]


@dataclass
class Event:
    code: str  # the last part of the ISU event path, e.g. gpf2025
    name: str
    city: str
    start: dt.date
    end: dt.date
    segments: list[Segment]


def api(key: str, base=API):
    """A YouTube Data API GET. The key goes in a header, so no URL, log or problem ever holds it."""
    def get(path: str, **params) -> dict:
        request = urllib.request.Request(f"{base}{path}?{urlencode(params)}", headers={"X-Goog-Api-Key": key})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    return get


def fetch(conn, get, problems: list[dict]) -> None:
    """Cache both uploads playlists: videos.list each new video and each row older than REFRESH_DAYS.

    `conn` is in autocommit mode (the fetch phase). A failed request is a problem and leaves the rest of the cache as it was.
    """
    path = "playlistItems"
    try:
        ids = []
        for channel in (SKATING_ISU, JGP):
            page = {}
            while True:
                page = get(path, part="contentDetails", playlistId="UU" + channel[2:], maxResults=50,
                           **({"pageToken": page["nextPageToken"]} if "nextPageToken" in page else {}))
                ids += [item["contentDetails"]["videoId"] for item in page["items"]]
                if "nextPageToken" not in page:
                    break
        if not ids:  # an empty answer would empty the cache below
            raise ValueError("no uploads")
        # Only after a complete pass: a video gone from both playlists leaves the cache (its links stay).
        conn.execute("delete from youtube_videos where youtube_id <> all(%s)", [ids])
        fresh = {i for (i,) in conn.execute(
            "select youtube_id from youtube_videos where refreshed_at > now() - make_interval(days => %s)", [REFRESH_DAYS])}
        wanted = [i for i in dict.fromkeys(ids) if i not in fresh]
        path = "videos"
        for n in range(0, len(wanted), 50):
            batch = wanted[n:n + 50]
            items = get(path, part="snippet,contentDetails,status", id=",".join(batch), maxResults=50)["items"]
            # Not returned: deleted or made private since the playlist page.
            conn.execute("delete from youtube_videos where youtube_id = any(%s)", [list(set(batch) - {i["id"] for i in items})])
            with conn.cursor() as cur:
                cur.executemany(
                    """insert into youtube_videos (youtube_id, title, channel_id, published_at, duration_seconds, blocked_regions,
                         allowed_regions, embeddable, made_for_kids, refreshed_at)
                       values (%(youtube_id)s, %(title)s, %(channel_id)s, %(published_at)s, %(duration_seconds)s,
                         %(blocked_regions)s, %(allowed_regions)s, %(embeddable)s, %(made_for_kids)s, now())
                       on conflict (youtube_id) do update set title = excluded.title, channel_id = excluded.channel_id,
                         published_at = excluded.published_at, duration_seconds = excluded.duration_seconds,
                         blocked_regions = excluded.blocked_regions, allowed_regions = excluded.allowed_regions,
                         embeddable = excluded.embeddable, made_for_kids = excluded.made_for_kids, refreshed_at = now()""",
                    [cache_row(item) for item in items])
    # URLError and HTTPError are OSErrors (their text holds no URL); the others are answers not shaped as expected.
    except (OSError, http.client.HTTPException, ValueError, KeyError, AttributeError) as e:
        problems.append({"step": "youtube", "kind": "fetch failed", "key": API + path, "detail": {"error": str(e)}})


def link(conn, problems: list[dict]) -> dict:
    """Match every cached video against every Performance and add the links not there yet; never touches a link's status."""
    events: dict[int, Event] = {}
    segments: dict[int, Segment] = {}
    for row in conn.execute(
            """select c.id, k.value, c.name, c.city, c.start_date, c.end_date, s.id, s.discipline, s.level, s.segment_type,
                      p.id, p.name, p.nation, p.start_number
               from performances p join segments s on s.id = p.segment_id join competitions c on c.id = s.competition_id
               join keys k on k.system = 'isu-event' and k.entity = 'competition' and k.entity_id = c.id
               where not p.gone order by p.id"""):
        event = events.setdefault(row[0], Event(row[1].rsplit("/", 1)[-1], *row[2:6], []))
        if row[6] not in segments:
            segments[row[6]] = Segment(*row[7:10], [])
            event.segments.append(segments[row[6]])
        segments[row[6]].entries.append(Entry(*row[10:]))
    pairs = []
    videos = conn.execute("select youtube_id, title, channel_id, published_at, duration_seconds from youtube_videos order by youtube_id")
    for video in [Video(*row) for row in videos]:
        ids, reason = match(video, list(events.values()))
        if reason:
            # The title stays out: it is API data, and problems outlive the 30-day cache.
            problems.append({"step": "youtube", "kind": NO_MATCH, "key": video.youtube_id,
                             "detail": {"reason": reason, "performances": ids}})
        else:
            pairs += [(video.youtube_id, i) for i in ids]
    created = conn.execute(
        """insert into performance_videos (youtube_id, performance_id, origin)
           select youtube_id, performance_id, 'official' from unnest(%s::text[], %s::bigint[]) as v (youtube_id, performance_id)
           on conflict do nothing""", [list(column) for column in zip(*pairs)] or [[], []]).rowcount
    return {"performance video": {"created": created, "updated": 0}} if created else {}


def cache_row(item: dict) -> dict:
    """A youtube_videos row from one videos.list item."""
    region = item["contentDetails"].get("regionRestriction", {})
    return {"youtube_id": item["id"], "title": item["snippet"]["title"], "channel_id": item["snippet"]["channelId"],
            "published_at": dt.datetime.fromisoformat(item["snippet"]["publishedAt"]),
            "duration_seconds": seconds(item["contentDetails"]["duration"]),
            "blocked_regions": region.get("blocked", []), "allowed_regions": region.get("allowed"),
            "embeddable": item["status"]["embeddable"], "made_for_kids": item["status"]["madeForKids"]}


def seconds(duration: str) -> int:
    """ISO 8601 as the API prints it: PT1H4M45S, P1DT2H, P0D."""
    d, h, m, s = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", duration).groups()
    return ((int(d or 0) * 24 + int(h or 0)) * 60 + int(m or 0)) * 60 + int(s or 0)


# ---------- matching ----------
FOLD = str.maketrans({"ł": "l", "Ł": "L", "ø": "o", "Ø": "O", "đ": "d", "ß": "ss", "æ": "ae", "’": "'"})


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", html.unescape(s).translate(FOLD))
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c)).lower()).strip()


# Not one Performance: other sports, highlights, interviews, galas, live and so on.
SKIP = (r"#shorts|\bwinners?\b|speed ?skating|short ?track|\b\d{3,5} ?m\b|relay|highlights|interview|relive|recap|"
        r"press conference|medal ceremony|victory ceremony|warm ?up|preview|behind the scenes|exhibition|gala|kiss|"
        r"live\b|🔴|day \d|best of|top \d")
STREAM_SKIP = r"|practice|ceremony|medals"
DISCIPLINES = [("ice dance", r"ice dance|\bdance\b"), ("pairs", r"\bpairs?\b"), ("women", r"\bwomen\b|\bladies\b|\bgirls\b"),
               ("men", r"\bmen\b|\bboys\b")]
# Short Dance is matched as Rhythm Dance (SAME_TYPE); in dance, Free and Short are mapped below.
SEGMENT_TYPES = [("compulsory dance", r"compulsory dance|\bcd\b"), ("free dance", r"free dance|\bfd\b"),
                 ("rhythm dance", r"rhythm dance|short dance|\brhythm\b|\bsd\b|\brd\b"), ("original dance", r"original dance|\bod\b"),
                 ("short program", r"short program|\bshort\b|\bsp\b"),
                 ("free skating", r"free skating|free skate|free program|\bfs\b|\bfree\b")]
SAME_TYPE = {"short dance": "rhythm dance"}
DANCE_TYPE = {"free skating": "free dance", "short program": "rhythm dance"}
GENERIC = set("skate isu figure skating championships championship world junior grand prix final international trophy cup "
              "of the gp jgp".split())
# One alias list per event type (ISU code prefix), not per event; Junior Grand Prix events are named by their city.
TYPE_ALIASES = {
    "wc": ["world championships", "world champs", "world figure skating", "worldfigure", "worlds"],
    "wjc": ["junior world", "world junior", "worldjfigure", "jr worlds", "junior worlds"],
    "ec": ["european", "euro champs", "eurofigure", "europeans"], "fc": ["four continents", "4contsfigure", "4cc"],
    "gpf": ["grand prix final", "gp final", "gp finals", "gpf"], "wtt": ["world team trophy", "wttfigure", "wtt"],
    "gpusa": ["skate america"], "gpcan": ["skate canada"], "gpchn": ["cup of china"],
    "gpfra": ["grand prix de france", "internationaux de france"], "gpjpn": ["nhk trophy"], "gpfin": ["finlandia"],
    "gpita": ["gran premio d italia", "grand prix of italy"],
}


def classify(t: str, table) -> str | None:
    return next((value for value, rx in table if re.search(rx, t)), None)


def names_event(t: str, event: Event) -> bool:
    """The title names the event by its type's alias, or by a word of its city or name."""
    if any(re.search(rf"\b{a}\b", t) for a in TYPE_ALIASES.get(re.sub(r"\d+$", "", event.code), [])):
        return True
    return not event_words(event.city, event.name).isdisjoint(t.split())


@functools.cache  # every video asks of every event
def event_words(city: str, name: str) -> frozenset[str]:
    return frozenset(w for w in norm(f"{city} {name}").split() if len(w) > 3 and w not in GENERIC and not w.isdigit())


def surnames(name: str) -> list[list[str]]:
    """Per Skater, the words ISU prints in capitals (2+ capitals: McBEATH, O'SHEA)."""
    return [[x for w in part.split() if sum(c.isupper() for c in w) >= 2 for x in norm(w).split()] for part in name.split("/")]


def givens(name: str) -> list[str]:
    return [norm(w) for part in name.split("/") for w in part.split() if sum(c.isupper() for c in w) < 2]


def close(a: str, b: str) -> bool:
    """At most one insertion, deletion or substitution apart (title typos like JUSKATE for JUSKAITE)."""
    if abs(len(a) - len(b)) > 1 or a == b:
        return a == b
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    return a[i + 1:] == b[i + 1:] or a[i:] == b[i + 1:] or a[i + 1:] == b[i:]


def match(video: Video, events: list[Event]) -> tuple[list, str | None]:
    """(Performance IDs, None) to link; (candidate Performance IDs, reason) to log; ([], None) when not ours."""
    t = norm(video.title)
    stream = video.duration_seconds > STREAM_SECONDS
    if re.search(SKIP + (STREAM_SKIP if stream else ""), video.title, re.I) or video.duration_seconds < CLIP_SECONDS:
        return [], None
    discipline, segment_type = classify(t, DISCIPLINES), classify(t, SEGMENT_TYPES)
    if not discipline:
        return [], None
    if discipline == "ice dance":
        segment_type = DANCE_TYPE.get(segment_type, segment_type)
    # Junior is known from the channel or the title; a stream without "junior" on the main channel is senior.
    level = "junior" if video.channel_id == JGP or re.search(r"\bjunior\b|\bjr\b", t) else "senior" if stream else None

    # The event the title names comes first; the publishedAt window only narrows a title without a year.
    years = {int(y) for y in re.findall(r"\b(?:19|20)\d\d\b", t)}
    published = video.published_at.date()
    in_window = lambda e: e.start - dt.timedelta(days=2) <= published <= e.end + dt.timedelta(days=10)
    named = [e for e in events if names_event(t, e)]
    # Only when the title names no event: the window alone, and a match found that way is logged, not linked.
    verified = bool(named)
    candidates = ([e for e in named if (years & {e.start.year, e.end.year} if years else in_window(e))] if verified
                  else [e for e in events if in_window(e)])
    if not candidates:
        return [], None  # names no loaded event

    segments = [s for e in candidates for s in e.segments if s.discipline == discipline
                and (not segment_type or SAME_TYPE.get(s.segment_type, s.segment_type) == segment_type)
                and (not level or s.level == level)]
    ids, reason = (stream_match if stream else clip_match)(t, segment_type, segments)
    if not verified:
        return (ids, "matched by the publishedAt window only") if ids and not reason else ([], None)
    return ids, reason


def clip_match(t: str, segment_type: str | None, segments: list[Segment]) -> tuple[list, str | None]:
    if not segment_type:
        return [], "no Segment type in the title"
    words = set(t.split())
    hits = []
    for fuzzy in (False, True):
        for s in segments:
            for e in s.entries:
                sn = surnames(e.name)
                if all(p and all(w in words or (fuzzy and len(w) > 4 and any(close(w, x) for x in words)) for w in p) for p in sn):
                    hits.append((sum(g in words for g in givens(e.name)) + (e.nation.lower() in words), e.performance_id))
        if hits:
            break
    if not hits:
        return [], "no entry matches the title" if segments else "no Segment matches the title"
    best = max(score for score, _ in hits)
    top = [performance_id for score, performance_id in hits if score == best]
    return (top, None) if len(top) == 1 else (top, "several entries match the title")


def stream_match(t: str, segment_type: str | None, segments: list[Segment]) -> tuple[list, str | None]:
    """A full-segment stream: every Performance of its Segment, or of the "Skaters N–M" start numbers it shows."""
    if len(segments) != 1 or not segment_type:
        return [], "stream matches no single Segment"
    entries = segments[0].entries
    if m := re.search(r"\bskaters? (\d+) (\d+)\b", t):
        first, last = int(m[1]), int(m[2])
        entries = [e for e in entries if e.start_number and first <= e.start_number <= last]
        if not entries:
            return [], "no start number in the stream's range"
    elif re.search(r"\bgroups?\b", t):
        return [], "group stream without a start-number range"
    return [e.performance_id for e in entries], None
