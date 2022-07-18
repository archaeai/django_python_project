from enum import auto
from typing import ContextManager
from django.shortcuts import render
from django.http import HttpResponse

import folium
import json
import pandas as pd
import numpy as np
import math
from sitemap.models import MarketScore

pd.options.display.float_format = '{:.2f}'.format

# Create your views here.
geo_path = 'sitemap/static/data/seoul_folium.json'
geo_str = json.load(open(geo_path, encoding='utf-8'))
service_sales = pd.read_csv('sitemap/static/data/업종별_연간_매출_영업개월_폐업률.csv')
sequential = 'YlGnBu'

def index(request):
    return render(request, 'sitemap/index.html')

def test(request):
    return render(request, 'sitemap/test.html')



def data_seoul(df, service):
    service_select = df.loc[df['서비스 업종'] == service]
    service_select['행정동_코드'] = [str(code)+'00'
                                for code in service_select['행정동_코드']]
    service_select.set_index('행정동_코드', inplace=True)
    score = (np.log10((service_select['점포당 연간매출'] / max(service_select['점포당 연간매출'])))
             * (service_select['운영_영업_개월_평균'] / max(service_select['운영_영업_개월_평균']))
             * (service_select['폐업_영업_개월_평균'] / max(service_select['폐업_영업_개월_평균']))
             * (100-service_select['폐업률']*2))
    service_select['상권점수'] = score
    return service_select



def map_service(request):
    geo_path = 'sitemap/static/data/seoul_folium.json'
    geo_str = json.load(open(geo_path, encoding='utf-8'))
    service_sales = pd.read_csv('sitemap/static/data/업종별_연간_매출_영업개월_폐업률.csv')

    try:
        service_name = request.POST['service']
    except:
        service_name = '치킨전문점'

    selected_data = data_seoul(service_sales, service_name)

    map = folium.Map(location=[37.5502, 126.982], zoom_start=11, tiles='Stamen Terrain',
                     width="100%", height="100%")

    folium.Choropleth(geo_data=geo_str, data=selected_data['상권점수'],
                      columns=[selected_data.index, selected_data['상권점수']],
                      fill_color=sequential, key_on='properties.adm_cd2').add_to(map)

    map = map._repr_html_()
    context = {
        'service_name': service_name,
        'm': map,
    }
    return render(request, 'sitemap/map_service.html', context)


def map_gu(request):
    try:
        service_name = request.POST['service']
        gu_name = request.POST['gu']
    except:
        service_name = '치킨전문점'
        gu_name = '강남구'

    #업종 입력 및 분류, 코드 처리
    service_select = service_sales.loc[service_sales['서비스 업종'] == service_name]
    service_select = service_select.copy()
    service_select['행정동_코드'] = [str(code)+'00' for code in service_select['행정동_코드']]

    #구 boundary geo_str 만들기
    geo_str_gu = {
        "type": "FeatureCollection",
        "name": "HangJeongDong_ver20201001",
        "crs": {"type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}}

    geo_str_features = []
    for i in range(len(geo_str['features'])):
        if geo_str['features'][i]['properties']['sggnm'] == gu_name:
            geo_str_features.append(geo_str['features'][i])
 
    geo_str_gu['features'] = geo_str_features

    #지도 중앙 잡기 및 동별 매칭
    lng_gu = []
    lat_gu = []
    dong_code_list = []

    for i in range(len(geo_str_gu['features'])):
        dong_code_list.append(
            geo_str_gu['features'][i]['properties']['adm_cd2'])

        for c1 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'])):
            for c2 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1])):
                for c3 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2])):
                    for c4 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3])):
                        if c4 == 0:
                            lat_gu.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])
                        else:
                            lng_gu.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])

    lng_gu_mid = (max(lng_gu)+min(lng_gu))/2
    lat_gu_mid = (max(lat_gu)+min(lat_gu))/2

    service_dong_select = service_select[service_select['행정동_코드'].isin(dong_code_list)]

    #수치 계산
    service_dong_select = service_dong_select.copy()
    service_dong_select['매출비율'] = [(gold / max(service_dong_select['점포당 연간매출']))
                                   for gold in service_dong_select['점포당 연간매출']]
    #상권점수 계산
    score = ((service_dong_select['점포당 연간매출'] / max(service_dong_select['점포당 연간매출']))
             * (service_dong_select['운영_영업_개월_평균'] / max(service_dong_select['운영_영업_개월_평균']))
             * (service_dong_select['폐업_영업_개월_평균'] / max(service_dong_select['폐업_영업_개월_평균']))
             * (100-service_dong_select['폐업률']*2))
    service_dong_select['상권점수'] = score

    #dataframe index 변경
    service_gu_select = service_dong_select.set_index('행정동_코드')

    #지도에 표시
    map = folium.Map(location=[lng_gu_mid, lat_gu_mid],
                     zoom_start=13, tiles='Stamen Terrain')

    folium.Choropleth(geo_data=geo_str_gu, data=service_gu_select['상권점수'],
                      columns=[service_gu_select.index,
                               service_gu_select['상권점수']],
                      fill_color=sequential, key_on='properties.adm_cd2').add_to(map)
    #동별 마커 설정
    for i in range(len(geo_str_gu['features'])):
        lng_dong = []
        lat_dong = []
        lng_dong_sum = 0
        lat_dong_sum = 0

        gu_dong_name = geo_str_gu['features'][i]['properties']['adm_nm'].split(
        )[1] + ' ' + geo_str_gu['features'][i]['properties']['adm_nm'].split()[2]

        row_data = service_dong_select.loc[service_dong_select['행정동_코드']
                                           == geo_str_gu['features'][i]['properties']['adm_cd2']]
        if len(row_data) == 1:
            html = popup_html(row_data, 0)
        else:
            html = """<!DOCTYPE html>
                    <html>
                    <head>
                    <h3 width="200px" style="color:skyblue">""" + geo_str_gu['features'][i]['properties']['adm_nm'].split()[2] + """</h3>
                    </head><p align='center'>정보 없음</p> """

        iframe = folium.IFrame(html)
        popup = folium.Popup(iframe, min_width=330, max_width=400)

        for c1 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'])):
            for c2 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1])):
                for c3 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2])):
                    for c4 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3])):
                        if c4 == 0:
                            lat_dong.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])
                            lat_dong_sum += geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4]
                        else:
                            lng_dong.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])
                            lng_dong_sum += geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4]

        lng_dong_avg = lng_dong_sum/len(lng_dong)
        lat_dong_avg = lat_dong_sum/len(lat_dong)

        folium.Marker(
             [lng_dong_avg, lat_dong_avg], 
             popup=popup,
             tooltip=gu_dong_name,
            icon=folium.Icon(color='lightblue', icon='th-list')
           ).add_to(map)

     

    map = map._repr_html_()
    context = {
        'm': map,
        'service_name': service_name,
        'gu_name': gu_name,
    }
    return render(request, 'sitemap/map_gu.html', context)



    


