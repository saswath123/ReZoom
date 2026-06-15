import sys
import os
import hashlib
import time

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import base64
import re
from datetime import datetime
import traceback
from werkzeug.utils import secure_filename
from extractor import extract_resume_text, extract_profile_image
from llm_parser import analyze_resume
from image_generator import generate_resume_image
from gap_analyzer import GapAnalyzer
from role_matcher import (
    get_predefined_roles,
    get_role_requirements,
    extract_skills_from_jd,
    calculate_role_fit_score,
    build_skill_gap_report
)

# Cache to prevent duplicate submissions
RECENT_UPLOADS = {}  # file_hash -> timestamp

def is_duplicate_upload(file_storage):
    """Check if the file has been processed recently (within 15s) using MD5 hash"""
    try:
        # Read the file bytes, generate hash
        file_bytes = file_storage.read()
        file_storage.seek(0)  # Reset stream position so it can be saved later
        
        file_hash = hashlib.md5(file_bytes).hexdigest()
        now = time.time()
        
        # Clean up old hashes (older than 15 seconds)
        expired = [h for h, t in RECENT_UPLOADS.items() if now - t > 15]
        for h in expired:
            RECENT_UPLOADS.pop(h, None)
            
        if file_hash in RECENT_UPLOADS:
            return True
            
        RECENT_UPLOADS[file_hash] = now
        return False
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        return False

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

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def ensure_list_of_strings(val):
    if not val:
        return []
    if isinstance(val, list):
        return [str(item) for item in val if item]
    if isinstance(val, str):
        return [s.strip() for s in re.split(r'[,;\n]+', val) if s.strip()]
    return [str(val)]


def sanitize_skill_proficiency(skills):
    cleaned = []
    if isinstance(skills, list):
        for s in skills:
            if isinstance(s, dict):
                skill_name = str(s.get("skill") or s.get("name") or "")
                if skill_name:
                    try:
                        pct = int(s.get("percentage", 80) or 80)
                    except (ValueError, TypeError):
                        pct = 80
                    cleaned.append({
                        "skill": skill_name,
                        "percentage": pct,
                        "category": str(s.get("category") or "Other")
                    })
            elif isinstance(s, str) and s.strip():
                cleaned.append({
                    "skill": s.strip(),
                    "percentage": 80,
                    "category": "Other"
                })
    elif isinstance(skills, dict):
        for k, v in skills.items():
            try:
                pct = int(v) if v is not None else 80
            except (ValueError, TypeError):
                pct = 80
            cleaned.append({
                "skill": str(k),
                "percentage": pct,
                "category": "Other"
            })
    return cleaned


# ============================================================
# SCORE CALCULATION FUNCTIONS
# ============================================================

