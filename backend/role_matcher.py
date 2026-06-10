import os
import json
import re
import httpx
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Groq client (shared http_client pattern from llm_parser.py)
# ---------------------------------------------------------------------------
http_client = httpx.Client(verify=False)
_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            api_key = "DUMMY_KEY"
        _groq_client = Groq(
            api_key=api_key,
            http_client=http_client
        )
    return _groq_client


# ---------------------------------------------------------------------------
# Load job roles from JSON
# ---------------------------------------------------------------------------
_ROLES_CACHE = None
_ROLES_FILE = os.path.join(os.path.dirname(__file__), "job_roles.json")


def _load_roles():
    global _ROLES_CACHE
    if _ROLES_CACHE is None:
        try:
            with open(_ROLES_FILE, "r") as f:
                _ROLES_CACHE = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load job_roles.json: {e}")
            _ROLES_CACHE = {}
    return _ROLES_CACHE


def get_predefined_roles():
    """Return list of predefined role names."""
    return list(_load_roles().keys())


def get_role_requirements(role_name):
    """
    Return requirements dict for a given role.
    Falls back to LLM generation for custom / unknown roles.
    """
    roles = _load_roles()
    if role_name in roles:
        reqs = dict(roles[role_name])
        reqs["role_name"] = role_name
        return reqs
    # Custom / unknown role — generate via LLM
    reqs = _generate_role_requirements_via_llm(role_name)
    reqs["role_name"] = role_name
    return reqs


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _generate_role_requirements_via_llm(role_name):
    """Use Groq to generate skill requirements for an unknown role."""
    prompt = f"""
You are a technical recruiter expert. Generate skill requirements for the role: "{role_name}"

Return ONLY valid JSON in this exact format:
{{
    "required_skills": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6"],
    "preferred_skills": ["skill1", "skill2", "skill3", "skill4"],
    "certifications": ["cert1", "cert2"],
    "min_experience_years": 2,
    "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
}}

Return ONLY the JSON object, no extra text.
"""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        data = json.loads(result)
        # Sanitise fields
        return {
            "required_skills": data.get("required_skills", []),
            "preferred_skills": data.get("preferred_skills", []),
            "certifications": data.get("certifications", []),
            "min_experience_years": data.get("min_experience_years", 2),
            "keywords": data.get("keywords", [])
        }
    except Exception as e:
        print(f"LLM role generation error: {e}")
        return {
            "required_skills": [],
            "preferred_skills": [],
            "certifications": [],
            "min_experience_years": 2,
            "keywords": []
        }


def extract_skills_from_jd(job_description):
    """
    Extract required and preferred skills from a pasted job description
    using the LLM.  Returns a partial role-requirements dict that can be
    merged with / override a predefined role template.
    """
    if not job_description or len(job_description.strip()) < 30:
        return None

    prompt = f"""
Analyze this job description and extract the required and preferred skills.

Return ONLY valid JSON:
{{
    "required_skills": ["skill1", "skill2", ...],
    "preferred_skills": ["skill1", "skill2", ...],
    "certifications": ["cert1", "cert2"],
    "min_experience_years": 3,
    "keywords": ["keyword1", "keyword2", ...]
}}

Job Description:
{job_description[:4000]}

Return ONLY the JSON object.
"""
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600
        )
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        return json.loads(result)
    except Exception as e:
        print(f"JD skill extraction error: {e}")
        return None


# ---------------------------------------------------------------------------
# Score & Gap calculation
# ---------------------------------------------------------------------------

def _normalise(text):
    """Lower-case and strip for comparison."""
    return str(text).lower().strip()


def _skill_in_text(skill, text_lower):
    """Check if a skill appears in the full resume text (fuzzy word match)."""
    skill_lower = _normalise(skill)
    # Direct substring match
    if skill_lower in text_lower:
        return True
    # Word boundary match for short skills to avoid false positives
    pattern = r'\b' + re.escape(skill_lower) + r'\b'
    return bool(re.search(pattern, text_lower))


