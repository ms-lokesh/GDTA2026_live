"""
Hackathon Registration Route - API endpoints for GDTA Challenge 2026
Handles hackathon participant registration and management
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
from db.firebase_models import HackathonRegistration, SimpleHackathonRegistration, EmailLog
from google.cloud.firestore import SERVER_TIMESTAMP
from functools import wraps
import re

hackathon_bp = Blueprint('hackathon', __name__)

EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
NAME_REGEX = re.compile(r"^[A-Za-z][A-Za-z .'\-]{1,99}$")
PHONE_ALLOWED_REGEX = re.compile(r"^[0-9+\-\s()]{8,20}$")
SIMPLE_HACKATHON_STATUSES = ['new', 'in_review', 'shortlisted', 'waitlisted', 'approved', 'rejected', 'closed']
SIMPLE_HACKATHON_PRIORITIES = ['low', 'medium', 'high', 'urgent']


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def _normalize_email(value):
    return _clean_text(value).lower()


def _normalize_phone(value):
    return _clean_text(value)


def _is_valid_phone(value):
    if not PHONE_ALLOWED_REGEX.fullmatch(value):
        return False

    digit_count = len(re.sub(r"\D", "", value))
    return 10 <= digit_count <= 15


def _serialize_simple_registration(registration):
    normalized_status = registration.status or 'new'
    normalized_priority = registration.priority or 'medium'
    return {
        "id": registration.id,
        "ticket_id": registration.ticket_id,
        "name": registration.name,
        "email": registration.email,
        "phone": registration.phone,
        "college": registration.college,
        "track": registration.track,
        "status": normalized_status,
        "priority": normalized_priority,
        "assigned_to": registration.assigned_to,
        "created_at": registration.created_at.isoformat() if registration.created_at else None,
        "updated_at": registration.updated_at.isoformat() if registration.updated_at else None,
        "last_contact_at": registration.last_contact_at.isoformat() if registration.last_contact_at else None,
        "resolved_at": registration.resolved_at.isoformat() if registration.resolved_at else None,
        "admin_notes": registration.admin_notes,
        "ticket_history": registration.ticket_history or []
    }


def require_admin_auth(f):
    """Require an authenticated admin session for admin-side hackathon controls."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            return jsonify({
                'error': 'Authentication required',
                'code': 'AUTH_REQUIRED'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


