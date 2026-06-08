from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
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

# Configuration
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "generated_images"
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
MAX_FILE_SIZE = 4 * 1024 * 1024  # 4MB for Vercel

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
    
    print("=" * 50)
    print("Calculating Fit Score:")
    
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
    print(f"  Skills found: {found_skills} -> Score: {skills_score:.1f}/40")
    
    # 2. Experience Match (30% weight)
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
    print(f"  Experience years: {exp_years} -> Score: {exp_score}/30")
    
    # 3. Role Alignment (20% weight)
    current_role = structured_data.get('current_role', '').lower()
    senior_indicators = ['senior', 'lead', 'architect', 'manager', 'principal', 'staff', 'head']
    has_senior = any(word in current_role for word in senior_indicators)
    role_score = 20 if has_senior else 10
    print(f"  Senior role: {has_senior} -> Score: {role_score}/20")
    
    # 4. Achievements Quality (10% weight)
    achievements = structured_data.get('latest_3_experiences', [])
    has_quantifiable = False
    quantifiers = ['%', 'increased', 'reduced', 'saved', 'launched', 
                  'built', 'created', 'improved', 'optimized', 'delivered',
                  'million', 'thousand', 'percent', 'led', 'managed']
    
    for exp in achievements:
        for resp in exp.get('responsibilities', []):
            resp_lower = resp.lower()
            if any(word in resp_lower for word in quantifiers):
                has_quantifiable = True
                break
        if has_quantifiable:
            break
    achievement_score = 10 if has_quantifiable else 5
    print(f"  Quantifiable achievements: {has_quantifiable} -> Score: {achievement_score}/10")
    
    # Calculate final fit score
    final_score = int(skills_score + exp_score + role_score + achievement_score)
    final_score = max(0, min(100, final_score))
    print(f"Final Fit Score: {final_score}")
    print("=" * 50)
    
    return final_score

def calculate_quality_score(structured_data, extracted_text):
    """Calculate RESUME QUALITY score - based on professionalism only"""
    resume_lower = extracted_text.lower()
    score = 100
    
    print("=" * 50)
    print("Calculating Quality Score:")
    
    # 1. Check for unprofessional language (-20 to -40)
    unprofessional_phrases = [
        'bored', 'urgently', 'please hire', 'genius', 'can do any job',
        'hardworking', 'timepass', 'chilling', 'lazy'
    ]
    for phrase in unprofessional_phrases:
        if phrase in resume_lower:
            score -= 25
            print(f"  - Unprofessional language detected: '{phrase}' (-25)")
            break
    
    # 2. Check for irrelevant skills (-20)
    irrelevant_skills = ['whatsapp', 'instagram', 'youtube', 'gaming', 'sleeping', 
                         'tiktok', 'facebook', 'pubg', 'freefire', 'netflix']
    for skill in irrelevant_skills:
        if skill in resume_lower:
            score -= 20
            print(f"  - Irrelevant skill detected: '{skill}' (-20)")
            break
    
    # 3. Check for missing contact info (-15)
    email = structured_data.get('email', '')
    phone = structured_data.get('phone', '')
    has_email = email not in [None, '', 'Not Provided', 'Not found', 'Not specified']
    has_phone = phone not in [None, '', 'Not Provided', 'Not found', 'Not specified']
    
    if not has_email or not has_phone:
        score -= 15
        print(f"  - Missing contact info: email={has_email}, phone={has_phone} (-15)")
    
    # 4. Check for missing dates (-15)
    import re
    has_years = bool(re.search(r'\b(19[0-9]{2}|20[0-2][0-9]|2030)\b', extracted_text))
    if not has_years:
        score -= 15
        print(f"  - Missing dates in resume (-15)")
    
    # 5. Check for no work experience (-35)
    experiences = structured_data.get('latest_3_experiences', [])
    if not experiences or len(experiences) == 0:
        score -= 35
        print(f"  - No work experience documented (-35)")
    
    # 6. Check for vague descriptions (-15)
    vague_phrases = [
        'worked in many companies', 'don\'t remember', 'did many things',
        'various tasks', 'responsible for', 'assisted with'
    ]
    for phrase in vague_phrases:
        if phrase in resume_lower:
            score -= 15
            print(f"  - Vague description detected (-15)")
            break
    
    # 7. Check for incomplete education (-10)
    education = structured_data.get('education', {})
    has_degree = education.get('degree') not in [None, '', 'Not Specified']
    has_institution = education.get('institution') not in [None, '', 'Not Specified']
    if not has_degree or not has_institution:
        score -= 10
        print(f"  - Incomplete education section (-10)")
    
    # 8. Check for poor formatting (-10)
    if len(extracted_text) < 100:
        score -= 10
        print(f"  - Resume too short/poor formatting (-10)")
    
    # Ensure score is within bounds
    final_score = max(0, min(100, score))
    print(f"Final Quality Score: {final_score}")
    print("=" * 50)
    
    return final_score

