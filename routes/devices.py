from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from services.db_service import DBService
from models.device import Device
from routes.auth import login_required, role_required, api_auth_required
from datetime import datetime
import uuid
import re

devices_bp = Blueprint('devices', __name__, url_prefix='/devices')

def calculate_iphone_compliance(model):
    """Calculate compliance percentage for iPhone models"""
    # Extract iPhone model number using regex
    model_match = re.search(r'iPhone (\d+)', model, re.IGNORECASE)
    if not model_match:
        return None
    
    model_number = int(model_match.group(1))
    
    # Define iPhone model compliance ranges
    # Based on current iOS support and lifecycle
    if model_number >= 15:  # Latest models
        return 20  # Early in lifecycle
    elif model_number >= 13:  # Recent models
        return 40  # Active support
    elif model_number >= 11:  # Mid-range models
        return 60  # Mid lifecycle
    elif model_number >= 8:  # Aging models
        return 80  # Limited support
    else:  # Old models
        return 100  # End of life

@devices_bp.route('/')
@login_required
def index():
    """Render the devices list page"""
    status_filter = request.args.get('status')
    search_query = request.args.get('search')
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    
    # Get sort parameters from request
    sort_by = request.args.get('sort_by')
    sort_dir = request.args.get('sort_dir', 'asc')
    
    db_service = DBService()
    
    # Get total count and calculate total pages
    total_count = db_service.get_device_count(status=status_filter, search_query=search_query)
    total_pages = (total_count + limit - 1) // limit  # Ceiling division
    
    devices = db_service.get_all_devices(
        limit=limit, 
        offset=offset, 
        status=status_filter,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search_query=search_query
    )
    
    return render_template(
        'devices/index.html', 
        devices=devices, 
        current_page=page,
        total_pages=total_pages,
        status_filter=status_filter,
        search_query=search_query,
        sort_by=sort_by,
        sort_dir=sort_dir
    )

@devices_bp.route('/new', methods=['GET'])
@login_required
def new():
    """Render the add device form"""
    db_service = DBService()
    locations = db_service.get_all_locations()
    hospitals = db_service.get_all_hospitals()
    
    return render_template('devices/new.html', 
                         locations=locations,
                         hospitals=hospitals)

