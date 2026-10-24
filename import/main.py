"""Import service: polls for a `pending` Import, fetches the ISU pages and the Wikidata crosswalk into the cache, then applies them."""

import os
import pathlib
import signal
import sys
import time
import traceback

import psycopg
from psycopg.types.json import Jsonb

import apply
import fetch
import isu
import wikidata
import youtube

POLL_SECONDS = 30
# Admin edits (R2) take the same lock, so they never interleave with an apply phase.
IMPORT_LOCK = "select pg_advisory_xact_lock(hashtext('import'))"
MAX_FAILED_FETCHES = 0.2
KEEP_PROBLEMS_OF_LAST = 10


class ImportFailed(Exception):
    pass


def read_events(events_file: pathlib.Path) -> list[str]:
    lines = (line.strip() for line in events_file.read_text().splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def mark_interrupted(conn) -> None:
    conn.execute("update imports set status = 'failed', error = 'interrupted', finished_at = now() where status = 'running'")


def claim(conn) -> int | None:
    """Atomically move the oldest `pending` Import to `running`; committed before the run starts."""
    row = conn.execute(
        """update imports set status = 'running', started_at = now()
           where id = (select id from imports where status = 'pending' order by id limit 1 for update skip locked)
           returning id"""
    ).fetchone()
    return row and row[0]


def run(conn, import_id: int, events_file: pathlib.Path, cache_dir: pathlib.Path, contact: str, interval=1.0,
        wikidata_endpoint: str | None = None, youtube_api=None) -> None:
    """Run one claimed Import to `succeeded` or `failed`. `conn` must be in autocommit mode. No `wikidata_endpoint`: no Wikidata step.
    No `youtube_api` (a `youtube.api` GET): no YouTube fetch, and videos are matched from the cache as it is."""
    problems: list[dict] = []
    try:
        if not contact:
            raise ImportFailed("IMPORT_CONTACT_EMAIL is not set: the crawl must name a contact")
        urls = read_events(events_file)
        fetcher = fetch.Fetcher(conn, cache_dir, f"iceskatesong-import/1.0 ({contact})", interval=interval)
        for url in urls:
            body = fetcher.get(url)
            try:
                pages = isu.parse_index(isu.decode(body)).segment_pages if body else []
            except Exception:
                pages = []  # logged by the apply phase
            for page in pages:
                fetcher.get(*apply.page_urls(url, page))
        if wikidata_endpoint:
            wikidata_bodies = wikidata.fetch(fetcher, wikidata_endpoint, import_id)
        problems += [{"step": "fetch", "kind": "fetch failed", "key": url, "detail": {"error": error}}
                     for url, error in fetcher.failures]
        if len(fetcher.failures) > MAX_FAILED_FETCHES * fetcher.fetches:
            raise ImportFailed(f"{len(fetcher.failures)} of {fetcher.fetches} fetches failed")
        if youtube_api:
            youtube.fetch(conn, youtube_api, problems)

        with conn.transaction():
            conn.execute(IMPORT_LOCK)
            counts = apply.Apply(conn, problems).run(urls, lambda url: fetch.read_cached(cache_dir, url))
            if wikidata_endpoint:
                counts |= wikidata.run(conn, wikidata_bodies, problems)
            counts |= youtube.link(conn, problems)  # after the ISU apply: links only to Performances that exist
            finish(conn, import_id, "succeeded", problems, counts=counts)
    except Exception as e:
        with conn.transaction():
            finish(conn, import_id, "failed", problems, error=str(e))
        if not isinstance(e, (ImportFailed, psycopg.Error)):
            traceback.print_exc()


def finish(conn, import_id: int, status: str, problems: list[dict], counts=None, error=None) -> None:
    conn.execute(
        """update imports set status = %s, finished_at = now(), counts = %s, problem_count = %s, error = %s
           where id = %s""",
        [status, Jsonb(counts or {}), len(problems), error, import_id],
    )
    with conn.cursor() as cur:
        cur.executemany(
            "insert into import_problems (import_id, step, kind, key, detail) values (%s, %s, %s, %s, %s)",
            [(import_id, p["step"], p["kind"], p["key"], Jsonb(p["detail"])) for p in problems],
        )
    conn.execute(
        "delete from import_problems where import_id not in (select id from imports order by id desc limit %s)",
        [KEEP_PROBLEMS_OF_LAST],
    )


def main() -> None:
    # As PID 1 the default SIGTERM handler is ignored, so exit explicitly on `docker compose stop`.
    # A run cut short this way stays `running` and is marked "interrupted" on the next start.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    here = pathlib.Path(__file__).parent
    events_file, cache_dir = here / "events.txt", here / "cache"  # cache/ is a Docker volume
    contact = os.environ.get("IMPORT_CONTACT_EMAIL", "")
    youtube_key = os.environ.get("YOUTUBE_API_KEY", "")
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as conn:
        mark_interrupted(conn)
        print("import: waiting for a pending Import", flush=True)
        while True:
            import_id = claim(conn)
            if import_id:
                print(f"import: running Import {import_id}", flush=True)
                run(conn, import_id, events_file, cache_dir, contact, wikidata_endpoint=wikidata.ENDPOINT,
                    youtube_api=youtube_key and youtube.api(youtube_key))
                print(f"import: Import {import_id} finished", flush=True)
            else:
                time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
