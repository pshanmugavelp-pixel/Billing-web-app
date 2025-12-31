"""
Inventory routes module
Handles all inventory-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')

@inventory_bp.route('/')
def index():
    """Display all inventory items"""
    conn = get_db_connection()
    items = conn.execute('SELECT * FROM inventory ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('inventory/index.html', items=items)

@inventory_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new inventory item"""
    if request.method == 'POST':
        product_id = request.form['product_id']
        product_name = request.form['product_name']
        hsn_code = request.form.get('hsn_code', '')
        manufacture_date = request.form.get('manufacture_date', '')
        expiry_month = request.form['expiry_month']
        quantity = request.form.get('quantity', 0)
        unit_price = request.form.get('unit_price', 0.0)
        mrp = request.form.get('mrp', 0.0)
        gst_percentage = request.form.get('gst_percentage', 0.0)
        
        if not product_id or not product_name or not expiry_month:
            flash('Product ID, Product Name, and Expiry Month are required!', 'error')
            return redirect(url_for('inventory.add'))
        
        conn = get_db_connection()
        
        # Check if product_id already exists
        existing = conn.execute('SELECT id FROM inventory WHERE product_id = ?', (product_id,)).fetchone()
        if existing:
            flash('Product ID already exists!', 'error')
            conn.close()
            return redirect(url_for('inventory.add'))
        
        conn.execute('''INSERT INTO inventory (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, unit_price, mrp, gst_percentage)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, unit_price, mrp, gst_percentage))
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
        hsn_code = request.form.get('hsn_code', '')
        manufacture_date = request.form.get('manufacture_date', '')
        expiry_month = request.form['expiry_month']
        quantity = request.form.get('quantity', 0)
        unit_price = request.form.get('unit_price', 0.0)
        mrp = request.form.get('mrp', 0.0)
        gst_percentage = request.form.get('gst_percentage', 0.0)
        
        if not product_id or not product_name or not expiry_month:
            flash('Product ID, Product Name, and Expiry Month are required!', 'error')
            conn.close()
            return redirect(url_for('inventory.update', id=id))
        
        # Check if product_id already exists (excluding current item)
        existing = conn.execute('SELECT id FROM inventory WHERE product_id = ? AND id != ?', (product_id, id)).fetchone()
        if existing:
            flash('Product ID already exists!', 'error')
            conn.close()
            return redirect(url_for('inventory.update', id=id))
        
        conn.execute('''UPDATE inventory SET product_id = ?, product_name = ?, hsn_code = ?, manufacture_date = ?,
                        expiry_month = ?, quantity = ?, unit_price = ?, mrp = ?, gst_percentage = ?,
                        updated_at = CURRENT_TIMESTAMP WHERE id = ?''',
                     (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, unit_price, mrp, gst_percentage, id))
        conn.commit()
        conn.close()
        
        flash('Inventory updated successfully!', 'success')
        return redirect(url_for('inventory.index'))
    
    item = conn.execute('SELECT * FROM inventory WHERE id = ?', (id,)).fetchone()
    conn.close()
    return render_template('inventory/update.html', item=item)

# Made with Bob
