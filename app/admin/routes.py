from datetime import datetime, timezone, date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, User, Laptop, BorrowRequest, LappyCoinTransaction, AuditLog, HandoverReturnRecord
from app.security import admin_required, get_current_user, log_audit_event, award_lappy_coins, create_notification

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/dashboard")
@admin_required
def dashboard():
    today = date.today()
    
    total_users = User.query.count()
    borrowers_count = User.query.filter_by(role="borrower").count()
    lenders_count = User.query.filter_by(role="lender").count()
    
    total_laptops = Laptop.query.count()
    available_laptops = Laptop.query.filter_by(is_active=True, is_available=True, under_maintenance=False).count()
    maintenance_laptops = Laptop.query.filter_by(under_maintenance=True).count()
    
    pending_requests = BorrowRequest.query.filter_by(status="pending").count()
    approved_reservations = BorrowRequest.query.filter_by(status="approved").count()
    borrowed_active = BorrowRequest.query.filter_by(status="borrowed").count()
    completed_returns = BorrowRequest.query.filter_by(status="returned").count()
    
    # Overdue loans
    overdue_count = BorrowRequest.query.filter(
        BorrowRequest.status == "borrowed",
        BorrowRequest.end_date < today
    ).count()
    
    # Total coins in circulation
    total_coins_issued = db.session.query(db.func.sum(LappyCoinTransaction.amount))\
        .filter(LappyCoinTransaction.amount > 0).scalar() or 0
        
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    recent_requests = BorrowRequest.query.order_by(BorrowRequest.created_at.desc()).limit(8).all()
    
    # Chart data: Status breakdown
    statuses = ["pending", "approved", "borrowed", "returned", "rejected", "cancelled"]
    status_counts = {s: BorrowRequest.query.filter_by(status=s).count() for s in statuses}
    
    # Chart data: Top laptop brands
    brand_stats = db.session.query(Laptop.brand, db.func.count(Laptop.id))\
        .group_by(Laptop.brand).order_by(db.func.count(Laptop.id).desc()).limit(5).all()
        
    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        borrowers_count=borrowers_count,
        lenders_count=lenders_count,
        total_laptops=total_laptops,
        available_laptops=available_laptops,
        maintenance_laptops=maintenance_laptops,
        pending_requests=pending_requests,
        approved_reservations=approved_reservations,
        borrowed_active=borrowed_active,
        completed_returns=completed_returns,
        overdue_count=overdue_count,
        total_coins_issued=total_coins_issued,
        recent_logs=recent_logs,
        recent_requests=recent_requests,
        status_counts=status_counts,
        brand_stats=brand_stats,
        today=today
    )

@admin_bp.route("/students")
@admin_required
def students():
    search = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()
    status_filter = request.args.get("status", "").strip()
    
    query = User.query
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.college_name.ilike(f"%{search}%")) |
            (User.department.ilike(f"%{search}%")) |
            (User.roll_number.ilike(f"%{search}%"))
        )
    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter:
        is_active = (status_filter == "active")
        query = query.filter_by(is_active=is_active)
        
    users = query.order_by(User.created_at.desc()).all()
    return render_template("admin/students.html", users=users, search=search, role_filter=role_filter, status_filter=status_filter)

@admin_bp.route("/students/<int:user_id>")
@admin_required
def student_detail(user_id):
    student = db.get_or_404(User, user_id)
    laptops = Laptop.query.filter_by(lender_id=student.id).all()
    borrowed_requests = BorrowRequest.query.filter_by(borrower_id=student.id).order_by(BorrowRequest.created_at.desc()).all()
    transactions = LappyCoinTransaction.query.filter_by(user_id=student.id).order_by(LappyCoinTransaction.created_at.desc()).all()
    
    return render_template(
        "admin/student_detail.html",
        student=student,
        laptops=laptops,
        borrowed_requests=borrowed_requests,
        transactions=transactions
    )

