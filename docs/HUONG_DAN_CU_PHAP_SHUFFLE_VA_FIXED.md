# Hướng Dẫn Kỹ Thuật Open edX: Shuffle, Fixed, Display Name & Simple Editor Markdown Roundtrip

Tài liệu này ghi lại chi tiết toàn bộ bản chất kỹ thuật, nguyên nhân gốc rễ các lỗi đã phát hiện trên nền tảng **daotao.ai (Open edX)** và giải pháp sửa chữa triệt để đã được triển khai, kiểm thử và đưa lên hệ thống.

---

## 1. Bản chất quy chuẩn của Open edX Simple Editor Markdown & OLX XML

### 1.1. Cú pháp Markdown dạng trơn chuẩn (Plain Simple Editor Format)
Trong Open edX Studio, khi giảng viên soạn thảo câu hỏi trắc nghiệm một đáp án (Multiple Choice / Radio) và nhiều đáp án (Multiple Select / Checkbox) bằng trình soạn thảo Simple Editor, hệ thống quy định cú pháp dạng trơn (như file chuẩn `library.mau_chuan.tar.gz`) như sau:

#### A. Trắc nghiệm 1 đáp án đúng (Multiple Choice / Radio):
- **Dòng đầu tiên:** Nội dung câu hỏi trần (không dùng thẻ `<p/>`, không dùng `>>...<<`, không có dải `=====`).
- **Dòng phương án đầu tiên:**
  - `(!)`: Phương án sai + **Kích hoạt xáo trộn (Shuffle = True)** cho toàn bộ câu hỏi.
  - `(!x)`: Phương án đúng + **Kích hoạt xáo trộn (Shuffle = True)** cho toàn bộ câu hỏi.
  - `( )`: Phương án sai (khi câu hỏi **KHÔNG bật shuffle**).
  - `(x)`: Phương án đúng (khi câu hỏi **KHÔNG bật shuffle**).
- **Các dòng phương án từ thứ 2 trở đi:**
  - `(x)`: Phương án đúng thông thường (được xáo trộn ngẫu nhiên nếu câu bật shuffle).
  - `( )`: Phương án sai thông thường (phải **có khoảng trắng** giữa 2 ngoặc đơn, không dùng `()`).
  - `(@)`: Phương án sai nhưng **CỐ ĐỊNH (FIXED)** tại vị trí này, không bị đảo (ví dụ: *"Tất cả các phương án trên đều sai"* ở cuối).
  - `(@x)` hoặc `(x@)`: Phương án đúng nhưng **CỐ ĐỊNH (FIXED)** tại vị trí này.

```text
Thiết bị nào sau đây là sản phẩm của Apple?
(!) Napster
( ) Microsoft Zune
(x) iPod
( ) Walkman
(@) Tất cả các phương án trên đều sai
```

#### B. Trắc nghiệm nhiều đáp án đúng (Multiple Select / Checkbox):
- **Dòng đầu tiên:** Nội dung câu hỏi trần.
- **Các dòng phương án:**
  - `[x]`: Phương án đúng.
  - `[ ]`: Phương án sai (phải **có khoảng trắng** giữa 2 ngoặc vuông).
  - **Quy tắc quan trọng:** Checkbox trong Open edX Studio **tuyệt đối không hỗ trợ `!` (shuffle) và `@` (fixed)**.

```text
Những ngôn ngữ nào sau đây là ngôn ngữ lập trình hướng đối tượng?
[x] Java
[ ] C
[x] Python
[ ] HTML
[x] C++
```

---

### 1.2. Cấu trúc OLX XML chuẩn tương ứng
Khi Open edX Studio dịch Markdown trơn sang XML (hoặc xuất Library/Course OLX):
- Thẻ `<problem>` mang thuộc tính:
  - `display_name`: Tên định danh của câu hỏi.
  - `tags`: Mảng JSON các tag phân loại (ví dụ `tags="[\"Apple\", \"De-01\"]"`).
  - `markdown`: Toàn bộ nội dung markdown của câu hỏi, các dòng phân tách bằng ký tự xuống dòng `\n` (khi serialize XML được mã hóa thành thực thể `&#10;` duy nhất).
