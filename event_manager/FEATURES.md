# Event Manager - Features Documentation

Comprehensive guide to all features in the Event Manager system.

## 📊 Dashboard Overview

### Super Admin Dashboard
**Access Level**: Super Admin only  
**Purpose**: Multi-event management and system administration

**Features**:
- Create, edit, delete events
- View all events in grid/card layout
- Event details with live statistics
- Admin user management
- Assign admins to specific events
- Real-time registration counts per event
- System-wide analytics

**Default URL**: `/super-admin` or `/static/super-admin-dashboard.html`

### Admin Dashboard
**Access Level**: Admin (event-specific)  
**Purpose**: Day-to-day event management operations

**Features**:
- View/filter/search registrations for assigned events
- Approve or reject registrations
- Edit registration details
- Bulk operations (approve, reject, email)
- Generate ID cards
- Check-in management
- Email template management
- Export data (CSV, Excel, PDF)
- Real-time statistics
- Advanced filtering system

**Default URL**: `/admin` or `/static/admin-dashboard.html`

### Volunteer Dashboard
**Access Level**: Volunteer (event-specific)  
**Purpose**: Check-in operations at event venue

**Features**:
- QR code scanner for attendee check-in
- Manual check-in by search
- Real-time check-in statistics
- Attendee lookup
- Check-in history

**Default URL**: `/volunteer` or `/static/volunteer-login.html`

---

## 👥 User Management

### Role Types

1. **Super Admin**
   - Full system access
   - Manage all events
   - Create/edit/delete admins
   - Assign admins to events
   - System configuration

2. **Admin**
   - Event-specific access
   - Manage registrations for assigned events
   - Generate ID cards
   - Check-in operations
   - Email attendees
   - Export data

3. **Volunteer**
   - Read-only access
   - Check-in scanner only
   - View attendee info during check-in
   - No edit permissions

### Creating Users

**Super Admin** (automatic on first run):
- Configured in `config.yaml`
- Created automatically when app starts
- Change default credentials immediately!

**Admin Users** (via Super Admin Dashboard):
1. Login as Super Admin
2. Go to "Admin Users" tab
3. Click "Create New Admin"
4. Fill in details (username, password, name, email)
5. Assign to one or more events
6. Save

**Volunteer Users** (via Super Admin or Admin Dashboard):
1. Login as Super Admin or Admin
2. Go to user management
3. Create new volunteer account
4. Assign to specific events
5. Provide credentials to volunteer

---

## 🎟️ Registration System

### Registration Flow

1. **Public Registration Form** (`/register`)
   - Attendees fill out form
   - Required fields: name, email, institution, country
   - Optional fields: GDTA membership, affiliation, etc.
   - Real-time validation
   - reCAPTCHA support (configurable)

2. **Admin Review**
   - New registrations appear as "Pending"
   - Admin reviews details
   - Approve or reject with optional notes

3. **Email Notification** (optional)
   - Automatically send approval/rejection emails
   - Customizable email templates
   - Include event details and instructions

4. **ID Card Generation**
   - Generate individual or bulk ID cards
   - QR code with unique identifier
   - Custom design with event branding

### Registration Fields

**Standard Fields**:
- Name
- Email (unique identifier)
- Institution/Organization
- Country
- Phone (optional)
- GDTA Member status
- GDTA Affiliation
- Additional notes

**Custom Fields**:
- Add custom fields in registration form
- Store in Firebase
- Display in admin dashboard

### Registration Status

- **Pending**: Awaiting admin review
- **Approved**: Accepted registration
- **Rejected**: Declined registration

---

## 🔍 Advanced Filtering

### Available Filters

1. **Status Filter** (Multi-select)
   - Pending
   - Approved
   - Rejected

2. **Country Filter** (Multi-select)
   - All countries from database
   - Dropdown with autocomplete

3. **Date Range Filters**
   - Registration date (created_at)
   - Last updated date (updated_at)
   - Custom date range picker

4. **GDTA Member Filter**
   - Yes
   - No
   - Either

