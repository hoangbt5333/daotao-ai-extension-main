"""
Outline import endpoints (Excel)
"""
from fastapi import APIRouter, UploadFile, File, Response
from typing import Dict, Any, List, Tuple
from io import BytesIO, StringIO
from openpyxl import Workbook, load_workbook
import csv
from app.models.schemas.responses import OutlineImportResponse
from app.config.settings import get_settings


router = APIRouter()


REQUIRED_HEADERS = ["Chapter", "Lesson", "Unit"]
OPTIONAL_HEADERS = ["Slide", "Youtube", "Type", "Content"]
ALL_KNOWN_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS
EXPECTED_HEADERS = REQUIRED_HEADERS + ["Slide", "Youtube"]  # Backward compatibility
TEMPLATE_HEADERS = ["Chapter", "Lesson", "Unit", "Type", "Content", "Slide", "Youtube"]

SUPPORTED_UNIT_TYPES = ["video", "pdf", "audio", "video_pdf", "embed", "text"]
TYPE_ALIASES = {
    "raw_html": "embed",
    "html_raw": "embed",
    "iframe": "embed",
    "html": "text",
}


def _header_index(sheet) -> Dict[str, int]:
    header_row = None
    for r in range(1, sheet.max_row + 1):
        vals = [str(sheet.cell(row=r, column=c).value or "").strip() for c in range(1, sheet.max_column + 1)]
        if any(vals):
            header_row = r
            break
    if not header_row:
        raise ValueError("Không tìm thấy header")

    idx: Dict[str, int] = {}
    for c in range(1, sheet.max_column + 1):
        v = str(sheet.cell(row=header_row, column=c).value or "").strip()
        if v in ALL_KNOWN_HEADERS:
            idx[v] = c
    missing = [h for h in REQUIRED_HEADERS if h not in idx]
    if missing:
        raise ValueError(f"Thiếu cột bắt buộc: {', '.join(missing)}. Vui lòng xem file mẫu để kiểm tra danh sách cột chuẩn.")
    return {"row": header_row, **idx}


def _validate_type(tp: str, row_idx: int) -> None:
    """Validate that unit type is in SUPPORTED_UNIT_TYPES or TYPE_ALIASES."""
    if tp:
        tp_norm = tp.lower()
        if tp_norm not in SUPPORTED_UNIT_TYPES and tp_norm not in TYPE_ALIASES:
            raise ValueError(
                f"Hàng {row_idx}: Giá trị Type '{tp}' không hợp lệ. "
                f"Các Type được hỗ trợ: {', '.join(SUPPORTED_UNIT_TYPES)}. "
                f"Vui lòng xem file mẫu để biết định dạng chuẩn."
            )


def _merged_top_left_map(sheet) -> Dict[Tuple[int, int], Tuple[int, int]]:
    m: Dict[Tuple[int, int], Tuple[int, int]] = {}
    for rng in sheet.merged_cells.ranges:
        r1, c1, r2, c2 = rng.min_row, rng.min_col, rng.max_row, rng.max_col
        top_left = (r1, c1)
        for r in range(r1, r2 + 1):
            for c in range(c1, c2 + 1):
                m[(r, c)] = top_left
    return m


def _get_cell_value(sheet, r: int, c: int, merged_map: Dict[Tuple[int, int], Tuple[int, int]]):
    val = sheet.cell(row=r, column=c).value
    if val not in [None, ""]:
        return str(val).strip()
    if (r, c) in merged_map:
        tr, tc = merged_map[(r, c)]
        return str(sheet.cell(row=tr, column=tc).value or "").strip()
    return ""


