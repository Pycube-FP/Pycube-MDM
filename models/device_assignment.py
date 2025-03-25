from datetime import datetime
import uuid

class DeviceAssignment:
    """
    Model for tracking device assignments and transfers between nurses
    """
    def __init__(self, device_id, nurse_id, assigned_at=None, returned_at=None, status='Active'):
        self.id = str(uuid.uuid4())
        self.device_id = device_id
        self.nurse_id = nurse_id
        self.assigned_at = assigned_at or datetime.now()
        self.returned_at = returned_at
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a device assignment instance from a dictionary"""
        return cls(
            device_id=data.get('device_id'),
            nurse_id=data.get('nurse_id'),
            assigned_at=data.get('assigned_at'),
            returned_at=data.get('returned_at'),
            status=data.get('status')
        )
    
    def to_dict(self):
        """Convert device assignment instance to dictionary"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'nurse_id': self.nurse_id,
            'assigned_at': self.assigned_at,
            'returned_at': self.returned_at,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"DeviceAssignment(id={self.id}, device_id={self.device_id}, nurse_id={self.nurse_id}, status={self.status})" 