# Báo cáo kiến trúc

> Phạm vi: rà soát mã nguồn và file tài liệu được liệt kê trong repo. Báo cáo phân biệt hiện trạng quan sát được với suy luận; không thay đổi file code. Đường dẫn bên dưới tương đối từ thư mục gốc.

## 1. Loại ứng dụng, công nghệ, build và chạy

- **Đã thấy trong code:** Đây là ứng dụng web nội bộ dạng frontend/backend, không phải extension trình duyệt. Frontend là Next.js App Router, React và TypeScript; backend là API Python FastAPI. Một số script Python chạy độc lập cũng có trong repo. Căn cứ: `frontend/package.json` (Next.js 15.4.3, React 19, TypeScript 5; scripts `dev`, `build`, `start`), `backend/app/main.py` (`app = FastAPI(...)`), `backend/code_cu/main.py` (ứng dụng FastAPI cũ/độc lập).
- Frontend dùng Material UI (`frontend/package.json`), backend dùng Pydantic, `python-multipart`, `pdfplumber`, `python-docx`, `openpyxl`, `lxml`, `requests` và `structlog` (`backend/requirements.txt`). Có các LLM provider OpenAI, Gemini, DeepSeek dưới `backend/app/services/llm/providers/`.
- **Build/chạy local:** backend theo `backend/README.md`: cài `backend/requirements.txt`, cấu hình env từ `backend/example.env`/`backend/README.md`, chạy `uvicorn app.main:app --host 0.0.0.0 --port 8000` từ thư mục `backend` (hoặc `python -m app.main`). Frontend: chạy `npm install`, `npm run dev` trong `frontend`; build bằng `npm run build`, chạy production bằng `npm run start` (`frontend/package.json`).
- **Docker:** `docker-compose.yml` dựng backend cổng 8000 và frontend cổng 3000 ở chế độ development; lệnh tương ứng nằm trong `backend/Dockerfile` và `frontend/Dockerfile`.
- **Lưu ý:** tên repo có “extension” nhưng không thấy manifest trình duyệt như `manifest.json`; tên gọi không chứng minh đây là extension.

## 2. Cấu trúc thư mục và vai trò

- `frontend/app/`: các route của Next.js: trang chính, tạo outline, chuyển định dạng, ngân hàng câu hỏi, tạo đề thi, video quiz và hướng dẫn. Các route dùng component trong `frontend/components/`.
- `frontend/components/`: giao diện và logic trình duyệt. Các luồng chính nằm tại `CourseGeneratorTool.tsx`, `QuestionBankTool.tsx`, `VideoQuizTool.tsx`, `ExamGeneratorTool.tsx`; `EditableOutlineTree.tsx` cho chỉnh outline. `FormatConverterTool.tsx` hiện chỉ hiển thị “đang được phát triển”.
- `frontend/config/api.ts`: base URL/API path và danh sách endpoint. Tuy vậy một số component dùng trực tiếp `http://localhost:8000` thay vì `getApiUrl`.
- `backend/app/api/v1/endpoints/`: HTTP endpoints chia theo chức năng (`questions.py`, `export.py`, `outline.py`, `mapping.py`, `providers.py`). `router.py` đăng ký các router dưới `/api/v1`.
- `backend/app/services/`: xử lý nghiệp vụ. `export/` sinh định dạng Open edX/library/exam/video quiz; `file/` trích xuất và đóng gói; `llm/` gọi các nhà cung cấp LLM.
- `backend/app/models/`: domain models trong `models/domain/`, schemas request/response trong `models/schemas/`.
- `backend/app/config/` và `backend/app/core/`: cấu hình, exceptions và logging; `backend/app/main.py` tạo FastAPI app, cấu hình CORS, mount thư mục export và gắn API router.
- `backend/code_cu/`: nhóm exporter/API phiên bản cũ hoặc mã thử nghiệm song song với `backend/app/`. Ví dụ `backend/code_cu/main.py`, `backend/code_cu/openedx_exporter.py`, `backend/code_cu/video_quiz_exporter.py`. Không nên mặc định sửa nhóm này thay cho `backend/app/` nếu chưa xác định luồng đang được chạy.
- `dethibca/`: script tiện ích xử lý/preview problem files. `compress_folder.py`: script đóng gói tổng quát ở root.
- `docs/`: có `docs/huong_dan_daotao_ai_trich_xuat.docx`. Không tìm thấy file tài liệu có tên/nội dung `invideoquiz_v2` được lập chỉ mục trong repo.
- **Không thấy `samples/`** trong danh sách file/thư mục repo. Không thể chỉ ra fixture mẫu sẵn có trong thư mục này.

