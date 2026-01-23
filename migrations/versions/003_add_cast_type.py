"""Add cast_type field to orders table

Revision ID: 003_add_cast_type
Revises: 002_add_is_test_order
Create Date: 2026-01-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_add_cast_type"
down_revision: Union[str, None] = "002_add_is_test_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the cast_type enum type
    cast_type_enum = sa.Enum(
        "cast_by_us", "customer_cast", "combination",
        name="casttype"
    )
    cast_type_enum.create(op.get_bind(), checkfirst=True)

    # Add cast_type column with default 'customer_cast' for backwards compatibility
    op.add_column(
        "orders",
        sa.Column(
            "cast_type",
            cast_type_enum,
            nullable=False,
            server_default="customer_cast"
        ),
    )

    # Create index for filtering by cast type
    op.create_index("idx_orders_cast_type", "orders", ["cast_type"])


def downgrade() -> None:
    op.drop_index("idx_orders_cast_type", table_name="orders")
    op.drop_column("orders", "cast_type")

    # Drop the enum type
    sa.Enum(name="casttype").drop(op.get_bind(), checkfirst=True)
