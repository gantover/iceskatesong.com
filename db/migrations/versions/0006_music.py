"""Pieces, ordered graded music occurrences and the raw-string LLM cache.

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.execute("""
        alter table music_claims add column entries jsonb not null default '[]';
        create table artists (
          id bigint generated always as identity primary key,
          name text not null,
          search_key text generated always as (f_unaccent(lower(name))) stored
        );
        create index on artists using gin (search_key gin_trgm_ops);
        create table sources (
          id bigint generated always as identity primary key,
          name text not null,
          search_key text generated always as (f_unaccent(lower(name))) stored
        );
        create index on sources using gin (search_key gin_trgm_ops);
        create table pieces (
          id bigint generated always as identity primary key,
          title text not null,
          source_id bigint references sources,
          search_key text generated always as (f_unaccent(lower(title))) stored
        );
        create index on pieces using gin (search_key gin_trgm_ops);
        create unique index one_music_qid on keys (entity, entity_id)
          where system = 'wikidata' and entity in ('piece', 'artist', 'source');
        create table piece_artists (
          piece_id bigint not null references pieces,
          artist_id bigint not null references artists,
          origin text not null,
          primary key (piece_id, artist_id, origin)
        );
        create table styles (
          id bigint generated always as identity primary key,
          slug text not null unique
        );
        create table genres (
          id bigint generated always as identity primary key,
          slug text not null unique
        );
        create table piece_genres (
          piece_id bigint not null references pieces,
          genre_id bigint not null references genres,
          origin text not null,
          primary key (piece_id, genre_id, origin)
        );
        create table arrangements (
          id bigint generated always as identity primary key,
          piece_id bigint not null references pieces,
          style_id bigint not null references styles,
          performer_id bigint references artists,
          unique nulls not distinct (piece_id, style_id, performer_id)
        );
        create table music_occurrences (
          program_id bigint not null,
          origin text not null,
          position int not null check (position >= 0),
          arrangement_id bigint not null references arrangements,
          grade text not null check (grade in ('identified', 'credited', 'title only')),
          raw_text text not null,
          primary key (program_id, origin, position),
          foreign key (program_id, origin) references music_claims on delete cascade
        );
        create index on music_occurrences (arrangement_id);
        create table music_llm_cache (
          kind text not null default 'parse' check (kind in ('parse', 'pair')),
          raw_text text not null,
          result jsonb not null,
          model text not null,
          created_at timestamptz not null default now(),
          primary key (kind, raw_text)
        );
    """)


def downgrade() -> None:
    op.execute("""
        drop table music_llm_cache, music_occurrences, arrangements, piece_genres, genres, styles,
          piece_artists, pieces, sources, artists;
        drop index one_music_qid;
        alter table music_claims drop column entries;
    """)
