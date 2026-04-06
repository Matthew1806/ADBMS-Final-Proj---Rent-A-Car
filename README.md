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
- Protected dashboard, booking, and profile routes
- Owner/admin protection for uploaded ID/license files

### Customer
- Multi-step booking form with date conflict checking
- Upload valid ID and driver's license
- Select payment method (Cash, GCash, Card)
- View, edit, and cancel own bookings
- Submit reviews for completed bookings

### Admin
- Dashboard with key stats
- Manage cars (add/edit/delete)
- Manage bookings and status updates
- Manage users
- View reports

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

5. Create tables.
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

## System Developer
- Errol Matthew Cudala
