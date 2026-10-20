"""
Mapping endpoints
"""
import json
import re
from typing import List
from fastapi import APIRouter, Form, File, UploadFile
from app.models.schemas.responses import MappingResponse

router = APIRouter()


@router.post("/pdfs")
async def map_pdfs_to_outline(
    files: List[UploadFile] = File(...),
    outline: str = Form(...)
):
    """Map PDF files to outline based on filename analysis"""
    try:
        # Parse outline
        outline_data = json.loads(outline)
        
        # Analyze filenames and map to outline
        mapped_outline = await map_pdf_files_to_outline(files, outline_data)
        
        return MappingResponse(
            success=True,
            mapped_outline=mapped_outline,
            mapped_count=len(files),
            message="PDF mapping completed successfully"
        )
    except Exception as e:
        return MappingResponse(
            success=False,
            mapped_outline={},
            mapped_count=0,
            message=f"PDF mapping failed: {str(e)}"
        )


async def map_pdf_files_to_outline(files: List[UploadFile], outline_data: dict) -> dict:
    """Map PDF files to outline using filename analysis"""
    # Create a copy of outline to modify
    mapped_outline = json.loads(json.dumps(outline_data))
    
    print(f"Starting PDF mapping for {len(files)} files")
    print(f"Original outline structure: {len(mapped_outline.get('outline', []))} chapters")
    
    # First pass: Try exact filename matching, then pattern analysis
    mapped_files = set()
    for file in files:
        filename = file.filename
        if not filename.lower().endswith('.pdf'):
            continue
            
        print(f"\nProcessing file: {filename}")
        
        # Try exact filename matching first
        if map_pdf_by_exact_filename(mapped_outline, filename):
            print(f"✓ Found exact filename match for: {filename}")
            mapped_files.add(filename)
            continue
        
        # Try smart title-based matching (for units without file field but similar title)
        if map_pdf_by_smart_title_matching(mapped_outline, filename):
            print(f"✓ Found smart title match for: {filename}")
            mapped_files.add(filename)
            continue
        
        # If no exact match, use pattern analysis
        mapping = analyze_filename_pattern(filename, mapped_outline)
        print(f"Filename analysis result: {mapping}")
        
        if mapping and mapping.get('confidence', 0) > 0.3:
            # Apply mapping to outline
            apply_mapping_to_outline(mapped_outline, filename, mapping)
            mapped_files.add(filename)
        else:
            print(f"Low confidence mapping for {filename}, using fallback")
            # Fallback: add to first available unit
            add_file_to_first_available_unit(mapped_outline, filename)
            mapped_files.add(filename)
    
    print(f"\nMapping completed. Successfully mapped {len(mapped_files)} files")
    print(f"Exact matches: {len([f for f in mapped_files if '✓' in str(f)])}")  # This won't work but shows intent
    
    # Print final outline structure
    print(f"\nFinal outline structure after mapping:")
    for i, chapter in enumerate(mapped_outline.get('outline', [])):
        print(f"Chapter {i}: {chapter.get('title', 'Untitled')}")
        for j, subsection in enumerate(chapter.get('subsections', [])):
            print(f"  Subsection {j}: {subsection.get('title', 'Untitled')} - {len(subsection.get('units', []))} units")
    
    return mapped_outline


