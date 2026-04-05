CREATE DATABASE car_rental;
USE car_rental;

CREATE TABLE `user` (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  contact VARCHAR(20),
  password VARCHAR(200) NOT NULL,
  is_admin BOOLEAN DEFAULT FALSE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
  amount_paid DECIMAL(10, 2) NOT NULL,
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