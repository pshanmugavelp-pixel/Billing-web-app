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
    """Display all bills with optional filter for cancelled bills"""
    show_cancelled = request.args.get('show_cancelled', 'false') == 'true'
    
    conn = get_db_connection()
    
    if show_cancelled:
        # Show only cancelled bills
        bills = conn.execute('''
            SELECT b.*, c.name as customer_name,
                   (SELECT COUNT(*) FROM billing_items WHERE bill_id = b.bill_id) as item_count
            FROM billing b
            JOIN customers c ON b.customer_id = c.id
            WHERE b.payment_status = 'Cancelled'
            ORDER BY b.created_at DESC
        ''').fetchall()
    else:
        # Show all bills except cancelled
        bills = conn.execute('''
            SELECT b.*, c.name as customer_name,
                   (SELECT COUNT(*) FROM billing_items WHERE bill_id = b.bill_id) as item_count
            FROM billing b
            JOIN customers c ON b.customer_id = c.id
            WHERE b.payment_status != 'Cancelled'
            ORDER BY b.created_at DESC
        ''').fetchall()
    
    conn.close()
    return render_template('billing/index.html', bills=bills, show_cancelled=show_cancelled)

@billing_bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new bill with multiple items"""
    conn = get_db_connection()
    
    # Get seller information for state comparison
    seller = conn.execute('SELECT state FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    seller_state = seller['state'] if seller and seller['state'] else ''
    
    # Get customers and inventory for form
    customers_rows = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
    customers = [dict(row) for row in customers_rows]
    
    inventory_rows = conn.execute('SELECT * FROM inventory WHERE quantity > 0 ORDER BY product_name').fetchall()
    inventory = [dict(row) for row in inventory_rows]
    
    if request.method == 'POST':
        bill_id = request.form.get('bill_id', '').strip()
        bill_id_mode = request.form.get('bill_id_mode', 'auto')
        customer_id = request.form.get('customer_id', '')
        bill_date = request.form.get('bill_date', '')
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
                # Return to form with existing data
                form_data = {
                    'bill_id': bill_id,
                    'customer_id': customer_id,
                    'bill_date': bill_date,
                    'payment_status': payment_status,
                    'notes': notes,
                    'items_data': request.form.get('items_data', '[]')
                }
                conn.close()
                return render_template('billing/create.html', customers=customers, inventory=inventory, form_data=form_data)
        
        # Get items data (sent as JSON)
        import json
        items_json = request.form.get('items_data', '[]')
        items = json.loads(items_json)
        
        if not customer_id or not bill_date:
            flash('Customer and Bill Date are required!', 'error')
            # Return to form with existing data
            form_data = {
                'bill_id': bill_id,
                'customer_id': customer_id,
                'bill_date': bill_date,
                'payment_status': payment_status,
                'notes': notes,
                'items_data': items_json
            }
            conn.close()
            return render_template('billing/create.html', customers=customers, inventory=inventory, form_data=form_data)
        
        if not items or len(items) == 0:
            flash('Please add at least one item to the bill!', 'error')
            # Return to form with existing data
            form_data = {
                'bill_id': bill_id,
                'customer_id': customer_id,
                'bill_date': bill_date,
                'payment_status': payment_status,
                'notes': notes,
                'items_data': items_json
            }
            conn.close()
            return render_template('billing/create.html', customers=customers, inventory=inventory, form_data=form_data)
        
        # Group items by product_id and sum quantities for duplicate products
        product_quantities = {}
        for item in items:
            product_id = item['product_id']
            if product_id in product_quantities:
                product_quantities[product_id]['total_quantity'] += item['quantity']
            else:
                product_quantities[product_id] = {
                    'total_quantity': item['quantity'],
                    'product_name': item['product_name']
                }
        
        # Check inventory for all products (considering total quantities)
        for product_id, data in product_quantities.items():
            product = conn.execute('SELECT product_id, product_name, quantity FROM inventory WHERE id = ?',
                                 (product_id,)).fetchone()
            if product:
                if product['quantity'] < data['total_quantity']:
                    flash(f'Insufficient quantity for {product["product_name"]} (Product ID: {product["product_id"]}). Requested: {data["total_quantity"]}, Available: {product["quantity"]}', 'error')
                    # Return to form with existing data
                    form_data = {
                        'bill_id': bill_id,
                        'customer_id': customer_id,
                        'bill_date': bill_date,
                        'payment_status': payment_status,
                        'notes': notes,
                        'items_data': items_json
                    }
                    conn.close()
                    return render_template('billing/create.html', customers=customers, inventory=inventory, form_data=form_data)
            else:
                flash(f'Product {data["product_name"]} not found in inventory!', 'error')
                # Return to form with existing data
                form_data = {
                    'bill_id': bill_id,
                    'customer_id': customer_id,
                    'bill_date': bill_date,
                    'payment_status': payment_status,
                    'notes': notes,
                    'items_data': items_json
                }
                conn.close()
                return render_template('billing/create.html', customers=customers, inventory=inventory, form_data=form_data)
        
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
        new_bill_numeric_id = cursor.lastrowid
        
        # Insert bill items and update inventory (use TEXT bill_id, not numeric ID)
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
        
        flash(f'Bill {bill_id} created successfully with {len(items)} item(s)! Inventory updated.', 'success')
        return redirect(url_for('billing.index'))
    
    # GET request - show empty form
    conn.close()
    return render_template('billing/create.html', customers=customers, inventory=inventory,
                         form_data=None, seller_state=seller_state)

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

@billing_bp.route('/cancel-bills-confirm', methods=['POST'])
def cancel_bills_confirm():
    """Show confirmation page for cancelling multiple bills with inventory changes"""
    bill_internal_ids = request.form.getlist('bill_ids[]')
    
    if not bill_internal_ids:
        flash('No bills selected!', 'error')
        return redirect(url_for('billing.index'))
    
    conn = get_db_connection()
    
    # Get bill details
    placeholders = ','.join('?' * len(bill_internal_ids))
    bills = conn.execute(f'''
        SELECT b.*, c.name as customer_name
        FROM billing b
        JOIN customers c ON b.customer_id = c.id
        WHERE b.id IN ({placeholders})
    ''', bill_internal_ids).fetchall()
    
    # Calculate inventory changes for all selected bills
    inventory_changes = []
    product_totals = {}
    
    for bill in bills:
        items = conn.execute('''
            SELECT product_id, product_name, quantity
            FROM billing_items
            WHERE bill_id = ?
        ''', (bill['id'],)).fetchall()
        
        for item in items:
            pid = item['product_id']
            if pid in product_totals:
                product_totals[pid]['quantity'] += item['quantity']
            else:
                product_totals[pid] = {
                    'product_name': item['product_name'],
                    'quantity': item['quantity']
                }
    
    # Get current inventory and calculate changes
    for pid, data in product_totals.items():
        current_inv = conn.execute('SELECT quantity FROM inventory WHERE id = ?', (pid,)).fetchone()
        current_qty = current_inv['quantity'] if current_inv else 0
        new_qty = current_qty + data['quantity']
        
        inventory_changes.append({
            'product_id': pid,
            'product_name': data['product_name'],
            'current_qty': current_qty,
            'restore_qty': data['quantity'],
            'new_qty': new_qty
        })
    
    conn.close()
    
    return render_template('billing/cancel_confirm.html',
                         bills=[dict(b) for b in bills],
                         bill_ids=bill_internal_ids,
                         inventory_changes=inventory_changes)

@billing_bp.route('/cancel-bills', methods=['POST'])
def cancel_bills():
    """Cancel multiple bills and restore inventory"""
    bill_internal_ids = request.form.getlist('bill_ids[]')
    
    if not bill_internal_ids:
        flash('No bills selected!', 'error')
        return redirect(url_for('billing.index'))
    
    conn = get_db_connection()
    
    # Restore inventory for all bills being cancelled
    for bill_id in bill_internal_ids:
        items = conn.execute('SELECT product_id, quantity FROM billing_items WHERE bill_id = ?',
                           (bill_id,)).fetchall()
        
        for item in items:
            conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE id = ?',
                        (item['quantity'], item['product_id']))
    
    # Update bills to Cancelled status
    placeholders = ','.join('?' * len(bill_internal_ids))
    conn.execute(f'UPDATE billing SET payment_status = ? WHERE id IN ({placeholders})',
                ['Cancelled'] + bill_internal_ids)
    conn.commit()
    conn.close()
    
    flash(f'{len(bill_internal_ids)} bill(s) cancelled successfully! Inventory restored.', 'success')
    return redirect(url_for('billing.index'))

@billing_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple bills (kept for backward compatibility)"""
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
    ''', (bill_dict['bill_id'],)).fetchall()
    
    # Get seller information
    seller = conn.execute('SELECT * FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    
    conn.close()
    return render_template('billing/view.html', bill=bill_dict, items=items, seller=seller)

@billing_bp.route('/print/<int:id>')
def print_bill(id):
    """Print-friendly view of bill details"""
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
    ''', (bill_dict['bill_id'],)).fetchall()
    
    # Get seller information
    seller = conn.execute('SELECT * FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    
    conn.close()
    return render_template('billing/print.html', bill=bill_dict, items=items, seller=seller)
@billing_bp.route('/print-multiple')
def print_multiple():
    """Print multiple bills in a single printable page"""
    bill_ids_str = request.args.get('bill_ids', '')
    
    if not bill_ids_str:
        flash('No bills selected for printing!', 'error')
        return redirect(url_for('billing.index'))
    
    # Parse bill IDs
    try:
        bill_ids = [int(bid.strip()) for bid in bill_ids_str.split(',') if bid.strip()]
    except ValueError:
        flash('Invalid bill IDs!', 'error')
        return redirect(url_for('billing.index'))
    
    if not bill_ids:
        flash('No valid bills selected!', 'error')
        return redirect(url_for('billing.index'))
    
    conn = get_db_connection()
    
    # Get seller information (same for all bills)
    seller = conn.execute('SELECT * FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    
    # Collect all bills data
    bills_data = []
    
    for bill_id in bill_ids:
        # Get bill details
        bill = conn.execute('''
            SELECT b.*, c.name as customer_name, c.email, c.mobile, c.address, c.gst_number
            FROM billing b
            JOIN customers c ON b.customer_id = c.id
            WHERE b.id = ?
        ''', (bill_id,)).fetchone()
        
        if not bill:
            continue
        
        # Convert bill to dict and format date
        bill_dict = dict(bill)
        if bill_dict['bill_date']:
            # Convert YYYY-MM-DD to DD-MM-YYYY
            date_obj = datetime.strptime(bill_dict['bill_date'], '%Y-%m-%d')
            bill_dict['bill_date'] = date_obj.strftime('%d-%m-%Y')
        
        # Get bill items
        items = conn.execute('''
            SELECT bi.*, i.product_id as inventory_product_id
            FROM billing_items bi
            LEFT JOIN inventory i ON bi.product_id = i.id
            WHERE bi.bill_id = ?
            ORDER BY bi.id
        ''', (bill_id,)).fetchall()
        
        bills_data.append({
            'bill': bill_dict,
            'items': items
        })
    
    conn.close()
    
    if not bills_data:
        flash('No valid bills found for printing!', 'error')
        return redirect(url_for('billing.index'))
    
    return render_template('billing/print_multiple.html', bills_data=bills_data, seller=seller)


@billing_bp.route('/update/<int:bill_id>', methods=['GET', 'POST'])
def update(bill_id):
    """Update an existing bill with multiple items"""
    conn = get_db_connection()
    
    # Get seller information for state comparison
    seller = conn.execute('SELECT state FROM seller_info ORDER BY id DESC LIMIT 1').fetchone()
    seller_state = seller['state'] if seller and seller['state'] else ''
    
    if request.method == 'POST':
        # Check if user confirmed the update
        confirm_update = request.form.get('confirm_update')
        
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
        current_bill_id_text = current_bill['bill_id']
        
        # Get old bill items (use numeric bill_id, not text bill_id)
        old_items = conn.execute('SELECT product_id, quantity, product_name FROM billing_items WHERE bill_id = ?',
                                (bill_id,)).fetchall()
        
        # If not confirmed, show preview of inventory changes
        if confirm_update != 'yes':
            # Calculate inventory changes
            inventory_changes = []
            
            # Track old items (will be restored)
            old_products = {}
            for old_item in old_items:
                pid = old_item['product_id']
                if pid in old_products:
                    old_products[pid]['quantity'] += old_item['quantity']
                else:
                    old_products[pid] = {
                        'product_name': old_item['product_name'],
                        'quantity': old_item['quantity']
                    }
            
            # Track new items (will be deducted)
            new_products = {}
            for item in items:
                pid = item['product_id']
                if pid in new_products:
                    new_products[pid]['quantity'] += item['quantity']
                else:
                    new_products[pid] = {
                        'product_name': item['product_name'],
                        'quantity': item['quantity']
                    }
            
            # Calculate net changes
            all_product_ids = set(old_products.keys()) | set(new_products.keys())
            for pid in all_product_ids:
                old_qty = old_products.get(pid, {}).get('quantity', 0)
                new_qty = new_products.get(pid, {}).get('quantity', 0)
                product_name = old_products.get(pid, {}).get('product_name') or new_products.get(pid, {}).get('product_name')
                
                # Get current inventory
                current_inv = conn.execute('SELECT quantity FROM inventory WHERE id = ?', (pid,)).fetchone()
                current_qty = current_inv['quantity'] if current_inv else 0
                
                net_change = old_qty - new_qty  # Positive means inventory increases, negative means decreases
                new_inventory = current_qty + net_change
                
                if net_change != 0:
                    inventory_changes.append({
                        'product_id': pid,
                        'product_name': product_name,
                        'current_qty': current_qty,
                        'old_bill_qty': old_qty,
                        'new_bill_qty': new_qty,
                        'net_change': net_change,
                        'new_inventory': new_inventory
                    })
            
            # Check if any new inventory would be negative
            insufficient_stock = []
            for change in inventory_changes:
                if change['new_inventory'] < 0:
                    insufficient_stock.append(change)
            
            if insufficient_stock:
                flash('Cannot update bill: Insufficient inventory for the following products:', 'error')
                for item in insufficient_stock:
                    flash(f"• {item['product_name']}: Current stock {item['current_qty']}, would become {item['new_inventory']} after update", 'error')
                conn.close()
                return redirect(url_for('billing.update', bill_id=bill_id))
            
            # Get all data for the confirmation form
            bill = conn.execute('SELECT * FROM billing WHERE id = ?', (bill_id,)).fetchone()
            customers_rows = conn.execute('SELECT * FROM customers ORDER BY name').fetchall()
            customers = [dict(row) for row in customers_rows]
            inventory_rows = conn.execute('SELECT * FROM inventory ORDER BY product_name').fetchall()
            inventory = [dict(row) for row in inventory_rows]
            
            conn.close()
            
            # Show confirmation page with inventory changes
            return render_template('billing/update_confirm.html',
                                 bill=dict(bill),
                                 items=items,
                                 customers=customers,
                                 inventory=inventory,
                                 inventory_changes=inventory_changes,
                                 form_data={
                                     'bill_id': new_bill_id,
                                     'customer_id': customer_id,
                                     'bill_date': bill_date,
                                     'payment_status': payment_status,
                                     'notes': notes,
                                     'items_data': items_json
                                 })
        
        # User confirmed - proceed with update
        # Restore old inventory quantities
        for old_item in old_items:
            conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE id = ?',
                        (old_item['quantity'], old_item['product_id']))
        
        # Group items by product_id and sum quantities for duplicate products
        product_quantities = {}
        for item in items:
            product_id = item['product_id']
            if product_id in product_quantities:
                product_quantities[product_id]['total_quantity'] += item['quantity']
            else:
                product_quantities[product_id] = {
                    'total_quantity': item['quantity'],
                    'product_name': item['product_name']
                }
        
        # Check inventory for all new items (considering total quantities)
        for product_id, data in product_quantities.items():
            product = conn.execute('SELECT product_id, product_name, quantity FROM inventory WHERE id = ?',
                                 (product_id,)).fetchone()
            if product:
                if product['quantity'] < data['total_quantity']:
                    # Restore the old quantities back since we're not proceeding
                    for old_item in old_items:
                        conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?',
                                    (old_item['quantity'], old_item['product_id']))
                    conn.commit()
                    flash(f'Insufficient quantity for {product["product_name"]} (Product ID: {product["product_id"]}). Requested: {data["total_quantity"]}, Available: {product["quantity"]}', 'error')
                    conn.close()
                    return redirect(url_for('billing.update', bill_id=bill_id))
            else:
                # Restore the old quantities back since we're not proceeding
                for old_item in old_items:
                    conn.execute('UPDATE inventory SET quantity = quantity - ? WHERE id = ?',
                                (old_item['quantity'], old_item['product_id']))
                conn.commit()
                flash(f'Product {data["product_name"]} not found in inventory!', 'error')
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
        
        # Get existing billing_items to update or delete
        existing_items = conn.execute('SELECT id FROM billing_items WHERE bill_id = ? ORDER BY id',
                                     (bill_id,)).fetchall()
        existing_item_ids = [item['id'] for item in existing_items]
        
        # Update or insert bill items
        for i, item in enumerate(items):
            if i < len(existing_item_ids):
                # Update existing item
                item_id = existing_item_ids[i]
                conn.execute('''UPDATE billing_items
                               SET product_id = ?, product_name = ?, quantity = ?,
                                   unit_price = ?, gst_percentage = ?, gst_amount = ?,
                                   cgst = ?, sgst = ?, igst = ?, total = ?
                               WHERE id = ?''',
                            (item['product_id'], item['product_name'], item['quantity'],
                             item['unit_price'], item['gst_percentage'],
                             item['gst_amount'], item.get('cgst', 0), item.get('sgst', 0),
                             item.get('igst', 0), item['total'], item_id))
            else:
                # Insert new item
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
        
        # Delete extra items if new list is shorter than old list
        if len(items) < len(existing_item_ids):
            for item_id in existing_item_ids[len(items):]:
                conn.execute('DELETE FROM billing_items WHERE id = ?', (item_id,))
        
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
                         customers=customers, inventory=inventory, seller_state=seller_state)

