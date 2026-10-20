"use client";

import React, { useState } from 'react';
import {
  Box, Typography, Paper, TextField, Button, CircularProgress, Stepper, Step, StepLabel,
  Chip, Stack, Alert, Divider, List, ListItem, ListItemText, IconButton, FormControl,
  InputLabel, Select, MenuItem
} from '@mui/material';
import UploadIcon from '@mui/icons-material/Upload';
import EditIcon from '@mui/icons-material/Edit';
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
  timestamp: string; // format: "MM:SS"
  seconds: number; // calculated from timestamp
}

export default function VideoQuizTool() {
  const [activeStep, setActiveStep] = useState(0);
  const [videoTitle, setVideoTitle] = useState("");
  const [videoUrl, setVideoUrl] = useState("");
  const [videoDescription, setVideoDescription] = useState("");
  const [questions, setQuestions] = useState<VideoQuestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [tarFile, setTarFile] = useState<string | null>(null);

  const BACKEND = "http://localhost:8000";

  // Convert timestamp to seconds
  const timestampToSeconds = (timestamp: string): number => {
    const parts = timestamp.split(':');
    if (parts.length === 2) {
      return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    }
    return 0;
  };

  // Convert seconds to timestamp
  const secondsToTimestamp = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Step 1: Video information
  const handleNextToQuestions = () => {
    if (videoTitle.trim() && videoUrl.trim()) {
      setActiveStep(1);
    }
  };

  // Step 2: Add question
  const handleAddQuestion = () => {
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
    const newQuestions = [...questions];
    newQuestions[index] = { ...newQuestions[index], [field]: value };
    
    // Update seconds when timestamp changes
    if (field === 'timestamp') {
      newQuestions[index].seconds = timestampToSeconds(value);
    }
    
    setQuestions(newQuestions);
  };

  // Delete question
  const handleDeleteQuestion = (index: number) => {
    setQuestions(questions.filter((_, i) => i !== index));
  };

  // Step 3: Export video quiz
  const handleExportVideoQuiz = async () => {
    if (questions.length === 0) {
      alert("Vui lòng thêm ít nhất một câu hỏi");
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("video_title", videoTitle);
      formData.append("video_url", videoUrl);
      formData.append("video_description", videoDescription);
      formData.append("questions", JSON.stringify(questions));
      
      const res = await fetch(`${BACKEND}/api/v1/export/video-quiz`, {
        method: "POST",
        body: formData,
      });
      
      const data = await res.json();
      if (data.success && data.tar_file) {
        setTarFile(data.tar_file);
        setActiveStep(2);
      } else {
        alert("Có lỗi xảy ra khi export video quiz: " + (data.message || "Unknown error"));
      }
    } catch (e) {
      console.error("Error exporting video quiz:", e);
      alert("Có lỗi xảy ra khi export video quiz");
    }
    setLoading(false);
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

      {activeStep === 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" mb={2}>Bước 1: Thông tin video</Typography>
          
          <TextField
            fullWidth
            label="Tiêu đề video"
            value={videoTitle}
            onChange={(e) => setVideoTitle(e.target.value)}
            placeholder="Bài giảng về Địa lý Việt Nam"
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="URL Video (YouTube hoặc file)"
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=..."
            sx={{ mb: 2 }}
          />
          
          <TextField
            fullWidth
            label="Mô tả video"
            value={videoDescription}
            onChange={(e) => setVideoDescription(e.target.value)}
            placeholder="Video giới thiệu về địa lý tự nhiên Việt Nam"
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
                    label="Thời điểm xuất hiện (MM:SS)"
                    value={q.timestamp}
                    onChange={(e) => handleUpdateQuestion(index, 'timestamp', e.target.value)}
                    placeholder="01:30"
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
                      <MenuItem value="multiple_choice">Trắc nghiệm</MenuItem>
                      <MenuItem value="multiple_select">Chọn nhiều</MenuItem>
                      <MenuItem value="text_input">Nhập text</MenuItem>
                      <MenuItem value="numerical">Nhập số</MenuItem>
                    </Select>
                  </FormControl>
                  
                  {q.type === 'multiple_choice' && (
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
                  )}
                  
                  <TextField
                    fullWidth
                    label="Đáp án đúng"
                    value={q.correct_answers.join(', ')}
                    onChange={(e) => {
                      const answers = e.target.value.split(',').map(a => parseInt(a.trim())).filter(a => !isNaN(a));
                      handleUpdateQuestion(index, 'correct_answers', answers);
                    }}
                    placeholder="0 hoặc 0, 1 cho nhiều đáp án"
                    sx={{ mb: 2 }}
                  />
                </Box>
              </ListItem>
            ))}
          </List>
          
          <Button
            variant="contained"
            onClick={handleExportVideoQuiz}
            disabled={loading || questions.length === 0}
            startIcon={loading ? <CircularProgress size={20} /> : <UploadIcon />}
          >
            {loading ? "Đang tạo video quiz..." : "Tạo video quiz"}
          </Button>
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
              <a href={`http://localhost:8000${tarFile}`} download>
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
            </>
          )}
        </Paper>
      )}
    </Box>
  );
} 