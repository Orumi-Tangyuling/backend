import joblib
import numpy as np
from typing import Optional


def predict_by_vector(
    model_path: str,
    dayofyear: int,
    day_sin: float,
    day_cos: float,
    wind_speed: float,
    current_speed: float,
    wind_u: float,
    wind_v: float,
    current_u: float,
    current_v: float
) -> float:
    """
    학습된 모델을 사용하여 쓰레기 양을 예측합니다.
    
    Args:
        model_path: 모델 파일 경로
        dayofyear: 연중 몇 번째 날인지 (1-365)
        day_sin: sin(2π * dayofyear / 365)
        day_cos: cos(2π * dayofyear / 365)
        wind_speed: 풍속
        current_speed: 유속
        wind_u: 바람 벡터 u 성분
        wind_v: 바람 벡터 v 성분
        current_u: 해류 벡터 u 성분
        current_v: 해류 벡터 v 성분
    
    Returns:
        예측된 쓰레기 양
    """
    # 모델 로드
    try:
        model = joblib.load(model_path)
    except FileNotFoundError:
        raise Exception(f"모델 파일을 찾을 수 없습니다: {model_path}")
    except Exception as e:
        raise Exception(f"모델 로드 실패: {str(e)}")
    
    # feature_order에 맞춰 feature 준비
    features = np.array([[
        dayofyear,      # 'dayofyear'
        day_sin,        # '일자_sin'
        day_cos,        # '일자_cos'
        wind_speed,     # '풍속'
        current_speed,  # '유속'
        wind_u,         # 'wind_u'
        wind_v,         # 'wind_v'
        current_u,      # 'current_u'
        current_v       # 'current_v'
    ]])

    print(f'features: {features}')
    
    # 예측 수행
    try:
        prediction = model.predict(features)
        return float(prediction[0])
    except Exception as e:
        raise Exception(f"예측 실패: {str(e)}")
