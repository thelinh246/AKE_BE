# Visa API - Documentation Index

Tài liệu chính (VN) cho dự án:

- [QUICK_START.md](QUICK_START.md): cách chạy nhanh, danh sách endpoint chính và ví dụ cURL.
- [docs/README.md](docs/README.md): tóm tắt API (Users + Chatbot + System) và các lệnh mẫu.
- [README_CHATBOT.md](README_CHATBOT.md): chi tiết pipeline chatbot và cấu trúc lưu hội thoại.
- Swagger: truy cập `http://localhost:8000/docs` để xem schema và thử API trực tiếp.
- Docker: dùng `docker-compose.yml` hoặc `Dockerfile` nếu muốn chạy bằng container.

Mẹo: cấu hình `.env` dựa trên `.env.example` (DATABASE_URL, SECRET_KEY, NEO4J_*, GOOGLE_API_KEY). Khi server chạy, kiểm tra `/health` và `/schema` trước khi gọi các endpoint khác.
