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
            buy_price REAL NOT NULL DEFAULT 0.0,
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
            bill_id TEXT UNIQUE NOT NULL,
            customer_id INTEGER NOT NULL,
            bill_date DATE NOT NULL,
            subtotal REAL DEFAULT 0.0,
            gst_amount REAL DEFAULT 0.0,
            round_off REAL DEFAULT 0.0,
            total_amount REAL NOT NULL DEFAULT 0.0,
            payment_status TEXT DEFAULT 'Pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers (id)
        )
    ''')
    
    # Billing items table (line items - multiple per bill)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS billing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            hsn_code TEXT,
            quantity INTEGER NOT NULL DEFAULT 1,
            unit_price REAL NOT NULL DEFAULT 0.0,
            gst_percentage REAL NOT NULL DEFAULT 0.0,
            gst_amount REAL NOT NULL DEFAULT 0.0,
            cgst REAL NOT NULL DEFAULT 0.0,
            sgst REAL NOT NULL DEFAULT 0.0,
            igst REAL NOT NULL DEFAULT 0.0,
            total REAL NOT NULL DEFAULT 0.0,
            FOREIGN KEY (bill_id) REFERENCES billing (bill_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES inventory (id)
        )
    ''')
    
    # Seller information table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS seller_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_name TEXT NOT NULL,
            address TEXT,
            email TEXT,
            mobile TEXT,
            state TEXT,
            gst_number TEXT,
            account_name TEXT,
            account_number TEXT,
            ifsc_code TEXT,
            account_type TEXT,
            branch TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default seller info if table is empty
    existing_seller = conn.execute('SELECT COUNT(*) as count FROM seller_info').fetchone()
    if existing_seller['count'] == 0:
        conn.execute('''INSERT INTO seller_info (seller_name, address, email, mobile, gst_number,
                        account_name, account_number, ifsc_code, account_type, branch)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    ('Your Company Name', 'Your Address', 'email@example.com', '1234567890', 'GST123456',
                     'Account Holder Name', '1234567890', 'IFSC0001234', 'Savings', 'Main Branch'))
        conn.commit()
    
    # Purchase table - tracks all purchases/stock additions
    conn.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            hsn_code TEXT,
            manufacture_date DATE,
            expiry_month TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            buy_price REAL NOT NULL DEFAULT 0.0,
            unit_price REAL NOT NULL DEFAULT 0.0,
            mrp REAL NOT NULL DEFAULT 0.0,
            gst_percentage REAL NOT NULL DEFAULT 0.0,
            purchase_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES inventory (product_id)
        )
    ''')
    
    conn.commit()
    conn.close()

