import React from 'react';
import { Box, Typography, Paper, Link } from '@mui/material';

export default function GuidePage() {
  return (
    <Box>
      <Typography variant="h5" fontWeight={700} mb={2}>Hướng dẫn sử dụng</Typography>
      <Paper sx={{ p: 2 }}>
        <Typography mb={2}>
          1. Chọn chức năng "Tạo khóa học" để upload file tài liệu (PDF, DOCX, TXT).<br/>
          2. Trích xuất văn bản, phân tích outline và câu hỏi bằng AI.<br/>
          3. Xuất file .tar.gz chuẩn Open edX.<br/>
          4. Đăng nhập vào <Link href="https://studio.daotao.ai" target="_blank">studio.daotao.ai</Link> và sử dụng chức năng Import để tải lên file .tar.gz.<br/>
        </Typography>
        <Typography>
          Nếu gặp lỗi khi import, kiểm tra lại cấu trúc file hoặc liên hệ hỗ trợ.<br/>
          Các chức năng khác sẽ được cập nhật trong tương lai.
        </Typography>
      </Paper>
    </Box>
  );
} 