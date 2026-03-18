from db.firebase_config import get_firestore_db, COLLECTIONS

db = get_firestore_db()

# Get all events
events_ref = db.collection(COLLECTIONS['events']).stream()
events = list(events_ref)

print(f"Total events found: {len(events)}\n")

for event in events:
    event_data = event.to_dict()
    print(f"Event: {event_data.get('name')}")
    print(f"  Doc ID: {event.id}")
    print(f"  Event ID: {event_data.get('event_id', 'NOT SET')}")
    print(f"  Year: {event_data.get('year')}")
    print(f"  Active: {event_data.get('is_active')}")
    print()

# Check registrations
print("=" * 50)
print("Checking registrations...")
print("=" * 50 + "\n")

reg_ref = db.collection(COLLECTIONS['registrations']).stream()
registrations = list(reg_ref)

print(f"Total registrations: {len(registrations)}")

# Group by event_id
event_id_counts = {}
for reg in registrations:
    reg_data = reg.to_dict()
    event_id = reg_data.get('event_id', 'NO_EVENT_ID')
    event_id_counts[event_id] = event_id_counts.get(event_id, 0) + 1

print("\nRegistrations by event_id:")
for event_id, count in event_id_counts.items():
    print(f"  {event_id}: {count} registrations")
