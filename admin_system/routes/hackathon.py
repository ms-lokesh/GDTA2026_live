"""
Hackathon Registration Route - API endpoints for GDTA Challenge 2026
Handles hackathon participant registration and management
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from db.firebase_models import HackathonRegistration
from google.cloud.firestore import SERVER_TIMESTAMP

hackathon_bp = Blueprint('hackathon', __name__)


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
