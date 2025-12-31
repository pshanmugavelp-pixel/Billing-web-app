"""
Purchase routes module
Handles all purchase-related routes and inventory updates
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import get_db_connection
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__, url_prefix='/purchases')

@purchases_bp.route('/')
def index():
    """Display all purchases"""
    conn = get_db_connection()
    purchases = conn.execute('''
        SELECT * FROM purchases 
        ORDER BY purchase_date DESC, created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('purchases/index.html', purchases=purchases)

@purchases_bp.route('/add', methods=['GET', 'POST'])
def add():
    """Add a new purchase"""
    if request.method == 'POST':
        product_name = request.form['product_name'].strip()
        hsn_code = request.form.get('hsn_code', '').strip()
        manufacture_date = request.form['manufacture_date']  # Required now
        expiry_month = request.form['expiry_month'].strip()
        quantity = int(request.form['quantity'])
        buy_price = float(request.form['buy_price'])
        unit_price = float(request.form['unit_price'])
        mrp = float(request.form['mrp'])
        gst_percentage = float(request.form['gst_percentage'])
        purchase_date = request.form['purchase_date']
        
        if not product_name or not manufacture_date or not expiry_month or quantity <= 0:
            flash('Please fill in all required fields with valid values!', 'error')
            return redirect(url_for('purchases.add'))
        
        conn = get_db_connection()
        
        # Check if product exists in inventory by product_name AND manufacture_date
        existing_product = conn.execute(
            'SELECT * FROM inventory WHERE product_name = ? AND manufacture_date = ?',
            (product_name, manufacture_date)
        ).fetchone()
        
        if existing_product:
            # Show confirmation page with inventory update details
            conn.close()
            return render_template('purchases/add_confirm.html',
                                 product_name=product_name,
                                 hsn_code=hsn_code,
                                 manufacture_date=manufacture_date,
                                 expiry_month=expiry_month,
                                 quantity=quantity,
                                 buy_price=buy_price,
                                 unit_price=unit_price,
                                 mrp=mrp,
                                 gst_percentage=gst_percentage,
                                 purchase_date=purchase_date,
                                 existing_product=dict(existing_product))
        else:
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
            except Exception as e:
                conn.rollback()
                flash(f'Error adding purchase: {str(e)}', 'error')
            finally:
                conn.close()
            
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
    
    conn = get_db_connection()
    
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
    except Exception as e:
        conn.rollback()
        flash(f'Error processing purchase: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('purchases.index'))

@purchases_bp.route('/delete/<int:id>')
def delete(id):
    """Delete a purchase record"""
    conn = get_db_connection()
    
    # Get purchase details
    purchase = conn.execute('SELECT * FROM purchases WHERE id = ?', (id,)).fetchone()
    
    if not purchase:
        flash('Purchase not found!', 'error')
        conn.close()
        return redirect(url_for('purchases.index'))
    
    try:
        # Delete the purchase record
        conn.execute('DELETE FROM purchases WHERE id = ?', (id,))
        conn.commit()
        flash(f'Purchase record deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error deleting purchase: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('purchases.index'))

# Made with Bob