- Bên trong khối response:
  - Câu hỏi được bọc trực tiếp trong thẻ `<p>{question}</p>`. Nếu không có câu hỏi (chỉ có lựa chọn), không sinh thẻ `<p>`.
  - **Không có** thẻ rỗng `<p/>`.
  - **Không có** thẻ `<label>` mang text hướng dẫn như *"Chọn 1 đáp án đúng"* hay *"Chọn tất cả đáp án đúng"*.
  - Thuộc tính `shuffle="true"` trên thẻ `<choicegroup>` **CHỈ xuất hiện** khi câu hỏi có ký hiệu `!` ở dòng phương án đầu tiên.
  - Thuộc tính `fixed="true"` trên thẻ `<choice>` **CHỈ xuất hiện** khi phương án có ký hiệu `@`.
  - Thuộc tính `partial_credit="EDC"` hoặc `"halves"` được giữ nguyên trên thẻ `<choiceresponse>`.

```xml
<!-- XML chuẩn cho Radio có shuffle và fixed -->
<problem display_name="Cau-01" tags="[&quot;Apple&quot;]" markdown="Thiết bị nào sau đây là sản phẩm của Apple?&#10;(!) Napster&#10;( ) Microsoft Zune&#10;(x) iPod&#10;( ) Walkman&#10;(@) Tất cả các phương án trên đều sai&#10;">
  <multiplechoiceresponse>
    <p>Thiết bị nào sau đây là sản phẩm của Apple?</p>
    <choicegroup type="MultipleChoice" shuffle="true">
      <choice correct="false">Napster</choice>
      <choice correct="false">Microsoft Zune</choice>
      <choice correct="true">iPod</choice>
      <choice correct="false">Walkman</choice>
      <choice correct="false" fixed="true">Tất cả các phương án trên đều sai</choice>
    </choicegroup>
  </multiplechoiceresponse>
</problem>

<!-- XML chuẩn cho Checkbox có partial credit -->
<problem display_name="Cau-02" tags="[&quot;CNTT&quot;]" markdown="Những ngôn ngữ nào sau đây là ngôn ngữ lập trình hướng đối tượng?&#10;[x] Java&#10;[ ] C&#10;[x] Python&#10;[ ] HTML&#10;[x] C++&#10;">
  <choiceresponse partial_credit="EDC">
    <p>Những ngôn ngữ nào sau đây là ngôn ngữ lập trình hướng đối tượng?</p>
    <checkboxgroup>
      <choice correct="true">Java</choice>
      <choice correct="false">C</choice>
      <choice correct="true">Python</choice>
      <choice correct="false">HTML</choice>
      <choice correct="true">C++</choice>
    </checkboxgroup>
  </choiceresponse>
</problem>
```

---

## 2. Tổng hợp các lỗi kỹ thuật & nguyên nhân gốc rễ đã phát hiện

### Lỗi 1: Không nhận diện được ký hiệu `@` (Cố định vị trí)
- **Vị trí phát hiện:** `backend/app/api/v1/endpoints/questions.py`
- **Nguyên nhân:** Regex nhận diện marker phương án cũ là `re.match(r'^[\(\)!x\s]+', line)`, hoàn toàn không có ký tự `@`.
- **Hậu quả:** Khi người dùng nhập `(@)` hoặc `(@x)`, parser coi đó là nội dung câu hỏi mới, làm cắt vụn câu hỏi và mất đáp án.

---

### Lỗi 2: Hardcode `(!x)` ở mọi đáp án đúng gây ghim cứng vị trí
- **Vị trí phát hiện:** `backend/app/services/export/library.py` (code cũ)
- **Nguyên nhân:** Vòng lặp duyệt choices kiểm tra `if i in correct_answers:` thì luôn gán marker `(!x)`.
- **Hậu quả:**
  - Nếu đáp án đúng ở vị trí 2 hoặc 3, dấu `!` xuất hiện ở giữa câu hỏi khiến Open edX hiểu nhầm đáp án đó bị ghim cố định, làm mất tính năng xáo trộn tổng thể.
  - Dòng đầu tiên bị mất dấu `!` kích hoạt shuffle của Open edX.