def get_quality_verdict(score):
    """Get quality verdict based on score"""
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
# UNPROFESSIONAL CONTENT DETECTION
# ============================================================

UNPROFESSIONAL_KEYWORDS = {
    'urgent': 30,
    'urgently': 35,
    'bored': 40,
    'bored at home': 45,
    'please hire': 40,
    'please hire me': 45,
    'genius': 35,
    'can do any job': 40,
    'whatsapp': 25,
    'instagram': 25,
    'youtube': 20,
    'gaming': 25,
    'sleeping': 30,
    'timepass': 35,
    "don't remember": 30,
    'some school': 35,
    'some college': 35,
    'need job': 30,
}

def is_unprofessional_resume(resume_text):
    """Check if resume is clearly unprofessional"""
    resume_lower = resume_text.lower()
    strong_indicators = [
        'bored', 'bored at home', 'please hire', 'whatsapp', 'instagram',
        'gaming', 'sleeping', 'timepass', "don't remember", 'some school'
    ]
    for indicator in strong_indicators:
        if indicator in resume_lower:
            return True
    return False


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():
    return jsonify({
        "status": "active",
        "message": "Intelligent Resume Parser AI API",
        "version": "2.0"
    })


@app.route("/upload", methods=["POST"])
def upload_resume():
    try:
        print("=" * 50)
        print("New upload request received")
        
        # Check if file exists
        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files["resume"]
        
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PDF or DOCX"}), 400
        
        # Save file
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)
        
        # Extract text
        extracted_text = extract_resume_text(file_path)
        print(f"Extracted text length: {len(extracted_text)} chars")
        
        # Check if unprofessional resume
        is_unprofessional = is_unprofessional_resume(extracted_text)
        print(f"Is unprofessional resume: {is_unprofessional}")
        
        # Analyze with LLM
        if is_unprofessional:
            print("Unprofessional resume detected - using fallback data")
            from llm_parser import generate_fallback_data
            structured_data = generate_fallback_data(extracted_text)
        else:
            print("Calling LLM for analysis...")
            structured_data = analyze_resume(extracted_text)
        
        # ============================================================
        # CALCULATE SEPARATE SCORES
        # ============================================================
        fit_score = calculate_fit_score(structured_data, extracted_text)
        quality_score = calculate_quality_score(structured_data, extracted_text)
        
        # Add scores to structured_data
        structured_data['fit_score'] = fit_score
        structured_data['resume_quality_score'] = quality_score
        structured_data['resume_quality_verdict'] = get_quality_verdict(quality_score)
        
        print(f"Fit Score: {fit_score}")
        print(f"Quality Score: {quality_score}")
        
        # Extract email and phone if missing
        if structured_data.get('email') in [None, 'Not Provided', 'Not found', '']:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', extracted_text)
            if email_match:
                structured_data['email'] = email_match.group()
        
        if structured_data.get('phone') in [None, 'Not Provided', 'Not found', '']:
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', extracted_text)
            if phone_match:
                structured_data['phone'] = phone_match.group()
        
        # Perform Gap Analysis
        gap_analyzer = GapAnalyzer()
        education_raw = structured_data.get('education_raw', [])
        experience_raw = structured_data.get('experience_raw', [])
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)
        
        # Generate PNG image
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename))
        
        # Convert to Base64
        with open(png_path, 'rb') as f:
            png_bytes = f.read()
        image_base64 = base64.b64encode(png_bytes).decode('utf-8')
        
        # Clean up uploaded file
        os.remove(file_path)
        
        # Return response
        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_base64": image_base64,
            "image_download_url": f"/download/{png_filename}",
            "fit_score": fit_score,
            "gap_analysis": gap_analysis
        }), 200
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route("/download/<filename>")
def download_image(filename):
    try:
        image_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(image_path):
            return send_file(image_path, as_attachment=True, download_name=filename, mimetype='image/png')
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)