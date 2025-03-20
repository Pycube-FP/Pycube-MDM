from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from services.db_service import DBService
from models.device import Device
from datetime import datetime

devices_bp = Blueprint('devices', __name__, url_prefix='/devices')

@devices_bp.route('/')
def index():
    """Render the devices list page"""
    status_filter = request.args.get('status')
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    
    db_service = DBService()
    devices = db_service.get_all_devices(limit=limit, offset=offset, status=status_filter)
    
    return render_template('devices/index.html', devices=devices, current_page=page, status_filter=status_filter)

@devices_bp.route('/new', methods=['GET'])
def new():
    """Render the add device form"""
    db_service = DBService()
    locations = db_service.get_all_locations()
    
    return render_template('devices/new.html', locations=locations)

@devices_bp.route('/', methods=['POST'])
def create():
    """Create a new device"""
    try:
        # Get form data
        serial_number = request.form.get('serial_number')
        model = request.form.get('model')
        manufacturer = request.form.get('manufacturer')
        rfid_tag = request.form.get('rfid_tag')
        status = request.form.get('status', 'Available')
        location_id = request.form.get('location_id') or None
        assigned_to = request.form.get('assigned_to') or None
        purchase_date_str = request.form.get('purchase_date')
        maintenance_date_str = request.form.get('last_maintenance_date')
        
        # Parse dates
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        last_maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').date() if maintenance_date_str else None
        
        # Create device object
        device = Device(
            serial_number=serial_number,
            model=model,
            manufacturer=manufacturer,
            rfid_tag=rfid_tag,
            status=status,
            location_id=location_id,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date
        )
        
        # Save to database
        db_service = DBService()
        device_id = db_service.create_device(device)
        
        flash('Device created successfully', 'success')
        return redirect(url_for('devices.show', device_id=device_id))
    
    except Exception as e:
        flash(f'Error creating device: {str(e)}', 'error')
        return redirect(url_for('devices.new'))

@devices_bp.route('/<device_id>')
def show(device_id):
    """Show device details"""
    db_service = DBService()
    device_data = db_service.get_device(device_id)
    
    if not device_data:
        flash('Device not found', 'error')
        return redirect(url_for('devices.index'))
    
    # Get movement history
    movements = db_service.get_device_movements(device_id)
    
    return render_template('devices/show.html', device=device_data, movements=movements)

@devices_bp.route('/<device_id>/edit', methods=['GET'])
def edit(device_id):
    """Render the edit device form"""
    db_service = DBService()
    device_data = db_service.get_device(device_id)
    
    if not device_data:
        flash('Device not found', 'error')
        return redirect(url_for('devices.index'))
    
    locations = db_service.get_all_locations()
    
    return render_template('devices/edit.html', device=device_data, locations=locations)

@devices_bp.route('/<device_id>', methods=['POST'])
def update(device_id):
    """Update a device"""
    try:
        db_service = DBService()
        device_data = db_service.get_device(device_id)
        
        if not device_data:
            flash('Device not found', 'error')
            return redirect(url_for('devices.index'))
        
        # Get form data
        serial_number = request.form.get('serial_number')
        model = request.form.get('model')
        manufacturer = request.form.get('manufacturer')
        rfid_tag = request.form.get('rfid_tag')
        status = request.form.get('status')
        location_id = request.form.get('location_id') or None
        assigned_to = request.form.get('assigned_to') or None
        purchase_date_str = request.form.get('purchase_date')
        maintenance_date_str = request.form.get('last_maintenance_date')
        
        # Parse dates
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        last_maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').date() if maintenance_date_str else None
        
        # Create device object with updated values
        device = Device(
            id=device_id,
            serial_number=serial_number,
            model=model,
            manufacturer=manufacturer,
            rfid_tag=rfid_tag,
            status=status,
            location_id=location_id,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date
        )
        
        # Update in database
        success = db_service.update_device(device)
        
        if success:
            flash('Device updated successfully', 'success')
        else:
            flash('No changes made to device', 'info')
            
        return redirect(url_for('devices.show', device_id=device_id))
    
    except Exception as e:
        flash(f'Error updating device: {str(e)}', 'error')
        return redirect(url_for('devices.edit', device_id=device_id))

@devices_bp.route('/<device_id>/delete', methods=['POST'])
def delete(device_id):
    """Delete a device"""
    try:
        db_service = DBService()
        success = db_service.delete_device(device_id)
        
        if success:
            flash('Device deleted successfully', 'success')
        else:
            flash('Device not found', 'error')
            
        return redirect(url_for('devices.index'))
    
    except Exception as e:
        flash(f'Error deleting device: {str(e)}', 'error')
        return redirect(url_for('devices.show', device_id=device_id))

@devices_bp.route('/scan', methods=['POST'])
def scan_rfid():
    """Endpoint to handle RFID scan"""
    rfid_tag = request.json.get('rfid_tag')
    
    if not rfid_tag:
        return jsonify({'error': 'RFID tag not provided'}), 400
    
    db_service = DBService()
    device = db_service.get_device_by_rfid(rfid_tag)
    
    if device:
        return jsonify({'success': True, 'device': device})
    else:
        return jsonify({'success': False, 'error': 'Device not found'}), 404 