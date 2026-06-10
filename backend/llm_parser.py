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

# Keywords that indicate unprofessional resume
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
    'hardworking': 15,
    'tiktok': 25,
    'pubg': 25,
    'facebook': 20,
    'chicken dinner': 30,
}


def analyze_resume(resume_text):
    """Enhanced LLM parsing with aggressive red flag detection"""
    
    if not resume_text or len(resume_text.strip()) < 50:
        return generate_fallback_data(resume_text)
    
    # First, check for unprofessional content using keyword detection
    resume_lower = resume_text.lower()
    unprofessional_score = 0
    detected_flags = []
    
    for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items():
        if keyword in resume_lower:
            unprofessional_score += penalty
            detected_flags.append(keyword)
    
    # If highly unprofessional, skip LLM and return direct fallback
    if unprofessional_score > 50 or len(detected_flags) > 5:
        print(f"Highly unprofessional resume detected. Flags: {detected_flags[:5]}")
        return generate_fallback_data(resume_text, is_worst=True)
    
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON.

    IMPORTANT: Be STRICT with scoring. If the resume has unprofessional content, 
    give a VERY LOW fit score (10-30) and mark appropriate red flags.

    Extract the following information:

    {{
        "name": "Full name or 'Unknown Candidate'",
        "gender": "male/female/neutral",
        "current_role": "Current job title or 'Not Specified'",
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": "email or 'Not Provided'",
        "phone": "phone or 'Not Provided'",
        "linkedin": "Not Provided",
        "professional_summary": "Brief summary",
        "skills": [],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {{
            "degree": "Not Specified",
            "institution": "Not Specified",
            "year": "Not Specified"
        }},
        "latest_3_experiences": [],
        "fit_score": 25,
        "strengths": [],
        "areas_for_improvement": [
            "Complete rewrite needed",
            "Remove unprofessional language",
            "Add proper work experience"
        ],
        "recommended_role": "Entry Level",
        "education_raw": ["No year mentioned"],
        "experience_raw": ["No year mentioned"],
        "red_flags": {{
            "poor_formatting": true,
            "missing_contact_info": true,
            "unprofessional_content": true,
            "generic_skills": true,
            "no_work_experience": true,
            "vague_descriptions": true,
            "unprofessional_language": true,
            "missing_dates": true,
            "over_exaggeration": true,
            "spelling_grammar_issues": true,
            "incomplete_education": true,
            "irrelevant_skills": true,
            "desperate_tone": true
        }},
        "resume_quality_score": 15,
        "resume_quality_verdict": "Worst",
        "quality_observations": [
            "CRITICAL: Resume contains extremely unprofessional content",
            "No valid work experience with proper details",
            "Skills listed are completely irrelevant for professional work",
            "Missing professional contact information",
            "Contains desperate and unprofessional tone",
            "Complete resume rewrite is strongly recommended"
        ]
    }}

    Resume Text:
    {resume_text[:3000]}

    Return ONLY the JSON object.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500
        )
        
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        
        parsed_data = json.loads(result)
        
        # Override with aggressive scoring if unprofessional
        if unprofessional_score > 30:
            parsed_data['fit_score'] = max(10, min(25, parsed_data.get('fit_score', 20)))
            parsed_data['resume_quality_score'] = max(5, min(20, parsed_data.get('resume_quality_score', 15)))
            parsed_data['resume_quality_verdict'] = "Worst"
            
            # Ensure red flags are set
            if 'red_flags' not in parsed_data:
                parsed_data['red_flags'] = {}
            parsed_data['red_flags']['unprofessional_content'] = True
            parsed_data['red_flags']['unprofessional_language'] = True
            parsed_data['red_flags']['desperate_tone'] = True
        
        return parsed_data
        
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text, is_worst=unprofessional_score > 30)


def generate_fallback_data(resume_text, is_worst=False):
    """Fallback when LLM fails - with aggressive scoring for worst resumes"""
    
    resume_lower = resume_text.lower() if resume_text else ""
    
    # Check for unprofessional keywords
    unprofessional_score = 0
    for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items():
        if keyword in resume_lower:
            unprofessional_score += penalty
    
    # Determine if this is a worst resume
    is_worst_resume = is_worst or unprofessional_score > 50 or len(resume_text) < 200
    
    # Extract email and phone if present
    email = "Not Provided"
    phone = "Not Provided"
    
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) if resume_text else None
    if email_match:
        email = email_match.group()
    
    phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) if resume_text else None
    if phone_match:
        phone = phone_match.group()
    
    if is_worst_resume:
        # Worst resume - very low scores
        fit_score = 10
        quality_score = 10
        verdict = "Worst"
        
        red_flags = {
            "poor_formatting": True,
            "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
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
        
        observations = [
            "⚠️ CRITICAL: Resume contains extremely unprofessional content",
            "⚠️ No valid work experience with proper details",
            "⚠️ Skills listed are completely irrelevant for professional work",
            "⚠️ Contains desperate and unprofessional tone ('need job urgently')",
            "⚠️ Complete resume rewrite is strongly recommended"
        ]
        
        skills = ["Not specified - Unprofessional content detected"]
        areas_for_improvement = [
            "Complete resume rewrite required",
            "Remove all unprofessional language",
            "Add proper work experience with dates",
            "Include relevant professional skills",
            "Add complete contact information"
        ]
        
    else:
        # Normal fallback
        fit_score = 50
        quality_score = 50
        verdict = "Average"
        
        red_flags = {
            "poor_formatting": False,
            "missing_contact_info": email == "Not Provided" or phone == "Not Provided",
            "unprofessional_content": False,
            "generic_skills": True,
            "no_work_experience": True,
            "vague_descriptions": True,
            "unprofessional_language": False,
            "missing_dates": True,
            "over_exaggeration": False,
            "spelling_grammar_issues": False,
            "incomplete_education": True,
            "irrelevant_skills": False,
            "desperate_tone": False
        }
        
        observations = [
            "Missing professional contact information",
            "Work experience needs more details",
            "Education section incomplete"
        ]
        
        skills = ["Not specified"]
        areas_for_improvement = [
            "Complete all sections",
            "Add professional details",
            "Include quantifiable achievements"
        ]
    
    return {
        "name": "Unknown Candidate" if is_worst_resume else "Candidate",
        "gender": "neutral",
        "current_role": "Not Specified",
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": email,
        "phone": phone,
        "linkedin": "Not Provided",
        "professional_summary": "Professional summary not available" if not is_worst_resume else "This resume requires complete rewrite - contains unprofessional content",
        "skills": skills,
        "skill_proficiencies": [],
        "certifications": [],
        "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
        "latest_3_experiences": [],
        "fit_score": fit_score,
        "strengths": ["Not available"],
        "areas_for_improvement": areas_for_improvement,
        "recommended_role": "Entry Level Position",
        "education_raw": ["No year mentioned"],
        "experience_raw": ["No year mentioned"],
        "red_flags": red_flags,
        "resume_quality_score": quality_score,
        "resume_quality_verdict": verdict,
        "quality_observations": observations
    }