def _normalize_rows(sheet) -> (List[Dict[str, str]], List[str]):
    idx = _header_index(sheet)
    merged_map = _merged_top_left_map(sheet)
    rows: List[Dict[str, str]] = []
    warnings: List[str] = []
    last_chapter = ""

    for r in range(idx["row"] + 1, sheet.max_row + 1):
        ch = _get_cell_value(sheet, r, idx["Chapter"], merged_map).strip()
        le = _get_cell_value(sheet, r, idx["Lesson"], merged_map).strip()
        un = _get_cell_value(sheet, r, idx["Unit"], merged_map).strip()
        sl = _get_cell_value(sheet, r, idx["Slide"], merged_map).strip() if "Slide" in idx else ""
        yt = _get_cell_value(sheet, r, idx["Youtube"], merged_map).strip() if "Youtube" in idx else ""
        tp = _get_cell_value(sheet, r, idx["Type"], merged_map).strip() if "Type" in idx else ""
        ct = _get_cell_value(sheet, r, idx["Content"], merged_map).strip() if "Content" in idx else ""

        if tp:
            _validate_type(tp, r)

        if not ch:
            ch = last_chapter
        else:
            last_chapter = ch

        if not le:
            le = "General"
            warnings.append(f"Hàng {r}: Thiếu Lesson → dùng mặc định 'General'")

        unit_title = un or (ct or sl or yt or "").split("/")[-1] or "Unit"

        rows.append({
            "Chapter": ch,
            "Lesson": le,
            "Unit": unit_title,
            "UnitRaw": un,
            "Slide": sl,
            "Youtube": yt,
            "Type": tp,
            "Content": ct
        })
    return rows, warnings


def _build_outline(rows: List[Dict[str, str]]) -> Dict[str, Any]:
    chapters: List[Dict[str, Any]] = []
    index_c: Dict[str, int] = {}
    by_key: Dict[Tuple[str, str, str], Dict[str, Any]] = {}

    for row in rows:
        ch = row["Chapter"].strip()
        le = row["Lesson"].strip()
        un = row["Unit"].strip()
        un_raw = (row.get("UnitRaw") or "").strip()
        sl = (row.get("Slide") or "").strip()
        yt = (row.get("Youtube") or "").strip()
        tp = (row.get("Type") or "").strip()
        ct = (row.get("Content") or "").strip()

        # If no media provided, create an empty unit only when user specified a Unit name in sheet
        if not sl and not yt and not tp and not ct:
            if not un_raw:
                # No explicit unit name -> skip
                continue

        if ch not in index_c:
            chapters.append({"title": ch or "Chương", "subsections": []})
            index_c[ch] = len(chapters) - 1

        cidx = index_c[ch]
        subs = chapters[cidx]["subsections"]

        lidx = None
        for i, s in enumerate(subs):
            if s["title"] == le:
                lidx = i
                break
        if lidx is None:
            subs.append({"title": le, "units": []})
            lidx = len(subs) - 1

        key = (ch, le, un)
        u = by_key.get(key)
        if not u:
            u = {"title": un}
            by_key[key] = u
            subs[lidx]["units"].append(u)

        # Logic ưu tiên: nếu có cột Type và ô Type không rỗng
        if tp:
            tp_norm = tp.lower()
            if tp_norm in TYPE_ALIASES:
                tp_norm = TYPE_ALIASES[tp_norm]
            if tp_norm == "audio":
                u["type"] = "audio"
                target_file = ct or sl
                u["audio_file"] = target_file
                u["file"] = target_file
            elif tp_norm == "pdf":
                u["type"] = "pdf"
                u["file"] = ct or sl
            elif tp_norm == "video":
                u["type"] = "video"
                u["video_url"] = ct or yt
            elif tp_norm == "video_pdf":
                u["type"] = "video_pdf"
                if yt:
                    u["video_url"] = yt
                elif ct and ("youtube" in ct.lower() or "youtu.be" in ct.lower() or ct.endswith(".mp4")):
                    u["video_url"] = ct
                if sl:
                    u["pdf_file"] = sl
                elif ct and ct.endswith(".pdf"):
                    u["pdf_file"] = ct
            elif tp_norm in ["embed", "raw_html", "html_raw", "iframe"]:
                u["type"] = "embed"
                u["embed_code"] = ct
            elif tp_norm in ["text", "html"]:
                u["type"] = "text"
                u["html_content"] = ct
            else:
                # Type tùy chỉnh khác
                u["type"] = tp_norm
                if ct:
                    u["content"] = ct
        else:
            # Fallback 100% logic cũ dựa trên Slide và Youtube
            if yt:
                u["video_url"] = yt
            if sl:
                if "video_url" in u:
                    u["pdf_file"] = sl
                else:
                    u["file"] = sl

            if "video_url" in u and ("pdf_file" in u or "file" in u):
                if "file" in u and "pdf_file" not in u:
                    u["pdf_file"] = u["file"]
                    del u["file"]
                u["type"] = "video_pdf"
            elif "video_url" in u:
                u["type"] = "video"
            elif "file" in u:
                u["type"] = "pdf"
            else:
                # Explicit empty unit: leave type unset (exporter defaults to text)
                pass

    return {"outline": chapters}


