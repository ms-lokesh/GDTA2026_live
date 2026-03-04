# GDTA 2026 - Admin & Registration System

A comprehensive multi-event management system for GDTA conferences with role-based access control, registration management, and ID card generation.

## 🚀 Features

### Super Admin Features
- **Event Management**: Create and manage multiple conference events
- **Admin Management**: Create admins and assign them to specific events
- **Dashboard**: Overview of all events, admins, and total registrations
- **Full System Control**: Manage the entire platform

### Regular Admin Features
- **Registration Management**: Review, approve, and manage registrations
- **ID Card Generation**: Generate QR code-based ID cards with unique IDs
- **Venue Management**: Create and manage conference venues
- **Volunteer Management**: Manage volunteers with venue assignments
- **Access Logs**: Track participant venue access via QR scanning
- **Email System**: Send emails to registrants (bulk or individual)
- **Data Export**: Export registration data to CSV

### Chatbot Features
- **AI-Powered Assistant**: Gemini-powered chatbot for conference queries
- **Registration Integration**: Users can register through chatbot
- **Session Information**: Query conference sessions and schedule
- **Smart Responses**: Context-aware conversations with memory

## 📁 Project Structure

```
admin_system/
├── app.py                          # Main Flask application
├── create_super_admin.py           # Script to create super admin users
├── migrate_to_multi_event.py       # Database migration script
├── requirements.txt                # Python dependencies
├── setup_firebase.sh               # Firebase setup script
├── .env.example                    # Environment variables template
├── .env                            # Environment variables (not in git)
│
├── data/                           # Static conference data
│   ├── conference.json             # Conference information
│   └── sessions.json               # Session details
│
├── db/                             # Database models and config
│   ├── firebase_config.py          # Firebase initialization
│   ├── firebase_models.py          # Firestore data models
│   ├── conversation_store.py       # Chatbot conversation storage
│   └── firebase-credentials.json   # Firebase credentials (not in git)
│
├── llm/                            # AI/LLM integration
│   ├── intent_resolver.py          # User intent detection
│   └── rag_engine.py               # RAG for conference data
│
├── logic/                          # Business logic
│   ├── registration.py             # Registration processing
│   ├── clash_detector.py           # Session clash detection
│   ├── filters.py                  # Session filtering
│   ├── planner.py                  # Schedule planning
│   └── id_card_generator.py        # ID card generation
│
├── routes/                         # API routes
│   ├── admin.py                    # Admin panel endpoints
│   ├── chat.py                     # Chatbot endpoints
│   ├── plan.py                     # Session planning endpoints
│   ├── register.py                 # Registration endpoints
│   └── cleanup.py                  # Database cleanup utilities
│
└── static/                         # Frontend files
    ├── admin-dashboard.html        # Admin panel UI
    ├── admin-dashboard.js          # Admin panel logic
    ├── super-admin-setup.html      # First-time super admin setup
    ├── registration.html           # Registration form
    ├── chatbot-widget.html         # Chatbot widget
    ├── index.html                  # Chatbot main page
    └── templates/                  # ID card templates
        └── id_card_config.json     # ID card configuration
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Python 3.8+
- Firebase account with Firestore enabled
- Google Gemini API key (for chatbot)
- Gmail account (for email functionality)

### 2. Install Dependencies

```bash
cd admin_system
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
```env
# Gemini API
GEMINI_API_KEY=your_gemini_api_key

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
EMAIL_FROM=your_email@gmail.com
EMAIL_FROM_NAME=GDTA 2026

# Flask Configuration
SECRET_KEY=your_secret_key_here
```

### 4. Setup Firebase

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Firestore Database
3. Download service account credentials
4. Save as `db/firebase-credentials.json`

Or run the setup script:
```bash
bash setup_firebase.sh
```

### 5. Initialize Database

Run the migration script to set up multi-event structure:
```bash
python3 migrate_to_multi_event.py
```

