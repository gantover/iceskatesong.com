"""Music evidence at the normaliser and Import boundaries (issue #35)."""

import json
import pathlib
from types import SimpleNamespace

import anthropic
import pytest
from psycopg.types.json import Jsonb

import main
import normalise
import wikipedia


class Claude:
    """Only the external SDK boundary is replaced; storage and the Import pipeline are real."""
    def __init__(self):
        self.calls = []
        self.same_piece = True
        self.messages = SimpleNamespace(create=self.create)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        raw = json.loads(kwargs["messages"][0]["content"])
        if "same_piece" in kwargs["output_config"]["format"]["schema"]["properties"]:
            return SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=100, output_tokens=10),
                                   content=[SimpleNamespace(type="text", text=json.dumps({"same_piece": self.same_piece}))])
        return SimpleNamespace(stop_reason="end_turn", usage=SimpleNamespace(input_tokens=100, output_tokens=100),
                               content=[SimpleNamespace(type="text", text=json.dumps({"pieces": normalise.parse(raw)}))])


def import_claim(conn, tmp_path, raw, client=None, cap=10):
    owner = conn.execute("insert into skaters (name, nation) values ('Test', 'USA') returning id").fetchone()[0]
    program = conn.execute("insert into programs (skater_id, season, segment_type) values (%s, 2024, 'free skating') returning id",
                           [owner]).fetchone()[0]
    conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision)
        values (%s, 'wikipedia', %s, 'Test', 1)""", [program, raw])
    return program, run_import(conn, tmp_path, client, cap)


def run_import(conn, tmp_path, client=None, cap=10, entity_endpoint=None):
    events = tmp_path / "events.txt"
    events.write_text("")
    conn.execute("insert into imports default values")
    id = main.claim(conn)
    main.run(conn, id, events, tmp_path / "cache", "test@example.com", interval=0,
             music_client=client, music_spend_cap=cap, music_entity_endpoint=entity_endpoint)
    status, error = conn.execute("select status, error from imports where id = %s", [id]).fetchone()
    assert status == "succeeded", error
    return id


def test_grades_belong_to_occurrences_and_model_memory_is_discarded():
    guessed = {"title": "Vuelvo al Sur", "composers": ["Astor Piazzolla", "Horacio Ferrer"],
               "source": "María de Buenos Aires", "performer": "Medialuna Tango Project", "style": "arrangement"}
    piece = normalise.resolve("Tango: Vuelvo al Sur by Medialuna Tango Project", guessed, {}, {})
    assert piece == {"title": "Vuelvo al Sur", "composers": [], "source": None,
                     "performer": "Medialuna Tango Project", "style": "original", "genres": [],
                     "qid": None, "grade": "title only"}

    tango = {"title": "Tango", "composers": [], "source": None, "performer": None, "style": "original"}
    assert normalise.resolve("Tango", tango, {}, {})["grade"] == "title only"
    identified = normalise.resolve("Tango by Cover Band", tango, {"Tango": "Q123"}, {
        "Q123": {"composers": [{"name": "Actual Composer", "qid": "Q456"}]}})
    assert identified["grade"] == "identified"
    assert identified["composers"] == [{"name": "Actual Composer", "qid": "Q456"}]


def test_import_saves_ordered_music_and_keeps_bare_titles_separate_on_reimport(conn, tmp_path):
    skater = conn.execute("insert into skaters (name, nation) values ('Test', 'USA') returning id").fetchone()[0]
    for season in (2023, 2024):
        program = conn.execute("insert into programs (skater_id, season, segment_type) values (%s, %s, 'free skating') returning id",
                               [skater, season]).fetchone()[0]
        conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision, entries)
            values (%s, 'wikipedia', 'Tango\nPrelude by Composer', 'Test', 1, %s)""",
            [program, Jsonb([{"raw": "Tango", "titles": {}}, {"raw": "Prelude by Composer", "titles": {}}])])
    events = tmp_path / "events.txt"
    events.write_text("")

    def run():
        conn.execute("insert into imports default values")
        id = main.claim(conn)
        main.run(conn, id, events, tmp_path / "cache", "test@example.com", interval=0)
        status, error = conn.execute("select status, error from imports where id = %s", [id]).fetchone()
        assert status == "succeeded", error
        return conn.execute("""select o.program_id, o.position, a.piece_id, p.title, o.grade
            from music_occurrences o join arrangements a on a.id = o.arrangement_id
            join pieces p on p.id = a.piece_id order by o.program_id, o.position""").fetchall()

    first = run()
    assert [(row[1], row[3], row[4]) for row in first] == [
        (0, "Tango", "title only"), (1, "Prelude", "credited"),
        (0, "Tango", "title only"), (1, "Prelude", "credited")]
    assert first[0][2] != first[2][2]
    assert first[1][2] == first[3][2]
    assert run() == first


