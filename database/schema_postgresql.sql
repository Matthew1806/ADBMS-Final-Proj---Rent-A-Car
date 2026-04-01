-- Create database first (run as superuser if needed)
-- CREATE DATABASE car_rental;
-- Then connect to the database: \c car_rental

-- ===============================================
-- USER TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS "user" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password VARCHAR(200) NOT NULL,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================================
-- CAR TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS car (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  price VARCHAR(50) NOT NULL,
  specs VARCHAR(200) NOT NULL,
  image VARCHAR(100) NOT NULL,
  transmission VARCHAR(50) NOT NULL,
  fuel VARCHAR(50) NOT NULL,
  capacity VARCHAR(50) NOT NULL,
  availability VARCHAR(20) DEFAULT 'Available',
  engine VARCHAR(100),
  mileage VARCHAR(50),
  color VARCHAR(50)
);

-- ===============================================
-- PAYMENT_METHOD TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS payment_method (
  id SERIAL PRIMARY KEY,
  method_name VARCHAR(50) NOT NULL
);

-- ===============================================
-- BOOKING TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS booking (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  contact VARCHAR(20) NOT NULL,
  car_id INT NOT NULL,
  pickup_date DATE NOT NULL,
  return_date DATE NOT NULL,
  id_file VARCHAR(200),
  license_file VARCHAR(200),
  notes TEXT,
  status VARCHAR(20) DEFAULT 'Pending',
  payment_method VARCHAR(50),
  payment_status VARCHAR(20) DEFAULT 'Unpaid',
  submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
  FOREIGN KEY (car_id) REFERENCES car(id) ON DELETE CASCADE
);

-- ===============================================
-- PAYMENT TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS payment (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL,
  booking_id INT NOT NULL,
  payment_method_id INT NOT NULL,
  amount_paid DECIMAL(10, 2) NOT NULL,
  date_paid VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
  FOREIGN KEY (booking_id) REFERENCES booking(id) ON DELETE CASCADE,
  FOREIGN KEY (payment_method_id) REFERENCES payment_method(id) ON DELETE CASCADE
);

-- ===============================================
-- REVIEW TABLE
-- ===============================================
CREATE TABLE IF NOT EXISTS review (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL,
  car_id INT NOT NULL,
  booking_id INT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
  FOREIGN KEY (car_id) REFERENCES car(id) ON DELETE CASCADE,
  FOREIGN KEY (booking_id) REFERENCES booking(id) ON DELETE CASCADE
);

-- ===============================================
-- INDEXES for better query performance
-- ===============================================
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);
CREATE INDEX IF NOT EXISTS idx_booking_user_id ON booking(user_id);
CREATE INDEX IF NOT EXISTS idx_booking_car_id ON booking(car_id);
CREATE INDEX IF NOT EXISTS idx_payment_user_id ON payment(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_booking_id ON payment(booking_id);
CREATE INDEX IF NOT EXISTS idx_review_user_id ON review(user_id);
CREATE INDEX IF NOT EXISTS idx_review_car_id ON review(car_id);
CREATE INDEX IF NOT EXISTS idx_review_booking_id ON review(booking_id);

-- ===============================================
-- DONE! PostgreSQL schema created successfully
-- ===============================================
