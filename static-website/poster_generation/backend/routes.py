import os
import uuid
import time
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_from_directory
from .config import Config
from .poster_generator import PosterGenerator

poster_bp = Blueprint('poster_bp', __name__, template_folder='../pages', static_folder='../static')
generator = PosterGenerator()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@poster_bp.route('/')
def landing():
    return render_template('landing.html')

@poster_bp.route('/upload')
def upload():
    return render_template('upload.html')

@poster_bp.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"temp_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)
        return jsonify({'success': True, 'temp_id': filename})
    return jsonify({'error': 'Invalid file type'}), 400

@poster_bp.route('/processing')
def processing():
    temp_id = request.args.get('id')
    name = request.args.get('name', '')
    if not temp_id:
        return redirect(url_for('poster_bp.upload'))
    return render_template('processing.html', temp_id=temp_id, name=name)

@poster_bp.route('/api/generate', methods=['POST'])
def api_generate():
    data = request.get_json()
    temp_id = data.get('id')
    name = data.get('name', '')
    if not temp_id:
        return jsonify({'error': 'Missing id'}), 400
        
    filepath = os.path.join(Config.UPLOAD_FOLDER, temp_id)
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
        
    generated_filename = generator.generate(filepath, name)
    
    # Simulate processing time so the user sees the cool loader
    time.sleep(1.5)
    
    # Cleanup temp file
    try:
        os.remove(filepath)
    except:
        pass
        
    if generated_filename:
        return jsonify({'success': True, 'poster_id': generated_filename})
    return jsonify({'error': 'Generation failed'}), 500

@poster_bp.route('/result')
def result():
    poster_id = request.args.get('id')
    if not poster_id:
        return redirect(url_for('poster_bp.upload'))
    return render_template('result.html', poster_id=poster_id, caption=Config.LINKEDIN_CAPTION)

@poster_bp.route('/download/<filename>')
def download(filename):
    return send_from_directory(Config.GENERATED_FOLDER, filename, as_attachment=True)

@poster_bp.route('/preview/<filename>')
def preview(filename):
    return send_from_directory(Config.GENERATED_FOLDER, filename)
