from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app.models import db, Laptop, BorrowRequest, User
from app.security import login_required, get_current_user, is_laptop_available, create_notification, log_audit_event

laptops_bp = Blueprint("laptops", __name__)

@laptops_bp.route("/find")
def find():
    # Search and filters
    search_query = request.args.get("q", "").strip()
    brand_filter = request.args.get("brand", "").strip()
    ram_filter = request.args.get("ram", "").strip()
    storage_filter = request.args.get("storage", "").strip()
    os_filter = request.args.get("os", "").strip()
    condition_filter = request.args.get("condition", "").strip()
    
    start_date_str = request.args.get("start_date", "").strip()
    end_date_str = request.args.get("end_date", "").strip()
    
    # Base query: only active laptops not under maintenance
    query = Laptop.query.filter(
        Laptop.is_active == True,
        Laptop.under_maintenance == False
    )
    
    if search_query:
        query = query.filter(
            (Laptop.brand.ilike(f"%{search_query}%")) |
            (Laptop.model.ilike(f"%{search_query}%")) |
            (Laptop.processor.ilike(f"%{search_query}%")) |
            (Laptop.academic_suitability.ilike(f"%{search_query}%"))
        )
        
    if brand_filter:
        query = query.filter(Laptop.brand.ilike(f"%{brand_filter}%"))
        
    if ram_filter:
        query = query.filter(Laptop.ram.ilike(f"%{ram_filter}%"))
        
    if storage_filter:
        query = query.filter(Laptop.storage.ilike(f"%{storage_filter}%"))
        
    if os_filter:
        query = query.filter(Laptop.operating_system.ilike(f"%{os_filter}%"))
        
    if condition_filter:
        query = query.filter(Laptop.condition == condition_filter)
        
    laptops = query.order_by(Laptop.created_at.desc()).all()
    
    # Filter by date range availability if dates provided
    filter_start = None
    filter_end = None
    if start_date_str and end_date_str:
        try:
            filter_start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            filter_end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            if filter_start <= filter_end:
                laptops = [l for l in laptops if is_laptop_available(l.id, filter_start, filter_end)]
            else:
                flash("Start date must be earlier than or equal to return date.", "warning")
        except ValueError:
            flash("Invalid date format. Please select dates properly.", "warning")
            
    # Distinct filter options for UI dropdowns
    brands = db.session.query(Laptop.brand).distinct().all()
    brands = sorted([b[0] for b in brands if b[0]])
    
    return render_template(
        "laptops/find_laptop.html",
        laptops=laptops,
        brands=brands,
        search_query=search_query,
        brand_filter=brand_filter,
        ram_filter=ram_filter,
        storage_filter=storage_filter,
        os_filter=os_filter,
        condition_filter=condition_filter,
        start_date=start_date_str,
        end_date=end_date_str
    )

@laptops_bp.route("/<int:laptop_id>")
def detail(laptop_id):
    laptop = db.get_or_404(Laptop, laptop_id)
    
    # Show upcoming booked intervals so borrower knows availability
    today = date.today()
    booked_intervals = BorrowRequest.query.filter(
        BorrowRequest.laptop_id == laptop.id,
        BorrowRequest.status.in_(["approved", "borrowed"]),
        BorrowRequest.end_date >= today
    ).order_by(BorrowRequest.start_date.asc()).all()
    
    return render_template(
        "laptops/laptop_details.html",
        laptop=laptop,
        booked_intervals=booked_intervals,
        today=today
    )

@laptops_bp.route("/<int:laptop_id>/request", methods=["POST"])
@login_required
def submit_request(laptop_id):
    user = get_current_user()
    laptop = db.get_or_404(Laptop, laptop_id)
    
    # Prevent lender from borrowing their own laptop
    if laptop.lender_id == user.id:
        flash("You cannot submit a borrowing request for your own laptop.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    start_date_str = request.form.get("start_date", "").strip()
    end_date_str = request.form.get("end_date", "").strip()
    purpose = request.form.get("purpose", "").strip()
    purpose_details = request.form.get("purpose_details", "").strip()
    borrower_message = request.form.get("borrower_message", "").strip()
    
    if not start_date_str or not end_date_str or not purpose:
        flash("Please provide requested pickup date, return date, and borrowing purpose.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Invalid date format.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    today = date.today()
    if start_date < today:
        flash("Pickup date cannot be in the past.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    if end_date < start_date:
        flash("Return date must be on or after pickup date.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    # Check if laptop is free for requested date range
    if not is_laptop_available(laptop.id, start_date, end_date):
        flash("This laptop already has an approved reservation for the selected dates. Please choose different dates.", "error")
        return redirect(url_for("laptops.detail", laptop_id=laptop.id))
        
    # Create request
    reference = BorrowRequest.generate_reference()
    borrow_req = BorrowRequest(
        reference_code=reference,
        laptop_id=laptop.id,
        borrower_id=user.id,
        start_date=start_date,
        end_date=end_date,
        purpose=purpose,
        purpose_details=purpose_details,
        borrower_message=borrower_message,
        status="pending"
    )
    
    db.session.add(borrow_req)
    db.session.commit()
    
    # Notify lender
    create_notification(
        user_id=laptop.lender_id,
        title="New Borrowing Request Received",
        message=f"{user.full_name} has requested to borrow your '{laptop.title}' from {start_date.strftime('%b %d')} to {end_date.strftime('%b %d')} for {purpose}.",
        category="request",
        link=url_for("lender.incoming_requests")
    )
    
    log_audit_event("REQUEST_CREATED", target_type="BorrowRequest", target_id=borrow_req.id, details=f"Ref: {reference}")
    flash(f"Borrowing request submitted successfully! Your tracking code is {reference}.", "success")
    return redirect(url_for("borrower.my_requests"))
