"""
Registration Route - API endpoints for registration management
This route handles registration state and submissions
"""

from flask import Blueprint, request, jsonify, session as flask_session
import json
import pickle
import base64
import os
import urllib.request
import urllib.parse
import urllib.error
import threading
import time
import re

from logic.registration import (
    start_registration,
    get_current_question,
    process_input,
    get_summary,
    cancel_registration,
    RegistrationState,
    RegistrationSteps,
    FEE_CONFIG
)

register_bp = Blueprint('register', __name__)


# In-memory storage for registration sessions
# In production, use database
registration_sessions = {}

# Payment endpoint runtime guards
payment_rate_limit_store = {}
PAYMENT_RATE_LIMIT_WINDOW_SECONDS = 60
PAYMENT_RATE_LIMIT_MAX_REQUESTS = 20

# Zoho token cache/lock for safe refresh across concurrent requests
zoho_token_cache = {
    'token': None,
    'expires_at': 0
}
zoho_token_lock = threading.Lock()


class ZohoAPIError(Exception):
    def __init__(self, message, status_code=502, error_code='ZOHO_API_ERROR'):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def serialize_state(state):
    """Serialize state object to store in session"""
    return base64.b64encode(pickle.dumps(state)).decode('utf-8')


def deserialize_state(state_str):
    """Deserialize state object from session"""
    return pickle.loads(base64.b64decode(state_str.encode('utf-8')))


def get_or_create_session_id():
    """
    Get or create a session ID for the user
    """
    if 'reg_session_id' not in flask_session:
        import uuid
        flask_session['reg_session_id'] = str(uuid.uuid4())
        flask_session.modified = True
    return flask_session['reg_session_id']


def _get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def _enforce_payment_rate_limit(endpoint_key):
    now = int(time.time())
    window_start = now - PAYMENT_RATE_LIMIT_WINDOW_SECONDS
    ip = _get_client_ip()
    bucket_key = f"{endpoint_key}:{ip}"

    hits = payment_rate_limit_store.get(bucket_key, [])
    hits = [t for t in hits if t >= window_start]

    if len(hits) >= PAYMENT_RATE_LIMIT_MAX_REQUESTS:
        return False

    hits.append(now)
    payment_rate_limit_store[bucket_key] = hits
    return True


def _accounts_base_domain():
    data_center = (os.environ.get('ZOHO_BOOKS_DATA_CENTER') or 'in').strip().lower()
    return f"accounts.zoho.{data_center}"


