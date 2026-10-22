import os
import secrets
from datetime import datetime, timezone, date
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from app.models import db, Laptop, BorrowRequest, HandoverReturnRecord, User
from app.security import (
    login_required, get_current_user, log_audit_event, 
    create_notification, award_lappy_coins, is_laptop_available
)

lender_bp = Blueprint("lender", __name__)

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]

@lender_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    
    # Counts
    my_laptops = Laptop.query.filter_by(lender_id=user.id).all()
    total_laptops = len(my_laptops)
    available_laptops = sum(1 for lap in my_laptops if lap.is_active and lap.is_available and not lap.under_maintenance)
    
    laptop_ids = [l.id for l in my_laptops]
    
    pending_requests_count = 0
    approved_requests_count = 0
    lent_count = 0
    completed_lending_count = 0
    
    if laptop_ids:
        pending_requests_count = BorrowRequest.query.filter(
            BorrowRequest.laptop_id.in_(laptop_ids),
            BorrowRequest.status == "pending"
        ).count()
        
        approved_requests_count = BorrowRequest.query.filter(
            BorrowRequest.laptop_id.in_(laptop_ids),
            BorrowRequest.status == "approved"
        ).count()
        
        lent_count = BorrowRequest.query.filter(
            BorrowRequest.laptop_id.in_(laptop_ids),
            BorrowRequest.status == "borrowed"
        ).count()
        
        completed_lending_count = BorrowRequest.query.filter(
            BorrowRequest.laptop_id.in_(laptop_ids),
            BorrowRequest.status == "returned"
        ).count()
        
    recent_incoming = []
    if laptop_ids:
        recent_incoming = BorrowRequest.query.filter(BorrowRequest.laptop_id.in_(laptop_ids))\
            .order_by(BorrowRequest.created_at.desc()).limit(6).all()
            
    return render_template(
        "lender/dashboard.html",
        user=user,
        total_laptops=total_laptops,
        available_laptops=available_laptops,
        pending_requests_count=pending_requests_count,
        approved_requests_count=approved_requests_count,
        lent_count=lent_count,
        completed_lending_count=completed_lending_count,
        my_laptops=my_laptops[:4],
        recent_incoming=recent_incoming
    )

@lender_bp.route("/laptops")
@login_required
def my_laptops():
    user = get_current_user()
    laptops = Laptop.query.filter_by(lender_id=user.id).order_by(Laptop.created_at.desc()).all()
    return render_template("lender/my_laptops.html", laptops=laptops)

@lender_bp.route("/laptops/new", methods=["GET", "POST"])
@login_required
def add_laptop():
    user = get_current_user()
    
    if request.method == "POST":
        brand = request.form.get("brand", "").strip()
        model = request.form.get("model", "").strip()
        processor = request.form.get("processor", "").strip()
        ram = request.form.get("ram", "").strip()
        storage = request.form.get("storage", "").strip()
        operating_system = request.form.get("operating_system", "").strip()
        condition = request.form.get("condition", "").strip()
        academic_suitability = request.form.get("academic_suitability", "").strip()
        lending_guidelines = request.form.get("lending_guidelines", "").strip()
        description = request.form.get("description", "").strip()
        
        if not brand or not model or not processor or not ram or not storage or not operating_system or not condition:
            flash("Please fill in all required laptop specifications.", "error")
            return render_template("lender/laptop_form.html", action="Add")
            
        # Handle optional image upload
        image_path = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename != "":
                if allowed_file(file.filename):
                    filename = f"laptop_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                    upload_dest = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                    file.save(upload_dest)
                    image_path = f"uploads/{filename}"
                else:
                    flash("Invalid image file format. Allowed: PNG, JPG, JPEG, WEBP.", "error")
                    return render_template("lender/laptop_form.html", action="Add")
                    
        laptop = Laptop(
            lender_id=user.id,
            brand=brand,
            model=model,
            processor=processor,
            ram=ram,
            storage=storage,
            operating_system=operating_system,
            condition=condition,
            academic_suitability=academic_suitability,
            lending_guidelines=lending_guidelines,
            description=description,
            image_path=image_path,
            is_available=True,
            is_active=True,
            under_maintenance=False
        )
        
        db.session.add(laptop)
        db.session.commit()
        
        # Award LappyCoins for listing an eligible laptop (+10 coins)
        reward_amount = current_app.config.get("LAPPYCOIN_REWARDS", {}).get("LIST_LAPTOP", 10)
        award_lappy_coins(
            user_id=user.id,
            event_type="LIST_LAPTOP",
            amount=reward_amount,
            description=f"Reward for listing laptop {laptop.title}",
            reference_id=f"laptop:{laptop.id}"
        )
        
        log_audit_event("LAPTOP_CREATED", target_type="Laptop", target_id=laptop.id, details=f"Title: {laptop.title}")
        flash(f"Laptop '{laptop.title}' has been listed successfully! You earned +{reward_amount} LappyCoins.", "success")
        return redirect(url_for("lender.my_laptops"))
        
    return render_template("lender/laptop_form.html", action="Add", laptop=None)

