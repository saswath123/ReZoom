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

# Red flag deduction values
RED_FLAG_DEDUCTIONS = {
    "missing_contact_info": 20,
    "no_work_experience": 35,
    "vague_descriptions": 15,
    "generic_skills": 15,
    "missing_dates": 15,
    "unprofessional_language": 35,  # Increased from 25
    "incomplete_education": 15,
    "poor_formatting": 10,
    "irrelevant_skills": 25,  # Increased
    "over_exaggeration": 25,
    "spelling_grammar_issues": 10,
    "unprofessional_content": 40,  # New - severe penalty
    "desperate_tone": 30,  # New - "need job urgently"
    "no_company_names": 15,
    "vague_experience": 20
}

# Unprofessional keywords that should drastically reduce fit score
UNPROFESSIONAL_KEYWORDS = [
    'urgently', 'bored at home', 'please hire me', 'genius', 'can do any job',
    'hardworking'  # when not backed by evidence
]

def calculate_quality_score_from_red_flags(red_flags):
    """Calculate quality score based on red flags"""
    score = 100
    for flag, is_present in red_flags.items():
        if is_present and flag in RED_FLAG_DEDUCTIONS:
            score -= RED_FLAG_DEDUCTIONS[flag]
    return max(0, min(100, score))

def calculate_fit_score_from_red_flags(red_flags):
    """Calculate FIT score based on red flags (lower for unprofessional content)"""
    score = 85  # Base fit score for a good resume
    
    # Severe penalties for unprofessional content
    if red_flags.get('unprofessional_content'):
        score -= 40
    if red_flags.get('unprofessional_language'):
        score -= 35
    if red_flags.get('desperate_tone'):
        score -= 30
    if red_flags.get('no_work_experience'):
        score -= 35
    if red_flags.get('irrelevant_skills'):
        score -= 25
    if red_flags.get('vague_descriptions'):
        score -= 20
    if red_flags.get('missing_contact_info'):
        score -= 15
    if red_flags.get('missing_dates'):
        score -= 10
    if red_flags.get('generic_skills'):
        score -= 15
    
    # Ensure score is within bounds
    return max(0, min(100, score))

