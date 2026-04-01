"""
Admin Routes - API endpoints for coordinator dashboard
Handles authentication, registration management, and email sending
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import smtplib
import json
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
from firebase_admin import auth as firebase_auth

from db.firebase_models import (
    Registration, AdminUser, EmailLog, Venue, AccessLog, Volunteer, Event, EmailTemplate
)
from db.firebase_config import get_firestore_db
from logic.id_card_generator import IDCardGenerator
from logic.access_control import AccessController

# Load environment variables
load_dotenv()

admin_bp = Blueprint('admin', __name__)


# Email configuration
EMAIL_CONFIG = {
    'host': os.getenv('EMAIL_HOST', 'smtp.gmail.com'),
    'port': int(os.getenv('EMAIL_PORT', '587')),
    'use_tls': os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true',
    'username': os.getenv('EMAIL_USERNAME', ''),
    'password': os.getenv('EMAIL_PASSWORD', ''),
    'from_name': os.getenv('EMAIL_FROM_NAME', 'GDTA 2026 Team')
}

# Firebase Auth configuration
FIREBASE_WEB_API_KEY = os.getenv('FIREBASE_WEB_API_KEY', '').strip()
FIREBASE_AUTH_REQUIRED = os.getenv('FIREBASE_AUTH_REQUIRED', 'False').lower() == 'true'


def _firebase_sign_in_with_email_password(email, password):
    """Validate credentials against Firebase Authentication via Identity Toolkit REST API."""
    if not FIREBASE_WEB_API_KEY:
        return False, 'Firebase Auth not configured (missing FIREBASE_WEB_API_KEY).'

    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    payload = {
        'email': email,
        'password': password,
        'returnSecureToken': True
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return bool(response_data.get('idToken')), None
    except urllib.error.HTTPError as e:
        try:
            err_payload = json.loads(e.read().decode('utf-8'))
            firebase_msg = err_payload.get('error', {}).get('message', 'AUTH_ERROR')
        except Exception:
            firebase_msg = 'AUTH_ERROR'

        if firebase_msg in ['INVALID_LOGIN_CREDENTIALS', 'EMAIL_NOT_FOUND', 'INVALID_PASSWORD', 'USER_DISABLED']:
            return False, 'Invalid email or password.'
        return False, f'Firebase Auth error: {firebase_msg}'
    except Exception as e:
        return False, f'Firebase Auth request failed: {str(e)}'


def _sync_firebase_auth_user(uid, email, password=None, display_name=None, disabled=False):
    """Create or update Firebase Auth user for admin/volunteer identities."""
    if not FIREBASE_WEB_API_KEY:
        return True, None  # Firebase Auth sync disabled by configuration

    if not email:
        if FIREBASE_AUTH_REQUIRED:
            return False, 'Email is required when FIREBASE_AUTH_REQUIRED=True.'
        return True, None

    try:
        try:
            user = firebase_auth.get_user(uid)
            update_kwargs = {
                'uid': user.uid,
                'email': email,
                'disabled': bool(disabled)
            }
            if display_name:
                update_kwargs['display_name'] = display_name
            if password:
                update_kwargs['password'] = password
            firebase_auth.update_user(**update_kwargs)
        except firebase_auth.UserNotFoundError:
            create_kwargs = {
                'uid': uid,
                'email': email,
                'disabled': bool(disabled)
            }
            if display_name:
                create_kwargs['display_name'] = display_name
            if password:
                create_kwargs['password'] = password
            else:
                if FIREBASE_AUTH_REQUIRED:
                    return False, 'Password is required to create Firebase Auth user when auth is enabled.'
            firebase_auth.create_user(**create_kwargs)

        return True, None
    except Exception as e:
        return False, f'Failed to sync Firebase Auth user: {str(e)}'


def _delete_firebase_auth_user(uid):
    """Delete Firebase Auth user if present (best effort)."""
    if not FIREBASE_WEB_API_KEY:
        return True, None
    try:
        firebase_auth.delete_user(uid)
        return True, None
    except firebase_auth.UserNotFoundError:
        return True, None
    except Exception as e:
        return False, f'Failed to delete Firebase Auth user: {str(e)}'


def send_smtp_email(to_email, subject, body, attachment_path=None):
    """
    Send email using SMTP (Gmail)
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
        attachment_path: Optional path to file to attach
    
    Returns:
        (success, error_message)
    """
    if not EMAIL_CONFIG['username'] or not EMAIL_CONFIG['password'] or EMAIL_CONFIG['password'] == 'your_app_password_here':
        return False, "Email not configured. Please set EMAIL_USERNAME and EMAIL_PASSWORD in .env file"
    
    try:
        from email.mime.base import MIMEBase
        from email import encoders
        
        # Create message
        msg = MIMEMultipart('mixed')
        msg['From'] = f"{EMAIL_CONFIG['from_name']} <{EMAIL_CONFIG['username']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Create alternative part for text/html
        msg_alternative = MIMEMultipart('alternative')
        
        # Add HTML and plain text versions
        text_part = MIMEText(body, 'plain')
        html_body = body.replace('\n', '<br>')
        html_part = MIMEText(f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                    <h2 style="color: white; margin: 0;">GDTA 2026</h2>
                    <p style="color: #93c5fd; margin: 5px 0 0 0;">Global Digital Transformation & Analytics Conference</p>
                </div>
                <div style="background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px;">
                    {html_body}
                </div>
                <div style="text-align: center; padding: 20px; color: #64748b; font-size: 12px;">
                    <p>This email was sent by GDTA 2026 Organizing Committee</p>
                    <p>For questions, reply to this email or visit our website</p>
                </div>
            </div>
        </body>
        </html>
        """, 'html')
        
        msg_alternative.attach(text_part)
        msg_alternative.attach(html_part)
        msg.attach(msg_alternative)
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                
                filename = os.path.basename(attachment_path)
                part.add_header('Content-Disposition', f'attachment; filename= {filename}')
                msg.attach(part)
        
        # Connect to SMTP server
        server = smtplib.SMTP(EMAIL_CONFIG['host'], EMAIL_CONFIG['port'])
        server.ehlo()
        
        if EMAIL_CONFIG['use_tls']:
            server.starttls()
            server.ehlo()
        
        # Login and send
        server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        return True, None
        
    except smtplib.SMTPAuthenticationError:
        return False, "Email authentication failed. Check EMAIL_USERNAME and EMAIL_PASSWORD (use App Password for Gmail)"
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {str(e)}"
    except Exception as e:
        return False, f"Failed to send email: {str(e)}"


def format_fee_display(currency, total_fee):
    """Format total fee for display in emails and ID card metadata."""
    if currency and total_fee is not None:
        if currency == 'USD':
            return f"${total_fee}"
        return f"Rs.{total_fee}"
    return ""


def format_safari_route_display(safari_route):
    """Format safari route text for display in templates and ID cards."""
    if safari_route:
        return str(safari_route)
    return ""


