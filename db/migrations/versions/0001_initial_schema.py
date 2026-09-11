"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgcrypto
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # 2. Customers
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active', 'blocked', 'inactive')", name='chk_customer_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_customers_status', 'customers', ['status'])

    # 3. Products
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('sku', sa.String(length=80), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('price >= 0', name='chk_product_price_non_negative'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku')
    )
    op.create_index('idx_products_category', 'products', ['category'])

    # 4. Warehouses
    op.create_table(
        'warehouses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('location', sa.String(length=150), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive', 'maintenance')", name='chk_warehouse_status'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 5. Inventory
    op.create_table(
        'inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), server_default='0', nullable=False),
        sa.Column('reserved_quantity', sa.Integer(), server_default='0', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity >= 0', name='chk_inventory_quantity_non_negative'),
        sa.CheckConstraint('reserved_quantity >= 0', name='chk_inventory_reserved_non_negative'),
        sa.CheckConstraint('reserved_quantity <= quantity', name='chk_inventory_reserved_le_quantity'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('warehouse_id', 'product_id', name='uq_inventory_warehouse_product')
    )
    op.create_index('idx_inventory_product_id', 'inventory', ['product_id'])
    op.create_index('idx_inventory_warehouse_id', 'inventory', ['warehouse_id'])

    # 6. Orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='placed', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('order_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expected_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shipping_address', sa.Text(), nullable=False),
        sa.CheckConstraint("status IN ('placed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded', 'replacement_pending', 'replacement_sent')", name='chk_order_status'),
        sa.CheckConstraint('total_amount >= 0', name='chk_order_total_amount_non_negative'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_orders_customer_id', 'orders', ['customer_id'])
    op.create_index('idx_orders_status', 'orders', ['status'])

    # 7. Order Items
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint('quantity > 0', name='chk_order_item_quantity_positive'),
        sa.CheckConstraint('unit_price >= 0', name='chk_order_item_unit_price_non_negative'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('idx_order_items_product_id', 'order_items', ['product_id'])

    # 8. Shipments
    op.create_table(
        'shipments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tracking_number', sa.String(length=100), nullable=False),
        sa.Column('carrier', sa.String(length=80), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='label_created', nullable=False),
        sa.Column('shipped_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_delivery', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('label_created', 'in_transit', 'out_for_delivery', 'delivered', 'delayed', 'lost', 'returned')", name='chk_shipment_status'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tracking_number')
    )
    op.create_index('idx_shipments_order_id', 'shipments', ['order_id'])
    op.create_index('idx_shipments_status', 'shipments', ['status'])

    # 9. Policies
    op.create_table(
        'policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('issue_type', sa.String(length=80), nullable=False),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('risk_level', sa.String(length=20), server_default='low', nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='100', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("risk_level IN ('low', 'medium', 'high')", name='chk_policy_risk_level'),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Cases
    op.create_table(
        'cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issue_type', sa.String(length=80), nullable=False),
        sa.Column('customer_goal', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='open', nullable=False),
        sa.Column('risk_level', sa.String(length=20), server_default='low', nullable=False),
        sa.Column('current_plan', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('resolution_type', sa.String(length=80), nullable=True),
        sa.Column('resolution_status', sa.String(length=50), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("risk_level IN ('low', 'medium', 'high')", name='chk_case_risk_level'),
        sa.CheckConstraint("status IN ('open', 'investigating', 'planning', 'awaiting_approval', 'executing', 'verifying', 'replanning', 'resolved', 'escalated', 'failed')", name='chk_case_status'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cases_customer_id', 'cases', ['customer_id'])
    op.create_index('idx_cases_order_id', 'cases', ['order_id'])
    op.create_index('idx_cases_risk_level', 'cases', ['risk_level'])
    op.create_index('idx_cases_status', 'cases', ['status'])

    # 11. Refunds
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('requires_approval', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('approved_by', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('amount > 0', name='chk_refund_amount_positive'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'processing', 'completed', 'failed', 'rejected')", name='chk_refund_status'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_refunds_case_id', 'refunds', ['case_id'])
    op.create_index('idx_refunds_order_id', 'refunds', ['order_id'])

    # 12. Replacements
    op.create_table(
        'replacements',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('requires_approval', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'processing', 'shipped', 'completed', 'failed', 'rejected')", name='chk_replacement_status'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_replacements_case_id', 'replacements', ['case_id'])
    op.create_index('idx_replacements_order_id', 'replacements', ['order_id'])
    op.create_index('idx_replacements_product_id', 'replacements', ['product_id'])
    op.create_index('idx_replacements_warehouse_id', 'replacements', ['warehouse_id'])

    # 13. Cancellations
    op.create_table(
        'cancellations',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('requires_approval', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'completed', 'failed', 'rejected')", name='chk_cancellation_status'),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cancellations_case_id', 'cancellations', ['case_id'])
    op.create_index('idx_cancellations_order_id', 'cancellations', ['order_id'])

    # 14. Agent Events
    op.create_table(
        'agent_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('tool_name', sa.String(length=80), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_agent_events_case_id', 'agent_events', ['case_id'])
    op.create_index('idx_agent_events_event_type', 'agent_events', ['event_type'])

    # 15. Triggers for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_inventory_updated_at ON inventory;
        CREATE TRIGGER trg_inventory_updated_at
            BEFORE UPDATE ON inventory
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS trg_policies_updated_at ON policies;
        CREATE TRIGGER trg_policies_updated_at
            BEFORE UPDATE ON policies
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();

        DROP TRIGGER IF EXISTS trg_cases_updated_at ON cases;
        CREATE TRIGGER trg_cases_updated_at
            BEFORE UPDATE ON cases
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_cases_updated_at ON cases")
    op.execute("DROP TRIGGER IF EXISTS trg_policies_updated_at ON policies")
    op.execute("DROP TRIGGER IF EXISTS trg_inventory_updated_at ON inventory")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    op.drop_table('agent_events')
    op.drop_table('cancellations')
    op.drop_table('replacements')
    op.drop_table('refunds')
    op.drop_table('cases')
    op.drop_table('policies')
    op.drop_table('shipments')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('inventory')
    op.drop_table('warehouses')
    op.drop_table('products')
    op.drop_table('customers')
