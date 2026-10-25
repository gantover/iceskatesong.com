"""The Wikipedia step through the Import pipeline, with cached rendered real program tables."""

import http.server
import gzip
import json
import pathlib
import threading
from urllib.parse import parse_qs, urlsplit

import pytest

import main

PAGES = pathlib.Path(__file__).parent / "pages/wikipedia"
ARTICLES = {d["parse"]["title"]: d["parse"] for p in PAGES.glob("*.json") for d in [json.loads(p.read_text())] if "parse" in d}


class Wikipedia(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = {key: values[0] for key, values in parse_qs(urlsplit(self.path).query).items()}
        self.server.log.append(params)
        if params["action"] == "parse":
            article = next(a for a in self.server.articles.values() if a["revid"] == int(params["oldid"]))
            answer = {"parse": article} if article["revid"] not in self.server.failed else {"error": {"info": "temporary failure"}}
        else:
            pages = []
            for title in params["titles"].split("|"):
                if title in self.server.articles:
                    a = self.server.articles[title]
                    pages.append({"title": title, "revisions": [{"revid": a["revid"]}]})
                else:
                    pages.append({"title": title, "pageprops": {"wikibase_item": self.server.qids.get(title)}})
            answer = {"query": {"pages": pages}}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(answer).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def wikipedia():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Wikipedia)
    server.log, server.articles, server.qids = [], dict(ARTICLES), json.loads((PAGES / "link-qids.json").read_text())
    server.failed = set()
    server.url = f"http://127.0.0.1:{server.server_port}/w/api.php"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()


def skater(conn, name, title, isu_id):
    id = conn.execute("insert into skaters (name, nation) values (%s, 'USA') returning id", [name]).fetchone()[0]
    for system, value in (("isu", isu_id), ("enwiki", title)):
        conn.execute("insert into keys (system, value, entity, entity_id) values (%s, %s, 'skater', %s)", [system, value, id])
    return id


def program(conn, owner, season, segment_type, entity="skater"):
    return conn.execute(f"insert into programs ({entity}_id, season, segment_type) values (%s, %s, %s) returning id",
                        [owner, season, segment_type]).fetchone()[0]


def run(conn, tmp_path, wikipedia, expected_status="succeeded"):
    events = tmp_path / "events.txt"
    events.write_text("")
    conn.execute("insert into imports default values")
    id = main.claim(conn)
    main.run(conn, id, events, tmp_path / "cache", "test@example.com", interval=0, wikipedia_endpoint=wikipedia.url)
    status, error = conn.execute("select status, error from imports where id = %s", [id]).fetchone()
    assert status == expected_status, error
    if expected_status == "succeeded":
        assert error is None


def test_a_wikipedia_music_claim_keeps_its_article_and_revision(conn, tmp_path, wikipedia):
    ilia = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    short = program(conn, ilia, 2024, "short program")

    run(conn, tmp_path, wikipedia)

    claim = conn.execute("select raw_text, article_title, revision from music_claims where program_id = %s", [short]).fetchone()
    assert claim[1:] == ("Ilia Malinin", 1378424980)
    assert "Running" in claim[0]
    assert "NF" in claim[0]


@pytest.mark.parametrize("title,season,segment_type,expected", [
    ("Yuzuru Hanyu", 2004, "short program", "Spartacus"),
    ("Yuzuru Hanyu", 2019, "short program", "Ballade No. 1"),
    ("Ilia Malinin", 2025, "free skating", "The Ball"),
])
def test_the_sample_skaters_music_matches_the_season_and_segment(conn, tmp_path, wikipedia, title, season, segment_type, expected):
    owner = skater(conn, title.upper(), title, "00123456")
    id = program(conn, owner, season, segment_type)

    run(conn, tmp_path, wikipedia)

    assert expected in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]


@pytest.mark.parametrize("title,season,segment_type,expected", [
    ("Aljona Savchenko", 2013, "short program", "The Pink Panther"),
    ("Robin Szolkowy", 2013, "free skating", "The Nutcracker"),
    ("Tessa Virtue", 2004, "original dance", "Call Me Irresponsible"),
    ("Scott Moir", 2017, "free dance", "El Tango De Roxanne"),
])
def test_a_partners_crosswalk_reaches_the_teams_program(conn, tmp_path, wikipedia, title, season, segment_type, expected):
    if title in ("Aljona Savchenko", "Robin Szolkowy"):
        first, second = "Aljona Savchenko", "Robin Szolkowy"
    else:
        first, second = "Tessa Virtue", "Scott Moir"
    owners = [skater(conn, name.upper(), name, str(12345600 + i)) for i, name in enumerate([first, second])]
    conn.execute("delete from keys where system = 'enwiki' and value <> %s", [title])
    team = conn.execute("insert into teams (name, skater1_id, skater2_id) values (%s, %s, %s) returning id",
                        [first + ' / ' + second, *owners]).fetchone()[0]
    id = program(conn, team, season, segment_type, entity="team")

    run(conn, tmp_path, wikipedia)

    assert expected in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]
    if title == "Aljona Savchenko":
        qids = conn.execute("select title_qids from music_claims where program_id = %s", [id]).fetchone()[0]
        assert qids["The Pink Panther (2006 film)"] == "Q844497"