@lender_bp.route("/laptops/<int:laptop_id>/edit", methods=["GET", "POST"])
@login_required
def edit_laptop(laptop_id):
    user = get_current_user()
    laptop = Laptop.query.filter_by(id=laptop_id, lender_id=user.id).first_or_404()
    
    if request.method == "POST":
        laptop.brand = request.form.get("brand", laptop.brand).strip()
        laptop.model = request.form.get("model", laptop.model).strip()
        laptop.processor = request.form.get("processor", laptop.processor).strip()
        laptop.ram = request.form.get("ram", laptop.ram).strip()
        laptop.storage = request.form.get("storage", laptop.storage).strip()
        laptop.operating_system = request.form.get("operating_system", laptop.operating_system).strip()
        laptop.condition = request.form.get("condition", laptop.condition).strip()
        laptop.academic_suitability = request.form.get("academic_suitability", laptop.academic_suitability).strip()
        laptop.lending_guidelines = request.form.get("lending_guidelines", laptop.lending_guidelines).strip()
        laptop.description = request.form.get("description", laptop.description).strip()
        
        laptop.is_active = bool(request.form.get("is_active"))
        laptop.under_maintenance = bool(request.form.get("under_maintenance"))
        laptop.maintenance_notes = request.form.get("maintenance_notes", "").strip()
        
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename != "":
                if allowed_file(file.filename):
                    filename = f"laptop_{user.id}_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
                    upload_dest = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
                    file.save(upload_dest)
                    laptop.image_path = f"uploads/{filename}"
                else:
                    flash("Invalid image file format. Allowed: PNG, JPG, JPEG, WEBP.", "error")
                    return render_template("lender/laptop_form.html", action="Edit", laptop=laptop)
                    
        db.session.commit()
        log_audit_event("LAPTOP_UPDATED", target_type="Laptop", target_id=laptop.id)
        flash("Laptop details updated successfully.", "success")
        return redirect(url_for("lender.my_laptops"))
        
    return render_template("lender/laptop_form.html", action="Edit", laptop=laptop)

@lender_bp.route("/laptops/<int:laptop_id>/toggle-status", methods=["POST"])
@login_required
def toggle_laptop_status(laptop_id):
    user = get_current_user()
    laptop = Laptop.query.filter_by(id=laptop_id, lender_id=user.id).first_or_404()
    
    laptop.is_active = not laptop.is_active
    db.session.commit()
    
    status_str = "activated" if laptop.is_active else "deactivated"
    flash(f"Laptop '{laptop.title}' has been {status_str}.", "info")
    return redirect(url_for("lender.my_laptops"))

@lender_bp.route("/requests")
@login_required
def incoming_requests():
    user = get_current_user()
    status_filter = request.args.get("status", "all").strip().lower()
    
    # Get requests for all laptops owned by this lender
    query = BorrowRequest.query.join(Laptop).filter(Laptop.lender_id == user.id)
    
    if status_filter != "all" and status_filter in ["pending", "approved", "rejected", "cancelled", "borrowed", "returned"]:
        query = query.filter(BorrowRequest.status == status_filter)
        
    requests_list = query.order_by(BorrowRequest.created_at.desc()).all()
    
    return render_template(
        "lender/incoming_requests.html",
        requests=requests_list,
        status_filter=status_filter
    )

