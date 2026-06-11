"""
llm_parser.py — Groq-powered resume parser for TalentLens.
"""
import json
import logging
import os
import re
from typing import Optional

import httpx
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# HTTP / Groq client — lazy singleton
# ---------------------------------------------------------------------------
_http_client = None  # type: Optional[httpx.Client]
_groq_client = None  # type: Optional[Groq]


def _get_http_client():  # type: () -> httpx.Client
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(verify=False)
    return _http_client


def _get_client():  # type: () -> Groq
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY environment variable is not set. "
                "Add it to your .env file or Vercel project settings."
            )
        _groq_client = Groq(api_key=api_key, http_client=_get_http_client())
    return _groq_client


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UNPROFESSIONAL_KEYWORDS: dict[str, int] = {
    "urgent": 30,
    "urgently": 35,
    "bored": 40,
    "bored at home": 45,
    "please hire": 40,
    "please hire me": 45,
    "genius": 35,
    "can do any job": 40,
    "whatsapp": 25,
    "instagram": 25,
    "youtube": 20,
    "gaming": 25,
    "sleeping": 30,
    "timepass": 35,
    "don't remember": 30,
    "some school": 35,
    "some college": 35,
    "need job": 30,
    "tiktok": 25,
    "pubg": 25,
    "facebook": 20,
}

MAX_CHARS: int = 20000       # hard cap before smart-truncation
PROMPT_CHARS: int = 12000    # chars forwarded to the LLM prompt
LLM_MODEL: str = "llama-3.1-8b-instant"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _smart_truncate(text: str, max_chars: int) -> str:
    """
    Preserve the most important resume sections (Skills, Experience,
    Education, Certifications) when the text exceeds max_chars.
    """
    if len(text) <= max_chars:
        return text

    section_headers = [
        r"\bskills?\b",
        r"\btechnical skills?\b",
        r"\bcore competenc",
        r"\bexperience\b",
        r"\bwork experience\b",
        r"\bprofessional experience\b",
        r"\bemployment\b",
        r"\beducation\b",
        r"\bacademic\b",
        r"\bcertification",
        r"\bprojects?\b",
        r"\bachievements?\b",
    ]

    lines = text.splitlines()
    section_blocks: dict[str, list[str]] = {}
    current_section = "header"
    section_blocks[current_section] = []

    for line in lines:
        line_lower = line.lower().strip()
        for pattern in section_headers:
            if re.match(pattern, line_lower) and len(line_lower) < 60:
                current_section = line_lower[:30]
                section_blocks.setdefault(current_section, [])
                break
        section_blocks[current_section].append(line)

    priority_keywords = [
        "skill", "experience", "employ", "education", "certif", "project", "header"
    ]
    ordered_sections: list[str] = []
    for kw in priority_keywords:
        for key in section_blocks:
            if kw in key and key not in ordered_sections:
                ordered_sections.append(key)
    for key in section_blocks:
        if key not in ordered_sections:
            ordered_sections.append(key)

    result: list[str] = []
    budget = max_chars
    for key in ordered_sections:
        block = "\n".join(section_blocks[key])
        if len(block) <= budget:
            result.append(block)
            budget -= len(block)
        else:
            result.append(block[:budget])
            break

    return "\n".join(result)


