"""
Admin Routes - API endpoints for coordinator dashboard
Handles authentication, registration management, and email sending
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash, generate_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

from db.firebase_models import (
    Registration, AdminUser, EmailLog, Venue, AccessLog, Volunteer, Event
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
        
        username = data['username']
        password = data['password']
        
        admin = AdminUser.get_by_username(username)
        
        if not admin or not admin.is_active or not admin.check_password(password):
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
        - status: pending/approved/rejected
        - country: filter by country
        - search: search in name, email, institution
        - limit: number of results (default 100)
        - offset: pagination offset (default 0)
        - sort_by: field to sort by (default: created_at)
        - sort_order: asc/desc (default: desc)
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Apply filters
        filters = {}
        
        # Event ID filter
        event_id = request.args.get('event_id')
        if event_id:
            filters['event_id'] = event_id
        
        status = request.args.get('status')
        if status:
            filters['status'] = status
        
        country = request.args.get('country')
        if country:
            filters['country'] = country
        
        # Get registrations from Firebase
        registrations = Registration.get_all(limit=limit, offset=offset, filters=filters if filters else None)
        print(f"Retrieved {len(registrations)} registrations from Firebase")
        
        # Get total count
        total_count = Registration.count(filters=filters if filters else None)
        print(f"Total count: {total_count}")
        
        # Apply search filter post-query (Firebase doesn't support LIKE)
        search = request.args.get('search')
        if search and registrations:
            search_lower = search.lower()
            registrations = [
                r for r in registrations 
                if (search_lower in r.name.lower() or 
                    search_lower in r.email.lower() or 
                    search_lower in r.institution.lower())
            ]
        
        result = {
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'registrations': [r.to_dict() for r in registrations]
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
                    qr_data=registration.unique_id
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
                            qr_data=recipient.unique_id
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


@admin_bp.route('/api/admin/export', methods=['GET'])
@require_auth
def export_registrations():
    """
    GET /api/admin/export?format=csv
    
    Export registrations to CSV
    """
    try:
        import csv
        from io import StringIO
        
        # Get event_id filter
        event_id = request.args.get('event_id')
        filters = {}
        if event_id:
            filters['event_id'] = event_id
        
        registrations = Registration.get_all(limit=1000, filters=filters if filters else None)
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Name', 'Email', 'Institution', 'Role', 
            'GDTA Member', 'GDTA Affiliation', 'Country', 'State',
            'Registration Source', 'Status', 'Created At'
        ])
        
        # Data
        for reg in registrations:
            created_at = reg.created_at.isoformat() if isinstance(reg.created_at, datetime) else str(reg.created_at)
            writer.writerow([
                reg.id, reg.name, reg.email, reg.institution, reg.role,
                reg.gdta_member, reg.gdta_affiliation or '', reg.country, reg.state or '',
                reg.registration_source, reg.status, created_at
            ])
        
        # Return CSV
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=gdta2026_registrations.csv'}
        )
        
    except Exception as e:
        return jsonify({'error': 'Failed to export', 'details': str(e)}), 500


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
            qr_data=registration.unique_id  # QR contains unique_id
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
                qr_data=unique_id
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
@require_auth
def generate_id_cards_batch():
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
                    qr_data=reg.unique_id  # Use unique_id in QR code
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
        
        username = data['username']
        password = data['password']
        
        volunteer = Volunteer.get_by_username(username)
        
        if not volunteer or not volunteer.is_active or not volunteer.check_password(password):
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
        
        Volunteer.delete(username)
        
        return jsonify({
            'success': True,
            'message': 'Volunteer deleted successfully'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to delete volunteer', 'details': str(e)}), 500


# ========== SUPER ADMIN - EVENT MANAGEMENT ==========

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
        
        # Create event
        event = Event(
            name=data['name'],
            year=data['year'],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            location=data.get('location'),
            description=data.get('description'),
            is_active=data.get('is_active', True),
            created_by=admin.username
        )
        
        event_id = event.save()
        
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
        
        return jsonify({
            'success': True,
            'message': 'Super Admin created successfully',
            'username': super_admin.username
        }), 201
        
    except Exception as e:
        return jsonify({'error': 'Failed to create super admin', 'details': str(e)}), 500


