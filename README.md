# Góc nhỏ cuộc sống V14 — API thật, full persona, 2 giọng, dataset hội thoại

Bản này bỏ hoàn toàn chế độ trả lời demo. Mọi tin nhắn đều gọi OpenAI API thật. Nếu thiếu API key, web trả lỗi rõ ràng và không tự dùng câu mẫu thay thế.

## Ba lớp điều khiển

1. **Mode**: Chỉ lắng nghe / Cùng phân tích / Cho hướng xử lý.
2. **Persona**: Lúc này lúc kia / Người khó tính / Người ôn hòa / Người lý trí / Người thực tế / Hài hước nhẹ / Luyện.
3. **Giọng**: Nhẹ nhàng / Thực tế.

## Dataset đang dùng

- `data/conversation_examples.json`: 54 lượt hội thoại nhiều lượt của Luyện.
- `data/persona_examples.json`: ví dụ cho 6 persona còn lại.
- `data/tone_examples.json`: ví dụ phân biệt Nhẹ nhàng và Thực tế.
- `data/personas.json`: quy luật của 7 persona.
- `data/conversation_rules.json`: flow cho 3 mode.
- `dataset_source/`: Excel nguồn để sửa và bổ sung hằng ngày.

## Chạy trực tiếp bằng API

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Mở `.env`, dán key thật:

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.6-luna
```

Sau đó chạy:

```powershell
python app.py
```

Mở `http://127.0.0.1:5000`.

## Cách hoạt động

Tin nhắn mới → lọc dataset theo mode/persona/giọng/chủ đề → lấy ví dụ gần nhất → ghép quy luật + lịch sử → gọi Responses API → kiểm tra đầu ra → lưu lịch sử và cập nhật trí nhớ.

## Lỗi thường gặp

- `Thiếu OPENAI_API_KEY`: chưa dán key vào `.env`.
- `service_unavailable`: kiểm tra key, model, billing và hạn mức API.
- Model không tồn tại hoặc tài khoản chưa được cấp quyền: đổi `OPENAI_MODEL` sang model tài khoản mày đang dùng được.
