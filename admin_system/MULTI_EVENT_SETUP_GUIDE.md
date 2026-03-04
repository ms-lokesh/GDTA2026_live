# Multi-Event Super Admin System - Setup Guide

## 🎯 Overview

The system now supports **hierarchical role-based access control** with multi-event management:

- **Super Admin**: Creates events, manages admins, full access to everything
- **Regular Admin**: Manages only their assigned event(s) - registrations, venues, volunteers, etc.

Each event has its own separate:
- Registrations
- Venues
- Volunteers  
- Access logs
- Email logs

## 🚀 Quick Start Guide

### Step 1: Run the Migration Script

First, migrate your existing data to the new multi-event system:

```bash
cd /Users/user/gdta/GDTA2026/chatbot
python3 migrate_to_multi_event.py
```

This will:
- Create a default "GDTA 2026" event
- Assign all existing registrations, venues, volunteers, logs to this event
- Update all admin users with `assigned_events` field

### Step 2: Create Your First Super Admin

1. Start the Flask app (if not running):
   ```bash
   python3 app.py
   ```

2. Visit the super admin setup page:
   ```
   http://localhost:5001/static/super-admin-setup.html
   ```

3. Fill in the form:
   - **Username**: Choose a unique username (e.g., `superadmin`)
   - **Full Name**: Your name
   - **Email**: Your email address
   - **Password**: Strong password (min 8 characters)
   - **Confirm Password**: Re-enter password

4. Click "Create Super Admin"

5. You'll be redirected to the login page

### Step 3: Login as Super Admin

1. Go to: `http://localhost:5001/static/admin-dashboard.html`
2. Login with your super admin credentials
3. You'll have access to all features plus event/admin management

## 📋 Available API Endpoints

### Super Admin Only (requires `role: 'super_admin'`)

#### Event Management
```
GET    /api/superadmin/events           # List all events
POST   /api/superadmin/events           # Create new event
PUT    /api/superadmin/events/:id       # Update event
DELETE /api/superadmin/events/:id       # Delete event
```

**Create Event Example:**
```json
POST /api/superadmin/events
{
  "name": "GDTA 2027",
  "year": 2027,
  "start_date": "2027-03-01",
  "end_date": "2027-03-05",
  "location": "New York, USA",
  "description": "Global Diaspora Tech Accelerator 2027",
  "is_active": true
}
```

#### Admin Management
```
GET    /api/superadmin/admins           # List all admins
POST   /api/superadmin/admins           # Create new admin
PUT    /api/superadmin/admins/:username # Update admin
DELETE /api/superadmin/admins/:username # Delete admin
```

**Create Admin Example:**
```json
POST /api/superadmin/admins
{
  "username": "admin2027",
  "password": "SecurePass123",
  "name": "John Doe",
  "email": "john@example.com",
  "role": "admin",
  "assigned_events": ["event_id_here"],
  "is_active": true
}
```

### All Authenticated Users

```
GET /api/admin/me  # Get current user info (shows role and assigned_events)
```

## 🔒 Access Control Rules

### Super Admin (`role: 'super_admin'`)
- Can create/edit/delete events
- Can create/edit/delete admins
- Can access ALL events' data
- `assigned_events` is empty (not used)

### Regular Admin (`role: 'admin'`)
- Can only access data from their `assigned_events` list
- Cannot create events
- Cannot manage other admins
- Can manage: registrations, venues, volunteers, emails, access logs (for their events only)

## 📊 Database Schema Changes

### New Model: `Event`
```python
{
  "id": "auto_generated",
  "name": "GDTA 2026",
  "year": 2026,
  "start_date": "2026-03-01",
  "end_date": "2026-03-05",
  "location": "TBA",
  "description": "...",
  "is_active": true,
  "created_at": "...",
  "created_by": "superadmin",
  "updated_at": "..."
}
```

### Updated Model: `AdminUser`
```python
{
  ...existing fields...,
  "role": "super_admin" | "admin",  # New field
  "assigned_events": ["event_id1", "event_id2"]  # New field
}
```

### All Other Models (Registration, Venue, Volunteer, AccessLog, EmailLog)
```python
{
  "event_id": "event_id_here",  # New field - links to Event
  ...existing fields...
}
```

## 🛠️ Updating Existing Code

### Before (Old System)
```python
# Everyone had full access
registrations = Registration.get_all()
venues = Venue.get_all()
```

### After (New System)
```python
# Regular admins must filter by event
admin = get_current_admin()

if admin.role == 'super_admin':
    # Super admin sees all events
    registrations = Registration.get_all()
else:
    # Regular admin sees only assigned events
    registrations = Registration.get_all(filters={'event_id': admin.assigned_events[0]})
```

## 🎨 Frontend Updates Needed

You'll need to update the admin dashboard to:

1. **Show event selector** (for super admins to switch between events)
2. **Add "Event Management" tab** (super admin only) - CRUD for events
3. **Add "Admin Management" tab** (super admin only) - CRUD for admins
4. **Filter all queries by event_id** (for regular admins)

Example event selector:
```javascript
// Check if user is super admin
const currentAdmin = await fetch('/api/admin/me').then(r => r.json());

if (currentAdmin.admin.role === 'super_admin') {
    // Show event selector dropdown
    // When event selected, set currentEventId and reload data
} else {
    // Regular admin - use their assigned event
    currentEventId = currentAdmin.admin.assigned_events[0];
}
```

## ⚠️ Important Notes

1. **Super Admin Setup Page** can only be used ONCE (when no super admin exists)
2. **Cannot delete the last super admin** (system protection)
3. **Migration is required** before the new system works properly
4. **All existing data** will be assigned to the default "GDTA 2026" event
5. **Regular admins** need at least one event assigned to access the system

## 🔄 Migration Rollback

If you need to rollback, the original data is preserved. The migration only ADDS the `event_id` field, it doesn't remove anything.

To rollback:
1. Restore the previous version of `firebase_models.py`
2. Remove `event_id` fields from Firestore (optional)

## 📞 Testing the System

### Test Super Admin Access
```bash
# Login as super admin
curl -X POST http://localhost:5001/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"username":"superadmin","password":"your_password"}'

# Get all events (should work)
curl -X GET http://localhost:5001/api/superadmin/events \
  -H "Cookie: session=..."
```

### Test Regular Admin Access  
```bash
# Try to access super admin routes (should fail with 403)
curl -X GET http://localhost:5001/api/superadmin/events \
  -H "Cookie: session_from_regular_admin"

# Response: {"error": "Super admin access required", "code": "FORBIDDEN"}
```

## 🎉 Benefits of This System

1. **Multi-tenant support** - Run multiple conferences from one system
2. **Proper access control** - Admins only see their event data
3. **Scalability** - Easy to add new events
4. **Security** - Role-based permissions
5. **Data isolation** - Each event's data is separate

---

**Next Steps:**
1. Run the migration script
2. Create your super admin account
3. Update the admin dashboard UI to support multi-event selection
4. Test the new access control

For questions or issues, check the implementation in:
- `/chatbot/db/firebase_models.py` - Data models
- `/chatbot/routes/admin.py` - API endpoints
- `/chatbot/static/super-admin-setup.html` - Setup page