def _unprofessional_score(text: str) -> int:
    text_lower = text.lower()
    return sum(
        penalty
        for keyword, penalty in UNPROFESSIONAL_KEYWORDS.items()
        if keyword in text_lower
    )


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------
def analyze_resume(resume_text):  # type: (str) -> dict
    """Parse a resume with the Groq LLM and return structured data."""
    if not resume_text or len(resume_text.strip()) < 50:
        return generate_fallback_data(resume_text)

    if _unprofessional_score(resume_text) > 50:
        return generate_fallback_data(resume_text, is_worst=True)

    resume_truncated = False
    if len(resume_text) > MAX_CHARS:
        resume_text = _smart_truncate(resume_text, MAX_CHARS)
        resume_truncated = True

    prompt = f"""Analyze this resume and return ONLY valid JSON.

Extract the following information carefully:

{{
    "name": "Full name",
    "current_role": "Current job title",
    "total_experience_years": 0,
    "location": "City, State",
    "email": "email address",
    "phone": "phone number",
    "linkedin": "LinkedIn URL or empty string",
    "professional_summary": "2-3 sentence summary",
    "skills": ["Skill1", "Skill2", "Skill3", "Skill4", "Skill5"],
    "skill_proficiency": [
        {{
            "skill": "Skill name",
            "percentage": 90,
            "category": "Programming Languages"
        }}
    ],
    "certifications": [],
    "education": {{
        "degree": "Degree name",
        "institution": "University name",
        "year": "Graduation year",
        "cgpa": "CGPA or percentage if available, else empty string"
    }},
    "latest_3_experiences": [
        {{
            "company": "Company name",
            "role": "Job title",
            "duration": "2020-2024 or 2022-Present",
            "responsibilities": ["Achievement 1", "Achievement 2"]
        }}
    ],
    "projects": [
        {{
            "name": "Project Name",
            "description": "Brief description (1-2 lines)",
            "technologies": ["Tech1", "Tech2"],
            "duration": "Duration/Date (if available, e.g. Jan 2023 - Mar 2023, or 3 months)",
            "github_url": "GitHub URL if available else empty string",
            "demo_url": "Demo URL if available else empty string",
            "contributions": ["Key contribution 1", "Key contribution 2"]
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
    "recommendation_reason": "1-sentence reason based on certifications/experience (e.g. Based on AWS certifications and 8+ years cloud experience)",
    "education_raw": ["Full education text"],
    "experience_raw": ["Full experience text"]
}}

For skill_proficiency: estimate a percentage (50-99) for each skill based on how prominently and frequently it appears in the resume. Group each skill into one of: "Programming Languages", "Cloud Technologies", "Databases", "AI/ML & GenAI", "DevOps Tools", "Frameworks", or "Other". Include 8-16 skills max.

Resume Text:
{resume_text[:PROMPT_CHARS]}

Return ONLY the JSON object."""

    try:
        logger.info("Calling Groq API (%s)…", LLM_MODEL)
        response = _get_client().chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=3000,

        )

        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*", "", raw)

        parsed: dict = json.loads(raw)

        # Defaults for optional arrays
        if not parsed.get("strengths"):
            parsed["strengths"] = [
                "Professional experience in relevant field",
                "Technical skills alignment",
                "Good communication skills",
            ]

        if not parsed.get("areas_for_improvement"):
            parsed["areas_for_improvement"] = [
                "Add more quantifiable achievements",
                "Include relevant certifications",
                "Improve resume formatting",
            ]

        # Role fallback
        if not parsed.get("current_role") or parsed.get("current_role") == "Professional":
            role_match = re.search(
                r"(?:Senior|Lead|Principal)?\s*"
                r"(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps)\s*"
                r"(?:Engineer|Developer|Architect|Analyst|Manager)",
                resume_text,
                re.IGNORECASE,
            )
            if role_match:
                parsed["current_role"] = role_match.group(0).strip()

        parsed["resume_truncated"] = resume_truncated
        return parsed

    except Exception as exc:
        logger.error("LLM API error: %s", exc)
        return generate_fallback_data(resume_text)


