"""Initial db layout

Revision ID: 38a7f29de7c7
Revises: 
Create Date: 2020-04-16 12:51:44.832584

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '38a7f29de7c7'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('account',
    sa.Column('address', sa.String(length=64), nullable=False),
    sa.Column('pkey', sa.String(length=64), nullable=True),
    sa.Column('index_address', sa.String(length=24), nullable=True),
    sa.Column('is_reaped', sa.Boolean(), nullable=True),
    sa.Column('is_validator', sa.Boolean(), nullable=True),
    sa.Column('was_validator', sa.Boolean(), nullable=True),
    sa.Column('is_nominator', sa.Boolean(), nullable=True),
    sa.Column('was_nominator', sa.Boolean(), nullable=True),
    sa.Column('is_council_member', sa.Boolean(), nullable=True),
    sa.Column('was_council_member', sa.Boolean(), nullable=True),
    sa.Column('is_tech_comm_member', sa.Boolean(), nullable=True),
    sa.Column('was_tech_comm_member', sa.Boolean(), nullable=True),
    sa.Column('is_registrar', sa.Boolean(), nullable=True),
    sa.Column('was_registrar', sa.Boolean(), nullable=True),
    sa.Column('is_sudo', sa.Boolean(), nullable=True),
    sa.Column('was_sudo', sa.Boolean(), nullable=True),
    sa.Column('is_treasury', sa.Boolean(), nullable=True),
    sa.Column('count_reaped', sa.Integer(), nullable=True),
    sa.Column('balance_total', sa.Numeric(precision=65, scale=10), nullable=True),
    sa.Column('balance_reserved', sa.Numeric(precision=65, scale=10), nullable=True),
    sa.Column('balance_free', sa.Numeric(precision=65, scale=10), nullable=True),
    sa.Column('nonce', sa.Integer(), nullable=True),
    sa.Column('has_identity', sa.Boolean(), nullable=True),
    sa.Column('has_subidentity', sa.Boolean(), nullable=True),
    sa.Column('identity_display', sa.String(length=32), nullable=True),
    sa.Column('identity_legal', sa.String(length=32), nullable=True),
    sa.Column('identity_web', sa.String(length=32), nullable=True),
    sa.Column('identity_riot', sa.String(length=32), nullable=True),
    sa.Column('identity_email', sa.String(length=32), nullable=True),
    sa.Column('identity_twitter', sa.String(length=32), nullable=True),
    sa.Column('identity_judgement_good', sa.Integer(), nullable=True),
    sa.Column('identity_judgement_bad', sa.Integer(), nullable=True),
    sa.Column('parent_identity', sa.String(length=64), nullable=True),
    sa.Column('subidentity_display', sa.String(length=32), nullable=True),
    sa.Column('created_at_block', sa.Integer(), nullable=False),
    sa.Column('updated_at_block', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('address'))
    op.create_index(op.f('ix_account_balance_free'), 'account', ['balance_free'], unique=False)
    op.create_index(op.f('ix_account_balance_reserved'), 'account', ['balance_reserved'], unique=False)
    op.create_index(op.f('ix_account_balance_total'), 'account', ['balance_total'], unique=False)
    op.create_index(op.f('ix_account_has_identity'), 'account', ['has_identity'], unique=False)
    op.create_index(op.f('ix_account_has_subidentity'), 'account', ['has_subidentity'], unique=False)
    op.create_index(op.f('ix_account_identity_display'), 'account', ['identity_display'], unique=False)
    op.create_index(op.f('ix_account_index_address'), 'account', ['index_address'], unique=False)
    op.create_index(op.f('ix_account_is_council_member'), 'account', ['is_council_member'], unique=False)
    op.create_index(op.f('ix_account_is_nominator'), 'account', ['is_nominator'], unique=False)
    op.create_index(op.f('ix_account_is_registrar'), 'account', ['is_registrar'], unique=False)
    op.create_index(op.f('ix_account_is_sudo'), 'account', ['is_sudo'], unique=False)
    op.create_index(op.f('ix_account_is_tech_comm_member'), 'account', ['is_tech_comm_member'], unique=False)
    op.create_index(op.f('ix_account_is_treasury'), 'account', ['is_treasury'], unique=False)
    op.create_index(op.f('ix_account_is_validator'), 'account', ['is_validator'], unique=False)
    op.create_index(op.f('ix_account_parent_identity'), 'account', ['parent_identity'], unique=False)
    op.create_index(op.f('ix_account_was_council_member'), 'account', ['was_council_member'], unique=False)
    op.create_index(op.f('ix_account_was_nominator'), 'account', ['was_nominator'], unique=False)
    op.create_index(op.f('ix_account_was_registrar'), 'account', ['was_registrar'], unique=False)
    op.create_index(op.f('ix_account_was_sudo'), 'account', ['was_sudo'], unique=False)
    op.create_index(op.f('ix_account_was_tech_comm_member'), 'account', ['was_tech_comm_member'], unique=False)
    op.create_index(op.f('ix_account_was_validator'), 'account', ['was_validator'], unique=False)
