import os

def get_sorted_pdf_names(folder_path):
    """
    Đọc tên các file PDF trong folder và sắp xếp theo thứ tự alphabet
    
    Args:
        folder_path (str): Đường dẫn đến folder chứa file PDF
        
    Returns:
        list: Danh sách tên file PDF đã sắp xếp (không có đuôi .pdf)
    """
    try:
        # Kiểm tra xem folder có tồn tại không
        if not os.path.exists(folder_path):
            print(f"Folder '{folder_path}' không tồn tại!")
            return []
        
        # Lấy tất cả file trong folder
        all_files = os.listdir(folder_path)
        
        # Lọc chỉ lấy file PDF (không phân biệt hoa thường)
        pdf_files = [file for file in all_files if file.lower().endswith('.pdf')]
        
        # Loại bỏ đuôi .pdf và sắp xếp theo alphabet
        pdf_names = [os.path.splitext(file)[0] for file in pdf_files]
        pdf_names.sort()
        
        return pdf_names
    
    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")
        return []

# Cách sử dụng
if __name__ == "__main__":
    # Thay đổi đường dẫn folder theo nhu cầu
    folder_path = "."  # Folder hiện tại
    folder_path = r"C:\Users\duong\Downloads\Bài giảng"  # Hoặc đường dẫn cụ thể
    
    pdf_names = get_sorted_pdf_names(folder_path)
    
    if pdf_names:
        print(f"Tìm thấy {len(pdf_names)} file PDF:")
        print("-" * 50)
        for i, name in enumerate(pdf_names, 1):
            print(f"{name}")
    else:
        print("Không tìm thấy file PDF nào trong folder.")
        
    # Nếu muốn trả về danh sách để sử dụng trong code khác
    print(f"\nDanh sách tên file: {pdf_names}")