import os
import secrets
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import session, request, redirect, url_for, flash, abort, current_app, g
from app.models import db, User, LappyCoinTransaction, Notification, AuditLog, BorrowRequest, PasswordResetToken

def generate_csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]

def verify_csrf():
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        if current_app.config.get("TESTING") and not current_app.config.get("WTF_CSRF_ENABLED", False):
            return
        token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        if not token or token != session.get("_csrf_token"):
            abort(400, description="Invalid or missing CSRF token. Please refresh the page and try again.")

def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    if not hasattr(g, "_cached_user") or getattr(g, "_cached_user_id", None) != user_id:
        user = db.session.get(User, user_id)
        if user and not user.is_active:
            session.clear()
            return None
        g._cached_user = user
        g._cached_user_id = user_id
    return g._cached_user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not user.is_active:
            flash("Your account has been deactivated. Please contact an administrator.", "error")
            session.clear()
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_admin:
            flash("Administrator privileges are required to view that page.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def lender_or_borrower_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function

def log_audit_event(action, target_type=None, target_id=None, details=None):
    try:
        user = get_current_user()
        admin_id = user.id if user and user.is_admin else (user.id if user else None)
        ip = request.remote_addr if request else "127.0.0.1"
        log = AuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details=details,
            ip_address=ip
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Audit log error: {e}")

def create_notification(user_id, title, message, category="info", link=None):
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            link=link
        )
        db.session.add(notif)
        db.session.commit()
        return notif
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Notification creation error: {e}")
        return None

def award_lappy_coins(user_id, event_type, amount, description, reference_id=None, admin_id=None):
    """
    Awards or adjusts LappyCoins atomically.
    Ensures idempotency if reference_id is provided (preventing duplicate rewards for same event).
    """
    user = db.session.get(User, user_id)
    if not user:
        return False, "User not found"
        
    # Idempotency check
    if reference_id is not None:
        existing = LappyCoinTransaction.query.filter_by(
            user_id=user_id,
            event_type=event_type,
            reference_id=str(reference_id)
        ).first()
        if existing:
            return False, f"Reward already claimed for this event ({reference_id})"
            
    # Calculate new balance and guard against negative balances
    new_balance = user.coin_balance + amount
    if new_balance < 0 and amount < 0:
        return False, f"Insufficient coin balance for adjustment. Current: {user.coin_balance}"
        
    tx = LappyCoinTransaction(
        user_id=user_id,
        amount=amount,
        event_type=event_type,
        reference_id=str(reference_id) if reference_id else None,
        description=description,
        created_by_admin_id=admin_id
    )
    user.coin_balance = new_balance
    db.session.add(tx)
    db.session.commit()
    
    # Notify user
    sign = "+" if amount > 0 else ""
    link_url = "/rewards"
    try:
        link_url = url_for("rewards.index")
    except Exception:
        link_url = "/rewards"

    create_notification(
        user_id=user_id,
        title=f"LappyCoins Update: {sign}{amount} Coins",
        message=f"{description} (New balance: {user.coin_balance} coins)",
        category="coins",
        link=link_url
    )
    
    return True, "Success"

def is_laptop_available(laptop_id, start_date, end_date, exclude_request_id=None):
    """
    Checks if a laptop is free between start_date and end_date (inclusive).
    Conflicting requests are those in 'approved' or 'borrowed' status
    whose date range overlaps: req.start_date <= end_date and req.end_date >= start_date.
    """
    query = BorrowRequest.query.filter(
        BorrowRequest.laptop_id == laptop_id,
        BorrowRequest.status.in_(["approved", "borrowed"]),
        BorrowRequest.start_date <= end_date,
        BorrowRequest.end_date >= start_date
    )
    if exclude_request_id:
        query = query.filter(BorrowRequest.id != exclude_request_id)
        
    conflicts = query.first()
    return conflicts is None
