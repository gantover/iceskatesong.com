"""Music text search: english full-text index over the raw music text

Revision ID: 0007
Revises: 0006
"""

from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    # The search query must use this exact expression for the index to apply.
    op.execute("create index music_claims_text on music_claims using gin (to_tsvector('english', raw_text))")


def downgrade() -> None:
    op.execute("drop index music_claims_text")