def test_wikipedia_preserves_each_piece_and_title_link_evidence():
    article = wikipedia.parse("Test", 1, '''<table class="wikitable"><tr><th>Season</th><th>Free skating</th></tr>
        <tr><td>2024–25</td><td><ul><li><a href="/wiki/Tango_(work)">Tango</a><br>by Cover Band</li>
        <li>Prelude<br>by Composer</li></ul></td></tr></table>''')
    assert article.rows[0].entries == [
        {"raw": "Tango by Cover Band", "titles": {"Tango": "Tango (work)"}},
        {"raw": "Prelude by Composer", "titles": {}}]


def test_template_tracks_keep_the_shared_work_heading_and_credits():
    from bs4 import BeautifulSoup
    cells = json.loads((pathlib.Path(__file__).parent / "pages/music/context-cells.json").read_text())
    entries = wikipedia.music_entries(BeautifulSoup(cells["3768"]["html"], "html.parser").td)
    assert len(entries) == 3
    assert all("Hans Zimmer" in entry["raw"] and "Pirates of the Caribbean" in entry["raw"] for entry in entries)


def test_second_import_reuses_llm_results_by_raw_string(conn, tmp_path):
    client = Claude()
    import_claim(conn, tmp_path, "Prelude by Composer", client)
    assert len(client.calls) == 1
    run_import(conn, tmp_path, client)
    assert len(client.calls) == 1
    assert conn.execute("select count(*) from music_llm_cache").fetchone()[0] == 1


def test_cap_stops_before_a_paid_call_and_import_still_succeeds(conn, tmp_path):
    client = Claude()
    _, id = import_claim(conn, tmp_path, "Prelude by Composer", client, cap=0)
    assert client.calls == []
    assert conn.execute("select count(*) from music_occurrences").fetchone()[0] == 0
    assert conn.execute("select kind from import_problems where import_id = %s order by id", [id]).fetchall() == [
        ("music spend cap reached",), ("music string with no alias match",)]


def test_identified_composers_come_from_wikidata_not_the_cover_credit(conn, tmp_path, site):
    program, _ = import_claim(conn, tmp_path, "Tango by Cover Band")
    conn.execute("update music_claims set title_qids = %s where program_id = %s", [Jsonb({"Tango": "Q123"}), program])
    (site.root / "entities").write_text(json.dumps({"entities": {
        "Q123": {"claims": {"P86": [{"mainsnak": {"datavalue": {"value": {"id": "Q456"}}}}]}},
        "Q456": {"labels": {"en": {"value": "Actual Composer"}}}}}))
    run_import(conn, tmp_path, entity_endpoint=site.url + "/entities")
    assert conn.execute("""select o.grade, a.name from music_occurrences o
        join arrangements ar on ar.id = o.arrangement_id join piece_artists pa on pa.piece_id = ar.piece_id
        join artists a on a.id = pa.artist_id where o.program_id = %s""", [program]).fetchall() == [("identified", "Actual Composer")]
    assert conn.execute("select entity from keys where system = 'wikidata' and value = 'Q456'").fetchone() == ("artist",)


