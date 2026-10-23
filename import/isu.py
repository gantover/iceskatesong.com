"""Parse ISU result pages (FS Manager by Swiss Timing): an event index and its SEGnnn pages."""

import datetime as dt
import html as htmllib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


class ParseError(Exception):
    pass


class Skipped(ParseError):
    """A page that is fine but not ours to import (Synchronized Skating is not one of the four Disciplines)."""


@dataclass
class Event:
    name: str
    city: str
    start: dt.date
    end: dt.date
    segment_pages: list[str]  # hrefs as the index prints them (SEG001.htm or SEG001.HTM)


@dataclass
class Entry:
    rank: int | None
    rank_label: str | None  # printed instead of a rank: WD, WDR, DSQ
    name: str
    nation: str
    isu_id: str | None
    tss: Decimal | None
    tes: Decimal | None
    pcs: Decimal | None
    deductions: Decimal | None
    start_number: int | None

    @property
    def key(self) -> str:
        """The import key as printed: the ISU ID, else name + nation."""
        return self.isu_id or f"{self.name} ({self.nation})"


@dataclass
class Segment:
    discipline: str
    level: str
    segment_type: str
    round: str
    entries: list[Entry]


DISCIPLINES = {"men": "men", "ladies": "women", "women": "women", "pairs": "pairs", "pair": "pairs",
               "pair skating": "pairs", "ice dance": "ice dance", "ice dancing": "ice dance"}
SEGMENT_TYPES = ["short program", "free skating", "short dance", "rhythm dance",
                 "free dance", "original dance", "compulsory dance"]
# Header text (after tags are stripped) → Entry field, matched by prefix.
COLUMNS = {"pl.": "rank", "name": "name", "nation": "nation", "tss": "tss", "tes": "tes", "pcs": "pcs",
           "tcs": "pcs", "ded": "deductions", "stn": "start_number"}  # TCS: early 2004–05 name for PCS


def decode(body: bytes) -> str:
    # Newer pages are ASCII/UTF-8; older ones are Latin-1 without a charset (e.g. "Göteborg").
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", errors="replace")


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")).strip()


def _dates(a1, sep, b1, year, a2, b2) -> tuple[dt.date, dt.date]:
    """Dots are day first (16.03.2008); with slashes either order is printed, so keep the reading that
    gives a plausible event (0 to 31 days: an Olympics with its team event runs 25). Years may have two digits.
    The end year comes from the start: events never cross New Year, and one index prints "10/13/2010 - 10/16/2020"."""
    orders = [(a1, b1, a2, b2)] if sep == "." else [(a1, b1, a2, b2), (b1, a1, b2, a2)]
    for d1, m1, d2, m2 in orders:
        try:
            y = int(year) + (2000 if len(year) == 2 else 0)
            start, end = dt.date(y, int(m1), int(d1)), dt.date(y, int(m2), int(d2))
        except ValueError:
            continue
        if 0 <= (end - start).days <= 31:
            return start, end
    raise ParseError(f"no plausible dates in {a1}{sep}{b1}{sep}{year} - {a2}{sep}{b2}")


def parse_index(page: str) -> Event:
    segment_pages = sorted(set(re.findall(r"(?i)href=\"?(SEG\d{3}\.html?)", page)))
    if not segment_pages:
        # e.g. the dataNNNN.htm pages of another vendor (some Japan-hosted events, 2017–2023)
        raise ParseError("no SEGnnn pages on the index")
    title = re.search(r"(?is)<title>(.*?)</title>", page)
    city = (re.search(r"(?is)<td[^>]*class=\"?caption3\"?[^>]*width=\"?50%[^>]*>(.*?)</td>", page)
            # 2004–05 Junior Grand Prix and Skate America: <H2>name</H2> <H3>city</H3> <H3>dates</H3>
            or re.search(r"(?is)</h2>\s*<p>\s*<h3>(.*?)</h3>", page))
    dates = re.search(r"(\d{1,2})([./])(\d{1,2})[./](\d{4}|\d\d)\s*-\s*(\d{1,2})[./](\d{1,2})[./]\d\d", page)
    if not (title and city and dates):
        raise ParseError("index without title, city or dates")
    start, end = _dates(*dates.groups())
    return Event(
        name=_text(title.group(1)),
        city=re.sub(r"\s*[/,]\s*[A-Z]{3}$", "", _text(city.group(1))),
        start=start,
        end=end,
        segment_pages=segment_pages,
    )


