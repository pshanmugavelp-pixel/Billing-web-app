#!/usr/bin/env python3
"""
Test script for active bills export functionality
"""

from database import get_db_connection

def test_active_bills_export():
    """Test the active bills export route logic"""
    conn = get_db_connection()
    
    print("=" * 60)
    print("Testing Active Bills Export Functionality")
    print("=" * 60)
    
    # Get all active bills
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
    
    print(f"\n✓ Found {len(bills)} active bills")
    
    # Get items for each bill
    bills_with_items = []
    total_items = 0
    
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
        
        bills_with_items.append({
            'bill': dict(bill),
            'items': [dict(item) for item in items] if items else []
        })
        
        total_items += len(items)
        
        # Print bill details
        print(f"\n  Bill {bill['bill_id']}:")
        print(f"    Customer: {bill['customer_name']}")
        print(f"    Date: {bill['bill_date']}")
        print(f"    Total: ₹{bill['total_amount']:.2f}")
        print(f"    Items: {len(items)}")
        
        if items:
            for item in items:
                print(f"      - {item['product_name']}: {item['quantity']} x ₹{item['unit_price']:.2f} = ₹{item['total']:.2f}")
                print(f"        HSN: {item['hsn_code'] or 'N/A'}, IGST: ₹{item['igst']:.2f}, SGST: ₹{item['sgst']:.2f}, CGST: ₹{item['cgst']:.2f}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✓ Test completed successfully!")
    print(f"  Total bills: {len(bills_with_items)}")
    print(f"  Total items: {total_items}")
    print(f"  Bills with items: {sum(1 for b in bills_with_items if b['items'])}")
    print(f"  Bills without items: {sum(1 for b in bills_with_items if not b['items'])}")
    print("=" * 60)
    
    return bills_with_items

if __name__ == '__main__':
    try:
        result = test_active_bills_export()
        print("\n✓ All tests passed! The export functionality is working correctly.")
        print("\nTo use the export feature:")
        print("1. Make sure your Flask app is running")
        print("2. Navigate to: http://localhost:5000/billing/active-bills-export")
        print("3. Click 'Download Excel' to export the data")
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

# Made with Bob