@admin_bp.route("/students/<int:user_id>/toggle-status", methods=["POST"])
@admin_required
def toggle_student_status(user_id):
    current_admin = get_current_user()
    if current_admin.id == user_id:
        flash("You cannot suspend your own administrator account.", "error")
        return redirect(url_for("admin.students"))
        
    user = db.get_or_404(User, user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status_text = "activated" if user.is_active else "suspended"
    log_audit_event(f"USER_{status_text.upper()}", target_type="User", target_id=user.id)
    flash(f"User '{user.full_name}' has been {status_text}.", "info")
    return redirect(url_for("admin.students"))

@admin_bp.route("/laptops")
@admin_required
def laptops():
    search = request.args.get("search", "").strip()
    query = Laptop.query
    if search:
        query = query.filter(
            (Laptop.brand.ilike(f"%{search}%")) |
            (Laptop.model.ilike(f"%{search}%")) |
            (Laptop.processor.ilike(f"%{search}%"))
        )
    laptops_list = query.order_by(Laptop.created_at.desc()).all()
    return render_template("admin/laptops.html", laptops=laptops_list, search=search)

@admin_bp.route("/laptops/<int:laptop_id>/toggle-maintenance", methods=["POST"])
@admin_required
def toggle_laptop_maintenance(laptop_id):
    laptop = db.get_or_404(Laptop, laptop_id)
    laptop.under_maintenance = not laptop.under_maintenance
    if laptop.under_maintenance:
        laptop.maintenance_notes = request.form.get("notes", "Marked under maintenance by administrator.")
    db.session.commit()
    
    status_str = "flagged for maintenance" if laptop.under_maintenance else "cleared from maintenance"
    log_audit_event("ADMIN_LAPTOP_MAINTENANCE_TOGGLE", target_type="Laptop", target_id=laptop.id, details=status_str)
    flash(f"Laptop '{laptop.title}' is now {status_str}.", "info")
    return redirect(url_for("admin.laptops"))

@admin_bp.route("/requests")
@admin_required
def requests():
    status_filter = request.args.get("status", "").strip()
    query = BorrowRequest.query
    today = date.today()
    
    if status_filter:
        if status_filter == "overdue":
            query = query.filter(BorrowRequest.status == "borrowed", BorrowRequest.end_date < today)
        else:
            query = query.filter_by(status=status_filter)
            
    requests_list = query.order_by(BorrowRequest.created_at.desc()).all()
    return render_template("admin/requests.html", requests=requests_list, status_filter=status_filter, today=today)

@admin_bp.route("/coins", methods=["GET", "POST"])
@admin_required
def coins():
    current_admin = get_current_user()
    
    if request.method == "POST":
        user_id = request.form.get("user_id")
        amount_str = request.form.get("amount")
        reason = request.form.get("reason", "").strip()
        
        if not user_id or not amount_str or not reason:
            flash("User, coin amount, and justification reason are all strictly required.", "error")
            return redirect(url_for("admin.coins"))
            
        try:
            amount = int(amount_str)
            target_user = db.get_or_404(User, int(user_id))
        except ValueError:
            flash("Invalid amount or user specified.", "error")
            return redirect(url_for("admin.coins"))
            
        success, msg = award_lappy_coins(
            user_id=target_user.id,
            event_type="ADMIN_ADJUSTMENT",
            amount=amount,
            description=f"Admin Adjustment: {reason}",
            reference_id=f"admin_adj_{int(datetime.now().timestamp())}",
            admin_id=current_admin.id
        )
        
        if success:
            log_audit_event(
                "LAPPYCOIN_MANUAL_ADJUSTMENT",
                target_type="User",
                target_id=target_user.id,
                details=f"Amount: {amount}, Reason: {reason}"
            )
            flash(f"Successfully adjusted {amount} LappyCoins for {target_user.full_name}. New balance: {target_user.coin_balance}", "success")
        else:
            flash(f"Failed to adjust coins: {msg}", "error")
            
        return redirect(url_for("admin.coins"))
        
    users = User.query.order_by(User.full_name.asc()).all()
    transactions = LappyCoinTransaction.query.order_by(LappyCoinTransaction.created_at.desc()).limit(100).all()
    return render_template("admin/coins.html", users=users, transactions=transactions)

@admin_bp.route("/audit-logs")
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/audit_logs.html", logs=logs)

@admin_bp.route("/reports")
@admin_required
def reports():
    today = date.today()
    total_loans = BorrowRequest.query.filter(BorrowRequest.status.in_(["borrowed", "returned"])).count()
    overdue_count = BorrowRequest.query.filter(BorrowRequest.status == "borrowed", BorrowRequest.end_date < today).count()
    active_lenders = db.session.query(Laptop.lender_id).distinct().count()
    active_borrowers = db.session.query(BorrowRequest.borrower_id).distinct().count()
    
    # Top lenders
    top_lenders = db.session.query(
        User, db.func.count(Laptop.id).label("laptop_count")
    ).join(Laptop, Laptop.lender_id == User.id)\
     .group_by(User.id).order_by(db.desc("laptop_count")).limit(5).all()
     
    return render_template(
        "admin/reports.html",
        total_loans=total_loans,
        overdue_count=overdue_count,
        active_lenders=active_lenders,
        active_borrowers=active_borrowers,
        top_lenders=top_lenders
    )
