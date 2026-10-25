"""Wikipedia program tables, reached through the Wikidata crosswalk; never creates Programs."""

import dataclasses
import json
import re
from urllib.parse import unquote, urlencode, urlsplit

from bs4 import BeautifulSoup
from psycopg.types.json import Jsonb

import wikidata

ENDPOINT = "https://en.wikipedia.org/w/api.php"
SEGMENTS = ("short program", "free skating", "short dance", "rhythm dance", "free dance", "original dance", "compulsory dance")


@dataclasses.dataclass
class Row:
    season: int
    segment_type: str
    raw_text: str
    titles: list[str]
    partner: str | None
    entries: list[dict] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Article:
    title: str
    revision: int
    rows: list[Row]
    follows: list[str]


def api_url(endpoint, **params):
    return endpoint + "?" + urlencode({"format": "json", "formatversion": 2, **params})


def problem(problems, kind, key, **detail):
    problems.append({"step": "wikipedia", "kind": kind, "key": key, "detail": detail})


def link_title(link):
    href = link.get("href", "")
    parts = urlsplit(href)
    if parts.netloc not in ("", "en.wikipedia.org") or not parts.path.startswith("/wiki/"):
        return None
    title = unquote(parts.path[6:]).replace("_", " ")
    return title if ":" not in title else None


def text(cell):
    return re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()


def music_entries(cell):
    """Keep Piece boundaries and visible link labels, including the program-list template's shared credits."""
    def entry(nodes):
        return {"raw": " ".join(text(n) for n in nodes),
                "titles": {text(a): title for n in nodes for a in n.select("a[href]") if (title := link_title(a))}}

    if box := cell.select_one("div[style*='padding-top:0.2em']"):
        ordered = box.find("ol")
        shared = ordered.find_next_sibling("ul") if ordered else box.find("ul")
        if ordered:
            entries = []
            for li in ordered.find_all("li", recursive=False):
                nodes = [li]
                if shared:
                    nodes.append(shared)
                entries.append(entry(nodes))
            return entries
        title = box.find("div", style=re.compile("line-height"))
        if title:
            return [entry([title] + ([shared] if shared else []))]
    listed = [li for li in cell.find_all("li") if not li.find_parent("li")]
    return [entry([li]) for li in listed] if listed else [entry([cell])]


def span(cell, name):
    # A real rendered Hanyu list has rowspan='data-sort-value=""'.
    return max(1, min(100, int(re.sub(r"\D", "", str(cell.get(name, "1"))) or 1)))


def grid(table):
    """Rendered cells, repeated across their rowspan/colspan (ported from the prototype)."""
    pending = {}
    for tr in table.find_all("tr"):
        if tr.find_parent("table") is not table:
            continue
        row, column = [], 0
        cells = iter(tr.find_all(["td", "th"], recursive=False))
        while True:
            if column in pending:
                cell, left = pending[column]
                row.append(cell)
                if left == 1:
                    del pending[column]
                else:
                    pending[column] = (cell, left - 1)
                column += 1
                continue
            cell = next(cells, None)
            if cell is None:
                break
            for _ in range(span(cell, "colspan")):
                row.append(cell)
                if (height := span(cell, "rowspan")) > 1:
                    pending[column] = (cell, height - 1)
                column += 1
        yield row


def segment_type(header):
    header = header.lower().replace("free skate program", "free skating").replace("free skate", "free skating")
    return next((segment for segment in SEGMENTS if segment in header), None)


def partner_of(table):
    for heading in table.find_all_previous(re.compile(r"^h[2-6]$")):
        label = text(heading)
        if re.match(r"with\s+", label, re.I):
            return re.sub(r"^with\s+", "", label, flags=re.I)
        if heading.name == "h2":
            break
    return None


def followed_notes(soup, title):
    """Eligible program-list/team pointers, excluding notes about background or individual music works."""
    for note in soup.select(".hatnote"):
        heading = note.find_previous(re.compile(r"^h[2-6]$"))
        if heading and "program" in text(heading).lower():
            links = [(a, t) for a in note.select("a[href]") if (t := link_title(a)) and t != title
                     and (re.search(r"\blist\b.*\bprogram", t, re.I) or text(note).lower().startswith("main article"))]
            if links:
                yield links


