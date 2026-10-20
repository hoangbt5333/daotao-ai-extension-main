#!/usr/bin/env python3
"""
Script để nén folder thành file .tar.gz với khả năng chèn path tùy chỉnh
Usage: python compress_folder.py <source_folder> <output_file> [--insert-path <path>]

Cấu hình: Chỉnh sửa các biến bên dưới theo nhu cầu
"""

import os
import sys
import tarfile
import argparse
from pathlib import Path

# ==================== CẤU HÌNH ====================
# Chỉnh sửa các giá trị bên dưới theo nhu cầu của bạn

# Đường dẫn mặc định đến folder cần nén
DEFAULT_SOURCE_PATH = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library"

# Tên file output mặc định (sẽ tự động thêm .tar.gz nếu chưa có)
DEFAULT_OUTPUT_PATH = r"D:\github\OUTSOURCE\daotao-ai-extension\lib\cu\library_backup2"

# Path mặc định để chèn vào trước tất cả files trong archive
DEFAULT_INSERT_PATH = ""

# Danh sách folder cần bỏ qua
EXCLUDE_DIRS = [
    "__pycache__", "node_modules", ".git", ".vscode", ".idea", 
    "venv", "uploads", "exports", ".pytest_cache", "dist", "build"
]

# Danh sách file cần bỏ qua
EXCLUDE_FILES = [
    ".DS_Store", "Thumbs.db", ".env", ".env.local", 
    "*.pyc", "*.pyo", "*.log", "*.tmp"
]

# =================================================


def compress_folder(source_folder, output_file, insert_path=None):
    """
    Nén folder thành file .tar.gz
    
    Args:
        source_folder (str): Đường dẫn đến folder cần nén
        output_file (str): Tên file output .tar.gz
        insert_path (str, optional): Path để chèn vào trước tất cả files trong archive
    """
    # Kiểm tra folder nguồn có tồn tại không
    if not os.path.exists(source_folder):
        print(f"Lỗi: Folder '{source_folder}' không tồn tại!")
        return False
    
    # Đảm bảo output file có đuôi .tar.gz
    if not output_file.endswith('.tar.gz'):
        output_file += '.tar.gz'
    
    try:
        # Tạo file tar.gz
        with tarfile.open(output_file, 'w:gz') as tar:
            source_path = Path(source_folder).resolve()
            
            print(f"Đang nén folder: {source_path}")
            print(f"Output file: {output_file}")
            if insert_path:
                print(f"Chèn path: {insert_path}")
            print(f"Bỏ qua folders: {', '.join(EXCLUDE_DIRS)}")
            print(f"Bỏ qua files: {', '.join(EXCLUDE_FILES)}")
            
            # Duyệt qua tất cả files và folders trong source
            for root, dirs, files in os.walk(source_folder):
                # Bỏ qua các folder ẩn và cache
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in EXCLUDE_DIRS]
                
                for file in files:
                    # Bỏ qua các file ẩn và files trong danh sách exclude
                    if file.startswith('.') or file in EXCLUDE_FILES:
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    # Tính relative path từ source folder
                    rel_path = os.path.relpath(file_path, source_folder)
                    
                    # Nếu có insert_path, thêm vào trước
                    if insert_path:
                        archive_name = os.path.join(insert_path, rel_path)
                    else:
                        archive_name = rel_path
                    
                    # Thêm file vào archive
                    tar.add(file_path, arcname=archive_name)
                    print(f"  + {rel_path} -> {archive_name}")
        
        print(f"\n✅ Nén thành công! File: {output_file}")
        
        # Hiển thị thông tin về file đã tạo
        file_size = os.path.getsize(output_file)
        print(f"📁 Kích thước file: {file_size / (1024*1024):.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Lỗi khi nén: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Nén folder thành file .tar.gz với khả năng chèn path",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ sử dụng:
  python compress_folder.py                    # Sử dụng cấu hình mặc định
  python compress_folder.py ./my_folder output.tar.gz
  python compress_folder.py ./my_folder output.tar.gz --insert-path "data/backup"
  python compress_folder.py ./project output --insert-path "archive/2024"
  
Cấu hình: Chỉnh sửa các biến ở đầu file script theo nhu cầu
        """
    )
    
    parser.add_argument('source_folder', nargs='?', 
                       default=DEFAULT_SOURCE_PATH,
                       help=f'Đường dẫn đến folder cần nén (mặc định: {DEFAULT_SOURCE_PATH})')
    parser.add_argument('output_file', nargs='?',
                       default=DEFAULT_OUTPUT_PATH,
                       help=f'Tên file output .tar.gz (mặc định: {DEFAULT_OUTPUT_PATH})')
    parser.add_argument('--insert-path', '-p', 
                       default=DEFAULT_INSERT_PATH,
                       help=f'Path để chèn vào trước tất cả files trong archive (mặc định: {DEFAULT_INSERT_PATH})')
    
    args = parser.parse_args()
    
    # Kiểm tra arguments
    if not args.source_folder or not args.output_file:
        print("❌ Thiếu thông tin source_folder hoặc output_file!")
        print("💡 Bạn có thể:")
        print("   1. Chạy không có arguments để sử dụng cấu hình mặc định")
        print("   2. Hoặc cung cấp arguments: python compress_folder.py <source> <output>")
        print("   3. Hoặc chỉnh sửa các biến cấu hình ở đầu file script")
        print("\nThông tin chi tiết:")
        parser.print_help()
        sys.exit(1)
    
    # Hiển thị thông tin cấu hình
    print("🔧 Cấu hình hiện tại:")
    print(f"   Source folder: {args.source_folder}")
    print(f"   Output file: {args.output_file}")
    if args.insert_path:
        print(f"   Insert path: {args.insert_path}")
    print()
    
    # Thực hiện nén
    success = compress_folder(args.source_folder, args.output_file, args.insert_path)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 