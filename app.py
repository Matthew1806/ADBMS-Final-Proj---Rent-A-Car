from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime, timedelta, date
from collections import Counter
from sqlalchemy import inspect, text, or_
from models import db, Car, User, Booking, Review, Payment
from forms import RegistrationForm, LoginForm, BookingForm, ReviewForm, CarForm, UserForm
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email.message import EmailMessage
import smtplib
import re

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
csrf = CSRFProtect(app)

# Database settings - MySQL with XAMPP
# Connection format: mysql+pymysql://username:password@host:port/database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://root:@localhost:3306/car_rental')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/images/uploads')
app.config['IMAGES_FOLDER'] = os.path.join(app.root_path, 'static/images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', '').strip()
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'true').lower() in {'1', 'true', 'yes', 'on'}
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '').strip()
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '').strip()
app.config['MAIL_FROM'] = os.getenv('MAIL_FROM', app.config['MAIL_USERNAME']).strip()
app.config['EMAIL_VERIFY_MAX_AGE_SECONDS'] = int(os.getenv('EMAIL_VERIFY_MAX_AGE_SECONDS', '86400'))
app.config['ADMIN_EMAILS'] = {
    email.strip().lower()
    for email in os.getenv('ADMIN_EMAILS', '').split(',')
    if email.strip()
}

# Ensure upload directory exists so file.save() does not fail.
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Set up user login system
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def get_email_serializer():
    """Serializer used to sign and validate email verification tokens."""
    return URLSafeTimedSerializer(app.secret_key)


def generate_email_verification_token(user):
    """Create a signed token for email verification links."""
    serializer = get_email_serializer()
    return serializer.dumps({'user_id': user.id, 'email': user.email}, salt='email-verify')


