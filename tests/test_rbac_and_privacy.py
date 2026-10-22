import unittest
from datetime import date, timedelta
from app import create_app
from app.models import db, User, Laptop, BorrowRequest

class RbacAndPrivacyTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Regular Student
        self.student = User(
            full_name="Regular Student",
            email="student@college.edu",
            phone="9876543210",
            college_name="Engineering College",
            department="CSE",
            year_of_study="2nd Year",
            role="borrower",
            is_admin=False
        )
        self.student.set_password("Password123")

        # Admin
        self.admin = User(
            full_name="Admin Faculty",
            email="admin@college.edu",
            phone="9123456789",
            college_name="Engineering College",
            department="Dean Office",
            year_of_study="Faculty",
            role="admin",
            is_admin=True
        )
        self.admin.set_password("AdminPass123")

        # Stranger / Intruder
        self.stranger = User(
            full_name="Stranger Student",
            email="stranger@college.edu",
            phone="9998887776",
            college_name="Engineering College",
            department="Civil",
            year_of_study="1st Year",
            role="borrower",
            is_admin=False
        )
        self.stranger.set_password("Password123")

        db.session.add_all([self.student, self.admin, self.stranger])
        db.session.commit()

        # Laptop & request between Student and someone else
        self.laptop = Laptop(
            lender_id=self.student.id,
            brand="HP",
            model="ProBook",
            processor="Intel Core i5",
            ram="8 GB",
            storage="512 GB SSD",
            operating_system="Windows 11",
            condition="Good",
            is_active=True
        )
        db.session.add(self.laptop)
        db.session.commit()

        self.req = BorrowRequest(
            reference_code="REQ-CONFIDENTIAL-01",
            laptop_id=self.laptop.id,
            borrower_id=self.student.id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=2),
            purpose="Lab Exam",
            status="pending"
        )
        db.session.add(self.req)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def get_client_for(self, user):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.full_name
            sess["user_role"] = user.role
            sess["is_admin"] = user.is_admin
        return client

    def test_unauthenticated_access_redirects_to_login(self):
        resp_borrower = self.client.get("/borrower/dashboard")
        self.assertEqual(resp_borrower.status_code, 302)
        self.assertIn("/auth/login", resp_borrower.headers["Location"])

        resp_lender = self.client.get("/lender/dashboard")
        self.assertEqual(resp_lender.status_code, 302)
        self.assertIn("/auth/login", resp_lender.headers["Location"])

        resp_admin = self.client.get("/admin/dashboard")
        self.assertEqual(resp_admin.status_code, 302)
        self.assertIn("/auth/login", resp_admin.headers["Location"])

    def test_admin_only_access_control(self):
        # Non-admin student attempts to view admin dashboard
        student_client = self.get_client_for(self.student)
        resp = student_client.get("/admin/dashboard")
        # Should redirect to login or show error
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.headers["Location"])

        # Admin user visits admin dashboard
        admin_client = self.get_client_for(self.admin)
        resp_admin = admin_client.get("/admin/dashboard")
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn(b"Platform Control Center", resp_admin.data)

    def test_unauthorized_access_to_private_request_details(self):
        # Stranger attempts to view request details they are neither borrower nor lender of
        stranger_client = self.get_client_for(self.stranger)
        resp = stranger_client.get(f"/requests/{self.req.reference_code}")
        self.assertEqual(resp.status_code, 403)

        # Admin is allowed to inspect
        admin_client = self.get_client_for(self.admin)
        resp_admin = admin_client.get(f"/requests/{self.req.reference_code}")
        self.assertEqual(resp_admin.status_code, 200)

if __name__ == "__main__":
    unittest.main()