def map_pdf_by_exact_filename(outline: dict, filename: str) -> bool:
    """
    Map PDF file to unit with exact matching filename in 'file' or 'pdf_file' field.
    Returns True if exact match found and mapped, False otherwise.
    """
    try:
        print(f"[EXACT_MATCH] Looking for exact match: {filename}")
        found_units = []
        
        # Remove .pdf extension for comparison
        filename_base = filename.replace('.pdf', '').replace('.PDF', '')
        
        for chapter_idx, chapter in enumerate(outline.get('outline', [])):
            for subsection_idx, subsection in enumerate(chapter.get('subsections', [])):
                for unit_idx, unit in enumerate(subsection.get('units', [])):
                    # Debug: show all units with file fields
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
                    
                    # Check exact match with full filename
                    if existing_file == filename or existing_pdf_file == filename:
                        print(f"[EXACT_MATCH] ✓ Found exact match (full): {filename} -> unit '{unit_title}' at Ch{chapter_idx}.{subsection_idx}.{unit_idx}")
                        
                        # Update the unit with PDF file
                        if unit.get('video_url'):
                            # If unit has video, set as pdf_file and type as video_pdf
                            unit['pdf_file'] = filename
                            if 'file' in unit:
                                del unit['file']  # Remove file field if exists
                            unit['type'] = 'video_pdf'
                            print(f"[EXACT_MATCH] Updated video unit with PDF: {unit_title}")
                        else:
                            # If no video, set as file and type as pdf
                            unit['file'] = filename
                            if 'pdf_file' in unit:
                                del unit['pdf_file']  # Remove pdf_file field if exists
                            if unit.get('type') not in ['video', 'video_pdf', 'docx', 'text']:
                                unit['type'] = 'pdf'
                            print(f"[EXACT_MATCH] Updated unit with PDF file: {unit_title}")
                        
                        return True
                    
                    # Check match without .pdf extension
                    existing_file_base = existing_file.replace('.pdf', '').replace('.PDF', '')
                    existing_pdf_file_base = existing_pdf_file.replace('.pdf', '').replace('.PDF', '')
                    
                    if existing_file_base == filename_base or existing_pdf_file_base == filename_base:
                        print(f"[EXACT_MATCH] ✓ Found exact match (base): {filename} -> unit '{unit_title}' at Ch{chapter_idx}.{subsection_idx}.{unit_idx}")
                        
                        # Update the unit with PDF file
                        if unit.get('video_url'):
                            # If unit has video, set as pdf_file and type as video_pdf
                            unit['pdf_file'] = filename
                            if 'file' in unit:
                                del unit['file']  # Remove file field if exists
                            unit['type'] = 'video_pdf'
                            print(f"[EXACT_MATCH] Updated video unit with PDF: {unit_title}")
                        else:
                            # If no video, set as file and type as pdf
                            unit['file'] = filename
                            if 'pdf_file' in unit:
                                del unit['pdf_file']  # Remove pdf_file field if exists
                            if unit.get('type') not in ['video', 'video_pdf', 'docx', 'text']:
                                unit['type'] = 'pdf'
                            print(f"[EXACT_MATCH] Updated unit with PDF file: {unit_title}")
                        
                        return True
        
        # Debug: show all units that have file/pdf_file fields
        if found_units:
            print(f"[EXACT_MATCH] Units with file fields found:")
            for unit_info in found_units:
                print(f"  - {unit_info['location']}: '{unit_info['title']}' file='{unit_info['file']}' pdf_file='{unit_info['pdf_file']}'")
        else:
            print(f"[EXACT_MATCH] No units with file/pdf_file fields found in outline")
        
        print(f"[EXACT_MATCH] ✗ No exact match found for: {filename}")
        return False
    except Exception as e:
        print(f"[EXACT_MATCH] Error in exact filename mapping: {e}")
        return False


