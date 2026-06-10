import re
from datetime import datetime

def subtract_intervals(generic_intervals, explaining_intervals):
    result = list(generic_intervals)
    for b_start, b_end in explaining_intervals:
        if b_start is None or b_end is None or b_start >= b_end:
            continue
        next_result = []
        for a_start, a_end in result:
            if a_start is None or a_end is None or a_start >= a_end:
                continue
            # No overlap
            if b_end <= a_start or b_start >= a_end:
                next_result.append((a_start, a_end))
            # Complete cover
            elif b_start <= a_start and b_end >= a_end:
                continue
            # Overlap start
            elif b_start <= a_start and b_end < a_end:
                next_result.append((b_end, a_end))
            # Overlap end
            elif b_start > a_start and b_end >= a_end:
                next_result.append((a_start, b_start))
            # Split
            else:
                next_result.append((a_start, b_start))
                next_result.append((b_end, a_end))
        result = next_result
    return result

def merge_and_sum_intervals(intervals):
    valid_intervals = []
    for s, e in intervals:
        if s is not None and e is not None:
            if s > e:
                s, e = e, s
            valid_intervals.append((s, e))
            
    if not valid_intervals:
        return 0
        
    valid_intervals.sort(key=lambda x: x[0])
    
    merged = []
    current_start, current_end = valid_intervals[0]
    
    for start, end in valid_intervals[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
            
    merged.append((current_start, current_end))
    
    return sum(e - s for s, e in merged)

class GapAnalyzer:
    """Career Gap Detection & Employment Continuity Analysis"""
    
    def __init__(self):
        self.career_break_keywords = [
            'career break', 'career gap', 'sabbatical', 'personal reasons',
            'family commitment', 'health break', 'parental leave', 'career hiatus',
            'time off', 'employment gap', 'break from work', 'upskilling break',
            'career transition', 'professional development', 'skill development'
        ]
    
    def extract_years_from_text(self, text):
        """Extract all years from text - improved pattern matching"""
        if not text:
            return []
        text = str(text)
        # Match 4-digit years between 1950 and 2030
        years = re.findall(r'\b(19[5-9][0-9]|20[0-2][0-9]|2030)\b', text)
        return [int(y) for y in years]
    
    def has_valid_years(self, text):
        """Check if text contains valid years"""
        if not text:
            return False
        return len(self.extract_years_from_text(text)) > 0
    
    def parse_date_range(self, text):
        """Extract start and end years from a date range string - SUPER ROBUST"""
        if not text:
            return None, None
        
        text = str(text)
        
        # 1. First extract all 4-digit years in range 1950-2030
        years = self.extract_years_from_text(text)
        
        # 2. Check if "present" or "current" is in the text
        has_present = bool(re.search(r'\b(?:[Pp]resent|[Cc]urrent)\b', text))
        
        if len(years) >= 2:
            # Sort years to ensure start is smaller than end
            sorted_years = sorted(years)
            return sorted_years[0], sorted_years[-1]
        elif len(years) == 1:
            year = years[0]
            if has_present:
                return year, datetime.now().year
            else:
                return year, year
        
        return None, None
    
    def is_career_break(self, text):
        """Check if text describes a career break"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.career_break_keywords)
    
    def extract_education_entries(self, education_raw):
        """Extract education entries with years - IMPROVED"""
        education_entries = []
        
        if not education_raw:
            return education_entries
        
        for edu in education_raw:
            if not edu:
                continue
            
            has_years = self.has_valid_years(edu)
            start, end = self.parse_date_range(edu)
            
            # If no date range found, try to extract any years present
            if not start and has_years:
                years = self.extract_years_from_text(edu)
                if years:
                    start = min(years)
                    end = max(years)
                    has_years = True
            
            education_entries.append({
                'text': edu,
                'start_year': start,
                'end_year': end if end else start,
                'has_years': has_years
            })
        
        return education_entries
    
    def extract_experience_entries(self, experience_raw):
        """Extract experience entries with years and detect career breaks - IMPROVED"""
        experience_entries = []
        
        if not experience_raw:
            return experience_entries
        
        for exp in experience_raw:
            if not exp:
                continue
            
            has_years = self.has_valid_years(exp)
            start, end = self.parse_date_range(exp)
            is_break = self.is_career_break(exp)
            
            # If no date range found but has years, use the years
            if not start and has_years:
                years = self.extract_years_from_text(exp)
                if years:
                    start = min(years)
                    end = max(years)
                    has_years = True
            
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
        edu_with_years = [e for e in education_entries if e.get('has_years') and e.get('end_year')]
        
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
        regular_jobs = [exp for exp in experience_entries if not exp.get('is_career_break') and exp.get('has_years') and exp.get('start_year')]
        
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
                        'description': f"{current_end} to {next_start} ({gap_years} year{'s' if gap_years != 1 else ''})"
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
                    elif duration == 0:
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
        elif isinstance(total_gap_years, str):
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
        raw_employment_gaps = self.analyze_employment_gaps(experience_entries)
        career_breaks = self.analyze_career_breaks(experience_entries)
        current_status = self.analyze_current_employment_gap(experience_entries)
        
        # 1. Extract explaining intervals (career breaks)
        explaining_intervals = []
        for cb in career_breaks:
            if isinstance(cb.get('duration_years'), (int, float)):
                explaining_intervals.append((cb['from_year'], cb['to_year']))
                
        # 2. Extract generic employment gap intervals
        generic_emp_intervals = []
        for eg in raw_employment_gaps:
            generic_emp_intervals.append((eg['from_year'], eg['to_year']))
            
        # 3. Subtract career breaks from generic employment gaps to prevent double-counting/redundancy
        adjusted_emp_intervals = subtract_intervals(generic_emp_intervals, explaining_intervals)
        
        # Rebuild employment_gaps list from adjusted intervals
        employment_gaps = []
        for start, end in adjusted_emp_intervals:
            gap_years = end - start
            employment_gaps.append({
                'type': 'Employment Gap',
                'from_year': start,
                'to_year': end,
                'duration_years': gap_years,
                'description': f"{start} to {end} ({gap_years} year{'s' if gap_years != 1 else ''})"
            })
            
        # 4. Calculate total gap using non-overlapping union of all intervals
        all_intervals = []
        if isinstance(edu_to_employment_gap, dict) and edu_to_employment_gap.get('duration_years') != 'Unknown':
            from_yr = edu_to_employment_gap.get('from_year')
            to_yr = edu_to_employment_gap.get('to_year')
            if from_yr is not None and to_yr is not None:
                all_intervals.append((from_yr, to_yr))
            
        for start, end in adjusted_emp_intervals:
            all_intervals.append((start, end))
            
        for start, end in explaining_intervals:
            all_intervals.append((start, end))
            
        current_gap = current_status.get('gap')
        if isinstance(current_gap, dict):
            from_yr = current_gap.get('from_year')
            to_yr = current_gap.get('to_year')
            if from_yr is not None and to_yr is not None:
                all_intervals.append((from_yr, to_yr))
            
        total_gap_years = merge_and_sum_intervals(all_intervals)
        
        # Handle unknown cases
        gap_years_known = True
        if edu_to_employment_gap and edu_to_employment_gap.get('duration_years') == 'Unknown':
            gap_years_known = False
            
        for cb in career_breaks:
            if cb.get('duration_years') == 'Unknown':
                gap_years_known = False
                
        if not gap_years_known or total_gap_years == 0:
            # Check if there's any year data at all
            has_any_years = any(e.get('has_years') for e in education_entries) or any(e.get('has_years') for e in experience_entries)
            if not has_any_years:
                total_gap_years = 'Unknown'
            elif total_gap_years == 0:
                total_gap_years = 0
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
    import json
    
    analyzer = GapAnalyzer()
    
    # Test with sample data
    education_raw = ["B.Tech in Computer Science (2017 - 2022) XYZ University"]
    experience_raw = ["Software Engineer at ABC Corp (2022 - Present)"]
    
    result = analyzer.analyze_complete_gaps(education_raw, experience_raw)
    print("\n" + "=" * 50)
    print("TEST RESULT:")
    print("=" * 50)
    print(json.dumps(result, indent=2))