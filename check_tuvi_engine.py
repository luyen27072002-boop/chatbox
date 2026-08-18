from tuvi_engine import build_full_tuvi_chart, render_full_tuvi_chart_image
chart=build_full_tuvi_chart(birth_date='2000-06-15',birth_time='10:30',gender='female',display_name='Test')
print('Engine:',chart.get('engine'))
print('Raw chart keys:',list((chart.get('raw_chart') or {}).keys()))
print('Palaces:',len(chart.get('palaces') or []))
print('Stars:',chart.get('star_count'))
print('Image:',render_full_tuvi_chart_image(birth_date='2000-06-15',birth_time='10:30',gender='female',display_name='Test'))
