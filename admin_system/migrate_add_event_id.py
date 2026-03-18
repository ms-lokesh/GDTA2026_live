#!/usr/bin/env python3
"""
Migration script to add event_id field to existing Event documents
This links events to registrations properly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.firebase_config import get_firestore_db, COLLECTIONS
from db.firebase_models import Event

def migrate_add_event_id():
    """Add event_id field to all existing events"""
    db = get_firestore_db()
    
    print("🔍 Fetching all events...")
    events_ref = db.collection(COLLECTIONS['events'])
    events = events_ref.stream()
    
    updated_count = 0
    
    for doc in events:
        event_data = doc.to_dict()
        event_id_value = event_data.get('event_id')
        
        # If event_id is missing, generate it
        if not event_id_value:
            name = event_data.get('name', '')
            year = event_data.get('year', '')
            
            if name and year:
                # Generate event_id: gdta-2026, conference-2027, etc.
                name_slug = name.lower().replace(' ', '-').replace('_', '-')
                event_id_value = f"{name_slug}-{year}"
                
                print(f"📝 Event: {name} ({year})")
                print(f"   Firebase Doc ID: {doc.id}")
                print(f"   Generated event_id: {event_id_value}")
                
                # Update the document
                events_ref.document(doc.id).update({
                    'event_id': event_id_value
                })
                
                updated_count += 1
                print(f"   ✅ Updated")
            else:
                print(f"⚠️  Event {doc.id} missing name or year, skipping")
        else:
            print(f"✓ Event {event_data.get('name')} already has event_id: {event_id_value}")
    
    print(f"\n✅ Migration complete! Updated {updated_count} event(s)")
    print("\nNow registrations will be linked via the event_id field.")

if __name__ == '__main__':
    migrate_add_event_id()
