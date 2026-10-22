from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import Laptop, User, BorrowRequest

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    # Public landing page with stats and featured available laptops
    total_laptops = Laptop.query.filter_by(is_active=True).count()
    available_count = Laptop.query.filter_by(is_active=True, is_available=True, under_maintenance=False).count()
    total_students = User.query.filter_by(is_active=True).count()
    completed_loans = BorrowRequest.query.filter_by(status="returned").count()
    
    # Showcase up to 6 featured available laptops
    featured_laptops = Laptop.query.filter_by(
        is_active=True, 
        is_available=True, 
        under_maintenance=False
    ).order_by(Laptop.created_at.desc()).limit(6).all()
    
    return render_template(
        "index.html",
        total_laptops=total_laptops,
        available_count=available_count,
        total_students=total_students,
        completed_loans=completed_loans,
        featured_laptops=featured_laptops
    )

@main_bp.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html")

@main_bp.route("/about")
def about():
    return render_template("about.html")

@main_bp.route("/safety")
def safety():
    return render_template("safety.html")

@main_bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        
        if not name or not email or not message:
            flash("Please fill in all required fields.", "error")
            return render_template("contact.html")
            
        # In a real academic environment, store or send to admin email
        flash("Thank you for reaching out! Your message has been received and our campus team will contact you soon.", "success")
        return redirect(url_for("main.contact"))
        
    return render_template("contact.html")