@billing_bp.route('/active-bills-export')
def active_bills_export():
    """Display all active bills with detailed item information for Excel export"""
    conn = get_db_connection()
    
    # Get all active bills (not cancelled) with customer details and items
    bills = conn.execute('''
        SELECT
            b.id,
            b.bill_id,
            c.name as customer_name,
            c.gst_number as customer_gst,
            b.bill_date,
            b.subtotal,
            b.gst_amount,
            b.total_amount,
            b.payment_status,
            b.notes,
            b.created_at,
            c.customer_id,
            c.vendor_code,
            c.email,
            c.mobile,
            c.address,
            c.state
        FROM billing b
        JOIN customers c ON b.customer_id = c.id
        WHERE b.payment_status != 'Cancelled'
        ORDER BY b.created_at DESC
    ''').fetchall()
    
    # Get items for each bill
    bills_with_items = []
    for bill in bills:
        items = conn.execute('''
            SELECT
                bi.product_name,
                i.hsn_code,
                bi.quantity,
                bi.unit_price,
                bi.gst_percentage,
                bi.igst,
                bi.sgst,
                bi.cgst,
                bi.total
            FROM billing_items bi
            LEFT JOIN inventory i ON bi.product_id = i.id
            WHERE bi.bill_id = ?
            ORDER BY bi.id
        ''', (bill['bill_id'],)).fetchall()
        
        # Add all bills, even if they have no items
        bills_with_items.append({
            'bill': dict(bill),
            'items': [dict(item) for item in items] if items else []
        })
    
    conn.close()
    return render_template('billing/active_bills_export.html', bills_with_items=bills_with_items)

# Made with Bob
