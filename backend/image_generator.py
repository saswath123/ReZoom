from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import math
import io
import base64
import re

def crop_to_circle(image, size):
    """Crop PIL Image to a circular shape of given size while maintaining aspect ratio"""
    image = image.convert("RGBA")
    width, height = image.size
    min_dim = min(width, height)
    
    # Center crop to square
    left = (width - min_dim) / 2
    top = (height - min_dim) / 2
    right = (width + min_dim) / 2
    bottom = (height + min_dim) / 2
    image = image.crop((left, top, right, bottom))
    
    resample = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", getattr(Image, "NEAREST", 0)))
    if hasattr(Image, "Resampling"):
        resample = getattr(getattr(Image, "Resampling"), "LANCZOS", resample)
            
    image = image.resize((size, size), resample)
    
    # Create circular mask
    mask = Image.new("L", (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size - 1, size - 1), fill=255)
    
    # Apply mask
    circular_image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circular_image.paste(image, (0, 0), mask=mask)
    return circular_image

def safe_str(value):
    """Convert None to empty string safely"""
    return str(value) if value is not None else ""

def parse_raw_education(raw_str):
    """Parse raw education string (e.g. 'B.Tech, Mechanical Engineering, Bharat University, Chennai, 2025, 68%')
    into a structured dict with degree, institution, and year keys."""
    if not raw_str:
        return None
    raw_str = str(raw_str)
    parts = [p.strip() for p in raw_str.split(',') if p.strip()]
    if not parts:
        return None
        
    degree = ""
    institution = ""
    year = ""
    
    # Extract any 4-digit year first
    year_match = re.search(r'\b(19\d{2}|20[0-2]\d|2030)\b', raw_str)
    if year_match:
        year = year_match.group(0)
        # Remove year and optional percentage from parts to clean up degree and institution
        parts = [p for p in parts if not re.search(r'\b' + year + r'\b', p)]
    
    # Remove items that look like percentages or CGPA
    parts = [p for p in parts if not re.search(r'%\b|cgpa\b|gpa\b', p, re.IGNORECASE)]
    
    if len(parts) >= 2:
        inst_idx = -1
        for idx, p in enumerate(parts):
            p_lower = p.lower()
            if any(keyword in p_lower for keyword in ['university', 'college', 'school', 'polytechnic', 'institute', 'academy', 'vidyalaya']):
                inst_idx = idx
                break
        
        if inst_idx != -1:
            degree = ", ".join(parts[:inst_idx])
            institution = ", ".join(parts[inst_idx:])
        else:
            half = len(parts) // 2
            degree = ", ".join(parts[:half])
            institution = ", ".join(parts[half:])
    elif len(parts) == 1:
        degree = parts[0]
        institution = "Institution not specified"
    else:
        degree = "Degree not specified"
        institution = "Institution not specified"
        
    return {
        "degree": degree or "Degree not specified",
        "institution": institution or "Institution not specified",
        "year": year
    }

