CREATE DATABASE bank_management;
USE bank_management;

CREATE TABLE customer_users (user_id VARCHAR(50) PRIMARY KEY,password VARCHAR(255) NOT NULL,full_name VARCHAR(100) NOT NULL,email VARCHAR(100) NOT NULL UNIQUE,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
select * from customer_users;

CREATE TABLE staff_users (staff_id VARCHAR(50) PRIMARY KEY,password VARCHAR(255) NOT NULL,full_name VARCHAR(100) NOT NULL,email VARCHAR(100) NOT NULL UNIQUE,role VARCHAR(50) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
select * from staff_users;

CREATE TABLE accounts (
    account_no BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    account_type ENUM('Savings', 'Current', 'Fixed Deposit') NOT NULL,
    balance DECIMAL(12,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES customer_users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE transactions (
    txn_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_no BIGINT,
    txn_type ENUM('Deposit', 'Withdrawal', 'Transfer', 'Loan EMI') NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2),
    related_account BIGINT NULL,
    remarks VARCHAR(200),
    txn_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_no) REFERENCES accounts(account_no)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE loan_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50),
    loan_type ENUM('Home Loan', 'Education Loan', 'Personal Loan', 'Car Loan') NOT NULL,
    principal_amount DECIMAL(12,2) NOT NULL,
    interest_rate DECIMAL(5,2),
    tenure_months INT NOT NULL,
    status ENUM('Pending', 'Approved', 'Rejected') DEFAULT 'Pending',
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(50) NULL,
    reviewed_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES customer_users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES staff_users(staff_id)
        ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE loans (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT,
    user_id VARCHAR(50),
    loan_type VARCHAR(50),
    principal_amount DECIMAL(12,2),
    interest_rate DECIMAL(5,2),
    tenure_months INT,
    emi_amount DECIMAL(12,2),
    start_date DATE,
    end_date DATE,
    status ENUM('Active', 'Closed') DEFAULT 'Active',
    FOREIGN KEY (request_id) REFERENCES loan_requests(request_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (user_id) REFERENCES customer_users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE fixed_deposits (
    fd_id INT AUTO_INCREMENT PRIMARY KEY,
    account_no INT,
    principal DECIMAL(12,2),
    tenure_months INT,
    interest_rate DECIMAL(5,2),
    maturity_date DATE,
    maturity_amount DECIMAL(12,2),
    FOREIGN KEY (account_no) REFERENCES accounts(account_no)
);
ALTER TABLE transactions 
MODIFY account_no BIGINT UNSIGNED NOT NULL;

ALTER TABLE accounts 
MODIFY account_no BIGINT UNSIGNED NOT NULL AUTO_INCREMENT;

ALTER TABLE transactions 
ADD CONSTRAINT transactions_ibfk_1 
FOREIGN KEY (account_no) REFERENCES accounts(account_no)
    ON DELETE CASCADE ON UPDATE CASCADE;

CREATE TABLE fixed_deposits (
    fd_id INT AUTO_INCREMENT PRIMARY KEY,
    account_no BIGINT UNSIGNED NOT NULL,
    principal DECIMAL(12,2) NOT NULL,
    tenure_months INT NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL DEFAULT 6.0,
    maturity_date DATE NOT NULL,
    maturity_amount DECIMAL(12,2) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_no) REFERENCES accounts(account_no)
        ON DELETE CASCADE ON UPDATE CASCADE
);

ALTER TABLE accounts 
ADD COLUMN aadhaar VARCHAR(12),
ADD COLUMN pan VARCHAR(10),
ADD COLUMN address TEXT,
ADD COLUMN status ENUM('Active', 'Dormant', 'Closed') DEFAULT 'Active';

CREATE TABLE contact_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    account_no VARCHAR(20) NULL,                  
    subject VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
