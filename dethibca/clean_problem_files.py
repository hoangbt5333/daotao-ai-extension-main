#!/usr/bin/env python3
"""
Script để xóa tất cả các file XML trong thư mục problem có chứa 
<h3 class="hd hd-2 problem-header">Câu hỏi</h3> và cập nhật library.xml
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

def clean_problem_files(problem_dir, library_xml_path):
    """
    Xóa tất cả các file XML có chứa thẻ h3 với class "hd hd-2 problem-header" và text "Câu hỏi"
    và cập nhật library.xml để xóa các tham chiếu tương ứng
    
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
    
    deleted_files = []
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
                # Xóa file
                os.remove(xml_file)
                deleted_files.append(xml_file.stem)  # Lưu tên file không có extension
                print(f"🗑️  Đã xóa: {xml_file.name}")
            else:
                print(f"✅ Giữ lại: {xml_file.name}")
                
        except Exception as e:
            print(f"❌ Lỗi khi xử lý file {xml_file.name}: {e}")
    
    # Cập nhật library.xml
    if deleted_files:
        print("\n📝 Đang cập nhật library.xml...")
        update_library_xml(library_xml_path, deleted_files)
    
    print("=" * 50)
    print(f"📊 Kết quả:")
    print(f"   - Tổng số file: {total_files}")
    print(f"   - Đã xóa: {len(deleted_files)}")
    print(f"   - Còn lại: {total_files - len(deleted_files)}")

def update_library_xml(library_xml_path, deleted_files):
    """
    Cập nhật library.xml để xóa các tham chiếu đến file đã bị xóa
    
    Args:
        library_xml_path (str): Đường dẫn đến file library.xml
        deleted_files (list): Danh sách tên file đã bị xóa (không có extension)
    """
    try:
        # Đọc file library.xml
        with open(library_xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Tạo backup
        backup_path = library_xml_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"💾 Đã tạo backup: {backup_path}")
        
        # Parse XML
        root = ET.fromstring(content)
        
        # Tìm và xóa các thẻ problem có url_name trùng với file đã xóa
        removed_refs = 0
        for problem_elem in root.findall('.//problem'):
            url_name = problem_elem.get('url_name')
            if url_name in deleted_files:
                root.remove(problem_elem)
                removed_refs += 1
                print(f"🔗 Đã xóa tham chiếu: {url_name}")
        
        # Ghi lại file XML
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Thêm XML declaration nếu chưa có
        if not xml_str.startswith('<?xml'):
            xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
        
        with open(library_xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_str)
        
        print(f"✅ Đã cập nhật library.xml - xóa {removed_refs} tham chiếu")
        
    except Exception as e:
        print(f"❌ Lỗi khi cập nhật library.xml: {e}")

def main():
    """Hàm chính"""
    # Đường dẫn đến thư mục problem và file library.xml
    problem_dir = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library\problem"
    library_xml_path = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library\library.xml"
    
    print("🧹 Script xóa file problem có thẻ h3 'Câu hỏi' và cập nhật library.xml")
    print("=" * 60)
    
    # Xác nhận từ người dùng
    response = input(f"Bạn có chắc muốn xóa các file trong {problem_dir} và cập nhật {library_xml_path}? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        clean_problem_files(problem_dir, library_xml_path)
    else:
        print("❌ Đã hủy thao tác.")

if __name__ == "__main__":
    main() 