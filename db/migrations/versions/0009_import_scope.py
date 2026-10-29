"""Import scope: a quick Import re-checks only the two newest listed Seasons' ISU pages, a full one every page.

Revision ID: 0009
Revises: 0008
"""

from alembic import op

revision = "0009"
down_revision = "0008"


def upgrade() -> None:
    op.execute("alter table imports add column scope text not null default 'full' check (scope in ('quick', 'full'))")


def downgrade() -> None:
    op.execute("alter table imports drop column scope")
