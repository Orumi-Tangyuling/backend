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


@router.get("/predict", response_model=PredictResponse)
async def get_predict(
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
        
        current_dir, current_speed = fetchers.fetch_current(date_obj, latitude, longitude)
        wind_dir, wind_speed = fetchers.fetch_wind(latitude, longitude)

        rad = np.deg2rad(current_dir)
        current_u = current_speed * np.cos(rad)
        current_v = current_speed * np.sin(rad)

        rad = np.deg2rad(wind_dir)
        wind_u = wind_speed * np.cos(rad)
        wind_v = wind_speed * np.sin(rad)

        dayofyear = date_obj.timetuple().tm_yday
        day_sin = np.sin(2 * np.pi * dayofyear / 365)
        day_cos = np.cos(2 * np.pi * dayofyear / 365)

        print(f'dayofyear: {dayofyear}')
        
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

        print(f'trash_amount: {trash_amount}')
        
        # status 결정
        if trash_amount < 100:
            status = TrashStatus.LOW
        elif trash_amount < 300:
            status = TrashStatus.MEDIUM
        else:
            status = TrashStatus.HIGH
        
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
