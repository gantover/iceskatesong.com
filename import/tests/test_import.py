import gzip
import re
import shutil

import apply
import fetch
import main

GPF = "results/season2526/gpf2025/index.htm"
RHYTHM_DANCE = "results/season2526/gpf2025/SEG007.htm"
DOMAIN_TABLES = ["competitions", "segments", "skaters", "teams", "programs", "performances", "keys", "names"]


def run_import(conn, site, tmp_path, events=(GPF,), wikidata=False, youtube_api=None, scope="full"):
    events_file = tmp_path / "events.txt"
    events_file.write_text("# test list\n\n" + "".join(f"{site.url}/{e}\n" for e in events))
    conn.execute("insert into imports (scope) values (%s)", [scope])
    import_id = main.claim(conn)
    site.log.clear()
    endpoint = f"{site.url}/wikidata/sparql" if wikidata else None  # answers every query with the combined fixture
    main.run(conn, import_id, events_file, tmp_path / "cache", "test@example.com", interval=0, wikidata_endpoint=endpoint,
             youtube_api=youtube_api)
    return conn.execute("select status, counts, error from imports where id = %s", [import_id]).fetchone()


def problems(conn, kind):
    return [key for (key,) in conn.execute("select key from import_problems where kind = %s order by id", [kind])]


def snapshot(conn):
    """Every domain row with its xmin, so a rewrite of an unchanged row shows up too."""
    return {t: conn.execute(f"select array_agg(t.xmin::text || ' ' || t::text order by t::text) from {t} t").fetchone()[0]
            for t in DOMAIN_TABLES}


def edit_cached(site, tmp_path, page, edit):
    path = fetch.cache_path(tmp_path / "cache", f"{site.url}/{page}")
    path.write_bytes(gzip.compress(edit(gzip.decompress(path.read_bytes()).decode()).encode()))


def without_row(isu_id):
    return lambda page: re.sub(rf"(?is)<tr[^>]*>(?:(?!</tr>).)*isufs{isu_id}.*?</tr>", "", page, count=1)


def test_an_import_creates_the_events_records_and_succeeds(conn, site, tmp_path):
    status, counts, error = run_import(conn, site, tmp_path)

    assert (status, error) == ("succeeded", None)
    assert counts["competition"]["created"] == 1
    assert counts["segment"]["created"] == 16
    assert counts["performance"]["created"] == conn.execute("select count(*) from performances").fetchone()[0] > 16 * 5
    assert conn.execute("select name, city, start_date::text, level from competitions").fetchone() == (
        "ISU Grand Prix Final 2025", "Aichi, Nagoya", "2025-12-04", "senior")

    team = conn.execute("""select t.name, s1.name, s2.name, p.rank, p.tss::text, pr.season, pr.segment_type
                           from performances p join teams t on t.id = p.team_id join programs pr on pr.id = p.program_id
                           join skaters s1 on s1.id = t.skater1_id join skaters s2 on s2.id = t.skater2_id
                           where p.entry_key = '00013665' and pr.segment_type = 'rhythm dance'""").fetchone()
    assert team == ("Madison CHOCK / Evan BATES", "Madison CHOCK", "Evan BATES", 1, "88.74", 2025, "rhythm dance")
    assert "Madison CHOCK" in problems(conn, "Team member created")
    # Junior and senior Segments of the same Discipline and type stay apart.
    assert conn.execute("select count(*) from segments where discipline = 'men'").fetchone()[0] == 4


def test_a_second_run_sends_conditional_gets_and_changes_nothing(conn, site, tmp_path):
    run_import(conn, site, tmp_path)
    before = snapshot(conn)

    status, counts, _ = run_import(conn, site, tmp_path)

    assert status == "succeeded"
    assert {status for method, path, status in site.log} == {"304"}
    assert len(site.log) == 17
    assert counts == {}
    assert snapshot(conn) == before


def test_wikidata_attaches_keys_and_names_once(conn, site, tmp_path):
    status, counts, _ = run_import(conn, site, tmp_path, wikidata=True)

    assert status == "succeeded"
    # Malinin by his Skater ID; Chock and Bates (created as Team members) through their Team ID.
    assert {k: counts[k] for k in ("key", "name")} == {"key": {"created": 6, "updated": 0, "deleted": 0}, "name": {"created": 6, "updated": 0, "deleted": 0}}
    assert conn.execute("""select s.name from names n join skaters s on s.id = n.entity_id
                           where n.entity = 'skater' and n.name = 'イリア・マリニン'""").fetchall() == [("Ilia MALININ",)]
    before = snapshot(conn)

    _, counts, _ = run_import(conn, site, tmp_path, wikidata=True)

    assert counts == {}
    assert snapshot(conn) == before


