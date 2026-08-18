# Mở Lối — quy tắc bắt buộc khi sửa code

Áp dụng cho mọi patch từ 08/08/2026. Mục tiêu: sửa đúng phần được yêu cầu nhưng không làm yếu security/privacy/payment hiện có.

## Không được đụng nếu yêu cầu không bắt buộc
- Không sửa/xóa `.env`, secret production, `app.db`, dữ liệu người dùng, `.git`, `.venv`.
- Không đổi database production, auth provider, payment provider, pricing, retention hoặc legal text theo hướng cam kết mới nếu chủ dự án chưa yêu cầu rõ.
- Không bỏ/giảm ownership check `user_id`, password hashing, cookie flags, security headers, same-origin guard, rate limit, quota, webhook verification hoặc idempotency.
- Không đưa `user_id`, giá tiền, số credit, quyền admin do frontend gửi lên thành nguồn sự thật.
- Không log password, API key, token, nội dung chat/nhật ký hoặc dữ liệu nhạy cảm nếu không thực sự cần.

## Mọi API mới phải qua checklist
1. Xác thực ở server nếu dữ liệu không public.
2. Resource phải query bằng cả `resource_id` + `user_id` khi thuộc người dùng.
3. Validate type/length/range; SQL dùng parameterized query.
4. POST/PUT/PATCH/DELETE phải tương thích same-origin/CSRF baseline.
5. Route auth/AI/payment/abuse-sensitive phải có rate limit phù hợp.
6. Không trả stack trace/secret cho client.
7. Nếu tạo dữ liệu cá nhân mới: cập nhật `DATA_MAP.md`, export và delete flow.
8. Nếu gọi vendor/API mới: cập nhật `VENDOR_MAP.md` và Privacy Policy trước public.
9. Nếu liên quan payment: server verify webhook + amount + idempotency; không cộng credit từ callback browser.
10. Thêm/điều chỉnh test trước khi gửi patch.

## Quy tắc đóng gói patch
- Chỉ gửi file cần sửa/thêm.
- Không gửi `.env`, database, `.git`, `.venv`, cache, model/dataset không liên quan.
- Chạy `python scripts/security_scan.py`, compile/test phần đã sửa trước khi bàn giao.
- Thay đổi lớn auth/payment/database phải được tách thành patch riêng và có phương án rollback.
