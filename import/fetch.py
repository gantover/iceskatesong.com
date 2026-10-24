"""Polite conditional GETs into a gzipped page cache indexed by `fetched_pages`."""

import gzip
import hashlib
import http.client
import os
import pathlib
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


def cache_path(cache_dir: pathlib.Path, url: str) -> pathlib.Path:
    parts = urlsplit(url)
    # Every query to an endpoint shares its path; a short hash of the query string tells them apart.
    query = "-" + hashlib.sha256(parts.query.encode()).hexdigest()[:16] if parts.query else ""
    return cache_dir / parts.netloc.replace(":", "_") / (parts.path.lstrip("/") + query + ".gz")


def read_cached(cache_dir: pathlib.Path, url: str) -> bytes | None:
    path = cache_path(cache_dir, url)
    return gzip.decompress(path.read_bytes()) if path.exists() else None


class Fetcher:
    """One request at a time, at most one per `interval` seconds per host, `attempts` tries per URL.

    `get` returns the cached body (fresh, or the old copy when every try failed), or None.
    `conn` is an autocommit connection: the fetch phase runs outside any transaction.
    """

    def __init__(self, conn, cache_dir: pathlib.Path, user_agent: str, interval=1.0, attempts=3):
        self.conn, self.cache_dir, self.user_agent = conn, cache_dir, user_agent
        self.interval, self.attempts = interval, attempts
        self.last_request: dict[str, float] = {}
        self.fetches = 0
        self.failures: list[tuple[str, str]] = []  # (url, last error)

    def get(self, url: str, *alternatives: str, timeout=30) -> bytes | None:
        """When the host has no `url` (404), tries each of `alternatives` in turn instead."""
        self.fetches += 1
        path = cache_path(self.cache_dir, url)
        headers = {"User-Agent": self.user_agent}
        row = self.conn.execute("select etag, last_modified from fetched_pages where url = %s", [url]).fetchone()
        # Without the cached body a 304 would leave nothing to parse, so only ask conditionally when it exists.
        if row and path.exists():
            if row[0]:
                headers["If-None-Match"] = row[0]
            if row[1]:
                headers["If-Modified-Since"] = row[1]
        error = ""
        for _ in range(self.attempts):
            self._wait(url)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
                    self._store(url, path, response.read(), response.headers)
                break
            except urllib.error.HTTPError as e:
                if e.code == 304:
                    break
                if e.code == 404 and alternatives:
                    self.fetches -= 1  # one page: count it once in the failure ratio
                    return self.get(*alternatives, timeout=timeout)
                error = f"HTTP {e.code}"
            except (OSError, http.client.HTTPException) as e:  # URLError, timeouts, resets, truncated bodies
                error = repr(e)
        else:
            self.failures.append((url, error))
        return read_cached(self.cache_dir, url)

    def _wait(self, url: str) -> None:
        host = urlsplit(url).netloc
        delay = self.last_request.get(host, 0) + self.interval - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self.last_request[host] = time.monotonic()

    def _store(self, url, path: pathlib.Path, body: bytes, headers) -> None:
        # Body first, atomically; the row (with its validators) only once the body is in place.
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(body))
        os.replace(tmp, path)
        self.conn.execute(
            """insert into fetched_pages (url, etag, last_modified, fetched_at, body_sha256)
               values (%s, %s, %s, now(), %s)
               on conflict (url) do update set etag = excluded.etag, last_modified = excluded.last_modified,
                 fetched_at = excluded.fetched_at, body_sha256 = excluded.body_sha256""",
            [url, headers.get("ETag"), headers.get("Last-Modified"), hashlib.sha256(body).hexdigest()],
        )
