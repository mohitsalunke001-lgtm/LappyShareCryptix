from datetime import datetime, timezone, date, timedelta
from app import create_app
from app.models import db, User, Laptop, BorrowRequest, HandoverReturnRecord, LappyCoinTransaction, Notification

def seed():
    app = create_app()
    with app.app_context():
        db.create_all()
        
        # Check if already seeded
        if User.query.filter_by(email="arjun.sharma@college.edu").first():
            print("Database already contains seed data.")
            return

        print("Seeding academic users, laptops, and requests...")
        
        # 1. Admin
        admin = User.query.filter_by(email="admin@lappyshare.edu").first()
        if not admin:
            admin = User(
                full_name="Prof. Rajesh Kulkarni",
                email="admin@lappyshare.edu",
                phone="9876543210",
                college_name="National Institute of Technology",
                department="Computer Science & Engineering",
                year_of_study="Faculty / Dean Academics",
                roll_number="FAC-CS-04",
                role="admin",
                is_admin=True,
                is_active=True,
                coin_balance=100
            )
            admin.set_password("AdminPass@2026")
            db.session.add(admin)
            db.session.flush()

        # 2. Lenders
        lender1 = User(
            full_name="Arjun Sharma",
            email="arjun.sharma@college.edu",
            phone="9823456780",
            college_name="National Institute of Technology",
            department="Computer Science & Engineering",
            year_of_study="4th Year",
            roll_number="CS2023-018",
            role="lender",
            is_admin=False,
            is_active=True,
            coin_balance=25
        )
        lender1.set_password("Password@123")
        db.session.add(lender1)

        lender2 = User(
            full_name="Priya Nair",
            email="priya.nair@college.edu",
            phone="9845123456",
            college_name="National Institute of Technology",
            department="Electronics & Communication",
            year_of_study="3rd Year",
            roll_number="EC2024-042",
            role="lender",
            is_admin=False,
            is_active=True,
            coin_balance=15
        )
        lender2.set_password("Password@123")
        db.session.add(lender2)

        lender3 = User(
            full_name="Rohit Verma",
            email="rohit.verma@college.edu",
            phone="9711234567",
            college_name="National Institute of Technology",
            department="Information Technology",
            year_of_study="3rd Year",
            roll_number="IT2024-055",
            role="lender",
            is_admin=False,
            is_active=True,
            coin_balance=10
        )
        lender3.set_password("Password@123")
        db.session.add(lender3)

        # 3. Borrowers
        borrower1 = User(
            full_name="Rahul Kumar",
            email="rahul.kumar@college.edu",
            phone="9988776655",
            college_name="National Institute of Technology",
            department="Computer Science & Engineering",
            year_of_study="2nd Year",
            roll_number="CS2025-089",
            role="borrower",
            is_admin=False,
            is_active=True,
            coin_balance=4
        )
        borrower1.set_password("Password@123")
        db.session.add(borrower1)

        borrower2 = User(
            full_name="Ananya Singh",
            email="ananya.singh@college.edu",
            phone="9876123490",
            college_name="National Institute of Technology",
            department="Information Technology",
            year_of_study="1st Year",
            roll_number="IT2026-012",
            role="borrower",
            is_admin=False,
            is_active=True,
            coin_balance=2
        )
        borrower2.set_password("Password@123")
        db.session.add(borrower2)

        borrower3 = User(
            full_name="Karthik M",
            email="karthik.m@college.edu",
            phone="9123456781",
            college_name="National Institute of Technology",
            department="Electronics & Communication",
            year_of_study="3rd Year",
            roll_number="EC2024-061",
            role="borrower",
            is_admin=False,
            is_active=True,
            coin_balance=0
        )
        borrower3.set_password("Password@123")
        db.session.add(borrower3)

        db.session.flush()

        # 4. Laptops
        laptop1 = Laptop(
            lender_id=lender1.id,
            brand="Lenovo",
            model="Legion 5 Gaming & Compute",
            processor="AMD Ryzen 7 5800H (8 Cores, 16 Threads)",
            ram="16 GB DDR4",
            storage="1 TB NVMe SSD",
            operating_system="Ubuntu Linux 22.04 LTS (Dual-boot Windows 11)",
            condition="Excellent",
            academic_suitability="Deep Learning, PyTorch, CUDA, Computer Vision, Docker containers",
            lending_guidelines="Please handle with care. Return with 230W OEM power adapter. Do not alter root bootloader settings.",
            description="High-performance machine equipped with NVIDIA RTX graphics, perfect for students taking machine learning practicals or running simulations.",
            is_available=True,
            is_active=True,
            under_maintenance=False
        )
        db.session.add(laptop1)

        laptop2 = Laptop(
            lender_id=lender1.id,
            brand="Dell",
            model="Latitude 5420 Business Series",
            processor="Intel Core i5-1145G7 (4.4 GHz Turbo)",
            ram="16 GB DDR4",
            storage="512 GB SSD",
            operating_system="Windows 11 Pro",
            condition="Good",
            academic_suitability="MATLAB, Proteus, Keil uVision, Embedded Systems Lab, C/C++ Development",
            lending_guidelines="Please use the provided neoprene sleeve. Comes with 65W USB-C charger.",
            description="Sturdy, reliable academic workhorse with long battery life. Ideal for microcontroller programming and electronics coursework.",
            is_available=True,
            is_active=True,
            under_maintenance=False
        )
        db.session.add(laptop2)

        laptop3 = Laptop(
            lender_id=lender2.id,
            brand="Apple",
            model="MacBook Air M1",
            processor="Apple M1 8-Core Silicon",
            ram="16 GB Unified Memory",
            storage="512 GB SSD",
            operating_system="macOS Sonoma",
            condition="Excellent",
            academic_suitability="Full-Stack Web Dev, React, Node.js, Flutter, UI/UX Design (Figma)",
            lending_guidelines="Handle with clean hands. Do not consume beverages around device. Return with MagSafe cable and 30W adapter.",
            description="Extremely efficient, 18-hour battery life laptop suited for web development, design projects, and hackathons.",
            is_available=True,
            is_active=True,
            under_maintenance=False
        )
        db.session.add(laptop3)

        laptop4 = Laptop(
            lender_id=lender3.id,
            brand="HP",
            model="Pavilion 15-eg2000",
            processor="Intel Core i5 12th Gen 1235U",
            ram="8 GB DDR4",
            storage="512 GB SSD",
            operating_system="Windows 11 Home",
            condition="Good",
            academic_suitability="Java Programming, DBMS / MySQL, Data Structures, Web Development",
            lending_guidelines="Clean screen regularly with micro-fiber cloth. Always store in protective bag.",
            description="Great student laptop for programming assignments, database labs, and presentations.",
            is_available=True,
            is_active=True,
            under_maintenance=False
        )
        db.session.add(laptop4)

        db.session.flush()

        # 5. Borrow Requests & Handover Records
        today = date.today()

        # Completed loan
        req_completed = BorrowRequest(
            reference_code="REQ-2026-COMP01",
            laptop_id=laptop2.id,
            borrower_id=borrower1.id,
            start_date=today - timedelta(days=12),
            end_date=today - timedelta(days=2),
            purpose="Embedded Systems Lab & ARM Microcontroller Project",
            purpose_details="Required for 3rd semester Embedded Microcontroller practical exam and project submission.",
            borrower_message="I will take good care of the device and return it on time with charger.",
            status="returned",
            decision_at=datetime.now(timezone.utc) - timedelta(days=13)
        )
        db.session.add(req_completed)
        db.session.flush()

        record_completed = HandoverReturnRecord(
            request_id=req_completed.id,
            handover_date=datetime.now(timezone.utc) - timedelta(days=12),
            handover_condition="Good, all ports verified",
            handover_confirmed=True,
            return_date=datetime.now(timezone.utc) - timedelta(days=2),
            return_condition="Excellent, clean and verified",
            return_confirmed=True,
            damage_reported=False
        )
        db.session.add(record_completed)

        # Currently borrowed loan
        req_borrowed = BorrowRequest(
            reference_code="REQ-2026-BORD02",
            laptop_id=laptop1.id,
            borrower_id=borrower1.id,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=5),
            purpose="Deep Learning / PyTorch Semester Project",
            purpose_details="Training a Convolutional Neural Network for medical imaging coursework.",
            borrower_message="Need the GPU for model training. Thanks Arjun!",
            status="borrowed",
            decision_at=datetime.now(timezone.utc) - timedelta(days=3)
        )
        db.session.add(req_borrowed)
        db.session.flush()

        record_borrowed = HandoverReturnRecord(
            request_id=req_borrowed.id,
            handover_date=datetime.now(timezone.utc) - timedelta(days=2),
            handover_condition="Clean condition, charger included",
            handover_qr_token="qr_tok_handover_12345",
            return_qr_token="qr_tok_return_67890",
            handover_confirmed=True
        )
        db.session.add(record_borrowed)

        # Approved upcoming request
        req_approved = BorrowRequest(
            reference_code="REQ-2026-APPR03",
            laptop_id=laptop3.id,
            borrower_id=borrower2.id,
            start_date=today + timedelta(days=2),
            end_date=today + timedelta(days=6),
            purpose="React & Node.js College Hackathon",
            purpose_details="Building an accessibility web application during the 48-hour inter-college hackathon.",
            borrower_message="Looking forward to using macOS for the Flutter build.",
            status="approved",
            decision_at=datetime.now(timezone.utc) - timedelta(hours=10)
        )
        db.session.add(req_approved)
        db.session.flush()

        record_approved = HandoverReturnRecord(
            request_id=req_approved.id,
            handover_qr_token="qr_handover_tok_appr3",
            return_qr_token="qr_return_tok_appr3"
        )
        db.session.add(record_approved)

        # Pending request
        req_pending = BorrowRequest(
            reference_code="REQ-2026-PEND04",
            laptop_id=laptop4.id,
            borrower_id=borrower3.id,
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=4),
            purpose="Java OOP & MySQL Database Practical Exam",
            purpose_details="Mid-term exam preparation and practical viva demonstration.",
            borrower_message="Hi Rohit, is your HP Pavilion available for the upcoming lab exam?",
            status="pending"
        )
        db.session.add(req_pending)

        # 6. Seed LappyCoin Transactions
        # Lender 1: 10 (laptop 1 listing) + 10 (laptop 2 listing) + 5 (completed lending) = 25
        db.session.add(LappyCoinTransaction(
            user_id=lender1.id,
            amount=10,
            event_type="LIST_LAPTOP",
            reference_id=f"laptop:{laptop1.id}",
            description="Reward for listing laptop Lenovo Legion 5"
        ))
        db.session.add(LappyCoinTransaction(
            user_id=lender1.id,
            amount=10,
            event_type="LIST_LAPTOP",
            reference_id=f"laptop:{laptop2.id}",
            description="Reward for listing laptop Dell Latitude 5420"
        ))
        db.session.add(LappyCoinTransaction(
            user_id=lender1.id,
            amount=5,
            event_type="COMPLETE_LENDING",
            reference_id=f"request_lender:{req_completed.id}",
            description=f"Reward for completing lending period of {laptop2.title}"
        ))

        # Lender 2: 10 (laptop 3 listing) + 5 (community help) = 15
        db.session.add(LappyCoinTransaction(
            user_id=lender2.id,
            amount=10,
            event_type="LIST_LAPTOP",
            reference_id=f"laptop:{laptop3.id}",
            description="Reward for listing laptop Apple MacBook Air M1"
        ))
        db.session.add(LappyCoinTransaction(
            user_id=lender2.id,
            amount=5,
            event_type="COMMUNITY_HELP",
            reference_id="community_mentor_01",
            description="Community contributor reward for mentoring junior students"
        ))

        # Lender 3: 10 (laptop 4 listing) = 10
        db.session.add(LappyCoinTransaction(
            user_id=lender3.id,
            amount=10,
            event_type="LIST_LAPTOP",
            reference_id=f"laptop:{laptop4.id}",
            description="Reward for listing laptop HP Pavilion 15"
        ))

        # Borrower 1: 2 (ontime return) + 2 (ontime return previous semester) = 4
        db.session.add(LappyCoinTransaction(
            user_id=borrower1.id,
            amount=2,
            event_type="ONTIME_RETURN",
            reference_id=f"request_borrower:{req_completed.id}",
            description=f"Reward for returning {laptop2.title} on time and in good condition"
        ))
        db.session.add(LappyCoinTransaction(
            user_id=borrower1.id,
            amount=2,
            event_type="ONTIME_RETURN",
            reference_id="request_borrower:prev_sem_01",
            description="Reward for on-time return during winter practicals"
        ))

        # Borrower 2: 2 (community help) = 2
        db.session.add(LappyCoinTransaction(
            user_id=borrower2.id,
            amount=2,
            event_type="COMMUNITY_HELP",
            reference_id="hackathon_volunteer",
            description="Campus peer volunteer recognition"
        ))

        # Notifications
        db.session.add(Notification(
            user_id=borrower1.id,
            title="Laptop Handed Over",
            message=f"You have received {laptop1.title} from Arjun Sharma. Please take care of the device.",
            category="handover",
            is_read=True
        ))
        db.session.add(Notification(
            user_id=borrower2.id,
            title="Request Approved!",
            message=f"Priya Nair accepted your request ({req_approved.reference_code}) for Apple MacBook Air M1.",
            category="approval",
            is_read=False
        ))
        db.session.add(Notification(
            user_id=lender3.id,
            title="New Borrowing Request Received",
            message=f"Karthik M has requested your HP Pavilion 15 for Java OOP & MySQL practicals.",
            category="request",
            is_read=False
        ))

        db.session.commit()
        print("Database successfully seeded with realistic academic records!")

if __name__ == "__main__":
    seed()