### 6. Create Super Admin

Create your first super admin account:
```bash
python3 create_super_admin.py
```

Or visit: `http://localhost:5000/static/super-admin-setup.html` after starting the app.

### 7. Run the Application

```bash
python3 app.py
```

The application will start on `http://localhost:5000`

## 🔐 Access URLs

- **Admin Dashboard**: `http://localhost:5000/static/admin-dashboard.html`
- **Super Admin Setup**: `http://localhost:5000/static/super-admin-setup.html` (one-time)
- **Registration Form**: `http://localhost:5000/static/registration.html`
- **Chatbot**: `http://localhost:5000/static/index.html`
- **Chatbot Widget**: Can be embedded in any page using `chatbot-widget.html`

## 👥 User Roles

### Super Admin
- Full system access
- Manage events and admins
- Dashboard shows: events overview, admin statistics
- Menu: Dashboard, Event Management, Admin Management

### Regular Admin
- Event-specific access
- Manage registrations, venues, volunteers
- Dashboard shows: registration statistics, country/role distribution
- Menu: Dashboard, Registrations, Venues, Volunteers, Access Logs, Email, Export

## 📊 Database Collections

- **events**: Conference events
- **admin_users**: Admin accounts with role-based access
- **registrations**: Participant registrations
- **venues**: Conference venues
- **volunteers**: Volunteer accounts with venue assignments
- **access_logs**: QR code scan logs
- **email_logs**: Email sending history

## 🔄 Multi-Event System

The system supports multiple events simultaneously:
- Each event has a unique ID
- Admins can be assigned to specific events
- Super admins see all events
- Data is automatically filtered by event
- Event selector for super admins to view specific event data

## 🎫 ID Card System

- Auto-generated 6-character unique IDs (alphanumeric)
- QR codes contain the unique ID
- Cards generated on registration approval
- Email attachments with downloadable PDF
- Regeneration requires admin approval
- Professional design with QR code, photo, and details

## 📧 Email System

- Send to all registrants or filtered groups
- Custom subject and message
- HTML email support
- Bulk sending capability
- Email logs for tracking

## 🔌 API Endpoints

### Admin Endpoints
- `POST /api/admin/login` - Admin login
- `GET /api/admin/registrations` - List registrations
- `PUT /api/admin/registrations/:id` - Update registration
- `POST /api/admin/id-card/generate/:id` - Generate ID card
- `GET /api/admin/stats` - Dashboard statistics

### Super Admin Endpoints
- `GET /api/superadmin/events` - List events
- `POST /api/superadmin/events` - Create event
- `PUT /api/superadmin/events/:id` - Update event
- `DELETE /api/superadmin/events/:id` - Delete event
- `GET /api/superadmin/admins` - List admins
- `POST /api/superadmin/admins` - Create admin
- `PUT /api/superadmin/admins/:username` - Update admin
- `DELETE /api/superadmin/admins/:username` - Delete admin

### Public Endpoints
- `POST /api/register` - Submit registration
- `POST /api/chat` - Chatbot interaction
- `GET /api/sessions` - Get session information

## 🛡️ Security Features

- Session-based authentication
- Password hashing (Werkzeug)
- Role-based access control
- Event-specific data isolation
- CORS protection
- Environment variable protection

## 🐛 Troubleshooting

### Firebase Connection Issues
- Verify `firebase-credentials.json` is in `db/` folder
- Check Firebase project permissions
- Ensure Firestore is enabled

### Email Not Sending
- Use Gmail app-specific password, not regular password
- Enable "Less secure app access" if needed
- Check SMTP settings in `.env`

### ID Cards Not Generating
- Check `static/templates/id_card_config.json` exists
- Verify unique_id field exists in registrations
- Check file permissions for `static/generated_ids/`

## 📝 License

This project is part of GDTA 2026 Conference System.

## 🤝 Support

For issues or questions, contact the GDTA technical team.
