"""Wikidata step: one SPARQL extract of every item with an ISU ID (P2694), applied as keys and JA/RU name aliases.

Attaches only to Skaters and Teams the ISU results created (ADR 0001); items whose ISU IDs match nothing are ignored.
"""

import dataclasses
import json
import re
import unicodedata
from urllib.parse import urlencode

# Without the optimizer hint Blazegraph scans the labels before the ISU-ID join: ~35 s instead of ~15 s.
QUERY = """SELECT ?item ?isu ?en ?title ?ja ?ru WHERE {
  hint:Query hint:optimizer "None" .
  ?item wdt:P2694 ?isu .
  OPTIONAL { ?item rdfs:label ?en . FILTER(LANG(?en) = "en") }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> ; schema:name ?title . }
  OPTIONAL { ?item rdfs:label ?ja . FILTER(LANG(?ja) = "ja") }
  OPTIONAL { ?item rdfs:label ?ru . FILTER(LANG(?ru) = "ru") }
}"""
URL = "https://query.wikidata.org/sparql?" + urlencode({"query": QUERY, "format": "json"})


@dataclasses.dataclass
class Item:
    qid: str
    isu_ids: list[str]
    en: str | None  # English label
    title: str | None  # English Wikipedia article: the Wikipedia step reads it from the `enwiki` key
    ja: str | None
    ru: str | None


def parse(body: bytes) -> list[Item]:
    """One Item per QID: an item can carry several ISU IDs (one per partner)."""
    items: dict[str, Item] = {}
    for row in json.loads(body)["results"]["bindings"]:
        value = {name: binding["value"] for name, binding in row.items()}
        qid = value["item"].rsplit("/", 1)[-1]
        item = items.setdefault(qid, Item(qid, [], value.get("en"), value.get("title"), value.get("ja"), value.get("ru")))
        item.isu_ids.append(value["isu"])
    if not items:  # an empty answer would delete every alias below
        raise ValueError("no items")
    return list(items.values())


def run(conn, body: bytes | None, problems: list[dict]) -> dict:
    if body is None:
        return {}  # never fetched: the fetch phase logged it
    try:
        items = parse(body)
    except Exception as e:
        problems.append({"step": "wikidata", "kind": "parse failed", "key": URL.split("?")[0], "detail": {"error": repr(e)}})
        return {}
    return apply(conn, items)


def apply(conn, items: list[Item]) -> dict:
    """Insert missing keys and aliases; remove only the `enwiki` keys and `wikidata` names this step no longer yields."""
    created = {"key": 0, "name": 0}
    titles, names = [], []
    for item in items:
        found = resolve(conn, item)
        if not found:
            continue
        rows = [("wikidata", item.qid)] + ([("enwiki", item.title)] if item.title else [])
        for system, value in rows:
            created["key"] += bool(conn.execute(
                """insert into keys (system, value, entity, entity_id) values (%s, %s, %s, %s)
                   on conflict do nothing returning 1""", [system, value, *found]).fetchone())
        titles += [item.title] if item.title else []
        for label in filter(None, (item.ja, item.ru)):
            names.append((*found, label))
            created["name"] += bool(conn.execute(
                """insert into names (entity, entity_id, name, origin) values (%s, %s, %s, 'wikidata')
                   on conflict do nothing returning 1""", [*found, label]).fetchone())
    deleted = {
        # A renamed article leaves its old title behind.
        "key": conn.execute("delete from keys where system = 'enwiki' and value <> all(%s)", [titles]).rowcount,
        # A changed label leaves the old one behind.
        "name": conn.execute("""delete from names where origin = 'wikidata' and (entity, entity_id, name) not in
                                  (select * from unnest(%s::text[], %s::bigint[], %s::text[]))""",
                             [list(column) for column in zip(*names)] or [[], [], []]).rowcount,
    }
    return {entity: {"created": created[entity], "deleted": deleted[entity]}
            for entity in created if created[entity] or deleted[entity]}


def resolve(conn, item: Item) -> tuple[str, int] | None:
    """The Skater this item is, or the Team when the item is the duo itself.

    Wikidata puts a pair's or couple's Team ID on each partner's own item, so a Team ID resolves to the member whose
    names best match the item's English label and article title; a tie (both partners named) is the Team.
    """
    hits = conn.execute("select entity, entity_id from keys where system = 'isu' and value = any(%s) order by entity_id",
                        [item.isu_ids]).fetchall()
    skaters = {entity_id for entity, entity_id in hits if entity == "skater"}
    if skaters:
        return "skater", min(skaters)
    label = words(f"{item.en or ''} {item.title or ''}")
    members = set()
    for team_id in (entity_id for entity, entity_id in hits if entity == "team"):
        scores = {}
        for skater_id, name in conn.execute(
                """select n.entity_id, n.name from teams t join names n on n.entity = 'skater'
                   and n.entity_id in (t.skater1_id, t.skater2_id) where t.id = %s""", [team_id]):
            scores[skater_id] = max(scores.get(skater_id, 0), len(words(name) & label))
        best = max(scores.values(), default=0)
        if not best:
            continue
        winners = [skater_id for skater_id, score in scores.items() if score == best]
        if len(winners) == 2:
            return "team", team_id
        members.add(winners[0])
    return ("skater", members.pop()) if len(members) == 1 else None


def words(text: str) -> set[str]:
    return set(re.findall(r"\w+", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()))
