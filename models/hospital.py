from datetime import datetime
import uuid

class Hospital:
    """Model for hospitals"""
    
    def __init__(self, name, code, address=None, city=None, state=None, zip_code=None, 
                 status='Active', id=None, created_at=None, updated_at=None):
        self.id = id or str(uuid.uuid4())
        self.name = name
        self.code = code
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data):
        """Create a Hospital instance from a dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            code=data.get('code'),
            address=data.get('address'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            status=data.get('status', 'Active'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def to_dict(self):
        """Convert Hospital instance to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        } 