## 3. Luồng chuyển câu hỏi sang dữ liệu Open edX

### Đầu vào và xử lý

1. Người dùng nhập/dán text câu hỏi trên `frontend/components/QuestionBankTool.tsx`, state `questionsText`. Đây không phải luồng upload file; các file có định dạng đầu vào cụ thể không bắt buộc.
2. `handleProcessQuestions()` gửi `FormData` gồm `questions_text`, `user_tags`, `tags_explanation`, `mode` và tùy chọn `user_format` đến `POST /api/v1/questions/process`.
3. `backend/app/api/v1/endpoints/questions.py::process_questions()` đọc các trường form. Chế độ `llm` gọi `LLMService.analyze_questions()` (khai báo ở `backend/app/services/llm/base.py`), rồi kiểm tra/ghép kết quả; nếu phản hồi không dùng được thì fallback sang parser. Chế độ custom gọi `parse_questions_from_text()` hoặc `parse_multiple_select_questions_from_text()`. `apply_user_tags_to_questions()` áp tag theo giải thích nếu có.
4. Frontend nhận mảng câu hỏi, cho chỉnh sửa nội dung/tag, rồi `handleExportLibrary()` gửi JSON câu hỏi cùng metadata đến `POST /api/v1/export/library`.
5. `backend/app/api/v1/endpoints/export.py::export_library()` parse JSON và gọi `export_service.export("library", ...)`. `backend/app/services/export/base.py::ExportService.export()` định tuyến đến `LibraryExporter`; `backend/app/services/export/library.py::LibraryExporter._create_library_structure()` tạo từng problem XML và library XML, sau đó đóng thành `.tar.gz`.

### Đầu ra

- Kết quả parse trung gian là JSON danh sách câu hỏi, mỗi câu có thể có `question`, `type`, `choices`, `correct_answers`, `tags`…
- Export từ giao diện Question Bank là gói Open edX Library `.tar.gz`, được phục vụ qua `/exports/...`; không phải file text/XML đơn lẻ. `LibraryExporter._create_problem_xml_for_library()` lưu `tags` trên problem XML.
- Một luồng khác là `CourseGeneratorTool.handleConvert()` gửi outline/questions đến `POST /api/v1/export/`; `export_openedx()` gọi `OpenEdXExporter`, nơi `_create_problems_from_questions()` tạo problem XML và đưa vào tar.gz cấu trúc course. Frontend hiện có `FormatConverterTool` riêng nhưng chưa triển khai chức năng (`frontend/components/FormatConverterTool.tsx`).
- `backend/app/services/file/extractor.py::extract_text_from_file()` hỗ trợ PDF, DOCX, TXT, nhưng đó là luồng trích văn bản file nói chung; không phải input trực tiếp của chức năng parse câu hỏi tại `questions/process`.

## 4. Luồng xây dựng tài liệu/outline khóa học

1. UI ở `frontend/components/CourseGeneratorTool.tsx` cho nhập outline từ Excel `.xlsx` hoặc CSV; `handleExcelPreview()` gửi file đến `POST /api/v1/outline/import-excel`.
2. `backend/app/api/v1/endpoints/outline.py::import_outline_excel()` đọc workbook/CSV, dùng `_header_index()`, `_normalize_rows()` và `_build_outline()` để dựng cấu trúc `chapters > subsections > units`. Header bắt buộc: `Chapter`, `Lesson`, `Unit`, `Slide`, `Youtube`. `_build_outline()` hợp nhất dòng cùng `Chapter + Lesson + Unit`.
3. UI có thể upload nhiều PDF; `handleAutoMapPdfs()` gọi `POST /api/v1/mapping/pdfs`. `backend/app/api/v1/endpoints/mapping.py` nhận files và outline rồi phân tích tên file/map vào unit. Sau đó người dùng có thể chỉnh outline qua `EditableOutlineTree`.
4. `handleConvert()` gửi outline, danh sách PDF và câu hỏi sang `/api/v1/export/`. `backend/app/api/v1/endpoints/export.py::export_openedx()` lưu PDF tạm và gọi `export_service.export("openedx", ...)`.
5. `backend/app/services/export/openedx.py::OpenEdXExporter._export_course_structure()` đi qua chapters/subsections/units, sinh XML cho chapter, sequential, vertical và components. `_create_vertical_xml()` chọn thành phần theo `unit["type"]`; `_copy_pdfs_to_static()` đưa PDF vào gói. `OpenEdXExporter.export()` tạo cấu trúc thư mục tạm, gọi `_create_tarfile()` và trả về `.tar.gz` qua `/exports/...`.

