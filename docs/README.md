# Visa API Documentation (VN)

Tài liệu nhanh cho API hiện tại. Trang Swagger có sẵn tại `/docs` (tự động sinh từ OpenAPI).

## Thành phần chính
- **Users**: đăng ký, đăng nhập, lấy thông tin, cập nhật, vô hiệu hóa tài khoản.
- **Chatbot**: hỏi đáp tư vấn du học/visa Úc (Gemini + Neo4j) và lưu lịch sử hội thoại.
- **System**: kiểm tra tình trạng dịch vụ và xem schema Neo4j đã nạp.

## Endpoint
- `GET /health` — kiểm tra server (không cần token)
- `GET /schema` — xem schema Neo4j snapshot
- `POST /api/users/register` — đăng ký
- `POST /api/users/login` — đăng nhập, nhận JWT
- `GET /api/users/me` — thông tin user hiện tại (Bearer token)
- `GET /api/users` — danh sách user (paginate)
- `GET /api/users/{id}` / `PUT` / `DELETE` / `POST .../deactivate`
- `POST /api/chatbot/message` — hỏi chatbot, lưu hội thoại
- `GET /api/chatbot/conservations` — danh sách hội thoại (Bearer token)
- `GET /api/chatbot/conservations/{id}/details` — chi tiết hội thoại (Bearer token)

## Chạy local nhanh
```bash
pip install -r requirements.txt
cp .env.example .env   # điền DATABASE_URL, NEO4J_URI, GOOGLE_API_KEY...
uvicorn api.server:app --reload
# Mở http://localhost:8000/docs
```

## Ví dụ cURL
```bash
# Đăng ký
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","username":"demo","full_name":"Demo","password":"Passw0rd!"}'

# Đăng nhập
TOKEN=$(curl -s -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"Passw0rd!"}' | jq -r .access_token)

# Hỏi chatbot
curl -X POST http://localhost:8000/api/chatbot/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"Visa 500 yêu cầu gì?"}'
```
