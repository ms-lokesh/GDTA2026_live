"""
GDTA 2026 Chatbot Backend - Main Application
Flask server with logic-controlled AI assistant

ARCHITECTURE PRINCIPLES:
1. Backend controls all decisions
2. AI used only for language understanding/generation
3. All scheduling logic is deterministic
4. JSON files are the single source of truth
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

# Import our route blueprints
from routes.chat import chat_bp
from routes.plan import plan_bp
from routes.register import register_bp
from routes.cleanup import cleanup_bp
from routes.admin import admin_bp

# Import database initialization
from db.firebase_models import init_firebase, create_default_admin


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['JSON_SORT_KEYS'] = False  # Preserve JSON order
    app.config['SESSION_TYPE'] = 'filesystem'  # For session support
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    
    # Enable CORS for frontend integration
    allowed_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000,http://127.0.0.1:5500,null')
    origins_list = [origin.strip() for origin in allowed_origins.split(',')]
    
    CORS(app, resources={
        r"/api/*": {
            "origins": origins_list,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True,
            "expose_headers": ["Set-Cookie"]
        }
    }, supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(register_bp)
    app.register_blueprint(cleanup_bp)
    app.register_blueprint(admin_bp)
    
    # Initialize Firebase Firestore
    with app.app_context():
        try:
            init_firebase()
            create_default_admin()
            print("✓ Firebase initialized successfully")
        except Exception as e:
            print(f"⚠ Firebase initialization warning: {e}")
            print(f"   Make sure firebase-credentials.json exists or FIREBASE_CREDENTIALS env var is set")
    
    # Serve main chatbot UI
    @app.route('/')
    def index():
        return send_from_directory('static', 'index.html')
    
    # Serve admin dashboard
    @app.route('/admin')
    def admin_dashboard():
        return send_from_directory('static', 'admin-dashboard.html')
    
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
    
    # Serve registration UI
    @app.route('/register')
    def registration_ui():
        return send_from_directory('static', 'registration.html')
    
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        return send_from_directory('static', filename)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'Check /api/chat or /api/plan'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'Something went wrong on the server'
        }), 500
    
    return app


if __name__ == '__main__':
    """
    Development server
    
    Run with: python app.py
    
    The server will start on http://localhost:5000
    """
    app = create_app()
    
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