**Cách tạo cấu trúc:** đã thấy code tự sinh XML theo định dạng import Open edX và tạo file tar.gz cục bộ. Không thấy lời gọi HTTP tới Studio API hay thao tác tự động giao diện Studio trong luồng này. Giáo viên tải gói và import thủ công theo hướng dẫn UI.

**Loại unit:** xử lý trực tiếp trong `OpenEdXExporter._create_vertical_xml()` gồm:
- `video`: tạo component video.
- `video_pdf`: video kèm HTML link/iframe PDF.
- `pdf`: HTML iframe PDF.
- `docx`: tạo HTML component nhưng nhánh hiện không đọc/nội dung file DOCX vào component.
- Mặc định, gồm `text` hoặc type khác: tạo HTML component.

Provider prompts (`backend/app/services/llm/providers/{openai,gemini,deepseek}.py`) nêu các type `pdf`, `video`, `docx`, `text`, `video_pdf`; flow outline Excel hiện chỉ tạo `pdf`, `video`, `video_pdf` hoặc unit trống (type mặc định khi export là `text`). UI Excel mô tả hàng không có media là bỏ qua, nhưng `_build_outline()` thực tế vẫn giữ unit khi cột `Unit` được điền; cần phân biệt UI hướng dẫn với logic backend.

## 5. Cách xử lý tag hiện tại

- UI Question Bank có một ô tags cho cả lượt xử lý, tách bằng dấu phẩy (`QuestionBankTool.tsx`, state `userTags`); gửi cùng request dưới `user_tags`.
- Parser có thể đọc marker dòng `de0`, `de1`… trong text. `parse_questions_from_text()` gán marker hiện hành cho các câu tiếp theo; hiện marker được cập nhật khi gặp marker mới, không reset sau từng câu. Parser multiple-select cũng giữ `current_de_tag` như vậy.
- Nếu chỉ dùng `user_tags` bình thường, parser thêm các tag đó cho mỗi câu. Với `tags_explanation`, `apply_user_tags_to_questions()` cố gắng chỉ áp tag thường cho câu có marker `deX` được nhắc trong phần giải thích; nếu giải thích không nhắc de tag nào, áp dụng cho tất cả.
- Chế độ LLM được hướng dẫn thêm user tags vào từng câu; phần hậu xử lý cũng có thể thêm chúng cho toàn bộ câu khi không có giải thích. Tag sau đó có thể được chỉnh từng câu trên UI trước export.
- **Kết luận:** tag `deX` có thể phân nhóm theo câu thông qua marker trong text; tag nhập ở ô UI không có mapping độc lập theo câu, thường được coi là tag chung cả lần chuyển, trừ trường hợp dùng `tags_explanation` để phân nhóm theo marker. Cần lưu ý fallback và nhánh LLM có logic hậu xử lý riêng.

## 6. Vị trí cần sửa cho các mở rộng

### (a) Tag riêng cho từng câu trong một lượt chuyển

- UI và payload: `frontend/components/QuestionBankTool.tsx::handleProcessQuestions()` hiện gửi `user_tags` dạng một mảng chung. Cần đổi UX/state/payload để mang mapping theo câu (ví dụ gán tag tại từng câu sau parse, hoặc cấu trúc input có tag theo block).
- Parser và hậu xử lý: `backend/app/api/v1/endpoints/questions.py::process_questions()`, `parse_questions_from_text()`, `parse_multiple_select_questions_from_text()`, `apply_user_tags_to_questions()` hiện là nơi gắn tag. Đảm bảo tag theo câu không bị các bước hậu xử lý thêm tag chung ghi đè/áp tràn.
- Duy trì chỉnh sửa/export: `QuestionBankTool` đã có giao diện sửa tag trên từng câu; `backend/app/services/export/library.py::LibraryExporter._create_problem_xml_for_library()` serializes `question_data["tags"]` vào XML. Kiểm thử output XML cuối để chắc mỗi câu giữ đúng tag.

### (b) Thêm loại unit ngoài PDF và video

