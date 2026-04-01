# Sample Data Guide

## Overview

This guide explains the sample data that has been added to the Rent A Car system for testing and demonstration purposes.

## Running the Sample Data Seeder

### Quick Start
```bash
python seed_complete_data.py
```

### Manual Method
```bash
python
>>> from seed_complete_data import seed_complete_database
>>> seed_complete_database()
```

## What Gets Added

### 🚗 Cars (8 Vehicles)

| Car Model | Daily Rate | Seats | Fuel | Transmission |
|-----------|-----------|-------|------|--------------|
| Toyota Innova | ₱2,500 | 7 | Diesel | Automatic |
| Honda City | ₱1,500 | 5 | Gasoline | Automatic |
| Mitsubishi Xpander | ₱1,800 | 7 | Gasoline | Automatic |
| Hyundai Accent | ₱1,200 | 5 | Gasoline | Manual |
| Suzuki APV | ₱1,400 | 8 | Gasoline | Manual |
| Toyota Vios | ₱1,300 | 5 | Gasoline | Automatic |
| Nissan Urvan | ₱2,200 | 15 | Diesel | Manual |
| Chevrolet Spark | ₱1,000 | 5 | Gasoline | Manual |

### 👥 Users (7 Accounts)

**Regular Customers:**
1. **Juan Carlos Santos**
   - Email: juan@example.com
   - Password: password123
   
2. **Maria Grace Silva**
   - Email: maria@example.com
   - Password: password123
   
3. **Pedro Alfonso**
   - Email: pedro@example.com
   - Password: password123
   
4. **Rosa Maria Delacruz**
   - Email: rosa@example.com
   - Password: password123
   
5. **Carlos Antonio**
   - Email: carlos@example.com
   - Password: password123
   
6. **Angela Louise**
   - Email: angela@example.com
   - Password: password123

**Admin Account:**
1. **System Administrator**
   - Email: admin@example.com
   - Password: admin123
   - **Permissions**: Full system access

### 💳 Payment Methods (5 Options)

1. **Credit Card** - Visa, Mastercard, American Express
2. **Debit Card** - Bank of Philippine Islands, Metrobank, etc.
3. **Cash** - On-site payment at pickup
4. **GCash** - Mobile payment solution
5. **Bank Transfer** - Direct bank deposit

### 📅 Bookings (8 Records)

Sample bookings with various statuses to test the booking workflow:

| Booking # | Customer | Car | Status | From | To | Payment Method |
|-----------|----------|-----|--------|------|-----|-----------------|
| 1 | Juan | Innova | Pending | 2024-01-15 | 2024-01-18 | Credit Card |
| 2 | Maria | City | Approved | 2024-01-20 | 2024-01-22 | Cash |
| 3 | Pedro | Xpander | Completed | 2024-01-10 | 2024-01-13 | GCash |
| 4 | Rosa | Innova | Rejected | 2024-01-25 | 2024-01-28 | Debit Card |
| 5 | Carlos | Accent | Approved | 2024-01-12 | 2024-01-15 | Bank Transfer |
| 6 | Angela | APV | Completed | 2024-01-05 | 2024-01-08 | Credit Card |
| 7 | Juan | Vios | Approved | 2024-01-22 | 2024-01-24 | Cash |
| 8 | Maria | Urvan | Pending | 2024-01-18 | 2024-01-20 | GCash |

### ⭐ Reviews (7 Feedbacks)

Sample reviews from customers about their rental experiences:

- **5-star reviews** (3): Perfect experiences, highly recommended
- **4-star reviews** (3): Good experiences with minor observations
- **3-star reviews** (1): Average experience, some issues

### 💰 Payments (5 Transactions)

Sample payment records showing different payment methods and amounts:

- **Credit Card**: ₱3,600 - ₱12,500
- **GCash**: ₱4,500 - ₱5,400
- **Bank Transfer**: ₱15,400
- **Cash**: ₱3,000

## Testing Workflows

### 1. Testing User Login
```
Use any customer account:
- Email: juan@example.com
- Password: password123
```

### 2. Testing Booking Management
1. Login as customer
2. View your bookings (Juan has 2 bookings)
3. Check booking statuses
4. View booking details

### 3. Testing Admin Dashboard
```
Login as admin:
- Email: admin@example.com
- Password: admin123
```

Then access:
- Dashboard Statistics
- Car Management
- Booking Management
- User Management
- Reports

### 4. Testing Car Reviews
1. Login as customer
2. Go to car details page
3. View existing reviews from sample data
4. Check rating distributions

### 5. Testing Date Conflict Detection
1. Try booking a car that already has an approved/completed booking
2. You should not be able to select overlapping dates

## Important Notes

### ✅ What You Can Do
- Login with any account and test features
- Make new bookings (the sample dates are set in the future)
- Leave reviews on completed bookings
- Edit your own bookings
- Admin can manage everything

### ⚠️ Important Behaviors
- **Pending bookings** don't block dates for new bookings
- **Approved, Completed, Returned bookings** block dates
- **Rejected bookings** don't block dates
- All sample users have the same password: `password123`
- Admin password is: `admin123`

### 🔄 Re-running the Seeder
You can safely re-run `python seed_complete_data.py` multiple times without creating duplicates. The script uses try-except blocks to handle duplicate entries gracefully.

## Cleaning Sample Data

If you want to start fresh with a clean database:

```bash
# Delete the database file
rm instance/car_rental.db

# Recreate the database
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()

# Add fresh sample data
python seed_complete_data.py
```

## Viewing Sample Data

### Using Python Shell
```python
from app import app
from models import Car, User, Booking, Review, Payment

with app.app_context():
    # View all cars
    cars = Car.query.all()
    for car in cars:
        print(f"{car.name} - ₱{car.price}")
    
    # View all bookings
    bookings = Booking.query.all()
    for booking in bookings:
        print(f"Booking: {booking.id} - Status: {booking.status}")
    
    # View all reviews
    reviews = Review.query.all()
    for review in reviews:
        print(f"Rating: {review.rating} stars - {review.comment}")
```

## Troubleshooting

### Issue: "Bookings already exist"
**Solution**: Run `python seed_complete_data.py` again. The script handles duplicates.

### Issue: Can't login with sample accounts
**Solution**: Make sure you've run `python seed_complete_data.py` first.

### Issue: No cars showing in car listing
**Solution**: Verify sample cars were added:
```python
from app import app
from models import Car

with app.app_context():
    print(Car.query.count())  # Should print 8
```

## Contact & Support

For questions about the sample data or testing:
1. Check this guide first
2. Review the status of your bookings
3. Verify admin account credentials
4. Check the system logs terminal output

---

**Last Updated**: 2024  
**Sample Data Version**: 1.0
