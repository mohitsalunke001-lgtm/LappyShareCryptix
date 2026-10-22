import unittest
from datetime import date, timedelta
from app import create_app
from app.models import db, User, Laptop, BorrowRequest, HandoverReturnRecord

class BorrowRequestTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create lender & borrower
        self.lender = User(
            full_name="Lender Alice",
            email="alice@college.edu",
            phone="9876543210",
            college_name="Engineering College",
            department="CSE",
            year_of_study="4th Year",
            role="lender",
            coin_balance=10
        )
        self.borrower = User(
            full_name="Borrower Bob",
            email="bob@college.edu",
            phone="9123456780",
            college_name="Engineering College",
            department="IT",
            year_of_study="2nd Year",
            role="borrower",
            coin_balance=0
        )
        self.lender.set_password("Password123")
        self.borrower.set_password("Password123")
        db.session.add_all([self.lender, self.borrower])
        db.session.commit()

        # Create laptop
        self.laptop = Laptop(
            lender_id=self.lender.id,
            brand="Dell",
            model="XPS 13",
            processor="Intel Core i7",
            ram="16 GB",
            storage="512 GB SSD",
            operating_system="Windows 11",
            condition="Excellent",
            is_active=True,
            is_available=True
        )
        db.session.add(self.laptop)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login_as(self, user):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.full_name
            sess["user_role"] = user.role
            sess["is_admin"] = user.is_admin

    def test_borrowing_request_submission(self):
        self.login_as(self.borrower)

        today = date.today()
        start = today + timedelta(days=2)
        end = today + timedelta(days=5)

        resp = self.client.post(f"/laptops/{self.laptop.id}/request", data={
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "purpose": "Machine Learning Practicals / Model Training",
            "purpose_details": "Course project lab",
            "borrower_message": "Thanks Alice"
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        req = BorrowRequest.query.filter_by(borrower_id=self.borrower.id).first()
        self.assertIsNotNone(req)
        self.assertEqual(req.status, "pending")
        self.assertEqual(req.laptop_id, self.laptop.id)
        self.assertTrue(req.reference_code.startswith("REQ-"))

    def test_prevent_borrowing_own_laptop(self):
        self.login_as(self.lender)
        today = date.today()
        resp = self.client.post(f"/laptops/{self.laptop.id}/request", data={
            "start_date": (today + timedelta(days=1)).isoformat(),
            "end_date": (today + timedelta(days=3)).isoformat(),
            "purpose": "Self test"
        }, follow_redirects=True)

        # Should flash error and prevent creation
        self.assertIn(b"cannot submit a borrowing request for your own laptop", resp.data)
        req = BorrowRequest.query.filter_by(borrower_id=self.lender.id).first()
        self.assertIsNone(req)

    def test_overlapping_reservation_prevention(self):
        today = date.today()
        # Create an already approved reservation from day 2 to day 6
        req1 = BorrowRequest(
            reference_code="REQ-EXISTING-01",
            laptop_id=self.laptop.id,
            borrower_id=self.borrower.id,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=6),
            purpose="Approved booking",
            status="approved"
        )
        db.session.add(req1)
        db.session.commit()

        # Create another student
        borrower2 = User(
            full_name="Borrower Charlie",
            email="charlie@college.edu",
            phone="9988112233",
            college_name="Engineering College",
            department="CSE",
            year_of_study="3rd Year",
            role="borrower"
        )
        borrower2.set_password("Password123")
        db.session.add(borrower2)
        db.session.commit()

        # Charlie tries to request overlapping dates (day 4 to day 8)
        self.login_as(borrower2)
        resp = self.client.post(f"/laptops/{self.laptop.id}/request", data={
            "start_date": (today + timedelta(days=4)).isoformat(),
            "end_date": (today + timedelta(days=8)).isoformat(),
            "purpose": "Conflicting Request"
        }, follow_redirects=True)

        self.assertIn(b"already has an approved reservation for the selected dates", resp.data)
        charlie_req = BorrowRequest.query.filter_by(borrower_id=borrower2.id).first()
        self.assertIsNone(charlie_req)

    def test_accept_and_handover_and_return_workflow(self):
        today = date.today()
        # 1. Create pending request
        req = BorrowRequest(
            reference_code="REQ-TEST-WORKFLOW",
            laptop_id=self.laptop.id,
            borrower_id=self.borrower.id,
            start_date=today,
            end_date=today + timedelta(days=3),
            purpose="Software Lab",
            status="pending"
        )
        db.session.add(req)
        db.session.commit()

        # 2. Lender accepts request
        self.login_as(self.lender)
        resp_accept = self.client.post(f"/lender/requests/{req.id}/accept", follow_redirects=True)
        self.assertEqual(resp_accept.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "approved")

        # 3. Handover
        resp_handover = self.client.post(f"/lender/requests/{req.id}/handover", data={
            "handover_condition": "Good",
            "handover_notes": "Charger provided"
        }, follow_redirects=True)
        self.assertEqual(resp_handover.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "borrowed")

        # 4. Return
        resp_return = self.client.post(f"/lender/requests/{req.id}/return", data={
            "return_condition": "Excellent",
            "return_notes": "All clean and intact"
        }, follow_redirects=True)
        self.assertEqual(resp_return.status_code, 200)
        db.session.refresh(req)
        self.assertEqual(req.status, "returned")

        # 5. Verify coins awarded:
        # Lender gets +5 for completed lending (started with 10 -> 15)
        db.session.refresh(self.lender)
        self.assertEqual(self.lender.coin_balance, 15)
        # Borrower gets +2 for on-time return (started with 0 -> 2)
        db.session.refresh(self.borrower)
        self.assertEqual(self.borrower.coin_balance, 2)

if __name__ == "__main__":
    unittest.main()