def test_a_failed_followed_article_keeps_the_previous_music_and_its_revision(conn, tmp_path, wikipedia):
    owner = skater(conn, "Yuzuru HANYU", "Yuzuru Hanyu", "00010967")
    id = program(conn, owner, 2004, "short program")
    run(conn, tmp_path, wikipedia)
    before = conn.execute("select raw_text, article_title, revision from music_claims where program_id = %s", [id]).fetchone()
    article = wikipedia.articles["List of figure skating programs of Yuzuru Hanyu"]
    wikipedia.articles[article["title"]] = {**article, "revid": article["revid"] + 1}
    wikipedia.failed.add(article["revid"] + 1)

    run(conn, tmp_path, wikipedia, expected_status="failed")

    assert conn.execute("select raw_text, article_title, revision from music_claims where program_id = %s", [id]).fetchone() == before


def test_a_failed_article_download_recovers_at_the_same_revision(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    revision = wikipedia.articles["Ilia Malinin"]["revid"]
    wikipedia.failed.add(revision)
    run(conn, tmp_path, wikipedia, expected_status="failed")
    assert conn.execute("select count(*) from music_claims").fetchone() == (0,)
    assert sum(request["action"] == "parse" for request in wikipedia.log) == 3
    assert all(b"temporary failure" not in gzip.decompress(p.read_bytes()) for p in (tmp_path / "cache").rglob("*.gz"))

    wikipedia.failed.clear()
    run(conn, tmp_path, wikipedia)

    claim = conn.execute("select raw_text, revision from music_claims where program_id = %s", [id]).fetchone()
    assert claim is not None
    assert "Running" in claim[0]
    assert claim[1] == revision


def test_only_program_evidence_is_persisted_and_an_unchanged_revision_uses_that_cache(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    article = wikipedia.articles["Ilia Malinin"]
    biography = '<table class="infobox"><tr><th>Born</th><td>1971-02-03</td></tr><tr><th>Height</th><td>1.93 metres</td></tr></table>'
    unfamiliar = '<h2>Programs</h2><table class="wikitable"><tr><th>Year</th><th>Unfamiliar program header</th></tr><tr><td>2024</td><td>Raw music for a future parser fix</td></tr></table>'
    wikipedia.articles["Ilia Malinin"] = {**article, "text": biography + unfamiliar + article["text"]}

    run(conn, tmp_path, wikipedia)

    stored = b"\n".join(gzip.decompress(p.read_bytes()) for p in (tmp_path / "cache").rglob("*.gz"))
    assert b"1971-02-03" not in stored
    assert b"1.93 metres" not in stored
    assert b"Running" in stored
    assert b"rowspan" in stored
    assert b"Shae-Lynn_Bourne" in stored
    assert b"Raw music for a future parser fix" in stored
    conn.execute("delete from music_claims")
    wikipedia.log.clear()

    run(conn, tmp_path, wikipedia)

    assert all(request["action"] != "parse" for request in wikipedia.log)
    assert "Running" in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]


def test_a_legacy_full_article_cache_is_minimized_before_reuse(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    run(conn, tmp_path, wikipedia)
    # Simulate a full response cached by the previous importer version.
    article = wikipedia.articles["Ilia Malinin"]
    legacy = {**article, "text": '<div class="infobox">Born 1971-02-03; height 1.93 metres</div>' + article["text"]}
    cached = next(p for p in (tmp_path / "cache").rglob("*.gz") if '"parse"' in gzip.decompress(p.read_bytes()).decode())
    cached.write_bytes(gzip.compress(json.dumps({"parse": legacy}).encode()))
    conn.execute("delete from music_claims")
    wikipedia.log.clear()

    run(conn, tmp_path, wikipedia)

    assert all(request["action"] != "parse" for request in wikipedia.log)
    assert b"1971-02-03" not in gzip.decompress(cached.read_bytes())
    assert b"1.93 metres" not in gzip.decompress(cached.read_bytes())
    assert "Running" in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]


def test_an_invalid_legacy_article_cache_is_refetched_at_the_same_revision(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    run(conn, tmp_path, wikipedia)
    cached = next(p for p in (tmp_path / "cache").rglob("*.gz") if '"parse"' in gzip.decompress(p.read_bytes()).decode())
    cached.write_bytes(gzip.compress(b'{"error": {"info": "temporary API failure"}}'))
    conn.execute("delete from music_claims")
    wikipedia.log.clear()

    run(conn, tmp_path, wikipedia)

    assert sum(request["action"] == "parse" for request in wikipedia.log) == 1
    assert "Running" in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]


def test_an_article_without_an_isu_crosswalk_creates_no_claim_and_logs_a_problem(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    program(conn, owner, 2024, "short program")
    conn.execute("delete from keys where system = 'isu'")

    run(conn, tmp_path, wikipedia)

    assert conn.execute("select count(*) from music_claims").fetchone() == (0,)
    assert conn.execute("select key from import_problems where kind = 'Wikipedia Skater with no ISU-ID crosswalk'").fetchall() == [("Ilia Malinin",)]


def test_the_first_import_attaches_wikipedia_to_the_programs_it_just_created(conn, site, tmp_path, wikipedia):
    events = tmp_path / "events.txt"
    events.write_text(f"{site.url}/results/season2526/gpf2025/index.htm\n")
    conn.execute("insert into imports default values")
    id = main.claim(conn)

    main.run(conn, id, events, tmp_path / "cache", "test@example.com", interval=0,
             wikidata_endpoint=f"{site.url}/wikidata/sparql", wikipedia_endpoint=wikipedia.url)

    assert conn.execute("select status, error from imports where id = %s", [id]).fetchone() == ("succeeded", None)
    claim = conn.execute("""select m.raw_text, m.article_title from music_claims m join programs p on p.id = m.program_id
        join skaters s on s.id = p.skater_id where s.name = 'Ilia MALININ' and p.season = 2025 and p.segment_type = 'free skating'""").fetchone()
    assert "The Ball" in claim[0]
    assert claim[1] == "Ilia Malinin"


def test_an_unchanged_revision_downloads_no_article_and_reparses_the_cached_music(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    run(conn, tmp_path, wikipedia)
    # Force the apply step to prove it reads the cached article again, rather than skipping it with the download.
    conn.execute("delete from music_claims")
    wikipedia.log.clear()

    run(conn, tmp_path, wikipedia)

    assert all(request["action"] != "parse" for request in wikipedia.log)
    assert "Running" in conn.execute("select raw_text from music_claims where program_id = %s", [id]).fetchone()[0]


def test_a_changed_revision_replaces_only_wikipedia_claims_and_logs_rows_with_no_program(conn, tmp_path, wikipedia):
    owner = skater(conn, "Ilia MALININ", "Ilia Malinin", "00108049")
    id = program(conn, owner, 2024, "short program")
    run(conn, tmp_path, wikipedia)
    conn.execute("insert into music_claims (program_id, origin, raw_text) values (%s, 'admin', 'Owner correction')", [id])
    article = wikipedia.articles["Ilia Malinin"]
    wikipedia.articles["Ilia Malinin"] = {**article, "revid": article["revid"] + 1, "text": article["text"].replace('Running', 'Corrected title')}

    run(conn, tmp_path, wikipedia)

    rows = conn.execute("select origin, raw_text, revision from music_claims where program_id = %s order by origin", [id]).fetchall()
    assert rows[0] == ("admin", "Owner correction", None)
    assert rows[1][0] == "wikipedia"
    assert "Corrected title" in rows[1][1]
    assert rows[1][2] == 1378424981
    assert conn.execute("select count(*) from programs").fetchone() == (1,)
    assert conn.execute("select count(*) from import_problems where kind = 'Wikipedia row with no Program'").fetchone()[0] > 0


def test_latest_revision_queries_batch_at_most_fifty_titles(conn, tmp_path, wikipedia):
    sample = ARTICLES["Ilia Malinin"]
    for i in range(51):
        title = f"Sample skater {i}"
        wikipedia.articles[title] = {**sample, "title": title, "revid": 1500000000 + i}
        skater(conn, title, title, str(12000000 + i))

    run(conn, tmp_path, wikipedia)

    batches = [r["titles"].split("|") for r in wikipedia.log if r.get("prop") == "revisions"]
    assert sorted(map(len, batches)) == [1, 50]
