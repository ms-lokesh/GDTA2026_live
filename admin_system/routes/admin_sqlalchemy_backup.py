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

from db.models import (
    get_db_session, Registration, AdminUser, EmailLog
)

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


def send_smtp_email(to_email, subject, body):
    """
    Send email using SMTP (Gmail)
    Returns (success, error_message)
    """
    if not EMAIL_CONFIG['username'] or not EMAIL_CONFIG['password'] or EMAIL_CONFIG['password'] == 'your_app_password_here':
        return False, "Email not configured. Please set EMAIL_USERNAME and EMAIL_PASSWORD in .env file"
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{EMAIL_CONFIG['from_name']} <{EMAIL_CONFIG['username']}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
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
        
        msg.attach(text_part)
        msg.attach(html_part)
        
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


def get_current_admin():
    """Get the currently logged in admin user"""
    if 'admin_user_id' not in session:
        return None
    
    db_session = get_db_session()
    admin = db_session.query(AdminUser).filter_by(
        id=session['admin_user_id'],
        is_active=True
    ).first()
    db_session.close()
    return admin


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
        
        db_session = get_db_session()
        admin = db_session.query(AdminUser).filter_by(
            username=username,
            is_active=True
        ).first()
        
        if not admin or not check_password_hash(admin.password_hash, password):
            db_session.close()
            return jsonify({'error': 'Invalid username or password'}), 401
        
        # Update last login
        admin.last_login = datetime.utcnow()
        db_session.commit()
        
        # Create session
        session['admin_user_id'] = admin.id
        session['admin_username'] = admin.username
        session['admin_role'] = admin.role
        session.permanent = True
        
        user_dict = admin.to_dict()
        db_session.close()
        
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
        db_session = get_db_session()
        query = db_session.query(Registration)
        
        # Apply filters
        status = request.args.get('status')
        if status:
            query = query.filter(Registration.status == status)
        
        country = request.args.get('country')
        if country:
            query = query.filter(Registration.country == country)
        
        search = request.args.get('search')
        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (Registration.name.like(search_pattern)) |
                (Registration.email.like(search_pattern)) |
                (Registration.institution.like(search_pattern))
            )
        
        # Get total count before pagination
        total_count = query.count()
        
        # Sorting
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if hasattr(Registration, sort_by):
            sort_column = getattr(Registration, sort_by)
            if sort_order == 'asc':
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())
        
        # Pagination
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        registrations = query.limit(limit).offset(offset).all()
        
        result = {
            'total': total_count,
            'limit': limit,
            'offset': offset,
            'registrations': [r.to_dict() for r in registrations]
        }
        
        db_session.close()
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch registrations', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/<int:registration_id>', methods=['GET'])
@require_auth
def get_registration_details(registration_id):
    """Get details of a specific registration"""
    try:
        db_session = get_db_session()
        registration = db_session.query(Registration).filter_by(id=registration_id).first()
        
        if not registration:
            db_session.close()
            return jsonify({'error': 'Registration not found'}), 404
        
        result = registration.to_dict()
        db_session.close()
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch registration', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/<int:registration_id>', methods=['PUT'])
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
        
        db_session = get_db_session()
        registration = db_session.query(Registration).filter_by(id=registration_id).first()
        
        if not registration:
            db_session.close()
            return jsonify({'error': 'Registration not found'}), 404
        
        # Update fields
        if 'status' in data:
            registration.status = data['status']
        
        if 'admin_notes' in data:
            registration.admin_notes = data['admin_notes']
        
        registration.updated_at = datetime.utcnow()
        db_session.commit()
        
        result = registration.to_dict()
        db_session.close()
        
        return jsonify({
            'success': True,
            'message': 'Registration updated successfully',
            'registration': result
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to update registration', 'details': str(e)}), 500


@admin_bp.route('/api/admin/registrations/<int:registration_id>', methods=['DELETE'])
@require_auth
def delete_registration(registration_id):
    """Delete a registration (use with caution)"""
    try:
        admin = get_current_admin()
        if admin.role != 'admin':
            return jsonify({'error': 'Only admins can delete registrations'}), 403
        
        db_session = get_db_session()
        registration = db_session.query(Registration).filter_by(id=registration_id).first()
        
        if not registration:
            db_session.close()
            return jsonify({'error': 'Registration not found'}), 404
        
        db_session.delete(registration)
        db_session.commit()
        db_session.close()
        
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
        db_session = get_db_session()
        
        # Total registrations
        total = db_session.query(Registration).count()
        
        # By status
        pending = db_session.query(Registration).filter_by(status='pending').count()
        approved = db_session.query(Registration).filter_by(status='approved').count()
        rejected = db_session.query(Registration).filter_by(status='rejected').count()
        
        # By country (top 10)
        from sqlalchemy import func
        countries = db_session.query(
            Registration.country,
            func.count(Registration.id).label('count')
        ).group_by(Registration.country).order_by(func.count(Registration.id).desc()).limit(10).all()
        
        # By role
        roles = db_session.query(
            Registration.role,
            func.count(Registration.id).label('count')
        ).group_by(Registration.role).all()
        
        # Recent registrations (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent = db_session.query(Registration).filter(
            Registration.created_at >= seven_days_ago
        ).count()
        
        # Today's registrations
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today = db_session.query(Registration).filter(
            Registration.created_at >= today_start
        ).count()
        
        db_session.close()
        
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
        return jsonify({'error': 'Failed to fetch statistics', 'details': str(e)}), 500


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
        
        db_session = get_db_session()
        
        # Determine recipients
        recipients = []
        
        if data.get('registration_ids') == 'all' or data.get('filter'):
            # Bulk email with optional filter
            query = db_session.query(Registration)
            
            if data.get('filter'):
                filters = data['filter']
                if filters.get('country'):
                    query = query.filter(Registration.country == filters['country'])
                if filters.get('status'):
                    query = query.filter(Registration.status == filters['status'])
            
            recipients = query.all()
        
        elif data.get('registration_ids'):
            # Specific registrants
            reg_ids = data['registration_ids']
            recipients = db_session.query(Registration).filter(
                Registration.id.in_(reg_ids)
            ).all()
        
        else:
            return jsonify({'error': 'No recipients specified'}), 400
        
        # Send emails with real SMTP
        sent_count = 0
        failed_count = 0
        failed_emails = []
        
        for recipient in recipients:
            try:
                # Send actual email via SMTP
                success, error = send_smtp_email(
                    to_email=recipient.email,
                    subject=subject,
                    body=message
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
                    db_session.add(email_log)
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
                    db_session.add(email_log)
                    failed_count += 1
                    failed_emails.append(f"{recipient.email}: {error}")
                    print(f"[EMAIL ERROR] Failed to send to {recipient.email}: {error}")
                
            except Exception as e:
                failed_count += 1
                failed_emails.append(f"{recipient.email}: {str(e)}")
                print(f"[EMAIL ERROR] Exception sending to {recipient.email}: {str(e)}")
        
        db_session.commit()
        db_session.close()
        
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
        
        db_session = get_db_session()
        registrations = db_session.query(Registration).all()
        
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
            writer.writerow([
                reg.id, reg.name, reg.email, reg.institution, reg.role,
                reg.gdta_member, reg.gdta_affiliation or '', reg.country, reg.state or '',
                reg.registration_source, reg.status, reg.created_at.isoformat()
            ])
        
        db_session.close()
        
        # Return CSV
        from flask import Response
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=gdta2026_registrations.csv'}
        )
        
    except Exception as e:
        return jsonify({'error': 'Failed to export', 'details': str(e)}), 500