def _calculate_single_cert_match(required_cert, resume_certs, full_text_lower):
    req_norm = required_cert.lower().strip()
    
    def clean_cert(name):
        name = name.replace("certified", "").replace("certification", "").replace("certificate", "")
        name = re.sub(r'\s+', ' ', name).strip()
        return name
        
    req_clean = clean_cert(req_norm)
    
    # 1. Exact Match (100%)
    for rc in resume_certs:
        rc_norm = rc.lower().strip()
        if req_norm == rc_norm or clean_cert(req_norm) == clean_cert(rc_norm):
            return 1.0
            
    if req_norm in full_text_lower or req_clean in full_text_lower:
        return 1.0

    # 2. Partial Match (50%): Same family/provider and general topic, but different level
    providers = ["aws", "azure", "gcp", "google cloud", "oracle", "comptia", "scrum", "pmp", "cisco", "ccna", "istqb", "mongodb"]
    req_provider = next((p for p in providers if p in req_norm), None)
    
    for rc in resume_certs:
        rc_norm = rc.lower().strip()
        rc_clean = clean_cert(rc_norm)
        rc_provider = next((p for p in providers if p in rc_norm), None)
        
        if req_provider and req_provider == rc_provider:
            key_terms = ["architect", "developer", "administrator", "engineer", "security", "data", "scrum", "database"]
            shared_terms = any(term in req_norm and term in rc_norm for term in key_terms)
            if shared_terms:
                return 0.5
            if req_clean in rc_clean or rc_clean in req_clean:
                return 0.5

    for provider in ["aws", "azure", "gcp", "google cloud", "oracle", "comptia", "scrum", "istqb", "mongodb"]:
        if provider in req_norm and provider in full_text_lower:
            key_terms = ["architect", "developer", "administrator", "engineer", "security", "data", "database"]
            shared_terms = any(term in req_norm and term in full_text_lower for term in key_terms)
            if shared_terms:
                return 0.5

    # 3. Keyword Match (25%)
    if req_provider:
        for rc in resume_certs:
            rc_norm = rc.lower().strip()
            rc_provider = next((p for p in providers if p in rc_norm), None)
            if req_provider == rc_provider:
                return 0.25
        if req_provider in full_text_lower:
            return 0.25
            
    return 0.0


def _calculate_role_alignment(current_role, target_role):
    curr = current_role.lower().strip()
    targ = target_role.lower().strip()
    
    if not curr or curr in ["not specified", "none", "professional", "candidate"]:
        return 40
        
    if curr == targ:
        return 100
        
    if curr in targ or targ in curr:
        return 90
        
    keywords = ["engineer", "developer", "architect", "analyst", "manager", "designer", "consultant", "administrator"]
    shared_keywords = sum(1 for kw in keywords if kw in curr and kw in targ)
    if shared_keywords > 0:
        return 75
        
    tech_terms = ["software", "data", "cloud", "devops", "qa", "system", "network", "cybersecurity", "security", "ai", "ml", "database", "backend", "frontend", "full stack"]
    is_curr_tech = any(t in curr for t in tech_terms)
    is_targ_tech = any(t in targ for t in tech_terms)
    if is_curr_tech and is_targ_tech:
        return 60
        
    return 30


def calculate_role_fit_score(structured_data, role_requirements, extracted_text=""):
    """
    Role-based fit score formula:
        Skills Match      × 35%
        Experience Match  × 25%
        Certifications    × 15%
        Role Alignment    × 15%
        Achievements      × 10%
    Returns an integer 0-100.
    """
    text_lower = _normalise(extracted_text)

    # --- 1. Skills Match (35%) ---
    required_skills = role_requirements.get("required_skills", [])
    preferred_skills = role_requirements.get("preferred_skills", [])

    resume_skills = [_normalise(s) for s in (structured_data.get("skills") or [])]
    all_required = required_skills + preferred_skills

    if not all_required:
        skills_pct = 75
    else:
        matched = sum(
            1 for skill in required_skills
            if _normalise(skill) in resume_skills or _skill_in_text(skill, text_lower)
        )
        preferred_matched = sum(
            1 for skill in preferred_skills
            if _normalise(skill) in resume_skills or _skill_in_text(skill, text_lower)
        )
        total_weight = len(required_skills) + 0.5 * len(preferred_skills)
        matched_weight = matched + 0.5 * preferred_matched
        skills_pct = int((matched_weight / total_weight) * 100) if total_weight > 0 else 0

    skills_score = skills_pct * 0.35

    # --- 2. Experience Match (25%) ---
    exp_years = structured_data.get("total_experience_years", 0) or 0
    try:
        exp_years = int(exp_years)
    except (ValueError, TypeError):
        exp_years = 0

    min_exp = role_requirements.get("min_experience_years", 2)
    if min_exp and min_exp > 0:
        exp_ratio = min(exp_years / min_exp, 1.5)
        exp_pct = min(int(exp_ratio * 100), 100)
    else:
        exp_pct = 80

    exp_score = exp_pct * 0.25

    # --- 3. Certifications Match (15%) ---
    role_certs = role_requirements.get("certifications", [])
    resume_certs = [_normalise(c) for c in (structured_data.get("certifications") or [])]

    if not role_certs:
        cert_pct = 80
    else:
        total_cert_score = sum(
            _calculate_single_cert_match(cert, resume_certs, text_lower) for cert in role_certs
        )
        cert_pct = int((total_cert_score / len(role_certs)) * 100)

    cert_score = cert_pct * 0.15

    # --- 4. Role Alignment (15%) ---
    current_role = structured_data.get("current_role", "") or ""
    target_role = role_requirements.get("role_name", "") or ""
    role_pct = _calculate_role_alignment(current_role, target_role)
    role_score = role_pct * 0.15

    # --- 5. Achievements Quality (10%) ---
    achievements = structured_data.get('latest_3_experiences', []) or []
    has_quantifiable = False
    quantifiers = ['%', 'increased', 'reduced', 'saved', 'launched', 
                  'built', 'created', 'improved', 'optimized', 'delivered',
                  'million', 'thousand', 'percent', 'led', 'managed']
    for exp in achievements:
        if not exp:
            continue
        for resp in exp.get('responsibilities', []) or []:
            if not resp:
                continue
            if any(word in resp.lower() for word in quantifiers):
                has_quantifiable = True
                break
        if has_quantifiable:
            break
    achievement_pct = 100 if has_quantifiable else 50
    achievement_score = achievement_pct * 0.10

    final = int(skills_score + exp_score + cert_score + role_score + achievement_score)
    return max(0, min(100, final))


