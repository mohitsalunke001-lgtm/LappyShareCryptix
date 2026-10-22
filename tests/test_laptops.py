import unittest
from app import create_app
from app.models import db, User, Laptop

class LaptopTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create lender
        self.lender = User(
            full_name="Lender Test",
            email="lender@college.edu",
            phone="9876543210",
            college_name="College",
            department="CSE",
            year_of_study="3rd Year",
            role="lender"
        )
        self.lender.set_password("Password123")
        db.session.add(self.lender)
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

    def test_laptop_listing_and_rewards(self):
        self.login_as(self.lender)

        response = self.client.post("/lender/laptops/new", data={
            "brand": "Dell",
            "model": "Inspiron 15",
            "processor": "Intel Core i7 11th Gen",
            "ram": "16 GB",
            "storage": "512 GB SSD",
            "operating_system": "Windows 11",
            "condition": "Excellent",
            "academic_suitability": "AI / ML, Coding",
            "lending_guidelines": "Return with charger",
            "description": "Good battery life"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        laptop = Laptop.query.filter_by(model="Inspiron 15").first()
        self.assertIsNotNone(laptop)
        self.assertEqual(laptop.lender_id, self.lender.id)
        
        # Verify LappyCoins listing reward (+10 coins)
        db.session.refresh(self.lender)
        self.assertEqual(self.lender.coin_balance, 10)

    def test_laptop_ownership_protection(self):
        # Create laptop owned by lender
        laptop = Laptop(
            lender_id=self.lender.id,
            brand="Lenovo",
            model="IdeaPad",
            processor="AMD Ryzen 5",
            ram="8 GB",
            storage="512 GB SSD",
            operating_system="Windows 11",
            condition="Good",
            is_active=True
        )
        db.session.add(laptop)
        db.session.commit()

        # Other user tries to edit
        other_user = User(
            full_name="Intruder",
            email="intruder@college.edu",
            phone="9123456789",
            college_name="College",
            department="ECE",
            year_of_study="2nd Year",
            role="borrower"
        )
        other_user.set_password("Password123")
        db.session.add(other_user)
        db.session.commit()

        self.login_as(other_user)
        # Attempt to edit someone else's laptop should 404/abort
        resp = self.client.post(f"/lender/laptops/{laptop.id}/edit", data={
            "brand": "Hacked",
            "model": "Hacked",
            "processor": "Intel",
            "ram": "8 GB",
            "storage": "512 GB SSD",
            "operating_system": "Windows 11",
            "condition": "Fair"
        })
        self.assertEqual(resp.status_code, 404)

    def test_find_laptop_search_and_filter(self):
        # Create two laptops with distinct specs
        l1 = Laptop(
            lender_id=self.lender.id,
            brand="Apple",
            model="MacBook Air M2",
            processor="Apple M2",
            ram="16 GB",
            storage="512 GB SSD",
            operating_system="macOS",
            condition="Excellent",
            academic_suitability="Web Dev, iOS",
            is_active=True,
            is_available=True
        )
        l2 = Laptop(
            lender_id=self.lender.id,
            brand="Lenovo",
            model="ThinkPad T14",
            processor="Intel Core i5",
            ram="8 GB",
            storage="256 GB SSD",
            operating_system="Ubuntu Linux",
            condition="Good",
            academic_suitability="Embedded Systems",
            is_active=True,
            is_available=True
        )
        db.session.add_all([l1, l2])
        db.session.commit()

        # Search for macOS
        resp_mac = self.client.get("/laptops/find?os=macOS")
        self.assertIn(b"MacBook Air M2", resp_mac.data)
        self.assertNotIn(b"ThinkPad T14", resp_mac.data)

        # Search for keyword "Embedded"
        resp_kw = self.client.get("/laptops/find?q=Embedded")
        self.assertIn(b"ThinkPad T14", resp_kw.data)
        self.assertNotIn(b"MacBook Air M2", resp_kw.data)

if __name__ == "__main__":
    unittest.main()
