"""The Corrections file (ADR 0002, R1): validated before the fetch, replayed on every Import.

Every Import first reverts the previous replay (the undo journal, then every row of origin `corrections`), so the
ISU, Wikidata and Wikipedia steps see the imported state, and then replays the whole file: deleting a line undoes it.
"""

import pathlib
import re

import yaml
from psycopg.types.json import Jsonb

import normalise

DISCIPLINES = ("men", "women", "pairs", "ice dance")
LEVELS = ("senior", "junior")
SEGMENT_TYPES = ("short program", "free skating", "short dance", "rhythm dance", "free dance", "original dance",
                 "compulsory dance")


class Invalid(Exception):
    pass


class Loader(yaml.SafeLoader):
    """PyYAML keeps the last of two equal keys; a fix silently dropped that way would be lost."""


def _mapping(loader, node):
    keys = [loader.construct_object(key) for key, _ in node.value]
    for key in keys:
        if keys.count(key) > 1:
            raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", node.start_mark)
    return loader.construct_mapping(node)


Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load(path: pathlib.Path) -> dict:
    """The file's four sections, checked for shape only: keys that match no record are logged by the apply phase."""
    try:
        data = yaml.load(path.read_text(), Loader) or {}
    except (OSError, yaml.YAMLError) as e:
        raise Invalid(str(e)) from e
    if not isinstance(data, dict):
        raise Invalid("expected the sections piece_aliases, program_music, skater_merges, video_hides")
    for section in data:
        if section not in ("piece_aliases", "program_music", "skater_merges", "video_hides"):
            raise Invalid(f"unknown section {section!r}")
    fixes = {"piece_aliases": data.get("piece_aliases") or [], "skater_merges": data.get("skater_merges") or {},
             "program_music": data.get("program_music") or [], "video_hides": data.get("video_hides") or []}

    raws = set()
    for i, line in enumerate(listed("piece_aliases", fixes["piece_aliases"])):
        where = f"piece_aliases[{i}]"
        fields(where, line, ("raw", "piece"), ("title", "artists", "source", "genres"))
        text(f"{where}.raw", line["raw"])
        text(f"{where}.piece", line["piece"])
        if line["raw"] in raws:
            raise Invalid(f"{where}.raw: listed twice")
        raws.add(line["raw"])
        if "title" in line:
            text(f"{where}.title", line["title"])
            for name in ("artists", "genres"):
                for j, value in enumerate(listed(f"{where}.{name}", line.get(name, []))):
                    text(f"{where}.{name}[{j}]", value)
            if line.get("source") is not None:
                text(f"{where}.source", line["source"])
        elif line.keys() - {"raw", "piece"}:
            raise Invalid(f"{where}: artists, source and genres need a title (a new Piece)")

    merges = fixes["skater_merges"]
    if not isinstance(merges, dict):
        raise Invalid("skater_merges: expected duplicate slug: survivor slug lines")
    for duplicate, survivor in merges.items():
        text("skater_merges key", duplicate)
        text(f"skater_merges.{duplicate}", survivor)
        if duplicate == survivor:
            raise Invalid(f"skater_merges: {duplicate} is merged into itself")
        if survivor in merges:
            raise Invalid(f"skater_merges: {survivor} is merged away and also a survivor")

    programs = []
    for i, line in enumerate(listed("program_music", fixes["program_music"])):
        where = f"program_music[{i}]"
        fields(where, line, ("program", "music"))
        program = program_key(f"{where}.program", line["program"])
        if program in programs:
            raise Invalid(f"{where}.program: listed twice")
        programs.append(program)
        for j, arrangement in enumerate(listed(f"{where}.music", line["music"], non_empty=True)):
            fields(f"{where}.music[{j}]", arrangement, ("piece",), ("style", "performer"))
            for name in arrangement:
                text(f"{where}.music[{j}].{name}", arrangement[name])

    for i, line in enumerate(listed("video_hides", fixes["video_hides"])):
        where = f"video_hides[{i}]"
        fields(where, line, ("youtube", "performance"))
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", text(f"{where}.youtube", line["youtube"])):
            raise Invalid(f"{where}.youtube: expected an 11-character YouTube ID")
        performance = fields(f"{where}.performance", line["performance"],
                             ("competition", "discipline", "segment_type", "entry"), ("level", "round"))
        for name in performance:
            text(f"{where}.performance.{name}", performance[name], empty=name == "round")
        one_of(f"{where}.performance.discipline", performance["discipline"], DISCIPLINES)
        one_of(f"{where}.performance.segment_type", performance["segment_type"], SEGMENT_TYPES)
        if "level" in performance:
            one_of(f"{where}.performance.level", performance["level"], LEVELS)
    return fixes


