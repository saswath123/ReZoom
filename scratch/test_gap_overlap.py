import sys
import os
from datetime import datetime

sys.path.append("/Users/bharatarv/Desktop/Talent Lens/TalentLens")
sys.path.append("/Users/bharatarv/Desktop/Talent Lens/TalentLens/backend")

from backend.gap_analyzer import GapAnalyzer
import json

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

class ImprovedGapAnalyzer(GapAnalyzer):
    def analyze_complete_gaps(self, education_raw, experience_raw):
        print("=" * 50)
        print("Improved Gap Analyzer Debug:")
        print(f"Education Raw: {education_raw}")
        print(f"Experience Raw: {experience_raw}")
        
        education_entries = self.extract_education_entries(education_raw)
        experience_entries = self.extract_experience_entries(experience_raw)
        
        # 1. First get initial raw analysis
        edu_to_employment_gap = self.analyze_education_to_employment_gap(education_entries, experience_entries)
        
        # We temporarily calculate employment gaps
        raw_employment_gaps = self.analyze_employment_gaps(experience_entries)
        career_breaks = self.analyze_career_breaks(experience_entries)
        current_status = self.analyze_current_employment_gap(experience_entries)
        
        # 2. Extract interval sets
        explaining_intervals = []
        for cb in career_breaks:
            if isinstance(cb.get('duration_years'), (int, float)):
                explaining_intervals.append((cb['from_year'], cb['to_year']))
                
        # generic employment gap intervals
        generic_emp_intervals = []
        for eg in raw_employment_gaps:
            generic_emp_intervals.append((eg['from_year'], eg['to_year']))
            
        # Subtract career breaks from employment gaps to remove redundancy
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
            
        # 3. Calculate total gap using non-overlapping union of all intervals
        all_intervals = []
        if edu_to_employment_gap and edu_to_employment_gap.get('duration_years') != 'Unknown':
            all_intervals.append((edu_to_employment_gap['from_year'], edu_to_employment_gap['to_year']))
            
        for start, end in adjusted_emp_intervals:
            all_intervals.append((start, end))
            
        for start, end in explaining_intervals:
            all_intervals.append((start, end))
            
        if current_status.get('gap'):
            all_intervals.append((current_status['gap']['from_year'], current_status['gap']['to_year']))
            
        total_gap_years = merge_and_sum_intervals(all_intervals)
        
        # Handle unknown cases
        gap_years_known = True
        if edu_to_employment_gap and edu_to_employment_gap.get('duration_years') == 'Unknown':
            gap_years_known = False
            
        for cb in career_breaks:
            if cb.get('duration_years') == 'Unknown':
                gap_years_known = False
                
        if not gap_years_known or total_gap_years == 0:
            has_any_years = any(e.get('has_years') for e in education_entries) or any(e.get('has_years') for e in experience_entries)
            if not has_any_years:
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

def run_test(name, edu, exp):
    analyzer = ImprovedGapAnalyzer()
    result = analyzer.analyze_complete_gaps(edu, exp)
    print(f"\n=== TEST: {name} ===")
    print(json.dumps(result, indent=2))

# Test case 1: Career break during education-to-first-job period
run_test(
    "Career Break during Ed-to-Emp",
    ["B.Tech (2017 - 2022)"],
    [
        "Career Break (2023 - 2024)",
        "Software Engineer (2025 - Present)"
    ]
)

# Test case 2: Sabbatical/Career break between two jobs
run_test(
    "Sabbatical between two jobs",
    ["B.Tech (2015 - 2019)"],
    [
        "Job 1 (2019 - 2020)",
        "Career Break / Sabbatical (2020 - 2022)",
        "Job 2 (2022 - Present)"
    ]
)
