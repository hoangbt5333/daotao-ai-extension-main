"use client";

import React, { useState } from 'react';
import {
  Box, Typography, Paper, TextField, Button, CircularProgress, Stepper, Step, StepLabel,
  Alert, List, ListItem, IconButton, FormControl,
  InputLabel, Select, MenuItem
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';

const steps = [
  "Thông tin video",
  "Thêm câu hỏi",
  "Xem trước & Export"
];

interface VideoQuestion {
  id: string;
  question: string;
  type: string;
  choices?: string[];
  correct_answers: number[];
  tags: string[];
  timestamp: string; // format: "MM:SS" or seconds
  seconds: number; // calculated from timestamp
}

// Single canonical place in frontend to extract YouTube 11-char ID
export function extractYouTubeId(url: string): string | null {
  if (!url || typeof url !== 'string') return null;
  const trimmed = url.trim();
  const lower = trimmed.toLowerCase();

  // Explicitly reject iframes, embed codes, and Google Drive (per docs 3.7)
  if (lower.includes('<iframe') || lower.includes('<video') || lower.includes('drive.google.com')) {
    return null;
  }

  // Support watch?v=, embed/, youtu.be/, shorts/
  const regExp = /(?:youtube\.com\/(?:watch\?.*v=|embed\/|v\/|shorts\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/;
  const match = trimmed.match(regExp);
  return match ? match[1] : null;
}

// Single canonical place in frontend to convert MM:SS or seconds string to integer seconds
export function parseTimestampToSeconds(ts: string): number | null {
  if (!ts) return null;
  const trimmed = ts.trim();

  // Pure integer seconds: e.g. "60", "90"
  if (/^\d+$/.test(trimmed)) {
    return parseInt(trimmed, 10);
  }

  // Format MM:SS: e.g. "01:30"
  const parts2 = trimmed.split(':');
  if (parts2.length === 2 && /^\d+$/.test(parts2[0]) && /^\d{2}$/.test(parts2[1])) {
    return parseInt(parts2[0], 10) * 60 + parseInt(parts2[1], 10);
  }

  // Format HH:MM:SS: e.g. "01:02:03"
  if (parts2.length === 3 && /^\d+$/.test(parts2[0]) && /^\d{2}$/.test(parts2[1]) && /^\d{2}$/.test(parts2[2])) {
    return parseInt(parts2[0], 10) * 3600 + parseInt(parts2[1], 10) * 60 + parseInt(parts2[2], 10);
  }

  return null;
}

export default function VideoQuizTool() {
  const [activeStep, setActiveStep] = useState(0);
  const [videoTitle, setVideoTitle] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoDescription, setVideoDescription] = useState("");
  const [questions, setQuestions] = useState<VideoQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tarFile, setTarFile] = useState<string | null>(null);

  const BACKEND = "http://localhost:8000";

  // Step 1: Video information
  const handleNextToQuestions = () => {
    setError(null);
    if (!videoTitle.trim()) {
      setError("Vui lòng nhập tiêu đề video.");
      return;
    }
    if (!videoUrl.trim()) {
      setError("Vui lòng nhập URL video YouTube.");
      return;
    }
    const ytId = extractYouTubeId(videoUrl);
    if (!ytId) {
      setError(
        "URL video không phải là YouTube hợp lệ (ID 11 ký tự). " +
        "In-Video Quiz chỉ hỗ trợ video YouTube (không áp dụng với iframe/raw HTML theo mục 3.7 tài liệu hướng dẫn)."
      );
      return;
    }
    setActiveStep(1);
  };

  // Step 2: Add question
  const handleAddQuestion = () => {
    setError(null);
    const newQuestion: VideoQuestion = {
      id: `q_${Date.now()}`,
      question: "Câu hỏi mới",
      type: "multiple_choice",
      choices: ["A", "B", "C", "D"],
      correct_answers: [0],
      tags: [],
      timestamp: "00:30",
      seconds: 30
    };
    setQuestions([...questions, newQuestion]);
  };

  // Update question
  const handleUpdateQuestion = (index: number, field: keyof VideoQuestion, value: any) => {
    setError(null);
    const newQuestions = [...questions];
    newQuestions[index] = { ...newQuestions[index], [field]: value };
    
    // Update seconds when timestamp changes
    if (field === 'timestamp') {
      const sec = parseTimestampToSeconds(value);
      if (sec !== null) {
        newQuestions[index].seconds = sec;
      }
    }
    
    setQuestions(newQuestions);
  };

  // Delete question
  const handleDeleteQuestion = (index: number) => {
    setError(null);
    setQuestions(questions.filter((_, i) => i !== index));
  };

  // Step 3: Export video quiz
  const handleExportVideoQuiz = async () => {
    setError(null);

    // Validate YouTube URL
    const ytId = extractYouTubeId(videoUrl);
    if (!ytId) {
      setError(
        "URL video không phải là YouTube hợp lệ (ID 11 ký tự). " +
        "In-Video Quiz chỉ hỗ trợ video YouTube (không áp dụng với iframe/raw HTML theo mục 3.7 tài liệu hướng dẫn)."
      );
      return;
    }

    if (questions.length === 0) {
      setError("Vui lòng thêm ít nhất một câu hỏi cho video.");
      return;
    }

    // Validate timestamps & check duplicates
    const seenSeconds = new Map<number, string>();
    const preparedQuestions: VideoQuestion[] = [];

    for (let i = 0; i < questions.length; i++) {
      const q = questions[i];
      if (!q.question.trim()) {
        setError(`Câu hỏi ${i + 1} chưa có nội dung.`);
        return;
      }

      const sec = parseTimestampToSeconds(q.timestamp);
      if (sec === null || sec < 0) {
        setError(
          `Câu hỏi ${i + 1} có thời điểm xuất hiện "${q.timestamp}" không hợp lệ. ` +
          "Vui lòng nhập định dạng MM:SS (ví dụ 01:30) hoặc số giây cố định (ví dụ 90)."
        );
        return;
      }

      if (seenSeconds.has(sec)) {
        const prevTs = seenSeconds.get(sec);
        setError(
          `Phát hiện mốc thời gian bị trùng lặp: ${q.timestamp} (${sec} giây, trùng với ${prevTs}). ` +
          "Mỗi mốc thời gian trong video chỉ được gắn một câu hỏi duy nhất."
        );
        return;
      }

      seenSeconds.set(sec, q.timestamp);
      preparedQuestions.push({
        ...q,
        seconds: sec
      });
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("video_title", videoTitle.trim());
      formData.append("video_url", videoUrl.trim());
      formData.append("video_description", videoDescription.trim());
      formData.append("questions", JSON.stringify(preparedQuestions));
      
      const res = await fetch(`${BACKEND}/api/v1/export/video-quiz`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        setError(data.message || "Có lỗi xảy ra khi export video quiz.");
      }
    } catch (e: any) {
      console.error("Error exporting video quiz:", e);
      setError("Không thể kết nối đến server backend hoặc server gặp lỗi: " + (e?.message || ""));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h5" fontWeight={700} mb={2}>
        Tạo Video Quiz Tương Tác
      </Typography>
      <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {activeStep === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 1: Thông tin video</Typography>
          
          <TextField
            fullWidth
            label="Tiêu đề video"
            value={videoTitle}
            onChange={(e) => {
              setVideoTitle(e.target.value);
              setError(null);
            }}
            placeholder="Bài giảng về Mạng máy tính"
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="URL Video YouTube"
            value={videoUrl}
            onChange={(e) => {
              setVideoUrl(e.target.value);
              setError(null);
            }}
            placeholder="https://www.youtube.com/watch?v=..."
            helperText="Chỉ hỗ trợ video YouTube (mục 3.7: không áp dụng với iframe/raw HTML)"
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="Mô tả video (tùy chọn)"
            value={videoDescription}
            onChange={(e) => setVideoDescription(e.target.value)}
            placeholder="Video mô tả ngắn gọn..."
            multiline
            rows={2}
            sx={{ mb: 2 }}
          />
          
          <Button
            variant="contained"
            onClick={handleNextToQuestions}
            disabled={!videoTitle.trim() || !videoUrl.trim()}
          >
            Tiếp theo
          </Button>
        </Paper>
      )}

      {activeStep === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 2: Thêm câu hỏi</Typography>
          
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddQuestion}
            sx={{ mb: 2 }}
          >
            Thêm câu hỏi
          </Button>
          
          <List>
            {questions.map((q, index) => (
              <ListItem key={q.id} divider sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <Box sx={{ width: '100%' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2" color="primary">
                      Câu hỏi {index + 1} - Thời điểm: {q.timestamp}
                    </Typography>
                    <IconButton 
                      size="small" 
                      color="error"
                      onClick={() => handleDeleteQuestion(index)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                  
                  <TextField
                    fullWidth
                    label="Thời điểm xuất hiện (MM:SS hoặc số giây)"
                    value={q.timestamp}
                    onChange={(e) => handleUpdateQuestion(index, 'timestamp', e.target.value)}
                    placeholder="01:30"
                    helperText="Ví dụ: 01:00 (phút 1) hoặc 60. Các câu hỏi không được trùng mốc thời gian."
                    sx={{ mb: 2 }}
                  />
                  
                  <TextField
                    fullWidth
                    label="Nội dung câu hỏi"
                    value={q.question}
                    onChange={(e) => handleUpdateQuestion(index, 'question', e.target.value)}
                    multiline
                    rows={2}
                    sx={{ mb: 2 }}
                  />
                  
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel>Loại câu hỏi</InputLabel>
                    <Select
                      value={q.type}
                      onChange={(e) => handleUpdateQuestion(index, 'type', e.target.value)}
                    >
                      <MenuItem value="multiple_choice">Trắc nghiệm một đáp án</MenuItem>
                      <MenuItem value="multiple_select">Chọn nhiều đáp án</MenuItem>
                    </Select>
                  </FormControl>
                  
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" mb={1}>
                      Lựa chọn:
                    </Typography>
                    {q.choices?.map((choice, choiceIndex) => (
                      <TextField
                        key={choiceIndex}
                        fullWidth
                        size="small"
                        value={choice}
                        onChange={(e) => {
                          const newChoices = [...(q.choices || [])];
                          newChoices[choiceIndex] = e.target.value;
                          handleUpdateQuestion(index, 'choices', newChoices);
                        }}
                        placeholder={`Lựa chọn ${String.fromCharCode(65 + choiceIndex)}`}
                        sx={{ mb: 1 }}
                      />
                    ))}
                  </Box>
                  
                  <TextField
                    fullWidth
                    label="Index đáp án đúng (bắt đầu từ 0)"
                    value={q.correct_answers.join(', ')}
                    onChange={(e) => {
                      const answers = e.target.value
                        .split(',')
                        .map(a => parseInt(a.trim(), 10))
                        .filter(a => !isNaN(a));
                      handleUpdateQuestion(index, 'correct_answers', answers);
                    }}
                    placeholder="0 hoặc 0, 1 cho nhiều đáp án"
                    helperText="Ví dụ: 0 ứng với lựa chọn A, 1 ứng với B"
                    sx={{ mb: 2 }}
                  />
                </Box>
              </ListItem>
            ))}
          </List>
          
          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => setActiveStep(0)}>
              Quay lại
            </Button>
            <Button
              variant="contained"
              onClick={handleExportVideoQuiz}
              disabled={loading || questions.length === 0}
              startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
            >
              {loading ? "Đang tạo video quiz..." : "Tạo video quiz"}
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
                Đã tạo video quiz thành công!
              </Alert>
              <a href={`${BACKEND}${tarFile}`} download>
                <Button variant="contained" sx={{ mb: 2 }}>
                  Tải về {videoTitle}.tar.gz
                </Button>
              </a>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-line' }}>
                <strong>Hướng dẫn Import vào daotao.ai:</strong>
                {'\n'}1. Đăng nhập vào studio.daotao.ai
                {'\n'}2. Vào khóa học → Tools → Import
                {'\n'}3. Upload file .tar.gz vừa tải về
                {'\n'}4. Chọn chế độ Expand hoặc Replace
                {'\n'}5. Kiểm tra lại video quiz trong khóa học
              </Typography>
              <Button sx={{ mt: 2 }} variant="outlined" onClick={() => setActiveStep(1)}>
                Chỉnh sửa lại câu hỏi
              </Button>
            </>
          )}
        </Paper>
      )}
    </Box>
  );
}
