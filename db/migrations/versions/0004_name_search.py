"""Name search: a trigram-indexed search_key on names

Revision ID: 0004
Revises: 0003
"""

from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    # names holds every Skater and Team display name (the Import writes it as an 'isu' name) plus every alias,
    # so this one column searches both.
    op.execute("""
        alter table names add column search_key text generated always as (f_unaccent(lower(name))) stored;
        create index on names using gin (search_key gin_trgm_ops);
    """)
