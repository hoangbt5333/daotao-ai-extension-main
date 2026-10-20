"use client";

import React, { useState } from 'react';
import {
  Box, Typography, Paper, TextField, Button, CircularProgress, Stepper, Step, StepLabel,
  Chip, Stack, Alert, Divider, List, ListItem, ListItemText, IconButton, FormControl,
  InputLabel, Select, MenuItem, Switch, FormControlLabel
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import EditIcon from '@mui/icons-material/Edit';
import AddIcon from '@mui/icons-material/Add';

const steps = [
  "Thông tin đề thi",
  "Chọn câu hỏi",
  "Xem trước & Export"
];

interface ExamQuestion {
  id: string;
  question: string;
  type: string;
  choices?: string[];
  correct_answers: number[];
  tags: string[];
  source: 'manual' | 'library';
  library_id?: string;
}

interface ExamSection {
  title: string;
  questions: ExamQuestion[];
  time_limit?: number; // minutes
}

export default function ExamGeneratorTool() {
  const [activeStep, setActiveStep] = useState(0);
  const [examName, setExamName] = useState("");
  const [examDescription, setExamDescription] = useState("");
  const [totalTime, setTotalTime] = useState(90); // minutes
  const [isTimed, setIsTimed] = useState(true);
  const [sections, setSections] = useState<ExamSection[]>([
    { title: "Phần trắc nghiệm", questions: [] }
  ]);
  const [loading, setLoading] = useState(false);
  const [tarFile, setTarFile] = useState<string | null>(null);

  const BACKEND = "http://localhost:8000";

  // Step 1: Exam information
  const handleNextToQuestions = () => {
    if (examName.trim()) {
      setActiveStep(1);
    }
  };

  // Step 2: Add questions from library
  const handleAddQuestionsFromLibrary = async (sectionIndex: number, tags: string[], count: number) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("tags", JSON.stringify(tags));
      formData.append("count", count.toString());
      
      const res = await fetch(`${BACKEND}/api/v1/questions/from-library`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.questions) {
        const newQuestions: ExamQuestion[] = data.questions.map((q: any, index: number) => ({
          id: `lib_${Date.now()}_${index}`,
          question: q.question,
          type: q.type,
          choices: q.choices,
          correct_answers: q.correct_answers,
          tags: q.tags,
          source: 'library' as const,
          library_id: q.id
        }));

        const newSections = [...sections];
        newSections[sectionIndex].questions.push(...newQuestions);
        setSections(newSections);
      }
    } catch (e) {
      console.error("Error adding questions from library:", e);
      alert("Có lỗi khi lấy câu hỏi từ Library");
    }
    setLoading(false);
  };

  // Step 2: Add manual question
  const handleAddManualQuestion = (sectionIndex: number) => {
    const newQuestion: ExamQuestion = {
      id: `manual_${Date.now()}`,
      question: "Câu hỏi mới",
      type: "multiple_choice",
      choices: ["A", "B", "C", "D"],
      correct_answers: [0],
      tags: [],
      source: 'manual'
    };

    const newSections = [...sections];
    newSections[sectionIndex].questions.push(newQuestion);
    setSections(newSections);
  };

  // Step 3: Export exam - Full course
  const handleExportExam = async () => {
    if (sections.every(s => s.questions.length === 0)) {
      alert("Vui lòng thêm ít nhất một câu hỏi vào đề thi");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("exam_name", examName);
      formData.append("exam_description", examDescription);
      formData.append("total_time", totalTime.toString());
      formData.append("is_timed", isTimed.toString());
      formData.append("sections", JSON.stringify(sections));
      
      const res = await fetch(`${BACKEND}/api/v1/export/exam`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        alert("Có lỗi xảy ra khi export đề thi: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error exporting exam:", e);
      alert("Có lỗi xảy ra khi export đề thi");
    }
    setLoading(false);
  };

  // Export as subsection only
  const handleExportExamSubsection = async () => {
    if (sections.every(s => s.questions.length === 0)) {
      alert("Vui lòng thêm ít nhất một câu hỏi vào đề thi");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("exam_name", examName);
      formData.append("exam_description", examDescription);
      formData.append("total_time", totalTime.toString());
      formData.append("is_timed", isTimed.toString());
      formData.append("sections", JSON.stringify(sections));
      
      const res = await fetch(`${BACKEND}/api/v1/export/exam-subsection`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        alert("Có lỗi xảy ra khi export subsection: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error exporting exam subsection:", e);
      alert("Có lỗi xảy ra khi export subsection");
    }
    setLoading(false);
  };

  // Export questions as library
  const handleExportQuestionsLibrary = async () => {
    if (sections.every(s => s.questions.length === 0)) {
      alert("Vui lòng thêm ít nhất một câu hỏi vào đề thi");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("sections", JSON.stringify(sections));
      
      const res = await fetch(`${BACKEND}/api/v1/export/exam-questions-library`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        alert("Có lỗi xảy ra khi export library: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error exporting questions library:", e);
      alert("Có lỗi xảy ra khi export library");
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} mb={2}>
        Tạo Đề Thi Tự Động
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
          <Typography variant="h6" mb={2}>Bước 1: Thông tin đề thi</Typography>
          
          <TextField
            fullWidth
            label="Tên đề thi"
            value={examName}
            onChange={(e) => setExamName(e.target.value)}
            placeholder="Đề thi cuối kỳ môn Toán"
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="Mô tả đề thi"
            value={examDescription}
            onChange={(e) => setExamDescription(e.target.value)}
            placeholder="Đề thi gồm 2 phần: trắc nghiệm và tự luận"
            multiline
            rows={2}
            sx={{ mb: 2 }}
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={isTimed}
                onChange={(e) => setIsTimed(e.target.checked)}
              />
            }
            label="Đề thi có giới hạn thời gian"
            sx={{ mb: 2 }}
          />
          
          {isTimed && (
            <TextField
              fullWidth
              label="Thời gian làm bài (phút)"
              type="number"
              value={totalTime}
              onChange={(e) => setTotalTime(parseInt(e.target.value) || 90)}
              sx={{ mb: 2 }}
            />
          )}
          
          <Button
            variant="contained"
            onClick={handleNextToQuestions}
            disabled={!examName.trim()}
          >
            Tiếp theo
          </Button>
        </Paper>
      )}

      {activeStep === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 2: Thêm câu hỏi</Typography>
          
          {sections.map((section, sectionIndex) => (
            <Box key={sectionIndex} sx={{ mb: 3 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={1}>
                {section.title}
              </Typography>
              
              <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => handleAddManualQuestion(sectionIndex)}
                >
                  Thêm câu hỏi thủ công
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={<UploadIcon />}
                  onClick={() => handleAddQuestionsFromLibrary(sectionIndex, [], 5)}
                  disabled={loading}
                >
                  Lấy từ Library (5 câu)
                </Button>
              </Stack>
              
              <List>
                {section.questions.map((q, qIndex) => (
                  <ListItem key={q.id} divider>
                    <ListItemText
                      primary={q.question}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Loại:</strong> {q.type} | <strong>Nguồn:</strong> {q.source}
                          </Typography>
                          {q.choices && q.choices.length > 0 && (
                            <Typography variant="body2" color="text.secondary">
                              <strong>Đáp án:</strong> {q.correct_answers.map(i => q.choices![i]).join(', ')}
                            </Typography>
                          )}
                          <Stack direction="row" spacing={1} mt={1}>
                            {q.tags.map((tag, i) => (
                              <Chip key={i} label={tag} size="small" />
                            ))}
                          </Stack>
                        </Box>
                      }
                    />
                    <IconButton>
                      <EditIcon />
                    </IconButton>
                  </ListItem>
                ))}
              </List>
            </Box>
          ))}
          
          <Divider sx={{ my: 3 }} />
          
          <Typography variant="h6" mb={2}>Tùy chọn Export:</Typography>
          
          <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
            <Button
              variant="contained"
              onClick={handleExportExam}
              disabled={loading || sections.every(s => s.questions.length === 0)}
              startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {loading ? "Đang tạo..." : "Export Full Course"}
            </Button>
            
            <Button
              variant="outlined"
              onClick={handleExportExamSubsection}
              disabled={loading || sections.every(s => s.questions.length === 0)}
              startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {loading ? "Đang tạo..." : "Export Subsection"}
            </Button>
            
            <Button
              variant="outlined"
              onClick={handleExportQuestionsLibrary}
              disabled={loading || sections.every(s => s.questions.length === 0)}
              startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {loading ? "Đang tạo..." : "Export Library"}
            </Button>
          </Stack>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            <strong>Full Course:</strong> Tạo khóa học hoàn chỉnh với đề thi
            <br />
            <strong>Subsection:</strong> Chỉ tạo subsection để thêm vào course có sẵn
            <br />
            <strong>Library:</strong> Export câu hỏi dạng Library để import vào Library có sẵn
          </Typography>
        </Paper>
      )}

      {activeStep === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 3: Hoàn thành</Typography>
          {tarFile && (
            <>
              <Alert severity="success" sx={{ mb: 2 }}>
                Đã tạo đề thi thành công!
              </Alert>
              <a href={`http://localhost:8000${tarFile}`} download>
                <Button variant="contained" sx={{ mb: 2 }}>
                  Tải về {examName}.tar.gz
                </Button>
              </a>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                <strong>Hướng dẫn Import vào daotao.ai:</strong>
                {'\n'}1. Đăng nhập vào studio.daotao.ai
                {'\n'}2. Vào khóa học → Tools → Import
                {'\n'}3. Upload file .tar.gz vừa tải về
                {'\n'}4. Chọn chế độ Expand hoặc Replace
                {'\n'}5. Kiểm tra lại đề thi trong khóa học
                {'\n\n'}<strong>Lưu ý:</strong>
                {'\n'}- <strong>Full Course:</strong> Import vào course mới hoặc thay thế course hiện tại
                {'\n'}- <strong>Subsection:</strong> Import vào course có sẵn để thêm subsection mới
                {'\n'}- <strong>Library:</strong> Import vào Library có sẵn để thêm câu hỏi
              </Typography>
            </>
          )}
        </Paper>
      )}
    </Box>
  );
} 