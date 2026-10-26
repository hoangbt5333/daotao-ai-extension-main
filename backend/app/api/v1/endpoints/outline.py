"""
Outline import endpoints (Excel)
"""
from fastapi import APIRouter, UploadFile, File
from typing import Dict, Any, List, Tuple
from io import BytesIO, StringIO
from openpyxl import load_workbook
import csv
from app.models.schemas.responses import OutlineImportResponse


router = APIRouter()


REQUIRED_HEADERS = ["Chapter", "Lesson", "Unit"]
OPTIONAL_HEADERS = ["Slide", "Youtube", "Type", "Content"]
ALL_KNOWN_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS
EXPECTED_HEADERS = REQUIRED_HEADERS + ["Slide", "Youtube"]  # Backward compatibility


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
        raise ValueError(f"Thiếu cột bắt buộc: {', '.join(missing)}")
    return {"row": header_row, **idx}


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
                return OutlineImportResponse(success=False, outline={"outline": []}, rows=[], warnings=[], message=f"Thiếu cột bắt buộc: {', '.join(missing)}")
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