def calculate_fit_score(structured_data, extracted_text):
    """Calculate JOB FIT score - based on skills, experience, certifications, role alignment, achievements"""
    resume_lower = extracted_text.lower()
    
    # Check if worst resume first
    is_worst, unscore = is_worst_resume(extracted_text)
    if is_worst:
        print(f"⚠️ Worst resume detected! Unprofessional score: {unscore}")
        return 15
    
    # 1. Skills Match (35% weight)
    technical_skills = [
        'python', 'java', 'javascript', 'typescript', 'aws', 'azure', 'gcp',
        'sql', 'mongodb', 'postgresql', 'react', 'angular', 'vue', 'node',
        'docker', 'kubernetes', 'terraform', 'jenkins', 'git', 'ci/cd',
        'tensorflow', 'pytorch', 'pandas', 'numpy', 'scikit-learn',
        'django', 'flask', 'spring', '.net', 'c++', 'go', 'rust'
    ]
    found_skills = sum(1 for skill in technical_skills if skill in resume_lower)
    skills_pct = min(100, (found_skills / 8) * 100) if found_skills > 0 else 30
    skills_score = skills_pct * 0.35
    
    # 2. Experience Match (25% weight)
    exp_years = structured_data.get('total_experience_years', 0)
    if exp_years is None:
        exp_years = 0
    try:
        exp_years = int(exp_years)
    except (ValueError, TypeError):
        exp_years = 0
    
    if exp_years >= 8:
        exp_pct = 100
    elif exp_years >= 5:
        exp_pct = 85
    elif exp_years >= 3:
        exp_pct = 70
    elif exp_years >= 1:
        exp_pct = 50
    else:
        exp_pct = 20
    exp_score = exp_pct * 0.25
    
    # 3. Certifications Match (15% weight)
    resume_certs = structured_data.get("certifications", []) or []
    if resume_certs:
        cert_pct = 100
    else:
        cert_pct = 75  # neutral default
    cert_score = cert_pct * 0.15
    
    # 4. Role Alignment (15% weight)
    current_role = structured_data.get('current_role', '')
    if current_role is None:
        current_role = ''
    current_role = current_role.lower()
    senior_indicators = ['senior', 'lead', 'architect', 'manager', 'principal', 'staff', 'director']
    has_senior = any(word in current_role for word in senior_indicators)
    role_pct = 100 if has_senior else 70
    role_score = role_pct * 0.15
    
    # 5. Achievements Quality (10% weight)
    achievements = structured_data.get('latest_3_experiences', [])
    if achievements is None:
        achievements = []
    has_quantifiable = False
    quantifiers = ['%', 'increased', 'reduced', 'saved', 'launched', 
                  'built', 'created', 'improved', 'optimized', 'delivered']
    for exp in achievements:
        if exp is None or not isinstance(exp, dict):
            continue
        for resp in exp.get('responsibilities', []):
            if resp is None:
                continue
            if any(word in resp.lower() for word in quantifiers):
                has_quantifiable = True
                break
        if has_quantifiable:
            break
    achievement_pct = 100 if has_quantifiable else 50
    achievement_score = achievement_pct * 0.10
    
    final_score = int(skills_score + exp_score + cert_score + role_score + achievement_score)
    return max(0, min(100, final_score))


def calculate_quality_score(structured_data, extracted_text):
    """Calculate RESUME QUALITY score - with None handling"""
    
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
    if isinstance(edu, list):
        edu = edu[0] if edu else {}
    if not isinstance(edu, dict):
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

