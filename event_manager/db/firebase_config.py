"""
Firebase Configuration for GDTA 2026
Cloud Firestore database connection
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Firebase
_db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global _db
    
    if _db is not None:
        return _db
    
    try:
        # Check if already initialized
        firebase_admin.get_app()
        _db = firestore.client()
        return _db
    except ValueError:
        pass
    
    # Get credentials from environment
    firebase_creds = os.getenv('FIREBASE_CREDENTIALS')
    
    if firebase_creds:
        # Production: Credentials from environment variable (JSON string)
        try:
            cred_dict = json.loads(firebase_creds)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized from environment credentials")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing FIREBASE_CREDENTIALS JSON: {e}")
            raise
    else:
        # Development: Credentials from file
        cred_path = os.path.join(os.path.dirname(__file__), 'firebase-credentials.json')
        
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(f"✅ Firebase initialized from file: {cred_path}")
        else:
            print("⚠️  Firebase credentials not found!")
            print("Please add firebase-credentials.json or set FIREBASE_CREDENTIALS environment variable")
            raise FileNotFoundError("Firebase credentials not configured")
    
    _db = firestore.client()
    return _db


def get_firestore_db():
    """Get Firestore database instance"""
    if _db is None:
        return initialize_firebase()
    return _db


# Collection names
COLLECTIONS = {
    'events': 'events',
    'registrations': 'registrations',
    'hackathon_registrations': 'hackathon_registrations',
    'admin_users': 'admin_users',
    'email_logs': 'email_logs',
    'email_templates': 'email_templates',
    'venues': 'venues',
    'access_logs': 'access_logs',
    'volunteers': 'volunteers'
}
