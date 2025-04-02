from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from services.db_service import DBService
from models.reader import Reader
from routes.auth import login_required, role_required
from datetime import datetime

readers_bp = Blueprint('readers', __name__, url_prefix='/readers')

@readers_bp.route('/')
@login_required
@role_required(['admin'])
def index():
    """List all readers"""
    db_service = DBService()
    
    # Get sort parameters from request
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    # Get pagination parameters
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    
    # Get total count and calculate total pages
    total_count = db_service.get_reader_count()
    total_pages = (total_count + limit - 1) // limit  # Ceiling division
    
    readers = db_service.get_all_readers(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir
    )
    
    return render_template(
        'readers/index.html', 
        readers=readers,
        current_page=page,
        total_pages=total_pages,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

@readers_bp.route('/create', methods=['GET', 'POST'])
@role_required(['admin'])
def create():
    """Create a new reader"""
    db_service = DBService()
    hospitals = db_service.get_all_hospitals()
    locations = db_service.get_all_locations()
    
    if request.method == 'POST':
        try:
            reader_data = {
                'reader_code': request.form['reader_code'],
                'antenna_number': int(request.form['antenna_number']),
                'name': request.form['name'] or f"{request.form['reader_code']} - Antenna {request.form['antenna_number']}",
                'hospital_id': request.form['hospital_id'],
                'location_id': request.form['location_id'],
                'status': request.form.get('status', 'Active'),
                'last_heartbeat': None
            }
            
            # Check if reader code and antenna number combination already exists
            existing = db_service.get_reader_by_code_and_antenna(
                reader_data['reader_code'], 
                reader_data['antenna_number']
            )
            if existing:
                flash('A reader with this code and antenna number already exists', 'error')
                return render_template('readers/create.html',
                                    hospitals=hospitals,
                                    locations=locations)
            
            reader = Reader.from_dict(reader_data)
            db_service.create_reader(reader)
            
            flash('Reader created successfully', 'success')
            return redirect(url_for('readers.index'))
            
        except Exception as e:
            flash(f'Error creating reader: {str(e)}', 'error')
            return render_template('readers/create.html',
                                hospitals=hospitals,
                                locations=locations)
    
    return render_template('readers/create.html',
                         hospitals=hospitals,
                         locations=locations)

@readers_bp.route('/<reader_id>')
@login_required
def show(reader_id):
    """Show reader details"""
    db_service = DBService()
    reader = db_service.get_reader(reader_id)
    
    if not reader:
        flash('Reader not found', 'error')
        return redirect(url_for('readers.index'))
    
    # Get reader statistics and recent events
    stats = db_service.get_reader_statistics(reader_id)
    events = db_service.get_reader_events(reader_id, limit=10)
    
    return render_template('readers/show.html',
                         reader=reader,
                         stats=stats,
                         events=events)

@readers_bp.route('/<reader_id>/edit', methods=['GET', 'POST'])
@role_required(['admin'])
def edit(reader_id):
    """Edit reader details"""
    db_service = DBService()
    reader = db_service.get_reader(reader_id)
    
    if not reader:
        flash('Reader not found', 'error')
        return redirect(url_for('readers.index'))
    
    hospitals = db_service.get_all_hospitals()
    locations = db_service.get_all_locations()
    
    if request.method == 'POST':
        try:
            new_reader_code = request.form['reader_code']
            new_antenna_number = int(request.form['antenna_number'])
            
            # Check if the new reader code and antenna number combination exists
            # (but ignore if it's the same reader we're editing)
            existing = db_service.get_reader_by_code_and_antenna(
                new_reader_code, 
                new_antenna_number
            )
            if existing and existing['id'] != reader_id:
                flash('A reader with this code and antenna number already exists', 'error')
                return render_template('readers/edit.html',
                                    reader=reader,
                                    hospitals=hospitals,
                                    locations=locations)
            
            reader_data = {
                'id': reader_id,
                'reader_code': new_reader_code,
                'antenna_number': new_antenna_number,
                'name': request.form['name'] or f"{new_reader_code} - Antenna {new_antenna_number}",
                'hospital_id': request.form['hospital_id'],
                'location_id': request.form['location_id'],
                'status': request.form.get('status'),
                'last_heartbeat': reader['last_heartbeat']
            }
            
            reader = Reader.from_dict(reader_data)
            db_service.update_reader(reader)
            
            flash('Reader updated successfully', 'success')
            return redirect(url_for('readers.show', reader_id=reader_id))
            
        except Exception as e:
            flash(f'Error updating reader: {str(e)}', 'error')
    
    return render_template('readers/edit.html',
                         reader=reader,
                         hospitals=hospitals,
                         locations=locations)

@readers_bp.route('/<reader_id>/events')
@login_required
def events(reader_id):
    """Show reader events"""
    db_service = DBService()
    reader = db_service.get_reader(reader_id)
    
    if not reader:
        flash('Reader not found', 'error')
        return redirect(url_for('readers.index'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    events = db_service.get_reader_events(reader_id, page=page, per_page=per_page)
    
    return render_template('readers/events.html',
                         reader=reader,
                         events=events,
                         page=page,
                         per_page=per_page)

# API Endpoints
@readers_bp.route('/api/list')
@login_required
def api_list():
    """API endpoint to get all readers"""
    try:
        db_service = DBService()
        readers = db_service.get_all_readers()
        return jsonify([reader.to_dict() for reader in readers])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readers_bp.route('/api/<reader_id>')
@login_required
def api_show(reader_id):
    """API endpoint to get reader details"""
    try:
        db_service = DBService()
        reader = db_service.get_reader(reader_id)
        if not reader:
            return jsonify({'error': 'Reader not found'}), 404
        return jsonify(reader.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readers_bp.route('/api/<reader_id>/events')
@login_required
def api_events(reader_id):
    """API endpoint to get reader events"""
    try:
        db_service = DBService()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        events = db_service.get_reader_events(reader_id, page=page, per_page=per_page)
        return jsonify([event.to_dict() for event in events])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@readers_bp.route('/api/<reader_id>/heartbeat', methods=['POST'])
def api_heartbeat(reader_id):
    """API endpoint for reader heartbeat"""
    try:
        db_service = DBService()
        reader = db_service.get_reader(reader_id)
        if not reader:
            return jsonify({'error': 'Reader not found'}), 404
            
        reader.last_heartbeat = datetime.utcnow()
        db_service.update_reader(reader)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 