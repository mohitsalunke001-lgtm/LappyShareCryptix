import os
import tempfile
from datetime import datetime, timezone
from flask import Flask, render_template, request, session, g
from app.models import db, User, Notification
from app.security import generate_csrf_token, verify_csrf, get_current_user
from config import config_by_name

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
        
    instance_path = None
    if os.environ.get("VERCEL"):
        instance_path = os.path.join(tempfile.gettempdir(), "lappyshare-instance")

    app = Flask(__name__, instance_path=instance_path)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))
    
    # Ensure instance and upload directories exist
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Initialize database
    db.init_app(app)
    
    # CSRF protection
    @app.before_request
    def run_csrf():
        verify_csrf()
        
    # Context processor for templates
    @app.context_processor
    def inject_context():
        user = get_current_user()
        unread_count = 0
        if user:
            try:
                unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
            except Exception:
                unread_count = 0
                
        return {
            "current_user": user,
            "csrf_token": generate_csrf_token,
            "unread_count": unread_count,
            "now_utc": datetime.now(timezone.utc),
            "app_name": "LappyShare",
            "rewards_config": app.config.get("LAPPYCOIN_REWARDS", {})
        }
        
    # Custom template filters
    @app.template_filter("format_date")
    def format_date(value, fmt="%b %d, %Y"):
        if not value:
            return "N/A"
        return value.strftime(fmt)

    @app.template_filter("status_badge")
    def status_badge(status):
        badges = {
            "pending": "badge-warning",
            "approved": "badge-info",
            "borrowed": "badge-primary",
            "returned": "badge-success",
            "rejected": "badge-danger",
            "cancelled": "badge-secondary",
            "overdue": "badge-danger",
            "Available": "badge-success",
            "Currently Borrowed": "badge-primary",
            "Under Maintenance": "badge-warning",
            "Deactivated": "badge-secondary"
        }
        return badges.get(status, "badge-secondary")

    # Register Blueprints
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.borrower.routes import borrower_bp
    from app.lender.routes import lender_bp
    from app.laptops.routes import laptops_bp
    from app.requests.routes import requests_bp
    from app.rewards.routes import rewards_bp
    from app.admin.routes import admin_bp
    from app.notifications.routes import notifications_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(borrower_bp, url_prefix="/borrower")
    app.register_blueprint(lender_bp, url_prefix="/lender")
    app.register_blueprint(laptops_bp, url_prefix="/laptops")
    app.register_blueprint(requests_bp, url_prefix="/requests")
    app.register_blueprint(rewards_bp, url_prefix="/rewards")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(notifications_bp, url_prefix="/notifications")

    if os.environ.get("VERCEL"):
        with app.app_context():
            db.create_all()
    
    # Custom error handlers
    @app.errorhandler(400)
    def bad_request_error(e):
        return render_template("errors/400.html", description=str(e.description if hasattr(e, 'description') else e)), 400

    @app.errorhandler(403)
    def forbidden_error(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
