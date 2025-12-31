"""
Admin routes module
Handles all admin and database management routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection, init_db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def index():
    """Admin dashboard for database management"""
    conn = get_db_connection()
    
    # Get table information
    tables_info = {}
    tables = ['customers', 'inventory', 'billing', 'billing_items']
    
    for table in tables:
        try:
            count = conn.execute(f'SELECT COUNT(*) as count FROM {table}').fetchone()['count']
            tables_info[table] = {'exists': True, 'count': count}
        except:
            tables_info[table] = {'exists': False, 'count': 0}
    
    conn.close()
    return render_template('admin/index.html', tables_info=tables_info)

@admin_bp.route('/view-table/<table_name>')
def view_table(table_name):
    """View table data and schema"""
    allowed_tables = ['customers', 'inventory', 'billing', 'billing_items']
    
    if table_name not in allowed_tables:
        flash('Invalid table name!', 'error')
        return redirect(url_for('admin.index'))
    
    conn = get_db_connection()
    
    try:
        # Get table schema
        schema = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        
        # Get table data
        data = conn.execute(f'SELECT * FROM {table_name} LIMIT 100').fetchall()
        
        # Get primary key column name
        pk_column = None
        for col in schema:
            if col['pk']:
                pk_column = col['name']
                break
        
        conn.close()
        return render_template('admin/view_table.html',
                             table_name=table_name,
                             schema=schema,
                             data=data,
                             pk_column=pk_column)
    except Exception as e:
        conn.close()
        flash(f'Error viewing table: {str(e)}', 'error')
        return redirect(url_for('admin.index'))

@admin_bp.route('/delete-rows/<table_name>', methods=['POST'])
def delete_rows(table_name):
    """Delete selected rows from a table"""
    allowed_tables = ['customers', 'inventory', 'billing', 'billing_items']
    
    if table_name not in allowed_tables:
        flash('Invalid table name!', 'error')
        return redirect(url_for('admin.index'))
    
    row_ids = request.form.getlist('row_ids[]')
    
    if not row_ids:
        flash('No rows selected!', 'error')
        return redirect(url_for('admin.view_table', table_name=table_name))
    
    conn = get_db_connection()
    
    try:
        # Get primary key column name
        schema = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
        pk_column = None
        for col in schema:
            if col['pk']:
                pk_column = col['name']
                break
        
        if not pk_column:
            flash('Table has no primary key!', 'error')
            conn.close()
            return redirect(url_for('admin.view_table', table_name=table_name))
        
        # Delete rows
        placeholders = ','.join('?' * len(row_ids))
        conn.execute(f'DELETE FROM {table_name} WHERE {pk_column} IN ({placeholders})', row_ids)
        conn.commit()
        conn.close()
        
        flash(f'{len(row_ids)} row(s) deleted successfully from {table_name}!', 'success')
    except Exception as e:
        conn.close()
        flash(f'Error deleting rows: {str(e)}', 'error')
    
    return redirect(url_for('admin.view_table', table_name=table_name))

@admin_bp.route('/reset-table/<table_name>', methods=['POST'])
def reset_table(table_name):
    """Reset a specific table"""
    allowed_tables = ['customers', 'inventory', 'billing', 'billing_items']
    
    if table_name not in allowed_tables:
        flash('Invalid table name!', 'error')
        return redirect(url_for('admin.index'))
    
    conn = get_db_connection()
    
    try:
        # Drop the table
        conn.execute(f'DROP TABLE IF EXISTS {table_name}')
        conn.commit()
        
        # Recreate the table with new schema
        if table_name == 'customers':
            conn.execute('''
                CREATE TABLE customers (
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
        elif table_name == 'inventory':
            conn.execute('''
                CREATE TABLE inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    hsn_code TEXT,
                    manufacture_date DATE,
                    expiry_month TEXT,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    unit_price REAL NOT NULL DEFAULT 0.0,
                    mrp REAL NOT NULL DEFAULT 0.0,
                    gst_percentage REAL NOT NULL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        elif table_name == 'billing':
            conn.execute('''
                CREATE TABLE billing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    bill_date DATE NOT NULL,
                    total_amount REAL NOT NULL DEFAULT 0.0,
                    payment_status TEXT DEFAULT 'Pending',
                    payment_method TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers (id)
                )
            ''')
        elif table_name == 'billing_items':
            conn.execute('''
                CREATE TABLE billing_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    billing_id INTEGER NOT NULL,
                    item_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    FOREIGN KEY (billing_id) REFERENCES billing (id),
                    FOREIGN KEY (item_id) REFERENCES inventory (id)
                )
            ''')
        
        conn.commit()
        flash(f'Table "{table_name}" has been reset successfully!', 'success')
    except Exception as e:
        flash(f'Error resetting table: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('admin.index'))

@admin_bp.route('/reset-all', methods=['POST'])
def reset_all():
    """Reset all tables"""
    conn = get_db_connection()
    
    try:
        # Drop all tables
        conn.execute('DROP TABLE IF EXISTS billing_items')
        conn.execute('DROP TABLE IF EXISTS billing')
        conn.execute('DROP TABLE IF EXISTS inventory')
        conn.execute('DROP TABLE IF EXISTS customers')
        conn.commit()
        
        # Reinitialize database
        conn.close()
        init_db()
        
        flash('All tables have been reset successfully!', 'success')
    except Exception as e:
        flash(f'Error resetting tables: {str(e)}', 'error')
        conn.close()
    
    return redirect(url_for('admin.index'))

# Made with Bob
