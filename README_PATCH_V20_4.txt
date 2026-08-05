V20.4 - TÀI KHOẢN CHỦ KHÔNG GIỚI HẠN QUA BIẾN MÔI TRƯỜNG

File cần chép đè/thêm:
- Dockerfile (chép đè)
- permanent_test_env.py (file mới)

Render Environment:
PERMANENT_TEST_EMAILS=luyen27072002@gmail.com

Có thể thêm nhiều email:
PERMANENT_TEST_EMAILS=email1@gmail.com,email2@gmail.com

Sau khi push lên GitHub, Render sẽ tự deploy lại. Khi deploy xong:
1. Refresh web.
2. Nếu đang đăng nhập, chỉ cần mở lại trang; hook chạy trước request tiếp theo.
3. Khu quota phải hiện "Tài khoản test không giới hạn".

Lưu ý bảo mật:
Dự án hiện chưa xác minh email. Trước khi mở rộng cho người dùng thật, cần bổ sung xác minh email để tránh người khác đăng ký bằng email chủ nếu database bị tạo lại.