def test_existing_piece_and_artist_keys_are_reused_and_title_only_grade_stays_local(conn, tmp_path):
    artist = conn.execute("insert into artists (name) values ('Composer') returning id").fetchone()[0]
    piece = conn.execute("insert into pieces (title) values ('Tango') returning id").fetchone()[0]
    conn.execute("insert into keys values ('wikidata', 'Q123', 'piece', %s)", [piece])
    conn.execute("insert into keys values ('wikidata', 'Q456', 'artist', %s)", [artist])
    conn.execute("insert into piece_artists values (%s, %s, 'admin')", [piece, artist])
    program, _ = import_claim(conn, tmp_path, "Tango by Composer")
    assert conn.execute("select count(*) from artists").fetchone()[0] == 1
    assert conn.execute("select piece_id from arrangements").fetchone() == (piece,)
    conn.execute("update music_claims set raw_text = 'Tango' where program_id = %s", [program])
    run_import(conn, tmp_path)
    assert conn.execute("select grade from music_occurrences").fetchone() == ("title only",)


def test_rules_keep_a_named_bare_piece_when_the_model_abstains(conn, tmp_path):
    conn.execute("insert into music_llm_cache (raw_text, result, model) values ('The Immigrant', '[]', %s)", [normalise.MODEL])
    import_claim(conn, tmp_path, "The Immigrant")
    assert conn.execute("select title from pieces").fetchall() == [("The Immigrant",)]


def test_llm_adjudicates_a_near_title_with_shared_credit_and_caches_the_verdict(conn, tmp_path):
    client = Claude()
    import_claim(conn, tmp_path, "Drink Up Me Hearties (from Pirates of the Caribbean) by Hans Zimmer", client)
    import_claim(conn, tmp_path, "Drink Up Me Hearties Yo Ho (from Pirates of the Caribbean) by Hans Zimmer", client)
    assert conn.execute("select count(*) from pieces").fetchone()[0] == 1
    calls = len(client.calls)
    run_import(conn, tmp_path, client)
    assert len(client.calls) == calls


def test_an_ambiguous_api_failure_keeps_its_budget_reservation_and_does_not_fail_import(conn, tmp_path):
    client = Claude()

    def timeout(**kwargs):
        client.calls.append(kwargs)
        raise anthropic.APIConnectionError(request=SimpleNamespace())

    client.messages.create = timeout
    _, id = import_claim(conn, tmp_path, "Prelude by Composer\nAnother by Composer", client, cap="0.013")
    assert len(client.calls) == 1
    assert conn.execute("select kind from import_problems where import_id = %s order by id", [id]).fetchall() == [
        ("music LLM failed",), ("music spend cap reached",),
        ("music string with no alias match",), ("music string with no alias match",)]


def test_reimport_does_not_replace_human_music_claims_or_occurrences(conn, tmp_path):
    program, _ = import_claim(conn, tmp_path, "Prelude by Composer")
    arrangement = conn.execute("select arrangement_id from music_occurrences").fetchone()[0]
    conn.execute("insert into music_claims (program_id, origin, raw_text) values (%s, 'admin', 'Human music')", [program])
    conn.execute("""insert into music_occurrences (program_id, origin, position, arrangement_id, grade, raw_text)
        values (%s, 'admin', 0, %s, 'identified', 'Human music')""", [program, arrangement])
    run_import(conn, tmp_path)
    assert conn.execute("select raw_text, grade from music_occurrences where origin = 'admin'").fetchall() == [("Human music", "identified")]


@pytest.mark.parametrize("a,b", [("Tango by Composer A", "Tango by Composer B"), ("Tango", "Tango by Composer A"),
                                 ("Tango by Composer A", "Tango")])
def test_same_title_never_overrides_conflicting_or_missing_identity_evidence(conn, tmp_path, a, b):
    client = Claude()
    import_claim(conn, tmp_path, a, client)
    import_claim(conn, tmp_path, b, client)
    assert all("pieces" in c["output_config"]["format"]["schema"]["properties"] for c in client.calls)
    assert conn.execute("select count(distinct a.piece_id) from music_occurrences o join arrangements a on a.id = o.arrangement_id").fetchone()[0] == 2


