# Ở Đây — MVP V5: hồ sơ nhiều lớp

V5 giữ toàn bộ chức năng V4 và thêm hệ thống cá nhân hóa theo nhiều lớp:

1. **Mục đích trò chuyện:** Chỉ lắng nghe, Cùng phân tích, Cho hướng xử lý.
2. **Nhân vật AI:** Lúc này lúc kia, Người khó tính, Người ôn hòa, Người lý trí, Người thực tế, Hài hước nhẹ, Luyện.
3. **Hồ sơ cách tiếp nhận:** độ thẳng, hỗ trợ cảm xúc, phản biện, chi tiết, hài hước và thiên hướng hành động.
4. **Bối cảnh sống:** tuổi, học sinh/sinh viên/người đi làm/doanh nhân/người chăm sóc/đã nghỉ hưu/người cao tuổi, tình trạng hôn nhân, con cái và hoàn cảnh sống.
5. **Tin nhắn hiện tại:** có ưu tiên cao hơn hồ sơ cũ.

Hệ thống không tạo một file code riêng cho từng tổ hợp. Backend ghép các lớp thành một prompt duy nhất để tránh hàng trăm trường hợp khó bảo trì.

## Điểm mới

- Tự mở trắc nghiệm 10 câu khi người dùng mới vào.
- Có các nhóm tuổi từ dưới 18 đến trên 61.
- Có học sinh, sinh viên, người mới đi làm, người đi làm, doanh nhân, nội trợ/người chăm sóc, người nghỉ hưu và người cao tuổi.
- Có độc thân/chưa kết hôn, đang hẹn hò, đã kết hôn, ly thân, ly hôn và góa.
- Có tình trạng con cái và hoàn cảnh sống.
- Kết quả được quy về 10 kiểu tiếp nhận ban đầu, nhưng vẫn giữ 6 điểm số liên tục thay vì ép người dùng vào một nhãn cứng.
- Giới tính chỉ dùng làm bối cảnh khi liên quan, không được dùng để suy ra tính cách.
- Hồ sơ được lưu trong SQLite và tự migration khi chép đè V4/V3.
- Lịch sử chat ghi lại kiểu hồ sơ đã dùng tại thời điểm tạo câu trả lời.
- Các nhân vật ngoài Luyện có thể đọc ví dụ trong `data/persona_examples.json`.
- Mode Luyện tiếp tục dùng `data/personality.json` và `data/examples.json`.

## Chạy trên Windows

Khuyến nghị Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe app.py
```

Mở `http://127.0.0.1:5000`.

Nếu chép V5 đè lên thư mục đang dùng:

1. Tắt server bằng `Ctrl + C`.
2. Chép file V5 vào và chọn Replace.
3. Giữ nguyên `.env`, `.venv` và `app.db`.
4. Chạy lại `python app.py`.
5. Nhấn `Ctrl + Shift + R` trong Chrome.

## Bật AI thật

Trong `.env`:

```env
OPENAI_API_KEY=key_thật_của_mày
OPENAI_MODEL=gpt-5-mini
DEMO_MODE=false
```

Không đặt key trong `.env.example`, JavaScript hoặc GitHub.

## Luồng ghép phản hồi

```text
An toàn
+ mục đích trò chuyện
+ tin nhắn hiện tại
+ nhân vật AI
+ hồ sơ cách tiếp nhận
+ bối cảnh sống
+ trí nhớ
+ ví dụ đã duyệt
= câu trả lời
```

Mục đích trò chuyện có ưu tiên cao hơn nhân vật. Nhân vật có ưu tiên cao hơn hồ sơ. Vì vậy `Người thực tế + Chỉ lắng nghe` vẫn phải lắng nghe, còn hồ sơ chỉ làm câu trả lời ngắn/dài, mềm/thẳng hơn.

## Dữ liệu hồ sơ

Hồ sơ được lưu trong cột `profile_json` của bảng `users`. Ví dụ:

```json
{
  "age_group": "61_plus",
  "life_stage": "retired",
  "relationship_status": "married",
  "children_status": "adult_children",
  "communication": {
    "directness": 55,
    "emotional_support": 72,
    "challenge_level": 40,
    "detail_level": 65,
    "humor_level": 35,
    "action_orientation": 45
  },
  "archetype": "gentle_guide"
}
```

## Chỉnh logic trắc nghiệm

Mở `profile_engine.py`:

- `QUESTIONNAIRE`: câu hỏi, phương án và điểm.
- `ARCHETYPES`: 10 kiểu tiếp nhận cùng vector mục tiêu.
- `LIFE_STAGE_PROMPTS`: bối cảnh học sinh, sinh viên, doanh nhân, người cao tuổi...
- `RELATIONSHIP_PROMPTS`: bối cảnh hôn nhân.
- `CHILDREN_PROMPTS`: bối cảnh con cái.

Không nên dùng giới tính để mặc định người dùng thích được an ủi hay thích giải pháp. Các điểm giao tiếp từ trắc nghiệm mới là tín hiệu chính.

## Thêm dữ liệu cho từng nhân vật

Mở `data/persona_examples.json` và thêm:

```json
{
  "persona": "practical",
  "mode": "advice",
  "tags": ["công việc", "nghỉ việc"],
  "user": "Tin nhắn mẫu",
  "assistant": "Cách Người thực tế nên trả lời",
  "approved": true
}
```

Các giá trị `persona`:

- `strict`
- `gentle`
- `rational`
- `practical`
- `light_humor`

Mode Luyện vẫn dùng file riêng `data/examples.json`.

## Lưu ý người dưới 18 tuổi

Code có lớp chỉ dẫn an toàn bổ sung cho hồ sơ dưới 18 hoặc học sinh. Trước khi phát hành thương mại cho trẻ vị thành niên vẫn cần:

- chính sách độ tuổi và sự đồng ý phù hợp;
- cơ chế báo cáo và hỗ trợ người thật;
- kiểm thử riêng cho bạo lực, lạm dụng, tình dục, tự hại và phụ thuộc cảm xúc;
- tư vấn pháp lý theo thị trường phát hành.

## Kiểm thử

```powershell
pytest -q
```
