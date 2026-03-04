"""
Firebase Firestore Models for GDTA 2026 Registration System
Replaces SQLAlchemy with Cloud Firestore
"""

import random
import string
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import firestore
from db.firebase_config import get_firestore_db, COLLECTIONS


def generate_unique_id(length=6):
    """Generate a unique alphanumeric ID"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


class FirestoreModel:
    """Base class for Firestore models"""
    
    @staticmethod
    def _serialize_datetime(dt):
        """Convert datetime to ISO string"""
        if isinstance(dt, datetime):
            return dt.isoformat()
        return dt
    
    @staticmethod
    def _deserialize_datetime(dt_str):
        """Convert ISO string to datetime"""
        if isinstance(dt_str, str):
            try:
                return datetime.fromisoformat(dt_str)
            except:
                return dt_str
        return dt_str


class Registration(FirestoreModel):
    """Registration model - stores all conference registrations"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.event_id = kwargs.get('event_id')  # Link to Event
        self.name = kwargs.get('name')
        self.email = kwargs.get('email')
        self.institution = kwargs.get('institution')
        self.role = kwargs.get('role')
        self.gdta_member = kwargs.get('gdta_member')
        self.gdta_affiliation = kwargs.get('gdta_affiliation')
        self.country = kwargs.get('country')
        self.state = kwargs.get('state')
        self.consent = kwargs.get('consent')
        self.registration_source = kwargs.get('registration_source', 'chatbot')
        self.session_id = kwargs.get('session_id')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.status = kwargs.get('status', 'pending')
        self.admin_notes = kwargs.get('admin_notes')
        
        # Unique ID for QR code (6-character alphanumeric)
        self.unique_id = kwargs.get('unique_id')
        if not self.unique_id:
            self.unique_id = self._generate_and_check_unique_id()
        
        # ID card generation tracking
        self.id_card_generated = kwargs.get('id_card_generated', False)
        self.id_card_generated_at = kwargs.get('id_card_generated_at')
        self.id_card_url = kwargs.get('id_card_url')  # Download URL of generated card
        self.id_card_regenerate_approved = kwargs.get('id_card_regenerate_approved', False)
    
    def to_dict(self):
        """Convert to dictionary for Firestore"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'name': self.name,
            'email': self.email,
            'institution': self.institution,
            'role': self.role,
            'gdta_member': self.gdta_member,
            'gdta_affiliation': self.gdta_affiliation,
            'country': self.country,
            'state': self.state,
            'consent': self.consent,
            'registration_source': self.registration_source,
            'session_id': self.session_id,
            'created_at': self._serialize_datetime(self.created_at),
            'updated_at': self._serialize_datetime(self.updated_at),
            'status': self.status,
            'admin_notes': self.admin_notes,
            'unique_id': self.unique_id,
            'id_card_generated': self.id_card_generated,
            'id_card_generated_at': self._serialize_datetime(self.id_card_generated_at),
            'id_card_url': self.id_card_url,
            'id_card_regenerate_approved': self.id_card_regenerate_approved
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create Registration from Firestore document"""
        data['id'] = doc_id
        data['created_at'] = cls._deserialize_datetime(data.get('created_at'))
        data['updated_at'] = cls._deserialize_datetime(data.get('updated_at'))
        data['id_card_generated_at'] = cls._deserialize_datetime(data.get('id_card_generated_at'))
        return cls(**data)
    
    @staticmethod
    def _generate_and_check_unique_id():
        """Generate a unique 6-character ID and check for duplicates"""
        db = get_firestore_db()
        max_attempts = 10
        
        for _ in range(max_attempts):
            new_id = generate_unique_id(6)
            
            # Check if this ID already exists
            existing = db.collection(COLLECTIONS['registrations']).where('unique_id', '==', new_id).limit(1).get()
            
            if not existing:
                return new_id
        
        # Fallback: use longer ID if collision persists
        return generate_unique_id(8)
    
    @classmethod
    def get_by_unique_id(cls, unique_id):
        """Get registration by unique_id"""
        db = get_firestore_db()
        docs = db.collection(COLLECTIONS['registrations']).where('unique_id', '==', unique_id).limit(1).get()
        
        if docs:
            doc = docs[0]
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    def save(self):
        """Save registration to Firestore"""
        db = get_firestore_db()
        self.updated_at = datetime.utcnow()
        
        if self.id:
            # Update existing
            doc_ref = db.collection(COLLECTIONS['registrations']).document(self.id)
            doc_ref.update(self.to_dict())
        else:
            # Create new - use email as document ID for easy duplicate checking
            doc_ref = db.collection(COLLECTIONS['registrations']).document(self.email)
            self.id = self.email
            doc_ref.set(self.to_dict())
        
        return self.id
    
    @classmethod
    def get_by_id(cls, doc_id):
        """Get registration by ID"""
        db = get_firestore_db()
        doc = db.collection(COLLECTIONS['registrations']).document(doc_id).get()
        
        if doc.exists:
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    @classmethod
    def get_by_email(cls, email):
        """Get registration by email"""
        return cls.get_by_id(email)
    
    @classmethod
    def get_all(cls, limit=100, offset=0, filters=None):
        """Get all registrations with optional filters"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['registrations'])
        
        # Apply filters
        if filters:
            if filters.get('event_id'):
                query = query.where('event_id', '==', filters['event_id'])
            if filters.get('status'):
                query = query.where('status', '==', filters['status'])
            if filters.get('country'):
                query = query.where('country', '==', filters['country'])
        
        # Order by created_at descending
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    @classmethod
    def count(cls, filters=None):
        """Count registrations"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['registrations'])
        
        if filters:
            if filters.get('event_id'):
                query = query.where('event_id', '==', filters['event_id'])
            if filters.get('status'):
                query = query.where('status', '==', filters['status'])
            if filters.get('country'):
                query = query.where('country', '==', filters['country'])
        
        return len(list(query.stream()))
    
    @classmethod
    def delete(cls, doc_id):
        """Delete registration"""
        db = get_firestore_db()
        db.collection(COLLECTIONS['registrations']).document(doc_id).delete()


