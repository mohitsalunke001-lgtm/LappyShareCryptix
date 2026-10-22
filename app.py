import os
import click
from app import create_app
from app.models import db, User, Laptop, BorrowRequest, HandoverReturnRecord, LappyCoinTransaction, Notification
from werkzeug.security import generate_password_hash

app = create_app(os.environ.get("FLASK_ENV", "development"))

@app.cli.command("init-db")
def init_db_command():
    """Clear existing data and create new database tables."""
    db.create_all()
    click.echo("Initialized the database tables successfully.")

@app.cli.command("create-admin")
@click.option("--name", prompt="Admin Full Name", default="Campus Administrator")
@click.option("--email", prompt="Admin Email", default="admin@lappyshare.edu")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--phone", prompt="Phone", default="9876543210")
@click.option("--college", prompt="College", default="Engineering & Tech Campus")
@click.option("--dept", prompt="Department", default="Computer Science")
def create_admin_command(name, email, password, phone, college, dept):
    """Create an administrator account securely."""
    existing = User.query.filter_by(email=email.strip().lower()).first()
    if existing:
        click.echo(f"Error: User with email '{email}' already exists.")
        return

    admin_user = User(
        full_name=name.strip(),
        email=email.strip().lower(),
        phone=phone.strip(),
        college_name=college.strip(),
        department=dept.strip(),
        year_of_study="Faculty / Admin",
        roll_number="ADMIN-001",
        role="admin",
        is_admin=True,
        is_active=True,
        coin_balance=100
    )
    admin_user.set_password(password)
    
    db.session.add(admin_user)
    db.session.commit()
    click.echo(f"Administrator account for '{email}' created successfully!")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="127.0.0.1", port=5000, debug=True)