def test_similar_numbered_works_by_one_composer_stay_distinct(conn, tmp_path):
    import_claim(conn, tmp_path, "Piano Concerto No. 1 by Composer")
    import_claim(conn, tmp_path, "Piano Concerto No. 2 by Composer")
    assert conn.execute("select count(distinct a.piece_id) from music_occurrences o join arrangements a on a.id = o.arrangement_id").fetchone()[0] == 2


def test_shared_performer_can_match_music_without_becoming_a_composer(conn, tmp_path):
    for raw in ("Human performed by Singer", "Human (cover) performed by Singer"):
        import_claim(conn, tmp_path, raw)
    assert conn.execute("select count(distinct a.piece_id) from music_occurrences o join arrangements a on a.id = o.arrangement_id").fetchone()[0] == 1
    assert conn.execute("select count(*) from piece_artists").fetchone()[0] == 0
    assert conn.execute("select distinct grade from music_occurrences").fetchall() == [("title only",)]


@pytest.mark.parametrize("verdict, count", [(True, 1), (False, 2)])
def test_differently_credited_occurrences_require_a_pair_verdict(conn, tmp_path, verdict, count):
    client = Claude()
    client.same_piece = verdict
    import_claim(conn, tmp_path, "Example by Composer", client)
    import_claim(conn, tmp_path, "Example performed by Singer", client)
    assert any("same_piece" in c["output_config"]["format"]["schema"]["properties"] for c in client.calls)
    assert conn.execute("select count(distinct a.piece_id) from music_occurrences o join arrangements a on a.id = o.arrangement_id").fetchone()[0] == count


def test_reimport_relinks_a_previously_split_performer_occurrence(conn, tmp_path):
    import_claim(conn, tmp_path, "Human performed by Singer")
    program, _ = import_claim(conn, tmp_path, "Human performed by Singer")
    duplicate = conn.execute("insert into pieces (title) values ('Human') returning id").fetchone()[0]
    arrangement = conn.execute("""insert into arrangements (piece_id, style_id, performer_id)
        select %s, style_id, performer_id from arrangements order by id limit 1 returning id""", [duplicate]).fetchone()[0]
    conn.execute("update music_occurrences set arrangement_id = %s where program_id = %s", [arrangement, program])
    run_import(conn, tmp_path)
    assert conn.execute("select count(distinct a.piece_id) from music_occurrences o join arrangements a on a.id = o.arrangement_id").fetchone()[0] == 1


def test_medley_titles_can_repeat_the_work_name_and_use_each_named_variation():
    raw = "Rhapsody on a Theme of Paganini Op. 43, Variations 11 & 8 by Sergei Rachmaninoff"
    parsed = {"title": "Rhapsody on a Theme of Paganini, Variation 8", "composers": ["Sergei Rachmaninoff"]}
    assert normalise.resolve(raw, parsed, {}, {})["title"] == "Rhapsody on a Theme of Paganini, Variation 8"
    assert normalise.resolve(raw, {**parsed, "title": "Rhapsody on a Theme of Paganini, Variation 99"}, {}, {}) is None


def test_twenty_original_entries_meet_the_precision_bar_with_the_known_role_error():
    sample = json.loads((pathlib.Path(__file__).parent / "pages/music/graded-entries.json").read_text())
    wrong = []
    for entry in sample["entries"]:
        parsed = entry["model_pieces"] or normalise.parse(entry["raw"])
        pieces = [normalise.resolve(entry["raw"], p, entry["title_qids"], sample["entities"]) for p in parsed]
        actual = [[p["title"], [c["name"] for c in p["composers"]], p["source"], p["performer"], p["grade"]]
                  for p in pieces if p]
        if actual != [entry["expected"]] or any(p and p["style"] != "original" for p in pieces):
            wrong.append(entry["id"])
    assert wrong == [6067]  # The model calls Rebotier a performer; the entry credits the composer.
    assert (len(sample["entries"]) - len(wrong)) / len(sample["entries"]) >= 0.95


