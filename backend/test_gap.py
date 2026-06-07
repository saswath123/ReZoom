# test_gap.py - Run this to debug gap analyzer

from gap_analyzer import GapAnalyzer
import json

# Simulate the data from your resume
education_raw = [
    "B.Tech in Computer Science (2017 - 2022) XYZ University"
]

experience_raw = [
    "Career Break (2023 - 2024) Focused on upskilling in Python, AWS, and Generative AI",
    "GenAI Developer (2025 - Present) Built AI-powered resume analyzer applications"
]

print("=" * 60)
print("TESTING GAP ANALYZER WITH YOUR RESUME DATA")
print("=" * 60)

# Create analyzer instance
analyzer = GapAnalyzer()

# Test individual functions
print("\n1. Testing extract_years_from_text:")
print(f"   '2017-2022' -> {analyzer.extract_years_from_text('2017-2022')}")
print(f"   '2023-2024' -> {analyzer.extract_years_from_text('2023-2024')}")
print(f"   '2025-Present' -> {analyzer.extract_years_from_text('2025-Present')}")

print("\n2. Testing parse_date_range:")
print(f"   '2017-2022' -> {analyzer.parse_date_range('2017-2022')}")
print(f"   '2023-2024' -> {analyzer.parse_date_range('2023-2024')}")
print(f"   '2025-Present' -> {analyzer.parse_date_range('2025-Present')}")

print("\n3. Testing is_career_break:")
print(f"   'Career Break (2023-2024)' -> {analyzer.is_career_break('Career Break (2023-2024)')}")
print(f"   'GenAI Developer (2025-Present)' -> {analyzer.is_career_break('GenAI Developer (2025-Present)')}")

print("\n4. Testing extract_education_entries:")
edu_entries = analyzer.extract_education_entries(education_raw)
print(f"   Result: {edu_entries}")

print("\n5. Testing extract_experience_entries:")
exp_entries = analyzer.extract_experience_entries(experience_raw)
print(f"   Result: {exp_entries}")

print("\n6. Testing analyze_education_to_employment_gap:")
gap = analyzer.analyze_education_to_employment_gap(edu_entries, exp_entries)
print(f"   Result: {gap}")

print("\n7. Testing analyze_career_breaks:")
breaks = analyzer.analyze_career_breaks(exp_entries)
print(f"   Result: {breaks}")

print("\n8. Testing analyze_complete_gaps (FULL):")
result = analyzer.analyze_complete_gaps(education_raw, experience_raw)
print(json.dumps(result, indent=2))