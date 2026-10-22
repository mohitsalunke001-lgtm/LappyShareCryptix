import unittest
from app import create_app
from app.models import db, User, LappyCoinTransaction
from app.security import award_lappy_coins

class RewardsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.user = User(
            full_name="Reward Tester",
            email="reward@college.edu",
            phone="9876543210",
            college_name="College",
            department="CSE",
            year_of_study="2nd Year",
            role="borrower",
            coin_balance=10
        )
        self.user.set_password("Password123")
        db.session.add(self.user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_award_coins_success(self):
        success, msg = award_lappy_coins(
            user_id=self.user.id,
            event_type="COMMUNITY_HELP",
            amount=5,
            description="Helping peer setup Linux",
            reference_id="mentor_session_01"
        )
        self.assertTrue(success)
        db.session.refresh(self.user)
        self.assertEqual(self.user.coin_balance, 15)

        # Verify transaction logged
        tx = LappyCoinTransaction.query.filter_by(reference_id="mentor_session_01").first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, 5)

    def test_prevent_duplicate_reward_for_same_event(self):
        # First award
        success1, msg1 = award_lappy_coins(
            user_id=self.user.id,
            event_type="LIST_LAPTOP",
            amount=10,
            description="Listing laptop 99",
            reference_id="laptop:99"
        )
        self.assertTrue(success1)
        db.session.refresh(self.user)
        self.assertEqual(self.user.coin_balance, 20)

        # Duplicate attempt with identical reference_id
        success2, msg2 = award_lappy_coins(
            user_id=self.user.id,
            event_type="LIST_LAPTOP",
            amount=10,
            description="Duplicate claim for laptop 99",
            reference_id="laptop:99"
        )
        self.assertFalse(success2)
        self.assertIn("already claimed", msg2)

        # Balance remains unchanged at 20
        db.session.refresh(self.user)
        self.assertEqual(self.user.coin_balance, 20)

    def test_prevent_negative_balance(self):
        # User has 10 coins. Trying to deduct 20 should fail
        success, msg = award_lappy_coins(
            user_id=self.user.id,
            event_type="ADMIN_ADJUSTMENT",
            amount=-20,
            description="Excessive penalty",
            reference_id="penalty_01"
        )
        self.assertFalse(success)
        self.assertIn("Insufficient coin balance", msg)
        db.session.refresh(self.user)
        self.assertEqual(self.user.coin_balance, 10)

if __name__ == "__main__":
    unittest.main()
