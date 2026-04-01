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
                "position": [40, 680],
                "font_size": 68,
                "color": "#000000",
                "align": "left",
                "font": "Helvetica-Bold"
            },
            "institution": {
                "position": [40, 760],
                "font_size": 44,
                "color": "#000000",
                "align": "left",
                "font": "Helvetica-Bold"
            },
            "qr_code": {
                "position": [40, 1050],
                "size": 200
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
    
    def _wrap_text_to_lines(self, draw, text: str, font_name: str, font_size: int, max_width: int, max_lines: int = 3):
        """
        Wrap text into multiple lines that fit within the given width
        Returns (font, lines_list, line_height)
        """
        font = self._get_font(font_name, font_size)
        words = text.split()
        lines = []
        current_line = ""
        
        # Try to fit text with current font size
        for word in words:
            # Check if this single word is too long for the line
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            
            if word_width > max_width:
                # Word is too long, need to break it
                if current_line:
                    lines.append(current_line)
                    current_line = ""
                
                # Break the long word into chunks
                char_chunks = []
                temp_chunk = ""
                for char in word:
                    test_chunk = temp_chunk + char
                    bbox = draw.textbbox((0, 0), test_chunk, font=font)
                    if (bbox[2] - bbox[0]) <= max_width:
                        temp_chunk = test_chunk
                    else:
                        if temp_chunk:
                            char_chunks.append(temp_chunk)
                        temp_chunk = char
                if temp_chunk:
                    char_chunks.append(temp_chunk)
                
                # Add the chunks as separate lines
                for chunk in char_chunks[:-1]:
                    lines.append(chunk)
                # Start new line with the last chunk
                current_line = char_chunks[-1] if char_chunks else ""
            else:
                # Regular word processing
                test_line = current_line + (" " if current_line else "") + word
                bbox = draw.textbbox((0, 0), test_line, font=font)
                test_width = bbox[2] - bbox[0]
                
                if test_width <= max_width:
                    current_line = test_line
                else:
                    # Current line is full, start a new line
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        # This shouldn't happen as we checked word width above
                        lines.append(word)
        
        # Add the last line
        if current_line:
            lines.append(current_line)
        
        # If we have too many lines, reduce font size and try again
        if len(lines) > max_lines and font_size > 12:
            return self._wrap_text_to_lines(draw, text, font_name, font_size - 2, max_width, max_lines)
        
        # If still too many lines, truncate
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if len(lines) == max_lines and len(lines) > 0:
                # Add ellipsis to last line if truncated
                last_line = lines[-1]
                if len(last_line) > 3:
                    lines[-1] = last_line[:-3] + "..."
        
        # Calculate line height
        bbox = draw.textbbox((0, 0), "Ag", font=font)
        line_height = (bbox[3] - bbox[1]) + 4  # Add 4px spacing between lines
        
        return font, lines, line_height
    
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
                        qr_data: Optional[str] = None,
                        fee_text: Optional[str] = None,
                        safari_route_text: Optional[str] = None) -> str:
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
        
        # Draw name with automatic line wrapping
        name_config = self.config['name']
        name_x, name_y = name_config['position']
        
        # Calculate available width for text (reduced margin for more text space)
        available_width = template.width - name_x - 180  # Reduced from 200px to 180px margin
        
        # Wrap text into multiple lines that fit
        name_font, name_lines, name_line_height = self._wrap_text_to_lines(
            draw, name, 
            name_config.get('font', 'Helvetica-Bold'), 
            name_config['font_size'],
            available_width,
            max_lines=2  # Allow max 2 lines for names
        )
        
        # Draw each line of the name
        for i, line in enumerate(name_lines):
            draw.text((name_x, name_y + i * name_line_height), line, 
                     fill=name_config['color'], font=name_font)
        
        # Draw institution with automatic line wrapping
        inst_config = self.config['institution']
        inst_x, inst_y = inst_config['position']
        
        # For institution, start after the name text (if name has multiple lines)
        if len(name_lines) > 1:
            # Adjust institution Y position to account for multi-line name
            inst_y = name_y + len(name_lines) * name_line_height + 20  # 20px gap
        
        # Wrap institution text into multiple lines with smaller font size for better fit
        inst_font_size = min(inst_config['font_size'], 26)  # Cap institution font at 26px for even better wrapping
        inst_font, inst_lines, inst_line_height = self._wrap_text_to_lines(
            draw, institution,
            inst_config.get('font', 'Helvetica-Bold'),
            inst_font_size,
            available_width + 120,  # Allow even more width for institution
            max_lines=6  # Allow max 6 lines for institutions
        )
        
        # Draw each line of the institution
        for i, line in enumerate(inst_lines):
            draw.text((inst_x, inst_y + i * inst_line_height), line,
                     fill=inst_config['color'], font=inst_font)
        
        # Generate and add QR code with dynamic positioning
        qr_config = self.config['qr_code']
        qr_data = qr_data or registration_id
        qr_img = self._generate_qr_code(qr_data, qr_config['size'])
        
        # Calculate QR position - place below institution text with large margin
        inst_text_bottom = inst_y + len(inst_lines) * inst_line_height + 80  # 80px margin (increased for more space)
        qr_y = max(qr_config['position'][1], inst_text_bottom)  # Use whichever is lower
        qr_x = qr_config['position'][0]
        
        # Ensure QR code doesn't go off the bottom of the template
        if qr_y + qr_config['size'] > template.height - 20:
            qr_y = template.height - qr_config['size'] - 20  # Reduced margin to allow lower positioning

        # Draw fee and safari route text above QR if available
        text_cursor_y = qr_y - 46
        if fee_text:
            fee_font = self._get_font('Helvetica-Bold', 30)
            fee_x = qr_x
            fee_y = max(20, text_cursor_y)
            draw.text((fee_x, fee_y), f"FEE: {fee_text}", fill="#000000", font=fee_font)
            text_cursor_y = fee_y - 34

        if safari_route_text:
            route_font = self._get_font('Helvetica', 20)
            route_x = qr_x
            route_y = max(20, text_cursor_y)
            draw.text((route_x, route_y), f"SAFARI: {safari_route_text}", fill="#000000", font=route_font)
        
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
def generate_id_card(name: str, institution: str, registration_id: str, fee_text: Optional[str] = None, safari_route_text: Optional[str] = None) -> str:
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
    return generator.generate_id_card(name, institution, registration_id, fee_text=fee_text, safari_route_text=safari_route_text)
