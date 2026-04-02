# Rent A Car Website

Flask-based car rental system with customer booking flows, review support, and a full admin panel.

## Features

### Public
- Browse available cars
- View car details and reviews
- View about page
- Register and log in

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

4. Configure DB connection in `app.py` if your MySQL credentials differ.
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/car_rental'
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

The app includes a built-in test admin login path:
- Email: `admin@test.com`
- Password: `password123`

On first successful login with these credentials, the account is created (or promoted to admin).

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
    mysql_syntax_reference.sql
    schema_postgresql.sql
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
- This project is currently configured for MySQL in `app.py`.
- If you plan to use PostgreSQL, update the SQLAlchemy URI and schema workflow accordingly.
- For production, replace the hardcoded `app.secret_key` with a secure environment variable.

## System Developer
- Errol Matthew Cudala
