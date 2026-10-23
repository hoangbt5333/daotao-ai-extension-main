# Giải thích Lỗi Xáo Trộn Đáp Án (Shuffle) & Cố Định Vị Trí (@) trong Open edX

Tài liệu này ghi lại chi tiết bản chất kỹ thuật, nguyên nhân gốc rễ của lỗi xáo trộn đáp án (shuffle) trên nền tảng **daotao.ai (Open edX)** và giải pháp sửa chữa triệt để.

---

## 1. Bản chất quy chuẩn của Open edX Simple Editor Markdown

Trong Open edX Studio, khi giảng viên soạn thảo câu hỏi trắc nghiệm một đáp án đúng (Multiple Choice) bằng trình soạn thảo Markdown (Simple Editor), hệ thống quy định vị trí và ý nghĩa của các dấu ngoặc như sau:

| Ký hiệu | Vị trí áp dụng | Ý nghĩa trong Open edX |
| :--- | :--- | :--- |
| **`(!)`** | **Chỉ ở dòng đầu tiên** | Phương án sai + **Kích hoạt tính năng xáo trộn (Shuffle = True)** cho toàn bộ câu hỏi. |
| **`(!x)`** | **Chỉ ở dòng đầu tiên** | Phương án đúng + **Kích hoạt tính năng xáo trộn (Shuffle = True)** cho toàn bộ câu hỏi. |
| **`(x)`** | Các dòng từ thứ 2 trở đi | Phương án đúng thông thường (được xáo trộn ngẫu nhiên). |
| **`( )`** hoặc **`()`** | Các dòng từ thứ 2 trở đi | Phương án sai thông thường (được xáo trộn ngẫu nhiên). |
| **`(@)`** | Bất kỳ dòng nào | Phương án sai nhưng **CỐ ĐỊNH (FIXED)** tại vị trí này, không bị xáo trộn (ví dụ: *"Tất cả các phương án trên đều sai"* ở vị trí cuối). |
| **`(@x)`** hoặc **`(x@)`** | Bất kỳ dòng nào | Phương án đúng nhưng **CỐ ĐỊNH (FIXED)** tại vị trí này (ví dụ: *"Tất cả các phương án trên đều đúng"* ở vị trí cuối). |

### Ví dụ chuẩn từ tài liệu Open edX:
```text
>>Thiết bị nào sau đây là sản phẩm của Apple?<<
(!) Napster
( ) Microsoft Zune
(x) iPod
( ) Walkman
(@) Tất cả các phương án trên đều sai
```
- Dòng 1 có `(!)`: edX hiểu là **Bật shuffle** cho câu hỏi này.
- Dòng 3 có `(x)`: Là đáp án đúng, được shuffle tự do giữa các vị trí A, B, C, D.
- Dòng 5 có `(@)`: Luôn cố định nằm ở vị trí cuối cùng (E).

---

## 2. Nguyên nhân gốc rễ của lỗi hiện tại trong dự án

### Lỗi 1: Không nhận diện được ký hiệu `@` (Cố định vị trí)
- **Vị trí:** `backend/app/api/v1/endpoints/questions.py` (dòng 488)
- **Đoạn code:**
  ```python
  marker_match = re.match(r'^[\(\)!x\s]+', line)
  ```
- **Hiện tượng:** Regex chỉ liệt kê `(`, `)`, `!`, `x`, hoàn toàn **không có ký tự `@`**. Khi người dùng nhập `(@)` hoặc `(@x)`, parser không nhận diện được phương án, dẫn đến coi đó là một câu hỏi mới và cắt vụn dữ liệu.

### Lỗi 2: Hardcode `(!x)` ở mọi đáp án đúng gây lỗi ghim cứng vị trí
- **Vị trí:** `backend/app/services/export/library.py` (dòng 243–247)
- **Đoạn code:**
  ```python
  for i, choice in enumerate(choices):
      if i in correct_answers:
          markdown_content += f"(!x) {choice}. \n"  # <-- LỖI: Ép cứng (!x) cho mọi đáp án đúng
      else:
          markdown_content += f"() {choice}\n"
  ```
- **Hậu quả:**
  - **Khi đáp án đúng ở dòng đầu tiên (`i = 0`):**
    Dòng đầu được sinh ra là `(!x) A.` -> Vô tình dấu `!` rơi trúng dòng đầu tiên, kích hoạt công tắc Shuffle của edX. Tất cả các phương án được đảo ngẫu nhiên bình thường.
  - **Khi đáp án đúng ở dòng 2 hoặc 3 (ví dụ C ở dòng 3):**
    - Dòng 1 sinh ra là `() A` -> Mất dấu `!` kích hoạt shuffle của edX!
    - Dòng 3 sinh ra là `(!x) C.` -> Dấu `!` xuất hiện ở giữa câu hỏi khiến edX hiểu nhầm là phương án C bị ghim cố định, trong khi các phương án khác bị lệch hành vi xáo trộn.

---

## 3. Kế hoạch sửa chữa chi tiết

### Bước 1: Nâng cấp Parser trong `backend/app/api/v1/endpoints/questions.py`
1. Sửa Regex nhận diện marker phương án thành `r'^\s*\([!x@\s]*\)'` để chấp nhận đầy đủ:
   - `(x)`, `( )`, `()`
   - `(!x)`, `(!)`
   - `(@)`, `(@x)`, `(x@)`
2. Trích xuất thông tin:
   - `is_correct`: chứa ký tự `x`.
   - `is_fixed`: chứa ký tự `@` (hoặc `!` nếu ở các dòng từ thứ 2 trở đi).
   - `has_shuffle`: câu hỏi có yêu cầu shuffle (mặc định luôn là `True` cho Multiple Choice).
3. Lưu trữ thêm trường `fixed_choices` (danh sách index các lựa chọn cố định) trong cấu trúc dữ liệu của câu hỏi.

### Bước 2: Nâng cấp Exporter trong `backend/app/services/export/library.py`
1. **Sinh Markdown (`_create_markdown_content`):**
   - **Dòng đầu tiên (`i == 0`):**
     - Nếu câu hỏi có shuffle:
       - Nếu đúng: sinh `(!x) {choice}`
       - Nếu sai: sinh `(!) {choice}`
   - **Các dòng tiếp theo (`i > 0`):**
     - Nếu là phương án cố định (`i in fixed_choices`):
       - Nếu đúng: sinh `(@x) {choice}`
       - Nếu sai: sinh `(@) {choice}`
     - Nếu là phương án bình thường:
       - Nếu đúng: sinh `(x) {choice}` *(không có dấu `!`)*
       - Nếu sai: sinh `( ) {choice}`
2. **Sinh XML (`_create_problem_xml_for_library`):**
   - Với các phương án có trong `fixed_choices`, bổ sung thuộc tính chuẩn XML của Open edX: `fixed="true"`.
   ```xml
   <choice correct="false" fixed="true">Tất cả đều sai</choice>
   ```

### Bước 3: Kiểm thử toàn diện
1. Test Case 1: Đáp án đúng ở dòng đầu `(!x) A` -> Sinh Markdown chuẩn: dòng đầu `(!x)`, các dòng sau `( )`.
2. Test Case 2: Đáp án đúng ở dòng 3 `(x) C`, dòng đầu `(!) A` -> Sinh Markdown chuẩn: dòng đầu `(!) A`, dòng 3 `(x) C`. Toàn bộ đều đảo ngẫu nhiên khi vào edX.
3. Test Case 3: Có phương án cố định `(@)` ở cuối -> Sinh Markdown `(@)` và thẻ XML có `fixed="true"`.
