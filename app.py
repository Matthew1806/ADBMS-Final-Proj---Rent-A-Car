from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from flask_wtf import CSRFProtect
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from datetime import datetime, timedelta, date, timezone
from collections import Counter
from sqlalchemy import inspect, text, or_, func
from models import db, Car, User, Booking, Review, Payment, SupportConcern
from forms import RegistrationForm, LoginForm, BookingForm, ReviewForm, CarForm, UserForm
from dotenv import load_dotenv
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email.message import EmailMessage
import smtplib
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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

try:
    PH_TZ = ZoneInfo('Asia/Manila')
except ZoneInfoNotFoundError:
    # Fallback for environments without IANA tz database (e.g., some Windows installs).
    PH_TZ = timezone(timedelta(hours=8))

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


def utcnow_naive():
    """Return current UTC time as naive datetime for DB DATETIME columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_ph_datetime(value):
    """Convert a datetime value (stored as UTC-naive) into Asia/Manila time."""
    if not value:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(PH_TZ)


def format_datetime_ph(value, fmt='%b %d, %Y %I:%M %p'):
    """Format datetime consistently in PH timezone for UI display."""
    ph_value = to_ph_datetime(value)
    if not ph_value:
        return ''
    return ph_value.strftime(fmt)


@app.template_filter('datetime_ph')
def datetime_ph_filter(value, fmt='%b %d, %Y %I:%M %p'):
    """Jinja filter: {{ dt|datetime_ph }} or {{ dt|datetime_ph('%Y-%m-%d') }}."""
    return format_datetime_ph(value, fmt)


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


@app.context_processor
def inject_admin_support_counts():
    """Expose support inbox and user notification counts to templates."""
    admin_unread_support_count = 0
    user_unread_support_reply_count = 0

    if current_user.is_authenticated:
        try:
            if current_user.is_admin:
                admin_unread_support_count = SupportConcern.query.filter(
                    SupportConcern.admin_reply.is_(None),
                    SupportConcern.is_archived.is_(False),
                    SupportConcern.admin_has_seen_message.is_(False)
                ).count()
            else:
                user_email = (current_user.email or '').strip().lower()
                user_unread_support_reply_count = SupportConcern.query.filter(
                    or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
                    SupportConcern.admin_reply.isnot(None),
                    SupportConcern.is_archived.is_(False),
                    SupportConcern.is_user_archived.is_(False),
                    SupportConcern.is_user_deleted.is_(False),
                    SupportConcern.user_has_seen_reply.is_(False)
                ).count()
        except Exception:
            admin_unread_support_count = 0
            user_unread_support_reply_count = 0

    return {
        'admin_unread_support_count': admin_unread_support_count,
        'user_unread_support_reply_count': user_unread_support_reply_count
    }

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


def ensure_user_last_login_column():
    """Add user.last_login_at column for login activity display in profile security section."""
    inspector = inspect(db.engine)
    if not inspector.has_table('user'):
        return

    column_names = {column['name'] for column in inspector.get_columns('user')}
    if 'last_login_at' not in column_names:
        db.session.execute(text("ALTER TABLE `user` ADD COLUMN last_login_at DATETIME NULL AFTER created_at"))
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


def ensure_support_concerns_table():
    """Create support_concern table if missing for contact support tracking."""
    inspector = inspect(db.engine)
    if not inspector.has_table('support_concern'):
        SupportConcern.__table__.create(bind=db.engine, checkfirst=True)


def ensure_support_concern_archive_columns():
    """Add support concern archive columns for older databases."""
    inspector = inspect(db.engine)
    if not inspector.has_table('support_concern'):
        return

    column_names = {column['name'] for column in inspector.get_columns('support_concern')}
    if 'is_archived' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN is_archived TINYINT(1) NOT NULL DEFAULT 0 AFTER user_has_seen_reply"))
        db.session.commit()
    if 'archived_at' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN archived_at DATETIME NULL AFTER is_archived"))
        db.session.commit()
    if 'archived_by_admin_id' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN archived_by_admin_id INTEGER NULL AFTER archived_at"))
        db.session.commit()


def ensure_support_concern_user_columns():
    """Add support concern thread and user visibility columns for older databases."""
    inspector = inspect(db.engine)
    if not inspector.has_table('support_concern'):
        return

    column_names = {column['name'] for column in inspector.get_columns('support_concern')}
    if 'thread_root_id' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN thread_root_id INTEGER NULL AFTER id"))
        db.session.commit()
    if 'is_user_archived' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN is_user_archived TINYINT(1) NOT NULL DEFAULT 0 AFTER archived_by_admin_id"))
        db.session.commit()
    if 'user_archived_at' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN user_archived_at DATETIME NULL AFTER is_user_archived"))
        db.session.commit()
    if 'is_user_deleted' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN is_user_deleted TINYINT(1) NOT NULL DEFAULT 0 AFTER user_archived_at"))
        db.session.commit()
    if 'user_deleted_at' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN user_deleted_at DATETIME NULL AFTER is_user_deleted"))
        db.session.commit()
    if 'admin_has_seen_message' not in column_names:
        db.session.execute(text("ALTER TABLE support_concern ADD COLUMN admin_has_seen_message TINYINT(1) NOT NULL DEFAULT 0 AFTER replied_by_admin_id"))
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
    ensure_user_last_login_column()
    ensure_booking_pickup_area_column()
    ensure_support_concerns_table()
    ensure_support_concern_archive_columns()
    ensure_support_concern_user_columns()

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
        user = db.session.get(User, review.user_id)
        car = db.session.get(Car, review.car_id)
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
            user = db.session.get(User, r.user_id)
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

        concern = SupportConcern(
            user_id=current_user.id if current_user.is_authenticated else None,
            name=name,
            email=email,
            subject=subject,
            message=message,
            admin_has_seen_message=False
        )

        try:
            db.session.add(concern)
            db.session.flush()
            concern.thread_root_id = concern.id
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Failed to save contact concern')
            flash('We could not save your concern right now. Please try again.', 'danger')
            return render_template('about_contact.html', form_data=request.form)

        admin_emails = [addr for addr in app.config.get('ADMIN_EMAILS', set()) if addr and '@' in addr]
        # For Gmail SMTP reliability, sender should match the authenticated mailbox.
        mail_sender = app.config.get('MAIL_USERNAME') or app.config.get('MAIL_FROM')
        primary_recipient = (admin_emails[0] if admin_emails else app.config.get('MAIL_USERNAME') or app.config.get('MAIL_FROM') or '').strip()
        recipient_candidates = [app.config.get('MAIL_USERNAME')] + admin_emails
        hidden_recipients = [addr for addr in dict.fromkeys(recipient_candidates) if addr and addr.lower() != primary_recipient.lower()]

        if not app.config.get('MAIL_SERVER') or not primary_recipient or not mail_sender:
            flash('Your concern was submitted successfully. Our admin team will review it soon.', 'success')
            return redirect(url_for('about_contact'))

        email_message = EmailMessage()
        email_message['Subject'] = f"[Rent A Car Contact #{concern.id}] {subject}"
        email_message['From'] = mail_sender
        email_message['To'] = primary_recipient
        if hidden_recipients:
            email_message['Bcc'] = ', '.join(hidden_recipients)
        email_message['Reply-To'] = email
        email_message.set_content(
            f"New customer concern from About page\n\n"
            f"Ticket ID: {concern.id}\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{message}\n\n"
            "For synced customer notifications, reply from Admin Portal > Support instead of email reply.\n"
        )

        try:
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=15) as smtp:
                if app.config.get('MAIL_USE_TLS'):
                    smtp.starttls()
                if app.config.get('MAIL_USERNAME'):
                    smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                smtp.send_message(email_message)

            flash('Your concern has been submitted and forwarded to our admin team.', 'success')
            return redirect(url_for('about_contact'))
        except Exception:
            app.logger.exception('Failed to send contact concern from About page')
            flash('Your concern was saved, but email forwarding is delayed. Admin can still reply from the portal.', 'warning')
            return redirect(url_for('about_contact'))

    return render_template('about_contact.html')

# API Routes
@app.route('/api/car/<int:car_id>/booked')
def api_car_booked(car_id):
    """Return a JSON list of booked ranges for a given car."""
    Car.query.get_or_404(car_id)
    
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
        return redirect(url_for('admin_dashboard' if current_user.is_admin else 'home'))

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

        user.last_login_at = utcnow_naive()
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            app.logger.exception('Failed to store last login timestamp for user %s', user.id)

        login_user(user)
        flash('Logged in successfully!', 'success')
        if next_path:
            return redirect(next_path)
        return redirect(url_for('admin_dashboard' if user.is_admin else 'home'))

    return render_template('login.html', form=form, next_path=next_path)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard' if current_user.is_admin else 'home'))

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
        otp_expires_at = utcnow_naive() + timedelta(minutes=15)

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
        except Exception:
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
        if user.otp_expires_at and utcnow_naive() > user.otp_expires_at:
            flash('Verification code expired. Please request a new one.', 'danger')
            return render_template('verify_otp.html', email=email)
        
        # Check if OTP is correct
        if user.otp == otp:
            user.email_verified = True
            user.email_verified_at = utcnow_naive()
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
    user.otp_expires_at = utcnow_naive() + timedelta(minutes=15)
    
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

    user = db.session.get(User, payload.get('user_id'))
    if not user or user.email.lower() != (payload.get('email') or '').lower():
        flash('Verification link is invalid.', 'danger')
        return redirect(url_for('login'))

    if user.email_verified:
        flash('Your email is already verified. You can log in now.', 'info')
        return redirect(url_for('login'))

    user.email_verified = True
    user.email_verified_at = utcnow_naive()
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
    """Legacy user dashboard endpoint retained for compatibility."""
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('profile'))


def build_profile_checklist(user):
    """Build reusable checklist items for profile settings completion."""
    return [
        {
            'label': 'Full name is set',
            'done': bool((user.name or '').strip()),
            'action_label': 'Update Name',
            'action_href': url_for('profile_settings_account')
        },
        {
            'label': 'Contact number is set',
            'done': bool((user.contact or '').strip()),
            'action_label': 'Add Contact',
            'action_href': url_for('profile_settings_account')
        },
        {
            'label': 'Email is verified',
            'done': bool(user.email_verified),
            'action_label': 'Verify Email',
            'action_href': url_for('profile_settings_security')
        },
        {
            'label': 'Profile photo uploaded',
            'done': bool((user.profile_picture or '').strip()),
            'action_label': 'Upload Photo',
            'action_href': url_for('profile_settings_photo')
        }
    ]


def get_profile_completion_data(user):
    """Return consistent completion percentage and checklist details."""
    profile_checklist = build_profile_checklist(user)
    total_items = len(profile_checklist)
    completed_items = sum(1 for item in profile_checklist if item['done'])
    profile_completion = int((completed_items / total_items) * 100) if total_items else 0
    return profile_completion, profile_checklist


@app.route('/profile')
@login_required
def profile():
    """User profile page focused on personal summary and support updates."""

    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.submitted_at.desc()).all()
    reviews = Review.query.filter_by(user_id=current_user.id).all()

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

    profile_completion, profile_checklist = get_profile_completion_data(current_user)

    member_since = current_user.created_at.strftime('%B %d, %Y') if current_user.created_at else 'Recently'
    membership_days = (date.today() - current_user.created_at.date()).days if current_user.created_at else 0

    user_email = (current_user.email or '').strip().lower()
    active_threads = build_user_support_threads(current_user.id, user_email, include_archived=False)
    unread_support_replies = [thread for thread in active_threads if thread.get('has_unread_admin_reply')]
    latest_support_threads = active_threads[:2]

    return render_template(
        'profile.html',
        total_spent_display=format_peso(total_spent),
        reviews_count=reviews_count,
        average_rating=average_rating,
        profile_completion=profile_completion,
        member_since=member_since,
        membership_days=membership_days,
        unread_support_reply_count=len(unread_support_replies),
        latest_support_threads=latest_support_threads
    )


@app.route('/profile/settings')
@login_required
def profile_settings():
    """Settings overview page with completion checklist and navigation."""
    profile_completion, profile_checklist = get_profile_completion_data(current_user)

    return render_template(
        'profile_settings.html',
        profile_completion=profile_completion,
        profile_checklist=profile_checklist,
        last_login_at=current_user.last_login_at
    )


@app.route('/profile/settings/account')
@login_required
def profile_settings_account():
    """Dedicated page for account profile fields."""
    profile_completion, profile_checklist = get_profile_completion_data(current_user)
    return render_template(
        'profile_account_settings.html',
        profile_completion=profile_completion,
        profile_checklist=profile_checklist
    )


@app.route('/profile/settings/security')
@login_required
def profile_settings_security():
    """Dedicated page for security tools and password update."""
    profile_completion, profile_checklist = get_profile_completion_data(current_user)
    return render_template(
        'profile_security_settings.html',
        profile_completion=profile_completion,
        profile_checklist=profile_checklist,
        last_login_at=current_user.last_login_at
    )


@app.route('/profile/settings/photo')
@login_required
def profile_settings_photo():
    """Dedicated page for profile photo upload only."""
    profile_completion, profile_checklist = get_profile_completion_data(current_user)
    return render_template(
        'profile_photo_settings.html',
        profile_completion=profile_completion,
        profile_checklist=profile_checklist
    )


@app.route('/profile/update', methods=['POST'])
@login_required
def update_profile_account():
    """Update profile identity fields and optional profile photo."""
    name = ' '.join((request.form.get('name') or '').strip().split())
    contact = (request.form.get('contact') or '').strip()
    profile_file = request.files.get('profile_picture')

    if len(name) < 2:
        flash('Please enter a valid full name (at least 2 characters).', 'warning')
        return redirect(url_for('profile_settings_account'))

    if contact and not re.fullmatch(r'^(\+63|0)\d{10}$', contact):
        flash('Contact number must use PH format like 09XXXXXXXXX or +63XXXXXXXXXX.', 'warning')
        return redirect(url_for('profile_settings_account'))

    if profile_file and profile_file.filename:
        extension = profile_file.filename.rsplit('.', 1)[-1].lower() if '.' in profile_file.filename else ''
        allowed_image_ext = {'jpg', 'jpeg', 'png', 'webp'}
        if extension not in allowed_image_ext:
            flash('Profile photo must be JPG, JPEG, PNG, or WEBP format.', 'warning')
            return redirect(url_for('profile_settings_account'))

        profile_file.stream.seek(0, os.SEEK_END)
        file_size = profile_file.stream.tell()
        profile_file.stream.seek(0)
        if file_size > 2 * 1024 * 1024:
            flash('Profile photo must be 2MB or smaller.', 'warning')
            return redirect(url_for('profile_settings_account'))

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename = secure_filename(f"profile_{current_user.id}_{int(utcnow_naive().timestamp())}.{extension}")
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        profile_file.save(save_path)
        current_user.profile_picture = f"/static/images/uploads/{filename}"

    current_user.name = name
    current_user.contact = contact or None

    try:
        db.session.commit()
        flash('Profile details updated successfully.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to update profile for user %s', current_user.id)
        flash('Could not update profile right now. Please try again.', 'danger')

    return redirect(url_for('profile_settings_account'))


@app.route('/profile/update-photo', methods=['POST'])
@login_required
def update_profile_photo():
    """Update only the current user's profile photo."""
    profile_file = request.files.get('profile_picture')

    if not profile_file or not profile_file.filename:
        flash('Please choose a photo before uploading.', 'warning')
        return redirect(url_for('profile_settings_photo'))

    extension = profile_file.filename.rsplit('.', 1)[-1].lower() if '.' in profile_file.filename else ''
    allowed_image_ext = {'jpg', 'jpeg', 'png', 'webp'}
    if extension not in allowed_image_ext:
        flash('Profile photo must be JPG, JPEG, PNG, or WEBP format.', 'warning')
        return redirect(url_for('profile_settings_photo'))

    profile_file.stream.seek(0, os.SEEK_END)
    file_size = profile_file.stream.tell()
    profile_file.stream.seek(0)
    if file_size > 2 * 1024 * 1024:
        flash('Profile photo must be 2MB or smaller.', 'warning')
        return redirect(url_for('profile_settings_photo'))

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    filename = secure_filename(f"profile_{current_user.id}_{int(utcnow_naive().timestamp())}.{extension}")
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    profile_file.save(save_path)
    current_user.profile_picture = f"/static/images/uploads/{filename}"

    try:
        db.session.commit()
        flash('Profile photo updated successfully.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to update profile photo for user %s', current_user.id)
        flash('Could not update profile photo right now. Please try again.', 'danger')

    return redirect(url_for('profile_settings_photo'))


