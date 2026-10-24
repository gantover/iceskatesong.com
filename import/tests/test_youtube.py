import dataclasses
import datetime as dt
import json
import re
import urllib.error

import isu
import youtube
from conftest import PAGES
from test_import import problems, run_import

SAMPLE = json.loads((PAGES / "youtube/gpf2025.json").read_text())  # videos.list answers, 28 Nov to 20 Dec 2025


def gpf():
    """The Grand Prix Final 2025 from its cached pages; a Performance is named "<page> <name>"."""
    root = PAGES / "results/season2526/gpf2025"
    event = isu.parse_index(isu.decode((root / "index.htm").read_bytes()))
    segments = []
    for page in event.segment_pages:
        s = isu.parse_segment(isu.decode((root / page).read_bytes()))
        entries = [youtube.Entry(f"{page[:6]} {e.name}", e.name, e.nation, e.start_number) for e in s.entries]
        segments.append(youtube.Segment(s.discipline, s.level, s.segment_type, entries))
    return [youtube.Competition("gpf2025", event.name, event.city, event.start, event.end, segments)]


def video(title, published="2025-12-05", channel=youtube.SKATING_ISU, minutes=6):
    return youtube.Video("x", title, channel, dt.datetime.fromisoformat(published + "T12:00:00+00:00"), minutes * 60)


def sample_video(item):
    row = youtube.cache_row(item)
    return youtube.Video(*(row[f.name] for f in dataclasses.fields(youtube.Video)))


def test_every_per_skater_clip_of_the_sample_links_to_the_performance_its_title_names():
    competitions = gpf()
    # Read independently of the matcher: "Given SURNAME (NAT) | [Junior ]<Discipline> <Segment type> | Grand Prix Final 2025"
    clip = re.compile(r"^(.+?) \(([A-Z]{3})\) \| (Junior )?(Men|Women|Pairs|Ice Dance) (Short Program|Free Skating|Rhythm Dance|Free Dance) \| Grand Prix Final 2025")
    pages = {(s.discipline, s.level, s.segment_type): s.entries[0].performance_id[:6] for s in competitions[0].segments}
    clips = 0
    for item in SAMPLE:
        m = clip.match(item["snippet"]["title"])
        if not m:
            continue
        clips += 1
        name, nation, junior, discipline, segment_type = m.groups()
        page = pages[(discipline.lower(), "junior" if junior else "senior", segment_type.lower())]

        expected = [f"{page} {full}" for full in names(competitions, page, nation, name)]
        assert youtube.match(sample_video(item), competitions) == (expected, None), item
    assert clips == 96  # every Performance of the event


def names(competitions, page, nation, title_name):
    """The entries of that page and nation printed as the title prints them: a Skater's full name, a Team's surnames."""
    surnames = lambda n: [w for w in n.replace("/", " ").split() if w.isupper() and len(w) > 1]
    return [e.name for s in competitions[0].segments for e in s.entries
            if e.performance_id.startswith(page) and e.nation == nation
            and (e.name == title_name if " / " not in e.name else surnames(e.name) == surnames(title_name))]


def test_a_full_segment_stream_links_every_performance_of_its_segment():
    ids, reason = youtube.match(video("Men Free Skating | Grand Prix Final 2025 | #GPFigure", minutes=70), gpf())

    assert reason is None
    assert len(ids) == 6 and {i[:6] for i in ids} == {"SEG002"}  # senior: the title doesn't say junior
    ids, _ = youtube.match(video("Men Free Skating | Grand Prix Final 2025 | #JGPFigure", minutes=70), gpf())
    assert {i[:6] for i in ids} == {"SEG010"}


def test_a_skaters_n_to_m_stream_links_only_that_start_number_range():
    competitions = gpf()
    ids, reason = youtube.match(video("Men Free Skating Skaters 1–3 | Grand Prix Final 2025", minutes=40), competitions)

    assert reason is None
    assert sorted(ids) == sorted(e.performance_id for e in competitions[0].segments[1].entries if e.start_number <= 3)
    assert len(ids) == 3


def test_a_group_stream_without_a_range_and_practice_streams_are_not_linked():
    competitions = gpf()

    assert youtube.match(video("Men Free Skating Group 1 | Grand Prix Final 2025", minutes=40), competitions) == (
        [], "group stream without a start-number range")
    assert youtube.match(video("Men Free Skating Practice | Grand Prix Final 2025", minutes=40), competitions) is None


def test_a_title_naming_another_year_links_nothing():
    assert youtube.match(video("Ilia MALININ (USA) | Men Free Skating | Grand Prix Final 2024"), gpf()) is None


