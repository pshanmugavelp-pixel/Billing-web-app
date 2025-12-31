# Business Management System

A comprehensive web-based application for managing customers, inventory, and billing operations with automatic inventory tracking, built using Flask and SQLite.

## Table of Contents
- [Overview](#overview)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Technical Implementation](#technical-implementation)
- [Tech Stack](#tech-stack)

## Overview

This application provides a complete business management solution with three core modules:
1. **Customer Management**: Maintain customer database with contact and GST information
2. **Inventory Management**: Track product stock, pricing, and expiry dates
3. **Billing System**: Create multi-item bills with automatic inventory deduction and GST calculation

The system uses a modular Flask Blueprint architecture with SQLite database for data persistence.

## Project Structure

```
Billing/
├── app.py                          # Main Flask application entry point
├── database.py                     # Database connection and schema management
├── requirements.txt                # Python dependencies
├── business.db                     # SQLite database file (auto-created)
├── routes/                         # Blueprint modules for routing
│   ├── __init__.py                # Routes package initializer
│   ├── customers.py               # Customer CRUD operations
│   ├── inventory.py               # Inventory CRUD operations
│   ├── billing.py                 # Billing operations with inventory tracking
│   └── admin.py                   # Admin panel for database management
└── templates/                      # Jinja2 HTML templates
    ├── dashboard.html             # Main dashboard/home page
    ├── customers/
    │   ├── index.html             # Customer list with search and bulk operations
    │   ├── add.html               # Add new customer form
    │   └── update.html            # Edit customer form
    ├── inventory/
    │   ├── index.html             # Inventory list with stock indicators
    │   ├── add.html               # Add new product form
    │   └── update.html            # Edit product form
    ├── billing/
    │   ├── index.html             # Bills list with payment status
    │   ├── create.html            # Create bill with multiple items
    │   ├── view.html              # View complete bill details
    │   └── update.html            # Edit existing bill
    └── admin/
        ├── index.html             # Admin dashboard
        └── view_table.html        # View table schema and data
```

## Architecture

### Flask Blueprint Structure
The application uses Flask Blueprints for modular organization:

- **Main App (`app.py`)**: Registers all blueprints and serves the dashboard
- **Customer Blueprint**: Handles all customer-related routes (`/customers/*`)
- **Inventory Blueprint**: Manages inventory operations (`/inventory/*`)
- **Billing Blueprint**: Processes billing with inventory integration (`/billing/*`)
- **Admin Blueprint**: Provides database management interface (`/admin/*`)

### Database Layer (`database.py`)
- **`get_db_connection()`**: Context manager for database connections with row_factory
- **`init_db()`**: Creates all tables if they don't exist
- **Schema Definitions**: SQL CREATE TABLE statements for all entities

### Template Inheritance
All templates extend a base layout with:
- Consistent navigation menu
- Responsive CSS styling
- JavaScript libraries (SheetJS for Excel export)
- Print-friendly CSS media queries

## Database Schema

### Table: `customers`
Stores customer information with unique identifiers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal database ID |
| customer_id | TEXT | UNIQUE NOT NULL | Business customer ID |
| vendor_code | TEXT | UNIQUE | Optional vendor code |
| name | TEXT | NOT NULL | Customer name |
| email | TEXT | | Email address |
| mobile | TEXT | | Mobile number |
| address | TEXT | | Physical address |
| state | TEXT | | State/region |
| gst_number | TEXT | | GST registration number |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration date |

**Validation Rules:**
- `customer_id` and `name` are mandatory
- `customer_id` and `vendor_code` must be unique

### Table: `inventory`
Tracks product stock, pricing, and expiry information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Internal database ID |
| product_id | TEXT | UNIQUE NOT NULL | Business product ID |
| product_name | TEXT | NOT NULL | Product name |
| hsn_code | TEXT | | HSN/SAC code for GST |
| manufacture_date | TEXT | | Manufacturing date |
| expiry_month | TEXT | NOT NULL | Expiry month (MM/YYYY) |
| quantity | INTEGER | NOT NULL | Current stock quantity |
| unit_price | REAL | NOT NULL | Price per unit (₹) |
| mrp | REAL | NOT NULL | Maximum retail price (₹) |
| gst_percentage | REAL | NOT NULL | GST percentage (e.g., 18.0) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation date |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update date |

**Validation Rules:**
- `product_id`, `product_name`, and `expiry_month` are mandatory
- `product_id` must be unique
- `quantity`, `unit_price`, `mrp`, and `gst_percentage` must be positive numbers

**Inventory Tracking:**
- Quantity automatically decreases when bills are created
- Quantity increases when bills are deleted
- Quantity adjusts when bills are updated

### Table: `billing`
Stores bill header information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Bill ID |
| customer_id | TEXT | FOREIGN KEY → customers(customer_id) | Reference to customer |
| bill_date | TEXT | NOT NULL | Bill date (YYYY-MM-DD) |
| subtotal | REAL | | Sum of all items before GST |
| gst_amount | REAL | | Total GST amount |
| total_amount | REAL | NOT NULL | Final bill amount (₹) |
| payment_status | TEXT | | Status: Paid/Pending/Partial |
| payment_method | TEXT | | Method: Cash/Card/UPI/Bank Transfer |
| notes | TEXT | | Additional notes |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation timestamp |

### Table: `billing_items`
Stores individual line items for each bill (one-to-many relationship).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Item ID |
| bill_id | INTEGER | FOREIGN KEY → billing(id) ON DELETE CASCADE | Reference to bill |
| product_id | TEXT | FOREIGN KEY → inventory(product_id) | Reference to product |
| product_name | TEXT | NOT NULL | Product name (snapshot) |
| quantity | INTEGER | NOT NULL | Quantity sold |
| unit_price | REAL | NOT NULL | Price per unit (₹) |
| subtotal | REAL | NOT NULL | quantity × unit_price |
| gst_percentage | REAL | NOT NULL | GST percentage |
| gst_amount | REAL | NOT NULL | GST amount for this item |
| total | REAL | NOT NULL | subtotal + gst_amount |

**Relationships:**
- Each bill can have multiple items (1:N)
- Deleting a bill cascades to delete all its items
- Items reference inventory for stock validation

## Features

### 1. Customer Management (`/customers/`)

**List Customers** (`GET /customers/`)
- Displays all customers in a table with ID column
- Search functionality (customer_id, vendor_code, name)
- Bulk selection with checkboxes
- Bulk delete operation
- Excel export (SheetJS)
- Print-friendly layout
- Actions: Edit, Delete

**Add Customer** (`GET/POST /customers/add`)
- Form with validation
- Required: customer_id, name
- Optional: vendor_code, email, mobile, address, state, gst_number
- Uniqueness check for customer_id and vendor_code
- Redirects to list on success

**Update Customer** (`GET/POST /customers/update/<customer_id>`)
- Pre-populated form with existing data
- Same validation as add
- Updates customer record

**Delete Customer** (`POST /customers/delete/<customer_id>`)
- Single customer deletion
- Redirects to list

**Bulk Delete** (`POST /customers/bulk-delete`)
- Accepts array of customer_ids
- Deletes multiple customers in one operation

### 2. Inventory Management (`/inventory/`)

**List Inventory** (`GET /inventory/`)
- Displays all products with ID column
- Shows: product_id, name, HSN, manufacture date, expiry, quantity, prices, GST%
- Low stock indicator (red text if quantity < 10)
- Bulk selection and delete
- Excel export
- Print functionality
- Actions: Edit, Delete

**Add Product** (`GET/POST /inventory/add`)
- Required: product_id, product_name, expiry_month, quantity, unit_price, mrp, gst_percentage
- Optional: hsn_code, manufacture_date
- Uniqueness check for product_id
- Numeric validation for prices and quantity

**Update Product** (`GET/POST /inventory/update/<product_id>`)
- Pre-populated form
- Same validation as add
- Updates product record and updated_at timestamp

**Delete Product** (`POST /inventory/delete/<product_id>`)
- Single product deletion

**Bulk Delete** (`POST /inventory/bulk-delete`)
- Deletes multiple products

### 3. Billing System (`/billing/`)

**List Bills** (`GET /billing/`)
- Displays all bills with ID column
- Shows: customer name, item count, bill date, total amount (₹), payment status, payment method
- Bulk selection and delete
- Excel export
- Print functionality
- Actions: View, Edit, Delete

**Create Bill** (`GET/POST /billing/create`)

*Frontend Flow:*
1. Customer Selection: Search and select customer (autocomplete)
2. Add Items Section:
   - Select product from dropdown (shows stock quantity)
   - Enter quantity (validates against stock)
   - Click "Add Item to Bill"
   - Item appears in items list with remove option
3. Bill Details: Enter bill date, payment status, method, notes
4. Real-time Calculations:
   - Subtotal = sum of all item subtotals
   - GST Amount = sum of all item GST amounts
   - Total = Subtotal + GST Amount
5. Submit button (validates at least one item)

*Backend Process:*
1. Receives customer_id, bill_date, payment details, and items array (JSON)
2. Validates all items have sufficient stock
3. Begins database transaction
4. Creates bill header record
5. Creates billing_items records for each item
6. Reduces inventory quantity for each product
7. Commits transaction
8. Redirects to bill list

**View Bill** (`GET /billing/view/<bill_id>`)
- Displays complete bill details
- Customer information section
- Bill information (date, payment status, method, notes)
- Items table with all products, quantities, prices, GST
- Totals summary (subtotal, GST, total)
- Print button for invoice

**Update Bill** (`GET/POST /billing/update/<bill_id>`)

*Frontend Flow:*
1. Loads existing bill data on page load
2. Pre-populates customer, items, and bill details
3. Allows adding/removing items
4. Real-time recalculation of totals
5. Submit updates

*Backend Process:*
1. Fetches existing bill and items
2. Restores inventory for old items (adds back quantities)
3. Validates new items have sufficient stock
4. Begins transaction
5. Deletes old billing_items
6. Updates bill header
7. Creates new billing_items
8. Reduces inventory for new items
9. Commits transaction

**Delete Bill** (`POST /billing/delete/<bill_id>`)
- Fetches all items for the bill
- Restores inventory quantities
- Deletes bill (cascades to items)

**Bulk Delete Bills** (`POST /billing/bulk-delete`)
- Processes multiple bills
- Restores inventory for all items
- Deletes all selected bills

### 4. Admin Panel (`/admin/`)

**Admin Dashboard** (`GET /admin/`)
- Lists all database tables
- Shows row count for each table
- Actions: View Schema, View Data, Reset Table

**View Table** (`GET /admin/view-table/<table_name>`)
- Displays table schema (columns, types, constraints)
- Shows all rows with data
- Delete row functionality
- Back to admin button

**Delete Row** (`POST /admin/delete-row/<table_name>/<row_id>`)
- Deletes specific row by ID

**Reset Table** (`POST /admin/reset-table/<table_name>`)
- Drops and recreates table (deletes all data)

## Installation

### Prerequisites
- Python 3.7+
- pip (Python package manager)

### Steps

1. **Clone or download the project**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Run the application:**
```bash
python app.py
```

4. **Access the application:**
Open browser and navigate to: `http://localhost:5000`

The database (`business.db`) will be created automatically on first run.

## Usage

### Customer Workflow
1. Navigate to "Customers" from dashboard
2. Click "Add New Customer"
3. Fill required fields (Customer ID, Name)
4. Add optional details (email, mobile, GST, etc.)
5. Submit to save
6. Use search to find customers
7. Edit or delete as needed
8. Use checkboxes for bulk operations
9. Export to Excel or print list

### Inventory Workflow
1. Navigate to "Inventory" from dashboard
2. Click "Add New Product"
3. Fill required fields (Product ID, Name, Expiry Month, Quantity, Prices, GST%)
4. Add optional details (HSN Code, Manufacture Date)
5. Submit to save
6. Monitor stock levels (red indicator for low stock)
7. Edit quantities and prices as needed
8. Export or print inventory list

### Billing Workflow

**Creating a Bill:**
1. Navigate to "Billing" from dashboard
2. Click "Create New Bill"
3. Search and select customer
4. Select product from dropdown
5. Enter quantity (system validates stock)
6. Click "Add Item to Bill"
7. Repeat for multiple items
8. Enter bill date and payment details
9. Review totals (auto-calculated)
10. Submit bill
11. System automatically reduces inventory

**Viewing a Bill:**
1. From billing list, click "View" button
2. See complete bill with all items
3. Print invoice if needed

**Editing a Bill:**
1. From billing list, click "Edit" button
2. Modify items, quantities, or payment details
3. System restores old inventory and adjusts for new items
4. Submit changes

**Deleting Bills:**
1. Single: Click "Delete" button on specific bill
2. Bulk: Select checkboxes and click "Delete Selected"
3. System automatically restores inventory quantities

## API Endpoints

### Customer API
- `GET /customers/api/customer/<customer_id>` - Returns customer JSON data

**Response:**
```json
{
  "customer_id": "CUST001",
  "name": "John Doe",
  "email": "john@example.com",
  "mobile": "9876543210",
  "address": "123 Main St",
  "state": "Maharashtra",
  "gst_number": "27XXXXX1234X1Z5"
}
```

### Inventory API
- `GET /billing/api/product/<product_id>` - Returns product JSON data

**Response:**
```json
{
  "product_id": "PROD001",
  "product_name": "Sample Product",
  "hsn_code": "1234",
  "manufacture_date": "01/2024",
  "expiry_month": "12/2025",
  "quantity": 100,
  "unit_price": 50.0,
  "mrp": 60.0,
  "gst_percentage": 18.0
}
```

## Technical Implementation

### Database Connection Management
- Uses context manager pattern for automatic connection cleanup
- Row factory set to `sqlite3.Row` for dict-like access
- All queries use parameterized statements to prevent SQL injection

### Transaction Handling
Billing operations use transactions to ensure data integrity:
```python
with get_db_connection() as conn:
    # Multiple operations
    conn.commit()  # All or nothing
```

### Inventory Tracking Algorithm

**On Bill Creation:**
1. Validate all items have sufficient stock
2. If any item insufficient, abort with error
3. Create bill and items in transaction
4. Reduce inventory: `UPDATE inventory SET quantity = quantity - ? WHERE product_id = ?`

**On Bill Update:**
1. Fetch old items
2. Restore inventory: `UPDATE inventory SET quantity = quantity + ? WHERE product_id = ?`
3. Validate new items
4. Update bill and create new items
5. Reduce inventory for new items

**On Bill Deletion:**
1. Fetch all items
2. Restore inventory for each item
3. Delete bill (cascades to items)

### Frontend JavaScript Features

**Dynamic Item Management:**
- Add/remove items without page reload
- Real-time total calculations
- Client-side validation before submission

**Search and Autocomplete:**
- Customer search with live filtering
- Product dropdown with stock display

**Excel Export (SheetJS):**
```javascript
// Convert table to workbook
var wb = XLSX.utils.table_to_book(table);
// Download as Excel file
XLSX.writeFile(wb, 'filename.xlsx');
```

**Print Functionality:**
- CSS media queries hide interactive elements
- `.no-print` class for buttons and checkboxes
- Print-optimized layout

### Form Validation

**Server-side (Python):**
- Required field checks
- Uniqueness validation
- Numeric range validation
- Foreign key validation

**Client-side (JavaScript):**
- HTML5 required attributes
- Pattern matching for formats
- Real-time feedback

### Error Handling
- Try-catch blocks for database operations
- Flash messages for user feedback
- Rollback on transaction failures
- Graceful error pages

## Tech Stack

### Backend
- **Python 3.x**: Programming language
- **Flask 2.x**: Web framework
- **SQLite3**: Embedded database

### Frontend
- **HTML5**: Markup
- **CSS3**: Styling with responsive design
- **JavaScript (ES6+)**: Client-side logic
- **SheetJS (xlsx.js)**: Excel file generation

### Architecture Patterns
- **MVC Pattern**: Separation of concerns
- **Blueprint Pattern**: Modular routing
- **Context Manager**: Resource management
- **Transaction Pattern**: Data integrity

### Development Tools
- **Jinja2**: Template engine
- **Werkzeug**: WSGI utilities (via Flask)

## Configuration

### Port
Default port: `5000`

To change port, modify `app.py`:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Change port here
```

### Database
Database file: `business.db` (created automatically)

Location: Same directory as `app.py`

### Debug Mode
Debug mode is enabled by default for development:
```python
app.run(debug=True)
```

Set to `False` for production deployment.

## Data Flow Examples

### Example 1: Creating a Bill with Multiple Items

**User Actions:**
1. Selects customer "CUST001"
2. Adds Product "PROD001" (qty: 5)
3. Adds Product "PROD002" (qty: 3)
4. Sets payment status: "Paid"
5. Submits form

**System Process:**
1. Frontend sends POST to `/billing/create` with JSON:
```json
{
  "customer_id": "CUST001",
  "bill_date": "2024-01-15",
  "payment_status": "Paid",
  "payment_method": "Cash",
  "items": [
    {"product_id": "PROD001", "quantity": 5},
    {"product_id": "PROD002", "quantity": 3}
  ]
}
```

2. Backend validates stock:
   - PROD001: current qty 100, requested 5 ✓
   - PROD002: current qty 50, requested 3 ✓

3. Calculates totals:
   - PROD001: 5 × ₹50 = ₹250, GST 18% = ₹45, Total = ₹295
   - PROD002: 3 × ₹30 = ₹90, GST 12% = ₹10.80, Total = ₹100.80
   - Bill Subtotal: ₹340
   - Bill GST: ₹55.80
   - Bill Total: ₹395.80

4. Creates records:
   - billing table: 1 row (bill header)
   - billing_items table: 2 rows (line items)

5. Updates inventory:
   - PROD001: 100 - 5 = 95
   - PROD002: 50 - 3 = 47

6. Commits transaction and redirects

### Example 2: Updating a Bill

**User Actions:**
1. Opens bill #5 for editing
2. Removes PROD001 (was qty: 5)
3. Adds PROD003 (qty: 2)
4. Keeps PROD002 (qty: 3)
5. Submits changes

**System Process:**
1. Fetches old items:
   - PROD001: qty 5
   - PROD002: qty 3

2. Restores inventory:
   - PROD001: 95 + 5 = 100
   - PROD002: 47 + 3 = 50

3. Validates new items:
   - PROD002: current 50, requested 3 ✓
   - PROD003: current 75, requested 2 ✓

4. Deletes old billing_items (2 rows)

5. Creates new billing_items (2 rows)

6. Updates inventory:
   - PROD002: 50 - 3 = 47
   - PROD003: 75 - 2 = 73

7. Updates bill header with new totals

8. Commits transaction

## Security Considerations

- **SQL Injection Prevention**: All queries use parameterized statements
- **Input Validation**: Server-side validation for all form inputs
- **Transaction Integrity**: ACID properties maintained for billing operations
- **Error Handling**: Graceful error messages without exposing system details

## Future Enhancements

Potential features for expansion:
- User authentication and role-based access
- Multi-currency support
- Advanced reporting and analytics
- Email notifications for low stock
- Barcode scanning integration
- PDF invoice generation
- Backup and restore functionality
- API for external integrations

## License

This project is for educational and business use.

## Support

For issues or questions, refer to the code comments and this documentation.