def verify_email_verification_token(token, max_age):
    """Validate and decode email verification token payload."""
    serializer = get_email_serializer()
    try:
        return serializer.loads(token, salt='email-verify', max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def send_verification_email(user):
    """Send an email verification link to a newly registered user."""
    mail_server = app.config['MAIL_SERVER']
    mail_port = app.config['MAIL_PORT']
    mail_from = app.config['MAIL_FROM']

    if not mail_server or not mail_from:
        raise RuntimeError('Mail settings are incomplete. Configure MAIL_SERVER and MAIL_FROM.')

    token = generate_email_verification_token(user)
    verify_url = url_for('verify_email', token=token, _external=True)

    subject = 'Verify your Rent A Car account'
    body = (
        f"Hello {user.name},\n\n"
        f"Please verify your email by opening this link:\n{verify_url}\n\n"
        f"This link expires in {app.config['EMAIL_VERIFY_MAX_AGE_SECONDS'] // 3600} hour(s).\n\n"
        'If you did not create this account, please ignore this email.'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = mail_from
    message['To'] = user.email
    message.set_content(body)

    with smtplib.SMTP(mail_server, mail_port, timeout=15) as smtp:
        if app.config['MAIL_USE_TLS']:
            smtp.starttls()
        if app.config['MAIL_USERNAME']:
            smtp.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        smtp.send_message(message)


def generate_otp():
    """Generate a random 6-digit OTP."""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def send_otp_email(user):
    """Send OTP via email to user."""
    mail_server = app.config['MAIL_SERVER']
    mail_port = app.config['MAIL_PORT']
    mail_from = app.config['MAIL_FROM']

    if not mail_server or not mail_from:
        raise RuntimeError('Mail settings are incomplete. Configure MAIL_SERVER and MAIL_FROM.')

    subject = 'Your Rent A Car Email Verification Code'
    body = (
        f"Hello {user.name},\n\n"
        f"Your verification code is: {user.otp}\n\n"
        f"This code expires in 15 minutes.\n\n"
        'If you did not request this code, please ignore this email.'
    )

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = mail_from
    message['To'] = user.email
    message.set_content(body)

    with smtplib.SMTP(mail_server, mail_port, timeout=15) as smtp:
        if app.config['MAIL_USE_TLS']:
            smtp.starttls()
        if app.config['MAIL_USERNAME']:
            smtp.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        smtp.send_message(message)


def sanitize_next_path(next_path):
    """Allow only local absolute paths for redirects to avoid open redirect issues."""
    if not next_path:
        return ''
    value = str(next_path).strip()
    if value.startswith('/') and not value.startswith('//'):
        return value
    return ''


def should_assign_admin(email):
    """Check if email is configured as admin via ADMIN_EMAILS env variable."""
    return bool(email and email.lower() in app.config['ADMIN_EMAILS'])

# Helper Functions
def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def admin_required(f):
    """Decorator to check if user is admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def parse_price(price_str):
    """Extract numeric price from string. Returns 0.0 if invalid."""
    if not price_str:
        return 0.0
    s = re.sub(r"[^0-9.]", "", price_str)
    try:
        return float(s)
    except Exception:
        return 0.0

def format_peso(amount):
    """Format amount as peso currency."""
    return f"₱{int(amount):,}" if float(amount).is_integer() else f"₱{amount:,.2f}"

def is_valid_status(status):
    """Check if booking status is valid."""
    return status in ['Pending', 'Approved', 'Rejected', 'Completed', 'Returned']

def get_car_stats(car_id):
    """Get average rating and review count for a car."""
    reviews = Review.query.filter_by(car_id=car_id).all()
    if not reviews:
        return None, 0
    avg_rating = sum(r.rating for r in reviews) / len(reviews)
    return round(avg_rating, 1), len(reviews)

def renumber_table_ids(table_class):
    """Renumber IDs in a table to remove gaps after deletion."""
    try:
        records = table_class.query.order_by(table_class.id).all()
        for new_id, record in enumerate(records, start=1):
            record.id = new_id
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error renumbering {table_class.__name__} IDs: {str(e)}")

def ensure_user_contact_column():
    """Add user.contact column for older databases that were created before this field existed."""
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        return

    column_names = {column['name'] for column in inspector.get_columns('user')}
    if 'contact' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN contact VARCHAR(20) NULL AFTER email"))
        db.session.commit()


def ensure_user_firebase_columns():
    """Add firebase-related user columns for older databases."""
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        return

    column_names = {column['name'] for column in inspector.get_columns('user')}
    if 'firebase_uid' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN firebase_uid VARCHAR(128) NULL AFTER email"))
        db.session.commit()
    if 'profile_picture' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN profile_picture VARCHAR(255) NULL AFTER firebase_uid"))
        db.session.commit()


def ensure_user_email_verification_columns():
    """Add email verification columns for older databases."""
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        return

    column_names = {column['name'] for column in inspector.get_columns('user')}
    if 'email_verified' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN email_verified TINYINT(1) NOT NULL DEFAULT 0 AFTER password"))
        db.session.commit()
    if 'email_verified_at' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN email_verified_at DATETIME NULL AFTER email_verified"))
        db.session.commit()


def ensure_user_otp_columns():
    """Add OTP columns for email verification via OTP."""
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        return

    column_names = {column['name'] for column in inspector.get_columns('user')}
    if 'otp' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN otp VARCHAR(6) NULL AFTER email_verified_at"))
        db.session.commit()
    if 'otp_expires_at' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN otp_expires_at DATETIME NULL AFTER otp"))
        db.session.commit()

def ensure_booking_pickup_area_column():
    """Add booking.pickup_area column for older databases that were created before this field existed."""
    inspector = inspect(db.engine)
    if not inspector.has_table('booking'):
        return

    column_names = {column['name'] for column in inspector.get_columns('booking')}
    if 'pickup_area' not in column_names:
        db.session.execute(text("ALTER TABLE booking ADD COLUMN pickup_area VARCHAR(100) NULL AFTER contact"))
        db.session.commit()

def split_legacy_pickup_area(notes_text):
    """Split legacy merged notes that start with 'Pick-up Area: ...' into (pickup_area, notes)."""
    raw_notes = (notes_text or '').strip()
    if not raw_notes:
        return '', ''

    lines = [line.strip() for line in raw_notes.splitlines() if line.strip()]
    if not lines:
        return '', ''

    match = re.match(r'^Pick[- ]?up Area:\s*(.+)$', lines[0], flags=re.IGNORECASE)
    if not match:
        return '', raw_notes

    pickup_area = match.group(1).strip()
    clean_notes = '\n'.join(lines[1:]).strip()
    return pickup_area, clean_notes

def get_booking_display_pickup_area_and_notes(booking):
    """Return pickup area and notes as separate display values, supporting legacy merged notes."""
    pickup_area = (getattr(booking, 'pickup_area', None) or '').strip()
    notes_text = (booking.notes or '').strip()

    if pickup_area:
        return pickup_area, notes_text

    legacy_area, clean_notes = split_legacy_pickup_area(notes_text)
    return legacy_area, clean_notes

with app.app_context():
    ensure_user_contact_column()
    ensure_user_firebase_columns()
    ensure_user_email_verification_columns()
    ensure_user_otp_columns()
    ensure_booking_pickup_area_column()

# Public Routes
@app.route('/')
def home():
    """Homepage shows general info."""
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    featured_cars = Car.query.order_by(Car.id.desc()).limit(6).all()
    for car in featured_cars:
        avg_rating, review_count = get_car_stats(car.id)
        car.average_rating = avg_rating
        car.review_count = review_count

    latest_reviews = Review.query.order_by(Review.created_at.desc()).limit(3).all()
    quick_action_cars = Car.query.order_by(Car.name.asc()).all()
    testimonial_cards = []
    for review in latest_reviews:
        user = User.query.get(review.user_id)
        car = Car.query.get(review.car_id)
        testimonial_cards.append({
            'author': user.name if user else 'Verified Customer',
            'car_name': car.name if car else 'Rental Vehicle',
            'rating': review.rating,
            'comment': review.comment,
            'date': review.created_at.strftime('%b %d, %Y') if review.created_at else ''
        })

    return render_template(
        'index.html',
        featured_cars=featured_cars,
        testimonial_cards=testimonial_cards,
        quick_action_cars=quick_action_cars
    )

@app.route('/cars')
def cars_page():
    """Display all available cars."""
    cars = Car.query.all()
     
    # Calculate average rating for each car
    for car in cars:
        reviews = Review.query.filter_by(car_id=car.id).all()
        if reviews:
            car.average_rating = round(sum(review.rating for review in reviews) / len(reviews), 1)
            car.review_count = len(reviews)
            car.reviews = reviews
        else:
            car.average_rating = None
            car.review_count = 0
            car.reviews = []
    
    return render_template('cars.html', cars=cars)

@app.route('/cars/<int:car_id>')
def car_details(car_id):
    """Show detailed information about a specific car."""
    car = Car.query.get_or_404(car_id)
    return render_template('car_details.html', car=car)

@app.route('/cars/<int:car_id>/reviews')
def car_reviews(car_id):
    """View all reviews for a specific car"""
    car = Car.query.get_or_404(car_id)
    
    # Fetch reviews for this car (most recent first)
    raw_reviews = Review.query.filter_by(car_id=car_id).order_by(Review.created_at.desc()).all()
    
    # Build a safe list of review dicts for the template
    reviews = []
    for r in raw_reviews:
        author = None
        try:
            user = User.query.get(r.user_id)
            author = user.name if user else 'Anonymous'
        except Exception:
            author = 'Anonymous'
        
        reviews.append({
            'author': author,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at.strftime('%Y-%m-%d') if getattr(r, 'created_at', None) else None
        })
    
    # Calculate rating distribution
    rating_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    for review in reviews:
        rating = int(review['rating'])
        if rating in rating_distribution:
            rating_distribution[rating] += 1
    
    # Compute average rating if not already present on car
    if not getattr(car, 'average_rating', None):
        if reviews:
            avg = round(sum(r['rating'] for r in reviews) / len(reviews), 1)
            car.average_rating = avg
            car.review_count = len(reviews)
        else:
            car.average_rating = None
            car.review_count = 0
    
    return render_template('car_reviews.html', car=car, reviews=reviews, rating_distribution=rating_distribution)

@app.route('/about', methods=['GET', 'POST'])
def about_contact():
    """About page with company information and contact form for concerns."""
    if request.method == 'POST':
        name = ' '.join((request.form.get('name') or '').strip().split())
        email = (request.form.get('email') or '').strip().lower()
        subject = ' '.join((request.form.get('subject') or '').strip().split())
        message = ' '.join((request.form.get('message') or '').strip().split())

        if not name or not email or not subject or not message:
            flash('Please complete all contact fields before submitting.', 'warning')
            return render_template('about_contact.html', form_data=request.form)

        if '@' not in email or '.' not in email.split('@')[-1]:
            flash('Please provide a valid email address.', 'warning')
            return render_template('about_contact.html', form_data=request.form)

        # Keep validation practical so valid concerns are not rejected.
        if len(name) < 2 or len(subject) < 2 or len(message) < 5:
            flash('Please provide a little more detail so we can assist you better.', 'warning')
            return render_template('about_contact.html', form_data=request.form)

        admin_emails = [addr for addr in app.config.get('ADMIN_EMAILS', set()) if addr and '@' in addr]
        # For Gmail SMTP reliability, sender should match the authenticated mailbox.
        mail_sender = app.config.get('MAIL_USERNAME') or app.config.get('MAIL_FROM')
        recipient_candidates = [app.config.get('MAIL_USERNAME'), app.config.get('MAIL_FROM')] + admin_emails
        recipients = [addr for addr in dict.fromkeys(recipient_candidates) if addr]

        if not app.config.get('MAIL_SERVER') or not recipients or not mail_sender:
            flash('Contact service is temporarily unavailable. Please try again later.', 'danger')
            return render_template('about_contact.html', form_data=request.form)

        email_message = EmailMessage()
        email_message['Subject'] = f"[Rent A Car Contact] {subject}"
        email_message['From'] = mail_sender
        email_message['To'] = ', '.join(recipients)
        email_message['Reply-To'] = email
        email_message.set_content(
            f"New customer concern from About page\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{message}\n"
        )

        try:
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=15) as smtp:
                if app.config.get('MAIL_USE_TLS'):
                    smtp.starttls()
                if app.config.get('MAIL_USERNAME'):
                    smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                smtp.send_message(email_message)

            flash('Your message has been sent to our team. We will contact you soon.', 'success')
            return redirect(url_for('about_contact'))
        except Exception:
            app.logger.exception('Failed to send contact concern from About page')
            flash('We could not send your message right now. Please try again after a few minutes.', 'danger')
            return render_template('about_contact.html', form_data=request.form)

    return render_template('about_contact.html')

# API Routes
@app.route('/api/car/<int:car_id>/booked')
def api_car_booked(car_id):
    """Return a JSON list of booked ranges for a given car."""
    car = Car.query.get_or_404(car_id)
    
    # Only show Approved, Returned, and Completed bookings as blocked
    bookings = Booking.query.filter(
        Booking.car_id == car_id,
        Booking.status.in_(['Approved', 'Returned', 'Completed'])
    ).all()
    
    ranges = []
    for b in bookings:
        start = b.pickup_date
        end = b.return_date
        
        if not start or not end:
            continue
        
        if isinstance(start, datetime):
            start_str = start.strftime('%Y-%m-%d')
        elif isinstance(start, date):
            start_str = start.strftime('%Y-%m-%d')
        else:
            start_str = str(start)
        
        if isinstance(end, datetime):
            end_str = end.strftime('%Y-%m-%d')
        elif isinstance(end, date):
            end_str = end.strftime('%Y-%m-%d')
        else:
            end_str = str(end)
        
        ranges.append({'from': start_str, 'to': end_str})
    
    return jsonify({'booked_ranges': ranges})

@app.route('/api/booked-dates/<int:car_id>')
@login_required
def get_booked_dates(car_id):
    """Get booked dates for a specific car."""
    # Only approved, returned, and completed bookings block dates
    bookings = Booking.query.filter(
        Booking.car_id == car_id,
        Booking.status.in_(['Approved', 'Returned', 'Completed'])
    ).all()
    
    booked_dates = []
    for booking in bookings:
        current_date = booking.pickup_date
        while current_date <= booking.return_date:
            booked_dates.append(current_date.isoformat())
            current_date = current_date + timedelta(days=1)
    
    return jsonify({'booked_dates': booked_dates})

@app.route('/check-booking-conflict', methods=['POST'])
@login_required
def check_booking_conflict():
    """Check if there's a booking conflict for selected car and dates."""
    try:
        data = request.get_json()
        car_id = data.get('car_id')
        pickup_date_str = data.get('pickup_date')
        return_date_str = data.get('return_date')
        
        # Convert string dates to date objects
        pickup_date = datetime.strptime(pickup_date_str, '%Y-%m-%d').date()
        return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date()
        
        print(f"Checking conflict for car {car_id}: {pickup_date} to {return_date}")
        
        # Check for overlapping bookings (only approved bookings block availability)
        conflicting_bookings = Booking.query.filter(
            Booking.car_id == car_id,
            Booking.status.in_(['Approved', 'Returned', 'Completed']),
            # Check if date ranges overlap
            Booking.pickup_date <= return_date,
            Booking.return_date >= pickup_date
        ).all()
        
        if conflicting_bookings:
            print(f"Found {len(conflicting_bookings)} conflicting bookings")
            conflicting_booking = conflicting_bookings[0]
            message = f"Car is booked from {conflicting_booking.pickup_date.strftime('%m/%d/%Y')} to {conflicting_booking.return_date.strftime('%m/%d/%Y')}. Please select different dates."
            return jsonify({
                'has_conflict': True,
                'message': message
            }), 409
        else:
            print("✓ No conflicts found")
            return jsonify({
                'has_conflict': False,
                'message': 'Car is available for selected dates'
            }), 200
            
    except Exception as e:
        print(f"Error checking booking conflict: {e}")
        return jsonify({
            'has_conflict': False,
            'message': 'Could not verify availability'
        }), 200

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login page with email verification enforcement."""
    form = LoginForm()

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    next_path = sanitize_next_path(request.args.get('next', '') or request.form.get('next', ''))

    if form.validate_on_submit():
        email = (form.email.data or '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, form.password.data):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html', form=form, next_path=next_path)

        # Check if email is verified
        if not user.email_verified:
            flash('Please verify your email first. Check your email for the verification code.', 'warning')
            return redirect(url_for('verify_otp_page', email=email))

        login_user(user)
        flash('Logged in successfully!', 'success')
        if next_path:
            return redirect(next_path)
        return redirect(url_for('dashboard'))

    return render_template('login.html', form=form, next_path=next_path)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():
        email = (form.email.data or '').strip().lower()
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered.', 'danger')
            return render_template('register.html', form=form)
        
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        otp = generate_otp()
        otp_expires_at = datetime.utcnow() + timedelta(minutes=15)

        new_user = User(
            name=form.name.data,
            email=email,
            contact=(form.contact.data or '').strip(),
            password=hashed_password,
            otp=otp,
            otp_expires_at=otp_expires_at,
            is_admin=should_assign_admin(email),
            email_verified=False,
            email_verified_at=None,
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Registration failed while creating account')
            flash('Could not create account. Please try again.', 'danger')
            return render_template('register.html', form=form)

        # Send OTP email
        try:
            send_otp_email(new_user)
            flash('Account created! Check your email for the verification code.', 'success')
            return redirect(url_for('verify_otp_page', email=email))
        except Exception as e:
            app.logger.exception('Unable to send OTP email for user %s during registration', new_user.email)
            flash('Account created but email failed to send. Please try resending the code.', 'warning')
            return redirect(url_for('verify_otp_page', email=email))

    return render_template('register.html', form=form)

@app.route('/verify-otp', methods=['GET', 'POST'])
@csrf.exempt
def verify_otp_page():
    """OTP verification page."""
    email = request.args.get('email', '').strip().lower()
    
    if not email:
        flash('Email not found. Please register again.', 'danger')
        return redirect(url_for('register'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found. Please register again.', 'danger')
        return redirect(url_for('register'))
    
    if request.method == 'POST':
        otp = request.form.get('otp', '').strip()
        
        # Check if OTP is expired
        if user.otp_expires_at and datetime.utcnow() > user.otp_expires_at:
            flash('Verification code expired. Please request a new one.', 'danger')
            return render_template('verify_otp.html', email=email)
        
        # Check if OTP is correct
        if user.otp == otp:
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
            user.otp = None
            user.otp_expires_at = None
            db.session.commit()
            flash('Email verified successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid verification code. Please try again.', 'danger')
            return render_template('verify_otp.html', email=email)
    
    return render_template('verify_otp.html', email=email)

@app.route('/resend-otp', methods=['POST'])
@csrf.exempt
def resend_otp():
    """Resend OTP to user."""
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email=email).first()
    
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('register'))
    
    # Generate new OTP
    user.otp = generate_otp()
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    try:
        send_otp_email(user)
        db.session.commit()
        flash('New verification code sent to your email.', 'success')
    except Exception:
        app.logger.exception('Unable to resend OTP email for user %s', email)
        flash('Could not send verification code. Please try again.', 'danger')
    
    return redirect(url_for('verify_otp_page', email=email))


@app.route('/verify-email/<token>')
def verify_email(token):
    """Confirm a user's email verification token."""
    payload = verify_email_verification_token(token, app.config['EMAIL_VERIFY_MAX_AGE_SECONDS'])
    if not payload:
        flash('Verification link is invalid or expired. Please request a new one.', 'danger')
        return redirect(url_for('login'))

    user = User.query.get(payload.get('user_id'))
    if not user or user.email.lower() != (payload.get('email') or '').lower():
        flash('Verification link is invalid.', 'danger')
        return redirect(url_for('login'))

    if user.email_verified:
        flash('Your email is already verified. You can log in now.', 'info')
        return redirect(url_for('login'))

    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    db.session.commit()
    flash('Email verified successfully. You can now log in.', 'success')
    return redirect(url_for('login'))


@app.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification link for unverified accounts."""
    email = (request.form.get('email') or '').strip().lower()
    if not email:
        flash('Please enter your email to resend verification.', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(email=email).first()
    if user and not user.email_verified:
        try:
            send_verification_email(user)
        except Exception:
            app.logger.exception('Failed to resend verification email for %s', email)
            flash('Unable to resend verification email right now. Please try again later.', 'danger')
            return redirect(url_for('login'))

    flash('If an unverified account exists for that email, a verification link has been sent.', 'info')
    return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with booking insights and quick actions."""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))

    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.submitted_at.desc()).all()
    status_counts = Counter((booking.status or 'Pending') for booking in bookings)
    total_spent = 0.0

    for booking in bookings:
        try:
            rental_days = (booking.return_date - booking.pickup_date).days + 1
            if rental_days < 1:
                rental_days = 1
        except Exception:
            rental_days = 1

        unit_price = parse_price(booking.car.price if booking.car else '')
        booking.rental_days = rental_days
        booking.total_cost = round(unit_price * rental_days, 2)
        booking.total_cost_display = format_peso(booking.total_cost)
        pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(booking)
        booking.pickup_area_display = pickup_area_display
        booking.notes_display = notes_display

        if (booking.payment_status or '').lower() == 'paid':
            total_spent += booking.total_cost

    today = date.today()
    upcoming_booking = Booking.query.filter_by(user_id=current_user.id).filter(
        Booking.pickup_date >= today,
        Booking.status.in_(['Pending', 'Approved'])
    ).order_by(Booking.pickup_date.asc()).first()

    if upcoming_booking:
        try:
            rental_days = (upcoming_booking.return_date - upcoming_booking.pickup_date).days + 1
            if rental_days < 1:
                rental_days = 1
        except Exception:
            rental_days = 1

        unit_price = parse_price(upcoming_booking.car.price if upcoming_booking.car else '')
        upcoming_booking.rental_days = rental_days
        upcoming_booking.total_cost = round(unit_price * rental_days, 2)
        upcoming_booking.total_cost_display = format_peso(upcoming_booking.total_cost)
        pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(upcoming_booking)
        upcoming_booking.pickup_area_display = pickup_area_display
        upcoming_booking.notes_display = notes_display

    return render_template(
        'dashboard.html',
        total_bookings=len(bookings),
        approved_bookings=status_counts.get('Approved', 0),
        pending_bookings=status_counts.get('Pending', 0),
        completed_bookings=status_counts.get('Completed', 0) + status_counts.get('Returned', 0),
        rejected_bookings=status_counts.get('Rejected', 0),
        total_spent_display=format_peso(total_spent),
        recent_bookings=bookings[:5],
        upcoming_booking=upcoming_booking
    )