class AdminUser(FirestoreModel):
    """Admin user model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.password_hash = kwargs.get('password_hash')
        self.email = kwargs.get('email')
        self.name = kwargs.get('name')
        self.role = kwargs.get('role', 'admin')  # 'super_admin' or 'admin'
        self.assigned_events = kwargs.get('assigned_events', [])  # List of event IDs for regular admins
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.last_login = kwargs.get('last_login')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'password_hash': self.password_hash,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'assigned_events': self.assigned_events,
            'is_active': self.is_active,
            'created_at': self._serialize_datetime(self.created_at),
            'last_login': self._serialize_datetime(self.last_login)
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create AdminUser from Firestore document"""
        data['id'] = doc_id
        data['created_at'] = cls._deserialize_datetime(data.get('created_at'))
        data['last_login'] = cls._deserialize_datetime(data.get('last_login'))
        return cls(**data)
    
    def save(self):
        """Save admin user to Firestore"""
        db = get_firestore_db()
        
        if self.id:
            doc_ref = db.collection(COLLECTIONS['admin_users']).document(self.id)
            doc_ref.update(self.to_dict())
        else:
            # Use username as document ID
            doc_ref = db.collection(COLLECTIONS['admin_users']).document(self.username)
            self.id = self.username
            doc_ref.set(self.to_dict())
        
        return self.id
    
    @classmethod
    def get_by_username(cls, username):
        """Get admin by username"""
        db = get_firestore_db()
        doc = db.collection(COLLECTIONS['admin_users']).document(username).get()
        
        if doc.exists:
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    def check_password(self, password):
        """Check if password is correct"""
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)


