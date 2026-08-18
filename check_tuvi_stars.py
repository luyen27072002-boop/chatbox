from tuvi_engine import build_full_tuvi_chart

print("Nhập thử dữ liệu mẫu để kiểm tra engine/parser")
chart = build_full_tuvi_chart(
    birth_date="2000-06-15",
    birth_time="10:30",
    gender="female",
    display_name="Test",
)
print("Tổng sao:", chart.get("star_count"))
print("Tổng chính tinh:", chart.get("major_star_count"))
for palace in chart.get("palaces", []):
    major = ", ".join(x.get("name", "") for x in palace.get("major_stars", [])) or "Vô chính diệu"
    print(f"{palace.get('name')}: {major} | tổng sao={palace.get('star_count')}")
