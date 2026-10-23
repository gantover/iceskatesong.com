"""Search extensions: pg_trgm, unaccent and the IMMUTABLE f_unaccent wrapper

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    # unaccent() is only STABLE, so generated columns and indexes go through
    # this wrapper, which pins the dictionary schema-qualified.
    op.execute("""
        create extension if not exists pg_trgm;
        create extension if not exists unaccent;

        create function f_unaccent(text) returns text
          language sql immutable parallel safe strict
          return public.unaccent('public.unaccent'::regdictionary, $1);
    """)
