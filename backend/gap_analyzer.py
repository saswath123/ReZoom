import re
from datetime import datetime, timedelta

def subtract_date_intervals(generic_intervals, explaining_intervals):
    """
    Subtract explaining_intervals (e.g., career breaks) from generic_intervals.
    All intervals are tuples of (start_date, end_date) datetimes.
    """
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

def merge_and_sum_date_intervals(intervals):
    """
    Merge overlapping date intervals and sum their total durations in years.
    Returns (total_years, merged_list).
    """
    valid_intervals = []
    for s, e in intervals:
        if s is not None and e is not None:
            if s > e:
                s, e = e, s
            valid_intervals.append((s, e))
            
    if not valid_intervals:
        return 0.0, []
        
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
    
    total_days = sum((e - s).days for s, e in merged)
    total_years = total_days / 365.25
    return total_years, merged

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
    
    def parse_date_range_to_datetime(self, text):
        """Extract start and end datetime from a date range string - Month & Year Aware"""
        if not text:
            return None, None
        
        text = str(text).strip()
        
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        
        month_names = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
        
        pattern_month_year = re.compile(
            rf"\b({month_names})[-/\s,']+(\d{{4}}|\b\d{{2}}\b)\b", re.IGNORECASE
        )
        pattern_numeric = re.compile(
            r"\b(0?[1-9]|1[0-2])[-/](\d{4}|\b\d{2}\b)\b"
        )
        pattern_year_only = re.compile(
            r"\b(19\d{2}|20[0-2]\d|2030)\b"
        )
        pattern_present = re.compile(
            r"\b(present|current|now|ongoing)\b", re.IGNORECASE
        )
        
        # Scan for date tokens in sequence
        unified_regex = re.compile(
            rf"({month_names}[-/\s,']+(?:\d{{4}}|\b\d{{2}}\b))|"
            r"(\b(?:0?[1-9]|1[0-2])[-/](?:\d{4}|\b\d{2}\b)\b)|"
            r"(\b(?:19\d{2}|20[0-2]\d|2030)\b)|"
            r"(\b(?:present|current|now|ongoing)\b)",
            re.IGNORECASE
        )
        
        matches = unified_regex.findall(text)
        raw_tokens = []
        for match in matches:
            for group in match:
                if group:
                    raw_tokens.append(group.strip())
                    break
        
        def parse_single_token(token, is_end=False):
            token_lower = token.lower()
            if pattern_present.match(token_lower):
                return datetime.now()
                
            # Month name + year
            m = pattern_month_year.match(token_lower)
            if m:
                m_str, y_str = m.group(1), m.group(2)
                month = month_map[m_str]
                year = int(y_str)
                if year < 100:
                    year += 2000 if year < 50 else 1900
                if is_end:
                    if month == 12:
                        return datetime(year, 12, 31)
                    else:
                        return datetime(year, month + 1, 1) - timedelta(days=1)
                else:
                    return datetime(year, month, 1)
                    
            # Numeric month/year
            m = pattern_numeric.match(token_lower)
            if m:
                m_str, y_str = m.group(1), m.group(2)
                month = int(m_str)
                year = int(y_str)
                if year < 100:
                    year += 2000 if year < 50 else 1900
                if is_end:
                    if month == 12:
                        return datetime(year, 12, 31)
                    else:
                        return datetime(year, month + 1, 1) - timedelta(days=1)
                else:
                    return datetime(year, month, 1)
                    
            # Year only
            m = pattern_year_only.match(token_lower)
            if m:
                year = int(m.group(1))
                if is_end:
                    return datetime(year, 12, 31)
                else:
                    return datetime(year, 1, 1)
                    
            return None

        dates = []
        for i, tok in enumerate(raw_tokens):
            is_end = (i > 0)
            d = parse_single_token(tok, is_end=is_end)
            if d:
                dates.append(d)
                
        if len(dates) >= 2:
            return dates[0], dates[1]
        elif len(dates) == 1:
            has_present = bool(pattern_present.search(text))
            if has_present:
                return dates[0], datetime.now()
            else:
                return dates[0], dates[0]
                
        return None, None

    def parse_date_range(self, text):
        """Backward-compatible: extract start and end years"""
        start_date, end_date = self.parse_date_range_to_datetime(text)
        if start_date and end_date:
            return start_date.year, end_date.year
        return None, None
    
    def is_career_break(self, text):
        """Check if text describes a career break"""
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.career_break_keywords)
    
    def extract_education_entries(self, education_raw):
        """Extract education entries with dates and years"""
        education_entries = []
        if not education_raw:
            return education_entries
            
        for edu in education_raw:
            if not edu:
                continue
            
            start_date, end_date = self.parse_date_range_to_datetime(edu)
            has_dates = start_date is not None
            
            # Fallback to year extraction if datetime parsing failed
            if not has_dates:
                years = self.extract_years_from_text(edu)
                if years:
                    s_yr = min(years)
                    e_yr = max(years)
                    start_date = datetime(s_yr, 1, 1)
                    end_date = datetime(e_yr, 12, 31)
                    has_dates = True
                    
            education_entries.append({
                'text': edu,
                'start_date': start_date,
                'end_date': end_date if end_date else start_date,
                'start_year': start_date.year if start_date else None,
                'end_year': end_date.year if end_date else (start_date.year if start_date else None),
                'has_years': has_dates
            })
        return education_entries
    
    def extract_experience_entries(self, experience_raw):
        """Extract experience entries with dates and detect career breaks"""
        experience_entries = []
        if not experience_raw:
            return experience_entries
            
        for exp in experience_raw:
            if not exp:
                continue
                
            start_date, end_date = self.parse_date_range_to_datetime(exp)
            has_dates = start_date is not None
            is_break = self.is_career_break(exp)
            is_present = 'present' in str(exp).lower() or 'current' in str(exp).lower() or 'now' in str(exp).lower()
            
            # Fallback to year extraction if datetime parsing failed
            if not has_dates:
                years = self.extract_years_from_text(exp)
                if years:
                    s_yr = min(years)
                    e_yr = max(years)
                    start_date = datetime(s_yr, 1, 1)
                    end_date = datetime(e_yr, 12, 31)
                    has_dates = True
                    
            experience_entries.append({
                'text': exp,
                'start_date': start_date,
                'end_date': end_date if end_date else start_date,
                'start_year': start_date.year if start_date else None,
                'end_year': end_date.year if end_date else (start_date.year if start_date else None),
                'has_years': has_dates,
                'is_career_break': is_break,
                'is_present': is_present
            })
            
        # Sort by start date (entries without dates go to the end)
        experience_entries.sort(key=lambda x: x['start_date'] if x['start_date'] else datetime(9999, 12, 31))
        return experience_entries
    
    def analyze_education_to_employment_gap(self, education_entries, experience_entries):
        """Detect gap between education completion and first job using month-level date calculations"""
        if not education_entries or not experience_entries:
            return None
            
        # Get latest education with valid dates
        edu_with_dates = [e for e in education_entries if e.get('start_date') and e.get('end_date')]
        if not edu_with_dates:
            return {
                'type': 'Education-to-Employment Gap',
                'from_year': 'Not specified',
                'to_year': 'Not specified',
                'duration_years': 'Unknown',
                'description': '❓ Cannot determine - missing graduation date'
            }
            
        latest_edu = max(edu_with_dates, key=lambda x: x['end_date'])
        edu_end_date = latest_edu['end_date']
        
        # Get first non-career-break job with valid dates
        first_job = None
        for exp in experience_entries:
            if not exp.get('is_career_break') and exp.get('start_date'):
                first_job = exp
                break
                
        if not first_job:
            return None
            
        job_start_date = first_job['start_date']
        
        if job_start_date and edu_end_date and job_start_date > edu_end_date:
            gap_days = (job_start_date - edu_end_date).days
            if gap_days <= 32:
                return None
                
            gap_months = (job_start_date.year - edu_end_date.year) * 12 + job_start_date.month - edu_end_date.month - 1
            if gap_months <= 1:
                return None
                
            gap_years = round(gap_months / 12.0, 1)
            
            return {
                'type': 'Education-to-Employment Gap',
                'from_year': edu_end_date.year,
                'to_year': job_start_date.year,
                'from_date': edu_end_date.strftime('%Y-%m-%d'),
                'to_date': job_start_date.strftime('%Y-%m-%d'),
                'duration_years': gap_years,
                'description': f"Graduation ({edu_end_date.strftime('%b %Y')}) → First Job ({job_start_date.strftime('%b %Y')}) ({gap_months} month{'s' if gap_months != 1 else ''})"
            }
            
        return None
    
    def analyze_employment_gaps(self, experience_entries):
        """Detect gaps between consecutive employments by merging overlapping dates first"""
        gaps = []
        
        regular_jobs = [
            exp for exp in experience_entries 
            if not exp.get('is_career_break') and exp.get('start_date') and exp.get('end_date')
        ]
        
        if not regular_jobs:
            return gaps
            
        # 1. Merge overlapping/consecutive (gap <= 32 days) employment periods
        merged_employments = []
        for job in regular_jobs:
            start, end = job['start_date'], job['end_date']
            if not merged_employments:
                merged_employments.append((start, end))
            else:
                prev_start, prev_end = merged_employments[-1]
                if start <= prev_end + timedelta(days=32):
                    merged_employments[-1] = (prev_start, max(prev_end, end))
                else:
                    merged_employments.append((start, end))
                    
        # 2. Find gaps between merged employment periods
        for i in range(len(merged_employments) - 1):
            current_end = merged_employments[i][1]
            next_start = merged_employments[i + 1][0]
            
            if next_start > current_end:
                gap_days = (next_start - current_end).days
                if gap_days <= 32:
                    continue
                    
                gap_months = (next_start.year - current_end.year) * 12 + next_start.month - current_end.month - 1
                if gap_months <= 1:
                    continue
                    
                gap_years = round(gap_months / 12.0, 1)
                gaps.append({
                    'type': 'Employment Gap',
                    'from_year': current_end.year,
                    'to_year': next_start.year,
                    'from_date': current_end.strftime('%Y-%m-%d'),
                    'to_date': next_start.strftime('%Y-%m-%d'),
                    'duration_years': gap_years,
                    'description': f"{current_end.strftime('%b %Y')} to {next_start.strftime('%b %Y')} ({gap_months} month{'s' if gap_months != 1 else ''})"
                })
                
        return gaps
    
    def analyze_career_breaks(self, experience_entries):
        """Extract career breaks as gaps with month-level duration"""
        career_breaks = []
        
        for exp in experience_entries:
            if exp.get('is_career_break'):
                has_dates = exp.get('has_years', False)
                start_date = exp.get('start_date')
                end_date = exp.get('end_date')
                
                if has_dates and start_date and end_date:
                    gap_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
                    if gap_months > 0:
                        duration_years = round(gap_months / 12.0, 1)
                        career_breaks.append({
                            'type': 'Career Break',
                            'from_year': start_date.year,
                            'to_year': end_date.year,
                            'from_date': start_date.strftime('%Y-%m-%d'),
                            'to_date': end_date.strftime('%Y-%m-%d'),
                            'duration_years': duration_years,
                            'description': f"Career Break ({start_date.strftime('%b %Y')} - {end_date.strftime('%b %Y')})"
                        })
                    else:
                        career_breaks.append({
                            'type': 'Career Break',
                            'from_year': start_date.year,
                            'to_year': end_date.year,
                            'from_date': start_date.strftime('%Y-%m-%d'),
                            'to_date': end_date.strftime('%Y-%m-%d'),
                            'duration_years': 0.1,
                            'description': f"Career Break (within {start_date.strftime('%b %Y')})"
                        })
                else:
                    career_breaks.append({
                        'type': 'Career Break',
                        'from_year': 'Not specified',
                        'to_year': 'Not specified',
                        'duration_years': 'Unknown',
                        'description': "❓ Career Break - dates not specified"
                    })
                    
        return career_breaks
    
    def analyze_current_employment_gap(self, experience_entries):
        """Detect if candidate is currently unemployed using month-level date checks"""
        if not experience_entries:
            return {'status': 'No experience listed', 'gap': None}
            
        regular_jobs = [
            exp for exp in experience_entries 
            if not exp.get('is_career_break') and exp.get('start_date') and exp.get('end_date')
        ]
        
        if not regular_jobs:
            return {'status': '❓ Cannot determine - missing dates', 'gap': None}
            
        latest_job = max(regular_jobs, key=lambda x: x['end_year'] if x['end_year'] else 0)
        current_date = datetime.now()
        
        if latest_job.get('is_present') or latest_job['end_date'] >= current_date - timedelta(days=32):
            return {'status': 'Currently Employed ✅', 'gap': None}
            
        gap_days = (current_date - latest_job['end_date']).days
        if gap_days <= 32:
            return {'status': 'Currently Employed ✅', 'gap': None}
            
        gap_months = (current_date.year - latest_job['end_date'].year) * 12 + current_date.month - latest_job['end_date'].month - 1
        if gap_months <= 1:
            return {'status': 'Currently Employed ✅', 'gap': None}
            
        gap_years = round(gap_months / 12.0, 1)
        
        return {
            'status': 'Not Currently Employed ⚠️',
            'gap': {
                'from_year': latest_job['end_date'].year,
                'to_year': current_date.year,
                'from_date': latest_job['end_date'].strftime('%Y-%m-%d'),
                'to_date': current_date.strftime('%Y-%m-%d'),
                'duration_years': gap_years,
                'description': f"Last Job ({latest_job['end_date'].strftime('%b %Y')}) → Present ({current_date.strftime('%b %Y')}) ({gap_months} month{'s' if gap_months != 1 else ''})"
            }
        }
    
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
            for exp in experience_entries:
                if exp.get('is_career_break') and exp.get('start_date') and exp.get('end_date'):
                    if exp['start_date'].year == cb.get('from_year') and exp['end_date'].year == cb.get('to_year'):
                        explaining_intervals.append((exp['start_date'], exp['end_date']))
                        break
                        
        # 2. Extract generic employment gap intervals
        generic_emp_intervals = []
        for eg in raw_employment_gaps:
            from_d = datetime.strptime(eg['from_date'], '%Y-%m-%d')
            to_d = datetime.strptime(eg['to_date'], '%Y-%m-%d')
            generic_emp_intervals.append((from_d, to_d))
            
        # 3. Subtract career breaks from generic employment gaps to prevent double-counting/redundancy
        adjusted_emp_intervals = subtract_date_intervals(generic_emp_intervals, explaining_intervals)
        
        # Rebuild employment_gaps list from adjusted intervals
        employment_gaps = []
        for start, end in adjusted_emp_intervals:
            gap_months = (end.year - start.year) * 12 + end.month - start.month - 1
            if gap_months <= 1:
                continue
            gap_years = round(gap_months / 12.0, 1)
            employment_gaps.append({
                'type': 'Employment Gap',
                'from_year': start.year,
                'to_year': end.year,
                'from_date': start.strftime('%Y-%m-%d'),
                'to_date': end.strftime('%Y-%m-%d'),
                'duration_years': gap_years,
                'description': f"{start.strftime('%b %Y')} to {end.strftime('%b %Y')} ({gap_months} month{'s' if gap_months != 1 else ''})"
            })
            
        # 4. Calculate total gap using non-overlapping union of all intervals
        all_intervals = []
        if isinstance(edu_to_employment_gap, dict) and edu_to_employment_gap.get('duration_years') != 'Unknown':
            from_dt = datetime.strptime(edu_to_employment_gap['from_date'], '%Y-%m-%d')
            to_dt = datetime.strptime(edu_to_employment_gap['to_date'], '%Y-%m-%d')
            all_intervals.append((from_dt, to_dt))
            
        for start, end in adjusted_emp_intervals:
            all_intervals.append((start, end))
            
        for start, end in explaining_intervals:
            all_intervals.append((start, end))
            
        current_gap = current_status.get('gap')
        if isinstance(current_gap, dict):
            from_dt = datetime.strptime(current_gap['from_date'], '%Y-%m-%d')
            to_dt = datetime.strptime(current_gap['to_date'], '%Y-%m-%d')
            all_intervals.append((from_dt, to_dt))
            
        total_gap_years, _ = merge_and_sum_date_intervals(all_intervals)
        
        # Handle unknown cases
        gap_years_known = True
        if edu_to_employment_gap and edu_to_employment_gap.get('duration_years') == 'Unknown':
            gap_years_known = False
            
        for cb in career_breaks:
            if cb.get('duration_years') == 'Unknown':
                gap_years_known = False
                
        if not gap_years_known or total_gap_years == 0:
            has_any_dates = any(e.get('has_years') for e in education_entries) or any(e.get('has_years') for e in experience_entries)
            if not has_any_dates:
                total_gap_years = 'Unknown'
            elif total_gap_years == 0:
                total_gap_years = 0.0
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