def _refresh_zoho_access_token(force=False):
    now = int(time.time())

    with zoho_token_lock:
        cached_token = zoho_token_cache.get('token')
        expires_at = int(zoho_token_cache.get('expires_at') or 0)
        if (not force) and cached_token and now < (expires_at - 30):
            return cached_token

        client_id = (os.environ.get('ZOHO_BOOKS_CLIENT_ID') or '').strip()
        client_secret = (os.environ.get('ZOHO_BOOKS_CLIENT_SECRET') or '').strip()
        refresh_token = (os.environ.get('ZOHO_BOOKS_REFRESH_TOKEN') or '').strip()

        # Backward-compatible fallback to static token, but refresh flow is preferred.
        fallback_access_token = (os.environ.get('ZOHO_BOOKS_ACCESS_TOKEN') or '').strip()

        if not client_id or not client_secret or not refresh_token:
            if fallback_access_token:
                zoho_token_cache['token'] = fallback_access_token
                zoho_token_cache['expires_at'] = now + 300
                return fallback_access_token
            raise ZohoAPIError(
                "Zoho Books auth not configured.",
                status_code=400,
                error_code='ZOHO_AUTH_NOT_CONFIGURED'
            )

        token_url = f"https://{_accounts_base_domain()}/oauth/v2/token"
        payload = urllib.parse.urlencode({
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token'
        }).encode('utf-8')

        req = urllib.request.Request(
            url=token_url,
            data=payload,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                token_data = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError:
            raise ZohoAPIError(
                "Unable to refresh Zoho access token.",
                status_code=502,
                error_code='ZOHO_TOKEN_REFRESH_FAILED'
            )
        except Exception:
            raise ZohoAPIError(
                "Unable to refresh Zoho access token.",
                status_code=502,
                error_code='ZOHO_TOKEN_REFRESH_FAILED'
            )

        access_token = (token_data.get('access_token') or '').strip()
        expires_in = int(token_data.get('expires_in', 3600))
        if not access_token:
            raise ZohoAPIError(
                "Zoho token refresh response missing access token.",
                status_code=502,
                error_code='ZOHO_TOKEN_INVALID_RESPONSE'
            )

        zoho_token_cache['token'] = access_token
        zoho_token_cache['expires_at'] = now + max(120, (expires_in - 60))
        return access_token


def _zoho_books_base_url():
    data_center = (os.environ.get('ZOHO_BOOKS_DATA_CENTER') or 'in').strip().lower()
    return f"https://www.zohoapis.{data_center}/books/v3"


def _zoho_books_headers():
    access_token = _refresh_zoho_access_token()
    return {
        'Authorization': f'Zoho-oauthtoken {access_token}',
        'Content-Type': 'application/json'
    }


def _zoho_books_request(method, path, org_id, payload=None, retry_on_unauthorized=True):
    query = urllib.parse.urlencode({'organization_id': org_id})
    url = f"{_zoho_books_base_url()}{path}?{query}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        url=url,
        data=data,
        method=method,
        headers=_zoho_books_headers()
    )

    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read().decode('utf-8')
            return json.loads(body)
    except urllib.error.HTTPError as http_err:
        if http_err.code == 401 and retry_on_unauthorized:
            _refresh_zoho_access_token(force=True)
            return _zoho_books_request(method, path, org_id, payload=payload, retry_on_unauthorized=False)

        raise ZohoAPIError(
            "Zoho Books API request failed.",
            status_code=502,
            error_code='ZOHO_API_HTTP_ERROR'
        )
    except ZohoAPIError:
        raise
    except Exception:
        raise ZohoAPIError(
            "Zoho Books API request failed.",
            status_code=502,
            error_code='ZOHO_API_REQUEST_FAILED'
        )


def _extract_payment_url(invoice_payload):
    if not invoice_payload:
        return None

    candidates = [
        invoice_payload.get('payment_link'),
        invoice_payload.get('payment_url'),
        invoice_payload.get('invoice_url'),
        invoice_payload.get('customer_view_url'),
        invoice_payload.get('url')
    ]

    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip().startswith('http'):
            return candidate.strip()

    return None


def _is_valid_email(email):
    return bool(re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email or ''))


def _is_valid_invoice_id(invoice_id):
    return bool(re.match(r'^[A-Za-z0-9_-]{6,80}$', invoice_id or ''))


def _parse_yes_no(value):
    return str(value or '').strip().lower() in ['yes', 'true', '1', 'y']


def _expected_fee_from_payload(data):
    category = (data.get('registration_category') or '').strip()
    if category not in FEE_CONFIG:
        return None

    cfg = FEE_CONFIG[category]
    addon_food = _parse_yes_no(data.get('addon_food_accommodation'))
    addon_safari = _parse_yes_no(data.get('addon_safari'))

    if cfg['fixed']:
        total = cfg['base']
    else:
        total = cfg['base']
        total += cfg['food'] if addon_food else 0
        total += cfg['safari'] if addon_safari else 0

    return {
        'category': category,
        'currency': cfg['currency'],
        'total': float(total)
    }


def _get_registration_for_payment(email=None, registration_id=None):
    from db.firebase_models import Registration

    registration = None
    if registration_id:
        registration = Registration.get_by_id(registration_id)
    if (not registration) and email:
        registration = Registration.get_by_email(email)
    return registration