def analyze_resume(resume_text):
    """Enhanced LLM parsing with red flag detection and quality scoring"""
    
    if not resume_text or len(resume_text.strip()) < 50:
        print(f"Warning: Resume text is too short or empty")
        return generate_fallback_data(resume_text)
    
    if len(resume_text) > 8000:
        resume_text = resume_text[:8000]
    
    # Check for unprofessional content BEFORE API call
    has_unprofessional_content = any(keyword in resume_text.lower() for keyword in UNPROFESSIONAL_KEYWORDS)
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON.

    IMPORTANT: Be STRICT with scoring. If the resume has unprofessional content, 
    give a VERY LOW fit score (10-30) and mark appropriate red flags.

    Extract the following information:

    {{
        "name": "Full name from resume or 'Unknown Candidate'",
        "gender": "male/female/neutral",
        "current_role": "Current job title or 'Not Specified'",
        "total_experience_years": number,
        "location": "City, Country or 'Not Specified'",
        "email": "email address or 'Not Provided'",
        "phone": "phone number or 'Not Provided'",
        "linkedin": "LinkedIn URL or 'Not Provided'",
        "professional_summary": "Brief summary",
        "skills": ["Skill1", "Skill2"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {{
            "degree": "Degree name or 'Not Specified'",
            "institution": "University name or 'Not Specified'",
            "year": "Graduation year or 'Not Specified'"
        }},
        "latest_3_experiences": [
            {{
                "company": "Company name or 'Not Specified'",
                "role": "Job title",
                "duration": "Start - End or 'Not Specified'",
                "responsibilities": ["Responsibility"]
            }}
        ],
        "fit_score": 75,
        "strengths": ["Strength"],
        "areas_for_improvement": ["Improvement"],
        "recommended_role": "Recommended role",
        
        "education_raw": ["Education text"],
        "experience_raw": ["Experience text"],
        
        "red_flags": {{
            "poor_formatting": false,
            "missing_contact_info": false,
            "unprofessional_content": false,
            "generic_skills": false,
            "no_work_experience": false,
            "vague_descriptions": false,
            "unprofessional_language": false,
            "missing_dates": false,
            "over_exaggeration": false,
            "spelling_grammar_issues": false,
            "incomplete_education": false,
            "irrelevant_skills": false,
            "desperate_tone": false,
            "no_company_names": false
        }},
        
        "resume_quality_score": 75,
        "resume_quality_verdict": "Good",
        "quality_observations": ["Observation"]
    }}

    CRITICAL SCORING RULES:

    FIT SCORE (0-100) - Be STRICT:
    - 0-20: Unprofessional resume, desperate tone, no real experience
    - 21-40: Very poor quality, missing critical information
    - 41-60: Below average, significant issues
    - 61-75: Average, needs improvement
    - 76-90: Good, minor issues
    - 91-100: Excellent, professional and complete

    RED FLAGS (set to true if detected):
    - unprofessional_content: "need job urgently", "bored", "please hire me"
    - unprofessional_language: "genius", "hardworking" without evidence, "can do any job"
    - desperate_tone: "urgently need job", "available immediately"
    - missing_contact_info: No email OR no phone
    - no_work_experience: No real work experience with dates
    - irrelevant_skills: WhatsApp, Instagram, Gaming, Eating, Sleeping
    - vague_descriptions: "worked in many companies", "did important things"
    - missing_dates: No years mentioned anywhere

    Resume Text:
    {resume_text}

    Return ONLY the JSON object.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2500
        )
        
        result = response.choices[0].message.content.strip()
        
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        result = result.strip()
        
        parsed_data = json.loads(result)
        
        # Ensure red_flags exist
        if not parsed_data.get('red_flags'):
            parsed_data['red_flags'] = {}
        
        # Override red_flags based on content analysis
        resume_lower = resume_text.lower()
        
        if any(word in resume_lower for word in ['urgently', 'bored', 'please hire']):
            parsed_data['red_flags']['unprofessional_content'] = True
            parsed_data['red_flags']['desperate_tone'] = True
        
        if any(word in resume_lower for word in ['genius', 'can do any job', 'hardworking']):
            parsed_data['red_flags']['unprofessional_language'] = True
        
        # Check for email and phone
        has_email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) is not None
        has_phone = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) is not None
        if not has_email or not has_phone:
            parsed_data['red_flags']['missing_contact_info'] = True
        
        # Calculate quality score from red flags
        quality_score = calculate_quality_score_from_red_flags(parsed_data['red_flags'])
        parsed_data['resume_quality_score'] = quality_score
        
        # Calculate fit score from red flags (MORE IMPORTANT)
        fit_score = calculate_fit_score_from_red_flags(parsed_data['red_flags'])
        parsed_data['fit_score'] = fit_score
        
        # Set verdict based on score
        if quality_score >= 90:
            parsed_data['resume_quality_verdict'] = "Excellent"
        elif quality_score >= 70:
            parsed_data['resume_quality_verdict'] = "Good"
        elif quality_score >= 50:
            parsed_data['resume_quality_verdict'] = "Average"
        elif quality_score >= 30:
            parsed_data['resume_quality_verdict'] = "Poor"
        elif quality_score >= 10:
            parsed_data['resume_quality_verdict'] = "Very Poor"
        else:
            parsed_data['resume_quality_verdict'] = "Worst"
        
        # Generate observations
        observations = []
        red_flags = parsed_data['red_flags']
        
        if red_flags.get('unprofessional_content'):
            observations.append("⚠ CRITICAL: Resume contains unprofessional content/desperate tone")
        if red_flags.get('unprofessional_language'):
            observations.append("⚠ Contains exaggerated or unprofessional language")
        if red_flags.get('missing_contact_info'):
            observations.append("⚠ Missing professional contact information (email or phone)")
        if red_flags.get('no_work_experience'):
            observations.append("⚠ No valid work experience documented")
        if red_flags.get('irrelevant_skills'):
            observations.append("⚠ Skills listed are irrelevant for professional work")
        if red_flags.get('vague_descriptions'):
            observations.append("⚠ Experience descriptions are vague without specifics")
        if red_flags.get('missing_dates'):
            observations.append("⚠ Missing dates for education or work experience")
        
        if not observations:
            observations.append("✓ Resume meets professional standards")
        
        parsed_data['quality_observations'] = observations
        
        # Ensure email and phone are captured properly
        if has_email and (parsed_data.get('email') == 'Not Provided' or not parsed_data.get('email')):
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
            if email_match:
                parsed_data['email'] = email_match.group()
        
        if has_phone and (parsed_data.get('phone') == 'Not Provided' or not parsed_data.get('phone')):
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text)
            if phone_match:
                parsed_data['phone'] = phone_match.group()
        
        print(f"Fit Score: {fit_score}")
        print(f"Quality Score: {quality_score}")
        print(f"Red Flags: {parsed_data['red_flags']}")
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return generate_fallback_data(resume_text)
    except Exception as e:
        print(f"LLM API error: {str(e)}")
        return generate_fallback_data(resume_text)