@router.post("/import-excel", response_model=OutlineImportResponse)
async def import_outline_excel(file: UploadFile = File(...)):
    try:
        fname = file.filename.lower()
        if fname.endswith(".xlsx"):
            content = await file.read()
            wb = load_workbook(BytesIO(content), data_only=True)
            sheet = wb["Outline"] if "Outline" in wb.sheetnames else wb.active
            rows, warnings = _normalize_rows(sheet)
            outline = _build_outline(rows)
        elif fname.endswith(".csv"):
            # Try UTF-8 with BOM first, then fallback to plain UTF-8
            raw_bytes = await file.read()
            try:
                raw_text = raw_bytes.decode('utf-8-sig')
            except UnicodeDecodeError:
                raw_text = raw_bytes.decode('utf-8', errors='replace')

            # Detect delimiter based on header line if Sniffer fails
            first_line = raw_text.splitlines()[0] if raw_text else ''
            delimiter = ';' if first_line.count(';') >= first_line.count(',') else ','

            reader = csv.DictReader(StringIO(raw_text), delimiter=delimiter)
            headers = [h.strip() for h in (reader.fieldnames or [])]
            # Validate required headers by inclusion, not strict order
            missing = [h for h in REQUIRED_HEADERS if h not in headers]
            if missing:
                return OutlineImportResponse(
                    success=False,
                    outline={"outline": []},
                    rows=[],
                    warnings=[],
                    message=f"Thiếu cột bắt buộc: {', '.join(missing)}. Vui lòng xem file mẫu để kiểm tra danh sách cột chuẩn."
                )
            rows: List[Dict[str, str]] = []
            warnings: List[str] = []
            last_chapter = ""
            for idx, r in enumerate(reader, start=2):
                ch = (r.get('Chapter') or '').strip()
                le = (r.get('Lesson') or '').strip()
                un = (r.get('Unit') or '').strip()
                sl = (r.get('Slide') or '').strip()
                yt = (r.get('Youtube') or '').strip()
                tp = (r.get('Type') or '').strip()
                ct = (r.get('Content') or '').strip()

                if tp:
                    try:
                        _validate_type(tp, idx)
                    except ValueError as e:
                        return OutlineImportResponse(
                            success=False,
                            outline={"outline": []},
                            rows=[],
                            warnings=[],
                            message=str(e)
                        )
                if not ch:
                    ch = last_chapter
                else:
                    last_chapter = ch
                if not le:
                    le = 'General'
                    warnings.append(f"Hàng {idx}: Thiếu Lesson → dùng mặc định 'General'")
                unit_title = un or (ct or sl or yt or "").split("/")[-1] or "Unit"
                rows.append({
                    "Chapter": ch,
                    "Lesson": le,
                    "Unit": unit_title,
                    "UnitRaw": un,
                    "Slide": sl,
                    "Youtube": yt,
                    "Type": tp,
                    "Content": ct
                })
            outline = _build_outline(rows)
        else:
            return OutlineImportResponse(success=False, outline={"outline": []}, rows=[], warnings=[], message="Chỉ hỗ trợ .xlsx hoặc .csv")

        return OutlineImportResponse(
            success=True,
            outline=outline,
            rows=rows,
            warnings=warnings,
            message="Đã nhập và dựng outline từ Excel"
        )
    except Exception as e:
        return OutlineImportResponse(success=False, outline={"outline": []}, rows=[], warnings=[], message=f"Import thất bại: {str(e)}")




