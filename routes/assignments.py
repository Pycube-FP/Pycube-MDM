from flask import Blueprint, request, jsonify, flash, redirect, url_for, render_template
from services.db_service import DBService
from models.device_assignment import DeviceAssignment
from models.device import Device
from models.nurse import Nurse
from routes.auth import login_required
from datetime import datetime

assignments_bp = Blueprint('assignments', __name__, url_prefix='/assignments')

@assignments_bp.route('/assign', methods=['GET'])
@login_required
def assign():
    """Redirect to consolidated assignment page"""
    return redirect(url_for('assignments.consolidated_assignment'))

@assignments_bp.route('/transfer', methods=['GET'])
@login_required
def transfer():
    """Redirect to consolidated assignment page"""
    return redirect(url_for('assignments.consolidated_assignment'))

@assignments_bp.route('/assign', methods=['POST'])
@login_required
def assign_device():
    """Assign a device to a nurse"""
    try:
        device_barcode = request.form.get('device_barcode')
        nurse_barcode = request.form.get('nurse_barcode')
        
        if not device_barcode or not nurse_barcode:
            return jsonify({'error': 'Both device and nurse barcodes are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse from barcodes
        device = db_service.get_device_by_barcode(device_barcode)
        nurse = db_service.get_nurse_by_barcode(nurse_barcode)
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        if not nurse:
            return jsonify({'error': 'Nurse not found'}), 404
        
        if device['status'] != 'Available':
            return jsonify({'error': 'Device is not available for assignment'}), 400
        
        # Create assignment
        assignment = DeviceAssignment(
            device_id=device['id'],
            nurse_id=nurse['id']
        )
        
        # Get nurse's full name
        nurse_name = f"{nurse['first_name']} {nurse['last_name']}"
        
        # Create a Device object for updating
        device_obj = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=nurse_name,  # Store the nurse's full name instead of ID
            purchase_date=device['purchase_date'],
            last_maintenance_date=device['last_maintenance_date'],
            eol_date=device.get('eol_date'),
            eol_status=device.get('eol_status', 'Active'),
            eol_notes=device.get('eol_notes')
        )
        
        # Save assignment and update device
        assignment_id = db_service.create_device_assignment(assignment)
        db_service.update_device(device_obj)
        
        # Create assignment response with nurse details
        assignment_dict = assignment.to_dict()
        assignment_dict.update({
            'nurse_name': nurse_name,
            'department': nurse['department']
        })
        
        return jsonify({
            'success': True,
            'message': f'Device successfully assigned to {nurse_name}',
            'assignment': assignment_dict,
            'next_action': {
                'text': 'Assign Another Device',
                'url': url_for('assignments.assign')
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/transfer', methods=['POST'])
@login_required
def transfer_device():
    """Transfer a device from one nurse to another"""
    try:
        device_barcode = request.form.get('device_barcode')
        nurse_barcode = request.form.get('nurse_barcode')
        
        if not device_barcode or not nurse_barcode:
            return jsonify({'error': 'Device barcode and new nurse barcode are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse
        device = db_service.get_device_by_barcode(device_barcode)
        to_nurse = db_service.get_nurse_by_barcode(nurse_barcode)
        
        if not device or not to_nurse:
            return jsonify({'error': 'Device or nurse not found'}), 404
        
        # Check if the new nurse already has an active device assignment
        existing_assignment = db_service.get_nurse_active_assignment(to_nurse['id'])
        if existing_assignment:
            return jsonify({
                'error': f"Nurse {to_nurse['first_name']} {to_nurse['last_name']} already has an active device assignment (Serial: {existing_assignment['serial_number']})"
            }), 400
        
        # Get current assignment
        current_assignment_data = db_service.get_active_assignment(device['id'])
        if not current_assignment_data:
            # If no current assignment, treat it as a new assignment
            return assign_device()
        
        # Get current nurse
        from_nurse = db_service.get_nurse(current_assignment_data['nurse_id'])
        if not from_nurse:
            return jsonify({'error': 'Current nurse not found'}), 404
        
        # Don't allow transfer to same nurse
        if current_assignment_data['nurse_id'] == to_nurse['id']:
            return jsonify({'error': 'Cannot assign device to the same nurse'}), 400
        
        # Create DeviceAssignment object for current assignment
        current_assignment = DeviceAssignment(
            device_id=current_assignment_data['device_id'],
            nurse_id=current_assignment_data['nurse_id'],
            assigned_at=current_assignment_data['assigned_at']
        )
        current_assignment.id = current_assignment_data['id']  # Set the ID after creation
        current_assignment.status = 'Transferred'
        current_assignment.returned_at = datetime.now()
        db_service.update_device_assignment(current_assignment)
        
        # Create new assignment
        new_assignment = DeviceAssignment(
            device_id=device['id'],
            nurse_id=to_nurse['id']
        )
        
        # Update device with new nurse's name while preserving other fields
        device_obj = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=f"{to_nurse['first_name']} {to_nurse['last_name']}",
            purchase_date=device['purchase_date'],
            last_maintenance_date=device['last_maintenance_date'],
            eol_date=device.get('eol_date'),
            eol_status=device.get('eol_status', 'Active'),
            eol_notes=device.get('eol_notes')
        )
        
        # Save changes
        db_service.create_device_assignment(new_assignment)
        db_service.update_device(device_obj)
        
        return jsonify({
            'success': True,
            'message': f"Device transferred from {from_nurse['first_name']} {from_nurse['last_name']} to {to_nurse['first_name']} {to_nurse['last_name']}",
            'assignment': new_assignment.to_dict(),
            'next_action': {
                'text': 'Transfer Another Device',
                'url': url_for('assignments.transfer')
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/return', methods=['POST'])
@login_required
def return_device():
    """Return a device to available pool"""
    try:
        device_barcode = request.form.get('device_barcode')
        nurse_barcode = request.form.get('nurse_barcode')
        
        if not device_barcode or not nurse_barcode:
            return jsonify({'error': 'Both device and nurse barcodes are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse
        device = db_service.get_device_by_barcode(device_barcode)
        nurse = db_service.get_nurse_by_barcode(nurse_barcode)
        
        if not device or not nurse:
            return jsonify({'error': 'Device or nurse not found'}), 404
        
        # Verify current assignment
        current_assignment = db_service.get_active_assignment(device.id)
        if not current_assignment or current_assignment.nurse_id != nurse.id:
            return jsonify({'error': 'Device is not currently assigned to the specified nurse'}), 400
        
        # Close assignment
        current_assignment.status = 'Returned'
        current_assignment.returned_at = datetime.now()
        db_service.update_device_assignment(current_assignment)
        
        # Update device
        device = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='Available',
            location_id=device['location_id'],
            assigned_to=None,
            purchase_date=device['purchase_date'],
            last_maintenance_date=device['last_maintenance_date'],
            eol_date=device.get('eol_date'),
            eol_status=device.get('eol_status', 'Active'),
            eol_notes=device.get('eol_notes')
        )
        
        db_service.update_device(device)
        
        return jsonify({
            'success': True,
            'message': f'Device returned by {nurse.name}',
            'assignment': current_assignment.to_dict()
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/consolidated', methods=['GET'])
@login_required
def consolidated_assignment():
    """Render the consolidated assignment page"""
    return render_template('assignments/consolidated_assignment.html')

@assignments_bp.route('/consolidated', methods=['POST'])
@login_required
def handle_consolidated_assignment():
    """Handle assignment or transfer based on device status"""
    try:
        device_barcode = request.form.get('device_barcode')
        nurse_barcode = request.form.get('nurse_barcode')
        
        if not device_barcode or not nurse_barcode:
            return jsonify({'error': 'Both device and nurse barcodes are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse
        device = db_service.get_device_by_barcode(device_barcode)
        nurse = db_service.get_nurse_by_barcode(nurse_barcode)
        
        if not device or not nurse:
            return jsonify({'error': 'Device or nurse not found'}), 404
        
        # Check if the device is currently assigned
        current_assignment = db_service.get_active_assignment(device['id'])
        if current_assignment:
            # Perform transfer
            return transfer_device()
        else:
            # Perform new assignment
            return assign_device()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/assign', methods=['POST'])
@login_required
def api_assign_device():
    """API endpoint to assign a device to a nurse using barcodes"""
    try:
        data = request.get_json()
        device_barcode = data.get('device_barcode')
        nurse_badge_id = data.get('nurse_badge_id')
        
        if not device_barcode or not nurse_badge_id:
            return jsonify({'error': 'Both device_barcode and nurse_badge_id are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse from barcodes
        device = db_service.get_device_by_barcode(device_barcode)
        nurse = db_service.get_nurse_by_badge(nurse_badge_id)
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        if not nurse:
            return jsonify({'error': 'Nurse not found'}), 404
        
        if device['status'] != 'Available':
            return jsonify({'error': 'Device is not available for assignment'}), 400
        
        # Create assignment
        assignment = DeviceAssignment(
            device_id=device['id'],
            nurse_id=nurse['id']
        )
        
        # Get nurse's full name
        nurse_name = f"{nurse['first_name']} {nurse['last_name']}"
        
        # Create a Device object for updating
        device_obj = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=nurse_name,
            purchase_date=device['purchase_date'],
            last_maintenance_date=device['last_maintenance_date'],
            eol_date=device.get('eol_date'),
            eol_status=device.get('eol_status', 'Active'),
            eol_notes=device.get('eol_notes')
        )
        
        # Save assignment and update device
        assignment_id = db_service.create_device_assignment(assignment)
        db_service.update_device(device_obj)
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment_id,
                'deviceId': device['id'],
                'nurseId': nurse['id'],
                'nurseName': nurse_name,
                'assignedAt': assignment.assigned_at.isoformat(),
                'status': assignment.status
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@assignments_bp.route('/api/transfer', methods=['POST'])
@login_required
def api_transfer_device():
    """API endpoint to transfer a device from one nurse to another using barcodes"""
    try:
        data = request.get_json()
        device_barcode = data.get('device_barcode')
        nurse_badge_id = data.get('nurse_badge_id')
        
        if not device_barcode or not nurse_badge_id:
            return jsonify({'error': 'Both device_barcode and nurse_badge_id are required'}), 400
        
        db_service = DBService()
        
        # Get device and nurse
        device = db_service.get_device_by_barcode(device_barcode)
        to_nurse = db_service.get_nurse_by_badge(nurse_badge_id)
        
        if not device or not to_nurse:
            return jsonify({'error': 'Device or nurse not found'}), 404
        
        # Get current assignment
        current_assignment_data = db_service.get_active_assignment(device['id'])
        if not current_assignment_data:
            # If no current assignment, treat it as a new assignment
            return api_assign_device()
        
        # Get current nurse
        from_nurse = db_service.get_nurse(current_assignment_data['nurse_id'])
        if not from_nurse:
            return jsonify({'error': 'Current nurse not found'}), 404
        
        # Don't allow transfer to same nurse
        if current_assignment_data['nurse_id'] == to_nurse['id']:
            return jsonify({'error': 'Cannot transfer device to the same nurse'}), 400
        
        # Create DeviceAssignment object for current assignment
        current_assignment = DeviceAssignment(
            device_id=current_assignment_data['device_id'],
            nurse_id=current_assignment_data['nurse_id'],
            assigned_at=current_assignment_data['assigned_at']
        )
        current_assignment.id = current_assignment_data['id']
        current_assignment.status = 'Transferred'
        current_assignment.returned_at = datetime.now()
        db_service.update_device_assignment(current_assignment)
        
        # Create new assignment
        new_assignment = DeviceAssignment(
            device_id=device['id'],
            nurse_id=to_nurse['id']
        )
        
        # Update device with new nurse's name
        device_obj = Device(
            id=device['id'],
            serial_number=device['serial_number'],
            model=device['model'],
            manufacturer=device['manufacturer'],
            rfid_tag=device['rfid_tag'],
            barcode=device['barcode'],
            status='In-Use',
            location_id=device['location_id'],
            assigned_to=f"{to_nurse['first_name']} {to_nurse['last_name']}",
            purchase_date=device['purchase_date'],
            last_maintenance_date=device['last_maintenance_date'],
            eol_date=device.get('eol_date'),
            eol_status=device.get('eol_status', 'Active'),
            eol_notes=device.get('eol_notes')
        )
        
        # Save changes
        assignment_id = db_service.create_device_assignment(new_assignment)
        db_service.update_device(device_obj)
        
        return jsonify({
            'success': True,
            'assignment': {
                'id': assignment_id,
                'deviceId': device['id'],
                'nurseId': to_nurse['id'],
                'nurseName': f"{to_nurse['first_name']} {to_nurse['last_name']}",
                'assignedAt': new_assignment.assigned_at.isoformat(),
                'status': new_assignment.status,
                'previousNurse': f"{from_nurse['first_name']} {from_nurse['last_name']}"
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 