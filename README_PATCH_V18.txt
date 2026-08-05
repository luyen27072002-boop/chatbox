PATCH V18 - Giọng đời thường, ít hỏi

Chép đè 4 file vào folder cũ:
- prompting.py
- ai_service.py
- data/conversation_rules.json
- data/tone_examples.json

Thay đổi:
- Không mặc định kết thúc bằng câu hỏi.
- Nếu lượt trước đã hỏi và người dùng vừa trả lời, lượt sau không hỏi tiếp theo quán tính.
- Tin nhắn đùa/than ngắn được đáp cùng nhịp, không bị kéo thành kế hoạch.
- Bỏ ví dụ dataset cũ dễ kéo giọng AI.
- Giảm số ví dụ đưa vào prompt và giảm max output token.
- Hàng rào cuối: tối đa 2 câu, 1 dấu hỏi, bỏ list đánh số.

Sau khi chép:
Ctrl+C
python app.py
Ctrl+F5 trên trình duyệt
