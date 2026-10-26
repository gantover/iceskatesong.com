"""The Corrections file (issue #36): validated before the fetch, replayed on every Import, undone by deleting a line."""

import pathlib
import re

import pytest

import corrections
import main
from test_import import GPF

ROOT = pathlib.Path(__file__).parents[2]


def run_import(conn, site, tmp_path, fixes: str, events=(GPF,)):
    events_file = tmp_path / "events.txt"
    events_file.write_text("".join(f"{site.url}/{e}\n" for e in events))
    corrections_file = tmp_path / "corrections.yaml"
    corrections_file.write_text(fixes)
    conn.execute("insert into imports default values")
    import_id = main.claim(conn)
    site.log.clear()
    main.run(conn, import_id, events_file, tmp_path / "cache", "test@example.com", interval=0, corrections_file=corrections_file)
    return conn.execute("select status, error from imports where id = %s", [import_id]).fetchone()


def unknown_keys(conn):
    return [key for (key,) in conn.execute(
        """select key from import_problems where kind = 'corrections line with an unknown key'
           and import_id = (select max(id) from imports) order by id""")]


@pytest.mark.parametrize("fixes, message", [
    ("skater_merges: [", "corrections.yaml"),
    ("pieces: []\n", "unknown section 'pieces'"),
    ("video_hides:\n  - youtube: abcdefghijk\n    performance: {competition: gpf2025, discipline: men,"
     " segment_type: free skating, entry: 00013665}\n", "video_hides[0].performance.entry: quote it"),
    ("skater_merges:\n  a: b\n  a: c\n", "duplicate key 'a'"),
    ("skater_merges:\n  a: b\n  b: c\n", "skater_merges: b is merged away and also a survivor"),
    ("piece_aliases:\n  - {raw: a, piece: x, title: X}\n  - {raw: b, piece: x, title: Y}\n", "piece_aliases[1].piece: defined twice"),
])
def test_an_invalid_file_fails_the_import_before_any_fetch(conn, site, tmp_path, fixes, message):
    status, error = run_import(conn, site, tmp_path, fixes)

    assert status == "failed"
    assert error.startswith("corrections.yaml") and message in error, error
    assert site.log == []


def test_the_committed_file_is_valid(tmp_path):
    # Its examples are comments: a broken committed file would fail every Import.
    assert not any(corrections.load(ROOT / "corrections.yaml").values())
    examples = tmp_path / "examples.yaml"
    examples.write_text(re.sub(r"(?m)^  # ", "  ", (ROOT / "corrections.yaml").read_text()))
    assert all(corrections.load(examples).values())


MALININ_FREE = """select id from performances where entry_key = '00108049' and segment_id =
    (select id from segments where segment_type = 'free skating' and discipline = 'men' and level = 'senior')"""
HIDE = """video_hides:
  - youtube: abcdefghijk
    performance: {competition: gpf2025, discipline: men, segment_type: free skating, entry: "00108049"}
  - youtube: abcdefghijk
    performance: {competition: gpf2025, discipline: men, level: junior, segment_type: free skating, entry: "00108049"}
"""


def test_a_video_hide_survives_reimports_until_its_line_is_deleted(conn, site, tmp_path):
    run_import(conn, site, tmp_path, "")
    for start in (0, 3600):
        conn.execute(f"""insert into performance_videos (youtube_id, start_seconds, performance_id, origin)
                         values ('abcdefghijk', %s, ({MALININ_FREE}), 'official')""", [start])
    videos = "select status from performance_videos order by start_seconds"
    run_import(conn, site, tmp_path, "")
    imported = contents(conn)

    assert run_import(conn, site, tmp_path, HIDE) == ("succeeded", None)
    assert conn.execute(videos).fetchall() == [("hidden",), ("hidden",)]
    # Malinin skated no junior free skating at this Final.
    assert unknown_keys(conn) == ["video_hides[1]"]

    run_import(conn, site, tmp_path, HIDE)
    assert conn.execute(videos).fetchall() == [("hidden",), ("hidden",)]

    run_import(conn, site, tmp_path, "video_hides: []\n")
    assert conn.execute(videos).fetchall() == [("active",), ("active",)]
    assert contents(conn) == imported


