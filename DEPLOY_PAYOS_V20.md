# Kết nối payOS sau khi deploy

## 1. Tạo kênh thanh toán

Tạo tài khoản/kênh thanh toán payOS và lấy ba giá trị:

- Client ID
- API Key
- Checksum Key

Không đưa các khóa này vào JavaScript, HTML hoặc GitHub.

## 2. Cấu hình biến môi trường trên server

```env
FREE_WELCOME_LIMIT=10
FREE_DAILY_LIMIT=3
BILLING_TIMEZONE=Asia/Ho_Chi_Minh

PAYOS_CLIENT_ID=...
PAYOS_API_KEY=...
PAYOS_CHECKSUM_KEY=...
PUBLIC_BASE_URL=https://ten-mien-cua-ban.vn
SESSION_COOKIE_SECURE=true
PAYMENT_ALLOW_LOCALHOST=false
```

## 3. Cài thư viện và chạy server

```bash
pip install -r requirements.txt
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 8
```

`app.db` phải nằm trên ổ đĩa persistent. Nếu nền tảng dùng ổ tạm, hãy gắn volume
và đặt `DATABASE_PATH` trỏ vào volume đó.

## 4. Đăng ký webhook

Sau khi domain HTTPS đã truy cập được:

```bash
python confirm_payos_webhook.py
```

Webhook được đăng ký là:

```text
https://ten-mien-cua-ban.vn/api/billing/webhook/payos
```

Endpoint chấp nhận payload mẫu của payOS khi confirm URL, nhưng chỉ cộng lượt cho
đơn có trong database, đúng số tiền và chưa từng được áp dụng.

## 5. Kiểm tra

1. Mở `/health`; `payment_configured` phải là `true`.
2. Đăng nhập bằng tài khoản test.
3. Chọn gói 5K.
4. Thanh toán 5.000đ.
5. Chờ trang quay về và kiểm tra tài khoản được cộng đúng 25 lượt.
6. Gửi lại cùng webhook không được cộng thêm lần hai.

Trang `payment/return` chỉ để giao diện biết cần kiểm tra đơn. Lượt chỉ được cộng bởi
webhook đã qua xác minh chữ ký, không cộng vì URL trên trình duyệt báo thành công.
