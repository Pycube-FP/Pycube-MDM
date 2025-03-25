from datetime import datetime
import uuid

class RFIDAlert:
    """
    Model for tracking RFID alerts when devices are detected at unauthorized locations
    """
    def __init__(self, id=None, device_id=None, reader_id=None,
                 location=None, timestamp=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.device_id = device_id
        self.reader_id = reader_id
        self.location = location  # Description of the reader location
        self.timestamp = timestamp or datetime.now()
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create an RFID alert instance from a dictionary"""
        return cls(
            id=data.get('id'),
            device_id=data.get('device_id'),
            reader_id=data.get('reader_id'),
            location=data.get('location'),
            timestamp=data.get('timestamp'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert RFID alert instance to dictionary"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'reader_id': self.reader_id,
            'location': self.location,
            'timestamp': self.timestamp,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"RFIDAlert(id={self.id}, device_id={self.device_id}, location={self.location})" 