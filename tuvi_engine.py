from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from typing import Any

class TuViEngineError(RuntimeError):
    pass

EARTHLY_BRANCHES=["Tý","Sửu","Dần","Mão","Thìn","Tỵ","Ngọ","Mùi","Thân","Dậu","Tuất","Hợi"]
HEAVENLY_STEMS=["Giáp","Ất","Bính","Đinh","Mậu","Kỷ","Canh","Tân","Nhâm","Quý"]
MAJOR_STAR_NAMES={"Tử Vi","Thiên Cơ","Thái Dương","Vũ Khúc","Thiên Đồng","Liêm Trinh","Thiên Phủ","Thái Âm","Tham Lang","Cự Môn","Thiên Tướng","Thiên Lương","Thất Sát","Phá Quân"}
BRANCH_GRID={"Tỵ":"g1","Ngọ":"g2","Mùi":"g3","Thân":"g4","Thìn":"g5","Dậu":"g6","Mão":"g7","Tuất":"g8","Dần":"g9","Sửu":"g10","Tý":"g11","Hợi":"g12"}

def birth_hour_index(hour:int)->int:
    if not 0<=int(hour)<=23: raise TuViEngineError("Giờ sinh phải nằm trong khoảng 00:00 đến 23:59.")
    return (((int(hour)+1)//2)%12)+1

def _gender_label(value:str)->str:
    text=str(value or '').strip().lower()
    if text in {'male','nam','m','1'}: return 'Nam'
    if text in {'female','nữ','nu','f','-1'}: return 'Nữ'
    raise TuViEngineError('Để lập Tử Vi Đẩu Số đầy đủ, hãy chọn Nam hoặc Nữ.')

def _dict(value:Any)->dict[str,Any]:
    if isinstance(value,dict): return value
    if hasattr(value,'to_dict'):
        try:
            out=value.to_dict()
            if isinstance(out,dict): return out
        except Exception: pass
    if hasattr(value,'__dict__'):
        try: return dict(value.__dict__)
        except Exception: pass
    return {}

def _pick(mapping:dict[str,Any],*keys:str,default:Any='')->Any:
    if not isinstance(mapping,dict): return default
    for key in keys:
        if key in mapping and mapping[key] not in (None,''): return mapping[key]
    norm={str(k).lower().replace('_',''):k for k in mapping}
    for key in keys:
        actual=norm.get(str(key).lower().replace('_',''))
        if actual is not None and mapping.get(actual) not in (None,''): return mapping[actual]
    return default

def _coerce_list(value:Any)->list[Any]:
    if value is None:return []
    if isinstance(value,list):return value
    if isinstance(value,tuple):return list(value)
    if isinstance(value,dict):return list(value.values())
    if isinstance(value,(str,bytes)):return []
    try:return list(value)
    except Exception:return []

def _star_list_from_palace(p:dict[str,Any])->list[Any]:
    for key in ('cung_sao','cungSao','stars','sao','danh_sach_sao','danhSachSao'):
        raw=_pick(p,key,default=None)
        if raw is not None:
            items=_coerce_list(raw)
            if items:return items
    for value in p.values():
        items=_coerce_list(value)
        if not items:continue
        sample=_dict(items[0]); keys={str(k).lower() for k in sample}
        if any('sao' in k or k in {'name','ten'} for k in keys):return items
    return []

def _normalize_star(value:Any)->dict[str,Any]:
    s=_dict(value)
    name=str(_pick(s,'sao_ten','saoTen','ten_sao','tenSao','name','ten',default='') or '').strip()
    element=str(_pick(s,'sao_ngu_hanh','saoNguHanh','ngu_hanh','nguHanh','element','hanh',default='') or '').strip()
    quality=str(_pick(s,'sao_dac_tinh','saoDacTinh','dac_tinh','dacTinh','quality',default='') or '').strip()
    try:star_type=int(_pick(s,'sao_loai','saoLoai','type','loai',default=99))
    except Exception:star_type=99
    major=name in MAJOR_STAR_NAMES or star_type==1
    return {'id':_pick(s,'sao_id','saoID','id',default=''),'name':name,'element':element,'type':star_type,'quality':quality,'direction':str(_pick(s,'sao_phuong_vi','saoPhuongVi','direction',default='') or ''),'yin_yang':str(_pick(s,'sao_am_duong','saoAmDuong','yin_yang',default='') or ''),'trang_sinh':bool(_pick(s,'vong_trang_sinh','vongTrangSinh','trang_sinh',default=False)),'css':str(_pick(s,'css_sao','cssSao','css',default='') or ''),'major':major}

def _find_branch(p:dict[str,Any])->str:
    branch=str(_pick(p,'dia_chi','diaChi','cung_dia_chi','cungDiaChi','branch','chi',default='') or '').strip()
    if branch in EARTHLY_BRANCHES:return branch
    combined=' '.join(str(v) for v in p.values() if isinstance(v,(str,int)))
    for item in EARTHLY_BRANCHES:
        if item in combined:return item
    return branch

def _find_palace_name(p:dict[str,Any])->str:
    known=['Mệnh','Phụ Mẫu','Phúc Đức','Điền Trạch','Quan Lộc','Nô Bộc','Thiên Di','Tật Ách','Tài Bạch','Tử Tức','Phu Thê','Huynh Đệ']
    for key in ('cung_chu','cungChu','ten_cung','tenCung','palace_name','name','cung'):
        value=str(_pick(p,key,default='') or '').strip()
        if value:
            for k in known:
                if k.lower() in value.lower():return k
            if value not in EARTHLY_BRANCHES:return value
    combined=' | '.join(str(v) for v in p.values() if isinstance(v,str))
    for k in known:
        if k.lower() in combined.lower():return k
    return ''

def _normalize_palaces(raw_dia_ban:Any)->list[dict[str,Any]]:
    palaces=[]
    for idx,value in enumerate(_coerce_list(raw_dia_ban)):
        p=_dict(value)
        if not p:continue
        branch=_find_branch(p)
        stars=[_normalize_star(s) for s in _star_list_from_palace(p)]
        stars=[s for s in stars if s.get('name')]
        try:number=int(_pick(p,'cung_so','cungSo','number','so','id',default=idx+1))
        except Exception:number=idx+1
        palaces.append({'number':number,'grid':BRANCH_GRID.get(branch,''),'name':_find_palace_name(p),'can_chi':str(_pick(p,'cung_ten','cungTen','can_chi','canChi','cung_can_chi',default='') or ''),'branch':branch,'element':str(_pick(p,'cung_hanh','cungHanh','hanh','element',default='') or ''),'yin_yang':str(_pick(p,'cung_am_duong','cungAmDuong','am_duong',default='') or ''),'is_than':bool(_pick(p,'cung_than','cungThan','than','is_than',default=False)),'dai_han':_pick(p,'cung_dai_han','cungDaiHan','dai_han','daiHan',default=''),'tieu_han':_pick(p,'cung_tieu_han','cungTieuHan','tieu_han','tieuHan',default=''),'tuan':bool(_pick(p,'tuan_trung','tuanTrung','tuan',default=False)),'triet':bool(_pick(p,'triet_lo','trietLo','triet',default=False)),'stars':stars,'major_stars':[s for s in stars if s.get('major')],'minor_stars':[s for s in stars if not s.get('major')],'raw':p})
    useful=[p for p in palaces if p.get('name') or p.get('branch') or p.get('stars')]
    return (useful if len(useful)>=12 else palaces)[:12]

def _load_tuvi_mcp():
    try:
        from tuvi_mcp import Horoscope
        return Horoscope
    except Exception as exc:
        raise TuViEngineError('Thiếu engine Tử Vi mới. Hãy chạy: pip install tuvi-mcp-server') from exc

def _horoscope_from_birth(*,birth_date:str,birth_time:str,gender:str,display_name:str,time_zone:int=7):
    Horoscope=_load_tuvi_mcp()
    try:
        born=datetime.strptime(str(birth_date),'%Y-%m-%d').date();datetime.strptime(str(birth_time),'%H:%M')
    except ValueError as exc:raise TuViEngineError('Ngày hoặc giờ sinh không hợp lệ.') from exc
    kwargs=dict(name=str(display_name or 'Khách'),year=born.year,month=born.month,day=born.day,hour=str(birth_time),gender=_gender_label(gender),calendar='solar')
    try:return Horoscope.from_birth(**kwargs,timezone=time_zone)
    except TypeError:
        try:return Horoscope.from_birth(**kwargs)
        except Exception as exc:raise TuViEngineError(f'Không lập được lá số Tử Vi: {exc}') from exc
    except Exception as exc:raise TuViEngineError(f'Không lập được lá số Tử Vi: {exc}') from exc

def build_full_tuvi_chart(*,birth_date:str,birth_time:str,gender:str,display_name:str='',time_zone:int=7)->dict[str,Any]:
    if not str(birth_time or '').strip():raise TuViEngineError('Lá số Tử Vi Đẩu Số đầy đủ cần giờ sinh.')
    horoscope=_horoscope_from_birth(birth_date=birth_date,birth_time=birth_time,gender=gender,display_name=display_name,time_zone=time_zone)
    try:
        chart_obj=horoscope.chart();raw=chart_obj.to_dict() if hasattr(chart_obj,'to_dict') else _dict(chart_obj)
    except Exception as exc:raise TuViEngineError(f'Engine không trả được dữ liệu lá số: {exc}') from exc
    if not isinstance(raw,dict) or not raw:raise TuViEngineError('Engine trả về lá số rỗng.')
    thien=_dict(_pick(raw,'thien_ban','thienBan','heaven',default={}));dia=_pick(raw,'dia_ban','diaBan','palaces',default=[]);palaces=_normalize_palaces(dia)
    born=datetime.strptime(str(birth_date),'%Y-%m-%d').date();current_year=date.today().year;stem=HEAVENLY_STEMS[(current_year-4)%10];branch=EARTHLY_BRANCHES[(current_year-4)%12]
    hour_idx=birth_hour_index(datetime.strptime(str(birth_time),'%H:%M').hour)
    return {'available':True,'engine':'tuvi-mcp-server','system':'Tử Vi Đẩu Số','time_zone':time_zone,'birth_hour_index':hour_idx,'birth_hour_branch':EARTHLY_BRANCHES[hour_idx-1],'heaven':{'name':str(display_name or 'Khách'),'gender':_gender_label(gender),'solar_day':born.day,'solar_month':born.month,'solar_year':born.year,'lunar_day':_pick(thien,'ngay_am','ngayAm','lunar_day',default=''),'lunar_month':_pick(thien,'thang_am','thangAm','lunar_month',default=''),'lunar_year':_pick(thien,'nam_am','namAm','lunar_year',default=''),'lunar_year_name':str(_pick(thien,'nam_am_lich','namAmLich','can_chi_nam','year_can_chi',default='') or ''),'yin_yang_destiny':str(_pick(thien,'am_duong_menh','amDuongMenh','yin_yang_destiny',default='') or ''),'bureau_name':str(_pick(thien,'ten_cuc','tenCuc','cuc','bureau',default='') or ''),'menh_chu':str(_pick(thien,'menh_chu','menhChu',default='') or ''),'than_chu':str(_pick(thien,'than_chu','thanChu',default='') or ''),'destiny':str(_pick(thien,'menh','ban_menh','banMenh','destiny',default='') or '')},'palaces':palaces,'star_count':sum(len(p.get('stars',[])) for p in palaces),'major_star_count':sum(len(p.get('major_stars',[])) for p in palaces),'cycle':{'current_year':current_year,'current_year_can_chi':f'{stem} {branch}','current_age':max(0,current_year-born.year)},'raw_chart':raw}

def render_full_tuvi_chart_image(*,birth_date:str,birth_time:str,gender:str,display_name:str='',current_year:int|None=None,time_zone:int=7)->str:
    horoscope=_horoscope_from_birth(birth_date=birth_date,birth_time=birth_time,gender=gender,display_name=display_name,time_zone=time_zone)
    chart_obj=horoscope.chart()
    try:rendered=horoscope.render_chart(chart_obj,year=int(current_year or date.today().year))
    except TypeError:rendered=horoscope.render_chart(chart_obj)
    except Exception as exc:raise TuViEngineError(f'Không render được ảnh lá số: {exc}') from exc
    path=Path(str(rendered))
    if not path.exists() or not path.is_file():raise TuViEngineError('Engine không tạo được file ảnh lá số.')
    return str(path)

def compact_chart_for_ai(chart:dict[str,Any])->dict[str,Any]:
    if not chart or not chart.get('available'):return {}
    raw=chart.get('raw_chart')
    if isinstance(raw,dict) and raw:return raw
    return {'system':chart.get('system'),'heaven':chart.get('heaven',{}),'cycle':chart.get('cycle',{}),'palaces':chart.get('palaces',[])}
