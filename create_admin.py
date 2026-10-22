import sys
import argparse
from app import create_app
from app.models import db, User

def make_admin(name, email, password, phone, college, dept):
    app = create_app()
    with app.app_context():
        db.create_all()
        clean_email = email.strip().lower()
        existing = User.query.filter_by(email=clean_email).first()
        if existing:
            if existing.is_admin:
                print(f"Account {clean_email} is already an administrator.")
                return True
            existing.is_admin = True
            existing.role = "admin"
            existing.set_password(password)
            db.session.commit()
            print(f"Updated existing user {clean_email} to administrator privileges.")
            return True

        admin_user = User(
            full_name=name.strip(),
            email=clean_email,
            phone=phone.strip(),
            college_name=college.strip(),
            department=dept.strip(),
            year_of_study="Faculty/Admin",
            roll_number="ADMIN-001",
            role="admin",
            is_admin=True,
            is_active=True,
            coin_balance=100
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Administrator {clean_email} created successfully!")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or elevate a LappyShare administrator account.")
    parser.add_argument("--name", default="Campus Administrator", help="Admin Full Name")
    parser.add_argument("--email", default="admin@lappyshare.edu", help="Admin College Email")
    parser.add_argument("--password", default="AdminPass@2026", help="Admin Password")
    parser.add_argument("--phone", default="9876543210", help="Phone Number")
    parser.add_argument("--college", default="Government Engineering College", help="College Name")
    parser.add_argument("--dept", default="Computer Science & Engineering", help="Department")

    args = parser.parse_args()
    make_admin(args.name, args.email, args.password, args.phone, args.college, args.dept)
