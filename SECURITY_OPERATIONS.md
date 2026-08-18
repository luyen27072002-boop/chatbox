# Security operations — beta baseline

## Khi API key/secret bị lộ
1. Vô hiệu hóa/rotate key tại nhà cung cấp ngay.
2. Thay secret trên Render/production environment, không commit key mới.
3. Kiểm tra Git history và log truy cập; nếu key từng commit, coi như đã lộ dù file đã xóa ở commit sau.
4. Chạy secret/dependency scan và redeploy.

## Khi nghi account takeover
1. Khóa/đổi thông tin đăng nhập tài khoản bị ảnh hưởng; xóa session nếu có server-side session store ở phiên bản tương lai.
2. Kiểm tra log 401/403/429 và các thao tác dữ liệu gần thời điểm sự cố.
3. Xác định dữ liệu bị truy cập/thay đổi; thông báo/tuân thủ nghĩa vụ sự cố nếu áp dụng.

## Khi database lỗi hoặc mất dữ liệu
1. Dừng thao tác ghi nếu có nguy cơ làm hỏng thêm.
2. Snapshot dữ liệu hiện tại.
3. Restore từ backup đã kiểm thử vào môi trường tách biệt trước.
4. Chỉ đưa production hoạt động lại sau kiểm tra integrity và account isolation.

## Khi bị spam/cháy API
1. Tăng rate limit chặt hơn tạm thời và khóa nguồn abuse.
2. Kiểm tra quota OpenAI và billing usage.
3. Rotate API key nếu nghi lộ key.
4. Không tắt ownership/security checks để “chữa cháy”.

## Trước public
- Chuyển production khỏi SQLite sang managed PostgreSQL.
- Có backup tự động và restore test thật.
- Chạy dependency/secret/static scan, test A/B ownership.
- Không còn lỗi Critical/High đã biết.
