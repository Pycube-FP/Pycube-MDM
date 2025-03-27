from datetime import datetime
import uuid

class Device:
    """
    Model for mobile devices tracked with RFID
    """
    def __init__(self, id=None, serial_number=None, model=None, manufacturer=None, 
                 rfid_tag=None, barcode=None, status="Available", hospital_id=None,
                 location_id=None, assigned_to=None, purchase_date=None, 
                 last_maintenance_date=None, eol_date=None, eol_status="Active", 
                 eol_notes=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.serial_number = serial_number
        self.model = model
        self.manufacturer = manufacturer
        self.rfid_tag = rfid_tag  # This is now the EPC Code but kept as rfid_tag for DB compatibility
        self.barcode = barcode
        self.status = status  # Available, In-Use, Maintenance, Missing
        self.hospital_id = hospital_id
        self.location_id = location_id
        self.assigned_to = assigned_to
        self.purchase_date = purchase_date
        self.last_maintenance_date = last_maintenance_date
        self.eol_date = eol_date
        self.eol_status = eol_status  # Active, Warning, Critical, Expired
        self.eol_notes = eol_notes
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @property
    def epc_code(self):
        """Get the EPC Code (renamed from rfid_tag)"""
        return self.rfid_tag
    
    @epc_code.setter
    def epc_code(self, value):
        """Set the EPC Code (sets rfid_tag)"""
        self.rfid_tag = value
    
    @classmethod
    def from_dict(cls, data):
        """Create a device instance from a dictionary"""
        return cls(
            id=data.get('id'),
            serial_number=data.get('serial_number'),
            model=data.get('model'),
            manufacturer=data.get('manufacturer'),
            rfid_tag=data.get('rfid_tag'),
            barcode=data.get('barcode'),
            status=data.get('status', 'Available'),
            hospital_id=data.get('hospital_id'),
            location_id=data.get('location_id'),
            assigned_to=data.get('assigned_to'),
            purchase_date=data.get('purchase_date'),
            last_maintenance_date=data.get('last_maintenance_date'),
            eol_date=data.get('eol_date'),
            eol_status=data.get('eol_status', 'Active'),
            eol_notes=data.get('eol_notes'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert device instance to dictionary"""
        return {
            'id': self.id,
            'serial_number': self.serial_number,
            'model': self.model,
            'manufacturer': self.manufacturer,
            'rfid_tag': self.rfid_tag,  # Keep original field name in dictionaries
            'epc_code': self.rfid_tag,  # Add new field name as well
            'barcode': self.barcode,
            'status': self.status,
            'hospital_id': self.hospital_id,
            'location_id': self.location_id,
            'assigned_to': self.assigned_to,
            'purchase_date': self.purchase_date,
            'last_maintenance_date': self.last_maintenance_date,
            'eol_date': self.eol_date,
            'eol_status': self.eol_status,
            'eol_notes': self.eol_notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"Device(id={self.id}, model={self.model}, status={self.status})" 