# Rent A Car Website

Flask-based car rental system with customer booking flows, review support, and a full admin panel.

## Features

### Public
- Browse available cars
- View car details and reviews
- View about page
- Register with email and password
- Login only after email verification

### Authentication & Security
- Email/password authentication using Flask-Login
- Verification link sent by email after registration
- Unverified users cannot login
- Resend verification link option on login page
- Protected booking and profile routes
- Owner/admin protection for uploaded ID/license files

### Customer
- Multi-step booking form with date conflict checking
- Upload valid ID and driver's license
- Select payment method (Cash, GCash, Card)
- View, edit, and cancel own bookings
- Submit reviews for completed bookings
- Profile redesign with settings split pages:
  - Settings overview/checklist
  - Account settings page
  - Security page
  - Photo-only upload page
- Support notifications with Gmail reply shortcut

### Admin
- Dashboard with key stats
- Manage cars (add/edit/delete)
- Manage bookings and status updates
- Manage users
- View reports
- Support inbox with reply flow, archive/restore, and delete action

## Tech Stack
- Python + Flask
- Flask-SQLAlchemy
- Flask-WTF
- Flask-Login
- MySQL (via PyMySQL)
- HTML/CSS/JavaScript (Jinja templates)

## Requirements
- Python 3.8+
- MySQL server (XAMPP/MySQL works)

## Quick Setup

1. Create and activate a virtual environment.

Windows (PowerShell):
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Install dependencies.
```bash
pip install -r requirements.txt
```

3. Create the MySQL database.
```sql
CREATE DATABASE car_rental;
```

4. Create a `.env` file with runtime configuration.
```env
SECRET_KEY=replace-with-strong-secret
DATABASE_URL=mysql+pymysql://root:@localhost:3306/car_rental

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_FROM=your_email@gmail.com
EMAIL_VERIFY_MAX_AGE_SECONDS=86400

ADMIN_EMAILS=admin1@gmail.com,admin2@gmail.com
FLASK_DEBUG=true
```

5. Create tables and baseline schema.

Recommended (ensures schema is fully aligned):
Import `database/mysql_syntax.sql` in phpMyAdmin.

Alternative (app-driven table creation):
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

6. Run the app.
```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Admin Access

Admin access is controlled by email via `ADMIN_EMAILS`.
Any authenticated user whose verified email is listed there is treated as admin.

### Create/Reset Admin Account (Optional)

If you need to create/update an admin directly in DB after a refresh, run this one-time script in project root:

```powershell
$script = @'
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import app, db
from models import User

ADMIN_EMAIL = 'admin@rentacar.com'
ADMIN_PASSWORD = 'Admin@12345'
ADMIN_NAME = 'System Admin'

with app.app_context():
  admin = User.query.filter_by(email=ADMIN_EMAIL).first()
  if admin:
    admin.name = admin.name or ADMIN_NAME
    admin.is_admin = True
    admin.email_verified = True
    admin.email_verified_at = admin.email_verified_at or datetime.utcnow()
    admin.password = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
  else:
    admin = User(
      name=ADMIN_NAME,
      email=ADMIN_EMAIL,
      contact=None,
      password=generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256'),
      is_admin=True,
      email_verified=True,
      email_verified_at=datetime.utcnow(),
    )
    db.session.add(admin)
  db.session.commit()
'@;
Set-Content -Path "_create_admin_account.py" -Value $script;
python _create_admin_account.py;
Remove-Item "_create_admin_account.py" -Force
```

Default credentials used above:
- Email: `admin@rentacar.com`
- Password: `Admin@12345`

## Booking Rules
- Overlap checks block bookings that conflict with statuses:
  - `Approved`
  - `Returned`
  - `Completed`
- Allowed upload file types:
  - `png`, `jpg`, `jpeg`, `gif`, `pdf`

## API Endpoints
- `GET /api/car/<car_id>/booked`
  - Returns booked date ranges for a car.
- `GET /api/booked-dates/<car_id>`
  - Login required. Returns individual blocked dates.
- `POST /check-booking-conflict`
  - Login required. Checks overlap for selected dates.

## Project Structure

```text
RentACar_Website/
  app.py
  models.py
  forms.py
  requirements.txt
  database/
    mysql_syntax.sql
  static/
    css/
    js/
      script.js
    images/
      cars/
      header/
      footer/
      uploads/
  templates/
    base.html
    index.html
    cars.html
    car_details.html
    car_reviews.html
    book.html
    my_bookings.html
    edit_booking.html
    review.html
    confirmation.html
    login.html
    register.html
    profile.html
    profile_settings.html
    profile_account_settings.html
    profile_security_settings.html
    profile_photo_settings.html
    profile_notifications.html
    about_contact.html
    admin_layout.html
    admin_dashboard.html
    admin_cars.html
    admin_car_form.html
    admin_bookings.html
    admin_booking_details.html
    admin_users.html
    admin_user_form.html
    admin_reports.html
```

## Notes
- Use strong environment secrets in production and disable debug mode.
- For fresh reset: clear `static/images/uploads/` and keep seed car images (`vios.png`, `city.jpg`, `montero.jpg`) unless you also plan to replace sample cars.

## System Developer
- Errol Matthew Cudala
