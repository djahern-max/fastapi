"""rename_rating_to_stars_in_showcase_ratings

Revision ID: 0aea0cc44575
Revises: 64bd507d85a6
Create Date: 2025-01-06 15:03:10.627863

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0aea0cc44575"
down_revision: Union[str, None] = "64bd507d85a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # op.create_unique_constraint('unique_request_comment_vote', 'request_comment_votes', ['user_id', 'comment_id'])
    op.add_column("showcase_ratings", sa.Column("stars", sa.Integer(), nullable=False))
    op.drop_column("showcase_ratings", "rating")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "showcase_ratings",
        sa.Column("rating", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_column("showcase_ratings", "stars")
    # op.drop_constraint('unique_request_comment_vote', 'request_comment_votes', type_='unique')
    # ### end Alembic commands ###