def map_pdf_by_smart_title_matching(outline: dict, filename: str) -> bool:
    """
    Map PDF file to unit based on title similarity when exact filename match fails.
    This handles cases where unit title is similar to filename but no 'file' field exists.
    """
    try:
        # Remove extension and normalize filename for comparison
        name_base = filename.replace('.pdf', '').replace('.PDF', '')
        
        def normalize_for_comparison(text: str) -> str:
            """Normalize text for similarity comparison"""
            import re
            # Replace hyphens, colons, and underscores with spaces
            text = text.replace('-', ' ').replace(':', ' ').replace('_', ' ')
            # Remove special chars, convert to lowercase, remove extra spaces
            normalized = re.sub(r'[^\w\s]', '', text.lower())
            normalized = ' '.join(normalized.split())  # Remove extra spaces
            return normalized
        
        norm_filename = normalize_for_comparison(name_base)
        print(f"[SMART_MATCH] Looking for title match: '{name_base}' (normalized: '{norm_filename}')")
        
        best_match = None
        best_score = 0
        
        for chapter_idx, chapter in enumerate(outline.get('outline', [])):
            for subsection_idx, subsection in enumerate(chapter.get('subsections', [])):
                for unit_idx, unit in enumerate(subsection.get('units', [])):
                    unit_title = unit.get('title', '')
                    existing_file = unit.get('file', '')
                    existing_pdf_file = unit.get('pdf_file', '')
                    
                    # Skip if unit already has a PDF file with .pdf extension (already processed)
                    if (existing_file and existing_file.endswith('.pdf')) or (existing_pdf_file and existing_pdf_file.endswith('.pdf')):
                        continue
                    
                    # Allow units with pdf_file without extension (these need to be updated)
                    norm_title = normalize_for_comparison(unit_title)
                    
                    # Calculate similarity score
                    score = calculate_similarity_score(norm_filename, norm_title)
                    print(f"[SMART_MATCH] Comparing '{norm_filename}' vs '{norm_title}' (from '{unit_title}'): score={score:.3f}")
                    
                    if score > best_score and score > 0.7:  # Threshold for good match
                        best_match = {
                            'chapter_idx': chapter_idx,
                            'subsection_idx': subsection_idx, 
                            'unit_idx': unit_idx,
                            'unit': unit,
                            'score': score,
                            'title': unit_title
                        }
                        best_score = score
        
        if best_match:
            unit = best_match['unit']
            print(f"[SMART_MATCH] ✓ Found title match (score: {best_score:.2f}): {filename} -> '{best_match['title']}'")
            
            # Update the unit
            if unit.get('video_url'):
                # If unit has video, add PDF as pdf_file
                unit['pdf_file'] = filename
                unit['type'] = 'video_pdf'
                print(f"[SMART_MATCH] Updated video unit with PDF: {best_match['title']}")
            else:
                # If no video, set as PDF file
                unit['file'] = filename
                unit['type'] = 'pdf'
                print(f"[SMART_MATCH] Updated unit with PDF file: {best_match['title']}")
            
            return True
        
        print(f"[SMART_MATCH] ✗ No good title match found for: {filename}")
        return False
        
    except Exception as e:
        print(f"[SMART_MATCH] Error in smart title matching: {e}")
        return False


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


