"""
ID Card Generator for GDTA 2026
Generates personalized ID cards with QR codes
"""

import os
import json
import qrcode
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict


class IDCardGenerator:
    """Generate ID cards for conference delegates"""
    
    def __init__(self, template_path: str = None, config_path: str = None):
        """
        Initialize ID card generator
        
        Args:
            template_path: Path to ID card template image
            config_path: Path to configuration JSON file
        """
        # Set default paths
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        if template_path is None:
            template_path = os.path.join(base_dir, 'static', 'templates', 'id_card_template.png')
        
        if config_path is None:
            config_path = os.path.join(base_dir, 'static', 'templates', 'id_card_config.json')
        
        self.template_path = template_path
        self.config_path = config_path
        self.output_dir = os.path.join(base_dir, 'static', 'generated_ids')
        
        # Load configuration
        self.config = self._load_config()
        
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load configuration from JSON file or use defaults"""
        default_config = {
            "name": {
                "position": [384, 400],  # Center horizontally, middle vertically
                "font_size": 50,
                "color": "#000000",
                "align": "center",
                "font": "Arial Bold"
            },
            "institution": {
                "position": [384, 480],
                "font_size": 28,
                "color": "#333333",
                "align": "center",
                "font": "Arial"
            },
            "qr_code": {
                "position": [50, 900],  # Bottom left
                "size": 150
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                print(f"Warning: Could not load config, using defaults: {e}")
        
        return default_config
    
    def _get_font(self, font_name: str, size: int):
        """Get font, fallback to default if not available"""
        try:
            # Try to load TTF font
            if font_name.lower().endswith('.ttf'):
                return ImageFont.truetype(font_name, size)
            
            # Map common font names to macOS system fonts
            font_map = {
                'Helvetica': 'Helvetica.ttc',
                'Helvetica-Bold': 'Helvetica.ttc',
                'Arial': 'Arial.ttf',
                'Arial Bold': 'Arial Bold.ttf',
            }
            
            # Try macOS system fonts
            if font_name in font_map:
                system_font = font_map[font_name]
                mac_paths = [
                    f"/System/Library/Fonts/{system_font}",
                    f"/Library/Fonts/{system_font}",
                ]
                
                for path in mac_paths:
                    if os.path.exists(path):
                        # For TTC fonts with bold, specify font index
                        if 'Bold' in font_name and path.endswith('.ttc'):
                            return ImageFont.truetype(path, size, index=1)
                        return ImageFont.truetype(path, size)
            
            # Try generic system font paths
            font_paths = [
                f"/System/Library/Fonts/{font_name}.ttf",
                f"/System/Library/Fonts/{font_name}.ttc",
                f"/Library/Fonts/{font_name}.ttf",
                f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}.ttf",
            ]
            
            for path in font_paths:
                if os.path.exists(path):
                    return ImageFont.truetype(path, size)
            
            # Fallback to default
            print(f"Warning: Font '{font_name}' not found, using default")
            return ImageFont.load_default()
        except Exception as e:
            print(f"Warning: Could not load font '{font_name}': {e}")
            return ImageFont.load_default()
    
    def _generate_qr_code(self, data: str, size: int) -> Image:
        """Generate QR code image"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size), Image.LANCZOS)
        
        return qr_img
    
    def generate_id_card(self, 
                        name: str, 
                        institution: str, 
                        registration_id: str,
                        qr_data: Optional[str] = None) -> str:
        """
        Generate ID card for a delegate
        
        Args:
            name: Delegate's full name
            institution: Institution name
            registration_id: Unique registration email/ID
            qr_data: Optional custom QR code data (defaults to registration_id)
        
        Returns:
            Path to generated ID card image
        """
        # Load template
        template = Image.open(self.template_path)
        template = template.convert('RGB')  # Ensure RGB mode
        
        # Create drawing context
        draw = ImageDraw.Draw(template)
        
        # Convert text to uppercase
        name = name.upper()
        institution = institution.upper()
        
        # Draw name
        name_config = self.config['name']
        name_font = self._get_font(name_config.get('font', 'Arial Bold'), name_config['font_size'])
        name_x, name_y = name_config['position']
        
        # Get text size for alignment calculations
        bbox = draw.textbbox((0, 0), name, font=name_font)
        text_width = bbox[2] - bbox[0]
        
        align_mode = name_config.get('align', 'left')
        if align_mode == 'center':
            # Center based on full template width
            name_x = (template.width - text_width) // 2
        elif align_mode == 'center_whitespace':
            # Center within white space area (excluding right border)
            # Assuming white space is approximately 680px wide (template is ~768px, border ~88px)
            whitespace_width = 680
            name_x = (whitespace_width - text_width) // 2 + name_config['position'][0]
        elif align_mode == 'right':
            name_x = template.width - text_width - name_config['position'][0]
        # For 'left' or 'free' mode, use position as-is
        
        draw.text((name_x, name_y), name, fill=name_config['color'], font=name_font)
        
        # Draw institution
        inst_config = self.config['institution']
        inst_font = self._get_font(inst_config.get('font', 'Arial'), inst_config['font_size'])
        inst_x, inst_y = inst_config['position']
        
        # Get text size for alignment calculations
        bbox = draw.textbbox((0, 0), institution, font=inst_font)
        text_width = bbox[2] - bbox[0]
        
        align_mode = inst_config.get('align', 'left')
        if align_mode == 'center':
            # Center based on full template width
            inst_x = (template.width - text_width) // 2
        elif align_mode == 'center_whitespace':
            # Center within white space area (excluding right border)
            whitespace_width = 680
            inst_x = (whitespace_width - text_width) // 2
        elif align_mode == 'right':
            inst_x = template.width - text_width - inst_config['position'][0]
        # For 'left' or 'free' mode, use position as-is
        
        draw.text((inst_x, inst_y), institution, fill=inst_config['color'], font=inst_font)
        
        # Generate and add QR code
        qr_config = self.config['qr_code']
        qr_data = qr_data or registration_id
        qr_img = self._generate_qr_code(qr_data, qr_config['size'])
        
        qr_x, qr_y = qr_config['position']
        template.paste(qr_img, (qr_x, qr_y))
        
        # Save generated ID card
        # Clean filename (replace special characters)
        safe_id = registration_id.replace('@', '_at_').replace('.', '_')
        output_filename = f"id_card_{safe_id}.png"
        output_path = os.path.join(self.output_dir, output_filename)
        
        template.save(output_path, 'PNG')
        
        return output_path
    
    def batch_generate(self, registrations: list) -> Dict[str, str]:
        """
        Generate ID cards for multiple registrations
        
        Args:
            registrations: List of registration dicts with keys:
                {name, institution, email/id}
        
        Returns:
            Dictionary mapping registration_id to generated file path
        """
        results = {}
        
        for reg in registrations:
            try:
                reg_id = reg.get('id') or reg.get('email')
                name = reg.get('name')
                institution = reg.get('institution')
                
                if not all([reg_id, name, institution]):
                    print(f"Skipping incomplete registration: {reg}")
                    continue
                
                output_path = self.generate_id_card(name, institution, reg_id)
                results[reg_id] = output_path
                print(f"✅ Generated ID card for {name}")
                
            except Exception as e:
                print(f"❌ Failed to generate ID card for {reg.get('name', 'unknown')}: {e}")
                results[reg_id] = None
        
        return results


# Convenience function
def generate_id_card(name: str, institution: str, registration_id: str) -> str:
    """
    Simple function to generate an ID card
    
    Args:
        name: Delegate's full name
        institution: Institution name
        registration_id: Unique registration ID/email
    
    Returns:
        Path to generated ID card
    """
    generator = IDCardGenerator()
    return generator.generate_id_card(name, institution, registration_id)