def get_font(size, bold=False):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    if bold:
        font_paths = [
            os.path.join(current_dir, "fonts", "Inter-Bold.ttf"),
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        font_paths = [
            os.path.join(current_dir, "fonts", "Inter-Regular.ttf"),
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue

    return ImageFont.load_default()

def wrap_text(draw, text, font, max_width):
    """Wrap text to fit within max_width"""
    if not text:
        return []
    
    words = safe_str(text).split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        try:
            line_width = draw.textlength(test_line, font=font)
        except:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_width = bbox[2] - bbox[0]
        
        if line_width <= max_width:
            continue
        else:
            if len(current_line) == 1:
                lines.append(test_line)
                current_line = []
            else:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]
    
    if current_line:
        lines.append(' '.join(current_line))
    
    return lines

def create_professional_avatar(draw, x, y, size, name, gender="neutral"):
    """Draw a professional premium avatar with initials, double border rings and shadow"""
    COLOR_PRIMARY_BLUE = (0, 94, 162)
    COLOR_DARK_BLUE = (0, 47, 81)
    COLOR_TEAL = (0, 168, 150)
    COLOR_WHITE = (255, 255, 255)
    
    # Subtle professional shadow (darker blue offset down and right)
    draw.ellipse([x + 3, y + 3, x + size + 3, y + size + 3], fill=COLOR_DARK_BLUE)
    
    # Outer Teal Circle Ring
    draw.ellipse([x, y, x + size, y + size], fill=COLOR_TEAL)
    
    # Inner White Gap Circle (Double border effect)
    draw.ellipse([x + 3, y + 3, x + size - 3, y + size - 3], fill=COLOR_WHITE)
    
    # Inner Solid Blue Circle
    draw.ellipse([x + 7, y + 7, x + size - 7, y + size - 7], fill=COLOR_PRIMARY_BLUE)
    
    # Thin Inner White Outline for high premium contrast
    draw.ellipse([x + 11, y + 11, x + size - 11, y + size - 11], outline=COLOR_WHITE, width=2)
    
    safe_name = safe_str(name)
    # Get initials e.g. "SA"
    words = [w for w in safe_name.split() if w]
    initials = ""
    if len(words) >= 2:
        initials = words[0][0].upper() + words[1][0].upper()
    elif len(words) == 1:
        initials = words[0][0].upper()
        if len(words[0]) > 1:
            initials += words[0][1].lower()  # use lowercase for second letter if only one word
    else:
        initials = "JD"
        
    try:
        font_size = int(size * 0.36)
        font = get_font(font_size, bold=True)
    except:
        font = ImageFont.load_default()
        
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center initials perfectly inside the circle by accounting for bbox offset
    text_x = x + (size - text_width) // 2 - bbox[0]
    text_y = y + (size - text_height) // 2 - bbox[1]
    
    draw.text((text_x, text_y), initials, fill=COLOR_WHITE, font=font)

def add_text_box(draw, x, y, width, height, text, font_size=11, 
                 bold=False, color=(51, 51, 51), align="left"):
    """Add text with proper positioning"""
    
    safe_text = safe_str(text)
    if not safe_text:
        return y
    
    try:
        font = get_font(font_size, bold)
    except:
        font = ImageFont.load_default()
    
    lines = wrap_text(draw, safe_text, font, width)
    
    current_y = y
    for line in lines:
        if align == "center":
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x + (width - text_width) // 2, current_y), line, fill=color, font=font)
        elif align == "right":
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            draw.text((x + width - text_width, current_y), line, fill=color, font=font)
        else:
            draw.text((x, current_y), line, fill=color, font=font)
        current_y += font_size + 4
    
    return current_y

def generate_resume_image(data, gap_analysis, output_path):
    """Generate professional resume image - SINGLE ENTRY POINT"""
    
    red_flags = data.get('red_flags', {})
    quality_score = data.get('resume_quality_score', 75)
    
    # Route to appropriate template based on quality score
    if quality_score < 30:
        return generate_worst_resume_template(data, gap_analysis, output_path)
    elif quality_score < 50:
        return generate_poor_resume_template(data, gap_analysis, output_path)
    else:
        return generate_professional_resume_template(data, gap_analysis, output_path)


def generate_worst_resume_template(data, gap_analysis, output_path):
    """Generate a 'Worst Resume' warning template"""
    
    width = 1600
    height = 1200
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    RED = (220, 38, 38)
    DARK_RED = (180, 20, 20)
    ORANGE = (249, 115, 22)
    WHITE = (255, 255, 255)
    GRAY = (100, 100, 100)
    
    try:
        font_title = get_font(56, bold=True)
        font_heading = get_font(28, bold=True)
        font_body = get_font(20)
        font_small = get_font(15)
    except:
        font_title = ImageFont.load_default()
        font_heading = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.rectangle([0, 0, width, 120], fill=RED)
    
    # Draw Profile Photo if present
    profile_image_base64 = data.get("profile_image_base64")
    if profile_image_base64:
        try:
            avatar_size = 100
            avatar_x = 40
            avatar_y = 10
            img_data = base64.b64decode(profile_image_base64)
            profile_img = Image.open(io.BytesIO(img_data))
            
            # White border
            draw.ellipse([avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3], fill=(255, 255, 255))
            circular_img = crop_to_circle(profile_img, avatar_size)
            img.paste(circular_img, (avatar_x, avatar_y), mask=circular_img)
        except Exception as e:
            print(f"Error drawing profile image: {e}")

    # Center title
    bbox = draw.textbbox((0, 0), "VERY POOR QUALITY RESUME", font=font_title)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) // 2, 35), "VERY POOR QUALITY RESUME", fill=WHITE, font=font_title)
    
    quality_score = data.get('resume_quality_score', 15)
    draw.ellipse([width-150, 15, width-30, 135], fill=DARK_RED)
    
    # Center quality score text inside ellipse
    score_str = str(quality_score)
    bbox_score = draw.textbbox((0, 0), score_str, font=font_title)
    score_w = bbox_score[2] - bbox_score[0]
    score_h = bbox_score[3] - bbox_score[1]
    draw.text((width - 90 - score_w//2, 75 - score_h//2), score_str, fill=WHITE, font=font_title)
    
    # Quality label
    bbox_lbl = draw.textbbox((0, 0), "QUALITY", font=font_small)
    lbl_w = bbox_lbl[2] - bbox_lbl[0]
    draw.text((width - 90 - lbl_w//2, 100), "QUALITY", fill=WHITE, font=font_small)
    
    y = 160
    draw.rectangle([40, y, width-40, y+60], fill=RED, outline=ORANGE, width=3)
    draw.text((60, y+15), "CRITICAL ISSUES DETECTED", fill=WHITE, font=font_heading)
    y += 80
    
    quality_observations = data.get('quality_observations', [])
    for obs in quality_observations[:8]:
        draw.text((60, y), obs, fill=RED, font=font_body)
        y += 32
    
    y += 20
    draw.rectangle([40, y, width-40, y+50], fill=GRAY)
    draw.text((60, y+12), "CANDIDATE INFORMATION", fill=WHITE, font=font_heading)
    y += 70
    
    name = data.get('name', 'Unknown Candidate')
    phone = data.get('phone', 'Not Provided')
    email = data.get('email', 'Not Provided')
    
    draw.text((60, y), f"Name: {name}", fill=(0,0,0), font=font_body)
    y += 35
    draw.text((60, y), f"Phone: {phone}", fill=(0,0,0), font=font_body)
    y += 35
    draw.text((60, y), f"Email: {email}", fill=(0,0,0), font=font_body)
    y += 50
    
    draw.rectangle([40, y, width-40, y+50], fill=ORANGE)
    draw.text((60, y+12), "RECOMMENDATIONS FOR IMPROVEMENT", fill=WHITE, font=font_heading)
    y += 70
    
    recommendations = [
        "1. Add complete and professional contact information",
        "2. Include relevant technical skills instead of social media",
        "3. Provide specific work experience with dates and achievements",
        "4. Write a professional summary focusing on skills",
        "5. Add proper education details with years and institutions",
        "6. Remove unprofessional language and exaggerations",
        "7. Use a standard resume format with clear sections"
    ]
    
    for rec in recommendations:
        draw.text((60, y), rec, fill=GRAY, font=font_body)
        y += 28
    
    draw.rectangle([0, height-60, width, height], fill=RED)
    
    footer_text = "This resume requires significant improvement before submission"
    bbox_footer = draw.textbbox((0, 0), footer_text, font=font_small)
    footer_w = bbox_footer[2] - bbox_footer[0]
    draw.text(((width - footer_w)//2, height-45), footer_text, fill=WHITE, font=font_small)
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def generate_poor_resume_template(data, gap_analysis, output_path):
    """Generate a 'Poor Quality' warning template"""
    
    width = 1600
    height = 1200
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    ORANGE = (249, 115, 22)
    YELLOW = (250, 204, 21)
    WHITE = (255, 255, 255)
    GRAY = (100, 100, 100)
    
    try:
        font_title = get_font(56, bold=True)
        font_heading = get_font(28, bold=True)
        font_body = get_font(20)
        font_small = get_font(16)
    except:
        font_title = ImageFont.load_default()
        font_heading = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.rectangle([0, 0, width, 120], fill=ORANGE)
    
    # Draw Profile Photo if present
    profile_image_base64 = data.get("profile_image_base64")
    if profile_image_base64:
        try:
            avatar_size = 100
            avatar_x = 40
            avatar_y = 10
            img_data = base64.b64decode(profile_image_base64)
            profile_img = Image.open(io.BytesIO(img_data))
            
            # White border
            draw.ellipse([avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3], fill=(255, 255, 255))
            circular_img = crop_to_circle(profile_img, avatar_size)
            img.paste(circular_img, (avatar_x, avatar_y), mask=circular_img)
        except Exception as e:
            print(f"Error drawing profile image: {e}")

    draw.text((width//2 - 300, 35), "POOR QUALITY RESUME", fill=WHITE, font=font_title)
    
    quality_score = data.get('resume_quality_score', 35)
    draw.ellipse([width-150, 15, width-30, 135], fill=YELLOW)
    draw.text((width-115, 30), str(quality_score), fill=(0,0,0), font=font_title)
    draw.text((width-120, 105), "QUALITY", fill=(0,0,0), font=font_small)
    
    y = 160
    draw.text((60, y), "Issues Detected:", fill=ORANGE, font=font_heading)
    y += 50
    
    quality_observations = data.get('quality_observations', [])
    for obs in quality_observations[:6]:
        draw.text((80, y), obs, fill=GRAY, font=font_body)
        y += 32
    
    y += 30
    draw.text((60, y), "Quick Fixes Needed:", fill=ORANGE, font=font_heading)
    y += 50
    
    fixes = [
        "Add professional email and phone number",
        "Include relevant technical skills",
        "Provide specific work experience with measurable achievements",
        "Use professional language throughout"
    ]
    
    for fix in fixes:
        draw.text((80, y), f"• {fix}", fill=GRAY, font=font_body)
        y += 32
        
    draw.rectangle([0, height-50, width, height], fill=ORANGE)
    draw.text((width//2 - 250, height-38), "This resume requires significant improvement before submission", fill=WHITE, font=font_small)
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def draw_circle_icon(draw, cx, cy, r, icon_type, color=(0, 94, 162), icon_color=(255, 255, 255)):
    """Draw a circular icon with white silhouette inside"""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    
    if icon_type == "user":
        # Head
        draw.ellipse([cx - r*0.25, cy - r*0.45, cx + r*0.25, cy - r*0.05], fill=icon_color)
        # Shoulders
        draw.chord([cx - r*0.45, cy - r*0.05, cx + r*0.45, cy + r*0.75], start=180, end=360, fill=icon_color)
    elif icon_type == "code":
        # Left angle <
        draw.line([(cx - r*0.4, cy), (cx - r*0.1, cy - r*0.35)], fill=icon_color, width=2)
        draw.line([(cx - r*0.4, cy), (cx - r*0.1, cy + r*0.35)], fill=icon_color, width=2)
        # Right angle >
        draw.line([(cx + r*0.4, cy), (cx + r*0.1, cy - r*0.35)], fill=icon_color, width=2)
        draw.line([(cx + r*0.4, cy), (cx + r*0.1, cy + r*0.35)], fill=icon_color, width=2)
        # Slash /
        draw.line([(cx - r*0.1, cy + r*0.4), (cx + r*0.1, cy - r*0.4)], fill=icon_color, width=2)
    elif icon_type == "briefcase":
        # Base
        draw.rectangle([cx - r*0.45, cy - r*0.15, cx + r*0.45, cy + r*0.45], fill=icon_color)
        # Handle
        draw.rectangle([cx - r*0.2, cy - r*0.35, cx + r*0.2, cy - r*0.15], outline=icon_color, width=2)
        # Lock or line
        draw.line([(cx - r*0.45, cy + r*0.15), (cx + r*0.45, cy + r*0.15)], fill=color, width=1)
        draw.rectangle([cx - r*0.08, cy + r*0.08, cx + r*0.08, cy + r*0.22], fill=icon_color)
    elif icon_type == "education":
        # Cap diamond
        draw.polygon([(cx, cy - r*0.4), (cx + r*0.5, cy - r*0.15), (cx, cy + r*0.15), (cx - r*0.5, cy - r*0.15)], fill=icon_color)
        # Cap base
        draw.rectangle([cx - r*0.25, cy + r*0.1, cx + r*0.25, cy + r*0.35], fill=icon_color)
        # Tassel
        draw.line([(cx + r*0.3, cy - r*0.15), (cx + r*0.4, cy + r*0.25)], fill=icon_color, width=2)
    elif icon_type == "certification":
        # Ribbons
        draw.polygon([(cx - r*0.2, cy), (cx - r*0.35, cy + r*0.55), (cx - r*0.1, cy + r*0.45)], fill=icon_color)
        draw.polygon([(cx + r*0.2, cy), (cx + r*0.35, cy + r*0.55), (cx + r*0.1, cy + r*0.45)], fill=icon_color)
        # Star/Medal
        draw.ellipse([cx - r*0.32, cy - r*0.35, cx + r*0.32, cy + r*0.28], fill=icon_color)
        draw.ellipse([cx - r*0.15, cy - r*0.18, cx + r*0.15, cy + r*0.12], fill=color)
    elif icon_type == "trophy":
        # Cup body
        draw.polygon([(cx - r*0.35, cy - r*0.4), (cx + r*0.35, cy - r*0.4), (cx + r*0.25, cy + r*0.1), (cx - r*0.25, cy + r*0.1)], fill=icon_color)
        # Stand stem
        draw.rectangle([cx - r*0.08, cy + r*0.1, cx + r*0.08, cy + r*0.38], fill=icon_color)
        # Stand base
        draw.rectangle([cx - r*0.25, cy + r*0.35, cx + r*0.25, cy + r*0.48], fill=icon_color)

def draw_contact_icon(draw, cx, cy, icon_type, color=(0, 168, 150)):
    """Draw small contact icon"""
    if icon_type == "phone":
        draw.rectangle([cx - 3, cy - 6, cx + 3, cy + 6], outline=color, width=2)
        draw.rectangle([cx - 2, cy - 4, cx + 2, cy - 2], fill=color)
        draw.rectangle([cx - 2, cy + 2, cx + 2, cy + 4], fill=color)
    elif icon_type == "location":
        draw.ellipse([cx - 5, cy - 8, cx + 5, cy + 2], fill=color)
        draw.polygon([(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy + 8)], fill=color)
        draw.ellipse([cx - 2, cy - 5, cx + 2, cy - 1], fill=(255, 255, 255))
    elif icon_type == "email":
        draw.rectangle([cx - 7, cy - 5, cx + 7, cy + 5], outline=color, width=2)
        draw.line([(cx - 7, cy - 5), (cx, cy + 1), (cx + 7, cy - 5)], fill=color, width=2)
    elif icon_type == "linkedin":
        try:
            draw.rounded_rectangle([cx - 7, cy - 7, cx + 7, cy + 7], radius=2, fill=color)
        except AttributeError:
            draw.rectangle([cx - 7, cy - 7, cx + 7, cy + 7], fill=color)
        font_tiny = get_font(10, bold=True)
        draw.text((cx - 5, cy - 6), "in", fill=(255, 255, 255), font=font_tiny)

def generate_professional_resume_template(data, gap_analysis, output_path):
    """Generate a professional corporate resume matching the reference image layout strictly"""
    
    width = 1600
    height = 1200
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # 1. Colors
    COLOR_PRIMARY_BLUE = (0, 94, 162)
    COLOR_DARK_TEAL = (0, 126, 138)
    COLOR_LIGHT_TEAL = (0, 168, 150)
    COLOR_TEXT_CHARCOAL = (51, 65, 85)
    COLOR_TEXT_DARK = (15, 23, 42)
    COLOR_TEXT_MUTED = (100, 116, 139)
    COLOR_DIVIDER = (203, 213, 225)
    
    # 2. Header
    # Base blue header
    draw.rectangle([0, 0, width, 180], fill=COLOR_PRIMARY_BLUE)
    
    # Teal polygons on the top right
    draw.polygon([(1320, 0), (1360, 180), (1600, 180), (1600, 0)], fill=COLOR_DARK_TEAL)
    draw.polygon([(1420, 0), (1450, 180), (1600, 180), (1600, 0)], fill=COLOR_LIGHT_TEAL)
    
    # Profile Photo
    avatar_size = 120
    avatar_x = 50
    avatar_y = 30
    
    profile_image_base64 = data.get("profile_image_base64")
    if profile_image_base64:
        try:
            img_data = base64.b64decode(profile_image_base64)
            profile_img = Image.open(io.BytesIO(img_data))
            
            # White border
            draw.ellipse([avatar_x - 3, avatar_y - 3, avatar_x + avatar_size + 3, avatar_y + avatar_size + 3], fill=(255, 255, 255))
            circular_img = crop_to_circle(profile_img, avatar_size)
            img.paste(circular_img, (avatar_x, avatar_y), mask=circular_img)
        except Exception as e:
            print(f"Error drawing profile image: {e}")
            create_professional_avatar(draw, avatar_x, avatar_y, avatar_size, 
                                       data.get("name", "Candidate"), data.get("gender", "neutral"))
    else:
        create_professional_avatar(draw, avatar_x, avatar_y, avatar_size, 
                                   data.get("name", "Candidate"), data.get("gender", "neutral"))
                                      # Candidate Name & Role in Header
    role_name = data.get('name', 'Professional Candidate')
    name = safe_str(role_name).upper()
    font_name = get_font(48, bold=True)
    draw.text((195, 46), name, fill=(255, 255, 255), font=font_name)
    
    if data.get('include_best_suited_role', False):
        curr_role = safe_str(data.get('current_role')).strip()
        if not curr_role or curr_role.lower() in ["not specified", "not_specified", "none"]:
            curr_role = "Professional"
        role = safe_str(data.get('custom_role') or data.get('job_role') or data.get('recommended_role') or curr_role)
        
        font_role = get_font(24)
        bbox_name = draw.textbbox((0, 0), name, font=font_name)
        name_w = bbox_name[2] - bbox_name[0]
        draw.text((195 + name_w + 25, 66), role, fill=(255, 255, 255), font=font_role)
    
    # 3. Two-Column Layout Setup
    # Middle Divider Line
    draw.line([(425, 210), (425, 1160)], fill=COLOR_DIVIDER, width=1)
    
    # Helper to draw section titles with circular icon
    def draw_section_title(draw, x, y, title, icon_type):
        cx = x + 18
        cy = y + 18
        draw_circle_icon(draw, cx, cy, 18, icon_type, color=COLOR_PRIMARY_BLUE)
        font_title = get_font(22, bold=True)
        draw.text((x + 48, y + 5), title.upper(), fill=COLOR_PRIMARY_BLUE, font=font_title)
        return y + 45
           # --- LEFT COLUMN (x = 40 to 400) ---
    left_x = 40
    left_width = 360
    
    # 1. TECHNICAL SKILLS SECTION (At the top, starting at 230)
    y_left = draw_section_title(draw, left_x, 230, "TECHNICAL SKILLS", "code")
    y_left += 5
    
    skills_p = data.get("skill_proficiency") or []
    if not skills_p:
        flat = data.get("skills") or []
        skills_p = [{"skill": s, "percentage": 80} for s in flat[:12]]
        
    skills_p = skills_p[:12]
    num_skills = len(skills_p)
    
    # Adaptive sizing based on skill count
    if num_skills <= 5:
        base_font_size = 18
        pct_font_size = 15
        bar_h = 5
        bar_offset = 8
        item_spacing = 24
    elif num_skills <= 7:
        base_font_size = 16
        pct_font_size = 13
        bar_h = 4
        bar_offset = 6
        item_spacing = 18
    elif num_skills <= 9:
        base_font_size = 14
        pct_font_size = 11
        bar_h = 3
        bar_offset = 5
        item_spacing = 12
    else:
        base_font_size = 13
        pct_font_size = 10
        bar_h = 3
        bar_offset = 4
        item_spacing = 8
        
    for sp in skills_p:
        skill_name = safe_str(sp.get("skill", ""))
        pct = min(100, max(10, int(sp.get("percentage") or 80)))
        
        # Reduce font size further for exceptionally long skill names
        f_size = base_font_size
        if len(skill_name) > 40:
            f_size = max(10, base_font_size - 3)
        elif len(skill_name) > 25:
            f_size = max(11, base_font_size - 2)
            
        # Draw Percentage Value (right aligned)
        add_text_box(draw, left_x + left_width - 45, y_left, 45, 20, f"{pct}%", font_size=pct_font_size, color=COLOR_TEXT_MUTED, align="right")
        
        # Draw Skill Name
        next_y = add_text_box(draw, left_x + 48, y_left, left_width - 98, 20, skill_name, font_size=f_size, bold=True, color=COLOR_TEXT_DARK)
        
        # Place the bar below the wrapped text
        bar_y = next_y + bar_offset
        draw.rounded_rectangle([left_x + 48, bar_y, left_x + left_width, bar_y + bar_h], radius=2, fill=(226, 232, 240))
        
        # Bar fill
        fill_w = int((left_width - 48) * pct / 100)
        draw.rounded_rectangle([left_x + 48, bar_y, left_x + 48 + fill_w, bar_y + bar_h], radius=2, fill=COLOR_LIGHT_TEAL)
        
        y_left = bar_y + bar_h + item_spacing
        
    # Divider after SKILLS
    draw.line([(left_x, y_left), (left_x + left_width, y_left)], fill=COLOR_DIVIDER, width=1)
    y_left += 15
    
    # 2. EDUCATION SECTION (Middle)
    edu_data = data.get('education') or {}
    if isinstance(edu_data, list):
        edu_list = edu_data
    elif isinstance(edu_data, dict):
        edu_list = [edu_data] if edu_data else []
    else:
        edu_list = []
        
    # Reconstruct/merge with education_raw to ensure we have all entries
    education_raw = data.get('education_raw') or []
    if isinstance(education_raw, list) and len(education_raw) > len(edu_list):
        parsed_raw_list = []
        for raw_str in education_raw:
            parsed = parse_raw_education(raw_str)
            if parsed:
                parsed_raw_list.append(parsed)
        if parsed_raw_list:
            edu_list = parsed_raw_list
            
    if not edu_list:
        edu_list = [{"degree": "Degree not specified", "institution": "Institution not specified", "year": ""}]
        
    # Calculate EDUCATION height for vertical centering between Skills end and Contact start (y = 930)
    edu_start = y_left
    edu_height = 45 + 5 # title + offset
    for edu in edu_list[:4]:
        degree = safe_str(edu.get('degree', 'Degree'))
        institution = safe_str(edu.get('institution', 'Institution'))
        year = safe_str(edu.get('year', ''))
        inst_text = f"{institution} ({year})" if year else institution
        
        degree_font_size = 15
        if len(degree) > 50: degree_font_size = 11
        elif len(degree) > 35: degree_font_size = 13
        
        inst_font_size = 14
        if len(inst_text) > 50: inst_font_size = 10
        elif len(inst_text) > 35: inst_font_size = 12
        
        try:
            temp_font_deg = get_font(degree_font_size, bold=True)
            deg_lines = len(wrap_text(draw, degree, temp_font_deg, left_width - 48))
        except:
            deg_lines = 1
        try:
            temp_font_inst = get_font(inst_font_size, bold=False)
            inst_lines = len(wrap_text(draw, inst_text, temp_font_inst, left_width - 48))
        except:
            inst_lines = 1
            
        edu_height += (deg_lines * (degree_font_size + 4)) + (inst_lines * (inst_font_size + 4)) + 6
        
    free_edu_space = 930 - edu_start - edu_height
    if free_edu_space > 0:
        y_left += free_edu_space // 2
        
    y_left = draw_section_title(draw, left_x, y_left, "EDUCATION", "education")
    y_left += 5
    
    # Defensive layout check: if space is tight, only render as many education items as will fit to prevent vertical overflow
    remaining_space = 1195 - y_left
    if remaining_space < 100:
        edu_list = edu_list[:1]
    elif remaining_space < 145:
        edu_list = edu_list[:2]
    elif remaining_space < 190:
        edu_list = edu_list[:3]
        
    for edu in edu_list[:4]:
        degree = safe_str(edu.get('degree', 'Degree'))
        institution = safe_str(edu.get('institution', 'Institution'))
        year = safe_str(edu.get('year', ''))
        inst_text = f"{institution} ({year})" if year else institution
        
        degree_font_size = 15
        if len(degree) > 50: degree_font_size = 11
        elif len(degree) > 35: degree_font_size = 13
        
        inst_font_size = 14
        if len(inst_text) > 50: inst_font_size = 10
        elif len(inst_text) > 35: inst_font_size = 12
        
        y_left = add_text_box(draw, left_x + 48, y_left, left_width - 48, 20, degree, font_size=degree_font_size, bold=True, color=COLOR_TEXT_DARK)
        y_left = add_text_box(draw, left_x + 48, y_left, left_width - 48, 20, inst_text, font_size=inst_font_size, color=COLOR_TEXT_CHARCOAL)
        y_left += 6
        
    # Divider after EDUCATION
    draw.line([(left_x, y_left), (left_x + left_width, y_left)], fill=COLOR_DIVIDER, width=1)
    
    # 3. CONTACT SECTION (At the bottom, starts at max(y_left + 45, 930))
    y_left = max(y_left + 45, 930)
    
    # Contact items spacing adjustment if remaining space is tight
    remaining_contact_space = 1195 - y_left
    contact_spacing = 12
    if remaining_contact_space < 250:
        contact_spacing = 6
        
    y_left = draw_section_title(draw, left_x, y_left, "CONTACT", "user")
    
    # Phone
    phone = data.get('phone') or 'Not specified'
    if phone:
        y_start = y_left
        y_lbl_end = add_text_box(draw, left_x + 48, y_start, left_width - 48, 20, "Phone", font_size=14, bold=True, color=COLOR_TEXT_DARK)
        y_det_end = add_text_box(draw, left_x + 48, y_lbl_end + 2, left_width - 48, 20, safe_str(phone), font_size=15, color=COLOR_TEXT_CHARCOAL)
        icon_cy = y_start + (y_det_end - y_start) // 2
        draw_contact_icon(draw, left_x + 18, icon_cy, "phone", color=COLOR_LIGHT_TEAL)
        y_left = y_det_end + contact_spacing
        
    # Location
    location = data.get('location') or 'Not specified'
    if location:
        y_start = y_left
        y_lbl_end = add_text_box(draw, left_x + 48, y_start, left_width - 48, 20, "Location", font_size=14, bold=True, color=COLOR_TEXT_DARK)
        y_det_end = add_text_box(draw, left_x + 48, y_lbl_end + 2, left_width - 48, 20, safe_str(location), font_size=15, color=COLOR_TEXT_CHARCOAL)
        icon_cy = y_start + (y_det_end - y_start) // 2
        draw_contact_icon(draw, left_x + 18, icon_cy, "location", color=COLOR_LIGHT_TEAL)
        y_left = y_det_end + contact_spacing
        
    # Email
    email = data.get('email') or 'Not specified'
    if email:
        y_start = y_left
        y_lbl_end = add_text_box(draw, left_x + 48, y_start, left_width - 48, 20, "Email", font_size=14, bold=True, color=COLOR_TEXT_DARK)
        y_det_end = add_text_box(draw, left_x + 48, y_lbl_end + 2, left_width - 48, 20, safe_str(email), font_size=15, color=COLOR_TEXT_CHARCOAL)
        icon_cy = y_start + (y_det_end - y_start) // 2
        draw_contact_icon(draw, left_x + 18, icon_cy, "email", color=COLOR_LIGHT_TEAL)
        y_left = y_det_end + contact_spacing
        
    # LinkedIn
    linkedin = data.get('linkedin') or ''
    if not linkedin:
        linkedin = f"linkedin.com/in/{name.lower().replace(' ', '')}"
    
    y_start = y_left
    y_lbl_end = add_text_box(draw, left_x + 48, y_start, left_width - 48, 20, "LinkedIn", font_size=14, bold=True, color=COLOR_TEXT_DARK)
    y_det_end = add_text_box(draw, left_x + 48, y_lbl_end + 2, left_width - 48, 20, safe_str(linkedin), font_size=15, color=COLOR_TEXT_CHARCOAL)
    icon_cy = y_start + (y_det_end - y_start) // 2
    draw_contact_icon(draw, left_x + 18, icon_cy, "linkedin", color=COLOR_LIGHT_TEAL)
    y_left = y_det_end + contact_spacing
        
        
    # --- RIGHT COLUMN (x = 455 to 1560) ---
    right_x = 455
    right_width = 1105
    
    # SUMMARY SECTION
    y_right = draw_section_title(draw, right_x, 210, "SUMMARY", "user")
    summary = safe_str(data.get('professional_summary', ''))
    if not summary:
        summary = "Results-driven professional with expertise in design and execution of software solutions."
        
    if len(summary) > 420:
        summary = summary[:417] + "..."
        
    y_right = add_text_box(draw, right_x + 15, y_right + 5, right_width - 15, 100, summary, font_size=17, color=COLOR_TEXT_CHARCOAL)
    y_right += 20
    
    # PROFESSIONAL EXPERIENCE SECTION
    y_right = draw_section_title(draw, right_x, y_right, "PROFESSIONAL EXPERIENCE", "briefcase")
    y_right += 10
    
    experiences = data.get('latest_3_experiences', []) or []
    
    timeline_y_start = y_right
    timeline_y_end = y_right
    timeline_dots = []
    
    for idx, exp in enumerate(experiences[:3]):
        job_y = y_right
        timeline_dots.append(job_y + 10)
        
        role_title = safe_str(exp.get('role', 'Position'))
        company = safe_str(exp.get('company', 'Company Name'))
        duration = safe_str(exp.get('duration', 'Date Range'))
        
        # 1. Job Role (size 19, bold, Primary Blue)
        role_y = add_text_box(draw, right_x + 30, job_y, right_width - 30, 20, role_title, font_size=19, bold=True, color=COLOR_PRIMARY_BLUE)
        # 2. Company Name (size 18, bold, Dark Teal Accent)
        comp_y = add_text_box(draw, right_x + 30, role_y + 2, right_width - 250, 20, company, font_size=18, bold=True, color=COLOR_DARK_TEAL)
        # 3. Employment Duration (size 15, regular, Muted) drawn beside company name on the right
        add_text_box(draw, right_x + right_width - 210, role_y + 4, 200, 20, duration, font_size=15, color=COLOR_TEXT_MUTED, align="right")
        y_right = comp_y + 2
        
        responsibilities = exp.get('responsibilities', []) or []
        resp_text = " ".join([safe_str(r).strip() for r in responsibilities if r])
        if resp_text:
            try:
                temp_font = get_font(17, bold=False)
            except:
                temp_font = ImageFont.load_default()
            wrapped_lines = wrap_text(draw, resp_text, temp_font, right_width - 30)
            if len(wrapped_lines) > 3:
                third_line = wrapped_lines[2]
                if not third_line.endswith("..."):
                    third_line = third_line.rstrip(".,; ") + "..."
                display_lines = [wrapped_lines[0], wrapped_lines[1], third_line]
            else:
                display_lines = wrapped_lines
            for line in display_lines:
                draw.text((right_x + 30, y_right), line, fill=COLOR_TEXT_CHARCOAL, font=temp_font)
                y_right += 17 + 4
            y_right += 6
                
        # Draw Tools & Technologies bullet line
        techs = exp.get('technologies', [])
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(',') if t.strip()]
        elif not isinstance(techs, list):
            techs = []
            
        if not techs:
            # Fallback to extracting from responsibilities / role if empty
            all_skills = data.get('skills', []) or []
            if not all_skills and data.get('skill_proficiency'):
                all_skills = [sp.get('skill') for sp in data.get('skill_proficiency', []) if sp.get('skill')]
            
            job_text = (role_title + " " + " ".join(responsibilities)).lower()
            found_techs = []
            for s in all_skills:
                if len(found_techs) >= 4:
                    break
                if f" {s.lower()} " in f" {job_text} " or job_text.startswith(s.lower() + " ") or job_text.endswith(" " + s.lower()):
                    found_techs.append(s)
            
            if len(found_techs) < 4:
                for s in all_skills:
                    if s not in found_techs and len(found_techs) < 4:
                        found_techs.append(s)
            techs = found_techs[:4]
            
        if techs:
            bold_font = get_font(17, bold=True)
            regular_font = get_font(17, bold=False)
            prefix = "Tools & Techs: "
            suffix = " • ".join(techs[:4])
            
            draw.text((right_x + 30, y_right), prefix, fill=COLOR_PRIMARY_BLUE, font=bold_font)
            try:
                prefix_width = draw.textlength(prefix, font=bold_font)
            except:
                bbox_p = draw.textbbox((0, 0), prefix, font=bold_font)
                prefix_width = bbox_p[2] - bbox_p[0]
                
            draw.text((right_x + 30 + prefix_width, y_right), suffix, fill=COLOR_TEXT_CHARCOAL, font=regular_font)
            y_right += 17 + 6
            
        y_right += 12
        timeline_y_end = y_right - 18
        
    if timeline_dots:
        draw.line([(right_x + 15, timeline_y_start), (right_x + 15, timeline_y_end)], fill=COLOR_LIGHT_TEAL, width=2)
        for dot_y in timeline_dots:
            draw.ellipse([right_x + 10, dot_y - 5, right_x + 20, dot_y + 5], fill=COLOR_LIGHT_TEAL)
            
    y_right += 10
    
    # CERTIFICATION'S SECTION
    certifications = data.get('certifications', []) or []
    certifications = [c for c in certifications if c]
    
    if certifications and y_right < 1080:
        y_right = draw_section_title(draw, right_x, y_right, "CERTIFICATIONS", "certification")
        y_right += 5
        
        col_width = (right_width - 40) // 2
        col1_x = right_x + 20
        col2_x = right_x + right_width // 2 + 10
        
        for i in range(0, len(certifications[:4]), 2):
            cert1 = safe_str(certifications[i])
            if len(cert1) > 55:
                cert1 = cert1[:52] + "..."
            
            cert2 = None
            if i + 1 < len(certifications[:4]):
                cert2 = safe_str(certifications[i+1])
                if len(cert2) > 55:
                    cert2 = cert2[:52] + "..."
            
            draw.ellipse([col1_x, y_right + 6, col1_x + 6, y_right + 12], fill=COLOR_PRIMARY_BLUE)
            y_col1 = add_text_box(draw, col1_x + 15, y_right, col_width - 15, 20, cert1, font_size=17, color=COLOR_TEXT_CHARCOAL)
            
            y_col2 = y_right
            if cert2:
                draw.ellipse([col2_x, y_right + 6, col2_x + 6, y_right + 12], fill=COLOR_PRIMARY_BLUE)
                y_col2 = add_text_box(draw, col2_x + 15, y_right, col_width - 15, 20, cert2, font_size=17, color=COLOR_TEXT_CHARCOAL)
            
            y_right = max(y_col1, y_col2) + 6
            
        y_right += 15
        
    # ACHIEVEMENTS SECTION
    achievements = data.get('achievements') or data.get('strengths') or []
    achievements = [a for a in achievements if a]
    
    if not achievements:
        fallback_role = safe_str(data.get('current_role') or data.get('job_role') or 'Software Engineer')
        achievements = [
            f"Successfully built and deployed {fallback_role} solutions, improving efficiency by 20%.",
            "Recognized by leadership for outstanding contribution and team collaboration."
        ]
        
    if achievements and y_right < 1080:
        y_right = draw_section_title(draw, right_x, y_right, "ACHIEVEMENTS", "trophy")
        y_right += 5
        
        col_width = (right_width - 40) // 2
        col1_x = right_x + 20
        col2_x = right_x + right_width // 2 + 10
        
        for i in range(0, len(achievements[:4]), 2):
            ach1 = safe_str(achievements[i])
            if len(ach1) > 55:
                ach1 = ach1[:52] + "..."
            
            ach2 = None
            if i + 1 < len(achievements[:4]):
                ach2 = safe_str(achievements[i+1])
                if len(ach2) > 55:
                    ach2 = ach2[:52] + "..."
            
            draw.ellipse([col1_x, y_right + 6, col1_x + 6, y_right + 12], fill=COLOR_PRIMARY_BLUE)
            y_col1 = add_text_box(draw, col1_x + 15, y_right, col_width - 15, 20, ach1, font_size=17, color=COLOR_TEXT_CHARCOAL)
            
            y_col2 = y_right
            if ach2:
                draw.ellipse([col2_x, y_right + 6, col2_x + 6, y_right + 12], fill=COLOR_PRIMARY_BLUE)
                y_col2 = add_text_box(draw, col2_x + 15, y_right, col_width - 15, 20, ach2, font_size=17, color=COLOR_TEXT_CHARCOAL)
            
            y_right = max(y_col1, y_col2) + 6
            
    # Optional Fit Score Display Check
    if data.get('include_fit_score', False):
        fit_score = data.get('fit_score', 85)
        if fit_score is None:
            fit_score = 85
        
        badge_size = 90
        badge_x = width - badge_size - 64
        badge_y = 45
        
        if fit_score >= 80:
            score_color = (46, 204, 113)
        elif fit_score >= 60:
            score_color = (241, 196, 15)
        else:
            score_color = (231, 76, 60)
            
        draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], fill=score_color)
        
        try:
            font_large = get_font(28, bold=True)
            font_small = get_font(9, bold=True)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), str(fit_score), font=font_large)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text((badge_x + (badge_size - text_w) // 2, badge_y + (badge_size - text_h) // 2 - 8), 
                  str(fit_score), fill=(255, 255, 255), font=font_large)
                  
        bbox = draw.textbbox((0, 0), "FIT SCORE", font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text((badge_x + (badge_size - text_w) // 2, badge_y + badge_size - 22), 
                  "FIT SCORE", fill=(255, 255, 255), font=font_small)
                  
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path