5. **Registration Source**
   - Form (manual registration)
   - Chatbot (if integrated)

6. **Check-in Status**
   - Checked in
   - Not checked in

7. **Search**
   - Name
   - Email
   - Institution
   - Full-text search across fields

### Using Filters

1. Open Admin Dashboard
2. Click "Advanced Filters" button
3. Select desired filters
4. Click "Apply Filters"
5. View filtered results
6. Export filtered results if needed

---

## ✅ Check-in System

### QR Code Check-in

1. **Generate ID Cards**
   - Each registration gets unique QR code
   - QR code contains unique identifier

2. **Scanner Setup**
   - Volunteers access `/volunteer`
   - Login with volunteer credentials
   - Camera permission required

3. **Check-in Process**
   - Volunteer scans attendee QR code
   - System verifies and marks checked-in
   - Timestamp recorded
   - Display attendee details
   - Success/error message shown

### Manual Check-in

1. Search by name or email
2. Select correct attendee
3. Click "Check In" button
4. Confirm check-in

### Check-in Statistics

Real-time dashboard showing:
- Total registrations
- Checked-in count
- Not checked-in count
- Check-in percentage
- Recent check-ins

---

## 🆔 ID Card Generation

### Features

- **Custom Design**: Template-based JSON configuration
- **QR Codes**: Unique QR code per attendee
- **Branding**: Event logo and colors
- **Bulk Generation**: Generate cards for all approved registrations
- **On-demand Regeneration**: Regenerate individual cards
- **Download Options**: Individual or bulk ZIP download

### Template Configuration

Edit `templates/id_card/id_card_config.json`:

```json
{
  "card": {
    "width": 1016,
    "height": 638,
    "background_color": "#FFFFFF"
  },
  "branding": {
    "event_logo": "path/to/logo.png",
    "event_name": "Your Event 2026",
    "tagline": "Conference Theme"
  },
  "fields": {
    "name": {"x": 100, "y": 200, "font_size": 48},
    "institution": {"x": 100, "y": 280, "font_size": 24},
    "qr_code": {"x": 750, "y": 150, "size": 250}
  },
  "colors": {
    "primary": "#1E40AF",
    "secondary": "#3B82F6",
    "text": "#1F2937"
  }
}
```

### Bulk Operations

1. Go to Admin Dashboard
2. Select registrations to process
3. Click "Bulk Actions" → "Generate ID Cards"
4. Wait for processing
5. Download ZIP file with all cards

---

## 📧 Email System

### Email Templates

**Create Templates**:
1. Admin Dashboard → Email Templates tab
2. Click "Create Template"
3. Enter template name
4. Compose email with placeholders
5. Available placeholders:
   - `{{name}}` - Attendee name
   - `{{email}}` - Attendee email
   - `{{event_name}}` - Event name
   - `{{event_date}}` - Event dates
   - Custom placeholders

**Send Bulk Emails**:
1. Filter registrations (e.g., all approved)
2. Select recipients
3. Click "Bulk Actions" → "Send Email"
4. Choose template
5. Preview and send

### Email Configuration

