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
    
    technical_skills = [
        'python', 'java', 'javascript', 'typescript', 'aws', 'azure', 'gcp',
        'sql', 'mongodb', 'postgresql', 'react', 'angular', 'vue', 'node',
        'docker', 'kubernetes', 'terraform', 'jenkins', 'git', 'ci/cd',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
        'django', 'flask', 'spring', '.net', 'c++', 'go', 'rust'
    ]
    found_skills = sum(1 for skill in technical_skills if skill in resume_lower)
    skills_score = min(40, (found_skills / 8) * 40) if found_skills > 0 else 15
    
    exp_years = structured_data.get('total_experience_years', 0)
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
    
    current_role = structured_data.get('current_role', '').lower()
    senior_indicators = ['senior', 'lead', 'architect', 'manager', 'principal', 'staff']
    has_senior = any(word in current_role for word in senior_indicators)
    role_score = 20 if has_senior else 10
    
    achievements = structured_data.get('latest_3_experiences', [])
    has_quantifiable = False
    quantifiers = ['%', 'increased', 'reduced', 'saved', 'launched', 
                  'built', 'created', 'improved', 'optimized', 'delivered']
    for exp in achievements:
        for resp in exp.get('responsibilities', []):
            if any(word in resp.lower() for word in quantifiers):
                has_quantifiable = True
                break
        if has_quantifiable:
            break
    achievement_score = 10 if has_quantifiable else 5
    
    final_score = int(skills_score + exp_score + role_score + achievement_score)
    return max(0, min(100, final_score))


def calculate_quality_score(structured_data, extracted_text):
    """Calculate RESUME QUALITY score - more strict"""
    resume_lower = extracted_text.lower()
    score = 100
    
    # Deductions
    if 'gap' in resume_lower or 'break' in resume_lower:
        score -= 15  # Career gaps detected
    
    # Check for missing dates
    import re
    has_years = bool(re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', extracted_text))
    if not has_years:
        score -= 15
    
    # Check for employment gaps in data
    experiences = structured_data.get('latest_3_experiences', [])
    if len(experiences) < 3:
        score -= 10
    
    # Check for education completeness
    edu = structured_data.get('education', {})
    if not edu.get('year') or edu.get('year') == 'Not Specified':
        score -= 10
    
    return max(0, min(100, score))

def get_quality_verdict(score):
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

@app.route("/api/upload", methods=["POST"])
def upload_resume():
    try:
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
        
        # Analyze with LLM
        structured_data = analyze_resume(extracted_text)
        
        # Calculate scores
        fit_score = calculate_fit_score(structured_data, extracted_text)
        quality_score = calculate_quality_score(structured_data, extracted_text)
        
        structured_data['fit_score'] = fit_score
        structured_data['resume_quality_score'] = quality_score
        structured_data['resume_quality_verdict'] = get_quality_verdict(quality_score)
        
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
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)

        # After getting structured_data, add this debug
        print(f"Quality Score: {quality_score}")
        print(f"Will use template: {'professional' if quality_score >= 50 else 'poor' if quality_score >= 30 else 'worst'}")
        
        # Generate PNG
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename))
        
        with open(png_path, 'rb') as f:
            png_bytes = f.read()
        image_base64 = base64.b64encode(png_bytes).decode('utf-8')
        
        # Clean up
        os.remove(file_path)
        os.remove(png_path)
        
        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_base64": image_base64,
            "fit_score": fit_score,
            "gap_analysis": gap_analysis
        }), 200
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# Vercel requires this
app = app