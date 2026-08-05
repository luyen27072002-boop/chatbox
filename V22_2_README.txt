V22.2 — MỖI CHỨC NĂNG MỘT KHÔNG GIAN RIÊNG

Bản này đã gộp luôn hotfix V22.1. Không cần cài V22.1 trước.

ĐÃ SỬA
- Sửa lỗi TypeError khi bấm Mở trò chuyện (/chat).
- Khôi phục khu vực tài khoản, email và trạng thái số lượt trên trang chủ.
- Mỗi chức năng có một trang riêng, không còn dồn nhiều tab vào cùng một màn hình.
- Giữ giao diện yên tĩnh, màu xanh lá và minh họa đồng nhất.
- Dòng đời trở thành trang lịch sử riêng, hiển thị cả trang đã viết và cuộc trò chuyện cũ.
- Link V21/V22 cũ dạng /life?tab=... tự chuyển sang trang mới.

ĐƯỜNG DẪN MỚI
/home        Không gian của tôi
/chat        Trò chuyện
/story       Viết lại hôm nay
/unsent      Điều chưa nói
/rehearsal   Nói thử trước
/threads     Chuyện đang mở
/timeline    Dòng đời

CÁCH CÀI
1. Giải nén ZIP vào thư mục dự án.
2. Chọn Replace/ghi đè khi Windows hỏi.
3. Chạy: python app.py
4. Đăng nhập và thử từng thẻ trên /home.

PUSH SAU KHI TEST
 git add app.py life_features.py templates static
 git commit -m "Redesign V22.2 focused life spaces"
 git push