def popup_html(df, row):
    i = row
    dong_name = df['동'].iloc[i]
    dong_score = df['상권점수'].iloc[i]
    dong_sales = df['점포당 연간매출'].iloc[i]
    dong_close_month = df['폐업_영업_개월_평균'].iloc[i]
    dong_close_rate = df['폐업률'].iloc[i]

    left_col_color = "#84dfff"
    right_col_color = "#c2fff9"

    html = """<!DOCTYPE html>
        <html>

        <head>
        <h3 width="200px" style="color:skyblue">{}</h3>""".format(dong_name) + """

        </head>
            <table style="height: 126px; width: 300px;">
        <tbody>
        <tr>
        <td style="background-color: """+ left_col_color +""";" align='center'><span style="color: #ffffff;">상권 점수</span></td>
        <td style="width: 150px;background-color: """+ right_col_color +""";" align='right'>{:.2f}점</td>""".format(dong_score) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +""";" align='center'><span style="color: #ffffff;">연평균 매출</span></td>
        <td style="width: 150px;background-color: """+ right_col_color +""";" align='right'>{:.2f}원</td>""".format(dong_sales) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +""";" align='center'><span style="color: #ffffff;">평균 폐업 기간</span></td>
        <td style="width: 150px;background-color: """+ right_col_color +""";" align='right'>{}개월</td>""".format(dong_close_month) + """
        </tr>
        <tr>
        <td style="background-color: """+ left_col_color +""";" align='center'><span style="color: #ffffff;">폐업률</span></td>
        <td style="width: 150px;background-color: """+ right_col_color +""";" align='right'>{:.2f}%</td>""".format(dong_close_rate) + """
        </tr>
        </tbody>
        </table>
        </html>"""
    return html


def graph(request):
    gu_value=[]
    gu_key=[]
    gu_list=['강남구',
 '강동구',
 '강북구',
 '강서구',
 '관악구',
 '광진구',
 '구로구',
 '금천구',
 '노원구',
 '도봉구',
 '동대문구',
 '동작구',
 '마포구',
 '서대문구',
 '서초구',
 '성동구',
 '성북구',
 '송파구',
 '양천구',
 '영등포구',
 '용산구',
 '은평구',
 '종로구',
 '중구',
 '중랑구']
    code_gugu=[11680.0,
11740.0,
 11305.0,
 11500.0,
 11620.0,
 11215.0,
 11530.0,
 11545.0,
 11350.0,
 11320.0,
 11230.0,
 11590.0,
 11440.0,
 11410.0,
 11650.0,
 11200.0,
 11290.0,
 11710.0,
 11470.0,
 11560.0,
 11170.0,
 11380.0,
 11110.0,
 11140.0,
 11260.0]
    for i in range(len(gu_list)):
        lanch=str(code_gugu[i])
        gu_ex=lanch
        gu_value.append(gu_ex)

    my_dic = { gu_list:gu_value for gu_list, gu_value in zip(gu_list, gu_value) }
        

    context =   {
        'gu_list': gu_list,
        'code_gugu' : code_gugu,
        'gu_value':gu_value,
        'my_dic' :  my_dic }
    
    return render(request, 'sitemap/graph.html',context) 



