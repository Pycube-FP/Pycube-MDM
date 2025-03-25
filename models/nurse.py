from datetime import datetime
import uuid

class Nurse:
    """Model class for nurses"""
    
    def __init__(self, badge_id, first_name, last_name, department, shift):
        self.id = str(uuid.uuid4())
        self.badge_id = badge_id
        self.first_name = first_name
        self.last_name = last_name
        self.department = department
        self.shift = shift
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self):
        """Convert nurse object to dictionary"""
        return {
            'id': self.id,
            'badge_id': self.badge_id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'department': self.department,
            'shift': self.shift,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"Nurse(id={self.id}, name={self.first_name} {self.last_name}, shift={self.shift})" 