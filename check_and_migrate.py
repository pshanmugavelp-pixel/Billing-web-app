import sqlite3

# Connect to database
conn = sqlite3.connect('business.db')
cursor = conn.cursor()

print("Checking current database structure...\n")

# Check billing_items table structure
print("=== billing_items table columns ===")
cursor.execute("PRAGMA table_info(billing_items)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

has_hsn = any(col[1] == 'hsn_code' for col in columns)
print(f"\nHSN code column exists: {has_hsn}")

# Check billing table structure
print("\n=== billing table columns ===")
cursor.execute("PRAGMA table_info(billing)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

has_roundoff = any(col[1] == 'round_off' for col in columns)
print(f"\nRound off column exists: {has_roundoff}")

print("\n" + "="*50)
print("Starting migration...\n")

# Add hsn_code if missing
if not has_hsn:
    try:
        print("Adding hsn_code column to billing_items...")
        cursor.execute('ALTER TABLE billing_items ADD COLUMN hsn_code TEXT')
        conn.commit()
        print("✓ hsn_code column added successfully")
    except Exception as e:
        print(f"✗ Error adding hsn_code: {e}")
else:
    print("✓ hsn_code column already exists")

# Add round_off if missing
if not has_roundoff:
    try:
        print("Adding round_off column to billing...")
        cursor.execute('ALTER TABLE billing ADD COLUMN round_off REAL DEFAULT 0.0')
        conn.commit()
        print("✓ round_off column added successfully")
    except Exception as e:
        print(f"✗ Error adding round_off: {e}")
else:
    print("✓ round_off column already exists")

print("\n" + "="*50)
print("Verifying final structure...\n")

# Verify billing_items
print("=== billing_items final columns ===")
cursor.execute("PRAGMA table_info(billing_items)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

# Verify billing
print("\n=== billing final columns ===")
cursor.execute("PRAGMA table_info(billing)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
print("\nMigration completed!")

# Made with Bob
