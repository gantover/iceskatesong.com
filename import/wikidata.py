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
        problems.append({"step": "wikidata", "kind": "parse failed", "key": URL.split("?")[0], "detail": {"error": str(e)}})
        return {}
    return apply(conn, items, problems)


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
