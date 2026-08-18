# Public Mở Lối: Render + PostgreSQL + Cloudflare R2

## Sau khi deploy có phải chạy `python app.py` không?

Không. `python app.py` chỉ dùng khi phát triển trên máy cá nhân. Khi deploy, Render chạy container và Gunicorn 24/7 theo `Dockerfile`. Mỗi lần push commit mới lên nhánh GitHub đã nối với Render, Render tự build và deploy lại.

## Kiến trúc production

- Render Web Service: Flask/Gunicorn và HTTPS.
- Render Postgres: tài khoản, chat, memory, Finance, tiến độ học, billing metadata.
- Cloudflare R2 private bucket: ảnh, PDF, Word, Excel, file code và file AI tạo.
- OpenAI API: chỉ xử lý AI; không dùng làm nơi lưu dữ liệu người dùng.

Local vẫn dùng `app.db` và thư mục `storage/` nếu không có `DATABASE_URL`/R2 credentials.

## 1. Tạo Cloudflare R2 trước

1. Mở Cloudflare Dashboard -> R2 Object Storage.
2. Tạo bucket private, ví dụ `mo-loi-private`.
3. Tạo R2 API Token có quyền Object Read & Write cho bucket đó.
4. Ghi lại bốn giá trị: Account ID, Access Key ID, Secret Access Key, Bucket name.
5. Không commit các key này vào GitHub hoặc `.env.example`.

## 2. Push project lên GitHub

Đảm bảo `.env`, `app.db` và `storage/` không được commit. Patch này đã thêm `storage/` vào `.gitignore`.

## 3. Deploy bằng Render Blueprint

1. Render Dashboard -> New -> Blueprint.
2. Kết nối GitHub và chọn repo chứa `render.yaml`.
3. Render sẽ tạo:
   - `mo-loi-ai` web service ở Singapore.
   - `mo-loi-postgres` PostgreSQL ở Singapore.
4. Trong lần tạo Blueprint, nhập các secret được hỏi:
   - `OPENAI_API_KEY`
   - `R2_ACCOUNT_ID`
   - `R2_ACCESS_KEY_ID`
   - `R2_SECRET_ACCESS_KEY`
   - `R2_BUCKET`
5. `DATABASE_URL` được Blueprint nối tự động từ Render Postgres; không tự copy database password vào code.
6. `SECRET_KEY` được Render sinh một lần và giữ trong environment.

`REQUIRE_POSTGRES=true` và `REQUIRE_R2_STORAGE=true` khiến production fail rõ ràng nếu thiếu storage thật, thay vì âm thầm rơi về SQLite/thư mục tạm và mất dữ liệu.

## 4. Kiểm tra sau deploy

1. Mở URL HTTPS do Render cấp.
2. Tạo tài khoản A, đăng nhập, thêm một khoản Finance và một đoạn chat.
3. Upload một ảnh/tệp nhỏ.
4. Đăng xuất, tạo tài khoản B và xác nhận B không nhìn thấy dữ liệu A.
5. Render Dashboard -> Web Service -> Manual Deploy -> Restart service.
6. Đăng nhập lại A: chat/Finance vẫn phải còn; file vẫn tải được.

## 5. Local development

`.env` local giữ:

```env
DATABASE_PATH=app.db
REQUIRE_POSTGRES=false
CHAT_STORAGE_DIR=storage
REQUIRE_R2_STORAGE=false
```

Không cần `DATABASE_URL` hay R2 keys để chạy local:

```bash
python app.py
```

## 6. Nếu muốn mang dữ liệu `app.db` cũ lên Postgres

Deploy production một lần trước để tạo schema. Sau đó trên máy local đặt tạm `DATABASE_URL` bằng **External Database URL** của Render Postgres và chạy:

```bash
python scripts/migrate_sqlite_to_postgres.py app.db
```

Xóa biến `DATABASE_URL` khỏi shell local sau khi migrate để local quay lại dùng SQLite. Script không xóa `app.db` cũ và dùng `ON CONFLICT DO NOTHING` để tránh ghi đè dữ liệu đã có.

File cũ trong thư mục local `storage/` không được script database tự upload lên R2. Nếu cần mang cả file cũ lên production, nên làm một migration riêng sau khi xác định file nào thực sự cần giữ.

## 7. Một lưu ý chi phí

Blueprint đang dùng Render Web `starter` và Postgres `basic-256mb` để dữ liệu production không phụ thuộc database free tạm thời. Có thể đổi plan trong `render.yaml` trước khi tạo Blueprint, nhưng không nên dùng Free Postgres cho dữ liệu công ty lâu dài.
