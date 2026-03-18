# Event Manager

A standalone, reusable event management system with multi-event support, role-based dashboards, and comprehensive attendee management features.

## 🌟 Features

### Multi-Event Management
- **Super Admin Dashboard**: Manage multiple events from a single interface
- **Event Creation**: Create and configure unlimited events
- **Admin Assignment**: Assign specific admins to specific events
- **Event Switching**: Seamlessly switch between different events

### Registration System
- ✅ Public registration form with customizable fields
- ✅ Approval workflow (pending → approved/rejected)
- ✅ Advanced filtering & search (by date, country, status, GDTA membership, etc.)
- ✅ Bulk operations (approve, reject, email)
- ✅ Email template management
- ✅ Export to CSV, Excel, PDF

### Check-in System
- 📱 QR code scanner for volunteers
- 📱 Check-in tracking with timestamp
- 📱 Dual scanner access (admin + volunteer dashboards)
- 📱 Real-time check-in statistics

### ID Card Generation
- 🎫 Beautiful, customizable ID cards
- 🎫 QR code integration for scanning
- 🎫 Bulk generation & download
- 🎫 On-demand regeneration
- 🎫 Template-based design system

### Dashboard System
- 👑 **Super Admin**: Multi-event management, admin user management
- 🔧 **Admin**: Event-specific operations, full CRUD on registrations
- 🎯 **Volunteer**: Check-in scanner, attendance tracking

### Additional Features
- 📊 Real-time statistics and analytics
- 📧 Email template management
- 🔍 Advanced search with multiple filters
- 📥 Export data in multiple formats
- 🔐 Role-based access control
- 🌐 Firebase Firestore backend
- 📱 Responsive design

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Firebase project with Firestore enabled
- Firebase service account credentials

### Installation

1. **Copy the event_manager folder to your project**
   ```bash
   cp -r event_manager /path/to/your/project/
   cd /path/to/your/project/event_manager
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Firebase**
   - Create a Firebase project at https://console.firebase.google.com
   - Enable Firestore Database
   - Generate a service account key (Settings → Service Accounts → Generate New Private Key)
   - Save the JSON file as `db/firebase-credentials.json`

5. **Configure the application**
   ```bash
   cp config.example.yaml config.yaml
   cp .env.example .env
   ```
   
   Edit `config.yaml` with your event details:
   - Organization name
   - Default event information
   - Branding settings
   - Feature toggles

6. **Run the application**
   ```bash
   python app.py
   ```
   
   The server will start at `http://localhost:5001`

## 📖 Configuration

### config.yaml
Main configuration file for application settings:

```yaml
app:
  name: "Event Manager"
  port: 5001
  secret_key: "your-secret-key"

branding:
  organization_name: "Your Organization"
  default_event_name: "Your Event 2026"
  support_email: "support@yourevent.com"

features:
  registration: true
  check_in: true
  email_templates: true
  id_card_generation: true
  volunteer_dashboard: true
```

### .env
Environment-specific variables (not committed to git):

```bash
FLASK_ENV=development
SECRET_KEY=your-super-secret-key
PORT=5001
FIREBASE_CREDENTIALS_PATH=db/firebase-credentials.json
```

## 🔑 Default Credentials

**Super Admin** (created on first run):
- Username: `admin` (configurable in `config.yaml`)
- Password: `changeme123` (⚠️ **CHANGE THIS IMMEDIATELY!**)

Change the default credentials in `config.yaml`:
```yaml
admin:
  default_super_admin:
    username: "yourusername"
    password: "securepassword"
    name: "Your Name"
    email: "your@email.com"
```

## 📱 Dashboard Access

After starting the server, access the dashboards:

- **Super Admin**: http://localhost:5001/super-admin
- **Admin**: http://localhost:5001/admin
- **Volunteer**: http://localhost:5001/volunteer
- **Registration Form**: http://localhost:5001/register
- **API Documentation**: http://localhost:5001/api

## 🏗️ Architecture

```
event_manager/
├── app.py                      # Main Flask application
├── config.yaml                 # Application configuration
├── requirements.txt            # Python dependencies
├── db/
│   ├── firebase_config.py      # Firebase initialization
│   ├── firebase_models.py      # Firestore data models
│   └── firebase-credentials.json  # (Your credentials - not in git)
├── logic/
│   ├── access_control.py       # Role-based access control
│   ├── clash_detector.py       # Schedule conflict detection
│   ├── filters.py              # Advanced filtering logic
│   ├── id_card_generator.py    # ID card generation
│   ├── planner.py              # Schedule planning
│   └── registration.py         # Registration workflows
├── routes/
│   ├── admin.py                # Admin API endpoints
│   ├── register.py             # Registration endpoints
│   ├── plan.py                 # Schedule planner endpoints
│   ├── hackathon.py            # Hackathon module
│   └── cleanup.py              # Cleanup utilities
├── static/
│   ├── admin-dashboard.html    # Admin UI
│   ├── admin-dashboard.js      # Admin logic
│   ├── super-admin-dashboard.html  # Super admin UI
│   ├── super-admin-dashboard.js    # Super admin logic
│   ├── volunteer-login.html    # Volunteer UI
│   ├── registration.html       # Registration form
│   └── generated_ids/          # Generated ID cards
└── templates/
    └── id_card/
        └── id_card_config.json # ID card template config
```

## 🔐 Security Best Practices

1. **Change default credentials immediately**
2. **Use strong SECRET_KEY in production**
3. **Enable HTTPS in production** (set `session.cookie_secure: true`)
4. **Restrict CORS origins** to your actual domains
5. **Use environment variables** for sensitive data
6. **Keep Firebase credentials secure** (never commit to git)
7. **Regularly update dependencies** (`pip install -U -r requirements.txt`)

## 🚢 Deployment

### Render.com

1. Create a new Web Service
2. Connect your repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Add environment variables:
   - `FIREBASE_CREDENTIALS`: (paste entire JSON)
   - `SECRET_KEY`: (generate strong key)
   - `PORT`: `10000` (Render default)

### Heroku

1. Create Heroku app
2. Add buildpack: `heroku/python`
3. Set config vars (same as Render)
4. Deploy: `git push heroku main`

### VPS/Dedicated Server

1. Install dependencies
2. Use gunicorn or uwsgi as WSGI server
3. Set up nginx as reverse proxy
4. Use systemd for process management
5. Configure SSL with Let's Encrypt

## 🎨 Customization

### Branding
Edit `config.yaml`:
```yaml
branding:
  organization_name: "Your Company"
  default_event_name: "Annual Conference 2026"
  support_email: "help@yourcompany.com"
  website_url: "https://yourcompany.com"
```

### ID Card Design
Edit `templates/id_card/id_card_config.json` to customize:
- Colors
- Fonts
- Logo placement
- Field positions

### Features
Enable/disable features in `config.yaml`:
```yaml
features:
  registration: true
  check_in: true
  email_templates: true
  id_card_generation: true
  volunteer_dashboard: true
  hackathon_module: false  # Disable if not needed
  schedule_planner: false  # Disable if not needed
```

## 🤝 Support

For questions or issues:
1. Check the documentation in this README
2. Review `FEATURES.md` for detailed feature documentation
3. Check logs for error messages
4. Ensure Firebase credentials are correctly configured

## 📄 License

This is a standalone event management system. Use it for your events!

## 🙏 Credits

Developed as a reusable system extracted from GDTA 2026 conference management platform.

---

**Note**: This system does NOT include chatbot functionality. Chatbot integration is event-specific and should be implemented separately if needed.
