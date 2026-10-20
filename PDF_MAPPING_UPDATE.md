# PDF Mapping Logic Update

## Thay đổi thực hiện

Đã cập nhật logic mapping file PDF vào outline để **ưu tiên mapping chính xác theo tên file** thay vì chỉ dựa vào pattern analysis.

### Logic mới (theo thứ tự ưu tiên):

1. **Exact Filename Matching** (Mới) - Ưu tiên cao nhất
   - Tìm unit có field `file` hoặc `pdf_file` trùng khớp chính xác với tên file PDF
   - Ví dụ: PDF "Bai1_1.pdf" sẽ mapping vào unit có `"file": "Bai1_1.pdf"`

2. **Pattern Analysis** (Cũ) - Ưu tiên thứ hai  
   - Phân tích pattern tên file (Bài X-Y, C_X_Y, Theory_X_Y, v.v.)
   - Mapping dựa trên số chương, số bài

3. **Fallback** (Cũ) - Ưu tiên cuối cùng
   - Thêm vào subsection đầu tiên có sẵn

## Workflow sử dụng

### 1. Import outline từ Excel/CSV
- Cột "Slide" chứa tên file PDF chính xác
- Ví dụ: "Bai1_1.pdf", "ML_Introduction.pdf"
- Hệ thống tạo unit với field `file` = tên file PDF

### 2. Upload PDF files  
- Upload các file PDF có tên trùng khớp với cột "Slide"
- Hệ thống tự động mapping chính xác vào đúng unit

### 3. Kết quả mapping
- **Video + PDF**: Tạo unit type `video_pdf` với `video_url` và `pdf_file`
- **Chỉ PDF**: Tạo unit type `pdf` với `file`
- **Không match**: Sử dụng pattern analysis hoặc fallback

## File thay đổi

### `/backend/app/api/v1/endpoints/mapping.py`

**Function mới:**
```python
def map_pdf_by_exact_filename(outline: dict, filename: str) -> bool:
    """
    Map PDF file to unit with exact matching filename in 'file' or 'pdf_file' field.
    Returns True if exact match found and mapped, False otherwise.
    """
```

**Function cập nhật:**
```python
async def map_pdf_files_to_outline(files: List[UploadFile], outline_data: dict) -> dict:
    """Map PDF files to outline by matching exact filenames first, then using filename analysis"""
    # Thêm logic exact matching trước khi dùng pattern analysis
```

## Test & Validation

### Test script: `test_mapping_logic.py`
```bash
python test_mapping_logic.py
```

**Test cases:**
- ✅ Exact filename matching với field `file`
- ✅ Exact filename matching với field `pdf_file`  
- ✅ Video + PDF combination
- ✅ Auto type setting (`pdf`, `video_pdf`)
- ✅ Fallback khi không có exact match

### Manual Testing

1. **Tạo outline Excel:**
```csv
Chapter,Lesson,Unit,Slide,Youtube
Chương 1,Bài 1,Giới thiệu,ML_Intro.pdf,
Chương 1,Bài 2,Thực hành,Practice.pdf,https://youtube.com/watch?v=123
```

2. **Upload PDF files:**
- `ML_Intro.pdf` → Sẽ map vào "Giới thiệu" unit
- `Practice.pdf` → Sẽ map vào "Thực hành" unit (tạo video_pdf)

3. **Kiểm tra kết quả:**
```json
{
  "outline": [
    {
      "title": "Chương 1",
      "subsections": [
        {
          "title": "Bài 1", 
          "units": [
            {
              "title": "Giới thiệu",
              "type": "pdf",
              "file": "ML_Intro.pdf"
            }
          ]
        },
        {
          "title": "Bài 2",
          "units": [
            {
              "title": "Thực hành", 
              "type": "video_pdf",
              "video_url": "https://youtube.com/watch?v=123",
              "pdf_file": "Practice.pdf"
            }
          ]
        }
      ]
    }
  ]
}
```

## API Endpoint

**POST** `/api/v1/mapping/pdfs`

**Request:**
- `files`: List[UploadFile] - PDF files to map
- `outline`: str - JSON string of outline structure

**Response:**
- `success`: bool
- `mapped_outline`: dict - Updated outline with mapped PDFs
- `mapped_count`: int - Number of successfully mapped files
- `message`: str

## Lợi ích

1. **Chính xác cao**: Mapping dựa trên tên file chính xác thay vì guess work
2. **Dễ sử dụng**: Người dùng chỉ cần đặt tên file PDF giống với cột Slide trong Excel
3. **Tương thích ngược**: Vẫn hỗ trợ pattern analysis cho các trường hợp không có exact match
4. **Linh hoạt**: Hỗ trợ cả unit chỉ có PDF và unit có cả Video + PDF

## Next Steps

- [ ] Test với backend server đang chạy
- [ ] Test với frontend integration  
- [ ] Cập nhật documentation cho user
- [ ] Add validation cho duplicate filenames
