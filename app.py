"""
Business Management System - Main Application
A comprehensive web-based application for managing customers, inventory, and billing
"""

from flask import Flask, render_template
from database import init_db
from routes.customers import customers_bp
from routes.inventory import inventory_bp
from routes.billing import billing_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Register blueprints
app.register_blueprint(customers_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(admin_bp)

@app.route('/')
def dashboard():
    """Main dashboard with three sections"""
    return render_template('dashboard.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8080)

# Made with Bob