def test_a_title_without_a_year_needs_the_publishedat_window():
    title = "Ilia MALININ (USA) | Men Free Skating | Grand Prix Final"

    assert youtube.match(video(title), gpf()) == (["SEG002 Ilia MALININ"], None)
    assert youtube.match(video(title, published="2026-03-01"), gpf()) is None


def test_a_title_naming_no_event_is_logged_when_the_window_alone_finds_the_performance():
    assert youtube.match(video("Ilia MALININ (USA) | Men Free Skating | 2025"), gpf()) == (
        ["SEG002 Ilia MALININ"], "matched by the publishedAt window only")
    assert youtube.match(video("Ilia MALININ (USA) | Men Free Skating | 2025", published="2026-03-01"), gpf()) is None


def test_the_competition_is_named_by_its_city_or_its_type_alias():
    for title in ("Ilia MALININ (USA) | Men Free Skating | Nagoya 2025", "Ilia MALININ (USA) | Men FS | GP Final 2025"):
        assert youtube.match(video(title), gpf()) == (["SEG002 Ilia MALININ"], None), title


def test_surnames_match_without_accents_and_with_one_typo():
    competitions = gpf()

    assert youtube.match(video("Niccolò MACII / Sara CONTI (ITA) | Pairs SP | Grand Prix Final 2025"), competitions) == (
        ["SEG005 Sara CONTI / Niccolo MACII"], None)
    assert youtube.match(video("Mikhail SHAIDOROF (KAZ) | Men Short Program | Grand Prix Final 2025"), competitions) == (
        ["SEG001 Mikhail SHAIDOROV"], None)


def test_given_names_break_a_tie_and_an_unbroken_tie_is_logged():
    competitions = gpf()

    assert youtube.match(video("Yujae KIM (KOR) | Junior Women Free Skating | Grand Prix Final 2025"), competitions) == (
        ["SEG012 Yujae KIM"], None)
    ids, reason = youtube.match(video("KIM (KOR) | Junior Women Free Skating | Grand Prix Final 2025"), competitions)
    assert (sorted(ids), reason) == (["SEG012 Yujae KIM", "SEG012 Yuseong KIM"], "several entries match the title")


def test_the_junior_channel_is_junior_and_dance_words_map_to_dance_segments():
    competitions = gpf()

    assert youtube.match(video("ABOIAN / VESELUKHIN (USA) | Ice Dance Short Dance | Grand Prix Final 2025", channel=youtube.JGP),
                         competitions) == (["SEG015 Hana Maria ABOIAN / Daniil VESELUKHIN"], None)
    assert youtube.match(video("CHOCK / BATES (USA) | Ice Dance Free | Grand Prix Final 2025"), competitions) == (
        ["SEG008 Madison CHOCK / Evan BATES"], None)


def test_a_clip_without_a_segment_type_is_logged_and_short_or_skipped_videos_are_not_ours():
    competitions = gpf()

    assert youtube.match(video("Ilia MALININ (USA) | Men | Grand Prix Final 2025"), competitions) == ([], "no Segment type in the title")
    assert youtube.match(video("Ilia MALININ (USA) | Men Free Skating | Grand Prix Final 2025", minutes=1), competitions) is None
    assert youtube.match(video("Ilia MALININ (USA) | Men Winner Interview | Grand Prix Final 2025"), competitions) is None


def test_a_clip_without_a_discipline_word_is_picked_by_its_surnames():
    assert youtube.match(video("Ilia MALININ (USA) | Free Skating | Grand Prix Final 2025"), gpf()) == (["SEG002 Ilia MALININ"], None)
    assert youtube.match(video("CHOCK / BATES (USA) | Free | Grand Prix Final 2025"), gpf()) == (
        ["SEG008 Madison CHOCK / Evan BATES"], None)


class FakeApi:
    """Answers playlistItems and videos.list from `videos` (videos.list items), 50 per page; `calls` logs each request."""

    def __init__(self, videos):
        self.videos, self.calls = list(videos), []

    def __call__(self, path, **params):
        self.calls.append((path, params))
        if path == "playlistItems":
            ids = [v["id"] for v in self.videos if "UU" + v["snippet"]["channelId"][2:] == params["playlistId"]]
            start = int(params.get("pageToken", 0))
            more = {"nextPageToken": str(start + 50)} if start + 50 < len(ids) else {}
            return {"items": [{"contentDetails": {"videoId": i}} for i in ids[start:start + 50]], **more}
        wanted = params["id"].split(",")
        assert len(wanted) <= 50
        return {"items": [v for v in self.videos if v["id"] in wanted]}

    def listed(self):
        return [i for path, params in self.calls if path == "videos" for i in params["id"].split(",")]


def links(conn):
    return conn.execute("""select count(*), count(start_seconds), count(*) filter (where status = 'hidden')
                           from performance_videos""").fetchone()