def _caption(caption: str) -> tuple[str, str, str, str]:
    """"<category> - <segment>", e.g. "Junior Ladies - Free Skating", "Team Men - Short Program",
    "Preliminary Round Ice Dance - Free Dance", "Men Single Skating - Short Program", "Men - Qualifying Group A",
    and the Olympic team events "Team Event - Men Single Skating - Short Program" (2022 on) and
    "Mixed NOC Team - Men Single Skating - Free Skating" (Youth Olympics 2020 on)."""
    caption = caption.lower()
    team_event = re.match(r"(team event|mixed noc team) - (?=.* - )", caption)
    if team_event:
        caption = "team " + caption[team_event.end():]
    category, _, segment = caption.partition(" - ")
    if " qualifying group " in category:  # "Men Qualifying Group A - Free Skating" (Junior Worlds 2005)
        category, _, group = category.partition(" qualifying group ")
        segment = "qualifying group " + group
    if category.startswith("synchronized"):
        raise Skipped(caption)
    round_ = ""
    for prefix in ("preliminary round", "team"):
        if category.startswith(prefix + " "):
            category, round_ = category.removeprefix(prefix + " "), prefix
    level = "junior" if category.startswith("junior ") else "senior"
    discipline = DISCIPLINES.get(category.removeprefix("junior ").removeprefix("senior ").removesuffix(" single skating"))
    if segment.startswith("qualifying") and discipline in ("men", "women", "pairs"):
        # Qualifying groups (to 2006) skated the free program ("Qualifying Free Skating A"): same Program.
        return discipline, level, "free skating", segment
    if not discipline or segment not in SEGMENT_TYPES:
        raise ParseError(f"unknown Segment caption {caption!r}")
    return discipline, level, segment, round_


def _number(s: str) -> Decimal | None:
    try:
        return Decimal(s) if s else None
    except InvalidOperation:
        raise ParseError(f"not a number: {s!r}") from None


def _given_first(name: str) -> str:
    """"TOTMIANINA Tatiana" → "Tatiana TOTMIANINA": Europeans 2005 and the 2006 Olympics print the surname
    (in capitals) first. Moves the leading all-caps words to the end when no all-caps word follows them."""
    # shortcut: guesses the order from capitals (only those two events trip it among the 2004–06 pages);
    # read each event's order instead if a given-first name ever starts with an all-caps word.
    words = name.split()
    n = next((i for i, w in enumerate(words) if not w.isupper()), len(words))
    return " ".join(words[n:] + words[:n]) if n and not any(w.isupper() for w in words[n:]) else name


def _name(printed: str, team: bool) -> str:
    """The name as printed, given name first; a Team's two Skaters joined by " / " (Europeans 2005 and the
    2006 Olympics print " - ")."""
    people = printed.split(" / " if " / " in printed else " - ") if team else [printed]
    return " / ".join(_given_first(p) for p in people)


def _entry(columns: list[str | None], cells: list[str], team: bool) -> Entry:
    if len(cells) != len(columns):
        raise ParseError(f"row has {len(cells)} cells, header has {len(columns)}")
    row = {field: cell for field, cell in zip(columns, cells) if field}
    isu_id = re.search(r"isufs(\d{8})", row["name"])
    rank, start_number = _text(row["rank"]), _text(row["start_number"]).lstrip("#")
    if not (start_number.isdigit() or start_number == ""):
        raise ParseError(f"bad start number: {start_number!r}")
    return Entry(
        rank=int(rank) if rank.isdigit() else None,
        rank_label=None if rank.isdigit() else rank or None,
        name=_name(_text(row["name"]), team),
        nation=_text(row["nation"]),
        isu_id=isu_id and isu_id.group(1),
        tss=_number(_text(row["tss"])),
        tes=_number(_text(row["tes"])),
        pcs=_number(_text(row["pcs"])),
        deductions=_number(_text(row["deductions"])),
        start_number=int(start_number) if start_number else None,
    )


def parse_segment(page: str) -> Segment:
    caption = (re.search(r"(?is)class=\"?caption2\"?>\s*<td[^>]*>(.*?)</td>", page)
               # 2004–05 Junior Grand Prix and Skate America: <CAPTION><H2>event</H2><H2>caption</H2>
               or re.search(r"(?is)<caption>\s*<h2>.*?</h2>\s*<h2>(.*?)</h2>", page))
    if not caption:
        raise ParseError("no Segment caption")
    discipline, level, segment_type, round_ = _caption(_text(caption.group(1)))

    # The results table: from its header row (the one with "Pl.") to the end of that table.
    table = re.search(r"(?is)(<tr[^>]*>\s*<th[^>]*>[^<]*Pl\..*?)</table>", page)
    if not table:
        raise ParseError("no results table")
    header, *rows = re.findall(r"(?is)<tr[^>]*>(.*?)</tr>", table.group(1))
    columns = [next((f for k, f in COLUMNS.items() if _text(h).lower().startswith(k)), None)
               for h in re.findall(r"(?is)<th[^>]*>(.*?)</th>", header)]
    if set(COLUMNS.values()) - set(columns):
        raise ParseError(f"missing columns {sorted(set(COLUMNS.values()) - set(columns))}")
    team = discipline in ("pairs", "ice dance")
    entries = [_entry(columns, re.findall(r"(?is)<td[^>]*>(.*?)</td>", row), team) for row in rows]
    if not entries:
        raise ParseError("no entries")
    if len({e.key for e in entries}) < len(entries):
        raise ParseError("two entries with the same import key")
    if team and any(len(e.name.split(" / ")) != 2 for e in entries):
        raise ParseError("a Team entry does not name two Skaters")
    return Segment(discipline, level, segment_type, round_, entries)
