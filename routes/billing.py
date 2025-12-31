"""
Billing routes module
Handles all billing-related routes with support for multiple items per bill
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_db_connection
from datetime import datetime

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')

@billing_bp.route('/')
def index():
    """Display all bills"""
    conn = get_db_connection()
    bills = conn.execute('''
        SELECT b.*, c.name as customer_name,
               (SELECT COUNT(*) FROM billing_items WHERE bill_id = b.id) as item_count
        FROM billing b 
        JOIN customers c ON b.customer_id = c.id 
        ORDER BY b.created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('billing/index.html', bills=bills)

@billing_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new bill with multiple items"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        bill_id_mode = request.form.get('bill_id_mode', 'auto')
        customer_id = request.form['customer_id']
        bill_date = request.form['bill_date']
        payment_status = request.form.get('payment_status', 'Pending')
        notes = request.form.get('notes', '')
        
        # Handle bill_id generation
        if bill_id_mode == 'auto' or not bill_id:
            # Auto-generate bill_id in format ST###
            last_bill = conn.execute('SELECT bill_id FROM billing ORDER BY id DESC LIMIT 1').fetchone()
            if last_bill and last_bill['bill_id']:
                # Extract number from last bill_id (e.g., ST486 -> 486)
                try:
                    last_num = int(last_bill['bill_id'][2:])  # Skip 'ST' prefix
                    next_num = last_num + 1
                except (ValueError, IndexError):
                    next_num = 1
            else:
                next_num = 1
            bill_id = f'ST{next_num}'
        else:
            # Manual mode - validate uniqueness
            existing = conn.execute('SELECT id FROM billing WHERE bill_id = ?', (bill_id,)).fetchone()
            if existing:
                flash(f'Bill ID "{bill_id}" already exists! Please use a different ID.', 'error')
                conn.close()
                return redirect(url_for('billing.create'))
        
        # Get items data (sent as JSON)
        import json
        items_json = request.form.get('items_data', '[]')
        items = json.loads(items_json)
        
        if not customer_id or not bill_date:
            flash('Customer and Bill Date are required!', 'error')
            conn.close()
            return redirect(url_for('billing.create'))
        
        if not items or len(items) == 0:
            flash('Please add at least one item to the bill!', 'error')
            conn.close()
            return redirect(url_for('billing.create'))
        
        # Check inventory for all items
        for item in items:
            product = conn.execute('SELECT product_id, product_name, quantity FROM inventory WHERE id = ?', 
                                 (item['product_id'],)).fetchone()
            if product:
                if product['quantity'] < item['quantity']:
                    flash(f'Insufficient quantity for {product["product_name"]} (Product ID: {product["product_id"]}). Only {product["quantity"]} available!', 'error')
                    conn.close()
                    return redirect(url_for('billing.create'))
        
        # Calculate totals
        subtotal = sum(float(item['subtotal']) for item in items)
        gst_amount = sum(float(item['gst_amount']) for item in items)
        total_amount = sum(float(item['total']) for item in items)
        
        # Insert bill header
        cursor = conn.execute('''INSERT INTO billing (bill_id, customer_id, bill_date, subtotal, gst_amount,
                                total_amount, payment_status, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (bill_id, customer_id, bill_date, subtotal, gst_amount, total_amount,
                             payment_status, notes))
        
        # Get the auto-generated numeric ID for the bill
        new_bill_id = cursor.lastrowid
        
        # Insert bill items and update inventory (use numeric bill ID)
        for item in items:
            conn.execute('''INSERT INTO billing_items (bill_id, product_id, product_name, quantity,
                           unit_price, gst_percentage, gst_amount, cgst, sgst, igst, total)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (new_bill_id, item['product_id'], item['product_name'], item['quantity'],
                         item['unit_price'], item['gst_percentage'],
                         item['gst_amount'], item.get('cgst', 0), item.get('sgst', 0),
                         item.get('igst', 0), item['total']))
            
            # Reduce inventory
            conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?',
                        (item['quantity'], item['product_id']))
        
        conn.commit()
        conn.close()
        
        flash(f'Bill {bill_id} created successfully with {len(items)} item(s)! Inventory updated.', 'success')
        return redirect(url_for('billing.index'))
    
    # Convert Row objects to dictionaries for JSON serialization
    customers_rows = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    customers = [dict(row) for row in customers_rows]
    
    inventory_rows = conn.execute('SELECT * FROM inventory WHERE quantity > 0 ORDER BY product_name').fetchall()
    inventory = [dict(row) for row in inventory_rows]
    
    conn.close()
    return render_template('billing/create.html', customers=customers, inventory=inventory)

@billing_bp.route('/api/customer/<int:customer_id>')
def get_customer(customer_id):
    """API endpoint to get customer details"""
    conn = get_db_connection()
    customer = conn.execute('SELECT * FROM customers WHERE id = ?', (customer_id,)).fetchone()
    conn.close()
    
    if customer:
        return jsonify({
            'id': customer['id'],
            'customer_id': customer['customer_id'],
            'name': customer['name'],
            'vendor_code': customer['vendor_code'],
            'state': customer['state'],
            'address': customer['address']
        })
    return jsonify({'error': 'Customer not found'}), 404

@billing_bp.route('/api/product/<int:product_id>')
def get_product(product_id):
    """API endpoint to get product details"""
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM inventory WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    if product:
        return jsonify({
            'id': product['id'],
            'product_id': product['product_id'],
            'product_name': product['product_name'],
            'hsn_code': product['hsn_code'],
            'manufacture_date': product['manufacture_date'],
            'expiry_month': product['expiry_month'],
            'quantity': product['quantity'],
            'unit_price': product['unit_price'],
            'mrp': product['mrp'],
            'gst_percentage': product['gst_percentage']
        })
    return jsonify({'error': 'Product not found'}), 404

@billing_bp.route('/delete/<int:id>')
def delete(id):
    """Delete a bill by ID"""
    conn = get_db_connection()
    
    # Get bill_id text from billing table
    bill = conn.execute('SELECT bill_id FROM billing WHERE id = ?', (id,)).fetchone()
    if not bill:
        flash('Bill not found!', 'error')
        conn.close()
        return redirect(url_for('billing.index'))
    
    bill_id_text = bill['bill_id']
    
    # Get bill items to restore inventory
    items = conn.execute('SELECT product_id, quantity FROM billing_items WHERE bill_id = ?', (bill_id_text,)).fetchall()
    
    for item in items:
        # Restore inventory quantity
        conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE id = ?',
                    (item['quantity'], item['product_id']))
    
    # Delete bill items and bill
    conn.execute('DELETE FROM billing_items WHERE bill_id = ?', (bill_id_text,))
    conn.execute('DELETE FROM billing WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Bill deleted successfully! Inventory restored.', 'success')
    return redirect(url_for('billing.index'))

@billing_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple bills"""
    bill_internal_ids = request.form.getlist('bill_ids[]')
    
    if not bill_internal_ids:
        flash('No bills selected!', 'error')
        return redirect(url_for('billing.index'))
    
    conn = get_db_connection()
    
    # Get bill_id texts for the selected bills
    placeholders = ','.join('?' * len(bill_internal_ids))
    bills = conn.execute(f'SELECT bill_id FROM billing WHERE id IN ({placeholders})', bill_internal_ids).fetchall()
    bill_id_texts = [bill['bill_id'] for bill in bills]
    
    # Restore inventory for all bills being deleted
    placeholders_text = ','.join('?' * len(bill_id_texts))
    items = conn.execute(f'SELECT product_id, quantity FROM billing_items WHERE bill_id IN ({placeholders_text})',
                        bill_id_texts).fetchall()
    
    for item in items:
        conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE id = ?',
                    (item['quantity'], item['product_id']))
    
    # Delete bill items and bills
    conn.execute(f'DELETE FROM billing_items WHERE bill_id IN ({placeholders_text})', bill_id_texts)
    placeholders_int = ','.join('?' * len(bill_internal_ids))
    conn.execute(f'DELETE FROM billing WHERE id IN ({placeholders_int})', bill_internal_ids)
    conn.commit()
    conn.close()
    
    flash(f'{len(bill_internal_ids)} bill(s) deleted successfully! Inventory restored.', 'success')
    return redirect(url_for('billing.index'))