def test_an_import_links_the_sample_clips_and_streams_once(conn, site, tmp_path):
    api = FakeApi(SAMPLE)
    status, counts, _ = run_import(conn, site, tmp_path, youtube_api=api)

    assert status == "succeeded"
    # 96 clips, and 15 streams untimed to their Segment's 6 Performances
    assert counts["performance video"] == {"created": 96 + 15 * 6, "updated": 0}
    assert links(conn) == (186, 0, 0)
    assert conn.execute("select count(*) from youtube_videos").fetchone() == (len(SAMPLE),)
    assert problems(conn, youtube.NO_MATCH) == [
        v["id"] for v in SAMPLE if v["snippet"]["title"].startswith("Junior Ice Dance Rhythm Dance | Grand Prix 2025")]

    status, counts, _ = run_import(conn, site, tmp_path, youtube_api=api)

    assert (status, counts) == ("succeeded", {})
    assert links(conn) == (186, 0, 0)


def test_a_hidden_link_stays_hidden_after_a_reimport(conn, site, tmp_path):
    api = FakeApi(SAMPLE)
    run_import(conn, site, tmp_path, youtube_api=api)
    conn.execute("""update performance_videos set status = 'hidden' where youtube_id in (select youtube_id from youtube_videos
                    where title like 'Men Free Skating |%%' or title like 'Ilia MALININ (USA) | Men Free%%')""")
    assert links(conn) == (186, 0, 7)

    run_import(conn, site, tmp_path, youtube_api=api)

    assert links(conn) == (186, 0, 7)


def test_cache_rows_older_than_25_days_are_refreshed_and_vanished_videos_leave_the_cache(conn, site, tmp_path):
    api = FakeApi(SAMPLE)
    run_import(conn, site, tmp_path, youtube_api=api)
    stale, fresh, gone = (v["id"] for v in SAMPLE[:3])
    conn.execute("update youtube_videos set refreshed_at = now() - interval '26 days', title = 'old' where youtube_id = %s", [stale])
    conn.execute("update youtube_videos set refreshed_at = now() - interval '10 days' where youtube_id = %s", [fresh])
    api.videos = [v for v in SAMPLE if v["id"] != gone]
    api.calls.clear()

    run_import(conn, site, tmp_path, youtube_api=api)

    assert api.listed() == [stale]
    assert conn.execute("select title, refreshed_at > now() - interval '1 minute' from youtube_videos where youtube_id = %s",
                        [stale]).fetchone() == (SAMPLE[0]["snippet"]["title"], True)
    assert conn.execute("select count(*) from youtube_videos where youtube_id = %s", [gone]).fetchone() == (0,)


def test_cache_rows_past_30_days_leave_the_cache_on_an_import_without_a_fetch_and_their_links_stay(conn, site, tmp_path):
    run_import(conn, site, tmp_path, youtube_api=FakeApi(SAMPLE))
    old = SAMPLE[0]["id"]
    conn.execute("update youtube_videos set refreshed_at = now() - interval '31 days' where youtube_id = %s", [old])

    run_import(conn, site, tmp_path)  # no YOUTUBE_API_KEY

    assert conn.execute("select count(*) from youtube_videos").fetchone() == (len(SAMPLE) - 1,)
    assert conn.execute("select count(*) from youtube_videos where youtube_id = %s", [old]).fetchone() == (0,)
    assert links(conn) == (186, 0, 0)


def test_a_failed_youtube_fetch_is_a_problem_and_keeps_the_cache(conn, site, tmp_path):
    run_import(conn, site, tmp_path, youtube_api=FakeApi(SAMPLE))

    def down(path, **params):
        raise urllib.error.URLError("no network")

    status, _, _ = run_import(conn, site, tmp_path, youtube_api=down)

    assert status == "succeeded"
    assert problems(conn, "fetch failed") == [youtube.API + "playlistItems"]
    assert conn.execute("select count(*) from youtube_videos").fetchone() == (len(SAMPLE),)
    assert links(conn) == (186, 0, 0)


def test_the_api_key_goes_in_a_header_never_in_a_url_or_a_problem(conn, site, tmp_path):
    status, _, _ = run_import(conn, site, tmp_path, youtube_api=youtube.api("SECRET", base=f"{site.url}/youtube/v3/"))

    assert status == "succeeded"
    assert [path for _, path, _ in site.log if path.startswith("/youtube/")] == [
        f"/youtube/v3/playlistItems?part=contentDetails&playlistId=UU{youtube.SKATING_ISU[2:]}&maxResults=50"]
    assert "SECRET" not in str(conn.execute("select * from import_problems").fetchall())
