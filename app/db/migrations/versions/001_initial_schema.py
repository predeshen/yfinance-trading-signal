"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol_alias', sa.String(), nullable=False),
        sa.Column('yf_symbol', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('time_generated_utc', sa.DateTime(), nullable=False),
        sa.Column('entry_price_at_signal', sa.Float(), nullable=False),
        sa.Column('initial_sl', sa.Float(), nullable=False),
        sa.Column('initial_tp', sa.Float(), nullable=False),
        sa.Column('strategy_name', sa.String(), nullable=False),
        sa.Column('notes', sa.String(), nullable=True),
        sa.Column('estimated_rr', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_signals_id'), 'signals', ['id'], unique=False)
    op.create_index(op.f('ix_signals_symbol_alias'), 'signals', ['symbol_alias'], unique=False)
    op.create_index(op.f('ix_signals_time_generated_utc'), 'signals', ['time_generated_utc'], unique=False)
    
    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('signal_id', sa.Integer(), nullable=False),
        sa.Column('symbol_alias', sa.String(), nullable=False),
        sa.Column('yf_symbol', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('planned_entry_price', sa.Float(), nullable=False),
        sa.Column('actual_entry_price', sa.Float(), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=False),
        sa.Column('take_profit', sa.Float(), nullable=False),
        sa.Column('state', sa.Enum('Open', 'ClosedByTp', 'ClosedBySl', 'ClosedManual', 'Expired', name='tradestate'), nullable=False),
        sa.Column('open_time_utc', sa.DateTime(), nullable=False),
        sa.Column('close_time_utc', sa.DateTime(), nullable=True),
        sa.Column('close_price', sa.Float(), nullable=True),
        sa.Column('close_reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['signal_id'], ['signals.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_id'), 'trades', ['id'], unique=False)
    op.create_index(op.f('ix_trades_symbol_alias'), 'trades', ['symbol_alias'], unique=False)
    op.create_index(op.f('ix_trades_state'), 'trades', ['state'], unique=False)
    op.create_index(op.f('ix_trades_open_time_utc'), 'trades', ['open_time_utc'], unique=False)
    
    # Create heartbeats table
    op.create_table(
        'heartbeats',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol_alias', sa.String(), nullable=False),
        sa.Column('timestamp_utc', sa.DateTime(), nullable=False),
        sa.Column('open_trade_count', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_heartbeats_id'), 'heartbeats', ['id'], unique=False)
    op.create_index(op.f('ix_heartbeats_symbol_alias'), 'heartbeats', ['symbol_alias'], unique=False)
    op.create_index(op.f('ix_heartbeats_timestamp_utc'), 'heartbeats', ['timestamp_utc'], unique=False)
    
    # Create error_logs table
    op.create_table(
        'error_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp_utc', sa.DateTime(), nullable=False),
        sa.Column('component', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('exception_type', sa.String(), nullable=True),
        sa.Column('symbol_alias', sa.String(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_error_logs_id'), 'error_logs', ['id'], unique=False)
    op.create_index(op.f('ix_error_logs_timestamp_utc'), 'error_logs', ['timestamp_utc'], unique=False)
    op.create_index(op.f('ix_error_logs_symbol_alias'), 'error_logs', ['symbol_alias'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_error_logs_symbol_alias'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_timestamp_utc'), table_name='error_logs')
    op.drop_index(op.f('ix_error_logs_id'), table_name='error_logs')
    op.drop_table('error_logs')
    
    op.drop_index(op.f('ix_heartbeats_timestamp_utc'), table_name='heartbeats')
    op.drop_index(op.f('ix_heartbeats_symbol_alias'), table_name='heartbeats')
    op.drop_index(op.f('ix_heartbeats_id'), table_name='heartbeats')
    op.drop_table('heartbeats')
    
    op.drop_index(op.f('ix_trades_open_time_utc'), table_name='trades')
    op.drop_index(op.f('ix_trades_state'), table_name='trades')
    op.drop_index(op.f('ix_trades_symbol_alias'), table_name='trades')
    op.drop_index(op.f('ix_trades_id'), table_name='trades')
    op.drop_table('trades')
    
    op.drop_index(op.f('ix_signals_time_generated_utc'), table_name='signals')
    op.drop_index(op.f('ix_signals_symbol_alias'), table_name='signals')
    op.drop_index(op.f('ix_signals_id'), table_name='signals')
    op.drop_table('signals')