@app.route("/")
def home():
    # Trigger reload to read .env
    return jsonify({
        "status": "active",
        "message": "AI Resume Parser API is running",
        "version": "2026-06-10-v8"
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.route("/api/version", methods=["GET"])
def version():
    return jsonify({
        "version": "2026-06-10-v8",
        "status": "active",
        "message": "AI Resume Parser is running with role-based fit scoring"
    })


@app.route("/api/job-roles", methods=["GET"])
def job_roles():
    """Return list of predefined job roles."""
    return jsonify({"roles": get_predefined_roles()})



@app.route("/api/analyze", methods=["POST"])
def analyze_resume_step():
    """Step 1: Extract & analyze resume. Returns structured data + skill suggestions.
    Does NOT generate the PNG image (that happens in /api/generate after skill selection)."""
    try:
        print("=" * 50)
        print("New /api/analyze request")

        if "resume" not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["resume"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type. Use PDF or DOCX"}), 400

        if is_duplicate_upload(file):
            return jsonify({"error": "Duplicate upload request detected. This file is already being processed."}), 429

        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename or 'upload')}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)

        job_role = request.form.get("job_role", "").strip()
        job_description = request.form.get("job_description", "").strip()

        extracted_text = extract_resume_text(file_path)
        print(f"Extracted text length: {len(extracted_text)} chars")

        # Extract profile image
        profile_image_base64 = None
        try:
            profile_bytes, profile_ext = extract_profile_image(file_path)
            if profile_bytes:
                profile_image_base64 = base64.b64encode(profile_bytes).decode("utf-8")
        except Exception as img_err:
            print(f"Profile image error: {img_err}")

        # Check for worst resume
        is_worst, unscore = is_worst_resume(extracted_text)
        structured_data = analyze_resume(extracted_text)
        if not isinstance(structured_data, dict):
            structured_data = {}
        edu = structured_data.get("education")
        if isinstance(edu, list):
            structured_data["education"] = edu[0] if edu else {}
        elif not isinstance(edu, dict):
            structured_data["education"] = {}
        if profile_image_base64:
            structured_data["profile_image_base64"] = profile_image_base64

        skill_gap = None
        if is_worst:
            structured_data["fit_score"] = 15
            structured_data["resume_quality_score"] = 15
            structured_data["resume_quality_verdict"] = "Worst"
        else:
            if job_role:
                role_requirements = get_role_requirements(job_role)
                if not isinstance(role_requirements, dict):
                    role_requirements = {}
                if job_description:
                    jd_data = extract_skills_from_jd(job_description)
                    if jd_data and isinstance(jd_data, dict):
                        for field in ["required_skills", "preferred_skills", "certifications", "keywords"]:
                            if jd_data.get(field):
                                extracted_list = ensure_list_of_strings(jd_data[field])
                                role_requirements[field] = list(set(
                                    ensure_list_of_strings(role_requirements.get(field, [])) + extracted_list
                                ))
                        if jd_data.get("min_experience_years"):
                            role_requirements["min_experience_years"] = jd_data["min_experience_years"]
                fit_score = calculate_role_fit_score(structured_data, role_requirements, extracted_text)
                skill_gap = build_skill_gap_report(structured_data, role_requirements, extracted_text)
            else:
                fit_score = calculate_fit_score(structured_data, extracted_text)

            quality_score = calculate_quality_score(structured_data, extracted_text)
            structured_data["fit_score"] = fit_score
            structured_data["resume_quality_score"] = quality_score
            structured_data["resume_quality_verdict"] = get_quality_verdict(quality_score)

        # Extract missing contact fields
        if structured_data.get("email") in [None, "Not Provided", "Not found", ""]:
            m = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", extracted_text)
            if m:
                structured_data["email"] = m.group()
        if structured_data.get("phone") in [None, "Not Provided", "Not found", ""]:
            m = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", extracted_text)
            if m:
                structured_data["phone"] = m.group()

        # Gap analysis
        gap_analyzer = GapAnalyzer()
        education_raw = ensure_list_of_strings(structured_data.get("education_raw"))
        experience_raw = ensure_list_of_strings(structured_data.get("experience_raw"))
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)

        # Build AI skill recommendations (top 7 by percentage)
        skill_proficiency = sanitize_skill_proficiency(structured_data.get("skill_proficiency"))
        if not skill_proficiency:
            flat = ensure_list_of_strings(structured_data.get("skills"))
            skill_proficiency = [{"skill": s, "percentage": 80, "category": "Other"} for s in flat[:14]]

        # Sort by percentage descending; top 7 are "AI recommended"
        skill_proficiency.sort(key=lambda x: x.get("percentage", 80), reverse=True)
        top7 = skill_proficiency[:7]
        rest = skill_proficiency[7:]

        # Clean up uploaded file
        try:
            os.remove(file_path)
        except Exception:
            pass

        structured_data["job_role"] = job_role if job_role else None

        return jsonify({
            "success": True,
            "message": "Resume analyzed successfully",
            "data": structured_data,
            "recommended_skills": top7,
            "all_skills": skill_proficiency,
            "fit_score": structured_data.get("fit_score"),
            "job_role": job_role if job_role else None,
            "skill_gap": skill_gap if job_role else None,
            "gap_analysis": gap_analysis,
            "session_id": unique_id,
        }), 200

    except Exception as e:
        print(f"ERROR in /api/analyze: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/api/generate", methods=["POST"])