@app.route('/profile')
@login_required
def profile():
    """User profile page with account and rental activity summary."""
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.submitted_at.desc()).all()
    reviews = Review.query.filter_by(user_id=current_user.id).all()

    total_bookings = len(user_bookings)
    approved_bookings = len([booking for booking in user_bookings if booking.status == 'Approved'])
    pending_bookings = len([booking for booking in user_bookings if booking.status == 'Pending'])
    completed_rentals = len([booking for booking in user_bookings if booking.status in ['Completed', 'Returned']])

    total_spent = 0.0
    for booking in user_bookings:
        try:
            rental_days = (booking.return_date - booking.pickup_date).days + 1
            if rental_days < 1:
                rental_days = 1
        except Exception:
            rental_days = 1

        unit_price = parse_price(booking.car.price if booking.car else '')
        booking.total_cost = round(unit_price * rental_days, 2)
        booking.total_cost_display = format_peso(booking.total_cost)

        if (booking.payment_status or '').lower() == 'paid':
            total_spent += booking.total_cost

    reviews_count = len(reviews)
    average_rating = round(sum(review.rating for review in reviews) / reviews_count, 1) if reviews_count else None

    completion_checks = [
        bool(current_user.name),
        bool(current_user.email),
        bool(current_user.contact),
        bool(current_user.email_verified)
    ]
    profile_completion = int((sum(1 for check in completion_checks if check) / len(completion_checks)) * 100)

    last_booking = user_bookings[0] if user_bookings else None
    if last_booking:
        pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(last_booking)
        last_booking.pickup_area_display = pickup_area_display
        last_booking.notes_display = notes_display

    member_since = current_user.created_at.strftime('%B %d, %Y') if current_user.created_at else 'Recently'
    membership_days = (date.today() - current_user.created_at.date()).days if current_user.created_at else 0

    return render_template(
        'profile.html',
        total_bookings=total_bookings,
        approved_bookings=approved_bookings,
        pending_bookings=pending_bookings,
        completed_rentals=completed_rentals,
        total_spent_display=format_peso(total_spent),
        reviews_count=reviews_count,
        average_rating=average_rating,
        profile_completion=profile_completion,
        member_since=member_since,
        membership_days=membership_days,
        last_booking=last_booking
    )

