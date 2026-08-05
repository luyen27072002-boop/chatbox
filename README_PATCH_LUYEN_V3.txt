BẢN VÁ TÍNH CÁCH LUYỆN V3

Mục tiêu
- Chuyển kết quả trắc nghiệm thành DNA tính cách thực tế của Luyện.
- Luyện tự đổi cách phản ứng: ấm khi buồn, san sẻ khi áp lực, nghịch khi vui, quyết đoán khi phân vân.
- Giữ nguyên nguyên tắc: không nịnh, không nói láo, không tục/chửi bậy, không đổ lỗi và không tạo lệ thuộc.
- Bênh người dùng trước về cảm xúc nhưng không xác nhận sai hoặc cổ vũ hành động gây hại.
- Câu hỏi kỹ thuật/học thuật được trả lời đầy đủ, có cấu trúc; không còn bị ép xuống 1–2 câu.

File thay đổi
- ai_service.py
- prompting.py
- data/personality.json
- data/personas.json
- data/conversation_rules.json

File mới
- data/luyen_response_examples.json
- tests/test_luyen_personality.py

Cách chép
1. Tắt web đang chạy.
2. Chép toàn bộ nội dung bản vá vào thư mục dự án hiện tại và chọn ghi đè.
3. Không xóa file .env hoặc app.db của dự án hiện tại.
4. Chạy lại start_windows.bat.

Kiểm tra tự động
python -m pytest -q