def program_evidence(body, revision):
    """Validate and retain raw program-table HTML before caching; never write biographies to disk."""
    try:
        article = json.loads(body)["parse"]
        if article["revid"] != revision:
            raise ValueError("article revision differs from the requested revision")
        title, html = article["title"], article["text"]
        if not isinstance(title, str) or not isinstance(html, str):
            raise ValueError("article title and HTML must be strings")
    except (KeyError, TypeError) as e:
        raise ValueError("invalid Wikipedia article response") from e
    soup = BeautifulSoup(html, "html.parser")
    fragments = []
    for table in soup.select("table.wikitable"):
        first = table.find("tr")
        cells = first.find_all(["th", "td"], recursive=False) if first else []
        section = table.find_previous("h2")
        in_programs = section and re.search(r"\bprograms?\b", text(section), re.I)
        recognized = cells and text(cells[0]).lower().startswith("season") and any(segment_type(text(c)) for c in cells[1:])
        if not in_programs and not recognized:
            continue
        fragments.append("<h2>Programs</h2>")
        if partner := partner_of(table):
            # Only the partnership scope is needed; unrelated headings can carry biographical information.
            scope = soup.new_tag("h3")
            scope.string = "With " + partner
            fragments.append(str(scope))
        fragments.append(str(table))
    for links in followed_notes(soup, title):
        fragments.append('<h2>Programs</h2><div class="hatnote">Main article: ' + " ".join(str(a) for a, _ in links) + "</div>")
    return json.dumps({"parse": {"title": title, "revid": revision, "text": "\n".join(fragments)}}, ensure_ascii=False).encode()


def parse(title, revision, html):
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("sup.reference, .mw-editsection, .sortkey, span[style*='display:none']"):
        node.decompose()
    rows = []
    for table in soup.select("table.wikitable"):
        headers = []
        partner = partner_of(table)
        for cells in grid(table):
            if not cells:
                continue
            labels = [text(c) for c in cells]
            if labels[0].lower().startswith("season"):
                headers = [segment_type(label) for label in labels]
                continue
            if not headers:
                continue
            season = re.match(r"((?:19|20)\d{2})\s*[–—−-]\s*(\d{2,4})", labels[0])
            if not season:
                # Older dance eras rename just one column halfway through the table.
                for i, label in enumerate(labels[:len(headers)]):
                    if segment := segment_type(label):
                        headers[i] = segment
                continue
            for header, cell in zip(headers[1:], cells[1:]):
                raw = text(cell)
                if header and raw and raw.lower() not in ("—", "–", "n/a", "none") and not re.search(
                        r"did not compete|not competing|no program", raw, re.I):
                    titles = list(dict.fromkeys(t for a in cell.select("a[href]") if (t := link_title(a))))
                    rows.append(Row(int(season[1]), header, raw, titles, partner, music_entries(cell)))
    follows = []
    # Follow only program-section main-article/see-also links, never all the music/person links in a table.
    for links in followed_notes(soup, title):
        follows += [title for _, title in links]
    return Article(title, revision, rows, list(dict.fromkeys(follows)))


def query(fetcher, endpoint, titles, prop, problems):
    """Latest metadata in MediaWiki's anonymous-client limit of 50 titles; include redirects/normalisation."""
    result = {}
    for start in range(0, len(titles), 50):
        batch = titles[start:start + 50]
        url = api_url(endpoint, action="query", titles="|".join(batch), prop=prop, rvprop="ids", redirects=1)
        body = fetcher.get(url)
        try:
            answer = json.loads(body)["query"]
            pages = {p["title"]: p for p in answer["pages"]}
            aliases = {p["from"]: p["to"] for k in ("normalized", "redirects") for p in answer.get(k, [])}
            for title in batch:
                canonical, seen = title, set()
                while canonical in aliases and canonical not in seen:
                    seen.add(canonical)
                    canonical = aliases[canonical]
                result[title] = pages.get(canonical, {})
        except (TypeError, ValueError, KeyError) as e:
            problem(problems, "parse failed", url, error=str(e))
    return result