@register_bp.route('/api/register/start', methods=['POST'])
def start_registration_session():
    """
    POST /api/register/start
    
    Starts a new registration session
    
    Optional Body:
    {
        "session_id": "optional - provide existing or let server generate"
    }
    
    Returns:
        {
            "message": "...",
            "question": {...},
            "session_id": "...",
            "state": {...}
        }
    """
    try:
        import uuid
        
        # Accept session_id from request body or generate new one
        data = request.get_json() or {}
        session_id = data.get('session_id') or str(uuid.uuid4())
        
        print(f"[DEBUG] Starting registration with session_id: {session_id}")
        
        # Initialize registration state
        reg_state = start_registration()
        
        # Store in both memory and Flask session for redundancy
        registration_sessions[session_id] = reg_state
        flask_session['reg_state'] = serialize_state(reg_state)
        flask_session['reg_session_id'] = session_id
        flask_session.modified = True
        
        print(f"[DEBUG] Registration session created. Active sessions: {list(registration_sessions.keys())}")
        print(f"[DEBUG] Flask session ID: {flask_session.get('reg_session_id')}")
        print(f"[DEBUG] Registration sessions dict id: {id(registration_sessions)}")
        
        # Get first question
        question = get_current_question(reg_state)
        
        return jsonify({
            "message": "Registration started. Please answer the following questions.",
            "question": question,
            "session_id": session_id,
            "state": reg_state.to_dict()
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to start registration: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Failed to start registration",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/answer', methods=['POST'])
def submit_answer():
    """
    POST /api/register/answer
    
    Body:
    {
        "answer": "user's answer",
        "session_id": "optional session id"
    }
    
    Returns:
        {
            "success": bool,
            "message": "...",
            "next_question": {...} or null,
            "completed": bool,
            "summary": "..." (if at confirmation step)
        }
    """
    try:
        data = request.get_json()
        
        print(f"[DEBUG] Received data: {data}")
        print(f"[DEBUG] Request headers: {dict(request.headers)}")
        
        if not data or 'answer' not in data:
            print(f"[ERROR] Missing answer field. Data received: {data}")
            return jsonify({"error": "Answer field required", "received": data}), 400
        
        # Use session_id from request body if provided, otherwise use Flask session
        session_id = data.get('session_id') or flask_session.get('reg_session_id')
        user_answer = data['answer']
        
        print(f"[DEBUG] Session ID from request: {data.get('session_id')}")
        print(f"[DEBUG] Session ID from Flask session: {flask_session.get('reg_session_id')}")
        print(f"[DEBUG] Using session ID: {session_id}")
        print(f"[DEBUG] Active sessions in memory: {list(registration_sessions.keys())}")
        print(f"[DEBUG] Registration sessions dict id: {id(registration_sessions)}")
        print(f"[DEBUG] Flask session has reg_state: {'reg_state' in flask_session}")
        
        # Try to get registration state from memory first, then Flask session
        reg_state = None
        
        if session_id and session_id in registration_sessions:
            print(f"[DEBUG] Found session in memory")
            reg_state = registration_sessions[session_id]
        elif 'reg_state' in flask_session:
            print(f"[DEBUG] Found session in Flask session, deserializing...")
            try:
                reg_state = deserialize_state(flask_session['reg_state'])
                # Restore to memory
                if session_id:
                    registration_sessions[session_id] = reg_state
                print(f"[DEBUG] Successfully restored from Flask session")
            except Exception as e:
                print(f"[ERROR] Failed to deserialize state: {e}")
        
        if not reg_state:
            print(f"[ERROR] Session {session_id} not found in memory or Flask session")
            return jsonify({
                "error": "No active registration session. Please start registration first.",
                "action": "start_registration"
            }), 400
        
        if not reg_state.is_active:
            return jsonify({
                "error": "Registration session has ended.",
                "action": "start_registration"
            }), 400
        
        # Process the answer
        result = process_input(reg_state, user_answer)
        
        # Update stored state in both places
        if session_id:
            registration_sessions[session_id] = reg_state
        flask_session['reg_state'] = serialize_state(reg_state)
        flask_session.modified = True
        
        # If at confirmation step, include summary
        if reg_state.current_step == RegistrationSteps.CONFIRMATION:
            result['summary'] = get_summary(reg_state)
        
        # If completed, clean up session
        if result.get('completed'):
            # Save to database
            completed_data = reg_state.data.copy()
            completed_data['session_id'] = session_id  # Add session_id for tracking
            print(f"Registration completed for session {session_id}: {completed_data}")
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to process answer",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/cancel', methods=['POST'])
def cancel_registration_session():
    """
    POST /api/register/cancel
    
    Cancels the current registration session
    
    Optional Body:
    {
        "session_id": "optional - provide existing or use Flask session"
    }
    """
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id') or get_or_create_session_id()
        
        if session_id in registration_sessions:
            reg_state = registration_sessions[session_id]
            result = cancel_registration(reg_state)
            
            # Clean up
            del registration_sessions[session_id]
            
            return jsonify(result), 200
        else:
            return jsonify({
                "message": "No active registration to cancel."
            }), 200
            
    except Exception as e:
        return jsonify({
            "error": "Failed to cancel registration",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/status', methods=['GET'])
def get_registration_status():
    """
    GET /api/register/status?session_id=xxx
    
    Gets the current registration status
    """
    try:
        # Accept session_id from query parameter or use Flask session
        session_id = request.args.get('session_id') or get_or_create_session_id()
        
        if session_id not in registration_sessions:
            return jsonify({
                "active": False,
                "message": "No active registration session."
            }), 200
        
        reg_state = registration_sessions[session_id]
        
        if not reg_state.is_active:
            return jsonify({
                "active": False,
                "message": "Registration session has ended."
            }), 200
        
        question = get_current_question(reg_state)
        summary = None
        
        if reg_state.current_step == RegistrationSteps.CONFIRMATION:
            summary = get_summary(reg_state)
        
        return jsonify({
            "active": True,
            "current_question": question,
            "summary": summary,
            "state": reg_state.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            "error": "Failed to get registration status",
            "details": str(e)
        }), 500


@register_bp.route('/api/register/submit-form', methods=['POST'])
def submit_form_registration():
    """
    POST /api/register/submit-form
    
    Direct form-based registration submission
    Accepts all registration data at once and submits to the same backend as chatbot
    
    Body:
    {
        "name": "...",
        "email": "...",
        "institution": "...",
        "role": "...",
        "gdta_member": "Yes/No",
        "gdta_affiliation": "...",
        "country": "...",
        "state": "...",
        "consent": "Yes"
    }
    
    Returns:
        {
            "success": true/false,
            "message": "...",
            "registration_id": "..." (if successful)
        }
    """
    try:
        from logic.registration import submit_registration
        
        # Get form data from request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "No data provided"
            }), 400
        
        # Prepare registration data with form source
        registration_data = {
            "title": data.get("title", "").strip(),
            "name": data.get("name", "").strip(),
            "gender": data.get("gender", "").strip(),
            "email": data.get("email", "").strip(),
            "institution": data.get("institution", "").strip(),
            "role": data.get("role", "").strip(),
            "gdta_member": data.get("gdta_member", "").strip(),
            "gdta_affiliation": data.get("gdta_affiliation", "").strip(),
            "country": data.get("country", "").strip(),
            "state": data.get("state", "").strip(),
            "consent": data.get("consent", "").strip(),
            "registration_category": data.get("registration_category", "").strip(),
            "addon_food_accommodation": data.get("addon_food_accommodation", "No"),
            "addon_safari": data.get("addon_safari", "No"),
            "safari_route": data.get("safari_route", "").strip(),
            "fee_currency": data.get("fee_currency"),
            "base_fee": data.get("base_fee"),
            "addon_food_accommodation_fee": data.get("addon_food_accommodation_fee"),
            "addon_safari_fee": data.get("addon_safari_fee"),
            "total_fee": data.get("total_fee"),
            "registration_source": "form"  # Mark as form registration
        }
        
        # Submit registration using the same backend logic
        result = submit_registration(registration_data)
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"Form registration error: {e}")
        return jsonify({
            "success": False,
            "message": "An error occurred during registration. Please try again.",
            "error": str(e)
        }), 500


@register_bp.route('/api/register/payment/zoho-books/create-link', methods=['POST'])
def create_zoho_books_payment_link():
    """
    Creates a Zoho Books invoice/payment link for a completed registration.
    """
    try:
        if not _enforce_payment_rate_limit('zoho_create_link'):
            return jsonify({
                "success": False,
                "message": "Too many payment attempts. Please wait a minute and try again."
            }), 429

        data = request.get_json() or {}
        org_id = (os.environ.get('ZOHO_BOOKS_ORGANIZATION_ID') or '').strip()

        if not org_id:
            return jsonify({
                "success": False,
                "message": "Zoho Books is not configured. Set ZOHO_BOOKS_ORGANIZATION_ID in .env"
            }), 400

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        registration_category = (data.get('registration_category') or '').strip()
        registration_id = (data.get('registration_id') or '').strip()

        expected_fee = _expected_fee_from_payload(data)
        if not expected_fee:
            return jsonify({
                "success": False,
                "message": "Invalid registration category for payment."
            }), 400

        if not name or len(name) > 120 or not _is_valid_email(email):
            return jsonify({
                "success": False,
                "message": "Invalid payer details."
            }), 400

        try:
            client_total = float(data.get('total_fee'))
        except (TypeError, ValueError):
            client_total = None

        amount = expected_fee['total']
        currency = expected_fee['currency']

        if amount <= 0 or amount > 1000000:
            return jsonify({
                "success": False,
                "message": "Invalid payment amount."
            }), 400

        if client_total is not None and abs(client_total - amount) > 0.01:
            return jsonify({
                "success": False,
                "message": "Payment amount mismatch. Please refresh and try again."
            }), 400

        contact_payload = {
            "contact_name": name,
            "email": email
        }
        contact_resp = _zoho_books_request('POST', '/contacts', org_id, payload=contact_payload)
        if contact_resp.get('code') not in [0, '0']:
            return jsonify({
                "success": False,
                "message": "Failed to create Zoho customer contact."
            }), 502

        contact = contact_resp.get('contact') or {}
        contact_id = contact.get('contact_id')
        if not contact_id:
            return jsonify({
                "success": False,
                "message": "Zoho contact creation did not return contact ID."
            }), 502

        invoice_payload = {
            "customer_id": contact_id,
            "currency_code": currency,
            "reference_number": registration_id or None,
            "line_items": [
                {
                    "name": f"GDTA 2026 - {registration_category}",
                    "description": f"GDTA 2026 conference registration fee ({registration_category})",
                    "quantity": 1,
                    "rate": amount
                }
            ]
        }

        invoice_resp = _zoho_books_request('POST', '/invoices', org_id, payload=invoice_payload)
        if invoice_resp.get('code') not in [0, '0']:
            return jsonify({
                "success": False,
                "message": "Failed to create Zoho invoice."
            }), 502

        invoice = invoice_resp.get('invoice') or {}
        invoice_id = invoice.get('invoice_id')
        payment_url = _extract_payment_url(invoice)

        if (not payment_url) and invoice_id:
            payment_template = (os.environ.get('ZOHO_BOOKS_PAYMENT_LINK_TEMPLATE') or '').strip()
            if payment_template and '{invoice_id}' in payment_template:
                payment_url = payment_template.replace('{invoice_id}', str(invoice_id))

        if not payment_url:
            return jsonify({
                "success": False,
                "message": "Invoice created, but no direct payment URL was returned. Configure ZOHO_BOOKS_PAYMENT_LINK_TEMPLATE in .env.",
                "invoice_id": invoice_id
            }), 502

        registration = _get_registration_for_payment(email=email, registration_id=registration_id)
        if registration:
            registration.payment_status = 'payment_link_created'
            registration.payment_provider = 'zoho_books'
            registration.payment_invoice_id = invoice_id
            registration.payment_link = payment_url
            registration.payment_amount = amount
            registration.payment_currency = currency
            registration.payment_method = (data.get('payment_method') or '').strip() or None
            registration.save()

        return jsonify({
            "success": True,
            "provider": "zoho_books",
            "invoice_id": invoice_id,
            "payment_url": payment_url,
            "currency": currency,
            "amount": amount,
            "message": "Zoho Books payment link created successfully."
        }), 200

    except ZohoAPIError as e:
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": e.error_code
        }), e.status_code
    except Exception as e:
        print(f"Zoho create-link error: {e}")
        return jsonify({
            "success": False,
            "message": "Failed to create Zoho Books payment link.",
            "error_code": "ZOHO_CREATE_LINK_FAILED"
        }), 500


