from datetime import datetime
import uuid

class Location:
    """
    Model for hospital locations that have RFID readers
    """
    def __init__(self, id=None, name=None, type=None, hospital_id=None,
                 building=None, floor=None, room=None, created_at=None, 
                 updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.type = type  # Entrance, Exit, Room, Ward, Department
        self.hospital_id = hospital_id
        self.building = building
        self.floor = floor
        self.room = room
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a location instance from a dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            type=data.get('type'),
            hospital_id=data.get('hospital_id'),
            building=data.get('building'),
            floor=data.get('floor'),
            room=data.get('room'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert location instance to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'hospital_id': self.hospital_id,
            'building': self.building,
            'floor': self.floor,
            'room': self.room,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __str__(self):
        return f"Location(id={self.id}, name={self.name}, type={self.type})" 