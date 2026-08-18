from tuvi_engine import _star_dict, _attr

def test_attr_reads_mapping():
    item = {"saoTen": "Tử vi", "saoLoai": 1}
    assert _attr(item, "saoTen") == "Tử vi"
    assert _attr(item, "saoLoai") == 1

def test_star_dict_reads_ansaotuvi_mapping():
    raw = {
        "saoID": 1,
        "saoTen": "Tử vi",
        "saoNguHanh": "O",
        "saoLoai": 1,
        "saoPhuongVi": "Đế tinh",
        "saoAmDuong": -1,
        "vongTrangSinh": 0,
        "cssSao": "hanhTho",
        "saoDacTinh": "M",
    }
    star = _star_dict(raw)
    assert star["name"] == "Tử vi"
    assert star["type"] == 1
    assert star["major"] is True
    assert star["element"] == "Thổ"
    assert star["quality"] == "M"
    assert star["css"] == "hanhTho"