@hackathon_bp.route('/api/hackathon/register', methods=['POST'])
def register_participant():
    """
    POST /api/hackathon/register
    
    Register a new hackathon participant
    
    Body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "institution": "University Name",
        "role": "student",
        "country": "USA",
        "state": "California",
        "participation_type": "student_innovator",
        "challenge_track": "healthcare",
        "team_name": "Team Alpha",
        "team_size": 3,
        "team_members": ["Member 1", "Member 2"],
        "github_username": "johndoe",
        "linkedin_url": "https://linkedin.com/in/johndoe",
        "portfolio_url": "https://johndoe.com",
        "technical_skills": ["Python", "AI/ML", "React"],
        "experience_level": "intermediate",
        "project_idea": "AI Healthcare Monitor",
        "project_description": "Detailed description...",
        "why_participate": "Reason for participation...",
        "previous_hackathons": "List of previous hackathons",
        "need_mentorship": false,
        "can_mentor": false,
        "consent": true
    }
    
    Returns:
        {
            "message": "Registration successful",
            "registration_id": "email@example.com",
            "unique_id": "ABC12345"
        }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'institution', 'role', 
                          'country', 'participation_type', 'challenge_track', 'consent']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "error": f"Missing required field: {field}"
                }), 400
        
        # Check if email already registered
        existing = HackathonRegistration.get_by_email(data['email'])
        if existing:
            return jsonify({
                "error": "This email is already registered for the hackathon",
                "registration_id": existing.id
            }), 409
        
        # Create new registration
        registration = HackathonRegistration(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            institution=data['institution'],
            role=data['role'],
            country=data['country'],
            state=data.get('state'),
            participation_type=data['participation_type'],
            challenge_track=data['challenge_track'],
            team_name=data.get('team_name'),
            team_size=data.get('team_size', 1),
            team_members=data.get('team_members', []),
            github_username=data.get('github_username'),
            linkedin_url=data.get('linkedin_url'),
            portfolio_url=data.get('portfolio_url'),
            technical_skills=data.get('technical_skills', []),
            experience_level=data.get('experience_level', 'intermediate'),
            project_idea=data.get('project_idea'),
            project_description=data.get('project_description'),
            why_participate=data.get('why_participate'),
            previous_hackathons=data.get('previous_hackathons'),
            need_mentorship=data.get('need_mentorship', False),
            can_mentor=data.get('can_mentor', False),
            consent=data['consent'],
            status='pending'
        )
        
        # Save to database
        reg_id = registration.save()
        
        print(f"✅ Hackathon registration created: {reg_id}")
        
        return jsonify({
            "message": "Registration successful! You'll receive a confirmation email shortly.",
            "registration_id": reg_id,
            "unique_id": registration.unique_id,
            "status": "pending"
        }), 201
        
    except Exception as e:
        print(f"❌ Error in hackathon registration: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Registration failed. Please try again.",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/registrations', methods=['GET'])
@require_admin_auth
def get_all_registrations():
    """
    GET /api/hackathon/registrations
    
    Get all hackathon registrations with optional filters
    
    Query params:
        - limit: Number of results (default: 100)
        - offset: Pagination offset (default: 0)
        - status: Filter by status
        - challenge_track: Filter by track
        - participation_type: Filter by participation type
    
    Returns:
        {
            "registrations": [...],
            "count": 123,
            "limit": 100,
            "offset": 0
        }
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Build filters
        filters = {}
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        if request.args.get('challenge_track'):
            filters['challenge_track'] = request.args.get('challenge_track')
        if request.args.get('participation_type'):
            filters['participation_type'] = request.args.get('participation_type')
        
        # Get registrations
        registrations = HackathonRegistration.get_all(limit=limit, offset=offset, filters=filters)
        total_count = HackathonRegistration.count(filters=filters)
        
        return jsonify({
            "registrations": [reg.to_dict() for reg in registrations],
            "count": total_count,
            "limit": limit,
            "offset": offset,
            "filters": filters
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching registrations: {e}")
        return jsonify({
            "error": "Failed to fetch registrations",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/registration/<registration_id>', methods=['GET'])
@require_admin_auth
def get_registration(registration_id):
    """
    GET /api/hackathon/registration/<registration_id>
    
    Get a specific registration by ID
    """
    try:
        registration = HackathonRegistration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        return jsonify(registration.to_dict()), 200
        
    except Exception as e:
        print(f"❌ Error fetching registration: {e}")
        return jsonify({
            "error": "Failed to fetch registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/registration/<registration_id>', methods=['PUT'])
@require_admin_auth
def update_registration(registration_id):
    """
    PUT /api/hackathon/registration/<registration_id>
    
    Update a registration (for admin or participant updates)
    
    Body: Any fields to update
    """
    try:
        registration = HackathonRegistration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        data = request.get_json()
        
        # Update allowed fields
        updatable_fields = [
            'name', 'phone', 'institution', 'role', 'country', 'state',
            'participation_type', 'challenge_track', 'team_name', 'team_size',
            'team_members', 'github_username', 'linkedin_url', 'portfolio_url',
            'technical_skills', 'experience_level', 'project_idea', 
            'project_description', 'why_participate', 'previous_hackathons',
            'need_mentorship', 'can_mentor', 'status', 'submission_url',
            'submission_date', 'score', 'judge_notes', 'admin_notes'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(registration, field, data[field])
        
        registration.save()
        
        return jsonify({
            "message": "Registration updated successfully",
            "registration": registration.to_dict()
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating registration: {e}")
        return jsonify({
            "error": "Failed to update registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/registration/<registration_id>/submit', methods=['POST'])
@require_admin_auth
def submit_project(registration_id):
    """
    POST /api/hackathon/registration/<registration_id>/submit
    
    Submit final project for a registration
    
    Body:
    {
        "submission_url": "https://github.com/user/project"
    }
    """
    try:
        registration = HackathonRegistration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        data = request.get_json()
        
        if not data.get('submission_url'):
            return jsonify({
                "error": "Submission URL is required"
            }), 400
        
        registration.submission_url = data['submission_url']
        registration.submission_date = datetime.utcnow()
        registration.status = 'submitted'
        registration.save()
        
        return jsonify({
            "message": "Project submitted successfully",
            "submission_url": registration.submission_url,
            "submission_date": registration.submission_date.isoformat()
        }), 200
        
    except Exception as e:
        print(f"❌ Error submitting project: {e}")
        return jsonify({
            "error": "Failed to submit project",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/registration/<registration_id>', methods=['DELETE'])
@require_admin_auth
def delete_registration(registration_id):
    """
    DELETE /api/hackathon/registration/<registration_id>
    
    Delete a registration (admin only)
    """
    try:
        registration = HackathonRegistration.get_by_id(registration_id)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        HackathonRegistration.delete(registration_id)
        
        return jsonify({
            "message": "Registration deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"❌ Error deleting registration: {e}")
        return jsonify({
            "error": "Failed to delete registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/stats', methods=['GET'])
@require_admin_auth
def get_hackathon_stats():
    """
    GET /api/hackathon/stats
    
    Get hackathon statistics
    
    Returns:
        {
            "total_registrations": 123,
            "by_status": {...},
            "by_track": {...},
            "by_participation_type": {...}
        }
    """
    try:
        total = HackathonRegistration.count()
        
        # Get counts by status
        by_status = {
            'pending': HackathonRegistration.count({'status': 'pending'}),
            'approved': HackathonRegistration.count({'status': 'approved'}),
            'submitted': HackathonRegistration.count({'status': 'submitted'}),
            'qualified': HackathonRegistration.count({'status': 'qualified'}),
            'winner': HackathonRegistration.count({'status': 'winner'})
        }
        
        # Get counts by track
        by_track = {
            'healthcare': HackathonRegistration.count({'challenge_track': 'healthcare'}),
            'edtech': HackathonRegistration.count({'challenge_track': 'edtech'}),
            'sustainability': HackathonRegistration.count({'challenge_track': 'sustainability'})
        }
        
        # Get counts by participation type
        by_participation_type = {
            'student_innovator': HackathonRegistration.count({'participation_type': 'student_innovator'}),
            'developer_professional': HackathonRegistration.count({'participation_type': 'developer_professional'})
        }
        
        return jsonify({
            "total_registrations": total,
            "by_status": by_status,
            "by_track": by_track,
            "by_participation_type": by_participation_type
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        return jsonify({
            "error": "Failed to fetch statistics",
            "details": str(e)
        }), 500


# ========== SIMPLE HACKATHON REGISTRATION ENDPOINTS ==========

@hackathon_bp.route('/api/hackathon/simple-register', methods=['POST'])
def simple_register_participant():
    """
    POST /api/hackathon/simple-register
    
    Register a participant with simple hackathon form (name, college, track)
    
    Body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+91 98765 43210",
        "college": "Massachusetts Institute of Technology",
        "track": "healthcare"
    }
    
    Returns:
        {
            "message": "Registration successful",
            "registration_id": "john@example.com"
        }
    """
    try:
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'college', 'track']
        
        for field in required_fields:
            if field not in data or not _clean_text(data[field]):
                return jsonify({
                    "error": f"Missing required field: {field}"
                }), 400

        name = _clean_text(data.get('name'))
        email = _normalize_email(data.get('email'))
        phone = _normalize_phone(data.get('phone'))
        college = _clean_text(data.get('college'))
        track = _clean_text(data.get('track')).lower()

        if not NAME_REGEX.fullmatch(name):
            return jsonify({
                "error": "Name must be 2-100 characters and contain only letters, spaces, apostrophes, periods, or hyphens"
            }), 400

        if not EMAIL_REGEX.fullmatch(email):
            return jsonify({
                "error": "Please enter a valid email address"
            }), 400

        if not _is_valid_phone(phone):
            return jsonify({
                "error": "Phone number must contain 10-15 digits and only valid phone characters"
            }), 400

        if len(college) < 2 or len(college) > 150:
            return jsonify({
                "error": "College/Organization must be between 2 and 150 characters"
            }), 400
        
        # Check if email already registered
        existing = SimpleHackathonRegistration.get_by_email(email)
        if existing:
            return jsonify({
                "error": "This email is already registered for the hackathon",
                "registration_id": existing.id
            }), 409
        
        # Validate track
        valid_tracks = ['healthcare', 'edtech', 'smart_city']
        if track not in valid_tracks:
            return jsonify({
                "error": f"Invalid track. Must be one of: {', '.join(valid_tracks)}"
            }), 400
        
        # Create new registration
        registration = SimpleHackathonRegistration(
            name=name,
            email=email,
            phone=phone,
            college=college,
            track=track,
            status='new',
            priority='medium'
        )
        registration.add_history_entry('registration_received', note='Registration entered the admin ticket queue')
        
        reg_id = registration.save()
        
        return jsonify({
            "message": "Registration successful",
            "registration_id": reg_id
        }), 201
        
    except Exception as e:
        print(f"❌ Error in simple_register_participant: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Registration failed",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations', methods=['GET'])
@require_admin_auth
def get_simple_registrations():
    """
    GET /api/hackathon/simple-registrations?track=healthcare&limit=50&offset=0
    
    Get all simple hackathon registrations with optional filtering
    """
    try:
        # Parse query parameters
        track = request.args.get('track')
        status = _clean_text(request.args.get('status')).lower()
        priority = _clean_text(request.args.get('priority')).lower()
        assigned_to = _clean_text(request.args.get('assigned_to'))
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        # Build filters
        filters = {}
        if track:
            filters['track'] = track
        if status:
            filters['status'] = status
        if priority:
            filters['priority'] = priority
        if assigned_to:
            filters['assigned_to'] = assigned_to
        
        # Get registrations
        registrations = SimpleHackathonRegistration.get_all(
            limit=limit,
            offset=offset,
            filters=filters if filters else None
        )
        
        total_count = SimpleHackathonRegistration.count(filters if filters else None)
        
        return jsonify({
            "registrations": [_serialize_simple_registration(r) for r in registrations],
            "total": total_count,
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching simple registrations: {e}")
        return jsonify({
            "error": "Failed to fetch registrations",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations/<email>', methods=['GET'])
@require_admin_auth
def get_simple_registration(email):
    """
    GET /api/hackathon/simple-registrations/<email>
    
    Get a specific simple hackathon registration by email
    """
    try:
        registration = SimpleHackathonRegistration.get_by_email(email)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        return jsonify(_serialize_simple_registration(registration)), 200
        
    except Exception as e:
        print(f"❌ Error fetching registration: {e}")
        return jsonify({
            "error": "Failed to fetch registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations/<email>', methods=['PUT'])
@require_admin_auth
def update_simple_registration(email):
    """
    PUT /api/hackathon/simple-registrations/<email>
    
    Update a simple hackathon registration (admin only)
    
    Body:
    {
        "status": "confirmed",
        "admin_notes": "Selected for next round"
    }
    """
    try:
        registration = SimpleHackathonRegistration.get_by_email(email)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        data = request.get_json() or {}
        actor = session.get('admin_username') or session.get('admin_user_id') or 'admin'
        status_before = registration.status
        priority_before = registration.priority
        assigned_before = registration.assigned_to
        note_before = registration.admin_notes or ''
        
        # Update fields
        if 'status' in data:
            next_status = _clean_text(data['status']).lower()
            if next_status not in SIMPLE_HACKATHON_STATUSES:
                return jsonify({
                    "error": f"Invalid status. Must be one of: {', '.join(SIMPLE_HACKATHON_STATUSES)}"
                }), 400
            registration.status = next_status
        if 'priority' in data:
            next_priority = _clean_text(data['priority']).lower()
            if next_priority not in SIMPLE_HACKATHON_PRIORITIES:
                return jsonify({
                    "error": f"Invalid priority. Must be one of: {', '.join(SIMPLE_HACKATHON_PRIORITIES)}"
                }), 400
            registration.priority = next_priority
        if 'assigned_to' in data:
            assigned_to = _clean_text(data['assigned_to'])
            registration.assigned_to = assigned_to or None
        if 'last_contact_at' in data and _clean_text(data['last_contact_at']):
            try:
                registration.last_contact_at = datetime.fromisoformat(_clean_text(data['last_contact_at']).replace('Z', '+00:00'))
            except ValueError:
                return jsonify({"error": "last_contact_at must be a valid ISO datetime"}), 400
        if 'admin_notes' in data:
            registration.admin_notes = _clean_text(data['admin_notes']) or None

        if registration.status in ['approved', 'rejected', 'closed'] and not registration.resolved_at:
            registration.resolved_at = datetime.utcnow()
        elif registration.status not in ['approved', 'rejected', 'closed']:
            registration.resolved_at = None

        history_changes = {}
        if registration.status != status_before:
            history_changes['status'] = {'from': status_before, 'to': registration.status}
        if registration.priority != priority_before:
            history_changes['priority'] = {'from': priority_before, 'to': registration.priority}
        if registration.assigned_to != assigned_before:
            history_changes['assigned_to'] = {'from': assigned_before, 'to': registration.assigned_to}
        if (registration.admin_notes or '') != note_before:
            history_changes['admin_notes_updated'] = True

        if history_changes:
            registration.add_history_entry(
                'ticket_updated',
                actor=actor,
                note=registration.admin_notes,
                metadata=history_changes
            )
        
        registration.save()
        
        return jsonify({
            "message": "Registration updated successfully",
            "registration_id": registration.id,
            "registration": _serialize_simple_registration(registration)
        }), 200
        
    except Exception as e:
        print(f"❌ Error updating registration: {e}")
        return jsonify({
            "error": "Failed to update registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations/send-email', methods=['POST'])
@require_admin_auth
def email_simple_registrations():
    """
    POST /api/hackathon/simple-registrations/send-email

    Send email to one or more simple hackathon registrations.

    Body:
    {
        "recipient_emails": ["person@example.com"],
        "subject": "Hackathon Update",
        "message": "Email body..."
    }

    Or:
    {
        "filter": {
            "status": "new",
            "priority": "high",
            "track": "edtech",
            "assigned_to": "admin"
        },
        "subject": "Hackathon Update",
        "message": "Email body..."
    }
    """
    try:
        from routes.admin import send_smtp_email

        data = request.get_json() or {}
        subject = _clean_text(data.get('subject'))
        message = str(data.get('message') or '').strip()
        actor = session.get('admin_username') or session.get('admin_user_id') or 'admin'

        if not subject or not message:
            return jsonify({"error": "Subject and message are required"}), 400

        recipients = []

        if data.get('recipient_emails'):
            for email in data.get('recipient_emails', []):
                normalized_email = _normalize_email(email)
                if not normalized_email:
                    continue
                registration = SimpleHackathonRegistration.get_by_email(normalized_email)
                if registration:
                    recipients.append(registration)
        elif data.get('filter'):
            raw_filter = data.get('filter') or {}
            filters = {}
            for key in ['status', 'priority', 'track', 'assigned_to']:
                value = _clean_text(raw_filter.get(key))
                if value:
                    filters[key] = value.lower() if key in ['status', 'priority', 'track'] else value
            recipients = SimpleHackathonRegistration.get_all(limit=1000, filters=filters if filters else None)
        else:
            return jsonify({"error": "No recipients specified"}), 400

        if not recipients:
            return jsonify({"error": "No matching hackathon participants found"}), 404

        sent_count = 0
        failed_count = 0
        failed_details = []

        for recipient in recipients:
            try:
                success, error_message = send_smtp_email(
                    to_email=recipient.email,
                    subject=subject,
                    body=message
                )

                email_log = EmailLog(
                    registration_id=recipient.id,
                    recipient_email=recipient.email,
                    subject=subject,
                    body=message,
                    sent_by=actor,
                    status='sent' if success else 'failed',
                    error_message=None if success else error_message
                )
                email_log.save()

                if success:
                    recipient.last_contact_at = datetime.utcnow()
                    recipient.add_history_entry(
                        'email_sent',
                        actor=actor,
                        note=f'Email sent: {subject}'
                    )
                    recipient.save()
                    sent_count += 1
                else:
                    failed_count += 1
                    failed_details.append(f"{recipient.email}: {error_message}")
            except Exception as recipient_error:
                failed_count += 1
                failed_details.append(f"{recipient.email}: {str(recipient_error)}")

        return jsonify({
            "success": True,
            "message": "Hackathon email dispatch completed",
            "sent": sent_count,
            "failed": failed_count,
            "total": sent_count + failed_count,
            "failed_details": failed_details if failed_details else None
        }), 200

    except Exception as e:
        print(f"❌ Error sending hackathon emails: {e}")
        return jsonify({
            "error": "Failed to send hackathon emails",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations/<email>', methods=['DELETE'])
@require_admin_auth
def delete_simple_registration(email):
    """
    DELETE /api/hackathon/simple-registrations/<email>
    
    Delete a simple hackathon registration (admin only)
    """
    try:
        registration = SimpleHackathonRegistration.get_by_email(email)
        
        if not registration:
            return jsonify({
                "error": "Registration not found"
            }), 404
        
        SimpleHackathonRegistration.delete(email)
        
        return jsonify({
            "message": "Registration deleted successfully"
        }), 200
        
    except Exception as e:
        print(f"❌ Error deleting registration: {e}")
        return jsonify({
            "error": "Failed to delete registration",
            "details": str(e)
        }), 500


@hackathon_bp.route('/api/hackathon/simple-registrations-stats', methods=['GET'])
@require_admin_auth
def get_simple_registrations_stats():
    """
    GET /api/hackathon/simple-registrations-stats
    
    Get statistics on simple hackathon registrations
    """
    try:
        total = SimpleHackathonRegistration.count()
        
        # Get counts by track
        by_track = {
            'healthcare': SimpleHackathonRegistration.count({'track': 'healthcare'}),
            'edtech': SimpleHackathonRegistration.count({'track': 'edtech'}),
            'smart_city': SimpleHackathonRegistration.count({'track': 'smart_city'})
        }
        
        # Get counts by status
        by_status = {
            status: SimpleHackathonRegistration.count({'status': status})
            for status in SIMPLE_HACKATHON_STATUSES
        }

        by_priority = {
            priority: SimpleHackathonRegistration.count({'priority': priority})
            for priority in SIMPLE_HACKATHON_PRIORITIES
        }
        
        return jsonify({
            "total_registrations": total,
            "by_track": by_track,
            "by_status": by_status,
            "by_priority": by_priority,
            "open_tickets": total - by_status.get('approved', 0) - by_status.get('rejected', 0) - by_status.get('closed', 0)
        }), 200
        
    except Exception as e:
        print(f"❌ Error fetching simple registration stats: {e}")
        return jsonify({
            "error": "Failed to fetch statistics",
            "details": str(e)
        }), 500
