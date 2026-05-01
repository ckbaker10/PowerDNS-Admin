"""add apikey rrset acl table

Revision ID: c9a1f2e8d701
Revises: b24bf17725d2
Create Date: 2026-05-01 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9a1f2e8d701'
down_revision = 'b24bf17725d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'apikey_rrset_acl',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('apikey_id', sa.Integer(), nullable=False),
        sa.Column('domain_id', sa.Integer(), nullable=False),
        sa.Column('record_name_pattern', sa.String(length=255), nullable=False),
        sa.Column('record_type', sa.String(length=10), nullable=False),
        sa.Column('allow_replace', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column('allow_delete', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.ForeignKeyConstraint(['apikey_id'], ['apikey.id'],
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['domain_id'], ['domain.id'],
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('apikey_rrset_acl', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_apikey_rrset_acl_apikey_id'),
            ['apikey_id'], unique=False)


def downgrade():
    with op.batch_alter_table('apikey_rrset_acl', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_apikey_rrset_acl_apikey_id'))
    op.drop_table('apikey_rrset_acl')
