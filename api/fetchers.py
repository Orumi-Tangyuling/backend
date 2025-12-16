import requests
import numpy as np
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_current(date, lat, lot):
    base_url = "http://www.khoa.go.kr/api/oceangrid/tidalCurrentArea/search.do"

    target_date = date.strftime("%Y%m%d")
    target_hour = date.strftime("%H")
    target_minute = date.strftime("%M")
    
    min_y = int(np.floor(lat))
    max_y = int(np.ceil(lat))
    min_x = int(np.floor(lot))
    max_x = int(np.ceil(lot))

    params = {
        "ServiceKey": os.environ.get('API_KEY'),
        "Date": target_date,
        "Hour": target_hour,
        "Minute": target_minute,
        "MaxX": max_x,
        "MinX": min_x,
        "MaxY": max_y,
        "MinY": min_y,
        "ResultType": "json"
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    if 'result' not in data or 'data' not in data['result']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    total_current_dir = 0.0
    total_current_speed = 0.0
    cnt = 0

    for d in data['result']['data']:
        if 'current_dir' not in d or 'current_speed' not in d:
            continue
        total_current_dir += float(d['current_dir'])
        total_current_speed += float(d['current_speed'])
        cnt += 1

    if cnt == 0:
        raise Exception("유효한 데이터가 없습니다")

    return total_current_dir / cnt, total_current_speed / cnt