def analyze_filename_pattern(filename: str, outline_data: dict) -> dict:
    """Analyze filename pattern to determine chapter and subsection mapping"""
    # Remove extension
    name = filename.replace('.pdf', '').replace('.PDF', '')
    
    print(f"Analyzing filename pattern: {name}")
    
    # Pattern: Bài X-Y.pdf (Chương X, bài Y)
    pattern = re.match(r'Bài\s*(\d+)[-–](\d+(?:\.\d+)?)', name)
    if pattern:
        chapter_num = int(pattern.group(1))
        bai_str = pattern.group(0).replace(' ', '')  # "Bài6-3"
        bai_num = pattern.group(2)  # "3" hoặc "3.1"
        chapter_index = chapter_num - 1
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            # Tìm subsection có tiêu đề chứa "Bài X-Y" hoặc "X-Y"
            for sub_idx, subsection in enumerate(chapter.get('subsections', [])):
                sub_title = subsection.get('title', '').replace(' ', '')
                if f"Bài{chapter_num}-{bai_num}" in sub_title or f"{chapter_num}-{bai_num}" in sub_title:
                    return {
                        "chapter_index": chapter_index,
                        "subsection_index": sub_idx,
                        "unit_title": generate_unit_title_from_filename(filename),
                        "confidence": 0.95
                    }
            # Nếu không tìm thấy, fallback về subsection đầu tiên
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    
    # Pattern 1: C_X_Y.pdf (Chapter X, Subsection Y)
    pattern1 = re.match(r'C_(\d+)_(\d+)', name)
    if pattern1:
        chapter_num = int(pattern1.group(1))
        subsection_num = int(pattern1.group(2))
        print(f"Pattern 1 match: Chapter {chapter_num}, Subsection {subsection_num}")
        
        # Adjust chapter index (chapters start from 1, array starts from 0)
        chapter_index = chapter_num - 1
        subsection_index = subsection_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            if subsection_index < len(chapter.get('subsections', [])):
                return {
                    "chapter_index": chapter_index,
                    "subsection_index": subsection_index,
                    "unit_title": generate_unit_title_from_filename(filename),
                    "confidence": 0.9
                }
    
    # Pattern 2: C_X.pdf (Chapter X, first subsection)
    pattern2 = re.match(r'C_(\d+)', name)
    if pattern2:
        chapter_num = int(pattern2.group(1))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,  # First subsection
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    
    # Pattern 3: Theory_X_Y.pdf (Theory chapter X, subsection Y)
    pattern3 = re.match(r'Theory_(\d+)_(\d+)', name)
    if pattern3:
        chapter_num = int(pattern3.group(1))
        subsection_num = int(pattern3.group(2))
        chapter_index = chapter_num - 1
        subsection_index = subsection_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            chapter = outline_data['outline'][chapter_index]
            if subsection_index < len(chapter.get('subsections', [])):
                return {
                    "chapter_index": chapter_index,
                    "subsection_index": subsection_index,
                    "unit_title": generate_unit_title_from_filename(filename),
                    "confidence": 0.9
                }
    
    # Pattern 4: Theory_X.pdf (Theory chapter X, first subsection)
    pattern4 = re.match(r'Theory_(\d+)', name)
    if pattern4:
        chapter_num = int(pattern4.group(1))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.8
            }
    
    # Pattern 5: Look for chapter numbers in filename
    chapter_match = re.search(r'chương\s*(\d+)|chapter\s*(\d+)|c(\d+)', name.lower())
    if chapter_match:
        chapter_num = int(chapter_match.group(1) or chapter_match.group(2) or chapter_match.group(3))
        chapter_index = chapter_num - 1
        
        if chapter_index < len(outline_data.get('outline', [])):
            return {
                "chapter_index": chapter_index,
                "subsection_index": 0,
                "unit_title": generate_unit_title_from_filename(filename),
                "confidence": 0.7
            }
    
    # Pattern 6: Try to match by keywords in chapter titles
    keywords = name.replace('_', ' ').replace('-', ' ').split()
    best_match = find_best_chapter_match_by_keywords(keywords, outline_data.get('outline', []))
    
    if best_match is not None:
        return {
            "chapter_index": best_match,
            "subsection_index": 0,
            "unit_title": generate_unit_title_from_filename(filename),
            "confidence": 0.6
        }
    
    return None


def find_best_chapter_match_by_keywords(keywords: list, chapters: list) -> int:
    """Find best matching chapter based on keywords"""
    if not chapters or not keywords:
        return None
    
    best_match = 0
    best_score = 0
    
    for i, chapter in enumerate(chapters):
        chapter_title = chapter.get('title', '').lower()
        score = sum(1 for keyword in keywords if keyword.lower() in chapter_title)
        if score > best_score:
            best_score = score
            best_match = i
    
    return best_match if best_score > 0 else None


def generate_unit_title_from_filename(filename: str) -> str:
    """Generate unit title from filename"""
    # Remove extension and common prefixes
    title = filename.replace('.pdf', '').replace('.PDF', '')
    
    # Replace underscores and dashes with spaces
    title = title.replace('_', ' ').replace('-', ' ')
    
    # Capitalize first letter of each word
    title = ' '.join(word.capitalize() for word in title.split())
    
    return title


