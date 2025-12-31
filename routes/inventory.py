"""
Inventory routes module
Handles all inventory-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import get_db_connection
from datetime import datetime
from dateutil.relativedelta import relativedelta

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

@inventory_bp.route('/')
def index():
    """Display all inventory items"""
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('inventory/index.html', items=items)

@inventory_bp.route('/api/products')
def api_products():
    """API endpoint to get all products for autocomplete"""
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM inventory ORDER BY product_name').fetchall()
    conn.close()
    
    # Convert to list of dicts
    products_list = [dict(row) for row in products]
    return jsonify(products_list)

@inventory_bp.route('/api/next-product-id')
def next_product_id():
    """API endpoint to get the next auto-generated product ID"""
    conn = get_db_connection()
    
    # Get the last product_id
    last_product = conn.execute('SELECT product_id FROM inventory ORDER BY id DESC LIMIT 1').fetchone()
    
    if last_product and last_product['product_id']:
        # Extract number from last product_id (e.g., PROD0001 -> 1)
        try:
            last_num = int(last_product['product_id'].replace('PROD', ''))
            next_num = last_num + 1
        except (ValueError, AttributeError):
            next_num = 1
    else:
        next_num = 1
    
    # Format as PROD0001, PROD0002, etc.
    product_id = f'PROD{next_num:04d}'
    
    conn.close()
    
    return jsonify({'product_id': product_id})

@inventory_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new inventory item"""
    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        
        # Auto-generate product_id if not provided or empty
        if not product_id:
            conn = get_db_connection()
            last_product = conn.execute('SELECT product_id FROM inventory ORDER BY id DESC LIMIT 1').fetchone()
            
            if last_product and last_product['product_id']:
                try:
                    last_num = int(last_product['product_id'].replace('PROD', ''))
                    next_num = last_num + 1
                except (ValueError, AttributeError):
                    next_num = 1
            else:
                next_num = 1
            
            product_id = f'PROD{next_num:04d}'
            conn.close()
        
        product_name = request.form['product_name']
        hsn_code = request.form.get('hsn_code', '').strip()
        manufacture_date = request.form.get('manufacture_date', '')
        expiry_months = request.form.get('expiry_months', 0)
        quantity = request.form.get('quantity', 0)
        buy_price = request.form.get('buy_price', 0.0)
        unit_price = request.form.get('unit_price', 0.0)
        mrp = request.form.get('mrp', 0.0)
        gst_percentage = request.form.get('gst_percentage', 0.0)
        
        # Calculate expiry month from manufacture date + expiry months
        expiry_month = ''
        if manufacture_date and expiry_months:
            try:
                mfg_date = datetime.strptime(manufacture_date, '%Y-%m-%d')
                expiry_date = mfg_date + relativedelta(months=int(expiry_months))
                expiry_month = expiry_date.strftime('%Y-%m')
            except:
                flash('Invalid manufacture date or expiry months!', 'error')
                return redirect(url_for('inventory.add'))
        
        if not product_id or not product_name or not hsn_code or not manufacture_date or not expiry_months:
            flash('Product ID, Product Name, HSN Code, Manufacture Date, and Expiry Months are required!', 'error')
            return redirect(url_for('inventory.add'))
        
        conn = get_db_connection()
        
        # Check if product_id already exists
        existing = conn.execute('SELECT id FROM inventory WHERE product_id = ?', (product_id,)).fetchone()
        if existing:
            flash('Product ID already exists!', 'error')
            conn.close()
            return redirect(url_for('inventory.add'))
        
        conn.execute('''INSERT INTO inventory (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage))
        conn.commit()
        conn.close()
        
        flash('Inventory item added successfully!', 'success')
        return redirect(url_for('inventory.index'))
    
    return render_template('inventory/add.html')

@inventory_bp.route('/delete/<int:id>')
def delete(id):
    """Delete an inventory item by ID"""
    conn = get_db_connection()
    conn.execute('DELETE FROM inventory WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('Inventory item deleted successfully!', 'success')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple inventory items"""
    item_ids = request.form.getlist('item_ids[]')
    
    if not item_ids:
        flash('No items selected!', 'error')
        return redirect(url_for('inventory.index'))
    
    conn = get_db_connection()
    placeholders = ','.join('?' * len(item_ids))
    conn.execute(f'DELETE FROM inventory WHERE id IN ({placeholders})', item_ids)
    conn.commit()
    conn.close()
    
    flash(f'{len(item_ids)} item(s) deleted successfully!', 'success')
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    """Update inventory item"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        product_name = request.form['product_name']
        hsn_code = request.form.get('hsn_code', '').strip()
        manufacture_date = request.form.get('manufacture_date', '')
        expiry_months = request.form.get('expiry_months', 0)
        quantity = request.form.get('quantity', 0)
        buy_price = request.form.get('buy_price', 0.0)
        unit_price = request.form.get('unit_price', 0.0)
        mrp = request.form.get('mrp', 0.0)
        gst_percentage = request.form.get('gst_percentage', 0.0)
        
        # Calculate expiry month from manufacture date + expiry months
        expiry_month = ''
        if manufacture_date and expiry_months:
            try:
                mfg_date = datetime.strptime(manufacture_date, '%Y-%m-%d')
                expiry_date = mfg_date + relativedelta(months=int(expiry_months))
                expiry_month = expiry_date.strftime('%Y-%m')
            except:
                flash('Invalid manufacture date or expiry months!', 'error')
                conn.close()
                return redirect(url_for('inventory.update', id=id))
        
        if not product_id or not product_name or not hsn_code or not manufacture_date or not expiry_months:
            flash('Product ID, Product Name, HSN Code, Manufacture Date, and Expiry Months are required!', 'error')
            conn.close()
            return redirect(url_for('inventory.update', id=id))
        
        # Check if product_id already exists (excluding current item)
        existing = conn.execute('SELECT id FROM inventory WHERE product_id = ? AND id != ?', (product_id, id)).fetchone()
        if existing:
            flash('Product ID already exists!', 'error')
            conn.close()
            return redirect(url_for('inventory.update', id=id))
        
        conn.execute('''UPDATE inventory SET product_id = ?, product_name = ?, hsn_code = ?, manufacture_date = ?,
                        expiry_month = ?, quantity = ?, buy_price = ?, unit_price = ?, mrp = ?, gst_percentage = ?,
                        updated_at = CURRENT_TIMESTAMP WHERE id = ?''',
                     (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage, id))
        conn.commit()
        conn.close()
        
        flash('Inventory updated successfully!', 'success')
        return redirect(url_for('inventory.index'))
    
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('inventory/update.html', item=item)

# Made with Bob
