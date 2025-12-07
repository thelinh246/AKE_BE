# Chatbot & Conversation API

Tài liệu nhanh cho API chatbot (Gemini + Neo4j) và lưu lịch sử hội thoại vào PostgreSQL.

## Base URL
```
/api/chatbot
```

## Endpoint

### POST /api/chatbot/message
Trả lời câu hỏi, đồng thời lưu lịch sử hội thoại.

**Headers**
- `Content-Type: application/json`
- `Authorization: Bearer <token>` (tùy chọn, để gắn conversation với user đã đăng nhập)

**Request body**
```json
{
  "message": "Tìm chương trình Master IT tại UNSW",
  "conversation_id": 1,            // optional: tiếp tục cuộc trò chuyện cũ
  "title": "Tu van du hoc UNSW"    // optional: đặt tiêu đề, mặc định cắt từ message
}
```

**Response**
```json
{
  "analysis": { "...": "intent/entities/query_type từ Gemini" },
  "results": [ { "university": "...", "program_name": "..."} ],  // có thể null nếu không chạy Cypher được
  "answer": "Câu trả lời thân thiện",
  "query_type": "find_programs_by_university",
  "conversation_id": 1
}
```

**Lưu ý**
- Nếu `conversation_id` không gửi, hệ thống sẽ tạo bản ghi mới.
- Nếu gửi `conversation_id` không tồn tại → 404.
- Nếu conversation gắn với một user khác → 403.
- Nếu không có `Authorization`, cuộc trò chuyện vẫn được lưu nhưng `user_id` là null.
- Trước khi chạy Cypher/Gemini, hệ thống sẽ **viết lại câu hỏi** dựa trên `title` + lịch sử 10 tin nhắn gần nhất, và có thể **cập nhật title** để tóm tắt hội thoại tốt hơn.

## Lưu trữ hội thoại trong PostgreSQL

| Bảng | Mục đích | Cột chính |
|------|----------|-----------|
| `conservation` | Thông tin cuộc trò chuyện | `id`, `user_id`, `title`, `last_update` |
| `conservation_detail` | Các tin nhắn trong cuộc trò chuyện | `id`, `conversation_id`, `role` (`user` hoặc `assistant`), `message`, `created_at` |

- Mỗi lần gọi `/api/chatbot/message`, hệ thống thêm 2 dòng vào `conservation_detail` (user và assistant) và cập nhật `last_update`.
- Bảng được tạo tự động khi chạy `init_db()` (đã gọi ở `api/server.py` startup).

## Quy trình xử lý
1. Nhận request và (tùy chọn) trích xuất user_id từ Bearer token.
2. Lấy hoặc tạo conversation (dựa trên `conversation_id` và `title`).
3. Chạy pipeline chatbot: detect intent → Cypher Neo4j → format câu trả lời bằng Gemini.
4. Lưu cặp tin nhắn (user + assistant) vào PostgreSQL.
5. Trả về nội dung trả lời kèm thông tin phân tích và conversation_id.

## Ví dụ cURL
```bash
curl -X POST http://localhost:8000/api/chatbot/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Visa 500 la gi va dieu kien?"}'
```

```bash
# Tiếp tục cuộc trò chuyện có id=3 và gắn user qua Bearer token
curl -X POST http://localhost:8000/api/chatbot/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"message": "Truong nao yeu cau IELTS 6.5?", "conversation_id": 3}'
```

### GET /api/chatbot/conservations
Lấy danh sách conservation. **Bắt buộc Bearer token**, kết quả lọc theo user_id của token.

**Query params**
- `skip` (int, default 0)
- `limit` (int, default 20)

**Response**
```json
[
  { "id": 1, "title": "Visa 500 la gi", "user_id": 2, "last_update": "2024-08-01T12:00:00Z" }
]
```

### GET /api/chatbot/conservations/{id}/details
Lấy toàn bộ tin nhắn của một conservation. **Bắt buộc Bearer token**, chỉ trả về nếu conversation thuộc user trong token.

**Response**
```json
[
  { "id": 10, "conversation_id": 1, "role": "user", "message": "Hello", "created_at": "..." },
  { "id": 11, "conversation_id": 1, "role": "assistant", "message": "Hi!", "created_at": "..." }
]
```
