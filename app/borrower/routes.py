from datetime import date, datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import db, Laptop, BorrowRequest, User
from app.security import login_required, get_current_user, log_audit_event, create_notification

borrower_bp = Blueprint("borrower", __name__)

@borrower_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    
    # Counts
    available_laptops_count = Laptop.query.filter_by(
        is_active=True, 
        is_available=True, 
        under_maintenance=False
    ).count()
    
    pending_count = BorrowRequest.query.filter_by(borrower_id=user.id, status="pending").count()
    approved_count = BorrowRequest.query.filter_by(borrower_id=user.id, status="approved").count()
    borrowed_count = BorrowRequest.query.filter_by(borrower_id=user.id, status="borrowed").count()
    completed_count = BorrowRequest.query.filter_by(borrower_id=user.id, status="returned").count()
    
    # Active / Upcoming loans
    active_requests = BorrowRequest.query.filter(
        BorrowRequest.borrower_id == user.id,
        BorrowRequest.status.in_(["approved", "borrowed"])
    ).order_by(BorrowRequest.start_date.asc()).all()
    
    # Check for overdue
    today = date.today()
    for req in active_requests:
        if req.status == "borrowed" and req.end_date < today:
            req.is_overdue = True
        else:
            req.is_overdue = False
            
    # Recent requests
    recent_requests = BorrowRequest.query.filter_by(borrower_id=user.id)\
        .order_by(BorrowRequest.created_at.desc()).limit(5).all()
        
    return render_template(
        "borrower/dashboard.html",
        user=user,
        available_laptops_count=available_laptops_count,
        pending_count=pending_count,
        approved_count=approved_count,
        borrowed_count=borrowed_count,
        completed_count=completed_count,
        active_requests=active_requests,
        recent_requests=recent_requests
    )

@borrower_bp.route("/requests")
@login_required
def my_requests():
    user = get_current_user()
    status_filter = request.args.get("status", "all").strip().lower()
    
    query = BorrowRequest.query.filter_by(borrower_id=user.id)
    if status_filter != "all" and status_filter in ["pending", "approved", "rejected", "cancelled", "borrowed", "returned", "overdue"]:
        if status_filter == "overdue":
            today = date.today()
            query = query.filter(BorrowRequest.status == "borrowed", BorrowRequest.end_date < today)
        else:
            query = query.filter_by(status=status_filter)
            
    requests_list = query.order_by(BorrowRequest.created_at.desc()).all()
    today = date.today()
    
    return render_template(
        "borrower/my_requests.html",
        requests=requests_list,
        status_filter=status_filter,
        today=today
    )

@borrower_bp.route("/requests/<int:request_id>/cancel", methods=["POST"])
@login_required
def cancel_request(request_id):
    user = get_current_user()
    borrow_req = BorrowRequest.query.filter_by(id=request_id, borrower_id=user.id).first_or_404()
    
    if borrow_req.status not in ["pending", "approved"]:
        flash(f"Cannot cancel request in status '{borrow_req.status}'.", "error")
        return redirect(url_for("borrower.my_requests"))
        
    reason = request.form.get("cancellation_reason", "Cancelled by borrower").strip()
    old_status = borrow_req.status
    borrow_req.status = "cancelled"
    borrow_req.cancellation_reason = reason
    db.session.commit()
    
    # Notify lender if request was already approved or pending
    create_notification(
        user_id=borrow_req.laptop.lender_id,
        title="Borrowing Request Cancelled",
        message=f"{user.full_name} cancelled their request ({borrow_req.reference_code}) for {borrow_req.laptop.title}.",
        category="request",
        link=url_for("lender.incoming_requests")
    )
    
    log_audit_event("REQUEST_CANCELLED", target_type="BorrowRequest", target_id=borrow_req.id, details=f"From status: {old_status}")
    flash("Your borrowing request has been cancelled.", "info")
    return redirect(url_for("borrower.my_requests"))
