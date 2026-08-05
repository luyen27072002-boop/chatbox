Ở ĐÂY AI / GÓC NHỎ CUỘC SỐNG — V20
=====================================

Bản V20 đã bao gồm toàn bộ V19 và bản tính cách Luyện V3. Không cần tải V19 trước.

NỘI DUNG CHÍNH
- Sửa tách sạch mode và persona, không lẫn prompt Luyện sang persona khác.
- Sửa tự hiểu câu “phân tích đi”.
- Sửa menu Đổi tên/Xóa bị thẻ bên dưới che.
- Sửa nhãn đăng ký bị đổi nhầm.
- 10 lượt chào mừng cho tài khoản mới.
- 3 lượt miễn phí mỗi ngày, không cộng dồn.
- Hệ thống ví lượt, gói mua thêm, gói tháng và gói Không giới hạn.
- Tích hợp payOS: tạo link thanh toán, verify webhook, cộng lượt đúng một lần.
- Không cộng lượt chỉ dựa vào trang quay về sau thanh toán.
- Nếu AI lỗi bất ngờ sau khi giữ lượt, hệ thống tự hoàn lại lượt.
- SQLite dùng WAL + busy timeout; cấu hình Gunicorn 1 worker/8 threads cho MVP.

CÁCH CHỒNG BẢN VÁ
1. Sao lưu app.db và .env hiện tại.
2. Chép toàn bộ file trong gói này vào thư mục dự án và chọn Replace.
3. Không xóa app.db cũ; code tự tạo thêm các bảng billing khi khởi động.
4. Không ghi đè .env bằng .env.example. Chỉ chép các biến mới sang .env.
5. Chạy:
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   .venv\Scripts\python.exe app.py

KIỂM TRA LOCAL
- Chat và quota chạy bình thường khi chưa có khóa payOS.
- Nút thanh toán sẽ bị khóa đến khi server có đủ PAYOS_CLIENT_ID,
  PAYOS_API_KEY và PAYOS_CHECKSUM_KEY.
- Localhost không nhận webhook thật. Cần deploy HTTPS hoặc dùng tunnel HTTPS.

LƯU Ý SERVER
- app.db phải nằm trên ổ đĩa persistent. Không dùng ổ tạm/ephemeral cho dữ liệu thật.
- Sau deploy, đặt SESSION_COOKIE_SECURE=true.
- Đặt PUBLIC_BASE_URL bằng URL HTTPS công khai, không có dấu / cuối.
- Chạy python confirm_payos_webhook.py sau khi server hoạt động.