def generate_fallback_data(resume_text):
    """Fallback when LLM fails - with proper scoring"""
    
    resume_lower = resume_text.lower() if resume_text else ""
    
    # Detect unprofessional content
    is_unprofessional = any(word in resume_lower for word in UNPROFESSIONAL_KEYWORDS)
    has_years = bool(re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', resume_text)) if resume_text else False
    has_email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text) if resume_text else False
    has_phone = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text) if resume_text else False
    
    red_flags = {
        "missing_contact_info": not has_email or not has_phone,
        "no_work_experience": True,
        "vague_descriptions": True,
        "generic_skills": True,
        "missing_dates": not has_years,
        "unprofessional_language": is_unprofessional,
        "incomplete_education": True,
        "poor_formatting": True,
        "irrelevant_skills": is_unprofessional,
        "over_exaggeration": is_unprofessional,
        "unprofessional_content": is_unprofessional,
        "desperate_tone": is_unprofessional
    }
    
    quality_score = calculate_quality_score_from_red_flags(red_flags)
    fit_score = calculate_fit_score_from_red_flags(red_flags)
    
    if quality_score >= 90:
        verdict = "Excellent"
    elif quality_score >= 70:
        verdict = "Good"
    elif quality_score >= 50:
        verdict = "Average"
    elif quality_score >= 30:
        verdict = "Poor"
    elif quality_score >= 10:
        verdict = "Very Poor"
    else:
        verdict = "Worst"
    
    # Extract email and phone if present
    email = "Not Provided"
    phone = "Not Provided"
    if has_email:
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
        if email_match:
            email = email_match.group()
    if has_phone:
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text)
        if phone_match:
            phone = phone_match.group()
    
    observations = []
    if red_flags.get('unprofessional_content'):
        observations.append("⚠ CRITICAL: Resume contains unprofessional content")
    if red_flags.get('missing_contact_info'):
        observations.append("⚠ Missing professional contact information")
    if red_flags.get('missing_dates'):
        observations.append("⚠ Missing dates in education or experience")
    
    return {
        "name": "Unknown Candidate",
        "gender": "neutral",
        "current_role": "Not Specified",
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": email,
        "phone": phone,
        "linkedin": "Not Provided",
        "professional_summary": "Professional summary not available",
        "skills": ["Not specified"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"},
        "latest_3_experiences": [],
        "fit_score": fit_score,
        "strengths": ["Information not available"],
        "areas_for_improvement": ["Complete all sections professionally", "Remove unprofessional language", "Add proper work experience"],
        "recommended_role": "Entry Level Position",
        "education_raw": ["No year mentioned"],
        "experience_raw": ["No year mentioned"],
        "red_flags": red_flags,
        "resume_quality_score": quality_score,
        "resume_quality_verdict": verdict,
        "quality_observations": observations
    }