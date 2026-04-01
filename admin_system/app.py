"""
GDTA 2026 Chatbot Backend - Main Application
Flask server with logic-controlled AI assistant

ARCHITECTURE PRINCIPLES:
1. Backend controls all decisions
2. AI used only for language understanding/generation
3. All scheduling logic is deterministic
4. JSON files are the single source of truth
"""

from flask import Flask, jsonify, send_from_directory, render_template, request
from flask_cors import CORS
import os
from urllib.parse import urlparse

# Import our route blueprints
from routes.chat import chat_bp
from routes.plan import plan_bp
from routes.register import register_bp
from routes.cleanup import cleanup_bp
from routes.admin import admin_bp
from routes.hackathon import hackathon_bp

# Import database initialization
from db.firebase_models import init_firebase, create_default_admin


def create_app():
    """Application factory pattern"""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False  # Preserve JSON order
    app.config['SESSION_TYPE'] = 'filesystem'  # For session support
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    app.config['ENABLE_SECURITY_HEADERS'] = os.environ.get('ENABLE_SECURITY_HEADERS', 'True').lower() == 'true'
    app.config['REQUIRE_ORIGIN_FOR_STATE_CHANGING'] = os.environ.get('REQUIRE_ORIGIN_FOR_STATE_CHANGING', 'True').lower() == 'true'
    
    # Enable CORS for frontend integration
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,http://127.0.0.1:5500,null')
    origins_list = [origin.strip() for origin in allowed_origins.split(',')]
    strict_origin_list = [origin for origin in origins_list if origin and origin.lower() != 'null']
    strict_origins = set(strict_origin_list)
    
    CORS(app, resources={
        r"/api/*": {
            "origins": origins_list,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True,
            "expose_headers": ["Set-Cookie"]
        }
    }, supports_credentials=True)

    @app.before_request
    def validate_state_changing_request_origin():
        """
        CSRF posture for cookie-authenticated admin routes:
        - For state-changing methods on /api/admin and /api/superadmin,
          require Origin (or Referer fallback) to match configured allowed origins.
        """
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return None

        if not (request.path.startswith('/api/admin') or request.path.startswith('/api/superadmin')):
            return None

        origin = (request.headers.get('Origin') or '').strip()
        referer = (request.headers.get('Referer') or '').strip()
        require_origin = app.config.get('REQUIRE_ORIGIN_FOR_STATE_CHANGING', True)

        if origin:
            if origin not in strict_origins:
                return jsonify({'success': False, 'message': 'Forbidden origin.'}), 403
            return None

        if referer:
            parsed = urlparse(referer)
            referer_origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ''
            if referer_origin and referer_origin in strict_origins:
                return None
            return jsonify({'success': False, 'message': 'Forbidden referer.'}), 403

        if require_origin:
            return jsonify({'success': False, 'message': 'Missing origin header.'}), 403
        return None

    @app.after_request
    def add_security_headers(response):
        if app.config.get('ENABLE_SECURITY_HEADERS', True):
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

            csp = (
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https: data:; "
                "style-src 'self' 'unsafe-inline' https:; "
                "script-src 'self' 'unsafe-inline' https:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
            response.headers['Content-Security-Policy'] = csp

            # HSTS should only be set over HTTPS
            if request.is_secure or request.headers.get('X-Forwarded-Proto', '').lower() == 'https':
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        return response
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(cleanup_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(hackathon_bp)
    
    # Initialize Firebase Firestore
    with app.app_context():
        try:
            init_firebase()
            create_default_admin()
            print("✓ Firebase initialized successfully")
        except Exception as e:
            print(f"⚠ Firebase initialization warning: {e}")
            print(f"   Make sure firebase-credentials.json exists or FIREBASE_CREDENTIALS env var is set")
    
    # Ensure generated_ids directory exists
    generated_ids_dir = os.path.join(os.path.dirname(__file__), 'static', 'generated_ids')
    os.makedirs(generated_ids_dir, exist_ok=True)
    print(f"✓ Generated IDs directory: {generated_ids_dir}")
    
    # Note: On Render free tier, filesystem is ephemeral
    if os.environ.get('RENDER'):
        print("⚠ WARNING: Running on Render - generated ID cards will be lost on restart")
        print("   Consider using Firebase Storage or regenerating on-demand")
    
    # API information endpoint
    @app.route('/api')
    def api_info():
        return jsonify({
            'service': 'GDTA 2026 Chatbot Backend',
            'status': 'running',
            'version': '2.0.0',
            'endpoints': {
                'chat': '/api/chat',
                'plan': '/api/plan',
                'sessions': '/api/sessions',
                'alternatives': '/api/alternatives/<session_id>',
                'validate': '/api/validate',
                'registration': {
                    'start': '/api/register/start',
                    'answer': '/api/register/answer',
                    'cancel': '/api/register/cancel',
                    'status': '/api/register/status',
                    'ui': '/register'
                },
                'admin': {
                    'dashboard': '/admin',
                    'login': '/api/admin/login',
                    'registrations': '/api/admin/registrations',
                    'stats': '/api/admin/stats',
                    'export': '/api/admin/export'
                }
            },
            'architecture': 'Logic-controlled AI assistant with admin management'
        })
    
    # Serve admin system's static files (including generated ID cards)
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files from admin_system/static directory"""
        import os
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        print(f"Serving static file: {filename} from {static_dir}")
        return send_from_directory(static_dir, filename)
    
    # Dedicated route for generated ID cards with better error handling
    @app.route('/static/generated_ids/<filename>')
    def serve_id_card(filename):
        """Serve generated ID card images, regenerate if missing"""
        import os
        generated_ids_dir = os.path.join(os.path.dirname(__file__), 'static', 'generated_ids')
        file_path = os.path.join(generated_ids_dir, filename)
        
        print(f"ID Card request: {filename}")
        print(f"Looking in: {generated_ids_dir}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if os.path.exists(file_path):
            return send_from_directory(generated_ids_dir, filename)
        else:
            # Try to regenerate if it's a valid ID card filename
            if filename.startswith('id_card_') and filename.endswith('.png'):
                try:
                    # Extract unique_id from filename
                    # Format: id_card_<unique_id>.png where unique_id has @ as _at_ and . as _
                    unique_id = filename.replace('id_card_', '').replace('.png', '')
                    # Note: We can't reliably reverse the transformation, so log warning
                    print(f"⚠ ID card file missing: {filename}")
                    print(f"   Note: Auto-regeneration from static URL not fully supported yet")
                    print(f"   Use /api/admin/id-card/view/<unique_id> endpoint instead")
                except Exception as e:
                    print(f"Failed to parse unique_id from filename: {e}")
            
            return jsonify({
                'error': 'ID card not found',
                'message': f'The ID card "{filename}" does not exist or has not been generated yet.',
                'note': 'Generated ID cards are stored temporarily on Render. Use the regenerate button or the /api/admin/id-card/view/<unique_id> endpoint.'
            }), 404
    
    # Serve chatbot UI at /chatbot (was previously at root)
    @app.route('/chatbot')
    def chatbot_route():
        import os
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'index.html')
    
    # Serve admin dashboard
    @app.route('/admin')
    def admin_route():
        import os
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'admin-dashboard.html')
    
    # Serve admin system registration UI at /register (different from main site register.html)
    @app.route('/register')
    def registration_ui():
        import os
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'registration.html')
    
    # Serve main website at root
    @app.route('/')
    @app.route('/index')
    def index():
        """Serve the main website's index.html from the templates directory"""
        return render_template('index.html')

    # Catch-all route for other HTML files
    @app.route('/<string:page_name>.html')
    def render_page(page_name):
        """Render a page from the templates directory"""
        return render_template(f'{page_name}.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'Available endpoints: /api, /chatbot, /admin, /register, or any main website file'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'Something went wrong on the server'
        }), 500
    
    return app


# Create app instance for gunicorn
app = create_app()


if __name__ == '__main__':
    """
    Development server
    
    Run with: python app.py
    
    The server will start on http://localhost:5000
    """
    
    # Development settings
    debug_mode = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("GDTA ADMIN SYSTEM")
    print("=" * 60)
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Server starting on http://0.0.0.0:{port}")
    print()
    print("Available endpoints:")
    print("  GET  /                      - API info")
    print("  GET  /static/admin-dashboard.html - Admin Dashboard")
    print("  POST /api/admin/login       - Admin login")
    print("  POST /api/register          - Registration")
    print("  POST /api/chat              - Chatbot")
    print("  POST /api/plan              - Schedule planner")
    print()
    print("Features: Multi-event | Super Admin | AI Chatbot")
    print("Database: Firebase Firestore")
    print("=" * 60)
    print()
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=False  # Disable auto-reload to avoid double initialization
    )
