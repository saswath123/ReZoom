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

# Generic unprofessional keywords (works for any resume)
UNPROFESSIONAL_KEYWORDS = {
    'urgent': 30, 'urgently': 35, 'bored': 40, 'please hire': 40,
    'genius': 35, 'can do any job': 40, 'whatsapp': 25, 'instagram': 25,
    'youtube': 20, 'gaming': 25, 'sleeping': 30, 'timepass': 35,
    "don't remember": 30, 'need job': 30, 'tiktok': 25, 'pubg': 25
}


def analyze_resume(resume_text):
    """Generic resume parser - works for ANY resume"""
    
    if not resume_text or len(resume_text.strip()) < 50:
        return generate_fallback_data(resume_text)
    
    # Check for unprofessional content
    resume_lower = resume_text.lower()
    unprofessional_score = sum(penalty for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items() if keyword in resume_lower)
    
    if unprofessional_score > 50:
        return generate_fallback_data(resume_text, is_worst=True)
    
    # Limit text length for API
    if len(resume_text) > 10000:
        resume_text = resume_text[:10000]
    
    prompt = f"""
    Analyze this resume and return ONLY valid JSON. Extract ALL information.

    Return this EXACT structure (do not add or remove fields):

    {{
        "name": "Full name from resume",
        "current_role": "Current or most recent job title",
        "total_experience_years": number,
        "location": "City, Country from contact",
        "email": "email address",
        "phone": "phone number",
        "linkedin": "LinkedIn URL if present",
        "professional_summary": "Professional summary or about section",
        "skills": ["Skill 1", "Skill 2", "Skill 3", "Skill 4", "Skill 5"],
        "certifications": ["Certification 1", "Certification 2"],
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
                "responsibilities": ["Responsibility 1", "Responsibility 2"]
            }}
        ],
        "fit_score": 75,
        "strengths": ["Strength 1", "Strength 2", "Strength 3"],
        "areas_for_improvement": ["Improvement 1", "Improvement 2"],
        "recommended_role": "Suggested job role",
        "education_raw": ["Full education text"],
        "experience_raw": ["Full experience text"]
    }}

    Resume Text:
    {resume_text}

    Return ONLY valid JSON. No other text.
    """
    
    try:
        print("Calling Groq API...")
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=3000
        )
        
        result = response.choices[0].message.content.strip()
        result = re.sub(r'```json\s*', '', result)
        result = re.sub(r'```\s*', '', result)
        
        parsed_data = json.loads(result)
        
        # Ensure all required fields exist (generic fallbacks)
        if not parsed_data.get('name'):
            parsed_data['name'] = extract_name_generic(resume_text)
        
        if not parsed_data.get('current_role'):
            parsed_data['current_role'] = extract_role_generic(resume_text)
        
        if not parsed_data.get('skills'):
            parsed_data['skills'] = extract_skills_generic(resume_text)
        
        if not parsed_data.get('certifications'):
            parsed_data['certifications'] = extract_certifications_generic(resume_text)
        
        if not parsed_data.get('education') or not parsed_data.get('education', {}).get('degree'):
            parsed_data['education'] = extract_education_generic(resume_text)
        
        if not parsed_data.get('latest_3_experiences'):
            parsed_data['latest_3_experiences'] = extract_experiences_generic(resume_text)
        
        if not parsed_data.get('strengths'):
            parsed_data['strengths'] = ["Professional experience", "Technical skills", "Domain expertise"]
        
        if not parsed_data.get('areas_for_improvement'):
            parsed_data['areas_for_improvement'] = ["Add quantifiable achievements", "Include relevant certifications"]
        
        if not parsed_data.get('email'):
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
            parsed_data['email'] = email_match.group() if email_match else "Not Provided"
        
        if not parsed_data.get('phone'):
            phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_text)
            parsed_data['phone'] = phone_match.group() if phone_match else "Not Provided"
        
        if not parsed_data.get('location'):
            location_match = re.search(r'([A-Za-z]+,\s*[A-Za-z\s]+)(?=\||$|Email|Phone)', resume_text[:300], re.IGNORECASE)
            parsed_data['location'] = location_match.group(1).strip() if location_match else "Not Specified"
        
        return parsed_data
        
    except Exception as e:
        print(f"LLM API error: {e}")
        return generate_fallback_data(resume_text)


