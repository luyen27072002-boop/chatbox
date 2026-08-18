# Data map — Mở Lối (baseline 08/08/2026)

| Nhóm dữ liệu | Nguồn | Lưu nội bộ | Có thể gửi ra vendor | Xóa/xuất |
|---|---|---|---|---|
| Tài khoản: tên, username, email | Đăng ký | accounts | Hosting production | Có |
| Password | Đăng ký | Chỉ password hash | Không gửi cho AI/payment | Xóa/vô hiệu hóa khi xóa account |
| Chat/profile/memory | Người dùng | users/messages/conversations | OpenAI khi dùng AI | Có |
| Nhật ký/life/rehearsal | Người dùng | life_* | OpenAI khi yêu cầu viết/phản hồi AI | Có |
| Học ngoại ngữ | Người dùng | language_* | OpenAI cho lượt roleplay AI | Có |
| Tử vi: ngày/giờ sinh, giới tính, lá số | Người dùng | astrology_* | OpenAI chỉ cho phần luận/hỏi khi bật AI | Có |
| Chi tiêu | Người dùng | finance_* | Hiện không cần gửi AI | Có |
| Big Five/EQ/tư duy | Người dùng | self_discovery_* | Hiện chấm bằng code | Có |
| Payment metadata | PayOS/user | payment_orders/subscriptions | PayOS | Xuất; retention phải chốt trước payment |
| Log kỹ thuật/an ninh | Request/server | stdout/log platform | Hosting/log provider cấu hình production | Retention phải chốt trước public |

Nguyên tắc: frontend không quyết định ownership. Dữ liệu AI chỉ gửi phần cần cho chức năng. Mọi module/vendor mới phải cập nhật bảng này.


## Career / CV / Job matching
| Dữ liệu | Nguồn | Lưu ở đâu | Có gửi vendor? | Ghi chú |
|---|---|---|---|---|
| Vai trò mục tiêu, kỹ năng, tóm tắt, kinh nghiệm, học vấn, dự án, ngôn ngữ | User | `career_profiles` | Chỉ gửi OpenAI khi user bấm viết lại CV/chấm câu trả lời | Không tự suy ra/bịa thêm kinh nghiệm |
| Bản CV đã tạo | User + optional OpenAI rewrite | `career_cv_versions` | OpenAI khi tạo bản AI | User phải kiểm tra trước khi nộp |
| Câu trả lời luyện phỏng vấn | User | `career_interview_answers` | OpenAI khi bật chấm AI | Chỉ phục vụ luyện tập; không phải quyết định tuyển dụng |
| Việc đã lưu / JD người dùng dán | User / nguồn tuyển dụng | `career_saved_jobs` | Không gửi OpenAI ở V1 | Có thể chứa thông tin của bên tuyển dụng; hạn chế lưu dữ liệu không cần thiết |
| Từ khóa tìm việc | User | Không lưu lâu dài | Gửi server Mở Lối; Remotive chỉ được backend fetch theo cache chung, không nhận profile user | Không gửi email/CV/profile sang Remotive |

Quyền dữ liệu: các bảng career được đưa vào luồng export và delete account. Mọi đọc/xóa resource phải lọc theo cả `user_id`.
