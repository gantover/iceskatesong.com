import gzip
import re

import fetch
import main

GPF = "results/season2526/gpf2025/index.htm"
RHYTHM_DANCE = "results/season2526/gpf2025/SEG007.htm"
DOMAIN_TABLES = ["competitions", "segments", "skaters", "teams", "programs", "performances", "keys", "names"]


def run_import(conn, site, tmp_path, events=(GPF,)):
    events_file = tmp_path / "events.txt"
    events_file.write_text("# test list\n\n" + "".join(f"{site.url}/{e}\n" for e in events))
    conn.execute("insert into imports default values")
    import_id = main.claim(conn)
    site.log.clear()
    main.run(conn, import_id, events_file, tmp_path / "cache", "test@example.com", interval=0)
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