def contents(conn):
    """Every row a replay may touch, without xmin: a replay rewrites the rows it reverted."""
    tables = ["keys", "names", "skaters", "teams", "programs", "performances", "music_claims", "music_occurrences",
              "performance_videos", "pieces", "piece_artists", "piece_genres", "artists", "sources", "genres", "styles",
              "arrangements"]
    return {t: conn.execute(f"select array_agg(t::text order by t::text) from {t} t").fetchone()[0] for t in tables}


def row_counts(conn):
    return {table: len(rows or []) for table, rows in contents(conn).items()}


def slug_owner(conn, slug):
    return conn.execute("select entity_id from keys where system = 'slug' and value = %s", [slug]).fetchone()[0]


def test_a_skater_merge_moves_keys_names_and_programs_until_its_line_is_deleted(conn, site, tmp_path):
    # The free skating page prints Malinin under a second ISU ID and spelling: a duplicate Skater, ilya-malinin.
    free = site.root / "results/season2526/gpf2025/SEG002.htm"
    free.write_text(free.read_text().replace("isufs00108049", "isufs00999999").replace("Ilia MALININ", "Ilya MALININ"))
    run_import(conn, site, tmp_path, "")
    survivor, duplicate = slug_owner(conn, "ilia-malinin"), slug_owner(conn, "ilya-malinin")
    assert survivor != duplicate
    # The survivor also has a free skating Program; both have Wikipedia music, the duplicate's also a Submission's.
    duplicate_free = conn.execute("select program_id from performances where entry_key = '00999999'").fetchone()[0]
    survivor_free = conn.execute("""insert into programs (skater_id, season, segment_type) values (%s, 2025, 'free skating')
                                    returning id""", [survivor]).fetchone()[0]
    for program, origin, raw in ((survivor_free, "wikipedia", "Survivor music"), (duplicate_free, "wikipedia", "Duplicate music"),
                                 (duplicate_free, "submitted", "Submitted music")):
        conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
                        values (%s, %s, %s, 'Ilia Malinin', 1)""", [program, origin, raw])
    run_import(conn, site, tmp_path, "")
    imported = contents(conn)
    merge = "skater_merges:\n  ilya-malinin: ilia-malinin\n  nobody: ilia-malinin\n"

    assert run_import(conn, site, tmp_path, merge) == ("succeeded", None)
    assert unknown_keys(conn) == ["skater_merges.nobody"]
    merged = contents(conn)
    assert slug_owner(conn, "ilya-malinin") == survivor
    assert conn.execute("select entity_id from keys where system = 'isu' and value = '00999999'").fetchone() == (survivor,)
    assert conn.execute("select distinct skater_id from performances where name like 'Il_a MALININ'").fetchall() == [(survivor,)]
    assert conn.execute("select program_id from performances where entry_key = '00999999'").fetchone() == (survivor_free,)
    assert conn.execute("select name from names where entity = 'skater' and entity_id = %s order by name", [survivor]).fetchall() == [
        ("Ilia MALININ",), ("Ilya MALININ",)]
    # The survivor keeps its own Wikipedia music; the Submission's moves over.
    assert conn.execute("select origin, raw_text from music_claims where program_id = %s order by origin", [survivor_free]).fetchall() == [
        ("submitted", "Submitted music"), ("wikipedia", "Survivor music")]

    run_import(conn, site, tmp_path, merge)
    assert contents(conn) == merged

    run_import(conn, site, tmp_path, "skater_merges:\n")
    assert contents(conn) == imported


def malinin_program(conn, segment_type):
    return conn.execute("""select distinct p.program_id from performances p join programs pr on pr.id = p.program_id
                           where p.entry_key = '00108049' and pr.segment_type = %s""", [segment_type]).fetchone()[0]


def occurrences(conn, program, origin):
    return conn.execute("""select p.title, s.slug, a.name, o.grade from music_occurrences o
        join arrangements ar on ar.id = o.arrangement_id join pieces p on p.id = ar.piece_id
        join styles s on s.id = ar.style_id left join artists a on a.id = ar.performer_id
        where o.program_id = %s and o.origin = %s order by o.position""", [program, origin]).fetchall()


PROGRAM_MUSIC = """program_music:
  - program: {skater: ilia-malinin, season: 2025, segment_type: short program}
    music:
      - piece: prelude
        style: piano
        performer: Composer
      - piece: tango
      - piece: bolero
  - program: {skater: ilia-malinin, season: 2025, segment_type: free skating, seq: 2}
    music: [{piece: tango}]
  - program: {skater: ilia-malinin, season: 2025, segment_type: free skating}
    music: [{piece: tango}, {piece: no-such-piece}]
