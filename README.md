# LappyShare — Campus Laptop Sharing Platform

> **Share. Learn. Grow.**  
> A peer-to-peer academic laptop sharing web platform designed for college students to bridge the campus computing hardware divide.

---

## 1. Project Overview

**LappyShare** is a student-to-student laptop sharing platform built for college environments. In modern engineering, computer science, and technology curricula, students often require high-performance computers for:
- **AI & Machine Learning Practicals**: Running deep learning models, PyTorch, TensorFlow, and GPU accelerated workflows.
- **Software Development & Programming Labs**: IDEs like VS Code, Android Studio, IntelliJ, Docker, and full-stack frameworks.
- **Embedded Systems Laboratories**: Microcontroller programming, Keil uVision, Proteus, Arduino IDE, and MATLAB.
- **Hackathons, Value-Added Courses, & Final Year Project Demonstrations**.

Students with spare laptops can voluntarily list them on the platform. Students in need can browse verified devices, submit academic borrowing requests, and coordinate safe in-person campus handovers.

---

## 2. Technology Stack

- **Backend**: Python 3.10+ with [Flask 3.x](https://palletsprojects.com/p/flask/)
- **Database & ORM**: SQLite with [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com/) / SQLAlchemy 2.0
- **Authentication & Security**:
  - Secure session cookies (HttpOnly, SameSite=Lax)
  - Werkzeug scrypt/pbkdf2 password hashing (no plaintext storage)
  - Full CSRF protection on state-changing requests
  - Role-based Access Control (RBAC) enforced on the backend
  - Input normalization and parameterized SQL queries
- **Frontend**:
  - Responsive HTML5, CSS3 Custom Properties (Design System), Vanilla JavaScript
  - Jinja2 server-side rendering
  - [Lucide Icons](https://lucide.dev/) for crisp UI icons
  - [Chart.js](https://www.chartjs.org/) for interactive administrator analytics
- **Advanced Features**:
  - Single-use, time-limited QR codes for secure laptop handover and return verification ([qrcode](https://pypi.org/project/qrcode/) & Pillow)
  - Idempotent LappyCoins rewards system with a double-entry transaction ledger
  - Comprehensive In-App Notification Center

---

## 3. Key Features

### Public Portal
- Responsive landing page with Hero section ("Share a Laptop. Support a Student.")
- Problem & Solution overview
- Interactive step-by-step guides for borrowing and lending
- Safety guidelines & campus meetup rules
- Available laptops preview and FAQ section

### Authentication & Account Management
- Student registration with academic profile (Department, College, Year of study, Roll number)
- Dual-role support (students can lend spare laptops and borrow other devices seamlessly)
- Login with session persistence and rate limiting guards
- Password recovery via time-limited, single-use tokens

### Borrower Dashboard & Workflows
- Personalized dashboard with real-time counters (Available laptops, Pending, Approved, Currently borrowed, Completed)
- Catalog search and filtering by CPU, RAM, storage, OS, condition, and availability dates
- Conflict-preventing reservation booking with unique reference codes (`REQ-YYYYMM-XXXXXXXX`)
- Request cancellation prior to device handover

### Lender Dashboard & Device Management
- Manage listings: add laptop, edit specifications, upload photos, set maintenance flags
- Review incoming borrowing requests with borrower details and academic purposes
- Conflict detection: backend ensures no overlapping approved reservations
- Accept or reject requests with audit logging
- Physical handover and return inspection forms with condition tracking and damage reporting

### QR-Based Handover & Return Verification
- Generates single-use cryptographic QR passes for authorized reservations
- In-person scanning or token input to confirm transfers instantly

### LappyCoins Reward System
- Merit and reputation ledger tracking community contributions
- Automatic awards:
  - **+10 Coins**: Listing an eligible laptop
  - **+5 Coins**: Completing a successful lending period
  - **+2 Coins**: Returning a borrowed laptop on time in good shape
  - **+5 Coins**: Community mentoring or verified peer help
- Strict duplicate reward prevention (idempotent transactions)
- Non-negative balance enforcement
- Borrowing is always **100% free**; LappyCoins represent academic trust, not real money or cryptocurrency

### Administrator Control Center
- Real-time statistics across students, devices, reservations, and coins
- Interactive Chart.js charts: Request status distribution and brand inventory
- Student management: profile inspection, activate/suspend accounts
- Laptop management: inventory oversight, maintenance flags
- Request auditing: inspect dates, resolve conflicts, monitor overdue loans
- LappyCoins adjustments: execute manual balance adjustments with mandatory audit justification
- Full administrative audit trail logging all actions with timestamps and IP addresses

---

## 4. Windows Setup & Installation

### Prerequisites
- Windows 10 or 11
- Python 3.10 or higher installed with `pip`
- PowerShell or Command Prompt

### Step 1: Open Project in Terminal
Open PowerShell and navigate to the project directory:
```powershell
cd C:\LappyShareCryptix
```

### Step 2: (Optional) Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 4: Initialize the Database and Seed Demo Academic Data
Populate realistic academic departments, laptops, active loans, and student accounts:
```powershell
python seed_data.py
```
*(Alternatively, initialize an empty schema using `flask init-db`)*

### Step 5: (Optional) Create a Custom Administrator
```powershell
python create_admin.py --name "Dr. Sharma" --email "admin@lappyshare.edu" --password "AdminPass@2026"
```

### Step 6: Start the Development Server
```powershell
python app.py
```

The application will start locally at:
```
http://127.0.0.1:5000
```

---

## 5. Pre-Configured Demo Accounts

For demonstration and grading, the seed database includes:

| Role | Name | Email | Password | Details |
|---|---|---|---|---|
| **Administrator** | Prof. Rajesh Kulkarni | `admin@lappyshare.edu` | `AdminPass@2026` | Full platform control, audit logs, coin adjustments |
| **Lender** | Arjun Sharma | `arjun.sharma@college.edu` | `Password@123` | CS 4th Year, owns Lenovo Legion (AI/ML) & Dell Latitude |
| **Lender** | Priya Nair | `priya.nair@college.edu` | `Password@123` | ECE 3rd Year, owns Apple MacBook Air M1 |
| **Borrower** | Rahul Kumar | `rahul.kumar@college.edu` | `Password@123` | CS 2nd Year, actively borrowing for PyTorch labs |
| **Borrower** | Ananya Singh | `ananya.singh@college.edu` | `Password@123` | IT 1st Year, approved reservation for college hackathon |

---

## 6. Running Automated Tests

Run the complete automated test suite (covering authentication, duplicate emails, password hashing, RBAC, listing ownership, conflict prevention, status transitions, rewards, and privacy):

```powershell
python -m unittest discover tests
```

---

## 7. Folder Structure

```
lappyshare/
│   app.py                   # Flask entry point and CLI commands
│   config.py                # Configurations (Dev, Testing, Production)
│   requirements.txt         # Python package dependencies
│   README.md                # Project documentation and setup guide
│   create_admin.py          # Script to create or update administrator account
│   seed_data.py             # Realistic campus data populator
│   .env.example             # Environment variable template
│   .gitignore               # Git ignore rules for db, venv, and cache
│
├───app/
│   │   __init__.py          # Application factory & context processors
│   │   models.py            # SQLAlchemy database models & relationships
│   │   security.py          # CSRF, auth decorators, and LappyCoins business logic
│   │
│   ├───auth/                # Authentication routes (login, register, reset password)
│   ├───borrower/            # Borrower dashboard and request cancellation
│   ├───lender/              # Lender dashboard, listings, and handover/return tracking
│   ├───laptops/             # Laptop catalog browsing, detail view, and request submission
│   ├───requests/            # Request details and QR verification endpoints
│   ├───rewards/             # LappyCoins overview and ledger
│   ├───notifications/       # In-app notifications center
│   ├───admin/               # Administrator control center & analytics
│   │
│   ├───static/
│   │   ├───css/
│   │   │       main.css     # Responsive CSS Design System
│   │   ├───js/
│   │   │       main.js      # Client UI interactivity
│   │   └───uploads/         # Uploaded laptop device images
│   │
│   └───templates/           # Jinja2 HTML templates
│       ├───base.html
│       ├───index.html
│       ├───how_it_works.html
│       ├───about.html
│       ├───safety.html
│       ├───contact.html
│       ├───auth/
│       ├───borrower/
│       ├───lender/
│       ├───laptops/
│       ├───requests/
│       ├───rewards/
│       ├───notifications/
│       ├───admin/
│       └───errors/
│
└───tests/                   # Automated unit & integration tests
        test_auth.py
        test_laptops.py
        test_requests.py
        test_rewards.py
        test_rbac_and_privacy.py
```

---

## 8. License & Academic Disclaimer

LappyShare is developed as an educational software project for college communities. All laptop lending is strictly voluntary and non-monetary. LappyCoins are community merit points and carry no financial or cash-equivalent value.
