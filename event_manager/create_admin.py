#!/usr/bin/env python3
"""
Script to create default admin user for Event Manager
"""
import sys
import os
sys.path.append('.')

from db.firebase_models import create_default_admin

if __name__ == '__main__':
    try:
        print("Creating default admin user...")
        create_default_admin(
            username='admin',
            password='changeme123',
            name='Super Admin',
            email='admin@yourevent.com'
        )
        print("✅ Admin creation completed!")
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        sys.exit(1)