from datetime import datetime
import uuid

class Nurse:
    """Model class for nurses"""
    
    def __init__(self, badge_id, first_name, last_name, hospital_id, department=None, shift=None,
                 id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.badge_id = badge_id
        self.first_name = first_name
        self.last_name = last_name
        self.hospital_id = hospital_id
        self.department = department
        self.shift = shift
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a Nurse instance from a dictionary"""
        return cls(
            id=data.get('id'),
            badge_id=data.get('badge_id'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            hospital_id=data.get('hospital_id'),
            department=data.get('department'),
            shift=data.get('shift'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert nurse object to dictionary"""
        return {
            'id': self.id,
            'badge_id': self.badge_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'hospital_id': self.hospital_id,
            'department': self.department,
            'shift': self.shift,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"Nurse(id={self.id}, name={self.first_name} {self.last_name}, shift={self.shift})" 