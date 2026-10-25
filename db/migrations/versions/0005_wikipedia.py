"""Raw music claims with Wikipedia revision attribution.

Revision ID: 0005
Revises: 0004
"""

from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.execute("""
        create table music_claims (
          program_id bigint not null references programs,
          origin text not null check (origin in ('admin', 'corrections', 'submitted', 'wikipedia', 'isu')),
          raw_text text not null,
          article_title text,
          revision bigint,
          -- Wikipedia link title -> Wikidata QID, evidence for the later normaliser.
          title_qids jsonb not null default '{}',
          primary key (program_id, origin),
          check (origin <> 'wikipedia' or (article_title is not null and revision is not null))
        );
    """)


def downgrade() -> None:
    op.execute("drop table music_claims")
