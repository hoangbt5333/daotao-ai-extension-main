# daotao-ai-extension

## 🚀 Hướng dẫn sử dụng nhanh

### 1. Clone repository
```bash
git clone https://github.com/your-org/daotao-ai-extension.git
cd daotao-ai-extension
```

### 2. Cấu hình môi trường
- Tạo file `.env` cho backend (xem mẫu `backend/env.example`).
- Tạo file `.env` cho frontend nếu cần.

### 3. Chạy ứng dụng bằng Docker Compose (khuyên dùng)
```bash
docker-compose up --build
```
- Backend FastAPI sẽ chạy ở: http://localhost:8000
- Frontend Next.js sẽ chạy ở: http://localhost:3000

### 4. Phát triển nhanh (dev hot reload)
- Mọi thay đổi code ở `backend/` hoặc `frontend/` sẽ tự động reload container tương ứng.
- Nếu thay đổi dependencies, hãy rebuild service đó:
  ```bash
  docker-compose build backend
  docker-compose build frontend
  ```

### 5. Cấu trúc thư mục chính
- `backend/`: FastAPI, xử lý AI, export Open edX, API.
- `frontend/`: Next.js, giao diện người dùng.
- `exports/`, `tdc*/`: Các file export, không cần commit.

### 6. Hướng dẫn chi tiết
- Xem chi tiết các bước, công nghệ, quy trình tại phần dưới hoặc tài liệu `README.md` này.
- Đọc kỹ các phần "Project Overview", "Workflow", "Technology Stack" để hiểu rõ kiến trúc và cách mở rộng.

---
Link hướng dẫn tạo outline: https://drive.google.com/file/d/1XhplEzdTwJOP59wlJlYOYvhNlP4MWzmB/view?usp=sharing
"# daotao-ai-extension-main" 
