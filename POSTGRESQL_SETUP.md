# PostgreSQL Setup Guide for RentACar Website

This guide walks you through setting up PostgreSQL for the RentACar Website project step by step.

---

## Table of Contents
1. [Install PostgreSQL](#install-postgresql)
2. [Create Database and User](#create-database-and-user)
3. [Initialize Database Schema](#initialize-database-schema)
4. [Update Python Dependencies](#update-python-dependencies)
5. [Verify Database Connection](#verify-database-connection)
6. [Troubleshooting](#troubleshooting)

---

## 1. Install PostgreSQL

### Option A: Windows (Using Official Installer)

1. Visit [PostgreSQL Official Website](https://www.postgresql.org/download/windows/)
2. Download the latest PostgreSQL installer (Version 14 or higher recommended)
3. Run the installer and follow these steps:
   - **Installation Directory**: Leave as default (C:\Program Files\PostgreSQL\15)
   - **Components**: Keep all checked (Server, pgAdmin 4, Command Line Tools)
   - **Password**: Set a password for the `postgres` user (e.g., `password`)
   - **Port**: Keep as default (5432)
   - **Locale**: Keep as default

4. Complete installation
5. PostgreSQL service should start automatically

### Option B: Windows (Using Chocolatey)

```powershell
choco install postgresql
```

### Verify Installation

Open PowerShell and test:
```powershell
psql --version
```

---

## 2. Create Database and User

### Step 1: Open PostgreSQL Command Line

**Windows**: Open "SQL Shell (psql)" from Start Menu or run in PowerShell:
```powershell
psql -U postgres
```

When prompted for password, enter the password you set during installation.

### Step 2: Create the Database

```sql
CREATE DATABASE car_rental;
```

Expected output: `CREATE DATABASE`

### Step 3: Create a User (Optional but Recommended)

```sql
CREATE USER car_user WITH PASSWORD 'secure_password';
```

Replace `secure_password` with a strong password of your choice.

### Step 4: Grant Privileges

```sql
GRANT ALL PRIVILEGES ON DATABASE car_rental TO car_user;
```

### Step 5: Exit psql

```sql
\q
```

---

## 3. Initialize Database Schema

### Option A: Using SQL File (Recommended)

1. Open PowerShell in your project directory:
```powershell
cd "d:\Users\EDMAR CUDALA\2nd Year\2ND YEAR - 2nd Sem\AdvDatabase\FINAL PROJECT\RentACar_Website\RentACar_Website"
```

2. Create the tables using the PostgreSQL schema file:
```powershell
psql -U postgres -d car_rental -f database/schema_postgresql.sql
```

3. Enter password when prompted

Expected output: Multiple `CREATE TABLE` and `CREATE INDEX` statements completed.

### Option B: Manual SQL Execution

1. Open SQL Shell (psql):
```powershell
psql -U postgres
```

2. Connect to the database:
```sql
\c car_rental
```

3. Copy all content from `database/schema_postgresql.sql` file
4. Paste and execute in the psql terminal
5. Verify tables were created:
```sql
\dt
```

You should see all tables listed: user, car, payment_method, booking, payment, review

---

## 4. Update Python Dependencies

### Step 1: Navigate to Project Directory

```powershell
cd "d:\Users\EDMAR CUDALA\2nd Year\2ND YEAR - 2nd Sem\AdvDatabase\FINAL PROJECT\RentACar_Website\RentACar_Website"
```

### Step 2: Create Virtual Environment (Recommended)

```powershell
python -m venv venv
```

Activate it:
```powershell
.\venv\Scripts\Activate.ps1
```

### Step 3: Upgrade pip

```powershell
python -m pip install --upgrade pip
```

### Step 4: Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install `psycopg2-binary` (PostgreSQL driver for Python) and all other required packages.

### Verify Installation

```powershell
python -c "import psycopg2; print('psycopg2 installed successfully')"
```

---

## 5. Update Configuration in app.py

The app.py has already been updated with PostgreSQL configuration. Verify the database URI:

**Current setting (default credentials):**
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost:5432/car_rental'
```

**If you created a custom user** (e.g., `car_user`), change it to:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://car_user:secure_password@localhost:5432/car_rental'
```

Replace:
- `car_user` with your username
- `secure_password` with your password

---

## 6. Verify Database Connection

### Option A: Test with Python Script

Create a test file `test_db.py`:

```python
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@localhost:5432/car_rental'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

try:
    with app.app_context():
        result = db.session.execute("SELECT 1")
        print("✓ Database connection successful!")
except Exception as e:
    print(f"✗ Connection failed: {e}")
```

Run it:
```powershell
python test_db.py
```

### Option B: Test with psql Command Line

```powershell
psql -U postgres -d car_rental -c "SELECT COUNT(*) FROM car;"
```

If successful, you should see a count (initially 0 if no data added yet).

---

## 7. Load Sample Data (Optional)

Once the schema is created, you can populate sample data:

```powershell
python seed_complete_data.py
```

This will add:
- 8 cars
- 7 users
- 8 bookings
- 7 reviews
- 5 payment methods
- 5 payments

---

## Running the Application

```powershell
python app.py
```

Access it at: `http://localhost:5000`

---

## Troubleshooting

### Connection Error: `could not translate host name "localhost" to address`

**Solution**: PostgreSQL service might not be running.

Windows:
```powershell
# Check if service is running
Get-Service PostgreSQL*

# If not running, start it
Start-Service PostgreSQL14
```

### Error: `password authentication failed for user "postgres"`

**Cause**: Wrong password entered
**Solution**: 
1. Reset password using pgAdmin 4 GUI, OR
2. Reinstall PostgreSQL with correct password

### Error: `FATAL: role "postgres" does not exist`

**Solution**: PostgreSQL installation incomplete. Reinstall PostgreSQL.

### Error: `role "car_user" does not exist`

**Solution**: You haven't created the `car_user` yet. Follow Step 2 of this guide.

### Port 5432 Already in Busy

**Cause**: Another PostgreSQL instance is running
**Solution**:
```powershell
# Find process using port 5432
netstat -ano | findstr :5432

# Kill the process (replace PID with actual number)
taskkill /PID <PID> /F

# Or change PostgreSQL port during installation
```

### Permission Denied on schema_postgresql.sql

**Solution**: 
```powershell
# Use full file path
psql -U postgres -d car_rental -f "database/schema_postgresql.sql"

# Or copy file content and paste directly in psql
```

---

## Common PostgreSQL Commands

### Connect to Database
```sql
psql -U postgres -d car_rental
```

### List All Databases
```sql
\l
```

### List All Tables
```sql
\dt
```

### View Table Structure
```sql
\d table_name
```

### Run SQL File
```sql
\i path/to/file.sql
```

### Exit psql
```sql
\q
```

---

## Next Steps

1. ✅ Install PostgreSQL
2. ✅ Create database and user
3. ✅ Initialize schema
4. ✅ Update Python dependencies
5. ✅ Run the Flask application
6. ✅ Test with sample data (optional)

Your RentACar Website is now ready with PostgreSQL!

---

## Useful Resources

- [PostgreSQL Official Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy PostgreSQL Dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [psycopg2 Documentation](https://www.psycopg.org/psycopg2/docs/)