def apply_mapping_to_outline(outline: dict, filename: str, mapping: dict):
    """Apply mapping to outline structure by merging PDF into existing units when possible."""
    try:
        chapter_index = mapping.get('chapter_index', 0)
        subsection_index = mapping.get('subsection_index', 0)
        unit_title = mapping.get('unit_title', generate_unit_title_from_filename(filename))

        print(f"Applying mapping: {filename} -> Chapter {chapter_index}, Subsection {subsection_index}, Title: {unit_title}")

        if not (chapter_index < len(outline.get('outline', [])) and 
                subsection_index < len(outline['outline'][chapter_index].get('subsections', []))):
            print(f"Invalid indices: chapter_index={chapter_index}, subsection_index={subsection_index}")
            print(f"Available chapters: {len(outline.get('outline', []))}")
            if outline.get('outline') and chapter_index < len(outline['outline']):
                print(f"Available subsections in chapter {chapter_index}: {len(outline['outline'][chapter_index].get('subsections', []))}")
            return

        subsection = outline['outline'][chapter_index]['subsections'][subsection_index]
        if 'units' not in subsection:
            subsection['units'] = []
        units = subsection['units']

        # If PDF already mapped to any unit, skip
        for u in units:
            if u.get('file') == filename or u.get('pdf_file') == filename:
                print(f"PDF {filename} already mapped to unit '{u.get('title','')}', skipping")
                return

        def _normalize(s: str) -> str:
            import re
            return re.sub(r'[^a-z0-9]', '', (s or '').lower())

        base = filename.replace('.pdf', '').replace('.PDF', '')
        norm_title = _normalize(unit_title)
        norm_base = _normalize(base)

        # Try to find existing unit by title or close to filename base
        existing_unit = None
        for u in units:
            t = _normalize(u.get('title', ''))
            if t and (t == norm_title or t == norm_base or norm_title in t or t in norm_title or norm_base in t or t in norm_base):
                existing_unit = u
                break

        # If not found, try to find a unit that already has the same base in file/pdf_file
        if not existing_unit:
            for u in units:
                f = _normalize((u.get('file') or u.get('pdf_file') or '').replace('.pdf', ''))
                if f and (f == norm_base):
                    existing_unit = u
                    break

        if existing_unit:
            # Merge PDF into existing unit, prefer video_pdf when video exists
            if existing_unit.get('video_url'):
                existing_unit['pdf_file'] = filename
                if 'file' in existing_unit:
                    # normalize to pdf_file
                    existing_unit['pdf_file'] = existing_unit.get('pdf_file') or existing_unit['file']
                    del existing_unit['file']
                existing_unit['type'] = 'video_pdf'
                print(f"Merged PDF into existing video unit: {existing_unit.get('title','')}")
            else:
                existing_unit['file'] = filename
                if existing_unit.get('type') not in ['video', 'video_pdf', 'docx', 'text']:
                    existing_unit['type'] = 'pdf'
                print(f"Updated existing unit with PDF: {existing_unit.get('title','')}")
            return

        # As a last resort, create a new PDF unit (no match found)
        unit = {
            "title": unit_title,
            "type": "pdf",
            "file": filename
        }
        units.append(unit)
        print(f"Added new PDF unit: {unit_title}")
    except Exception as e:
        print(f"Error applying mapping: {e}")


def add_file_to_first_available_unit(outline: dict, filename: str):
    """Fallback: merge into a likely existing unit in the first available subsection, else create one."""
    try:
        if not outline.get('outline'):
            return
        for chapter_idx, chapter in enumerate(outline['outline']):
            if not chapter.get('subsections'):
                continue
            subsection = chapter['subsections'][0]
            if 'units' not in subsection:
                subsection['units'] = []
            units = subsection['units']

            # Prevent duplicate mapping
            for u in units:
                if u.get('file') == filename or u.get('pdf_file') == filename:
                    print(f"Fallback: PDF {filename} already present in a unit, skipping")
                    return

            # Try to match by similar title
            base_title = generate_unit_title_from_filename(filename)
            def _norm(s: str) -> str:
                import re
                return re.sub(r'[^a-z0-9]', '', (s or '').lower())
            nbase = _norm(base_title)
            target = None
            for u in units:
                if _norm(u.get('title', '')) in (nbase,) or nbase in _norm(u.get('title','')):
                    target = u
                    break

            if target:
                if target.get('video_url'):
                    target['pdf_file'] = filename
                    if 'file' in target:
                        target['pdf_file'] = target.get('pdf_file') or target['file']
                        del target['file']
                    target['type'] = 'video_pdf'
                    print(f"Fallback: merged PDF into existing video unit '{target.get('title','')}'")
                else:
                    target['file'] = filename
                    if target.get('type') not in ['video', 'video_pdf', 'docx', 'text']:
                        target['type'] = 'pdf'
                    print(f"Fallback: updated existing unit with PDF '{target.get('title','')}'")
                return

            # Create new unit only if no match
            unit = {
                "title": base_title,
                "type": "pdf",
                "file": filename
            }
            units.append(unit)
            print(f"Fallback: Added {filename} to chapter {chapter_idx}, first subsection as new unit")
            break
    except Exception as e:
        print(f"Error adding file to first unit: {e}")