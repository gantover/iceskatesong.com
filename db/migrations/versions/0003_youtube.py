"""YouTube: the 30-day API cache and Performance videos

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.execute("""
        -- YouTube Data API answers, refreshed by the Import when older than 25 days (the API terms allow 30).
        -- Only performance_videos.youtube_id outlives a row here.
        create table youtube_videos (
          youtube_id text primary key,
          title text not null,
          channel_id text not null,
          published_at timestamptz not null,
          duration_seconds int not null,
          blocked_regions text[] not null default '{}',
          -- null: every region not blocked
          allowed_regions text[],
          embeddable boolean not null,
          made_for_kids boolean not null,
          refreshed_at timestamptz not null
        );
        create index on youtube_videos (refreshed_at);

        create table performance_videos (
          id bigint generated always as identity primary key,
          -- No foreign key: the cache row may be gone, the link stays.
          youtube_id text not null,
          -- null: an untimed full-segment stream
          start_seconds int,
          performance_id bigint not null references performances,
          origin text not null check (origin in ('official', 'admin', 'submitted')),
          status text not null default 'active' check (status in ('active', 'hidden')),
          unique nulls not distinct (youtube_id, start_seconds, performance_id)
        );
        create index on performance_videos (performance_id);
    """)
