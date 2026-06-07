from groq import Groq
from dotenv import load_dotenv
import os
import json
import httpx
import re

load_dotenv()

# Keep verify=False as requested for office network
http_client = httpx.Client(verify=False)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
    http_client=http_client
)

def analyze_resume(resume_text):
    """Enhanced LLM parsing with raw data extraction for gap analysis"""
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON. Do not include any markdown or explanatory text.

    Extract the following information in this exact JSON format:

    {{
        "name": "Full name",
        "gender": "male/female/neutral (infer from name if possible)",
        "current_role": "Current job title",
        "total_experience_years": number,
        "location": "City, Country",
        "email": "email address",
        "phone": "phone number",
        "linkedin": "LinkedIn URL or username",
        "professional_summary": "Brief 2-3 sentence summary",
        "skills": ["Skill1", "Skill2", ...],
        "skill_proficiencies": [{{"skill": "Skill name", "level": "Beginner/Intermediate/Expert"}}],
        "certifications": ["Cert1", "Cert2", ...],
        "education": {{
            "degree": "Degree name",
            "institution": "University/College name",
            "year": "Graduation year"
        }},
        "latest_3_experiences": [
            {{
                "company": "Company name",
                "role": "Job title",
                "duration": "Start - End",
                "responsibilities": ["Achievement 1", "Achievement 2"]
            }}
        ],
        "fit_score": number between 0-100,
        "strengths": ["Key strength 1", "Strength 2", ...],
        "areas_for_improvement": ["Area 1", "Area 2", ...],
        "recommended_role": "Best matching job role based on experience",
        
        "education_raw": [
            "Full education entry exactly as written in resume. Example: 'B.Tech in Computer Science (2017 - 2022) XYZ University'",
            "Include ALL education entries with their dates"
        ],
        
        "experience_raw": [
            "Full experience entry exactly as written in resume. Example: 'GenAI Developer (2025 - Present) Built AI-powered applications'",
            "ALSO include any career breaks, sabbaticals, or gaps. Example: 'Career Break (2023 - 2024) Focused on upskilling'",
            "Include ALL work experience and career break entries"
        ]
    }}

    IMPORTANT INSTRUCTIONS:
    1. For education_raw: Copy the EXACT text from the Education section including years.
    2. For experience_raw: Copy the EXACT text from Experience and Career Break sections.
    3. Keep all dates in their original format (YYYY-YYYY, YYYY-Present, etc.).
    4. Do NOT summarize or modify the raw text.

    Resume Text:
    {resume_text[:8000]}

    Return ONLY the JSON object, no other text.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        print(f"Raw response received: {len(result)} chars")
        
        # Clean markdown formatting
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        
        # Parse JSON
        parsed_data = json.loads(result)
        
        # Validate required fields
        required_fields = ['name', 'skills', 'latest_3_experiences']
        for field in required_fields:
            if field not in parsed_data:
                parsed_data[field] = [] if field == 'skills' or field == 'latest_3_experiences' else "Not specified"
        
        # Ensure fit_score exists
        if 'fit_score' not in parsed_data:
            parsed_data['fit_score'] = 75
        
        # ===== CRITICAL: Ensure education_raw and experience_raw exist =====
        if not parsed_data.get('education_raw'):
            # Extract from education object
            edu = parsed_data.get('education', {})
            if edu.get('degree') or edu.get('institution'):
                year = edu.get('year', '')
                degree = edu.get('degree', '')
                institution = edu.get('institution', '')
                if year:
                    parsed_data['education_raw'] = [f"{degree} at {institution} ({year})"]
                else:
                    parsed_data['education_raw'] = [f"{degree} at {institution}"]
            else:
                # Try to extract from resume text
                parsed_data['education_raw'] = extract_education_from_text(resume_text)
        
        if not parsed_data.get('experience_raw'):
            # Extract from latest_3_experiences
            experiences = parsed_data.get('latest_3_experiences', [])
            parsed_data['experience_raw'] = []
            for exp in experiences:
                exp_text = f"{exp.get('role', '')} at {exp.get('company', '')} ({exp.get('duration', '')})"
                parsed_data['experience_raw'].append(exp_text)
            
            # Also extract career breaks from resume text
            career_breaks = extract_career_breaks_from_text(resume_text)
            parsed_data['experience_raw'].extend(career_breaks)
        
        print(f"education_raw: {parsed_data.get('education_raw')}")
        print(f"experience_raw: {parsed_data.get('experience_raw')}")
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {result if 'result' in locals() else 'No response'}")
        return generate_fallback_data(resume_text)
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)