# Booking Routes
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    """Handle car booking form - requires user login."""
    form = BookingForm()
    cars = Car.query.all()
    initial_step = 1

    if request.method == 'GET':
        pickup_city_arg = (request.args.get('pickup_city') or '').strip()
        pickup_date_arg = (request.args.get('pickup_date') or '').strip()
        return_date_arg = (request.args.get('return_date') or '').strip()
        start_step_arg = (request.args.get('start_step') or '').strip()
        selected_car_arg = (request.args.get('car_id') or '').strip()
        selected_car_id = int(selected_car_arg) if selected_car_arg.isdigit() else None

        if start_step_arg.isdigit():
            initial_step = max(1, min(4, int(start_step_arg)))

        valid_pickup_areas = {'Lipa', 'Batangas City', 'Tanauan'}
        if pickup_city_arg in valid_pickup_areas:
            form.pickup_area.data = pickup_city_arg

        if pickup_date_arg and return_date_arg:
            try:
                pickup_date = datetime.strptime(pickup_date_arg, '%Y-%m-%d').date()
                return_date = datetime.strptime(return_date_arg, '%Y-%m-%d').date()

                if return_date < pickup_date:
                    cars = []
                    flash('Return date must be after the pick-up date. Please choose valid dates.', 'warning')
                else:
                    booked_car_subquery = db.session.query(Booking.car_id).filter(
                        Booking.status.in_(['Approved', 'Returned', 'Completed']),
                        Booking.pickup_date <= return_date,
                        Booking.return_date >= pickup_date
                    )

                    cars = Car.query.filter(~Car.id.in_(booked_car_subquery)).all()

                    if cars:
                        flash(f'{len(cars)} car(s) available for your selected dates.', 'success')
                    else:
                        flash('No available cars on selected days. Please choose other dates.', 'warning')

                form.pickup.data = pickup_date
                form.return_date.data = return_date
                initial_step = max(initial_step, 2)
            except ValueError:
                cars = []
                flash('Invalid date format. Please select your dates again.', 'warning')
                initial_step = max(initial_step, 2)

        if selected_car_id:
            visible_car_ids = {car.id for car in cars}
            if selected_car_id in visible_car_ids:
                form.car.data = selected_car_id
            elif pickup_date_arg and return_date_arg:
                selected_car = Car.query.get(selected_car_id)
                selected_car_name = selected_car.name if selected_car else 'Selected car'
                flash(f'{selected_car_name} is not available on selected days. Please choose another car or dates.', 'warning')
                initial_step = max(initial_step, 2)

    form.car.choices = [(car.id, f"{car.name} - {car.price}") for car in cars]
    today = date.today()

    if request.method == 'GET':
        form.name.data = current_user.name or ''
        form.email.data = current_user.email or ''
        form.contact.data = (current_user.contact or '').strip() if getattr(current_user, 'contact', None) else ''
    
    if form.validate_on_submit():
        # Check for date conflicts with approved, returned, or completed bookings
        car_id = form.car.data
        pickup_date = form.pickup.data
        return_date = form.return_date.data
        pickup_area = (form.pickup_area.data or '').strip()
        payment_method_pref = request.form.get('payment_method', '').strip()

        allowed_payment_methods = ['Cash', 'GCash', 'Card']
        if payment_method_pref and payment_method_pref not in allowed_payment_methods:
            flash('Please select a valid payment preference.', 'danger')
            return render_template('book.html', form=form, cars=cars, today=today)

        if pickup_date < today:
            flash('Pick-up date cannot be earlier than today.', 'danger')
            return render_template('book.html', form=form, cars=cars, today=today)

        if return_date < pickup_date:
            flash('Return date must be after the pick-up date.', 'danger')
            return render_template('book.html', form=form, cars=cars, today=today)
        
        # Get all approved/returned/completed bookings for this car
        conflicting_bookings = Booking.query.filter(
            Booking.car_id == car_id,
            Booking.status.in_(['Approved', 'Returned', 'Completed']),
            Booking.return_date >= pickup_date,
            Booking.pickup_date <= return_date
        ).all()
        
        if conflicting_bookings:
            flash('The selected dates conflict with an existing booking. Please choose different dates.', 'danger')
            return render_template('book.html', form=form, cars=cars, today=today)
        
        # Handle file uploads for ID and license
        id_filename = None
        license_filename = None
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        if form.id_file.data and allowed_file(form.id_file.data.filename):
            id_filename = secure_filename(form.id_file.data.filename)
            form.id_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], id_filename))
        
        if form.license_file.data and allowed_file(form.license_file.data.filename):
            license_filename = secure_filename(form.license_file.data.filename)
            form.license_file.data.save(os.path.join(app.config['UPLOAD_FOLDER'], license_filename))

        notes_value = (form.notes.data or '').strip()
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            name=form.name.data,
            email=form.email.data,
            contact=form.contact.data,
            pickup_area=pickup_area if pickup_area else None,
            car_id=form.car.data,
            pickup_date=form.pickup.data,
            return_date=form.return_date.data,
            id_file=id_filename,
            license_file=license_filename,
            notes=notes_value,
            payment_method=payment_method_pref if payment_method_pref else None,
            payment_status='Unpaid'
        )

        # Keep the user's profile contact synced for future auto-fill on booking.
        profile_contact = (current_user.contact or '').strip() if getattr(current_user, 'contact', None) else ''
        submitted_contact = (form.contact.data or '').strip()
        if submitted_contact and submitted_contact != profile_contact:
            current_user.contact = submitted_contact
        
        db.session.add(booking)
        db.session.commit()
        
        flash('Your booking has been submitted successfully! Please wait for admin approval.', 'success')
        return redirect(url_for('my_bookings'))
    
    return render_template('book.html', form=form, cars=cars, today=today, initial_step=initial_step)

