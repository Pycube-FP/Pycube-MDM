from flask import Blueprint, render_template, jsonify
from services.db_service import DBService
from routes.auth import login_required

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Render the dashboard page"""
    db_service = DBService()
    stats = db_service.get_statistics()
    
    return render_template('dashboard.html', stats=stats)

@dashboard_bp.route('/api/stats')
@login_required
def get_stats():
    """API endpoint to get dashboard statistics"""
    db_service = DBService()
    stats = db_service.get_statistics()
    
    return jsonify(stats) 