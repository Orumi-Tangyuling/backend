from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from fetch import fetchers
from enum import Enum
import numpy as np
from core.predict import predict_by_vector
import os

router = APIRouter(
    prefix="/v1/trash",
    tags=["trash"]
)


class TrashStatus(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Location(BaseModel):
    latitude: float
    longitude: float


class Prediction(BaseModel):
    trash_amount: float


class PredictResponse(BaseModel):
    date: str
    location: Location
    prediction: Prediction
    status: TrashStatus


class BeachPredictionResponse(BaseModel):
    name: str
    date: str
    location: Location
    prediction: Prediction
    status: TrashStatus


# 제주도 주요 해변 위치 정보
BEACHES = [
    {"name": "AEWOL", "latitude": 33.44639, "longitude": 126.29343, "description": "애월해안(곽지과물해변)"},
    {"name": "JOCHEON", "latitude": 33.54323, "longitude": 126.66986, "description": "조천해안(함덕해수욕장)"},
    {"name": "YERAE", "latitude": 33.22843, "longitude": 126.47737, "description": "예래해안(강정크루즈터미널)"},
    {"name": "HALLIM", "latitude": 33.39511, "longitude": 126.24028, "description": "한림해안(협재해수욕장)"},
    {"name": "SEONGSAN", "latitude": 33.47330, "longitude": 126.93454, "description": "성산해안(성산항)"},
    {"name": "JUNGMUN", "latitude": 33.24421, "longitude": 126.41406, "description": "중문해안(중문색달해수욕장)"},
    {"name": "GUJWA", "latitude": 33.55565, "longitude": 126.79566, "description": "구좌해안(월정리해변)"},
    {"name": "PYOSEON", "latitude": 33.32585, "longitude": 126.84252, "description": "표선해안(표선해비치해변)"},
    {"name": "ANDEOK", "latitude": 33.23000, "longitude": 126.29500, "description": "안덕해안(사계해변)"},
    {"name": "NAMWON", "latitude": 33.27262, "longitude": 126.66034, "description": "남원해안(위미항)"},
    {"name": "DAEJEONG", "latitude": 33.21641, "longitude": 126.25031, "description": "대정해안(모슬포항)"}
]


def calculate_trash_prediction(date_obj: datetime, latitude: float, longitude: float) -> tuple[float, TrashStatus]:
    """
    주어진 날짜와 위치에 대한 쓰레기 양을 예측합니다.
    
    Args:
        date_obj: 예측 날짜
        latitude: 위도
        longitude: 경도
    
    Returns:
        (trash_amount, status) 튜플
    """
    # 해류 및 풍속 데이터 가져오기
    current_dir, current_speed = fetchers.fetch_current(date_obj, latitude, longitude)
    wind_dir, wind_speed = fetchers.fetch_wind(latitude, longitude)

    # 벡터 계산
    rad = np.deg2rad(current_dir)
    current_u = current_speed * np.cos(rad)
    current_v = current_speed * np.sin(rad)

    rad = np.deg2rad(wind_dir)
    wind_u = wind_speed * np.cos(rad)
    wind_v = wind_speed * np.sin(rad)

    # 날짜 feature 계산
    dayofyear = date_obj.timetuple().tm_yday
    day_sin = np.sin(2 * np.pi * dayofyear / 365)
    day_cos = np.cos(2 * np.pi * dayofyear / 365)
    
    print(f'Features - dayofyear: {dayofyear}, day_sin: {day_sin:.4f}, day_cos: {day_cos:.4f}, '
          f'wind_speed: {wind_speed:.2f}, current_speed: {current_speed:.2f}, '
          f'wind_u: {wind_u:.2f}, wind_v: {wind_v:.2f}, current_u: {current_u:.2f}, current_v: {current_v:.2f}')
    
    # trash_amount 예측
    trash_amount = predict_by_vector(
        model_path=os.environ.get('MODEL_PATH'),
        dayofyear=dayofyear,
        day_sin=day_sin,
        day_cos=day_cos,
        wind_speed=wind_speed,
        current_speed=current_speed,
        wind_u=wind_u,
        wind_v=wind_v,
        current_u=current_u,
        current_v=current_v
    )
    
    # status 결정
    if trash_amount < 100:
        status = TrashStatus.LOW
    elif trash_amount < 300:
        status = TrashStatus.MEDIUM
    else:
        status = TrashStatus.HIGH
    
    return trash_amount, status


@router.get("/predict", response_model=PredictResponse)
async def get_prediction(
    date: str = Query(
        ..., 
        description="날짜 및 시간 (ISO 8601 형식)",
        example="2016-01-05T15:20:00"
    ),
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
        description="위도 (-90 ~ 90)",
        example=33.4507
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
        description="경도 (-180 ~ 180)",
        example=126.5707
    )
):
    """
    쓰레기 양 예측 데이터를 조회합니다.
    
    - **date**: 날짜 및 시간 (ISO 8601 형식, 예: "2016-01-05T15:20:00")
    - **latitude**: 위도 (-90 ~ 90)
    - **longitude**: 경도 (-180 ~ 180)
    """
    try:
        # ISO 8601 형식 날짜 파싱
        date_obj = datetime.fromisoformat(date)
        
        # 쓰레기 양 예측
        trash_amount, status = calculate_trash_prediction(date_obj, latitude, longitude)
        
        return PredictResponse(
            date=date_obj.strftime("%Y-%m-%d"),
            location=Location(
                latitude=latitude,
                longitude=longitude
            ),
            prediction=Prediction(
                trash_amount=trash_amount
            ),
            status=status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"날짜 형식이 올바르지 않습니다 (ISO 8601 형식 필요): {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/beach", response_model=list[BeachPredictionResponse])
async def get_beach_predictions():
    """
    제주도 주요 해변의 쓰레기 양 예측 데이터를 조회합니다.
    
    11개 해변의 현재 시점 기준 쓰레기 예측량을 반환합니다.
    """
    try:
        # 현재 날짜 및 시간 사용
        date_obj = datetime.now()
        
        results = []
        
        for beach in BEACHES:
            try:
                latitude = beach["latitude"]
                longitude = beach["longitude"]
                
                # 쓰레기 양 예측
                trash_amount, status = calculate_trash_prediction(date_obj, latitude, longitude)
                
                results.append(BeachPredictionResponse(
                    name=beach["name"],
                    date=date_obj.strftime("%Y-%m-%d"),
                    location=Location(
                        latitude=latitude,
                        longitude=longitude
                    ),
                    prediction=Prediction(
                        trash_amount=trash_amount
                    ),
                    status=status
                ))
                
            except Exception as beach_error:
                # 개별 해변 에러는 로깅만 하고 계속 진행
                print(f"해변 {beach['name']} 예측 실패: {str(beach_error)}")
                continue
        
        if not results:
            raise Exception("모든 해변 예측에 실패했습니다")
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
