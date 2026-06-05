import re
from datetime import datetime
from dateutil import parser
import calendar

class GapAnalyzer:
    """Career Gap Detection & Employment Continuity Analysis"""
    
    def __init__(self):
        self.excluded_roles = [
            'freelance', 'freelancing', 'self-employed', 'self employment',
            'consultant', 'consulting', 'startup founder', 'founder',
            'entrepreneur', 'contractor', 'intern', 'internship'
        ]
    
    def parse_date(self, date_str):
        """Parse various date formats to datetime"""
        if not date_str or date_str == 'Present':
            return None
        
        date_str = str(date_str).strip()
        
        # Handle year only (YYYY)
        if re.match(r'^\d{4}$', date_str):
            return datetime(int(date_str), 1, 1)
        
        # Handle MM/YYYY
        if re.match(r'^\d{1,2}/\d{4}$', date_str):
            month, year = date_str.split('/')
            return datetime(int(year), int(month), 1)
        
        # Handle Month YYYY
        try:
            return parser.parse(date_str, fuzzy=True)
        except:
            return None
    
    def format_date_for_display(self, date_obj):
        """Format datetime object for display"""
        if not date_obj:
            return "Present"
        return date_obj.strftime("%Y")
    
    def calculate_gap_years(self, end_date, start_date):
        """Calculate gap in years between two dates"""
        if not end_date or not start_date:
            return None
        
        gap_days = (start_date - end_date).days
        if gap_days < 0:  # Overlapping dates
            return 0
        
        gap_years = gap_days / 365.25
        return round(gap_years, 1)
    
    def is_excluded_role(self, role):
        """Check if role should be excluded from gap analysis"""
        role_lower = role.lower()
        return any(excluded in role_lower for excluded in self.excluded_roles)
    
    def extract_dates_from_text(self, text, item_type="experience"):
        """Extract dates from education or experience text"""
        date_patterns = [
            (r'(\d{4})\s*[-–—]\s*(\d{4}|Present)', 'year-year'),
            (r'(\d{1,2}/\d{4})\s*[-–—]\s*(\d{1,2}/\d{4}|Present)', 'monthyear-monthyear'),
            (r'([A-Za-z]+\s+\d{4})\s*[-–—]\s*([A-Za-z]+\s+\d{4}|Present)', 'month-year-month-year'),
            (r'(\d{4})\s*[-–—]\s*(Present)', 'year-present'),
            (r'(\d{1,2}/\d{4})\s*[-–—]\s*(Present)', 'monthyear-present'),
        ]
        
        for pattern, date_type in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_str, end_str = match.groups()
                start_date = self.parse_date(start_str)
                end_date = self.parse_date(end_str) if end_str != 'Present' else None
                return start_date, end_date
        
        return None, None
    
    def analyze_education_to_employment_gap(self, education_list, experience_list):
        """Detect gap between education completion and first job"""
        if not education_list or not experience_list:
            return None
        
        # Get latest education end date
        latest_education_end = None
        latest_education_name = None
        
        for edu in education_list:
            start_date, end_date = self.extract_dates_from_text(edu, "education")
            if end_date and (not latest_education_end or end_date > latest_education_end):
                latest_education_end = end_date
                # Extract degree name
                degree_match = re.search(r'([A-Za-z\s]+(?:Degree|Bachelor|Master|PhD|MBA))', edu, re.IGNORECASE)
                latest_education_name = degree_match.group(1) if degree_match else "Education"
        
        # Get first job start date (excluding internships)
        first_job_start = None
        first_job_name = None
        
        for exp in experience_list:
            # Skip if it's an internship
            if 'intern' in exp.lower():
                continue
            
            start_date, end_date = self.extract_dates_from_text(exp, "experience")
            if start_date and (not first_job_start or start_date < first_job_start):
                # Check if role is excluded
                if not self.is_excluded_role(exp):
                    first_job_start = start_date
                    # Extract company/role
                    company_match = re.search(r'(?:at|@|-)\s*([A-Za-z\s]+)', exp, re.IGNORECASE)
                    first_job_name = company_match.group(1) if company_match else "First Job"
        
        if latest_education_end and first_job_start:
            gap_years = self.calculate_gap_years(latest_education_end, first_job_start)
            if gap_years and gap_years > 0:
                return {
                    'type': 'Education-to-Employment Gap',
                    'from_date': self.format_date_for_display(latest_education_end),
                    'to_date': self.format_date_for_display(first_job_start),
                    'duration_years': gap_years,
                    'from_name': latest_education_name,
                    'to_name': first_job_name,
                    'description': f"{latest_education_name} ({self.format_date_for_display(latest_education_end)}) → First Job ({self.format_date_for_display(first_job_start)})"
                }
        return None
    
    def analyze_employment_gaps(self, experience_list):
        """Detect gaps between consecutive employments"""
        gaps = []
        
        # Sort experiences by start date
        dated_experiences = []
        for exp in experience_list:
            if self.is_excluded_role(exp):
                continue
            
            start_date, end_date = self.extract_dates_from_text(exp, "experience")
            if start_date:
                dated_experiences.append({
                    'text': exp,
                    'start': start_date,
                    'end': end_date or datetime.now()
                })
        
        # Sort by start date
        dated_experiences.sort(key=lambda x: x['start'])
        
        # Find gaps between consecutive experiences
        for i in range(len(dated_experiences) - 1):
            current_end = dated_experiences[i]['end']
            next_start = dated_experiences[i + 1]['start']
            
            if current_end and next_start:
                gap_years = self.calculate_gap_years(current_end, next_start)
                if gap_years and gap_years > 0.1:  # More than ~1 month
                    # Extract company names
                    company1_match = re.search(r'(?:at|@|-)\s*([A-Za-z\s]+)', dated_experiences[i]['text'], re.IGNORECASE)
                    company2_match = re.search(r'(?:at|@|-)\s*([A-Za-z\s]+)', dated_experiences[i+1]['text'], re.IGNORECASE)
                    
                    company1 = company1_match.group(1).strip() if company1_match else "Previous Role"
                    company2 = company2_match.group(1).strip() if company2_match else "Next Role"
                    
                    gaps.append({
                        'type': 'Employment Gap',
                        'from_date': self.format_date_for_display(current_end),
                        'to_date': self.format_date_for_display(next_start),
                        'duration_years': gap_years,
                        'from_name': company1,
                        'to_name': company2,
                        'description': f"{company1} → {company2}"
                    })
        
        return gaps
    
    def analyze_current_employment_gap(self, experience_list):
        """Detect if candidate is currently unemployed"""
        if not experience_list:
            return None
        
        # Get latest experience
        latest_exp = None
        latest_end_date = None
        
        for exp in experience_list:
            if self.is_excluded_role(exp):
                continue
            
            start_date, end_date = self.extract_dates_from_text(exp, "experience")
            if not end_date:  # Present
                return {
                    'status': 'Currently Employed',
                    'gap': None
                }
            
            if end_date and (not latest_end_date or end_date > latest_end_date):
                latest_end_date = end_date
                latest_exp = exp
        
        if latest_end_date:
            current_date = datetime.now()
            gap_years = self.calculate_gap_years(latest_end_date, current_date)
            
            if gap_years and gap_years > 0.1:
                company_match = re.search(r'(?:at|@|-)\s*([A-Za-z\s]+)', latest_exp, re.IGNORECASE)
                company = company_match.group(1).strip() if company_match else "Last Role"
                
                return {
                    'status': 'Not Currently Employed',
                    'gap': {
                        'from_date': self.format_date_for_display(latest_end_date),
                        'to_date': self.format_date_for_display(current_date),
                        'duration_years': gap_years,
                        'company': company
                    }
                }
        
        return {'status': 'Currently Employed', 'gap': None}
    
    def get_risk_indicator(self, total_gap_years):
        """Get risk indicator based on total gap duration"""
        if total_gap_years == 0:
            return "🟢 No Gap (0 Years)"
        elif total_gap_years < 1:
            return "🟡 Minor Gap (Less than 1 Year)"
        elif total_gap_years <= 2:
            return "🟡 Minor Gap (1-2 Years)"
        elif total_gap_years <= 3:
            return "🟠 Moderate Gap (2-3 Years)"
        else:
            return "🔴 Significant Gap (More than 3 Years)"
    
    def analyze_complete_gaps(self, education_texts, experience_texts):
        """Complete gap analysis"""
        # Parse education and experience
        education_list = [edu for edu in education_texts if edu.strip()]
        experience_list = [exp for exp in experience_texts if exp.strip()]
        
        # Perform analyses
        edu_to_employment_gap = self.analyze_education_to_employment_gap(education_list, experience_list)
        employment_gaps = self.analyze_employment_gaps(experience_list)
        current_status = self.analyze_current_employment_gap(experience_list)
        
        # Calculate total gap
        total_gap_years = 0
        if edu_to_employment_gap:
            total_gap_years += edu_to_employment_gap['duration_years']
        for gap in employment_gaps:
            total_gap_years += gap['duration_years']
        if current_status and current_status.get('gap'):
            total_gap_years += current_status['gap']['duration_years']
        
        total_gap_years = round(total_gap_years, 1)
        
        return {
            'current_status': current_status['status'] if current_status else 'Unknown',
            'education_to_employment_gap': edu_to_employment_gap,
            'employment_gaps': employment_gaps,
            'current_employment_gap': current_status.get('gap') if current_status else None,
            'total_gap_years': total_gap_years,
            'risk_indicator': self.get_risk_indicator(total_gap_years)
        }