def build_skill_gap_report(structured_data, role_requirements, extracted_text=""):
    """
    Build a human-readable skill gap report.

    Returns dict:
        matched_skills       : list of str
        missing_skills       : list of str
        match_percentage     : int (0-100, required skills only)
        experience_match_pct : int
        certification_match_pct : int
        recommendations      : list of str
    """
    text_lower = _normalise(extracted_text)

    # --- Skills ---
    required_skills = role_requirements.get("required_skills", [])
    preferred_skills = role_requirements.get("preferred_skills", [])
    resume_skills_lower = [_normalise(s) for s in (structured_data.get("skills") or [])]

    matched = []
    missing = []

    for skill in required_skills:
        if _normalise(skill) in resume_skills_lower or _skill_in_text(skill, text_lower):
            matched.append(skill)
        else:
            missing.append(skill)

    # Preferred skills — show as bonus matches
    preferred_matched = []
    for skill in preferred_skills:
        if _normalise(skill) in resume_skills_lower or _skill_in_text(skill, text_lower):
            preferred_matched.append(f"{skill} ⭐")

    match_pct = int((len(matched) / len(required_skills)) * 100) if required_skills else 50

    # --- Experience ---
    exp_years = structured_data.get("total_experience_years", 0) or 0
    try:
        exp_years = int(exp_years)
    except (ValueError, TypeError):
        exp_years = 0
    min_exp = role_requirements.get("min_experience_years", 2)
    exp_pct = min(int((exp_years / min_exp) * 100), 100) if min_exp > 0 else 100

    # --- Certifications ---
    role_certs = role_requirements.get("certifications", [])
    resume_certs_lower = [_normalise(c) for c in (structured_data.get("certifications") or [])]
    cert_matched_score = sum(
        _calculate_single_cert_match(cert, resume_certs_lower, text_lower) for cert in role_certs
    ) if role_certs else 0.0
    cert_pct = int((cert_matched_score / len(role_certs)) * 100) if role_certs else 50

    # --- Recommendations ---
    recommendations = []
    for skill in missing[:3]:  # top 3 missing skills
        recommendations.append(f"Add '{skill}' to your resume through projects or certifications")

    if exp_years < min_exp:
        gap = min_exp - exp_years
        recommendations.append(
            f"Gain {gap} more year{'s' if gap != 1 else ''} of relevant experience "
            f"(current: {exp_years}yr, required: {min_exp}yr)"
        )

    if role_certs and cert_matched_score < len(role_certs):
        missing_certs = [
            c for c in role_certs
            if _calculate_single_cert_match(c, resume_certs_lower, text_lower) < 0.5
        ]
        if missing_certs:
            recommendations.append(f"Consider obtaining: {missing_certs[0]}")

    if not recommendations:
        recommendations.append("Strong match! Focus on highlighting quantifiable achievements.")

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "preferred_matched": preferred_matched,
        "match_percentage": match_pct,
        "experience_match_pct": exp_pct,
        "certification_match_pct": cert_pct,
        "recommendations": recommendations,
        "min_experience_years": min_exp,
        "resume_experience_years": exp_years
    }
