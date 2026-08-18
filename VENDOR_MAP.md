# Vendor map — baseline

| Vendor | Vai trò dự kiến | Dữ liệu có thể nhận | Trạng thái |
|---|---|---|---|
| OpenAI | Model AI | Prompt/ngữ cảnh cần thiết của chat, language, astrology/life AI | Đang tích hợp |
| Render | Hosting production | Request, app runtime, DB/log tùy kiến trúc deploy | Đã dùng cho deploy; cần chốt DB managed trước public |
| PayOS | Payment gateway | Order/payment metadata; không tự lưu card/CVV trong app | Code đã tích hợp, chưa nên bật trước business/legal gate |
| GitHub | Source control | Source code; không được chứa `.env`, production DB hoặc user data | Đang dùng |

Email/analytics/monitoring riêng: chưa được xác nhận trong code hiện tại. Khi thêm vendor mới phải cập nhật Privacy Policy/data map và rà chuyển dữ liệu xuyên biên giới nếu áp dụng.


## Remotive — nguồn việc làm remote công khai
- Mục đích: cung cấp một nguồn việc remote công khai cho khu Tìm việc.
- Dữ liệu gửi từ Mở Lối: backend tải feed công khai theo cache chung; không gửi tên, email, CV, hồ sơ nghề nghiệp hay lịch sử người dùng cho Remotive.
- Dữ liệu nhận: tiêu đề việc, công ty, địa điểm được phép ứng tuyển, loại việc, lương nếu có, mô tả và URL tin gốc.
- Hiển thị: phải ghi nguồn Remotive và link về URL gốc theo điều khoản public API.
- Giới hạn vận hành: cache tối thiểu 6 giờ để tránh gọi API quá thường xuyên.
- Trước public: Privacy Policy/Vendor Map phải tiếp tục nêu rõ nguồn dữ liệu tuyển dụng bên thứ ba.


## Job search outbound sources — search gateway
- Mục đích: giúp người dùng mở cùng một truy vấn tìm việc trên nhiều nền tảng tuyển dụng.
- Nguồn hiện có trong UI: TopCV, VietnamWorks, CareerViet, Việc Làm 24h, JobsGO, JobOKO, CareerLink, Glints, Indeed Việt Nam, LinkedIn Jobs, ITviec, TopDev, JobStreet; Remotive tiếp tục là nguồn remote có kết quả hiển thị trong Mở Lối.
- Cách hoạt động: với nguồn có URL tìm kiếm ổn định, trình duyệt mở trực tiếp truy vấn trên nguồn. Với nguồn có cấu trúc URL không ổn định, Mở Lối cung cấp nút tìm kiếm web giới hạn đúng domain và một nút mở website gốc.
- Dữ liệu gửi: chỉ từ khóa và địa điểm mà người dùng chủ động nhập vào trường tìm kiếm/URL khi họ bấm mở. Mở Lối không gửi CV, email, profile, lịch sử chat, personality, tử vi hay dữ liệu chi tiêu sang các nguồn outbound.
- Không crawler/scrape kho tin của các nguồn này trong V2. Không lưu nội dung JD của nguồn outbound nếu người dùng không chủ động dán/lưu.
- Mọi link ngoài mở bằng tab mới với `rel="noopener noreferrer"`.


## Jooble REST API — job result aggregator
- Mục đích: lấy danh sách job cụ thể để hiển thị title, công ty, địa điểm, lương, loại việc, nguồn và link trong Mở Lối.
- Cơ sở tích hợp: Jooble công khai REST API cho webmaster của portal/search engine để đưa kết quả tìm việc lên website theo giao diện riêng.
- Biến môi trường: `JOOBLE_API_KEY`.
- Dữ liệu gửi: chỉ `keywords`, `location`, page/result count do người dùng chủ động tìm.
- Không gửi: tên user, email, CV, career profile, chat, tử vi, personality, finance hoặc lịch sử tài khoản.
- Matching với profile Mở Lối được thực hiện ở backend Mở Lối sau khi nhận job result.
- Link job sử dụng trực tiếp trường `link` do Jooble trả về; UI vẫn hiển thị trường `source`.
- Nếu API key chưa được cấu hình, hệ thống fallback về Remotive + outbound source gateway; không giả lập job.
