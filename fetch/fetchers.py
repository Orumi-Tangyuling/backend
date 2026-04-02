import requests
from datetime import datetime
import os
from dotenv import load_dotenv
from utils import location

load_dotenv()

DEFAULT_CURRENT_API_URL = "https://apis.data.go.kr/1192136/twRecent/GetTWRecentApiService"
DEPRECATED_CURRENT_API_URL_PATTERNS = (
    "khoa.go.kr/api/oceangrid/tidalcurrentarea/search.do",
    "khoa.go.kr/api/oceangrid/tidalcurrent/search.do",
)


def _resolve_current_api_url() -> str:
    configured = (os.environ.get('CURRENT_API_URL') or "").strip()
    if configured and (
        (configured.startswith('"') and configured.endswith('"'))
        or (configured.startswith("'") and configured.endswith("'"))
    ):
        configured = configured[1:-1]

    if not configured:
        return DEFAULT_CURRENT_API_URL

    configured_lower = configured.lower()
    if any(pattern in configured_lower for pattern in DEPRECATED_CURRENT_API_URL_PATTERNS):
        return DEFAULT_CURRENT_API_URL

    return configured


def _resolve_current_api_key() -> str | None:
    # 배포 환경 호환을 위해 CURRENT_API_KEY를 우선 사용하고, 없으면 WIND_API_KEY를 사용한다.
    return os.environ.get('CURRENT_API_KEY') or os.environ.get('WIND_API_KEY')


def _parse_observation_time(value: str) -> datetime | None:
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def _fetch_tw_recent_items(
    *,
    base_url: str,
    api_key: str,
    obs_code: str,
    req_date: str,
    interval_min: int = 30,
) -> list[dict]:
    params = {
        "serviceKey": api_key,
        "obsCode": obs_code,
        "reqDate": req_date,
        "min": interval_min,
        "pageNo": 1,
        "numOfRows": 300,
        "type": "json",
    }

    response = requests.get(base_url, params=params, timeout=20)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    if 'header' not in data:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    if data['header']['resultCode'] != "00":
        raise Exception(f"API 오류: {data['header'].get('resultMsg', 'Unknown error')}")

    if 'body' not in data or 'items' not in data['body'] or 'item' not in data['body']['items']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    items = data['body']['items']['item']
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return items
    return []


def _select_best_current_item(items: list[dict], target_time: datetime) -> dict | None:
    candidates: list[tuple[float, dict]] = []
    for item in items:
        if item.get('crdir') is None or item.get('crsp') is None:
            continue

        observed_at = _parse_observation_time(item.get('obsrvnDt'))
        if observed_at is None:
            continue

        try:
            float(item['crdir'])
            float(item['crsp'])
        except (TypeError, ValueError):
            continue

        distance = abs((observed_at - target_time).total_seconds())
        candidates.append((distance, item))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def fetch_current(date: datetime, lat: float, lot: float):
    base_url = _resolve_current_api_url()
    api_key = _resolve_current_api_key()
    if not api_key:
        raise Exception("CURRENT_API_KEY가 설정되지 않았습니다")

    req_date = date.strftime("%Y%m%d")

    # 가까운 관측소부터 순차 조회하여 유향/유속 결측 시 다음 관측소로 fallback
    ordered_locations = sorted(
        location.OBSERVATORY_LOCATIONS,
        key=lambda loc: loc.distance_to(lat, lot)
    )

    errors: list[str] = []

    for loc in ordered_locations:
        try:
            items = _fetch_tw_recent_items(
                base_url=base_url,
                api_key=api_key,
                obs_code=loc.code,
                req_date=req_date,
                interval_min=30,
            )
            best = _select_best_current_item(items, date)
            if best is None:
                errors.append(f"{loc.code}: 유향/유속 유효값 없음")
                continue

            return float(best['crdir']), float(best['crsp'])
        except Exception as e:
            errors.append(f"{loc.code}: {str(e)}")

    raise Exception(f"유효한 데이터가 없습니다 ({'; '.join(errors)})")

def fetch_wind(date: datetime, lat: float, lot: float):
    base_url = os.environ.get('WIND_API_URL')

    nearest = location.find_nearest_legacy_location(lat, lot)
    
    # 날짜를 YYYYMMDD 형식으로 변환
    req_date = date.strftime("%Y%m%d")

    params = {
        "serviceKey": os.environ.get('WIND_API_KEY'),
        "obsCode": nearest.code,
        "reqDate": req_date,
        "min": 30,
        "numOfRows": 300,
        "type": "json"
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    # header 검증
    if 'header' not in data:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")
    
    if data['header']['resultCode'] != "00":
        raise Exception(f"API 오류: {data['header'].get('resultMsg', 'Unknown error')}")

    # body 검증
    if 'body' not in data or 'items' not in data['body'] or 'item' not in data['body']['items']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    items = data['body']['items']['item']
    
    total_wind_dir = 0.0
    total_wind_speed = 0.0
    cnt = 0

    for item in items:
        if 'wndrct' not in item or 'wspd' not in item:
            continue
        if item['wndrct'] is None or item['wspd'] is None:
            continue
        total_wind_dir += float(item['wndrct'])
        total_wind_speed += float(item['wspd'])
        cnt += 1

    if cnt == 0:
        raise Exception("유효한 데이터가 없습니다")

    return total_wind_dir / cnt, total_wind_speed / cnt

def fetch_temperature(date: datetime, lat: float, lot: float):
    base_url = os.environ.get('TEMPERATURE_API_URL')

    nearest = location.find_nearest_legacy_location(lat, lot)

    # 날짜를 YYYYMMDD 형식으로 변환
    req_date = date.strftime("%Y%m%d")

    params = {
        "serviceKey": os.environ.get('TEMPERATURE_API_KEY'),
        "obsCode": nearest.code,
        "reqDate": req_date,
        "min": 30,
        "numOfRows": 300,
        "type": "json"
    }

    response = requests.get(base_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API 요청 실패: {response.status_code}")

    try:
        data = response.json()
    except ValueError as e:
        raise Exception(f"JSON 파싱 실패: {response.text}")

    # header 검증
    if 'header' not in data:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")
    
    if data['header']['resultCode'] != "00":
        raise Exception(f"API 오류: {data['header'].get('resultMsg', 'Unknown error')}")

    # body 검증
    if 'body' not in data or 'items' not in data['body'] or 'item' not in data['body']['items']:
        raise Exception("응답 데이터 형식이 올바르지 않습니다")

    items = data['body']['items']['item']
    
    total_temperature = 0.0
    cnt = 0

    for item in items:
        if 'wtem' not in item:
            continue
        if item['wtem'] is None:
            continue
        total_temperature += float(item['wtem'])
        cnt += 1

    if cnt == 0:
        raise Exception("유효한 데이터가 없습니다")

    return total_temperature / cnt
