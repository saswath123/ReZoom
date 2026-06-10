from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime

def safe_str(value):
    return str(value) if value is not None else ""


def get_font(size, bold=False):
    """Get font compatible with Vercel (Linux) environment"""
    
    # Fonts available on Vercel Linux (in priority order)
    if bold:
        bold_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica-Bold.ttf",  # Mac fallback
        ]
        for path in bold_fonts:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    regular_fonts = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",  # Mac fallback
    ]
    
    for path in regular_fonts:
        try:
            return ImageFont.truetype(path, size)
        except:
            continue
    
    return ImageFont.load_default()


def wrap_text(draw, text, font, max_width):
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
    return generate_professional_template(data, gap_analysis, output_path)


def generate_professional_template(data, gap_analysis, output_path):
    width = 1920
    height = 1350
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    NAVY = (26, 35, 80)
    GOLD = (212, 175, 55)
    GRAY_DARK = (51, 51, 51)
    GRAY_MEDIUM = (102, 102, 102)
    WHITE = (255, 255, 255)
    LIGHT_GRAY = (248, 248, 248)
    
    FONT_NAME = get_font(44, bold=True)
    FONT_ROLE = get_font(24, bold=True)
    FONT_SECTION = get_font(20, bold=True)
    FONT_SUBHEADING = get_font(18, bold=True)
    FONT_BODY = get_font(15, bold=False)
    FONT_SMALL = get_font(13, bold=False)
    FONT_FOOTER = get_font(11, bold=False)
    
    # LEFT PANEL
    panel_width = 480
    draw.rectangle([0, 0, panel_width, height], fill=LIGHT_GRAY)
    
    name = safe_str(data.get('name', 'RAJESH VERMA')).upper()
    draw.text((40, 50), name, fill=NAVY, font=FONT_NAME)
    
    role = safe_str(data.get('current_role', 'Senior Full Stack Engineer | Cloud Architect'))
    draw.text((40, 110), role, fill=GOLD, font=FONT_ROLE)
    
    y = 170
    draw.text((40, y), "CONTACT", fill=NAVY, font=FONT_SECTION)
    y += 35
    
    phone = safe_str(data.get('phone', ''))
    if phone and phone not in ['Not Provided', 'Not found', '']:
        draw.text((40, y), f"Phone: {phone}", fill=GRAY_DARK, font=FONT_SMALL)
        y += 28
    
    email = safe_str(data.get('email', ''))
    if email and email not in ['Not Provided', 'Not found', '']:
        draw.text((40, y), f"Email: {email}", fill=GRAY_DARK, font=FONT_SMALL)
        y += 28
    
    location = safe_str(data.get('location', ''))
    if location and location not in ['Not Specified', '']:
        draw.text((40, y), f"Location: {location}", fill=GRAY_DARK, font=FONT_SMALL)
        y += 40
    
    draw.text((40, y), "SKILLS", fill=NAVY, font=FONT_SECTION)
    y += 35
    
    skills = data.get('skills', [])
    for skill in skills[:12]:
        draw.text((40, y), f"- {skill}", fill=GRAY_DARK, font=FONT_SMALL)
        y += 24
        if y > 800:
            break
    
    # RIGHT PANEL
    right_x = panel_width + 50
    max_width = width - right_x - 50
    
    name_small = safe_str(data.get('name', 'RAJESH VERMA'))
    draw.text((right_x, 50), name_small, fill=NAVY, font=FONT_NAME)
    
    role_small = safe_str(data.get('current_role', 'Senior Full Stack Engineer | Cloud Architect'))
    draw.text((right_x, 100), role_small, fill=GOLD, font=FONT_ROLE)
    
    draw.line([(right_x, 140), (width - 50, 140)], fill=GOLD, width=2)
    
    y = 170
    draw.text((right_x, y), "PROFESSIONAL SUMMARY", fill=NAVY, font=FONT_SECTION)
    draw.line([(right_x, y + 25), (right_x + 180, y + 25)], fill=GOLD, width=2)
    y += 45
    
    summary = safe_str(data.get('professional_summary', ''))
    for line in wrap_text(draw, summary, FONT_BODY, max_width)[:4]:
        draw.text((right_x, y), line, fill=GRAY_MEDIUM, font=FONT_BODY)
        y += 26
    
    y += 30
    draw.text((right_x, y), "WORK EXPERIENCE", fill=NAVY, font=FONT_SECTION)
    draw.line([(right_x, y + 25), (right_x + 200, y + 25)], fill=GOLD, width=2)
    y += 50
    
    experiences = data.get('latest_3_experiences', [])
    for exp in experiences[:3]:
        if y > 1000:
            break
        
        role_exp = safe_str(exp.get('role', ''))
        company = safe_str(exp.get('company', ''))
        duration = safe_str(exp.get('duration', ''))
        
        draw.text((right_x, y), f"{role_exp} | {company}", fill=NAVY, font=FONT_SUBHEADING)
        if duration:
            draw.text((width - 200, y), duration, fill=GOLD, font=FONT_SMALL)
        y += 35
        
        for resp in exp.get('responsibilities', [])[:4]:
            resp_text = safe_str(resp)[:100]
            draw.text((right_x + 15, y), "-", fill=GOLD, font=FONT_BODY)
            draw.text((right_x + 32, y), resp_text, fill=GRAY_DARK, font=FONT_BODY)
            y += 26
        
        y += 15
    
    if y < 1050:
        draw.text((right_x, y), "EDUCATION", fill=NAVY, font=FONT_SECTION)
        draw.line([(right_x, y + 25), (right_x + 150, y + 25)], fill=GOLD, width=2)
        y += 50
        
        edu = data.get('education', {})
        degree = safe_str(edu.get('degree', ''))
        institution = safe_str(edu.get('institution', ''))
        
        if degree:
            draw.text((right_x, y), f"{degree} | {institution}", fill=NAVY, font=FONT_SUBHEADING)
    
    quality_score = data.get('resume_quality_score', 85)
    if quality_score >= 80:
        badge_color = (46, 204, 113)
    elif quality_score >= 60:
        badge_color = (241, 196, 15)
    else:
        badge_color = (231, 76, 60)
    
    badge_size = 80
    badge_x = width - badge_size - 30
    badge_y = 30
    
    draw.ellipse([badge_x, badge_y, badge_x + badge_size, badge_y + badge_size], fill=badge_color)
    draw.text((badge_x + 25, badge_y + 30), str(quality_score), fill=WHITE, font=get_font(32, bold=True))
    draw.text((badge_x + 15, badge_y + 62), "QUALITY", fill=WHITE, font=FONT_SMALL)
    
    footer_y = height - 40
    footer_text = f"AI Resume Intelligence Report - Generated {datetime.now().strftime('%B %d, %Y')}"
    draw.text((width // 2 - 240, footer_y), footer_text, fill=GRAY_MEDIUM, font=FONT_FOOTER)
    
    img.save(output_path, "PNG", dpi=(300, 300))
    return output_path