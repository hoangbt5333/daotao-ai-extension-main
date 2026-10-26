import React, { useState } from "react";
import { Box, Button, Typography, TextField, CircularProgress, Paper, Stepper, Step, StepLabel, Snackbar, Alert } from "@mui/material";
import Table from "@mui/material/Table";
import TableHead from "@mui/material/TableHead";
import TableBody from "@mui/material/TableBody";
import TableRow from "@mui/material/TableRow";
import TableCell from "@mui/material/TableCell";
import EditableOutlineTree, { OutlineData } from "./EditableOutlineTree";
import FolderIcon from '@mui/icons-material/Folder';
import UploadIcon from '@mui/icons-material/Upload';

const steps = [
  "Nhập outline",
  "Chuyển đổi sang Open edX",
  "Đóng gói & Hướng dẫn Import"
];

export default function CourseGeneratorTool() {
  const [activeStep, setActiveStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState("");
  const [outline, setOutline] = useState<OutlineData>({ outline: [] });
  const [questions, setQuestions] = useState<any[]>([]);
  const [tarFile, setTarFile] = useState<string | null>(null);
  const [conversionLog, setConversionLog] = useState<string>("");
  const [packagingLog, setPackagingLog] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{open: boolean, message: string, severity: 'success'|'error'}>({open: false, message: '', severity: 'success'});
  const [exportFilename, setExportFilename] = useState<string>("course_export");
  const [pdfFiles, setPdfFiles] = useState<File[]>([]);
  const [mappingStatus, setMappingStatus] = useState<string>("");
  const [pastedText, setPastedText] = useState("");
  const [customPrompt, setCustomPrompt] = useState("");
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [excelRows, setExcelRows] = useState<any[]>([]);
  const [excelWarnings, setExcelWarnings] = useState<string[]>([]);
  const [excelOutlinePreview, setExcelOutlinePreview] = useState<OutlineData | null>(null);

  const BACKEND = "http://localhost:8000";

  // Step 1: Import outline (Excel/CSV)
  const handleExcelPreview = async () => {
    if (!excelFile) {
      setSnackbar({open: true, message: "Vui lòng chọn file Excel .xlsx", severity: 'error'});
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", excelFile);
      const res = await fetch(`${BACKEND}/api/v1/outline/import-excel`, { method: "POST", body: formData });
      const raw = await res.text();
      let data: any;
      try {
        data = JSON.parse(raw);
      } catch (e) {
        console.error("Import response is not valid JSON:", raw);
        throw new Error("INVALID_JSON_RESPONSE");
      }
      if (res.ok && data.success) {
        setExcelRows(data.rows || []);
        setExcelWarnings(data.warnings || []);
        const out = data.outline?.outline ? data.outline : { outline: data.outline || [] };
        setExcelOutlinePreview(out);
        setSnackbar({open: true, message: "Đã tạo preview từ Excel", severity: 'success'});
      } else {
        setSnackbar({open: true, message: (data && data.message) || `Import Excel/CSV thất bại (HTTP ${res.status})`, severity: 'error'});
      }
    } catch (e) {
      setSnackbar({open: true, message: "Lỗi kết nối hoặc phản hồi không hợp lệ khi import Excel/CSV", severity: 'error'});
    }
    setLoading(false);
  };

  const applyExcelOutline = () => {
    if (excelOutlinePreview) {
      setOutline(excelOutlinePreview);
      setSnackbar({open: true, message: "Đã áp dụng outline từ Excel", severity: 'success'});
    }
  };
  // removed legacy text/LLM handlers

  // Handle folder upload for PDF and Audio files
  const handleFolderUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    const assetFiles = files.filter(file => {
      const name = file.name.toLowerCase();
      return name.endsWith('.pdf') || name.endsWith('.mp3') || file.type === 'application/pdf' || file.type.startsWith('audio/');
    });
    setPdfFiles(assetFiles);
    setMappingStatus(`Đã chọn ${assetFiles.length} file (PDF/Audio)`);
  };

  // Auto-map PDF files to outline
  const handleAutoMapPdfs = async () => {
    if (pdfFiles.length === 0 || outline.outline.length === 0) {
      setSnackbar({open: true, message: "Vui lòng upload PDF files và tạo outline trước!", severity: 'error'});
      return;
    }

    setLoading(true);
    setMappingStatus("Đang phân tích và mapping PDF files...");

    try {
      const formData = new FormData();
      pdfFiles.forEach((file, index) => {
        formData.append(`files`, file);
      });
      formData.append("outline", JSON.stringify(outline));

      console.log("Sending outline to backend:", outline);

      const res = await fetch(`${BACKEND}/api/v1/mapping/pdfs`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      
      console.log("Backend response:", data);
      
      if (data.success) {
        console.log("Mapped outline received:", data.mapped_outline);
        setOutline(data.mapped_outline);
        setMappingStatus(`Đã mapping thành công ${data.mapped_count} file PDF vào outline`);
        setSnackbar({open: true, message: "Mapping PDF files thành công!", severity: 'success'});
      } else {
        setMappingStatus("Lỗi khi mapping PDF files");
        setSnackbar({open: true, message: "Mapping thất bại: " + data.message, severity: 'error'});
      }
    } catch (error) {
      console.error("Mapping error:", error);
      setMappingStatus("Lỗi kết nối khi mapping PDF files");
      setSnackbar({open: true, message: "Lỗi kết nối khi mapping!", severity: 'error'});
    }

    setLoading(false);
  };

  // Step 2: Conversion
  const handleConvert = async () => {
    if (!outline || outline.outline.length === 0) return;
    setLoading(true);
    setConversionLog("");
    setPackagingLog("");
    setTarFile(null);
    try {
      const formData = new FormData();
      // Gửi các file PDF đã chọn
      pdfFiles.forEach((file) => {
        formData.append("files", file);
      });
      formData.append("outline", JSON.stringify(outline));
      formData.append("questions", JSON.stringify(questions));
      const res = await fetch(`${BACKEND}/api/v1/export/?filename=${encodeURIComponent(exportFilename)}`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        setTarFile(data.tar_file);
        setConversionLog("Đã tạo file XML và cấu trúc thư mục thành công.\n" + (data.tar_file ? `Đã sẵn sàng đóng gói: ${data.tar_file}` : ""));
        setActiveStep(2);
        setSnackbar({open: true, message: "Chuyển đổi thành công!", severity: 'success'});
      } else {
        setConversionLog("Lỗi khi chuyển đổi sang Open edX.");
        setSnackbar({open: true, message: "Chuyển đổi thất bại: " + data.message, severity: 'error'});
      }
    } catch (e) {
      setConversionLog("Lỗi khi chuyển đổi sang Open edX.");
      setSnackbar({open: true, message: "Chuyển đổi thất bại!", severity: 'error'});
    }
    setLoading(false);
  };

  // Step 3: Packaging (log hiển thị ở conversionLog, packagingLog)
  // (Ở đây file .tar.gz đã được tạo ở bước conversion, chỉ cần tải về và hướng dẫn)

  // Stepper navigation
  const handleNext = () => setActiveStep((prev) => prev + 1);
  const handleBack = () => setActiveStep((prev) => prev - 1);
  const handleReset = () => {
    setActiveStep(0);
    setFile(null);
    setText("");
    setOutline({ outline: [] });
    setQuestions([]);
    setTarFile(null);
    setConversionLog("");
    setPackagingLog("");
    setExportFilename("course_export");
    setPdfFiles([]);
    setMappingStatus("");
    setPastedText("");
    setCustomPrompt("");
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} mb={2}>Tạo khóa học từ tài liệu</Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {activeStep === 0 && (
        <>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" mb={2}>1. Import outline từ Excel/CSV</Typography>
            <input
              type="file"
              accept=".xlsx,.csv"
              onChange={e => setExcelFile(e.target.files?.[0] || null)}
              style={{ marginRight: 12 }}
            />
            <Button variant="outlined" onClick={handleExcelPreview} disabled={loading || !excelFile}>Xem preview</Button>

            <Box sx={{ mt: 2 }}>
              <Alert severity="info">
                <Typography variant="subtitle2" fontWeight={700} mb={1}>Quy ước/Quy định định dạng Excel/CSV</Typography>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  <li><b>Header bắt buộc</b>: Chapter, Lesson, Unit, Slide, Youtube (đúng chính tả, phân biệt hoa thường).</li>
                  <li><b>Excel .xlsx</b>: Hỗ trợ merged cells. Hệ thống sẽ <i>expand</i> vùng merge (lấy giá trị ô góc trên‑trái). Khuyến nghị không dùng merge để ổn định tối đa.</li>
                  <li><b>CSV</b>: Lưu với mã hóa UTF‑8 (khuyến nghị UTF‑8 with BOM). Header phải đúng như trên.</li>
                  <li><b>Tạo Unit</b>:
                    <ul style={{ margin: 0, paddingLeft: 18 }}>
                      <li>Có <i>Youtube</i> và <i>Slide</i> → type = "video_pdf"; dùng <code>video_url</code> và <code>pdf_file</code>.</li>
                      <li>Chỉ <i>Youtube</i> → type = "video"; dùng <code>video_url</code>.</li>
                      <li>Chỉ <i>Slide</i> → type = "pdf"; dùng <code>file</code> (tên file).</li>
                      <li>Không có cả Youtube lẫn Slide → bỏ qua, không tạo unit.</li>
                    </ul>
                  </li>
                  <li><b>Gộp unit</b>: Các dòng trùng bộ <i>Chapter + Lesson + Unit</i> sẽ được hợp nhất vào 1 unit (ví dụ dòng 1 có YouTube, dòng 2 có Slide).</li>
                  <li><b>Slide</b>: Điền <u>tên file PDF</u> (ví dụ: Bai1_1.pdf). Sau đó upload các PDF trùng tên ở bước kế tiếp để mapping tự động.</li>
                  <li><b>Thiếu Lesson</b>: Tự động dùng "General" và hiển thị cảnh báo trong phần preview. <b>Chapter trống</b> sẽ lấy theo dòng gần nhất bên trên.</li>
                  <li><b>Youtube</b>: Nên dùng liên kết YouTube dạng chuẩn (watch?v=ID, youtu.be/ID, hoặc embed/ID). Hệ thống sẽ tự trích <i>VIDEO_ID</i> để tương thích Open edX.</li>
                </ul>
              </Alert>
            </Box>
            {excelWarnings.length > 0 && (
              <Alert severity="warning" sx={{ mt: 2 }}>
                {excelWarnings.map((w, i) => <div key={i}>{w}</div>)}
              </Alert>
            )}
            {excelRows.length > 0 && (
              <Box sx={{ mt: 2, maxHeight: 260, overflow: 'auto' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Chapter</TableCell>
                      <TableCell>Lesson</TableCell>
                      <TableCell>Unit</TableCell>
                      <TableCell>Slide</TableCell>
                      <TableCell>Youtube</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {excelRows.map((r, idx) => (
                      <TableRow key={idx}>
                        <TableCell>{r.Chapter}</TableCell>
                        <TableCell>{r.Lesson}</TableCell>
                        <TableCell>{r.Unit}</TableCell>
                        <TableCell>{r.Slide}</TableCell>
                        <TableCell>{r.Youtube}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            )}
            {excelOutlinePreview && (
              <Box sx={{ mt: 2 }}>
                <EditableOutlineTree outlineData={excelOutlinePreview} onChange={setExcelOutlinePreview as any} />
                <Button variant="contained" onClick={applyExcelOutline} sx={{ mt: 2 }}>
                  Dùng outline này
                </Button>
              </Box>
            )}
          </Paper>

          {/* Removed text/LLM upload flow; only Excel/CSV import remains */}

          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h6" mb={2}>2. Upload folder PDF slides / Audio (tùy chọn)</Typography>
            <Typography variant="body2" color="text.secondary" mb={2}>
              Upload folder chứa các file PDF slides hoặc file audio MP3. Hệ thống sẽ tự động phân tích và đưa vào gói tài nguyên.
            </Typography>
            <input
              type="file"
              multiple
              accept=".pdf,.mp3,audio/*"
              onChange={handleFolderUpload}
              style={{ display: 'none' }}
              id="pdf-folder-upload"
            />
            <label htmlFor="pdf-folder-upload">
              <Button
                variant="outlined"
                component="span"
                startIcon={<FolderIcon />}
                sx={{ mr: 2 }}
              >
                Chọn files PDF / Audio
              </Button>
            </label>
            {pdfFiles.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="primary">
                  {mappingStatus || `Đã chọn ${pdfFiles.length} file (PDF/Audio)`}
                </Typography>
                <Box sx={{ mt: 1, maxHeight: 200, overflow: 'auto' }}>
                  {pdfFiles.map((file, index) => (
                    <Typography key={index} variant="caption" display="block">
                      • {file.name}
                    </Typography>
                  ))}
                </Box>
              </Box>
            )}
          </Paper>

          {loading && <CircularProgress sx={{ mb: 2 }} />}
          
          {/* Removed text-based outline section */}

          {outline && outline.outline.length > 0 && (
            <>
              <EditableOutlineTree outlineData={outline} onChange={setOutline} />
              
              {pdfFiles.length > 0 && (
                <Paper sx={{ p: 2, mb: 3 }}>
                  <Typography variant="h6" mb={2}>3. Tự động mapping PDF slides</Typography>
                  <Button 
                    onClick={handleAutoMapPdfs} 
                    variant="contained" 
                    disabled={loading}
                    startIcon={<UploadIcon />}
                  >
                    Tự động mapping PDF vào outline
                  </Button>
                  {mappingStatus && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      {mappingStatus}
                    </Typography>
                  )}
                </Paper>
              )}
            </>
          )}

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
            <Button onClick={handleNext} variant="contained" disabled={!outline || outline.outline.length === 0}>Tiếp tục</Button>
          </Box>
        </>
      )}
      
      {activeStep === 1 && (
        <>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={2}>Chuyển đổi sang định dạng Open edX</Typography>
            <TextField
              label="Tên file xuất ra (.tar.gz)"
              value={exportFilename}
              onChange={e => setExportFilename(e.target.value.replace(/[^a-zA-Z0-9-_\.]/g, ""))}
              size="small"
              sx={{ mb: 2, width: 300 }}
              helperText="Chỉ dùng chữ, số, dấu gạch ngang, gạch dưới, chấm. Không cần .tar.gz"
            />
            <Button onClick={handleConvert} variant="contained" disabled={!outline || outline.outline.length === 0 || loading} sx={{ mb: 2, ml: 2 }}>
              Chuyển đổi & Đóng gói
            </Button>
            {loading && <CircularProgress sx={{ ml: 2 }} />}
            <Typography variant="body2" sx={{ mt: 2, whiteSpace: 'pre-line' }}>{conversionLog}</Typography>
          </Paper>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
            <Button onClick={handleBack}>Quay lại</Button>
            <Button onClick={handleNext} variant="contained" disabled={!tarFile}>Tiếp tục</Button>
          </Box>
        </>
      )}
      
      {activeStep === 2 && (
        <>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="subtitle1" fontWeight={600} mb={2}>Đóng gói & Hướng dẫn Import</Typography>
            {tarFile ? (
              <>
                <Typography>File .tar.gz đã sẵn sàng:</Typography>
                <a href={`http://localhost:8000${tarFile}`} download>
                  <Button variant="contained" sx={{ mt: 1 }}>Tải về {exportFilename}.tar.gz</Button>
                </a>
                <Typography variant="body2" sx={{ mt: 2, whiteSpace: 'pre-line' }}>{conversionLog}</Typography>
                <Box sx={{ mt: 3 }}>
                  <Typography variant="h6">Hướng dẫn Import vào studio.daotao.ai</Typography>
                  <ol>
                    <li>Đăng nhập vào <b>studio.daotao.ai</b> với tài khoản giảng viên.</li>
                    <li>Vào khóa học bạn muốn thêm outline.</li>
                    <li>Chọn menu <b>Tools → Import</b>.</li>
                    <li>Tải lên file <b>.tar.gz</b> vừa tải về.</li>
                    <li>Chờ hệ thống xử lý và kiểm tra lại outline trên web.</li>
                  </ol>
                </Box>
              </>
            ) : (
              <Typography color="error">Chưa có file .tar.gz. Hãy thực hiện chuyển đổi ở bước trước.</Typography>
            )}
          </Paper>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 2 }}>
            <Button onClick={handleBack}>Quay lại</Button>
            <Button onClick={handleReset}>Làm lại từ đầu</Button>
          </Box>
        </>
      )}
      
      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={() => setSnackbar({...snackbar, open: false})}>
        <Alert onClose={() => setSnackbar({...snackbar, open: false})} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
} 