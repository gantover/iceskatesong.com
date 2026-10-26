"""Corrections file: the undo journal of its last replay, and music claims that can move between Programs.

Revision ID: 0008
Revises: 0007
"""

from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade() -> None:
    op.execute("""
        -- R1 only: the statements that put back what the last corrections replay moved or created (merges, hides,
        -- new records). The next Import deletes the corrections-origin rows, runs these in reverse id order, then replays the file.
        create table corrections_undo (
          id bigint generated always as identity primary key,
          statement text not null,
          params jsonb not null
        );

        -- A Skater merge moves a music claim to the survivor's Program, and its occurrences with it.
        alter table music_occurrences drop constraint music_occurrences_program_id_origin_fkey,
          add foreign key (program_id, origin) references music_claims on update cascade on delete cascade;
    """)


def downgrade() -> None:
    op.execute("""
        alter table music_occurrences drop constraint music_occurrences_program_id_origin_fkey,
          add foreign key (program_id, origin) references music_claims on delete cascade;
        drop table corrections_undo;
    """)