@app.route('/profile/change-password', methods=['POST'])
@login_required
def change_profile_password():
    """Change the current user's account password from profile security section."""
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not check_password_hash(current_user.password, current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('profile_settings_security'))

    if len(new_password) < 8:
        flash('New password must be at least 8 characters long.', 'warning')
        return redirect(url_for('profile_settings_security'))

    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'warning')
        return redirect(url_for('profile_settings_security'))

    if check_password_hash(current_user.password, new_password):
        flash('Please use a different password from your current one.', 'warning')
        return redirect(url_for('profile_settings_security'))

    current_user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
    try:
        db.session.commit()
        flash('Password changed successfully.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to change password for user %s', current_user.id)
        flash('Could not change password right now. Please try again.', 'danger')

    return redirect(url_for('profile_settings_security'))


@app.route('/profile/support-replies/<int:concern_id>/reply', methods=['POST'])
@login_required
def profile_reply_support(concern_id):
    """Allow user to submit support follow-up directly in app (no external Gmail needed)."""
    concern = SupportConcern.query.get_or_404(concern_id)

    user_email = (current_user.email or '').strip().lower()
    concern_email = (concern.email or '').strip().lower()
    if concern.user_id != current_user.id and concern_email != user_email:
        flash('You are not allowed to reply to this support concern.', 'danger')
        return redirect(url_for('profile_notifications'))

    follow_up = ' '.join((request.form.get('follow_up_reply') or '').strip().split())
    if len(follow_up) < 5:
        flash('Please enter at least 5 characters for your reply.', 'warning')
        return redirect(url_for('profile_notifications', status='all'))

    if concern.is_user_archived or concern.is_user_deleted:
        flash('This concern is not available for reply.', 'warning')
        return redirect(url_for('profile_notifications', status='all'))

    thread_root_id = resolve_thread_root_for_user(concern, current_user.id, user_email)
    root_concern = db.session.get(SupportConcern, thread_root_id)
    thread_subject = normalize_support_subject((root_concern.subject if root_concern else concern.subject) or concern.subject)

    new_concern = SupportConcern(
        user_id=current_user.id,
        name=(current_user.name or concern.name or 'Customer').strip(),
        email=(current_user.email or concern.email or '').strip(),
        subject=thread_subject[:160],
        message=follow_up,
        thread_root_id=thread_root_id,
        admin_reply=None,
        admin_has_seen_message=False,
        user_has_seen_reply=True,
        is_archived=False,
        is_user_archived=False,
        is_user_deleted=False,
        created_at=utcnow_naive()
    )

    try:
        # If the thread was archived by admin, reactivate the whole thread so follow-up
        # continues in the same original ticket instead of creating a separate one.
        thread_items = SupportConcern.query.filter(
            or_(SupportConcern.id == thread_root_id, SupportConcern.thread_root_id == thread_root_id)
        ).all()
        for item in thread_items:
            item.is_archived = False
            item.archived_at = None
            item.archived_by_admin_id = None

        concern.user_has_seen_reply = True
        db.session.add(new_concern)
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to save in-app support follow-up for concern %s', concern_id)
        flash('Could not send your reply right now. Please try again.', 'danger')
        return redirect(url_for('profile_notifications', status='all'))

    # Notify admin inbox email list so follow-ups are not missed outside the web UI.
    mail_server = app.config.get('MAIL_SERVER')
    mail_sender = (app.config.get('MAIL_FROM') or app.config.get('MAIL_USERNAME') or '').strip()
    admin_emails = [addr for addr in app.config.get('ADMIN_EMAILS', set()) if addr and '@' in addr]
    fallback_admin = (app.config.get('MAIL_USERNAME') or app.config.get('MAIL_FROM') or '').strip()
    if fallback_admin and '@' in fallback_admin and fallback_admin.lower() not in {addr.lower() for addr in admin_emails}:
        admin_emails.append(fallback_admin)

    if mail_server and mail_sender and admin_emails:
        email_message = EmailMessage()
        email_message['Subject'] = f"[Rent A Car Follow-up #{thread_root_id}] {thread_subject}"
        email_message['From'] = mail_sender
        email_message['To'] = admin_emails[0]
        if len(admin_emails) > 1:
            email_message['Bcc'] = ', '.join(admin_emails[1:])
        email_message.set_content(
            f"Customer {new_concern.name} sent a follow-up reply.\n\n"
            f"Thread ID: #{thread_root_id}\n"
            f"Subject: {thread_subject}\n"
            f"Email: {new_concern.email}\n"
            f"Sent: {new_concern.created_at.strftime('%b %d, %Y %I:%M %p UTC')}\n\n"
            f"Message:\n{follow_up}\n"
        )

        try:
            mail_port = int(app.config.get('MAIL_PORT', 587))
            if mail_port == 465:
                with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], mail_port, timeout=15) as smtp:
                    if app.config.get('MAIL_USERNAME'):
                        smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                    smtp.send_message(email_message)
            else:
                with smtplib.SMTP(app.config['MAIL_SERVER'], mail_port, timeout=15) as smtp:
                    if app.config.get('MAIL_USE_TLS'):
                        smtp.starttls()
                    if app.config.get('MAIL_USERNAME'):
                        smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                    smtp.send_message(email_message)
            flash('Reply sent successfully. Admin was notified.', 'success')
        except Exception:
            app.logger.exception('Failed to send follow-up notification email to admins')
            flash('Reply saved in support inbox, but email notification to admin failed.', 'warning')
    else:
        flash('Your reply was sent to support. Admin will respond here in notifications.', 'success')

    return redirect(url_for('profile_notifications', status='all'))


