from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from services.db_service import DBService
from models.hospital import Hospital
from routes.auth import login_required, role_required
from datetime import datetime

hospitals_bp = Blueprint('hospitals', __name__, url_prefix='/hospitals')

@hospitals_bp.route('/')
@login_required
@role_required(['admin'])
def index():
    """List all hospitals"""
    db_service = DBService()
    
    # Get sort parameters from request
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    hospitals = db_service.get_all_hospitals(sort_by=sort_by, sort_dir=sort_dir)
    return render_template('hospitals/index.html', 
                         hospitals=hospitals,
                         sort_by=sort_by,
                         sort_dir=sort_dir)

@hospitals_bp.route('/create', methods=['GET', 'POST'])
@role_required(['admin'])
def create():
    """Create a new hospital"""
    if request.method == 'POST':
        try:
            hospital_data = {
                'name': request.form['name'],
                'code': request.form['code'],
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'zip_code': request.form.get('zip_code'),
                'status': request.form.get('status', 'Active')
            }
            
            hospital = Hospital.from_dict(hospital_data)
            db_service = DBService()
            db_service.create_hospital(hospital)
            
            flash('Hospital created successfully', 'success')
            return redirect(url_for('hospitals.index'))
            
        except Exception as e:
            flash(f'Error creating hospital: {str(e)}', 'error')
            return render_template('hospitals/create.html')
    
    return render_template('hospitals/create.html')

@hospitals_bp.route('/<hospital_id>')
@login_required
def show(hospital_id):
    """Show hospital details"""
    db_service = DBService()
    hospital = db_service.get_hospital(hospital_id)
    
    if not hospital:
        flash('Hospital not found', 'error')
        return redirect(url_for('hospitals.index'))
    
    # Get hospital statistics
    stats = db_service.get_hospital_statistics(hospital_id)
    
    return render_template('hospitals/show.html', 
                         hospital=hospital,
                         stats=stats)

@hospitals_bp.route('/<hospital_id>/edit', methods=['GET', 'POST'])
@role_required(['admin'])
def edit(hospital_id):
    """Edit hospital details"""
    db_service = DBService()
    hospital = db_service.get_hospital(hospital_id)
    
    if not hospital:
        flash('Hospital not found', 'error')
        return redirect(url_for('hospitals.index'))
    
    if request.method == 'POST':
        try:
            hospital_data = {
                'id': hospital_id,
                'name': request.form['name'],
                'code': request.form['code'],
                'address': request.form.get('address'),
                'city': request.form.get('city'),
                'state': request.form.get('state'),
                'zip_code': request.form.get('zip_code'),
                'status': request.form.get('status')
            }
            
            hospital = Hospital.from_dict(hospital_data)
            db_service.update_hospital(hospital)
            
            flash('Hospital updated successfully', 'success')
            return redirect(url_for('hospitals.show', hospital_id=hospital_id))
            
        except Exception as e:
            flash(f'Error updating hospital: {str(e)}', 'error')
    
    return render_template('hospitals/edit.html', hospital=hospital)

@hospitals_bp.route('/<hospital_id>/readers')
@login_required
def readers(hospital_id):
    """Show hospital's readers"""
    db_service = DBService()
    hospital = db_service.get_hospital(hospital_id)
    
    if not hospital:
        flash('Hospital not found', 'error')
        return redirect(url_for('hospitals.index'))
    
    readers = db_service.get_hospital_readers(hospital_id)
    return render_template('hospitals/readers.html',
                         hospital=hospital,
                         readers=readers)

# API Endpoints
@hospitals_bp.route('/api/list')
@login_required
def api_list():
    """API endpoint to get all hospitals"""
    try:
        db_service = DBService()
        hospitals = db_service.get_all_hospitals()
        return jsonify([hospital.to_dict() for hospital in hospitals])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hospitals_bp.route('/api/<hospital_id>/readers')
@login_required
def api_readers(hospital_id):
    """API endpoint to get hospital's readers"""
    try:
        db_service = DBService()
        readers = db_service.get_hospital_readers(hospital_id)
        return jsonify([reader.to_dict() for reader in readers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hospitals_bp.route('/api/<hospital_id>/stats')
@login_required
def api_stats(hospital_id):
    """API endpoint to get hospital statistics"""
    try:
        db_service = DBService()
        stats = db_service.get_hospital_statistics(hospital_id)
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500 