CREATE DATABASE IF NOT EXISTS natureflex;

USE natureflex;

-- =========================
-- USERS
-- =========================

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,

    name VARCHAR(100) NOT NULL,

    email VARCHAR(150) NOT NULL UNIQUE,

    password_hash VARCHAR(255) NOT NULL,

    height DECIMAL(5,2),

    weight DECIMAL(5,2),

    seeds INT DEFAULT 0,

    trees INT DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- =========================
-- DAILY ACTIVITY
-- =========================

CREATE TABLE IF NOT EXISTS activity (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    steps INT DEFAULT 0,

    seeds_earned INT DEFAULT 0,

    activity_date DATE NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE KEY unique_user_date (user_id, activity_date),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);


-- =========================
-- REWARDS
-- =========================

CREATE TABLE IF NOT EXISTS rewards (
    id INT AUTO_INCREMENT PRIMARY KEY,

    user_id INT NOT NULL,

    reward_name VARCHAR(150) NOT NULL,

    status VARCHAR(30) DEFAULT 'unlocked',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);