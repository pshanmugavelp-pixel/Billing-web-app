"""
Business Management System - Main Application
A comprehensive web-based application for managing customers, inventory, and billing
"""

from flask import Flask, render_template
from pathlib import Path
import shutil
from database import init_db
from routes.customers import customers_bp
from routes.inventory import inventory_bp
from routes.billing import billing_bp
from routes.admin import admin_bp
from routes.purchases import purchases_bp

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'


def _ensure_static_assets():
    base_dir = Path(__file__).resolve().parent

    src_seal = base_dir / 'Logo' / 'Company_Seal.jpeg'
    dst_dir = base_dir / 'static' / 'Logo'
    dst_seal = dst_dir / 'Company_Seal.jpeg'

    if not src_seal.exists():
        return

    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        if (not dst_seal.exists()) or (src_seal.stat().st_mtime > dst_seal.stat().st_mtime):
            shutil.copy2(src_seal, dst_seal)
    except OSError:
        # Non-fatal (e.g., read-only filesystem). Printing will simply not show the seal.
        return


_ensure_static_assets()

# Register blueprints
app.register_blueprint(customers_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(purchases_bp)

@app.route('/')
def dashboard():
    """Main dashboard with three sections"""
    return render_template('dashboard.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8080)
