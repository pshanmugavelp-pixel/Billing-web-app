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
    
    # Add buy_price column to existing inventory table if it doesn't exist
    try:
        conn.execute('SELECT buy_price FROM inventory LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it with default value 0.0
        conn.execute('ALTER TABLE inventory ADD COLUMN buy_price REAL NOT NULL DEFAULT 0.0')
        conn.commit()
    
    # Billing table (header - one per bill)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id TEXT UNIQUE NOT NULL,
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
    
    # Add bill_id column to existing billing table if it doesn't exist
    try:
        conn.execute('SELECT bill_id FROM billing LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        conn.execute('ALTER TABLE billing ADD COLUMN bill_id TEXT')
        # Generate bill_ids for existing records
        existing_bills = conn.execute('SELECT id FROM billing ORDER BY id').fetchall()
        for idx, bill in enumerate(existing_bills, start=1):
            bill_id = f'ST{idx}'
            conn.execute('UPDATE billing SET bill_id = ? WHERE id = ?', (bill_id, bill['id']))
        # Make bill_id unique after populating
        conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_bill_id ON billing(bill_id)
        ''')
        conn.commit()
    
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
