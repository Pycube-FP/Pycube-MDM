from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from services.db_service import DBService
from routes.auth import login_required
from models.nurse import Nurse

nurses_bp = Blueprint('nurses', __name__, url_prefix='/nurses')

@nurses_bp.route('/')
@login_required
def index():
    """List all nurses"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        
        # Get sort parameters from request
        sort_by = request.args.get('sort_by')
        sort_dir = request.args.get('sort_dir', 'asc')
        
        db_service = DBService()
        
        # Get total count and calculate total pages
        total_count = db_service.get_nurse_count()
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        nurses = db_service.get_all_nurses(limit=per_page, offset=offset, sort_by=sort_by, sort_dir=sort_dir)
        return render_template(
            'nurses/index.html', 
            nurses=nurses, 
            current_page=page, 
            total_pages=total_pages,
            sort_by=sort_by, 
            sort_dir=sort_dir
        )
    except Exception as e:
        flash(f'Error loading nurses: {str(e)}', 'error')
        return redirect(url_for('dashboard.index'))

@nurses_bp.route('/<nurse_id>')
@login_required
def show(nurse_id):
    """Show nurse details"""
    try:
        db_service = DBService()
        nurse = db_service.get_nurse(nurse_id)
        if not nurse:
            flash('Nurse not found', 'error')
            return redirect(url_for('nurses.index'))
        
        assignments = db_service.get_nurse_assignments(nurse_id)
        return render_template('nurses/show.html', nurse=nurse, assignments=assignments)
    except Exception as e:
        flash(f'Error loading nurse details: {str(e)}', 'error')
        return redirect(url_for('nurses.index'))

@nurses_bp.route('/new')
@login_required
def new():
    """Show new nurse form"""
    return render_template('nurses/new.html')

@nurses_bp.route('/', methods=['POST'])
@login_required
def create():
    """Create a new nurse"""
    try:
        # Create a new Nurse object
        nurse = Nurse(
            badge_id=request.form['badge_id'],
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            department=request.form['department'],
            shift=request.form['shift']
        )
        
        db_service = DBService()
        nurse_id = db_service.create_nurse(nurse)
        
        flash('Nurse created successfully', 'success')
        return redirect(url_for('nurses.show', nurse_id=nurse_id))
    except Exception as e:
        flash(f'Error creating nurse: {str(e)}', 'error')
        return redirect(url_for('nurses.new'))

@nurses_bp.route('/<nurse_id>/edit')
@login_required
def edit(nurse_id):
    """Show edit nurse form"""
    try:
        db_service = DBService()
        nurse = db_service.get_nurse(nurse_id)
        if not nurse:
            flash('Nurse not found', 'error')
            return redirect(url_for('nurses.index'))
        
        return render_template('nurses/edit.html', nurse=nurse)
    except Exception as e:
        flash(f'Error loading nurse: {str(e)}', 'error')
        return redirect(url_for('nurses.index'))

@nurses_bp.route('/<nurse_id>', methods=['POST'])
@login_required
def update(nurse_id):
    """Update a nurse"""
    try:
        nurse_data = {
            'first_name': request.form['first_name'],
            'last_name': request.form['last_name'],
            'badge_id': request.form['badge_id'],
            'department': request.form['department'],
            'shift': request.form['shift'],
            'email': request.form.get('email'),
            'phone': request.form.get('phone')
        }
        
        db_service = DBService()
        db_service.update_nurse(nurse_id, nurse_data)
        
        flash('Nurse updated successfully', 'success')
        return redirect(url_for('nurses.show', nurse_id=nurse_id))
    except Exception as e:
        flash(f'Error updating nurse: {str(e)}', 'error')
        return redirect(url_for('nurses.edit', nurse_id=nurse_id))

@nurses_bp.route('/<nurse_id>/delete', methods=['POST'])
@login_required
def delete(nurse_id):
    """Delete a nurse"""
    try:
        db_service = DBService()
        db_service.delete_nurse(nurse_id)
        flash('Nurse deleted successfully', 'success')
        return redirect(url_for('nurses.index'))
    except Exception as e:
        flash(f'Error deleting nurse: {str(e)}', 'error')
        return redirect(url_for('nurses.show', nurse_id=nurse_id))

@nurses_bp.route('/lookup/<badge_id>')
@login_required
def lookup_by_badge(badge_id):
    """Look up a nurse by their badge ID"""
    try:
        db_service = DBService()
        nurse = db_service.get_nurse_by_badge(badge_id)
        
        if nurse:
            return jsonify({
                'success': True,
                'nurse': nurse
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Nurse not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@nurses_bp.route('/api/list')
@login_required
def api_list():
    """API endpoint for fetching paginated nurses data"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 10
        offset = (page - 1) * per_page
        
        # Get sort parameters from request
        sort_by = request.args.get('sort_by')
        sort_dir = request.args.get('sort_dir', 'asc')
        
        db_service = DBService()
        
        # Get total count and calculate total pages
        total_count = db_service.get_nurse_count()
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        nurses = db_service.get_all_nurses(limit=per_page, offset=offset, sort_by=sort_by, sort_dir=sort_dir)
        
        # Convert datetime objects to strings for JSON serialization
        for nurse in nurses:
            if nurse.get('created_at'):
                nurse['created_at'] = nurse['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if nurse.get('updated_at'):
                nurse['updated_at'] = nurse['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify({
            'nurses': nurses,
            'current_page': page,
            'total_pages': total_pages,
            'total_count': total_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 