class EmailLog(FirestoreModel):
    """Email log model"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.event_id = kwargs.get('event_id')  # Link to Event
        self.registration_id = kwargs.get('registration_id')
        self.recipient_email = kwargs.get('recipient_email')
        self.subject = kwargs.get('subject')
        self.body = kwargs.get('body')
        self.sent_by = kwargs.get('sent_by')
        self.sent_at = kwargs.get('sent_at', datetime.utcnow())
        self.status = kwargs.get('status', 'sent')
        self.error_message = kwargs.get('error_message')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'registration_id': self.registration_id,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'body': self.body,
            'sent_by': self.sent_by,
            'sent_at': self._serialize_datetime(self.sent_at),
            'status': self.status,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create EmailLog from Firestore document"""
        data['id'] = doc_id
        data['sent_at'] = cls._deserialize_datetime(data.get('sent_at'))
        return cls(**data)
    
    def save(self):
        """Save email log to Firestore"""
        db = get_firestore_db()
        doc_ref = db.collection(COLLECTIONS['email_logs']).document()
        self.id = doc_ref.id
        doc_ref.set(self.to_dict())
        return self.id


class Venue(FirestoreModel):
    """Venue model for access control"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.event_id = kwargs.get('event_id')  # Link to Event
        self.name = kwargs.get('name')
        self.venue_type = kwargs.get('venue_type')  # 'entry', 'food', 'session', 'lounge', 'other'
        self.description = kwargs.get('description')
        self.capacity = kwargs.get('capacity')
        self.location = kwargs.get('location')
        self.requires_approval = kwargs.get('requires_approval', False)
        self.is_active = kwargs.get('is_active', True)
        self.access_limit = kwargs.get('access_limit', 'unlimited')  # 'unlimited', 'once', or numeric string like '2', '5'
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'name': self.name,
            'venue_type': self.venue_type,
            'description': self.description,
            'capacity': self.capacity,
            'location': self.location,
            'requires_approval': self.requires_approval,
            'is_active': self.is_active,
            'access_limit': self.access_limit,
            'created_at': self._serialize_datetime(self.created_at),
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create Venue from Firestore document"""
        data['id'] = doc_id
        data['created_at'] = cls._deserialize_datetime(data.get('created_at'))
        return cls(**data)
    
    def save(self):
        """Save venue to Firestore"""
        db = get_firestore_db()
        
        if self.id:
            doc_ref = db.collection(COLLECTIONS['venues']).document(self.id)
            doc_ref.update(self.to_dict())
        else:
            doc_ref = db.collection(COLLECTIONS['venues']).document()
            self.id = doc_ref.id
            doc_ref.set(self.to_dict())
        
        return self.id
    
    @classmethod
    def get_by_id(cls, doc_id):
        """Get venue by ID"""
        db = get_firestore_db()
        doc = db.collection(COLLECTIONS['venues']).document(doc_id).get()
        
        if doc.exists:
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    @classmethod
    def get_all(cls, is_active=None, event_id=None):
        """Get all venues"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['venues'])
        
        if event_id is not None:
            query = query.where('event_id', '==', event_id)
        
        if is_active is not None:
            query = query.where('is_active', '==', is_active)
        
        query = query.order_by('name')
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    @classmethod
    def delete(cls, doc_id):
        """Delete venue"""
        db = get_firestore_db()
        db.collection(COLLECTIONS['venues']).document(doc_id).delete()


class Volunteer(FirestoreModel):
    """Volunteer user model for QR scanner access"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.event_id = kwargs.get('event_id')  # Link to Event
        self.username = kwargs.get('username')
        self.password_hash = kwargs.get('password_hash')
        self.name = kwargs.get('name')
        self.email = kwargs.get('email')
        self.phone = kwargs.get('phone')
        self.assigned_venues = kwargs.get('assigned_venues', [])  # List of venue IDs
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by')
        self.last_login = kwargs.get('last_login')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'username': self.username,
            'password_hash': self.password_hash,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'assigned_venues': self.assigned_venues,
            'is_active': self.is_active,
            'created_at': self._serialize_datetime(self.created_at),
            'created_by': self.created_by,
            'last_login': self._serialize_datetime(self.last_login)
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create Volunteer from Firestore document"""
        data['id'] = doc_id
        data['created_at'] = cls._deserialize_datetime(data.get('created_at'))
        data['last_login'] = cls._deserialize_datetime(data.get('last_login'))
        return cls(**data)
    
    def save(self):
        """Save volunteer to Firestore"""
        db = get_firestore_db()
        
        if self.id:
            doc_ref = db.collection(COLLECTIONS['volunteers']).document(self.id)
            doc_ref.update(self.to_dict())
        else:
            # Use username as document ID
            doc_ref = db.collection(COLLECTIONS['volunteers']).document(self.username)
            self.id = self.username
            doc_ref.set(self.to_dict())
        
        return self.id
    
    @classmethod
    def get_by_username(cls, username):
        """Get volunteer by username"""
        db = get_firestore_db()
        doc = db.collection(COLLECTIONS['volunteers']).document(username).get()
        
        if doc.exists:
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    @classmethod
    def get_all(cls, event_id=None):
        """Get all volunteers"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['volunteers'])
        
        if event_id is not None:
            query = query.where('event_id', '==', event_id)
        
        query = query.order_by('name')
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    def check_password(self, password):
        """Check if password is correct"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Set password hash"""
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)
    
    @classmethod
    def delete(cls, username):
        """Delete volunteer"""
        db = get_firestore_db()
        db.collection(COLLECTIONS['volunteers']).document(username).delete()