def fetch(fetcher, endpoint, roots, problems):
    """(root title -> fetched root/list articles, title -> QID). Immutable revision URLs never relabel stale text."""
    articles, pending = {}, sorted(set(roots))
    while pending:
        metadata = query(fetcher, endpoint, pending, "revisions", problems)
        next_titles = []
        for requested, page in metadata.items():
            try:
                revision = page["revisions"][0]["revid"]
                url = api_url(endpoint, action="parse", oldid=revision, prop="text|revid")
                transform = lambda body: program_evidence(body, revision)
                body = fetcher.cached(url, transform)
                if body is None:
                    body = fetcher.get(url, transform=transform)
                parsed = json.loads(body)["parse"]
                if parsed["revid"] != revision:
                    raise ValueError("article revision differs from the requested revision")
                article = parse(parsed["title"], revision, parsed["text"])
                articles[requested] = article
                next_titles += article.follows
            except (KeyError, IndexError, TypeError, ValueError) as e:
                problem(problems, "parse failed", requested, error=str(e))
        pending = sorted(set(next_titles) - set(articles) - set(pending))
    links = sorted({t for article in articles.values() for row in article.rows for t in row.titles})
    qids = {title: p.get("pageprops", {}).get("wikibase_item")
            for title, p in query(fetcher, endpoint, links, "pageprops", problems).items()}
    reached = {}
    for root in sorted(roots):
        seen, todo, selected, complete = set(), [root], [], True
        while todo:
            title = todo.pop(0)
            if title in seen:
                continue
            if title not in articles:
                complete = False
                continue
            seen.add(title)
            article = articles[title]
            selected.append(article)
            todo.extend(article.follows)
        if selected and complete:
            reached[root] = selected
    return reached, {t: qid for t, qid in qids.items() if qid}


def apply(conn, reached, qids, problems):
    created = updated = deleted = 0
    claims = {}
    refreshed = set()
    for root, articles in reached.items():
        record = conn.execute("select entity, entity_id from keys where system = 'enwiki' and value = %s", [root]).fetchone()
        if not record or record[0] not in ("skater", "team"):
            problem(problems, "Wikipedia Skater with no ISU-ID crosswalk", root)
            continue
        entity, owner = record
        crosswalk = conn.execute("""select 1 from keys where system = 'isu' and
            ((entity = %s and entity_id = %s) or (%s = 'skater' and entity = 'team' and entity_id in
              (select id from teams where %s in (skater1_id, skater2_id)))) limit 1""",
            [entity, owner, entity, owner]).fetchone()
        if not crosswalk:
            problem(problems, "Wikipedia Skater with no ISU-ID crosswalk", root)
            continue
        if not any(article.rows for article in articles):
            problem(problems, "parse failed", root, error="no program tables")
            continue
        if entity == "team":
            programs = conn.execute("select id, season, segment_type, null::text from programs where team_id = %s", [owner]).fetchall()
        else:
            programs = conn.execute("""select p.id, p.season, p.segment_type, other.name
                from programs p left join teams t on t.id = p.team_id
                left join skaters other on other.id = case when t.skater1_id = %s then t.skater2_id else t.skater1_id end
                where p.skater_id = %s or %s in (t.skater1_id, t.skater2_id)""", [owner, owner, owner]).fetchall()
        refreshed.update(p[0] for p in programs)
        for article in articles:
            grouped = {}
            for row in article.rows:
                hits = [p for p in programs if p[1:3] == (row.season, row.segment_type)
                        and (not row.partner or (p[3] and wikidata.words(row.partner) & wikidata.words(p[3])))]
                if len(hits) != 1:
                    problem(problems, "Wikipedia row with no Program", article.title,
                            season=row.season, segment_type=row.segment_type, partner=row.partner, matches=len(hits))
                    continue
                grouped.setdefault(hits[0][0], []).append(row)
            for program, rows in grouped.items():
                raw = "\n".join(dict.fromkeys(r.raw_text for r in rows))
                title_qids = {t: qids[t] for row in rows for t in row.titles if t in qids}
                # A dedicated program list follows the summary article and supplies the fuller raw text.
                entries = list({json.dumps(e, sort_keys=True): e for row in rows for e in row.entries}.values())
                claims[program] = (raw, article.title, article.revision, title_qids, entries)
    for program in sorted(refreshed):
        if program not in claims:
            deleted += conn.execute("delete from music_claims where program_id = %s and origin = 'wikipedia'", [program]).rowcount
            continue
        raw, title, revision, title_qids, entries = claims[program]
        row = conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision, title_qids, entries)
            values (%s, 'wikipedia', %s, %s, %s, %s, %s) on conflict (program_id, origin) do update
            set raw_text = excluded.raw_text, article_title = excluded.article_title, revision = excluded.revision,
                title_qids = excluded.title_qids, entries = excluded.entries
            where (music_claims.raw_text, music_claims.article_title, music_claims.revision, music_claims.title_qids, music_claims.entries)
                is distinct from (excluded.raw_text, excluded.article_title, excluded.revision, excluded.title_qids, excluded.entries)
            returning xmax = 0""", [program, raw, title, revision, Jsonb(title_qids), Jsonb(entries)]).fetchone()
        if row:
            if row[0]:
                created += 1
            else:
                updated += 1
    return {"music_claim": {"created": created, "updated": updated, "deleted": deleted}} if created or updated or deleted else {}
