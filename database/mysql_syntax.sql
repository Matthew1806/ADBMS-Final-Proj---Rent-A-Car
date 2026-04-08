CREATE DATABASE IF NOT EXISTS car_rental;
USE car_rental;

CREATE TABLE `user` (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  firebase_uid VARCHAR(128) UNIQUE,
  profile_picture VARCHAR(255),
  contact VARCHAR(20),
  password VARCHAR(200) NOT NULL,
  email_verified BOOLEAN NOT NULL DEFAULT FALSE,
  email_verified_at DATETIME,
  otp VARCHAR(6),
  otp_expires_at DATETIME,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at DATETIME
);

CREATE TABLE car (
  id INT AUTO_INCREMENT PRIMARY KEY,
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

CREATE TABLE payment_method (
  id INT AUTO_INCREMENT PRIMARY KEY,
  method_name VARCHAR(50) NOT NULL
);

CREATE TABLE booking (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  contact VARCHAR(20) NOT NULL,
  pickup_area VARCHAR(100),
  car_id INT NOT NULL,
  pickup_date DATE NOT NULL,
  return_date DATE NOT NULL,
  id_file VARCHAR(200),
  license_file VARCHAR(200),
  notes TEXT,
  status VARCHAR(20) DEFAULT 'Pending',
  payment_method VARCHAR(50),
  payment_status VARCHAR(20) DEFAULT 'Unpaid',
  submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(id),
  FOREIGN KEY (car_id) REFERENCES car(id)
);

CREATE TABLE payment (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  booking_id INT NOT NULL,
  payment_method_id INT NOT NULL,
  amount_paid INT NOT NULL,
  date_paid VARCHAR(50),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(id),
  FOREIGN KEY (booking_id) REFERENCES booking(id),
  FOREIGN KEY (payment_method_id) REFERENCES payment_method(id)
);

CREATE TABLE review (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  car_id INT NOT NULL,
  booking_id INT NOT NULL,
  rating INT NOT NULL,
  comment TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(id),
  FOREIGN KEY (car_id) REFERENCES car(id),
  FOREIGN KEY (booking_id) REFERENCES booking(id)
);

CREATE TABLE support_concern (
  id INT AUTO_INCREMENT PRIMARY KEY,
  thread_root_id INT NULL,
  user_id INT NULL,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(120) NOT NULL,
  subject VARCHAR(160) NOT NULL,
  message TEXT NOT NULL,
  admin_reply TEXT NULL,
  admin_replied_at DATETIME NULL,
  replied_by_admin_id INT NULL,
  admin_has_seen_message BOOLEAN NOT NULL DEFAULT FALSE,
  user_has_seen_reply BOOLEAN NOT NULL DEFAULT FALSE,
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  archived_at DATETIME NULL,
  archived_by_admin_id INT NULL,
  is_user_archived BOOLEAN NOT NULL DEFAULT FALSE,
  user_archived_at DATETIME NULL,
  is_user_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  user_deleted_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES `user`(id),
  FOREIGN KEY (replied_by_admin_id) REFERENCES `user`(id),
  FOREIGN KEY (archived_by_admin_id) REFERENCES `user`(id)
);

-- Promote specific account to admin after the user exists.
UPDATE user
SET is_admin = 1
WHERE email = 'admin@rentacar.com';