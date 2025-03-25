import uuid
from datetime import datetime

class ReaderEvent:
    """Model for RFID reader events"""
    
    def __init__(self, device_id=None, rfid_tag=None, reader_id=None, location_id=None, timestamp=None):
        self.id = str(uuid.uuid4())
        self.device_id = device_id
        self.rfid_tag = rfid_tag
        self.reader_id = reader_id
        self.location_id = location_id
        self.timestamp = timestamp or datetime.now()
        self.created_at = datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a ReaderEvent instance from a dictionary"""
        instance = cls()
        instance.id = data.get('id', str(uuid.uuid4()))
        instance.device_id = data.get('device_id')
        instance.rfid_tag = data.get('rfid_tag')
        instance.reader_id = data.get('reader_id')
        instance.location_id = data.get('location_id')
        instance.timestamp = data.get('timestamp')
        instance.created_at = data.get('created_at', datetime.now())
        return instance
    
    def to_dict(self):
        """Convert ReaderEvent instance to dictionary"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'rfid_tag': self.rfid_tag,
            'reader_id': self.reader_id,
            'location_id': self.location_id,
            'timestamp': self.timestamp,
            'created_at': self.created_at
        }
    
    def __str__(self):
        """String representation of ReaderEvent"""
        return f"ReaderEvent(id={self.id}, device_id={self.device_id}, reader_id={self.reader_id}, location_id={self.location_id}, timestamp={self.timestamp})" 