@app.route('/confirmation/<int:booking_id>')
@login_required
def confirmation(booking_id):
    """Show booking confirmation page with overlap-adjusted pricing."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only view their own bookings (unless admin)
    if booking.user_id != current_user.id and not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    car = Car.query.get(booking.car_id)
    
    # Calculate price with overlap exclusion
    price_per_day = parse_price(car.price if car else '')
    
    # Calculate total days
    try:
        total_days = (booking.return_date - booking.pickup_date).days + 1
        if total_days < 1:
            total_days = 1
    except Exception:
        total_days = 1
    
    # Find overlapping bookings (Approved, Returned, Completed)
    overlapping_bookings = Booking.query.filter(
        Booking.car_id == booking.car_id,
        Booking.id != booking.id,
        Booking.status.in_(['Approved', 'Returned', 'Completed']),
        Booking.return_date >= booking.pickup_date,
        Booking.pickup_date <= booking.return_date
    ).all()
    
    # Calculate overlapping days
    overlapping_days = set()
    for other_booking in overlapping_bookings:
        current_date = max(booking.pickup_date, other_booking.pickup_date)
        end_date = min(booking.return_date, other_booking.return_date)
        
        while current_date <= end_date:
            overlapping_days.add(current_date)
            current_date += timedelta(days=1)
    
    # Billable days = total days - overlapping days
    days = total_days - len(overlapping_days)
    if days < 1:
        days = 1
    
    total = round(price_per_day * days, 2)
    total_display = format_peso(total)
    pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(booking)
    booking.pickup_area_display = pickup_area_display
    booking.notes_display = notes_display
    
    return render_template('confirmation.html', booking=booking, car=car, total_display=total_display, total_amount=total)

@app.route('/confirmation/<int:booking_id>/payment', methods=['POST'])
@login_required
def confirmation_payment(booking_id):
    """Handle payment method selection by user."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only update their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
    # Can only select payment if booking is approved
    if booking.status != 'Approved':
        flash('Payment can only be made for approved bookings.', 'warning')
        return redirect(url_for('my_bookings'))
    
    payment_method = request.form.get('payment_method')
    
    if payment_method:
        booking.payment_method = payment_method
        # For Cash payment, mark as Unpaid since payment is at pickup
        # For online payment (GCash/Card), keep as Unpaid until they complete the payment form
        if payment_method == 'Cash':
            booking.payment_status = 'Unpaid'  # Will pay upon pickup
        db.session.commit()
        flash('Payment method selected successfully!', 'success')
    
    return redirect(url_for('confirmation', booking_id=booking_id))

