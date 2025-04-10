from datetime import datetime
import uuid
import pytz

# Configure timezone
TIMEZONE = pytz.timezone('America/New_York')

class RFIDAlert:
    """
    Model for tracking RFID alerts when devices are detected at unauthorized locations
    """
    def __init__(self, id=None, device_id=None, reader_id=None, hospital_id=None,
                 location_id=None, timestamp=None, created_at=None, updated_at=None,
                 reader_code=None, antenna_number=None, rfid_tag=None, status=None,
                 previous_status=None):
        self.id = id or str(uuid.uuid4())
        self.device_id = device_id
        self.reader_id = reader_id
        self.hospital_id = hospital_id
        self.location_id = location_id  # Reference to locations table
        
        # Use timezone-aware timestamps with EST
        now = datetime.now(TIMEZONE)
        
        # Set timestamp with timezone info
        if timestamp:
            self.timestamp = timestamp if timestamp.tzinfo else TIMEZONE.localize(timestamp)
        else:
            self.timestamp = now
            
        self.created_at = created_at if created_at and created_at.tzinfo else now
        self.updated_at = updated_at if updated_at and updated_at.tzinfo else now
        
        self.reader_code = reader_code
        self.antenna_number = antenna_number
        self.rfid_tag = rfid_tag
        self.status = status
        self.previous_status = previous_status
    
    @classmethod
    def from_dict(cls, data):
        """Create an RFID alert instance from a dictionary"""
        return cls(
            id=data.get('id'),
            device_id=data.get('device_id'),
            reader_id=data.get('reader_id'),
            hospital_id=data.get('hospital_id'),
            location_id=data.get('location_id'),
            timestamp=data.get('timestamp'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            reader_code=data.get('reader_code'),
            antenna_number=data.get('antenna_number'),
            rfid_tag=data.get('rfid_tag'),
            status=data.get('status'),
            previous_status=data.get('previous_status')
        )
    
    def to_dict(self):
        """Convert RFID alert instance to dictionary"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'reader_id': self.reader_id,
            'hospital_id': self.hospital_id,
            'location_id': self.location_id,
            'timestamp': self.timestamp,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'reader_code': self.reader_code,
            'antenna_number': self.antenna_number,
            'rfid_tag': self.rfid_tag,
            'status': self.status,
            'previous_status': self.previous_status
        }
    
    def __str__(self):
        return f"RFIDAlert(id={self.id}, device_id={self.device_id}, location_id={self.location_id})" 