"""


def test_program_music_sets_ordered_arrangements_graded_by_the_picked_pieces(conn, site, tmp_path):
    run_import(conn, site, tmp_path, "")
    free, short = malinin_program(conn, "free skating"), malinin_program(conn, "short program")
    conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
                    values (%s, 'wikipedia', 'Tango\nPrelude by Composer', 'Ilia Malinin', 1)""", [free])
    bolero = conn.execute("insert into pieces (title) values ('Bolero') returning id").fetchone()[0]
    conn.execute("insert into keys values ('slug', 'bolero', 'piece', %s), ('wikidata', 'Q1', 'piece', %s)", [bolero, bolero])
    run_import(conn, site, tmp_path, "")
    imported = contents(conn)

    assert run_import(conn, site, tmp_path, PROGRAM_MUSIC) == ("succeeded", None)
    # A bare title stays title only; a Piece with a composer is credited; one with a Wikidata item identified.
    assert occurrences(conn, short, "corrections") == [
        ("Prelude", "piano", "Composer", "credited"), ("Tango", "original", None, "title only"), ("Bolero", "original", None, "identified")]
    assert conn.execute("select raw_text from music_claims where program_id = %s", [short]).fetchone() == ("Prelude\nTango\nBolero",)
    # An unknown Piece drops the whole line: a partial ordered list would be wrong.
    assert unknown_keys(conn) == ["program_music[1].program", "program_music[2].music[1].piece"]
    assert occurrences(conn, free, "corrections") == []
    with_music = occurrences(conn, short, "corrections"), row_counts(conn)

    # A replay recreates what it created, under new ids, and piles nothing up.
    run_import(conn, site, tmp_path, PROGRAM_MUSIC)
    assert (occurrences(conn, short, "corrections"), row_counts(conn)) == with_music

    run_import(conn, site, tmp_path, "")
    assert contents(conn) == imported


ALIASES = """piece_aliases:
  - raw: Tango
    piece: bolero
  - raw: He is a Pirate from Pirates
    piece: he-s-a-pirate
    title: He's a Pirate
    artists: [Klaus Badelt]
    source: Pirates of the Caribbean
    genres: [film]
  - raw: Prelude by Composer
    piece: no-such-piece
  - raw: Malinin's Prelude
    piece: ilia-malinin
    title: Prelude
  - raw: Ravel's Bolero
    piece: bolero
    title: Boléro
    source: Ballets
"""


