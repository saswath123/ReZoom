from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

def safe_str(value):
    """Convert None to empty string safely"""
    return str(value) if value is not None else ""

def get_font(size, bold=False):
    """Get Helvetica font - Mac/Linux compatible"""
    # Helvetica font paths (priority order)
    helvetica_paths = [
        # Mac paths
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttf",
        "/Library/Fonts/Helvetica.ttf",
        # Linux paths
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        # Windows paths
        "C:/Windows/Fonts/Helvetica.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ]
    helvetica_bold_paths = [
        # Mac paths
        "/System/Library/Fonts/Helvetica-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        # Linux paths
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        # Windows paths
        "C:/Windows/Fonts/Helvetica-Bold.ttf",
        "C:/Windows/Fonts/Arialbd.ttf",
    ]
    
    paths = helvetica_bold_paths if bold else helvetica_paths
    
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    
    # Final fallback
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
    """Wrap text to fit within max_width"""
    if not text:
        return []
    
    words = text.split()
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


def generate_resume_image(data, gap_analysis, output_path):
    """Generate professional resume image"""
    return generate_professional_template(data, gap_analysis, output_path)


def generate_professional_template(data, gap_analysis, output_path):
    """Generate a clean, professional corporate resume using Helvetica font"""
    
    # Canvas size
    width = 1920
    height = 1350
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # Color palette
    NAVY = (26, 35, 80)
    GOLD = (212, 175, 55)
    GRAY_DARK = (51, 51, 51)
    GRAY_MEDIUM = (102, 102, 102)
    GRAY_LIGHT = (245, 245, 245)
    WHITE = (255, 255, 255)
    LINE_COLOR = (212, 175, 55)
    
    # Helvetica fonts
    FONT_NAME = get_font(53, bold=True)
    FONT_ROLE = get_font(33, bold=True)
    FONT_SECTION = get_font(27, bold=True)
    FONT_SUBHEADING = get_font(23, bold=True)
    FONT_BODY = get_font(21)
    FONT_SMALL = get_font(18)
    FONT_FOOTER = get_font(16)
    
    # ===== LEFT PANEL =====
    panel_width = 520
    draw.rectangle([0, 0, panel_width, height], fill=NAVY)
    
    # Name
    name = safe_str(data.get('name', 'Professional')).upper()
    draw.text((45, 55), name, fill=WHITE, font=FONT_NAME)
    
    # Role
    role = safe_str(data.get('current_role', 'Professional'))
    draw.text((45, 115), role, fill=GOLD, font=FONT_ROLE)
    
    # Divider
    draw.line([(45, 150), (panel_width - 45, 150)], fill=GOLD, width=2)
    
    # Contact Information
    y = 180
    draw.text((45, y), "CONTACT", fill=GOLD, font=FONT_SECTION)
    y += 35
    
    phone = safe_str(data.get('phone', ''))
    if phone and phone not in ['Not Provided', 'Not found', '']:
        draw.text((45, y), f"T: {phone}", fill=WHITE, font=FONT_SMALL)
        y += 28
    
    email = safe_str(data.get('email', ''))
    if email and email not in ['Not Provided', 'Not found', '']:
        draw.text((45, y), f"E: {email}", fill=WHITE, font=FONT_SMALL)
        y += 28
    
    location = safe_str(data.get('location', ''))
    if location and location not in ['Not Specified', '']:
        draw.text((45, y), f"L: {location}", fill=WHITE, font=FONT_SMALL)
        y += 40
    
    # Skills
    draw.text((45, y), "SKILLS", fill=GOLD, font=FONT_SECTION)
    y += 35
    
    skills = data.get('skills', [])
    for skill in skills[:12]:
        draw.text((45, y), f"- {skill}", fill=WHITE, font=FONT_SMALL)
        y += 24
        if y > 800:
            break
    
    # ===== RIGHT PANEL =====
    right_x = panel_width + 50
    max_width = width - right_x - 45
    
    # Professional Summary
    draw.text((right_x, 55), "PROFESSIONAL SUMMARY", fill=NAVY, font=FONT_SECTION)
    draw.line([(right_x, 85), (right_x + 180, 85)], fill=LINE_COLOR, width=2)
    
    summary = safe_str(data.get('professional_summary', ''))
    y = 110
    for line in wrap_text(draw, summary, FONT_BODY, max_width)[:5]:
        draw.text((right_x, y), line, fill=GRAY_MEDIUM, font=FONT_BODY)
        y += 26
    
    # Work Experience
    y += 30
    draw.text((right_x, y), "WORK EXPERIENCE", fill=NAVY, font=FONT_SECTION)
    draw.line([(right_x, y + 30), (right_x + 200, y + 30)], fill=LINE_COLOR, width=2)
    y += 55
    
    experiences = data.get('latest_3_experiences', [])
    for exp in experiences[:3]:
        if y > 950:
            break
        
        role = safe_str(exp.get('role', ''))
        company = safe_str(exp.get('company', ''))
        duration = safe_str(exp.get('duration', ''))
        
        # Job title
        draw.text((right_x, y), f"{role}", fill=NAVY, font=FONT_SUBHEADING)
        
        # Company and duration on same line
        draw.text((right_x, y + 28), company, fill=GRAY_DARK, font=FONT_BODY)
        draw.text((width - 200, y + 28), duration, fill=GOLD, font=FONT_SMALL)
        
        y += 60
        
        # Responsibilities
        for resp in exp.get('responsibilities', [])[:3]:
            resp_text = safe_str(resp)[:95]
            draw.text((right_x + 18, y), "-", fill=GOLD, font=FONT_BODY)
            draw.text((right_x + 35, y), resp_text, fill=GRAY_DARK, font=FONT_BODY)
            y += 28
        
        y += 15
    
    # Education
    if y < 1000:
        draw.text((right_x, y), "EDUCATION", fill=NAVY, font=FONT_SECTION)
        draw.line([(right_x, y + 30), (right_x + 150, y + 30)], fill=LINE_COLOR, width=2)
        y += 55
        
        edu = data.get('education', {})
        degree = safe_str(edu.get('degree', ''))
        institution = safe_str(edu.get('institution', ''))
        year = safe_str(edu.get('year', ''))
        
        if degree:
            draw.text((right_x, y), degree, fill=NAVY, font=FONT_SUBHEADING)
            if year and year not in ['Not Specified', '']:
                draw.text((width - 150, y), year, fill=GOLD, font=FONT_SMALL)
            y += 32
            draw.text((right_x, y), institution, fill=GRAY_MEDIUM, font=FONT_BODY)
            y += 30
    
    # Quality Score Badge
    quality_score = data.get('resume_quality_score', 80)
    if quality_score >= 80:
        badge_color = (46, 204, 113)
    elif quality_score >= 60:
        badge_color = (241, 196, 15)
    else:
        badge_color = (231, 76, 60)
    
    badge_size = 85
    badge_x = width - badge_size - 25
    badge_y = 25
    
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], fill=badge_color)
    draw.text((badge_x + 28, badge_y + 28), str(quality_score), fill=WHITE, font=get_font(34, bold=True))
    draw.text((badge_x + 18, badge_y + 62), "QUALITY", fill=WHITE, font=FONT_SMALL)
    
    # Footer
    footer_text = f"AI Resume Intelligence Report - Generated {datetime.now().strftime('%B %d, %Y')}"
    draw.text((width // 2 - 230, height - 35), footer_text, fill=GRAY_MEDIUM, font=FONT_FOOTER)
    
    # Save
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path


# For testing
if __name__ == "__main__":
    test_data = {
        "name": "Rajesh Kumar",
        "current_role": "Senior Software Engineer",
        "phone": "+1 234 567 8900",
        "email": "rajesh@example.com",
        "location": "San Francisco, CA",
        "skills": ["Python", "JavaScript", "React", "Node.js", "AWS", "Docker"],
        "professional_summary": "Experienced software engineer with 8+ years of experience building scalable web applications.",
        "latest_3_experiences": [
            {
                "role": "Senior Software Engineer",
                "company": "Google",
                "duration": "2022 - Present",
                "responsibilities": ["Led team of 5 engineers", "Improved performance by 40%"]
            },
            {
                "role": "Software Engineer",
                "company": "Microsoft",
                "duration": "2019 - 2022",
                "responsibilities": ["Built microservices", "Reduced costs by 30%"]
            }
        ],
        "education": {
            "degree": "M.Tech in Computer Science",
            "institution": "IIT Bombay",
            "year": "2019"
        },
        "resume_quality_score": 85
    }
    
    generate_resume_image(test_data, None, "test_output.png")
    print("Test image generated: test_output.png")