def normalize_support_subject(subject):
    """Normalize support subject so follow-ups stay under one thread title."""
    value = (subject or '').strip()
    if not value:
        return 'Support Concern'
    normalized = re.sub(r'^\s*follow[- ]?up\s*:\s*', '', value, flags=re.IGNORECASE).strip()
    return normalized or value


def resolve_thread_root_for_user(concern, user_id, user_email):
    """Resolve thread root id even for legacy rows that were created before thread_root_id existed."""
    if concern.thread_root_id:
        return min(concern.id, concern.thread_root_id)

    normalized_subject = normalize_support_subject(concern.subject)
    owner_concerns = SupportConcern.query.filter(
        or_(SupportConcern.user_id == user_id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.is_user_deleted.is_(False)
    ).order_by(SupportConcern.created_at.asc(), SupportConcern.id.asc()).all()

    matching_items = [item for item in owner_concerns if normalize_support_subject(item.subject) == normalized_subject]
    if matching_items:
        canonical_root_id = min(
            [item.id for item in matching_items] +
            [item.thread_root_id for item in matching_items if item.thread_root_id]
        )
        has_updates = False
        for item in matching_items:
            if item.thread_root_id != canonical_root_id:
                item.thread_root_id = canonical_root_id
                has_updates = True
        if has_updates:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return canonical_root_id

    return concern.id


def build_user_support_threads(user_id, user_email, include_archived=False):
    """Return grouped support conversation threads for a user."""
    query = SupportConcern.query.filter(
        or_(SupportConcern.user_id == user_id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.is_user_deleted.is_(False)
    )

    if include_archived:
        query = query.filter(SupportConcern.is_user_archived.is_(True))
    else:
        query = query.filter(SupportConcern.is_user_archived.is_(False))

    concerns = query.order_by(SupportConcern.created_at.asc(), SupportConcern.id.asc()).all()
    concern_ids = {item.id for item in concerns}
    subject_roots = {}
    has_thread_updates = False

    grouped_threads = {}
    for concern in concerns:
        normalized_subject = normalize_support_subject(concern.subject)
        derived_root = min(concern.id, concern.thread_root_id or concern.id)
        if concern.thread_root_id and concern.thread_root_id in concern_ids:
            root_id = min(concern.id, concern.thread_root_id)
        else:
            root_id = subject_roots.get(normalized_subject, derived_root)
            if concern.thread_root_id != root_id:
                concern.thread_root_id = root_id
                has_thread_updates = True

        subject_roots.setdefault(normalized_subject, root_id)
        grouped_threads.setdefault(root_id, []).append(concern)

    if has_thread_updates:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    threads = []
    for root_id, messages in grouped_threads.items():
        ordered_messages = sorted(messages, key=lambda item: (item.created_at or datetime.min, item.id))
        root_concern = next((item for item in ordered_messages if item.id == root_id), ordered_messages[0])
        latest_message = ordered_messages[-1]

        has_any_admin_reply = any(bool((item.admin_reply or '').strip()) for item in ordered_messages)
        has_unread_admin_reply = any(
            bool((item.admin_reply or '').strip()) and not item.user_has_seen_reply
            for item in ordered_messages
        )
        latest_has_admin_reply = bool((latest_message.admin_reply or '').strip())
        last_activity_at = latest_message.admin_replied_at if latest_has_admin_reply else latest_message.created_at
        if latest_has_admin_reply:
            last_reply_actor = 'Admin'
            last_reply_preview = (latest_message.admin_reply or '').strip()
        else:
            last_reply_actor = 'Customer'
            last_reply_preview = (latest_message.message or '').strip()

        threads.append({
            'thread_id': root_id,
            'root': root_concern,
            'display_subject': normalize_support_subject(root_concern.subject),
            'messages': ordered_messages,
            'latest': latest_message,
            'has_any_admin_reply': has_any_admin_reply,
            'has_unread_admin_reply': has_unread_admin_reply,
            # Pending means no admin reply yet in the whole thread.
            'is_pending': not has_any_admin_reply,
            'last_reply_actor': last_reply_actor,
            'last_reply_preview': last_reply_preview,
            'last_activity_at': last_activity_at or latest_message.created_at
        })

    threads.sort(key=lambda item: item['last_activity_at'] or datetime.min, reverse=True)
    return threads


@app.route('/profile/notifications')
@login_required
def profile_notifications():
    """Dedicated support inbox showing user concerns and admin replies in one place."""
    status_filter = (request.args.get('status') or 'all').strip().lower()
    open_thread_raw = (request.args.get('open_thread') or '').strip()
    opened_thread_id = int(open_thread_raw) if open_thread_raw.isdigit() else None
    user_email = (current_user.email or '').strip().lower()

    # Mark unread admin replies in the opened thread as seen when user clicks a thread.
    if opened_thread_id is not None:
        opened_concern = db.session.get(SupportConcern, opened_thread_id)
        if opened_concern:
            concern_email = (opened_concern.email or '').strip().lower()
            if opened_concern.user_id == current_user.id or concern_email == user_email:
                root_id = resolve_thread_root_for_user(opened_concern, current_user.id, user_email)
                unread_rows = SupportConcern.query.filter(
                    or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
                    or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
                    SupportConcern.admin_reply.isnot(None),
                    SupportConcern.user_has_seen_reply.is_(False)
                ).all()
                if unread_rows:
                    for row in unread_rows:
                        row.user_has_seen_reply = True
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()

    active_threads = build_user_support_threads(current_user.id, user_email, include_archived=False)
    archived_threads = build_user_support_threads(current_user.id, user_email, include_archived=True)

    all_count = len(active_threads)
    pending_count = sum(1 for thread in active_threads if thread['is_pending'])
    replied_count = sum(1 for thread in active_threads if thread['has_any_admin_reply'])
    unread_count = sum(1 for thread in active_threads if thread['has_unread_admin_reply'])
    read_count = max(0, replied_count - unread_count)
    archived_count = len(archived_threads)

    if status_filter == 'pending':
        threads = [thread for thread in active_threads if thread['is_pending']]
    elif status_filter == 'replied':
        threads = [thread for thread in active_threads if thread['has_any_admin_reply']]
    elif status_filter == 'archived':
        threads = archived_threads
    elif status_filter == 'unread':
        threads = [thread for thread in active_threads if thread['has_unread_admin_reply']]
    elif status_filter == 'read':
        threads = [thread for thread in active_threads if thread['has_any_admin_reply'] and not thread['has_unread_admin_reply']]
    else:
        status_filter = 'all'
        threads = active_threads

    return render_template(
        'profile_notifications.html',
        threads=threads,
        opened_thread_id=opened_thread_id,
        status_filter=status_filter,
        all_count=all_count,
        pending_count=pending_count,
        replied_count=replied_count,
        archived_count=archived_count,
        unread_count=unread_count,
        read_count=read_count
    )


@app.route('/profile/notifications/<int:thread_id>/mark-seen')
@login_required
def mark_profile_notification_thread_seen(thread_id):
    """Mark unread admin replies as seen for a thread without reloading the page."""
    concern = db.session.get(SupportConcern, thread_id)
    if not concern:
        return jsonify({'ok': False, 'error': 'Thread not found'}), 404

    user_email = (current_user.email or '').strip().lower()
    concern_email = (concern.email or '').strip().lower()
    if concern.user_id != current_user.id and concern_email != user_email:
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403

    root_id = resolve_thread_root_for_user(concern, current_user.id, user_email)
    unread_rows = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
        or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.admin_reply.isnot(None),
        SupportConcern.user_has_seen_reply.is_(False)
    ).all()

    if not unread_rows:
        return jsonify({'ok': True, 'updated': 0})

    for row in unread_rows:
        row.user_has_seen_reply = True

    try:
        db.session.commit()
        return jsonify({'ok': True, 'updated': len(unread_rows)})
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to mark thread %s as seen', thread_id)
        return jsonify({'ok': False, 'error': 'Unable to update'}), 500


@app.route('/profile/notifications/<int:concern_id>/archive', methods=['POST'])
@login_required
def archive_profile_notification_thread(concern_id):
    """Archive a support thread from the user's notification center."""
    concern = SupportConcern.query.get_or_404(concern_id)
    user_email = (current_user.email or '').strip().lower()
    concern_email = (concern.email or '').strip().lower()
    if concern.user_id != current_user.id and concern_email != user_email:
        flash('You are not allowed to archive this thread.', 'danger')
        return redirect(url_for('profile_notifications'))

    root_id = resolve_thread_root_for_user(concern, current_user.id, user_email)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
        or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.is_user_deleted.is_(False)
    ).all()

    if not thread_items:
        flash('Thread not found.', 'warning')
        return redirect(url_for('profile_notifications'))

    for item in thread_items:
        item.is_user_archived = True
        item.user_archived_at = utcnow_naive()

    try:
        db.session.commit()
        flash('Thread archived.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to archive thread for concern %s', concern_id)
        flash('Could not archive this thread right now. Please try again.', 'danger')

    return redirect(url_for('profile_notifications'))


