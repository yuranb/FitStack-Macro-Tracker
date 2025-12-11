-- FitStack Macro Tracker - Database Schema
-- Database design for nutrition tracking app

-- Main tables:
-- products: stores food/supplement nutrition info
-- daily_logs: what user ate each day (links to products via foreign key)
-- user_goals: daily nutrition targets

-- Products table - all nutrition values are per 100g/100ml
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    calories DECIMAL(8,2) NOT NULL DEFAULT 0,
    protein DECIMAL(8,2) NOT NULL DEFAULT 0,
    carbs DECIMAL(8,2) NOT NULL DEFAULT 0,
    fat DECIMAL(8,2) NOT NULL DEFAULT 0,
    serving_unit VARCHAR(20) NOT NULL DEFAULT 'g',  -- g, ml, piece, scoop, etc
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Daily logs - records what user ate
-- Using foreign key to link to products table
CREATE TABLE daily_logs (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity DECIMAL(8,2) NOT NULL DEFAULT 100,
    log_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User goals table
CREATE TABLE user_goals (
    id SERIAL PRIMARY KEY,
    daily_calories INTEGER NOT NULL DEFAULT 2500,  -- my current TDEE
    daily_protein INTEGER NOT NULL DEFAULT 150,
    daily_carbs INTEGER NOT NULL DEFAULT 250,
    daily_fat INTEGER NOT NULL DEFAULT 80,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better query performance
-- Need these because we'll be querying by date a lot
CREATE INDEX idx_daily_logs_date ON daily_logs(log_date);
CREATE INDEX idx_daily_logs_product ON daily_logs(product_id);

-- ============================================
-- Seed Data
-- ============================================

-- Default goals (based on my own targets)
INSERT INTO user_goals (daily_calories, daily_protein, daily_carbs, daily_fat) 
VALUES (2500, 150, 250, 80);

-- Food data - collected from USDA database and nutrition websites
-- All values per 100g unless unit is ml
INSERT INTO products (name, calories, protein, carbs, fat, serving_unit) VALUES

-- Meats
('Chicken Breast', 165, 31, 0, 3.6, 'g'),
('Lean Beef', 250, 26, 0, 15, 'g'),
('Pork Tenderloin', 143, 21, 0, 6, 'g'),
('Salmon', 208, 20, 0, 13, 'g'),
('Shrimp', 99, 24, 0, 0.3, 'g'),

-- Eggs & Dairy
('Whole Egg', 155, 13, 1.1, 11, 'g'),
('Egg White', 52, 11, 0.7, 0.2, 'g'),
('Whole Milk', 61, 3.2, 4.8, 3.3, 'ml'),
('Greek Yogurt', 97, 9, 3.6, 5, 'g'),

-- Grains & Starches
('Cooked White Rice', 130, 2.7, 28, 0.3, 'g'),
('Oats', 389, 17, 66, 7, 'g'),
('Whole Wheat Bread', 247, 13, 41, 3.4, 'g'),
('Sweet Potato', 86, 1.6, 20, 0.1, 'g'),

-- Vegetables
('Broccoli', 34, 2.8, 7, 0.4, 'g'),
('Spinach', 23, 2.9, 3.6, 0.4, 'g'),
('Cucumber', 15, 0.7, 3.6, 0.1, 'g'),

-- Supplements (what I use)
('Whey Protein Powder', 400, 80, 8, 4, 'g'),
('Creatine', 0, 0, 0, 0, 'g'),
('BCAA', 0, 0, 0, 0, 'g'),

-- Nuts
('Almonds', 579, 21, 22, 50, 'g'),
('Peanut Butter', 588, 25, 20, 50, 'g'),

-- Fruits
('Banana', 89, 1.1, 23, 0.3, 'g'),
('Apple', 52, 0.3, 14, 0.2, 'g'),
('Blueberry', 57, 0.7, 14, 0.3, 'g');
