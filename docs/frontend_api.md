# API cho Frontend (FE)

Tài liệu ngắn gọn cho FE tích hợp với backend hiện tại (FastAPI).

## Base URL
- Local dev: `http://localhost:8000`
- Render/Prod: tùy cấu hình, ví dụ `https://<your-domain>/`

## Auth
- JWT từ `POST /api/users/login`
- Gửi header: `Authorization: Bearer <token>`
- Các endpoint Chatbot vẫn cho phép không có token, nhưng nếu có token thì sẽ gắn hội thoại với user.

## Users
### POST /api/users/register
- Body: `email`, `username`, `full_name` (optional), `password`, `role` (default `user`)
- Trả về: user object
- Body mẫu:
```json
{
  "email": "demo@example.com",
  "username": "demo",
  "full_name": "Demo User",
  "password": "Passw0rd!",
  "role": "user"
}
```
- Response mẫu:
```json
{
  "id": 1,
  "email": "demo@example.com",
  "username": "demo",
  "full_name": "Demo User",
  "role": "user",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### POST /api/users/login
- Body: `email`, `password`
- Trả về: `{ access_token, token_type, user }`
- Body mẫu:
```json
{ "email": "demo@example.com", "password": "Passw0rd!" }
```
- Response mẫu:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "demo@example.com",
    "username": "demo",
    "full_name": "Demo User",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

### GET /api/users/me
- Header: `Authorization: Bearer <token>`
- Trả về: user object
- Response mẫu: như phần `user` ở login.

### GET /api/users?skip=0&limit=10
- Trả về: danh sách user (không cần token)
- Response mẫu:
```json
[
  {
    "id": 1,
    "email": "demo@example.com",
    "username": "demo",
    "full_name": "Demo User",
    "role": "user",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### GET/PUT/DELETE /api/users/{id}
- PUT body: trường muốn cập nhật (`email`, `username`, `full_name`, `password`, `role`)
- DELETE: trả 204 nếu thành công
- PUT body mẫu:
```json
{ "full_name": "New Name", "role": "admin" }
```
- PUT response: user object sau cập nhật.

### POST /api/users/{id}/deactivate
- Vô hiệu hóa tài khoản, trả về user object
- Response mẫu:
```json
{
  "id": 1,
  "email": "demo@example.com",
  "username": "demo",
  "full_name": "Demo User",
  "role": "user",
  "is_active": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-02T00:00:00Z"
}
```

## Chatbot
### POST /api/chatbot/message
- Header: optional `Authorization: Bearer <token>`
- Body:
```json
{ "message": "Visa 500 yêu cầu gì?", "conversation_id": 1, "title": "Tu van visa" }
```
- Trả về:
```json
{
  "analysis": { "intent": "...", "entities": {...}, "query_type": "..." },
  "results": [ { "university": "...", "program_name": "..."} ] | null,
  "answer": "Chuỗi trả lời thân thiện",
  "query_type": "find_programs_by_university",
  "conversation_id": 1
}
```
- Response cấu trúc:
```json
{
  "analysis": {
    "intent": "STUDY",
    "entities": { "university_name": "UNSW", "level": "Master" },
    "query_type": "find_programs_by_university"
  },
  "results": [
    {
      "university": "UNSW",
      "program_name": "Master of IT",
      "program_url": "https://...",
      "requirements": [{ "exam": "IELTS", "score": 6.5 }]
    }
  ],
  "answer": "Tóm tắt tiếng Việt",
  "query_type": "find_programs_by_university",
  "conversation_id": 1
}
```
- Notes:
  - Nếu không gửi `conversation_id` → tạo mới.
  - Nếu conversation không thuộc user của token → 403.
  - Nếu không có token, conversation vẫn lưu với `user_id` null.

### GET /api/chatbot/conservations
- Header: `Authorization: Bearer <token>`
- Query: `skip`, `limit`
- Trả về danh sách hội thoại của user
- Response mẫu:
```json
[
  { "id": 3, "title": "Visa 500", "user_id": 1, "last_update": "2024-01-02T00:00:00Z" }
]
```

### GET /api/chatbot/conservations/{id}/details
- Header: `Authorization: Bearer <token>`
- Trả về danh sách tin nhắn (user/assistant) của hội thoại
- Response mẫu:
```json
[
  { "id": 10, "conversation_id": 3, "role": "user", "message": "Visa 500 cần gì?", "created_at": "..." },
  { "id": 11, "conversation_id": 3, "role": "assistant", "message": "Trả lời ...", "created_at": "..." }
]
```

## System
### GET /health
- Trả về `{ "status": "ok" }` để FE kiểm tra server đang chạy

### GET /schema
- Trả về snapshot schema Neo4j (text)

## Lưu ý FE
- CORS đã bật `allow_origins=["*"]`.
- Nếu cần refresh state, ưu tiên gọi `/health` trước khi thực hiện luồng chính.
- Handle lỗi 401/403 từ các endpoint yêu cầu token; redirect login nếu token hết hạn. 
