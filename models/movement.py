from datetime import datetime
import uuid

class ReaderEvent:
    """
    Model for tracking device reads at RFID readers
    """
    def __init__(self, id=None, device_id=None, rfid_tag=None, reader_id=None, 
                 location_id=None, timestamp=None, created_at=None):
        self.id = id or str(uuid.uuid4())
        self.device_id = device_id
        self.rfid_tag = rfid_tag
        self.reader_id = reader_id
        self.location_id = location_id
        self.timestamp = timestamp or datetime.now()
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a reader event instance from a dictionary"""
        return cls(
            id=data.get('id'),
            device_id=data.get('device_id'),
            rfid_tag=data.get('rfid_tag'),
            reader_id=data.get('reader_id'),
            location_id=data.get('location_id'),
            timestamp=data.get('timestamp'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self):
        """Convert reader event instance to dictionary"""
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
        return f"ReaderEvent(id={self.id}, device_id={self.device_id}, timestamp={self.timestamp})" 