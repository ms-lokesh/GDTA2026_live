import os
from PIL import Image, ImageDraw, ImageOps

class ImageProcessor:
    def __init__(self, template_path):
        self.template_path = template_path
        # New template: 1122x1713, left oriented
        self.target_size = (450, 450)
        self.paste_coords = (55, 600)

    def process_and_merge(self, user_img_path, output_path, name=None):
        try:
            user_img = Image.open(user_img_path).convert("RGBA")
            template_img = Image.open(self.template_path).convert("RGBA")
            
            # Crop the user image to the target size, prioritizing the top to avoid cutting off heads
            user_img = ImageOps.fit(user_img, self.target_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.0))
            
            # Create a circular mask for the user image
            mask = Image.new('L', self.target_size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0) + self.target_size, fill=255)
            
            user_img.putalpha(mask)
            
            # We paste the template ON TOP of the user image if the template has a transparent hole.
            # But wait, it's easier to create a background canvas, paste the user image, then paste the template.
            # Let's assume the template is a full poster with a transparent circle.
            # Create a background canvas
            final_img = Image.new("RGBA", template_img.size, (255, 255, 255, 255))
            
            # Paste the template first (since it doesn't have a transparent hole)
            final_img.paste(template_img, (0, 0))
            
            # Paste the user image ON TOP of the template using the circular mask
            final_img.paste(user_img, self.paste_coords, mask)
            
            if name:
                from PIL import ImageFont
                draw = ImageDraw.Draw(final_img)
                
                max_text_width = 500
                font_size = 90
                font = None
                
                def get_text_width(f, text):
                    try:
                        return f.getbbox(text)[2] - f.getbbox(text)[0]
                    except AttributeError:
                        return draw.textsize(text, font=f)[0]
                
                while font_size >= 20:
                    try:
                        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", font_size)
                    except:
                        try:
                            font = ImageFont.truetype("arial.ttf", font_size)
                        except:
                            font = ImageFont.load_default()
                            break
                    
                    if get_text_width(font, name) <= max_text_width:
                        break
                    font_size -= 4
                
                # Calculate text position (center below the photo)
                photo_center_x = self.paste_coords[0] + (self.target_size[0] // 2)
                photo_bottom_y = self.paste_coords[1] + self.target_size[1] + 20
                
                text_width = get_text_width(font, name)
                text_x = photo_center_x - (text_width // 2)
                
                # Ensure it doesn't go completely off-screen on the left even if max_width constraint failed
                text_x = max(10, text_x)
                
                draw.text((text_x, photo_bottom_y), name, font=font, fill="black")
            
            final_img.save(output_path, "PNG")
            return True
        except Exception as e:
            print(f"Error processing image: {e}")
            return False
