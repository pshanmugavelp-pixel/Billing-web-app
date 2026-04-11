"""
Customer routes module
Handles all customer-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
import sqlite3
from database import db_connection

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
def index():
    """Display all customers with optional search - no pagination"""
    search_query = request.args.get('search', '').strip()
    
    with db_connection() as conn:
        if search_query:
            # Get all matching customers
            customers = conn.execute('''
                SELECT * FROM customers
                WHERE customer_id LIKE ? OR vendor_code LIKE ? OR name LIKE ?
                ORDER BY created_at DESC
            ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%')).fetchall()
        else:
            # Get all customers
            customers = conn.execute('''
                SELECT * FROM customers
                ORDER BY created_at DESC
            ''').fetchall()
    
    total_count = len(customers)
    
    return render_template('customers/index.html',
                         customers=customers,
                         search_query=search_query,
                         total_count=total_count)

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
        gst_number = gst_number.strip().upper()
        
        # If customer_id not provided for some reason, auto-generate one
        if not customer_id:
            with db_connection() as conn:
                row = conn.execute('SELECT MAX(id) FROM customers').fetchone()
                max_id = row[0] if row and row[0] else 0
                customer_id = f"CUST{str(max_id+1).zfill(4)}"

        # Validate required fields (customer_id, name, address and state)
        if not customer_id or not name or not address or not state:
            flash('Customer ID, Customer Name, Address and State are required!', 'error')
            return redirect(url_for('customers.add'))

        # Optional GST validation: must be exactly 15 characters if provided
        if gst_number and len(gst_number) != 15:
            flash('GST Number must be exactly 15 characters.', 'error')
            return redirect(url_for('customers.add'))
        
        with db_connection() as conn:
            # Check if customer_id already exists
            existing_cid = conn.execute('SELECT id FROM customers WHERE customer_id = ?', (customer_id,)).fetchone()

            if existing_cid:
                flash('Customer ID already exists! Please use a unique ID.', 'error')
                return redirect(url_for('customers.add'))

            # Check if vendor code already exists (only if provided)
            if vendor_code:
                existing_vcode = conn.execute('SELECT id FROM customers WHERE vendor_code = ?', (vendor_code,)).fetchone()
                if existing_vcode:
                    flash('Vendor Code already exists! Please use a unique code.', 'error')
                    return redirect(url_for('customers.add'))

            try:
                conn.execute('''INSERT INTO customers (customer_id, vendor_code, name, email, mobile, address, state, gst_number)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (customer_id, vendor_code, name, email, mobile, address, state, gst_number))
                conn.commit()

                flash('Customer added successfully!', 'success')
                return redirect(url_for('customers.index'))
            except Exception:
                current_app.logger.exception('Error adding customer')
                flash('Could not add the customer. Please try again.', 'error')
                return redirect(url_for('customers.add'))
    
    # For GET: generate a suggested customer_id and render form
    with db_connection() as conn:
        row = conn.execute('SELECT MAX(id) FROM customers').fetchone()
        max_id = row[0] if row and row[0] else 0
        suggested_cid = f"CUST{str(max_id+1).zfill(4)}"
        return render_template('customers/add.html', customer_id=suggested_cid)

@customers_bp.route('/update/<int:customer_id>', methods=['GET', 'POST'])
def update(customer_id):
    """Update a customer"""
    with db_connection() as conn:
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
            gst_number = gst_number.strip().upper()

            # Validate required fields
            if not new_customer_id or not name or not address or not state:
                flash('Customer ID, Customer Name, Address and State are required!', 'error')
                return redirect(url_for('customers.update', customer_id=customer_id))

            # Optional GST validation: must be exactly 15 characters if provided
            if gst_number and len(gst_number) != 15:
                flash('GST Number must be exactly 15 characters.', 'error')
                return redirect(url_for('customers.update', customer_id=customer_id))

            # Check if new customer_id already exists (excluding current customer)
            existing_cid = conn.execute('SELECT id FROM customers WHERE customer_id = ? AND id != ?',
                                       (new_customer_id, customer_id)).fetchone()
            if existing_cid:
                flash('Customer ID already exists! Please use a unique ID.', 'error')
                return redirect(url_for('customers.update', customer_id=customer_id))

            # Check if vendor code already exists (excluding current customer, only if provided)
            if vendor_code:
                existing_vcode = conn.execute('SELECT id FROM customers WHERE vendor_code = ? AND id != ?',
                                             (vendor_code, customer_id)).fetchone()
                if existing_vcode:
                    flash('Vendor Code already exists! Please use a unique code.', 'error')
                    return redirect(url_for('customers.update', customer_id=customer_id))

            try:
                conn.execute('''UPDATE customers
                               SET customer_id = ?, vendor_code = ?, name = ?, email = ?,
                                   mobile = ?, address = ?, state = ?, gst_number = ?
                               WHERE id = ?''',
                            (new_customer_id, vendor_code, name, email, mobile, address, state, gst_number, customer_id))
                conn.commit()

                flash('Customer updated successfully!', 'success')
                return redirect(url_for('customers.index'))
            except Exception:
                current_app.logger.exception('Error updating customer id=%s', customer_id)
                flash('Could not update the customer. Please try again.', 'error')
                return redirect(url_for('customers.update', customer_id=customer_id))

        # GET request - show update form
        customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()

        if not customer:
            flash('Customer not found!', 'error')
            return redirect(url_for('customers.index'))

        return render_template('customers/update.html', customer=customer)

@customers_bp.route('/delete/<int:id>')
def delete(id):
    """Delete a customer by ID"""
    with db_connection() as conn:
        # Check if customer has any bills
        bills = conn.execute('SELECT COUNT(*) as count FROM billing WHERE customer_id = ?', (id,)).fetchone()
        if bills and bills['count'] > 0:
            flash(f'Cannot delete customer! This customer has {bills["count"]} associated bill(s). Delete or reassign the bills first.', 'error')
            return redirect(url_for('customers.index'))

        conn.execute('DELETE FROM customers WHERE id = ?', (id,))
        conn.commit()

        flash('Customer deleted successfully!', 'success')
        return redirect(url_for('customers.index'))

@customers_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple customers"""
    customer_ids = request.form.getlist('customer_ids[]')
    
    if not customer_ids:
        flash('No customers selected!', 'error')
        return redirect(url_for('customers.index'))
    
    with db_connection() as conn:
        # Check if any selected customers have bills
        placeholders = ','.join('?' * len(customer_ids))
        bills = conn.execute(f'SELECT COUNT(*) as count FROM billing WHERE customer_id IN ({placeholders})', customer_ids).fetchone()

        if bills and bills['count'] > 0:
            flash(f'Cannot delete! {bills["count"]} bill(s) are associated with the selected customer(s). Delete or reassign the bills first.', 'error')
            return redirect(url_for('customers.index'))

        conn.execute(f'DELETE FROM customers WHERE id IN ({placeholders})', customer_ids)
        conn.commit()

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

    with db_connection() as conn:
        existing = conn.execute('SELECT id FROM customers WHERE vendor_code = ?', (vendor_code,)).fetchone()
        return jsonify({'exists': bool(existing)})
