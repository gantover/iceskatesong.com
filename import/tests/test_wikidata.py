import pathlib

import wikidata

SPARQL = (pathlib.Path(__file__).parent / "pages/wikidata/sparql").read_bytes()  # trimmed from a real query result


def skater(conn, name, nation, isu_id=None):
    skater_id = conn.execute("insert into skaters (name, nation) values (%s, %s) returning id", [name, nation]).fetchone()[0]
    conn.execute("insert into names (entity, entity_id, name, origin) values ('skater', %s, %s, 'isu')", [skater_id, name])
    if isu_id:
        conn.execute("insert into keys (system, value, entity, entity_id) values ('isu', %s, 'skater', %s)", [isu_id, skater_id])
    return skater_id


def team(conn, isu_id, *members):
    team_id = conn.execute("insert into teams (name, skater1_id, skater2_id) values ('t', %s, %s) returning id", members).fetchone()[0]
    conn.execute("insert into keys (system, value, entity, entity_id) values ('isu', %s, 'team', %s)", [isu_id, team_id])
    return team_id


def search(conn, text):
    """What the name search (#32) will match: an unaccented, case-insensitive substring of any name."""
    return conn.execute("""select distinct entity, entity_id from names
                           where lower(f_unaccent(name)) like '%%' || lower(f_unaccent(%s)) || '%%'""", [text]).fetchall()


def keys(conn, entity_id, entity="skater"):
    return conn.execute("select system, value from keys where entity = %s and entity_id = %s and system <> 'isu' order by system",
                        [entity, entity_id]).fetchall()


def test_japanese_and_russian_names_find_the_skater(conn):
    hanyu = skater(conn, "Yuzuru HANYU", "JPN", "00010967")
    plushenko = skater(conn, "Evgeni PLUSHENKO", "RUS", "00000124")

    wikidata.run(conn, SPARQL, [])

    assert search(conn, "羽生結弦") == [("skater", hanyu)]
    assert search(conn, "Плющенко") == [("skater", plushenko)]
    assert keys(conn, hanyu) == [("enwiki", "Yuzuru Hanyu"), ("wikidata", "Q597023")]
    # The display name stays the ISU Latin name.
    assert conn.execute("select name from skaters where id = %s", [hanyu]).fetchone() == ("Yuzuru HANYU",)


def test_a_team_id_on_each_partners_item_attaches_to_that_partner(conn):
    chock, bates = skater(conn, "Madison CHOCK", "USA"), skater(conn, "Evan BATES", "USA")
    chock_bates = team(conn, "00013665", chock, bates)
    # One Skater with two partners: Wikidata puts both Team IDs on her item.
    bazarova, larionov, deputat = (skater(conn, name, "RUS") for name in ("Vera BAZAROVA", "Yuri LARIONOV", "Andrei DEPUTAT"))
    team(conn, "00009807", bazarova, larionov)
    team(conn, "00054476", bazarova, deputat)

    wikidata.run(conn, SPARQL, [])

    assert search(conn, "メディソン・チョーク") == [("skater", chock)]
    assert search(conn, "Эван Бейтс") == [("skater", bates)]
    assert keys(conn, bazarova) == [("enwiki", "Vera Bazarova"), ("wikidata", "Q462429")]
    assert keys(conn, deputat) == [("enwiki", "Andrei Deputat"), ("wikidata", "Q4755771")]
    assert keys(conn, chock_bates, "team") == []


def test_an_item_naming_both_partners_attaches_to_the_team(conn):
    davis_white = team(conn, "00006260", skater(conn, "Meryl DAVIS", "USA"), skater(conn, "Charlie WHITE", "USA"))

    wikidata.run(conn, SPARQL, [])

    assert keys(conn, davis_white, "team") == [("enwiki", "Meryl Davis and Charlie White"), ("wikidata", "Q96592016")]


