"""
data.py

Database Model Objects

<Author>: Hanaa Abbas
<Email>: hanaaloutfy94@gmail.com
<Date>: 31 May, 2023

GNU General Public License Version 3
"""
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Block(BaseModel):
    __tablename__ = 'block'

    id = sa.Column(sa.Integer(), primary_key=True, autoincrement=False)
    parent_id = sa.Column(sa.Integer(), nullable=False)
    hash = sa.Column(sa.String(66), unique=True, index=True, nullable=False)
    parent_hash = sa.Column(sa.String(66), index=True, nullable=False)
    state_root = sa.Column(sa.String(66), nullable=False)
    extrinsics_root = sa.Column(sa.String(66), nullable=False)
    author = sa.Column(sa.String(48), nullable=True)
    count_extrinsics = sa.Column(sa.Integer(), nullable=False)
    count_extrinsics_unsigned = sa.Column(sa.Integer(), nullable=False)
    count_extrinsics_signed = sa.Column(sa.Integer(), nullable=False)
    count_extrinsics_error = sa.Column(sa.Integer(), nullable=False)
    count_extrinsics_success = sa.Column(sa.Integer(), nullable=False)
    count_events = sa.Column(sa.Integer(), nullable=False)
    count_accounts_new = sa.Column(sa.Integer(), nullable=False)
    count_accounts_reaped = sa.Column(sa.Integer(), nullable=False)
    count_sessions_new = sa.Column(sa.Integer(), nullable=False)
    count_log = sa.Column(sa.Integer(), nullable=False)
    datetime = sa.Column(sa.DateTime(), nullable=True)
    timestamp = sa.Column(sa.BigInteger(), nullable=True)
    slot_number = sa.Column(sa.Numeric(precision=65, scale=0), nullable=True)
    authority_index = sa.Column(sa.Integer(), nullable=True)
    spec_version_id = sa.Column(sa.String(64), nullable=False)
    logs = sa.Column(sa.JSON(), default=None, server_default=None)

    def set_datetime(self, datetime):
        self.datetime = datetime

    @classmethod
    def get_head(cls, session):
        with session.begin():
            query = session.query(cls)
            model = query.order_by(cls.id.desc()).first()
        return model

    @classmethod
    def get_missing_block_ids(cls, session):
        return session.execute(text("""
                                            SELECT
                                              z.expected as block_from, z.got-1 as block_to
                                            FROM (
                                             SELECT
                                              @rownum:=@rownum+1 AS expected,
                                              IF(@rownum=id, 0, @rownum:=id) AS got
                                             FROM
                                              (SELECT @rownum:=0) AS a
                                              JOIN block
                                              ORDER BY id
                                             ) AS z
                                            WHERE z.got!=0
                                            ORDER BY block_from ASC
                                            """)
                               )


class Transaction(BaseModel):
    __tablename__ = 'extrinsic'

    block_id = sa.Column(sa.Integer(), primary_key=True, index=True)
    block = relationship(Block, foreign_keys=[block_id], primaryjoin=block_id == Block.id)
    extrinsic_idx = sa.Column(sa.Integer(), primary_key=True, index=True)
    nesting_idx = sa.Column(sa.Integer(), primary_key=True, index=True,
                        default=0)  # Added to handle nested transactions like Utiltiy, Proxy, Multisig
    batch_idx = sa.Column(sa.Integer(), primary_key=True, index=True,
                          default=0)  # Added to handle Utility Batch extrinsics
    unique_sequence = sa.Column(sa.Integer(), primary_key=True, index=True, default=0)
    extrinsic_length = sa.Column(sa.String(10))
    extrinsic_hash = sa.Column(sa.String(66), nullable=True)
    signed = sa.Column(sa.SmallInteger(), nullable=False)

    from_address = sa.Column(sa.String(64), index=True)
    to_address = sa.Column(sa.String(64), index=True, nullable=True)
    value = sa.Column(sa.Numeric(precision=65, scale=10), default=0, nullable=True)
    signature = sa.Column(sa.String(150))
    tip = sa.Column(sa.Numeric(precision=65, scale=10), default=0, nullable=True)
    fee = sa.Column(sa.Numeric(precision=65, scale=10), default=0, nullable=True)
    nonce = sa.Column(sa.Integer())

    module_id = sa.Column(sa.String(64), index=True)
    call_id = sa.Column(sa.String(64), index=True)

    success = sa.Column(sa.SmallInteger(), default=0, nullable=False)
    spec_version_id = sa.Column(sa.Integer())
    # debug_info = sa.Column(sa.JSON(), default=None, server_default=None)

    datetime = sa.Column(sa.DateTime(), nullable=True)
    timestamp = sa.Column(sa.BigInteger(), nullable=True)

    def serialize_id(self):
        return '{}-{}-{}'.format(self.block_id, self.extrinsic_idx, self.nesting_idx, self.batch_idx)

