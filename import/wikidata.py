"""Wikidata step: a SPARQL extract of every item with an ISU ID (P2694), applied as keys and JA/RU name aliases.

Attaches only to Skaters and Teams the ISU results created (ADR 0001); items whose ISU IDs match nothing are ignored.
"""

import dataclasses
import json
import re
import unicodedata
from urllib.parse import urlencode

ENDPOINT = "https://query.wikidata.org/sparql"
# Without the optimizer hint Blazegraph scans the labels before the ISU-ID join.
# As one query this ran close to the endpoint's 60 s limit (#54). Split in three: keys ~6 s, each label query 6–37 s.
QUERIES = ["""SELECT ?item ?isu ?en ?title WHERE {
  hint:Query hint:optimizer "None" .
  ?item wdt:P2694 ?isu .
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title . }
}"""] + [f"""SELECT ?item ?{lang} WHERE {{
  hint:Query hint:optimizer "None" .
  ?item wdt:P2694 [] .
  OPTIONAL {{ ?item rdfs:label ?{lang} . FILTER(LANG(?{lang}) = "{lang}") }}
}}""" for lang in ("ja", "ru")]


@dataclasses.dataclass
class Item:
    qid: str
    isu_ids: list[str]
    en: str | None  # English label
    title: str | None  # English Wikipedia article: the Wikipedia step reads it from the `enwiki` key
    ja: str | None
    ru: str | None


def fetch(fetcher, endpoint: str, import_id: int, problems: list[dict]) -> list[Item] | None:
    """Every query's answer merged into Items, or None when one is missing: applying the others alone would delete the
    aliases or titles it holds. An answer that does not parse (a timed-out query still answers HTTP 200, and Wikidata's
    cache serves it again) is asked once more under a URL the cache has not seen."""
    answers = []
    for query in QUERIES:
        for attempt in (query, f"# import {import_id}\n{query}"):
            body = fetcher.get(url(endpoint, attempt), timeout=60)  # the endpoint gives up at 60 s
            if body is None:
                return None  # every try failed, and the fetcher logged it
            try:
                answers.append(bindings(body))
                break
            except Exception as e:
                error = e
        else:
            problems.append({"step": "wikidata", "kind": "parse failed", "key": ENDPOINT, "detail": {"error": str(error)}})
            return None
    return parse(answers)


def url(endpoint: str, query: str) -> str:
    return endpoint + "?" + urlencode({"query": query, "format": "json"})


def bindings(body: bytes) -> list[dict]:
    rows = json.loads(body)["results"]["bindings"]
    if not rows:  # an empty answer would delete every alias in `apply`
        raise ValueError("no items")
    return rows


def parse(answers: list[list[dict]]) -> list[Item]:
    """One Item per QID across the queries' answers: an item can carry several ISU IDs (one per partner)."""
    items: dict[str, Item] = {}
    for rows in answers:
        for row in rows:
            value = {name: binding["value"] for name, binding in row.items()}
            qid = value.pop("item").rsplit("/", 1)[-1]
            item = items.setdefault(qid, Item(qid, [], None, None, None, None))
            if (isu := value.pop("isu", None)) and isu not in item.isu_ids:
                item.isu_ids.append(isu)
            for name, label in value.items():
                setattr(item, name, label)  # the queries name their variables after Item's fields
    return list(items.values())


def apply(conn, items: list[Item], problems: list[dict]) -> dict:
    """Add missing keys and aliases. Only `enwiki` keys and `wikidata` names are this step's own, so only they move or go.

    A Wikidata QID key is never moved or removed here: the Admin may have fixed it.
    """
    created, updated = {"key": 0, "name": 0}, {"key": 0, "name": 0}
    titles, aliases = [], []
    for item in items:
        record = resolve(conn, item, problems)
        if not record:
            continue
        created["key"] += bool(conn.execute(
            """insert into keys (system, value, entity, entity_id) values ('wikidata', %s, %s, %s)
               on conflict do nothing returning 1""", [item.qid, *record]).fetchone())
        if item.title:
            titles.append(item.title)
            row = conn.execute(
                """insert into keys (system, value, entity, entity_id) values ('enwiki', %s, %s, %s)
                   on conflict (system, value) do update set entity = excluded.entity, entity_id = excluded.entity_id
                   where (keys.entity, keys.entity_id) is distinct from (excluded.entity, excluded.entity_id)
                   returning xmax = 0""", [item.title, *record]).fetchone()  # xmax = 0: inserted, not moved
            if row:
                (created if row[0] else updated)["key"] += 1
        for label in filter(None, (item.ja, item.ru)):
            aliases.append((*record, label))
            created["name"] += bool(conn.execute(
                """insert into names (entity, entity_id, name, origin) values (%s, %s, %s, 'wikidata')
                   on conflict do nothing returning 1""", [*record, label]).fetchone())
    deleted = {
        # A renamed article leaves its old title behind.
        "key": conn.execute("delete from keys where system = 'enwiki' and value <> all(%s)", [titles]).rowcount,
        # A changed label leaves the old one behind.
        "name": conn.execute("""delete from names where origin = 'wikidata' and (entity, entity_id, name) not in
                                  (select * from unnest(%s::text[], %s::bigint[], %s::text[]))""",
                             [list(column) for column in zip(*aliases)] or [[], [], []]).rowcount,
    }
    return {table: {"created": created[table], "updated": updated[table], "deleted": deleted[table]}
            for table in created if created[table] or updated[table] or deleted[table]}


def resolve(conn, item: Item, problems: list[dict]) -> tuple[str, int] | None:
    """(entity, entity_id) of the Skater this item is, or of the Team when the item names both partners.

    Wikidata puts a pair's or couple's Team ID on each partner's own item, so a Team ID resolves to the member whose
    names best match the item's English label and article title; a tie (both partners named) is the Team.
    Only the words one partner doesn't share with the other count, so a shared surname alone names no one.
    """
    hits = conn.execute("select entity, entity_id from keys where system = 'isu' and value = any(%s) order by entity_id",
                        [item.isu_ids]).fetchall()
    skaters = sorted({entity_id for entity, entity_id in hits if entity == "skater"})
    if len(skaters) > 1:  # one person, several Skaters: a duplicate for the Admin to merge
        problems.append({"step": "wikidata", "kind": "Wikidata item matches several Skaters", "key": item.qid,
                         "detail": {"label": item.en or item.title, "skaters": skaters}})
        return None
    if skaters:
        return "skater", skaters[0]
    teams = [entity_id for entity, entity_id in hits if entity == "team"]
    if not teams:
        return None  # matches nothing: ignored
    label = words(f"{item.en or ''} {item.title or ''}")
    members = set()
    for team_id in teams:
        names: dict[int, set[str]] = {}
        for skater_id, name in conn.execute(
                """select n.entity_id, n.name from teams t join names n on n.entity = 'skater'
                   and n.entity_id in (t.skater1_id, t.skater2_id) where t.id = %s""", [team_id]):
            names.setdefault(skater_id, set()).update(words(name))
        scores = {skater_id: len((own - set().union(*(w for s, w in names.items() if s != skater_id))) & label)
                  for skater_id, own in names.items()}
        best = max(scores.values(), default=0)
        if not best:
            continue
        winners = [skater_id for skater_id, score in scores.items() if score == best]
        if len(winners) == 2:
            return "team", team_id
        members.add(winners[0])
    if len(members) == 1:
        return "skater", members.pop()
    problems.append({"step": "wikidata", "kind": "Wikidata item with no Team member match", "key": item.qid,
                     "detail": {"label": item.en or item.title, "teams": teams, "members": sorted(members)}})
    return None


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()))