---

### Lỗi 3: XML problem luôn bị gán cứng `display_name="Multiple Choice"`
- **Vị trí phát hiện:** `library.py` và `openedx.py`
- **Nguyên nhân:** Thuộc tính `display_name` của thẻ `<problem>` bị fix cứng chuỗi `"Multiple Choice"`.
- **Hậu quả:** Toàn bộ thẻ bài tập trong Library và LMS đều hiển thị cùng một tên, giảng viên không phân biệt được câu hỏi và không theo dõi được đề mục.

---

### Lỗi 4: Lỗi hiển thị và vỡ câu hỏi khi Chỉnh sửa (Edit) -> Lưu (Save) trong Studio Simple Editor
Đây là lỗi nghiêm trọng nhất ảnh hưởng trực tiếp đến quy trình biên tập đề thi trên Open edX Studio.
- **Hiện tượng:**
  - Gói Library import vào Studio ban đầu vẫn hiển thị làm bài được.
  - Tuy nhiên, khi giáo viên mở nút **"Chỉnh sửa" (Edit)** trong Simple Editor:
    - Nội dung bị dồn thành 1 dòng duy nhất, lộ mã thực thể XML thô:
      `<p/>&#10;Câu hỏi...&#10;=====&#10;>>Chọn tất cả đáp án đúng<<&#10;[x] ...`
    - Bấm **"Lưu" (Save)** lập tức làm hỏng câu hỏi: nội dung câu hỏi bị đẩy ra ngoài thành một đoạn text HTML vu vơ (`<p>`), tiêu đề câu hỏi bị đổi thành nhãn hướng dẫn "Chọn 1 đáp án đúng" / "Chọn tất cả đáp án đúng", hoặc mất tính năng chấm điểm.
- **Nguyên nhân gốc rễ:**
  1. **Lỗi Double-escaping ký tự xuống dòng (`&amp;#10;`):**
     - Code trong `helpers.py` thực hiện: `markdown_content = markdown_content.replace("\n", "&#10;")`.
     - Sau đó đưa vào `problem_elem.set("markdown", markdown_content)`.
     - Khi `lxml.etree.tostring` serialize XML, theo chuẩn W3C XML, thư viện `lxml` tự động escape ký tự `&` trong thuộc tính thành `&amp;`. Vì vậy chuỗi `&#10;` bị biến thành `&amp;#10;` trên file XML.
     - Khi Studio đọc XML, parser dịch `&amp;#10;` thành chuỗi ký tự `"&#10;"`. Simple Editor nhận chuỗi thô này và hiển thị dồn 1 dòng có chữ `&#10;`.
  2. **Nội dung Markdown chứa các thẻ và marker rác:**
     - Code cũ sinh: `<p/>\n{question}\n=====\n>>Chọn 1 đáp án đúng<<\n`.
     - Cụm `>>...<<` trong Open edX capa Simple Editor được hiểu là prompt/label của câu hỏi. Khi Studio parse lại markdown này, nó coi "Chọn 1 đáp án đúng" là câu hỏi, còn câu hỏi thật trước `=====` bị văng ra ngoài.
  3. **Bất nhất giữa XML và Markdown:**
     - XML của tool trước đó chứa `<p/>` rỗng, chứa thẻ `<label>` chứa chữ "Chọn 1 đáp án đúng", đẩy câu hỏi vào `<p>` thứ hai. Cấu trúc này không khớp với cách Studio biên dịch markdown trơn.
  4. **Marker đáp án sai dùng `"()"` không có khoảng trắng:**
     - Cú pháp chuẩn Studio yêu cầu `( )` có khoảng trắng.
  5. **Tự ý gán `shuffle="true"` cho tất cả câu hỏi:**
     - Parser cũ mặc định `current_shuffle = True`, dẫn đến câu hỏi không có `!` vẫn bị gán `shuffle="true"`.