def test_each_query_to_one_endpoint_is_its_own_cache_file(tmp_path):
    sparql = "https://query.wikidata.org/sparql"

    assert fetch.cache_path(tmp_path, f"{sparql}?query=a") != fetch.cache_path(tmp_path, f"{sparql}?query=b")
    assert fetch.cache_path(tmp_path, f"{sparql}?query=a").parent == tmp_path / "query.wikidata.org"
    # A page without a query string keeps its path, so the ISU cache stays where it is.
    assert fetch.cache_path(tmp_path, "http://127.0.0.1:80/results/index.htm") == tmp_path / "127.0.0.1_80/results/index.htm.gz"


def test_an_entry_removed_from_a_cached_page_is_gone_until_it_returns(conn, site, tmp_path):
    run_import(conn, site, tmp_path)
    original = fetch.read_cached(tmp_path / "cache", f"{site.url}/{RHYTHM_DANCE}").decode()

    edit_cached(site, tmp_path, RHYTHM_DANCE, without_row("00013665"))
    run_import(conn, site, tmp_path)
    gone = "select gone from performances where entry_key = '00013665' and segment_id = (select id from segments where segment_type = 'rhythm dance' and level = 'senior')"
    assert conn.execute(gone).fetchone() == (True,)
    assert problems(conn, "vanished import key") == ["00013665"]

    edit_cached(site, tmp_path, RHYTHM_DANCE, lambda _: original)
    run_import(conn, site, tmp_path)
    assert conn.execute(gone).fetchone() == (False,)


def test_a_page_that_fails_to_parse_leaves_its_segment_untouched(conn, site, tmp_path):
    run_import(conn, site, tmp_path)
    edit_cached(site, tmp_path, RHYTHM_DANCE, lambda page: page.replace("Rhythm Dance</td>", "Mystery Dance</td>"))

    status, counts, _ = run_import(conn, site, tmp_path)

    assert status == "succeeded"
    assert problems(conn, "parse failed") == [f"{site.url}/{RHYTHM_DANCE}"]
    assert conn.execute("select count(*) from performances where gone").fetchone() == (0,)


def test_a_quick_import_rechecks_only_the_two_newest_listed_seasons(conn, site, tmp_path):
    for season in ("season2425/gpf2024", "season1920/gpf2019"):
        shutil.copytree(site.root / "results/season2526/gpf2025", site.root / "results" / season)
    events = (GPF, "results/season2425/gpf2024/index.htm", "results/season1920/gpf2019/index.htm", JGP_2004)  # no Season folder: older
    run_import(conn, site, tmp_path, events=events)
    before = snapshot(conn)

    status, _, _ = run_import(conn, site, tmp_path, events=events, scope="quick")

    assert status == "succeeded"
    assert {path.split("/")[2] for _, path, _ in site.log} == {"season2526", "season2425"}
    assert snapshot(conn) == before  # the older events are applied from their cached pages


def test_a_quick_import_fetches_an_older_event_it_has_never_fetched(conn, site, tmp_path):
    run_import(conn, site, tmp_path)

    run_import(conn, site, tmp_path, events=(GPF, "results/wc2008/index.htm"), scope="quick")

    assert sorted(path for _, path, status in site.log if status == "200") == ["/results/wc2008/SEG001.HTM", "/results/wc2008/index.htm"]


def test_an_index_with_an_empty_title_takes_its_name_from_events_txt(conn, site, tmp_path):
    # Some FS Manager indexes (2019–20 to 2021–22, World Team Trophy 2025) print the name only in their header image.
    run_import(conn, site, tmp_path)
    edit_cached(site, tmp_path, GPF, lambda page: re.sub(r"(?is)<title>.*?</title>", "<title></title>", page))
    name = "select name from competitions"

    run_import(conn, site, tmp_path, events=(f"{GPF}  ISU GP Final 2025 ",))
    assert conn.execute(name).fetchone() == ("ISU GP Final 2025",)
    assert problems(conn, "parse failed") == []

    run_import(conn, site, tmp_path)
    assert conn.execute(name).fetchone() == ("season2526/gpf2025",)  # never blank: the event path stands in
    assert problems(conn, "parse failed") == [f"{site.url}/{GPF}"]


