import os
from flask import Flask, send_from_directory
from backend.config import Config
from backend.routes import poster_bp

app = Flask(__name__, static_folder=os.path.join(Config.BASE_DIR, '../assets'), static_url_path='/static') 
app.config.from_object(Config)

# Register blueprint
app.register_blueprint(poster_bp, url_prefix='/poster')

@app.route('/poster/static/<path:filename>')
def poster_static(filename):
    return send_from_directory(os.path.join(Config.BASE_DIR, 'static'), filename)

@app.route('/')
def index():
    from flask import redirect, url_for
    return redirect(url_for('poster_bp.landing'))

if __name__ == '__main__':
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(Config.GENERATED_FOLDER, exist_ok=True)
    os.makedirs(os.path.dirname(Config.TEMPLATE_PATH), exist_ok=True)
    
    # Generate a placeholder template if it doesn't exist
    if not os.path.exists(Config.TEMPLATE_PATH):
        from PIL import Image, ImageDraw, ImageFont
        template = Image.new("RGBA", (1080, 1080), (233, 30, 99, 255)) # GDTA Pink
        draw = ImageDraw.Draw(template)
        # Draw some text
        # Assuming no font file available, use default
        try:
            draw.text((300, 100), "GDTA'26 Build4Change", fill="white", font=ImageFont.truetype("arial.ttf", 60))
        except:
            draw.text((300, 100), "GDTA'26 Build4Change", fill="white")
            
        # Draw a transparent circle for the photo
        # Cutout coordinate should match image_processor paste_coords: (240, 240) size (600, 600)
        draw.ellipse((240, 240, 840, 840), fill=(255, 255, 255, 0))
        # Draw border
        draw.ellipse((235, 235, 845, 845), outline="white", width=10)
        
        template.save(Config.TEMPLATE_PATH, "PNG")

    app.run(debug=True, port=8001)
