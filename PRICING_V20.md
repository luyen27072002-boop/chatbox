# Bảng giá V20

## Miễn phí

- 10 lượt chào mừng cho mỗi tài khoản mới.
- 3 lượt miễn phí mỗi ngày, không cộng dồn.
- Xóa đoạn chat hoặc xóa dữ liệu hội thoại không làm mới quota.

## Mua lượt — không hết hạn

| Giá | Lượt | Giá/lượt |
|---:|---:|---:|
| 5.000đ | 25 | 200đ |
| 10.000đ | 55 | khoảng 182đ |
| 20.000đ | 120 | khoảng 167đ |
| 50.000đ | 320 | khoảng 156đ |
| 100.000đ | 700 | khoảng 143đ |
| 200.000đ | 1.500 | khoảng 133đ |
| 500.000đ | 4.000 | 125đ |

## Gói tháng — 30 ngày

| Giá | Quyền lợi | Giá tối đa/lượt |
|---:|---:|---:|
| 49.000đ | 400 lượt | khoảng 123đ |
| 99.000đ | 900 lượt | 110đ |
| 199.000đ | 1.800 lượt | khoảng 111đ |
| 399.000đ | 3.600 lượt | khoảng 111đ |
| 799.000đ | Không giới hạn, tối đa 200 lượt/ngày | khoảng 133đ nếu dùng đủ 6.000 lượt |

Gói Không giới hạn không có trần theo tháng, nhưng có chính sách sử dụng hợp lý
200 lượt/ngày để chặn bot, chia sẻ tài khoản và gọi API tự động. Người dùng bình thường
rất khó chạm mức này.

## Nguyên tắc cấp lượt

Hệ thống dùng theo thứ tự:

1. 3 lượt miễn phí trong ngày.
2. 10 lượt chào mừng còn lại.
3. Gói tháng đang hoạt động.
4. Lượt mua thêm không hết hạn.

Giá và số lượt được đọc từ `data/pricing_plans.json`, không tin giá do trình duyệt gửi lên.
Webhook phải có chữ ký hợp lệ, đúng mã đơn và đúng số tiền mới cộng lượt.
