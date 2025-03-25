from flask import Blueprint, request, jsonify, render_template
from services.db_service import DBService
from models.rfid_alert import RFIDAlert
from models.device import Device
from datetime import datetime
from routes.auth import login_required
import math

rfid_bp = Blueprint('rfid', __name__, url_prefix='/rfid')

@rfid_bp.route('/alerts')
@login_required
def alerts():
    """Display the RFID alerts page"""
    db_service = DBService()
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of alerts per page
    
    # Get total count of alerts for pagination
    total_alerts = len(db_service.get_rfid_alerts())
    total_pages = math.ceil(total_alerts / per_page)
    
    # Get alerts for current page
    offset = (page - 1) * per_page
    alerts = db_service.get_rfid_alerts(limit=per_page, offset=offset)
    
    return render_template('rfid/alerts.html', 
                         alerts=alerts,
                         current_page=page,
                         total_pages=total_pages)

@rfid_bp.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get RFID alerts with optional filtering"""
    try:
        # Get query parameters
        device_id = request.args.get('device_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        db_service = DBService()
        alerts = db_service.get_rfid_alerts(
            device_id=device_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify({
            'success': True,
            'alerts': [alert.to_dict() for alert in alerts]
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@rfid_bp.route('/alert', methods=['POST'])
def handle_rfid_alert():
    """Handle RFID reader alerts"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        reader_id = data.get('reader_id')
        rfid_tag = data.get('rfid_tag')
        location = data.get('location')
        
        if not all([reader_id, rfid_tag, location]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        db_service = DBService()
        
        # Get device from RFID tag
        device = db_service.get_device_by_rfid(rfid_tag)
        
        if not device:
            return jsonify({'error': 'Device not found for RFID tag'}), 404
        
        # Create alert and mark device as missing
        alert = RFIDAlert(
            device_id=device.id,
            reader_id=reader_id,
            location=location
        )
        
        # Mark device as missing if it's currently in use
        if device.status == 'In-Use':
            device.status = 'Missing'
            db_service.update_device(device)
        
        # Save alert
        db_service.create_rfid_alert(alert)
        
        # Get device details including assignment
        device_details = db_service.get_device_details(device.id)
        
        response_data = {
            'success': True,
            'alert': alert.to_dict(),
            'device': device_details,
            'message': f"Missing Alert: Device {device.model} ({device.serial_number}) detected at {location}"
        }
        
        if device.status == 'Missing':
            response_data['warning'] = 'WARNING: Device has been marked as missing'
        
        return jsonify(response_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500 