def test_a_team_id_item_naming_neither_partner_is_a_problem(conn):
    team(conn, "00013665", skater(conn, "Someone ELSE", "USA"), skater(conn, "Another PERSON", "USA"))
    problems = []

    wikidata.run(conn, SPARQL, problems)

    assert sorted(p["key"] for p in problems) == ["Q2470854", "Q457792"]  # Bates, Chock
    assert conn.execute("select count(*) from keys where system <> 'isu'").fetchone() == (0,)


def test_partners_sharing_only_a_surname_with_the_item_are_a_problem_not_the_team(conn):
    # Siblings or a married couple: "Madison Chock" names neither "Madisen" nor "Ted" (the given name is spelt differently).
    chocks = team(conn, "00013665", skater(conn, "Madisen CHOCK", "USA"), skater(conn, "Ted CHOCK", "USA"))
    problems = []

    wikidata.run(conn, SPARQL, problems)

    assert sorted(p["key"] for p in problems) == ["Q2470854", "Q457792"]  # Bates, Chock
    assert keys(conn, chocks, "team") == []


def test_an_item_matching_several_skaters_is_a_problem(conn):
    # Bazarova's item carries two ISU IDs; here each one is a different Skater: a duplicate, not a choice to make.
    skater(conn, "Vera BAZAROVA", "RUS", "00009807")
    skater(conn, "Vera BAZAROVA", "RUS", "00054476")
    problems = []

    wikidata.run(conn, SPARQL, problems)

    assert [(p["kind"], p["key"]) for p in problems] == [("Wikidata item matches several Skaters", "Q462429")]
    assert conn.execute("select count(*) from keys where value in ('Q462429', 'Vera Bazarova')").fetchone() == (0,)


def test_an_article_title_follows_its_item_to_another_record(conn):
    hanyu = skater(conn, "Yuzuru HANYU", "JPN", "00010967")
    conn.execute("insert into keys (system, value, entity, entity_id) values ('enwiki', 'Yuzuru Hanyu', 'skater', %s)", [hanyu + 1])

    counts = wikidata.run(conn, SPARQL, [])

    assert counts["key"] == {"created": 1, "updated": 1, "deleted": 0}  # the QID; the moved title
    assert keys(conn, hanyu) == [("enwiki", "Yuzuru Hanyu"), ("wikidata", "Q597023")]


def test_a_changed_label_or_article_title_replaces_the_old_one(conn):
    hanyu = skater(conn, "Yuzuru HANYU", "JPN", "00010967")
    wikidata.run(conn, SPARQL, [])

    changed = SPARQL.decode().replace("Юдзуру Ханю", "Юдзуру Ханю (фигурист)").replace('"Yuzuru Hanyu"', '"Yuzuru Hanyu (skater)"')
    counts = wikidata.run(conn, changed.encode(), [])

    assert counts == {"key": {"created": 1, "updated": 0, "deleted": 1}, "name": {"created": 1, "updated": 0, "deleted": 1}}
    assert keys(conn, hanyu) == [("enwiki", "Yuzuru Hanyu (skater)"), ("wikidata", "Q597023")]
    assert conn.execute("select name from names where origin = 'wikidata' order by name").fetchall() == [
        ("Юдзуру Ханю (фигурист)",), ("羽生結弦",)]


def test_an_unparseable_answer_is_a_problem_and_changes_nothing(conn):
    skater(conn, "Yuzuru HANYU", "JPN", "00010967")
    wikidata.run(conn, SPARQL, [])
    problems = []

    assert wikidata.run(conn, b'{"results": {"bindings": []}}', problems) == {}

    assert [p["kind"] for p in problems] == ["parse failed"]
    assert conn.execute("select count(*) from names where origin = 'wikidata'").fetchone() == (2,)


def test_items_whose_isu_ids_match_nothing_are_ignored(conn):
    problems = []

    assert wikidata.run(conn, SPARQL, problems) == {}

    assert problems == []
    assert conn.execute("select count(*) from keys").fetchone() == (0,)
    assert conn.execute("select count(*) from names").fetchone() == (0,)
