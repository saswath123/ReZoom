import re
from datetime import datetime

class GapAnalyzer:
    """Career Gap Detection & Employment Continuity Analysis"""
    
    def __init__(self):
        self.career_break_keywords = [
            'career break', 'career gap', 'sabbatical', 'personal reasons',
            'family commitment', 'health break', 'parental leave', 'career hiatus',
            'time off', 'employment gap', 'break from work', 'upskilling break'
        ]
    
    def extract_years_from_text(self, text):
        """Extract all years from text"""
        if not text:
            return []
        years = re.findall(r'\b(19[0-9]{2}|20[0-2][0-9]|2030)\b', str(text))
        return [int(y) for y in years]
    
    def has_valid_years(self, text):
        """Check if text contains valid years"""
        if not text:
            return False
        return len(self.extract_years_from_text(text)) > 0
    
    def parse_date_range(self, text):
        """Extract start and end years from a date range string"""
        if not text:
            return None, None
        
        text = str(text)
        
        # Pattern: YYYY-YYYY or YYYY - YYYY or YYYY–YYYY
        match = re.search(r'(\d{4})\s*[-–—]\s*(\d{4})', text)
        if match:
            return int(match.group(1)), int(match.group(2))
        
        # Pattern: YYYY-Present
        match = re.search(r'(\d{4})\s*[-–—]\s*[Pp]resent', text)
        if match:
            return int(match.group(1)), datetime.now().year
        
        # Pattern: Single year
        match = re.search(r'(\d{4})', text)
        if match:
            year = int(match.group(1))
            return year, year
        
        return None, None
    
    def is_career_break(self, text):
        """Check if text describes a career break"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.career_break_keywords)
    
    def extract_education_entries(self, education_raw):
        """Extract education entries with years"""
        education_entries = []
        
        if not education_raw:
            return education_entries
        
        for edu in education_raw:
            if not edu:
                continue
            
            has_years = self.has_valid_years(edu)
            start, end = self.parse_date_range(edu)
            
            education_entries.append({
                'text': edu,
                'start_year': start,
                'end_year': end if end else start,
                'has_years': has_years
            })
        
        return education_entries
    
    def extract_experience_entries(self, experience_raw):
        """Extract experience entries with years and detect career breaks"""
        experience_entries = []
        
        if not experience_raw:
            return experience_entries
        
        for exp in experience_raw:
            if not exp:
                continue
            
            has_years = self.has_valid_years(exp)
            start, end = self.parse_date_range(exp)
            is_break = self.is_career_break(exp)
            
            experience_entries.append({
                'text': exp,
                'start_year': start,
                'end_year': end if end else start,
                'has_years': has_years,
                'is_career_break': is_break,
                'is_present': 'present' in str(exp).lower()
            })
        
        # Sort by start year (entries without years go to the end)
        experience_entries.sort(key=lambda x: x['start_year'] if x['start_year'] else 9999)
        
        return experience_entries
    
    def analyze_education_to_employment_gap(self, education_entries, experience_entries):
        """Detect gap between education completion and first job"""
        if not education_entries or not experience_entries:
            return None
        
        # Get latest education with valid years
        edu_with_years = [e for e in education_entries if e.get('has_years')]
        
        # If no education has years
        if not edu_with_years:
            return {
                'type': 'Education-to-Employment Gap',
                'from_year': 'Not specified',
                'to_year': 'Not specified',
                'duration_years': 'Unknown',
                'description': '❓ Cannot determine - missing graduation year'
            }
        
        latest_edu = max(edu_with_years, key=lambda x: x['end_year'] if x['end_year'] else 0)
        edu_end_year = latest_edu['end_year']
        
        # Get first non-career-break job with valid years
        first_job = None
        for exp in experience_entries:
            if not exp.get('is_career_break') and exp.get('has_years') and exp.get('start_year'):
                first_job = exp
                break
        
        if not first_job:
            return None
        
        job_start_year = first_job['start_year']
        
        if job_start_year and edu_end_year and job_start_year > edu_end_year:
            gap_years = job_start_year - edu_end_year
            return {
                'type': 'Education-to-Employment Gap',
                'from_year': edu_end_year,
                'to_year': job_start_year,
                'duration_years': gap_years,
                'description': f"Graduation ({edu_end_year}) → First Job ({job_start_year})"
            }
        elif not edu_end_year:
            return {
                'type': 'Education-to-Employment Gap',
                'from_year': 'Not specified',
                'to_year': job_start_year if job_start_year else 'Not specified',
                'duration_years': 'Unknown',
                'description': '❓ Cannot determine - missing graduation year'
            }
        
        return None
    
    def analyze_employment_gaps(self, experience_entries):
        """Detect gaps between consecutive employments"""
        gaps = []
        
        # Filter out career breaks and entries without years
        regular_jobs = [exp for exp in experience_entries if not exp.get('is_career_break') and exp.get('has_years')]
        
        for i in range(len(regular_jobs) - 1):
            current_end = regular_jobs[i]['end_year']
            next_start = regular_jobs[i + 1]['start_year']
            
            if current_end and next_start and next_start > current_end:
                gap_years = next_start - current_end
                if gap_years >= 1:
                    gaps.append({
                        'type': 'Employment Gap',
                        'from_year': current_end,
                        'to_year': next_start,
                        'duration_years': gap_years,
                        'description': f"Employment gap of {gap_years} year{'s' if gap_years != 1 else ''}"
                    })
        
        return gaps
    
    def analyze_career_breaks(self, experience_entries):
        """Extract career breaks as gaps"""
        career_breaks = []
        
        for exp in experience_entries:
            if exp.get('is_career_break'):
                has_years = exp.get('has_years', False)
                start_year = exp['start_year']
                end_year = exp['end_year']
                
                if has_years and start_year and end_year:
                    duration = end_year - start_year
                    if duration > 0:
                        career_breaks.append({
                            'type': 'Career Break',
                            'from_year': start_year,
                            'to_year': end_year,
                            'duration_years': duration,
                            'description': f"Career Break ({start_year} - {end_year})"
                        })
                    else:
                        career_breaks.append({
                            'type': 'Career Break',
                            'from_year': start_year,
                            'to_year': end_year,
                            'duration_years': 'Less than 1 year',
                            'description': f"Career Break (within {start_year})"
                        })
                else:
                    career_breaks.append({
                        'type': 'Career Break',
                        'from_year': 'Not specified',
                        'to_year': 'Not specified',
                        'duration_years': 'Unknown',
                        'description': "❓ Career Break - years not specified"
                    })
        
        return career_breaks
    
    def analyze_current_employment_gap(self, experience_entries):
        """Detect if candidate is currently unemployed"""
        if not experience_entries:
            return {'status': 'No experience listed', 'gap': None}
        
        # Filter out career breaks and get jobs with years
        regular_jobs = [exp for exp in experience_entries if not exp.get('is_career_break') and exp.get('has_years')]
        
        if not regular_jobs:
            return {'status': '❓ Cannot determine - missing dates', 'gap': None}
        
        # Get latest job
        latest_job = max(regular_jobs, key=lambda x: x['end_year'] if x['end_year'] else 0)
        
        current_year = datetime.now().year
        
        if latest_job.get('is_present'):
            return {'status': 'Currently Employed ✅', 'gap': None}
        
        if latest_job['end_year'] and latest_job['end_year'] < current_year:
            gap_years = current_year - latest_job['end_year']
            if gap_years >= 1:
                return {
                    'status': 'Not Currently Employed ⚠️',
                    'gap': {
                        'from_year': latest_job['end_year'],
                        'to_year': current_year,
                        'duration_years': gap_years,
                        'description': f"Last Job ({latest_job['end_year']}) → Present ({current_year})"
                    }
                }
        
        return {'status': 'Currently Employed ✅', 'gap': None}
    
    def get_risk_indicator(self, total_gap_years):
        """Get risk indicator based on total gap duration"""
        if total_gap_years == 0:
            return "🟢 No Gap (0 Years)"
        elif total_gap_years == 'Unknown':
            return "🟡 Cannot Determine - Missing Date Information"
        elif total_gap_years <= 1:
            return "🟡 Minor Gap (Less than 1 Year)"
        elif total_gap_years <= 2:
            return "🟡 Minor Gap (1-2 Years)"
        elif total_gap_years <= 3:
            return "🟠 Moderate Gap (2-3 Years)"
        else:
            return "🔴 Significant Gap (More than 3 Years)"
    
    def analyze_complete_gaps(self, education_raw, experience_raw):
        """Complete gap analysis - main function to call"""
        
        print("=" * 50)
        print("Gap Analyzer Debug:")
        print(f"Education Raw: {education_raw}")
        print(f"Experience Raw: {experience_raw}")
        
        # Parse education and experience
        education_entries = self.extract_education_entries(education_raw)
        experience_entries = self.extract_experience_entries(experience_raw)
        
        print(f"Education Entries: {education_entries}")
        print(f"Experience Entries: {experience_entries}")
        
        # Perform analyses
        edu_to_employment_gap = self.analyze_education_to_employment_gap(education_entries, experience_entries)
        employment_gaps = self.analyze_employment_gaps(experience_entries)
        career_breaks = self.analyze_career_breaks(experience_entries)
        current_status = self.analyze_current_employment_gap(experience_entries)
        
        # Calculate total gap
        total_gap_years = 0
        gap_years_known = True
        
        if edu_to_employment_gap:
            if edu_to_employment_gap.get('duration_years') == 'Unknown':
                gap_years_known = False
            else:
                total_gap_years += edu_to_employment_gap['duration_years']
        
        for gap in employment_gaps:
            total_gap_years += gap['duration_years']
        
        for gap in career_breaks:
            if gap.get('duration_years') == 'Unknown':
                gap_years_known = False
            elif isinstance(gap.get('duration_years'), (int, float)):
                total_gap_years += gap['duration_years']
        
        if current_status.get('gap'):
            total_gap_years += current_status['gap']['duration_years']
        
        if not gap_years_known:
            total_gap_years = 'Unknown'
        else:
            total_gap_years = round(total_gap_years, 1)
        
        result = {
            'current_status': current_status['status'],
            'education_to_employment_gap': edu_to_employment_gap,
            'employment_gaps': employment_gaps,
            'career_breaks': career_breaks,
            'current_employment_gap': current_status.get('gap'),
            'total_gap_years': total_gap_years,
            'risk_indicator': self.get_risk_indicator(total_gap_years)
        }
        
        print(f"Gap Analysis Result: {result}")
        print("=" * 50)
        
        return result


# For testing
if __name__ == "__main__":
    analyzer = GapAnalyzer()
    
    # Test with sample data
    education_raw = [
        "B.Tech in Computer Science (2017 - 2022) XYZ University"
    ]
    
    experience_raw = [
        "Career Break (2023 - 2024) Focused on upskilling",
        "GenAI Developer (2025 - Present) Built AI applications"
    ]
    
    result = analyzer.analyze_complete_gaps(education_raw, experience_raw)
    print("\n" + "=" * 50)
    print("FINAL RESULT:")
    print("=" * 50)
    print(json.dumps(result, indent=2))