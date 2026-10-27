// Nếu chưa cài: npm install @mui/x-date-pickers @date-io/dayjs dayjs
import React, { useState } from 'react';
import {
  Box, Typography, Paper, TextField, Button, CircularProgress, Stepper, Step, StepLabel,
  Chip, Stack, Alert, Divider, List, ListItem, ListItemText, IconButton, Collapse
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import EditIcon from '@mui/icons-material/Edit';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import AddIcon from '@mui/icons-material/Add';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs, { Dayjs } from 'dayjs';
import utc from 'dayjs/plugin/utc';
dayjs.extend(utc);
import PhotoCamera from '@mui/icons-material/PhotoCamera';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';

import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';

const steps = [
  "Upload/Paste câu hỏi",
  "Xử lý & Kiểm tra format",
  "Quản lý tags & Export"
];

interface Question {
  question: string;
  type: string;
  choices: string[];
  correct_answers: number[];
  tags: string[];
  topic?: string;
  is_valid?: boolean;
  errors?: string[];
  image_url?: string; // Added for image URL
}

export default function QuestionBankTool() {
  const [activeStep, setActiveStep] = useState(0);
  const [questionsText, setQuestionsText] = useState("");
  const [userTags, setUserTags] = useState<string[]>([]);
  const [tagsInput, setTagsInput] = useState<string>("");
  const [tagsExplanation, setTagsExplanation] = useState<string>("");
  const [processedQuestions, setProcessedQuestions] = useState<Question[]>([]);
  const [libraryName, setLibraryName] = useState("Question Bank");
  const [loading, setLoading] = useState(false);
  const [tarFile, setTarFile] = useState<string | null>(null);
  const [org, setOrg] = useState("SoDiTEC");
  const [libraryCode, setLibraryCode] = useState("2025-2");
  const [startTime, setStartTime] = useState<Dayjs | null>(dayjs('2030-01-01T00:00:00Z'));
  const [editIndex, setEditIndex] = useState<number | null>(null);
  const [editQuestion, setEditQuestion] = useState<Question | null>(null);
  const [editImage, setEditImage] = useState<File | null>(null);
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editTagInput, setEditTagInput] = useState<string>("");
  // parseMode: 'llm' | 'custom_single' | 'multiple_select'
  const [parseMode, setParseMode] = useState<'llm' | 'custom_single' | 'multiple_select'>('custom_single');
  const [userFormat, setUserFormat] = useState('');
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [exportQuestionType, setExportQuestionType] = useState<'multiple_choice' | 'multiple_select'>('multiple_choice');
  const [showGuide, setShowGuide] = useState(false);

  // Khi thay đổi parseMode, tự động sync exportQuestionType cho phù hợp
  const handleParseModeChange = (newMode: 'llm' | 'custom_single' | 'multiple_select') => {
    setParseMode(newMode);
    if (newMode === 'multiple_select') {
      setExportQuestionType('multiple_select');
    } else {
      // LLM hoặc custom_single đều mặc định export multiple_choice
      setExportQuestionType('multiple_choice');
    }
  };

  // Tạo bộ câu hỏi mới (làm sạch dữ liệu và về bước 1)
  const handleCreateNew = () => {
    setQuestionsText("");
    setProcessedQuestions([]);
    setTotalQuestions(0);
    setTarFile(null);
    setUserTags([]);
    setTagsInput("");
    setTagsExplanation("");
    setLibraryName("Question Bank");
    setEditIndex(null);
    setEditQuestion(null);
    setEditImage(null);
    setEditTags([]);
    setEditTagInput("");
    setActiveStep(0);
  };

  const BACKEND = "http://localhost:8000";

  // Step 1: Upload/Paste questions
  const handleProcessQuestions = async () => {
    if (!questionsText.trim()) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("questions_text", questionsText);
      formData.append("user_tags", JSON.stringify(userTags));
      formData.append("tags_explanation", tagsExplanation);
      // Gửi payload theo chế độ được chọn
      if (parseMode === 'llm') {
        // LLM: để AI phân tích, không gửi user_format
        formData.append("mode", "llm");
      } else if (parseMode === 'custom_single') {
        // Custom parser — một đáp án đúng: parse_questions_from_text()
        // hỗ trợ (x)/(!x)/( )/(!), de0/de1, @tag:
        formData.append("mode", "custom");
        // Không gửi user_format → backend dùng parse_questions_from_text()
      } else if (parseMode === 'multiple_select') {
        // Multiple Selection — nhiều đáp án đúng: parse_multiple_select_questions_from_text()
        formData.append("mode", "custom");
        formData.append("user_format", "multiple_select");
      }
      const res = await fetch(`${BACKEND}/api/v1/questions/process`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log("Response from process-questions:", data);
      if (data.success && data.questions) {
        const questionsArray = Array.isArray(data.questions) ? data.questions : [];
        setProcessedQuestions(questionsArray);
        setTotalQuestions(questionsArray.length);
        setActiveStep(1);
      } else {
        console.error("Invalid response format:", data);
        alert("Có lỗi xảy ra khi xử lý câu hỏi: " + data.message);
      }
    } catch (e) {
      console.error("Error processing questions:", e);
      alert("Có lỗi xảy ra khi xử lý câu hỏi");
    }
    setLoading(false);
  };

  // Step 2: Export Library
  const handleExportLibrary = async () => {
    if (!processedQuestions || processedQuestions.length === 0) {
      alert("Không có câu hỏi nào để export");
      return;
    }
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("questions", JSON.stringify({ questions: processedQuestions }));
      formData.append("library_name", libraryName);
      formData.append("org", org);
      formData.append("library_code", libraryCode);
      // Convert startTime to UTC ISO string with T và Z
      const startIso = startTime ? startTime.toDate().toISOString().replace('.000', '') : '2030-01-01T00:00:00Z';
      formData.append("start_time", startIso);
      formData.append("question_type", exportQuestionType); // <--- truyền loại export
      const res = await fetch(`${BACKEND}/api/v1/export/library`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      console.log("Export response:", data);
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        alert("Có lỗi xảy ra khi export Library: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error exporting library:", e);
      alert("Có lỗi xảy ra khi export Library");
    }
    setLoading(false);
  };

  const handleEdit = (q: Question, idx: number) => {
    setEditIndex(idx);
    setEditQuestion({ ...q });
    setEditTags(q.tags || []);
    setEditTagInput((q.tags || []).join(", "));
    setEditImage(null);
  };
  const handleEditSave = () => {
    if (editIndex === null || !editQuestion) return;
    // Đảm bảo correct_answers là mảng số
    const correctAnswers = Array.isArray(editQuestion.correct_answers)
      ? editQuestion.correct_answers.map(n => typeof n === 'string' ? parseInt(n) : n).filter(n => !isNaN(n))
      : [];
    const updated = [...processedQuestions];
    updated[editIndex] = {
      ...editQuestion,
      tags: editTags,
      image_url: editImage ? URL.createObjectURL(editImage) : editQuestion.image_url,
      correct_answers: correctAnswers,
    };
    setProcessedQuestions(updated);
    setTotalQuestions(updated.length);
    setEditIndex(null);
    setEditQuestion(null);
    setEditImage(null);
    setEditTags([]);
    setEditTagInput("");
  };
  const handleEditCancel = () => {
    setEditIndex(null);
    setEditQuestion(null);
    setEditImage(null);
    setEditTags([]);
    setEditTagInput("");
  };



  return (
    <Box>
      <Typography variant="h5" fontWeight={700} mb={2}>
        Ngân hàng câu hỏi - Tạo Library
      </Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
      {activeStep === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 1: Nhập câu hỏi</Typography>
          <RadioGroup
            row
            value={parseMode}
            onChange={e => handleParseModeChange(e.target.value as 'llm' | 'custom_single' | 'multiple_select')}
            sx={{ mb: 2 }}
          >
            <FormControlLabel value="custom_single" control={<Radio />} label="Custom parser — một đáp án đúng" />
            <FormControlLabel value="multiple_select" control={<Radio />} label="Multiple Selection — nhiều đáp án đúng" />
            <FormControlLabel value="llm" control={<Radio />} label="Để AI tự nhận diện (LLM)" />
          </RadioGroup>
          {parseMode !== 'llm' && (
            <Box sx={{ mb: 2 }}>
              <Button
                size="small"
                variant="outlined"
                startIcon={<HelpOutlineIcon fontSize="small" />}
                onClick={() => setShowGuide(!showGuide)}
                sx={{ textTransform: 'none', fontWeight: 600, borderRadius: 2 }}
              >
                {showGuide ? "Đóng hướng dẫn cú pháp" : "Xem hướng dẫn cú pháp"}
              </Button>
            </Box>
          )}

          <Collapse in={showGuide && parseMode !== 'llm'} sx={{ mb: showGuide && parseMode !== 'llm' ? 2 : 0 }}>
            {parseMode === 'custom_single' && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <strong>Hướng dẫn cú pháp — Một đáp án đúng (Open edX Standard):</strong><br/>
                <pre style={{ margin: '8px 0', fontFamily: 'monospace', fontSize: '0.85em', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`de0
Câu hỏi 1: Đáp án đúng ở dòng 3 (tất cả phương án đều được đảo ngẫu nhiên)?
(!) Phương án A (dòng đầu có dấu ! để kích hoạt xáo trộn đề thi)
( ) Phương án B (phương án sai)
(x) Phương án C (đáp án đúng)
(@) Phương án D (cố định ở cuối: Tất cả đều sai)

@tag: Chương 1, Tuần 1
Câu hỏi 2: Đáp án đúng ở ngay dòng đầu tiên?
(!x) Phương án A (vừa đúng vừa kích hoạt xáo trộn)
( ) Phương án B (sai)
( ) Phương án C (sai)`}
                </pre>
                <strong>Quy ước cú pháp:</strong><br/>
                • <strong>Dòng đầu tiên:</strong> Phải có <code>(!)</code> (nếu sai) hoặc <code>(!x)</code> (nếu đúng) để kích hoạt xáo trộn thứ tự đáp án khi thi.<br/>
                • <strong>Các dòng sau:</strong> Dùng <code>(x)</code> cho đáp án đúng bình thường, <code>( )</code> cho đáp án sai bình thường.<br/>
                • <strong>Cố định vị trí:</strong> Dùng <code>(@)</code> (hoặc <code>(@x)</code>) cho phương án không được xáo trộn (ví dụ câu *"Tất cả các phương án trên đều sai"*).<br/>
                • <strong>Gán nhãn:</strong> <code>de0</code>, <code>de1</code>… ở đầu block hoặc <code>@tag: tag1, tag2</code> ngay trước câu hỏi.
              </Alert>
            )}
            {parseMode === 'multiple_select' && (
              <Alert severity="info" sx={{ mb: 1 }}>
                <strong>Hướng dẫn cú pháp — Multiple Selection (nhiều đáp án đúng):</strong><br/>
                <pre style={{ margin: '8px 0', fontFamily: 'monospace', fontSize: '0.85em', background: '#f5f5f5', padding: '8px', borderRadius: '4px' }}>
{`de0
Câu hỏi có nhiều đáp án đúng?
[x] Đáp án đúng 1
[x] Đáp án đúng 2
[ ] Đáp án sai 1
[ ] Đáp án sai 2`}
                </pre>
                • Dùng <code>[x]</code> cho các đáp án đúng, <code>[ ]</code> cho các đáp án sai.<br/>
                • Có thể thêm <code>de0</code>, <code>de1</code>… hoặc <code>@tag: tag1, tag2</code> trước câu hỏi.
              </Alert>
            )}
          </Collapse>
          <TextField
            label="Nhập hoặc dán danh sách câu hỏi"
            multiline
            minRows={8}
            fullWidth
            value={questionsText}
            onChange={e => setQuestionsText(e.target.value)}
            sx={{ mb: 2 }}
          />
          {/* Tags: nhập theo dấu phẩy */}
          <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Tags:</Typography>
          <TextField
            fullWidth
            label="Tags (phân cách bằng dấu phẩy)"
            value={tagsInput}
            onChange={(e) => {
              setTagsInput(e.target.value);
              // Parse tags from comma-separated string
              const tags = e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
              setUserTags(tags);
            }}
            placeholder="Ví dụ: Module 3-1 bai 1, AI, Machine Learning"
            helperText="Nhập tags và phân cách bằng dấu phẩy (,)"
            sx={{ mb: 1 }}
          />
          {/* Hiển thị tags xem trước */}
          {userTags.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Tags đã nhập ({userTags.length}):
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {userTags.map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    size="small"
                    color="primary"
                    variant="outlined"
                    sx={{ mb: 1 }}
                  />
                ))}
              </Stack>
            </Box>
          )}
          <TextField
            label="Giải thích tags (nếu cần)"
            fullWidth
            value={tagsExplanation}
            onChange={e => setTagsExplanation(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Button
            variant="contained"
            onClick={handleProcessQuestions}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {loading ? "Đang xử lý..." : "Xử lý & Kiểm tra format"}
          </Button>
        </Paper>
      )}
      {activeStep === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 2: Quản lý & Export</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Tổng số câu hỏi đã quét được:</strong> {totalQuestions} câu hỏi
            </Typography>
          </Alert>
          <TextField
            fullWidth
            label="Tên Library"
            value={libraryName}
            onChange={(e) => setLibraryName(e.target.value)}
            sx={{ mb: 2 }}
          />
          <TextField
            fullWidth
            label="Tên tổ chức (org) trên hệ thống"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
            sx={{ mb: 2 }}
            helperText="Phải đúng với org của Library trên hệ thống daotao.ai"
          />
          <TextField
            fullWidth
            label="Mã thư viện (library code) trên hệ thống"
            value={libraryCode}
            onChange={(e) => setLibraryCode(e.target.value)}
            sx={{ mb: 2 }}
            helperText="Phải đúng với mã thư viện trên hệ thống daotao.ai (ví dụ: 2025-2)"
          />
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DatePicker
              label="Ngày bắt đầu hiệu lực (start time)"
              value={startTime}
              onChange={(newValue: Dayjs | null) => setStartTime(newValue)}
              sx={{ mb: 2, width: '100%' }}
              slotProps={{ textField: { fullWidth: true, helperText: 'Chọn ngày bắt đầu hiệu lực cho Library (UTC)', size: 'medium' } }}
            />
          </LocalizationProvider>
          <List>
            {processedQuestions && processedQuestions.length > 0 ? (
              processedQuestions.map((q, index) => (
                <ListItem key={index} divider alignItems="flex-start">
                  <ListItemText
                    primary={q.question || "Câu hỏi không có nội dung"}
                    secondary={
                      <Box>
                        {/* Question type and choices */}
                        <Typography variant="body2" color="text.secondary" mb={1}>
                          <strong>Loại:</strong> {q.type} | <strong>Đáp án:</strong> {q.correct_answers?.map(i => q.choices?.[i] || `Đáp án ${i}`).join(', ') || 'Không có'}
                        </Typography>
                        {/* Choices */}
                        {q.choices && q.choices.length > 0 && (
                          <Box mb={1}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Lựa chọn:</strong>
                            </Typography>
                            {q.choices.map((choice, i) => (
                              <Typography key={i} variant="body2" color="text.secondary" sx={{ ml: 2 }}>
                                {String.fromCharCode(65 + i)}. {choice}
                              </Typography>
                            ))}
                          </Box>
                        )}
                        {/* Tags */}
                        <Stack direction="row" spacing={1} mt={1} flexWrap="wrap" useFlexGap>
                          {(q.tags && q.tags.length > 0 ? q.tags : userTags).map((tag, i) => (
                            <Chip key={i} label={tag} size="small" color="primary" />
                          ))}
                        </Stack>
                        {/* Topic */}
                        {q.topic && (
                          <Typography variant="body2" color="text.secondary" mt={1}>
                            <strong>Chủ đề:</strong> {q.topic}
                          </Typography>
                        )}
                        {/* Ảnh */}
                        {q.image_url && (
                          <Box mt={1}>
                            <img src={q.image_url} alt="img" style={{ maxWidth: 200, maxHeight: 120 }} />
                          </Box>
                        )}
                      </Box>
                    }
                  />
                  <IconButton onClick={() => handleEdit(q, index)}>
                    <EditIcon />
                  </IconButton>
                </ListItem>
              ))
            ) : (
              <ListItem>
                <ListItemText
                  primary="Chưa có câu hỏi nào được xử lý"
                  secondary="Vui lòng quay lại bước 1 để nhập câu hỏi"
                />
              </ListItem>
            )}
          </List>
          {/* Dialog chỉnh sửa câu hỏi */}
          <Dialog open={editIndex !== null} onClose={handleEditCancel} maxWidth="sm" fullWidth>
            <DialogTitle>Chỉnh sửa câu hỏi</DialogTitle>
            <DialogContent>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="type-label">Loại câu hỏi</InputLabel>
                <Select
                  labelId="type-label"
                  value={editQuestion?.type || 'multiple_choice'}
                  label="Loại câu hỏi"
                  onChange={e => setEditQuestion(q => q ? { ...q, type: e.target.value as any, correct_answers: [] } : q)}
                >
                  <MenuItem value="multiple_choice">Trắc nghiệm 1 đáp án</MenuItem>
                  <MenuItem value="multiple_select">Trắc nghiệm nhiều đáp án</MenuItem>
                  <MenuItem value="text_input">Tự luận (text input)</MenuItem>
                  <MenuItem value="numerical">Tự luận số (numerical)</MenuItem>
                </Select>
              </FormControl>
              <TextField
                fullWidth
                multiline
                minRows={3}
                maxRows={8}
                label="Nội dung câu hỏi"
                value={editQuestion?.question || ''}
                onChange={e => setEditQuestion(q => q ? { ...q, question: e.target.value } : q)}
                sx={{ mb: 2 }}
              />
              {/* Đáp án: chỉ hiển thị nếu là multiple_choice hoặc multiple_select */}
              {(editQuestion?.type === 'multiple_choice' || editQuestion?.type === 'multiple_select') && (
                <>
                  <Typography variant="subtitle2" sx={{ mt: 1, mb: 1 }}>Các lựa chọn đáp án:</Typography>
                  {editQuestion?.choices?.map((choice, i) => (
                    <Box key={i} display="flex" alignItems="center" sx={{ mb: 1 }}>
                      <TextField
                        value={choice}
                        onChange={e => setEditQuestion(q => q ? { ...q, choices: q.choices.map((c, idx) => idx === i ? e.target.value : c) } : q)}
                        size="small"
                        sx={{ flex: 1, mr: 1 }}
                        label={`Đáp án ${String.fromCharCode(65 + i)}`}
                      />
                      {editQuestion?.type === 'multiple_select' ? (
                        <Checkbox
                          checked={editQuestion.correct_answers?.includes(i) || false}
                          onChange={e => setEditQuestion(q => q ? { ...q, correct_answers: e.target.checked ? [...(q.correct_answers || []), i] : (q.correct_answers || []).filter(idx => idx !== i) } : q)}
                          color="primary"
                        />
                      ) : (
                        <Radio
                          checked={editQuestion.correct_answers?.[0] === i}
                          onChange={() => setEditQuestion(q => q ? { ...q, correct_answers: [i] } : q)}
                          color="primary"
                        />
                      )}
                      <Button color="error" onClick={() => setEditQuestion(q => q ? { ...q, choices: q.choices.filter((_, idx) => idx !== i), correct_answers: (q.correct_answers || []).filter(idx => idx !== i) } : q)} size="small">Xóa</Button>
                    </Box>
                  ))}
                  <Button variant="outlined" onClick={() => setEditQuestion(q => q ? { ...q, choices: [...(q.choices || []), ''] } : q)} sx={{ mb: 2 }}>Thêm đáp án</Button>
                </>
              )}
                             {/* Tags: nhập theo dấu phẩy */}
               <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Tags:</Typography>
               <TextField
                 fullWidth
                 label="Tags (phân cách bằng dấu phẩy)"
                 value={editTagInput}
                 onChange={(e) => {
                   setEditTagInput(e.target.value);
                   // Parse tags from comma-separated string
                   const tags = e.target.value.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
                   setEditTags(tags);
                 }}
                 placeholder="Ví dụ: Module 3-1 bai 1, AI, Machine Learning"
                 helperText="Nhập tags và phân cách bằng dấu phẩy (,)"
                 sx={{ mb: 1 }}
               />
               {/* Hiển thị tags xem trước trong dialog */}
               {editTags.length > 0 && (
                 <Box sx={{ mb: 2 }}>
                   <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                     Tags đã nhập ({editTags.length}):
                   </Typography>
                   <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                     {editTags.map((tag, index) => (
                       <Chip
                         key={index}
                         label={tag}
                         size="small"
                         color="primary"
                         variant="outlined"
                         sx={{ mb: 1 }}
                       />
                     ))}
                   </Stack>
                 </Box>
               )}
              <Button
                variant="contained"
                component="label"
                startIcon={<PhotoCamera />}
                sx={{ mb: 2 }}
              >
                Thêm ảnh
                <input
                  type="file"
                  accept="image/*"
                  hidden
                  onChange={e => setEditImage(e.target.files?.[0] || null)}
                />
              </Button>
              {editImage && (
                <Typography variant="body2" color="text.secondary" mb={1}>
                  Đã chọn: {editImage.name}
                </Typography>
              )}
              {editQuestion?.image_url && !editImage && (
                <Box mt={1}>
                  <img src={editQuestion.image_url} alt="img" style={{ maxWidth: 200, maxHeight: 120 }} />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={handleEditCancel}>Hủy</Button>
              <Button onClick={handleEditSave} variant="contained">Lưu</Button>
            </DialogActions>
          </Dialog>
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Chọn loại export:</Typography>
            <RadioGroup
              row
              value={exportQuestionType}
              onChange={e => setExportQuestionType(e.target.value as 'multiple_choice' | 'multiple_select')}
            >
              <FormControlLabel value="multiple_choice" control={<Radio />} label="Multiple Choice (1 đáp án đúng)" />
              <FormControlLabel value="multiple_select" control={<Radio />} label="Multiple Selection (nhiều đáp án đúng)" />
            </RadioGroup>
          </Box>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={() => setActiveStep(0)}
              disabled={loading}
            >
              ← Quay lại Bước 1
            </Button>
            <Button
              variant="contained"
              onClick={handleExportLibrary}
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {loading ? "Đang export..." : "Export Library"}
            </Button>
          </Box>
        </Paper>
      )}
      {activeStep === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 3: Hoàn thành</Typography>
          {tarFile && (
            <>
              <Alert severity="success" sx={{ mb: 2 }}>
                Đã tạo Library thành công!
              </Alert>
              <a href={`http://localhost:8000${tarFile}`} download>
                <Button variant="contained" sx={{ mb: 2 }}>
                  Tải về {libraryName}.tar.gz
                </Button>
              </a>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                <strong>Hướng dẫn Import vào daotao.ai:</strong>
                {'\n'}1. Đăng nhập vào studio.daotao.ai
                {'\n'}2. Vào Libraries → Import
                {'\n'}3. Upload file .tar.gz vừa tải về
                {'\n'}4. Chọn chế độ Expand hoặc Replace
                {'\n'}5. Kiểm tra lại câu hỏi trong Library
              </Typography>
            </>
          )}
          <Box sx={{ mt: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
            <Button
              variant="outlined"
              onClick={() => setActiveStep(1)}
            >
              ← Quay lại Bước 2
            </Button>
            <Button
              variant="contained"
              color="primary"
              startIcon={<AddIcon />}
              onClick={handleCreateNew}
            >
              Tạo bộ câu hỏi mới
            </Button>
          </Box>
      </Paper>
      )}
    </Box>
  );
} 