#!/usr/bin/env python3
"""
Script để xem trước các file XML trong thư mục problem có chứa 
<h3 class="hd hd-2 problem-header">Câu hỏi</h3> mà không xóa chúng
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

def preview_problem_files(problem_dir, library_xml_path):
    """
    Xem trước các file XML có chứa thẻ h3 với class "hd hd-2 problem-header" và text "Câu hỏi"
    
    Args:
        problem_dir (str): Đường dẫn đến thư mục problem
        library_xml_path (str): Đường dẫn đến file library.xml
    """
    problem_path = Path(problem_dir)
    library_path = Path(library_xml_path)
    
    if not problem_path.exists():
        print(f"❌ Thư mục {problem_dir} không tồn tại!")
        return
    
    if not library_path.exists():
        print(f"❌ File {library_xml_path} không tồn tại!")
        return
    
    # Pattern để tìm thẻ h3 với class và text cụ thể
    pattern = r'<h3\s+class="hd\s+hd-2\s+problem-header">\s*Câu hỏi\s*</h3>'
    
    matched_files = []
    total_files = 0
    
    print(f"🔍 Đang quét thư mục: {problem_dir}")
    print("=" * 50)
    
    # Duyệt qua tất cả file XML trong thư mục
    for xml_file in problem_path.glob("*.xml"):
        total_files += 1
        
        try:
            # Đọc nội dung file
            with open(xml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Kiểm tra xem file có chứa pattern không
            if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                matched_files.append(xml_file.stem)  # Lưu tên file không có extension
                print(f"🔴 Sẽ xóa: {xml_file.name}")
            else:
                print(f"✅ Giữ lại: {xml_file.name}")
                
        except Exception as e:
            print(f"❌ Lỗi khi xử lý file {xml_file.name}: {e}")
    
    # Kiểm tra tham chiếu trong library.xml
    library_refs = []
    if matched_files:
        print("\n📋 Đang kiểm tra tham chiếu trong library.xml...")
        library_refs = check_library_references(library_xml_path, matched_files)
    
    print("=" * 50)
    print(f"📊 Kết quả xem trước:")
    print(f"   - Tổng số file: {total_files}")
    print(f"   - Sẽ xóa: {len(matched_files)}")
    print(f"   - Sẽ giữ lại: {total_files - len(matched_files)}")
    print(f"   - Tham chiếu trong library.xml sẽ bị xóa: {len(library_refs)}")
    
    if matched_files:
        print("\n📋 Danh sách file sẽ bị xóa:")
        for i, filename in enumerate(matched_files, 1):
            print(f"   {i:2d}. {filename}.xml")
    
    if library_refs:
        print("\n🔗 Danh sách tham chiếu trong library.xml sẽ bị xóa:")
        for i, ref in enumerate(library_refs, 1):
            print(f"   {i:2d}. <problem url_name=\"{ref}\"/>")
    
    return matched_files, library_refs

def check_library_references(library_xml_path, file_names):
    """
    Kiểm tra các tham chiếu trong library.xml sẽ bị xóa
    
    Args:
        library_xml_path (str): Đường dẫn đến file library.xml
        file_names (list): Danh sách tên file sẽ bị xóa
    
    Returns:
        list: Danh sách các tham chiếu sẽ bị xóa
    """
    try:
        with open(library_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        root = ET.fromstring(content)
        
        refs_to_remove = []
        for problem_elem in root.findall('.//problem'):
            url_name = problem_elem.get('url_name')
            if url_name in file_names:
                refs_to_remove.append(url_name)
        
        return refs_to_remove
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra library.xml: {e}")
        return []

def main():
    """Hàm chính"""
    # Đường dẫn đến thư mục problem và file library.xml
    problem_dir = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library\problem"
    library_xml_path = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library\library.xml"
    
    print("👀 Script xem trước file problem có thẻ h3 'Câu hỏi'")
    print("=" * 50)
    
    matched_files, library_refs = preview_problem_files(problem_dir, library_xml_path)
    
    if matched_files:
        print(f"\n💡 Để thực sự xóa {len(matched_files)} file và {len(library_refs)} tham chiếu, chạy:")
        print(f"   python backend/clean_problem_files.py")

if __name__ == "__main__":
    main() 