@app.route('/profile/notifications/<int:concern_id>/restore', methods=['POST'])
@login_required
def restore_profile_notification_thread(concern_id):
    """Restore an archived support thread back to active notifications."""
    concern = SupportConcern.query.get_or_404(concern_id)
    user_email = (current_user.email or '').strip().lower()
    concern_email = (concern.email or '').strip().lower()
    if concern.user_id != current_user.id and concern_email != user_email:
        flash('You are not allowed to restore this thread.', 'danger')
        return redirect(url_for('profile_notifications', status='archived'))

    root_id = resolve_thread_root_for_user(concern, current_user.id, user_email)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
        or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.is_user_deleted.is_(False)
    ).all()

    for item in thread_items:
        item.is_user_archived = False
        item.user_archived_at = None

    try:
        db.session.commit()
        flash('Thread restored to Notification Center.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to restore thread for concern %s', concern_id)
        flash('Could not restore this thread right now. Please try again.', 'danger')

    return redirect(url_for('profile_notifications', status='archived'))


@app.route('/profile/notifications/<int:concern_id>/delete', methods=['POST'])
@login_required
def delete_profile_notification_thread(concern_id):
    """Soft delete a support thread from user notifications only."""
    concern = SupportConcern.query.get_or_404(concern_id)
    user_email = (current_user.email or '').strip().lower()
    concern_email = (concern.email or '').strip().lower()
    if concern.user_id != current_user.id and concern_email != user_email:
        flash('You are not allowed to delete this thread.', 'danger')
        return redirect(url_for('profile_notifications'))

    root_id = resolve_thread_root_for_user(concern, current_user.id, user_email)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
        or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.is_user_deleted.is_(False)
    ).all()

    if not thread_items:
        flash('Thread already deleted.', 'info')
        return redirect(url_for('profile_notifications'))

    for item in thread_items:
        item.is_user_deleted = True
        item.user_deleted_at = utcnow_naive()

    try:
        db.session.commit()
        flash('Thread deleted from your Notification Center.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to delete thread for concern %s', concern_id)
        flash('Could not delete this thread right now. Please try again.', 'danger')

    return redirect(url_for('profile_notifications'))


