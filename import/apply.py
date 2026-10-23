"""Apply phase: re-parse every cached ISU page into Competitions, Segments, Skaters, Teams, Programs and Performances.

Runs inside the caller's transaction, which holds the Import advisory lock. Follows ADR 0002: records are
found by key; Skater/Team and Program links on a Performance are set on insert only; slugs never change.
"""

import collections
import re
import unicodedata
from typing import Callable
from urllib.parse import urljoin, urlsplit

import isu

TEAM_DISCIPLINES = ("pairs", "ice dance")
JUNIOR_EVENT_CODES = ("jgp", "wjc", "yog", "wyog")  # Junior Grand Prix (and Final), Junior Worlds, Youth Olympics


class Apply:
    def __init__(self, conn, problems: list[dict]):
        self.conn, self.problems = conn, problems
        self.counts = collections.defaultdict(lambda: {"created": 0, "updated": 0})

    def problem(self, kind: str, key: str, **detail) -> None:
        self.problems.append({"step": "isu", "kind": kind, "key": key, "detail": detail})

    def one(self, query: str, params=()):
        row = self.conn.execute(query, params).fetchone()
        return row and row[0]

    def run(self, event_urls: list[str], read: Callable[[str], bytes | None]) -> dict:
        segments = []
        for url in event_urls:
            body = read(url)
            if body is None:
                continue  # never fetched: the fetch phase logged it
            try:
                event = isu.parse_index(isu.decode(body))
            except Exception as e:  # the parser is pure: any error is this page's, never the run's
                self.problem("parse failed", url, error=str(e))
                continue
            competition_id = self.competition(url, event)
            seen = set()
            for page in event.segment_pages:
                page_url = urljoin(url, page)
                body = read(page_url)
                if body is None:
                    continue
                try:
                    segment = isu.parse_segment(isu.decode(body))
                except isu.Skipped:
                    continue
                except Exception as e:
                    self.problem("parse failed", page_url, error=str(e))
                    continue
                key = (segment.discipline, segment.level, segment.segment_type, segment.round)
                if key in seen:  # would merge two pages' entries into one Segment
                    self.problem("parse failed", page_url, error=f"second page for Segment {key}")
                    continue
                seen.add(key)
                if event_level(url) == "junior":  # Youth Olympics captions don't say "Junior"
                    segment.level = "junior"
                segments.append((competition_id, season(event), page_url, segment))
        # Singles first, so Team members match the Skaters their singles entries created.
        for args in sorted(segments, key=lambda s: s[3].discipline in TEAM_DISCIPLINES):
            self.segment(*args)
        return dict(self.counts)

    def competition(self, url: str, event: isu.Event) -> int:
        path = event_path(url)
        fields = [event.name, event.city, event.start, event.end, event_level(url)]
        competition_id = self.one("select entity_id from keys where system = 'isu-event' and value = %s", [path])
        if competition_id:
            if self.one("""update competitions set name = %s, city = %s, start_date = %s, end_date = %s, level = %s
                           where id = %s and (name, city, start_date, end_date, level) is distinct from (%s, %s, %s, %s, %s)
                           returning id""", [*fields, competition_id, *fields]):
                self.counts["competition"]["updated"] += 1
            return competition_id
        competition_id = self.one("""insert into competitions (name, city, start_date, end_date, level)
                                     values (%s, %s, %s, %s, %s) returning id""", fields)
        self.key("isu-event", path, "competition", competition_id)
        self.slug(path.rsplit("/", 1)[-1], "competition", competition_id)
        self.counts["competition"]["created"] += 1
        return competition_id

    def segment(self, competition_id: int, season_: int, url: str, segment: isu.Segment) -> None:
        natural = [competition_id, segment.discipline, segment.level, segment.segment_type, segment.round]
        segment_id = self.one("""select id from segments where competition_id = %s and discipline = %s and level = %s
                                 and segment_type = %s and round = %s""", natural)
        if not segment_id:
            segment_id = self.one("""insert into segments (competition_id, discipline, level, segment_type, round, url)
                                     values (%s, %s, %s, %s, %s, %s) returning id""", [*natural, url])
            self.counts["segment"]["created"] += 1
        elif self.one("update segments set url = %s where id = %s and url <> %s returning id", [url, segment_id, url]):
            self.counts["segment"]["updated"] += 1

        for entry in segment.entries:
            self.performance(segment_id, season_, segment, entry)

        for (key,) in self.conn.execute(
            """update performances set gone = true where segment_id = %s and not gone and entry_key <> all(%s)
               returning entry_key""", [segment_id, [e.key for e in segment.entries]]
        ):
            self.counts["performance"]["updated"] += 1
            self.problem("vanished import key", key, segment=url)

    def performance(self, segment_id: int, season_: int, segment: isu.Segment, entry: isu.Entry) -> None:
        fields = [entry.rank, entry.tss, entry.tes, entry.pcs, entry.deductions, entry.start_number, entry.name, entry.nation]
        performance_id = self.one("select id from performances where segment_id = %s and entry_key = %s", [segment_id, entry.key])
        if performance_id:
            if self.one("""update performances set rank = %s, tss = %s, tes = %s, pcs = %s, deductions = %s,
                             start_number = %s, name = %s, nation = %s, gone = false
                           where id = %s and (rank, tss, tes, pcs, deductions, start_number, name, nation, gone)
                             is distinct from (%s, %s, %s, %s, %s, %s, %s, %s, false)
                           returning id""", [*fields, performance_id, *fields]):
                self.counts["performance"]["updated"] += 1
            return

        if segment.discipline in TEAM_DISCIPLINES:
            skater_id, team_id = None, self.team(entry)
        else:
            skater_id, team_id = self.skater(entry.isu_id, entry.name, entry.nation), None
        program = [skater_id, team_id, season_, segment.segment_type]
        program_id = self.one("""select id from programs where skater_id is not distinct from %s
                                 and team_id is not distinct from %s and season = %s and segment_type = %s and seq = 1""", program)
        if not program_id:
            program_id = self.one("""insert into programs (skater_id, team_id, season, segment_type)
                                     values (%s, %s, %s, %s) returning id""", program)
            self.counts["program"]["created"] += 1
        self.conn.execute(
            """insert into performances (segment_id, entry_key, skater_id, team_id, program_id,
                 rank, tss, tes, pcs, deductions, start_number, name, nation)
               values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            [segment_id, entry.key, skater_id, team_id, program_id, *fields],
        )
        self.counts["performance"]["created"] += 1

    def skater(self, isu_id: str | None, name: str, nation: str) -> int:
        skater_id = (self.one("select entity_id from keys where system = 'isu' and value = %s and entity = 'skater'", [isu_id])
                     if isu_id else self.match_skater(name, nation))
        if not skater_id:
            skater_id = self.create_skater(name, nation)
            if isu_id:
                self.key("isu", isu_id, "skater", skater_id)
        self.name("skater", skater_id, name)
        return skater_id

    def match_skater(self, name: str, nation: str) -> int | None:
        """A Skater with this normalised name (any alias) and nationality."""
        return self.one("""select s.id from skaters s join names n on n.entity = 'skater' and n.entity_id = s.id
                           where s.nation = %s and lower(f_unaccent(n.name)) = lower(f_unaccent(%s))
                           order by s.id limit 1""", [nation, name])

    def create_skater(self, name: str, nation: str) -> int:
        skater_id = self.one("insert into skaters (name, nation) values (%s, %s) returning id", [name, nation])
        self.slug(name, "skater", skater_id)
        self.counts["skater"]["created"] += 1
        return skater_id

    def team(self, entry: isu.Entry) -> int:
        team_id = entry.isu_id and self.one(
            "select entity_id from keys where system = 'isu' and value = %s and entity = 'team'", [entry.isu_id])
        if not team_id:
            # ISU Team IDs don't link to the Skaters: match members by normalised name + nationality.
            members = []
            for name in entry.name.split(" / "):
                skater_id = self.match_skater(name, entry.nation)
                if not skater_id:
                    skater_id = self.create_skater(name, entry.nation)
                    self.problem("Team member created", name, team=entry.name, nation=entry.nation)
                self.name("skater", skater_id, name)
                members.append(skater_id)
            if not entry.isu_id:
                team_id = self.one("select id from teams where skater1_id = %s and skater2_id = %s", members)
            if not team_id:
                team_id = self.one("insert into teams (name, skater1_id, skater2_id) values (%s, %s, %s) returning id",
                                   [entry.name, *members])
                if entry.isu_id:
                    self.key("isu", entry.isu_id, "team", team_id)
                self.slug(entry.name, "team", team_id)
                self.counts["team"]["created"] += 1
        self.name("team", team_id, entry.name)
        return team_id

    def name(self, entity: str, entity_id: int, name: str) -> None:
        self.conn.execute("insert into names (entity, entity_id, name, origin) values (%s, %s, %s, 'isu') on conflict do nothing",
                          [entity, entity_id, name])

    def key(self, system: str, value: str, entity: str, entity_id: int) -> None:
        self.conn.execute("insert into keys (system, value, entity, entity_id) values (%s, %s, %s, %s)",
                          [system, value, entity, entity_id])

    def slug(self, text: str, entity: str, entity_id: int) -> None:
        base = slugify(text)
        slug, n = base, 1
        while self.one("select 1 from keys where system = 'slug' and value = %s", [slug]):
            n += 1
            slug = f"{base}-{n}"
        self.key("slug", slug, entity, entity_id)


def event_path(url: str) -> str:
    """The Competition key: the event's path on the results host, e.g. season2526/gpf2025."""
    return urlsplit(url).path.removeprefix("/results/").removesuffix("/index.htm")


def event_level(url: str) -> str:
    return "junior" if event_path(url).rsplit("/", 1)[-1].startswith(JUNIOR_EVENT_CODES) else "senior"


def slugify(text: str) -> str:
    ascii_ = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_.lower()).strip("-") or "x"


def season(event: isu.Event) -> int:
    """A Season is named by its start year and runs July to June."""
    return event.start.year if event.start.month >= 7 else event.start.year - 1
