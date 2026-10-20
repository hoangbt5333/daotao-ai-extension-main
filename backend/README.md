# Daotao AI Extension Backend

Backend API cho ứng dụng Daotao AI Extension, được refactor theo kiến trúc SOLID principles.

## Cấu trúc Project

```
backend/
├── app/
│   ├── api/                    # API endpoints
│   │   └── v1/
│   │       ├── endpoints/      # API endpoint handlers
│   │       └── router.py       # API router
│   ├── config/                 # Configuration
│   │   └── settings.py         # App settings
│   ├── core/                   # Core functionality
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── logging.py          # Logging configuration
│   ├── models/                 # Data models
│   │   ├── domain/             # Domain models
│   │   └── schemas/            # Pydantic schemas
│   ├── services/               # Business logic services
│   │   ├── export/             # Export services
│   │   ├── file/               # File processing services
│   │   └── llm/                # LLM services
│   └── main.py                 # FastAPI app entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Cài đặt

1. **Tạo virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows
```

2. **Cài đặt dependencies:**
```bash
pip install -r requirements.txt
```

3. **Tạo file .env:**
```bash
cp env.example .env
```

4. **Cấu hình environment variables trong .env:**
```env
# LLM API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
DEFAULT_LLM_PROVIDER=openai

# App settings
DEBUG=true
HOST=0.0.0.0
PORT=8000

# CORS
CORS_ORIGINS=["http://localhost:3000"]

# File settings
UPLOAD_DIR=uploads
EXPORT_DIR=exports
MAX_FILE_SIZE=52428800
```

## Chạy ứng dụng

### Development mode:
```bash
python -m app.main
```

### Production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

### Core Endpoints
- `GET /` - Root endpoint với thông tin API
- `GET /health` - Health check
- `GET /api/v1/providers/` - Lấy thông tin LLM providers

### Upload & Analysis
- `POST /api/v1/upload/` - Upload và extract text từ file
- `POST /api/v1/analyze/` - Phân tích văn bản với LLM
- `POST /api/v1/mapping/pdfs` - Map PDF files vào outline

### Question Processing
- `POST /api/v1/questions/process` - Xử lý câu hỏi text
- `POST /api/v1/questions/from-library` - Lấy câu hỏi từ library

### Export Endpoints
- `POST /api/v1/export/` - Export course OpenEdX
- `POST /api/v1/export/library` - Export library
- `POST /api/v1/export/exam` - Export exam
- `POST /api/v1/export/exam-subsection` - Export exam subsection
- `POST /api/v1/export/exam-questions-library` - Export exam questions as library
- `POST /api/v1/export/exam-section` - Export exam section
- `POST /api/v1/export/video-quiz` - Export video quiz

## Kiến trúc

### SOLID Principles
- **Single Responsibility**: Mỗi service chỉ có một trách nhiệm
- **Open/Closed**: Dễ dàng mở rộng mà không sửa đổi code hiện tại
- **Liskov Substitution**: Các provider có thể thay thế cho nhau
- **Interface Segregation**: Interfaces nhỏ, chuyên biệt
- **Dependency Inversion**: Phụ thuộc vào abstractions, không phải concretions

### Services
- **LLM Service**: Quản lý các LLM providers (Gemini, OpenAI, DeepSeek)
- **Export Service**: Quản lý các exporters (OpenEdX, Library, Exam, Video Quiz)
- **File Service**: Xử lý file upload, extraction, packaging

### Error Handling
- Custom exceptions cho từng loại lỗi
- Structured logging với structlog
- Consistent error responses

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

## Deployment

### Docker
```bash
docker build -t daotao-ai-backend .
docker run -p 8000:8000 daotao-ai-backend
```

### Environment Variables
Đảm bảo set đúng các environment variables cho production:
- `DEBUG=false`
- `CORS_ORIGINS` với domain thực tế
- API keys cho LLM providers
- File storage paths 