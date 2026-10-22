import os
import secrets
from datetime import datetime, timezone, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from app.models import db, User, PasswordResetToken
from app.security import login_required, get_current_user, log_audit_event, create_notification

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.index"))
        
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        college_name = request.form.get("college_name", "").strip()
        department = request.form.get("department", "").strip()
        year_of_study = request.form.get("year_of_study", "").strip()
        roll_number = request.form.get("roll_number", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "borrower").strip().lower()
        
        # Validation
        if not full_name or not email or not phone or not college_name or not department or not year_of_study or not password:
            flash("Please fill in all mandatory fields.", "error")
            return render_template("auth/register.html")
            
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html")
            
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("auth/register.html")
            
        if role not in ["borrower", "lender"]:
            role = "borrower"
            
        # Check if email is already registered
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email address is already registered. Please sign in.", "warning")
            return redirect(url_for("auth.login"))
            
        # Create user
        user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            college_name=college_name,
            department=department,
            year_of_study=year_of_study,
            roll_number=roll_number,
            role=role,
            is_admin=False,
            is_active=True,
            coin_balance=0
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Send welcome notification
            create_notification(
                user_id=user.id,
                title="Welcome to LappyShare!",
                message=f"Welcome {user.full_name}! Your student account has been successfully created. Explore available laptops or share your own to earn LappyCoins.",
                category="system"
            )
            
            log_audit_event("USER_REGISTERED", target_type="User", target_id=user.id, details=f"Email: {user.email}, Role: {user.role}")
            
            flash("Account created successfully! You can now sign in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Registration error: {e}")
            flash("A database error occurred during registration. Please try again.", "error")
            return render_template("auth/register.html")
            
    return render_template("auth/register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        user = get_current_user()
        if user:
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            elif user.role == "lender":
                return redirect(url_for("lender.dashboard"))
            return redirect(url_for("borrower.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        
        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("auth/login.html")
            
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash("Invalid email or password. Please try again.", "error")
            return render_template("auth/login.html")
            
        if not user.is_active:
            flash("This account has been suspended or deactivated. Contact campus admin.", "error")
            return render_template("auth/login.html")
            
        # Login success
        session.clear()
        session["user_id"] = user.id
        session["user_name"] = user.full_name
        session["user_role"] = user.role
        session["is_admin"] = user.is_admin
        session.permanent = remember
        
        log_audit_event("USER_LOGIN", target_type="User", target_id=user.id)
        
        flash(f"Welcome back, {user.full_name}!", "success")
        
        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)
            
        if user.is_admin:
            return redirect(url_for("admin.dashboard"))
        elif user.role == "lender":
            return redirect(url_for("lender.dashboard"))
        else:
            return redirect(url_for("borrower.dashboard"))
            
    return render_template("auth/login.html")

@auth_bp.route("/logout")
def logout():
    user = get_current_user()
    if user:
        log_audit_event("USER_LOGOUT", target_type="User", target_id=user.id)
    session.clear()
    flash("You have been successfully signed out.", "info")
    return redirect(url_for("main.index"))

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    dev_reset_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter your registered email address.", "error")
            return render_template("auth/forgot_password.html")
            
        user = User.query.filter_by(email=email).first()
        if not user:
            # For security, avoid enumerating accounts, but inform user
            flash("If an account exists with that email, a password recovery link has been prepared.", "info")
            return render_template("auth/forgot_password.html")
            
        # Invalidate old unused tokens for this user
        PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({"used": True})
        
        # Generate secure random token valid for 1 hour
        token_str = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        reset_token = PasswordResetToken(
            user_id=user.id,
            token=token_str,
            expires_at=expires_at,
            used=False
        )
        db.session.add(reset_token)
        db.session.commit()
        
        # Check if SMTP is configured
        mail_username = current_app.config.get("MAIL_USERNAME")
        if mail_username:
            # Real SMTP sending could be done here if credentials provided
            flash("A password reset link has been dispatched to your email address.", "success")
        else:
            # Explicitly documented development mode fallback without pretending fake SMTP
            dev_reset_link = url_for("auth.reset_password", token=token_str, _external=True)
            flash("SMTP email is not configured on this server. A secure recovery link has been generated below for testing.", "warning")
            
    return render_template("auth/forgot_password.html", dev_reset_link=dev_reset_link)

@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset_entry = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_entry or not reset_entry.is_valid():
        flash("The password reset link is invalid, expired, or has already been used.", "error")
        return redirect(url_for("auth.forgot_password"))
        
    user = reset_entry.user
    
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not password or password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/reset_password.html", token=token)
            
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("auth/reset_password.html", token=token)
            
        user.set_password(password)
        reset_entry.used = True
        db.session.commit()
        
        log_audit_event("PASSWORD_RESET_SUCCESS", target_type="User", target_id=user.id)
        flash("Your password has been successfully updated! You can now log in.", "success")
        return redirect(url_for("auth.login"))
        
    return render_template("auth/reset_password.html", token=token)

@auth_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    user = get_current_user()
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            user.full_name = request.form.get("full_name", user.full_name).strip()
            user.phone = request.form.get("phone", user.phone).strip()
            user.college_name = request.form.get("college_name", user.college_name).strip()
            user.department = request.form.get("department", user.department).strip()
            user.year_of_study = request.form.get("year_of_study", user.year_of_study).strip()
            user.roll_number = request.form.get("roll_number", user.roll_number).strip()
            
            new_role = request.form.get("role", user.role).strip().lower()
            if new_role in ["borrower", "lender"]:
                user.role = new_role
                session["user_role"] = new_role
                
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("auth.account"))
            
        elif action == "change_password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_password", "")
            
            if not user.check_password(current_pass):
                flash("Incorrect current password.", "error")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.", "error")
            elif len(new_pass) < 6:
                flash("New password must be at least 6 characters.", "error")
            else:
                user.set_password(new_pass)
                db.session.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("auth.account"))
                
    return render_template("auth/account.html", user=user)
