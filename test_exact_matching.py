#!/usr/bin/env python3
"""
Test exact filename mapping với sample data giống như trong log
"""

import json
import requests

# Sample outline tương tự như trong log
test_outline = {
    "outline": [
        {
            "title": "Chương 1",
            "subsections": [
                {
                    "title": "1.1. intro_Database",
                    "units": [
                        {
                            "title": "1.1. intro_Database",
                            "type": "video",
                            "video_url": "https://youtube.com/watch?v=123"
                            # Không có field 'file' - đây là lý do exact match fail
                        }
                    ]
                },
                {
                    "title": "1.2. Db_Concept", 
                    "units": [
                        {
                            "title": "Slide concept",
                            "file": "1.2. Db_Concept.pdf"  # Có exact filename
                        }
                    ]
                },
                {
                    "title": "1.3. Dbms",
                    "units": [
                        {
                            "title": "DBMS slides",
                            "file": "1.3. Dbms.pdf"  # Có exact filename
                        }
                    ]
                }
            ]
        },
        {
            "title": "Chương 2", 
            "subsections": [
                {
                    "title": "2.1. Algebra_Relation",
                    "units": [
                        {
                            "title": "Relation slides",
                            "file": "2.1. Algebra_Relation.pdf"  # Có exact filename
                        }
                    ]
                }
            ]
        }
    ]
}

def test_local_mapping():
    """Test exact filename mapping logic locally"""
    
    # Mock function (copy từ mapping.py)
    def map_pdf_by_exact_filename(outline: dict, filename: str) -> bool:
        print(f"[TEST] Looking for exact match: {filename}")
        found_units = []
        
        for chapter_idx, chapter in enumerate(outline.get('outline', [])):
            for subsection_idx, subsection in enumerate(chapter.get('subsections', [])):
                for unit_idx, unit in enumerate(subsection.get('units', [])):
                    existing_file = unit.get('file', '')
                    existing_pdf_file = unit.get('pdf_file', '')
                    unit_title = unit.get('title', '')
                    
                    if existing_file or existing_pdf_file:
                        found_units.append({
                            'location': f"Ch{chapter_idx}.{subsection_idx}.{unit_idx}",
                            'title': unit_title,
                            'file': existing_file,
                            'pdf_file': existing_pdf_file
                        })
                    
                    if existing_file == filename or existing_pdf_file == filename:
                        print(f"[TEST] ✓ Found exact match: {filename} -> '{unit_title}'")
                        if unit.get('video_url'):
                            unit['pdf_file'] = filename
                            if 'file' in unit:
                                del unit['file']
                            unit['type'] = 'video_pdf'
                        else:
                            unit['file'] = filename
                            if 'pdf_file' in unit:
                                del unit['pdf_file']
                            unit['type'] = 'pdf'
                        return True
        
        if found_units:
            print(f"[TEST] Units with file fields:")
            for unit_info in found_units:
                print(f"  - {unit_info['location']}: '{unit_info['title']}' file='{unit_info['file']}' pdf_file='{unit_info['pdf_file']}'")
        else:
            print(f"[TEST] No units with file/pdf_file fields found")
        
        print(f"[TEST] ✗ No exact match for: {filename}")
        return False
    
    # Test files from log
    test_files = [
        "1.1. intro_Database.pdf",  # Should NOT match (unit has no 'file' field)
        "1.2. Db_Concept.pdf",      # Should match
        "1.3. Dbms.pdf",            # Should match
        "2.1. Algebra_Relation.pdf" # Should match
    ]
    
    print("=== Testing Exact Filename Matching ===")
    outline_copy = json.loads(json.dumps(test_outline))
    
    for filename in test_files:
        print(f"\n--- Testing: {filename} ---")
        result = map_pdf_by_exact_filename(outline_copy, filename)
        print(f"Result: {'SUCCESS' if result else 'FAILED'}")
    
    print(f"\n=== Final Outline Structure ===")
    for ch_idx, chapter in enumerate(outline_copy.get('outline', [])):
        print(f"Chapter {ch_idx}: {chapter.get('title', '')}")
        for sub_idx, subsection in enumerate(chapter.get('subsections', [])):
            print(f"  Subsection {sub_idx}: {subsection.get('title', '')}")
            for unit_idx, unit in enumerate(subsection.get('units', [])):
                print(f"    Unit {unit_idx}: {unit.get('title', '')} [type: {unit.get('type', 'none')}]")
                if unit.get('file'):
                    print(f"      file: {unit['file']}")
                if unit.get('pdf_file'):
                    print(f"      pdf_file: {unit['pdf_file']}")
                if unit.get('video_url'):
                    print(f"      video: {unit['video_url']}")

if __name__ == "__main__":
    test_local_mapping()
    
    print("\n" + "="*60)
    print("GIẢI THÍCH VẤN ĐỀ:")
    print("- File '1.1. intro_Database.pdf' KHÔNG match vì unit tương ứng không có field 'file'")
    print("- Unit chỉ có 'video_url', chưa có 'file' để so sánh")
    print("- Để exact matching hoạt động, cần:")
    print("  1. Import Excel với cột 'Slide' chứa đúng tên file PDF")
    print("  2. Hoặc thêm field 'file' vào unit thủ công")
    print("="*60)