@lender_bp.route("/requests/<int:request_id>/accept", methods=["POST"])
@login_required
def accept_request(request_id):
    user = get_current_user()
    borrow_req = BorrowRequest.query.join(Laptop).filter(
        BorrowRequest.id == request_id,
        Laptop.lender_id == user.id
    ).first_or_404()
    
    if borrow_req.status != "pending":
        flash(f"Cannot accept request with status '{borrow_req.status}'.", "error")
        return redirect(url_for("lender.incoming_requests"))
        
    # Check availability on backend to prevent conflicting approved reservations
    if not is_laptop_available(borrow_req.laptop_id, borrow_req.start_date, borrow_req.end_date, exclude_request_id=borrow_req.id):
        flash("Conflict detected: This laptop is already booked for an overlapping period.", "error")
        return redirect(url_for("lender.incoming_requests"))
        
    # Transactional update
    borrow_req.status = "approved"
    borrow_req.decision_at = datetime.now(timezone.utc)
    
    # Initialize HandoverReturnRecord if not present
    if not borrow_req.record:
        qr_token = secrets.token_hex(16)
        record = HandoverReturnRecord(
            request_id=borrow_req.id,
            handover_qr_token=qr_token,
            return_qr_token=secrets.token_hex(16)
        )
        db.session.add(record)
        
    db.session.commit()
    
    # Notify borrower
    create_notification(
        user_id=borrow_req.borrower_id,
        title="Request Approved!",
        message=f"Good news! Your borrowing request ({borrow_req.reference_code}) for '{borrow_req.laptop.title}' has been accepted by {user.full_name}. You can now view coordination details.",
        category="approval",
        link=url_for("borrower.my_requests")
    )
    
    log_audit_event("REQUEST_ACCEPTED", target_type="BorrowRequest", target_id=borrow_req.id)
    flash(f"Request {borrow_req.reference_code} accepted successfully! You can now coordinate handover with {borrow_req.borrower.full_name}.", "success")
    return redirect(url_for("lender.incoming_requests"))

@lender_bp.route("/requests/<int:request_id>/reject", methods=["POST"])
@login_required
def reject_request(request_id):
    user = get_current_user()
    borrow_req = BorrowRequest.query.join(Laptop).filter(
        BorrowRequest.id == request_id,
        Laptop.lender_id == user.id
    ).first_or_404()
    
    if borrow_req.status != "pending":
        flash("Can only reject pending requests.", "error")
        return redirect(url_for("lender.incoming_requests"))
        
    reason = request.form.get("rejection_reason", "").strip() or "Unavailable or conflicting academic schedule"
    borrow_req.status = "rejected"
    borrow_req.rejection_reason = reason
    borrow_req.decision_at = datetime.now(timezone.utc)
    db.session.commit()
    
    # Notify borrower
    create_notification(
        user_id=borrow_req.borrower_id,
        title="Request Update",
        message=f"Your request ({borrow_req.reference_code}) for '{borrow_req.laptop.title}' was declined. Reason: {reason}",
        category="request",
        link=url_for("borrower.my_requests")
    )
    
    log_audit_event("REQUEST_REJECTED", target_type="BorrowRequest", target_id=borrow_req.id, details=reason)
    flash(f"Request {borrow_req.reference_code} has been rejected.", "info")
    return redirect(url_for("lender.incoming_requests"))

