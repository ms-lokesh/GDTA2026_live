#!/usr/bin/env python3
"""
Create default GDTA 2026 event in Firebase
"""

from db.firebase_models import Event, Registration, init_firebase
from datetime import datetime

def main():
    print("Initializing Firebase...")
    init_firebase()
    
    # Check if gdta-2026 event exists
    event = Event.get_by_id('gdta-2026')
    if event:
        print(f'✓ Event gdta-2026 already exists: {event.name}')
    else:
        print('✗ Event gdta-2026 does NOT exist')
        print('Creating default event...')
        
        # Create the event
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
        event_id = event.save()
        print(f'✓ Created event: {event_id}')
    
    # Check registrations count
    print('\nChecking registrations...')
    regs = Registration.get_all(filters={'event_id': 'gdta-2026'}, limit=10)
    print(f'✓ Found {len(regs)} registrations with event_id=gdta-2026')
    
    if regs:
        print('\nSample registration:')
        print(f'  Name: {regs[0].name}')
        print(f'  Email: {regs[0].email}')
        print(f'  Event ID: {regs[0].event_id}')

if __name__ == '__main__':
    main()