def starbucks(request):
    try:
        service_name = request.POST['service']
        gu_name = request.POST['gu']
    except:
        service_name = '커피-음료'
        gu_name = '금천구'
    #업종 입력 및 분류, 코드 처리
    service_select = service_sales.loc[service_sales['서비스 업종'] == service_name]
    service_select = service_select.copy()
    service_select['행정동_코드'] = [str(code)+'00' for code in service_select['행정동_코드']]
    #구 boundary geo_str 만들기
    geo_str_gu = {
        "type": "FeatureCollection",
        "name": "HangJeongDong_ver20201001",
        "crs": {"type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}}
    geo_str_features = []
    for i in range(len(geo_str['features'])):
        if geo_str['features'][i]['properties']['sggnm'] == gu_name:
            geo_str_features.append(geo_str['features'][i])
    geo_str_gu['features'] = geo_str_features
    #지도 중앙 잡기 및 동별 매칭
    lng_gu = []
    lat_gu = []
    dong_code_list = []
    for i in range(len(geo_str_gu['features'])):
        dong_code_list.append(
            geo_str_gu['features'][i]['properties']['adm_cd2'])
        for c1 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'])):
            for c2 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1])):
                for c3 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2])):
                    for c4 in range(len(geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3])):
                        if c4 == 0:
                            lat_gu.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])
                        else:
                            lng_gu.append(
                                geo_str_gu['features'][i]['geometry']['coordinates'][c1][c2][c3][c4])
    lng_gu_mid = (max(lng_gu)+min(lng_gu))/2
    lat_gu_mid = (max(lat_gu)+min(lat_gu))/2
    service_dong_select = service_select[service_select['행정동_코드'].isin(dong_code_list)]
    #수치 계산
    service_dong_select = service_dong_select.copy()
    service_dong_select['매출비율'] = [(gold / max(service_dong_select['점포당 연간매출']))
                                   for gold in service_dong_select['점포당 연간매출']]
    #상권점수 계산
    score = ((service_dong_select['점포당 연간매출'] / max(service_dong_select['점포당 연간매출']))
             * (service_dong_select['운영_영업_개월_평균'] / max(service_dong_select['운영_영업_개월_평균']))
             * (service_dong_select['폐업_영업_개월_평균'] / max(service_dong_select['폐업_영업_개월_평균']))
             * (100-service_dong_select['폐업률']*2))
    service_dong_select['상권점수'] = score
    #dataframe index 변경
    service_gu_select = service_dong_select.set_index('행정동_코드')
    #지도에 표시
    map = folium.Map(location=[lng_gu_mid, lat_gu_mid],
                     zoom_start=13, tiles='Stamen Terrain')
    folium.Choropleth(geo_data=geo_str_gu, data=service_gu_select['상권점수'],
                      columns=[service_gu_select.index,
                               service_gu_select['상권점수']],
                      fill_color=sequential, key_on='properties.adm_cd2').add_to(map)
    pd.set_option('display.float_format', None)
    star = pd.read_csv('sitemap/static/data/starbucks_dong.csv')
    for i in range(len(star)):
        if star.loc[i]['구'] == gu_name:
            star_lat = star.loc[i]['위도']
            star_lng = star.loc[i]['경도']
            star_tooltip = star.loc[i]['구'] + ' ' + star.loc[i]['동']
            star_html = """<!DOCTYPE html>
                    <html>
                    <head>
                    <h3 width="200px" style="color:green" align='center'>""" + star.loc[i]['매장명'] + """점</h3>
                    </head>"""
            star_iframe = folium.IFrame(star_html)
            star_popup = folium.Popup(star_iframe, min_width=180, max_width=200)
            folium.Marker([star_lat, star_lng], popup=star_popup, tooltip=star_tooltip,
                        icon=folium.Icon(color='green', icon='glyphicon-star')).add_to(map)
    map = map._repr_html_()
    context = {
        'm': map,
        'service_name': service_name,
        'gu_name': gu_name,
    }
    return render(request, 'sitemap/starbucks.html', context)


    