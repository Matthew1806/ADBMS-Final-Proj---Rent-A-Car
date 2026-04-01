"""
Sample Data Seeder for Rent A Car System
Adds sample users, payment methods, bookings, reviews, and payments
Make sure to add at least 5 cars first before running this script
"""

from app import app, db
from models import User, PaymentMethod, Booking, Review, Payment
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date

def seed_complete_database():
    """Add comprehensive sample data to the database"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("🚗 RENT A CAR - COMPLETE SAMPLE DATA SEEDER 🚗".center(60))
        print("="*60 + "\n")
        
        # Check existing cars first
        from models import Car
        existing_cars = Car.query.all()
        car_ids = [car.id for car in existing_cars]
        
        if not car_ids:
            print("❌ ERROR: No cars found in database!")
            print("⚠️  Please add at least 1 car before running this seeder.")
            print("="*60 + "\n")
            return
        
        print(f"✅ Found {len(existing_cars)} car(s) in database: {car_ids}\n")
        
        # ========== USERS ==========
        print("👥 Adding Users...")
        users = [
            User(
                name="Juan Dela Cruz",
                email="juan@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            ),
            User(
                name="Maria Santos",
                email="maria@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            ),
            User(
                name="Admin User",
                email="admin@example.com",
                password=generate_password_hash("admin123"),
                is_admin=True,
                created_at=datetime.utcnow()
            ),
            User(
                name="Pedro Garcia",
                email="pedro@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            ),
            User(
                name="Rosa Reyes",
                email="rosa@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            ),
            User(
                name="Carlos Mendoza",
                email="carlos@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            ),
            User(
                name="Angela Fernandez",
                email="angela@example.com",
                password=generate_password_hash("password123"),
                is_admin=False,
                created_at=datetime.utcnow()
            )
        ]
        
        for user in users:
            try:
                existing = User.query.filter_by(email=user.email).first()
                if not existing:
                    db.session.add(user)
            except:
                db.session.add(user)
        db.session.commit()
        print(f"✅ Added {len(users)} users\n")
        
        # ========== PAYMENT METHODS ==========
        print("💳 Adding Payment Methods...")
        payment_methods = [
            PaymentMethod(method_name="Credit Card"),
            PaymentMethod(method_name="Debit Card"),
            PaymentMethod(method_name="Cash"),
            PaymentMethod(method_name="GCash"),
            PaymentMethod(method_name="Bank Transfer")
        ]
        
        for method in payment_methods:
            try:
                existing = PaymentMethod.query.filter_by(method_name=method.method_name).first()
                if not existing:
                    db.session.add(method)
            except:
                db.session.add(method)
        db.session.commit()
        print(f"✅ Added {len(payment_methods)} payment methods\n")
        
        # ========== BOOKINGS ==========
        print("📅 Adding Bookings (2-3 per user)...")
        bookings = [
            # User 1 - Juan Dela Cruz (3 bookings)
            Booking(
                user_id=1,
                name="Juan Dela Cruz",
                email="juan@example.com",
                contact="09171234567",
                car_id=1,
                pickup_date=date.today() + timedelta(days=5),
                return_date=date.today() + timedelta(days=10),
                status="Approved",
                payment_method="Credit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=1,
                name="Juan Dela Cruz",
                email="juan@example.com",
                contact="09171234567",
                car_id=2,
                pickup_date=date.today() + timedelta(days=15),
                return_date=date.today() + timedelta(days=18),
                status="Pending",
                payment_method="GCash",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=1,
                name="Juan Dela Cruz",
                email="juan@example.com",
                contact="09171234567",
                car_id=3,
                pickup_date=date.today() + timedelta(days=25),
                return_date=date.today() + timedelta(days=28),
                status="Completed",
                payment_method="Cash",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            # User 2 - Maria Santos (3 bookings)
            Booking(
                user_id=2,
                name="Maria Santos",
                email="maria@example.com",
                contact="09187654321",
                car_id=1,
                pickup_date=date.today() + timedelta(days=3),
                return_date=date.today() + timedelta(days=7),
                status="Approved",
                payment_method="Debit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=2,
                name="Maria Santos",
                email="maria@example.com",
                contact="09187654321",
                car_id=4,
                pickup_date=date.today() + timedelta(days=12),
                return_date=date.today() + timedelta(days=16),
                status="Pending",
                payment_method="Bank Transfer",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=2,
                name="Maria Santos",
                email="maria@example.com",
                contact="09187654321",
                car_id=5,
                pickup_date=date.today() + timedelta(days=20),
                return_date=date.today() + timedelta(days=23),
                status="Completed",
                payment_method="GCash",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            # User 3 - Admin User (2 bookings)
            Booking(
                user_id=3,
                name="Admin User",
                email="admin@example.com",
                contact="09161111111",
                car_id=2,
                pickup_date=date.today() + timedelta(days=8),
                return_date=date.today() + timedelta(days=11),
                status="Approved",
                payment_method="Credit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=3,
                name="Admin User",
                email="admin@example.com",
                contact="09161111111",
                car_id=3,
                pickup_date=date.today() + timedelta(days=30),
                return_date=date.today() + timedelta(days=35),
                status="Pending",
                payment_method="Cash",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            ),
            # User 4 - Pedro Garcia (3 bookings)
            Booking(
                user_id=4,
                name="Pedro Garcia",
                email="pedro@example.com",
                contact="09159876543",
                car_id=4,
                pickup_date=date.today() + timedelta(days=2),
                return_date=date.today() + timedelta(days=5),
                status="Approved",
                payment_method="Debit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=4,
                name="Pedro Garcia",
                email="pedro@example.com",
                contact="09159876543",
                car_id=1,
                pickup_date=date.today() + timedelta(days=10),
                return_date=date.today() + timedelta(days=14),
                status="Completed",
                payment_method="GCash",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=4,
                name="Pedro Garcia",
                email="pedro@example.com",
                contact="09159876543",
                car_id=5,
                pickup_date=date.today() + timedelta(days=18),
                return_date=date.today() + timedelta(days=22),
                status="Rejected",
                payment_method="Bank Transfer",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            ),
            # User 5 - Rosa Reyes (2 bookings)
            Booking(
                user_id=5,
                name="Rosa Reyes",
                email="rosa@example.com",
                contact="09165432109",
                car_id=2,
                pickup_date=date.today() + timedelta(days=6),
                return_date=date.today() + timedelta(days=9),
                status="Completed",
                payment_method="Credit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=5,
                name="Rosa Reyes",
                email="rosa@example.com",
                contact="09165432109",
                car_id=3,
                pickup_date=date.today() + timedelta(days=24),
                return_date=date.today() + timedelta(days=27),
                status="Approved",
                payment_method="Cash",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            # User 6 - Carlos Mendoza (3 bookings)
            Booking(
                user_id=6,
                name="Carlos Mendoza",
                email="carlos@example.com",
                contact="09163334444",
                car_id=4,
                pickup_date=date.today() + timedelta(days=1),
                return_date=date.today() + timedelta(days=4),
                status="Approved",
                payment_method="Debit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=6,
                name="Carlos Mendoza",
                email="carlos@example.com",
                contact="09163334444",
                car_id=5,
                pickup_date=date.today() + timedelta(days=9),
                return_date=date.today() + timedelta(days=13),
                status="Pending",
                payment_method="GCash",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=6,
                name="Carlos Mendoza",
                email="carlos@example.com",
                contact="09163334444",
                car_id=1,
                pickup_date=date.today() + timedelta(days=32),
                return_date=date.today() + timedelta(days=36),
                status="Completed",
                payment_method="Bank Transfer",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            # User 7 - Angela Fernandez (3 bookings)
            Booking(
                user_id=7,
                name="Angela Fernandez",
                email="angela@example.com",
                contact="09175557777",
                car_id=2,
                pickup_date=date.today() + timedelta(days=7),
                return_date=date.today() + timedelta(days=11),
                status="Completed",
                payment_method="Credit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=7,
                name="Angela Fernandez",
                email="angela@example.com",
                contact="09175557777",
                car_id=3,
                pickup_date=date.today() + timedelta(days=17),
                return_date=date.today() + timedelta(days=21),
                status="Approved",
                payment_method="Debit Card",
                payment_status="Paid",
                submitted_at=datetime.utcnow()
            ),
            Booking(
                user_id=7,
                name="Angela Fernandez",
                email="angela@example.com",
                contact="09175557777",
                car_id=5,
                pickup_date=date.today() + timedelta(days=29),
                return_date=date.today() + timedelta(days=33),
                status="Pending",
                payment_method="GCash",
                payment_status="Unpaid",
                submitted_at=datetime.utcnow()
            )
        ]
        
        for booking in bookings:
            try:
                db.session.add(booking)
            except:
                pass
        db.session.commit()
        print(f"✅ Added {len(bookings)} bookings\n")
        
        # ========== REVIEWS ==========
        print("⭐ Adding Reviews...")
        reviews = [
            Review(
                user_id=1,
                car_id=1,
                booking_id=1,
                rating=5,
                comment="Excellent car! Very clean and well-maintained. Great service!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=1,
                car_id=3,
                booking_id=3,
                rating=4,
                comment="Good condition, comfortable drive. Highly recommended!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=2,
                car_id=1,
                booking_id=4,
                rating=5,
                comment="Perfect! Everything was great. Will rent again!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=2,
                car_id=5,
                booking_id=6,
                rating=4,
                comment="Good value for money, reliable vehicle.",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=3,
                car_id=2,
                booking_id=7,
                rating=5,
                comment="Amazing experience, very satisfied!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=4,
                car_id=4,
                booking_id=9,
                rating=4,
                comment="Good car, comfortable and reliable.",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=4,
                car_id=1,
                booking_id=10,
                rating=5,
                comment="Excellent service and car condition!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=5,
                car_id=2,
                booking_id=13,
                rating=4,
                comment="Very good rental experience.",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=6,
                car_id=4,
                booking_id=15,
                rating=5,
                comment="Best rental experience ever!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=6,
                car_id=1,
                booking_id=17,
                rating=4,
                comment="Good quality service and vehicle.",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=7,
                car_id=2,
                booking_id=18,
                rating=5,
                comment="Wonderful experience, highly recommend!",
                created_at=datetime.utcnow()
            ),
            Review(
                user_id=7,
                car_id=3,
                booking_id=19,
                rating=4,
                comment="Great car and excellent service.",
                created_at=datetime.utcnow()
            )
        ]
        
        for review in reviews:
            try:
                db.session.add(review)
            except:
                pass
        db.session.commit()
        print(f"✅ Added {len(reviews)} reviews\n")
        
        # ========== PAYMENTS ==========
        print("💰 Adding Payments...")
        payments = [
            Payment(
                user_id=1,
                booking_id=1,
                payment_method_id=1,
                amount_paid=12500,
                date_paid="2026-03-20",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=1,
                booking_id=3,
                payment_method_id=3,
                amount_paid=7500,
                date_paid="2026-03-25",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=2,
                booking_id=4,
                payment_method_id=2,
                amount_paid=15000,
                date_paid="2026-03-19",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=2,
                booking_id=6,
                payment_method_id=4,
                amount_paid=9000,
                date_paid="2026-03-22",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=3,
                booking_id=7,
                payment_method_id=1,
                amount_paid=11000,
                date_paid="2026-03-17",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=4,
                booking_id=9,
                payment_method_id=2,
                amount_paid=9000,
                date_paid="2026-03-18",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=4,
                booking_id=10,
                payment_method_id=4,
                amount_paid=10000,
                date_paid="2026-03-21",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=5,
                booking_id=13,
                payment_method_id=1,
                amount_paid=7500,
                date_paid="2026-03-16",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=6,
                booking_id=15,
                payment_method_id=2,
                amount_paid=9000,
                date_paid="2026-03-19",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=6,
                booking_id=17,
                payment_method_id=5,
                amount_paid=12500,
                date_paid="2026-03-23",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=7,
                booking_id=18,
                payment_method_id=1,
                amount_paid=11000,
                date_paid="2026-03-20",
                created_at=datetime.utcnow()
            ),
            Payment(
                user_id=7,
                booking_id=19,
                payment_method_id=2,
                amount_paid=10000,
                date_paid="2026-03-24",
                created_at=datetime.utcnow()
            )
        ]
        
        for payment in payments:
            try:
                db.session.add(payment)
            except:
                pass
        db.session.commit()
        print(f"✅ Added {len(payments)} payments\n")
        
        # ========== SUMMARY ==========
        print("="*60)
        print("🎉 SAMPLE DATA SUCCESSFULLY ADDED!".center(60))
        print("="*60 + "\n")
        
        users_count = User.query.count()
        methods_count = PaymentMethod.query.count()
        bookings_count = Booking.query.count()
        reviews_count = Review.query.count()
        payments_count = Payment.query.count()
        
        print("📊 DATA SUMMARY:")
        print(f"  👥 Users:             {users_count}")
        print(f"  💳 Payment Methods:   {methods_count}")
        print(f"  📅 Bookings:          {bookings_count}")
        print(f"  ⭐ Reviews:           {reviews_count}")
        print(f"  💰 Payments:          {payments_count}")
        print("\n" + "="*60)
        
        print("\n📝 SAMPLE LOGIN CREDENTIALS:")
        print("  Regular User:")
        print("    Email: juan@example.com")
        print("    Password: password123")
        print("\n  Admin User:")
        print("    Email: admin@example.com")
        print("    Password: admin123")
        print("\n" + "="*60 + "\n")
        
        print("⚠️  NOTE: Make sure you have at least 5 cars added in the database!")
        print("   Cars used: car_id 1, 2, 3, 4, 5")
        print("="*60 + "\n")

if __name__ == "__main__":
    seed_complete_database()