@register_bp.route('/api/register/payment/zoho-books/status', methods=['GET'])
def get_zoho_books_payment_status():
    """
    Checks invoice payment status from Zoho Books.
    """
    try:
        if not _enforce_payment_rate_limit('zoho_payment_status'):
            return jsonify({
                "success": False,
                "message": "Too many status checks. Please wait a minute and try again."
            }), 429

        org_id = (os.environ.get('ZOHO_BOOKS_ORGANIZATION_ID') or '').strip()
        invoice_id = (request.args.get('invoice_id') or '').strip()

        if not org_id:
            return jsonify({
                "success": False,
                "message": "Zoho Books is not configured."
            }), 400

        if not invoice_id or not _is_valid_invoice_id(invoice_id):
            return jsonify({
                "success": False,
                "message": "Valid invoice_id is required."
            }), 400

        status_resp = _zoho_books_request('GET', f'/invoices/{invoice_id}', org_id)
        if status_resp.get('code') not in [0, '0']:
            return jsonify({
                "success": False,
                "message": "Failed to fetch invoice status from Zoho Books."
            }), 502

        invoice = status_resp.get('invoice') or {}
        invoice_status = (invoice.get('status') or '').lower()
        try:
            balance = float(invoice.get('balance') if invoice.get('balance') is not None else 0)
        except (TypeError, ValueError):
            balance = 0

        paid = invoice_status == 'paid' or balance <= 0

        if paid:
            from datetime import datetime

            registration = _get_registration_for_payment(registration_id=invoice.get('reference_number'))
            if (not registration) and invoice.get('customer_email'):
                registration = _get_registration_for_payment(email=invoice.get('customer_email'))

            if registration:
                registration.payment_status = 'paid'
                registration.payment_provider = 'zoho_books'
                registration.payment_invoice_id = invoice_id
                registration.payment_amount = float(invoice.get('total') or registration.payment_amount or 0)
                registration.payment_currency = invoice.get('currency_code') or registration.payment_currency
                registration.payment_paid_at = datetime.utcnow()
                registration.save()
        else:
            registration = _get_registration_for_payment(registration_id=invoice.get('reference_number'))
            if registration and str(getattr(registration, 'payment_status', '')).lower() != 'paid':
                registration.payment_status = 'payment_pending'
                registration.payment_provider = 'zoho_books'
                registration.payment_invoice_id = invoice_id
                registration.save()

        return jsonify({
            "success": True,
            "provider": "zoho_books",
            "invoice_id": invoice_id,
            "status": invoice_status or 'unknown',
            "balance": balance,
            "paid": paid,
            "raw_status": invoice.get('status')
        }), 200

    except ZohoAPIError as e:
        return jsonify({
            "success": False,
            "message": e.message,
            "error_code": e.error_code
        }), e.status_code
    except Exception as e:
        print(f"Zoho status error: {e}")
        return jsonify({
            "success": False,
            "message": "Failed to check Zoho Books payment status.",
            "error_code": "ZOHO_STATUS_FAILED"
        }), 500