@app.route('/process-payment/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    """Process payment for GCash or Card."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only process their own bookings
    if booking.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Can only process payment if booking is approved
    if booking.status != 'Approved':
        return jsonify({'success': False, 'message': 'Payment can only be made for approved bookings'}), 400
    
    try:
        data = request.get_json()
        payment_method = data.get('payment_method')
        
        # Here you would integrate with actual payment gateway
        # For now, we'll simulate successful payment
        
        # Update booking with payment details
        booking.payment_method = payment_method
        booking.payment_status = 'Paid'  # Mark as paid
        
        # You could store additional payment details if needed
        # For example: transaction_id, payment_date, etc.
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/my-bookings')
@login_required
def my_bookings():
    """Display user's booking history organized by status."""
    try:
        all_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.submitted_at.desc()).all()

        for booking in all_bookings:
            try:
                rental_days = (booking.return_date - booking.pickup_date).days + 1
                if rental_days < 1:
                    rental_days = 1
            except Exception:
                rental_days = 1

            booking.rental_days = rental_days
            unit_price = parse_price(booking.car.price if booking.car else '')
            booking.total_cost = round(unit_price * rental_days, 2)
            booking.total_cost_display = format_peso(booking.total_cost)
            pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(booking)
            booking.pickup_area_display = pickup_area_display
            booking.notes_display = notes_display
        
        # Organize bookings by status
        bookings_by_status = {
            'Pending': [],
            'Approved': [],
            'Rejected': [],
            'Returned': [],
            'Completed': []
        }
        
        for booking in all_bookings:
            status = booking.status
            if status in bookings_by_status:
                bookings_by_status[status].append(booking)
            else:
                if 'Other' not in bookings_by_status:
                    bookings_by_status['Other'] = []
                bookings_by_status['Other'].append(booking)
        
        return render_template('my_bookings.html', bookings_by_status=bookings_by_status, total_bookings=len(all_bookings))
    
    except Exception as e:
        flash('An error occurred while loading your bookings.', 'danger')
        return redirect(url_for('home'))

