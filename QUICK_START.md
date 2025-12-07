# Visa API - Quick Start

Hướng dẫn ngắn để chạy và dùng API. Swagger luôn sẵn tại `http://localhost:8000/docs`.

## Chạy local
```bash
pip install -r requirements.txt
cp .env.example .env   # cập nhật DATABASE_URL, SECRET_KEY, NEO4J_*, GOOGLE_API_KEY...
uvicorn api.server:app --reload
```

## Các nhóm endpoint (xem chi tiết trong /docs)
- **Users** (`/api/users/...`): đăng ký, đăng nhập, lấy thông tin, cập nhật, vô hiệu hóa tài khoản (field `role`: `admin` | `user`, mặc định `user`).
- **Chatbot** (`/api/chatbot/...`): hỏi đáp tư vấn du học/visa Úc, lưu lịch sử hội thoại.
- **System**: `/health` kiểm tra service, `/schema` xem snapshot schema Neo4j.

## Ví dụ nhanh
```bash
# Đăng ký
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","username":"demo","full_name":"Demo","password":"Passw0rd!"}'

# Đăng nhập và lấy token
TOKEN=$(curl -s -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Passw0rd!"}' | jq -r .access_token)

# Gửi câu hỏi tới chatbot (có thể bỏ Authorization nếu không cần gắn user)
curl -X POST http://localhost:8000/api/chatbot/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Visa 500 yêu cầu gì?"}'
```

## Lưu ý
- JWT lấy từ `/api/users/login`, gửi qua header `Authorization: Bearer <token>`.
- Neo4j và Google API key cần thiết để chatbot trả kết quả từ graph.
- Mọi endpoint và schema luôn cập nhật trong Swagger `/docs`.
