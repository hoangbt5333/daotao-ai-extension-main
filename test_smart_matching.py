#!/usr/bin/env python3
"""
Test smart title matching logic
"""

def normalize_for_comparison(text: str) -> str:
    """Normalize text for similarity comparison"""
    import re
    # Remove special chars, convert to lowercase, remove extra spaces
    normalized = re.sub(r'[^\w\s]', ' ', text.lower())
    normalized = ' '.join(normalized.split())  # Remove extra spaces
    return normalized

def calculate_similarity_score(text1: str, text2: str) -> float:
    """Calculate similarity score between two normalized texts"""
    try:
        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        # Jaccard similarity
        jaccard = len(intersection) / len(union) if union else 0
        
        # Bonus for exact substring matches
        substring_bonus = 0
        if text1 in text2 or text2 in text1:
            substring_bonus = 0.3
        
        return min(1.0, jaccard + substring_bonus)
    except:
        return 0.0

def test_smart_matching():
    """Test smart title matching logic"""
    
    # Test cases from real log
    test_cases = [
        {
            "filename": "1.1. intro_Database.pdf",
            "unit_title": "1.1. intro_Database",
            "expected_score": "high"
        },
        {
            "filename": "1.7. Thực hành- HQTCSDL.pdf", 
            "unit_title": "1.7. Thực hành: HQTCSDL",
            "expected_score": "high"
        },
        {
            "filename": "1.5. ERModel.pdf",
            "unit_title": "1.5. ERModel",
            "expected_score": "high"
        },
        {
            "filename": "2.2. Algebra_Collection.pdf",
            "unit_title": "Different Title",
            "expected_score": "low"
        }
    ]
    
    print("=== Testing Smart Title Matching ===")
    
    for i, test_case in enumerate(test_cases, 1):
        filename = test_case["filename"]
        unit_title = test_case["unit_title"]
        expected = test_case["expected_score"]
        
        # Remove extension and normalize
        name_base = filename.replace('.pdf', '').replace('.PDF', '')
        norm_filename = normalize_for_comparison(name_base)
        norm_title = normalize_for_comparison(unit_title)
        
        score = calculate_similarity_score(norm_filename, norm_title)
        
        print(f"\nTest {i}:")
        print(f"  Filename: '{filename}'")
        print(f"  Unit title: '{unit_title}'")
        print(f"  Normalized filename: '{norm_filename}'")
        print(f"  Normalized title: '{norm_title}'")
        print(f"  Similarity score: {score:.3f}")
        print(f"  Would match (>0.7): {'YES' if score > 0.7 else 'NO'}")
        print(f"  Expected: {expected}")
        
        # Evaluate result
        if expected == "high" and score > 0.7:
            print(f"  ✓ PASS")
        elif expected == "low" and score <= 0.7:
            print(f"  ✓ PASS") 
        else:
            print(f"  ✗ FAIL")

if __name__ == "__main__":
    test_smart_matching()
    
    print("\n" + "="*60)
    print("KẾT LUẬN:")
    print("- Smart title matching sẽ tìm units có title tương tự filename")
    print("- Threshold 0.7 để đảm bảo chất lượng matching")
    print("- Ưu tiên thêm PDF vào video unit (tạo video_pdf)")
    print("- Fallback tạo PDF unit mới nếu không match")
    print("="*60)