@devices_bp.route('/', methods=['POST'])
@login_required
def create():
    """Create a new device"""
    try:
        # Get form data
        serial_number = request.form.get('serial_number')
        model = request.form.get('model')
        manufacturer = request.form.get('manufacturer')
        rfid_tag = request.form.get('rfid_tag')
        status = request.form.get('status', 'Available')
        hospital_id = request.form.get('hospital_id')
        location_id = request.form.get('location_id')
        assigned_to = request.form.get('assigned_to')
        purchase_date_str = request.form.get('purchase_date')
        maintenance_date_str = request.form.get('last_maintenance_date')
        eol_date_str = request.form.get('eol_date')
        eol_status = request.form.get('eol_status', 'Active')
        eol_notes = request.form.get('eol_notes')
        
        # Parse dates
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else None
        last_maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').date() if maintenance_date_str else None
        eol_date = datetime.strptime(eol_date_str, '%Y-%m-%d').date() if eol_date_str else None
        
        # Create device object
        device = Device(
            serial_number=serial_number,
            model=model,
            manufacturer=manufacturer,
            rfid_tag=rfid_tag,
            status=status,
            hospital_id=hospital_id,
            location_id=location_id,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date,
            eol_date=eol_date,
            eol_status=eol_status,
            eol_notes=eol_notes
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
@login_required
def show(device_id):
    """Display device details"""
    db_service = DBService()
    device_data = db_service.get_device(device_id)
    
    if not device_data:
        flash('Device not found', 'error')
        return redirect(url_for('devices.index'))
    
    # Get movement history from rfid_alerts table (shows status transitions)
    movements = db_service.get_device_movement_history(device_id)
    
    # Get assignment history
    assignments = db_service.get_device_assignments(device_id)
    
    # Calculate compliance percentage for iPhones
    compliance_percent = None
    if device_data['manufacturer'].lower() == 'apple' and 'iphone' in device_data['model'].lower():
        compliance_percent = calculate_iphone_compliance(device_data['model'])
    
    return render_template('devices/show.html', 
                         device=device_data, 
                         movements=movements,
                         assignments=assignments,
                         compliance_percent=compliance_percent)

@devices_bp.route('/<device_id>/edit', methods=['GET'])
@login_required
def edit(device_id):
    """Render the edit device form"""
    db_service = DBService()
    device_data = db_service.get_device(device_id)
    
    if not device_data:
        flash('Device not found', 'error')
        return redirect(url_for('devices.index'))
    
    locations = db_service.get_all_locations()
    hospitals = db_service.get_all_hospitals()
    
    return render_template('devices/edit.html', 
                         device=device_data, 
                         locations=locations,
                         hospitals=hospitals)

@devices_bp.route('/<device_id>', methods=['POST'])
@login_required
def update(device_id):
    """Update a device"""
    try:
        db_service = DBService()
        existing_device = db_service.get_device(device_id)
        
        if not existing_device:
            flash('Device not found', 'error')
            return redirect(url_for('devices.index'))
        
        # Get form data, using existing values as defaults
        serial_number = request.form.get('serial_number', existing_device['serial_number'])
        model = request.form.get('model', existing_device['model'])
        manufacturer = request.form.get('manufacturer', existing_device['manufacturer'])
        rfid_tag = request.form.get('rfid_tag', existing_device['rfid_tag'])
        status = request.form.get('status', existing_device['status'])
        hospital_id = request.form.get('hospital_id') if request.form.get('hospital_id') else existing_device['hospital_id']
        location_id = request.form.get('location_id') if request.form.get('location_id') else existing_device['location_id']
        assigned_to = request.form.get('assigned_to') if request.form.get('assigned_to') else existing_device['assigned_to']
        purchase_date_str = request.form.get('purchase_date')
        maintenance_date_str = request.form.get('last_maintenance_date')
        eol_date_str = request.form.get('eol_date')
        eol_status = request.form.get('eol_status', existing_device.get('eol_status', 'Active'))
        eol_notes = request.form.get('eol_notes', existing_device.get('eol_notes'))
        
        # Parse dates, keeping existing values if not provided
        if purchase_date_str:
            purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()
        else:
            purchase_date = existing_device['purchase_date']
            
        if maintenance_date_str:
            last_maintenance_date = datetime.strptime(maintenance_date_str, '%Y-%m-%d').date()
        else:
            last_maintenance_date = existing_device['last_maintenance_date']

        if eol_date_str:
            eol_date = datetime.strptime(eol_date_str, '%Y-%m-%d').date()
        else:
            eol_date = existing_device.get('eol_date')
        
        # Create device object with updated values
        device = Device(
            id=device_id,
            serial_number=serial_number,
            model=model,
            manufacturer=manufacturer,
            rfid_tag=rfid_tag,
            barcode=existing_device['barcode'],  # Preserve existing barcode
            status=status,
            hospital_id=hospital_id,
            location_id=location_id,
            assigned_to=assigned_to,
            purchase_date=purchase_date,
            last_maintenance_date=last_maintenance_date,
            eol_date=eol_date,
            eol_status=eol_status,
            eol_notes=eol_notes
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
@login_required
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
@login_required
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

@devices_bp.route('/lookup/<barcode>')
@login_required
def lookup_by_barcode(barcode):
    """Look up a device by its barcode"""
    try:
        db_service = DBService()
        device = db_service.get_device_by_barcode(barcode)
        
        if device:
            # Add assigned_to_name to match what's displayed
            device['assigned_to_name'] = device['assigned_to']
            
            return jsonify({
                'success': True,
                'device': device
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Device not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@devices_bp.route('/api/list')
def api_list_devices():
    """API endpoint to get all devices"""
    try:
        db_service = DBService()
        devices = db_service.get_all_devices()
        
        # Convert devices to JSON format
        devices_json = []
        for device in devices:
            devices_json.append({
                'id': device['id'],
                'serialNumber': device['serial_number'],
                'model': device['model'],
                'manufacturer': device['manufacturer'],
                'rfidTag': device['rfid_tag'],
                'barcode': device['barcode'],
                'status': device['status'],
                'assignedTo': device['assigned_to'],
                'locationId': device['location_id'],
                'eolDate': device['eol_date'].isoformat() if device['eol_date'] else None,
                'eolStatus': device['eol_status']
            })
        
        return jsonify(devices_json)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/<device_id>/assign', methods=['POST'])
def api_assign_device(device_id):
    """API endpoint to assign a device"""
    try:
        data = request.get_json()
        nurse_id = data.get('nurse_id')
        
        if not nurse_id:
            return jsonify({'error': 'nurse_id is required'}), 400
        
        db_service = DBService()
        
        # First check if nurse exists
        nurse = db_service.get_nurse(nurse_id)
        if not nurse:
            return jsonify({'error': 'Nurse not found'}), 404
            
        device = db_service.get_device(device_id)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
            
        if device['assigned_to']:
            return jsonify({'error': 'Device is already assigned'}), 400
            
        # Generate a UUID for the assignment
        assignment_id = str(uuid.uuid4())
        
        # Create assignment dictionary
        assignment = {
            'id': assignment_id,
            'device_id': device_id,
            'nurse_id': nurse_id,
            'assigned_at': datetime.now(),
            'returned_at': None,
            'status': 'Active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Update device status and create assignment
        db_service.update_device_status(device_id, 'In-Use')
        db_service.create_device_assignment(assignment)
        
        # Update device's assigned_to field
        device_update = Device(
            id=device_id,
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=nurse_id
        )
        db_service.update_device(device_update)
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment_id,
                'deviceId': device_id,
                'nurseId': nurse_id,
                'assignedAt': assignment['assigned_at'].isoformat(),
                'status': assignment['status']
            }
        })
        
    except Exception as e:
        print(f"Error in api_assign_device: {str(e)}")
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/<device_id>/transfer', methods=['POST'])
def api_transfer_device(device_id):
    """API endpoint to transfer a device"""
    try:
        data = request.get_json()
        from_nurse_id = data.get('from_nurse_id')
        to_nurse_id = data.get('to_nurse_id')
        
        if not from_nurse_id or not to_nurse_id:
            return jsonify({'error': 'Both from_nurse_id and to_nurse_id are required'}), 400
            
        db_service = DBService()
        device = db_service.get_device(device_id)
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
            
        if not device['assigned_to']:
            return jsonify({'error': 'Device is not currently assigned'}), 400
            
        # Close current assignment
        current_assignment = db_service.get_active_assignment(device_id)
        if current_assignment:
            update_data = {
                'id': current_assignment['id'],
                'status': 'Transferred',
                'returned_at': datetime.now()
            }
            db_service.update_device_assignment(update_data)
        
        # Create new assignment
        new_assignment_id = str(uuid.uuid4())
        new_assignment = {
            'id': new_assignment_id,
            'device_id': device_id,
            'nurse_id': to_nurse_id,
            'assigned_at': datetime.now(),
            'returned_at': None,
            'status': 'Active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        db_service.create_device_assignment(new_assignment)
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': new_assignment_id,
                'deviceId': device_id,
                'nurseId': to_nurse_id,
                'assignedAt': new_assignment['assigned_at'].isoformat(),
                'status': new_assignment['status']
            }
        })
        
    except Exception as e:
        print(f"Error in api_transfer_device: {str(e)}")
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/<device_id>/status', methods=['POST'])
@login_required
def update_status(device_id):
    """Update device status"""
    try:
        db_service = DBService()
        existing_device = db_service.get_device(device_id)
        
        if not existing_device:
            return jsonify({'success': False, 'error': 'Device not found'}), 404
        
        # Get status from request
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status not provided'}), 400
        
        # Create device object with updated status, preserving all other fields
        device = Device(
            id=device_id,
            serial_number=existing_device['serial_number'],
            model=existing_device['model'],
            manufacturer=existing_device['manufacturer'],
            rfid_tag=existing_device['rfid_tag'],
            barcode=existing_device['barcode'],
            status=new_status,
            location_id=existing_device['location_id'],
            assigned_to=existing_device['assigned_to'],
            purchase_date=existing_device['purchase_date'],
            last_maintenance_date=existing_device['last_maintenance_date'],
            eol_date=existing_device.get('eol_date'),
            eol_status=existing_device.get('eol_status', 'Active'),
            eol_notes=existing_device.get('eol_notes')
        )
        
        # Update in database
        success = db_service.update_device(device)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'No changes made to device'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@devices_bp.route('/api/nurses')