def generate_resume_step():
    """Step 2: Generate PNG resume with user-selected skills.
    Expects JSON body: { data: {...}, selected_skills: [{skill, percentage, category}...] }"""
    try:
        body = request.get_json(force=True)
        if not body:
            return jsonify({"error": "JSON body required"}), 400

        structured_data = body.get("data") or {}
        selected_skills = sanitize_skill_proficiency(body.get("selected_skills") or [])

        if not structured_data:
            return jsonify({"error": "No resume data provided"}), 400

        # Override skill_proficiency with user-selected skills (max 7)
        structured_data["skill_proficiency"] = selected_skills[:7]
        structured_data["include_fit_score"] = body.get("include_fit_score", False)
        structured_data["include_best_suited_role"] = body.get("include_best_suited_role", False)
        if body.get("job_role"):
            structured_data["job_role"] = body.get("job_role")
        if body.get("custom_role"):
            structured_data["custom_role"] = body.get("custom_role")

        # Gap analysis (minimal — data already processed)
        gap_analyzer = GapAnalyzer()
        education_raw = ensure_list_of_strings(structured_data.get("education_raw"))
        experience_raw = ensure_list_of_strings(structured_data.get("experience_raw"))
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)

        unique_id = str(uuid.uuid4())[:8]
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(
            structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename)
        )

        with open(png_path, "rb") as f:
            png_bytes = f.read()
        image_base64 = base64.b64encode(png_bytes).decode("utf-8")

        try:
            os.remove(png_path)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "image_base64": image_base64,
        }), 200

    except Exception as e:
        print(f"ERROR in /api/generate: {e}")
        print(traceback.format_exc())
        return jsonify({"error": f"Image generation failed: {str(e)}"}), 500


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

        if is_duplicate_upload(file):
            return jsonify({"error": "Duplicate upload request detected. This file is already being processed."}), 429

        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename or 'upload')}"
        file_path = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(file_path)

        # --- Optional role / JD params ---
        job_role = request.form.get("job_role", "").strip()
        job_description = request.form.get("job_description", "").strip()
        include_fit_score = request.form.get("include_fit_score", "false").lower() == "true"
        include_best_suited_role = request.form.get("include_best_suited_role", "false").lower() == "true"
        print(f"Job Role: '{job_role}' | JD length: {len(job_description)} | Include Fit Score: {include_fit_score}")

        extracted_text = extract_resume_text(file_path)
        print(f"Extracted text length: {len(extracted_text)} chars")
        is_worst, unscore = is_worst_resume(extracted_text)

        # Extract profile image
        profile_image_base64 = None
        try:
            profile_bytes, profile_ext = extract_profile_image(file_path)
            if profile_bytes:
                profile_image_base64 = base64.b64encode(profile_bytes).decode("utf-8")
        except Exception as img_err:
            print(f"Error extracting profile photo: {img_err}")

        # Analyze with LLM
        structured_data = analyze_resume(extracted_text)
        if not isinstance(structured_data, dict):
            structured_data = {}
        structured_data["include_fit_score"] = include_fit_score
        structured_data["include_best_suited_role"] = include_best_suited_role
        edu = structured_data.get("education")
        if isinstance(edu, list):
            structured_data["education"] = edu[0] if edu else {}
        elif not isinstance(edu, dict):
            structured_data["education"] = {}
        if profile_image_base64:
            structured_data["profile_image_base64"] = profile_image_base64

        # Initialize skill_gap — may be set later in the role branch
        skill_gap = None

        # Force low scores for worst resumes
        if is_worst:
            structured_data["fit_score"] = 15
            structured_data["resume_quality_score"] = 15
            structured_data["resume_quality_verdict"] = "Worst"
            structured_data["red_flags"] = {
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
                "desperate_tone": True,
            }
            structured_data["quality_observations"] = [
                "⚠️ CRITICAL: Resume contains extremely unprofessional content",
                "⚠️ No valid work experience with proper details",
                "⚠️ Skills listed are completely irrelevant for professional work",
                "⚠️ Contains desperate and unprofessional tone",
                "⚠️ Complete resume rewrite is strongly recommended",
            ]
        else:
            # Calculate scores — role-based or generic
            if job_role:
                role_requirements = get_role_requirements(job_role)
                if not isinstance(role_requirements, dict):
                    role_requirements = {}
                if job_description:
                    jd_data = extract_skills_from_jd(job_description)
                    if jd_data and isinstance(jd_data, dict):
                        for field in ["required_skills", "preferred_skills", "certifications", "keywords"]:
                            if jd_data.get(field):
                                extracted_list = ensure_list_of_strings(jd_data[field])
                                role_requirements[field] = list(set(
                                    ensure_list_of_strings(role_requirements.get(field, [])) + extracted_list
                                ))
                        if jd_data.get("min_experience_years"):
                            role_requirements["min_experience_years"] = jd_data["min_experience_years"]

                fit_score = calculate_role_fit_score(structured_data, role_requirements, extracted_text)
                skill_gap = build_skill_gap_report(structured_data, role_requirements, extracted_text)
            else:
                fit_score = calculate_fit_score(structured_data, extracted_text)
                skill_gap = None

            quality_score = calculate_quality_score(structured_data, extracted_text)

            structured_data["fit_score"] = fit_score
            structured_data["resume_quality_score"] = quality_score
            structured_data["resume_quality_verdict"] = get_quality_verdict(quality_score)

        print(f"Final Fit Score: {structured_data.get('fit_score')}")
        print(f"Final Quality Score: {structured_data.get('resume_quality_score')}")
        print(f"Quality Verdict: {structured_data.get('resume_quality_verdict')}")

        # Extract email and phone if missing
        if structured_data.get("email") in [None, "Not Provided", "Not found", ""]:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", extracted_text)
            if email_match:
                structured_data["email"] = email_match.group()

        if structured_data.get("phone") in [None, "Not Provided", "Not found", ""]:
            phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", extracted_text)
            if phone_match:
                structured_data["phone"] = phone_match.group()

        # Gap Analysis
        gap_analyzer = GapAnalyzer()
        education_raw = ensure_list_of_strings(structured_data.get("education_raw"))
        experience_raw = ensure_list_of_strings(structured_data.get("experience_raw"))
        gap_analysis = gap_analyzer.analyze_complete_gaps(education_raw, experience_raw)

        # For batch: auto-use top 7 skills
        skill_proficiency = sanitize_skill_proficiency(structured_data.get("skill_proficiency"))
        if not skill_proficiency:
            flat = ensure_list_of_strings(structured_data.get("skills"))
            skill_proficiency = [{"skill": s, "percentage": 80, "category": "Other"} for s in flat[:7]]
        skill_proficiency.sort(key=lambda x: x.get("percentage", 80), reverse=True)
        structured_data["skill_proficiency"] = skill_proficiency[:7]
        structured_data["job_role"] = job_role if job_role else None

        # Generate PNG image
        png_filename = f"Resume_{structured_data.get('name', 'Candidate')}_{unique_id}.png"
        png_path = generate_resume_image(structured_data, gap_analysis, os.path.join(OUTPUT_FOLDER, png_filename))

        with open(png_path, "rb") as f:
            png_bytes = f.read()
        image_base64 = base64.b64encode(png_bytes).decode("utf-8")

        # Clean up
        try:
            os.remove(file_path)
            os.remove(png_path)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Resume processed successfully",
            "data": structured_data,
            "image_base64": image_base64,
            "fit_score": structured_data.get("fit_score"),
            "job_role": job_role if job_role else None,
            "skill_gap": skill_gap if job_role else None,
            "gap_analysis": gap_analysis,
        }), 200

    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


# For local development
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)