---

## 3. Giải pháp sửa chữa triệt để & Kiến trúc hệ thống

### Bước 1: Nâng cấp Parser trong `backend/app/api/v1/endpoints/questions.py`
1. **Khởi tạo trạng thái mặc định không shuffle:**
   - Đặt `current_shuffle = False` khi bắt đầu parse câu hỏi mới.
   - Chỉ chuyển `current_shuffle = True` khi dòng phương án đầu tiên (`choice_idx == 0`) thực sự chứa ký tự `!`.
2. **Nhận diện đầy đủ marker phương án:**
   - Regex: `r'^\s*\(([!x@\s]*)\)\s*(.*)'`.
   - Đáp án đúng khi chứa `x`.
   - Phương án cố định khi chứa `@` (hoặc `!` ở các dòng từ thứ 2 trở đi).
   - Lưu trữ danh sách `fixed_choices` và cờ `shuffle` vào từ điển câu hỏi.

---

### Bước 2: Chuẩn hóa Markdown & XML trong `backend/app/services/export/helpers.py`

#### A. Hàm `create_markdown_content`:
- Sinh markdown trơn hoàn toàn, không có `<p/>`, `=====`, `>>...<<`, `||`.
- Dòng đầu tiên là nội dung câu hỏi (nếu có).
- **Với `multiple_choice`:**
  - Dòng 0: nếu câu có shuffle thì sinh `(!x)` (đúng) hoặc `(!)` (sai); nếu không shuffle thì sinh `(x)` (đúng) hoặc `( )` (sai).
  - Dòng cố định (`i in fixed_choices`): sinh `(@x)` hoặc `(@)`.
  - Phương án sai thông thường: luôn dùng `( )` có khoảng trắng.
- **Với `multiple_select`:**
  - Luôn dùng `[x]` và `[ ]` có khoảng trắng.
  - Tuyệt đối không sinh `!` và `@`.
- **Dấu xuống dòng:** Giữ nguyên `\n` thật trong chuỗi Python.

#### B. Hàm `build_single_problem_xml`:
- **Loại bỏ lệnh lỗi:** Xóa hoàn toàn `markdown_content.replace("\n", "&#10;")`.
  - Gán thẳng chuỗi chứa `\n` vào `problem_elem.set("markdown", markdown_content)`.
  - `lxml` tự động chuyển đổi `\n` thành `&#10;` chuẩn (single escape) trong XML.
- **Cấu trúc thẻ con chuẩn:**
  - Câu hỏi nằm trực tiếp trong thẻ `<p>{question}</p>` bên trong `<multiplechoiceresponse>` hoặc `<choiceresponse>`.
  - Không sinh thẻ `<p/>` rỗng, không sinh thẻ `<label>` hướng dẫn.
  - Thuộc tính `shuffle="true"` chỉ xuất hiện khi câu hỏi có shuffle (`has_shuffle = True`).
  - Thuộc tính `fixed="true"` chỉ xuất hiện khi lựa chọn nằm trong `fixed_choices`.
  - Bảo toàn `partial_credit` trên thẻ `<choiceresponse>`.

---

### Bước 3: Đảm bảo duy nhất MỘT hàm `build_single_problem_xml` dùng chung
- Toàn bộ các luồng xuất dữ liệu (Library, Course OLX, In-Video Quiz) đều dùng chung duy nhất một hàm chuẩn [`build_single_problem_xml`](backend/app/services/export/helpers.py) tại `helpers.py`.
- Tuyệt đối không tạo hàm trùng tên hoặc tự parse XML thủ công bằng gán chuỗi `.text`.

---

### Bước 4: Chuẩn hóa tên câu hỏi `display_name` qua `resolve_question_display_name`
- Hàm dùng chung `resolve_question_display_name` trong `helpers.py` xử lý:
  - Lấy tên giảng viên nhập trong trường `name` hoặc `display_name`.
  - Nếu thiếu: tự động fallback thành `Cau-01`, `Cau-02`...
  - Xử lý trùng lặp tự động thêm hậu tố `_1`, `_2`...
  - An toàn với tiếng Việt có dấu và ký tự đặc biệt XML (`&`, `<`, `>`, `"`).