@app.route('/profile/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_profile_notifications_read():
    """Mark all unread support replies as read for the current user."""
    user_email = (current_user.email or '').strip().lower()
    unread_replies = SupportConcern.query.filter(
        or_(SupportConcern.user_id == current_user.id, func.lower(SupportConcern.email) == user_email),
        SupportConcern.admin_reply.isnot(None),
        SupportConcern.is_user_archived.is_(False),
        SupportConcern.is_user_deleted.is_(False),
        SupportConcern.user_has_seen_reply.is_(False)
    ).all()

    if not unread_replies:
        flash('No unread support replies found.', 'info')
        return redirect(url_for('profile_notifications'))

    for concern in unread_replies:
        concern.user_has_seen_reply = True

    try:
        db.session.commit()
        reply_word = 'reply' if len(unread_replies) == 1 else 'replies'
        flash(f'Marked {len(unread_replies)} support {reply_word} as read.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to mark all support replies as read for user %s', current_user.id)
        flash('Could not update notifications right now. Please try again.', 'danger')

    return redirect(url_for('profile_notifications'))

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
                selected_car = db.session.get(Car, selected_car_id)
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
    
    car = db.session.get(Car, booking.car_id)
    
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
    
    except Exception:
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
    
    car = db.session.get(Car, booking.car_id)
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
    car = db.session.get(Car, booking.car_id)
    user = db.session.get(User, booking.user_id)
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
                return render_template('admin_car_form.html', form=form, title='Add Car', is_edit=False)
            
            # Validate image file type
            if not allowed_file(form.image.data.filename):
                flash('Invalid file type. Only PNG, JPG, JPEG, GIF are allowed.', 'danger')
                return render_template('admin_car_form.html', form=form, title='Add Car', is_edit=False)
            
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
    
    return render_template('admin_car_form.html', form=form, title='Add Car', is_edit=False)

@app.route('/admin/cars/<int:car_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_car(car_id):
    """Admin edit an existing car."""
    car = Car.query.get_or_404(car_id)
    form = CarForm(obj=car)
    
    if form.validate_on_submit():
        # Handle main image upload if a new image is provided.
        if form.image.data and form.image.data.filename:
            if not allowed_file(form.image.data.filename):
                flash('Invalid file type. Only PNG, JPG, JPEG, GIF are allowed.', 'danger')
                return render_template('admin_car_form.html', form=form, title='Edit Car', car=car, is_edit=True)

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
    
    return render_template('admin_car_form.html', form=form, title='Edit Car', car=car, is_edit=True)

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
            email_verified_at=utcnow_naive()
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


@app.route('/admin/support')
@admin_required
def admin_support():
    """Admin inbox in threaded conversation view."""
    status_filter = (request.args.get('status') or 'all').strip().lower()

    active_threads = build_admin_support_threads(include_archived=False)
    archived_threads = build_admin_support_threads(include_archived=True)

    total_active_count = len(active_threads)
    active_unread_count = sum(1 for thread in active_threads if thread['has_unread_customer_message'])
    active_replied_count = sum(1 for thread in active_threads if not thread['has_unread_customer_message'])
    archived_count = len(archived_threads)

    if status_filter == 'unread':
        threads = [thread for thread in active_threads if thread['has_unread_customer_message']]
    elif status_filter == 'archived':
        threads = archived_threads
    else:
        status_filter = 'all'
        threads = active_threads

    return render_template(
        'admin_support.html',
        threads=threads,
        status_filter=status_filter,
        total_active_count=total_active_count,
        active_replied_count=active_replied_count,
        active_unread_count=active_unread_count,
        archived_count=archived_count
    )


@app.route('/admin/support/<int:concern_id>/reply', methods=['POST'])
@admin_required
def admin_reply_support(concern_id):
    """Admin sends a reply for a concern and notifies customer email."""
    concern = SupportConcern.query.get_or_404(concern_id)
    reply_text = ' '.join((request.form.get('reply') or '').strip().split())

    if len(reply_text) < 5:
        flash('Please provide a complete reply before sending.', 'warning')
        return redirect(url_for('admin_support'))

    concern.admin_reply = reply_text
    concern.admin_replied_at = utcnow_naive()
    concern.replied_by_admin_id = current_user.id
    concern.admin_has_seen_message = True
    concern.user_has_seen_reply = False
    db.session.commit()

    mail_server = app.config.get('MAIL_SERVER')
    mail_sender = app.config.get('MAIL_FROM') or app.config.get('MAIL_USERNAME')

    if not mail_server or not mail_sender:
        flash('Reply saved. Customer can view this reply in their profile notifications.', 'success')
        return redirect(url_for('admin_support'))

    linked_user = db.session.get(User, concern.user_id) if concern.user_id else None
    target_email = (linked_user.email if linked_user and linked_user.email else concern.email or '').strip().lower()

    if '@' not in target_email:
        flash('Reply saved, but there is no valid customer email to send to.', 'warning')
        return redirect(url_for('admin_support'))

    email_message = EmailMessage()
    email_message['Subject'] = f"[Rent A Car Support Reply #{concern.id}] {concern.subject}"
    email_message['From'] = mail_sender
    email_message['To'] = target_email
    email_message['Reply-To'] = mail_sender
    email_message.set_content(
        f"Hello {concern.name},\n\n"
        f"Our admin team replied to your concern:\n\n"
        f"Subject: {concern.subject}\n"
        f"Reply:\n{reply_text}\n\n"
        "You can also check this reply in your Rent A Car profile under Support Notifications.\n"
    )

    try:
        mail_port = int(app.config.get('MAIL_PORT', 587))
        if mail_port == 465:
            with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], mail_port, timeout=15) as smtp:
                if app.config.get('MAIL_USERNAME'):
                    smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                smtp.send_message(email_message)
        else:
            with smtplib.SMTP(app.config['MAIL_SERVER'], mail_port, timeout=15) as smtp:
                if app.config.get('MAIL_USE_TLS'):
                    smtp.starttls()
                if app.config.get('MAIL_USERNAME'):
                    smtp.login(app.config['MAIL_USERNAME'], app.config.get('MAIL_PASSWORD') or '')
                smtp.send_message(email_message)
        flash('Reply sent successfully and customer notification is now available.', 'success')
    except Exception:
        app.logger.exception('Failed to send admin support reply email')
        flash('Reply saved, but email delivery failed. Customer can still view notification in profile.', 'warning')

    return redirect(url_for('admin_support'))


