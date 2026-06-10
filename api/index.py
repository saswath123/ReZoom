import sys
import os

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import base64
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from extractor import extract_resume_text
from llm_parser import analyze_resume
from image_generator import generate_resume_image
from gap_analyzer import GapAnalyzer

# Aggressive scoring for unprofessional resumes
UNPROFESSIONAL_KEYWORDS = {
    'urgent': 30, 'urgently': 35, 'bored': 40, 'bored at home': 45,
    'please hire': 40, 'please hire me': 45, 'genius': 35,
    'can do any job': 40, 'whatsapp': 25, 'instagram': 25,
    'youtube': 20, 'gaming': 25, 'sleeping': 30, 'timepass': 35,
    "don't remember": 30, 'some school': 35, 'some college': 35,
    'need job': 30, 'tiktok': 25, 'pubg': 25, 'chicken dinner': 30,
    'facebook': 20
}

def detect_unprofessional_score(extracted_text):
    """Detect if resume is unprofessional and return score"""
    text_lower = extracted_text.lower()
    score = 0
    for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items():
        if keyword in text_lower:
            score += penalty
    return score

def is_worst_resume(extracted_text):
    """Check if resume is worst quality"""
    score = detect_unprofessional_score(extracted_text)
    return score > 50, score

app = Flask(__name__)
CORS(app)

# Configuration for Vercel (use /tmp for temporary storage)
UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/generated_images"
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE = 4 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# SCORE CALCULATION FUNCTIONS
# ============================================================

def calculate_fit_score(structured_data, extracted_text):
    """Calculate JOB FIT score - based on skills, experience, role match only"""
    resume_lower = extracted_text.lower()
    
    # Check if worst resume first
    is_worst, unscore = is_worst_resume(extracted_text)
    if is_worst:
        print(f"⚠️ Worst resume detected! Unprofessional score: {unscore}")
        return 15
    
    # 1. Skills Match (40% weight)
    technical_skills = [
        'python', 'java', 'javascript', 'typescript', 'aws', 'azure', 'gcp',
        'sql', 'mongodb', 'postgresql', 'react', 'angular', 'vue', 'node',
        'docker', 'kubernetes', 'terraform', 'jenkins', 'git', 'ci/cd',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
        'django', 'flask', 'spring', '.net', 'c++', 'go', 'rust'
    ]
    found_skills = sum(1 for skill in technical_skills if skill in resume_lower)
    skills_score = min(40, (found_skills / 8) * 40) if found_skills > 0 else 15
    
    # 2. Experience Match (30% weight)
    exp_years = structured_data.get('total_experience_years', 0)
    if exp_years is None:
        exp_years = 0
    try:
        exp_years = int(exp_years)
    except (ValueError, TypeError):
        exp_years = 0
    
    if exp_years >= 8:
        exp_score = 30
    elif exp_years >= 5:
        exp_score = 25
    elif exp_years >= 3:
        exp_score = 20
    elif exp_years >= 1:
        exp_score = 12
    else:
        exp_score = 5
    
    # 3. Role Alignment (20% weight)
    current_role = structured_data.get('current_role', '')
    if current_role is None:
        current_role = ''
    current_role = current_role.lower()
    senior_indicators = ['senior', 'lead', 'architect', 'manager', 'principal', 'staff']
    has_senior = any(word in current_role for word in senior_indicators)
    role_score = 20 if has_senior else 10
    
    # 4. Achievements Quality (10% weight)
    achievements = structured_data.get('latest_3_experiences', [])
    if achievements is None:
        achievements = []
    has_quantifiable = False
    quantifiers = ['%', 'increased', 'reduced', 'saved', 'launched', 
                  'built', 'created', 'improved', 'optimized', 'delivered']
    for exp in achievements:
        if exp is None:
            continue
        for resp in exp.get('responsibilities', []):
            if resp is None:
                continue
            if any(word in resp.lower() for word in quantifiers):
                has_quantifiable = True
                break
        if has_quantifiable:
            break
    achievement_score = 10 if has_quantifiable else 5
    
    final_score = int(skills_score + exp_score + role_score + achievement_score)
    return max(0, min(100, final_score))


