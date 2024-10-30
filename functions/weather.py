from sqlalchemy.orm import Session
from models import User, AssistantThread
from datetime import datetime, timedelta
import json
import os
import sqlite3
import xml.etree.ElementTree as ET
import numpy as np
import requests
from utils.config import variables

weather_key = variables.WEATHER_KEY

try:
    weather_db = sqlite3.connect('database/location_grid.db')
except sqlite3.Error as e:
    print(f"Error: {e}\n\t└ Failed to connect to database")
cursor = weather_db.cursor()

# WEATHER_CATEGORIES_KOR = {
#     "T1H" : "기온", # ℃
#     "RN1" : "시간당 강수량", # 범주
#     "SKY" : "하늘상태", # 맑음(1), 구름많음(3), 흐림(4)
#     "UUU" : "동서바람성분", # m/s
#     "VVV" : "남북바람성분", # m/s
#     "REH" : "습도", # %
#     "PTY" : "강수형태", # 없음(0), 비(1), 비/눈(2), 눈(3), 빗방울(5), 빗방울눈날림(6), 눈날림(7)
#     "LGT" : "낙뢰", # kA
#     "VEC" : "풍향", # deg
#     "WSD" : "풍속", # m/s
#     "WCT" : "체감온도", # ℃
# }
    # 아래 정보를 GPT에게 넣어주어야함
    # * +900이상, –900 이하 값은 Missing 값으로 처리
    # 관측장비가 없는 해양 지역이거나 관측장비의 결측 등으로 자료가 없음을 의미
    # * 압축 Bit 수의 경우 Missing 값이 아닌 경우의 기준
def calcTemp(tmp, wind_speed):
    if tmp is not None and wind_speed is not None:
        return 13.12 + 0.6215 * float(tmp) - 11.37 * (float(wind_speed) ** 0.16) + 0.3965 * float(tmp) * (float(wind_speed) ** 0.16)
    return None
def saveWeatherFile(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def loadWeatherFile(filepath):
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)
    
def parseWeatherData(items):
    weather_summaries = {}
    
    for item in items:
        category = item.find('category').text
        value = item.find('fcstValue').text
        date = item.find('fcstDate').text
        time = item.find('fcstTime').text
        datetime_key = f"{date}_{time}"
        
        if category not in weather_summaries:
            weather_summaries[category] = {}
        weather_summaries[category][datetime_key] = value
    
    for datetime_key in weather_summaries.get('TMP', {}):
        temp = float(weather_summaries['TMP'][datetime_key])
        wind_speed = float(weather_summaries.get('WSD', {}).get(datetime_key, 0))
        wind_chill = calcTemp(temp, wind_speed)
        if 'WCI' not in weather_summaries:
            weather_summaries['WCI'] = {}
        weather_summaries['WCI'][datetime_key] = round(wind_chill, 2)
    
    return weather_summaries


def returnFormat(status, message, data=None):
    return {
        "status" : status,
        "message" : message,
        "data" : data if data else {}
    }
def getRoundedTime(time):
    if time.minute >= 30:
        return time.replace(minute=30, second=0, microsecond=0)
    else:
        return time.replace(minute=0, second=0, microsecond=0)
def getUltraSrtFcst(thread_id = None, db: Session = None):
    user = db.query(User).join(AssistantThread).filter(AssistantThread.thread_id == thread_id).first()
    
    if user is None or user.latitude is None or user.longitude is None:
        return returnFormat("105", "사용자 위치 정보가 없습니다.")
    
    latitude = user.latitude
    longitude = user.longitude
    
    def haversine(lat1, lon1, lat2, lon2):
        # Haversine 공식을 이용한 거리 계산
        R = 6371.0
        lat1_rad, lon1_rad = np.radians(lat1), np.radians(lon1)
        lat2_rad, lon2_rad = np.radians(lat2), np.radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        return R * c

    cursor = weather_db.cursor()
    cursor.execute("SELECT x, y, latitude_s_per_100, longitude_s_per_100 FROM location_grid")
    rows = cursor.fetchall()
    nearest_x = None
    nearest_y = None
    min_distance = float('inf')

    for row in rows:
        x, y, lat_s_per_100, lon_s_per_100 = row
        distance = haversine(latitude, longitude, lat_s_per_100, lon_s_per_100)
        if distance < min_distance:
            min_distance = distance
            nearest_x = x
            nearest_y = y

    current_time = datetime.now()
    base_date = current_time.strftime('%Y%m%d')

    rounded_time = getRoundedTime(current_time)
    time_list = [(rounded_time - timedelta(minutes=30 * i)).strftime('%H%M') for i in range(10)]
    cache_file = f'./weather_data/{nearest_x}_{nearest_y}_{base_date}_{time_list[0]}.xml'
    if os.path.exists(cache_file):
        data = loadWeatherFile(cache_file)
        return returnFormat("00", "NORMAL_SERVICE", data)
            
    for i in range(6):
        base_time = rounded_time.strftime('%H%M')
        rounded_time -= timedelta(minutes=30)

        # API 호출 시도
        # 아래 엔드포인트는 단기예보... 아침시간에 준나 오래 걸림 ( 거의 40초? )
        # 대신 점심, 저녁 사용량이 적은 시간대는 빠르긴함 ( 약 2~3초 )
        # 타임아웃 걸고 못찾았다고 하는 것 도 좋아보이긴함
        # url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'
        # 초단기 예보, 초 빠름 ( <1s )
        # 단기예보 : 최대 3일까지 예보
        # 초단기예보 : 6시간 예보

        url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst'
        params = {
            'serviceKey': weather_key,
            'pageNo': '1',
            'numOfRows': '266',
            'dataType': 'XML', # JSON 타입은 가끔 XML로 반한되어버림
            'base_date': base_date,
            'base_time': base_time,
            'nx': nearest_x,
            'ny': nearest_y
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.content)
                items = root.find('.//items')
                header = root.find('header')
                resultMsg = header.find('resultMsg').text
                resultCode = header.find('resultCode').text
                if resultCode == "00":
                    items = root.find('.//items')
                    weather_summary = parseWeatherData(items.findall('item'))
                    saveWeatherFile(cache_file, weather_summary)
                    return returnFormat("00", "NORMAL_SERVICE", weather_summary)
                
                elif i < 9:
                    continue
                else:
                    return returnFormat(resultCode, resultMsg)
                
            except ET.ParseError:
                return returnFormat("102", "Failed to parse XML response")
        else:
            return returnFormat("103", f"API request failed with status {response.status_code}")


    return returnFormat("104", "No valid weather data found after attempts")