@app.route('/admin/support/mark-all-read', methods=['POST'])
@admin_required
def admin_mark_all_support_read():
    """Mark all unread customer messages as read in active admin inbox."""
    unread_messages = SupportConcern.query.filter(
        SupportConcern.is_archived.is_(False),
        SupportConcern.admin_reply.is_(None),
        SupportConcern.admin_has_seen_message.is_(False)
    ).all()

    if not unread_messages:
        flash('No unread customer messages found.', 'info')
        return redirect(url_for('admin_support'))

    for message in unread_messages:
        message.admin_has_seen_message = True

    try:
        db.session.commit()
        flash(f'Marked {len(unread_messages)} customer message(s) as read.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to mark admin support messages as read')
        flash('Could not update support messages right now. Please try again.', 'danger')

    return redirect(url_for('admin_support'))


@app.route('/admin/support/<int:concern_id>/mark-read')
@admin_required
def admin_mark_support_thread_read(concern_id):
    """Mark unread customer messages as read for one admin support thread."""
    concern = SupportConcern.query.get_or_404(concern_id)
    root_id = resolve_thread_root_for_admin(concern)

    unread_messages = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id),
        SupportConcern.admin_reply.is_(None),
        SupportConcern.admin_has_seen_message.is_(False)
    ).all()

    if not unread_messages:
        remaining_unread_count = SupportConcern.query.filter(
            SupportConcern.is_archived.is_(False),
            SupportConcern.admin_reply.is_(None),
            SupportConcern.admin_has_seen_message.is_(False)
        ).count()
        return jsonify({'ok': True, 'updated': 0, 'remaining_unread_count': remaining_unread_count})

    for message in unread_messages:
        message.admin_has_seen_message = True

    try:
        db.session.commit()
        remaining_unread_count = SupportConcern.query.filter(
            SupportConcern.is_archived.is_(False),
            SupportConcern.admin_reply.is_(None),
            SupportConcern.admin_has_seen_message.is_(False)
        ).count()
        return jsonify({'ok': True, 'updated': len(unread_messages), 'remaining_unread_count': remaining_unread_count})
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to mark support thread %s as read', concern_id)
        return jsonify({'ok': False, 'error': 'Unable to update'}), 500


