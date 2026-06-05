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
    """Enhanced LLM parsing with better structure and scoring"""
    
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
        "fit_score": number between 0-100 (calculate based on skills relevance, experience, and completeness),
        "strengths": ["Key strength 1", "Strength 2", ...],
        "areas_for_improvement": ["Area 1", "Area 2", ...],
        "recommended_role": "Best matching job role based on experience"
    }}

    Resume Text:
    {resume_text[:8000]}

    Return ONLY the JSON object, no other text.
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000
        )
        
        result = response.choices[0].message.content.strip()
        
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
        
        return parsed_data
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response: {result}")
        return generate_fallback_data(resume_text)
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)

def generate_fallback_data(resume_text):
    """Fallback when LLM fails"""
    return {
        "name": "Candidate",
        "gender": "neutral",
        "current_role": "Professional",
        "total_experience_years": 0,
        "location": "Not specified",
        "email": "Not found",
        "phone": "Not found",
        "linkedin": "Not found",
        "professional_summary": resume_text[:200] + "...",
        "skills": ["Communication", "Teamwork", "Problem Solving"],
        "skill_proficiencies": [],
        "certifications": [],
        "education": {"degree": "Not specified", "institution": "Not specified", "year": "N/A"},
        "latest_3_experiences": [],
        "fit_score": 70,
        "strengths": ["Experience in relevant field"],
        "areas_for_improvement": ["Add more quantifiable achievements"],
        "recommended_role": "General Professional"
    }
