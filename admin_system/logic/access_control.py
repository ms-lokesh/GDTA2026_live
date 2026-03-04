"""
Access Control Logic for GDTA 2026
Handles QR code validation and access permission checks
"""

from datetime import datetime
from db.firebase_models import Registration, Venue, AccessLog


class AccessController:
    """Handles access control and validation"""
    
    @staticmethod
    def validate_qr_access(qr_code, venue_id, scanned_by):
        """
        Validate QR code and check if participant can access venue
        
        Args:
            qr_code: QR code from ID card (unique_id or email for backward compatibility)
            venue_id: Venue ID being accessed
            scanned_by: Username of volunteer/admin scanning
        
        Returns:
            {
                'success': bool,
                'message': str,
                'participant': dict or None,
                'venue': dict or None,
                'access_log_id': str or None
            }
        """
        result = {
            'success': False,
            'message': '',
            'participant': None,
            'venue': None,
            'access_log_id': None
        }
        
        # Try to get registration by unique_id first, then by email (backward compatibility)
        registration = Registration.get_by_unique_id(qr_code)
        if not registration:
            registration = Registration.get_by_email(qr_code)
        
        if not registration:
            result['message'] = '❌ QR Code Invalid - Participant not found'
            AccessController._log_access('denied', None, venue_id, scanned_by, 'Invalid QR code')
            return result
        
        # Check if registration is approved
        if registration.status != 'approved':
            result['message'] = f'❌ Access Denied - Registration status: {registration.status.upper()}'
            result['participant'] = {
                'name': registration.name,
                'email': registration.email,
                'unique_id': registration.unique_id,
                'status': registration.status
            }
            AccessController._log_access('denied', registration, venue_id, scanned_by, 
                                        f'Registration not approved: {registration.status}')
            return result
        
        # Get venue details
        venue = Venue.get_by_id(venue_id)
        if not venue:
            result['message'] = '❌ Venue not found'
            result['participant'] = {
                'name': registration.name,
                'email': registration.email,
                'unique_id': registration.unique_id,
                'status': registration.status
            }
            return result
        
        # Check if venue is active
        if not venue.is_active:
            result['message'] = f'❌ {venue.name} is currently closed'
            result['participant'] = {
                'name': registration.name,
                'email': registration.email,
                'unique_id': registration.unique_id,
                'institution': registration.institution,
                'role': registration.role
            }
            result['venue'] = {
                'name': venue.name,
                'is_active': venue.is_active
            }
            AccessController._log_access('denied', registration, venue_id, scanned_by, 
                                        'Venue not active')
            return result
        
        # Check access limit (scan count restrictions)
        access_limit = getattr(venue, 'access_limit', 'unlimited')
        if access_limit != 'unlimited':
            # Count previous successful check-ins for this participant at this venue
            previous_checkins = AccessLog.get_all(filters={
                'registration_id': registration.id,
                'venue_id': venue_id,
                'action_type': 'check-in'
            })
            
            checkin_count = len(previous_checkins)
            
            if access_limit == 'once' and checkin_count > 0:
                result['message'] = f'❌ Access Denied - Already scanned at {venue.name} (allowed once only)'
                result['participant'] = {
                    'name': registration.name,
                    'email': registration.email,
                    'unique_id': registration.unique_id,
                    'institution': registration.institution,
                    'role': registration.role
                }
                result['venue'] = {
                    'name': venue.name,
                    'access_limit': access_limit,
                    'previous_scans': checkin_count
                }
                AccessController._log_access('denied', registration, venue_id, scanned_by, 
                                            f'Access limit exceeded: already scanned {checkin_count} time(s), limit is once')
                return result
            elif access_limit.isdigit():
                limit_number = int(access_limit)
                if checkin_count >= limit_number:
                    result['message'] = f'❌ Access Denied - Scan limit reached at {venue.name} ({checkin_count}/{limit_number})'
                    result['participant'] = {
                        'name': registration.name,
                        'email': registration.email,
                        'unique_id': registration.unique_id,
                        'institution': registration.institution,
                        'role': registration.role
                    }
                    result['venue'] = {
                        'name': venue.name,
                        'access_limit': access_limit,
                        'previous_scans': checkin_count
                    }
                    AccessController._log_access('denied', registration, venue_id, scanned_by, 
                                                f'Access limit exceeded: scanned {checkin_count} time(s), limit is {limit_number}')
                    return result
        
        # All checks passed - grant access
        log_id = AccessController._log_access('check-in', registration, venue_id, scanned_by)
        
        result['success'] = True
        result['message'] = f'✅ Access Granted to {venue.name}'
        result['participant'] = {
            'name': registration.name,
            'email': registration.email,
            'unique_id': registration.unique_id,
            'institution': registration.institution,
            'role': registration.role,
            'country': registration.country
        }
        result['venue'] = {
            'id': venue.id,
            'name': venue.name,
            'type': venue.venue_type,
            'location': venue.location
        }
        result['access_log_id'] = log_id
        
        return result
    
    @staticmethod
    def _log_access(action_type, registration, venue_id, scanned_by, notes=None):
        """
        Log access attempt
        
        Args:
            action_type: 'check-in', 'check-out', or 'denied'
            registration: Registration object or None
            venue_id: Venue ID
            scanned_by: Username of scanner
            notes: Optional notes
        
        Returns:
            Access log ID
        """
        venue = Venue.get_by_id(venue_id) if venue_id else None
        
        access_log = AccessLog(
            registration_id=registration.id if registration else None,
            registration_email=registration.email if registration else None,
            participant_name=registration.name if registration else 'Unknown',
            venue_id=venue_id,
            venue_name=venue.name if venue else 'Unknown',
            action_type=action_type,
            scanned_by=scanned_by,
            timestamp=datetime.utcnow(),
            notes=notes,
            qr_code=registration.email if registration else None
        )
        
        return access_log.save()
    
    @staticmethod
    def get_participant_access_history(registration_email, limit=50):
        """Get access history for a participant"""
        registration = Registration.get_by_email(registration_email)
        if not registration:
            return []
        
        logs = AccessLog.get_by_registration(registration.id, limit)
        return [log.to_dict() for log in logs]
    
    @staticmethod
    def get_venue_access_stats(venue_id):
        """Get access statistics for a venue"""
        logs = AccessLog.get_by_venue(venue_id, limit=1000)
        
        total_access = len([log for log in logs if log.action_type == 'check-in'])
        total_denied = len([log for log in logs if log.action_type == 'denied'])
        
        # Get unique participants
        unique_participants = set(log.registration_id for log in logs 
                                 if log.registration_id and log.action_type == 'check-in')
        
        return {
            'total_check_ins': total_access,
            'total_denied': total_denied,
            'unique_participants': len(unique_participants),
            'recent_logs': [log.to_dict() for log in logs[:20]]
        }
    
    @staticmethod
    def check_duplicate_entry(registration_email, venue_id, minutes=5):
        """
        Check if participant recently checked into this venue
        
        Args:
            registration_email: Participant email
            venue_id: Venue ID
            minutes: Time window in minutes
        
        Returns:
            True if duplicate entry detected
        """
        from datetime import timedelta
        
        registration = Registration.get_by_email(registration_email)
        if not registration:
            return False
        
        logs = AccessLog.get_by_registration(registration.id, limit=10)
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        for log in logs:
            if (log.venue_id == venue_id and 
                log.action_type == 'check-in' and 
                log.timestamp > cutoff_time):
                return True
        
        return False