@app.route('/admin/support/<int:concern_id>/archive', methods=['POST'])
@admin_required
def admin_archive_support(concern_id):
    """Archive a full support thread from active inbox view."""
    concern = SupportConcern.query.get_or_404(concern_id)
    root_id = resolve_thread_root_for_admin(concern)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id)
    ).all()

    try:
        archived_at = utcnow_naive()
        for item in thread_items:
            item.is_archived = True
            item.archived_at = archived_at
            item.archived_by_admin_id = current_user.id
        db.session.commit()
        flash(f'Support thread #{root_id} archived.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to archive support concern %s', concern_id)
        flash('Could not archive support concern right now. Please try again.', 'danger')

    return redirect(url_for('admin_support'))


@app.route('/admin/support/<int:concern_id>/unarchive', methods=['POST'])
@admin_required
def admin_unarchive_support(concern_id):
    """Restore an archived support thread back to active inbox view."""
    concern = SupportConcern.query.get_or_404(concern_id)
    root_id = resolve_thread_root_for_admin(concern)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id)
    ).all()

    try:
        for item in thread_items:
            item.is_archived = False
            item.archived_at = None
            item.archived_by_admin_id = None
        db.session.commit()
        flash(f'Support thread #{root_id} restored to active inbox.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to unarchive support concern %s', concern_id)
        flash('Could not restore support concern right now. Please try again.', 'danger')

    return redirect(url_for('admin_support', status='archived'))