- UI/outline schema và nhập liệu: `frontend/components/CourseGeneratorTool.tsx`, `frontend/components/EditableOutlineTree.tsx`, `backend/app/api/v1/endpoints/outline.py::_build_outline()` và schema liên quan cần hỗ trợ trường/loại mới, nếu cần file đính kèm.
- Sinh Open edX: `backend/app/services/export/openedx.py::OpenEdXExporter._create_vertical_xml()` là điểm quyết định cách tạo component cho từng type. Nếu loại mới cần asset, cần cập nhật thêm lưu/copy file vào cấu trúc đúng trong `_export_course_structure()` và kiểm tra gói tar.gz.
- Nếu cần AI đề xuất unit, cập nhật format/prompt/validation ở `backend/app/services/llm/providers/*.py` và các schema liên quan; chỉ đổi prompt là chưa đủ nếu exporter không biết type đó.

### (c) Tự gắn câu hỏi vào video (`invideoquiz_v2`)

- Luồng UI hiện có: `frontend/components/VideoQuizTool.tsx` nhập video, câu hỏi và timestamp; `handleExportVideoQuiz()` gửi `/api/v1/export/video-quiz`.
- Exporter đang được dùng: `backend/app/services/export/video_quiz.py::VideoQuizExporter._create_video_quiz_structure()`, `_create_vertical_xml_for_video_quiz()`, `_create_video_xml()`, `_create_invideoquiz_xml()`. Endpoint nối qua `backend/app/api/v1/endpoints/export.py::export_video_quiz()` và `ExportService`.
- Nên xác minh/cập nhật cấu trúc XML và mapping timestamp→problem trong exporter đang chạy, sau khi đối chiếu mẫu `invideoquiz_v2` hợp lệ của môi trường daotao.ai/Open edX. Có logic timemap trong mã cũ `backend/code_cu/video_quiz_exporter.py` (hàm `create_video_quiz_structure()` và `create_video_quiz_xml_for_video_quiz()`), nhưng đó không phải exporter mới trong `backend/app/services/export/`; không nên coi là implementation hiện hành.
- `backend/app/services/export/video_quiz.py` hiện sinh `problem` và một file `problem` điều khiển quiz. Quan hệ component, loại XBlock chính xác, định dạng timemap và cách import tương thích `invideoquiz_v2` **chưa xác nhận được** chỉ từ code hiện hành. File `docs/huong_dan_daotao_ai_trich_xuat.docx` cần được đọc/đối chiếu thủ công nếu có quy cách đó; tìm kiếm text trong repo không cho thấy tài liệu `invideoquiz_v2` riêng.

## 7. Test và đề xuất kiểm thử nhỏ nhất

- Có pytest trong `backend/requirements.txt`, nhưng danh sách file hiện thấy không có test suite rõ cho `backend/app/`. Có script `backend/test_parser.py::test_parse()` tự in kết quả, nhưng định nghĩa parser bên trong là bản minh họa riêng, không import `app/api/v1/endpoints/questions.py`; do đó không phải test tự động đáng tin cậy cho parser production.
- Có `backend/code_cu/test_library_export.py`, nhưng tên/vị trí cho thấy nó thuộc mã cũ; cần kiểm tra import trước khi dùng làm test của `app/`. Các file `test_exact_matching.py`, `test_mapping_logic.py`, `test_smart_matching.py` ở root chưa được rà soát nội dung sâu; chưa xác minh được chúng chạy bằng pytest hay còn phù hợp.
- Lệnh tổng quát được `backend/README.md` ghi là `pytest` chạy từ `backend`, nhưng đây mới là hướng dẫn; chưa xác nhận toàn suite hiện chạy thành công. Frontend không khai báo script test trong `frontend/package.json`.
- Không tìm thấy thư mục `samples/`, vì vậy hiện không thể đề xuất đường dẫn fixture cụ thể bên trong đó. Kiểm thử nhỏ nhất sau khi bổ sung/chọn file mẫu đã được phép dùng:
  1. Dùng một file câu hỏi đã ẩn danh/không có dữ liệu sinh viên thật, với hai câu, đáp án marker `(x)`/`(!x)` và marker `de0` rồi `de1`; POST `/api/v1/questions/process` ở custom mode, xác nhận số câu, đáp án đúng và tag từng câu.
  2. Gửi JSON kết quả đến `/api/v1/export/library`, mở tar.gz và kiểm tra mỗi `library/problem/*.xml` có tags đúng.
  3. Với outline, dùng CSV/XLSX nhỏ có header bắt buộc và một hàng PDF, một hàng Youtube, một hàng kết hợp; gọi `/api/v1/outline/import-excel`, kiểm tra type/structure; sau đó export và kiểm tra tar.gz có XML course hierarchy cùng static PDF tương ứng.
  4. Với video quiz, dùng video URL test và hai câu timestamp khác nhau; export rồi kiểm tra XML/timemap đối chiếu với gói mẫu `invideoquiz_v2` chuẩn trước khi kết luận tương thích.
