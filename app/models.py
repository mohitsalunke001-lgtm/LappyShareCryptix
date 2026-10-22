from datetime import datetime, timezone, date
import uuid
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=False)
    college_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    year_of_study = db.Column(db.String(30), nullable=False)
    roll_number = db.Column(db.String(50), nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="borrower", nullable=False) # 'borrower', 'lender', 'admin'
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    coin_balance = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    
    # Relationships
    laptops = db.relationship("Laptop", backref="lender", lazy="dynamic", cascade="all, delete-orphan")
    borrow_requests = db.relationship("BorrowRequest", backref="borrower", lazy="dynamic", foreign_keys="BorrowRequest.borrower_id")
    coin_transactions = db.relationship("LappyCoinTransaction", backref="user", lazy="dynamic", foreign_keys="LappyCoinTransaction.user_id")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    reset_tokens = db.relationship("PasswordResetToken", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    @property
    def display_name(self):
        return self.full_name
        
    def to_dict(self, include_sensitive=False):
        data = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "college_name": self.college_name,
            "department": self.department,
            "year_of_study": self.year_of_study,
            "role": self.role,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "coin_balance": self.coin_balance,
            "created_at": self.created_at.strftime("%Y-%m-%d"),
        }
        if include_sensitive:
            data["phone"] = self.phone
            data["roll_number"] = self.roll_number
        return data


class Laptop(db.Model):
    __tablename__ = "laptops"
    
    id = db.Column(db.Integer, primary_key=True)
    lender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    brand = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    processor = db.Column(db.String(100), nullable=False)
    ram = db.Column(db.String(20), nullable=False) # e.g. "8 GB", "16 GB"
    storage = db.Column(db.String(50), nullable=False) # e.g. "512 GB SSD"
    operating_system = db.Column(db.String(50), nullable=False) # e.g. "Windows 11", "Ubuntu Linux"
    condition = db.Column(db.String(30), nullable=False) # "Excellent", "Good", "Fair"
    description = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(255), nullable=True)
    lending_guidelines = db.Column(db.Text, nullable=True)
    academic_suitability = db.Column(db.String(255), nullable=True) # e.g. "Machine Learning, Web Dev, Programming"
    
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Lender can toggle listing on/off
    under_maintenance = db.Column(db.Boolean, default=False, nullable=False)
    maintenance_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    
    # Relationships
    requests = db.relationship("BorrowRequest", backref="laptop", lazy="dynamic", cascade="all, delete-orphan")
    
    @property
    def title(self):
        return f"{self.brand} {self.model}"
        
    @property
    def current_status(self):
        if not self.is_active:
            return "Deactivated"
        if self.under_maintenance:
            return "Under Maintenance"
        # Check if currently actively borrowed
        active_borrow = self.requests.filter(BorrowRequest.status == "borrowed").first()
        if active_borrow:
            return "Currently Borrowed"
        return "Available"


class BorrowRequest(db.Model):
    __tablename__ = "borrow_requests"
    
    id = db.Column(db.Integer, primary_key=True)
    reference_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    laptop_id = db.Column(db.Integer, db.ForeignKey("laptops.id"), nullable=False, index=True)
    borrower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    purpose = db.Column(db.String(100), nullable=False)
    purpose_details = db.Column(db.Text, nullable=True)
    borrower_message = db.Column(db.Text, nullable=True)
    
    # Status: pending, approved, rejected, cancelled, borrowed, returned, overdue
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    decision_at = db.Column(db.DateTime, nullable=True)
    
    # Handover and return tracking
    record = db.relationship("HandoverReturnRecord", backref="request", uselist=False, cascade="all, delete-orphan")
    
    @staticmethod
    def generate_reference():
        unique_suffix = uuid.uuid4().hex[:8].upper()
        return f"REQ-{datetime.now().strftime('%Y%m')}-{unique_suffix}"


class HandoverReturnRecord(db.Model):
    __tablename__ = "handover_return_records"
    
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey("borrow_requests.id"), unique=True, nullable=False)
    
    # Handover info
    handover_date = db.Column(db.DateTime, nullable=True)
    handover_condition = db.Column(db.String(100), nullable=True)
    handover_notes = db.Column(db.Text, nullable=True)
    handover_qr_token = db.Column(db.String(64), unique=True, nullable=True)
    handover_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    
    # Return info
    return_date = db.Column(db.DateTime, nullable=True)
    return_condition = db.Column(db.String(100), nullable=True)
    return_notes = db.Column(db.Text, nullable=True)
    return_qr_token = db.Column(db.String(64), unique=True, nullable=True)
    return_confirmed = db.Column(db.Boolean, default=False, nullable=False)
    
    # Damage & maintenance
    damage_reported = db.Column(db.Boolean, default=False, nullable=False)
    damage_details = db.Column(db.Text, nullable=True)
    is_overdue = db.Column(db.Boolean, default=False, nullable=False)
    
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)


class LappyCoinTransaction(db.Model):
    __tablename__ = "lappy_coin_transactions"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False) # e.g. +10, +5, +2, or +/- manual adjustment
    event_type = db.Column(db.String(50), nullable=False) # LIST_LAPTOP, COMPLETE_LENDING, ONTIME_RETURN, COMMUNITY_HELP, ADMIN_ADJUSTMENT
    reference_id = db.Column(db.String(100), nullable=True) # e.g. "laptop:1", "request:5"
    description = db.Column(db.String(255), nullable=False)
    created_by_admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    admin_actor = db.relationship("User", foreign_keys=[created_by_admin_id])
    
    __table_args__ = (
        db.Index("idx_user_event_ref", "user_id", "event_type", "reference_id"),
    )


class Notification(db.Model):
    __tablename__ = "notifications"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), default="info", nullable=False) # request, approval, handover, return, coins, system
    link = db.Column(db.String(255), nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    def is_valid(self):
        # Comparison with timezone-aware or naive datetime safely
        now = datetime.now(timezone.utc)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return not self.used and now <= expires


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    target_type = db.Column(db.String(50), nullable=True) # User, Laptop, BorrowRequest, LappyCoinTransaction
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    admin = db.relationship("User", foreign_keys=[admin_id])