@app.route('/admin/support/<int:concern_id>/delete', methods=['POST'])
@admin_required
def admin_delete_support(concern_id):
    """Delete a full support thread from admin inbox."""
    concern = SupportConcern.query.get_or_404(concern_id)
    root_id = resolve_thread_root_for_admin(concern)
    thread_items = SupportConcern.query.filter(
        or_(SupportConcern.id == root_id, SupportConcern.thread_root_id == root_id)
    ).all()

    try:
        for item in thread_items:
            db.session.delete(item)
        db.session.commit()
        flash(f'Support thread #{root_id} deleted successfully.', 'success')
    except Exception:
        db.session.rollback()
        app.logger.exception('Failed to delete support concern %s', concern_id)
        flash('Could not delete support concern right now. Please try again.', 'danger')

    return redirect(url_for('admin_support'))


def resolve_thread_root_for_admin(concern):
    """Resolve thread root id for admin, including legacy rows without root id."""
    if concern.thread_root_id:
        return min(concern.id, concern.thread_root_id)

    normalized_subject = normalize_support_subject(concern.subject)
    base_query = SupportConcern.query
    if concern.user_id:
        base_query = base_query.filter(SupportConcern.user_id == concern.user_id)
    else:
        base_query = base_query.filter(func.lower(SupportConcern.email) == (concern.email or '').strip().lower())

    owner_concerns = base_query.order_by(SupportConcern.created_at.asc(), SupportConcern.id.asc()).all()
    matching_items = [item for item in owner_concerns if normalize_support_subject(item.subject) == normalized_subject]
    if matching_items:
        canonical_root_id = min(
            [item.id for item in matching_items] +
            [item.thread_root_id for item in matching_items if item.thread_root_id]
        )
        has_updates = False
        for item in matching_items:
            if item.thread_root_id != canonical_root_id:
                item.thread_root_id = canonical_root_id
                has_updates = True
        if has_updates:
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
        return canonical_root_id

    return concern.id


def build_admin_support_threads(include_archived=False):
    """Return grouped support conversation threads for admin inbox."""
    query = SupportConcern.query
    if include_archived:
        query = query.filter(SupportConcern.is_archived.is_(True))
    else:
        query = query.filter(SupportConcern.is_archived.is_(False))

    concerns = query.order_by(SupportConcern.created_at.asc(), SupportConcern.id.asc()).all()
    subject_roots = {}
    has_thread_updates = False
    grouped_threads = {}

    for concern in concerns:
        owner_key = concern.user_id if concern.user_id else (concern.email or '').strip().lower()
        subject_key = (owner_key, normalize_support_subject(concern.subject))
        derived_root = min(concern.id, concern.thread_root_id or concern.id)

        if concern.thread_root_id:
            root_id = min(concern.id, concern.thread_root_id)
        else:
            root_id = subject_roots.get(subject_key, derived_root)
            if concern.thread_root_id != root_id:
                concern.thread_root_id = root_id
                has_thread_updates = True

        subject_roots.setdefault(subject_key, root_id)
        grouped_threads.setdefault(root_id, []).append(concern)

    if has_thread_updates:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    threads = []
    for root_id, items in grouped_threads.items():
        ordered_messages = sorted(items, key=lambda item: (item.created_at or datetime.min, item.id))
        root_concern = next((item for item in ordered_messages if item.id == root_id), None)
        if not root_concern:
            root_concern = db.session.get(SupportConcern, root_id) or ordered_messages[0]
        latest_message = ordered_messages[-1]
        pending_items = [item for item in ordered_messages if not (item.admin_reply or '').strip()]
        pending_target = pending_items[-1] if pending_items else None
        unread_customer_items = [item for item in pending_items if not item.admin_has_seen_message]

        has_any_admin_reply = any(bool((item.admin_reply or '').strip()) for item in ordered_messages)
        has_pending = bool(pending_target)
        has_unread_customer_message = bool(unread_customer_items)
        last_activity_at = latest_message.admin_replied_at if (latest_message.admin_reply or '').strip() else latest_message.created_at

        threads.append({
            'thread_id': root_id,
            'root': root_concern,
            'display_subject': normalize_support_subject(root_concern.subject),
            'messages': ordered_messages,
            'latest': latest_message,
            'pending_target': pending_target,
            'has_pending': has_pending,
            'has_unread_customer_message': has_unread_customer_message,
            'has_any_admin_reply': has_any_admin_reply,
            'last_activity_at': last_activity_at or latest_message.created_at
        })

    threads.sort(key=lambda item: item['last_activity_at'] or datetime.min, reverse=True)
    return threads

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
    now = utcnow_naive()
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