class Account(BaseModel):
    __tablename__ = 'account'

    address = sa.Column(sa.String(64), primary_key=True)
    pkey = sa.Column(sa.String(64), nullable=True)
    index_address = sa.Column(sa.String(24), index=True)
    is_reaped = sa.Column(sa.Boolean, default=False)

    is_validator = sa.Column(sa.Boolean, default=False, index=True)
    was_validator = sa.Column(sa.Boolean, default=False, index=True)
    is_nominator = sa.Column(sa.Boolean, default=False, index=True)
    was_nominator = sa.Column(sa.Boolean, default=False, index=True)
    is_council_member = sa.Column(sa.Boolean, default=False, index=True)
    was_council_member = sa.Column(sa.Boolean, default=False, index=True)
    is_tech_comm_member = sa.Column(sa.Boolean, default=False, index=True)
    was_tech_comm_member = sa.Column(sa.Boolean, default=False, index=True)
    is_registrar = sa.Column(sa.Boolean, default=False, index=True)
    was_registrar = sa.Column(sa.Boolean, default=False, index=True)
    is_sudo = sa.Column(sa.Boolean, default=False, index=True)
    was_sudo = sa.Column(sa.Boolean, default=False, index=True)
    is_treasury = sa.Column(sa.Boolean, default=False, index=True)
    count_reaped = sa.Column(sa.Integer(), default=0)
    balance_total = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    balance_free = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    balance_reserved = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    nonce = sa.Column(sa.Integer(), nullable=True)
    has_identity = sa.Column(sa.Boolean, default=False, index=True)
    has_subidentity = sa.Column(sa.Boolean, default=False, index=True)
    identity_display = sa.Column(sa.String(32), index=True, nullable=True)
    identity_legal = sa.Column(sa.String(32), nullable=True)
    identity_web = sa.Column(sa.String(32), nullable=True)
    identity_riot = sa.Column(sa.String(32), nullable=True)
    identity_email = sa.Column(sa.String(32), nullable=True)
    identity_twitter = sa.Column(sa.String(32), nullable=True)
    identity_judgement_good = sa.Column(sa.Integer(), default=0)
    identity_judgement_bad = sa.Column(sa.Integer(), default=0)
    parent_identity = sa.Column(sa.String(64), index=True, nullable=True)
    subidentity_display = sa.Column(sa.String(32), nullable=True)

    created_at_block = sa.Column(sa.Integer(), nullable=False)
    updated_at_block = sa.Column(sa.Integer(), nullable=False)

    def serialize_id(self):
        return self.address


class AccountInfoSnapshot(BaseModel):
    __tablename__ = 'account_info_snapshot'
    block_id = sa.Column(sa.Integer(), primary_key=True, index=True)
    account_id = sa.Column(sa.String(64), primary_key=True, index=True)
    pkey = sa.Column(sa.String(64), index=True)
    balance_total = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    balance_free = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    balance_reserved = sa.Column(sa.Numeric(precision=65, scale=10), nullable=True, index=True)
    nonce = sa.Column(sa.Integer(), nullable=True)


class Event(BaseModel):
    __tablename__ = 'event'

    block_id = sa.Column(sa.Integer(), primary_key=True, index=True)
    block = relationship(Block, foreign_keys=[block_id], primaryjoin=block_id == Block.id)
    event_idx = sa.Column(sa.Integer(), primary_key=True, index=True)
    extrinsic_idx = sa.Column(sa.Integer(), index=True)
    type = sa.Column(sa.String(4), index=True)
    module_id = sa.Column(sa.String(64), index=True)
    event_id = sa.Column(sa.String(64), index=True)
    system = sa.Column(sa.SmallInteger(), index=True, nullable=False)
    phase = sa.Column(sa.String(100), default=None)
    attributes = sa.Column(sa.JSON())
    spec_version_id = sa.Column(sa.Integer())

    def serialize_id(self):
        return '{}-{}'.format(self.block_id, self.event_idx)

class ProxyAccount(BaseModel):
    __tablename__ = 'proxy_account'

    address = sa.Column(sa.String(64), primary_key=True)
    proxied_account_address = sa.Column(sa.String(64), primary_key=True)
    proxy_type = sa.Column(sa.String(64))

    def serialize_id(self):
        return '{}-{}'.format(self.block_id, self.event_idx)

class MultisigMemberAccount(BaseModel):
    __tablename__ = 'multisig_member_account'

    address = sa.Column(sa.String(255), primary_key=True)
    multisig_account_address = sa.Column(sa.String(255), primary_key=True)

class ProxyExtrinsicRealAddress(BaseModel):
    __tablename__ = 'proxy_extrinsic_real_address'

    block_id = sa.Column(sa.Integer(), primary_key=True, index=True)
    extrinsic_idx = sa.Column(sa.Integer(), primary_key=True, index=True)
    nesting_idx = sa.Column(sa.Integer(), primary_key=True, index=True, default=0)
    batch_idx = sa.Column(sa.Integer(), primary_key=True, index=True, default=0)
    unique_sequence = sa.Column(sa.Integer(), primary_key=True, index=True, default=0)
    real_address = sa.Column(sa.String(64), nullable=False, index=True)