def extract_education_from_text(text):
    """Extract education information from raw text"""
    if not text:
        return ["Education information not found"]
    
    # Look for education section
    edu_match = re.search(r'EDUCATION(.*?)(?:EXPERIENCE|SKILLS|PROJECTS|WORK|$)', text, re.IGNORECASE | re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).strip()
        # Get first few lines
        lines = edu_text.split('\n')[:3]
        for line in lines:
            if line.strip() and any(c.isdigit() for c in line):
                return [line.strip()]
    
    # Look for degree pattern
    degree_match = re.search(r'(B\.?Tech|M\.?Tech|B\.?E|M\.?E|Bachelor|Master|PhD|MBA).*?(\d{4})', text, re.IGNORECASE)
    if degree_match:
        return [degree_match.group(0).strip()]
    
    return ["Education information not found"]


def extract_career_breaks_from_text(text):
    """Extract career break information from raw text"""
    if not text:
        return []
    
    career_breaks = []
    
    # Look for career break section
    break_match = re.search(r'CAREER BREAK(.*?)(?:EXPERIENCE|SKILLS|PROJECTS|EDUCATION|$)', text, re.IGNORECASE | re.DOTALL)
    if break_match:
        break_text = break_match.group(1).strip()
        # Extract date range
        date_match = re.search(r'(\d{4})\s*[-–—]\s*(\d{4})', break_text)
        if date_match:
            career_breaks.append(f"Career Break ({date_match.group(1)} - {date_match.group(2)}) {break_text[:100]}")
        else:
            career_breaks.append(f"Career Break {break_text[:100]}")
    
    # Also look for gap patterns in text
    gap_match = re.search(r'gap.*?(\d{4})\s*[-–—]\s*(\d{4})', text, re.IGNORECASE)
    if gap_match and not career_breaks:
        career_breaks.append(f"Career Gap ({gap_match.group(1)} - {gap_match.group(2)})")
    
    return career_breaks


def generate_fallback_data(resume_text):
    """Fallback when LLM fails"""
    # Try to extract raw data from text
    education_raw = extract_education_from_text(resume_text)
    experience_raw = extract_career_breaks_from_text(resume_text)
    
    # Also try to extract normal experience
    exp_match = re.search(r'EXPERIENCE(.*?)(?:EDUCATION|SKILLS|PROJECTS|$)', resume_text, re.IGNORECASE | re.DOTALL)
    if exp_match:
        exp_text = exp_match.group(1).strip()
        lines = exp_text.split('\n')[:2]
        for line in lines:
            if line.strip() and any(c.isdigit() for c in line):
                experience_raw.append(line.strip())
    
    return {
        "name": "Candidate",
        "gender": "neutral",
        "current_role": "Professional",
        "total_experience_years": 0,
        "location": "Not specified",
        "email": "Not found",
        "phone": "Not found",
        "linkedin": "Not found",
        "professional_summary": resume_text[:200] + "..." if resume_text else "Professional summary not available",
        "skills": ["Communication", "Teamwork", "Problem Solving"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {"degree": "Not specified", "institution": "Not specified", "year": "N/A"},
        "latest_3_experiences": [],
        "fit_score": 70,
        "strengths": ["Experience in relevant field"],
        "areas_for_improvement": ["Add more quantifiable achievements"],
        "recommended_role": "General Professional",
        "education_raw": education_raw,
        "experience_raw": experience_raw
    }