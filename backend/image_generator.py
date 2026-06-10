from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import math

def safe_str(value):
    """Convert None to empty string safely"""
    return str(value) if value is not None else ""

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
    """Draw a professional avatar with initials"""
    
    if gender == "male":
        bg_color = (52, 73, 94)
    elif gender == "female":
        bg_color = (192, 57, 43)
    else:
        bg_color = (41, 128, 185)
    
    draw.ellipse([x, y, x + size, y + size], fill=bg_color)
    draw.ellipse([x + 3, y + 3, x + size - 3, y + size - 3], outline=(255, 255, 255), width=2)
    
    safe_name = safe_str(name)
    initials = ''.join([word[0].upper() for word in safe_name.split()[:2] if word])
    if not initials:
        initials = "P"
    
    try:
        font = get_font(size // 2, bold=True)
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), initials, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text((x + (size - text_width) // 2, y + (size - text_height) // 2), 
              initials, fill=(255, 255, 255), font=font)

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
    
    width = 1920
    height = 1080
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    RED = (220, 38, 38)
    DARK_RED = (180, 20, 20)
    ORANGE = (249, 115, 22)
    WHITE = (255, 255, 255)
    GRAY = (100, 100, 100)
    
    try:
        font_title = get_font(72, bold=True)
        font_heading = get_font(36, bold=True)
        font_body = get_font(24)
        font_small = get_font(18)
    except:
        font_title = ImageFont.load_default()
        font_heading = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.rectangle([0, 0, width, 120], fill=RED)
    draw.text((width//2 - 200, 35), "VERY POOR QUALITY RESUME", fill=WHITE, font=font_title)
    
    quality_score = data.get('resume_quality_score', 15)
    draw.ellipse([width-150, 20, width-30, 140], fill=DARK_RED)
    draw.text((width-115, 60), str(quality_score), fill=WHITE, font=font_title)
    draw.text((width-120, 105), "QUALITY", fill=WHITE, font=font_small)
    
    y = 160
    draw.rectangle([40, y, width-40, y+60], fill=RED, outline=ORANGE, width=3)
    draw.text((60, y+15), "CRITICAL ISSUES DETECTED", fill=WHITE, font=font_heading)
    y += 80
    
    quality_observations = data.get('quality_observations', [])
    for obs in quality_observations[:8]:
        draw.text((60, y), obs, fill=RED, font=font_body)
        y += 40
    
    y += 20
    draw.rectangle([40, y, width-40, y+50], fill=GRAY)
    draw.text((60, y+12), "CANDIDATE INFORMATION", fill=WHITE, font=font_heading)
    y += 70
    
    name = data.get('name', 'Unknown Candidate')
    phone = data.get('phone', 'Not Provided')
    email = data.get('email', 'Not Provided')
    
    draw.text((60, y), f"Name: {name}", fill=(0,0,0), font=font_body)
    y += 40
    draw.text((60, y), f"Phone: {phone}", fill=(0,0,0), font=font_body)
    y += 40
    draw.text((60, y), f"Email: {email}", fill=(0,0,0), font=font_body)
    y += 60
    
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
        y += 35
    
    draw.rectangle([0, height-60, width, height], fill=RED)
    draw.text((width//2 - 250, height-45), "This resume requires significant improvement before submission", fill=WHITE, font=font_small)
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def generate_poor_resume_template(data, gap_analysis, output_path):
    """Generate a 'Poor Quality' warning template"""
    
    width = 1920
    height = 1080
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    ORANGE = (249, 115, 22)
    YELLOW = (250, 204, 21)
    WHITE = (255, 255, 255)
    GRAY = (100, 100, 100)
    
    try:
        font_title = get_font(52, bold=True)
        font_heading = get_font(28, bold=True)
        font_body = get_font(20)
        font_small = get_font(16)
    except:
        font_title = ImageFont.load_default()
        font_heading = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    draw.rectangle([0, 0, width, 100], fill=ORANGE)
    draw.text((width//2 - 180, 30), "POOR QUALITY RESUME", fill=WHITE, font=font_title)
    
    quality_score = data.get('resume_quality_score', 35)
    draw.ellipse([width-150, 15, width-30, 135], fill=YELLOW)
    draw.text((width-115, 50), str(quality_score), fill=(0,0,0), font=font_title)
    draw.text((width-120, 95), "QUALITY", fill=GRAY, font=font_small)
    
    y = 140
    draw.text((60, y), "Issues Detected:", fill=ORANGE, font=font_heading)
    y += 45
    
    quality_observations = data.get('quality_observations', [])
    for obs in quality_observations[:6]:
        draw.text((80, y), obs, fill=GRAY, font=font_body)
        y += 35
    
    y += 20
    draw.text((60, y), "Quick Fixes Needed:", fill=ORANGE, font=font_heading)
    y += 45
    
    fixes = [
        "Add professional email and phone number",
        "Include relevant technical skills",
        "Provide specific work experience with measurable achievements",
        "Use professional language throughout"
    ]
    
    for fix in fixes:
        draw.text((80, y), fix, fill=GRAY, font=font_body)
        y += 35
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


def generate_professional_resume_template(data, gap_analysis, output_path):
    """Generate a professional, clean corporate resume as PNG image"""
    
    width = 1920
    height = 1440
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    COLOR_NAVY = (31, 58, 147)
    COLOR_GOLD = (198, 155, 53)
    COLOR_GRAY = (128, 128, 128)
    COLOR_LIGHT_GRAY = (245, 245, 245)
    COLOR_DARK = (51, 51, 51)
    COLOR_WHITE = (255, 255, 255)
    
    def inches_to_pixels(inches):
        return int(inches * 192)
    
    sidebar_width = inches_to_pixels(3)
    draw.rectangle([0, 0, sidebar_width, height], fill=COLOR_LIGHT_GRAY)
    
    avatar_size = inches_to_pixels(1.5)
    avatar_x = (sidebar_width - avatar_size) // 2
    avatar_y = inches_to_pixels(0.4)
    create_professional_avatar(draw, avatar_x, avatar_y, avatar_size, 
                               data.get("name", "Candidate"), data.get("gender", "neutral"))
    
    contact_y = inches_to_pixels(2.2)
    add_text_box(draw, inches_to_pixels(0.4), contact_y, inches_to_pixels(2.2), 
                inches_to_pixels(0.3), "CONTACT", font_size=26, bold=True, color=COLOR_NAVY)
    
    phone = data.get('phone', '')
    if phone and phone not in ['Not specified', 'Not found', '']:
        add_text_box(draw, inches_to_pixels(0.4), contact_y + inches_to_pixels(0.35), 
                    inches_to_pixels(2.2), inches_to_pixels(0.25), f"Phone: {safe_str(phone)}", 
                    font_size=22, color=COLOR_GRAY)
    
    email = data.get('email', '')
    if email and email not in ['Not specified', 'Not found', '']:
        add_text_box(draw, inches_to_pixels(0.4), contact_y + inches_to_pixels(0.65), 
                    inches_to_pixels(2.2), inches_to_pixels(0.25), f"Email: {safe_str(email)}", 
                    font_size=22, color=COLOR_GRAY)
    
    location = data.get('location', '')
    if location and location not in ['Not specified', '']:
        add_text_box(draw, inches_to_pixels(0.4), contact_y + inches_to_pixels(0.95), 
                    inches_to_pixels(2.2), inches_to_pixels(0.25), f"Location: {safe_str(location)}", 
                    font_size=22, color=COLOR_GRAY)
    
    skills_y = contact_y + inches_to_pixels(1.8)
    add_text_box(draw, inches_to_pixels(0.4), skills_y, inches_to_pixels(2.2), 
                inches_to_pixels(0.3), "SKILLS", font_size=28, bold=True, color=COLOR_NAVY)
    
    skills = data.get('skills', [])
    skill_y = skills_y + inches_to_pixels(0.4)
    for skill in skills[:8]:
        if skill:
            skill_y = add_text_box(draw, inches_to_pixels(0.5), skill_y, inches_to_pixels(2.1), 
                                  inches_to_pixels(0.25), f"- {safe_str(skill)}", 
                                  font_size=20, color=COLOR_DARK)
            skill_y += inches_to_pixels(0.05)
        if skill_y > inches_to_pixels(7.0):
            break
    
    right_x = inches_to_pixels(3.3)
    content_width = width - right_x - inches_to_pixels(0.5)
    
    name = safe_str(data.get('name', 'Professional Candidate')).upper()
    add_text_box(draw, right_x, inches_to_pixels(0.5), inches_to_pixels(6.2), 
                inches_to_pixels(0.7), name, font_size=48, bold=True, color=COLOR_NAVY)
    
    role = safe_str(data.get('current_role', 'Professional'))
    add_text_box(draw, right_x, inches_to_pixels(1.1), inches_to_pixels(6.2), 
                inches_to_pixels(0.4), role, font_size=32, color=COLOR_GOLD)
    
    divider_y = inches_to_pixels(1.55)
    draw.rectangle([right_x, divider_y, right_x + inches_to_pixels(6.2), divider_y + inches_to_pixels(0.02)], 
                  fill=COLOR_GOLD)
    
    summary_y = inches_to_pixels(1.8)
    add_text_box(draw, right_x, summary_y, inches_to_pixels(3), inches_to_pixels(0.4), 
                "PROFESSIONAL SUMMARY", font_size=28, bold=True, color=COLOR_NAVY)
    draw.rectangle([right_x, summary_y + inches_to_pixels(0.35), 
                   right_x + inches_to_pixels(0.8), summary_y + inches_to_pixels(0.38)], 
                  fill=COLOR_GOLD)
    
    summary = safe_str(data.get('professional_summary', ''))
    if len(summary) > 400:
        summary = summary[:400] + "..."
    
    add_text_box(draw, right_x, summary_y + inches_to_pixels(0.45), inches_to_pixels(6.2), 
                inches_to_pixels(0.9), summary, font_size=24, color=COLOR_GRAY)
    
    exp_y = inches_to_pixels(2.8)
    add_text_box(draw, right_x, exp_y, inches_to_pixels(3), inches_to_pixels(0.4), 
                "WORK EXPERIENCE", font_size=28, bold=True, color=COLOR_NAVY)
    draw.rectangle([right_x, exp_y + inches_to_pixels(0.35), 
                   right_x + inches_to_pixels(1.2), exp_y + inches_to_pixels(0.38)], 
                  fill=COLOR_GOLD)
    
    experiences = data.get('latest_3_experiences', [])
    exp_item_y = exp_y + inches_to_pixels(0.45)
    
    for idx, exp in enumerate(experiences[:3]):
        if exp_item_y > inches_to_pixels(6.2):
            break
        
        company = safe_str(exp.get('company', 'Company Name'))
        role = safe_str(exp.get('role', 'Position'))
        company_role_text = f"{role}  |  {company}"
        exp_item_y = add_text_box(draw, right_x, exp_item_y, inches_to_pixels(5), 
                                 inches_to_pixels(0.3), company_role_text, 
                                 font_size=24, bold=True, color=COLOR_NAVY)
        
        duration = safe_str(exp.get('duration', 'Date Range'))
        add_text_box(draw, right_x + inches_to_pixels(4.5), exp_item_y - inches_to_pixels(0.3), 
                    inches_to_pixels(1.7), inches_to_pixels(0.3), duration, 
                    font_size=22, color=COLOR_GRAY, align="right")
        
        responsibilities = exp.get('responsibilities', [])
        for resp in responsibilities[:3]:
            if resp:
                resp_text = safe_str(resp)
                if len(resp_text) > 70:
                    resp_text = resp_text[:67] + "..."
                exp_item_y = add_text_box(draw, right_x + inches_to_pixels(0.15), exp_item_y, 
                                         inches_to_pixels(6), inches_to_pixels(0.25), 
                                         f"- {resp_text}", font_size=19, color=COLOR_DARK)
        
        exp_item_y += inches_to_pixels(0.2)
    
    if exp_item_y < inches_to_pixels(6.0):
        edu_y = exp_item_y + inches_to_pixels(0.1)
        add_text_box(draw, right_x, edu_y, inches_to_pixels(3), inches_to_pixels(0.4), 
                    "EDUCATION", font_size=28, bold=True, color=COLOR_NAVY)
        draw.rectangle([right_x, edu_y + inches_to_pixels(0.35), 
                       right_x + inches_to_pixels(0.8), edu_y + inches_to_pixels(0.38)], 
                      fill=COLOR_GOLD)
        
        education = data.get('education', {})
        if education:
            degree = safe_str(education.get('degree', 'Degree'))
            institution = safe_str(education.get('institution', 'Institution'))
            year = safe_str(education.get('year', 'Year'))
            edu_text = f"{degree}  |  {institution}"
            add_text_box(draw, right_x, edu_y + inches_to_pixels(0.45), inches_to_pixels(5), 
                        inches_to_pixels(0.3), edu_text, font_size=20, bold=True, color=COLOR_NAVY)
            
            add_text_box(draw, right_x + inches_to_pixels(4.5), edu_y + inches_to_pixels(0.45), 
                        inches_to_pixels(1.7), inches_to_pixels(0.3), year, 
                        font_size=16, color=COLOR_GRAY, align="right")
    
    fit_score = data.get('fit_score', 85)
    if fit_score is None:
        fit_score = 85
    
    badge_size = inches_to_pixels(0.8)
    badge_x = width - badge_size - inches_to_pixels(0.5)
    badge_y = inches_to_pixels(0.4)
    
    if fit_score >= 80:
        score_color = (46, 204, 113)
    elif fit_score >= 60:
        score_color = (241, 196, 15)
    else:
        score_color = (231, 76, 60)
    
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], fill=score_color)
    
    try:
        font_large = get_font(52, bold=True)
    except:
        font_large = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), str(fit_score), font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text((badge_x + (badge_size - text_width) // 2, badge_y + (badge_size - text_height) // 2 - 10), 
              str(fit_score), fill=COLOR_WHITE, font=font_large)
    
    try:
        font_small = get_font(14)
    except:
        font_small = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), "FIT SCORE", font=font_small)
    text_width = bbox[2] - bbox[0]
    draw.text((badge_x + (badge_size - text_width) // 2, badge_y + badge_size - inches_to_pixels(0.25)), 
              "FIT SCORE", fill=COLOR_WHITE, font=font_small)
    
    footer_y = height - inches_to_pixels(0.3)
    footer_text = f"AI Resume Intelligence Report - Generated {datetime.now().strftime('%B %d, %Y')}"
    
    try:
        font_footer = get_font(12)
    except:
        font_footer = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), footer_text, font=font_footer)
    text_width = bbox[2] - bbox[0]
    draw.text((width // 2 - text_width // 2, footer_y), footer_text, fill=COLOR_GRAY, font=font_footer)
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path