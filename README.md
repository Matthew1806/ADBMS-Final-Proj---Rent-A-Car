# 🚗 Car Rental Website System

A full-featured Flask-based car rental management system with user bookings, admin dashboard, payment integration support, and review system.

**Last Updated**: December 22, 2025  
**Version**: 1.1.0  
**Status**: Production Ready

## 📋 Table of Contents
- [Features](#features)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Sample Data Setup](#sample-data-setup)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Database Schema](#database-schema)
- [User Roles](#user-roles)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)

---

## ✨ Features

### 🔓 Public Features
- **Browse Cars**: View available cars with detailed specifications
- **Car Reviews**: Read reviews and ratings from other customers
- **User Registration**: Create new accounts
- **Secure Login**: User authentication system

### 👤 Customer Features (Logged-in Users)
- **Book Cars**: Reserve cars with date selection and availability checking
- **Booking Management**: View, edit, and cancel bookings
- **Payment Selection**: Choose payment method (Cash, GCash, Card)
- **Reviews**: Rate and review completed bookings
- **Booking History**: Track all bookings organized by status
- **Document Upload**: Submit ID and driver's license for verification

### 🔧 Admin Features
- **Dashboard**: Overview of bookings, cars, and users
- **Car Management**: Add, edit, delete cars
- **Booking Management**: Approve/reject bookings, update status
- **User Management**: Add, edit, delete users
- **Reports**: Generate rental reports and analytics
- **Date Conflict Detection**: Automatic booking overlap detection

---

## 🖥️ System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **RAM**: Minimum 512MB
- **Storage**: 500MB for installation
- **Browser**: Modern browser (Chrome, Firefox, Safari, Edge)

---

## 📦 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Matthew1806/RENT_A_CAR_WEBSITE.git
cd RENT_A_CAR_WEBSITE
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```bash
FLASK_ENV=development
FLASK_APP=app.py
SECRET_KEY=your-secret-key-change-this
DATABASE_URL=sqlite:///instance/car_rental.db
```

### 5. Initialize Database
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

---

## 📊 Sample Data Setup

### Add Sample Data for Testing and Demonstration

The system includes a comprehensive sample data seeder that populates the database with realistic car rental data.

#### What's Included:
- **8 Cars**: Toyota Innova, Honda City, Mitsubishi Xpander, Hyundai Accent, Suzuki APV, Toyota Vios, Nissan Urvan, Chevrolet Spark
- **7 Users**: 6 regular customer accounts + 1 admin account
- **5 Payment Methods**: Credit Card, Debit Card, Cash, GCash, Bank Transfer
- **8 Bookings**: Various statuses (Pending, Approved, Completed, Rejected) with realistic dates
- **7 Reviews**: Customer ratings (3-5 stars) with authentic feedback
- **5 Payment Records**: Transaction history with realistic amounts

#### Test Account Credentials:
```
Regular User:
- Email: juan@example.com
- Password: password123

Admin Account:
- Email: admin@example.com
- Password: admin123
```

#### Run the Sample Data Seeder:

**Option 1: Python Script (Recommended)**
```bash
python seed_complete_data.py
```

**Option 2: Interactive Python Shell**
```bash
python
>>> from seed_complete_data import populate_db
>>> populate_db()
>>> exit()
```

#### Expected Output:
```
✅ Database populated successfully!
📊 Sample Data Summary:
  🚗 Cars: 8 added
  👥 Users: 7 added (6 customers, 1 admin)
  💳 Payment Methods: 5 added
  📅 Bookings: 8 added
  ⭐ Reviews: 7 added
  💰 Payments: 5 added
```

⚠️ **Note**: The seeder uses try-except blocks to prevent duplicate entries if run multiple times. You can safely re-run the script without causing duplicate data errors.

---

## ⚙️ Configuration

### Key Settings in `app.py`:
```python
# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/car_rental.db'

# Upload Settings
app.config['UPLOAD_FOLDER'] = 'static/images/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

# Security
app.secret_key = "supersecret"  # Change this in production!
```

---

## 🚀 Running the Application

### Option 1: Direct Python
```bash
python app.py
```

### Option 2: Using Flask CLI
```bash
flask run
```

Then open your browser and navigate to:
```
http://localhost:5000
```

---

## 📁 Project Structure

```
car_rental_website_draft-main/
├── app.py                          # Main Flask application
├── models.py                       # Database models (Car, User, Booking, etc.)
├── forms.py                        # WTForms form definitions
├── requirements.txt                # Python dependencies
├── .gitignore                      # Git ignore rules
│
├── static/                         # Static files (CSS, JS, Images)
│   ├── css/                       # Stylesheets
│   │   ├── base.css
│   │   ├── index.css
│   │   ├── cars.css
│   │   ├── car_details.css
│   │   ├── book.css
│   │   ├── my_bookings.css
│   │   ├── admin_*.css
│   │   └── responsive.css
│   ├── script.js                  # JavaScript functionality
│   └── images/
│       ├── cars/                  # Car images
│       ├── header/                # Header images
│       ├── footer/                # Footer images
│       └── uploads/               # User uploads
│
├── templates/                      # HTML templates
│   ├── base.html                  # Base template
│   ├── index.html                 # Homepage
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── cars.html                  # Car listing
│   ├── car_details.html           # Car details page
│   ├── book.html                  # Booking form
│   ├── my_bookings.html           # User bookings
│   ├── edit_booking.html          # Edit booking
│   ├── confirmation.html          # Booking confirmation
│   ├── car_reviews.html           # Car reviews
│   ├── review.html                # Submit review
│   ├── about_contact.html         # About/Contact page
│   ├── admin_dashboard.html       # Admin overview
│   ├── admin_cars.html            # Admin car management
│   ├── admin_car_form.html        # Add/Edit car form
│   ├── admin_users.html           # Admin user management
│   ├── admin_user_form.html       # Add/Edit user form
│   ├── admin_bookings.html        # Admin bookings view
│   ├── admin_booking_details.html # Admin booking details
│   └── admin_reports.html         # Admin reports
│
├── database/                       # Database files
│   ├── schema_v1.sql              # Initial schema
│   ├── schema_v2.sql              # Schema updates
│   ├── seeds.sql                  # Sample data
│   └── migrations/                # Database migration scripts
│
├── data/                           # JSON data files
│   ├── users.json
│   ├── cars.json
│   ├── bookings.json
│   ├── reviews.json
│   ├── payments.json
│   └── payment_methods.json
│
├── instance/                       # SQLite database (auto-created)
│   └── car_rental.db
│
└── uploads/                        # User uploaded documents
```

---

## 🗄️ Database Schema

### Users Table
```
- id (Primary Key)
- name (String)
- email (String, Unique)
- password (String, Hashed)
- is_admin (Boolean)
- created_at (DateTime)
```

### Cars Table
```
- id (Primary Key)
- name (String)
- price (String)
- specs (String)
- image (String)
- transmission (String)
- fuel (String)
- capacity (String)
- engine (String)
- mileage (String)
- color (String)
- availability (String)
```

### Bookings Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- car_id (Foreign Key → Cars)
- name (String)
- email (String)
- contact (String)
- pickup_date (Date)
- return_date (Date)
- id_file (String - filename)
- license_file (String - filename)
- notes (Text)
- status (String - Pending/Approved/Rejected/Returned/Completed)
- payment_method (String - Cash/GCash/Card)
- payment_status (String - Paid/Unpaid)
- submitted_at (DateTime)
```

### Reviews Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- car_id (Foreign Key → Cars)
- booking_id (Foreign Key → Bookings)
- rating (Integer 1-5)
- comment (Text)
- created_at (DateTime)
```

### PaymentMethods Table
```
- id (Primary Key)
- method_name (String)
```

### Payments Table
```
- id (Primary Key)
- user_id (Foreign Key → Users)
- booking_id (Foreign Key → Bookings)
- payment_method_id (Foreign Key → PaymentMethods)
- amount_paid (Integer)
- date_paid (String)
- created_at (DateTime)
```

---

## 👥 User Roles

### 1. **Anonymous User**
- Browse cars
- View reviews
- Access homepage and about page
- No booking capability

### 2. **Customer (Regular User)**
- Everything from Anonymous +
- Create account
- Login/Logout
- Book cars
- Edit/Cancel own bookings
- Submit reviews for completed bookings
- View booking history

### 3. **Admin**
- Everything from Customer +
- Dashboard with statistics
- Manage all cars (CRUD operations)
- Manage all bookings (approve/reject/status updates)
- Manage users
- View reports
- Override any booking decision

---

## 🔌 API Documentation

### Public API Endpoints

#### GET `/api/car/<car_id>/booked`
Returns JSON list of booked date ranges for a car.
```json
{
  "booked_ranges": [
    {"from": "2024-12-20", "to": "2024-12-22"},
    {"from": "2024-12-25", "to": "2024-12-27"}
  ]
}
```

#### GET `/api/booked-dates/<car_id>` (Requires Login)
Returns individual booked dates.
```json
{
  "booked_dates": ["2024-12-20", "2024-12-21", "2024-12-22"]
}
```

---

## 🔐 Authentication

### Test Accounts (After Running Sample Data)

**Regular Customer Account:**
- **Email**: juan@example.com
- **Password**: password123

**Admin Account:**
- **Email**: admin@example.com
- **Password**: admin123

### Default Account (Manual Creation)
If you haven't run the sample data seeder:
- **Email**: admin@test.com
- **Password**: password123

⚠️ **Important**: Change these credentials in production!

### Password Security
- Passwords are hashed using PBKDF2:SHA256
- Minimum 6 characters for regular users

---

## 📝 Important Features Explained

### 1. **Booking Status Workflow**
```
Pending → Approved → Returned → Completed
   ↓
Rejected (final)
```

### 2. **Date Conflict Detection**
- System automatically checks for booking overlaps
- Only "Approved", "Returned", and "Completed" bookings block dates
- Prevents double-booking of cars

### 3. **Payment Methods**
- **Cash**: Pay at pickup (marked as Unpaid until pickup)
- **GCash**: Online payment (ready for gateway integration)
- **Card**: Credit/Debit card (ready for gateway integration)

### 4. **File Uploads**
- Valid ID and Driver's License required for booking
- Allowed formats: PNG, JPG, JPEG, GIF, PDF
- Files stored in `static/images/uploads/`

---

## 🛠️ Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flask'"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "RuntimeError: No scoped session available"
**Solution**: Ensure app context is active
```bash
python -c "from app import app, db; app.app_context().push()"
```

### Issue: Database locked or corrupted
**Solution**: Delete and recreate database
```bash
rm instance/car_rental.db
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### Issue: Upload folder not found
**Solution**: Create upload folder
```bash
mkdir -p static/images/uploads
```

### Issue: Cannot login with admin account
**Solution**: Reset admin account in Python shell
```python
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User.query.filter_by(email='admin@test.com').first()
    if admin:
        admin.password = generate_password_hash('password123', method='pbkdf2:sha256')
        admin.is_admin = True
        db.session.commit()
```

---

## 🚀 Deployment

For production deployment:

1. **Set SECRET_KEY**: Change to a strong random string
2. **Disable Debug**: Set `DEBUG = False` in app.py
3. **Use Production WSGI**: Deploy with Gunicorn/uWSGI
4. **SSL Certificate**: Use HTTPS
5. **Environment Variables**: Use proper .env configuration
6. **Database**: Consider PostgreSQL instead of SQLite
7. **Payment Gateway**: Integrate real payment processing

---

## 📞 Support & Development

For issues or contributions:
1. Check this README first
2. Review error logs in console
3. Verify all dependencies are installed
4. Ensure database is properly initialized

---

## 📄 License

This project is open source and available under the MIT License.

---

## 👨‍💻 Authors

- Matthew1806

---

**Last Maintained**: December 18, 2025