# ---------------------------------------------------------------------------
# Fallback data (no LLM)
# ---------------------------------------------------------------------------
def generate_fallback_data(resume_text, is_worst=False):  # type: (Optional[str], bool) -> dict
    """Return minimal structured data extracted with regex (no LLM)."""
    text = resume_text or ""
    text_lower = text.lower()

    # Role
    role = "Professional"
    _ROLE_PATTERNS = [
        r"(?:Senior|Lead|Principal)?\s*"
        r"(?:Software|Full Stack|Data|Product|Project|Cloud|DevOps)\s*"
        r"(?:Engineer|Developer|Architect|Analyst|Manager)",
        r"(?:Python|Java|JavaScript|React|AWS)\s*(?:Developer|Engineer)",
    ]
    for pattern in _ROLE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE) if text else None
        if m:
            role = m.group(0).strip()
            break

    # Name
    name = "Candidate"
    name_m = re.search(
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text[:200], re.MULTILINE
    )
    if name_m:
        name = name_m.group(1)

    # Contact
    email = "Not Provided"
    phone = "Not Provided"
    email_m = re.search(r"[\w.\-]+@[\w.\-]+\.\w+", text)
    if email_m:
        email = email_m.group()
    phone_m = re.search(
        r"(\+?\d{1,3}[.\-\s]?)?\(?\d{3}\)?[.\-\s]?\d{3}[.\-\s]?\d{4}", text
    )
    if phone_m:
        phone = phone_m.group()

    missing_contact = email == "Not Provided" or phone == "Not Provided"

    if is_worst:
        return {
            "name": name,
            "current_role": "Not Specified",
            "total_experience_years": 0,
            "location": "Not Specified",
            "email": email,
            "phone": phone,
            "linkedin": "Not Provided",
            "professional_summary": "This resume requires a complete rewrite.",
            "skills": ["Not specified"],
            "certifications": [],
            "education": {
                "degree": "Not Specified",
                "institution": "Not Specified",
                "year": "Not Specified",
            },
            "latest_3_experiences": [],
            "projects": [],
            "fit_score": 15,
            "strengths": ["Not available — resume needs a complete rewrite"],
            "areas_for_improvement": [
                "Complete resume rewrite required",
                "Remove all unprofessional language",
                "Add proper work experience with dates",
                "Include relevant professional skills",
                "Add complete contact information",
            ],
            "recommended_role": "Entry Level",
            "recommendation_reason": "Resume contains unprofessional content and requires a complete rewrite.",
            "education_raw": ["No year mentioned"],
            "experience_raw": ["No year mentioned"],
            "red_flags": {
                "unprofessional_content": True,
                "missing_contact_info": missing_contact,
                "no_work_experience": True,
                "irrelevant_skills": True,
                "missing_dates": True,
            },
            "resume_quality_score": 15,
            "resume_quality_verdict": "Worst",
            "quality_observations": [
                "⚠️ CRITICAL: Resume contains unprofessional content",
                "⚠️ No valid work experience documented",
                "⚠️ Complete resume rewrite needed",
            ],
        }

    return {
        "name": name,
        "current_role": role,
        "total_experience_years": 0,
        "location": "Not Specified",
        "email": email,
        "phone": phone,
        "linkedin": "Not Provided",
        "professional_summary": "Professional summary not available.",
        "skills": ["Communication", "Teamwork", "Problem Solving"],
        "certifications": [],
        "education": {
            "degree": "Not Specified",
            "institution": "Not Specified",
            "year": "Not Specified",
        },
        "latest_3_experiences": [],
        "projects": [],
        "fit_score": 50,
        "strengths": [
            "Professional experience in relevant field",
            "Technical skills foundation",
            "Good communication abilities",
        ],
        "areas_for_improvement": [
            "Complete all sections with detailed information",
            "Add quantifiable achievements to experience",
            "Include relevant certifications",
            "Add proper dates to education and experience",
        ],
        "recommended_role": "Entry Level Position",
        "recommendation_reason": "Based on academic background and initial technical skill set.",
        "education_raw": ["No year mentioned"],
        "experience_raw": ["No year mentioned"],
        "red_flags": {
            "missing_contact_info": missing_contact,
            "missing_dates": True,
        },
        "resume_quality_score": 50,
        "resume_quality_verdict": "Average",
        "quality_observations": [
            "Missing professional contact information",
            "Work experience needs more details",
            "Education section incomplete",
            "Add dates to experience and education",
        ],
    }