def calculate_quality_score(structured_data, extracted_text):
    """Calculate RESUME QUALITY score - with None handling"""
    resume_lower = extracted_text.lower()
    
    # Check if worst resume first
    is_worst, unscore = is_worst_resume(extracted_text)
    if is_worst:
        print(f"⚠️ Worst resume detected! Quality score forced to 15")
        return 15
    
    score = 100
    
    # Check for missing dates
    has_years = bool(re.search(r'\b(19[0-9]{2}|20[0-2][0-9]|2030)\b', extracted_text))
    if not has_years:
        score -= 15
    
    # Check for employment gaps in data
    experiences = structured_data.get('latest_3_experiences', [])
    if experiences is None:
        experiences = []
    if len(experiences) < 1:
        score -= 25
    
    # Check for education completeness
    edu = structured_data.get('education', {})
    if edu is None:
        edu = {}
    year = edu.get('year', '')
    if year is None:
        year = ''
    if not year or year in ['Not Specified', 'None', '']:
        score -= 10
    
    # Check for contact info
    email = structured_data.get('email', '')
    phone = structured_data.get('phone', '')
    if not email or email in ['Not Provided', 'Not found', '']:
        score -= 10
    if not phone or phone in ['Not Provided', 'Not found', '']:
        score -= 10
    
    # Check for generic skills
    generic_skills = ['communication', 'teamwork', 'problem solving', 'leadership']
    skills = structured_data.get('skills', [])
    if skills and all(skill.lower() in generic_skills for skill in skills[:3]):
        score -= 15
    
    return max(0, min(100, score))


def get_quality_verdict(score):
    if score is None:
        return "Average"
    if score >= 90:
        return "Excellent"
    elif score >= 70:
        return "Good"
    elif score >= 50:
        return "Average"
    elif score >= 30:
        return "Poor"
    else:
        return "Worst"


# ============================================================
# MAIN ROUTES
# ============================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.route("/api/version", methods=["GET"])
def version():
    return jsonify({
        "version": "2026-06-10-v7",
        "status": "active",
        "message": "AI Resume Parser is running with worst resume detection"
    })


@app.route("/api/upload", methods=["POST"])
def upload_resume():
    try:
        print("=" * 50)
        print("New upload request received")
        
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["resume"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PDF or DOCX"}), 400
        
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)
        
        extracted_text = extract_resume_text(file_path)
        print(f"Extracted text length: {len(extracted_text)} chars")
        
        # Check for worst resume BEFORE LLM call
        is_worst, unscore = is_worst_resume(extracted_text)
        print(f"Unprofessional score: {unscore}, Is worst: {is_worst}")
        
        # Analyze with LLM
        structured_data = analyze_resume(extracted_text)
        
        # Force low scores for worst resumes
        if is_worst:
            structured_data['fit_score'] = 15
            structured_data['resume_quality_score'] = 15
            structured_data['resume_quality_verdict'] = "Worst"
            structured_data['red_flags'] = {
                "poor_formatting": True,
                "missing_contact_info": True,
                "unprofessional_content": True,
                "generic_skills": True,
                "no_work_experience": True,
                "vague_descriptions": True,
                "unprofessional_language": True,
                "missing_dates": True,
                "over_exaggeration": True,
                "spelling_grammar_issues": True,
                "incomplete_education": True,
                "irrelevant_skills": True,
                "desperate_tone": True
            }
            structured_data['quality_observations'] = [
                "⚠️ CRITICAL: Resume contains extremely unprofessional content",
                "⚠️ No valid work experience with proper details",
                "⚠️ Skills listed are completely irrelevant for professional work",
                "⚠️ Contains desperate and unprofessional tone",
                "⚠️ Complete resume rewrite is strongly recommended"
            ]
        else:
            # Calculate scores normally
            fit_score = calculate_fit_score(structured_data, extracted_text)
            quality_score = calculate_quality_score(structured_data, extracted_text)
            
            structured_data['fit_score'] = fit_score
            structured_data['resume_quality_score'] = quality_score
            structured_data['resume_quality_verdict'] = get_quality_verdict(quality_score)
        
        print(f"Final Fit Score: {structured_data.get('fit_score')}")
        print(f"Final Quality Score: {structured_data.get('resume_quality_score')}")
        print(f"Quality Verdict: {structured_data.get('resume_quality_verdict')}")
        
        # Extract email and phone if missing
        if structured_data.get('email') in [None, 'Not Provided', 'Not found', '']:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', extracted_text)
            if email_match:
                structured_data['email'] = email_match.group()
        
        if structured_data.get('phone') in [None, 'Not Provided', 'Not found', '']:
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', extracted_text)
            if phone_match:
                structured_data['phone'] = phone_match.group()
        
        # Gap Analysis
        gap_analyzer = GapAnalyzer()
        education_raw = structured_data.get('education_raw', [])
        experience_raw = structured_data.get('experience_raw', [])
        if education_raw is None:
            education_raw = []
        if experience_raw is None:
            experience_raw = []
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)
        
        # Generate PNG image
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename))
        
        with open(png_path, 'rb') as f:
            png_bytes = f.read()
        image_base64 = base64.b64encode(png_bytes).decode('utf-8')
        
        # Clean up
        try:
            os.remove(file_path)
            os.remove(png_path)
        except:
            pass
        
        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_base64": image_base64,
            "fit_score": structured_data.get('fit_score'),
            "gap_analysis": gap_analysis
        }), 200
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


# For local development
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)