---

## 4. Bộ Test TDD và Kết quả kiểm thử thực tế

Hệ thống kiểm thử được thiết lập theo phương pháp TDD với 77 bài test tự động bao phủ toàn diện:

| File Test | Số lượng test | Nội dung kiểm thử |
| :--- | :--- | :--- |
| **`test_problem_markdown_roundtrip.py`** | 10 tests | - So khớp 100% cấu trúc XML và Markdown với fixture chuẩn `library.mau_chuan.tar.gz` (Câu 01, 02, 03).<br>- Kiểm tra byte nhị phân trong file `.tar.gz` xuất ra: không chứa `&amp;#10;`, không chứa `<p/>`, `=====`, `>>...<<`.<br>- Kiểm tra ký tự xuống dòng `\n` thật.<br>- Kiểm tra ký tự đặc biệt (`&`, `<`, `>`, `"`) và tiếng Việt.<br>- Kiểm tra quy tắc `shuffle="true"` chỉ khi có `!` và `fixed="true"` chỉ khi có `@`. |
| **`test_multiselect_parity.py`** | 11 tests | - Parser trắc nghiệm nhiều đáp án (1 đáp án đúng, nhiều đáp án đúng, tất cả đúng).<br>- Validation (loại bỏ câu 0 đáp án đúng, câu thiếu phương án).<br>- Bỏ qua an toàn các biến thể `[!x]`, `[@]`, cảnh báo không hỗ trợ shuffle trên checkbox.<br>- Cấu trúc XML sạch, bảo toàn `partial_credit` (`EDC`, `halves`). |
| **`test_question_display_name.py`** | 11 tests | - Độ ưu tiên tên rõ ràng, fallback 2 chữ số (`Cau-01`), hậu tố trùng lặp, tiếng Việt, ký tự XML.<br>- Tích hợp `LibraryExporter` và `OpenEdXExporter`. |
| **`test_multi_tag.py`** | 12 tests | - Phân tích cú pháp `@tag:` theo cụm câu hỏi, thừa kế tag, tag có dấu tiếng Việt, ký tự ASCII đặc biệt. |
| **`test_outline_template.py`** | 10 tests | - Template outline Excel/CSV, forward-fill Lesson/Chapter, thông báo lỗi Type. |
| **`test_unit_types_export.py`** | 13 tests | - Chuẩn hóa Vertical, HTML component OLX, Audio, Video, PDF, Embed. |

**Kết quả kiểm thử trước khi bàn giao:**
```text
======================= 77 passed, 22 warnings in 2.75s =======================
```

---

## 5. Hướng dẫn kiểm tra Roundtrip trên Open edX Studio

Để kiểm tra xác nhận tính tương thích trên hệ thống Studio thực tế:
1. Xuất file thư viện câu hỏi `.tar.gz` từ hệ thống daotao.ai.
2. Đăng nhập Open edX Studio -> Vào **Thư viện (Libraries)** -> Chọn **Nhập (Import)** -> Nạp file `.tar.gz`.
3. Mở xem chi tiết câu hỏi trong thư viện: các câu hỏi hiển thị đầy đủ tiêu đề, câu hỏi, các lựa chọn đúng/sai và nhãn tag.
4. Bấm nút **Chỉnh sửa (Edit)** trên giao diện:
   - Trình soạn thảo Simple Editor hiển thị các dòng câu hỏi và lựa chọn ngắt dòng rõ ràng, mạch lạc bằng ký tự xuống dòng thật.
   - Không xuất hiện chuỗi `&#10;` thô, không có thẻ `<p/>` rác.
5. Bấm **Lưu (Save)**:
   - Câu hỏi được lưu thành công, giữ nguyên 100% cấu trúc, nội dung và các đáp án đúng/sai, không bị vỡ bố cục.