def test_ten_original_merge_groups_retain_strict_evidence_guards(conn, tmp_path, site):
    from bs4 import BeautifulSoup
    sample = json.loads((pathlib.Path(__file__).parent / "pages/music/graded-merges.json").read_text())
    cells = json.loads((pathlib.Path(__file__).parent / "pages/music/context-cells.json").read_text())
    wire = {}
    for qid, entity in sample["entities"].items():
        wire[qid] = {"claims": {"P86": [{"mainsnak": {"datavalue": {"value": {"id": c["qid"]}}}}
                                         for c in entity["composers"]]}}
        for c in entity["composers"]:
            wire[c["qid"]] = {"labels": {"en": {"value": c["name"]}}}
    (site.root / "entities").write_text(json.dumps({"entities": wire}))
    for cached in sample["cache"]:
        conn.execute("insert into music_llm_cache (kind, raw_text, result, model) values (%s, %s, %s, %s)",
                     [cached["kind"], cached["raw_text"], Jsonb(cached["result"]), normalise.MODEL])
    owner = conn.execute("insert into skaters (name, nation) values ('Grading sample', 'USA') returning id").fetchone()[0]
    for i, entry in enumerate(e for g in sample["groups"] for e in g["entries"]):
        program = conn.execute("insert into programs (skater_id, season, segment_type) values (%s, %s, 'free skating') returning id",
                               [owner, 2004 + i]).fetchone()[0]
        entry["program"] = program
        raw = entry["raw"]
        if entry.get("cell"):
            extracted = wikipedia.music_entries(BeautifulSoup(cells[entry["cell"]]["html"], "html.parser").td)
            raw = next(e["raw"] for e in extracted if normalise.norm(e["raw"]).startswith(normalise.norm(entry.get("track", ""))))
        conn.execute("""insert into music_claims (program_id, origin, raw_text, article_title, revision, title_qids)
            values (%s, 'wikipedia', %s, 'Sample', 1, %s)""", [program, raw, Jsonb(entry["title_qids"])])
    client = Claude()
    run_import(conn, tmp_path, client, entity_endpoint=site.url + "/entities")
    assert len(client.calls) == 0, [json.loads(c["messages"][0]["content"]) for c in client.calls]
    expected = {758: 2, 814: 1, 2325: 1, 2907: 5, 59: 1, 2637: 2, 625: 1, 3843: 2, 3245: 1, 3768: 1}
    missed = []
    for group in sample["groups"]:
        count = conn.execute("""select count(distinct a.piece_id) from music_occurrences o
            join arrangements a on a.id = o.arrangement_id where o.program_id = any(%s)""",
            [[e["program"] for e in group["entries"]]]).fetchone()[0]
        assert count >= expected[group["id"]], f"false merge in {group['id']}"
        if count > expected[group["id"]]:
            missed.append(group["id"])
    assert len(missed) <= 1, f"missed duplicate groups: {missed}"
    run_import(conn, tmp_path, client, entity_endpoint=site.url + "/entities")
    assert len(client.calls) == 0, [json.loads(c["messages"][0]["content"]) for c in client.calls]


def test_wikidata_error_envelope_logs_a_problem_without_failing_import(conn, tmp_path, site):
    program, _ = import_claim(conn, tmp_path, "Tango by Composer")
    conn.execute("update music_claims set title_qids = %s where program_id = %s", [Jsonb({"Tango": "Q123"}), program])
    (site.root / "entities").write_text('{"error":{"code":"maxlag","info":"Waiting for replicas"}}')
    id = run_import(conn, tmp_path, entity_endpoint=site.url + "/entities")
    assert conn.execute("select kind from import_problems where import_id = %s", [id]).fetchall() == [("music Wikidata fetch failed",)]