Configure SMTP in `.env`:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@yourevent.com
```

---

## 📊 Export & Reports

### Export Formats

1. **CSV**
   - Simple spreadsheet format
   - Compatible with Excel, Google Sheets
   - All registration fields

2. **Excel (.xlsx)**
   - Formatted workbook
   - Multiple sheets for different data
   - Styled headers and cells

3. **PDF**
   - Professional printable format
   - Event branding included
   - Paginated and formatted

### Export Options

- Export all registrations
- Export filtered results only
- Export by status (approved/pending/rejected)
- Export checked-in attendees only
- Export with QR codes

### Generating Reports

1. Apply desired filters
2. Click "Export" button
3. Select format (CSV/Excel/PDF)
4. Choose export options
5. Download generated file

---

## 🎯 Multi-Event Management

### Creating Events

1. Login as Super Admin
2. Go to "Events" tab
3. Click "Create New Event"
4. Fill in event details:
   - Event ID (unique identifier)
   - Event name
   - Year
   - Start date
   - End date
   - Location
   - Description
   - Active status

### Event IDs

**Important**: Event ID is used to link registrations  
- Format: lowercase-with-hyphens (e.g., `gdta-2026`)
- Must be unique across system
- Cannot be changed after creation
- Used in API calls and registration forms

### Assigning Admins to Events

1. Super Admin Dashboard → Admin Users
2. Select admin to edit
3. Check events to assign
4. Admin can only see assigned events
5. Admin cannot switch between unassigned events

### Event Statistics

Per-event dashboard showing:
- Total registrations
- Approved count
- Pending count
- Check-in statistics
- Assigned admins count

---

## 🔧 Advanced Features

### Schedule Planner

Plan and manage event schedules:
- Session management
- Track scheduling
- Conflict detection
- Attendee session preferences

### Hackathon Module

Special features for hackathons:
- Team registration
- Project submissions
- Judging workflow
- Winner selection

### Cleanup Utilities

Background tasks:
- Old session cleanup
- Temporary file removal
- Database optimization

---

## 🎨 Customization

### Branding

Update `config.yaml`:
```yaml
branding:
  organization_name: "Your Organization"
  default_event_name: "Your Event 2026"
  support_email: "support@yourevent.com"
  website_url: "https://yourevent.com"
  primary_color: "#1E40AF"
  secondary_color: "#3B82F6"
```

### Feature Toggles

Enable/disable features:
```yaml
features:
  registration: true
  check_in: true
  email_templates: true
  id_card_generation: true
  volunteer_dashboard: true
  hackathon_module: false
  schedule_planner: false
```

---

## 📱 API Endpoints

### Authentication

```
POST /api/admin/login
Body: {"username": "admin", "password": "password"}
```

### Events (Super Admin)

```
GET    /api/superadmin/events
POST   /api/superadmin/events
PUT    /api/superadmin/events/<event_id>
DELETE /api/superadmin/events/<event_id>
```

### Registrations (Admin)

```
GET    /api/admin/registrations?event_id=<id>
GET    /api/admin/registrations/<id>
PUT    /api/admin/registrations/<id>
DELETE /api/admin/registrations/<id>
POST   /api/admin/registrations/bulk/approve
POST   /api/admin/registrations/bulk/reject
POST   /api/admin/registrations/bulk/email
```

### Check-in (Admin/Volunteer)

```
POST   /api/admin/check-in/<registration_id>
GET    /api/admin/check-in/stats?event_id=<id>
POST   /api/admin/check-in/scan
```

### ID Cards (Admin)

```
GET    /api/admin/id-card/view/<unique_id>
POST   /api/admin/id-card/generate/<unique_id>
POST   /api/admin/id-card/bulk/generate
GET    /api/admin/id-card/download/bulk
```

---

## 🐛 Troubleshooting

### Common Issues

**ID Cards not displaying**:
- Check if generated_ids directory exists
- Verify file permissions
- On cloud platforms: Regenerate on-demand

**Check-in scanner not working**:
- Ensure HTTPS (required for camera access)
- Check browser camera permissions
- Verify QR codes are valid

**Email sending fails**:
- Verify SMTP credentials
- Check firewall/network settings
- Enable "Less secure apps" for Gmail

**Registration counts show 0**:
- Verify event_id matches between Event and Registrations
- Check Firebase indexes
- Review browser console for errors

---

## 💡 Best Practices

1. **Security**
   - Change default credentials immediately
   - Use strong passwords
   - Enable HTTPS in production
   - Restrict CORS origins

2. **Data Management**
   - Regular backups of Firebase
   - Export data periodically
   - Clean up old events

3. **Performance**
   - Use Firebase indexes for common queries
   - Limit bulk operations batch size
   - Optimize ID card generation

4. **User Experience**
   - Train volunteers before event
   - Test QR scanner ahead of time
   - Have backup manual check-in process
   - Provide clear instructions to attendees

---

For more information, see the main README.md file.
