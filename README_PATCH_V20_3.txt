Ở ĐÂY AI — V20.3: TÀI KHOẢN TEST VĨNH VIỄN

Bản này chép đè lên V20.2.

Tính năng:
- Một tài khoản có thể được chủ dự án bật quyền test không giới hạn vĩnh viễn.
- Không dùng 3 lượt/ngày, 10 lượt chào mừng, gói tháng hoặc lượt đã mua.
- Không có giới hạn 200 lượt/ngày.
- Vẫn ghi nhận tổng số tin đã dùng để theo dõi chi phí API.
- Xóa lịch sử chat không làm mất quyền test.
- Không hard-code mật khẩu hoặc tài khoản trong source code.

CÁCH BẬT
1. Chạy web và tạo tài khoản test bình thường.
2. Dừng server bằng Ctrl+C.
3. Tại thư mục dự án, chạy:

   python set_permanent_test_account.py TEN_DANG_NHAP

Ví dụ:

   python set_permanent_test_account.py owner_test

Có thể dùng email thay tên đăng nhập:

   python set_permanent_test_account.py owner-test@example.com

4. Chạy lại web:

   python app.py

5. Đăng nhập tài khoản đó. Giao diện sẽ hiện:

   Tài khoản test không giới hạn

CÁCH TẮT

   python set_permanent_test_account.py owner_test --disable

LƯU Ý
- Phải tạo tài khoản trên web trước rồi mới chạy lệnh bật.
- Quyền được lưu trong app.db, vì vậy khi đưa lên server phải giữ app.db trên ổ persistent.
- Không gửi tài khoản/mật khẩu test cho người khác vì tài khoản này không bị giới hạn lượt.