def program_key(where: str, program) -> tuple:
    fields(where, program, ("season", "segment_type"), ("skater", "team", "seq"))
    if ("skater" in program) == ("team" in program):
        raise Invalid(f"{where}: name exactly one of skater or team")
    owner = "skater" if "skater" in program else "team"
    text(f"{where}.{owner}", program[owner])
    one_of(f"{where}.segment_type", program["segment_type"], SEGMENT_TYPES)
    for name, minimum in (("season", 1900), ("seq", 1)):
        value = program.get(name, 1)
        if type(value) is not int or value < minimum:
            raise Invalid(f"{where}.{name}: expected a whole number from {minimum}, YAML read {value!r}")
    return owner, program[owner], program["season"], program["segment_type"], program.get("seq", 1)


def listed(where: str, value, non_empty=False) -> list:
    if not isinstance(value, list) or (non_empty and not value):
        raise Invalid(f"{where}: expected a {'non-empty ' if non_empty else ''}list")
    return value


def fields(where: str, value, required: tuple, optional=()) -> dict:
    if not isinstance(value, dict):
        raise Invalid(f"{where}: expected a mapping with {', '.join(required)}")
    for name in value:
        if name not in required + optional:
            raise Invalid(f"{where}: unknown field {name!r}")
    for name in required:
        if name not in value:
            raise Invalid(f"{where}: missing {name}")
    return value


def text(where: str, value, empty=False) -> str:
    # YAML 1.1 reads yes/no as booleans and 00013665 as an octal number: such values must be quoted.
    if not isinstance(value, str):
        raise Invalid(f"{where}: quote it, YAML read {value!r} as {type(value).__name__}")
    if not (value.strip() or empty):
        raise Invalid(f"{where}: must not be empty")
    return value


def one_of(where: str, value: str, choices: tuple) -> None:
    if value not in choices:
        raise Invalid(f"{where}: expected one of {', '.join(choices)}")


def problem(problems: list[dict], where: str, line, kind="corrections line with an unknown key") -> None:
    problems.append({"step": "corrections", "kind": kind, "key": where, "detail": {"line": line}})


def undo(conn, statement: str, *params) -> None:
    conn.execute("insert into corrections_undo (statement, params) values (%s, %s)", [statement, Jsonb(list(params))])


def revert(conn) -> None:
    """Put back the imported state: run the undo journal backwards and drop every row of origin `corrections`."""
    for statement, params in conn.execute("select statement, params from corrections_undo order by id desc").fetchall():
        conn.execute(statement, params)
    conn.execute("delete from corrections_undo")
    for table in ("music_claims", "names", "piece_artists", "piece_genres"):
        conn.execute(f"delete from {table} where origin = 'corrections'")


