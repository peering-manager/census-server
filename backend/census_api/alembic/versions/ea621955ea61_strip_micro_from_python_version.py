"""Strip micro from Python version

Revision ID: ea621955ea61
Revises: 91c2a580f3c6
Create Date: 2024-11-29 22:34:12.724662

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "ea621955ea61"
down_revision: Union[str, None] = "91c2a580f3c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        r"""
        UPDATE "censusrecord"
        SET "python_version" = regexp_replace("python_version", '^(\d+\.\d+)\..*$', '\1')
        WHERE "python_version" ~ '^(\d+\.\d+)\..*$'
        """
    )


def downgrade() -> None:
    pass
