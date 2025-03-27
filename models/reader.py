from datetime import datetime
import uuid

class Reader:
    """Model for RFID readers"""
    
    def __init__(self, reader_code, hospital_id, antenna_number, location_id, 
                 name=None, status='Active', last_heartbeat=None, id=None, 
                 created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.reader_code = reader_code
        self.antenna_number = antenna_number
        self.name = name or f"{reader_code} - Antenna {antenna_number}"
        self.hospital_id = hospital_id
        self.location_id = location_id
        self.status = status
        self.last_heartbeat = last_heartbeat or datetime.now()
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a Reader instance from a dictionary"""
        return cls(
            id=data.get('id'),
            reader_code=data.get('reader_code'),
            antenna_number=data.get('antenna_number'),
            name=data.get('name'),
            hospital_id=data.get('hospital_id'),
            location_id=data.get('location_id'),
            status=data.get('status', 'Active'),
            last_heartbeat=data.get('last_heartbeat'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert Reader instance to dictionary"""
        return {
            'id': self.id,
            'reader_code': self.reader_code,
            'antenna_number': self.antenna_number,
            'name': self.name,
            'hospital_id': self.hospital_id,
            'location_id': self.location_id,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp"""
        self.last_heartbeat = datetime.now()
        self.updated_at = datetime.now()
    
    @property
    def display_name(self):
        """Get a display name that includes the antenna number"""
        return f"{self.name} (Antenna {self.antenna_number})" 