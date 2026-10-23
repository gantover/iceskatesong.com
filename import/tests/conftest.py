"""A throwaway database in the Compose Postgres, migrated by Alembic, and a local server for the cached pages."""

import functools
import http.server
import os
import pathlib
import shutil
import subprocess
import threading
import time

import psycopg
import pytest

ROOT = pathlib.Path(__file__).parents[2]
PAGES = pathlib.Path(__file__).parent / "pages"


def base_url() -> str:
    if url := os.environ.get("DATABASE_URL"):
        return url
    # .env.example's dev default: a git worktree has no .env.
    for env in (ROOT / ".env", ROOT / ".env.example"):
        for line in env.read_text().splitlines() if env.exists() else []:
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("DATABASE_URL is not set")


@pytest.fixture(scope="session")
def database_url():
    base = base_url()
    name = f"test_import_{os.getpid()}_{int(time.time())}"
    with psycopg.connect(base, autocommit=True) as admin:
        admin.execute(f"create database {name}")
        url = base.rsplit("/", 1)[0] + "/" + name
        try:
            subprocess.run(["uv", "run", "--project", ROOT / "db", "alembic", "-c", ROOT / "db/alembic.ini", "upgrade", "head"],
                           env={**os.environ, "DATABASE_URL": url}, check=True, capture_output=True)
            yield url
        finally:
            admin.execute(f"drop database {name} with (force)")


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("""truncate imports, import_problems, fetched_pages, keys, names, competitions, segments,
                        skaters, teams, programs, performances restart identity cascade""")
        yield conn


class Handler(http.server.SimpleHTTPRequestHandler):
    def log_request(self, code="-", size="-"):
        self.server.log.append((self.command, self.path, str(int(code))))

    def log_message(self, format, *args):
        pass


@pytest.fixture
def site(tmp_path):
    """Serves a copy of tests/pages (tests may edit it). `site.url`, `site.root`, `site.log` of (method, path, status)."""
    root = tmp_path / "site"
    shutil.copytree(PAGES, root)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=root))
    server.log, server.root = [], root
    server.url = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server
    server.shutdown()
