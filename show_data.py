from app import app, db
from models import User, PaymentMethod, Booking, Review, Payment

with app.app_context():
    print('='*60)
    print('📊 SAMPLE DATA SUMMARY')
    print('='*60)
    
    print('\n👥 USERS (5):')
    users = db.session.query(User).all()
    for u in users[:5]:
        admin_badge = "👑 ADMIN" if u.is_admin else "user"
        print(f'   • {u.name} ({u.email}) - {admin_badge}')
    
    print('\n💳 PAYMENT METHODS (5):')
    methods = db.session.query(PaymentMethod).all()
    for m in methods:
        print(f'   • {m.method_name}')
    
    print('\n🚗 BOOKINGS (5):')
    bookings = db.session.query(Booking).all()
    for b in bookings[:5]:
        print(f'   • ID {b.id}: {b.name} - Car {b.car_id} - Status: {b.status}')
    
    print('\n⭐ REVIEWS (5):')
    reviews = db.session.query(Review).all()
    for r in reviews[:5]:
        print(f'   • Rating: {r.rating}/5 - "{r.comment[:45]}..."')
    
    print('\n💰 PAYMENTS (5):')
    payments = db.session.query(Payment).all()
    for p in payments[:5]:
        print(f'   • Payment {p.id}: PHP {p.amount_paid} - Booking {p.booking_id}')
    
    print('\n' + '='*60)
    print('✅ All sample data ready for testing!')
    print('='*60)
