"""
Smart Sample Data Seeder for Rent A Car System
Automatically uses existing cars and creates interconnected data
No hardcoded car IDs - works with whatever cars are in the database
"""

from app import app, db
from models import User, PaymentMethod, Booking, Review, Payment, Car
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta, date

def seed_complete_database():
    """Add comprehensive sample data that matches existing cars"""
    
    with app.app_context():
        print("\n" + "="*60)
        print("🚗 RENT A CAR - SMART DATA SEEDER 🚗".center(60))
        print("="*60 + "\n")
        
        # Check existing cars first
        existing_cars = Car.query.all()
        car_ids = [car.id for car in existing_cars]
        
        if not car_ids:
            print("❌ ERROR: No cars found in database!")
            print("⚠️  Please add at least 1 car before running this seeder.")
            print("   Go to Admin → Cars → Add Car")
            print("="*60 + "\n")
            return
        
        print(f"✅ Found {len(existing_cars)} car(s) in database")
        for car in existing_cars:
            print(f"   - Car #{car.id}: {car.name}")
        print()
        
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
        
        # Cycle through available cars
        payment_statuses = ["Paid", "Paid", "Unpaid", "Paid"]
        car_index = 0
        
        bookings = [
            # User 1 - Juan (3 bookings)
            Booking(user_id=1, name="Juan Dela Cruz", email="juan@example.com", contact="09171234567",
                   car_id=car_ids[car_index % len(car_ids)], pickup_date=date.today() + timedelta(days=5),
                   return_date=date.today() + timedelta(days=10), status="Approved", 
                   payment_method="Credit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=1, name="Juan Dela Cruz", email="juan@example.com", contact="09171234567",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=15),
                   return_date=date.today() + timedelta(days=18), status="Pending",
                   payment_method="GCash", payment_status="Unpaid", submitted_at=datetime.utcnow()),
            Booking(user_id=1, name="Juan Dela Cruz", email="juan@example.com", contact="09171234567",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=25),
                   return_date=date.today() + timedelta(days=28), status="Completed",
                   payment_method="Cash", payment_status="Paid", submitted_at=datetime.utcnow()),
            
            # User 2 - Maria (3 bookings)
            Booking(user_id=2, name="Maria Santos", email="maria@example.com", contact="09187654321",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=3),
                   return_date=date.today() + timedelta(days=7), status="Approved",
                   payment_method="Debit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=2, name="Maria Santos", email="maria@example.com", contact="09187654321",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=12),
                   return_date=date.today() + timedelta(days=16), status="Pending",
                   payment_method="Bank Transfer", payment_status="Unpaid", submitted_at=datetime.utcnow()),
            Booking(user_id=2, name="Maria Santos", email="maria@example.com", contact="09187654321",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=20),
                   return_date=date.today() + timedelta(days=23), status="Completed",
                   payment_method="GCash", payment_status="Paid", submitted_at=datetime.utcnow()),
            
            # User 3 - Admin (2 bookings)
            Booking(user_id=3, name="Admin User", email="admin@example.com", contact="09161111111",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=8),
                   return_date=date.today() + timedelta(days=11), status="Approved",
                   payment_method="Credit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=3, name="Admin User", email="admin@example.com", contact="09161111111",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=30),
                   return_date=date.today() + timedelta(days=35), status="Pending",
                   payment_method="Cash", payment_status="Unpaid", submitted_at=datetime.utcnow()),
            
            # User 4 - Pedro (3 bookings)
            Booking(user_id=4, name="Pedro Garcia", email="pedro@example.com", contact="09159876543",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=2),
                   return_date=date.today() + timedelta(days=5), status="Approved",
                   payment_method="Debit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=4, name="Pedro Garcia", email="pedro@example.com", contact="09159876543",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=10),
                   return_date=date.today() + timedelta(days=14), status="Completed",
                   payment_method="GCash", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=4, name="Pedro Garcia", email="pedro@example.com", contact="09159876543",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=18),
                   return_date=date.today() + timedelta(days=22), status="Rejected",
                   payment_method="Bank Transfer", payment_status="Unpaid", submitted_at=datetime.utcnow()),
            
            # User 5 - Rosa (2 bookings)
            Booking(user_id=5, name="Rosa Reyes", email="rosa@example.com", contact="09165432109",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=6),
                   return_date=date.today() + timedelta(days=9), status="Completed",
                   payment_method="Credit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=5, name="Rosa Reyes", email="rosa@example.com", contact="09165432109",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=24),
                   return_date=date.today() + timedelta(days=27), status="Approved",
                   payment_method="Cash", payment_status="Paid", submitted_at=datetime.utcnow()),
            
            # User 6 - Carlos (3 bookings)
            Booking(user_id=6, name="Carlos Mendoza", email="carlos@example.com", contact="09163334444",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=1),
                   return_date=date.today() + timedelta(days=4), status="Approved",
                   payment_method="Debit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=6, name="Carlos Mendoza", email="carlos@example.com", contact="09163334444",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=9),
                   return_date=date.today() + timedelta(days=13), status="Pending",
                   payment_method="GCash", payment_status="Unpaid", submitted_at=datetime.utcnow()),
            Booking(user_id=6, name="Carlos Mendoza", email="carlos@example.com", contact="09163334444",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=32),
                   return_date=date.today() + timedelta(days=36), status="Completed",
                   payment_method="Bank Transfer", payment_status="Paid", submitted_at=datetime.utcnow()),
            
            # User 7 - Angela (3 bookings)
            Booking(user_id=7, name="Angela Fernandez", email="angela@example.com", contact="09175557777",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=7),
                   return_date=date.today() + timedelta(days=11), status="Completed",
                   payment_method="Credit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=7, name="Angela Fernandez", email="angela@example.com", contact="09175557777",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=17),
                   return_date=date.today() + timedelta(days=21), status="Approved",
                   payment_method="Debit Card", payment_status="Paid", submitted_at=datetime.utcnow()),
            Booking(user_id=7, name="Angela Fernandez", email="angela@example.com", contact="09175557777",
                   car_id=car_ids[(car_index:=car_index+1) % len(car_ids)], pickup_date=date.today() + timedelta(days=29),
                   return_date=date.today() + timedelta(days=33), status="Pending",
                   payment_method="GCash", payment_status="Unpaid", submitted_at=datetime.utcnow())
        ]
        
        for booking in bookings:
            db.session.add(booking)
        db.session.commit()
        print(f"✅ Added {len(bookings)} bookings\n")
        
        # Get all bookings to reference in reviews/payments
        created_bookings = Booking.query.all()
        booking_ids = [b.id for b in created_bookings]
        
        # ========== REVIEWS ==========
        print("⭐ Adding Reviews...")
        reviews = [
            Review(user_id=1, car_id=created_bookings[0].car_id, booking_id=booking_ids[0], rating=5,
                   comment="Excellent car! Very clean and well-maintained. Highly recommended!", created_at=datetime.utcnow()),
            Review(user_id=1, car_id=created_bookings[2].car_id, booking_id=booking_ids[2], rating=4,
                   comment="Good condition, comfortable drive. Will rent again!", created_at=datetime.utcnow()),
            Review(user_id=2, car_id=created_bookings[3].car_id, booking_id=booking_ids[3], rating=5,
                   comment="Perfect! Everything was great. Highly satisfied!", created_at=datetime.utcnow()),
            Review(user_id=2, car_id=created_bookings[5].car_id, booking_id=booking_ids[5], rating=4,
                   comment="Good value for money, reliable vehicle.", created_at=datetime.utcnow()),
            Review(user_id=3, car_id=created_bookings[6].car_id, booking_id=booking_ids[6], rating=5,
                   comment="Amazing experience, very satisfied!", created_at=datetime.utcnow()),
            Review(user_id=4, car_id=created_bookings[8].car_id, booking_id=booking_ids[8], rating=4,
                   comment="Good car, comfortable and reliable.", created_at=datetime.utcnow()),
            Review(user_id=4, car_id=created_bookings[9].car_id, booking_id=booking_ids[9], rating=5,
                   comment="Excellent service and car condition!", created_at=datetime.utcnow()),
            Review(user_id=5, car_id=created_bookings[11].car_id, booking_id=booking_ids[11], rating=4,
                   comment="Very good rental experience.", created_at=datetime.utcnow()),
            Review(user_id=6, car_id=created_bookings[13].car_id, booking_id=booking_ids[13], rating=5,
                   comment="Best rental experience ever!", created_at=datetime.utcnow()),
            Review(user_id=6, car_id=created_bookings[15].car_id, booking_id=booking_ids[15], rating=4,
                   comment="Good quality service and vehicle.", created_at=datetime.utcnow()),
            Review(user_id=7, car_id=created_bookings[16].car_id, booking_id=booking_ids[16], rating=5,
                   comment="Wonderful experience, highly recommend!", created_at=datetime.utcnow()),
            Review(user_id=7, car_id=created_bookings[17].car_id, booking_id=booking_ids[17], rating=4,
                   comment="Great car and excellent service.", created_at=datetime.utcnow())
        ]
        
        for review in reviews:
            db.session.add(review)
        db.session.commit()
        print(f"✅ Added {len(reviews)} reviews\n")
        
        # ========== PAYMENTS ==========
        print("💰 Adding Payments...")
        # Only add payments for bookings with "Paid" status
        paid_bookings = [b for b in created_bookings if b.payment_status == "Paid"]
        
        payments = []
        for idx, booking in enumerate(paid_bookings[:10]):  # Max 10 payments
            payment = Payment(
                user_id=booking.user_id,
                booking_id=booking.id,
                payment_method_id=((idx % 5) + 1),  # Cycle through payment methods
                amount_paid=5000 + (idx * 1000),
                date_paid=(booking.submitted_at + timedelta(days=1)).strftime("%Y-%m-%d"),
                created_at=datetime.utcnow()
            )
            payments.append(payment)
            db.session.add(payment)
        
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
        print(f"  🚗 Cars:              {len(car_ids)}")
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

if __name__ == "__main__":
    seed_complete_database()