def apply(conn, fixes: dict, problems: list[dict]) -> None:
    """Replayed last, after every imported row exists: merges first, so later keys may name a merged-away slug."""
    for duplicate, survivor in fixes["skater_merges"].items():
        ids = [slug_owner(conn, "skater", slug) for slug in (duplicate, survivor)]
        if not all(ids):
            problem(problems, f"skater_merges.{duplicate}", {duplicate: survivor})
            continue
        merge(conn, *ids)

    writer = normalise.Writer(conn, {}, origin="corrections")
    aliases = {}
    for i, line in enumerate(fixes["piece_aliases"]):
        piece = slug_owner(conn, "piece", line["piece"])
        if "title" in line and not piece:
            if conn.execute("select 1 from keys where system = 'slug' and value = %s", [line["piece"]]).fetchone():
                problem(problems, f"piece_aliases[{i}].piece", line, kind="corrections slug taken by another record")
                continue
            piece = conn.execute("insert into pieces (title) values (%s) returning id", [line["title"]]).fetchone()[0]
            writer.records.key("slug", line["piece"], "piece", piece)
        if not piece:
            problem(problems, f"piece_aliases[{i}].piece", line)
            continue
        if "title" in line:  # the line defines the Piece
            source = line.get("source") and writer.record("source", line["source"])
            old = conn.execute("""update pieces p set title = %s, source_id = coalesce(%s, p.source_id) from pieces old
                                  where p.id = %s and old.id = p.id returning old.title, old.source_id""",
                               [line["title"], source, piece]).fetchone()
            undo(conn, "update pieces set title = %s, source_id = %s where id = %s", *old, piece)
            for name in line.get("artists", []):
                conn.execute("insert into piece_artists values (%s, %s, 'corrections') on conflict do nothing",
                             [piece, writer.record("artist", name)])
            for genre in line.get("genres", []):
                conn.execute("insert into piece_genres values (%s, %s, 'corrections') on conflict do nothing",
                             [piece, writer.lookup("genres", genre)])
        writer.name("piece", piece, line["raw"])
        aliases[line["raw"]] = piece

    for i, line in enumerate(fixes["program_music"]):
        owner, slug, season, segment_type, seq = program_key("", line["program"])
        program = conn.execute(f"""select pr.id from programs pr join keys k on k.system = 'slug' and k.entity = %s
            and k.value = %s and k.entity_id = pr.{owner}_id where pr.season = %s and pr.segment_type = %s and pr.seq = %s""",
            [owner, slug, season, segment_type, seq]).fetchone()
        if not program:
            problem(problems, f"program_music[{i}].program", line)
            continue
        pieces = [slug_owner(conn, "piece", arrangement["piece"]) for arrangement in line["music"]]
        if None in pieces:
            problem(problems, f"program_music[{i}].music[{pieces.index(None)}].piece", line)
            continue
        titles = [conn.execute("select title from pieces where id = %s", [piece]).fetchone()[0] for piece in pieces]
        if not conn.execute("""insert into music_claims (program_id, origin, raw_text) values (%s, 'corrections', %s)
                               on conflict do nothing returning 1""", [program[0], "\n".join(titles)]).fetchone():
            problem(problems, f"program_music[{i}].program", line, kind="corrections line repeats a Program")
            continue
        for position, (arrangement, piece, title) in enumerate(zip(line["music"], pieces, titles)):
            conn.execute("""insert into music_occurrences (program_id, origin, position, arrangement_id, grade, raw_text)
                            values (%s, 'corrections', %s, %s, %s, %s)""",
                         [program[0], position, writer.arrangement(piece, arrangement.get("style", "original"),
                                                                   arrangement.get("performer")),
                          normalise.piece_grade(conn, piece), title])

    # An aliased Wikipedia entry gets its own claim: Wikipedia's text, attribution and occurrences with the aliased
    # entries repointed. The Wikipedia rows stay as imported, so deleting the line restores them exactly.
    for program, raw, entries, qids, article, revision in conn.execute("""select program_id, raw_text, entries, title_qids,
            article_title, revision from music_claims c where origin = 'wikipedia' and not exists (select from music_claims o
              where o.program_id = c.program_id and o.origin in ('admin', 'corrections', 'submitted'))""").fetchall():
        entries = [entry["raw"] for entry in normalise.claim_entries(raw, entries, qids)]
        if not aliases.keys() & set(entries):
            continue
        conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
                        values (%s, 'corrections', %s, %s, %s)""", [program, raw, article, revision])
        imported = conn.execute("""select arrangement_id, grade, raw_text from music_occurrences
            where program_id = %s and origin = 'wikipedia' order by position""", [program]).fetchall()
        position = 0
        for entry in entries:
            found = []
            while imported and imported[0][2] == entry:
                found.append(imported.pop(0))
            if entry in aliases:
                found = [(writer.arrangement(aliases[entry], "original", None), normalise.piece_grade(conn, aliases[entry]), entry)]
            for arrangement, grade, text in found:
                conn.execute("""insert into music_occurrences (program_id, origin, position, arrangement_id, grade, raw_text)
                                values (%s, 'corrections', %s, %s, %s, %s)""", [program, position, arrangement, grade, text])
                position += 1

    for i, line in enumerate(fixes["video_hides"]):
        key = line["performance"]
        performance = conn.execute("""select p.id from performances p join segments s on s.id = p.segment_id
            join competitions c on c.id = s.competition_id
            join keys k on k.system = 'slug' and k.entity = 'competition' and k.entity_id = c.id
            where k.value = %s and s.discipline = %s and s.level = coalesce(%s, c.level) and s.segment_type = %s
              and s.round = %s and p.entry_key = %s""",
            [key["competition"], key["discipline"], key.get("level"), key["segment_type"], key.get("round", ""), key["entry"]]).fetchone()
        links = performance and conn.execute("select id, status from performance_videos where youtube_id = %s and performance_id = %s",
                                             [line["youtube"], performance[0]]).fetchall()
        if not links:
            problem(problems, f"video_hides[{i}]", line)
            continue
        hidden = [id for id, status in links if status == "active"]
        conn.execute("update performance_videos set status = 'hidden' where id = any(%s)", [hidden])
        undo(conn, "update performance_videos set status = 'active' where id = any(%s)", hidden)


def slug_owner(conn, entity: str, slug: str) -> int | None:
    row = conn.execute("select entity_id from keys where system = 'slug' and entity = %s and value = %s", [entity, slug]).fetchone()
    return row and row[0]


def merge(conn, duplicate: int, survivor: int) -> None:
    """Move the duplicate Skater's keys, names, Team places, Programs and Performances to the survivor (ADR 0002).
    The emptied duplicate row stays, so the journal can put everything back with plain updates."""
    for system, value in conn.execute("""update keys set entity_id = %s where entity = 'skater' and entity_id = %s
                                         returning system, value""", [survivor, duplicate]).fetchall():
        undo(conn, "update keys set entity_id = %s where system = %s and value = %s", duplicate, system, value)
    for name, origin in conn.execute("""insert into names (entity, entity_id, name, origin)
            select entity, %s, name, origin from names where entity = 'skater' and entity_id = %s
            on conflict do nothing returning name, origin""", [survivor, duplicate]).fetchall():
        undo(conn, "delete from names where entity = 'skater' and entity_id = %s and name = %s and origin = %s", survivor, name, origin)
    for name, origin in conn.execute("delete from names where entity = 'skater' and entity_id = %s returning name, origin",
                                     [duplicate]).fetchall():
        undo(conn, "insert into names (entity, entity_id, name, origin) values ('skater', %s, %s, %s)", duplicate, name, origin)
    for column in ("skater1_id", "skater2_id"):
        teams = ids(conn, f"update teams set {column} = %s where {column} = %s returning id", survivor, duplicate)
        undo(conn, f"update teams set {column} = %s where id = any(%s)", duplicate, teams)

    for program, season, segment_type, seq in conn.execute(
            "select id, season, segment_type, seq from programs where skater_id = %s", [duplicate]).fetchall():
        same = conn.execute("select id from programs where skater_id = %s and season = %s and segment_type = %s and seq = %s",
                            [survivor, season, segment_type, seq]).fetchone()
        if not same:
            conn.execute("update programs set skater_id = %s where id = %s", [survivor, program])
            undo(conn, "update programs set skater_id = %s where id = %s", duplicate, program)
            continue
        # Programs with the same key merge: Performances move, and music claims of an origin the survivor lacks.
        moved = ids(conn, "update performances set program_id = %s where program_id = %s returning id", same[0], program)
        undo(conn, "update performances set program_id = %s where id = any(%s)", program, moved)
        origins = [origin for (origin,) in conn.execute("""update music_claims set program_id = %s where program_id = %s
            and origin not in (select origin from music_claims where program_id = %s) returning origin""",
            [same[0], program, same[0]])]
        undo(conn, "update music_claims set program_id = %s where program_id = %s and origin = any(%s)", program, same[0], origins)

    moved = ids(conn, "update performances set skater_id = %s where skater_id = %s returning id", survivor, duplicate)
    undo(conn, "update performances set skater_id = %s where id = any(%s)", duplicate, moved)


def ids(conn, statement: str, *params) -> list[int]:
    return [id for (id,) in conn.execute(statement, params)]
