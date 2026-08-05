V22 - KHÔNG GIAN CỦA TÔI

Mục tiêu:
- Sau đăng nhập, trang đầu tiên là “Hôm nay bạn muốn làm gì?”
- 6 chức năng có vai trò ngang nhau:
  1. Trò chuyện
  2. Viết lại hôm nay
  3. Điều chưa nói
  4. Nói thử trước
  5. Chuyện đang mở
  6. Dòng đời
- Giao diện xanh lá bình yên, có minh họa ở từng chức năng.
- Bỏ nút nổi “Cuốn đời tôi”.
- Đổi lịch sử trò chuyện thành “Dòng đời”.
- Sửa font và cách xuống dòng tiếng Việt ở trang Cuộc đời của tôi.

Cài đặt:
1. Giải nén.
2. Chép toàn bộ file/thư mục vào gốc dự án.
3. Chọn Replace khi Windows hỏi.
4. Chạy: python app.py
5. Đăng nhập lại. Sau đăng nhập web tự chuyển tới /home.

Kiểm tra:
- /home: trang chọn chức năng.
- /chat: giao diện trò chuyện.
- /life?tab=autobiography: viết lại hôm nay.
- /life?tab=unsent: điều chưa nói.
- /life?tab=rehearsal: nói thử trước.
- /life?tab=threads: chuyện đang mở.
- /chat?open=dong-doi: mở Dòng đời.

Các file trong patch:
app.py
life_features.py
templates/home.html
templates/index.html
templates/life.html
static/home.css
static/home.js
static/app.js
static/styles.css
static/life.css
static/life.js
