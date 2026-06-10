from groq import Groq
from dotenv import load_dotenv
import os
import json
import httpx
import re

load_dotenv()

http_client = httpx.Client(verify=False)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=http_client
)

UNPROFESSIONAL_KEYWORDS = {
    'urgent': 30, 'urgently': 35, 'bored': 40, 'bored at home': 45,
    'please hire': 40, 'please hire me': 45, 'genius': 35,
    'can do any job': 40, 'whatsapp': 25, 'instagram': 25,
    'youtube': 20, 'gaming': 25, 'sleeping': 30, 'timepass': 35,
    "don't remember": 30, 'some school': 35, 'some college': 35,
    'need job': 30, 'tiktok': 25, 'pubg': 25, 'facebook': 20
}


def analyze_resume(resume_text):
    """Enhanced LLM parsing with strengths and growth areas"""
    
    if not resume_text or len(resume_text.strip()) < 50:
        return generate_fallback_data(resume_text)
    
    resume_lower = resume_text.lower()
    unprofessional_score = sum(penalty for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items() if keyword in resume_lower)
    
    if unprofessional_score > 50:
        return generate_fallback_data(resume_text, is_worst=True)
    
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON.

    Extract the following information carefully:

    {{
        "name": "Full name",
        "current_role": "Current job title",
        "total_experience_years": number,
        "location": "City, State",
        "email": "email address",
        "phone": "phone number",
        "linkedin": "LinkedIn URL",
        "professional_summary": "2-3 sentence summary",
        "skills": ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5"],
        "certifications": [],
        "education": {{
            "degree": "Degree name",
            "institution": "University name",
            "year": "Graduation year"
        }},
        "latest_3_experiences": [
            {{
                "company": "Company name",
                "role": "Job title",
                "duration": "2020-2024 or 2022-Present",
                "responsibilities": ["Achievement 1", "Achievement 2"]
            }}
        ],
        "fit_score": 75,
        "strengths": [
            "Extract a key technical strength",
            "Extract a leadership/soft skill strength", 
            "Extract an achievement-based strength"
        ],
        "areas_for_improvement": [
            "Extract a missing skill or certification",
            "Extract a formatting or content issue",
            "Extract a career gap or missing detail"
        ],
        "recommended_role": "Best matching job role",
        "education_raw": ["Full education text"],
        "experience_raw": ["Full experience text"]
    }}

    Resume Text:
    {resume_text[:4000]}

    Return ONLY the JSON object.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        
        parsed_data = json.loads(result)
        
        # Ensure strengths exist
        if not parsed_data.get('strengths') or len(parsed_data.get('strengths', [])) == 0:
            parsed_data['strengths'] = [
                "Professional experience in relevant field",
                "Technical skills alignment",
                "Good communication skills"
            ]
        
        # Ensure areas_for_improvement exist
        if not parsed_data.get('areas_for_improvement') or len(parsed_data.get('areas_for_improvement', [])) == 0:
            parsed_data['areas_for_improvement'] = [
                "Add more quantifiable achievements",
                "Include relevant certifications",
                "Improve resume formatting"
            ]
        
        # Extract role if missing
        if not parsed_data.get('current_role') or parsed_data.get('current_role') == 'Professional':
            role_match = re.search(r'(?:Senior|Lead|Principal)?\s*(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps)\s*(?:Engineer|Developer|Architect|Analyst|Manager)', resume_text, re.IGNORECASE)
            if role_match:
                parsed_data['current_role'] = role_match.group(0).strip()
        
        return parsed_data
        
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)


def generate_fallback_data(resume_text, is_worst=False):
    """Fallback with proper strengths and growth areas"""
    
    resume_lower = resume_text.lower() if resume_text else ""
    
    # Extract role
    role = "Professional"
    role_patterns = [
        r'(?:Senior|Lead|Principal)?\s*(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps)\s*(?:Engineer|Developer|Architect|Analyst|Manager)',
        r'(?:Python|Java|JavaScript|React|AWS)\s*(?:Developer|Engineer)',
    ]
    for pattern in role_patterns:
        match = re.search(pattern, resume_text, re.IGNORECASE) if resume_text else None
        if match:
            role = match.group(0).strip()
            break
    
    # Extract name
    name = "Candidate"
    name_match = re.search(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', resume_text[:200] if resume_text else "", re.MULTILINE)
    if name_match:
        name = name_match.group(1)
    
    # Extract email and phone
    email = "Not Provided"
    phone = "Not Provided"
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) if resume_text else None
    if email_match:
        email = email_match.group()
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) if resume_text else None
    if phone_match:
        phone = phone_match.group()
    
    if is_worst:
        return {
            "name": name,
            "current_role": "Not Specified",
            "total_experience_years": 0,
            "location": "Not Specified",
            "email": email,
            "phone": phone,
            "linkedin": "Not Provided",
            "professional_summary": "This resume requires complete rewrite",
            "skills": ["Not specified"],
            "certifications": [],
            "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
            "latest_3_experiences": [],
            "fit_score": 15,
            "strengths": ["Not available - Resume needs complete rewrite"],
            "areas_for_improvement": [
                "Complete resume rewrite required",
                "Remove all unprofessional language",
                "Add proper work experience with dates",
                "Include relevant professional skills",
                "Add complete contact information"
            ],
            "recommended_role": "Entry Level",
            "education_raw": ["No year mentioned"],
            "experience_raw": ["No year mentioned"],
            "red_flags": {
                "unprofessional_content": True,
                "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
                "no_work_experience": True,
                "irrelevant_skills": True,
                "missing_dates": True
            },
            "resume_quality_score": 15,
            "resume_quality_verdict": "Worst",
            "quality_observations": [
                "⚠️ CRITICAL: Resume contains unprofessional content",
                "⚠️ No valid work experience documented",
                "⚠️ Complete resume rewrite needed"
            ]
        }
    else:
        return {
            "name": name,
            "current_role": role,
            "total_experience_years": 0,
            "location": "Not Specified",
            "email": email,
            "phone": phone,
            "linkedin": "Not Provided",
            "professional_summary": "Professional summary not available",
            "skills": ["Communication", "Teamwork", "Problem Solving"],
            "certifications": [],
            "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
            "latest_3_experiences": [],
            "fit_score": 50,
            "strengths": [
                "Professional experience in relevant field",
                "Technical skills foundation",
                "Good communication abilities"
            ],
            "areas_for_improvement": [
                "Complete all sections with detailed information",
                "Add quantifiable achievements to experience",
                "Include relevant certifications",
                "Add proper dates to education and experience"
            ],
            "recommended_role": "Entry Level Position",
            "education_raw": ["No year mentioned"],
            "experience_raw": ["No year mentioned"],
            "red_flags": {
                "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
                "missing_dates": True
            },
            "resume_quality_score": 50,
            "resume_quality_verdict": "Average",
            "quality_observations": [
                "Missing professional contact information",
                "Work experience needs more details",
                "Education section incomplete",
                "Add dates to experience and education"
            ]
        }