@billing_bp.route('/view/<int:id>')
def view(id):
    """View bill details with all items"""
    conn = get_db_connection()
    bill = conn.execute('''
        SELECT b.*, c.name as customer_name, c.email, c.mobile, c.address, c.gst_number
        FROM billing b
        JOIN customers c ON b.customer_id = c.id
        WHERE b.id = ?
    ''', (id,)).fetchone()
    
    if not bill:
        flash('Bill not found!', 'error')
        conn.close()
        return redirect(url_for('billing.index'))
    
    # Convert bill to dict and format date
    bill_dict = dict(bill)
    if bill_dict['bill_date']:
        # Convert YYYY-MM-DD to DD-MM-YYYY
        date_obj = datetime.strptime(bill_dict['bill_date'], '%Y-%m-%d')
        bill_dict['bill_date'] = date_obj.strftime('%d-%m-%Y')
    
    items = conn.execute('''
        SELECT bi.*, i.product_id as inventory_product_id
        FROM billing_items bi
        LEFT JOIN inventory i ON bi.product_id = i.id
        WHERE bi.bill_id = ?
        ORDER BY bi.id
    ''', (id,)).fetchall()
    
    # Get seller information
    seller = conn.execute('SELECT * FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    
    conn.close()
    return render_template('billing/view.html', bill=bill_dict, items=items, seller=seller)

@billing_bp.route('/update/<int:bill_id>', methods=['GET', 'POST'])
def update(bill_id):
    """Update an existing bill with multiple items"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        new_bill_id = request.form.get('bill_id', '').strip()
        customer_id = request.form['customer_id']
        bill_date = request.form['bill_date']
        payment_status = request.form.get('payment_status', 'Pending')
        notes = request.form.get('notes', '')
        
        # Validate bill_id uniqueness (if changed)
        current_bill = conn.execute('SELECT bill_id FROM billing WHERE id = ?', (bill_id,)).fetchone()
        if new_bill_id != current_bill['bill_id']:
            existing = conn.execute('SELECT id FROM billing WHERE bill_id = ? AND id != ?',
                                   (new_bill_id, bill_id)).fetchone()
            if existing:
                flash(f'Bill ID "{new_bill_id}" already exists! Please use a different ID.', 'error')
                conn.close()
                return redirect(url_for('billing.update', bill_id=bill_id))
        
        # Get items data (sent as JSON)
        import json
        items_json = request.form.get('items_data', '[]')
        items = json.loads(items_json)
        
        if not customer_id or not bill_date:
            flash('Customer and Bill Date are required!', 'error')
            conn.close()
            return redirect(url_for('billing.update', bill_id=bill_id))
        
        if not items or len(items) == 0:
            flash('Please add at least one item to the bill!', 'error')
            conn.close()
            return redirect(url_for('billing.update', bill_id=bill_id))
        
        # Get current bill's bill_id text
        current_bill = conn.execute('SELECT bill_id FROM billing WHERE id = ?', (bill_id,)).fetchone()
        current_bill_id_text = current_bill['bill_id']
        
        # Get old bill items to restore inventory
        old_items = conn.execute('SELECT product_id, quantity FROM billing_items WHERE bill_id = ?',
                                (current_bill_id_text,)).fetchall()
        
        # Restore old inventory quantities
        for old_item in old_items:
            conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE id = ?',
                        (old_item['quantity'], old_item['product_id']))
        
        # Check inventory for all new items
        for item in items:
            product = conn.execute('SELECT product_id, product_name, quantity FROM inventory WHERE id = ?',
                                 (item['product_id'],)).fetchone()
            if product:
                if product['quantity'] < item['quantity']:
                    # Restore the old quantities back since we're not proceeding
                    for old_item in old_items:
                        conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?',
                                    (old_item['quantity'], old_item['product_id']))
                    conn.commit()
                    flash(f'Insufficient quantity for {product["product_name"]} (Product ID: {product["product_id"]}). Only {product["quantity"]} available!', 'error')
                    conn.close()
                    return redirect(url_for('billing.update', bill_id=bill_id))
        
        # Calculate totals
        subtotal = sum(float(item['quantity']) * float(item['unit_price']) for item in items)
        gst_amount = sum(float(item['gst_amount']) for item in items)
        total_amount = sum(float(item['total']) for item in items)
        
        # Update bill header
        conn.execute('''UPDATE billing SET bill_id = ?, customer_id = ?, bill_date = ?, subtotal = ?, gst_amount = ?,
                       total_amount = ?, payment_status = ?, notes = ?
                       WHERE id = ?''',
                    (new_bill_id, customer_id, bill_date, subtotal, gst_amount, total_amount,
                     payment_status, notes, bill_id))
        
        # Delete old bill items
        conn.execute('DELETE FROM billing_items WHERE bill_id = ?', (bill_id,))
        
        # Insert new bill items with numeric bill_id and update inventory
        for item in items:
            conn.execute('''INSERT INTO billing_items (bill_id, product_id, product_name, quantity,
                           unit_price, gst_percentage, gst_amount, cgst, sgst, igst, total)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (bill_id, item['product_id'], item['product_name'], item['quantity'],
                         item['unit_price'], item['gst_percentage'],
                         item['gst_amount'], item.get('cgst', 0), item.get('sgst', 0),
                         item.get('igst', 0), item['total']))
            
            # Reduce inventory
            conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?',
                        (item['quantity'], item['product_id']))
        
        conn.commit()
        conn.close()
        
        flash(f'Bill {new_bill_id} updated successfully with {len(items)} item(s)! Inventory updated.', 'success')
        return redirect(url_for('billing.index'))
    
    # GET request - load bill for editing
    bill = conn.execute('SELECT * FROM billing WHERE id = ?', (bill_id,)).fetchone()
    
    if not bill:
        conn.close()
        flash('Bill not found!', 'error')
        return redirect(url_for('billing.index'))
    
    # Get bill items
    items = conn.execute('SELECT * FROM billing_items WHERE bill_id = ? ORDER BY id', (bill_id,)).fetchall()
    
    # Convert Row objects to dictionaries for JSON serialization
    customers_rows = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    customers = [dict(row) for row in customers_rows]
    
    inventory_rows = conn.execute('SELECT * FROM inventory WHERE quantity > 0 ORDER BY product_name').fetchall()
    inventory = [dict(row) for row in inventory_rows]
    
    # Convert bill items to list of dicts
    bill_items = [dict(row) for row in items]
    
    conn.close()
    return render_template('billing/update.html', bill=dict(bill), bill_items=bill_items,
                         customers=customers, inventory=inventory)

# Made with Bob
