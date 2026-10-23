"""Import: job rows, problems, page cache index, keys, names, and the ISU-created records

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.execute("""
        create table imports (
          id bigint generated always as identity primary key,
          status text not null default 'pending'
            check (status in ('pending', 'running', 'succeeded', 'failed')),
          created_at timestamptz not null default now(),
          started_at timestamptz,
          finished_at timestamptz,
          -- {"skater": {"created": n, "updated": n}, ...}
          counts jsonb not null default '{}',
          problem_count int not null default 0,
          error text
        );

        create table import_problems (
          id bigint generated always as identity primary key,
          import_id bigint not null references imports on delete cascade,
          step text not null,
          kind text not null,
          key text not null,
          detail jsonb not null default '{}'
        );
        create index on import_problems (import_id);

        create table fetched_pages (
          url text primary key,
          etag text,
          last_modified text,
          fetched_at timestamptz not null,
          body_sha256 text not null
        );

        -- Polymorphic (ADR 0002): no foreign key, so the code writing these keeps
        -- (entity, entity_id) valid and merges move them in the same transaction.
        create table keys (
          system text not null,
          value text not null,
          entity text not null,
          entity_id bigint not null,
          primary key (system, value)
        );
        create index on keys (entity, entity_id);

        create table names (
          entity text not null,
          entity_id bigint not null,
          name text not null,
          origin text not null,
          primary key (entity, entity_id, name, origin)
        );

        create table competitions (
          id bigint generated always as identity primary key,
          name text not null,
          city text not null,
          start_date date not null,
          end_date date not null,
          level text not null check (level in ('senior', 'junior'))
        );

        create table segments (
          id bigint generated always as identity primary key,
          competition_id bigint not null references competitions,
          discipline text not null check (discipline in ('men', 'women', 'pairs', 'ice dance')),
          level text not null check (level in ('senior', 'junior')),
          segment_type text not null check (segment_type in ('short program', 'free skating',
            'short dance', 'rhythm dance', 'free dance', 'original dance', 'compulsory dance')),
          -- '' for the main round; else e.g. 'qualifying group a' or 'team'
          round text not null default '',
          url text not null,
          unique (competition_id, discipline, level, segment_type, round)
        );

        create table skaters (
          id bigint generated always as identity primary key,
          name text not null,
          -- Nation printed when the Skater was created; matches Team members to Skaters.
          nation text not null
        );

        create table teams (
          id bigint generated always as identity primary key,
          name text not null,
          skater1_id bigint not null references skaters,
          skater2_id bigint not null references skaters
        );

        create table programs (
          id bigint generated always as identity primary key,
          skater_id bigint references skaters,
          team_id bigint references teams,
          season int not null,
          segment_type text not null check (segment_type in ('short program', 'free skating',
            'short dance', 'rhythm dance', 'free dance', 'original dance', 'compulsory dance')),
          seq int not null default 1,
          check (num_nonnulls(skater_id, team_id) = 1),
          unique nulls not distinct (skater_id, team_id, season, segment_type, seq)
        );

        create table performances (
          id bigint generated always as identity primary key,
          segment_id bigint not null references segments,
          -- As printed: the ISU ID, else name + nation
          entry_key text not null,
          -- Links are set on insert only (ADR 0002)
          skater_id bigint references skaters,
          team_id bigint references teams,
          program_id bigint not null references programs,
          rank int,
          tss numeric(6, 2),
          tes numeric(6, 2),
          pcs numeric(6, 2),
          deductions numeric(5, 2),
          start_number int,
          name text not null,
          nation text not null,
          gone boolean not null default false,
          check (num_nonnulls(skater_id, team_id) = 1),
          unique (segment_id, entry_key)
        );
        create index on performances (skater_id);
        create index on performances (team_id);
        create index on performances (program_id);
    """)
