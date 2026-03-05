#!/usr/bin/env python3
"""
Post-Deployment Setup Script for Render
Runs migrations and setup tasks after deployment
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.firebase_models import Event, Registration, AdminUser, init_firebase
from datetime import datetime

def main():
    print("=" * 60)
    print("GDTA 2026 - Post-Deployment Setup")
    print("=" * 60)
    
    try:
        # Initialize Firebase
        print("\n1. Initializing Firebase...")
        init_firebase()
        print("✓ Firebase initialized")
        
        # Create GDTA 2026 event if it doesn't exist
        print("\n2. Checking GDTA 2026 event...")
        event = Event.get_by_id('gdta-2026')
        if not event:
            print("  Creating GDTA 2026 event...")
            event = Event(
                id='gdta-2026',
                name='GDTA 2026',
                year=2026,
                start_date=datetime(2026, 6, 4),
                end_date=datetime(2026, 6, 6),
                location='SNS College of Technology, Coimbatore',
                description='Global Digital Transformation Alliance Conference 2026',
                is_active=True,
                created_by='system'
            )
            event.save()
            print("✓ Event created")
        else:
            print(f"✓ Event exists: {event.name}")
        
        # Migrate registrations to have correct event_id
        print("\n3. Migrating registrations...")
        all_regs = Registration.get_all(limit=1000, filters=None)
        print(f"  Found {len(all_regs)} registrations")
        
        need_migration = [r for r in all_regs if not r.event_id or r.event_id != 'gdta-2026']
        if need_migration:
            print(f"  Migrating {len(need_migration)} registrations...")
            for reg in need_migration:
                reg.event_id = 'gdta-2026'
                reg.save()
            print(f"✓ Migrated {len(need_migration)} registrations")
        else:
            print("✓ All registrations already have correct event_id")
        
        # Update admin user assigned_events
        print("\n4. Updating admin user...")
        admin = AdminUser.get_by_username('admin')
        if admin:
            if admin.assigned_events != ['gdta-2026']:
                admin.assigned_events = ['gdta-2026']
                admin.save()
                print("✓ Admin assigned_events updated")
            else:
                print("✓ Admin already assigned to gdta-2026")
        else:
            print("⚠ Admin user not found (will be created on first run)")
        
        # Summary
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        regs_gdta = Registration.get_all(limit=1000, filters={'event_id': 'gdta-2026'})
        print(f"✓ Total registrations with event_id='gdta-2026': {len(regs_gdta)}")
        print(f"✓ Event 'GDTA 2026' is active")
        print(f"✓ Admin dashboard ready")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
