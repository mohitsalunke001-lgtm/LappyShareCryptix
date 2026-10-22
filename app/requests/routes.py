import io
from datetime import datetime, timezone, date
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, abort, current_app
from app.models import db, BorrowRequest, HandoverReturnRecord, User
from app.security import login_required, get_current_user, log_audit_event, create_notification, award_lappy_coins

requests_bp = Blueprint("requests", __name__)

@requests_bp.route("/<string:reference_code>")
@login_required
def details(reference_code):
    user = get_current_user()
    borrow_req = BorrowRequest.query.filter_by(reference_code=reference_code).first_or_404()
    
    # Security check: only borrower, lender, or admin can view request details
    is_borrower = (user.id == borrow_req.borrower_id)
    is_lender = (user.id == borrow_req.laptop.lender_id)
    if not (is_borrower or is_lender or user.is_admin):
        abort(403, description="You are not authorized to view this request.")
        
    record = borrow_req.record
    
    return render_template(
        "requests/details.html",
        request=borrow_req,
        record=record,
        is_borrower=is_borrower,
        is_lender=is_lender,
        user=user
    )

@requests_bp.route("/<int:request_id>/qr/<string:token_type>")
@login_required
def generate_qr(request_id, token_type):
    """
    Generates a secure QR code for handover or return verification.
    """
    user = get_current_user()
    borrow_req = db.get_or_404(BorrowRequest, request_id)
    
    # Authorized only for borrower, lender, or admin
    if not (user.id == borrow_req.borrower_id or user.id == borrow_req.laptop.lender_id or user.is_admin):
        abort(403)
        
    record = borrow_req.record
    if not record:
        abort(404, description="No handover record found.")
        
    token_val = record.handover_qr_token if token_type == "handover" else record.return_qr_token
    if not token_val:
        abort(400, description="Verification token is not available.")
        
    # Generate QR Code image in-memory
    qr_data = f"LAPPYSHARE:{token_type.upper()}:{borrow_req.reference_code}:{token_val}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f2b5c", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@requests_bp.route("/verify-qr", methods=["GET", "POST"])
@login_required
def verify_qr():
    user = get_current_user()
    
    if request.method == "POST":
        qr_code_str = request.form.get("qr_code_str", "").strip()
        
        # Format expected: LAPPYSHARE:<TYPE>:<REFERENCE>:<TOKEN> or raw TOKEN
        parts = qr_code_str.split(":")
        token_type = None
        token_val = None
        
        if len(parts) == 4 and parts[0] == "LAPPYSHARE":
            token_type = parts[1].lower()
            ref_code = parts[2]
            token_val = parts[3]
            record = HandoverReturnRecord.query.join(BorrowRequest).filter(BorrowRequest.reference_code == ref_code).first()
        else:
            token_val = qr_code_str
            # Look up by token in handover or return fields
            record = HandoverReturnRecord.query.filter(
                (HandoverReturnRecord.handover_qr_token == token_val) |
                (HandoverReturnRecord.return_qr_token == token_val)
            ).first()
            if record:
                token_type = "handover" if record.handover_qr_token == token_val else "return"
                
        if not record or not token_val:
            flash("Invalid or unrecognized QR token.", "error")
            return render_template("requests/verify_qr.html")
            
        borrow_req = record.request
        
        # Verify authorized participant
        if not (user.id == borrow_req.laptop.lender_id or user.id == borrow_req.borrower_id or user.is_admin):
            flash("You are not authorized to verify this reservation.", "error")
            return render_template("requests/verify_qr.html")
            
        now = datetime.now(timezone.utc)
        
        if token_type == "handover":
            if borrow_req.status != "approved":
                flash(f"Handover cannot be completed. Request is currently '{borrow_req.status}'.", "warning")
                return redirect(url_for("requests.details", reference_code=borrow_req.reference_code))
                
            record.handover_confirmed = True
            record.handover_date = now
            record.handover_condition = "Verified via QR Handover"
            borrow_req.status = "borrowed"
            db.session.commit()
            
            create_notification(
                user_id=borrow_req.borrower_id if user.id != borrow_req.borrower_id else borrow_req.laptop.lender_id,
                title="QR Handover Confirmed!",
                message=f"Handover for {borrow_req.laptop.title} verified successfully via secure QR token.",
                category="handover"
            )
            flash("Handover successfully confirmed via QR code! Laptop is now officially marked as borrowed.", "success")
            return redirect(url_for("requests.details", reference_code=borrow_req.reference_code))
            
        elif token_type == "return":
            if borrow_req.status not in ["borrowed", "overdue"]:
                flash(f"Return cannot be completed. Request status is '{borrow_req.status}'.", "warning")
                return redirect(url_for("requests.details", reference_code=borrow_req.reference_code))
                
            record.return_confirmed = True
            record.return_date = now
            record.return_condition = "Verified via QR Return"
            borrow_req.status = "returned"
            db.session.commit()
            
            # Award coins
            lender_reward = current_app.config.get("LAPPYCOIN_REWARDS", {}).get("COMPLETE_LENDING", 5)
            award_lappy_coins(
                user_id=borrow_req.laptop.lender_id,
                event_type="COMPLETE_LENDING",
                amount=lender_reward,
                description=f"Reward for completing lending of {borrow_req.laptop.title}",
                reference_id=f"request_lender:{borrow_req.id}"
            )
            
            if date.today() <= borrow_req.end_date:
                borrower_reward = current_app.config.get("LAPPYCOIN_REWARDS", {}).get("ONTIME_RETURN", 2)
                award_lappy_coins(
                    user_id=borrow_req.borrower_id,
                    event_type="ONTIME_RETURN",
                    amount=borrower_reward,
                    description=f"Reward for returning {borrow_req.laptop.title} on time",
                    reference_id=f"request_borrower:{borrow_req.id}"
                )
                
            flash("Laptop return successfully verified via QR code! Rewards have been credited.", "success")
            return redirect(url_for("requests.details", reference_code=borrow_req.reference_code))
            
    return render_template("requests/verify_qr.html")
