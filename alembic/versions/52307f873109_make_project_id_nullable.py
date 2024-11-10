"""make_project_id_nullable

Revision ID: 52307f873109
Revises: 0cc9fedcbc4c
Create Date: 2024-11-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic
revision: str = '52307f873109'
down_revision: Union[str, None] = '0cc9fedcbc4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('requests', 'project_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('requests', 'project_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###