@lender_bp.route("/requests/<int:request_id>/handover", methods=["GET", "POST"])
@login_required
def process_handover(request_id):
    user = get_current_user()
    borrow_req = BorrowRequest.query.join(Laptop).filter(
        BorrowRequest.id == request_id,
        Laptop.lender_id == user.id
    ).first_or_404()
    
    if borrow_req.status != "approved":
        flash("Only approved requests can be handed over.", "error")
        return redirect(url_for("lender.incoming_requests"))
        
    record = borrow_req.record
    if not record:
        record = HandoverReturnRecord(
            request_id=borrow_req.id,
            handover_qr_token=secrets.token_hex(16),
            return_qr_token=secrets.token_hex(16)
        )
        db.session.add(record)
        db.session.commit()
        
    if request.method == "POST":
        condition = request.form.get("handover_condition", "Good").strip()
        notes = request.form.get("handover_notes", "").strip()
        
        record.handover_date = datetime.now(timezone.utc)
        record.handover_condition = condition
        record.handover_notes = notes
        record.handover_confirmed = True
        
        borrow_req.status = "borrowed"
        db.session.commit()
        
        create_notification(
            user_id=borrow_req.borrower_id,
            title="Laptop Handed Over",
            message=f"Handover confirmed for {borrow_req.laptop.title}! Expected return date: {borrow_req.end_date.strftime('%b %d, %Y')}.",
            category="handover",
            link=url_for("borrower.my_requests")
        )
        
        log_audit_event("HANDOVER_COMPLETED", target_type="BorrowRequest", target_id=borrow_req.id)
        flash("Handover successfully confirmed! Laptop is now marked as actively borrowed.", "success")
        return redirect(url_for("lender.incoming_requests"))
        
    return render_template("lender/handover.html", request=borrow_req, record=record)

@lender_bp.route("/requests/<int:request_id>/return", methods=["GET", "POST"])
@login_required
def process_return(request_id):
    user = get_current_user()
    borrow_req = BorrowRequest.query.join(Laptop).filter(
        BorrowRequest.id == request_id,
        Laptop.lender_id == user.id
    ).first_or_404()
    
    if borrow_req.status not in ["borrowed", "overdue"]:
        flash("Only currently borrowed laptops can be returned.", "error")
        return redirect(url_for("lender.incoming_requests"))
        
    record = borrow_req.record
    if not record:
        record = HandoverReturnRecord(request_id=borrow_req.id)
        db.session.add(record)
        db.session.commit()
        
    if request.method == "POST":
        return_condition = request.form.get("return_condition", "Good").strip()
        notes = request.form.get("return_notes", "").strip()
        damage_reported = bool(request.form.get("damage_reported"))
        damage_details = request.form.get("damage_details", "").strip() if damage_reported else None
        
        now = datetime.now(timezone.utc)
        record.return_date = now
        record.return_condition = return_condition
        record.return_notes = notes
        record.damage_reported = damage_reported
        record.damage_details = damage_details
        record.return_confirmed = True
        
        borrow_req.status = "returned"
        
        # Check if laptop should be put under maintenance due to damage
        if damage_reported:
            borrow_req.laptop.under_maintenance = True
            borrow_req.laptop.maintenance_notes = f"Damage reported on return ({now.strftime('%Y-%m-%d')}): {damage_details}"
            
        db.session.commit()
        
        # 1. Reward lender for completing eligible lending period (+5 coins)
        lender_reward = current_app.config.get("LAPPYCOIN_REWARDS", {}).get("COMPLETE_LENDING", 5)
        award_lappy_coins(
            user_id=user.id,
            event_type="COMPLETE_LENDING",
            amount=lender_reward,
            description=f"Reward for completing lending period of {borrow_req.laptop.title}",
            reference_id=f"request_lender:{borrow_req.id}"
        )
        
        # 2. If returned on or before end_date, reward borrower for on-time return (+2 coins)
        today = date.today()
        if today <= borrow_req.end_date and not damage_reported:
            borrower_reward = current_app.config.get("LAPPYCOIN_REWARDS", {}).get("ONTIME_RETURN", 2)
            award_lappy_coins(
                user_id=borrow_req.borrower_id,
                event_type="ONTIME_RETURN",
                amount=borrower_reward,
                description=f"Reward for returning {borrow_req.laptop.title} on time and in good condition",
                reference_id=f"request_borrower:{borrow_req.id}"
            )
            
        create_notification(
            user_id=borrow_req.borrower_id,
            title="Laptop Return Confirmed",
            message=f"Return confirmed for {borrow_req.laptop.title}. Thank you for being a responsible member of LappyShare!",
            category="return",
            link=url_for("borrower.my_requests")
        )
        
        log_audit_event("RETURN_COMPLETED", target_type="BorrowRequest", target_id=borrow_req.id, details=f"Damage reported: {damage_reported}")
        flash(f"Return successfully registered! You earned +{lender_reward} LappyCoins.", "success")
        return redirect(url_for("lender.incoming_requests"))
        
    return render_template("lender/return.html", request=borrow_req, record=record)
