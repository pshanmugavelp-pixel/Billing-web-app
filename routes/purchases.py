"""Purchase routes module
Handles all purchase-related routes and inventory updates
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from database import db_connection
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')


def _build_purchases_index_context(*, search_query: str, page: int, per_page: int):
    """Build template context for purchases index + AJAX partial search."""
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
        where_clause = 'WHERE product_name LIKE ? OR hsn_code LIKE ? OR purchase_date LIKE ?'
        params.extend([like, like, like])

    with db_connection() as conn:
        total_count = conn.execute(
            f'SELECT COUNT(*) as count FROM purchases {where_clause}',
            params,
        ).fetchone()['count']

        # Calculate pagination info
        total_pages = max(1, (total_count + per_page - 1) // per_page) if total_count > 0 else 1

        # Ensure page doesn't exceed total_pages
        if page > total_pages:
            page = total_pages

        # Calculate offset
        offset = (page - 1) * per_page

        purchases = conn.execute(
            f'''
            SELECT * FROM purchases
            {where_clause}
            ORDER BY purchase_date DESC, created_at DESC
            LIMIT ? OFFSET ?
            ''',
            (*params, per_page, offset),
        ).fetchall()

    has_prev = page > 1
    has_next = page < total_pages

    return {
        'purchases': purchases,
        'search_query': search_query,
        'page': page,
        'per_page': per_page,
        'total_count': total_count,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
    }


@purchases_bp.route('/search')
def search_api():
    """AJAX endpoint: return filtered purchases table HTML + count for live search."""
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    context = _build_purchases_index_context(search_query=search_query, page=page, per_page=per_page)
    html = render_template('purchases/_purchases_table.html', **context)
    return jsonify({'html': html, 'total_count': context['total_count']})

@purchases_bp.route('/')
def index():
    """Display all purchases with pagination and optional search"""
    search_query = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    context = _build_purchases_index_context(search_query=search_query, page=page, per_page=per_page)
    return render_template('purchases/index.html', **context)

@purchases_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new purchase"""
    if request.method == 'POST':
        product_name = request.form['product_name'].strip()
        hsn_code = request.form.get('hsn_code', '').strip()
        manufacture_month = request.form['manufacture_month']  # Format: YYYY-MM
        expiry_month = request.form['expiry_month'].strip()
        quantity = int(request.form['quantity'])
        buy_price = float(request.form['buy_price'])
        unit_price = float(request.form['unit_price'])
        mrp = float(request.form['mrp'])
        gst_percentage = float(request.form['gst_percentage'])
        purchase_date = request.form['purchase_date']
        
        if not product_name or not manufacture_month or not expiry_month or quantity <= 0:
            flash('Please fill in all required fields with valid values!', 'error')
            return redirect(url_for('purchases.add'))
        
        # Convert manufacture month to full date (1st of the month)
        from datetime import datetime
        manufacture_date = f"{manufacture_month}-01"  # YYYY-MM-01
        
        with db_connection() as conn:
            # Check if product exists in inventory by product_name AND manufacture_date
            existing_product = conn.execute(
                'SELECT * FROM inventory WHERE product_name = ? AND manufacture_date = ?',
                (product_name, manufacture_date)
            ).fetchone()

            if existing_product:
                # Show confirmation page with inventory update details
                return render_template('purchases/add_confirm.html',
                                     product_name=product_name,
                                     hsn_code=hsn_code,
                                     manufacture_month=manufacture_month,
                                     manufacture_date=manufacture_date,
                                     expiry_month=expiry_month,
                                     quantity=quantity,
                                     buy_price=buy_price,
                                     unit_price=unit_price,
                                     mrp=mrp,
                                     gst_percentage=gst_percentage,
                                     purchase_date=purchase_date,
                                     existing_product=dict(existing_product))

            # Product doesn't exist, generate product_id and add to both tables
            try:
                # Generate auto product_id
                last_product = conn.execute('SELECT product_id FROM inventory ORDER BY id DESC LIMIT 1').fetchone()
                if last_product and last_product['product_id']:
                    try:
                        # Extract number from last product_id (e.g., P001 -> 1)
                        last_num = int(last_product['product_id'][1:])
                        next_num = last_num + 1
                    except (ValueError, IndexError):
                        next_num = 1
                else:
                    next_num = 1
                product_id = f'P{next_num:03d}'  # Format as P001, P002, etc.

                # Add to purchases table
                conn.execute('''
                    INSERT INTO purchases (product_id, product_name, hsn_code, manufacture_date,
                                         expiry_month, quantity, buy_price, unit_price, mrp,
                                         gst_percentage, purchase_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, product_name, hsn_code, manufacture_date, expiry_month,
                      quantity, buy_price, unit_price, mrp, gst_percentage, purchase_date))

                # Add to inventory table
                conn.execute('''
                    INSERT INTO inventory (product_id, product_name, hsn_code, manufacture_date,
                                         expiry_month, quantity, buy_price, unit_price, mrp,
                                         gst_percentage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (product_id, product_name, hsn_code, manufacture_date, expiry_month,
                      quantity, buy_price, unit_price, mrp, gst_percentage))

                conn.commit()
                flash(f'New product "{product_name}" (ID: {product_id}) added to inventory with {quantity} units!', 'success')
            except Exception:
                conn.rollback()
                current_app.logger.exception('Error adding purchase for new product')
                flash('Could not add the purchase. Please try again.', 'error')

            return redirect(url_for('purchases.index'))
    
    # GET request - show form
    return render_template('purchases/add.html')

@purchases_bp.route('/confirm-add', methods=['POST'])
def confirm_add():
    """Confirm and process purchase with inventory update"""
    existing_product_id = request.form['existing_product_id']
    product_name = request.form['product_name']
    hsn_code = request.form.get('hsn_code', '')
    manufacture_date = request.form['manufacture_date']
    expiry_month = request.form['expiry_month']
    quantity = int(request.form['quantity'])
    buy_price = float(request.form['buy_price'])
    unit_price = float(request.form['unit_price'])
    mrp = float(request.form['mrp'])
    gst_percentage = float(request.form['gst_percentage'])
    purchase_date = request.form['purchase_date']
    
    with db_connection() as conn:
        try:
            # Add to purchases table (use existing product_id)
            conn.execute('''
                INSERT INTO purchases (product_id, product_name, hsn_code, manufacture_date,
                                     expiry_month, quantity, buy_price, unit_price, mrp,
                                     gst_percentage, purchase_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (existing_product_id, product_name, hsn_code, manufacture_date, expiry_month,
                  quantity, buy_price, unit_price, mrp, gst_percentage, purchase_date))

            # Update inventory quantity by product_name and manufacture_date
            conn.execute('''
                UPDATE inventory
                SET quantity = quantity + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ? AND manufacture_date = ?
            ''', (quantity, product_name, manufacture_date))

            conn.commit()
            flash(f'Purchase recorded! Added {quantity} units of "{product_name}" to inventory.', 'success')
        except Exception:
            conn.rollback()
            current_app.logger.exception('Error processing purchase confirm-add')
            flash('Could not process the purchase. Please try again.', 'error')
    
    return redirect(url_for('purchases.index'))

@purchases_bp.route('/delete/<int:id>')
def delete(id):
    """Delete a purchase record"""
    with db_connection() as conn:
        # Get purchase details
        purchase = conn.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()

        if not purchase:
            flash('Purchase not found!', 'error')
            return redirect(url_for('purchases.index'))

        try:
            # Delete the purchase record
            conn.execute('DELETE FROM purchases WHERE id = ?', (id,))
            conn.commit()
            flash(f'Purchase record deleted successfully!', 'success')
        except Exception:
            conn.rollback()
            current_app.logger.exception('Error deleting purchase id=%s', id)
            flash('Could not delete the purchase record. Please try again.', 'error')

        return redirect(url_for('purchases.index'))