def api_list_nurses():
    """API endpoint to get all nurses"""
    try:
        db_service = DBService()
        nurses = db_service.get_all_nurses()
        
        # Convert nurses to JSON format
        nurses_json = []
        for nurse in nurses:
            nurses_json.append({
                'id': nurse['id'],
                'badgeId': nurse['badge_id'],
                'firstName': nurse['first_name'],
                'lastName': nurse['last_name'],
                'department': nurse['department'],
                'shift': nurse['shift']
            })
        
        return jsonify(nurses_json)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/nurses/<nurse_id>')
def api_get_nurse(nurse_id):
    """API endpoint to get a specific nurse"""
    try:
        db_service = DBService()
        nurse = db_service.get_nurse(nurse_id)
        
        if not nurse:
            return jsonify({'error': 'Nurse not found'}), 404
            
        return jsonify({
            'id': nurse['id'],
            'badgeId': nurse['badge_id'],
            'firstName': nurse['first_name'],
            'lastName': nurse['last_name'],
            'department': nurse['department'],
            'shift': nurse['shift']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/nurses', methods=['POST'])
def api_create_nurse():
    """API endpoint to create a new nurse"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        required_fields = ['badgeId', 'firstName', 'lastName', 'department', 'shift']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Generate a UUID for the new nurse
        nurse_id = str(uuid.uuid4())
        
        nurse_data = {
            'id': nurse_id,
            'badge_id': data['badgeId'],
            'first_name': data['firstName'],
            'last_name': data['lastName'],
            'department': data['department'],
            'shift': data['shift'],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        db_service = DBService()
        db_service.create_user(nurse_data)
        
        return jsonify({
            'success': True,
            'nurse': {
                'id': nurse_id,
                'badgeId': data['badgeId'],
                'firstName': data['firstName'],
                'lastName': data['lastName'],
                'department': data['department'],
                'shift': data['shift']
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/assign', methods=['POST'])
def api_assign_device_by_barcode():
    """API endpoint to assign a device using barcode"""
    try:
        data = request.get_json()
        device_barcode = data.get('device_barcode')
        nurse_badge_id = data.get('nurse_badge_id')
        
        if not device_barcode or not nurse_badge_id:
            return jsonify({'error': 'Both device_barcode and nurse_badge_id are required'}), 400
            
        db_service = DBService()
        
        # First get the device by barcode
        device = db_service.get_device_by_barcode(device_barcode)
        if not device:
            return jsonify({'error': 'Device not found'}), 404
            
        # Then get the nurse by badge ID
        nurse = db_service.get_nurse_by_badge(nurse_badge_id)
        if not nurse:
            return jsonify({'error': 'Nurse not found'}), 404
            
        if device['assigned_to']:
            return jsonify({'error': 'Device is already assigned'}), 400
            
        # Generate a UUID for the assignment
        assignment_id = str(uuid.uuid4())
        
        # Create assignment dictionary
        assignment = {
            'id': assignment_id,
            'device_id': device['id'],
            'nurse_id': nurse['id'],
            'assigned_at': datetime.now(),
            'returned_at': None,
            'status': 'Active',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        
        # Update device status and create assignment
        db_service.update_device_status(device['id'], 'In-Use')
        db_service.create_device_assignment(assignment)
        
        # Update device's assigned_to field
        device_update = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=nurse['id']
        )
        db_service.update_device(device_update)
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment_id,
                'deviceId': device['id'],
                'nurseId': nurse['id'],
                'assignedAt': assignment['assigned_at'].isoformat(),
                'status': assignment['status']
            }
        })
        
    except Exception as e:
        print(f"Error in api_assign_device_by_barcode: {str(e)}")
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/count')
@api_auth_required
def api_device_count():
    """API endpoint to get total device count"""
    try:
        db_service = DBService()
        count = db_service.get_device_count()
        
        return jsonify({
            'count': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/count/missing')
@api_auth_required
def api_missing_device_count():
    """API endpoint to get count of missing devices"""
    try:
        db_service = DBService()
        count = db_service.get_device_count(status='Missing')
        
        return jsonify({
            'count': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@devices_bp.route('/api/count/by-status')
@api_auth_required
def api_device_count_by_status():
    """API endpoint to get device counts grouped by status"""
    try:
        db_service = DBService()
        
        # Get counts for each status
        in_facility_count = db_service.get_device_count(status='In-Facility')
        missing_count = db_service.get_device_count(status='Missing')
        temp_out_count = db_service.get_device_count(status='Temporarily Out')
        
        return jsonify({
            'counts': {
                'In-Facility': in_facility_count,
                'Missing': missing_count,
                'Temporarily Out': temp_out_count
            },
            'total': in_facility_count + missing_count + temp_out_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500 