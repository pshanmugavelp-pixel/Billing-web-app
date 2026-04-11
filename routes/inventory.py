"""
Inventory routes module
Handles all inventory-related routes
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import db_connection
from datetime import datetime
from dateutil.relativedelta import relativedelta

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


def _build_inventory_index_context(*, search_query: str, page: int, per_page: int):
    """Build template context for inventory index + AJAX partial search."""
    # Validate per_page values
    if per_page not in [10, 20, 50, 100]:
        per_page = 20

    # Validate page number
    if page < 1:
        page = 1

    search_query = (search_query or '').strip()
    params = []
    where_clause = ''
    if search_query:
        like = f'%{search_query}%'
        where_clause = 'WHERE product_name LIKE ? OR hsn_code LIKE ?'
        params.extend([like, like])

    with db_connection() as conn:
        total_count = conn.execute(
            f'SELECT COUNT(*) as count FROM inventory {where_clause}',
            params,
        ).fetchone()['count']

        total_pages = max(1, (total_count + per_page - 1) // per_page) if total_count > 0 else 1
        if page > total_pages:
            page = total_pages

        offset = (page - 1) * per_page

        items = conn.execute(
            f'SELECT * FROM inventory {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (*params, per_page, offset),
        ).fetchall()

    has_prev = page > 1
    has_next = page < total_pages

    return {
        'items': items,
        'search_query': search_query,
        'page': page,
        'per_page': per_page,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
    }


@inventory_bp.route('/search')
def search_api():
    """AJAX endpoint: return filtered inventory table HTML + count for live search."""
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    context = _build_inventory_index_context(search_query=search_query, page=page, per_page=per_page)
    html = render_template('inventory/_items_table.html', **context)
    return jsonify({'html': html, 'total_count': context['total_count']})

@inventory_bp.route('/')
def index():
    """Display all inventory items with pagination and optional search"""
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    context = _build_inventory_index_context(search_query=search_query, page=page, per_page=per_page)
    return render_template('inventory/index.html', **context)

@inventory_bp.route('/api/products')
def api_products():
    """API endpoint to get all products for autocomplete"""
    with db_connection() as conn:
        products = conn.execute('SELECT * FROM inventory ORDER BY product_name').fetchall()

        # Convert to list of dict
        products_list = [dict(row) for row in products]
        return jsonify(products_list)

@inventory_bp.route('/api/next-product-id')
def next_product_id():
    """API endpoint to get the next auto-generated product ID"""
    with db_connection() as conn:
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

        return jsonify({'product_id': product_id})

@inventory_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new inventory item"""
    if request.method == 'POST':
        product_id = request.form.get('product_id', '').strip()
        
        # Auto-generate product_id if not provided or empty
        if not product_id:
            with db_connection() as conn:
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
        
        with db_connection() as conn:
            # Check if product_id already exists
            existing = conn.execute('SELECT id FROM inventory WHERE product_id = ?', (product_id,)).fetchone()
            if existing:
                flash('Product ID already exists!', 'error')
                return redirect(url_for('inventory.add'))

            conn.execute('''INSERT INTO inventory (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage))
            conn.commit()

            flash('Inventory item added successfully!', 'success')
            return redirect(url_for('inventory.index'))
    
    return render_template('inventory/add.html')

@inventory_bp.route('/delete/<int:id>')
def delete(id):
    """Delete an inventory item by ID"""
    with db_connection() as conn:
        # Check if product is used in any billing items
        billing_items = conn.execute('SELECT COUNT(*) as count FROM billing_items WHERE product_id = ?', (id,)).fetchone()
        if billing_items and billing_items['count'] > 0:
            flash(f'Cannot delete product! This product is used in {billing_items["count"]} billing item(s). Delete the bills first.', 'error')
            return redirect(url_for('inventory.index'))

        conn.execute('DELETE FROM inventory WHERE id = ?', (id,))
        conn.commit()

        flash('Inventory item deleted successfully!', 'success')
        return redirect(url_for('inventory.index'))

@inventory_bp.route('/delete-multiple', methods=['POST'])
def delete_multiple():
    """Delete multiple inventory items"""
    item_ids = request.form.getlist('item_ids[]')
    
    if not item_ids:
        flash('No items selected!', 'error')
        return redirect(url_for('inventory.index'))
    
    with db_connection() as conn:
        # Check if any selected products are used in billing items
        placeholders = ','.join('?' * len(item_ids))
        billing_items = conn.execute(f'SELECT COUNT(*) as count FROM billing_items WHERE product_id IN ({placeholders})', item_ids).fetchone()

        if billing_items and billing_items['count'] > 0:
            flash(f'Cannot delete! {billing_items["count"]} billing item(s) reference the selected product(s). Delete the bills first.', 'error')
            return redirect(url_for('inventory.index'))

        conn.execute(f'DELETE FROM inventory WHERE id IN ({placeholders})', item_ids)
        conn.commit()

        flash(f'{len(item_ids)} item(s) deleted successfully!', 'success')
        return redirect(url_for('inventory.index'))

@inventory_bp.route('/update/<int:id>', methods=['GET', 'POST'])
def update(id):
    """Update inventory item"""
    with db_connection() as conn:
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
                except Exception:
                    flash('Invalid manufacture date or expiry months!', 'error')
                    return redirect(url_for('inventory.update', id=id))

            if not product_id or not product_name or not hsn_code or not manufacture_date or not expiry_months:
                flash('Product ID, Product Name, HSN Code, Manufacture Date, and Expiry Months are required!', 'error')
                return redirect(url_for('inventory.update', id=id))

            # Check if product_id already exists (excluding current item)
            existing = conn.execute('SELECT id FROM inventory WHERE product_id = ? AND id != ?', (product_id, id)).fetchone()
            if existing:
                flash('Product ID already exists!', 'error')
                return redirect(url_for('inventory.update', id=id))

            conn.execute('''UPDATE inventory SET product_id = ?, product_name = ?, hsn_code = ?, manufacture_date = ?,
                            expiry_month = ?, quantity = ?, buy_price = ?, unit_price = ?, mrp = ?, gst_percentage = ?,
                            updated_at = CURRENT_TIMESTAMP WHERE id = ?''',
                         (product_id, product_name, hsn_code, manufacture_date, expiry_month, quantity, buy_price, unit_price, mrp, gst_percentage, id))
            conn.commit()

            flash('Inventory updated successfully!', 'success')
            return redirect(url_for('inventory.index'))

        item = conn.execute('SELECT * FROM inventory WHERE id = ?', (id,)).fetchone()
        return render_template('inventory/update.html', item=item)
