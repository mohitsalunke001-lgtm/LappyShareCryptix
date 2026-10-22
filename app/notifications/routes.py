from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from app.models import db, Notification
from app.security import login_required, get_current_user

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.route("/")
@login_required
def index():
    user = get_current_user()
    notifications = Notification.query.filter_by(user_id=user.id)\
        .order_by(Notification.created_at.desc()).all()
    return render_template("notifications/index.html", notifications=notifications)

@notifications_bp.route("/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_read(notif_id):
    user = get_current_user()
    notif = Notification.query.filter_by(id=notif_id, user_id=user.id).first_or_404()
    notif.is_read = True
    db.session.commit()
    
    if request.is_json:
        return jsonify({"success": True})
        
    if notif.link:
        return redirect(notif.link)
    return redirect(url_for("notifications.index"))

@notifications_bp.route("/mark-all-read", methods=["POST"])
@login_required
def mark_all_read():
    user = get_current_user()
    Notification.query.filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "info")
    return redirect(url_for("notifications.index"))

@notifications_bp.route("/unread-count")
@login_required
def unread_count():
    user = get_current_user()
    count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({"unread_count": count})
