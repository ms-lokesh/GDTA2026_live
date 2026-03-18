#!/usr/bin/env python3
"""
Script to list existing admin users in Firebase
"""
import sys
import os
sys.path.append('.')

from db.firebase_config import get_firestore_db, COLLECTIONS
from db.firebase_models import AdminUser

if __name__ == '__main__':
    try:
        print("Listing all admin users...")
        
        # Get all admin users directly from Firestore
        db = get_firestore_db()
        admin_collection = db.collection(COLLECTIONS['admin_users']).get()
        
        if not admin_collection:
            print("No admin users found.")
        else:
            print(f"Found {len(admin_collection)} admin user(s):")
            for doc in admin_collection:
                data = doc.to_dict()
                admin = AdminUser.from_dict(doc.id, data)
                print(f"  - Username: {admin.username}")
                print(f"    Name: {admin.name}")
                print(f"    Email: {admin.email}")
                print(f"    Role: {admin.role}")
                print(f"    Active: {admin.is_active}")
                print(f"    Created: {admin.created_at}")
                print(f"    Has Password: {bool(admin.password_hash)}")
                print()
                
    except Exception as e:
        print(f"❌ Error listing admins: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)