def test_piece_aliases_repoint_wikipedia_entries_until_their_line_is_deleted(conn, site, tmp_path):
    run_import(conn, site, tmp_path, "")
    free = malinin_program(conn, "free skating")
    conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
                    values (%s, 'wikipedia', 'Tango\nHe is a Pirate from Pirates\nPrelude by Composer', 'Ilia Malinin', 7)""", [free])
    bolero = conn.execute("insert into pieces (title) values ('Bolero') returning id").fetchone()[0]
    conn.execute("insert into keys values ('slug', 'bolero', 'piece', %s)", [bolero])
    run_import(conn, site, tmp_path, "")
    imported, wikipedia = contents(conn), occurrences(conn, free, "wikipedia")
    assert [title for title, *_ in wikipedia] == ["Tango", "He is a Pirate", "Prelude"]

    def assert_aliased():
        # A corrections claim carries Wikipedia's text and attribution; aliased entries are graded by their Piece.
        assert occurrences(conn, free, "corrections") == [
            ("Bolero", "original", None, "title only"), ("He's a Pirate", "original", None, "credited"), wikipedia[2]]
        assert conn.execute("select raw_text, article_title, revision from music_claims where origin = 'corrections'").fetchall() == [
            ("Tango\nHe is a Pirate from Pirates\nPrelude by Composer", "Ilia Malinin", 7)]
        assert occurrences(conn, free, "wikipedia") == wikipedia
        assert conn.execute("""select s.name, array(select a.name from piece_artists pa join artists a on a.id = pa.artist_id
                                                     where pa.piece_id = p.id), array(select g.slug from piece_genres pg
                                                     join genres g on g.id = pg.genre_id where pg.piece_id = p.id)
                               from pieces p join sources s on s.id = p.source_id where p.title = %s""", ["He's a Pirate"]).fetchall() == [
            ("Pirates of the Caribbean", ["Klaus Badelt"], ["film"])]
        # Only new Pieces are defined inline: an imported Piece keeps its title and Source, and still takes the alias.
        assert conn.execute("select name from names where entity = 'piece' and entity_id = %s order by name", [bolero]).fetchall() == [
            ("Ravel's Bolero",), ("Tango",)]
        assert conn.execute("select title, source_id from pieces where id = %s", [bolero]).fetchone() == ("Bolero", None)
        assert unknown_keys(conn) == ["piece_aliases[2].piece"]
        assert conn.execute("select key from import_problems where kind = 'corrections slug taken by another record'"
                            " and import_id = (select max(id) from imports) order by id").fetchall() == [
            ("piece_aliases[3].piece",), ("piece_aliases[4].piece",)]

    assert run_import(conn, site, tmp_path, ALIASES) == ("succeeded", None)
    assert_aliased()
    with_aliases = row_counts(conn)

    # A replay recreates what it created, under new ids, and piles nothing up.
    run_import(conn, site, tmp_path, ALIASES)
    assert_aliased()
    assert row_counts(conn) == with_aliases

    # Deleting the lines removes the Piece, Artist, Source and Genre they created, with their slugs.
    run_import(conn, site, tmp_path, "")
    assert contents(conn) == imported


def test_a_defined_piece_yields_its_slug_to_the_imported_piece(conn, site, tmp_path):
    run_import(conn, site, tmp_path, "")
    define = """piece_aliases:
  - raw: Pirates
    piece: he-s-a-pirate
    title: He's a Pirate!
    source: Pirates of the Caribbean
"""
    run_import(conn, site, tmp_path, define)
    conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
                    values (%s, 'wikipedia', 'He''s a Pirate from Pirates of the Caribbean', 'Ilia Malinin', 1)""",
                 [malinin_program(conn, "free skating")])
    wikipedia_piece = """select p.title from music_occurrences o join arrangements a on a.id = o.arrangement_id
                         join pieces p on p.id = a.piece_id where o.origin = 'wikipedia'"""

    # The revert removes the file's Piece before the music step, so Wikipedia's entry creates its own Piece under
    # that slug, and the file's definition is skipped: the line only aliases.
    run_import(conn, site, tmp_path, define)
    assert conn.execute(wikipedia_piece).fetchall() == [("He's a Pirate",)]
    assert conn.execute("select key from import_problems where kind = 'corrections slug taken by another record'"
                        " and import_id = (select max(id) from imports)").fetchall() == [("piece_aliases[0].piece",)]

    run_import(conn, site, tmp_path, "")
    assert conn.execute(wikipedia_piece).fetchall() == [("He's a Pirate",)]
    assert conn.execute("select title from pieces where title like 'He%%'").fetchall() == [("He's a Pirate",)]


def test_an_alias_may_name_a_piece_a_later_line_defines(conn, site, tmp_path):
    run_import(conn, site, tmp_path, "")
    fixes = """piece_aliases:
  - raw: Pirates
    piece: he-s-a-pirate
  - raw: He is a Pirate
    piece: he-s-a-pirate
    title: He's a Pirate
"""
    aliases = """select n.name from names n join keys k on k.system = 'slug' and k.entity = 'piece' and k.entity_id = n.entity_id
                 where k.value = 'he-s-a-pirate' and n.origin = 'corrections' order by n.name"""
    # The revert deletes the file's Piece, so every replay, not only the first, must define it before aliasing it.
    for _ in range(2):
        assert run_import(conn, site, tmp_path, fixes) == ("succeeded", None)
        assert unknown_keys(conn) == []
        assert conn.execute(aliases).fetchall() == [("He is a Pirate",), ("Pirates",)]
