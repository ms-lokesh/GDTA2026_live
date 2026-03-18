# Restructuring Summary

## What Changed

The GDTA 2026 project has been restructured to separate the reusable event management system from event-specific components.

### New Structure

```
GDTA2026/
├── event_manager/              ✅ NEW: Standalone reusable system
│   ├── app.py
│   ├── config.yaml
│   ├── requirements.txt
│   ├── README.md
│   ├── FEATURES.md
│   ├── db/
│   ├── logic/
│   ├── routes/ (no chat.py)
│   ├── static/
│   └── templates/
│
├── gdta_chatbot/               ✅ NEW: GDTA-specific chatbot
│   ├── routes/chat.py
│   ├── chatbot-widget.js
│   ├── chatbot-widget.html
│   └── README.md
│
├── admin_system/               ⚠️ OLD: Keep for reference or delete
│   └── (original files)
│
└── (website files)             ✅ UNCHANGED: GDTA website HTML/CSS/JS
```

## What Is event_manager?

**event_manager** is a standalone, production-ready event management system that can be reused for ANY event.

### Features Include:
✅ Multi-event management (one system, unlimited events)
✅ Role-based access (Super Admin, Admin, Volunteer)
✅ Registration system with approval workflow
✅ Check-in system with QR scanner
✅ ID card generation (bulk & individual)
✅ Email template management
✅ Advanced filtering & search
✅ Export to CSV/Excel/PDF
✅ Real-time statistics
✅ Bulk operations

### What's NOT Included:
❌ Chatbot (moved to gdta_chatbot)
❌ Event-specific logic
❌ GDTA-specific branding (configurable)

## How to Use event_manager for a New Event

### Option 1: Copy to New Project

```bash
# For a new event called "TechConf 2027"
cp -r event_manager /path/to/techconf2027/
cd /path/to/techconf2027/event_manager

# Configure
cp config.example.yaml config.yaml
cp .env.example .env

# Edit config.yaml with your event details
# Add Firebase credentials to db/firebase-credentials.json

# Run
python3 app.py
```

### Option 2: Keep as Shared System

```bash
# Use the same event_manager for multiple events
cd event_manager
python3 app.py

# Access super admin dashboard
open http://localhost:5001/super-admin

# Create multiple events in the UI
# - GDTA 2026
# - Tech Conference 2027
# - Workshop Series 2026
```

## What Is gdta_chatbot?

**gdta_chatbot** is the GDTA-specific chatbot that:
- Uses Google Gemini AI
- Has GDTA 2026 conference knowledge
- Helps attendees with queries
- Initiates registrations through chat
- **Is NOT part of the reusable system**

### To use chatbot with event_manager:

```python
# In event_manager/app.py, add:
from sys import path
path.insert(0, '../gdta_chatbot')
from routes.chat import chat_bp
app.register_blueprint(chat_bp)
```

## Configuration System

### config.yaml (Main Config)

```yaml
app:
  name: "Your Event Manager"
  port: 5001

branding:
  organization_name: "Your Organization"
  default_event_name: "Your Event 2026"
  
features:
  registration: true
  check_in: true
  email_templates: true
```

### .env (Secrets)

```bash
SECRET_KEY=your-secret-key
FIREBASE_CREDENTIALS_PATH=db/firebase-credentials.json
```

## Migrating from admin_system to event_manager

### For GDTA 2026 Project

**Keep Running**:
The old admin_system still works. No immediate changes needed.

**To Switch**:
1. Stop admin_system: `lsof -ti:5001 | xargs kill -9`
2. Start event_manager: `cd event_manager && python3 app.py`
3. Access dashboards at same URLs
4. All data is in Firebase (shared between both systems)

### Database Compatibility

✅ Both systems use the SAME Firebase database
✅ No data migration needed
✅ Events and registrations work in both
✅ Can switch back and forth

## Testing Checklist

- [x] event_manager starts successfully
- [x] API endpoints respond correctly
- [x] Super admin dashboard accessible
- [x] Admin dashboard accessible
- [x] Firebase connection works
- [x] Config system loads properly
- [x] Documentation is comprehensive

## Next Steps

### For GDTA 2026:
1. ✅ Test event_manager with existing data
2. ⬜ Update deployment scripts if needed
3. ⬜ Decide whether to keep or delete admin_system folder

### For New Events:
1. ⬜ Copy event_manager folder to new project
2. ⬜ Update config.yaml with event details
3. ⬜ Add Firebase credentials
4. ⬜ Customize branding/templates
5. ⬜ Deploy and run!

## Benefits of This Structure

### Reusability
- Copy event_manager to any new event project
- No event-specific code to remove
- Works out of the box with minimal configuration

### Maintainability
- Clear separation of concerns
- Event-specific code isolated
- Core system improvements benefit all events

### Scalability
- One system, unlimited events
- Multi-tenant by design
- Role-based access control built-in

### Flexibility
- Enable/disable features via config
- Customize branding per deployment
- Optional modules (chatbot, hackathon, etc.)

## Files Created

1. **event_manager/app.py** - Config-driven Flask app
2. **event_manager/config.yaml** - Application configuration
3. **event_manager/config.example.yaml** - Configuration template
4. **event_manager/.env.example** - Environment variables template
5. **event_manager/requirements.txt** - Updated with PyYAML
6. **event_manager/README.md** - Comprehensive setup guide
7. **event_manager/FEATURES.md** - Detailed feature documentation
8. **event_manager/db/firebase_models.py** - Updated create_default_admin()
9. **gdta_chatbot/README.md** - Chatbot documentation
10. **RESTRUCTURE_SUMMARY.md** - This document

## Support

- **Event Manager Docs**: `event_manager/README.md`
- **Features Guide**: `event_manager/FEATURES.md`
- **Chatbot Docs**: `gdta_chatbot/README.md`

## Questions?

**Q: Do I need to migrate data?**  
A: No, both systems use the same Firebase database.

**Q: Can I still use the old admin_system?**  
A: Yes, it still works. event_manager is an alternative, not a replacement (yet).

**Q: How do I use this for a new event?**  
A: Copy event_manager folder, update config.yaml, add Firebase creds, run!

**Q: What about the chatbot?**  
A: Chatbot is event-specific. For new events, create a new chatbot or use event_manager without one.

**Q: Is this production-ready?**  
A: Yes! All features from admin_system are included and tested.

---

✅ **Restructuring Complete**  
📦 **event_manager** is ready to use for any event!  
🎉 **GDTA 2026** can continue using either system!