def generate_outline_template_excel(settings=None) -> BytesIO:
    """Generate Excel outline template in memory with 2 sheets: 'Mẫu' and 'Hướng dẫn'."""
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    if settings is None:
        settings = get_settings()

    wb = Workbook()

    # ---------------------------------------------------------
    # Sheet 1: Mẫu
    # ---------------------------------------------------------
    ws_mau = wb.active
    ws_mau.title = "Mẫu"

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    ws_mau.append(TEMPLATE_HEADERS)
    for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
        cell = ws_mau.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # Dummy sample rows covering every supported type + auto-detect
    sample_data = [
        # 1. video
        [
            "Chương 1: Mở đầu",
            "Bài 1.1: Giới thiệu chung",
            "1.1.1 Video giới thiệu tổng quan",
            "video",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "",
            "",
        ],
        # 2. pdf
        [
            "Chương 1: Mở đầu",
            "Bài 1.1: Giới thiệu chung",
            "1.1.2 Tài liệu hướng dẫn học tập",
            "pdf",
            "huong_dan_hoc_tap.pdf",
            "",
            "",
        ],
        # 3. audio
        [
            "Chương 1: Mở đầu",
            "Bài 1.2: Luyện nghe và phát âm",
            "1.2.1 Bài nghe hội thoại mẫu",
            "audio",
            "audio_bai_01.mp3",
            "",
            "",
        ],
        # 4. video_pdf
        [
            "Chương 2: Kiến thức trọng tâm",
            "Bài 2.1: Lý thuyết căn bản",
            "2.1.1 Bài giảng lý thuyết kèm slide",
            "video_pdf",
            "",
            "slide_ly_thuyet_bai_2.pdf",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ],
        # 5. embed
        [
            "Chương 2: Kiến thức trọng tâm",
            "Bài 2.2: Tài liệu tương tác trực tuyến",
            "2.2.1 Tài liệu nhúng Google Drive",
            "embed",
            "https://drive.google.com/file/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs/preview",
            "",
            "",
        ],
        # 6. text
        [
            "Chương 3: Tổng kết & Ôn tập",
            "Bài 3.1: Hướng dẫn ôn tập",
            "3.1.1 Tóm tắt kiến thức cốt lõi",
            "text",
            "<p>Bài học dạng văn bản HTML tóm tắt các điểm quan trọng trong khóa học.</p>",
            "",
            "",
        ],
        # 7. Auto-detect row (Type trống, điền Slide)
        [
            "Chương 3: Tổng kết & Ôn tập",
            "Bài 3.1: Hướng dẫn ôn tập",
            "3.1.2 Tài liệu tham khảo bổ sung",
            "",
            "",
            "tai_lieu_tham_khao.pdf",
            "",
        ],
    ]

    for row in sample_data:
        ws_mau.append(row)

    for row in ws_mau.iter_rows(min_row=2, max_row=len(sample_data) + 1, min_col=1, max_col=len(TEMPLATE_HEADERS)):
        for cell in row:
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center")

    for col in ws_mau.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = col[0].column_letter
        ws_mau.column_dimensions[col_letter].width = max(max_len + 4, 15)

    # ---------------------------------------------------------
    # Sheet 2: Hướng dẫn
    # ---------------------------------------------------------
    ws_guide = wb.create_sheet(title="Hướng dẫn")
    guide_title_font = Font(name="Calibri", size=13, bold=True, color="1F497D")
    section_font = Font(name="Calibri", size=11, bold=True)
    normal_font = Font(name="Calibri", size=10)

    max_mb = settings.file.max_file_size // (1024 * 1024)

    guide_content = [
        ("HƯỚNG DẪN ĐỊNH DẠNG FILE OUTLINE KHÓA HỌC", guide_title_font),
        ("", normal_font),
        ("1. CÁC CỘT TRONG FILE OUTLINE (SHEET 'MẪU')", section_font),
        ("• Chapter (Bắt buộc): Tên chương / section. Nếu để trống, hệ thống sẽ lấy theo Chapter của dòng gần nhất phía trên.", normal_font),
        ("• Lesson (Bắt buộc): Tên bài học / subsection. Nếu để trống, hệ thống sẽ tự động gán vào 'General'.", normal_font),
        ("• Unit (Bắt buộc): Tên đơn vị học liệu / unit hiển thị trên cây khóa học.", normal_font),
        ("• Type (Tùy chọn): Xác định loại học liệu. Xem chi tiết các giá trị hợp lệ ở mục 2 bên dưới.", normal_font),
        ("• Content (Tùy chọn): Tên file tài nguyên (PDF/MP3), URL video/YouTube, URL/mã iframe nhúng, hoặc nội dung text/HTML.", normal_font),
        ("• Slide (Tùy chọn - Cột cũ): Tên file slide PDF. Hệ thống hỗ trợ 100% tương thích ngược khi không có cột Type.", normal_font),
        ("• Youtube (Tùy chọn - Cột cũ): URL video YouTube. Hệ thống hỗ trợ 100% tương thích ngược khi không có cột Type.", normal_font),
        ("", normal_font),
        ("2. CÁC LOẠI UNIT HỢP LỆ (CỘT 'TYPE')", section_font),
        ("• video: Video bài giảng. Cột Content điền link YouTube hoặc link video trực tiếp.", normal_font),
        ("• pdf: Tài liệu bài giảng PDF. Cột Content điền tên file PDF (ví dụ: bai1.pdf). Upload file ở mục 'Chọn files PDF / Audio'.", normal_font),
        ("• audio: Bài giảng âm thanh MP3. Cột Content điền tên file audio (ví dụ: bai1.mp3). Upload file ở mục 'Chọn files PDF / Audio'.", normal_font),
        ("• video_pdf: Bài giảng tích hợp video và slide PDF. Có thể khai báo đồng thời video và slide tương ứng.", normal_font),
        ("• embed: Nhúng tài liệu ngoài (Google Drive, OneDrive, SharePoint, Stream). Cột Content dán link chia sẻ hoặc mã <iframe>.", normal_font),
        ("• text: Bài giảng văn bản hoặc mã HTML trực tiếp trong cột Content.", normal_font),
        ("", normal_font),
        ("3. QUY TẮC ĐẶT TÊN FILE TÀI NGUYÊN (THEO TÀI LIỆU HƯỚNG DẪN MỤC 3.4.2)", section_font),
        ("• Tên file PDF và MP3 cần ngắn gọn, viết liền không dấu, không chứa khoảng trắng và không chứa ký tự đặc biệt.", normal_font),
        ("• Ví dụ đúng: bai_01_slide.pdf, audio_unit_02.mp3, chuong1_bai1.pdf.", normal_font),
        ("• Ví dụ sai: Bài 1 Slide.pdf, nghe bài 1.mp3, bai#1@test.pdf.", normal_font),
        ("", normal_font),
        ("4. GIỚI HẠN KÍCH THƯỚC VÀ ĐÓNG GÓI TÀI NGUYÊN", section_font),
        (f"• Giới hạn kích thước file tải lên tối đa là {max_mb}MB (theo cấu hình hệ thống).", normal_font),
        ("• Các file PDF và MP3 có tên trong outline cần được chọn tải lên ở mục '2. Upload folder PDF slides / Audio' trên giao diện.", normal_font),
        ("", normal_font),
        ("5. GHI CHÚ VỀ TÍNH TƯƠNG THÍCH NGƯỢC", section_font),
        ("• Các file Excel hoặc CSV cũ chỉ có 5 cột (Chapter, Lesson, Unit, Slide, Youtube) vẫn được hỗ trợ đầy đủ 100%.", normal_font),
        ("• Nếu cột Type để trống nhưng có điền Slide hoặc Youtube, hệ thống sẽ tự động nhận diện thành pdf, video hoặc video_pdf.", normal_font),
    ]

    for text, font in guide_content:
        ws_guide.append([text])
        cell = ws_guide.cell(row=ws_guide.max_row, column=1)
        cell.font = font

    ws_guide.column_dimensions["A"].width = 110

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@router.get("/template")
async def download_outline_template():
    """Download standard Excel template for course outline."""
    buffer = generate_outline_template_excel()
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="outline_template.xlsx"'
        }
    )
