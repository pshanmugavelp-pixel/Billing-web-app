"""
Database module for Business Management System
Handles all database connections and initialization
"""

import sqlite3

# Database configuration
DATABASE = 'business.db'

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with all required tables"""
    conn = get_db_connection()
    
    # Customers table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT UNIQUE NOT NULL,
            vendor_code TEXT UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            mobile TEXT,
            address TEXT,
            state TEXT,
            gst_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Inventory table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            hsn_code TEXT,
            manufacture_date DATE,
            expiry_month TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_price REAL NOT NULL DEFAULT 0.0,
            mrp REAL NOT NULL DEFAULT 0.0,
            gst_percentage REAL NOT NULL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Billing table (header - one per bill)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            bill_date DATE NOT NULL,
            subtotal REAL DEFAULT 0.0,
            gst_amount REAL DEFAULT 0.0,
            total_amount REAL NOT NULL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Pending',
            payment_method TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Billing items table (line items - multiple per bill)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS billing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL DEFAULT 0.0,
            subtotal REAL NOT NULL DEFAULT 0.0,
            gst_percentage REAL NOT NULL DEFAULT 0.0,
            gst_amount REAL NOT NULL DEFAULT 0.0,
            total REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (bill_id) REFERENCES billing (id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES inventory (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Made with Bob