@app.route('/bookings/<int:booking_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_booking(booking_id):
    """Allow users to edit their pending or approved bookings."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only edit their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('my_bookings'))
    
    # Only pending or approved bookings can be edited
    if booking.status not in ['Pending', 'Approved']:
        flash('You cannot edit a booking that is not pending or approved.', 'warning')
        return redirect(url_for('my_bookings'))
    
    if request.method == 'POST':
        pickup_date = request.form.get('pickup_date')
        return_date = request.form.get('return_date')
        notes = request.form.get('notes')
        
        if not pickup_date or not return_date:
            flash('Pick-up and return dates are required.', 'danger')
            return redirect(url_for('edit_booking', booking_id=booking_id))
        
        booking.pickup_date = datetime.strptime(pickup_date, '%Y-%m-%d').date()
        booking.return_date = datetime.strptime(return_date, '%Y-%m-%d').date()
        booking.notes = notes
        
        db.session.commit()
        flash('Booking updated successfully!', 'success')
        return redirect(url_for('my_bookings'))
    
    pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(booking)
    booking.pickup_area_display = pickup_area_display
    booking.notes_display = notes_display
    return render_template('edit_booking.html', booking=booking)

@app.route('/bookings/<int:booking_id>/delete', methods=['POST'])
@login_required
def delete_booking(booking_id):
    """Allow users to delete their own bookings."""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Ensure user can only delete their own bookings
        if booking.user_id != current_user.id:
            flash('Access denied. You can only delete your own bookings.', 'danger')
            return redirect(url_for('my_bookings'))
        
        # Check if booking can be deleted (only pending or approved)
        if booking.status not in ['Pending', 'Approved']:
            flash('You can only delete pending or approved bookings.', 'warning')
            return redirect(url_for('my_bookings'))
        
        db.session.delete(booking)
        db.session.commit()
        flash('Booking deleted successfully.', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the booking. Please try again.', 'danger')
        print(f"Error deleting booking: {str(e)}")
    
    return redirect(url_for('my_bookings'))

# Review Routes
@app.route('/review/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def review(booking_id):
    """Allow users to submit ratings for returned bookings."""
    booking = Booking.query.get_or_404(booking_id)
    
    # Ensure user can only review their own bookings
    if booking.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('my_bookings'))
    
    # Only returned bookings can be reviewed
    if booking.status != 'Returned':
        flash('You can only review returned bookings.', 'warning')
        return redirect(url_for('my_bookings'))
    
    # Check if review already exists
    existing_review = Review.query.filter_by(booking_id=booking_id).first()
    if existing_review:
        flash('You have already reviewed this booking.', 'info')
        return redirect(url_for('my_bookings'))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        review_obj = Review(
            user_id=current_user.id,
            car_id=booking.car_id,
            booking_id=booking_id,
            rating=form.rating.data,
            comment=form.comment.data if form.comment.data else None
        )
        
        db.session.add(review_obj)
        booking.status = 'Completed'
        db.session.commit()
        
        flash('Thank you for your review!', 'success')
        return redirect(url_for('my_bookings'))
    
    car = Car.query.get(booking.car_id)
    return render_template('review.html', form=form, booking=booking, car=car)

# Admin Routes
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    """Admin dashboard with statistics."""
    total_cars = Car.query.count()
    available_cars = Car.query.filter_by(availability='Available').count()
    total_bookings = Booking.query.count()
    total_users = User.query.filter_by(is_admin=False).count()
    active_rentals = Booking.query.filter(Booking.status.in_(['Approved', 'Returned'])).count()
    
    # Get bookings by status for dashboard display
    pending_bookings = Booking.query.filter_by(status='Pending').order_by(Booking.submitted_at.desc()).limit(5).all()
    approved_bookings = Booking.query.filter_by(status='Approved').order_by(Booking.submitted_at.desc()).limit(5).all()
    completed_bookings = Booking.query.filter_by(status='Completed').order_by(Booking.submitted_at.desc()).limit(5).all()
    rejected_bookings = Booking.query.filter_by(status='Rejected').order_by(Booking.submitted_at.desc()).limit(5).all()
    recent_bookings = Booking.query.order_by(Booking.submitted_at.desc()).limit(6).all()
    
    return render_template('admin_dashboard.html',
                         total_cars=total_cars,
                         available_cars=available_cars,
                         total_bookings=total_bookings,
                         active_rentals=active_rentals,
                         total_users=total_users,
                         pending_bookings=pending_bookings,
                         approved_bookings=approved_bookings,
                         completed_bookings=completed_bookings,
                         rejected_bookings=rejected_bookings,
                         recent_bookings=recent_bookings)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    """Admin view all bookings with optional status filter."""
    status_filter = request.args.get('status', None)
    
    if status_filter:
        bookings = Booking.query.filter_by(status=status_filter).order_by(Booking.submitted_at.desc()).all()
    else:
        bookings = Booking.query.order_by(Booking.submitted_at.desc()).all()
    
    return render_template('admin_bookings.html', bookings=bookings, status_filter=status_filter)

@app.route('/admin/bookings/<int:booking_id>')
@admin_required
def admin_booking_details(booking_id):
    """Admin view detailed booking information."""
    booking = Booking.query.get_or_404(booking_id)
    car = Car.query.get(booking.car_id)
    user = User.query.get(booking.user_id)
    pickup_area_display, notes_display = get_booking_display_pickup_area_and_notes(booking)
    booking.pickup_area_display = pickup_area_display
    booking.notes_display = notes_display
    
    return render_template('admin_booking_details.html', booking=booking, car=car, user=user)

@app.route('/admin/bookings/<int:booking_id>/status', methods=['POST'])
@admin_required
def admin_update_booking_status(booking_id):
    """Admin update booking status with validation."""
    booking = Booking.query.get_or_404(booking_id)
    new_status = request.form.get('status')
    current_status = booking.status
    
    # Check if payment method exists
    has_payment = booking.payment_method is not None and booking.payment_method != ''
    
    # Validation 0: Check for date overlaps when approving
    if new_status == 'Approved' and current_status == 'Pending':
        # Check for conflicting bookings with the same car
        conflicting_bookings = Booking.query.filter(
            Booking.car_id == booking.car_id,
            Booking.id != booking.id,
            Booking.status.in_(['Approved', 'Returned', 'Completed']),
            Booking.return_date >= booking.pickup_date,
            Booking.pickup_date <= booking.return_date
        ).all()
        
        if conflicting_bookings:
            conflict_details = []
            for cb in conflicting_bookings:
                conflict_details.append(f"Booking #{cb.id} ({cb.pickup_date.strftime('%b %d')} - {cb.return_date.strftime('%b %d')})")
            
            flash(f'Cannot approve booking due to date overlap with: {", ".join(conflict_details)}. Please reject this booking or ask the customer to change dates.', 'danger')
            return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Validation 1: Cannot change to Pending if payment method exists
    if new_status == 'Pending' and has_payment:
        flash('Cannot change status to Pending because a payment method has been selected.', 'warning')
        return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Validation 2: Status transition rules
    error = None
    
    if current_status == 'Pending':
        if new_status not in ['Pending', 'Approved', 'Rejected']:
            error = 'From Pending, you can only approve or reject.'
    
    elif current_status == 'Approved':
        if new_status not in ['Approved', 'Returned']:
            error = 'From Approved, you can only mark as Returned.'
    
    elif current_status == 'Rejected':
        error = 'Cannot change status from Rejected (final status).'
    
    elif current_status == 'Returned':
        if new_status in ['Pending', 'Approved', 'Rejected']:
            error = 'Cannot go back from Returned status.'
    
    elif current_status == 'Completed':
        error = 'Cannot change status from Completed (final status).'
    
    if error:
        flash(error, 'danger')
        return redirect(url_for('admin_booking_details', booking_id=booking_id))
    
    # Update status if valid
    if is_valid_status(new_status):
        booking.status = new_status
        db.session.commit()
        flash('Booking status updated successfully!', 'success')
    else:
        flash('Invalid status.', 'danger')
    
    return redirect(url_for('admin_booking_details', booking_id=booking_id))

@app.route('/admin/bookings/<int:booking_id>/delete', methods=['POST'])
@admin_required
def admin_delete_booking(booking_id):
    """Allow admins to delete any booking."""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Delete associated reviews if exists
        Review.query.filter_by(booking_id=booking_id).delete()
        
        db.session.delete(booking)
        db.session.commit()
        
        # Renumber booking IDs to remove gaps
        renumber_table_ids(Booking)
        flash('Booking deleted successfully.', 'success')
    
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the booking. Please try again.', 'danger')
        print(f"Error deleting booking: {str(e)}")
    
    return redirect(url_for('admin_bookings'))

# Admin Car Routes
@app.route('/admin/cars')
@admin_required
def admin_cars():
    """Admin view all cars."""
    cars = Car.query.all()
    
    # Calculate average rating for each car
    for car in cars:
        reviews = Review.query.filter_by(car_id=car.id).all()
        if reviews:
            avg_rating = sum(review.rating for review in reviews) / len(reviews)
            car.avg_rating = round(avg_rating, 1)
            car.review_count = len(reviews)
        else:
            car.avg_rating = 0
            car.review_count = 0
    
    return render_template('admin_cars.html', cars=cars)

@app.route('/admin/cars/add', methods=['GET', 'POST'])
@admin_required
def admin_add_car():
    """Admin add a new car."""
    form = CarForm()
    
    if request.method == 'POST':
        if form.validate_on_submit():
            # Validate that image is provided
            if not form.image.data:
                flash('Car image is required!', 'danger')
                return render_template('admin_car_form.html', form=form, title='Add Car')
            
            # Validate image file type
            if not allowed_file(form.image.data.filename):
                flash('Invalid file type. Only PNG, JPG, JPEG, GIF are allowed.', 'danger')
                return render_template('admin_car_form.html', form=form, title='Add Car')
            
            # Handle main image upload
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['IMAGES_FOLDER'], 'cars', image_filename))
            
            car = Car(
                name=form.name.data,
                price=form.price.data,
                specs=form.specs.data,
                image=f"images/cars/{image_filename}",
                transmission=form.transmission.data,
                fuel=form.fuel.data,
                capacity=form.capacity.data,
                engine=form.engine.data,
                mileage=form.mileage.data,
                color=form.color.data
            )
            
            db.session.add(car)
            db.session.commit()
            flash('Car added successfully!', 'success')
            return redirect(url_for('admin_cars'))
        else:
            # Show validation errors
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
    
    return render_template('admin_car_form.html', form=form, title='Add Car')

@app.route('/admin/cars/<int:car_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_car(car_id):
    """Admin edit an existing car."""
    car = Car.query.get_or_404(car_id)
    form = CarForm(obj=car)
    
    if form.validate_on_submit():
        # Handle main image upload if new
        if form.image.data and allowed_file(form.image.data.filename):
            image_filename = secure_filename(form.image.data.filename)
            form.image.data.save(os.path.join(app.config['IMAGES_FOLDER'], 'cars', image_filename))
            car.image = f"images/cars/{image_filename}"
        
        car.name = form.name.data
        car.price = form.price.data
        car.specs = form.specs.data
        car.transmission = form.transmission.data
        car.fuel = form.fuel.data
        car.capacity = form.capacity.data
        car.engine = form.engine.data
        car.mileage = form.mileage.data
        car.color = form.color.data
        
        db.session.commit()
        flash('Car updated successfully!', 'success')
        return redirect(url_for('admin_cars'))
    
    return render_template('admin_car_form.html', form=form, title='Edit Car', car=car)

@app.route('/admin/cars/<int:car_id>/delete', methods=['POST'])
@admin_required
def admin_delete_car(car_id):
    """Admin delete a car and all related data (cascade)."""
    car = Car.query.get_or_404(car_id)
    
    # Cascade delete: Remove all related reviews and bookings
    Review.query.filter_by(car_id=car_id).delete()
    Booking.query.filter_by(car_id=car_id).delete()
    
    db.session.delete(car)
    db.session.commit()
    # Renumber car IDs to remove gaps
    renumber_table_ids(Car)
    flash('Car and all related data deleted successfully!', 'success')
    return redirect(url_for('admin_cars'))

# Admin User Routes
@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin view all users."""
    users = User.query.filter_by(is_admin=False).all()
    admins = User.query.filter_by(is_admin=True).all()
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users, admins=admins, all_users=all_users)

