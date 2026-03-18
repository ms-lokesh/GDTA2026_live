"""
Database Models for GDTA 2026 Registration System
Supports both SQLite (development) and PostgreSQL (production)
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()


def get_database_url():
    """
    Get database URL from environment or use SQLite as fallback
    
    For PostgreSQL, set DATABASE_URL in .env:
    DATABASE_URL=postgresql://username:password@localhost:5432/gdta2026
    
    For production (Heroku, Railway, etc):
    DATABASE_URL=postgresql://user:pass@host:port/dbname
    """
    db_url = os.getenv('DATABASE_URL')
    
    if db_url:
        # Handle Heroku's postgres:// URL (should be postgresql://)
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        return db_url
    
    # Fallback to SQLite for development
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, '..', 'gdta_registrations.db')
    return f'sqlite:///{db_path}'


class Registration(Base):
    """Registration model - stores all conference registrations"""
    __tablename__ = 'registrations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Registration data
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    institution = Column(String(300), nullable=False)
    role = Column(String(100), nullable=False)
    
    # GDTA membership
    gdta_member = Column(String(50), nullable=False)  # Yes/No/Not Sure
    gdta_affiliation = Column(String(200), nullable=True)
    
    # Location
    country = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=True)  # Only for India
    
    # Consent
    consent = Column(String(10), nullable=False)  # Yes/No
    
    # Metadata
    registration_source = Column(String(50), default='chatbot')  # chatbot/webform
    session_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Admin fields
    status = Column(String(50), default='pending')  # pending/approved/rejected
    admin_notes = Column(Text, nullable=True)
    
    def to_dict(self):
        """Convert registration to dictionary"""
        return {
            'id': self.id,
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'admin_notes': self.admin_notes
        }


class AdminUser(Base):
    """Admin user model - coordinators and SPOCs"""
    __tablename__ = 'admin_users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    role = Column(String(50), default='coordinator')  # coordinator/spoc/admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert admin user to dictionary (without password)"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class EmailLog(Base):
    """Email log - track all emails sent to registrants"""
    __tablename__ = 'email_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    registration_id = Column(Integer, nullable=True)  # Can be bulk email
    recipient_email = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    sent_by = Column(String(100), nullable=False)  # Admin username
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='sent')  # sent/failed
    error_message = Column(Text, nullable=True)
    
    def to_dict(self):
        """Convert email log to dictionary"""
        return {
            'id': self.id,
            'registration_id': self.registration_id,
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'body': self.body,
            'sent_by': self.sent_by,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'status': self.status,
            'error_message': self.error_message
        }


# Database initialization functions
def get_database_path():
    """Get the path to the database file (SQLite only)"""
    db_dir = os.path.join(os.path.dirname(__file__), '..')
    db_path = os.path.join(db_dir, 'gdta_registrations.db')
    return db_path


def init_db():
    """Initialize database - create all tables"""
    db_url = get_database_url()
    
    # Create engine with appropriate settings
    if db_url.startswith('sqlite'):
        engine = create_engine(db_url, echo=False)
        print(f"Database initialized (SQLite): {get_database_path()}")
    else:
        # PostgreSQL - use pool for better connection management
        engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600    # Recycle connections after 1 hour
        )
        print(f"Database initialized (PostgreSQL): {db_url.split('@')[1] if '@' in db_url else 'connected'}")
    
    Base.metadata.create_all(engine)
    return engine


def get_db_session():
    """Get a database session"""
    db_url = get_database_url()
    
    if db_url.startswith('sqlite'):
        engine = create_engine(db_url, echo=False)
    else:
        engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600
        )
    
    Session = sessionmaker(bind=engine)
    return Session()


def create_default_admin():
    """Create a default admin user if none exists"""
    from werkzeug.security import generate_password_hash
    
    session = get_db_session()
    
    # Check if any admin exists
    admin_count = session.query(AdminUser).count()
    
    if admin_count == 0:
        # Create default admin
        default_admin = AdminUser(
            username='admin',
            password_hash=generate_password_hash('admin123'),  # Change in production!
            email='admin@gdta2026.com',
            name='Administrator',
            role='admin',
            is_active=True
        )
        session.add(default_admin)
        session.commit()
        print("Default admin created: username='admin', password='admin123'")
        print("⚠️  IMPORTANT: Change the default password in production!")
    
    session.close()


if __name__ == '__main__':
    # Initialize database when run directly
    print("Initializing GDTA 2026 Registration Database...")
    init_db()
    create_default_admin()
    print("Database setup complete!")
