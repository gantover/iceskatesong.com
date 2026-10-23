import main


def test_startup_marks_a_running_import_failed_interrupted(conn):
    conn.execute("insert into imports (status) values ('running'), ('succeeded')")

    main.mark_interrupted(conn)

    assert conn.execute("select status, error from imports order by id").fetchall() == [
        ("failed", "interrupted"), ("succeeded", None)]


def test_claim_takes_the_oldest_pending_import_only(conn):
    conn.execute("insert into imports default values")
    conn.execute("insert into imports default values")

    assert main.claim(conn) == 1
    assert conn.execute("select status from imports order by id").fetchall() == [("running",), ("pending",)]


def test_claim_finds_nothing_without_a_pending_import(conn):
    conn.execute("insert into imports (status) values ('failed')")

    assert main.claim(conn) is None
