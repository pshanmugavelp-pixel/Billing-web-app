"""
Customer routes module
Handles all customer-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from database import get_db_connection

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
def index():
    """Display all customers with optional search"""
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    
    if search_query:
        # Search by customer_id, vendor_code, or name
        customers = conn.execute('''
            SELECT * FROM customers
            WHERE customer_id LIKE ? OR vendor_code LIKE ? OR name LIKE ?
            ORDER BY created_at DESC
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')).fetchall()
    else:
        customers = conn.execute('SELECT * FROM customers ORDER BY created_at DESC').fetchall()
    
    conn.close()
    return render_template('customers/index.html', customers=customers, search_query=search_query)

@customers_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new customer"""
    if request.method == 'POST':
        customer_id = request.form.get('customer_id', '').strip()
        vendor_code = request.form.get('vendor_code', '').strip()
        # treat empty vendor_code as NULL so UNIQUE constraint isn't violated by empty strings
        vendor_code = vendor_code if vendor_code != '' else None
        name = request.form['name']
        email = request.form.get('email', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')
        state = request.form.get('state', '')
        gst_number = request.form.get('gst_number', '')
        
        # If customer_id not provided for some reason, auto-generate one
        if not customer_id:
            conn = get_db_connection()
            row = conn.execute('SELECT MAX(id) FROM customers').fetchone()
            max_id = row[0] if row and row[0] else 0
            customer_id = f"CUST{str(max_id+1).zfill(4)}"
            conn.close()

        # Validate required fields (customer_id, name, address and state)
        if not customer_id or not name or not address or not state:
            flash('Customer ID, Customer Name, Address and State are required!', 'error')
            return redirect(url_for('customers.add'))
        
        # Check if customer_id already exists
        conn = get_db_connection()
        existing_cid = conn.execute('SELECT id FROM customers WHERE customer_id = ?', (customer_id,)).fetchone()
        
        if existing_cid:
            conn.close()
            flash('Customer ID already exists! Please use a unique ID.', 'error')
            return redirect(url_for('customers.add'))
        
        # Check if vendor code already exists (only if provided)
        if vendor_code:
            existing_vcode = conn.execute('SELECT id FROM customers WHERE vendor_code = ?', (vendor_code,)).fetchone()
            if existing_vcode:
                conn.close()
                flash('Vendor Code already exists! Please use a unique code.', 'error')
                return redirect(url_for('customers.add'))
        
        try:
            conn.execute('''INSERT INTO customers (customer_id, vendor_code, name, email, mobile, address, state, gst_number)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (customer_id, vendor_code, name, email, mobile, address, state, gst_number))
            conn.commit()
            conn.close()
            
            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            conn.close()
            flash(f'Error adding customer: {str(e)}', 'error')
            return redirect(url_for('customers.add'))
    
    # For GET: generate a suggested customer_id and render form
    conn = get_db_connection()
    row = conn.execute('SELECT MAX(id) FROM customers').fetchone()
    max_id = row[0] if row and row[0] else 0
    suggested_cid = f"CUST{str(max_id+1).zfill(4)}"
    conn.close()
    return render_template('customers/add.html', customer_id=suggested_cid)

@customers_bp.route('/update/<int:customer_id>', methods=['GET', 'POST'])
def update(customer_id):
    """Update a customer"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_customer_id = request.form['customer_id'].strip()
        vendor_code = request.form.get('vendor_code', '').strip()
        vendor_code = vendor_code if vendor_code != '' else None
        name = request.form['name']
        email = request.form.get('email', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')
        state = request.form.get('state', '')
        gst_number = request.form.get('gst_number', '')
        try:
            conn.execute('''INSERT INTO customers (customer_id, vendor_code, name, email, mobile, address, state, gst_number)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (customer_id, vendor_code, name, email, mobile, address, state, gst_number))
            conn.commit()
            conn.close()
            
            flash('Customer added successfully!', 'success')
            return redirect(url_for('customers.index'))
        except sqlite3.IntegrityError as e:
            conn.close()
            msg = str(e)
            if 'vendor_code' in msg:
                flash('Vendor Code must be unique. Please provide a different Vendor Code or leave it blank.', 'error')
            elif 'customer_id' in msg:
                flash('Customer ID already exists. Please use a unique Customer ID.', 'error')
            else:
                flash(f'Database integrity error: {msg}', 'error')
            return redirect(url_for('customers.add'))
        except Exception as e:
            conn.close()
            flash(f'Error adding customer: {str(e)}', 'error')
            return redirect(url_for('customers.add'))
            return redirect(url_for('customers.update', customer_id=customer_id))
        
        # Check if vendor code already exists (excluding current customer, only if provided)
        if vendor_code:
            existing_vcode = conn.execute('SELECT id FROM customers WHERE vendor_code = ? AND id != ?',
                                         (vendor_code, customer_id)).fetchone()
            if existing_vcode:
                conn.close()
                flash('Vendor Code already exists! Please use a unique code.', 'error')
                return redirect(url_for('customers.update', customer_id=customer_id))
        
        try:
            conn.execute('''UPDATE customers
                           SET customer_id = ?, vendor_code = ?, name = ?, email = ?,
                               mobile = ?, address = ?, state = ?, gst_number = ?
                           WHERE id = ?''',
                        (new_customer_id, vendor_code, name, email, mobile, address, state, gst_number, customer_id))
            conn.commit()
            conn.close()
            
            flash('Customer updated successfully!', 'success')
            return redirect(url_for('customers.index'))
        except Exception as e:
            conn.close()
            flash(f'Error updating customer: {str(e)}', 'error')
            return redirect(url_for('customers.update', customer_id=customer_id))
    
    # GET request - show update form
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    
    if not customer:
        flash('Customer not found!', 'error')
        return redirect(url_for('customers.index'))
    
    return render_template('customers/update.html', customer=customer)

@customers_bp.route('/delete/<int:id>')
def delete(id):
    """Delete a customer by ID"""
    conn = get_db_connection()
    conn.execute('DELETE FROM customers WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers.index'))

@customers_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple customers"""
    customer_ids = request.form.getlist('customer_ids[]')
    
    if not customer_ids:
        flash('No customers selected!', 'error')
        return redirect(url_for('customers.index'))
    
    conn = get_db_connection()
    placeholders = ','.join('?' * len(customer_ids))
    conn.execute(f'DELETE FROM customers WHERE id IN ({placeholders})', customer_ids)
    conn.commit()
    conn.close()
    
    flash(f'{len(customer_ids)} customer(s) deleted successfully!', 'success')
    return redirect(url_for('customers.index'))


@customers_bp.route('/check-vendor', methods=['POST'])
def check_vendor():
    """AJAX endpoint: check if vendor_code already exists"""
    # Accept JSON or form data
    if request.is_json:
        data = request.get_json()
        vendor_code = data.get('vendor_code')
    else:
        vendor_code = request.form.get('vendor_code')

    if not vendor_code:
        return jsonify({'exists': False})

    conn = get_db_connection()
    existing = conn.execute('SELECT id FROM customers WHERE vendor_code = ?', (vendor_code,)).fetchone()
    conn.close()

    return jsonify({'exists': bool(existing)})

# Made with Bob