# Authentication decorator
def require_auth(f):
    """Decorator to require authentication for admin routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_super_admin(f):
    """Decorator to require super admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        
        admin = get_current_admin()
        if not admin or admin.role != 'super_admin':
            return jsonify({'error': 'Super admin access required', 'code': 'FORBIDDEN'}), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_admin_or_volunteer_auth(f):
    """Decorator to require either admin or volunteer authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session and 'volunteer_user_id' not in session:
            return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_admin():
    """Get the currently logged in admin user"""
    if 'admin_user_id' not in session:
        return None
    
    admin = AdminUser.get_by_username(session['admin_user_id'])
    return admin if (admin and admin.is_active) else None


# ========== AUTHENTICATION ENDPOINTS ==========

@admin_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    """
    POST /api/admin/login
    
    Body:
    {
        "username": "admin",
        "password": "password"
    }
    
    Returns:
        {
            "success": true,
            "user": {...},
            "message": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400

        if FIREBASE_AUTH_REQUIRED and (not FIREBASE_WEB_API_KEY or FIREBASE_WEB_API_KEY == 'YOUR_FIREBASE_WEB_API_KEY_HERE'):
            return jsonify({'error': 'Server config error: FIREBASE_WEB_API_KEY is required when FIREBASE_AUTH_REQUIRED=True'}), 500
        
        username = data['username']
        password = data['password']
        
        admin = AdminUser.get_by_username(username)

        if not admin or not admin.is_active:
            return jsonify({'error': 'Invalid username or password'}), 401

        authenticated = False
        firebase_error = None

        # Preferred path: Firebase Auth (email/password)
        if admin.email and FIREBASE_WEB_API_KEY:
            authenticated, firebase_error = _firebase_sign_in_with_email_password(admin.email, password)
            if not authenticated and FIREBASE_AUTH_REQUIRED:
                return jsonify({'error': 'Invalid username or password'}), 401
        elif FIREBASE_AUTH_REQUIRED:
            return jsonify({'error': 'Admin account missing email required for Firebase Auth'}), 400

        # Backward-compatible fallback: existing local password hash
        if not authenticated:
            authenticated = admin.check_password(password)

        if not authenticated:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Update last login
        admin.last_login = datetime.utcnow()
        admin.save()
        
        # Create session
        session['admin_user_id'] = admin.username
        session['admin_username'] = admin.username
        session['admin_role'] = admin.role
        session.permanent = True
        
        user_dict = admin.to_dict()
        
        return jsonify({
            'success': True,
            'user': user_dict,
            'message': f'Welcome back, {admin.name}!'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500


@admin_bp.route('/api/admin/logout', methods=['POST'])
@require_auth
def admin_logout():
    """Logout current admin user"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200


@admin_bp.route('/api/admin/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current logged in admin user info"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': admin.to_dict()}), 200


# ========== REGISTRATION MANAGEMENT ENDPOINTS ==========

@admin_bp.route('/api/admin/registrations', methods=['GET'])
@require_auth
def get_all_registrations():
    """
    GET /api/admin/registrations?status=pending&country=India&search=john&limit=50&offset=0
    
    Get all registrations with optional filtering
    
    Query params:
        - status: comma-separated statuses (pending,approved,rejected)
        - country: comma-separated countries
        - search: search in name, email, institution
        - limit: number of results (default 100)
        - offset: pagination offset (default 0)
        - sort_by: field to sort by (default: created_at)
        - sort_order: asc/desc (default: desc)
        - date_from: filter created_at >= this date (ISO format)
        - date_to: filter created_at <= this date (ISO format)
        - updated_from: filter updated_at >= this date (ISO format)
        - updated_to: filter updated_at <= this date (ISO format)
        - is_gdta_member: yes/no filter
        - registration_source: form/chatbot filter
        - checked_in: true/false filter
    """
    try:
        from datetime import datetime
        
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Apply basic filters for Firebase query
        filters = {}
        
        # Event ID filter
        event_id = request.args.get('event_id')
        if event_id:
            filters['event_id'] = event_id
        
        # Get all registrations (we'll filter post-query for complex filters)
        registrations = Registration.get_all(limit=10000, filters=filters if filters else None)
        print(f"Retrieved {len(registrations)} registrations from Firebase")
        
        # Apply advanced filters post-query
        filtered_registrations = registrations
        
        # Status filter (multi-select)
        status_param = request.args.get('status')
        if status_param:
            statuses = [s.strip() for s in status_param.split(',')]
            filtered_registrations = [r for r in filtered_registrations if r.status in statuses]
        
        # Country filter (multi-select)
        country_param = request.args.get('country')
        if country_param:
            countries = [c.strip() for c in country_param.split(',')]
            filtered_registrations = [r for r in filtered_registrations if r.country in countries]
        
        # Date range filter for created_at
        date_from = request.args.get('date_from')
        if date_from:
            try:
                date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                filtered_registrations = [r for r in filtered_registrations if r.created_at >= date_from_dt]
            except ValueError:
                pass
        
        date_to = request.args.get('date_to')
        if date_to:
            try:
                date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                filtered_registrations = [r for r in filtered_registrations if r.created_at <= date_to_dt]
            except ValueError:
                pass
        
        # Date range filter for updated_at
        updated_from = request.args.get('updated_from')
        if updated_from:
            try:
                updated_from_dt = datetime.fromisoformat(updated_from.replace('Z', '+00:00'))
                filtered_registrations = [r for r in filtered_registrations if r.updated_at >= updated_from_dt]
            except ValueError:
                pass
        
        updated_to = request.args.get('updated_to')
        if updated_to:
            try:
                updated_to_dt = datetime.fromisoformat(updated_to.replace('Z', '+00:00'))
                filtered_registrations = [r for r in filtered_registrations if r.updated_at <= updated_to_dt]
            except ValueError:
                pass
        
        # GDTA member filter
        is_gdta_member = request.args.get('is_gdta_member')
        if is_gdta_member and is_gdta_member.lower() in ['yes', 'no']:
            target_value = 'yes' if is_gdta_member.lower() == 'yes' else 'no'
            filtered_registrations = [r for r in filtered_registrations if r.gdta_member == target_value]
        
        # Registration source filter
        registration_source = request.args.get('registration_source')
        if registration_source and registration_source in ['form', 'chatbot']:
            filtered_registrations = [r for r in filtered_registrations if r.registration_source == registration_source]
        
        # Check-in status filter
        checked_in = request.args.get('checked_in')
        if checked_in and checked_in.lower() in ['true', 'false']:
            target_checked_in = checked_in.lower() == 'true'
            filtered_registrations = [r for r in filtered_registrations if r.checked_in == target_checked_in]
        
        # Apply search filter
        search = request.args.get('search')
        if search:
            search_lower = search.lower()
            filtered_registrations = [
                r for r in filtered_registrations 
                if (search_lower in r.name.lower() or 
                    search_lower in r.email.lower() or 
                    search_lower in r.institution.lower())
            ]
        
        # Get total after filtering
        total_count = len(filtered_registrations)
        
        # Apply pagination
        paginated_registrations = filtered_registrations[offset:offset + limit]
        
        result = {
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'registrations': [r.to_dict() for r in paginated_registrations]
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        print(f"❌ Error in get_all_registrations: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch registrations', 'details': str(e), 'type': type(e).__name__}), 500


@admin_bp.route('/api/admin/registrations/<registration_id>', methods=['GET'])
@require_auth
def get_registration_details(registration_id):
    """Get details of a specific registration"""
    try:
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        result = registration.to_dict()
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch registration', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/<registration_id>', methods=['PUT'])
@require_auth
def update_registration(registration_id):
    """
    PUT /api/admin/registrations/<id>
    
    Update registration status or notes
    
    Body:
    {
        "status": "approved",
        "admin_notes": "Approved for conference"
    }
    """
    try:
        data = request.get_json()
        
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        old_status = registration.status
        
        # Update fields
        if 'status' in data:
            registration.status = data['status']
        
        if 'admin_notes' in data:
            registration.admin_notes = data['admin_notes']
        
        registration.updated_at = datetime.utcnow()
        registration.save()
        
        # Auto-generate ID card when status changes to "approved"
        if registration.status == 'approved' and old_status != 'approved' and not registration.id_card_generated:
            try:
                # Ensure unique_id exists
                if not registration.unique_id:
                    print(f"[AUTO-GEN ERROR] Registration {registration.id} missing unique_id!")
                    raise Exception("Missing unique_id - cannot generate ID card")
                
                generator = IDCardGenerator()
                output_path = generator.generate_id_card(
                    name=registration.name,
                    institution=registration.institution,
                    registration_id=registration.unique_id,  # Use unique_id
                    qr_data=registration.unique_id,
                    fee_text=format_fee_display(getattr(registration, 'fee_currency', None), getattr(registration, 'total_fee', None)),
                    safari_route_text=format_safari_route_display(getattr(registration, 'safari_route', None))
                )
                
                filename = os.path.basename(output_path)
                download_url = f"/static/generated_ids/{filename}"
                
                # Update registration with ID card info
                registration.id_card_generated = True
                registration.id_card_generated_at = datetime.utcnow()
                registration.id_card_url = download_url
                registration.id_card_regenerate_approved = False
                registration.save()
                
            except Exception as e:
                # Log error but don't fail the status update
                print(f"Failed to auto-generate ID card for {registration.id}: {str(e)}")
        
        result = registration.to_dict()
        
        return jsonify({
            'success': True,
            'message': 'Registration updated successfully',
            'registration': result,
            'id_card_auto_generated': registration.id_card_generated and old_status != 'approved'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update registration', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/<registration_id>', methods=['DELETE'])
@require_auth
def delete_registration(registration_id):
    """Delete a registration (use with caution)"""
    try:
        admin = get_current_admin()
        if admin.role != 'admin':
            return jsonify({'error': 'Only admins can delete registrations'}), 403
        
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        Registration.delete(registration_id)
        
        return jsonify({
            'success': True,
            'message': 'Registration deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete registration', 'details': str(e)}), 500


# ========== BULK OPERATIONS ==========

@admin_bp.route('/api/admin/registrations/bulk/approve', methods=['POST'])
@require_auth
def bulk_approve_registrations():
    """
    Bulk approve multiple registrations
    POST /api/admin/registrations/bulk/approve
    
    Body:
    {
        "registration_ids": ["id1", "id2", "id3"]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'registration_ids' not in data:
            return jsonify({'error': 'registration_ids required'}), 400
        
        registration_ids = data['registration_ids']
        
        if not isinstance(registration_ids, list) or len(registration_ids) == 0:
            return jsonify({'error': 'registration_ids must be a non-empty array'}), 400
        
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for reg_id in registration_ids:
            try:
                registration = Registration.get_by_id(reg_id)
                
                if not registration:
                    failed_ids.append({'id': reg_id, 'reason': 'Not found'})
                    failed_count += 1
                    continue
                
                registration.status = 'approved'
                registration.save()
                success_count += 1
                
            except Exception as e:
                failed_ids.append({'id': reg_id, 'reason': str(e)})
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Approved {success_count} registrations',
            'approved': success_count,
            'failed': failed_count,
            'failed_details': failed_ids if failed_ids else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to bulk approve', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/bulk/reject', methods=['POST'])
@require_auth
def bulk_reject_registrations():
    """
    Bulk reject multiple registrations
    POST /api/admin/registrations/bulk/reject
    
    Body:
    {
        "registration_ids": ["id1", "id2", "id3"]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'registration_ids' not in data:
            return jsonify({'error': 'registration_ids required'}), 400
        
        registration_ids = data['registration_ids']
        
        if not isinstance(registration_ids, list) or len(registration_ids) == 0:
            return jsonify({'error': 'registration_ids must be a non-empty array'}), 400
        
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for reg_id in registration_ids:
            try:
                registration = Registration.get_by_id(reg_id)
                
                if not registration:
                    failed_ids.append({'id': reg_id, 'reason': 'Not found'})
                    failed_count += 1
                    continue
                
                registration.status = 'rejected'
                registration.save()
                success_count += 1
                
            except Exception as e:
                failed_ids.append({'id': reg_id, 'reason': str(e)})
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Rejected {success_count} registrations',
            'rejected': success_count,
            'failed': failed_count,
            'failed_details': failed_ids if failed_ids else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to bulk reject', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/bulk/status', methods=['POST'])
@require_auth
def bulk_update_status():
    """
    Bulk update status for multiple registrations
    POST /api/admin/registrations/bulk/status
    
    Body:
    {
        "registration_ids": ["id1", "id2", "id3"],
        "status": "approved" | "rejected" | "pending"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'registration_ids' not in data or 'status' not in data:
            return jsonify({'error': 'registration_ids and status required'}), 400
        
        registration_ids = data['registration_ids']
        new_status = data['status']
        
        if not isinstance(registration_ids, list) or len(registration_ids) == 0:
            return jsonify({'error': 'registration_ids must be a non-empty array'}), 400
        
        if new_status not in ['approved', 'rejected', 'pending']:
            return jsonify({'error': 'Invalid status. Must be: approved, rejected, or pending'}), 400
        
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for reg_id in registration_ids:
            try:
                registration = Registration.get_by_id(reg_id)
                
                if not registration:
                    failed_ids.append({'id': reg_id, 'reason': 'Not found'})
                    failed_count += 1
                    continue
                
                registration.status = new_status
                registration.save()
                success_count += 1
                
            except Exception as e:
                failed_ids.append({'id': reg_id, 'reason': str(e)})
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Updated {success_count} registrations to {new_status}',
            'updated': success_count,
            'failed': failed_count,
            'failed_details': failed_ids if failed_ids else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to bulk update status', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/bulk/email', methods=['POST'])
@require_auth
def bulk_send_email():
    """
    Send email to selected registrations
    POST /api/admin/registrations/bulk/email
    
    Body - Option 1 (Direct):
    {
        "registration_ids": ["id1", "id2", "id3"],
        "subject": "Email subject",
        "message": "Email body"
    }
    
    Body - Option 2 (Template):
    {
        "registration_ids": ["id1", "id2", "id3"],
        "template_id": "template_id_here"
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        if not data or 'registration_ids' not in data:
            return jsonify({'error': 'registration_ids required'}), 400
        
        registration_ids = data['registration_ids']
        
        if not isinstance(registration_ids, list) or len(registration_ids) == 0:
            return jsonify({'error': 'registration_ids must be a non-empty array'}), 400
        
        # Check if using template or direct content
        use_template = 'template_id' in data
        template = None
        subject = None
        message = None
        
        if use_template:
            template_id = data['template_id']
            template = EmailTemplate.get_by_id(template_id)
            if not template:
                return jsonify({'error': 'Template not found'}), 404
        else:
            # Direct content
            if 'subject' not in data or 'message' not in data:
                return jsonify({'error': 'subject and message required when not using template'}), 400
            subject = data['subject']
            message = data['message']
        
        # Get registrations by IDs
        recipients = []
        for reg_id in registration_ids:
            reg = Registration.get_by_id(reg_id)
            if reg:
                recipients.append(reg)
        
        if not recipients:
            return jsonify({'error': 'No valid registrations found'}), 404
        
        # Send emails
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        for recipient in recipients:
            try:
                # Prepare email content
                if use_template:
                    # Render template for this recipient
                    context = {
                        'name': recipient.name,
                        'email': recipient.email,
                        'institution': recipient.institution,
                        'role': recipient.role,
                        'country': recipient.country,
                        'unique_id': recipient.unique_id,
                        'registration_category': getattr(recipient, 'registration_category', None),
                        'safari_route': getattr(recipient, 'safari_route', None),
                        'fee_currency': getattr(recipient, 'fee_currency', None),
                        'total_fee': getattr(recipient, 'total_fee', None),
                        'fee_display': format_fee_display(getattr(recipient, 'fee_currency', None), getattr(recipient, 'total_fee', None)),
                        'event_name': 'GDTA 2026',
                        'event_year': '2026',
                        'event_location': 'Sri Nakhon Pathom, Thailand'
                    }
                    email_subject, email_body = template.render(context)
                else:
                    # Use direct content
                    email_subject = subject
                    email_body = message
                
                success, error = send_smtp_email(
                    to_email=recipient.email,
                    subject=email_subject,
                    body=email_body
                )
                
                if success:
                    # Log successful email
                    email_log = EmailLog(
                        registration_id=recipient.id,
                        recipient_email=recipient.email,
                        subject=email_subject,
                        body=email_body,
                        sent_by=admin.username,
                        status='sent'
                    )
                    email_log.save()
                    sent_count += 1
                else:
                    failed_emails.append({
                        'email': recipient.email,
                        'name': recipient.name,
                        'error': error
                    })
                    failed_count += 1
                    
                    # Log failed email
                    email_log = EmailLog(
                        registration_id=recipient.id,
                        recipient_email=recipient.email,
                        subject=email_subject,
                        body=email_body,
                        sent_by=admin.username,
                        status='failed',
                        error=error
                    )
                    email_log.save()
                    
            except Exception as e:
                failed_emails.append({
                    'email': recipient.email,
                    'name': recipient.name,
                    'error': str(e)
                })
                failed_count += 1
        
        response = {
            'success': True,
            'sent': sent_count,
            'failed': failed_count,
            'total': len(recipients)
        }
        
        if failed_emails:
            response['failed_details'] = failed_emails
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to send bulk emails', 'details': str(e)}), 500


# ========== CHECK-IN ENDPOINTS ==========

@admin_bp.route('/api/admin/check-in', methods=['POST'])
@require_auth
def check_in_registration():
    """
    Check in a registration by unique_id (from QR code scan)
    POST /api/admin/check-in
    
    Body:
    {
        "unique_id": "ABC123"  // or "registration_id": "xxxxxx"
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Support both unique_id (QR code) and registration_id
        unique_id = data.get('unique_id')
        registration_id = data.get('registration_id')
        
        if not unique_id and not registration_id:
            return jsonify({'error': 'unique_id or registration_id required'}), 400
        
        # Get registration
        if unique_id:
            registration = Registration.get_by_unique_id(unique_id)
            if not registration:
                return jsonify({'error': 'Registration not found with this QR code'}), 404
        else:
            registration = Registration.get_by_id(registration_id)
            if not registration:
                return jsonify({'error': 'Registration not found'}), 404
        
        # Check if already checked in
        if registration.checked_in:
            return jsonify({
                'success': True,
                'already_checked_in': True,
                'message': f'{registration.name} was already checked in',
                'checked_in_at': registration.checked_in_at,
                'checked_in_by': registration.checked_in_by,
                'registration': registration.to_dict()
            }), 200
        
        # Check if registration is approved
        if registration.status != 'approved':
            return jsonify({
                'error': 'Registration must be approved before check-in',
                'status': registration.status,
                'registration': registration.to_dict()
            }), 400
        
        # Mark as checked in
        registration.checked_in = True
        registration.checked_in_at = datetime.utcnow()
        registration.checked_in_by = admin.username
        registration.save()
        
        return jsonify({
            'success': True,
            'message': f'{registration.name} checked in successfully',
            'registration': registration.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Check-in failed', 'details': str(e)}), 500


@admin_bp.route('/api/admin/check-in/stats', methods=['GET'])
@require_auth
def get_checkin_stats():
    """
    Get check-in statistics
    GET /api/admin/check-in/stats?event_id=gdta-2026
    """
    try:
        event_id = request.args.get('event_id')
        
        # Get all registrations for the event
        filters = {'status': 'approved'}
        if event_id:
            filters['event_id'] = event_id
        
        registrations = Registration.get_all(filters=filters)
        
        total_approved = len(registrations)
        checked_in_count = sum(1 for r in registrations if r.checked_in)
        not_checked_in_count = total_approved - checked_in_count
        
        # Recent check-ins (last 10)
        checked_in_regs = [r for r in registrations if r.checked_in]
        checked_in_regs.sort(key=lambda x: x.checked_in_at if x.checked_in_at else datetime.min, reverse=True)
        recent_checkins = [
            {
                'name': r.name,
                'email': r.email,
                'unique_id': r.unique_id,
                'checked_in_at': r.checked_in_at,
                'checked_in_by': r.checked_in_by
            }
            for r in checked_in_regs[:10]
        ]
        
        return jsonify({
            'success': True,
            'stats': {
                'total_approved': total_approved,
                'checked_in': checked_in_count,
                'not_checked_in': not_checked_in_count,
                'percentage': round((checked_in_count / total_approved * 100) if total_approved > 0 else 0, 1)
            },
            'recent_checkins': recent_checkins
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get check-in stats', 'details': str(e)}), 500


# ========== EMAIL TEMPLATE ENDPOINTS ==========

@admin_bp.route('/api/admin/email-templates', methods=['GET'])
@require_auth
def get_email_templates():
    """
    Get all email templates
    GET /api/admin/email-templates?event_id=xxx&category=xxx
    """
    try:
        filters = {}
        
        # Optional filters
        event_id = request.args.get('event_id')
        category = request.args.get('category')
        is_active = request.args.get('is_active')
        
        if event_id:
            filters['event_id'] = event_id
        if category:
            filters['category'] = category
        if is_active is not None:
            filters['is_active'] = is_active.lower() == 'true'
        
        templates = EmailTemplate.get_all(filters=filters)
        
        return jsonify({
            'success': True,
            'templates': [t.to_dict() for t in templates]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get templates', 'details': str(e)}), 500


@admin_bp.route('/api/admin/email-templates/<template_id>', methods=['GET'])
@require_auth
def get_email_template(template_id):
    """
    Get email template by ID
    GET /api/admin/email-templates/:id
    """
    try:
        template = EmailTemplate.get_by_id(template_id)
        
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        return jsonify({
            'success': True,
            'template': template.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get template', 'details': str(e)}), 500


@admin_bp.route('/api/admin/email-templates', methods=['POST'])
@require_auth
def create_email_template():
    """
    Create new email template
    POST /api/admin/email-templates
    
    Body:
    {
        "name": "Welcome Email",
        "subject": "Welcome to {{event_name}}!",
        "body": "Dear {{name}},\n\nWelcome...",
        "category": "welcome",
        "variables": ["name", "email", "event_name", "unique_id"],
        "event_id": "gdta-2026" (optional)
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        if not data or 'name' not in data or 'subject' not in data or 'body' not in data:
            return jsonify({'error': 'name, subject, and body are required'}), 400
        
        # Create template
        template = EmailTemplate(
            name=data['name'],
            subject=data['subject'],
            body=data['body'],
            category=data.get('category', 'custom'),
            variables=data.get('variables', []),
            event_id=data.get('event_id'),
            is_active=data.get('is_active', True),
            created_by=admin.username
        )
        
        template_id = template.save()
        
        return jsonify({
            'success': True,
            'message': 'Template created successfully',
            'template_id': template_id,
            'template': template.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create template', 'details': str(e)}), 500


@admin_bp.route('/api/admin/email-templates/<template_id>', methods=['PUT'])
@require_auth
def update_email_template(template_id):
    """
    Update email template
    PUT /api/admin/email-templates/:id
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        template = EmailTemplate.get_by_id(template_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        # Update fields
        if 'name' in data:
            template.name = data['name']
        if 'subject' in data:
            template.subject = data['subject']
        if 'body' in data:
            template.body = data['body']
        if 'category' in data:
            template.category = data['category']
        if 'variables' in data:
            template.variables = data['variables']
        if 'is_active' in data:
            template.is_active = data['is_active']
        if 'event_id' in data:
            template.event_id = data['event_id']
        
        template.save()
        
        return jsonify({
            'success': True,
            'message': 'Template updated successfully',
            'template': template.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update template', 'details': str(e)}), 500


@admin_bp.route('/api/admin/email-templates/<template_id>', methods=['DELETE'])
@require_auth
def delete_email_template(template_id):
    """
    Delete email template
    DELETE /api/admin/email-templates/:id
    """
    try:
        template = EmailTemplate.get_by_id(template_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        EmailTemplate.delete(template_id)
        
        return jsonify({
            'success': True,
            'message': 'Template deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete template', 'details': str(e)}), 500


@admin_bp.route('/api/admin/email-templates/<template_id>/preview', methods=['POST'])
@require_auth
def preview_email_template(template_id):
    """
    Preview email template with sample data
    POST /api/admin/email-templates/:id/preview
    
    Body:
    {
        "registration_id": "xxx" (optional, will use registration data)
        or
        "context": {"name": "John", "email": "john@example.com", ...}
    }
    """
    try:
        data = request.get_json()
        
        template = EmailTemplate.get_by_id(template_id)
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        # Build context for rendering
        context = {}
        
        if data and 'registration_id' in data:
            # Use real registration data
            registration = Registration.get_by_id(data['registration_id'])
            if registration:
                context = {
                    'name': registration.name,
                    'email': registration.email,
                    'institution': registration.institution,
                    'role': registration.role,
                    'country': registration.country,
                    'unique_id': registration.unique_id,
                    'registration_category': getattr(registration, 'registration_category', None),
                    'safari_route': getattr(registration, 'safari_route', None),
                    'fee_currency': getattr(registration, 'fee_currency', None),
                    'total_fee': getattr(registration, 'total_fee', None),
                    'fee_display': format_fee_display(getattr(registration, 'fee_currency', None), getattr(registration, 'total_fee', None)),
                    'event_name': 'GDTA 2026',
                    'event_year': '2026',
                    'event_location': 'Sri Nakhon Pathom, Thailand'
                }
        elif data and 'context' in data:
            # Use provided context
            context = data['context']
        else:
            # Use default sample data
            context = {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'institution': 'Sample University',
                'role': 'Educator',
                'country': 'Thailand',
                'unique_id': 'ABC123',
                'registration_category': 'Student',
                'safari_route': 'Route 02 - Urban Pulse & Living Heritage',
                'fee_currency': 'INR',
                'total_fee': 500,
                'fee_display': 'Rs.500',
                'event_name': 'GDTA 2026',
                'event_year': '2026',
                'event_location': 'Sri Nakhon Pathom, Thailand'
            }
        
        # Render template
        rendered_subject, rendered_body = template.render(context)
        
        return jsonify({
            'success': True,
            'preview': {
                'subject': rendered_subject,
                'body': rendered_body,
                'context': context
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to preview template', 'details': str(e)}), 500


# ========== STATISTICS ENDPOINTS ==========

@admin_bp.route('/api/admin/stats', methods=['GET'])
@require_auth
def get_statistics():
    """
    GET /api/admin/stats
    
    Get dashboard statistics
    """
    try:
        # Get event_id filter
        event_id = request.args.get('event_id')
        filters = {}
        
        if event_id:
            filters['event_id'] = event_id
        
        # Get all registrations for aggregation
        all_regs = Registration.get_all(limit=1000, filters=filters if filters else None)
        
        # Total registrations
        total = len(all_regs)
        
        # By status
        pending = sum(1 for r in all_regs if r.status == 'pending')
        approved = sum(1 for r in all_regs if r.status == 'approved')
        rejected = sum(1 for r in all_regs if r.status == 'rejected')
        
        # By country (top 10)
        country_counts = {}
        for r in all_regs:
            country_counts[r.country] = country_counts.get(r.country, 0) + 1
        countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # By role
        role_counts = {}
        for r in all_regs:
            role_counts[r.role] = role_counts.get(r.role, 0) + 1
        roles = list(role_counts.items())
        
        # Recent registrations (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = sum(1 for r in all_regs if isinstance(r.created_at, datetime) and r.created_at >= seven_days_ago)
        
        # Today's registrations
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today = sum(1 for r in all_regs if isinstance(r.created_at, datetime) and r.created_at >= today_start)
        
        return jsonify({
            'total': total,
            'by_status': {
                'pending': pending,
                'approved': approved,
                'rejected': rejected
            },
            'by_country': [{'country': c[0], 'count': c[1]} for c in countries],
            'by_role': [{'role': r[0], 'count': r[1]} for r in roles],
            'recent_7_days': recent,
            'today': today
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ Error in get_statistics: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch statistics', 'details': str(e), 'type': type(e).__name__}), 500


# ========== EMAIL ENDPOINTS ==========

@admin_bp.route('/api/admin/email/send', methods=['POST'])
@require_auth
def send_email_to_registrant():
    """
    POST /api/admin/email/send
    
    Send email to one or more registrants
    
    Body:
    {
        "registration_ids": [1, 2, 3] or "all",
        "subject": "Welcome to GDTA 2026",
        "message": "Email body...",
        "filter": {
            "country": "India",
            "status": "approved"
        }
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        if not data or 'subject' not in data or 'message' not in data:
            return jsonify({'error': 'Subject and message required'}), 400
        
        subject = data['subject']
        message = data['message']
        
        # Determine recipients
        recipients = []
        
        if data.get('registration_ids') == 'all' or data.get('filter'):
            # Bulk email with optional filter
            filters = {}
            if data.get('filter'):
                if data['filter'].get('country'):
                    filters['country'] = data['filter']['country']
                if data['filter'].get('status'):
                    filters['status'] = data['filter']['status']
            
            recipients = Registration.get_all(limit=1000, filters=filters if filters else None)
        
        elif data.get('registration_ids'):
            # Specific registrants
            reg_ids = data['registration_ids']
            recipients = [Registration.get_by_id(rid) for rid in reg_ids if Registration.get_by_id(rid)]
        
        else:
            return jsonify({'error': 'No recipients specified'}), 400
        
        # Send emails with real SMTP
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        # Check if ID cards should be attached
        attach_id_card = data.get('attach_id_card', False)
        
        for recipient in recipients:
            try:
                # Generate ID card if requested
                attachment_path = None
                if attach_id_card:
                    try:
                        from logic.id_card_generator import IDCardGenerator
                        generator = IDCardGenerator()
                        
                        # Ensure recipient has unique_id
                        if not hasattr(recipient, 'unique_id') or not recipient.unique_id:
                            print(f"[ID CARD ERROR] Recipient {recipient.name} missing unique_id!")
                            raise Exception("Missing unique_id - run migration script first")
                        
                        # Generate ID card with unique_id in QR code
                        id_card_path = generator.generate_id_card(
                            name=recipient.name,
                            institution=recipient.institution,
                            registration_id=recipient.unique_id,  # Use unique_id for registration_id too
                            qr_data=recipient.unique_id,
                            fee_text=format_fee_display(getattr(recipient, 'fee_currency', None), getattr(recipient, 'total_fee', None)),
                            safari_route_text=format_safari_route_display(getattr(recipient, 'safari_route', None))
                        )
                        
                        if id_card_path and os.path.exists(id_card_path):
                            attachment_path = id_card_path
                            print(f"[ID CARD] Generated for {recipient.name}: {id_card_path}")
                        else:
                            print(f"[ID CARD WARNING] Failed to generate for {recipient.name}")
                    except Exception as e:
                        print(f"[ID CARD ERROR] Failed to generate for {recipient.name}: {str(e)}")
                
                # Send actual email via SMTP
                success, error = send_smtp_email(
                    to_email=recipient.email,
                    subject=subject,
                    body=message,
                    attachment_path=attachment_path
                )
                
                if success:
                    # Log successful email
                    email_log = EmailLog(
                        registration_id=recipient.id,
                        recipient_email=recipient.email,
                        subject=subject,
                        body=message,
                        sent_by=admin.username,
                        status='sent'
                    )
                    email_log.save()
                    sent_count += 1
                    print(f"[EMAIL SENT] To: {recipient.email} | Subject: {subject}")
                else:
                    # Log failed email
                    email_log = EmailLog(
                        registration_id=recipient.id,
                        recipient_email=recipient.email,
                        subject=subject,
                        body=message,
                        sent_by=admin.username,
                        status=f'failed: {error}'
                    )
                    email_log.save()
                    failed_count += 1
                    failed_emails.append(f"{recipient.email}: {error}")
                    print(f"[EMAIL ERROR] Failed to send to {recipient.email}: {error}")
                
            except Exception as e:
                failed_count += 1
                failed_emails.append(f"{recipient.email}: {str(e)}")
                print(f"[EMAIL ERROR] Exception sending to {recipient.email}: {str(e)}")
        
        response = {
            'success': True,
            'message': f'Email sending completed',
            'sent': sent_count,
            'failed': failed_count,
            'total': sent_count + failed_count
        }
        
        if failed_emails:
            response['failed_details'] = failed_emails
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to send emails', 'details': str(e)}), 500


@admin_bp.route('/api/admin/export/registrations', methods=['GET'])
@require_auth
def export_registrations():
    """
    GET /api/admin/export/registrations?format=csv&event_id=gdta-2026
    
    Export registrations to CSV, Excel, or PDF
    
    Query params:
        - format: csv, excel, pdf (default: csv)
        - event_id: filter by event
    """
    try:
        from flask import Response
        from io import BytesIO
        
        # Get parameters
        export_format = request.args.get('format', 'csv').lower()
        event_id = request.args.get('event_id')
        
        # Get data
        filters = {}
        if event_id:
            filters['event_id'] = event_id
        
        registrations = Registration.get_all(limit=1000, filters=filters if filters else None)
        
        if export_format == 'excel':
            return _export_registrations_excel(registrations, event_id)
        elif export_format == 'pdf':
            return _export_registrations_pdf(registrations, event_id)
        else:  # csv
            return _export_registrations_csv(registrations, event_id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to export', 'details': str(e)}), 500


def _export_registrations_csv(registrations, event_id=None):
    """Export registrations to CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Unique ID', 'Name', 'Email', 'Institution', 'Role', 
        'GDTA Member', 'GDTA Affiliation', 'Country', 'State',
        'Registration Source', 'Status', 'Created At'
    ])
    
    # Data
    for reg in registrations:
        created_at = reg.created_at.isoformat() if isinstance(reg.created_at, datetime) else str(reg.created_at)
        writer.writerow([
            reg.id, reg.unique_id or '', reg.name, reg.email, reg.institution, reg.role,
            reg.gdta_member, reg.gdta_affiliation or '', reg.country, reg.state or '',
            reg.registration_source, reg.status, created_at
        ])
    
    filename = f'registrations_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_registrations_excel(registrations, event_id=None):
    """Export registrations to Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    from flask import Response
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Registrations"
    
    # Header styling
    header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
    header_font = Font(color="F2B705", bold=True, size=12)
    
    # Headers
    headers = [
        'ID', 'Unique ID', 'Name', 'Email', 'Institution', 'Role',
        'GDTA Member', 'GDTA Affiliation', 'Country', 'State',
        'Registration Source', 'Status', 'Created At'
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Data
    for row_num, reg in enumerate(registrations, 2):
        created_at = reg.created_at.isoformat() if isinstance(reg.created_at, datetime) else str(reg.created_at)
        row_data = [
            reg.id, reg.unique_id or '', reg.name, reg.email, reg.institution, reg.role,
            reg.gdta_member, reg.gdta_affiliation or '', reg.country, reg.state or '',
            reg.registration_source, reg.status, created_at
        ]
        
        for col_num, value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num).value = value
    
    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min((max_length + 2), 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save to BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f'registrations_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_registrations_pdf(registrations, event_id=None):
    """Export registrations to PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from io import BytesIO
    from flask import Response
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch)
    
    # Container for elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#000000'),
        spaceAfter=30,
        alignment=1  # Center
    )
    elements.append(Paragraph("GDTA 2026 - Registration Report", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary
    summary_style = styles['Normal']
    elements.append(Paragraph(f"<b>Total Registrations:</b> {len(registrations)}", summary_style))
    elements.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", summary_style))
    if event_id:
        elements.append(Paragraph(f"<b>Event:</b> {event_id}", summary_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Table data
    table_data = [['Name', 'Email', 'Institution', 'Role', 'Country', 'Status']]
    
    for reg in registrations:
        table_data.append([
            reg.name[:30],
            reg.email[:35],
            reg.institution[:30],
            reg.role,
            reg.country,
            reg.status
        ])
    
    # Create table
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#F2B705')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
    ]))
    
    elements.append(table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f'registrations_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.pdf'
    return Response(
        buffer.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


@admin_bp.route('/api/admin/export/venues', methods=['GET'])
@require_auth
def export_venues():
    """
    GET /api/admin/export/venues?format=csv&event_id=gdta-2026
    
    Export venues to CSV or Excel
    """
    try:
        from flask import Response
        
        # Get parameters
        export_format = request.args.get('format', 'csv').lower()
        event_id = request.args.get('event_id')
        
        # Get data
        venues = Venue.get_all(event_id=event_id)
        
        if export_format == 'excel':
            return _export_venues_excel(venues, event_id)
        else:  # csv
            return _export_venues_csv(venues, event_id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to export venues', 'details': str(e)}), 500


def _export_venues_csv(venues, event_id=None):
    """Export venues to CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'ID', 'Name', 'Type', 'Description', 'Location', 'Capacity',
        'Access Limit', 'Requires Approval', 'Active', 'Created At'
    ])
    
    # Data
    for venue in venues:
        created_at = venue.created_at.isoformat() if isinstance(venue.created_at, datetime) else str(venue.created_at)
        writer.writerow([
            venue.id, venue.name, venue.venue_type, venue.description or '',
            venue.location or '', venue.capacity or '',
            venue.access_limit, venue.requires_approval, venue.is_active, created_at
        ])
    
    filename = f'venues_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_venues_excel(venues, event_id=None):
    """Export venues to Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    from flask import Response
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Venues"
    
    # Header styling
    header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
    header_font = Font(color="F2B705", bold=True, size=12)
    
    # Headers
    headers = [
        'ID', 'Name', 'Type', 'Description', 'Location', 'Capacity',
        'Access Limit', 'Requires Approval', 'Active', 'Created At'
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Data
    for row_num, venue in enumerate(venues, 2):
        created_at = venue.created_at.isoformat() if isinstance(venue.created_at, datetime) else str(venue.created_at)
        row_data = [
            venue.id, venue.name, venue.venue_type, venue.description or '',
            venue.location or '', venue.capacity or '',
            venue.access_limit, 'Yes' if venue.requires_approval else 'No',
            'Yes' if venue.is_active else 'No', created_at
        ]
        
        for col_num, value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num).value = value
    
    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min((max_length + 2), 50)
        ws.column_dimensions[column].width = adjusted_width
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f'venues_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


@admin_bp.route('/api/admin/export/volunteers', methods=['GET'])
@require_auth
def export_volunteers():
    """
    GET /api/admin/export/volunteers?format=csv&event_id=gdta-2026
    
    Export volunteers to CSV or Excel
    """
    try:
        from flask import Response
        
        # Get parameters
        export_format = request.args.get('format', 'csv').lower()
        event_id = request.args.get('event_id')
        
        # Get data
        volunteers = Volunteer.get_all(event_id=event_id)
        
        if export_format == 'excel':
            return _export_volunteers_excel(volunteers, event_id)
        else:  # csv
            return _export_volunteers_csv(volunteers, event_id)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to export volunteers', 'details': str(e)}), 500


def _export_volunteers_csv(volunteers, event_id=None):
    """Export volunteers to CSV"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Username', 'Name', 'Email', 'Phone', 'Assigned Venues',
        'Active', 'Created At'
    ])
    
    # Data
    for vol in volunteers:
        created_at = vol.created_at.isoformat() if isinstance(vol.created_at, datetime) else str(vol.created_at)
        assigned_venues = ', '.join(vol.assigned_venues) if vol.assigned_venues else ''
        writer.writerow([
            vol.username, vol.name, vol.email or '', vol.phone or '',
            assigned_venues, vol.is_active, created_at
        ])
    
    filename = f'volunteers_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_volunteers_excel(volunteers, event_id=None):
    """Export volunteers to Excel"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from io import BytesIO
    from flask import Response
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Volunteers"
    
    # Header styling
    header_fill = PatternFill(start_color="000000", end_color="000000", fill_type="solid")
    header_font = Font(color="F2B705", bold=True, size=12)
    
    # Headers
    headers = [
        'Username', 'Name', 'Email', 'Phone', 'Assigned Venues',
        'Active', 'Created At'
    ]
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Data
    for row_num, vol in enumerate(volunteers, 2):
        created_at = vol.created_at.isoformat() if isinstance(vol.created_at, datetime) else str(vol.created_at)
        assigned_venues = ', '.join(vol.assigned_venues) if vol.assigned_venues else ''
        row_data = [
            vol.username, vol.name, vol.email or '', vol.phone or '',
            assigned_venues, 'Yes' if vol.is_active else 'No', created_at
        ]
        
        for col_num, value in enumerate(row_data, 1):
            ws.cell(row=row_num, column=col_num).value = value
    
    # Adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = min((max_length + 2), 50)
        ws.column_dimensions[column].width = adjusted_width
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f'volunteers_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


# ========== ID CARDS & BADGES EXPORT ==========

@admin_bp.route('/api/admin/export/id-cards-bulk', methods=['GET'])
@require_auth
def export_bulk_id_cards():
    """
    Generate and export QR codes with names as a ZIP file
    Lightweight alternative to full ID cards - just QR code + name
    
    GET /api/admin/export/id-cards-bulk?event_id=xxx
    """
    try:
        import qrcode
        import zipfile
        from io import BytesIO
        from flask import Response
        from PIL import Image, ImageDraw, ImageFont
        
        event_id = request.args.get('event_id', session.get('event_id'))
        
        if not event_id:
            return jsonify({'error': 'Event ID required'}), 400
        
        # Get all registrations for the event
        registrations = Registration.get_all(limit=1000, filters={'event_id': event_id})
        
        if not registrations:
            return jsonify({'error': 'No registrations found'}), 404
        
        # Create ZIP file in memory
        zip_buffer = BytesIO()
        generated_count = 0
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for reg in registrations:
                try:
                    # Generate simple QR code with name
                    # Create QR code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10,
                        border=2,
                    )
                    qr.add_data(reg.email)
                    qr.make(fit=True)
                    qr_img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Create canvas with QR code and name
                    canvas_width = 400
                    canvas_height = 500
                    canvas = Image.new('RGB', (canvas_width, canvas_height), 'white')
                    draw = ImageDraw.Draw(canvas)
                    
                    # Resize QR code to fit
                    qr_size = 350
                    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
                    
                    # Paste QR code centered
                    qr_x = (canvas_width - qr_size) // 2
                    qr_y = 20
                    canvas.paste(qr_img, (qr_x, qr_y))
                    
                    # Add name below QR code
                    try:
                        # Try to use system font
                        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
                        font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
                    except:
                        font = ImageFont.load_default()
                        font_bold = ImageFont.load_default()
                    
                    # Draw name (bold)
                    name_text = reg.name.upper()
                    bbox = draw.textbbox((0, 0), name_text, font=font_bold)
                    text_width = bbox[2] - bbox[0]
                    text_x = (canvas_width - text_width) // 2
                    draw.text((text_x, 390), name_text, fill='black', font=font_bold)
                    
                    # Draw email (smaller)
                    email_text = reg.email
                    bbox = draw.textbbox((0, 0), email_text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_x = (canvas_width - text_width) // 2
                    draw.text((text_x, 430), email_text, fill='gray', font=font)
                    
                    # Save to bytes
                    img_buffer = BytesIO()
                    canvas.save(img_buffer, 'PNG', optimize=True)
                    img_buffer.seek(0)
                    
                    # Add to ZIP with clean filename
                    safe_name = reg.name.replace(' ', '_').replace('/', '_')
                    zip_filename = f"QR_{safe_name}_{reg.email.split('@')[0]}.png"
                    
                    zip_file.writestr(zip_filename, img_buffer.getvalue())
                    generated_count += 1
                    
                except Exception as e:
                    print(f"Error generating QR code for {reg.name}: {e}")
                    continue
        
        zip_buffer.seek(0)
        
        filename = f'qr_codes_bulk_{event_id}_{datetime.now().strftime("%Y%m%d")}.zip'
        
        return Response(
            zip_buffer.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment;filename={filename}',
                'X-Generated-Count': str(generated_count)
            }
        )
        
    except Exception as e:
        print(f"Bulk QR code export error: {e}")
        return jsonify({'error': 'Failed to generate bulk QR codes', 'details': str(e)}), 500


@admin_bp.route('/api/admin/export/badge-list', methods=['GET'])
@require_auth
def export_badge_list():
    """
    Export badge printing list - simple name list for badge printing
    
    GET /api/admin/export/badge-list?event_id=xxx&format=csv
    """
    try:
        event_id = request.args.get('event_id', session.get('event_id'))
        export_format = request.args.get('format', 'csv').lower()
        
        if not event_id:
            return jsonify({'error': 'Event ID required'}), 400
        
        registrations = Registration.get_all(limit=1000, filters={'event_id': event_id})
        
        if not registrations:
            return jsonify({'error': 'No registrations found'}), 404
        
        if export_format == 'csv':
            return _export_badge_list_csv(registrations, event_id)
        elif export_format == 'excel':
            return _export_badge_list_excel(registrations, event_id)
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
            
    except Exception as e:
        print(f"Badge list export error: {e}")
        return jsonify({'error': 'Failed to export badge list', 'details': str(e)}), 500


def _export_badge_list_csv(registrations, event_id=None):
    """Generate CSV badge printing list"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(['#', 'Full Name', 'Institution', 'Role', 'Country'])
    
    # Data rows
    for idx, reg in enumerate(registrations, 1):
        writer.writerow([
            idx,
            reg.name,
            reg.institution,
            reg.role or 'Participant',
            reg.country
        ])
    
    output.seek(0)
    filename = f'badge_printing_list_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_badge_list_excel(registrations, event_id=None):
    """Generate Excel badge printing list with formatting"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    
    wb = Workbook()
    ws = wb.active
    ws.title = 'Badge Printing List'
    
    # Header row with styling
    headers = ['#', 'Full Name', 'Institution', 'Role', 'Country']
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=12)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Data rows
    for idx, reg in enumerate(registrations, 1):
        row_num = idx + 1
        row_data = [
            idx,
            reg.name,
            reg.institution,
            reg.role or 'Participant',
            reg.country
        ]
        
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = value
            
            # Alternate row coloring
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 8
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 20
    ws.column_dimensions['E'].width = 15
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f'badge_printing_list_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


@admin_bp.route('/api/admin/export/qr-codes', methods=['GET'])
@require_auth
def export_qr_code_list():
    """
    Export QR code list - all unique IDs for verification scanning
    
    GET /api/admin/export/qr-codes?event_id=xxx&format=csv
    """
    try:
        event_id = request.args.get('event_id', session.get('event_id'))
        export_format = request.args.get('format', 'csv').lower()
        
        if not event_id:
            return jsonify({'error': 'Event ID required'}), 400
        
        registrations = Registration.get_all(limit=1000, filters={'event_id': event_id})
        
        if not registrations:
            return jsonify({'error': 'No registrations found'}), 404
        
        if export_format == 'csv':
            return _export_qr_codes_csv(registrations, event_id)
        elif export_format == 'excel':
            return _export_qr_codes_excel(registrations, event_id)
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
            
    except Exception as e:
        print(f"QR code list export error: {e}")
        return jsonify({'error': 'Failed to export QR code list', 'details': str(e)}), 500


def _export_qr_codes_csv(registrations, event_id=None):
    """Generate CSV QR code list"""
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(['Unique ID', 'Name', 'Email', 'Institution', 'Status'])
    
    # Data rows
    for reg in registrations:
        unique_id = reg.email  # Using email as unique identifier
        writer.writerow([
            unique_id,
            reg.name,
            reg.email,
            reg.institution,
            reg.status or 'pending'
        ])
    
    output.seek(0)
    filename = f'qr_code_list_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.csv'
    
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


def _export_qr_codes_excel(registrations, event_id=None):
    """Generate Excel QR code list with formatting"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    
    wb = Workbook()
    ws = wb.active
    ws.title = 'QR Code List'
    
    # Header row with styling
    headers = ['Unique ID', 'Name', 'Email', 'Institution', 'Status']
    header_fill = PatternFill(start_color='28A745', end_color='28A745', fill_type='solid')
    header_font = Font(bold=True, color='FFFFFF', size=12)
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Data rows
    for idx, reg in enumerate(registrations, 1):
        row_num = idx + 1
        unique_id = reg.email  # Using email as unique identifier
        
        row_data = [
            unique_id,
            reg.name,
            reg.email,
            reg.institution,
            reg.status or 'pending'
        ]
        
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = value
            
            # Alternate row coloring
            if idx % 2 == 0:
                cell.fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 35
    ws.column_dimensions['B'].width = 30
    ws.column_dimensions['C'].width = 35
    ws.column_dimensions['D'].width = 35
    ws.column_dimensions['E'].width = 15
    
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f'qr_code_list_{event_id or "all"}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


# ========== ID CARD GENERATION ==========

@admin_bp.route('/api/admin/id-card/generate/<registration_id>', methods=['POST'])
@require_auth
def generate_id_card(registration_id):
    """
    Generate ID card for a specific registration
    
    POST /api/admin/id-card/generate/<registration_id>
    """
    try:
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        # Check if ID card already generated and regenerate not approved
        if registration.id_card_generated and not registration.id_card_regenerate_approved:
            return jsonify({
                'error': 'ID card already generated. Regeneration requires approval.',
                'code': 'ALREADY_GENERATED'
            }), 403
        
        # Validate unique_id exists
        if not registration.unique_id:
            return jsonify({
                'error': 'Cannot generate ID card: unique_id missing. Please contact admin.',
                'code': 'MISSING_UNIQUE_ID'
            }), 400
        
        # Generate ID card using unique_id in QR code
        generator = IDCardGenerator()
        output_path = generator.generate_id_card(
            name=registration.name,
            institution=registration.institution,
            registration_id=registration.unique_id,  # Use unique_id
            qr_data=registration.unique_id,  # QR contains unique_id
            fee_text=format_fee_display(getattr(registration, 'fee_currency', None), getattr(registration, 'total_fee', None)),
            safari_route_text=format_safari_route_display(getattr(registration, 'safari_route', None))
        )
        
        # Return the relative path for downloading
        filename = os.path.basename(output_path)
        download_url = f"/static/generated_ids/{filename}"
        
        # Mark ID card as generated and reset regenerate approval
        registration.id_card_generated = True
        registration.id_card_generated_at = datetime.utcnow()
        registration.id_card_url = download_url
        registration.id_card_regenerate_approved = False
        registration.save()
        
        return jsonify({
            'success': True,
            'message': 'ID card generated successfully',
            'download_url': download_url,
            'filename': filename,
            'unique_id': registration.unique_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to generate ID card', 'details': str(e)}), 500


@admin_bp.route('/api/admin/id-card/view/<unique_id>', methods=['GET'])
def view_id_card(unique_id):
    """
    View/Download ID card by unique_id
    Regenerates on-the-fly if file is missing (handles ephemeral storage)
    
    GET /api/admin/id-card/view/<unique_id>
    
    This endpoint does not require authentication to allow easy public access
    via QR codes or email links.
    """
    try:
        from flask import send_file
        import os
        
        # Find registration by unique_id
        registrations = Registration.get_all(limit=1000)  # TODO: Add query by unique_id
        registration = None
        for reg in registrations:
            if reg.unique_id == unique_id:
                registration = reg
                break
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        if not registration.id_card_generated:
            return jsonify({
                'error': 'ID card not generated yet',
                'message': 'Please contact admin to generate your ID card'
            }), 404
        
        # Check if file exists
        base_dir = os.path.dirname(os.path.dirname(__file__))
        safe_id = unique_id.replace('@', '_at_').replace('.', '_')
        filename = f"id_card_{safe_id}.png"
        file_path = os.path.join(base_dir, 'static', 'generated_ids', filename)
        
        # Regenerate if missing (handles ephemeral storage on Render)
        if not os.path.exists(file_path):
            print(f"⚠ ID card file missing for {unique_id}, regenerating...")
            generator = IDCardGenerator()
            output_path = generator.generate_id_card(
                name=registration.name,
                institution=registration.institution,
                registration_id=unique_id,
                qr_data=unique_id,
                fee_text=format_fee_display(getattr(registration, 'fee_currency', None), getattr(registration, 'total_fee', None)),
                safari_route_text=format_safari_route_display(getattr(registration, 'safari_route', None))
            )
            file_path = output_path
            print(f"✓ Regenerated ID card at {file_path}")
        
        # Serve the file
        return send_file(
            file_path,
            mimetype='image/png',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        print(f"❌ Error serving ID card: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to retrieve ID card', 'details': str(e)}), 500


@admin_bp.route('/api/admin/id-card/batch', methods=['POST'])
@require_auth
def batch_generate_id_cards():
    """
    Generate ID cards for multiple registrations
    
    POST /api/admin/id-card/batch
    Body: {
        "registration_ids": ["id1", "id2"] or "all",
        "filter": {"status": "approved", "country": "India"}
    }
    """
    try:
        data = request.get_json()
        
        # Determine which registrations to generate for
        registrations = []
        
        if data.get('registration_ids') == 'all' or data.get('filter'):
            # Bulk generation with optional filter
            filters = {}
            if data.get('filter'):
                if data['filter'].get('country'):
                    filters['country'] = data['filter']['country']
                if data['filter'].get('status'):
                    filters['status'] = data['filter']['status']
            
            registrations = Registration.get_all(limit=1000, filters=filters if filters else None)
        
        elif data.get('registration_ids'):
            # Specific registrations
            reg_ids = data['registration_ids']
            registrations = [Registration.get_by_id(rid) for rid in reg_ids if Registration.get_by_id(rid)]
        
        else:
            return jsonify({'error': 'No registrations specified'}), 400
        
        # Generate ID cards
        generator = IDCardGenerator()
        results = []
        success_count = 0
        failed_count = 0
        
        for reg in registrations:
            try:
                # Skip if already generated and regenerate not approved
                if reg.id_card_generated and not reg.id_card_regenerate_approved:
                    results.append({
                        'registration_id': reg.id,
                        'name': reg.name,
                        'success': False,
                        'error': 'ID card already generated, regeneration pending approval',
                        'unique_id': reg.unique_id
                    })
                    failed_count += 1
                    continue
                
                # Validate unique_id
                if not reg.unique_id:
                    results.append({
                        'registration_id': reg.id,
                        'name': reg.name,
                        'success': False,
                        'error': 'Missing unique_id',
                        'unique_id': None
                    })
                    failed_count += 1
                    continue
                
                output_path = generator.generate_id_card(
                    name=reg.name,
                    institution=reg.institution,
                    registration_id=reg.unique_id,  # Use unique_id
                    qr_data=reg.unique_id,  # Use unique_id in QR code
                    fee_text=format_fee_display(getattr(reg, 'fee_currency', None), getattr(reg, 'total_fee', None)),
                    safari_route_text=format_safari_route_display(getattr(reg, 'safari_route', None))
                )
                
                filename = os.path.basename(output_path)
                download_url = f"/static/generated_ids/{filename}"
                
                # Mark as generated
                reg.id_card_generated = True
                reg.id_card_generated_at = datetime.utcnow()
                reg.id_card_url = download_url
                reg.id_card_regenerate_approved = False
                reg.save()
                
                results.append({
                    'registration_id': reg.id,
                    'name': reg.name,
                    'unique_id': reg.unique_id,
                    'success': True,
                    'download_url': download_url
                })
                success_count += 1
                
            except Exception as e:
                results.append({
                    'registration_id': reg.id,
                    'name': reg.name,
                    'success': False,
                    'error': str(e)
                })
                failed_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Generated {success_count} ID cards',
            'total': len(registrations),
            'success_count': success_count,
            'failed_count': failed_count,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to generate ID cards', 'details': str(e)}), 500


@admin_bp.route('/api/admin/id-card/approve-regenerate/<registration_id>', methods=['POST'])
@require_auth
def approve_id_card_regeneration(registration_id):
    """
    Approve regeneration of ID card for a registration
    
    POST /api/admin/id-card/approve-regenerate/<registration_id>
    Body: {
        "reason": "Lost card" (optional)
    }
    """
    try:
        admin = get_current_admin()
        if admin.role != 'admin':
            return jsonify({'error': 'Only admins can approve regeneration'}), 403
        
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        # Approve regeneration
        registration.id_card_regenerate_approved = True
        registration.admin_notes = registration.admin_notes or ''
        
        data = request.get_json() or {}
        reason = data.get('reason', 'Regeneration approved')
        registration.admin_notes += f"\n[{datetime.utcnow().isoformat()}] ID Card Regeneration Approved: {reason}"
        
        registration.save()
        
        return jsonify({
            'success': True,
            'message': 'ID card regeneration approved. You can now generate the card again.',
            'regenerate_approved': True
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to approve regeneration', 'details': str(e)}), 500


@admin_bp.route('/api/admin/id-card/status/<registration_id>', methods=['GET'])
@require_auth
def get_id_card_status(registration_id):
    """
    Get ID card generation status for a registration
    
    GET /api/admin/id-card/status/<registration_id>
    """
    try:
        registration = Registration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({'error': 'Registration not found'}), 404
        
        return jsonify({
            'success': True,
            'unique_id': registration.unique_id,
            'id_card_generated': registration.id_card_generated,
            'id_card_generated_at': registration.id_card_generated_at.isoformat() if registration.id_card_generated_at else None,
            'id_card_url': registration.id_card_url,
            'regenerate_approved': registration.id_card_regenerate_approved,
            'can_generate': not registration.id_card_generated or registration.id_card_regenerate_approved
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch ID card status', 'details': str(e)}), 500


# ========== VENUE MANAGEMENT ENDPOINTS ==========# ========== VENUE MANAGEMENT ENDPOINTS ==========

@admin_bp.route('/api/admin/venues', methods=['GET'])
@require_admin_or_volunteer_auth
def get_all_venues():
    """
    GET /api/admin/venues?is_active=true
    
    Get all venues with optional filter
    """
    try:
        event_id = request.args.get('event_id')
        is_active = request.args.get('is_active')
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
        venues = Venue.get_all(is_active=is_active, event_id=event_id)
        
        return jsonify({
            'success': True,
            'venues': [venue.to_dict() for venue in venues],
            'count': len(venues)
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ Error in get_all_venues: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch venues', 'details': str(e), 'type': type(e).__name__}), 500


@admin_bp.route('/api/admin/venues/<venue_id>', methods=['GET'])
@require_auth
def get_venue_by_id(venue_id):
    """Get venue by ID"""
    try:
        venue = Venue.get_by_id(venue_id)
        
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        return jsonify({
            'success': True,
            'venue': venue.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch venue', 'details': str(e)}), 500


@admin_bp.route('/api/admin/venues', methods=['POST'])
@require_auth
def create_venue():
    """
    POST /api/admin/venues
    
    Body:
    {
        "name": "Main Conference Hall",
        "venue_type": "entry",
        "description": "Main venue entry",
        "capacity": 500,
        "location": "Building A, Floor 1",
        "requires_approval": false
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Venue name is required'}), 400
        
        if not data.get('venue_type'):
            return jsonify({'error': 'Venue type is required'}), 400
        
        # Validate venue type
        valid_types = ['entry', 'food', 'session', 'lounge', 'other']
        if data['venue_type'] not in valid_types:
            return jsonify({'error': f'Invalid venue type. Must be one of: {", ".join(valid_types)}'}), 400
        
        # Validate access_limit if provided
        access_limit = data.get('access_limit', 'unlimited')
        valid_limits = ['unlimited', 'once']
        if access_limit not in valid_limits and not access_limit.isdigit():
            return jsonify({'error': f'Invalid access limit. Must be "unlimited", "once", or a numeric value'}), 400
        
        # Create venue
        venue = Venue(
            name=data['name'],
            venue_type=data['venue_type'],
            description=data.get('description', ''),
            capacity=data.get('capacity'),
            location=data.get('location', ''),
            requires_approval=data.get('requires_approval', False),
            is_active=data.get('is_active', True),
            access_limit=access_limit,
            created_by=admin.username if admin else None
        )
        
        venue_id = venue.save()
        
        return jsonify({
            'success': True,
            'message': 'Venue created successfully',
            'venue': venue.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create venue', 'details': str(e)}), 500


@admin_bp.route('/api/admin/venues/<venue_id>', methods=['PUT'])
@require_auth
def update_venue(venue_id):
    """Update venue"""
    try:
        data = request.get_json()
        venue = Venue.get_by_id(venue_id)
        
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        # Update fields
        if 'name' in data:
            venue.name = data['name']
        if 'venue_type' in data:
            valid_types = ['entry', 'food', 'session', 'lounge', 'other']
            if data['venue_type'] not in valid_types:
                return jsonify({'error': f'Invalid venue type. Must be one of: {", ".join(valid_types)}'}), 400
            venue.venue_type = data['venue_type']
        if 'description' in data:
            venue.description = data['description']
        if 'capacity' in data:
            venue.capacity = data['capacity']
        if 'location' in data:
            venue.location = data['location']
        if 'requires_approval' in data:
            venue.requires_approval = data['requires_approval']
        if 'is_active' in data:
            venue.is_active = data['is_active']
        if 'access_limit' in data:
            access_limit = data['access_limit']
            valid_limits = ['unlimited', 'once']
            if access_limit not in valid_limits and not access_limit.isdigit():
                return jsonify({'error': f'Invalid access limit. Must be "unlimited", "once", or a numeric value'}), 400
            venue.access_limit = access_limit
        
        venue.save()
        
        return jsonify({
            'success': True,
            'message': 'Venue updated successfully',
            'venue': venue.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update venue', 'details': str(e)}), 500


@admin_bp.route('/api/admin/venues/<venue_id>', methods=['DELETE'])
@require_auth
def delete_venue(venue_id):
    """Delete venue"""
    try:
        venue = Venue.get_by_id(venue_id)
        
        if not venue:
            return jsonify({'error': 'Venue not found'}), 404
        
        Venue.delete(venue_id)
        
        return jsonify({
            'success': True,
            'message': 'Venue deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete venue', 'details': str(e)}), 500


# ========== ACCESS LOG ENDPOINTS ==========

@admin_bp.route('/api/admin/access-logs', methods=['GET'])
@require_auth
def get_access_logs():
    """
    GET /api/admin/access-logs?venue_id=xxx&limit=100
    
    Get access logs with optional filters
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        filters = {}
        if request.args.get('event_id'):
            filters['event_id'] = request.args.get('event_id')
        if request.args.get('venue_id'):
            filters['venue_id'] = request.args.get('venue_id')
        if request.args.get('action_type'):
            filters['action_type'] = request.args.get('action_type')
        
        logs = AccessLog.get_all(limit=limit, filters=filters if filters else None)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'count': len(logs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch access logs', 'details': str(e)}), 500


@admin_bp.route('/api/admin/access-logs/venue/<venue_id>', methods=['GET'])
@require_auth
def get_venue_access_logs(venue_id):
    """Get access logs for a specific venue"""
    try:
        limit = int(request.args.get('limit', 100))
        logs = AccessLog.get_by_venue(venue_id, limit)
        
        return jsonify({
            'success': True,
            'logs': [log.to_dict() for log in logs],
            'count': len(logs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch venue logs', 'details': str(e)}), 500


@admin_bp.route('/api/admin/access-logs/participant/<registration_email>', methods=['GET'])
@require_auth
def get_participant_access_logs(registration_email):
    """Get access logs for a specific participant"""
    try:
        limit = int(request.args.get('limit', 50))
        logs = AccessController.get_participant_access_history(registration_email, limit)
        
        return jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch participant logs', 'details': str(e)}), 500


@admin_bp.route('/api/admin/venues/<venue_id>/stats', methods=['GET'])
@require_auth
def get_venue_stats(venue_id):
    """Get access statistics for a venue"""
    try:
        stats = AccessController.get_venue_access_stats(venue_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch venue stats', 'details': str(e)}), 500


# ========== QR CODE VALIDATION ENDPOINT ==========

@admin_bp.route('/api/validate-qr', methods=['POST'])
def validate_qr_code():
    """
    POST /api/validate-qr
    
    Validate QR code for venue access (public endpoint for volunteers)
    
    Body:
    {
        "qr_code": "participant@email.com",
        "venue_id": "venue123",
        "scanned_by": "volunteer_name"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('qr_code'):
            return jsonify({'error': 'QR code is required'}), 400
        if not data.get('venue_id'):
            return jsonify({'error': 'Venue ID is required'}), 400
        if not data.get('scanned_by'):
            return jsonify({'error': 'Scanner identification is required'}), 400
        
        # Validate access
        result = AccessController.validate_qr_access(
            qr_code=data['qr_code'],
            venue_id=data['venue_id'],
            scanned_by=data['scanned_by']
        )
        
        # Return appropriate status code
        status_code = 200 if result['success'] else 403
        
        return jsonify(result), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': str(e)
        }), 500


@admin_bp.route('/api/validate-qr/check-duplicate', methods=['POST'])
def check_duplicate_entry():
    """Check if participant recently entered this venue"""
    try:
        data = request.get_json()
        
        is_duplicate = AccessController.check_duplicate_entry(
            registration_email=data.get('qr_code'),
            venue_id=data.get('venue_id'),
            minutes=int(data.get('minutes', 5))
        )
        
        return jsonify({
            'success': True,
            'is_duplicate': is_duplicate
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to check duplicate', 'details': str(e)}), 500


# ========== VOLUNTEER AUTHENTICATION ENDPOINTS ==========

@admin_bp.route('/api/volunteer/login', methods=['POST'])
def volunteer_login():
    """
    POST /api/volunteer/login
    
    Body:
    {
        "username": "volunteer1",
        "password": "password"
    }
    
    Returns:
        {
            "success": true,
            "volunteer": {...},
            "message": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'username' not in data or 'password' not in data:
            return jsonify({'error': 'Username and password required'}), 400

        if FIREBASE_AUTH_REQUIRED and (not FIREBASE_WEB_API_KEY or FIREBASE_WEB_API_KEY == 'YOUR_FIREBASE_WEB_API_KEY_HERE'):
            return jsonify({'error': 'Server config error: FIREBASE_WEB_API_KEY is required when FIREBASE_AUTH_REQUIRED=True'}), 500
        
        username = data['username']
        password = data['password']
        
        volunteer = Volunteer.get_by_username(username)

        if not volunteer or not volunteer.is_active:
            return jsonify({'error': 'Invalid username or password'}), 401

        authenticated = False

        # Preferred path: Firebase Auth (email/password)
        if volunteer.email and FIREBASE_WEB_API_KEY:
            authenticated, _ = _firebase_sign_in_with_email_password(volunteer.email, password)
            if not authenticated and FIREBASE_AUTH_REQUIRED:
                return jsonify({'error': 'Invalid username or password'}), 401
        elif FIREBASE_AUTH_REQUIRED:
            return jsonify({'error': 'Volunteer account missing email required for Firebase Auth'}), 400

        # Backward-compatible fallback: existing local password hash
        if not authenticated:
            authenticated = volunteer.check_password(password)

        if not authenticated:
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Update last login
        volunteer.last_login = datetime.utcnow()
        volunteer.save()
        
        # Create session
        session['volunteer_user_id'] = volunteer.username
        session['volunteer_name'] = volunteer.name
        session.permanent = True
        
        volunteer_dict = volunteer.to_dict()
        # Don't send password hash to client
        volunteer_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'volunteer': volunteer_dict,
            'message': f'Welcome, {volunteer.name}!'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'details': str(e)}), 500


@admin_bp.route('/api/volunteer/logout', methods=['POST'])
def volunteer_logout():
    """Logout current volunteer user"""
    if 'volunteer_user_id' in session:
        session.pop('volunteer_user_id', None)
        session.pop('volunteer_name', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200


@admin_bp.route('/api/volunteer/me', methods=['GET'])
def get_current_volunteer():
    """Get current logged in volunteer user info"""
    if 'volunteer_user_id' not in session:
        return jsonify({'error': 'Not authenticated', 'code': 'AUTH_REQUIRED'}), 401
    
    volunteer = Volunteer.get_by_username(session['volunteer_user_id'])
    
    if not volunteer or not volunteer.is_active:
        session.pop('volunteer_user_id', None)
        session.pop('volunteer_name', None)
        return jsonify({'error': 'Volunteer not found or inactive'}), 404
    
    volunteer_dict = volunteer.to_dict()
    volunteer_dict.pop('password_hash', None)
    
    return jsonify({'volunteer': volunteer_dict}), 200


# ========== VOLUNTEER MANAGEMENT ENDPOINTS (Admin only) ==========

@admin_bp.route('/api/admin/volunteers', methods=['GET'])
@require_auth
def get_all_volunteers():
    """
    GET /api/admin/volunteers
    
    Get all volunteers
    """
    try:
        event_id = request.args.get('event_id')
        volunteers = Volunteer.get_all(event_id=event_id)
        
        volunteers_list = []
        for v in volunteers:
            v_dict = v.to_dict()
            v_dict.pop('password_hash', None)  # Don't send password hashes
            volunteers_list.append(v_dict)
        
        return jsonify({
            'success': True,
            'volunteers': volunteers_list,
            'count': len(volunteers_list)
        }), 200
        
    except Exception as e:
        import traceback
        print(f"❌ Error in get_all_volunteers: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch volunteers', 'details': str(e), 'type': type(e).__name__}), 500


@admin_bp.route('/api/admin/volunteers/<username>', methods=['GET'])
@require_auth
def get_volunteer_by_username(username):
    """Get volunteer by username"""
    try:
        volunteer = Volunteer.get_by_username(username)
        
        if not volunteer:
            return jsonify({'error': 'Volunteer not found'}), 404
        
        volunteer_dict = volunteer.to_dict()
        volunteer_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'volunteer': volunteer_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch volunteer', 'details': str(e)}), 500


@admin_bp.route('/api/admin/volunteers', methods=['POST'])
@require_auth
def create_volunteer():
    """
    POST /api/admin/volunteers
    
    Body:
    {
        "username": "volunteer1",
        "password": "password123",
        "name": "John Volunteer",
        "email": "volunteer@example.com",
        "phone": "+1234567890",
        "assigned_venues": ["venue_id_1", "venue_id_2"]
    }
    """
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        # Validate required fields
        if not data.get('username'):
            return jsonify({'error': 'Username is required'}), 400
        
        if not data.get('password'):
            return jsonify({'error': 'Password is required'}), 400
        
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400

        if FIREBASE_AUTH_REQUIRED and not data.get('email'):
            return jsonify({'error': 'Email is required when Firebase Auth is enabled'}), 400
        
        # Check if username already exists
        existing = Volunteer.get_by_username(data['username'])
        if existing:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create volunteer
        volunteer = Volunteer(
            username=data['username'],
            name=data['name'],
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            assigned_venues=data.get('assigned_venues', []),
            is_active=data.get('is_active', True),
            created_by=admin.username if admin else None
        )
        
        volunteer.set_password(data['password'])
        volunteer_id = volunteer.save()

        # Sync Firebase Auth identity (uses deterministic UID)
        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"volunteer:{volunteer.username}",
            email=volunteer.email,
            password=data['password'],
            display_name=volunteer.name,
            disabled=not volunteer.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Volunteer created but Firebase Auth sync failed: {sync_error}'}), 500
        
        volunteer_dict = volunteer.to_dict()
        volunteer_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'message': 'Volunteer created successfully',
            'volunteer': volunteer_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create volunteer', 'details': str(e)}), 500


@admin_bp.route('/api/admin/volunteers/<username>', methods=['PUT'])
@require_auth
def update_volunteer(username):
    """Update volunteer"""
    try:
        data = request.get_json()
        volunteer = Volunteer.get_by_username(username)
        
        if not volunteer:
            return jsonify({'error': 'Volunteer not found'}), 404
        
        # Update fields
        if 'name' in data:
            volunteer.name = data['name']
        if 'email' in data:
            volunteer.email = data['email']
        if 'phone' in data:
            volunteer.phone = data['phone']
        if 'assigned_venues' in data:
            volunteer.assigned_venues = data['assigned_venues']
        if 'is_active' in data:
            volunteer.is_active = data['is_active']
        if 'password' in data and data['password']:
            volunteer.set_password(data['password'])
        
        volunteer.save()

        # Sync Firebase Auth identity
        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"volunteer:{volunteer.username}",
            email=volunteer.email,
            password=data.get('password'),
            display_name=volunteer.name,
            disabled=not volunteer.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Volunteer updated but Firebase Auth sync failed: {sync_error}'}), 500
        
        volunteer_dict = volunteer.to_dict()
        volunteer_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'message': 'Volunteer updated successfully',
            'volunteer': volunteer_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update volunteer', 'details': str(e)}), 500


@admin_bp.route('/api/admin/volunteers/<username>', methods=['DELETE'])
@require_auth
def delete_volunteer(username):
    """Delete volunteer"""
    try:
        volunteer = Volunteer.get_by_username(username)
        
        if not volunteer:
            return jsonify({'error': 'Volunteer not found'}), 404
        
        # Delete Firebase Auth user (best effort)
        delete_ok, delete_error = _delete_firebase_auth_user(f"volunteer:{volunteer.username}")
        if not delete_ok:
            return jsonify({'error': f'Failed to delete volunteer auth user: {delete_error}'}), 500

        Volunteer.delete(username)
        
        return jsonify({
            'success': True,
            'message': 'Volunteer deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete volunteer', 'details': str(e)}), 500


# ========== SUPER ADMIN - EVENT MANAGEMENT ==========

@admin_bp.route('/api/admin/events', methods=['GET'])
@require_auth
def get_accessible_events():
    """Get events accessible to the current admin."""
    try:
        admin = get_current_admin()
        if not admin:
            return jsonify({'error': 'Not authenticated'}), 401

        if admin.role == 'super_admin':
            events = Event.get_all(limit=100)
        else:
            assigned = admin.assigned_events or []
            events = []
            for event_id in assigned:
                event = Event.get_by_id(event_id)
                if event:
                    events.append(event)

        return jsonify({'events': [event.to_dict() for event in events]}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to load events', 'details': str(e)}), 500

@admin_bp.route('/api/superadmin/events', methods=['GET'])
@require_super_admin
def get_all_events():
    """Get all events (super admin only)"""
    try:
        events = Event.get_all(limit=100)
        return jsonify({
            'events': [event.to_dict() for event in events]
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to load events', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/events', methods=['POST'])
@require_super_admin
def create_event():
    """Create new event (super admin only)"""
    try:
        data = request.get_json()
        admin = get_current_admin()
        
        # Validate required fields
        if not data.get('name') or not data.get('year'):
            return jsonify({'error': 'Event name and year are required'}), 400
        
        # Generate event_id from name and year if not provided
        event_id = data.get('event_id')
        if not event_id:
            # Create event_id as lowercase slug: gdta-2026, conference-2027, etc.
            name_slug = data['name'].lower().replace(' ', '-').replace('_', '-')
            event_id = f"{name_slug}-{data['year']}"
        
        # Create event
        event = Event(
            event_id=event_id,
            name=data['name'],
            year=data['year'],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            location=data.get('location'),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_by=admin.username
        )
        
        event.save()
        
        return jsonify({
            'success': True,
            'message': 'Event created successfully',
            'event': event.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create event', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/events/<event_id>', methods=['PUT'])
@require_super_admin
def update_event(event_id):
    """Update event (super admin only)"""
    try:
        data = request.get_json()
        event = Event.get_by_id(event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        # Update fields
        if 'event_id' in data:
            event.event_id = data['event_id']
        if 'name' in data:
            event.name = data['name']
        if 'year' in data:
            event.year = data['year']
        if 'start_date' in data:
            event.start_date = data['start_date']
        if 'end_date' in data:
            event.end_date = data['end_date']
        if 'location' in data:
            event.location = data['location']
        if 'description' in data:
            event.description = data['description']
        if 'is_active' in data:
            event.is_active = data['is_active']
        
        event.save()
        
        return jsonify({
            'success': True,
            'message': 'Event updated successfully',
            'event': event.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update event', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/events/<event_id>', methods=['DELETE'])
@require_super_admin
def delete_event(event_id):
    """Delete event (super admin only)"""
    try:
        event = Event.get_by_id(event_id)
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        Event.delete(event_id)
        
        return jsonify({
            'success': True,
            'message': 'Event deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete event', 'details': str(e)}), 500


# ========== SUPER ADMIN - ADMIN MANAGEMENT ==========

@admin_bp.route('/api/admin/admins', methods=['GET'])
@require_auth
def get_all_admins_manageable():
    """Get admins list for admin management UI.

    - super_admin: returns all admins
    - admin: returns only non-super-admin users
    """
    try:
        current = get_current_admin()
        if not current:
            return jsonify({'error': 'Not authenticated'}), 401

        db = get_firestore_db()
        docs = db.collection('admin_users').stream()
        admins = [AdminUser.from_dict(doc.id, doc.to_dict()) for doc in docs]

        if current.role != 'super_admin':
            admins = [a for a in admins if a.role != 'super_admin']

        admin_list = []
        for admin in admins:
            admin_dict = admin.to_dict()
            admin_dict.pop('password_hash', None)
            admin_list.append(admin_dict)

        return jsonify({'admins': admin_list}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to load admins', 'details': str(e)}), 500


@admin_bp.route('/api/admin/admins', methods=['POST'])
@require_auth
def create_admin_manageable():
    """Create admin user.

    - super_admin: can create admin/super_admin
    - admin: can create only admin
    """
    try:
        current = get_current_admin()
        if not current:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json() or {}

        if not data.get('username') or not data.get('password') or not data.get('name'):
            return jsonify({'error': 'Username, password, and name are required'}), 400

        if FIREBASE_AUTH_REQUIRED and not data.get('email'):
            return jsonify({'error': 'Email is required when Firebase Auth is enabled'}), 400

        requested_role = data.get('role', 'admin')
        if current.role != 'super_admin' and requested_role != 'admin':
            return jsonify({'error': 'Regular admins can only create admin users'}), 403

        existing = AdminUser.get_by_username(data['username'])
        if existing:
            return jsonify({'error': 'Username already exists'}), 400

        assigned_events = data.get('assigned_events', [])
        if requested_role == 'admin':
            if current.role == 'super_admin':
                if not assigned_events:
                    return jsonify({'error': 'Please assign at least one event to this admin'}), 400
            else:
                # For regular admins, bound event assignments to their own scope
                current_events = set(current.assigned_events or [])
                assigned_events = [eid for eid in assigned_events if eid in current_events]
                if not assigned_events:
                    assigned_events = list(current_events)
                if not assigned_events:
                    return jsonify({'error': 'Your account has no assigned events to delegate'}), 400

        admin = AdminUser(
            username=data['username'],
            email=data.get('email'),
            name=data['name'],
            role=requested_role,
            assigned_events=assigned_events,
            is_active=data.get('is_active', True)
        )
        admin.set_password(data['password'])
        admin.save()

        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"admin:{admin.username}",
            email=admin.email,
            password=data['password'],
            display_name=admin.name,
            disabled=not admin.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Admin created but Firebase Auth sync failed: {sync_error}'}), 500

        admin_dict = admin.to_dict()
        admin_dict.pop('password_hash', None)
        return jsonify({'success': True, 'message': 'Admin created successfully', 'admin': admin_dict}), 201
    except Exception as e:
        return jsonify({'error': 'Failed to create admin', 'details': str(e)}), 500


@admin_bp.route('/api/admin/admins/<username>', methods=['PUT'])
@require_auth
def update_admin_manageable(username):
    """Update admin user with role-aware restrictions."""
    try:
        current = get_current_admin()
        if not current:
            return jsonify({'error': 'Not authenticated'}), 401

        data = request.get_json() or {}
        admin = AdminUser.get_by_username(username)

        if not admin:
            return jsonify({'error': 'Admin not found'}), 404

        if current.role != 'super_admin':
            if admin.role == 'super_admin':
                return jsonify({'error': 'Regular admins cannot modify super admins'}), 403
            if 'role' in data and data['role'] != 'admin':
                return jsonify({'error': 'Regular admins cannot assign super admin role'}), 403

        if 'name' in data:
            admin.name = data['name']
        if 'email' in data:
            admin.email = data['email']
        if 'role' in data and current.role == 'super_admin':
            admin.role = data['role']
        if 'assigned_events' in data:
            if current.role == 'super_admin':
                admin.assigned_events = data['assigned_events']
            else:
                current_events = set(current.assigned_events or [])
                bounded = [eid for eid in (data['assigned_events'] or []) if eid in current_events]
                if not bounded:
                    bounded = list(current_events)
                admin.assigned_events = bounded
        if 'is_active' in data:
            admin.is_active = data['is_active']
        if 'password' in data and data['password']:
            admin.set_password(data['password'])

        admin.save()

        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"admin:{admin.username}",
            email=admin.email,
            password=data.get('password'),
            display_name=admin.name,
            disabled=not admin.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Admin updated but Firebase Auth sync failed: {sync_error}'}), 500

        admin_dict = admin.to_dict()
        admin_dict.pop('password_hash', None)

        return jsonify({'success': True, 'message': 'Admin updated successfully', 'admin': admin_dict}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to update admin', 'details': str(e)}), 500


@admin_bp.route('/api/admin/admins/<username>', methods=['DELETE'])
@require_auth
def delete_admin_manageable(username):
    """Delete admin user with role-aware restrictions."""
    try:
        current = get_current_admin()
        if not current:
            return jsonify({'error': 'Not authenticated'}), 401

        admin = AdminUser.get_by_username(username)
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404

        if current.role != 'super_admin':
            if admin.role == 'super_admin':
                return jsonify({'error': 'Regular admins cannot delete super admins'}), 403
            if username == current.username:
                return jsonify({'error': 'Regular admins cannot delete their own account'}), 400
        else:
            if admin.role == 'super_admin':
                db = get_firestore_db()
                super_admins = db.collection('admin_users').where('role', '==', 'super_admin').stream()
                if len(list(super_admins)) <= 1:
                    return jsonify({'error': 'Cannot delete the last super admin'}), 400

        delete_ok, delete_error = _delete_firebase_auth_user(f"admin:{admin.username}")
        if not delete_ok:
            return jsonify({'error': f'Failed to delete admin auth user: {delete_error}'}), 500

        db = get_firestore_db()
        db.collection('admin_users').document(username).delete()

        return jsonify({'success': True, 'message': 'Admin deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete admin', 'details': str(e)}), 500

@admin_bp.route('/api/superadmin/admins', methods=['GET'])
@require_super_admin
def get_all_admins():
    """Get all admins (super admin only)"""
    try:
        db = get_firestore_db()
        docs = db.collection('admin_users').stream()
        admins = [AdminUser.from_dict(doc.id, doc.to_dict()) for doc in docs]
        
        admin_list = []
        for admin in admins:
            admin_dict = admin.to_dict()
            admin_dict.pop('password_hash', None)
            admin_list.append(admin_dict)
        
        return jsonify({'admins': admin_list}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to load admins', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/admins', methods=['POST'])
@require_super_admin
def create_admin():
    """Create new admin (super admin only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password') or not data.get('name'):
            return jsonify({'error': 'Username, password, and name are required'}), 400

        if FIREBASE_AUTH_REQUIRED and not data.get('email'):
            return jsonify({'error': 'Email is required when Firebase Auth is enabled'}), 400
        
        # Check if username already exists
        existing = AdminUser.get_by_username(data['username'])
        if existing:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Create admin
        admin = AdminUser(
            username=data['username'],
            email=data.get('email'),
            name=data['name'],
            role=data.get('role', 'admin'),
            assigned_events=data.get('assigned_events', []),
            is_active=data.get('is_active', True)
        )
        admin.set_password(data['password'])
        admin.save()

        # Sync Firebase Auth identity
        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"admin:{admin.username}",
            email=admin.email,
            password=data['password'],
            display_name=admin.name,
            disabled=not admin.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Admin created but Firebase Auth sync failed: {sync_error}'}), 500
        
        admin_dict = admin.to_dict()
        admin_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'message': 'Admin created successfully',
            'admin': admin_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create admin', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/admins/<username>', methods=['PUT'])
@require_super_admin
def update_admin_user(username):
    """Update admin (super admin only)"""
    try:
        data = request.get_json()
        admin = AdminUser.get_by_username(username)
        
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Update fields
        if 'name' in data:
            admin.name = data['name']
        if 'email' in data:
            admin.email = data['email']
        if 'role' in data:
            admin.role = data['role']
        if 'assigned_events' in data:
            admin.assigned_events = data['assigned_events']
        if 'is_active' in data:
            admin.is_active = data['is_active']
        if 'password' in data and data['password']:
            admin.set_password(data['password'])
        
        admin.save()

        # Sync Firebase Auth identity
        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"admin:{admin.username}",
            email=admin.email,
            password=data.get('password'),
            display_name=admin.name,
            disabled=not admin.is_active
        )
        if not sync_ok:
            return jsonify({'error': f'Admin updated but Firebase Auth sync failed: {sync_error}'}), 500
        
        admin_dict = admin.to_dict()
        admin_dict.pop('password_hash', None)
        
        return jsonify({
            'success': True,
            'message': 'Admin updated successfully',
            'admin': admin_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update admin', 'details': str(e)}), 500


@admin_bp.route('/api/superadmin/admins/<username>', methods=['DELETE'])
@require_super_admin
def delete_admin_user(username):
    """Delete admin (super admin only)"""
    try:
        admin = AdminUser.get_by_username(username)
        
        if not admin:
            return jsonify({'error': 'Admin not found'}), 404
        
        # Prevent deleting the last super admin
        if admin.role == 'super_admin':
            db = get_firestore_db()
            super_admins = db.collection('admin_users').where('role', '==', 'super_admin').stream()
            if len(list(super_admins)) <= 1:
                return jsonify({'error': 'Cannot delete the last super admin'}), 400

        # Delete Firebase Auth user (best effort)
        delete_ok, delete_error = _delete_firebase_auth_user(f"admin:{admin.username}")
        if not delete_ok:
            return jsonify({'error': f'Failed to delete admin auth user: {delete_error}'}), 500
        
        db = get_firestore_db()
        db.collection('admin_users').document(username).delete()
        
        return jsonify({
            'success': True,
            'message': 'Admin deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete admin', 'details': str(e)}), 500


# ========== ADMIN INFO ==========

@admin_bp.route('/api/admin/me', methods=['GET'])
@require_auth
def get_current_admin_info():
    """Get current admin info including role and assigned events"""
    admin = get_current_admin()
    if not admin:
        return jsonify({'error': 'Not authenticated'}), 401
    
    admin_dict = admin.to_dict()
    admin_dict.pop('password_hash', None)
    
    return jsonify({'admin': admin_dict}), 200


# ========== SUPER ADMIN SETUP (ONE-TIME) ==========

@admin_bp.route('/api/super-admin-setup', methods=['POST'])
def super_admin_setup():
    """One-time endpoint to create the first super admin"""
    try:
        # Check if any super admin already exists
        db = get_firestore_db()
        super_admins = list(db.collection('admin_users').where('role', '==', 'super_admin').limit(1).stream())
        
        if super_admins:
            return jsonify({'error': 'Super admin already exists. This endpoint can only be used once.'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('username') or not data.get('password') or not data.get('name'):
            return jsonify({'error': 'Username, password, and name are required'}), 400

        if FIREBASE_AUTH_REQUIRED and not data.get('email'):
            return jsonify({'error': 'Email is required when Firebase Auth is enabled'}), 400
        
        # Create super admin
        super_admin = AdminUser(
            username=data['username'],
            email=data.get('email'),
            name=data['name'],
            role='super_admin',
            assigned_events=[],  # Super admins have access to all events
            is_active=True
        )
        super_admin.set_password(data['password'])
        super_admin.save()

        # Sync Firebase Auth identity
        sync_ok, sync_error = _sync_firebase_auth_user(
            uid=f"admin:{super_admin.username}",
            email=super_admin.email,
            password=data['password'],
            display_name=super_admin.name,
            disabled=False
        )
        if not sync_ok:
            return jsonify({'error': f'Super Admin created but Firebase Auth sync failed: {sync_error}'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Super Admin created successfully',
            'username': super_admin.username
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create super admin', 'details': str(e)}), 500


