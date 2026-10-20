# Frontend Next.js cho daotao-ai-extension

## Cài đặt

```bash
cd frontend
npm install
```

## Chạy development server

```bash
npm run dev
```

Truy cập http://localhost:3000

## Kết nối backend
- Mặc định frontend gọi API backend tại http://localhost:8000
- Đảm bảo backend Python đã chạy trước khi sử dụng frontend.

## Tính năng
- Upload file PDF, DOCX, TXT → Trích xuất văn bản
- Gửi văn bản → Phân tích outline/questions bằng AI
- Xuất file .tar.gz chuẩn Open edX