@app.route('/admin/users/add', methods=['GET', 'POST'])
@admin_required
def admin_add_user():
    """Admin add a new user."""
    form = UserForm()
    
    if form.validate_on_submit():
        # Use password from form or default password
        password = form.password.data if form.password.data else 'defaultpassword'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user = User(
            name=form.name.data,
            email=form.email.data,
            password=hashed_password,
            is_admin=form.is_admin.data == 'True',
            email_verified=True,
            email_verified_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        flash('User added successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_user_form.html', form=form, title='Add User', is_edit=False)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    """Admin edit an existing user."""
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data == 'True'
        # Password is not updated when editing
        
        db.session.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_user_form.html', form=form, title='Edit User', is_edit=True)

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Admin delete a user."""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin_users'))
    
    try:
        # Delete all associated bookings first
        Booking.query.filter_by(user_id=user_id).delete()
        
        # Delete all associated reviews
        Review.query.filter_by(user_id=user_id).delete()
        
        # Delete all associated payments
        Payment.query.filter_by(user_id=user_id).delete()
        
        # Now delete the user
        db.session.delete(user)
        db.session.commit()
        # Renumber user IDs to remove gaps
        renumber_table_ids(User)
        flash('User and associated records deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/reports')
@admin_required
def admin_reports():
    """Admin reports page with live operational metrics and trends."""
    cars = Car.query.all()
    bookings = Booking.query.all()
    payments = Payment.query.all()
    customers = User.query.filter_by(is_admin=False).all()

    total_cars = len(cars)
    total_bookings = len(bookings)
    total_customers = len(customers)
    paid_bookings = sum(1 for booking in bookings if (booking.payment_status or '').lower() == 'paid')
    paid_rate = round((paid_bookings / total_bookings) * 100, 1) if total_bookings else 0

    total_revenue = sum(payment.amount_paid or 0 for payment in payments)

    status_order = ['Pending', 'Approved', 'Rejected', 'Completed', 'Returned']
    status_counter = Counter((booking.status or 'Pending') for booking in bookings)
    booking_status_data = [{
        'label': status,
        'count': status_counter.get(status, 0)
    } for status in status_order]

    availability_order = ['Available', 'Rented', 'Maintenance']
    availability_counter = Counter((car.availability or 'Available') for car in cars)
    fleet_status_data = [{
        'label': status,
        'count': availability_counter.get(status, 0)
    } for status in availability_order]

    # Build six-month booking and revenue trends.
    now = datetime.utcnow()
    month_keys = []
    for step in range(5, -1, -1):
        month_index = (now.year * 12 + (now.month - 1)) - step
        year = month_index // 12
        month = month_index % 12 + 1
        month_keys.append((year, month))

    month_labels = [datetime(year, month, 1).strftime('%b %Y') for year, month in month_keys]
    bookings_by_month = {(year, month): 0 for year, month in month_keys}
    revenue_by_month = {(year, month): 0 for year, month in month_keys}

    for booking in bookings:
        if booking.submitted_at:
            key = (booking.submitted_at.year, booking.submitted_at.month)
            if key in bookings_by_month:
                bookings_by_month[key] += 1

    for payment in payments:
        if payment.created_at:
            key = (payment.created_at.year, payment.created_at.month)
            if key in revenue_by_month:
                revenue_by_month[key] += payment.amount_paid or 0

    monthly_bookings = [bookings_by_month[key] for key in month_keys]
    monthly_revenue = [revenue_by_month[key] for key in month_keys]

    top_vehicle_counter = Counter()
    for booking in bookings:
        car_name = booking.car.name if booking.car else 'Unknown Vehicle'
        top_vehicle_counter[car_name] += 1
    top_vehicles = top_vehicle_counter.most_common(5)

    top_customer_counter = Counter()
    for booking in bookings:
        customer_name = booking.name or 'Unknown Customer'
        top_customer_counter[customer_name] += 1
    top_customers = top_customer_counter.most_common(5)

    payment_method_counter = Counter((booking.payment_method or 'Not Specified') for booking in bookings)
    payment_method_data = [
        {'label': label, 'count': count}
        for label, count in payment_method_counter.most_common(5)
    ]

    chart_data = {
        'month_labels': month_labels,
        'monthly_bookings': monthly_bookings,
        'monthly_revenue': monthly_revenue,
        'status_labels': [item['label'] for item in booking_status_data],
        'status_counts': [item['count'] for item in booking_status_data],
        'fleet_labels': [item['label'] for item in fleet_status_data],
        'fleet_counts': [item['count'] for item in fleet_status_data]
    }

    return render_template(
        'admin_reports.html',
        total_cars=total_cars,
        total_bookings=total_bookings,
        total_customers=total_customers,
        total_revenue=format_peso(total_revenue),
        paid_rate=paid_rate,
        booking_status_data=booking_status_data,
        fleet_status_data=fleet_status_data,
        top_vehicles=top_vehicles,
        top_customers=top_customers,
        payment_method_data=payment_method_data,
        chart_data=chart_data
    )

# File Serving Route
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """Serve uploaded files only to owner or admin users."""
    booking = Booking.query.filter(
        or_(Booking.id_file == filename, Booking.license_file == filename)
    ).first()

    if not booking:
        abort(404)

    if not current_user.is_admin and booking.user_id != current_user.id:
        abort(403)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Database Initialization
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Add sample cars if not exist
        if not Car.query.first():
            sample_cars = [
                Car(
                    name="Toyota Vios 2020",
                    price="2,000",
                    specs="Automatic, 5 Seater",
                    image="images/cars/vios.png",
                    transmission="Automatic",
                    fuel="Gas",
                    capacity="5-Seater",
                    engine="1.5L 4-Cylinder",
                    mileage="25 km/l",
                    color="White"
                ),
                Car(
                    name="Honda City 2020",
                    price="2,200",
                    specs="Manual, 5 Seater",
                    image="images/cars/city.jpg",
                    transmission="Manual",
                    fuel="Gas",
                    capacity="5-Seater",
                    engine="1.5L 4-Cylinder",
                    mileage="22 km/l",
                    color="Silver"
                ),
                Car(
                    name="Mitsubishi Montero 2020",
                    price="3,500",
                    specs="Automatic, 7 Seater",
                    image="images/cars/montero.jpg",
                    transmission="Automatic",
                    fuel="Diesel",
                    capacity="7-Seater",
                    engine="2.5L Turbo Diesel",
                    mileage="15 km/l",
                    color="Black"
                )
            ]
            db.session.add_all(sample_cars)
            db.session.commit()
        
        # Promote configured admin emails if those users already exist.
        if app.config['ADMIN_EMAILS']:
            users_to_promote = User.query.filter(User.email.in_(list(app.config['ADMIN_EMAILS']))).all()
            for admin_user in users_to_promote:
                admin_user.is_admin = True
        
        db.session.commit()

    debug_enabled = os.getenv('FLASK_DEBUG', 'false').lower() in {'1', 'true', 'yes', 'on'}
    app.run(debug=debug_enabled)

