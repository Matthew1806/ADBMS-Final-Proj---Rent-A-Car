# 🚗 Sample Data Quick Start Guide

## What Was Added?

A comprehensive set of realistic sample data has been prepared for testing and demonstrating the Rent A Car system:

- **8 Realistic Cars** with full specifications
- **7 User Accounts** (6 customers + 1 admin)
- **8 Sample Bookings** with various statuses
- **7 Customer Reviews** with ratings
- **5 Payment Methods** and transactional data
- **5 Payment Records** showing various transactions

## ⚡ Quick Start (3 Steps)

### Step 1: Initialize Database
```bash
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()
```

### Step 2: Add Sample Data
```bash
python seed_complete_data.py
```

You should see output like:
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

### Step 3: Verify Installation
```bash
python verify_sample_data.py
```

You should see detailed information about all the sample data that was added.

## 🔐 Test Account Credentials

### Customer Account
```
Email: juan@example.com
Password: password123
```

### Admin Account
```
Email: admin@example.com
Password: admin123
```

## 📊 Sample Data Contents

### Cars (₱1,000 - ₱2,500 per day)
1. **Toyota Innova** - ₱2,500/day (7-seater family SUV)
2. **Honda City** - ₱1,500/day (5-seater economy sedan)
3. **Mitsubishi Xpander** - ₱1,800/day (7-seater MPV)
4. **Hyundai Accent** - ₱1,200/day (5-seater budget sedan)
5. **Suzuki APV** - ₱1,400/day (8-seater van)
6. **Toyota Vios** - ₱1,300/day (5-seater entry sedan)
7. **Nissan Urvan** - ₱2,200/day (15-seater minibus)
8. **Chevrolet Spark** - ₱1,000/day (5-seater ultra-budget)

### Customer Accounts
- Juan Carlos Santos (juan@example.com)
- Maria Grace Silva (maria@example.com)
- Pedro Alfonso (pedro@example.com)
- Rosa Maria Delacruz (rosa@example.com)
- Carlos Antonio (carlos@example.com)
- Angela Louise (angela@example.com)

**All use password: `password123`**

### Booking Statuses in Sample
- **Pending**: Awaiting admin approval
- **Approved**: Admin approved, ready for pickup
- **Completed**: Rental period finished
- **Rejected**: Admin rejected the booking

### Payment Methods
1. Credit Card
2. Debit Card
3. Cash
4. GCash
5. Bank Transfer

## 🧪 What You Can Test

### 1. User Authentication
✅ Login with juan@example.com  
✅ Login with admin@example.com  
✅ Logout functionality  
✅ Session management  

### 2. Booking Workflow
✅ View available cars  
✅ Book a car (create new booking)  
✅ Check date conflicts  
✅ View your bookings  
✅ Edit/cancel bookings  

### 3. Admin Functions
✅ Dashboard overview  
✅ Manage cars (CRUD)  
✅ Approve/reject bookings  
✅ Manage users  
✅ View reports  
✅ Check payment records  

### 4. Reviews & Ratings
✅ View car reviews  
✅ Check ratings (3-5 stars)  
✅ Submit new reviews  
✅ Filter by rating  

### 5. Payment System
✅ Multiple payment methods  
✅ Payment history  
✅ Transaction records  

## 📁 Related Files

| File | Purpose |
|------|---------|
| **seed_complete_data.py** | Adds all sample data to database |
| **verify_sample_data.py** | Checks if data was added correctly |
| **SAMPLE_DATA_GUIDE.md** | Detailed guide with all sample data info |
| **README.md** | Project documentation with setup instructions |

## 🔄 Re-running Sample Data

You can safely run the seeder multiple times without creating duplicates:

```bash
python seed_complete_data.py
```

The script will:
- Skip duplicate entries
- Show what was added
- Provide timestamps for all records

## 🗑️ Clearing Sample Data

To start fresh with a clean database:

```bash
# Remove database file
rm instance/car_rental.db

# Recreate empty database
python
>>> from app import app, db
>>> with app.app_context():
...     db.create_all()
>>> exit()

# Add fresh sample data
python seed_complete_data.py
```

## ⚠️ Important Notes

1. **All passwords are: `password123`** (except admin which is `admin123`)
2. **Sample dates** are set in the future so bookings are realistic
3. **Booking dates don't conflict** in the sample data for testing
4. **Admin has full access** - can approve all bookings
5. **Try-except protection** prevents duplicate errors on re-runs

## 🎯 Testing Scenarios

### Scenario 1: Complete a Booking
1. Login as juan@example.com
2. Browse available cars
3. Create a new booking
4. Admin approves the booking
5. Complete the booking
6. Leave a review

### Scenario 2: Admin Management
1. Login as admin@example.com
2. View dashboard statistics
3. Check pending bookings
4. Approve/reject bookings
5. View payment records
6. Manage car inventory

### Scenario 3: Multi-user Testing
1. Login as different users (maria, pedro, rosa, etc.)
2. Check their respective bookings
3. View personalized booking history
4. Test guest (non-logged-in) features

## 📞 Troubleshooting

### Issue: "Can't login with sample accounts"
**Check**: Did you run `python seed_complete_data.py`?

### Issue: "No cars visible"
**Check**: Verify with `python verify_sample_data.py`

### Issue: "Bookings showing wrong status"
**Check**: Admin might need to approve/update booking status

### Issue: "Can't find payment records"
**Check**: Some sample bookings may not have payment records yet

## 🚀 Next Steps

After verifying the sample data:

1. **Try different user accounts** to test multi-user scenarios
2. **Create new bookings** to test the booking workflow
3. **Use admin dashboard** to manage the system
4. **Leave reviews** on completed bookings
5. **Test responsive design** on different screen sizes
6. **Check API endpoints** if you're testing the backend

## 📚 Additional Resources

- See **README.md** for full setup instructions
- See **SAMPLE_DATA_GUIDE.md** for detailed sample data breakdown
- Run **verify_sample_data.py** to check everything is correct

---

**Last Updated**: 2024  
**Sample Data Version**: 1.0  
**Status**: Ready for Testing ✅