class AccessLog(FirestoreModel):
    """Access log model - records when participants access venues"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.event_id = kwargs.get('event_id')  # Link to Event
        self.registration_id = kwargs.get('registration_id')
        self.registration_email = kwargs.get('registration_email')
        self.participant_name = kwargs.get('participant_name')
        self.venue_id = kwargs.get('venue_id')
        self.venue_name = kwargs.get('venue_name')
        self.action_type = kwargs.get('action_type', 'check-in')  # 'check-in', 'check-out', 'denied'
        self.scanned_by = kwargs.get('scanned_by')  # volunteer/admin username
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.notes = kwargs.get('notes')
        self.qr_code = kwargs.get('qr_code')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'registration_id': self.registration_id,
            'registration_email': self.registration_email,
            'participant_name': self.participant_name,
            'venue_id': self.venue_id,
            'venue_name': self.venue_name,
            'action_type': self.action_type,
            'scanned_by': self.scanned_by,
            'timestamp': self._serialize_datetime(self.timestamp),
            'notes': self.notes,
            'qr_code': self.qr_code
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create AccessLog from Firestore document"""
        data['id'] = doc_id
        data['timestamp'] = cls._deserialize_datetime(data.get('timestamp'))
        return cls(**data)
    
    def save(self):
        """Save access log to Firestore"""
        db = get_firestore_db()
        doc_ref = db.collection(COLLECTIONS['access_logs']).document()
        self.id = doc_ref.id
        doc_ref.set(self.to_dict())
        return self.id
    
    @classmethod
    def get_by_registration(cls, registration_id, limit=50):
        """Get access logs for a registration"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['access_logs'])\
            .where('registration_id', '==', registration_id)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(limit)
        
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    @classmethod
    def get_by_venue(cls, venue_id, limit=100):
        """Get access logs for a venue"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['access_logs'])\
            .where('venue_id', '==', venue_id)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(limit)
        
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    @classmethod
    def get_all(cls, limit=100, filters=None):
        """Get all access logs with filters"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['access_logs'])
        
        if filters:
            if filters.get('event_id'):
                query = query.where('event_id', '==', filters['event_id'])
            if filters.get('venue_id'):
                query = query.where('venue_id', '==', filters['venue_id'])
            if filters.get('action_type'):
                query = query.where('action_type', '==', filters['action_type'])
        
        query = query.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        docs = query.stream()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]


# Helper functions
def init_firebase():
    """Initialize Firebase and print status"""
    try:
        db = get_firestore_db()
        print("✅ Firebase Firestore initialized successfully")
        print(f"📊 Collections: {', '.join(COLLECTIONS.values())}")
        return db
    except Exception as e:
        print(f"❌ Firebase initialization failed: {e}")
        raise


class Event(FirestoreModel):
    """Event/Conference model for multi-event management"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.name = kwargs.get('name')
        self.year = kwargs.get('year')
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        self.location = kwargs.get('location')
        self.description = kwargs.get('description')
        self.is_active = kwargs.get('is_active', True)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by')  # Super admin username
        self.updated_at = kwargs.get('updated_at')
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'year': self.year,
            'start_date': self._serialize_datetime(self.start_date),
            'end_date': self._serialize_datetime(self.end_date),
            'location': self.location,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self._serialize_datetime(self.created_at),
            'created_by': self.created_by,
            'updated_at': self._serialize_datetime(self.updated_at)
        }
    
    @classmethod
    def from_dict(cls, doc_id, data):
        """Create Event from Firestore document"""
        data['id'] = doc_id
        data['created_at'] = cls._deserialize_datetime(data.get('created_at'))
        data['updated_at'] = cls._deserialize_datetime(data.get('updated_at'))
        data['start_date'] = cls._deserialize_datetime(data.get('start_date'))
        data['end_date'] = cls._deserialize_datetime(data.get('end_date'))
        return cls(**data)
    
    def save(self):
        """Save event to Firestore"""
        db = get_firestore_db()
        self.updated_at = datetime.utcnow()
        
        if self.id:
            doc_ref = db.collection(COLLECTIONS['events']).document(self.id)
            doc_ref.update(self.to_dict())
        else:
            doc_ref = db.collection(COLLECTIONS['events']).document()
            self.id = doc_ref.id
            doc_ref.set(self.to_dict())
        
        return self.id
    
    @classmethod
    def get_by_id(cls, doc_id):
        """Get event by ID"""
        db = get_firestore_db()
        doc = db.collection(COLLECTIONS['events']).document(doc_id).get()
        
        if doc.exists:
            return cls.from_dict(doc.id, doc.to_dict())
        return None
    
    @classmethod
    def get_all(cls, limit=100, filters=None):
        """Get all events with optional filters"""
        db = get_firestore_db()
        query = db.collection(COLLECTIONS['events'])
        
        # Apply filters
        if filters:
            if filters.get('is_active') is not None:
                query = query.where('is_active', '==', filters['is_active'])
            if filters.get('year'):
                query = query.where('year', '==', filters['year'])
        
        # Order by year and start_date descending
        query = query.order_by('year', direction=firestore.Query.DESCENDING)
        query = query.limit(limit)
        
        docs = query.get()
        return [cls.from_dict(doc.id, doc.to_dict()) for doc in docs]
    
    @classmethod
    def delete(cls, doc_id):
        """Delete event"""
        db = get_firestore_db()
        db.collection(COLLECTIONS['events']).document(doc_id).delete()


def create_default_admin():
    """Create default admin user if none exists"""
    try:
        admin = AdminUser.get_by_username('admin')
        
        if admin is None:
            # Create default admin
            admin = AdminUser(
                username='admin',
                email='admin@gdta2026.com',
                name='Administrator',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            admin.save()
            
            print("✅ Default admin created")
            print("   Username: admin")
            print("   Password: admin123")
            print("   ⚠️  IMPORTANT: Change password in production!")
        else:
            print("ℹ️  Admin user already exists")
    
    except Exception as e:
        print(f"❌ Failed to create admin: {e}")
        raise


if __name__ == '__main__':
    # Initialize Firebase when run directly
    print("Initializing GDTA 2026 Firebase Firestore...")
    init_firebase()
    create_default_admin()
    print("✅ Firebase setup complete!")
