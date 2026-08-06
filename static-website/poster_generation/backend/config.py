import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    GENERATED_FOLDER = os.path.join(BASE_DIR, 'generated')
    TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates', 'poster_template.png')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
    
    LINKEDIN_CAPTION = """🚀 Excited to be attending D Conference 2026 at SNS Institutions!

Looking forward to an inspiring day of innovation, creativity, and collaboration with fellow designers, innovators, and industry experts. Excited to explore fresh ideas, meaningful discussions, and the future of design thinking.

See you at D Conference 2026!
Register and learn more: https://gdta2026.com/

#DConference2026 #DesignThinking #GDTA2026 #SNSInstitutions #Innovation #Creativity #FutureOfDesign #DesignCommunity #Learning #Networking"""