# ============================================================
# GENERIC EXTRACTION FUNCTIONS (Work for ANY resume)
# ============================================================

def extract_name_generic(text):
    """Extract name from ANY resume"""
    # Look for name patterns at the beginning of resume
    lines = text.split('\n')[:10]
    for line in lines:
        line = line.strip()
        # Name usually has 2-3 capitalized words
        if len(line.split()) in [2, 3] and all(word[0].isupper() for word in line.split() if word):
            return line
    return "Candidate"


def extract_role_generic(text):
    """Extract role/title from ANY resume"""
    # Look for common role patterns
    patterns = [
        r'(?:Senior|Lead|Principal|Junior|Associate)?\s*(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps|AI|ML|GenAI|Frontend|Backend)\s*(?:Engineer|Developer|Architect|Analyst|Manager|Scientist)',
        r'(?:Machine Learning|Data|AI)\s*(?:Engineer|Scientist)',
        r'(?:Product|Project|Program)\s*(?:Manager)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:Engineer|Developer)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return "Professional"


def extract_skills_generic(text):
    """Extract skills from ANY resume"""
    skills = []
    
    # Look for skills section
    skills_section = re.search(r'SKILLS(?:\s*&?\s*TOOLS)?(.*?)(?:EXPERIENCE|EDUCATION|CERTIFICATIONS|PROJECTS|$)', text, re.IGNORECASE | re.DOTALL)
    if skills_section:
        skills_text = skills_section.group(1)
        # Extract words that look like skills (capitalized or technical terms)
        skill_matches = re.findall(r'\b([A-Z][a-z]+(?:\+[A-Z][a-z]+)?|[A-Z]{2,})\b', skills_text)
        skills = list(dict.fromkeys(skill_matches))[:12]
    
    if not skills:
        # Common technical skills to look for
        common_skills = ['Python', 'Java', 'JavaScript', 'AWS', 'SQL', 'React', 'Node.js', 'Docker', 'Kubernetes', 'Git']
        skills = [s for s in common_skills if s.lower() in text.lower()]
    
    return skills if skills else ["Communication", "Teamwork", "Problem Solving"]


def extract_certifications_generic(text):
    """Extract certifications from ANY resume"""
    certifications = []
    
    # Look for certifications section
    cert_section = re.search(r'CERTIFICATIONS?(.*?)(?:EDUCATION|EXPERIENCE|SKILLS|PROJECTS|$)', text, re.IGNORECASE | re.DOTALL)
    if cert_section:
        cert_text = cert_section.group(1)
        # Extract lines that look like certifications
        lines = cert_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 5 and len(line) < 100:
                # Look for certification keywords
                if any(keyword in line.lower() for keyword in ['certified', 'aws', 'microsoft', 'google', 'scrum', 'pmp', 'security']):
                    certifications.append(line)
    
    # Also look for AWS/Azure/Google certs anywhere
    cert_patterns = [
        r'(AWS Certified[A-Za-z\s]+)',
        r'(Microsoft Certified[A-Za-z\s]+)',
        r'(Google Certified[A-Za-z\s]+)',
        r'(Certified Scrum[A-Za-z\s]+)',
    ]
    for pattern in cert_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.strip() and match.strip() not in certifications:
                certifications.append(match.strip())
    
    return certifications[:5]


def extract_education_generic(text):
    """Extract education from ANY resume"""
    education = {"degree": "Not Specified", "institution": "Not Specified", "year": "Not Specified"}
    
    # Look for education section
    edu_section = re.search(r'EDUCATION(.*?)(?:EXPERIENCE|SKILLS|CERTIFICATIONS|PROJECTS|$)', text, re.IGNORECASE | re.DOTALL)
    if edu_section:
        edu_text = edu_section.group(1)
        
        # Extract degree
        degree_patterns = [
            r'(B\.?Tech|M\.?Tech|B\.?E|M\.?E|Bachelor|Master|PhD|MBA|B\.Sc|M\.Sc|B\.A|M\.A)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+in\s+([A-Z][a-z]+)',
        ]
        for pattern in degree_patterns:
            match = re.search(pattern, edu_text, re.IGNORECASE)
            if match:
                education['degree'] = match.group(0).strip()[:50]
                break
        
        # Extract institution
        institution_patterns = [
            r'(?:University|College|Institute|School)\s+of\s+([A-Z][a-z]+)',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:University|College)',
        ]
        for pattern in institution_patterns:
            match = re.search(pattern, edu_text, re.IGNORECASE)
            if match:
                education['institution'] = match.group(0).strip()[:50]
                break
        
        # Extract year
        year_match = re.search(r'\b(19|20)\d{2}\b', edu_text)
        if year_match:
            education['year'] = year_match.group()
    
    return education


