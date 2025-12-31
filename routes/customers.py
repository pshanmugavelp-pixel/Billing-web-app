"""
Customer routes module
Handles all customer-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
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
        customer_id = request.form['customer_id'].strip()
        vendor_code = request.form.get('vendor_code', '').strip()
        name = request.form['name']
        email = request.form.get('email', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')
        state = request.form.get('state', '')
        gst_number = request.form.get('gst_number', '')
        
        # Validate required fields (customer_id and name only)
        if not customer_id or not name:
            flash('Customer ID and Customer Name are required!', 'error')
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
    
    return render_template('customers/add.html')

@customers_bp.route('/update/<int:customer_id>', methods=['GET', 'POST'])
def update(customer_id):
    """Update a customer"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_customer_id = request.form['customer_id'].strip()
        vendor_code = request.form.get('vendor_code', '').strip()
        name = request.form['name']
        email = request.form.get('email', '')
        mobile = request.form.get('mobile', '')
        address = request.form.get('address', '')
        state = request.form.get('state', '')
        gst_number = request.form.get('gst_number', '')
        
        # Validate required fields
        if not new_customer_id or not name:
            flash('Customer ID and Customer Name are required!', 'error')
            conn.close()
            return redirect(url_for('customers.update', customer_id=customer_id))
        
        # Check if new customer_id already exists (excluding current customer)
        existing_cid = conn.execute('SELECT id FROM customers WHERE customer_id = ? AND id != ?',
                                   (new_customer_id, customer_id)).fetchone()
        if existing_cid:
            conn.close()
            flash('Customer ID already exists! Please use a unique ID.', 'error')
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

# Made with Bob
