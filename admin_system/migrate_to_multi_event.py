#!/usr/bin/env python3
"""
Migrate existing data to multi-event system
Creates a default "GDTA 2026" event and assigns all existing data to it
"""

import os
import sys

# Add the chatbot directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from db.firebase_config import get_firestore_db, COLLECTIONS
from db.firebase_models import Event, Registration, Venue, Volunteer, EmailLog, AccessLog, AdminUser

def migrate_to_multi_event():
    """Migrate all existing data to the multi-event system"""
    print("=" * 70)
    print("GDTA 2026 - Multi-Event System Migration")
    print("=" * 70)
    print()
    
    try:
        db = get_firestore_db()
        
        # Step 1: Create default "GDTA 2026" event
        print("📅 Step 1: Creating default event 'GDTA 2026'...")
        
        # Check if default event already exists
        events = Event.get_all()
        default_event = None
        
        for event in events:
            if event.name == "GDTA 2026":
                default_event = event
                print(f"   ✅ Default event already exists (ID: {event.id})")
                break
        
        if not default_event:
            default_event = Event(
                name="GDTA 2026",
                year=2026,
                start_date=datetime(2026, 3, 1),
                end_date=datetime(2026, 3, 5),
                location="To be announced",
                description="Global Diaspora Tech Accelerator 2026",
                is_active=True,
                created_by="system"
            )
            default_event.save()
            print(f"   ✅ Created default event (ID: {default_event.id})")
        
        event_id = default_event.id
        print()
        
        # Step 2: Migrate registrations
        print("👥 Step 2: Migrating registrations...")
        registrations = Registration.get_all(limit=1000)
        reg_count = 0
        
        for reg in registrations:
            if not hasattr(reg, 'event_id') or not reg.event_id:
                reg.event_id = event_id
                reg.save()
                reg_count += 1
        
        print(f"   ✅ Migrated {reg_count} registrations to event '{default_event.name}'")
        print()
        
        # Step 3: Migrate venues
        print("🏢 Step 3: Migrating venues...")
        venues_query = db.collection(COLLECTIONS['venues']).stream()
        venue_count = 0
        
        for doc in venues_query:
            venue_data = doc.to_dict()
            if 'event_id' not in venue_data or not venue_data['event_id']:
                db.collection(COLLECTIONS['venues']).document(doc.id).update({'event_id': event_id})
                venue_count += 1
        
        print(f"   ✅ Migrated {venue_count} venues to event '{default_event.name}'")
        print()
        
        # Step 4: Migrate volunteers
        print("🙋 Step 4: Migrating volunteers...")
        volunteers_query = db.collection(COLLECTIONS['volunteers']).stream()
        volunteer_count = 0
        
        for doc in volunteers_query:
            volunteer_data = doc.to_dict()
            if 'event_id' not in volunteer_data or not volunteer_data['event_id']:
                db.collection(COLLECTIONS['volunteers']).document(doc.id).update({'event_id': event_id})
                volunteer_count += 1
        
        print(f"   ✅ Migrated {volunteer_count} volunteers to event '{default_event.name}'")
        print()
        
        # Step 5: Migrate access logs
        print("📋 Step 5: Migrating access logs...")
        logs_query = db.collection(COLLECTIONS['access_logs']).stream()
        log_count = 0
        
        for doc in logs_query:
            log_data = doc.to_dict()
            if 'event_id' not in log_data or not log_data['event_id']:
                db.collection(COLLECTIONS['access_logs']).document(doc.id).update({'event_id': event_id})
                log_count += 1
        
        print(f"   ✅ Migrated {log_count} access logs to event '{default_event.name}'")
        print()
        
        # Step 6: Migrate email logs
        print("📧 Step 6: Migrating email logs...")
        emails_query = db.collection(COLLECTIONS['email_logs']).stream()
        email_count = 0
        
        for doc in emails_query:
            email_data = doc.to_dict()
            if 'event_id' not in email_data or not email_data['event_id']:
                db.collection(COLLECTIONS['email_logs']).document(doc.id).update({'event_id': event_id})
                email_count += 1
        
        print(f"   ✅ Migrated {email_count} email logs to event '{default_event.name}'")
        print()
        
        # Step 7: Update existing admins
        print("👑 Step 7: Updating admin users...")
        admins_query = db.collection(COLLECTIONS['admin_users']).stream()
        admin_count = 0
        
        for doc in admins_query:
            admin_data = doc.to_dict()
            # Add assigned_events field if it doesn't exist
            if 'assigned_events' not in admin_data:
                # Regular admins get assigned to the default event
                # Super admins get empty list (access to all events)
                role = admin_data.get('role', 'admin')
                assigned_events = [] if role == 'super_admin' else [event_id]
                
                db.collection(COLLECTIONS['admin_users']).document(doc.id).update({
                    'assigned_events': assigned_events
                })
                admin_count += 1
        
        print(f"   ✅ Updated {admin_count} admin users")
        print()
        
        # Summary
        print("=" * 70)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  • Event Created: {default_event.name} (ID: {event_id})")
        print(f"  • Registrations: {reg_count}")
        print(f"  • Venues: {venue_count}")
        print(f"  • Volunteers: {volunteer_count}")
        print(f"  • Access Logs: {log_count}")
        print(f"  • Email Logs: {email_count}")
        print(f"  • Admins Updated: {admin_count}")
        print()
        print("All existing data has been successfully migrated to the multi-event system!")
        print()
        print("Next Steps:")
        print("  1. Visit http://localhost:5001/static/super-admin-setup.html")
        print("  2. Create your first Super Admin account")
        print("  3. Log in and manage events and admins")
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    migrate_to_multi_event()
