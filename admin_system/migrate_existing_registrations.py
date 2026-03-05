#!/usr/bin/env python3
"""
Migrate existing registrations to add event_id field
This fixes registrations created before the event_id field was added
"""

from db.firebase_models import Registration, init_firebase

def main():
    print("Initializing Firebase...")
    init_firebase()
    
    print("\nFetching all registrations...")
    all_regs = Registration.get_all(limit=1000, filters=None)
    print(f"Found {len(all_regs)} total registrations")
    
    # Find registrations without event_id or with wrong event_id
    need_migration = [r for r in all_regs if not r.event_id or r.event_id != 'gdta-2026']
    print(f"Found {len(need_migration)} registrations needing event_id update")
    
    if not need_migration:
        print("✓ All registrations already have event_id='gdta-2026'. No migration needed.")
        return
    
    print("\nMigrating registrations to event_id='gdta-2026'...")
    
    success_count = 0
    fail_count = 0
    
    for reg in need_migration:
        try:
            # Set event_id to gdta-2026
            reg.event_id = 'gdta-2026'
            reg.save()
            print(f"✓ Updated {reg.email}")
            success_count += 1
        except Exception as e:
            print(f"✗ Failed to update {reg.email}: {e}")
            fail_count += 1
    
    print(f"\n{'='*60}")
    print(f"Migration complete!")
    print(f"  Success: {success_count}")
    print(f"  Failed: {fail_count}")
    print(f"{'='*60}")
    
    # Verify
    print("\nVerifying migration...")
    regs_with_event = Registration.get_all(limit=1000, filters={'event_id': 'gdta-2026'})
    print(f"✓ Total registrations with event_id='gdta-2026': {len(regs_with_event)}")

if __name__ == '__main__':
    main()
