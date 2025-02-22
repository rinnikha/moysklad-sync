from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from flask_login import UserMixin
from app import db, login_manager
from werkzeug.security import generate_password_hash, check_password_hash

import enum

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class SyncLogStatus(enum.IntEnum):
    PENDING = 0
    COMPLETED = 1
    FAILED = 2

class CounterpartyMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    ms1_cp_name = db.Column(db.String(255), nullable=False)
    ms1_cp_id = db.Column(db.String(50), unique=True, nullable=False)
    ms1_cp_meta = db.Column(JSON, nullable=False)

    ms2_org_name = db.Column(db.String(255), nullable=False)
    ms2_org_meta = db.Column(JSON, nullable=False)

    group_name = db.Column(db.String(255), nullable=False)
    group_meta = db.Column(JSON, nullable=False)

    owner_name = db.Column(db.String(255), nullable=False)
    owner_meta = db.Column(JSON, nullable=False)

    store_name = db.Column(db.String(255), nullable=False)
    store_meta = db.Column(JSON, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SyncLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sync_time = db.Column(db.DateTime, default=None, nullable=True)
    order_moment = db.Column(db.DateTime, default=datetime.utcnow)
    order_amount = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text)
    details = db.Column(db.Text)
    order_id = db.Column(db.String(50))
    ms2_purchase_id = db.Column(db.String(50), nullable=True)
    counterparty_id = db.Column(db.Integer, db.ForeignKey('counterparty_mapping.id'))
    
    # Relationships
    counterparty = db.relationship('CounterpartyMapping', backref='logs')



