import sqlite3

# Connect to database
conn = sqlite3.connect('business.db')
cursor = conn.cursor()

try:
    # Add hsn_code column to billing_items
    print("Adding hsn_code column to billing_items...")
    cursor.execute('ALTER TABLE billing_items ADD COLUMN hsn_code TEXT')
    print("✓ hsn_code column added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("✓ hsn_code column already exists")
    else:
        print(f"✗ Error adding hsn_code: {e}")

try:
    # Add round_off column to billing
    print("Adding round_off column to billing...")
    cursor.execute('ALTER TABLE billing ADD COLUMN round_off REAL DEFAULT 0.0')
    print("✓ round_off column added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e).lower():
        print("✓ round_off column already exists")
    else:
        print(f"✗ Error adding round_off: {e}")

conn.commit()
conn.close()
print("\nDatabase migration completed!")

# Made with Bob