def test_two_spellings_of_one_isu_id_are_one_skater(conn, site, tmp_path):
    free = site.root / "results/season2526/gpf2025/SEG002.htm"
    free.write_text(free.read_text().replace("Ilia MALININ", "Ilya MALININ"))

    run_import(conn, site, tmp_path)

    skaters = conn.execute("""select distinct p.skater_id from performances p join keys k
                              on k.entity = 'skater' and k.entity_id = p.skater_id and k.system = 'isu' and k.value = '00108049'""").fetchall()
    assert len(skaters) == 1
    assert conn.execute("select name from names where entity = 'skater' and entity_id = %s order by name", skaters[0]).fetchall() == [
        ("Ilia MALININ",), ("Ilya MALININ",)]


def test_a_hand_changed_skater_link_survives_a_reimport(conn, site, tmp_path):
    run_import(conn, site, tmp_path)
    other = conn.execute("insert into skaters (name, nation) values ('Someone ELSE', 'USA') returning id").fetchone()[0]
    conn.execute("update performances set skater_id = %s where entry_key = '00108049'", [other])
    edit_cached(site, tmp_path, "results/season2526/gpf2025/SEG001.htm", lambda page: page.replace("Ilia MALININ", "Ilia MALININ-X"))

    _, counts, _ = run_import(conn, site, tmp_path)

    assert counts["performance"]["updated"] == 1
    assert conn.execute("select distinct skater_id from performances where entry_key = '00108049'").fetchall() == [(other,)]


def test_an_index_without_segment_pages_fails_to_parse(conn, site, tmp_path):
    status, _, _ = run_import(conn, site, tmp_path, events=(GPF, "results/season2324/gpjpn2023/index.htm"))

    assert status == "succeeded"
    assert problems(conn, "parse failed") == [f"{site.url}/results/season2324/gpjpn2023/index.htm"]


def test_too_many_failed_fetches_fail_the_import_and_write_nothing(conn, site, tmp_path):
    status, _, error = run_import(conn, site, tmp_path, events=("results/nowhere/index.htm",))

    assert status == "failed"
    assert error == "1 of 1 fetches failed"
    assert problems(conn, "fetch failed") == [f"{site.url}/results/nowhere/index.htm"]
    assert len(site.log) == 3
    assert conn.execute("select count(*) from competitions").fetchone() == (0,)


JGP_2004 = "results/jgpchn2004/index.htm"  # links SEG001.HTM, the host serves seg001.htm


def skaters_printed_as(conn, name):
    return conn.execute("select distinct skater_id from performances where name = %s", [name]).fetchall()


def test_a_2004_event_imports_its_lowercase_pages_and_entries_without_isu_id(conn, site, tmp_path):
    status, counts, _ = run_import(conn, site, tmp_path, events=(JGP_2004,))

    assert status == "succeeded"
    assert problems(conn, "fetch failed") == problems(conn, "parse failed") == []
    assert counts["segment"]["created"] == 9
    assert conn.execute("select name, city, start_date::text, level from competitions").fetchone() == (
        "ISU Junior Grand Prix Harbin", "Harbin", "2004-09-16", "junior")
    assert conn.execute("select url from segments order by id limit 1").fetchone() == (f"{site.url}/results/jgpchn2004/seg001.htm",)
    # Entries without an ISU ID: one Skater (and one Team) per person across the event's Segments.
    assert len(skaters_printed_as(conn, "Jinlin GUAN")) == 1
    assert conn.execute("select count(distinct team_id) from performances where name = 'Elena EFAIEVA / Alexei MENSHIKOV'").fetchone() == (1,)


def test_entries_without_isu_id_are_one_skater_or_team_across_events_and_join_their_isu_id_once_printed(conn, site, tmp_path):
    # Yu-Na KIM and Tessa VIRTUE / Scott MOIR skate JGP Harbin and Budapest without an ISU ID, then the JGP Final with one.
    status, _, _ = run_import(conn, site, tmp_path, events=(JGP_2004, "results/jgphun2004/index.htm", "results/jgpf0405/index.htm"))

    assert status == "succeeded"
    assert problems(conn, "parse failed") == []
    assert conn.execute("select count(distinct segment_id) from performances where name = 'Yu-Na KIM'").fetchone() == (6,)
    assert skaters_printed_as(conn, "Yu-Na KIM") == conn.execute(
        "select entity_id from keys where system = 'isu' and value = '00007232'").fetchall()
    assert conn.execute("select distinct team_id from performances where name = 'Tessa VIRTUE / Scott MOIR'").fetchall() == conn.execute(
        "select entity_id from keys where system = 'isu' and value = '00006989'").fetchall()


def test_youth_olympics_and_junior_series_are_junior():
    assert [apply.event_level(f"https://results.isu.org/results/{path}/index.htm") for path in
            ("season1920/wyog2020", "yog2012", "season2526/jgptha2025", "season2526/gpf2025")] == ["junior", "junior", "junior", "senior"]
