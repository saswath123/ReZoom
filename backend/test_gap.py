# test_gap.py - Run this to debug and verify gap analyzer on the 4 test cases.

from gap_analyzer import GapAnalyzer
import json

def run_tests():
    analyzer = GapAnalyzer()
    
    cases = [
        {
            "name": "Case 1: Minor Transition (Dec 23 -> Feb 24)",
            "education": ["B.Tech (2017 - 2022) XYZ University"],
            "experience": [
                "Software Engineer at X Corp (Jan 2023 - Dec 2023)",
                "Senior Developer at Y Corp (Feb 2024 - Present)"
            ],
            "expected": "Gap = 0 Year (or 1 Month gap, which is considered a minor transition and ignored)"
        },
        {
            "name": "Case 2: 1-Year Gap (Dec 20 -> Jan 22)",
            "education": ["B.Tech (2015 - 2019) XYZ University"],
            "experience": [
                "Software Engineer at X Corp (Jan 2020 - Dec 2020)",
                "Senior Developer at Y Corp (Jan 2022 - Present)"
            ],
            "expected": "~1 year gap"
        },
        {
            "name": "Case 3: Continuous Employment (Present)",
            "education": ["B.Tech (2015 - 2019) XYZ University"],
            "experience": [
                "Software Engineer at X Corp (Jan 2020 - Present)"
            ],
            "expected": "No gap"
        },
        {
            "name": "Case 4: Overlapping Jobs",
            "education": ["B.Tech (2015 - 2019) XYZ University"],
            "experience": [
                "Software Engineer at X Corp (Jan 2020 - Dec 2022)",
                "Full Stack Developer at Y Corp (Jun 2022 - Present)"
            ],
            "expected": "No gap"
        }
    ]
    
    print("=" * 60)
    print("RUNNING CAREER GAP ANALYZER VERIFICATION SUITE")
    print("=" * 60)
    
    for i, case in enumerate(cases, 1):
        print(f"\n--- Running Test {i}: {case['name']} ---")
        print(f"Education: {case['education']}")
        print(f"Experience: {case['experience']}")
        print(f"Expected: {case['expected']}")
        
        result = analyzer.analyze_complete_gaps(case['education'], case['experience'])
        total_gap = result['total_gap_years']
        gaps = result['employment_gaps']
        
        print(f"Result Total Gap: {total_gap} Years")
        print(f"Employment Gaps Detected: {json.dumps(gaps, indent=2)}")
        print(f"Risk Indicator: {result['risk_indicator']}")
        print(f"Status: {result['current_status']}")
        
        # validations
        if i == 1:
            assert total_gap == 0.0 or total_gap == 0, f"Expected 0 year gap, got {total_gap}"
        elif i == 2:
            assert 0.9 <= total_gap <= 1.1, f"Expected ~1 year gap, got {total_gap}"
        elif i == 3:
            assert total_gap == 0.0 or total_gap == 0, f"Expected 0 year gap, got {total_gap}"
        elif i == 4:
            assert total_gap == 0.0 or total_gap == 0, f"Expected 0 year gap, got {total_gap}"
            
        print("✅ PASS")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()