def extract_experiences_generic(text):
    """Extract work experiences from ANY resume"""
    experiences = []
    
    # Look for experience section
    exp_section = re.search(r'(?:WORK\s+)?EXPERIENCE(.*?)(?:EDUCATION|SKILLS|CERTIFICATIONS|PROJECTS|$)', text, re.IGNORECASE | re.DOTALL)
    if exp_section:
        exp_text = exp_section.group(1)
        
        # Split by company patterns
        company_matches = re.finditer(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:,|\s+-\s+|\s+\|\s+)(\d{4}\s*-\s*(?:\d{4}|Present))', exp_text, re.IGNORECASE)
        
        for match in company_matches:
            company = match.group(1).strip()
            duration = match.group(2).strip()
            
            # Extract role (look for title before company or in parentheses)
            role = "Professional"
            role_match = re.search(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:Engineer|Developer|Manager|Analyst)', exp_text[:match.start()])
            if role_match:
                role = role_match.group(0).strip()
            
            # Extract responsibilities (bulleted text after the match)
            resp_text = exp_text[match.end():match.end()+200]
            responsibilities = []
            for line in resp_text.split('\n')[:3]:
                line = line.strip()
                if line.startswith(('•', '-', '*')) or (line and len(line) > 20):
                    responsibilities.append(line[:100])
            
            if not responsibilities:
                responsibilities = ["Key responsibilities and achievements"]
            
            experiences.append({
                "company": company[:50],
                "role": role[:50],
                "duration": duration[:30],
                "responsibilities": responsibilities[:3]
            })
            
            if len(experiences) >= 3:
                break
    
    return experiences[:3]


def generate_fallback_data(resume_text, is_worst=False):
    """Generic fallback - works for ANY resume"""
    
    is_worst = is_worst or False
    
    return {
        "name": extract_name_generic(resume_text),
        "current_role": extract_role_generic(resume_text),
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": "Not Provided",
        "phone": "Not Provided",
        "linkedin": "Not Provided",
        "professional_summary": "Professional summary not available",
        "skills": extract_skills_generic(resume_text),
        "certifications": extract_certifications_generic(resume_text),
        "education": extract_education_generic(resume_text),
        "latest_3_experiences": extract_experiences_generic(resume_text),
        "fit_score": 15 if is_worst else 50,
        "strengths": ["Professional experience", "Technical skills", "Domain knowledge"] if not is_worst else ["Resume needs improvement"],
        "areas_for_improvement": ["Complete all sections", "Add quantifiable achievements", "Include relevant certifications"],
        "recommended_role": extract_role_generic(resume_text),
        "education_raw": ["Education information extracted"],
        "experience_raw": ["Experience information extracted"],
        "red_flags": {
            "missing_contact_info": True,
            "missing_dates": True
        } if is_worst else {},
        "resume_quality_score": 15 if is_worst else 50,
        "resume_quality_verdict": "Worst" if is_worst else "Average",
        "quality_observations": ["Resume needs professional improvement"] if is_worst else ["Basic resume structure detected"]
    }