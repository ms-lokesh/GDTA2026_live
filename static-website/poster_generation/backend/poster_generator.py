import os
import uuid
from .image_processor import ImageProcessor
from .config import Config

class PosterGenerator:
    def __init__(self):
        self.processor = ImageProcessor(Config.TEMPLATE_PATH)

    def generate(self, user_img_path, name=None):
        filename = f"poster_{uuid.uuid4().hex}.png"
        output_path = os.path.join(Config.GENERATED_FOLDER, filename)
        
        success = self.processor.process_and_merge(user_img_path, output_path, name)
        
        if success:
            return filename
        return None
