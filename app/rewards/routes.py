from flask import Blueprint, render_template
from app.models import db, LappyCoinTransaction, User
from app.security import login_required, get_current_user

rewards_bp = Blueprint("rewards", __name__)

@rewards_bp.route("/")
@login_required
def index():
    user = get_current_user()
    
    # Ledger transactions
    transactions = LappyCoinTransaction.query.filter_by(user_id=user.id)\
        .order_by(LappyCoinTransaction.created_at.desc()).all()
        
    # Stats
    total_earned = sum(tx.amount for tx in transactions if tx.amount > 0)
    total_deducted = sum(abs(tx.amount) for tx in transactions if tx.amount < 0)
    
    return render_template(
        "rewards/index.html",
        user=user,
        transactions=transactions,
        total_earned=total_earned,
        total_deducted=total_deducted
    )