- Có thể trước mắt chạy `cd backend && pytest`; nếu các file test hiện có không kiểm tra `backend/app`, ưu tiên một test pytest nhỏ import hàm parser/exporter hiện hành và dùng fixture giả/ẩn danh, không cần thêm thư viện.

## 8. Rủi ro và điều chưa chắc chắn

### Đã thấy trong code

- Tên repo không tương ứng với cấu trúc browser extension; frontend/backend là ứng dụng web/API (`frontend/package.json`, `backend/app/main.py`).
- UI `format-converter` hiện là placeholder (`frontend/components/FormatConverterTool.tsx`), trong khi chức năng parse/export câu hỏi nằm ở Question Bank và backend.
- Có hai thế hệ mã: `backend/app/` và `backend/code_cu/`; một số hành vi trong mã cũ khác exporter hiện hành.
- Frontend có địa chỉ backend hard-coded `http://localhost:8000` trong `CourseGeneratorTool.tsx` và `VideoQuizTool.tsx` (một số config khác dùng env trong `frontend/config/api.ts`). Điều này có thể không phù hợp khi triển khai host khác.
- `CourseGeneratorTool` gửi các file được lọc là PDF; endpoint export course chỉ lưu upload có tên kết thúc `.pdf`. Nhánh `docx` của exporter chưa chèn nội dung DOCX vào HTML. PDF của unit được tham chiếu bằng tên file nên mapping/tên file phải thống nhất.
- `OpenEdXExporter._create_vertical_xml()` tạo video và HTML/PDF, nhưng ở luồng course chính không thấy gắn câu hỏi vào timestamp video; video quiz là luồng export riêng.
- `VideoQuizTool` có timestamp/seconds ở frontend; exporter hiện hành được nhìn thấy có nhiều điểm cần đối chiếu (IDs/references và định dạng component) trước khi khẳng định gói import tương thích.
- Không thấy `samples/` trong repo; bộ test chính thức cho `backend/app` và test frontend chưa xác minh được.

### Suy đoán / cần xác minh

- `backend/code_cu/` có vẻ là mã cũ vì tên thư mục và cấu trúc song song; chưa có bằng chứng rằng không có script/deploy nào đang chạy nó.
- Mô hình component chính xác của `invideoquiz_v2`, tên XBlock cần đăng ký, cấu trúc timemap và schema XML phụ thuộc phiên bản/config Open edX của daotao.ai; phải lấy gói mẫu đã import thành công hoặc tài liệu được giảng viên xác nhận.
- Không thể xác định từ repo liệu metadata “tag” có yêu cầu dùng cho lọc thư viện, phân loại đề hay mục đích nghiệp vụ nào khác; điều này ảnh hưởng lựa chọn UX/tag convention.
- Chưa chạy app/test trong quá trình khảo sát; các lệnh chạy là theo manifest/README, chưa xác nhận trên môi trường hiện tại.

## Câu hỏi cần hỏi giảng viên (tối đa 5)

1. Có thể cung cấp một gói export tối giản đã import thành công cho `invideoquiz_v2` trên daotao.ai, gồm XML và ví dụ timemap/timestamp không?
2. Khi gán tag riêng từng câu, tag cần nhập theo định dạng nào: marker trong text, bảng mapping, hay chỉnh trực tiếp từng câu sau parse? Tag `de0`… có quy ước cố định không?
3. Những loại unit mới cần hỗ trợ là gì, và mỗi loại cần thành phần/asset nào trong Open edX (HTML, file tải lên, link ngoài, SCORM…)?
4. Câu hỏi gắn vào video sẽ được tạo từ câu hỏi đã parse hay nhập riêng; timestamp dùng `MM:SS`, giây, hay một format khác và có yêu cầu xử lý nhiều câu cùng thời điểm không?
5. Quy trình bàn giao mong muốn là tải `.tar.gz` để import thủ công trong Studio, hay cần tích hợp API Studio/tự động hóa thao tác khác?
