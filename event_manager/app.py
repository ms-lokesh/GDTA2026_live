"""
Event Manager - Standalone Event Management System
Flask-based multi-event management platform with admin dashboard

Features:
- Multi-event management with super admin
- Registration system with approval workflow
- Check-in system with QR code scanning
- Email template management
- ID card generation
- Volunteer dashboard
- Bulk operations & advanced filtering

Architecture:
- Config-driven (YAML + environment variables)
- Database-backed (Firebase Firestore)
- Role-based access control (Super Admin, Admin, Volunteer)
- RESTful API with Blueprint structure
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os
import yaml
from pathlib import Path

# Import blueprints
from routes.admin import admin_bp
from routes.register import register_bp
from routes.plan import plan_bp
from routes.hackathon import hackathon_bp
from routes.cleanup import cleanup_bp

# Import database initialization
from db.firebase_models import init_firebase, create_default_admin


def load_config():
    """Load configuration from YAML file and environment variables"""
    config = {}
    
    # Load from config.yaml (or config.example.yaml as fallback)
    config_path = Path(__file__).parent / 'config.yaml'
    example_config_path = Path(__file__).parent / 'config.example.yaml'
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("✓ Loaded config from config.yaml")
    elif example_config_path.exists():
        with open(example_config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("⚠ Using config.example.yaml (copy to config.yaml for customization)")
    else:
        print("⚠ No config file found, using defaults")
        config = get_default_config()
    
    # Environment variables override config file
    if os.environ.get('SECRET_KEY'):
        config.setdefault('app', {})['secret_key'] = os.environ.get('SECRET_KEY')
    
    if os.environ.get('PORT'):
        config.setdefault('app', {})['port'] = int(os.environ.get('PORT'))
    
    if os.environ.get('FLASK_DEBUG'):
        config.setdefault('app', {})['debug'] = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    
    if os.environ.get('CORS_ORIGINS'):
        origins = os.environ.get('CORS_ORIGINS').split(',')
        config.setdefault('cors', {})['allowed_origins'] = [o.strip() for o in origins]
    
    return config


def get_default_config():
    """Default configuration if no config file is found"""
    return {
        'app': {
            'name': 'Event Manager',
            'version': '1.0.0',
            'debug': True,
            'port': 5001,
            'secret_key': 'dev-secret-key-change-in-production'
        },
        'branding': {
            'organization_name': 'Your Organization',
            'default_event_name': 'Your Event 2026',
            'support_email': 'support@example.com'
        },
        'cors': {
            'allowed_origins': ['http://localhost:5000', 'http://127.0.0.1:5000']
        },
        'session': {
            'type': 'filesystem',
            'cookie_samesite': 'Lax',
            'cookie_httponly': True
        },
        'features': {
            'registration': True,
            'check_in': True,
            'email_templates': True,
            'id_card_generation': True,
            'volunteer_dashboard': True
        }
    }


def create_app(config=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config is None:
        config = load_config()
    
    # Store config in app for access in blueprints
    app.config['EVENT_MANAGER_CONFIG'] = config
    
    # Flask configuration
    app_config = config.get('app', {})
    app.config['SECRET_KEY'] = app_config.get('secret_key', 'dev-secret-key')
    app.config['JSON_SORT_KEYS'] = False
    
    session_config = config.get('session', {})
    app.config['SESSION_TYPE'] = session_config.get('type', 'filesystem')
    app.config['SESSION_COOKIE_SAMESITE'] = session_config.get('cookie_samesite', 'Lax')
    app.config['SESSION_COOKIE_HTTPONLY'] = session_config.get('cookie_httponly', True)
    app.config['SESSION_COOKIE_SECURE'] = session_config.get('cookie_secure', False)
    
    # Enable CORS
    cors_config = config.get('cors', {})
    allowed_origins = cors_config.get('allowed_origins', ['http://localhost:5000'])
    
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True,
            "expose_headers": ["Set-Cookie"]
        }
    }, supports_credentials=True)
    
    # Register blueprints (excluding chatbot which is event-specific)
    app.register_blueprint(admin_bp)
    
    # Register optional blueprints based on features
    features = config.get('features', {})
    
    if features.get('registration', True):
        app.register_blueprint(register_bp)
    
    if features.get('schedule_planner', True):
        app.register_blueprint(plan_bp)
    
    if features.get('hackathon_module', True):
        app.register_blueprint(hackathon_bp)
    
    app.register_blueprint(cleanup_bp)
    
    # Initialize Firebase
    with app.app_context():
        if os.environ.get('FIREBASE_DISABLED', 'false').lower() != 'true':
            try:
                init_firebase()
                
                # Create default super admin if configured
                admin_config = config.get('admin', {}).get('default_super_admin', {})
                if admin_config:
                    create_default_admin(
                        username=admin_config.get('username', 'admin'),
                        password=admin_config.get('password', 'changeme123'),
                        name=admin_config.get('name', 'Super Admin'),
                        email=admin_config.get('email', 'admin@example.com')
                    )
                
                print("✓ Firebase initialized successfully")
            except Exception as e:
                print(f"⚠ Firebase initialization warning: {e}")
                print(f"   Make sure firebase-credentials.json exists or FIREBASE_CREDENTIALS env var is set")
        else:
            print("⚠ Firebase disabled via FIREBASE_DISABLED environment variable")
            print("  Super admin interface will work in demo mode without database")
    
    # Ensure generated_ids directory exists
    id_card_config = config.get('id_card', {})
    generated_ids_dir = os.path.join(os.path.dirname(__file__), 
                                     id_card_config.get('output_dir', 'static/generated_ids'))
    os.makedirs(generated_ids_dir, exist_ok=True)
    print(f"✓ Generated IDs directory: {generated_ids_dir}")
    
    # Warning for cloud deployments with ephemeral storage
    if id_card_config.get('ephemeral_storage_warning', True):
        if os.environ.get('RENDER') or os.environ.get('HEROKU'):
            print("⚠ WARNING: Running on cloud platform with ephemeral storage")
            print("   Generated ID cards will be lost on restart")
            print("   Consider using Firebase Storage or regenerating on-demand")
    
    # API information endpoint
    @app.route('/api')
    def api_info():
        branding = config.get('branding', {})
        return jsonify({
            'service': app_config.get('name', 'Event Manager'),
            'status': 'running',
            'version': app_config.get('version', '1.0.0'),
            'organization': branding.get('organization_name', 'Your Organization'),
            'endpoints': {
                'admin': {
                    'super_admin_dashboard': '/static/super-admin-dashboard.html',
                    'admin_dashboard': '/static/admin-dashboard.html',
                    'volunteer_dashboard': '/static/volunteer-login.html',
                    'login': '/api/admin/login',
                    'registrations': '/api/admin/registrations',
                    'events': '/api/superadmin/events',
                    'check_in': '/api/admin/check-in',
                    'stats': '/api/admin/stats',
                    'export': '/api/admin/export'
                },
                'registration': {
                    'ui': '/static/registration.html',
                    'submit': '/api/register'
                } if features.get('registration') else None,
                'planner': {
                    'api': '/api/plan'
                } if features.get('schedule_planner') else None
            },
            'features': features,
            'architecture': 'Multi-event management with role-based access control'
        })
    
    # Serve static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        """Serve static files from static directory"""
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, filename)
    
    # Serve generated ID cards
    @app.route('/static/generated_ids/<filename>')
    def serve_id_card(filename):
        """Serve generated ID card images"""
        generated_ids_dir = os.path.join(os.path.dirname(__file__), 
                                         id_card_config.get('output_dir', 'static/generated_ids'))
        file_path = os.path.join(generated_ids_dir, filename)
        
        if os.path.exists(file_path):
            return send_from_directory(generated_ids_dir, filename)
        else:
            return jsonify({
                'error': 'ID card not found',
                'message': f'The ID card "{filename}" does not exist or has not been generated yet.',
                'note': 'Use the /api/admin/id-card/view/<unique_id> endpoint to generate on-demand.'
            }), 404
    
    # Primary routes
    @app.route('/')
    def index():
        """Root endpoint - redirect to admin dashboard"""
        return jsonify({
            'message': 'Event Manager API',
            'version': app_config.get('version', '1.0.0'),
            'endpoints': {
                'super_admin': '/static/super-admin-dashboard.html',
                'admin': '/static/admin-dashboard.html',
                'volunteer': '/static/volunteer-login.html',
                'registration': '/static/registration.html',
                'api_docs': '/api'
            }
        })
    
    # Convenience routes for dashboards
    @app.route('/admin')
    def admin_route():
        """Serve admin dashboard"""
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'admin-dashboard.html')
    
    @app.route('/super-admin')
    def super_admin_route():
        """Serve super admin dashboard"""
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'super-admin-dashboard.html')
    
    @app.route('/volunteer')
    def volunteer_route():
        """Serve volunteer dashboard"""
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'volunteer-login.html')
    
    @app.route('/register')
    def registration_ui():
        """Serve registration UI"""
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_dir, 'registration.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'Available endpoints at /api'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'Something went wrong on the server'
        }), 500
    
    return app


# Create app instance for WSGI servers (gunicorn, etc.)
app = create_app()


if __name__ == '__main__':
    """
    Development server
    
    Run with: python app.py
    """
    config = load_config()
    app_config = config.get('app', {})
    
    debug_mode = app_config.get('debug', True)
    port = app_config.get('port', 5001)
    
    print("=" * 60)
    print(f"{app_config.get('name', 'EVENT MANAGER').upper()}")
    print("=" * 60)
    print(f"Version: {app_config.get('version', '1.0.0')}")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Server starting on http://0.0.0.0:{port}")
    print()
    print("Available dashboards:")
    print("  /admin              - Admin Dashboard")
    print("  /super-admin        - Super Admin Dashboard (multi-event)")
    print("  /volunteer          - Volunteer Dashboard (check-in)")
    print("  /register           - Registration Form")
    print()
    print("API Documentation:")
    print("  /api                - API information & endpoints")
    print()
    
    features = config.get('features', {})
    enabled_features = [k for k, v in features.items() if v]
    print(f"Enabled Features: {', '.join(enabled_features)}")
    print()
    
    branding = config.get('branding', {})
    print(f"Organization: {branding.get('organization_name', 'Your Organization')}")
    print(f"Database: Firebase Firestore")
    print("=" * 60)
    print()
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_mode,
        use_reloader=False  # Disable auto-reload to avoid double initialization
    )
