import unittest
from datetime import datetime, timezone, timedelta
from app import create_app
from app.models import db, User, PasswordResetToken

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_registration_and_password_hashing(self):
        response = self.client.post("/auth/register", data={
            "full_name": "Test Student",
            "email": "test.student@college.edu",
            "phone": "9876543210",
            "college_name": "Tech Institute",
            "department": "Computer Science",
            "year_of_study": "2nd Year",
            "roll_number": "CS-101",
            "password": "SecurePassword123",
            "confirm_password": "SecurePassword123",
            "role": "borrower"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        user = User.query.filter_by(email="test.student@college.edu").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.full_name, "Test Student")
        # Ensure password is not stored plaintext
        self.assertNotEqual(user.password_hash, "SecurePassword123")
        self.assertTrue(user.check_password("SecurePassword123"))
        self.assertFalse(user.check_password("WrongPassword"))

    def test_duplicate_email_rejection(self):
        # Create initial user
        user = User(
            full_name="Original User",
            email="duplicate@college.edu",
            phone="9876543210",
            college_name="Tech Institute",
            department="Computer Science",
            year_of_study="3rd Year",
            role="lender"
        )
        user.set_password("Password123")
        db.session.add(user)
        db.session.commit()

        # Try to register again with same email
        response = self.client.post("/auth/register", data={
            "full_name": "Copycat User",
            "email": "duplicate@college.edu",
            "phone": "9123456780",
            "college_name": "Tech Institute",
            "department": "IT",
            "year_of_study=" : "1st Year",
            "password": "AnotherPassword",
            "confirm_password": "AnotherPassword",
            "role": "borrower"
        }, follow_redirects=True)

        users_count = User.query.filter_by(email="duplicate@college.edu").count()
        self.assertEqual(users_count, 1)

    def test_login_and_logout(self):
        user = User(
            full_name="Login Test",
            email="login@college.edu",
            phone="9876543210",
            college_name="Tech Institute",
            department="CSE",
            year_of_study="4th Year",
            role="borrower"
        )
        user.set_password("CorrectPass")
        db.session.add(user)
        db.session.commit()

        # Failed login
        resp_fail = self.client.post("/auth/login", data={
            "email": "login@college.edu",
            "password": "WrongPassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", resp_fail.data)

        # Successful login
        resp_success = self.client.post("/auth/login", data={
            "email": "login@college.edu",
            "password": "CorrectPass"
        }, follow_redirects=True)
        self.assertEqual(resp_success.status_code, 200)

        # Logout
        resp_logout = self.client.get("/auth/logout", follow_redirects=True)
        self.assertIn(b"signed out", resp_logout.data)

    def test_password_reset_token_expiration_and_single_use(self):
        user = User(
            full_name="Reset User",
            email="reset@college.edu",
            phone="9876543210",
            college_name="Tech Institute",
            department="CSE",
            year_of_study="1st Year",
            role="borrower"
        )
        user.set_password("OldPassword123")
        db.session.add(user)
        db.session.commit()

        # Valid token
        token1 = PasswordResetToken(
            user_id=user.id,
            token="valid_token_123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used=False
        )
        # Expired token
        token2 = PasswordResetToken(
            user_id=user.id,
            token="expired_token_456",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            used=False
        )
        db.session.add_all([token1, token2])
        db.session.commit()

        self.assertTrue(token1.is_valid())
        self.assertFalse(token2.is_valid())

        # Use token1 to reset password
        resp = self.client.post(f"/auth/reset-password/{token1.token}", data={
            "password": "BrandNewPassword123",
            "confirm_password": "BrandNewPassword123"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Verify token is now marked used
        db.session.refresh(token1)
        self.assertTrue(token1.used)
        self.assertFalse(token1.is_valid())

        # Verify password changed
        db.session.refresh(user)
        self.assertTrue(user.check_password("BrandNewPassword123"))

if __name__ == "__main__":
    unittest.main()
